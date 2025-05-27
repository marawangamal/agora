import json
from typing import Dict, List, Literal, Optional, Tuple, Union
from tabulate import tabulate
from collections import Counter, defaultdict
from html import escape

from jrun._base import JobDB
from jrun.interfaces import JobSpec

SABBRV = {
    "COMPLETED": "✅",
    "FAILED": "❌",
    "CANCELLED": "❌",
    "PENDING": "⏸️",
    "RUNNING": "▶️",
    "TIMEOUT": "⌛",
    "BLOCKED": "⛔",
}


class JobViewer(JobDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _group_jobs(
        self, jobs: List[JobSpec]
    ) -> Dict[Tuple[frozenset, frozenset], List[JobSpec]]:
        """Group jobs that have the same parents and children."""
        # Build dependency graph (parent -> children)
        parent_to_child_map = defaultdict(set)
        for job in jobs:
            for dep in job.depends_on:
                parent_to_child_map[dep].add(job.job_id)

        # Group jobs by their full dependency signature
        groups = defaultdict(list)
        for job in jobs:
            parents = frozenset(job.depends_on)
            children = frozenset(parent_to_child_map.get(job.job_id, set()))
            groups[(parents, children)].append(job)

        return groups

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
                return f"{job_ids[0]}-{job_ids[-1]} ({len(job_ids)})"
            else:
                # Has gaps - show first, last, and count
                return f"{job_ids[0]}...{job_ids[-1]} ({len(job_ids)})"

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

    def _get_status_totals(self, jobs: List[JobSpec]):
        status_counts = Counter(job.status for job in jobs)
        total = len(jobs)
        done = status_counts.get("COMPLETED", 0)
        failed = sum(status_counts[s] for s in ("FAILED", "CANCELLED", "TIMEOUT"))
        running = status_counts.get("RUNNING", 0)
        pending = status_counts.get("PENDING", 0)
        blocked = status_counts.get("BLOCKED", 0)
        cancelled = status_counts.get("CANCELLED", 0)
        timeout = status_counts.get("TIMEOUT", 0)
        return {
            "completed": done,
            "running": running,
            "pending": pending,
            "blocked": blocked,
            "cancelled": cancelled,
            "timeout": timeout,
            "failed": failed,
            "total": total,
        }

    def _get_footer(self, jobs: List[JobSpec]) -> str:
        """Generate a footer with job status summary."""
        status = self._get_status_totals(jobs)
        finished = sum(
            status[k] for k in status.keys() if k not in ["running", "pending", "total"]
        )
        status_str = (
            f"{finished}/{status['total']} ({100 * finished // status['total']:.1f}%) "
            + " | ".join(
                f"{status[k]} {k.lower()}"
                for k in ["completed", "running", "pending", "blocked", "failed"]
                if status[k]
            )
        )
        return status_str

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

        headers = [
            "IDS",
            "GROUP",
            "PASS (PROG)",
            "C",
            "R",
            "PD",
            "F",
            "B",
            "COMMAND",
            "DEPENDENCIES",
        ]
        table_data = []
        col_widths = [40, 10] + [20] * 6 + [80, 80]
        for group in self._group_jobs(jobs).values():
            id = self._smart_range_display([j.job_id for j in group])
            group_name = group[0].group_name or "root"
            status = self._get_status_totals(group)
            finished = sum(
                status[k]
                for k in status.keys()
                if k not in ["running", "pending", "total"]
            )
            stat_arr = [
                (
                    f'{status["completed"]:>2}/{status["total"]:<2} '
                    f'({int(finished/status["total"]*100):>3}%) '
                )
            ] + [
                status[k]
                for k in ["completed", "running", "pending", "failed", "blocked"]
            ]

            cmd = group[0].command[:25] + ("..." if len(group[0].command) > 25 else "")
            deps = self._smart_range_display(
                group[0].depends_on  # type:ignore
            )  #  (i.e., parents)
            table_data.append([id, group_name, *stat_arr, cmd, deps])

        # Print table using tabulate
        table_str = tabulate(
            table_data,
            headers=headers,
            maxcolwidths=col_widths,
        )

        # Calculate actual table width from the first line (header border)
        table_lines = [line for line in table_str.split("\n") if line.strip()]
        table_width = max(len(line) for line in table_lines) if table_lines else 80

        # Print table
        print("\n" + table_str)
        print("-" * table_width)
        print(self._get_footer(jobs))

    def visualize_mermaid(self, filters: Optional[List[str]] = None) -> None:
        jobs = self.get_jobs(filters)
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

    def visualize_json(self, filters: Optional[List[str]] = None) -> None:
        """Return job data as JSON for API consumption."""
        jobs = self.get_jobs(filters=filters, ignore_status=True)

        # Convert JobSpec objects to dictionaries
        jobs_data = []
        for job in jobs:
            jobs_data.append(
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "command": job.command,
                    "group_name": job.group_name,
                    "depends_on": job.depends_on,
                    "preamble": job.preamble,
                    "loop_id": job.loop_id,
                }
            )

        # Add summary stats
        stats = self._get_status_totals(jobs)

        output = {"jobs": jobs_data, "stats": stats, "count": len(jobs_data)}

        print(json.dumps(output, indent=2))

    def status(self, filters: Optional[List[str]] = None) -> None:
        """Display a simple job status table using tabulate."""
        jobs = self.get_jobs(filters=filters)
        if not jobs:
            print("No jobs found.")
            return
        table_data = []
        for job in jobs:
            table_data.append(
                [
                    job.job_id,
                    job.group_name,
                    job.loop_id or "N/A",
                    job.command,
                    job.status,
                ]
            )

        # Print table using tabulate
        headers = ["ID", "GROUP", "LOOP" "COMMAND", "STATUS"]
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
