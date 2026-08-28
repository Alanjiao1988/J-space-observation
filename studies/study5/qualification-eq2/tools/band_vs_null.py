"""Band extraction against a matched-norm random-lens null (OA-004).

Replaces OD-015's scale-free rule, which produced a band on any profile with an
interior peak, including a small signal or pure noise.

    band = the longest contiguous mid-depth run of layers whose readrate
           significantly exceeds the random-lens null upper confidence bound

The null ceiling is the MAXIMUM over at least 5 independent random lenses of
their per-layer upper confidence bounds, which is the conservative direction:
taking the maximum makes the null harder to beat.

OA-004 revision 3 requires non-vacuity to be DEMONSTRATED before this criterion
touches real data. `demonstrate_non_vacuity()` is that gate, and `main()` refuses
to run without it.

Confidence bounds use the Wilson score interval, which is well behaved at the
very small proportions this measurement produces; the normal approximation is
not, and would give a nonsensical interval at readrate 0.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

CONFIDENCE = 0.95
Z = 1.959963984540054  # two-sided 95%
MIN_NULL_REPLICATES = 5

#: Mid-depth requirement: the band must not begin at the very first layer nor
#: end at the very last, since a run touching an endpoint is what a monotone
#: trend looks like rather than a band.
def is_mid_depth(band: list[int], layers: list[int]) -> bool:
    if not band:
        return False
    return band[0] > layers[0] and band[-1] < layers[-1]


def wilson_bounds(successes: int, trials: int, z: float = Z) -> tuple[float, float]:
    """Wilson score interval. Returns (lower, upper).

    At successes = 0 this gives (0, something positive), which is the behaviour
    the null needs: an unobserved event still has a non-zero upper bound, so a
    single lucky hit in the real profile cannot clear it trivially.
    """
    if trials <= 0:
        return 0.0, 1.0
    phat = successes / trials
    denom = 1.0 + z * z / trials
    centre = (phat + z * z / (2 * trials)) / denom
    margin = (
        z
        * math.sqrt(phat * (1 - phat) / trials + z * z / (4 * trials * trials))
        / denom
    )
    return max(0.0, centre - margin), min(1.0, centre + margin)


def longest_contiguous_run(flags: list[bool], layers: list[int]) -> list[int]:
    best: list[int] = []
    current: list[int] = []
    for flag, layer in zip(flags, layers, strict=True):
        if flag:
            current.append(layer)
            if len(current) > len(best):
                best = list(current)
        else:
            current = []
    return best


def null_ceiling(
    null_profiles: list[list[dict]], trials: int
) -> dict[int, float]:
    """Per-layer null ceiling: the max over replicates of each upper bound."""
    if len(null_profiles) < MIN_NULL_REPLICATES:
        raise ValueError(
            f"OA-004 requires at least {MIN_NULL_REPLICATES} null replicates, "
            f"got {len(null_profiles)}"
        )
    ceiling: dict[int, float] = {}
    for profile in null_profiles:
        for point in profile:
            layer = int(point["layer"])
            hits = int(point["hits"])
            _lo, hi = wilson_bounds(hits, trials)
            ceiling[layer] = max(ceiling.get(layer, 0.0), hi)
    return ceiling


def extract_band(
    real_profile: list[dict],
    null_profiles: list[list[dict]],
    trials: int,
) -> dict:
    """Apply the OA-004 criterion. Chooses nothing."""
    layers = [int(p["layer"]) for p in real_profile]
    ceiling = null_ceiling(null_profiles, trials)

    per_layer = []
    flags = []
    for point in real_profile:
        layer = int(point["layer"])
        hits = int(point["hits"])
        rate = float(point["readrate"])
        lo, _hi = wilson_bounds(hits, trials)
        cap = ceiling[layer]
        # Significant means the real lower bound clears the null ceiling, so the
        # two intervals do not overlap.
        significant = lo > cap
        flags.append(significant)
        per_layer.append(
            {
                "layer": layer,
                "readrate": rate,
                "hits": hits,
                "real_lower_bound": lo,
                "null_ceiling": cap,
                "significant": significant,
            }
        )

    band = longest_contiguous_run(flags, layers)
    mid_depth = is_mid_depth(band, layers)

    return {
        "band": band if mid_depth else [],
        "raw_longest_significant_run": band,
        "band_length": len(band) if mid_depth else 0,
        "mid_depth": mid_depth,
        "band_exists": bool(band) and mid_depth,
        "significant_layers": [p["layer"] for p in per_layer if p["significant"]],
        "n_significant_layers": sum(flags),
        "trials": trials,
        "confidence": CONFIDENCE,
        "null_replicates": len(null_profiles),
        "per_layer": per_layer,
        "reason": (
            "band significantly exceeds the matched-norm random-lens null"
            if (band and mid_depth)
            else "no contiguous mid-depth run clears the null ceiling"
        ),
    }


# --------------------------------------------------------------------------
# OA-004 revision 3: non-vacuity, demonstrated before any real data is touched
# --------------------------------------------------------------------------


def _profile(rates: list[float], trials: int) -> list[dict]:
    return [
        {"layer": i, "readrate": r, "hits": int(round(r * trials))}
        for i, r in enumerate(rates)
    ]


def demonstrate_non_vacuity(trials: int = 900, seed: int = 20260828) -> dict:
    """Three negative cases that must all yield NO band.

    Until these pass, the criterion may not be applied to any real profile.
    """
    rng = random.Random(seed)
    n_layers = 27
    cases = {}

    # Case 1: a random lens's own profile, judged against random-lens nulls.
    # This is the sharpest case: the thing under test is drawn from the same
    # distribution as the null, so a criterion that flags it is vacuous.
    base_rate = 0.002
    subject = _profile(
        [max(0.0, rng.gauss(base_rate, base_rate * 0.5)) for _ in range(n_layers)],
        trials,
    )
    nulls = [
        _profile(
            [max(0.0, rng.gauss(base_rate, base_rate * 0.5)) for _ in range(n_layers)],
            trials,
        )
        for _ in range(MIN_NULL_REPLICATES)
    ]
    cases["random_lens_own_profile"] = extract_band(subject, nulls, trials)

    # Case 2: pure noise, judged against the same nulls.
    noise = _profile(
        [max(0.0, rng.gauss(base_rate, base_rate)) for _ in range(n_layers)], trials
    )
    cases["pure_noise_profile"] = extract_band(noise, nulls, trials)

    # Case 3: an all-zero profile.
    zeros = _profile([0.0] * n_layers, trials)
    cases["all_zero_profile"] = extract_band(zeros, nulls, trials)

    passed = all(not c["band_exists"] for c in cases.values())
    return {
        "rule": "OA-004 revision 3",
        "trials": trials,
        "seed": seed,
        "null_replicates": MIN_NULL_REPLICATES,
        "cases": {
            name: {
                "band_exists": c["band_exists"],
                "band": c["band"],
                "n_significant_layers": c["n_significant_layers"],
                "must_be": "no band",
                "passed": not c["band_exists"],
            }
            for name, c in cases.items()
        },
        "all_passed": passed,
        "meaning": (
            "the criterion is not vacuous: it does not manufacture a band from a "
            "random lens, from noise, or from an empty profile"
        ),
        "proven_before_any_real_profile_was_judged": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demonstrate-only", action="store_true")
    parser.add_argument("--real")
    parser.add_argument("--null", action="append", default=[])
    parser.add_argument("--role")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    # The gate. It runs on every invocation, not only when asked.
    demo = demonstrate_non_vacuity()
    for name, case in demo["cases"].items():
        print(f"  non-vacuity {name:26} band_exists={case['band_exists']}  "
              f"{'PASS' if case['passed'] else 'FAIL'}")
    if not demo["all_passed"]:
        Path(args.out).write_text(
            json.dumps(demo, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print("EQ2-CHECK-NON-VACUITY FAILED", file=sys.stderr)
        return 1
    print("EQ2-CHECK-NON-VACUITY PASSED")

    if args.demonstrate_only:
        Path(args.out).write_text(
            json.dumps(demo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        return 0

    if not args.real or not args.null:
        raise SystemExit("--real and at least one --null are required")

    real_report = json.loads(Path(args.real).read_text(encoding="utf-8"))
    real_profile = real_report["pooled_profile"]["1"]
    trials = int(real_report["pooled_scored_intermediates"])

    null_profiles = []
    for path in args.null:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        null_profiles.append(report["pooled_profile"]["1"])

    result = extract_band(real_profile, null_profiles, trials)
    result["role"] = args.role
    result["rule"] = "OA-004"
    result["supersedes"] = "OD-015"
    result["non_vacuity"] = demo
    result["claim_ceiling"] = "A band extraction. It licenses no claim of any kind."

    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(
        f"{args.role}: band={result['band']} exists={result['band_exists']} "
        f"significant_layers={result['significant_layers']}"
    )
    print(f"EQ2-CHECK-BAND-VS-NULL-{args.role} PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
