from tabulate import tabulate
from collections import defaultdict
from html import escape

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

    def visualize_mermaid(self) -> None:
        jobs = self.get_jobs()
        if not jobs:
            print("No jobs found.")
            return

        icons = {
            "COMPLETED": "✅",
            "FAILED": "❌",
            "CANCELLED": "❌",
            "PENDING": "⏸️",
            "RUNNING": "▶️",
            "TIMEOUT": "⌛",
        }

        def short(cmd, n=50):
            cmd = cmd.replace('"', "'")
            return cmd[: n - 1] + "…" if len(cmd) > n else cmd

        print("```mermaid")
        print("stateDiagram-v2")

        # Nodes
        id_map = {}
        for job in jobs:
            sid = f"S{job.job_id}"  # IDs must not start with a digit
            id_map[job.job_id] = sid
            # NEW – no escape(), just swap double quotes for single quotes
            clean_cmd = short(job.command).replace('"', "'")
            label = (
                f"{icons.get(job.status,'?')} {job.job_id}<br/><code>{clean_cmd}</code>"
            )
            print(f'    state "{label}" as {sid}')

        # Edges
        for job in jobs:
            for dep in job.depends_on:
                if dep in id_map:
                    print(f"    {id_map[dep]} --> {id_map[job.job_id]}")

        print("```")
        print(
            "\nPaste the fenced block above into mermaid.live (or any Markdown viewer with Mermaid support) to render the diagram."
        )

    def status(self):
        """Display a simple job status table using tabulate."""
        jobs = self.get_jobs()
        table_data = []
        for job in jobs:
            table_data.append([job.job_id, job.group_name, job.command, job.status])

        # Print table using tabulate
        headers = ["ID", "GROUP", "COMMAND", "STATUS"]
        col_widths = [10, 10, 80, 10]
        # print("\n" + tabulate(table_data, headers=headers, tablefmt="simple"))
        print(
            "\n"
            + tabulate(
                table_data, headers=headers, tablefmt="grid", maxcolwidths=col_widths
            )
        )

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
