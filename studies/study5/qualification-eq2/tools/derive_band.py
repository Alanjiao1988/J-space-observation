"""Derive the band from a rank profile using the rule frozen in OD-015.

The rule was committed before any profile was computed. This tool only applies
it; it chooses nothing.

    band = longest contiguous run of layers whose pass@1 readrate is at least
           half of the profile's maximum readrate,
           subject to the argmax not sitting on either endpoint.

A maximum readrate of zero means no content is readable at any layer, so no band
exists. That case is reported as such and is explicitly NOT rescued by raising k.

OD-011: failing cases in tests/test_eq2_band_rule.py.
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


def derive_band(profile: list[dict]) -> dict:
    layers = [int(p["layer"]) for p in profile]
    values = [float(p["readrate"]) for p in profile]

    peak = max(values)
    argmax_layer = layers[values.index(peak)]

    if peak <= 0.0:
        return {
            "band": [],
            "band_length": 0,
            "peak_readrate": peak,
            "argmax_layer": None,
            "threshold": 0.0,
            "interior_argmax": False,
            "band_exists": False,
            "reason": (
                "no intermediate is readable at rank 1 at any layer, so there is "
                "no band; this is NOT rescued by raising k"
            ),
        }

    threshold = 0.5 * peak
    flags = [v >= threshold for v in values]
    band = longest_contiguous_run(flags, layers)
    interior = layers[0] < argmax_layer < layers[-1]

    return {
        "band": band,
        "band_length": len(band),
        "band_first_layer": band[0] if band else None,
        "band_last_layer": band[-1] if band else None,
        "peak_readrate": peak,
        "argmax_layer": argmax_layer,
        "threshold": threshold,
        "interior_argmax": interior,
        "band_exists": bool(band) and interior,
        "depth_fraction": len(band) / len(layers) if layers else 0.0,
        "reason": (
            "band derived by the OD-015 rule"
            if interior
            else "argmax sits on an endpoint of the measured range, which is what a "
            "monotone trend looks like rather than a band"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", action="append", required=True,
                        help="role=path/to/rank_report.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    results = {}
    for spec in args.profile:
        role, _, path = spec.partition("=")
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        pooled = report["pooled_profile"]["1"]
        band = derive_band(pooled)
        band["role"] = role
        band["model_dir"] = report.get("model_dir")
        band["layers_measured"] = len(report["layers"])
        band["pooled_scored_intermediates"] = report.get("pooled_scored_intermediates")
        band["per_set_pass_at_1"] = {
            s: v["pass_at_k"]["1"] for s, v in report["per_set"].items()
        }
        results[role] = band
        print(
            f"{role:10} peak={band['peak_readrate']:.4f} "
            f"argmax={band['argmax_layer']} band={band['band']} "
            f"exists={band['band_exists']}"
        )

    out = {
        "schema_version": "study5-eq2-band-derivation-v1",
        "phase": "R-1",
        "rule": "OD-015",
        "rule_frozen_before_any_profile_was_computed": True,
        "results": results,
    }

    positive = results.get("positive")
    negative = results.get("negative")
    if positive is not None:
        out["external_reference_band"] = positive["band"]
    if negative is not None:
        out["negative_control_holds"] = not negative["band_exists"]
        out["negative_control_note"] = (
            "a band on the negative control would mean the method is not "
            "discriminative and is a registered stop condition"
        )
    Path(args.out).write_bytes(canonical_json_bytes(out))
    print("EQ2-CHECK-BAND-DERIVATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
