"""OD-011 failing cases for the D-1 degeneracy diagnostic.

Two things must be demonstrated, not asserted:

  * the categorisation actually discriminates - it must return negative-B on a
    genuinely identity-like J, and negative-A on one that is not. A rule that
    returned the same label either way would be a diagnostic that cannot fail;
  * the tool REFUSES to open a sealed EQ1 lens. That refusal is the only thing
    standing between this diagnostic and a violation of OD-012, so it is tested
    rather than trusted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location("eq2_d1", _TOOLS / "d1_degeneracy.py")
assert _SPEC is not None and _SPEC.loader is not None
d1 = importlib.util.module_from_spec(_SPEC)
sys.modules["eq2_d1"] = d1
_SPEC.loader.exec_module(d1)

torch = pytest.importorskip("torch")


# --------------------------------------------------------------------------
# the categorisation must discriminate
# --------------------------------------------------------------------------


def test_an_identity_like_j_is_categorised_negative_B() -> None:
    """The alternative hypothesis must be reachable.

    If this returned negative-A, the diagnostic could never conclude that our
    construction was degenerate, and running it would be theatre.
    """

    category, meaning = d1.categorise(0.05)
    assert category == "negative-B"
    assert "degenerates" in meaning


def test_a_far_from_identity_j_is_categorised_negative_A() -> None:
    category, meaning = d1.categorise(1.28)
    assert category == "negative-A"
    assert "departs substantially" in meaning


def test_the_middle_range_is_reported_as_intermediate_not_forced() -> None:
    """Between the two registered thresholds the category is not forced."""

    category, _meaning = d1.categorise(0.75)
    assert category == "INTERMEDIATE"


def test_the_thresholds_are_the_registered_values() -> None:
    assert d1.NEGATIVE_B_BELOW == 0.5
    assert d1.NEGATIVE_A_AT_OR_ABOVE == 1.0


def test_the_boundaries_are_handled_as_registered() -> None:
    """Exactly 1.0 is registered as 'at or above', so it is negative-A."""

    assert d1.categorise(1.0)[0] == "negative-A"
    assert d1.categorise(0.4999)[0] == "negative-B"
    assert d1.categorise(0.5)[0] == "INTERMEDIATE"


# --------------------------------------------------------------------------
# the OD-012 refusal
# --------------------------------------------------------------------------


def test_the_sealed_digests_are_the_committed_ones() -> None:
    assert (
        "2910b7bf80784a48f4e0d41f1a6fd002781f1d3f4f6bc3df83fb547848164083"
        in d1.SEALED_LENS_SHA256
    )
    assert (
        "e6d7eec9cb33035edb4b702bc3fae807a48d42c29270f40b9c461e6116ee528a"
        in d1.SEALED_LENS_SHA256
    )


def test_a_file_whose_digest_matches_a_sealed_lens_is_refused(tmp_path, monkeypatch) -> None:
    """The refusal must trigger on CONTENT, not on filename.

    A sealed lens copied to an innocuous path still carries its digest, so the
    check is driven by hashing the file rather than by inspecting its name.
    """

    fake = tmp_path / "totally_innocent.pt"
    fake.write_bytes(b"not really a lens")

    sealed = next(iter(d1.SEALED_LENS_SHA256))
    monkeypatch.setattr(d1, "sha256_file", lambda _path: sealed)

    with pytest.raises(SystemExit) as excinfo:
        d1.analyse_lens(fake)
    assert "sealed EQ1 lens" in str(excinfo.value)


def test_an_external_lens_is_not_refused(tmp_path, monkeypatch) -> None:
    """The guard must not refuse everything; that would also be a check that
    cannot fail, in the opposite direction."""

    path = tmp_path / "external.pt"
    torch.save(
        {"J": {0: torch.eye(4)}, "d_model": 4, "n_prompts": 1, "source_layers": [0]},
        str(path),
    )
    monkeypatch.setattr(d1, "sha256_file", lambda _p: "00" * 32)
    result = d1.analyse_lens(path)
    assert result["is_a_sealed_eq1_lens"] is False
    assert result["layers"] == 1


# --------------------------------------------------------------------------
# the degeneracy measure itself
# --------------------------------------------------------------------------


def test_an_exact_identity_measures_zero_distance(tmp_path, monkeypatch) -> None:
    path = tmp_path / "identity.pt"
    torch.save(
        {"J": {0: torch.eye(8)}, "d_model": 8, "n_prompts": 1, "source_layers": [0]},
        str(path),
    )
    monkeypatch.setattr(d1, "sha256_file", lambda _p: "11" * 32)
    result = d1.analyse_lens(path)
    layer = result["per_layer"][0]
    assert layer["relative_distance_from_identity"] < 1e-9
    assert abs(layer["best_scaled_identity_alpha"] - 1.0) < 1e-9
    assert layer["identity_attributable_share_of_energy"] > 0.999


def test_a_scaled_identity_is_recognised_as_identity_like(tmp_path, monkeypatch) -> None:
    """2*I is not the identity, but it is entirely identity-DIRECTION.

    The energy share must see that even though the raw distance does not.
    """

    path = tmp_path / "scaled.pt"
    torch.save(
        {"J": {0: 2.0 * torch.eye(8)}, "d_model": 8, "n_prompts": 1, "source_layers": [0]},
        str(path),
    )
    monkeypatch.setattr(d1, "sha256_file", lambda _p: "22" * 32)
    result = d1.analyse_lens(path)
    layer = result["per_layer"][0]
    assert abs(layer["best_scaled_identity_alpha"] - 2.0) < 1e-9
    assert layer["identity_attributable_share_of_energy"] > 0.999
    assert layer["relative_distance_from_identity"] > 0.9


def test_a_random_matrix_has_a_low_identity_share(tmp_path, monkeypatch) -> None:
    path = tmp_path / "random.pt"
    generator = torch.Generator().manual_seed(7)
    torch.save(
        {
            "J": {0: torch.randn(64, 64, generator=generator)},
            "d_model": 64,
            "n_prompts": 1,
            "source_layers": [0],
        },
        str(path),
    )
    monkeypatch.setattr(d1, "sha256_file", lambda _p: "33" * 32)
    result = d1.analyse_lens(path)
    layer = result["per_layer"][0]
    assert layer["identity_attributable_share_of_energy"] < 0.05
    assert layer["residual_share_of_energy"] > 0.95


def test_identity_and_residual_shares_sum_to_one(tmp_path, monkeypatch) -> None:
    """The decomposition must be exhaustive; otherwise the shares are not shares."""

    path = tmp_path / "mixed.pt"
    generator = torch.Generator().manual_seed(11)
    J = torch.eye(32) + 0.5 * torch.randn(32, 32, generator=generator)
    torch.save(
        {"J": {0: J}, "d_model": 32, "n_prompts": 1, "source_layers": [0]},
        str(path),
    )
    monkeypatch.setattr(d1, "sha256_file", lambda _p: "44" * 32)
    result = d1.analyse_lens(path)
    layer = result["per_layer"][0]
    total = (
        layer["identity_attributable_share_of_energy"]
        + layer["residual_share_of_energy"]
    )
    assert abs(total - 1.0) < 1e-9
