"""One-shot evaluation lifecycle for the successor ``parser-v3-v2`` set.

Phase 1.2H-R2 / 1.2J. This module owns the part of the round that decides
whether a formal parser-v3 result is *permitted to exist*: the ordered state
machine, the evaluation ordinal, the create-only sealing semantics for both the
set and the prediction stream, and the identity/storage separation that keeps
Stage P away from labels and Stage E away from the parser.

Why a separate module, and what it deliberately does not do
-----------------------------------------------------------

``parser_v3_v2_access_ledger`` records *what has happened*. This module decides
*what may happen next*. Keeping them apart matters because a ledger that both
records an event and authorises it can be walked in one edit: append the event,
and the authorisation follows from the record you just wrote. Here the ordering
rules are evaluated against a proposed transition and refuse independently of
whatever a ledger already claims.

This module computes no score, holds no threshold, and reads no label. It does
not decide whether parser v3 passed. It decides whether the question was asked
exactly once, in the registered order, by the registered identities, against a
complete and immutable prediction stream. A green result here is *not* a parser
validation result, and no caller may present it as one.

Parser isolation
----------------

Nothing in this file references a parser symbol or invokes a parser. That is
narrower than "no parser module is loaded", and the difference is the same one
``parser_v3_v2_access_ledger`` documents: ``jspace_observation/__init__.py``
eagerly imports the legacy parser, so importing this module *through the
package* does place parser code in ``sys.modules``. Stage E must therefore not
import it through the package. :func:`load_module_without_package` exists for
that, and :func:`assert_stage_e_import_is_parser_free` is the check that makes
the claim testable rather than asserted.

The supportable claim is differential: this module adds no parser dependency.
It is not a claim about the process that imports it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "LifecycleError",
    "LIFECYCLE_SCHEMA_VERSION",
    "STATES",
    "TERMINAL_STATES",
    "PERMITTED_TRANSITIONS",
    "ORDINAL_ADVANCING_TRANSITION",
    "MAX_FORMAL_EVALUATION_ORDINAL",
    "EXPECTED_SET_MEMBER_COUNT",
    "STAGE_P_FORBIDDEN_READ_CLASSES",
    "STAGE_E_FORBIDDEN_READ_CLASSES",
    "ROLE_LANES",
    "assert_transition_permitted",
    "next_ordinal",
    "assert_ordinal_succession",
    "assert_create_only_plan",
    "assert_terminal_manifest_last",
    "assert_prediction_stream_complete",
    "assert_stage_p_scope",
    "assert_stage_e_scope",
    "assert_status_is_exclusive",
    "assert_report_only_metrics_cannot_reach_status",
    "compile_final_contract_once",
    "load_module_without_package",
    "assert_stage_e_import_is_parser_free",
]


class LifecycleError(Exception):
    """Raised when a proposed lifecycle action is not permitted.

    Deliberately one exception type. A caller that can distinguish
    "ordering violation" from "scope violation" by exception class is a caller
    that can catch one and continue, and every condition in this module is a
    stop condition.
    """


LIFECYCLE_SCHEMA_VERSION = "phase1-parser-v3-v2-evaluation-lifecycle/v1"

#: Every state the successor set's formal evaluation may occupy.
#:
#: ``SET_SEALED`` is the entry state rather than ``SET_CONSTRUCTED``: a set that
#: is built but not sealed cannot be preregistered, so admitting a pre-seal
#: state here would create a reachable path in which preregistration binds
#: bytes that can still change.
STATES: tuple[str, ...] = (
    "SET_SEALED",
    "PREREGISTERED",
    "PREDICTION_RUNNING",
    "PREDICTION_SEALED",
    "LABELS_OPENED",
    "EVALUATED_ACCEPTED",
    "EVALUATED_NOT_ACCEPTED",
    "EVALUATION_INVALID",
)

TERMINAL_STATES: frozenset[str] = frozenset(
    {"EVALUATED_ACCEPTED", "EVALUATED_NOT_ACCEPTED", "EVALUATION_INVALID"}
)

#: The complete permitted transition relation. Anything absent is refused.
#:
#: ``PREDICTION_RUNNING -> EVALUATION_INVALID`` is present because an
#: infrastructure abort during Stage P is a real outcome and pretending it is
#: not would force a caller to invent a state. ``PREREGISTERED ->
#: EVALUATION_INVALID`` is absent on purpose: nothing has been executed at that
#: point, so the honest status is a blocked one from the controlling prompt's
#: list, not an invalid formal evaluation.
PERMITTED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("SET_SEALED", "PREREGISTERED"),
        ("PREREGISTERED", "PREDICTION_RUNNING"),
        ("PREDICTION_RUNNING", "PREDICTION_SEALED"),
        ("PREDICTION_RUNNING", "EVALUATION_INVALID"),
        ("PREDICTION_SEALED", "LABELS_OPENED"),
        ("LABELS_OPENED", "EVALUATED_ACCEPTED"),
        ("LABELS_OPENED", "EVALUATED_NOT_ACCEPTED"),
        ("LABELS_OPENED", "EVALUATION_INVALID"),
    }
)

#: The single transition that advances the formal evaluation ordinal.
#:
#: It is the label-opening transition and not the Stage P launch. Generating a
#: prediction spends nothing that cannot be spent again on a different set; it
#: is opening the scoring labels that consumes the one-shot property, because
#: after that the author has seen the answer.
ORDINAL_ADVANCING_TRANSITION: tuple[str, str] = ("PREDICTION_SEALED", "LABELS_OPENED")

MAX_FORMAL_EVALUATION_ORDINAL = 1

#: Exact member count of the successor set, from the FINAL stratum policy:
#: twelve strata of ten.
EXPECTED_SET_MEMBER_COUNT = 120

#: Read classes Stage P must never touch.
STAGE_P_FORBIDDEN_READ_CLASSES: frozenset[str] = frozenset(
    {
        "scoring_labels",
        "reference_labels",
        "arbitration_records",
        "reviewer_decisions",
        "stage_e_result",
        "comparator_predictions",
    }
)

#: Read classes Stage E must never touch, plus the capability it must not hold.
#:
#: ``parser_source`` and ``parser_invocation`` are separate entries because they
#: fail differently: the first is a file Stage E must not be able to open, the
#: second is a capability it must not be able to exercise even if some other
#: image layer supplied the code.
STAGE_E_FORBIDDEN_READ_CLASSES: frozenset[str] = frozenset(
    {
        "parser_source",
        "parser_invocation",
        "construction_staging",
        "reviewer_decisions",
        "candidate_cases",
    }
)

#: Minimum role -> permitted lane mapping, from section 7.4 of the controlling
#: prompt. Read as: a role may read only from ``reads`` and write only to
#: ``writes``. Absence is denial; there is no implicit inheritance.
ROLE_LANES: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "source_custodian": {
        "reads": ("retired_v1_source",),
        "writes": ("v2_private_staging",),
    },
    "reviewer_a": {"reads": ("blinded_case_packets",), "writes": ("reviewer_a_decisions",)},
    "reviewer_b": {"reads": ("blinded_case_packets",), "writes": ("reviewer_b_decisions",)},
    "broker": {
        "reads": ("reviewer_a_decisions", "reviewer_b_decisions"),
        "writes": ("disagreements",),
    },
    "arbiter": {"reads": ("disagreement_packets",), "writes": ("arbitration_records",)},
    "private_set_auditor": {
        "reads": ("final_candidate", "provenance"),
        "writes": ("audit_findings",),
    },
    "seal_custodian": {
        "reads": ("finalized_immutable_bytes", "seal_plan"),
        "writes": ("v2_sealed_namespace", "listing_witness"),
    },
    "stage_p": {
        "reads": ("sealed_v2_inputs", "frozen_parser_assets"),
        "writes": ("prediction_namespace",),
    },
    "prediction_sealer": {
        "reads": ("prediction_members",),
        "writes": ("prediction_manifest", "prediction_witness"),
    },
    "stage_e": {
        "reads": ("sealed_predictions", "scoring_labels", "policy", "final_contract"),
        "writes": ("formal_result",),
    },
    "receipt_exporter": {
        "reads": ("content_free_receipts",),
        "writes": ("public_projection",),
    },
    # --- additive lanes required by section 5.2 --------------------------
    #
    # Section 7.4 registers the minimum matrix above. Section 5.2 requires a
    # production entrypoint for four further roles, and ``_assert_scope``
    # refuses any role absent from this table --- so without these entries the
    # normalizer, selector, facts compiler and preregistration compiler could
    # not verify their lanes at all, which is the opposite of fail-closed.
    #
    # The eleven entries above are unchanged. A control asserts that, because
    # "we only added rows" is a claim about a diff and must be testable from
    # the running table instead.
    "normalizer": {
        "reads": ("v2_private_staging",),
        "writes": ("normalized_candidates",),
    },
    "selector": {
        "reads": (
            "normalized_candidates",
            "reviewer_a_decisions",
            "reviewer_b_decisions",
            "arbitration_records",
        ),
        "writes": ("final_candidate", "quarantine_records", "replacement_records"),
    },
    "facts_compiler": {
        "reads": ("final_candidate",),
        "writes": ("set_facts",),
    },
    # Deliberately does not read ``v2_sealed_namespace``. The compiler needs the
    # sealed set's manifest digest, not its cases, and the listing witness is
    # the content-free artifact that already carries exactly that. Granting the
    # namespace would hand a role that never needs case content the ability to
    # read all 120 of them.
    "preregistration_compiler": {
        "reads": ("set_facts", "listing_witness", "final_contract", "policy"),
        "writes": ("preregistration_lock",),
    },
}

#: The eleven role names registered by section 7.4, recorded separately so a
#: control can prove the additive extension above did not edit them.
SECTION_7_4_ROLES: tuple[str, ...] = (
    "source_custodian",
    "reviewer_a",
    "reviewer_b",
    "broker",
    "arbiter",
    "private_set_auditor",
    "seal_custodian",
    "stage_p",
    "prediction_sealer",
    "stage_e",
    "receipt_exporter",
)

#: The only role permitted to read scoring labels. Named here so the property
#: is checkable against the whole lane table rather than against Stage E alone.
LABEL_READING_ROLE = "stage_e"


# ---------------------------------------------------------------------------
# schema binding
# ---------------------------------------------------------------------------

#: Every schema id the lifecycle recognises, closed.
#:
#: Section 5.1 requires schema ids and hashes to be bound in the lifecycle. The
#: ids are written here by hand: that is the binding. The digests below are
#: derived mechanically in Azure from the schema documents themselves and pasted
#: back, in the same way ``requirements.lock.txt`` was produced --- a digest a
#: human typed from memory certifies nothing.
BOUND_SCHEMA_IDS: tuple[str, ...] = (
    "phase1-parser-v3-v2-access-event/v1",
    "phase1-parser-v3-v2-admission-record/v1",
    "phase1-parser-v3-v2-arbitration-result/v1",
    "phase1-parser-v3-v2-authenticated-listing-projection/v1",
    "phase1-parser-v3-v2-blinded-case-packet/v1",
    "phase1-parser-v3-v2-construction-plan/v1",
    "phase1-parser-v3-v2-deployment-evidence/v1",
    "phase1-parser-v3-v2-disagreement-packet/v1",
    "phase1-parser-v3-v2-final-contract-receipt/v1",
    "phase1-parser-v3-v2-listing-witness-receipt/v1",
    "phase1-parser-v3-v2-planned-seal-members/v1",
    "phase1-parser-v3-v2-prediction-manifest/v1",
    "phase1-parser-v3-v2-prediction-member/v1",
    "phase1-parser-v3-v2-prediction-receipt/v1",
    "phase1-parser-v3-v2-preregistration-lock/v1",
    "phase1-parser-v3-v2-public-receipt/v1",
    "phase1-parser-v3-v2-quarantine-record/v1",
    "phase1-parser-v3-v2-replacement-record/v1",
    "phase1-parser-v3-v2-reviewer-decision/v1",
    "phase1-parser-v3-v2-runtime-canary-result/v1",
    "phase1-parser-v3-v2-set-facts-projection/v1",
    "phase1-parser-v3-v2-stage-e-result/v1",
    "phase1-parser-v3-v2-terminal-manifest/v1",
    "phase1-parser-v3-v2-terminal-state-receipt/v1",
)

#: Azure-derived SHA-256 of each bound schema document.
#:
#: Produced by ACR run cm2p from commit 71e13c9d, by importing the registry and
#: printing ``SCHEMA_DIGESTS``. Editing any schema byte changes the value here
#: and ``assert_schema_binding`` refuses until the change is bound on purpose.
BOUND_SCHEMA_DIGESTS: Mapping[str, str] = {
    "phase1-parser-v3-v2-access-event/v1": "a58c13c958275a395da214c87bf7df2f52ee0c2cfb55f914e95b403faaeb2bcd",
    "phase1-parser-v3-v2-admission-record/v1": "9d5c02d5ff2e03f1508779222cad30862f94cbe47f6e674c1d7625fdace2e6b0",
    "phase1-parser-v3-v2-arbitration-result/v1": "64bca5c9b3c0b331559c8ed6372e16c9daccb2a6097edc05d2641e8ac1bdc222",
    "phase1-parser-v3-v2-authenticated-listing-projection/v1": "a0cd23e32984e541fa330a4d1cca1051e4aef7ea2760bb6171964bf4a4e1ae00",
    "phase1-parser-v3-v2-blinded-case-packet/v1": "0e9d27e0b395357497ee4a450d3c7dd47cad08eb7a459ce81552a4ae921b8452",
    "phase1-parser-v3-v2-construction-plan/v1": "8ef4c849f33e95d48e8be6c1233377bf740cb5c1389caa0d8624f4c08a79f9c2",
    "phase1-parser-v3-v2-deployment-evidence/v1": "c130fdd660bd135f76dc0d0b44027a0057f38eedb5e0144804601cd991ba8262",
    "phase1-parser-v3-v2-disagreement-packet/v1": "d70f1c1ef02c354d5819ceb9a01690c9d5be2e2c1639a0adbdb729bb46fbb8ba",
    "phase1-parser-v3-v2-final-contract-receipt/v1": "c527c61ce96f1f63c0d3c9c1a6bc9de2e7b40e4b04f7b52e90c9fbc55cd1fdc0",
    "phase1-parser-v3-v2-listing-witness-receipt/v1": "a23652dbca2c4491cafa021252ec7b15ea55a0d6ad9d4d2340baf63a5335e62b",
    "phase1-parser-v3-v2-planned-seal-members/v1": "c8565701db6267e5d3af9aff1c6fd43f20ed99aed32e6154b80bb6e8861c2e9a",
    "phase1-parser-v3-v2-prediction-manifest/v1": "f7147e815a645d8cfe097725b21e6d5cc8306beea199906e3f0cf90e7d04ee8a",
    "phase1-parser-v3-v2-prediction-member/v1": "ec685d585f46bbe7e10219f8ee1821349a5a71088963fbabfa48a95937e0a158",
    "phase1-parser-v3-v2-prediction-receipt/v1": "47da75d0ca9bc5c16b760e95c64724a8bdeb14c27ab9505c7064e0b9ef53ed5a",
    "phase1-parser-v3-v2-preregistration-lock/v1": "9455edbb400221001a2ae6c211867992fed18daf97d0205ab94a2de264d573aa",
    "phase1-parser-v3-v2-public-receipt/v1": "6d2b5b5c20d67d00eaa2f560b23c9223bf813ce276a02f12baf0c8ca9e2678bd",
    "phase1-parser-v3-v2-quarantine-record/v1": "4ee5ed220605c6a7b8d9a456b52ec957bcd8f662aee7f2efe84df1f3eacb8159",
    "phase1-parser-v3-v2-replacement-record/v1": "3b2a8593619e7ecc0442ee9c28fa1e006499189a693f84ae78da9bcb19649436",
    "phase1-parser-v3-v2-reviewer-decision/v1": "c5013b5073e3df957c6ecd8790fecd17c38be543c09578ae778bd307f8b81c58",
    "phase1-parser-v3-v2-runtime-canary-result/v1": "82c98628751a74268acfa658330d1f4b5d59075ffd5f38a569a489795788428f",
    "phase1-parser-v3-v2-set-facts-projection/v1": "b38ac7395a81e4a49474b246b10521ccf450a40e3c3608cfeac35a2d6bb59a53",
    "phase1-parser-v3-v2-stage-e-result/v1": "447675e2ae677cfe1cd37b53de987fef7a67d012e5ceaf7a4fc31a881b949728",
    "phase1-parser-v3-v2-terminal-manifest/v1": "a05b1c0f82670d0a0fcd5e89e3c1ace2dca41ecfa5cd07fdb0c102a856c2c0ce",
    "phase1-parser-v3-v2-terminal-state-receipt/v1": "1c6d68676d7822526c979d4cff686f13f52501fab4d3e6c689cfb330d594af2e",
}

#: Azure-derived SHA-256 over the whole digest table.
BOUND_SCHEMA_REGISTRY_DIGEST: str = (
    "211b1b28f6f26ab7f4bc891892357947a97597b3c61f4f064154da4501c4193b"
)


def assert_schema_binding(
    *, registry_digests: Mapping[str, str], registry_digest: str
) -> None:
    """Refuse any drift between the schema registry and this binding.

    Refuses an unfilled binding first. An empty expected table would otherwise
    make every comparison below vacuously true, which is the precise shape of
    the check-that-checks-nothing this repository has already had to remove
    five times.
    """
    if not BOUND_SCHEMA_DIGESTS or not BOUND_SCHEMA_REGISTRY_DIGEST:
        raise LifecycleError(
            "the lifecycle schema binding is empty; derive the digests in Azure "
            "and bind them before any artifact is validated against them"
        )
    bound_ids = set(BOUND_SCHEMA_IDS)
    if set(BOUND_SCHEMA_DIGESTS) != bound_ids:
        raise LifecycleError(
            "the bound digest table and the bound id list describe different "
            "schema sets"
        )
    supplied = set(registry_digests)
    missing = sorted(bound_ids - supplied)
    if missing:
        raise LifecycleError(f"schema registry is missing bound schema(s): {missing}")
    added = sorted(supplied - bound_ids)
    if added:
        raise LifecycleError(f"schema registry carries unbound schema(s): {added}")
    changed = sorted(
        sid for sid in bound_ids if registry_digests[sid] != BOUND_SCHEMA_DIGESTS[sid]
    )
    if changed:
        raise LifecycleError(f"bound schema document(s) changed: {changed}")
    for sid in sorted(bound_ids):
        _require_sha256(registry_digests[sid], f"schema digest for {sid}")
    if registry_digest != BOUND_SCHEMA_REGISTRY_DIGEST:
        raise LifecycleError(
            "the schema registry digest does not match the bound registry digest"
        )

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise LifecycleError(
            f"{field} must be a lowercase 64-character SHA-256 hex digest, got {value!r}"
        )
    return value


# ---------------------------------------------------------------------------
# ordering
# ---------------------------------------------------------------------------


def assert_transition_permitted(current: str, proposed: str) -> None:
    """Refuse any transition outside :data:`PERMITTED_TRANSITIONS`.

    Unknown state names are refused before the relation is consulted, so a
    typo cannot be read as "not in the permitted set, therefore some other
    rule applies". A terminal state has no successor at all.
    """
    for name, value in (("current", current), ("proposed", proposed)):
        if value not in STATES:
            raise LifecycleError(f"{name} state {value!r} is not a registered state")
    if current in TERMINAL_STATES:
        raise LifecycleError(
            f"{current} is terminal; no transition out of it is permitted, "
            f"and {proposed!r} was proposed"
        )
    if (current, proposed) not in PERMITTED_TRANSITIONS:
        raise LifecycleError(f"transition {current} -> {proposed} is not permitted")


def next_ordinal(current: str, proposed: str, current_ordinal: int) -> int:
    """Return the ordinal after a permitted transition.

    The ordinal advances on exactly one transition and is otherwise carried
    unchanged. It never decreases and never exceeds
    :data:`MAX_FORMAL_EVALUATION_ORDINAL`.
    """
    assert_transition_permitted(current, proposed)
    if not isinstance(current_ordinal, int) or isinstance(current_ordinal, bool):
        raise LifecycleError(f"ordinal must be an int, got {current_ordinal!r}")
    if current_ordinal < 0:
        raise LifecycleError(f"ordinal must not be negative, got {current_ordinal}")
    if current_ordinal > MAX_FORMAL_EVALUATION_ORDINAL:
        raise LifecycleError(
            f"ordinal {current_ordinal} already exceeds the maximum "
            f"{MAX_FORMAL_EVALUATION_ORDINAL}"
        )
    if (current, proposed) != ORDINAL_ADVANCING_TRANSITION:
        return current_ordinal
    if current_ordinal != 0:
        raise LifecycleError(
            "labels may be opened only once; the ordinal is already "
            f"{current_ordinal}, so a second formal evaluation was attempted"
        )
    return 1


def assert_ordinal_succession(before: int, after: int) -> None:
    """Refuse a reset, a decrement, or a double increment."""
    for name, value in (("before", before), ("after", after)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise LifecycleError(f"{name} ordinal must be an int, got {value!r}")
    if after < before:
        raise LifecycleError(
            f"the formal evaluation ordinal must never decrease: {before} -> {after}"
        )
    if after > MAX_FORMAL_EVALUATION_ORDINAL:
        raise LifecycleError(
            f"the formal evaluation ordinal must never exceed "
            f"{MAX_FORMAL_EVALUATION_ORDINAL}: {before} -> {after}"
        )
    if after - before > 1:
        raise LifecycleError(f"the ordinal must advance by at most 1: {before} -> {after}")


# ---------------------------------------------------------------------------
# create-only object lifecycle
# ---------------------------------------------------------------------------


def assert_create_only_plan(
    *,
    existing_objects: Iterable[str],
    planned_objects: Sequence[str],
    terminal_manifest: str,
) -> None:
    """Refuse any write plan that is not strictly create-only.

    A plan is create-only when the target namespace is empty of every planned
    name, the planned names are unique, and the terminal manifest is one of
    them. Overwrite, resume and rename are all the same failure from the
    outside --- an object that existed before the write and has different bytes
    after it --- so all three are refused by the same rule rather than by three
    rules a caller could satisfy one at a time.
    """
    existing = set(existing_objects)
    if not planned_objects:
        raise LifecycleError("a create-only plan must contain at least one object")
    duplicates = sorted({name for name in planned_objects if planned_objects.count(name) > 1})
    if duplicates:
        raise LifecycleError(f"planned objects contain duplicates: {duplicates}")
    collisions = sorted(existing.intersection(planned_objects))
    if collisions:
        raise LifecycleError(
            "create-only violated: the target namespace already contains "
            f"{len(collisions)} planned object(s); the seal must use a "
            "never-before-used identity and prefix rather than resume"
        )
    if terminal_manifest not in planned_objects:
        raise LifecycleError("the terminal manifest must be part of the planned objects")


def assert_terminal_manifest_last(
    *, write_order: Sequence[str], terminal_manifest: str
) -> None:
    """Require the terminal manifest to be the final write.

    Manifest-first is the failure this refuses. A manifest written before its
    members describes a set that does not yet exist, and any reader that trusts
    it observes a complete set that was never complete.
    """
    if terminal_manifest not in write_order:
        raise LifecycleError("the terminal manifest does not appear in the write order")
    if write_order[-1] != terminal_manifest:
        raise LifecycleError(
            "the terminal manifest must be written last; it is at position "
            f"{write_order.index(terminal_manifest)} of {len(write_order)}"
        )


def assert_prediction_stream_complete(
    *,
    sealed_case_ids: Sequence[str],
    prediction_case_ids: Sequence[str],
    expected_count: int = EXPECTED_SET_MEMBER_COUNT,
) -> None:
    """Refuse a partial, duplicated or misaligned prediction stream.

    Completeness is checked against the sealed set's own case identifiers, not
    against a count. A stream of the right size drawn from the wrong set is the
    more dangerous error, because a count check passes it.
    """
    if len(sealed_case_ids) != expected_count:
        raise LifecycleError(
            f"the sealed set must carry exactly {expected_count} cases, "
            f"got {len(sealed_case_ids)}"
        )
    sealed_unique = set(sealed_case_ids)
    if len(sealed_unique) != len(sealed_case_ids):
        raise LifecycleError("the sealed set contains duplicate case identifiers")
    duplicates = sorted(
        {cid for cid in prediction_case_ids if prediction_case_ids.count(cid) > 1}
    )
    if duplicates:
        raise LifecycleError(
            f"the prediction stream contains {len(duplicates)} duplicated case "
            "identifier(s); a duplicated prediction cannot seal"
        )
    predicted = set(prediction_case_ids)
    missing = sealed_unique - predicted
    if missing:
        raise LifecycleError(
            f"the prediction stream is incomplete: {len(missing)} sealed case(s) "
            "have no prediction, so the stream must not seal"
        )
    extra = predicted - sealed_unique
    if extra:
        raise LifecycleError(
            f"the prediction stream carries {len(extra)} prediction(s) for cases "
            "that are not in the sealed set"
        )


# ---------------------------------------------------------------------------
# scope separation
# ---------------------------------------------------------------------------


def _assert_scope(role: str, requested: Iterable[str], forbidden: frozenset[str]) -> None:
    lanes = ROLE_LANES.get(role)
    if lanes is None:
        raise LifecycleError(f"{role!r} is not a registered role")
    permitted = set(lanes["reads"])
    requested_set = list(requested)
    violations = sorted({item for item in requested_set if item in forbidden})
    if violations:
        raise LifecycleError(
            f"{role} requested forbidden read class(es): {violations}"
        )
    unlisted = sorted({item for item in requested_set if item not in permitted})
    if unlisted:
        raise LifecycleError(
            f"{role} requested read class(es) outside its lane: {unlisted}"
        )


def assert_stage_p_scope(requested_read_classes: Iterable[str]) -> None:
    """Refuse any Stage P read that reaches a label or a scoring artifact."""
    _assert_scope("stage_p", requested_read_classes, STAGE_P_FORBIDDEN_READ_CLASSES)


def assert_stage_e_scope(requested_read_classes: Iterable[str]) -> None:
    """Refuse any Stage E read that reaches parser code or construction state."""
    _assert_scope("stage_e", requested_read_classes, STAGE_E_FORBIDDEN_READ_CLASSES)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def assert_status_is_exclusive(
    *, binding_gate_results: Mapping[str, bool], declared_status: str
) -> None:
    """Derive the status from the binding gates and refuse any other value.

    The status is not an input that gets checked; it is recomputed and compared.
    A function that accepts a status and merely validates it is one that can be
    satisfied by passing the status you wanted.
    """
    if declared_status not in {"PASS", "FAIL", "INVALID"}:
        raise LifecycleError(f"declared status {declared_status!r} is not PASS, FAIL or INVALID")
    if not binding_gate_results:
        raise LifecycleError("a status cannot be derived from zero binding gates")
    non_bool = sorted(
        name for name, value in binding_gate_results.items() if not isinstance(value, bool)
    )
    if non_bool:
        raise LifecycleError(f"binding gate result(s) are not boolean: {non_bool}")
    derived = "PASS" if all(binding_gate_results.values()) else "FAIL"
    if declared_status != derived:
        failed = sorted(name for name, value in binding_gate_results.items() if not value)
        raise LifecycleError(
            f"declared status {declared_status} does not match the status derived "
            f"from the binding gates ({derived}); failing gate(s): {failed}"
        )


def assert_report_only_metrics_cannot_reach_status(
    *, binding_gate_names: Iterable[str], report_only_metric_names: Iterable[str]
) -> None:
    """Refuse any overlap between binding gates and report-only diagnostics.

    Macro-F1, the confusion matrix and every comparator figure are report-only.
    The failure this refuses is a diagnostic being promoted into the acceptance
    derivation by sharing a name with a gate.
    """
    binding = set(binding_gate_names)
    report_only = set(report_only_metric_names)
    overlap = sorted(binding.intersection(report_only))
    if overlap:
        raise LifecycleError(
            "report-only metric(s) appear among the binding gates and could "
            f"therefore reach the status: {overlap}"
        )


# ---------------------------------------------------------------------------
# final contract
# ---------------------------------------------------------------------------


def compile_final_contract_once(
    *,
    policy_sha256: str,
    set_manifest_sha256: str,
    listing_witness_sha256: str,
    parser_source_sha256: str,
    scorer_source_sha256: str,
    prospective_protocol_commit: str,
    existing_contract_objects: Iterable[str],
    contract_object_name: str,
) -> dict[str, Any]:
    """Compile the one-time final contract, or refuse.

    The contract binds the manifest and the *authenticated listing witness*
    together. Binding the manifest alone would let a self-consistent set that
    was never observed at the storage layer satisfy the contract, which is the
    ``L-32`` failure this repository already recorded.
    """
    if contract_object_name in set(existing_contract_objects):
        raise LifecycleError(
            "the final contract already exists; it is compiled exactly once and "
            "may not be recompiled, patched or overwritten"
        )
    if not re.fullmatch(r"[0-9a-f]{40}", prospective_protocol_commit):
        raise LifecycleError(
            "prospective_protocol_commit must be a full 40-character Git SHA-1, "
            f"got {prospective_protocol_commit!r}"
        )
    payload = {
        "schema_version": LIFECYCLE_SCHEMA_VERSION,
        "policy_sha256": _require_sha256(policy_sha256, "policy_sha256"),
        "set_manifest_sha256": _require_sha256(set_manifest_sha256, "set_manifest_sha256"),
        "listing_witness_sha256": _require_sha256(
            listing_witness_sha256, "listing_witness_sha256"
        ),
        "parser_source_sha256": _require_sha256(parser_source_sha256, "parser_source_sha256"),
        "scorer_source_sha256": _require_sha256(scorer_source_sha256, "scorer_source_sha256"),
        "prospective_protocol_commit": prospective_protocol_commit,
        "expected_member_count": EXPECTED_SET_MEMBER_COUNT,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["contract_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


# ---------------------------------------------------------------------------
# parser isolation
# ---------------------------------------------------------------------------


def load_module_without_package(path: Path, module_name: str) -> Any:
    """Import a module from a file path without executing a package ``__init__``.

    Stage E must not import parser code. Importing anything as
    ``jspace_observation.X`` runs ``jspace_observation/__init__.py``, which
    eagerly imports the legacy parser, so the package import path is closed to
    Stage E by construction rather than by convention.
    """
    path = Path(path)
    # ``spec_from_file_location`` happily returns a spec for a path that does
    # not exist; the failure only surfaces later as a FileNotFoundError from
    # ``exec_module``. Checking first keeps the refusal inside this module's
    # own error type instead of leaking an import-machinery exception that a
    # caller might catch as "some unrelated IO problem".
    if not path.is_file():
        raise LifecycleError(f"cannot load {module_name}: {path} is not a file")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise LifecycleError(f"cannot load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - re-raised as a refusal below
        sys.modules.pop(module_name, None)
        raise LifecycleError(f"cannot load {module_name} from {path}: {exc}") from exc
    return module


def assert_stage_e_import_is_parser_free(
    loaded_module_names: Iterable[str],
    *,
    parser_markers: Sequence[str] = ("eval_parsing", "parser_v3_repair", "model_loader"),
) -> None:
    """Refuse a Stage E process that has parser code in ``sys.modules``.

    ``jspace_observation`` itself is a marker only through its submodules: the
    package name alone is checked separately by the caller, because this
    function is also used to check processes that legitimately load unrelated
    helpers from the same distribution.
    """
    loaded = list(loaded_module_names)
    hits = sorted(
        {name for name in loaded for marker in parser_markers if marker in name}
    )
    if hits:
        raise LifecycleError(
            f"parser-bearing module(s) present in a Stage E process: {hits}"
        )
