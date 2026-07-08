"""Unit tests for no-CoT utilities."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation import (
    construct_empty_think_prefill_prompt,
    construct_answer_only_prompt,
    construct_visible_cot_prompt,
    construct_r1_style_thinking_prompt,
    validate_no_cot_output,
    extract_answer_from_output,
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
    assert result.reason_for_invalidity == "visible_reasoning_generated"


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
