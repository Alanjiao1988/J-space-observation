"""No-CoT prompt construction and validation utilities."""

import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class NoCoTValidationResult:
    """Result of no-CoT validation."""
    is_valid: bool
    reason_for_invalidity: Optional[str] = None
    has_think_tag: bool = False
    think_tag_content: Optional[str] = None
    has_visible_reasoning: bool = False
    exceeded_token_budget: bool = False
    parse_failed: bool = False


def construct_empty_think_prefill_prompt(base_prompt: str) -> str:
    """
    Construct prompt with empty think prefill for R1-Distill.
    
    Format:
    <think>
    </think>
    
    {base_prompt}
    
    Args:
        base_prompt: The actual question/prompt
    
    Returns:
        Full prompt with empty think prefill
    """
    return f"<think>\n</think>\n\n{base_prompt}"


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
    result = NoCoTValidationResult(is_valid=True)
    
    # Check for think tags
    think_pattern = r'<think>(.*?)</think>'
    think_matches = re.findall(think_pattern, output, re.DOTALL)
    
    if think_matches:
        result.has_think_tag = True
        think_content = think_matches[0]
        result.think_tag_content = think_content
        
        # For empty-think prefill, any think tag content is invalid
        # (since we start with empty <think></think>)
        if method == "empty_think_prefill":
            # Allow only minimal think tags (whitespace only)
            if think_content.strip():
                result.is_valid = False
                result.reason_for_invalidity = "think_tag_generated"
                return result
    
    # Check for visible reasoning patterns (if not allowed)
    if not allow_visible_reasoning:
        reasoning_patterns = [
            r'step\s+\d+',
            r'first[,]?\s+',
            r'then[,]?\s+',
            r'next[,]?\s+',
            r'therefore',
            r'thus[,]?\s+',
            r'let[\'s]?\s+',
            r'we\s+(?:have|need|can)',
            r'this\s+(?:means|implies)',
        ]
        
        text_lower = output.lower()
        for pattern in reasoning_patterns:
            if re.search(pattern, text_lower):
                result.has_visible_reasoning = True
                result.is_valid = False
                result.reason_for_invalidity = "visible_reasoning_generated"
                return result
    
    # Check token count if provided
    if max_token_count is not None:
        # Simple heuristic: ~4 chars per token
        estimated_tokens = len(output) // 4
        if estimated_tokens > max_token_count:
            result.exceeded_token_budget = True
            result.is_valid = False
            result.reason_for_invalidity = "exceeded_token_budget"
    
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
    
    record = {
        "prompt": prompt,
        "output": output,
        "answer": answer,
        "model_name": model_name,
        "no_cot_method": no_cot_method,
        "no_cot_validity": validation.is_valid,
        "reason_for_invalidity": validation.reason_for_invalidity,
        "has_think_tag": validation.has_think_tag,
        "has_visible_reasoning": validation.has_visible_reasoning,
        "exceeded_token_budget": validation.exceeded_token_budget,
    }
    
    if task_id:
        record["task_id"] = task_id
    if ground_truth:
        record["ground_truth"] = ground_truth
    
    # Add any additional metadata
    record.update(kwargs)
    
    return record
