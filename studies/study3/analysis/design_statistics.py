"""Study 3 design-statistics derivation instrument (model-free).

This script is part of the Study 3 *design* packet. It performs no model
operation of any kind: no download, no weight load, no tokenizer construction,
no forward pass, no generation, no activation extraction, no probe, no patch,
no ablation, no lens operation, no GPU work and no provider call. It draws no
seed, writes no task-bank row, and produces no scientific evidence row.

Everything it emits is a *design parameter* computed by exact model-free
arithmetic from declared numeric assumptions. Nothing here is a measurement,
and nothing here is frozen: the sample sizes, alphas, margins and floors below
are v0.2 planning proposals that remain subject to the independent methods
review recorded as OD5 and OD6.

Usage
-----
    python studies/study3/analysis/design_statistics.py --emit
    python studies/study3/analysis/design_statistics.py --check

``--emit`` regenerates ``design_statistics_tables.json`` beside this file.
``--check`` recomputes every table and compares it value-for-value against the
committed JSON, exiting non-zero on any difference. ``--check`` is the mode used
by the committed tests and by CPU-only Azure validation.

The script is fail-closed. If a declared method cannot be implemented and
independently verified - in particular if Tango's paired score interval fails
its published McNemar reduction, disagrees with a direct numerical maximisation
of the constrained likelihood, or fails exact enumeration of its own type-I
error - the script raises and produces no tables.

Standard library only, by design: the validation image installs
``requirements.lock.txt``, which contains no statistics or schema dependency.
"""

import argparse
import json
import math
import os
import sys

# --------------------------------------------------------------------------
# Declared design assumptions. These are proposals, not frozen decisions.
# --------------------------------------------------------------------------

STUDY_ALPHA = 0.005
SELECTABLE_SURFACE_COUNT = 3          # S1, S2, S3. S4 is never selectable.
TARGET_POWER = 0.90

TOLERANCE = 1e-12


# --------------------------------------------------------------------------
# Exact binomial machinery
# --------------------------------------------------------------------------

def binom_pmf(k, n, p):
    """Exact-arithmetic binomial pmf, evaluated in floating point."""
    if k < 0 or k > n:
        return 0.0
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0 if k == n else 0.0
    return math.comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k))


def binom_upper_tail(x, n, p):
    """P[X >= x] for X ~ Binomial(n, p)."""
    if x <= 0:
        return 1.0
    if x > n:
        return 0.0
    return math.fsum(binom_pmf(k, n, p) for k in range(x, n + 1))


def binom_lower_tail(x, n, p):
    """P[X <= x] for X ~ Binomial(n, p)."""
    if x < 0:
        return 0.0
    if x >= n:
        return 1.0
    return math.fsum(binom_pmf(k, n, p) for k in range(0, x + 1))


def exact_one_sided_threshold(n, p0, alpha):
    """Smallest x with P[X >= x | p0] <= alpha. None if no such x exists."""
    for x in range(0, n + 1):
        if binom_upper_tail(x, n, p0) <= alpha:
            return x
    return None


def clopper_pearson_lower(x, n, alpha_one_sided):
    """Exact Clopper-Pearson lower confidence bound by tail inversion."""
    if x <= 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if binom_upper_tail(x, n, mid) < alpha_one_sided:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def central_acceptance_band(n, p, alpha):
    """Exact central acceptance band [lo, hi] with each tail <= alpha/2."""
    lo = 0
    while lo <= n and binom_lower_tail(lo, n, p) < alpha / 2.0:
        lo += 1
    hi = n
    while hi >= 0 and binom_upper_tail(hi, n, p) < alpha / 2.0:
        hi -= 1
    return [lo, hi]


# --------------------------------------------------------------------------
# Tango (1998) score interval for the difference of paired proportions
#
# Tango T. "Equivalence test and confidence interval for the difference in
# proportions for the paired-sample design." Statistics in Medicine 17(8),
# 891-908, 1998 (PMID 9595618).
#
# Notation: n pairs; n12 = discordant favouring the first condition, n21 =
# discordant favouring the second; delta = p12 - p21. Under H0: delta = d0 the
# constrained MLE of p21 solves
#
#     2n q^2 - [ (n12 + n21) - d0 (2n - n12 + n21) ] q - n21 d0 (1 - d0) = 0
#
# and the score statistic is
#
#     Z(d0) = (n12 - n21 - n d0) / sqrt( n ( 2 q~ + d0 (1 - d0) ) ).
#
# Both the quadratic and the variance form are verified below, against a direct
# numerical maximisation of the constrained likelihood and against the
# published property that Z(0) reduces exactly to McNemar's statistic.
# --------------------------------------------------------------------------

def tango_constrained_p21(n12, n21, n, d0):
    """Constrained MLE of p21 under delta = d0, by the closed-form root."""
    a = 2.0 * n
    b = -((n12 + n21) - d0 * (2.0 * n - n12 + n21))
    c = -n21 * d0 * (1.0 - d0)
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        disc = 0.0
    root = (-b + math.sqrt(disc)) / (2.0 * a)
    return max(root, 0.0)


def tango_statistic(n12, n21, n, d0):
    """Tango's score statistic Z(d0)."""
    q = tango_constrained_p21(n12, n21, n, d0)
    var = n * (2.0 * q + d0 * (1.0 - d0))
    if var <= 0.0:
        return 0.0 if (n12 - n21 - n * d0) == 0 else math.copysign(math.inf,
                                                                   n12 - n21 - n * d0)
    return (n12 - n21 - n * d0) / math.sqrt(var)


def _constrained_loglik(n11, n12, n21, n22, q, d0):
    """Profile log-likelihood at p21 = q under the constraint p12 - p21 = d0."""
    p12 = q + d0
    if q <= 0.0 or p12 <= 0.0:
        return -math.inf
    rest = 1.0 - 2.0 * q - d0
    if rest <= 0.0:
        return -math.inf
    m = n11 + n22
    if m == 0:
        p11 = p22 = 0.0
        total = 0.0
    else:
        p11 = n11 * rest / m
        p22 = n22 * rest / m
        total = 0.0
        if n11:
            if p11 <= 0.0:
                return -math.inf
            total += n11 * math.log(p11)
        if n22:
            if p22 <= 0.0:
                return -math.inf
            total += n22 * math.log(p22)
    if n12:
        total += n12 * math.log(p12)
    if n21:
        total += n21 * math.log(q)
    return total


def _numeric_constrained_p21(n11, n12, n21, n22, d0):
    """Golden-section maximisation of the constrained likelihood, for checking."""
    lo, hi = 1e-12, max((1.0 - d0) / 2.0 - 1e-12, 1e-11)
    phi = (math.sqrt(5.0) - 1.0) / 2.0
    x1 = hi - phi * (hi - lo)
    x2 = lo + phi * (hi - lo)
    f1 = _constrained_loglik(n11, n12, n21, n22, x1, d0)
    f2 = _constrained_loglik(n11, n12, n21, n22, x2, d0)
    for _ in range(400):
        if f1 < f2:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + phi * (hi - lo)
            f2 = _constrained_loglik(n11, n12, n21, n22, x2, d0)
        else:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - phi * (hi - lo)
            f1 = _constrained_loglik(n11, n12, n21, n22, x1, d0)
    return (lo + hi) / 2.0


def tango_equivalence_rejects(n12, n21, n, margin, z_crit):
    """Two one-sided Tango score tests at +/- margin.

    Declares equivalence only when both one-sided nulls are rejected, which is
    the intersection-union form of the equivalence decision. A non-significant
    difference is never treated as equivalence.
    """
    lower_ok = tango_statistic(n12, n21, n, -margin) > z_crit
    upper_ok = tango_statistic(n12, n21, n, margin) < -z_crit
    return bool(lower_ok and upper_ok)


def _normal_quantile(p):
    """Inverse standard normal CDF (Acklam's rational approximation, refined)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low, p_high = 0.02425, 1.0 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    # one Halley refinement against the exact erfc-based CDF
    e = 0.5 * math.erfc(-x / math.sqrt(2.0)) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    return x - u / (1.0 + x * u / 2.0)


_REJECTION_CACHE = {}


def rejection_region(n, margin, z_crit):
    """Enumerate the exact rejection region of the paired equivalence decision.

    The decision depends only on (n12, n21, n), so the region can be enumerated
    once and reused for every alternative. Cached because the region is a pure
    function of its arguments.
    """
    key = (n, margin, round(z_crit, 12))
    cached = _REJECTION_CACHE.get(key)
    if cached is None:
        cached = [(a, b)
                  for a in range(n + 1)
                  for b in range(n - a + 1)
                  if tango_equivalence_rejects(a, b, n, margin, z_crit)]
        _REJECTION_CACHE[key] = cached
    return cached


def trinomial_rejection_probability(n, p12, p21, margin, z_crit):
    """Exact probability that the paired equivalence decision rejects.

    Sums the exact joint distribution of the two discordant counts over the
    enumerated rejection region. This is an exact computation, not a simulation
    and not a normal approximation of the outcome space.
    """
    p_rest = 1.0 - p12 - p21
    if p_rest < -1e-15:
        raise ValueError("p12 + p21 exceeds 1")
    p_rest = max(p_rest, 0.0)
    log_p12 = math.log(p12) if p12 > 0 else -math.inf
    log_p21 = math.log(p21) if p21 > 0 else -math.inf
    log_rest = math.log(p_rest) if p_rest > 0 else -math.inf
    log_fact = [0.0] * (n + 1)
    for i in range(1, n + 1):
        log_fact[i] = log_fact[i - 1] + math.log(i)
    terms = []
    for a, b in rejection_region(n, margin, z_crit):
        rest = n - a - b
        if (a and p12 == 0.0) or (b and p21 == 0.0) or (rest and p_rest == 0.0):
            continue
        lp = log_fact[n] - log_fact[a] - log_fact[b] - log_fact[rest]
        if a:
            lp += a * log_p12
        if b:
            lp += b * log_p21
        if rest:
            lp += rest * log_rest
        terms.append(math.exp(lp))
    return math.fsum(terms)


# --------------------------------------------------------------------------
# Verification of the declared paired method. Fail-closed.
# --------------------------------------------------------------------------

def verify_paired_method():
    """Verify Tango's statistic before it is used for any planning number."""
    results = {}

    # 1. Published property: Z(0) is exactly McNemar's statistic.
    worst = 0.0
    for n12, n21, n in [(12, 2, 59), (30, 10, 100), (5, 5, 40), (0, 7, 25),
                        (9, 0, 30), (44, 31, 192)]:
        z = tango_statistic(n12, n21, n, 0.0)
        mcnemar = (n12 - n21) / math.sqrt(n12 + n21)
        worst = max(worst, abs(z - mcnemar))
    if worst > 1e-9:
        raise AssertionError("Tango statistic does not reduce to McNemar at "
                             "delta0 = 0 (max deviation %r)" % worst)
    results["mcnemar_reduction_max_abs_deviation"] = worst

    # 2. Closed-form constrained MLE against direct numerical maximisation.
    worst_mle = 0.0
    for n11, n12, n21, n22 in [(40, 12, 2, 5), (100, 30, 10, 52),
                               (10, 5, 5, 20), (60, 9, 1, 30)]:
        n = n11 + n12 + n21 + n22
        for d0 in (-0.10, -0.05, 0.05, 0.10, 0.20):
            closed = tango_constrained_p21(n12, n21, n, d0)
            numeric = _numeric_constrained_p21(n11, n12, n21, n22, d0)
            worst_mle = max(worst_mle, abs(closed - numeric))
    if worst_mle > 1e-6:
        raise AssertionError("closed-form constrained MLE disagrees with direct "
                             "likelihood maximisation (max deviation %r)" % worst_mle)
    results["constrained_mle_max_abs_deviation"] = worst_mle

    # 3. Exact type-I error of the equivalence decision at the null boundary.
    #    The decision must not exceed its nominal one-sided level when the true
    #    difference sits exactly on the margin.
    z_crit = _normal_quantile(1.0 - 0.025)
    typei = []
    for n, margin, psi in [(96, 0.10, 0.20), (128, 0.10, 0.20), (192, 0.10, 0.30)]:
        p12 = (psi + margin) / 2.0
        p21 = (psi - margin) / 2.0
        rate = trinomial_rejection_probability(n, p12, p21, margin, z_crit)
        typei.append({"n": n, "margin": margin, "discordance": psi,
                      "exact_type_i": round(rate, 6)})
        if rate > 0.025 + 1e-9:
            raise AssertionError("paired equivalence decision exceeds its nominal "
                                 "one-sided level: %r" % rate)
    results["exact_type_i_at_boundary"] = typei
    results["normal_quantile_check"] = round(abs(_normal_quantile(0.975)
                                                 - 1.959963984540054), 12)
    if results["normal_quantile_check"] > 1e-9:
        raise AssertionError("normal quantile helper is not accurate enough")
    return results


# --------------------------------------------------------------------------
# Table construction
# --------------------------------------------------------------------------

def build_tables():
    verification = verify_paired_method()

    # ---- retained exact binomial gates (I1a, I1b, I2) --------------------
    retained = []
    for spec in [
        {"gate": "I1a", "construct": "trivial content recovery and output validity",
         "p0": 0.90, "n": 192, "alpha": STUDY_ALPHA, "alts": [0.97, 0.98, 0.99]},
        {"gate": "I1a", "construct": "trivial content recovery and output validity",
         "p0": 0.90, "n": 128, "alpha": STUDY_ALPHA, "alts": [0.97, 0.98, 0.99]},
        {"gate": "I1b", "construct": "explicit content-to-symbol binding",
         "p0": 0.90, "n": 192, "alpha": STUDY_ALPHA, "alts": [0.97, 0.98, 0.99]},
        {"gate": "I1b", "construct": "explicit content-to-symbol binding",
         "p0": 0.90, "n": 128, "alpha": STUDY_ALPHA, "alts": [0.97, 0.98, 0.99]},
        {"gate": "I2", "construct": "primitive headroom, per family",
         "p0": 0.50, "n": 192, "alpha": STUDY_ALPHA, "alts": [0.70, 0.75, 0.80]},
        {"gate": "I2", "construct": "primitive headroom, per family",
         "p0": 0.50, "n": 128, "alpha": STUDY_ALPHA, "alts": [0.70, 0.75, 0.80]},
    ]:
        n, p0, alpha = spec["n"], spec["p0"], spec["alpha"]
        x = exact_one_sided_threshold(n, p0, alpha)
        row = {
            "gate": spec["gate"], "construct": spec["construct"],
            "null_hypothesis": "p <= %g" % p0, "n": n, "alpha": alpha,
            "acceptance_count": x,
            "acceptance_rate": round(x / n, 10) if x is not None else None,
            "exact_null_tail": round(binom_upper_tail(x, n, p0), 12),
            "power": {str(a): round(binom_upper_tail(x, n, a), 6)
                      for a in spec["alts"]},
        }
        row["meets_target_power_0_90_at_lowest_alternative"] = bool(
            row["power"][str(spec["alts"][0])] >= TARGET_POWER)
        retained.append(row)

    # ---- rejected v0.1 chance-null I4 proposal ---------------------------
    x_rej = exact_one_sided_threshold(128, 0.25, 0.001)
    rejected_i4 = {
        "status": "REJECTED_BY_OPERATOR_REVIEW",
        "why": "a chance-level null does not establish a positive-capability "
               "floor; clearing 0.25 shows only that the reference is above "
               "guessing, which cannot license the inference that the interface "
               "is adequate for a capable model",
        "null_hypothesis": "p <= 0.25", "n": 128, "alpha": 0.001,
        "acceptance_count": x_rej,
        "acceptance_rate": round(x_rej / 128, 10),
        "exact_null_tail": round(binom_upper_tail(x_rej, 128, 0.25), 12),
    }

    # ---- replacement I4 competence floor --------------------------------
    i4_floor = 0.80
    i4_alpha_proposal = round(STUDY_ALPHA / SELECTABLE_SURFACE_COUNT, 12)
    i4 = []
    for n in (128, 192, 256, 384):
        for alpha in (STUDY_ALPHA, i4_alpha_proposal, 0.001):
            x = exact_one_sided_threshold(n, i4_floor, alpha)
            if x is None:
                i4.append({"n": n, "alpha": alpha, "acceptance_count": None,
                           "feasible": False})
                continue
            i4.append({
                "null_hypothesis": "p <= %g" % i4_floor, "n": n,
                "alpha": round(alpha, 12), "acceptance_count": x,
                "acceptance_rate": round(x / n, 10),
                "exact_null_tail": round(binom_upper_tail(x, n, i4_floor), 12),
                "power": {str(a): round(binom_upper_tail(x, n, a), 6)
                          for a in (0.90, 0.95, 0.97)},
                "feasible": True,
            })
    for row in i4:
        if row.get("feasible"):
            row["meets_target_power_0_90_at_0_95"] = bool(
                row["power"]["0.95"] >= TARGET_POWER)

    # ---- I3 primary: item-level content consistency floor ----------------
    consistency = []
    for p0 in (0.90, 0.95):
        for n in (128, 192, 256, 384):
            x = exact_one_sided_threshold(n, p0, STUDY_ALPHA)
            if x is None:
                consistency.append({"null_hypothesis": "p <= %g" % p0, "n": n,
                                    "alpha": STUDY_ALPHA,
                                    "acceptance_count": None, "feasible": False})
                continue
            consistency.append({
                "null_hypothesis": "p <= %g" % p0, "n": n, "alpha": STUDY_ALPHA,
                "acceptance_count": x, "acceptance_rate": round(x / n, 10),
                "exact_null_tail": round(binom_upper_tail(x, n, p0), 12),
                "power": {str(a): round(binom_upper_tail(x, n, a), 6)
                          for a in (0.97, 0.98, 0.99)},
                "feasible": True,
            })

    # ---- Clopper-Pearson lower bounds for descriptive per-cell reporting --
    cp = []
    for cells in (4, 8, 12, 24):
        alpha_cell = STUDY_ALPHA / cells
        for n, x in ((192, 184), (192, 176), (128, 120)):
            cp.append({"cells": cells, "n": n, "successes": x,
                       "simultaneous_alpha": round(alpha_cell, 12),
                       "clopper_pearson_lower": round(
                           clopper_pearson_lower(x, n, alpha_cell / 2.0), 6)})

    # ---- label-selection uniformity bands (label-bearing profiles only) ---
    uniformity = []
    for n in (192, 384, 768):
        band = central_acceptance_band(n, 0.25, STUDY_ALPHA / 4.0)
        uniformity.append({"n": n, "labels": 4, "expected_per_label": n / 4.0,
                           "bonferroni_alpha": round(STUDY_ALPHA / 4.0, 12),
                           "acceptance_band": band,
                           "applies_to": "label-bearing profiles only; NA for "
                                         "content-only profiles"})

    # ---- I3 secondary: paired equivalence sensitivity --------------------
    z_crit = _normal_quantile(1.0 - 0.025)
    paired = []
    for margin in (0.05, 0.10):
        for n in (128, 192, 256, 384):
            for psi in (0.05, 0.10, 0.20, 0.30):
                power = trinomial_rejection_probability(n, psi / 2.0, psi / 2.0,
                                                        margin, z_crit)
                p12_b = (psi + margin) / 2.0
                p21_b = (psi - margin) / 2.0
                typei = (trinomial_rejection_probability(n, p12_b, p21_b, margin,
                                                         z_crit)
                         if p21_b >= 0.0 else None)
                paired.append({
                    "method": "Tango 1998 score interval, two one-sided tests",
                    "margin": margin, "n": n, "discordance_rate": psi,
                    "true_difference": 0.0,
                    "one_sided_alpha": 0.025,
                    "exact_power": round(power, 6),
                    "exact_type_i_at_margin": (round(typei, 6)
                                               if typei is not None else None),
                    "meets_target_power": bool(power >= TARGET_POWER),
                })

    # ---- feasibility verdict for the v0.1 claim about n = 192 -------------
    n192_margin_05 = [r for r in paired if r["n"] == 192 and r["margin"] == 0.05]
    n192_margin_10 = [r for r in paired if r["n"] == 192 and r["margin"] == 0.10]
    verdict = {
        "claim_under_review": "v0.1 asserted an aggregate equivalence margin of "
                              "0.05 without any paired power analysis",
        "n": 192, "target_power": TARGET_POWER,
        "margin_0_05_supported_at_any_tested_discordance": bool(
            any(r["meets_target_power"] for r in n192_margin_05)),
        "margin_0_05_discordance_rates_supported": [
            r["discordance_rate"] for r in n192_margin_05 if r["meets_target_power"]],
        "margin_0_10_discordance_rates_supported": [
            r["discordance_rate"] for r in n192_margin_10 if r["meets_target_power"]],
        "conclusion": None,
    }
    if not verdict["margin_0_05_supported_at_any_tested_discordance"]:
        verdict["conclusion"] = (
            "n = 192 does NOT support the v0.1 aggregate equivalence margin of "
            "0.05 at 0.90 power under any tested discordance rate. The margin, "
            "the sample size, or both must be revised by the independent methods "
            "review. This is why OD5 and OD6 remain blocking.")
    else:
        verdict["conclusion"] = (
            "n = 192 supports the 0.05 margin only at the discordance rates "
            "listed, which must be justified before it may be relied upon.")

    # ---- hypothesis families and alpha allocation -------------------------
    families = {
        "principle": (
            "Two structurally different multiplicity problems are kept apart. "
            "Within one interface profile, every gate and every atomic cell must "
            "pass; that conjunction is an intersection-union test, whose size is "
            "bounded by the level of its individual components, so no inflation "
            "correction is applied to the conjunction itself. Across interface "
            "profiles, by contrast, the study may proceed if ANY selectable "
            "profile qualifies; that is a union event and it does inflate the "
            "false-qualification rate, so it is Bonferroni-corrected by the "
            "number of selectable profiles."),
        "family_A_within_profile": {
            "type": "intersection_union_conjunctive",
            "members": ["I1a", "I1b", "I2", "I3_primary", "I3_uniformity", "I4"],
            "per_component_alpha": STUDY_ALPHA,
            "correction": "none required; IU size is bounded by the component level",
            "note": "each atomic cell inside a gate is itself a conjunctive "
                    "member; a failed cell fails the gate and no pooled summary "
                    "may rescue it",
        },
        "family_B_across_profiles": {
            "type": "union_selection",
            "members": ["S1", "S2", "S3"],
            "excluded": ["S4 is never selectable and never enters selection"],
            "study_alpha": STUDY_ALPHA,
            "per_profile_alpha": i4_alpha_proposal,
            "correction": "Bonferroni over %d selectable profiles"
                          % SELECTABLE_SURFACE_COUNT,
        },
        "family_C_descriptive": {
            "type": "descriptive_only",
            "members": ["pooled summaries", "softmax confidences",
                        "per-cell Clopper-Pearson intervals"],
            "correction": "simultaneous Clopper-Pearson bounds are reported for "
                          "readability; they carry no gate authority",
        },
        "unresolved": ["the final alpha allocation is a v0.2 proposal and is "
                       "part of the blocking OD5 decision"],
    }

    return {
        "document_class": "design_statistics_derivation",
        "status": "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS_NOT_FROZEN",
        "draft_version": "draft-v0.2",
        "declared_assumptions": {
            "study_alpha": STUDY_ALPHA,
            "selectable_surface_count": SELECTABLE_SURFACE_COUNT,
            "target_power": TARGET_POWER,
            "i4_competence_floor": i4_floor,
        },
        "operation_counts": {
            "model_downloads": 0, "weight_loads": 0, "tokenizer_constructions": 0,
            "forward_passes": 0, "generations": 0, "gpu_jobs": 0,
            "provider_calls": 0, "bank_rows": 0, "seeds_drawn": 0,
            "evidence_rows": 0,
        },
        "paired_method_verification": verification,
        "retained_exact_binomial_gates": retained,
        "rejected_v0_1_i4_chance_null": rejected_i4,
        "i4_competence_floor_thresholds": i4,
        "i3_primary_item_level_consistency": consistency,
        "i3_secondary_paired_equivalence_sensitivity": paired,
        "i3_feasibility_verdict": verdict,
        "descriptive_clopper_pearson_lower_bounds": cp,
        "label_selection_uniformity_bands": uniformity,
        "hypothesis_families_and_alpha_allocation": families,
    }


# --------------------------------------------------------------------------

def _tables_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "design_statistics_tables.json")


def _serialise(tables):
    return json.dumps(tables, indent=2, sort_keys=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--emit", action="store_true",
                       help="regenerate the committed tables")
    group.add_argument("--check", action="store_true",
                       help="verify the committed tables reproduce exactly")
    args = parser.parse_args(argv)

    tables = build_tables()
    text = _serialise(tables)
    path = _tables_path()

    if args.emit:
        with open(path, "wb") as handle:
            handle.write(text.encode("utf-8"))
        print("wrote %s (%d bytes)" % (path, len(text.encode("utf-8"))))
        return 0

    if not os.path.exists(path):
        print("FAIL committed tables are missing: %s" % path)
        return 1
    with open(path, "rb") as handle:
        committed = handle.read().decode("utf-8")
    if committed != text:
        print("FAIL recomputed tables differ from the committed tables")
        expected = json.loads(committed)
        for key in sorted(set(expected) | set(tables)):
            if expected.get(key) != tables.get(key):
                print("  differing section: %s" % key)
        return 1
    print("DESIGN_STATISTICS_CHECK_OK sections=%d" % len(tables))
    return 0


if __name__ == "__main__":
    sys.exit(main())
