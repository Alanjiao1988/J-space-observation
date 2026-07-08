"""Run logging and metadata utilities."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class RunMetadata:
    """Metadata for a single experiment run."""
    timestamp: str
    run_id: str
    phase: str
    model_names: List[str]
    experiment_config: Dict[str, Any]
    git_commit: Optional[str] = None
    notes: Optional[str] = None


class RunLogger:
    """Manages run logging and metadata."""
    
    def __init__(self, base_results_dir: Path):
        """Initialize run logger."""
        self.base_results_dir = Path(base_results_dir)
        self.base_results_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir = self.base_results_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
    
    def create_run_directory(self, phase: str) -> Path:
        """
        Create a timestamped run directory.
        
        Args:
            phase: Phase name (e.g., "phase0_5", "phase1")
        
        Returns:
            Path to run directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.runs_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
    
    def save_metadata(
        self,
        run_dir: Path,
        metadata: RunMetadata
    ) -> Path:
        """Save metadata.json to run directory."""
        metadata_path = run_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(asdict(metadata), f, indent=2)
        return metadata_path
    
    def save_config(
        self,
        run_dir: Path,
        config: Dict[str, Any],
        name: str = "config.json"
    ) -> Path:
        """Save configuration to run directory."""
        config_path = run_dir / name
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return config_path
    
    def save_summary(
        self,
        run_dir: Path,
        summary: str,
        name: str = "summary.md"
    ) -> Path:
        """Save summary markdown to run directory."""
        summary_path = run_dir / name
        with open(summary_path, "w") as f:
            f.write(summary)
        return summary_path
    
    def append_run_log_entry(
        self,
        run_log_path: Path,
        phase: str,
        command: str,
        run_dir: Path,
        status: str = "completed",
        notes: Optional[str] = None
    ) -> None:
        """
        Append entry to run_log.md.
        
        Args:
            run_log_path: Path to docs/run_log.md
            phase: Phase name
            command: Command that was run
            run_dir: Directory where results were saved
            status: Status (completed, failed, in_progress)
            notes: Optional notes
        """
        timestamp = datetime.now().isoformat()
        run_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        entry = f"\n## {phase} - {timestamp}\n"
        entry += f"**Status**: {status}\n"
        entry += f"**Results**: {run_dir}\n"
        entry += f"**Command**: `{command}`\n"
        if notes:
            entry += f"**Notes**: {notes}\n"
        
        with open(run_log_path, "a") as f:
            f.write(entry)


class SummaryBuilder:
    """Build experiment summary reports."""
    
    def __init__(self, phase: str):
        self.phase = phase
        self.sections = {}
    
    def add_section(self, title: str, content: str) -> None:
        """Add a section to the summary."""
        self.sections[title] = content
    
    def add_metric(self, title: str, name: str, value: Any) -> None:
        """Add a metric."""
        if title not in self.sections:
            self.sections[title] = ""
        self.sections[title] += f"- **{name}**: {value}\n"
    
    def add_table(self, title: str, rows: List[tuple]) -> None:
        """Add a table to the summary."""
        if title not in self.sections:
            self.sections[title] = ""
        
        if rows:
            headers = rows[0]
            self.sections[title] += "| " + " | ".join(str(h) for h in headers) + " |\n"
            self.sections[title] += "| " + " | ".join("---" for _ in headers) + " |\n"
            for row in rows[1:]:
                self.sections[title] += "| " + " | ".join(str(v) for v in row) + " |\n"
    
    def build(self) -> str:
        """Build the summary markdown."""
        lines = [f"# {self.phase} Summary\n"]
        lines.append(f"Generated: {datetime.now().isoformat()}\n")
        
        for title, content in self.sections.items():
            lines.append(f"\n## {title}\n")
            lines.append(content)
        
        return "\n".join(lines)


def create_run_metadata(
    phase: str,
    model_names: List[str],
    experiment_config: Dict[str, Any],
    notes: Optional[str] = None
) -> RunMetadata:
    """Create RunMetadata object."""
    timestamp = datetime.now().isoformat()
    run_id = f"{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return RunMetadata(
        timestamp=timestamp,
        run_id=run_id,
        phase=phase,
        model_names=model_names,
        experiment_config=experiment_config,
        notes=notes,
    )


def record_resource_usage(
    run_dir: Path,
    wall_clock_time: float,
    peak_gpu_memory: Optional[float] = None,
    cpu_memory_peak: Optional[float] = None,
) -> Dict[str, Any]:
    """Record resource usage to run directory."""
    usage = {
        "wall_clock_time_seconds": wall_clock_time,
        "peak_gpu_memory_gb": peak_gpu_memory,
        "peak_cpu_memory_gb": cpu_memory_peak,
    }
    
    usage_path = run_dir / "resource_usage.json"
    with open(usage_path, "w") as f:
        json.dump(usage, f, indent=2)
    
    return usage
