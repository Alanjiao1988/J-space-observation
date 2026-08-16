"""Tests for the Study 3 draft-v0.7 single independent focused methods review.

These tests belong to the review, not to the candidate. They do two things:

1. they check the review's own artifacts for internal consistency and schema
   conformance;
2. they independently re-establish the mechanical evidence behind every BLOCKING
   finding directly from the committed bytes, so an operator can re-run the
   review's factual claims without re-reading the report.

They import nothing from ``v0_7_protocol_build.py``, ``design_statistics.py`` or
any production gate calculator, and they modify nothing.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTOCOL_DIR = ROOT / "studies" / "study3" / "protocol"
REVIEWS = ROOT / "studies" / "study3" / "reviews"
ANALYSIS = ROOT / "studies" / "study3" / "analysis"
PROMPTS = ROOT / "studies" / "study3" / "prompts"

REVIEWED_COMMIT = "459d002442641039196ac3880d47a45a3b79a4c8"

REVIEW_OWN_PATHS = {
    "studies/study3/prompts/study3_v0_7_single_focused_methods_review_authority.md",
    "studies/study3/reviews/v0_7_single_focused_methods_review.md",
    "studies/study3/reviews/v0_7_single_focused_methods_review.json",
    "studies/study3/reviews/v0_7_single_focused_methods_review.schema.json",
    "studies/study3/analysis/independent_methods_recalculation_v0_7.py",
    "studies/study3/analysis/independent_methods_recalculation_tables_v0_7.json",
    "studies/study3/methods_review_receipt_v0_7.json",
    "tests/test_study3_v0_7_focused_review.py",
}


def _json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def review():
    return _json(REVIEWS / "v0_7_single_focused_methods_review.json")


@pytest.fixture(scope="module")
def review_schema():
    return _json(REVIEWS / "v0_7_single_focused_methods_review.schema.json")


@pytest.fixture(scope="module")
def protocol():
    return _json(PROTOCOL_DIR / "interface_calibration_protocol_draft_v0_7.json")


@pytest.fixture(scope="module")
def protocol_schema():
    return _json(
        PROTOCOL_DIR / "interface_calibration_protocol_draft_v0_7.schema.json")


@pytest.fixture(scope="module")
def registry_v0_7():
    return _json(PROTOCOL_DIR / "interface_calibration_rendering_registry_v0_7.json")


@pytest.fixture(scope="module")
def registry_v0_6():
    return _json(PROTOCOL_DIR / "interface_calibration_rendering_registry_v0_6.json")


@pytest.fixture(scope="module")
def pointer():
    return _json(PROTOCOL_DIR / "interface_calibration_protocol_current.json")


@pytest.fixture(scope="module")
def legacy():
    return _json(PROTOCOL_DIR / "interface_calibration_protocol_draft.json")


@pytest.fixture(scope="module")
def tables():
    return _json(ANALYSIS / "independent_methods_recalculation_tables_v0_7.json")


# ---------------------------------------------------------------------------
# 1. The review's own artifacts
# ---------------------------------------------------------------------------


def test_the_review_validates_against_its_own_schema(review, review_schema):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(review, review_schema)


def test_the_review_returns_the_rejection_state_because_findings_remain(review):
    counts = review["severity_counts"]
    blocking_or_major = counts["BLOCKING"] + counts["MAJOR"]
    assert blocking_or_major > 0
    assert review["verdict"] == "STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED"


def test_the_severity_counts_match_the_finding_list(review):
    counts = {"BLOCKING": 0, "MAJOR": 0, "MINOR": 0}
    for finding in review["findings"]:
        counts[finding["severity"]] += 1
    assert counts == review["severity_counts"]


def test_every_finding_id_is_unique_and_severity_tagged(review):
    ids = [f["id"] for f in review["findings"]]
    assert len(ids) == len(set(ids))
    letters = {"BLOCKING": "B", "MAJOR": "M", "MINOR": "N"}
    for finding in review["findings"]:
        assert finding["id"][6] == letters[finding["severity"]]


def test_the_review_implemented_no_repair_anywhere(review):
    assert all(f["reviewer_implemented_a_repair"] is False
               for f in review["findings"])
    assert review["review_identity"]["is_a_repair"] is False
    assert review["review_identity"]["is_an_amendment"] is False
    assert review["review_identity"]["is_a_freeze"] is False


def test_the_review_targets_the_registered_commit_and_tree(review):
    identity = review["review_identity"]
    assert identity["reviewed_commit"] == REVIEWED_COMMIT
    assert identity["reviewed_tree"] == \
        "2c84d55e6a965972e7cd3f69e3b0cded0bddfb04"
    assert identity["reviewed_parent"] == \
        "b9cddfc3a4c57a55bfef6105702be914c2545da1"


def test_the_review_authority_bytes_are_the_recorded_bytes(review):
    import hashlib
    recorded = review["authority"]
    path = ROOT / recorded["path"]
    payload = path.read_bytes()
    assert len(payload) == recorded["bytes"]
    assert hashlib.sha256(payload).hexdigest() == recorded["sha256"]
    assert b"\r" not in payload
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")


def test_every_prohibited_operation_counter_is_zero(review):
    counters = review["boundary"]["prohibited_operation_counters"]
    assert counters
    assert all(value == 0 for value in counters.values())
    assert review["boundary"]["reviewed_candidate_paths_changed"] == 0
    assert review["boundary"]["historical_protected_paths_changed"] == 0
    assert review["boundary"]["formal_execution_authorized"] is False
    assert review["boundary"]["research_question_answered"] is False
    assert review["boundary"]["evidence_ledger_tail"] == "EV-0016"


def test_the_evidence_ledger_still_ends_at_ev_0016():
    rows = (ROOT / "paper" / "evidence_ledger.csv").read_text(
        encoding="utf-8").splitlines()
    assert rows[-1].startswith("EV-0016,")


def test_the_review_changed_no_reviewed_or_historical_path():
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", REVIEWED_COMMIT, "HEAD"],
            cwd=str(ROOT), capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git history for the reviewed commit is unavailable here")
    changed = {line.strip() for line in completed.stdout.splitlines() if line.strip()}
    assert changed <= REVIEW_OWN_PATHS, sorted(changed - REVIEW_OWN_PATHS)


# ---------------------------------------------------------------------------
# 2. The independent recalculation
# ---------------------------------------------------------------------------


def test_the_independent_recalculation_reproduces_its_tables():
    completed = subprocess.run(
        [sys.executable,
         str(ANALYSIS / "independent_methods_recalculation_v0_7.py"), "--check"],
        cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "STUDY3_V0_7_INDEPENDENT_RECALCULATION_REPRODUCES=1" in completed.stdout


def test_the_recalculation_uses_no_external_package_and_no_production_calculator(
        tables):
    assert tables["external_packages_used"] == []
    forbidden = set(tables["does_not_import"])
    assert "studies/study3/analysis/v0_7_protocol_build.py" in forbidden
    assert "studies/study3/analysis/design_statistics.py" in forbidden
    source = (ANALYSIS / "independent_methods_recalculation_v0_7.py").read_text(
        encoding="utf-8")
    for module in ("v0_7_protocol_build", "design_statistics",
                   "scoring_boundary_v0_6"):
        assert "import %s" % module not in source


def test_every_exact_binomial_row_was_reproduced(tables, review):
    for name in ("I1a+I1b+I3", "I2", "I4"):
        for stage in ("development", "confirmation"):
            row = tables["components"][name][stage]
            assert row["pass_count_is_minimal_at_alpha"] is True
    assert tables["comparison"]["agreement_count"] == \
        review["independent_recalculation"]["agreement_count"]
    assert tables["comparison"]["mismatch_count"] == \
        review["independent_recalculation"]["mismatch_count"]


def test_the_registered_sample_sizes_are_minimal_only_without_the_wrapper_factor(
        tables):
    at_target = tables["minimal_sizes_at_registered_per_cell_target"]
    assert all(row["registered_n_equals_minimal_n"] for row in at_target.values())
    wrapped = tables["wrapper_multiplicity"]["minimal_sizes_with_wrapper_factor"]
    assert all(row["registered_n_equals_minimal_n"] is False
               for row in wrapped.values())
    assert tables["wrapper_multiplicity"]["m_max_with_wrapper_factor"] == \
        2 * tables["wrapper_multiplicity"]["m_max_without_wrapper_factor"]


# ---------------------------------------------------------------------------
# 3. Mechanical re-establishment of each BLOCKING finding
# ---------------------------------------------------------------------------


def test_b01_two_active_fields_name_different_normative_protocols(protocol,
                                                                  pointer):
    authoritative = protocol["status"]["authoritative_artifact"]
    assert "interface_calibration_protocol_draft.json" in authoritative
    assert "interface_calibration_protocol_draft_v0_7.json" not in authoritative
    assert protocol["protocol_placement_v0_7"][
        "sole_top_level_normative_protocol"].endswith(
            "interface_calibration_protocol_draft_v0_7.json")
    assert pointer["loader_contract"][
        "must_not_load_interface_calibration_protocol_draft_json"] is True
    design_test = (ROOT / "tests" / "test_study3_design.py").read_text(
        encoding="utf-8")
    assert "v0_7" not in design_test
    assert "tests/test_study3_design.py" in authoritative


def test_b02_the_normative_v0_6_registry_is_outside_the_active_bundle(
        registry_v0_7, registry_v0_6, pointer, protocol):
    inherited = registry_v0_7["inherited_v0_6_scoring_boundary"]
    assert "normative" in inherited["why"]
    active = {entry["path"] for entry in pointer["active_bundle"].values()}
    assert inherited["source"]["path"] not in active
    assert pointer["loader_contract"][
        "must_resolve_only_to_the_versioned_v0_7_bundle"] is True
    assert pointer["fallback_to_legacy_permitted"] is False
    assert protocol["provenance_v0_7"]["self_contained"] is True
    roles = [d["role"] for d in protocol["provenance_v0_7"]["derived_from"]]
    assert any(role.startswith("normative v0.6") for role in roles)
    assert protocol["protocol_placement_v0_7"][
        "legacy_and_v0_6_are_provenance_inputs_not_runtime_overlays"] is True
    for rule in ("question_stem_templates", "instructions", "separators",
                 "label_alphabets", "answer_cue", "scoring_boundary"):
        assert rule in registry_v0_6
        assert rule not in registry_v0_7


def test_b03_od2_is_still_blocking_and_the_ladder_has_no_referent(protocol):
    assert protocol["blocking_decisions"] == ["OD2"]
    od2 = [d for d in protocol["unresolved_operator_decisions"]
           if d["id"] == "OD2"][0]
    assert od2["status"] == "unresolved" and od2["blocking"] is True
    assert "freeze" in od2["blocks"]
    ladder = protocol["q0_and_rp_b_v0_7"]["ladder"]
    assert ladder["blocked_on"] == "OD2"
    assert ladder["length_L_deferred_to"] == "DEFER-02"
    text = json.dumps(protocol, ensure_ascii=True)
    assert text.count("Qwen-family size ladder") == 1
    assert "candidate universe" not in text and "observation date" not in text
    assert protocol["numerical_closure_v0_7"][
        "operator_discretion_clause_count"] == 0


def test_b04_the_state_machine_omits_every_v0_7_gate_and_reuses_q0(protocol,
                                                                  legacy):
    machine = protocol["state_machine_v0_4"]
    ids = [state["id"] for state in machine["states"]]
    assert ids[0] == "Q0_INSTRUMENT"
    assert "model-free I0 fixtures" in machine["states"][0]["rule"]
    joined = json.dumps(machine, ensure_ascii=True).lower()
    for absent in ("shakedown", "cot", "e0", "d0", "rp-b", "rp_b", "rp-m",
                   "wrapper", "negative control", "activation"):
        assert absent not in joined
    assert machine["total"] is True
    assert json.dumps(machine, sort_keys=True) == \
        json.dumps(legacy["state_machine_v0_4"], sort_keys=True)


def test_b05_k6_sep_applicability_contradicts_itself_across_active_fields(
        protocol, registry_v0_6):
    truth = {row["profile"]: row for row in protocol["gate_truth_table"]["rows"]}
    census = protocol["competence_floor_battery_v0_7"]["gate_bearing_cell_counts"]
    power = protocol["power_architecture_v0_4"]["cell_counts"]["by_profile"]
    ceiling = {g["gate_id"]: g for g in protocol["gate_hierarchy"]}["I3"][
        "claim_ceiling_by_profile"]
    v0_6_counts = registry_v0_6["applicability_table"][
        "per_profile_applicable_contrast_counts"]
    for profile in ("S2", "S3"):
        assert truth[profile]["I3_K6"]["K6-SEP"] == "not_applicable"
        assert census[profile]["applicable_i3_contrast_ids"] == ["K6-INSTR"]
        assert power[profile]["applicable_i3_contrast_count"] == 1
        assert v0_6_counts[profile] == 1
        assert "K6-SEP" in ceiling[profile]["applicable_cells"]
        assert ceiling[profile]["applicable_cell_count"] == 2
    semantics = {g["gate_id"]: g for g in protocol["gate_hierarchy"]}["I3"][
        "not_applicable_semantics"]
    assert "two K6 contrasts are applicable to every profile" in semantics


def test_b05_the_s2_and_s3_projection_is_the_two_contrast_figure(protocol,
                                                                tables):
    streams = protocol["operation_boundaries"]["projected_future_operations"][
        "work_streams"]["target_role_development"]["by_profile"]
    for committed_name, mine in (("S2", "S2"), ("S3_if_independently_rendered", "S3")):
        assert streams[committed_name]["base_item_contrast_clusters"] == 826
        assert tables["projection"][mine]["base_item_contrast_clusters"] == 413
    mismatched = {m["where"].rsplit(".", 1)[-1]
                  for m in tables["comparison"]["mismatches"]}
    assert mismatched == {"base_item_contrast_clusters", "cluster_rendered_rows",
                          "rendered_rows_per_target_role"}


def test_b05_the_contradiction_was_carried_forward_verbatim(protocol, legacy):
    carried = protocol["provenance_v0_7"]["carried_forward_top_level_keys"]
    identical = [key for key in carried
                 if json.dumps(legacy[key], sort_keys=True)
                 == json.dumps(protocol[key], sort_keys=True)]
    assert len(identical) == 35
    for key in ("gate_hierarchy", "gate_truth_table", "operation_boundaries"):
        assert key in identical


def test_b06_no_wrapper_arm_registers_any_byte_level_field(registry_v0_7):
    fields = set()
    for wrapper in registry_v0_7["wrappers"]:
        fields |= set(wrapper)
    assert fields == {"role", "arm", "wrapper_id", "chat_template_applied",
                      "description", "shared_across_roles", "deterministic",
                      "few_shot_completion_format"}
    for required in ("messages", "system", "user", "assistant", "separator",
                     "bos", "eos", "template_bytes", "template_revision",
                     "demonstrations", "answer_cue", "differing_field"):
        assert not any(required in field for field in fields), required
    for wrapper in registry_v0_7["wrappers"]:
        assert isinstance(wrapper.get("few_shot_completion_format", False), bool)


def test_b07_the_wrapper_gate_is_a_gate_but_not_a_cell_factor(protocol,
                                                             registry_v0_7):
    gate = protocol["wrapper_matched_contrast_v0_7"]["gate"]
    assert gate["kind"] == "joint_adequacy"
    assert len(gate["conditions"]) == 2
    factors = protocol["atomic_evaluation_cells"]["cell_factors"]
    assert not any("wrapper" in factor for factor in factors)
    assert len(registry_v0_7["wrapper_arms"]) == 2
    streams = set(protocol["operation_boundaries"]["projected_future_operations"][
        "work_streams"])
    joined = " ".join(streams).lower()
    for absent in ("wrapper", "e0", "cot", "ceiling", "negative", "q0", "rp_b"):
        assert absent not in joined


def test_b08_the_negative_control_registers_no_executable_design(protocol):
    block = protocol["negative_control_equivalence_v0_7"]
    assert set(block) == {"derivation", "test",
                          "quantitative_upper_bound_exact_rational",
                          "not_significantly_above_chance_is_an_equivalence"
                          "_demonstration"}
    joined = json.dumps(block, ensure_ascii=True).lower()
    for absent in ("clopper", "pearson", "beta quantile", "independent_unit",
                   "sample size", "multiplicity"):
        assert absent not in joined
    markers = {m["json_key"] for m in protocol["decision_markers_v0_7"]}
    assert "negative_control_equivalence_v0_7" not in markers


def test_b09_the_two_token_claim_depends_on_deferred_revisions(protocol):
    contract = protocol["e0_answer_and_decoding_contract"]
    assert contract["eos_and_stop_semantics"]["max_new_tokens"] == 3
    assert contract["complete_token_id_sequence_per_surface_and_revision"][
        "deferred_to"] == "DEFER-01"
    assert protocol["estimands_v0_7"]["E0"]["is_the_primary_gate_for_rp_b"] is True
    equivalence = protocol["checkpoint_functional_equivalence_v0_7"]
    assert equivalence["failure_classification"] == "isomorphic_reinstantiation"
    joined = json.dumps(equivalence, ensure_ascii=True).lower()
    assert "legal surface" not in joined and "max_new_tokens" not in joined
    states = [entry["fail_closed_absent_state"] for entry in
              protocol["deterministic_deferrals_v0_7"]["entries"]]
    assert not any("TOKEN" in state and "SURFACE" in state for state in states)


def test_b10_the_ceiling_has_no_population_and_no_resource_bound(protocol,
                                                                tables):
    frozen = protocol["generated_cot_ceiling_v0_7"]["frozen"]
    for absent in ("task_population", "stratum", "bank", "generator",
                   "operation_upper_bound", "resource_upper_bound"):
        assert absent not in frozen
    assert frozen["maximum_generation_length_rule"].endswith("DEFER-03")
    ceiling = tables["cot_ceiling"]
    assert ceiling["recomputed_pass_count"] == frozen["pass_count"] == 129
    assert ceiling["critical_accuracy_exact_rational"] == "129/214"
    assert ceiling["theta_exact_rational"] == "1/2"
    assert ceiling["null_floor_equals_e0_restricted_chance_level"] is False
    cells = protocol["sampling_frame_v0_4"]["development_sampling_cells"]
    assert not any("cot" in json.dumps(cell, ensure_ascii=True).lower()
                   for cell in cells)


def test_b11_the_protocol_schema_leaves_decision_bearing_keys_unconstrained(
        protocol_schema):
    properties = protocol_schema["properties"]
    unconstrained = sorted(key for key, value in properties.items() if value == {})
    assert len(properties) == 62
    assert len(unconstrained) == 52
    for key in ("gate_hierarchy", "gate_truth_table",
                "competence_floor_battery_v0_7", "blocking_decisions",
                "unresolved_operator_decisions", "state_machine_v0_4",
                "recursive_manifest_seal_v0_7",
                "negative_control_equivalence_v0_7",
                "e0_answer_and_decoding_contract", "operation_boundaries",
                "power_architecture_v0_4", "deterministic_deferrals_v0_7"):
        assert key in unconstrained, key
    ceiling = properties["generated_cot_ceiling_v0_7"]["properties"]
    for numeric in ("theta_exact_rational", "n", "pass_count"):
        assert numeric not in ceiling
    assert "derived_constants" not in properties["numerical_closure_v0_7"][
        "properties"]


def test_b11_the_committed_regeneration_test_compares_against_its_own_generator():
    source = (ROOT / "tests" / "test_study3_v0_7_protocol.py").read_text(
        encoding="utf-8")
    assert "v0_7_protocol_build.py" in source
    assert "STUDY3_V0_7_BUNDLE_REPRODUCES=1" in source
    assert 'protocol_schema["additionalProperties"] is False' in source


def test_b12_the_manifest_seal_names_no_generator_and_omits_normative_paths(
        protocol, pointer, registry_v0_7):
    seal = protocol["recursive_manifest_seal_v0_7"]
    assert seal["manifest_generation_script_is_included_and_hashed"] is True
    assert seal["covers_all_decision_bearing_bytes"] is True
    joined = json.dumps(seal, ensure_ascii=True)
    assert ".py" in joined
    globs = seal["inclusion_path_globs"]
    assert len(globs) == 4
    pointer_path = "studies/study3/protocol/interface_calibration_protocol_current"
    assert not any(pointer_path in glob for glob in globs)
    v0_6 = registry_v0_7["inherited_v0_6_scoring_boundary"]["source"]["path"]
    assert not any(v0_6.rsplit("/", 1)[-1].split(".")[0] in glob for glob in globs)
    for noun in ("task banks", "tokenizer files", "image digest"):
        assert noun in seal["inclusion"]
    assert not any("src/" in glob for glob in globs)


# ---------------------------------------------------------------------------
# 4. MAJOR findings
# ---------------------------------------------------------------------------


def test_m01_fourth_review_language_survives_in_active_fields(protocol):
    text = json.dumps(protocol, ensure_ascii=True)
    assert text.count("FOURTH_INDEPENDENT_METHODS_REVIEW") >= 11
    assert "FOURTH independent methods review" in text
    assert protocol["state"].endswith("AWAITING_SINGLE_FOCUSED_METHODS_REVIEW")


def test_m02_eight_v0_7_blocks_carry_no_decision_marker(protocol):
    markers = {m["json_key"] for m in protocol["decision_markers_v0_7"]}
    assert len(markers) == 14
    unmarked = {key for key in protocol if key.endswith("_v0_7")} - markers
    assert unmarked == {"decision_markers_v0_7", "focused_review_packet_v0_7",
                        "negative_control_equivalence_v0_7",
                        "numerical_closure_v0_7", "p0_r2_historical_treatment_v0_7",
                        "prohibited_language_v0_7", "provenance_v0_7",
                        "zero_operation_boundary_v0_7"}


def test_m03_the_markdown_claims_self_containment_and_hides_the_blocker(protocol):
    markdown = (PROTOCOL_DIR /
                "interface_calibration_protocol_draft_v0_7.md").read_text(
                    encoding="utf-8")
    assert "never layers" in markdown
    assert "blocking_decisions" not in markdown
    assert "OD2" not in markdown
    assert protocol["blocking_decisions"] == ["OD2"]
