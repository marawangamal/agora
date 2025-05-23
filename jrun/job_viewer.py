from typing import List, Optional, Union
from tabulate import tabulate
from collections import Counter, defaultdict
from html import escape

from jrun._base import JobDB
from jrun.interfaces import JobSpec


class JobViewer(JobDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _group_jobs_by_children(self, jobs):
        """Group jobs that have the same set of children."""
        # Build dependency graph (parent -> children)
        children_map = defaultdict(set)
        for job in jobs:
            for dep in job.depends_on:
                children_map[dep].add(job.job_id)

        # Group jobs by their children sets
        children_to_jobs = defaultdict(list)
        for job in jobs:
            children = frozenset(children_map.get(job.job_id, set()))
            children_to_jobs[children].append(job)

        return children_to_jobs

    def _smart_range_display(self, job_ids_mixed: List[Union[int, str]]) -> str:
        """Create a smart range display that handles gaps."""
        job_ids = [int(job_id) for job_id in job_ids_mixed]
        job_ids = sorted(job_ids)

        if len(job_ids) == 1:
            return str(job_ids[0])
        elif len(job_ids) <= 3:
            return ",".join(map(str, job_ids))
        else:
            # Check if it's a continuous range
            is_continuous = all(
                job_ids[i] == job_ids[i - 1] + 1 for i in range(1, len(job_ids))
            )

            if is_continuous:
                return f"{job_ids[0]}-{job_ids[-1]}"
            else:
                # Has gaps - show first, last, and count
                return f"{job_ids[0]}...{job_ids[-1]} ({len(job_ids)} jobs)"

    def _get_footer(self, jobs: List[JobSpec]) -> str:
        status_counts = Counter(job.status for job in jobs)
        total = len(jobs)
        done = status_counts.get("COMPLETED", 0)
        failed = sum(status_counts[s] for s in ("FAILED", "CANCELLED", "TIMEOUT"))
        running = status_counts.get("RUNNING", 0)
        pending = status_counts.get("PENDING", 0)
        blocked = status_counts.get("BLOCKED", 0)
        pct = 100 * done / total
        return f"{done}/{total} ({pct:.1f}%) completed | {running} running | {pending} pending | {blocked} blocked | {failed} failed"

    def visualize(self, filters: Optional[List[str]] = None) -> None:
        """Display a compact dependency visualization."""
        jobs = self.get_jobs(filters=filters)

        if not jobs:
            print("No jobs found.")
            return

        border_width = 100
        print("=" * border_width)
        print("Job Dependencies:")
        print("=" * border_width)

        job_statuses = {job.job_id: job.status for job in jobs}

        for job in jobs:
            deps = " <- " + ", ".join(job.depends_on) if job.depends_on else ""
            cmd = job.command[:30] + "..." if len(job.command) > 30 else job.command
            status = job_statuses.get(str(job.job_id), "UNKNOWN")  # type: ignore
            status_color = self._get_status_color(status)
            print(
                f"{job.job_id} [{job.group_name}]: ({status_color}{status}\033[0m): {cmd}{deps}"
            )

        print("-" * border_width)
        print(self._get_footer(jobs))
        print("=" * border_width)

    def visualize_grouped(self, filters: Optional[List[str]] = None) -> None:
        """Display grouped job dependencies."""
        jobs = self.get_jobs(filters=filters)
        if not jobs:
            print("No jobs found.")
            return

        print("=" * 80 + "\nJob Dependencies:\n" + "=" * 80)

        for group in self._group_jobs_by_children(jobs).values():
            first_job = group[0]
            id_string = self._smart_range_display([j.job_id for j in group])

            # Simple status logic
            if len(group) == 1:
                status_color = self._get_status_color(first_job.status)
                status_text = f"{status_color}{first_job.status}\033[0m"
            else:
                counts = Counter(j.status for j in group)
                done = counts.get("COMPLETED", 0)
                total = len(group)

                # Show problems first, otherwise completion ratio
                for status in ["BLOCKED", "FAILED", "RUNNING"]:
                    if counts.get(status, 0) > 0:
                        status_color = self._get_status_color(status)
                        status_text = f"{status_color}{done}/{total}, {counts[status]} {status.lower()}\033[0m"
                        break
                else:
                    status_color = self._get_status_color(
                        "COMPLETED" if done == total else "PENDING"
                    )
                    status_text = f"{status_color}{done}/{total}\033[0m"

            # Print job line
            cmd = first_job.command[:25] + (
                "..." if len(first_job.command) > 25 else ""
            )
            deps = (
                f" <- {self._smart_range_display(first_job.depends_on)}"
                if first_job.depends_on
                else ""
            )
            print(
                f"{id_string} [{first_job.group_name or 'default'}]: ({status_text}): {cmd}{deps}"
            )

        # Summary
        counts = Counter(j.status for j in jobs)
        done = counts.get("COMPLETED", 0)
        total = len(jobs)
        pct = 100 * done // total if total else 0

        summary = [f"{done}/{total} ({pct}%)"]
        for status in ["RUNNING", "PENDING", "BLOCKED", "FAILED"]:
            if counts.get(status):
                summary.append(f"{counts[status]} {status.lower()}")

        print(f"{'-' * 80}\n{' | '.join(summary)}\n{'=' * 80}")

    def visualize_mermaid(self, filters: Optional[List[str]] = None) -> None:
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

        print(
            "\nPaste the code block above into https://mermaid.live (or any Markdown viewer with Mermaid support) to render the diagram."
        )

    def status(self, filters: Optional[List[str]] = None) -> None:
        """Display a simple job status table using tabulate."""
        jobs = self.get_jobs(filters=filters)
        if not jobs:
            print("No jobs found.")
            return
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

        border_width = 100
        print("-" * border_width)
        print(self._get_footer(jobs))
        print("=" * border_width)

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
