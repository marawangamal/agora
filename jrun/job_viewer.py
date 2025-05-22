import json
import sqlite3
from tabulate import tabulate
from typing import List, Dict, Set
from collections import defaultdict, deque

from jrun._base import JobDB
from jrun.interfaces import JobSpec

from rich.console import Console
from rich.tree import Tree
class JobViewer(JobDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def visualize(self):
        """Simple Rich terminal visualization."""
        console = Console()
        jobs = self.get_jobs()
        
        if not jobs:
            console.print("No jobs found.", style="yellow")
            return
        
        # Status colors
        colors = {
            "COMPLETED": "green", "RUNNING": "blue", "PENDING": "yellow",
            "FAILED": "red", "CANCELLED": "magenta"
        }
        
        tree = Tree("🚀 Jobs", style="bold")
        
        for job in jobs:
            # Simple job display
            cmd = job.command[:40] + "..." if len(job.command) > 40 else job.command
            color = colors.get(getattr(job, 'status', 'UNKNOWN'), "dim")
            
            job_line = f"[bold]{job.job_id}[/bold] [{job.group_name}] [{color}]{getattr(job, 'status', 'UNKNOWN')}[/{color}]: {cmd}"
            
            if job.depends_on:
                job_line += f" (depends: {', '.join(job.depends_on)})"
                
            tree.add(job_line)
        
        console.print(tree)

    def visualize_v1(self):
        """Display a simple ASCII visualization of job dependencies."""
        jobs = self.get_jobs()
        
        if not jobs:
            print("No jobs found.")
            return
            
        # Get job statuses
        job_statuses = {job.job_id: job.status for job in jobs}
            
        # Build dependency graph
        job_map = {job.job_id: job for job in jobs}
        
        # Find root jobs (jobs with no dependencies)
        root_jobs = [job for job in jobs if not job.depends_on]
        
        if not root_jobs:
            print("No root jobs found (all jobs have dependencies - possible cycle?)")
            return
            
        print("\nJob Dependency Graph:")
        print("=" * 50)
        
        # Track visited jobs to avoid cycles
        visited = set()
        
        for root in root_jobs:
            self._print_job_tree(root, job_map, job_statuses, visited, level=0)  # <- This line needs job_statuses

    def _print_job_tree(
        self,
        job: JobSpec,
        job_map: Dict[str, JobSpec],
        job_statuses: Dict[str, str],
        visited: Set[str],
        level: int = 0,
    ):
        """Recursively print job tree with ASCII art."""

        if job.job_id in visited:
            return

        visited.add(job.job_id)

        # Create indentation
        indent = "  " * level
        if level > 0:
            indent = "  " * (level - 1) + "├─ "

        # Truncate long commands for readability
        cmd = job.command
        if len(cmd) > 30:
            cmd = cmd[:27] + "..."

        # Get job status
        status = job_statuses.get(str(job.job_id), "UNKNOWN")
        status_color = self._get_status_color(status)

        # Print job info with status
        print(
            f"{indent}Job {job.job_id} [{job.group_name}] ({status_color}{status}\033[0m): {cmd}"
        )

        # Find jobs that depend on this job
        dependent_jobs = [j for j in job_map.values() if job.job_id in j.depends_on]

        # Recursively print dependent jobs
        for dep_job in dependent_jobs:
            self._print_job_tree(dep_job, job_map, job_statuses, visited, level + 1)

    def visualize_compact(self):
        """Display a compact dependency visualization."""
        jobs = self.get_jobs()

        if not jobs:
            print("No jobs found.")
            return

        print("\nJob Dependencies (Compact View):")
        print("=" * 40)

        job_statuses = {job.job_id: job.status for job in jobs}

        for job in jobs:
            deps = " <- " + ", ".join(job.depends_on) if job.depends_on else ""
            cmd = job.command[:30] + "..." if len(job.command) > 30 else job.command
            status = job_statuses.get(str(job.job_id), "UNKNOWN")
            status_color = self._get_status_color(status)
            print(f"{job.job_id} [{job.group_name}]: ({status_color}{status}\033[0m): {cmd}{deps}")

    def visualize_mermaid(self):
        """Generate Mermaid diagram syntax for job dependencies."""
        jobs = self.get_jobs()

        if not jobs:
            print("No jobs found.")
            return

        print("\nMermaid Diagram (copy to mermaid.js editor):")
        print("=" * 50)
        print("graph TD")

        for job in jobs:
            # Create node with job info
            cmd = (
                job.command.replace('"', "'")[:20] + "..."
                if len(job.command) > 20
                else job.command.replace('"', "'")
            )
            print(f'    {job.job_id}["{job.job_id}<br/>{cmd}"]')

            # Create edges for dependencies
            for dep in job.depends_on:
                print(f"    {dep} --> {job.job_id}")

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
            "RUNNING": "\033[94m",    # Blue
            "PENDING": "\033[93m",    # Yellow
            "FAILED": "\033[91m",     # Red
            "CANCELLED": "\033[95m",  # Magenta
            "TIMEOUT": "\033[91m",    # Red
        }
        return color_map.get(status, "\033[90m")  # Gray for unknown