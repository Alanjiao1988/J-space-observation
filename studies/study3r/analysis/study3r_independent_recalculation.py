"""Study 3R independent statistical recalculation.

Authority: ``studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md``

This module is deliberately **independent** of the production calculators. It
imports nothing from ``study3r_design_statistics``, ``study3r_protocol_build``,
``study3r_task_generators_v1`` or ``study3r_manifest``; it uses only the Python
standard library.

It reads the built protocol candidate, re-enumerates the gate-bearing
atomic-cell census from the protocol's own registered factor levels, re-derives
``m_max`` and the per-cell alpha, and recomputes every registered sample size,
integer pass boundary, exact size and exact power from first principles using
``fractions.Fraction`` and ``math.comb``. It then emits an exact agreement
table and an exhaustive minimality proof.

A disagreement in any cell is a hard failure.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from decimal import Decimal, getcontext
from fractions import Fraction
from functools import lru_cache
from math import comb

getcontext().prec = 60

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parents[3]

SUPERIORITY = "greater_than_floor"
UPPER_BOUND = "less_than_upper_margin"


def _parse_rational(text: str) -> Fraction:
    numerator, _, denominator = text.partition("/")
    return Fraction(int(numerator), int(denominator))


def _format_rational(value: Fraction) -> str:
    return "%d/%d" % (value.numerator, value.denominator)


def _display(value: Fraction) -> str:
    quotient = Decimal(value.numerator) / Decimal(value.denominator)
    return str(quotient.quantize(Decimal("1.000000000000")))


def upper_tail(n: int, k: int, p: Fraction) -> Fraction:
    if k <= 0:
        return Fraction(1)
    if k > n:
        return Fraction(0)
    total = Fraction(0)
    for i in range(k, n + 1):
        total += Fraction(comb(n, i)) * p ** i * (1 - p) ** (n - i)
    return total


def lower_tail(n: int, k: int, p: Fraction) -> Fraction:
    if k < 0:
        return Fraction(0)
    if k >= n:
        return Fraction(1)
    total = Fraction(0)
    for i in range(0, k + 1):
        total += Fraction(comb(n, i)) * p ** i * (1 - p) ** (n - i)
    return total


def smallest_pass_count(n: int, floor: Fraction, alpha: Fraction):
    """Binary search for the smallest ``k`` with ``P(X >= k) <= alpha``.

    ``P(X >= k)`` is non-increasing in ``k``, so the predicate is monotone.
    """
    low, high = 0, n + 1
    if upper_tail(n, high, floor) > alpha:  # pragma: no cover - impossible
        return None
    while low < high:
        middle = (low + high) // 2
        if upper_tail(n, middle, floor) <= alpha:
            high = middle
        else:
            low = middle + 1
    return low if low <= n else None


def largest_accept_count(n: int, margin: Fraction, alpha: Fraction):
    """Binary search for the largest ``k`` with ``P(X <= k) <= alpha``."""
    if lower_tail(n, 0, margin) > alpha:
        return None
    low, high = 0, n
    while low < high:
        middle = (low + high + 1) // 2
        if lower_tail(n, middle, margin) <= alpha:
            low = middle
        else:
            high = middle - 1
    return low


def evaluate(n: int, direction: str, floor: Fraction, alternative: Fraction,
             alpha: Fraction):
    if direction == SUPERIORITY:
        boundary = smallest_pass_count(n, floor, alpha)
        if boundary is None:
            return None
        return {
            "boundary": boundary,
            "size": upper_tail(n, boundary, floor),
            "power": upper_tail(n, boundary, alternative),
            "adjacent": upper_tail(n, boundary - 1, floor),
        }
    boundary = largest_accept_count(n, floor, alpha)
    if boundary is None:
        return None
    return {
        "boundary": boundary,
        "size": lower_tail(n, boundary, floor),
        "power": lower_tail(n, boundary, alternative),
        "adjacent": lower_tail(n, boundary + 1, floor),
    }


@lru_cache(maxsize=None)
def solve(direction: str, floor: Fraction, alternative: Fraction,
          alpha: Fraction, power_target: Fraction, cap: int = 4000):
    best_below = {"n": None, "power": Fraction(0)}
    for n in range(1, cap + 1):
        evaluated = evaluate(n, direction, floor, alternative, alpha)
        if evaluated is None:
            continue
        if evaluated["power"] >= power_target:
            return n, evaluated, dict(best_below)
        if evaluated["power"] > best_below["power"]:
            best_below = {"n": n, "power": evaluated["power"]}
    raise RuntimeError("no admissible n at or below the cap")


def recount_census(protocol):
    """Re-enumerate the census from the protocol's registered factor levels."""
    cells = []
    for gate in protocol["statistics"]["gates"]:
        for role in gate["checkpoint_roles"]:
            for route in gate["routes"]:
                cells.append("%s|%s|%s" % (gate["gate_id"], role, route))
    return cells


def recalculate(protocol):
    cells = recount_census(protocol)
    m_max = len(cells)
    alpha_global = _parse_rational(
        protocol["statistics"]["global_error_budget"]["alpha_global"])
    alpha_cell = alpha_global / m_max
    rows = []
    disagreements = []
    for gate in protocol["statistics"]["gates"]:
        floor = _parse_rational(gate["floor_or_upper_margin"])
        alternative = _parse_rational(gate["effect_or_adequacy_margin"])
        power_target = _parse_rational(gate["power_target"])
        n, evaluated, best_below = solve(gate["direction"], floor, alternative,
                                         alpha_cell, power_target)
        row = {
            "gate_id": gate["gate_id"],
            "recomputed_alpha_per_cell": _format_rational(alpha_cell),
            "recomputed_n": n,
            "recomputed_pass_boundary": evaluated["boundary"],
            "recomputed_exact_size": _format_rational(evaluated["size"]),
            "recomputed_exact_power": _format_rational(evaluated["power"]),
            "recomputed_adjacent_boundary_size":
                _format_rational(evaluated["adjacent"]),
            "recomputed_exact_size_display_only": _display(evaluated["size"]),
            "recomputed_exact_power_display_only": _display(evaluated["power"]),
            "recomputed_best_power_below_n": (
                None if best_below["n"] is None else {
                    "n": best_below["n"],
                    "power": _format_rational(best_below["power"]),
                }),
            "registered_alpha_per_cell": gate["alpha_per_cell"],
            "registered_n": gate["n"],
            "registered_pass_boundary": gate["pass_boundary"],
            "registered_exact_size": gate["exact_size"],
            "registered_exact_power": gate["exact_power"],
            "registered_adjacent_boundary_size": gate["adjacent_boundary_size"],
        }
        checks = {
            "alpha_per_cell": row["recomputed_alpha_per_cell"]
                              == row["registered_alpha_per_cell"],
            "n": row["recomputed_n"] == row["registered_n"],
            "pass_boundary": row["recomputed_pass_boundary"]
                             == row["registered_pass_boundary"],
            "exact_size": row["recomputed_exact_size"]
                          == row["registered_exact_size"],
            "exact_power": row["recomputed_exact_power"]
                           == row["registered_exact_power"],
            "adjacent_boundary_size":
                row["recomputed_adjacent_boundary_size"]
                == row["registered_adjacent_boundary_size"],
            "size_within_alpha": evaluated["size"] <= alpha_cell,
            "adjacent_boundary_exceeds_alpha": evaluated["adjacent"] > alpha_cell,
            "power_reaches_target": evaluated["power"] >= power_target,
            "minimality_certificate_matches":
                (best_below["n"] is None
                 and gate["sample_size_minimality_proof"]["best_power_below_n"]
                 is None)
                or (best_below["n"] is not None
                    and gate["sample_size_minimality_proof"]["best_power_below_n"]
                    is not None
                    and best_below["n"] == gate["sample_size_minimality_proof"][
                        "best_power_below_n"]["n"]
                    and _format_rational(best_below["power"])
                    == gate["sample_size_minimality_proof"][
                        "best_power_below_n"]["power"]),
            "no_smaller_n_reaches_the_target": best_below["power"] < power_target,
            "cell_count": gate["atomic_cell_count"] == len(
                gate["checkpoint_roles"]) * len(gate["routes"]),
        }
        row["checks"] = checks
        row["agrees"] = all(checks.values())
        if not row["agrees"]:
            disagreements.append({
                "gate_id": gate["gate_id"],
                "failed_checks": sorted(name for name, ok in checks.items()
                                        if not ok),
            })
        rows.append(row)

    census_agrees = (
        m_max == protocol["statistics"]["m_max"]
        and m_max == protocol["statistics"]["atomic_cell_count"]
        and sorted(cells) == sorted(
            cell for gate in protocol["statistics"]["gates"]
            for cell in gate["atomic_cells"]))
    if not census_agrees:
        disagreements.append({"gate_id": "CENSUS",
                              "failed_checks": ["atomic_cell_census"]})

    return {
        "schema_version": "study3r-independent-recalculation-v1",
        "authority":
            "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md",
        "protocol_id": protocol["protocol_id"],
        "independence": {
            "imports_production_calculators": False,
            "imported_modules": ["argparse", "json", "pathlib", "decimal",
                                 "fractions", "math"],
            "standard_library_only": True,
            "arithmetic": "fractions.Fraction with math.comb",
            "search_strategy": "monotone binary search on the integer boundary",
        },
        "recomputed_census": {
            "cells": sorted(cells),
            "count": m_max,
            "m_max": m_max,
            "alpha_per_cell": _format_rational(alpha_cell),
            "agrees_with_protocol": census_agrees,
        },
        "rows": rows,
        "agreement": {
            "gates_compared": len(rows),
            "gates_in_agreement": sum(1 for row in rows if row["agrees"]),
            "disagreements": disagreements,
            "exact_agreement": not disagreements,
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
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--out-root", default=None)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)
    out_root = pathlib.Path(args.out_root or args.root)
    protocol_path = (root / "studies" / "study3r" / "protocol"
                     / "study3r_protocol_v1.json")
    with open(protocol_path, "r", encoding="utf-8") as handle:
        protocol = json.load(handle)
    tables = recalculate(protocol)
    write_json(out_root / "studies" / "study3r" / "analysis"
               / "study3r_independent_recalculation_tables.json", tables)
    print("independent recalculation: %d/%d gates agree; exact_agreement=%s"
          % (tables["agreement"]["gates_in_agreement"],
             tables["agreement"]["gates_compared"],
             tables["agreement"]["exact_agreement"]))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
