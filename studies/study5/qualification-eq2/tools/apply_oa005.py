"""Apply OA-005's revised three-part band criterion and report the outcome.

    (i)   longest contiguous run significantly exceeding the matched-norm
          random-lens null upper confidence bound
    (ii)  within that run, J-lens significantly exceeds the plain logit lens
    (iii) the run's argmax is not at an endpoint

(ii) is the new condition. It can remove the band entirely, and if it does that
is reported as the result rather than worked around.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bvn = _load("oa5_bvn", "band_vs_null.py")
llc = _load("oa5_llc", "logit_lens_control.py")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    results = {}
    for role, n_layers in (("positive", 27), ("depth", 27), ("negative", 11)):
        band_report = json.loads(
            (ROOT / f"r1/band_vs_null_{role}.json").read_text(encoding="utf-8")
        )
        j_report = json.loads(
            (ROOT / f"r1/rank_{role}.json").read_text(encoding="utf-8")
        )
        logit_path = ROOT / f"r1b/logitlens_{role}.json"
        if not logit_path.is_file():
            print(f"  {role}: no logit lens control, skipping")
            continue
        l_report = json.loads(logit_path.read_text(encoding="utf-8"))

        trials = int(j_report["pooled_scored_intermediates"])
        l_trials = int(l_report["pooled_scored_intermediates"])
        if trials != l_trials:
            raise SystemExit(
                f"{role}: trial counts differ, {trials} vs {l_trials}; the two "
                "profiles are not comparable"
            )

        band_i = band_report["band"]
        j_profile = j_report["pooled_profile"]["1"]
        l_profile = l_report["pooled_profile"]["1"]

        if not band_i:
            results[role] = {
                "condition_i_band": [],
                "condition_i_passed": False,
                "condition_ii": None,
                "final_band": [],
                "band_valid": False,
                "reason": "condition (i) produced no band",
            }
            print(f"  {role}: no band from condition (i)")
            continue

        cii = llc.condition_ii(j_profile, l_profile, band_i, trials)
        revised = cii["revised_band"]

        layers = [int(p["layer"]) for p in j_profile]
        readrates = {int(p["layer"]): float(p["readrate"]) for p in j_profile}
        argmax_ok = bvn.argmax_is_interior(revised, readrates, layers) if revised else False
        peak_layer = (
            max(revised, key=lambda l: readrates[l]) if revised else None
        )

        valid = bool(revised) and argmax_ok
        results[role] = {
            "condition_i_band": band_i,
            "condition_i_passed": True,
            "condition_ii": cii,
            "condition_iii_argmax_interior": argmax_ok,
            "condition_iii_peak_layer": peak_layer,
            "final_band": revised if valid else [],
            "final_band_length": len(revised) if valid else 0,
            "band_valid": valid,
            "depth_fraction_of_lower_edge": (
                revised[0] / (n_layers - 1) if revised else None
            ),
            "depth_fraction_of_peak": (
                peak_layer / (n_layers - 1) if peak_layer is not None else None
            ),
            "j_peak_readrate": max(p["readrate"] for p in j_profile),
            "logit_lens_peak_readrate": max(p["readrate"] for p in l_profile),
            "reason": (
                "all three conditions hold"
                if valid
                else "condition (ii) or (iii) removed the band"
            ),
        }
        print(
            f"  {role:9} (i)={band_i} -> (ii) passes {cii['layers_passing_condition_ii']} "
            f"fails {cii['layers_failing_condition_ii']} -> final {results[role]['final_band']} "
            f"valid={valid}"
        )

    report = {
        "schema_version": "study5-eq2-oa005-band-v1",
        "phase": "R-1b",
        "step": "C",
        "rule": "OA-005",
        "criterion": {
            "i": "significantly exceeds the matched-norm random-lens null",
            "ii": "within that run, J-lens significantly exceeds the plain logit lens",
            "iii": "the run's argmax is not at an endpoint",
        },
        "condition_ii_is_new_and_tightens_the_criterion": True,
        "results": results,
        "mid_depth_language_is_forbidden": (
            "if a band survives it must NOT be described as reproducing the "
            "published mid-depth band; it is a late band at roughly 74 to 78 "
            "percent of depth"
        ),
        "claim_ceiling": "A band determination. It licenses no claim of any kind.",
    }
    out = ROOT / "r1b" / "oa005_band_determination.json"
    out.write_bytes(canonical_json_bytes(report))
    print("EQ2-CHECK-OA005-BAND PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
