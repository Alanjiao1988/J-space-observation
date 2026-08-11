"""Tests for the Study 3 draft-v0.6 rendering and scoring registry.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 3,
5, 9 and 10.

draft-v0.6 changes exactly one normative thing: where the S2/S3 decision
statistic is read. This module holds that claim to its word. It asserts that

* the v0.6 registry reproduces from code and validates against its own schema;
* every visible rendering byte is identical to draft-v0.5, asset for asset;
* the draft-v0.5 registry and schema are still present and byte-identical, so
  the P0-T observations are never restated against a surface that did not exist
  when they were made;
* the new scoring boundary is complete, exact and self-reconciling for all four
  profiles; and
* every statistic the new boundary could have moved is re-derived from
  ``design_statistics.py`` and shown unchanged, while the two quantities that do
  change are surfaced explicitly rather than absorbed.

Standard library and pytest only, by design. No tokenizer, checkpoint, GPU or
model operation occurs.
"""

import hashlib
import importlib.util
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY3 = os.path.join(REPO_ROOT, "studies", "study3")
PROTOCOL_DIR = os.path.join(STUDY3, "protocol")
ANALYSIS_DIR = os.path.join(STUDY3, "analysis")
P0_R1_DIR = os.path.join(STUDY3, "pilot", "p0_r1")

REGISTRY_V0_6_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_6.json")
REGISTRY_V0_6_SCHEMA_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_6.schema.json")
REGISTRY_V0_5_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_5.json")
REGISTRY_V0_5_SCHEMA_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_5.schema.json")
TABLES_PATH = os.path.join(ANALYSIS_DIR, "scoring_boundary_v0_6_tables.json")

PROFILES = ("S1", "S2", "S3", "S4")
OPTION_LESS = ("S2", "S3")
DIGITS = "0123456789"

# The published draft-v0.5 identity. It must remain exactly this.
REGISTRY_V0_5_SHA256 = (
    "7e95c4911a36a3ffa2d2bf834a561e4d3743f1f641d29770dd0bc402b0a87d80")
REGISTRY_V0_5_BYTES = 37259


def _module(name, filename, directory):
    if name in sys.modules:
        return sys.modules[name]
    if directory not in sys.path:
        sys.path.insert(0, directory)
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(directory, filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SCHEMAS = _module("p0_r1_schemas", "p0_r1_schemas.py", P0_R1_DIR)
BOUNDARY = _module("scoring_boundary_v0_6", "scoring_boundary_v0_6.py",
                   ANALYSIS_DIR)


def _load(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def _raw(path):
    with open(path, "rb") as handle:
        return handle.read()


@pytest.fixture(scope="module")
def registry():
    return _load(REGISTRY_V0_6_PATH)


@pytest.fixture(scope="module")
def registry_schema():
    return _load(REGISTRY_V0_6_SCHEMA_PATH)


@pytest.fixture(scope="module")
def registry_v0_5():
    return _load(REGISTRY_V0_5_PATH)


@pytest.fixture(scope="module")
def tables():
    return _load(TABLES_PATH)


# --------------------------------------------------------------------------
# Identity and reproducibility.
# --------------------------------------------------------------------------

def test_the_registry_validates_against_its_committed_schema(registry,
                                                             registry_schema):
    assert SCHEMAS.schema_errors(registry, registry_schema) == []


def test_the_registry_identity_reproduces_exactly(registry):
    published = registry["registry_identity"]["registry_sha256"]
    probe = json.loads(json.dumps(registry))
    probe["registry_identity"]["registry_sha256"] = None
    canonical = json.dumps(probe, indent=1, sort_keys=True,
                           ensure_ascii=True) + "\n"
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == published


def test_the_registry_schema_and_tables_reproduce_from_code(registry,
                                                            registry_schema,
                                                            tables):
    assert BOUNDARY.canonical(BOUNDARY.build_registry()) == \
        _raw(REGISTRY_V0_6_PATH).decode("utf-8")
    assert BOUNDARY.canonical(BOUNDARY.build_schema()) == \
        _raw(REGISTRY_V0_6_SCHEMA_PATH).decode("utf-8")
    assert BOUNDARY.canonical(BOUNDARY.build_tables()) == \
        _raw(TABLES_PATH).decode("utf-8")
    assert registry["draft_version"] == "draft-v0.6"
    assert registry_schema["properties"]["draft_version"]["const"] == "draft-v0.6"
    assert tables["draft_version"] == "draft-v0.6"


def test_the_registry_is_a_binding_input_not_an_example(registry):
    assert registry["binding_status"].startswith(
        "BINDING_NORMATIVE_INPUT_NOT_AN_ILLUSTRATIVE_EXAMPLE")


def test_every_file_is_strict_lf(registry):
    del registry
    for path in (REGISTRY_V0_6_PATH, REGISTRY_V0_6_SCHEMA_PATH, TABLES_PATH):
        assert b"\r" not in _raw(path), path


# --------------------------------------------------------------------------
# draft-v0.5 stays history.
# --------------------------------------------------------------------------

def test_the_v0_5_registry_and_schema_are_preserved_byte_for_byte():
    raw = _raw(REGISTRY_V0_5_PATH)
    assert len(raw) == REGISTRY_V0_5_BYTES
    assert hashlib.sha256(raw).hexdigest() == REGISTRY_V0_5_SHA256
    assert os.path.exists(REGISTRY_V0_5_SCHEMA_PATH)


def test_v0_6_records_that_it_supersedes_v0_5_without_editing_it(registry):
    supersedes = registry["supersedes"]
    assert supersedes["registry"].endswith(
        "interface_calibration_rendering_registry_v0_5.json")
    assert supersedes["schema"].endswith(
        "interface_calibration_rendering_registry_v0_5.schema.json")
    assert supersedes["preserved_byte_for_byte_as_history"] is True


def test_v0_6_names_the_two_demonstrated_p0_t_defects_it_closes(registry):
    closes = registry["closes_p0_t_demonstrated_defects"]
    assert len(closes) == 2
    joined = " ".join(closes).lower()
    assert "not implementable" in joined
    assert "empty reason" in joined


# --------------------------------------------------------------------------
# The visible rendering surface is unchanged.
# --------------------------------------------------------------------------

def test_the_visible_rendering_surface_is_identical_to_v0_5(registry,
                                                            registry_v0_5):
    guarded = (
        "answer_cue", "answer_domain", "applicability_table", "encoding_policy",
        "instructions", "label_alphabets", "pair_isolation_rules",
        "placeholders", "prohibited_substitutions", "question_stem_templates",
        "renderings", "separators",
    )
    for key in guarded:
        assert registry[key] == registry_v0_5[key], key


def test_every_normative_template_asset_is_unchanged(registry, registry_v0_5):
    before = registry_v0_5["registry_identity"]["normative_template_assets"]
    after = registry["registry_identity"]["normative_template_assets"]
    assert after == before
    assert registry["registry_identity"]["normative_template_asset_count"] == 22


def test_the_answer_cue_and_candidate_surfaces_are_unchanged(registry):
    cue = registry["answer_cue"]
    assert cue["literal"] == "Answer:"
    assert cue["trailing_whitespace"].startswith("none")
    assert cue["candidate_surfaces_carry_exactly_one_leading_space"] is True
    for profile in registry["profiles"]:
        if profile["profile"] in OPTION_LESS:
            surfaces = profile["candidate_surfaces"]["answer_domain"]
            assert surfaces == [" %s" % digit for digit in DIGITS]
            for surface in surfaces:
                assert len(surface) == 2
                assert surface[0] == "\u0020"
        if profile["profile"] in ("S1", "S4"):
            assert profile["candidate_surfaces"].get(
                "by_label_alphabet", {}) == \
                _profile(registry, profile["profile"], from_v0_5=True).get(
                    "by_label_alphabet", {})


def _profile(registry, name, from_v0_5=False):
    source = _load(REGISTRY_V0_5_PATH) if from_v0_5 else registry
    for profile in source["profiles"]:
        if profile["profile"] == name:
            return profile["candidate_surfaces"]
    raise AssertionError("no profile %s" % name)


def test_the_registered_tie_break_orders_are_unchanged(registry, registry_v0_5):
    for index, profile in enumerate(registry["profiles"]):
        before = registry_v0_5["profiles"][index]
        assert profile["candidate_surfaces"]["tie_break_order"] == \
            before["candidate_surfaces"]["tie_break_order"]


def test_k6_sep_remains_structurally_absent_for_the_option_less_profiles(
        registry):
    rows = {(row["profile"], row["contrast"]): row
            for row in registry["applicability_table"]["rows"]}
    for profile in OPTION_LESS:
        row = rows[(profile, "K6-SEP")]
        assert row["applicability"] == "not_applicable"
        assert row["gate_bearing"] is False
        assert rows[(profile, "K6-INSTR")]["applicability"] == "applicable"


# --------------------------------------------------------------------------
# The new scoring boundary.
# --------------------------------------------------------------------------

def test_the_scoring_boundary_passes_the_production_validator(registry):
    assert SCHEMAS.validate_scoring_boundary(registry) is True


def test_the_first_discriminative_token_rule_is_registered_exactly(registry):
    rule = registry["scoring_boundary"]["first_discriminative_token_rule"]
    assert rule["factorization"] == "candidate_d = common_prefix || discriminant_d"
    assert "followed by the verified common-prefix token" in \
        rule["s2_scoring_context"]
    assert "CPU" in rule["s3_evaluation"]
    assert "teacher-forced" in rule["common_prefix_is"]
    assert "not a generated token" in rule["common_prefix_is"]
    prohibited = " ".join(rule["prohibited"]).lower()
    for phrase in ("scoring the shared first token",
                   "pretending the two-token candidate is one token",
                   "summing unrelated positions", "free generation",
                   "new calibration parameter"):
        assert phrase in prohibited
    assert "ascending mod-10 residue order" in rule["tie_break_order"]


def test_the_five_eligibility_conditions_are_registered(registry):
    conditions = registry["scoring_boundary"]["eligibility_conditions"]
    assert [entry["id"] for entry in conditions] == [
        "SB-1", "SB-2", "SB-3", "SB-4", "SB-5"]
    joined = " ".join(entry["condition"] for entry in conditions).lower()
    assert "exactly two tokens" in joined
    assert "identical for all ten candidates" in joined
    assert "registered leading u+0020" in joined
    assert "pairwise distinct" in joined
    assert "no bos, eos, chat template" in joined


def test_the_equivalence_proof_is_registered_and_exact(registry):
    assert SCHEMAS.validate_equivalence_registration(registry) is True
    proof = registry["scoring_boundary"]["equivalence_proof"]
    assert proof["identity"] == "P(u, v_d | x) = P(u | x) * P(v_d | x, u)"
    assert proof["consequence"] == (
        "argmax_d P(u, v_d | x) = argmax_d P(v_d | x, u)")
    assert "not an approximation" in proof["why_exact"]
    assert len(proof["does_not_extend_to"]) >= 6


def test_the_token_identities_are_derived_with_zero_encodes(registry):
    derived = registry["scoring_boundary"]["derived_token_identities"]
    assert derived["tokenizer_encodes_performed_by_the_derivation"] == 0
    assert derived["derivation_module"].endswith("p0_r1_factorization.py")
    assert "never transcribed" in derived["provenance"]
    assert len(derived["immutable_sources"]) == 4
    for role in ("RT", "RL", "RI"):
        entry = derived["by_role"][role]
        assert entry["common_prefix_token"] == 220
        assert entry["common_prefix_bytes"] == "\u0020"
        assert entry["discriminant_token_ids"] == list(range(15, 25))
        assert entry["discriminant_bytes"] == list(DIGITS)
        assert entry["eligible"] is True
    assert registry["scoring_boundary"][
        "common_prefix_token_for_every_pinned_role"] == 220


def test_every_profile_records_both_token_counts(registry):
    expected_rule = {
        "S1": "single_next_token_restricted_argmax",
        "S2": "first_discriminative_token_restricted_argmax",
        "S3": "first_discriminative_token_restricted_argmax",
        "S4": "bounded_greedy_generation_mapped_by_the_pinned_parser",
    }
    for profile in registry["profiles"]:
        name = profile["profile"]
        boundary = profile["scoring_boundary"]
        assert boundary["scoring_rule"] == expected_rule[name]
        assert boundary["registered_prompt_token_count"] > 0
        assert boundary["scoring_context_token_count"] == (
            boundary["registered_prompt_token_count"]
            + boundary["common_prefix_token_count"])
        assert boundary["common_prefix_token_count"] == (
            boundary["common_prefix_token_count_per_scored_row"]
            * boundary["scored_rows"])
        if name in OPTION_LESS:
            assert boundary["common_prefix_token_count_per_scored_row"] == 1
            assert boundary["teacher_forced_common_prefix"] is True
            assert boundary["verified_common_prefix_token"] == 220
            assert boundary["verified_discriminant_token_ids"] == \
                list(range(15, 25))
        else:
            assert boundary["common_prefix_token_count_per_scored_row"] == 0
            assert boundary["teacher_forced_common_prefix"] is False


def test_the_teacher_forced_prefix_is_not_a_generation_or_an_evaluation(
        registry):
    for profile in registry["profiles"]:
        if profile["profile"] not in OPTION_LESS:
            continue
        boundary = profile["scoring_boundary"]
        assert boundary["teacher_forced_common_prefix_is_a_generation"] is False
        assert boundary[
            "teacher_forced_common_prefix_is_a_separate_sequence_level_model_"
            "evaluation"] is False
        assert boundary[
            "teacher_forced_common_prefix_is_a_prompt_rendering_change"] is False


def test_s2_costs_one_evaluation_and_s3_costs_none(registry):
    boundaries = {profile["profile"]: profile["scoring_boundary"]
                  for profile in registry["profiles"]}
    assert boundaries["S1"][
        "sequence_level_model_evaluations_per_scored_row"] == 1
    assert boundaries["S2"][
        "sequence_level_model_evaluations_per_scored_row"] == 1
    assert boundaries["S3"][
        "sequence_level_model_evaluations_per_scored_row"] == 0
    assert boundaries["S3"]["tokens_processed"] == 0
    assert boundaries["S3"]["scoring_context_is_the_reused_s2_context"] is True
    assert boundaries["S2"]["scoring_context_token_count"] == \
        boundaries["S3"]["scoring_context_token_count"]


def test_s4_stays_diagnostic_only(registry):
    boundary = None
    for profile in registry["profiles"]:
        if profile["profile"] == "S4":
            boundary = profile["scoring_boundary"]
    assert boundary["participates_in_target_role_executability"] is False
    assert boundary["teacher_forced_common_prefix"] is False
    assert registry["scoring_boundary"]["s4_scoring_boundary_unchanged"][
        "participates_in_target_role_executability"] is False


def test_s1_scoring_is_unchanged(registry):
    block = registry["scoring_boundary"]["s1_scoring_boundary_unchanged"]
    assert "four registered label token IDs" in block["rule"]
    for role in ("RT", "RL", "RI"):
        for alphabet in ("ALPHA-1", "ALPHA-2"):
            entry = block["observed_label_token_ids"][role][alphabet]
            assert entry["all_single_token"] is True
            assert entry["pairwise_distinct"] is True
            assert len(entry["token_ids"]) == 4


# --------------------------------------------------------------------------
# Token accounting and statistical invariance.
# --------------------------------------------------------------------------

def test_the_token_accounting_reconciles(registry, tables):
    accounting = registry["token_accounting"]
    assert accounting == tables["token_accounting"]
    totals = accounting["p0_r1_totals"]
    by_profile = accounting["by_profile"]
    assert by_profile["S1"]["scored_rows"] == 162
    assert by_profile["S2"]["scored_rows"] == 18
    assert by_profile["S3"]["scored_rows"] == 18
    assert by_profile["S4"]["scored_rows"] == 12
    assert totals["scored_rows"] == 210
    assert totals["common_prefix_tokens_processed"] == 18
    assert totals["scoring_context_tokens_processed"] == (
        totals["registered_prompt_tokens_processed_by_restricted_scoring"]
        + totals["common_prefix_tokens_processed"])
    assert totals["s3_tokens_processed"] == 0
    assert totals["s3_sequence_level_model_evaluations"] == 0
    assert totals["extra_tokens_versus_the_v0_5_rule"] == 18
    assert totals[
        "extra_sequence_level_model_evaluations_versus_the_v0_5_rule"] == 0


def test_no_registered_statistic_moves(tables):
    values = tables["statistical_invariance"]["unchanged_and_why"]["values"]
    assert values["m_max"] == 43
    assert values["per_cell_false_negative_budget_exact_rational"] == "19/17200"
    assert values["per_cell_power_target_exact_rational"] == "17181/17200"
    assert values["profile_stage_power_floor_exact_rational"] == "381/400"
    assert values["study_end_to_end_power_floor_exact_rational"] == "9/10"
    assert values["development_sizes"] == {
        "I1_I3_joint_correctness_floor": 413,
        "I2_headroom_floor": 214,
        "I4_positive_reference_floor": 448,
    }
    assert values["development_pass_counts"] == {
        "I1_I3_joint_correctness_floor": 389,
        "I2_headroom_floor": 129,
        "I4_positive_reference_floor": 383,
    }
    assert values["confirmation_pass_counts"] == {
        "I1_I3_joint_correctness_floor": 388,
        "I2_headroom_floor": 127,
        "I4_positive_reference_floor": 381,
    }
    assert values["total_gate_bearing_cells"] == {
        "S1": 43, "S2": 16, "S3": 16, "S4": 12}
    assert values["applicable_i3_contrast_counts"]["S2"] == 1
    assert values["applicable_i3_contrast_counts"]["S3"] == 1
    assert values["development_projection_scored_rows"] == 31065
    assert values[
        "development_projection_sequence_level_model_evaluation_equivalents"] \
        == 31065
    assert values["development_projection_by_profile_prefill_evaluations"] == {
        "S1": 26064, "S2": 5001, "S3_if_independently_rendered": 5001}
    assert values["s3_incremental_sequence_evaluations"] == 0


def test_the_two_changed_quantities_are_surfaced_not_absorbed(tables):
    changed = tables["statistical_invariance"]["changed_and_surfaced"]
    assert sorted(changed) == ["s2_scoring_context_token_count",
                               "s3_zero_incremental_cost_condition"]
    tokens = changed["s2_scoring_context_token_count"]
    assert tokens["before"] == "registered_prompt_token_count"
    assert tokens["after"] == "registered_prompt_token_count + 1"
    assert tokens["development_projection_extra_tokens_processed"] == 5001
    assert tokens[
        "development_projection_extra_sequence_level_evaluations"] == 0
    condition = changed["s3_zero_incremental_cost_condition"]
    assert "jointly single-token registered answer domain" in \
        condition["before"][0]
    assert "common prefix token" in condition["after"][0]
    assert condition["numeric_effect"].startswith("none")
    assert tables["statistical_invariance"][
        "no_number_preserved_for_continuity"] is True


# --------------------------------------------------------------------------
# Claim boundary.
# --------------------------------------------------------------------------

def test_the_disposition_is_proposed_not_accepted(registry, tables):
    assert registry["disposition_status"] == (
        "PROPOSED_RESOLVED_SUBJECT_TO_FINAL_FOCUSED_REVIEW")
    assert registry["state"] == (
        "STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_6_COMPLETE_"
        "AWAITING_FINAL_FOCUSED_METHODS_REVIEW")
    assert tables["disposition_status"] == registry["disposition_status"]
    boundary = " ".join(registry["scoring_boundary"]["claim_boundary"]).lower()
    assert "not reviewed" in boundary
    assert "not frozen" in boundary
    assert "unanswered" in boundary


def test_every_authority_flag_stays_false_or_null(tables):
    flags = tables["authority_flags"]
    assert flags["frozen"] is False
    assert flags["formal_execution_authorized"] is False
    assert flags["draft_v0_6_reviewed"] is False
    assert flags["draft_v0_6_selected"] is False
    assert flags["interface_selected"] is None
    assert flags["positive_reference_selected"] is False
    assert flags["seed_authorized"] is False
    assert flags["bank_authorized"] is False
    assert flags["confirmation_access_authorized"] is False
    assert flags["winner_selected"] is False
    assert flags["od2_status"] == "unresolved"
    assert flags["ur22_status"] == "unresolved"
    assert flags["evidence_ledger_last_row"] == "EV-0016"


def test_the_rp_wrapper_stays_null_under_od2(registry):
    assert registry["rp_wrapper"]["wrapper"] is None


def test_no_tokenizer_or_model_operation_is_claimed(tables):
    counters = tables["operation_counters_in_the_calibration_session"]
    for name, value in counters.items():
        assert value == 0, name
    assert counters["tokenizer_encodes"] == 0
    assert counters["local_pytest_runs"] == 0


def test_this_module_performs_no_model_operation():
    source = open(os.path.abspath(__file__), encoding="utf-8").read()
    for forbidden in ("import " + "torch", "import " + "transformers",
                      "import " + "tokenizers", "AutoTokenizer", "AutoModel"):
        assert forbidden not in source
    boundary_source = open(
        os.path.join(ANALYSIS_DIR, "scoring_boundary_v0_6.py"),
        encoding="utf-8").read()
    for forbidden in ("import " + "torch", "import " + "transformers",
                      "AutoTokenizer"):
        assert forbidden not in boundary_source
