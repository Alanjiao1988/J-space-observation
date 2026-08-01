"""Live execution/access ledger for the parser-v3-v2 set-repair lifecycle.

Phase 1.2H. The Phase 1.2G acceptance policy is ``FINAL`` and carries an
``execution_state`` block. That block was correct when it was written and it
must not become a live counter: an artifact that states the rule for judging a
future evaluation should not also be the place where "how many things have
happened so far" is edited. Mixing the two invites exactly the failure this
repository has hit before, where a semantic change is smuggled in as a routine
state update, and where a stale counter silently contradicts a live one.

This module separates the two concerns:

*policy semantics*
    Immutable for the round. Bound here by the policy's full-file SHA-256 and,
    independently, by a ``policy_semantics_sha256`` computed over the policy
    with ``execution_state`` projected out. The second hash is the load-bearing
    one: it is stable across any future licensed execution-state edit, so a
    semantic change cannot hide behind one.

*live execution and access state*
    Mutable, append-only, role-scoped. Counters may rise and never fall.
    Events may be appended and never removed or rewritten.

The distinctions the ledger is required to preserve are deliberately explicit
rather than implied by a single "accessed" flag:

* retired ``parser-v3-v1`` **repair** access is not formal ``parser-v3-v2``
  **evaluation** access;
* a **byte-only integrity verification** (streaming a file to a digest and
  discarding the bytes) is not a **semantic content read**;
* set construction, sealing, preregistration, prediction generation, opening
  labels for scoring and running a formal evaluation are six different things
  and get six different counters.

A single boolean "accessed" field cannot express any of that, and the history
of this repository is that collapsed flags get restated later as stronger
claims than the evidence supports.

Nothing here reads a private set, a sealed blob or a locked label. This module
introduces no new parser dependency: it references no parser symbol and invokes
no parser. That is narrower than "no parser module is loaded", and the
difference is deliberate --- ``jspace_observation/__init__.py`` eagerly imports
the legacy parser, so importing this module *through the package* does place
parser code in ``sys.modules``. The supportable and tested claim is
differential.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

__all__ = [
    "LedgerError",
    "LEDGER_SCHEMA_VERSION",
    "SEMANTIC_PROJECTION_EXCLUDES",
    "COUNTER_GROUPS",
    "TERMINAL_STATES",
    "BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE",
    "COUNTER_PROVENANCE_CLASSES",
    "EVENT_KINDS",
    "policy_semantics_sha256",
    "validate_ledger",
    "assert_monotonic_succession",
    "counter_value",
]


class LedgerError(Exception):
    """Raised when a ledger is structurally or semantically invalid."""


LEDGER_SCHEMA_VERSION = "phase1-parser-v3-v2-execution-access-ledger/v1"

#: Keys projected out of the policy before computing ``policy_semantics_sha256``.
#:
#: Nothing is excluded at the top level. Audit G finding G-04: excluding the
#: whole ``execution_state`` block also excluded its free-text
#: ``final_policy_is_not_a_result`` statement, so that statement could be
#: rewritten to assert "a formal evaluation was run and parser v3 was
#: validated" without changing the semantic hash. Only the mutable integer
#: counters are projected out --- see
#: :data:`SEMANTIC_PROJECTION_COUNTER_EXCLUDES` --- because those are what a
#: future licensed execution-state edit legitimately touches. Everything else,
#: including the prose claim, is inside the hash.
SEMANTIC_PROJECTION_EXCLUDES: tuple[str, ...] = ()

#: Counters inside ``execution_state`` that a future licensed edit may change
#: without that being a semantic change to the policy.
SEMANTIC_PROJECTION_COUNTER_EXCLUDES: tuple[str, ...] = (
    "formal_evaluation_ordinal",
    "locked_label_reads",
    "parser_v3_runs_against_any_locked_set",
    "parser_v3_v2_sealed_sets_constructed",
    "predictions_generated",
)

#: The cumulative ``byte_only_integrity_verifications`` a ledger must carry
#: once the Phase 1.2H-R1 access gate has completed: the 2 verifications
#: already on record before R1, plus the 12 authoritative objects the gate
#: streams. It is a floor rather than an equality so that a later authorised
#: byte-only round can add to it without this constant needing to move.
BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE: int = 14

#: Terminal states this ledger may record. They are exactly the Phase 1.2H
#: terminal states; a ledger may not invent a state that the protocol does not
#: define, because a novel state name is how a blocked round gets described as
#: something better than it was.
#:
#: Audit C (C-07) found three vocabularies in circulation: this one, a protocol
#: table naming ``PRIVATE_SOURCE_ACCESS_RESTORED``, and
#: ``classify_terminal_state`` returning
#: ``READY_FOR_SEPARATELY_AUTHORISED_PRIVATE_REVIEW`` --- with the latter two
#: absent here, so the boundary instrument could produce a state this validator
#: would reject. This set is now the single vocabulary: the protocol table was
#: rewritten to match it, and
#: ``tests/test_phase1_2h_r1_review_boundary.py`` asserts that every state
#: ``classify_terminal_state`` can return is a member. The assertion lives in a
#: test rather than in a runtime import because the boundary instrument must not
#: import this package: ``jspace_observation/__init__`` eagerly imports the
#: legacy parser, and that would place parser code in the instrument's process.
TERMINAL_STATES: frozenset[str] = frozenset(
    {
        "IN_PROGRESS",
        "SEALED_READY_FOR_PREREGISTRATION",
        "BLOCKED_ON_PRIVATE_SOURCE_ACCESS",
        "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY",
        "BLOCKED_ON_INDEPENDENCE",
        "BLOCKED_ON_SET_REPAIR",
        "BLOCKED_ON_SEALING",
        "READY_FOR_SEPARATELY_AUTHORISED_PRIVATE_REVIEW",
    }
)

#: Every counter the ledger carries, grouped by role scope. The grouping is the
#: point: ``retired_v1_repair_access`` and ``formal_v2_evaluation_access`` are
#: different groups so that a repair read can never be reported as, or confused
#: with, an evaluation read.
COUNTER_GROUPS: Mapping[str, tuple[str, ...]] = {
    "retired_v1_repair_access": (
        "sealed_input_semantic_reads",
        "sealed_label_semantic_reads",
        "private_curator_files_read",
        "byte_only_integrity_verifications",
        "labels_opened_for_scoring",
    ),
    "formal_v2_evaluation_access": (
        "sealed_input_semantic_reads",
        "sealed_label_semantic_reads",
        "labels_opened_for_scoring",
        "formal_evaluations_run",
        "preregistrations_completed",
    ),
    "v2_construction": (
        "candidate_cases_constructed",
        "candidate_cases_reviewed",
        "replacement_candidates_generated",
        "sets_sealed",
        "listing_witnesses_obtained",
        "final_contracts_compiled",
    ),
    "parser_execution": (
        "parser_invocations_on_private_or_locked_data",
        "candidate_predictions_generated",
        "comparator_predictions_generated",
    ),
    "azure": (
        "control_plane_reads",
        "data_plane_content_reads",
        "data_plane_writes",
        "resource_creations_or_changes",
        "job_executions",
    ),
}

#: Event kinds the ledger accepts. A closed vocabulary keeps a future round
#: from inventing a reassuring-sounding event that no validator understands.
EVENT_KINDS: frozenset[str] = frozenset(
    {
        "baseline_verification",
        "byte_only_integrity_verification",
        "source_authentication_attempt",
        "retired_v1_semantic_read",
        "private_curator_file_read",
        "v2_case_construction",
        "v2_case_review",
        "seal_write",
        "listing_witness",
        "final_contract_compilation",
        "parser_invocation",
        "prediction_generation",
        "formal_evaluation",
        "terminal_determination",
        "record_correction",
    }
)

#: ``record_correction`` exists because prior events are immutable --- see
#: :func:`assert_monotonic_succession` --- and an immutable record with no way
#: to record that one of its entries was wrong is a record that has to choose
#: between being tamper-evident and being accurate.
#:
#: Audit C found two defects in the text of committed event 8: it cited
#: "protocol section 12.3", which does not exist, and it made a
#: *subscription*-scoped negative claim from *resource-group and region*-scoped
#: evidence. Rewriting the event would have destroyed the property that makes
#: the ledger evidence. This kind appends the correction instead, so both the
#: original claim and its correction remain readable.
#:
#: A correction event must name what it corrects. It never licenses a counter
#: change: if the underlying facts changed rather than their description, that
#: is a new observation and needs the event kind for that observation.
CORRECTION_EVENT_KIND: str = "record_correction"

#: A citation a reader can follow: a repository path with a recognised
#: extension, or a function/identifier named with enough specificity to locate.
#: Deliberately permissive about *what* is cited and strict about *whether*
#: anything is.
_CITATION_PATTERN = re.compile(
    r"(?:[\w./-]+\.(?:json|py|md|ya?ml|txt))|(?:\b\w+\(\))"
)

#: A committed Phase 1.2H-R1 access receipt, by path. Narrower than
#: :data:`_CITATION_PATTERN` on purpose: the boundary terminal state may only be
#: earned by citing a receipt, not by citing any file at all.
_RECEIPT_CITATION_PATTERN = re.compile(
    r"docs/phase1_2h_r1_access_receipt[\w.-]*\.json"
)

_REQUIRED_TOP_LEVEL: tuple[str, ...] = (
    "schema_version",
    "ledger_id",
    "phase",
    "status",
    "policy_binding",
    "phase_1_2g_finalization_snapshot",
    "live_counters",
    "counter_provenance",
    "events",
    "retired_v1_state",
    "successor_set_state",
)

#: The ledger's closed top-level key set. Audit G showed that an open top level
#: lets a round add a reassuring-sounding block that no validator reads, so an
#: unknown key is an error rather than ignored decoration.
LEDGER_KEYS: frozenset[str] = frozenset(
    _REQUIRED_TOP_LEVEL + ("purpose", "counter_semantics")
)

#: Closed key set for ``counter_provenance``, whose job is to say which
#: counters are machine-derived and which an operator maintains by hand.
#:
#: Phase 1.2H-R1 added it because the round produced both kinds at once: the
#: data-plane and semantic-read counters come from a schema-validated execution
#: receipt, while the count of ``az`` calls an operator made over an interactive
#: session does not and cannot. Recording both without distinguishing them
#: would let a hand-maintained number be cited with the authority of a receipt.
#: The block is validated rather than decorative --- see
#: :func:`_validate_counter_provenance` --- so it cannot drift out of step with
#: the counters it describes.
#:
#: Audit C (C-03) found the block *optional*: ``validate_ledger`` only checked
#: it if present, so deleting the entire control left a valid ledger and the
#: distinction it exists to draw simply disappeared. It is required now, listed
#: in :data:`_REQUIRED_TOP_LEVEL`.
COUNTER_PROVENANCE_CLASSES: tuple[str, ...] = (
    "receipt_derived_exact",
    "azure_verified_exact",
    "structurally_zero_by_source_analysis",
    "operator_maintained_approximate",
)

#: What each provenance class asserts, and what would have to be true for the
#: assertion to hold. Audit C (C-04) found two counters classified as
#: ``receipt_derived_exact`` when the receipt has no corresponding field, and
#: five described as "in-process instrumentation" when they are literals the
#: emitting program writes. The distinction those findings turn on is between a
#: number *read back* from a machine artifact and a number whose value is a
#: property of the *code*, so the second now has a class of its own rather than
#: borrowing the authority of the first.
COUNTER_PROVENANCE_CLASS_MEANING: Mapping[str, str] = {
    "receipt_derived_exact": (
        "the value appears as a field in a committed, schema-validated "
        "execution receipt and was copied from it"
    ),
    "azure_verified_exact": (
        "the value was observed from an Azure control-plane response that is "
        "committed to the repository"
    ),
    "structurally_zero_by_source_analysis": (
        "the value is zero because no code path that could increment it exists, "
        "which an AST check over the emitting source enforces; it is not a "
        "measurement of a run"
    ),
    "operator_maintained_approximate": (
        "the value is a hand-maintained count and carries no machine evidence; "
        "it may only be used for counters whose value is not a safety claim"
    ),
}

#: Counters whose value is a safety claim, and which therefore may never be
#: classified as operator-maintained. A round may not assert "no semantic read
#: occurred" on the strength of someone's recollection.
#:
#: Audit C (C-03) found four safety counters missing from this set, including
#: both ``formal_v2_evaluation_access`` semantic-read counters --- so a ledger
#: could have asserted that no locked label had been opened for scoring, on no
#: evidence at all.
_MACHINE_EVIDENCE_REQUIRED: frozenset[str] = frozenset(
    {
        "retired_v1_repair_access.sealed_input_semantic_reads",
        "retired_v1_repair_access.sealed_label_semantic_reads",
        "retired_v1_repair_access.private_curator_files_read",
        "retired_v1_repair_access.byte_only_integrity_verifications",
        "retired_v1_repair_access.labels_opened_for_scoring",
        "formal_v2_evaluation_access.sealed_input_semantic_reads",
        "formal_v2_evaluation_access.sealed_label_semantic_reads",
        "azure.data_plane_content_reads",
        "azure.data_plane_writes",
        "parser_execution.parser_invocations_on_private_or_locked_data",
        "parser_execution.candidate_predictions_generated",
        "parser_execution.comparator_predictions_generated",
    }
)

#: Closed key set for the retired-v1 state block, with the type each key takes.
RETIRED_V1_STATE_KEYS: Mapping[str, type | tuple[type, ...]] = {
    "set_id": str,
    "sealed_bytes_unchanged": bool,
    "repair_input_content_accessed": bool,
    "repair_label_content_accessed": bool,
    "repair_access_purpose": str,
    "formal_evaluation_ever_run": bool,
    "prediction_streams_generated_against_v1": int,
    "labels_opened_for_scoring": int,
    "formally_scorable": bool,
    "formal_eligibility": str,
    "current_state_label": str,
    "current_state_note": str,
}

#: Closed key set for the successor-set state block.
SUCCESSOR_SET_STATE_KEYS: Mapping[str, type | tuple[type, ...]] = {
    "set_id": str,
    "exists": bool,
    "cases_constructed": int,
    "sealed": bool,
    "sealed_object_count": (int, type(None)),
    "sealed_object_count_note": str,
    "preregistered": bool,
    "formal_evaluation_ordinal": int,
}

#: The canonical retired-v1 state label. It is pinned so that a later round
#: cannot soften or re-word it while leaving every other check green.
RETIRED_V1_STATE_LABEL = "SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE"

#: Closed key set for a ledger event. ``corrects`` is present only on
#: ``record_correction`` events, where it is mandatory: a correction that does
#: not say what it corrects is just another claim.
EVENT_KEYS: frozenset[str] = frozenset(
    {"sequence", "kind", "role", "summary", "private_content_read", "corrects"}
)

#: Event kinds that read private content by definition. Declaring one of these
#: with ``private_content_read: false`` is a contradiction, not a nuance.
INHERENTLY_PRIVATE_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "retired_v1_semantic_read",
        "private_curator_file_read",
        "v2_case_review",
    }
)

#: Event kinds Phase 1.2H never authorises. Their presence is an error even if
#: every counter were somehow adjusted to match.
PHASE_FORBIDDEN_EVENT_KINDS: frozenset[str] = frozenset(
    {"parser_invocation", "prediction_generation", "formal_evaluation"}
)

#: Each entry maps an event kind to the counters that must account for it. An
#: event asserting an access that no counter records is the exact shape of the
#: defect Audit G demonstrated.
_EVENT_COUNTER_SUPPORT: Mapping[str, tuple[tuple[str, str], ...]] = {
    "retired_v1_semantic_read": (
        ("retired_v1_repair_access", "sealed_input_semantic_reads"),
        ("retired_v1_repair_access", "sealed_label_semantic_reads"),
    ),
    "private_curator_file_read": (
        ("retired_v1_repair_access", "private_curator_files_read"),
    ),
    "byte_only_integrity_verification": (
        ("retired_v1_repair_access", "byte_only_integrity_verifications"),
    ),
    "v2_case_construction": (("v2_construction", "candidate_cases_constructed"),),
    "v2_case_review": (("v2_construction", "candidate_cases_reviewed"),),
    "seal_write": (("v2_construction", "sets_sealed"),),
    "listing_witness": (("v2_construction", "listing_witnesses_obtained"),),
    "final_contract_compilation": (("v2_construction", "final_contracts_compiled"),),
}

_REQUIRED_POLICY_BINDING: tuple[str, ...] = (
    "policy_path",
    "policy_sha256",
    "policy_schema_version",
    "policy_status",
    "policy_bytes_modified_this_round",
    "policy_semantics_sha256",
    "semantic_projection_excludes",
    "semantic_projection_counter_excludes",
)

# A ledger sentence that describes ``execution_state`` as projected out of the
# semantic hash. Audit G's blocker was a narrated field drifting away from the
# validated field beside it, and the projection note is exactly such a field:
# after the projection narrowed to the five counters, a note still claiming the
# whole block is excluded understates what the hash protects.
_BLOCK_PROJECTION_CLAIM = re.compile(
    r"execution_state[^.]{0,40}?\b(?:projected\s+out|excluded|removed)\b"
    r"|\b(?:projects?|projected|projecting|excludes?|excluded|excluding|"
    r"removes?|removed)\b[^.]{0,40}?execution_state",
    re.IGNORECASE,
)

# Wording that makes such a sentence legitimate: it either names the counters,
# or it is describing a design that is explicitly recorded as superseded.
_PROJECTION_CLAIM_QUALIFIERS = re.compile(
    r"\bcounters?\b|\brejected\b|\bearlier\s+design\b|\bno\s+longer\b"
    r"|\bpreviously\b|\bsuperseded\b|\bused\s+to\b",
    re.IGNORECASE,
)


def _validate_projection_prose(binding: Mapping[str, Any]) -> None:
    """Reject free text that overstates what the semantic projection removes."""

    if SEMANTIC_PROJECTION_EXCLUDES:
        return
    for key, value in sorted(binding.items()):
        if not isinstance(value, str):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", value):
            if not _BLOCK_PROJECTION_CLAIM.search(sentence):
                continue
            if _PROJECTION_CLAIM_QUALIFIERS.search(sentence):
                continue
            raise LedgerError(
                f"policy_binding.{key} describes execution_state as projected "
                "out of the semantic hash, but the projection removes only "
                f"{list(SEMANTIC_PROJECTION_COUNTER_EXCLUDES)}. Say which "
                "counters are excluded, or mark the sentence as describing a "
                f"superseded design: {sentence!r}"
            )


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def policy_semantics_sha256(policy: Mapping[str, Any]) -> str:
    """Return the SHA-256 of the policy's *semantic projection*.

    The projection removes exactly :data:`SEMANTIC_PROJECTION_EXCLUDES` at the
    top level and :data:`SEMANTIC_PROJECTION_COUNTER_EXCLUDES` inside
    ``execution_state``, then serialises canonically. Two policies that differ
    only in their embedded execution-state *counters* therefore hash
    identically, while any change to a threshold, gate, ontology entry,
    population figure, comparator role, status rule or to the
    ``final_policy_is_not_a_result`` statement changes the hash.
    """

    if not isinstance(policy, Mapping):
        raise LedgerError("policy must be a mapping")
    projected: dict[str, Any] = {}
    for key, value in policy.items():
        if key in SEMANTIC_PROJECTION_EXCLUDES:
            continue
        if key == "execution_state" and isinstance(value, Mapping):
            value = {
                inner: item
                for inner, item in value.items()
                if inner not in SEMANTIC_PROJECTION_COUNTER_EXCLUDES
            }
        projected[key] = value
    return hashlib.sha256(_canonical(projected).encode("utf-8")).hexdigest()


def _is_count(value: Any) -> bool:
    """True only for a genuine non-negative ``int``.

    ``bool`` is rejected explicitly. In Python ``isinstance(True, int)`` is
    ``True``, so a plain ``int`` check would silently accept ``False`` as zero
    and ``True`` as one --- which is precisely how a "no access occurred"
    assertion could be written as a boolean and then counted as a number.
    """

    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def counter_value(ledger: Mapping[str, Any], group: str, name: str) -> int:
    """Return one counter, raising if the group or counter is absent."""

    counters = ledger.get("live_counters")
    if not isinstance(counters, Mapping):
        raise LedgerError("live_counters must be a mapping")
    scope = counters.get(group)
    if not isinstance(scope, Mapping):
        raise LedgerError(f"live_counters.{group} must be a mapping")
    if name not in scope:
        raise LedgerError(f"live_counters.{group}.{name} is missing")
    value = scope[name]
    if not _is_count(value):
        raise LedgerError(
            f"live_counters.{group}.{name} must be a non-negative int, "
            f"got {value!r}"
        )
    return int(value)


def _validate_policy_binding(
    binding: Any, policy: Mapping[str, Any] | None, policy_sha256: str | None
) -> None:
    if not isinstance(binding, Mapping):
        raise LedgerError("policy_binding must be a mapping")
    for key in _REQUIRED_POLICY_BINDING:
        if key not in binding:
            raise LedgerError(f"policy_binding.{key} is missing")

    excludes = binding["semantic_projection_excludes"]
    if not isinstance(excludes, Sequence) or isinstance(excludes, (str, bytes)):
        raise LedgerError("policy_binding.semantic_projection_excludes must be a list")
    if tuple(excludes) != SEMANTIC_PROJECTION_EXCLUDES:
        raise LedgerError(
            "policy_binding.semantic_projection_excludes must be exactly "
            f"{list(SEMANTIC_PROJECTION_EXCLUDES)}; a ledger that projects out "
            "more than the licensed execution-state counters would hide a "
            "semantic change"
        )

    counter_excludes = binding["semantic_projection_counter_excludes"]
    if not isinstance(counter_excludes, Sequence) or isinstance(
        counter_excludes, (str, bytes)
    ):
        raise LedgerError(
            "policy_binding.semantic_projection_counter_excludes must be a list"
        )
    if tuple(counter_excludes) != SEMANTIC_PROJECTION_COUNTER_EXCLUDES:
        raise LedgerError(
            "policy_binding.semantic_projection_counter_excludes must be exactly "
            f"{list(SEMANTIC_PROJECTION_COUNTER_EXCLUDES)}; the prose statement "
            "in execution_state is deliberately inside the semantic hash"
        )

    _validate_projection_prose(binding)

    modified = binding["policy_bytes_modified_this_round"]
    if not isinstance(modified, bool):
        raise LedgerError(
            "policy_binding.policy_bytes_modified_this_round must be a bool"
        )

    if policy_sha256 is not None and binding["policy_sha256"] != policy_sha256:
        raise LedgerError(
            "policy_binding.policy_sha256 does not match the policy file: "
            f"declared {binding['policy_sha256']}, actual {policy_sha256}"
        )

    if policy is not None:
        expected = policy_semantics_sha256(policy)
        if binding["policy_semantics_sha256"] != expected:
            raise LedgerError(
                "policy_binding.policy_semantics_sha256 does not match the "
                f"policy semantic projection: declared "
                f"{binding['policy_semantics_sha256']}, actual {expected}"
            )
        if binding["policy_schema_version"] != policy.get("schema_version"):
            raise LedgerError(
                "policy_binding.policy_schema_version does not match the policy"
            )
        if binding["policy_status"] != policy.get("status"):
            raise LedgerError("policy_binding.policy_status does not match the policy")


def _validate_snapshot(snapshot: Any, policy: Mapping[str, Any] | None) -> None:
    if not isinstance(snapshot, Mapping):
        raise LedgerError("phase_1_2g_finalization_snapshot must be a mapping")
    if "role" not in snapshot:
        raise LedgerError("phase_1_2g_finalization_snapshot.role is missing")
    role = snapshot["role"]
    if not isinstance(role, str) or "snapshot" not in role.lower():
        raise LedgerError(
            "phase_1_2g_finalization_snapshot.role must describe the block as a "
            "snapshot, so it cannot be mistaken for live state"
        )
    if "values" not in snapshot:
        raise LedgerError("phase_1_2g_finalization_snapshot.values is missing")
    if policy is not None:
        declared = snapshot["values"]
        actual = policy.get("execution_state")
        if declared != actual:
            raise LedgerError(
                "phase_1_2g_finalization_snapshot.values must reproduce the "
                "policy's execution_state block exactly; it is a snapshot of "
                "that block, not an independent restatement of it"
            )


def _validate_counters(counters: Any) -> None:
    if not isinstance(counters, Mapping):
        raise LedgerError("live_counters must be a mapping")
    unknown = set(counters) - set(COUNTER_GROUPS)
    if unknown:
        raise LedgerError(f"live_counters has unknown groups: {sorted(unknown)}")
    for group, names in COUNTER_GROUPS.items():
        if group not in counters:
            raise LedgerError(f"live_counters.{group} is missing")
        scope = counters[group]
        if not isinstance(scope, Mapping):
            raise LedgerError(f"live_counters.{group} must be a mapping")
        extra = set(scope) - set(names)
        if extra:
            raise LedgerError(
                f"live_counters.{group} has unknown counters: {sorted(extra)}"
            )
        for name in names:
            counter_value({"live_counters": counters}, group, name)


def _validate_events(events: Any) -> list[Mapping[str, Any]]:
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        raise LedgerError("events must be a list")
    seen: set[int] = set()
    ordered: list[Mapping[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise LedgerError(f"events[{index}] must be a mapping")
        for key in ("sequence", "kind", "role", "summary", "private_content_read"):
            if key not in event:
                raise LedgerError(f"events[{index}].{key} is missing")
        unknown = set(event) - EVENT_KEYS
        if unknown:
            raise LedgerError(
                f"events[{index}] has unknown keys: {sorted(unknown)}; the event "
                "schema is closed so an unvalidated field cannot ride along"
            )
        sequence = event["sequence"]
        if not _is_count(sequence):
            raise LedgerError(f"events[{index}].sequence must be a non-negative int")
        if sequence in seen:
            raise LedgerError(f"events[{index}].sequence {sequence} is duplicated")
        seen.add(int(sequence))
        if index and int(sequence) <= int(events[index - 1]["sequence"]):
            raise LedgerError(
                f"events[{index}].sequence must strictly increase; an "
                "out-of-order or rewritten event is indistinguishable from a "
                "deleted one"
            )
        kind = event["kind"]
        if kind not in EVENT_KINDS:
            raise LedgerError(f"events[{index}].kind {kind!r} is not a known kind")
        if kind in PHASE_FORBIDDEN_EVENT_KINDS:
            raise LedgerError(
                f"events[{index}].kind {kind!r} is not authorised in Phase 1.2H; "
                "this phase runs no parser, generates no prediction and performs "
                "no formal evaluation"
            )
        if not isinstance(event["private_content_read"], bool):
            raise LedgerError(
                f"events[{index}].private_content_read must be a bool"
            )
        if kind in INHERENTLY_PRIVATE_EVENT_KINDS and not event[
            "private_content_read"
        ]:
            raise LedgerError(
                f"events[{index}].kind {kind!r} reads private content by "
                "definition, so private_content_read cannot be false"
            )
        if not isinstance(event["role"], str) or not event["role"].strip():
            raise LedgerError(f"events[{index}].role must be a non-empty string")
        if not isinstance(event["summary"], str) or not event["summary"].strip():
            raise LedgerError(f"events[{index}].summary must be a non-empty string")
        _validate_correction_event(event, index, events)
        ordered.append(event)
    return ordered


def _validate_correction_event(
    event: Mapping[str, Any], index: int, events: Sequence[Mapping[str, Any]]
) -> None:
    """Constrain ``record_correction`` events and forbid ``corrects`` elsewhere.

    A correction must identify an *earlier* event that actually exists. Allowing
    it to point forward, at itself, or at nothing would let a round attach the
    word "corrected" to a claim without any prior claim being amended --- which
    reads as diligence while asserting nothing.
    """

    kind = event["kind"]
    if kind != CORRECTION_EVENT_KIND:
        if "corrects" in event:
            raise LedgerError(
                f"events[{index}].corrects is only meaningful on "
                f"{CORRECTION_EVENT_KIND!r} events, not {kind!r}"
            )
        return

    if "corrects" not in event:
        raise LedgerError(
            f"events[{index}] is a {CORRECTION_EVENT_KIND!r} but names no "
            "corrected event; a correction that does not say what it corrects "
            "is only a further claim"
        )
    target = event["corrects"]
    if not _is_count(target):
        raise LedgerError(
            f"events[{index}].corrects must be a non-negative int sequence number"
        )
    target = int(target)
    if target >= int(event["sequence"]):
        raise LedgerError(
            f"events[{index}].corrects {target} does not precede this event; a "
            "correction cannot amend the present or the future"
        )
    earlier_by_sequence = {
        int(prior["sequence"]): prior for prior in events[:index]
    }
    if target not in earlier_by_sequence:
        raise LedgerError(
            f"events[{index}].corrects {target} matches no earlier event"
        )
    if earlier_by_sequence[target]["kind"] == CORRECTION_EVENT_KIND:
        raise LedgerError(
            f"events[{index}].corrects {target}, which is itself a correction; "
            "amend the original record rather than chaining corrections"
        )


def _validate_event_counter_support(
    ledger: Mapping[str, Any], events: Sequence[Mapping[str, Any]]
) -> None:
    """Require every recorded access event to be accounted for by a counter.

    Audit G appended a ``retired_v1_semantic_read`` event to a ledger whose
    semantic-read counters were both zero, and the ledger validated. An event
    is a claim about what happened; a counter is the tally of the same thing.
    If the two can disagree, neither is evidence.
    """

    tally: dict[str, int] = {}
    for event in events:
        tally[event["kind"]] = tally.get(event["kind"], 0) + 1

    for kind, counters in _EVENT_COUNTER_SUPPORT.items():
        occurrences = tally.get(kind, 0)
        if not occurrences:
            continue
        total = sum(counter_value(ledger, group, name) for group, name in counters)
        if total < occurrences:
            joined = ", ".join(f"{group}.{name}" for group, name in counters)
            raise LedgerError(
                f"{occurrences} {kind!r} event(s) are recorded but the "
                f"supporting counters ({joined}) total {total}; an event that "
                "no counter accounts for is an unsupported access claim"
            )

    private_events = sum(
        1 for event in events if event.get("private_content_read") is True
    )
    if private_events:
        private_total = (
            counter_value(
                ledger, "retired_v1_repair_access", "sealed_input_semantic_reads"
            )
            + counter_value(
                ledger, "retired_v1_repair_access", "sealed_label_semantic_reads"
            )
            + counter_value(
                ledger, "retired_v1_repair_access", "private_curator_files_read"
            )
            + counter_value(ledger, "v2_construction", "candidate_cases_reviewed")
        )
        if private_total < private_events:
            raise LedgerError(
                f"{private_events} event(s) declare private_content_read=true but "
                f"the private-access counters total {private_total}; private "
                "access cannot be narrated without being counted"
            )


def _validate_closed_block(
    name: str, block: Any, schema: Mapping[str, type | tuple[type, ...]]
) -> Mapping[str, Any]:
    if not isinstance(block, Mapping):
        raise LedgerError(f"{name} must be a mapping")
    missing = set(schema) - set(block)
    if missing:
        raise LedgerError(f"{name} is missing keys: {sorted(missing)}")
    unknown = set(block) - set(schema)
    if unknown:
        raise LedgerError(
            f"{name} has unknown keys: {sorted(unknown)}; the schema is closed "
            "so an unvalidated field cannot be rendered as though it were checked"
        )
    for key, expected in schema.items():
        value = block[key]
        if expected is bool:
            if not isinstance(value, bool):
                raise LedgerError(f"{name}.{key} must be a bool")
        elif expected is int:
            if not _is_count(value):
                raise LedgerError(f"{name}.{key} must be a non-negative int")
        elif expected is str:
            if not isinstance(value, str) or not value.strip():
                raise LedgerError(f"{name}.{key} must be a non-empty string")
        elif not isinstance(value, expected):
            raise LedgerError(f"{name}.{key} has the wrong type")
    return block


def _validate_retired_v1_state(ledger: Mapping[str, Any]) -> None:
    """Reconcile the narrated retired-v1 state with the counters."""

    block = _validate_closed_block(
        "retired_v1_state", ledger["retired_v1_state"], RETIRED_V1_STATE_KEYS
    )
    if block["set_id"] != "parser-v3-v1":
        raise LedgerError("retired_v1_state.set_id must be 'parser-v3-v1'")
    if not block["sealed_bytes_unchanged"]:
        raise LedgerError(
            "retired_v1_state.sealed_bytes_unchanged is false; Phase 1.2H may "
            "not modify the retired set's bytes"
        )

    inputs = counter_value(
        ledger, "retired_v1_repair_access", "sealed_input_semantic_reads"
    )
    labels = counter_value(
        ledger, "retired_v1_repair_access", "sealed_label_semantic_reads"
    )
    opened = counter_value(ledger, "retired_v1_repair_access", "labels_opened_for_scoring")

    if block["repair_input_content_accessed"] != (inputs > 0):
        raise LedgerError(
            "retired_v1_state.repair_input_content_accessed disagrees with "
            f"sealed_input_semantic_reads={inputs}"
        )
    if block["repair_label_content_accessed"] != (labels > 0):
        raise LedgerError(
            "retired_v1_state.repair_label_content_accessed disagrees with "
            f"sealed_label_semantic_reads={labels}"
        )
    if block["labels_opened_for_scoring"] != opened:
        raise LedgerError(
            "retired_v1_state.labels_opened_for_scoring disagrees with the "
            f"counter ({block['labels_opened_for_scoring']} vs {opened})"
        )
    if block["formal_evaluation_ever_run"]:
        raise LedgerError(
            "retired_v1_state.formal_evaluation_ever_run is true; parser-v3-v1 "
            "was retired unspent and no evaluation was ever run against it"
        )
    if block["prediction_streams_generated_against_v1"]:
        raise LedgerError(
            "retired_v1_state.prediction_streams_generated_against_v1 must be 0"
        )
    if block["formally_scorable"]:
        raise LedgerError(
            "retired_v1_state.formally_scorable is true; the retired set is "
            "unscorable and no round may re-open that"
        )
    if block["formal_eligibility"] != "RETIRED_AS_INELIGIBLE":
        raise LedgerError(
            "retired_v1_state.formal_eligibility must be 'RETIRED_AS_INELIGIBLE'"
        )
    if block["current_state_label"] != RETIRED_V1_STATE_LABEL:
        raise LedgerError(
            "retired_v1_state.current_state_label must be "
            f"{RETIRED_V1_STATE_LABEL!r}"
        )


def _validate_successor_set_state(ledger: Mapping[str, Any], status: str) -> None:
    """Reconcile the narrated successor-set state with the counters.

    Audit G set ``exists``, ``sealed`` and ``sealed_object_count`` to a fully
    constructed 120-case set while ``sets_sealed`` remained ``0`` and the status
    remained blocked, and the ledger validated. These three fields are what the
    current-state generator renders, so an unchecked value here becomes a public
    claim about a set that does not exist.
    """

    block = _validate_closed_block(
        "successor_set_state", ledger["successor_set_state"], SUCCESSOR_SET_STATE_KEYS
    )
    if block["set_id"] != "parser-v3-v2":
        raise LedgerError("successor_set_state.set_id must be 'parser-v3-v2'")

    constructed = counter_value(ledger, "v2_construction", "candidate_cases_constructed")
    sealed = counter_value(ledger, "v2_construction", "sets_sealed")
    prereg = counter_value(
        ledger, "formal_v2_evaluation_access", "preregistrations_completed"
    )
    evaluations = counter_value(
        ledger, "formal_v2_evaluation_access", "formal_evaluations_run"
    )

    if block["cases_constructed"] != constructed:
        raise LedgerError(
            "successor_set_state.cases_constructed disagrees with the counter "
            f"({block['cases_constructed']} vs {constructed})"
        )
    if block["sealed"] != (sealed > 0):
        raise LedgerError(
            f"successor_set_state.sealed disagrees with sets_sealed={sealed}"
        )
    if block["exists"] and not (constructed or sealed):
        raise LedgerError(
            "successor_set_state.exists is true but no case was constructed and "
            "no set was sealed; a set cannot exist without either"
        )
    if block["sealed"] and status != "SEALED_READY_FOR_PREREGISTRATION":
        raise LedgerError(
            f"successor_set_state.sealed is true under status {status!r}; a "
            "round that sealed a set did not block before sealing"
        )
    if not block["sealed"] and block["sealed_object_count"] is not None:
        raise LedgerError(
            "successor_set_state.sealed_object_count must be null while the set "
            "is unsealed; under limitation L-32 the count requires an "
            "authenticated seal-time observation and is undefined, not zero"
        )
    if block["sealed"] and block["sealed_object_count"] is None:
        raise LedgerError(
            "successor_set_state.sealed_object_count is null for a sealed set; "
            "sealing produces the authenticated observation that defines it"
        )
    if block["preregistered"] != (prereg > 0):
        raise LedgerError(
            "successor_set_state.preregistered disagrees with "
            f"preregistrations_completed={prereg}"
        )
    if block["preregistered"]:
        raise LedgerError(
            "successor_set_state.preregistered is true; Phase 1.2H does not "
            "authorise preregistration"
        )
    if block["formal_evaluation_ordinal"] != evaluations:
        raise LedgerError(
            "successor_set_state.formal_evaluation_ordinal disagrees with "
            f"formal_evaluations_run={evaluations}"
        )



def validate_ledger(
    ledger: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
    policy_sha256: str | None = None,
) -> None:
    """Validate a ledger, optionally against the policy it claims to bind.

    Raises :class:`LedgerError` on the first defect. Passing ``policy`` and
    ``policy_sha256`` turns the declared bindings into checked ones; omitting
    them checks structure only.
    """

    if not isinstance(ledger, Mapping):
        raise LedgerError("ledger must be a mapping")
    for key in _REQUIRED_TOP_LEVEL:
        if key not in ledger:
            raise LedgerError(f"{key} is missing")
    unknown = set(ledger) - LEDGER_KEYS
    if unknown:
        raise LedgerError(
            f"ledger has unknown top-level keys: {sorted(unknown)}; the schema "
            "is closed so an unvalidated block cannot be added"
        )
    if ledger["schema_version"] != LEDGER_SCHEMA_VERSION:
        raise LedgerError(
            f"schema_version must be {LEDGER_SCHEMA_VERSION!r}, "
            f"got {ledger['schema_version']!r}"
        )
    status = ledger["status"]
    if status not in TERMINAL_STATES:
        raise LedgerError(f"status {status!r} is not a recognised Phase 1.2H state")

    _validate_policy_binding(ledger["policy_binding"], policy, policy_sha256)
    _validate_snapshot(ledger["phase_1_2g_finalization_snapshot"], policy)
    _validate_counters(ledger["live_counters"])
    events = _validate_events(ledger["events"])

    # Provenance is validated before the status-specific rules because those
    # rules read it. A status check that consulted an unvalidated provenance
    # block would report a state-agreement failure for what is really a
    # malformed-provenance failure, which sends a reader to the wrong place.
    _validate_counter_provenance(ledger["counter_provenance"])

    _validate_status_agreement(ledger, status)
    _validate_event_counter_support(ledger, events)
    _validate_retired_v1_state(ledger)
    _validate_successor_set_state(ledger, status)


def _assert_evidence_is_citable(class_name: str, evidence: str) -> None:
    """Require a machine-evidence class to cite something a reader can open.

    Audit C (C-03) found ``evidence`` accepted as free text and never checked,
    so a class asserting machine derivation could cite nothing at all and the
    ledger would still validate. This does not verify that the citation is
    *correct* --- no string check can --- but it does require that one is
    present in a form a reader can follow to a committed artifact.
    """

    if _CITATION_PATTERN.search(evidence):
        return
    raise LedgerError(
        f"counter_provenance.{class_name}.evidence claims machine derivation "
        "but cites no committed artifact; name the receipt, the committed "
        "control-plane response, or the source file and check that establishes "
        f"the value (got: {evidence!r})"
    )


def _validate_counter_provenance(block: Any) -> None:
    """Require the provenance block to partition the counters it names.

    Three properties are enforced. Every counter named must exist, so the block
    cannot describe a counter that was renamed away. No counter may appear in
    two classes, because a value is either machine-derived or it is not. And
    every counter in :data:`_MACHINE_EVIDENCE_REQUIRED` must be present and
    classified as machine-derived --- those are the counters that carry the
    round's safety claims, and an operator's recollection is not evidence for
    them.
    """

    if not isinstance(block, Mapping):
        raise LedgerError("counter_provenance must be a mapping")
    unknown = set(block) - set(COUNTER_PROVENANCE_CLASSES) - {"role"}
    if unknown:
        raise LedgerError(
            f"counter_provenance has unknown keys: {sorted(unknown)}; the "
            "classes are fixed so a fourth, vaguer class cannot be introduced"
        )

    valid_paths = {
        f"{group}.{name}"
        for group, names in COUNTER_GROUPS.items()
        for name in names
    }
    seen: dict[str, str] = {}
    for class_name in COUNTER_PROVENANCE_CLASSES:
        entry = block.get(class_name)
        if entry is None:
            continue
        if not isinstance(entry, Mapping):
            raise LedgerError(f"counter_provenance.{class_name} must be a mapping")
        counters = entry.get("counters")
        if not isinstance(counters, list) or not counters:
            raise LedgerError(
                f"counter_provenance.{class_name}.counters must be a non-empty list"
            )
        for path in counters:
            if path not in valid_paths:
                raise LedgerError(
                    f"counter_provenance.{class_name} names {path!r}, which is "
                    "not a counter this ledger carries"
                )
            if path in seen:
                raise LedgerError(
                    f"counter_provenance classifies {path!r} as both "
                    f"{seen[path]} and {class_name}; a counter has one provenance"
                )
            seen[path] = class_name

        evidence = entry.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise LedgerError(
                f"counter_provenance.{class_name}.evidence must be a non-empty "
                "string naming where these values came from"
            )
        if class_name != "operator_maintained_approximate":
            _assert_evidence_is_citable(class_name, evidence)

        unknown_entry_keys = set(entry) - {"counters", "evidence", "note"}
        if unknown_entry_keys:
            raise LedgerError(
                f"counter_provenance.{class_name} has unknown keys: "
                f"{sorted(unknown_entry_keys)}"
            )
        note = entry.get("note")
        if note is not None and (not isinstance(note, str) or not note.strip()):
            raise LedgerError(
                f"counter_provenance.{class_name}.note must be a non-empty "
                "string when present"
            )

    for path in sorted(_MACHINE_EVIDENCE_REQUIRED):
        provenance = seen.get(path)
        if provenance is None:
            raise LedgerError(
                f"counter_provenance omits {path!r}, which carries a safety "
                "claim and must state where its value came from"
            )
        if provenance == "operator_maintained_approximate":
            raise LedgerError(
                f"counter_provenance classifies {path!r} as operator-maintained; "
                "a safety counter requires machine evidence, not recollection"
            )


def _assert_gate_receipt_is_cited(ledger: Mapping[str, Any]) -> None:
    """Require the boundary state to rest on a named execution receipt.

    Audit C (C-02): the state was previously earned by an integer in the
    ledger's own file. Raising that integer to 14 was sufficient to claim that
    the authoritative source had been reached, which means the check verified
    the ledger's self-consistency rather than anything about the world.

    A receipt cannot be summoned by editing this file, so requiring one moves
    the claim from arithmetic onto evidence. This function does not open the
    receipt --- the ledger module reads nothing from disk, deliberately, and the
    receipt-to-ledger binding is asserted by the ledger test suite, which can.
    What it requires is that the ledger names one, in the provenance block that
    is the ledger's own account of where its numbers came from.
    """

    provenance = ledger.get("counter_provenance")
    if not isinstance(provenance, Mapping):  # pragma: no cover - defensive
        raise LedgerError(
            "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY requires a counter_provenance "
            "block naming the gate receipt"
        )
    entry = provenance.get("receipt_derived_exact")
    evidence = entry.get("evidence", "") if isinstance(entry, Mapping) else ""
    counters = entry.get("counters", []) if isinstance(entry, Mapping) else []

    if "retired_v1_repair_access.byte_only_integrity_verifications" not in counters:
        raise LedgerError(
            "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY requires "
            "byte_only_integrity_verifications to be receipt-derived; the state "
            "asserts that a gate ran, and a hand-maintained count is not "
            "evidence that one did"
        )
    if not _RECEIPT_CITATION_PATTERN.search(evidence):
        raise LedgerError(
            "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY requires "
            "counter_provenance.receipt_derived_exact.evidence to name a "
            "committed access receipt; without one the state rests on an "
            f"integer in this file (got: {evidence!r})"
        )


def _validate_status_agreement(ledger: Mapping[str, Any], status: str) -> None:
    """Require the counters to support the declared status.

    This is the check that stops a ledger from claiming an outcome its own
    numbers contradict --- a sealed set with zero seal writes, or a blocked
    source-access round that nonetheless recorded semantic reads.
    """

    sealed = counter_value(ledger, "v2_construction", "sets_sealed")
    witnesses = counter_value(ledger, "v2_construction", "listing_witnesses_obtained")
    contracts = counter_value(ledger, "v2_construction", "final_contracts_compiled")
    v1_inputs = counter_value(
        ledger, "retired_v1_repair_access", "sealed_input_semantic_reads"
    )
    v1_labels = counter_value(
        ledger, "retired_v1_repair_access", "sealed_label_semantic_reads"
    )

    if status == "SEALED_READY_FOR_PREREGISTRATION":
        if sealed != 1:
            raise LedgerError(
                "SEALED_READY_FOR_PREREGISTRATION requires exactly one sealed "
                f"set, got sets_sealed={sealed}"
            )
        if witnesses < 1:
            raise LedgerError(
                "SEALED_READY_FOR_PREREGISTRATION requires an authenticated "
                "listing witness"
            )
        if contracts != 1:
            raise LedgerError(
                "SEALED_READY_FOR_PREREGISTRATION requires exactly one final "
                f"contract, got final_contracts_compiled={contracts}"
            )
    else:
        if sealed:
            raise LedgerError(
                f"status {status!r} is inconsistent with sets_sealed={sealed}; a "
                "round that sealed a set did not block before sealing"
            )

    if status == "BLOCKED_ON_PRIVATE_SOURCE_ACCESS" and (v1_inputs or v1_labels):
        raise LedgerError(
            "BLOCKED_ON_PRIVATE_SOURCE_ACCESS is inconsistent with recorded "
            f"retired-v1 semantic reads (inputs={v1_inputs}, labels={v1_labels}); "
            "a round that read the source did not block on reaching it"
        )

    if status == "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY":
        # This state was added in Phase 1.2H-R1, after independent Audit B
        # observed that the round's own intended terminal state was not one the
        # ledger would accept. It means something narrow and must be earned:
        # the authoritative source WAS reached, byte-only, and the round then
        # stopped because no qualifying private semantic-review backend exists.
        #
        # Precedence, per independent Audit B (B-09): if the byte-only gate
        # fails, the correct state is BLOCKED_ON_PRIVATE_SOURCE_ACCESS. Only
        # once the gate has passed can the boundary be the thing that blocks.
        # Enforcing that here is what stops the more advanced-sounding state
        # from being claimed by a round that never got that far.
        if v1_inputs or v1_labels:
            raise LedgerError(
                "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY is inconsistent with "
                f"retired-v1 semantic reads (inputs={v1_inputs}, labels={v1_labels}); "
                "the boundary is precisely what prevents a semantic read, so a "
                "round that performed one did not block on it"
            )
        verifications = counter_value(
            ledger, "retired_v1_repair_access", "byte_only_integrity_verifications"
        )
        if verifications < BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE:
            raise LedgerError(
                "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY requires a completed "
                "byte-only access gate: at least the 12 authoritative objects "
                "the gate streams, plus the 2 pre-R1 local curator-file "
                "verifications already on record, so "
                f"byte_only_integrity_verifications >= "
                f"{BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE}, got {verifications}; "
                "a round that could not reach the source must record "
                "BLOCKED_ON_PRIVATE_SOURCE_ACCESS instead"
            )
        _assert_gate_receipt_is_cited(ledger)

    # Formal evaluation state is invariant for this whole phase.
    for name in ("formal_evaluations_run", "preregistrations_completed"):
        if counter_value(ledger, "formal_v2_evaluation_access", name):
            raise LedgerError(
                f"formal_v2_evaluation_access.{name} must be 0 in Phase 1.2H; "
                "this phase authorises neither preregistration nor evaluation"
            )
    for name in COUNTER_GROUPS["parser_execution"]:
        if counter_value(ledger, "parser_execution", name):
            raise LedgerError(
                f"parser_execution.{name} must be 0 in Phase 1.2H; no parser may "
                "run and no prediction may be generated"
            )


def assert_monotonic_succession(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> None:
    """Require ``current`` to be a legal successor of ``previous``.

    Both ledgers are validated first. Audit G changed only ``status`` on an
    otherwise blocked ledger --- to ``SEALED_READY_FOR_PREREGISTRATION``, with
    ``sets_sealed`` still ``0`` --- and succession accepted it, because
    comparing two records says nothing about whether either is internally
    coherent. Every counter must then be greater than or equal to its prior
    value, and every prior event must survive unchanged at the same sequence
    number. That is the property that makes the ledger evidence rather than
    assertion: a round cannot quietly unwind an access it already recorded.
    """

    validate_ledger(previous)
    validate_ledger(current)

    for group, names in COUNTER_GROUPS.items():
        for name in names:
            before = counter_value(previous, group, name)
            after = counter_value(current, group, name)
            if after < before:
                raise LedgerError(
                    f"live_counters.{group}.{name} decreased from {before} to "
                    f"{after}; access counters are monotonic"
                )

    prior_events = _validate_events(previous["events"])
    next_events = _validate_events(current["events"])
    if len(next_events) < len(prior_events):
        raise LedgerError(
            f"events shrank from {len(prior_events)} to {len(next_events)}; "
            "recorded events cannot be erased"
        )
    for index, prior in enumerate(prior_events):
        if next_events[index] != prior:
            raise LedgerError(
                f"events[{index}] was rewritten; recorded events are immutable"
            )
