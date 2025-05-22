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

        jobs = self.get_jobs()
        table_data = []
        for job in jobs:
            table_data.append([job.job_id, job.group_name, job.command, job.status])

        # Print table using tabulate
        headers = ["ID", "GROUP", "COMMAND", "STATUS"]
        print("\n" + tabulate(table_data, headers=headers, tablefmt="simple"))

