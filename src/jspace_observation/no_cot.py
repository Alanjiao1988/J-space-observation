"""No-CoT prompt construction and validation utilities."""

import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class NoCoTValidationResult:
    """Result of no-CoT validation."""
    is_valid: bool
    reason_for_invalidity: Optional[str] = None
    violation_reasons: Optional[list[str]] = None
    has_think_tag: bool = False
    think_tag_content: Optional[str] = None
    has_visible_reasoning: bool = False
    has_visible_reasoning_marker: bool = False
    has_reasoning_heading: bool = False
    has_stepwise_marker: bool = False
    has_explanation_marker: bool = False
    has_multi_line_reasoning: bool = False
    has_excessive_length_for_answer_only: bool = False
    answer_only_format_valid: bool = True
    exceeded_token_budget: bool = False
    parse_failed: bool = False


@dataclass(frozen=True)
class ConditionGenerationConfig:
    """Generation settings tied to a prompt condition."""
    max_new_tokens: int
    temperature: float
    top_p: float
    do_sample: bool
    decoding_profile: str


def construct_empty_think_prefill_prompt(base_prompt: str) -> str:
    """
    Construct strict no-CoT prompt with empty-think prefill for R1-Distill.
    
    Format:
    {base_prompt}

    <think>
    </think>

    Answer:

    The question appears first. The already-closed empty think block then keeps
    R1-style models in-distribution while forcing zero visible thinking budget
    before final answer generation.
    
    Args:
        base_prompt: The actual question/prompt
    
    Returns:
        Full prompt with empty think prefill
    """
    instruction = (
        "You must output only the final answer. Do not explain. Do not show "
        "steps. Do not include reasoning. Do not include a step-by-step "
        "explanation."
    )
    return f"{base_prompt}\n\n{instruction}\n\n<think>\n</think>\n\nAnswer:"


def construct_prefill_answer_prompt(base_prompt: str) -> str:
    """Construct direct answer-prefill prompt without think tags."""
    instruction = (
        "You must output only the final answer. Do not explain. Do not show "
        "steps. Do not include reasoning. Do not include a step-by-step "
        "explanation. Do not include <think> tags."
    )
    return f"{base_prompt}\n\n{instruction}\n\nAnswer:"


def construct_answer_only_prompt(base_prompt: str) -> str:
    """
    Construct answer-only prompt for Qwen or other models.
    
    Args:
        base_prompt: The actual question/prompt
    
    Returns:
        Prompt instructing answer-only format
    """
    instruction = "Answer the question directly with only the final answer. Do not show any reasoning steps.\n\n"
    return instruction + base_prompt


def get_generation_config_for_condition(
    condition: str,
    default_max_new_tokens: int,
) -> ConditionGenerationConfig:
    """Return condition-specific decoding settings."""
    if condition == "strict_answer_only":
        return ConditionGenerationConfig(
            max_new_tokens=min(default_max_new_tokens, 12),
            temperature=0.0,
            top_p=1.0,
            do_sample=False,
            decoding_profile="strict_empty_think_answer_only_max12",
        )
    if condition == "strict_answer_only_prefill_answer":
        return ConditionGenerationConfig(
            max_new_tokens=min(default_max_new_tokens, 8),
            temperature=0.0,
            top_p=1.0,
            do_sample=False,
            decoding_profile="strict_prefill_answer_only_max8",
        )
    return ConditionGenerationConfig(
        max_new_tokens=default_max_new_tokens,
        temperature=1.0,
        top_p=1.0,
        do_sample=False,
        decoding_profile="default_greedy",
    )


def construct_visible_cot_prompt(base_prompt: str) -> str:
    """
    Construct prompt allowing visible chain-of-thought.
    
    Args:
        base_prompt: The actual question/prompt
    
    Returns:
        Prompt allowing CoT
    """
    instruction = "Think through this step by step and show your reasoning.\n\n"
    return instruction + base_prompt


def construct_r1_style_thinking_prompt(base_prompt: str) -> str:
    """
    Construct prompt for R1-style thinking (allow <think> tags).
    
    Args:
        base_prompt: The actual question/prompt
    
    Returns:
        Prompt allowing R1 style <think> tags
    """
    instruction = "You can use <think> tags to show your reasoning.\n\n"
    return instruction + base_prompt


def validate_no_cot_output(
    output: str,
    method: str = "empty_think_prefill",
    max_token_count: Optional[int] = None,
    allow_visible_reasoning: bool = False
) -> NoCoTValidationResult:
    """
    Validate if output respects no-CoT constraints.
    
    Args:
        output: Generated output text
        method: Method used (empty_think_prefill or answer_only_prompt)
        max_token_count: Optional token count for budget check
        allow_visible_reasoning: Whether visible reasoning is allowed
    
    Returns:
        NoCoTValidationResult with validity status and details
    """
    result = NoCoTValidationResult(is_valid=True, violation_reasons=[])
    
    # Check for think tags
    think_pattern = r'<think>(.*?)</think>'
    think_matches = re.findall(think_pattern, output, re.DOTALL)
    
    if think_matches:
        result.has_think_tag = True
        think_content = think_matches[0]
        result.think_tag_content = think_content
        
        # For empty-think prefill, any generated think tag content is invalid
        # because the prompt has already closed the empty <think></think> block.
        if method == "empty_think_prefill":
            # Allow only minimal think tags (whitespace only)
            if think_content.strip():
                result.violation_reasons.append("think_tag_generated")

    # Any generated think tag marker is a strict no-CoT violation. This catches
    # unmatched tags like a stray "</think>" as well as matched tags with empty
    # content.
    if method in {"empty_think_prefill", "answer_only_prompt", "answer_prefill"} and re.search(
        r"</?think>", output, flags=re.IGNORECASE
    ):
        result.has_think_tag = True
        if "think_tag_generated" not in result.violation_reasons:
            result.violation_reasons.append("think_tag_generated")
    
    # Check for visible reasoning patterns (if not allowed)
    if not allow_visible_reasoning:
        text_lower = output.lower()
        reasoning_heading_patterns = [
            r"step[-\s]*by[-\s]*step",
            r"\bexplanation\b",
            r"\breasoning\b",
            r"\bcalculation\b",
            r"\bshow your work\b",
        ]
        stepwise_patterns = [
            r"\bstep\s*\d+\b",
            r"(?m)^\s*\d+[\).]\s+",
            r"(?m)^\s*[-*]\s*(?:first|then|next|second|third)\b",
            r"\bfirst,\s+",
            r"\bsecond,\s+",
            r"\bthird,\s+",
            r"\bthen,\s+",
            r"\bnext,\s+",
            r"\btherefore\b",
            r"\bthus,\s+",
        ]
        explanation_patterns = [
            r"\blet['’]?s solve\b",
            r"\blet us solve\b",
            r"\bwe need to\b",
            r"\bwe can calculate\b",
            r"\bto solve\b",
            r"\bfollow these steps\b",
            r"\bbecause\b",
            r"\bso we\b",
            r"\balright\b",
            r"\bhmm\b",
            r"\bwait[,:\s]",
        ]

        if any(re.search(pattern, text_lower) for pattern in reasoning_heading_patterns):
            result.has_reasoning_heading = True
            result.violation_reasons.append("reasoning_heading_generated")

        if any(re.search(pattern, text_lower) for pattern in stepwise_patterns):
            result.has_stepwise_marker = True
            result.violation_reasons.append("intermediate_steps_generated")

        if any(re.search(pattern, text_lower) for pattern in explanation_patterns):
            result.has_explanation_marker = True
            result.violation_reasons.append("visible_reasoning_generated")

        nonempty_lines = [line.strip() for line in output.splitlines() if line.strip()]
        if len(nonempty_lines) >= 3 and (
            any(re.search(pattern, text_lower) for pattern in reasoning_heading_patterns + stepwise_patterns + explanation_patterns)
            or len(output.split()) > 25
        ):
            result.has_multi_line_reasoning = True
            result.violation_reasons.append("multi_line_reasoning_generated")

        if len(output) > 160 or len(output.split()) > 35:
            result.has_excessive_length_for_answer_only = True
            result.answer_only_format_valid = False
            result.violation_reasons.append("exceeded_answer_only_format_budget")

        if result.violation_reasons:
            result.has_visible_reasoning = any(
                reason != "think_tag_generated" for reason in result.violation_reasons
            )
            result.has_visible_reasoning_marker = result.has_visible_reasoning
    
    # Check token count if provided
    if max_token_count is not None:
        # Simple heuristic: ~4 chars per token
        estimated_tokens = len(output) // 4
        if estimated_tokens > max_token_count:
            result.exceeded_token_budget = True
            result.violation_reasons.append("exceeded_token_budget")

    # De-duplicate while preserving order.
    result.violation_reasons = list(dict.fromkeys(result.violation_reasons))
    result.is_valid = not result.violation_reasons
    result.reason_for_invalidity = (
        result.violation_reasons[0] if result.violation_reasons else None
    )
    
    return result


def extract_answer_from_output(output: str) -> str:
    """
    Extract the final answer from output, removing think tags and preamble.
    
    Args:
        output: Generated output
    
    Returns:
        Cleaned answer text
    """
    # Remove think tags and content
    text = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL)
    
    # Clean up whitespace
    text = text.strip()
    
    return text


def create_generation_record(
    prompt: str,
    output: str,
    no_cot_method: str,
    model_name: str,
    task_id: Optional[str] = None,
    ground_truth: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a structured generation record.
    
    Args:
        prompt: Input prompt
        output: Model output
        no_cot_method: Method used (e.g., empty_think_prefill)
        model_name: Model name
        task_id: Optional task identifier
        ground_truth: Optional ground truth answer
        **kwargs: Additional metadata
    
    Returns:
        Dictionary with generation record
    """
    validation = validate_no_cot_output(output, method=no_cot_method)
    answer = extract_answer_from_output(output)
    no_cot_applicable = no_cot_method in {"empty_think_prefill", "answer_only_prompt", "answer_prefill"}
    
    record = {
        "prompt": prompt,
        "output": output,
        "answer": answer,
        "model_name": model_name,
        "no_cot_method": no_cot_method,
        "no_cot_applicable": no_cot_applicable,
        "no_cot_validity": validation.is_valid if no_cot_applicable else None,
        "reason_for_invalidity": validation.reason_for_invalidity,
        "no_cot_violation_reasons": validation.violation_reasons,
        "has_think_tag": validation.has_think_tag,
        "has_visible_reasoning": validation.has_visible_reasoning,
        "has_visible_reasoning_marker": validation.has_visible_reasoning_marker,
        "has_reasoning_heading": validation.has_reasoning_heading,
        "has_stepwise_marker": validation.has_stepwise_marker,
        "has_explanation_marker": validation.has_explanation_marker,
        "has_multi_line_reasoning": validation.has_multi_line_reasoning,
        "has_excessive_length_for_answer_only": validation.has_excessive_length_for_answer_only,
        "answer_only_format_valid": validation.answer_only_format_valid,
        "exceeded_token_budget": validation.exceeded_token_budget,
    }
    
    if task_id:
        record["task_id"] = task_id
    if ground_truth:
        record["ground_truth"] = ground_truth
    
    # Add any additional metadata
    record.update(kwargs)
    
    return record
