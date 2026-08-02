"""Controls for the closed schema registry.

The registry's whole claim is that a published constraint and an enforced
constraint are the same object. These controls test that claim from both
directions: valid artifacts pass, and each specific way an artifact can be
wrong is refused by name.

The drift controls matter most. ``parser_v3_v2_schemas`` deliberately mirrors
several vocabularies (agreement fields, quarantine reasons, preregistered
bindings, roles, strata) rather than importing them, so that it stays
standalone-loadable. A mirror that silently follows its original is useless;
these controls make the mirror fail loudly the moment the original moves.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jspace_observation import parser_v3_v2_construction as construction  # noqa: E402
from jspace_observation import parser_v3_v2_evaluation as evaluation  # noqa: E402
from jspace_observation import parser_v3_v2_lifecycle as lifecycle  # noqa: E402
from jspace_observation import parser_v3_v2_schemas as schemas  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures: minimal valid instances
# ---------------------------------------------------------------------------

_D = "a" * 64
_D2 = "b" * 64


def _reviewer_decision(reviewer: str = "reviewer_a", **overrides: object) -> dict:
    decision = {
        "schema_version": "phase1-parser-v3-v2-reviewer-decision/v1",
        "reviewer_id": reviewer,
        "case_ref": "case-ref-0001",
        "typed_decision": "present",
        "canonical_value": "42",
        "canonical_candidates": ["42"],
        "literal_spans": [{"literal": True, "start": 0, "end": 2, "text": "42"}],
        "span_roles": ["answer"],
        "ambiguity": False,
        "equivalence": "exact",
        "extraction_strategy": "rightmost",
        "output_quality": "clean",
        "warnings": [],
        "failure_reasons": [],
        "stratum": "S01",
        "subtype": "numeric_plain",
        "decision_digest": _D,
    }
    decision.update(overrides)
    return decision


def _blinded_packet(**overrides: object) -> dict:
    packet = {
        "schema_version": "phase1-parser-v3-v2-blinded-case-packet/v1",
        "packet_id": "packet-0001",
        "case_ref": "case-ref-0001",
        "case_content": "What is the total?",
        "public_ontology_packet": {
            "ontology_version": "v2",
            "stratum_definitions_digest": _D,
            "subtype_slots": ["numeric_plain"],
        },
    }
    packet.update(overrides)
    return packet


def _admission(**overrides: object) -> dict:
    record = {
        "schema_version": "phase1-parser-v3-v2-admission-record/v1",
        "case_id": "c-0001",
        "stratum": "S01",
        "decision_class": "present",
        "eligible": True,
        "adjudicable": True,
        "mandatory": True,
        "unresolved": False,
        "subtype_slot": "numeric_plain",
        "literal_spans": [{"literal": True, "start": 0, "end": 2, "text": "42"}],
        "content_digest": _D,
    }
    record.update(overrides)
    return record


# ---------------------------------------------------------------------------
# registry structure
# ---------------------------------------------------------------------------


def test_every_registered_schema_declares_its_identity():
    for schema_id, document in schemas.SCHEMAS.items():
        assert document["$id"] == schema_id
        assert document["$schema"].startswith("https://json-schema.org/draft/")
        assert document["title"]
        assert document["description"]


def test_every_object_boundary_in_the_registry_is_closed():
    """No object anywhere in the registry may accept an undeclared field."""

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                assert "additionalProperties" in node, path
                additional = node["additionalProperties"]
                assert additional is False or "propertyNames" in node, path
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    for schema_id, document in schemas.SCHEMAS.items():
        walk(document, schema_id)


def test_registry_digest_covers_every_schema():
    assert len(schemas.SCHEMA_DIGESTS) == len(schemas.SCHEMAS)
    for digest in schemas.SCHEMA_DIGESTS.values():
        assert len(digest) == 64 and set(digest) <= set("0123456789abcdef")
    assert len(schemas.REGISTRY_DIGEST) == 64


def test_registry_ids_match_the_lifecycle_binding():
    """The lifecycle's hand-written id list is the binding; prove it is exact."""
    assert schemas.SCHEMA_IDS == tuple(sorted(lifecycle.BOUND_SCHEMA_IDS))


def test_every_schema_required_by_section_5_1_is_present():
    for name in (
        "blinded-case-packet",
        "reviewer-decision",
        "disagreement-packet",
        "arbitration-result",
        "admission-record",
        "quarantine-record",
        "replacement-record",
        "construction-plan",
        "set-facts-projection",
        "planned-seal-members",
        "terminal-manifest",
        "authenticated-listing-projection",
        "listing-witness-receipt",
        "final-contract-receipt",
        "preregistration-lock",
        "prediction-member",
        "prediction-manifest",
        "prediction-receipt",
        "stage-e-result",
        "terminal-state-receipt",
        "deployment-evidence",
        "runtime-canary-result",
        "access-event",
        "public-receipt",
    ):
        assert f"phase1-parser-v3-v2-{name}/v1" in schemas.SCHEMAS, name


# ---------------------------------------------------------------------------
# the fail-closed vocabulary --- the load-bearing property
# ---------------------------------------------------------------------------


def test_a_schema_keyword_the_validator_cannot_enforce_is_refused():
    """An unenforceable constraint must never reach the registry.

    This is the control that makes the whole design honest. Without it, an
    author could write ``"multipleOf": 3`` and ship a document promising a
    constraint that nothing checks.
    """
    with pytest.raises(schemas.SchemaError, match="not implemented"):
        schemas._assert_closed({"type": "integer", "multipleOf": 3}, "$")


def test_an_object_without_additional_properties_is_refused():
    with pytest.raises(schemas.SchemaError, match="additionalProperties"):
        schemas._assert_closed({"type": "object", "properties": {}}, "$")


def test_an_object_that_requires_an_undeclared_property_is_refused():
    with pytest.raises(schemas.SchemaError, match="never be satisfied"):
        schemas._assert_closed(
            {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "required": ["a", "b"],
                "additionalProperties": False,
            },
            "$",
        )


def test_an_array_without_items_is_refused():
    with pytest.raises(schemas.SchemaError, match="must declare items"):
        schemas._assert_closed({"type": "array", "minItems": 1}, "$")


def test_an_empty_enum_is_refused():
    with pytest.raises(schemas.SchemaError, match="non-empty"):
        schemas._assert_closed({"type": "string", "enum": []}, "$")


def test_an_open_extension_object_must_constrain_its_key_space():
    with pytest.raises(schemas.SchemaError, match="propertyNames"):
        schemas._assert_closed(
            {
                "type": "object",
                "properties": {},
                "additionalProperties": {"type": "string"},
            },
            "$",
        )


def test_emptying_the_supported_keyword_table_changes_live_behaviour(monkeypatch):
    """Mutation control: the vocabulary is consulted, not merely declared."""
    schemas._assert_closed({"type": "string"}, "$")
    monkeypatch.setattr(schemas, "SUPPORTED_KEYWORDS", frozenset())
    with pytest.raises(schemas.SchemaError, match="not implemented"):
        schemas._assert_closed({"type": "string"}, "$")


# ---------------------------------------------------------------------------
# drift controls: the mirrors must track their originals
# ---------------------------------------------------------------------------


def test_agreement_fields_mirror_the_construction_module():
    assert schemas._AGREEMENT_FIELDS == construction.AGREEMENT_FIELDS


def test_quarantine_reasons_mirror_the_construction_module():
    assert set(schemas._QUARANTINE_REASONS) == set(construction.QUARANTINE_REASONS)


def test_strata_and_decision_classes_mirror_the_construction_module():
    assert schemas._STRATA == construction.STRATA
    assert schemas._DECISION_CLASSES == construction.DECISION_CLASSES


def test_preregistered_bindings_mirror_the_evaluation_module():
    assert schemas._PREREGISTERED_BINDINGS == evaluation.PREREGISTERED_BINDINGS


def test_evaluation_vocabularies_mirror_the_evaluation_module():
    assert schemas._RESIDUAL_STRATA == evaluation.ZERO_ERROR_RESIDUAL_STRATA
    assert schemas._PINNED_GATES == evaluation.PINNED_ZERO_ERROR_GATES
    assert schemas._PRESENCE_CLASSES == evaluation.ANSWER_PRESENCE_CLASSES


def test_roles_mirror_the_lane_table():
    assert schemas._ROLES == tuple(sorted(lifecycle.ROLE_LANES))


def test_binding_gate_names_match_what_stage_e_can_emit():
    """The gate list is enumerated, so prove the enumeration is the real one."""
    expected = {"residual_pooled_zero_error"}
    expected |= {f"residual_{s}_zero_error" for s in evaluation.ZERO_ERROR_RESIDUAL_STRATA}
    expected |= set(evaluation.PINNED_ZERO_ERROR_GATES)
    assert set(schemas._BINDING_GATES) == expected


# ---------------------------------------------------------------------------
# instance validation: positive and negative
# ---------------------------------------------------------------------------


def test_a_well_formed_reviewer_decision_validates():
    schemas.assert_valid("phase1-parser-v3-v2-reviewer-decision/v1", _reviewer_decision())


def test_a_reviewer_decision_missing_an_agreement_field_is_refused():
    decision = _reviewer_decision()
    del decision["literal_spans"]
    errors = schemas.validate("phase1-parser-v3-v2-reviewer-decision/v1", decision)
    assert any("literal_spans" in error for error in errors)


def test_an_unknown_field_is_refused_everywhere():
    decision = _reviewer_decision(surprise="extra")
    with pytest.raises(schemas.SchemaValidationError, match="closed"):
        schemas.assert_valid("phase1-parser-v3-v2-reviewer-decision/v1", decision)


def test_a_wrong_schema_version_is_refused():
    decision = _reviewer_decision(schema_version="phase1-parser-v3-v2-reviewer-decision/v2")
    with pytest.raises(schemas.SchemaValidationError):
        schemas.assert_valid("phase1-parser-v3-v2-reviewer-decision/v1", decision)


def test_a_blinded_packet_carrying_the_old_label_is_unrepresentable():
    """Closure, not a denylist, is what keeps the label out."""
    packet = _blinded_packet(old_label="42")
    with pytest.raises(schemas.SchemaValidationError, match="closed"):
        schemas.assert_valid("phase1-parser-v3-v2-blinded-case-packet/v1", packet)


@pytest.mark.parametrize(
    "forbidden",
    sorted(construction.REVIEWER_FORBIDDEN_INPUTS),
)
def test_no_reviewer_forbidden_input_can_appear_in_a_blinded_packet(forbidden):
    packet = _blinded_packet(**{forbidden: "anything"})
    with pytest.raises(schemas.SchemaValidationError):
        schemas.assert_valid("phase1-parser-v3-v2-blinded-case-packet/v1", packet)


def test_a_valid_admission_record_validates():
    schemas.assert_valid("phase1-parser-v3-v2-admission-record/v1", _admission())


@pytest.mark.parametrize("flag", ["eligible", "adjudicable", "mandatory"])
def test_an_admission_record_that_is_not_fully_admissible_is_refused(flag):
    with pytest.raises(schemas.SchemaValidationError):
        schemas.assert_valid("phase1-parser-v3-v2-admission-record/v1", _admission(**{flag: False}))


def test_an_admission_record_with_an_unresolved_decision_is_refused():
    with pytest.raises(schemas.SchemaValidationError):
        schemas.assert_valid("phase1-parser-v3-v2-admission-record/v1", _admission(unresolved=True))


def test_an_admission_record_with_a_non_literal_span_is_refused():
    record = _admission(literal_spans=[{"literal": False, "start": 0, "end": 2, "text": "42"}])
    with pytest.raises(schemas.SchemaValidationError):
        schemas.assert_valid("phase1-parser-v3-v2-admission-record/v1", record)


def test_an_unregistered_quarantine_reason_is_refused():
    record = {
        "schema_version": "phase1-parser-v3-v2-quarantine-record/v1",
        "case_id": "c-0001",
        "reason": "other",
        "recorded_at_batch": 0,
        "quarantine_digest": _D,
    }
    with pytest.raises(schemas.SchemaValidationError):
        schemas.assert_valid("phase1-parser-v3-v2-quarantine-record/v1", record)


def test_every_registered_quarantine_reason_is_accepted():
    for reason in sorted(construction.QUARANTINE_REASONS):
        record = {
            "schema_version": "phase1-parser-v3-v2-quarantine-record/v1",
            "case_id": "c-0001",
            "reason": reason,
            "recorded_at_batch": 0,
            "quarantine_digest": _D,
        }
        schemas.assert_valid("phase1-parser-v3-v2-quarantine-record/v1", record)


def test_a_disagreement_packet_validates_through_its_references():
    packet = {
        "schema_version": "phase1-parser-v3-v2-disagreement-packet/v1",
        "case_ref": "case-ref-0001",
        "case_content": "What is the total?",
        "reviewer_a": _reviewer_decision("reviewer_a"),
        "reviewer_b": _reviewer_decision("reviewer_b", canonical_value="43"),
        "disagreeing_fields": ["canonical_value"],
    }
    schemas.assert_valid("phase1-parser-v3-v2-disagreement-packet/v1", packet)


def test_a_referenced_document_is_validated_not_merely_named():
    """A $ref that were not followed would accept any nested object at all."""
    packet = {
        "schema_version": "phase1-parser-v3-v2-disagreement-packet/v1",
        "case_ref": "case-ref-0001",
        "case_content": "What is the total?",
        "reviewer_a": {"nonsense": True},
        "reviewer_b": _reviewer_decision("reviewer_b"),
        "disagreeing_fields": ["canonical_value"],
    }
    errors = schemas.validate("phase1-parser-v3-v2-disagreement-packet/v1", packet)
    assert any("reviewer_a" in error for error in errors)


def test_a_partial_prediction_seal_is_refused_by_the_receipt_schema():
    receipt = {
        "state": "PREDICTION_SEALED",
        "ordinal": 0,
        "lock_digest": _D,
        "member_count": 119,
        "listing_witness_digest": _D,
        "stream_digest": _D2,
        "write_order": ["a", "b"],
        "receipt_digest": _D,
    }
    with pytest.raises(schemas.SchemaValidationError):
        schemas.assert_valid("phase1-parser-v3-v2-prediction-receipt/v1", receipt)


def test_a_preregistration_lock_missing_a_binding_is_refused():
    lock = {"schema_version": "phase1-parser-v3-v2-preregistration/v1"}
    errors = schemas.validate("phase1-parser-v3-v2-preregistration-lock/v1", lock)
    assert len(errors) >= len(evaluation.PREREGISTERED_BINDINGS)


def test_an_access_event_cannot_carry_a_free_text_message():
    event = {
        "schema_version": "phase1-parser-v3-v2-access-event/v1",
        "event_id": "lane_check_passed",
        "role": "stage_p",
        "status": "ok",
        "occurred_at_step": 0,
        "message": "raw prompt text",
    }
    with pytest.raises(schemas.SchemaValidationError, match="closed"):
        schemas.assert_valid("phase1-parser-v3-v2-access-event/v1", event)


def test_an_unregistered_event_id_is_refused():
    event = {
        "schema_version": "phase1-parser-v3-v2-access-event/v1",
        "event_id": "something_happened",
        "role": "stage_p",
        "status": "ok",
        "occurred_at_step": 0,
    }
    with pytest.raises(schemas.SchemaValidationError):
        schemas.assert_valid("phase1-parser-v3-v2-access-event/v1", event)


def test_all_errors_are_reported_not_only_the_first():
    decision = _reviewer_decision(stratum="S99", typed_decision="maybe", first_extra=1)
    errors = schemas.validate("phase1-parser-v3-v2-reviewer-decision/v1", decision)
    assert len(errors) >= 3


def test_unique_items_is_enforced():
    projection = {
        "schema_version": "phase1-parser-v3-v2-authenticated-listing-projection/v1",
        "prefix": "sealed/",
        "entries": [
            {"object_name": "a", "content_digest": _D},
            {"object_name": "a", "content_digest": _D},
        ],
        "listing_digest": _D,
    }
    with pytest.raises(schemas.SchemaValidationError, match="unique"):
        schemas.assert_valid("phase1-parser-v3-v2-authenticated-listing-projection/v1", projection)


# ---------------------------------------------------------------------------
# registry mutation controls
# ---------------------------------------------------------------------------


def test_an_unregistered_schema_id_is_refused():
    with pytest.raises(schemas.SchemaError, match="unregistered"):
        schemas.get_schema("phase1-parser-v3-v2-not-a-schema/v1")


def test_changing_a_schema_document_changes_its_digest(monkeypatch):
    before = schemas.schema_digest("phase1-parser-v3-v2-access-event/v1")
    tampered = dict(schemas.SCHEMAS)
    edited = dict(tampered["phase1-parser-v3-v2-access-event/v1"])
    edited["title"] = "Access event (edited)"
    tampered["phase1-parser-v3-v2-access-event/v1"] = edited
    monkeypatch.setattr(schemas, "SCHEMAS", tampered)
    assert schemas.schema_digest("phase1-parser-v3-v2-access-event/v1") != before


def test_registry_drift_against_a_bound_table_is_refused():
    tampered = dict(schemas.SCHEMA_DIGESTS)
    tampered["phase1-parser-v3-v2-access-event/v1"] = _D
    with pytest.raises(schemas.SchemaError, match="changed after binding"):
        schemas.assert_registry_matches(tampered)


def test_a_missing_bound_schema_is_refused():
    tampered = dict(schemas.SCHEMA_DIGESTS)
    tampered.pop("phase1-parser-v3-v2-access-event/v1")
    with pytest.raises(schemas.SchemaError, match="unbound"):
        schemas.assert_registry_matches(tampered)


def test_naming_an_unregistered_schema_is_refused():
    with pytest.raises(schemas.SchemaError, match="unregistered"):
        schemas.assert_all_ids_reachable(["phase1-parser-v3-v2-invented/v1"])


def test_exported_documents_round_trip_to_the_registry():
    import json

    exported = schemas.export_schema_documents()
    assert len(exported) == len(schemas.SCHEMAS)
    for text in exported.values():
        document = json.loads(text)
        assert document["$id"] in schemas.SCHEMAS
        assert document == schemas.SCHEMAS[document["$id"]]


# ---------------------------------------------------------------------------
# lifecycle lane and binding controls
# ---------------------------------------------------------------------------


def test_the_section_7_4_lane_matrix_is_unchanged_by_the_additive_roles():
    expected = {
        "source_custodian": {"reads": ("retired_v1_source",), "writes": ("v2_private_staging",)},
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
    }
    assert set(lifecycle.SECTION_7_4_ROLES) == set(expected)
    for role, lanes in expected.items():
        assert lifecycle.ROLE_LANES[role] == lanes, role


def test_only_stage_e_may_read_scoring_labels():
    readers = [
        role for role, lanes in lifecycle.ROLE_LANES.items() if "scoring_labels" in lanes["reads"]
    ]
    assert readers == [lifecycle.LABEL_READING_ROLE]


def test_no_construction_role_may_read_frozen_parser_assets():
    readers = {
        role
        for role, lanes in lifecycle.ROLE_LANES.items()
        if "frozen_parser_assets" in lanes["reads"]
    }
    assert readers == {"stage_p"}


def test_every_added_role_declares_both_lanes():
    for role in ("normalizer", "selector", "facts_compiler", "preregistration_compiler"):
        lanes = lifecycle.ROLE_LANES[role]
        assert lanes["reads"] and lanes["writes"], role


def test_an_unregistered_role_still_has_no_lane():
    with pytest.raises(lifecycle.LifecycleError, match="not a registered role"):
        lifecycle._assert_scope("ghost_role", [], frozenset())


def test_an_unfilled_schema_binding_refuses_rather_than_passing_vacuously(monkeypatch):
    """An empty expected table must never validate anything."""
    monkeypatch.setattr(lifecycle, "BOUND_SCHEMA_DIGESTS", {})
    with pytest.raises(lifecycle.LifecycleError, match="binding is empty"):
        lifecycle.assert_schema_binding(
            registry_digests=schemas.SCHEMA_DIGESTS,
            registry_digest=schemas.REGISTRY_DIGEST,
        )


def test_the_bound_schema_binding_matches_the_live_registry():
    lifecycle.assert_schema_binding(
        registry_digests=schemas.SCHEMA_DIGESTS,
        registry_digest=schemas.REGISTRY_DIGEST,
    )


def test_a_tampered_registry_digest_is_refused():
    with pytest.raises(lifecycle.LifecycleError, match="registry digest"):
        lifecycle.assert_schema_binding(
            registry_digests=schemas.SCHEMA_DIGESTS,
            registry_digest=_D,
        )


def test_an_extra_schema_in_the_registry_is_refused():
    extended = dict(schemas.SCHEMA_DIGESTS)
    extended["phase1-parser-v3-v2-smuggled/v1"] = _D
    with pytest.raises(lifecycle.LifecycleError, match="unbound"):
        lifecycle.assert_schema_binding(
            registry_digests=extended,
            registry_digest=schemas.REGISTRY_DIGEST,
        )
