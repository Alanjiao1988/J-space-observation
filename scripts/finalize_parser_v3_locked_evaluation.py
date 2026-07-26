"""Run Stage E scoring for the parser-v3 locked evaluation.

Selecting the scoring profile by entrypoint, not by argument, keeps Stage E's
identity as fixed as Stage P's. The profile chosen here is a *scoring* profile:
Stage E loads no parser under any profile, and every parser-import guard in the
scorer remains in force.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


PROFILE_ID = "parser-v3-v1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_E_PATH = (
    PROJECT_ROOT / "scripts" / "finalize_parser_v2_locked_evaluation.py"
)
STAGE_E_MODULE_NAME = "_jspace_parser_v3_stage_e_entrypoint"

CANDIDATE_ALGORITHM_ID = "jspace-parser-v3-reference-blind-extraction/v1"
CANDIDATE_VERSION = (
    "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace"
)
CANDIDATE_SOURCE_SHA256 = (
    "76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9"
)


def load_stage_e() -> ModuleType:
    """Import Stage E with the parser-v3 scoring profile fixed before execution."""
    spec = importlib.util.spec_from_file_location(
        STAGE_E_MODULE_NAME, STAGE_E_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot direct-load the Stage E entrypoint")
    module = importlib.util.module_from_spec(spec)
    module.__dict__["_PRESEEDED_PARSER_PROFILE_ID"] = PROFILE_ID
    sys.modules[STAGE_E_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(STAGE_E_MODULE_NAME, None)
        raise
    if module.STAGE_E_PROFILE_ID != PROFILE_ID:
        raise RuntimeError("Stage E ignored the parser-v3 scoring profile")
    if "_PRESEEDED_PARSER_PROFILE_ID" in module.__dict__:
        raise RuntimeError("Stage E leaked its profile seed")
    if (
        module._CANDIDATE_PREDICTIONS_MEMBER
        != "parser_v3_candidate_predictions.jsonl"
        or module._GATING_COMPARATOR_PREDICTIONS_MEMBER
        != "parser_v2_comparator_predictions.jsonl"
        or module._LEGACY_PREDICTIONS_MEMBER
        != "legacy_comparator_predictions.jsonl"
    ):
        raise RuntimeError("Stage E stream members are not the frozen ones")
    return module


def main(argv: list[str] | None = None) -> int:
    return load_stage_e().main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
