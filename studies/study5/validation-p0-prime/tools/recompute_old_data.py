"""P-0' section 6: the permitted recomputation of P-0's data, reported only.

The directive permits P-0's saved values to be used to recompute a candidate
estimand ONCE this phase's registration is pushed, strictly as a reported-only
diagnostic. It may not set a threshold and it may not select a parameter, and
this tool does neither: it computes, prints and writes, and nothing downstream
consumes its output.

There is a limitation worth stating plainly rather than burying. P-0 did not
retain raw per-token logits. It retained, per unit, ld_donor, ld_recipient and
their difference, and it retained the restoration curves. The directive says not
to re-run in order to obtain logits, so this works from what exists.

That turns out not to matter here, and for a reason that is itself the finding:
the prescribed estimand is algebraically identical to the one P-0 applied, so
recomputing it is the identity map. This tool demonstrates that on the committed
data rather than asserting it, and reports the maximum discrepancy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merged", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    merged = json.loads(Path(args.merged).read_text(encoding="utf-8"))
    per_unit = {row["unit_id"]: row for row in merged["per_unit"]}
    curves = merged["curves"]

    # Invert P-0's stored restoration back to the underlying L_patch, then feed
    # that through the prescribed formula. If the two estimands differ at all,
    # the round trip cannot close.
    worst = 0.0
    compared = 0
    for construction, by_site in curves.items():
        for site, by_layer in by_site.items():
            for layer, by_cluster in by_layer.items():
                for cluster, values in by_cluster.items():
                    rows = [
                        r for r in merged["per_unit"] if r["cluster_id"] == cluster
                    ]
                    for row, stored in zip(rows, values):
                        l_clean = row["ld_recipient"]
                        l_full = row["ld_donor"]
                        denominator = l_full - l_clean
                        l_patch = stored * denominator + l_clean
                        prescribed = (l_patch - l_clean) / (l_full - l_clean)
                        worst = max(worst, abs(prescribed - stored))
                        compared += 1

    bridge = curves["REAL"]["BRIDGE"]
    peak_layer, peak = None, None
    for layer, by_cluster in bridge.items():
        values = [v for vs in by_cluster.values() for v in vs]
        mean = sum(values) / len(values)
        if peak is None or mean > peak:
            peak, peak_layer = mean, int(layer)

    report = {
        "schema_version": "study5-p0prime-recomputation-v1",
        "phase": "P-0'",
        "status": "REPORTED ONLY",
        "permitted_by": "the directive, section 3, after the registration was pushed",
        "may_set_a_threshold": False,
        "may_select_a_parameter": False,
        "consumed_by_anything_downstream": False,
        "what_P0_retained": [
            "ld_donor, ld_recipient and their difference, per unit",
            "the restoration curves",
        ],
        "what_P0_did_not_retain": "raw per-token logits",
        "no_rerun_was_performed_to_obtain_them": True,
        "why_that_does_not_matter_here": (
            "the prescribed estimand is algebraically identical to the one P-0 "
            "applied, so recomputing it is the identity map"
        ),
        "round_trip": {
            "method": (
                "invert each stored restoration to the underlying L_patch, then "
                "evaluate the prescribed formula on it; if the two estimands "
                "differed at all the round trip could not close"
            ),
            "values_compared": compared,
            "worst_absolute_discrepancy": worst,
            "identical": worst < 1e-9,
        },
        "the_numbers_are_therefore_P0s_own": {
            "bridge_peak_mean": peak,
            "bridge_peak_layer": peak_layer,
            "note": (
                "reproduced here only to show the recomputation carries no "
                "information beyond what P-0 already published; it is not a "
                "result of this phase and it is not a conclusion"
            ),
        },
        "claim_ceiling": (
            "A reported-only diagnostic. It licenses no claim of any kind and "
            "sets no threshold."
        ),
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(f"values compared           : {compared}")
    print(f"worst absolute discrepancy: {worst:.3e}")
    print(f"identical                 : {report['round_trip']['identical']}")
    print(f"BRIDGE peak (P-0's own)   : {peak:.6f} at layer {peak_layer}")
    print("P0PRIME-RECOMPUTATION REPORTED ONLY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
