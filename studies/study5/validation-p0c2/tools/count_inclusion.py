"""P-0c-2 step 4-5: per-position accuracy and the correct-both count.

Two registered obligations are discharged here, both from CLEAN runs and both
before anything is patched.

The per-position report is mandatory for a specific reason. Correct-both
filtering is a selection, and source-line position is the only free confound the
BRIDGE equal-length identity does not eliminate. P-0c measured that confound
ranging from 1.000 at position 0 to 0.565 at position 3, so a filtered subset
could be systematically biased toward earlier positions without anything in the
downstream analysis showing it. The only way to see it is to report the position
distribution BEFORE and AFTER the filter and compare them.

The unit count is then taken against the floor of 60, which was registered
before any of this existed.

Both quantities are independent of every patching result and of the held
estimand.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def distribution(rows, key="registration_line_position"):
    out: dict[str, int] = {}
    for row in rows:
        out[str(row[key])] = out.get(str(row[key]), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def accuracy_by_position(rows):
    buckets: dict[str, dict] = {}
    for row in rows:
        slot = buckets.setdefault(
            str(row["registration_line_position"]), {"n": 0, "correct": 0}
        )
        slot["n"] += 1
        slot["correct"] += bool(row["correct"])
    return {
        position: {
            "n": v["n"],
            "correct": v["correct"],
            "accuracy": v["correct"] / v["n"] if v["n"] else 0.0,
        }
        for position, v in sorted(buckets.items(), key=lambda kv: int(kv[0]))
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", required=True)
    parser.add_argument("--proof", required=True)
    parser.add_argument("--registration", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    reg = json.loads(Path(args.registration).read_text(encoding="utf-8"))
    obj = json.loads(Path(args.object).read_text(encoding="utf-8"))
    proof = json.loads(Path(args.proof).read_text(encoding="utf-8"))

    floor = 60
    for requirement in reg["3_all_seven_requirements_are_re_proven_from_scratch"][
        "the_seven"
    ].values():
        if isinstance(requirement, str) and ">= 60" in requirement:
            floor = 60

    by_item = {row["item_id"]: row for row in proof["per_item"]}
    units = obj["units"]

    all_units = []
    correct_both = []
    for unit in units:
        donor = by_item[unit["donor"]]
        recipient = by_item[unit["recipient"]]
        record = {
            "unit_id": unit["unit_id"],
            "cluster_id": unit["cluster_id"],
            "donor_position": unit["donor_position"],
            "recipient_position": unit["recipient_position"],
            "donor_correct": donor["correct"],
            "recipient_correct": recipient["correct"],
        }
        all_units.append(record)
        if donor["correct"] and recipient["correct"]:
            correct_both.append(record)

    # Position accuracy over every item, and over the items that survive the
    # correct-both filter. The second is a tautology at the item level - every
    # surviving item is correct - so what is compared is the DISTRIBUTION of
    # positions, which is where the bias would show.
    items_before = proof["per_item"]
    surviving_ids = {r["unit_id"] for r in correct_both}
    items_after = [
        by_item[unit[role]]
        for unit in units
        if unit["unit_id"] in surviving_ids
        for role in ("donor", "recipient")
    ]

    before_dist = distribution(items_before)
    after_dist = distribution(items_after)
    total_before = sum(before_dist.values()) or 1
    total_after = sum(after_dist.values()) or 1

    shift = {
        position: {
            "share_before": before_dist.get(position, 0) / total_before,
            "share_after": after_dist.get(position, 0) / total_after,
            "change": (
                after_dist.get(position, 0) / total_after
                - before_dist.get(position, 0) / total_before
            ),
        }
        for position in sorted(
            set(before_dist) | set(after_dist), key=lambda p: int(p)
        )
    }
    worst_shift = max((abs(v["change"]) for v in shift.values()), default=0.0)

    meets = len(correct_both) >= floor
    report = {
        "schema_version": "study5-p0c2-inclusion-v1",
        "phase": "P-0c-2",
        "computed_after_the_registration_was_pushed": True,
        "registration_sha256": sha256_file(Path(args.registration)),
        "object_sha256": sha256_file(Path(args.object)),
        "measured_on_clean_runs_only": True,
        "independent_of_every_patching_result": True,
        "independent_of_the_held_estimand": True,

        "counts": {
            "units_total": len(all_units),
            "correct_both_units": len(correct_both),
            "correct_both_clusters": len({r["cluster_id"] for r in correct_both}),
            "fraction": len(correct_both) / len(all_units) if all_units else 0.0,
            "floor": floor,
            "meets_the_floor": meets,
        },

        "mandatory_per_position_report": {
            "why_it_is_mandatory": (
                "correct-both filtering is a selection, and source-line position "
                "is the only free confound the BRIDGE equal-length identity does "
                "not eliminate; without the before-and-after comparison the "
                "selection bias returns unnoticed"
            ),
            "accuracy_by_position_all_items": accuracy_by_position(items_before),
            "position_counts_before_filtering": before_dist,
            "position_counts_after_filtering": after_dist,
            "position_share_shift": shift,
            "worst_absolute_share_shift": worst_shift,
            "how_to_read_the_shift": (
                "each entry is the change in a position's SHARE of the surviving "
                "items; a large positive value at an early position would mean "
                "the filter had concentrated the analysis there"
            ),
            "position_control_applied_at_build_time": obj["position_control"][
                "realised_distribution_over_items"
            ],
        },

        "predecessor_comparison_reported_only": {
            "note": "P-0c's per-position accuracy, for context; it sets no threshold here",
            "p0c": {"0": 1.0, "1": 0.7917, "2": 0.6552, "3": 0.5645, "4": 0.7209, "5": 0.8125},
        },

        "consequence": (
            "the floor is met and the object may serve as the selection set"
            if meets
            else "the floor is NOT met; stop and report"
        ),
        "correct_both_units_detail": correct_both,
        "claim_ceiling": "An inclusion count. It licenses no claim of any kind.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(f"units total          : {len(all_units)}")
    print(f"correct-both units   : {len(correct_both)}  floor {floor}  -> "
          f"{'PASS' if meets else 'FAIL'}")
    print(f"correct-both clusters: {len({r['cluster_id'] for r in correct_both})}")
    print("\naccuracy by registration-line position, all items:")
    for position, stats in report["mandatory_per_position_report"][
        "accuracy_by_position_all_items"
    ].items():
        print(f"  position {position}: {stats['correct']:3}/{stats['n']:3} = "
              f"{stats['accuracy']:.4f}")
    print("\nposition share, before -> after correct-both filtering:")
    for position, stats in shift.items():
        print(
            f"  position {position}: {stats['share_before']:.4f} -> "
            f"{stats['share_after']:.4f}  ({stats['change']:+.4f})"
        )
    print(f"\nworst absolute share shift: {worst_shift:.4f}")
    if not meets:
        print("P0C2-CHECK-INCLUSION FAILED", file=sys.stderr)
        return 1
    print("P0C2-CHECK-INCLUSION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
