"""Configuration and settings for J-space observation project."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ModelConfig:
    """Model loading configuration."""
    model_name: str
    dtype: str = "float16"  # float16, bfloat16, float32
    device_map: str = "auto"
    output_hidden_states: bool = True
    load_in_8bit: bool = False
    load_in_4bit: bool = False


@dataclass
class NoCoTConfig:
    """No-CoT generation configuration."""
    method: str = "empty_think_prefill"  # empty_think_prefill, answer_only_prompt
    max_new_tokens: int = 128
    min_new_tokens: int = 1
    temperature: float = 1.0
    top_p: float = 1.0
    do_sample: bool = False
    
    # Validation thresholds
    max_think_tag_length: int = 10  # Very short is expected for empty-think
    allow_visible_reasoning: bool = False


@dataclass
class ExperimentConfig:
    """Experiment-wide configuration."""
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    results_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "results")
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    docs_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "docs")
    
    # Ensure directories exist
    def __post_init__(self):
        for d in [self.results_dir, self.data_dir, self.docs_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    @property
    def runs_dir(self) -> Path:
        return self.results_dir / "runs"
    
    @property
    def prompts_dir(self) -> Path:
        return self.data_dir / "prompts"


def get_default_config() -> ExperimentConfig:
    """Get default experiment configuration."""
    return ExperimentConfig()
