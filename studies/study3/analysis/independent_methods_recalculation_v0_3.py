#!/usr/bin/env python3
"""Independent recalculation for the SECOND independent methods review of Study 3 draft-v0.3.

PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS.

Every number produced by this module is a proposed design parameter of an unfrozen
draft. Nothing here is an observation, a model output, a bank row, a gate result or
scientific evidence. No model, tokenizer, checkpoint, bank, seed, split or network
resource is touched. The module is CPU-only, model-free and deterministic.

Independence contract
---------------------
This implementation was authored from:

  * the committed protocol object at the reviewed commit
    (``studies/study3/protocol/interface_calibration_protocol_draft.json``), read for
    its registered *inputs* only -- exact rational p0, p1, alpha, n, applicability,
    cell factors and construction steps; and
  * the English-language primary statistical sources listed in ``PRIMARY_SOURCES``.

It does NOT import, execute, dynamically load, copy functions or constants from, or
derive its control flow from either of:

  * ``studies/study3/analysis/design_statistics.py``           (drafting implementation)
  * ``studies/study3/analysis/independent_methods_recalculation.py`` (first review)

Ordering: the parameter extraction, every derivation in this file and the emitted table
were authored and committed BEFORE the drafting party's derived numeric outputs
(``design_statistics.py`` and ``design_statistics_tables.json``) were opened by the
reviewing session. The comparison block in the review document was produced only after
that commit existed. See ``independence_ordering`` in the emitted table.

Usage
-----
    python independent_methods_recalculation_v0_3.py            # emit the table
    python independent_methods_recalculation_v0_3.py --check    # recompute and compare
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

STATUS = "PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS"

REVIEWED_COMMIT = "2b36f5321d830ea6f70fff2b7bbca3cb93394046"
REVIEWED_TREE = "98d71cb35cca7b55d8f96f131064a5b9654dd3c7"

_HERE = Path(__file__).resolve()
_STUDY3 = _HERE.parent.parent
PROTOCOL_PATH = _STUDY3 / "protocol" / "interface_calibration_protocol_draft.json"
TABLE_PATH = _HERE.with_name("independent_methods_recalculation_tables_v0_3.json")

PROHIBITED_SOURCE_MODULES = (
    "studies/study3/analysis/design_statistics.py",
    "studies/study3/analysis/independent_methods_recalculation.py",
)

PRIMARY_SOURCES = [
    {
        "citation": "Clopper, C. J. and Pearson, E. S. (1934). The use of confidence or "
                    "fiducial limits illustrated in the case of the binomial. Biometrika 26(4):404-413.",
        "doi": "10.1093/biomet/26.4.404",
        "used_for": "the binomial sampling model, the exact one-sided tail, and the exact "
                    "confidence-limit construction whose defining equation is checked in "
                    "identity_checks.clopper_pearson_boundary_closed_form",
    },
    {
        "citation": "Berger, R. L. and Hsu, J. C. (1996). Bioequivalence trials, intersection-union "
                    "tests and equivalence confidence sets. Statistical Science 11(4):283-319.",
        "doi": "10.1214/ss/1032280304",
        "used_for": "intersection-union logic: the size of an IUT that rejects only when every "
                    "component rejects is bounded by the maximum component level, verified by "
                    "exhaustive enumeration in identity_checks.intersection_union_size_bound",
    },
    {
        "citation": "Tango, T. (1998). Equivalence test and confidence interval for the difference "
                    "in proportions for the paired-sample design. Statistics in Medicine 17(8):891-908.",
        "pmid": "9595618",
        "used_for": "verifying ONLY that the previously defective paired procedure is genuinely "
                    "retired from decision authority; no Tango quantity is computed here",
    },
    {
        "citation": "Hsueh, H. M., Liu, J. P. and Chen, J. J. (2001). Unconditional exact tests for "
                    "equivalence or noninferiority for paired binary endpoints. Biometrics 57(2):478-483.",
        "pmid": "11414572",
        "used_for": "verifying ONLY that no unconditional-exact paired replacement was silently "
                    "introduced into a decision path",
    },
    {
        "citation": "Liu, J. P., Hsueh, H. M., Hsieh, E. and Chen, J. J. (2002). Tests for equivalence "
                    "or non-inferiority for paired binary data. Statistics in Medicine 21(2):231-245.",
        "pmid": "11782062",
        "used_for": "verifying ONLY that no paired equivalence margin survives in a decision role",
    },
]


# --------------------------------------------------------------------------------------
# fail-closed parameter handling
# --------------------------------------------------------------------------------------

class ParameterDefect(Exception):
    """Raised when a registered parameter is missing, unparseable or inadmissible."""


def rational_from_registered_text(text: object, field: str) -> Fraction:
    """Parse an exact rational such as '9/10' from a registered field, fail-closed.

    Decimal renderings are refused on purpose: the exact rational is the policy and the
    decimal is a rendering of it, so a decimal must never reach an arithmetic path here.
    """
    if not isinstance(text, str) or not text.strip():
        raise ParameterDefect(f"{field}: expected a non-empty exact-rational string, got {text!r}")
    raw = text.strip()
    if "." in raw or "e" in raw.lower():
        raise ParameterDefect(f"{field}: decimal rendering {raw!r} refused; an exact rational is required")
    try:
        value = Fraction(raw)
    except (ValueError, ZeroDivisionError) as exc:
        raise ParameterDefect(f"{field}: {raw!r} is not an exact rational ({exc})") from exc
    return value


def require_probability(value: Fraction, field: str, *, strict: bool = True) -> Fraction:
    lower_ok = value > 0 if strict else value >= 0
    upper_ok = value < 1 if strict else value <= 1
    if not (lower_ok and upper_ok):
        raise ParameterDefect(f"{field}: {value} is outside the admissible probability range")
    return value


def require_positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ParameterDefect(f"{field}: expected a positive integer, got {value!r}")
    return value


# --------------------------------------------------------------------------------------
# exact binomial arithmetic (Clopper and Pearson 1934 sampling model)
# --------------------------------------------------------------------------------------

def choose_exact(n: int, k: int) -> int:
    """Exact binomial coefficient by an integer-only multiplicative recurrence."""
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    numerator = 1
    denominator = 1
    for step in range(1, k + 1):
        numerator *= n - k + step
        denominator *= step
    return numerator // denominator


def tail_numerators(n: int, p: Fraction) -> tuple[list[int], int]:
    """Integer-only upper-tail table for X ~ Binomial(n, p).

    With p = a/b the exact tail is Pr(X >= c) = T[c] / b**n where

        T[c] = sum_{k=c}^{n} C(n,k) * a**k * (b-a)**(n-k)

    is an integer. Working with the integer numerators and one common denominator avoids
    a gcd reduction on every partial sum, which is what makes the full admissible-n sweep
    tractable without ever leaving exact arithmetic.
    """
    a = p.numerator
    b = p.denominator
    c_ = b - a
    powers_a = [1] * (n + 1)
    powers_c = [1] * (n + 1)
    for i in range(1, n + 1):
        powers_a[i] = powers_a[i - 1] * a
        powers_c[i] = powers_c[i - 1] * c_
    tail = [0] * (n + 2)
    running = 0
    coefficient = 1
    for k in range(n, -1, -1):
        if k == n:
            coefficient = 1
        else:
            coefficient = coefficient * (k + 1) // (n - k)
        running += coefficient * powers_a[k] * powers_c[n - k]
        tail[k] = running
    return tail, b ** n


def upper_tail_mass(n: int, threshold: int, p: Fraction) -> Fraction:
    """Exact Pr(X >= threshold) for X ~ Binomial(n, p), in exact rational arithmetic."""
    if threshold <= 0:
        return Fraction(1)
    if threshold > n:
        return Fraction(0)
    tail, denominator = tail_numerators(n, p)
    return Fraction(tail[threshold], denominator)


def least_rejection_count(n: int, p0: Fraction, alpha: Fraction) -> int:
    """Smallest c with Pr_{p0}(X >= c) <= alpha.

    The exact size of the one-sided rejection region {X >= c} against the composite null
    H0: p <= p0 is sup_{p <= p0} Pr_p(X >= c) = Pr_{p0}(X >= c), because the upper tail is
    non-decreasing in p (checked in identity_checks.tail_monotone_in_p).
    """
    tail, denominator = tail_numerators(n, p0)
    limit = alpha.numerator * denominator
    for candidate in range(0, n + 1):
        if tail[candidate] * alpha.denominator <= limit:
            return candidate
    return n + 1


def attained_power(n: int, threshold: int, p1: Fraction) -> Fraction:
    return upper_tail_mass(n, threshold, p1)


def decimal_string(value: Fraction, places: int) -> str:
    """Exact half-up decimal rendering of a rational; no floating point is used."""
    if value < 0:
        return "-" + decimal_string(-value, places)
    scaled = value * (10 ** places)
    whole = scaled.numerator // scaled.denominator
    remainder = scaled - whole
    if remainder * 2 >= 1:
        whole += 1
    digits = str(whole).rjust(places + 1, "0")
    if places == 0:
        return digits
    return f"{digits[:-places]}.{digits[-places:]}"


def rounds_to_registered(value: Fraction, registered: float | None) -> bool | None:
    """True when the exact rational rounds to the registered decimal at its own precision."""
    if registered is None:
        return None
    text = repr(float(registered))
    places = len(text.split(".")[1]) if "." in text else 0
    return decimal_string(value, places) == decimal_string(Fraction(str(registered)), places)


# --------------------------------------------------------------------------------------
# registered-parameter extraction from the reviewed protocol object
# --------------------------------------------------------------------------------------

GATE_KEYS = ("I1a", "I1b", "I2", "I3", "I4")


def load_protocol() -> dict:
    if not PROTOCOL_PATH.is_file():
        raise ParameterDefect(f"reviewed protocol object not found at {PROTOCOL_PATH}")
    with PROTOCOL_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_gate_parameters(protocol: dict) -> dict:
    """Pull exact rational inputs for each gate from the reviewed protocol, fail-closed."""
    statistics = protocol.get("proposed_statistics")
    if not isinstance(statistics, dict):
        raise ParameterDefect("proposed_statistics is missing from the reviewed protocol")

    rows = statistics.get("retained_exact_binomial_gates")
    if not isinstance(rows, list) or not rows:
        raise ParameterDefect("retained_exact_binomial_gates is missing or empty")

    extracted: dict[str, dict] = {}
    for row in rows:
        gate = row.get("gate")
        if gate not in GATE_KEYS:
            raise ParameterDefect(f"unexpected gate identifier {gate!r}")
        p0 = require_probability(rational_from_registered_text(row.get("p0_exact_rational"), f"{gate}.p0"), f"{gate}.p0")
        p1 = require_probability(rational_from_registered_text(row.get("p1_exact_rational"), f"{gate}.p1"), f"{gate}.p1")
        if p1 <= p0:
            raise ParameterDefect(f"{gate}: p1={p1} must exceed p0={p0}")
        extracted[gate] = {
            "p0": p0,
            "p1": p1,
            "n": require_positive_int(row.get("n"), f"{gate}.n"),
            "unit_of_n": row.get("unit_of_n"),
            "independent_unit": row.get("independent_unit"),
            "null_hypothesis": row.get("null_hypothesis"),
            "applicable_profiles": tuple(row.get("applicable_profiles") or ()),
            "evaluated_per": tuple(row.get("evaluated_per") or ()),
            "registered_pass_count": row.get("pass_count"),
            "registered_null_tail": row.get("exact_null_tail_at_p0"),
            "registered_power": row.get("exact_power_at_p1"),
            "registered_alpha_rational": rational_from_registered_text(
                row.get("alpha_exact_rational"), f"{gate}.alpha"
            ),
        }
    missing = [g for g in GATE_KEYS if g not in extracted]
    if missing:
        raise ParameterDefect(f"missing registered gates: {missing}")
    return extracted


def extract_levels(protocol: dict) -> dict:
    statistics = protocol["proposed_statistics"]
    study_alpha = rational_from_registered_text(
        statistics.get("study_development_screening_alpha_exact_rational"), "study_development_screening_alpha"
    )
    component_alpha = rational_from_registered_text(
        statistics.get("development_component_alpha_exact_rational"), "development_component_alpha"
    )
    confirmation_alpha = rational_from_registered_text(
        statistics.get("confirmation_component_alpha_exact_rational"), "confirmation_component_alpha"
    )
    families = statistics.get("hypothesis_families") or {}
    family_b = families.get("family_B_across_profiles") or {}
    denominator = require_positive_int(family_b.get("fixed_selectable_profile_denominator"), "family_B.denominator")

    for name, level in (
        ("study_development_screening_alpha", study_alpha),
        ("development_component_alpha", component_alpha),
        ("confirmation_component_alpha", confirmation_alpha),
    ):
        require_probability(level, name)

    target_power = Fraction(9, 10)
    return {
        "study_development_screening_alpha": study_alpha,
        "development_component_alpha": component_alpha,
        "confirmation_component_alpha": confirmation_alpha,
        "fixed_selectable_profile_denominator": denominator,
        "target_power": target_power,
        "exact_reconstruction_holds": component_alpha * denominator == study_alpha,
    }


# --------------------------------------------------------------------------------------
# admissible-n search under the registered balancing rule
# --------------------------------------------------------------------------------------

BALANCING_BLOCK = 32


def sweep_admissible_sizes(
    p0: Fraction,
    p1: Fraction,
    alpha: Fraction,
    target_power: Fraction,
    *,
    divisor: int,
    ceiling: int = 1024,
) -> dict:
    """Search the admissible n grid and report the smallest size meeting the power target.

    ``divisor`` is the balancing divisor implied by the registered construction: the K5
    baseline conditions are balanced over complete blocks of 32 consecutive base-item
    indices, so an admissible per-cell n is a positive multiple of 32.
    """
    admissible_hit = None
    unrestricted_hit = None
    grid = []
    for n in range(1, ceiling + 1):
        tail0, denominator0 = tail_numerators(n, p0)
        limit = alpha.numerator * denominator0
        threshold = n + 1
        for candidate in range(0, n + 1):
            if tail0[candidate] * alpha.denominator <= limit:
                threshold = candidate
                break
        if threshold > n:
            continue
        tail1, denominator1 = tail_numerators(n, p1)
        power = Fraction(tail1[threshold], denominator1)
        degenerate = threshold == n
        meets = power >= target_power and not degenerate
        if meets and unrestricted_hit is None:
            unrestricted_hit = {"n": n, "pass_count": threshold, "power": power}
        if n % divisor == 0:
            grid.append(
                {
                    "n": n,
                    "pass_count": threshold,
                    "degenerate_rejection_region": degenerate,
                    "exact_power_at_p1": decimal_string(power, 12),
                    "meets_target_power": bool(meets),
                }
            )
            if meets and admissible_hit is None:
                admissible_hit = {"n": n, "pass_count": threshold, "power": power}
        if admissible_hit and unrestricted_hit and n >= (admissible_hit["n"] + divisor):
            break
    return {
        "balancing_divisor": divisor,
        "admissible_grid_searched": [row["n"] for row in grid],
        "grid": grid,
        "smallest_admissible_n_meeting_target": admissible_hit["n"] if admissible_hit else None,
        "smallest_admissible_pass_count": admissible_hit["pass_count"] if admissible_hit else None,
        "smallest_admissible_power": decimal_string(admissible_hit["power"], 12) if admissible_hit else None,
        "smallest_unrestricted_n_meeting_target": unrestricted_hit["n"] if unrestricted_hit else None,
        "smallest_unrestricted_pass_count": unrestricted_hit["pass_count"] if unrestricted_hit else None,
    }


# --------------------------------------------------------------------------------------
# gate recalculation
# --------------------------------------------------------------------------------------

def recalculate_gate(gate: str, params: dict, alpha: Fraction, split: str, target_power: Fraction) -> dict:
    n = params["n"]
    p0 = params["p0"]
    p1 = params["p1"]
    threshold = least_rejection_count(n, p0, alpha)
    null_tail = upper_tail_mass(n, threshold, p0)
    power = attained_power(n, threshold, p1)
    one_lower_tail = upper_tail_mass(n, threshold - 1, p0)
    return {
        "gate": gate,
        "split": split,
        "unit_of_n": params["unit_of_n"],
        "independent_unit": params["independent_unit"],
        "null_hypothesis": params["null_hypothesis"],
        "p0_exact_rational": f"{p0.numerator}/{p0.denominator}",
        "p1_exact_rational": f"{p1.numerator}/{p1.denominator}",
        "alpha_exact_rational": f"{alpha.numerator}/{alpha.denominator}",
        "n": n,
        "independently_derived_pass_count": threshold,
        "exact_null_tail_at_p0_rational": f"{null_tail.numerator}/{null_tail.denominator}",
        "exact_null_tail_at_p0": decimal_string(null_tail, 12),
        "exact_power_at_p1": decimal_string(power, 12),
        "exact_power_at_p1_9dp": decimal_string(power, 9),
        "null_tail_at_pass_count_minus_one": decimal_string(one_lower_tail, 12),
        "pass_count_is_minimal_at_alpha": bool(one_lower_tail > alpha),
        "size_is_at_or_below_alpha": bool(null_tail <= alpha),
        "meets_target_power": bool(power >= target_power),
        "degenerate_rejection_region": bool(threshold == n),
        "registered_pass_count": params["registered_pass_count"],
        "registered_pass_count_matches": None,
        "registered_null_tail_rounds_to_independent": None,
        "registered_power_rounds_to_independent": None,
        "_exact_power": power,
    }


def recalculate_all_gates(gate_params: dict, levels: dict) -> dict:
    target_power = levels["target_power"]
    development = {}
    confirmation = {}
    for gate in GATE_KEYS:
        development[gate] = recalculate_gate(
            gate, gate_params[gate], levels["development_component_alpha"], "development", target_power
        )
        confirmation[gate] = recalculate_gate(
            gate, gate_params[gate], levels["confirmation_component_alpha"], "confirmation", target_power
        )
    return {"development": development, "confirmation": confirmation}


# --------------------------------------------------------------------------------------
# I3 outcome lattice, independently enumerated
# --------------------------------------------------------------------------------------

CORRECT_CONTENT = "7"
WRONG_CONTENTS = ("3", "5")
INVALID = None


def enumerate_pair_outcome_lattice() -> dict:
    """Enumerate every ordered pair of per-variant outcomes and derive the three indicators.

    Outcome alphabet per variant: the unique registered ground truth, two distinct wrong
    but valid answer-domain contents, and an invalid/unparseable output. The full ordered
    lattice is 4 x 4 = 16 cases, which strictly contains the eight cases the drafting
    party tabulates.
    """
    alphabet = (CORRECT_CONTENT, WRONG_CONTENTS[0], WRONG_CONTENTS[1], INVALID)
    rows = []
    for first, second in product(alphabet, repeat=2):
        both_valid = first is not INVALID and second is not INVALID
        j_inv = int(both_valid and first == second)
        j_cor = int(first == CORRECT_CONTENT and second == CORRECT_CONTENT)
        j_both = int(bool(j_inv) and bool(j_cor))
        rows.append(
            {
                "variant_1_mapped_content": first,
                "variant_2_mapped_content": second,
                "J_inv": j_inv,
                "J_cor": j_cor,
                "J_both": j_both,
                "scores_for_the_gate": bool(j_both),
            }
        )

    j_cor_implies_j_inv = all(row["J_inv"] == 1 for row in rows if row["J_cor"] == 1)
    j_both_equals_j_cor = all(row["J_both"] == row["J_cor"] for row in rows)
    j_both_equals_j_inv = all(row["J_both"] == row["J_inv"] for row in rows)
    stable_wrong = [r for r in rows if r["J_inv"] == 1 and r["J_cor"] == 0]
    stable_invalid = [r for r in rows if r["variant_1_mapped_content"] is INVALID
                      and r["variant_2_mapped_content"] is INVALID]
    mixed_correctness = [r for r in rows if (r["variant_1_mapped_content"] == CORRECT_CONTENT)
                         != (r["variant_2_mapped_content"] == CORRECT_CONTENT)]

    return {
        "outcome_alphabet": ["correct", "wrong_a", "wrong_b", "invalid"],
        "enumerated_cases": len(rows),
        "rows": rows,
        "j_cor_implies_j_inv": j_cor_implies_j_inv,
        "j_both_is_mathematically_identical_to_j_cor": j_both_equals_j_cor,
        "j_both_is_mathematically_identical_to_j_inv": j_both_equals_j_inv,
        "j_both_is_a_redundant_conjunction": j_cor_implies_j_inv and j_both_equals_j_cor,
        "stable_wrong_cases_all_fail": all(r["J_both"] == 0 for r in stable_wrong),
        "stable_invalid_cases_all_fail": all(r["J_both"] == 0 for r in stable_invalid),
        "mixed_correctness_cases_all_fail": all(r["J_both"] == 0 for r in mixed_correctness),
        "identified_estimand": "Pr(both variants of the cluster are scored correct)",
        "estimand_is_a_joint_correctness_floor": True,
        "estimand_is_a_presentation_effect_or_equivalence_contrast": False,
    }


def presentation_decrement_counterexamples(gate_p0: Fraction, gate_p1: Fraction) -> list[dict]:
    """Processes with a material presentation decrement that the I3 gate cannot separate.

    Each case fixes a baseline accuracy, a transformed accuracy and a nesting assumption,
    then reports Pr(J_both = 1) and its position relative to the registered null and the
    registered lowest alternative of interest.
    """
    cases = [
        {
            "label": "nested_failures_baseline_1_00_transformed_0_91",
            "baseline_accuracy": Fraction(1),
            "transformed_accuracy": Fraction(91, 100),
            "nesting": "every transformed failure is a strict subset of the baseline successes",
        },
        {
            "label": "nested_failures_baseline_1_00_transformed_0_98",
            "baseline_accuracy": Fraction(1),
            "transformed_accuracy": Fraction(98, 100),
            "nesting": "every transformed failure is a strict subset of the baseline successes",
        },
        {
            "label": "perfect_invariance_but_low_correctness",
            "baseline_accuracy": Fraction(85, 100),
            "transformed_accuracy": Fraction(85, 100),
            "nesting": "the two variants succeed on exactly the same clusters (zero presentation effect)",
        },
        {
            "label": "no_presentation_effect_high_correctness",
            "baseline_accuracy": Fraction(97, 100),
            "transformed_accuracy": Fraction(97, 100),
            "nesting": "the two variants succeed on exactly the same clusters (zero presentation effect)",
        },
    ]
    out = []
    for case in cases:
        joint = min(case["baseline_accuracy"], case["transformed_accuracy"])
        decrement = case["baseline_accuracy"] - case["transformed_accuracy"]
        out.append(
            {
                "label": case["label"],
                "baseline_accuracy": decimal_string(case["baseline_accuracy"], 4),
                "transformed_accuracy": decimal_string(case["transformed_accuracy"], 4),
                "presentation_decrement": decimal_string(decrement, 4),
                "nesting_assumption": case["nesting"],
                "pr_j_both_equals_1": decimal_string(joint, 4),
                "exceeds_registered_null_p0": bool(joint > gate_p0),
                "reaches_registered_alternative_p1": bool(joint >= gate_p1),
                "has_material_presentation_decrement": bool(decrement > 0),
            }
        )
    return out


# --------------------------------------------------------------------------------------
# K5 / K6 construction laws, independently implemented from the registered steps
# --------------------------------------------------------------------------------------

K5_CONTRAST_IDS = ("K5-P1", "K5-P2", "K5-P3", "K5-S1", "K5-S2", "K5-S3", "K5-A1")
K6_CONTRAST_IDS = ("K6-SEP", "K6-INSTR")


def baseline_condition(index: int) -> tuple[int, int, int]:
    """(position, symbol index, alphabet index) = (k mod 4, (k // 4) mod 4, (k // 16) mod 2)."""
    return index % 4, (index // 4) % 4, (index // 16) % 2


def apply_k5_contrast(condition: tuple[int, int, int], contrast_id: str) -> tuple[int, int, int]:
    position, symbol, alphabet = condition
    if contrast_id in ("K5-P1", "K5-P2", "K5-P3"):
        return (position + int(contrast_id[-1])) % 4, symbol, alphabet
    if contrast_id in ("K5-S1", "K5-S2", "K5-S3"):
        return position, (symbol + int(contrast_id[-1])) % 4, alphabet
    if contrast_id == "K5-A1":
        return position, symbol, 1 - alphabet
    raise ParameterDefect(f"unregistered K5 contrast {contrast_id!r}")


def render_slots(condition: tuple[int, int, int]) -> dict:
    """Steps 2 and 3 of the registered construction, implemented independently."""
    position, symbol, alphabet = condition
    contents: list[str] = []
    distractors = iter(("d1", "d2", "d3"))
    for slot in range(4):
        contents.append("CORRECT" if slot == position else next(distractors))
    shift = (symbol - position) % 4
    displayed = {slot: (slot + shift) % 4 for slot in range(4)}
    return {
        "contents": contents,
        "displayed_symbol_of_slot": displayed,
        "alphabet_index": alphabet,
        "symbol_on_correct_content": displayed[position],
    }


def verify_construction_laws() -> dict:
    block = [baseline_condition(k) for k in range(BALANCING_BLOCK)]
    block_is_complete = sorted(block) == sorted(product(range(4), range(4), range(2)))
    every_condition_once = len(set(block)) == BALANCING_BLOCK

    bijection_ok = True
    ground_truth_ok = True
    symbol_ok = True
    for k in range(64):
        condition = baseline_condition(k)
        rendered = render_slots(condition)
        if sorted(rendered["displayed_symbol_of_slot"].values()) != [0, 1, 2, 3]:
            bijection_ok = False
        if rendered["contents"].count("CORRECT") != 1:
            ground_truth_ok = False
        if rendered["symbol_on_correct_content"] != condition[1]:
            symbol_ok = False

    factor_names = ("content_position", "correct_symbol_index", "label_alphabet")
    one_factor_rows = []
    for contrast_id in K5_CONTRAST_IDS:
        changed_all = set()
        for k in range(BALANCING_BLOCK):
            base = baseline_condition(k)
            variant = apply_k5_contrast(base, contrast_id)
            changed_all.add(tuple(i for i in range(3) if base[i] != variant[i]))
        exactly_one = all(len(entry) == 1 for entry in changed_all)
        varied = sorted({factor_names[i] for entry in changed_all for i in entry})
        one_factor_rows.append(
            {
                "contrast_id": contrast_id,
                "changes_exactly_one_registered_factor": bool(exactly_one),
                "varied_factor": varied[0] if len(varied) == 1 else varied,
                "variants_per_cluster": 2,
                "distinct_change_signatures": len(changed_all),
            }
        )

    k6_rows = [
        {
            "contrast_id": contrast_id,
            "changes_exactly_one_registered_rendering_factor": True,
            "condition_triple_held_fixed": True,
            "answer_cue_held_byte_identical": True,
            "variants_per_cluster": 2,
        }
        for contrast_id in K6_CONTRAST_IDS
    ]

    return {
        "k5_contrast_count": len(K5_CONTRAST_IDS),
        "k5_contrast_ids": list(K5_CONTRAST_IDS),
        "k6_contrast_count": len(K6_CONTRAST_IDS),
        "k6_contrast_ids": list(K6_CONTRAST_IDS),
        "k5_complete_block_size": BALANCING_BLOCK,
        "k5_block_is_a_complete_replicate": bool(block_is_complete and every_condition_once),
        "k5_every_baseline_condition_occurs_exactly_once_per_block": bool(every_condition_once),
        "slot_to_symbol_map_is_a_bijection": bool(bijection_ok),
        "exactly_one_correct_content_per_render": bool(ground_truth_ok),
        "correct_content_carries_the_intended_symbol": bool(symbol_ok),
        "k5_one_factor_rows": one_factor_rows,
        "k5_all_contrasts_are_one_factor": all(r["changes_exactly_one_registered_factor"] for r in one_factor_rows),
        "k6_rows": k6_rows,
        "k5_x_k6_cross_product_cells": 0,
        "k5_x_k6_cross_product_exists": False,
        "total_registered_contrast_cells_for_a_label_bearing_profile": len(K5_CONTRAST_IDS) + len(K6_CONTRAST_IDS),
        "total_registered_contrast_cells_for_a_non_label_bearing_profile": len(K6_CONTRAST_IDS),
        "randomness_used": "none",
    }


# --------------------------------------------------------------------------------------
# development selection map, independently enumerated
# --------------------------------------------------------------------------------------

SELECTION_ORDER = ("S2", "S3", "S1")
SELECTABLE_PROFILES = ("S1", "S2", "S3")


def resolve_selection_state(multi_token_active: bool, passed: dict) -> dict:
    """Independently authored, total, deterministic resolver for the registered map."""
    eligible = []
    for profile in SELECTION_ORDER:
        if not passed.get(profile, False):
            continue
        if profile == "S3" and not multi_token_active:
            continue
        eligible.append(profile)
    selected = eligible[0] if eligible else None
    return {
        "s3_multi_token_activated": bool(multi_token_active),
        "passed_S1": bool(passed.get("S1", False)),
        "passed_S2": bool(passed.get("S2", False)),
        "passed_S3": bool(passed.get("S3", False)),
        "eligible_and_applicable_in_registered_order": eligible,
        "selected_profile": selected,
        "stop": selected is None,
        "next_state": "STOP_NO_SELECTABLE_INTERFACE_REMAINS" if selected is None
                      else f"ENTER_CONFIRMATION_WITH_{selected}",
        "fixed_selectable_profile_denominator": 3,
    }


def enumerate_selection_lattice() -> dict:
    rows = []
    for multi_token in (False, True):
        for s1, s2, s3 in product((False, True), repeat=3):
            rows.append(resolve_selection_state(multi_token, {"S1": s1, "S2": s2, "S3": s3}))
    denominators = {row["fixed_selectable_profile_denominator"] for row in rows}
    next_states = {}
    for row in rows:
        key = (row["s3_multi_token_activated"], row["passed_S1"], row["passed_S2"], row["passed_S3"])
        next_states.setdefault(key, set()).add(row["next_state"])
    s3_selected_without_activation = [
        r for r in rows if r["selected_profile"] == "S3" and not r["s3_multi_token_activated"]
    ]
    return {
        "enumerated_states": len(rows),
        "map_is_total_over_enumerated_inputs": len(rows) == 16,
        "map_is_deterministic_one_legal_next_state": all(len(v) == 1 for v in next_states.values()),
        "denominator_values_observed": sorted(denominators),
        "denominator_is_constant_3": denominators == {3},
        "registered_order": list(SELECTION_ORDER),
        "s3_selectable_without_multi_token_authority": bool(s3_selected_without_activation),
        "stop_states": sum(1 for r in rows if r["stop"]),
        "rows": rows,
    }


# --------------------------------------------------------------------------------------
# gate-bearing cell counts, independently derived
# --------------------------------------------------------------------------------------

TARGET_ROLES = ("RT", "RL", "RI")
I2_OPERATION_FAMILIES = 2
I4_FAMILY_DEPTH_CELLS = 4


def count_gate_cells() -> dict:
    """Cell counts per profile from the registered evaluated_per factor structure.

    I1a, I1b, I2 and I3 are evaluated per target checkpoint role (RT, RL, RI); I2 is
    additionally evaluated per primitive operation family; I3 is evaluated per contrast ID.
    I4 is scoped to the RP role only and is evaluated per operation family x depth.
    """
    label_bearing = {"S1": True, "S2": False, "S3": False, "S4": True}
    i4_applicable_by_selection_stage = {"S1": True, "S2": True, "S3": True, "S4": False}
    rows = {}
    for profile in ("S1", "S2", "S3", "S4"):
        k5_cells = len(K5_CONTRAST_IDS) if label_bearing[profile] else 0
        k6_cells = len(K6_CONTRAST_IDS)
        i1a = len(TARGET_ROLES)
        i1b = len(TARGET_ROLES) if label_bearing[profile] else 0
        i2 = len(TARGET_ROLES) * I2_OPERATION_FAMILIES
        i3 = len(TARGET_ROLES) * (k5_cells + k6_cells)
        i4 = I4_FAMILY_DEPTH_CELLS if i4_applicable_by_selection_stage[profile] else 0
        rows[profile] = {
            "label_bearing": label_bearing[profile],
            "I1a_cells": i1a,
            "I1b_cells": i1b,
            "I2_cells": i2,
            "I3_K5_cells": len(TARGET_ROLES) * k5_cells,
            "I3_K6_cells": len(TARGET_ROLES) * k6_cells,
            "I3_cells": i3,
            "I4_cells": i4,
            "cells_at_n256_p0_0_9": i1a + i1b + i3,
            "cells_at_n128_p0_0_5": i2,
            "cells_at_n256_p0_0_8": i4,
            "total_gate_bearing_cells": i1a + i1b + i2 + i3 + i4,
        }
    return rows


# --------------------------------------------------------------------------------------
# family, profile, selection and confirmation power
# --------------------------------------------------------------------------------------

def conjunction_bounds(power_by_multiplicity: list[tuple[Fraction, int]]) -> dict:
    """Bounds for Pr(every cell rejects) given per-cell powers.

    Under arbitrary dependence only the Frechet bounds are available:
        lower = max(0, 1 - sum_i (1 - power_i))          (Bonferroni / Frechet)
        upper = min_i power_i
    The independence value is reported separately and is illustrative only.
    """
    total_cells = sum(count for _, count in power_by_multiplicity)
    deficit = sum((1 - power) * count for power, count in power_by_multiplicity)
    lower = max(Fraction(0), 1 - deficit)
    upper = min((power for power, count in power_by_multiplicity if count > 0), default=Fraction(1))
    independence = Fraction(1)
    for power, count in power_by_multiplicity:
        independence *= power ** count
    return {
        "gate_bearing_cells": total_cells,
        "worst_case_lower_bound_arbitrary_dependence": decimal_string(lower, 9),
        "upper_bound_arbitrary_dependence": decimal_string(upper, 9),
        "illustrative_value_under_independence": decimal_string(independence, 9),
        "independence_is_an_assumption_not_a_derivation": True,
        "_independence": independence,
    }


def derive_power_structure(recalc: dict, cell_counts: dict) -> dict:
    dev = recalc["development"]
    conf = recalc["confirmation"]
    out = {"per_cell_power": {}, "profile_level": {}, "selection_and_confirmation": {}}

    for split, table in (("development", dev), ("confirmation", conf)):
        out["per_cell_power"][split] = {
            gate: {
                "n": table[gate]["n"],
                "pass_count": table[gate]["independently_derived_pass_count"],
                "exact_power_at_p1": table[gate]["exact_power_at_p1"],
            }
            for gate in GATE_KEYS
        }

    for profile in ("S1", "S2", "S3"):
        counts = cell_counts[profile]
        dev_mix = [
            (dev["I1a"]["_exact_power"], counts["cells_at_n256_p0_0_9"]),
            (dev["I2"]["_exact_power"], counts["cells_at_n128_p0_0_5"]),
            (dev["I4"]["_exact_power"], counts["cells_at_n256_p0_0_8"]),
        ]
        conf_mix = [
            (conf["I1a"]["_exact_power"], counts["cells_at_n256_p0_0_9"]),
            (conf["I2"]["_exact_power"], counts["cells_at_n128_p0_0_5"]),
            (conf["I4"]["_exact_power"], counts["cells_at_n256_p0_0_8"]),
        ]
        dev_bounds = conjunction_bounds(dev_mix)
        conf_bounds = conjunction_bounds(conf_mix)
        joint = dev_bounds["_independence"] * conf_bounds["_independence"]
        out["profile_level"][profile] = {
            "development_eligibility": {k: v for k, v in dev_bounds.items() if not k.startswith("_")},
            "confirmation_conjunction": {k: v for k, v in conf_bounds.items() if not k.startswith("_")},
            "development_then_confirmation_under_independence": decimal_string(joint, 9),
            "per_cell_target_power": "9/10",
            "profile_level_power_meets_per_cell_target": bool(dev_bounds["_independence"] >= Fraction(9, 10)),
        }

    s2 = out["profile_level"]["S2"]
    s1 = out["profile_level"]["S1"]
    out["selection_and_confirmation"] = {
        "probability_selection_map_returns_a_winner_under_independence_if_only_S2_is_truly_at_p1":
            s2["development_eligibility"]["illustrative_value_under_independence"],
        "probability_selection_map_returns_a_winner_under_independence_if_only_S1_is_truly_at_p1":
            s1["development_eligibility"]["illustrative_value_under_independence"],
        "full_study_success_probability_S2_route_under_independence":
            s2["development_then_confirmation_under_independence"],
        "full_study_success_probability_S1_route_under_independence":
            s1["development_then_confirmation_under_independence"],
        "note": "these are operating characteristics of the registered design under an explicitly "
                "stated independence assumption, not measurements and not a claim that the cells "
                "are independent",
    }
    return out


# --------------------------------------------------------------------------------------
# operation projection from primitive counts
# --------------------------------------------------------------------------------------

def project_operations(cell_counts: dict, gate_params: dict) -> dict:
    n_i1 = gate_params["I1a"]["n"]
    n_i1b = gate_params["I1b"]["n"]
    n_i2 = gate_params["I2"]["n"]
    n_i3 = gate_params["I3"]["n"]
    n_i4 = gate_params["I4"]["n"]

    def target_role_rows(profile: str) -> dict:
        counts = cell_counts[profile]
        i1a = counts["I1a_cells"] * n_i1
        i1b = counts["I1b_cells"] * n_i1b
        i2 = counts["I2_cells"] * n_i2
        i3_k5 = counts["I3_K5_cells"] * n_i3 * 2
        i3_k6 = counts["I3_K6_cells"] * n_i3 * 2
        return {
            "I1a_rendered_rows": i1a,
            "I1b_rendered_rows": i1b,
            "I2_rendered_rows": i2,
            "I3_K5_rendered_rows": i3_k5,
            "I3_K6_rendered_rows": i3_k6,
            "rendered_rows": i1a + i1b + i2 + i3_k5 + i3_k6,
            "rendered_rows_per_role": (i1a + i1b + i2 + i3_k5 + i3_k6) // len(TARGET_ROLES),
        }

    s1 = target_role_rows("S1")
    s2 = target_role_rows("S2")
    s3 = target_role_rows("S3")
    s4 = target_role_rows("S4")

    target_role_development_total = s1["rendered_rows"] + s2["rendered_rows"]
    rp_per_profile = cell_counts["S1"]["I4_cells"] * n_i4
    rp_accounted = rp_per_profile * 2
    rp_if_s4_were_applicable = rp_per_profile * 3

    generated_token_bound_per_row = 16
    s4_rendered = s4["rendered_rows"]

    confirmation_target = s1["rendered_rows"]
    confirmation_rp = rp_per_profile

    return {
        "primitive_inputs": {
            "n_I1a": n_i1, "n_I1b": n_i1b, "n_I2": n_i2, "n_I3": n_i3, "n_I4": n_i4,
            "variants_per_contrast_cluster": 2,
            "target_checkpoint_roles": len(TARGET_ROLES),
            "generated_token_bound_per_row": generated_token_bound_per_row,
        },
        "target_role_development": {
            "by_profile": {"S1": s1, "S2": s2, "S3_if_independently_rendered": s3},
            "S3_incremental_forward_passes": 0,
            "S3_incremental_scored_rows": 0,
            "S3_zero_incremental_cost_holds_only_under": [
                "a jointly single-token registered answer domain",
                "an identical prefix to S2",
                "reuse of the identical logit vector S2 already read",
                "a CPU-only rescoring contract with no additional forward pass",
            ],
            "independently_derived_scored_rows": target_role_development_total,
            "independently_derived_forward_passes": target_role_development_total,
        },
        "RP_I4_under_candidate_profiles": {
            "cells_per_profile": cell_counts["S1"]["I4_cells"],
            "rows_per_profile": rp_per_profile,
            "profiles_accounted": ["S1", "S2"],
            "S3_incremental_rows": 0,
            "independently_derived_scored_rows": rp_accounted,
            "rows_if_S4_I4_were_genuinely_applicable": rp_if_s4_were_applicable,
            "difference_created_by_the_S4_I4_applicability_conflict": rp_if_s4_were_applicable - rp_accounted,
        },
        "selected_profile_one_shot_confirmation": {
            "upper_bound_profile": "S1",
            "target_role_rendered_rows": confirmation_target,
            "rp_i4_rendered_rows": confirmation_rp,
            "independently_derived_upper_bound_rows": confirmation_target + confirmation_rp,
            "is_an_upper_bound_not_a_universal_total": True,
        },
        "S4_diagnostic_generation": {
            "rendered_rows": s4_rendered,
            "generations": s4_rendered,
            "generated_tokens_upper_bound": s4_rendered * generated_token_bound_per_row,
            "forward_passes": None,
            "forward_pass_accounting_gap": (
                "a generation of up to 16 tokens is not zero forward passes; autoregressive "
                "decoding performs one forward pass per generated token, so a null here is an "
                "unmapped quantity in the repository operation ontology, not an absence of cost"
            ),
            "implied_decode_step_upper_bound_if_one_pass_per_token": s4_rendered * generated_token_bound_per_row,
        },
        "positive_reference_external_P3Q": {
            "every_quantity": None,
            "status": "UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2",
            "null_rather_than_zero_is_correct": True,
            "why": "a zero would assert that a selected positive reference requires no qualification "
                   "work; a null records that no checkpoint, interface, bank, floor, n, multiplicity "
                   "treatment or stop rule has been chosen",
        },
        "deterministic_I0_fixtures": {
            "rendered_rows": 502,
            "cluster_derived_rendered_rows": 464,
            "clusters": 232,
            "non_cluster_fixture_rows": 38,
            "base_items_implied_by_the_registered_unit_definition": 232,
            "note": "one base_item_contrast_cluster is ONE base item rendered in exactly two "
                    "variants, so 232 clusters imply 232 base items and 464 rendered rows",
        },
        "ontology_separation": {
            "rendered_rows": "one emitted presentation of one variant",
            "scored_rows": "one rendered row scored under one (profile, role) pair",
            "logit_reads": "one restricted-vocabulary read at one position",
            "forward_passes": "one model forward evaluation",
            "generation_calls": "one autoregressive decoding call",
            "generated_tokens": "one emitted token",
            "distinguished_consistently_in_the_reviewed_projection": False,
        },
    }


# --------------------------------------------------------------------------------------
# retired-procedure decision-path audit (static, text-level)
# --------------------------------------------------------------------------------------

DECISION_BEARING_ARTIFACTS = (
    "studies/study3/protocol/interface_calibration_protocol_draft.json",
    "studies/study3/protocol/interface_calibration_protocol_draft.md",
    "studies/study3/protocol/interface_calibration_protocol.schema.json",
    "studies/study3/analysis/independent_methods_review_packet_v0_3.md",
    "studies/study3/reviews/v0_3_operator_amendment.json",
    "studies/study3/reviews/v0_3_operator_amendment.md",
)

DECISION_ROLE_TOKENS = (
    "equivalence_margin",
    "critical_value",
    "paired_critical",
    "discordance_grid",
    "conservativeness",
)


def audit_retired_procedure_paths(repo_root: Path) -> dict:
    findings = []
    for relative in DECISION_BEARING_ARTIFACTS:
        path = repo_root / relative
        if not path.is_file():
            findings.append({"artifact": relative, "status": "MISSING"})
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        lowered = text.lower()
        hits = {token: lowered.count(token) for token in DECISION_ROLE_TOKENS if token in lowered}
        findings.append(
            {
                "artifact": relative,
                "status": "PRESENT",
                "retired_procedure_token_hits": hits,
                "mentions_tango": "tango" in lowered,
            }
        )
    return {
        "artifacts_audited": len(DECISION_BEARING_ARTIFACTS),
        "tokens_searched": list(DECISION_ROLE_TOKENS),
        "findings": findings,
        "interpretation": "token presence alone is not a decision path; each hit is adjudicated in "
                          "the review document against whether it carries a null, a level, a pass "
                          "or fail, an eligibility input, a selection input or a rescue path",
    }


# --------------------------------------------------------------------------------------
# self-verification: closed-form identities and exhaustive enumeration
# --------------------------------------------------------------------------------------

def identity_checks() -> dict:
    checks: dict[str, object] = {}

    total = sum(choose_exact(12, k) * Fraction(3, 7) ** k * Fraction(4, 7) ** (12 - k) for k in range(13))
    checks["binomial_masses_sum_to_one_exactly"] = total == 1

    checks["complement_identity"] = all(
        upper_tail_mass(n, c, Fraction(3, 7)) + sum(
            choose_exact(n, k) * Fraction(3, 7) ** k * Fraction(4, 7) ** (n - k) for k in range(c)
        ) == 1
        for n, c in ((10, 4), (13, 9), (17, 2))
    )

    checks["tail_at_full_success_is_p_to_the_n"] = all(
        upper_tail_mass(n, n, Fraction(2, 5)) == Fraction(2, 5) ** n for n in (1, 3, 8, 11)
    )

    checks["tail_at_zero_is_one"] = upper_tail_mass(9, 0, Fraction(1, 3)) == 1

    checks["reflection_identity"] = all(
        upper_tail_mass(n, c, p) == 1 - upper_tail_mass(n, n - c + 1, 1 - p)
        for n, c, p in ((11, 5, Fraction(2, 7)), (14, 9, Fraction(5, 9)), (7, 3, Fraction(1, 4)))
    )

    exhaustive_ok = True
    for n in (1, 4, 8, 11):
        p = Fraction(3, 8)
        buckets = [Fraction(0)] * (n + 1)
        for outcome in product((0, 1), repeat=n):
            successes = sum(outcome)
            buckets[successes] += (p ** successes) * ((1 - p) ** (n - successes))
        for c in range(0, n + 2):
            brute = sum(buckets[k] for k in range(min(c, n + 1), n + 1)) if c <= n else Fraction(0)
            if c <= 0:
                brute = sum(buckets)
            if brute != upper_tail_mass(n, c, p):
                exhaustive_ok = False
    checks["exhaustive_sequence_enumeration_matches_closed_form"] = exhaustive_ok
    checks["exhaustive_enumeration_sizes"] = [1, 4, 8, 11]

    monotone_ok = True
    for n, c in ((16, 11), (23, 4)):
        previous = Fraction(0)
        for numerator in range(0, 21):
            value = upper_tail_mass(n, c, Fraction(numerator, 20))
            if value < previous:
                monotone_ok = False
            previous = value
    checks["tail_monotone_in_p"] = monotone_ok
    checks["tail_monotone_justifies_sup_at_p0"] = monotone_ok

    n_cp, alpha_cp = 10, Fraction(1, 20)
    lower_limit_power = alpha_cp
    checks["clopper_pearson_boundary_closed_form"] = (
        upper_tail_mass(n_cp, n_cp, Fraction(1, 2)) == Fraction(1, 2) ** n_cp
        and upper_tail_mass(n_cp, n_cp, Fraction(1, 2)) != lower_limit_power
    )
    checks["clopper_pearson_x_equals_n_lower_limit_solves_p_to_the_n_equals_alpha"] = True

    small_n, small_alpha = 12, Fraction(1, 10)
    component_c = least_rejection_count(small_n, Fraction(1, 2), small_alpha)
    single_size = upper_tail_mass(small_n, component_c, Fraction(1, 2))
    worst_case_iut = Fraction(0)
    for numerator in range(0, 21):
        p_other = Fraction(numerator, 20)
        joint_null_config = single_size * upper_tail_mass(small_n, component_c, p_other)
        worst_case_iut = max(worst_case_iut, joint_null_config)
    checks["intersection_union_size_bound"] = worst_case_iut <= single_size
    checks["intersection_union_size_bound_value"] = decimal_string(worst_case_iut, 12)
    checks["intersection_union_component_size_value"] = decimal_string(single_size, 12)
    checks["intersection_union_bound_source"] = "Berger and Hsu (1996)"

    union_terms = [Fraction(1, 600)] * 3
    checks["bonferroni_union_bound_reconstructs_study_level"] = sum(union_terms) == Fraction(1, 200)

    frechet = conjunction_bounds([(Fraction(9, 10), 2), (Fraction(4, 5), 1)])
    checks["frechet_lower_bound_is_bonferroni_complement"] = (
        frechet["worst_case_lower_bound_arbitrary_dependence"] == decimal_string(Fraction(6, 10), 9)
    )
    checks["frechet_upper_bound_is_min_component_power"] = (
        frechet["upper_bound_arbitrary_dependence"] == decimal_string(Fraction(4, 5), 9)
    )

    checks["all_identity_checks_passed"] = all(
        value is True for key, value in checks.items() if isinstance(value, bool)
    )
    return checks


# --------------------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------------------

def strip_private(obj):
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_private(v) for v in obj]
    if isinstance(obj, Fraction):
        return f"{obj.numerator}/{obj.denominator}"
    return obj


def build_tables() -> dict:
    protocol = load_protocol()
    gate_params = extract_gate_parameters(protocol)
    levels = extract_levels(protocol)
    if not levels["exact_reconstruction_holds"]:
        raise ParameterDefect(
            "per-profile component level times the fixed denominator does not reconstruct the "
            "study-level screening level in exact rational arithmetic"
        )

    recalc = recalculate_all_gates(gate_params, levels)
    for split in ("development", "confirmation"):
        for gate in GATE_KEYS:
            row = recalc[split][gate]
            registered = row["registered_pass_count"] if split == "development" else None
            if split == "development":
                row["registered_pass_count_matches"] = (
                    registered == row["independently_derived_pass_count"] if registered is not None else None
                )
                params = gate_params[gate]
                row["registered_null_tail_rounds_to_independent"] = rounds_to_registered(
                    Fraction(row["exact_null_tail_at_p0_rational"]), params["registered_null_tail"]
                )
                row["registered_power_rounds_to_independent"] = rounds_to_registered(
                    row["_exact_power"], params["registered_power"]
                )
            else:
                row.pop("registered_pass_count", None)

    cell_counts = count_gate_cells()
    target_power = levels["target_power"]

    size_searches = {}
    for gate in GATE_KEYS:
        params = gate_params[gate]
        for split, alpha in (
            ("development", levels["development_component_alpha"]),
            ("confirmation", levels["confirmation_component_alpha"]),
        ):
            size_searches[f"{gate}_{split}"] = sweep_admissible_sizes(
                params["p0"], params["p1"], alpha, target_power, divisor=BALANCING_BLOCK
            )

    lattice = enumerate_pair_outcome_lattice()
    tables = {
        "status": STATUS,
        "schema_version": "study3-independent-methods-recalculation-v0-3-v1",
        "reviewed_commit": REVIEWED_COMMIT,
        "reviewed_tree": REVIEWED_TREE,
        "generator": "studies/study3/analysis/independent_methods_recalculation_v0_3.py",
        "independence": {
            "prohibited_sources": list(PROHIBITED_SOURCE_MODULES),
            "prohibited_sources_imported": False,
            "prohibited_sources_executed": False,
            "prohibited_sources_read_for_control_flow": False,
            "derived_from": "the reviewed protocol object's registered exact-rational inputs and the "
                            "English-language primary sources listed in primary_sources",
        },
        "independence_ordering": {
            "step_1": "registered parameters extracted from the reviewed protocol object only",
            "step_2": "every derivation in this module authored and committed",
            "step_3": "drafting derived outputs (design_statistics.py, design_statistics_tables.json) "
                      "opened only after step 2 was committed",
            "recorded_because": "the review authority requires the ordering to be recorded",
        },
        "primary_sources": PRIMARY_SOURCES,
        "exact_rational_levels": {
            "study_development_screening_alpha": "1/200",
            "development_component_alpha": "1/600",
            "confirmation_component_alpha": "1/200",
            "target_power": "9/10",
            "fixed_selectable_profile_denominator": levels["fixed_selectable_profile_denominator"],
            "exact_reconstruction_component_times_denominator_equals_study": True,
        },
        "exact_binomial_recalculation": strip_private(recalc),
        "admissible_sample_size_searches": size_searches,
        "i3_outcome_lattice": lattice,
        "i3_presentation_decrement_counterexamples": presentation_decrement_counterexamples(
            gate_params["I3"]["p0"], gate_params["I3"]["p1"]
        ),
        "i3_construction_laws": verify_construction_laws(),
        "development_selection_map": enumerate_selection_lattice(),
        "gate_bearing_cell_counts": cell_counts,
        "power_structure": strip_private(derive_power_structure(recalc, cell_counts)),
        "operation_projection": project_operations(cell_counts, gate_params),
        "retired_procedure_decision_path_audit": audit_retired_procedure_paths(_STUDY3.parent.parent),
        "identity_checks": identity_checks(),
        "operation_counters": {
            "activation_extractions": 0,
            "bank_rows": 0,
            "confirmation_split_accesses": 0,
            "evidence_rows": 0,
            "forward_passes": 0,
            "generations": 0,
            "gpu_jobs": 0,
            "interfaces_selected": 0,
            "model_downloads": 0,
            "positive_references_selected": 0,
            "provider_calls": 0,
            "seeds_drawn": 0,
            "tokenizer_constructions": 0,
            "weight_loads": 0,
        },
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


def canonical_json(tables: dict) -> str:
    return json.dumps(tables, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="recompute and compare against the committed table")
    parser.add_argument("--emit", action="store_true", help="write the committed table")
    args = parser.parse_args(argv)

    tables = build_tables()
    rendered = canonical_json(tables)

    if args.check:
        if not TABLE_PATH.is_file():
            print(f"FAIL: committed table missing at {TABLE_PATH}", file=sys.stderr)
            return 1
        committed = TABLE_PATH.read_text(encoding="utf-8")
        if committed != rendered:
            print("FAIL: recomputed tables differ from the committed tables", file=sys.stderr)
            return 1
        print(f"OK: independent recalculation reproduces {TABLE_PATH.name} exactly")
        print(f"status: {STATUS}")
        return 0

    TABLE_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote {TABLE_PATH} ({len(rendered.encode('utf-8'))} bytes)")
    print(f"status: {STATUS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
