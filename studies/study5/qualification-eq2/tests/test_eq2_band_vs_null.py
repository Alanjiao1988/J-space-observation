"""OD-011 failing cases for the OA-004 band criterion.

Two directions must both be demonstrated, and a criterion that only shows one is
not demonstrated at all:

  * it must NOT manufacture a band from a random lens, from noise, or from an
    empty profile - that is the OA-004 revision 3 gate;
  * it must STILL DETECT a real band when one is present - otherwise "no band"
    would be guaranteed and the criterion would be vacuous in the opposite
    direction, which is just as useless.

The second direction matters here specifically because OA-004 was written after
the failure of a rule that was too permissive; over-correcting into a rule that
can never fire would be the obvious way to get that wrong.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location("eq2_bvn", _TOOLS / "band_vs_null.py")
assert _SPEC is not None and _SPEC.loader is not None
bvn = importlib.util.module_from_spec(_SPEC)
sys.modules["eq2_bvn"] = bvn
_SPEC.loader.exec_module(bvn)

TRIALS = 900
N_LAYERS = 27


def profile(rates):
    return [
        {"layer": i, "readrate": r, "hits": int(round(r * TRIALS))}
        for i, r in enumerate(rates)
    ]


def flat_nulls(rate=0.002, n=5):
    return [profile([rate] * N_LAYERS) for _ in range(n)]


# --------------------------------------------------------------------------
# direction 1: it must not manufacture a band
# --------------------------------------------------------------------------


def test_the_registered_non_vacuity_demonstration_passes() -> None:
    demo = bvn.demonstrate_non_vacuity()
    assert demo["all_passed"] is True
    for name in ("random_lens_own_profile", "pure_noise_profile", "all_zero_profile"):
        assert demo["cases"][name]["band_exists"] is False


def test_a_profile_identical_to_the_null_yields_no_band() -> None:
    rates = [0.002] * N_LAYERS
    result = bvn.extract_band(profile(rates), flat_nulls(0.002), TRIALS)
    assert result["band_exists"] is False
    assert result["n_significant_layers"] == 0


def test_the_gpt2_shaped_small_signal_no_longer_yields_a_band() -> None:
    """The exact case that fired HB-002.

    A single interior layer at 0.0078 against a null of comparable magnitude
    must NOT produce a band. Under the superseded OD-015 rule it did.
    """

    rates = [0.0] * 11
    rates[9] = 0.0078
    rates[7] = 0.0011
    rates[8] = 0.0011
    rates[10] = 0.0022
    subject = [
        {"layer": i, "readrate": r, "hits": int(round(r * 898))}
        for i, r in enumerate(rates)
    ]
    nulls = [
        [{"layer": i, "readrate": 0.004, "hits": int(round(0.004 * 898))}
         for i in range(11)]
        for _ in range(5)
    ]
    result = bvn.extract_band(subject, nulls, 898)
    assert result["band_exists"] is False


# --------------------------------------------------------------------------
# direction 2: it must still detect a genuine band
# --------------------------------------------------------------------------


def test_a_strong_mid_depth_band_is_detected() -> None:
    """Guards against over-correction into a rule that can never fire."""

    rates = [0.001] * N_LAYERS
    for layer in range(12, 20):
        rates[layer] = 0.15
    result = bvn.extract_band(profile(rates), flat_nulls(0.002), TRIALS)
    assert result["band_exists"] is True
    assert result["band"] == list(range(12, 20))


def test_a_band_touching_the_last_layer_is_rejected_as_not_mid_depth() -> None:
    rates = [0.001] * N_LAYERS
    for layer in range(20, N_LAYERS):
        rates[layer] = 0.15
    result = bvn.extract_band(profile(rates), flat_nulls(0.002), TRIALS)
    assert result["raw_longest_significant_run"]
    assert result["mid_depth"] is False
    assert result["band_exists"] is False


def test_a_band_touching_the_first_layer_is_rejected() -> None:
    rates = [0.001] * N_LAYERS
    for layer in range(0, 8):
        rates[layer] = 0.15
    result = bvn.extract_band(profile(rates), flat_nulls(0.002), TRIALS)
    assert result["band_exists"] is False


# --------------------------------------------------------------------------
# the null ceiling itself
# --------------------------------------------------------------------------


def test_fewer_than_five_null_replicates_is_refused() -> None:
    """OA-004 fixes the replicate count; four must not be silently accepted."""

    with pytest.raises(ValueError):
        bvn.extract_band(profile([0.1] * N_LAYERS), flat_nulls(0.002, n=4), TRIALS)


def test_the_ceiling_is_the_maximum_over_replicates_not_the_mean() -> None:
    """Taking the max is the conservative direction; a mean would be laxer."""

    nulls = flat_nulls(0.001, n=4) + [profile([0.02] * N_LAYERS)]
    ceiling = bvn.null_ceiling(nulls, TRIALS)
    _lo, hi_high = bvn.wilson_bounds(int(0.02 * TRIALS), TRIALS)
    assert abs(ceiling[5] - hi_high) < 1e-12


def test_a_zero_hit_null_still_has_a_positive_upper_bound() -> None:
    """The reason for Wilson rather than the normal approximation.

    With zero observed hits the normal interval collapses to a point at zero,
    and then a single lucky hit in the real profile would clear it. Wilson keeps
    a positive upper bound.
    """

    _lo, hi = bvn.wilson_bounds(0, TRIALS)
    assert hi > 0.0
    assert hi < 0.01


def test_wilson_bounds_bracket_the_point_estimate() -> None:
    lo, hi = bvn.wilson_bounds(90, 900)
    assert lo < 0.1 < hi


def test_significance_requires_non_overlapping_intervals() -> None:
    """A readrate above the null POINT estimate is not enough on its own."""

    rates = [0.001] * N_LAYERS
    for layer in range(12, 20):
        rates[layer] = 0.0035  # above the null rate, but well inside its interval
    result = bvn.extract_band(profile(rates), flat_nulls(0.002), TRIALS)
    assert result["band_exists"] is False


def test_confidence_level_is_the_registered_convention() -> None:
    assert bvn.CONFIDENCE == 0.95
    assert bvn.MIN_NULL_REPLICATES == 5
