"""Closed machine-readable schemas for every parser-v3-v2 cross-role artifact.

Why this module exists
======================

Section 5.1 of the controlling prompt requires closed JSON Schemas for every
cross-role and lifecycle artifact that production entrypoints actually consume,
and requires that "production entrypoints must call the same validators the
tests exercise".

The single most repeated finding in this repository's history is *a check bound
to something other than what runs*. A published schema document that some
hand-written validator only partially enforces is exactly that failure in a new
costume: the document says ``additionalProperties: false`` while the code that
runs never looks at it, so an unknown field is advertised as impossible and is
in fact accepted.

This module removes the gap by construction rather than by discipline:

* the JSON Schema documents in :data:`SCHEMAS` are the only source of truth, and
  they are emitted verbatim as the public artifacts;
* :func:`validate` interprets those same documents;
* the validator is **fail-closed on its own vocabulary** --- a schema keyword it
  does not implement is a hard error at registry-construction time, so it is
  impossible to write a constraint here that silently is not enforced;
* :func:`_assert_closed` refuses, at import time, any object schema that does not
  declare ``additionalProperties`` and ``properties``, any ``required`` naming a
  property that does not exist, any empty ``enum``, and any array without
  ``items``.

The third bullet is the load-bearing one. Every other validator design fails
open when the author writes a keyword the implementation forgot; this one fails
closed, and it fails at import, which means the test suite cannot start with an
unenforceable schema in the registry.

Dependency posture
==================

This module imports only the standard library. ``jsonschema`` is deliberately
not added: the pinned 94-package closure in ``requirements.lock.txt`` was
generated and reproduced in Azure, and widening it for a validator whose
"closed" semantics we would still have to assert separately buys nothing and
costs supply-chain surface in a project whose entire subject is integrity.

Like :mod:`jspace_observation.parser_v3_v2_lifecycle`, this module has no
intra-package imports, so it can be loaded standalone by
``load_module_without_package`` in an import-isolation control.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "SchemaError",
    "SchemaValidationError",
    "SUPPORTED_KEYWORDS",
    "SCHEMAS",
    "SCHEMA_IDS",
    "SCHEMA_DIGESTS",
    "REGISTRY_DIGEST",
    "canonical_json",
    "schema_digest",
    "get_schema",
    "validate",
    "assert_valid",
    "export_schema_documents",
]


class SchemaError(Exception):
    """Raised when a schema document itself is unusable."""


class SchemaValidationError(Exception):
    """Raised when an instance does not satisfy its schema."""


# ---------------------------------------------------------------------------
# canonical form
# ---------------------------------------------------------------------------


def canonical_json(payload: Any) -> str:
    """Return the canonical JSON text used for every digest in this module.

    NFC normalisation is applied to strings before serialisation so that two
    byte-different but canonically identical Unicode spellings cannot produce
    two different digests for the same schema.
    """

    def _norm(value: Any) -> Any:
        if isinstance(value, str):
            return unicodedata.normalize("NFC", value)
        if isinstance(value, Mapping):
            return {_norm(k): _norm(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_norm(item) for item in value]
        return value

    return json.dumps(_norm(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# the closed keyword vocabulary
# ---------------------------------------------------------------------------

#: Keywords the validator implements. Anything else in a schema is refused when
#: the registry is built, which is the property that makes a published
#: constraint and an enforced constraint the same thing.
SUPPORTED_KEYWORDS: frozenset[str] = frozenset(
    {
        # annotations, carried into the published document, not enforced
        "$schema",
        "$id",
        "title",
        "description",
        "$comment",
        # reference
        "$ref",
        # any type
        "type",
        "enum",
        "const",
        # object
        "properties",
        "required",
        "additionalProperties",
        "propertyNames",
        "minProperties",
        "maxProperties",
        # array
        "items",
        "minItems",
        "maxItems",
        "uniqueItems",
        # string
        "pattern",
        "minLength",
        "maxLength",
        # numeric
        "minimum",
        "maximum",
    }
)

_TYPES: Mapping[str, Any] = {
    "object": Mapping,
    "array": (list, tuple),
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}

_ANNOTATIONS = frozenset({"$schema", "$id", "title", "description", "$comment"})


# ---------------------------------------------------------------------------
# reusable fragments
# ---------------------------------------------------------------------------

_SHA256 = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_NAME = {"type": "string", "minLength": 1, "maxLength": 256}
_CASE_ID = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"}
_OBJECT_NAME = {"type": "string", "minLength": 1, "maxLength": 1024}
_NON_NEGATIVE = {"type": "integer", "minimum": 0}
_UNIT_INTERVAL = {"type": "number", "minimum": 0, "maximum": 1}

_STRATA = tuple(f"S{index:02d}" for index in range(1, 13))
_DECISION_CLASSES = ("present", "no_answer", "ambiguous")
_PRESENCE_CLASSES = ("present", "no_answer", "ambiguous")

#: Mirrors ``parser_v3_v2_construction.AGREEMENT_FIELDS``. It is duplicated
#: rather than imported so this module stays standalone-loadable; a test asserts
#: the two lists are identical, which is a stronger control than an import
#: because it fails loudly on drift instead of silently following it.
_AGREEMENT_FIELDS = (
    "typed_decision",
    "canonical_value",
    "canonical_candidates",
    "literal_spans",
    "span_roles",
    "ambiguity",
    "equivalence",
    "extraction_strategy",
    "output_quality",
    "warnings",
    "failure_reasons",
    "stratum",
    "subtype",
)

#: Mirrors ``parser_v3_v2_construction.QUARANTINE_REASONS``.
_QUARANTINE_REASONS = (
    "cannot_satisfy_mandatory_correct_handling",
    "compromised_blinding",
    "conflicts_with_v2_ontology",
    "failed_deterministic_validation",
    "prohibited_collision",
    "semantic_uncertainty",
    "unresolved_after_arbitration",
)

#: Mirrors ``parser_v3_v2_evaluation.PREREGISTERED_BINDINGS``.
_PREREGISTERED_BINDINGS = (
    "sealed_set_manifest_digest",
    "sealed_set_listing_witness_digest",
    "set_facts_digest",
    "final_contract_digest",
    "policy_full_file_digest",
    "policy_semantic_digest",
    "parser_v3_digest",
    "scorer_digest",
    "dependency_lock_digest",
    "base_image_digest",
    "image_payload_manifest_digest",
    "evaluation_image_digest",
    "cuda_runtime",
    "stage_p_entrypoint",
    "stage_p_command",
    "stage_p_identity",
    "stage_p_read_classes",
    "stage_e_entrypoint",
    "stage_e_command",
    "stage_e_identity",
    "stage_e_read_classes",
    "prediction_member_layout",
    "prediction_completeness_rule",
    "prediction_seal_mode",
    "prediction_listing_schema",
    "prediction_receipt_schema",
    "state_machine_digest",
    "evaluation_ordinal",
    "retry_rule",
    "binding_acceptance_criteria",
    "nonbinding_diagnostics",
    "formal_result_schema",
    "public_redaction_projection",
)

#: The binding gates ``run_stage_e`` actually emits, enumerated exactly. A
#: schema that accepted "some booleans" would pass a result whose gate set had
#: quietly shrunk, which is the one shape of drift that turns FAIL into PASS.
_BINDING_GATES = (
    "residual_pooled_zero_error",
    "residual_S04_zero_error",
    "residual_S05_zero_error",
    "residual_S06_zero_error",
    "residual_S09_zero_error",
    "canonical_present_value_exact",
    "answer_presence_class_exact",
    "no_answer_not_fabricated",
    "ambiguity_not_resolved_silently",
)

_PINNED_GATES = (
    "canonical_present_value_exact",
    "answer_presence_class_exact",
    "no_answer_not_fabricated",
    "ambiguity_not_resolved_silently",
)

_RESIDUAL_STRATA = ("S04", "S05", "S06", "S09")

#: Closed role vocabulary. Mirrors the keys of
#: ``parser_v3_v2_lifecycle.ROLE_LANES`` exactly; a control asserts the two are
#: identical, so a role added to the lane table without a schema entry fails
#: loudly instead of logging under a name nothing validates.
_ROLES = (
    "arbiter",
    "broker",
    "facts_compiler",
    "normalizer",
    "prediction_sealer",
    "preregistration_compiler",
    "private_set_auditor",
    "receipt_exporter",
    "reviewer_a",
    "reviewer_b",
    "seal_custodian",
    "selector",
    "source_custodian",
    "stage_e",
    "stage_p",
)


def _obj(properties: Mapping[str, Any], required: Sequence[str], **extra: Any) -> dict[str, Any]:
    """Build a closed object schema.

    ``additionalProperties: false`` is applied here rather than left to each
    call site, because a closed-by-default helper makes the open case something
    an author has to write on purpose.
    """
    schema: dict[str, Any] = {
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": False,
    }
    schema.update(extra)
    return schema


def _map_of(value_schema: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    """Build a closed object whose keys are exactly ``keys``."""
    return _obj({key: dict(value_schema) for key in keys}, list(keys))


def _enum_string(values: Sequence[str]) -> dict[str, Any]:
    return {"type": "string", "enum": list(values)}


_LITERAL_SPAN = _obj(
    {
        "literal": {"type": "boolean", "const": True},
        "start": _NON_NEGATIVE,
        "end": _NON_NEGATIVE,
        "text": {"type": "string", "minLength": 1, "maxLength": 4096},
        "role": {"type": "string", "minLength": 1, "maxLength": 64},
    },
    ["literal", "start", "end", "text"],
)

_PUBLIC_ONTOLOGY_PACKET = _obj(
    {
        "ontology_version": _NAME,
        "stratum_definitions_digest": _SHA256,
        "subtype_slots": {
            "type": "array",
            "items": _NAME,
            "minItems": 1,
            "uniqueItems": True,
        },
    },
    ["ontology_version", "stratum_definitions_digest", "subtype_slots"],
)

#: The per-field shapes of the thirteen agreement fields, defined once.
#:
#: The reviewer decision and the arbitration result must describe the same
#: values, so they are built from this one table. Two hand-maintained copies
#: would eventually disagree, and the disagreement would appear as an arbiter
#: producing a "valid" resolution the reviewers could never have produced.
_AGREEMENT_FIELD_SCHEMAS: Mapping[str, Any] = {
    "typed_decision": _enum_string(_DECISION_CLASSES),
    "canonical_value": {"type": ["string", "null"], "maxLength": 4096},
    "canonical_candidates": {
        "type": "array",
        "items": {"type": "string", "maxLength": 4096},
        "maxItems": 64,
    },
    "literal_spans": {"type": "array", "items": _LITERAL_SPAN, "maxItems": 64},
    "span_roles": {
        "type": "array",
        "items": {"type": "string", "minLength": 1, "maxLength": 64},
        "maxItems": 64,
    },
    "ambiguity": {"type": "boolean"},
    "equivalence": {"type": "string", "minLength": 1, "maxLength": 64},
    "extraction_strategy": {"type": "string", "minLength": 1, "maxLength": 64},
    "output_quality": {"type": "string", "minLength": 1, "maxLength": 64},
    "warnings": {
        "type": "array",
        "items": {"type": "string", "minLength": 1, "maxLength": 256},
        "maxItems": 64,
    },
    "failure_reasons": {
        "type": "array",
        "items": {"type": "string", "minLength": 1, "maxLength": 256},
        "maxItems": 64,
    },
    "stratum": _enum_string(_STRATA),
    "subtype": {"type": "string", "minLength": 1, "maxLength": 128},
}


# ---------------------------------------------------------------------------
# the registry
# ---------------------------------------------------------------------------


def _sid(name: str) -> str:
    return f"phase1-parser-v3-v2-{name}/v1"


_RAW_SCHEMAS: dict[str, dict[str, Any]] = {}


def _register(name: str, title: str, description: str, body: Mapping[str, Any]) -> str:
    schema_id = _sid(name)
    document = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_id,
        "title": title,
        "description": description,
    }
    document.update(body)
    if schema_id in _RAW_SCHEMAS:
        raise SchemaError(f"duplicate schema id {schema_id!r}")
    _RAW_SCHEMAS[schema_id] = document
    return schema_id


# --- construction lane -----------------------------------------------------

BLINDED_CASE_PACKET = _register(
    "blinded-case-packet",
    "Blinded case packet",
    "The only payload a reviewer may receive. Every input that would break "
    "reviewer independence is absent by closure rather than by a denylist: "
    "because additionalProperties is false, old_label, migrated_label, "
    "parser_code, parser_result, prediction, reuse_status, "
    "other_reviewer_decision and arbitration_record are all unrepresentable.",
    _obj(
        {
            "schema_version": {"const": _sid("blinded-case-packet")},
            "packet_id": _NAME,
            "case_ref": _NAME,
            "case_content": {"type": "string", "minLength": 1, "maxLength": 65536},
            "public_ontology_packet": _PUBLIC_ONTOLOGY_PACKET,
        },
        ["schema_version", "packet_id", "case_ref", "case_content", "public_ontology_packet"],
    ),
)

REVIEWER_DECISION = _register(
    "reviewer-decision",
    "Reviewer decision",
    "One reviewer's independent decision. Every scoring-relevant agreement "
    "field is required, because a decision missing a field must count as a "
    "disagreement rather than as silent concurrence.",
    _obj(
        {
            "schema_version": {"const": _sid("reviewer-decision")},
            "reviewer_id": _enum_string(["reviewer_a", "reviewer_b"]),
            "case_ref": _NAME,
            **{name: dict(sub) for name, sub in _AGREEMENT_FIELD_SCHEMAS.items()},
            "decision_digest": _SHA256,
        },
        ["schema_version", "reviewer_id", "case_ref", *_AGREEMENT_FIELDS, "decision_digest"],
    ),
)

DISAGREEMENT_PACKET = _register(
    "disagreement-packet",
    "Disagreement packet",
    "What the broker hands the arbiter. The old label and every parser-bearing "
    "input are unrepresentable before adjudication because this document is "
    "closed and does not declare them.",
    _obj(
        {
            "schema_version": {"const": _sid("disagreement-packet")},
            "case_ref": _NAME,
            "case_content": {"type": "string", "minLength": 1, "maxLength": 65536},
            "public_ontology_packet": _PUBLIC_ONTOLOGY_PACKET,
            "reviewer_a": {"$ref": REVIEWER_DECISION},
            "reviewer_b": {"$ref": REVIEWER_DECISION},
            "disagreeing_fields": {
                "type": "array",
                "items": _enum_string(_AGREEMENT_FIELDS),
                "minItems": 1,
                "uniqueItems": True,
            },
        },
        [
            "schema_version",
            "case_ref",
            "case_content",
            "reviewer_a",
            "reviewer_b",
            "disagreeing_fields",
        ],
    ),
)

ARBITRATION_RESULT = _register(
    "arbitration-result",
    "Arbitration result",
    "The arbiter's adjudication. 'unresolved' is a first-class outcome that "
    "routes to quarantine; it is not a way to admit a case with a guess.",
    _obj(
        {
            "schema_version": {"const": _sid("arbitration-result")},
            "case_ref": _NAME,
            "arbiter_id": _NAME,
            "adjudication_permanently_recorded": {"type": "boolean", "const": True},
            "outcome": _enum_string(["adjudicated", "unresolved"]),
            "resolved_fields": _obj(
                {name: dict(sub) for name, sub in _AGREEMENT_FIELD_SCHEMAS.items()},
                [],
            ),
            "arbitration_digest": _SHA256,
        },
        [
            "schema_version",
            "case_ref",
            "arbiter_id",
            "adjudication_permanently_recorded",
            "outcome",
            "arbitration_digest",
        ],
    ),
)

ADMISSION_RECORD = _register(
    "admission-record",
    "Admission record",
    "One admitted case. Mirrors exactly what assert_final_set_invariants "
    "requires, so a set that validates against this schema and then fails the "
    "invariant check indicates schema drift rather than a merely unlucky set.",
    _obj(
        {
            "schema_version": {"const": _sid("admission-record")},
            "case_id": _CASE_ID,
            "stratum": _enum_string(_STRATA),
            "decision_class": _enum_string(_DECISION_CLASSES),
            "eligible": {"type": "boolean", "const": True},
            "adjudicable": {"type": "boolean", "const": True},
            "mandatory": {"type": "boolean", "const": True},
            "unresolved": {"type": "boolean", "const": False},
            "subtype_slot": {"type": "string", "minLength": 1, "maxLength": 128},
            "literal_spans": {"type": "array", "items": _LITERAL_SPAN, "maxItems": 64},
            "rightmost_distractor_registration": {"type": "boolean"},
            "ambiguity_registration": {"type": "boolean"},
            "content_digest": _SHA256,
        },
        [
            "schema_version",
            "case_id",
            "stratum",
            "decision_class",
            "eligible",
            "adjudicable",
            "mandatory",
            "unresolved",
            "subtype_slot",
            "literal_spans",
            "content_digest",
        ],
    ),
)

QUARANTINE_RECORD = _register(
    "quarantine-record",
    "Quarantine record",
    "Why a case left the pool. The reason enum is closed to the seven "
    "registered reasons; there is no 'other', because an open reason list is "
    "where an inconvenient case gets removed.",
    _obj(
        {
            "schema_version": {"const": _sid("quarantine-record")},
            "case_id": _CASE_ID,
            "reason": _enum_string(_QUARANTINE_REASONS),
            "recorded_at_batch": _NON_NEGATIVE,
            "quarantine_digest": _SHA256,
        },
        ["schema_version", "case_id", "reason", "recorded_at_batch", "quarantine_digest"],
    ),
)

REPLACEMENT_RECORD = _register(
    "replacement-record",
    "Replacement record",
    "One bounded replacement. The cumulative count is carried in the record "
    "itself so the bound is auditable from the artifacts alone rather than "
    "from a coordinator's memory.",
    _obj(
        {
            "schema_version": {"const": _sid("replacement-record")},
            "replaced_case_id": _CASE_ID,
            "replacement_case_id": _CASE_ID,
            "batch_index": _NON_NEGATIVE,
            "batch_size": {"type": "integer", "minimum": 1},
            "cumulative_replacements": _NON_NEGATIVE,
            "within_limit": {"type": "boolean", "const": True},
        },
        [
            "schema_version",
            "replaced_case_id",
            "replacement_case_id",
            "batch_index",
            "batch_size",
            "cumulative_replacements",
            "within_limit",
        ],
    ),
)

CONSTRUCTION_PLAN = _register(
    "construction-plan",
    "Construction plan",
    "The create-only write plan for the set seal. Both the planned object set "
    "and the write order are carried, because create-only and "
    "terminal-manifest-last are two different failures.",
    _obj(
        {
            "schema_version": {"const": _sid("construction-plan")},
            "plan_id": _NAME,
            "total_cases": {"type": "integer", "const": 120},
            "stratum_quota": {"type": "integer", "const": 10},
            "decision_class_quota": _map_of(_NON_NEGATIVE, _DECISION_CLASSES),
            "planned_objects": {
                "type": "array",
                "items": _OBJECT_NAME,
                "minItems": 1,
                "uniqueItems": True,
            },
            "write_order": {"type": "array", "items": _OBJECT_NAME, "minItems": 1},
            "terminal_manifest": _OBJECT_NAME,
        },
        [
            "schema_version",
            "plan_id",
            "total_cases",
            "stratum_quota",
            "decision_class_quota",
            "planned_objects",
            "write_order",
            "terminal_manifest",
        ],
    ),
)

SET_FACTS_PROJECTION = _register(
    "set-facts-projection",
    "Set-facts projection",
    "The content-free projection of the constructed set. Deliberately carries "
    "no field whose name contains a parser-bearing fragment, so it survives "
    "assert_no_parser_field unchanged.",
    _obj(
        {
            "schema_version": {"const": _sid("set-facts-projection")},
            "set_id": _NAME,
            "member_count": {"type": "integer", "const": 120},
            "per_stratum_count": _map_of(_NON_NEGATIVE, _STRATA),
            "per_decision_class_count": _map_of(_NON_NEGATIVE, _DECISION_CLASSES),
            "gate_pinned_count": _NON_NEGATIVE,
            "residual_count": _NON_NEGATIVE,
            "quarantined_count": _NON_NEGATIVE,
            "replacement_count": _NON_NEGATIVE,
            "facts_digest": _SHA256,
        },
        [
            "schema_version",
            "set_id",
            "member_count",
            "per_stratum_count",
            "per_decision_class_count",
            "gate_pinned_count",
            "residual_count",
            "quarantined_count",
            "replacement_count",
            "facts_digest",
        ],
    ),
)

# --- sealing lane ----------------------------------------------------------

PLANNED_SEAL_MEMBERS = _register(
    "planned-seal-members",
    "Planned seal members",
    "Exactly the objects the seal will create, before it creates them.",
    _obj(
        {
            "schema_version": {"const": _sid("planned-seal-members")},
            "prefix": _OBJECT_NAME,
            "members": {
                "type": "array",
                "items": _obj(
                    {"object_name": _OBJECT_NAME, "case_id": _CASE_ID, "member_digest": _SHA256},
                    ["object_name", "case_id", "member_digest"],
                ),
                "minItems": 1,
                "maxItems": 120,
                "uniqueItems": True,
            },
            "terminal_manifest": _OBJECT_NAME,
        },
        ["schema_version", "prefix", "members", "terminal_manifest"],
    ),
)

TERMINAL_MANIFEST = _register(
    "terminal-manifest",
    "Terminal manifest",
    "The last object a seal writes. A manifest written before its members "
    "describes a set that does not yet exist, so the write position is part of "
    "the record and not an implementation detail.",
    _obj(
        {
            "schema_version": {"const": _sid("terminal-manifest")},
            "set_id": _NAME,
            "member_count": {"type": "integer", "const": 120},
            "listing_witness_digest": _SHA256,
            "set_digest": _SHA256,
            "write_position": _enum_string(["last"]),
            "manifest_digest": _SHA256,
        },
        [
            "schema_version",
            "set_id",
            "member_count",
            "listing_witness_digest",
            "set_digest",
            "write_position",
            "manifest_digest",
        ],
    ),
)

AUTHENTICATED_LISTING_PROJECTION = _register(
    "authenticated-listing-projection",
    "Authenticated listing projection",
    "The server-side listing, projected to identifiers and digests only.",
    _obj(
        {
            "schema_version": {"const": _sid("authenticated-listing-projection")},
            "prefix": _OBJECT_NAME,
            "entries": {
                "type": "array",
                "items": _obj(
                    {"object_name": _OBJECT_NAME, "content_digest": _SHA256},
                    ["object_name", "content_digest"],
                ),
                "minItems": 1,
                "uniqueItems": True,
            },
            "listing_digest": _SHA256,
        },
        ["schema_version", "prefix", "entries", "listing_digest"],
    ),
)

LISTING_WITNESS_RECEIPT = _register(
    "listing-witness-receipt",
    "Listing-witness receipt",
    "Proof that what the seal planned and what the store lists are the same "
    "set, computed from the store's own listing rather than from the writer's "
    "claim about it.",
    _obj(
        {
            "schema_version": {"const": _sid("listing-witness-receipt")},
            "prefix": _OBJECT_NAME,
            "planned_digest": _SHA256,
            "listed_digest": _SHA256,
            "matches": {"type": "boolean", "const": True},
            "witness_digest": _SHA256,
        },
        ["schema_version", "prefix", "planned_digest", "listed_digest", "matches", "witness_digest"],
    ),
)

FINAL_CONTRACT_RECEIPT = _register(
    "final-contract-receipt",
    "Final-contract receipt",
    "The one-time compiled contract. Compiled once, from the sealed set, and "
    "never recompiled.",
    _obj(
        {
            "schema_version": {"const": _sid("final-contract-receipt")},
            "contract_id": _NAME,
            "compiled_from_set_digest": _SHA256,
            "policy_full_file_digest": _SHA256,
            "policy_semantic_digest": _SHA256,
            "compilation_ordinal": {"type": "integer", "const": 0},
            "contract_digest": _SHA256,
        },
        [
            "schema_version",
            "contract_id",
            "compiled_from_set_digest",
            "policy_full_file_digest",
            "policy_semantic_digest",
            "compilation_ordinal",
            "contract_digest",
        ],
    ),
)

# --- evaluation lane -------------------------------------------------------

PREREGISTRATION_LOCK = _register(
    "preregistration-lock",
    "Preregistration lock",
    "The closed binding set. Required and closed at once: a missing binding "
    "means the run was not fully preregistered, and an extra binding means the "
    "run could be authorised against something nobody registered.",
    _obj(
        {
            "schema_version": {"const": "phase1-parser-v3-v2-preregistration/v1"},
            "sealed_set_manifest_digest": _SHA256,
            "sealed_set_listing_witness_digest": _SHA256,
            "set_facts_digest": _SHA256,
            "final_contract_digest": _SHA256,
            "policy_full_file_digest": _SHA256,
            "policy_semantic_digest": _SHA256,
            "parser_v3_digest": _SHA256,
            "scorer_digest": _SHA256,
            "dependency_lock_digest": _SHA256,
            "base_image_digest": _NAME,
            "image_payload_manifest_digest": _SHA256,
            "evaluation_image_digest": _NAME,
            "cuda_runtime": _NAME,
            "stage_p_entrypoint": _NAME,
            "stage_p_command": {"type": "array", "items": _NAME, "minItems": 1},
            "stage_p_identity": _NAME,
            "stage_p_read_classes": {
                "type": "array",
                "items": _NAME,
                "minItems": 1,
                "uniqueItems": True,
            },
            "stage_e_entrypoint": _NAME,
            "stage_e_command": {"type": "array", "items": _NAME, "minItems": 1},
            "stage_e_identity": _NAME,
            "stage_e_read_classes": {
                "type": "array",
                "items": _NAME,
                "minItems": 1,
                "uniqueItems": True,
            },
            "prediction_member_layout": _NAME,
            "prediction_completeness_rule": _NAME,
            "prediction_seal_mode": {"const": "create_only"},
            "prediction_listing_schema": _NAME,
            "prediction_receipt_schema": _NAME,
            "state_machine_digest": _SHA256,
            "evaluation_ordinal": {"type": "integer", "const": 0},
            "retry_rule": _NAME,
            "binding_acceptance_criteria": {
                "type": "array",
                "items": _NAME,
                "minItems": 1,
                "uniqueItems": True,
            },
            "nonbinding_diagnostics": {
                "type": "array",
                "items": _NAME,
                "minItems": 1,
                "uniqueItems": True,
            },
            "formal_result_schema": _NAME,
            "public_redaction_projection": _NAME,
        },
        ["schema_version", *_PREREGISTERED_BINDINGS],
    ),
)

_PARSER_OUTPUT = _obj(
    {
        "answer_presence": _enum_string(_PRESENCE_CLASSES),
        "canonical_value": {"type": ["string", "null"], "maxLength": 4096},
        "canonical_candidates": {
            "type": "array",
            "items": {"type": "string", "maxLength": 4096},
            "maxItems": 64,
        },
        "literal_spans": {"type": "array", "items": _LITERAL_SPAN, "maxItems": 64},
        "span_roles": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 64},
            "maxItems": 64,
        },
        "ambiguity": {"type": "boolean"},
        "equivalence": {"type": "string", "minLength": 1, "maxLength": 64},
        "extraction_strategy": {"type": "string", "minLength": 1, "maxLength": 64},
        "output_quality": {"type": "string", "minLength": 1, "maxLength": 64},
        "warnings": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 256},
            "maxItems": 64,
        },
        "failure_reasons": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 256},
            "maxItems": 64,
        },
        "typed_decision": _enum_string(_DECISION_CLASSES),
        "subtype": {"type": "string", "minLength": 1, "maxLength": 128},
    },
    ["answer_presence"],
)

PREDICTION_MEMBER = _register(
    "prediction-member",
    "Prediction member",
    "One sealed prediction, exactly as run_stage_p emits it. The parser output "
    "is itself closed: the preregistration binds prediction_member_layout, so a "
    "member carrying an unregistered field is a layout change and must be "
    "refused rather than tolerated.",
    _obj(
        {
            "case_id": _CASE_ID,
            "position": _NON_NEGATIVE,
            "source_digest": _SHA256,
            "prediction": _PARSER_OUTPUT,
            "member_digest": _SHA256,
        },
        ["case_id", "position", "source_digest", "prediction", "member_digest"],
    ),
)

PREDICTION_MANIFEST = _register(
    "prediction-manifest",
    "Prediction manifest",
    "The unsealed Stage P stream. Representable while partial on purpose: a "
    "design in which producing and sealing are one step cannot demonstrate "
    "that a partial stream is refused.",
    _obj(
        {
            "state": {"const": "PREDICTION_RUNNING"},
            "ordinal": {"type": "integer", "const": 0},
            "lock_digest": _SHA256,
            "members": {
                "type": "array",
                "items": {"$ref": PREDICTION_MEMBER},
                "minItems": 0,
                "maxItems": 120,
            },
        },
        ["state", "ordinal", "lock_digest", "members"],
    ),
)

PREDICTION_RECEIPT = _register(
    "prediction-receipt",
    "Prediction receipt",
    "The create-only prediction seal receipt, exactly as seal_prediction_stream "
    "emits it.",
    _obj(
        {
            "state": {"const": "PREDICTION_SEALED"},
            "ordinal": {"type": "integer", "const": 0},
            "lock_digest": _SHA256,
            "member_count": {"type": "integer", "const": 120},
            "listing_witness_digest": _SHA256,
            "stream_digest": _SHA256,
            "write_order": {"type": "array", "items": _OBJECT_NAME, "minItems": 1},
            "receipt_digest": _SHA256,
        },
        [
            "state",
            "ordinal",
            "lock_digest",
            "member_count",
            "listing_witness_digest",
            "stream_digest",
            "write_order",
            "receipt_digest",
        ],
    ),
)

STAGE_E_RESULT = _register(
    "stage-e-result",
    "Stage-E formal result",
    "The unique formal result. The binding gate set is enumerated exactly, "
    "because a result whose gate set had quietly shrunk is the one shape of "
    "drift that converts FAIL into PASS while every gate present still reads "
    "true.",
    _obj(
        {
            "schema_version": {"const": "phase1-parser-v3-v2-formal-result/v1"},
            "state": _enum_string(["EVALUATED_ACCEPTED", "EVALUATED_NOT_ACCEPTED"]),
            "ordinal": {"type": "integer", "const": 1},
            "lock_digest": _SHA256,
            "prediction_receipt_digest": _SHA256,
            "eligible_case_count": {"type": "integer", "const": 120},
            "status": _enum_string(["PASS", "FAIL"]),
            "binding_gates": _map_of({"type": "boolean"}, _BINDING_GATES),
            "residual_mismatches": _map_of(_NON_NEGATIVE, _RESIDUAL_STRATA),
            "pinned_mismatches": _map_of(_NON_NEGATIVE, _PINNED_GATES),
            "nonbinding_diagnostics": _obj(
                {
                    "answer_presence_confusion_matrix": _map_of(
                        _map_of(_NON_NEGATIVE, _PRESENCE_CLASSES), _PRESENCE_CLASSES
                    ),
                    "per_class_precision": _map_of(_UNIT_INTERVAL, _PRESENCE_CLASSES),
                    "per_class_recall": _map_of(_UNIT_INTERVAL, _PRESENCE_CLASSES),
                    "per_class_f1": _map_of(_UNIT_INTERVAL, _PRESENCE_CLASSES),
                    "macro_f1": _UNIT_INTERVAL,
                    "parser_v2_comparison": _enum_string(["FINAL", "NOT_RUN", "REPORT_ONLY"]),
                    "note": {"type": "string", "minLength": 1, "maxLength": 1024},
                },
                [
                    "answer_presence_confusion_matrix",
                    "per_class_precision",
                    "per_class_recall",
                    "per_class_f1",
                    "macro_f1",
                    "parser_v2_comparison",
                    "note",
                ],
            ),
            "result_digest": _SHA256,
        },
        [
            "schema_version",
            "state",
            "ordinal",
            "lock_digest",
            "prediction_receipt_digest",
            "eligible_case_count",
            "status",
            "binding_gates",
            "residual_mismatches",
            "pinned_mismatches",
            "nonbinding_diagnostics",
            "result_digest",
        ],
    ),
)

TERMINAL_STATE_RECEIPT = _register(
    "terminal-state-receipt",
    "Terminal-state receipt",
    "The single declared terminal state for the round, with the exact facts "
    "that justify it.",
    _obj(
        {
            "schema_version": {"const": _sid("terminal-state-receipt")},
            "terminal_state": _enum_string(
                [
                    "PARSER_V3_VALIDATED_READY_FOR_JSPACE_EXPERIMENT",
                    "PARSER_V3_EVALUATED_NOT_ACCEPTED",
                    "FORMAL_EVALUATION_INVALID",
                    "READY_FOR_SINGLE_LAUNCH_EVALUATION",
                    "SEALED_READY_FOR_PREREGISTRATION",
                    "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY",
                    "BLOCKED_ON_MODEL_AVAILABILITY_OR_QUOTA",
                    "BLOCKED_ON_EGRESS_CONTROL",
                    "BLOCKED_ON_REVIEW_DATA_GOVERNANCE",
                    "BLOCKED_ON_CLOUD_EXECUTION",
                    "BLOCKED_ON_PRIVATE_SOURCE_ACCESS",
                    "BLOCKED_ON_INDEPENDENCE",
                    "BLOCKED_ON_SET_REPAIR",
                    "BLOCKED_ON_SEALING",
                    "BLOCKED_ON_PROTOCOL_INTEGRITY",
                    "BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE",
                    "BLOCKED_ON_GIT_CREDENTIAL",
                    "BLOCKED_ON_GIT_DIVERGENCE",
                ]
            ),
            "bound_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "bound_tree": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "evaluation_ordinal": {"type": "integer", "minimum": 0, "maximum": 1},
            "receipt_digest": _SHA256,
        },
        [
            "schema_version",
            "terminal_state",
            "bound_commit",
            "bound_tree",
            "evaluation_ordinal",
            "receipt_digest",
        ],
    ),
)

# --- infrastructure lane ---------------------------------------------------

DEPLOYMENT_EVIDENCE = _register(
    "deployment-evidence",
    "Deployment and read-back evidence",
    "What a deployment actually produced, read back from the control plane "
    "rather than asserted by the deployer.",
    _obj(
        {
            "schema_version": {"const": _sid("deployment-evidence")},
            "deployment_name": _NAME,
            "resource_group": _NAME,
            "location": _NAME,
            "template_digest": _SHA256,
            "parameter_digest": _SHA256,
            "provisioning_state": _enum_string(["Succeeded", "Failed", "Canceled", "Running"]),
            "read_back_matches_template": {"type": "boolean"},
            "outputs_digest": _SHA256,
            "evidence_digest": _SHA256,
        },
        [
            "schema_version",
            "deployment_name",
            "resource_group",
            "location",
            "template_digest",
            "parameter_digest",
            "provisioning_state",
            "read_back_matches_template",
            "outputs_digest",
            "evidence_digest",
        ],
    ),
)

RUNTIME_CANARY_RESULT = _register(
    "runtime-canary-result",
    "Runtime canary result",
    "A positive or negative runtime control. A negative canary that did not "
    "actually fail is recorded as a failed control, not as a pass: a boundary "
    "test that never observed a refusal has demonstrated nothing.",
    _obj(
        {
            "schema_version": {"const": _sid("runtime-canary-result")},
            "canary_id": _NAME,
            "polarity": _enum_string(["positive", "negative"]),
            "expected_outcome": _enum_string(["allowed", "refused"]),
            "observed_outcome": _enum_string(["allowed", "refused", "inconclusive"]),
            "control_satisfied": {"type": "boolean"},
            "event_id": _NAME,
            "result_digest": _SHA256,
        },
        [
            "schema_version",
            "canary_id",
            "polarity",
            "expected_outcome",
            "observed_outcome",
            "control_satisfied",
            "event_id",
            "result_digest",
        ],
    ),
)

ACCESS_EVENT = _register(
    "access-event",
    "Access event",
    "A content-free access record. Only closed identifiers and statuses are "
    "representable, so a raw prompt, response, private object name or "
    "content-bearing exception cannot be logged through this schema.",
    _obj(
        {
            "schema_version": {"const": _sid("access-event")},
            "event_id": {
                "type": "string",
                "enum": [
                    "lane_check_passed",
                    "lane_check_refused",
                    "payload_read_started",
                    "payload_read_completed",
                    "payload_write_created",
                    "payload_write_refused",
                    "schema_validation_passed",
                    "schema_validation_refused",
                    "role_assertion_passed",
                    "role_assertion_refused",
                    "identity_assertion_passed",
                    "identity_assertion_refused",
                    "import_isolation_passed",
                    "import_isolation_refused",
                    "entrypoint_started",
                    "entrypoint_completed",
                    "entrypoint_refused",
                ],
            },
            "role": _enum_string(_ROLES),
            "status": _enum_string(["ok", "refused"]),
            "read_class": {"type": ["string", "null"], "maxLength": 128},
            "object_count": _NON_NEGATIVE,
            "occurred_at_step": _NON_NEGATIVE,
        },
        ["schema_version", "event_id", "role", "status", "occurred_at_step"],
    ),
)

PUBLIC_RECEIPT = _register(
    "public-receipt",
    "Content-free public receipt",
    "The only artifact class that may leave the private boundary. Every field "
    "is an identifier, a count, a digest or a closed status; no field can carry "
    "case content.",
    _obj(
        {
            "schema_version": {"const": _sid("public-receipt")},
            "receipt_id": _NAME,
            "bound_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "counts": _obj(
                {
                    "private_semantic_reads": _NON_NEGATIVE,
                    "sealed_sets": _NON_NEGATIVE,
                    "preregistrations": _NON_NEGATIVE,
                    "stage_p_runs": _NON_NEGATIVE,
                    "stage_e_runs": _NON_NEGATIVE,
                },
                [
                    "private_semantic_reads",
                    "sealed_sets",
                    "preregistrations",
                    "stage_p_runs",
                    "stage_e_runs",
                ],
            ),
            "digests": _obj(
                {
                    "policy_full_file_digest": _SHA256,
                    "policy_semantic_digest": _SHA256,
                    "dependency_lock_digest": _SHA256,
                    "schema_registry_digest": _SHA256,
                },
                [
                    "policy_full_file_digest",
                    "policy_semantic_digest",
                    "dependency_lock_digest",
                    "schema_registry_digest",
                ],
            ),
            "receipt_digest": _SHA256,
        },
        ["schema_version", "receipt_id", "bound_commit", "counts", "digests", "receipt_digest"],
    ),
)


# ---------------------------------------------------------------------------
# structural gate: refuse an unenforceable schema at import time
# ---------------------------------------------------------------------------


def _assert_closed(schema: Mapping[str, Any], path: str) -> None:
    """Refuse any schema this validator could not fully enforce.

    Runs at import. A schema that reaches the registry is therefore one whose
    every keyword is implemented below, which is what makes the published
    document and the enforced behaviour the same object.
    """
    if not isinstance(schema, Mapping):
        raise SchemaError(f"{path}: schema must be a mapping, got {type(schema).__name__}")

    unknown = sorted(set(schema) - SUPPORTED_KEYWORDS)
    if unknown:
        raise SchemaError(
            f"{path}: keyword(s) {unknown} are not implemented by this validator. "
            "Implement them or remove them; an advertised constraint that is not "
            "enforced is worse than no constraint."
        )

    if "$ref" in schema:
        extra = sorted(set(schema) - _ANNOTATIONS - {"$ref"})
        if extra:
            raise SchemaError(f"{path}: $ref must not be combined with {extra}")
        return

    declared = schema.get("type")
    if declared is None:
        if not ({"enum", "const"} & set(schema)):
            raise SchemaError(f"{path}: schema must declare a type, enum or const")
        types: tuple[str, ...] = ()
    elif isinstance(declared, str):
        types = (declared,)
    elif isinstance(declared, list) and declared:
        types = tuple(declared)
    else:
        raise SchemaError(f"{path}: type must be a string or a non-empty list")

    for name in types:
        if name not in _TYPES:
            raise SchemaError(f"{path}: unknown type {name!r}")

    if "enum" in schema:
        if not isinstance(schema["enum"], list) or not schema["enum"]:
            raise SchemaError(f"{path}: enum must be a non-empty list")

    if "object" in types:
        if "properties" not in schema:
            raise SchemaError(f"{path}: object schema must declare properties")
        if "additionalProperties" not in schema:
            raise SchemaError(
                f"{path}: object schema must declare additionalProperties; "
                "closedness is never inherited by default here"
            )
        additional = schema["additionalProperties"]
        if additional is not False:
            if not isinstance(additional, Mapping):
                raise SchemaError(
                    f"{path}: additionalProperties must be false or a documented "
                    "extension schema"
                )
            if "propertyNames" not in schema:
                raise SchemaError(
                    f"{path}: an open extension object must constrain propertyNames"
                )
            _assert_closed(additional, f"{path}.additionalProperties")
        properties = schema["properties"]
        if not isinstance(properties, Mapping):
            raise SchemaError(f"{path}: properties must be a mapping")
        for key, sub in properties.items():
            _assert_closed(sub, f"{path}.properties.{key}")
        required = schema.get("required", [])
        if not isinstance(required, list):
            raise SchemaError(f"{path}: required must be a list")
        if additional is False:
            missing = sorted(set(required) - set(properties))
            if missing:
                raise SchemaError(
                    f"{path}: required names {missing} that are not declared properties, "
                    "so the schema can never be satisfied"
                )
        if "propertyNames" in schema:
            _assert_closed(schema["propertyNames"], f"{path}.propertyNames")

    if "array" in types:
        if "items" not in schema:
            raise SchemaError(f"{path}: array schema must declare items")
        _assert_closed(schema["items"], f"{path}.items")


for _schema_id, _document in _RAW_SCHEMAS.items():
    _assert_closed(_document, _schema_id)

#: Every registered schema, keyed by ``$id``. This mapping is the published
#: artifact and the enforced constraint at once.
SCHEMAS: Mapping[str, Mapping[str, Any]] = dict(_RAW_SCHEMAS)

SCHEMA_IDS: tuple[str, ...] = tuple(sorted(SCHEMAS))


def schema_digest(schema_id: str) -> str:
    """Return the canonical SHA-256 of one schema document."""
    if schema_id not in SCHEMAS:
        raise SchemaError(f"unregistered schema id {schema_id!r}")
    return _digest(SCHEMAS[schema_id])


SCHEMA_DIGESTS: Mapping[str, str] = {sid: _digest(doc) for sid, doc in SCHEMAS.items()}

#: One digest over the whole registry, so a single comparison detects the
#: addition, removal or edit of any schema.
REGISTRY_DIGEST: str = _digest(dict(sorted(SCHEMA_DIGESTS.items())))


def get_schema(schema_id: str) -> Mapping[str, Any]:
    if schema_id not in SCHEMAS:
        raise SchemaError(f"unregistered schema id {schema_id!r}")
    return SCHEMAS[schema_id]


# ---------------------------------------------------------------------------
# the validator
# ---------------------------------------------------------------------------


def _type_matches(value: Any, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if name == "object":
        return isinstance(value, Mapping)
    if name == "array":
        return isinstance(value, (list, tuple))
    if name == "string":
        return isinstance(value, str)
    raise SchemaError(f"unknown type {name!r}")


def _validate(
    instance: Any,
    schema: Mapping[str, Any],
    path: str,
    errors: list[str],
    seen: tuple[str, ...],
) -> None:
    if "$ref" in schema:
        target = schema["$ref"]
        if target in seen:
            errors.append(f"{path}: cyclic $ref through {target!r}")
            return
        _validate(instance, get_schema(target), path, errors, seen + (target,))
        return

    declared = schema.get("type")
    if declared is not None:
        names = (declared,) if isinstance(declared, str) else tuple(declared)
        if not any(_type_matches(instance, name) for name in names):
            errors.append(
                f"{path}: expected type {'|'.join(names)}, got {type(instance).__name__}"
            )
            return

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {schema['enum']}")

    declares_object = bool(
        {"properties", "additionalProperties", "required", "propertyNames",
         "minProperties", "maxProperties"}
        & set(schema)
    )
    declares_array = bool({"items", "minItems", "maxItems", "uniqueItems"} & set(schema))

    if isinstance(instance, Mapping) and declares_object:
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", False)
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{path}: missing required property {name!r}")
        for key, value in instance.items():
            child = f"{path}.{key}"
            if key in properties:
                _validate(value, properties[key], child, errors, seen)
            elif additional is False:
                errors.append(
                    f"{child}: unknown property {key!r} is not permitted; this "
                    "object is closed"
                )
            else:
                if "propertyNames" in schema:
                    _validate(key, schema["propertyNames"], f"{child}<key>", errors, seen)
                _validate(value, additional, child, errors, seen)
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errors.append(f"{path}: fewer than {schema['minProperties']} properties")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            errors.append(f"{path}: more than {schema['maxProperties']} properties")

    elif isinstance(instance, (list, tuple)) and declares_array:
        items = schema.get("items")
        if items is not None:
            for index, value in enumerate(instance):
                _validate(value, items, f"{path}[{index}]", errors, seen)
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen_items = [canonical_json(item) for item in instance]
            if len(set(seen_items)) != len(seen_items):
                errors.append(f"{path}: items must be unique")

    elif isinstance(instance, str):
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: does not match {schema['pattern']!r}")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']}")

    elif isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above maximum {schema['maximum']}")


def validate(schema_id: str, instance: Any) -> tuple[str, ...]:
    """Return every way ``instance`` fails ``schema_id``.

    All violations are collected rather than only the first, because a caller
    repairing an artifact one error per run will eventually stop reading them.
    """
    errors: list[str] = []
    _validate(instance, get_schema(schema_id), "$", errors, (schema_id,))
    return tuple(errors)


def assert_valid(schema_id: str, instance: Any) -> None:
    """Raise unless ``instance`` satisfies ``schema_id`` exactly."""
    errors = validate(schema_id, instance)
    if errors:
        raise SchemaValidationError(
            f"{schema_id}: {len(errors)} violation(s): " + "; ".join(errors)
        )


def export_schema_documents() -> Mapping[str, str]:
    """Return ``{filename: json text}`` for publishing the registry."""
    return {
        f"{sid.replace('/', '_')}.json": json.dumps(doc, indent=2, sort_keys=True) + "\n"
        for sid, doc in SCHEMAS.items()
    }


def assert_registry_matches(expected: Mapping[str, str]) -> None:
    """Refuse any drift between this registry and a bound digest table."""
    actual = dict(SCHEMA_DIGESTS)
    missing = sorted(set(expected) - set(actual))
    if missing:
        raise SchemaError(f"bound schema id(s) absent from the registry: {missing}")
    added = sorted(set(actual) - set(expected))
    if added:
        raise SchemaError(f"registry carries unbound schema id(s): {added}")
    changed = sorted(sid for sid in expected if expected[sid] != actual[sid])
    if changed:
        raise SchemaError(f"schema document(s) changed after binding: {changed}")


def assert_all_ids_reachable(ids: Iterable[str]) -> None:
    """Refuse a caller that names a schema this registry does not carry."""
    unknown = sorted(set(ids) - set(SCHEMAS))
    if unknown:
        raise SchemaError(f"unregistered schema id(s): {unknown}")
