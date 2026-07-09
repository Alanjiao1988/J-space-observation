"""Tests for raw-vs-postprocessed answer-only handling."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.postprocess import postprocess_answer_only


def test_postprocess_explicit_answer():
    result = postprocess_answer_only("Answer: 42")
    assert result.postprocessed_output == "42"
    assert result.postprocessed_answer_like
    assert result.postprocessed_no_cot_valid


def test_postprocess_boxed_truncates_before_wait():
    result = postprocess_answer_only("\\boxed{12}\n\nWait, I should check")
    assert result.postprocessed_output == "\\boxed{12}"
    assert result.postprocessing_applied
    assert result.postprocessing_reason == "boxed_answer_extracted"
    assert not result.raw_no_cot_valid
    assert result.postprocessed_no_cot_valid


def test_postprocess_incomplete_boxed_warns():
    result = postprocess_answer_only("7 + 5 = \\boxed")
    assert result.postprocessing_warning == "incomplete_boxed_answer"
    assert not result.postprocessed_answer_like


def test_postprocess_truncates_before_alright():
    result = postprocess_answer_only("12\n\nAlright, so I have")
    assert result.postprocessed_output == "12"
    assert result.postprocessing_reason == "truncated_before_reasoning_marker"
    assert not result.raw_no_cot_valid
    assert result.postprocessed_no_cot_valid


def test_postprocess_no_good_answer_from_reasoning_only():
    result = postprocess_answer_only("Step-by-step explanation: add 5 and 7.")
    assert result.postprocessing_warning
    assert not result.raw_no_cot_valid


def test_postprocess_final_answer_entity():
    result = postprocess_answer_only("Final answer: Paris\nExplanation: because...")
    assert result.postprocessed_output == "Paris"
    assert not result.raw_no_cot_valid
    assert result.postprocessed_no_cot_valid

