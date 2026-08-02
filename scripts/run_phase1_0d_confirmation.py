"""Container entrypoint for the Phase 1.0D headroom confirmation run.

Thin by design: every decision lives in
``jspace_observation.phase1_0d_generation`` so the code that runs in the GPU
container is the same code the Azure test gate exercises on CPU.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jspace_observation.phase1_0d_generation import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
