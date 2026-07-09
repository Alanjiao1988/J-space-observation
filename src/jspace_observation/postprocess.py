"""Postprocess visible-reasoning-prone outputs into answer-like spans."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .no_cot import validate_no_cot_output


@dataclass
class PostprocessResult:
    """Result of deterministic answer-only postprocessing."""

    raw_output: str
    postprocessed_output: str
    postprocessing_applied: bool
    postprocessing_strategy: str
    postprocessing_reason: str | None
    postprocessing_warning: str | None
    raw_no_cot_valid: bool
    postprocessed_no_cot_valid: bool
    postprocessed_answer_like: bool


REASONING_START_PATTERNS = [
    r"\n\s*wait[,:\s]",
    r"\n\s*alright[,:\s]",
    r"\n\s*step[-\s]*by[-\s]*step",
    r"\n\s*explanation\b",
    r"\n\s*first[,:\s]",
    r"\n\s*then[,:\s]",
    r"\n\s*let['’]?s\b",
    r"\n\s*i\s+need\b",
    r"\n\s*we\s+need\b",
]


def _is_answer_like(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > 80 or len(stripped.split()) > 12:
        return False
    if re.search(r"step[-\s]*by[-\s]*step|explanation|follow these steps", stripped, re.I):
        return False
    return bool(re.search(r"[A-Za-z0-9\\{}]", stripped))


def _truncate_before_reasoning(raw_output: str) -> str | None:
    earliest = None
    for pattern in REASONING_START_PATTERNS:
        match = re.search(pattern, raw_output, flags=re.IGNORECASE)
        if match and (earliest is None or match.start() < earliest):
            earliest = match.start()
    if earliest is None:
        return None
    return raw_output[:earliest].strip()


def postprocess_answer_only(raw_output: str, task_type: str | None = None) -> PostprocessResult:
    """Extract an answer-like span while preserving raw-output validity."""
    raw_validation = validate_no_cot_output(raw_output, method="answer_prefill")
    warning = None
    strategy = "none"
    reason = None
    postprocessed = raw_output.strip()
    applied = False

    boxed_match = re.search(r"(\\?boxed\{[^{}]{1,80}\})", raw_output)
    incomplete_boxed = re.search(r"\\?boxed\s*\{?\s*$|\\?boxed\s*\{?\s*\n", raw_output)
    if boxed_match:
        postprocessed = boxed_match.group(1).strip()
        strategy = "boxed_answer"
        reason = "boxed_answer_extracted"
        applied = postprocessed != raw_output.strip()
    elif incomplete_boxed:
        postprocessed = ""
        strategy = "incomplete_boxed"
        reason = "incomplete_boxed_answer"
        warning = "incomplete_boxed_answer"
        applied = True
    else:
        explicit = re.search(
            r"(?:final\s+answer|answer|final|therefore,\s+the\s+answer\s+is|thus,\s+the\s+answer\s+is|答案)\s*[:：]?\s*(.+)",
            raw_output,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if explicit:
            candidate = explicit.group(1).strip()
            truncated = _truncate_before_reasoning(candidate)
            if truncated is not None:
                candidate = truncated
                reason = "truncated_before_reasoning_marker"
            else:
                candidate = candidate.splitlines()[0].strip()
                reason = "explicit_answer_extracted"
            postprocessed = candidate
            strategy = "explicit_answer"
            applied = postprocessed != raw_output.strip()
        else:
            truncated = _truncate_before_reasoning(raw_output)
            if truncated is not None:
                postprocessed = truncated
                strategy = "truncate_before_reasoning"
                reason = "truncated_before_reasoning_marker"
                applied = True
            else:
                first_line = raw_output.strip().splitlines()[0].strip() if raw_output.strip() else ""
                postprocessed = first_line
                strategy = "first_line"
                reason = "first_line_answer_like" if _is_answer_like(first_line) else "no_valid_answer"
                applied = postprocessed != raw_output.strip()

    answer_like = _is_answer_like(postprocessed)
    if not answer_like and warning is None:
        warning = "no_answer_like_span"

    postprocessed_validation = validate_no_cot_output(postprocessed, method="answer_prefill")
    return PostprocessResult(
        raw_output=raw_output,
        postprocessed_output=postprocessed,
        postprocessing_applied=applied,
        postprocessing_strategy=strategy,
        postprocessing_reason=reason,
        postprocessing_warning=warning,
        raw_no_cot_valid=raw_validation.is_valid,
        postprocessed_no_cot_valid=postprocessed_validation.is_valid,
        postprocessed_answer_like=answer_like,
    )

