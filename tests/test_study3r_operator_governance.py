"""Tests for the Study 3 draft-v0.7 terminal decision and the Study 3R charter.

These tests enforce the operator-governance state produced under
``studies/study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md``.

They deliberately do two things the committed independent-review tests cannot:

1. they assert the terminal, non-executable status of draft-v0.7 and the
   clean-room authorization of Study 3R against restrictive schemas;
2. they re-establish, at the *governance* head, the substantive property that
   ``tests/test_study3_v0_7_focused_review.py::test_the_review_changed_no_reviewed_or_historical_path``
   asserted only at the *review* head.

That review test is an independent-review artifact and is not editable under this
authority. Its assertion compares ``git diff --name-only <reviewed> HEAD`` with
the review's own path set, so it necessarily expires the moment any authorized
commit is added after the review head. The expiry is a scope condition, not a
protected-byte violation, and ``test_governance_changed_no_reviewed_candidate_or_protected_path``
below proves the underlying guarantee still holds.

Nothing here modifies any reviewed, historical or independent-review artifact.
"""

from __future__ import annotations

import json
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STUDY3 = ROOT / "studies" / "study3"
STUDY3R = ROOT / "studies" / "study3r"
REVIEWS = STUDY3 / "reviews"

REVIEWED_COMMIT = "459d002442641039196ac3880d47a45a3b79a4c8"
REVIEW_HEAD = "a08ec1462f023da49247cac0756b7af5f32ba75a"

DECISION_JSON = REVIEWS / "v0_7_operator_terminal_decision.json"
DECISION_SCHEMA = REVIEWS / "v0_7_operator_terminal_decision.schema.json"
DECISION_MD = REVIEWS / "v0_7_operator_terminal_decision.md"
RECONCILE_JSON = REVIEWS / "v0_7_review_head_test_count_reconciliation.json"
RECONCILE_SCHEMA = REVIEWS / "v0_7_review_head_test_count_reconciliation.schema.json"
RECONCILE_MD = REVIEWS / "v0_7_review_head_test_count_reconciliation.md"
CHARTER_JSON = STUDY3R / "study3r_charter.json"
CHARTER_SCHEMA = STUDY3R / "study3r_charter.schema.json"
CHARTER_MD = STUDY3R / "CHARTER.md"
AUTHORITY = STUDY3 / "prompts" / \
    "study3_v0_7_terminal_decision_and_study3r_successor_authority.md"

# Paths the governance session is permitted to touch. Everything else that
# existed at the reviewed commit must be byte-identical.
GOVERNANCE_ADDED = {
    "studies/study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md",
    "studies/study3/reviews/v0_7_operator_terminal_decision.md",
    "studies/study3/reviews/v0_7_operator_terminal_decision.json",
    "studies/study3/reviews/v0_7_operator_terminal_decision.schema.json",
    "studies/study3/reviews/v0_7_review_head_test_count_reconciliation.md",
    "studies/study3/reviews/v0_7_review_head_test_count_reconciliation.json",
    "studies/study3/reviews/v0_7_review_head_test_count_reconciliation.schema.json",
    "studies/study3r/README.md",
    "studies/study3r/CHARTER.md",
    "studies/study3r/study3r_charter.json",
    "studies/study3r/study3r_charter.schema.json",
    "tests/test_study3r_operator_governance.py",
}
GOVERNANCE_MODIFIED = {"studies/study3/README.md"}

# The single Study 3R protocol-authoring session authorized by
# ``studies/study3r/CHARTER.md`` runs under
# ``studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md``. It
# writes only inside the Study 3R namespace declared by the charter
# (``charter["study_identity"]["namespace"] == "studies/study3r/"``), plus the
# one protocol test module its authority names by path, plus the line-ending
# attributes that keep that bundle reproducible on every host.
#
# The two scope assertions below were written at the governance head and would
# otherwise expire the moment that authorized session added a commit — the same
# scope-expiry that retired
# ``tests/test_study3_v0_7_focused_review.py::test_the_review_changed_no_reviewed_or_historical_path``.
# Extending them here keeps their substantive guarantee intact: no reviewed,
# rejected-candidate, independent-review or protected historical byte may move,
# and nothing outside the Study 3R namespace may be added. Every protected-blob
# assertion in this module is unchanged.
AUTHORING_NAMESPACE = "studies/study3r/"
AUTHORING_ADDED = {"tests/test_study3r_protocol_v1.py"}
AUTHORING_MODIFIED = {
    ".gitattributes",
    "studies/study3r/README.md",
    "tests/test_study3r_operator_governance.py",
}

# The v0.7 candidate bundle, retained byte-exactly as rejected-candidate history.
REJECTED_CANDIDATE_PATHS = (
    "studies/study3/protocol/interface_calibration_protocol_draft_v0_7.json",
    "studies/study3/protocol/interface_calibration_protocol_draft_v0_7.md",
    "studies/study3/protocol/interface_calibration_protocol_draft_v0_7.schema.json",
    "studies/study3/protocol/interface_calibration_rendering_registry_v0_7.json",
    "studies/study3/protocol/interface_calibration_rendering_registry_v0_7.schema.json",
    "studies/study3/protocol/interface_calibration_protocol_current.json",
    "studies/study3/protocol/interface_calibration_protocol_current.schema.json",
    "studies/study3/analysis/v0_7_protocol_build.py",
    "tests/test_study3_v0_7_protocol.py",
    "studies/study3/reviews/v0_7_operator_amendment.json",
    "studies/study3/reviews/v0_7_operator_amendment.md",
    "studies/study3/reviews/v0_7_operator_amendment.schema.json",
)

# Independent-review artifacts. Immutable under this authority.
REVIEW_ARTIFACTS = (
    "studies/study3/reviews/v0_7_single_focused_methods_review.md",
    "studies/study3/reviews/v0_7_single_focused_methods_review.json",
    "studies/study3/reviews/v0_7_single_focused_methods_review.schema.json",
    "studies/study3/analysis/independent_methods_recalculation_v0_7.py",
    "studies/study3/analysis/independent_methods_recalculation_tables_v0_7.json",
    "studies/study3/methods_review_receipt_v0_7.json",
    "tests/test_study3_v0_7_focused_review.py",
    "studies/study3/prompts/study3_v0_7_single_focused_methods_review_authority.md",
)

# Historical protected bytes.
PROTECTED_HISTORICAL = (
    "studies/study3/protocol/interface_calibration_protocol_draft.json",
    "studies/study3/protocol/interface_calibration_protocol_draft.md",
    "studies/study3/protocol/interface_calibration_protocol.schema.json",
    "studies/study3/pilot/p0/corpus/p0_corpus_manifest.json",
    "studies/study3/pilot/p0/p0_freeze_corpus.py",
    "tests/test_study3_p0_feasibility_pilot.py",
    "paper/evidence_ledger.csv",
)


def _json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _git(*args):
    return subprocess.run(["git", "--no-pager", *args], cwd=str(ROOT),
                          capture_output=True, text=True, check=True).stdout


@pytest.fixture(scope="module")
def decision():
    return _json(DECISION_JSON)


@pytest.fixture(scope="module")
def charter():
    return _json(CHARTER_JSON)


@pytest.fixture(scope="module")
def reconciliation():
    return _json(RECONCILE_JSON)


# ---------------------------------------------------------------------------
# 1. Schema conformance
# ---------------------------------------------------------------------------


def test_the_terminal_decision_validates_against_its_schema(decision):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(decision, _json(DECISION_SCHEMA))


def test_the_charter_validates_against_its_schema(charter):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(charter, _json(CHARTER_SCHEMA))


def test_the_reconciliation_validates_against_its_schema(reconciliation):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(reconciliation, _json(RECONCILE_SCHEMA))


@pytest.mark.parametrize("path", [DECISION_MD, CHARTER_MD, RECONCILE_MD,
                                  STUDY3R / "README.md"])
def test_every_governance_markdown_exists_and_is_lf_only(path):
    payload = path.read_bytes()
    assert payload, path
    assert b"\r" not in payload, path
    assert payload.endswith(b"\n"), path


# ---------------------------------------------------------------------------
# 2. The terminal decision
# ---------------------------------------------------------------------------


def test_draft_v0_7_is_rejected_terminal_and_non_executable(decision):
    assert decision["decision"] == "STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION"
    status = decision["draft_v0_7_status"]
    assert status["failed_its_single_allowed_independent_focused_review"] is True
    assert status["no_finding_is_converted_into_a_limitation"] is True
    for key in ("frozen", "selected", "executable", "amendable"):
        assert status[key] is False, key


def test_no_incremental_successor_may_be_automatically_drafted(decision):
    prohibitions = decision["prohibitions"]
    assert prohibitions["v0_7_may_be_repaired"] is False
    assert prohibitions["v0_7_1_may_be_automatically_drafted"] is False
    assert prohibitions["v0_8_may_be_automatically_drafted"] is False
    assert prohibitions["incremental_carry_forward_repair_permitted"] is False


def test_the_decision_adopts_the_independent_review_verdict_verbatim(decision):
    assessment = decision["governing_assessment"]
    assert assessment["reviewed_commit"] == REVIEWED_COMMIT
    assert assessment["review_head_commit"] == REVIEW_HEAD
    assert assessment["review_disposition"] == \
        "STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED"
    assert assessment["accepted_as_governing"] is True
    review = _json(ROOT / assessment["review_json"])
    assert assessment["severity_counts"] == review["severity_counts"]
    assert assessment["review_disposition"] == review["verdict"]


def test_the_old_current_pointer_is_not_an_active_project_protocol(decision):
    pointer = decision["old_current_pointer"]
    assert pointer["path"] == \
        "studies/study3/protocol/interface_calibration_protocol_current.json"
    assert pointer["is_an_active_project_protocol"] is False
    assert pointer["is_an_internal_pointer_of_the_rejected_candidate"] is True
    assert pointer["prospective_readers_must_not_resolve_it"] is True


def test_the_rejected_candidate_bundle_is_retained_byte_exactly(decision):
    import hashlib
    retained = decision["retained_rejected_candidate_history"]
    assert retained["status"] == "REJECTED_CANDIDATE_HISTORY_NOT_AN_ACTIVE_PROTOCOL"
    assert retained["immutable"] is True
    assert retained["bytes_changed_by_this_decision"] == 0
    assert set(retained["artifacts"]) == set(REJECTED_CANDIDATE_PATHS)
    for relative, recorded in retained["artifacts"].items():
        payload = (ROOT / relative).read_bytes()
        assert len(payload) == recorded["bytes"], relative
        assert hashlib.sha256(payload).hexdigest() == recorded["sha256"], relative


def test_the_governance_boundary_counters_are_all_zero(decision):
    boundary = decision["boundary"]
    assert boundary["formal_execution_authorized"] is False
    assert boundary["evidence_ledger_tail"] == "EV-0016"
    assert boundary["no_scientific_evidence_was_produced"] is True
    assert boundary["research_question_answered"] is False
    counters = boundary["prohibited_operation_counters"]
    assert counters
    assert all(value == 0 for value in counters.values())


def test_the_evidence_ledger_still_ends_at_ev_0016():
    rows = (ROOT / "paper" / "evidence_ledger.csv").read_text(
        encoding="utf-8").splitlines()
    assert rows[-1].startswith("EV-0016,")


# ---------------------------------------------------------------------------
# 3. The Study 3 README terminal routing banner
# ---------------------------------------------------------------------------


def test_the_study3_readme_routes_to_the_terminal_decision_first():
    text = (STUDY3 / "README.md").read_text(encoding="utf-8")
    banner = text.split("\n\n")[1]
    assert "TERMINAL ROUTING" in banner
    assert "STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION" in banner
    assert "reviews/v0_7_operator_terminal_decision.md" in banner
    assert "REJECTED, NON-EXECUTABLE" in banner


def test_the_readme_labels_every_v0_7_artifact_as_a_rejected_candidate():
    text = (STUDY3 / "README.md").read_text(encoding="utf-8")
    banner = text.split("\n\n")[1]
    assert "REJECTED_CANDIDATE_HISTORY_NOT_AN_ACTIVE_PROTOCOL" in banner
    for stem in ("interface_calibration_protocol_draft_v0_7.json",
                 "interface_calibration_rendering_registry_v0_7.json",
                 "interface_calibration_protocol_current.json",
                 "v0_7_protocol_build.py",
                 "test_study3_v0_7_protocol.py"):
        assert stem in banner, stem
    assert "There is no active Study 3 interface-calibration protocol" in banner
    assert "must not resolve it" in banner


def test_the_readme_no_longer_routes_prospective_readers_to_v0_7():
    text = (STUDY3 / "README.md").read_text(encoding="utf-8")
    banner = text.split("\n\n")[1]
    assert "Active protocol routing" not in banner
    assert "The active normative protocol is" not in banner
    assert "study3r" in banner


# ---------------------------------------------------------------------------
# 4. The Study 3R charter
# ---------------------------------------------------------------------------


def test_study3r_is_authorized_and_awaiting_one_authoring_session(charter,
                                                                 decision):
    expected = "STUDY3R_CLEAN_ROOM_PROTOCOL_AUTHORIZED_AWAITING_SINGLE_AUTHORING_SESSION"
    assert charter["state"] == expected
    assert decision["successor"]["state"] == expected
    assert decision["successor"]["authorized"] is True
    assert decision["successor"]["protocol_authored_in_this_session"] is False


def test_study3r_is_a_clean_room_successor_not_an_incremental_version(charter,
                                                                     decision):
    assert charter["scope"]["is_v0_8"] is False
    assert charter["scope"]["is_a_copy_on_write_continuation"] is False
    assert decision["successor"]["is_v0_8"] is False
    assert decision["successor"][
        "is_a_copy_on_write_continuation_of_the_legacy_protocol"] is False
    assert charter["study_identity"]["namespace"] == "studies/study3r/"
    assert charter["validation_requirements"][
        "legacy_forty_key_protocol_structure_carried_forward"] is False


def test_the_charter_freezes_exactly_sixteen_decisions(charter):
    decisions = charter["frozen_project_decisions"]
    assert len(decisions) == 16
    ids = [d["id"] for d in decisions]
    assert ids == ["S3R-D%02d" % n for n in range(1, 17)]
    assert len(set(ids)) == 16


def test_the_rp_b_ladder_is_fixed_with_l_equal_to_three(charter):
    ladder = charter["rp_b_ladder"]
    assert ladder["membership"] == [
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    ]
    assert ladder["L"] == 3 == len(ladder["membership"])
    assert ladder["membership_is_fixed"] is True
    assert ladder["order_is_fixed"] is True
    assert ladder["ordering_rule"] == "parameter count ascending"
    assert ladder["fallback_candidate"] is None
    assert ladder["post_result_expansion_permitted"] is False
    assert ladder["immutable_revisions_sealed_before_protocol_freeze"] is True
    assert charter["q0"]["multiplicity_correction_over"] == \
        "the full registered L = 3"


def test_e0_is_primary_and_d0_is_never_an_rp_b_gate(charter):
    assert charter["estimands"]["E0"]["id"] == \
        "E0_zero_generated_reasoning_token_expressed_competence"
    assert charter["estimands"]["E0"]["role"] == "primary_headline"
    assert charter["estimands"]["D0"]["role"] == "conditional_diagnostic_only"
    assert charter["estimands"]["D0"]["is_ever_an_rp_b_gate"] is False
    assert charter["q0"]["primary_gate"] == charter["estimands"]["E0"]["id"]


def test_both_wrapper_arms_must_enter_the_census_and_multiplicity(charter):
    wrapper = charter["wrapper_qualification"]
    assert wrapper["gate_kind"] == "joint_adequacy"
    assert wrapper["arms"] == 2
    assert wrapper["both_arms_in_the_atomic_cell_census"] is True
    assert wrapper["both_arms_in_the_multiplicity_calculation"] is True
    assert wrapper["m_max_43_may_be_reused_without_independent_rederivation"] \
        is False
    assert len(wrapper["must_freeze_exactly"]) >= 6


def test_the_universal_max_new_tokens_three_is_not_inherited(charter):
    contract = charter["e0_surface_contract"]
    assert contract["is_checkpoint_revision_specific"] is True
    assert contract["universal_max_new_tokens_3_is_inherited"] is False
    assert "longest frozen legal answer surface" in \
        contract["max_new_tokens_derivation"]
    tokenizer = charter["tokenizer_functional_inequality"]
    assert tokenizer["creates_a_separate_isomorphic_reinstantiation_stratum"] is True
    assert tokenizer["may_be_pooled_as_the_same_frozen_interface"] is False


def test_the_negative_control_must_register_every_executable_component(charter):
    control = charter["negative_control"]
    assert control[
        "must_be_executable_one_sided_upper_bound_or_equivalence_design"] is True
    assert set(control["must_register"]) == {
        "unit", "chance level", "margin", "sample size", "alpha",
        "exact construction", "multiplicity family"}


def test_the_cot_ceiling_is_a_bounded_precondition_not_a_selector(charter):
    ceiling = charter["generated_cot_ceiling"]
    assert ceiling["is_a_per_checkpoint_execution_precondition"] is True
    assert ceiling["is_an_interface_selector"] is False
    assert ceiling["k"] == 1
    assert "total resource bound" in ceiling["must_freeze"]


def test_mechanism_work_is_out_of_scope_and_unauthorized(charter):
    out = charter["out_of_scope"]
    assert out["rp_m"] is False
    assert out["activation_patching"] is False
    assert out["mechanism_claims"] is False
    assert out["authorized_now"] is False
    assert out["may_be_considered_later_as"].startswith("Study 3M")
    assert charter["scope"]["covers"] == \
        "behavioral and interface qualification only"


def test_validation_must_include_coordinated_generator_mutation_tests(charter):
    requirements = charter["validation_requirements"]
    assert requirements["every_decision_bearing_schema_field_must_be_constrained"] \
        is True
    assert requirements["coordinated_generator_mutation_tests_required"] is True
    assert requirements["artifact_versus_generator_byte_equality_is_sufficient"] \
        is False
    assert len(requirements["written_cleanly_from_scratch"]) >= 6


def test_study3r_receives_one_authoring_session_and_one_review(charter):
    authorization = charter["authorization"]
    assert authorization["authoring_sessions_allowed"] == 1
    assert authorization["independent_focused_reviews_allowed"] == 1
    assert authorization["terminates_on_any_blocking_review_finding"] is True
    assert authorization["automatic_amendment_after_a_blocking_review_finding"] \
        is False
    assert authorization["predecessor_decision"] == \
        "STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION"


def test_the_charter_contains_no_protocol_and_no_execution_authorization(charter):
    boundary = charter["charter_boundary"]
    assert all(value is False for value in boundary.values())
    counters = charter["zero_operation_boundary"]
    assert len(counters) >= 10
    assert all(value == 0 for value in counters.values())


# ---------------------------------------------------------------------------
# 5. Provenance reconciliation
# ---------------------------------------------------------------------------


def test_the_reconciliation_quotes_both_counts_against_their_commits(
        reconciliation):
    counts = reconciliation["counts"]
    assert counts["reviewed_target"]["commit"] == REVIEWED_COMMIT
    assert counts["reviewed_target"]["verbatim"] == \
        "7 failed, 4,926 passed, 16 skipped"
    assert counts["reviewed_target"]["label_in_the_committed_artifacts"] == \
        "review_head_result"
    assert counts["reviewed_target"][
        "label_is_imprecise_and_is_not_edited_here"] is True
    assert counts["review_head"]["commit"] == REVIEW_HEAD
    assert counts["review_head"]["verbatim"] == \
        "7 failed, 4,958 passed, 16 skipped"
    assert counts["review_head"]["passed"] - counts["reviewed_target"]["passed"] \
        == 32


def test_the_thirty_two_test_difference_is_fully_accounted_for(reconciliation):
    accounting = reconciliation["accounting"]
    assert accounting["total_collected_reviewed_target"] == 4949
    assert accounting["total_collected_review_head_disclosed"] == 4981
    assert accounting["total_collected_review_head_rerun"] == 4981
    assert accounting["delta_total_collected"] == 32
    assert accounting["new_test_module"] == \
        "tests/test_study3_v0_7_focused_review.py"
    assert accounting["new_test_module_added_in_commit"] == REVIEW_HEAD
    assert accounting["new_test_module_collected_count"] == 32
    assert accounting["other_modules_added_removed_or_reparametrized"] == 0
    assert accounting["residual_unexplained_tests"] == 0
    assert accounting["difference_is_fully_accounted_for"] is True
    assert reconciliation["reconciliation_state"] == \
        "STUDY3_V0_7_REVIEW_HEAD_TEST_COUNT_RECONCILED"


def test_the_quoted_and_rerun_totals_are_internally_consistent(reconciliation):
    for key in ("reviewed_target", "review_head"):
        row = reconciliation["counts"][key]
        assert row["failed"] + row["passed"] + row["skipped"] == \
            row["total_collected"], key
    rerun = reconciliation["independent_rerun"]
    assert rerun["failed"] + rerun["passed"] + rerun["skipped"] == \
        rerun["total_collected"]
    assert rerun["total_collected"] == \
        reconciliation["counts"]["review_head"]["total_collected"]
    assert rerun["total_collected_matches_the_terminal_disclosure"] is True
    assert rerun["pass_fail_split_matches_the_terminal_disclosure"] is False
    assert reconciliation["counts"]["review_head"]["total_collected"] \
        - reconciliation["counts"]["reviewed_target"]["total_collected"] == 32


def test_the_extra_full_suite_failure_is_disclosed_as_an_unrelated_flake(
        reconciliation):
    flake = reconciliation["unstable_test_disclosure"]
    assert flake["node_id"] == \
        "tests/test_study2_stage_bd.py::test_pack_writes_the_core_manifest_last"
    assert flake["belongs_to_study_3"] is False
    assert flake["observed_in_the_full_suite_rerun"] == "failed"
    assert flake["result_in_isolation"] == "passed"
    assert flake["result_in_its_own_module"] == "passed"
    assert flake["affects_the_total_collected_count"] is False
    assert flake["affects_the_v0_7_verdict"] is False
    assert flake["repaired_by_this_session"] is False
    assert "st_mtime_ns" in flake["instability_mechanism"]
    assert len(flake["evidence"]) >= 3
    standing = reconciliation["standing_failures"]
    assert len(standing["node_ids"]) == 7
    assert flake["node_id"] not in standing["node_ids"]
    assert set(standing["node_ids"]) < set(
        reconciliation["independent_rerun"]["failing_node_ids"])
    assert standing["new_failures_introduced_between_the_two_commits"] == 0


def test_the_reconciliation_does_not_revise_the_methods_verdict(reconciliation):
    assert reconciliation["revises_the_methods_verdict"] is False
    assert reconciliation["review_artifacts_modified"] == 0
    scope = reconciliation["scope"]
    assert scope["is_a_provenance_reconciliation"] is True
    assert scope["is_a_revision_of_the_methods_verdict"] is False
    assert scope["governing_verdict_unchanged"] == \
        "STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED"
    assert scope["severity_counts_unchanged"] == {"BLOCKING": 12, "MAJOR": 3,
                                                  "MINOR": 2}


def test_the_new_review_module_really_collects_thirty_two_tests():
    import sys
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "tests/test_study3_v0_7_focused_review.py"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    collected = [line for line in completed.stdout.splitlines()
                 if "::" in line and line.startswith("tests/")]
    assert len(collected) == 32, completed.stdout


# ---------------------------------------------------------------------------
# 6. Protected bytes at the governance head
# ---------------------------------------------------------------------------


def test_governance_changed_no_reviewed_candidate_or_protected_path():
    """The substantive guarantee the expired review-scope test asserted.

    ``tests/test_study3_v0_7_focused_review.py::test_the_review_changed_no_reviewed_or_historical_path``
    compares the reviewed commit against ``HEAD``, so it holds only while HEAD is
    the review head. It is an independent-review artifact and is not editable
    under this authority, so it necessarily fails once an authorized governance
    commit exists. This test carries the same guarantee forward.
    """
    changed = {line.strip() for line
               in _git("diff", "--name-only", REVIEWED_COMMIT, "HEAD").splitlines()
               if line.strip()}
    review_added = {
        "studies/study3/analysis/independent_methods_recalculation_tables_v0_7.json",
        "studies/study3/analysis/independent_methods_recalculation_v0_7.py",
        "studies/study3/methods_review_receipt_v0_7.json",
        "studies/study3/prompts/study3_v0_7_single_focused_methods_review_authority.md",
        "studies/study3/reviews/v0_7_single_focused_methods_review.json",
        "studies/study3/reviews/v0_7_single_focused_methods_review.md",
        "studies/study3/reviews/v0_7_single_focused_methods_review.schema.json",
        "tests/test_study3_v0_7_focused_review.py",
    }
    permitted = review_added | GOVERNANCE_ADDED | GOVERNANCE_MODIFIED \
        | AUTHORING_ADDED | AUTHORING_MODIFIED
    unexpected = {path for path in changed
                  if path not in permitted
                  and not path.startswith(AUTHORING_NAMESPACE)}
    assert unexpected == set(), sorted(unexpected)


@pytest.mark.parametrize("relative", REJECTED_CANDIDATE_PATHS + REVIEW_ARTIFACTS
                         + PROTECTED_HISTORICAL)
def test_every_protected_blob_is_identical_to_the_review_head(relative):
    """No reviewed, historical or independent-review byte moved after a08ec146."""
    at_head = _git("rev-parse", "%s:%s" % (REVIEW_HEAD, relative)).strip()
    now = _git("rev-parse", "HEAD:%s" % relative).strip()
    assert at_head == now, relative


def test_only_the_readme_was_modified_and_everything_else_was_added():
    statuses = {}
    for line in _git("diff", "--name-status", REVIEW_HEAD, "HEAD").splitlines():
        if not line.strip():
            continue
        code, path = line.split("\t", 1)
        statuses[path.strip()] = code.strip()
    modified = {p for p, c in statuses.items() if c != "A"}
    assert GOVERNANCE_MODIFIED <= modified, sorted(GOVERNANCE_MODIFIED - modified)
    assert modified <= GOVERNANCE_MODIFIED | AUTHORING_MODIFIED, sorted(
        modified - (GOVERNANCE_MODIFIED | AUTHORING_MODIFIED))
    added = {p for p, c in statuses.items() if c == "A"}
    unexpected = {p for p in added
                  if p not in GOVERNANCE_ADDED | AUTHORING_ADDED
                  and not p.startswith(AUTHORING_NAMESPACE)}
    assert unexpected == set(), sorted(unexpected)


def test_the_governance_history_is_linear_and_merge_free():
    commits = [line.strip() for line
               in _git("rev-list", "%s..HEAD" % REVIEWED_COMMIT).splitlines()
               if line.strip()]
    assert commits, "no governance commits found"
    merges = [line.strip() for line
              in _git("rev-list", "--merges", "%s..HEAD" % REVIEWED_COMMIT).splitlines()
              if line.strip()]
    assert merges == []
    assert _git("merge-base", REVIEWED_COMMIT, "HEAD").strip() == REVIEWED_COMMIT
    assert REVIEW_HEAD in commits


def test_the_governance_authority_bytes_match_the_recorded_identity(decision):
    import hashlib
    recorded = decision["authority"]
    payload = (ROOT / recorded["path"]).read_bytes()
    assert len(payload) == recorded["bytes"]
    assert hashlib.sha256(payload).hexdigest() == recorded["sha256"]
    assert b"\r" not in payload
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert recorded["parent_commit"] == REVIEW_HEAD
    assert recorded["published_alone_as_the_first_commit_after_the_review_head"] \
        is True
    listed = [line.strip() for line
              in _git("show", "--name-only", "--format=", recorded["commit"]
                      ).splitlines() if line.strip()]
    assert listed == [recorded["path"]]


def test_the_authority_file_is_the_one_this_session_executed():
    text = AUTHORITY.read_text(encoding="utf-8")
    assert "STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION" in text
    assert "STUDY3R_CLEAN_ROOM_PROTOCOL_AUTHORIZED_AWAITING_SINGLE_AUTHORING_SESSION" \
        in text
    assert REVIEW_HEAD[:8] in text and REVIEWED_COMMIT[:8] in text
