"""OD-011 failing cases for the P-0 decision rule.

The rule has to be shown capable of BOTH verdicts. A rule that can only return
CAUSALLY_USED manufactures evidence; a rule that can only return
NOT_CAUSALLY_USED makes the measurement decorative. Both directions are tested,
along with each structural gate.
"""

from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


decider = load("p0_decider_test", "decide_p0.py")

SITES = ("CUE", "BRIDGE", "READOUT")
LAYERS = list(range(-1, 6))
CLUSTERS = [f"c{i:03d}" for i in range(40)]


def series(rng, mean, sigma):
    return {c: [rng.gauss(mean, sigma), rng.gauss(mean, sigma)] for c in CLUSTERS}


def nulls(rng, sigma=0.05):
    out = {}
    for replicate in range(3):
        for family in ("NULL_C", "NULL_R"):
            out[f"{family}_{replicate}"] = {
                site: {str(layer): series(rng, 0.0, sigma) for layer in LAYERS}
                for site in SITES
            }
    return out


def real(rng, bridge_mean, bridge_layers=(2, 3)):
    return {
        site: {
            str(layer): series(
                rng,
                bridge_mean if (site == "BRIDGE" and layer in bridge_layers) else 0.0,
                0.05,
            )
            for layer in LAYERS
        }
        for site in SITES
    }


def build(rng, bridge_mean, **kw):
    curves = {"REAL": real(rng, bridge_mean, **kw)}
    curves.update(nulls(rng))
    return curves


def run(curves):
    summary = decider.summarise_curves(curves)
    return decider.decide(summary, "REAL", sorted(k for k in curves if k != "REAL"))


# --------------------------------------------------------- both directions


def test_a_flat_zero_curve_returns_the_negative_verdict():
    outcome = run(build(random.Random(1), 0.0))
    assert outcome["verdict"] == "NOT_CAUSALLY_USED"
    assert outcome["layers_above_ceiling"] == []


def test_a_strong_localised_curve_returns_the_positive_verdict():
    outcome = run(build(random.Random(2), 0.60))
    assert outcome["verdict"] == "CAUSALLY_USED"
    assert outcome["layers_above_ceiling"] == [2, 3]


def test_the_null_fed_back_as_the_real_series_returns_the_negative_verdict():
    rng = random.Random(3)
    curves = build(rng, 0.0)
    curves["REAL"] = curves["NULL_C_0"]
    assert run(curves)["verdict"] == "NOT_CAUSALLY_USED"


# ------------------------------------------------- only BRIDGE can decide


def test_a_huge_effect_at_CUE_alone_does_not_produce_a_positive_verdict():
    rng = random.Random(4)
    curves = build(rng, 0.0)
    for layer in LAYERS:
        curves["REAL"]["CUE"][str(layer)] = series(rng, 5.0, 0.05)
    outcome = run(curves)
    assert outcome["verdict"] == "NOT_CAUSALLY_USED"


def test_a_huge_effect_at_READOUT_alone_does_not_produce_a_positive_verdict():
    rng = random.Random(5)
    curves = build(rng, 0.0)
    for layer in LAYERS:
        curves["REAL"]["READOUT"][str(layer)] = series(rng, 5.0, 0.05)
    assert run(curves)["verdict"] == "NOT_CAUSALLY_USED"


# ------------------------------------------------------------- the ceiling


def test_a_noisier_null_raises_the_ceiling_and_can_flip_the_verdict():
    rng = random.Random(6)
    quiet = build(rng, 0.25)
    assert run(quiet)["verdict"] == "CAUSALLY_USED"

    rng = random.Random(6)
    loud = {"REAL": real(rng, 0.25)}
    loud.update(nulls(rng, sigma=2.0))
    assert run(loud)["verdict"] == "NOT_CAUSALLY_USED"


def test_the_ceiling_is_a_maximum_over_every_null_series():
    rng = random.Random(7)
    curves = build(rng, 0.0)
    curves["NULL_R_2"]["READOUT"]["4"] = series(rng, 9.0, 0.01)
    outcome = run(curves)
    assert outcome["ceiling"] > 8.0
    assert outcome["ceiling_source"]["construction"] == "NULL_R_2"
    assert outcome["ceiling_source"]["site"] == "READOUT"
    assert outcome["ceiling_source"]["layer"] == 4


def test_the_integrity_site_is_kept_out_of_the_ceiling():
    rng = random.Random(8)
    curves = build(rng, 0.0)
    for key in [k for k in curves if k.startswith("NULL_")]:
        curves[key]["PREFIX"] = {
            str(layer): series(rng, 9.0, 0.01) for layer in LAYERS
        }
    assert run(curves)["ceiling"] < 1.0


def test_a_missing_null_construction_is_an_error_not_a_default():
    rng = random.Random(9)
    curves = build(rng, 0.0)
    summary = decider.summarise_curves(curves)
    with pytest.raises(decider.DeciderError):
        decider.decide(summary, "REAL", ["NULL_DOES_NOT_EXIST"])


def test_a_missing_decisive_site_is_an_error_not_a_negative_verdict():
    rng = random.Random(10)
    curves = build(rng, 0.0)
    del curves["REAL"]["BRIDGE"]
    summary = decider.summarise_curves(curves)
    with pytest.raises(decider.DeciderError):
        decider.decide(summary, "REAL", sorted(k for k in curves if k != "REAL"))


# ------------------------------------------------------------------ gates


def gated(rng, prefix_mean, cue_minus_one_mean):
    curves = build(rng, 0.0)
    curves["REAL"]["PREFIX"] = {
        str(layer): {c: [prefix_mean, prefix_mean] for c in CLUSTERS}
        for layer in LAYERS
    }
    curves["REAL"]["CUE"]["-1"] = series(rng, cue_minus_one_mean, 0.01)
    return decider.check_gates(decider.summarise_curves(curves), "REAL")


def test_both_gates_pass_on_a_well_formed_measurement():
    gates = gated(random.Random(11), 0.0, 1.0)
    assert gates["integrity"]["verdict"] == "PASS"
    assert gates["harness_positive_control"]["verdict"] == "PASS"
    assert gates["all_passed"]


def test_a_non_zero_prefix_fails_the_integrity_gate():
    gates = gated(random.Random(12), 0.01, 1.0)
    assert gates["integrity"]["verdict"] == "FAIL"
    assert not gates["all_passed"]


def test_a_weak_embedding_patch_fails_the_harness_gate():
    gates = gated(random.Random(13), 0.0, 0.5)
    assert gates["harness_positive_control"]["verdict"] == "FAIL"
    assert not gates["all_passed"]


def test_a_missing_harness_series_fails_rather_than_being_skipped():
    rng = random.Random(14)
    curves = build(rng, 0.0)
    curves["REAL"]["PREFIX"] = {
        str(layer): {c: [0.0, 0.0] for c in CLUSTERS} for layer in LAYERS
    }
    del curves["REAL"]["CUE"]["-1"]
    gates = decider.check_gates(decider.summarise_curves(curves), "REAL")
    assert gates["harness_positive_control"]["verdict"] == "FAIL"


# ------------------------------------------------------------- bootstrap


def test_the_bootstrap_resamples_clusters_not_observations():
    # one cluster holding every observation must give a zero-width interval,
    # because every resample draws the same cluster
    single = {"only": [0.0, 1.0, 2.0]}
    out = decider.cluster_bootstrap(single, resamples=200, seed=1)
    assert out["lcb"] == out["ucb"] == out["mean"] == 1.0
    assert out["n_clusters"] == 1
    assert out["n_observations"] == 3


def test_percentiles_are_ordered_and_bracket_the_mean():
    rng = random.Random(15)
    out = decider.cluster_bootstrap(series(rng, 0.3, 0.2), resamples=500, seed=2)
    assert out["lcb"] < out["mean"] < out["ucb"]


def test_an_empty_sample_raises():
    with pytest.raises(decider.DeciderError):
        decider.cluster_bootstrap({})


def test_registered_constants_are_what_the_registration_says():
    assert decider.DECISIVE_SITE == "BRIDGE"
    assert decider.CONFIDENCE == 0.95
    assert decider.LOWER_PERCENTILE == 2.5
    assert decider.UPPER_PERCENTILE == 97.5
    assert decider.BOOTSTRAP_RESAMPLES == 10000
    assert decider.BOOTSTRAP_SEED == 20260829
    assert decider.HARNESS_GATE_SITE == "CUE"
    assert decider.HARNESS_GATE_LAYER == -1
    assert decider.HARNESS_GATE_MIN_LCB == 0.90
    assert decider.INTEGRITY_SITE == "PREFIX"
    assert decider.INTEGRITY_TOLERANCE == 1e-4
