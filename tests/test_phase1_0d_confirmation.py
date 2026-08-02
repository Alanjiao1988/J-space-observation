"""Tests for the frozen Phase 1.0D confirmation protocol.

Everything asserted here must hold *before* any target-model generation: the
disjoint split, the prompt renderings, the registered budgets, the adjudication
rules, and the cell gate.  A protocol that only becomes checkable after the run
cannot constrain the run.
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
    ARTIFACT_ROOT,
    DEFAULT_BANK_PATH,
    ELIGIBLE_SPLITS,
    EXPECTED_ITEM_COUNT,
    GATE_MIN_VISIBLE_CORRECT,
    GATE_STRICT_CORRECT_HIGH,
    GATE_STRICT_CORRECT_LOW,
    ITEMS_PER_CELL,
    LITERAL_ANSWER_PLACEHOLDER,
    PHASE_1_0C_SPLIT,
    PRESERVED_PHASE_1_0C_PACK,
    SPONTANEOUS_NO_COT_ARM,
    STRICT_MAX_NEW_TOKENS,
    STRUCTURAL_NO_COT_ARM,
    VISIBLE_CONTROL_ARM,
    VISIBLE_MAX_NEW_TOKENS,
    CellOutcome,
    Phase1_0DBankShortage,
    Phase1_0DError,
    arbitrate,
    assert_strict_budget_fits_every_answer,
    cell_availability,
    eligible_items,
    evaluate_cell_gate,
    generation_config,
    paired_difference,
    phase_1_0c_item_ids,
    prompt_defects,
    protocol_snapshot,
    render_prompt,
    requires_secondary_review,
    select_confirmation_items,
    selection_summary,
)
from jspace_observation.headroom_calibration import (
    MODEL_ID,
    MODEL_REVISION,
    PROMPT_OVERRIDE_TEXT,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def bank():
    return load_task_bank(REPO_ROOT / DEFAULT_BANK_PATH)


@pytest.fixture(scope="module")
def used_item_ids():
    return phase_1_0c_item_ids(load_phase_1_0c_records())


@pytest.fixture(scope="module")
def selection(bank, used_item_ids):
    return select_confirmation_items(bank, used_item_ids)


# ---------------------------------------------------------------------------
# The protocol does not overwrite Phase 1.0C
# ---------------------------------------------------------------------------


def test_the_new_namespace_is_not_the_preserved_one():
    assert ARTIFACT_ROOT != PRESERVED_PHASE_1_0C_PACK
    assert not PRESERVED_PHASE_1_0C_PACK.startswith(ARTIFACT_ROOT)
    assert not ARTIFACT_ROOT.startswith(PRESERVED_PHASE_1_0C_PACK)


def test_the_preserved_pack_is_still_on_disk():
    assert (REPO_ROOT / PRESERVED_PHASE_1_0C_PACK).is_dir()


def test_the_target_model_is_the_same_pin_as_phase_1_0c():
    snapshot = protocol_snapshot()
    assert snapshot["model_id"] == MODEL_ID
    assert snapshot["model_revision"] == MODEL_REVISION


# ---------------------------------------------------------------------------
# Deterministic disjoint confirmation split
# ---------------------------------------------------------------------------


def test_phase_1_0c_used_exactly_the_calibration_split(bank, used_item_ids):
    calibration_ids = {
        str(item["task_id"]) for item in bank if item["split"] == PHASE_1_0C_SPLIT
    }
    assert used_item_ids <= calibration_ids
    assert used_item_ids == calibration_ids


def test_the_eligible_pool_excludes_every_phase_1_0c_item(bank, used_item_ids):
    eligible = eligible_items(bank, used_item_ids)
    eligible_ids = {str(item["task_id"]) for item in eligible}
    assert eligible_ids & used_item_ids == set()
    assert {str(item["split"]) for item in eligible} <= set(ELIGIBLE_SPLITS)


def test_the_bank_supports_the_exact_registered_split(bank, used_item_ids):
    availability = cell_availability(eligible_items(bank, used_item_ids))
    assert len(availability) == 15
    shortages = {c: n for c, n in availability.items() if n < ITEMS_PER_CELL}
    assert shortages == {}


def test_the_selection_is_the_full_registered_sample(selection):
    assert len(selection) == EXPECTED_ITEM_COUNT == 300
    counts = cell_availability(selection)
    assert set(counts.values()) == {ITEMS_PER_CELL}


def test_the_selection_is_disjoint_from_phase_1_0c(selection, used_item_ids):
    summary = selection_summary(selection, used_item_ids)
    assert summary["disjoint_from_phase_1_0c"] is True
    assert summary["overlap_with_phase_1_0c"] == []
    assert summary["item_count"] == EXPECTED_ITEM_COUNT


def test_the_selection_is_deterministic(bank, used_item_ids):
    first = select_confirmation_items(bank, used_item_ids)
    second = select_confirmation_items(list(reversed(list(bank))), used_item_ids)
    assert [item["task_id"] for item in first] == [
        item["task_id"] for item in second
    ]


def test_a_short_cell_stops_the_run_before_inference(bank, used_item_ids):
    trimmed = [
        item
        for item in bank
        if not (
            item["task_family"] == "arithmetic"
            and item["difficulty_band"] == "easy"
            and item["split"] != PHASE_1_0C_SPLIT
        )
    ]
    with pytest.raises(Phase1_0DBankShortage) as excinfo:
        select_confirmation_items(trimmed, used_item_ids)
    assert "arithmetic|easy" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Prompt rendering — the P10C-D1 repair
# ---------------------------------------------------------------------------


def test_no_real_rendered_prompt_carries_a_prohibited_construct(selection):
    for item in selection:
        for arm in ARMS:
            prompt = render_prompt(str(item["question"]), arm)
            assert prompt_defects(prompt, arm) == [], (
                item["task_id"],
                arm.arm_id,
            )


def test_no_real_rendered_prompt_contains_the_literal_placeholder(selection):
    for item in selection:
        for arm in ARMS:
            assert LITERAL_ANSWER_PLACEHOLDER not in render_prompt(
                str(item["question"]), arm
            )


def test_the_phase_1_0c_override_is_not_reused():
    prompt = render_prompt("What is 2 + 2?", VISIBLE_CONTROL_ARM)
    assert PROMPT_OVERRIDE_TEXT not in prompt
    assert LITERAL_ANSWER_PLACEHOLDER in PROMPT_OVERRIDE_TEXT


def test_the_visible_control_shows_a_concrete_example_instead_of_a_placeholder():
    prompt = render_prompt("What is 2 + 2?", VISIBLE_CONTROL_ARM)
    assert "Final answer: 42" in prompt
    assert "Do not write angle brackets." in prompt
    assert "Do not write a placeholder." in prompt


def test_the_strict_arms_do_not_inherit_the_visible_override():
    for arm in (STRUCTURAL_NO_COT_ARM, SPONTANEOUS_NO_COT_ARM):
        prompt = render_prompt("What is 2 + 2?", arm)
        assert "Format override for this run" not in prompt
        assert "Final answer:" not in prompt


def test_raw_strict_has_no_think_tag_and_no_prefill():
    prompt = render_prompt("What is 2 + 2?", SPONTANEOUS_NO_COT_ARM)
    assert "<think>" not in prompt
    assert "</think>" not in prompt
    assert prompt_defects(prompt, SPONTANEOUS_NO_COT_ARM) == []


def test_raw_strict_is_not_model_name_dependent():
    prompt = render_prompt("What is 2 + 2?", SPONTANEOUS_NO_COT_ARM)
    for token in ("Qwen", "DeepSeek", "R1", "deepseek", "qwen"):
        assert token not in prompt


def test_the_structural_arm_still_carries_the_empty_think_prefill():
    prompt = render_prompt("What is 2 + 2?", STRUCTURAL_NO_COT_ARM)
    assert "<think>" in prompt
    assert prompt_defects(prompt, STRUCTURAL_NO_COT_ARM) == []


def test_the_defect_detector_actually_fires():
    bad = render_prompt("What is 2 + 2?", VISIBLE_CONTROL_ARM) + "\nFinal answer: <answer>"
    assert "literal_answer_placeholder" in prompt_defects(bad, VISIBLE_CONTROL_ARM)
    assert "unexpanded_template_token" in prompt_defects(
        "Value is {start} plus one.", VISIBLE_CONTROL_ARM
    )
    assert any(
        defect.startswith("think_tag_in_raw_strict")
        for defect in prompt_defects("<think></think> answer", SPONTANEOUS_NO_COT_ARM)
    )


# ---------------------------------------------------------------------------
# Registered budgets — the P10C-D2 repair
# ---------------------------------------------------------------------------


def test_the_visible_control_gets_at_least_1024_new_tokens():
    assert VISIBLE_MAX_NEW_TOKENS >= 1024
    assert generation_config(VISIBLE_CONTROL_ARM).max_new_tokens >= 1024


def test_the_strict_arms_keep_a_budget_that_cannot_hold_visible_reasoning():
    for arm in (STRUCTURAL_NO_COT_ARM, SPONTANEOUS_NO_COT_ARM):
        config = generation_config(arm)
        assert config.max_new_tokens == STRICT_MAX_NEW_TOKENS
        assert config.max_new_tokens < 64


def test_every_arm_decodes_greedily_so_the_arms_stay_comparable():
    for arm in ARMS:
        assert generation_config(arm).do_sample is False


def test_the_1_0d_profile_cannot_be_mistaken_for_the_registered_short_profile():
    for arm in ARMS:
        assert generation_config(arm).decoding_profile.startswith("phase1_0d_")


def test_the_strict_budget_provably_fits_every_registered_answer(bank):
    check = assert_strict_budget_fits_every_answer(bank)
    assert check["budget"] == STRICT_MAX_NEW_TOKENS
    assert check["longest_answer_bytes"] < STRICT_MAX_NEW_TOKENS
    assert check["headroom_tokens"] > 0


def test_an_answer_longer_than_the_budget_is_refused():
    with pytest.raises(Phase1_0DError):
        assert_strict_budget_fits_every_answer(
            [{"task_id": "synthetic", "registered_answer": "x" * 40}]
        )


# ---------------------------------------------------------------------------
# Adjudication rules (section 4.3)
# ---------------------------------------------------------------------------


def test_unresolved_and_invalid_rows_always_get_a_second_review():
    for label in ("unresolved", "invalid"):
        assert requires_secondary_review(
            "row-1", primary_label=label, parser_agrees_with_primary=True
        )


def test_every_parser_disagreement_gets_a_second_review():
    assert requires_secondary_review(
        "row-1", primary_label="correct", parser_agrees_with_primary=False
    )


def test_the_remaining_sample_is_deterministic_and_near_twenty_percent():
    ids = [f"p1hd-row-{index:04d}" for index in range(2000)]
    sampled = [
        record_id
        for record_id in ids
        if requires_secondary_review(
            record_id, primary_label="correct", parser_agrees_with_primary=True
        )
    ]
    again = [
        record_id
        for record_id in ids
        if requires_secondary_review(
            record_id, primary_label="correct", parser_agrees_with_primary=True
        )
    ]
    assert sampled == again
    assert 0.15 < len(sampled) / len(ids) < 0.25


def test_agreement_stands_and_disagreement_never_resolves_to_correct():
    assert arbitrate("correct", "correct")["final_label"] == "correct"
    disagreement = arbitrate("correct", "incorrect")
    assert disagreement["final_label"] == "unresolved"
    assert disagreement["arbitration_required"] is True
    assert disagreement["agreement"] is False


def test_a_row_without_a_second_review_keeps_the_primary_label():
    outcome = arbitrate("correct", None)
    assert outcome["final_label"] == "correct"
    assert outcome["agreement"] is None


def test_an_unregistered_label_is_refused():
    with pytest.raises(Phase1_0DError):
        arbitrate("probably_right", None)


def test_the_parser_may_only_route():
    assert protocol_snapshot()["parser_role"] == "routing_only"


# ---------------------------------------------------------------------------
# Cell gate (section 4.4)
# ---------------------------------------------------------------------------


def _outcome(arm_id, **kwargs):
    base = dict(
        task_family="arithmetic",
        difficulty_band="easy",
        arm_id=arm_id,
        resolved=20,
        correct=15,
        truncated=0,
        invalid=0,
        no_answer=0,
        placeholder=0,
        unresolved=0,
        loop_repetition=0,
    )
    base.update(kwargs)
    return CellOutcome(**base)


def test_a_clean_cell_passes_the_gate():
    visible = _outcome(VISIBLE_CONTROL_ARM.arm_id, correct=GATE_MIN_VISIBLE_CORRECT)
    strict = _outcome(SPONTANEOUS_NO_COT_ARM.arm_id, correct=GATE_STRICT_CORRECT_LOW)
    result = evaluate_cell_gate(visible, strict)
    assert result["rq2_pilot_candidate"] is True
    assert result["failed_criteria"] == []


def test_a_weak_control_fails_the_gate():
    visible = _outcome(VISIBLE_CONTROL_ARM.arm_id, correct=GATE_MIN_VISIBLE_CORRECT - 1)
    strict = _outcome(SPONTANEOUS_NO_COT_ARM.arm_id, correct=10)
    result = evaluate_cell_gate(visible, strict)
    assert result["rq2_pilot_candidate"] is False
    assert "visible_control_correct_at_least_14" in result["failed_criteria"]


def test_a_saturated_strict_arm_fails_the_gate():
    visible = _outcome(VISIBLE_CONTROL_ARM.arm_id, correct=20)
    strict = _outcome(
        SPONTANEOUS_NO_COT_ARM.arm_id, correct=GATE_STRICT_CORRECT_HIGH + 1
    )
    assert (
        "strict_correct_within_8_to_18"
        in evaluate_cell_gate(visible, strict)["failed_criteria"]
    )


def test_an_unresolved_row_fails_the_gate():
    visible = _outcome(VISIBLE_CONTROL_ARM.arm_id, resolved=19, correct=15, unresolved=1)
    strict = _outcome(SPONTANEOUS_NO_COT_ARM.arm_id, correct=12)
    assert (
        "all_visible_rows_resolved"
        in evaluate_cell_gate(visible, strict)["failed_criteria"]
    )


def test_excess_truncation_fails_the_gate():
    visible = _outcome(VISIBLE_CONTROL_ARM.arm_id, correct=18, truncated=3)
    strict = _outcome(SPONTANEOUS_NO_COT_ARM.arm_id, correct=12)
    assert (
        "visible_truncation_within_10_percent"
        in evaluate_cell_gate(visible, strict)["failed_criteria"]
    )


def test_the_gate_refuses_mismatched_arguments():
    visible = _outcome(VISIBLE_CONTROL_ARM.arm_id)
    strict = _outcome(SPONTANEOUS_NO_COT_ARM.arm_id, task_family="synthetic_relation")
    with pytest.raises(Phase1_0DError):
        evaluate_cell_gate(visible, strict)
    with pytest.raises(Phase1_0DError):
        evaluate_cell_gate(_outcome(SPONTANEOUS_NO_COT_ARM.arm_id), strict)


def test_the_gate_states_that_it_is_not_a_performance_claim():
    result = evaluate_cell_gate(
        _outcome(VISIBLE_CONTROL_ARM.arm_id),
        _outcome(SPONTANEOUS_NO_COT_ARM.arm_id, correct=10),
    )
    assert "not population performance claims" in result["interpretation"]


def test_cell_metrics_report_a_wilson_interval():
    row = _outcome(VISIBLE_CONTROL_ARM.arm_id, correct=15).as_dict()
    assert row["accuracy"] == 0.75
    assert 0.0 < row["wilson_95_low"] < 0.75 < row["wilson_95_high"] < 1.0


def test_paired_differences_use_the_same_items():
    visible = {"a": True, "b": True, "c": False}
    strict = {"a": True, "b": False, "c": False}
    paired = paired_difference(visible, strict)
    assert paired["paired_items"] == 3
    assert paired["visible_only_correct"] == 1
    assert paired["strict_only_correct"] == 0
    assert paired["difference"] == pytest.approx(1 / 3)


def test_paired_differences_need_shared_items():
    with pytest.raises(Phase1_0DError):
        paired_difference({"a": True}, {"b": True})


# ---------------------------------------------------------------------------
# Protocol snapshot
# ---------------------------------------------------------------------------


def test_the_snapshot_is_serializable_and_self_hashing(selection, used_item_ids):
    snapshot = protocol_snapshot(
        selection=selection_summary(selection, used_item_ids),
        strict_budget_check={"budget": STRICT_MAX_NEW_TOKENS},
    )
    assert json.loads(json.dumps(snapshot)) == snapshot
    assert len(snapshot["protocol_sha256"]) == 64


def test_the_snapshot_registers_all_three_arms():
    arms = protocol_snapshot()["arms"]
    assert [arm["arm_id"] for arm in arms] == [
        "visible_reasoning_control",
        "structural_no_cot",
        "spontaneous_no_cot",
    ]
    assert [arm["condition"] for arm in arms] == [
        "r1_style_thinking",
        "strict_answer_only_empty_think_prefill",
        "strict_answer_only",
    ]
    assert [arm["branch"] for arm in arms] == [
        "visible_reasoning_baseline",
        "prefill_intervention",
        "prompt_only_raw_strict",
    ]


def test_the_snapshot_records_both_repairs():
    repairs = protocol_snapshot()["repairs"]
    assert set(repairs) == {"P10C-D1", "P10C-D2"}


def test_the_snapshot_disclaims_hidden_reasoning():
    disclaimed = protocol_snapshot()["licenses_no_claim_about"]
    assert "J-space" in disclaimed
    assert "invisible chain-of-thought" in disclaimed


def test_the_committed_snapshot_matches_the_recomputed_protocol(
    selection, used_item_ids, bank
):
    artifact_path = REPO_ROOT / "docs" / "phase1_0d_protocol_snapshot.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    expected = protocol_snapshot(
        selection=selection_summary(selection, used_item_ids),
        strict_budget_check=assert_strict_budget_fits_every_answer(selection),
    )
    assert artifact["snapshot"] == expected
    assert artifact["status"] == "FROZEN_BEFORE_INFERENCE"
    assert artifact["context"]["eligible_pool"]["item_count"] == EXPECTED_ITEM_COUNT
    assert artifact["context"]["bank_item_count"] == len(bank)
    assert artifact["not_established"]
