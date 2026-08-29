"""P-0 decision rule, isolated from any measurement.

This module is a pure function of curves. It never opens a model, never reads
an evaluation set and never learns which curve came from the real measurement
and which came from a null. That isolation is the point: the OD-011 non-vacuity
demonstration feeds it a null, pure noise and an all-zero curve, and it must
return NOT_CAUSALLY_USED for all three; it feeds a synthetic strong curve and it
must return CAUSALLY_USED. A decider that could not do both would be a check
that cannot fail, which OD-011 registers as equivalent to not being implemented.

The registered rule, in full:

  * the estimand at each (site, layer) is the mean over units of normalised
    restoration;
  * uncertainty is a nonparametric CLUSTER bootstrap: the resampling unit is
    the unordered pair, so both directions of a pair move together;
  * the ceiling C is the largest 97.5th bootstrap percentile observed over
    every null construction, every replicate, every site and every layer;
  * the verdict is CAUSALLY_USED if and only if some layer of the DECISIVE
    site has a 2.5th bootstrap percentile strictly greater than C;
  * the reported layer set is exactly those layers.

The ceiling is a single scalar taken as a maximum over everything, which is the
conservative direction: it is harder to exceed than a per-layer ceiling would
be. That choice is registered here rather than argued for later.

OD-011: failing cases in tests/test_p0_decider.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

#: Registered confidence level. 95 percent two-sided is the statistical
#: convention; it is not fitted to anything in this study.
CONFIDENCE = 0.95
LOWER_PERCENTILE = 2.5
UPPER_PERCENTILE = 97.5

#: Registered bootstrap size and seed.
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20260829

#: The site the verdict is read from. CUE and READOUT are measured and reported
#: but cannot decide: both are positive whether or not an intermediate exists,
#: so a rule resting on them could not return the negative verdict.
DECISIVE_SITE = "BRIDGE"

#: PREFIX is a guaranteed no-op by causal masking. It is an integrity gate, not
#: a contributor to the ceiling: including a structurally-zero, zero-variance
#: construction in a maximum can only lower the ceiling, never raise it, so
#: leaving it out is the conservative choice.
INTEGRITY_SITE = "PREFIX"
INTEGRITY_TOLERANCE = 1e-4

#: The harness gate. Patching CUE at the embedding-output layer replaces the
#: donor's embeddings at exactly the positions where the two prompts differ, so
#: the recipient run becomes token-identical to the donor run and restoration
#: must be 1. This is the passing positive control EQ2 never obtained, at the
#: level P-0 needs one: it certifies the instrument without assuming anything
#: about the model.
HARNESS_GATE_SITE = "CUE"
HARNESS_GATE_LAYER = -1
HARNESS_GATE_MIN_LCB = 0.90

VERDICT_POSITIVE = "CAUSALLY_USED"
VERDICT_NEGATIVE = "NOT_CAUSALLY_USED"


class DeciderError(RuntimeError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolated percentile of an already sorted list."""
    if not sorted_values:
        raise DeciderError("percentile of an empty sample")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] * (1.0 - frac) + sorted_values[high] * frac


def cluster_bootstrap(
    values_by_cluster: dict[str, list[float]],
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Mean, and a percentile interval, resampling clusters with replacement.

    `values_by_cluster` maps a cluster id to the observations belonging to it.
    Resampling whole CLUSTERS is what keeps the two directions of one unordered
    pair from being counted as independent evidence: a resample takes a cluster
    entire or not at all.

    The resampled statistic is the mean over all observations in the drawn
    clusters, so a cluster contributes in proportion to its size. The draw
    matrix is generated from the registered seed and depends only on the number
    of clusters, which means every series in one report is resampled along the
    same pattern - common random numbers, so differences between series are not
    contaminated by differences in the resampling noise.
    """
    import numpy as np

    clusters = sorted(values_by_cluster)
    if not clusters:
        raise DeciderError("no clusters to bootstrap")
    sums = np.array([float(sum(values_by_cluster[c])) for c in clusters])
    counts = np.array([float(len(values_by_cluster[c])) for c in clusters])
    if counts.sum() == 0:
        raise DeciderError("no observations to bootstrap")
    point = float(sums.sum() / counts.sum())

    n = len(clusters)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n, size=(resamples, n))
    means = np.sort(sums[draws].sum(axis=1) / counts[draws].sum(axis=1))
    return {
        "mean": point,
        "lcb": float(np.percentile(means, LOWER_PERCENTILE)),
        "ucb": float(np.percentile(means, UPPER_PERCENTILE)),
        "n_observations": int(counts.sum()),
        "n_clusters": n,
    }


def summarise_curves(curves: dict) -> dict:
    """Bootstrap every (construction, site, layer) series in a measurement file.

    `curves` is
        {construction: {site: {layer: {cluster_id: [restoration, ...]}}}}
    """
    summary: dict = {}
    for construction, by_site in sorted(curves.items()):
        summary[construction] = {}
        for site, by_layer in sorted(by_site.items()):
            summary[construction][site] = {}
            for layer, by_cluster in sorted(by_layer.items(), key=lambda kv: int(kv[0])):
                summary[construction][site][str(layer)] = cluster_bootstrap(by_cluster)
    return summary


def decide(summary: dict, real_key: str, null_keys: list[str]) -> dict:
    """Apply the registered rule to bootstrapped summaries."""
    if real_key not in summary:
        raise DeciderError(f"no series named {real_key!r}")
    missing = [key for key in null_keys if key not in summary]
    if missing:
        raise DeciderError(f"null constructions absent: {missing}")

    ceiling = None
    ceiling_source = None
    for key in null_keys:
        for site, by_layer in sorted(summary[key].items()):
            if site == INTEGRITY_SITE:
                continue
            for layer, stats in sorted(by_layer.items(), key=lambda kv: int(kv[0])):
                if ceiling is None or stats["ucb"] > ceiling:
                    ceiling = stats["ucb"]
                    ceiling_source = {
                        "construction": key,
                        "site": site,
                        "layer": int(layer),
                    }
    if ceiling is None:
        raise DeciderError("the null constructions produced no usable series")

    decisive = summary[real_key].get(DECISIVE_SITE)
    if decisive is None:
        raise DeciderError(f"the real series has no {DECISIVE_SITE} site")

    passing = [
        int(layer)
        for layer, stats in sorted(decisive.items(), key=lambda kv: int(kv[0]))
        if stats["lcb"] > ceiling
    ]
    verdict = VERDICT_POSITIVE if passing else VERDICT_NEGATIVE

    return {
        "verdict": verdict,
        "decisive_site": DECISIVE_SITE,
        "layers_above_ceiling": passing,
        "ceiling": ceiling,
        "ceiling_source": ceiling_source,
        "ceiling_rule": (
            "the maximum, over every null construction, every replicate, every "
            "site other than the structurally-zero integrity site, and every "
            "layer, of the upper 95 percent cluster-bootstrap bound"
        ),
        "confidence": CONFIDENCE,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "null_constructions_used": list(null_keys),
        "decisive_site_series": {
            layer: {
                "mean": stats["mean"],
                "lcb": stats["lcb"],
                "ucb": stats["ucb"],
            }
            for layer, stats in sorted(decisive.items(), key=lambda kv: int(kv[0]))
        },
    }


def check_gates(summary: dict, real_key: str) -> dict:
    """The two structural gates that must hold before a verdict means anything."""
    gates: dict = {}

    integrity = summary[real_key].get(INTEGRITY_SITE)
    if integrity is None:
        gates["integrity"] = {
            "verdict": "FAIL",
            "why": f"the real series has no {INTEGRITY_SITE} site",
        }
    else:
        worst = max(abs(stats["mean"]) for stats in integrity.values())
        gates["integrity"] = {
            "verdict": "PASS" if worst <= INTEGRITY_TOLERANCE else "FAIL",
            "site": INTEGRITY_SITE,
            "max_abs_mean": worst,
            "tolerance": INTEGRITY_TOLERANCE,
            "why": (
                "causal masking makes donor and recipient states identical "
                "before the first differing token, so patching there must move "
                "nothing; a non-zero value here means the harness is writing "
                "something it should not"
            ),
        }

    harness = (
        summary[real_key]
        .get(HARNESS_GATE_SITE, {})
        .get(str(HARNESS_GATE_LAYER))
    )
    if harness is None:
        gates["harness_positive_control"] = {
            "verdict": "FAIL",
            "why": (
                f"no {HARNESS_GATE_SITE} series at layer {HARNESS_GATE_LAYER}; "
                "without it the instrument is uncertified"
            ),
        }
    else:
        gates["harness_positive_control"] = {
            "verdict": "PASS" if harness["lcb"] >= HARNESS_GATE_MIN_LCB else "FAIL",
            "site": HARNESS_GATE_SITE,
            "layer": HARNESS_GATE_LAYER,
            "mean": harness["mean"],
            "lcb": harness["lcb"],
            "required_lcb": HARNESS_GATE_MIN_LCB,
            "why": (
                "patching the differing positions at the embedding output makes "
                "the recipient run token-identical to the donor run, so "
                "restoration must be 1; this certifies the instrument without "
                "assuming anything about the model"
            ),
        }

    gates["all_passed"] = all(
        gate.get("verdict") == "PASS"
        for key, gate in gates.items()
        if isinstance(gate, dict)
    )
    return gates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--curves", required=True)
    parser.add_argument("--real-key", default="REAL")
    parser.add_argument("--null-key", action="append", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--skip-gates",
        action="store_true",
        help=(
            "for the OD-011 demonstration only: synthetic curves carry no "
            "harness control, and the demonstration is about the verdict rule"
        ),
    )
    args = parser.parse_args()

    curves = json.loads(Path(args.curves).read_text(encoding="utf-8"))["curves"]
    summary = summarise_curves(curves)
    report = decide(summary, args.real_key, args.null_key)
    report["schema_version"] = "study5-p0-decision-v1"
    report["gates"] = (
        {"skipped": True} if args.skip_gates else check_gates(summary, args.real_key)
    )
    report["summary"] = summary
    report["claim_ceiling"] = (
        "An item-validity determination. It is not a scientific finding."
    )
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(json.dumps({k: v for k, v in report.items() if k != "summary"}, indent=1))
    if not args.skip_gates and not report["gates"].get("all_passed"):
        print("P0-CHECK-DECISION FAILED: a structural gate did not pass", file=sys.stderr)
        return 1
    print("P0-CHECK-DECISION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
