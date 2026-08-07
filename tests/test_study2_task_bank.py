"""Independent reconstruction tests for frozen Study 2 task banks."""

from __future__ import annotations

import ast
import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))

import study2_protocol as s2  # noqa: E402
import study2_task_bank as generator  # noqa: E402

DATA = ROOT / "studies/study2/data"


@pytest.fixture(scope="module")
def report() -> dict:
    return s2.verify_task_banks(ROOT, require_manifest=True)


def test_exact_role_and_cell_counts(report: dict) -> None:
    assert report["role_counts"] == s2.EXPECTED_ROLE_COUNTS
    for role, filename in s2.BANK_FILES.items():
        rows = s2.load_jsonl(DATA / filename)
        pair_rows = role.startswith("mechanistic")
        depths = s2.COMPOSITIONAL_DEPTHS if pair_rows else s2.DEPTHS
        for family in s2.FAMILIES:
            for depth in depths:
                assert sum(row["family"] == family and row["depth"] == depth for row in rows) == s2.EXPECTED_CELL_COUNTS[role]


def test_manifest_hashes_bytes_counts_and_manifest_last_claim(report: dict) -> None:
    manifest = report["manifest"]
    assert manifest["schema_version"] == s2.MANIFEST_VERSION
    assert manifest["status"] in {"CANDIDATE_MODEL_FREE_BANKS", "FROZEN_MODEL_FREE_BANKS"}
    assert manifest["determinism"] == {
        "algorithm": "sha256_counter_mode_with_rejection_randbelow",
        "python_hash_used": False,
        "rng_state_used": False,
        "manifest_written_last": True,
    }
    for role, row in manifest["files"].items():
        path = ROOT / row["path"]
        assert row["rows"] == s2.EXPECTED_ROLE_COUNTS[role]
        assert row["bytes"] == path.stat().st_size
        assert row["sha256"] == s2.sha256_file(path)


def test_every_task_ground_truth_trace_and_prompt_is_independently_recomputed() -> None:
    for role in ("development", "behavioral_confirmation"):
        for row in s2.load_jsonl(DATA / s2.BANK_FILES[role]):
            s2.verify_task_row(row)
            assert row["prompts"]["NT"].endswith("Answer:")
            assert set(row["prompts"]) == ({"NT"} if row["depth"] == 1 else {"NT", "PT", "WT"} if row["depth"] == 2 else {"NT", "PT", "WT", "ST"})
            if row["depth"] >= 2:
                assert row["counterfactual"]["implied_final_state"] in row["option_values"]
                assert row["counterfactual"]["implied_final_state"] != row["ground_truth"]["final_state"]


def test_every_pair_recombination_and_control_is_independently_recomputed() -> None:
    for role in ("mechanistic_development", "mechanistic_candidate_confirmation"):
        for row in s2.load_jsonl(DATA / s2.BANK_FILES[role]):
            s2.verify_pair_row(row)
            primary = row["primary"]
            assert len({primary["donor_answer"], primary["recipient_answer"], primary["recombinant_answer"]}) == 3
            assert len({primary["donor_label"], primary["recipient_label"], primary["recombinant_label"]}) == 3
            assert row["controls"]["no_op_donor"] == primary["recipient"]
            assert row["controls"]["same_intermediate_donor"]["ground_truth"]["pre_answer_intermediate"] == primary["recipient_intermediate"]
            assert row["controls"]["same_answer_donor"]["ground_truth"]["final_state"] == primary["recipient_answer"]
            assert row["controls"]["same_answer_donor"]["ground_truth"]["pre_answer_intermediate"] != primary["recipient_intermediate"]
            assert row["controls"]["random_donor"]["ground_truth"]["pre_answer_intermediate"] != primary["recipient_intermediate"]
            assert row["controls"]["random_donor"]["ground_truth"]["final_state"] != primary["recipient_answer"]


def test_balance_tables_are_exact_and_all_registered_spreads_are_at_most_one(report: dict) -> None:
    for cell, row in report["balance"].items():
        assert set(row["counts"]["labels"].values()) == {s2.EXPECTED_CELL_COUNTS[cell.split("/")[0]] // 4}
        assert set(row["counts"]["templates"].values()) == {s2.EXPECTED_CELL_COUNTS[cell.split("/")[0]] // 2}
        for field in ("start", "pre_answer", "final", "final_operator"):
            values = row["counts"][field].values()
            assert max(values) - min(values) <= 1
        for field_table in row["conditional_label_tables"].values():
            for label_counts in field_table.values():
                assert max(label_counts.values()) - min(label_counts.values()) <= 1


def test_mechanistic_hash_order_has_balanced_front_128_and_back_128() -> None:
    for role in ("mechanistic_development", "mechanistic_candidate_confirmation"):
        rows = s2.load_jsonl(DATA / s2.BANK_FILES[role])
        for family in s2.FAMILIES:
            for depth in s2.COMPOSITIONAL_DEPTHS:
                cell = sorted(
                    (row for row in rows if row["family"] == family and row["depth"] == depth),
                    key=lambda row: row["pair_semantic_id"],
                )
                assert len(cell) == 256
                assert all(row["hash_partition"] == "front" for row in cell[:128])
                assert all(row["hash_partition"] == "back" for row in cell[128:])
                for subset in (cell[:128], cell[128:]):
                    assert Counter(row["template_id"] for row in subset) == Counter({"T-A": 64, "T-B": 64})
                    assert Counter(row["primary"]["recipient_label"] for row in subset) == Counter({label: 32 for label in s2.LABELS})


def test_zero_semantic_and_protected_prompt_overlap(report: dict) -> None:
    assert all(value == 0 for value in report["semantic_overlap_counts"].values())
    assert report["protected_prompt_overlap"] == {"exact": 0, "normalized": 0}
    assert report["protected_prompt_count"] > 0


def test_stage_t_selector_contains_only_tokenizer_mechanics_and_frozen_hashes() -> None:
    forbidden = {"logit", "accuracy", "activation", "probe", "lens", "patch", "correct"}
    for role in ("mechanistic_development", "mechanistic_candidate_confirmation"):
        for row in s2.load_jsonl(DATA / s2.BANK_FILES[role]):
            selector = json.dumps(row["stage_t_selector"], sort_keys=True).casefold()
            assert not any(word in selector for word in forbidden)
            assert row["stage_t_selector"]["sort_key"] == row["pair_semantic_id"]
            assert row["stage_t_selector"]["outcome_fields_allowed"] == []


def test_generator_uses_sha256_counter_mode_not_python_random_or_hash() -> None:
    source_path = ROOT / "src/jspace_observation/study2_task_bank.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            calls.append(node.func.id if isinstance(node.func, ast.Name) else "")
    assert "random" not in imported
    assert "hash" not in calls
    assert "hashlib.sha256" in source
    assert s2.SEEDS == s2.load_json(ROOT / "studies/study2/protocol/reasoning_internalization_protocol.json")["task_design"]["seeds"]


def test_generator_repeats_registered_development_rows_byte_exactly() -> None:
    first = generator.build_role_rows("development")
    second = generator.build_role_rows("development")
    assert b"".join(s2.canonical_json_bytes(row) for row in first) == b"".join(s2.canonical_json_bytes(row) for row in second)
    assert b"".join(s2.canonical_json_bytes(row) for row in first) == (DATA / "development.jsonl").read_bytes()


def test_independent_verifier_rejects_ground_truth_recombination_and_selector_drift() -> None:
    task = s2.load_jsonl(DATA / "development.jsonl")[0]
    mutated_task = copy.deepcopy(task)
    mutated_task["ground_truth"]["final_state"] = (task["ground_truth"]["final_state"] + 1) % len(task["state_space"])
    with pytest.raises(s2.ProtocolError):
        s2.verify_task_row(mutated_task)

    pair = s2.load_jsonl(DATA / "mechanistic_development_candidate_pairs.jsonl")[0]
    mutated_pair = copy.deepcopy(pair)
    mutated_pair["primary"]["recombinant_answer"] = mutated_pair["primary"]["donor_answer"]
    with pytest.raises(s2.ProtocolError):
        s2.verify_pair_row(mutated_pair)
    selector_drift = copy.deepcopy(pair)
    selector_drift["stage_t_selector"]["outcome_fields_allowed"] = ["accuracy"]
    with pytest.raises(s2.ProtocolError):
        s2.verify_pair_row(selector_drift)
