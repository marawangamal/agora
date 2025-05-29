from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union



@dataclass
class JobInsert:
    id: str
    command: str
    preamble: str
    created_at: str
    updated_at: str
    node_id: Optional[str] = None
    node_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Job:
    """Specification for a SLURM job."""

    id: str
    command: str
    preamble: str
    created_at: str
    updated_at: str
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    # Fields not in vw_jobs
    status: str = "UNKNOWN"  
    slurm_log: Optional[str] = None
    slurm_err: Optional[str] = None


    @property
    def preamble_sbatch(self) -> List[str]:
        """Return the preamble with resolved SBATCH log paths."""
        sbatch_lines = []
        for line in self.preamble.split("\n"):
            line = line.strip()
            if line.startswith("#SBATCH") or line.startswith("#!/"):
                sbatch_lines.append(line)
        return sbatch_lines

    @property
    def preamble_setup(self) -> List[str]:
        setup_lines = []
        for line in self.preamble.split("\n"):
            if line:  # Non-empty, non-SBATCH line
                setup_lines.append(line)
        return setup_lines

    def to_dict(self) -> Dict[str, Any]:
        """Convert the dataclass instance to a dictionary."""
        return asdict(self)

    def to_script(self, deptype: Literal["afterok", "afterany"] = "afterok") -> str:
        """Convert job spec to a SLURM script.

        Returns:
            String containing the complete SLURM script
        """
        # Split preamble into SBATCH directives and setup commands
        sbatch_lines = self.preamble_sbatch
        setup_lines = self.preamble_setup

        # for line in self.preamble.split("\n"):
        #     line = line.strip()
        #     if line.startswith("#SBATCH") or line.startswith("#!/"):
        #         sbatch_lines.append(line)
        #     elif line:  # Non-empty, non-SBATCH line
        #         setup_lines.append(line)

        script_lines = sbatch_lines.copy()

        # Add dependency information if needed (must come with other SBATCH directives)
        if self.parents:
            # Convert job IDs to a colon-separated string
            # (e.g., "123:456:789")
            # Filter out inactive dependencies
            if len(self.parents) != 0:
                dependencies = ":".join(self.parents)
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
    loop_count: int = 1
    name: str = ""
