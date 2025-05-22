from dataclasses import asdict, dataclass, field
from typing import List, Dict, Any, Union


@dataclass
class JobSpec:
    """Specification for a SLURM job."""

    job_id: int
    command: str
    preamble: str
    group_name: str
    depends_on: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the dataclass instance to a dictionary."""
        return asdict(self)

    def to_script(self) -> str:
        """Convert job spec to a SLURM script.

        Returns:
            String containing the complete SLURM script
        """
        script_lines = [self.preamble]

        # Add dependency information if needed
        if self.depends_on:
            dependencies = ":".join(self.depends_on)
            script_lines.append(f"#SBATCH --dependency=afterok:{dependencies}")

        # Add the command
        script_lines.append(self.command)

        return "\n".join(script_lines)


@dataclass
class PJob:
    preamble: str
    command: str


@dataclass
class SJob:
    preamble: str
    command: str


@dataclass
class PGroup:
    type: str
    jobs: List[Union[PJob, "PGroup"]]
    preamble: str = ""
    sweep: Dict[str, List[Any]] = field(default_factory=dict)
    sweep_template: str = ""
