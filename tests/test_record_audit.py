"""Tests for the model-free Phase 1 record-level audit."""

from __future__ import annotations

import sys
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.eval_parsing import create_eval_record
from jspace_observation.no_cot import STRICT_ANSWER_ONLY_STOP_STRINGS
from jspace_observation.phase1_branches import get_phase1_branch_metadata
from jspace_observation.record_audit import (
    AMBIGUOUS_SOURCE_FIELDS,
    AUDIT_OUTPUT_NAMES,
    AuditInputError,
    audit_field_consistency,
    audit_membership,
    audit_pairing,
    audit_transformation_consistency,
    build_ambiguous_audit_records,
    build_upload_plan,
    compare_branch_classifications,
    compare_metric_rows,
    expected_record_keys,
    parse_jsonl_bytes,
    parse_metrics_csv_bytes,
    recompute_branch_classifications,
    recompute_metric_rows,
    recompute_parser_fields,
    record_key,
    validate_audit_prefixes,
)


def _answer_by_task() -> dict[str, str]:
    return {
        "arith_1op_001": "12",
        "arith_1op_002": "15",
        "arith_1op_003": "24",
        "arith_2op_001": "16",
        "arith_2op_002": "16",
        "arith_2op_003": "4",
        "arith_3op_001": "18",
        "arith_3op_002": "34",
        "arith_3op_003": "26",
    }


def _fixture_records() -> tuple[list[dict], list[dict]]:
    generations = []
    evaluations = []
    answers = _answer_by_task()
    for model, task_family, depth, condition, task_id in expected_record_keys():
        answer = answers[task_id]
        branch = get_phase1_branch_metadata(condition)
        stopped = condition == "strict_answer_only_stopped"
        postprocessed = condition == "strict_answer_only_postprocessed"
        strict = condition.startswith("strict_answer_only")
        selected = "stopped" if stopped else "postprocessed" if postprocessed else "raw"
        evaluation = create_eval_record(
            output=answer,
            parse_type="numeric",
            expected_answer=answer,
            task_id=task_id,
            model_name=model,
            task_family=task_family,
            depth=depth,
            condition=condition,
            **branch,
        )
        evaluation.update(
            {
                "raw_correctness": True,
                "raw_parsed_answer": answer,
                "raw_parse_valid": True,
                "eval_output_used": selected,
                "eval_correctness": True,
                "stopped_correctness": True if stopped else None,
                "postprocessed_correctness": True if postprocessed else None,
                "stop_control_enabled": stopped,
                "stop_triggered": stopped,
                "stop_reason": "stop_string_matched" if stopped else None,
                "stop_string": "\n\n" if stopped else None,
                "stop_mode": "truncate_at_stop_string" if stopped else None,
                "stop_warning": None,
                "raw_output_before_stop_cleanup": answer,
                "raw_output": answer,
                "stopped_output": answer if stopped else None,
                "stopped_no_cot_valid": True if stopped else None,
                "raw_output_before_postprocess": answer,
                "postprocessed_output": answer if postprocessed else None,
                "postprocessing_applied": False,
                "postprocessing_strategy": "first_line" if postprocessed else None,
                "postprocessing_reason": (
                    "first_line_answer_like" if postprocessed else None
                ),
                "postprocessing_warning": None,
                "raw_no_cot_valid": True if strict else None,
                "postprocessed_no_cot_valid": True if postprocessed else None,
                "postprocessed_answer_like": True if postprocessed else None,
            }
        )
        generation = {
            "model_name": model,
            "task_family": task_family,
            "depth": depth,
            "condition": condition,
            "task_id": task_id,
            "prompt": f"Question for {task_id}",
            "ground_truth": answer,
            "output": answer,
            "raw_output": answer,
            "eval_output": answer,
            "eval_output_used": selected,
            "no_cot_applicable": strict,
            "no_cot_validity": True if strict else None,
            "generation_time_s": 1.0,
            "phase1_branch": branch["phase1_branch"],
            "stop_string": "\n\n" if stopped else None,
            "stop_strings": (
                list(STRICT_ANSWER_ONLY_STOP_STRINGS) if stopped else []
            ),
        }
        generations.append(generation)
        evaluations.append(evaluation)
    return generations, evaluations


def _classification_fixture() -> tuple[list[dict], str]:
    generations, evaluations = _fixture_records()
    _, pairs = audit_pairing(generations, evaluations)
    metrics, _ = recompute_metric_rows(pairs)
    for row in metrics:
        if row["depth"] == "3" and row["condition"] == "visible_cot":
            row["accuracy"] = "0.0000"
            row["eval_accuracy"] = "0.0000"
            row["accuracy_raw"] = "0.0000"
        if (
            row["depth"] == "3"
            and row["condition"] == "strict_answer_only_postprocessed"
        ):
            row["postprocessing_success_rate"] = "0.3333"
            row["postprocessing_warning_rate"] = "0.6667"
            row["accuracy"] = "0.0000"
            row["eval_accuracy"] = "0.0000"
            row["accuracy_raw"] = "0.0000"
            row["accuracy_postprocessed"] = "0.0000"
    classifications = recompute_branch_classifications(metrics, generations)
    fields = [
        "model",
        "task_family",
        "depth",
        "branch",
        "condition",
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
    ]
    header = "| " + " | ".join(fields) + " |"
    separator = "|" + "|".join("---" for _ in fields) + "|"
    rows = [
        "| " + " | ".join(str(row[field]) for field in fields) + " |"
        for row in classifications
    ]
    return classifications, "\n".join((header, separator, *rows))


def test_pairs_all_45_records_by_composite_key():
    generations, evaluations = _fixture_records()

    report, pairs = audit_pairing(generations, evaluations)

    assert report["result"] == "PASS"
    assert report["pairing_key_type"] == "composite"
    assert report["unique_generation_keys"] == 45
    assert report["unique_eval_keys"] == 45
    assert len(pairs) == 45


def test_duplicate_generation_key_is_reported():
    generations, evaluations = _fixture_records()
    generations.append(deepcopy(generations[0]))

    report, _ = audit_pairing(generations, evaluations)

    assert report["result"] == "FAIL"
    assert report["duplicate_generation_keys"][0]["count"] == 2


def test_duplicate_eval_key_is_reported():
    generations, evaluations = _fixture_records()
    evaluations.append(deepcopy(evaluations[0]))

    report, _ = audit_pairing(generations, evaluations)

    assert report["result"] == "FAIL"
    assert report["duplicate_eval_keys"][0]["count"] == 2


def test_generation_only_and_eval_only_keys_are_reported():
    generations, evaluations = _fixture_records()
    generations.pop()
    evaluations.pop(0)

    report, _ = audit_pairing(generations, evaluations)

    assert len(report["generation_only_keys"]) == 1
    assert len(report["eval_only_keys"]) == 1


def test_composite_key_uses_actual_registered_fields():
    generations, _ = _fixture_records()

    key = record_key(generations[0])

    assert key == (
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "arithmetic",
        1,
        "strict_answer_only_prefill_answer",
        "arith_1op_001",
    )


def test_pairing_key_rejects_boolean_depth():
    generations, _ = _fixture_records()
    generations[0]["depth"] = True

    with pytest.raises(AuditInputError):
        record_key(generations[0])


def test_pairing_reports_invalid_key_without_crashing_order_check():
    generations, evaluations = _fixture_records()
    generations[0]["depth"] = True

    report, pairs = audit_pairing(generations, evaluations)

    assert report["result"] == "FAIL"
    assert len(report["invalid_generation_keys"]) == 1
    assert len(pairs) == 44


def test_membership_reports_missing_condition_depth_item():
    generations, _ = _fixture_records()
    generations.pop()

    report = audit_membership(generations)

    assert report["result"] == "FAIL"
    assert report["actual_observations"] == 44
    assert len(report["missing_combinations"]) == 1


def test_membership_rejects_extra_model_task_depth_and_condition():
    generations, _ = _fixture_records()
    extra = deepcopy(generations[0])
    extra.update(
        {
            "model_name": "extra-model",
            "task_family": "extra-task",
            "depth": 9,
            "condition": "extra-condition",
        }
    )
    generations.append(extra)

    report = audit_membership(generations)

    assert report["result"] == "FAIL"
    assert "extra-model" in report["actual_models"]
    assert len(report["extra_combinations"]) == 1


def test_membership_validates_registered_expected_answer():
    generations, evaluations = _fixture_records()
    generations[0]["ground_truth"] = "999"
    evaluations[0]["expected_answer"] = "999"

    generation_report = audit_membership(generations)
    eval_report = audit_membership(evaluations)

    assert generation_report["result"] == "FAIL"
    assert eval_report["result"] == "FAIL"
    assert generation_report["registered_answer_mismatches"][0]["expected"] == "12"


def test_common_field_mismatch_distinguishes_values():
    generations, evaluations = _fixture_records()
    generations[0]["parsed_answer"] = "12"
    evaluations[0]["parsed_answer"] = "13"
    _, pairs = audit_pairing(generations[:1], evaluations[:1])

    report = audit_field_consistency(pairs)

    assert report["result"] == "FAIL"
    assert report["mismatched_fields"]["generation.parsed_answer"] == 1


def test_invalid_jsonl_and_duplicate_member_are_not_repaired():
    data = b'{"ok": 1}\nnot-json\n{"dup": 1, "dup": 2}\n'

    report = parse_jsonl_bytes(data, "test.jsonl")

    assert report["valid_records"] == 1
    assert report["parse_status"] == "FAIL"
    assert [item["line"] for item in report["invalid_lines"]] == [2, 3]


def test_blank_jsonl_line_is_a_syntax_failure():
    report = parse_jsonl_bytes(b'{"ok": 1}\n\n{"ok": 2}\n', "test.jsonl")

    assert report["valid_records"] == 2
    assert report["blank_lines"] == 1
    assert report["parse_status"] == "FAIL"


def test_empty_jsonl_is_a_syntax_failure():
    report = parse_jsonl_bytes(b"", "empty.jsonl")

    assert report["valid_records"] == 0
    assert report["parse_status"] == "FAIL"
    assert report["invalid_lines"][0]["error"] == "JSONL must contain at least one record"


def test_malformed_and_blank_csv_rows_are_rejected():
    malformed = (
        ",".join(
            (
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
        )
        + '\n"unterminated'
    ).encode()

    malformed_report = parse_metrics_csv_bytes(malformed)

    assert malformed_report["parse_status"] == "FAIL"


def test_metrics_recomputation_matches_15_cells():
    generations, evaluations = _fixture_records()
    _, pairs = audit_pairing(generations, evaluations)

    rows, limitations = recompute_metric_rows(pairs)
    comparison = compare_metric_rows(deepcopy(rows), rows)

    assert len(rows) == 15
    assert {row["n"] for row in rows} == {"3"}
    assert limitations == []
    assert comparison["result"] == "PASS"
    assert comparison["matching_rows"] == 15


def test_metric_tolerance_accepts_exact_boundary_and_rejects_excess():
    generations, evaluations = _fixture_records()
    _, pairs = audit_pairing(generations, evaluations)
    rows, _ = recompute_metric_rows(pairs)
    stored = deepcopy(rows)
    stored[0]["accuracy"] = "1.0001"

    boundary = compare_metric_rows(stored, rows, tolerance=1e-4)

    assert boundary["result"] == "PASS"
    stored[0]["accuracy"] = "1.0002"
    excess = compare_metric_rows(stored, rows, tolerance=1e-4)
    assert excess["result"] == "FAIL"
    assert "accuracy" in excess["mismatching_fields"]


def test_ambiguous_selector_emits_exact_flagged_records():
    generations, evaluations = _fixture_records()
    for index in range(18):
        answer = evaluations[index]["expected_answer"]
        replay = create_eval_record(
            output=f"First, 1. Therefore {answer}.",
            parse_type="numeric",
            expected_answer=answer,
        )
        evaluations[index].update(replay)
        evaluations[index]["raw_output"] = replay["output"]
        evaluations[index]["raw_output_before_stop_cleanup"] = replay["output"]
        evaluations[index]["raw_output_before_postprocess"] = replay["output"]
        evaluations[index]["raw_parsed_answer"] = replay["parsed_answer"]
        evaluations[index]["raw_parse_valid"] = replay["parse_valid"]
        evaluations[index]["raw_correctness"] = replay["correctness"]
        evaluations[index]["eval_correctness"] = replay["correctness"]
        assert evaluations[index]["parse_ambiguous"] is True
    _, pairs = audit_pairing(generations, evaluations)
    _, mechanical = recompute_parser_fields(evaluations)

    records, reviews = build_ambiguous_audit_records(pairs, mechanical)

    assert len(records) == 18
    assert len(reviews) == 18
    assert all(set(record["source"]) == set(AMBIGUOUS_SOURCE_FIELDS) for record in records)


def test_parser_alias_mismatch_cannot_report_pass():
    _, evaluations = _fixture_records()
    evaluations[0]["eval_correctness"] = False

    report, _ = recompute_parser_fields(evaluations)

    assert report["result"] == "FAIL"
    assert report["all_mismatch_counts"]["eval_correctness"] == 1
    assert any(
        item["field"] == "eval_correctness"
        for item in report["mismatch_details"]
    )


def test_selected_output_derivation_is_recomputed():
    generations, evaluations = _fixture_records()
    _, pairs = audit_pairing(generations, evaluations)

    clean, _ = audit_transformation_consistency(pairs)

    assert clean["result"] == "PASS"
    stopped_index = next(
        index
        for index, record in enumerate(evaluations)
        if record["condition"] == "strict_answer_only_stopped"
    )
    generations[stopped_index]["stopped_output"] = "999"
    evaluations[stopped_index]["stopped_output"] = "999"
    _, changed_pairs = audit_pairing(generations, evaluations)
    changed, _ = audit_transformation_consistency(changed_pairs)
    assert changed["result"] == "FAIL"
    assert changed["mismatched_fields"]["stopped_output"] == 1


def test_depth3_zero_non_degradation_remains_task_failed():
    visible = {
        "model": "m",
        "task_family": "arithmetic",
        "depth": "3",
        "condition": "visible_cot",
        "branch": "visible_reasoning_baseline",
        "n": "3",
        "accuracy_raw": "0.0000",
        "parse_valid_rate": "1.0000",
        "answer_format_warning_rate": "1.0000",
    }
    postprocessed = {
        "model": "m",
        "task_family": "arithmetic",
        "depth": "3",
        "condition": "strict_answer_only_postprocessed",
        "branch": "postprocessed_utility",
        "n": "3",
        "postprocessed_no_cot_valid_rate": "1.0000",
        "postprocessing_success_rate": "0.3333",
        "postprocessing_warning_rate": "0.6667",
        "accuracy_raw": "0.0000",
        "accuracy_postprocessed": "0.0000",
    }

    rows = recompute_branch_classifications([postprocessed, visible], [])

    assert rows[0]["classification"] == "postprocessed_surface_clean_but_task_failed"
    detail = rows[0]["classification_detail"]
    assert detail["absolute_accuracy_passed"] is False
    assert detail["relative_accuracy_gate_passed"] is None
    assert detail["classification_is_provisional"] is False


def test_summary_classification_comparison_checks_criteria_order():
    recomputed, summary = _classification_fixture()

    comparison = compare_branch_classifications(summary, recomputed)

    assert comparison["result"] == "PASS"
    assert comparison["d3_zero_non_degradation_regression"] == "PASS"


def test_summary_duplicate_classification_row_is_rejected():
    recomputed, summary = _classification_fixture()
    duplicate_row = summary.splitlines()[2]

    comparison = compare_branch_classifications(
        f"{summary}\n{duplicate_row}",
        recomputed,
    )

    assert comparison["result"] == "FAIL"
    assert any(
        item["field"] in {"stored_classification_row_count", "summary_row_multiplicity"}
        for item in comparison["mismatches"]
    )


def test_d3_regression_requires_both_accuracies_to_be_zero():
    recomputed, summary = _classification_fixture()
    d3 = next(
        row
        for row in recomputed
        if row["branch"] == "postprocessed_utility" and row["depth"] == "3"
    )
    d3["accuracy_raw"] = "0.3000"
    d3["accuracy_postprocessed"] = "0.4000"

    comparison = compare_branch_classifications(summary, recomputed)

    assert comparison["d3_zero_non_degradation_regression"] == "FAIL"
    assert comparison["result"] == "FAIL"


def test_source_and_audit_prefixes_must_be_isolated():
    source = "phase1-limited-n3-gates/20260710T152820Z"

    validate_audit_prefixes(
        source,
        "phase1-audits/n3-gates-20260710T152820Z/20260711T000000Z",
    )
    with pytest.raises(AuditInputError):
        validate_audit_prefixes(source, source)
    with pytest.raises(AuditInputError):
        validate_audit_prefixes(source, f"{source}/audit")
    with pytest.raises(AuditInputError):
        validate_audit_prefixes(f"phase1-audits/{source}", "phase1-audits")


def test_upload_plan_never_targets_source_artifact_names():
    prefix = "phase1-audits/n3/run"

    plan = build_upload_plan(prefix)

    assert len(plan) == len(AUDIT_OUTPUT_NAMES)
    assert all(name.startswith(f"{prefix}/") for name in plan)
    assert all("phase1-limited-n3-gates" not in name for name in plan)


def test_azure_helper_passes_cpu_audit_environment_variables():
    script = (
        Path(__file__).parent.parent
        / "infra"
        / "azure"
        / "scripts"
        / "06_run_job_acr_mi.sh"
    ).read_text(encoding="utf-8")

    assert 'JSPACE_AUDIT_SOURCE_PREFIX="${JSPACE_AUDIT_SOURCE_PREFIX:-}"' in script
    assert 'JSPACE_AUDIT_OUTPUT_PREFIX="${JSPACE_AUDIT_OUTPUT_PREFIX:-}"' in script
    assert '"JSPACE_AUDIT_IMPLEMENTATION_COMMIT": audit_implementation_commit' in script
    assert 'echo "Workload profile: ${WORKLOAD_PROFILE_NAME}"' in script
    assert "Audit mode requires an explicit non-GPU WORKLOAD_PROFILE_NAME" in script


def test_audit_cli_bootstraps_src_path_for_direct_invocation():
    root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "audit_phase1_blob_run.py"), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--source-prefix" in result.stdout
