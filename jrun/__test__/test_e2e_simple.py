#!/usr/bin/env python3
"""
Simple test for jrun package.
This script tests the basic functionality of jrun by submitting a simple job.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from jrun.job_submitter import JobSubmitter
from jrun.job_viewer import JobViewer


class TestJrunSimple(unittest.TestCase):
    """Simple test for jrun package."""

    def tearDown(self):
        # Remove temporary file
        if os.path.exists("test.yaml"):
            os.remove("test.yaml")

        # Remove database if created
        if os.path.exists("test.db"):
            os.remove("test.db")

    @patch("os.popen")
    def test_basic_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""
        # Setup mock to return job IDs
        mock_popen.side_effect = [
            MagicMock(read=MagicMock(return_value="Submitted batch job 12345")),
            MagicMock(read=MagicMock(return_value="Submitted batch job 12346")),
        ]
        viewer = JobViewer("test.db")
        submitter = JobSubmitter("test.db")
        root = {
            "group": {
                "name": "test-group",
                "type": "sequential",
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

        job_ids = submitter.walk(
            # node=root["group"],
            node=submitter._parse_group_dict(root["group"]),
            group_name=root["group"]["name"],
            preamble_map=preamble_map,
        )
        if not job_ids:
            raise RuntimeError("No job IDs returned from walk method.")

        # Verify submission
        self.assertEqual(len(job_ids), 2)
        self.assertTrue(any(12345 == value for value in job_ids))
        self.assertTrue(any(12346 == value for value in job_ids))

        # Verify the sbatch command was called twice
        self.assertEqual(mock_popen.call_count, 2)

        # Verify the first call had base preamble
        first_call_args = mock_popen.call_args_list[0][0][0]
        self.assertIn("sbatch", first_call_args)

        # Verify jobs are in the database
        jobs = viewer.list_jobs()
        job_ids_list = [job.job_id for job in jobs]
        self.assertIn("12345", job_ids_list)
        self.assertIn("12346", job_ids_list)

        # Verify second job depends on first job
        dependencies = jobs[1].depends_on
        self.assertIn("12345", dependencies)

        print("Test completed successfully!")

    @patch("os.popen")
    def test_nested_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""
        # Setup mock to return job IDs
        mock_popen.side_effect = [
            MagicMock(
                read=MagicMock(return_value="Submitted batch job 12345")
            ),  # parallel job 1
            MagicMock(
                read=MagicMock(return_value="Submitted batch job 12346")
            ),  # parallel job 2
            MagicMock(
                read=MagicMock(return_value="Submitted batch job 12347")
            ),  # parallel job 3
        ]
        viewer = JobViewer("test.db")
        submitter = JobSubmitter("test.db")
        root = {
            "group": {
                "name": "test-group-nested",
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "type": "parallel",
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
                    },
                    {
                        "job": {
                            "preamble": "gpu",
                            "command": "echo 'Third job'",
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

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            group_name=root["group"]["name"],
            preamble_map=preamble_map,
        )

        # Verify submission
        jobs = viewer.list_jobs()
        job_ids_list = [job.job_id for job in jobs]
        self.assertIn("12345", job_ids_list)
        self.assertIn("12346", job_ids_list)
        self.assertIn("12347", job_ids_list)

        # Verify dependencies
        self.assertIn("12345", jobs[2].depends_on)
        self.assertIn("12346", jobs[2].depends_on)


    @patch("os.popen")
    def test_sweep_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""
        # Setup mock to return job IDs
        mock_popen.side_effect = [
            MagicMock(
                read=MagicMock(return_value="Submitted batch job 22345")
            ),  
            MagicMock(
                read=MagicMock(return_value="Submitted batch job 22346")
            ),
            MagicMock(
                read=MagicMock(return_value="Submitted batch job 22347")
            ),
            MagicMock(
                read=MagicMock(return_value="Submitted batch job 22348")
            ),
        ]
        viewer = JobViewer("test.db")
        submitter = JobSubmitter("test.db")
        root = {
            "group": {
                "name": "test-group-nested",
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "type": "sweep",
                            "sweep": {
                                "param1": [1, 2],
                                "param2": ["a", "b"],
                            },
                            "sweep_template": "echo First job with param1={param1} and param2={param2}",
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

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            group_name=root["group"]["name"],
            preamble_map=preamble_map,
        )

        # Verify submission
        jobs = viewer.list_jobs()
        job_ids_list = [job.job_id for job in jobs]
        self.assertIn("22345", job_ids_list)
        self.assertIn("22346", job_ids_list)
        self.assertIn("22347", job_ids_list)
        self.assertIn("22347", job_ids_list)



if __name__ == "__main__":
    unittest.main()
