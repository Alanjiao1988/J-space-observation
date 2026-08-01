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
RECEIPT = ROOT / "docs" / "phase1_2h_r1_access_receipt_003.json"


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


def passing_gate() -> dict:
    """Gate evidence derived from the committed receipt, not asserted.

    Audit C (C-01) found these tests --- and the CI workflow --- handing the
    assessor ``byte_only_gate_passed=True`` as a literal, so the instrument that
    decides the round's terminal state was being told its own answer. Every call
    site now goes through the receipt, which means the tests exercise the
    derivation path that production uses instead of bypassing it.
    """

    return assessor.load_gate_evidence(RECEIPT)


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
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
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
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
    assert result["qualification_verdict"] == "DOES_NOT_QUALIFY"
    assert result["terminal_state"] == "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"


def test_the_decisive_failure_is_the_absence_of_any_in_boundary_reviewer(evidence):
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
    by_key = {c["key"]: c for c in result["conditions"]}
    assert by_key["worker_in_project_vnet_or_approved_private_link_boundary"]["verdict"] == "FAIL"
    assert by_key["reviewer_public_network_access_disabled"]["verdict"] == "FAIL"


def test_unrestricted_egress_is_reported_as_a_failure(evidence):
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
    by_key = {c["key"]: c for c in result["conditions"]}
    assert (
        by_key["no_unrestricted_internet_egress_while_holding_private_material"]["verdict"]
        == "FAIL"
    )


def test_attaching_a_route_table_would_clear_the_egress_condition(mutable_evidence):
    # Records the fact that the gap is configuration, not capability: the
    # environment is a workload-profiles environment, so a UDR is supported.
    mutable_evidence["worker_egress"]["route_table"] = "/subscriptions/x/routeTables/rt"
    result = assessor.build_assessment(mutable_evidence, gate_evidence=passing_gate())
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
    result = assessor.build_assessment(mutable_evidence, gate_evidence=passing_gate())
    assert result["summary"]["passed"] == 3
    assert result["qualification_verdict"] == "DOES_NOT_QUALIFY"


def test_no_reviewer_at_all_is_reported_as_a_failure_not_a_pass(mutable_evidence):
    mutable_evidence["candidate_reviewer_endpoints"] = []
    result = assessor.build_assessment(mutable_evidence, gate_evidence=passing_gate())
    by_key = {c["key"]: c for c in result["conditions"]}
    assert by_key["reviewer_public_network_access_disabled"]["verdict"] == "FAIL"
    assert by_key["reviewer_dns_resolves_to_registered_private_endpoint"]["verdict"] == "FAIL"


# --- 5. The emitted document is closed --------------------------------------


def test_the_boundary_schema_is_closed_everywhere():
    validator.load_schema(BOUNDARY_SCHEMA)


def test_the_assessment_validates(evidence):
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
    validator.validate_receipt(result, BOUNDARY_SCHEMA)


def test_an_undeclared_field_is_rejected(evidence):
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
    result["prompt_text"] = "what does case 7 say"
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(result, BOUNDARY_SCHEMA)


def test_the_assessment_cannot_report_a_semantic_read(evidence):
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
    result["instrument_access_effect"]["sealed_input_semantic_reads"] = 1
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(result, BOUNDARY_SCHEMA)


def test_the_assessment_cannot_report_a_resource_change(evidence):
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
    result["instrument_access_effect"]["azure_resource_changes"] = 1
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


# --- 6. Audit C remediations -------------------------------------------------


def test_the_gate_outcome_is_derived_from_the_receipt_not_supplied():
    # C-01, the blocker. The assessor took --byte-only-gate-passed as an
    # operator literal and CI passed `true`. The instrument that decides the
    # round's terminal state was being handed its own answer, so a round that
    # never reached the source could still have produced
    # BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY -- the state that asserts a gate ran.
    import inspect

    signature = inspect.signature(assessor.build_assessment)
    assert "byte_only_gate_passed" not in signature.parameters
    assert "gate_evidence" in signature.parameters

    source = ASSESSOR_PATH.read_text(encoding="utf-8")
    assert "--byte-only-gate-passed" not in source

    workflow = (
        ROOT / ".github" / "workflows" / "phase1_2h_r1_public_validation.yml"
    ).read_text(encoding="utf-8")
    # Comments may name the removed flag -- the workflow explains why it went --
    # so only executable lines are checked.
    executable = [
        line for line in workflow.splitlines() if not line.lstrip().startswith("#")
    ]
    assert not any("--byte-only-gate-passed" in line for line in executable)
    assert any("--receipt" in line for line in executable)


def test_no_receipt_means_the_gate_did_not_pass():
    # Absence of evidence is recorded as absence, not as an error and not as a
    # pass. A round that could not reach the source must still be able to state
    # its result.
    gate = assessor.load_gate_evidence(None)
    assert gate["passed"] is False
    assert gate["receipt_sha256"] is None
    assert gate["unmet_requirements"]


def test_without_a_gate_the_round_cannot_claim_the_boundary_state(evidence):
    result = assessor.build_assessment(
        evidence, gate_evidence=assessor.load_gate_evidence(None)
    )
    assert result["terminal_state"] == "BLOCKED_ON_PRIVATE_SOURCE_ACCESS"


def test_the_committed_receipt_satisfies_every_gate_requirement():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    passed, failures = assessor.derive_gate_outcome(receipt)
    assert passed is True
    assert failures == []
    assert len(assessor.GATE_REQUIREMENTS) >= 12


@pytest.mark.parametrize(
    "section,key,bad",
    [
        ("verdict", "access_gate_passed", False),
        ("streaming", "objects_streamed", 11),
        ("streaming", "all_digests_match", False),
        ("streaming", "digest_mismatch_count", 1),
        ("membership", "member_sets_equal", False),
        ("counters", "semantic_input_reads", 1),
        ("counters", "semantic_label_reads", 1),
        ("execution", "exit_status", "REFUSED"),
    ],
)
def test_a_single_broken_conjunct_fails_the_whole_gate(section, key, bad):
    # Reading verdict.access_gate_passed alone would barely improve on an
    # operator boolean -- it is one field the probe wrote about itself. Every
    # conjunct must hold independently, so breaking any one is decisive.
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt[section][key] = bad
    passed, failures = assessor.derive_gate_outcome(receipt)
    assert passed is False
    assert any(key in failure for failure in failures)


def test_a_boolean_does_not_satisfy_a_count_requirement():
    # `objects_streamed: True` must not pass a requirement for 12, and it must
    # not pass one for 1 either: in Python True == 1.
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt["streaming"]["digest_mismatch_count"] = False
    passed, failures = assessor.derive_gate_outcome(receipt)
    assert passed is False
    assert any("digest_mismatch_count" in failure for failure in failures)


def test_the_assessment_records_which_receipt_it_read(evidence):
    result = assessor.build_assessment(evidence, gate_evidence=passing_gate())
    binding = result["byte_only_gate_evidence"]
    assert binding["receipt_path"].endswith("phase1_2h_r1_access_receipt_003.json")
    assert len(binding["receipt_sha256"]) == 64
    assert binding["passed"] is True


def test_a_receipt_that_fails_its_own_schema_is_not_usable_as_evidence(tmp_path):
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt["counters"]["semantic_input_reads"] = 1
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    # The assessor loads its own copy of the validator module, so the exception
    # class it raises is not the one this file loaded. Matching on the message
    # is what distinguishes "refused for the right reason" from "refused".
    with pytest.raises(Exception) as exc:
        assessor.load_gate_evidence(path)
    assert "semantic_input_reads" in str(exc.value)
    assert "above maximum 0" in str(exc.value)


def test_the_terminal_state_vocabularies_agree():
    # C-07. Three vocabularies existed: the ledger's TERMINAL_STATES, the
    # protocol's table, and the state this assessor can emit. The assessor must
    # not import jspace_observation -- __init__ eagerly imports the legacy
    # parser, which would place parser code in the instrument's process -- so
    # the subset assertion lives here, where a test may import both freely.
    src = str(ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from jspace_observation.parser_v3_v2_access_ledger import TERMINAL_STATES

    emitted = set(assessor.TERMINAL_STATE_BY_OUTCOME.values())
    assert emitted
    assert emitted <= set(TERMINAL_STATES)


def test_the_assessor_does_not_import_the_package():
    source = ASSESSOR_PATH.read_text(encoding="utf-8")
    assert "import jspace_observation" not in source
    assert "from jspace_observation" not in source
