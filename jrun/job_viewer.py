import json
import sqlite3
from tabulate import tabulate
from typing import List

from jrun._base import JobDB
from jrun.interfaces import JobSpec


class JobViewer(JobDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def visualize(self):
        pass

    def status(self):
        """Display a simple job status table using tabulate."""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get basic job information
        cursor.execute(
            "SELECT job_id, group_name, command FROM jobs ORDER BY updated_at DESC"
        )
        jobs = cursor.fetchall()

        if not jobs:
            print("No jobs found.")
            conn.close()
            return

        # Get job statuses
        job_ids = [job[0] for job in jobs]
        job_statuses = self._get_job_statuses(job_ids)

        # Prepare table data
        table_data = []
        for job_id, group, cmd in jobs:
            # Truncate long commands
            if len(cmd) > 40:
                cmd = cmd[:37] + "..."

            # Get job status
            status = job_statuses.get(str(job_id), "UNKNOWN")

            # Add to table data
            table_data.append([job_id, group, cmd, status])

        # Print table using tabulate
        headers = ["ID", "GROUP", "COMMAND", "STATUS"]
        print("\n" + tabulate(table_data, headers=headers, tablefmt="simple"))

        conn.close()

    def list_jobs(self) -> List[JobSpec]:
        """List all jobs in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all jobs
        cursor.execute("SELECT * FROM jobs")
        jobs = cursor.fetchall()
        conn.close()

        return [
            JobSpec(
                job_id=row[0],
                command=row[1],
                preamble=row[2],
                group_name=row[3],
                depends_on=json.loads(
                    row[4] if row[4] else "[]"
                ),  # Convert JSON text to list
            )
            for row in jobs
        ]
