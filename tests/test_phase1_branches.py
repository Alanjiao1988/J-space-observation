"""Tests for Phase 1 answer-control branch reporting."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.phase1_branches import (
    BRANCH_ABSOLUTE_ACCURACY_FLOOR,
    MIN_BRANCH_CLASSIFICATION_N,
    MIN_VISIBLE_COT_BASELINE_N,
    MIN_VISIBLE_COT_PARSE_VALID_RATE,
    PHASE1_BRANCH_CLASSIFICATION_WARNING,
    PHASE1_BRANCH_SAMPLE_SIZE_WARNING,
    PHASE1_INTERPRETATION_BOUNDARIES,
    PHASE1_POSTPROCESSING_ACCURACY_WARNING,
    PHASE1_VISIBLE_COT_BASELINE_WARNING,
    PHASE1_PREFILL_CLASSIFICATION_WARNING,
    LEGACY_BRANCH_TAXONOMY_VERSION,
    PROSPECTIVE_BRANCH_TAXONOMY_VERSION,
    LEGACY_CONDITION_TO_BRANCH,
    POSTPROCESSED_UTILITY_BRANCH,
    PREFILL_INTERVENTION_BRANCH,
    PROMPT_ONLY_RAW_STRICT_BRANCH,
    RAW_STRICT_BRANCH,
    STOPPED_INTERVENTION_BRANCH,
    UNCLASSIFIED_BRANCH,
    VISIBLE_REASONING_BASELINE_BRANCH,
    classify_branch_result,
    evaluate_visible_cot_baseline,
    get_legacy_phase1_branch,
    get_phase1_branch,
    get_phase1_branch_metadata,
    get_prospective_phase1_branch,
    resolve_branch_taxonomy_version,
    render_branch_metrics_table,
    render_branch_success_classification_section,
)


def test_raw_strict_conditions_share_branch():
    assert get_phase1_branch("strict_answer_only") == RAW_STRICT_BRANCH
    assert get_phase1_branch("strict_answer_only_prefill_answer") == RAW_STRICT_BRANCH


@pytest.mark.parametrize(
    ("condition", "legacy_branch", "prospective_branch"),
    [
        (
            "strict_answer_only",
            RAW_STRICT_BRANCH,
            PROMPT_ONLY_RAW_STRICT_BRANCH,
        ),
        (
            "strict_answer_only_prefill_answer",
            RAW_STRICT_BRANCH,
            PREFILL_INTERVENTION_BRANCH,
        ),
        (
            "strict_answer_only_empty_think_prefill",
            UNCLASSIFIED_BRANCH,
            PREFILL_INTERVENTION_BRANCH,
        ),
        (
            "strict_answer_only_stopped",
            STOPPED_INTERVENTION_BRANCH,
            STOPPED_INTERVENTION_BRANCH,
        ),
        (
            "strict_answer_only_postprocessed",
            POSTPROCESSED_UTILITY_BRANCH,
            POSTPROCESSED_UTILITY_BRANCH,
        ),
        (
            "visible_cot",
            VISIBLE_REASONING_BASELINE_BRANCH,
            VISIBLE_REASONING_BASELINE_BRANCH,
        ),
        (
            "r1_style_thinking",
            VISIBLE_REASONING_BASELINE_BRANCH,
            VISIBLE_REASONING_BASELINE_BRANCH,
        ),
    ],
)
def test_v1_and_v2_crosswalk_rows(condition, legacy_branch, prospective_branch):
    assert get_legacy_phase1_branch(condition) == legacy_branch
    assert get_phase1_branch(condition) == legacy_branch
    assert (
        get_phase1_branch(condition, LEGACY_BRANCH_TAXONOMY_VERSION)
        == legacy_branch
    )
    assert get_prospective_phase1_branch(condition) == prospective_branch
    assert (
        get_phase1_branch(condition, PROSPECTIVE_BRANCH_TAXONOMY_VERSION)
        == prospective_branch
    )


def test_missing_taxonomy_version_is_v1_and_legacy_mapping_is_immutable():
    assert resolve_branch_taxonomy_version(None) == LEGACY_BRANCH_TAXONOMY_VERSION
    assert (
        get_phase1_branch("strict_answer_only_prefill_answer")
        == RAW_STRICT_BRANCH
    )
    with pytest.raises(TypeError):
        LEGACY_CONDITION_TO_BRANCH["strict_answer_only"] = "changed"


def test_stopped_condition_maps_to_intervention_branch():
    assert get_phase1_branch("strict_answer_only_stopped") == STOPPED_INTERVENTION_BRANCH


def test_postprocessed_condition_maps_to_utility_branch():
    assert get_phase1_branch("strict_answer_only_postprocessed") == POSTPROCESSED_UTILITY_BRANCH


def test_visible_conditions_are_labeled_as_baselines():
    assert get_phase1_branch("visible_cot") == VISIBLE_REASONING_BASELINE_BRANCH
    assert get_phase1_branch("r1_style_thinking") == VISIBLE_REASONING_BASELINE_BRANCH


def test_branch_metadata_is_record_ready():
    metadata = get_phase1_branch_metadata(
        "strict_answer_only_prefill_answer",
        taxonomy_version=PROSPECTIVE_BRANCH_TAXONOMY_VERSION,
    )
    assert (
        metadata["branch_taxonomy_version"]
        == PROSPECTIVE_BRANCH_TAXONOMY_VERSION
    )
    assert metadata["legacy_phase1_branch"] == RAW_STRICT_BRANCH
    assert metadata["prospective_phase1_branch"] == PREFILL_INTERVENTION_BRANCH
    assert metadata["phase1_branch"] == metadata["legacy_phase1_branch"]

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


def test_prospective_prefill_report_does_not_reuse_raw_success_criteria():
    section = render_branch_success_classification_section(
        [
            {
                "model": "test-model",
                "task_family": "arithmetic",
                "depth": 1,
                "condition": "strict_answer_only_prefill_answer",
                "branch_taxonomy_version": "v2",
                "legacy_phase1_branch": RAW_STRICT_BRANCH,
                "prospective_phase1_branch": PREFILL_INTERVENTION_BRANCH,
                "branch": PREFILL_INTERVENTION_BRANCH,
                **passing_raw_metrics(),
            }
        ]
    )

    assert "| prefill_intervention | strict_answer_only_prefill_answer | v2 |" in section
    assert "not_applicable" in section
    assert "prospective_prefill_intervention_success_criteria" in section
    assert "raw_strict_preliminarily_established" not in section


def valid_visible_cot_baseline():
    return {
        "visible_cot_n": MIN_VISIBLE_COT_BASELINE_N,
        "visible_cot_accuracy": 0.60,
        "visible_cot_parse_valid_rate": MIN_VISIBLE_COT_PARSE_VALID_RATE,
        "visible_cot_answer_format_warning_rate": 0.0,
    }


def passing_raw_metrics():
    return {
        "n": MIN_BRANCH_CLASSIFICATION_N,
        "raw_no_cot_valid_rate": 0.90,
        "visible_reasoning_marker_rate": 0.10,
        "parse_valid_rate": 0.80,
        "parse_ambiguous_rate": 0.20,
        "answer_format_warning_rate": 0.20,
        "accuracy_raw": 0.50,
        **valid_visible_cot_baseline(),
    }


def passing_stopped_metrics():
    return {
        "n": MIN_BRANCH_CLASSIFICATION_N,
        "stopped_no_cot_valid_rate": 0.90,
        "stop_success_rate": 0.80,
        "parse_valid_rate": 0.80,
        "accuracy_stopped": 0.50,
        **valid_visible_cot_baseline(),
    }


def passing_postprocessed_metrics():
    return {
        "n": MIN_BRANCH_CLASSIFICATION_N,
        "postprocessed_no_cot_valid_rate": 0.90,
        "postprocessing_success_rate": 0.80,
        "postprocessing_warning_rate": 0.20,
        "accuracy_raw": 0.30,
        "accuracy_postprocessed": 0.60,
        **valid_visible_cot_baseline(),
    }


def test_prospective_prefill_classification_is_explicitly_not_applicable():
    result = classify_branch_result(
        PREFILL_INTERVENTION_BRANCH,
        passing_raw_metrics(),
    )

    assert result["classification"] == "not_applicable"
    assert result["absolute_accuracy_passed"] is None
    assert result["classification_criteria_version"] is None
    assert result["criteria_passed"] == []
    assert result["criteria_failed"] == []
    assert result["criteria_not_applicable"] == [
        "prospective_prefill_intervention_success_criteria"
    ]
    assert "not spontaneous no-CoT" in result["interpretation_warning"]


def test_prompt_only_branch_labels_reused_raw_criteria_as_historical_v1():
    result = classify_branch_result(
        PROMPT_ONLY_RAW_STRICT_BRANCH,
        passing_raw_metrics(),
    )

    assert result["classification"] == "raw_strict_preliminarily_established"
    assert result["classification_criteria_version"] == "v1"
    assert result["classification_criteria_branch"] == RAW_STRICT_BRANCH


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


def test_raw_strict_relative_gate_does_not_replace_absolute_floor():
    metrics = passing_raw_metrics()
    metrics["accuracy_raw"] = 0.49

    result = classify_branch_result(RAW_STRICT_BRANCH, metrics)

    assert result["absolute_accuracy_passed"] is False
    assert result["relative_accuracy_gate_passed"] is True
    assert result["classification"] == "surface_answer_only_but_task_failed"


def test_raw_strict_valid_visible_cot_baseline_applies_relative_gate():
    metrics = passing_raw_metrics()
    metrics["visible_cot_accuracy"] = 0.80

    result = classify_branch_result(RAW_STRICT_BRANCH, metrics)

    assert result["baseline_valid"] is True
    assert result["relative_accuracy_gate_applicable"] is True
    assert result["relative_accuracy_gate_passed"] is False
    assert result["classification"] == "surface_answer_only_but_task_failed"


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


def test_stopped_intervention_valid_baseline_applies_relative_gate():
    metrics = passing_stopped_metrics()
    metrics["visible_cot_accuracy"] = 0.80

    result = classify_branch_result(STOPPED_INTERVENTION_BRANCH, metrics)

    assert result["absolute_accuracy_passed"] is True
    assert result["relative_accuracy_gate_passed"] is False
    assert result["classification"] == "stopped_surface_compliant_but_task_failed"


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


def test_postprocessed_zero_non_degradation_fails_absolute_floor():
    metrics = passing_postprocessed_metrics()
    metrics["accuracy_raw"] = 0.0
    metrics["accuracy_postprocessed"] = 0.0

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["absolute_accuracy_floor"] == BRANCH_ABSOLUTE_ACCURACY_FLOOR
    assert result["absolute_accuracy_passed"] is False
    assert result["classification"] == "postprocessed_surface_clean_but_task_failed"


def test_postprocessed_non_degradation_below_absolute_floor_is_not_usable():
    metrics = passing_postprocessed_metrics()
    metrics["accuracy_raw"] = 0.20
    metrics["accuracy_postprocessed"] = 0.30

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert any(
        "accuracy_postprocessed >= accuracy_raw" in criterion
        for criterion in result["criteria_passed"]
    )
    assert result["absolute_accuracy_passed"] is False
    assert result["classification"] == "postprocessed_surface_clean_but_task_failed"


def test_postprocessed_non_degradation_and_absolute_floor_can_be_usable():
    metrics = passing_postprocessed_metrics()
    metrics["accuracy_raw"] = 0.30
    metrics["accuracy_postprocessed"] = 0.60

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["absolute_accuracy_passed"] is True
    assert result["classification"] == "postprocessed_answer_recovery_usable"


def test_postprocessed_visible_cot_relative_comparison_is_report_only():
    metrics = passing_postprocessed_metrics()
    metrics["visible_cot_accuracy"] = 1.0

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["relative_accuracy_gate_applicable"] is True
    assert result["relative_accuracy_gate_required"] is False
    assert result["relative_accuracy_gate_passed"] is False
    assert result["classification"] == "postprocessed_answer_recovery_usable"


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


def test_postprocessed_task_failure_takes_priority_over_warning_failure():
    metrics = passing_postprocessed_metrics()
    metrics["postprocessing_warning_rate"] = 0.21
    metrics["accuracy_raw"] = 0.0
    metrics["accuracy_postprocessed"] = 0.0

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["classification"] == "postprocessed_surface_clean_but_task_failed"
    assert any(
        "postprocessing_warning_rate" in criterion
        for criterion in result["criteria_failed"]
    )


def test_postprocessed_utility_not_useful_when_validity_is_low():
    metrics = passing_postprocessed_metrics()
    metrics["postprocessed_no_cot_valid_rate"] = 0.89

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["classification"] == "postprocessed_utility_not_useful"


def test_visible_cot_zero_accuracy_makes_relative_gate_not_applicable():
    metrics = passing_raw_metrics()
    metrics["visible_cot_accuracy"] = 0.0

    result = classify_branch_result(RAW_STRICT_BRANCH, metrics)

    assert result["baseline_valid"] is False
    assert "visible_cot_accuracy_zero" in result["baseline_failure_reasons"]
    assert result["relative_accuracy_gate_passed"] is None
    assert "relative_accuracy_gate" in result["criteria_not_applicable"]


def test_visible_cot_parse_invalidates_baseline():
    metrics = valid_visible_cot_baseline()
    metrics["visible_cot_parse_valid_rate"] = 0.79

    baseline = evaluate_visible_cot_baseline(metrics)

    assert baseline["baseline_valid"] is False
    assert "visible_cot_parse_invalid" in baseline["baseline_failure_reasons"]


def test_visible_cot_small_sample_invalidates_baseline():
    metrics = valid_visible_cot_baseline()
    metrics["visible_cot_n"] = MIN_VISIBLE_COT_BASELINE_N - 1

    baseline = evaluate_visible_cot_baseline(metrics)

    assert baseline["baseline_valid"] is False
    assert "insufficient_visible_cot_samples" in baseline["baseline_failure_reasons"]


def test_visible_cot_valid_baseline_is_available_for_relative_comparison():
    baseline = evaluate_visible_cot_baseline(valid_visible_cot_baseline())

    assert baseline["baseline_available"] is True
    assert baseline["baseline_valid"] is True
    assert baseline["baseline_failure_reasons"] == []


def test_raw_strict_success_is_pilot_only_below_minimum_sample_size():
    metrics = passing_raw_metrics()
    metrics["n"] = 1

    result = classify_branch_result(RAW_STRICT_BRANCH, metrics)

    assert result["sample_size_sufficient"] is False
    assert result["classification"] == "raw_strict_pilot_only"
    assert result["classification_is_provisional"] is True


def test_stopped_failure_label_is_preserved_below_minimum_sample_size():
    metrics = passing_stopped_metrics()
    metrics["n"] = 1
    metrics["stop_success_rate"] = 0.0
    metrics["accuracy_stopped"] = 0.0

    result = classify_branch_result(STOPPED_INTERVENTION_BRANCH, metrics)

    assert result["sample_size_sufficient"] is False
    assert result["classification"] == "stopped_intervention_not_useful"


def test_stopped_success_is_formal_at_minimum_sample_size():
    result = classify_branch_result(
        STOPPED_INTERVENTION_BRANCH,
        passing_stopped_metrics(),
    )

    assert result["sample_size_sufficient"] is True
    assert result["classification"] == "stopped_intervention_usable"
    assert result["classification_is_provisional"] is False


def test_postprocessed_success_is_pilot_only_below_minimum_sample_size():
    metrics = passing_postprocessed_metrics()
    metrics["n"] = 1

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["classification"] == "postprocessed_utility_pilot_only"
    assert result["classification_is_provisional"] is True


def test_postprocessed_success_is_formal_at_minimum_sample_size():
    result = classify_branch_result(
        POSTPROCESSED_UTILITY_BRANCH,
        passing_postprocessed_metrics(),
    )

    assert result["sample_size_sufficient"] is True
    assert result["classification"] == "postprocessed_answer_recovery_usable"


def test_depth3_zero_non_degradation_regression_is_task_failed_even_at_n_one():
    metrics = {
        "n": 1,
        "raw_no_cot_valid_rate": 0.0,
        "postprocessed_no_cot_valid_rate": 1.0,
        "postprocessing_success_rate": 1.0,
        "postprocessing_warning_rate": 0.0,
        "accuracy_raw": 0.0,
        "accuracy_postprocessed": 0.0,
        **valid_visible_cot_baseline(),
    }

    result = classify_branch_result(POSTPROCESSED_UTILITY_BRANCH, metrics)

    assert result["classification"] == "postprocessed_surface_clean_but_task_failed"
    assert result["classification"] != "postprocessed_answer_recovery_usable"


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
    assert PHASE1_BRANCH_SAMPLE_SIZE_WARNING in section
    assert PHASE1_VISIBLE_COT_BASELINE_WARNING in section
    assert PHASE1_POSTPROCESSING_ACCURACY_WARNING in section
    assert PHASE1_PREFILL_CLASSIFICATION_WARNING in section
    assert "hidden reasoning" in section
    assert "internal workspace behavior" in section
    assert "J-space evidence" in section
    assert "raw_strict_preliminarily_established" in section
    assert "| test-model | arithmetic | 1 | raw_strict |" in section
    assert "stop_string_distribution" in section
    assert "minimum_n" in section
    assert "sample_size_sufficient" in section
    assert "visible_cot_baseline_valid" in section
    assert "relative_accuracy_gate" in section
    assert "criteria_not_applicable" in section
    assert "NA" in section
