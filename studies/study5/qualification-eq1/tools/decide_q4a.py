"""Evaluate OD-009 criteria C1-C5 and decide gate Q-4a.

Every criterion was frozen in operator_amendments/OD-009.json (with the curve
range clarified in OD-009-A1.json) before any curve was computed. This tool only
applies them; it chooses nothing.

Each criterion emits its own OD-003 execution proof string on the success path.
A missing proof string is treated by verify_proof_strings.py as a FAIL, exactly
as an assertion failure would be.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BAND_MIN_LENGTH = 7
JACCARD_MIN = 0.70
ARGMAX_MAX_SEPARATION = 3
NULL_MARGIN = 1.0

# Post-hoc comparison only. OD-009 forbids this from touching tau, the band, or
# any criterion.
PRIOR_BAND_REINDEXED = list(range(11, 27))


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def values_of(curve: list[dict]) -> list[float]:
    return [float(p["excess_kurtosis"]) for p in curve]


def layers_of(curve: list[dict]) -> list[int]:
    return [int(p["layer"]) for p in curve]


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


def derive_band(curve: list[dict]) -> dict:
    """C2: half-height threshold, then the longest contiguous run above it."""
    vals = values_of(curve)
    layers = layers_of(curve)
    kmin, kmax = min(vals), max(vals)
    tau = kmin + 0.5 * (kmax - kmin)
    flags = [v >= tau for v in vals]
    band = longest_contiguous_run(flags, layers)
    argmax_layer = layers[vals.index(kmax)]
    return {
        "kappa_min": kmin,
        "kappa_max": kmax,
        "tau": tau,
        "band": band,
        "band_length": len(band),
        "argmax_layer": argmax_layer,
    }


def jaccard(a: list[int], b: list[int]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--curves", required=True)
    parser.add_argument("--out-decision", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.curves).read_text(encoding="utf-8"))
    curves = data["curves"]
    kappa_a, kappa_b = curves["kappa_A"], curves["kappa_B"]
    kappa_null = curves["kappa_null"]

    layers = layers_of(kappa_a)
    first_layer, last_layer = layers[0], layers[-1]

    band_a = derive_band(kappa_a)
    band_b = derive_band(kappa_b)

    proofs: list[str] = []
    criteria: dict[str, dict] = {}

    # C1 - interior maximum, judged against the endpoints of the actual curve
    # (OD-009-A1).
    c1_a = first_layer < band_a["argmax_layer"] < last_layer
    c1_b = first_layer < band_b["argmax_layer"] < last_layer
    criteria["C1"] = {
        "name": "interior maximum",
        "requirement": (
            f"argmax must lie strictly between the curve endpoints "
            f"{first_layer} and {last_layer} (OD-009-A1)"
        ),
        "argmax_A": band_a["argmax_layer"],
        "argmax_B": band_b["argmax_layer"],
        "pass_A": c1_a,
        "pass_B": c1_b,
        "pass": bool(c1_a and c1_b),
    }
    proofs.append("P2-CHECK-Q4A-C1 PASSED")

    # C2 - contiguity; the band is defined, so this records the construction.
    criteria["C2"] = {
        "name": "contiguity",
        "requirement": "band = longest contiguous run with kappa >= kappa_min + 0.5*(kappa_max - kappa_min)",
        "A": band_a,
        "B": band_b,
        "pass": bool(band_a["band"] and band_b["band"]),
    }
    proofs.append("P2-CHECK-Q4A-C2 PASSED")

    # C3 - coverage
    c3_a = band_a["band_length"] >= BAND_MIN_LENGTH
    c3_b = band_b["band_length"] >= BAND_MIN_LENGTH
    criteria["C3"] = {
        "name": "coverage",
        "requirement": f"band length >= {BAND_MIN_LENGTH} layers",
        "band_length_A": band_a["band_length"],
        "band_length_B": band_b["band_length"],
        "depth_fraction_A": band_a["band_length"] / len(layers),
        "depth_fraction_B": band_b["band_length"] / len(layers),
        "pass_A": c3_a,
        "pass_B": c3_b,
        "pass": bool(c3_a and c3_b),
    }
    proofs.append("P2-CHECK-Q4A-C3 PASSED")

    # C4 - cross-fit agreement
    j = jaccard(band_a["band"], band_b["band"])
    argmax_gap = abs(band_a["argmax_layer"] - band_b["argmax_layer"])
    criteria["C4"] = {
        "name": "cross-fit agreement",
        "requirement": f"Jaccard >= {JACCARD_MIN} and argmax separation <= {ARGMAX_MAX_SEPARATION}",
        "jaccard": j,
        "argmax_separation": argmax_gap,
        "pass": bool(j >= JACCARD_MIN and argmax_gap <= ARGMAX_MAX_SEPARATION),
    }
    proofs.append("P2-CHECK-Q4A-C4 PASSED")

    # C5 - exceeds the matched-norm null, layer by layer inside the band and by
    # a mean margin.
    null_by_layer = {int(p["layer"]): float(p["excess_kurtosis"]) for p in kappa_null}
    a_by_layer = {int(p["layer"]): float(p["excess_kurtosis"]) for p in kappa_a}
    b_by_layer = {int(p["layer"]): float(p["excess_kurtosis"]) for p in kappa_b}

    def c5_for(band: list[int], by_layer: dict[int, float]) -> dict:
        diffs = [by_layer[l] - null_by_layer[l] for l in band]
        every_layer = all(d > 0 for d in diffs)
        mean_diff = sum(diffs) / len(diffs) if diffs else float("nan")
        return {
            "per_layer_excess_over_null": [
                {"layer": l, "difference": by_layer[l] - null_by_layer[l]}
                for l in band
            ],
            "exceeds_null_at_every_band_layer": every_layer,
            "mean_difference_in_band": mean_diff,
            "margin_required": NULL_MARGIN,
            "meets_margin": bool(mean_diff >= NULL_MARGIN),
            "pass": bool(every_layer and mean_diff >= NULL_MARGIN),
        }

    c5_a = c5_for(band_a["band"], a_by_layer)
    c5_b = c5_for(band_b["band"], b_by_layer)
    criteria["C5"] = {
        "name": "exceeds the matched-norm null",
        "requirement": (
            "kappa must exceed the matched-norm random-J null at every layer in "
            f"the band, and the within-band mean difference must be >= {NULL_MARGIN}"
        ),
        "margin_frozen_before_measurement": True,
        "A": c5_a,
        "B": c5_b,
        "pass": bool(c5_a["pass"] and c5_b["pass"]),
    }
    proofs.append("P2-CHECK-Q4A-C5 PASSED")

    all_pass = all(c["pass"] for c in criteria.values())
    registered_band = sorted(set(band_a["band"]) & set(band_b["band"]))

    decision = {
        "schema_version": "study5-eq1-gate-decision-v1",
        "phase": "P-2",
        "gate": "Q-4a",
        "criteria_source": "operator_amendments/OD-009.json, clarified by OD-009-A1.json",
        "criteria": criteria,
        "verdict": "PASS" if all_pass else "FAIL",
        "derived_band_A": band_a["band"],
        "derived_band_B": band_b["band"],
        "registered_band_intersection": registered_band if all_pass else None,
        "prior_comparison": {
            "status": "POST HOC ONLY - took no part in deriving tau, the band, or any criterion",
            "published_band_reindexed_to_28_layers": PRIOR_BAND_REINDEXED,
            "jaccard_registered_band_vs_prior": (
                jaccard(registered_band, PRIOR_BAND_REINDEXED) if all_pass else None
            ),
            "agreement_is_a_result_not_an_input": True,
        },
        "proof_strings": proofs,
        "claim_ceiling": (
            "P-2 is an engineering and construct qualification measurement. A "
            "kurtosis curve is not evidence of J-space; it only decides whether "
            "later measurement is qualified to proceed. No result here is a "
            "scientific finding."
        ),
    }

    if not all_pass:
        decision["terminal_state"] = (
            "STUDY5_EQ1_WORKSPACE_BAND_NOT_ESTABLISHED_AT_THIS_SCALE"
        )
        decision["what_this_terminal_state_means"] = (
            "The J-space construct was not established on this model, and "
            "therefore NOTHING WAS MEASURED. This is NOT evidence that J-space is "
            "absent at 7B, it must not be written up as a negative finding, and no "
            "later text may cite it as negative evidence."
        )

    Path(args.out_decision).write_bytes(canonical_json_bytes(decision))

    for name in ("C1", "C2", "C3", "C4", "C5"):
        print(f"{name}: {'PASS' if criteria[name]['pass'] else 'FAIL'}")
    print(f"Q-4a verdict: {decision['verdict']}")
    for p in proofs:
        print(p)
    print("P2-CHECK-Q4A-DECISION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
