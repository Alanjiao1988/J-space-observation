"""Study 3R production design statistics.

Authority: ``studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md``

This module independently enumerates the Study 3R gate-bearing atomic-cell
census from the registered factor levels, derives ``m_max`` from that census,
and closes every registered gate with **exact integer binomial arithmetic**.

No normal approximation, no floating-point comparison and no inherited sample
size, threshold or alpha allocation is used anywhere. Every probability is
carried as an exact rational ``numerator / denominator`` pair and every
comparison is an integer cross-multiplication.

The independent recalculation in ``study3r_independent_recalculation.py``
imports nothing from this module.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from decimal import Decimal, getcontext
from math import gcd

getcontext().prec = 60

ROOT = pathlib.Path(__file__).resolve().parents[3]
ANALYSIS_DIR = ROOT / "studies" / "study3r" / "analysis"

# ---------------------------------------------------------------------------
# Registered factor levels
# ---------------------------------------------------------------------------

#: Checkpoint roles, in registered order. ``RT`` is the sole target checkpoint;
#: ``RP_B1..RP_B3`` are the fixed, ordered natural positive-reference ladder.
CHECKPOINT_ROLES = ("RT", "RP_B1", "RP_B2", "RP_B3")
RP_B_ROLES = ("RP_B1", "RP_B2", "RP_B3")
RT_ROLES = ("RT",)
LADDER_LENGTH = len(RP_B_ROLES)

#: The two matched E0 wrapper arms. Both enter the census and the multiplicity
#: calculation.
E0_ARMS = ("W1_RAW_DIRECT", "W2_ROLE_CANONICAL")

#: The generated-CoT ceiling route. It is a separate canonical route, never an
#: E0 arm and never an interface selector.
COT_ROUTE = ("C1_CANONICAL_GENERATED_COT",)

#: Global one-sided error budget.
ALPHA_GLOBAL = (1, 20)

#: Per-cell power target.
POWER_TARGET = (9, 10)

#: Offset applied to the derived integer pass boundary. Registered as zero: the
#: boundary is exactly the minimal (or maximal) integer that satisfies the
#: registered size constraint, with no slack in either direction.
PASS_BOUNDARY_OFFSET = 0

#: Chance level of the four-label answer domain.
CHANCE_LEVEL = (1, 4)

#: The single registered multiplicity family.
MULTIPLICITY_FAMILY = "F_GLOBAL_STUDY3R"

#: The single registered RP-B qualification decision identifier. It names one
#: construct and is never reused.
RPB_DECISION_ID = "Q0_RPB_QUALIFICATION_DECISION"

SUPERIORITY = "greater_than_floor"
UPPER_BOUND = "less_than_upper_margin"

#: Every gate-bearing construct. ``roles`` and ``routes`` are the registered
#: factor levels whose cross product forms that gate's atomic cells.
GATE_SPECS = (
    {
        "gate_id": "G01_COT_CEILING",
        "title": "Generated-CoT ceiling",
        "estimand": "COT_generated_reasoning_ceiling",
        "phase": "precondition",
        "roles": CHECKPOINT_ROLES,
        "routes": COT_ROUTE,
        "task_family": "D2_D3_CEILING_BANK",
        "direction": SUPERIORITY,
        "floor": (3, 4),
        "alternative": (9, 10),
        "statistical_unit": "item",
        "terminal_on_failure": "T03_COT_CEILING_FAILED",
    },
    {
        "gate_id": "G02_CONTROL_RECOVERY",
        "title": "Trivial content-recovery competence control",
        "estimand": "E0_zero_generated_reasoning_token_expressed_competence",
        "phase": "control",
        "roles": CHECKPOINT_ROLES,
        "routes": E0_ARMS,
        "task_family": "REC",
        "direction": SUPERIORITY,
        "floor": (9, 10),
        "alternative": (99, 100),
        "statistical_unit": "item",
        "terminal_on_failure": "T04_COMPETENCE_CONTROL_FAILED",
    },
    {
        "gate_id": "G03_CONTROL_BINDING",
        "title": "Explicit answer-label binding control",
        "estimand": "E0_zero_generated_reasoning_token_expressed_competence",
        "phase": "control",
        "roles": CHECKPOINT_ROLES,
        "routes": E0_ARMS,
        "task_family": "BIND",
        "direction": SUPERIORITY,
        "floor": (9, 10),
        "alternative": (99, 100),
        "statistical_unit": "item",
        "terminal_on_failure": "T04_COMPETENCE_CONTROL_FAILED",
    },
    {
        "gate_id": "G04_CONTROL_PRIMITIVE",
        "title": "Single-primitive operation control",
        "estimand": "E0_zero_generated_reasoning_token_expressed_competence",
        "phase": "control",
        "roles": CHECKPOINT_ROLES,
        "routes": E0_ARMS,
        "task_family": "PRIM",
        "direction": SUPERIORITY,
        "floor": (9, 10),
        "alternative": (99, 100),
        "statistical_unit": "item",
        "terminal_on_failure": "T04_COMPETENCE_CONTROL_FAILED",
    },
    {
        "gate_id": "G05_NEGATIVE_CONTROL",
        "title": "Deliberately invalid negative control",
        "estimand": "E0_zero_generated_reasoning_token_expressed_competence",
        "phase": "control",
        "roles": CHECKPOINT_ROLES,
        "routes": E0_ARMS,
        "task_family": "NEG",
        "direction": UPPER_BOUND,
        "floor": (35, 100),
        "alternative": CHANCE_LEVEL,
        "statistical_unit": "item",
        "terminal_on_failure": "T05_NEGATIVE_CONTROL_FAILED",
    },
    {
        "gate_id": "G06_WRAPPER_JOINT_ADEQUACY",
        "title": "Two-wrapper joint adequacy",
        "estimand": "E0_zero_generated_reasoning_token_expressed_competence",
        "phase": "adequacy",
        "roles": CHECKPOINT_ROLES,
        "routes": E0_ARMS,
        "task_family": "D2_ADEQUACY_BANK",
        "direction": SUPERIORITY,
        "floor": (1, 2),
        "alternative": (3, 4),
        "statistical_unit": "item",
        "terminal_on_failure": "T06_WRAPPER_ADEQUACY_FAILED",
    },
    {
        "gate_id": "G07_RPB_DEVELOPMENT",
        "title": "RP-B ladder development evaluation",
        "estimand": "E0_zero_generated_reasoning_token_expressed_competence",
        "phase": "development",
        "roles": RP_B_ROLES,
        "routes": E0_ARMS,
        "task_family": "D2_D3_DEVELOPMENT_BANK",
        "direction": SUPERIORITY,
        "floor": (1, 2),
        "alternative": (3, 4),
        "statistical_unit": "item",
        "terminal_on_failure": "T07_NO_QUALIFIED_REFERENCE",
    },
    {
        "gate_id": "G08_RPB_CONFIRMATION",
        "title": "RP-B ladder item-disjoint confirmation evaluation",
        "estimand": "E0_zero_generated_reasoning_token_expressed_competence",
        "phase": "confirmation",
        "roles": RP_B_ROLES,
        "routes": E0_ARMS,
        "task_family": "D2_D3_CONFIRMATION_BANK",
        "direction": SUPERIORITY,
        "floor": (1, 2),
        "alternative": (3, 4),
        "statistical_unit": "item",
        "terminal_on_failure": "T07_NO_QUALIFIED_REFERENCE",
    },
    {
        "gate_id": "G09_RT_E0_QUALIFICATION",
        "title": "RT E0 behavioral qualification",
        "estimand": "E0_zero_generated_reasoning_token_expressed_competence",
        "phase": "target",
        "roles": RT_ROLES,
        "routes": E0_ARMS,
        "task_family": "D2_D3_TARGET_BANK",
        "direction": SUPERIORITY,
        "floor": (1, 2),
        "alternative": (3, 4),
        "statistical_unit": "item",
        "terminal_on_failure": "T09_RT_NOT_QUALIFIED",
    },
)

#: The diagnostic readout. It bears no gate and therefore contributes no cell.
D0_DIAGNOSTIC_ID = "D0_single_forward_decodability"

MISSING_TREATMENT = (
    "Every scheduled item is scored. An unparseable generation, an empty "
    "generation, a generation that is not a full-sequence exact match to a "
    "frozen legal answer surface, and any runtime failure are all scored "
    "incorrect. No item is dropped and no registered n is reduced."
)

STOP_RULE = (
    "Each atomic cell is evaluated exactly once at its registered n. There is "
    "no interim analysis, no adaptive stopping, no sample-size re-estimation "
    "and no post-result expansion. The RP-B ladder scan stops at the first "
    "confirmed pass, but every cell in the census is corrected over the full "
    "registered L = 3 regardless of where scanning stops."
)


# ---------------------------------------------------------------------------
# Exact integer binomial arithmetic
# ---------------------------------------------------------------------------


def _binomial_terms(n: int, a: int, b: int):
    """Return ``[C(n,i) * a**i * (b-a)**(n-i) for i in range(n + 1)]``.

    The exact probability of ``i`` successes under ``p = a / b`` is
    ``terms[i] / b**n``. Everything is an integer.
    """
    c = b - a
    pow_a = [1] * (n + 1)
    pow_c = [1] * (n + 1)
    for i in range(1, n + 1):
        pow_a[i] = pow_a[i - 1] * a
        pow_c[i] = pow_c[i - 1] * c
    terms = []
    binomial = 1
    for i in range(n + 1):
        terms.append(binomial * pow_a[i] * pow_c[n - i])
        binomial = binomial * (n - i) // (i + 1)
    return terms


def _le(num_a: int, den_a: int, num_b: int, den_b: int) -> bool:
    """Exact ``num_a/den_a <= num_b/den_b`` for positive denominators."""
    return num_a * den_b <= num_b * den_a


def upper_tail_numerator(terms, k: int) -> int:
    """Numerator of ``P(X >= k)`` over the common denominator ``b**n``."""
    if k <= 0:
        return sum(terms)
    if k >= len(terms):
        return 0
    return sum(terms[k:])


def lower_tail_numerator(terms, k: int) -> int:
    """Numerator of ``P(X <= k)`` over the common denominator ``b**n``."""
    if k < 0:
        return 0
    if k >= len(terms) - 1:
        return sum(terms)
    return sum(terms[: k + 1])


def minimal_pass_count(n: int, floor, alpha):
    """Smallest ``k`` with ``P(X >= k | n, floor) <= alpha``; ``None`` if none."""
    a, b = floor
    terms = _binomial_terms(n, a, b)
    denominator = b ** n
    running = 0
    best = None
    for k in range(n, -1, -1):
        running += terms[k]
        if _le(running, denominator, alpha[0], alpha[1]):
            best = k
        else:
            break
    return best


def maximal_accept_count(n: int, margin, alpha):
    """Largest ``k`` with ``P(X <= k | n, margin) <= alpha``; ``None`` if none."""
    a, b = margin
    terms = _binomial_terms(n, a, b)
    denominator = b ** n
    running = 0
    best = None
    for k in range(0, n + 1):
        running += terms[k]
        if _le(running, denominator, alpha[0], alpha[1]):
            best = k
        else:
            break
    return best


def upper_tail_probability(n: int, k: int, p):
    a, b = p
    terms = _binomial_terms(n, a, b)
    return upper_tail_numerator(terms, k), b ** n


def lower_tail_probability(n: int, k: int, p):
    a, b = p
    terms = _binomial_terms(n, a, b)
    return lower_tail_numerator(terms, k), b ** n


def _rational(pair) -> str:
    return "%d/%d" % (pair[0], pair[1])


def _exact(pair) -> str:
    """Canonical lowest-terms rendering of an exact rational pair."""
    numerator, denominator = pair
    if denominator == 0:  # pragma: no cover - defensive
        raise ZeroDivisionError("zero denominator")
    divisor = gcd(numerator, denominator)
    if divisor == 0:
        return "0/1"
    return "%d/%d" % (numerator // divisor, denominator // divisor)


def _display(num: int, den: int) -> str:
    return str((Decimal(num) / Decimal(den)).quantize(Decimal("1.000000000000")))


def size_and_power(n: int, direction, floor, alternative, alpha):
    """Exact size and power of one cell at ``n`` under its registered design."""
    if direction == SUPERIORITY:
        boundary = minimal_pass_count(n, floor, alpha)
        if boundary is None or boundary > n:
            return None
        boundary += PASS_BOUNDARY_OFFSET
        if boundary > n or boundary < 0:
            return None
        size_num, size_den = upper_tail_probability(n, boundary, floor)
        power_num, power_den = upper_tail_probability(n, boundary, alternative)
        strict_num, strict_den = upper_tail_probability(n, boundary - 1, floor)
    else:
        boundary = maximal_accept_count(n, floor, alpha)
        if boundary is None or boundary < 0:
            return None
        boundary -= PASS_BOUNDARY_OFFSET
        if boundary < 0 or boundary > n:
            return None
        size_num, size_den = lower_tail_probability(n, boundary, floor)
        power_num, power_den = lower_tail_probability(n, boundary, alternative)
        strict_num, strict_den = lower_tail_probability(n, boundary + 1, floor)
    return {
        "boundary": boundary,
        "size": (size_num, size_den),
        "power": (power_num, power_den),
        "adjacent_boundary_size": (strict_num, strict_den),
    }


def solve_cell(direction, floor, alternative, alpha, power_target,
               n_cap: int = 4000):
    """Smallest ``n`` whose exact power reaches ``power_target``.

    Returns the solution together with an exhaustive minimality certificate
    over every smaller ``n``.
    """
    best_below = {"n": None, "power": (0, 1)}
    for n in range(1, n_cap + 1):
        evaluated = size_and_power(n, direction, floor, alternative, alpha)
        if evaluated is None:
            continue
        power_num, power_den = evaluated["power"]
        if _le(power_target[0], power_target[1], power_num, power_den):
            return n, evaluated, best_below
        if _le(best_below["power"][0], best_below["power"][1],
               power_num, power_den):
            best_below = {"n": n, "power": (power_num, power_den)}
    raise RuntimeError("no admissible n at or below the registered cap")


# ---------------------------------------------------------------------------
# Census
# ---------------------------------------------------------------------------


def enumerate_census():
    """Enumerate every gate-bearing atomic cell from the registered factors."""
    cells = []
    for spec in GATE_SPECS:
        for role in spec["roles"]:
            for route in spec["routes"]:
                cells.append({
                    "cell_id": "%s|%s|%s" % (spec["gate_id"], role, route),
                    "gate_id": spec["gate_id"],
                    "checkpoint_role": role,
                    "route": route,
                    "phase": spec["phase"],
                    "task_family": spec["task_family"],
                    "statistical_unit": spec["statistical_unit"],
                })
    identifiers = [cell["cell_id"] for cell in cells]
    if len(set(identifiers)) != len(identifiers):
        raise RuntimeError("atomic-cell census contains a duplicate cell id")
    return cells


def build_tables():
    cells = enumerate_census()
    m_max = len(cells)
    alpha_cell = (ALPHA_GLOBAL[0], ALPHA_GLOBAL[1] * m_max)

    by_gate = {}
    for cell in cells:
        by_gate.setdefault(cell["gate_id"], []).append(cell["cell_id"])

    gates = []
    for spec in GATE_SPECS:
        n, evaluated, best_below = solve_cell(
            spec["direction"], spec["floor"], spec["alternative"],
            alpha_cell, POWER_TARGET)
        boundary = evaluated["boundary"]
        witness = None
        if best_below["n"] is not None:
            witness = {
                "n": best_below["n"],
                "power": _exact(best_below["power"]),
                "power_display_only": _display(*best_below["power"]),
            }
        if spec["direction"] == SUPERIORITY:
            null_hypothesis = "H0: p <= %s" % _rational(spec["floor"])
            alternative_hypothesis = "H1: p > %s" % _rational(spec["floor"])
            decision_rule = ("pass if and only if the number of correct items "
                             "k satisfies k >= %d out of n = %d" % (boundary, n))
            boundary_minimality = (
                "k = %d is the smallest integer whose exact upper-tail "
                "probability under the floor does not exceed the per-cell "
                "alpha; k = %d exceeds it." % (boundary, boundary - 1))
        else:
            null_hypothesis = "H0: p >= %s" % _rational(spec["floor"])
            alternative_hypothesis = "H1: p < %s" % _rational(spec["floor"])
            decision_rule = ("pass if and only if the number of correct items "
                             "k satisfies k <= %d out of n = %d" % (boundary, n))
            boundary_minimality = (
                "k = %d is the largest integer whose exact lower-tail "
                "probability under the upper margin does not exceed the "
                "per-cell alpha; k = %d exceeds it." % (boundary, boundary + 1))
        gates.append({
            "gate_id": spec["gate_id"],
            "title": spec["title"],
            "estimand": spec["estimand"],
            "phase": spec["phase"],
            "task_family": spec["task_family"],
            "checkpoint_roles": list(spec["roles"]),
            "routes": list(spec["routes"]),
            "atomic_cells": sorted(by_gate[spec["gate_id"]]),
            "atomic_cell_count": len(by_gate[spec["gate_id"]]),
            "statistical_unit": spec["statistical_unit"],
            "direction": spec["direction"],
            "null_hypothesis": null_hypothesis,
            "alternative_hypothesis": alternative_hypothesis,
            "chance_level": _rational(CHANCE_LEVEL),
            "floor_or_upper_margin": _rational(spec["floor"]),
            "effect_or_adequacy_margin": _rational(spec["alternative"]),
            "test": "exact one-sided binomial test on integer arithmetic",
            "multiplicity_family": MULTIPLICITY_FAMILY,
            "multiplicity_method": "bonferroni_equal_allocation",
            "alpha_global": _rational(ALPHA_GLOBAL),
            "alpha_per_cell": _rational(alpha_cell),
            "development_alpha": _rational(alpha_cell),
            "confirmation_alpha": _rational(alpha_cell),
            "power_target": _rational(POWER_TARGET),
            "n": n,
            "pass_boundary": boundary,
            "decision_rule": decision_rule,
            "exact_size": _exact(evaluated["size"]),
            "exact_size_display_only": _display(*evaluated["size"]),
            "exact_power": _exact(evaluated["power"]),
            "exact_power_display_only": _display(*evaluated["power"]),
            "adjacent_boundary_size": _exact(
                evaluated["adjacent_boundary_size"]),
            "adjacent_boundary_size_display_only": _display(
                *evaluated["adjacent_boundary_size"]),
            "boundary_minimality_proof": boundary_minimality,
            "sample_size_minimality_proof": {
                "claim": ("n = %d is the smallest sample size whose exact power "
                          "at the registered alternative reaches the registered "
                          "power target under the per-cell alpha." % n),
                "search_lower_bound": 1,
                "smaller_n_values_checked": n - 1,
                "every_smaller_n_falls_short": True,
                "best_power_below_n": witness,
            },
            "stop_rule": STOP_RULE,
            "missing_or_unparseable_treatment": MISSING_TREATMENT,
            "terminal_on_failure": spec["terminal_on_failure"],
        })

    total_scheduled = 0
    for spec, gate in zip(GATE_SPECS, gates):
        total_scheduled += gate["n"] * gate["atomic_cell_count"]

    return {
        "schema_version": "study3r-design-statistics-v1",
        "authority":
            "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md",
        "arithmetic": {
            "representation": "exact integer numerators over a common denominator",
            "uses_normal_approximation": False,
            "uses_floating_point_comparison": False,
            "inherited_sample_size_or_alpha_reused": False,
        },
        "factors": {
            "checkpoint_role": list(CHECKPOINT_ROLES),
            "e0_wrapper_arm": list(E0_ARMS),
            "cot_route": list(COT_ROUTE),
            "rp_b_ladder_length": LADDER_LENGTH,
        },
        "chance_level": _rational(CHANCE_LEVEL),
        "global_error_budget": {
            "alpha_global": _rational(ALPHA_GLOBAL),
            "sided": "one_sided",
            "family_id": MULTIPLICITY_FAMILY,
            "method": "bonferroni_equal_allocation",
            "m_max": m_max,
            "alpha_per_cell": _rational(alpha_cell),
            "correction_scope": (
                "every gate-bearing atomic cell in the census, including both "
                "E0 wrapper arms and the full registered L = 3 ladder, "
                "regardless of where ladder scanning stops"),
            "claims_fixed_sequence_protection": False,
        },
        "rp_b_decision_id": RPB_DECISION_ID,
        "diagnostic_without_a_gate": D0_DIAGNOSTIC_ID,
        "atomic_cell_census": {
            "cells": cells,
            "count": m_max,
            "counts_by_gate": {gate_id: len(members)
                               for gate_id, members in sorted(by_gate.items())},
        },
        "gates": gates,
        "totals": {
            "gate_count": len(gates),
            "atomic_cell_count": m_max,
            "scheduled_item_evaluations": total_scheduled,
        },
    }


def write_json(path: pathlib.Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=1, sort_keys=True,
                          ensure_ascii=True) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(ANALYSIS_DIR))
    args = parser.parse_args(argv)
    tables = build_tables()
    write_json(pathlib.Path(args.out_dir) /
               "study3r_design_statistics_tables.json", tables)
    print("m_max=%d gates=%d scheduled_item_evaluations=%d"
          % (tables["global_error_budget"]["m_max"],
             tables["totals"]["gate_count"],
             tables["totals"]["scheduled_item_evaluations"]))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
