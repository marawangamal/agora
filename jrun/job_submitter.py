import copy
import itertools
import os
import random
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Union

import yaml
from jrun._base import JobDB
from jrun.interfaces import JobSpec, PGroup, PJob

JOB_RE = re.compile(r"Submitted batch job (\d+)")


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

    def _submit_jobspec(self, job_spec: JobSpec) -> int:
        """Submit a single job to SLURM and return the job ID.

        Args:
            job_spec: The job specification to submit
        Returns:
            The job ID as a string
        """
        # Create a temporary script file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            script_path = f.name
            f.write(job_spec.to_script())

        try:
            # Check if the job is already submitted
            prev_job = self.get_job_by_command(job_spec.command)
            if prev_job:
                if prev_job.status in ["PENDING", "RUNNING", "COMPLETED"]:
                    print(f"Job with command '{job_spec.command}' already submitted")
                    return prev_job.job_id
                else:
                    print(f"Job with command '{job_spec.command}' failed, resubmitting")
                    self.delete_record(prev_job)

            # Submit the job using sbatch
            result = os.popen(f"sbatch {script_path}").read()
            job_id = self._parse_job_id(result)
            job_spec.job_id = job_id
            self.insert_record(JobSpec(**job_spec.to_dict()))
            print(f"Submitted job with ID {job_id}")
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

    def submit(self, file: str, dry: bool = False):
        """Parse the YAML file and submit jobs."""
        cfg = yaml.safe_load(open(file))

        preamble_map = {
            name: "\n".join(lines) for name, lines in cfg["preambles"].items()
        }
        self.walk(
            node=self._parse_group_dict(cfg["group"]),
            preamble_map=preamble_map,
            dry=dry,
        )

    def walk(
        self,
        node: Union[PGroup, PJob],
        preamble_map: Dict[str, str],
        dry: bool = False,
        depends_on: List[int] = [],
        group_name: str = "",
        submitted_jobs: List[int] = [],
    ):
        """Recursively walk the job tree and submit jobs."""

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
            )
            if dry:
                print(f"DRY-RUN: {job.to_script()}")
            else:
                job_id = self._submit_jobspec(job)
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
                cmd = cmd_template.format(**params)
                job = JobSpec(
                    job_id=job_id,
                    group_name=group_name,
                    command=cmd,
                    preamble=preamble_map.get(node.preamble, ""),
                    depends_on=[str(_id) for _id in depends_on],
                )
                if dry:
                    print(f"DRY-RUN: {job.to_script()}")
                else:
                    job_id = self._submit_jobspec(job)
                submitted_jobs.append(job_id)
                job_ids.append(job_id)
            return job_ids

        # Recursive case:
        elif node.type == "sequential":
            # Sequential group
            for i, entry in enumerate(node.jobs):
                job_ids = self.walk(
                    entry,
                    dry=dry,
                    preamble_map=preamble_map,
                    # depends_on=depends_on,
                    # make a copy of depends_on
                    depends_on=copy.deepcopy(depends_on),
                    submitted_jobs=submitted_jobs,
                )
                if job_ids:
                    depends_on.extend(job_ids)
            return job_ids

        elif node.type == "parallel":
            # Parallel group
            parallel_job_ids = []
            for entry in node.jobs:
                job_ids = self.walk(
                    entry,
                    dry=dry,
                    preamble_map=preamble_map,
                    depends_on=copy.deepcopy(depends_on),
                    submitted_jobs=submitted_jobs,
                )
                if job_ids:
                    parallel_job_ids.extend(job_ids)
            return parallel_job_ids

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
