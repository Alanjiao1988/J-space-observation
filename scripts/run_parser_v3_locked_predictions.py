"""Run Stage P for the parser-v3 locked evaluation.

This launcher exists so the candidate parser is chosen by *which entrypoint was
started*, never by an argument, an environment variable, or a locked input. The
profile name below is a literal: it is seeded into the Stage P module's
namespace before that module executes, so the candidate identity is fixed at
import time and cannot be rebound afterwards.

Starting `run_parser_v2_locked_predictions.py` directly still runs parser v2,
exactly as it always has.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


PROFILE_ID = "parser-v3-v1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_P_PATH = PROJECT_ROOT / "scripts" / "run_parser_v2_locked_predictions.py"
STAGE_P_MODULE_NAME = "_jspace_parser_v3_stage_p_entrypoint"

CANDIDATE_WORKER_MODULE = "scripts/parser_v3_process_worker.py"
CANDIDATE_ALGORITHM_ID = "jspace-parser-v3-reference-blind-extraction/v1"
CANDIDATE_VERSION = (
    "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace"
)
CANDIDATE_SOURCE_SHA256 = (
    "76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9"
)


def load_stage_p() -> ModuleType:
    """Import Stage P with the parser-v3 profile fixed before execution."""
    spec = importlib.util.spec_from_file_location(
        STAGE_P_MODULE_NAME, STAGE_P_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot direct-load the Stage P entrypoint")
    module = importlib.util.module_from_spec(spec)
    module.__dict__["_PRESEEDED_PARSER_PROFILE_ID"] = PROFILE_ID
    sys.modules[STAGE_P_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(STAGE_P_MODULE_NAME, None)
        raise
    if module.STAGE_P_PROFILE_ID != PROFILE_ID:
        raise RuntimeError("Stage P ignored the parser-v3 profile")
    if "_PRESEEDED_PARSER_PROFILE_ID" in module.__dict__:
        raise RuntimeError("Stage P leaked its profile seed")
    if module.PARSER_V3_WORKER_PATH != PROJECT_ROOT / Path(
        CANDIDATE_WORKER_MODULE
    ):
        raise RuntimeError("Stage P candidate worker path is not the frozen one")
    if module._PARSER_V3_VERSION != CANDIDATE_VERSION:
        raise RuntimeError("Stage P candidate version is not the frozen one")
    return module


def main(argv: list[str] | None = None) -> int:
    return load_stage_p().main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
