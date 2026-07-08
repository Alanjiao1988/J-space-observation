"""Unit tests for evaluation parsing."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation import (
    parse_numeric_answer,
    parse_entity_answer,
    parse_yes_no_answer,
    parse_answer,
    evaluate_answer,
)


def test_parse_numeric_simple():
    """Test parsing simple numeric answer."""
    output = "The answer is 12."
    result = parse_numeric_answer(output)
    assert result.parse_valid
    assert result.parsed_answer == "12"


def test_parse_numeric_negative():
    """Test parsing negative numbers."""
    output = "The result is -5."
    result = parse_numeric_answer(output)
    assert result.parse_valid
    assert result.parsed_answer == "-5"


def test_parse_numeric_float():
    """Test parsing floating point."""
    output = "The answer is 3.14."
    result = parse_numeric_answer(output)
    assert result.parse_valid
    assert result.parsed_answer == "3.14"


def test_parse_numeric_no_number():
    """Test handling when no number found."""
    output = "I cannot solve this."
    result = parse_numeric_answer(output)
    assert not result.parse_valid
    assert result.parse_error_type == "no_numeric_found"


def test_parse_numeric_multiple_numbers():
    """Test parsing last number when multiple exist."""
    output = "5 + 7 = 12"
    result = parse_numeric_answer(output)
    assert result.parse_valid
    # Should return the last number
    assert result.parsed_answer == "12"


def test_parse_entity_simple():
    """Test parsing entity answer."""
    output = "Paris"
    result = parse_entity_answer(output)
    assert result.parse_valid
    assert result.parsed_answer == "Paris"


def test_parse_entity_with_prefix():
    """Test parsing entity with answer prefix."""
    output = "The answer is Paris."
    result = parse_entity_answer(output)
    assert result.parse_valid
    assert "Paris" in result.parsed_answer


def test_parse_entity_empty():
    """Test handling empty output."""
    output = ""
    result = parse_entity_answer(output)
    assert not result.parse_valid


def test_parse_yes_no_yes():
    """Test parsing yes answer."""
    output = "Yes, that is correct."
    result = parse_yes_no_answer(output)
    assert result.parse_valid
    assert result.parsed_answer == "yes"


def test_parse_yes_no_no():
    """Test parsing no answer."""
    output = "No, that is not right."
    result = parse_yes_no_answer(output)
    assert result.parse_valid
    assert result.parsed_answer == "no"


def test_parse_yes_no_true():
    """Test parsing true as yes."""
    output = "True"
    result = parse_yes_no_answer(output)
    assert result.parse_valid
    assert result.parsed_answer == "yes"


def test_parse_yes_no_false():
    """Test parsing false as no."""
    output = "False"
    result = parse_yes_no_answer(output)
    assert result.parse_valid
    assert result.parsed_answer == "no"


def test_parse_answer_dispatch_numeric():
    """Test parse_answer dispatches correctly."""
    output = "42"
    result = parse_answer(output, parse_type="numeric")
    assert result.parse_valid
    assert result.parsed_answer == "42"


def test_evaluate_answer_correct():
    """Test evaluating correct answer."""
    is_correct, error = evaluate_answer("12", "12", parse_valid=True)
    assert is_correct
    assert error is None


def test_evaluate_answer_wrong():
    """Test evaluating wrong answer."""
    is_correct, error = evaluate_answer("10", "12", parse_valid=True)
    assert not is_correct
    assert error == "numeric_mismatch"


def test_evaluate_answer_parse_failed():
    """Test evaluating with parse failure."""
    is_correct, error = evaluate_answer(None, "12", parse_valid=False)
    assert not is_correct
    assert error == "parse_failed"


def test_evaluate_answer_case_insensitive():
    """Test case insensitive string comparison."""
    is_correct, error = evaluate_answer("Paris", "paris", parse_valid=True)
    assert is_correct


def test_evaluate_answer_partial_match():
    """Test partial entity match."""
    is_correct, error = evaluate_answer("Paris", "Paris, France", parse_valid=True)
    assert is_correct
