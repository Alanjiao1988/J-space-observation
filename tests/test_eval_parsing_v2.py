"""Public-development tests for the prospective parser-v2 implementation."""

from __future__ import annotations

import builtins
import hashlib
import inspect
import json
import os
import socket
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jspace_observation.eval_parsing_v2 import (
    PARSER_SOURCE_SHA256,
    PARSER_VERSION,
    canonicalize_parser_source_for_digest,
    compare_parsed_answer_to_reference,
    compute_parser_source_sha256,
    compute_parser_version,
    parse_v2,
)
from jspace_observation.evaluator_validation import (
    PARSER_REQUEST_SCHEMA_VERSION,
    PARSER_RESULT_SCHEMA_VERSION,
    ValidationSetError,
    derive_typed_decision,
    normalize_rational_literal,
    validate_development_record,
    validate_parser_result,
)


DEVELOPMENT_PATH = (
    ROOT / "evaluator_sets" / "parser_v2_v1" / "development_cases.jsonl"
)
DEVELOPMENT_SHA256 = (
    "bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27"
)
MODULE_PATH = ROOT / "src" / "jspace_observation" / "eval_parsing_v2.py"
RESULT_FIELDS = {
    "schema_version",
    "parser_version",
    "answer_type",
    "input_sha256",
    "answer_presence",
    "parse_valid",
    "parse_ambiguous",
    "parsed_answer",
    "candidate_answers",
    "evidence_spans",
    "extraction_strategy",
    "output_quality",
    "failure_reasons",
    "format_warnings",
}
EXTRACTION_FIELDS = (
    "answer_presence",
    "parse_valid",
    "parse_ambiguous",
    "parsed_answer",
    "candidate_answers",
    "evidence_spans",
    "extraction_strategy",
    "output_quality",
    "failure_reasons",
    "format_warnings",
)
EXPECTED_TO_PARSER_PRESENCE = {
    "present": "present",
    "ambiguous": "uncertain",
    "no_answer": "absent",
}


def request(output_text: str) -> dict[str, str]:
    return {
        "schema_version": PARSER_REQUEST_SCHEMA_VERSION,
        "answer_type": "numeric",
        "output_text": output_text,
    }


def load_public_development_rows() -> list[dict]:
    payload = DEVELOPMENT_PATH.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == DEVELOPMENT_SHA256
    return [
        json.loads(line)
        for line in payload.decode("utf-8").splitlines()
        if line
    ]


def expected_extraction(row: dict) -> dict:
    expected = {
        field: deepcopy(row[f"expected_{field}"])
        for field in EXTRACTION_FIELDS
    }
    expected["answer_presence"] = EXPECTED_TO_PARSER_PRESENCE[
        expected["answer_presence"]
    ]
    return expected


def extraction(result: dict) -> dict:
    return {field: result[field] for field in EXTRACTION_FIELDS}


def test_all_60_public_development_rows_match_exact_extraction_oracle():
    rows = load_public_development_rows()
    assert len(rows) == 60

    for index, row in enumerate(rows):
        validate_development_record(row, name=f"development[{index}]")
        parser_request = request(row["output_text"])
        assert set(parser_request) == {
            "schema_version",
            "answer_type",
            "output_text",
        }

        result = parse_v2(parser_request)
        assert set(result) == RESULT_FIELDS
        validate_parser_result(
            result,
            row["output_text"],
            name=f"result[{row['case_id']}]",
        )
        assert extraction(result) == expected_extraction(row)
        assert derive_typed_decision(result) == derive_typed_decision(row)

        correctness = compare_parsed_answer_to_reference(
            result, row["registered_reference_answer"]
        )
        assert correctness is row["expected_correctness"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: {key: item for key, item in value.items() if key != "output_text"},
        lambda value: {**value, "case_id": "forbidden"},
        lambda value: {**value, "schema_version": "phase1-parser-v2-request/v0"},
        lambda value: {**value, "answer_type": "entity"},
        lambda value: {**value, "output_text": None},
        lambda value: {**value, "output_text": 7},
        lambda value: {**value, "answer_type": 1},
        lambda value: {**value, "schema_version": None},
    ],
)
def test_request_fails_closed_on_missing_extra_invalid_schema_or_type(mutation):
    with pytest.raises(ValidationSetError):
        parse_v2(mutation(request("Answer: 1")))


def test_parse_v2_accepts_no_kwargs_or_reference_channel():
    assert tuple(inspect.signature(parse_v2).parameters) == ("request",)
    with pytest.raises(TypeError):
        parse_v2(request("Answer: 1"), reference_answer="1")


@pytest.mark.parametrize(
    ("surface", "canonical"),
    [
        ("+0012", "12"),
        ("-0.000", "0"),
        (".5", "1/2"),
        ("1.25", "5/4"),
        ("5e-1", "1/2"),
        ("-6/8", "-3/4"),
    ],
)
def test_exact_bounded_rational_normalization(surface, canonical):
    assert normalize_rational_literal(surface) == canonical
    result = parse_v2(request(f"Final answer: {surface}"))
    assert result["parsed_answer"] == canonical


@pytest.mark.parametrize(
    "surface",
    [
        "1e5000",
        "0e" + "9" * 97,
        "1" * 101,
        "1/0",
        "25%",
        "1 /2",
        "1+2",
    ],
)
def test_unsupported_or_out_of_bound_marker_literal_fails_closed(surface):
    result = parse_v2(request(f"Final answer: {surface}"))
    assert derive_typed_decision(result) == "no_answer"
    assert result["failure_reasons"] == ["unsupported_numeric_literal"]
    assert result["parse_ambiguous"] is False


def test_evidence_priority_and_lower_priority_conflicts():
    boxed = parse_v2(
        request("Answer: 2\nFinal answer: 3\nThe result is \\boxed{1}.")
    )
    assert derive_typed_decision(boxed) == "present:1"
    assert boxed["extraction_strategy"] == "boxed_answer"
    assert "lower_priority_conflict_ignored" in boxed["format_warnings"]

    final = parse_v2(request("Final answer: 3\nAnswer: 4\nx = 5"))
    assert derive_typed_decision(final) == "present:3"
    assert final["extraction_strategy"] == "explicit_final_marker"
    assert "lower_priority_conflict_ignored" in final["format_warnings"]

    answer = parse_v2(request("Answer: 4\nx = 5"))
    assert derive_typed_decision(answer) == "present:4"
    assert answer["extraction_strategy"] == "explicit_answer_marker"
    assert "lower_priority_conflict_ignored" in answer["format_warnings"]


def test_terminal_equation_and_single_candidate_are_bounded_fallbacks():
    terminal = parse_v2(request("Working line:\n3 / 4 = .75"))
    assert derive_typed_decision(terminal) == "present:3/4"
    assert terminal["extraction_strategy"] == "terminal_equation"

    single = parse_v2(request("[+.50]."))
    assert derive_typed_decision(single) == "present:1/2"
    assert single["extraction_strategy"] == "single_candidate"

    prose = parse_v2(request("We considered 3, then 4, and finally mentioned 5."))
    assert derive_typed_decision(prose) == "no_answer"
    assert prose["failure_reasons"] == ["no_reliable_answer"]


def test_balanced_unclosed_malformed_and_stray_think_regions():
    balanced = parse_v2(
        request("<THINK>Answer: 99</THINK>\nFinal answer: 2")
    )
    assert derive_typed_decision(balanced) == "present:2"
    assert balanced["evidence_spans"][0]["start"] == (
        "<THINK>Answer: 99</THINK>\nFinal answer: 2".rindex("2")
    )

    unclosed = parse_v2(request("<think>Final answer: 2"))
    assert derive_typed_decision(unclosed) == "no_answer"
    assert unclosed["output_quality"] == "truncated"
    assert "unbalanced_think_tag" in unclosed["format_warnings"]

    malformed = parse_v2(request("<think broken>Answer: 2"))
    assert derive_typed_decision(malformed) == "no_answer"
    assert "unbalanced_think_tag" in malformed["format_warnings"]

    stray = parse_v2(request("</think> Answer: 2"))
    assert derive_typed_decision(stray) == "present:2"
    assert stray["output_quality"] == "malformed_recoverable"
    assert "stray_think_tag" in stray["format_warnings"]


def test_equivalent_claims_collapse_and_distinct_claims_are_ambiguous():
    equivalent = parse_v2(request("Answer: 1/2\nAnswer: .5"))
    assert derive_typed_decision(equivalent) == "present:1/2"
    assert equivalent["candidate_answers"] == ["1/2"]
    assert [span["disposition"] for span in equivalent["evidence_spans"]] == [
        "selected",
        "equivalent",
    ]
    assert "equivalent_repeated_claim" in equivalent["format_warnings"]

    ambiguous = parse_v2(request("Answer: 1\nAnswer: 2"))
    assert derive_typed_decision(ambiguous) == "ambiguous"
    assert ambiguous["candidate_answers"] == ["1", "2"]
    assert all(
        span["disposition"] == "ambiguous_candidate"
        for span in ambiguous["evidence_spans"]
    )


def test_explicit_correction_resolves_an_earlier_same_tier_claim():
    result = parse_v2(
        request("Final answer: 1. Correction: Final answer: 2")
    )
    assert derive_typed_decision(result) == "present:2"
    assert "lower_priority_conflict_ignored" in result["format_warnings"]


def test_invalid_complete_box_blocks_lower_tiers_but_incomplete_box_falls_through():
    invalid = parse_v2(request("\\boxed{7/0}\nFinal answer: 1"))
    assert derive_typed_decision(invalid) == "no_answer"
    assert invalid["failure_reasons"] == ["unsupported_numeric_literal"]

    incomplete = parse_v2(request("\\boxed{?\nFinal answer: 3"))
    assert derive_typed_decision(incomplete) == "present:3"
    assert incomplete["output_quality"] == "truncated"
    assert "incomplete_box" in incomplete["format_warnings"]


def test_unicode_code_point_span_is_exact():
    text = "雪🙂 Final answer: -6/8"
    result = parse_v2(request(text))
    span = result["evidence_spans"][0]
    assert span["start"] == text.index("-6/8")
    assert span["end"] == span["start"] + len("-6/8")
    assert text[span["start"] : span["end"]] == span["text"]
    assert span["normalized_answer"] == "-3/4"
    validate_parser_result(result, text)


def test_last_number_traps_do_not_override_or_create_ambiguity():
    explicit = parse_v2(
        request("Final answer: 5\nMetadata code: 99")
    )
    assert derive_typed_decision(explicit) == "present:5"
    assert explicit["parse_ambiguous"] is False
    assert "incidental_numeric_material" in explicit["format_warnings"]

    no_claim = parse_v2(request("Scratch values were 5 and 99."))
    assert derive_typed_decision(no_claim) == "no_answer"
    assert no_claim["parse_ambiguous"] is False


def test_empty_placeholder_and_no_reliable_answer_are_distinct_not_ambiguous():
    empty = parse_v2(request(""))
    assert empty["output_quality"] == "empty"
    assert empty["failure_reasons"] == ["empty_output"]

    placeholder = parse_v2(request("I cannot provide an answer."))
    assert placeholder["output_quality"] == "placeholder"
    assert placeholder["failure_reasons"] == ["placeholder_without_answer"]

    no_answer = parse_v2(request("A discussion has value 7 but no conclusion."))
    assert no_answer["output_quality"] == "complete"
    assert no_answer["failure_reasons"] == ["no_reliable_answer"]
    assert no_answer["parse_ambiguous"] is False


def test_correctness_comparison_is_post_extraction_and_exact():
    result = parse_v2(request("Final answer: .5"))
    frozen_result = deepcopy(result)
    assert compare_parsed_answer_to_reference(result, "1/2") is True
    assert compare_parsed_answer_to_reference(result, "0.50") is True
    assert compare_parsed_answer_to_reference(result, "2") is False
    assert result == frozen_result
    assert tuple(
        inspect.signature(compare_parsed_answer_to_reference).parameters
    ) == ("parser_output", "reference_answer")


def test_parse_is_deterministic_and_binds_exact_utf8_input():
    parser_request = request("雪\nFinal answer: +0012")
    first = parse_v2(parser_request)
    for _ in range(20):
        assert parse_v2(deepcopy(parser_request)) == first
    assert first["input_sha256"] == hashlib.sha256(
        parser_request["output_text"].encode("utf-8")
    ).hexdigest()
    assert first["parser_version"] == PARSER_VERSION
    assert first["schema_version"] == PARSER_RESULT_SCHEMA_VERSION


def test_parser_version_and_source_digest_recipe_are_stable():
    source = MODULE_PATH.read_bytes()
    assert compute_parser_source_sha256(source) == PARSER_SOURCE_SHA256
    assert compute_parser_version(PARSER_SOURCE_SHA256) == PARSER_VERSION
    lf_source = source.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    assert compute_parser_source_sha256(
        lf_source.replace(b"\n", b"\r\n")
    ) == PARSER_SOURCE_SHA256

    canonical = canonicalize_parser_source_for_digest(source)
    changed_constants = source.replace(
        PARSER_VERSION.encode("ascii"),
        ("f" * 64).encode("ascii"),
        1,
    )
    assert canonicalize_parser_source_for_digest(changed_constants) == canonical
    assert compute_parser_source_sha256(source + b"\n# semantic change\n") != (
        PARSER_SOURCE_SHA256
    )


def test_extraction_uses_no_environment_filesystem_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("ambient access is forbidden during extraction")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    result = parse_v2(request("Final answer: 7/8"))
    assert derive_typed_decision(result) == "present:7/8"
