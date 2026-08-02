"""Emit the frozen Phase 1.0D protocol snapshot.

Runs in Azure only.  Prints the whole committed artifact as canonical JSON on
stdout, disclosures included, so ``docs/phase1_0d_protocol_snapshot.json`` is a
transcript of an Azure run with no hand-authored part.

The run-specific provenance is supplied by the caller, because only the caller
knows which ACR run produced the transcript.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from jspace_observation.phase1_0c_defect_audit import load_phase_1_0c_records  # noqa: E402
from jspace_observation.headroom_calibration import load_task_bank  # noqa: E402
from jspace_observation.phase1_0d_confirmation import (  # noqa: E402
    AUTHORITY_PROMPT_PATH,
    AUTHORITY_PROMPT_SHA256,
    AUTHORITY_SECTIONS,
    PROTOCOL_CONSEQUENCES,
    PROTOCOL_NOT_ESTABLISHED,
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="unrecorded")
    parser.add_argument("--commit", default="unrecorded")
    arguments = parser.parse_args()

    bank = load_task_bank(REPO_ROOT / DEFAULT_BANK_PATH)
    used = phase_1_0c_item_ids(load_phase_1_0c_records())
    eligible = eligible_items(bank, used)
    selected = select_confirmation_items(bank, used)
    snapshot = protocol_snapshot(
        selection=selection_summary(selected, used),
        strict_budget_check=assert_strict_budget_fits_every_answer(selected),
    )
    payload = {
        "artifact": "phase1_0d_protocol_snapshot",
        "work_package": "S1",
        "status": "FROZEN_BEFORE_INFERENCE",
        "authority": {
            "prompt": AUTHORITY_PROMPT_PATH,
            "prompt_sha256": AUTHORITY_PROMPT_SHA256,
            "section": AUTHORITY_SECTIONS,
        },
        "provenance": {
            "executed_in": "azure_container_registry_tasks",
            "registry": "acrjspaceobssea0708231738",
            "run_id": arguments.run_id,
            "platform": "linux/amd64",
            "base_image": "python:3.11-bookworm",
            "python_version": platform.python_version(),
            "dependency_closure": "requirements.lock.txt",
            "bound_commit": arguments.commit,
            "producer": "infra/azure/scripts/emit_phase1_0d_protocol.py",
            "protocol_module": "src/jspace_observation/phase1_0d_confirmation.py",
            "protocol_tests": "tests/test_phase1_0d_confirmation.py",
        },
        "snapshot": snapshot,
        "context": {
            "bank_item_count": len(bank),
            "phase_1_0c_item_count": len(used),
            "eligible_pool": {
                "item_count": len(eligible),
                "per_family_band": cell_availability(eligible),
            },
        },
        "consequences": list(PROTOCOL_CONSEQUENCES),
        "not_established": list(PROTOCOL_NOT_ESTABLISHED),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
