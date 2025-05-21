# SLURM JobRunner (jrun)

A tool for defining, submitting, and tracking SLURM job workflows.

## Installation

```bash
pip install -e . # editable install
```

## Usage

```bash
# Submit a workflow from YAML file
jrun submit --file workflow.yaml

# Check job statuses
jrun status

# Submit a single job
jrun sbatch --cpus-per-task=4 --mem=16G --wrap="python train.py"
```

## Example Workflow YAML

```yaml
preambles:
  base:
    - "#!/bin/bash"
    - "#SBATCH --cpus-per-task=4"
    - "#SBATCH --mem=8G"

group:
  name: "example-workflow"
  type: sequential
  jobs:
    - job:
        preamble: base
        command: "python preprocess.py"
    
    - job:
        preamble: base
        command: "python train.py"
```

## Requirements

- Python 3.6+
- SLURM environment
- PyYAML >= 6.0
- tabulate >= 0.9.0