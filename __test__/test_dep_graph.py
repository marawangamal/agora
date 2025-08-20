#!/usr/bin/env python3
"""
Simple test for agora package.
This script tests the basic functionality of agora by submitting a simple job.
"""

import os
import re
import tempfile
from typing import Optional
import unittest
from unittest.mock import patch, MagicMock

from agora.interfaces import Job
from agora.job_submitter import JobSubmitter
from agora.job_viewer import JobViewer


class TestJrunSimple(unittest.TestCase):
    """Simple test for agora package."""

    # ------------------------------------------------------------------ #
    # set-up / tear-down                                                 #
    # ------------------------------------------------------------------ #
    def setUp(self):

        # Create a temporary database file
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Create commond preamble map
        self.preamble_map = {
            "base": "\n".join(
                [
                    "#!/bin/bash",
                    "#SBATCH --partition=debug",
                    "#SBATCH --output=test.out",
                    "#SBATCH --error=test.err",
                ]
            ),
            "gpu": "\n".join(
                [
                    "#SBATCH --gres=gpu:1",
                    "#SBATCH --mem=8G",
                ]
            ),
        }

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def get_popen_mock_fn(self):
        """Setup mocks for os.popen."""

        def mock_popen_func(command):
            # Only mock sbatch calls, let other calls through or return empty
            if "sbatch" in command:
                # Track how many sbatch calls we've made
                if not hasattr(mock_popen_func, "sbatch_count"):
                    mock_popen_func.sbatch_count = 0

                mock_popen_func.sbatch_count += 1
                if mock_popen_func.sbatch_count in [1, 2, 3, 4, 5, 6, 7, 8]:
                    return_value = {
                        1: "Submitted batch job 12345",
                        2: "Submitted batch job 12346",
                        3: "Submitted batch job 12347",
                        4: "Submitted batch job 12348",
                        5: "Submitted batch job 12349",
                        6: "Submitted batch job 12350",
                        7: "Submitted batch job 12351",
                        8: "Submitted batch job 12352",
                    }[mock_popen_func.sbatch_count]
                    return MagicMock(read=MagicMock(return_value=return_value))
                else:
                    return MagicMock(
                        read=MagicMock(return_value="Submitted batch job 99999")
                    )
            else:
                # For non-sbatch calls, return empty result
                return MagicMock(read=MagicMock(return_value=""))

        return mock_popen_func

    @patch("os.popen")
    def test_pll_root_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()

        ##### Setup test
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "test-group",
                "type": "parallel:root",
                "jobs": [
                    {
                        "job": {
                            "preamble": "base",
                            "command": "echo 'First job'",
                        }
                    },
                    {
                        "job": {
                            "preamble": "gpu",
                            "command": "echo 'Second job'",
                        }
                    },
                ],
            }
        }
        preamble_map = {
            "base": "\n".join(
                [
                    "#!/bin/bash",
                    "#SBATCH --partition=debug",
                    "#SBATCH --output=test-%j.out",
                    "#SBATCH --error=test-%j.err",
                ]
            ),
            "gpu": "\n".join(
                [
                    "#SBATCH --gres=gpu:1",
                    "#SBATCH --mem=8G",
                ]
            ),
        }

        ##### Submit jobs
        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        # Verify jobs are in the database
        jobs = submitter.get_jobs()
        assert jobs[0].node_id != jobs[1].node_id
        print("Test completed successfully!")


if __name__ == "__main__":
    unittest.main()
