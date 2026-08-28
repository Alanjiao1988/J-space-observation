"""OD-011 failing cases for the OD-015 band rule and the rank-profile helpers.

Every check below is driven with wrong input to prove it reports the failure,
not merely with correct input to prove it agrees.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parent.parent / "tools"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, _TOOLS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


band = _load("eq2_band", "derive_band.py")
rank = _load("eq2_rank", "rank_profile.py")

LAYERS = list(range(27))


def profile(values):
    assert len(values) == len(LAYERS)
    return [
        {"layer": l, "readrate": v, "hits": 0}
        for l, v in zip(LAYERS, values, strict=True)
    ]


# --------------------------------------------------------------------------
# band rule: positive path
# --------------------------------------------------------------------------


def test_a_mid_depth_bump_yields_an_interior_band() -> None:
    values = [0.0] * 27
    for l in range(12, 20):
        values[l] = 0.8
    values[16] = 1.0
    result = band.derive_band(profile(values))
    assert result["band_exists"] is True
    assert result["band"] == list(range(12, 20))
    assert result["argmax_layer"] == 16


# --------------------------------------------------------------------------
# OD-011 failing cases for the band rule
# --------------------------------------------------------------------------


def test_an_all_zero_profile_yields_no_band() -> None:
    """The case that matters for the negative control.

    A profile where nothing is readable anywhere must yield NO band. A rule that
    divided by the maximum without checking it would raise, or worse would treat
    an all-zero profile as uniformly 'at threshold' and return every layer.
    """

    result = band.derive_band(profile([0.0] * 27))
    assert result["band_exists"] is False
    assert result["band"] == []
    assert result["peak_readrate"] == 0.0
    assert "NOT rescued by raising k" in result["reason"]


def test_a_monotone_ramp_is_rejected_because_its_argmax_is_an_endpoint() -> None:
    values = [l / 26.0 for l in LAYERS]
    result = band.derive_band(profile(values))
    assert result["argmax_layer"] == 26
    assert result["interior_argmax"] is False
    assert result["band_exists"] is False


def test_a_maximum_at_the_first_layer_is_also_rejected() -> None:
    values = [1.0 - l / 26.0 for l in LAYERS]
    result = band.derive_band(profile(values))
    assert result["argmax_layer"] == 0
    assert result["band_exists"] is False


def test_scattered_layers_above_threshold_do_not_form_a_band() -> None:
    """A band is a connected region."""

    values = [0.0] * 27
    for l in (3, 9, 14, 21):
        values[l] = 1.0
    values[14] = 1.0
    result = band.derive_band(profile(values))
    assert result["band_length"] == 1


def test_a_uniform_nonzero_profile_spans_everything_and_has_no_interior_peak() -> None:
    """Flat means no band, and the endpoint rule is what catches it."""

    result = band.derive_band(profile([0.5] * 27))
    assert result["argmax_layer"] == 0
    assert result["band_exists"] is False


# --------------------------------------------------------------------------
# readout position rules
# --------------------------------------------------------------------------


def test_poetry_reads_out_at_the_last_newline_not_the_last_token() -> None:
    """The set-specific rule that is easiest to get wrong.

    Harmonising poetry to 'final prompt token' would silently change the method,
    so this pins the difference.
    """

    tokens = ["A", " couplet", ":", "\n", "The", " soldier", "\n", "And", " closed"]
    assert rank.readout_position("poetry", tokens) == 6
    assert rank.readout_position("association", tokens) == 8


def test_poetry_without_a_newline_raises_rather_than_falling_back() -> None:
    """A silent fallback to the last token would produce a plausible wrong number."""

    with pytest.raises(rank.RankProfileError):
        rank.readout_position("poetry", ["no", " newline", " here"])


def test_every_registered_set_has_a_readout_rule() -> None:
    assert set(rank.READOUT_RULE) == {
        "multihop", "multilingual", "order-ops", "poetry", "association", "typo",
    }


def test_an_unknown_set_is_rejected() -> None:
    with pytest.raises(KeyError):
        rank.readout_position("not-a-set", ["a"])


# --------------------------------------------------------------------------
# synonym expansion
# --------------------------------------------------------------------------


def test_order_ops_numbers_expand_to_digit_and_word_forms() -> None:
    forms = rank.synonym_forms("order-ops", "5")
    assert "5" in forms
    assert "five" in forms
    assert " five" in forms


def test_order_ops_operations_expand_to_symbol_and_word_forms() -> None:
    forms = rank.synonym_forms("order-ops", "multiplication")
    assert "*" in forms
    assert "multiplication" in forms


def test_other_sets_do_not_get_the_order_ops_expansion() -> None:
    """The synonym rule is specific to order-ops and must not leak."""

    forms = rank.synonym_forms("association", "grief")
    assert "*" not in forms
    assert all("five" != f.strip() for f in forms)


def test_casing_and_leading_space_variants_are_always_offered() -> None:
    forms = rank.synonym_forms("association", "grief")
    assert "grief" in forms
    assert " grief" in forms
    assert "Grief" in forms


class _FakeTokenizer:
    """Encodes single words as one token, multi-word strings as several."""

    def __call__(self, text, add_special_tokens=False):
        pieces = text.strip().split()
        return {"input_ids": [abs(hash(p)) % 1000 for p in pieces] or [0]}


def test_multi_token_forms_are_excluded_not_scored_on_a_prefix() -> None:
    """The official order-ops rule says min over SINGLE TOKEN synonyms.

    Scoring a multi-token form on its first piece would silently rank a
    different token than the one intended.
    """

    ids = rank.single_token_ids(_FakeTokenizer(), ["alpha", "two words here"])
    assert len(ids) == 1
