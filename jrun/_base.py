import datetime
import json
import os
import sqlite3
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from jrun.interfaces import JobSpec, PGroup, PJob


class JobDB:
    """Track SLURM job status with support for complex job hierarchies."""

    def __init__(
        self,
        db_path: str = "~/.cache/jobrunner/jobs.db",
        deptype: Literal["afterok", "afterany"] = "afterok",
    ):
        """Initialize the job tracker.

        Args:
            db_path: Path to SQLite database for job tracking
        """
        self.db_path = os.path.expanduser(db_path)
        self.deptype: Literal["afterok", "afterany"] = deptype
        dir = os.path.dirname(self.db_path)
        if dir:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create jobs table if it doesn't exist
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            preamble TEXT NOT NULL,
            group_name TEXT NOT NULL,
            depends_on TEXT NOT NULL,  -- JSON text for list of job IDs
            slurm_log TEXT NOT NULL,
            slurm_err TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
            loop_id TEXT,
            inactive_deps TEXT NOT NULL DEFAULT '[]',  -- JSON text for inactive dependencies
        )
        """
        )

        conn.commit()
        conn.close()

    @staticmethod
    def _get_job_statuses(
        job_ids: list, on_add_status: Optional[Callable[[str], str]] = None
    ) -> Dict[str, str]:
        """Get the status of a list of job IDs."""

        def fmt_job_id(job_id: Union[str, int, float]):
            """Get the job ID as a string."""
            # Could be a NaN
            if isinstance(job_id, float) and job_id != job_id:
                return "NaN"
            else:
                return str(job_id)

        statuses = {}
        formatted_job_ids = [fmt_job_id(job_id) for job_id in job_ids]

        if not formatted_job_ids:
            return statuses

        try:
            # Get all job statuses and reasons in one call
            job_list = ",".join(formatted_job_ids)
            out = os.popen(
                f"squeue -j {job_list} --format='%i %T %r' --noheader"
            ).read()

            # Parse squeue output
            for line in out.strip().split("\n"):
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        job_id = parts[0]
                        status = parts[1]
                        reason = " ".join(parts[2:]) if len(parts) > 2 else ""

                        # Convert PENDING with DependencyNeverSatisfied to BLOCKED
                        if status == "PENDING" and "DependencyNeverSatisfied" in reason:
                            status = "BLOCKED"

                        statuses[job_id] = (
                            on_add_status(status) if on_add_status else status
                        )

            # For jobs not found in squeue (completed, failed, etc), fall back to sacct
            missing_jobs = set(formatted_job_ids) - set(statuses.keys())
            for job_id in missing_jobs:
                try:
                    out = os.popen(
                        f"sacct -j {job_id} --format state --noheader"
                    ).read()
                    status = out.strip().split("\n")[0].strip()
                    statuses[job_id] = (
                        on_add_status(status) if on_add_status else status
                    )
                except:
                    statuses[job_id] = "UNKNOWN"

        except:
            # Fallback to individual sacct calls if squeue fails
            for job_id in formatted_job_ids:
                try:
                    out = os.popen(
                        f"sacct -j {job_id} --format state --noheader"
                    ).read()
                    status = out.strip().split("\n")[0].strip()
                    statuses[job_id] = (
                        on_add_status(status) if on_add_status else status
                    )
                except:
                    statuses[job_id] = "UNKNOWN"

        return statuses

    def _parse_group_dict(self, d: Dict[str, Any]) -> PGroup:
        """Convert the `group` sub-dict into a PGroup (recursive)."""
        gtype = d["type"]
        sweep = d.get("sweep", {})
        preamble = d.get("preamble", "")
        sweep_template = d.get("sweep_template", "")
        children: List[Union[PGroup, PJob]] = []
        name = d.get("name", "")
        loop_count = d.get("loop_count", 1)

        for item in d.get("jobs", []):
            if "job" in item:  # leaf
                jd = item["job"]
                children.append(PJob(**jd))
            elif "group" in item:  # nested group
                children.append(self._parse_group_dict(item["group"]))
            else:
                raise ValueError(f"Unrecognized node: {item}")

        return PGroup(
            type=gtype,
            jobs=children,
            sweep=sweep,
            sweep_template=sweep_template,
            preamble=preamble,
            name=name,
            loop_count=loop_count,
        )

    @staticmethod
    def _parse_filter(filter_str: str) -> Tuple[str, Any]:
        """Parse filter like 'status=COMPLETED' or 'command~python'"""
        if "~" in filter_str:
            field, value = filter_str.split("~", 1)
            return f"{field} LIKE ?", f"%{value}%"
        elif "=" in filter_str:
            field, value = filter_str.split("=", 1)
            return f"{field} = ?", value
        else:
            raise ValueError(f"Invalid filter: {filter_str}")

    def insert_record(self, rec: JobSpec) -> None:
        """Insert a new job row (fails if job_id already exists)."""
        now = datetime.datetime.utcnow().isoformat(timespec="seconds")
        values = rec.to_dict()

        # Build the SQL dynamically
        columns = ", ".join(values.keys())
        placeholders = ", ".join(f":{k}" for k in values.keys())

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(f"INSERT INTO jobs ({columns}) VALUES ({placeholders})", values)
            conn.commit()

    def update_record(self, rec: JobSpec):
        pass

    def delete_record(self, job_id: Union[int, str]) -> None:
        """Delete a job record from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM jobs WHERE job_id = ?",
                (str(job_id),),
            )
            conn.commit()

    def get_job_by_id(self, job_id: int) -> JobSpec:
        """Get a job by its ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            row_dict = dict(row)
            row_dict["depends_on"] = json.loads(row_dict["depends_on"])
            return JobSpec(**row_dict)

        raise ValueError(f"Job with ID {job_id} not found in the database.")

    def get_job_by_command(self, command: str) -> Optional[JobSpec]:
        """Get a job by its command."""
        prev_jobs = self.get_jobs()
        for job in prev_jobs:
            if job.command == command:
                return job
        return None

    def get_jobs(
        self, filters: Optional[List[str]] = None, ignore_status: bool = False
    ) -> List[JobSpec]:
        """Get jobs with optional filters."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all job information
        query = "SELECT * FROM jobs"
        params = []

        # Remove status from filters
        status_filter = None
        if filters:
            conditions = []
            for f in filters:
                if f.startswith("status"):
                    status_filter = f
                    continue
                condition, param = self._parse_filter(f)
                conditions.append(condition)
                params.append(param)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at ASC"

        cursor.execute(query, params)
        jobs = cursor.fetchall()
        job_ids = [job["job_id"] for job in jobs]

        # Get job statuses from SLURM
        if not ignore_status:
            job_statuses = self._get_job_statuses(job_ids)
        else:
            job_statuses = {str(job["job_id"]): "UNKNOWN" for job in jobs}

        conn.close()

        # Filter out jobs based on status filter
        if status_filter:
            field, value = self._parse_filter(status_filter)
            jobs = [
                job
                for job in jobs
                if job_statuses.get(str(job["job_id"]), "UNKNOWN").lower()
                == value.lower()
            ]

        # Convert to JobSpec objects
        result = []
        for row in jobs:
            row_dict = dict(row)
            # Handle JSON fields
            row_dict["depends_on"] = json.loads(row_dict["depends_on"])
            row_dict["inactive_deps"] = json.loads(row_dict["inactive_deps"])
            # Override status with SLURM status if available
            row_dict["status"] = job_statuses.get(
                str(row_dict["job_id"]), row_dict["status"]
            )

            result.append(JobSpec(**row_dict))

        return result

    def update_depends_on(self, new_job_id: int, old_job_id: int) -> None:
        """Update all jobs that depend on old_job_id to depend on new_job_id instead."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all jobs with their dependencies
        cursor.execute("SELECT job_id, depends_on FROM jobs")
        jobs = cursor.fetchall()

        updated_count = 0
        now = datetime.datetime.utcnow().isoformat(timespec="seconds")

        for job_id, depends_on_json in jobs:
            # Parse the JSON list (handle empty/null case)
            depends_on = json.loads(depends_on_json) if depends_on_json else []

            # Check if this job depends on the old job ID
            old_job_str = str(old_job_id)
            new_job_str = str(new_job_id)

            if old_job_str in depends_on:
                # Replace old job ID with new job ID
                updated_depends_on = [
                    new_job_str if dep == old_job_str else dep for dep in depends_on
                ]

                # Update the database
                cursor.execute(
                    "UPDATE jobs SET depends_on = ?, updated_at = ? WHERE job_id = ?",
                    (json.dumps(updated_depends_on), now, job_id),
                )
                updated_count += 1
                print(f"Updated job {job_id}: dependency {old_job_id} -> {new_job_id}")

        conn.commit()
        conn.close()

        print(f"Updated dependencies for {updated_count} jobs")

    def get_children(self, job_id: int) -> List[JobSpec]:
        """Get all child jobs of a given job ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all jobs with their dependencies
        cursor.execute("SELECT job_id, depends_on FROM jobs")
        jobs = cursor.fetchall()

        child_jobs = []
        for job in jobs:
            if str(job_id) in json.loads(job[1]):
                child_jobs.append(self.get_job_by_id(job[0]))

        conn.close()
        return child_jobs
