"""OD-011 non-vacuity demonstration for the P-0 decision rule.

OD-011: a check must carry a demonstrated failing case, or it counts as not
implemented. This file demonstrates both directions, because either one alone
leaves a hole:

  * fed a null, pure noise, or an all-zero curve, the rule must return
    NOT_CAUSALLY_USED - otherwise it manufactures a positive out of nothing;
  * fed a strong localised curve, it must return CAUSALLY_USED - otherwise it
    is a rule that always says no, which is equally uninformative and would
    have made the whole measurement decorative.

The demonstration runs on SYNTHETIC curves with a registered seed, so it can be
completed before any real measurement exists. That ordering is the requirement:
a criterion that has not been shown capable of failing may not be pointed at
real data.

A second, confirmatory pass is registered for after the measurement, using the
real null ensemble in place of the synthetic one. It cannot change the verdict
and cannot change the rule; it exists because a synthetic null is only as good
as the dispersion assumed for it.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent

#: Registered synthetic-ensemble parameters.
DEMO_SEED = 20260829
DEMO_CLUSTERS = 95
DEMO_SITES = ("CUE", "BRIDGE", "READOUT")
DEMO_LAYERS = list(range(-1, 28))
DEMO_NULL_SIGMAS = (0.05, 0.15)
DEMO_REPLICATES = 5

#: The strong case: a localised band with a plausible magnitude.
DEMO_SIGNAL_LAYERS = (12, 13, 14, 15, 16)
DEMO_SIGNAL_MEAN = 0.45
DEMO_SIGNAL_SIGMA = 0.15


def load_decider():
    spec = importlib.util.spec_from_file_location("p0_decider", TOOLS / "decide_p0.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["p0_decider"] = module
    spec.loader.exec_module(module)
    return module


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def clusters() -> list[str]:
    return [f"c{index:03d}" for index in range(DEMO_CLUSTERS)]


def gaussian_series(rng: random.Random, mean: float, sigma: float) -> dict:
    return {
        cluster: [rng.gauss(mean, sigma), rng.gauss(mean, sigma)]
        for cluster in clusters()
    }


def constant_series(value: float) -> dict:
    return {cluster: [value, value] for cluster in clusters()}


def build_null_ensemble(rng: random.Random) -> dict:
    ensemble: dict = {}
    for replicate in range(DEMO_REPLICATES):
        for family, sigma in (("NULL_C", DEMO_NULL_SIGMAS[0]), ("NULL_R", DEMO_NULL_SIGMAS[1])):
            key = f"{family}_{replicate}"
            ensemble[key] = {
                site: {
                    str(layer): gaussian_series(rng, 0.0, sigma)
                    for layer in DEMO_LAYERS
                }
                for site in DEMO_SITES
            }
    return ensemble


def case_curves(name: str, rng: random.Random, ensemble: dict) -> dict:
    """One demonstration case: a REAL series placed beside the shared nulls."""
    if name == "the_null_itself":
        real = json.loads(json.dumps(ensemble["NULL_C_0"]))
    elif name == "pure_noise":
        real = {
            site: {
                str(layer): gaussian_series(rng, 0.0, DEMO_NULL_SIGMAS[1])
                for layer in DEMO_LAYERS
            }
            for site in DEMO_SITES
        }
    elif name == "all_zero":
        real = {
            site: {str(layer): constant_series(0.0) for layer in DEMO_LAYERS}
            for site in DEMO_SITES
        }
    elif name == "strong_localised_effect":
        real = {}
        for site in DEMO_SITES:
            real[site] = {}
            for layer in DEMO_LAYERS:
                if site == "BRIDGE" and layer in DEMO_SIGNAL_LAYERS:
                    real[site][str(layer)] = gaussian_series(
                        rng, DEMO_SIGNAL_MEAN, DEMO_SIGNAL_SIGMA
                    )
                else:
                    real[site][str(layer)] = gaussian_series(
                        rng, 0.0, DEMO_NULL_SIGMAS[0]
                    )
    else:
        raise RuntimeError(f"unregistered demonstration case {name}")

    curves = {"REAL": real}
    curves.update(json.loads(json.dumps(ensemble)))
    return curves


REQUIRED = {
    "the_null_itself": "NOT_CAUSALLY_USED",
    "pure_noise": "NOT_CAUSALLY_USED",
    "all_zero": "NOT_CAUSALLY_USED",
    "strong_localised_effect": "CAUSALLY_USED",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--real-nulls",
        help=(
            "optional: a measured curves file whose null constructions replace "
            "the synthetic ensemble, for the registered confirmatory pass"
        ),
    )
    args = parser.parse_args()

    decider = load_decider()
    rng = random.Random(DEMO_SEED)

    if args.real_nulls:
        measured = json.loads(Path(args.real_nulls).read_text(encoding="utf-8"))["curves"]
        ensemble = {
            key: {
                site: by_layer
                for site, by_layer in value.items()
                if site in DEMO_SITES
            }
            for key, value in measured.items()
            if key != "REAL"
        }
        source = "measured null constructions"
    else:
        ensemble = build_null_ensemble(rng)
        source = "synthetic ensemble"

    null_keys = sorted(ensemble)
    cases: dict = {}
    all_passed = True
    for name, required in REQUIRED.items():
        curves = case_curves(name, rng, ensemble)
        summary = decider.summarise_curves(curves)
        outcome = decider.decide(summary, "REAL", null_keys)
        passed = outcome["verdict"] == required
        all_passed = all_passed and passed
        cases[name] = {
            "must_be": required,
            "verdict": outcome["verdict"],
            "layers_above_ceiling": outcome["layers_above_ceiling"],
            "ceiling": outcome["ceiling"],
            "passed": passed,
        }
        print(
            f"  {name:26} must_be={required:18} got={outcome['verdict']:18} "
            f"{'PASS' if passed else 'FAIL'}"
        )

    report = {
        "schema_version": "study5-p0-non-vacuity-v1",
        "rule": "OD-011",
        "decision_rule_under_test": "tools/decide_p0.py",
        "null_source": source,
        "seed": DEMO_SEED,
        "clusters": DEMO_CLUSTERS,
        "layers": DEMO_LAYERS,
        "sites": list(DEMO_SITES),
        "null_sigmas": list(DEMO_NULL_SIGMAS),
        "signal_layers": list(DEMO_SIGNAL_LAYERS),
        "signal_mean": DEMO_SIGNAL_MEAN,
        "cases": cases,
        "all_passed": all_passed,
        "meaning": (
            "the rule does not manufacture a positive from a null, from noise "
            "or from an empty curve, and it is still able to return a positive "
            "when one is present; both directions are required, because a rule "
            "that can only say no is as uninformative as one that can only say "
            "yes"
        ),
        "proven_before_any_real_curve_was_judged": args.real_nulls is None,
        "claim_ceiling": "A governance demonstration. It licenses no claim.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))
    if not all_passed:
        print("P0-CHECK-NON-VACUITY FAILED", file=sys.stderr)
        return 1
    print("P0-CHECK-NON-VACUITY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
