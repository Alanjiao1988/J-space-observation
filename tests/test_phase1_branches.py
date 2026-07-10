"""Tests for Phase 1 answer-control branch reporting."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.phase1_branches import (
    PHASE1_BRANCH_CLASSIFICATION_WARNING,
    PHASE1_INTERPRETATION_BOUNDARIES,
    POSTPROCESSED_UTILITY_BRANCH,
    RAW_STRICT_BRANCH,
    STOPPED_INTERVENTION_BRANCH,
    VISIBLE_REASONING_BASELINE_BRANCH,
    classify_branch_result,
    get_phase1_branch,
    get_phase1_branch_metadata,
    render_branch_metrics_table,
    render_branch_success_classification_section,
)


def test_raw_strict_conditions_share_branch():
    assert get_phase1_branch("strict_answer_only") == RAW_STRICT_BRANCH
    assert get_phase1_branch("strict_answer_only_prefill_answer") == RAW_STRICT_BRANCH


def test_stopped_condition_maps_to_intervention_branch():
    assert get_phase1_branch("strict_answer_only_stopped") == STOPPED_INTERVENTION_BRANCH


def test_postprocessed_condition_maps_to_utility_branch():
    assert get_phase1_branch("strict_answer_only_postprocessed") == POSTPROCESSED_UTILITY_BRANCH


def test_visible_conditions_are_labeled_as_baselines():
    assert get_phase1_branch("visible_cot") == VISIBLE_REASONING_BASELINE_BRANCH
    assert get_phase1_branch("r1_style_thinking") == VISIBLE_REASONING_BASELINE_BRANCH


def test_branch_metadata_is_record_ready():
    metadata = get_phase1_branch_metadata("strict_answer_only_stopped")
    assert metadata["phase1_branch"] == STOPPED_INTERVENTION_BRANCH
    assert "Stop-controlled" in metadata["phase1_branch_label"]
    assert "intervention" in metadata["phase1_branch_interpretation"]


def test_interpretation_boundaries_reject_cross_branch_claims():
    assert "Metrics from these branches are not interchangeable." in PHASE1_INTERPRETATION_BOUNDARIES
    assert "does not prove spontaneous no-CoT" in PHASE1_INTERPRETATION_BOUNDARIES
    assert "does not prove the raw model output was no-CoT" in PHASE1_INTERPRETATION_BOUNDARIES
    assert "No result in this Phase 1 pilot is hidden-reasoning or J-space evidence." in PHASE1_INTERPRETATION_BOUNDARIES


def test_branch_metrics_table_uses_na_for_non_applicable_metrics():
    table = render_branch_metrics_table(
        [
            {
                "model": "test-model",
                "task_family": "arithmetic",
                "depth": 1,
                "condition": "strict_answer_only_prefill_answer",
                "raw_no_cot_valid_rate": "1.0000",
                "stopped_no_cot_valid_rate": None,
                "postprocessed_no_cot_valid_rate": "NA",
                "stop_triggered_rate": None,
                "postprocessing_applied_rate": None,
                "accuracy_raw": "0.0000",
                "accuracy_stopped": None,
                "accuracy_postprocessed": None,
            }
        ]
    )
    assert "| raw_strict | strict_answer_only_prefill_answer |" in table
    assert "1.0000" in table
    assert "NA" in table


def passing_raw_metrics():
    return {
        "raw_no_cot_valid_rate": 0.90,
        "visible_reasoning_marker_rate": 0.10,
        "parse_valid_rate": 0.80,
        "parse_ambiguous_rate": 0.20,
        "answer_format_warning_rate": 0.20,
        "accuracy_raw": 0.50,
    }


def passing_stopped_metrics():
    return {
        "stopped_no_cot_valid_rate": 0.90,
        "stop_success_rate": 0.80,
        "parse_valid_rate": 0.80,
        "accuracy_stopped": 0.50,
    }


def passing_postprocessed_metrics():
    return {
        "postprocessed_no_cot_valid_rate": 0.90,
        "postprocessing_success_rate": 0.80,
        "postprocessing_warning_rate": 0.20,
        "accuracy_raw": 0.40,
        "accuracy_postprocessed": 0.50,
    }


def test_raw_strict_fails_when_raw_validity_is_low():
    metrics = passing_raw_metrics()
    metrics["raw_no_cot_valid_rate"] = 0.89

    result = classify_branch_result(RAW_STRICT_BRANCH, metrics)

    assert result["classification"] == "raw_strict_not_established"
    assert any("raw_no_cot_valid_rate" in item for item in result["criteria_failed"])


def test_raw_strict_surface_compliant_but_task_failed_when_accuracy_is_low():
    metrics = passing_raw_metrics()
    metrics["accuracy_raw"] = 0.49

    result = classify_branch_result(RAW_STRICT_BRANCH, metrics)

    assert result["classification"] == "surface_answer_only_but_task_failed"


def test_raw_strict_preliminarily_established_at_all_threshold_boundaries():
    result = classify_branch_result(RAW_STRICT_BRANCH, passing_raw_metrics())

    assert result["classification"] == "raw_strict_preliminarily_established"
    assert not result["criteria_failed"]


def test_raw_strict_accepts_relative_visible_cot_accuracy_standard():
    metrics = passing_raw_metrics()
    metrics["accuracy_raw"] = 0.49
    metrics["visible_cot_accuracy"] = 0.70

    result = classify_branch_result(RAW_STRICT_BRANCH, metrics)

    assert result["classification"] == "raw_strict_preliminarily_established"


def test_stopped_intervention_surface_compliant_but_task_failed_on_low_accuracy():
    metrics = passing_stopped_metrics()
    metrics["accuracy_stopped"] = 0.49

    result = classify_branch_result(STOPPED_INTERVENTION_BRANCH, metrics)

    assert result["classification"] == "stopped_surface_compliant_but_task_failed"


def test_stopped_intervention_usable_when_all_thresholds_pass():
    result = classify_branch_result(
        STOPPED_INTERVENTION_BRANCH,
        passing_stopped_metrics(),
    )

    assert result["classification"] == "stopped_intervention_usable"
    assert not result["criteria_failed"]


def test_stopped_intervention_warning_rejects_spontaneous_no_cot_claim():
    result = classify_branch_result(
        STOPPED_INTERVENTION_BRANCH,
        passing_stopped_metrics(),
    )

    assert "intervention" in result["interpretation_warning"]
    assert "not spontaneous no-CoT" in result["interpretation_warning"]


def test_postprocessed_answer_recovery_usable_when_accuracy_improves():
    result = classify_branch_result(
        POSTPROCESSED_UTILITY_BRANCH,
        passing_postprocessed_metrics(),
    )

    assert result["classification"] == "postprocessed_answer_recovery_usable"
    assert not result["criteria_failed"]


def test_postprocessed_warning_rejects_raw_no_cot_claim():
    result = classify_branch_result(
        POSTPROCESSED_UTILITY_BRANCH,
        passing_postprocessed_metrics(),
    )

    assert "not raw no-CoT" in result["interpretation_warning"]


def test_postprocessed_surface_clean_but_warning_high():
    metrics = passing_postprocessed_metrics()
    metrics["postprocessing_success_rate"] = 0.79
    metrics["postprocessing_warning_rate"] = 0.21

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["classification"] == "postprocessed_surface_clean_but_warning_high"
    assert any("postprocessing_success_rate" in item for item in result["criteria_failed"])


def test_postprocessed_utility_not_useful_when_validity_is_low():
    metrics = passing_postprocessed_metrics()
    metrics["postprocessed_no_cot_valid_rate"] = 0.89

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["classification"] == "postprocessed_utility_not_useful"


def test_branch_classification_summary_has_mandatory_scientific_warning():
    row = {
        "model": "test-model",
        "task_family": "arithmetic",
        "depth": 1,
        "branch": RAW_STRICT_BRANCH,
        "condition": "strict_answer_only",
        **passing_raw_metrics(),
    }

    section = render_branch_success_classification_section([row])

    assert PHASE1_BRANCH_CLASSIFICATION_WARNING in section
    assert "hidden reasoning" in section
    assert "internal workspace behavior" in section
    assert "J-space evidence" in section
    assert "raw_strict_preliminarily_established" in section
    assert "| test-model | arithmetic | 1 | raw_strict |" in section
    assert "stop_string_distribution" in section
    assert "NA" in section
