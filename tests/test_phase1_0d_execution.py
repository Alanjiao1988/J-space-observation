"""Tests for the Phase 1.0D execution pipeline.

The pipeline is validated end to end on CPU with a deterministic self-test
backend.  Fabricated rows are never evidence about the model; they exist so that
the routing, review-selection, arbitration, aggregation, and decision code is
constrained before a GPU run spends real capacity.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.headroom_calibration import load_task_bank
from jspace_observation.phase1_0c_defect_audit import load_phase_1_0c_records
from jspace_observation.phase1_0d_confirmation import (
    ARMS,
    DEFAULT_BANK_PATH,
    NO_HEADROOM_RESULT,
    RUN_BASE_SEED,
    SPONTANEOUS_NO_COT_ARM,
    STRICT_MAX_NEW_TOKENS,
    STRUCTURAL_NO_COT_ARM,
    VISIBLE_CONTROL_ARM,
    VISIBLE_MAX_NEW_TOKENS,
    Phase1_0DError,
    phase_1_0c_item_ids,
    select_confirmation_items,
)
from jspace_observation.phase1_0d_execution import (
    GenerationOutput,
    SelfTestBackend,
    annotate_review_selection,
    apply_judgments,
    build_decision,
    build_records,
    compute_cell_outcomes,
    final_answer_surface,
    looks_like_a_loop,
    plan_work_units,
    record_id_for,
    review_agreement,
    triage,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def items():
    bank = load_task_bank(REPO_ROOT / DEFAULT_BANK_PATH)
    used = phase_1_0c_item_ids(load_phase_1_0c_records())
    return select_confirmation_items(bank, used)


@pytest.fixture(scope="module")
def units(items):
    return plan_work_units(items, base_seed=RUN_BASE_SEED)


@pytest.fixture(scope="module")
def pipeline(units):
    backend = SelfTestBackend()
    outputs = {unit.record_id: backend.generate(unit) for unit in units}
    records = build_records(units, outputs)
    for record in records:
        route = record["triage"]["route"]
        record["evaluation"]["primary_label"] = {
            "candidate_correct": "correct",
            "candidate_incorrect": "incorrect",
            "no_final_answer_surface": "no_answer",
            "placeholder_echo": "invalid",
            "truncated_at_budget": "invalid",
            "possible_loop": "invalid",
        }[route]
    annotated = annotate_review_selection(records)
    for record in annotated:
        if record["evaluation"]["secondary_review_required"]:
            record["evaluation"]["secondary_label"] = record["evaluation"]["primary_label"]
    return apply_judgments(annotated)


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def test_the_plan_covers_every_item_in_every_arm(items, units):
    assert len(units) == len(items) * len(ARMS) == 900
    assert len({unit.record_id for unit in units}) == 900


def test_every_planned_unit_carries_its_registered_budget(units):
    for unit in units:
        expected = (
            VISIBLE_MAX_NEW_TOKENS
            if unit.arm_id == VISIBLE_CONTROL_ARM.arm_id
            else STRICT_MAX_NEW_TOKENS
        )
        assert unit.max_new_tokens == expected


def test_the_plan_is_deterministic(items):
    first = plan_work_units(items, base_seed=RUN_BASE_SEED)
    second = plan_work_units(items, base_seed=RUN_BASE_SEED)
    assert [unit.record_id for unit in first] == [unit.record_id for unit in second]
    assert [unit.prompt for unit in first] == [unit.prompt for unit in second]


def test_a_defective_prompt_stops_the_plan_before_generation():
    bad_item = {
        "task_id": "synthetic-01",
        "task_family": "arithmetic",
        "difficulty_band": "easy",
        "split": "confirmation",
        "registered_answer": "4",
        "question": "What is {start} + 2? Final answer: <answer>",
    }
    with pytest.raises(Phase1_0DError) as excinfo:
        plan_work_units([bad_item], base_seed=RUN_BASE_SEED)
    assert "literal_answer_placeholder" in str(excinfo.value)


def test_record_ids_are_stable():
    assert record_id_for("t-1", "spontaneous_no_cot") == "t-1::spontaneous_no_cot::r0"


# ---------------------------------------------------------------------------
# Triage routes but never labels
# ---------------------------------------------------------------------------


def test_triage_never_claims_to_decide_correctness(pipeline):
    assert all(record["triage"]["decides_correctness"] is False for record in pipeline)


def test_the_visible_surface_is_read_after_the_registered_prefix(units):
    unit = next(u for u in units if u.arm_id == VISIBLE_CONTROL_ARM.arm_id)
    assert final_answer_surface("blah\nFinal answer: 42", unit.arm) == "42"
    assert final_answer_surface("no surface here", unit.arm) is None


def test_the_last_final_answer_line_wins(units):
    unit = next(u for u in units if u.arm_id == VISIBLE_CONTROL_ARM.arm_id)
    text = "Final answer: 1\nWait, correcting.\nFinal answer: 2"
    assert final_answer_surface(text, unit.arm) == "2"


def test_a_strict_output_is_its_own_surface(units):
    unit = next(u for u in units if u.arm_id == SPONTANEOUS_NO_COT_ARM.arm_id)
    assert final_answer_surface("  224 ", unit.arm) == "224"
    assert final_answer_surface("   ", unit.arm) is None


def test_a_truncated_row_is_routed_not_scored(units):
    unit = next(u for u in units if u.arm_id == VISIBLE_CONTROL_ARM.arm_id)
    row = triage(unit, GenerationOutput("thinking " * 500, unit.max_new_tokens))
    assert row["truncated_at_budget"] is True
    assert row["route"] in {"truncated_at_budget", "no_final_answer_surface", "possible_loop"}


def test_a_placeholder_echo_is_detected(units):
    unit = next(u for u in units if u.arm_id == VISIBLE_CONTROL_ARM.arm_id)
    row = triage(unit, GenerationOutput("Final answer: <answer>", 6))
    assert row["placeholder_echo"] is True
    assert row["route"] == "placeholder_echo"


def test_the_loop_diagnostic_needs_real_repetition():
    assert looks_like_a_loop("one two three four five six seven eight " * 4)
    assert not looks_like_a_loop("one two three four five six seven eight nine ten")


# ---------------------------------------------------------------------------
# Review selection and arbitration
# ---------------------------------------------------------------------------


def test_every_row_is_primary_reviewed_before_selection(units):
    backend = SelfTestBackend()
    outputs = {unit.record_id: backend.generate(unit) for unit in units[:3]}
    records = build_records(units[:3], outputs)
    with pytest.raises(Phase1_0DError):
        annotate_review_selection(records)


def test_every_invalid_row_is_double_reviewed(pipeline):
    for record in pipeline:
        if record["evaluation"]["primary_label"] == "invalid":
            assert record["evaluation"]["secondary_review_required"] is True


def test_the_secondary_review_covers_more_than_the_forced_rows(pipeline):
    forced = sum(
        1
        for record in pipeline
        if record["evaluation"]["primary_label"] in {"invalid", "unresolved"}
    )
    selected = sum(
        1 for record in pipeline if record["evaluation"]["secondary_review_required"]
    )
    assert selected > forced


def test_a_missing_secondary_review_is_refused(units):
    backend = SelfTestBackend()
    outputs = {unit.record_id: backend.generate(unit) for unit in units[:20]}
    records = build_records(units[:20], outputs)
    for record in records:
        record["evaluation"]["primary_label"] = "invalid"
    annotated = annotate_review_selection(records)
    with pytest.raises(Phase1_0DError):
        apply_judgments(annotated)


def test_a_reviewer_disagreement_becomes_unresolved(units):
    backend = SelfTestBackend()
    outputs = {unit.record_id: backend.generate(unit) for unit in units[:1]}
    records = build_records(units[:1], outputs)
    records[0]["evaluation"]["primary_label"] = "correct"
    annotated = annotate_review_selection(records)
    annotated[0]["evaluation"]["secondary_review_required"] = True
    annotated[0]["evaluation"]["secondary_label"] = "incorrect"
    resolved = apply_judgments(annotated)
    assert resolved[0]["evaluation"]["final_label"] == "unresolved"
    assert resolved[0]["evaluation"]["arbitration_required"] is True


def test_agreement_reporting_separates_reviewers_from_the_parser(pipeline):
    report = review_agreement(pipeline)
    assert report["parser_agreement_is_not_reviewer_agreement"] is True
    assert report["double_reviewed_rows"] > 0
    assert report["reviewer_agreements"] + report["reviewer_disagreements"] == (
        report["double_reviewed_rows"]
    )
    assert "parser_agreements" in report


# ---------------------------------------------------------------------------
# Aggregation and decision
# ---------------------------------------------------------------------------


def test_every_cell_and_arm_is_aggregated(pipeline):
    outcomes = compute_cell_outcomes(pipeline)
    assert len(outcomes) == 15 * len(ARMS)
    assert all(outcome.resolved + outcome.unresolved == 20 for outcome in outcomes)


def test_the_decision_reports_every_cell_and_both_strict_arms(pipeline):
    decision = build_decision(pipeline)
    assert decision["cell_count"] == 15 * 2
    assert decision["all_cells_reported"] is True
    assert decision["strict_arms"] == [
        STRUCTURAL_NO_COT_ARM.arm_id,
        SPONTANEOUS_NO_COT_ARM.arm_id,
    ]
    assert json.loads(json.dumps(decision)) == decision


def test_the_decision_carries_paired_differences(pipeline):
    decision = build_decision(pipeline)
    for cell in decision["cells"]:
        assert cell["paired"]["paired_items"] == 20


def test_a_run_with_no_passing_cell_reports_the_scientific_result(pipeline):
    stripped = [
        {
            **record,
            "evaluation": {**record["evaluation"], "final_label": "incorrect"},
        }
        for record in pipeline
    ]
    decision = build_decision(stripped)
    assert decision["rq2_pilot_candidates"] == []
    assert decision["result"] == NO_HEADROOM_RESULT


def test_a_cell_without_a_visible_control_is_refused(pipeline):
    without_control = [
        record
        for record in pipeline
        if record["arm_id"] != VISIBLE_CONTROL_ARM.arm_id
    ]
    with pytest.raises(Phase1_0DError):
        build_decision(without_control)


def test_a_missing_strict_arm_is_reported_not_hidden(pipeline):
    dropped = [
        record
        for record in pipeline
        if not (
            record["arm_id"] == STRUCTURAL_NO_COT_ARM.arm_id
            and record["task_family"] == "arithmetic"
            and record["difficulty_band"] == "easy"
        )
    ]
    decision = build_decision(dropped)
    assert decision["all_cells_reported"] is False
    assert decision["cell_count"] == 15 * 2 - 1


def test_the_decision_disclaims_hidden_reasoning(pipeline):
    assert "J-space" in build_decision(pipeline)["licenses_no_claim_about"]


def test_the_self_test_backend_is_marked_as_not_a_model():
    assert SelfTestBackend.is_real_model is False
