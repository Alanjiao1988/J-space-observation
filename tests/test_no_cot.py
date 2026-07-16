"""Unit tests for no-CoT utilities."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation import (
    EMPTY_THINK_PREFILL,
    SUPPORTED_PHASE1_CONDITIONS,
    construct_empty_think_prefill_prompt,
    construct_answer_only_prompt,
    construct_prefill_answer_prompt,
    construct_visible_cot_prompt,
    construct_r1_style_thinking_prompt,
    render_empty_think_prefill_metadata,
    validate_phase1_conditions,
    get_generation_config_for_condition,
    STRICT_ANSWER_ONLY_STOP_STRINGS,
    apply_stop_control_cleanup,
    validate_no_cot_output,
    extract_answer_from_output,
    create_generation_record,
    NoCoTValidationResult,
)


def test_empty_think_prefill_prompt():
    """Test empty think prefill prompt construction."""
    base = "What is 2+2?"
    result = construct_empty_think_prefill_prompt(base)
    assert EMPTY_THINK_PREFILL in result
    assert result.count("<think>") == 1
    assert result.count("</think>") == 1
    assert base in result
    assert result.endswith(EMPTY_THINK_PREFILL)
    assert result.index(base) < result.index(EMPTY_THINK_PREFILL)


def test_answer_only_prompt():
    """Test answer-only prompt construction."""
    base = "What is 2+2?"
    result = construct_answer_only_prompt(base)
    assert base in result
    assert "Answer" in result or "answer" in result
    assert "<think>" not in result
    assert "</think>" not in result


def test_prefill_answer_prompt_is_strict_and_ends_with_answer():
    base = "What is 2+2?"
    result = construct_prefill_answer_prompt(base)
    assert result.startswith(base)
    assert "Do not explain" in result
    assert "Do not show steps" in result
    assert "<think>" not in result
    assert "</think>" not in result
    assert "show your reasoning" not in result.lower()
    assert result.endswith("Answer:")


class DeterministicFakeTokenizer:
    def __init__(self):
        self.calls = []

    def __call__(self, *_args, **_kwargs):
        raise AssertionError("rendering helper must not retokenize rendered strings")

    def apply_chat_template(
        self,
        messages,
        *,
        tokenize,
        add_generation_prompt=False,
        continue_final_message=False,
        chat_template=None,
    ):
        self.calls.append(
            {
                "tokenize": tokenize,
                "add_generation_prompt": add_generation_prompt,
                "continue_final_message": continue_final_message,
                "chat_template": chat_template,
            }
        )
        text = "<bos>"
        for message in messages:
            if message["role"] == "user":
                text += f"<user>{message['content']}</user>"
            else:
                text += f"<assistant>{message['content']}"
                if not continue_final_message:
                    text += "</assistant>"
        if add_generation_prompt:
            text += "<assistant>"
        return [ord(character) for character in text] if tokenize else text

    def decode(self, token_ids, **_kwargs):
        return "".join(chr(int(token_id)) for token_id in token_ids)


def test_empty_think_rendering_metadata_uses_chat_template_tokenization():
    tokenizer = DeterministicFakeTokenizer()

    metadata = render_empty_think_prefill_metadata(
        tokenizer,
        "Only answer.\n\nWhat is 2+2?",
        chat_template="deterministic-template",
    )

    assert metadata["raw_prefill"] == "<think>\n</think>"
    assert metadata["rendered_chat_text"].endswith(metadata["raw_prefill"])
    assert metadata["token_ids"] == [
        ord(character) for character in metadata["rendered_chat_text"]
    ]
    assert "".join(metadata["decoded_tokens"]) == metadata["rendered_chat_text"]
    boundary = metadata["assistant_prefix_boundary"]
    assert (
        metadata["rendered_chat_text"][boundary["character_index"]:]
        == metadata["raw_prefill"]
    )
    assert metadata["token_ids"][boundary["token_index"]:] == [
        ord(character) for character in metadata["raw_prefill"]
    ]
    assert all(
        call["chat_template"] == "deterministic-template"
        for call in tokenizer.calls
    )


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
    assert cfg.decoding_profile == "strict_prompt_only_answer_only_max12"


def test_prefill_generation_config_uses_tiny_budget():
    cfg = get_generation_config_for_condition("strict_answer_only_prefill_answer", 64)
    assert cfg.max_new_tokens == 8
    assert cfg.temperature == 0.0
    assert not cfg.do_sample
    assert "prefill" in cfg.decoding_profile


def test_empty_think_condition_is_explicit_and_uses_tiny_budget():
    assert "strict_answer_only_empty_think_prefill" in SUPPORTED_PHASE1_CONDITIONS
    cfg = get_generation_config_for_condition(
        "strict_answer_only_empty_think_prefill",
        64,
    )
    assert cfg.max_new_tokens == 8
    assert cfg.decoding_profile == "strict_empty_think_prefill_answer_only_max8"


def test_unknown_condition_fails_instead_of_using_thinking_defaults():
    with pytest.raises(ValueError, match="unknown Phase 1 condition"):
        validate_phase1_conditions(["strict_answer_only", "typo_condition"])
    with pytest.raises(ValueError, match="typo_condition"):
        get_generation_config_for_condition("typo_condition", 64)


def test_visible_generation_config_is_not_tightened():
    cfg = get_generation_config_for_condition("visible_cot", 64)
    assert cfg.max_new_tokens == 64
    assert cfg.temperature == 1.0
    assert not cfg.do_sample
    assert cfg.decoding_profile == "default_greedy"
    assert not cfg.stop_control_enabled


def test_r1_generation_config_is_not_tightened():
    cfg = get_generation_config_for_condition("r1_style_thinking", 64)
    assert cfg.max_new_tokens == 64
    assert cfg.decoding_profile == "default_greedy"
    assert not cfg.stop_control_enabled


def test_stopped_generation_config_enables_stop_controls():
    cfg = get_generation_config_for_condition("strict_answer_only_stopped", 64)
    assert cfg.max_new_tokens == 32
    assert cfg.temperature == 0.0
    assert not cfg.do_sample
    assert cfg.stop_control_enabled
    assert cfg.stop_mode == "truncate_at_stop_string"
    assert "stopped" in cfg.decoding_profile


def test_strict_stop_strings_cover_known_reasoning_markers():
    assert "Wait," in STRICT_ANSWER_ONLY_STOP_STRINGS
    assert "Step-by-step" in STRICT_ANSWER_ONLY_STOP_STRINGS
    assert "Explanation" in STRICT_ANSWER_ONLY_STOP_STRINGS
    assert "\n\n" in STRICT_ANSWER_ONLY_STOP_STRINGS


def test_stop_cleanup_preserves_raw_output_and_truncates_stopped_output():
    raw = "\\boxed{12}\n\nWait, I should check"
    result = apply_stop_control_cleanup(raw)
    assert result.raw_output_before_stop_cleanup == raw
    assert result.raw_output == raw
    assert result.stopped_output == "\\boxed{12}"
    assert result.stop_triggered
    assert result.stop_string == "\n\n"
    assert result.stop_reason == "stop_string_matched"


def test_stop_cleanup_no_trigger_keeps_stopped_output_equal_to_raw_strip():
    raw = "42"
    result = apply_stop_control_cleanup(raw)
    assert result.raw_output_before_stop_cleanup == raw
    assert result.raw_output == raw
    assert result.stopped_output == raw
    assert not result.stop_triggered


def test_raw_and_stopped_validity_are_separate():
    raw = "12\n\nWait, I should check"
    stopped = apply_stop_control_cleanup(raw).stopped_output
    raw_validation = validate_no_cot_output(raw, method="answer_prefill")
    stopped_validation = validate_no_cot_output(stopped, method="answer_prefill")
    assert not raw_validation.is_valid
    assert stopped_validation.is_valid


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
