"""One-off updater for resource_accounting.json and STATUS.json at P-2 close.

Kept as a committed script rather than an ad hoc edit so the numbers in those
two files can be traced to the arithmetic that produced them.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FIT_GPU_SECONDS = 14289.8 + 14306.4 + 14459.7 + 14320.2
CURVE_GPU_SECONDS = 3720.0
P2_GPU_HOURS = round((FIT_GPU_SECONDS + CURVE_GPU_SECONDS) / 3600.0, 6)
CUMULATIVE_GPU_HOURS = 31.582505
LENS_BYTES = 1387272497


def update_resources() -> None:
    path = ROOT / "resource_accounting.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    d["updated_at_utc"] = "2026-08-28T04:30:00Z"
    d["phase"] = "P-2 complete"
    aug = d["quantities"]["actively_used_gpu_hours"]
    aug["value_this_invocation"] = CUMULATIVE_GPU_HOURS
    aug["remaining"] = round(240 - CUMULATIVE_GPU_HOURS, 6)
    d["per_phase_actively_used_gpu_hours"]["P-2"] = P2_GPU_HOURS
    d["p2_budget"] = {
        "ceiling": 48,
        "units": "actively used GPU-hours",
        "consumed": P2_GPU_HOURS,
        "remaining": round(48 - P2_GPU_HOURS, 6),
        "reserve_drawn_on": 0.0,
        "reserve_rule": "OD-007",
        "breakdown": {
            "step1_retokenisation_cpu_only": 0.0,
            "step2_lens_fitting_four_shards": round(FIT_GPU_SECONDS / 3600.0, 6),
            "step3_kurtosis_four_curves": round(CURVE_GPU_SECONDS / 3600.0, 6),
            "control_diagnostic_and_reruns": "included in the figures above",
            "step4_decision_cpu_only": 0.0,
            "upload_cpu_only": 0.0,
        },
        "note": (
            "Within the phase ceiling; the OD-007 shared reserve was not drawn on."
        ),
    }
    d["od_007_reserve"] = {
        "rule": "OD-007",
        "unallocated_at_plan_time": 12.0,
        "returned_from_P-1": 9.388634,
        "returned_from_P-2": round(48 - P2_GPU_HOURS, 6),
        "total_available_reserve": round(12.0 + 9.388634 + (48 - P2_GPU_HOURS), 6),
        "consumed_from_reserve_so_far": 0.0,
        "global_ceiling_is_the_only_hard_stop": 240,
    }
    d["bytes_written"]["blob_bytes_written_this_invocation"] = (
        53330976198 + 2 * LENS_BYTES
    )
    d["bytes_written"]["blobs_written"] = 84
    d["bytes_written"]["p2_lens_blobs"] = {
        "count": 2,
        "bytes": 2 * LENS_BYTES,
        "prefix": "runs/study5-eq1/p2/lenses/sha256/",
        "create_only": True,
        "round_trip_rehashed": True,
        "overwrites": 0,
        "containers_created": 0,
    }
    path.write_text(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"P-2 consumed {P2_GPU_HOURS} of 48; cumulative {CUMULATIVE_GPU_HOURS} of 240")


def update_status() -> None:
    path = ROOT / "STATUS.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    d["lifecycle_state"] = "STUDY5_EQ1_P2_COMPLETE_Q4A_FAIL_AWAITING_OPERATOR"
    d["current_phase"] = "P-2 complete"
    d["next_phase"] = (
        "none without an operator decision; Q-4a FAIL is a registered terminal "
        "state for the workspace-band construct"
    )
    d["gates"] = d.get("gates", {})
    d["gates"]["Q-4a"] = {
        "verdict": "FAIL",
        "terminal_state": "STUDY5_EQ1_WORKSPACE_BAND_NOT_ESTABLISHED_AT_THIS_SCALE",
        "criteria_source": "OD-009, clarified by OD-009-A1",
        "C1_interior_maximum": False,
        "C2_contiguity": True,
        "C3_coverage": False,
        "C4_cross_fit_agreement": False,
        "C5_exceeds_matched_norm_null": False,
        "what_it_means": (
            "The J-space construct was not established on this model, and "
            "therefore NOTHING WAS MEASURED. This is NOT evidence that J-space "
            "is absent at 7B, it must not be written up as a negative finding, "
            "and no later text may cite it as negative evidence."
        ),
        "verdict_invariant_to_the_position_rule": True,
    }
    d["is_a_scientific_result"] = False
    d["confirmation_authorized"] = False
    path.write_text(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"STATUS lifecycle_state -> {d['lifecycle_state']}")


if __name__ == "__main__":
    update_resources()
    update_status()
