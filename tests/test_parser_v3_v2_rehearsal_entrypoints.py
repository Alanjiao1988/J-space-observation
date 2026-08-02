"""Public synthetic rehearsal driven through the registered entrypoints.

Section 5.4 does not ask for another rehearsal. It asks for the rehearsal to be
re-run *through the closed schemas, the exact container entrypoints, the role
configuration and the lifecycle* -- because the Phase A rehearsal called the
lifecycle and evaluation functions directly, and a rehearsal that calls a
function the deployment does not call proves something about the function
rather than about the deployment.

So every stage below is reached the way a container reaches it: the registered
command tuple is resolved through ``resolve_entrypoint`` and the resolved
callable is invoked with a full ``RoleConfig``. Nothing here calls
``parser_v3_v2_evaluation`` or ``parser_v3_v2_construction`` to *perform* a
protocol step. Those modules are imported only to read closed vocabularies and
to name the exception types a refusal is expected to raise.

This is also the first time real payloads pass through the schema registry:
until now the entrypoint tests substituted the evaluation calls, so the
registered documents had never been validated against what the implementation
actually emits. Any mismatch found here is a defect in the material being
frozen, not in the rehearsal.

The material is synthetic and public: 120 generated cases, a parser that
answers them from the case identifier alone, and in-memory storage. No
invariant is stubbed or relaxed. The nine paths section 5.4 enumerates --
PASS, FAIL, INVALID, partial upload, partial prediction, wrong role, wrong
entrypoint, ineligible sealed case, second launch -- each have a class below,
and each asserts the accepted case alongside the refusal, because a refusal
test that would also pass against a pipeline that refuses everything
establishes nothing.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from jspace_observation import parser_v3_v2_entrypoints as entrypoints  # noqa: E402

construction = entrypoints.construction
evaluation = entrypoints.evaluation
lifecycle = entrypoints.lifecycle
schemas = entrypoints.schemas

EntrypointError = entrypoints.EntrypointError
ConstructionError = construction.ConstructionError
EvaluationError = evaluation.EvaluationError
LifecycleError = lifecycle.LifecycleError
SchemaValidationError = schemas.SchemaValidationError

CLIENT_ID = "11111111-2222-3333-4444-555555555555"
IMAGE_DIGEST = "sha256:" + "ab" * 32
CONFIG_DIGEST = "cd" * 32
ZERO_DIGEST = "0" * 64
ENDPOINT = "stjspacefiles0709085305.privatelink.blob.core.windows.net"

#: A parser-free, scorer-free module list.
#:
#: The guarded prologue inspects the names it is given rather than the live
#: interpreter, so the rehearsal can state exactly what a container would be
#: holding instead of inheriting whatever pytest happens to have imported.
CLEAN_MODULES = ("json", "hashlib", "unicodedata", "typing")

TOTAL = construction.TOTAL_CASES


# ---------------------------------------------------------------------------
# synthetic public material
# ---------------------------------------------------------------------------

_SUBJECTS = ("depot", "harbour", "registry", "warehouse", "terminal")
_OBJECTS = ("consignment", "parcel", "charter", "sailing")
_QUALIFIERS = ("earliest", "shortest", "cheapest", "safest", "latest", "nearest")

REPLACEMENT_CASE_ID = "synthetic-120"
REPLACEMENT_PROMPT = "a substitute manifest lodged with the notary"


def _prompt(index: int) -> str:
    """A digit-free phrasing unique to this case.

    One template plus a case identifier is exactly what the template-family
    collision rule exists to reject, so every case gets its own literal frame:
    five subjects times four objects times six qualifiers is 120 of them.
    """
    qualifier = _QUALIFIERS[index % len(_QUALIFIERS)]
    obj = _OBJECTS[(index // len(_QUALIFIERS)) % len(_OBJECTS)]
    subject = _SUBJECTS[index // (len(_QUALIFIERS) * len(_OBJECTS))]
    return f"the {qualifier} {obj} recorded at the {subject}"


def _case_id(index: int) -> str:
    return f"synthetic-{index:03d}"


def _stratum(index: int) -> str:
    return construction.STRATA[index // construction.STRATUM_QUOTA]


def _decision_class(index: int) -> str:
    if index < construction.DECISION_CLASS_QUOTA["present"]:
        return "present"
    if index < 110:
        return "no_answer"
    return "ambiguous"


def _canonical_value(index: int) -> str | None:
    return f"value-{index:03d}" if _decision_class(index) == "present" else None


def _span(text: str) -> dict[str, Any]:
    return {"literal": True, "start": 0, "end": len(text), "text": text}


def _admission_record(
    index: int, *, case_id: str | None = None, prompt: str | None = None
) -> dict[str, Any]:
    text = prompt if prompt is not None else _prompt(index)
    record: dict[str, Any] = {
        "schema_version": "phase1-parser-v3-v2-admission-record/v1",
        "case_id": case_id if case_id is not None else _case_id(index),
        "stratum": _stratum(index),
        "decision_class": _decision_class(index),
        "eligible": True,
        "adjudicable": True,
        "mandatory": True,
        "unresolved": False,
        "subtype_slot": f"slot-{index % 5}",
        "literal_spans": [_span(text)],
        "content_digest": construction.content_hash(text),
    }
    if record["stratum"] == "S06":
        record["rightmost_distractor_registration"] = True
    if record["stratum"] == "S11":
        record["ambiguity_registration"] = True
    return record


def _admitted() -> list[dict[str, Any]]:
    return [_admission_record(index) for index in range(TOTAL)]


def _ontology() -> dict[str, Any]:
    return {
        "ontology_version": "v2-public-ontology/2026-08",
        "stratum_definitions_digest": ZERO_DIGEST,
        "subtype_slots": [f"slot-{n}" for n in range(5)],
    }


def _packet(index: int) -> dict[str, Any]:
    return {
        "schema_version": "phase1-parser-v3-v2-blinded-case-packet/v1",
        "packet_id": f"packet-{index:03d}",
        "case_ref": _case_id(index),
        "case_content": _prompt(index),
        "public_ontology_packet": _ontology(),
    }


def _decision(index: int, reviewer: str, **overrides: Any) -> dict[str, Any]:
    text = _prompt(index)
    decision: dict[str, Any] = {
        "schema_version": "phase1-parser-v3-v2-reviewer-decision/v1",
        "reviewer_id": reviewer,
        "case_ref": _case_id(index),
        "typed_decision": _decision_class(index),
        "canonical_value": _canonical_value(index),
        "canonical_candidates": [],
        "literal_spans": [_span(text)],
        "span_roles": ["subject"],
        "ambiguity": _decision_class(index) == "ambiguous",
        "equivalence": "exact",
        "extraction_strategy": "literal-span",
        "output_quality": "clean",
        "warnings": [],
        "failure_reasons": [],
        "stratum": _stratum(index),
        "subtype": f"slot-{index % 5}",
        "decision_digest": construction.content_hash(f"{reviewer}:{text}"),
    }
    decision.update(overrides)
    return decision


def _pair(index: int, **b_overrides: Any) -> dict[str, Any]:
    return {
        "case_ref": _case_id(index),
        "case_content": _prompt(index),
        "public_ontology_packet": _ontology(),
        "reviewer_a": _decision(index, "reviewer_a"),
        "reviewer_b": _decision(index, "reviewer_b", **b_overrides),
    }


def _adjudicate(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase1-parser-v3-v2-arbitration-result/v1",
        "case_ref": packet["case_ref"],
        "arbiter_id": "arbiter-001",
        "adjudication_permanently_recorded": True,
        "outcome": "adjudicated",
        "resolved_fields": {
            "typed_decision": packet["reviewer_a"]["typed_decision"],
            "canonical_value": packet["reviewer_a"]["canonical_value"],
        },
        "arbitration_digest": construction.content_hash(f"arbitration:{packet['case_ref']}"),
    }


def _construction_plan() -> dict[str, Any]:
    members = [f"sealed/v2/cases/{_case_id(index)}.json" for index in range(TOTAL)]
    manifest = "sealed/v2/manifests/set_manifest.json"
    return {
        "schema_version": "phase1-parser-v3-v2-construction-plan/v1",
        "plan_id": "v2-set-seal-001",
        "total_cases": TOTAL,
        "stratum_quota": construction.STRATUM_QUOTA,
        "decision_class_quota": dict(construction.DECISION_CLASS_QUOTA),
        "planned_objects": members + [manifest],
        "write_order": members + [manifest],
        "terminal_manifest": manifest,
    }


def _set_facts(*, quarantined: int = 0, replacements: int = 0) -> dict[str, Any]:
    return {
        "schema_version": "phase1-parser-v3-v2-set-facts-projection/v1",
        "set_id": "v2-set-001",
        "member_count": TOTAL,
        "per_stratum_count": {
            stratum: construction.STRATUM_QUOTA for stratum in construction.STRATA
        },
        "per_decision_class_count": dict(construction.DECISION_CLASS_QUOTA),
        "gate_pinned_count": 80,
        "residual_count": 40,
        "quarantined_count": quarantined,
        "replacement_count": replacements,
        "facts_digest": ZERO_DIGEST,
    }


def _bindings(**overrides: Any) -> dict[str, Any]:
    """The preregistration bindings, bound to the registered entrypoints.

    The stage commands and identities are read out of the entrypoint registry
    rather than written here. That is the point of section 5.4: the command the
    lock preregisters has to be the command the container runs, and the only
    way to guarantee that is to take both from the same table.
    """
    bindings: dict[str, Any] = {name: ZERO_DIGEST for name in evaluation.PREREGISTERED_BINDINGS}
    bindings.update(
        {
            "base_image_digest": IMAGE_DIGEST,
            "evaluation_image_digest": IMAGE_DIGEST,
            "cuda_runtime": "cuda-12.4",
            "stage_p_entrypoint": entrypoints.ENTRYPOINTS["stage_p"].name,
            "stage_p_command": list(entrypoints.ENTRYPOINTS["stage_p"].command),
            "stage_p_identity": entrypoints.ROLE_IDENTITY_NAMES["stage_p"],
            "stage_p_read_classes": ["sealed_v2_inputs", "frozen_parser_assets"],
            "stage_e_entrypoint": entrypoints.ENTRYPOINTS["stage_e"].name,
            "stage_e_command": list(entrypoints.ENTRYPOINTS["stage_e"].command),
            "stage_e_identity": entrypoints.ROLE_IDENTITY_NAMES["stage_e"],
            "stage_e_read_classes": [
                "sealed_predictions",
                "scoring_labels",
                "policy",
                "final_contract",
            ],
            "prediction_member_layout": "one object per case plus a terminal manifest",
            "prediction_completeness_rule": "exact sealed case identifiers, no more, no fewer",
            "prediction_seal_mode": "create_only",
            "prediction_listing_schema": "phase1-prediction-listing/v1",
            "prediction_receipt_schema": "phase1-parser-v3-v2-prediction-receipt/v1",
            "evaluation_ordinal": 0,
            "retry_rule": "infrastructure-only, never after a prediction-bearing write",
            "binding_acceptance_criteria": list(evaluation.PINNED_ZERO_ERROR_GATES),
            "nonbinding_diagnostics": list(evaluation.NONBINDING_DIAGNOSTICS),
            "formal_result_schema": "phase1-parser-v3-v2-formal-result/v1",
            "public_redaction_projection": "aggregate counts only, no case-level errors",
        }
    )
    bindings.update(overrides)
    return bindings


def _locked_inputs() -> list[dict[str, Any]]:
    return [
        {
            "case_id": _case_id(index),
            "stratum": _stratum(index),
            "prompt": _prompt(index),
            "context": "synthetic public context, held free of any scoring signal",
        }
        for index in range(TOTAL)
    ]


def _labels() -> dict[str, dict[str, Any]]:
    return {
        _case_id(index): {
            "case_id": _case_id(index),
            "eligible": True,
            "answer_presence": _decision_class(index),
            "canonical_value": _canonical_value(index),
        }
        for index in range(TOTAL)
    }


def _strata() -> dict[str, str]:
    return {_case_id(index): _stratum(index) for index in range(TOTAL)}


def _perfect_parser(case: dict[str, Any]) -> dict[str, Any]:
    index = int(case["case_id"].rsplit("-", 1)[1])
    return {
        "answer_presence": _decision_class(index),
        "canonical_value": _canonical_value(index),
    }


def _prediction_write_order(case_ids: list[str]) -> tuple[list[str], str]:
    manifest = "predictions/manifest.json"
    return [f"predictions/{case_id}.json" for case_id in case_ids] + [manifest], manifest


def _public_receipt() -> dict[str, Any]:
    return {
        "schema_version": "phase1-parser-v3-v2-public-receipt/v1",
        "receipt_id": "rehearsal-receipt-001",
        "bound_commit": "0" * 40,
        "counts": {
            "private_semantic_reads": 0,
            "sealed_sets": 0,
            "preregistrations": 0,
            "stage_p_runs": 0,
            "stage_e_runs": 0,
        },
        "digests": {
            "policy_full_file_digest": ZERO_DIGEST,
            "policy_semantic_digest": ZERO_DIGEST,
            "dependency_lock_digest": ZERO_DIGEST,
            "schema_registry_digest": lifecycle.BOUND_SCHEMA_REGISTRY_DIGEST,
        },
        "receipt_digest": ZERO_DIGEST,
    }


# ---------------------------------------------------------------------------
# reaching the roles the way a container reaches them
# ---------------------------------------------------------------------------


def _config(role: str, **overrides: Any) -> entrypoints.RoleConfig:
    fields: dict[str, Any] = {
        "role": role,
        "uami_name": entrypoints.ROLE_IDENTITY_NAMES[role],
        "uami_client_id": CLIENT_ID,
        "private_endpoint": ENDPOINT,
        "container": entrypoints.REGISTERED_CONTAINERS[role],
        "prefix": entrypoints.REGISTERED_PREFIXES[role],
        "schema_ids": entrypoints.ROLE_SCHEMAS[role],
        "image_digest": IMAGE_DIGEST,
        "config_digest": CONFIG_DIGEST,
    }
    fields.update(overrides)
    return entrypoints.RoleConfig(**fields)


def _env() -> dict[str, str]:
    return {"AZURE_CLIENT_ID": CLIENT_ID, "PYTHONHASHSEED": "0"}


def launch(name: str, *, config: entrypoints.RoleConfig | None = None, **payload: Any) -> Any:
    """Reach an entrypoint through its registered command, as a container does.

    The command tuple is resolved rather than the function being imported by
    name, and the resolution is cross-checked against the role. If the registry
    and the deployment ever disagree, this raises instead of quietly rehearsing
    something the platform would never run.
    """
    spec = entrypoints.ENTRYPOINTS[name]
    resolved = entrypoints.resolve_entrypoint(spec.command)
    entrypoints.assert_container_command_is_registered(role=spec.role, command=spec.command)
    assert resolved is spec, "the registered command resolved to a different entrypoint"
    return resolved.function(
        config=config if config is not None else _config(spec.role),
        environment=_env(),
        loaded_module_names=CLEAN_MODULES,
        **payload,
    )


# ---------------------------------------------------------------------------
# the rehearsal itself
# ---------------------------------------------------------------------------


def rehearse(
    *,
    parser: Any = _perfect_parser,
    labels: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Drive all fifteen roles once and return every intermediate artifact."""
    admitted = _admitted()
    case_ids = [record["case_id"] for record in admitted]
    labels = labels if labels is not None else _labels()

    custodian = launch("source_custodian", admission_records=admitted)
    normalizer = launch("normalizer", admission_records=admitted)

    packets = [_packet(index) for index in range(TOTAL)]
    reviewer_a = launch(
        "reviewer_a",
        packets=packets,
        decide=lambda packet: _decision(
            int(packet["case_ref"].rsplit("-", 1)[1]), "reviewer_a"
        ),
    )
    reviewer_b = launch(
        "reviewer_b",
        packets=packets,
        decide=lambda packet: _decision(
            int(packet["case_ref"].rsplit("-", 1)[1]), "reviewer_b"
        ),
    )

    pairs = [_pair(index) for index in range(TOTAL)]
    broker = launch("broker", pairs=pairs)
    arbiter = launch("arbiter", packets=broker["routed"], adjudicate=_adjudicate)

    selector = launch("selector", admitted=admitted)
    auditor = launch("private_set_auditor", admitted=admitted)
    facts = launch("facts_compiler", admitted=admitted, facts=_set_facts())

    plan = _construction_plan()
    seal = launch("seal_custodian", plan=plan)

    preregistration = launch("preregistration_compiler", bindings=_bindings())
    lock = preregistration["lock"]
    lock_digest = preregistration["lock_digest"]

    stage_p = launch(
        "stage_p",
        lock=lock,
        lock_digest=lock_digest,
        state="PREREGISTERED",
        ordinal=0,
        locked_inputs=_locked_inputs(),
        parser=parser,
    )
    stream = stage_p["stream"]

    order, manifest = _prediction_write_order(case_ids)
    sealer = launch(
        "prediction_sealer",
        stream=stream,
        sealed_case_ids=case_ids,
        write_order=order,
        terminal_manifest=manifest,
    )
    receipt = sealer["receipt"]

    stage_e = launch(
        "stage_e",
        lock=lock,
        lock_digest=lock_digest,
        prediction_receipt=receipt,
        sealed_members=stream["members"],
        labels=labels,
        strata=_strata(),
    )
    exporter = launch("receipt_exporter", receipt=_public_receipt())

    returns = {
        "custodian": custodian,
        "normalizer": normalizer,
        "reviewer_a": reviewer_a,
        "reviewer_b": reviewer_b,
        "broker": broker,
        "arbiter": arbiter,
        "selector": selector,
        "auditor": auditor,
        "facts": facts,
        "seal": seal,
        "preregistration": preregistration,
        "stage_p": stage_p,
        "sealer": sealer,
        "stage_e": stage_e,
        "exporter": exporter,
    }
    return {
        **returns,
        "returns": returns,
        "admitted": admitted,
        "case_ids": case_ids,
        "plan": plan,
        "lock": lock,
        "lock_digest": lock_digest,
        "stream": stream,
        "receipt": receipt,
        "result": stage_e["result"],
        "write_order": order,
        "terminal_manifest": manifest,
    }


@pytest.fixture(scope="module")
def run() -> dict[str, Any]:
    return rehearse()


# ---------------------------------------------------------------------------
# the rehearsal runs through the deployed path
# ---------------------------------------------------------------------------


class TestTheRehearsalUsesTheRegisteredCommands:
    def test_every_registered_role_is_exercised_exactly_once(self, run) -> None:
        exercised = [returned["role"] for returned in run["returns"].values()]
        assert sorted(exercised) == sorted(entrypoints.ROLE_IDENTITY_NAMES)

    def test_each_stage_was_reached_through_its_command_tuple(self) -> None:
        for name, spec in entrypoints.ENTRYPOINTS.items():
            assert entrypoints.resolve_entrypoint(spec.command) is spec
            assert spec.command[1] == entrypoints.CONTAINER_ENTRYPOINT_PATH
            assert spec.command[2] == name

    def test_every_role_logged_its_guard_before_its_work(self, run) -> None:
        for returned in run["returns"].values():
            ids = returned["log"].event_ids()
            assert ids[:3] == (
                "identity_assertion_passed",
                "lane_check_passed",
                "import_isolation_passed",
            )
            assert ids[-1] == "entrypoint_completed"

    def test_no_logged_event_can_carry_content(self, run) -> None:
        for returned in run["returns"].values():
            for event in returned["log"].events:
                assert set(event) == {
                    "schema_version",
                    "event_id",
                    "role",
                    "status",
                    "read_class",
                    "object_count",
                    "occurred_at_step",
                }


class TestCleanTwelveByTenConstruction:
    def test_the_admitted_set_is_twelve_strata_of_ten(self, run) -> None:
        per_stratum: dict[str, int] = {}
        for record in run["admitted"]:
            per_stratum[record["stratum"]] = per_stratum.get(record["stratum"], 0) + 1
        assert len(per_stratum) == 12
        assert set(per_stratum.values()) == {construction.STRATUM_QUOTA}

    def test_the_custodian_and_normalizer_admitted_the_whole_set(self, run) -> None:
        assert run["custodian"]["accepted"] == TOTAL
        assert run["normalizer"]["normalized"] == TOTAL

    def test_the_selector_accepted_the_whole_set(self, run) -> None:
        assert run["selector"]["selected"] == TOTAL

    def test_the_independent_auditor_re_derived_the_same_set(self, run) -> None:
        assert run["auditor"]["audited"] == TOTAL

    def test_the_set_facts_are_content_free(self, run) -> None:
        construction.assert_no_parser_field(run["facts"]["facts"], path="set_facts")
        rendered = repr(run["facts"]["facts"])
        for case_id in run["case_ids"][:5]:
            assert case_id not in rendered

    def test_a_set_of_the_wrong_size_is_refused(self) -> None:
        with pytest.raises(ConstructionError):
            launch("selector", admitted=_admitted()[:-1])

    def test_a_stratum_quota_violation_is_refused(self) -> None:
        admitted = _admitted()
        admitted[0]["stratum"] = admitted[-1]["stratum"]
        with pytest.raises(ConstructionError):
            launch("selector", admitted=admitted)

    def test_a_decision_class_quota_violation_is_refused(self) -> None:
        admitted = _admitted()
        admitted[0]["decision_class"] = "ambiguous"
        with pytest.raises(ConstructionError):
            launch("selector", admitted=admitted)


class TestBlindedAgreement:
    def test_both_reviewers_decided_every_case(self, run) -> None:
        assert len(run["reviewer_a"]["decisions"]) == TOTAL
        assert len(run["reviewer_b"]["decisions"]) == TOTAL

    def test_a_packet_carrying_a_forbidden_input_is_unrepresentable(self) -> None:
        packets = [_packet(0)]
        packets[0]["old_label"] = "leaked"
        with pytest.raises(SchemaValidationError):
            launch("reviewer_a", packets=packets, decide=lambda p: _decision(0, "reviewer_a"))

    def test_no_reviewer_ever_receives_the_other(self) -> None:
        seen: list[dict[str, Any]] = []

        def record(packet: dict[str, Any]) -> dict[str, Any]:
            seen.append(packet)
            return _decision(int(packet["case_ref"].rsplit("-", 1)[1]), "reviewer_b")

        launch("reviewer_b", packets=[_packet(0)], decide=record)
        assert seen
        for packet in seen:
            assert "reviewer_a" not in packet
            assert "other_reviewer_decision" not in packet


class TestDeterministicDisagreementAndArbitration:
    def test_full_agreement_routes_nothing(self, run) -> None:
        assert run["broker"]["routed"] == []
        assert run["arbiter"]["results"] == []

    def test_one_field_disagreement_routes_exactly_one_case(self) -> None:
        pairs = [_pair(index) for index in range(TOTAL)]
        pairs[4] = _pair(4, equivalence="normalised")
        broker = launch("broker", pairs=pairs)
        assert [packet["case_ref"] for packet in broker["routed"]] == [_case_id(4)]
        assert broker["routed"][0]["disagreeing_fields"] == ["equivalence"]

    def test_routing_is_deterministic_across_runs(self) -> None:
        pairs = [_pair(index) for index in range(TOTAL)]
        pairs[9] = _pair(9, output_quality="degraded")
        first = launch("broker", pairs=pairs)
        second = launch("broker", pairs=copy.deepcopy(pairs))
        assert [p["case_ref"] for p in first["routed"]] == [
            p["case_ref"] for p in second["routed"]
        ]
        assert first["routed"][0]["disagreeing_fields"] == (
            second["routed"][0]["disagreeing_fields"]
        )

    def test_the_arbiter_adjudicates_only_what_the_broker_routed(self) -> None:
        pairs = [_pair(index) for index in range(TOTAL)]
        pairs[4] = _pair(4, equivalence="normalised")
        broker = launch("broker", pairs=pairs)
        arbiter = launch("arbiter", packets=broker["routed"], adjudicate=_adjudicate)
        assert [result["case_ref"] for result in arbiter["results"]] == [_case_id(4)]

    def test_an_arbiter_packet_carrying_the_old_label_is_unrepresentable(self) -> None:
        pairs = [_pair(index) for index in range(TOTAL)]
        pairs[4] = _pair(4, equivalence="normalised")
        tainted = copy.deepcopy(launch("broker", pairs=pairs)["routed"])
        tainted[0]["old_label"] = "the retired answer"
        with pytest.raises(SchemaValidationError):
            launch("arbiter", packets=tainted, adjudicate=_adjudicate)

    def test_arbitrating_a_case_the_reviewers_agreed_on_is_refused(self) -> None:
        pairs = [_pair(index) for index in range(TOTAL)]
        agreed = {
            "schema_version": "phase1-parser-v3-v2-disagreement-packet/v1",
            "case_ref": _case_id(0),
            "case_content": _prompt(0),
            "public_ontology_packet": _ontology(),
            "reviewer_a": _decision(0, "reviewer_a"),
            "reviewer_b": _decision(0, "reviewer_b"),
            "disagreeing_fields": ["equivalence"],
        }
        with pytest.raises(ConstructionError):
            construction.assert_only_disagreements_reached_arbiter(
                arbitrated_case_ids=[agreed["case_ref"]],
                decisions_by_case={
                    pair["case_ref"]: (pair["reviewer_a"], pair["reviewer_b"])
                    for pair in pairs
                },
            )


class TestQuarantineAndBoundedReplacement:
    """Quarantine removes a case; replacement puts one back, at most so often.

    The replacement is a genuinely different case with its own identifier and
    its own literal frame, not the quarantined one re-admitted, because
    re-admitting the same content is how a set quietly keeps the case it
    claimed to remove.
    """

    def _quarantine(self, case_id: str, reason: str, batch: int = 0) -> dict[str, Any]:
        return {
            "schema_version": "phase1-parser-v3-v2-quarantine-record/v1",
            "case_id": case_id,
            "reason": reason,
            "recorded_at_batch": batch,
            "quarantine_digest": construction.content_hash(f"quarantine:{case_id}"),
        }

    def _replacement(self, batch: int) -> dict[str, Any]:
        return {
            "schema_version": "phase1-parser-v3-v2-replacement-record/v1",
            "replaced_case_id": _case_id(TOTAL - 1),
            "replacement_case_id": REPLACEMENT_CASE_ID,
            "batch_index": batch,
            "batch_size": 1,
            "cumulative_replacements": batch + 1,
            "within_limit": True,
        }

    def _replaced_set(self) -> list[dict[str, Any]]:
        admitted = _admitted()
        admitted[TOTAL - 1] = _admission_record(
            TOTAL - 1, case_id=REPLACEMENT_CASE_ID, prompt=REPLACEMENT_PROMPT
        )
        return admitted

    def test_a_quarantined_case_replaced_within_the_bound_is_accepted(self) -> None:
        result = launch(
            "selector",
            admitted=self._replaced_set(),
            quarantined=[self._quarantine(_case_id(TOTAL - 1), "semantic_uncertainty")],
            replacements=[self._replacement(0)],
            replacement_batch_limit=1,
        )
        assert result["selected"] == TOTAL

    def test_the_replacement_carries_a_different_identifier_and_frame(self) -> None:
        replaced = self._replaced_set()
        assert replaced[TOTAL - 1]["case_id"] == REPLACEMENT_CASE_ID
        assert replaced[TOTAL - 1]["content_digest"] == construction.content_hash(
            REPLACEMENT_PROMPT
        )
        contents = {_case_id(index): _prompt(index) for index in range(TOTAL - 1)}
        contents[REPLACEMENT_CASE_ID] = REPLACEMENT_PROMPT
        construction.assert_no_prohibited_collision(set_contents=contents)

    def test_an_unregistered_quarantine_reason_is_unrepresentable(self) -> None:
        record = self._quarantine(_case_id(TOTAL - 1), "semantic_uncertainty")
        record["reason"] = "inconvenient"
        with pytest.raises(SchemaValidationError):
            launch("selector", admitted=self._replaced_set(), quarantined=[record])

    def test_every_registered_reason_is_accepted(self) -> None:
        for reason in sorted(construction.QUARANTINE_REASONS):
            launch(
                "selector",
                admitted=self._replaced_set(),
                quarantined=[self._quarantine(_case_id(TOTAL - 1), reason)],
                replacements=[self._replacement(0)],
                replacement_batch_limit=1,
            )

    def test_a_second_replacement_batch_beyond_the_bound_is_refused(self) -> None:
        with pytest.raises(construction.BlockedOnSetRepair):
            launch(
                "selector",
                admitted=self._replaced_set(),
                quarantined=[self._quarantine(_case_id(TOTAL - 1), "semantic_uncertainty")],
                replacements=[self._replacement(1)],
                replacement_batch_limit=1,
            )

    def test_the_bound_is_the_preregistered_one_and_not_a_default(self) -> None:
        result = launch(
            "selector",
            admitted=self._replaced_set(),
            replacements=[self._replacement(1)],
            replacement_batch_limit=2,
        )
        assert result["selected"] == TOTAL


class TestEveryCollisionRule:
    """Each registered rule is shown catching a collision the earlier ones miss.

    ``assert_no_prohibited_collision`` applies the rules in registration order
    and raises on the first one that finds a duplicate, so naming the rule in
    the refusal is evidence that *that* rule did the catching. A pair that
    collides under every rule would prove only that the first rule works.
    """

    _BASE = "a lone dispatch filed with the harbourmaster"

    #: rule under test -> (first text, second text, rules that must NOT collide)
    _CASES: dict[str, tuple[str, str, tuple[str, ...]]] = {
        "exact": (_BASE, _BASE, ()),
        "normalized": (_BASE, f"   {_BASE.upper()}   ", ("exact",)),
        "numeric_normalized": (
            f"{_BASE} lot 07",
            f"{_BASE} lot 7",
            ("exact", "normalized"),
        ),
        "template_family": (
            f'{_BASE} marked "alpha"',
            f'{_BASE} marked "beta"',
            ("exact", "normalized", "numeric_normalized"),
        ),
    }

    def test_the_rehearsal_set_is_collision_free_under_every_rule(self) -> None:
        contents = {_case_id(index): _prompt(index) for index in range(TOTAL)}
        construction.assert_no_prohibited_collision(set_contents=contents)

    def test_every_registered_rule_has_a_case(self) -> None:
        assert set(self._CASES) == set(construction.COLLISION_RULES)

    @pytest.mark.parametrize("rule_name", sorted(_CASES))
    def test_the_rule_maps_the_pair_to_one_fingerprint(self, rule_name: str) -> None:
        first, second, immune = self._CASES[rule_name]
        rule = construction.COLLISION_RULES[rule_name]
        assert rule(first) == rule(second)
        for other in immune:
            assert construction.COLLISION_RULES[other](first) != (
                construction.COLLISION_RULES[other](second)
            )

    @pytest.mark.parametrize("rule_name", sorted(_CASES))
    def test_the_checker_refuses_the_pair_under_that_rule(self, rule_name: str) -> None:
        first, second, _ = self._CASES[rule_name]
        contents = {_case_id(index): _prompt(index) for index in range(TOTAL)}
        contents["intruder-one"] = first
        contents["intruder-two"] = second
        with pytest.raises(ConstructionError, match=f"within-set collision under rule '{rule_name}'"):
            construction.assert_no_prohibited_collision(set_contents=contents)

    def test_no_rule_can_be_skipped(self) -> None:
        assert set(construction.COLLISION_RULES) == {
            "exact",
            "normalized",
            "numeric_normalized",
            "template_family",
        }

    def test_a_corpus_without_a_fingerprint_for_a_rule_is_refused(self) -> None:
        contents = {_case_id(index): _prompt(index) for index in range(TOTAL)}
        with pytest.raises(ConstructionError, match="supplied no fingerprint"):
            construction.assert_no_prohibited_collision(
                set_contents=contents,
                external_corpus_fingerprints={"retired-v1": {"exact": "deadbeef"}},
            )


class TestCreateOnlySetSealAndListingWitness:
    def test_the_seal_creates_every_planned_object(self, run) -> None:
        assert run["seal"]["created"] == len(run["plan"]["planned_objects"])
        assert run["seal"]["created"] == TOTAL + 1

    def test_the_seal_writes_the_terminal_manifest_last(self, run) -> None:
        assert run["plan"]["write_order"][-1] == run["plan"]["terminal_manifest"]

    def test_the_seal_records_a_create_event_before_completing(self, run) -> None:
        ids = run["seal"]["log"].event_ids()
        assert ids.index("payload_write_created") < ids.index("entrypoint_completed")

    def test_sealing_into_a_non_empty_namespace_is_refused(self) -> None:
        plan = _construction_plan()
        with pytest.raises(LifecycleError):
            launch("seal_custodian", plan=plan, existing_objects=[plan["planned_objects"][0]])

    def test_a_manifest_written_before_its_members_is_refused(self) -> None:
        plan = _construction_plan()
        plan["write_order"] = [plan["terminal_manifest"]] + plan["write_order"][:-1]
        with pytest.raises(LifecycleError):
            launch("seal_custodian", plan=plan)


class TestThePassPath:
    def test_the_pipeline_produces_exactly_one_accepted_result(self, run) -> None:
        assert run["stream"]["state"] == "PREDICTION_RUNNING"
        assert run["receipt"]["state"] == "PREDICTION_SEALED"
        assert run["receipt"]["member_count"] == TOTAL
        assert run["result"]["state"] == "EVALUATED_ACCEPTED"
        assert run["result"]["status"] == "PASS"
        assert run["result"]["ordinal"] == 1
        assert run["result"]["eligible_case_count"] == TOTAL

    def test_every_binding_gate_is_true_and_none_are_missing(self, run) -> None:
        gates = run["result"]["binding_gates"]
        assert all(gates.values())
        for stratum in evaluation.ZERO_ERROR_RESIDUAL_STRATA:
            assert f"residual_{stratum}_zero_error" in gates
        for gate in evaluation.PINNED_ZERO_ERROR_GATES:
            assert gate in gates

    def test_the_result_is_bound_to_the_lock_and_the_seal(self, run) -> None:
        assert run["result"]["lock_digest"] == run["lock_digest"]
        assert run["result"]["prediction_receipt_digest"] == run["receipt"]["receipt_digest"]

    def test_the_lock_preregisters_the_registered_commands(self, run) -> None:
        assert run["lock"]["stage_p_command"] == list(
            entrypoints.ENTRYPOINTS["stage_p"].command
        )
        assert run["lock"]["stage_e_command"] == list(
            entrypoints.ENTRYPOINTS["stage_e"].command
        )
        assert run["lock"]["stage_p_identity"] == entrypoints.ROLE_IDENTITY_NAMES["stage_p"]
        assert run["lock"]["stage_e_identity"] == entrypoints.ROLE_IDENTITY_NAMES["stage_e"]

    def test_the_exported_receipt_is_the_only_thing_that_leaves(self, run) -> None:
        exported = run["exporter"]["exported"]
        construction.assert_no_parser_field(exported, path="public_receipt")
        assert set(exported["counts"]) == {
            "private_semantic_reads",
            "sealed_sets",
            "preregistrations",
            "stage_p_runs",
            "stage_e_runs",
        }

    def test_the_diagnostics_had_no_path_to_the_status(self, run) -> None:
        overlap = set(evaluation.NONBINDING_DIAGNOSTICS) & set(run["result"]["binding_gates"])
        assert overlap == set()


class TestTheFailPath:
    def test_one_eligible_mismatch_fails_rather_than_prompting_a_review(self) -> None:
        def one_wrong(case: dict[str, Any]) -> dict[str, Any]:
            prediction = _perfect_parser(case)
            if case["case_id"] == _case_id(0):
                prediction["canonical_value"] = "wrong"
            return prediction

        result = rehearse(parser=one_wrong)["result"]
        assert result["status"] == "FAIL"
        assert result["state"] == "EVALUATED_NOT_ACCEPTED"
        assert result["pinned_mismatches"]["canonical_present_value_exact"] == 1

    def test_a_residual_stratum_error_fails_pooled_and_per_stratum(self) -> None:
        residual_index = construction.STRATA.index("S04") * construction.STRATUM_QUOTA

        def wrong_in_s04(case: dict[str, Any]) -> dict[str, Any]:
            prediction = _perfect_parser(case)
            if case["case_id"] == _case_id(residual_index):
                prediction["canonical_value"] = "wrong"
            return prediction

        result = rehearse(parser=wrong_in_s04)["result"]
        gates = result["binding_gates"]
        assert gates["residual_pooled_zero_error"] is False
        assert gates["residual_S04_zero_error"] is False
        assert gates["residual_S05_zero_error"] is True
        assert result["status"] == "FAIL"

    def test_a_failing_run_still_produces_a_complete_result(self) -> None:
        def one_wrong(case: dict[str, Any]) -> dict[str, Any]:
            prediction = _perfect_parser(case)
            if case["case_id"] == _case_id(0):
                prediction["canonical_value"] = "wrong"
            return prediction

        result = rehearse(parser=one_wrong)["result"]
        assert result["eligible_case_count"] == TOTAL
        assert result["ordinal"] == 1


class TestTheInvalidPath:
    """A protocol violation must produce no result at all.

    FAIL is a scientific outcome and INVALID is not. A run whose bindings
    moved, whose receipt was forged, or whose stages ran out of order has not
    measured anything, and the difference between the two is the difference
    between reporting a negative result and reporting a number that means
    nothing. Each case below therefore asserts that no result object exists,
    not that the result says something bad.
    """

    def test_a_moved_binding_produces_no_result(self, run) -> None:
        tampered = copy.deepcopy(run["lock"])
        tampered["retry_rule"] = "retry freely"
        with pytest.raises(EvaluationError, match="lock changed after creation"):
            launch(
                "stage_e",
                lock=tampered,
                lock_digest=run["lock_digest"],
                prediction_receipt=run["receipt"],
                sealed_members=run["stream"]["members"],
                labels=_labels(),
                strata=_strata(),
            )

    def test_a_forged_receipt_produces_no_result(self, run) -> None:
        forged = copy.deepcopy(run["receipt"])
        forged["receipt_digest"] = "f" * 64
        with pytest.raises(EvaluationError, match="does not verify"):
            launch(
                "stage_e",
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=forged,
                sealed_members=run["stream"]["members"],
                labels=_labels(),
                strata=_strata(),
            )

    def test_predictions_that_are_not_the_sealed_stream_produce_no_result(self, run) -> None:
        swapped = copy.deepcopy(run["stream"]["members"])
        swapped[0], swapped[1] = swapped[1], swapped[0]
        with pytest.raises(EvaluationError, match="not the sealed prediction stream"):
            launch(
                "stage_e",
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=run["receipt"],
                sealed_members=swapped,
                labels=_labels(),
                strata=_strata(),
            )

    def test_stage_e_before_the_seal_is_unrepresentable(self, run) -> None:
        unsealed = copy.deepcopy(run["receipt"])
        unsealed["state"] = "PREDICTION_RUNNING"
        with pytest.raises(SchemaValidationError):
            launch(
                "stage_e",
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=unsealed,
                sealed_members=run["stream"]["members"],
                labels=_labels(),
                strata=_strata(),
            )

    def test_a_label_bearing_input_refuses_before_the_parser_runs(self, run) -> None:
        inputs = _locked_inputs()
        inputs[7]["gold_answer"] = "leaked"
        calls: list[str] = []

        def counting_parser(case: dict[str, Any]) -> dict[str, Any]:
            calls.append(case["case_id"])
            return _perfect_parser(case)

        with pytest.raises(EvaluationError, match="label-bearing field"):
            launch(
                "stage_p",
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                state="PREREGISTERED",
                ordinal=0,
                locked_inputs=inputs,
                parser=counting_parser,
            )
        assert calls == [], "the parser ran before the label check refused the payload"


class TestThePartialUploadPath:
    def test_a_partially_uploaded_namespace_cannot_be_resumed(self) -> None:
        plan = _construction_plan()
        with pytest.raises(LifecycleError):
            launch("seal_custodian", plan=plan, existing_objects=plan["planned_objects"][:60])

    def test_a_plan_missing_an_object_it_will_write_is_refused(self) -> None:
        plan = _construction_plan()
        plan["planned_objects"] = plan["planned_objects"][:-1]
        with pytest.raises(LifecycleError):
            launch("seal_custodian", plan=plan)

    def test_the_complete_plan_into_an_empty_namespace_is_accepted(self) -> None:
        assert launch("seal_custodian", plan=_construction_plan())["created"] == TOTAL + 1


class TestThePartialPredictionPath:
    def test_a_stream_missing_a_case_cannot_seal(self, run) -> None:
        short = copy.deepcopy(run["stream"])
        short["members"] = short["members"][:-1]
        order, manifest = _prediction_write_order(run["case_ids"])
        with pytest.raises(LifecycleError):
            launch(
                "prediction_sealer",
                stream=short,
                sealed_case_ids=run["case_ids"],
                write_order=order,
                terminal_manifest=manifest,
            )

    def test_a_stream_with_an_extra_member_is_unrepresentable(self, run) -> None:
        extra = copy.deepcopy(run["stream"])
        extra["members"] = list(extra["members"]) + [extra["members"][0]]
        order, manifest = _prediction_write_order(run["case_ids"])
        with pytest.raises(SchemaValidationError):
            launch(
                "prediction_sealer",
                stream=extra,
                sealed_case_ids=run["case_ids"],
                write_order=order,
                terminal_manifest=manifest,
            )

    def test_the_complete_stream_seals(self, run) -> None:
        assert run["receipt"]["member_count"] == TOTAL
        assert len(run["stream"]["members"]) == TOTAL


class TestTheWrongRolePath:
    def test_stage_e_run_under_the_stage_p_identity_is_refused(self, run) -> None:
        with pytest.raises(EntrypointError):
            entrypoints.run_stage_e(
                config=_config("stage_p"),
                environment=_env(),
                loaded_module_names=CLEAN_MODULES,
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=run["receipt"],
                sealed_members=run["stream"]["members"],
                labels=_labels(),
                strata=_strata(),
            )

    def test_a_role_running_under_another_roles_identity_is_refused(self) -> None:
        config = _config("selector", uami_name=entrypoints.ROLE_IDENTITY_NAMES["arbiter"])
        with pytest.raises(EntrypointError):
            launch("selector", config=config, admitted=_admitted())

    def test_a_role_reaching_another_roles_container_is_refused(self) -> None:
        config = _config("normalizer", container=entrypoints.REGISTERED_CONTAINERS["stage_e"])
        with pytest.raises(EntrypointError):
            launch("normalizer", config=config, admission_records=_admitted())

    def test_a_role_holding_no_managed_identity_is_refused(self) -> None:
        spec = entrypoints.ENTRYPOINTS["normalizer"]
        with pytest.raises(EntrypointError):
            spec.function(
                config=_config("normalizer"),
                environment={},
                loaded_module_names=CLEAN_MODULES,
                admission_records=_admitted(),
            )

    def test_no_role_other_than_stage_e_may_read_labels(self) -> None:
        for role in entrypoints.ROLE_IDENTITY_NAMES:
            if role == lifecycle.LABEL_READING_ROLE:
                continue
            with pytest.raises(EntrypointError):
                entrypoints.assert_lanes(role, reads=["scoring_labels"], writes=[])


class TestTheWrongEntrypointPath:
    def test_a_command_naming_another_role_is_refused_for_this_role(self) -> None:
        stage_e = entrypoints.ENTRYPOINTS["stage_e"]
        assert entrypoints.resolve_entrypoint(stage_e.command).role == "stage_e"
        with pytest.raises(EntrypointError):
            entrypoints.assert_container_command_is_registered(
                role="stage_p", command=stage_e.command
            )

    def test_the_module_form_command_is_refused(self) -> None:
        with pytest.raises(EntrypointError):
            entrypoints.resolve_entrypoint(
                ("python", "-m", "jspace_observation.parser_v3_v2_entrypoints", "stage_p")
            )

    def test_an_unregistered_entrypoint_name_is_refused(self) -> None:
        with pytest.raises(EntrypointError):
            entrypoints.resolve_entrypoint(
                ("python", entrypoints.CONTAINER_ENTRYPOINT_PATH, "stage_x")
            )

    def test_an_extra_argument_is_refused_rather_than_ignored(self) -> None:
        with pytest.raises(EntrypointError):
            entrypoints.resolve_entrypoint(
                tuple(entrypoints.ENTRYPOINTS["stage_p"].command) + ("--extra",)
            )


class TestTheIneligibleSealedCasePath:
    def test_an_ineligible_label_is_refused_rather_than_skipped(self) -> None:
        labels = _labels()
        labels[_case_id(3)]["eligible"] = False
        with pytest.raises(EvaluationError, match="ineligible at scoring time"):
            rehearse(labels=labels)

    def test_the_denominator_cannot_shrink_after_sealing(self, run) -> None:
        assert run["result"]["eligible_case_count"] == TOTAL

    def test_a_sealed_case_with_no_label_is_refused(self, run) -> None:
        labels = _labels()
        labels.pop(_case_id(5))
        with pytest.raises(EvaluationError, match="no label for sealed prediction"):
            launch(
                "stage_e",
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=run["receipt"],
                sealed_members=run["stream"]["members"],
                labels=labels,
                strata=_strata(),
            )

    def test_an_ineligible_case_cannot_be_admitted_in_the_first_place(self) -> None:
        admitted = _admitted()
        admitted[3]["eligible"] = False
        with pytest.raises(SchemaValidationError):
            launch("selector", admitted=admitted)


class TestTheSecondLaunchPath:
    def test_a_second_preregistration_is_refused(self, run) -> None:
        with pytest.raises(EvaluationError, match="already exists"):
            launch(
                "preregistration_compiler",
                bindings=_bindings(),
                existing_lock_digest=run["lock_digest"],
            )

    def test_a_second_stage_p_is_refused(self, run) -> None:
        with pytest.raises(EvaluationError):
            launch(
                "stage_p",
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                state="PREDICTION_SEALED",
                ordinal=1,
                locked_inputs=_locked_inputs(),
                parser=_perfect_parser,
            )

    def test_a_second_prediction_seal_is_refused(self, run) -> None:
        order, manifest = _prediction_write_order(run["case_ids"])
        with pytest.raises(LifecycleError):
            launch(
                "prediction_sealer",
                stream=run["stream"],
                sealed_case_ids=run["case_ids"],
                write_order=order,
                terminal_manifest=manifest,
                existing_objects=[order[0]],
            )

    def test_the_ordinal_advances_exactly_once(self, run) -> None:
        assert run["result"]["ordinal"] == lifecycle.MAX_FORMAL_EVALUATION_ORDINAL
        with pytest.raises(LifecycleError):
            lifecycle.assert_ordinal_succession(
                run["result"]["ordinal"], run["result"]["ordinal"] + 1
            )
