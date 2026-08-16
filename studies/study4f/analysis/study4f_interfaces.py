"""Study 4F interfaces: one primary E0 route and one CoT headroom route.

Authority: ``studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md``

Section 6 registers exactly two routes:

``W1_RAW_DIRECT`` (primary, E0)
    The raw direct-answer wrapper. No chat template and no forced ``</think>``
    closure. Legal answers are exactly the frozen one-token surfaces A/B/C/D.
    A response is correct **only** if the generated continuation is exactly
    ``[one registered answer token, registered EOS]``. There is no prefix
    matching, no whitespace normalization, no textual reparsing and no post-hoc
    surface addition. A missing EOS, any extra non-EOS token and every
    unparseable output are incorrect.

``C1_LONG_GENERATED_COT_HEADROOM`` (headroom precondition only)
    The canonical generated-CoT wrapper. It never selects an interface. Its
    final non-empty generated line must match ``FINAL: A``/``B``/``C``/``D``
    exactly. Anything else is incorrect, and unparseable responses are counted,
    never dropped.

Both parsers are written as *exact* comparisons rather than regular
expressions, which makes the coordinated ``adv_cot_parser_regex_unanchored``
mutation structurally inapplicable rather than merely killed.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Sequence, Tuple

LABELS: Tuple[str, ...] = ("A", "B", "C", "D")

# ---------------------------------------------------------------------------
# W1_RAW_DIRECT
# ---------------------------------------------------------------------------

#: Separator between the item body and the answer cue.
RAW_ENVELOPE_SEPARATOR = "\n\n"

#: The answer cue. It ends in a newline so the first generated token starts a
#: line and no wrapper ever ends in a bare space.
ANSWER_CUE = "Answer:\n"

#: Provenance of the copied raw-direct wrapper. The source surface was
#: independently reproduced by the Study 3R focused review; Study 4F copies the
#: bytes into its own registry and binds the source hash. It never resolves a
#: Study 3R pointer at runtime.
W1_PROVENANCE: Dict[str, object] = {
    "source_path": "studies/study3r/protocol/study3r_rendering_registry_v1.json",
    "source_arm_id": "W1_RAW_DIRECT",
    "source_rendered_utf8_sha256":
        "9dab5a865967308bc43b219f5b44476cc610fb0b310dd6f528dd3fd0934a4c95",
    "source_rendered_utf8_bytes": 157,
    "source_rendered_token_count": 57,
    "independently_reproduced_by_the_study3r_focused_review": True,
    "uses_a_chat_template": False,
    "forced_reasoning_closure": None,
    "forced_reasoning_closure_is_explicitly_absent": True,
}

#: The deterministic placeholder fixture whose rendered bytes freeze the W1
#: surface. It is a surface fixture, never a scientific item.
W1_SURFACE_FIXTURE_BODY = (
    "You are answering a multiple-choice item.\n"
    "Reply with exactly one option label and nothing else.\n"
    "\n"
    "Item: Compute (8 + 3) * 4.\n"
    "A) 44\n"
    "B) 33\n"
    "C) 51\n"
    "D) 38"
)


def render_w1_raw_direct(item_body: str) -> str:
    """Render the ``W1_RAW_DIRECT`` prompt around an item body.

    The prompt is a pure function of ``item_body``. No answer field and no
    answer-derived field is an argument, so none can leak into the prompt.
    """
    return item_body + RAW_ENVELOPE_SEPARATOR + ANSWER_CUE


def w1_surface_sha256() -> str:
    """SHA-256 of the frozen W1 surface, for binding against the source hash."""
    rendered = render_w1_raw_direct(W1_SURFACE_FIXTURE_BODY)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# E0 generation contract
# ---------------------------------------------------------------------------

#: Every E0 decoding field, frozen. No field is inherited or left unspecified.
E0_GENERATION_CONTRACT: Dict[str, object] = {
    "do_sample": False,
    "temperature": 1.0,
    "temperature_is_the_explicitly_frozen_neutral_value": True,
    "top_p": 1.0,
    "top_k": 0,
    "num_beams": 1,
    "num_return_sequences": 1,
    "repetition_penalty": 1.0,
    "length_penalty": 1.0,
    "early_stopping": False,
    "use_cache": True,
    "batch_size": 1,
    "padding": "none",
    "max_new_tokens": 2,
    "max_new_tokens_rationale": "one answer token plus one EOS opportunity",
}

E0_VERDICTS = (
    "CORRECT",
    "INCORRECT_WRONG_LABEL",
    "INCORRECT_MISSING_EOS",
    "INCORRECT_EXTRA_TOKEN",
    "UNPARSEABLE",
)


class Study4FParserError(ValueError):
    """Raised when a parser is called outside its registered contract."""


def parse_e0(generated_token_ids: Sequence[int],
             answer_token_ids: Dict[str, int],
             eos_token_id: int) -> Tuple[Optional[str], str]:
    """Parse an E0 continuation into ``(label, verdict)``.

    The continuation is correct **only** when it is exactly
    ``[registered answer token, registered EOS]``. Every other shape is a
    non-correct verdict; none of them is silently dropped.
    """
    if eos_token_id in answer_token_ids.values():
        raise Study4FParserError("EOS collides with a registered answer token")
    if sorted(answer_token_ids) != sorted(LABELS):
        raise Study4FParserError("answer token map is not exactly A/B/C/D")
    if len(set(answer_token_ids.values())) != len(LABELS):
        raise Study4FParserError("answer token ids are not distinct")

    tokens = list(generated_token_ids)
    inverse = {value: label for label, value in answer_token_ids.items()}

    if len(tokens) == 0:
        return None, "UNPARSEABLE"
    if tokens[0] not in inverse:
        return None, "UNPARSEABLE"
    label = inverse[tokens[0]]
    if len(tokens) == 1:
        return label, "INCORRECT_MISSING_EOS"
    if len(tokens) > 2:
        return label, "INCORRECT_EXTRA_TOKEN"
    if tokens[1] != eos_token_id:
        return label, "INCORRECT_EXTRA_TOKEN"
    return label, "CORRECT"


def score_e0(generated_token_ids: Sequence[int], expected_label: str,
             answer_token_ids: Dict[str, int], eos_token_id: int) -> bool:
    """True only for an exactly shaped continuation carrying the right label."""
    label, verdict = parse_e0(generated_token_ids, answer_token_ids,
                              eos_token_id)
    if verdict != "CORRECT":
        return False
    return label == expected_label


# ---------------------------------------------------------------------------
# C1_LONG_GENERATED_COT_HEADROOM
# ---------------------------------------------------------------------------

#: Provenance of the canonical generated-CoT envelope. The chat template is
#: bound by the digest the Study 3R focused review reproduced for every
#: checkpoint. Study 4F re-verifies the digest before execution and never
#: resolves a Study 3R pointer at runtime.
C1_PROVENANCE: Dict[str, object] = {
    "source_path": "studies/study3r/protocol/study3r_rendering_registry_v1.json",
    "source_arm_id": "W2_ROLE_CANONICAL",
    "source_chat_template_sha256":
        "56a1447ad31926fdc21fb07e56e5642bd9c850c4f52d8c8af7bbe5f079a84f5f",
    "chat_template_digest_agrees_for_every_checkpoint": True,
    "reasoning_span_opened_by_template": True,
    # F-06 of the Study 3R review recorded that the source arm injected a forced
    # reasoning closure absent from its authoritative Markdown. The generated-CoT
    # route must *not* close the span, and Study 4F names that absence explicitly
    # instead of leaving it implied.
    "forced_reasoning_closure": None,
    "forced_reasoning_closure_is_explicitly_absent": True,
    "closure_absence_is_decision_bearing": True,
}

#: The frozen instruction appended to the item body on the CoT route. It names
#: the required final line exactly and adds no answer-derived field.
C1_INSTRUCTION = (
    "Reason step by step. End your response with a final line of exactly "
    "\"FINAL: X\", where X is one of A, B, C or D."
)

#: The four and only legal final lines.
C1_LEGAL_FINAL_LINES: Tuple[str, ...] = tuple("FINAL: %s" % label
                                              for label in LABELS)

#: Every C1 runtime field, frozen.
C1_GENERATION_CONTRACT: Dict[str, object] = {
    "do_sample": True,
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 0,
    "num_beams": 1,
    "num_return_sequences": 1,
    "k": 1,
    "aggregation": "per-item exact correctness",
    "repetition_penalty": 1.0,
    "length_penalty": 1.0,
    "early_stopping": False,
    "use_cache": True,
    "max_new_tokens": 4096,
    "batch_size": 1,
    "padding": "none",
}

C1_VERDICTS = ("CORRECT", "INCORRECT_WRONG_LABEL", "UNPARSEABLE")


def render_c1_body(item_body: str) -> str:
    """The user content placed inside the canonical envelope on the CoT route."""
    return item_body + "\n\n" + C1_INSTRUCTION


def cot_seed(study_identity: str, checkpoint_role: str, depth: str,
             item_id: str) -> int:
    """Derive one per-item sampling seed.

    The seed is a pure function of the sealed study identity, the checkpoint
    role, the depth and the item ID, so every seed can be recorded before
    generation and reproduced afterwards.
    """
    material = "|".join([study_identity, checkpoint_role, depth, item_id])
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def parse_cot(generated_text: str) -> Tuple[Optional[str], str]:
    """Parse a generated CoT response into ``(label, verdict)``.

    The final non-empty line must be *exactly* one of the four legal final
    lines. A line counts as non-empty when it contains a non-whitespace
    character; the comparison itself performs no stripping, no normalization
    and no substring search, so a trailing space or an embedded ``FINAL: A``
    earlier in the response cannot be accepted.
    """
    lines = generated_text.split("\n")
    final_line = None
    for line in reversed(lines):
        if line.strip():
            final_line = line
            break
    if final_line is None:
        return None, "UNPARSEABLE"
    for label, legal in zip(LABELS, C1_LEGAL_FINAL_LINES):
        if final_line == legal:
            return label, "CORRECT"
    return None, "UNPARSEABLE"


def score_cot(generated_text: str, expected_label: str) -> bool:
    """True only when the exact legal final line carries the expected label."""
    label, verdict = parse_cot(generated_text)
    if verdict != "CORRECT":
        return False
    return label == expected_label


def cot_outcome(generated_text: str, expected_label: str) -> str:
    """Registered per-item outcome; unparseable responses are never dropped."""
    label, verdict = parse_cot(generated_text)
    if verdict == "UNPARSEABLE":
        return "UNPARSEABLE"
    return "CORRECT" if label == expected_label else "INCORRECT_WRONG_LABEL"


def e0_outcome(generated_token_ids: Sequence[int], expected_label: str,
               answer_token_ids: Dict[str, int], eos_token_id: int) -> str:
    """Registered per-item E0 outcome; nothing is dropped."""
    label, verdict = parse_e0(generated_token_ids, answer_token_ids,
                              eos_token_id)
    if verdict == "CORRECT":
        return "CORRECT" if label == expected_label else "INCORRECT_WRONG_LABEL"
    return verdict


def registered_routes() -> List[str]:
    return ["W1_RAW_DIRECT", "C1_LONG_GENERATED_COT_HEADROOM"]
