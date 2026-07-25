"""Deterministic, reference-blind numeric extraction for parser-v3.

``parse_v3`` accepts only the frozen three-field request.  Correctness is kept
in ``compare_parsed_answer_to_reference`` so a reference cannot affect
extraction.  The module is standalone: it never imports parser-v2, and the
extraction entry point ``_extract`` receives a single ``str`` so no reference,
expected label, case ID, or stratum can reach candidate selection.

Parser v3 is failure-directed.  It keeps every parser-v2 rule that the frozen
protocol registers and changes exactly five families of behaviour that the
parser-v2 locked evaluation showed to be either protocol-nonconforming or
internally inconsistent:

1. a complete balanced box whose interior is one registered literal wrapped in
   presentation-only decoration is recovered instead of failing closed;
2. presentation-only decoration between a marker, its separator, and its
   literal is transparent;
3. the registered ``is`` separator applies to every registered marker label,
   not only to the bare ``Answer`` label;
4. a whitespace-separated trailing unit word no longer invalidates an
   otherwise complete claim, because token context, not following prose,
   decides span validity; and
5. an explicit ellipsis or question placeholder after a marker or box is a
   truncation cue rather than an unsupported literal.

Parser provenance uses two non-self-referential digests.  The source digest is
SHA-256 over a domain separator and this UTF-8 source after newline
canonicalization and replacement of the two digest assignment values below by
64 zeroes.  ``parser_version`` is SHA-256 over a second domain separator and a
canonical JSON manifest binding that source digest to the frozen protocol,
request/result schemas, normalizer, and algorithm identifiers.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .evaluator_validation import (
    FROZEN_PROTOCOL_BUNDLE_SHA256,
    FROZEN_PROTOCOL_VERSION,
    PARSER_REQUEST_SCHEMA_VERSION,
    PARSER_RESULT_SCHEMA_VERSION,
    ValidationSetError,
    derive_typed_decision,
    normalize_rational_literal,
    validate_evidence_span,
    validate_parser_request,
    validate_parser_result,
)


PARSER_SOURCE_SHA256 = "76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9"
PARSER_VERSION = "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace"

PARSER_SOURCE_DIGEST_DOMAIN = b"jspace-parser-v3/source/v1\0"
PARSER_VERSION_DIGEST_DOMAIN = b"jspace-parser-v3/version/v1\0"
PARSER_ALGORITHM_ID = "jspace-parser-v3-reference-blind-extraction/v1"
PARSER_NORMALIZER_ID = (
    "jspace_observation.evaluator_validation.normalize_rational_literal"
)

_PROVENANCE_LINE_PATTERN = re.compile(
    r'^(PARSER_SOURCE_SHA256|PARSER_VERSION) = "[0-9a-f]{64}"$',
    re.MULTILINE,
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)

_NUMERIC_BODY = (
    r"(?:"
    r"[+-]?[0-9]+/[0-9]+"
    r"|"
    r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))"
    r"(?:[eE][+-]?[0-9]+)?"
    r")"
)
_NUMERIC_TOKEN_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9_]){_NUMERIC_BODY}(?![A-Za-z0-9_])",
    re.ASCII,
)
_NUMERIC_AT_PATTERN = re.compile(_NUMERIC_BODY, re.ASCII)
_NUMERIC_FULL_PATTERN = re.compile(rf"{_NUMERIC_BODY}\Z", re.ASCII)
_BOX_OPEN_PATTERN = re.compile(r"\\boxed\s*\{", re.ASCII)
_MARKER_LABEL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?P<label>final\s+answer|the\s+answer\s+is|answer|final)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE | re.ASCII,
)
_THINK_TAG_PATTERN = re.compile(
    r"<\s*(?P<closing>/?)\s*think(?P<tail>[^>]*)>",
    re.IGNORECASE,
)
_BROKEN_THINK_OPEN_PATTERN = re.compile(r"<\s*think\b", re.IGNORECASE)
_CONCLUSION_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:candidate|alternate|alternative)\s+"
    r"(?:conclusion|answer|result)"
    r"\s*(?:(?:[:：=])|\bis\b)?\s*",
    re.IGNORECASE | re.ASCII,
)

_WARNING_ORDER = (
    "multiple_numeric_mentions",
    "reasoning_continues_after_answer",
    "equivalent_repeated_claim",
    "lower_priority_conflict_ignored",
    "incomplete_box",
    "unbalanced_think_tag",
    "stray_think_tag",
    "redundant_answer_marker",
    "noncanonical_numeric_surface",
    "incidental_numeric_material",
)

_HARMLESS_RESIDUAL_PATTERN = re.compile(r"[\s.,;:!?()\[\]{}$\\'\"`*_~]*\Z")
_PLACEHOLDER_PATTERN = re.compile(
    r"(?:"
    r"\bcannot\b|\brefus(?:e|ed|al)\b|\bomitted\b|"
    r"\bno\s+answer\b|\bprompt\s+echoed\b|"
    r"(?:^|\W)n\s*/?\s*a(?:\W|$)"
    r")",
    re.IGNORECASE | re.ASCII,
)
_TRUNCATION_CUE_PATTERN = re.compile(
    r"(?:"
    r"\b(?:incomplete|truncated|cut\s+off)\b|"
    r"\b(?:should|would|will)\s+(?:now\s+)?(?:say|follow)\b|"
    r"\bintended\s+answer\b"
    r")",
    re.IGNORECASE | re.ASCII,
)
_STRONG_MALFORMED_PATTERN = re.compile(
    r"(?:"
    r"\b(?:broken|corrupt(?:ed)?|damaged|unreadable|garbled)\b|"
    r"<\s*/?\s*answer\b|</\s*ans\s+wer\s*>|\?\?\?"
    r")",
    re.IGNORECASE | re.ASCII,
)
_REASONING_CONTINUATION_PATTERN = re.compile(
    r"(?:"
    r"<\s*think\b|"
    r"\b(?:verification|verify|reconsider(?:ed|ation)?|derivation|proof)\b|"
    r"\bbecause\b|\bthis\s+follows\b|"
    r"\bafter\s+(?:a\s+)?review\b|"
    r"\bafter\s+step\s+[0-9]+\b"
    r")",
    re.IGNORECASE | re.ASCII,
)
_INCIDENTAL_SUFFIX_PATTERN = re.compile(
    r"(?:"
    r"\b(?:metadata|confidence|code|fields?|instruction|distractor|record)\b|"
    r"\bnon-answer\b|\bnot\s+an?\s+answer\b|"
    r"\bignore(?:d)?\b|\bafter\s+step\s+[0-9]+\b"
    r")",
    re.IGNORECASE | re.ASCII,
)
_CORRECTION_PATTERN = re.compile(
    r"(?:correction|corrected|revised|revision)\s*[:：]?\s*$",
    re.IGNORECASE | re.ASCII,
)
_TERMINAL_SUFFIX_PATTERN = re.compile(r"[\s.,;:!?()[\]{}$\\'\"`*_~]*\Z")

_DECORATION_OPENERS = "*_`~\"'([{"
_DECORATION_MIRRORS = {
    "*": "*",
    "_": "_",
    "`": "`",
    "~": "~",
    '"': '"',
    "'": "'",
    "(": ")",
    "[": "]",
    "{": "}",
}
_LATEX_DECORATION_PREFIXES = (
    r"\qquad",
    r"\quad",
    r"\left(",
    r"\left[",
    r"\displaystyle",
    r"\(",
    r"\[",
    r"\,",
    r"\!",
    r"\;",
    r"\:",
)
_BOX_DECORATION_PATTERN = re.compile(
    r"\\(?:boxed|displaystyle|mathbf|mathrm|textbf|textrm|text|left|right"
    r"|quad|qquad|rm|bf)(?![A-Za-z])"
    r"|\\[,;:!]"
    r"|[{}]",
    re.ASCII,
)
_BOX_FORM_PATTERN = re.compile(
    rf"{_NUMERIC_BODY}(?:\s+[A-Za-z]+)*\Z",
    re.ASCII,
)
_BOX_PLACEHOLDER_PATTERN = re.compile(r"(?:\?+|\.{3,}|…+)")


def canonicalize_parser_source_for_digest(source_bytes: bytes) -> bytes:
    """Return the canonical, non-self-referential source-digest payload."""
    if not isinstance(source_bytes, bytes):
        raise TypeError("source_bytes must be bytes")
    text = source_bytes.decode("utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    replaced: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        replaced.add(name)
        return f'{name} = "{"0" * 64}"'

    canonical = _PROVENANCE_LINE_PATTERN.sub(replace, text)
    if replaced != {"PARSER_SOURCE_SHA256", "PARSER_VERSION"}:
        raise ValueError("source must contain both provenance digest assignments")
    return canonical.encode("utf-8")


def compute_parser_source_sha256(source_bytes: bytes) -> str:
    """Compute the registered source digest without reading a file."""
    digest = hashlib.sha256()
    digest.update(PARSER_SOURCE_DIGEST_DOMAIN)
    digest.update(canonicalize_parser_source_for_digest(source_bytes))
    return digest.hexdigest()


def parser_version_manifest(source_sha256: str) -> dict[str, str]:
    """Build the exact canonical manifest bound by ``parser_version``."""
    if not isinstance(source_sha256, str) or not _SHA256_PATTERN.fullmatch(
        source_sha256
    ):
        raise ValueError("source_sha256 must be lowercase SHA-256")
    return {
        "algorithm_id": PARSER_ALGORITHM_ID,
        "normalizer_id": PARSER_NORMALIZER_ID,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "protocol_version": FROZEN_PROTOCOL_VERSION,
        "request_schema_version": PARSER_REQUEST_SCHEMA_VERSION,
        "result_schema_version": PARSER_RESULT_SCHEMA_VERSION,
        "source_sha256": source_sha256,
    }


def compute_parser_version(source_sha256: str) -> str:
    """Derive ``parser_version`` from a source digest and frozen bindings."""
    manifest_bytes = json.dumps(
        parser_version_manifest(source_sha256),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    digest = hashlib.sha256()
    digest.update(PARSER_VERSION_DIGEST_DOMAIN)
    digest.update(manifest_bytes)
    return digest.hexdigest()


@dataclass(frozen=True)
class _Candidate:
    start: int
    end: int
    text: str
    kind: str
    normalized: str
    claim_start: int


@dataclass(frozen=True)
class _ThinkScan:
    visible_text: str
    unbalanced: bool
    stray: bool
    unclosed: bool
    malformed_open: bool


@dataclass(frozen=True)
class _BoxScan:
    candidates: tuple[_Candidate, ...]
    invalid_complete: bool
    incomplete: bool


@dataclass(frozen=True)
class _MarkerOccurrence:
    family: str
    label_key: str
    marker_start: int
    payload_start: int
    candidate: _Candidate | None
    invalid_complete: bool
    incomplete: bool
    wraps_box: bool
    repeated_separator: bool


@dataclass(frozen=True)
class _EquationScan:
    candidates: tuple[_Candidate, ...]
    invalid_complete: bool
    incomplete: bool


def _mask_ranges(text: str, ranges: list[tuple[int, int]]) -> str:
    characters = list(text)
    for start, end in ranges:
        for index in range(start, end):
            if characters[index] not in "\r\n":
                characters[index] = " "
    return "".join(characters)


def _scan_think_regions(text: str) -> _ThinkScan:
    ranges: list[tuple[int, int]] = []
    matched_ranges: list[tuple[int, int]] = []
    depth = 0
    region_start = 0
    unbalanced = False
    stray = False
    unclosed = False
    malformed_open = False

    for match in _THINK_TAG_PATTERN.finditer(text):
        matched_ranges.append(match.span())
        closing = bool(match.group("closing"))
        malformed = bool(match.group("tail").strip())
        if closing:
            if depth == 0:
                ranges.append(match.span())
                stray = True
                if malformed:
                    unbalanced = True
                continue
            if malformed:
                unbalanced = True
            depth -= 1
            if depth == 0:
                ranges.append((region_start, match.end()))
        else:
            if depth == 0:
                region_start = match.start()
            else:
                unbalanced = True
            depth += 1
            if malformed:
                malformed_open = True
                unbalanced = True

    for match in _BROKEN_THINK_OPEN_PATTERN.finditer(text):
        if not any(start <= match.start() < end for start, end in matched_ranges):
            if depth == 0:
                region_start = match.start()
            depth += 1
            malformed_open = True
            unbalanced = True
            break

    if depth:
        ranges.append((region_start, len(text)))
        unbalanced = True
        unclosed = True

    return _ThinkScan(
        visible_text=_mask_ranges(text, ranges),
        unbalanced=unbalanced,
        stray=stray,
        unclosed=unclosed,
        malformed_open=malformed_open,
    )


def _candidate(
    output_text: str,
    start: int,
    end: int,
    kind: str,
    *,
    claim_start: int | None = None,
) -> _Candidate | None:
    if start < 0 or end <= start or end > len(output_text):
        return None
    surface = output_text[start:end]
    try:
        normalized = normalize_rational_literal(surface)
        validate_evidence_span(
            {
                "start": start,
                "end": end,
                "text": surface,
                "kind": kind,
                "normalized_answer": normalized,
                "disposition": "selected",
            },
            output_text,
        )
    except ValidationSetError:
        return None
    return _Candidate(
        start=start,
        end=end,
        text=surface,
        kind=kind,
        normalized=normalized,
        claim_start=start if claim_start is None else claim_start,
    )


def _matching_brace(text: str, opening: int) -> int | None:
    depth = 1
    for index in range(opening + 1, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _skip_decoration(text: str, cursor: int) -> tuple[int, tuple[str, ...]]:
    """Skip presentation-only decoration and report the delimiters opened."""
    opened: list[str] = []
    while cursor < len(text):
        character = text[cursor]
        if character.isspace():
            cursor += 1
            continue
        if character in _DECORATION_OPENERS:
            opened.append(character)
            cursor += 1
            continue
        prefix = next(
            (
                item
                for item in _LATEX_DECORATION_PREFIXES
                if text.startswith(item, cursor)
            ),
            None,
        )
        if prefix is None:
            break
        if prefix.endswith(("(", "[")):
            opened.append(prefix[-1])
        cursor += len(prefix)
    return cursor, tuple(opened)


def _skip_closing_decoration(
    text: str, cursor: int, opened: tuple[str, ...]
) -> int:
    """Consume only closers that are mirrored and immediately adjacent."""
    remaining = [_DECORATION_MIRRORS[item] for item in opened]
    while cursor < len(text) and remaining and text[cursor] in remaining:
        remaining.remove(text[cursor])
        cursor += 1
    return cursor


def _strip_outer_brackets(value: str) -> str:
    pairs = {"(": ")", "[": "]"}
    text = value.strip()
    while len(text) >= 2 and text[0] in pairs and text[-1] == pairs[text[0]]:
        depth = 0
        balanced = True
        for index, character in enumerate(text):
            if character in pairs:
                depth += 1
            elif character in pairs.values():
                depth -= 1
                if depth == 0 and index != len(text) - 1:
                    balanced = False
                    break
        if not balanced:
            break
        text = text[1:-1].strip()
    return text


def _box_interior_is_decorated_literal(interior: str) -> bool:
    """Accept one registered literal wrapped in presentation-only decoration."""
    if "%" in interior:
        return False
    stripped = " ".join(_BOX_DECORATION_PATTERN.sub(" ", interior).split())
    stripped = _strip_outer_brackets(stripped)
    return bool(_BOX_FORM_PATTERN.fullmatch(stripped))


def _decorated_box_candidate(
    output_text: str,
    visible_text: str,
    start: int,
    end: int,
    claim_start: int,
) -> tuple[_Candidate | None, str]:
    interior = visible_text[start:end]
    if _BOX_PLACEHOLDER_PATTERN.fullmatch(interior):
        return None, "incomplete"
    if not _box_interior_is_decorated_literal(interior):
        return None, "invalid"
    tokens = [
        found
        for match in _NUMERIC_TOKEN_PATTERN.finditer(visible_text, start, end)
        for found in (
            _candidate(
                output_text,
                match.start(),
                _claim_numeric_end(visible_text, match),
                "boxed",
                claim_start=claim_start,
            ),
        )
        if found is not None
    ]
    if len(tokens) != 1:
        return None, "invalid"
    return tokens[0], "valid"


def _scan_boxes(output_text: str, visible_text: str) -> _BoxScan:
    candidates: list[_Candidate] = []
    invalid_complete = False
    incomplete = False
    cursor = 0
    while True:
        match = _BOX_OPEN_PATTERN.search(visible_text, cursor)
        if match is None:
            break
        opening = visible_text.rfind("{", match.start(), match.end())
        closing = _matching_brace(visible_text, opening)
        if closing is None:
            incomplete = True
            cursor = match.end()
            continue
        inner = visible_text[opening + 1 : closing]
        leading = len(inner) - len(inner.lstrip())
        trailing = len(inner.rstrip())
        if trailing <= leading:
            invalid_complete = True
        else:
            start = opening + 1 + leading
            end = opening + 1 + trailing
            surface = output_text[start:end]
            if _NUMERIC_FULL_PATTERN.fullmatch(surface):
                found = _candidate(
                    output_text,
                    start,
                    end,
                    "boxed",
                    claim_start=match.start(),
                )
                if found is None:
                    invalid_complete = True
                else:
                    candidates.append(found)
            else:
                found, state = _decorated_box_candidate(
                    output_text,
                    visible_text,
                    start,
                    end,
                    match.start(),
                )
                if found is not None:
                    candidates.append(found)
                elif state == "incomplete":
                    incomplete = True
                else:
                    invalid_complete = True
        cursor = closing + 1
    return _BoxScan(
        candidates=tuple(candidates),
        invalid_complete=invalid_complete,
        incomplete=incomplete,
    )


def _skip_whitespace(text: str, cursor: int) -> tuple[int, bool]:
    start = cursor
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor, cursor > start


def _claim_has_invalid_continuation(
    text: str, token_end: int, opened: tuple[str, ...] = ()
) -> bool:
    cursor = _skip_closing_decoration(text, token_end, opened)
    cursor, _ = _skip_whitespace(text, cursor)
    if cursor >= len(text):
        return False
    if text[cursor] in "+*/":
        return True
    if (
        text[cursor] == "-"
        and cursor + 1 < len(text)
        and (text[cursor + 1].isdigit() or text[cursor + 1] == ".")
    ):
        return True
    return False


def _claim_numeric_end(text: str, match: re.Match[str]) -> int:
    """Treat a bare terminal decimal point as sentence punctuation."""
    surface = match.group(0)
    if re.fullmatch(r"[+-]?[0-9]+\.", surface, re.ASCII):
        following = text[match.end() : match.end() + 1]
        if not following or following.isspace() or following in ")]};,!?:$":
            return match.end() - 1
    return match.end()


def _marker_separator(
    visible_text: str, match: re.Match[str], label_text: str
) -> tuple[int, bool, tuple[str, ...]] | None:
    """Locate the registered separator, tolerating surrounding decoration."""
    plain_cursor, had_whitespace = _skip_whitespace(visible_text, match.end())
    scan_cursor, opened = _skip_decoration(visible_text, match.end())
    repeated_separator = False

    if scan_cursor < len(visible_text) and visible_text[scan_cursor] in ":：=":
        cursor = scan_cursor
        first = visible_text[cursor]
        count = 0
        while cursor < len(visible_text) and visible_text[cursor] in ":：=":
            count += 1
            cursor += 1
        repeated_separator = count > 1 or (
            count == 1
            and cursor < len(visible_text)
            and visible_text[cursor] == first
        )
        return cursor, repeated_separator, opened

    if (
        visible_text[scan_cursor : scan_cursor + 2].casefold() == "is"
        and (
            scan_cursor + 2 == len(visible_text)
            or not visible_text[scan_cursor + 2].isalnum()
        )
        and label_text != "the answer is"
    ):
        cursor = scan_cursor + 2
        cursor, _ = _skip_whitespace(visible_text, cursor)
        if cursor < len(visible_text) and visible_text[cursor] in ":：=":
            count = 0
            while cursor < len(visible_text) and visible_text[cursor] in ":：=":
                count += 1
                cursor += 1
            repeated_separator = count > 1
        return cursor, repeated_separator, opened

    if had_whitespace:
        payload_cursor, payload_opened = _skip_decoration(
            visible_text, plain_cursor
        )
        if (
            payload_cursor == len(visible_text)
            or _NUMERIC_AT_PATTERN.match(visible_text, payload_cursor)
            or visible_text.startswith(r"\boxed", payload_cursor)
        ):
            return plain_cursor, False, payload_opened
    return None


def _scan_markers(
    output_text: str, visible_text: str
) -> tuple[_MarkerOccurrence, ...]:
    occurrences: list[_MarkerOccurrence] = []
    for match in _MARKER_LABEL_PATTERN.finditer(visible_text):
        label_text = re.sub(r"\s+", " ", match.group("label").casefold())
        family = "final" if label_text.startswith("final") else "answer"
        separator = _marker_separator(visible_text, match, label_text)
        if separator is None:
            continue
        cursor, repeated_separator, opened = separator
        cursor, payload_opened = _skip_decoration(visible_text, cursor)
        opened = opened + payload_opened

        wraps_box = visible_text.startswith(r"\boxed", cursor)
        candidate: _Candidate | None = None
        invalid_complete = False
        incomplete = cursor >= len(visible_text)
        if not incomplete and not wraps_box:
            numeric_match = _NUMERIC_AT_PATTERN.match(visible_text, cursor)
            if numeric_match is not None:
                numeric_end = _claim_numeric_end(visible_text, numeric_match)
                effective_family = (
                    "final"
                    if label_text == "the answer is" and repeated_separator
                    else family
                )
                candidate = _candidate(
                    output_text,
                    numeric_match.start(),
                    numeric_end,
                    (
                        "explicit_final_marker"
                        if effective_family == "final"
                        else "explicit_answer_marker"
                    ),
                    claim_start=match.start(),
                )
                if candidate is None or _claim_has_invalid_continuation(
                    visible_text, numeric_end, opened
                ):
                    candidate = None
                    invalid_complete = True
            else:
                payload = visible_text[cursor : cursor + 32].lstrip()
                if not payload or payload.startswith(("?", "...", "…")):
                    incomplete = True
                elif re.match(
                    r"(?:[+\-./0-9$]|NaN\b|Infinity\b)",
                    payload,
                    re.IGNORECASE | re.ASCII,
                ):
                    invalid_complete = True

        occurrences.append(
            _MarkerOccurrence(
                family=(
                    "final"
                    if label_text == "the answer is" and repeated_separator
                    else family
                ),
                label_key=label_text,
                marker_start=match.start(),
                payload_start=cursor,
                candidate=candidate,
                invalid_complete=invalid_complete,
                incomplete=incomplete,
                wraps_box=wraps_box,
                repeated_separator=repeated_separator,
            )
        )
    return tuple(occurrences)


def _last_substantive_line(text: str) -> tuple[int, str] | None:
    offset = 0
    result: tuple[int, str] | None = None
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if content.strip():
            result = (offset, content)
        offset += len(line)
    if offset < len(text):
        content = text[offset:]
        if content.strip():
            result = (offset, content)
    if result is None and text.strip():
        return (0, text)
    return result


def _equation_lhs_is_supported(line: str, equals_index: int) -> bool:
    boundary = max(
        line.rfind(";", 0, equals_index),
        line.rfind(",", 0, equals_index),
    )
    lhs = line[boundary + 1 : equals_index].strip()
    if not lhs:
        return False
    if re.search(r"[0-9+\-*/()[\]]", lhs, re.ASCII):
        return True
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,4}", lhs, re.ASCII))


def _terminal_suffix_is_harmless(
    line: str, candidates: list[_Candidate], line_start: int
) -> bool:
    if not candidates:
        return False
    end = candidates[-1].end - line_start
    return bool(_TERMINAL_SUFFIX_PATTERN.fullmatch(line[end:]))


def _scan_terminal_equations(
    output_text: str, visible_text: str
) -> _EquationScan:
    final_line = _last_substantive_line(visible_text)
    if final_line is None:
        return _EquationScan((), False, False)
    line_start, line = final_line
    candidates: list[_Candidate] = []
    invalid_complete = False
    incomplete = False
    for match in re.finditer(r"(?<![<>=])=(?!=)", line, re.ASCII):
        if not _equation_lhs_is_supported(line, match.start()):
            continue
        cursor, opened = _skip_decoration(line, match.end())
        if cursor >= len(line):
            incomplete = True
            continue
        numeric_match = _NUMERIC_AT_PATTERN.match(line, cursor)
        if numeric_match is None:
            payload = line[cursor : cursor + 24].lstrip()
            if payload.startswith(("?", "...", "…")):
                incomplete = True
            elif re.match(
                r"(?:[+\-./0-9$]|NaN\b|Infinity\b)",
                payload,
                re.IGNORECASE | re.ASCII,
            ):
                invalid_complete = True
            continue
        numeric_end = _claim_numeric_end(line, numeric_match)
        found = _candidate(
            output_text,
            line_start + numeric_match.start(),
            line_start + numeric_end,
            "terminal_equation",
            claim_start=line_start + match.start(),
        )
        if found is None or _claim_has_invalid_continuation(
            line, numeric_end, opened
        ):
            invalid_complete = True
        else:
            candidates.append(found)
    if candidates and not _terminal_suffix_is_harmless(
        line, candidates, line_start
    ):
        candidates = []
    return _EquationScan(
        candidates=tuple(candidates),
        invalid_complete=invalid_complete,
        incomplete=incomplete,
    )


def _scan_semantic_candidates(
    output_text: str, visible_text: str
) -> tuple[_Candidate, ...]:
    candidates: list[_Candidate] = []
    for match in _CONCLUSION_PATTERN.finditer(visible_text):
        numeric_match = _NUMERIC_AT_PATTERN.match(visible_text, match.end())
        if numeric_match is None:
            continue
        numeric_end = _claim_numeric_end(visible_text, numeric_match)
        found = _candidate(
            output_text,
            numeric_match.start(),
            numeric_end,
            "single_candidate",
            claim_start=match.start(),
        )
        if found is not None:
            candidates.append(found)
    if candidates:
        return tuple(candidates)

    token_matches = list(_NUMERIC_TOKEN_PATTERN.finditer(visible_text))
    valid: list[_Candidate] = []
    for match in token_matches:
        numeric_end = _claim_numeric_end(visible_text, match)
        found = _candidate(
            output_text,
            match.start(),
            numeric_end,
            "single_candidate",
        )
        if found is not None:
            valid.append(found)
    if not valid:
        return ()

    residual_parts: list[str] = []
    cursor = 0
    for candidate in valid:
        residual_parts.append(visible_text[cursor : candidate.start])
        cursor = candidate.end
    residual_parts.append(visible_text[cursor:])
    residual = "".join(residual_parts)
    if len(valid) > 1:
        residual = re.sub(
            r"(?<![A-Za-z0-9_])(?:or|and)(?![A-Za-z0-9_])",
            "",
            residual,
            flags=re.IGNORECASE | re.ASCII,
        )
        residual = residual.replace("|", "").replace("/", "")
    if _HARMLESS_RESIDUAL_PATTERN.fullmatch(residual):
        return tuple(valid)
    return ()


def _dedupe_candidates(
    candidates: tuple[_Candidate, ...] | list[_Candidate],
) -> list[_Candidate]:
    result: list[_Candidate] = []
    seen: set[tuple[int, int]] = set()
    for candidate in sorted(candidates, key=lambda item: (item.start, item.end)):
        key = (candidate.start, candidate.end)
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return result


def _apply_explicit_revision(
    candidates: list[_Candidate], visible_text: str
) -> tuple[list[_Candidate], bool]:
    revision_indexes: list[int] = []
    for index, candidate in enumerate(candidates):
        prefix = visible_text[max(0, candidate.claim_start - 40) : candidate.claim_start]
        if _CORRECTION_PATTERN.search(prefix):
            revision_indexes.append(index)
    if not revision_indexes:
        return candidates, False
    chosen = candidates[revision_indexes[-1] :]
    ignored_values = {
        item.normalized for item in candidates[: revision_indexes[-1]]
    }
    chosen_values = {item.normalized for item in chosen}
    return chosen, bool(ignored_values - chosen_values)


def _resolve_tier(
    candidates: list[_Candidate], present_strategy: str
) -> tuple[dict[str, Any], set[str]]:
    candidates = _dedupe_candidates(candidates)
    values: list[str] = []
    for candidate in candidates:
        if candidate.normalized not in values:
            values.append(candidate.normalized)
    warnings: set[str] = set()
    if len(values) == 1:
        spans: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates):
            spans.append(
                {
                    "start": candidate.start,
                    "end": candidate.end,
                    "text": candidate.text,
                    "kind": candidate.kind,
                    "normalized_answer": candidate.normalized,
                    "disposition": "selected" if index == 0 else "equivalent",
                }
            )
        if len(candidates) > 1:
            warnings.add("equivalent_repeated_claim")
        return (
            {
                "answer_presence": "present",
                "parse_valid": True,
                "parse_ambiguous": False,
                "parsed_answer": values[0],
                "candidate_answers": values,
                "evidence_spans": spans,
                "extraction_strategy": present_strategy,
                "failure_reasons": [],
            },
            warnings,
        )
    spans = [
        {
            "start": candidate.start,
            "end": candidate.end,
            "text": candidate.text,
            "kind": candidate.kind,
            "normalized_answer": candidate.normalized,
            "disposition": "ambiguous_candidate",
        }
        for candidate in candidates
    ]
    return (
        {
            "answer_presence": "uncertain",
            "parse_valid": True,
            "parse_ambiguous": True,
            "parsed_answer": None,
            "candidate_answers": values,
            "evidence_spans": spans,
            "extraction_strategy": "ambiguous_candidates",
            "failure_reasons": [],
        },
        warnings,
    )


def _ordered_warnings(warnings: set[str]) -> list[str]:
    return [warning for warning in _WARNING_ORDER if warning in warnings]


def _raw_numeric_matches(text: str) -> list[re.Match[str]]:
    return list(_NUMERIC_TOKEN_PATTERN.finditer(text))


def _has_unmatched_closing_brace(text: str) -> bool:
    depth = 0
    for character in text:
        if character == "{":
            depth += 1
        elif character == "}":
            if depth == 0:
                return True
            depth -= 1
    return False


def _looks_placeholder(text: str) -> bool:
    stripped = text.strip()
    return bool(
        stripped in {"...", "…", "N/A", "n/a"}
        or _PLACEHOLDER_PATTERN.search(stripped)
    )


def _looks_strongly_malformed(
    text: str, visible_text: str, think: _ThinkScan
) -> bool:
    return bool(
        think.malformed_open
        or think.stray
        or _STRONG_MALFORMED_PATTERN.search(text)
        or _has_unmatched_closing_brace(visible_text)
    )


def _base_absent_result(
    output_text: str,
    *,
    unsupported: bool,
    incomplete: bool,
    think: _ThinkScan,
) -> dict[str, Any]:
    if not output_text.strip():
        quality = "empty"
        failure = "empty_output"
    elif unsupported:
        quality = "malformed_unrecoverable"
        failure = "unsupported_numeric_literal"
    elif _looks_placeholder(output_text):
        quality = "placeholder"
        failure = "placeholder_without_answer"
    elif _looks_strongly_malformed(
        output_text, think.visible_text, think
    ) and not _TRUNCATION_CUE_PATTERN.search(output_text):
        quality = "malformed_unrecoverable"
        failure = "malformed_without_reliable_answer"
    elif (
        incomplete
        or think.unclosed
        or _TRUNCATION_CUE_PATTERN.search(output_text)
    ):
        quality = "truncated"
        failure = "truncated_before_final_answer"
    else:
        quality = "complete"
        failure = "no_reliable_answer"
    return {
        "answer_presence": "absent",
        "parse_valid": False,
        "parse_ambiguous": False,
        "parsed_answer": None,
        "candidate_answers": [],
        "evidence_spans": [],
        "extraction_strategy": "none",
        "output_quality": quality,
        "failure_reasons": [failure],
    }


def _has_reasoning_continuation(
    output_text: str, candidates: list[_Candidate]
) -> bool:
    if not candidates:
        return False
    suffix = output_text[max(candidate.end for candidate in candidates) :]
    return bool(_REASONING_CONTINUATION_PATTERN.search(suffix))


def _has_trailing_incidental_numeric(
    output_text: str,
    candidates: list[_Candidate],
    *,
    reasoning_continues: bool,
) -> bool:
    if not candidates:
        return False
    final_evidence_end = max(candidate.end for candidate in candidates)
    suffix = output_text[final_evidence_end:]
    has_number = bool(_NUMERIC_TOKEN_PATTERN.search(suffix))
    if not has_number:
        return False
    return bool(
        not reasoning_continues or _INCIDENTAL_SUFFIX_PATTERN.search(suffix)
    )


def _lower_tier_conflicts(
    selected: list[_Candidate], lower: list[_Candidate]
) -> bool:
    selected_values = {candidate.normalized for candidate in selected}
    return any(
        candidate.normalized not in selected_values for candidate in lower
    )


def _extract(output_text: str) -> dict[str, Any]:
    """Extract from output text alone; no reference channel exists here."""
    think = _scan_think_regions(output_text)
    visible_text = think.visible_text
    raw_numbers = _raw_numeric_matches(output_text)
    warnings: set[str] = set()
    if len(raw_numbers) > 1:
        warnings.add("multiple_numeric_mentions")
    if think.unbalanced:
        warnings.add("unbalanced_think_tag")
    if think.stray:
        warnings.add("stray_think_tag")

    boxes = _scan_boxes(output_text, visible_text)
    if boxes.incomplete:
        warnings.add("incomplete_box")
    markers = _scan_markers(output_text, visible_text)
    marker_labels = {item.label_key for item in markers}
    if any(item.repeated_separator for item in markers) or len(marker_labels) > 1:
        warnings.add("redundant_answer_marker")
    equations = _scan_terminal_equations(output_text, visible_text)
    semantic = list(_scan_semantic_candidates(output_text, visible_text))

    final_occurrences = [item for item in markers if item.family == "final"]
    answer_occurrences = [item for item in markers if item.family == "answer"]
    final_candidates = [
        item.candidate
        for item in final_occurrences
        if item.candidate is not None
    ]
    answer_candidates = [
        item.candidate
        for item in answer_occurrences
        if item.candidate is not None
    ]
    final_invalid = any(item.invalid_complete for item in final_occurrences)
    answer_invalid = any(item.invalid_complete for item in answer_occurrences)
    marker_incomplete = any(item.incomplete for item in markers)

    selected_candidates: list[_Candidate] = []
    lower_candidates: list[_Candidate] = []
    extraction: dict[str, Any] | None = None
    tier_warnings: set[str] = set()
    unsupported = False

    if boxes.candidates or boxes.invalid_complete:
        if boxes.invalid_complete:
            unsupported = True
        elif boxes.candidates:
            selected_candidates, revision_conflict = _apply_explicit_revision(
                _dedupe_candidates(boxes.candidates), visible_text
            )
            extraction, tier_warnings = _resolve_tier(
                selected_candidates, "boxed_answer"
            )
            lower_candidates = (
                final_candidates
                + answer_candidates
                + list(equations.candidates)
                + semantic
            )
            if revision_conflict:
                tier_warnings.add("lower_priority_conflict_ignored")
    elif final_candidates or final_invalid:
        if final_invalid:
            unsupported = True
        else:
            selected_candidates, revision_conflict = _apply_explicit_revision(
                _dedupe_candidates(final_candidates), visible_text
            )
            extraction, tier_warnings = _resolve_tier(
                selected_candidates, "explicit_final_marker"
            )
            lower_candidates = (
                answer_candidates + list(equations.candidates) + semantic
            )
            if revision_conflict:
                tier_warnings.add("lower_priority_conflict_ignored")
    elif answer_candidates or answer_invalid:
        if answer_invalid:
            unsupported = True
        else:
            selected_candidates, revision_conflict = _apply_explicit_revision(
                _dedupe_candidates(answer_candidates), visible_text
            )
            extraction, tier_warnings = _resolve_tier(
                selected_candidates, "explicit_answer_marker"
            )
            lower_candidates = list(equations.candidates) + semantic
            if revision_conflict:
                tier_warnings.add("lower_priority_conflict_ignored")
    elif equations.candidates or equations.invalid_complete:
        if equations.invalid_complete:
            unsupported = True
        else:
            selected_candidates = _dedupe_candidates(equations.candidates)
            extraction, tier_warnings = _resolve_tier(
                selected_candidates, "terminal_equation"
            )
            lower_candidates = semantic
    elif semantic:
        selected_candidates = _dedupe_candidates(semantic)
        extraction, tier_warnings = _resolve_tier(
            selected_candidates, "single_candidate"
        )

    warnings.update(tier_warnings)
    if extraction is not None:
        if (
            extraction["answer_presence"] == "present"
            and _lower_tier_conflicts(selected_candidates, lower_candidates)
        ):
            warnings.add("lower_priority_conflict_ignored")
        if any(
            candidate.text != candidate.normalized
            for candidate in selected_candidates
        ):
            warnings.add("noncanonical_numeric_surface")
        reasoning_continues = (
            extraction["answer_presence"] == "present"
            and _has_reasoning_continuation(output_text, selected_candidates)
        )
        if reasoning_continues:
            warnings.add("reasoning_continues_after_answer")
        if (
            extraction["answer_presence"] == "present"
            and _has_trailing_incidental_numeric(
                output_text,
                selected_candidates,
                reasoning_continues=reasoning_continues,
            )
        ):
            warnings.add("incidental_numeric_material")

        recoverable_malformed = bool(
            think.unbalanced
            or think.stray
            or any(item.repeated_separator for item in markers)
            or _has_unmatched_closing_brace(visible_text)
            or re.search(r"<\s*garbled\s*>", output_text, re.IGNORECASE)
        )
        if recoverable_malformed:
            quality = "malformed_recoverable"
        elif boxes.incomplete:
            quality = "truncated"
        else:
            quality = "complete"
        extraction["output_quality"] = quality
    else:
        extraction = _base_absent_result(
            output_text,
            unsupported=unsupported,
            incomplete=(
                boxes.incomplete
                or marker_incomplete
                or equations.incomplete
            ),
            think=think,
        )
        if raw_numbers and not unsupported:
            warnings.add("incidental_numeric_material")

    extraction["format_warnings"] = _ordered_warnings(warnings)
    return extraction


def parse_v3(request: Mapping[str, Any]) -> dict[str, Any]:
    """Parse one exact frozen request without reference or ambient-data access."""
    checked_request = validate_parser_request(request)
    output_text = checked_request["output_text"]
    result = {
        "schema_version": PARSER_RESULT_SCHEMA_VERSION,
        "parser_version": PARSER_VERSION,
        "answer_type": "numeric",
        "input_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        **_extract(output_text),
    }
    validate_parser_result(result, output_text)
    derive_typed_decision(result)
    return result


def compare_parsed_answer_to_reference(
    parser_output: Mapping[str, Any], reference_answer: str
) -> bool:
    """Compare only after extraction using exact bounded rational equality."""
    if not isinstance(parser_output, Mapping):
        raise TypeError("parser_output must be a mapping")
    canonical_reference = normalize_rational_literal(reference_answer)
    parsed_answer = parser_output.get("parsed_answer")
    if (
        parser_output.get("answer_presence") != "present"
        or parser_output.get("parse_valid") is not True
        or parser_output.get("parse_ambiguous") is not False
        or not isinstance(parsed_answer, str)
    ):
        return False
    try:
        canonical_parsed = normalize_rational_literal(parsed_answer)
    except ValidationSetError:
        return False
    return (
        canonical_parsed == parsed_answer
        and parsed_answer == canonical_reference
    )
