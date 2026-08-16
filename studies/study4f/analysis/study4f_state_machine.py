"""Study 4F candidate-local execution state machine.

Authority: ``studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md``

Sections 8 and 9. The defining property, and the direct answer to Study 3R
finding F-03, is that a candidate's failure is **candidate-local**: a failure by
``RP_B1`` must never block ``RP_B2`` or ``RP_B3``.

Per candidate, in the fixed order ``RP_B1 -> RP_B2 -> RP_B3``:

1. run its CoT D2 cell;
2. run its CoT D3 cell;
3. if either CoT cell fails, mark **only that candidate** unqualified and continue;
4. if both CoT cells pass, run its E0 D2 and E0 D3 cells;
5. if either E0 cell fails, mark **only that candidate** unqualified and continue;
6. if both E0 cells pass, freeze that checkpoint as
   ``RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION`` and stop the ladder.

If no candidate qualifies the pilot stops at
``STUDY4F_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER``
without running RT, without introducing an unregistered model, and without
concluding anything about positive references, the interface or J-space in
general.

D2 and D3 are separate cells everywhere. This module never pools them.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Tuple

LADDER: Tuple[str, ...] = ("RP_B1", "RP_B2", "RP_B3")
TARGET = "RT"
DEPTHS: Tuple[str, ...] = ("D2", "D3")

#: Every terminal state Study 4F may register. Nothing outside this tuple is a
#: legal Study 4F outcome.
REGISTERED_TERMINAL_STATES: Tuple[str, ...] = (
    "STUDY4F_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION",
    "STUDY4F_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM",
    "STUDY4F_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED",
    "STUDY4F_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER",
    "STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE",
    "STUDY4F_REGISTERED_BANK_CAPACITY_UNAVAILABLE",
    "STUDY4F_PREFLIGHT_FAILED_NO_MODEL_EXECUTION",
    "STUDY4F_TERMINAL_OPERATOR_DECISION_REQUIRED",
    "STUDY4F_BLOCKED_ON_CONCURRENT_REPOSITORY_ADVANCE",
    "STUDY4F_RESTART_BLOCKED_ON_STUDY3R_CLOSURE_INTEGRITY",
)

#: The only candidate-level positive disposition Study 4F may reach. It is
#: developmental and never a confirmation.
CANDIDATE_QUALIFIED = "RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION"


class Study4FStateMachineError(RuntimeError):
    """Raised when the state machine is driven outside its registered contract."""


def _cell(results: Mapping[Tuple[str, str, str], bool], role: str, depth: str,
          route: str) -> bool:
    key = (role, depth, route)
    if key not in results:
        raise Study4FStateMachineError("missing registered cell: %r" % (key,))
    return bool(results[key])


def evaluate_candidate(role: str,
                       results: Mapping[Tuple[str, str, str], bool]
                       ) -> Dict[str, object]:
    """Run one candidate's local transitions. Never inspects another candidate."""
    cot = {depth: _cell(results, role, depth, "COT") for depth in DEPTHS}
    record: Dict[str, object] = {
        "role": role,
        "cot": dict(cot),
        "e0": {},
        "qualified": False,
        "reason": "",
        "e0_cells_run": 0,
    }
    if not all(cot.values()):
        failed = [depth for depth in DEPTHS if not cot[depth]]
        record["reason"] = "COT_HEADROOM_ABSENT_ON_%s" % ("_AND_".join(failed),)
        return record
    e0 = {depth: _cell(results, role, depth, "E0") for depth in DEPTHS}
    record["e0"] = dict(e0)
    record["e0_cells_run"] = len(DEPTHS)
    if not all(e0.values()):
        failed = [depth for depth in DEPTHS if not e0[depth]]
        record["reason"] = "E0_NOT_OBSERVED_ON_%s" % ("_AND_".join(failed),)
        return record
    record["qualified"] = True
    record["reason"] = CANDIDATE_QUALIFIED
    return record


def run_ladder(results: Mapping[Tuple[str, str, str], bool]) -> Dict[str, object]:
    """Walk the fixed ladder, stopping at the first qualified candidate."""
    candidates: List[Dict[str, object]] = []
    qualified: Optional[str] = None
    for role in LADDER:
        record = evaluate_candidate(role, results)
        candidates.append(record)
        if record["qualified"]:
            qualified = role
            break
    outcome: Dict[str, object] = {
        "candidates": candidates,
        "candidates_evaluated": len(candidates),
        "qualified_candidate": qualified,
        "rt_authorized": qualified is not None,
        "state": None,
    }
    if qualified is None:
        outcome["state"] = \
            "STUDY4F_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER"
        outcome["rt_cells_run"] = 0
    return outcome


def run_rt(results: Mapping[Tuple[str, str, str], bool]) -> Dict[str, object]:
    """Section 9. Only legal once a developmental candidate is identified."""
    cot = {depth: _cell(results, TARGET, depth, "COT") for depth in DEPTHS}
    record: Dict[str, object] = {"cot": dict(cot), "e0": {}, "state": None}
    if not all(cot.values()):
        record["state"] = "STUDY4F_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM"
        return record
    e0 = {depth: _cell(results, TARGET, depth, "E0") for depth in DEPTHS}
    record["e0"] = dict(e0)
    if not all(e0.values()):
        record["state"] = "STUDY4F_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED"
        return record
    record["state"] = \
        "STUDY4F_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION"
    return record


def run_study(results: Mapping[Tuple[str, str, str], bool]) -> Dict[str, object]:
    """The complete registered execution: ladder first, RT only if authorized."""
    outcome = run_ladder(results)
    if not outcome["rt_authorized"]:
        outcome["rt"] = None
        return outcome
    rt = run_rt(results)
    outcome["rt"] = rt
    outcome["state"] = rt["state"]
    return outcome


def state_is_registered(state: str) -> bool:
    return state in REGISTERED_TERMINAL_STATES
