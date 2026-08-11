"""Registration tests for Study 3 P0-R1 and the draft-v0.6 scoring boundary.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 3,
4, 6, 8 and 10.

Two things make this module different from a schema smoke test.

*Every mutation is non-vacuous.* Section 8 requires each negative mutation to
alter live input that production code reads, and to be rejected by the
production validator. Every mutation here therefore goes through
``assert_live_mutation_rejected``, which

1. loads the real committed document from disk;
2. proves the production validator ACCEPTS it unmutated, so the field really is
   read on real data;
3. applies the mutation and proves the canonical bytes actually changed; and
4. proves the production validator REJECTS the mutated document.

A perturbation of a fabricated test-local copy that no production code reads
would fail step 2 and is therefore impossible to write here by accident.

*No model operation occurs.* This module performs zero tokenizer encodes, zero
tokenizer constructions, zero checkpoint downloads, zero weight loads, zero GPU
allocations and zero forward passes, and it asserts that torch, transformers and
tokenizers are never imported by the code under test.

Standard library and pytest only, by design.
"""

import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY3 = os.path.join(REPO_ROOT, "studies", "study3")
P0_R1_DIR = os.path.join(STUDY3, "pilot", "p0_r1")
ANALYSIS_DIR = os.path.join(STUDY3, "analysis")
PROTOCOL_DIR = os.path.join(STUDY3, "protocol")

REGISTRY_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_6.json")
RECEIPT_PATH = os.path.join(P0_R1_DIR, "p0_r1_pre_execution_receipt.json")
PROTOCOL_JSON_PATH = os.path.join(P0_R1_DIR, "p0_r1_protocol.json")
CORRECTED_TABLE_PATH = os.path.join(
    ANALYSIS_DIR, "p0_r1_corrected_eligibility_tables.json")

P0_RESULT_REPO_PATH = (
    "studies/study3/pilot/p0/results/p0-t/p0_tokenizer_gate_result.json")
P0_RECEIPT_REPO_PATH = (
    "studies/study3/pilot/p0/results/p0-t/p0_tokenizer_gate_receipt.json")
P0_DISPOSITION_REPO_PATH = (
    "studies/study3/pilot/p0/results/p0-t/P0_T_DISPOSITION.md")
P0_CORPUS_REPO_PATH = "studies/study3/pilot/p0/corpus/p0_corpus.json"

FORBIDDEN_MODULES = ("torch", "transformers", "tokenizers")


def _module(name, filename, directory=P0_R1_DIR):
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


FACT = _module("p0_r1_factorization", "p0_r1_factorization.py")
ELIG = _module("p0_r1_eligibility", "p0_r1_eligibility.py")
SCHEMAS = _module("p0_r1_schemas", "p0_r1_schemas.py")
RUNNER = _module("p0_r1_model_runner", "p0_r1_model_runner.py")
SUMMARIZE = _module("p0_r1_summarize", "p0_r1_summarize.py")
COUNTERS = _module("p0_r1_counters", "p0_r1_counters.py")
GATE = _module("p0_r1_replay_gate", "p0_r1_replay_gate.py")


def _load(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def _canonical(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True)


# --------------------------------------------------------------------------
# The non-vacuity harness required by section 8.
# --------------------------------------------------------------------------

def assert_live_mutation_rejected(live, mutate, validator, rejects,
                                  label="the mutation"):
    """Prove a mutation alters live input and is rejected by production code.

    ``live`` is the real committed document. ``validator`` is the production
    function that reads it. The unmutated document must be accepted, the mutated
    document must differ in canonical bytes, and the mutated document must be
    rejected.
    """
    assert validator(live) is True, (
        "the production validator must accept the live document, otherwise the "
        "mutation would not be testing live input")

    mutated = copy.deepcopy(live)
    mutate(mutated)
    assert _canonical(mutated) != _canonical(live), (
        "%s did not change the live document, so it is vacuous" % label)

    with pytest.raises(rejects):
        validator(mutated)
    return mutated


# --------------------------------------------------------------------------
# Fixtures over live committed documents.
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def registry():
    return _load(REGISTRY_PATH)


@pytest.fixture(scope="module")
def receipt():
    return _load(RECEIPT_PATH)


@pytest.fixture(scope="module")
def p0_r1_protocol():
    return _load(PROTOCOL_JSON_PATH)


@pytest.fixture(scope="module")
def p0_t_result():
    return FACT.load_immutable(FACT.RESULT_PATH)


@pytest.fixture(scope="module")
def frozen_corpus():
    return FACT.load_immutable(FACT.CORPUS_PATH)


@pytest.fixture(scope="module")
def factorization(registry):
    return FACT.gate(registry)


@pytest.fixture(scope="module")
def corrected(p0_t_result, factorization):
    s1 = GATE.published_s1_surfaces(p0_t_result)
    return ELIG.classify(p0_t_result["records"], factorization, s1, GATE.ROLES)


@pytest.fixture(scope="module")
def live_plan(registry, factorization):
    """A live S2 scoring plan, built from the committed registry and evidence."""
    role = factorization["roles"][0]
    result = FACT.load_immutable(FACT.RESULT_PATH)
    prompt = None
    for record in result["records"]:
        if record.get("structural_absence"):
            continue
        if record["profile"] == "S2" and record["role"] == role["role"] \
                and record.get("source") == "frozen_corpus":
            prompt = record["members"][0]["token_ids"]
            break
    assert prompt, "the immutable evidence carries an S2 prompt encode"
    surfaces = None
    for profile in registry["profiles"]:
        if profile["profile"] == "S2":
            surfaces = list(profile["candidate_surfaces"]["answer_domain"])
    return RUNNER.build_scoring_plan(
        "S2", role["role"], "p0-r1-live", prompt,
        role["complete_candidate_token_ids"], surfaces,
        common_prefix_token=role["common_prefix_token"],
        tie_break_order=surfaces)


# --------------------------------------------------------------------------
# Positive: the registered derivation.
# --------------------------------------------------------------------------

def test_no_model_or_tokenizer_library_is_imported():
    """A static guard: no P0-R1 module may import a model or tokenizer library.

    This is deliberately a source-text guard rather than a ``sys.modules`` probe.
    In a full-suite run another module may legitimately import torch, and a
    process-global probe would then report a fact about the suite rather than
    about this package.
    """
    for name in sorted(os.listdir(P0_R1_DIR)):
        if not name.endswith(".py"):
            continue
        source = open(os.path.join(P0_R1_DIR, name), encoding="utf-8").read()
        for module in FORBIDDEN_MODULES:
            assert "import " + module not in source, (
                "%s imports %s; the P0-R1 replay and registration path performs "
                "zero tokenizer and model operations" % (name, module))
        assert "from " + "transformers" not in source, name
        assert "AutoTokenizer" not in source, name
        assert "AutoModel" not in source, name


def test_this_module_performs_no_model_operation(factorization):
    assert factorization["tokenizer_encodes_performed"] == 0
    assert factorization["tokenizer_constructions_performed"] == 0
    assert factorization["model_operations_performed"] == 0
    source = open(os.path.abspath(__file__), encoding="utf-8").read()
    for module in FORBIDDEN_MODULES:
        assert "\nimport " + module not in source


def test_the_replay_verifier_reads_only_immutable_sources(factorization):
    paths = {entry["path"] for entry in factorization["immutable_sources"]}
    assert P0_RESULT_REPO_PATH in paths
    assert P0_CORPUS_REPO_PATH in paths
    for entry in factorization["immutable_sources"]:
        registered = FACT.IMMUTABLE_SOURCES[entry["path"]]
        assert entry["bytes"] == registered["bytes"]
        assert entry["sha256"] == registered["sha256"]


def test_the_common_prefix_token_is_derived_not_transcribed(factorization):
    """The identity must come out of the evidence, and must be 220 for these roles."""
    source = open(os.path.join(P0_R1_DIR, "p0_r1_factorization.py"),
                  encoding="utf-8").read()
    assert re.search(r"(?<![0-9a-zA-Z])220(?![0-9a-zA-Z])", source) is None, (
        "the common-prefix token identity is written into the verifier as a "
        "literal; section 3.2 requires it to be derived")
    for token in range(15, 25):
        assert re.search(r"(?<![0-9a-zA-Z])%d(?![0-9a-zA-Z])" % token,
                         source) is None, (
            "discriminant token %d is written into the verifier as a literal"
            % token)
    for role in factorization["roles"]:
        assert role["common_prefix_token"] == 220
        assert role["common_prefix_bytes"] == "\u0020"
    assert factorization["common_prefix_token_is_common_to_every_role"]


def test_the_discriminant_token_ids_are_derived_and_map_to_the_digits(
        factorization):
    for role in factorization["roles"]:
        assert role["discriminant_token_ids"] == list(range(15, 25))
        assert role["discriminant_bytes"] == list("0123456789")
        assert role["registered_candidate_surfaces"] == [
            " %s" % digit for digit in "0123456789"]


def test_every_section_3_2_condition_holds_for_every_pinned_role(factorization):
    required = (
        "every_complete_candidate_is_exactly_two_tokens",
        "the_first_token_is_identical_for_all_ten_candidates",
        "the_common_token_decodes_byte_exactly_to_one_registered_u0020",
        "the_second_token_ids_are_pairwise_distinct",
        "the_second_token_ids_map_byte_exactly_to_0_through_9_in_order",
        "the_factorization_reproduces_every_complete_candidate_surface",
        "no_constant_sequence_initial_token_across_distinct_prompts",
        "no_sequence_final_token_absent_from_every_interior_position",
        "no_registered_prompt_ends_with_the_common_prefix_token",
        "every_published_sequence_reconciles_with_its_prompt_bytes",
    )
    assert {entry["role"] for entry in factorization["roles"]} == {"RT", "RL",
                                                                   "RI"}
    for role in factorization["roles"]:
        assert role["eligible"], role["reasons"]
        for condition in required:
            assert role["conditions"][condition] is True, (
                "%s failed condition %s" % (role["role"], condition))


def test_the_ranking_equivalence_holds_exactly():
    conditional = {digit: 0.05 for digit in "0123456789"}
    conditional["7"] = 0.55
    assert FACT.assert_ranking_equivalence(0.3, conditional) == "7"
    assert FACT.assert_ranking_equivalence(0.9, conditional) == "7"


def test_the_registered_tie_break_is_preserved_under_a_tie():
    conditional = {digit: 0.1 for digit in "0123456789"}
    assert FACT.assert_ranking_equivalence(0.4, conditional) == "0"


# --------------------------------------------------------------------------
# Positive: the repaired classifier.
# --------------------------------------------------------------------------

def test_the_corrected_matrix_has_no_empty_reason_ineligible_row(corrected):
    for cell in corrected["matrix"]:
        if cell["status"] == ELIG.INELIGIBLE:
            assert cell["reasons"], (
                "%s/%s/%s is ineligible with an empty reason list"
                % (cell["role"], cell["profile"], cell["contrast"]))


def test_the_corrected_matrix_repairs_the_published_propagation_defect(
        p0_t_result, corrected):
    historical = p0_t_result["eligibility_matrix"]
    empty = [cell for cell in historical
             if cell["status"] != "eligible" and not cell["reasons"]]
    assert len(empty) == 27, (
        "the immutable P0-T result records 27 empty-reason ineligible S1 cells")
    repaired = ELIG.validate_no_propagation(corrected["matrix"], historical)
    assert len(repaired) == 27
    assert {entry["profile"] for entry in repaired} == {"S1"}
    assert all(entry["corrected_status"] == ELIG.ELIGIBLE for entry in repaired)


def test_every_target_role_retains_an_executable_genuine_i3_contrast(corrected):
    executable = corrected["executable_genuine_i3_contrasts"]
    assert sorted(executable) == ["RI", "RL", "RT"]
    for role in ("RT", "RL", "RI"):
        assert len(executable[role]) == 11, executable[role]
        assert not any(entry.startswith("S4/") for entry in executable[role])
    assert corrected["roles_without_executable_contrast"] == []


def test_the_stop_label_is_unambiguous_and_the_old_one_is_historical(corrected):
    assert corrected["stop_label_if_any_role_has_none"] == (
        "STUDY3_P0_R1_STOPPED_SOME_TARGET_ROLE_HAS_NO_EXECUTABLE_GENUINE_I3_"
        "CONTRAST")
    assert corrected["stop_label_semantics"] == (
        "one or more target roles has no executable genuine I3 contrast")
    assert corrected["historical_stop_label"] == (
        "STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE")
    assert "historical text" in corrected["historical_stop_label_status"]


def test_structural_absence_is_never_instantiated_or_counted(corrected):
    absent = corrected["structurally_absent"]
    assert len(absent) == 2
    assert {(entry["profile"], entry["contrast"]) for entry in absent} == {
        ("S2", "K6-SEP"), ("S3", "K6-SEP")}
    for entry in absent:
        assert entry["instantiated"] is False
        assert entry["counted"] is False
        assert entry["applicability"] == ELIG.NOT_APPLICABLE
    keys = {(cell["profile"], cell["contrast"]) for cell in corrected["matrix"]}
    assert ("S2", "K6-SEP") not in keys
    assert ("S3", "K6-SEP") not in keys


def test_the_classifier_repair_alone_is_recorded_separately():
    table = _load(CORRECTED_TABLE_PATH)
    view = table["classifier_repair_only_under_the_v0_5_rule"]
    assert view["ineligible_cells"] == 6
    assert view["ineligible_cells_by_profile"] == {"S1": 0, "S2": 3, "S3": 3,
                                                   "S4": 0}
    assert view["ineligible_cells_with_an_empty_reason_list"] == 0
    assert view["executable_genuine_i3_contrasts_per_role"] == {
        "RI": 9, "RL": 9, "RT": 9}
    assert view["roles_without_executable_contrast"] == []


# --------------------------------------------------------------------------
# Positive: the scoring contract.
# --------------------------------------------------------------------------

def test_the_live_scoring_plan_matches_the_registered_boundary(live_plan):
    assert RUNNER.validate_scoring_plan(live_plan) is True
    assert live_plan["common_prefix_token"] == 220
    assert live_plan["common_prefix_token_count"] == 1
    assert live_plan["scoring_context_token_count"] == (
        live_plan["registered_prompt_token_count"] + 1)
    assert live_plan["logit_read_position"] == (
        live_plan["scoring_context_token_count"] - 1)
    assert live_plan["scoring_context_token_ids"][:-1] == \
        live_plan["registered_prompt_token_ids"]
    assert live_plan["scoring_context_token_ids"][-1] == 220
    assert live_plan["sequence_level_model_evaluations"] == 1


def test_scoring_selects_the_registered_complete_candidate_surface(live_plan):
    logits = {token: 0.0 for token in live_plan["discriminant_token_ids"]}
    logits[live_plan["discriminant_token_ids"][4]] = 3.0
    row = RUNNER.score_from_logits(live_plan, logits)
    assert row["selected_complete_candidate_surface"] == " 4"
    assert row["selected_discriminant_token"] == 19
    assert row["sequence_level_model_evaluations"] == 1


def test_s3_reuses_the_s2_vector_and_adds_zero_evaluations(live_plan):
    counters = COUNTERS.P0R1Counters()
    logits = {token: 0.0 for token in live_plan["discriminant_token_ids"]}
    logits[live_plan["discriminant_token_ids"][2]] = 5.0
    s2_row = RUNNER.score_from_logits(live_plan, logits, counters=counters)
    s3_row = RUNNER.reuse_for_s3(live_plan, logits, counters=counters)
    assert s2_row["selected_complete_candidate_surface"] == \
        s3_row["selected_complete_candidate_surface"] == " 2"
    assert s3_row["sequence_level_model_evaluations"] == 0
    assert s3_row["reuses_row_id"] == live_plan["row_id"]
    snapshot = counters.snapshot()
    assert snapshot["s2_scored_rows"] == 1
    assert snapshot["s3_cpu_only_reuse_scored_rows"] == 1
    assert snapshot["non_generative_prefill_evaluations"] == 1
    assert snapshot["common_prefix_tokens_processed"] == 1


def test_the_counter_ontology_separates_identities_from_load_events():
    counters = COUNTERS.P0R1Counters()
    for _ in range(2):
        for role in ("RT", "RL", "RI"):
            counters.add("tokenizer_construction_events", 1)
            counters.observe_identity(
                "distinct_tokenizer_identities_constructed", role)
    snapshot = counters.snapshot()
    assert snapshot["tokenizer_construction_events"] == 6
    assert snapshot["distinct_tokenizer_identities_constructed"] == 3
    aggregate = COUNTERS.aggregate_view(
        {"tokenizer_encoded_sequences": 4956,
         "distinct_tokenizer_identities_constructed": 3},
        [snapshot])
    assert aggregate["counters"]["tokenizer_encoded_sequences"] == 4956
    assert aggregate["counters"][
        "distinct_tokenizer_identities_constructed"] == 3
    assert aggregate["counters"]["tokenizer_construction_events"] == 6


def test_the_model_pilot_refuses_to_start_in_the_calibration_session():
    with pytest.raises(RUNNER.ExecutionRefused):
        RUNNER.run()
    with pytest.raises(RUNNER.ExecutionRefused):
        RUNNER.run(authorization={"p0_r1_pilot_execution_authorized": True})


def test_the_registered_replay_gate_is_refused_in_the_calibration_session():
    assert GATE.main(["--gate"]) == 3


def test_no_p0_r1_result_artifact_exists():
    results = os.path.join(P0_R1_DIR, "results")
    assert not (os.path.isdir(results) and os.listdir(results)), (
        "the calibration session registers P0-R1 and never runs it")


# --------------------------------------------------------------------------
# Section 8 negative mutations. Each is live and each is rejected.
# --------------------------------------------------------------------------

def _factorization_validator(role_entry, candidates, surfaces):
    def validate(result):
        entry = FACT.derive_role_factorization(
            result, candidates, role_entry, surfaces)
        if not entry["eligible"]:
            raise FACT.FactorizationDefect("; ".join(entry["reasons"]))
        return True
    return validate


@pytest.fixture(scope="module")
def solved_candidates(p0_t_result, frozen_corpus):
    by_hash = FACT.corpus_prompts_by_hash(frozen_corpus)
    pairs = FACT.bound_sequences(p0_t_result, by_hash, "RT")
    return FACT.solve_token_pieces(pairs)


@pytest.fixture(scope="module")
def registered_surfaces(registry):
    return FACT.registered_candidate_surfaces(registry)


def test_m01_a_candidate_lacking_the_common_prefix_is_rejected(live_plan):
    def mutate(plan):
        plan["complete_candidate_token_ids"][3] = [18]
    assert_live_mutation_rejected(
        live_plan, mutate, RUNNER.validate_scoring_plan, RUNNER.ScoringDefect,
        "removing the common prefix from one candidate")


def test_m02_a_candidate_with_a_different_prefix_is_rejected(live_plan):
    def mutate(plan):
        plan["complete_candidate_token_ids"][3] = [221, 18]
    assert_live_mutation_rejected(
        live_plan, mutate, RUNNER.validate_scoring_plan, RUNNER.ScoringDefect,
        "giving one candidate a different prefix")


def test_m03_a_candidate_with_a_third_token_is_rejected(live_plan):
    def mutate(plan):
        plan["complete_candidate_token_ids"][3] = [220, 18, 99]
    assert_live_mutation_rejected(
        live_plan, mutate, RUNNER.validate_scoring_plan, RUNNER.ScoringDefect,
        "giving one candidate a third token")


def test_m04_colliding_discriminant_token_ids_are_rejected(live_plan):
    def mutate(plan):
        plan["complete_candidate_token_ids"][3] = [220, 15]
        plan["discriminant_token_ids"][3] = 15
    assert_live_mutation_rejected(
        live_plan, mutate, RUNNER.validate_scoring_plan, RUNNER.ScoringDefect,
        "colliding two discriminant token IDs")


def test_m05_a_prefix_that_is_not_one_u0020_is_rejected(
        registry, p0_t_result, solved_candidates, registered_surfaces):
    """Rejected on the live registry and on the live derivation input."""
    def mutate(document):
        for role in document["scoring_boundary"]["derived_token_identities"][
                "by_role"].values():
            role["common_prefix_bytes"] = "\u0020\u0020"
    assert_live_mutation_rejected(
        registry, mutate, SCHEMAS.validate_scoring_boundary,
        SCHEMAS.SchemaDefect,
        "declaring a two-space common prefix")

    validate = _factorization_validator("RT", solved_candidates,
                                        registered_surfaces)
    assert validate(p0_t_result) is True
    mutated_candidates = dict(solved_candidates)
    mutated_candidates[220] = {"\u00a0"}
    with pytest.raises(FACT.FactorizationDefect):
        _factorization_validator("RT", mutated_candidates,
                                 registered_surfaces)(p0_t_result)


def test_m06_a_digit_token_mapped_to_the_wrong_surface_is_rejected(live_plan):
    def mutate(plan):
        plan["discriminant_token_ids"][3], plan["discriminant_token_ids"][4] = (
            plan["discriminant_token_ids"][4], plan["discriminant_token_ids"][3])
    assert_live_mutation_rejected(
        live_plan, mutate, RUNNER.validate_scoring_plan, RUNNER.ScoringDefect,
        "mapping a digit token to the wrong complete candidate surface")


def test_m07_reading_logits_before_the_common_prefix_is_rejected(live_plan):
    def mutate(plan):
        plan["logit_read_position"] -= 1
    assert_live_mutation_rejected(
        live_plan, mutate, RUNNER.validate_scoring_plan, RUNNER.ScoringDefect,
        "reading logits before the teacher-forced common prefix")


def test_m08_an_s3_row_performing_a_model_evaluation_is_rejected(live_plan):
    s3_plan = dict(copy.deepcopy(live_plan))
    s3_plan["profile"] = "S3"
    s3_plan["sequence_level_model_evaluations"] = 0
    s3_plan["reuses_row_id"] = live_plan["row_id"]

    def mutate(plan):
        plan["sequence_level_model_evaluations"] = 1
    assert_live_mutation_rejected(
        s3_plan, mutate, RUNNER.validate_scoring_plan, RUNNER.ScoringDefect,
        "letting S3 perform an additional model evaluation")


def test_m09_changing_the_registered_tie_break_order_is_rejected(live_plan):
    def mutate(plan):
        plan["tie_break_order"] = list(reversed(plan["tie_break_order"]))
    assert_live_mutation_rejected(
        live_plan, mutate, RUNNER.validate_scoring_plan, RUNNER.ScoringDefect,
        "reversing the registered digit-order tie break")


def _matrix_validator(matrix):
    return ELIG.validate_matrix(matrix, roles=("RT", "RL", "RI"))


def test_m10_an_s2_failure_propagating_to_s1_is_rejected(corrected):
    live = corrected["matrix"]

    def mutate(matrix):
        for cell in matrix:
            if cell["profile"] == "S1" and cell["role"] == "RT":
                cell["status"] = ELIG.INELIGIBLE
                cell["reasons"] = [ELIG.reason(
                    "S2_S3_FIRST_DISCRIMINATIVE_TOKEN_FACTORIZATION_FAILED",
                    "the S2 candidate set failed", role="RT", profile="S2")]
                return
    assert_live_mutation_rejected(
        live, mutate, _matrix_validator, ELIG.EligibilityDefect,
        "propagating an S2 failure onto an S1 cell")


def test_m11_an_s1_failure_propagating_to_s2_and_s3_is_rejected(corrected):
    live = corrected["matrix"]

    def mutate(matrix):
        for cell in matrix:
            if cell["profile"] in ("S2", "S3") and cell["role"] == "RL":
                cell["status"] = ELIG.INELIGIBLE
                cell["reasons"] = [ELIG.reason(
                    "S1_CANDIDATE_SURFACES_NOT_SINGLE_TOKEN",
                    "the S1 label surfaces failed", role="RL", profile="S1")]
                return
    assert_live_mutation_rejected(
        live, mutate, _matrix_validator, ELIG.EligibilityDefect,
        "propagating an S1 failure onto an S2/S3 cell")


def test_m12_one_roles_failure_propagating_to_another_is_rejected(corrected):
    live = corrected["matrix"]

    def mutate(matrix):
        for cell in matrix:
            if cell["role"] == "RI":
                cell["status"] = ELIG.INELIGIBLE
                cell["reasons"] = [ELIG.reason(
                    "S2_S3_FIRST_DISCRIMINATIVE_TOKEN_FACTORIZATION_FAILED",
                    "role RT failed", role="RT")]
                return
    assert_live_mutation_rejected(
        live, mutate, _matrix_validator, ELIG.EligibilityDefect,
        "propagating one role's failure onto another role")


def test_m13_an_ineligible_row_without_a_reason_is_rejected(corrected):
    live = corrected["matrix"]

    def mutate(matrix):
        matrix[0]["status"] = ELIG.INELIGIBLE
        matrix[0]["reasons"] = []
    assert_live_mutation_rejected(
        live, mutate, _matrix_validator, ELIG.EligibilityDefect,
        "emitting an ineligible row with an empty reason list")


def test_m14_s4_satisfying_target_role_executability_is_rejected(corrected):
    live = corrected["matrix"]
    executable = ELIG.target_role_executability(live)
    for role in ("RT", "RL", "RI"):
        assert not any(entry.startswith("S4/") for entry in executable[role])

    def mutate(matrix):
        for cell in matrix:
            if cell["profile"] == "S4":
                cell["genuine_gate_bearing_i3_contrast"] = True
                return
    assert_live_mutation_rejected(
        live, mutate, _matrix_validator, ELIG.EligibilityDefect,
        "letting S4 satisfy target-role executability")


def test_m15_instantiating_or_counting_a_not_applicable_row_is_rejected(
        corrected, p0_t_result):
    live = corrected["matrix"]

    def mutate(matrix):
        matrix[0]["status"] = ELIG.NOT_APPLICABLE
    assert_live_mutation_rejected(
        live, mutate, _matrix_validator, ELIG.EligibilityDefect,
        "counting a not_applicable row as a cell status")

    records = p0_t_result["records"]
    assert ELIG.structural_absence_index(records)
    mutated = copy.deepcopy(records)
    for record in mutated:
        if record.get("structural_absence"):
            record["members"] = [{"role_in_pair": "baseline"}]
            break
    with pytest.raises(ELIG.EligibilityDefect):
        ELIG.structural_absence_index(mutated)


def test_m16_editing_the_historical_result_receipt_or_disposition_is_rejected(
        tmp_path, p0_t_result):
    """A single altered byte in the consumed P0 namespace stops the replay."""
    assert FACT.verify_immutable_sources()

    for repo_path in (P0_RESULT_REPO_PATH, P0_RECEIPT_REPO_PATH,
                      P0_DISPOSITION_REPO_PATH):
        root = tmp_path / repo_path.replace("/", "_")
        for source in FACT.IMMUTABLE_SOURCES:
            target = root / source.replace("/", os.sep)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(REPO_ROOT, *source.split("/")),
                            str(target))
        victim = root / repo_path.replace("/", os.sep)
        raw = victim.read_bytes()
        assert FACT.source_identity(repo_path, root=str(root))["sha256"] == \
            FACT.IMMUTABLE_SOURCES[repo_path]["sha256"]
        victim.write_bytes(raw + b" ")
        with pytest.raises(FACT.FactorizationDefect):
            FACT.verify_immutable_sources(root=str(root))
        with pytest.raises(FACT.FactorizationDefect):
            FACT.load_immutable(repo_path, root=str(root))

    # The published P0 counter snapshot is equally protected.
    live = {"historical_p0_t_snapshot": dict(p0_t_result["counters"])}

    def validator(document):
        return SCHEMAS.validate_historical_counter_snapshot(
            document["historical_p0_t_snapshot"])

    def mutate(document):
        document["historical_p0_t_snapshot"][
            "tokenizer_encoded_sequences"] = 4900
    assert_live_mutation_rejected(
        live, mutate, validator, SCHEMAS.SchemaDefect,
        "editing the historical P0-T counter snapshot")


def test_m17_weakening_or_removing_the_equivalence_assertion_is_rejected(
        registry):
    def remove(document):
        document["scoring_boundary"].pop("equivalence_proof")
    assert_live_mutation_rejected(
        registry, remove, SCHEMAS.validate_equivalence_registration,
        SCHEMAS.SchemaDefect, "removing the equivalence assertion")

    def weaken(document):
        document["scoring_boundary"]["equivalence_proof"]["identity"] = (
            "P(u, v_d | x) is approximately P(v_d | x, u)")
    assert_live_mutation_rejected(
        registry, weaken, SCHEMAS.validate_equivalence_registration,
        SCHEMAS.SchemaDefect, "weakening the equivalence identity")

    def narrow(document):
        document["scoring_boundary"]["equivalence_proof"][
            "does_not_extend_to"] = ["free generation"]
    assert_live_mutation_rejected(
        registry, narrow, SCHEMAS.validate_equivalence_registration,
        SCHEMAS.SchemaDefect, "weakening the equivalence claim boundary")


def test_m18_changing_the_frozen_corpus_or_a_member_hash_is_rejected(
        frozen_corpus, tmp_path):
    def mutate(corpus):
        corpus["rows"][0]["members"][0]["prompt"] += " "
    assert_live_mutation_rejected(
        frozen_corpus, mutate, SCHEMAS.validate_corpus_binding,
        SCHEMAS.SchemaDefect, "changing a frozen corpus prompt")

    def drop_row(corpus):
        corpus["rows"].pop()
    assert_live_mutation_rejected(
        frozen_corpus, drop_row, SCHEMAS.validate_corpus_binding,
        SCHEMAS.SchemaDefect, "removing a frozen corpus row")

    def rehash(corpus):
        member = corpus["rows"][2]["members"][1]
        member["prompt_sha256"] = hashlib.sha256(b"other").hexdigest()
    assert_live_mutation_rejected(
        frozen_corpus, rehash, SCHEMAS.validate_corpus_binding,
        SCHEMAS.SchemaDefect, "rewriting a frozen corpus member hash")

    root = tmp_path / "corpus-bytes"
    for source in FACT.IMMUTABLE_SOURCES:
        target = root / source.replace("/", os.sep)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.path.join(REPO_ROOT, *source.split("/")),
                        str(target))
    victim = root / P0_CORPUS_REPO_PATH.replace("/", os.sep)
    victim.write_bytes(victim.read_bytes() + b"\n")
    with pytest.raises(FACT.FactorizationDefect):
        FACT.load_immutable(FACT.CORPUS_PATH, root=str(root))


def test_m19_resetting_a_counter_or_omitting_a_construction_event_is_rejected():
    live = {
        "previous": {"tokenizer_encoded_sequences": 12,
                     "tokenizer_construction_events": 3,
                     "distinct_tokenizer_identities_constructed": 3},
        "current": {"tokenizer_encoded_sequences": 20,
                    "tokenizer_construction_events": 3,
                    "distinct_tokenizer_identities_constructed": 3},
    }

    def validator(document):
        return SCHEMAS.validate_counter_progression(
            document["previous"], document["current"])

    def reset(document):
        document["current"]["tokenizer_encoded_sequences"] = 0
    assert_live_mutation_rejected(
        live, reset, validator, SCHEMAS.SchemaDefect,
        "resetting a cumulative counter")

    def omit(document):
        document["current"]["tokenizer_construction_events"] = 2
        document["previous"]["tokenizer_construction_events"] = 2
    assert_live_mutation_rejected(
        live, omit, validator, SCHEMAS.SchemaDefect,
        "omitting a tokenizer construction event")

    counters = COUNTERS.P0R1Counters({"tokenizer_encoded_sequences": 5})
    with pytest.raises(COUNTERS.CounterDefect):
        counters.merge_cumulative({"tokenizer_encoded_sequences": 9})
    with pytest.raises(COUNTERS.CounterDefect):
        counters.add("distinct_tokenizer_identities_constructed", 1)


def test_m20_a_formal_flag_becoming_true_or_non_null_is_rejected(receipt):
    live = receipt["authority_flags"]

    for flag in ("seed_authorized", "bank_authorized",
                 "confirmation_access_authorized", "winner_selected",
                 "od2_resolved", "ur22_resolved", "rp_selected",
                 "evidence_row_written", "formal_execution_authorized",
                 "frozen"):
        def mutate(document, flag=flag):
            document[flag] = True
        assert_live_mutation_rejected(
            live, mutate, SCHEMAS.validate_authority_flags,
            SCHEMAS.SchemaDefect, "setting %s true" % flag)

    for item in ("interface_selected", "positive_reference", "rp_wrapper"):
        def mutate(document, item=item):
            document[item] = "S1"
        assert_live_mutation_rejected(
            live, mutate, SCHEMAS.validate_authority_flags,
            SCHEMAS.SchemaDefect, "resolving %s" % item)

    def consume(document):
        document["p0_r1_pilot_execution_consumed"] = True
    assert_live_mutation_rejected(
        live, consume, SCHEMAS.validate_authority_flags, SCHEMAS.SchemaDefect,
        "consuming the P0-R1 execution authorization in the drafting session")

    def ledger(document):
        document["evidence_ledger_last_row"] = "EV-0017"
    assert_live_mutation_rejected(
        live, ledger, SCHEMAS.validate_authority_flags, SCHEMAS.SchemaDefect,
        "advancing the evidence ledger tail")


# --------------------------------------------------------------------------
# Registration integrity.
# --------------------------------------------------------------------------

def test_the_registration_state_is_awaiting_the_replay_gate(p0_r1_protocol,
                                                            receipt):
    state = "STUDY3_P0_R1_REGISTERED_AWAITING_REPLAY_GATE"
    assert p0_r1_protocol["state"] == state
    assert receipt["state"] == state
    legal = p0_r1_protocol["legal_status"]
    assert legal["formal_execution_authorized"] is False
    assert legal["p0_r1_pilot_execution_authorized"] is True
    assert legal["p0_r1_pilot_execution_consumed"] is False
    assert legal["draft_v0_6_frozen"] is False
    assert legal["draft_v0_6_reviewed"] is False
    assert legal["interface_selected"] is None
    assert legal["evidence_ledger_last_row"] == "EV-0016"


def test_the_receipt_binds_authority_candidate_corpus_and_code(receipt):
    assert SCHEMAS.validate_document(
        receipt, SCHEMAS.PRE_EXECUTION_RECEIPT_SCHEMA, "receipt") is True
    authority = receipt["authority"]
    assert authority["bytes"] == 19632
    assert authority["sha256"] == (
        "f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200845ddc19d2")
    assert authority["byte_identical"] is True
    assert authority["lf_only"] is True
    assert receipt["corpus"]["row_count"] == 35
    assert receipt["corpus"]["member_count"] == 70
    assert len(receipt["p0_t_source_artifacts"]) == 4
    assert len(receipt["model_and_tokenizer_revisions"]) == 3
    for blob in receipt["code_blobs"]:
        assert blob["present"] is True, blob["path"]
        assert blob["carries_cr"] is False, blob["path"]
    assert receipt["container"]["image_digest"] is None
    for name, value in receipt["operations_in_the_calibration_session"].items():
        assert value == 0, name


def test_the_p0_r1_package_never_edits_the_consumed_p0_namespace():
    for name in sorted(os.listdir(P0_R1_DIR)):
        if not name.endswith(".py"):
            continue
        source = open(os.path.join(P0_R1_DIR, name), encoding="utf-8").read()
        stripped = source.replace("p0_tokenizer_gate_result", "").replace(
            "p0_tokenizer_gate_receipt", "")
        assert "p0_tokenizer_gate" not in stripped, (
            "%s imports or drives the historical buggy classifier" % name)
    runner = open(os.path.join(P0_R1_DIR, "p0_r1_model_runner.py"),
                  encoding="utf-8").read()
    assert "import p0_tokenizer_gate" not in runner
    assert "evaluate_eligibility" not in runner


def test_the_registered_caps_and_allocation_are_unchanged(p0_r1_protocol):
    caps = p0_r1_protocol["caps"]
    assert caps["non_generative_prefill_evaluations"] == 180
    assert caps["s4_generation_calls"] == 12
    assert caps["total_sequence_level_model_evaluation_equivalents"] == 228
    assert caps["s1_scored_rows"] == 162
    assert caps["s2_scored_rows"] == 18
    assert caps["s3_cpu_only_reuse_scored_rows"] == 18
    assert caps["s4_scored_generation_rows"] == 12
    assert caps["total_scored_rows"] == 210
    assert caps["hosted_provider_inference_calls"] == 0
    assert caps["seeds_drawn"] == 0
    assert caps["bank_rows_written"] == 0
    assert caps["positive_reference_operations"] == 0
    assert p0_r1_protocol["smoke_exact_allocation"][
        "non_generative_prefill_evaluations"] == 60
    allocation = p0_r1_protocol["allocation"]
    assert allocation[
        "the_common_prefix_changes_token_processing_not_evaluations"] is True


def test_the_summarizer_preserves_every_row_and_reconciles_tokens(live_plan):
    logits = {token: float(index)
              for index, token in enumerate(live_plan["discriminant_token_ids"])}
    s2_row = RUNNER.score_from_logits(live_plan, logits)
    s3_row = RUNNER.reuse_for_s3(live_plan, logits)
    summary = SUMMARIZE.summarize([s2_row, s3_row],
                                  s4_completions=["raw"], exceptions=[])
    assert summary["rows_preserved"] == 2
    assert summary["raw_s4_completions_preserved"] == 1
    assert summary["by_profile"]["S3"][
        "sequence_level_model_evaluations"] == 0
    assert summary["no_output_conditioned_retry_or_row_replacement"] is True

    with pytest.raises(SUMMARIZE.SummaryDefect):
        SUMMARIZE.summarize([s2_row, s2_row])
