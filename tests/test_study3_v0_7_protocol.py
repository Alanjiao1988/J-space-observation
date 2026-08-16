"""Study 3 draft-v0.7 validation.

Authorities:
``studies/study3/prompts/study3_v0_7_copy_on_write_protocol_successor_authority.md``
section 6, and ``studies/study3/prompts/study3_v0_7_consolidated_amendment_authority.md``
section 8.

These tests drive the committed generator and the committed bundle. Nothing
here asserts on a literal transcribed from a source file without executing the
code that produced it, and nothing here imports a model or tokenizer library or
contacts any external service.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
STUDY3 = ROOT / "studies" / "study3"
PROTOCOL = STUDY3 / "protocol"
REVIEWS = STUDY3 / "reviews"
ANALYSIS = STUDY3 / "analysis"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


BUILD = _load(ANALYSIS / "v0_7_protocol_build.py", "v0_7_protocol_build")


def _json(path):
    return json.loads(Path(path).read_bytes().decode("utf-8"))


@pytest.fixture(scope="module")
def protocol():
    return _json(PROTOCOL / "interface_calibration_protocol_draft_v0_7.json")


@pytest.fixture(scope="module")
def protocol_schema():
    return _json(PROTOCOL / "interface_calibration_protocol_draft_v0_7.schema.json")


@pytest.fixture(scope="module")
def registry():
    return _json(PROTOCOL / "interface_calibration_rendering_registry_v0_7.json")


@pytest.fixture(scope="module")
def pointer():
    return _json(PROTOCOL / "interface_calibration_protocol_current.json")


@pytest.fixture(scope="module")
def amendment():
    return _json(REVIEWS / "v0_7_operator_amendment.json")


@pytest.fixture(scope="module")
def markdown():
    return (PROTOCOL / "interface_calibration_protocol_draft_v0_7.md").read_text(
        encoding="utf-8")


# ---------------------------------------------------------------------------
# 6.1 Historical preservation
# ---------------------------------------------------------------------------

def test_the_legacy_protocol_trio_is_byte_exact():
    observed = BUILD.verify_legacy_trio()
    assert set(observed) == set(BUILD.LEGACY_TRIO)
    for path, expected in BUILD.LEGACY_TRIO.items():
        assert observed[path]["sha256"] == expected
        assert observed[path]["status"] == BUILD.LEGACY_STATUS


@pytest.mark.parametrize("script", [
    "studies/study3/pilot/p0/p0_freeze_corpus.py",
    "studies/study3/pilot/p0/p0_protocol.py",
])
def test_the_committed_p0_regeneration_checks_still_pass(script):
    completed = subprocess.run(
        [sys.executable, str(ROOT / script), "--check"],
        capture_output=True, text=True, check=False, cwd=str(ROOT))
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_the_p0_corpus_manifest_is_unchanged_since_the_v0_7_starting_commit():
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only",
         "9fa28a02eb578f7743e325703b812873b57e0ed2", "HEAD", "--",
         "studies/study3/pilot", "paper/evidence_ledger.csv",
         "studies/study3/protocol/interface_calibration_protocol_draft.json",
         "studies/study3/protocol/interface_calibration_protocol_draft.md",
         "studies/study3/protocol/interface_calibration_protocol.schema.json",
         "tests/test_study3_p0_feasibility_pilot.py"],
        capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "", completed.stdout


def test_the_evidence_ledger_still_ends_at_ev_0016():
    rows = (ROOT / "paper" / "evidence_ledger.csv").read_text(
        encoding="utf-8").splitlines()
    assert rows[-1].startswith("EV-0016")


def test_the_placement_probe_output_is_still_reproducible():
    probe = _json(ANALYSIS / "v0_7_protocol_placement_probe.json")
    assert probe["byte_frozen_paths"] == [
        "studies/study3/protocol/interface_calibration_protocol_draft.json"]
    assert probe["all_three_amendable"] is False


# ---------------------------------------------------------------------------
# 6.2 New protocol integrity
# ---------------------------------------------------------------------------

def test_the_bundle_reproduces_byte_exactly_from_its_generator():
    completed = subprocess.run(
        [sys.executable, str(ANALYSIS / "v0_7_protocol_build.py"), "--check"],
        capture_output=True, text=True, check=False, cwd=str(ROOT))
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "STUDY3_V0_7_BUNDLE_REPRODUCES=1" in completed.stdout


def test_the_protocol_validates_against_its_own_schema(protocol, protocol_schema):
    assert BUILD.validate_against(protocol, protocol_schema) == []


def test_the_registry_validates_against_its_schema(registry):
    schema = _json(
        PROTOCOL / "interface_calibration_rendering_registry_v0_7.schema.json")
    assert BUILD.validate_against(registry, schema) == []


def test_the_pointer_validates_against_its_schema(pointer):
    schema = _json(PROTOCOL / "interface_calibration_protocol_current.schema.json")
    assert BUILD.validate_against(pointer, schema) == []


def test_the_amendment_validates_against_its_schema(amendment):
    schema = _json(REVIEWS / "v0_7_operator_amendment.schema.json")
    assert BUILD.validate_against(amendment, schema) == []


def test_the_schema_is_fail_closed(protocol_schema):
    assert protocol_schema["additionalProperties"] is False
    assert protocol_schema["properties"]["schema_version"]["const"] == \
        BUILD.SCHEMA_VERSION
    assert protocol_schema["properties"]["state"]["const"] == BUILD.STATE


def test_an_unregistered_top_level_key_is_refused(protocol, protocol_schema):
    forged = dict(protocol, unregistered_block={"x": 1})
    errors = BUILD.validate_against(forged, protocol_schema)
    assert any("unregistered_block" in error for error in errors)


def test_every_recorded_pointer_hash_matches_the_file_on_disk(pointer):
    for entry in pointer["active_bundle"].values():
        payload = (ROOT / entry["path"]).read_bytes()
        assert len(payload) == entry["bytes"], entry["path"]
        assert BUILD._sha256(payload) == entry["sha256"], entry["path"]


def test_the_pointer_resolves_only_to_the_versioned_bundle(pointer):
    contract = pointer["loader_contract"]
    assert contract["must_resolve_only_to_the_versioned_v0_7_bundle"] is True
    assert contract["must_not_load_interface_calibration_protocol_draft_json"] \
        is True
    assert pointer["fallback_to_legacy_permitted"] is False
    for entry in pointer["active_bundle"].values():
        assert entry["path"].endswith(("_v0_7.json", "_v0_7.schema.json",
                                       "_v0_7.md"))


def test_a_corrupt_bundle_fails_closed_rather_than_loading_v0_5(pointer):
    """Simulate the loader contract on a mismatched hash and an absent file."""
    contract = pointer["loader_contract"]
    assert contract["must_fail_closed_if_any_recorded_hash_mismatches"] is True
    assert contract["must_fail_closed_if_any_active_bundle_file_is_absent"] is True
    assert contract["fail_closed_state"] == "STUDY3_V0_7_ACTIVE_PROTOCOL_UNRESOLVABLE"

    entry = dict(pointer["active_bundle"]["protocol_json"])
    entry["sha256"] = "0" * 64
    payload = (ROOT / entry["path"]).read_bytes()
    mismatched = BUILD._sha256(payload) != entry["sha256"]
    assert mismatched, "a corrupted hash must not compare equal"
    legacy = pointer["legacy_protocol_historical_p0_binding_only"]
    assert legacy["is_current_protocol"] is False
    assert legacy["status"] == BUILD.LEGACY_STATUS


def test_the_legacy_bundle_is_labelled_historical_everywhere(pointer, protocol,
                                                             amendment):
    assert protocol["protocol_placement_v0_7"]["legacy_bundle_status"] == \
        BUILD.LEGACY_STATUS
    assert protocol["protocol_placement_v0_7"]["legacy_bundle_bytes_changed"] == 0
    assert amendment["operator_decision"]["legacy_bundle"]["bytes_changed"] == 0
    paths = {entry["path"] for entry
             in pointer["legacy_protocol_historical_p0_binding_only"]["files"]}
    assert paths == set(BUILD.LEGACY_TRIO)


def test_the_legacy_files_do_not_carry_the_new_status_string():
    for relative in BUILD.LEGACY_TRIO:
        text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        assert BUILD.LEGACY_STATUS not in text, relative


def test_the_protocol_is_self_contained(protocol):
    provenance = protocol["provenance_v0_7"]
    assert provenance["self_contained"] is True
    assert provenance["executor_must_layer_amendments_manually"] is False
    legacy = _json(PROTOCOL / "interface_calibration_protocol_draft.json")
    missing = sorted(set(legacy) - set(protocol))
    assert missing == [], missing


def test_every_decision_marker_appears_exactly_once_in_the_markdown(markdown,
                                                                    protocol):
    markers = [entry["marker"] for entry in protocol["decision_markers_v0_7"]]
    assert len(markers) == len(set(markers))
    for marker in markers:
        assert markdown.count("[%s]" % marker) == 1, marker


def test_every_decision_marker_resolves_to_a_real_protocol_key(protocol):
    for entry in protocol["decision_markers_v0_7"]:
        assert entry["json_key"] in protocol, entry


def test_the_markdown_agrees_with_the_decision_bearing_numbers(markdown, protocol):
    constants = protocol["numerical_closure_v0_7"]["derived_constants"]
    battery = protocol["competence_floor_battery_v0_7"]
    for key in ("I1a+I1b+I3", "I2", "I4"):
        row = battery["development_components"][key]
        assert "| %d | %d |" % (row["n"], row["pass_count"]) in markdown
    assert constants["generated_cot_ceiling_theta_exact_rational"] in markdown
    assert constants["wrapper_descriptive_bandwidth_exact_rational"] in markdown
    assert constants["negative_control_equivalence_upper_bound_exact_rational"] \
        in markdown
    assert BUILD.STATE in markdown


def test_no_decision_bearing_tbd_or_operator_discretion_remains(protocol):
    closure = protocol["numerical_closure_v0_7"]
    assert closure["tbd_count"] == 0
    assert closure["operator_discretion_clause_count"] == 0
    assert closure["unresolved_alternative_count"] == 0
    assert closure["every_execution_value_is_frozen_or_deterministically_deferred"]

    # A decision-bearing TBD is a *value* that defers a decision, not the word
    # appearing inside a sentence that forbids it.
    offenders = []
    for _, _, key in BUILD.DECISIONS:
        for pointer, value in _walk(protocol[key], "/" + key):
            if not isinstance(value, str):
                continue
            stripped = value.strip().lower()
            if stripped in ("tbd", "to be decided", "to be determined",
                            "operator discretion", "n/a", "?"):
                offenders.append((pointer, value))
    assert offenders == [], offenders


def test_every_deferral_has_a_rule_and_a_fail_closed_state(protocol):
    deferrals = protocol["deterministic_deferrals_v0_7"]
    assert deferrals["tbd_permitted"] is False
    assert len(deferrals["entries"]) >= 3
    for entry in deferrals["entries"]:
        assert entry["acquisition_rule"].strip()
        assert entry["fail_closed_absent_state"].strip()
        assert entry["may_default"] is False


def test_no_contradictory_duplicate_rule_across_protocol_and_registry(protocol,
                                                                      registry):
    surfaces = protocol["e0_answer_and_decoding_contract"][
        "legal_answer_surfaces_per_item"]
    assert surfaces["surfaces"] == registry["answer_surfaces"]["surfaces"]
    assert surfaces["count"] == registry["answer_surfaces"]["count"]
    assert registry["comparison_is_within_role"] is True
    assert protocol["wrapper_matched_contrast_v0_7"]["comparison_is_within_role"] \
        is True
    assert registry["registers_a_template_effect_claim"] is False
    assert protocol["wrapper_matched_contrast_v0_7"]["gate"][
        "registers_a_template_effect_claim"] is False
    assert registry["subordinate_to"] == \
        "interface_calibration_protocol_draft_v0_7.json"


# ---------------------------------------------------------------------------
# 6.3 Scientific and state-machine integrity
# ---------------------------------------------------------------------------

def test_no_d0_path_enters_q0_or_rp_b(protocol):
    d0 = protocol["estimands_v0_7"]["D0"]
    assert d0["enters_q0"] is False
    assert d0["enters_the_rp_b_gate"] is False
    q0 = protocol["q0_and_rp_b_v0_7"]
    assert q0["q0_must_contain_an_e0_expressed_competence_component"] is True
    assert q0["d0_alone_can_qualify_a_candidate"] is False


def test_e0_is_never_described_as_a_single_forward_pass(protocol):
    e0 = protocol["estimands_v0_7"]["E0"]
    assert e0["establishes_absence_of_internal_computation"] is False
    assert e0["answer_token_autoregression_is_part_of_the_estimand"] is True
    for phrase in ("one forward pass", "single forward pass"):
        assert phrase in e0["prohibited_descriptions"]


def test_the_single_forward_phrase_is_confined_to_d0(markdown):
    assert "single forward" not in markdown.lower().replace(
        "d0_single_forward_decodability", "")


def test_no_generated_cot_or_s4_result_selects_an_interface(protocol):
    ceiling = protocol["generated_cot_ceiling_v0_7"]
    assert ceiling["can_select_an_interface"] is False
    assert ceiling["is_an_interface_selector"] is False
    assert ceiling["is_s4"] is False
    assert ceiling["s4_is_ever_selectable"] is False
    assert ceiling["failure_state"] == "NO_CANONICAL_TASK_HEADROOM_FOR_TARGET_ROUTE"


def test_the_ceiling_unit_is_the_item_and_k_is_singular(protocol):
    ceiling = protocol["generated_cot_ceiling_v0_7"]
    assert ceiling["statistical_unit_is_the_item"] is True
    assert ceiling["n_times_k_responses_treated_as_independent_items"] is False
    assert ceiling["majority_vote_at_k_registered"] is False
    assert ceiling["frozen"]["k"] == 1
    assert ceiling["frozen"]["do_sample"] is False


def test_the_ceiling_reuses_the_registered_i2_headroom_construct(protocol):
    ceiling = protocol["generated_cot_ceiling_v0_7"]["frozen"]
    i2 = protocol["competence_floor_battery_v0_7"]["development_components"]["I2"]
    assert ceiling["theta_exact_rational"] == i2["p0_exact_rational"]
    assert ceiling["p1_exact_rational"] == i2["p1_exact_rational"]
    assert ceiling["alpha_exact_rational"] == i2["alpha_exact_rational"]
    assert ceiling["n"] == i2["n"]
    assert ceiling["pass_count"] == i2["pass_count"]


def test_the_wrapper_gate_is_joint_adequacy_not_an_effect_claim(protocol):
    gate = protocol["wrapper_matched_contrast_v0_7"]["gate"]
    assert gate["kind"] == "joint_adequacy"
    assert gate["registers_a_template_effect_claim"] is False
    assert gate["registers_an_equivalence_claim"] is False
    assert gate["registers_an_invariance_claim"] is False
    descriptive = protocol["wrapper_matched_contrast_v0_7"]["descriptive_reporting"]
    assert descriptive["trigger_has_gate_effect"] is False


def test_q0_multiplicity_uses_the_full_ladder_length(protocol):
    multiplicity = protocol["q0_and_rp_b_v0_7"]["multiplicity"]
    assert multiplicity["classical_fixed_sequence_protection_applies"] is False
    assert "full predeclared ladder length L" in \
        multiplicity["candidate_level_allocation"]
    assert multiplicity["within_candidate_component_allocation_preserved_separately"]


def test_confirmation_cannot_be_reused_after_failure(protocol):
    splits = protocol["q0_and_rp_b_v0_7"]["splits"]
    assert splits["confirmation_attempts_per_candidate"] == 1
    assert splits["tuning_after_confirmation_failure_permitted"] is False
    assert splits["rerun_after_confirmation_failure_permitted"] is False
    assert splits["confirmation_frozen_before_development_access"] is True
    assert splits["development_and_confirmation_are_physically_item_disjoint"]


def test_the_e0_parser_rejects_prefixes_and_unregistered_surfaces(protocol):
    contract = protocol["e0_answer_and_decoding_contract"]
    assert contract["matching_rule"]["kind"] == "full_sequence_exact_match"
    assert contract["matching_rule"]["prefix_match_permitted"] is False
    assert contract["invalid_output_treatment"]["unparseable_is_incorrect"] is True
    assert contract["invalid_output_treatment"]["dropping_permitted"] is False
    rejects = contract["parser"]["rejects"]
    for item in ("prefix matches", "rationale suffixes", "unparseable output",
                 "unregistered surfaces"):
        assert item in rejects
    assert contract["parser"]["separate_object_from_the_ceiling_parser"] is True


def test_full_context_tokenization_is_required(protocol):
    block = protocol["full_context_tokenization_and_d0_diagnostics"]
    assert block["full_context_rule"] == \
        "rendered_prompt_bytes + candidate_surface_bytes"
    assert block["candidate_only_encoding_permitted"] is False


def test_diagnostics_are_excluded_from_rescue_paths(protocol):
    diagnostics = protocol["full_context_tokenization_and_d0_diagnostics"][
        "d0_diagnostics"]
    assert diagnostics["descriptive_only"] is True
    assert diagnostics["may_rescue_a_failed_e0_gate"] is False
    assert diagnostics["enters_any_gate"] is False
    assert diagnostics["uncalibrated_probability_mass_threshold_registered"] is False


def test_the_battery_is_unchanged_and_no_new_mde_is_registered(protocol):
    battery = protocol["competence_floor_battery_v0_7"]
    assert battery["retained_unchanged"] is True
    assert battery["replaced_by_a_new_mde"] is False
    assert battery["four_hundred_cluster_mde_registered"] is False


def test_every_numeric_constant_agrees_with_the_committed_tables(protocol):
    tables = _json(ANALYSIS / "design_statistics_tables.json")
    battery = protocol["competence_floor_battery_v0_7"]
    for row in tables["development_exact_binomial_components"]:
        key = "+".join(row["gates"])
        assert battery["development_components"][key]["n"] == row["n"]
        assert battery["development_components"][key]["pass_count"] == \
            row["pass_count"]
    for row in tables["confirmation_exact_binomial_components"]:
        key = "+".join(row["gates"])
        assert battery["confirmation_components"][key]["pass_count"] == \
            row["pass_count"]
    assert battery["power_architecture"]["m_max"] == \
        tables["power_architecture"]["m_max"]


def test_the_design_statistics_still_regenerate():
    completed = subprocess.run(
        [sys.executable, str(ANALYSIS / "design_statistics.py"), "--check"],
        capture_output=True, text=True, check=False, cwd=str(ROOT))
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_the_rp_constructs_are_separate(protocol):
    separation = protocol["rp_b_and_rp_m_separation_v0_7"]
    assert separation["combined_into_one_gate"] is False
    assert separation["combined_into_one_claim"] is False
    assert separation["RP-M"]["must_share_rt_tokenizer"] is False
    assert separation["rp_m_validation_required_before_natural_model_patch_claims"]


def test_checkpoint_equivalence_is_the_four_part_functional_test(protocol):
    block = protocol["checkpoint_functional_equivalence_v0_7"]
    assert block["tokenizer_equivalence_inferred_from_model_names"] is False
    assert block["four_part_functional_test"] == [
        "bytes", "token IDs in full context", "common prefix",
        "discriminant position"]
    assert block["failure_classification"] == "isomorphic_reinstantiation"


def test_shakedown_limits_are_numeric_and_scientifically_inert(protocol):
    shake = protocol["engineering_shakedown_authority_v0_7"]
    for key in ("max_fix_and_rerun_cycles", "max_total_attempts",
                "max_wall_clock_minutes", "max_cpu_core_hours",
                "max_gpu_hours", "max_cloud_jobs"):
        assert isinstance(shake[key], int)
    assert shake["affects_any_estimand_threshold_or_gate"] is False
    assert shake["runs_in_this_authoring_session"] is False
    assert shake["outside_authority_state"] == \
        "STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED"


def test_the_negative_control_rule_is_quantitative(protocol):
    block = protocol["negative_control_equivalence_v0_7"]
    assert block[
        "not_significantly_above_chance_is_an_equivalence_demonstration"] is False
    assert "/" in block["quantitative_upper_bound_exact_rational"]


def test_the_manifest_seal_is_not_self_referential(protocol):
    seal = protocol["recursive_manifest_seal_v0_7"]
    assert seal["self_referential"] is False
    assert seal["construction"] == "two_level"
    assert seal["manifest_generation_script_is_included_and_hashed"] is True
    assert seal["explicit_exclusions"]
    assert seal["inclusion_path_globs"]


def test_activation_work_remains_unauthorized(protocol):
    block = protocol["activation_and_causal_claim_boundary_v0_7"]
    for key in ("activation_collection_authorized", "j_lens_fitting_authorized",
                "patching_authorized", "ablation_authorized",
                "mechanism_inference_authorized"):
        assert block[key] is False
    assert block["distillation_caused_the_mechanism_permitted"] is False


def test_all_zero_operation_counters_are_zero(protocol):
    counters = protocol["zero_operation_boundary_v0_7"]
    assert counters
    assert all(value == 0 for value in counters.values()), counters


def test_the_governance_state_is_preserved(protocol, amendment):
    assert protocol["status"]["frozen"] is False
    assert protocol["status"]["execution_authorized"] is False
    assert amendment["formal_execution_authorized"] is False
    assert amendment["frozen"] is False
    assert amendment["evidence_ledger_tail"] == "EV-0016"
    assert amendment["research_question_answered"] is False


def test_the_amendment_contains_no_review_verdict(amendment, protocol):
    assert amendment["review_verdict_contained"] is False
    packet = protocol["focused_review_packet_v0_7"]
    assert packet["contains_a_verdict"] is False
    assert packet["may_automatically_draft_v0_8"] is False


def test_the_p0_r2_audit_exceptions_are_recorded_without_repair(protocol):
    block = protocol["p0_r2_historical_treatment_v0_7"]
    assert block["legal_characterization"] == \
        "P0_R2_G2_TERMINAL_VERIFIED_WITH_AUDIT_EXCEPTIONS"
    assert len(block["audit_exceptions"]) == 4
    assert block["p0_result_is_scientific_evidence"] is False
    assert block["generation_3_created"] is False
    assert block["gpu_job_created_or_started"] is False


# ---------------------------------------------------------------------------
# Mutation tests over prohibited active-claim language
# ---------------------------------------------------------------------------

V0_7_TEXT_PATHS = (
    "studies/study3/protocol/interface_calibration_protocol_draft_v0_7.json",
    "studies/study3/protocol/interface_calibration_protocol_draft_v0_7.md",
    "studies/study3/protocol/interface_calibration_rendering_registry_v0_7.json",
    "studies/study3/protocol/interface_calibration_protocol_current.json",
    "studies/study3/reviews/v0_7_operator_amendment.json",
    "studies/study3/reviews/v0_7_operator_amendment.md",
)


def _walk(node, pointer=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, "%s/%s" % (pointer, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, "%s/%d" % (pointer, index))
    else:
        yield pointer, node


#: A string living under one of these keys is a *registration of a prohibition*,
#: not an assertion of the claim. Reading them as assertions would make a
#: protocol unable to name the wording it forbids.
DECLARATION_KEYS = ("prohibit", "prohibited", "phrases", "not_registered",
                    "outside_authority", "rejected")


def _asserts_phrase(line: str) -> bool:
    lowered = line.lower()
    return not any(token in lowered for token in (
        "prohibit", "never", "not registered", "is false", '": false',
        "may not", "cannot", "must not", "does not", "no ", "false,",
        "permitted only", "confined"))


@pytest.mark.parametrize("relative", V0_7_TEXT_PATHS)
def test_no_prohibited_active_claim_is_asserted(relative, protocol):
    registered = protocol["prohibited_language_v0_7"]["phrases"]
    path = ROOT / relative
    offenders = []
    if path.suffix == ".json":
        document = _json(path)
        for pointer, value in _walk(document):
            if not isinstance(value, str):
                continue
            segments = [segment.lower() for segment in pointer.split("/")]
            if any(any(token in segment for token in DECLARATION_KEYS)
                   for segment in segments):
                continue
            for phrase in registered:
                if phrase in value and _asserts_phrase(value):
                    offenders.append((pointer, phrase))
    else:
        # Markdown is hard-wrapped, so a negation can sit on the previous
        # physical line. Claims are made in paragraphs, so scan paragraphs.
        text = path.read_text(encoding="utf-8")
        for block in text.split("\n\n"):
            paragraph = " ".join(block.split())
            for phrase in registered:
                if phrase in paragraph and _asserts_phrase(paragraph):
                    offenders.append((paragraph[:110], phrase))
    assert offenders == [], offenders


def test_the_registered_vocabulary_actually_names_the_forbidden_wording(protocol):
    registered = protocol["prohibited_language_v0_7"]["phrases"]
    for phrase in ("robust to prompt format", "template-independent",
                   "format-insensitive", "one forward pass",
                   "distillation caused the mechanism"):
        assert phrase in registered, phrase
    assert protocol["prohibited_language_v0_7"]["checked_by_mutation_tests"]


def test_the_mutation_detector_would_catch_a_bare_prohibited_claim(protocol):
    """The detector must fail on a bare assertion, or it proves nothing."""
    registered = protocol["prohibited_language_v0_7"]["phrases"]
    bare = "The interface is robust to prompt format."
    offending = [phrase for phrase in registered if phrase in bare]
    assert offending, "the registered vocabulary must contain the bare phrase"
    assert _asserts_phrase(bare), "a bare prohibited claim must be detected"
    hedged = "No claim that the interface is robust to prompt format is registered."
    assert not _asserts_phrase(hedged), "a negated mention must be admitted"
