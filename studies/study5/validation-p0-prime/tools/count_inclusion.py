"""P-0' step 6: how many units survive the registered inclusion rules.

Run only AFTER P0PRIME_PREREGISTRATION.json was committed and pushed, so the
count cannot have informed the floor it is judged against. The directive is
explicit that the floor of 30 was set without knowledge of this number, and the
disclosure in the registration records that the joint count had never been
computed at that point.

Both rules are evaluated on CLEAN runs only, so neither depends on any patching
result, and neither depends on which estimand is eventually chosen.

  correct-only       the model's top-1 continuation equals the item's own target
                     for BOTH the donor and the recipient
  denominator floor  L_full - L_clean is at least 1.0 logits
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

#: Read from the pushed registration rather than hard-coded, so this tool cannot
#: silently disagree with the text it is applying.
REGISTRATION = "P0PRIME_PREREGISTRATION.json"


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merged", required=True)
    parser.add_argument("--registration", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    reg = json.loads(Path(args.registration).read_text(encoding="utf-8"))
    operative = reg["2_registered_and_operative_regardless_of_the_estimand"]
    floor_n = int(operative["n_floor"]["value"])
    floor_denominator = float(operative["denominator_floor"]["value"])
    sensitivity = operative["denominator_floor"]["sensitivity_to_be_reported"]

    merged = json.loads(Path(args.merged).read_text(encoding="utf-8"))
    rows = merged["per_unit"]

    correct_both = [
        r
        for r in rows
        if r["donor_top1_is_donor_target"] and r["recipient_top1_is_recipient_target"]
    ]

    def surviving(threshold):
        kept = [r for r in correct_both if r["denominator"] >= threshold]
        return kept

    at_floor = surviving(floor_denominator)
    by_threshold = {
        str(t): {
            "units": len(surviving(t)),
            "clusters": len({r["cluster_id"] for r in surviving(t)}),
        }
        for t in sorted({floor_denominator, *(float(x) for x in sensitivity)})
    }

    meets = len(at_floor) >= floor_n
    report = {
        "schema_version": "study5-p0prime-inclusion-v1",
        "phase": "P-0'",
        "computed_after_the_registration_was_pushed": True,
        "registration_applied": args.registration,
        "rules_evaluated_on_clean_runs_only": True,
        "independent_of_every_patching_result": True,
        "independent_of_the_held_estimand": True,
        "population": {
            "units_measured_in_P0": len(rows),
            "clusters_measured_in_P0": len({r["cluster_id"] for r in rows}),
        },
        "marginals_previously_reported_by_P0": {
            "donor_top1_equals_donor_target": sum(
                1 for r in rows if r["donor_top1_is_donor_target"]
            ),
            "recipient_top1_equals_recipient_target": sum(
                1 for r in rows if r["recipient_top1_is_recipient_target"]
            ),
            "note": "these two marginals were the only accuracy numbers P-0 published; the joint below was never computed until now",
        },
        "correct_both": {
            "units": len(correct_both),
            "clusters": len({r["cluster_id"] for r in correct_both}),
            "fraction_of_measured": len(correct_both) / len(rows) if rows else 0.0,
        },
        "after_the_denominator_floor": {
            "floor": floor_denominator,
            "units": len(at_floor),
            "clusters": len({r["cluster_id"] for r in at_floor}),
        },
        "sensitivity_to_the_denominator_floor": by_threshold,
        "n_floor": floor_n,
        "meets_the_floor": meets,
        "consequence": (
            "the registered floor is met and a successor may proceed once the "
            "estimand is settled"
            if meets
            else "the registered floor is NOT met; the directive requires "
            "reporting and moving to P-0c rather than running"
        ),
        "claim_ceiling": "An inclusion count. It licenses no claim of any kind.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(f"units measured in P-0            : {report['population']['units_measured_in_P0']}")
    print(
        f"correct on BOTH sides            : {report['correct_both']['units']} "
        f"units, {report['correct_both']['clusters']} clusters "
        f"({report['correct_both']['fraction_of_measured']:.4f})"
    )
    print(
        f"after denominator floor {floor_denominator:>4}     : "
        f"{report['after_the_denominator_floor']['units']} units, "
        f"{report['after_the_denominator_floor']['clusters']} clusters"
    )
    for threshold, counts in sorted(by_threshold.items(), key=lambda kv: float(kv[0])):
        print(f"   sensitivity, floor {threshold:>5}      : {counts['units']} units")
    print(f"registered floor                 : {floor_n}")
    print(f"meets the floor                  : {meets}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
