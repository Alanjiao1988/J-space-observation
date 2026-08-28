"""Tests for the Q-4a criteria implementation (OD-009, clarified by OD-009-A1).

The point of these tests is that the criteria must reject the shapes they were
written to reject. C5 in particular is the falsifiability anchor: a curve that
looks like a beautiful band but does not beat the matched-norm null must FAIL,
because otherwise "a band exists" is unfalsifiable.

Every case here is synthetic. No real curve is involved, so nothing in this file
can be tuned against the measured result.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "study5_eq1_q4a", _TOOLS / "decide_q4a.py"
)
assert _SPEC is not None and _SPEC.loader is not None
q4a = importlib.util.module_from_spec(_SPEC)
sys.modules["study5_eq1_q4a"] = q4a
_SPEC.loader.exec_module(q4a)

LAYERS = list(range(27))


def curve(values: list[float]) -> list[dict]:
    assert len(values) == len(LAYERS)
    return [
        {"layer": l, "excess_kurtosis": v, "n_position_samples": 100}
        for l, v in zip(LAYERS, values, strict=True)
    ]


def band_shape(peak: int = 13, height: float = 10.0, width: float = 6.0) -> list[float]:
    """A smooth interior bump, the shape Q-4a is meant to accept."""
    return [height * pow(2.718281828, -(((l - peak) / width) ** 2)) for l in LAYERS]


def write_curves(tmp_path, a, b, null, logit) -> Path:
    payload = {
        "curves": {
            "kappa_A": curve(a),
            "kappa_B": curve(b),
            "kappa_null": curve(null),
            "kappa_logitlens": curve(logit),
        }
    }
    path = tmp_path / "curves.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def decide(tmp_path, a, b, null, logit) -> dict:
    curves_path = write_curves(tmp_path, a, b, null, logit)
    out = tmp_path / "decision.json"
    argv = sys.argv
    sys.argv = [
        "decide_q4a.py",
        "--curves",
        str(curves_path),
        "--out-decision",
        str(out),
    ]
    try:
        q4a.main()
    finally:
        sys.argv = argv
    return json.loads(out.read_text(encoding="utf-8"))


def test_a_clean_interior_band_that_beats_the_null_passes(tmp_path) -> None:
    shape = band_shape()
    null = [0.2] * len(LAYERS)
    result = decide(tmp_path, shape, shape, null, [0.1] * len(LAYERS))
    assert result["verdict"] == "PASS"
    assert result["criteria"]["C1"]["pass"]
    assert result["criteria"]["C5"]["pass"]
    assert result["registered_band_intersection"]


def test_monotone_ramp_fails_c1_because_the_maximum_sits_at_an_endpoint(
    tmp_path,
) -> None:
    """A rising trend is not a band; its argmax is the last measured point."""

    ramp = [float(l) for l in LAYERS]
    null = [0.0] * len(LAYERS)
    result = decide(tmp_path, ramp, ramp, null, null)
    assert result["criteria"]["C1"]["pass"] is False
    assert result["verdict"] == "FAIL"
    assert result["criteria"]["C1"]["argmax_A"] == LAYERS[-1]


def test_narrow_spike_fails_c3(tmp_path) -> None:
    spike = [0.0] * len(LAYERS)
    spike[13] = 20.0
    spike[12] = 6.0
    spike[14] = 6.0
    null = [0.0] * len(LAYERS)
    result = decide(tmp_path, spike, spike, null, null)
    assert result["criteria"]["C3"]["pass"] is False
    assert result["verdict"] == "FAIL"


def test_bands_in_different_places_fail_c4(tmp_path) -> None:
    a = band_shape(peak=6)
    b = band_shape(peak=20)
    null = [0.2] * len(LAYERS)
    result = decide(tmp_path, a, b, null, null)
    assert result["criteria"]["C4"]["pass"] is False
    assert result["verdict"] == "FAIL"


def test_a_perfect_band_that_does_not_beat_the_null_fails_c5(tmp_path) -> None:
    """The criterion that makes Q-4a falsifiable.

    This curve satisfies C1 through C4 completely: a smooth interior bump, wide,
    identical across both fits. If C5 did not exist it would pass. It must fail,
    because the matched-norm random J produces the very same shape, so the shape
    carries no information about J.
    """

    shape = band_shape()
    result = decide(tmp_path, shape, shape, list(shape), [0.0] * len(LAYERS))
    assert result["criteria"]["C1"]["pass"]
    assert result["criteria"]["C2"]["pass"]
    assert result["criteria"]["C3"]["pass"]
    assert result["criteria"]["C4"]["pass"]
    assert result["criteria"]["C5"]["pass"] is False
    assert result["verdict"] == "FAIL"


def test_beating_the_null_by_less_than_the_margin_fails_c5(tmp_path) -> None:
    shape = band_shape()
    null = [v - 0.25 for v in shape]  # positive everywhere but below margin 1.0
    result = decide(tmp_path, shape, shape, null, [0.0] * len(LAYERS))
    assert result["criteria"]["C5"]["A"]["exceeds_null_at_every_band_layer"]
    assert result["criteria"]["C5"]["A"]["meets_margin"] is False
    assert result["verdict"] == "FAIL"


def test_failing_one_band_layer_fails_c5_even_with_a_large_mean_margin(
    tmp_path,
) -> None:
    """The per-layer requirement is not redundant with the mean requirement."""

    shape = band_shape()
    null = [0.0] * len(LAYERS)
    # Make the null win at exactly one layer inside the band.
    null[13] = shape[13] + 0.5
    result = decide(tmp_path, shape, shape, null, [0.0] * len(LAYERS))
    assert result["criteria"]["C5"]["A"]["exceeds_null_at_every_band_layer"] is False
    assert result["criteria"]["C5"]["A"]["mean_difference_in_band"] > 1.0
    assert result["verdict"] == "FAIL"


def test_fail_records_the_terminal_state_and_its_exact_meaning(tmp_path) -> None:
    ramp = [float(l) for l in LAYERS]
    result = decide(tmp_path, ramp, ramp, [0.0] * len(LAYERS), [0.0] * len(LAYERS))
    assert (
        result["terminal_state"]
        == "STUDY5_EQ1_WORKSPACE_BAND_NOT_ESTABLISHED_AT_THIS_SCALE"
    )
    meaning = result["what_this_terminal_state_means"]
    assert "NOTHING WAS MEASURED" in meaning
    assert "NOT evidence that J-space is absent" in meaning


def test_the_prior_is_recorded_as_post_hoc_and_never_used_to_derive(tmp_path) -> None:
    """OD-009 forbids the published band from touching the derivation.

    A band deliberately placed away from the prior must still be reported as
    derived, with the prior comparison recorded separately.
    """

    shape = band_shape(peak=5, width=3.0)
    null = [0.2] * len(LAYERS)
    result = decide(tmp_path, shape, shape, null, null)
    assert "POST HOC ONLY" in result["prior_comparison"]["status"]
    assert result["derived_band_A"]
    # The derived band is what the data gave, not the prior's 11..26.
    assert min(result["derived_band_A"]) < 11


def test_band_is_the_longest_contiguous_run_not_scattered_layers(tmp_path) -> None:
    values = [0.0] * len(LAYERS)
    for l in range(10, 19):
        values[l] = 10.0
    values[2] = 10.0  # isolated spike far away, above tau but not contiguous
    values[24] = 10.0
    null = [0.1] * len(LAYERS)
    result = decide(tmp_path, values, values, null, null)
    band = result["criteria"]["C2"]["A"]["band"]
    assert band == list(range(10, 19))
    assert 2 not in band and 24 not in band


def test_every_criterion_emits_its_proof_string(tmp_path) -> None:
    shape = band_shape()
    null = [0.2] * len(LAYERS)
    result = decide(tmp_path, shape, shape, null, null)
    for name in ("C1", "C2", "C3", "C4", "C5"):
        assert f"P2-CHECK-Q4A-{name} PASSED" in result["proof_strings"]
