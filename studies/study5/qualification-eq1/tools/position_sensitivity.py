"""Sensitivity check: is the Q-4a verdict an artifact of the position rule?

The frozen aggregation (readout_convention.json) averages over positions 1.. .
measure_kurtosis.py also recorded, at no extra cost, the same per-position
values averaged over positions 16.. , matching the convention the fit itself
uses.

This re-runs the identical, unmodified criteria on the secondary aggregation and
reports whether the verdict changes. It is a SENSITIVITY ARTIFACT, not a second
decision: the registered verdict is the one computed on the frozen primary rule,
whatever this says.

The reason to run it is the same reason the P-1 ceiling sensitivity was run - a
verdict that depends on an arbitrary convention should be known to depend on it,
and the operator should be told either way.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--curves", required=True)
    parser.add_argument("--primary-decision", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()

    tools = Path(__file__).resolve().parent
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    data = json.loads(Path(args.curves).read_text(encoding="utf-8"))

    swapped = {"curves": {}}
    for name, points in data["curves"].items():
        swapped["curves"][name] = [
            {
                "layer": p["layer"],
                "excess_kurtosis": p["excess_kurtosis_skip_first_16"],
                "n_position_samples": p["n_position_samples_skip_first_16"],
            }
            for p in points
        ]

    alt_curves = workdir / "curves_skip_first_16.json"
    alt_curves.write_bytes(canonical_json_bytes(swapped))
    alt_decision = workdir / "decision_skip_first_16.json"

    # The criteria tool is invoked unchanged, as a subprocess, so there is no
    # possibility of this script influencing how the criteria are applied.
    result = subprocess.run(
        [
            sys.executable,
            str(tools / "decide_q4a.py"),
            "--curves",
            str(alt_curves),
            "--out-decision",
            str(alt_decision),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"criteria tool failed: {result.stderr}")

    primary = json.loads(Path(args.primary_decision).read_text(encoding="utf-8"))
    secondary = json.loads(alt_decision.read_text(encoding="utf-8"))

    per_criterion = {
        name: {
            "primary": primary["criteria"][name]["pass"],
            "secondary_skip_first_16": secondary["criteria"][name]["pass"],
            "agrees": primary["criteria"][name]["pass"]
            == secondary["criteria"][name]["pass"],
        }
        for name in ("C1", "C2", "C3", "C4", "C5")
    }

    report = {
        "schema_version": "study5-eq1-p2-position-sensitivity-v1",
        "phase": "P-2",
        "status": "SENSITIVITY ARTIFACT - not a decision",
        "registered_verdict_is_the_primary_one": primary["verdict"],
        "secondary_verdict": secondary["verdict"],
        "verdict_invariant_to_the_position_rule": primary["verdict"]
        == secondary["verdict"],
        "primary_rule": "mean over positions 1.. (frozen in readout_convention.json)",
        "secondary_rule": "mean over positions 16.. (matches jlens fit skip_first)",
        "per_criterion": per_criterion,
        "primary_bands": {
            "A": primary["criteria"]["C2"]["A"]["band"],
            "B": primary["criteria"]["C2"]["B"]["band"],
            "argmax_A": primary["criteria"]["C1"]["argmax_A"],
            "argmax_B": primary["criteria"]["C1"]["argmax_B"],
        },
        "secondary_bands": {
            "A": secondary["criteria"]["C2"]["A"]["band"],
            "B": secondary["criteria"]["C2"]["B"]["band"],
            "argmax_A": secondary["criteria"]["C1"]["argmax_A"],
            "argmax_B": secondary["criteria"]["C1"]["argmax_B"],
        },
        "claim_ceiling": (
            "A sensitivity check on a measurement convention. It licenses no "
            "claim of any kind, and it does not alter the registered verdict."
        ),
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))
    print(json.dumps(report, indent=1))
    print("P2-CHECK-POSITION-SENSITIVITY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
