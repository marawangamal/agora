import copy
import itertools
import os
import random
import re
import subprocess
import tempfile
import time
from typing import Callable, Dict, List, Optional, Union

import yaml
from jrun._base import JobDB
from jrun.interfaces import JobSpec, PGroup, PJob

JOB_RE = re.compile(r"Submitted batch job (\d+)")
# TODO: Add deps table to schema and use a view to get deps on the fly


class JobSubmitter(JobDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _parse_job_id(self, result: str) -> int:
        # job_id = result.split(" ")[-1].strip()
        # if not job_id:
        #     raise ValueError("Failed to parse job ID from sbatch output.")
        # return job_id
        # Typical line: "Submitted batch job 123456"
        m = JOB_RE.search(result)
        if m:
            jobid = int(m.group(1))
            return jobid
        else:
            raise RuntimeError(f"Could not parse job id from sbatch output:\n{result}")

    def _submit_jobspec(
        self,
        job_spec: JobSpec,
        dry: bool = False,
        ignore_statuses: List[str] = ["PENDING", "RUNNING", "COMPLETED"],
    ):
        """Submit a single job to SLURM and return the job ID.

        Args:
            job_spec: The job specification to submit
        Returns:
            The job ID as a string
        """

        if dry:
            job_spec.command += " --dry"

        # Create a temporary script file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            script_path = f.name
            f.write(job_spec.to_script(deptype=self.deptype))

        try:
            # Check if the job is already submitted
            prev_job = self.get_job_by_command(job_spec.command)
            if prev_job:
                if prev_job.status in ignore_statuses:
                    print(f"Job with command '{job_spec.command}' already submitted")
                    return prev_job.job_id
                else:
                    print(f"Job with command '{job_spec.command}' failed, resubmitting")

            # Submit the job using sbatch
            result = os.popen(f"sbatch {script_path}").read()
            job_id = self._parse_job_id(result)
            job_spec.job_id = job_id
            self.insert_record(JobSpec(**job_spec.to_dict()))
            print(f"Submitted job with ID {job_id}")

            # clean up
            if prev_job:
                # remove the previous job from the database
                self.delete_record(prev_job.job_id)

            # add small delay
            time.sleep(0.1)
            return job_id
        finally:
            # Clean up the temporary file
            os.unlink(script_path)

    def cancel(self, job_id: int):
        """Cancel jobs with the given job IDs."""
        try:
            subprocess.run(["scancel", str(job_id)], check=True)
            print(f"Cancelled job {job_id}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to cancel job {job_id}: {e}")

    def cancel_all(self):
        """Cancel all jobs in the database."""
        jobs = self.get_jobs()
        for job in jobs:
            self.cancel(job.job_id)

    def delete(self, job_ids: Optional[List[int]] = None, cascade: bool = False):
        """Delete jobs with the given job IDs."""
        if job_ids is None:
            # If no job IDs are provided, delete all jobs
            job_ids = [job.job_id for job in self.get_jobs()]

        for job_id in job_ids:
            self.cancel(job_id)
            self.delete_record(job_id)
            if cascade:
                self.delete([c.job_id for c in self.get_children(job_id)])

    def retry(self, job_id: int, job: Optional[JobSpec] = None, force: bool = False):
        """Retry a job with the given job ID."""
        if job is None:
            job = self.get_job_by_id(job_id)
        inactive_jobs = [j for j in self.get_jobs() if j.status == "COMPLETED"]
        if job:
            job.inactive_deps = [
                j.job_id for j in inactive_jobs if j.job_id in job.depends_on
            ]
            print(f"Retrying job {job_id}")
            ignore_statuses = ["RUNNING", "COMPLETED"] if not force else []
            new_job_id = self._submit_jobspec(
                job, dry=False, ignore_statuses=ignore_statuses
            )

            # Get children -- should be resubmitted too
            children = self.get_children(job_id)
            for child in children:
                child.depends_on.remove(str(job_id))
                child.depends_on.append(str(new_job_id))
                # delete the old job
                # self.delete_record(child)
                self.retry(child.job_id, child)

        else:
            print(f"Job {job_id} not found in the database.")

    def submit(
        self,
        file: str,
        dry: bool = False,
        debug: bool = False,
        use_group_id: bool = False,
    ):
        """Parse the YAML file and submit jobs."""
        cfg = yaml.safe_load(open(file))

        preamble_map = {
            name: "\n".join(lines) for name, lines in cfg["preambles"].items()
        }

        submit_fn = lambda job: self._submit_jobspec(job, dry=dry)
        self.walk(
            node=self._parse_group_dict(cfg["group"]),
            preamble_map=preamble_map,
            debug=debug,
            depends_on=[],
            submitted_jobs=[],
            submit_fn=submit_fn,
        )

    def walk(
        self,
        node: Union[PGroup, PJob],
        preamble_map: Dict[str, str],
        debug: bool = False,
        depends_on: List[int] = [],
        group_name: str = "",
        submitted_jobs: List[int] = [],
        submit_fn: Optional[Callable[[JobSpec], int]] = None,
        group_id: Optional[str] = None,
        loop_id: Optional[str] = None,
    ):
        """Recursively walk the job tree and submit jobs."""
        submit_fn = submit_fn if submit_fn is not None else self._submit_jobspec
        subgroup_id = f"{random.randint(100000, 999999)}"
        group_id = subgroup_id if group_id is None else f"{group_id}-{subgroup_id}"

        # Base case (single leaf)
        if isinstance(node, PJob):
            # Leaf node
            # generate rand job id int
            job_id = random.randint(100000, 999999)
            job = JobSpec(
                job_id=job_id,
                group_name=group_name,
                command=node.command,
                preamble=preamble_map.get(node.preamble, ""),
                depends_on=[str(_id) for _id in depends_on],
                loop_id=loop_id,
            )
            job.command = job.command.format(group_id=group_id)
            if debug:
                print(f"\nDEBUG:\n{job.to_script(self.deptype)}\n")
            else:
                job_id = submit_fn(job)
            submitted_jobs.append(job_id)
            return [job_id]

        # Base case (sweep)
        elif node.type == "sweep":
            job_ids = []
            cmd_template = node.sweep_template
            sweep = node.sweep
            # Generate all combinations of the sweep parameters
            keys = list(sweep.keys())
            values = list(sweep.values())
            # Generate all combinations of the sweep parameters
            combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
            # Iterate over the combinations
            for i, params in enumerate(combinations):
                job_id = random.randint(100000, 999999)
                cmd = cmd_template.format(**params, group_id=group_id)
                job = JobSpec(
                    job_id=job_id,
                    group_name=group_name,
                    command=cmd,
                    preamble=preamble_map.get(node.preamble, ""),
                    depends_on=[str(_id) for _id in depends_on],
                    loop_id=loop_id,
                )
                if debug:
                    print(f"\nDEBUG:\n{job.to_script(self.deptype)}\n")
                else:
                    job_id = submit_fn(job)
                submitted_jobs.append(job_id)
                job_ids.append(job_id)
            return job_ids

        # Recursive case:
        elif node.type == "sequential":
            # Sequential group
            for i, entry in enumerate(node.jobs):
                group_name_i = ":".join(
                    [p for p in [copy.deepcopy(group_name), entry.name] if p]
                )
                job_ids = self.walk(
                    entry,
                    debug=debug,
                    preamble_map=preamble_map,
                    # depends_on=depends_on,
                    # make a copy of depends_on
                    depends_on=copy.deepcopy(depends_on),
                    submitted_jobs=submitted_jobs,
                    submit_fn=submit_fn,
                    group_id=copy.deepcopy(group_id),
                    group_name=group_name_i,
                )
                if job_ids:
                    depends_on.extend(job_ids)
            return job_ids

        elif node.type == "parallel":
            # Parallel group
            parallel_job_ids = []
            for entry in node.jobs:
                group_name_i = ":".join(
                    [p for p in [copy.deepcopy(group_name), entry.name] if p]
                )
                job_ids = self.walk(
                    entry,
                    debug=debug,
                    preamble_map=preamble_map,
                    depends_on=copy.deepcopy(depends_on),
                    submitted_jobs=submitted_jobs,
                    submit_fn=submit_fn,
                    group_id=copy.deepcopy(group_id),
                    group_name=group_name_i,
                )
                if job_ids:
                    parallel_job_ids.extend(job_ids)
            return parallel_job_ids

        elif node.type == "loop":
            # Sequential group
            sequential_job_ids = []
            loop_id = (
                f"{random.randint(100000, 999999)}" if loop_id is None else loop_id
            )
            for t in range(node.loop_count):
                for i, entry in enumerate(node.jobs):
                    group_name_i = ":".join(
                        [p for p in [copy.deepcopy(group_name), entry.name] if p]
                    )
                    job_ids = self.walk(
                        entry,
                        debug=debug,
                        preamble_map=preamble_map,
                        # depends_on=depends_on,
                        # make a copy of depends_on
                        depends_on=copy.deepcopy(depends_on),
                        submitted_jobs=submitted_jobs,
                        submit_fn=submit_fn,
                        group_id=copy.deepcopy(group_id),
                        group_name=group_name_i,
                        loop_id=loop_id,
                    )
                    if job_ids:
                        depends_on.extend(job_ids)
                        sequential_job_ids.extend(job_ids)
            return sequential_job_ids

        return submitted_jobs

    def sbatch(self, args: list):
        # Call sbatch with the provided arguments
        result = subprocess.run(
            ["sbatch"] + args, check=True, capture_output=True, text=True
        ).stdout.strip()
        job_id = self._parse_job_id(result)
        self.insert_record(
            JobSpec(
                job_id=job_id,
                group_name="sbatch",
                command=" ".join(args),
                preamble="",
                depends_on=[],
            )
        )
