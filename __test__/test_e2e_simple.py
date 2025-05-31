#!/usr/bin/env python3
"""
Simple test for jrun package.
This script tests the basic functionality of jrun by submitting a simple job.
"""

import os
import re
import tempfile
from typing import Optional
import unittest
from unittest.mock import patch, MagicMock

from jrun.interfaces import Job
from jrun.job_submitter import JobSubmitter
from jrun.job_viewer import JobViewer


class TestJrunSimple(unittest.TestCase):
    """Simple test for jrun package."""

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
                if mock_popen_func.sbatch_count in [1, 2, 3, 4]:
                    return_value = {
                        1: "Submitted batch job 12345",
                        2: "Submitted batch job 12346",
                        3: "Submitted batch job 12347",
                        4: "Submitted batch job 12348",
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
    def test_basic_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()

        ##### Setup test
        submitter = JobSubmitter(self.db_path)
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
        self.assertEqual(len(jobs), 2)
        job_ids_list = [job.id for job in jobs]
        self.assertIn("12345", job_ids_list)
        self.assertIn("12346", job_ids_list)

        # Verify second job depends on first job
        self.assertIn("12345", jobs[1].parents)

        print("Test completed successfully!")

    @patch("os.popen")
    def test_nested_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()

        ##### Setup test
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
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

        ##### Submit jobs
        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        ##### Run tests
        # Verify submission
        jobs = viewer.get_jobs()
        job_ids_list = [job.id for job in jobs]
        self.assertIn("12345", job_ids_list)
        self.assertIn("12346", job_ids_list)
        self.assertIn("12347", job_ids_list)

        # Verify dependencies
        self.assertIn("12345", jobs[2].parents)
        self.assertIn("12346", jobs[2].parents)

    @patch("os.popen")
    def test_sweep_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
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
            node_name=root["group"]["name"],
            preamble_map=preamble_map,
        )

        # Verify submission
        jobs = viewer.get_jobs()
        job_ids_list = [job.id for job in jobs]
        self.assertIn("12345", job_ids_list)
        self.assertIn("12346", job_ids_list)
        self.assertIn("12347", job_ids_list)
        self.assertIn("12348", job_ids_list)

    @patch("os.popen")
    def test_nested_seqs_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "test-group-nested",
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "type": "sequential",
                            "jobs": [
                                {
                                    "job": {
                                        "preamble": "base",
                                        "command": "echo 'First job'",
                                    }
                                }
                            ],
                        },
                    },
                    {
                        "group": {
                            "type": "sequential",
                            "jobs": [
                                {
                                    "job": {
                                        "preamble": "base",
                                        "command": "echo 'Second job'",
                                    },
                                },
                                {
                                    "job": {
                                        "preamble": "base",
                                        "command": "echo 'Third job'",
                                    },
                                },
                            ],
                        },
                    },
                ],
            }
        }

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        # Verify submission
        jobs = viewer.get_jobs()
        job_ids_list = [job.id for job in jobs]
        self.assertIn("12345", job_ids_list)
        self.assertIn("12346", job_ids_list)

        # Verify dependencies
        self.assertIn("12345", jobs[1].parents)
        self.assertIn("12346", jobs[2].parents)

    @patch("os.popen")
    def test_groupid_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "test-group-nested",
                "type": "sequential",
                "jobs": [
                    {
                        "job": {
                            "preamble": "base",
                            "command": "echo 'First job'",
                        },
                    },
                    {
                        "job": {
                            "preamble": "base",
                            "command": "echo 'Second job'",
                        },
                    },
                ],
            }
        }

        def submit_fn(*args, **kwargs):
            return submitter._submit_job(*args, **kwargs, dry=True)

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
            submit_fn=submit_fn,
        )

        # Verify submission
        jobs = viewer.get_jobs()
        self.assertIn("--dry", jobs[0].command)

    @patch("os.popen")
    def test_dryrun_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
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
                                        "command": "echo 'First job' --group_id {group_id}",
                                    }
                                },
                                {
                                    "job": {
                                        "preamble": "gpu",
                                        "command": "echo 'Second job' --group_id {group_id}",
                                    }
                                },
                            ],
                        }
                    },
                    {
                        "job": {
                            "preamble": "gpu",
                            "command": "echo 'Third job' --group_id {group_id}",
                        }
                    },
                ],
            }
        }

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        # Verify submission
        jobs = viewer.get_jobs()
        group_id_first = jobs[0].command.split("--group_id ")[1].split("-")[0]
        group_id_third = jobs[2].command.split("--group_id ")[1].split("-")[0]
        self.assertEqual(
            group_id_third,
            group_id_first,
        )

    @patch("os.popen")
    def test_groupname_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "a",
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "name": "b",
                            "type": "parallel",
                            "jobs": [
                                {
                                    "job": {
                                        "preamble": "base",
                                        "command": "echo 'First job' --group_id {group_id}",
                                    }
                                },
                            ],
                        }
                    },
                    {
                        "group": {
                            "type": "parallel",
                            "jobs": [
                                {
                                    "job": {
                                        "preamble": "gpu",
                                        "command": "echo 'Second job' --group_id {group_id}",
                                    }
                                },
                            ],
                        }
                    },
                    {
                        "job": {
                            "preamble": "gpu",
                            "command": "echo 'Third job' --group_id {group_id}",
                            "name": "c",
                        }
                    },
                ],
            }
        }

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        # Verify submission
        jobs = viewer.get_jobs()
        for job in jobs:
            if job.command.startswith("echo 'First job'"):
                self.assertEqual(job.node_name, "a:b")
            elif job.command.startswith("echo 'Second job'"):
                self.assertEqual(job.node_name, "a")
            elif job.command.startswith("echo 'Third job'"):
                self.assertEqual(job.node_name, "a:c")

    @patch("os.popen")
    def test_nested_loop_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "test-group-loop",
                "type": "loop",
                "loop_count": 2,
                "jobs": [
                    {
                        "job": {
                            "preamble": "gpu",
                            "command": "echo 'loop job' --group_id {group_id}",
                        }
                    },
                ],
            }
        }

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        # Verify submission
        jobs = viewer.get_jobs()
        self.assertEqual(len(jobs), 2)

    @patch("os.popen")
    def test_loop_workflow(self, mock_popen):
        """Test that jobs are submitted correctly."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "test-group-loop-root",
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "type": "loop",
                            "loop_count": 2,
                            "jobs": [
                                {
                                    "job": {
                                        "preamble": "gpu",
                                        "command": "echo 'first loop' --group_id {group_id}",
                                    }
                                },
                            ],
                        }
                    },
                    {
                        "group": {
                            "type": "loop",
                            "loop_count": 2,
                            "jobs": [
                                {
                                    "job": {
                                        "preamble": "gpu",
                                        "command": "echo 'second loop' --group_id {group_id}",
                                    }
                                },
                            ],
                        }
                    },
                ],
            },
        }

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        # Verify submission
        jobs = viewer.get_jobs()
        self.assertEqual(len(jobs), 4)
        job_ids_list = [job.id for job in jobs]
        for i in range(1, len(job_ids_list)):
            self.assertEqual(
                " ".join(jobs[i].parents),
                " ".join([str(j) for j in job_ids_list[i - 1 : i]]),
            )

        # assert first two and second two have diff loop_ids
        for i in range(2):
            self.assertNotEqual(
                jobs[i].node_id,
                jobs[i + 2].node_id,
                f"Loop IDs should be different for job {i} and {i + 2}",
            )
        # assert first two have same loop_id
        self.assertEqual(
            jobs[0].node_id,
            jobs[1].node_id,
            f"Loop IDs should be the same for job {i} and {i + 1}",
        )

    @patch("os.popen")
    def test_node_ids_workflow(self, mock_popen):
        """Test that jobs are submitted correctly with node IDs."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "test-group-node-ids",
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "name": "test-group-node-ids",
                            "type": "parallel",
                            "jobs": [
                                {
                                    "job": {
                                        "preamble": "base",
                                        "command": "echo 'First job' --group_id {group_id}",
                                    },
                                },
                                {
                                    "job": {
                                        "preamble": "gpu",
                                        "command": "echo 'Second job' --group_id {group_id}",
                                    },
                                },
                            ],
                        }
                    },
                    {
                        "group": {
                            "name": "test-group-node-ids",
                            "type": "sweep",
                            "preamble": "gpu",
                            "sweep": {
                                "param1": [1, 2],
                            },
                            "sweep_template": "python test.py param1={param1} --group_id {group_id}",
                        }
                    },
                ],
            }
        }

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        # Verify submission
        jobs = viewer.get_jobs()
        self.assertEqual(
            [j.node_id for j in jobs], [jobs[0].node_id] * 2 + [jobs[2].node_id] * 2
        )

    @patch("os.popen")
    def test_node_idx_workflow(self, mock_popen):
        """Test that jobs are submitted correctly with node IDs."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "test-group-node-ids",
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "name": "test-group-node-ids",
                            "type": "sequential",
                            "jobs": [
                                {
                                    "job": {
                                        "preamble": "base",
                                        "command": "echo 'First job' --group_id {group_id}",
                                    },
                                },
                                {
                                    "job": {
                                        "preamble": "gpu",
                                        "command": "echo 'Second job' --group_id {group_id}",
                                    },
                                },
                            ],
                        }
                    },
                    {
                        "group": {
                            "name": "test-group-node-ids",
                            "type": "sweep",
                            "preamble": "gpu",
                            "sweep": {
                                "param1": [1, 2],
                            },
                            "sweep_template": "python test.py param1={param1} --group_id {group_id} --sidx {sidx}",
                        }
                    },
                ],
            }
        }

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        parse_idx = lambda cmd: (
            match := re.search(r"--sidx (\d+)", cmd)
        ) and match.group(1)

        # Verify submission
        jobs = viewer.get_jobs()
        self.assertEqual([parse_idx(j.command) for j in jobs], [None, None, "0", "1"])

    # @patch("os.popen")
    # def test_sbatch_args(self, mock_popen):
    #     """Test that sbatch args are passed correctly."""

    #     ##### Setup mocks
    #     mock_popen.side_effect = self.get_popen_mock_fn()
    #     viewer = JobViewer(self.db_path)
    #     submitter = JobSubmitter(self.db_path)
    #     cfg = {
    #         "group": {
    #             "name": "test-group-sbatch",
    #             "type": "sequential",
    #             "jobs": [
    #                 {
    #                     "job": {
    #                         "preamble": "base",
    #                         "command": "echo 'First job'",
    #                     },
    #                 },
    #             ],
    #         },
    #     }

    #     submitter.walk(
    #         node=submitter._parse_group_dict(cfg["group"]),
    #         group_name=cfg["group"]["name"],
    #         preamble_map=self.preamble_map,
    #         depends_on=[],
    #         submitted_jobs=[],
    #     )

    #     # Verify submission
    #     jobs = viewer.get_jobs()
    #     self.assertNotIn("#SBATCH --output=test.out", jobs[0].preamble_sbatch)


if __name__ == "__main__":
    unittest.main()
