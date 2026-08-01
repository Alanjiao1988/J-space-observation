"""Tests for the Phase 1.2H-R1 private-review-boundary assessment instrument.

Independent Audit B (B-09) found the round's terminal state rested on prose:
nothing committed could be re-executed to check it, and nothing recorded which
frozen condition failed. These tests attack the instrument that replaced the
prose -- in particular the two ways such an instrument goes wrong, which are
letting an unassessed condition read as satisfied, and letting the more
advanced-sounding terminal state be claimed by a round that never reached the
source.

Nothing here touches Azure, the network, or any private material.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ASSESSOR_PATH = SCRIPTS / "phase1_2h_r1_review_boundary_assessment.py"
VALIDATOR_PATH = SCRIPTS / "phase1_2h_r1_receipt_validator.py"
BOUNDARY_SCHEMA = ROOT / "docs" / "phase1_2h_r1_review_boundary.schema.json"
EVIDENCE = ROOT / "docs" / "phase1_2h_r1_review_boundary_evidence.json"
DECISION_RECORD = ROOT / "docs" / "phase1_2h_r1_access_decision_record.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


assessor = _load(ASSESSOR_PATH, "_p12hr1_boundary")
validator = _load(VALIDATOR_PATH, "_p12hr1_boundary_validator")


@pytest.fixture(scope="module")
def evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


@pytest.fixture()
def mutable_evidence(evidence: dict) -> dict:
    return copy.deepcopy(evidence)


# --- 1. The instrument agrees with the frozen record ------------------------


def test_the_key_list_matches_the_frozen_condition_list():
    # If a condition is added to the decision record and no key is added here,
    # the instrument must fail loudly rather than assess 13 of 14 conditions
    # and report a clean result.
    conditions = assessor.load_conditions()
    assert len(conditions) == len(assessor.CONDITION_KEYS)


def test_a_diverged_condition_list_is_refused(tmp_path):
    record = json.loads(DECISION_RECORD.read_text(encoding="utf-8"))
    record["private_review_boundary_requirements"]["conditions"].append("a new one")
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(assessor.BoundaryAssessmentError):
        assessor.load_conditions(path)


def test_every_frozen_condition_appears_in_the_assessment(evidence):
    result = assessor.build_assessment(evidence, byte_only_gate_passed=True)
    assert len(result["conditions"]) == len(assessor.CONDITION_KEYS)
    assert [c["key"] for c in result["conditions"]] == list(assessor.CONDITION_KEYS)


# --- 2. NOT_ASSESSABLE is not a pass ----------------------------------------


def test_an_unassessable_condition_does_not_qualify():
    results = {key: {"verdict": "PASS", "basis": "x"} for key in assessor.CONDITION_KEYS}
    assert assessor.qualification_verdict(results) == "QUALIFIES"
    results[assessor.CONDITION_KEYS[0]] = {"verdict": "NOT_ASSESSABLE", "basis": "x"}
    assert assessor.qualification_verdict(results) == "DOES_NOT_QUALIFY"


def test_a_single_failure_does_not_qualify():
    results = {key: {"verdict": "PASS", "basis": "x"} for key in assessor.CONDITION_KEYS}
    results[assessor.CONDITION_KEYS[-1]] = {"verdict": "FAIL", "basis": "x"}
    assert assessor.qualification_verdict(results) == "DOES_NOT_QUALIFY"


# --- 3. Precedence between the two blocked states ---------------------------


def test_a_failed_byte_gate_blocks_on_source_access_not_the_boundary():
    # The whole point of the precedence rule: a round that never reached the
    # source cannot claim the state that means "I reached it and stopped".
    state = assessor.classify_terminal_state(False, "DOES_NOT_QUALIFY")
    assert state == "BLOCKED_ON_PRIVATE_SOURCE_ACCESS"


def test_a_failed_byte_gate_blocks_on_source_access_even_if_a_backend_qualifies():
    state = assessor.classify_terminal_state(False, "QUALIFIES")
    assert state == "BLOCKED_ON_PRIVATE_SOURCE_ACCESS"


def test_a_passed_gate_with_no_qualifying_backend_blocks_on_the_boundary():
    state = assessor.classify_terminal_state(True, "DOES_NOT_QUALIFY")
    assert state == "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"


def test_a_passed_gate_and_a_qualifying_backend_is_not_authorisation_to_review():
    state = assessor.classify_terminal_state(True, "QUALIFIES")
    assert state == "READY_FOR_SEPARATELY_AUTHORISED_PRIVATE_REVIEW"


# --- 4. The observed facts produce the recorded verdict ---------------------


def test_the_committed_evidence_does_not_qualify(evidence):
    result = assessor.build_assessment(evidence, byte_only_gate_passed=True)
    assert result["qualification_verdict"] == "DOES_NOT_QUALIFY"
    assert result["terminal_state"] == "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"


def test_the_decisive_failure_is_the_absence_of_any_in_boundary_reviewer(evidence):
    result = assessor.build_assessment(evidence, byte_only_gate_passed=True)
    by_key = {c["key"]: c for c in result["conditions"]}
    assert by_key["worker_in_project_vnet_or_approved_private_link_boundary"]["verdict"] == "FAIL"
    assert by_key["reviewer_public_network_access_disabled"]["verdict"] == "FAIL"


def test_unrestricted_egress_is_reported_as_a_failure(evidence):
    result = assessor.build_assessment(evidence, byte_only_gate_passed=True)
    by_key = {c["key"]: c for c in result["conditions"]}
    assert (
        by_key["no_unrestricted_internet_egress_while_holding_private_material"]["verdict"]
        == "FAIL"
    )


def test_attaching_a_route_table_would_clear_the_egress_condition(mutable_evidence):
    # Records the fact that the gap is configuration, not capability: the
    # environment is a workload-profiles environment, so a UDR is supported.
    mutable_evidence["worker_egress"]["route_table"] = "/subscriptions/x/routeTables/rt"
    result = assessor.build_assessment(mutable_evidence, byte_only_gate_passed=True)
    by_key = {c["key"]: c for c in result["conditions"]}
    assert (
        by_key["no_unrestricted_internet_egress_while_holding_private_material"]["verdict"]
        == "PASS"
    )
    # But the round is still blocked, because a reviewer still does not exist.
    assert result["qualification_verdict"] == "DOES_NOT_QUALIFY"


def test_a_private_reviewer_alone_does_not_qualify_the_boundary(mutable_evidence):
    # A reviewer inside a private boundary clears the first three conditions
    # and nothing else. The eight design conditions remain NOT_ASSESSABLE, so
    # the verdict must not flip to QUALIFIES on infrastructure alone.
    mutable_evidence["candidate_reviewer_endpoints"] = [
        {
            "name": "synthetic",
            "resource_group": "rg-jspace-observation-sea",
            "kind": "Microsoft.CognitiveServices/accounts",
            "location": "southeastasia",
            "public_network_access": "Disabled",
            "network_default_action": "Deny",
            "private_endpoint_count": 1,
            "in_project_resource_group": True,
        }
    ]
    result = assessor.build_assessment(mutable_evidence, byte_only_gate_passed=True)
    assert result["summary"]["passed"] == 3
    assert result["qualification_verdict"] == "DOES_NOT_QUALIFY"


def test_no_reviewer_at_all_is_reported_as_a_failure_not_a_pass(mutable_evidence):
    mutable_evidence["candidate_reviewer_endpoints"] = []
    result = assessor.build_assessment(mutable_evidence, byte_only_gate_passed=True)
    by_key = {c["key"]: c for c in result["conditions"]}
    assert by_key["reviewer_public_network_access_disabled"]["verdict"] == "FAIL"
    assert by_key["reviewer_dns_resolves_to_registered_private_endpoint"]["verdict"] == "FAIL"


# --- 5. The emitted document is closed --------------------------------------


def test_the_boundary_schema_is_closed_everywhere():
    validator.load_schema(BOUNDARY_SCHEMA)


def test_the_assessment_validates(evidence):
    result = assessor.build_assessment(evidence, byte_only_gate_passed=True)
    validator.validate_receipt(result, BOUNDARY_SCHEMA)


def test_an_undeclared_field_is_rejected(evidence):
    result = assessor.build_assessment(evidence, byte_only_gate_passed=True)
    result["prompt_text"] = "what does case 7 say"
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(result, BOUNDARY_SCHEMA)


def test_the_assessment_cannot_report_a_semantic_read(evidence):
    result = assessor.build_assessment(evidence, byte_only_gate_passed=True)
    result["access_ledger_effect"]["sealed_input_semantic_reads"] = 1
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(result, BOUNDARY_SCHEMA)


def test_the_assessment_cannot_report_a_resource_change(evidence):
    result = assessor.build_assessment(evidence, byte_only_gate_passed=True)
    result["access_ledger_effect"]["azure_resource_changes"] = 1
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(result, BOUNDARY_SCHEMA)


def test_the_instrument_reads_no_private_material(evidence):
    # The evidence bundle is committed and public. Guard structurally against a
    # future edit that points it at private material.
    #
    # A substring search would be the wrong instrument here, and the first
    # draft of this test proved it: the bundle's own note legitimately says
    # "no private curator file", so searching for "curator" failed on correct
    # content. That is the same defect class independent Audit B raised as
    # B-06. The check is now an exact key allowlist plus a value-shape rule.
    allowed_top = {
        "observed_at",
        "evidence_source",
        "note",
        "project_resource_group",
        "candidate_reviewer_endpoints",
        "worker_egress",
    }
    assert set(evidence) == allowed_top

    allowed_endpoint = {
        "name",
        "resource_group",
        "kind",
        "location",
        "public_network_access",
        "network_default_action",
        "private_endpoint_count",
        "in_project_resource_group",
        "comment",
    }
    for endpoint in evidence["candidate_reviewer_endpoints"]:
        assert set(endpoint) <= allowed_endpoint

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            # No filesystem path and no blob URL may appear anywhere in the
            # bundle: those are the shapes that could address private content.
            assert "://" not in node or node.startswith("https://github.com/")
            assert not node.startswith("/subscriptions/") or "/providers/" in node

    walk(evidence)


def test_the_instrument_does_not_import_the_eager_parser_package():
    import ast

    tree = ast.parse(ASSESSOR_PATH.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            roots.add((node.module or "").split(".")[0])
    assert "jspace_observation" not in roots
