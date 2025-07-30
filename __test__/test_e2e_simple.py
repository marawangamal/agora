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
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "name": "test-group-loop",
                            "type": "loop",
                            "loop_type": "parallel",
                            "loop_count": 2,
                            "jobs": [
                                {
                                    "group": {
                                        "type": "sequential",
                                        "jobs": [
                                            {
                                                "job": {
                                                    "preamble": "gpu",
                                                    "command": "echo 'first job' --group_id {group_id} --loop_idx {loop_idx}",
                                                }
                                            },
                                            {
                                                "job": {
                                                    "preamble": "gpu",
                                                    "command": "echo 'second job' --group_id {group_id} --loop_idx {loop_idx}",
                                                }
                                            },
                                        ],
                                    }
                                },
                            ],
                        }
                    }
                ],
            }
        }

        #   - group:
        #       type: loop
        #       name: "loop"
        #       loop_count: 24
        #       loop_type: "parallel"
        #       jobs:
        #         - group:
        #             type: sequential
        #             jobs:
        #               # aaa-bbb-ccc-aaa
        #               # Creates a <experiment_name>/.best file
        #               - job:
        #                   preamble: gpu1
        #                   command: "python main.py train --lookup --epochs 300  --group_level 1 --group_id {group_id} --idx {loop_idx}"
        #                   name: "ltrain"

        #               # Run expensive test on best models
        #               # aaa-bbb-ccc-bbb
        #               - job:
        #                   preamble: gpu1
        #                   command: "python main.py test --lookup --group_level 1 --group_id {group_id} --idx {loop_idx} --delete_ckpt --gen_mode draft_multi_horizon"
        #                   name: "ltest"

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

        # Check that loop_idx is set correctly
        for i, job in zip([0] * 2 + [1] * 2, jobs):
            match = re.search(r"--loop_idx (\d+)", job.command)
            self.assertIsNotNone(match, f"Loop index not found in job {i} command")
            self.assertEqual(int(match.group(1)), i, f"Loop index mismatch for job {i}")  # type: ignore

    @patch("os.popen")
    def test_loop_seq_workflow(self, mock_popen):
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

        expected_node_ids = [jobs[0].node_id] * 2 + [jobs[2].node_id] * 2
        actual_node_ids = [j.node_id for j in jobs]
        self.assertEqual(
            expected_node_ids,
            actual_node_ids,
            "Node IDs should match the expected pattern",
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
    def test_loop_parallel_workflow(self, mock_popen):
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
                            "name": "test-group-node-ids",
                            "type": "sweep",
                            "preamble": "gpu",
                            "sweep": {
                                "param1": [1, 2],
                            },
                            "sweep_template": "python test.py param1={param1} --group_id {group_id}",
                        },
                    },
                    {
                        "group": {
                            "type": "loop",
                            "loop_count": 2,
                            "loop_type": "parallel",
                            "jobs": [
                                {
                                    "group": {
                                        "type": "sequential",
                                        "jobs": [
                                            {
                                                "job": {
                                                    "preamble": "gpu",
                                                    "command": "echo 'first job' --group_id {group_id}",
                                                }
                                            },
                                            {
                                                "job": {
                                                    "preamble": "gpu",
                                                    "command": "echo 'second job' --group_id {group_id}",
                                                }
                                            },
                                        ],
                                    }
                                },
                            ],
                        },
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
        self.assertEqual(len(jobs), 6)

        expected_parents = [
            [],
            [],
            [j.id for j in jobs[:2]],
            [jobs[2].id],
            [j.id for j in jobs[:2]],
            [jobs[4].id],
        ]
        actual_parents = [j.parents for j in jobs]
        self.assertEqual(
            expected_parents,
            actual_parents,
            "Parents should match the expected pattern",
        )

        expected_node_ids = [jobs[0].node_id] * 2 + [jobs[2].node_id] * 4
        actual_node_ids = [j.node_id for j in jobs]
        self.assertEqual(
            expected_node_ids,
            actual_node_ids,
            "Node IDs should match the expected pattern",
        )

    @patch("os.popen")
    def test_loop_parallel_node_id_workflow(self, mock_popen):
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
                            "name": "sweep",
                            "type": "sweep",
                            "preamble": "gpu",
                            "sweep": {
                                "param1": [1, 2],
                            },
                            "sweep_template": "python test.py param1={param1} --group_id {group_id}",
                        },
                    },
                    {
                        "job": {
                            "command": "python main.py tag --group_by rank horizon --group_level 1 --group_id {group_id}",
                            "preamble": "gpu",
                            "name": "tag",
                        },
                    },
                    {
                        "group": {
                            "name": "loop",
                            "type": "loop",
                            "loop_count": 2,
                            "loop_type": "parallel",
                            "jobs": [
                                {
                                    "group": {
                                        "type": "sequential",
                                        "jobs": [
                                            {
                                                "job": {
                                                    "preamble": "gpu",
                                                    "command": "echo 'first job' --group_id {group_id}",
                                                }
                                            },
                                            {
                                                "job": {
                                                    "preamble": "gpu",
                                                    "command": "echo 'second job' --group_id {group_id}",
                                                }
                                            },
                                        ],
                                    }
                                },
                            ],
                        },
                    },
                ],
            },
        }

        #    #  1. Sweep over lr, rank, horizon
        #   - group:
        #       # aaa-bbb-XXXX
        #       name: "sweep"
        #       type: sweep
        #       preamble: gpu4long
        #       sweep: # 3x4x5=60
        #         lr: [1e-3, 5e-4, 1e-4, 5e-5]
        #       sweep_template:  "python main.py train --accel_strategy fsdp --dataset gsm8k --model meta-llama/Llama-3.2-3B-Instruct --epochs 2 --batch_size 8 --seq_len 128 --lr {lr} --model_head base --rank 1 --horizon 1 --use_memory_efficient_loss --slurm_job_id $SLURM_JOB_ID --group_id {group_id} --loss_mode joint --delete_ckpt"

        #   # 2. Tag best model for each (rank, horizon) combination
        #   - job:
        #       # aaa-bbb-bbb
        #       # Creates a <experiment_name>/.prospect file
        #       preamble: cpu
        #       command: "python main.py tag --group_by rank horizon --group_level 1 --group_id {group_id}"
        #       name: "tag"

        submitter.walk(
            node=submitter._parse_group_dict(root["group"]),
            node_name=root["group"]["name"],
            preamble_map=self.preamble_map,
            depends_on=[],
            submitted_jobs=[],
        )

        # Verify submission
        jobs = viewer.get_jobs()
        self.assertEqual(len(jobs), 7)

        expected_node_ids = (
            [jobs[0].node_id] * 2 + [jobs[2].node_id] + [jobs[3].node_id] * 4
        )
        actual_node_ids = [j.node_id for j in jobs]
        self.assertEqual(
            expected_node_ids,
            actual_node_ids,
            "Node IDs should match the expected pattern",
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
                            "sweep_template": "python test.py param1={param1} --group_id {group_id} --sweep_idx {sweep_idx}",
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
            match := re.search(r"--sweep_idx (\d+)", cmd)
        ) and match.group(1)

        # Verify submission
        jobs = viewer.get_jobs()
        self.assertEqual([parse_idx(j.command) for j in jobs], [None, None, "0", "1"])

    @patch("os.popen")
    def test_group_node_id_workflow(self, mock_popen):
        """Test that jobs are submitted correctly with node IDs."""

        ##### Setup mocks
        mock_popen.side_effect = self.get_popen_mock_fn()
        viewer = JobViewer(self.db_path)
        submitter = JobSubmitter(self.db_path)
        root = {
            "group": {
                "name": "root",
                "type": "sequential",
                "jobs": [
                    {
                        "group": {
                            "name": "pgroup",
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
                            "name": "sweep",
                            "type": "sweep",
                            "preamble": "gpu",
                            "sweep": {
                                "param1": [1, 2],
                            },
                            "sweep_template": "python test.py param1={param1} --group_id {group_id} --sweep_idx {sweep_idx}",
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
            match := re.search(r"--sweep_idx (\d+)", cmd)
        ) and match.group(1)

        # Verify submission
        jobs = viewer.get_jobs()
        self.assertIsNotNone(jobs[0].node_id, "Node ID should not be None")
        self.assertEqual(
            jobs[0].node_id,
            jobs[1].node_id,
            "Node IDs should be the same for parallel group",
        )

        self.assertEqual(
            jobs[2].node_id,
            jobs[3].node_id,
            "Node IDs should be the same for parallel group",
        )

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
