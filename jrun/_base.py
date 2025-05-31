
import os
import os.path as osp
import re
import sqlite3
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from jrun.interfaces import JobInsert, Job, PGroup, PJob


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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            preamble TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            node_id TEXT,
            node_name TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS deps (
            parent TEXT NOT NULL,
            child TEXT NOT NULL,
            dep_type TEXT NOT NULL,
            FOREIGN KEY (parent) REFERENCES jobs(job_id) ON DELETE CASCADE ON UPDATE CASCADE, -- delete record if parent is deleted
            FOREIGN KEY (child) REFERENCES jobs(job_id) ON DELETE CASCADE ON UPDATE CASCADE, -- delete record if child is deleted
            UNIQUE (parent, child, dep_type)
        )
        """)

        cursor.execute("""
        CREATE VIEW IF NOT EXISTS vw_jobs AS
            SELECT
                j.*,
                (SELECT GROUP_CONCAT(d.child, ',') FROM deps d WHERE d.parent = j.id) AS children,
                (SELECT GROUP_CONCAT(d2.parent, ',') FROM deps d2 WHERE d2.child = j.id) AS parents
            FROM jobs j;
        """)
        conn.commit()
        conn.close()

    # @staticmethod
    # def _get_job_statuses(
    #     job_ids: list, on_add_status: Optional[Callable[[str], str]] = None
    # ) -> Dict[str, str]:
    #     """Get the status of a list of job IDs."""

    #     def fmt_job_id(job_id: Union[str, int, float]):
    #         """Get the job ID as a string."""
    #         # Could be a NaN
    #         if isinstance(job_id, float) and job_id != job_id:
    #             return "NaN"
    #         else:
    #             return str(job_id)

    #     statuses = {}
    #     formatted_job_ids = [fmt_job_id(job_id) for job_id in job_ids]

    #     if not formatted_job_ids:
    #         return statuses

    #     try:
    #         # Get all job statuses and reasons in one call
    #         job_list = ",".join(formatted_job_ids)
    #         out = os.popen(
    #             f"squeue -j {job_list} --format='%i %T %r' --noheader"
    #         ).read()

    #         # Parse squeue output
    #         for line in out.strip().split("\n"):
    #             if line.strip():
    #                 parts = line.strip().split()
    #                 if len(parts) >= 2:
    #                     job_id = parts[0]
    #                     status = parts[1]
    #                     reason = " ".join(parts[2:]) if len(parts) > 2 else ""

    #                     # Convert PENDING with DependencyNeverSatisfied to BLOCKED
    #                     if status == "PENDING" and "DependencyNeverSatisfied" in reason:
    #                         status = "BLOCKED"

    #                     statuses[job_id] = (
    #                         on_add_status(status) if on_add_status else status
    #                     )

    #         # For jobs not found in squeue (completed, failed, etc), fall back to sacct
    #         missing_jobs = set(formatted_job_ids) - set(statuses.keys())
    #         for job_id in missing_jobs:
    #             try:
    #                 out = os.popen(
    #                     f"sacct -j {job_id} --format state --noheader"
    #                 ).read()
    #                 status = out.strip().split("\n")[0].strip()
    #                 statuses[job_id] = (
    #                     on_add_status(status) if on_add_status else status
    #                 )
    #             except:
    #                 statuses[job_id] = "UNKNOWN"

    #     except:
    #         # Fallback to individual sacct calls if squeue fails
    #         for job_id in formatted_job_ids:
    #             try:
    #                 out = os.popen(
    #                     f"sacct -j {job_id} --format state --noheader"
    #                 ).read()
    #                 status = out.strip().split("\n")[0].strip()
    #                 statuses[job_id] = (
    #                     on_add_status(status) if on_add_status else status
    #                 )
    #             except:
    #                 statuses[job_id] = "UNKNOWN"

    #     return statuses

    @staticmethod
    def _get_job_state(job_ids: list) -> Dict[str, Dict[str, str]]:
        job_list = ",".join(str(j) for j in job_ids)
        output = os.popen(f"sacct -j {job_list} --format jobid,state,start,end,workdir --noheader --parsable2").read()
        return {parts[0]: {"status": parts[1], "start": parts[2], "end": parts[3], "workdir": parts[4]}
                for line in output.strip().split("\n") if (parts := line.split("|")) and len(parts) >= 4}


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


    def _parse_preamble(self, preamble: str, job_id:str) -> Tuple[str, str]:
        """Parse the preamble to extract SLURM output and error paths."""
        output_match = re.search(r'#SBATCH\s+--output[=\s]+(\S+)', preamble)
        error_match = re.search(r'#SBATCH\s+--error[=\s]+(\S+)', preamble)
        output_path = output_match.group(1) if output_match else ""
        error_path = error_match.group(1) if error_match else ""
        for spec in ["%j", "%J"]:
            if spec in output_path:
                output_path = output_path.replace(spec, job_id)
            if spec in error_path:
                error_path = error_path.replace(spec, job_id)
        return output_path, error_path


    def _run_query(self, query: str, params: List[Any] = []) -> List[sqlite3.Row]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows


    ############################################################################
    #                                CRUD operations (jobs)                    #
    ############################################################################

    def create_job(self, rec: JobInsert) -> None:
        """Insert a new job row (fails if job_id already exists)."""
        values = rec.to_dict()
        columns = ", ".join(values.keys())
        placeholders = ", ".join(f":{k}" for k in values.keys())

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(f"INSERT INTO jobs ({columns}) VALUES ({placeholders})", values)
            conn.commit()

    def delete_job(self, job_id: str, cascade: bool = True, on_delete: Optional[Callable[[str], None]] = None) -> None:

        jobs = self.get_jobs([f"id={job_id}"], ignore_status=True)
        job = jobs[0] if jobs else None
        if not job:
            print(f"Job {job_id} not found, nothing to delete.")
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM jobs WHERE id = ?",
                (str(job_id),),
            )
            conn.commit()
            on_delete(job_id) if on_delete else None

        if cascade:
            for child_id in job.children:
                self.delete_job(child_id, cascade=True)

    def update_job(self, job_id: str, job: JobInsert) -> None:
        """Update job fields. Only updates fields that are provided."""
        set_clause = ", ".join(f"{k} = ?" for k in job.to_dict().keys())
        params = list(job.to_dict().values()) + [job_id]

        query = f"UPDATE jobs SET {set_clause}, updated_at = datetime('now') WHERE id = ?"

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()

    def get_jobs(
        self, filters: Optional[List[str]] = None, ignore_status: bool = False
    ) -> List[Job]:
        """Get jobs with optional filters."""
        query = "SELECT * FROM vw_jobs"
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
        jobs = self._run_query(query, params)
        job_ids = [job[0] for job in jobs]

        # Get job statuses from SLURM
        job_states = {str(job['id']): {"status": "UNKNOWN", "start": None, "end": None} for job in jobs}
        if not ignore_status:
            job_states = self._get_job_state(job_ids)


        # Filter out jobs based on status filter
        if status_filter:
            field, value = self._parse_filter(status_filter)
            jobs = [
                job
                for job in jobs
                if job_states.get(job['id'], {}).get('status', 'UNKNOWN').lower() == value.lower()
            ]

        # Convert to JobSpec objects
        result = []
        for row in jobs:
            row_dict = dict(row)
            row_dict["parents"] = row_dict["parents"].split(',') if row_dict["parents"] else []
            row_dict["children"] = row_dict["children"].split(',') if row_dict["children"] else []
            row_dict["status"] = job_states.get(row_dict["id"], {}).get("status", "UNKNOWN")
            row_dict["start_time"] = job_states.get(row_dict["id"], {}).get("start", None)
            row_dict["end_time"] = job_states.get(row_dict["id"], {}).get("end", None)
            out_path, err_path = self._parse_preamble(row_dict.get("preamble", ""), row_dict["id"])
            row_dict["slurm_out"] = osp.join(job_states.get(row_dict["id"], {}).get("workdir", ""), out_path) if out_path else None
            row_dict["slurm_err"] = osp.join(job_states.get(row_dict["id"], {}).get("workdir", ""), err_path) if err_path else None

            print(f"Job {row_dict['id']} - Slurm Out: {row_dict['slurm_out']}, Slurm Err: {row_dict['slurm_err']}")

            result.append(Job(**row_dict))

        return result


    ############################################################################
    #                                CRUD operations (deps)                    #
    ############################################################################


    def upsert_deps(self, child_id: str, parent_ids: List[str], dep_type: Literal["afterok", "afterany"] = "afterok") -> None:
        """Update dependencies for a job."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            # Delete existing dependencies for this child
            cur.execute(
                "DELETE FROM deps WHERE child = ?",
                (child_id,),
            )

            # Insert new dependencies
            for parent_id in parent_ids:
                cur.execute(
                    "INSERT OR IGNORE INTO deps (parent, child, dep_type) VALUES (?, ?, ?)",
                    (parent_id, child_id, dep_type),
                )
            conn.commit()


    # def update_depends_on(self, new_job_id: int, old_job_id: int) -> None:
    #     """Update all jobs that depend on old_job_id to depend on new_job_id instead."""
    #     conn = sqlite3.connect(self.db_path)
    #     cursor = conn.cursor()

    #     # Get all jobs with their dependencies
    #     cursor.execute("SELECT job_id, depends_on FROM jobs")
    #     jobs = cursor.fetchall()

    #     updated_count = 0
    #     now = datetime.datetime.utcnow().isoformat(timespec="seconds")

    #     for job_id, depends_on_json in jobs:
    #         # Parse the JSON list (handle empty/null case)
    #         depends_on = json.loads(depends_on_json) if depends_on_json else []

    #         # Check if this job depends on the old job ID
    #         old_job_str = str(old_job_id)
    #         new_job_str = str(new_job_id)

    #         if old_job_str in depends_on:
    #             # Replace old job ID with new job ID
    #             updated_depends_on = [
    #                 new_job_str if dep == old_job_str else dep for dep in depends_on
    #             ]

    #             # Update the database
    #             cursor.execute(
    #                 "UPDATE jobs SET depends_on = ?, updated_at = ? WHERE job_id = ?",
    #                 (json.dumps(updated_depends_on), now, job_id),
    #             )
    #             updated_count += 1
    #             print(f"Updated job {job_id}: dependency {old_job_id} -> {new_job_id}")

    #     conn.commit()
    #     conn.close()

    #     print(f"Updated dependencies for {updated_count} jobs")

