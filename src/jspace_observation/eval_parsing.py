"""Answer parsing and evaluation utilities."""

import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParseResult:
    """Result of parsing model output."""
    parsed_answer: Optional[str] = None
    parse_valid: bool = False
    parse_error_type: Optional[str] = None
    parse_ambiguous: bool = False
    parse_strategy: Optional[str] = None
    candidate_answers: Optional[list[str]] = None
    answer_format_warning: Optional[str] = None


def parse_numeric_answer(output: str) -> ParseResult:
    """
    Parse numeric answer from output.
    
    Looks for patterns like "12", "-5", "3.14", etc.
    Prioritizes final numeric value in the output.
    
    Args:
        output: Model output text
    
    Returns:
        ParseResult with parsed numeric answer
    """
    text = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL | re.IGNORECASE)

    # Prefer explicit final-answer forms when available.
    final_patterns = [
        r"(?:final\s+answer|answer|the\s+answer\s+is)\s*[:：]?\s*(-?\d+(?:\.\d+)?)",
    ]
    explicit_matches = []
    for pattern in final_patterns:
        explicit_matches.extend(re.findall(pattern, text, flags=re.IGNORECASE))

    # Find all numeric patterns
    numeric_pattern = r'-?\d+(?:\.\d+)?'
    matches = re.findall(numeric_pattern, text)
    
    if not matches:
        return ParseResult(
            parse_valid=False,
            parse_error_type="no_numeric_found",
            candidate_answers=[],
            parse_strategy="no_numeric_found",
        )

    reasoning_like = bool(
        re.search(
            r"step[-\s]*by[-\s]*step|explanation|follow these steps|to solve|first,|then,|therefore|because|\bstep\s*\d+\b",
            text,
            flags=re.IGNORECASE,
        )
    )

    if explicit_matches:
        parsed_answer = explicit_matches[-1]
        strategy = "explicit_answer"
    else:
        # Return the last numeric match (likely the final answer), but make the
        # strategy explicit so downstream analysis can audit ambiguity.
        parsed_answer = matches[-1]
        strategy = "single_number" if len(matches) == 1 else "last_number"

    parse_ambiguous = len(matches) > 1 and (reasoning_like or len(text) > 80)
    warning = None
    if parse_ambiguous:
        warning = f"multiple_numeric_candidates:{len(matches)}"
    elif len(matches) > 1:
        warning = f"multiple_numbers_short_output:{len(matches)}"
    
    return ParseResult(
        parsed_answer=parsed_answer,
        parse_valid=True,
        parse_ambiguous=parse_ambiguous,
        parse_strategy=strategy,
        candidate_answers=matches,
        answer_format_warning=warning,
    )


def parse_entity_answer(output: str, max_length: int = 50) -> ParseResult:
    """
    Parse entity/string answer from output.
    
    Looks for short strings that could be entity names.
    
    Args:
        output: Model output text
        max_length: Maximum length for entity name
    
    Returns:
        ParseResult with parsed entity
    """
    # Remove think tags first
    text = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL)
    text = text.strip()
    
    if not text:
        return ParseResult(parse_valid=False, parse_error_type="empty_output", parse_strategy="entity_last_line")
    
    # Split into lines and find meaningful lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        return ParseResult(parse_valid=False, parse_error_type="no_lines", parse_strategy="entity_last_line")
    
    # Take the last line, it's likely the answer
    candidate = lines[-1]
    
    # Clean up common answer markers
    candidate = re.sub(r'^(?:answer[:\s]+|final answer[:\s]+|the answer is[:\s]+)', '', candidate, flags=re.IGNORECASE)
    candidate = candidate.strip()
    
    # Remove trailing punctuation
    candidate = re.sub(r'[.,!?;]*$', '', candidate)
    candidate = candidate.strip()
    
    if len(candidate) > max_length:
        return ParseResult(
            parse_valid=False,
            parse_error_type="answer_too_long",
            parse_ambiguous=True,
            parse_strategy="entity_last_line",
            answer_format_warning="entity_answer_too_long",
        )
    
    if not candidate:
        return ParseResult(parse_valid=False, parse_error_type="empty_after_cleaning", parse_strategy="entity_last_line")
    
    return ParseResult(
        parsed_answer=candidate,
        parse_valid=True,
        parse_ambiguous=len(lines) > 1,
        parse_strategy="entity_last_line",
        candidate_answers=[candidate],
        answer_format_warning="multi_line_entity_output" if len(lines) > 1 else None,
    )


def parse_yes_no_answer(output: str) -> ParseResult:
    """
    Parse yes/no answer from output.
    
    Args:
        output: Model output text
    
    Returns:
        ParseResult with yes/no answer
    """
    text = output.lower()
    
    # Remove think tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Look for yes pattern
    if re.search(r'\byes\b', text):
        return ParseResult(parsed_answer="yes", parse_valid=True, parse_strategy="yes_no_keyword", candidate_answers=["yes"])
    
    # Look for no pattern
    if re.search(r'\bno\b', text):
        return ParseResult(parsed_answer="no", parse_valid=True, parse_strategy="yes_no_keyword", candidate_answers=["no"])
    
    # Look for true/false as fallback
    if re.search(r'\btrue\b', text):
        return ParseResult(parsed_answer="yes", parse_valid=True, parse_strategy="true_false_keyword", candidate_answers=["true"])
    
    if re.search(r'\bfalse\b', text):
        return ParseResult(parsed_answer="no", parse_valid=True, parse_strategy="true_false_keyword", candidate_answers=["false"])
    
    return ParseResult(parse_valid=False, parse_error_type="no_yes_no_found", parse_strategy="yes_no_keyword")


def parse_answer(
    output: str,
    parse_type: str = "numeric",
    **kwargs
) -> ParseResult:
    """
    Parse answer based on type.
    
    Args:
        output: Model output text
        parse_type: Type of answer (numeric, entity, yes_no)
        **kwargs: Additional arguments for specific parsers
    
    Returns:
        ParseResult
    """
    if parse_type == "numeric":
        return parse_numeric_answer(output)
    elif parse_type == "entity":
        return parse_entity_answer(output, **kwargs)
    elif parse_type == "yes_no":
        return parse_yes_no_answer(output)
    else:
        return ParseResult(parse_valid=False, parse_error_type="unknown_parse_type")


def evaluate_answer(
    parsed_answer: Optional[str],
    expected_answer: str,
    parse_valid: bool
) -> Tuple[bool, Optional[str]]:
    """
    Evaluate correctness of parsed answer.
    
    Args:
        parsed_answer: The parsed answer from model
        expected_answer: The ground truth answer
        parse_valid: Whether parsing succeeded
    
    Returns:
        Tuple of (is_correct, error_type)
    """
    if not parse_valid:
        return False, "parse_failed"
    
    if parsed_answer is None:
        return False, "parse_failed"
    
    # Normalize for comparison
    parsed_norm = str(parsed_answer).strip().lower()
    expected_norm = str(expected_answer).strip().lower()
    
    # Try numeric comparison if both look numeric
    if parsed_norm.replace('-', '', 1).replace('.', '', 1).isdigit() and \
       expected_norm.replace('-', '', 1).replace('.', '', 1).isdigit():
        try:
            parsed_num = float(parsed_norm)
            expected_num = float(expected_norm)
            # Allow small floating point differences
            if abs(parsed_num - expected_num) < 1e-6:
                return True, None
            else:
                return False, "numeric_mismatch"
        except ValueError:
            pass
    
    # String comparison
    if parsed_norm == expected_norm:
        return True, None
    
    # Partial match for entities (e.g., "paris" vs "Paris, France")
    if parsed_norm in expected_norm or expected_norm in parsed_norm:
        return True, None
    
    return False, "mismatch"


def create_eval_record(
    output: str,
    parse_type: str,
    expected_answer: str,
    task_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create structured evaluation record.
    
    Args:
        output: Model output
        parse_type: Type of answer to parse
        expected_answer: Ground truth answer
        task_id: Optional task identifier
        **kwargs: Additional metadata
    
    Returns:
        Dictionary with evaluation record
    """
    parse_result = parse_answer(output, parse_type)
    is_correct, error_type = evaluate_answer(
        parse_result.parsed_answer,
        expected_answer,
        parse_result.parse_valid
    )
    
    record = {
        "output": output,
        "parse_type": parse_type,
        "expected_answer": expected_answer,
        "parsed_answer": parse_result.parsed_answer,
        "parse_valid": parse_result.parse_valid,
        "parse_error_type": parse_result.parse_error_type,
        "parse_ambiguous": parse_result.parse_ambiguous,
        "parse_strategy": parse_result.parse_strategy,
        "candidate_answers": parse_result.candidate_answers,
        "answer_format_warning": parse_result.answer_format_warning,
        "correctness": is_correct,
        "error_type": error_type,
    }
    
    if task_id:
        record["task_id"] = task_id
    
    record.update(kwargs)
    
    return record
