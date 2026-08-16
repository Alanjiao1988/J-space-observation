"""Independent Study 3R design recalculation (single focused review).

Authority:
``studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md``

This module is a *review* artifact. It imports nothing from the candidate:
not ``study3r_protocol_build.py``, not ``study3r_design_statistics.py``, not
``study3r_independent_recalculation.py``, and not the task-bank production
calculators. It uses only the Python standard library, and every probability is
carried as an exact :class:`fractions.Fraction`; there is no floating-point
comparison anywhere in a decision path.

It recalculates, from the registered factor levels alone:

* every gate-bearing atomic cell and ``m_max``;
* ``alpha_global`` and ``alpha_per_cell``;
* every exact null tail and integer pass boundary;
* every exact power and the minimality of every ``n``;
* the total scheduled evaluation count;
* the first-confirmed-pass multiplicity over ``L = 3``;
* the negative-control direction and boundary;
* a clearly labelled **counterfactual** census in which depth-2 and depth-3
  are separate gate-bearing factors.

The counterfactual is a diagnostic that quantifies a defect. It is not a
repair, not an amendment and not a proposed design.

Run::

    python studies/study3r/reviews/study3r_review_independent_recalculation.py

It writes ``study3r_review_independent_recalculation_tables.json`` beside this
module.
"""

from __future__ import annotations

import json
import pathlib
from decimal import Decimal, getcontext
from fractions import Fraction
from math import comb
from typing import Dict, List, Optional, Sequence, Tuple

getcontext().prec = 60

OUT = (pathlib.Path(__file__).parent
       / "study3r_review_independent_recalculation_tables.json")

# ---------------------------------------------------------------------------
# Registered factor levels, re-typed from the candidate protocol
# ---------------------------------------------------------------------------

CHECKPOINT_ROLES = ("RT", "RP_B1", "RP_B2", "RP_B3")
RP_B_ROLES = ("RP_B1", "RP_B2", "RP_B3")
RT_ROLES = ("RT",)
LADDER_LENGTH = len(RP_B_ROLES)
E0_ARMS = ("W1_RAW_DIRECT", "W2_ROLE_CANONICAL")
COT_ROUTE = ("C1_CANONICAL_GENERATED_COT",)

ALPHA_GLOBAL = Fraction(1, 20)
POWER_TARGET = Fraction(9, 10)
CHANCE_LEVEL = Fraction(1, 4)

GREATER = "greater_than_floor"
LESS = "less_than_upper_margin"

GATES: Tuple[Dict[str, object], ...] = (
    {"gate_id": "G01_COT_CEILING", "roles": CHECKPOINT_ROLES,
     "routes": COT_ROUTE, "direction": GREATER,
     "floor": Fraction(3, 4), "alternative": Fraction(9, 10),
     "bank": "D2_D3_CEILING_BANK", "mixed_depth": True,
     "registered_n": 128, "registered_pass_boundary": 111},
    {"gate_id": "G02_CONTROL_RECOVERY", "roles": CHECKPOINT_ROLES,
     "routes": E0_ARMS, "direction": GREATER,
     "floor": Fraction(9, 10), "alternative": Fraction(99, 100),
     "bank": "REC", "mixed_depth": False,
     "registered_n": 110, "registered_pass_boundary": 108},
    {"gate_id": "G03_CONTROL_BINDING", "roles": CHECKPOINT_ROLES,
     "routes": E0_ARMS, "direction": GREATER,
     "floor": Fraction(9, 10), "alternative": Fraction(99, 100),
     "bank": "BIND", "mixed_depth": False,
     "registered_n": 110, "registered_pass_boundary": 108},
    {"gate_id": "G04_CONTROL_PRIMITIVE", "roles": CHECKPOINT_ROLES,
     "routes": E0_ARMS, "direction": GREATER,
     "floor": Fraction(9, 10), "alternative": Fraction(99, 100),
     "bank": "PRIM", "mixed_depth": False,
     "registered_n": 110, "registered_pass_boundary": 108},
    {"gate_id": "G05_NEGATIVE_CONTROL", "roles": CHECKPOINT_ROLES,
     "routes": E0_ARMS, "direction": LESS,
     "floor": Fraction(35, 100), "alternative": CHANCE_LEVEL,
     "bank": "NEG", "mixed_depth": False,
     "registered_n": 416, "registered_pass_boundary": 115},
    {"gate_id": "G06_WRAPPER_JOINT_ADEQUACY", "roles": CHECKPOINT_ROLES,
     "routes": E0_ARMS, "direction": GREATER,
     "floor": Fraction(1, 2), "alternative": Fraction(3, 4),
     "bank": "D2_ADEQUACY_BANK", "mixed_depth": False,
     "registered_n": 74, "registered_pass_boundary": 51},
    {"gate_id": "G07_RPB_DEVELOPMENT", "roles": RP_B_ROLES,
     "routes": E0_ARMS, "direction": GREATER,
     "floor": Fraction(1, 2), "alternative": Fraction(3, 4),
     "bank": "D2_D3_DEVELOPMENT_BANK", "mixed_depth": True,
     "registered_n": 74, "registered_pass_boundary": 51},
    {"gate_id": "G08_RPB_CONFIRMATION", "roles": RP_B_ROLES,
     "routes": E0_ARMS, "direction": GREATER,
     "floor": Fraction(1, 2), "alternative": Fraction(3, 4),
     "bank": "D2_D3_CONFIRMATION_BANK", "mixed_depth": True,
     "registered_n": 74, "registered_pass_boundary": 51},
    {"gate_id": "G09_RT_E0_QUALIFICATION", "roles": RT_ROLES,
     "routes": E0_ARMS, "direction": GREATER,
     "floor": Fraction(1, 2), "alternative": Fraction(3, 4),
     "bank": "D2_D3_TARGET_BANK", "mixed_depth": True,
     "registered_n": 74, "registered_pass_boundary": 51},
)

#: Registered exact-power display strings, re-typed for comparison only.
REGISTERED_DISPLAY = {
    "G01_COT_CEILING": ("0.912498598878", "0.000856460763"),
    "G02_CONTROL_RECOVERY": ("0.901331394239", "0.000807913105"),
    "G03_CONTROL_BINDING": ("0.901331394239", "0.000807913105"),
    "G04_CONTROL_PRIMITIVE": ("0.901331394239", "0.000807913105"),
    "G05_NEGATIVE_CONTROL": ("0.902527305436", "0.000827387853"),
    "G06_WRAPPER_JOINT_ADEQUACY": ("0.907835037241", "0.000758111832"),
    "G07_RPB_DEVELOPMENT": ("0.907835037241", "0.000758111832"),
    "G08_RPB_CONFIRMATION": ("0.907835037241", "0.000758111832"),
    "G09_RT_E0_QUALIFICATION": ("0.907835037241", "0.000758111832"),
}

REGISTERED_M_MAX = 58
REGISTERED_ALPHA_PER_CELL = Fraction(1, 1160)


# ---------------------------------------------------------------------------
# Exact binomial arithmetic on Fractions
# ---------------------------------------------------------------------------


def pmf(n: int, p: Fraction) -> List[Fraction]:
    """Exact binomial pmf as a list of ``n + 1`` Fractions."""
    q = 1 - p
    return [comb(n, i) * p ** i * q ** (n - i) for i in range(n + 1)]


def upper_tail(terms: Sequence[Fraction], k: int) -> Fraction:
    """``P(X >= k)``."""
    if k <= 0:
        return Fraction(1)
    if k > len(terms) - 1:
        return Fraction(0)
    return sum(terms[k:], Fraction(0))


def lower_tail(terms: Sequence[Fraction], k: int) -> Fraction:
    """``P(X <= k)``."""
    if k < 0:
        return Fraction(0)
    if k >= len(terms) - 1:
        return Fraction(1)
    return sum(terms[: k + 1], Fraction(0))


def minimal_pass_count(n: int, floor: Fraction,
                       alpha: Fraction) -> Optional[int]:
    """Smallest ``k`` with ``P(X >= k | n, floor) <= alpha``."""
    terms = pmf(n, floor)
    running = Fraction(0)
    best: Optional[int] = None
    for k in range(n, -1, -1):
        running += terms[k]
        if running <= alpha:
            best = k
        else:
            break
    return best


def maximal_accept_count(n: int, margin: Fraction,
                         alpha: Fraction) -> Optional[int]:
    """Largest ``k`` with ``P(X <= k | n, margin) <= alpha``."""
    terms = pmf(n, margin)
    running = Fraction(0)
    best: Optional[int] = None
    for k in range(0, n + 1):
        running += terms[k]
        if running <= alpha:
            best = k
        else:
            break
    return best


def cell_operating_characteristics(n: int, direction: str, floor: Fraction,
                                   alternative: Fraction,
                                   alpha: Fraction):
    """Exact boundary, size and power of one cell at ``n``."""
    if direction == GREATER:
        boundary = minimal_pass_count(n, floor, alpha)
        if boundary is None:
            return None
        null_terms = pmf(n, floor)
        alt_terms = pmf(n, alternative)
        size = upper_tail(null_terms, boundary)
        power = upper_tail(alt_terms, boundary)
        adjacent = upper_tail(null_terms, boundary - 1)
    else:
        boundary = maximal_accept_count(n, floor, alpha)
        if boundary is None:
            return None
        null_terms = pmf(n, floor)
        alt_terms = pmf(n, alternative)
        size = lower_tail(null_terms, boundary)
        power = lower_tail(alt_terms, boundary)
        adjacent = lower_tail(null_terms, boundary + 1)
    return {"boundary": boundary, "size": size, "power": power,
            "adjacent": adjacent}


def minimal_sample_size(direction: str, floor: Fraction,
                        alternative: Fraction, alpha: Fraction,
                        ceiling: int) -> Dict[str, object]:
    """Smallest ``n <= ceiling`` reaching the power target, exhaustively."""
    failures: List[int] = []
    for n in range(1, ceiling + 1):
        oc = cell_operating_characteristics(n, direction, floor, alternative,
                                            alpha)
        if oc is None or oc["power"] < POWER_TARGET:
            failures.append(n)
            continue
        return {"n": n, "boundary": oc["boundary"], "size": oc["size"],
                "power": oc["power"], "adjacent": oc["adjacent"],
                "every_smaller_n_fails_the_power_target":
                    failures == list(range(1, n)),
                "smaller_n_checked": len(failures)}
    return {"n": None, "smaller_n_checked": len(failures)}


def display(value: Fraction) -> str:
    return str((Decimal(value.numerator) / Decimal(value.denominator))
               .quantize(Decimal("1.000000000000")))


def rational(value: Fraction) -> str:
    return "%d/%d" % (value.numerator, value.denominator)


# ---------------------------------------------------------------------------
# Census
# ---------------------------------------------------------------------------


def enumerate_cells(gates: Sequence[Dict[str, object]],
                    split_depth: bool) -> List[str]:
    cells: List[str] = []
    for gate in gates:
        depths: Tuple[str, ...] = ("",)
        if split_depth and gate["mixed_depth"]:
            depths = ("D2", "D3")
        for role in gate["roles"]:                       # type: ignore[index]
            for route in gate["routes"]:                 # type: ignore[index]
                for depth in depths:
                    suffix = ("|%s" % depth) if depth else ""
                    cells.append("%s|%s|%s%s"
                                 % (gate["gate_id"], role, route, suffix))
    return cells


def close_design(split_depth: bool, ceiling: int = 1200) -> Dict[str, object]:
    cells = enumerate_cells(GATES, split_depth)
    assert len(cells) == len(set(cells)), "duplicate atomic cell identifier"
    m_max = len(cells)
    alpha_per_cell = ALPHA_GLOBAL / m_max

    rows = []
    scheduled = 0
    for gate in GATES:
        gate_cells = [c for c in cells
                      if c.startswith("%s|" % gate["gate_id"])]
        minimal = minimal_sample_size(str(gate["direction"]),
                                      gate["floor"],       # type: ignore[arg-type]
                                      gate["alternative"], # type: ignore[arg-type]
                                      alpha_per_cell, ceiling)
        n = minimal["n"]
        scheduled += len(gate_cells) * (n or 0)
        row: Dict[str, object] = {
            "gate_id": gate["gate_id"],
            "bank_id": gate["bank"],
            "direction": gate["direction"],
            "floor_or_upper_margin": rational(gate["floor"]),      # type: ignore[arg-type]
            "effect_or_adequacy_margin":
                rational(gate["alternative"]),                     # type: ignore[arg-type]
            "atomic_cell_count": len(gate_cells),
            "atomic_cells": gate_cells,
            "alpha_per_cell": rational(alpha_per_cell),
            "n_minimal": n,
            "pass_boundary": minimal.get("boundary"),
            "exact_size": rational(minimal["size"]) if n else None,
            "exact_size_display": display(minimal["size"]) if n else None,
            "exact_power": rational(minimal["power"]) if n else None,
            "exact_power_display": display(minimal["power"]) if n else None,
            "adjacent_boundary_size":
                rational(minimal["adjacent"]) if n else None,
            "adjacent_boundary_size_display":
                display(minimal["adjacent"]) if n else None,
            "every_smaller_n_fails_the_power_target":
                minimal.get("every_smaller_n_fails_the_power_target"),
            "boundary_is_minimal_for_its_size_constraint": None,
            "scheduled_evaluations": len(gate_cells) * (n or 0),
        }
        if n:
            # Boundary minimality: k - 1 must violate the size constraint.
            oc_prev = minimal["adjacent"]
            row["boundary_is_minimal_for_its_size_constraint"] = (
                oc_prev > alpha_per_cell)
        rows.append(row)

    return {
        "split_depth_into_separate_cells": split_depth,
        "m_max": m_max,
        "alpha_global": rational(ALPHA_GLOBAL),
        "alpha_per_cell": rational(alpha_per_cell),
        "power_target": rational(POWER_TARGET),
        "multiplicity_family": "F_GLOBAL_STUDY3R",
        "multiplicity_method": "bonferroni_equal_allocation",
        "total_scheduled_evaluations": scheduled,
        "gates": rows,
    }


# ---------------------------------------------------------------------------
# Ladder multiplicity
# ---------------------------------------------------------------------------


def ladder_multiplicity(alpha_per_cell: Fraction) -> Dict[str, object]:
    """First-confirmed-pass scanning over the full registered ``L = 3``."""
    dev_cells = len(RP_B_ROLES) * len(E0_ARMS)
    conf_cells = len(RP_B_ROLES) * len(E0_ARMS)
    return {
        "registered_L": LADDER_LENGTH,
        "selection_rule": "first_confirmed_pass",
        "claims_fixed_sequence_protection": False,
        "development_cells_over_full_L": dev_cells,
        "confirmation_cells_over_full_L": conf_cells,
        "development_and_confirmation_are_separate_inferential_cells": True,
        "evaluations_per_candidate": {"development": 1, "confirmation": 1},
        "corrected_over_full_registered_L": True,
        "worst_case_family_wise_error_over_the_ladder_cells":
            rational((dev_cells + conf_cells) * alpha_per_cell),
        "worst_case_family_wise_error_over_the_ladder_cells_display":
            display((dev_cells + conf_cells) * alpha_per_cell),
    }


# ---------------------------------------------------------------------------
# D2 / D3 pooling and masking
# ---------------------------------------------------------------------------


def depth_masking(n: int, pass_boundary: int, alpha: Fraction) -> Dict[str, object]:
    """Exact masking arithmetic for one pooled depth-2/depth-3 cell.

    Reports, for every integer allocation ``(n_d2, n_d3)`` with
    ``n_d2 + n_d3 == n``, the weakest depth-3 count compatible with passing
    when depth-2 performance is perfect, and whether that depth-3 record is
    itself distinguishable from the chance level at ``alpha``.
    """
    rows = []
    for n_d3 in range(0, n + 1):
        n_d2 = n - n_d3
        min_d3 = max(0, pass_boundary - n_d2)
        row: Dict[str, object] = {
            "n_d2": n_d2, "n_d3": n_d3,
            "minimum_d3_correct_when_d2_is_perfect": min_d3,
        }
        if n_d3:
            row["implied_d3_accuracy"] = rational(Fraction(min_d3, n_d3))
            row["implied_d3_accuracy_display"] = display(
                Fraction(min_d3, n_d3))
            chance_terms = pmf(n_d3, CHANCE_LEVEL)
            tail = upper_tail(chance_terms, min_d3)
            row["exact_one_sided_p_vs_chance"] = display(tail)
            row["d3_record_beats_chance_at_alpha_per_cell"] = tail <= alpha
            row["d3_record_reaches_the_registered_floor"] = (
                Fraction(min_d3, n_d3) >= Fraction(1, 2))
        else:
            row["implied_d3_accuracy"] = None
            row["d3_record_beats_chance_at_alpha_per_cell"] = False
            row["d3_record_reaches_the_registered_floor"] = False
        rows.append(row)
    balanced = rows[n // 2]
    worst = [r for r in rows
             if r["n_d3"] and not r["d3_record_beats_chance_at_alpha_per_cell"]]
    return {
        "n": n,
        "pass_boundary": pass_boundary,
        "allocation_is_registered_by_the_candidate": False,
        "balanced_allocation": balanced,
        "largest_n_d3_whose_minimum_passing_record_does_not_beat_chance":
            max((r["n_d3"] for r in worst), default=0),
        "zero_depth_three_success_passes_when_n_d2_at_least":
            pass_boundary,
        "all_allocations": rows,
    }


def main() -> Dict[str, object]:
    registered = close_design(split_depth=False)
    counterfactual = close_design(split_depth=True)

    comparison = []
    for gate in GATES:
        row = next(r for r in registered["gates"]        # type: ignore[index]
                   if r["gate_id"] == gate["gate_id"])
        power_display, size_display = REGISTERED_DISPLAY[str(gate["gate_id"])]
        comparison.append({
            "gate_id": gate["gate_id"],
            "registered_n": gate["registered_n"],
            "recalculated_n": row["n_minimal"],
            "n_agrees": row["n_minimal"] == gate["registered_n"],
            "registered_pass_boundary": gate["registered_pass_boundary"],
            "recalculated_pass_boundary": row["pass_boundary"],
            "pass_boundary_agrees":
                row["pass_boundary"] == gate["registered_pass_boundary"],
            "registered_power_display": power_display,
            "recalculated_power_display": row["exact_power_display"],
            "power_display_agrees":
                row["exact_power_display"] == power_display,
            "registered_size_display": size_display,
            "recalculated_size_display": row["exact_size_display"],
            "size_display_agrees":
                row["exact_size_display"] == size_display,
        })

    alpha_per_cell = ALPHA_GLOBAL / int(registered["m_max"])  # type: ignore[arg-type]

    masking = {
        "G09_RT_E0_QUALIFICATION": depth_masking(74, 51, alpha_per_cell),
        "G07_RPB_DEVELOPMENT": depth_masking(74, 51, alpha_per_cell),
        "G08_RPB_CONFIRMATION": depth_masking(74, 51, alpha_per_cell),
        "G01_COT_CEILING": depth_masking(128, 111, alpha_per_cell),
    }

    return {
        "authority": ("studies/study3r/prompts/"
                      "study3r_protocol_v1_single_focused_review_authority.md"),
        "schema_version": "study3r-review-independent-recalculation-v1",
        "imports_no_candidate_calculator": True,
        "arithmetic": "exact rational (fractions.Fraction) and exact integers",
        "registered_design": registered,
        "registered_m_max": REGISTERED_M_MAX,
        "m_max_agrees": registered["m_max"] == REGISTERED_M_MAX,
        "registered_alpha_per_cell": rational(REGISTERED_ALPHA_PER_CELL),
        "alpha_per_cell_agrees":
            ALPHA_GLOBAL / int(registered["m_max"]) ==  # type: ignore[arg-type]
            REGISTERED_ALPHA_PER_CELL,
        "gate_comparison": comparison,
        "all_gates_agree": all(r["n_agrees"] and r["pass_boundary_agrees"]
                               and r["power_display_agrees"]
                               and r["size_display_agrees"]
                               for r in comparison),
        "ladder_multiplicity": ladder_multiplicity(alpha_per_cell),
        "depth_masking": masking,
        "counterfactual_depth_split_census": counterfactual,
        "counterfactual_is_a_diagnostic_not_a_repair": True,
    }


if __name__ == "__main__":
    payload = main()
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print("wrote", OUT)
    print("m_max", payload["registered_design"]["m_max"],
          "agrees", payload["m_max_agrees"])
    print("all gates agree:", payload["all_gates_agree"])
    print("counterfactual m_max",
          payload["counterfactual_depth_split_census"]["m_max"])
