"""P-0c-2 step 7: the OD-022 clean-run destruction sweep, over the closed shortlist.

OD-022 requires that a candidate estimand's value under a PURELY DESTRUCTIVE
patch be computed from clean runs alone, and reported, before the candidate may
be registered. A candidate that is not approximately zero under pure destruction
is out. It is not repaired.

The substitution
----------------
A destroyed residual state carries no information about which answer token is
which. The model's output at that position therefore tends toward a distribution
that does not distinguish them - in the limit, the model's own prior over the
answer vocabulary, with the cue-specific structure gone. That limit is what is
substituted, and every candidate is evaluated against it on the SAME clean runs.

Nothing here is patched, nothing is on a GPU, and no candidate has been given
a threshold from any measured effect. The sweep is the cheapest possible way to
learn that a formula cannot do the job, and it has already killed two natural
families before either cost a forward pass.

The four candidates are read from the closed shortlist. They may not be added
to, removed from, or repaired.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

#: Registered sweep parameters. Fixed before any candidate was evaluated.
SWEEP_SEED = 20260829
SWEEP_DRAWS = 20000

#: How "approximately zero" is decided, without inventing a numeric tolerance
#: for the estimate itself: the sweep's central 95 percent must contain zero,
#: and the mean must be small relative to the unit scale the estimand is
#: normalised on. Both are registered here, before any candidate is run.
MEAN_TOLERANCE = 0.05


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def percentile(sorted_values, pct):
    if not sorted_values:
        raise RuntimeError("empty sample")
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] * (1.0 - frac) + sorted_values[high] * frac


def softmax(logits):
    top = max(logits)
    exps = [math.exp(v - top) for v in logits]
    total = sum(exps)
    return [v / total for v in exps]


def draw_clean_world(rng, vocab=9):
    """One unit's clean runs, as answer-vocabulary logits.

    The recipient's clean run prefers a_R and the donor's prefers a_D, which is
    the only structural fact any candidate depends on and is a property of the
    task rather than of this data: an item the model answers correctly is by
    definition one whose clean run prefers its own answer.
    """
    base = [rng.gauss(0.0, 2.0) for _ in range(vocab)]
    i_d, i_r = 0, 1
    preference = rng.uniform(3.0, 10.0)

    recipient = list(base)
    recipient[i_r] += preference
    donor = list(base)
    donor[i_d] += preference
    return donor, recipient, i_d, i_r


def destroyed(recipient, rng, kind):
    """The output after a patch that carries no answer information.

    Two constructions, because "destroyed" is not a single thing and a candidate
    that survives only one of them has not survived:

      flatten   the cue-specific structure is gone and the distribution tends
                toward uniform over the answer vocabulary
      resample  the state is replaced by an unrelated in-distribution state, so
                the logits are a fresh draw with no relation to either answer
    """
    if kind == "flatten":
        return [0.0 for _ in recipient]
    if kind == "resample":
        return [rng.gauss(0.0, 2.0) for _ in recipient]
    raise RuntimeError(kind)


# ---------------------------------------------------------------- candidates

def c1_null_subtracted(donor, recipient, patched, i_d, i_r, null_patched):
    """C1: measure destruction explicitly and subtract it.

    raw is the logit difference; the subtrahend is the same raw quantity under a
    destructive patch, estimated on the same unit.
    """
    def raw(logits):
        return logits[i_d] - logits[i_r]

    numerator = raw(patched) - raw(null_patched)
    denominator = raw(donor) - raw(recipient)
    return numerator / denominator


def c2_matched_control(donor, recipient, patched, i_d, i_r, null_patched):
    """C2: deduct the flattening term using probability-matched control tokens."""
    p_clean = softmax(recipient)
    p_patch = softmax(patched)
    target = p_clean[i_d]
    controls = sorted(
        (k for k in range(len(recipient)) if k not in (i_d, i_r)),
        key=lambda k: abs(p_clean[k] - target),
    )[:3]
    rise_d = math.log(max(p_patch[i_d], 1e-12)) - math.log(max(p_clean[i_d], 1e-12))
    rise_c = sum(
        math.log(max(p_patch[k], 1e-12)) - math.log(max(p_clean[k], 1e-12))
        for k in controls
    ) / len(controls)
    p_full = softmax(donor)
    scale = math.log(max(p_full[i_d], 1e-12)) - math.log(max(p_clean[i_d], 1e-12))
    return (rise_d - rise_c) / scale if abs(scale) > 1e-9 else 0.0


def c3_rank(donor, recipient, patched, i_d, i_r, null_patched):
    """C3: improvement in the rank of a_D, normalised on the donor's clean run."""
    def rank_of(logits, index):
        return sum(1 for v in logits if v > logits[index])

    r_clean = rank_of(recipient, i_d)
    r_patch = rank_of(patched, i_d)
    r_full = rank_of(donor, i_d)
    denominator = r_clean - r_full
    return (r_clean - r_patch) / denominator if denominator else 0.0


def c4_two_sided_margin(donor, recipient, patched, i_d, i_r, null_patched):
    """C4: the share p(a_D)/(p(a_D)+p(a_R)), rescaled to clean endpoints."""
    def share(logits):
        a = math.exp(logits[i_d] - max(logits))
        b = math.exp(logits[i_r] - max(logits))
        return a / (a + b) if (a + b) > 0 else 0.5

    s_clean = share(recipient)
    s_full = share(donor)
    denominator = s_full - s_clean
    return (share(patched) - s_clean) / denominator if abs(denominator) > 1e-9 else 0.0


CANDIDATES = {
    "C1_null_subtracted": c1_null_subtracted,
    "C2_matched_control_contrast": c2_matched_control,
    "C3_rank": c3_rank,
    "C4_two_sided_margin": c4_two_sided_margin,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shortlist", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    shortlist = json.loads(Path(args.shortlist).read_text(encoding="utf-8"))
    declared = set(shortlist["the_candidates"])
    if set(CANDIDATES) != declared:
        print(
            f"the implemented candidates {sorted(CANDIDATES)} do not match the "
            f"closed shortlist {sorted(declared)}",
            file=sys.stderr,
        )
        return 1

    results: dict[str, dict] = {}
    for name, fn in sorted(CANDIDATES.items()):
        per_kind: dict[str, dict] = {}
        for kind in ("flatten", "resample"):
            rng = random.Random(SWEEP_SEED)
            values = []
            for _ in range(SWEEP_DRAWS):
                donor, recipient, i_d, i_r = draw_clean_world(rng)
                dead = destroyed(recipient, rng, kind)
                # the null subtrahend C1 uses is itself a destructive patch,
                # drawn independently so the candidate is not handed its own
                # answer
                null_patched = destroyed(recipient, rng, kind)
                values.append(fn(donor, recipient, dead, i_d, i_r, null_patched))
            values.sort()
            mean = sum(values) / len(values)
            lo = percentile(values, 2.5)
            hi = percentile(values, 97.5)
            per_kind[kind] = {
                "mean": mean,
                "p2_5": lo,
                "p97_5": hi,
                "min": values[0],
                "max": values[-1],
                "fraction_at_or_below_zero": sum(1 for v in values if v <= 0.0)
                / len(values),
                "interval_contains_zero": lo <= 0.0 <= hi,
                "mean_within_tolerance": abs(mean) <= MEAN_TOLERANCE,
            }

        survives = all(
            k["interval_contains_zero"] and k["mean_within_tolerance"]
            for k in per_kind.values()
        )
        results[name] = {
            "per_destruction_kind": per_kind,
            "survives": survives,
            "why_it_might_survive": shortlist["the_candidates"][name][
                "why_it_might_survive"
            ],
            "known_risk_stated_in_advance": shortlist["the_candidates"][name][
                "known_risk_stated_in_advance"
            ],
        }
        for kind, stats in per_kind.items():
            print(
                f"  {name:28} {kind:9} mean {stats['mean']:+.6f}  "
                f"95% [{stats['p2_5']:+.4f}, {stats['p97_5']:+.4f}]  "
                f"frac<=0 {stats['fraction_at_or_below_zero']:.4f}"
            )
        print(f"  {name:28} -> {'SURVIVES' if survives else 'ELIMINATED'}\n")

    survivors = sorted(n for n, r in results.items() if r["survives"])
    report = {
        "schema_version": "study5-p0c2-od022-sweep-v1",
        "rule": "OD-022",
        "phase": "P-0c-2",
        "shortlist_is_closed": True,
        "candidates_evaluated": sorted(CANDIDATES),
        "candidates_added": 0,
        "candidates_repaired": 0,
        "sweep": {
            "seed": SWEEP_SEED,
            "draws": SWEEP_DRAWS,
            "destruction_kinds": ["flatten", "resample"],
            "why_two_kinds": (
                "destroyed is not a single thing, and a candidate that survives "
                "only one construction has not survived"
            ),
            "mean_tolerance": MEAN_TOLERANCE,
            "uses_any_patched_data": False,
            "uses_any_gpu": False,
            "uses_any_measured_effect_as_a_threshold": False,
        },
        "results": results,
        "survivors": survivors,
        "n_survivors": len(survivors),
        "eliminated": sorted(n for n, r in results.items() if not r["survives"]),
        "all_candidate_numbers_are_reported_including_the_eliminated": True,
        "claim_ceiling": "A governance sweep. It licenses no claim of any kind.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(f"survivors: {survivors}")
    if not survivors:
        print("P0C2-CHECK-OD022 NO SURVIVORS", file=sys.stderr)
        return 1
    print("P0C2-CHECK-OD022 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
