#!/usr/bin/env python3
"""Independent re-derivation of the Study 3 draft-v0.2 design statistics.

This module is the independent methods reviewer's own implementation. It exists
so that the reviewed numbers are produced a second time, from the cited primary
sources and the protocol definitions, by a differently structured program.

INDEPENDENCE CONTRACT
---------------------
This file never imports, executes, copies functions from, or dynamically loads
``studies/study3/analysis/design_statistics.py``. That is enforced at run time
by :func:`assert_independence_of_drafting_implementation`, which fails closed.

The drafting table ``design_statistics_tables.json`` is read only in the
comparison stage, only as inert data, and only after the independent values
already exist. Agreement with the drafting implementation is never treated as
validation. Each statistical family carries at least one closed-form or
published-identity check that does not reference the drafting output at all.

DELIBERATE STRUCTURAL DIFFERENCES FROM THE DRAFTING SCRIPT
----------------------------------------------------------
* Exact binomial tails are computed in **exact integer arithmetic** over a
  rational success probability (numerator/denominator), never in floating point.
  Decisions such as "is this tail at or below alpha" are made by integer
  cross-multiplication, so no rounding can move a rejection count.
* The regularized incomplete beta function is implemented independently by a
  modified Lentz continued fraction and is used only as a cross-check of the
  exact integer route, via the published identity
  ``P(X >= k) = I_p(k, n - k + 1)``.
* Normal quantiles come from :class:`statistics.NormalDist`, not from a
  hand-rolled rational approximation.
* The paired procedure is re-derived from the score equation rather than
  transcribed, its rejection region is materialised as a lattice, and its size
  is obtained by **maximising over the nuisance parameter along the whole
  feasible null boundary** instead of reading a four-point sensitivity grid.
* All internal function names are distinct from the drafting implementation.

STATUS OF EVERY NUMBER PRODUCED HERE
------------------------------------
Proposed design parameters. Not observations, not measurements, not results,
not evidence, and not model performance. No model, tokenizer, bank, seed, or
prior result is read. No network access is performed.

PRIMARY SOURCES RE-DERIVED FROM
-------------------------------
* Tango T. "Equivalence test and confidence interval for the difference in
  proportions for the paired-sample design." Statistics in Medicine 1998;
  17(8):891-908. PMID 9595618.
* Hsueh HM, Liu JP, Chen JJ. "Unconditional exact tests for equivalence or
  noninferiority for paired binary endpoints." Biometrics 2001;57(2):478-483.
  PMID 11414572.
* Liu JP, Hsueh HM, Hsieh E, Chen JJ. "Tests for equivalence or non-inferiority
  for paired binary data." Statistics in Medicine 2002;21(2):231-245.
  PMID 11782062.
* Berger RL, Hsu JC. "Bioequivalence trials, intersection-union tests and
  equivalence confidence sets." Statistical Science 1996;11(4):283-319.
  DOI 10.1214/ss/1032280304.
* Clopper CJ, Pearson ES. "The use of confidence or fiducial limits illustrated
  in the case of the binomial." Biometrika 1934;26(4):404-413.

USAGE
-----
    python independent_methods_recalculation.py --emit
    python independent_methods_recalculation.py --check
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import sys
from bisect import bisect_left, bisect_right
from fractions import Fraction
from statistics import NormalDist

# ---------------------------------------------------------------------------
# Registered constants. Every one of these is a design parameter under review,
# not a measurement. Changing one changes the review, so they live here and are
# validated fail-closed before any arithmetic runs.
# ---------------------------------------------------------------------------

REVIEW_TABLE_BASENAME = "independent_methods_recalculation_tables.json"
DRAFTING_TABLE_BASENAME = "design_statistics_tables.json"
DRAFTING_SCRIPT_BASENAME = "design_statistics.py"

STATUS_LINE = "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS_NOT_FROZEN"
REVIEW_VERSION = "study3-independent-methods-review-v0.2"

STUDY_ALPHA = Fraction("0.005")
SELECTABLE_PROFILE_COUNT = 3
BONFERRONI_PER_PROFILE_ALPHA = Fraction("0.001666666667")
TARGET_POWER = Fraction("0.9")

# The counterbalancing construction published in the protocol enumerates four
# physical positions crossed with four displayed-symbol assignments, giving 16
# (position, symbol) cells, and then crosses that with the label-alphabet
# factor. Two label alphabets are registered as permitted, so a complete block
# for a label-bearing gate is 16 * 2 = 32 base items.
COUNTERBALANCE_POSITION_COUNT = 4
COUNTERBALANCE_SYMBOL_COUNT = 4
COUNTERBALANCE_ALPHABET_COUNT = 2
COUNTERBALANCE_RENDERING_COUNT = 3

ADMISSIBLE_N_MIN = 32
ADMISSIBLE_N_MAX = 768

# Alpha levels reviewed for every exact-binomial gate. 0.005 is the drafting
# per-component level; the Bonferroni per-profile level is what the drafting
# multiplicity statement actually claims to deliver; 0.001 is retained only to
# reproduce the drafting I4 table.
REVIEWED_ALPHAS = (
    ("alpha_0_005", STUDY_ALPHA),
    ("alpha_bonferroni_per_profile", BONFERRONI_PER_PROFILE_ALPHA),
    ("alpha_0_001", Fraction("0.001")),
)

# gate key -> (null p0, ordered alternatives of interest p1)
REVIEWED_BINOMIAL_GATES = (
    ("I1a_trivial_recovery", Fraction("0.90"),
     (Fraction("0.95"), Fraction("0.97"), Fraction("0.98"), Fraction("0.99"))),
    ("I1b_symbol_binding", Fraction("0.90"),
     (Fraction("0.95"), Fraction("0.97"), Fraction("0.98"), Fraction("0.99"))),
    ("I2_primitive_headroom", Fraction("0.50"),
     (Fraction("0.65"), Fraction("0.70"), Fraction("0.75"), Fraction("0.80"))),
    ("I3_primary_consistency_p0_090", Fraction("0.90"),
     (Fraction("0.97"), Fraction("0.98"), Fraction("0.99"))),
    ("I3_primary_consistency_p0_095", Fraction("0.95"),
     (Fraction("0.97"), Fraction("0.98"), Fraction("0.99"))),
    ("I4_competence_floor", Fraction("0.80"),
     (Fraction("0.90"), Fraction("0.95"), Fraction("0.97"))),
)

# Paired-equivalence review grid. The (margin, n) pairs mirror the drafting
# sensitivity table so the comparison is like-for-like; the nuisance treatment
# does not.
PAIRED_MARGINS = (Fraction("0.05"), Fraction("0.10"))
PAIRED_SAMPLE_SIZES = (128, 192, 256, 384)
PAIRED_ONE_SIDED_ALPHA = 0.025
PAIRED_TRUE_DIFFERENCE_FOR_POWER = 0.0

# Registered numerical-optimisation contract for the continuous nuisance
# parameter q = pi21 on the null boundary delta = margin.
NUISANCE_DOMAIN_NOTE = ("q = pi21 on the null boundary delta = +margin, with "
                        "pi12 = q + margin; feasible domain q in "
                        "[0, (1 - margin) / 2]")
NUISANCE_COARSE_GRID_POINTS = 64
NUISANCE_GOLDEN_TOLERANCE = 1e-7
NUISANCE_GOLDEN_MAX_ITERATIONS = 80
NUISANCE_ON_NONCONVERGENCE = "retain the coarse-grid maximum and flag it"
TRINOMIAL_WINDOW_SIGMA = 10.0
TRINOMIAL_WINDOW_PAD = 8

CALIBRATION_TARGETS = ((Fraction("0.10"), 192), (Fraction("0.10"), 384))
CALIBRATION_Z_TOLERANCE = 1e-4
CALIBRATION_Z_MAX_ITERATIONS = 24

PROBABILITY_DECIMALS = 9
NUISANCE_DECIMALS = 6
CHECK_ABSOLUTE_TOLERANCE = 1e-9

EMIT_BEGIN_MARKER = "=== BEGIN INDEPENDENT RECALCULATION TABLE ==="
EMIT_END_MARKER = "=== END INDEPENDENT RECALCULATION TABLE ==="

FORBIDDEN_MODULE_SUBSTRINGS = (
    "design_statistics",
    "torch",
    "transformers",
    "tokenizers",
    "numpy",
    "scipy",
    "requests",
    "urllib3",
    "httpx",
)

# This implementation is standard-library-only by construction. Declaring the
# permitted roots makes that auditable instead of aspirational.
PERMITTED_IMPORT_ROOTS = (
    "__future__",
    "argparse",
    "ast",
    "bisect",
    "fractions",
    "hashlib",
    "json",
    "math",
    "os",
    "statistics",
    "sys",
)

FORBIDDEN_DYNAMIC_CALLS = (
    "eval",
    "exec",
    "compile",
    "__import__",
    "import_module",
    "load_module",
    "spec_from_file_location",
    "module_from_spec",
    "runpy",
    "run_path",
)

ZERO_OPERATION_COUNTERS = (
    "activation_extractions",
    "bank_rows_read",
    "evidence_rows_created",
    "forward_passes",
    "generations",
    "gpu_jobs",
    "model_downloads",
    "network_calls",
    "prior_result_reads",
    "provider_calls",
    "seeds_drawn",
    "tokenizer_constructions",
    "weight_loads",
)


class RecalculationError(RuntimeError):
    """Raised whenever a fail-closed precondition is violated."""


# ---------------------------------------------------------------------------
# Fail-closed guards
# ---------------------------------------------------------------------------

def assert_independence_of_drafting_implementation() -> None:
    """Fail closed unless this module is structurally independent of the draft.

    The review is worthless if it silently re-runs the code it is reviewing, so
    independence is checked rather than asserted in prose. The check is
    deliberately about *this* module -- its own import graph and its own
    namespace -- and not about whatever else happens to be loaded in the
    process, because under the repository test runner other test modules
    legitimately import the drafting script into the same interpreter.
    """
    source = os.path.abspath(__file__)
    with open(source, "r", encoding="utf-8") as handle:
        body = handle.read()
    # A substring scan over this file's own text would be defeated by its own
    # guard list, so the check is structural: parse this module and inspect the
    # import and call nodes themselves.
    imported = set()
    for node in ast.walk(ast.parse(body)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise RecalculationError(
                    "relative imports are not allowed in this module")
            names = [node.module or ""]
        elif isinstance(node, ast.Call):
            target = node.func
            called = getattr(target, "id", None) or getattr(target, "attr", None)
            if called in FORBIDDEN_DYNAMIC_CALLS:
                raise RecalculationError(
                    "this file uses the dynamic-loading call %r, which would "
                    "let the drafting implementation back in" % called)
            continue
        else:
            continue
        for name in names:
            imported.add(name.split(".")[0])
    for name in sorted(imported):
        if name.lower() in FORBIDDEN_MODULE_SUBSTRINGS:
            raise RecalculationError(
                "this file imports %r, which is forbidden for an independent "
                "implementation" % name)
        if DRAFTING_SCRIPT_BASENAME[:-3] in name.lower():
            raise RecalculationError(
                "this file imports the drafting implementation %r" % name)
        if name not in PERMITTED_IMPORT_ROOTS:
            raise RecalculationError(
                "this file imports %r, which is outside the declared "
                "standard-library-only dependency set" % name)
    # Nothing bound in this module's namespace may originate from the drafting
    # script, which catches injection after import as well as at import time.
    for key, value in list(globals().items()):
        holder = getattr(value, "__module__", None)
        if holder and DRAFTING_SCRIPT_BASENAME[:-3] in str(holder).lower():
            raise RecalculationError(
                "global %r was supplied by the drafting implementation" % key)
        origin = getattr(sys.modules.get(str(holder)), "__file__", None) or ""
        if os.path.basename(origin) == DRAFTING_SCRIPT_BASENAME:
            raise RecalculationError(
                "global %r resolves to %s" % (key, DRAFTING_SCRIPT_BASENAME))


def validate_registered_parameters() -> None:
    """Fail closed on any out-of-domain registered parameter."""
    if not Fraction(0) < STUDY_ALPHA < Fraction(1):
        raise RecalculationError("study alpha out of range")
    if not Fraction(0) < BONFERRONI_PER_PROFILE_ALPHA < STUDY_ALPHA:
        raise RecalculationError("per-profile alpha must be below study alpha")
    if SELECTABLE_PROFILE_COUNT < 1:
        raise RecalculationError("selectable profile count must be positive")
    if not Fraction(0) < TARGET_POWER < Fraction(1):
        raise RecalculationError("target power out of range")
    for key, p0, alternatives in REVIEWED_BINOMIAL_GATES:
        if not Fraction(0) < p0 < Fraction(1):
            raise RecalculationError("null p0 out of range for %s" % key)
        if not alternatives:
            raise RecalculationError("no alternative registered for %s" % key)
        for p1 in alternatives:
            if not p0 < p1 < Fraction(1):
                raise RecalculationError(
                    "alternative %s is not strictly above the null for %s"
                    % (p1, key))
    for margin in PAIRED_MARGINS:
        if not Fraction(0) < margin < Fraction(1, 2):
            raise RecalculationError("paired margin out of range")
    for size in PAIRED_SAMPLE_SIZES:
        if size < 1:
            raise RecalculationError("paired sample size must be positive")
    if not 0.0 < PAIRED_ONE_SIDED_ALPHA < 0.5:
        raise RecalculationError("paired one-sided alpha out of range")
    if ADMISSIBLE_N_MIN < 1 or ADMISSIBLE_N_MAX < ADMISSIBLE_N_MIN:
        raise RecalculationError("admissible n range is degenerate")


# ---------------------------------------------------------------------------
# Exact binomial machinery, in exact integer arithmetic
# ---------------------------------------------------------------------------

_WEIGHT_CACHE = {}
_WEIGHT_CACHE_LIMIT = 64


def _weighted_counts(trials: int, success: Fraction):
    """Return (suffix_weights, prefix_weights, denominator) as exact integers.

    For a success probability ``a / b`` the unnormalised weight of ``j``
    successes is ``C(n, j) * a**j * (b - a)**(n - j)`` and the normaliser is
    ``b**n``. Working with these integers rather than with floating-point
    products is what makes the rejection counts below exact rather than
    approximately exact.
    """
    cached = _WEIGHT_CACHE.get((trials, success))
    if cached is not None:
        return cached
    numerator = success.numerator
    complement = success.denominator - success.numerator
    # Powers are built by repeated multiplication rather than by exponentiating
    # inside the loop; the naive form is quadratic in the number of digits and
    # dominates the whole run at the larger reviewed sample sizes.
    power_success = [1] * (trials + 1)
    power_failure = [1] * (trials + 1)
    for j in range(1, trials + 1):
        power_success[j] = power_success[j - 1] * numerator
        power_failure[j] = power_failure[j - 1] * complement
    terms = []
    coefficient = 1
    for j in range(trials + 1):
        if j:
            coefficient = coefficient * (trials - j + 1) // j
        terms.append(coefficient * power_success[j] * power_failure[trials - j])
    suffix = [0] * (trials + 2)
    for j in range(trials, -1, -1):
        suffix[j] = suffix[j + 1] + terms[j]
    prefix = [0] * (trials + 2)
    running = 0
    for j in range(trials + 1):
        running += terms[j]
        prefix[j] = running
    prefix[trials + 1] = running
    result = (suffix, prefix, success.denominator ** trials)
    if len(_WEIGHT_CACHE) >= _WEIGHT_CACHE_LIMIT:
        _WEIGHT_CACHE.clear()
    _WEIGHT_CACHE[(trials, success)] = result
    return result


def exact_upper_tail(threshold: int, trials: int, success: Fraction) -> Fraction:
    """Exact ``P(X >= threshold)`` for ``X ~ Binomial(trials, success)``."""
    if threshold <= 0:
        return Fraction(1)
    if threshold > trials:
        return Fraction(0)
    suffix, _prefix, denominator = _weighted_counts(trials, success)
    return Fraction(suffix[threshold], denominator)


def smallest_rejection_count(trials: int, null_p: Fraction,
                             alpha: Fraction) -> tuple:
    """Smallest acceptance count whose exact upper tail is at or below alpha.

    Returns ``(count, exact_tail)``. ``count`` is the smallest integer ``k``
    with ``P(X >= k | null_p) <= alpha``; observing at least ``k`` successes
    rejects the null. The comparison is done by integer cross-multiplication so
    that a tail exactly equal to alpha is accepted and no floating-point
    representation of alpha can move the boundary.
    """
    suffix, _prefix, denominator = _weighted_counts(trials, null_p)
    limit_numerator = alpha.numerator * denominator
    limit_denominator = alpha.denominator
    for count in range(0, trials + 2):
        tail_weight = suffix[count] if count <= trials + 1 else 0
        if tail_weight * limit_denominator <= limit_numerator:
            return count, Fraction(tail_weight, denominator)
    raise RecalculationError("no admissible rejection count exists")


def exact_power(trials: int, count: int, alternative: Fraction) -> Fraction:
    """Exact ``P(X >= count)`` under the alternative."""
    return exact_upper_tail(count, trials, alternative)


def central_acceptance_band(trials: int, success: Fraction,
                            alpha: Fraction) -> tuple:
    """Exact central acceptance band with each tail at or below ``alpha / 2``.

    Returns ``(lower, upper, lower_tail, upper_tail)``. This is the acceptance
    region of the exact two-sided test of ``p = success``; a count outside the
    band rejects symmetry at level ``alpha``.
    """
    suffix, prefix, denominator = _weighted_counts(trials, success)
    half = alpha / 2
    limit_numerator = half.numerator * denominator
    limit_denominator = half.denominator
    lower = 0
    for candidate in range(0, trials + 1):
        below = prefix[candidate - 1] if candidate else 0
        if below * limit_denominator <= limit_numerator:
            lower = candidate
        else:
            break
    upper = trials
    for candidate in range(trials, -1, -1):
        above = suffix[candidate + 1]
        if above * limit_denominator <= limit_numerator:
            upper = candidate
        else:
            break
    lower_tail = Fraction(prefix[lower - 1] if lower else 0, denominator)
    upper_tail = Fraction(suffix[upper + 1], denominator)
    return lower, upper, lower_tail, upper_tail


# ---------------------------------------------------------------------------
# Regularized incomplete beta, used only as an independent cross-check
# ---------------------------------------------------------------------------

def _beta_continued_fraction(x: float, a: float, b: float) -> float:
    """Modified Lentz evaluation of the continued fraction for I_x(a, b)."""
    tiny = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-16:
            return h
    raise RecalculationError("incomplete beta continued fraction stalled")


def regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta ``I_x(a, b)``."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                 + a * math.log(x) + b * math.log1p(-x))
    if log_front < -745.0:
        # The prefactor has underflowed, so the tail is zero or one to within
        # double precision and the continued fraction need not be evaluated at
        # all. Evaluating it anyway risks a spurious stall.
        return 0.0 if x < (a + 1.0) / (a + b + 2.0) else 1.0
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(x, a, b) / a
    return 1.0 - front * _beta_continued_fraction(1.0 - x, b, a) / b


def binomial_upper_tail_via_beta(threshold: int, trials: int,
                                 success: float) -> float:
    """``P(X >= threshold)`` through the published beta identity."""
    if threshold <= 0:
        return 1.0
    if threshold > trials:
        return 0.0
    return regularized_incomplete_beta(success, float(threshold),
                                       float(trials - threshold + 1))


def clopper_pearson_lower_limit(successes: int, trials: int,
                                one_sided_alpha: float) -> float:
    """One-sided Clopper-Pearson lower confidence limit.

    Defined by the published inversion ``P(X >= successes | limit) =
    one_sided_alpha``, equivalently the ``one_sided_alpha`` quantile of a
    ``Beta(successes, trials - successes + 1)`` law. Both routes are computed
    and required to agree, which is the closed-form check for this family.
    """
    if successes <= 0:
        return 0.0
    if not 0.0 < one_sided_alpha < 1.0:
        raise RecalculationError("Clopper-Pearson alpha out of range")
    low, high = 0.0, 1.0
    for _ in range(400):
        middle = 0.5 * (low + high)
        if binomial_upper_tail_via_beta(successes, trials, middle) > \
                one_sided_alpha:
            high = middle
        else:
            low = middle
        if high - low < 1e-15:
            break
    return 0.5 * (low + high)


# ---------------------------------------------------------------------------
# Paired binary equivalence, re-derived from the score equation
# ---------------------------------------------------------------------------
#
# Notation. n pairs, cell counts n11, n12, n21, n22 with cell probabilities
# p11, p12, p21, p22 and estimand delta = p12 - p21. Under the constraint
# delta = d0 write p21 = q and p12 = q + d0, so that p11 + p22 = 1 - 2q - d0.
# Profiling p11 and p22 out in proportion to n11 and n22 leaves
#
#     dL/dq = n12 / (q + d0) + n21 / q - 2 m / (1 - d0 - 2q),   m = n11 + n22
#
# and clearing denominators gives the quadratic
#
#     2 n q^2 - [ (n12 + n21) - d0 (2 n - n12 + n21) ] q - n21 d0 (1 - d0) = 0
#
# whose relevant root is the constrained maximum-likelihood nuisance estimate.
# The null variance of n12 - n21 is n (2 q + d0 (1 - d0)), so the score
# statistic is Z(d0) = (n12 - n21 - n d0) / sqrt(n (2 q + d0 (1 - d0))).
# At d0 = 0 the root collapses to q = (n12 + n21) / (2 n) and Z reduces to
# (n12 - n21) / sqrt(n12 + n21), which is McNemar's statistic: the published
# special case, reproduced here as an algebraic identity rather than by
# numerical coincidence.


def paired_null_nuisance_root(discordant_12: int, discordant_21: int,
                              pairs: int, null_difference: float) -> float:
    """Constrained maximum-likelihood estimate of ``pi21`` under the null."""
    if pairs <= 0:
        raise RecalculationError("paired sample size must be positive")
    linear = ((discordant_12 + discordant_21)
              - null_difference * (2 * pairs - discordant_12 + discordant_21))
    constant = discordant_21 * null_difference * (1.0 - null_difference)
    discriminant = linear * linear + 8.0 * pairs * constant
    if discriminant < 0.0:
        discriminant = 0.0
    root = (linear + math.sqrt(discriminant)) / (4.0 * pairs)
    if root < 0.0:
        root = 0.0
    return root


def paired_score_statistic(discordant_12: int, discordant_21: int, pairs: int,
                           null_difference: float):
    """Tango-form score statistic, or ``None`` where the null variance dies."""
    nuisance = paired_null_nuisance_root(discordant_12, discordant_21, pairs,
                                         null_difference)
    variance = pairs * (2.0 * nuisance
                        + null_difference * (1.0 - null_difference))
    if variance <= 0.0:
        return None
    numerator = discordant_12 - discordant_21 - pairs * null_difference
    return numerator / math.sqrt(variance)


def paired_equivalence_declared(discordant_12: int, discordant_21: int,
                                pairs: int, margin: float,
                                critical_value: float) -> bool:
    """Two one-sided score tests combined as an intersection-union decision.

    Equivalence is declared only when both one-sided nulls are rejected, which
    is the intersection-union construction of Berger and Hsu (1996). A merely
    non-significant difference is never equivalence.
    """
    lower = paired_score_statistic(discordant_12, discordant_21, pairs, -margin)
    if lower is None or lower <= critical_value:
        return False
    upper = paired_score_statistic(discordant_12, discordant_21, pairs, margin)
    if upper is None or upper >= -critical_value:
        return False
    return True


def paired_rejection_lattice(pairs: int, margin: float,
                             critical_value: float) -> dict:
    """Materialise the acceptance-of-equivalence region as ``n21 -> [n12]``.

    The decision depends on the data only through ``(n12, n21, n)``, so the
    region can be built once and reused for every nuisance value.
    """
    lattice = {}
    for discordant_21 in range(pairs + 1):
        row = []
        for discordant_12 in range(pairs - discordant_21 + 1):
            if paired_equivalence_declared(discordant_12, discordant_21, pairs,
                                           margin, critical_value):
                row.append(discordant_12)
        if row:
            lattice[discordant_21] = row
    return lattice


_LOG_FACTORIAL = [0.0]


def _log_factorial(upto: int):
    while len(_LOG_FACTORIAL) <= upto:
        _LOG_FACTORIAL.append(_LOG_FACTORIAL[-1]
                              + math.log(len(_LOG_FACTORIAL)))
    return _LOG_FACTORIAL


def trinomial_region_probability(lattice: dict, pairs: int, prob_12: float,
                                 prob_21: float, windowed: bool = True) -> float:
    """Total probability of a lattice region under the paired trinomial law.

    The concordant cells are collapsed because the decision never separates
    ``n11`` from ``n22``: only ``n12``, ``n21`` and ``n`` enter the statistic.
    """
    prob_other = 1.0 - prob_12 - prob_21
    if prob_12 < 0.0 or prob_21 < 0.0 or prob_other < -1e-12:
        raise RecalculationError("infeasible paired cell probabilities")
    prob_other = max(prob_other, 0.0)
    log_factorial = _log_factorial(pairs)
    log_total = log_factorial[pairs]
    neg_inf = float("-inf")
    log_12 = math.log(prob_12) if prob_12 > 0.0 else neg_inf
    log_21 = math.log(prob_21) if prob_21 > 0.0 else neg_inf
    log_other = math.log(prob_other) if prob_other > 0.0 else neg_inf

    if windowed:
        spread_12 = math.sqrt(pairs * prob_12 * (1.0 - prob_12))
        spread_21 = math.sqrt(pairs * prob_21 * (1.0 - prob_21))
        low_12 = max(0, int(pairs * prob_12
                            - TRINOMIAL_WINDOW_SIGMA * spread_12)
                     - TRINOMIAL_WINDOW_PAD)
        high_12 = min(pairs, int(pairs * prob_12
                                 + TRINOMIAL_WINDOW_SIGMA * spread_12)
                      + TRINOMIAL_WINDOW_PAD)
        low_21 = max(0, int(pairs * prob_21
                            - TRINOMIAL_WINDOW_SIGMA * spread_21)
                     - TRINOMIAL_WINDOW_PAD)
        high_21 = min(pairs, int(pairs * prob_21
                                 + TRINOMIAL_WINDOW_SIGMA * spread_21)
                      + TRINOMIAL_WINDOW_PAD)
    else:
        low_12, high_12, low_21, high_21 = 0, pairs, 0, pairs

    total = 0.0
    exp = math.exp
    for discordant_21, row in lattice.items():
        if discordant_21 < low_21 or discordant_21 > high_21:
            continue
        if log_21 == neg_inf and discordant_21:
            continue
        start = bisect_left(row, low_12)
        stop = bisect_right(row, high_12)
        if start >= stop:
            continue
        base = (log_total - log_factorial[discordant_21]
                + discordant_21 * (log_21 if discordant_21 else 0.0))
        for index in range(start, stop):
            discordant_12 = row[index]
            if log_12 == neg_inf and discordant_12:
                continue
            concordant = pairs - discordant_12 - discordant_21
            if log_other == neg_inf and concordant:
                continue
            exponent = (base - log_factorial[discordant_12]
                        - log_factorial[concordant]
                        + (discordant_12 * log_12 if discordant_12 else 0.0)
                        + (concordant * log_other if concordant else 0.0))
            if exponent > -70.0:
                total += exp(exponent)
    return total


def paired_boundary_rejection_probability(lattice: dict, pairs: int,
                                          margin: float, nuisance: float,
                                          windowed: bool = True) -> float:
    """Rejection probability at the null boundary ``delta = +margin``."""
    return trinomial_region_probability(lattice, pairs, nuisance + margin,
                                        nuisance, windowed=windowed)


def paired_size_supremum(pairs: int, margin: float, critical_value: float,
                         lattice=None, coarse_points: int = None) -> dict:
    """Maximise the boundary rejection probability over the nuisance parameter.

    The four discordance values used by the drafting sensitivity table are a
    sensitivity grid, not a size proof: the feasible nuisance domain at the
    null boundary is the whole interval ``q in [0, (1 - margin) / 2]``, which
    corresponds to a discordance rate anywhere in ``[margin, 1]``. The size of
    the procedure is the supremum over that interval, so it is computed here.
    """
    if lattice is None:
        lattice = paired_rejection_lattice(pairs, margin, critical_value)
    if coarse_points is None:
        # The boundary rejection probability is not smooth in the nuisance
        # parameter: it steps as lattice points enter and leave the region, with
        # a characteristic scale of about 1/n. A grid coarser than that can walk
        # straight past the maximum, so the resolution is tied to n.
        coarse_points = max(NUISANCE_COARSE_GRID_POINTS, 2 * pairs)
    upper_bound = (1.0 - margin) / 2.0
    grid = [upper_bound * index / coarse_points
            for index in range(coarse_points + 1)]
    values = [paired_boundary_rejection_probability(lattice, pairs, margin,
                                                    point) for point in grid]
    best_index = max(range(len(values)), key=lambda i: values[i])
    coarse_best = values[best_index]
    left = grid[max(0, best_index - 1)]
    right = grid[min(len(grid) - 1, best_index + 1)]

    golden = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = left, right
    c = b - golden * (b - a)
    d = a + golden * (b - a)
    fc = paired_boundary_rejection_probability(lattice, pairs, margin, c)
    fd = paired_boundary_rejection_probability(lattice, pairs, margin, d)
    converged = False
    iterations = 0
    for iterations in range(1, NUISANCE_GOLDEN_MAX_ITERATIONS + 1):
        if abs(b - a) < NUISANCE_GOLDEN_TOLERANCE:
            converged = True
            break
        if fc > fd:
            b, d, fd = d, c, fc
            c = b - golden * (b - a)
            fc = paired_boundary_rejection_probability(lattice, pairs, margin, c)
        else:
            a, c, fc = c, d, fd
            d = a + golden * (b - a)
            fd = paired_boundary_rejection_probability(lattice, pairs, margin, d)
    refined_point = c if fc >= fd else d
    refined_best = max(fc, fd)
    if refined_best >= coarse_best:
        best_value, best_point = refined_best, refined_point
    else:
        best_value, best_point = coarse_best, grid[best_index]
    return {
        "converged": converged,
        "golden_iterations": iterations,
        "coarse_grid_points": coarse_points,
        "nuisance_at_supremum": best_point,
        "discordance_at_supremum": 2.0 * best_point + margin,
        "coarse_grid_maximum": coarse_best,
        "size_supremum": best_value,
    }


def calibrate_paired_critical_value(pairs: int, margin: float,
                                    nominal_alpha: float) -> dict:
    """Smallest critical value whose supremum size respects the nominal level.

    This is the "calibrate a conservative critical value over the registered
    parameter domain" remedy. It is reported so that the cost of restoring size
    control is visible, not because the reviewer adopts it on the operator's
    behalf.
    """
    low = NormalDist().inv_cdf(1.0 - nominal_alpha)
    high = low + 1.5
    def supremum(value):
        lattice = paired_rejection_lattice(pairs, margin, value)
        if not lattice:
            return 0.0
        return paired_size_supremum(
            pairs, margin, value, lattice=lattice)["size_supremum"]

    baseline = supremum(low)
    if baseline <= nominal_alpha:
        return {
            "calibration_required": False,
            "nominal_critical_value": low,
            "calibrated_critical_value": low,
            "supremum_at_nominal": baseline,
            "supremum_at_calibrated": baseline,
            "iterations": 0,
        }
    iterations = 0
    for iterations in range(1, CALIBRATION_Z_MAX_ITERATIONS + 1):
        middle = 0.5 * (low + high)
        if supremum(middle) > nominal_alpha:
            low = middle
        else:
            high = middle
        if high - low < CALIBRATION_Z_TOLERANCE:
            break
    return {
        "calibration_required": True,
        "nominal_critical_value": NormalDist().inv_cdf(1.0 - nominal_alpha),
        "calibrated_critical_value": high,
        "supremum_at_nominal": baseline,
        "supremum_at_calibrated": supremum(high),
        "iterations": iterations,
    }


# ---------------------------------------------------------------------------
# Admissible sample sizes implied by the published counterbalancing design
# ---------------------------------------------------------------------------

def counterbalancing_divisors() -> dict:
    """Divisors that make a base-item count admissible."""
    position_symbol = COUNTERBALANCE_POSITION_COUNT * COUNTERBALANCE_SYMBOL_COUNT
    complete_block = position_symbol * COUNTERBALANCE_ALPHABET_COUNT
    return {
        "position_symbol_cells": position_symbol,
        "label_alphabets": COUNTERBALANCE_ALPHABET_COUNT,
        "complete_block_base_items": complete_block,
        "minimum_balance_divisor": position_symbol,
        "label_bearing_divisor": complete_block,
        "content_only_divisor": 1,
        "k6_renderings_per_base_item": COUNTERBALANCE_RENDERING_COUNT,
    }


def admissible_sample_sizes() -> list:
    divisor = counterbalancing_divisors()["label_bearing_divisor"]
    first = ((ADMISSIBLE_N_MIN + divisor - 1) // divisor) * divisor
    return list(range(first, ADMISSIBLE_N_MAX + 1, divisor))


# ---------------------------------------------------------------------------
# Closed-form and published-identity validation, independent of the draft
# ---------------------------------------------------------------------------

def validate_binomial_family() -> dict:
    """Closed-form identities that hold for any correct binomial tail."""
    worst_all_successes = 0.0
    worst_at_least_one = 0.0
    worst_symmetry = 0
    worst_beta = 0.0
    for trials in (16, 32, 64, 128, 192, 256, 384):
        for success in (Fraction("0.5"), Fraction("0.8"), Fraction("0.9"),
                        Fraction("0.95"), Fraction("0.97")):
            all_successes = exact_upper_tail(trials, trials, success)
            worst_all_successes = max(
                worst_all_successes,
                abs(float(all_successes - success ** trials)))
            at_least_one = exact_upper_tail(1, trials, success)
            closed = Fraction(1) - (Fraction(1) - success) ** trials
            worst_at_least_one = max(worst_at_least_one,
                                     abs(float(at_least_one - closed)))
            for threshold in (1, trials // 4, trials // 2, trials - 1, trials):
                exact = float(exact_upper_tail(threshold, trials, success))
                approx = binomial_upper_tail_via_beta(threshold, trials,
                                                      float(success))
                worst_beta = max(worst_beta, abs(exact - approx))
        suffix, prefix, denominator = _weighted_counts(trials, Fraction(1, 2))
        for threshold in range(trials + 1):
            left = suffix[threshold]
            right = prefix[trials - threshold]
            worst_symmetry = max(worst_symmetry, abs(left - right))
        if suffix[0] != denominator:
            raise RecalculationError("binomial masses do not sum to one")
    return {
        "identity_all_successes_max_abs_deviation": worst_all_successes,
        "identity_at_least_one_max_abs_deviation": worst_at_least_one,
        "identity_symmetry_at_p_one_half_max_abs_deviation": worst_symmetry,
        "identity_regularized_incomplete_beta_max_abs_deviation": worst_beta,
        "note": ("exact integer tails validated against closed forms and "
                 "against the published identity P(X >= k) = I_p(k, n-k+1); "
                 "no drafting output is referenced"),
    }


def validate_clopper_pearson_family() -> dict:
    """The limit must invert the exact tail, which is its definition."""
    worst_inversion = 0.0
    worst_monotone = 0.0
    previous = None
    for successes, trials, alpha in ((184, 192, 0.000625), (176, 192, 0.000625),
                                     (120, 128, 0.000625), (184, 192, 0.00125),
                                     (100, 128, 0.005), (64, 64, 0.005)):
        limit = clopper_pearson_lower_limit(successes, trials, alpha)
        if successes < trials:
            achieved = binomial_upper_tail_via_beta(successes, trials, limit)
            worst_inversion = max(worst_inversion, abs(achieved - alpha))
        else:
            worst_inversion = max(worst_inversion,
                                  abs(limit ** trials - alpha))
    for alpha in (0.05, 0.01, 0.005, 0.00125, 0.000625):
        limit = clopper_pearson_lower_limit(184, 192, alpha)
        # A smaller one-sided alpha buys a wider interval, so the lower limit
        # must be non-increasing as alpha decreases. An increase is the error.
        if previous is not None and limit > previous + 1e-15:
            worst_monotone = max(worst_monotone, limit - previous)
        previous = limit
    return {
        "inversion_max_abs_deviation": worst_inversion,
        "monotone_decreasing_in_decreasing_alpha_max_violation": worst_monotone,
        "note": ("the lower limit is defined by P(X >= x | limit) = alpha; "
                 "the check re-evaluates that tail at the returned limit"),
    }


def validate_paired_family() -> dict:
    """McNemar reduction, score-equation residual, and quantile identities."""
    worst_mcnemar = 0.0
    worst_residual = 0.0
    worst_root = 0.0
    interior_checks = 0
    boundary_solutions = 0
    infeasible_roots = 0
    for pairs in (48, 96, 128, 192):
        for discordant_12 in range(0, min(pairs, 40) + 1, 3):
            for discordant_21 in range(0, min(pairs - discordant_12, 40) + 1, 3):
                if discordant_12 + discordant_21 == 0:
                    continue
                observed = paired_score_statistic(discordant_12, discordant_21,
                                                  pairs, 0.0)
                closed = ((discordant_12 - discordant_21)
                          / math.sqrt(discordant_12 + discordant_21))
                worst_mcnemar = max(worst_mcnemar, abs(observed - closed))
                for null_difference in (-0.1, -0.05, 0.05, 0.1):
                    nuisance = paired_null_nuisance_root(
                        discordant_12, discordant_21, pairs, null_difference)
                    concordant = pairs - discordant_12 - discordant_21
                    remaining = 1.0 - 2.0 * nuisance - null_difference
                    # The quadratic residual is a polynomial identity and holds
                    # everywhere, including where the constrained maximum sits on
                    # the edge of the feasible set.
                    quadratic = (2.0 * pairs * nuisance * nuisance
                                 - ((discordant_12 + discordant_21)
                                    - null_difference
                                    * (2 * pairs - discordant_12
                                       + discordant_21)) * nuisance
                                 - discordant_21 * null_difference
                                 * (1.0 - null_difference))
                    worst_root = max(worst_root,
                                     abs(quadratic) / (2.0 * pairs))
                    if nuisance + null_difference < -1e-12:
                        infeasible_roots += 1
                        continue
                    # The score equation itself is only stationary at an
                    # interior solution; at a boundary solution the derivative
                    # is one-sided and a residual of zero is not expected.
                    if (nuisance <= 1e-9
                            or nuisance + null_difference <= 1e-9
                            or remaining <= 1e-9):
                        boundary_solutions += 1
                        continue
                    residual = (discordant_12 / (nuisance + null_difference)
                                + discordant_21 / nuisance
                                - 2.0 * concordant / remaining)
                    interior_checks += 1
                    worst_residual = max(worst_residual,
                                         abs(residual) / pairs)
    normal = NormalDist()
    quantile_deviation = max(
        abs(normal.inv_cdf(0.975) - 1.959963984540054),
        abs(normal.inv_cdf(0.995) - 2.5758293035489004),
        abs(normal.inv_cdf(0.95) - 1.6448536269514722),
    )
    return {
        "mcnemar_reduction_max_abs_deviation": worst_mcnemar,
        "score_equation_residual_max_abs_deviation": worst_residual,
        "quadratic_root_max_abs_residual": worst_root,
        "standard_normal_quantile_max_abs_deviation": quantile_deviation,
        "interior_score_equation_checks": interior_checks,
        "boundary_constrained_solutions": boundary_solutions,
        "infeasible_constrained_roots": infeasible_roots,
        "note": ("at a null difference of zero the constrained root collapses "
                 "to (n12+n21)/(2n) and the statistic becomes McNemar's; that "
                 "published special case is verified as an algebraic identity. "
                 "The constrained maximum can sit on the edge of the feasible "
                 "set, where the score equation is not stationary; those cases "
                 "are counted and checked through the polynomial residual "
                 "instead, and none of them is infeasible"),
    }


def validate_enumeration_accuracy() -> dict:
    """Windowed and unwindowed lattice sums must agree.

    This separates enumeration accuracy, which is a numerical property of the
    summation, from test size, which is a statistical property of the rule.
    Conflating the two is exactly the error the review is checking for.
    """
    margin = 0.10
    pairs = 128
    critical = NormalDist().inv_cdf(1.0 - PAIRED_ONE_SIDED_ALPHA)
    lattice = paired_rejection_lattice(pairs, margin, critical)
    worst = 0.0
    for nuisance in (0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.44):
        windowed = paired_boundary_rejection_probability(lattice, pairs, margin,
                                                         nuisance)
        exhaustive = paired_boundary_rejection_probability(
            lattice, pairs, margin, nuisance, windowed=False)
        worst = max(worst, abs(windowed - exhaustive))
    full_mass = trinomial_region_probability(
        {b: list(range(pairs - b + 1)) for b in range(pairs + 1)}, pairs,
        0.2, 0.1, windowed=False)
    return {
        "windowed_versus_exhaustive_max_abs_deviation": worst,
        "total_lattice_mass_max_abs_deviation_from_one": abs(full_mass - 1.0),
        "note": ("enumeration accuracy only; it says nothing about whether the "
                 "asymptotic decision rule attains its nominal level"),
    }


# ---------------------------------------------------------------------------
# Table construction
# ---------------------------------------------------------------------------

def _round(value, decimals=PROBABILITY_DECIMALS):
    return round(float(value), decimals)


def _decimal_key(value) -> str:
    """Render a Fraction probability as a plain decimal string.

    ``str(Fraction("0.9"))`` is ``"9/10"``, which would make the emitted keys
    both unreadable and impossible to line up against the drafting table.
    """
    return format(float(value), ".10g")


def _binomial_evidence() -> dict:
    """One pass over the admissible grid, with n outermost.

    Iterating sample size outermost keeps the exact-integer weight arrays for a
    single n resident while every gate, alpha and alternative that needs them is
    evaluated, which is what makes the exact-arithmetic route affordable at the
    upper end of the reviewed grid.
    """
    evidence = {}
    for size in admissible_sample_sizes():
        # Only one sample size is ever resident, which bounds the memory held by
        # the exact-integer weight arrays.
        _WEIGHT_CACHE.clear()
        for gate, null_p, alternatives in REVIEWED_BINOMIAL_GATES:
            for alpha_key, alpha in REVIEWED_ALPHAS:
                count, tail = smallest_rejection_count(size, null_p, alpha)
                feasible = count <= size
                power = {}
                for alternative in alternatives:
                    power[_decimal_key(alternative)] = (
                        float(exact_power(size, count, alternative))
                        if feasible else 0.0)
                evidence[(gate, alpha_key, size)] = {
                    "rejection_count": count,
                    "exact_null_tail": tail,
                    "feasible": feasible,
                    "power": power,
                }
    return evidence


def build_exact_binomial_grid(evidence: dict) -> list:
    grid = []
    sizes = admissible_sample_sizes()
    for gate, null_p, alternatives in REVIEWED_BINOMIAL_GATES:
        for alpha_key, alpha in REVIEWED_ALPHAS:
            rows = []
            for size in sizes:
                found = evidence[(gate, alpha_key, size)]
                rows.append({
                    "n_base_items_per_atomic_cell": size,
                    "rejection_count": found["rejection_count"],
                    "rejection_rate": _round(
                        Fraction(found["rejection_count"], size)),
                    "exact_null_tail": _round(found["exact_null_tail"], 12),
                    "feasible": found["feasible"],
                    "power_at_alternative": {
                        key: _round(value)
                        for key, value in found["power"].items()},
                })
            grid.append({
                "gate": gate,
                "null_p0": float(null_p),
                "alpha_key": alpha_key,
                "alpha": float(alpha),
                "alternatives": [float(value) for value in alternatives],
                "rows": rows,
            })
    return grid


def build_smallest_admissible_n(evidence: dict) -> list:
    """Smallest admissible n reaching target power, respecting discreteness."""
    out = []
    sizes = admissible_sample_sizes()
    target = float(TARGET_POWER)
    for gate, _null_p, alternatives in REVIEWED_BINOMIAL_GATES:
        for alpha_key, alpha in REVIEWED_ALPHAS:
            for alternative in alternatives:
                key = _decimal_key(alternative)
                powers = []
                for size in sizes:
                    found = evidence[(gate, alpha_key, size)]
                    powers.append(found["power"][key] if found["feasible"]
                                  else 0.0)
                monotone = all(powers[index] >= powers[index - 1] - 1e-12
                               for index in range(1, len(powers)))
                first_reached = None
                for index, size in enumerate(sizes):
                    if powers[index] >= target:
                        first_reached = size
                        break
                # Exact-binomial power is not monotone in n, because the
                # rejection count moves in integer steps. The reported value is
                # therefore the smallest reviewed n from which every larger
                # reviewed n also holds the target, not merely the first n that
                # happens to touch it.
                stable = None
                for index, size in enumerate(sizes):
                    if all(value >= target for value in powers[index:]):
                        stable = size
                        break
                out.append({
                    "gate": gate,
                    "alpha_key": alpha_key,
                    "alpha": float(alpha),
                    "alternative_p1": float(alternative),
                    "target_power": target,
                    "first_admissible_n_reaching_target": first_reached,
                    "smallest_admissible_n_holding_target_thereafter": stable,
                    "power_monotone_over_reviewed_grid": monotone,
                })
    return out


def build_label_uniformity_bands() -> list:
    bands = []
    labels = 4
    alpha = STUDY_ALPHA / labels
    for size in (192, 384, 768):
        lower, upper, lower_tail, upper_tail = central_acceptance_band(
            size, Fraction(1, labels), alpha)
        wide_lower, wide_upper, _lt, _ut = central_acceptance_band(
            size, Fraction(1, labels), alpha * 2)
        bands.append({
            "n_base_items_per_atomic_cell": size,
            "labels": labels,
            "expected_per_label": _round(Fraction(size, labels)),
            "bonferroni_alpha": float(alpha),
            "acceptance_band_each_tail_at_most_half_alpha": [lower, upper],
            "achieved_lower_tail": _round(lower_tail, 12),
            "achieved_upper_tail": _round(upper_tail, 12),
            "alternative_band_each_tail_at_most_alpha": [wide_lower, wide_upper],
            "applies_to": ("label-bearing profiles only; not_applicable for "
                           "content-only profiles"),
        })
    return bands


def build_clopper_pearson_rows() -> list:
    rows = []
    for cells in (4, 8, 12, 24):
        simultaneous = STUDY_ALPHA / cells
        for successes, size in ((184, 192), (176, 192), (120, 128)):
            one_sided = float(simultaneous)
            halved = one_sided / 2.0
            rows.append({
                "cells": cells,
                "n_base_items_per_atomic_cell": size,
                "successes": successes,
                "simultaneous_alpha": float(simultaneous),
                "lower_limit_one_sided_at_alpha": _round(
                    clopper_pearson_lower_limit(successes, size, one_sided), 6),
                "lower_limit_one_sided_at_half_alpha": _round(
                    clopper_pearson_lower_limit(successes, size, halved), 6),
                "authority": "descriptive_only_no_gate_authority",
            })
    return rows


def build_paired_tables() -> dict:
    critical = NormalDist().inv_cdf(1.0 - PAIRED_ONE_SIDED_ALPHA)
    size_rows = []
    power_rows = []
    for margin in PAIRED_MARGINS:
        margin_value = float(margin)
        for pairs in PAIRED_SAMPLE_SIZES:
            lattice = paired_rejection_lattice(pairs, margin_value, critical)
            supremum = paired_size_supremum(pairs, margin_value, critical,
                                            lattice=lattice)
            grid_rows = []
            for discordance in (0.05, 0.10, 0.20, 0.30):
                nuisance = (discordance - margin_value) / 2.0
                if nuisance < 0.0:
                    grid_rows.append({
                        "discordance_rate": discordance,
                        "feasible_at_null_boundary": False,
                        "boundary_rejection_probability": None,
                    })
                    continue
                grid_rows.append({
                    "discordance_rate": discordance,
                    "feasible_at_null_boundary": True,
                    "boundary_rejection_probability": _round(
                        paired_boundary_rejection_probability(
                            lattice, pairs, margin_value, nuisance)),
                })
            size_rows.append({
                "margin": margin_value,
                "n_base_items_per_atomic_cell": pairs,
                "nominal_one_sided_alpha": PAIRED_ONE_SIDED_ALPHA,
                "nominal_critical_value": _round(critical, 12),
                "nuisance_domain": NUISANCE_DOMAIN_NOTE,
                "feasible_discordance_range": [margin_value, 1.0],
                "drafting_grid_rows": grid_rows,
                "size_supremum_over_feasible_boundary": _round(
                    supremum["size_supremum"]),
                "nuisance_at_supremum": _round(supremum["nuisance_at_supremum"],
                                               NUISANCE_DECIMALS),
                "discordance_at_supremum": _round(
                    supremum["discordance_at_supremum"], NUISANCE_DECIMALS),
                "coarse_grid_maximum": _round(supremum["coarse_grid_maximum"]),
                "nuisance_grid_points": supremum["coarse_grid_points"],
                "supremum_is_a_lower_bound": True,
                "inference_direction": ("a finite grid can only bound the "
                                        "supremum from below, so an exceedance "
                                        "found here is real while the absence "
                                        "of one is never proof of size "
                                        "control"),
                "golden_section_converged": supremum["converged"],
                "golden_section_iterations": supremum["golden_iterations"],
                "exceeds_nominal_one_sided_alpha":
                    supremum["size_supremum"] > PAIRED_ONE_SIDED_ALPHA,
            })
            power_grid = []
            for discordance in (0.05, 0.10, 0.20, 0.30):
                achieved = trinomial_region_probability(
                    lattice, pairs, discordance / 2.0, discordance / 2.0)
                power_grid.append({
                    "discordance_rate": discordance,
                    "exact_power": _round(achieved),
                    "meets_target_power": achieved >= float(TARGET_POWER),
                })
            power_rows.append({
                "margin": margin_value,
                "n_base_items_per_atomic_cell": pairs,
                "true_difference": PAIRED_TRUE_DIFFERENCE_FOR_POWER,
                "discordance_rate_rows": power_grid,
            })
    calibration = []
    for margin, pairs in CALIBRATION_TARGETS:
        result = calibrate_paired_critical_value(pairs, float(margin),
                                                 PAIRED_ONE_SIDED_ALPHA)
        calibrated = result["calibrated_critical_value"]
        lattice = paired_rejection_lattice(pairs, float(margin), calibrated)
        power_at_calibrated = []
        for discordance in (0.05, 0.10, 0.20, 0.30):
            power_at_calibrated.append({
                "discordance_rate": discordance,
                "exact_power": _round(trinomial_region_probability(
                    lattice, pairs, discordance / 2.0, discordance / 2.0)),
            })
        calibration.append({
            "margin": float(margin),
            "n_base_items_per_atomic_cell": pairs,
            "nominal_one_sided_alpha": PAIRED_ONE_SIDED_ALPHA,
            "calibration_required": result["calibration_required"],
            "nominal_critical_value": _round(result["nominal_critical_value"],
                                             12),
            "calibrated_critical_value": _round(calibrated, 6),
            "size_supremum_at_nominal_critical_value": _round(
                result["supremum_at_nominal"]),
            "size_supremum_at_calibrated_critical_value": _round(
                result["supremum_at_calibrated"]),
            "bisection_iterations": result["iterations"],
            "power_at_calibrated_critical_value": power_at_calibrated,
        })
    return {
        "rejection_rule": {
            "estimand": "delta = pi12 - pi21 on paired base-item indicators",
            "statistic": ("Tango (1998) constrained-score statistic Z(d0) = "
                          "(n12 - n21 - n d0) / sqrt(n (2 q~ + d0 (1 - d0))) "
                          "with q~ the constrained maximum-likelihood pi21"),
            "constrained_root": ("2 n q^2 - [(n12 + n21) - d0 (2n - n12 + n21)] "
                                 "q - n21 d0 (1 - d0) = 0, positive root"),
            "decision": ("intersection-union: equivalence is declared only if "
                         "Z(-margin) > z_(1-alpha) and Z(+margin) < "
                         "-z_(1-alpha); a non-significant difference is never "
                         "equivalence"),
            "one_sided_alpha": PAIRED_ONE_SIDED_ALPHA,
            "critical_value": _round(critical, 12),
            "exactness_scope": ("the enumeration of the joint law of (n12, n21) "
                                "is exact; the decision rule itself is "
                                "asymptotic and is not conservative by "
                                "construction"),
            "nuisance_optimisation": {
                "domain": NUISANCE_DOMAIN_NOTE,
                "coarse_grid_points": NUISANCE_COARSE_GRID_POINTS,
                "coarse_grid_points_rule": ("max(64, 2n), so that the grid is "
                                            "finer than the 1/n scale on which "
                                            "the lattice region changes"),
                "bracketing": "coarse argmax with its two neighbours",
                "refinement": "golden-section search",
                "tolerance": NUISANCE_GOLDEN_TOLERANCE,
                "max_iterations": NUISANCE_GOLDEN_MAX_ITERATIONS,
                "on_nonconvergence": NUISANCE_ON_NONCONVERGENCE,
                "independent_validation": ("windowed and exhaustive lattice "
                                           "sums are compared, and the refined "
                                           "maximum is never allowed to fall "
                                           "below the coarse-grid maximum"),
            },
        },
        "size_over_feasible_null_boundary": size_rows,
        "power_at_nominal_critical_value": power_rows,
        "conservative_critical_value_calibration": calibration,
    }


def build_multiplicity_decision() -> dict:
    per_profile = BONFERRONI_PER_PROFILE_ALPHA
    implemented_rows = []
    for gate, null_p, _alternatives in REVIEWED_BINOMIAL_GATES:
        at_study, _t1 = smallest_rejection_count(192, null_p, STUDY_ALPHA)
        at_profile, _t2 = smallest_rejection_count(192, null_p, per_profile)
        implemented_rows.append({
            "gate": gate,
            "n_base_items_per_atomic_cell": 192,
            "rejection_count_at_alpha_0_005": at_study,
            "rejection_count_at_per_profile_alpha": at_profile,
            "counts_differ": at_study != at_profile,
        })
    return {
        "family_A_within_profile": {
            "type": "intersection_union_conjunctive",
            "claim": ("the size of an intersection-union test is bounded by "
                      "the level of its components, so the conjunction needs "
                      "no inflation correction"),
            "source": "Berger and Hsu (1996), Statistical Science 11(4)",
            "reviewer_verdict": "valid as stated for the within-profile claim",
        },
        "family_B_across_profiles": {
            "type": "union_selection",
            "stated_per_profile_alpha": float(per_profile),
            "stated_study_alpha": float(STUDY_ALPHA),
            "selectable_profile_count": SELECTABLE_PROFILE_COUNT,
            "implemented_component_alpha_in_drafting_tables": float(STUDY_ALPHA),
            "union_bound_delivered_by_component_alpha_0_005": float(
                STUDY_ALPHA * SELECTABLE_PROFILE_COUNT),
            "rejection_counts_at_each_level": implemented_rows,
            "reviewer_verdict": ("the stated per-profile level is not delivered "
                                 "by any committed component rule; at component "
                                 "alpha 0.005 the union bound is 0.015, three "
                                 "times the stated study alpha"),
        },
    }


def build_projected_cells_and_operations() -> dict:
    """Model-free planning arithmetic. Every executed count stays at zero."""
    divisors = counterbalancing_divisors()
    variants = {
        "S1_label_bearing": {
            "position_and_symbol_variants_per_base_item":
                divisors["position_symbol_cells"],
            "label_alphabet_variants_per_base_item":
                COUNTERBALANCE_ALPHABET_COUNT,
            "rendering_variants_per_base_item": COUNTERBALANCE_RENDERING_COUNT,
            "applicable_variants_per_base_item":
                divisors["position_symbol_cells"]
                * COUNTERBALANCE_ALPHABET_COUNT
                * COUNTERBALANCE_RENDERING_COUNT,
        },
        "S2_content_only": {
            "position_and_symbol_variants_per_base_item": 0,
            "label_alphabet_variants_per_base_item": 0,
            "rendering_variants_per_base_item": COUNTERBALANCE_RENDERING_COUNT,
            "applicable_variants_per_base_item": COUNTERBALANCE_RENDERING_COUNT,
        },
        "S3_content_only": {
            "position_and_symbol_variants_per_base_item": 0,
            "label_alphabet_variants_per_base_item": 0,
            "rendering_variants_per_base_item": COUNTERBALANCE_RENDERING_COUNT,
            "applicable_variants_per_base_item": COUNTERBALANCE_RENDERING_COUNT,
        },
        "S4_diagnostic_never_selectable": {
            "position_and_symbol_variants_per_base_item":
                divisors["position_symbol_cells"],
            "label_alphabet_variants_per_base_item":
                COUNTERBALANCE_ALPHABET_COUNT,
            "rendering_variants_per_base_item": COUNTERBALANCE_RENDERING_COUNT,
            "applicable_variants_per_base_item":
                divisors["position_symbol_cells"]
                * COUNTERBALANCE_ALPHABET_COUNT
                * COUNTERBALANCE_RENDERING_COUNT,
        },
    }
    return {
        "unit_definitions": {
            "base_item": ("one registered question stem; the sampling unit and "
                          "the independent unit for every derived variant"),
            "derived_variant": ("one rendered presentation of a base item under "
                                "one (position, symbol, alphabet, rendering) "
                                "condition"),
            "scored_row": "one derived variant scored under one (profile, role)",
            "n_symbol_meaning": ("throughout this review, n always means base "
                                 "items per atomic cell, never derived variants "
                                 "and never total calls"),
        },
        "variants_per_base_item_by_profile": variants,
        "counterbalancing_divisors": divisors,
        "note": ("this is planning arithmetic only; it authorises nothing and "
                 "every executed operation count below remains zero"),
        "executed_operation_counts": {name: 0
                                      for name in ZERO_OPERATION_COUNTERS},
    }


def compare_with_drafting_tables(independent: dict, drafting_path: str) -> dict:
    """Compare the independent values with the drafting table, after the fact."""
    if not os.path.exists(drafting_path):
        return {"available": False,
                "note": "drafting table absent; comparison skipped"}
    with open(drafting_path, "r", encoding="utf-8") as handle:
        drafting = json.load(handle)

    rows = []
    grid_index = {}
    for block in independent["exact_binomial_gate_grid"]:
        for row in block["rows"]:
            grid_index[(block["gate"], block["alpha"],
                        row["n_base_items_per_atomic_cell"])] = row

    gate_map = {
        "I1a": "I1a_trivial_recovery",
        "I1b": "I1b_symbol_binding",
        "I2": "I2_primitive_headroom",
    }
    for entry in drafting.get("retained_exact_binomial_gates", []):
        key = (gate_map[entry["gate"]], entry["alpha"], entry["n"])
        mine = grid_index.get(key)
        rows.append({
            "family": "retained_exact_binomial_gates",
            "identifier": "%s n=%d alpha=%s" % (entry["gate"], entry["n"],
                                                entry["alpha"]),
            "drafting_rejection_count": entry["acceptance_count"],
            "independent_rejection_count": mine["rejection_count"] if mine
            else None,
            "agree": bool(mine and mine["rejection_count"]
                          == entry["acceptance_count"]),
        })
    for entry in drafting.get("i4_competence_floor_thresholds", []):
        key = ("I4_competence_floor", entry["alpha"], entry["n"])
        mine = grid_index.get(key)
        rows.append({
            "family": "i4_competence_floor_thresholds",
            "identifier": "I4 n=%d alpha=%s" % (entry["n"], entry["alpha"]),
            "drafting_rejection_count": entry["acceptance_count"],
            "independent_rejection_count": mine["rejection_count"] if mine
            else None,
            "agree": bool(mine and mine["rejection_count"]
                          == entry["acceptance_count"]),
        })
    for entry in drafting.get("i3_primary_item_level_consistency", []):
        gate = ("I3_primary_consistency_p0_090"
                if entry["null_hypothesis"] == "p <= 0.9"
                else "I3_primary_consistency_p0_095")
        mine = grid_index.get((gate, entry["alpha"], entry["n"]))
        rows.append({
            "family": "i3_primary_item_level_consistency",
            "identifier": "%s n=%d alpha=%s" % (entry["null_hypothesis"],
                                                entry["n"], entry["alpha"]),
            "drafting_rejection_count": entry["acceptance_count"],
            "independent_rejection_count": mine["rejection_count"] if mine
            else None,
            "agree": bool(mine and mine["rejection_count"]
                          == entry["acceptance_count"]),
        })

    band_rows = []
    mine_bands = {row["n_base_items_per_atomic_cell"]: row
                  for row in independent["label_selection_uniformity_bands"]}
    for entry in drafting.get("label_selection_uniformity_bands", []):
        mine = mine_bands.get(entry["n"])
        band_rows.append({
            "n": entry["n"],
            "drafting_band": entry["acceptance_band"],
            "independent_band_each_tail_at_most_half_alpha":
                mine["acceptance_band_each_tail_at_most_half_alpha"] if mine
                else None,
            "independent_band_each_tail_at_most_alpha":
                mine["alternative_band_each_tail_at_most_alpha"] if mine
                else None,
            "agree_with_half_alpha_convention": bool(
                mine and mine["acceptance_band_each_tail_at_most_half_alpha"]
                == entry["acceptance_band"]),
            "agree_with_alpha_convention": bool(
                mine and mine["alternative_band_each_tail_at_most_alpha"]
                == entry["acceptance_band"]),
        })

    paired_rows = []
    mine_paired = {(row["margin"], row["n_base_items_per_atomic_cell"]): row
                   for row in independent["paired_equivalence"]
                   ["size_over_feasible_null_boundary"]}
    drafting_max = 0.0
    for entry in drafting.get("i3_secondary_paired_equivalence_sensitivity", []):
        value = entry.get("exact_type_i_at_margin")
        if value is not None:
            drafting_max = max(drafting_max, value)
    for (margin, pairs), row in sorted(mine_paired.items()):
        paired_rows.append({
            "margin": margin,
            "n": pairs,
            "independent_size_supremum":
                row["size_supremum_over_feasible_boundary"],
            "independent_discordance_at_supremum":
                row["discordance_at_supremum"],
            "drafting_grid_covers_that_discordance":
                row["discordance_at_supremum"] <= 0.30 + 1e-9,
            "exceeds_nominal_one_sided_alpha":
                row["exceeds_nominal_one_sided_alpha"],
        })
    verification = drafting.get("paired_method_verification", {})
    checked = verification.get("exact_type_i_at_boundary", [])

    return {
        "available": True,
        "exact_binomial_rows": rows,
        "exact_binomial_all_agree": all(row["agree"] for row in rows),
        "label_uniformity_rows": band_rows,
        "paired_size_rows": paired_rows,
        "drafting_maximum_recorded_type_i": drafting_max,
        "drafting_verification_configurations_checked": len(checked),
        "drafting_verification_discordance_values_checked": sorted(
            {row["discordance"] for row in checked}),
        "note": ("agreement on the exact-binomial family is expected because "
                 "both implementations evaluate the same closed-form law; it "
                 "is not evidence that the design is correct, and it carries "
                 "no weight for the paired family, where the two "
                 "implementations answer different questions"),
    }


def build_review_tables(drafting_path: str) -> dict:
    validate_registered_parameters()
    evidence = _binomial_evidence()
    tables = {
        "admissible_n_rule": {
            "statement": ("a base-item count is admissible for a label-bearing "
                          "gate only if it is a multiple of the complete "
                          "counterbalancing block"),
            "divisors": counterbalancing_divisors(),
            "reviewed_grid": admissible_sample_sizes(),
            "reviewed_grid_min": ADMISSIBLE_N_MIN,
            "reviewed_grid_max": ADMISSIBLE_N_MAX,
        },
        "closed_form_validation": {
            "binomial_family": validate_binomial_family(),
            "clopper_pearson_family": validate_clopper_pearson_family(),
            "paired_family": validate_paired_family(),
            "enumeration_accuracy": validate_enumeration_accuracy(),
        },
        "declared_assumptions": {
            "i4_competence_floor": 0.8,
            "selectable_surface_count": SELECTABLE_PROFILE_COUNT,
            "study_alpha": float(STUDY_ALPHA),
            "target_power": float(TARGET_POWER),
        },
        "descriptive_clopper_pearson_lower_bounds": build_clopper_pearson_rows(),
        "document_class": "independent_methods_recalculation",
        "exact_binomial_gate_grid": build_exact_binomial_grid(evidence),
        "independence_declaration": {
            "drafting_script_imported": False,
            "drafting_script_executed": False,
            "drafting_table_read": "comparison stage only, as inert data",
            "reimplementation_basis": ("primary sources and protocol "
                                       "definitions"),
            "standard_library_only": True,
            "permitted_import_roots": list(PERMITTED_IMPORT_ROOTS),
            "independence_guard": ("structural: this module's own import and "
                                   "call graph is parsed and its namespace is "
                                   "checked for objects originating in "
                                   + DRAFTING_SCRIPT_BASENAME),
        },
        "label_selection_uniformity_bands": build_label_uniformity_bands(),
        "multiplicity_decision": build_multiplicity_decision(),
        "operation_counts": {name: 0 for name in ZERO_OPERATION_COUNTERS},
        "paired_equivalence": build_paired_tables(),
        "projected_cells_and_operations": build_projected_cells_and_operations(),
        "review_version": REVIEW_VERSION,
        "smallest_admissible_n_reaching_target_power":
            build_smallest_admissible_n(evidence),
        "status": STATUS_LINE,
    }
    tables["drafting_table_comparison"] = compare_with_drafting_tables(
        tables, drafting_path)
    return tables


# ---------------------------------------------------------------------------
# Emit / check
# ---------------------------------------------------------------------------

def _canonical(document) -> str:
    return json.dumps(document, indent=2, sort_keys=True,
                      ensure_ascii=True) + "\n"


def _sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _deviations(left, right, path="$", out=None, stats=None):
    if out is None:
        out = []
    if stats is None:
        stats = {"max_abs": 0.0}
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                out.append((path + "." + str(key), "missing", None))
            else:
                _deviations(left[key], right[key], path + "." + str(key), out,
                            stats)
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            out.append((path, "length %d vs %d" % (len(left), len(right)), None))
        else:
            for index, (a, b) in enumerate(zip(left, right)):
                _deviations(a, b, "%s[%d]" % (path, index), out, stats)
    elif isinstance(left, bool) or isinstance(right, bool):
        if left != right:
            out.append((path, "%r vs %r" % (left, right), None))
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        delta = abs(float(left) - float(right))
        if delta > stats["max_abs"]:
            stats["max_abs"] = delta
        if delta > CHECK_ABSOLUTE_TOLERANCE:
            out.append((path, "%r vs %r" % (left, right), delta))
    elif left != right:
        out.append((path, "%r vs %r" % (left, right), None))
    return out, stats


def main(argv=None) -> int:
    assert_independence_of_drafting_implementation()
    parser = argparse.ArgumentParser(
        description="Independent recalculation of the Study 3 draft-v0.2 "
                    "design statistics.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--emit", action="store_true",
                       help="write this implementation's own review table")
    group.add_argument("--check", action="store_true",
                       help="recompute and compare against the committed table")
    parser.add_argument("--out", default=None,
                        help="destination for --emit (default: alongside this "
                             "file)")
    args = parser.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    review_path = args.out or os.path.join(here, REVIEW_TABLE_BASENAME)
    drafting_path = os.path.join(here, DRAFTING_TABLE_BASENAME)

    tables = build_review_tables(drafting_path)
    rendered = _canonical(tables)

    if args.emit:
        if args.out == "-":
            # The review calculation is executed only in the container, so the
            # emitted document has to leave through the run log rather than
            # through a file the operator cannot reach.
            print(EMIT_BEGIN_MARKER)
            sys.stdout.write(rendered)
            print(EMIT_END_MARKER)
            print("INDEPENDENT_RECALCULATION_EMITTED=stdout")
        else:
            with open(review_path, "w", encoding="utf-8",
                      newline="\n") as handle:
                handle.write(rendered)
            print("INDEPENDENT_RECALCULATION_EMITTED=%s" % review_path)
        print("INDEPENDENT_RECALCULATION_BYTES=%d"
              % len(rendered.encode("utf-8")))
        print("INDEPENDENT_RECALCULATION_SHA256=%s"
              % _sha256_of_text(rendered))
        print("STATUS=%s" % STATUS_LINE)
        return 0

    if not os.path.exists(review_path):
        print("INDEPENDENT_RECALCULATION_CHECK_FAILED=missing %s" % review_path)
        return 1
    with open(review_path, "r", encoding="utf-8") as handle:
        committed = json.load(handle)
    problems, stats = _deviations(committed, tables)
    if problems:
        for path, description, delta in problems[:40]:
            print("MISMATCH %s: %s%s"
                  % (path, description,
                     "" if delta is None else " (delta %.3g)" % delta))
        print("INDEPENDENT_RECALCULATION_CHECK_FAILED=%d" % len(problems))
        return 1
    print("INDEPENDENT_RECALCULATION_CHECK_OK=1")
    print("CHECK_MAX_ABS_DEVIATION=%.3g" % stats["max_abs"])
    print("STATUS=%s" % STATUS_LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
