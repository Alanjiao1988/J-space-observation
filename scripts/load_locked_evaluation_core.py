"""Load the locked-evaluation core bound to one frozen parser profile.

The core selects its candidate parser once, at import, from a name seeded into
its namespace before execution. Loading it without a profile yields the
parser-v2 identity that every pre-existing caller already relied on.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = (
    PROJECT_ROOT / "src" / "jspace_observation" / "parser_v2_locked_evaluation.py"
)
DEFAULT_PROFILE_ID = "parser-v2-v1"


def load_locked_evaluation_core(
    module_name: str,
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    core_path: Path | None = None,
    register: bool = True,
    spec_from_file_location=None,
) -> ModuleType:
    """Import the core with `profile_id` fixed for the lifetime of the module."""
    path = CORE_PATH if core_path is None else core_path
    factory = (
        importlib.util.spec_from_file_location
        if spec_from_file_location is None
        else spec_from_file_location
    )
    spec = factory(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot direct-load locked-evaluation core")
    module = importlib.util.module_from_spec(spec)
    module.__dict__["_PRESEEDED_PARSER_PROFILE_ID"] = profile_id
    if register:
        sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if register:
            sys.modules.pop(module_name, None)
        raise
    if module.ACTIVE_PARSER_PROFILE_ID != profile_id:
        raise RuntimeError("locked-evaluation core ignored the requested profile")
    if "_PRESEEDED_PARSER_PROFILE_ID" in module.__dict__:
        raise RuntimeError("locked-evaluation core leaked its profile seed")
    return module
