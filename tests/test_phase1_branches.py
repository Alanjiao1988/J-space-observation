"""Tests for Phase 1 answer-control branch reporting."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.phase1_branches import (
    PHASE1_INTERPRETATION_BOUNDARIES,
    POSTPROCESSED_UTILITY_BRANCH,
    RAW_STRICT_BRANCH,
    STOPPED_INTERVENTION_BRANCH,
    VISIBLE_REASONING_BASELINE_BRANCH,
    get_phase1_branch,
    get_phase1_branch_metadata,
    render_branch_metrics_table,
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
