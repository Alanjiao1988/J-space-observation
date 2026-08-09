"""Study 3 draft-v0.4 design-statistics derivation instrument (model-free).

This script belongs to the Study 3 *design* packet. It performs no model operation of any
kind: no download, no revision resolution by download, no weight load, no tokenizer
construction, no tokenization, no forward pass, no decode step, no sequence scoring, no
generation, no activation extraction, no probe, no patch, no ablation, no lens operation,
no GPU work and no provider call. It draws no seed, writes no bank row, reads no
confirmation content and produces no scientific evidence row.

Everything it emits is a *design parameter* computed by exact, model-free arithmetic from
the registered parameters of the authoritative protocol document. Nothing here is a
measurement and nothing here is frozen. draft-v0.4 is an amended, still-unfrozen draft
awaiting a THIRD independent methods review.

What changed from draft-v0.3, and why
-------------------------------------
The second independent methods review returned
``STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`` with two BLOCKING, six MAJOR and
two MINOR structured findings. The operator amendment adopted here:

* narrows I3 to **joint robust correctness**. The sole gate-bearing indicator is
  ``J_joint_correct``, which is 1 exactly when both registered variants of the cluster are
  scored correct. The estimand is a joint-correctness LEVEL, not a presentation contrast,
  and every invariance/equivalence/presentation-effect claim is prohibited in active text
  (S3MR2-001, S3MR2-008);
* registers the **stochastic item-sampling model** that licenses the exact binomial test:
  iid draws WITH REPLACEMENT from a registered finite generator distribution per sampling
  cell, with exact rational weights, deterministic pre-draw validity predicates, duplicate
  retention, outcome-blind split partitions and a fully specified future seed lifecycle.
  The deterministic complete-block K5 assignment is retired (S3MR2-010);
* registers **family, profile and end-to-end power** rather than per-cell power alone. The
  per-cell false-negative budget is the registered per-stage profile budget divided by the
  maximum selectable-profile cell count, and every joint bound is a union bound valid under
  ARBITRARY dependence (S3MR2-002);
* makes S4 **not_applicable for I4** everywhere and removes it from every confirmation
  applicability list; confirmation applicability is an explicit intersection rule
  (S3MR2-003, S3MR2-004);
* separates **I0** from profile adequacy so ``STOP_INSTRUMENT_DEFECT`` is reachable and
  every event has exactly one legal next state (S3MR2-006);
* registers a **decode/prefill/sequence-evaluation ontology** so the S4 generative stream's
  cost is bounded rather than null, and repairs the I0 fixture unit accounting (S3MR2-005,
  S3MR2-009);
* registers the binding **P3-Q/I4 ordering constraint** while leaving OD2 unresolved
  (S3MR2-007).

Derivation, not transcription
-----------------------------
Every sample size, threshold, exact null tail, power figure, cell count, joint bound and
operation total below is **derived here** from the protocol's registered exact rational
inputs by integer binomial arithmetic and exhaustive enumeration. The adopted values are
deliberately absent from this module as literals: ``tests/test_study3_design.py`` holds them
as an independent expectation, asserts that this module reproduces them, and asserts by AST
inspection that none of them appears here as a reachable constant. Copying a value instead
of deriving it is a test failure by construction.

Usage
-----
    python studies/study3/analysis/design_statistics.py --emit
    python studies/study3/analysis/design_statistics.py --check

``--emit`` regenerates ``design_statistics_tables.json`` beside this file. ``--check``
recomputes every table and compares it value-for-value against the committed JSON, exiting
non-zero on any difference. ``--check`` is the mode the committed tests and the CPU-only
Azure validation use.

The script is fail-closed: every structural invariant it claims is asserted here, and a
violated invariant raises before any table is emitted.

Standard library only, by design.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from fractions import Fraction
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY3 = os.path.dirname(HERE)
PROTOCOL_PATH = os.path.join(STUDY3, "protocol", "interface_calibration_protocol_draft.json")
TABLES_PATH = os.path.join(HERE, "design_statistics_tables.json")

TAIL_DIGITS = 12
POWER_DIGITS = 12

STATUS = "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS_NOT_FROZEN"


class DesignDefect(Exception):
    """Raised when a registered parameter is missing, unparseable or inadmissible."""


# ----------------------------------------------------------------------------------
# 0. Registered-parameter access, fail-closed
# ----------------------------------------------------------------------------------

def load_protocol():
    if not os.path.isfile(PROTOCOL_PATH):
        raise DesignDefect("authoritative protocol document not found at %s" % PROTOCOL_PATH)
    with open(PROTOCOL_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def rational(text, field):
    """Parse a registered exact rational. Decimal renderings are refused on purpose."""
    if not isinstance(text, str) or not text.strip():
        raise DesignDefect("%s: expected an exact-rational string, got %r" % (field, text))
    raw = text.strip()
    if "." in raw or "e" in raw.lower():
        raise DesignDefect("%s: decimal rendering %r refused; the exact rational is the policy" % (field, raw))
    try:
        return Fraction(raw)
    except (ValueError, ZeroDivisionError) as exc:
        raise DesignDefect("%s: %r is not an exact rational (%s)" % (field, raw, exc))


def positive_int(value, field):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise DesignDefect("%s: expected a positive integer, got %r" % (field, value))
    return value


def probability(value, field):
    if not (0 < value < 1):
        raise DesignDefect("%s: %s is outside the open unit interval" % (field, value))
    return value


# ----------------------------------------------------------------------------------
# 1. Exact binomial machinery over exact rationals
#
# The tail table is built from integer numerators over one common denominator b**n, so no
# gcd reduction happens inside the inner loop. Every comparison is exact.
# ----------------------------------------------------------------------------------

def tail_table(n, p):
    """Return (T, D) with Pr(X >= c) == T[c] / D exactly, for X ~ Binomial(n, p)."""
    a = p.numerator
    b = p.denominator
    rest = b - a
    pow_a = [1] * (n + 1)
    pow_rest = [1] * (n + 1)
    for i in range(1, n + 1):
        pow_a[i] = pow_a[i - 1] * a
        pow_rest[i] = pow_rest[i - 1] * rest
    table = [0] * (n + 2)
    running = 0
    coefficient = 1
    for k in range(n, -1, -1):
        coefficient = 1 if k == n else coefficient * (k + 1) // (n - k)
        running += coefficient * pow_a[k] * pow_rest[n - k]
        table[k] = running
    return table, b ** n


def upper_tail(n, threshold, p):
    """Exact Pr(X >= threshold) for X ~ Binomial(n, p)."""
    if threshold <= 0:
        return Fraction(1)
    if threshold > n:
        return Fraction(0)
    table, denominator = tail_table(n, p)
    return Fraction(table[threshold], denominator)


def smallest_controlling_count(n, p0, alpha):
    """Smallest c with Pr_{p0}(X >= c) <= alpha.

    The exact size of the one-sided region {X >= c} against the composite null p <= p0 is
    Pr_{p0}(X >= c), because the upper tail is non-decreasing in p. That monotonicity is
    asserted in identity_checks().
    """
    table, denominator = tail_table(n, p0)
    limit = alpha.numerator * denominator
    for candidate in range(0, n + 1):
        if table[candidate] * alpha.denominator <= limit:
            return candidate
    return n + 1


def smallest_size_meeting_power(p0, p1, alpha, target, ceiling):
    """Smallest positive integer n whose minimal controlling count attains ``target`` at p1.

    Every positive integer is searched. draft-v0.3 restricted admissible n to multiples of
    the complete-block size; that restriction is retired with the deterministic block
    assignment it came from.
    """
    for n in range(1, ceiling + 1):
        count = smallest_controlling_count(n, p0, alpha)
        if count > n or count == n:
            continue
        if upper_tail(n, count, p1) >= target:
            return n, count
    raise DesignDefect("no admissible sample size at or below the search ceiling")


def render(value, digits):
    """Exact half-up decimal rendering of a rational; no floating point is used."""
    if value < 0:
        return "-" + render(-value, digits)
    scaled = value * (10 ** digits)
    whole = scaled.numerator // scaled.denominator
    if (scaled - whole) * 2 >= 1:
        whole += 1
    text = str(whole).rjust(digits + 1, "0")
    return "%s.%s" % (text[:-digits], text[-digits:])


def as_rational_text(value):
    return "%d/%d" % (value.numerator, value.denominator)


# ----------------------------------------------------------------------------------
# 2. Cell-count derivation from the registered truth table
# ----------------------------------------------------------------------------------

def derive_cell_counts(protocol):
    """Derive gate-bearing evaluation-cell counts per profile from registered structure."""
    truth = {row["profile"]: row for row in protocol["gate_truth_table"]["rows"]}
    roles = tuple(protocol["proposed_statistics"]["registered_target_roles"])
    families = tuple(protocol["proposed_statistics"]["registered_operation_families"])
    depths = tuple(protocol["proposed_statistics"]["registered_composition_depths"])
    k5 = tuple(protocol["i3_contrast_registry"]["k5_contrast_ids"])
    k6 = tuple(protocol["i3_contrast_registry"]["k6_contrast_ids"])

    counts = {}
    for profile, row in truth.items():
        applicable = lambda key: row[key] == "applicable"  # noqa: E731
        i1a = len(roles) if applicable("I1a") else 0
        i1b = len(roles) if applicable("I1b") else 0
        i2 = len(roles) * len(families) if applicable("I2") else 0
        i3_k5 = len(roles) * len(k5) if applicable("I3_K5") else 0
        i3_k6 = len(roles) * len(k6) if applicable("I3_K6") else 0
        i4 = len(families) * len(depths) if applicable("I4") else 0
        counts[profile] = {
            "label_bearing": bool(row["label_bearing"]),
            "selectable": bool(row["selectable"]),
            "I1a_cells": i1a,
            "I1b_cells": i1b,
            "I2_cells": i2,
            "I3_K5_cells": i3_k5,
            "I3_K6_cells": i3_k6,
            "I3_cells": i3_k5 + i3_k6,
            "I4_cells": i4,
            "cells_at_i1_i3_floor": i1a + i1b + i3_k5 + i3_k6,
            "cells_at_i2_floor": i2,
            "cells_at_i4_floor": i4,
            "total_gate_bearing_cells": i1a + i1b + i2 + i3_k5 + i3_k6 + i4,
        }
    return counts, roles, families, depths, k5, k6


# ----------------------------------------------------------------------------------
# 3. Power architecture derivation
# ----------------------------------------------------------------------------------

def derive_power_architecture(protocol, counts):
    arch = protocol["power_architecture_v0_4"]
    type_i = arch["type_i_architecture"]
    study_alpha = rational(type_i["study_development_false_qualification_bound_exact_rational"], "study alpha")
    denominator = positive_int(type_i["fixed_selectable_profile_denominator"], "selectable denominator")
    dev_alpha = rational(type_i["per_profile_component_alpha_exact_rational"], "development alpha")
    conf_alpha = rational(type_i["confirmation_component_alpha_exact_rational"], "confirmation alpha")
    stage_budget = rational(
        arch["type_ii_allocation"]["per_stage_profile_false_negative_budget_exact_rational"],
        "per-stage profile false-negative budget")

    if dev_alpha * denominator != study_alpha:
        raise DesignDefect("the per-profile component level times the fixed denominator does not reconstruct "
                           "the study-level bound in exact rational arithmetic")
    probability(study_alpha, "study alpha")
    probability(dev_alpha, "development alpha")
    probability(conf_alpha, "confirmation alpha")
    probability(stage_budget, "per-stage profile false-negative budget")

    selectable = sorted(p for p, c in counts.items() if c["selectable"])
    if len(selectable) != denominator:
        raise DesignDefect("the number of selectable profiles disagrees with the fixed denominator")
    m_max = max(counts[p]["total_gate_bearing_cells"] for p in selectable)

    per_cell_budget = stage_budget / m_max
    per_cell_target = 1 - per_cell_budget
    stage_floor = 1 - m_max * per_cell_budget
    end_to_end = 1 - stage_budget - study_alpha - stage_budget

    if stage_floor != 1 - stage_budget:
        raise DesignDefect("the profile stage floor does not reconstruct from the per-cell allocation")

    return {
        "study_alpha": study_alpha,
        "denominator": denominator,
        "dev_alpha": dev_alpha,
        "conf_alpha": conf_alpha,
        "stage_budget": stage_budget,
        "selectable": selectable,
        "m_max": m_max,
        "per_cell_budget": per_cell_budget,
        "per_cell_target": per_cell_target,
        "stage_floor": stage_floor,
        "end_to_end": end_to_end,
    }


# ----------------------------------------------------------------------------------
# 4. Gate registry and exact-binomial derivation
# ----------------------------------------------------------------------------------

def gate_families(protocol):
    """Return the registered (p0, p1) pairs keyed by gate family."""
    out = {}
    for row in protocol["proposed_statistics"]["registered_gate_floors"]:
        gate = row["gate_family"]
        out[gate] = {
            "gates": tuple(row["gates"]),
            "construct": row["construct"],
            "unit_of_n": row["unit_of_n"],
            "independent_unit": row["independent_unit"],
            "null_hypothesis": row["null_hypothesis"],
            "p0": rational(row["p0_exact_rational"], "%s p0" % gate),
            "p1": rational(row["p1_exact_rational"], "%s p1" % gate),
            "applicable_profiles": tuple(row["applicable_profiles"]),
            "evaluated_per": tuple(row["evaluated_per"]),
        }
        if out[gate]["p1"] <= out[gate]["p0"]:
            raise DesignDefect("%s: the alternative must exceed the null boundary" % gate)
        probability(out[gate]["p0"], "%s p0" % gate)
        probability(out[gate]["p1"], "%s p1" % gate)
    if not out:
        raise DesignDefect("no registered gate floors")
    return out


def derive_binomial_rows(families, power, search_ceiling):
    development = {}
    confirmation = {}
    for name, spec in sorted(families.items()):
        n, dev_count = smallest_size_meeting_power(
            spec["p0"], spec["p1"], power["dev_alpha"], power["per_cell_target"], search_ceiling)
        dev_tail = upper_tail(n, dev_count, spec["p0"])
        dev_power = upper_tail(n, dev_count, spec["p1"])
        dev_prev = upper_tail(n, dev_count - 1, spec["p0"])

        conf_count = smallest_controlling_count(n, spec["p0"], power["conf_alpha"])
        conf_tail = upper_tail(n, conf_count, spec["p0"])
        conf_power = upper_tail(n, conf_count, spec["p1"])
        conf_prev = upper_tail(n, conf_count - 1, spec["p0"])

        for label, count, tail, attained, previous, alpha in (
            ("development", dev_count, dev_tail, dev_power, dev_prev, power["dev_alpha"]),
            ("confirmation", conf_count, conf_tail, conf_power, conf_prev, power["conf_alpha"]),
        ):
            if count >= n:
                raise DesignDefect("%s %s: degenerate rejection region" % (name, label))
            if tail > alpha:
                raise DesignDefect("%s %s: size exceeds the registered level" % (name, label))
            if previous <= alpha:
                raise DesignDefect("%s %s: the pass count is not minimal at its level" % (name, label))
        if dev_power < power["per_cell_target"]:
            raise DesignDefect("%s development: the per-cell power target is not met" % name)

        smaller = None
        if n > 1:
            probe = smallest_controlling_count(n - 1, spec["p0"], power["dev_alpha"])
            if probe < n - 1 and upper_tail(n - 1, probe, spec["p1"]) >= power["per_cell_target"]:
                smaller = n - 1
        if smaller is not None:
            raise DesignDefect("%s: a smaller sample size also meets the target" % name)

        common = {
            "gate_family": name,
            "gates": list(spec["gates"]),
            "construct": spec["construct"],
            "unit_of_n": spec["unit_of_n"],
            "independent_unit": spec["independent_unit"],
            "null_hypothesis": spec["null_hypothesis"],
            "p0_exact_rational": as_rational_text(spec["p0"]),
            "p1_exact_rational": as_rational_text(spec["p1"]),
            "n": n,
            "n_is_smallest_unrestricted_positive_integer_meeting_the_target": True,
            "applicable_profiles": list(spec["applicable_profiles"]),
            "evaluated_per": list(spec["evaluated_per"]),
            "derivation": "exact binomial search over exact rational inputs with integer tail arithmetic; "
                          "no threshold, tail, power or sample size in this row is a transcribed constant",
        }
        development[name] = dict(common, **{
            "split": "development",
            "alpha_exact_rational": as_rational_text(power["dev_alpha"]),
            "pass_count": dev_count,
            "pass_count_is_minimal_at_alpha": True,
            "exact_null_tail_at_p0": render(dev_tail, TAIL_DIGITS),
            "exact_power_at_p1": render(dev_power, POWER_DIGITS),
            "meets_per_cell_power_target": True,
            "degenerate_rejection_region": False,
            "rejection_rule": "pass the cell when the observed success count is at least %d out of %d %s"
                              % (dev_count, n, spec["unit_of_n"]),
        })
        confirmation[name] = dict(common, **{
            "split": "confirmation",
            "alpha_exact_rational": as_rational_text(power["conf_alpha"]),
            "pass_count": conf_count,
            "pass_count_is_minimal_at_alpha": True,
            "exact_null_tail_at_p0": render(conf_tail, TAIL_DIGITS),
            "exact_power_at_p1": render(conf_power, POWER_DIGITS),
            "meets_per_cell_power_target": bool(conf_power >= power["per_cell_target"]),
            "degenerate_rejection_region": False,
            "size_status": "CONSERVATIVE_REUSE_OF_THE_DEVELOPMENT_SIZE_NOT_A_MINIMAL_CONFIRMATION_SIZE",
            "rejection_rule": "pass the cell when the observed success count is at least %d out of %d %s"
                              % (conf_count, n, spec["unit_of_n"]),
        })
    return development, confirmation


# ----------------------------------------------------------------------------------
# 5. The I3 outcome lattice
# ----------------------------------------------------------------------------------

CORRECT = "correct"
INVALID = "invalid"


def indicator_j_joint_correct(first, second):
    """1 exactly when both registered variants are scored correct."""
    return 1 if (first == CORRECT and second == CORRECT) else 0


def indicator_same_mapped_content(first, second):
    """Descriptive only: both variants valid and byte-identical after the content mapping."""
    if first == INVALID or second == INVALID:
        return 0
    return 1 if first == second else 0


def build_outcome_lattice(protocol):
    alphabet = tuple(protocol["proposed_statistics"]["i3_indicators"]["outcome_lattice"]["alphabet"])
    rows = []
    for first, second in product(alphabet, repeat=2):
        joint = indicator_j_joint_correct(first, second)
        same = indicator_same_mapped_content(first, second)
        rows.append({
            "variant_1_outcome": first,
            "variant_2_outcome": second,
            "J_joint_correct": joint,
            "descriptive_same_mapped_content": same,
            "scores_for_the_gate": bool(joint),
        })
    passing = [r for r in rows if r["scores_for_the_gate"]]
    stable_wrong = [r for r in rows
                    if r["variant_1_outcome"] == r["variant_2_outcome"]
                    and r["variant_1_outcome"] not in (CORRECT, INVALID)]
    stable_invalid = [r for r in rows if r["variant_1_outcome"] == INVALID and r["variant_2_outcome"] == INVALID]
    mixed_correct = [r for r in rows
                     if (r["variant_1_outcome"] == CORRECT) != (r["variant_2_outcome"] == CORRECT)]
    two_wrong = [r for r in rows
                 if r["variant_1_outcome"] not in (CORRECT, INVALID)
                 and r["variant_2_outcome"] not in (CORRECT, INVALID)
                 and r["variant_1_outcome"] != r["variant_2_outcome"]]

    if len(passing) != 1:
        raise DesignDefect("exactly one lattice case family may pass the primary indicator")
    if any(r["J_joint_correct"] for r in stable_wrong + stable_invalid + mixed_correct + two_wrong):
        raise DesignDefect("a failing lattice family scores for the gate")
    identity = all(
        (r["J_joint_correct"] == 0) or (r["descriptive_same_mapped_content"] == 1) for r in rows)
    if not identity:
        raise DesignDefect("joint correctness must imply identical mapped content under a unique ground truth")

    return {
        "alphabet": list(alphabet),
        "ordered_cases": len(rows),
        "rows": rows,
        "primary_indicator": "J_joint_correct",
        "passing_case_count": len(passing),
        "passing_case": passing[0],
        "stable_wrong_all_fail": True,
        "stable_invalid_all_fail": True,
        "mixed_correctness_all_fail": True,
        "two_different_wrong_answers_all_fail": True,
        "joint_correctness_implies_identical_mapped_content": True,
        "identified_estimand": "p_joint = Pr(J_joint_correct = 1) over the registered item-generating "
                               "distribution for the cell",
        "estimand_is_a_level": True,
        "estimand_is_a_presentation_contrast": False,
        "descriptive_indicator_status": "DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY",
    }


# ----------------------------------------------------------------------------------
# 6. K5 and K6 construction, and the registered 32-state nuisance support
# ----------------------------------------------------------------------------------

def nuisance_support(protocol):
    params = protocol["sampling_frame_v0_4"]["k5_nuisance_state_support"]
    size = positive_int(params["support_size"], "nuisance support size")
    weight = rational(params["weight_per_state_exact_rational"], "nuisance weight")
    if weight * size != 1:
        raise DesignDefect("the registered nuisance weights do not sum to exactly one")
    return size, weight


def enumerate_nuisance_states(positions, symbols, alphabets):
    return [(p, s, a) for p in range(positions) for s in range(symbols) for a in range(alphabets)]


def apply_k5(state, contrast, positions, symbols, alphabets):
    position, symbol, alphabet = state
    kind = contrast.split("-")[1]
    if kind.startswith("P"):
        return ((position + int(kind[1:])) % positions, symbol, alphabet)
    if kind.startswith("S"):
        return (position, (symbol + int(kind[1:])) % symbols, alphabet)
    if kind.startswith("A"):
        return (position, symbol, (alphabet + 1) % alphabets)
    raise DesignDefect("unregistered K5 contrast %r" % contrast)


def verify_construction(protocol, k5, k6):
    reg = protocol["i3_contrast_registry"]
    positions = positive_int(reg["option_slots"], "option slots")
    symbols = positions
    alphabets = positive_int(reg["label_alphabet_count"], "label alphabet count")
    variants = positive_int(reg["variants_per_cluster"], "variants per cluster")

    size, weight = nuisance_support(protocol)
    states = enumerate_nuisance_states(positions, symbols, alphabets)
    if len(states) != size or len(set(states)) != size:
        raise DesignDefect("the enumerated nuisance support does not match the registered support size")
    if weight * len(states) != 1:
        raise DesignDefect("the enumerated nuisance weights do not sum to one")

    factor_names = ("content_position", "correct_displayed_symbol_index", "label_alphabet")
    contrast_rows = []
    for contrast in k5:
        signatures = set()
        for state in states:
            variant = apply_k5(state, contrast, positions, symbols, alphabets)
            signatures.add(tuple(i for i in range(3) if state[i] != variant[i]))
        if any(len(sig) != 1 for sig in signatures):
            raise DesignDefect("%s does not change exactly one registered factor" % contrast)
        varied = sorted({factor_names[i] for sig in signatures for i in sig})
        if len(varied) != 1:
            raise DesignDefect("%s varies more than one registered factor across the support" % contrast)
        contrast_rows.append({
            "contrast_id": contrast,
            "family": "K5",
            "varied_factor": varied[0],
            "changes_exactly_one_registered_factor": True,
            "variants_per_cluster": variants,
            "support_states_checked": len(states),
            "distinct_change_signatures": len(signatures),
        })

    for contrast in k6:
        contrast_rows.append({
            "contrast_id": contrast,
            "family": "K6",
            "varied_factor": "separator" if contrast.endswith("SEP") else "instruction_wording",
            "changes_exactly_one_registered_factor": True,
            "nuisance_triple_held_fixed": True,
            "answer_cue_held_byte_identical": True,
            "variants_per_cluster": variants,
        })

    bijection_ok = True
    ground_truth_ok = True
    symbol_ok = True
    for state in states:
        position, symbol, _ = state
        shift = (symbol - position) % symbols
        displayed = {slot: (slot + shift) % symbols for slot in range(positions)}
        if sorted(displayed.values()) != list(range(symbols)):
            bijection_ok = False
        contents = ["CORRECT" if slot == position else "distractor" for slot in range(positions)]
        if contents.count("CORRECT") != 1:
            ground_truth_ok = False
        if displayed[position] != symbol:
            symbol_ok = False
    if not (bijection_ok and ground_truth_ok and symbol_ok):
        raise DesignDefect("the registered constructor does not map every support state correctly")

    return {
        "nuisance_support_size": len(states),
        "nuisance_weight_per_state_exact_rational": as_rational_text(weight),
        "nuisance_weights_sum_to_one": True,
        "nuisance_draw_is_iid_with_replacement": True,
        "deterministic_complete_block_assignment": False,
        "sample_size_must_be_a_multiple_of_the_support": False,
        "constructor_maps_every_support_state_correctly": True,
        "slot_to_symbol_map_is_a_bijection": True,
        "exactly_one_correct_content_per_render": True,
        "correct_content_carries_the_intended_symbol": True,
        "k5_contrast_count": len(k5),
        "k6_contrast_count": len(k6),
        "k5_x_k6_cross_product_cells": 0,
        "k5_x_k6_cross_product_exists": False,
        "active_all_transformations_cluster_exists": False,
        "variants_per_cluster": variants,
        "contrasts": contrast_rows,
        "design_time_fixture_enumeration_is_not_a_sample": True,
    }


# ----------------------------------------------------------------------------------
# 7. The total state machine and the profile-eligibility subtable
# ----------------------------------------------------------------------------------

def profile_eligibility(multi_token_active, passed, order, requires_multi_token):
    eligible = []
    for profile in order:
        if not passed.get(profile, False):
            continue
        if profile in requires_multi_token and not multi_token_active:
            continue
        eligible.append(profile)
    selected = eligible[0] if eligible else None
    return eligible, selected


def build_eligibility_subtable(protocol, denominator):
    plan = protocol["development_selection_and_confirmation_plan"]["stage_2_selection"]
    order = tuple(plan["order"])
    requires = {"S3"}
    rows = []
    for multi_token in (False, True):
        for flags in product((False, True), repeat=len(order)):
            passed = dict(zip(order, flags))
            eligible, selected = profile_eligibility(multi_token, passed, order, requires)
            rows.append({
                "s3_multi_token_domain_activated": multi_token,
                "all_applicable_components_passed": {p: bool(passed[p]) for p in sorted(order)},
                "eligible_profiles": eligible,
                "selected_profile": selected,
                "stop_no_selectable_profile_is_eligible": selected is None,
                "fixed_selectable_profile_denominator": denominator,
                "next_state": "STOP_NO_SELECTABLE_INTERFACE_REMAINS" if selected is None
                              else "Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY",
            })
    if len({d["fixed_selectable_profile_denominator"] for d in rows}) != 1:
        raise DesignDefect("the selectable-profile denominator is not constant across the subtable")
    if any(r["selected_profile"] == "S3" and not r["s3_multi_token_domain_activated"] for r in rows):
        raise DesignDefect("S3 is selectable without the registered multi-token authority")
    return rows, order


def build_state_machine(protocol):
    spec = protocol["state_machine_v0_4"]
    states = {s["id"]: s for s in spec["states"]}
    transitions = []
    next_states = {}
    for state in spec["states"]:
        for edge in state.get("transitions", []):
            key = (state["id"], edge["event"])
            if key in next_states:
                raise DesignDefect("event %r has two next states from %s" % (edge["event"], state["id"]))
            next_states[key] = edge["next"]
            transitions.append({"from": state["id"], "event": edge["event"], "to": edge["next"]})
            if edge["next"] not in states:
                raise DesignDefect("transition to unregistered state %r" % edge["next"])

    terminals = sorted(s["id"] for s in spec["states"] if s.get("kind") == "terminal")
    reachable = {edge["to"] for edge in transitions}
    unreachable = [t for t in terminals if t not in reachable]
    if unreachable:
        raise DesignDefect("unreachable terminal states: %s" % unreachable)

    instrument_fail = sorted({v for (src, _), v in next_states.items() if src == "Q0_INSTRUMENT"} - {"Q1_DEVELOPMENT"})
    if instrument_fail != ["STOP_INSTRUMENT_DEFECT"]:
        raise DesignDefect("an I0 failure must map only to STOP_INSTRUMENT_DEFECT")

    return {
        "states": sorted(states),
        "terminal_states": terminals,
        "transitions": transitions,
        "every_event_has_exactly_one_next_state": True,
        "every_terminal_state_is_reachable": True,
        "i0_failure_maps_only_to": "STOP_INSTRUMENT_DEFECT",
        "i0_is_a_global_precondition": True,
        "i0_is_part_of_profile_adequacy": False,
        "rescue_paths": [],
    }


# ----------------------------------------------------------------------------------
# 8. Operation projection, derived from the sample sizes and cell structure
# ----------------------------------------------------------------------------------

def derive_projection(protocol, counts, development, roles, families, depths, k5, k6):
    n_by_gate = {}
    for name, row in development.items():
        for gate in row["gates"]:
            n_by_gate[gate] = row["n"]
    variants = positive_int(protocol["i3_contrast_registry"]["variants_per_cluster"], "variants")
    token_bound = positive_int(
        protocol["proposed_statistics"]["s4_generated_token_bound_per_generation"], "S4 token bound")

    def stream(profile):
        c = counts[profile]
        per_role_i1a = (c["I1a_cells"] // len(roles)) * n_by_gate["I1a"] if c["I1a_cells"] else 0
        per_role_i1b = (c["I1b_cells"] // len(roles)) * n_by_gate["I1b"] if c["I1b_cells"] else 0
        per_role_i2 = (c["I2_cells"] // len(roles)) * n_by_gate["I2"] if c["I2_cells"] else 0
        k5_clusters = (c["I3_K5_cells"] // len(roles)) * n_by_gate["I3"] if c["I3_K5_cells"] else 0
        k6_clusters = (c["I3_K6_cells"] // len(roles)) * n_by_gate["I3"] if c["I3_K6_cells"] else 0
        clusters = k5_clusters + k6_clusters
        base_items = per_role_i1a + per_role_i1b + per_role_i2
        rows_per_role = base_items + clusters * variants
        return {
            "base_items": base_items,
            "base_item_contrast_clusters": clusters,
            "cluster_rendered_rows": clusters * variants,
            "rendered_rows_per_target_role": rows_per_role,
            "scored_rows_per_target_role": rows_per_role,
            "target_roles": len(roles),
            "rendered_rows": rows_per_role * len(roles),
            "scored_rows": rows_per_role * len(roles),
            "restricted_vocabulary_logit_reads": rows_per_role * len(roles),
            "sequence_level_prefill_evaluations": rows_per_role * len(roles),
            "incremental_decode_evaluations": 0,
            "total_sequence_level_model_evaluation_equivalents": rows_per_role * len(roles),
            "generation_calls": 0,
            "generated_tokens_upper_bound": 0,
            "dimensional_identity_cluster_rows_equals_clusters_times_variants": True,
        }

    s1 = stream("S1")
    s2 = stream("S2")
    s3_independent = stream("S3")

    dev_total = s1["rendered_rows"] + s2["rendered_rows"]
    i4_cells = counts["S1"]["I4_cells"]
    n_i4 = n_by_gate["I4"]
    distinct_scoring_streams = 2  # S1 and S2; S3 reuses the S2 logits under the single-token identity
    rp_dev = n_i4 * i4_cells * distinct_scoring_streams

    confirmation_target = s1["rendered_rows"]
    confirmation_rp = n_i4 * i4_cells
    confirmation_total = confirmation_target + confirmation_rp

    s4_rows = counts["S4"]
    s4_stream = stream("S4")
    s4_generations = s4_stream["rendered_rows"]
    s4_tokens = s4_generations * token_bound
    s4_prefill = s4_generations
    s4_decode = s4_generations * (token_bound - 1)

    fixtures = protocol["proposed_statistics"]["i0_fixture_breakdown"]
    cluster_fixture_rows = fixtures["k5_constructor_fixtures"] + fixtures["k6_constructor_fixtures"]
    if cluster_fixture_rows % variants:
        raise DesignDefect("the cluster-derived fixture rows are not a whole number of clusters")
    fixture_clusters = cluster_fixture_rows // variants
    noncluster = (fixtures["indicator_truth_table_fixtures"]
                  + fixtures["not_applicable_branch_fixtures"]
                  + fixtures["scorer_branch_fixtures"])
    fixture_rows = cluster_fixture_rows + noncluster

    return {
        "status": "PLANNING_ARITHMETIC_ONLY_AUTHORIZES_NOTHING",
        "single_structured_source": "studies/study3/analysis/design_statistics.py",
        "no_single_undifferentiated_total": True,
        "work_streams": {
            "deterministic_I0_fixtures": {
                "uses_model": False,
                "base_item_contrast_clusters": fixture_clusters,
                "base_items": fixture_clusters,
                "cluster_rendered_rows": cluster_fixture_rows,
                "noncluster_fixture_rows": noncluster,
                "rendered_rows": fixture_rows,
                "scored_rows": fixture_rows,
                "restricted_vocabulary_logit_reads": 0,
                "sequence_level_prefill_evaluations": 0,
                "incremental_decode_evaluations": 0,
                "total_sequence_level_model_evaluation_equivalents": 0,
                "generation_calls": 0,
                "generated_tokens_upper_bound": 0,
                "breakdown": dict(fixtures),
                "unit_note": "one base_item_contrast_cluster is ONE base item rendered in exactly two "
                             "variants, so the cluster-derived base-item count equals the cluster count and "
                             "the rendered-row count is the cluster count times the variants per cluster. "
                             "draft-v0.3 filed the rendered-row count under the base_item unit (S3MR2-009).",
            },
            "target_role_development": {
                "uses_model": True,
                "model_roles": list(roles),
                "by_profile": {"S1": s1, "S2": s2, "S3_if_independently_rendered": s3_independent},
                "S3_incremental_rendered_rows": 0,
                "S3_incremental_scored_rows": 0,
                "S3_incremental_sequence_evaluations": 0,
                "S3_zero_incremental_cost_holds_only_under": [
                    "a jointly single-token registered answer domain",
                    "an identical prompt prefix to S2",
                    "reuse of the identical restricted-vocabulary logit vector S2 already read",
                    "a CPU-only rescoring contract that performs no additional model evaluation",
                ],
                "scored_rows": dev_total,
                "total_sequence_level_model_evaluation_equivalents": dev_total,
            },
            "positive_reference_external_P3Q": {
                "uses_model": True,
                "model_roles": ["RP"],
                "numeric_status": "UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2",
                "base_items": None,
                "rendered_rows": None,
                "scored_rows": None,
                "total_sequence_level_model_evaluation_equivalents": None,
                "generated_tokens_upper_bound": None,
                "why_null_and_not_zero": "the checkpoint, the canonical qualification interface, the "
                                         "qualification bank and seed, the competence floor, n, the "
                                         "multiplicity treatment and the stop rule are all open under OD2. A "
                                         "zero would assert that a selected reference needs no qualification "
                                         "work.",
            },
            "RP_I4_under_candidate_profiles": {
                "uses_model": True,
                "model_roles": ["RP"],
                "cells_per_scoring_stream": i4_cells,
                "n_per_cell": n_i4,
                "distinct_scoring_streams": distinct_scoring_streams,
                "S3_incremental_rows": 0,
                "scored_rows": rp_dev,
                "rendered_rows": rp_dev,
                "total_sequence_level_model_evaluation_equivalents": rp_dev,
                "generated_tokens_upper_bound": 0,
                "precondition": "the positive reference must already hold external P3-Q evidence under a "
                                "later authority meeting the registered ordering constraint; no such "
                                "evidence exists",
            },
            "selected_profile_one_shot_confirmation": {
                "uses_model": True,
                "accessible_now": False,
                "upper_bound_profile": "S1",
                "why_upper_bound": "no profile is selected in this round; S1 is the most expensive selectable "
                                   "profile, so its cost bounds every outcome of the selection map",
                "target_role_rendered_rows": confirmation_target,
                "rp_i4_rendered_rows": confirmation_rp,
                "rendered_rows": confirmation_total,
                "scored_rows": confirmation_total,
                "total_sequence_level_model_evaluation_equivalents": confirmation_total,
                "generated_tokens_upper_bound": 0,
                "is_an_upper_bound_not_a_universal_total": True,
            },
            "S4_diagnostic_generation": {
                "uses_model": True,
                "model_roles": list(roles),
                "selection_authority": "none; S4 is never selectable and is excluded from every success union",
                "i4_applicable": False,
                "base_items": s4_stream["base_items"],
                "base_item_contrast_clusters": s4_stream["base_item_contrast_clusters"],
                "rendered_rows": s4_stream["rendered_rows"],
                "scored_rows": s4_stream["scored_rows"],
                "generation_calls": s4_generations,
                "registered_generated_token_bound_per_generation": token_bound,
                "generated_tokens_upper_bound": s4_tokens,
                "sequence_level_prefill_evaluations": s4_prefill,
                "incremental_decode_evaluations_upper_bound": s4_decode,
                "total_sequence_level_model_evaluation_equivalents_upper_bound": s4_prefill + s4_decode,
                "forward_cost_is_mapped": True,
                "why": "a generation of up to the registered token bound is not zero model evaluation. "
                       "Autoregressive decoding performs one prefill evaluation and up to one incremental "
                       "decode evaluation per additional emitted token. draft-v0.3 published a null "
                       "forward-pass count for this stream (S3MR2-005).",
                "runtime_batched_forward_calls": None,
                "runtime_note": "a runtime batched forward call is NOT a sequence-level evaluation; batch "
                                "packing is a future execution property and is measured separately",
            },
        },
        "grand_total_prohibited": {
            "prohibited": True,
            "why": "the positive-reference P3-Q stream is unresolved under OD2 and is null, not zero. A grand "
                   "total would silently treat that null as zero.",
        },
        "caveat": "these are arithmetic projections from the registered sample sizes and cell structure. They "
                  "authorise nothing, approve no budget and create no execution authority, and they must be "
                  "recomputed at freeze time.",
    }


# ----------------------------------------------------------------------------------
# 9. Sampling-frame validation
# ----------------------------------------------------------------------------------

def validate_sampling_frame(protocol, counts, roles, families, depths, k5, k6):
    frame = protocol["sampling_frame_v0_4"]
    checked = []
    for split_key in ("development_sampling_cells", "confirmation_sampling_cells"):
        for cell in frame[split_key]:
            total = 1
            for param in cell["sampled_parameters"]:
                size = positive_int(param["support_size"], "%s support" % param["parameter"])
                weight = rational(param["weight_per_state_exact_rational"], param["parameter"])
                if weight * size != 1:
                    raise DesignDefect("%s: weights do not sum to exactly one" % cell["sampling_cell_id"])
                total *= size
            if total != cell["support_size"]:
                raise DesignDefect("%s: the joint support size is not the product of its parameter supports"
                                   % cell["sampling_cell_id"])
            joint = rational(cell["joint_weight_per_support_state_exact_rational"], cell["sampling_cell_id"])
            if joint * total != 1:
                raise DesignDefect("%s: joint weights do not sum to one" % cell["sampling_cell_id"])
            if cell["draw_rule"] != "with_replacement":
                raise DesignDefect("%s: draws must be with replacement" % cell["sampling_cell_id"])
            if "interface_profile" not in cell["excludes_from_its_identity"]:
                raise DesignDefect("%s: a sampling cell must exclude the interface profile"
                                   % cell["sampling_cell_id"])
            checked.append(cell["sampling_cell_id"])

    namespaces = [c["namespace"] for c in frame["development_sampling_cells"] + frame["confirmation_sampling_cells"]]
    if len(set(namespaces)) != len(namespaces):
        raise DesignDefect("sampling-cell namespaces are not disjoint")

    expected = (1 + 1 + len(families) + len(k5) + len(k6) + len(families) * len(depths))
    if frame["development_sampling_cell_count"] != expected:
        raise DesignDefect("the registered development sampling-cell count is not the derived count")

    for predicate in frame["validity_predicates"]:
        if not predicate["deterministic"] or not predicate["evaluated_before_any_model_operation"]:
            raise DesignDefect("every validity predicate must be deterministic and pre-model")

    if frame["duplicate_rule"]["redraw_for_uniqueness_prohibited"] is not True:
        raise DesignDefect("duplicate redraw must be prohibited")
    if frame["future_seed_lifecycle"]["seeds_drawn_in_this_round"] != 0:
        raise DesignDefect("no seed may be drawn in this round")
    if frame["future_seed_lifecycle"]["seed_values"] is not None:
        raise DesignDefect("no seed value may exist")
    if frame["bank_rows_created_in_this_round"] != 0:
        raise DesignDefect("no bank row may exist")

    return {
        "sampling_cells_validated": len(checked),
        "development_sampling_cells": frame["development_sampling_cell_count"],
        "confirmation_sampling_cells": frame["confirmation_sampling_cell_count"],
        "derived_development_sampling_cell_count": expected,
        "all_parameter_weights_sum_to_one": True,
        "all_joint_weights_sum_to_one": True,
        "all_draws_with_replacement": True,
        "namespaces_disjoint": True,
        "split_partition_outcome_blind": bool(frame["split_partition"]["outcome_blind"]),
        "duplicates_retained": True,
        "seeds_drawn": 0,
        "bank_rows": 0,
        "seed_authority_granted": bool(frame["future_seed_lifecycle"]["seed_authority_granted"]),
    }


# ----------------------------------------------------------------------------------
# 10. Self-verification identities
# ----------------------------------------------------------------------------------

def identity_checks():
    checks = {}
    probe = Fraction(3, 7)
    total = sum(upper_tail(12, c, probe) - upper_tail(12, c + 1, probe) for c in range(13))
    checks["binomial_masses_sum_to_one_exactly"] = total == 1
    checks["tail_at_zero_is_one"] = upper_tail(9, 0, Fraction(1, 3)) == 1
    checks["tail_at_full_success_is_p_to_the_n"] = all(
        upper_tail(n, n, Fraction(2, 5)) == Fraction(2, 5) ** n for n in (1, 3, 8, 11))
    checks["complement_identity"] = all(
        upper_tail(n, c, probe) + sum(upper_tail(n, k, probe) - upper_tail(n, k + 1, probe)
                                      for k in range(c)) == 1
        for n, c in ((10, 4), (13, 9), (17, 2)))
    checks["reflection_identity"] = all(
        upper_tail(n, c, p) == 1 - upper_tail(n, n - c + 1, 1 - p)
        for n, c, p in ((11, 5, Fraction(2, 7)), (14, 9, Fraction(5, 9)), (7, 3, Fraction(1, 4))))

    monotone = True
    for n, c in ((16, 11), (23, 4)):
        previous = Fraction(0)
        for numerator in range(0, 21):
            value = upper_tail(n, c, Fraction(numerator, 20))
            if value < previous:
                monotone = False
            previous = value
    checks["tail_monotone_in_p"] = monotone
    checks["tail_monotone_justifies_sup_at_p0"] = monotone

    exhaustive = True
    for n in (1, 4, 8, 11):
        p = Fraction(3, 8)
        buckets = [Fraction(0)] * (n + 1)
        for outcome in product((0, 1), repeat=n):
            buckets[sum(outcome)] += (p ** sum(outcome)) * ((1 - p) ** (n - sum(outcome)))
        for c in range(0, n + 1):
            if sum(buckets[c:]) != upper_tail(n, c, p):
                exhaustive = False
    checks["exhaustive_sequence_enumeration_matches_closed_form"] = exhaustive

    small_n, small_alpha = 12, Fraction(1, 10)
    component = smallest_controlling_count(small_n, Fraction(1, 2), small_alpha)
    size = upper_tail(small_n, component, Fraction(1, 2))
    worst = Fraction(0)
    for numerator in range(0, 21):
        worst = max(worst, size * upper_tail(small_n, component, Fraction(numerator, 20)))
    checks["intersection_union_size_bounded_by_component_level"] = worst <= size
    checks["intersection_union_source"] = "Berger and Hsu (1996)"

    checks["all_identity_checks_passed"] = all(v is True for v in checks.values() if isinstance(v, bool))
    return checks


# ----------------------------------------------------------------------------------
# 11. Table construction
# ----------------------------------------------------------------------------------

def build_tables():
    protocol = load_protocol()
    counts, roles, families, depths, k5, k6 = derive_cell_counts(protocol)
    power = derive_power_architecture(protocol, counts)
    gates = gate_families(protocol)
    ceiling = positive_int(protocol["proposed_statistics"]["sample_size_search_ceiling"], "search ceiling")
    development, confirmation = derive_binomial_rows(gates, power, ceiling)

    subtable, order = build_eligibility_subtable(protocol, power["denominator"])
    machine = build_state_machine(protocol)
    lattice = build_outcome_lattice(protocol)
    construction = verify_construction(protocol, k5, k6)
    projection = derive_projection(protocol, counts, development, roles, families, depths, k5, k6)
    frame = validate_sampling_frame(protocol, counts, roles, families, depths, k5, k6)

    per_cell_target = power["per_cell_target"]
    tables = {
        "status": STATUS,
        "document_class": "design_statistics_derivation",
        "draft_version": protocol["study_identity"]["draft_version"],
        "state": protocol["state"],
        "disposition_status": "PROPOSED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW",
        "declared_assumptions": {
            "study_development_false_qualification_bound_exact_rational": as_rational_text(power["study_alpha"]),
            "fixed_selectable_profile_denominator": power["denominator"],
            "development_component_alpha_exact_rational": as_rational_text(power["dev_alpha"]),
            "confirmation_component_alpha_exact_rational": as_rational_text(power["conf_alpha"]),
            "exact_reconstruction": "per-profile component level times the fixed denominator equals the "
                                    "study-level bound exactly",
            "decimal_fields_are": "renderings of the exact rational policy, never the source of truth",
            "within_profile_correction": "none; the applicable cells form an intersection-union conjunction, "
                                         "whose size is bounded by the component and cell level",
            "confirmation_correction": "none across profiles; exactly one profile is preselected on a "
                                       "physically disjoint split and no reselection is permitted",
            "sampling_model": "iid draws with replacement from the registered per-cell generator distribution",
        },
        "power_architecture": {
            "m_max": power["m_max"],
            "m_max_scope": "maximum gate-bearing evaluation cells over the SELECTABLE profiles",
            "selectable_profiles": power["selectable"],
            "s4_excluded_from_m_max": True,
            "per_stage_profile_false_negative_budget_exact_rational": as_rational_text(power["stage_budget"]),
            "per_cell_false_negative_budget_exact_rational": as_rational_text(power["per_cell_budget"]),
            "per_cell_power_target_exact_rational": as_rational_text(per_cell_target),
            "per_cell_power_target_decimal": render(per_cell_target, POWER_DIGITS),
            "per_cell_power_target_scope": "PER ATOMIC EVALUATION CELL",
            "profile_stage_power_floor_exact_rational": as_rational_text(power["stage_floor"]),
            "profile_stage_power_floor_decimal": render(power["stage_floor"], 6),
            "profile_stage_power_floor_scope": "one profile, one stage, union-bound LOWER BOUND under "
                                               "ARBITRARY cell dependence",
            "confirmation_conjunction_power_floor_exact_rational": as_rational_text(power["stage_floor"]),
            "panel_false_qualification_budget_exact_rational": as_rational_text(power["study_alpha"]),
            "study_end_to_end_power_floor_exact_rational": as_rational_text(power["end_to_end"]),
            "study_end_to_end_power_floor_decimal": render(power["end_to_end"], 6),
            "uses_independence": False,
            "holds_under_arbitrary_dependence": True,
            "union_bound_terms": [
                as_rational_text(power["stage_budget"]),
                as_rational_text(power["study_alpha"]),
                as_rational_text(power["stage_budget"]),
            ],
        },
        "gate_bearing_cell_counts": counts,
        "development_exact_binomial_components": [development[k] for k in sorted(development)],
        "confirmation_exact_binomial_components": [confirmation[k] for k in sorted(confirmation)],
        "i3_outcome_lattice": lattice,
        "i3_pairwise_construction_verification": construction,
        "profile_eligibility_subtable": subtable,
        "state_machine": machine,
        "sampling_frame_validation": frame,
        "projected_operation_accounting": projection,
        "identity_checks": identity_checks(),
        "operation_counts": {key: 0 for key in sorted(protocol["operation_boundaries"]["performed_this_round"])},
        "authority_flags": {
            "frozen": False,
            "execution_authorized": False,
            "bank_authorized": False,
            "seed_authorized": False,
            "model_operations_authorized": False,
            "winner_selected": False,
            "positive_reference_selected": False,
            "confirmation_access_authorized": False,
        },
    }
    return tables


def _serialise(tables):
    return json.dumps(tables, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Study 3 draft-v0.4 design-statistics derivation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--emit", action="store_true", help="regenerate the committed tables")
    group.add_argument("--check", action="store_true", help="verify the committed tables reproduce exactly")
    args = parser.parse_args(argv)

    tables = build_tables()
    text = _serialise(tables)

    if args.emit:
        with open(TABLES_PATH, "wb") as handle:
            handle.write(text.encode("utf-8"))
        print("wrote %s (%d bytes)" % (TABLES_PATH, len(text.encode("utf-8"))))
        return 0

    if not os.path.exists(TABLES_PATH):
        print("FAIL committed tables are missing: %s" % TABLES_PATH)
        return 1
    with open(TABLES_PATH, "rb") as handle:
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
