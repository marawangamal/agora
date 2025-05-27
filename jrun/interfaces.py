from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Union
import os.path as osp
import appdirs
from pathlib import Path


def get_default_logs_dir() -> str:
    """Get (and create) a default logs directory under the jrun user‐data dir."""
    app_data_dir = Path(appdirs.user_data_dir("jrun"))
    logs_dir = app_data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return str(logs_dir)


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
    logs_dir: str = get_default_logs_dir()

    @property
    def preamble_sbatch(self) -> List[str]:
        """Return the preamble with resolved SBATCH log paths."""
        sbatch_lines = []
        for line in self.preamble.split("\n"):
            line = line.strip()
            if line.startswith("#SBATCH") or line.startswith("#!/"):
                sbatch_lines.append(line)
        return self._replace_sbatch_log_paths(sbatch_lines)

    @property
    def preamble_setup(self) -> List[str]:
        setup_lines = []
        for line in self.preamble.split("\n"):
            if line:  # Non-empty, non-SBATCH line
                setup_lines.append(line)
        return setup_lines

    def _replace_sbatch_log_paths(self, sbatch_lines: List[str]) -> List[str]:
        """Replace SBATCH log paths with the default logs directory."""
        updated_lines = []
        for line in sbatch_lines:
            if line.startswith("#SBATCH --output="):
                updated_lines.append(
                    f"#SBATCH --output={osp.join(self.logs_dir, 'slurm-%j.out')}"
                )
            elif line.startswith("#SBATCH --error="):
                updated_lines.append(
                    f"#SBATCH --error={osp.join(self.logs_dir, 'slurm-%j.err')}"
                )
            else:
                updated_lines.append(line)
        return updated_lines

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
    loop_count: int = 1
    name: str = ""
