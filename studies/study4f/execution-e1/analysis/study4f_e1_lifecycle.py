"""Study 4F-E1 lifecycle router and shakedown budget.

Authority: ``studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md``

Sections 7, 9 and 10. Three separate things live here, and none of them is a
reimplementation of the Study 4F state machine:

1. the nine **registered E1 terminal states**, which are the only legal
   outcomes of this successor;
2. the **remaining shakedown allowance** carried over from the original Study 4F
   disposition, which consumed 1 of 3 attempts and 0 of 6 accelerator-hours;
3. the **post-first-call freeze**, which is what makes section 9 enforceable:
   after the first study-bank model call no engineering fix, hardware switch,
   reseal or reinterpretation is permitted.

The ladder itself is *not* here. E1 executes
``studies/study4f/analysis/study4f_state_machine.py`` unchanged;
:func:`execute_registered_ladder` loads and delegates to it so there is exactly
one implementation of the registered transitions in the repository.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

#: The nine registered E1 terminal states from section 10. Nothing else is a
#: legal E1 outcome.
REGISTERED_TERMINAL_STATES: Tuple[str, ...] = (
    "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL",
    "STUDY4F_E1_QUALIFYING_ACCELERATOR_CAPACITY_UNAVAILABLE",
    "STUDY4F_E1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT",
    "STUDY4F_E1_SHAKEDOWN_FAILED_NO_STUDY_BANK_EXECUTION",
    "STUDY4F_E1_EXECUTION_INTERRUPTED_NO_REINTERPRETATION",
    "STUDY4F_E1_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER",
    "STUDY4F_E1_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM",
    "STUDY4F_E1_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED",
    "STUDY4F_E1_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION",
)

#: Blocking states registered outside section 10's terminal list.
BLOCKING_STATES: Tuple[str, ...] = (
    "STUDY4F_E1_BLOCKED_ON_STARTING_STATE_INTEGRITY",
    "STUDY4F_E1_BLOCKED_ON_CONCURRENT_REPOSITORY_ADVANCE",
    "STUDY4F_E1_INSTRUMENT_BINDING_FAILED",
    "STUDY4F_E1_TEST_DIFFERENTIAL_FAILED",
)

#: No E1 state authorizes any of these.
NEVER_AUTHORIZED_BY_ANY_STATE: Tuple[str, ...] = (
    "automatic_confirmation", "d0", "activation_capture", "patching", "study3m",
)

#: Original Study 4F consumption, read from its published shakedown disposition.
ORIGINAL_SHAKEDOWN_ATTEMPTS_USED = 1
ORIGINAL_SHAKEDOWN_ATTEMPTS_PERMITTED = 3
ORIGINAL_ACCELERATOR_HOURS_USED = 0
ORIGINAL_ACCELERATOR_HOURS_PERMITTED = 6

#: What E1 may consume: the remainder, never a fresh budget.
E1_MAX_ADDITIONAL_SHAKEDOWN_ATTEMPTS = 2
E1_MAX_TOTAL_ACCELERATOR_HOURS = 6

#: Section 7 white list. Anything outside it is a non-white-listed defect.
WHITE_LISTED_FIXES: Tuple[str, ...] = (
    "driver_or_container_compatibility",
    "dependency_installation",
    "paths_and_permissions",
    "networking_for_public_checkpoint_acquisition",
    "serialization",
    "logging",
    "crash_recovery",
    "azure_deployment_mechanics",
)

#: Section 7 values that may never change, under any fix.
IMMUTABLE_DECISION_BEARING_VALUES: Tuple[str, ...] = (
    "checkpoint", "revision", "dtype", "hardware_selection_rule", "task",
    "bank", "prompt", "parser", "decoding_configuration", "threshold", "alpha",
    "pass_boundary", "state_transition", "claim_language",
)

SHAKEDOWN_FAILED_STATE = "STUDY4F_E1_SHAKEDOWN_FAILED_NO_STUDY_BANK_EXECUTION"
INTERRUPTED_STATE = "STUDY4F_E1_EXECUTION_INTERRUPTED_NO_REINTERPRETATION"


class Study4FE1LifecycleError(RuntimeError):
    """Raised when the successor is driven outside its registered contract."""


def state_is_registered(state: str) -> bool:
    return state in REGISTERED_TERMINAL_STATES


def require_registered_state(state: str) -> str:
    if not state_is_registered(state):
        raise Study4FE1LifecycleError("unregistered E1 terminal state: %r"
                                      % (state,))
    return state


def remaining_allowance(attempts_used: int, accelerator_hours_used: float
                        ) -> Dict[str, object]:
    """Remaining shakedown budget. Both ceilings are hard."""
    if attempts_used < 0 or accelerator_hours_used < 0:
        raise Study4FE1LifecycleError("consumption cannot be negative")
    attempts_left = E1_MAX_ADDITIONAL_SHAKEDOWN_ATTEMPTS - attempts_used
    hours_left = E1_MAX_TOTAL_ACCELERATOR_HOURS - accelerator_hours_used
    exhausted = attempts_left <= 0 or hours_left <= 0
    return {
        "original_attempts_used": ORIGINAL_SHAKEDOWN_ATTEMPTS_USED,
        "e1_additional_attempts_permitted": E1_MAX_ADDITIONAL_SHAKEDOWN_ATTEMPTS,
        "e1_attempts_used": attempts_used,
        "e1_attempts_remaining": max(attempts_left, 0),
        "total_accelerator_hours_permitted": E1_MAX_TOTAL_ACCELERATOR_HOURS,
        "accelerator_hours_used": accelerator_hours_used,
        "accelerator_hours_remaining": max(hours_left, 0),
        "exhausted": exhausted,
        "state_when_exhausted_without_a_pass": SHAKEDOWN_FAILED_STATE,
    }


def fix_is_white_listed(fix: str) -> bool:
    return fix in WHITE_LISTED_FIXES


def classify_fixes(fixes: Sequence[str]) -> Dict[str, object]:
    """Split proposed shakedown fixes into white-listed and refused."""
    refused = [fix for fix in fixes if not fix_is_white_listed(fix)]
    return {
        "applied": [fix for fix in fixes if fix_is_white_listed(fix)],
        "refused": refused,
        "non_white_listed_defect_found": bool(refused),
        "state_if_refused": SHAKEDOWN_FAILED_STATE if refused else None,
    }


def post_first_call_freeze(first_study_bank_call_made: bool) -> Dict[str, bool]:
    """Section 9. After the first study-bank call the instrument is frozen."""
    frozen = bool(first_study_bank_call_made)
    return {
        "first_study_bank_call_made": frozen,
        "engineering_fix_permitted": not frozen,
        "hardware_switch_permitted": not frozen,
        "reseal_permitted": not frozen,
        "parser_or_output_reinterpretation_permitted": False,
        "cell_repetition_because_unfavorable_permitted": False,
        "resume_only_through_the_sealed_create_only_journal": frozen,
    }


def resume_is_legal(journal: Mapping[str, object], item_id: str) -> bool:
    """A create-only journal resume may never duplicate or replace an item."""
    completed = set(journal.get("completed_item_ids") or ())
    return item_id not in completed


def load_registered_state_machine(repo_root: Path):
    """Import the published Study 4F state machine unchanged."""
    path = (repo_root / "studies" / "study4f" / "analysis" /
            "study4f_state_machine.py")
    spec = importlib.util.spec_from_file_location(
        "study4f_e1_bound_state_machine", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise Study4FE1LifecycleError("cannot load the predecessor state machine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


#: Study 4F terminal state -> the E1 state that reports the same outcome.
_STUDY4F_TO_E1 = {
    "STUDY4F_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER":
        "STUDY4F_E1_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER",
    "STUDY4F_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM":
        "STUDY4F_E1_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM",
    "STUDY4F_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED":
        "STUDY4F_E1_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED",
    "STUDY4F_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION":
        "STUDY4F_E1_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION",
}


def translate_study4f_state(state: str) -> str:
    """Report a Study 4F outcome under its E1 name without altering it."""
    if state not in _STUDY4F_TO_E1:
        raise Study4FE1LifecycleError(
            "Study 4F state %r has no registered E1 execution outcome" % (state,))
    return _STUDY4F_TO_E1[state]


def execute_registered_ladder(repo_root: Path,
                              results: Mapping[Tuple[str, str, str], bool],
                              *, execution_authorized: bool) -> Dict[str, object]:
    """Run the *existing* Study 4F state machine exactly once, unaltered.

    ``execution_authorized`` is the sealed-commit gate: developmental execution
    authorization is false until the E1 seal is published, and this function
    refuses to run before then.
    """
    if not execution_authorized:
        raise Study4FE1LifecycleError(
            "developmental execution is not authorized until the E1 execution "
            "seal is published")
    machine = load_registered_state_machine(repo_root)
    outcome = dict(machine.run_study(results))
    study4f_state = outcome.get("state")
    outcome["study4f_state"] = study4f_state
    outcome["state"] = translate_study4f_state(str(study4f_state))
    outcome["registered_transitions_altered"] = False
    return outcome


def interrupted(reason: str) -> Dict[str, object]:
    """Section 9. An interruption is never a licence to reinterpret."""
    return {
        "state": INTERRUPTED_STATE,
        "reason": reason,
        "reinterpretation_permitted": False,
        "reseal_permitted": False,
        "completed_items_replaced": 0,
        "completed_items_duplicated": 0,
    }


def authorization_flags(state: str) -> Dict[str, bool]:
    """No registered state authorizes confirmation, D0, capture, patching or 3M."""
    require_registered_state(state)
    return {
        "automatic_confirmation_authorized": False,
        "d0_authorized": False,
        "activation_capture_authorized": False,
        "activation_patching_authorized": False,
        "study3m_authorized": False,
    }


def claim_ceiling() -> Dict[str, bool]:
    """Section 14. The scientific claim ceiling, stated as refusals."""
    return {
        "claims_j_space_exists": False,
        "claims_j_space_does_not_exist": False,
        "claims_j_space_is_observable": False,
        "claims_j_space_is_unobservable": False,
        "claims_rp_b_confirmed": False,
        "claims_any_result_generalizes": False,
        "is_a_scientific_result": False,
    }


def final_state(*, quota_sufficient: bool,
                capacity_found: Optional[bool] = None,
                preflight_passed: Optional[bool] = None,
                shakedown_passed: Optional[bool] = None,
                interrupted_execution: bool = False,
                ladder_state: Optional[str] = None) -> str:
    """Route the registered branches to exactly one E1 terminal state."""
    if not quota_sufficient:
        return "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL"
    if capacity_found is False:
        return "STUDY4F_E1_QUALIFYING_ACCELERATOR_CAPACITY_UNAVAILABLE"
    if preflight_passed is False:
        return "STUDY4F_E1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT"
    if shakedown_passed is False:
        return SHAKEDOWN_FAILED_STATE
    if interrupted_execution:
        return INTERRUPTED_STATE
    if ladder_state is None:
        raise Study4FE1LifecycleError(
            "an executed successor must report a ladder outcome")
    return require_registered_state(ladder_state)
