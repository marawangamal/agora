# Enhanced SLURM JobRunner

A powerful tool for defining, submitting, and tracking complex SLURM job workflows.

## Installation
```
pip install slurm-jobrunner
```

## Basic Usage
```bash
jrun submit --file workflow.yaml                            # submit many jobs
jrun status                                                 # view progress
jrun sbatch job.sh
jrun sbatch --gres=gpu:2 --cpus-per-task=4 --mem=16G --wrap="python hello.py"  # submit single job
```