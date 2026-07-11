"""Read-only integrity audit helpers for bounded Phase 1 artifacts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .eval_parsing import create_eval_record
from .no_cot import (
    STRICT_ANSWER_ONLY_STOP_STRINGS,
    apply_stop_control_cleanup,
    validate_no_cot_output,
)
from .postprocess import postprocess_answer_only
from .phase1_branches import (
    POSTPROCESSED_UTILITY_BRANCH,
    RAW_STRICT_BRANCH,
    STOPPED_INTERVENTION_BRANCH,
    classify_branch_result,
    evaluate_visible_cot_baseline,
    get_phase1_branch_metadata,
)


AUDIT_SCHEMA_VERSION = "phase1-record-integrity/v1"
SOURCE_CODE_COMMIT = "359643b7b5eb8f95c13cca2e60fa753df8701282"
SOURCE_ARTIFACT_NAMES = (
    "phase1_generations.jsonl",
    "phase1_eval_records.jsonl",
    "phase1_metrics.csv",
    "phase1_summary.md",
)
AUDIT_OUTPUT_NAMES = (
    "record_audit_manifest.json",
    "record_audit_report.json",
    "record_audit_report.md",
    "record_pairing_mismatches.jsonl",
    "ambiguous_parse_records.jsonl",
    "ambiguous_parse_deterministic_review.jsonl",
    "recomputed_metrics.csv",
    "recomputed_branch_classifications.json",
)

EXPECTED_MODEL = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
EXPECTED_TASK_FAMILY = "arithmetic"
EXPECTED_CONDITIONS = (
    "strict_answer_only_prefill_answer",
    "strict_answer_only_stopped",
    "strict_answer_only_postprocessed",
    "visible_cot",
    "r1_style_thinking",
)
EXPECTED_TASKS_BY_DEPTH = {
    1: (
        ("arith_1op_001", "12"),
        ("arith_1op_002", "15"),
        ("arith_1op_003", "24"),
    ),
    2: (
        ("arith_2op_001", "16"),
        ("arith_2op_002", "16"),
        ("arith_2op_003", "4"),
    ),
    3: (
        ("arith_3op_001", "18"),
        ("arith_3op_002", "34"),
        ("arith_3op_003", "26"),
    ),
}
PAIRING_KEY_FIELDS = (
    "model_name",
    "task_family",
    "depth",
    "condition",
    "task_id",
)
CELL_KEY_FIELDS = ("model", "task_family", "depth", "condition")
METRIC_COLUMNS = (
    "model",
    "task_family",
    "depth",
    "condition",
    "branch",
    "branch_label",
    "n",
    "accuracy",
    "eval_accuracy",
    "parse_valid_rate",
    "parse_ambiguous_rate",
    "no_cot_valid_rate",
    "visible_reasoning_marker_rate",
    "answer_format_warning_rate",
    "raw_no_cot_valid_rate",
    "stopped_no_cot_valid_rate",
    "postprocessed_no_cot_valid_rate",
    "stop_triggered_rate",
    "stop_success_rate",
    "stop_warning_rate",
    "postprocessing_applied_rate",
    "postprocessing_success_rate",
    "postprocessing_warning_rate",
    "accuracy_raw",
    "accuracy_stopped",
    "accuracy_postprocessed",
    "eval_output_used",
    "avg_latency_s",
)
NUMERIC_METRIC_COLUMNS = frozenset(METRIC_COLUMNS[6:-2] + ("avg_latency_s",))
COMMON_FIELDS = (
    "model_name",
    "task_id",
    "task_family",
    "depth",
    "condition",
    "phase1_branch",
    "phase1_branch_label",
    "phase1_branch_interpretation",
    "parsed_answer",
    "parse_valid",
    "parse_ambiguous",
    "parse_strategy",
    "answer_format_warning",
    "raw_correctness",
    "raw_parsed_answer",
    "eval_output_used",
    "eval_correctness",
    "stopped_correctness",
    "postprocessed_correctness",
    "stop_control_enabled",
    "stop_triggered",
    "stop_reason",
    "stop_string",
    "stop_mode",
    "stop_warning",
    "raw_output_before_stop_cleanup",
    "raw_output",
    "stopped_output",
    "stopped_no_cot_valid",
    "raw_output_before_postprocess",
    "postprocessed_output",
    "postprocessing_applied",
    "postprocessing_strategy",
    "postprocessing_reason",
    "postprocessing_warning",
    "raw_no_cot_valid",
    "postprocessed_no_cot_valid",
    "postprocessed_answer_like",
)
PARSER_FIELDS = (
    "parsed_answer",
    "parse_valid",
    "parse_error_type",
    "parse_ambiguous",
    "parse_strategy",
    "candidate_answers",
    "answer_format_warning",
    "correctness",
    "error_type",
)
AMBIGUOUS_SOURCE_FIELDS = (
    "task_id",
    "model_name",
    "task_family",
    "depth",
    "condition",
    "phase1_branch",
    "phase1_branch_label",
    "phase1_branch_interpretation",
    "output",
    "parse_type",
    "expected_answer",
    "parsed_answer",
    "parse_valid",
    "parse_error_type",
    "parse_ambiguous",
    "parse_strategy",
    "candidate_answers",
    "answer_format_warning",
    "correctness",
    "error_type",
    "eval_output_used",
    "raw_output",
    "raw_output_before_stop_cleanup",
    "stopped_output",
    "stop_control_enabled",
    "stop_triggered",
    "stop_reason",
    "stop_string",
    "stop_mode",
    "stop_warning",
    "stopped_no_cot_valid",
    "raw_output_before_postprocess",
    "postprocessed_output",
    "postprocessing_applied",
    "postprocessing_strategy",
    "postprocessing_reason",
    "postprocessing_warning",
    "raw_no_cot_valid",
    "postprocessed_no_cot_valid",
    "postprocessed_answer_like",
    "raw_parsed_answer",
    "raw_parse_valid",
    "raw_correctness",
    "eval_correctness",
    "stopped_correctness",
    "postprocessed_correctness",
)
SUMMARY_SECTIONS = (
    "Objective",
    "Experimental Design",
    "Outputs",
    "Branch-level Metrics",
    "Branch success classification",
    "Interpretation Boundaries",
    "Validation Warnings",
    "Next Steps",
)

_MISSING = object()


class AuditInputError(ValueError):
    """Raised when an audit input violates the registered artifact contract."""


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 digest of exact artifact bytes."""
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditInputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> None:
    raise AuditInputError(f"non-finite JSON value: {value}")


def parse_jsonl_bytes(data: bytes, artifact_name: str) -> dict[str, Any]:
    """Parse JSONL without repairing invalid source lines."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {
            "artifact": artifact_name,
            "physical_lines": 0,
            "blank_lines": 0,
            "valid_records": 0,
            "invalid_lines": [{"line": None, "error": str(exc)}],
            "records": [],
            "parse_status": "FAIL",
        }

    physical_lines = text.splitlines()
    records: list[dict[str, Any]] = []
    invalid_lines: list[dict[str, Any]] = []
    blank_lines = 0
    for line_number, line in enumerate(physical_lines, start=1):
        if not line.strip():
            blank_lines += 1
            continue
        try:
            record = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_nonfinite_json,
            )
            if not isinstance(record, dict):
                raise AuditInputError("JSONL record is not an object")
            records.append(record)
        except (AuditInputError, json.JSONDecodeError) as exc:
            invalid_lines.append({"line": line_number, "error": str(exc)})

    parse_status = (
        "PASS"
        if records and not invalid_lines and blank_lines == 0
        else "FAIL"
    )
    if blank_lines:
        invalid_lines.append(
            {
                "line": None,
                "error": f"blank JSONL lines are not allowed: {blank_lines}",
            }
        )
    if not records:
        invalid_lines.append(
            {"line": None, "error": "JSONL must contain at least one record"}
        )
    return {
        "artifact": artifact_name,
        "physical_lines": len(physical_lines),
        "blank_lines": blank_lines,
        "valid_records": len(records),
        "invalid_lines": invalid_lines,
        "records": records,
        "parse_status": parse_status,
    }


def parse_metrics_csv_bytes(data: bytes) -> dict[str, Any]:
    """Parse the metrics CSV and enforce the registered header and row width."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {
            "header": [],
            "rows": [],
            "invalid_rows": [{"row": None, "error": str(exc)}],
            "parse_status": "FAIL",
        }

    reader = csv.reader(io.StringIO(text), strict=True)
    try:
        rows = list(reader)
    except csv.Error as exc:
        return {
            "header": [],
            "rows": [],
            "invalid_rows": [{"row": reader.line_num, "error": str(exc)}],
            "parse_status": "FAIL",
        }
    if not rows:
        return {
            "header": [],
            "rows": [],
            "invalid_rows": [{"row": 1, "error": "empty CSV"}],
            "parse_status": "FAIL",
        }
    header = rows[0]
    invalid_rows: list[dict[str, Any]] = []
    if tuple(header) != METRIC_COLUMNS:
        invalid_rows.append(
            {
                "row": 1,
                "error": "unexpected metrics header",
                "expected": list(METRIC_COLUMNS),
                "actual": header,
            }
        )

    parsed_rows: list[dict[str, str]] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            invalid_rows.append(
                {"row": row_number, "error": "blank CSV rows are not allowed"}
            )
            continue
        if len(row) != len(header):
            invalid_rows.append(
                {
                    "row": row_number,
                    "error": "unexpected CSV row width",
                    "expected": len(header),
                    "actual": len(row),
                }
            )
            continue
        parsed_rows.append(dict(zip(header, row)))

    return {
        "header": header,
        "physical_rows": len(rows),
        "rows": parsed_rows,
        "invalid_rows": invalid_rows,
        "parse_status": "PASS" if not invalid_rows else "FAIL",
    }


def validate_audit_prefixes(source_prefix: str, audit_output_prefix: str) -> None:
    """Reject output prefixes that can overwrite or enter the source namespace."""
    source = source_prefix.strip("/")
    output = audit_output_prefix.strip("/")
    if not source or not output:
        raise AuditInputError("source and audit output prefixes must be non-empty")
    if (
        output == source
        or output.startswith(f"{source}/")
        or source.startswith(f"{output}/")
    ):
        raise AuditInputError(
            "source and audit output prefixes must not overlap"
        )


def build_upload_plan(audit_output_prefix: str) -> list[str]:
    """Return the fixed, source-independent audit output blob names."""
    prefix = audit_output_prefix.strip("/")
    if not prefix:
        raise AuditInputError("audit output prefix must be non-empty")
    return [f"{prefix}/{name}" for name in AUDIT_OUTPUT_NAMES]


def expected_record_keys() -> list[tuple[Any, ...]]:
    """Return all 45 registered record keys in canonical writer order."""
    return [
        (EXPECTED_MODEL, EXPECTED_TASK_FAMILY, depth, condition, task_id)
        for depth in EXPECTED_TASKS_BY_DEPTH
        for condition in EXPECTED_CONDITIONS
        for task_id, _ in EXPECTED_TASKS_BY_DEPTH[depth]
    ]


def expected_cell_keys() -> list[tuple[Any, ...]]:
    """Return all 15 registered metric-cell keys in canonical order."""
    return [
        (EXPECTED_MODEL, EXPECTED_TASK_FAMILY, depth, condition)
        for depth in EXPECTED_TASKS_BY_DEPTH
        for condition in EXPECTED_CONDITIONS
    ]


def record_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """Build the registered composite record key from actual fields."""
    missing = [field for field in PAIRING_KEY_FIELDS if field not in record]
    if missing:
        raise AuditInputError(f"missing pairing fields: {', '.join(missing)}")
    for field in ("model_name", "task_family", "condition", "task_id"):
        if not isinstance(record[field], str) or not record[field]:
            raise AuditInputError(f"pairing field {field} must be a non-empty string")
    if isinstance(record["depth"], bool) or not isinstance(record["depth"], int):
        raise AuditInputError("pairing field depth must be an integer, not boolean")
    return tuple(record[field] for field in PAIRING_KEY_FIELDS)


def _record_key_dict(key: tuple[Any, ...]) -> dict[str, Any]:
    return dict(zip(PAIRING_KEY_FIELDS, key))


def _key_sort_value(key: tuple[Any, ...]) -> tuple[int, ...] | tuple[str, ...]:
    expected = {value: index for index, value in enumerate(expected_record_keys())}
    if key in expected:
        return (0, expected[key])
    return (1, *tuple(str(value) for value in key))


def _type_sensitive_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _type_sensitive_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _type_sensitive_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _describe_value(value: Any) -> dict[str, Any]:
    if value is _MISSING:
        return {"state": "absent"}
    if value is None:
        return {"state": "null", "value": None}
    if value == "":
        return {"state": "empty_string", "value": ""}
    if isinstance(value, str) and len(value) > 240:
        encoded = value.encode("utf-8")
        return {
            "state": "value",
            "type": "str",
            "length": len(value),
            "sha256": sha256_bytes(encoded),
            "preview": value[:240],
        }
    return {"state": "value", "type": type(value).__name__, "value": value}


def audit_pairing(
    generation_records: Sequence[Mapping[str, Any]],
    eval_records: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[tuple[tuple[Any, ...], Mapping[str, Any], Mapping[str, Any]]]]:
    """Audit key uniqueness and build only unambiguous generation/eval pairs."""

    def index_records(
        records: Sequence[Mapping[str, Any]], artifact: str
    ) -> tuple[dict[tuple[Any, ...], list[Mapping[str, Any]]], list[dict[str, Any]]]:
        index: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
        invalid: list[dict[str, Any]] = []
        for ordinal, record in enumerate(records, start=1):
            try:
                index[record_key(record)].append(record)
            except AuditInputError as exc:
                invalid.append(
                    {"artifact": artifact, "ordinal": ordinal, "error": str(exc)}
                )
        return index, invalid

    generation_index, invalid_generation = index_records(
        generation_records, "phase1_generations.jsonl"
    )
    eval_index, invalid_eval = index_records(
        eval_records, "phase1_eval_records.jsonl"
    )
    duplicate_generation = {
        key: len(records)
        for key, records in generation_index.items()
        if len(records) != 1
    }
    duplicate_eval = {
        key: len(records)
        for key, records in eval_index.items()
        if len(records) != 1
    }
    generation_keys = set(generation_index)
    eval_keys = set(eval_index)
    generation_only = sorted(generation_keys - eval_keys, key=_key_sort_value)
    eval_only = sorted(eval_keys - generation_keys, key=_key_sort_value)
    pairs = [
        (key, generation_index[key][0], eval_index[key][0])
        for key in sorted(generation_keys & eval_keys, key=_key_sort_value)
        if len(generation_index[key]) == 1 and len(eval_index[key]) == 1
    ]
    canonical = expected_record_keys()
    generation_order: list[tuple[Any, ...]] = []
    for record in generation_records:
        try:
            generation_order.append(record_key(record))
        except AuditInputError:
            continue
    eval_order: list[tuple[Any, ...]] = []
    for record in eval_records:
        try:
            eval_order.append(record_key(record))
        except AuditInputError:
            continue
    passed = not (
        invalid_generation
        or invalid_eval
        or duplicate_generation
        or duplicate_eval
        or generation_only
        or eval_only
    )
    return (
        {
            "pairing_key_type": "composite",
            "pairing_key_fields": list(PAIRING_KEY_FIELDS),
            "unique_generation_keys": len(generation_index),
            "unique_eval_keys": len(eval_index),
            "duplicate_generation_keys": [
                {"key": _record_key_dict(key), "count": count}
                for key, count in sorted(
                    duplicate_generation.items(), key=lambda item: _key_sort_value(item[0])
                )
            ],
            "duplicate_eval_keys": [
                {"key": _record_key_dict(key), "count": count}
                for key, count in sorted(
                    duplicate_eval.items(), key=lambda item: _key_sort_value(item[0])
                )
            ],
            "generation_only_keys": [_record_key_dict(key) for key in generation_only],
            "eval_only_keys": [_record_key_dict(key) for key in eval_only],
            "invalid_generation_keys": invalid_generation,
            "invalid_eval_keys": invalid_eval,
            "generation_canonical_order": generation_order == canonical,
            "eval_canonical_order": eval_order == canonical,
            "pairs_checked": len(pairs),
            "result": "PASS" if passed else "FAIL",
        },
        pairs,
    )


def audit_membership(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare actual record membership against the exact 45-record design."""
    actual_keys: list[tuple[Any, ...]] = []
    invalid: list[dict[str, Any]] = []
    for ordinal, record in enumerate(records, start=1):
        try:
            actual_keys.append(record_key(record))
        except AuditInputError as exc:
            invalid.append({"ordinal": ordinal, "error": str(exc)})
    actual_counts = Counter(actual_keys)
    expected_counts = Counter(expected_record_keys())
    missing = list((expected_counts - actual_counts).elements())
    extra = list((actual_counts - expected_counts).elements())
    expected_answers = {
        task_id: answer
        for tasks in EXPECTED_TASKS_BY_DEPTH.values()
        for task_id, answer in tasks
    }
    answer_mismatches: list[dict[str, Any]] = []
    for ordinal, record in enumerate(records, start=1):
        task_id = record.get("task_id")
        if task_id not in expected_answers:
            continue
        expected_answer = expected_answers[task_id]
        answer_fields = [
            field
            for field in ("ground_truth", "expected_answer")
            if field in record
        ]
        if not answer_fields:
            answer_mismatches.append(
                {
                    "ordinal": ordinal,
                    "task_id": task_id,
                    "field": "registered_answer",
                    "expected": expected_answer,
                    "actual": "absent",
                }
            )
        for field in answer_fields:
            if (
                not isinstance(record[field], str)
                or record[field] != expected_answer
            ):
                answer_mismatches.append(
                    {
                        "ordinal": ordinal,
                        "task_id": task_id,
                        "field": field,
                        "expected": expected_answer,
                        "actual": record[field],
                    }
                )

    cell_rows: list[dict[str, Any]] = []
    for model, task_family, depth, condition in expected_cell_keys():
        matching = [
            key
            for key in actual_keys
            if key[:4] == (model, task_family, depth, condition)
        ]
        unique_items = {key[4] for key in matching}
        expected_items = {
            task_id for task_id, _ in EXPECTED_TASKS_BY_DEPTH[depth]
        }
        cell_rows.append(
            {
                "model": model,
                "task_family": task_family,
                "depth": depth,
                "condition": condition,
                "record_count": len(matching),
                "unique_item_count": len(unique_items),
                "expected_count": 3,
                "missing_items": sorted(expected_items - unique_items),
                "extra_items": sorted(unique_items - expected_items),
                "status": (
                    "PASS"
                    if len(matching) == 3 and unique_items == expected_items
                    else "FAIL"
                ),
            }
        )

    duplicate_membership = [
        {"key": _record_key_dict(key), "count": count}
        for key, count in sorted(actual_counts.items(), key=lambda item: _key_sort_value(item[0]))
        if count > 1
    ]
    result = (
        "PASS"
        if not (
            invalid
            or missing
            or extra
            or duplicate_membership
            or answer_mismatches
        )
        else "FAIL"
    )
    return {
        "expected_models": [EXPECTED_MODEL],
        "actual_models": sorted({str(key[0]) for key in actual_keys}),
        "expected_tasks": [EXPECTED_TASK_FAMILY],
        "actual_tasks": sorted({str(key[1]) for key in actual_keys}),
        "expected_depths": list(EXPECTED_TASKS_BY_DEPTH),
        "actual_depths": sorted({key[2] for key in actual_keys}, key=str),
        "expected_conditions": list(EXPECTED_CONDITIONS),
        "actual_conditions": sorted({str(key[3]) for key in actual_keys}),
        "expected_observations": 45,
        "actual_observations": len(records),
        "missing_combinations": [_record_key_dict(key) for key in missing],
        "extra_combinations": [_record_key_dict(key) for key in extra],
        "duplicate_prompt_item_membership": duplicate_membership,
        "registered_answer_mismatches": answer_mismatches,
        "invalid_keys": invalid,
        "cells": cell_rows,
        "result": result,
    }


def audit_field_consistency(
    pairs: Sequence[
        tuple[tuple[Any, ...], Mapping[str, Any], Mapping[str, Any]]
    ],
) -> dict[str, Any]:
    """Check same-name and registered cross-schema field invariants."""
    mismatches: list[dict[str, Any]] = []
    field_counts: Counter[str] = Counter()

    def compare(
        key: tuple[Any, ...],
        rule_id: str,
        left_name: str,
        left_value: Any,
        right_name: str,
        right_value: Any,
    ) -> None:
        if _type_sensitive_equal(left_value, right_value):
            return
        field_counts[left_name] += 1
        field_counts[right_name] += 1
        mismatches.append(
            {
                "key": _record_key_dict(key),
                "rule_id": rule_id,
                "left_field": left_name,
                "left": _describe_value(left_value),
                "right_field": right_name,
                "right": _describe_value(right_value),
            }
        )

    for key, generation, evaluation in pairs:
        for field in COMMON_FIELDS:
            compare(
                key,
                "same_name_field",
                f"generation.{field}",
                generation.get(field, _MISSING),
                f"eval.{field}",
                evaluation.get(field, _MISSING),
            )
        cross_rules = (
            ("selected_output", "eval_output", "output"),
            ("expected_answer", "ground_truth", "expected_answer"),
            ("correctness", "correct", "correctness"),
            ("eval_correctness", "eval_correct", "eval_correctness"),
            ("raw_correctness", "raw_correct", "raw_correctness"),
            ("stopped_correctness", "stopped_correct", "stopped_correctness"),
            (
                "postprocessed_correctness",
                "postprocessed_correct",
                "postprocessed_correctness",
            ),
        )
        for rule_id, generation_field, eval_field in cross_rules:
            compare(
                key,
                rule_id,
                f"generation.{generation_field}",
                generation.get(generation_field, _MISSING),
                f"eval.{eval_field}",
                evaluation.get(eval_field, _MISSING),
            )
        raw_references = (
            ("generation.output", generation.get("output", _MISSING)),
            ("generation.raw_output", generation.get("raw_output", _MISSING)),
            (
                "generation.raw_output_before_stop_cleanup",
                generation.get("raw_output_before_stop_cleanup", _MISSING),
            ),
            (
                "generation.raw_output_before_postprocess",
                generation.get("raw_output_before_postprocess", _MISSING),
            ),
            ("eval.raw_output", evaluation.get("raw_output", _MISSING)),
            (
                "eval.raw_output_before_stop_cleanup",
                evaluation.get("raw_output_before_stop_cleanup", _MISSING),
            ),
            (
                "eval.raw_output_before_postprocess",
                evaluation.get("raw_output_before_postprocess", _MISSING),
            ),
        )
        anchor_name, anchor_value = raw_references[0]
        for field_name, value in raw_references[1:]:
            compare(key, "raw_output_invariant", anchor_name, anchor_value, field_name, value)

    return {
        "pairs_checked": len(pairs),
        "mismatched_pairs": len(
            {
                tuple(item["key"][field] for field in PAIRING_KEY_FIELDS)
                for item in mismatches
            }
        ),
        "mismatch_count": len(mismatches),
        "mismatched_fields": dict(sorted(field_counts.items())),
        "mismatches": mismatches,
        "result": "PASS" if not mismatches else "FAIL",
    }


def audit_transformation_consistency(
    pairs: Sequence[
        tuple[tuple[Any, ...], Mapping[str, Any], Mapping[str, Any]]
    ],
) -> tuple[dict[str, Any], dict[tuple[Any, ...], dict[str, Any]]]:
    """Recompute selected-output derivation for each registered condition."""
    mismatches: list[dict[str, Any]] = []
    mismatch_counts: Counter[str] = Counter()
    checks_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}

    def compare(
        key: tuple[Any, ...],
        field: str,
        stored: Any,
        recomputed: Any,
    ) -> None:
        if _type_sensitive_equal(stored, recomputed):
            return
        mismatch_counts[field] += 1
        mismatches.append(
            {
                "key": _record_key_dict(key),
                "field": field,
                "stored": _describe_value(stored),
                "recomputed": _describe_value(recomputed),
            }
        )

    for key, generation, evaluation in pairs:
        condition = evaluation.get("condition")
        raw_output = evaluation.get("raw_output", _MISSING)
        parse_type = evaluation.get("parse_type", _MISSING)
        before_count = len(mismatches)
        if not isinstance(raw_output, str) or not isinstance(parse_type, str):
            compare(
                key,
                "transformation_input_schema",
                {
                    "raw_output": _describe_value(raw_output),
                    "parse_type": _describe_value(parse_type),
                },
                {"raw_output": "str", "parse_type": "str"},
            )
            checks_by_key[key] = {
                "selected_output_derivation_consistent": False,
                "mismatched_fields": ["transformation_input_schema"],
            }
            continue

        expected_selected = {
            "strict_answer_only_prefill_answer": "raw",
            "strict_answer_only_stopped": "stopped",
            "strict_answer_only_postprocessed": "postprocessed",
            "visible_cot": "raw",
            "r1_style_thinking": "raw",
        }.get(str(condition))
        compare(
            key,
            "eval_output_used",
            evaluation.get("eval_output_used", _MISSING),
            expected_selected,
        )
        compare(
            key,
            "generation.eval_output_used",
            generation.get("eval_output_used", _MISSING),
            expected_selected,
        )

        if expected_selected == "stopped":
            compare(
                key,
                "generation.stop_strings",
                generation.get("stop_strings", _MISSING),
                list(STRICT_ANSWER_ONLY_STOP_STRINGS),
            )
            stop_result = apply_stop_control_cleanup(
                raw_output=raw_output,
                stop_strings=STRICT_ANSWER_ONLY_STOP_STRINGS,
                stop_control_enabled=True,
                stop_mode=str(evaluation.get("stop_mode")),
                triggered_stop_string=evaluation.get("stop_string"),
            )
            expected_fields = {
                "raw_output_before_stop_cleanup": (
                    stop_result.raw_output_before_stop_cleanup
                ),
                "raw_output": stop_result.raw_output,
                "stopped_output": stop_result.stopped_output,
                "stop_control_enabled": stop_result.stop_control_enabled,
                "stop_triggered": stop_result.stop_triggered,
                "stop_reason": stop_result.stop_reason,
                "stop_string": stop_result.stop_string,
                "stop_mode": stop_result.stop_mode,
                "stop_warning": stop_result.stop_warning,
                "stopped_no_cot_valid": validate_no_cot_output(
                    stop_result.stopped_output,
                    method="answer_prefill",
                ).is_valid,
            }
            for field, recomputed in expected_fields.items():
                compare(
                    key,
                    field,
                    evaluation.get(field, _MISSING),
                    recomputed,
                )
            selected_output = stop_result.stopped_output
        elif expected_selected == "postprocessed":
            postprocessed = postprocess_answer_only(
                raw_output,
                task_type=parse_type,
            )
            expected_fields = {
                "raw_output_before_postprocess": postprocessed.raw_output,
                "postprocessed_output": postprocessed.postprocessed_output,
                "postprocessing_applied": postprocessed.postprocessing_applied,
                "postprocessing_strategy": postprocessed.postprocessing_strategy,
                "postprocessing_reason": postprocessed.postprocessing_reason,
                "postprocessing_warning": postprocessed.postprocessing_warning,
                "raw_no_cot_valid": postprocessed.raw_no_cot_valid,
                "postprocessed_no_cot_valid": (
                    postprocessed.postprocessed_no_cot_valid
                ),
                "postprocessed_answer_like": (
                    postprocessed.postprocessed_answer_like
                ),
            }
            for field, recomputed in expected_fields.items():
                compare(
                    key,
                    field,
                    evaluation.get(field, _MISSING),
                    recomputed,
                )
            selected_output = postprocessed.postprocessed_output
        elif expected_selected == "raw":
            selected_output = raw_output
        else:
            compare(
                key,
                "condition",
                condition,
                "one of the five registered conditions",
            )
            selected_output = _MISSING

        compare(
            key,
            "eval.output",
            evaluation.get("output", _MISSING),
            selected_output,
        )
        compare(
            key,
            "generation.eval_output",
            generation.get("eval_output", _MISSING),
            selected_output,
        )
        record_mismatches = mismatches[before_count:]
        checks_by_key[key] = {
            "selected_output_derivation_consistent": not record_mismatches,
            "mismatched_fields": sorted(
                {item["field"] for item in record_mismatches}
            ),
        }

    return (
        {
            "pairs_checked": len(pairs),
            "mismatched_pairs": sum(
                not check["selected_output_derivation_consistent"]
                for check in checks_by_key.values()
            ),
            "mismatch_count": len(mismatches),
            "mismatched_fields": dict(sorted(mismatch_counts.items())),
            "mismatches": mismatches,
            "result": "PASS" if not mismatches else "FAIL",
        },
        checks_by_key,
    )


def recompute_parser_fields(
    eval_records: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[tuple[Any, ...], dict[str, Any]]]:
    """Replay the current parser without changing stored source fields."""
    mismatch_counts: Counter[str] = Counter()
    mismatch_details: list[dict[str, Any]] = []
    mechanical_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}

    for record in eval_records:
        key = record_key(record)
        required = ("output", "parse_type", "expected_answer", "raw_output")
        missing = [field for field in required if field not in record]
        if missing:
            raise AuditInputError(
                f"{_record_key_dict(key)} missing parser fields: {', '.join(missing)}"
            )
        selected = create_eval_record(
            output=record["output"],
            parse_type=record["parse_type"],
            expected_answer=record["expected_answer"],
        )
        raw = create_eval_record(
            output=record["raw_output"],
            parse_type=record["parse_type"],
            expected_answer=record["expected_answer"],
        )
        mismatched_fields: list[str] = []
        for field in PARSER_FIELDS:
            if not _type_sensitive_equal(record.get(field, _MISSING), selected[field]):
                mismatch_counts[field] += 1
                mismatched_fields.append(field)
                mismatch_details.append(
                    {
                        "key": _record_key_dict(key),
                        "field": field,
                        "stored": _describe_value(record.get(field, _MISSING)),
                        "recomputed": _describe_value(selected[field]),
                    }
                )
        raw_aliases = {
            "raw_parsed_answer": raw["parsed_answer"],
            "raw_parse_valid": raw["parse_valid"],
            "raw_correctness": raw["correctness"],
        }
        for field, expected in raw_aliases.items():
            if not _type_sensitive_equal(record.get(field, _MISSING), expected):
                mismatch_counts[field] += 1
                mismatched_fields.append(field)
                mismatch_details.append(
                    {
                        "key": _record_key_dict(key),
                        "field": field,
                        "stored": _describe_value(record.get(field, _MISSING)),
                        "recomputed": _describe_value(expected),
                    }
                )
        alias_consistent = _type_sensitive_equal(
            record.get("eval_correctness", _MISSING),
            record.get("correctness", _MISSING),
        )
        if not alias_consistent:
            mismatch_counts["eval_correctness"] += 1
            mismatched_fields.append("eval_correctness")
            mismatch_details.append(
                {
                    "key": _record_key_dict(key),
                    "field": "eval_correctness",
                    "stored": _describe_value(
                        record.get("eval_correctness", _MISSING)
                    ),
                    "recomputed": _describe_value(
                        record.get("correctness", _MISSING)
                    ),
                }
            )
        mechanical_by_key[key] = {
            "stored_parser_consistent": not any(
                field in PARSER_FIELDS for field in mismatched_fields
            ),
            "stored_raw_parser_consistent": not any(
                field in raw_aliases for field in mismatched_fields
            ),
            "stored_correctness_consistent": (
                "correctness" not in mismatched_fields and alias_consistent
            ),
            "mismatched_fields": sorted(set(mismatched_fields)),
            "recomputed_selected": {field: selected[field] for field in PARSER_FIELDS},
            "recomputed_raw": raw_aliases,
        }

    requested_counts = {
        f"{field}_mismatches": mismatch_counts.get(field, 0)
        for field in (
            "parse_valid",
            "parse_ambiguous",
            "parse_strategy",
            "parsed_answer",
            "correctness",
        )
    }
    return (
        {
            **requested_counts,
            "all_mismatch_counts": dict(sorted(mismatch_counts.items())),
            "mismatch_details": mismatch_details,
            "source_parser_version": None,
            "source_parser_version_status": "legacy_unversioned",
            "source_code_commit": SOURCE_CODE_COMMIT,
            "result": "PASS" if not mismatch_counts else "FAIL",
        },
        mechanical_by_key,
    )


def build_ambiguous_audit_records(
    pairs: Sequence[
        tuple[tuple[Any, ...], Mapping[str, Any], Mapping[str, Any]]
    ],
    mechanical_by_key: Mapping[tuple[Any, ...], Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Project stored ambiguous records and deterministic consistency evidence."""
    selected = [
        (key, generation, evaluation)
        for key, generation, evaluation in pairs
        if evaluation.get("parse_ambiguous") is True
    ]
    selected.sort(key=lambda item: _key_sort_value(item[0]))
    ambiguous_records: list[dict[str, Any]] = []
    deterministic_reviews: list[dict[str, Any]] = []
    for audit_index, (key, generation, evaluation) in enumerate(selected, start=1):
        source = {
            field: evaluation.get(field, _MISSING)
            for field in AMBIGUOUS_SOURCE_FIELDS
        }
        missing = [field for field, value in source.items() if value is _MISSING]
        if missing:
            raise AuditInputError(
                f"{_record_key_dict(key)} missing ambiguous-review fields: "
                f"{', '.join(missing)}"
            )
        mechanical = dict(mechanical_by_key[key])
        record = {
            "audit_index": audit_index,
            "pairing_key": _record_key_dict(key),
            "source": source,
            "generation_context": {
                "prompt": generation.get("prompt"),
                "ground_truth": generation.get("ground_truth"),
            },
            "mechanical_checks": mechanical,
        }
        ambiguous_records.append(record)

        issues: list[str] = []
        output = str(evaluation.get("output") or "")
        if not output.strip():
            issues.append("placeholder_or_no_answer")
        if evaluation.get("parse_strategy") == "last_number":
            issues.append("last_number_selection_risk")
        if output.lower().count("<think>") != output.lower().count("</think>"):
            issues.append("malformed_output")
        if not mechanical["stored_correctness_consistent"]:
            issues.append("stored_correctness_inconsistent")
        deterministic_reviews.append(
            {
                "audit_index": audit_index,
                "pairing_key": _record_key_dict(key),
                "audit_ambiguity_category": "review_inconclusive",
                "audit_issue_categories": sorted(set(issues)),
                "audit_answer_judgment": "requires_independent_review",
                "audit_stored_parser_consistent": mechanical[
                    "stored_parser_consistent"
                ],
                "audit_stored_correctness_consistent": mechanical[
                    "stored_correctness_consistent"
                ],
                "audit_confidence": 1,
                "audit_notes": [
                    "Deterministic checks do not replace independent semantic review."
                ],
            }
        )
    return ambiguous_records, deterministic_reviews


def _condition_method(condition: str) -> str:
    if condition in {
        "strict_answer_only_prefill_answer",
        "strict_answer_only_stopped",
        "strict_answer_only_postprocessed",
    }:
        return "answer_prefill"
    if condition == "visible_cot":
        return "visible_cot"
    if condition == "r1_style_thinking":
        return "r1_style_thinking"
    raise AuditInputError(f"unregistered condition: {condition}")


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _format_rate(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4f}"


def recompute_metric_rows(
    pairs: Sequence[
        tuple[tuple[Any, ...], Mapping[str, Any], Mapping[str, Any]]
    ],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Recompute the 15 historical metric rows from paired source records."""
    grouped: dict[
        tuple[Any, ...],
        list[tuple[Mapping[str, Any], Mapping[str, Any]]],
    ] = defaultdict(list)
    for key, generation, evaluation in pairs:
        grouped[key[:4]].append((generation, evaluation))

    rows: list[dict[str, Any]] = []
    latency_limitations: list[dict[str, Any]] = []
    for cell in expected_cell_keys():
        cell_pairs = grouped.get(cell, [])
        model, task_family, depth, condition = cell
        branch_metadata = get_phase1_branch_metadata(condition)
        evaluations = [evaluation for _, evaluation in cell_pairs]
        generations = [generation for generation, _ in cell_pairs]
        n = len(cell_pairs)
        eval_output_values = {record.get("eval_output_used") for record in evaluations}
        if len(eval_output_values) != 1:
            raise AuditInputError(f"mixed eval_output_used in cell: {cell}")
        eval_output_used = next(iter(eval_output_values), "raw")

        no_cot_applicable = [
            record for record in generations if record.get("no_cot_applicable") is True
        ]
        stopped = [
            record
            for record in evaluations
            if record.get("eval_output_used") == "stopped"
        ]
        postprocessed = [
            record
            for record in evaluations
            if record.get("eval_output_used") == "postprocessed"
        ]
        visible_markers = 0
        for generation in generations:
            raw_output = generation.get("raw_output")
            if not isinstance(raw_output, str):
                raise AuditInputError(f"missing raw_output in metric cell: {cell}")
            validation = validate_no_cot_output(
                raw_output,
                method=_condition_method(condition),
            )
            if validation.has_visible_reasoning_marker:
                visible_markers += 1

        latency_values = [
            generation.get("generation_time_s") for generation in generations
        ]
        latency_recomputable = all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            and float(value) > 0
            for value in latency_values
        )
        avg_latency: float | None = None
        if latency_recomputable and latency_values:
            avg_latency = sum(float(value) for value in latency_values) / len(
                latency_values
            )
        else:
            latency_limitations.append(
                {
                    "cell": dict(zip(CELL_KEY_FIELDS, cell)),
                    "field": "avg_latency_s",
                    "reason": (
                        "generation failures are omitted from the source latency "
                        "denominator and cannot be inferred from zero-valued records"
                    ),
                }
            )

        correct_count = sum(record.get("correctness") is True for record in evaluations)
        raw_correct_count = sum(
            record.get("raw_correctness") is True for record in evaluations
        )
        row: dict[str, Any] = {
            "model": model,
            "task_family": task_family,
            "depth": str(depth),
            "condition": condition,
            "branch": branch_metadata["phase1_branch"],
            "branch_label": branch_metadata["phase1_branch_label"],
            "n": str(n),
            "accuracy": _format_rate(_rate(correct_count, n)),
            "eval_accuracy": _format_rate(_rate(correct_count, n)),
            "parse_valid_rate": _format_rate(
                _rate(sum(record.get("parse_valid") is True for record in evaluations), n)
            ),
            "parse_ambiguous_rate": _format_rate(
                _rate(
                    sum(
                        record.get("parse_ambiguous") is True
                        for record in evaluations
                    ),
                    n,
                )
            ),
            "no_cot_valid_rate": _format_rate(
                _rate(
                    sum(
                        record.get("no_cot_validity") is True
                        for record in no_cot_applicable
                    ),
                    len(no_cot_applicable),
                )
            ),
            "visible_reasoning_marker_rate": _format_rate(
                _rate(visible_markers, n)
            ),
            "answer_format_warning_rate": _format_rate(
                _rate(
                    sum(bool(record.get("answer_format_warning")) for record in evaluations),
                    n,
                )
            ),
            "raw_no_cot_valid_rate": _format_rate(
                _rate(
                    sum(
                        record.get("raw_no_cot_valid") is True
                        for record in evaluations
                        if record.get("condition") in EXPECTED_CONDITIONS[:3]
                    ),
                    len(no_cot_applicable),
                )
            ),
            "stopped_no_cot_valid_rate": _format_rate(
                _rate(
                    sum(record.get("stopped_no_cot_valid") is True for record in stopped),
                    len(stopped),
                )
            ),
            "postprocessed_no_cot_valid_rate": _format_rate(
                _rate(
                    sum(
                        record.get("postprocessed_no_cot_valid") is True
                        for record in postprocessed
                    ),
                    len(postprocessed),
                )
            ),
            "stop_triggered_rate": _format_rate(
                _rate(
                    sum(record.get("stop_triggered") is True for record in stopped),
                    len(stopped),
                )
            ),
            "stop_success_rate": _format_rate(
                _rate(
                    sum(
                        record.get("stopped_no_cot_valid") is True
                        and record.get("parse_valid") is True
                        for record in stopped
                    ),
                    len(stopped),
                )
            ),
            "stop_warning_rate": _format_rate(
                _rate(
                    sum(bool(record.get("stop_warning")) for record in stopped),
                    len(stopped),
                )
            ),
            "postprocessing_applied_rate": _format_rate(
                _rate(
                    sum(
                        record.get("postprocessing_applied") is True
                        for record in postprocessed
                    ),
                    len(postprocessed),
                )
            ),
            "postprocessing_success_rate": _format_rate(
                _rate(
                    sum(
                        record.get("postprocessed_answer_like") is True
                        for record in postprocessed
                    ),
                    len(postprocessed),
                )
            ),
            "postprocessing_warning_rate": _format_rate(
                _rate(
                    sum(
                        bool(record.get("postprocessing_warning"))
                        for record in postprocessed
                    ),
                    len(postprocessed),
                )
            ),
            "accuracy_raw": _format_rate(_rate(raw_correct_count, n)),
            "accuracy_stopped": _format_rate(
                _rate(
                    sum(record.get("correctness") is True for record in stopped),
                    len(stopped),
                )
            ),
            "accuracy_postprocessed": _format_rate(
                _rate(
                    sum(
                        record.get("correctness") is True
                        for record in postprocessed
                    ),
                    len(postprocessed),
                )
            ),
            "eval_output_used": str(eval_output_used),
            "avg_latency_s": (
                None if avg_latency is None else f"{avg_latency:.4f}"
            ),
        }
        rows.append(row)
    return rows, latency_limitations


def compare_metric_rows(
    stored_rows: Sequence[Mapping[str, str]],
    recomputed_rows: Sequence[Mapping[str, Any]],
    tolerance: float = 1e-4,
) -> dict[str, Any]:
    """Compare stored and recomputed metrics with the registered tolerance."""
    stored_index: dict[tuple[str, str, str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in stored_rows:
        stored_index[
            (
                str(row.get("model")),
                str(row.get("task_family")),
                str(row.get("depth")),
                str(row.get("condition")),
            )
        ].append(row)
    mismatches: list[dict[str, Any]] = []
    unverifiable: list[dict[str, Any]] = []
    max_absolute_difference = 0.0
    matching_rows = 0
    for recomputed in recomputed_rows:
        key = tuple(str(recomputed[field]) for field in CELL_KEY_FIELDS)
        candidates = stored_index.get(key, [])
        if len(candidates) != 1:
            mismatches.append(
                {
                    "cell": dict(zip(CELL_KEY_FIELDS, key)),
                    "field": "row_multiplicity",
                    "stored_count": len(candidates),
                    "expected_count": 1,
                }
            )
            continue
        stored = candidates[0]
        row_mismatch = False
        for field in METRIC_COLUMNS:
            expected = recomputed[field]
            actual = stored.get(field)
            if field == "avg_latency_s" and expected is None:
                unverifiable.append(
                    {
                        "cell": dict(zip(CELL_KEY_FIELDS, key)),
                        "field": field,
                        "stored": actual,
                        "reason": "source latency denominator is not independently recoverable",
                    }
                )
                continue
            if field in NUMERIC_METRIC_COLUMNS:
                if str(expected).upper() == "NA" or str(actual).upper() == "NA":
                    equal = str(expected).upper() == str(actual).upper()
                    difference = None
                else:
                    try:
                        difference = abs(float(expected) - float(actual))
                        equal = difference <= tolerance
                        max_absolute_difference = max(
                            max_absolute_difference, difference
                        )
                    except (TypeError, ValueError):
                        equal = False
                        difference = None
            else:
                equal = str(expected) == str(actual)
                difference = None
            if not equal:
                row_mismatch = True
                mismatches.append(
                    {
                        "cell": dict(zip(CELL_KEY_FIELDS, key)),
                        "field": field,
                        "stored": actual,
                        "recomputed": expected,
                        "absolute_difference": difference,
                    }
                )
        if not row_mismatch:
            matching_rows += 1
    expected_keys = {
        tuple(str(row[field]) for field in CELL_KEY_FIELDS)
        for row in recomputed_rows
    }
    extra_rows = [
        dict(zip(CELL_KEY_FIELDS, key))
        for key in stored_index
        if key not in expected_keys
    ]
    return {
        "expected_rows": len(recomputed_rows),
        "stored_rows": len(stored_rows),
        "recomputed_rows": len(recomputed_rows),
        "matching_rows": matching_rows,
        "mismatching_rows": len(
            {
                tuple(item["cell"][field] for field in CELL_KEY_FIELDS)
                for item in mismatches
            }
        ),
        "mismatching_fields": sorted(
            {item["field"] for item in mismatches}
        ),
        "mismatches": mismatches,
        "unverifiable_fields": unverifiable,
        "extra_rows": extra_rows,
        "max_absolute_difference": max_absolute_difference,
        "result": "PASS" if not mismatches and not extra_rows else "FAIL",
    }


def _attach_visible_cot_baselines(
    metric_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    baseline_by_depth = {
        (str(row["model"]), str(row["task_family"]), str(row["depth"])): {
            "visible_cot_n": row["n"],
            "visible_cot_accuracy": row["accuracy_raw"],
            "visible_cot_parse_valid_rate": row["parse_valid_rate"],
            "visible_cot_answer_format_warning_rate": row[
                "answer_format_warning_rate"
            ],
        }
        for row in metric_rows
        if row["condition"] == "visible_cot"
    }
    enriched: list[dict[str, Any]] = []
    for row in metric_rows:
        key = (str(row["model"]), str(row["task_family"]), str(row["depth"]))
        enriched.append({**row, **baseline_by_depth.get(key, {})})
    return enriched


def recompute_visible_cot_baselines(
    metric_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Recompute visible-CoT validity by depth."""
    result: dict[str, dict[str, Any]] = {}
    for row in _attach_visible_cot_baselines(metric_rows):
        if row["condition"] != "visible_cot":
            continue
        result[str(row["depth"])] = evaluate_visible_cot_baseline(row)
    return result


def _stop_string_distributions(
    generation_records: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str, str, str], str]:
    counts: dict[tuple[str, str, str, str], Counter[str]] = defaultdict(Counter)
    for record in generation_records:
        if record.get("phase1_branch") != STOPPED_INTERVENTION_BRANCH:
            continue
        key = (
            str(record.get("model_name")),
            str(record.get("task_family")),
            str(record.get("depth")),
            str(record.get("condition")),
        )
        stop_string = record.get("stop_string")
        counts[key][
            json.dumps(stop_string, ensure_ascii=False)
            if stop_string is not None
            else "none"
        ] += 1
    return {
        key: ", ".join(
            f"{label}={count}" for label, count in sorted(distribution.items())
        )
        for key, distribution in counts.items()
    }


def recompute_branch_classifications(
    metric_rows: Sequence[Mapping[str, Any]],
    generation_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Recompute the nine answer-control classifications using current helpers."""
    allowed = {
        RAW_STRICT_BRANCH,
        STOPPED_INTERVENTION_BRANCH,
        POSTPROCESSED_UTILITY_BRANCH,
    }
    stop_distributions = _stop_string_distributions(generation_records)
    classifications: list[dict[str, Any]] = []
    for row in _attach_visible_cot_baselines(metric_rows):
        branch = str(row["branch"])
        if branch not in allowed:
            continue
        classification = classify_branch_result(branch, row)
        relative = classification["relative_accuracy_gate_passed"]
        if relative is None:
            relative_label = "NA"
        elif classification["relative_accuracy_gate_required"]:
            relative_label = "passed" if relative else "failed"
        else:
            relative_label = "reported_passed" if relative else "reported_failed"
        stop_key = (
            str(row["model"]),
            str(row["task_family"]),
            str(row["depth"]),
            str(row["condition"]),
        )
        rendered = {
            "model": str(row["model"]),
            "task_family": str(row["task_family"]),
            "depth": str(row["depth"]),
            "branch": branch,
            "condition": str(row["condition"]),
            "n": str(classification["sample_size"]),
            "minimum_n": str(classification["minimum_sample_size"]),
            "sample_size_sufficient": str(
                classification["sample_size_sufficient"]
            ),
            "classification": classification["classification"],
            "provisional": str(classification["classification_is_provisional"]),
            "absolute_accuracy_passed": str(
                classification["absolute_accuracy_passed"]
            ),
            "visible_cot_baseline_valid": str(classification["baseline_valid"]),
            "relative_accuracy_gate": relative_label,
            "criteria_passed": "; ".join(classification["criteria_passed"])
            or "NA",
            "criteria_failed": "; ".join(classification["criteria_failed"])
            or "NA",
            "criteria_not_applicable": "; ".join(
                classification["criteria_not_applicable"]
            )
            or "NA",
            "stop_string_distribution": stop_distributions.get(stop_key, "NA"),
        }
        classifications.append(
            {
                **rendered,
                "accuracy_raw": row.get("accuracy_raw"),
                "accuracy_postprocessed": row.get("accuracy_postprocessed"),
                "classification_detail": classification,
            }
        )
    return classifications


def _split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_summary_classification_table(summary: str) -> list[dict[str, str]]:
    """Extract the persisted branch-classification table from the summary."""
    lines = summary.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        header = _split_markdown_row(line)
        if not {
            "classification",
            "criteria_passed",
            "criteria_failed",
            "criteria_not_applicable",
        }.issubset(header):
            continue
        rows: list[dict[str, str]] = []
        for row_line in lines[index + 2 :]:
            if not row_line.lstrip().startswith("|"):
                break
            cells = _split_markdown_row(row_line)
            if len(cells) != len(header):
                raise AuditInputError("malformed summary classification row")
            rows.append(dict(zip(header, cells)))
        return rows
    raise AuditInputError("branch classification table not found in summary")


def compare_branch_classifications(
    summary: str,
    recomputed: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare persisted summary classifications and ordered criterion lists."""
    stored = parse_summary_classification_table(summary)
    key_fields = ("model", "task_family", "depth", "branch", "condition")
    compare_fields = (
        "classification",
        "n",
        "minimum_n",
        "sample_size_sufficient",
        "provisional",
        "absolute_accuracy_passed",
        "visible_cot_baseline_valid",
        "relative_accuracy_gate",
        "criteria_passed",
        "criteria_failed",
        "criteria_not_applicable",
        "stop_string_distribution",
    )
    stored_index: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in stored:
        stored_index[tuple(row[field] for field in key_fields)].append(row)
    mismatches: list[dict[str, Any]] = []
    expected_keys = {
        tuple(str(row[field]) for field in key_fields) for row in recomputed
    }
    if len(stored) != 9:
        mismatches.append(
            {
                "key": {},
                "field": "stored_classification_row_count",
                "stored": len(stored),
                "expected": 9,
            }
        )
    for row in recomputed:
        key = tuple(str(row[field]) for field in key_fields)
        candidates = stored_index.get(key, [])
        if len(candidates) != 1:
            mismatches.append(
                {
                    "key": dict(zip(key_fields, key)),
                    "field": "summary_row_multiplicity",
                    "stored": len(candidates),
                    "expected": 1,
                }
            )
            continue
        source = candidates[0]
        for field in compare_fields:
            if str(source.get(field)) != str(row.get(field)):
                mismatches.append(
                    {
                        "key": dict(zip(key_fields, key)),
                        "field": field,
                        "stored": source.get(field),
                        "recomputed": row.get(field),
                    }
                )
    for key, candidates in stored_index.items():
        if key not in expected_keys:
            mismatches.append(
                {
                    "key": dict(zip(key_fields, key)),
                    "field": "extra_summary_row",
                    "stored": len(candidates),
                    "expected": 0,
                }
            )
    d3 = next(
        (
            row
            for row in recomputed
            if row["branch"] == POSTPROCESSED_UTILITY_BRANCH
            and str(row["depth"]) == "3"
        ),
        None,
    )
    d3_detail = d3["classification_detail"] if d3 else {}
    d3_regression = bool(
        d3
        and float(d3.get("accuracy_raw")) == 0.0
        and float(d3.get("accuracy_postprocessed")) == 0.0
        and d3["classification"] == "postprocessed_surface_clean_but_task_failed"
        and d3_detail.get("absolute_accuracy_passed") is False
        and any(
            "accuracy_postprocessed >= accuracy_raw" in criterion
            for criterion in d3_detail.get("criteria_passed", [])
        )
    )
    if not d3_regression:
        mismatches.append(
            {"key": {"branch": POSTPROCESSED_UTILITY_BRANCH, "depth": 3}, "field": "d3_0_ge_0_regression"}
        )
    return {
        "stored_rows": len(stored),
        "recomputed_rows": len(recomputed),
        "classification_mismatches": sum(
            item["field"] == "classification" for item in mismatches
        ),
        "criteria_list_mismatches": sum(
            item["field"]
            in {"criteria_passed", "criteria_failed", "criteria_not_applicable"}
            for item in mismatches
        ),
        "mismatches": mismatches,
        "d3_zero_non_degradation_regression": (
            "PASS" if d3_regression else "FAIL"
        ),
        "result": "PASS" if not mismatches else "FAIL",
    }


def audit_summary_structure(summary: str) -> dict[str, Any]:
    """Check required summary sections without changing historical content."""
    present = [
        section
        for section in SUMMARY_SECTIONS
        if f"## {section}" in summary or f"# {section}" in summary
    ]
    missing = [section for section in SUMMARY_SECTIONS if section not in present]
    return {
        "summary_present": bool(summary.strip()),
        "sections_present": present,
        "sections_missing": missing,
        "result": "PASS" if not missing else "FAIL",
    }


def run_record_audit(
    generation_records: Sequence[Mapping[str, Any]],
    eval_records: Sequence[Mapping[str, Any]],
    stored_metric_rows: Sequence[Mapping[str, str]],
    summary: str,
    *,
    implementation_commit: str | None = None,
    expected_ambiguous_count: int = 18,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run all deterministic audits over already parsed source artifacts."""
    pairing, pairs = audit_pairing(generation_records, eval_records)
    generation_membership = audit_membership(generation_records)
    eval_membership = audit_membership(eval_records)
    fields = audit_field_consistency(pairs)
    transformations, transformation_by_key = audit_transformation_consistency(pairs)
    parser, mechanical = recompute_parser_fields(eval_records)
    for key, checks in mechanical.items():
        checks.update(transformation_by_key.get(key, {}))
    ambiguous, deterministic = build_ambiguous_audit_records(pairs, mechanical)
    recomputed_metrics, latency_limitations = recompute_metric_rows(pairs)
    metrics = compare_metric_rows(stored_metric_rows, recomputed_metrics)
    baselines = recompute_visible_cot_baselines(recomputed_metrics)
    classifications = recompute_branch_classifications(
        recomputed_metrics, generation_records
    )
    classification_comparison = compare_branch_classifications(
        summary, classifications
    )
    summary_structure = audit_summary_structure(summary)
    ambiguous_count_result = (
        "PASS" if len(ambiguous) == expected_ambiguous_count else "FAIL"
    )

    conclusive_failures = [
        pairing["result"],
        generation_membership["result"],
        eval_membership["result"],
        fields["result"],
        transformations["result"],
        parser["result"],
        metrics["result"],
        classification_comparison["result"],
        summary_structure["result"],
        ambiguous_count_result,
    ]
    completed_with_findings = any(status != "PASS" for status in conclusive_failures)
    report = {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "overall_status": (
            "completed_with_findings" if completed_with_findings else "completed_clean"
        ),
        "scope": {
            "mode": "read_only_model_free",
            "writer_source_commit": SOURCE_CODE_COMMIT,
            "audit_implementation_commit": implementation_commit,
            "source_modified": False,
            "model_inference_performed": False,
            "new_observations_generated": False,
        },
        "pairing": pairing,
        "membership": {
            "generation": generation_membership,
            "evaluation": eval_membership,
        },
        "field_consistency": fields,
        "transformation_consistency": transformations,
        "parser_recomputation": {
            **parser,
            "current_code_commit": implementation_commit,
            "current_parser_version": None,
        },
        "ambiguous_parse_audit": {
            "expected_ambiguous": expected_ambiguous_count,
            "actual_ambiguous": len(ambiguous),
            "count_result": ambiguous_count_result,
            "deterministic_review_only": True,
            "semantic_review_status": "pending_independent_review",
            "underflag_limitation": (
                "Reviewing only stored parse_ambiguous=true records cannot detect "
                "underflags among the other records."
            ),
        },
        "metrics_recomputation": {
            **metrics,
            "latency_limitations": latency_limitations,
        },
        "visible_cot_baselines": baselines,
        "branch_recomputation": {
            **classification_comparison,
            "classifications": classifications,
        },
        "summary_audit": summary_structure,
        "audit_limitations": [
            "LLM ambiguity adjudication is audit opinion, not human ground truth.",
            "Parser consistency does not establish semantic correctness.",
            "Artifact integrity does not establish the experiment conclusion.",
            "n=3 is the registered minimum evidence gate, not statistical stability.",
            "Stopped outputs remain intervention-controlled.",
            "Postprocessed outputs remain answer-recovery utility, not raw no-CoT.",
        ],
        "scientific_boundary": (
            "Artifact integrity and evaluator consistency only; no hidden-reasoning "
            "or J-space inference."
        ),
    }
    outputs = {
        "ambiguous_records": ambiguous,
        "ambiguous_deterministic_reviews": deterministic,
        "recomputed_metrics": recomputed_metrics,
        "recomputed_classifications": classifications,
        "pairing_mismatches": (
            pairing["duplicate_generation_keys"]
            + pairing["duplicate_eval_keys"]
            + pairing["generation_only_keys"]
            + pairing["eval_only_keys"]
            + fields["mismatches"]
            + transformations["mismatches"]
        ),
    }
    return report, outputs


def write_metric_rows(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write recomputed metrics with the historical column order."""
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: (
                        "UNVERIFIABLE"
                        if field == "avg_latency_s" and row.get(field) is None
                        else row.get(field)
                    )
                    for field in METRIC_COLUMNS
                }
            )


def write_json(path: str | Path, value: Any) -> None:
    """Write deterministic, human-readable JSON."""
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: str | Path, records: Iterable[Mapping[str, Any]]) -> None:
    """Write one JSON-safe object per line."""
    with Path(path).open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def render_audit_markdown(report: Mapping[str, Any]) -> str:
    """Render a concise deterministic audit report."""
    pairing = report["pairing"]
    membership = report["membership"]["evaluation"]
    fields = report["field_consistency"]
    transformations = report["transformation_consistency"]
    parser = report["parser_recomputation"]
    metrics = report["metrics_recomputation"]
    branches = report["branch_recomputation"]
    ambiguous = report["ambiguous_parse_audit"]
    lines = [
        "# Phase 1 n=3 Record-Level Audit",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Scope",
        "",
        "- Read-only, model-free audit of existing artifacts.",
        "- No source artifact was modified.",
        "- No new behavioral observation was generated.",
        "",
        "## Pairing and Membership",
        "",
        f"- Unique generation keys: {pairing['unique_generation_keys']}",
        f"- Unique eval keys: {pairing['unique_eval_keys']}",
        f"- Pairs checked: {pairing['pairs_checked']}",
        f"- Missing combinations: {len(membership['missing_combinations'])}",
        f"- Extra combinations: {len(membership['extra_combinations'])}",
        f"- Pairing result: `{pairing['result']}`",
        "",
        "## Field and Parser Consistency",
        "",
        f"- Mismatched pairs: {fields['mismatched_pairs']}",
        f"- Field result: `{fields['result']}`",
        f"- Transformation mismatches: {transformations['mismatch_count']}",
        f"- Transformation result: `{transformations['result']}`",
        f"- Parser mismatch fields: {sum(parser['all_mismatch_counts'].values())}",
        f"- Parser result: `{parser['result']}`",
        "",
        "## Ambiguous Parses",
        "",
        f"- Expected: {ambiguous['expected_ambiguous']}",
        f"- Actual: {ambiguous['actual_ambiguous']}",
        "- Independent reviewer adjudication is reported separately.",
        "",
        "## Metrics and Classifications",
        "",
        f"- Recomputed metric rows: {metrics['recomputed_rows']}",
        f"- Metric mismatching rows: {metrics['mismatching_rows']}",
        f"- Metric result: `{metrics['result']}`",
        f"- Classification mismatches: {branches['classification_mismatches']}",
        f"- Criteria-list mismatches: {branches['criteria_list_mismatches']}",
        f"- D3 0>=0 regression: `{branches['d3_zero_non_degradation_regression']}`",
        f"- Branch result: `{branches['result']}`",
        "",
        "## Scientific Boundaries",
        "",
        "- This audit evaluates artifact integrity and evaluator consistency only.",
        "- LLM adjudication is not human ground truth.",
        "- n=3 does not establish stability or generalizability.",
        "- Stopped outputs remain intervention-controlled.",
        "- Postprocessed outputs remain answer-recovery utility.",
        "- No hidden-reasoning or J-space claim is made.",
        "",
    ]
    return "\n".join(lines)
