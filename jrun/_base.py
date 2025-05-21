import datetime
import json
import os
import sqlite3
from typing import Any, Callable, Dict, List, Optional, Union

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

    def add_record(self, rec: JobSpec) -> None:
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

    def delete_record(self, rec: JobSpec):
        pass

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
        for job_id in [fmt_job_id(job_id) for job_id in job_ids]:
            try:
                out = os.popen("sacct -j {} --format state".format(job_id)).read()
                status = out.split("\n")[2].strip()
                statuses[job_id] = on_add_status(status) if on_add_status else status
            except:
                statuses[job_id] = "UNKNOWN"
        return statuses

    
    def _parse_group_dict(self, d: Dict[str, Any]) -> PGroup:
        """Convert the `group` sub-dict into a PGroup (recursive)."""
        gtype = d["type"]
        sweep = d.get("sweep", {})
        children: List[Union[PGroup, PJob]] = []

        for item in d.get("jobs", []):
            if "job" in item:                    # leaf
                jd = item["job"]
                children.append(PJob(**jd))
            elif "group" in item:                # nested group
                children.append(self._parse_group_dict(item["group"]))
            else:
                raise ValueError(f"Unrecognized node: {item}")

        return PGroup(type=gtype, jobs=children, sweep=sweep)
