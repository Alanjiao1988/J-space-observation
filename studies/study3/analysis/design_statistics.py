"""Study 3 draft-v0.3 design-statistics derivation instrument (model-free).

This script belongs to the Study 3 *design* packet. It performs no model
operation of any kind: no download, no revision resolution by download, no
weight load, no tokenizer construction, no tokenization, no forward pass, no
sequence scoring, no generation, no activation extraction, no probe, no patch,
no ablation, no lens operation, no GPU work and no provider call. It draws no
seed, writes no task-bank row, reads no confirmation content, and produces no
scientific evidence row.

Everything it emits is a *design parameter* computed by exact model-free
arithmetic from declared assumptions. Nothing here is a measurement and nothing
here is frozen. draft-v0.3 is an amended, still-unfrozen draft awaiting a second
independent methods review.

What changed from draft-v0.2, and why
-------------------------------------
The independent methods review of draft-v0.2 returned
``STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`` with six blocking
findings. The operator amendment adopted here:

* replaces the undefined "all transformations" I3 cluster with pre-registered
  **pairwise base-item contrast clusters** holding exactly two variants each
  (S3MR-001, S3MR-014);
* publishes three I3 indicators ``J_inv``, ``J_cor`` and ``J_both``, with
  ``J_both`` as the primary gate indicator, so a stable-but-wrong answer and a
  stable-but-invalid output both score zero (S3MR-002);
* implements the per-profile development component alpha as the **exact
  rational** ``1/600`` in every component, not as a decimal that is stated in
  one place and unimplemented everywhere else (S3MR-003);
* **retires the Tango paired aggregate-equivalence procedure from every
  decision role**. The false conservativeness assertion is withdrawn, the
  four-point discordance grid is removed from active verification, and no
  critical value, equivalence margin or discordance grid carries gate,
  eligibility, selection, confirmation or claim authority (S3MR-004,
  S3MR-005, S3MR-009). Paired 2x2 summaries survive as *descriptive only*:
  they have no null, no alpha, no p-value, no pass/fail, no rescue path and no
  ranking weight;
* registers exactly **one** active I3 floor ``p0 = 0.90`` with
  ``p1 = 0.97`` and ``n = 256`` contrast clusters per contrast cell; the
  ``p0 = 0.95`` variant is deleted from every active table (S3MR-006,
  S3MR-007, S3MR-015);
* raises I1a/I1b to ``n = 256`` base items per atomic cell so the reviewed
  target power is met at the implemented alpha (S3MR-008);
* fixes the Family B selectable-profile denominator at **3** before any data
  (S3MR-016) and publishes an executable pre-data development selection map
  and a complete I5 confirmation specification (S3MR-017);
* decomposes the operation projection into six named work streams with
  per-stream units, and fixes the current-domain S3 incremental cost at zero
  (S3MR-012, S3MR-013).

Derivation, not transcription
-----------------------------
Every threshold, exact null tail, power figure and expected pass count below is
**derived here** by exact binomial search over exact rational arithmetic. The
reviewer-returned planning targets are deliberately absent from this module as
literals: ``tests/test_study3_design.py`` holds them as an independent
expectation and asserts that this module's derivation reproduces them, and it
also asserts by AST inspection that none of those counts appears as an integer
constant in this file. Copying a constant instead of deriving it is a test
failure by construction.

Usage
-----
    python studies/study3/analysis/design_statistics.py --emit
    python studies/study3/analysis/design_statistics.py --check

``--emit`` regenerates ``design_statistics_tables.json`` beside this file.
``--check`` recomputes every table and compares it value-for-value against the
committed JSON, exiting non-zero on any difference. ``--check`` is the mode the
committed tests and the CPU-only Azure validation use.

The script is fail-closed: every structural invariant it claims is asserted
here, and a violated invariant raises before any table is emitted.

Standard library only, by design: the validation image installs
``requirements.lock.txt``, which carries no statistics or schema dependency.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from fractions import Fraction

# --------------------------------------------------------------------------
# 1. Declared design assumptions
#
# These are operator proposals for draft-v0.3. They are not frozen and they are
# not measurements. Decimal renderings appear in the emitted tables for
# readability; the exact rational value is the policy, and the rational form is
# emitted alongside every decimal so the two can never drift apart.
# --------------------------------------------------------------------------

# Family B: the study-level development screening level, and the fixed
# selectable-profile denominator. The denominator is fixed *before data* and
# never shrinks, including when S3's activation condition is not met.
STUDY_DEVELOPMENT_SCREENING_ALPHA = Fraction(1, 200)
SELECTABLE_PROFILE_DENOMINATOR = 3

# Family A: every exact-binomial component inside one profile is tested at this
# level. Within a profile the components form an intersection-union
# conjunction, so no further within-profile Bonferroni correction is applied.
DEVELOPMENT_COMPONENT_ALPHA = (STUDY_DEVELOPMENT_SCREENING_ALPHA
                               / SELECTABLE_PROFILE_DENOMINATOR)

# Confirmation is a separate error role on a physically disjoint one-shot
# split, entered by exactly one pre-selected profile, so it carries no
# across-profile correction.
CONFIRMATION_COMPONENT_ALPHA = Fraction(1, 200)

TARGET_POWER = Fraction(9, 10)

# Registered structural constants of the design.
LABEL_ALPHABETS = (("A", "B", "C", "D"), ("W", "X", "Y", "Z"))
ANSWER_DOMAIN_SURFACE_FORMS = tuple(str(d) for d in range(10))
OPTION_SLOTS = 4
VARIANTS_PER_CONTRAST_CLUSTER = 2

PRIMITIVE_OPERATION_FAMILIES = ("affine_mod10", "permutation_chain")
COMPOSITION_DEPTHS = (2, 3)
TARGET_MODEL_ROLES = ("RT", "RL", "RI")
POSITIVE_REFERENCE_ROLE = "RP"

# S4 is a never-selectable diagnostic. Its generated-token ceiling is a
# registered planning bound, not an authorization to generate anything.
S4_GENERATED_TOKEN_UPPER_BOUND_PER_ROW = 16

RATIONAL_TOLERANCE = 0

# Rendering precision. Tails are rendered to 12 decimal places and powers to 9,
# which is the precision at which the independent review reported its own
# recalculation, so the two can be compared without a tolerance argument.
TAIL_DIGITS = 12
POWER_DIGITS = 9


# --------------------------------------------------------------------------
# 2. Exact binomial machinery over exact rationals
#
# Everything below is exact: the pmf, both tails and the threshold search are
# computed in Fraction arithmetic, so the emitted decimal is a *rendering* of an
# exact value rather than the accumulation of floating-point error.
# --------------------------------------------------------------------------

def binom_pmf(k: int, n: int, p: Fraction) -> Fraction:
    """Exact binomial pmf P[X = k] for X ~ Binomial(n, p)."""
    if k < 0 or k > n:
        return Fraction(0)
    if p == 0:
        return Fraction(1) if k == 0 else Fraction(0)
    if p == 1:
        return Fraction(1) if k == n else Fraction(0)
    return Fraction(math.comb(n, k)) * p ** k * (1 - p) ** (n - k)


def binom_upper_tail(x: int, n: int, p: Fraction) -> Fraction:
    """Exact P[X >= x] for X ~ Binomial(n, p)."""
    if x <= 0:
        return Fraction(1)
    if x > n:
        return Fraction(0)
    return sum((binom_pmf(k, n, p) for k in range(x, n + 1)), Fraction(0))


def binom_lower_tail(x: int, n: int, p: Fraction) -> Fraction:
    """Exact P[X <= x] for X ~ Binomial(n, p)."""
    if x < 0:
        return Fraction(0)
    if x >= n:
        return Fraction(1)
    return sum((binom_pmf(k, n, p) for k in range(0, x + 1)), Fraction(0))


def exact_one_sided_threshold(n: int, p0: Fraction, alpha: Fraction):
    """Smallest x with P[X >= x | p0] <= alpha, or None if none exists.

    The comparison is exact rational, so a tail that merely rounds to alpha in
    floating point is not accepted as meeting alpha.
    """
    for x in range(0, n + 1):
        if binom_upper_tail(x, n, p0) <= alpha + RATIONAL_TOLERANCE:
            return x
    return None


def clopper_pearson_lower(x: int, n: int, tail_mass: Fraction) -> float:
    """Descriptive Clopper-Pearson lower bound by exact tail inversion.

    ``tail_mass`` is the probability placed in the *lower* tail of the interval.
    This bound is descriptive only: finding S3MR-019 recorded that draft-v0.2
    filed a two-sided convention under a field named one-sided, so the caller
    must name its convention explicitly and this function names its argument
    after the mass it actually consumes.
    """
    if x <= 0:
        return 0.0
    lo, hi = Fraction(0), Fraction(1)
    for _ in range(200):
        mid = (lo + hi) / 2
        if binom_upper_tail(x, n, mid) < tail_mass:
            lo = mid
        else:
            hi = mid
    return _render(float((lo + hi) / 2), 6)


def central_acceptance_band(n: int, p: Fraction, total_two_sided_mass: Fraction):
    """Exact central band [lo, hi], each tail holding at most half the mass.

    Diagnostic only in draft-v0.3. The band carries no gate, eligibility,
    selection or confirmation authority.
    """
    half = total_two_sided_mass / 2
    lo = 0
    while lo <= n and binom_lower_tail(lo, n, p) < half:
        lo += 1
    hi = n
    while hi >= 0 and binom_upper_tail(hi, n, p) < half:
        hi -= 1
    return [lo, hi]


def _render(value: float, digits: int) -> float:
    return round(value, digits)


def _rational(value: Fraction) -> str:
    return "%d/%d" % (value.numerator, value.denominator)


# --------------------------------------------------------------------------
# 3. Gate registry
#
# Every sample size carries the unit it is measured in, at the point of
# definition. Finding S3MR-014 recorded that draft-v0.2 changed the meaning of
# ``n`` between artifacts without declaring it anywhere, so ``unit_of_n`` is
# mandatory here and is propagated into every emitted row.
# --------------------------------------------------------------------------

GATE_SPECS = (
    {
        "gate": "I1a",
        "construct": "trivial content recovery and output validity",
        "unit_of_n": "base items per atomic cell",
        "independent_unit": "base_item",
        "n": 256,
        "p0": Fraction(9, 10),
        "p1": Fraction(97, 100),
        "source_stratum": "K2",
        "applicable_profiles": ("S1", "S2", "S3", "S4"),
        "evaluated_per": ("interface profile", "checkpoint role", "split"),
    },
    {
        "gate": "I1b",
        "construct": "explicit content-to-symbol binding",
        "unit_of_n": "base items per atomic cell",
        "independent_unit": "base_item",
        "n": 256,
        "p0": Fraction(9, 10),
        "p1": Fraction(97, 100),
        "source_stratum": "K1",
        "applicable_profiles": ("S1", "S4"),
        "evaluated_per": ("interface profile", "checkpoint role",
                          "label alphabet balancing block", "split"),
    },
    {
        "gate": "I2",
        "construct": "primitive headroom, evaluated separately per family",
        "unit_of_n": "base items per primitive-family cell",
        "independent_unit": "base_item",
        "n": 128,
        "p0": Fraction(1, 2),
        "p1": Fraction(7, 10),
        "source_stratum": "K3",
        "applicable_profiles": ("S1", "S2", "S3", "S4"),
        "evaluated_per": ("interface profile", "checkpoint role",
                          "primitive operation family", "split"),
    },
    {
        "gate": "I3",
        "construct": "pairwise presentation invariance and correctness, J_both",
        "unit_of_n": "base-item contrast clusters per contrast cell",
        "independent_unit": "base_item_contrast_cluster",
        "n": 256,
        "p0": Fraction(9, 10),
        "p1": Fraction(97, 100),
        "source_stratum": "K5 and K6",
        "applicable_profiles": ("S1", "S2", "S3", "S4"),
        "evaluated_per": ("interface profile", "checkpoint role",
                          "contrast family", "contrast ID", "split"),
    },
    {
        "gate": "I4",
        "construct": "positive-reference competence recovery through the profile",
        "unit_of_n": ("RP base items per operation-family x depth cell "
                      "per candidate profile"),
        "independent_unit": "base_item",
        "n": 256,
        "p0": Fraction(4, 5),
        "p1": Fraction(9, 10),
        "source_stratum": "K4",
        "applicable_profiles": ("S1", "S2", "S3", "S4"),
        "evaluated_per": ("interface profile", "registered operation family",
                          "depth"),
    },
)


def _binomial_row(spec, alpha: Fraction, split: str):
    """Derive one exact-binomial decision row. Nothing here is transcribed."""
    n, p0, p1 = spec["n"], spec["p0"], spec["p1"]
    x = exact_one_sided_threshold(n, p0, alpha)
    if x is None:
        raise AssertionError(
            "no admissible rejection count exists for %s at n=%d, p0=%s, "
            "alpha=%s" % (spec["gate"], n, p0, _rational(alpha)))
    if x >= n:
        # S3MR-015: a rejection region requiring every single unit to succeed
        # is degenerate. It is excluded by construction, not by inspection.
        raise AssertionError(
            "degenerate rejection region for %s: pass count %d equals n %d"
            % (spec["gate"], x, n))
    tail = binom_upper_tail(x, n, p0)
    power = binom_upper_tail(x, n, p1)
    return {
        "gate": spec["gate"],
        "construct": spec["construct"],
        "split": split,
        "unit_of_n": spec["unit_of_n"],
        "independent_unit": spec["independent_unit"],
        "source_stratum": spec["source_stratum"],
        "applicable_profiles": list(spec["applicable_profiles"]),
        "evaluated_per": list(spec["evaluated_per"]),
        "n": n,
        "null_hypothesis": "p <= %s" % _render(float(p0), 4),
        "p0": _render(float(p0), 4),
        "p0_exact_rational": _rational(p0),
        "p1_lowest_alternative_of_interest": _render(float(p1), 4),
        "p1_exact_rational": _rational(p1),
        "alpha": _render(float(alpha), TAIL_DIGITS),
        "alpha_exact_rational": _rational(alpha),
        "pass_count": x,
        "pass_rate": _render(x / n, 10),
        "rejection_rule": ("pass the component when the observed success count "
                           "is at least %d out of %d %s"
                           % (x, n, spec["unit_of_n"])),
        "exact_null_tail_at_p0": _render(float(tail), TAIL_DIGITS),
        "exact_power_at_p1": _render(float(power), POWER_DIGITS),
        "meets_target_power": bool(power >= TARGET_POWER),
        "degenerate_rejection_region": bool(x >= n),
        "derivation": ("exact binomial search over exact rational arithmetic; "
                       "no threshold, tail or power value in this row is a "
                       "transcribed constant"),
    }


# --------------------------------------------------------------------------
# 4. I3 pairwise contrast construction (K5 and K6)
#
# The independent sampling unit is a base_item_contrast_cluster holding exactly
# two variants: the registered baseline for that contrast cell, and one
# registered content-equivalent transformed presentation. There is no
# cross-product: K5 and K6 are not crossed, base-item identities are disjoint
# across contrast cells, and no base item appears in more than one cell.
#
# No random draw occurs anywhere in this construction.
# --------------------------------------------------------------------------

K5_CONTRASTS = (
    {"id": "K5-P1", "factor": "content_position", "offset": 1},
    {"id": "K5-P2", "factor": "content_position", "offset": 2},
    {"id": "K5-P3", "factor": "content_position", "offset": 3},
    {"id": "K5-S1", "factor": "correct_symbol_index", "offset": 1},
    {"id": "K5-S2", "factor": "correct_symbol_index", "offset": 2},
    {"id": "K5-S3", "factor": "correct_symbol_index", "offset": 3},
    {"id": "K5-A1", "factor": "label_alphabet", "offset": None},
)

K6_CONTRASTS = (
    {"id": "K6-SEP", "baseline": "R-base", "variant": "R-sep",
     "varies": "the option separator only"},
    {"id": "K6-INSTR", "baseline": "R-base", "variant": "R-instr",
     "varies": "the instruction sentence only"},
)

# One complete balancing block covers every (position, symbol index, alphabet)
# combination exactly once.
COMPLETE_BLOCK_SIZE = OPTION_SLOTS * OPTION_SLOTS * len(LABEL_ALPHABETS)


def baseline_condition(index: int):
    """Deterministic baseline condition for base-item index ``index``.

    Returns (position of the correct content, index of the correct displayed
    symbol, label-alphabet index). Cycling the three factors at different rates
    balances all of them over each complete block of 32 base items, with no
    seed and no random draw.
    """
    position = index % OPTION_SLOTS
    symbol = (index // OPTION_SLOTS) % OPTION_SLOTS
    alphabet = (index // (OPTION_SLOTS * OPTION_SLOTS)) % len(LABEL_ALPHABETS)
    return position, symbol, alphabet


def symbol_permutation(position: int, symbol: int):
    """Bijective position -> symbol-index map sending ``position`` to ``symbol``.

    A rotation is a bijection on the four slots, so every displayed symbol is
    used exactly once and the option list is never degenerate.
    """
    shift = (symbol - position) % OPTION_SLOTS
    return tuple((slot + shift) % OPTION_SLOTS for slot in range(OPTION_SLOTS))


def content_placement(position: int):
    """Bijective slot -> content-role map placing the correct content.

    Slot ``position`` holds the correct content; the three registered
    distractors fill the remaining slots in ascending slot order, which is a
    fixed function of the condition and uses no random draw.
    """
    placement = [None] * OPTION_SLOTS
    placement[position] = "correct"
    remaining = [slot for slot in range(OPTION_SLOTS) if slot != position]
    for rank, slot in enumerate(remaining):
        placement[slot] = "distractor_%d" % rank
    return tuple(placement)


def render_variant(index: int, position: int, symbol: int, alphabet: int,
                   rendering: str):
    """Emit one variant as a fully determined, verifiable record."""
    alphabet_symbols = LABEL_ALPHABETS[alphabet]
    permutation = symbol_permutation(position, symbol)
    placement = content_placement(position)
    options = [
        {
            "slot": slot,
            "label": alphabet_symbols[permutation[slot]],
            "content_role": placement[slot],
        }
        for slot in range(OPTION_SLOTS)
    ]
    return {
        "base_item_index": index,
        "content_position": position,
        "correct_symbol_index": symbol,
        "label_alphabet_index": alphabet,
        "rendering": rendering,
        "options": options,
        "ground_truth_label": alphabet_symbols[symbol],
        "ground_truth_content_role": "correct",
    }


def k5_cluster(contrast, index: int):
    """Build one K5 base-item contrast cluster: exactly two variants."""
    position, symbol, alphabet = baseline_condition(index)
    if contrast["factor"] == "content_position":
        moved = ((position + contrast["offset"]) % OPTION_SLOTS, symbol,
                 alphabet)
    elif contrast["factor"] == "correct_symbol_index":
        moved = (position, (symbol + contrast["offset"]) % OPTION_SLOTS,
                 alphabet)
    elif contrast["factor"] == "label_alphabet":
        moved = (position, symbol, (alphabet + 1) % len(LABEL_ALPHABETS))
    else:
        raise AssertionError("unregistered K5 factor %r" % contrast["factor"])
    return {
        "contrast_family": "K5",
        "contrast_id": contrast["id"],
        "varied_factor": contrast["factor"],
        "base_item_identity": "%s#%d" % (contrast["id"], index),
        "variants": [
            render_variant(index, position, symbol, alphabet, "R-base"),
            render_variant(index, moved[0], moved[1], moved[2], "R-base"),
        ],
    }


def k6_cluster(contrast, index: int, label_bearing: bool):
    """Build one K6 base-item contrast cluster: exactly two variants."""
    if label_bearing:
        position, symbol, alphabet = baseline_condition(index)
    else:
        position, symbol, alphabet = 0, 0, 0
    return {
        "contrast_family": "K6",
        "contrast_id": contrast["id"],
        "varied_factor": contrast["varies"],
        "base_item_identity": "%s#%d" % (contrast["id"], index),
        "answer_cue": "byte-identical across both variants",
        "variants": [
            render_variant(index, position, symbol, alphabet,
                           contrast["baseline"]),
            render_variant(index, position, symbol, alphabet,
                           contrast["variant"]),
        ],
    }


def verify_pairwise_construction():
    """Fail-closed structural verification of the I3 pairwise construction."""
    report = {}

    # 4.1 No label alphabet may collide with the answer domain, and the two
    # alphabets must be disjoint so replacing one is a real manipulation.
    answer_domain = set(ANSWER_DOMAIN_SURFACE_FORMS)
    for alphabet in LABEL_ALPHABETS:
        if set(alphabet) & answer_domain:
            raise AssertionError("label alphabet collides with the answer "
                                 "domain: %r" % (alphabet,))
        if any(symbol.isdigit() for symbol in alphabet):
            raise AssertionError("digits are forbidden as label symbols: %r"
                                 % (alphabet,))
    if set(LABEL_ALPHABETS[0]) & set(LABEL_ALPHABETS[1]):
        raise AssertionError("the two label alphabets are not disjoint")
    report["label_alphabets_disjoint_from_answer_domain"] = True
    report["label_alphabets_mutually_disjoint"] = True

    # 4.2 Every K5 cluster has exactly two variants, every option list is a
    # bijection on labels and on contents, the ground truth is preserved, and
    # each contrast varies exactly one registered factor.
    block = COMPLETE_BLOCK_SIZE
    factor_counts = {}
    for contrast in K5_CONTRASTS:
        seen_conditions = {}
        for index in range(block):
            cluster = k5_cluster(contrast, index)
            if len(cluster["variants"]) != VARIANTS_PER_CONTRAST_CLUSTER:
                raise AssertionError("%s cluster does not hold exactly two "
                                     "variants" % contrast["id"])
            base, moved = cluster["variants"]
            for variant in (base, moved):
                labels = [option["label"] for option in variant["options"]]
                roles = [option["content_role"] for option in variant["options"]]
                if len(set(labels)) != OPTION_SLOTS:
                    raise AssertionError("label mapping is not a bijection in "
                                         "%s" % contrast["id"])
                if len(set(roles)) != OPTION_SLOTS:
                    raise AssertionError("content mapping is not a bijection "
                                         "in %s" % contrast["id"])
                correct_slot = [option["slot"] for option in variant["options"]
                                if option["content_role"] == "correct"]
                if len(correct_slot) != 1:
                    raise AssertionError("the correct content is not unique in "
                                         "%s" % contrast["id"])
                if correct_slot[0] != variant["content_position"]:
                    raise AssertionError("the correct content is not at its "
                                         "declared position in %s"
                                         % contrast["id"])
                displayed = [option["label"] for option in variant["options"]
                             if option["slot"] == variant["content_position"]]
                if displayed[0] != variant["ground_truth_label"]:
                    raise AssertionError("ground truth is not preserved in %s"
                                         % contrast["id"])
            changed = set()
            for key in ("content_position", "correct_symbol_index",
                        "label_alphabet_index"):
                if base[key] != moved[key]:
                    changed.add(key)
            if len(changed) != 1:
                raise AssertionError(
                    "%s changes %d factors; K5 contrasts are one-factor"
                    % (contrast["id"], len(changed)))
            factor_counts.setdefault(contrast["id"], set()).update(changed)
            key = (base["content_position"], base["correct_symbol_index"],
                   base["label_alphabet_index"])
            seen_conditions[key] = seen_conditions.get(key, 0) + 1
        if len(seen_conditions) != block or set(seen_conditions.values()) != {1}:
            raise AssertionError("%s baseline conditions are not balanced over "
                                 "a complete block" % contrast["id"])
    report["k5_contrast_count"] = len(K5_CONTRASTS)
    report["k5_one_factor_per_contrast"] = all(
        len(values) == 1 for values in factor_counts.values())
    report["k5_complete_block_size"] = block
    report["k5_baseline_conditions_balanced_over_a_complete_block"] = True

    # 4.3 K6 is two disjoint pairwise cells drawn from three renderings, with
    # the answer cue and every other byte held fixed within each pair.
    for contrast in K6_CONTRASTS:
        for label_bearing in (True, False):
            cluster = k6_cluster(contrast, 0, label_bearing)
            if len(cluster["variants"]) != VARIANTS_PER_CONTRAST_CLUSTER:
                raise AssertionError("%s cluster does not hold exactly two "
                                     "variants" % contrast["id"])
            base, moved = cluster["variants"]
            for key in ("content_position", "correct_symbol_index",
                        "label_alphabet_index", "ground_truth_label"):
                if base[key] != moved[key]:
                    raise AssertionError(
                        "%s varies %s; only the registered rendering factor may "
                        "change" % (contrast["id"], key))
            if base["rendering"] == moved["rendering"]:
                raise AssertionError("%s does not vary its rendering"
                                     % contrast["id"])
    renderings = {contrast["baseline"] for contrast in K6_CONTRASTS}
    renderings |= {contrast["variant"] for contrast in K6_CONTRASTS}
    report["k6_contrast_count"] = len(K6_CONTRASTS)
    report["k6_rendering_set"] = sorted(renderings)
    report["k6_answer_cue_fixed_within_every_pair"] = True

    # 4.4 K5 and K6 are not crossed and share no base-item identity.
    k5_identities = {k5_cluster(contrast, index)["base_item_identity"]
                     for contrast in K5_CONTRASTS for index in range(block)}
    k6_identities = {k6_cluster(contrast, index, True)["base_item_identity"]
                     for contrast in K6_CONTRASTS for index in range(block)}
    if k5_identities & k6_identities:
        raise AssertionError("K5 and K6 share a base-item identity")
    if len(k5_identities) != len(K5_CONTRASTS) * block:
        raise AssertionError("K5 base-item identities are not unique per cell")
    if len(k6_identities) != len(K6_CONTRASTS) * block:
        raise AssertionError("K6 base-item identities are not unique per cell")
    report["k5_k6_base_item_identities_disjoint"] = True
    report["k5_x_k6_cross_product_exists"] = False
    report["variants_per_base_item_contrast_cluster"] = (
        VARIANTS_PER_CONTRAST_CLUSTER)
    return report


# --------------------------------------------------------------------------
# 5. I3 indicators
#
# J_inv  = 1 iff both variants produce valid answer-domain content and the two
#          mapped contents are byte-identical after the registered content
#          mapping. Stable invalid or unparseable output scores 0.
# J_cor  = 1 iff both variants are scored correct against the unique registered
#          ground truth. A stable but wrong answer scores 0.
# J_both = J_inv AND J_cor, and is the primary I3 gate indicator.
#
# Under a unique ground truth J_cor implies J_inv. That implication is recorded
# below as an expected integrity invariant rather than treated as evidence that
# the two indicators are independent. The explicit conjunction is retained so
# the stable-wrong and stable-invalid semantics fail closed.
# --------------------------------------------------------------------------

def indicator_j_inv(first, second) -> int:
    if first is None or second is None:
        return 0
    if first not in ANSWER_DOMAIN_SURFACE_FORMS:
        return 0
    if second not in ANSWER_DOMAIN_SURFACE_FORMS:
        return 0
    return 1 if first == second else 0


def indicator_j_cor(first, second, truth) -> int:
    return 1 if (first == truth and second == truth) else 0


def indicator_j_both(first, second, truth) -> int:
    return indicator_j_inv(first, second) & indicator_j_cor(first, second, truth)


def build_indicator_truth_table():
    """Enumerate the registered outcome cases and assert the invariants."""
    truth = "7"
    cases = (
        ("both_correct", "7", "7"),
        ("stable_but_wrong", "3", "3"),
        ("one_correct_one_wrong", "7", "3"),
        ("one_wrong_one_correct", "3", "7"),
        ("both_wrong_and_different", "3", "5"),
        ("stable_but_invalid", None, None),
        ("one_valid_one_invalid", "7", None),
        ("one_invalid_one_valid", None, "7"),
    )
    rows = []
    for name, first, second in cases:
        j_inv = indicator_j_inv(first, second)
        j_cor = indicator_j_cor(first, second, truth)
        j_both = indicator_j_both(first, second, truth)
        if j_cor == 1 and j_inv != 1:
            raise AssertionError("integrity invariant violated: J_cor without "
                                 "J_inv in case %s" % name)
        if j_both != (j_inv & j_cor):
            raise AssertionError("J_both is not the conjunction in case %s"
                                 % name)
        rows.append({
            "case": name,
            "variant_1_mapped_content": first,
            "variant_2_mapped_content": second,
            "registered_ground_truth": truth,
            "J_inv": j_inv,
            "J_cor": j_cor,
            "J_both": j_both,
            "scores_for_the_gate": bool(j_both == 1),
        })
    if any(row["J_both"] for row in rows if row["case"] == "stable_but_wrong"):
        raise AssertionError("a stable but wrong answer must score 0")
    if any(row["J_both"] for row in rows if row["case"] == "stable_but_invalid"):
        raise AssertionError("a stable but invalid output must score 0")
    return rows


# --------------------------------------------------------------------------
# 6. Development selection map
#
# Executable and fully determined before any data exists. Development data may
# not alter the order, the applicability definitions, the denominator, the
# thresholds or the confirmation plan.
# --------------------------------------------------------------------------

SELECTION_ORDER = ("S2", "S3", "S1")
NEVER_SELECTABLE = ("S4",)


def development_selection(component_pass, s3_multi_token_domain_activated):
    """Return the pre-registered selection outcome for one pass/fail vector.

    ``component_pass`` maps a selectable profile id to True only when *every*
    applicable development component passed for that profile. The denominator
    is fixed at 3 and does not depend on this argument in any way.
    """
    denominator = SELECTABLE_PROFILE_DENOMINATOR
    eligible = []
    for profile in SELECTION_ORDER:
        if not component_pass.get(profile, False):
            continue
        if profile == "S3" and not s3_multi_token_domain_activated:
            # S3 remains inside the fixed denominator under every outcome; its
            # activation condition is a pre-data applicability condition, not a
            # gate outcome, so failing it skips the profile without shrinking
            # the denominator.
            continue
        eligible.append(profile)
    selected = eligible[0] if eligible else None
    return {
        "fixed_selectable_profile_denominator": denominator,
        "eligible_profiles": eligible,
        "selected_profile": selected,
        "selection_order": list(SELECTION_ORDER),
        "never_selectable": list(NEVER_SELECTABLE),
        "stop": selected is None,
    }


def build_selection_map():
    """Enumerate every pre-data selection scenario, so the map is executable."""
    rows = []
    for activated in (False, True):
        for bits in range(1 << len(SELECTION_ORDER)):
            vector = {profile: bool(bits >> position & 1)
                      for position, profile in enumerate(("S1", "S2", "S3"))}
            outcome = development_selection(vector, activated)
            if outcome["fixed_selectable_profile_denominator"] != (
                    SELECTABLE_PROFILE_DENOMINATOR):
                raise AssertionError("the Family B denominator moved")
            if outcome["selected_profile"] in NEVER_SELECTABLE:
                raise AssertionError("a never-selectable profile was selected")
            if not activated and outcome["selected_profile"] == "S3":
                raise AssertionError("S3 was selected without its activation "
                                     "condition")
            rows.append({
                "s3_multi_token_domain_activated": activated,
                "all_applicable_components_passed": dict(sorted(vector.items())),
                "eligible_profiles": outcome["eligible_profiles"],
                "selected_profile": outcome["selected_profile"],
                "stop_no_selectable_profile_is_eligible": outcome["stop"],
                "fixed_selectable_profile_denominator": (
                    outcome["fixed_selectable_profile_denominator"]),
            })
    if len(rows) != 2 * (1 << len(SELECTION_ORDER)):
        raise AssertionError("the selection map is not exhaustive")
    return rows


# --------------------------------------------------------------------------
# 7. Work-stream operation projection
#
# A single undifferentiated total is prohibited. Every stream reports its own
# base items, contrast clusters, variants per cluster, rendered rows, scored
# rows, model roles and forward-pass accounting, and every dimensional identity
# is asserted rather than asserted-by-narrative.
# --------------------------------------------------------------------------

def _gate_n(gate_id: str) -> int:
    for spec in GATE_SPECS:
        if spec["gate"] == gate_id:
            return spec["n"]
    raise AssertionError("unregistered gate %r" % gate_id)


def _profile_component_cells(profile: str):
    """Registered development cell structure for one interface profile.

    Returns a list of component records. Each record is explicit about its
    independent-unit type, its unit count and its variants per unit, so a
    rendered-row count can never be mistaken for an ``n``.
    """
    label_bearing = profile in ("S1", "S4")
    components = [
        {
            "component": "I1a",
            "independent_unit_type": "base_item",
            "independent_unit_count": _gate_n("I1a"),
            "cells": 1,
            "variants_per_independent_unit": 1,
        },
        {
            "component": "I2",
            "independent_unit_type": "base_item",
            "independent_unit_count": _gate_n("I2"),
            "cells": len(PRIMITIVE_OPERATION_FAMILIES),
            "variants_per_independent_unit": 1,
        },
        {
            "component": "I3_K6",
            "independent_unit_type": "base_item_contrast_cluster",
            "independent_unit_count": _gate_n("I3"),
            "cells": len(K6_CONTRASTS),
            "variants_per_independent_unit": VARIANTS_PER_CONTRAST_CLUSTER,
        },
    ]
    if label_bearing:
        components.append({
            "component": "I1b",
            "independent_unit_type": "base_item",
            "independent_unit_count": _gate_n("I1b"),
            "cells": 1,
            "variants_per_independent_unit": 1,
        })
        components.append({
            "component": "I3_K5",
            "independent_unit_type": "base_item_contrast_cluster",
            "independent_unit_count": _gate_n("I3"),
            "cells": len(K5_CONTRASTS),
            "variants_per_independent_unit": VARIANTS_PER_CONTRAST_CLUSTER,
        })
    else:
        components.append({
            "component": "I1b",
            "independent_unit_type": "not_applicable",
            "independent_unit_count": 0,
            "cells": 0,
            "variants_per_independent_unit": 0,
            "not_applicable_reason": ("this profile displays no label alphabet, "
                                      "so there is no symbol-binding step; "
                                      "not_applicable is not a pass"),
        })
        components.append({
            "component": "I3_K5",
            "independent_unit_type": "not_applicable",
            "independent_unit_count": 0,
            "cells": 0,
            "variants_per_independent_unit": 0,
            "not_applicable_reason": ("this profile renders no option list and "
                                      "no label alphabet, so K5 has no "
                                      "referent; not_applicable is not a pass"),
        })
    for record in components:
        record["independent_units_total"] = (record["independent_unit_count"]
                                             * record["cells"])
        record["rendered_rows"] = (record["independent_units_total"]
                                   * record["variants_per_independent_unit"])
        if record["independent_unit_type"] == "base_item_contrast_cluster":
            if record["variants_per_independent_unit"] != (
                    VARIANTS_PER_CONTRAST_CLUSTER):
                raise AssertionError("an I3 cluster does not hold exactly two "
                                     "variants in %s" % record["component"])
            if record["rendered_rows"] != (record["independent_units_total"]
                                           * VARIANTS_PER_CONTRAST_CLUSTER):
                raise AssertionError("rendered rows are not clusters x 2 in %s"
                                     % record["component"])
    return components


def build_projection():
    streams = {}

    # 7.1 Deterministic I0 fixtures. No model, no role, no forward pass.
    k5_fixtures = (len(K5_CONTRASTS) * COMPLETE_BLOCK_SIZE
                   * VARIANTS_PER_CONTRAST_CLUSTER)
    k6_fixtures = (len(K6_CONTRASTS) * 4 * VARIANTS_PER_CONTRAST_CLUSTER)
    indicator_fixtures = len(build_indicator_truth_table())
    na_fixtures = len(K5_CONTRASTS) * 2
    scorer_fixtures = 4 * 4
    streams["deterministic_I0_fixtures"] = {
        "scope": "renderer, content mapping, scorer and indicator fixtures",
        "uses_model": False,
        "model_roles": 0,
        "base_items": k5_fixtures + k6_fixtures,
        "base_item_contrast_clusters": (len(K5_CONTRASTS) * COMPLETE_BLOCK_SIZE
                                        + len(K6_CONTRASTS) * 4),
        "variants_per_cluster": VARIANTS_PER_CONTRAST_CLUSTER,
        "rendered_rows": (k5_fixtures + k6_fixtures + indicator_fixtures
                          + na_fixtures + scorer_fixtures),
        "scored_rows": (k5_fixtures + k6_fixtures + indicator_fixtures
                        + na_fixtures + scorer_fixtures),
        "forward_passes": 0,
        "logit_reads": 0,
        "generated_tokens_upper_bound": 0,
        "breakdown": {
            "k5_constructor_fixtures": k5_fixtures,
            "k6_constructor_fixtures": k6_fixtures,
            "indicator_truth_table_fixtures": indicator_fixtures,
            "not_applicable_branch_fixtures": na_fixtures,
            "scorer_branch_fixtures": scorer_fixtures,
        },
    }

    # 7.2 Target-role development for the three selectable profiles.
    per_profile = {}
    for profile in ("S1", "S2", "S3"):
        components = _profile_component_cells(profile)
        rendered = sum(record["rendered_rows"] for record in components)
        clusters = sum(record["independent_units_total"] for record in components
                       if record["independent_unit_type"]
                       == "base_item_contrast_cluster")
        base_items = sum(record["independent_units_total"] for record in components
                         if record["independent_unit_type"] == "base_item")
        if profile == "S3":
            # Under the current single-token answer domain S3's ranking is
            # analytically identical to S2's under the same prefix, so S3 reuses
            # the S2 forward pass and adds nothing.
            per_profile[profile] = {
                "components": components,
                "base_items": base_items,
                "base_item_contrast_clusters": clusters,
                "variants_per_cluster": VARIANTS_PER_CONTRAST_CLUSTER,
                "rendered_rows_if_independently_rendered": (
                    rendered * len(TARGET_MODEL_ROLES)),
                "incremental_rendered_rows": 0,
                "incremental_scored_rows": 0,
                "incremental_forward_passes": 0,
                "incremental_sequence_scoring_rows": 0,
                "derived_from": "S2",
                "why": ("under the registered single-token answer domain the "
                        "length-normalised sequence score of a one-token "
                        "candidate is a monotone function of that token's log "
                        "probability, so S3's argmax equals S2's by "
                        "construction; the comparison is CPU arithmetic on the "
                        "logits S2 already recorded"),
            }
            continue
        per_profile[profile] = {
            "components": components,
            "base_items": base_items,
            "base_item_contrast_clusters": clusters,
            "variants_per_cluster": VARIANTS_PER_CONTRAST_CLUSTER,
            "rendered_rows_per_role": rendered,
            "model_roles": len(TARGET_MODEL_ROLES),
            "rendered_rows": rendered * len(TARGET_MODEL_ROLES),
            "scored_rows": rendered * len(TARGET_MODEL_ROLES),
            "forward_passes": rendered * len(TARGET_MODEL_ROLES),
            "logit_reads": rendered * len(TARGET_MODEL_ROLES),
            "generated_tokens_upper_bound": 0,
        }
    streams["target_role_development"] = {
        "scope": ("every applicable development component for each selectable "
                  "profile, scored on the development split"),
        "uses_model": True,
        "model_roles": list(TARGET_MODEL_ROLES),
        "excludes": ["I4, which is scoped to the RP role only",
                     "S4, which is a never-selectable diagnostic"],
        "by_profile": per_profile,
        "scored_rows": sum(per_profile[p].get("scored_rows", 0)
                           for p in per_profile),
        "forward_passes": sum(per_profile[p].get("forward_passes", 0)
                              for p in per_profile),
        "generated_tokens_upper_bound": 0,
    }

    # 7.3 External positive-reference qualification. Unresolved under OD2.
    streams["positive_reference_external_P3Q"] = {
        "scope": ("qualification of the positive reference through a canonical "
                  "interface external to S1-S4, under a later authority"),
        "uses_model": True,
        "model_roles": [POSITIVE_REFERENCE_ROLE],
        "base_items": None,
        "base_item_contrast_clusters": None,
        "variants_per_cluster": None,
        "rendered_rows": None,
        "scored_rows": None,
        "forward_passes": None,
        "generated_tokens_upper_bound": None,
        "numeric_status": "UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2",
        "why_null": ("the checkpoint, the canonical qualification interface, "
                     "the qualification bank, the floor, n, the multiplicity "
                     "treatment and the stop rule are all open under OD2; a "
                     "number here would imply a selection that has not been "
                     "made"),
    }

    # 7.4 RP gate I4 under each candidate profile.
    i4_cells = len(PRIMITIVE_OPERATION_FAMILIES) * len(COMPOSITION_DEPTHS)
    i4_base_items = i4_cells * _gate_n("I4")
    i4_by_profile = {}
    for profile in ("S1", "S2", "S3"):
        if profile == "S3":
            i4_by_profile[profile] = {
                "base_items": i4_base_items,
                "incremental_rendered_rows": 0,
                "incremental_scored_rows": 0,
                "incremental_forward_passes": 0,
                "derived_from": "S2",
            }
            continue
        i4_by_profile[profile] = {
            "base_items": i4_base_items,
            "base_item_contrast_clusters": 0,
            "variants_per_cluster": 1,
            "rendered_rows": i4_base_items,
            "scored_rows": i4_base_items,
            "forward_passes": i4_base_items,
            "logit_reads": i4_base_items,
        }
    streams["RP_I4_under_candidate_profiles"] = {
        "scope": ("the positive reference scored on the registered K4 "
                  "construct through each candidate profile, separately per "
                  "operation family and depth"),
        "uses_model": True,
        "model_roles": [POSITIVE_REFERENCE_ROLE],
        "cells": i4_cells,
        "unit_of_n": ("RP base items per operation-family x depth cell "
                      "per candidate profile"),
        "n_per_cell": _gate_n("I4"),
        "by_profile": i4_by_profile,
        "scored_rows": sum(i4_by_profile[p].get("scored_rows", 0)
                           for p in i4_by_profile),
        "forward_passes": sum(i4_by_profile[p].get("forward_passes", 0)
                              for p in i4_by_profile),
        "generated_tokens_upper_bound": 0,
        "conjunction": ("every registered operation family and every depth "
                        "must pass; no pooling across families or depths"),
        "precondition": ("RP must already hold valid external P3-Q evidence "
                         "under a later authority; no such evidence exists"),
    }

    # 7.5 One-shot confirmation of the single development-selected profile.
    # No profile is selected, so the projection is published as an upper bound
    # under the most expensive profile and is explicitly labelled as such.
    confirmation_components = _profile_component_cells("S1")
    confirmation_rendered = sum(record["rendered_rows"]
                                for record in confirmation_components)
    streams["selected_profile_one_shot_confirmation"] = {
        "scope": ("every applicable component for the single "
                  "development-selected profile, on the physically disjoint "
                  "one-shot confirmation split"),
        "uses_model": True,
        "model_roles": list(TARGET_MODEL_ROLES) + [POSITIVE_REFERENCE_ROLE],
        "selected_profile": None,
        "upper_bound_profile_used_for_this_projection": "S1",
        "why_upper_bound": ("no profile is selected in this round; S1 is the "
                            "most expensive applicable profile, so its cost "
                            "bounds every outcome of the selection map"),
        "base_items": sum(record["independent_units_total"]
                          for record in confirmation_components
                          if record["independent_unit_type"] == "base_item"),
        "base_item_contrast_clusters": sum(
            record["independent_units_total"]
            for record in confirmation_components
            if record["independent_unit_type"] == "base_item_contrast_cluster"),
        "variants_per_cluster": VARIANTS_PER_CONTRAST_CLUSTER,
        "target_role_rendered_rows": (confirmation_rendered
                                      * len(TARGET_MODEL_ROLES)),
        "rp_i4_rendered_rows": i4_base_items,
        "rendered_rows": (confirmation_rendered * len(TARGET_MODEL_ROLES)
                          + i4_base_items),
        "scored_rows": (confirmation_rendered * len(TARGET_MODEL_ROLES)
                        + i4_base_items),
        "forward_passes": (confirmation_rendered * len(TARGET_MODEL_ROLES)
                           + i4_base_items),
        "generated_tokens_upper_bound": 0,
        "accessible_now": False,
    }

    # 7.6 S4 diagnostic generation. Never selectable, zero selection authority.
    s4_components = _profile_component_cells("S4")
    s4_rendered = sum(record["rendered_rows"] for record in s4_components)
    streams["S4_diagnostic_generation"] = {
        "scope": "the never-selectable free-generation diagnostic profile",
        "uses_model": True,
        "model_roles": list(TARGET_MODEL_ROLES),
        "selection_authority": "none; excluded from every success union",
        "base_items": sum(record["independent_units_total"]
                          for record in s4_components
                          if record["independent_unit_type"] == "base_item"),
        "base_item_contrast_clusters": sum(
            record["independent_units_total"] for record in s4_components
            if record["independent_unit_type"] == "base_item_contrast_cluster"),
        "variants_per_cluster": VARIANTS_PER_CONTRAST_CLUSTER,
        "rendered_rows_per_role": s4_rendered,
        "rendered_rows": s4_rendered * len(TARGET_MODEL_ROLES),
        "scored_rows": s4_rendered * len(TARGET_MODEL_ROLES),
        "forward_passes": None,
        "generations": s4_rendered * len(TARGET_MODEL_ROLES),
        "generated_tokens_upper_bound": (s4_rendered * len(TARGET_MODEL_ROLES)
                                         * S4_GENERATED_TOKEN_UPPER_BOUND_PER_ROW),
        "registered_generated_token_bound_per_row": (
            S4_GENERATED_TOKEN_UPPER_BOUND_PER_ROW),
    }

    # 7.7 Dimensional identities. Asserted, not narrated.
    identities = []
    for profile, record in per_profile.items():
        for component in record["components"]:
            if component["independent_unit_type"] != "base_item_contrast_cluster":
                continue
            expected = (component["independent_units_total"]
                        * VARIANTS_PER_CONTRAST_CLUSTER)
            if component["rendered_rows"] != expected:
                raise AssertionError(
                    "%s %s rendered rows %d are not clusters x 2"
                    % (profile, component["component"],
                       component["rendered_rows"]))
            identities.append({
                "profile": profile,
                "component": component["component"],
                "identity": "rendered_rows = base_item_contrast_clusters x 2",
                "base_item_contrast_clusters": component[
                    "independent_units_total"],
                "rendered_rows": component["rendered_rows"],
                "holds": True,
            })
    if per_profile["S3"]["incremental_forward_passes"] != 0:
        raise AssertionError("S3 must add zero forward passes in the current "
                             "single-token domain")
    if per_profile["S3"]["incremental_sequence_scoring_rows"] != 0:
        raise AssertionError("S3 must add zero sequence-scoring rows in the "
                             "current single-token domain")
    return {
        "character": ("planning arithmetic only; this authorises nothing, "
                      "approves no budget and creates no execution authority"),
        "unit_definitions": {
            "base_item": "one registered question stem",
            "base_item_contrast_cluster": ("one base item rendered in exactly "
                                           "two registered variants; the "
                                           "independent sampling unit for I3"),
            "rendered_row": "one emitted presentation of one variant",
            "scored_row": "one rendered row scored under one (profile, role)",
            "n": ("always the count of independent units in one cell, never a "
                  "rendered-row or scored-row count; every table states the "
                  "unit at the point of definition"),
        },
        "prohibition": ("a single undifferentiated total is prohibited; every "
                        "stream reports its own units"),
        "work_streams": streams,
        "dimensional_identities": identities,
        "s3_current_domain_accounting": {
            "additional_forward_passes": 0,
            "additional_sequence_scoring_rows": 0,
            "reuses": "the S2 forward pass and logit read under the same prefix",
            "future_multi_token_activation": ("outside this projection; it "
                                              "requires a new authority, image, "
                                              "scoring contract and cost table"),
        },
        "executed_operation_counts": {
            "model_downloads": 0,
            "weight_loads": 0,
            "tokenizer_constructions": 0,
            "forward_passes": 0,
            "sequence_scorings": 0,
            "generations": 0,
            "activation_extractions": 0,
            "gpu_jobs": 0,
            "provider_calls": 0,
            "bank_rows": 0,
            "seeds_drawn": 0,
            "evidence_rows": 0,
        },
    }


# --------------------------------------------------------------------------
# 8. Descriptive-only paired summary specification
#
# Retained for readability and for diagnosing where an invariance failure sits.
# It carries no null, no alpha, no p-value, no confidence-based pass or fail, no
# equivalence declaration, no rescue path and no ranking weight. The Tango
# score procedure, its critical values, its equivalence margins and the
# four-point discordance grid are removed from every decision role.
# --------------------------------------------------------------------------

def build_descriptive_paired_specification():
    return {
        "status": "DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY",
        "reported_per": "contrast cell",
        "reported_quantities": [
            "the paired 2x2 table of variant-1 correctness by variant-2 "
            "correctness",
            "the raw discordance count and rate",
            "the paired accuracy difference",
        ],
        "carries_no": [
            "null hypothesis", "alpha", "p-value", "critical value",
            "equivalence margin", "confidence-based pass or fail",
            "equivalence declaration", "rescue path for a failed J_both",
            "ranking weight in the selection map",
        ],
        "retired_procedure": {
            "name": "Tango (1998) paired score equivalence procedure",
            "retired_from": [
                "I3 gate authority", "profile eligibility",
                "development selection", "confirmation", "claim language",
                "equivalence margins", "critical values",
                "the four-point discordance grid",
                "any conservativeness or verified-size statement",
            ],
            "operator_resolution": (
                "S3MR-004 and S3MR-005 are resolved by removal rather than by "
                "repair: the uncontrolled asymptotic rule is unnecessary for "
                "the primary construct, so it is withdrawn from inferential "
                "use instead of being recalibrated"),
            "historical_evidence": (
                "the independent review's recalculation is preserved unedited "
                "as immutable historical evidence at "
                "studies/study3/analysis/independent_methods_recalculation.py "
                "and its committed tables"),
            "second_reviewer_question": (
                "does retiring the paired aggregate-equivalence procedure from "
                "every decision role fully remove the size-control defect "
                "recorded in S3MR-004 and S3MR-005, or does a residual "
                "decision path remain?"),
            "disposition_status": "PROPOSED_RESOLVED_SUBJECT_TO_INDEPENDENT_REVIEW",
        },
    }


# --------------------------------------------------------------------------
# 9. Table construction
# --------------------------------------------------------------------------

def build_tables():
    construction = verify_pairwise_construction()

    development = [_binomial_row(spec, DEVELOPMENT_COMPONENT_ALPHA,
                                 "development")
                   for spec in GATE_SPECS]
    confirmation = [_binomial_row(spec, CONFIRMATION_COMPONENT_ALPHA,
                                  "confirmation")
                    for spec in GATE_SPECS]

    for row in development:
        if row["alpha_exact_rational"] != _rational(DEVELOPMENT_COMPONENT_ALPHA):
            raise AssertionError("a development component is not at 1/600")
        if not row["meets_target_power"]:
            raise AssertionError("%s does not reach the target power at p1"
                                 % row["gate"])
        if row["degenerate_rejection_region"]:
            raise AssertionError("%s has a degenerate rejection region"
                                 % row["gate"])
    for row in confirmation:
        if row["alpha_exact_rational"] != _rational(CONFIRMATION_COMPONENT_ALPHA):
            raise AssertionError("a confirmation component is not at 1/200")
        if row["degenerate_rejection_region"]:
            raise AssertionError("%s has a degenerate confirmation rejection "
                                 "region" % row["gate"])

    # The exact rational identity that makes the fixed denominator meaningful.
    if (DEVELOPMENT_COMPONENT_ALPHA * SELECTABLE_PROFILE_DENOMINATOR
            != STUDY_DEVELOPMENT_SCREENING_ALPHA):
        raise AssertionError("the per-profile alpha does not reconstruct the "
                             "study-level screening alpha exactly")

    # S3MR-006 and S3MR-015: exactly one active I3 floor, and it is 0.90.
    active_i3_floors = {row["p0_exact_rational"]
                        for row in development + confirmation
                        if row["gate"] == "I3"}
    if active_i3_floors != {_rational(Fraction(9, 10))}:
        raise AssertionError("more than one active I3 floor is registered: %r"
                             % sorted(active_i3_floors))

    # Descriptive Clopper-Pearson bounds, with the tail convention named.
    clopper = []
    for cells in (4, 8, 12, 24):
        simultaneous = STUDY_DEVELOPMENT_SCREENING_ALPHA / cells
        for n, successes in ((256, 250), (256, 245), (128, 120)):
            clopper.append({
                "status": "DESCRIPTIVE_ONLY_NO_GATE_AUTHORITY",
                "simultaneous_cells": cells,
                "unit_of_n": "independent units in the cell",
                "n": n,
                "successes": successes,
                "two_sided_simultaneous_mass": _render(float(simultaneous),
                                                       TAIL_DIGITS),
                "two_sided_simultaneous_mass_exact_rational": _rational(
                    simultaneous),
                "lower_tail_mass_consumed_by_this_bound": _render(
                    float(simultaneous / 2), TAIL_DIGITS),
                "tail_convention": ("two-sided simultaneous mass, of which half "
                                    "is consumed by the lower bound reported "
                                    "here; the field is named after the mass it "
                                    "actually consumes, which S3MR-019 recorded "
                                    "draft-v0.2 did not do"),
                "clopper_pearson_lower_bound": clopper_pearson_lower(
                    successes, n, simultaneous / 2),
            })

    # Selected-label uniformity: a diagnostic nuisance report only.
    uniformity = []
    for n in (256, 512, 1024):
        mass = STUDY_DEVELOPMENT_SCREENING_ALPHA / OPTION_SLOTS
        uniformity.append({
            "status": "DIAGNOSTIC_NUISANCE_REPORT_ONLY",
            "carries_gate_authority": False,
            "carries_eligibility_authority": False,
            "carries_selection_authority": False,
            "carries_confirmation_authority": False,
            "unit_of_n": "scored rows in the cell",
            "n": n,
            "labels": OPTION_SLOTS,
            "expected_per_label": n / OPTION_SLOTS,
            "two_sided_mass_across_the_band": _render(float(mass), TAIL_DIGITS),
            "two_sided_mass_exact_rational": _rational(mass),
            "tail_convention": ("two-sided central band; each tail holds at "
                                "most half the stated mass"),
            "acceptance_band": central_acceptance_band(n, Fraction(1, 4), mass),
            "applies_to": ("label-bearing profiles only; not_applicable to S2 "
                           "and S3, which display no label alphabet"),
        })

    return {
        "document_class": "design_statistics_derivation",
        "draft_version": "draft-v0.3",
        "status": "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS_NOT_FROZEN",
        "disposition_status": (
            "PROPOSED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW"),
        "declared_assumptions": {
            "study_development_screening_alpha": _render(
                float(STUDY_DEVELOPMENT_SCREENING_ALPHA), TAIL_DIGITS),
            "study_development_screening_alpha_exact_rational": _rational(
                STUDY_DEVELOPMENT_SCREENING_ALPHA),
            "selectable_profile_denominator": SELECTABLE_PROFILE_DENOMINATOR,
            "denominator_is_fixed_before_data": True,
            "denominator_never_shrinks": True,
            "development_component_alpha": _render(
                float(DEVELOPMENT_COMPONENT_ALPHA), TAIL_DIGITS),
            "development_component_alpha_exact_rational": _rational(
                DEVELOPMENT_COMPONENT_ALPHA),
            "confirmation_component_alpha": _render(
                float(CONFIRMATION_COMPONENT_ALPHA), TAIL_DIGITS),
            "confirmation_component_alpha_exact_rational": _rational(
                CONFIRMATION_COMPONENT_ALPHA),
            "target_power": _render(float(TARGET_POWER), 4),
            "within_profile_correction": (
                "none; the components form an intersection-union conjunction, "
                "so every applicable component must pass and no further "
                "within-profile Bonferroni correction is applied"),
            "across_profile_correction": (
                "Bonferroni over the fixed denominator %d"
                % SELECTABLE_PROFILE_DENOMINATOR),
            "confirmation_correction": (
                "none across profiles; exactly one pre-selected profile enters "
                "the one-shot confirmation split and no reselection is "
                "permitted, so the claim is conditional on that profile"),
            "decimal_fields_are": ("renderings of the exact rational policy, "
                                   "not the source of truth"),
        },
        "operation_counts": {
            "model_downloads": 0, "weight_loads": 0,
            "tokenizer_constructions": 0, "forward_passes": 0,
            "sequence_scorings": 0, "generations": 0, "gpu_jobs": 0,
            "provider_calls": 0, "bank_rows": 0, "seeds_drawn": 0,
            "evidence_rows": 0, "confirmation_accesses": 0,
            "interfaces_selected": 0, "positive_references_selected": 0,
        },
        "i3_pairwise_construction_verification": construction,
        "i3_contrast_registry": {
            "k5": [dict(contrast) for contrast in K5_CONTRASTS],
            "k6": [dict(contrast) for contrast in K6_CONTRASTS],
            "k5_applicability": {
                "applicable_profiles": ["S1", "S4"],
                "not_applicable_profiles": ["S2", "S3"],
                "not_applicable_semantics": (
                    "not_applicable is a third value: it is not a pass, not a "
                    "zero effect and not evidence of robustness, and it may "
                    "never be counted as a satisfied component"),
            },
            "k6_applicability": {"applicable_profiles": ["S1", "S2", "S3", "S4"]},
            "combined_factor_interactions": (
                "outside the Study 3 claim ceiling; the seven K5 cells test "
                "registered one-factor contrasts only and imply no "
                "full-factorial robustness"),
        },
        "i3_indicator_truth_table": build_indicator_truth_table(),
        "i3_indicator_semantics": {
            "J_inv": ("1 iff both variants produce valid answer-domain content "
                      "and the two mapped contents are byte-identical after the "
                      "registered content mapping; stable invalid or "
                      "unparseable output is 0"),
            "J_cor": ("1 iff both variants are scored correct against the "
                      "unique registered ground truth; a stable but wrong "
                      "answer is 0"),
            "J_both": "J_inv AND J_cor; the primary I3 gate indicator",
            "expected_integrity_invariant": (
                "under a unique ground truth J_cor implies J_inv; this is "
                "recorded as an expected invariant and is not treated as "
                "evidence that the two indicators are independent"),
            "why_the_conjunction_is_retained": (
                "so that stable-wrong and stable-invalid outcomes fail closed "
                "rather than being scored as invariance"),
            "estimand": ("Pr(J_both = 1) over independently sampled base-item "
                         "contrast clusters, separately in every applicable "
                         "atomic contrast cell"),
        },
        "development_exact_binomial_components": development,
        "confirmation_exact_binomial_components": confirmation,
        "development_selection_map": build_selection_map(),
        "descriptive_paired_summary": build_descriptive_paired_specification(),
        "descriptive_clopper_pearson_lower_bounds": clopper,
        "selected_label_uniformity_diagnostic": uniformity,
        "projected_operation_accounting": build_projection(),
        "pooling_prohibitions": [
            "K5 and K6 are never pooled",
            "contrast IDs are never pooled",
            "the two label alphabets are never pooled",
            "K5 position contrast cells and K5 symbol contrast cells are never "
            "pooled",
            "source strata are never pooled",
            "primitive operation families are never pooled",
            "K4 depth 2 and depth 3 are never pooled",
            "checkpoint roles are never pooled",
            "interface profiles are never pooled",
            "renderings are never pooled",
            "splits are never pooled",
            "J_inv, J_cor and the descriptive paired table may never rescue a "
            "failed J_both",
        ],
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
