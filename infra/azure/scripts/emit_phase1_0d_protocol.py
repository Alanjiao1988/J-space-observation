"""Emit the frozen Phase 1.0D protocol snapshot.

Runs in Azure only.  Prints the snapshot as canonical JSON on stdout so the
snapshot committed to ``docs/`` is a transcript of an Azure run rather than
something computed on a laptop.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from jspace_observation.phase1_0c_defect_audit import load_phase_1_0c_records  # noqa: E402
from jspace_observation.headroom_calibration import load_task_bank  # noqa: E402
from jspace_observation.phase1_0d_confirmation import (  # noqa: E402
    DEFAULT_BANK_PATH,
    assert_strict_budget_fits_every_answer,
    cell_availability,
    eligible_items,
    phase_1_0c_item_ids,
    protocol_snapshot,
    select_confirmation_items,
    selection_summary,
)


def main() -> int:
    bank = load_task_bank(REPO_ROOT / DEFAULT_BANK_PATH)
    used = phase_1_0c_item_ids(load_phase_1_0c_records())
    eligible = eligible_items(bank, used)
    selected = select_confirmation_items(bank, used)
    snapshot = protocol_snapshot(
        selection=selection_summary(selected, used),
        strict_budget_check=assert_strict_budget_fits_every_answer(selected),
    )
    payload = {
        "snapshot": snapshot,
        "context": {
            "bank_item_count": len(bank),
            "phase_1_0c_item_count": len(used),
            "eligible_pool": {
                "item_count": len(eligible),
                "per_family_band": cell_availability(eligible),
            },
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
