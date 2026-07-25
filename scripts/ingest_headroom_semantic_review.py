#!/usr/bin/env python3
"""Validate structured semantic-review output and emit calibration judgments.

The registered reviewer form for Phase 1.0C Track B has exactly nine fields:

    record_id, semantic_answer, semantic_correct, output_complete, truncated,
    no_answer, ambiguity, confidence, notes

This tool validates that form strictly, then converts it into the judgment
records that ``headroom_calibration.load_judgments`` consumes.  The conversion
is a total, deterministic mapping and adds no judgement of its own:

    semantic_correct is true   -> semantic_label "correct"
    semantic_correct is false  -> semantic_label "incorrect"
    semantic_correct is null   -> semantic_label "unresolved"

Nothing here relabels a row, fills a missing review, or infers an answer the
reviewer did not state.  A row that is absent from the reviewer file stays
unreviewed, and any cell containing it cannot be selected.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


REVIEW_FIELDS: tuple[str, ...] = (
    "record_id",
    "semantic_answer",
    "semantic_correct",
    "output_complete",
    "truncated",
    "no_answer",
    "ambiguity",
    "confidence",
    "notes",
)
AMBIGUITY_VALUES: tuple[str, ...] = ("none", "minor", "major")
CONFIDENCE_VALUES: tuple[str, ...] = ("low", "medium", "high")
BOOLEAN_FIELDS: tuple[str, ...] = ("output_complete", "truncated", "no_answer")
LABEL_BY_CORRECTNESS = {True: "correct", False: "incorrect", None: "unresolved"}
SCHEMA_VERSION = "phase1-headroom-calibration-review-form/v1"


class ReviewIngestError(ValueError):
    """Raised when reviewer output cannot be trusted as-is."""


def review_form_schema() -> dict[str, Any]:
    """Machine-readable contract handed to the reviewer."""

    return {
        "ambiguity_values": list(AMBIGUITY_VALUES),
        "confidence_values": list(CONFIDENCE_VALUES),
        "fields": list(REVIEW_FIELDS),
        "label_mapping": {
            "false": "incorrect",
            "null": "unresolved",
            "true": "correct",
        },
        "notes": (
            "One JSON object per reviewed row, exactly these nine fields. "
            "semantic_correct may be null when the row cannot be decided; do "
            "not guess. This form judges only whether the emitted output "
            "states the registered answer and licenses no claim about hidden "
            "reasoning or internal representations."
        ),
        "schema_version": SCHEMA_VERSION,
    }


def _require_bool(row: Mapping[str, Any], field: str, line: int) -> bool:
    value = row[field]
    if not isinstance(value, bool):
        raise ReviewIngestError(f"line {line}: {field} must be true or false")
    return value


def validate_review_row(row: Any, line: int) -> dict[str, Any]:
    """Validate one reviewer row against the registered nine-field form."""

    if not isinstance(row, dict):
        raise ReviewIngestError(f"line {line}: review row must be a JSON object")
    if set(row) != set(REVIEW_FIELDS):
        missing = sorted(set(REVIEW_FIELDS) - set(row))
        unexpected = sorted(set(row) - set(REVIEW_FIELDS))
        raise ReviewIngestError(
            f"line {line}: review fields must be exactly {list(REVIEW_FIELDS)}; "
            f"missing={missing or 'none'} unexpected={unexpected or 'none'}"
        )
    record_id = row["record_id"]
    if not isinstance(record_id, str) or not record_id.strip():
        raise ReviewIngestError(f"line {line}: record_id must be a non-empty string")
    semantic_answer = row["semantic_answer"]
    if semantic_answer is not None and not isinstance(semantic_answer, str):
        raise ReviewIngestError(f"line {line}: semantic_answer must be a string or null")
    semantic_correct = row["semantic_correct"]
    if semantic_correct is not None and not isinstance(semantic_correct, bool):
        raise ReviewIngestError(
            f"line {line}: semantic_correct must be true, false or null"
        )
    for field in BOOLEAN_FIELDS:
        _require_bool(row, field, line)
    if row["ambiguity"] not in AMBIGUITY_VALUES:
        raise ReviewIngestError(
            f"line {line}: ambiguity must be one of {list(AMBIGUITY_VALUES)}"
        )
    if row["confidence"] not in CONFIDENCE_VALUES:
        raise ReviewIngestError(
            f"line {line}: confidence must be one of {list(CONFIDENCE_VALUES)}"
        )
    if not isinstance(row["notes"], str):
        raise ReviewIngestError(f"line {line}: notes must be a string")

    if row["output_complete"] and row["truncated"]:
        raise ReviewIngestError(
            f"line {line}: output_complete and truncated cannot both be true"
        )
    if row["no_answer"] and semantic_correct is True:
        raise ReviewIngestError(
            f"line {line}: no_answer cannot be true for a correct row"
        )
    if row["no_answer"] and isinstance(semantic_answer, str) and semantic_answer.strip():
        raise ReviewIngestError(
            f"line {line}: no_answer cannot be true when an answer is transcribed"
        )
    if semantic_correct is True and not (
        isinstance(semantic_answer, str) and semantic_answer.strip()
    ):
        raise ReviewIngestError(
            f"line {line}: a correct row must transcribe the stated answer"
        )
    return dict(row)


def load_review_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with open(path, "r", encoding="utf-8") as handle:
        for line, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ReviewIngestError(f"line {line}: invalid JSON: {exc}") from exc
            row = validate_review_row(payload, line)
            record_id = str(row["record_id"])
            if record_id in seen:
                raise ReviewIngestError(f"line {line}: duplicate record_id {record_id}")
            seen.add(record_id)
            rows.append(row)
    if not rows:
        raise ReviewIngestError(f"reviewer file contains no rows: {path}")
    return rows


def to_judgments(rows: Iterable[Mapping[str, Any]], reviewer_id: str) -> list[dict[str, Any]]:
    """Convert validated reviewer rows into calibration judgment records."""

    if not reviewer_id.strip():
        raise ReviewIngestError("reviewer id is required")
    judgments = [
        {
            "ambiguity": row["ambiguity"],
            "confidence": row["confidence"],
            "no_answer": row["no_answer"],
            "notes": row["notes"],
            "output_complete": row["output_complete"],
            "record_id": str(row["record_id"]),
            "reviewer_id": reviewer_id,
            "semantic_answer": row["semantic_answer"],
            "semantic_correct": row["semantic_correct"],
            "semantic_label": LABEL_BY_CORRECTNESS[row["semantic_correct"]],
            "truncated": row["truncated"],
        }
        for row in rows
    ]
    return sorted(judgments, key=lambda row: row["record_id"])


def _pack_record_ids(review_pack: Path) -> tuple[set[str], set[str]]:
    """Return (all review-pack ids, mandatory ids) from an emitted pack."""

    all_ids: set[str] = set()
    mandatory: set[str] = set()
    with open(review_pack, "r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if payload.get("status") == "not_applicable":
                continue
            record_id = payload.get("record_id")
            if not record_id:
                continue
            all_ids.add(str(record_id))
            reasons = payload.get("review_reasons") or []
            if any(reason != "deterministic_random_sample" for reason in reasons):
                mandatory.add(str(record_id))
    return all_ids, mandatory


def coverage_report(
    judgments: list[dict[str, Any]], review_pack: Path | None
) -> dict[str, Any]:
    reviewed = {row["record_id"] for row in judgments}
    report: dict[str, Any] = {
        "labels": {
            label: sum(1 for row in judgments if row["semantic_label"] == label)
            for label in ("correct", "incorrect", "unresolved")
        },
        "reviewed_rows": len(reviewed),
        "schema_version": SCHEMA_VERSION,
    }
    if review_pack is None:
        report["review_pack"] = "not_supplied"
        report["coverage_complete"] = None
        return report
    all_ids, mandatory = _pack_record_ids(review_pack)
    unknown = sorted(reviewed - all_ids)
    if unknown:
        raise ReviewIngestError(
            "reviewer rows are not in the review pack: " + ", ".join(unknown[:10])
        )
    outstanding = sorted(mandatory - reviewed)
    report["review_pack"] = review_pack.as_posix()
    report["review_pack_rows"] = len(all_ids)
    report["mandatory_rows"] = len(mandatory)
    report["outstanding_mandatory_rows"] = outstanding
    report["coverage_complete"] = not outstanding
    return report


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(payload)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, help="Structured reviewer JSONL.")
    parser.add_argument("--reviewer-id", default="")
    parser.add_argument("--output", type=Path, help="Judgment JSONL to write.")
    parser.add_argument(
        "--review-pack",
        type=Path,
        default=None,
        help="Optional review_pack/review_pack.jsonl for coverage checking.",
    )
    parser.add_argument(
        "--emit-schema",
        type=Path,
        default=None,
        help="Write the reviewer form schema and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.emit_schema is not None:
        args.emit_schema.parent.mkdir(parents=True, exist_ok=True)
        with open(args.emit_schema, "w", encoding="utf-8", newline="") as handle:
            handle.write(
                json.dumps(review_form_schema(), ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            )
        print(args.emit_schema)
        return 0
    if args.review is None or args.output is None:
        raise ReviewIngestError("--review and --output are required")
    rows = load_review_rows(args.review)
    judgments = to_judgments(rows, args.reviewer_id)
    write_jsonl(args.output, judgments)
    report = coverage_report(judgments, args.review_pack)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReviewIngestError as error:
        print(f"[FAIL] {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
