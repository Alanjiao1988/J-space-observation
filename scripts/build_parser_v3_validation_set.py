#!/usr/bin/env python3
"""Deterministic construction and manifest generation for the parser-v3 locked set.

Track D (Phase 1.2C) holdout curation tooling.

This script is *not* a parser. It never extracts an answer from text. It only:

1. reads curator-authored private case sources;
2. resolves curator-declared evidence spans from ``(literal, occurrence)`` pairs;
3. validates schema, vocabularies, stratum quotas and cross-cutting quotas;
4. canonicalises numeric surfaces with the frozen exact-rational rule;
5. runs the registered overlap checker against every reachable prior corpus;
6. measures span-boundary variation against the public parser-v2 development set;
7. emits the locked inputs, the reference-blind reviewer packet, the merged
   locked labels, and the inputs/labels/set manifests.

Secrecy split (see ``SECRECY`` below). The locked case inputs, the locked
labels and the three reviewer/arbiter row files are private holdout material
excluded from Git by rules the main agent owns in ``.gitignore``. The three
manifests under ``manifests/`` are public: they carry per-record fingerprints,
byte counts and SHA-256 digests but no case text and no label content, so the
set stays reviewable without being readable.

Usage:
    python scripts/build_parser_v3_validation_set.py --stage inputs
    python scripts/build_parser_v3_validation_set.py --stage labels
    python scripts/build_parser_v3_validation_set.py            # both stages
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import secrets
import unicodedata
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SET_ROOT = PROJECT_ROOT / "evaluator_sets" / "parser_v3_v1"
PRIVATE_ROOT = SET_ROOT / "private"
MANIFEST_ROOT = SET_ROOT / "manifests"

# Single source of truth for every artifact path this builder reads or writes,
# together with whether it is secret holdout material or a committable public
# artifact.  `.gitignore` is owned by the main agent and is never edited here;
# the private names below are the ones its rules already cover.
LOCKED_INPUTS_NAME = "locked_inputs.jsonl"
LOCKED_LABELS_NAME = "locked_labels.jsonl"
REVIEWER_A_NAME = "reviewer_a_locked_labels.jsonl"
REVIEWER_B_NAME = "reviewer_b_locked_labels.jsonl"
ARBITRATION_NAME = "arbitration_locked_labels.jsonl"
INPUTS_MANIFEST_NAME = "inputs_manifest.json"
LABELS_MANIFEST_NAME = "labels_manifest.json"
SET_MANIFEST_NAME = "set_manifest.json"

LOCKED_INPUTS_PATH = SET_ROOT / LOCKED_INPUTS_NAME
LOCKED_LABELS_PATH = SET_ROOT / LOCKED_LABELS_NAME
REVIEWER_A_PATH = SET_ROOT / REVIEWER_A_NAME
REVIEWER_B_PATH = SET_ROOT / REVIEWER_B_NAME
ARBITRATION_PATH = SET_ROOT / ARBITRATION_NAME
INPUTS_MANIFEST_PATH = MANIFEST_ROOT / INPUTS_MANIFEST_NAME
LABELS_MANIFEST_PATH = MANIFEST_ROOT / LABELS_MANIFEST_NAME
SET_MANIFEST_PATH = MANIFEST_ROOT / SET_MANIFEST_NAME

SECRECY = {
    LOCKED_INPUTS_NAME: "private",
    LOCKED_LABELS_NAME: "private",
    REVIEWER_A_NAME: "private",
    REVIEWER_B_NAME: "private",
    ARBITRATION_NAME: "private",
    f"manifests/{INPUTS_MANIFEST_NAME}": "public",
    f"manifests/{LABELS_MANIFEST_NAME}": "public",
    f"manifests/{SET_MANIFEST_NAME}": "public",
}

SET_ID = "parser-v3-v1"
CASE_ID_PREFIX = "PV3-"
CASE_ID_DOMAIN = b"jspace-parser-v3-validation/case-id/v1\x00"
LABEL_FINGERPRINT_DOMAIN = b"jspace-parser-v3-validation/label-fingerprint/v1\x00"

INPUT_SCHEMA = "phase1-parser-v3-locked-input/v1"
LABEL_SCHEMA = "phase1-parser-v3-locked-label/v1"
SOURCE_SCHEMA = "phase1-parser-v3-case-source/v1"
REVIEW_SCHEMA = "phase1-parser-v3-review/v1"
PACKET_SCHEMA = "phase1-parser-v3-review-packet/v1"
ARBITRATION_PACKET_SCHEMA = "phase1-parser-v3-arbitration-packet/v1"

STRATA = [f"S{index:02d}" for index in range(1, 13)]
CLEAN_STRATA = {"S01", "S02", "S03", "S12"}
NO_ANSWER_STRATA = {"S07", "S08", "S10"}
AMBIGUOUS_STRATA = {"S11"}
ANSWER_BEARING_STRATA = [s for s in STRATA if s not in NO_ANSWER_STRATA | AMBIGUOUS_STRATA]
CASES_PER_STRATUM = 10
TOTAL_CASES = 120

PRESENCE_VALUES = ("present", "ambiguous", "no_answer")
STRATEGY_VALUES = (
    "boxed_answer",
    "explicit_final_marker",
    "explicit_answer_marker",
    "terminal_equation",
    "single_candidate",
    "none",
    "ambiguous_candidates",
)
QUALITY_VALUES = (
    "empty",
    "placeholder",
    "malformed_unrecoverable",
    "malformed_recoverable",
    "truncated",
    "complete",
)
FAILURE_VALUES = (
    "empty_output",
    "placeholder_without_answer",
    "truncated_before_final_answer",
    "malformed_without_reliable_answer",
    "unsupported_numeric_literal",
    "no_reliable_answer",
)
WARNING_VALUES = (
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
SPAN_KIND_VALUES = (
    "boxed",
    "explicit_final_marker",
    "explicit_answer_marker",
    "terminal_equation",
    "single_candidate",
)
DISPOSITION_VALUES = ("selected", "equivalent", "ambiguous_candidate")

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

DECIMAL_RE = re.compile(
    r"^[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]+)?$"
)
FRACTION_RE = re.compile(r"^[+-]?[0-9]+/[0-9]+$")
NUMERIC_TOKEN_RE = re.compile(
    r"[+-]?(?:[0-9]+/[0-9]+"
    r"|(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]+)?)"
)

MAX_TOKEN_CHARS = 100
MAX_CANONICAL_CHARS = 4096
MAX_EXPONENT_MAGNITUDE = 8192
NEAR_DUPLICATE_THRESHOLD = 0.85
NGRAM = 5

PARSER_V2_DEVELOPMENT = (
    PROJECT_ROOT / "evaluator_sets" / "parser_v2_v1" / "development_cases.jsonl"
)
HISTORICAL_CORPORA = (
    PROJECT_ROOT / "artifacts" / "record_audit" / "ambiguous_records_for_review.jsonl",
)
HISTORICAL_TEXT_KEYS = (
    "output",
    "raw_output",
    "raw_output_before_postprocess",
    "raw_output_before_stop_cleanup",
    "stopped_output",
    "postprocessed_output",
    "eval_output_used",
)

BOUNDARY_STRATA = ("S01", "S02", "S05", "S06")


class BuildError(RuntimeError):
    """Raised when any registered construction invariant fails."""


# --------------------------------------------------------------------------- io


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")


def canonical_jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
            "ascii"
        )
        + b"\n"
        for row in rows
    )


def read_jsonl(path: Path, name: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise BuildError(f"{name} is missing: {path}")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise BuildError(f"{name} line {index} is not valid JSON: {error}") from error
        if not isinstance(row, dict):
            raise BuildError(f"{name} line {index} is not a JSON object")
        rows.append(row)
    return rows


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    if path.read_bytes() != payload:
        raise BuildError(f"local write verification failed: {path}")


# ------------------------------------------------------------------ numerics


def canonical_numeric(surface: str) -> str:
    """Exact reduced-rational canonical rendering of a registered numeric surface."""
    if not isinstance(surface, str) or not surface:
        raise BuildError("numeric surface must be a non-empty string")
    if len(surface) > MAX_TOKEN_CHARS:
        raise BuildError(f"numeric token exceeds {MAX_TOKEN_CHARS} characters")
    if FRACTION_RE.match(surface):
        sign = -1 if surface[0] == "-" else 1
        body = surface[1:] if surface[0] in "+-" else surface
        numerator_text, denominator_text = body.split("/", 1)
        denominator = int(denominator_text)
        if denominator == 0:
            raise BuildError("fraction denominator must not be zero")
        value = Fraction(sign * int(numerator_text), denominator)
    elif DECIMAL_RE.match(surface):
        body = surface
        sign = 1
        if body[0] in "+-":
            sign = -1 if body[0] == "-" else 1
            body = body[1:]
        exponent = 0
        if "e" in body or "E" in body:
            mantissa, exponent_text = re.split(r"[eE]", body, maxsplit=1)
            exponent = int(exponent_text)
            if abs(exponent) > MAX_EXPONENT_MAGNITUDE:
                raise BuildError("exponent magnitude exceeds the registered bound")
        else:
            mantissa = body
        if "." in mantissa:
            integer_text, fraction_text = mantissa.split(".", 1)
        else:
            integer_text, fraction_text = mantissa, ""
        digits = (integer_text or "0") + fraction_text
        scale = len(fraction_text)
        value = Fraction(int(digits or "0"), 10**scale)
        if exponent >= 0:
            value = value * Fraction(10**exponent, 1)
        else:
            value = value / Fraction(10 ** (-exponent), 1)
        value = value * sign
    else:
        raise BuildError(f"unsupported numeric surface: {surface!r}")
    if value == 0:
        return "0"
    rendered = (
        str(value.numerator)
        if value.denominator == 1
        else f"{value.numerator}/{value.denominator}"
    )
    if len(rendered) > MAX_CANONICAL_CHARS:
        raise BuildError("canonical rendering exceeds the registered bound")
    return rendered


def try_canonical_numeric(surface: str) -> str | None:
    try:
        return canonical_numeric(surface)
    except BuildError:
        return None


# ------------------------------------------------------------- normalisation

_PUNCTUATION_MAP = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u00a0": " ",
}


def normalize_text(text: str) -> str:
    """Registered normalisation: NFKC, LF, punctuation folding, whitespace, casefold."""
    value = unicodedata.normalize("NFKC", text)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    for source, target in _PUNCTUATION_MAP.items():
        value = value.replace(source, target)
    value = re.sub(r"\s+", " ", value).strip()
    return value.casefold()


def numeric_normalized_text(text: str) -> str:
    """Normalised text with every numeric surface replaced by its canonical value."""

    def replace(match: re.Match[str]) -> str:
        canonical = try_canonical_numeric(match.group(0))
        return canonical if canonical is not None else match.group(0)

    return NUMERIC_TOKEN_RE.sub(replace, normalize_text(text))


def masked_template_text(text: str) -> str:
    """Normalised text with every numeric surface masked, for near-duplicate screening."""
    return NUMERIC_TOKEN_RE.sub("<NUM>", normalize_text(text))


def fingerprints(text: str) -> dict[str, str]:
    return {
        "exact_sha256": sha256_bytes(text.encode("utf-8")),
        "normalized_sha256": sha256_bytes(normalize_text(text).encode("utf-8")),
        "numeric_normalized_sha256": sha256_bytes(
            numeric_normalized_text(text).encode("utf-8")
        ),
        "masked_template_sha256": sha256_bytes(masked_template_text(text).encode("utf-8")),
    }


def ngrams(value: str, size: int = NGRAM) -> set[str]:
    if len(value) < size:
        return {value} if value else set()
    return {value[index : index + size] for index in range(len(value) - size + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


# ------------------------------------------------------------------- salts


def load_or_create_salts() -> dict[str, str]:
    path = PRIVATE_ROOT / "salts.json"
    if path.is_file():
        salts = json.loads(path.read_text(encoding="utf-8"))
        for key in ("case_id_salt", "label_fingerprint_salt"):
            if not isinstance(salts.get(key), str) or len(salts[key]) < 32:
                raise BuildError(f"private salt {key} is malformed")
        return salts
    salts = {
        "schema_version": "phase1-parser-v3-private-salts/v1",
        "set_id": SET_ID,
        "case_id_salt": secrets.token_hex(32),
        "label_fingerprint_salt": secrets.token_hex(32),
    }
    write_bytes(path, canonical_json_bytes(salts))
    return salts


def case_id_for(output_text: str, parse_type: str, salt: str) -> str:
    digest = hashlib.sha256()
    digest.update(CASE_ID_DOMAIN)
    digest.update(bytes.fromhex(salt))
    digest.update(parse_type.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(output_text.encode("utf-8"))
    return CASE_ID_PREFIX + digest.hexdigest()[:20]


def label_fingerprint(payload: bytes, salt: str) -> str:
    return hmac.new(
        bytes.fromhex(salt), LABEL_FINGERPRINT_DOMAIN + payload, hashlib.sha256
    ).hexdigest()


# ------------------------------------------------------------------- spans


def resolve_occurrence(text: str, literal: str, occurrence: int) -> int:
    if occurrence < 1:
        raise BuildError("span occurrence index must be >= 1")
    start = -1
    for _ in range(occurrence):
        start = text.find(literal, start + 1)
        if start < 0:
            raise BuildError(
                f"span literal {literal!r} occurrence {occurrence} not found in output"
            )
    return start


def resolve_spans(
    text: str, declared: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for entry in declared:
        literal = entry["text"]
        occurrence = int(entry.get("occurrence", 1))
        kind = entry["kind"]
        disposition = entry["disposition"]
        if kind not in SPAN_KIND_VALUES:
            raise BuildError(f"unregistered span kind: {kind}")
        if disposition not in DISPOSITION_VALUES:
            raise BuildError(f"unregistered span disposition: {disposition}")
        start = resolve_occurrence(text, literal, occurrence)
        end = start + len(literal)
        if text[start:end] != literal:
            raise BuildError("resolved span text does not match the declared literal")
        resolved.append(
            {
                "disposition": disposition,
                "end": end,
                "kind": kind,
                "normalized_answer": span_normalized_answer(literal),
                "start": start,
                "text": literal,
            }
        )
    resolved.sort(key=lambda span: (span["start"], span["end"]))
    return resolved


def span_normalized_answer(literal: str) -> str | None:
    """Canonical value carried by an evidence span.

    Reviewers may quote a bare literal or the whole licensing construct, marker
    included.  The value of the span is the last legal numeric surface it
    contains; a span with no legal surface carries no value.
    """

    tokens = NUMERIC_TOKEN_RE.findall(literal)
    for token in reversed(tokens):
        try:
            return canonical_numeric(token)
        except BuildError:
            continue
    return None


def span_signature(span: Mapping[str, Any]) -> tuple[str, str, str | None]:
    return (span["kind"], span["disposition"], span["normalized_answer"])


def order_vocabulary(values: Iterable[str], vocabulary: Sequence[str]) -> list[str]:
    unique = set(values)
    unknown = unique - set(vocabulary)
    if unknown:
        raise BuildError(f"unregistered vocabulary entries: {sorted(unknown)}")
    return [item for item in vocabulary if item in unique]


def typed_decision(presence: str, parsed_answer: str | None) -> str:
    if presence == "present":
        if parsed_answer is None:
            return "present_unextractable"
        return f"present:{parsed_answer}"
    if presence == "ambiguous":
        return "ambiguous"
    return "no_answer"


# --------------------------------------------------------------- case sources


def load_case_sources(salt: str) -> list[dict[str, Any]]:
    rows = read_jsonl(PRIVATE_ROOT / "case_sources.jsonl", "case sources")
    if len(rows) != TOTAL_CASES:
        raise BuildError(f"expected {TOTAL_CASES} case sources, found {len(rows)}")
    cases: list[dict[str, Any]] = []
    for row in rows:
        if row.get("schema_version") != SOURCE_SCHEMA:
            raise BuildError("case source schema_version is not registered")
        if row.get("source_kind") != "constructed_model_free_fixture":
            raise BuildError("every case must be a constructed model-free fixture")
        if row.get("parse_type") != "numeric":
            raise BuildError("only the numeric parse type is registered")
        stratum = row["stratum"]
        if stratum not in STRATA:
            raise BuildError(f"unregistered stratum: {stratum}")
        text = row["output_text"]
        if not isinstance(text, str) or not text.strip():
            raise BuildError("output_text must be a non-empty, non-blank string")
        presence = row["expected_answer_presence"]
        if presence not in PRESENCE_VALUES:
            raise BuildError(f"unregistered answer presence: {presence}")
        spans = resolve_spans(text, row["expected_evidence_spans"])
        parsed = row["expected_parsed_answer"]
        strategy = row["expected_extraction_strategy"]
        quality = row["expected_output_quality"]
        if strategy not in STRATEGY_VALUES:
            raise BuildError(f"unregistered extraction strategy: {strategy}")
        if quality not in QUALITY_VALUES:
            raise BuildError(f"unregistered output quality: {quality}")
        failures = order_vocabulary(row["expected_failure_reasons"], FAILURE_VALUES)
        warnings = order_vocabulary(row["expected_format_warnings"], WARNING_VALUES)
        selected = [span for span in spans if span["disposition"] == "selected"]
        ambiguous_spans = [
            span for span in spans if span["disposition"] == "ambiguous_candidate"
        ]
        if presence == "present":
            if parsed is None or not selected:
                raise BuildError("a present case needs a parsed answer and a selected span")
            if canonical_numeric(parsed) != parsed:
                raise BuildError(f"parsed answer {parsed!r} is not canonical")
            for span in spans:
                if span["normalized_answer"] != parsed:
                    raise BuildError(
                        "every present-case span must carry the selected canonical value"
                    )
            candidates = []
            if row["expected_parse_valid"] is not True or row["expected_parse_ambiguous"]:
                raise BuildError("present cases must be valid and non-ambiguous")
        elif presence == "ambiguous":
            if parsed is not None or len(ambiguous_spans) < 2:
                raise BuildError("ambiguous cases need >= 2 candidate spans and no answer")
            candidates = []
            for span in ambiguous_spans:
                if span["normalized_answer"] not in candidates:
                    candidates.append(span["normalized_answer"])
            if len(candidates) < 2:
                raise BuildError("ambiguous cases need >= 2 distinct canonical candidates")
            if row["expected_parse_valid"] is not True or not row["expected_parse_ambiguous"]:
                raise BuildError("ambiguous cases must be valid and ambiguous")
        else:
            if parsed is not None or spans:
                raise BuildError("no-answer cases must carry no answer and no span")
            candidates = []
            if row["expected_parse_valid"] or row["expected_parse_ambiguous"]:
                raise BuildError("no-answer cases must be invalid and non-ambiguous")
            if not failures:
                raise BuildError("no-answer cases must register a failure reason")
        reference = row["registered_reference_answer"]
        canonical_reference = canonical_numeric(reference)
        computed_correctness = bool(
            presence == "present" and parsed is not None and parsed == canonical_reference
        )
        if bool(row["expected_correctness"]) != computed_correctness:
            raise BuildError(
                "registered correctness disagrees with the frozen correctness rule"
            )
        if computed_correctness and not row["material_error_if_missed"]:
            raise BuildError("a reference-correct case must be material if missed")
        case_id = case_id_for(text, "numeric", salt)
        cases.append(
            {
                "authoring_index": row["authoring_index"],
                "candidate_answers": candidates,
                "canonical_reference": canonical_reference,
                "case_id": case_id,
                "critical_case": bool(row["critical_case"]),
                "curation_notes": row["curation_notes"],
                "curator_id": row["curator_id"],
                "expected_correctness": computed_correctness,
                "failure_reasons": failures,
                "format_warnings": warnings,
                "material_error_if_missed": bool(row["material_error_if_missed"]),
                "output_quality": quality,
                "output_text": text,
                "parse_ambiguous": bool(row["expected_parse_ambiguous"]),
                "parse_valid": bool(row["expected_parse_valid"]),
                "parsed_answer": parsed,
                "presence": presence,
                "reference_answer": reference,
                "spans": spans,
                "strategy": strategy,
                "stratum": stratum,
                "subtype_slot": row["subtype_slot"],
            }
        )
    ids = [case["case_id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise BuildError("case identifiers are not unique")
    cases.sort(key=lambda case: case["case_id"])
    return cases


# ------------------------------------------------------------- composition


def validate_composition(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    per_stratum: dict[str, list[Mapping[str, Any]]] = {s: [] for s in STRATA}
    for case in cases:
        per_stratum[case["stratum"]].append(case)
    for stratum, rows in per_stratum.items():
        if len(rows) != CASES_PER_STRATUM:
            raise BuildError(f"{stratum} holds {len(rows)} cases, expected {CASES_PER_STRATUM}")
        slots = sorted({row["subtype_slot"] for row in rows})
        if len(slots) != 5:
            raise BuildError(f"{stratum} must exercise exactly five subtype slots")
        for slot in slots:
            count = sum(1 for row in rows if row["subtype_slot"] == slot)
            if count != 2:
                raise BuildError(f"{stratum} slot {slot} holds {count} cases, expected 2")
    presence_counts = {value: 0 for value in PRESENCE_VALUES}
    for case in cases:
        presence_counts[case["presence"]] += 1
    if presence_counts != {"present": 80, "ambiguous": 10, "no_answer": 30}:
        raise BuildError(f"registered support violated: {presence_counts}")
    for stratum in ANSWER_BEARING_STRATA:
        rows = per_stratum[stratum]
        correct = sum(1 for row in rows if row["expected_correctness"])
        if correct != 5:
            raise BuildError(f"{stratum} holds {correct} reference-correct cases, expected 5")
    for stratum in NO_ANSWER_STRATA:
        for row in per_stratum[stratum]:
            if row["presence"] != "no_answer":
                raise BuildError(f"{stratum} must be a no-answer stratum")
    for row in per_stratum["S11"]:
        if row["presence"] != "ambiguous":
            raise BuildError("S11 must be the only ambiguity-positive stratum")
    for stratum in STRATA:
        if stratum in NO_ANSWER_STRATA or stratum == "S11":
            continue
        for row in per_stratum[stratum]:
            if row["presence"] != "present":
                raise BuildError(f"{stratum} must be answer-bearing")
    for row in cases:
        expected_critical = row["stratum"] not in CLEAN_STRATA
        if row["critical_case"] != expected_critical:
            raise BuildError("critical-case flag disagrees with the registered strata split")

    features = feature_counts(cases)
    quotas = {
        "negative_answers": 10,
        "decimal_surfaces": 10,
        "fraction_surfaces": 10,
        "balanced_think_regions": 10,
        "malformed_think_regions": 10,
    }
    for name, minimum in quotas.items():
        if features[name] < minimum:
            raise BuildError(f"cross-cutting quota {name} = {features[name]} < {minimum}")
    for stratum in NO_ANSWER_STRATA:
        count = sum(
            1
            for row in per_stratum[stratum]
            if "incidental_numeric_material" in row["format_warnings"]
        )
        if count < 5:
            raise BuildError(f"{stratum} needs >= 5 incidental-distractor cases, has {count}")
    for stratum in ANSWER_BEARING_STRATA:
        if stratum == "S12":
            continue
        count = sum(
            1
            for row in per_stratum[stratum]
            if row["parsed_answer"] is not None
            and ("/" in row["parsed_answer"] or row["parsed_answer"].startswith("-"))
        )
        if count < 2:
            raise BuildError(f"{stratum} needs >= 2 signed or fractional answers")
    for row in per_stratum["S06"]:
        tail = row["output_text"][max(span["end"] for span in row["spans"]) :]
        tail_values = {
            canonical
            for token in NUMERIC_TOKEN_RE.findall(tail)
            if (canonical := try_canonical_numeric(token)) is not None
        }
        if not tail_values:
            raise BuildError("every S06 case needs a trailing numeric distractor")
        if row["parsed_answer"] in tail_values:
            raise BuildError("an S06 trailing distractor must differ from the answer")
    return {
        "per_stratum": {stratum: len(rows) for stratum, rows in per_stratum.items()},
        "presence": presence_counts,
        "reference_correct": sum(1 for case in cases if case["expected_correctness"]),
        "critical_cases": sum(1 for case in cases if case["critical_case"]),
        "material_if_missed": sum(1 for case in cases if case["material_error_if_missed"]),
        "features": features,
    }


def feature_counts(cases: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    negative = decimal = fraction = 0
    balanced_think = malformed_think = 0
    for case in cases:
        answer = case["parsed_answer"]
        if answer is not None and answer.startswith("-"):
            negative += 1
        surfaces = [span["text"] for span in case["spans"]]
        if any("." in surface or "e" in surface or "E" in surface for surface in surfaces):
            decimal += 1
        if any("/" in surface for surface in surfaces) or (
            answer is not None and "/" in answer
        ):
            fraction += 1
        text = case["output_text"]
        strict = re.findall(r"</?think>", text, flags=re.IGNORECASE)
        loose = re.findall(r"<[^>]*t\s*h\s*i\s*n\s*k[^>]*>", text, flags=re.IGNORECASE)
        opens = sum(1 for tag in strict if not tag.startswith("</"))
        closes = len(strict) - opens
        well_formed = (
            bool(strict)
            and opens == closes
            and len(loose) == len(strict)
            and _think_is_balanced(text)
        )
        if well_formed:
            balanced_think += 1
        elif strict or loose:
            malformed_think += 1
    return {
        "negative_answers": negative,
        "decimal_surfaces": decimal,
        "fraction_surfaces": fraction,
        "balanced_think_regions": balanced_think,
        "malformed_think_regions": malformed_think,
    }


def _think_is_balanced(text: str) -> bool:
    depth = 0
    for match in re.finditer(r"</?think>", text, flags=re.IGNORECASE):
        if match.group(0).startswith("</"):
            depth -= 1
        else:
            depth += 1
        if depth < 0 or depth > 1:
            return False
    return depth == 0


# ------------------------------------------------------------ span boundaries


def boundary_profile(text: str, spans: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    anchor = [span for span in spans if span["disposition"] == "selected"]
    if not anchor:
        anchor = [span for span in spans if span["disposition"] == "ambiguous_candidate"]
    if not anchor:
        return None
    span = anchor[0]
    start, end = span["start"], span["end"]
    before = text[max(0, start - 2) : start]
    after = text[end : end + 2]
    line_index = text.count("\n", 0, start)
    total_lines = text.count("\n") + 1
    if line_index == 0:
        line_class = "first"
    elif line_index == total_lines - 1:
        line_class = "last"
    else:
        line_class = "interior"
    return {
        "start": start,
        "tail_gap": len(text) - end,
        "length": len(text),
        "span_count": len(spans),
        "window": f"{before}|{after}",
        "line_class": line_class,
    }


def boundary_metrics(
    records: Sequence[tuple[str, Sequence[Mapping[str, Any]]]]
) -> dict[str, Any]:
    profiles = [
        profile
        for text, spans in records
        if (profile := boundary_profile(text, spans)) is not None
    ]
    if not profiles:
        return {"n": 0}
    starts = [profile["start"] for profile in profiles]
    tails = [profile["tail_gap"] for profile in profiles]
    lengths = [profile["length"] for profile in profiles]
    return {
        "n": len(profiles),
        "span_count_values": sorted({profile["span_count"] for profile in profiles}),
        "start_min": min(starts),
        "start_max": max(starts),
        "start_range": max(starts) - min(starts),
        "tail_gap_min": min(tails),
        "tail_gap_max": max(tails),
        "tail_gap_range": max(tails) - min(tails),
        "length_min": min(lengths),
        "length_max": max(lengths),
        "length_range": max(lengths) - min(lengths),
        "boundary_windows": sorted({profile["window"] for profile in profiles}),
        "line_classes": sorted({profile["line_class"] for profile in profiles}),
    }


def load_parser_v2_development() -> list[dict[str, Any]]:
    return read_jsonl(PARSER_V2_DEVELOPMENT, "parser-v2 development set")


def span_boundary_comparison(
    cases: Sequence[Mapping[str, Any]], v2_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for stratum in BOUNDARY_STRATA:
        v3_records = [
            (case["output_text"], case["spans"])
            for case in cases
            if case["stratum"] == stratum
        ]
        v2_records = [
            (row["output_text"], row["expected_evidence_spans"])
            for row in v2_rows
            if row.get("stratum") == stratum
        ]
        v3_metrics = boundary_metrics(v3_records)
        v2_metrics = boundary_metrics(v2_records)
        missing = sorted(
            set(v2_metrics["boundary_windows"]) - set(v3_metrics["boundary_windows"])
        )
        added = sorted(
            set(v3_metrics["boundary_windows"]) - set(v2_metrics["boundary_windows"])
        )
        checks = {
            "covers_v2_windows": not missing,
            "more_distinct_windows": len(v3_metrics["boundary_windows"])
            > len(v2_metrics["boundary_windows"]),
            "more_span_count_values": len(v3_metrics["span_count_values"])
            > len(v2_metrics["span_count_values"]),
            "wider_start_range": v3_metrics["start_range"] > v2_metrics["start_range"],
            "wider_tail_gap_range": v3_metrics["tail_gap_range"]
            > v2_metrics["tail_gap_range"],
            "wider_length_range": v3_metrics["length_range"] > v2_metrics["length_range"],
            "at_least_as_many_line_classes": len(v3_metrics["line_classes"])
            >= len(v2_metrics["line_classes"]),
        }
        report[stratum] = {
            "parser_v2_development": v2_metrics,
            "parser_v3_locked": v3_metrics,
            "windows_missing_from_v3": missing,
            "windows_added_by_v3": added,
            "checks": checks,
            "passed": all(checks.values()),
        }
    report["all_passed"] = all(report[stratum]["passed"] for stratum in BOUNDARY_STRATA)
    return report


# ------------------------------------------------------------------ overlap


def collect_prior_fingerprints() -> dict[str, Any]:
    exact: dict[str, str] = {}
    normalized: dict[str, str] = {}
    numeric: dict[str, str] = {}
    masked_texts: list[tuple[str, str]] = []
    sources: list[dict[str, Any]] = []

    v2_rows = load_parser_v2_development()
    for index, row in enumerate(v2_rows):
        text = row["output_text"]
        label = f"parser_v2_development[{index}]"
        exact.setdefault(fingerprints(text)["exact_sha256"], label)
        normalized.setdefault(fingerprints(text)["normalized_sha256"], label)
        numeric.setdefault(fingerprints(text)["numeric_normalized_sha256"], label)
        masked_texts.append((label, masked_template_text(text)))
    sources.append(
        {
            "source": "parser_v2_v1/development_cases.jsonl",
            "records": len(v2_rows),
            "sha256": sha256_bytes(PARSER_V2_DEVELOPMENT.read_bytes()),
            "readable": True,
        }
    )

    historical_texts = 0
    for path in HISTORICAL_CORPORA:
        if not path.is_file():
            sources.append(
                {
                    "source": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "records": 0,
                    "readable": False,
                    "note": "not present in this worktree",
                }
            )
            continue
        rows = read_jsonl(path, path.name)
        for index, row in enumerate(rows):
            source = row.get("source", {})
            for key in HISTORICAL_TEXT_KEYS:
                text = source.get(key)
                if not isinstance(text, str) or not text.strip():
                    continue
                historical_texts += 1
                label = f"historical[{index}].{key}"
                marks = fingerprints(text)
                exact.setdefault(marks["exact_sha256"], label)
                normalized.setdefault(marks["normalized_sha256"], label)
                numeric.setdefault(marks["numeric_normalized_sha256"], label)
                masked_texts.append((label, masked_template_text(text)))
        sources.append(
            {
                "source": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "records": len(rows),
                "sha256": sha256_bytes(path.read_bytes()),
                "readable": True,
            }
        )
    return {
        "exact": exact,
        "normalized": normalized,
        "numeric_normalized": numeric,
        "masked": masked_texts,
        "sources": sources,
        "historical_text_fields": historical_texts,
    }


def overlap_report(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    prior = collect_prior_fingerprints()
    exact_hits: list[dict[str, str]] = []
    normalized_hits: list[dict[str, str]] = []
    numeric_hits: list[dict[str, str]] = []
    internal_exact: list[str] = []
    internal_normalized: list[str] = []
    seen_exact: dict[str, str] = {}
    seen_normalized: dict[str, str] = {}

    for case in cases:
        marks = fingerprints(case["output_text"])
        if marks["exact_sha256"] in prior["exact"]:
            exact_hits.append(
                {"case_id": case["case_id"], "prior": prior["exact"][marks["exact_sha256"]]}
            )
        if marks["normalized_sha256"] in prior["normalized"]:
            normalized_hits.append(
                {
                    "case_id": case["case_id"],
                    "prior": prior["normalized"][marks["normalized_sha256"]],
                }
            )
        if marks["numeric_normalized_sha256"] in prior["numeric_normalized"]:
            numeric_hits.append(
                {
                    "case_id": case["case_id"],
                    "prior": prior["numeric_normalized"][
                        marks["numeric_normalized_sha256"]
                    ],
                }
            )
        if marks["exact_sha256"] in seen_exact:
            internal_exact.append(case["case_id"])
        seen_exact[marks["exact_sha256"]] = case["case_id"]
        if marks["normalized_sha256"] in seen_normalized:
            internal_normalized.append(case["case_id"])
        seen_normalized[marks["normalized_sha256"]] = case["case_id"]

    case_masked = [
        (case["case_id"], ngrams(masked_template_text(case["output_text"])))
        for case in cases
    ]
    prior_masked = [(label, ngrams(text)) for label, text in prior["masked"]]
    near_prior: list[dict[str, Any]] = []
    max_prior = 0.0
    for case_id, case_grams in case_masked:
        for label, prior_grams in prior_masked:
            score = jaccard(case_grams, prior_grams)
            max_prior = max(max_prior, score)
            if score >= NEAR_DUPLICATE_THRESHOLD:
                near_prior.append(
                    {"case_id": case_id, "prior": label, "similarity": round(score, 4)}
                )
    near_internal: list[dict[str, Any]] = []
    max_internal = 0.0
    for left in range(len(case_masked)):
        for right in range(left + 1, len(case_masked)):
            score = jaccard(case_masked[left][1], case_masked[right][1])
            max_internal = max(max_internal, score)
            if score >= NEAR_DUPLICATE_THRESHOLD:
                near_internal.append(
                    {
                        "case_id_a": case_masked[left][0],
                        "case_id_b": case_masked[right][0],
                        "similarity": round(score, 4),
                    }
                )
    report = {
        "checked_sources": prior["sources"],
        "historical_text_fields": prior["historical_text_fields"],
        "hard_exact_overlap": len(exact_hits),
        "hard_exact_overlap_detail": exact_hits,
        "normalized_overlap": len(normalized_hits),
        "normalized_overlap_detail": normalized_hits,
        "numeric_normalized_overlap": len(numeric_hits),
        "numeric_normalized_overlap_detail": numeric_hits,
        "internal_exact_duplicates": len(internal_exact),
        "internal_normalized_duplicates": len(internal_normalized),
        "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
        "near_duplicates_vs_prior": near_prior,
        "near_duplicates_internal": near_internal,
        "max_similarity_vs_prior": round(max_prior, 4),
        "max_similarity_internal": round(max_internal, 4),
        "unreachable_corpora": [
            {
                "corpus": "parser-v2-v1 retired locked holdout",
                "reason": "sealed in private Blob storage; not readable from this worktree",
                "mitigation": (
                    "per-record exact, normalized, numeric-normalized and masked-template "
                    "fingerprints are published in the input manifest so the main agent can "
                    "run the cross-check against the sealed set"
                ),
            },
            {
                "corpus": "phase-1 historical generation and evaluation records (full 45)",
                "reason": "phase1_generations.jsonl / phase1_eval_records.jsonl are not present locally",
                "mitigation": "the reachable 18-record audit extract was fingerprinted instead",
            },
        ],
    }
    report["hard_failure_count"] = (
        report["hard_exact_overlap"]
        + report["normalized_overlap"]
        + report["internal_exact_duplicates"]
        + report["internal_normalized_duplicates"]
        + len(near_prior)
        + len(near_internal)
    )
    return report


def require_zero_overlap(report: Mapping[str, Any]) -> None:
    if report["hard_exact_overlap"]:
        raise BuildError("hard exact overlap with a prior corpus is not permitted")
    if report["normalized_overlap"]:
        raise BuildError("normalized overlap with a prior corpus is not permitted")
    if report["internal_exact_duplicates"] or report["internal_normalized_duplicates"]:
        raise BuildError("duplicate cases inside the locked set are not permitted")
    if report["near_duplicates_vs_prior"] or report["near_duplicates_internal"]:
        raise BuildError("near-duplicate cases at or above the threshold are not permitted")


# --------------------------------------------------------------- stage: inputs


def build_inputs(cases: Sequence[Mapping[str, Any]]) -> bytes:
    rows = [
        {
            "case_id": case["case_id"],
            "output_text": case["output_text"],
            "parse_type": "numeric",
            "schema_version": INPUT_SCHEMA,
            "set_id": SET_ID,
            "source_kind": "constructed_model_free_fixture",
        }
        for case in cases
    ]
    return canonical_jsonl_bytes(rows)


def build_review_packet(cases: Sequence[Mapping[str, Any]]) -> bytes:
    rows = [
        {
            "case_id": case["case_id"],
            "output_text": case["output_text"],
            "parse_type": "numeric",
            "schema_version": PACKET_SCHEMA,
        }
        for case in cases
    ]
    return canonical_jsonl_bytes(rows)


# --------------------------------------------------------------- stage: labels


def normalize_review_row(
    row: Mapping[str, Any], case: Mapping[str, Any]
) -> dict[str, Any]:
    if row.get("schema_version") not in (REVIEW_SCHEMA, None):
        raise BuildError("review row schema_version is not registered")
    presence = row["answer_presence"]
    if presence not in PRESENCE_VALUES:
        raise BuildError(f"unregistered reviewer presence value: {presence}")
    strategy = row["extraction_strategy"]
    if strategy not in STRATEGY_VALUES:
        raise BuildError(f"unregistered reviewer strategy: {strategy}")
    quality = row["output_quality"]
    if quality not in QUALITY_VALUES:
        raise BuildError(f"unregistered reviewer quality: {quality}")
    spans = resolve_spans(case["output_text"], row.get("evidence_spans", []))
    parsed = row.get("parsed_answer")
    if parsed is not None:
        parsed = canonical_numeric(str(parsed))
    candidates = [canonical_numeric(str(value)) for value in row.get("candidate_answers", [])]
    ordered_candidates: list[str] = []
    for value in candidates:
        if value not in ordered_candidates:
            ordered_candidates.append(value)
    return {
        "answer_presence": presence,
        "parse_valid": bool(row["parse_valid"]),
        "parse_ambiguous": bool(row["parse_ambiguous"]),
        "parsed_answer": parsed,
        "candidate_answers": ordered_candidates,
        "evidence_spans": spans,
        "extraction_strategy": strategy,
        "output_quality": quality,
        "failure_reasons": order_vocabulary(row.get("failure_reasons", []), FAILURE_VALUES),
        "format_warnings": order_vocabulary(row.get("format_warnings", []), WARNING_VALUES),
    }


def load_review(path: Path, name: str, cases: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path, name)
    if len(rows) != TOTAL_CASES:
        raise BuildError(f"{name} holds {len(rows)} rows, expected {TOTAL_CASES}")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = row["case_id"]
        if case_id not in cases:
            raise BuildError(f"{name} references unknown case {case_id}")
        if case_id in result:
            raise BuildError(f"{name} repeats case {case_id}")
        result[case_id] = normalize_review_row(row, cases[case_id])
    return result


def selected_span_key(judgement: Mapping[str, Any]) -> list[tuple[int, int]]:
    return sorted(
        (span["start"], span["end"])
        for span in judgement["evidence_spans"]
        if span["disposition"] == "selected"
    )


def field_agreement(
    reviewer_a: Mapping[str, Mapping[str, Any]],
    reviewer_b: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    case_ids = sorted(reviewer_a)
    stats: dict[str, Any] = {}
    disagreements: list[str] = []
    for case_id in case_ids:
        left, right = reviewer_a[case_id], reviewer_b[case_id]
        if any(left[field] != right[field] for field in EXTRACTION_FIELDS):
            disagreements.append(case_id)
    for field in EXTRACTION_FIELDS:
        exact = sum(
            1 for case_id in case_ids if reviewer_a[case_id][field] == reviewer_b[case_id][field]
        )
        stats[field] = {"exact": exact, "n": len(case_ids)}
    for field in ("candidate_answers", "failure_reasons", "format_warnings"):
        scores = [
            jaccard(set(reviewer_a[case_id][field]), set(reviewer_b[case_id][field]))
            for case_id in case_ids
        ]
        stats[field]["mean_jaccard"] = round(sum(scores) / len(scores), 4)
    span_scores = []
    span_exact = 0
    for case_id in case_ids:
        left = set(selected_span_key(reviewer_a[case_id]))
        right = set(selected_span_key(reviewer_b[case_id]))
        if left == right:
            span_exact += 1
        span_scores.append(jaccard({str(x) for x in left}, {str(x) for x in right}))
    stats["selected_spans"] = {
        "exact": span_exact,
        "n": len(case_ids),
        "mean_jaccard": round(sum(span_scores) / len(span_scores), 4),
    }
    value_exact = 0
    for case_id in case_ids:
        left = {
            span["normalized_answer"]
            for span in reviewer_a[case_id]["evidence_spans"]
            if span["disposition"] == "selected"
        }
        right = {
            span["normalized_answer"]
            for span in reviewer_b[case_id]["evidence_spans"]
            if span["disposition"] == "selected"
        }
        if left == right:
            value_exact += 1
    stats["selected_span_values"] = {"exact": value_exact, "n": len(case_ids)}
    stats["output_quality"]["cohen_kappa"] = round(
        cohen_kappa(
            [reviewer_a[case_id]["output_quality"] for case_id in case_ids],
            [reviewer_b[case_id]["output_quality"] for case_id in case_ids],
        ),
        4,
    )
    stats["answer_presence"]["cohen_kappa"] = round(
        cohen_kappa(
            [reviewer_a[case_id]["answer_presence"] for case_id in case_ids],
            [reviewer_b[case_id]["answer_presence"] for case_id in case_ids],
        ),
        4,
    )
    return {
        "fields": stats,
        "row_exact_agreement": len(case_ids) - len(disagreements),
        "row_disagreements": len(disagreements),
        "disagreement_case_ids": disagreements,
        "n": len(case_ids),
    }


def cohen_kappa(left: Sequence[str], right: Sequence[str]) -> float:
    total = len(left)
    if total == 0:
        return 0.0
    observed = sum(1 for a, b in zip(left, right) if a == b) / total
    categories = set(left) | set(right)
    expected = sum(
        (left.count(category) / total) * (right.count(category) / total)
        for category in categories
    )
    if expected >= 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def merge_labels(
    cases: Sequence[Mapping[str, Any]],
    reviewer_a: Mapping[str, Mapping[str, Any]],
    reviewer_b: Mapping[str, Mapping[str, Any]],
    arbitration: Mapping[str, Mapping[str, Any]],
    disagreements: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    unresolved: list[str] = []
    intent_matches = 0
    intent_matches_excluding_spans = 0
    intent_presence_matches = 0
    intent_field_matches: dict[str, int] = {field: 0 for field in EXTRACTION_FIELDS}
    rows: list[dict[str, Any]] = []
    disagreement_set = set(disagreements)
    if set(arbitration) != disagreement_set:
        raise BuildError(
            "arbitration membership must equal the reviewer disagreement set exactly"
        )
    for case in cases:
        case_id = case["case_id"]
        if case_id in disagreement_set:
            judgement = arbitration[case_id]
            source = "arbitrated"
        else:
            judgement = reviewer_a[case_id]
            source = "consensus"
        if any(judgement[field] is None for field in ("answer_presence",)):
            unresolved.append(case_id)
        presence = judgement["answer_presence"]
        parsed = judgement["parsed_answer"]
        correctness = bool(
            presence == "present"
            and parsed is not None
            and parsed == case["canonical_reference"]
        )
        intent_core = (
            case["presence"] == presence
            and case["parsed_answer"] == parsed
            and case["strategy"] == judgement["extraction_strategy"]
            and case["output_quality"] == judgement["output_quality"]
            and case["failure_reasons"] == judgement["failure_reasons"]
            and case["format_warnings"] == judgement["format_warnings"]
            and case["candidate_answers"] == judgement["candidate_answers"]
        )
        intent = intent_core and (
            [span_signature(span) for span in case["spans"]]
            == [span_signature(span) for span in judgement["evidence_spans"]]
        )
        if intent:
            intent_matches += 1
        if intent_core:
            intent_matches_excluding_spans += 1
        if case["presence"] == presence and case["parsed_answer"] == parsed:
            intent_presence_matches += 1
        registered_view = {
            "answer_presence": case["presence"],
            "parse_valid": case["parse_valid"],
            "parse_ambiguous": case["parse_ambiguous"],
            "parsed_answer": case["parsed_answer"],
            "candidate_answers": case["candidate_answers"],
            "evidence_spans": [span_signature(span) for span in case["spans"]],
            "extraction_strategy": case["strategy"],
            "output_quality": case["output_quality"],
            "failure_reasons": case["failure_reasons"],
            "format_warnings": case["format_warnings"],
        }
        for field in EXTRACTION_FIELDS:
            observed = judgement[field]
            if field == "evidence_spans":
                observed = [span_signature(span) for span in observed]
            if registered_view[field] == observed:
                intent_field_matches[field] += 1
        rows.append(
            {
                "case_id": case_id,
                "critical_case": case["critical_case"],
                "curation_notes": case["curation_notes"],
                "expected_answer_presence": presence,
                "expected_candidate_answers": judgement["candidate_answers"],
                "expected_correctness": correctness,
                "expected_evidence_spans": judgement["evidence_spans"],
                "expected_extraction_strategy": judgement["extraction_strategy"],
                "expected_failure_reasons": judgement["failure_reasons"],
                "expected_format_warnings": judgement["format_warnings"],
                "expected_output_quality": judgement["output_quality"],
                "expected_parse_ambiguous": judgement["parse_ambiguous"],
                "expected_parse_valid": judgement["parse_valid"],
                "expected_parsed_answer": parsed,
                "label_source": source,
                "material_error_if_missed": case["material_error_if_missed"],
                "registered_reference_answer": case["reference_answer"],
                "schema_version": LABEL_SCHEMA,
                "set_id": SET_ID,
                "stratum": case["stratum"],
                "subtype_slot": case["subtype_slot"],
                "typed_decision": typed_decision(presence, parsed),
            }
        )
    summary = {
        "unresolved": len(unresolved),
        "unresolved_case_ids": unresolved,
        "arbitrated_rows": len(disagreement_set),
        "consensus_rows": TOTAL_CASES - len(disagreement_set),
        "construction_intent_exact": intent_matches,
        "construction_intent_exact_excluding_spans": intent_matches_excluding_spans,
        "construction_intent_presence_and_answer": intent_presence_matches,
        "construction_intent_by_field": intent_field_matches,
        "final_labels": len(rows),
        "presence_counts": {
            value: sum(1 for row in rows if row["expected_answer_presence"] == value)
            for value in PRESENCE_VALUES
        },
        "typed_decision_distinct_values": len({row["typed_decision"] for row in rows}),
        "reference_correct_labels": sum(1 for row in rows if row["expected_correctness"]),
    }
    return rows, summary


# ----------------------------------------------------------------- manifests


def build_input_manifest(
    cases: Sequence[Mapping[str, Any]], payload: bytes
) -> dict[str, Any]:
    return {
        "schema_version": "phase1-parser-v3-input-manifest/v1",
        "set_id": SET_ID,
        "record_count": len(cases),
        "file": {
            "path": f"evaluator_sets/parser_v3_v1/{LOCKED_INPUTS_NAME}",
            "secrecy": "private",
            "committed_to_git": False,
            "sha256": sha256_bytes(payload),
            "bytes": len(payload),
        },
        "fingerprint_scheme": {
            "exact_sha256": "SHA-256 over the exact UTF-8 output_text bytes",
            "normalized_sha256": (
                "SHA-256 over NFKC + LF + punctuation-folded + whitespace-collapsed + "
                "casefolded output_text"
            ),
            "numeric_normalized_sha256": (
                "normalized text with every registered numeric surface replaced by its "
                "exact reduced-rational canonical rendering"
            ),
            "masked_template_sha256": (
                "normalized text with every registered numeric surface replaced by <NUM>"
            ),
        },
        "records": [
            {
                "case_id": case["case_id"],
                "output_text_chars": len(case["output_text"]),
                "output_text_bytes": len(case["output_text"].encode("utf-8")),
                **fingerprints(case["output_text"]),
            }
            for case in cases
        ],
    }


def build_label_manifest(
    rows: Sequence[Mapping[str, Any]], payload: bytes, salt: str
) -> dict[str, Any]:
    return {
        "schema_version": "phase1-parser-v3-label-manifest/v1",
        "set_id": SET_ID,
        "record_count": len(rows),
        "file": {
            "path": f"evaluator_sets/parser_v3_v1/{LOCKED_LABELS_NAME}",
            "secrecy": "private",
            "committed_to_git": False,
            "sha256": sha256_bytes(payload),
            "bytes": len(payload),
        },
        "fingerprint_scheme": (
            "HMAC-SHA256 keyed with the private label salt over the canonical label JSON; "
            "salted so that per-record label hashes cannot be brute-forced from the inputs"
        ),
        "records": [
            {
                "case_id": row["case_id"],
                "label_bytes": len(canonical_json_bytes(row)) - 1,
                "label_fingerprint": label_fingerprint(canonical_json_bytes(row), salt),
            }
            for row in rows
        ],
    }


def build_overall_manifest(payloads: Mapping[str, bytes], report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase1-parser-v3-set-manifest/v1",
        "set_id": SET_ID,
        "written_last": True,
        "files": [
            {
                "leaf": leaf,
                "path": path,
                "secrecy": SECRECY[path],
                "committed_to_git": SECRECY[path] == "public",
                "sha256": sha256_bytes(payload),
                "bytes": len(payload),
            }
            for leaf, path, payload in sorted(
                (
                    ("locked-inputs", LOCKED_INPUTS_NAME, payloads["inputs"]),
                    ("locked-labels", LOCKED_LABELS_NAME, payloads.get("labels", b"")),
                    (
                        "manifests",
                        f"manifests/{INPUTS_MANIFEST_NAME}",
                        payloads["input_manifest"],
                    ),
                    (
                        "manifests",
                        f"manifests/{LABELS_MANIFEST_NAME}",
                        payloads.get("label_manifest", b""),
                    ),
                )
            )
            if payload
        ],
        "report": dict(report),
    }


# ---------------------------------------------------------------------- main


def build_arbitration_packet(
    cases: Mapping[str, Mapping[str, Any]],
    reviewer_a: Mapping[str, Mapping[str, Any]],
    reviewer_b: Mapping[str, Mapping[str, Any]],
    disagreements: Sequence[str],
) -> bytes:
    """Arbiter packet.

    Contains only the rows on which the two reviewers disagreed, the fields that
    actually differ, and the two competing judgements.  Reviewer identities are
    replaced by neutral labels so the arbiter cannot systematically favour one
    reviewer, and no reference answer, stratum or parser prediction is included.
    """

    rows = []
    for case_id in disagreements:
        left, right = reviewer_a[case_id], reviewer_b[case_id]
        differing = [field for field in EXTRACTION_FIELDS if left[field] != right[field]]
        rows.append(
            {
                "case_id": case_id,
                "differing_fields": differing,
                "judgement_1": {field: left[field] for field in EXTRACTION_FIELDS},
                "judgement_2": {field: right[field] for field in EXTRACTION_FIELDS},
                "output_text": cases[case_id]["output_text"],
                "parse_type": "numeric",
                "schema_version": ARBITRATION_PACKET_SCHEMA,
            }
        )
    return canonical_jsonl_bytes(rows)


def run(stage: str) -> int:
    salts = load_or_create_salts()
    cases = load_case_sources(salts["case_id_salt"])
    composition = validate_composition(cases)
    overlap = overlap_report(cases)
    require_zero_overlap(overlap)
    boundary = span_boundary_comparison(cases, load_parser_v2_development())
    if not boundary["all_passed"]:
        raise BuildError("span-boundary variation gate failed for a registered stratum")

    input_bytes = build_inputs(cases)
    packet_bytes = build_review_packet(cases)
    write_bytes(LOCKED_INPUTS_PATH, input_bytes)
    write_bytes(PRIVATE_ROOT / "reviewer_packet.jsonl", packet_bytes)
    input_manifest = build_input_manifest(cases, input_bytes)
    input_manifest_bytes = canonical_json_bytes(input_manifest)
    write_bytes(INPUTS_MANIFEST_PATH, input_manifest_bytes)

    payloads: dict[str, bytes] = {
        "inputs": input_bytes,
        "input_manifest": input_manifest_bytes,
    }
    report: dict[str, Any] = {
        "composition": composition,
        "overlap": overlap,
        "span_boundary_variation": boundary,
        "labels_present": False,
    }

    if stage in ("labels", "all"):
        by_id = {case["case_id"]: case for case in cases}
        reviewer_a_path = REVIEWER_A_PATH
        reviewer_b_path = REVIEWER_B_PATH
        arbitration_path = ARBITRATION_PATH
        if not (reviewer_a_path.is_file() and reviewer_b_path.is_file()):
            print(
                "inputs and reviewer packet written; reviewer rows are not present yet",
            )
            write_bytes(
                SET_MANIFEST_PATH,
                canonical_json_bytes(build_overall_manifest(payloads, report)),
            )
            return 3
        reviewer_a = load_review(reviewer_a_path, "reviewer A", by_id)
        reviewer_b = load_review(reviewer_b_path, "reviewer B", by_id)
        agreement = field_agreement(reviewer_a, reviewer_b)
        write_bytes(
            PRIVATE_ROOT / "agreement_report.json",
            canonical_json_bytes(agreement),
        )
        write_bytes(
            PRIVATE_ROOT / "arbitration_packet.jsonl",
            build_arbitration_packet(
                by_id, reviewer_a, reviewer_b, agreement["disagreement_case_ids"]
            ),
        )
        arbitration_rows = (
            read_jsonl(arbitration_path, "arbitration") if arbitration_path.is_file() else []
        )
        arbitration = {}
        for row in arbitration_rows:
            case_id = row["case_id"]
            if case_id not in by_id:
                raise BuildError(f"arbitration references unknown case {case_id}")
            arbitration[case_id] = normalize_review_row(row, by_id[case_id])
        label_rows, label_summary = merge_labels(
            cases, reviewer_a, reviewer_b, arbitration, agreement["disagreement_case_ids"]
        )
        if label_summary["unresolved"]:
            raise BuildError("unresolved labels are not permitted")
        label_bytes = canonical_jsonl_bytes(label_rows)
        write_bytes(LOCKED_LABELS_PATH, label_bytes)
        label_manifest = build_label_manifest(
            label_rows, label_bytes, salts["label_fingerprint_salt"]
        )
        label_manifest_bytes = canonical_json_bytes(label_manifest)
        write_bytes(LABELS_MANIFEST_PATH, label_manifest_bytes)
        payloads["labels"] = label_bytes
        payloads["label_manifest"] = label_manifest_bytes
        report["labels_present"] = True
        report["agreement"] = agreement
        report["labeling"] = label_summary

    overall = build_overall_manifest(payloads, report)
    write_bytes(SET_MANIFEST_PATH, canonical_json_bytes(overall))
    print(
        "parser-v3 locked set: cases={cases} strata={strata} exact_overlap={exact} "
        "normalized_overlap={norm} labels={labels}".format(
            cases=len(cases),
            strata=len(STRATA),
            exact=overlap["hard_exact_overlap"],
            norm=overlap["normalized_overlap"],
            labels=report["labels_present"],
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("inputs", "labels", "all"), default="all")
    args = parser.parse_args(argv)
    try:
        return run(args.stage)
    except BuildError as error:
        print(f"parser-v3 locked-set build failed: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
