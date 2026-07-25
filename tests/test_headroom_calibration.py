"""Targeted tests for the Phase 1.0C Track B headroom calibration module."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from jspace_observation import headroom_calibration as hc  # noqa: E402

FROZEN_TIME = "2026-07-25T00:00:00Z"


@pytest.fixture(scope="module")
def bank() -> list[dict[str, Any]]:
    return hc.load_task_bank(hc.DEFAULT_BANK_PATH)


@pytest.fixture(scope="module")
def selected(bank: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return hc.select_calibration_items(bank)


def _run(mode: str, output_root: Path, **overrides: Any) -> dict[str, Any]:
    config = hc.RunConfig(
        mode=mode,
        output_root=output_root,
        bank_path=hc.DEFAULT_BANK_PATH,
        repo_root=ROOT,
        frozen_time=FROZEN_TIME,
        code_commit="0" * 40,
        image_digest="sha256:" + "0" * 64,
        hardware="cpu-unit-test",
        **overrides,
    )
    return hc.run_calibration(config)


@pytest.fixture(scope="module")
def self_test_pack(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_root = tmp_path_factory.mktemp("selftest_pack")
    result = _run("self-test", output_root, backend=hc.SelfTestBackend())
    return Path(result["output_dir"])


@pytest.fixture(scope="module")
def plan_pack(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_root = tmp_path_factory.mktemp("plan_pack")
    result = _run("plan", output_root)
    assert result["decision"]["status"] == "BLOCKED"
    return Path(result["output_dir"])


# ---------------------------------------------------------------------------
# frozen constants
# ---------------------------------------------------------------------------


def test_frozen_identifiers() -> None:
    assert hc.PHASE == "1.0C"
    assert hc.TRACK == "track-b"
    assert hc.MODEL_ID == "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    assert hc.MODEL_REVISION == "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
    assert hc.CONDITIONS == ("r1_style_thinking", "visible_cot")
    assert set(hc.DEFERRED_CONDITIONS) == {
        "answer_prefill",
        "empty_think_prefill",
        "postprocessed",
        "prompt_only_raw_strict",
        "stopped",
    }


def test_frozen_thresholds() -> None:
    assert hc.REQUIRED_CELL_N == 10
    assert hc.ACCURACY_BAND_LOW == pytest.approx(0.70)
    assert hc.ACCURACY_BAND_HIGH == pytest.approx(0.90)
    assert hc.MIN_CORRECT_COUNT == 7
    assert hc.MAX_TRUNCATION_RATE == pytest.approx(0.10)
    assert hc.MAX_NO_ANSWER_RATE == pytest.approx(0.10)
    assert hc.REVIEW_SAMPLE_FRACTION == pytest.approx(0.10)
    assert hc.SELECTION_SEED == 20260725


def test_parser_v2_is_never_authoritative() -> None:
    assert hc.TRIAGE_AUTHORITY == "screening_only_not_locked"
    assert "failed" in hc.PARSER_V2_LOCKED_VALIDATION_STATUS


def test_prohibited_interpretations_cover_the_claim_boundary() -> None:
    joined = " ".join(hc.PROHIBITED_INTERPRETATIONS).lower()
    for token in ("hidden reasoning", "j-space", "rq1", "pass@k", "parser v2"):
        assert token in joined


def test_artifact_and_metric_contracts() -> None:
    assert hc.ARTIFACT_FILES[-1] == "artifact_manifest.json"
    assert len(hc.ARTIFACT_FILES) == 10
    assert list(hc.METRICS_HEADER) == [
        "run_id",
        "phase",
        "track",
        "metric",
        "stratum",
        "condition",
        "n",
        "numerator",
        "denominator",
        "value",
        "ci_lower",
        "ci_upper",
        "threshold",
        "passed",
        "not_applicable_reason",
    ]


# ---------------------------------------------------------------------------
# deterministic selection
# ---------------------------------------------------------------------------


def test_selection_is_150_unique_calibration_items(selected: list[dict[str, Any]]) -> None:
    assert len(selected) == 150
    ids = [item["task_id"] for item in selected]
    assert len(set(ids)) == 150
    assert {item["split"] for item in selected} == {"calibration"}


def test_selection_grid_counts(selected: list[dict[str, Any]]) -> None:
    summary = hc.selection_summary(selected)
    assert summary["item_count"] == 150
    assert summary["split"] == "calibration"
    assert summary["selection_seed"] == hc.SELECTION_SEED
    assert summary["per_family"] == {family: 30 for family in hc.TASK_FAMILIES}
    assert summary["per_band"] == {band: 50 for band in hc.DIFFICULTY_BANDS}
    assert len(summary["per_family_band"]) == 15
    assert set(summary["per_family_band"].values()) == {10}


def test_selection_is_ordered_and_order_independent(bank: list[dict[str, Any]]) -> None:
    first = [item["task_id"] for item in hc.select_calibration_items(bank)]
    second = [item["task_id"] for item in hc.select_calibration_items(list(reversed(bank)))]
    assert first == second
    grid = [
        (item["task_family"], item["difficulty_band"], item["task_id"])
        for item in hc.select_calibration_items(bank)
    ]
    family_rank = {family: index for index, family in enumerate(hc.TASK_FAMILIES)}
    band_rank = {band: index for index, band in enumerate(hc.DIFFICULTY_BANDS)}
    keys = [(family_rank[f], band_rank[b], t) for f, b, t in grid]
    assert keys == sorted(keys)


def test_selection_digest_is_stable(selected: list[dict[str, Any]]) -> None:
    summary = hc.selection_summary(selected)
    joined = "\n".join(sorted(item["task_id"] for item in selected)) + "\n"
    assert summary["task_ids_sha256"] == hashlib.sha256(joined.encode("utf-8")).hexdigest()


def test_held_out_splits_are_never_selected(selected: list[dict[str, Any]]) -> None:
    for item in selected:
        assert item["split"] not in {"confirmation", "mechanistic"}


def test_selection_rejects_a_short_cell(bank: list[dict[str, Any]]) -> None:
    truncated = [
        item
        for item in bank
        if not (
            item["split"] == "calibration"
            and item["task_family"] == "arithmetic"
            and item["difficulty_band"] == "easy"
            and item["task_id"].endswith("-01")
        )
    ]
    with pytest.raises(ValueError):
        hc.select_calibration_items(truncated)


# ---------------------------------------------------------------------------
# prompts, generation config, seeds
# ---------------------------------------------------------------------------


def test_generation_profile_is_frozen() -> None:
    for condition in hc.CONDITIONS:
        config = hc.generation_config(condition)
        assert config.max_new_tokens == 512
        assert config.temperature == pytest.approx(0.6)
        assert config.top_p == pytest.approx(0.95)
        assert config.do_sample is True


def test_generation_config_rejects_a_deferred_condition() -> None:
    with pytest.raises(ValueError):
        hc.generation_config("prompt_only_raw_strict")


def test_prompts_carry_the_registered_override(selected: list[dict[str, Any]]) -> None:
    question = str(selected[0]["question"])
    for condition in hc.CONDITIONS:
        prompt = hc.build_condition_prompt(question, condition)
        assert question in prompt
        assert hc.PROMPT_OVERRIDE_TEXT.strip() in prompt
        assert "Final answer:" in prompt


def test_prompts_differ_between_conditions(selected: list[dict[str, Any]]) -> None:
    question = str(selected[0]["question"])
    assert hc.build_condition_prompt(question, "visible_cot") != hc.build_condition_prompt(
        question, "r1_style_thinking"
    )


def test_prompt_construction_is_deterministic(selected: list[dict[str, Any]]) -> None:
    question = str(selected[3]["question"])
    assert hc.build_condition_prompt(question, "visible_cot") == hc.build_condition_prompt(
        question, "visible_cot"
    )


def test_work_unit_plan_is_300_units(selected: list[dict[str, Any]]) -> None:
    units = hc.plan_work_units(selected)
    assert len(units) == 300
    assert len({(unit.task_id, unit.condition) for unit in units}) == 300
    assert len({unit.record_id for unit in units}) == 300
    assert {unit.condition for unit in units} == set(hc.CONDITIONS)


def test_work_unit_seed_matches_the_registered_rule(selected: list[dict[str, Any]]) -> None:
    unit = hc.plan_work_units(selected)[0]
    assert unit.seed == hc.derive_run_seed(
        unit.task_id, unit.condition, 512, hc.DECODING_PROFILE, hc.REPLICATE_INDEX
    )


def test_work_unit_plan_is_stable(selected: list[dict[str, Any]]) -> None:
    first = [(u.record_id, u.seed, u.prompt_sha256) for u in hc.plan_work_units(selected)]
    second = [(u.record_id, u.seed, u.prompt_sha256) for u in hc.plan_work_units(selected)]
    assert first == second


def test_work_unit_seeds_are_distinct_per_condition(selected: list[dict[str, Any]]) -> None:
    units = {(u.task_id, u.condition): u.seed for u in hc.plan_work_units(selected)}
    task_id = selected[0]["task_id"]
    assert units[(task_id, "visible_cot")] != units[(task_id, "r1_style_thinking")]


# ---------------------------------------------------------------------------
# triage
# ---------------------------------------------------------------------------


def test_triage_numeric_accepts_a_clean_final_answer() -> None:
    result = hc.triage_numeric("Some reasoning.\nFinal answer: 42", "42")
    assert result.parse_valid is True
    assert result.answer_presence == "present"
    assert result.matches_registered_answer is True
    assert result.parse_ambiguous is False


def test_triage_numeric_flags_a_mismatch() -> None:
    result = hc.triage_numeric("Final answer: 41", "42")
    assert result.answer_presence == "present"
    assert result.matches_registered_answer is False


def test_triage_numeric_flags_a_missing_answer() -> None:
    result = hc.triage_numeric("I am still thinking about it.", "42")
    assert result.matches_registered_answer is not True
    assert result.parse_valid is False or result.answer_presence != "present"


def test_triage_entity_finds_the_final_line_entity() -> None:
    result = hc.triage_entity(
        "<think>weighing options</think>\nFinal answer: Zarn",
        "Zarn",
        ["Zarn", "Quel"],
    )
    assert result.answer_presence == "present"
    assert result.matches_registered_answer is True
    assert result.parse_ambiguous is False


def test_triage_entity_flags_multiple_candidates() -> None:
    result = hc.triage_entity("Final answer: Zarn or Quel", "Zarn", ["Zarn", "Quel"])
    assert result.parse_ambiguous is True


def test_triage_entity_flags_an_answer_outside_the_final_line() -> None:
    result = hc.triage_entity(
        "The answer is Zarn.\nI hope this helps.", "Zarn", ["Zarn", "Quel"]
    )
    assert result.parse_valid is False
    assert "answer_not_in_final_line" in result.failure_reasons


def test_triage_entity_reports_absence() -> None:
    result = hc.triage_entity("No idea at all.", "Zarn", ["Zarn", "Quel"])
    assert result.answer_presence == "absent"
    assert result.matches_registered_answer is None


def test_triage_entity_engine_is_marked_non_authoritative() -> None:
    result = hc.triage_entity("Final answer: Zarn", "Zarn", ["Zarn"])
    assert result.engine == "entity_surface_match_v1"


def test_triage_output_routes_by_answer_type() -> None:
    numeric = hc.triage_output("Final answer: 7", "numeric", "7")
    assert numeric.engine == "parser_v2_read_only"
    entity = hc.triage_output("Final answer: Zarn", "entity", "Zarn", ["Zarn"])
    assert entity.engine == "entity_surface_match_v1"


# ---------------------------------------------------------------------------
# record fixtures
# ---------------------------------------------------------------------------


def _fake_records(
    *,
    correct_per_cell: int = 10,
    n_cells: int = 1,
    truncated: int = 0,
    no_answer: int = 0,
    n_per_cell: int = hc.REQUIRED_CELL_N,
) -> list[dict[str, Any]]:
    """Build synthetic scored records with a controlled per-cell correct count."""

    records: list[dict[str, Any]] = []
    for cell_index in range(n_cells):
        family = hc.TASK_FAMILIES[cell_index % len(hc.TASK_FAMILIES)]
        band = hc.DIFFICULTY_BANDS[cell_index % len(hc.DIFFICULTY_BANDS)]
        condition = hc.CONDITIONS[cell_index % len(hc.CONDITIONS)]
        cell_id = f"{family}|{band}|{condition}"
        truncated_ix = set(range(n_per_cell - truncated, n_per_cell))
        no_answer_ix = set(
            range(n_per_cell - truncated - no_answer, n_per_cell - truncated)
        )
        for index in range(n_per_cell):
            correct = index < correct_per_cell
            record_id = f"fake-{cell_index:02d}-{index:02d}::{condition}::r0"
            records.append(
                {
                    "record_id": record_id,
                    "run_id": "test-run",
                    "phase": hc.PHASE,
                    "track": hc.TRACK,
                    "source_item_id": f"fake-{cell_index:02d}-{index:02d}",
                    "condition": condition,
                    "status": hc.STATUS_GENERATED,
                    "input_hash": hc.sha256_text(record_id + "-in"),
                    "output_hash": hc.sha256_text(record_id + "-out"),
                    "output_text": f"Final answer: {'1' if correct else '0'}",
                    "evaluation": {
                        "final_correct": None,
                        "no_answer": index in no_answer_ix,
                        "provisional_correct": correct,
                        "review_reasons": [],
                        "review_required": False,
                        "semantic_label": None,
                        "semantic_label_source": hc.LABEL_SOURCE_NOT_ADJUDICATED,
                        "triage": {
                            "answer_presence": "absent" if index in no_answer_ix else "present",
                            "candidate_answers": [],
                            "engine": "test_fixture",
                            "engine_version": "test_fixture",
                            "failure_reasons": [],
                            "matches_registered_answer": correct,
                            "output_quality": "complete",
                            "parse_ambiguous": False,
                            "parse_valid": True,
                            "parsed_answer": "1" if correct else "0",
                            "triage_authority": hc.TRIAGE_AUTHORITY,
                        },
                        "truncated": index in truncated_ix,
                    },
                    "provenance": {
                        "answer_type": "numeric",
                        "cell_id": cell_id,
                        "difficulty_band": band,
                        "prompt_text": "prompt",
                        "registered_answer": "1",
                        "task_family": family,
                    },
                }
            )
    return records


def _adjudicate(records: list[dict[str, Any]], *, cover_review: bool = True) -> None:
    for record in records:
        evaluation = record["evaluation"]
        correct = bool(evaluation["provisional_correct"])
        evaluation["final_correct"] = correct
        evaluation["semantic_label"] = "correct" if correct else "incorrect"
        if evaluation["review_required"] and cover_review:
            evaluation["semantic_label_source"] = hc.LABEL_SOURCE_PRIMARY
        else:
            evaluation["semantic_label_source"] = hc.LABEL_SOURCE_TRIAGE_ACCEPTED


def _score(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hc.annotate_review_selection(records)
    _adjudicate(records)
    return hc.score_cells(records)


# ---------------------------------------------------------------------------
# bounded review selection
# ---------------------------------------------------------------------------


def test_review_selection_flags_every_mandatory_category() -> None:
    records = _fake_records(correct_per_cell=8, n_cells=1, truncated=1, no_answer=1)
    hc.annotate_review_selection(records)
    reasons = {
        reason for record in records for reason in record["evaluation"]["review_reasons"]
    }
    assert "truncated_output" in reasons
    assert "no_answer" in reasons
    assert "triage_disagrees_with_registered_answer" in reasons
    assert "provisional_headroom_cell" in reasons
    assert reasons <= set(hc.REVIEW_REASON_CODES)


def test_review_selection_flags_parse_failures() -> None:
    records = _fake_records(correct_per_cell=1, n_cells=1)
    records[0]["evaluation"]["triage"]["parse_valid"] = False
    records[1]["evaluation"]["triage"]["parse_ambiguous"] = True
    hc.annotate_review_selection(records)
    assert "parse_invalid" in records[0]["evaluation"]["review_reasons"]
    assert "ambiguous_parse" in records[1]["evaluation"]["review_reasons"]


def test_provisional_headroom_cells_are_reviewed_in_full() -> None:
    records = _fake_records(correct_per_cell=hc.PROVISIONAL_REVIEW_MIN_CORRECT, n_cells=1)
    hc.annotate_review_selection(records)
    assert all(record["evaluation"]["review_required"] for record in records)


def test_below_provisional_threshold_cells_are_not_reviewed_in_full() -> None:
    records = _fake_records(correct_per_cell=hc.PROVISIONAL_REVIEW_MIN_CORRECT - 1, n_cells=1)
    hc.annotate_review_selection(records)
    assert not all(record["evaluation"]["review_required"] for record in records)


def test_review_selection_is_deterministic() -> None:
    first = _fake_records(correct_per_cell=3, n_cells=4)
    second = _fake_records(correct_per_cell=3, n_cells=4)
    hc.annotate_review_selection(first)
    hc.annotate_review_selection(second)
    assert [r["evaluation"]["review_reasons"] for r in first] == [
        r["evaluation"]["review_reasons"] for r in second
    ]


def test_review_sample_uses_the_ceiling_of_ten_percent() -> None:
    records = _fake_records(correct_per_cell=3, n_cells=4)
    clean = 4 * 3
    hc.annotate_review_selection(records)
    sampled = [
        r
        for r in records
        if r["evaluation"]["review_reasons"] == ["deterministic_random_sample"]
    ]
    assert len(sampled) == math.ceil(hc.REVIEW_SAMPLE_FRACTION * clean)


def test_review_load_stays_bounded_for_low_accuracy_cells() -> None:
    records = _fake_records(correct_per_cell=3, n_cells=4)
    hc.annotate_review_selection(records)
    flagged = [r for r in records if r["evaluation"]["review_required"]]
    assert 0 < len(flagged) < len(records)


def test_planned_records_are_never_sent_for_review() -> None:
    records = _fake_records(correct_per_cell=8, n_cells=1)
    for record in records:
        record["status"] = hc.STATUS_PLANNED
    hc.annotate_review_selection(records)
    assert not any(record["evaluation"]["review_required"] for record in records)


def test_review_pack_ids_are_unique_and_ordered() -> None:
    records = _fake_records(correct_per_cell=3, n_cells=4)
    hc.annotate_review_selection(records)
    review_rows, triage_rows = hc.build_review_pack("test-run", records)
    ids = [row["review_id"] for row in review_rows]
    assert ids == [f"R{index:03d}" for index in range(1, len(ids) + 1)]
    assert len(set(ids)) == len(ids)
    assert [row["review_id"] for row in triage_rows] == ids


def test_review_pack_is_blinded_to_the_triage_verdict() -> None:
    records = _fake_records(correct_per_cell=3, n_cells=4)
    hc.annotate_review_selection(records)
    review_rows, triage_rows = hc.build_review_pack("test-run", records)
    for row in review_rows:
        assert "matches_registered_answer" not in json.dumps(row)
        assert "triage" not in row
        assert row["model_output"]
    assert all("triage" in row for row in triage_rows)


def test_review_pack_ordering_is_stable() -> None:
    first_records = _fake_records(correct_per_cell=3, n_cells=4)
    second_records = _fake_records(correct_per_cell=3, n_cells=4)
    hc.annotate_review_selection(first_records)
    hc.annotate_review_selection(second_records)
    first, _ = hc.build_review_pack("test-run", first_records)
    second, _ = hc.build_review_pack("test-run", second_records)
    assert [row["record_id"] for row in first] == [row["record_id"] for row in second]


# ---------------------------------------------------------------------------
# cell scoring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("correct", "classification"),
    [
        (10, "control_sanity_high_accuracy"),
        (9, "selected_headroom"),
        (8, "selected_headroom"),
        (7, "selected_headroom"),
        (6, "difficulty_boundary_excluded"),
        (0, "difficulty_boundary_excluded"),
    ],
)
def test_cell_classification_boundaries(correct: int, classification: str) -> None:
    cells = _score(_fake_records(correct_per_cell=correct, n_cells=1))
    assert len(cells) == 1
    assert cells[0]["accuracy"] == pytest.approx(correct / 10)
    assert cells[0]["classification"] == classification
    assert cells[0]["selected"] is (classification == "selected_headroom")


def test_high_accuracy_cells_are_control_only() -> None:
    cells = _score(_fake_records(correct_per_cell=10, n_cells=1))
    assert "accuracy_above_band_control_only" in cells[0]["exclusion_reasons"]
    assert cells[0]["selected"] is False


def test_low_accuracy_cells_are_retained_as_difficulty_boundaries() -> None:
    cells = _score(_fake_records(correct_per_cell=5, n_cells=1))
    assert "accuracy_below_band_difficulty_boundary" in cells[0]["exclusion_reasons"]
    assert "insufficient_correct_count" in cells[0]["exclusion_reasons"]


def test_truncation_gate_boundary() -> None:
    ok = _score(_fake_records(correct_per_cell=8, n_cells=1, truncated=1))
    assert ok[0]["classification"] == "selected_headroom"
    bad = _score(_fake_records(correct_per_cell=8, n_cells=1, truncated=2))
    assert bad[0]["classification"] == "excluded_quality_gate"
    assert "truncation_rate_above_threshold" in bad[0]["exclusion_reasons"]


def test_no_answer_gate_boundary() -> None:
    ok = _score(_fake_records(correct_per_cell=8, n_cells=1, no_answer=1))
    assert ok[0]["classification"] == "selected_headroom"
    bad = _score(_fake_records(correct_per_cell=8, n_cells=1, no_answer=2))
    assert bad[0]["classification"] == "excluded_quality_gate"
    assert "no_answer_rate_above_threshold" in bad[0]["exclusion_reasons"]


def test_unresolved_labels_block_selection() -> None:
    records = _fake_records(correct_per_cell=8, n_cells=1)
    hc.annotate_review_selection(records)
    _adjudicate(records)
    records[0]["evaluation"]["final_correct"] = None
    records[0]["evaluation"]["semantic_label"] = None
    cells = hc.score_cells(records)
    assert cells[0]["unresolved"] == 1
    assert cells[0]["selected"] is False
    assert cells[0]["accuracy"] is None
    assert "unresolved_semantic_labels_present" in cells[0]["exclusion_reasons"]


def test_incomplete_review_coverage_blocks_selection() -> None:
    records = _fake_records(correct_per_cell=8, n_cells=1)
    hc.annotate_review_selection(records)
    _adjudicate(records, cover_review=False)
    cells = hc.score_cells(records)
    assert cells[0]["review_coverage_complete"] is False
    assert cells[0]["exclusion_reasons"] == ["incomplete_review_coverage"]
    assert hc.supplementary_review_cells(cells) == [cells[0]["cell_id"]]


def test_supplementary_review_excludes_otherwise_failing_cells() -> None:
    records = _fake_records(correct_per_cell=2, n_cells=1)
    hc.annotate_review_selection(records)
    _adjudicate(records, cover_review=False)
    cells = hc.score_cells(records)
    assert hc.supplementary_review_cells(cells) == []


def test_incomplete_cell_is_excluded() -> None:
    records = _fake_records(correct_per_cell=8, n_cells=1, n_per_cell=9)
    cells = _score(records)
    assert cells[0]["n"] == 9
    assert cells[0]["selected"] is False
    assert "incomplete_cell_n" in cells[0]["exclusion_reasons"]


def test_cells_are_never_pooled_across_conditions() -> None:
    cells = _score(_fake_records(correct_per_cell=8, n_cells=6))
    assert len({cell["cell_id"] for cell in cells}) == len(cells)
    for cell in cells:
        assert cell["cell_id"].endswith(cell["condition"])
        assert cell["cell_id"].startswith(cell["task_family"])


def test_parser_v2_alone_never_produces_a_final_label() -> None:
    records = _fake_records(correct_per_cell=8, n_cells=1)
    hc.annotate_review_selection(records)
    cells = hc.score_cells(records)
    assert cells[0]["selected"] is False
    assert cells[0]["classification"] == "not_adjudicated"


def test_exclusion_reason_codes_are_registered() -> None:
    cells = _score(_fake_records(correct_per_cell=2, n_cells=3, truncated=2))
    for cell in cells:
        for reason in cell["exclusion_reasons"]:
            assert reason in hc.EXCLUSION_REASON_CODES
        assert cell["classification"] in hc.CLASSIFICATIONS


def test_wilson_ci_brackets_the_point_estimate() -> None:
    lower, upper = hc.wilson_ci(8, 10)
    assert 0.0 <= lower < 0.8 < upper <= 1.0
    assert hc.wilson_ci(0, 0) == (0.0, 0.0) or hc.wilson_ci(0, 0)[0] == 0.0


def test_metric_rows_match_the_registered_header() -> None:
    cells = _score(_fake_records(correct_per_cell=8, n_cells=2))
    records = _fake_records(correct_per_cell=8, n_cells=2)
    hc.annotate_review_selection(records)
    _adjudicate(records)
    rows = hc.build_metrics_rows("test-run", records, cells)
    assert rows
    for row in rows:
        assert len(row) == len(hc.METRICS_HEADER)


# ---------------------------------------------------------------------------
# artifact pack
# ---------------------------------------------------------------------------


def test_plan_mode_is_blocked_and_emits_every_artifact(plan_pack: Path) -> None:
    for name in hc.ARTIFACT_FILES:
        assert (plan_pack / name).is_file(), name
    decision = json.loads((plan_pack / "04_decision.json").read_text("utf-8"))
    assert decision["status"] == "BLOCKED"


def test_plan_mode_plans_exactly_300_records(plan_pack: Path) -> None:
    lines = (plan_pack / "02_records.jsonl").read_text("utf-8").splitlines()
    assert len(lines) == 300
    assert all(json.loads(line)["status"] == hc.STATUS_PLANNED for line in lines)


def test_self_test_pack_emits_every_artifact(self_test_pack: Path) -> None:
    for name in hc.ARTIFACT_FILES:
        assert (self_test_pack / name).is_file(), name
    assert (self_test_pack / "review_pack" / "review_pack.jsonl").is_file()
    assert (self_test_pack / "review_pack" / "deterministic_triage.jsonl").is_file()
    assert (self_test_pack / "review_pack" / "arbitration_packet.jsonl").is_file()
    assert (self_test_pack / "cell_selection" / "selected_headroom_cells.csv").is_file()
    assert (self_test_pack / "cell_selection" / "excluded_cells.csv").is_file()
    assert (self_test_pack / "cell_selection" / "cell_exclusion_reasons.json").is_file()


def test_manifest_is_written_last_and_lists_every_file(self_test_pack: Path) -> None:
    manifest = json.loads((self_test_pack / "artifact_manifest.json").read_text("utf-8"))
    listed = {entry["path"] for entry in manifest["files"]}
    on_disk = {
        path.relative_to(self_test_pack).as_posix()
        for path in self_test_pack.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    }
    assert on_disk == listed
    for entry in manifest["files"]:
        blob = (self_test_pack / entry["path"]).read_bytes()
        assert entry["sha256"] == hashlib.sha256(blob).hexdigest()
        assert entry["bytes"] == len(blob)


def test_records_always_carry_provenance(self_test_pack: Path) -> None:
    lines = (self_test_pack / "02_records.jsonl").read_text("utf-8").splitlines()
    assert len(lines) == 300
    for line in lines:
        record = json.loads(line)
        for key in (
            "record_id",
            "run_id",
            "phase",
            "track",
            "source_item_id",
            "condition",
            "status",
            "input_hash",
            "output_hash",
            "evaluation",
        ):
            assert key in record, key
        assert record["condition"] in hc.CONDITIONS
        assert record["input_hash"]
        assert record["output_hash"]


def test_metrics_csv_header_matches_the_specification(self_test_pack: Path) -> None:
    with (self_test_pack / "03_metrics.csv").open("r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == list(hc.METRICS_HEADER)


def test_metrics_csv_reports_confidence_intervals(self_test_pack: Path) -> None:
    with (self_test_pack / "03_metrics.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    accuracy = [row for row in rows if row["metric"] == "semantic_accuracy"]
    assert accuracy
    for row in accuracy:
        assert row["ci_lower"] and row["ci_upper"]
        assert float(row["ci_lower"]) <= float(row["value"]) <= float(row["ci_upper"])


def test_decision_json_shape(self_test_pack: Path) -> None:
    decision = json.loads((self_test_pack / "04_decision.json").read_text("utf-8"))
    assert decision["status"] in {"PASS", "FAIL", "COMPLETE", "INCONCLUSIVE", "BLOCKED"}
    for key in (
        "decision",
        "criteria_passed",
        "criteria_failed",
        "criteria_not_applicable",
        "deviations",
        "scientific_interpretation",
        "prohibited_interpretations",
        "next_gate",
    ):
        assert key in decision, key
    assert decision["prohibited_interpretations"] == list(hc.PROHIBITED_INTERPRETATIONS)


def test_summary_sections_are_in_the_required_order(self_test_pack: Path) -> None:
    text = (self_test_pack / "05_summary.md").read_text("utf-8")
    expected = [
        "# Summary",
        "## Objective",
        "## Scope",
        "## Provenance",
        "## Execution",
        "## Results",
        "## Decision",
        "## Deviations and errors",
        "## Scientific interpretation",
        "## Limitations",
        "## Paper relevance",
        "## Next gate",
    ]
    positions = [text.find(heading) for heading in expected]
    assert all(position >= 0 for position in positions), positions
    assert positions == sorted(positions)


def test_stage_manifest_fields(self_test_pack: Path) -> None:
    manifest = json.loads((self_test_pack / "00_stage_manifest.json").read_text("utf-8"))
    for key in (
        "schema_version",
        "phase",
        "track",
        "run_id",
        "status",
        "start_time_utc",
        "end_time_utc",
        "objective",
        "hypothesis",
        "scope",
        "out_of_scope",
        "model_id",
        "model_revision",
        "code_commit",
        "image_digest",
        "hardware",
        "subagents",
        "inputs",
        "protocol_hash",
        "output_files",
    ):
        assert key in manifest, key
    assert manifest["model_id"] == hc.MODEL_ID
    assert manifest["model_revision"] == hc.MODEL_REVISION
    assert manifest["phase"] == hc.PHASE
    assert manifest["track"] == hc.TRACK


def test_protocol_snapshot_fields(self_test_pack: Path) -> None:
    snapshot = json.loads((self_test_pack / "01_protocol_snapshot.json").read_text("utf-8"))
    for key in (
        "research_question",
        "primary_metric",
        "secondary_metrics",
        "decision_rules",
        "sample_size",
        "seeds",
        "conditions",
        "inclusion_rules",
        "exclusion_rules",
        "stopping_rules",
        "retry_rules",
        "scientific_claim_boundary",
    ):
        assert key in snapshot, key
    assert snapshot["sample_size"]["generations"] == 300
    assert snapshot["sample_size"]["items"] == 150
    assert snapshot["seeds"]["selection_seed"] == hc.SELECTION_SEED
    assert set(snapshot["conditions"]["deferred_this_round"]) == set(hc.DEFERRED_CONDITIONS)
    assert snapshot["conditions"]["prompt_override_sha256"] == hc.sha256_text(
        hc.PROMPT_OVERRIDE_TEXT
    )


def test_deviations_file_always_exists(self_test_pack: Path) -> None:
    deviations = json.loads((self_test_pack / "08_deviations.json").read_text("utf-8"))
    for key in ("deviations", "unregistered_changes", "effect_on_interpretation"):
        assert key in deviations, key


def test_plan_mode_deviations_file_is_empty_shaped(plan_pack: Path) -> None:
    deviations = json.loads((plan_pack / "08_deviations.json").read_text("utf-8"))
    assert deviations["deviations"] == []
    assert deviations["unregistered_changes"] == []
    assert deviations["effect_on_interpretation"] == "none"


def test_not_applicable_artifacts_declare_a_reason(plan_pack: Path) -> None:
    manifest = json.loads((plan_pack / "artifact_manifest.json").read_text("utf-8"))
    not_applicable = [
        entry for entry in manifest["files"] if entry.get("status") == "not_applicable"
    ]
    assert not_applicable
    for entry in not_applicable:
        assert entry.get("reason")


def test_self_test_registers_a_synthetic_output_deviation(self_test_pack: Path) -> None:
    deviations = json.loads((self_test_pack / "08_deviations.json").read_text("utf-8"))
    assert deviations["deviations"]
    assert "synthetic" in json.dumps(deviations).lower()


def test_self_test_reaches_a_complete_decision(self_test_pack: Path) -> None:
    decision = json.loads((self_test_pack / "04_decision.json").read_text("utf-8"))
    assert decision["status"] == "COMPLETE"


def test_paper_and_figure_tables_cover_every_cell(self_test_pack: Path) -> None:
    with (self_test_pack / "06_paper_table.csv").open("r", encoding="utf-8", newline="") as handle:
        paper = list(csv.DictReader(handle))
    assert len(paper) == 30
    with (self_test_pack / "07_figure_data.csv").open("r", encoding="utf-8", newline="") as handle:
        figure = list(csv.DictReader(handle))
    assert figure


# ---------------------------------------------------------------------------
# review -> finalize -> arbitration sequence
# ---------------------------------------------------------------------------


def _judgments_from_review_pack(pack: Path, flip: str | None = None) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (pack / "review_pack" / "review_pack.jsonl").read_text("utf-8").splitlines()
    ]
    judgments: list[dict[str, Any]] = []
    for row in rows:
        markers = [
            part.strip()
            for part in row["model_output"].split("Final answer:")[1:]
        ]
        observed = markers[-1].splitlines()[0].strip() if markers else ""
        label = "correct" if observed == str(row["registered_answer"]).strip() else "incorrect"
        if flip is not None and row["record_id"] == flip:
            label = "incorrect" if label == "correct" else "correct"
        judgments.append(
            {
                "notes": "",
                "record_id": row["record_id"],
                "review_id": row["review_id"],
                "reviewer_id": "reviewer-test",
                "semantic_label": label,
            }
        )
    return judgments


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_bytes(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8")
    )
    return path


def test_finalize_applies_primary_judgments(self_test_pack: Path, tmp_path: Path) -> None:
    judgments = _write_jsonl(
        tmp_path / "primary.jsonl", _judgments_from_review_pack(self_test_pack)
    )
    result = _run(
        "finalize",
        tmp_path / "out",
        run_id="finalize-probe",
        records_path=self_test_pack / "02_records.jsonl",
        judgments_path=judgments,
    )
    assert result["decision"]["status"] == "COMPLETE"
    assert len(result["decision"]["selected_headroom_cells"]) == 30


def test_conflicting_primary_label_requires_arbitration(
    self_test_pack: Path, tmp_path: Path
) -> None:
    records = [
        json.loads(line)
        for line in (self_test_pack / "02_records.jsonl").read_text("utf-8").splitlines()
    ]
    flipped = next(
        record["record_id"]
        for record in records
        if record["evaluation"]["triage"]["matches_registered_answer"] is True
    )
    judgments = _write_jsonl(
        tmp_path / "conflict.jsonl",
        _judgments_from_review_pack(self_test_pack, flip=flipped),
    )
    result = _run(
        "finalize",
        tmp_path / "out",
        run_id="conflict-probe",
        records_path=self_test_pack / "02_records.jsonl",
        judgments_path=judgments,
    )
    assert result["decision"]["status"] == "INCONCLUSIVE"
    assert len(result["decision"]["selected_headroom_cells"]) < 30
    packet = [
        json.loads(line)
        for line in (Path(result["output_dir"]) / "review_pack" / "arbitration_packet.jsonl")
        .read_text("utf-8")
        .splitlines()
    ]
    assert [row["record_id"] for row in packet] == [flipped]

    arbiter = _write_jsonl(
        tmp_path / "arbiter.jsonl",
        [
            {
                "arbiter_id": "arbiter-test",
                "record_id": flipped,
                "review_id": packet[0]["review_id"],
                "semantic_label": "correct",
            }
        ],
    )
    resolved = _run(
        "finalize",
        tmp_path / "out2",
        run_id="arbiter-probe",
        records_path=self_test_pack / "02_records.jsonl",
        judgments_path=judgments,
        arbiter_judgments_path=arbiter,
    )
    assert resolved["decision"]["status"] == "COMPLETE"
    assert len(resolved["decision"]["selected_headroom_cells"]) == 30


def test_finalize_requires_a_records_file(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        _run("finalize", tmp_path / "out")


# ---------------------------------------------------------------------------
# determinism and portability
# ---------------------------------------------------------------------------


def test_pack_is_byte_reproducible(tmp_path: Path) -> None:
    digests = []
    for index in range(2):
        result = _run("plan", tmp_path / f"run{index}")
        pack = Path(result["output_dir"])
        digests.append(
            {
                path.relative_to(pack).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(pack.rglob("*"))
                if path.is_file()
            }
        )
    assert digests[0] == digests[1]


def test_all_text_artifacts_use_lf_newlines(self_test_pack: Path) -> None:
    for path in sorted(self_test_pack.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".csv", ".md"}:
            assert b"\r\n" not in path.read_bytes(), path.name


def test_artifacts_are_utf8(self_test_pack: Path) -> None:
    for path in sorted(self_test_pack.rglob("*")):
        if path.is_file():
            path.read_bytes().decode("utf-8")


def test_canonical_json_is_stable() -> None:
    payload = {"b": 1, "a": [3, 2, 1]}
    assert hc.canonical_json(payload) == hc.canonical_json({"a": [3, 2, 1], "b": 1})
    assert hc.canonical_json(payload).endswith("\n")


def test_module_does_not_import_torch_at_module_scope() -> None:
    source = Path(hc.__file__).read_text("utf-8")
    for line in source.splitlines():
        if line.startswith(("import ", "from ")):
            assert "torch" not in line
            assert "transformers" not in line


def test_module_never_shells_out() -> None:
    source = Path(hc.__file__).read_text("utf-8")
    assert "subprocess" not in source
    assert "os.system" not in source


def test_protected_parser_modules_still_exist() -> None:
    for name in (
        "eval_parsing.py",
        "eval_parsing_v2.py",
        "parser_v2_locked_evaluation.py",
    ):
        assert (ROOT / "src" / "jspace_observation" / name).is_file(), name


def test_entrypoint_script_exists() -> None:
    assert (ROOT / "scripts" / "run_phase1_headroom_calibration.py").is_file()


def test_protocol_document_exists() -> None:
    assert (ROOT / "docs" / "phase1_headroom_calibration_protocol.md").is_file()
