"""Unit tests for no-CoT utilities."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation import (
    construct_empty_think_prefill_prompt,
    construct_answer_only_prompt,
    construct_prefill_answer_prompt,
    construct_visible_cot_prompt,
    construct_r1_style_thinking_prompt,
    get_generation_config_for_condition,
    validate_no_cot_output,
    extract_answer_from_output,
    create_generation_record,
    NoCoTValidationResult,
)


def test_empty_think_prefill_prompt():
    """Test empty think prefill prompt construction."""
    base = "What is 2+2?"
    result = construct_empty_think_prefill_prompt(base)
    assert "<think>" in result
    assert "</think>" in result
    assert base in result
    assert result.startswith(base)
    assert result.endswith("Answer:")
    assert result.index(base) < result.index("<think>")
    assert result.index("</think>") < result.index("Answer:")


def test_answer_only_prompt():
    """Test answer-only prompt construction."""
    base = "What is 2+2?"
    result = construct_answer_only_prompt(base)
    assert base in result
    assert "Answer" in result or "answer" in result


def test_prefill_answer_prompt_is_strict_and_ends_with_answer():
    base = "What is 2+2?"
    result = construct_prefill_answer_prompt(base)
    assert result.startswith(base)
    assert "Do not explain" in result
    assert "Do not show steps" in result
    assert "Do not include <think> tags" in result
    assert "show your reasoning" not in result.lower()
    assert result.endswith("Answer:")


def test_visible_cot_prompt():
    """Test visible CoT prompt construction."""
    base = "What is 2+2?"
    result = construct_visible_cot_prompt(base)
    assert base in result
    assert "step" in result.lower() or "reason" in result.lower()


def test_r1_style_thinking_prompt():
    """Test R1-style thinking prompt construction."""
    base = "What is 2+2?"
    result = construct_r1_style_thinking_prompt(base)
    assert base in result


def test_strict_generation_config_uses_small_budget():
    cfg = get_generation_config_for_condition("strict_answer_only", 64)
    assert cfg.max_new_tokens == 12
    assert cfg.temperature == 0.0
    assert not cfg.do_sample
    assert "strict" in cfg.decoding_profile


def test_prefill_generation_config_uses_tiny_budget():
    cfg = get_generation_config_for_condition("strict_answer_only_prefill_answer", 64)
    assert cfg.max_new_tokens == 8
    assert cfg.temperature == 0.0
    assert not cfg.do_sample
    assert "prefill" in cfg.decoding_profile


def test_visible_generation_config_is_not_tightened():
    cfg = get_generation_config_for_condition("visible_cot", 64)
    assert cfg.max_new_tokens == 64
    assert cfg.temperature == 1.0
    assert not cfg.do_sample
    assert cfg.decoding_profile == "default_greedy"


def test_r1_generation_config_is_not_tightened():
    cfg = get_generation_config_for_condition("r1_style_thinking", 64)
    assert cfg.max_new_tokens == 64
    assert cfg.decoding_profile == "default_greedy"


def test_validate_no_cot_empty_think_valid():
    """Test validation with valid empty-think output."""
    output = "The answer is 4."
    result = validate_no_cot_output(
        output,
        method="empty_think_prefill",
        allow_visible_reasoning=False
    )
    assert result.is_valid
    assert result.reason_for_invalidity is None


def test_validate_no_cot_with_think_tag():
    """Test validation detects think tag content."""
    output = "<think>2 + 2 = 4</think>\n\nThe answer is 4."
    result = validate_no_cot_output(
        output,
        method="empty_think_prefill",
        allow_visible_reasoning=False
    )
    assert not result.is_valid
    assert result.reason_for_invalidity == "think_tag_generated"
    assert result.has_think_tag


def test_validate_no_cot_with_visible_reasoning():
    """Test validation detects visible reasoning."""
    output = "Step 1: We need to add 2+2.\nStep 2: The result is 4."
    result = validate_no_cot_output(
        output,
        method="empty_think_prefill",
        allow_visible_reasoning=False
    )
    assert not result.is_valid
    assert result.reason_for_invalidity == "intermediate_steps_generated"
    assert "intermediate_steps_generated" in result.violation_reasons


@pytest.mark.parametrize(
    "output",
    [
        "Step-by-step explanation: 7 + 5 = 12, so the answer is 12.",
        "Follow these steps: first add 7 and 5. The answer is 12.",
        "First, compute 7 + 5. Then, write 12.",
        "To solve this, add the numbers.\n1) 7 + 5 = 12\nAnswer: 12",
        "Alright, so I have this problem.",
        "Wait, that answer needs checking.",
    ],
)
def test_validate_no_cot_rejects_reasoning_markers(output):
    result = validate_no_cot_output(output, method="empty_think_prefill")
    assert not result.is_valid
    assert result.has_visible_reasoning_marker
    assert result.violation_reasons


def test_validate_no_cot_allows_short_numeric_answer():
    result = validate_no_cot_output("42", method="empty_think_prefill")
    assert result.is_valid
    assert result.violation_reasons == []


def test_validate_no_cot_allows_short_answer_cue():
    result = validate_no_cot_output("Answer: 42", method="empty_think_prefill")
    assert result.is_valid


def test_validate_no_cot_allows_short_entity_answer():
    result = validate_no_cot_output("Paris", method="answer_only_prompt")
    assert result.is_valid


def test_validate_no_cot_rejects_multiline_explanation():
    output = "Answer: 12\nExplanation:\nFirst add 7.\nThen add 5."
    result = validate_no_cot_output(output, method="empty_think_prefill")
    assert not result.is_valid
    assert "reasoning_heading_generated" in result.violation_reasons


def test_generation_record_preserves_decoding_metadata():
    record = create_generation_record(
        prompt="What is 2+2?\n\nAnswer:",
        output="4",
        no_cot_method="answer_prefill",
        model_name="test-model",
        condition_max_new_tokens=8,
        condition_temperature=0.0,
        condition_do_sample=False,
        decoding_profile="strict_prefill_answer_only_max8",
    )
    assert record["no_cot_validity"] is True
    assert record["decoding_profile"] == "strict_prefill_answer_only_max8"
    assert record["condition_max_new_tokens"] == 8


def test_validate_no_cot_token_budget():
    """Test validation respects token budget."""
    output = "The answer is 4."
    result = validate_no_cot_output(
        output,
        method="empty_think_prefill",
        max_token_count=1  # Very tight budget
    )
    assert not result.is_valid
    assert result.reason_for_invalidity == "exceeded_token_budget"


def test_extract_answer_from_output_simple():
    """Test extracting answer from simple output."""
    output = "The answer is 4."
    result = extract_answer_from_output(output)
    assert "4" in result
    assert result.strip() == "The answer is 4."


def test_extract_answer_removes_think_tags():
    """Test that think tags are removed."""
    output = "<think>2+2=4</think>\n\nThe answer is 4."
    result = extract_answer_from_output(output)
    assert "<think>" not in result
    assert "4" in result
