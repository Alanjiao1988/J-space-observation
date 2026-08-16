"""Study 4F frozen statistical gates.

Authority: ``studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md``

Section 7 freezes the whole error budget before any execution:

* statistical unit: the item;
* maximum registered gate cells ``m_max = 16``
  (4 checkpoints x 2 depths x CoT = 8, plus 4 checkpoints x 2 depths x E0 = 8);
* global familywise ``alpha = 1/20``;
* Bonferroni over all 16 cells regardless of how many are reached;
* per-cell ``alpha = 1/320``;
* target power ``9/10``;
* exact one-sided integer binomial tests only.

Registered cells:

===== ================== ================== === ====
cell  null floor         design alternative n   pass
===== ================== ================== === ====
CoT   ``p <= 3/4``       ``p = 9/10``       104 >= 90
E0    ``p <= 1/2``       ``p = 3/4``        60  >= 41
===== ================== ================== === ====

D2 and D3 are always separate cells. They may never be pooled for a gate, a
headline or a ladder transition; :func:`pool` exists only to raise.

Everything here is exact integer/rational arithmetic. No floating point value
takes part in any decision.
"""

from __future__ import annotations

from fractions import Fraction
from math import comb
from typing import Dict, Tuple

#: Global familywise error rate.
ALPHA_GLOBAL = Fraction(1, 20)

#: Maximum registered gate cells. Bonferroni divides by this regardless of how
#: many cells are actually reached.
M_MAX = 16

#: Per-cell error budget.
ALPHA_PER_CELL = ALPHA_GLOBAL / M_MAX

#: Target power per cell.
TARGET_POWER = Fraction(9, 10)

#: The two registered cell kinds.
CELLS: Dict[str, Dict[str, object]] = {
    "COT": {
        "route": "C1_LONG_GENERATED_COT_HEADROOM",
        "null_floor": Fraction(3, 4),
        "design_alternative": Fraction(9, 10),
        "n": 104,
        "pass_boundary": 90,
    },
    "E0": {
        "route": "W1_RAW_DIRECT",
        "null_floor": Fraction(1, 2),
        "design_alternative": Fraction(3, 4),
        "n": 60,
        "pass_boundary": 41,
    },
}

#: The registered depths. They are never pooled.
DEPTHS: Tuple[str, ...] = ("D2", "D3")

#: The registered checkpoint roles, in ladder order with the target last.
CHECKPOINT_ROLES: Tuple[str, ...] = ("RP_B1", "RP_B2", "RP_B3", "RT")


class Study4FPoolingProhibitedError(RuntimeError):
    """Raised on any attempt to pool D2 and D3 into one decision."""


def binomial_tail(n: int, k: int, p: Fraction) -> Fraction:
    """Exact ``P[X >= k]`` for ``X ~ Binomial(n, p)``."""
    if not 0 <= k <= n + 1:
        raise ValueError("boundary outside the support")
    return sum((Fraction(comb(n, i)) * p ** i * (1 - p) ** (n - i)
                for i in range(k, n + 1)), Fraction(0))


def exact_size(cell: str) -> Fraction:
    """Exact one-sided size of a registered cell at its null floor."""
    spec = CELLS[cell]
    return binomial_tail(int(spec["n"]), int(spec["pass_boundary"]),
                         spec["null_floor"])  # type: ignore[arg-type]


def exact_power(cell: str) -> Fraction:
    """Exact power of a registered cell at its design alternative."""
    spec = CELLS[cell]
    return binomial_tail(int(spec["n"]), int(spec["pass_boundary"]),
                         spec["design_alternative"])  # type: ignore[arg-type]


def minimal_boundary(n: int, null_floor: Fraction,
                     alpha: Fraction = ALPHA_PER_CELL) -> int:
    """Smallest integer boundary whose exact size does not exceed ``alpha``."""
    for boundary in range(0, n + 2):
        if binomial_tail(n, boundary, null_floor) <= alpha:
            return boundary
    raise ValueError("no boundary attains the budget")


def minimal_design(null_floor: Fraction, design_alternative: Fraction,
                   alpha: Fraction = ALPHA_PER_CELL,
                   power: Fraction = TARGET_POWER,
                   limit: int = 400) -> Tuple[int, int]:
    """Smallest ``(n, boundary)`` meeting both the size and the power budget."""
    for n in range(1, limit + 1):
        boundary = minimal_boundary(n, null_floor, alpha)
        if binomial_tail(n, boundary, design_alternative) >= power:
            return n, boundary
    raise ValueError("no design attains the budget within the search limit")


def passes(cell: str, correct: int) -> bool:
    """Registered pass rule: an integer comparison against the boundary."""
    spec = CELLS[cell]
    n = int(spec["n"])
    if not 0 <= correct <= n:
        raise ValueError("correct count outside the registered n")
    return correct >= int(spec["pass_boundary"])


def cell_id(checkpoint_role: str, depth: str, cell: str) -> str:
    """The registered atomic-cell identifier."""
    if checkpoint_role not in CHECKPOINT_ROLES:
        raise ValueError("unregistered checkpoint role: %r" % (checkpoint_role,))
    if depth not in DEPTHS:
        raise ValueError("unregistered depth: %r" % (depth,))
    if cell not in CELLS:
        raise ValueError("unregistered cell kind: %r" % (cell,))
    return "%s|%s|%s" % (checkpoint_role, depth, cell)


def registered_cells() -> Tuple[str, ...]:
    """Every gate cell in the Bonferroni family, in registered order."""
    return tuple(cell_id(role, depth, cell)
                 for cell in ("COT", "E0")
                 for role in CHECKPOINT_ROLES
                 for depth in DEPTHS)


def pool(*_args, **_kwargs):
    """D2 and D3 may never be pooled. This function only ever raises."""
    raise Study4FPoolingProhibitedError(
        "D2 and D3 are always separate cells and may never be pooled for a "
        "gate, a headline or a ladder transition")
