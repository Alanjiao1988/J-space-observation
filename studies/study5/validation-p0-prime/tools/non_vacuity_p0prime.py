"""P-0' non-vacuity: the four registered synthetic cases for a candidate estimand.

The directive requires four cases, all on synthetic or constructed objects, none
of them permitted to take a threshold from P-0's existing data:

  1  no-op patch                      -> exactly 0
  2  random-vector patch              -> approximately 0
  3  full-donor-run patch             -> 1
  4  a construction that genuinely carries the intermediate -> significantly positive

Case 2 is the whole reason a replacement was ordered, so it is the case that has
to be shown passing rather than assumed.

The tool takes the estimand as an argument rather than hard-coding one, so a
candidate can be tested BEFORE it is adopted rather than after it has produced a
curve. That ordering is the point: an estimand whose discriminating property is
only checked once real profiles exist cannot be distinguished from an estimand
chosen because those profiles came out well.

The synthetic world
-------------------
A residual state in R^d and a set of answer directions, nothing else. The
recipient's clean state is built so its own answer outranks the donor's, and the
donor's clean state the other way round. That single structural fact is all any
of the four cases depends on, and it is a fact about the task rather than about
this data: an item the model gets right is by definition one where the clean run
prefers its own answer.

"Approximately zero" is formalised without inventing a tolerance: the
construction's 95 percent cluster-bootstrap interval must contain zero at every
layer. A registered numeric tolerance would have been a number I chose, and a
number chosen after the failure it is meant to judge is not evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
P0_TOOLS = TOOLS.parent.parent / "validation-p0" / "tools"

#: Registered synthetic-world parameters. Fixed before any case is run and not
#: derived from any P-0 artifact.
DEMO_SEED = 20260829
D_MODEL = 64
N_UNITS = 200
N_LAYERS = 8

#: How strongly a clean state prefers its own answer, in logits. Chosen to be
#: unremarkable rather than tuned; the analytic sweep at the end shows the
#: conclusion does not depend on the value.
PREFERENCE = 6.0

#: Case 4's construction carries this fraction of the donor state.
CARRY_FRACTION = 0.6

REQUIRED = {
    "case_1_no_op": "EXACTLY_ZERO",
    "case_2_random_vector": "APPROXIMATELY_ZERO",
    "case_3_full_donor": "ONE",
    "case_4_carries_the_intermediate": "SIGNIFICANTLY_POSITIVE",
}

EXACT_TOLERANCE = 1e-12
ONE_TOLERANCE = 1e-6


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load_decider():
    spec = importlib.util.spec_from_file_location(
        "p0p_decider", P0_TOOLS / "decide_p0.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["p0p_decider"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------- the estimand

def estimand_logit_difference_recovery(l_clean: float, l_patch: float,
                                       l_full: float) -> float:
    """The estimand the directive prescribes.

        effect = (L_patch - L_clean) / (L_full - L_clean)

    where each L is a logit DIFFERENCE, donor answer minus recipient answer,
    taken in the run named by the subscript.
    """
    return (l_patch - l_clean) / (l_full - l_clean)


ESTIMANDS = {
    "logit_difference_recovery": estimand_logit_difference_recovery,
}


# ------------------------------------------------------------ synthetic world

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def unit_vector(rng, d):
    v = [rng.gauss(0.0, 1.0) for _ in range(d)]
    length = norm(v) or 1.0
    return [x / length for x in v]


def build_world(rng):
    """One donor/recipient state pair per unit, each with its own answer directions.

    Per-unit directions mean the four cases are averaged over a population
    rather than read off a single hand-built example.
    """
    world = []
    for _ in range(N_UNITS):
        dir_donor = unit_vector(rng, D_MODEL)
        dir_recipient = unit_vector(rng, D_MODEL)
        background = unit_vector(rng, D_MODEL)
        scale = rng.uniform(0.6, 1.6)
        world.append(
            {
                "dir_donor": dir_donor,
                "dir_recipient": dir_recipient,
                "state_recipient": [
                    scale * (PREFERENCE * dir_recipient[i] + background[i])
                    for i in range(D_MODEL)
                ],
                "state_donor": [
                    scale * (PREFERENCE * dir_donor[i] + background[i])
                    for i in range(D_MODEL)
                ],
            }
        )
    return world


def logit_gap(unit, state):
    """logit(donor answer) - logit(recipient answer) for one state."""
    return dot(state, unit["dir_donor"]) - dot(state, unit["dir_recipient"])


def patched_state(case, unit, rng):
    if case == "case_1_no_op":
        return list(unit["state_recipient"])
    if case == "case_3_full_donor":
        return list(unit["state_donor"])
    if case == "case_2_random_vector":
        raw = [rng.gauss(0.0, 1.0) for _ in range(D_MODEL)]
        factor = norm(unit["state_recipient"]) / (norm(raw) or 1.0)
        return [x * factor for x in raw]
    if case == "case_4_carries_the_intermediate":
        return [
            (1.0 - CARRY_FRACTION) * unit["state_recipient"][i]
            + CARRY_FRACTION * unit["state_donor"][i]
            for i in range(D_MODEL)
        ]
    raise RuntimeError(f"unregistered case {case}")


def run_case(case, world, estimand, rng):
    """Effect values for one case, keyed by cluster, at every synthetic layer."""
    by_layer: dict[str, dict[str, list[float]]] = {}
    for layer in range(N_LAYERS):
        bucket: dict[str, list[float]] = {}
        for index, unit in enumerate(world):
            l_clean = logit_gap(unit, unit["state_recipient"])
            l_full = logit_gap(unit, unit["state_donor"])
            l_patch = logit_gap(unit, patched_state(case, unit, rng))
            bucket[f"c{index:04d}"] = [estimand(l_clean, l_patch, l_full)]
        by_layer[str(layer)] = bucket
    return by_layer


def judge(case, stats):
    """Verdict for one case against its registered requirement."""
    required = REQUIRED[case]
    means = [s["mean"] for s in stats.values()]
    worst = max(abs(m) for m in means)
    contains_zero = all(s["lcb"] <= 0.0 <= s["ucb"] for s in stats.values())

    if required == "EXACTLY_ZERO":
        passed = worst <= EXACT_TOLERANCE
        detail = f"worst |mean| {worst:.3e} against {EXACT_TOLERANCE:.0e}"
    elif required == "APPROXIMATELY_ZERO":
        passed = contains_zero
        detail = (
            f"worst |mean| {worst:.6f}; every layer's 95% interval contains "
            f"zero: {contains_zero}"
        )
    elif required == "ONE":
        worst_from_one = max(abs(m - 1.0) for m in means)
        passed = worst_from_one <= ONE_TOLERANCE
        detail = f"worst |mean - 1| {worst_from_one:.3e} against {ONE_TOLERANCE:.0e}"
    elif required == "SIGNIFICANTLY_POSITIVE":
        smallest = min(s["lcb"] for s in stats.values())
        passed = smallest > 0.0
        detail = f"smallest lower bound {smallest:.6f}, required strictly above zero"
    else:
        raise RuntimeError(required)

    return passed, detail, worst, contains_zero


def analytic_note(estimand):
    """What the estimand does to a patch that destroys the state, in closed form.

    A destroyed state carries no information about which answer token is which,
    so its expected logit gap is zero. Substituting L_patch = 0 leaves a value
    that depends only on the two clean runs, and it is not zero.
    """
    rng = random.Random(DEMO_SEED + 1)
    samples = [
        estimand(-rng.uniform(1.0, 15.0), 0.0, rng.uniform(1.0, 15.0))
        for _ in range(20000)
    ]
    return {
        "substitution": (
            "L_patch = 0, the expected gap of a state carrying no information "
            "about which answer token is which"
        ),
        "closed_form": "effect = -L_clean / (L_full - L_clean)",
        "why_L_clean_is_negative": (
            "in its own clean run the recipient prefers its own answer, so "
            "logit(donor answer) - logit(recipient answer) is below zero"
        ),
        "consequence": (
            "the numerator is positive and the denominator is positive, so a "
            "patch that destroys the state produces a POSITIVE effect, not zero"
        ),
        "sweep_over_plausible_clean_runs": {
            "L_clean_range": [-15.0, -1.0],
            "L_full_range": [1.0, 15.0],
            "draws": len(samples),
            "min": min(samples),
            "mean": sum(samples) / len(samples),
            "max": max(samples),
            "fraction_at_or_below_zero": (
                sum(1 for s in samples if s <= 0.0) / len(samples)
            ),
        },
        "the_sweep_uses_no_P0_data": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--estimand", default="logit_difference_recovery")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    decider = load_decider()
    estimand = ESTIMANDS[args.estimand]
    world = build_world(random.Random(DEMO_SEED))

    cases: dict[str, dict] = {}
    all_passed = True
    for offset, case in enumerate(REQUIRED):
        curves = run_case(case, world, estimand, random.Random(DEMO_SEED + offset))
        stats = {
            layer: decider.cluster_bootstrap(bucket, resamples=2000, seed=DEMO_SEED)
            for layer, bucket in curves.items()
        }
        passed, detail, worst, contains_zero = judge(case, stats)
        all_passed = all_passed and passed
        cases[case] = {
            "must_be": REQUIRED[case],
            "pooled_mean_per_layer": {k: v["mean"] for k, v in stats.items()},
            "worst_abs_mean": worst,
            "every_layer_interval_contains_zero": contains_zero,
            "detail": detail,
            "passed": passed,
        }
        print(
            f"  {case:34} must_be={REQUIRED[case]:24} "
            f"{'PASS' if passed else 'FAIL'}   {detail}"
        )

    report = {
        "schema_version": "study5-p0prime-non-vacuity-v1",
        "rule": "OD-011, as revised to require a must-return-positive case",
        "estimand_under_test": args.estimand,
        "estimand_formula": "(L_patch - L_clean) / (L_full - L_clean)",
        "world": {
            "seed": DEMO_SEED,
            "d_model": D_MODEL,
            "units": N_UNITS,
            "layers": N_LAYERS,
            "preference_logits": PREFERENCE,
            "carry_fraction": CARRY_FRACTION,
            "derived_from_any_P0_artifact": False,
            "any_threshold_taken_from_P0_data": False,
        },
        "how_approximately_zero_is_formalised": (
            "the construction's 95 percent cluster-bootstrap interval must "
            "contain zero at every layer; no numeric tolerance is invented, "
            "because a tolerance chosen after the failure it is meant to judge "
            "would not be evidence"
        ),
        "cases": cases,
        "all_passed": all_passed,
        "analytic": analytic_note(estimand),
        "claim_ceiling": "A governance demonstration. It licenses no claim.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print()
    note = report["analytic"]
    print(f"analytic: {note['closed_form']}")
    sweep = note["sweep_over_plausible_clean_runs"]
    print(
        f"  over {sweep['draws']} plausible clean-run pairs: min "
        f"{sweep['min']:.4f}, mean {sweep['mean']:.4f}, max {sweep['max']:.4f}, "
        f"fraction <= 0: {sweep['fraction_at_or_below_zero']:.4f}"
    )
    if not all_passed:
        print("P0PRIME-CHECK-NON-VACUITY FAILED", file=sys.stderr)
        return 1
    print("P0PRIME-CHECK-NON-VACUITY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
