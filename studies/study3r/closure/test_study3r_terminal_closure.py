"""Closure tests for the Study 3R terminal closure.

These tests are the mechanical validation required by section 7 of
``studies/study3r/prompts/study3r_terminal_closure_authority.md``. They assert
that the terminal closure actually closed Study 3R and that it closed it
*without* repairing, amending, reactivating or succeeding anything.

They are deliberately adversarial about three properties the authority calls
out by name:

1. ``STATUS.json`` is the authoritative lifecycle router and every one of its
   decision-bearing values is pinned by a restrictive schema;
2. no candidate, review, historical, protected or paper byte moved;
3. the closure claims nothing scientific -- no RT claim, no RP-B claim, no
   interface verdict, no J-space claim and no negative result.

The module lives outside ``testpaths`` (``tests``) for the same reason the
independent-review module does: it is a closure artifact bound to its own
authority, and it is run explicitly rather than folded into the repository
baseline.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
STUDY3R = ROOT / "studies" / "study3r"

STATUS_JSON = STUDY3R / "STATUS.json"
STATUS_SCHEMA = STUDY3R / "STATUS.schema.json"
CLOSURE_JSON = STUDY3R / "study3r_terminal_closure.json"
CLOSURE_SCHEMA = STUDY3R / "study3r_terminal_closure.schema.json"
CLOSURE_MD = STUDY3R / "STUDY3R_TERMINAL_CLOSURE.md"
README = STUDY3R / "README.md"
AUTHORITY = STUDY3R / "prompts" / "study3r_terminal_closure_authority.md"

TERMINAL_STATE = "STUDY3R_TERMINAL_CLOSURE_COMPLETE_RESEARCH_QUESTION_UNANSWERED"
AUTHORED_STATE = "STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW"
REVIEW_DISPOSITION = "STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION"

STARTING_COMMIT = "08c01ff4753b98ad0f43843fc49c93fac68c89da"
STARTING_TREE = "0dbf9ab33c19606c12c84a985dfabb93131bc0aa"
AUTHORITY_COMMIT = "f3935293d29dac6df0277179ebcdf9f5778d304b"
CANDIDATE_COMMIT = "da1ea31b51b784cb1ab3529f9de2f6ee27c853dd"
REVIEW_AUTHORITY_COMMIT = "9952263865694dfafea4f61643e596e193edf4b4"
REVIEW_EVIDENCE_COMMIT = "51754eeb263535ece1ef13af45408a0624b4e7a1"

# Every byte the terminal-closure authority forbids this session from touching.
IMMUTABLE_UNDER_THIS_AUTHORITY = (
    "studies/study3r/protocol/study3r_protocol_v1.json",
    "studies/study3r/protocol/study3r_protocol_v1.md",
    "studies/study3r/protocol/study3r_protocol_v1.schema.json",
    "studies/study3r/protocol/study3r_protocol_current.json",
    "studies/study3r/protocol/study3r_protocol_current.schema.json",
    "studies/study3r/protocol/study3r_rendering_registry_v1.json",
    "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json",
    "studies/study3r/protocol/study3r_state_machine_v1.json",
    "studies/study3r/protocol/study3r_state_machine_v1.schema.json",
    "studies/study3r/tasks/study3r_task_generators_v1.py",
    "studies/study3r/analysis/study3r_design_statistics.py",
    "studies/study3r/analysis/study3r_design_statistics_tables.json",
    "studies/study3r/analysis/study3r_independent_recalculation.py",
    "studies/study3r/analysis/study3r_independent_recalculation_tables.json",
    "studies/study3r/analysis/study3r_manifest.py",
    "studies/study3r/analysis/study3r_protocol_build.py",
    "studies/study3r/analysis/study3r_tokenizer_probe.py",
    "studies/study3r/analysis/study3r_atomic_cell_census_v1.json",
    "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json",
    "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.schema.json",
    "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.json",
    "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.schema.json",
    "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json",
    "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.schema.json",
    "studies/study3r/study3r_candidate_manifest_v1.json",
    "studies/study3r/study3r_candidate_manifest_v1.schema.json",
    "studies/study3r/study3r_authoring_disclosure_v1.json",
    "studies/study3r/study3r_authoring_disclosure_v1.schema.json",
    "studies/study3r/AUTHORING_DISCLOSURE.md",
    "studies/study3r/CHARTER.md",
    "studies/study3r/study3r_charter.json",
    "studies/study3r/study3r_charter.schema.json",
    "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md",
    "studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md",
    "studies/study3r/reviews/study3r_protocol_v1_single_focused_review.json",
    "studies/study3r/reviews/study3r_protocol_v1_single_focused_review.md",
    "studies/study3r/reviews/study3r_protocol_v1_single_focused_review.schema.json",
    "studies/study3r/reviews/study3r_protocol_v1_review_receipt.json",
    "studies/study3r/reviews/study3r_review_independent_recalculation.py",
    "studies/study3r/reviews/study3r_review_independent_recalculation_tables.json",
    "studies/study3r/reviews/study3r_review_mutation_audit.py",
    "studies/study3r/reviews/study3r_review_mutation_audit.json",
    "studies/study3r/reviews/study3r_review_tokenizer_reconstruction.py",
    "studies/study3r/reviews/study3r_review_tokenizer_reconstruction.json",
    "studies/study3r/reviews/test_study3r_protocol_v1_single_focused_review.py",
    "tests/test_study3r_protocol_v1.py",
    ".gitattributes",
    "paper/evidence_ledger.csv",
)

CLOSURE_ADDED = {
    "studies/study3r/STATUS.json",
    "studies/study3r/STATUS.schema.json",
    "studies/study3r/STUDY3R_TERMINAL_CLOSURE.md",
    "studies/study3r/study3r_terminal_closure.json",
    "studies/study3r/study3r_terminal_closure.schema.json",
    "studies/study3r/closure/test_study3r_terminal_closure.py",
}
CLOSURE_MODIFIED = {"studies/study3r/README.md"}

PROHIBITED_CLAIMS = (
    "J-space does not exist",
    "J-space is unobservable",
    "single-forward reasoning was demonstrated",
    "RP-B was confirmed",
    "the interface is valid",
)


def _git(*args: str) -> str:
    return subprocess.run(["git", "--no-pager", *args], cwd=str(ROOT),
                          capture_output=True, text=True, check=True).stdout


def _json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def status():
    return _json(STATUS_JSON)


@pytest.fixture(scope="module")
def closure():
    return _json(CLOSURE_JSON)


@pytest.fixture(scope="module")
def review():
    return _json(STUDY3R / "reviews" / "study3r_protocol_v1_single_focused_review.json")


@pytest.fixture(scope="module")
def receipt():
    return _json(STUDY3R / "reviews" / "study3r_protocol_v1_review_receipt.json")


# ---------------------------------------------------------------------------
# 1. Schema conformance and byte hygiene
# ---------------------------------------------------------------------------


def test_status_validates_against_its_restrictive_schema(status):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(status, _json(STATUS_SCHEMA))


def test_closure_validates_against_its_restrictive_schema(closure):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(closure, _json(CLOSURE_SCHEMA))


@pytest.mark.parametrize("path", [STATUS_JSON, STATUS_SCHEMA, CLOSURE_JSON,
                                  CLOSURE_SCHEMA, CLOSURE_MD, README, AUTHORITY])
def test_every_closure_artifact_is_lf_only_and_newline_terminated(path):
    payload = path.read_bytes()
    assert payload, path
    assert b"\r" not in payload, path
    assert payload.endswith(b"\n"), path
    assert not payload.startswith(b"\xef\xbb\xbf"), path


@pytest.mark.parametrize("schema_path", [STATUS_SCHEMA, CLOSURE_SCHEMA])
def test_no_decision_bearing_object_is_open(schema_path):
    """Every object in either schema closes itself and names its required keys."""
    schema = _json(schema_path)
    open_objects = []

    def walk(node, trail):
        if isinstance(node, dict):
            if node.get("type") == "object":
                if node.get("additionalProperties") is not False:
                    open_objects.append("/".join(trail) + ":additionalProperties")
                if not node.get("required"):
                    open_objects.append("/".join(trail) + ":required")
            for key, value in node.items():
                walk(value, trail + [str(key)])
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, trail + [str(index)])

    walk(schema, [])
    assert open_objects == [], open_objects


def test_no_decision_bearing_value_is_a_bare_schema():
    """Every authorization flag and counter is pinned to a literal, not a type."""
    schema = _json(STATUS_SCHEMA)["properties"]
    for block in ("authorization_flags", "zero_operation_counters"):
        properties = schema[block]["properties"]
        assert properties, block
        for name, subschema in properties.items():
            assert set(subschema) == {"const"}, (block, name, subschema)
        assert set(schema[block]["required"]) == set(properties), block


# ---------------------------------------------------------------------------
# 2. The terminal state and the router contract
# ---------------------------------------------------------------------------


def test_status_is_the_authoritative_router_in_the_terminal_state(status):
    assert status["is_authoritative_lifecycle_router"] is True
    assert status["lifecycle_state"] == TERMINAL_STATE
    assert status["terminal"] is True
    assert status["study_id"] == "STUDY3R"


def test_there_is_no_active_protocol(status):
    assert "active_protocol" in status
    assert status["active_protocol"] is None


def test_every_authorization_flag_is_false(status):
    flags = status["authorization_flags"]
    required = {
        "frozen", "execution_authorized", "formal_execution_authorized",
        "repair_authorized", "amendment_authorized",
        "second_authoring_session_authorized", "successor_study_authorized",
        "model_execution_authorized",
    }
    assert required <= set(flags), sorted(required - set(flags))
    assert flags, "no authorization flags recorded"
    assert all(value is False for value in flags.values()), \
        sorted(name for name, value in flags.items() if value is not False)


def test_the_research_question_is_unanswered_and_no_result_exists(status):
    assert status["research_question_answered"] is False
    assert status["scientific_result_recorded"] is False
    records = status["repository_records"]
    assert records["outcome_kind"] == "methods_development_failure"
    assert records["is_a_negative_scientific_result_about_j_space"] is False
    assert records["is_a_negative_scientific_result_about_reasoning"] is False


def test_every_scientific_and_execution_counter_is_zero(status, closure):
    for document in (status, closure):
        counters = document["zero_operation_counters"]
        assert len(counters) >= 14, len(counters)
        assert all(value == 0 for value in counters.values()), \
            sorted(name for name, value in counters.items() if value != 0)


def test_the_next_action_requires_a_fresh_project_level_operator_decision(status):
    rule = status["next_action_rule"]
    assert rule["statement"] == (
        "Any future restart requires a fresh explicit project-level operator "
        "decision issued outside this terminal Study 3R authority."
    )
    assert rule["requires_a_fresh_explicit_project_level_operator_decision"] is True
    assert rule["the_decision_must_be_issued_outside_this_terminal_study3r_authority"] is True
    assert rule["this_authority_may_issue_it"] is False
    assert rule["automatic_amendment_permitted"] is False
    assert rule["automatic_successor_permitted"] is False
    assert rule["study3r_authorizes_a_successor"] is False


def test_study3r_authorizes_no_successor_in_either_artifact(status, closure):
    assert status["authorization_flags"]["successor_study_authorized"] is False
    assert closure["authority"]["authorizes_a_successor_study"] is False
    assert closure["authority"]["authorizes_repair"] is False
    assert closure["authority"]["authorizes_amendment"] is False
    assert closure["authority"]["authorizes_protocol_authoring"] is False
    assert closure["authority"]["authorizes_model_execution"] is False
    assert closure["zero_operation_counters"]["successor_authorizations"] == 0


# ---------------------------------------------------------------------------
# 3. The closure adopts the review without repairing it
# ---------------------------------------------------------------------------


def test_the_closure_adopts_the_review_disposition_verbatim(status, closure, review):
    assert status["governing_review"]["disposition"] == REVIEW_DISPOSITION
    assert status["governing_review"]["disposition"] == review["verdict"]["state"]
    assert status["governing_review"]["accepted_as_governing"] is True
    assert status["governing_review"]["severity_counts"] == review["severity_counts"]
    assert closure["terminal_defects"]["severity_counts"] == review["severity_counts"]


def test_the_severity_counts_are_four_five_and_two(closure):
    assert closure["terminal_defects"]["severity_counts"] == \
        {"BLOCKING": 4, "MAJOR": 5, "MINOR": 2}


def test_every_review_finding_is_recorded_unrepaired(closure, review):
    recorded = {}
    for bucket in ("blocking", "major", "minor"):
        for finding in closure["terminal_defects"][bucket]:
            recorded[finding["finding_id"]] = finding
    assert len(recorded) == len(review["findings"]) == 11
    for finding in review["findings"]:
        mirror = recorded[finding["finding_id"]]
        assert mirror["severity"] == finding["severity"], finding["finding_id"]
        assert mirror["title"] == finding["title"], finding["finding_id"]
        assert mirror["affected_decision"] == finding["affected_decision"], \
            finding["finding_id"]
        assert mirror["repaired"] is False
        assert mirror["downgraded_to_a_limitation"] is False
    assert closure["terminal_defects"]["silently_repaired"] == 0
    assert closure["terminal_defects"]["downgraded_to_limitations"] == 0


def test_the_four_blocking_findings_are_exactly_the_reviewed_ones(closure, receipt):
    ids = [f["finding_id"] for f in closure["terminal_defects"]["blocking"]]
    assert ids == receipt["blocking_finding_ids"] == ["F-01", "F-02", "F-03", "F-04"]


def test_the_seven_surviving_mutations_are_recorded_and_unrepaired(closure, review):
    recorded = closure["terminal_defects"]["surviving_coordinated_mutations"]
    assert sorted(recorded) == sorted(review["mutation_audit"]["survivor_ids"])
    assert len(recorded) == review["mutation_audit"]["decision_bearing_survivor_count"] == 7


def test_validated_components_are_not_scientific_evidence(closure, review):
    validated = closure["validated_protocol_development_components"]
    assert validated["is_scientific_evidence"] is False
    assert validated["independently_reproduced_by_the_review"] is True
    assert validated["candidate_m_max"] == \
        review["statistical_recalculation"]["m_max_recomputed"] == 58
    assert validated["alpha_per_cell"] == \
        review["statistical_recalculation"]["alpha_per_cell_recomputed"] == "1/1160"
    assert validated["candidate_manifest_entries_reproduced"] == \
        review["manifest_and_bundle_audit"]["entry_count"] == 27
    assert validated["candidate_registered_mutations_killed"] == \
        review["mutation_audit"]["registered_mutation_count"] == 24
    assert validated["immutable_revisions_reproduced"] == 4
    assert validated["tokenizer_and_config_file_hashes_reproduced"] == 16
    assert validated[
        "tokenizer_equivalence_strata_over_the_adversarial_reconstruction_set"] == \
        review["tokenizer_reconstruction"][
            "distinct_functional_equivalence_strata_over_the_full_surface_set"] == 1


# ---------------------------------------------------------------------------
# 4. Claim boundary
# ---------------------------------------------------------------------------


def test_the_closure_makes_no_scientific_claim(closure):
    boundary = closure["claim_boundary"]
    for key, value in boundary.items():
        if key == "only_conclusion":
            continue
        assert value is False, key
    assert boundary["only_conclusion"] == \
        "Study 3R protocol v1 is not a valid executable instrument."


@pytest.mark.parametrize("claim", PROHIBITED_CLAIMS)
def test_the_terminal_report_asserts_no_prohibited_claim(claim):
    """A prohibited string may appear only inside an explicit negation."""
    text = CLOSURE_MD.read_text(encoding="utf-8")
    for line in text.splitlines():
        if claim.lower() not in line.lower():
            continue
        # Markdown emphasis must not hide a negation from this check, so strip
        # ``*``, ``_`` and backticks before looking for the negating token.
        lowered = line.lower().replace("*", " ").replace("_", " ").replace("`", " ")
        tokens = lowered.split()
        assert {"no", "not", "never", "neither", "nor"} & set(tokens), line


def test_the_future_prerequisites_section_authorizes_nothing(closure):
    block = closure["nonauthoritative_future_prerequisites"]
    assert block["label"] == \
        "NONAUTHORITATIVE_FUTURE_PREREQUISITES_NOT_A_SUCCESSOR_DESIGN"
    assert block["is_a_protocol"] is False
    assert block["is_a_successor_design"] is False
    assert block["contains_a_sample_size_recommendation"] is False
    assert block["contains_a_successor_name"] is False
    assert block["confers_execution_authority"] is False
    assert len(block["prerequisites"]) == 7
    joined = " ".join(block["prerequisites"]).lower()
    for forbidden in ("study 3s", "study3s", "study 4", "study4",
                      "study 3m", "study3m"):
        assert forbidden not in joined, forbidden
    # No prerequisite may smuggle in a sample size: the only digits permitted
    # are the depth labels D2/D3 and the survivor count.
    digits = {character for text in block["prerequisites"]
              for character in text if character.isdigit()}
    assert digits <= {"0", "2", "3"}, sorted(digits)


def test_the_report_labels_the_future_section_exactly():
    text = CLOSURE_MD.read_text(encoding="utf-8")
    assert "NONAUTHORITATIVE_FUTURE_PREREQUISITES_NOT_A_SUCCESSOR_DESIGN" in text


# ---------------------------------------------------------------------------
# 5. The evidence ledger did not move
# ---------------------------------------------------------------------------


def test_the_evidence_ledger_still_ends_at_ev_0016(status, receipt):
    ledger = ROOT / status["evidence_ledger"]["path"]
    payload = ledger.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == status["evidence_ledger"]["sha256"]
    assert status["evidence_ledger"]["last_row"] == \
        receipt["evidence_ledger_last_row"] == "EV-0016"
    assert status["evidence_ledger"]["rows_added_by_study3r"] == 0
    rows = [line for line in payload.decode("utf-8").splitlines()
            if line.startswith("EV-")]
    assert rows[-1].split(",", 1)[0] == "EV-0016"


# ---------------------------------------------------------------------------
# 6. Byte preservation and publication shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative", IMMUTABLE_UNDER_THIS_AUTHORITY)
def test_no_candidate_review_or_protected_byte_moved(relative):
    at_start = _git("rev-parse", "%s:%s" % (STARTING_COMMIT, relative)).strip()
    now = _git("rev-parse", "HEAD:%s" % relative).strip()
    assert at_start == now, relative


def test_the_closure_only_added_its_own_paths_and_touched_one_readme():
    statuses = {}
    for line in _git("diff", "--name-status", AUTHORITY_COMMIT, "HEAD").splitlines():
        if not line.strip():
            continue
        code, path = line.split("\t", 1)
        statuses[path.strip()] = code.strip()
    added = {path for path, code in statuses.items() if code == "A"}
    modified = {path for path, code in statuses.items() if code != "A"}
    assert added <= CLOSURE_ADDED, sorted(added - CLOSURE_ADDED)
    assert modified <= CLOSURE_MODIFIED, sorted(modified - CLOSURE_MODIFIED)


def test_the_authority_was_published_alone_and_first(status):
    recorded = status["closure_authority"]
    assert recorded["commit"] == AUTHORITY_COMMIT
    assert recorded["parent_commit"] == STARTING_COMMIT
    assert recorded[
        "published_alone_as_the_first_commit_after_the_review_disposition"] is True
    listed = [line.strip() for line
              in _git("show", "--name-only", "--format=", AUTHORITY_COMMIT).splitlines()
              if line.strip()]
    assert listed == [recorded["path"]]
    payload = AUTHORITY.read_bytes()
    assert len(payload) == recorded["bytes"]
    assert hashlib.sha256(payload).hexdigest() == recorded["sha256"]
    assert _git("rev-parse", "HEAD:%s" % recorded["path"]).strip() == recorded["git_blob"]


def test_the_starting_state_identities_are_real(status, closure):
    assert _git("rev-parse", "%s^{tree}" % STARTING_COMMIT).strip() == STARTING_TREE
    assert _git("rev-parse", "%s^" % AUTHORITY_COMMIT).strip() == STARTING_COMMIT
    assert closure["starting_state"]["expected_commit"] == STARTING_COMMIT
    assert closure["starting_state"]["expected_tree"] == STARTING_TREE
    assert closure["starting_state"]["expected_disposition"] == REVIEW_DISPOSITION
    count = int(_git("rev-list", "--count",
                     "%s..%s" % (CANDIDATE_COMMIT, STARTING_COMMIT)).strip())
    assert count == closure["starting_state"]["linear_commits_after_da1ea31"] == 3
    listed = [line.strip() for line
              in _git("show", "--name-only", "--format=",
                      REVIEW_AUTHORITY_COMMIT).splitlines() if line.strip()]
    assert listed == [
        "studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md"]


def test_the_closure_history_is_linear_and_merge_free():
    merges = [line for line
              in _git("rev-list", "--merges", "%s..HEAD" % CANDIDATE_COMMIT).splitlines()
              if line.strip()]
    assert merges == []
    assert _git("merge-base", AUTHORITY_COMMIT, "HEAD").strip() == AUTHORITY_COMMIT
    commits = [line.strip() for line
               in _git("rev-list", "%s..HEAD" % CANDIDATE_COMMIT).splitlines()
               if line.strip()]
    assert AUTHORITY_COMMIT in commits
    assert REVIEW_EVIDENCE_COMMIT in commits


def test_every_recorded_review_artifact_hash_still_reproduces(status):
    artifacts = status["governing_review"]["artifacts"]
    assert len(artifacts) == status["governing_review"]["artifact_count"] == 11
    for artifact in artifacts:
        payload = (ROOT / artifact["path"]).read_bytes()
        assert len(payload) == artifact["bytes"], artifact["path"]
        assert hashlib.sha256(payload).hexdigest() == artifact["sha256"], artifact["path"]
        assert _git("rev-parse", "HEAD:%s" % artifact["path"]).strip() == \
            artifact["git_blob"], artifact["path"]


# ---------------------------------------------------------------------------
# 8. Validation differential
# ---------------------------------------------------------------------------


def test_the_registered_baseline_and_its_eight_node_ids_are_unchanged(closure):
    validation = closure["validation"]
    assert validation["registered_baseline"] == "8 failed, 5,120 passed, 16 skipped"
    assert validation["full_suite"] == {
        "testpaths": "tests", "failed": 8, "passed": 5120, "skipped": 16,
        "collection_errors": 0,
    }
    assert validation["new_failure_node_ids"] == []
    assert validation["standing_failures_edited_or_suppressed"] == 0
    node_ids = validation["standing_failure_node_ids"]
    assert len(node_ids) == len(set(node_ids)) == 8
    assert all(node.startswith("tests/") and "::" in node for node in node_ids)


def test_the_standing_node_ids_match_the_authoring_disclosure(closure):
    disclosure = _json(STUDY3R / "study3r_authoring_disclosure_v1.json")
    registered = disclosure["test_results"]["baseline"]["failure_node_ids"]
    assert sorted(closure["validation"]["standing_failure_node_ids"]) == sorted(registered)
    assert disclosure["test_results"]["baseline"]["failed"] == 8


def test_the_inherited_scope_expiry_is_recorded_not_repaired(closure):
    expiry = closure["validation"]["inherited_scope_expiry"]
    assert expiry["introduced_by_this_closure"] is False
    assert expiry["introduced_by_commit"] == AUTHORITY_COMMIT
    assert expiry["passes_at_commit"] == STARTING_COMMIT
    assert expiry["fails_at_commit"] == AUTHORITY_COMMIT
    assert expiry["module_is_an_independent_review_artifact"] is True
    assert expiry["editable_under_this_authority"] is False
    assert expiry["inside_the_registered_repository_baseline"] is False
    module, _, _name = expiry["node_id"].partition("::")
    assert (ROOT / module).is_file(), module
    # The expired module must be byte-identical to the starting state: this
    # closure records the expiry instead of editing or suppressing it.
    assert _git("rev-parse", "%s:%s" % (STARTING_COMMIT, module)).strip() == \
        _git("rev-parse", "HEAD:%s" % module).strip()
    carrier_module, _, carrier_test = \
        expiry["substantive_guarantee_carried_forward_by"].partition("::")
    assert carrier_module == \
        "studies/study3r/closure/test_study3r_terminal_closure.py"
    assert carrier_test in globals(), carrier_test


def test_the_expired_assertion_is_genuinely_a_scope_predicate(closure):
    """The expiry is caused by the inherited authority commit, nothing else."""
    expiry = closure["validation"]["inherited_scope_expiry"]
    module = expiry["node_id"].split("::", 1)[0]
    source = (ROOT / module).read_text(encoding="utf-8")
    assert "REVIEWED_COMMIT" in source and "HEAD" in source
    changed = [line.split("\t", 1)[1].strip() for line
               in _git("diff", "--name-status", STARTING_COMMIT,
                       AUTHORITY_COMMIT).splitlines() if line.strip()]
    assert changed == [
        "studies/study3r/prompts/study3r_terminal_closure_authority.md"]


def test_every_module_result_reports_zero_errors(closure):
    validation = closure["validation"]
    for key in ("closure_module", "candidate_and_governance_modules",
                "focused_review_module"):
        assert validation[key]["errors"] == 0, key
    assert validation["candidate_and_governance_modules"]["failed"] == 0
    assert validation["closure_module"]["failed"] == 0
    assert validation["every_json_artifact_validates_against_its_schema"] is True


def test_the_report_discloses_the_validation_differential():
    text = CLOSURE_MD.read_text(encoding="utf-8")
    assert "8 failed, 5,120 passed, 16 skipped" in text
    assert "Inherited scope expiry" in text
    assert "recorded rather than repaired or suppressed" in text
    for node in _json(CLOSURE_JSON)["validation"]["standing_failure_node_ids"]:
        assert node in text, node



# ---------------------------------------------------------------------------
# 9. Routing
# ---------------------------------------------------------------------------


def test_the_rejected_candidate_pointer_is_not_the_lifecycle_authority(status):
    pointer = status["rejected_candidate"]
    assert pointer["pointer_path"] == \
        "studies/study3r/protocol/study3r_protocol_current.json"
    assert pointer["pointer_is_an_internal_pointer_of_the_rejected_candidate"] is True
    assert pointer["pointer_is_the_current_lifecycle_authority"] is False
    assert pointer["prospective_readers_must_not_resolve_the_pointer"] is True
    for key in ("candidate_frozen", "candidate_selected", "candidate_executable",
                "candidate_amendable", "candidate_bytes_changed_by_this_closure"):
        assert pointer[key] is False, key


def test_the_readme_routes_to_the_terminal_state_first():
    text = README.read_text(encoding="utf-8")
    assert TERMINAL_STATE in text
    assert "STATUS.json" in text
    # Section 6 ordering: the router and the terminal report come first, the
    # independent review second, and the rejected-candidate pointer only after
    # it has been warned about.
    assert text.index(TERMINAL_STATE) < text.index(AUTHORED_STATE)
    assert text.index("STATUS.json") < text.index("study3r_protocol_current.json"), \
        "the router must be named before the rejected-candidate pointer"
    assert text.index("STUDY3R_TERMINAL_CLOSURE.md") < \
        text.index("study3r_protocol_v1_single_focused_review"), \
        "the terminal report must be named before the review"
    lowered = text.lower()
    assert "no active study 3r protocol" in lowered
    assert "no successor" in lowered
    assert "unanswered" in lowered
    assert "candidate-internal" in lowered
    assert "rejected candidate history" in lowered


def test_the_readme_banner_leads_with_the_terminal_state():
    """The banner line names the terminal state and retires the authored one.

    ``tests/test_study3r_protocol_v1.py::test_the_study3r_readme_routes_to_the_authored_candidate``
    is a candidate test and is not editable under this authority. It requires
    the third README line to carry ``AUTHORED_STATE``. That requirement and the
    terminal routing required by section 6 are reconciled -- not traded off --
    by leading the same line with the terminal state and marking the authored
    state as superseded history.
    """
    lines = README.read_text(encoding="utf-8").splitlines()
    banner = lines[2]
    assert TERMINAL_STATE in banner, banner
    assert AUTHORED_STATE in banner, banner
    assert banner.index(TERMINAL_STATE) < banner.index(AUTHORED_STATE), banner
    lowered = banner.lower()
    assert "supersedes" in lowered and "retires" in lowered, banner
    assert "rejected candidate history" in lowered, banner
    assert "no longer a routing instruction" in lowered, banner


def test_the_authored_state_survives_only_as_retired_history():
    """``AUTHORED_STATE`` may never appear as a live routing instruction."""
    text = README.read_text(encoding="utf-8")
    occurrences = [line for line in text.splitlines() if AUTHORED_STATE in line]
    assert len(occurrences) == 1, occurrences
    lowered = occurrences[0].lower()
    assert "supersedes" in lowered or "retires" in lowered or "history" in lowered
    assert not text.rstrip().endswith(AUTHORED_STATE + "`"), \
        "the README must terminate in the terminal state"
    assert text.rstrip().endswith("`%s`" % TERMINAL_STATE)


def test_the_closure_artifacts_index_is_complete_and_real(status):
    for path in status["closure_artifacts"].values():
        assert (ROOT / path).is_file(), path
    assert set(status["closure_artifacts"].values()) | {"studies/study3r/STATUS.json"} \
        == CLOSURE_ADDED
