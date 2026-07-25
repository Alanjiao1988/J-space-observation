"""Build the public parser-v3 adversarial development fixture set.

The fixtures are authored declaratively in :data:`FIXTURE_SPECS` from the
frozen parser protocol (``docs/phase1_parser_v2_protocol.md``) and the frozen
stratum taxonomy (``docs/phase1_evaluator_validation_set.md``).  Nothing in
this builder reads parser output, so the expectations are independent of any
parser implementation; the resulting file is an oracle, not a transcript.

Provenance rules for this set:

* The set is PUBLIC development material.  It is authored for parser-v3
  failure-directed development and must never be used as a locked holdout.
* No case text is copied from the retired parser-v2 holdout.  Every string is
  written here in the open.
* ``case_id`` values are derived with :func:`derive_case_id` under the PUBLIC
  salt :data:`PUBLIC_CASE_ID_SALT`.  The salt is deliberately published: these
  fixtures carry no confidentiality function, and a published salt makes the
  identifiers reproducible by any reviewer.
* Quota diagnostic tags are derived from content with the frozen
  ``_surface_features`` helper, exactly as the frozen curator path does; the
  remaining ``secondary_tags`` are declared by the author.

Usage::

    python scripts/build_parser_v3_adversarial_cases.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from jspace_observation.evaluator_validation import (  # noqa: E402
    DEVELOPMENT_SCHEMA_VERSION,
    QUOTA_DIAGNOSTIC_TAGS,
    SECONDARY_TAGS,
    SOURCE_KIND,
    CRITICAL_STRATA,
    ValidationSetError,
    _surface_features,
    derive_case_id,
    validate_development_record,
)

OUTPUT_PATH = (
    REPO_ROOT
    / "evaluator_sets"
    / "parser_v3_v1"
    / "adversarial_development_cases.jsonl"
)

PUBLIC_CASE_ID_SALT = "jspace-parser-v3-public-adversarial-development-salt/v1"

PRESENCE_PRESENT = "present"
PRESENCE_AMBIGUOUS = "ambiguous"
PRESENCE_NO_ANSWER = "no_answer"


def present(
    *,
    parsed: str,
    spans: list[tuple[str, int, str, str, str]],
    strategy: str,
    quality: str = "complete",
    warnings: tuple[str, ...] = (),
    candidates: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Declare a present typed decision."""
    return {
        "presence": PRESENCE_PRESENT,
        "parse_valid": True,
        "parse_ambiguous": False,
        "parsed": parsed,
        "candidates": list(candidates if candidates is not None else (parsed,)),
        "spans": spans,
        "strategy": strategy,
        "quality": quality,
        "failures": [],
        "warnings": list(warnings),
    }


def ambiguous(
    *,
    candidates: tuple[str, ...],
    spans: list[tuple[str, int, str, str, str]],
    quality: str = "complete",
    warnings: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Declare an ambiguous typed decision."""
    return {
        "presence": PRESENCE_AMBIGUOUS,
        "parse_valid": True,
        "parse_ambiguous": True,
        "parsed": None,
        "candidates": list(candidates),
        "spans": spans,
        "strategy": "ambiguous_candidates",
        "quality": quality,
        "failures": [],
        "warnings": list(warnings),
    }


def no_answer(
    *,
    quality: str,
    failure: str,
    warnings: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Declare a no-answer typed decision."""
    return {
        "presence": PRESENCE_NO_ANSWER,
        "parse_valid": False,
        "parse_ambiguous": False,
        "parsed": None,
        "candidates": [],
        "spans": [],
        "strategy": "none",
        "quality": quality,
        "failures": [failure],
        "warnings": list(warnings),
    }


BOX = "boxed"
FIN = "explicit_final_marker"
ANS = "explicit_answer_marker"
EQU = "terminal_equation"
SEL = "selected"
EQV = "equivalent"
AMB = "ambiguous_candidate"


FIXTURE_SPECS: tuple[dict[str, Any], ...] = (
    # ---------------------------------------------------------------- family
    # F1 nested boxed answer (exercises v3 change C1)
    {
        "slot": "nested_box_plain",
        "family": "nested_boxed_answer",
        "rule": "C1",
        "stratum": "S01",
        "text": "The result is \\boxed{\\boxed{17}}",
        "reference": "17",
        "material": True,
        "tags": (),
        "notes": (
            "Nested box wrapper. Protocol evidence priority puts the boxed tier "
            "first; the payload carries exactly one registered numeric literal, "
            "so the inner literal is the selected span."
        ),
        "expected": present(
            parsed="17",
            spans=[("17", 0, BOX, SEL, "17")],
            strategy="boxed_answer",
        ),
    },
    {
        "slot": "nested_box_text_macro_negative",
        "family": "nested_boxed_answer",
        "rule": "C1",
        "stratum": "S01",
        "text": "Working done.\n\\boxed{\\text{-6}}",
        "reference": "-6",
        "material": True,
        "tags": (),
        "notes": (
            "Box payload nested inside a typesetting macro. The macro carries no "
            "arithmetic meaning, so it must not change the claim."
        ),
        "expected": present(
            parsed="-6",
            spans=[("-6", 0, BOX, SEL, "-6")],
            strategy="boxed_answer",
        ),
    },
    {
        "slot": "nested_box_left_right_delimiters",
        "family": "nested_boxed_answer",
        "rule": "C1",
        "stratum": "S01",
        "text": "\\boxed{\\left(19\\right)}",
        "reference": "19",
        "material": True,
        "tags": (),
        "notes": (
            "Sized LaTeX delimiters inside the box. Balanced delimiters around a "
            "single literal are decoration, not an expression."
        ),
        "expected": present(
            parsed="19",
            spans=[("19", 0, BOX, SEL, "19")],
            strategy="boxed_answer",
        ),
    },
    {
        "slot": "nested_box_thin_space_macros",
        "family": "nested_boxed_answer",
        "rule": "C1",
        "stratum": "S01",
        "text": "Hence \\boxed{\\,-11\\,} follows.",
        "reference": "-11",
        "material": True,
        "tags": (),
        "notes": (
            "Spacing macros inside the box. Spacing is decoration and must be "
            "transparent to the numeric claim."
        ),
        "expected": present(
            parsed="-11",
            spans=[("-11", 0, BOX, SEL, "-11")],
            strategy="boxed_answer",
        ),
    },
    # F2 box with surrounding punctuation
    {
        "slot": "box_trailing_period",
        "family": "box_with_surrounding_punctuation",
        "rule": "baseline",
        "stratum": "S01",
        "text": "Therefore the total is \\boxed{24}.",
        "reference": "24",
        "material": True,
        "tags": (),
        "notes": (
            "Sentence punctuation after the closing brace is prose, not part of "
            "the claim; the span must stop at the literal."
        ),
        "expected": present(
            parsed="24",
            spans=[("24", 0, BOX, SEL, "24")],
            strategy="boxed_answer",
        ),
    },
    {
        "slot": "box_parenthetical_lead_and_bang",
        "family": "box_with_surrounding_punctuation",
        "rule": "baseline",
        "stratum": "S01",
        "text": "(See the box.) \\boxed{9}!",
        "reference": "9",
        "material": True,
        "tags": (),
        "notes": (
            "Parenthetical lead-in and trailing exclamation mark. Neither is "
            "numeric material and neither may move the span."
        ),
        "expected": present(
            parsed="9",
            spans=[("9", 0, BOX, SEL, "9")],
            strategy="boxed_answer",
        ),
    },
    {
        "slot": "box_fraction_trailing_period",
        "family": "box_with_surrounding_punctuation",
        "rule": "baseline",
        "stratum": "S01",
        "text": "Total in the box: \\boxed{3/4}.",
        "reference": "3/4",
        "material": True,
        "tags": (),
        "notes": (
            "Fractional boxed payload with trailing punctuation. The registered "
            "fraction literal is already canonical."
        ),
        "expected": present(
            parsed="3/4",
            spans=[("3/4", 0, BOX, SEL, "3/4")],
            strategy="boxed_answer",
        ),
    },
    {
        "slot": "box_quoted_then_semicolon",
        "family": "box_with_surrounding_punctuation",
        "rule": "baseline",
        "stratum": "S01",
        "text": "Reported value: \\boxed{58}; archived.",
        "reference": "58",
        "material": True,
        "tags": (),
        "notes": (
            "Semicolon-joined clause after the box. Trailing prose must not "
            "downgrade a complete boxed claim."
        ),
        "expected": present(
            parsed="58",
            spans=[("58", 0, BOX, SEL, "58")],
            strategy="boxed_answer",
        ),
    },
    # F3 multiple boxes
    {
        "slot": "two_boxes_distinct",
        "family": "multiple_boxes",
        "rule": "baseline",
        "stratum": "S11",
        "text": "\\boxed{5} and later \\boxed{8}",
        "reference": "5",
        "material": True,
        "tags": ("multiple_numeric_mentions", "multiple_distinct_candidates"),
        "notes": (
            "Two unranked boxed claims with different values. The protocol "
            "forbids guessing between equal-priority claims."
        ),
        "expected": ambiguous(
            candidates=("5", "8"),
            spans=[("5", 0, BOX, AMB, "5"), ("8", 0, BOX, AMB, "8")],
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "two_boxes_reflection_conflict",
        "family": "multiple_boxes",
        "rule": "baseline",
        "stratum": "S11",
        "text": "\\boxed{2}\nBut on reflection \\boxed{3} is better.",
        "reference": "3",
        "material": True,
        "tags": ("multiple_numeric_mentions", "multiple_distinct_candidates"),
        "notes": (
            "Soft preference prose is not a registered revision marker, so the "
            "two boxed claims stay unranked and the case is ambiguous."
        ),
        "expected": ambiguous(
            candidates=("2", "3"),
            spans=[("2", 0, BOX, AMB, "2"), ("3", 0, BOX, AMB, "3")],
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "two_boxes_identical_value",
        "family": "multiple_boxes",
        "rule": "baseline",
        "stratum": "S01",
        "text": "\\boxed{6}\n\nOn reflection, \\boxed{6} again.",
        "reference": "6",
        "material": True,
        "tags": ("multiple_numeric_mentions",),
        "notes": (
            "Repeated boxed claim with one canonical value. Repetition of the "
            "same value is not ambiguity."
        ),
        "expected": present(
            parsed="6",
            spans=[("6", 0, BOX, SEL, "6"), ("6", 1, BOX, EQV, "6")],
            strategy="boxed_answer",
            warnings=("multiple_numeric_mentions", "equivalent_repeated_claim"),
        ),
    },
    {
        "slot": "two_boxes_equivalent_surfaces",
        "family": "multiple_boxes",
        "rule": "baseline",
        "stratum": "S12",
        "text": "First \\boxed{2.5}, then \\boxed{5/2}",
        "reference": "5/2",
        "material": True,
        "tags": ("multiple_numeric_mentions", "noncanonical_numeric_surface"),
        "notes": (
            "Two boxed claims whose canonical values agree. Canonical rational "
            "equality resolves the pair to one claim; the leftmost surface is "
            "the selected span."
        ),
        "expected": present(
            parsed="5/2",
            spans=[("2.5", 0, BOX, SEL, "5/2"), ("5/2", 0, BOX, EQV, "5/2")],
            strategy="boxed_answer",
            warnings=(
                "multiple_numeric_mentions",
                "equivalent_repeated_claim",
                "noncanonical_numeric_surface",
            ),
        ),
    },
    # F4 box followed by explanation
    {
        "slot": "box_then_justification",
        "family": "box_followed_by_explanation",
        "rule": "baseline",
        "stratum": "S05",
        "text": "\\boxed{12}\nThis is because 3 * 4 = 12.",
        "reference": "12",
        "material": True,
        "tags": ("multiple_numeric_mentions", "continued_reasoning"),
        "notes": (
            "Explanation after the box restates the same value. Continued "
            "reasoning is reported as a warning, never as ambiguity."
        ),
        "expected": present(
            parsed="12",
            spans=[("12", 0, BOX, SEL, "12")],
            strategy="boxed_answer",
            warnings=(
                "multiple_numeric_mentions",
                "reasoning_continues_after_answer",
            ),
        ),
    },
    {
        "slot": "box_then_verification",
        "family": "box_followed_by_explanation",
        "rule": "baseline",
        "stratum": "S05",
        "text": "\\boxed{-7}\nLet me verify: -7 + 7 = 0. Correct.",
        "reference": "-7",
        "material": True,
        "tags": ("multiple_numeric_mentions", "continued_reasoning"),
        "notes": (
            "Post-hoc verification arithmetic after a negative boxed claim. The "
            "check numbers are not competing claims."
        ),
        "expected": present(
            parsed="-7",
            spans=[("-7", 0, BOX, SEL, "-7")],
            strategy="boxed_answer",
            warnings=(
                "multiple_numeric_mentions",
                "reasoning_continues_after_answer",
            ),
        ),
    },
    {
        "slot": "box_then_units_sentence",
        "family": "box_followed_by_explanation",
        "rule": "baseline",
        "stratum": "S05",
        "text": "\\boxed{15}\nThis follows because 15 minutes is the runtime.",
        "reference": "15",
        "material": True,
        "tags": ("multiple_numeric_mentions", "continued_reasoning"),
        "notes": (
            "Explanatory unit sentence after the box repeats the same value; the "
            "boxed span stays selected."
        ),
        "expected": present(
            parsed="15",
            spans=[("15", 0, BOX, SEL, "15")],
            strategy="boxed_answer",
            warnings=(
                "multiple_numeric_mentions",
                "reasoning_continues_after_answer",
            ),
        ),
    },
    # F5 explicit final marker plus trailing metadata
    {
        "slot": "marker_then_confidence_metadata",
        "family": "final_marker_plus_trailing_metadata",
        "rule": "baseline",
        "stratum": "S06",
        "text": "Final answer: 42\nConfidence: 0.93",
        "reference": "42",
        "material": True,
        "tags": (
            "multiple_numeric_mentions",
            "last_number_distractor",
        ),
        "notes": (
            "Confidence metadata after the marker is the rightmost number. A "
            "last-number heuristic would select it; the marker tier must win."
        ),
        "expected": present(
            parsed="42",
            spans=[("42", 0, FIN, SEL, "42")],
            strategy="explicit_final_marker",
            warnings=(
                "multiple_numeric_mentions",
                "incidental_numeric_material",
            ),
        ),
    },
    {
        "slot": "marker_then_trace_id_metadata",
        "family": "final_marker_plus_trailing_metadata",
        "rule": "baseline",
        "stratum": "S06",
        "text": "Final answer: 108\nInternal trace id 77.",
        "reference": "108",
        "material": True,
        "tags": (
            "multiple_numeric_mentions",
            "last_number_distractor",
        ),
        "notes": (
            "Trailing identifier metadata. Identifiers are incidental numeric "
            "material and must not become the claim."
        ),
        "expected": present(
            parsed="108",
            spans=[("108", 0, FIN, SEL, "108")],
            strategy="explicit_final_marker",
            warnings=(
                "multiple_numeric_mentions",
                "incidental_numeric_material",
            ),
        ),
    },
    {
        "slot": "marker_then_step_count_metadata",
        "family": "final_marker_plus_trailing_metadata",
        "rule": "baseline",
        "stratum": "S06",
        "text": "Answer: -21\nSolved in 4 steps.",
        "reference": "-21",
        "material": True,
        "tags": (
            "multiple_numeric_mentions",
            "last_number_distractor",
        ),
        "notes": (
            "Step-count metadata after a negative marker claim. The trailing "
            "count is a distractor, not a revision."
        ),
        "expected": present(
            parsed="-21",
            spans=[("-21", 0, ANS, SEL, "-21")],
            strategy="explicit_answer_marker",
            warnings=(
                "multiple_numeric_mentions",
                "incidental_numeric_material",
            ),
        ),
    },
    {
        "slot": "marker_then_rating_metadata",
        "family": "final_marker_plus_trailing_metadata",
        "rule": "baseline",
        "stratum": "S06",
        "text": "Final answer: 7\nSelf-rating 9 out of 10.",
        "reference": "7",
        "material": True,
        "tags": (
            "multiple_numeric_mentions",
            "last_number_distractor",
        ),
        "notes": (
            "Self-rating metadata contains two later numbers; neither competes "
            "with the marker claim."
        ),
        "expected": present(
            parsed="7",
            spans=[("7", 0, FIN, SEL, "7")],
            strategy="explicit_final_marker",
            warnings=(
                "multiple_numeric_mentions",
                "incidental_numeric_material",
            ),
        ),
    },
    # F6 correct numeric span embedded in unit text (exercises v3 change C4)
    {
        "slot": "marker_value_with_unit_kg",
        "family": "numeric_span_embedded_in_unit_text",
        "rule": "C4",
        "stratum": "S02",
        "text": "Final answer: 42 kg",
        "reference": "42",
        "material": True,
        "tags": (),
        "notes": (
            "A unit word after the literal is prose. Units carry no arithmetic "
            "operator, so the claim stays complete and the span is the literal."
        ),
        "expected": present(
            parsed="42",
            spans=[("42", 0, FIN, SEL, "42")],
            strategy="explicit_final_marker",
        ),
    },
    {
        "slot": "marker_value_with_unit_phrase",
        "family": "numeric_span_embedded_in_unit_text",
        "rule": "C4",
        "stratum": "S02",
        "text": "The answer is 3.5 liters of solvent.",
        "reference": "7/2",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "Multi-word unit phrase after a decimal literal. Unit prose must not "
            "invalidate the claim, and the decimal normalizes to a rational."
        ),
        "expected": present(
            parsed="7/2",
            spans=[("3.5", 0, ANS, SEL, "7/2")],
            strategy="explicit_answer_marker",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    {
        "slot": "boxed_value_with_unit_macro",
        "family": "numeric_span_embedded_in_unit_text",
        "rule": "C1",
        "stratum": "S01",
        "text": "\\boxed{42\\text{ kg}}",
        "reference": "42",
        "material": True,
        "tags": (),
        "notes": (
            "Unit typeset inside the box via a text macro. The macro payload is "
            "decoration; the numeric literal is the claim."
        ),
        "expected": present(
            parsed="42",
            spans=[("42", 0, BOX, SEL, "42")],
            strategy="boxed_answer",
        ),
    },
    {
        "slot": "marker_negative_value_with_unit",
        "family": "numeric_span_embedded_in_unit_text",
        "rule": "C4",
        "stratum": "S12",
        "text": "Final answer: -40 degrees",
        "reference": "-40",
        "material": True,
        "tags": (),
        "notes": (
            "Negative literal followed by a unit word. The unit must not be read "
            "as continued arithmetic."
        ),
        "expected": present(
            parsed="-40",
            spans=[("-40", 0, FIN, SEL, "-40")],
            strategy="explicit_final_marker",
        ),
    },
    # F7 equivalent fractions and decimals
    {
        "slot": "equivalent_decimal_to_fraction_chain",
        "family": "equivalent_fractions_decimals",
        "rule": "baseline",
        "stratum": "S12",
        "text": "We simplify: -1.5 = -3/2\nFinal answer: -3/2",
        "reference": "-3/2",
        "material": True,
        "tags": ("multiple_numeric_mentions",),
        "notes": (
            "Equivalence chain in the working, then an explicit marker. The "
            "marker tier outranks the earlier equation."
        ),
        "expected": present(
            parsed="-3/2",
            spans=[("-3/2", 1, FIN, SEL, "-3/2")],
            strategy="explicit_final_marker",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "decimal_quarter_normalizes",
        "family": "equivalent_fractions_decimals",
        "rule": "baseline",
        "stratum": "S12",
        "text": "Final answer: 0.25",
        "reference": "1/4",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "Decimal surface with a rational canonical form. The reported value "
            "is canonical while the span keeps the observed surface."
        ),
        "expected": present(
            parsed="1/4",
            spans=[("0.25", 0, FIN, SEL, "1/4")],
            strategy="explicit_final_marker",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    {
        "slot": "unreduced_fraction_normalizes",
        "family": "equivalent_fractions_decimals",
        "rule": "C3",
        "stratum": "S12",
        "text": "The final answer is 4/6",
        "reference": "2/3",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "Unreduced fraction after an `is` separator. Canonicalization must "
            "reduce the value without moving the span."
        ),
        "expected": present(
            parsed="2/3",
            spans=[("4/6", 0, FIN, SEL, "2/3")],
            strategy="explicit_final_marker",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    {
        "slot": "equivalent_marker_and_equation",
        "family": "equivalent_fractions_decimals",
        "rule": "baseline",
        "stratum": "S12",
        "text": "0.75 = 3/4\nAnswer: 0.75",
        "reference": "3/4",
        "material": True,
        "tags": ("multiple_numeric_mentions", "noncanonical_numeric_surface"),
        "notes": (
            "Equation and marker agree canonically across different surfaces; "
            "the higher-priority marker tier supplies the selected span."
        ),
        "expected": present(
            parsed="3/4",
            spans=[("0.75", 1, ANS, SEL, "3/4")],
            strategy="explicit_answer_marker",
            warnings=(
                "multiple_numeric_mentions",
                "noncanonical_numeric_surface",
            ),
        ),
    },
    # F8 negative-sign span
    {
        "slot": "negative_marker_integer",
        "family": "negative_sign_span",
        "rule": "baseline",
        "stratum": "S12",
        "text": "Final answer: -18",
        "reference": "-18",
        "material": True,
        "tags": (),
        "notes": (
            "The sign belongs to the literal. A span that omits the leading "
            "minus reports the wrong value."
        ),
        "expected": present(
            parsed="-18",
            spans=[("-18", 0, FIN, SEL, "-18")],
            strategy="explicit_final_marker",
        ),
    },
    {
        "slot": "negative_boxed_decimal",
        "family": "negative_sign_span",
        "rule": "baseline",
        "stratum": "S12",
        "text": "\\boxed{-0.75}",
        "reference": "-3/4",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "Negative decimal inside a box; the sign must be inside the span and "
            "preserved through canonicalization."
        ),
        "expected": present(
            parsed="-3/4",
            spans=[("-0.75", 0, BOX, SEL, "-3/4")],
            strategy="boxed_answer",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    {
        "slot": "negative_after_positive_working",
        "family": "negative_sign_span",
        "rule": "baseline",
        "stratum": "S04",
        "text": "Step 1: 9 - 30 gives a deficit.\nFinal answer: -21",
        "reference": "-21",
        "material": True,
        "tags": ("multiple_numeric_mentions",),
        "notes": (
            "Intermediate positive numbers precede a negative marker claim. Sign "
            "loss here would silently flip the reported value."
        ),
        "expected": present(
            parsed="-21",
            spans=[("-21", 0, FIN, SEL, "-21")],
            strategy="explicit_final_marker",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "negative_decorated_marker",
        "family": "negative_sign_span",
        "rule": "C2",
        "stratum": "S12",
        "text": "Final answer: **-4**",
        "reference": "-4",
        "material": True,
        "tags": (),
        "notes": (
            "Emphasis markup around a negative literal. Markup is decoration; "
            "the span must contain the sign and exclude the asterisks."
        ),
        "expected": present(
            parsed="-4",
            spans=[("-4", 0, FIN, SEL, "-4")],
            strategy="explicit_final_marker",
        ),
    },
    # F9 scientific notation span
    {
        "slot": "scientific_marker_positive",
        "family": "scientific_notation_span",
        "rule": "baseline",
        "stratum": "S12",
        "text": "Final answer: 2.5e3",
        "reference": "2500",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "Scientific notation is a registered decimal surface; the whole "
            "literal including the exponent is one span."
        ),
        "expected": present(
            parsed="2500",
            spans=[("2.5e3", 0, FIN, SEL, "2500")],
            strategy="explicit_final_marker",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    {
        "slot": "scientific_boxed_negative_exponent",
        "family": "scientific_notation_span",
        "rule": "baseline",
        "stratum": "S12",
        "text": "\\boxed{-1.2E-2}",
        "reference": "-3/250",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "Upper-case exponent marker with a negative exponent and a negative "
            "mantissa. Truncating at the exponent sign would change the value."
        ),
        "expected": present(
            parsed="-3/250",
            spans=[("-1.2E-2", 0, BOX, SEL, "-3/250")],
            strategy="boxed_answer",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    {
        "slot": "scientific_with_unit_suffix",
        "family": "scientific_notation_span",
        "rule": "C4",
        "stratum": "S02",
        "text": "The answer is 6.02e23 particles",
        "reference": "602000000000000000000000",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "Scientific literal followed by a unit noun. The unit must not "
            "truncate or invalidate the exponent."
        ),
        "expected": present(
            parsed="602000000000000000000000",
            spans=[("6.02e23", 0, ANS, SEL, "602000000000000000000000")],
            strategy="explicit_answer_marker",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    {
        "slot": "scientific_plus_exponent_decorated",
        "family": "scientific_notation_span",
        "rule": "C2",
        "stratum": "S12",
        "text": "**Final answer:** 1.5e+2",
        "reference": "150",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "Explicit positive exponent sign inside a decorated marker. Both the "
            "decoration and the exponent sign must be handled."
        ),
        "expected": present(
            parsed="150",
            spans=[("1.5e+2", 0, FIN, SEL, "150")],
            strategy="explicit_final_marker",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    # F10 reasoning continuation after the final answer
    {
        "slot": "marker_then_double_check",
        "family": "reasoning_continuation_after_answer",
        "rule": "baseline",
        "stratum": "S05",
        "text": "Final answer: 30\nLet me double-check: 5 * 6 = 30, which matches.",
        "reference": "30",
        "material": True,
        "tags": ("multiple_numeric_mentions", "continued_reasoning"),
        "notes": (
            "Verification pass after the marker. Re-derivation that agrees is a "
            "warning, never a competing claim."
        ),
        "expected": present(
            parsed="30",
            spans=[("30", 0, FIN, SEL, "30")],
            strategy="explicit_final_marker",
            warnings=(
                "multiple_numeric_mentions",
                "incidental_numeric_material",
            ),
        ),
    },
    {
        "slot": "marker_then_rederivation",
        "family": "reasoning_continuation_after_answer",
        "rule": "baseline",
        "stratum": "S05",
        "text": "Answer: 14\nActually, let me re-derive. 7 + 7 = 14. Yes.",
        "reference": "14",
        "material": True,
        "tags": ("multiple_numeric_mentions", "continued_reasoning"),
        "notes": (
            "Hedged re-derivation that lands on the same value. `Actually` is "
            "not a registered revision marker."
        ),
        "expected": present(
            parsed="14",
            spans=[("14", 0, ANS, SEL, "14")],
            strategy="explicit_answer_marker",
            warnings=(
                "multiple_numeric_mentions",
                "incidental_numeric_material",
            ),
        ),
    },
    {
        "slot": "marker_then_tagged_continuation",
        "family": "reasoning_continuation_after_answer",
        "rule": "baseline",
        "stratum": "S05",
        "text": "Final answer: 51\n<think>Sanity check: 3 * 17 = 51.</think>",
        "reference": "51",
        "material": True,
        "tags": ("multiple_numeric_mentions", "continued_reasoning"),
        "notes": (
            "Balanced reasoning tags after the answer. Hidden working is not "
            "part of the visible claim."
        ),
        "expected": present(
            parsed="51",
            spans=[("51", 0, FIN, SEL, "51")],
            strategy="explicit_final_marker",
            warnings=(
                "multiple_numeric_mentions",
                "reasoning_continues_after_answer",
            ),
        ),
    },
    {
        "slot": "boxed_then_alternative_discussion",
        "family": "reasoning_continuation_after_answer",
        "rule": "baseline",
        "stratum": "S05",
        "text": "\\boxed{33}\nVerification: an alternative route also lands on 33.",
        "reference": "33",
        "material": True,
        "tags": ("multiple_numeric_mentions", "continued_reasoning"),
        "notes": (
            "Alternative-route discussion after a boxed claim, agreeing on the "
            "same value."
        ),
        "expected": present(
            parsed="33",
            spans=[("33", 0, BOX, SEL, "33")],
            strategy="boxed_answer",
            warnings=(
                "multiple_numeric_mentions",
                "reasoning_continues_after_answer",
            ),
        ),
    },
    # F11 decoration-transparent markers (exercises v3 change C2)
    {
        "slot": "marker_bold_wrapping_label",
        "family": "decorated_explicit_marker",
        "rule": "C2",
        "stratum": "S02",
        "text": "**Final answer:** 21",
        "reference": "21",
        "material": True,
        "tags": (),
        "notes": (
            "Emphasis markup wrapping the marker label and separator. Markup "
            "carries no arithmetic meaning."
        ),
        "expected": present(
            parsed="21",
            spans=[("21", 0, FIN, SEL, "21")],
            strategy="explicit_final_marker",
        ),
    },
    {
        "slot": "marker_backtick_payload",
        "family": "decorated_explicit_marker",
        "rule": "C2",
        "stratum": "S02",
        "text": "Answer: `7`",
        "reference": "7",
        "material": True,
        "tags": (),
        "notes": (
            "Inline-code markup around the payload. The span must exclude the "
            "backticks."
        ),
        "expected": present(
            parsed="7",
            spans=[("7", 0, ANS, SEL, "7")],
            strategy="explicit_answer_marker",
        ),
    },
    {
        "slot": "marker_math_delimited_payload",
        "family": "decorated_explicit_marker",
        "rule": "C2",
        "stratum": "S02",
        "text": "Final answer: \\(96\\)",
        "reference": "96",
        "material": True,
        "tags": (),
        "notes": (
            "Inline math delimiters around the payload. Balanced math delimiters "
            "are decoration."
        ),
        "expected": present(
            parsed="96",
            spans=[("96", 0, FIN, SEL, "96")],
            strategy="explicit_final_marker",
        ),
    },
    {
        "slot": "marker_parenthesized_payload",
        "family": "decorated_explicit_marker",
        "rule": "C2",
        "stratum": "S02",
        "text": "Final answer: (13)",
        "reference": "13",
        "material": True,
        "tags": (),
        "notes": (
            "Parentheses around a single literal are grouping decoration, not an "
            "expression."
        ),
        "expected": present(
            parsed="13",
            spans=[("13", 0, FIN, SEL, "13")],
            strategy="explicit_final_marker",
        ),
    },
    # F12 generalized `is` separator (exercises v3 change C3)
    {
        "slot": "final_answer_is_separator",
        "family": "is_separator_generalization",
        "rule": "C3",
        "stratum": "S02",
        "text": "Final answer is 63",
        "reference": "63",
        "material": True,
        "tags": (),
        "notes": (
            "The protocol registers `is` as a marker separator. It must apply to "
            "every registered label, not only to the bare `Answer` label."
        ),
        "expected": present(
            parsed="63",
            spans=[("63", 0, FIN, SEL, "63")],
            strategy="explicit_final_marker",
        ),
    },
    {
        "slot": "final_is_separator_short_label",
        "family": "is_separator_generalization",
        "rule": "C3",
        "stratum": "S02",
        "text": "Final is 11",
        "reference": "11",
        "material": True,
        "tags": (),
        "notes": (
            "Short `Final` label with the `is` separator; separator support must "
            "not depend on label length."
        ),
        "expected": present(
            parsed="11",
            spans=[("11", 0, FIN, SEL, "11")],
            strategy="explicit_final_marker",
        ),
    },
    {
        "slot": "answer_is_separator_negative",
        "family": "is_separator_generalization",
        "rule": "C3",
        "stratum": "S12",
        "text": "Answer is -2.25",
        "reference": "-9/4",
        "material": True,
        "tags": ("noncanonical_numeric_surface",),
        "notes": (
            "`Answer is` with a negative decimal payload; separator handling and "
            "sign handling must compose."
        ),
        "expected": present(
            parsed="-9/4",
            spans=[("-2.25", 0, ANS, SEL, "-9/4")],
            strategy="explicit_answer_marker",
            warnings=("noncanonical_numeric_surface",),
        ),
    },
    # F13 fail-closed guards that must NOT be relaxed
    {
        "slot": "guard_box_thousands_separator",
        "family": "fail_closed_guard",
        "rule": "C1-guard",
        "stratum": "S10",
        "text": "\\boxed{1,234}",
        "reference": "1234",
        "material": False,
        "tags": ("multiple_numeric_mentions", "malformed_output"),
        "notes": (
            "Grouping separators are not a registered numeric surface. "
            "Decoration tolerance must not silently accept them."
        ),
        "expected": no_answer(
            quality="malformed_unrecoverable",
            failure="unsupported_numeric_literal",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "guard_box_zero_denominator",
        "family": "fail_closed_guard",
        "rule": "C1-guard",
        "stratum": "S10",
        "text": "\\boxed{7/0}",
        "reference": "0",
        "material": False,
        "tags": ("malformed_output",),
        "notes": (
            "Zero denominators have no rational value. The claim must fail "
            "closed rather than report a surface."
        ),
        "expected": no_answer(
            quality="malformed_unrecoverable",
            failure="unsupported_numeric_literal",
        ),
    },
    {
        "slot": "guard_box_latex_fraction_macro",
        "family": "fail_closed_guard",
        "rule": "C1-guard",
        "stratum": "S10",
        "text": "\\boxed{\\frac{1}{2}}",
        "reference": "1/2",
        "material": False,
        "tags": ("multiple_numeric_mentions", "malformed_output"),
        "notes": (
            "A fraction macro is structure, not decoration: stripping it would "
            "invent a value the surface never wrote. Must stay fail-closed."
        ),
        "expected": no_answer(
            quality="malformed_unrecoverable",
            failure="unsupported_numeric_literal",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "guard_box_percent_suffix",
        "family": "fail_closed_guard",
        "rule": "C1-guard",
        "stratum": "S10",
        "text": "\\boxed{25\\%}",
        "reference": "1/4",
        "material": False,
        "tags": ("malformed_output",),
        "notes": (
            "A percent sign changes the value by a factor of 100. It is not a "
            "unit word and must not be treated as decoration."
        ),
        "expected": no_answer(
            quality="malformed_unrecoverable",
            failure="unsupported_numeric_literal",
        ),
    },
    {
        "slot": "guard_marker_unresolved_product",
        "family": "fail_closed_guard",
        "rule": "C4-guard",
        "stratum": "S10",
        "text": "Final answer: 8 * 3",
        "reference": "24",
        "material": False,
        "tags": ("multiple_numeric_mentions", "malformed_output"),
        "notes": (
            "An unevaluated arithmetic expression is not a numeric claim. "
            "Relaxing unit prose must not relax operator continuations."
        ),
        "expected": no_answer(
            quality="malformed_unrecoverable",
            failure="unsupported_numeric_literal",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "guard_marker_unresolved_sum",
        "family": "fail_closed_guard",
        "rule": "C4-guard",
        "stratum": "S10",
        "text": "Final answer: 8 + 1",
        "reference": "9",
        "material": False,
        "tags": ("multiple_numeric_mentions", "malformed_output"),
        "notes": (
            "Addition continuation after the payload. The parser must not "
            "silently truncate at the first operand."
        ),
        "expected": no_answer(
            quality="malformed_unrecoverable",
            failure="unsupported_numeric_literal",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "guard_box_expression_payload",
        "family": "fail_closed_guard",
        "rule": "C1-guard",
        "stratum": "S10",
        "text": "\\boxed{x - 5}",
        "reference": "5",
        "material": False,
        "tags": ("malformed_output",),
        "notes": (
            "Symbolic expression inside the box. Decoration stripping must not "
            "reduce an expression to one of its operands."
        ),
        "expected": no_answer(
            quality="malformed_unrecoverable",
            failure="unsupported_numeric_literal",
        ),
    },
    # F14 truncation and placeholder ordering (exercises v3 change C5)
    {
        "slot": "placeholder_marker_ellipsis",
        "family": "placeholder_before_operator",
        "rule": "C5",
        "stratum": "S07",
        "text": "Final answer: ...",
        "reference": "0",
        "material": False,
        "tags": ("truncated_construct",),
        "notes": (
            "An ellipsis payload is a truncation placeholder, not an unsupported "
            "literal. Ordering the placeholder test first preserves diagnosis."
        ),
        "expected": no_answer(
            quality="truncated",
            failure="truncated_before_final_answer",
        ),
    },
    {
        "slot": "placeholder_box_question_mark",
        "family": "placeholder_before_operator",
        "rule": "C5",
        "stratum": "S07",
        "text": "\\boxed{?}",
        "reference": "0",
        "material": False,
        "tags": ("truncated_construct",),
        "notes": (
            "A question-mark box is an unfilled box, which is a truncated "
            "construct rather than a malformed literal."
        ),
        "expected": no_answer(
            quality="truncated",
            failure="truncated_before_final_answer",
            warnings=("incomplete_box",),
        ),
    },
    {
        "slot": "placeholder_answer_label_ellipsis",
        "family": "placeholder_before_operator",
        "rule": "C5",
        "stratum": "S07",
        "text": "Answer: ...",
        "reference": "0",
        "material": False,
        "tags": ("truncated_construct",),
        "notes": (
            "Same placeholder payload under the `Answer` label; the diagnosis "
            "must not depend on which registered label was used."
        ),
        "expected": no_answer(
            quality="truncated",
            failure="truncated_before_final_answer",
        ),
    },
    {
        "slot": "truncated_empty_marker",
        "family": "placeholder_before_operator",
        "rule": "baseline",
        "stratum": "S07",
        "text": "Final answer:",
        "reference": "0",
        "material": False,
        "tags": ("truncated_construct",),
        "notes": (
            "Marker with no payload at all. This is the canonical truncation "
            "signature and must not be reported as malformed."
        ),
        "expected": no_answer(
            quality="truncated",
            failure="truncated_before_final_answer",
        ),
    },
    # F15 remaining stratum coverage
    {
        "slot": "terminal_equation_numeric_lhs",
        "family": "terminal_equation",
        "rule": "baseline",
        "stratum": "S03",
        "text": "Adding the parts: 3 + 4 = 7",
        "reference": "7",
        "material": True,
        "tags": ("multiple_numeric_mentions",),
        "notes": (
            "Terminal equation with a supported numeric left-hand side; the "
            "right-hand side is the claim."
        ),
        "expected": present(
            parsed="7",
            spans=[("7", 0, EQU, SEL, "7")],
            strategy="terminal_equation",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "stepwise_working_then_marker",
        "family": "multi_step_working",
        "rule": "baseline",
        "stratum": "S04",
        "text": "Step 1: 6 * 7 = 42\nStep 2: confirm.\nFinal answer: 42",
        "reference": "42",
        "material": True,
        "tags": ("multiple_numeric_mentions",),
        "notes": (
            "Numbered working followed by an explicit marker. Step indices and "
            "operands must not compete with the marker claim."
        ),
        "expected": present(
            parsed="42",
            spans=[("42", 1, FIN, SEL, "42")],
            strategy="explicit_final_marker",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "malformed_recoverable_extra_braces",
        "family": "malformed_recoverable",
        "rule": "baseline",
        "stratum": "S09",
        "text": "<think>Scratch 5.</think>\nAnswer: 19}}",
        "reference": "19",
        "material": True,
        "tags": ("multiple_numeric_mentions", "balanced_think_tags"),
        "notes": (
            "Unmatched closing braces after the payload. The claim is still "
            "recoverable and must be reported with a malformed quality."
        ),
        "expected": present(
            parsed="19",
            spans=[("19", 0, ANS, SEL, "19")],
            strategy="explicit_answer_marker",
            quality="malformed_recoverable",
            warnings=("multiple_numeric_mentions",),
        ),
    },
    {
        "slot": "malformed_recoverable_doubled_separator",
        "family": "malformed_recoverable",
        "rule": "C3",
        "stratum": "S09",
        "text": "The answer is:: -8",
        "reference": "-8",
        "material": True,
        "tags": (),
        "notes": (
            "Doubled separator punctuation after a label that already contains "
            "`is`. The redundancy is recoverable, not fatal."
        ),
        "expected": present(
            parsed="-8",
            spans=[("-8", 0, FIN, SEL, "-8")],
            strategy="explicit_final_marker",
            quality="malformed_recoverable",
            warnings=("redundant_answer_marker",),
        ),
    },
    {
        "slot": "unbalanced_think_truncation",
        "family": "truncated_reasoning",
        "rule": "baseline",
        "stratum": "S07",
        "text": "<think>Draft.\nFinal answer: 16",
        "reference": "16",
        "material": False,
        "tags": (
            "malformed_think_tags",
            "incidental_numeric_distractor",
            "truncated_construct",
        ),
        "notes": (
            "The unclosed reasoning tag swallows the marker, so no visible claim "
            "exists. Reporting the hidden value would be a reference leak."
        ),
        "expected": no_answer(
            quality="truncated",
            failure="truncated_before_final_answer",
            warnings=("unbalanced_think_tag", "incidental_numeric_material"),
        ),
    },
    {
        "slot": "placeholder_not_available",
        "family": "placeholder_output",
        "rule": "baseline",
        "stratum": "S08",
        "text": "Result: N/A",
        "reference": "0",
        "material": False,
        "tags": ("placeholder_output",),
        "notes": (
            "Explicit not-available placeholder with no numeric material at all."
        ),
        "expected": no_answer(
            quality="placeholder",
            failure="placeholder_without_answer",
        ),
    },
    {
        "slot": "refusal_without_numbers",
        "family": "placeholder_output",
        "rule": "baseline",
        "stratum": "S08",
        "text": "I cannot determine a numeric result.",
        "reference": "0",
        "material": False,
        "tags": ("placeholder_output",),
        "notes": (
            "Refusal text. There is no claim to extract and none may be "
            "invented."
        ),
        "expected": no_answer(
            quality="placeholder",
            failure="placeholder_without_answer",
        ),
    },
    {
        "slot": "empty_box_payload",
        "family": "fail_closed_guard",
        "rule": "C1-guard",
        "stratum": "S10",
        "text": "\\boxed{}",
        "reference": "0",
        "material": False,
        "tags": ("malformed_output",),
        "notes": (
            "An empty box has no payload to decorate. Decoration tolerance must "
            "not turn emptiness into a claim."
        ),
        "expected": no_answer(
            quality="malformed_unrecoverable",
            failure="unsupported_numeric_literal",
        ),
    },
)


def _span_offsets(text: str, needle: str, occurrence: int) -> tuple[int, int]:
    start = -1
    for _ in range(occurrence + 1):
        start = text.find(needle, start + 1)
        if start < 0:
            raise ValueError(f"needle {needle!r} occurrence {occurrence} not found")
    return start, start + len(needle)


def _build_spans(
    text: str, declared: list[tuple[str, int, str, str, str]]
) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for needle, occurrence, kind, disposition, normalized in declared:
        start, end = _span_offsets(text, needle, occurrence)
        spans.append(
            {
                "disposition": disposition,
                "end": end,
                "kind": kind,
                "normalized_answer": normalized,
                "start": start,
                "text": needle,
            }
        )
    return spans


def build_record(spec: dict[str, Any]) -> dict[str, Any]:
    """Materialize one validated development record from a declared spec."""
    text = spec["text"]
    expected = spec["expected"]
    spans = _build_spans(text, expected["spans"])
    presence = expected["presence"]
    reference = spec["reference"]
    correctness = presence == "present" and expected["parsed"] == reference
    declared_tags = set(spec["tags"]) - QUOTA_DIAGNOSTIC_TAGS
    derived_quota = (
        _surface_features(
            {
                "output_text": text,
                "expected_parsed_answer": expected["parsed"],
                "expected_evidence_spans": spans,
            }
        )
        & QUOTA_DIAGNOSTIC_TAGS
    )
    secondary_tags = [
        tag
        for tag in SECONDARY_TAGS
        if tag in declared_tags or tag in derived_quota
    ]
    record = {
        "case_id": derive_case_id(PUBLIC_CASE_ID_SALT, "numeric", text),
        "critical_case": spec["stratum"] in CRITICAL_STRATA,
        "curation_notes": (
            f"Public parser-v3 adversarial development fixture for slot "
            f"{spec['slot']} (family {spec['family']}, rule {spec['rule']}). "
            f"{spec['notes']}"
        ),
        "expected_answer_presence": presence,
        "expected_candidate_answers": list(expected["candidates"]),
        "expected_correctness": correctness,
        "expected_evidence_spans": spans,
        "expected_extraction_strategy": expected["strategy"],
        "expected_failure_reasons": list(expected["failures"]),
        "expected_format_warnings": list(expected["warnings"]),
        "expected_output_quality": expected["quality"],
        "expected_parse_ambiguous": expected["parse_ambiguous"],
        "expected_parse_valid": expected["parse_valid"],
        "expected_parsed_answer": expected["parsed"],
        "material_error_if_missed": spec["material"],
        "output_text": text,
        "parse_type": "numeric",
        "registered_reference_answer": reference,
        "schema_version": DEVELOPMENT_SCHEMA_VERSION,
        "secondary_tags": secondary_tags,
        "source_kind": SOURCE_KIND,
        "stratum": spec["stratum"],
    }
    validate_development_record(record, name=f"adversarial[{spec['slot']}]")
    return record


def build_all() -> list[dict[str, Any]]:
    """Build, validate, and order every adversarial development record."""
    slots = [spec["slot"] for spec in FIXTURE_SPECS]
    if len(set(slots)) != len(slots):
        raise ValidationSetError("adversarial slots must be unique")
    texts = [spec["text"] for spec in FIXTURE_SPECS]
    if len(set(texts)) != len(texts):
        raise ValidationSetError("adversarial output_text values must be unique")
    records = [build_record(spec) for spec in FIXTURE_SPECS]
    case_ids = [record["case_id"] for record in records]
    if len(set(case_ids)) != len(case_ids):
        raise ValidationSetError("adversarial case_id values must be unique")
    records.sort(key=lambda record: record["case_id"])
    return records


def serialize(records: list[dict[str, Any]]) -> str:
    """Render the canonical JSONL payload."""
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the on-disk file matches the declared specs",
    )
    args = parser.parse_args()
    records = build_all()
    payload = serialize(records)
    if args.check:
        current = OUTPUT_PATH.read_text(encoding="utf-8")
        if current != payload:
            print("adversarial development fixtures are out of date")
            return 1
        print(f"adversarial development fixtures are current ({len(records)} cases)")
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    print(f"wrote {len(records)} adversarial development cases to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
