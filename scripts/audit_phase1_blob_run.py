#!/usr/bin/env python3
"""Audit an existing Phase 1 Blob run without invoking a model."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from jspace_observation.record_audit import (
    AUDIT_OUTPUT_NAMES,
    SOURCE_ARTIFACT_NAMES,
    build_upload_plan,
    parse_jsonl_bytes,
    parse_metrics_csv_bytes,
    render_audit_markdown,
    run_record_audit,
    sha256_bytes,
    validate_audit_prefixes,
    write_json,
    write_jsonl,
    write_metric_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-account", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--source-prefix", required=True)
    parser.add_argument("--audit-output-prefix", required=True)
    parser.add_argument("--download-dir", required=True)
    parser.add_argument("--require-exact-generation-count", type=int, required=True)
    parser.add_argument("--require-exact-eval-count", type=int, required=True)
    parser.add_argument("--expected-items-per-cell", type=int, required=True)
    parser.add_argument("--emit-ambiguous-records", action="store_true")
    parser.add_argument("--upload-audit-report", action="store_true")
    return parser.parse_args()


def _current_commit() -> str | None:
    configured = os.getenv("JSPACE_AUDIT_IMPLEMENTATION_COMMIT")
    if configured:
        return configured
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _parser_changed_from_source() -> bool | None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "359643b7b5eb8f95c13cca2e60fa753df8701282",
            "HEAD",
            "--",
            "src/jspace_observation/eval_parsing.py",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return False
    if result.returncode == 1:
        return True
    return None


def _property_snapshot(properties: Any) -> dict[str, Any]:
    return {
        "content_length": int(properties.size),
        "etag": str(properties.etag),
        "last_modified": (
            properties.last_modified.isoformat()
            if properties.last_modified is not None
            else None
        ),
        "version_id": getattr(properties, "version_id", None),
    }


def _download_sources(
    service: BlobServiceClient,
    container: str,
    source_prefix: str,
    source_dir: Path,
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    source_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, bytes] = {}
    manifest: list[dict[str, Any]] = []
    for name in SOURCE_ARTIFACT_NAMES:
        blob_name = f"{source_prefix.strip('/')}/{name}"
        blob = service.get_blob_client(container=container, blob=blob_name)
        before = _property_snapshot(blob.get_blob_properties())
        data = blob.download_blob(max_concurrency=1).readall()
        if len(data) != before["content_length"]:
            raise RuntimeError(
                f"downloaded byte count differs from Blob properties: {blob_name}"
            )
        local_path = source_dir / name
        local_path.write_bytes(data)
        artifacts[name] = data
        manifest.append(
            {
                "blob_name": blob_name,
                **before,
                "sha256": sha256_bytes(data),
                "local_file": str(local_path),
            }
        )
    return artifacts, manifest


def _confirm_sources_unchanged(
    service: BlobServiceClient,
    container: str,
    manifest: list[dict[str, Any]],
) -> bool:
    unchanged = True
    for entry in manifest:
        blob = service.get_blob_client(
            container=container,
            blob=entry["blob_name"],
        )
        after = _property_snapshot(blob.get_blob_properties())
        entry["after_audit"] = after
        entry["unchanged"] = all(
            entry.get(field) == after.get(field)
            for field in ("content_length", "etag", "last_modified", "version_id")
        )
        unchanged = unchanged and entry["unchanged"]
    return unchanged


def _upload_outputs(
    service: BlobServiceClient,
    container: str,
    output_dir: Path,
    audit_output_prefix: str,
) -> list[str]:
    planned = build_upload_plan(audit_output_prefix)
    uploaded: list[str] = []
    for name, blob_name in zip(AUDIT_OUTPUT_NAMES, planned):
        local_path = output_dir / name
        if not local_path.is_file():
            raise FileNotFoundError(f"audit output missing: {local_path}")
        blob = service.get_blob_client(container=container, blob=blob_name)
        with local_path.open("rb") as handle:
            blob.upload_blob(handle, overwrite=False)
        uploaded.append(blob_name)
        print(f"Uploaded audit blob: {blob_name}")
    return uploaded


def _print_marker(name: str, value: Any) -> None:
    print(f"=== {name} ===")
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def main() -> int:
    args = parse_args()
    validate_audit_prefixes(args.source_prefix, args.audit_output_prefix)
    if args.expected_items_per_cell != 3:
        raise ValueError("this registered audit requires exactly 3 items per cell")

    client_id = os.getenv("AZURE_CLIENT_ID")
    credential = DefaultAzureCredential(
        managed_identity_client_id=client_id or None
    )
    service = BlobServiceClient(
        account_url=f"https://{args.storage_account}.blob.core.windows.net",
        credential=credential,
    )
    root = Path(args.download_dir)
    source_dir = root / "source"
    output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts, source_manifest = _download_sources(
        service,
        args.container,
        args.source_prefix,
        source_dir,
    )
    generation_parse = parse_jsonl_bytes(
        artifacts["phase1_generations.jsonl"],
        "phase1_generations.jsonl",
    )
    eval_parse = parse_jsonl_bytes(
        artifacts["phase1_eval_records.jsonl"],
        "phase1_eval_records.jsonl",
    )
    metrics_parse = parse_metrics_csv_bytes(artifacts["phase1_metrics.csv"])
    summary = artifacts["phase1_summary.md"].decode("utf-8")
    if generation_parse["parse_status"] != "PASS":
        raise RuntimeError("generation JSONL contains invalid source lines")
    if eval_parse["parse_status"] != "PASS":
        raise RuntimeError("eval JSONL contains invalid source lines")
    if metrics_parse["parse_status"] != "PASS":
        raise RuntimeError("metrics CSV violates the registered source schema")

    implementation_commit = _current_commit()
    report, outputs = run_record_audit(
        generation_parse["records"],
        eval_parse["records"],
        metrics_parse["rows"],
        summary,
        implementation_commit=implementation_commit,
    )
    count_findings = []
    if generation_parse["valid_records"] != args.require_exact_generation_count:
        count_findings.append(
            {
                "artifact": "phase1_generations.jsonl",
                "expected": args.require_exact_generation_count,
                "actual": generation_parse["valid_records"],
            }
        )
    if eval_parse["valid_records"] != args.require_exact_eval_count:
        count_findings.append(
            {
                "artifact": "phase1_eval_records.jsonl",
                "expected": args.require_exact_eval_count,
                "actual": eval_parse["valid_records"],
            }
        )
    if count_findings:
        report["overall_status"] = "completed_with_findings"

    source_unchanged = _confirm_sources_unchanged(
        service,
        args.container,
        source_manifest,
    )
    if not source_unchanged:
        report["overall_status"] = "completed_with_findings"
    report["scope"].update(
        {
            "storage_account": args.storage_account,
            "container": args.container,
            "source_prefix": args.source_prefix.strip("/"),
            "audit_output_prefix": args.audit_output_prefix.strip("/"),
            "source_modified": not source_unchanged,
        }
    )
    report["source_syntax_count_audit"] = {
        "generation_physical_lines": generation_parse["physical_lines"],
        "valid_generation_records": generation_parse["valid_records"],
        "invalid_generation_lines": generation_parse["invalid_lines"],
        "eval_physical_lines": eval_parse["physical_lines"],
        "valid_eval_records": eval_parse["valid_records"],
        "invalid_eval_lines": eval_parse["invalid_lines"],
        "metrics_rows": len(metrics_parse["rows"]),
        "summary_present": bool(summary.strip()),
        "exact_count_findings": count_findings,
    }
    report["parser_recomputation"]["source_current_parser_code_changed"] = (
        _parser_changed_from_source()
    )
    report["source_immutability"] = {
        "confirmed_unchanged": source_unchanged,
        "comparison_fields": [
            "content_length",
            "etag",
            "last_modified",
            "version_id",
        ],
    }

    manifest = {
        "audit_schema_version": report["audit_schema_version"],
        "audit_implementation_commit": implementation_commit,
        "storage_account": args.storage_account,
        "container": args.container,
        "source_prefix": args.source_prefix.strip("/"),
        "audit_output_prefix": args.audit_output_prefix.strip("/"),
        "source_artifacts": source_manifest,
        "source_unchanged": source_unchanged,
        "planned_output_blobs": build_upload_plan(args.audit_output_prefix),
        "model_inference_performed": False,
        "new_observations_generated": False,
    }
    for entry in source_manifest:
        name = Path(entry["blob_name"]).name
        if name == "phase1_generations.jsonl":
            entry["line_count"] = generation_parse["physical_lines"]
            entry["parse_status"] = generation_parse["parse_status"]
        elif name == "phase1_eval_records.jsonl":
            entry["line_count"] = eval_parse["physical_lines"]
            entry["parse_status"] = eval_parse["parse_status"]
        elif name == "phase1_metrics.csv":
            entry["line_count"] = metrics_parse["physical_rows"]
            entry["parse_status"] = metrics_parse["parse_status"]
        else:
            entry["line_count"] = len(summary.splitlines())
            entry["parse_status"] = "PASS"

    write_json(output_dir / "record_audit_manifest.json", manifest)
    write_json(output_dir / "record_audit_report.json", report)
    (output_dir / "record_audit_report.md").write_text(
        render_audit_markdown(report),
        encoding="utf-8",
    )
    write_jsonl(
        output_dir / "record_pairing_mismatches.jsonl",
        outputs["pairing_mismatches"],
    )
    write_jsonl(
        output_dir / "ambiguous_parse_records.jsonl",
        outputs["ambiguous_records"],
    )
    write_jsonl(
        output_dir / "ambiguous_parse_deterministic_review.jsonl",
        outputs["ambiguous_deterministic_reviews"],
    )
    write_metric_rows(
        output_dir / "recomputed_metrics.csv",
        outputs["recomputed_metrics"],
    )
    write_json(
        output_dir / "recomputed_branch_classifications.json",
        outputs["recomputed_classifications"],
    )

    _print_marker("AUDIT MANIFEST", manifest)
    _print_marker("PAIRING AUDIT", report["pairing"])
    _print_marker("MEMBERSHIP AUDIT", report["membership"])
    _print_marker("FIELD CONSISTENCY AUDIT", report["field_consistency"])
    _print_marker("METRICS RECOMPUTATION", report["metrics_recomputation"])
    _print_marker("BRANCH RECOMPUTATION", report["branch_recomputation"])
    if args.emit_ambiguous_records:
        print("=== AMBIGUOUS RECORDS BEGIN ===")
        for record in outputs["ambiguous_records"]:
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
        print("=== AMBIGUOUS RECORDS END ===")

    uploaded: list[str] = []
    if args.upload_audit_report:
        uploaded = _upload_outputs(
            service,
            args.container,
            output_dir,
            args.audit_output_prefix,
        )
    _print_marker(
        "AUDIT FINAL STATUS",
        {
            "overall_status": report["overall_status"],
            "source_unchanged": source_unchanged,
            "uploaded_files": uploaded,
            "model_inference_performed": False,
            "new_observations_generated": False,
        },
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("=== AUDIT FINAL STATUS ===")
        print(
            json.dumps(
                {
                    "overall_status": "tool_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "model_inference_performed": False,
                    "new_observations_generated": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        raise
