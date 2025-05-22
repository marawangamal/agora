import sqlite3
from tabulate import tabulate

from jrun._base import JobDB


class JobViewer(JobDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def visualize(self):
        """Display a compact dependency visualization."""
        jobs = self.get_jobs()

        if not jobs:
            print("No jobs found.")
            return

        print("\nJob Dependencies:")
        print("=" * 40)

        job_statuses = {job.job_id: job.status for job in jobs}

        for job in jobs:
            deps = " <- " + ", ".join(job.depends_on) if job.depends_on else ""
            cmd = job.command[:30] + "..." if len(job.command) > 30 else job.command
            status = job_statuses.get(str(job.job_id), "UNKNOWN")  # type: ignore
            status_color = self._get_status_color(status)
            print(
                f"{job.job_id} [{job.group_name}]: ({status_color}{status}\033[0m): {cmd}{deps}"
            )

    def visualize_mermaid(self):
        """Generate Mermaid diagram syntax for job dependencies."""
        jobs = self.get_jobs()

        if not jobs:
            print("No jobs found.")
            return

        print("\nMermaid Diagram:")
        print("=" * 40)
        print("graph TD")

        for job in jobs:
            # Create node with job info
            cmd = (
                job.command.replace('"', "'")[:20] + "..."
                if len(job.command) > 20
                else job.command.replace('"', "'")
            )
            print(f'    {job.job_id}["{job.job_id}<br/>{job.status}<br/>{cmd}"]')

            # Create edges for dependencies
            for dep in job.depends_on:
                print(f"    {dep} --> {job.job_id}")

        print("\nCopy the above to https://mermaid.live to visualize.")

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

    def _get_status_color(self, status: str) -> str:
        """Get ANSI color code for job status."""
        color_map = {
            "COMPLETED": "\033[92m",  # Green
            "RUNNING": "\033[94m",  # Blue
            "PENDING": "\033[93m",  # Yellow
            "FAILED": "\033[91m",  # Red
            "CANCELLED": "\033[95m",  # Magenta
            "TIMEOUT": "\033[91m",  # Red
        }
        return color_map.get(status, "\033[90m")  # Gray for unknown
