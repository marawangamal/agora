import datetime
import json
import os
import sqlite3
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from jrun.interfaces import JobSpec, PGroup, PJob


class JobDB:
    """Track SLURM job status with support for complex job hierarchies."""

    def __init__(self, db_path: str = "~/.cache/jobrunner/jobs.db"):
        """Initialize the job tracker.

        Args:
            db_path: Path to SQLite database for job tracking
        """
        self.db_path = os.path.expanduser(db_path)
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
            depends_on TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
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
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO jobs (
                    job_id, command, preamble, group_name,
                    depends_on, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(rec.job_id),
                    rec.command,
                    rec.preamble,
                    rec.group_name,
                    json.dumps(rec.depends_on),  # store list as JSON text
                    # inverse: json.loads(rec.depends_on),
                    now,
                    now,
                ),
            )
            conn.commit()

    def update_record(self, rec: JobSpec):
        pass

    def delete_record(self, rec: JobSpec) -> None:
        """Delete a job record from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM jobs WHERE job_id = ?",
                (str(rec.job_id),),
            )
            conn.commit()

    def get_job_by_id(self, job_id: int) -> JobSpec:
        """Get a job by its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get job information
        cursor.execute(
            "SELECT job_id, command, preamble, group_name, depends_on FROM jobs WHERE job_id = ?",
            (job_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return JobSpec(
                job_id=row[0],
                command=row[1],
                preamble=row[2],
                group_name=row[3],
                depends_on=json.loads(row[4]),
            )
        raise ValueError(f"Job with ID {job_id} not found in the database.")

    def get_job_by_command(self, command: str) -> Optional[JobSpec]:
        """Get a job by its command."""
        prev_jobs = self.get_jobs()
        for job in prev_jobs:
            if job.command == command:
                return job
        return None

    def get_jobs(self, filters: Optional[List[str]] = None) -> List[JobSpec]:
        """Get jobs with optional filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get basic job information
        query = "SELECT job_id, command, preamble, group_name, depends_on FROM jobs"
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
        job_ids = [job[0] for job in jobs]

        # Get job statuses from SLURM
        job_statuses = self._get_job_statuses(job_ids)

        conn.close()

        # Filter out jobs based on status filter
        if status_filter:
            field, value = self._parse_filter(status_filter)
            jobs = [
                job
                for job in jobs
                if job_statuses.get(str(job[0]), "UNKNOWN").lower() == value.lower()
            ]

        return [
            JobSpec(
                job_id=row[0],
                command=row[1],
                preamble=row[2],
                group_name=row[3],
                depends_on=json.loads(row[4]),
                status=job_statuses.get(str(row[0]), "UNKNOWN"),
            )
            for row in jobs
        ]

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
