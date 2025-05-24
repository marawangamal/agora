from dataclasses import asdict, dataclass, field
from typing import List, Dict, Any, Literal, Union


@dataclass
class JobSpec:
    """Specification for a SLURM job."""

    job_id: int
    command: str
    preamble: str
    group_name: str
    depends_on: List[str]
    status: str = "UNKNOWN"
    inactive_deps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the dataclass instance to a dictionary."""
        return asdict(self)

    def to_script(self, deptype: Literal["afterok", "afterany"] = "afterok") -> str:
        """Convert job spec to a SLURM script.

        Returns:
            String containing the complete SLURM script
        """
        # Split preamble into SBATCH directives and setup commands
        sbatch_lines = []
        setup_lines = []

        for line in self.preamble.split("\n"):
            line = line.strip()
            if line.startswith("#SBATCH") or line.startswith("#!/"):
                sbatch_lines.append(line)
            elif line:  # Non-empty, non-SBATCH line
                setup_lines.append(line)

        script_lines = sbatch_lines.copy()

        # Add dependency information if needed (must come with other SBATCH directives)
        if self.depends_on:
            # Convert job IDs to a colon-separated string
            # (e.g., "123:456:789")
            # Filter out inactive dependencies
            active_deps = [
                dep for dep in self.depends_on if dep not in self.inactive_deps
            ]
            if len(active_deps) != 0:
                dependencies = ":".join(active_deps)
                script_lines.append(f"#SBATCH --dependency={deptype}:{dependencies}")

        # Add setup commands
        if setup_lines:
            script_lines.extend(setup_lines)

        # Add the main command
        script_lines.append(self.command)

        return "\n".join(script_lines)


@dataclass
class PJob:
    preamble: str
    command: str
    name: str = ""


@dataclass
class PGroup:
    type: str
    jobs: List[Union[PJob, "PGroup"]]
    preamble: str = ""
    sweep: Dict[str, List[Any]] = field(default_factory=dict)
    sweep_template: str = ""
    name: str = ""
