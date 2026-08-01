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


# --- Audit E / Audit F regressions -----------------------------------------

COMMITTED_ASSESSMENT = ROOT / "docs" / "phase1_2h_r1_review_boundary_assessment.json"
INVENTORY = ROOT / "docs" / "phase1_2h_r1_job_execution_inventory.json"


def test_the_consistency_check_runs_against_the_committed_assessment():
    """Audit E (E-01): the check could not fail.

    ``assert_gate_evidence_consistent`` was only ever called on the object
    ``build_assessment`` had just returned, which was derived from the same gate
    evidence the check re-derives. Three documents described it as an
    enforcement point in three places. It is now applied to the committed file,
    which is the artifact a reader trusts and the one an editor would tamper
    with, and the tests below show it rejecting tampering.
    """

    committed = json.loads(COMMITTED_ASSESSMENT.read_text(encoding="utf-8"))
    assessor.assert_gate_evidence_consistent(committed)


def _tampered(mutate) -> dict:
    committed = json.loads(COMMITTED_ASSESSMENT.read_text(encoding="utf-8"))
    mutate(committed)
    return committed


def test_flipping_the_gate_flag_in_the_committed_file_is_rejected():
    def mutate(doc):
        doc["byte_only_gate_evidence"]["passed"] = False

    with pytest.raises(assessor.BoundaryAssessmentError):
        assessor.assert_gate_evidence_consistent(_tampered(mutate))


def test_a_receipt_digest_that_does_not_match_the_named_file_is_rejected():
    def mutate(doc):
        doc["byte_only_gate_evidence"]["receipt_sha256"] = "0" * 64

    with pytest.raises(assessor.BoundaryAssessmentError) as exc:
        assessor.assert_gate_evidence_consistent(_tampered(mutate))
    assert "does not hash to the digest recorded" in str(exc.value)


def test_a_gate_evidence_block_naming_a_missing_receipt_is_rejected():
    def mutate(doc):
        doc["byte_only_gate_evidence"]["receipt_path"] = "docs/no_such_receipt.json"

    with pytest.raises(assessor.BoundaryAssessmentError) as exc:
        assessor.assert_gate_evidence_consistent(_tampered(mutate))
    assert "does not exist" in str(exc.value)


def test_a_gate_evidence_block_naming_the_wrong_execution_is_rejected():
    def mutate(doc):
        doc["byte_only_gate_evidence"]["platform_attested_execution"] = "other-run"

    with pytest.raises(assessor.BoundaryAssessmentError) as exc:
        assessor.assert_gate_evidence_consistent(_tampered(mutate))
    assert "platform-attested execution" in str(exc.value)


def test_a_terminal_state_that_does_not_follow_from_the_verdict_is_rejected():
    def mutate(doc):
        doc["terminal_state"] = "READY_FOR_SEPARATELY_AUTHORISED_PRIVATE_REVIEW"

    with pytest.raises(assessor.BoundaryAssessmentError):
        assessor.assert_gate_evidence_consistent(_tampered(mutate))


# --- E-07: the gate outcome is anchored to evidence the probe did not write --


def test_the_anchors_are_recomputed_from_committed_public_evidence():
    """E-07: every gate conjunct was the receipt agreeing with itself.

    The expected-evidence file is committed, its SHA-256 is pinned in the
    decision record, and the aggregate digest the receipt reports is a pure
    function of its contents. So it can be recomputed here, offline, without
    trusting the receipt at all -- and it is recomputed rather than hard-coded,
    so editing the evidence file cannot move the target to meet it.
    """

    anchors = assessor.derive_expected_anchors()
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert anchors["object_count"] == 12
    assert anchors["total_bytes"] == receipt["streaming"]["total_bytes_streamed"]
    assert (
        anchors["aggregate_digest"]
        == receipt["streaming"]["observed_aggregate_digest"]
    )


def test_a_receipt_whose_aggregate_digest_disagrees_with_the_evidence_fails():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt["streaming"]["observed_aggregate_digest"] = "0" * 64
    passed, failures = assessor.derive_gate_outcome(receipt)
    assert not passed
    assert any("observed_aggregate_digest" in failure for failure in failures)


def test_a_receipt_whose_byte_total_disagrees_with_the_evidence_fails():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt["streaming"]["total_bytes_streamed"] += 1
    passed, failures = assessor.derive_gate_outcome(receipt)
    assert not passed
    assert any("total_bytes_streamed" in failure for failure in failures)


def test_the_committed_receipt_still_satisfies_every_conjunct():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    passed, failures = assessor.derive_gate_outcome(receipt)
    assert passed, failures


# --- F-01: the receipt is bound to control-plane output it cannot author -----


def test_the_execution_is_bound_to_platform_recorded_output():
    """F-01: the receipt was a self-authored, unsigned self-report.

    Nothing signs it and nothing external corroborated it, yet the round's
    terminal state rested on it. This does not make the receipt's counters true
    -- no attestation can, since the platform does not observe what the program
    did with the bytes -- but it does bind the execution to a record the probe
    could not write: the control-plane execution list.
    """

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assessor.assert_execution_is_platform_attested(receipt)


def test_an_execution_name_absent_from_the_platform_inventory_is_rejected():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt["execution"]["aca_execution_name"] = "job-that-never-ran"
    with pytest.raises(assessor.PlatformAttestationError):
        assessor.assert_execution_is_platform_attested(receipt)


def test_an_image_digest_the_platform_did_not_record_is_rejected():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt["provenance"]["image_digest"] = "sha256:" + "e" * 64
    with pytest.raises(assessor.PlatformAttestationError):
        assessor.assert_execution_is_platform_attested(receipt)


def test_the_attestation_does_not_claim_to_verify_the_counters():
    # The distinction this docstring carries is the whole point of F-01. If it
    # were dropped, the attestation would read as corroboration of the safety
    # claims, which it is not: the platform records that a container ran, not
    # what it did with the bytes it read.
    doc = assessor.assert_execution_is_platform_attested.__doc__ or ""
    assert "does **not** establish" in doc
    assert "counters" in doc


def test_the_committed_inventory_agrees_with_the_job_executions_counter():
    # E-11. The inventory was committed to answer C-13, then bound to nothing:
    # the counter it justifies was never compared against it.
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    ledger = json.loads(
        (ROOT / "docs" / "phase1_2h_execution_access_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(inventory["executions"]) == ledger["live_counters"]["azure"][
        "job_executions"
    ]


# --- F-05: QUALIFIES is unreachable, and that is a property worth pinning ----


def test_qualifying_is_unreachable_from_the_current_evidence_schema():
    """F-05: ``QUALIFIES`` cannot be produced, and this makes that explicit.

    Eight of the thirteen frozen conditions have no evidence field that could
    satisfy them, so they are ``NOT_ASSESSABLE`` for any input this schema
    admits, and ``NOT_ASSESSABLE`` is not a pass. That is the correct behaviour
    -- an unprovisioned boundary must not be assessable as qualifying -- but it
    was an accident of the implementation rather than a stated property. A
    future round that adds evidence fields must see this test fail and decide
    deliberately, rather than discover that the verdict silently became
    reachable.
    """

    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assessment = assessor.build_assessment(
        evidence, gate_evidence=assessor.load_gate_evidence(RECEIPT)
    )
    statuses = [condition["verdict"] for condition in assessment["conditions"]]
    assert "PASS" not in statuses
    assert statuses.count("NOT_ASSESSABLE") == 8
    assert assessment["qualification_verdict"] == "DOES_NOT_QUALIFY"


def test_not_assessable_is_never_counted_as_a_pass():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assessment = assessor.build_assessment(
        evidence, gate_evidence=assessor.load_gate_evidence(RECEIPT)
    )
    assert assessment["summary"]["passed"] == 0
    assert assessment["summary"]["not_assessable"] == 8


def test_f11_platform_attestation_is_described_as_an_unsigned_transcript():
    """Audit F (F-11): the check claimed the platform agreed the run happened.

    ``assert_execution_is_platform_attested`` reads
    ``docs/phase1_2h_r1_job_execution_inventory.json``, which is committed JSON
    an operator transcribed from an ``az`` command. Nothing signs it and nothing
    binds it to Azure, so an operator who can edit the receipt can edit it in
    the same commit and the check still holds. What it buys is independence of
    *authorship* --- two consistent forgeries instead of one --- not attestation.

    This test fixes the wording, because the wording is the claim.
    """
    doc = assessor.assert_execution_is_platform_attested.__doc__ or ""
    assert "unsigned committed transcript" in doc
    assert "Genuine attestation would require a signed platform artifact" in doc
    assert "which this round did not obtain and does not claim" in doc
    # The overbroad phrasing must not return.
    assert "the platform agrees" not in doc
    assert "Azure's own execution list" not in doc

    source = Path(assessor.__file__).read_text(encoding="utf-8")
    constant_comment = source[: source.index("JOB_EXECUTION_INVENTORY = ")]
    assert "not attestation" in constant_comment
    assert "Nothing signs it" in constant_comment


def test_f12_the_not_assessable_reason_cites_the_input_it_rests_on():
    """Audit F (F-12): the eight reasons appealed to the wrong file's silence.

    The reason named "the execution inventory this assessor reads". That
    inventory lists runs of the access-gate job; a review backend would never
    appear in it under any circumstances, so its silence supported nothing.
    Backend facts come from the review-boundary evidence bundle --- which does
    not fall silent. It lists a candidate endpoint and reports it as
    non-qualifying, which is a different and stronger reading than absence.
    """
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    results = assessor.assess(evidence)
    not_assessable = [
        entry for entry in results.values() if entry["verdict"] == "NOT_ASSESSABLE"
    ]
    assert len(not_assessable) == 8

    for entry in not_assessable:
        basis = entry["basis"]
        assert "review-boundary evidence bundle" in basis
        assert "execution inventory" not in basis
        # The candidate is reported as non-qualifying, not as absent.
        assert "the one candidate listed" in basis
        assert "public network access enabled" in basis
        # The bundle's provenance is disclosed where the reading is made.
        assert "unsigned operator transcript" in basis
        assert "not proof none exists" in basis

    # The bundle really does list the candidate the reason describes, so the
    # reason is not merely well-phrased.
    candidates = evidence["candidate_reviewer_endpoints"]
    assert candidates
    assert all(c.get("public_network_access") == "Enabled" for c in candidates)
    assert all(int(c.get("private_endpoint_count", 0)) == 0 for c in candidates)
    assert all(c.get("in_project_resource_group") is False for c in candidates)


def test_f12_the_schema_scopes_not_assessable_to_the_assessed_inputs():
    """The schema said the review design "does not exist", unconditionally.

    That is a claim about the world made by a document that reads two committed
    JSON files. It is now scoped to what those files show.
    """
    schema = json.loads(
        (ROOT / "docs" / "phase1_2h_r1_review_boundary.schema.json").read_text(
            encoding="utf-8"
        )
    )
    verdict = schema["properties"]["conditions"]["items"]["properties"]["verdict"]
    description = verdict["description"]
    assert "NOT_ASSESSABLE is not a pass" in description
    assert "has not been provisioned and evidenced to this assessor" in description
    assert "is not a claim that no such design exists anywhere" in description
    assert "a review design that does not exist" not in description
