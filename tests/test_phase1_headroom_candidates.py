"""Model-free tests for the Phase 1 capability-headroom candidate bank."""

import ast
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

import pytest


ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jspace_observation.headroom_candidates import (  # noqa: E402
    DIFFICULTY_BANDS,
    ITEMS_PER_CELL,
    SPLITS,
    TASK_FAMILIES,
    TOP_LEVEL_FIELDS,
    candidate_bank_sha256,
    candidate_count_matrix,
    candidate_schema,
    derive_run_seed,
    generate_candidate_bank,
    method_suitability_counts,
    serialize_candidate_bank,
    validate_candidate_bank,
)


DATA_PATH = ROOT / "data" / "phase1_task_headroom_candidates.jsonl"
SCHEMA_PATH = ROOT / "data" / "phase1_task_headroom_candidate.schema.json"
TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@pytest.fixture(scope="module")
def records():
    return generate_candidate_bank()


def test_exact_schema_unique_ids_and_total(records):
    assert len(records) == 450
    assert all(set(record) == set(TOP_LEVEL_FIELDS) for record in records)
    task_ids = [record["task_id"] for record in records]
    assert len(task_ids) == len(set(task_ids))
    validate_candidate_bank(records)

    schema = candidate_schema()
    assert schema["required"] == list(TOP_LEVEL_FIELDS)
    assert schema["additionalProperties"] is False


def test_family_band_split_counts_and_template_isolation(records):
    expected_splits = {split: ITEMS_PER_CELL for split in SPLITS}
    matrix = candidate_count_matrix(records)
    for family in TASK_FAMILIES:
        for band in DIFFICULTY_BANDS:
            assert matrix[family][band] == expected_splits

            split_templates = []
            for split in SPLITS:
                templates = {
                    record["template_family_id"]
                    for record in records
                    if (
                        record["task_family"],
                        record["difficulty_band"],
                        record["split"],
                    )
                    == (family, band, split)
                }
                assert len(templates) == 5
                split_templates.append(templates)
            assert not (split_templates[0] & split_templates[1])
            assert not (split_templates[0] & split_templates[2])
            assert not (split_templates[1] & split_templates[2])


def test_answers_and_concepts_are_counterbalanced(records):
    cells = defaultdict(list)
    for record in records:
        cells[
            (
                record["task_family"],
                record["difficulty_band"],
                record["split"],
            )
        ].append(record)

    for cell_records in cells.values():
        answer_counts = Counter(
            record["registered_answer"] for record in cell_records
        )
        concept_counts = Counter(
            record["intermediate_concept"] for record in cell_records
        )
        assert len(answer_counts) >= 2
        assert len(concept_counts) >= 2
        assert max(answer_counts.values()) <= 5
        assert max(concept_counts.values()) <= 5


def test_references_are_mechanical_and_all_facts_are_in_prompt(records):
    validate_candidate_bank(records)
    for record in records:
        metadata = record["metadata"]
        pair = record["clean_corrupted_pair"]
        assert all(fact in record["question"] for fact in metadata["facts"])
        assert all(
            fact in pair["corrupted"]["question"]
            for fact in metadata["corrupted_facts"]
        )
        assert metadata["difficulty_parameters"]["external_knowledge_required"] is False

    factual = [
        record
        for record in records
        if record["task_family"] == "prompt_grounded_two_hop_factual"
    ]
    assert all(
        record["metadata"]["difficulty_parameters"]["lookup_hops"] == 2
        for record in factual
    )


def test_clean_corrupted_pairs_are_minimal_aligned_and_answer_changing(records):
    for record in records:
        pair = record["clean_corrupted_pair"]
        clean = pair["clean"]
        corrupted = pair["corrupted"]
        clean_tokens = TOKEN_RE.findall(clean["question"])
        corrupted_tokens = TOKEN_RE.findall(corrupted["question"])
        assert len(clean_tokens) == len(corrupted_tokens)
        assert sum(
            left != right
            for left, right in zip(clean_tokens, corrupted_tokens)
        ) == 1
        assert clean["registered_answer"] != corrupted["registered_answer"]
        assert pair["intervention"]["surface_token_mismatches"] == 1
        assert (
            pair["intervention"]["position_alignment"]
            == "same_rendered_template_slot"
        )
        assert record["patching_suitability"]["both_baselines_correct_required"]
        assert record["patching_suitability"]["scan"] == "layer_by_position"


def test_entities_are_disjoint_across_splits(records):
    by_family_split = defaultdict(set)
    for record in records:
        by_family_split[(record["task_family"], record["split"])].update(
            record["metadata"]["entity_ids"]
        )

    for family in TASK_FAMILIES:
        split_sets = [by_family_split[(family, split)] for split in SPLITS]
        assert not (split_sets[0] & split_sets[1])
        assert not (split_sets[0] & split_sets[2])
        assert not (split_sets[1] & split_sets[2])


def test_controls_and_token_registration_are_preregistered(records):
    by_id = {record["task_id"]: record for record in records}
    for record in records:
        requirement = record["concept_tokenization_requirement"]
        assert requirement["surface_form"] == record["intermediate_concept"]
        assert requirement["required_token_count"] == 1
        assert requirement["registration_status"].startswith("pending_")

        controls = record["metadata"]["controls"]
        matched = by_id[controls["matched_control_task_id"]]
        assert matched["template_family_id"] == record["template_family_id"]
        assert matched["registered_answer"] != record["registered_answer"]
        assert matched["intermediate_concept"] != record["intermediate_concept"]
        assert controls["prompt_echo_control"]["required"] is True


def test_method_suitability_counts_and_arithmetic_boundary(records):
    assert method_suitability_counts(records) == {
        "jlens": 450,
        "patching": 450,
        "ablation": 360,
        "ability_matching": 360,
    }
    arithmetic = [
        record for record in records if record["task_family"] == "arithmetic"
    ]
    assert len(arithmetic) == 90
    assert all(
        record["jlens_suitability"]["evidence_role"] == "sanity_only"
        for record in arithmetic
    )
    assert all(
        not record["ablation_suitability"]["design_candidate"]
        and not record["ability_match_suitability"]["design_candidate"]
        for record in arithmetic
    )


def test_entity_records_require_typed_locked_evaluation(records):
    entity_records = [
        record
        for record in records
        if record["metadata"]["answer_type"] == "entity"
    ]
    assert len(entity_records) == 270
    assert all(
        record["metadata"]["future_evaluation"]["parser_route"]
        == "separately_locked_typed_entity_evaluator_required"
        for record in entity_records
    )
    wrong_cot = [
        record
        for record in records
        if record["task_family"] == "wrong_cot_error_detection"
    ]
    assert all(
        record["metadata"]["answer_type"] == "numeric_step_code"
        and record["metadata"]["future_evaluation"]["numeric_codebook"]
        for record in wrong_cot
    )


def test_generation_and_seed_rule_are_deterministic(records):
    regenerated = generate_candidate_bank()
    assert serialize_candidate_bank(records) == serialize_candidate_bank(regenerated)
    assert candidate_bank_sha256(records) == (
        "acf59ec44b7afb73c03392d2c9b7223eff7311e29e2261ff0d65b38a3a416407"
    )
    assert derive_run_seed(
        "p1hd-arith-easy-calibration-01",
        "visible_cot",
        256,
        "deterministic",
        0,
    ) == 4349202314845195451


def test_checked_in_bank_and_schema_are_current(records):
    assert DATA_PATH.read_text(encoding="utf-8") == serialize_candidate_bank(records)
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) == candidate_schema()

    loaded = [
        json.loads(line)
        for line in DATA_PATH.read_text(encoding="utf-8").splitlines()
    ]
    assert loaded == records
    validate_candidate_bank(loaded)


def test_generator_has_no_target_model_or_network_dependency():
    source_path = ROOT / "src" / "jspace_observation" / "headroom_candidates.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots <= {
        "__future__",
        "collections",
        "hashlib",
        "json",
        "pathlib",
        "re",
        "typing",
    }
    lowered = source.lower()
    for forbidden in (
        "import torch",
        "import transformers",
        "import requests",
        "import openai",
        "import azure",
    ):
        assert forbidden not in lowered
