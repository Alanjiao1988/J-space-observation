"""Validation of the excess-kurtosis statistic against distributions whose
kurtosis is known analytically.

Why this exists. The Q-4a curves came out near 1.0, and my control measurement
showed the model's OWN final-layer logits score 1.533 - the same order of
magnitude. I had written a diagnostic interpretation rule predicting that a
language model's logits would score in the tens or hundreds, and that a
near-one reading would mean the measurement was broken.

That prior was wrong, and a wrong prior is not a reason to discard data. It is
also not something to quietly re-interpret after the fact. The question "is the
statistic correct?" has a definite answer that does not depend on anyone's
expectations, so it is settled here against distributions with analytically
known excess kurtosis:

    Gaussian     0
    Uniform     -1.2
    Laplace      3
    Student-t(5) 6
    Bernoulli(p) (1 - 6p(1-p)) / (p(1-p))

If the implementation recovers these, it is correct, and the near-Gaussian
readings are a real property of the logits rather than an artifact.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "study5_eq1_kctl", _TOOLS / "kurtosis_control.py"
)
assert _SPEC is not None and _SPEC.loader is not None
kctl = importlib.util.module_from_spec(_SPEC)
sys.modules["study5_eq1_kctl"] = kctl
_SPEC.loader.exec_module(kctl)

N = 400_000
TOL = 0.12


def one_row(samples) -> float:
    return kctl.excess_kurtosis_rowwise(samples.reshape(1, -1))[0]


def test_gaussian_scores_zero() -> None:
    g = torch.Generator().manual_seed(11)
    x = torch.randn(N, generator=g, dtype=torch.float64)
    assert abs(one_row(x) - 0.0) < TOL


def test_uniform_scores_minus_one_point_two() -> None:
    g = torch.Generator().manual_seed(12)
    x = torch.rand(N, generator=g, dtype=torch.float64)
    assert abs(one_row(x) - (-1.2)) < TOL


def test_laplace_scores_three() -> None:
    g = torch.Generator().manual_seed(13)
    u = torch.rand(N, generator=g, dtype=torch.float64) - 0.5
    x = -torch.sign(u) * torch.log1p(-2 * u.abs())
    assert abs(one_row(x) - 3.0) < 0.35


def test_student_t_with_five_df_scores_six() -> None:
    g = torch.Generator().manual_seed(14)
    df = 5
    z = torch.randn(N, generator=g, dtype=torch.float64)
    chi2 = torch.stack(
        [torch.randn(N, generator=g, dtype=torch.float64) ** 2 for _ in range(df)]
    ).sum(dim=0)
    x = z / torch.sqrt(chi2 / df)
    # t(5) has finite fourth moment but a very heavy tail, so the sample
    # estimator is noisy; a wide band still separates 6 from 0 decisively.
    assert 3.0 < one_row(x) < 12.0


def test_bernoulli_matches_its_closed_form() -> None:
    g = torch.Generator().manual_seed(15)
    p = 0.2
    x = (torch.rand(N, generator=g, dtype=torch.float64) < p).double()
    expected = (1 - 6 * p * (1 - p)) / (p * (1 - p))
    assert abs(one_row(x) - expected) < 0.2


def test_the_statistic_is_not_stuck_near_one() -> None:
    """The specific failure mode the control was written to catch.

    A statistic that returned roughly 1 regardless of its input would make the
    Q-4a curves meaningless. These inputs span from -1.2 to well above 6.
    """

    g = torch.Generator().manual_seed(16)
    gaussian = one_row(torch.randn(N, generator=g, dtype=torch.float64))
    uniform = one_row(torch.rand(N, generator=g, dtype=torch.float64))
    spread = abs(uniform - gaussian)
    assert spread > 1.0


def test_it_is_scale_and_shift_invariant() -> None:
    """Kurtosis must not move when the logits are rescaled or offset.

    This matters because the null lens is norm-matched: if the statistic
    responded to scale, exceeding the null could be an artifact of magnitude
    rather than of shape.
    """

    g = torch.Generator().manual_seed(17)
    x = torch.randn(N, generator=g, dtype=torch.float64)
    base = one_row(x)
    assert abs(one_row(x * 137.0) - base) < 1e-6
    assert abs(one_row(x + 42.0) - base) < 1e-6
    assert abs(one_row(x * -3.0) - base) < 1e-6


def test_it_agrees_with_a_naive_direct_computation() -> None:
    """Independent formula: E[(x-mu)^4]/sigma^4 - 3, computed without the
    standardise-first rearrangement the tool uses for numerical range."""

    g = torch.Generator().manual_seed(18)
    x = torch.randn(20_000, generator=g, dtype=torch.float64) * 5.0 + 3.0
    mu = x.mean()
    m4 = ((x - mu) ** 4).mean()
    var = ((x - mu) ** 2).mean()
    naive = (m4 / var**2 - 3.0).item()
    assert abs(one_row(x) - naive) < 1e-9


def test_float32_inputs_are_promoted_before_the_fourth_moment() -> None:
    """Large logits in float32 would overflow or lose precision in E[x^4];
    the tool casts to float64 first, and this pins that behaviour."""

    g = torch.Generator().manual_seed(19)
    x64 = torch.randn(50_000, generator=g, dtype=torch.float64) * 1000.0
    x32 = x64.float()
    assert abs(one_row(x32) - one_row(x64)) < 1e-3


def test_a_handful_of_extreme_outliers_barely_moves_a_large_vocabulary() -> None:
    """The quantitative reason a language model's own logits do NOT score in
    the hundreds, which is where my original prior was wrong.

    With a 152064-token vocabulary, even ten tokens sitting five standard
    deviations out contribute about 10 * 5^4 / 152064, which is far below 1.
    Kurtosis over a vocabulary that large is dominated by the bulk, not by the
    few tokens the model actually favours.
    """

    vocab = 152064
    g = torch.Generator().manual_seed(20)
    x = torch.randn(vocab, generator=g, dtype=torch.float64)
    before = one_row(x)
    x[:10] = 5.0
    after = one_row(x)
    assert abs(after - before) < 0.1
