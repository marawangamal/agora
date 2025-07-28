from contextlib import contextmanager
import os
import os.path as osp
import re
import sqlite3
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from agora.interfaces import JobInsert, Job, PGroup, PJob


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
        conn.execute("PRAGMA foreign_keys = ON")

        # Create jobs table if it doesn't exist
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            preamble TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            node_id TEXT,
            node_name TEXT
        )
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS deps (
            parent TEXT NOT NULL,
            child TEXT NOT NULL,
            dep_type TEXT NOT NULL,
            FOREIGN KEY (parent) REFERENCES jobs(id) ON DELETE CASCADE ON UPDATE CASCADE, -- delete record if parent is deleted
            FOREIGN KEY (child) REFERENCES jobs(id) ON DELETE CASCADE ON UPDATE CASCADE, -- delete record if child is deleted
            UNIQUE (parent, child, dep_type)
        )
        """
        )

        cursor.execute(
            """
        CREATE VIEW IF NOT EXISTS vw_jobs AS
            SELECT
                j.*,
                (SELECT GROUP_CONCAT(d.child, ',') FROM deps d WHERE d.parent = j.id) AS children,
                (SELECT GROUP_CONCAT(d2.parent, ',') FROM deps d2 WHERE d2.child = j.id) AS parents
            FROM jobs j;
        """
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_job_states(job_ids: list) -> Dict[str, Dict[str, str]]:
        job_list = ",".join(str(j) for j in job_ids)
        output = os.popen(
            f"sacct -j {job_list} --format jobid,state,start,end,workdir --noheader --parsable2"
        ).read()
        job_states = {
            parts[0]: {
                "status": parts[1],
                "start": parts[2],
                "end": parts[3],
                "workdir": parts[4],
            }
            for line in output.strip().split("\n")
            if (parts := line.split("|")) and len(parts) >= 4
        }

        # Check if pending jobs are blocked
        for job_id, jstate in job_states.items():
            if jstate["status"] == "PENDING":
                pd_reason = (
                    os.popen(f"squeue -j {job_id} -o %R --noheader").read().strip()
                )
                if "DependencyNeverSatisfied".lower() in pd_reason.lower():
                    jstate["status"] = "BLOCKED"

        return job_states

    def _parse_group_dict(self, d: Dict[str, Any]) -> PGroup:
        """Convert the `group` sub-dict into a PGroup (recursive)."""
        gtype = d["type"]
        sweep = d.get("sweep", {})
        preamble = d.get("preamble", "")
        sweep_template = d.get("sweep_template", "")
        children: List[Union[PGroup, PJob]] = []
        name = d.get("name", "")
        loop_count = d.get("loop_count", 1)
        loop_type = d.get("loop_type", "sequential")

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
            loop_type=loop_type,
        )

    @staticmethod
    def _parse_filter(filter_str: str, param_name: str) -> Tuple[str, Any]:
        """Parse filter like 'status=COMPLETED' or 'command~python'"""
        if "~" in filter_str:
            field, value = filter_str.split("~", 1)
            return f"{field} LIKE :{param_name}", f"%{value}%"
        elif "=" in filter_str:
            field, value = filter_str.split("=", 1)
            return f"{field} = :{param_name}", value
        else:
            raise ValueError(f"Invalid filter: {filter_str}")

    def _parse_preamble(self, preamble: str, job_id: str) -> Tuple[str, str]:
        """Parse the preamble to extract SLURM output and error paths."""
        output_match = re.search(r"#SBATCH\s+--output[=\s]+(\S+)", preamble)
        error_match = re.search(r"#SBATCH\s+--error[=\s]+(\S+)", preamble)
        output_path = output_match.group(1) if output_match else ""
        error_path = error_match.group(1) if error_match else ""
        for spec in ["%j", "%J"]:
            if spec in output_path:
                output_path = output_path.replace(spec, job_id)
            if spec in error_path:
                error_path = error_path.replace(spec, job_id)
        return output_path, error_path

    @contextmanager
    def get_connection(self):
        """Get a database connection context manager with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()  # Auto-commit on success
        except Exception:
            conn.rollback()  # Rollback on error
            raise
        finally:
            conn.close()  # Always close

    def _run_query(
        self, query: str, params: Optional[Dict] = None
    ) -> List[sqlite3.Row]:
        """Execute a SELECT query that returns data."""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)  # Named parameters
            return cursor.fetchall()

    def _execute_query(self, query: str, params: Optional[Dict] = None) -> None:
        """Execute an INSERT/UPDATE/DELETE query that doesn't return data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)  # Named parameters

    ############################################################################
    #                                CRUD operations (jobs)                    #
    ############################################################################

    def create_job(self, rec: JobInsert) -> None:
        """Insert a new job row (fails if job_id already exists)."""
        job_dict = rec.to_dict()
        attrs_str = ", ".join(job_dict.keys())
        vals_str = ", ".join(f":{k}" for k in job_dict.keys())
        query = f"INSERT INTO jobs ({attrs_str}) VALUES ({vals_str})"
        try:
            self._execute_query(query, job_dict)
        except sqlite3.IntegrityError as e:
            print(f"Failed to execute query: {query} with params {job_dict}")
            raise e

    def delete_job(
        self,
        job_id: str,
        cascade: bool = True,
        on_delete: Optional[Callable[[str], None]] = None,
    ) -> None:

        jobs = self.get_jobs([f"id={job_id}"], ignore_status=True)
        job = jobs[0] if jobs else None
        if not job:
            print(f"Job {job_id} not found, nothing to delete.")
            return

        # Delete job from db
        self._execute_query("DELETE FROM jobs WHERE id = :job_id", {"job_id": job_id})
        on_delete(job_id) if on_delete else None

        if cascade:
            for child_id in job.children:
                self.delete_job(child_id, cascade=True)

    def update_job(self, job_id: str, job: JobInsert) -> None:
        """Update job fields. Only updates fields that are provided."""
        job_dict = job.to_dict()
        set_clause = ", ".join(f"{k} = :{k}" for k in job_dict.keys())
        query = f"UPDATE jobs SET {set_clause}, updated_at = datetime('now') WHERE id = :old_id"
        params = {**job_dict, "old_id": job_id}
        self._execute_query(query, params)

    def get_jobs(
        self, filters: Optional[List[str]] = None, ignore_status: bool = False
    ) -> List[Job]:
        query = "SELECT * FROM vw_jobs"
        params = {}

        # Remove status from filters
        status_filter = None
        if filters:
            conditions = []
            param_counter = 0
            for f in filters:
                if f.startswith("status"):
                    status_filter = f
                    continue

                param_name = f"param_{param_counter}"
                condition, param_value = self._parse_filter(f, param_name)
                conditions.append(condition)
                params[param_name] = param_value
                param_counter += 1

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at ASC"
        jobs = self._run_query(query, params)
        job_ids = [job[0] for job in jobs]

        # Get job statuses from SLURM
        job_states = {
            str(job["id"]): {"status": "UNKNOWN", "start": None, "end": None}
            for job in jobs
        }
        if not ignore_status:
            job_states = self.get_job_states(job_ids)

        # Filter out jobs based on status filter
        if status_filter:
            _, value = self._parse_filter(status_filter, "status")
            jobs = [
                job
                for job in jobs
                if job_states.get(job["id"], {}).get("status", "UNKNOWN").lower()
                == value.lower()
            ]

        # Convert to JobSpec objects
        result = []
        for row in jobs:
            row_dict = dict(row)
            row_dict["parents"] = (
                row_dict["parents"].split(",") if row_dict["parents"] else []
            )
            row_dict["children"] = (
                row_dict["children"].split(",") if row_dict["children"] else []
            )
            row_dict["status"] = job_states.get(row_dict["id"], {}).get(
                "status", "UNKNOWN"
            )
            row_dict["start_time"] = job_states.get(row_dict["id"], {}).get(
                "start", None
            )
            row_dict["end_time"] = job_states.get(row_dict["id"], {}).get("end", None)
            out_path, err_path = self._parse_preamble(
                row_dict.get("preamble", ""), row_dict["id"]
            )
            row_dict["slurm_out"] = (
                osp.join(
                    job_states.get(row_dict["id"], {}).get("workdir", ""), out_path
                )
                if out_path
                else None
            )
            row_dict["slurm_err"] = (
                osp.join(
                    job_states.get(row_dict["id"], {}).get("workdir", ""), err_path
                )
                if err_path
                else None
            )
            result.append(Job(**row_dict))

        return result

    ############################################################################
    #                                CRUD operations (deps)                    #
    ############################################################################

    def upsert_deps(
        self,
        child_id: str,
        parent_ids: List[str],
        dep_type: Literal["afterok", "afterany"] = "afterok",
    ) -> None:
        """Update dependencies for a job."""

        # Delete existing dependencies for this child
        self._execute_query(
            "DELETE FROM deps WHERE child = :child_id", {"child_id": child_id}
        )

        # Insert new dependencies
        for parent_id in parent_ids:
            self._execute_query(
                "INSERT OR IGNORE INTO deps (parent, child, dep_type) VALUES (:parent_id, :child_id, :dep_type)",
                {"parent_id": parent_id, "child_id": child_id, "dep_type": dep_type},
            )
