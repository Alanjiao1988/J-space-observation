"""Tests for the Study 3R protocol-v1 single independent focused review.

Authority:
``studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md``

This module lives under ``studies/study3r/reviews/`` rather than the top-level
``tests/`` directory, exactly as the review authority requires. It is not
collected by the repository's default ``testpaths = ["tests"]`` configuration
and is run explicitly:

    python -m pytest studies/study3r/reviews/test_study3r_protocol_v1_single_focused_review.py

It asserts three classes of property:

1. the review disposition validates against its own restrictive schema and is
   internally consistent with the findings it records;
2. the review artifacts are additive, LF-only, and changed no candidate,
   protected or historical path;
3. the decision-bearing claims behind the four BLOCKING findings are
   re-derived here from the committed candidate bytes, so a reader can check
   the verdict without trusting the review prose.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
from fractions import Fraction
from math import comb

import pytest

REVIEWS = pathlib.Path(__file__).resolve().parent
STUDY3R = REVIEWS.parent
ROOT = STUDY3R.parent.parent

REVIEW_JSON = REVIEWS / "study3r_protocol_v1_single_focused_review.json"
REVIEW_SCHEMA = REVIEWS / "study3r_protocol_v1_single_focused_review.schema.json"
REVIEW_MD = REVIEWS / "study3r_protocol_v1_single_focused_review.md"
RECEIPT = REVIEWS / "study3r_protocol_v1_review_receipt.json"
RECALC_TABLES = REVIEWS / "study3r_review_independent_recalculation_tables.json"
TOKENIZER_REPORT = REVIEWS / "study3r_review_tokenizer_reconstruction.json"
MUTATION_REPORT = REVIEWS / "study3r_review_mutation_audit.json"

AUTHORITY_RELATIVE = ("studies/study3r/prompts/"
                      "study3r_protocol_v1_single_focused_review_authority.md")
REVIEWED_COMMIT = "da1ea31b51b784cb1ab3529f9de2f6ee27c853dd"
REVIEWED_TREE = "c1de862ba3782b4930191a51df8790bb4279344c"
AUTHORING_START = "cd9c0af3118ca2f254bd0bbaa8eb2ee4dad6d1ed"

PERMITTED_VERDICTS = (
    "STUDY3R_PROTOCOL_V1_FOCUSED_REVIEW_ACCEPTED_AWAITING_FREEZE_AUTHORITY",
    "STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION",
    "STUDY3R_PROTOCOL_V1_TERMINAL_OPERATOR_DECISION_REQUIRED",
)

#: Candidate paths the review may not touch.
CANDIDATE_PATHS = (
    "studies/study3r/protocol/study3r_protocol_v1.json",
    "studies/study3r/protocol/study3r_protocol_v1.md",
    "studies/study3r/protocol/study3r_protocol_v1.schema.json",
    "studies/study3r/protocol/study3r_rendering_registry_v1.json",
    "studies/study3r/protocol/study3r_state_machine_v1.json",
    "studies/study3r/protocol/study3r_protocol_current.json",
    "studies/study3r/analysis/study3r_protocol_build.py",
    "studies/study3r/analysis/study3r_design_statistics.py",
    "studies/study3r/analysis/study3r_independent_recalculation.py",
    "studies/study3r/analysis/study3r_tokenizer_probe.py",
    "studies/study3r/analysis/study3r_manifest.py",
    "studies/study3r/tasks/study3r_task_generators_v1.py",
    "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json",
    "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json",
    "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.json",
    "studies/study3r/study3r_candidate_manifest_v1.json",
    "studies/study3r/study3r_authoring_disclosure_v1.json",
    "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md",
    "tests/test_study3r_protocol_v1.py",
    "tests/test_study3r_operator_governance.py",
    ".gitattributes",
    "paper/evidence_ledger.csv",
)


def _json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _git(*args: str) -> str:
    return subprocess.run(["git", "--no-pager", *args], cwd=str(ROOT),
                          capture_output=True, text=True, check=True).stdout


@pytest.fixture(scope="module")
def review():
    return _json(REVIEW_JSON)


@pytest.fixture(scope="module")
def candidate_protocol():
    return _json(ROOT / "studies/study3r/protocol/study3r_protocol_v1.json")


@pytest.fixture(scope="module")
def candidate_machine():
    return _json(ROOT / "studies/study3r/protocol/study3r_state_machine_v1.json")


# ---------------------------------------------------------------------------
# 1. The disposition itself
# ---------------------------------------------------------------------------


def test_the_review_validates_against_its_restrictive_schema(review):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(review, _json(REVIEW_SCHEMA))


@pytest.mark.parametrize("path", [REVIEW_JSON, REVIEW_SCHEMA, REVIEW_MD,
                                  RECEIPT, RECALC_TABLES, TOKENIZER_REPORT,
                                  MUTATION_REPORT])
def test_every_review_artifact_exists_and_is_lf_only_without_a_bom(path):
    payload = path.read_bytes()
    assert payload, path
    assert b"\r" not in payload, path
    assert not payload.startswith(b"\xef\xbb\xbf"), path
    assert payload.endswith(b"\n"), path


def test_the_review_binds_the_expected_reviewed_object(review):
    start = review["starting_state"]
    assert start["expected_commit"] == REVIEWED_COMMIT
    assert start["expected_tree"] == REVIEWED_TREE
    assert start["integrity_verified"] is True
    assert start["clean_worktree"] is True
    assert start["head_equals_fetched_origin_main"] is True
    assert start["evidence_ledger_last_row"] == "EV-0016"
    assert start["all_execution_authorized_fields_false"] is True


def test_exactly_one_registered_verdict_state_is_recorded(review):
    assert review["verdict"]["state"] in PERMITTED_VERDICTS
    assert review["verdict"]["authorizes_execution"] is False
    assert review["verdict"]["authorizes_an_amendment"] is False
    assert review["verdict"][
        "no_confirmed_decision_bearing_defect_was_downgraded"] is True


def test_the_verdict_follows_the_authority_severity_rules(review):
    counts = review["severity_counts"]
    observed = {"BLOCKING": 0, "MAJOR": 0, "MINOR": 0}
    for finding in review["findings"]:
        observed[finding["severity"]] += 1
    assert observed == counts
    if counts["BLOCKING"] >= 1:
        assert review["verdict"]["state"] == \
            "STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION"
    else:
        assert review["verdict"]["state"] in (
            "STUDY3R_PROTOCOL_V1_FOCUSED_REVIEW_ACCEPTED_AWAITING_FREEZE_AUTHORITY",
            "STUDY3R_PROTOCOL_V1_TERMINAL_OPERATOR_DECISION_REQUIRED")


def test_no_finding_was_downgraded_to_a_limitation(review):
    for finding in review["findings"]:
        assert finding["downgraded_to_a_limitation"] is False, finding


def test_finding_identifiers_are_unique_and_contiguous(review):
    ids = [finding["finding_id"] for finding in review["findings"]]
    assert len(set(ids)) == len(ids)
    assert ids == ["F-%02d" % index for index in range(1, len(ids) + 1)]


def test_every_finding_id_appears_in_the_markdown(review):
    markdown = REVIEW_MD.read_text(encoding="utf-8")
    for finding in review["findings"]:
        assert finding["finding_id"] in markdown, finding["finding_id"]
    assert review["verdict"]["state"] in markdown


def test_the_review_declares_its_independence(review):
    independence = review["independence"]
    assert independence["is_independent_of_the_authoring_party"] is True
    assert independence["drafted_or_edited_any_candidate_artifact"] is False
    assert independence["imported_the_candidate_tokenizer_probe"] is False
    assert independence[
        "imported_any_candidate_calculator_in_the_recalculation"] is False


def test_every_prohibited_operation_counter_is_zero(review):
    for name, value in review["prohibited_operation_counters"].items():
        assert value == 0, name


# ---------------------------------------------------------------------------
# 2. Additivity and protected bytes
# ---------------------------------------------------------------------------


def test_the_review_changed_no_candidate_or_protected_path():
    changed = {line.strip() for line
               in _git("diff", "--name-only", REVIEWED_COMMIT,
                       "HEAD").splitlines() if line.strip()}
    for relative in CANDIDATE_PATHS:
        assert relative not in changed, relative


def test_every_review_path_is_additive_and_inside_the_reviews_directory():
    lines = [line for line
             in _git("diff", "--name-status", REVIEWED_COMMIT,
                     "HEAD").splitlines() if line.strip()]
    permitted_outside = {AUTHORITY_RELATIVE}
    for line in lines:
        status, path = line.split("\t", 1)
        path = path.strip()
        assert status.strip() == "A", line
        assert (path.startswith("studies/study3r/reviews/")
                or path in permitted_outside), path


def test_the_review_history_is_linear_and_merge_free():
    merges = [line.strip() for line
              in _git("rev-list", "--merges",
                      "%s..HEAD" % REVIEWED_COMMIT).splitlines() if line.strip()]
    assert merges == []
    assert _git("merge-base", REVIEWED_COMMIT, "HEAD").strip() == REVIEWED_COMMIT


def test_the_review_authority_was_published_alone_and_first(review):
    commits = [line.strip() for line
               in _git("rev-list", "--reverse",
                       "%s..HEAD" % REVIEWED_COMMIT).splitlines() if line.strip()]
    assert commits, "no review commits found"
    listed = [line.strip() for line
              in _git("show", "--name-only", "--format=",
                      commits[0]).splitlines() if line.strip()]
    assert listed == [AUTHORITY_RELATIVE], listed
    assert _git("rev-parse", "%s^" % commits[0]).strip() == REVIEWED_COMMIT
    assert review["review_authority_commit"]["commit"] == commits[0]
    assert review["review_authority_commit"]["parent"] == REVIEWED_COMMIT
    assert review["review_authority_commit"][
        "published_alone_before_any_finding"] is True


def test_the_recorded_review_authority_identity_matches_the_committed_bytes(
        review):
    recorded = review["review_authority_commit"]
    import hashlib

    payload = (ROOT / pathlib.PurePosixPath(AUTHORITY_RELATIVE)).read_bytes()
    assert len(payload) == recorded["authority_byte_length"]
    assert hashlib.sha256(payload).hexdigest() == recorded["authority_sha256"]
    blob = _git("hash-object",
                str(ROOT / pathlib.PurePosixPath(AUTHORITY_RELATIVE))).strip()
    assert blob == recorded["authority_blob"]


def test_the_candidate_state_and_execution_flags_were_not_changed(
        candidate_protocol):
    pointer = _json(ROOT / "studies/study3r/protocol/study3r_protocol_current.json")
    assert pointer["authored_state"] == \
        "STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW"
    assert pointer["execution_authorized"] is False
    assert pointer["frozen"] is False
    status = candidate_protocol["status"]
    assert status["frozen"] is False
    assert status["execution_authorized"] is False
    assert status["formal_execution_authorized"] is False


def test_the_evidence_ledger_still_ends_at_ev_0016():
    rows = (ROOT / "paper" / "evidence_ledger.csv").read_text(
        encoding="utf-8").splitlines()
    assert rows[-1].startswith("EV-0016,")


# ---------------------------------------------------------------------------
# 3. The BLOCKING findings, re-derived from the committed candidate bytes
# ---------------------------------------------------------------------------


def test_f01_no_mixed_bank_registers_a_depth_allocation_rule(
        candidate_protocol):
    """F-01: four banks mix D2 and D3 and none registers an allocation."""
    banks = candidate_protocol["task_populations"]["banks"]
    mixed = [bank for bank in banks
             if sorted(bank["family_mix"]) == ["D2", "D3"]]
    assert len(mixed) == 4, [bank["bank_id"] for bank in mixed]
    for bank in mixed:
        assert set(bank) == {"bank_id", "family_mix", "gate_id", "n"}, bank

    haystack = "\n".join(
        (ROOT / pathlib.PurePosixPath(relative)).read_text(encoding="utf-8")
        for relative in (
            "studies/study3r/protocol/study3r_protocol_v1.json",
            "studies/study3r/protocol/study3r_protocol_v1.schema.json",
            "studies/study3r/protocol/study3r_protocol_v1.md",
            "studies/study3r/analysis/study3r_atomic_cell_census_v1.json",
            "studies/study3r/analysis/study3r_design_statistics.py",
            "studies/study3r/tasks/study3r_task_generators_v1.py",
        ))
    for token in ("d2_count", "d3_count", "depth_allocation",
                  "items_per_depth", "depth_balance", "per_depth"):
        assert token not in haystack, token

    generators = (ROOT / "studies/study3r/tasks/study3r_task_generators_v1.py"
                  ).read_text(encoding="utf-8")
    assert "def realize_bank(bank_id: str, family: str, size: int, *," \
        in generators, "realize_bank no longer takes a single family"


def test_f02_the_pooled_depth_cell_admits_a_chance_level_depth_three_record():
    """F-02: exact integer counterexamples at the registered n and boundary."""
    alpha = Fraction(1, 1160)
    chance = Fraction(1, 4)

    def upper_tail(n: int, k: int, p: Fraction) -> Fraction:
        q = 1 - p
        return sum((comb(n, i) * p ** i * q ** (n - i)
                    for i in range(max(k, 0), n + 1)), Fraction(0))

    # G09 / G07 / G08: n = 74, pass if k >= 51.
    n, boundary = 74, 51
    # Balanced 37/37 allocation with perfect depth-2 performance.
    minimum_d3 = boundary - 37
    assert minimum_d3 == 14
    accuracy = Fraction(minimum_d3, 37)
    assert accuracy < Fraction(1, 2), accuracy
    assert upper_tail(37, minimum_d3, chance) > alpha
    # Zero depth-3 successes still pass whenever n_d3 <= n - boundary.
    assert n - boundary == 23
    assert max(0, boundary - (n - 23)) == 0

    # G01: n = 128, pass if k >= 111.
    n, boundary = 128, 111
    assert n - boundary == 17
    assert max(0, boundary - (n - 17)) == 0


def test_f02_counterexamples_are_recorded_in_the_review(review):
    counterexamples = {row["gate_id"]: row
                       for row in review["depth_audit"]["counterexamples"]}
    assert "G09_RT_E0_QUALIFICATION" in counterexamples
    target = counterexamples["G09_RT_E0_QUALIFICATION"]
    assert target["n"] == 74
    assert target["pass_boundary"] == 51
    assert target["balanced_minimum_depth_three_correct"] == 14
    assert target["balanced_minimum_depth_three_accuracy"] == "14/37"
    assert target[
        "balanced_minimum_depth_three_beats_chance_at_alpha_per_cell"] is False
    assert target[
        "zero_depth_three_success_passes_when_depth_three_size_at_most"] == 23
    assert review["depth_audit"]["depth_is_a_gate_bearing_factor"] is False
    assert review["depth_audit"]["allocation_rule_registered_anywhere"] is False


def test_f03_the_prequalification_states_are_globally_conjunctive(
        candidate_machine, candidate_protocol):
    """F-03: one failing cell in S03-S06 reaches a global terminal."""
    states = {state["state_id"]: state for state in candidate_machine["states"]}
    expected = {
        "S03_GENERATED_COT_CEILING": "T03_COT_CEILING_FAILED",
        "S04_COMPETENCE_CONTROLS": "T04_COMPETENCE_CONTROL_FAILED",
        "S05_NEGATIVE_CONTROL": "T05_NEGATIVE_CONTROL_FAILED",
        "S06_TWO_WRAPPER_JOINT_ADEQUACY": "T06_WRAPPER_ADEQUACY_FAILED",
    }
    for state_id, terminal in expected.items():
        transitions = {transition["outcome"]: transition["target"]
                       for transition in states[state_id]["transitions"]}
        assert terminal in transitions.values(), state_id
        failing = [outcome for outcome, target in transitions.items()
                   if target == terminal]
        assert len(failing) == 1, state_id
        assert ("at_least_one" in failing[0]
                or "at_least_one_arm_failed" in failing[0]), failing

    # Every one of those gates spans all four checkpoint roles, so a single
    # RP-B candidate's failure reaches the global terminal.
    gates = {gate["gate_id"]: gate
             for gate in candidate_protocol["statistics"]["gates"]}
    prequalification = ("G01_COT_CEILING", "G02_CONTROL_RECOVERY",
                        "G03_CONTROL_BINDING", "G04_CONTROL_PRIMITIVE",
                        "G05_NEGATIVE_CONTROL", "G06_WRAPPER_JOINT_ADEQUACY")
    cells = 0
    for gate_id in prequalification:
        gate = gates[gate_id]
        assert set(gate["checkpoint_roles"]) == {"RT", "RP_B1", "RP_B2",
                                                 "RP_B3"}, gate_id
        cells += gate["atomic_cell_count"]
    assert cells == 44

    # ... while the authoritative Markdown promises scanning past failures.
    markdown = (ROOT / "studies/study3r/protocol/study3r_protocol_v1.md"
                ).read_text(encoding="utf-8")
    assert "scans past failures until the first confirmed pass" in markdown


def test_f03_scope_conclusions_are_recorded_in_the_review(review):
    scope = review["gate_scope_audit"]
    assert scope["rp_b1_failure_blocks_rp_b2"] is True
    assert scope["rp_b2_failure_blocks_rp_b3"] is True
    assert scope["cells_that_must_pass_before_ladder_scanning_begins"] == 44
    assert scope[
        "candidate_specific_failure_is_promoted_to_study_wide_failure"] is True
    assert scope["markdown_claims_the_ladder_scans_past_failures"] is True
    assert scope["state_paths_reconstructed_independently"] is True


def test_f04_the_cot_route_registers_no_further_decoding_field(
        candidate_protocol):
    """F-04: the CoT contract stops at do_sample, k, parser and bounds."""
    ceiling = candidate_protocol["estimands"]["generated_cot_ceiling"]
    for absent in ("temperature", "top_p", "top_k", "num_beams", "seed",
                   "batch_size", "padding_side", "aggregation", "dtype",
                   "quantization", "device_map", "stop_tokens",
                   "eos_token_id", "library_version"):
        assert absent not in ceiling, absent
    for bound in ceiling["resource_bounds_per_checkpoint"].values():
        assert set(bound) == {"canonical_prompt_token_count",
                              "context_window_tokens", "fits_context_window",
                              "items", "max_new_tokens_per_item",
                              "worst_case_sequence_tokens",
                              "worst_case_total_tokens"}, bound

    bundle = "\n".join(
        (ROOT / pathlib.PurePosixPath(relative)).read_text(encoding="utf-8")
        for relative in (
            "studies/study3r/protocol/study3r_protocol_v1.json",
            "studies/study3r/protocol/study3r_protocol_v1.md",
            "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json",
        ))
    for absent in ("top_p", "top_k", "torch_dtype", "device_map",
                   "padding_side", "quantization", "bfloat16"):
        assert absent not in bundle, absent


def test_f04_cot_audit_is_recorded_in_the_review(review):
    audit = review["cot_ceiling_audit"]
    assert audit["do_sample_registered"] is True
    assert audit["k_registered"] is True
    for absent in ("temperature_registered", "top_p_registered",
                   "top_k_registered", "num_beams_registered",
                   "seed_semantics_registered", "aggregation_registered",
                   "batch_size_registered", "padding_side_registered",
                   "eos_or_stop_tokens_registered",
                   "dtype_or_quantization_registered",
                   "library_version_pinned_as_part_of_the_execution_contract"):
        assert audit[absent] is False, absent
    assert audit["every_checkpoint_must_pass_before_ladder_scanning"] is True


# ---------------------------------------------------------------------------
# 4. The independent evidence artifacts agree with the disposition
# ---------------------------------------------------------------------------


def test_the_recalculation_agrees_with_the_candidate_on_every_number(review):
    tables = _json(RECALC_TABLES)
    assert tables["imports_no_candidate_calculator"] is True
    assert tables["m_max_agrees"] is True
    assert tables["alpha_per_cell_agrees"] is True
    assert tables["all_gates_agree"] is True
    recorded = review["statistical_recalculation"]
    assert recorded["m_max_recomputed"] == tables["registered_design"]["m_max"]
    assert recorded["alpha_per_cell_recomputed"] == \
        tables["registered_design"]["alpha_per_cell"]
    assert recorded["total_scheduled_evaluations"] == \
        tables["registered_design"]["total_scheduled_evaluations"]
    assert recorded["mismatches"] == []
    assert recorded["counterfactual_m_max_with_separate_depth_cells"] == \
        tables["counterfactual_depth_split_census"]["m_max"]
    assert recorded["counterfactual_is_a_diagnostic_not_a_repair"] is True


def test_the_tokenizer_reconstruction_agrees_with_the_disposition(review):
    report = _json(TOKENIZER_REPORT)
    assert report["imported_the_candidate_probe"] is False
    recorded = review["tokenizer_reconstruction"]
    assert recorded["adversarial_grid_size"] == report["adversarial_grid_size"]
    assert recorded["surfaces_rendered_per_checkpoint"] == \
        report["surfaces_rendered_per_checkpoint"]
    assert recorded[
        "distinct_functional_equivalence_strata_over_the_full_surface_set"] == \
        report["joint_strata"]["distinct_stratum_count"]
    for entry in report["checkpoints"]:
        assert entry["trust_remote_code"] is False
        assert entry["weight_paths_present_in_repository"], entry["role"]
        ids = {label: value["token_ids"]
               for label, value in entry["e0_legal_answer_surfaces"].items()}
        assert ids == {"A": [32], "B": [33], "C": [34], "D": [35]}, entry["role"]
        assert entry["chat_template_opens_reasoning_span"] is True
        assert entry["chat_template_emits_the_closure_itself"] is False


def test_the_d0_position_varies_across_the_adversarial_surface_set(review):
    report = _json(TOKENIZER_REPORT)
    recorded = review["tokenizer_reconstruction"]
    for entry in report["checkpoints"]:
        w1 = entry["distinct_d0_discriminant_positions_W1_RAW_DIRECT"]
        w2 = entry["distinct_d0_discriminant_positions_W2_ROLE_CANONICAL"]
        assert len(w1) > 1 and len(w2) > 1, entry["role"]
        assert [min(w1), max(w1)] == recorded["d0_position_range_w1"]
        assert [min(w2), max(w2)] == recorded["d0_position_range_w2"]
        assert recorded["d0_registered_position_w1"] in w1
        assert recorded["d0_registered_position_w2"] in w2
    assert recorded["d0_position_is_fixture_specific"] is True


def test_every_registered_candidate_mutation_was_killed(review):
    report = _json(MUTATION_REPORT)
    assert report["registered_mutation_count"] == 24
    survivors = [row["mutation_id"] for row in report["registered_mutations"]
                 if row["outcome"] != "killed"]
    assert survivors == [], survivors
    assert review["mutation_audit"]["registered_mutation_count"] == 24


def test_the_recorded_mutation_survivors_match_the_audit(review):
    report = _json(MUTATION_REPORT)
    recorded = review["mutation_audit"]
    assert recorded["total_mutation_count"] == report["total_mutation_count"]
    assert recorded["killed_count"] == report["killed_count"]
    assert recorded["survivor_count"] == report["survivor_count"]
    assert sorted(recorded["survivor_ids"]) == \
        sorted(row["mutation_id"] for row in report["survivors"])
    for row in report["survivors"]:
        assert row["class"] == "coordinated", row
        assert row["changed_artifacts"], row


def test_the_manifest_still_reproduces_from_the_committed_bytes(review):
    import hashlib

    manifest = _json(ROOT / "studies/study3r/study3r_candidate_manifest_v1.json")
    lines = []
    for entry in sorted(manifest["entries"], key=lambda item: item["path"]):
        payload = (ROOT / pathlib.PurePosixPath(entry["path"])).read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        assert digest == entry["sha256"], entry["path"]
        assert len(payload) == entry["bytes"], entry["path"]
        lines.append("%s\0%s\0%d\n" % (entry["path"], digest, len(payload)))
    aggregate = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    assert aggregate == manifest["aggregate_sha256"]
    recorded = review["manifest_and_bundle_audit"]
    assert recorded["aggregate_sha256_recomputed"] == aggregate
    assert recorded["aggregate_sha256_registered"] == \
        manifest["aggregate_sha256"]
    assert recorded["every_entry_reproduces"] is True


# ---------------------------------------------------------------------------
# 5. The receipt
# ---------------------------------------------------------------------------


def test_the_receipt_matches_the_review(review):
    receipt = _json(RECEIPT)
    assert receipt["verdict"] == review["verdict"]["state"]
    assert receipt["reviewed_commit"] == REVIEWED_COMMIT
    assert receipt["reviewed_tree"] == REVIEWED_TREE
    assert receipt["authority"] == AUTHORITY_RELATIVE
    assert receipt["execution_authorized"] is False
    assert receipt["candidate_frozen"] is False
    assert receipt["severity_counts"] == review["severity_counts"]
    assert receipt["blocking_finding_ids"] == [
        finding["finding_id"] for finding in review["findings"]
        if finding["severity"] == "BLOCKING"]
    for name, value in receipt["prohibited_operation_counters"].items():
        assert value == 0, name


def test_the_receipt_lists_every_published_review_artifact():
    import hashlib

    receipt = _json(RECEIPT)
    for entry in receipt["artifacts"]:
        path = ROOT / pathlib.PurePosixPath(entry["path"])
        assert path.is_file(), entry["path"]
        payload = path.read_bytes()
        assert len(payload) == entry["bytes"], entry["path"]
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"], \
            entry["path"]
        assert entry["path"].startswith("studies/study3r/reviews/") \
            or entry["path"] == AUTHORITY_RELATIVE, entry["path"]
