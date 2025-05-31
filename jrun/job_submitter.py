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
from jrun.interfaces import Job, JobInsert, Job, PGroup, PJob

JOB_RE = re.compile(r"Submitted batch job (\d+)")
INACTIVE_PARENT_RULES = [
    lambda id, status, force: status in ["COMPLETED"],
    lambda id, status, force: status in ["FAILED", "CANCELLED"] and force,
]

class JobSubmitter(JobDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _parse_job_id(self, result: str) -> str:
        m = JOB_RE.search(result)
        if m:
            jobid = m.group(1)
            return jobid
        else:
            raise RuntimeError(f"Could not parse job id from sbatch output:\n{result}")

    def _submit_job(
        self,
        job: Job,
        dry: bool = False,
        ignore_statuses: List[str] = ["PENDING", "RUNNING", "COMPLETED"],
        prev_job_id: Optional[str] = None,
    ):
        """Submit a single job to SLURM and return the job ID.

        Args:
            job_spec: The job specification to submit
        Returns:
            The job ID as a string
        """

        if dry:
            job.command += " --dry"

        # 1. Create a temporary file from script
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            script_path = f.name
            f.write(job.to_script(deptype=self.deptype))

        try:
            # 2. Check for prev job
            prev_job = None
            if prev_job_id:  # Lookup by ID
                prev_jobs = self.get_jobs([f"id={prev_job_id}"])
                prev_job = prev_jobs[0] if prev_jobs else None
            else:  # Lookup by command
                prev_jobs = self.get_jobs([f"command='{job.command}'"])
                prev_job = prev_jobs[0] if prev_jobs else None
                if prev_job and prev_job.status in ignore_statuses:
                    print(f"Job {prev_job.id} already submitted with status {prev_job.status}.")
                    return prev_job.id

            # 3. Submit job (sbatch)
            result = os.popen(f"sbatch {script_path}").read()
            job.id = self._parse_job_id(result)
            print(f"Submitted job with ID {job.id}")


            # 4. Upsert job in the database
            upsert_job = JobInsert(**{
                k: v for k, v in job.to_dict().items() if k in JobInsert.__dataclass_fields__
            })

            # clean up
            if prev_job:
                print(f"Updating existing job: {prev_job.id} => {upsert_job.id}")
                self.update_job(prev_job.id, upsert_job)
            else:
                print(f"Inserting new job: {upsert_job.id}")
                self.create_job(upsert_job)
            self.upsert_deps(upsert_job.id, job.parents)
            time.sleep(0.1)
            return job.id
        finally:
            # Clean up the temporary file
            os.unlink(script_path)

    def cancel(self, job_id: str):
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
            self.cancel(job.id)

    def delete(self, job_ids: Optional[List[str]] = None, cascade: bool = False):
        """Delete jobs with the given job IDs."""
        if not job_ids:
            print("No job IDs provided, deleting all jobs in the database.")
            job_ids = [job.id for job in self.get_jobs(ignore_status=True)]

        for id in job_ids:
            print(f"Deleting job {id}")
            self.delete_job(id, on_delete=lambda id: self.cancel(id), cascade=cascade)

    def retry(self, job_id: str, force: bool = False):
        """Retry a job with the given job ID."""
        job = self.get_jobs([f"id={job_id}"])[0]
        parent_states = self.get_job_states(job.parents)

        if job:
            print(f"Retrying job {job_id}")
            ignore_statuses = ["COMPLETED"] if not force else []

            # Add inactive parents to the job
            for parent_id in job.parents:
                for rule in INACTIVE_PARENT_RULES:
                    parent_state = parent_states.get(parent_id, {})
                    if rule(parent_id, parent_state.get("status", ""), force):
                        job.inactive_parents.append(parent_id)
            
            self._submit_job(
                job, dry=False, ignore_statuses=ignore_statuses, prev_job_id=job_id
            )

            # Get children -- should be resubmitted too
            for child_id in job.children:
                self.retry(child_id)
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

        submit_fn = lambda job: self._submit_job(job, dry=dry)
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
        depends_on: List[str] = [],
        submitted_jobs: List[str] = [],
        submit_fn: Optional[Callable[[Job], str]] = None,
        group_id: Optional[str] = None,
        node_id: Optional[str] = None,
        node_name: str = "",

    ):
        """Recursively walk the job tree and submit jobs."""
        submit_fn = submit_fn if submit_fn is not None else self._submit_job
        subgroup_id = f"{random.randint(100000, 999999)}"
        group_id = subgroup_id if group_id is None else f"{group_id}-{subgroup_id}"

        # Base case (single leaf)
        if isinstance(node, PJob):
            # Leaf node
            # generate rand job id int
            job_id = f"{random.randint(100000, 999999)}"
            job = Job(
                id=job_id,
                command=node.command,
                preamble=preamble_map.get(node.preamble, ""),
                node_id=node_id,
                node_name=node_name,
                parents=[str(_id) for _id in depends_on],

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
            node_id = (
                f"{random.randint(100000, 999999)}" if node_id is None else node_id
            )
            # Iterate over the combinations
            for i, params in enumerate(combinations):
                job_id = f"{random.randint(100000, 999999)}"
                cmd = cmd_template.format(**params, group_id=group_id)
                job = Job(
                    id=job_id,
                    command=cmd,
                    preamble=preamble_map.get(node.preamble, ""),
                    parents=[str(_id) for _id in depends_on],
                    node_id=node_id,
                    node_name=node_name,

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
                    [p for p in [copy.deepcopy(node_name), entry.name] if p]
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
                    node_name=group_name_i,
                )
                if job_ids:
                    depends_on = copy.deepcopy(job_ids)
            return job_ids

        elif node.type == "parallel":
            # Parallel group
            parallel_job_ids = []
            node_id = (
                f"{random.randint(100000, 999999)}" if node_id is None else node_id
            )
            for entry in node.jobs:
                group_name_i = ":".join(
                    [p for p in [copy.deepcopy(node_name), entry.name] if p]
                )
                job_ids = self.walk(
                    entry,
                    debug=debug,
                    preamble_map=preamble_map,
                    depends_on=copy.deepcopy(depends_on),
                    submitted_jobs=submitted_jobs,
                    submit_fn=submit_fn,
                    group_id=copy.deepcopy(group_id),
                    node_name=group_name_i,
                    node_id=node_id,
                )
                if job_ids:
                    parallel_job_ids.extend(job_ids)
            return parallel_job_ids

        elif node.type == "loop":
            # Sequential group
            sequential_job_ids = []
            node_id = (
                f"{random.randint(100000, 999999)}" if node_id is None else node_id
            )
            for t in range(node.loop_count):
                for i, entry in enumerate(node.jobs):
                    group_name_i = ":".join(
                        [p for p in [copy.deepcopy(node_name), entry.name] if p]
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
                        node_name=group_name_i,
                        node_id=node_id,
                    )
                    if job_ids:
                        # depends_on.extend(job_ids)
                        sequential_job_ids.extend(job_ids)
                        depends_on = copy.deepcopy(job_ids)
            return sequential_job_ids[-1:] or sequential_job_ids 

        return submitted_jobs

    def sbatch(self, args: list):
        raise NotImplementedError("The sbatch method is not implemented")
        # # Call sbatch with the provided arguments
        # result = subprocess.run(
        #     ["sbatch"] + args, check=True, capture_output=True, text=True
        # ).stdout.strip()
        # job_id = self._parse_job_id(result)
        # self.insert_record(
        #     Job(
        #         job_id=job_id,
        #         group_name="sbatch",
        #         command=" ".join(args),
        #         preamble="",
        #         depends_on=[],
        #     )
        # )
