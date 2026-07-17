#!/usr/bin/env python3
"""Recoverable F0-F5 runner for the pinned Phase 0.5A J-lens feasibility gate."""

from __future__ import annotations

import argparse
import csv
import importlib
import importlib.metadata
import inspect
import json
import math
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = PROJECT_ROOT / "src" / "jspace_observation"
sys.path.insert(0, str(HELPER_ROOT))

import phase05_jlens as protocol  # noqa: E402

F2_PROMPT = (
    "A field technician reviews a calibration table before starting the test, "
    "records each measurement in sequence, compares the final values with the "
    "documented tolerances, and asks a second technician to verify anomalies."
)
SANITY_PROMPTS = (
    {
        "id": "sanity-entity-completion",
        "category": "entity_completion",
        "text": "The chemical symbol used for the element gold is",
    },
    {
        "id": "sanity-single-step-concept",
        "category": "single_step_concept",
        "text": "When liquid water freezes, its physical state becomes",
    },
    {
        "id": "sanity-technical-order",
        "category": "technical_sequence",
        "text": "In an ascending sorted sequence, the item after the minimum value is",
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, protocol.canonical_json_bytes(value))


def atomic_torch_save(torch_module: Any, value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    torch_module.save(value, temporary)
    os.replace(temporary, path)


def safe_error(error: BaseException) -> str:
    message = re.sub(r"(?i)(sig|token|secret|password)=\S+", r"\1=<redacted>", str(error))
    return message[:2000]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_corpus(path: Path) -> tuple[list[dict[str, str]], str]:
    records: list[dict[str, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        record = json.loads(raw)
        if set(record) != {"id", "text"}:
            raise protocol.Phase05ValidationError(
                f"corpus line {line_number} must contain only id/text"
            )
        if not all(isinstance(record[key], str) and record[key].strip() for key in record):
            raise protocol.Phase05ValidationError(
                f"corpus line {line_number} contains an empty value"
            )
        lowered = f"{record['id']} {record['text']}".lower()
        if any(
            term in lowered
            for term in (
                "phase1",
                "phase 1",
                "evaluator",
                "locked",
                "reference answer",
                "answer-only",
            )
        ):
            raise protocol.Phase05ValidationError("corpus contains a forbidden fixture cue")
        records.append({"id": record["id"], "text": record["text"]})
    if not 2 <= len(records) <= 5:
        raise protocol.Phase05ValidationError("fit corpus must contain 2-5 prompts")
    if len({record["id"] for record in records}) != len(records):
        raise protocol.Phase05ValidationError("fit corpus IDs must be unique")
    return records, protocol.canonical_jsonl_sha256(records)


class BlobTransport:
    """Managed-identity-only snapshot transport, imported lazily."""

    def __init__(self, run_prefix: str, attempt_id: str) -> None:
        self.account = os.getenv("JSPACE_BLOB_ACCOUNT", "").strip()
        self.container = os.getenv("JSPACE_BLOB_CONTAINER", "").strip()
        self.run_prefix = run_prefix.strip("/")
        self.attempt_id = attempt_id
        self.client_id = os.getenv("AZURE_CLIENT_ID", "").strip() or None
        self._container_client: Any = None
        protocol.validate_blob_auth_config(
            {
                "credential_mode": "default_credential_managed_identity_only",
                "managed_identity_client_id": self.client_id,
                "account": self.account,
                "container": self.container,
            }
        )

    @property
    def configured(self) -> bool:
        return bool(self.account and self.container)

    def _client(self) -> Any:
        if self._container_client is not None:
            return self._container_client
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        credential = DefaultAzureCredential(
            managed_identity_client_id=self.client_id,
            exclude_environment_credential=True,
            exclude_workload_identity_credential=True,
            exclude_shared_token_cache_credential=True,
            exclude_visual_studio_code_credential=True,
            exclude_cli_credential=True,
            exclude_powershell_credential=True,
            exclude_developer_cli_credential=True,
            exclude_interactive_browser_credential=True,
            exclude_broker_credential=True,
        )
        service = BlobServiceClient(
            account_url=f"https://{self.account}.blob.core.windows.net",
            credential=credential,
        )
        self._container_client = service.get_container_client(self.container)
        return self._container_client

    def restore_latest_snapshot(self, output_dir: Path, resume_prefix: str) -> dict[str, Any]:
        if not self.configured:
            raise protocol.CheckpointValidationError(
                "Blob resume requested without account/container configuration"
            )
        prefix = resume_prefix.strip("/")
        client = self._client()
        available = list(client.list_blobs(name_starts_with=prefix))
        candidates = []
        for blob in available:
            if (
                not blob.name.endswith("/phase05_jlens_stage_results.json")
                or "/snapshots/" not in blob.name
            ):
                continue
            snapshot_prefix = blob.name.rsplit("/", 1)[0] + "/"
            members = [
                member for member in available if member.name.startswith(snapshot_prefix)
            ]
            manifests = [
                member
                for member in members
                if member.name
                == snapshot_prefix + "phase05_jlens_artifact_manifest.json"
            ]
            if not manifests:
                continue
            manifest_blob = manifests[0]
            if any(
                member.last_modified > manifest_blob.last_modified
                for member in members
            ):
                continue
            candidates.append((blob, manifest_blob))
        if not candidates:
            raise protocol.CheckpointValidationError(
                f"no manifest-complete recoverable stage snapshot exists under {prefix}"
            )
        selected, selected_manifest = max(
            candidates, key=lambda item: item[1].last_modified
        )
        snapshot_prefix = selected.name.rsplit("/", 1)[0] + "/"
        restored = 0
        for blob in client.list_blobs(name_starts_with=snapshot_prefix):
            relative = blob.name[len(snapshot_prefix) :]
            relative_path = Path(relative)
            if not relative or relative_path.is_absolute() or ".." in relative_path.parts:
                raise protocol.CheckpointValidationError("unsafe Blob snapshot path")
            destination = output_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(destination, client.download_blob(blob.name).readall())
            restored += 1
        restored_manifest = read_json(
            output_dir / "phase05_jlens_artifact_manifest.json"
        )
        if (
            restored_manifest.get("schema_version")
            != "phase05-jlens-artifact-manifest-v1"
        ):
            raise protocol.CheckpointValidationError(
                "restored artifact manifest schema is invalid"
            )
        for artifact in restored_manifest.get("artifacts", []):
            relative_path = Path(str(artifact.get("path", "")))
            if (
                relative_path.is_absolute()
                or ".." in relative_path.parts
                or not relative_path.parts
            ):
                raise protocol.CheckpointValidationError(
                    "restored artifact manifest contains an unsafe path"
                )
            artifact_path = output_dir / relative_path
            if (
                not artifact_path.is_file()
                or artifact_path.stat().st_size != artifact.get("bytes")
                or protocol.sha256_file(artifact_path) != artifact.get("sha256")
            ):
                raise protocol.CheckpointValidationError(
                    f"restored artifact failed manifest validation: {relative_path}"
                )
        return {
            "status": "restored",
            "source_prefix": snapshot_prefix.rstrip("/"),
            "files": restored,
            "manifest_last_modified": selected_manifest.last_modified.isoformat(),
            "manifest_completion_verified": True,
        }

    def upload_snapshot(self, output_dir: Path, stage: str, sequence: int) -> dict[str, Any]:
        if not self.configured:
            return {"status": "not_configured", "uploaded": 0}
        destination = self.snapshot_destination(stage, sequence)
        files = self.snapshot_files(output_dir)
        client = self._client()
        uploaded = []
        for path in files:
            relative = path.relative_to(output_dir).as_posix()
            blob_name = f"{destination}/{relative}"
            with path.open("rb") as handle:
                client.upload_blob(name=blob_name, data=handle, overwrite=False)
            uploaded.append(blob_name)
        return {
            "status": "uploaded",
            "uploaded": len(uploaded),
            "prefix": destination,
            "manifest_uploaded_last": bool(
                uploaded
                and uploaded[-1].endswith("phase05_jlens_artifact_manifest.json")
            ),
        }

    def snapshot_destination(self, stage: str, sequence: int) -> str:
        return (
            f"{self.run_prefix}/attempts/{self.attempt_id}/snapshots/"
            f"{sequence:02d}-{stage}"
        )

    @staticmethod
    def snapshot_files(output_dir: Path) -> list[Path]:
        return sorted(
            (
                path
                for path in output_dir.rglob("*")
                if path.is_file()
                and not any(
                    part.startswith(".")
                    for part in path.relative_to(output_dir).parts
                )
                and ".tmp." not in path.name
            ),
            key=lambda path: (
                path.name == "phase05_jlens_artifact_manifest.json",
                path.relative_to(output_dir).as_posix(),
            ),
        )


class Phase05Runner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.output_dir = Path(args.output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.started_monotonic = time.monotonic()
        self.run_id = os.getenv("JSPACE_PHASE05_RUN_ID", "").strip() or utc_stamp()
        self.attempt_id = os.getenv("JSPACE_ATTEMPT_ID", "primary").strip()
        prefix = os.getenv("JSPACE_BLOB_PREFIX", "").strip()
        self.blob_prefix = prefix or f"phase05-jlens-feasibility/{self.run_id}"
        self.blob = BlobTransport(self.blob_prefix, self.attempt_id)
        self.snapshot_sequence = 0
        self.restore_record: dict[str, Any] | None = None
        self.restore_error: dict[str, str] | None = None
        self.upload_history: list[dict[str, Any]] = []

        results_path = self.output_dir / "phase05_jlens_stage_results.json"
        resume_prefix = os.getenv("JSPACE_BLOB_RESUME_PREFIX", "").strip()
        if args.resume and not results_path.exists() and resume_prefix:
            try:
                self.restore_record = self.blob.restore_latest_snapshot(
                    self.output_dir, resume_prefix
                )
            except Exception as error:
                self.restore_error = {
                    "error_type": type(error).__name__,
                    "error": safe_error(error),
                }
                self.restore_record = {
                    "status": "restore_failed",
                    **self.restore_error,
                    "source_prefix": resume_prefix,
                }

        self.results: dict[str, dict[str, Any]] = {}
        self.metrics: list[dict[str, str]] = []
        self.scaling_plan: dict[str, Any] | None = None
        self.environment: dict[str, Any] = {
            "schema_version": "phase05-jlens-environment-v1",
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "created_at_utc": utc_now(),
            "tooling_state": "UNRATED",
            "protocol": {
                "official_repository": protocol.OFFICIAL_REPOSITORY,
                "official_commit": protocol.OFFICIAL_COMMIT,
                "official_uv_lock_sha256": protocol.OFFICIAL_UV_LOCK_SHA256,
                "model_id": protocol.MODEL_ID,
                "model_revision": protocol.MODEL_REVISION,
                "runtime_dtype": protocol.RUNTIME_DTYPE,
                "platform_timeout_seconds": protocol.PLATFORM_TIMEOUT_SECONDS,
                "application_watchdog_seconds": protocol.APPLICATION_WATCHDOG_SECONDS,
                "planning_budget_seconds": protocol.PLANNING_BUDGET_SECONDS,
            },
            "blob": {
                "configured": self.blob.configured,
                "run_prefix": self.blob_prefix,
                "attempt_id": self.attempt_id,
                "credential_mode": "default_credential_managed_identity_only",
                "restore": self.restore_record,
                "upload_history": self.upload_history,
            },
        }
        self._load_resume_state()
        self.prior_success = {
            stage for stage, result in self.results.items() if result.get("status") == "success"
        }

        self.torch: Any = None
        self.jlens: Any = None
        self.transformers: Any = None
        self.hf_config: Any = None
        self.hf_model: Any = None
        self.tokenizer: Any = None
        self.lens_model: Any = None
        self.fitted_lens: Any = None
        self.loaded_lens: Any = None
        self.layers: dict[str, Any] | None = None
        self.corpus_records: list[dict[str, str]] = []
        self.corpus_sha256 = ""

    def _load_resume_state(self) -> None:
        if not self.args.resume:
            return
        stage_path = self.output_dir / "phase05_jlens_stage_results.json"
        environment_path = self.output_dir / "phase05_jlens_environment.json"
        metrics_path = self.output_dir / "phase05_jlens_metrics.csv"
        if stage_path.exists():
            saved = read_json(stage_path)
            if saved.get("schema_version") != "phase05-jlens-stage-results-v1":
                raise protocol.CheckpointValidationError("saved stage schema is invalid")
            self.results = dict(saved.get("stages", {}))
            self.scaling_plan = saved.get("scaling_plan")
        if environment_path.exists():
            previous = read_json(environment_path)
            self.environment["resumed_from_run_id"] = previous.get("run_id")
            previous_attempt = previous.get("attempt_id")
            for record in previous.get("blob", {}).get("upload_history", []):
                carried = dict(record)
                if previous_attempt != self.attempt_id:
                    carried["required"] = False
                    carried["carried_from_attempt"] = previous_attempt
                self.upload_history.append(carried)
            self.snapshot_sequence = max(
                (
                    int(record.get("sequence", 0))
                    for record in self.upload_history
                    if record.get("attempt_id") == self.attempt_id
                ),
                default=self.snapshot_sequence,
            )
        if metrics_path.exists():
            with metrics_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if tuple(reader.fieldnames or ()) != protocol.METRICS_COLUMNS:
                    raise protocol.CheckpointValidationError("saved metrics schema is invalid")
                self.metrics = list(reader)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_monotonic

    def check_watchdog(self) -> None:
        if self.elapsed_seconds >= protocol.APPLICATION_WATCHDOG_SECONDS:
            raise protocol.ApplicationTimeoutError("application watchdog expired")

    def add_metrics(self, stage: str, status: str, values: dict[str, tuple[Any, str]]) -> None:
        recorded = utc_now()
        for metric, (value, unit) in values.items():
            if isinstance(value, float):
                rendered = format(value, ".12g")
            else:
                rendered = str(value)
            self.metrics.append(
                {
                    "stage": stage,
                    "status": status,
                    "metric": metric,
                    "value": rendered,
                    "unit": unit,
                    "recorded_at_utc": recorded,
                }
            )

    def persistence_status(self) -> dict[str, Any]:
        return protocol.persistence_summary(
            self.upload_history, configured=self.blob.configured
        )

    def stage_document(self, generated_at_utc: str | None = None) -> dict[str, Any]:
        return {
            "schema_version": "phase05-jlens-stage-results-v1",
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "updated_at_utc": generated_at_utc or utc_now(),
            "stage_order": list(protocol.STAGES),
            "stages": self.results,
            "scaling_plan": self.scaling_plan,
            "persistence": self.persistence_status(),
            "authorized_compatibility_fix_attempted": (
                self.args.authorized_compatibility_fix_attempted
            ),
        }

    def decision_document(self, generated_at_utc: str | None = None) -> dict[str, Any]:
        persistence = self.persistence_status()
        decision = protocol.derive_decision(
            self.results,
            authorized_compatibility_fix_attempted=(
                self.args.authorized_compatibility_fix_attempted
            ),
            scaling_plan=self.scaling_plan,
            persistence=persistence,
        )
        return {
            "schema_version": "phase05-jlens-decision-v1",
            "generated_at_utc": generated_at_utc or utc_now(),
            **decision,
            "persistence": persistence,
            "red_requires_authorized_fix": True,
            "automatic_plan_b": False,
        }

    def render_report(self, decision: dict[str, Any]) -> str:
        lines = [
            "# Phase 0.5A J-lens feasibility report",
            "",
            f"- Run: `{self.run_id}` / attempt `{self.attempt_id}`",
            f"- Decision: **{decision['decision']}** ({decision['gate_status']})",
            f"- Reason: {decision['reason']}",
            f"- Official source: `{protocol.OFFICIAL_REPOSITORY}@{protocol.OFFICIAL_COMMIT}`",
            f"- Target: `{protocol.MODEL_ID}@{protocol.MODEL_REVISION}` in fp16",
            f"- Persistence: **{decision['persistence']['status']}**",
            "- Plan B was not triggered automatically.",
            "",
            "## Stages",
            "",
            "| Stage | Status | Failure class | Duration (s) |",
            "|---|---|---|---:|",
        ]
        for stage in protocol.STAGES:
            result = self.results.get(stage, {})
            duration = result.get("duration_seconds")
            rendered_duration = "" if duration is None else f"{duration:.2f}"
            lines.append(
                f"| {stage} | {result.get('status', 'not_run')} | "
                f"{result.get('failure_class', '')} | {rendered_duration} |"
            )
        lines.extend(
            [
                "",
                "## Interpretation boundary",
                "",
                "F4 is a technical save/load/apply sanity check only. Token rankings, "
                "decoded text, and logit relationships are not semantic evidence and "
                "make no hidden-workspace claim.",
                "",
                "A dependency or F1 block remains UNRATED/BLOCKED. RED is allowed only "
                "after one separately authorized compatibility-fix attempt. The optional "
                "F5 merge check never changes a successful F0-F4 gate into failure.",
                "",
            ]
        )
        return "\n".join(lines)

    def _write_outputs(
        self, generated_at_utc: str, output_dir: Path | None = None
    ) -> None:
        target_dir = output_dir or self.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        self.environment["updated_at_utc"] = generated_at_utc
        self.environment["blob"]["configured"] = self.blob.configured
        self.environment["blob"]["persistence"] = self.persistence_status()
        decision = self.decision_document(generated_at_utc)
        atomic_write_json(
            target_dir / "phase05_jlens_environment.json", self.environment
        )
        atomic_write_json(
            target_dir / "phase05_jlens_stage_results.json",
            self.stage_document(generated_at_utc),
        )
        metrics_path = target_dir / "phase05_jlens_metrics.csv"
        temporary = metrics_path.with_name(f".{metrics_path.name}.tmp.{os.getpid()}")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=protocol.METRICS_COLUMNS)
            writer.writeheader()
            writer.writerows(self.metrics)
        os.replace(temporary, metrics_path)
        atomic_write_json(target_dir / "phase05_jlens_decision.json", decision)
        atomic_write_bytes(
            target_dir / "phase05_jlens_report.md",
            self.render_report(decision).encode("utf-8"),
        )
        manifest = protocol.build_artifact_manifest(
            target_dir, generated_at_utc=generated_at_utc
        )
        atomic_write_json(
            target_dir / "phase05_jlens_artifact_manifest.json", manifest
        )
        protocol.validate_output_schema(
            environment=self.environment,
            stage_results=self.stage_document(generated_at_utc),
            decision=decision,
            metrics_header=protocol.METRICS_COLUMNS,
            manifest=manifest,
        )

    def persist(
        self, stage_label: str, *, upload: bool = True, required: bool = True
    ) -> bool:
        generated_at = utc_now()
        if not upload:
            self._write_outputs(generated_at)
            return self.persistence_status()["ready"]

        self.snapshot_sequence += 1
        is_required = bool(required and self.blob.configured)
        if self.blob.configured:
            destination = self.blob.snapshot_destination(
                stage_label, self.snapshot_sequence
            )
            final_transaction = stage_label == "final"
            event = {
                "sequence": self.snapshot_sequence,
                "stage_label": stage_label,
                "attempt_id": self.attempt_id,
                "required": is_required,
                "status": "pending" if final_transaction else "confirmed",
                "transport_status": (
                    "upload_pending" if final_transaction else "uploaded"
                ),
                "failure_class": None,
                "prefix": destination,
                "manifest_uploaded_last": not final_transaction,
                "completed_at_utc": generated_at,
            }
            self.upload_history.append(event)
            self.environment["blob"]["last_snapshot"] = event
            if stage_label in self.results:
                self.results[stage_label].setdefault("details", {})[
                    "blob_snapshot"
                ] = event
            self._write_outputs(generated_at)
            event["uploaded"] = len(self.blob.snapshot_files(self.output_dir))
            self._write_outputs(generated_at)
            upload_source = self.output_dir
            staging_dir: Path | None = None
            try:
                if final_transaction:
                    staging_root = self.output_dir / ".snapshot-staging"
                    staging_root.mkdir(parents=True, exist_ok=True)
                    staging_dir = staging_root / (
                        f"final-snapshot-"
                        f"{os.getpid()}-{self.snapshot_sequence}"
                    )
                    if staging_dir.exists():
                        shutil.rmtree(staging_dir)
                    event.update(
                        {
                            "status": "confirmed",
                            "transport_status": "uploaded",
                            "manifest_uploaded_last": True,
                        }
                    )
                    shutil.copytree(
                        self.output_dir,
                        staging_dir,
                        ignore=shutil.ignore_patterns(".*"),
                    )
                    self._write_outputs(generated_at, staging_dir)
                    upload_source = staging_dir
                result = self.blob.upload_snapshot(
                    upload_source, stage_label, self.snapshot_sequence
                )
                if (
                    result.get("status") != "uploaded"
                    or result.get("prefix") != destination
                    or result.get("uploaded") != event["uploaded"]
                    or result.get("manifest_uploaded_last") is not True
                ):
                    raise protocol.CheckpointValidationError(
                        f"Blob snapshot confirmation mismatch: {result}"
                    )
            except Exception as error:
                event.update(
                    {
                        "status": "failed",
                        "transport_status": "upload_failed",
                        "failure_class": "checkpoint_failure",
                        "manifest_uploaded_last": False,
                        "error_type": type(error).__name__,
                        "error": safe_error(error),
                    }
                )
            finally:
                if staging_dir is not None and staging_dir.exists():
                    shutil.rmtree(staging_dir)
                    staging_root = staging_dir.parent
                    if staging_root.exists() and not any(staging_root.iterdir()):
                        staging_root.rmdir()
            self._write_outputs(generated_at)
            print(
                f"Blob snapshot {stage_label}: {event['status']} "
                f"({event.get('uploaded', 0)} files)",
                flush=True,
            )
            return event["status"] == "confirmed"

        event = {
            "sequence": self.snapshot_sequence,
            "stage_label": stage_label,
            "attempt_id": self.attempt_id,
            "required": False,
            "status": "not_configured",
            "transport_status": "not_configured",
            "failure_class": None,
            "manifest_uploaded_last": False,
            "uploaded": 0,
            "completed_at_utc": generated_at,
        }
        self.upload_history.append(event)
        if stage_label in self.results:
            self.results[stage_label].setdefault("details", {})["blob_snapshot"] = event
        self.environment["blob"]["last_snapshot"] = event
        self._write_outputs(generated_at)
        return True

    def execute(self, stage: str, function: Any) -> bool:
        if not protocol.can_start_stage(stage, self.results):
            predecessor = protocol.REQUIRED_PREDECESSOR[stage]
            self.results[stage] = {
                "status": "blocked",
                "started_at_utc": utc_now(),
                "finished_at_utc": utc_now(),
                "failure_class": None,
                "reason": f"prerequisite {predecessor} did not succeed",
                "details": {},
            }
            self.persist(stage)
            return False

        self.check_watchdog()
        started = time.monotonic()
        self.results[stage] = {
            "status": "running",
            "started_at_utc": utc_now(),
            "failure_class": None,
            "details": {},
        }
        if not self.persist(stage):
            now = utc_now()
            self.results[stage].update(
                {
                    "status": "failed",
                    "finished_at_utc": now,
                    "duration_seconds": time.monotonic() - started,
                    "failure_class": "checkpoint_failure",
                    "error_type": "BlobPersistenceError",
                    "error": "required stage-entry snapshot upload failed",
                    "details": {
                        "persistence": self.persistence_status(),
                    },
                }
            )
            self.persist(stage, upload=False)
            return False
        try:
            details = function()
            status = details.pop("_status", "success")
            if status not in {"success", "skipped_cost_guard"}:
                raise protocol.Phase05ValidationError(
                    f"invalid successful stage status {status}"
                )
            metric_values = details.pop("_metrics", {})
            duration = time.monotonic() - started
            self.results[stage].update(
                {
                    "status": status,
                    "finished_at_utc": utc_now(),
                    "duration_seconds": duration,
                    "details": details,
                }
            )
            self.add_metrics(stage, status, metric_values)
            self.add_metrics(stage, status, {"wall_seconds": (duration, "seconds")})
            persisted = self.persist(stage)
            if not persisted:
                self.results[stage]["details"]["persistence_failure"] = {
                    "failure_class": "checkpoint_failure",
                    "status": self.persistence_status(),
                }
                self.persist(stage, upload=False)
            return status in {"success", "skipped_cost_guard"} and persisted
        except Exception as error:
            duration = time.monotonic() - started
            failure_class = protocol.classify_failure(error, stage)
            self.results[stage].update(
                {
                    "status": "failed",
                    "finished_at_utc": utc_now(),
                    "duration_seconds": duration,
                    "failure_class": failure_class,
                    "error_type": type(error).__name__,
                    "error": safe_error(error),
                    "traceback_tail": traceback.format_exc().splitlines()[-12:],
                }
            )
            self.add_metrics(stage, "failed", {"wall_seconds": (duration, "seconds")})
            self.persist(stage)
            return False

    def block_remaining(self, after_stage: str, reason: str) -> None:
        for stage in protocol.stages_after_failure(after_stage, self.results):
            self.results[stage] = {
                "status": "blocked",
                "started_at_utc": utc_now(),
                "finished_at_utc": utc_now(),
                "failure_class": None,
                "reason": reason,
                "details": {},
            }
        self.persist(f"{after_stage}-blocked")

    def _runtime_memory(self) -> dict[str, Any]:
        psutil = importlib.import_module("psutil")
        process = psutil.Process()
        virtual = psutil.virtual_memory()
        disk = shutil.disk_usage(self.output_dir)
        return {
            "host_total_bytes": virtual.total,
            "host_available_bytes": virtual.available,
            "process_rss_bytes": process.memory_info().rss,
            "disk_total_bytes": disk.total,
            "disk_free_bytes": disk.free,
            "disk_path": str(self.output_dir),
        }

    def _start_gpu_measurement(self) -> None:
        self.torch.cuda.synchronize()
        self.torch.cuda.empty_cache()
        self.torch.cuda.reset_peak_memory_stats()

    def _finish_gpu_measurement(self) -> dict[str, Any]:
        self.torch.cuda.synchronize()
        free_bytes, total_bytes = self.torch.cuda.mem_get_info()
        host = self._runtime_memory()
        peak_allocated = self.torch.cuda.max_memory_allocated()
        peak_reserved = self.torch.cuda.max_memory_reserved()
        memory = protocol.classify_memory(
            gpu_peak_reserved_bytes=peak_reserved,
            gpu_total_bytes=total_bytes,
            gpu_free_bytes=free_bytes,
            host_rss_bytes=host["process_rss_bytes"],
            host_total_bytes=host["host_total_bytes"],
        )
        return {
            **memory,
            "gpu_peak_allocated_bytes": peak_allocated,
            "gpu_peak_reserved_bytes": peak_reserved,
            "gpu_total_bytes": total_bytes,
            "gpu_free_bytes": free_bytes,
            "host_rss_bytes": host["process_rss_bytes"],
            "host_total_bytes": host["host_total_bytes"],
        }

    def run_f0(self) -> dict[str, Any]:
        if sys.version_info[:2] != (3, 11):
            raise protocol.DependencyValidationError("Phase 0.5A requires Python 3.11")
        protocol.validate_source_pin(
            f"{protocol.OFFICIAL_REPOSITORY}@{protocol.OFFICIAL_COMMIT}"
        )
        protocol.validate_import_name("jlens")
        protocol.validate_model_controls(
            model_id=protocol.MODEL_ID,
            revision=protocol.MODEL_REVISION,
            dtype=protocol.RUNTIME_DTYPE,
            trust_remote_code=False,
        )

        self.torch = importlib.import_module("torch")
        self.transformers = importlib.import_module("transformers")
        self.jlens = importlib.import_module("jlens")
        huggingface_hub = importlib.import_module("huggingface_hub")
        numpy = importlib.import_module("numpy")

        installed = {
            "jlens": importlib.metadata.version("jlens"),
            "torch": self.torch.__version__.split("+", 1)[0],
            "transformers": self.transformers.__version__,
            "huggingface-hub": huggingface_hub.__version__,
            "numpy": numpy.__version__,
        }
        protocol.validate_dependency_versions(installed)

        distribution = importlib.metadata.distribution("jlens")
        direct_url_text = distribution.read_text("direct_url.json")
        if not direct_url_text:
            raise protocol.DependencyValidationError("jlens direct_url provenance missing")
        direct_url = json.loads(direct_url_text)
        installed_repository = (
            str(direct_url.get("url", "")).rstrip("/").removesuffix(".git")
        )
        if installed_repository != protocol.OFFICIAL_REPOSITORY:
            raise protocol.DependencyValidationError(
                f"installed jlens repository mismatch: {installed_repository!r}"
            )
        protocol.validate_source_pin(
            f"{direct_url.get('url', '')}@"
            f"{direct_url.get('vcs_info', {}).get('commit_id', '')}"
        )
        vcs = direct_url.get("vcs_info", {})
        if vcs.get("commit_id") != protocol.OFFICIAL_COMMIT:
            raise protocol.DependencyValidationError("installed jlens commit mismatch")
        requested_revision = vcs.get("requested_revision")
        if requested_revision and requested_revision != protocol.OFFICIAL_COMMIT:
            raise protocol.DependencyValidationError("requested jlens revision mismatch")
        module_path = Path(self.jlens.__file__).resolve()
        if distribution.metadata.get("Name", "").lower() != protocol.JLENS_DISTRIBUTION:
            raise protocol.DependencyValidationError("installed jlens distribution name mismatch")
        if module_path.name != "__init__.py" or module_path.parent.name != "jlens":
            raise protocol.DependencyValidationError(
                f"unexpected jlens package path: {module_path}"
            )
        license_value = (
            distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or ""
        )
        if "Apache-2.0" not in license_value:
            raise protocol.DependencyValidationError(
                f"unexpected jlens license metadata: {license_value!r}"
            )

        expected_signatures = {
            "from_hf": (
                "hf_model",
                "tokenizer",
                "layout",
                "text_module",
                "compile",
                "force_bos",
            ),
            "jacobian_for_prompt": (
                "model",
                "prompt",
                "source_layers",
                "target_layer",
                "dim_batch",
                "max_seq_len",
                "skip_first",
            ),
            "fit": (
                "model",
                "prompts",
                "source_layers",
                "target_layer",
                "dim_batch",
                "max_seq_len",
                "skip_first",
                "checkpoint_path",
                "checkpoint_every",
                "resume",
            ),
        }
        observed_signatures = {}
        for name, expected in expected_signatures.items():
            observed = tuple(inspect.signature(getattr(self.jlens, name)).parameters)
            if observed != expected:
                raise protocol.DependencyValidationError(
                    f"official API signature mismatch for {name}: {observed}"
                )
            observed_signatures[name] = list(observed)
        if not hasattr(self.jlens, "JacobianLens"):
            raise protocol.DependencyValidationError("jlens.JacobianLens missing")
        lens_signatures = {
            "load": ("path",),
            "save": ("self", "path", "dtype"),
            "apply": (
                "self",
                "model",
                "prompt",
                "layers",
                "positions",
                "max_seq_len",
                "use_jacobian",
            ),
            "merge": ("lenses",),
        }
        for name, expected in lens_signatures.items():
            observed = tuple(
                inspect.signature(getattr(self.jlens.JacobianLens, name)).parameters
            )
            if observed != expected:
                raise protocol.DependencyValidationError(
                    f"official JacobianLens.{name} signature mismatch: {observed}"
                )
            observed_signatures[f"JacobianLens.{name}"] = list(observed)

        AutoConfig = self.transformers.AutoConfig
        self.hf_config = AutoConfig.from_pretrained(
            protocol.MODEL_ID,
            revision=protocol.MODEL_REVISION,
            trust_remote_code=False,
        )
        config_metadata = {
            "architectures": list(self.hf_config.architectures or []),
            "n_layers": self.hf_config.num_hidden_layers,
            "d_model": self.hf_config.hidden_size,
            "checkpoint_dtype": str(
                getattr(self.hf_config, "dtype", None)
                or getattr(self.hf_config, "torch_dtype", "")
            ),
            "resolved_revision": getattr(self.hf_config, "_commit_hash", None),
        }
        protocol.validate_config_metadata(config_metadata)

        if not self.torch.cuda.is_available():
            raise protocol.DependencyValidationError("CUDA is not available")
        if self.torch.cuda.device_count() != 1:
            raise protocol.DependencyValidationError(
                "exactly one visible CUDA device is required"
            )
        gpu_name = self.torch.cuda.get_device_name(0)
        if "T4" not in gpu_name.upper():
            raise protocol.DependencyValidationError(f"expected T4 GPU, got {gpu_name}")
        properties = self.torch.cuda.get_device_properties(0)
        x = self.torch.randn(
            64,
            64,
            device="cuda:0",
            dtype=self.torch.float16,
            requires_grad=True,
        )
        toy_loss = (x @ x.T).float().square().mean()
        toy_loss.backward()
        if x.grad is None or not self.torch.isfinite(x.grad).all() or x.grad.norm() <= 0:
            raise protocol.DependencyValidationError("fp16 toy CUDA backward failed")
        del x, toy_loss
        self.torch.cuda.empty_cache()

        self.corpus_records, self.corpus_sha256 = load_corpus(Path(self.args.corpus))
        requirements_path = PROJECT_ROOT / "requirements-jlens.txt"
        dockerfile_path = PROJECT_ROOT / "Dockerfile.jlens"
        requirement_text = requirements_path.read_text(encoding="utf-8")
        protocol.validate_source_pin(requirement_text)
        docker_text = dockerfile_path.read_text(encoding="utf-8")
        protocol.validate_source_pin(
            f"{protocol.OFFICIAL_REPOSITORY}@"
            f"{protocol.OFFICIAL_COMMIT if protocol.OFFICIAL_COMMIT in docker_text else ''}"
        )
        freeze = subprocess.run(
            [sys.executable, "-m", "pip", "freeze", "--all"],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        ).stdout.splitlines()
        memory = self._runtime_memory()
        free_bytes, total_bytes = self.torch.cuda.mem_get_info()
        self.environment.update(
            {
                "tooling_state": "EXECUTING",
                "python": {
                    "version": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "executable": sys.executable,
                },
                "dependencies": {
                    "expected": protocol.EXPECTED_DEPENDENCIES,
                    "installed": installed,
                    "installed_freeze": sorted(freeze, key=str.lower),
                },
                "jlens_provenance": {
                    "distribution": distribution.metadata["Name"],
                    "version": distribution.version,
                    "license": license_value,
                    "module_path": str(module_path),
                    "direct_url": direct_url,
                    "api_signatures": observed_signatures,
                },
                "target_config": config_metadata,
                "corpus": {
                    "path": str(Path(self.args.corpus).resolve()),
                    "n_prompts": len(self.corpus_records),
                    "canonical_sha256": self.corpus_sha256,
                },
                "file_hashes": {
                    "requirements-jlens.txt": protocol.sha256_file(requirements_path),
                    "Dockerfile.jlens": protocol.sha256_file(dockerfile_path),
                    "data/jlens_feasibility_prompts.jsonl": protocol.sha256_file(
                        self.args.corpus
                    ),
                },
                "cuda": {
                    "available": True,
                    "visible_device_count": 1,
                    "device_name": gpu_name,
                    "device_total_memory_bytes": properties.total_memory,
                    "memory_total_bytes": total_bytes,
                    "memory_free_bytes": free_bytes,
                    "torch_cuda_version": self.torch.version.cuda,
                    "cudnn_version": self.torch.backends.cudnn.version(),
                    "fp16_toy_backward": "passed",
                },
                "host": memory,
            }
        )
        return {
            "provenance_verified": True,
            "config_metadata_only": True,
            "model_loaded": False,
            "dependency_versions": installed,
            "gpu_name": gpu_name,
            "corpus_sha256": self.corpus_sha256,
            "_metrics": {
                "gpu_total_bytes": (properties.total_memory, "bytes"),
                "gpu_free_bytes": (free_bytes, "bytes"),
                "host_rss_bytes": (memory["process_rss_bytes"], "bytes"),
                "disk_free_bytes": (memory["disk_free_bytes"], "bytes"),
            },
        }

    def run_f1(self) -> dict[str, Any]:
        protocol.validate_model_controls(
            model_id=protocol.MODEL_ID,
            revision=protocol.MODEL_REVISION,
            dtype=protocol.RUNTIME_DTYPE,
            trust_remote_code=False,
            quantized=False,
            compile_model=False,
        )
        self.torch.set_grad_enabled(True)
        self.hf_config.use_cache = False
        self.hf_config.output_hidden_states = False
        self.tokenizer = self.transformers.AutoTokenizer.from_pretrained(
            protocol.MODEL_ID,
            revision=protocol.MODEL_REVISION,
            trust_remote_code=False,
        )
        transformers_hub = importlib.import_module("transformers.utils.hub")
        tokenizer_config_path = transformers_hub.cached_file(
            protocol.MODEL_ID,
            "tokenizer_config.json",
            revision=protocol.MODEL_REVISION,
        )
        tokenizer_revision = transformers_hub.extract_commit_hash(
            tokenizer_config_path, None
        )
        if tokenizer_revision != protocol.MODEL_REVISION:
            raise protocol.DependencyValidationError(
                "resolved tokenizer revision mismatch"
            )
        self.hf_model = self.transformers.AutoModelForCausalLM.from_pretrained(
            protocol.MODEL_ID,
            revision=protocol.MODEL_REVISION,
            config=self.hf_config,
            dtype=self.torch.float16,
            trust_remote_code=False,
        )
        self.hf_model.to(self.torch.device("cuda:0"))
        self.hf_model.eval()
        self.hf_model.config.use_cache = False
        self.hf_model.config.output_hidden_states = False
        if getattr(self.hf_model.config, "_commit_hash", None) != protocol.MODEL_REVISION:
            raise protocol.DependencyValidationError("loaded model revision mismatch")

        devices = {parameter.device.type + f":{parameter.device.index}" for parameter in self.hf_model.parameters()}
        if devices != {"cuda:0"}:
            raise protocol.DependencyValidationError(f"model spans unexpected devices: {devices}")
        floating_dtypes = {
            str(parameter.dtype)
            for parameter in self.hf_model.parameters()
            if parameter.is_floating_point()
        }
        if floating_dtypes != {"torch.float16"}:
            raise protocol.DependencyValidationError(
                f"model parameter dtype mismatch: {floating_dtypes}"
            )

        self.lens_model = self.jlens.from_hf(
            self.hf_model,
            self.tokenizer,
            layout=None,
            text_module=None,
            compile=False,
            force_bos=True,
        )
        self.layers = protocol.representative_layers(self.lens_model.n_layers)
        if self.lens_model.n_layers != protocol.MODEL_LAYERS:
            raise protocol.AdapterValidationError("adapter layer count mismatch")
        if self.lens_model.d_model != protocol.MODEL_WIDTH:
            raise protocol.AdapterValidationError("adapter residual width mismatch")
        if len(self.lens_model.layers) != protocol.MODEL_LAYERS:
            raise protocol.AdapterValidationError("adapter block handle count mismatch")
        if self.lens_model.layout.path != "model":
            raise protocol.AdapterValidationError(
                f"expected direct Qwen2 model.layers layout, got {self.lens_model.layout}"
            )
        if self.lens_model.layers is not self.hf_model.model.layers:
            raise protocol.AdapterValidationError("adapter did not use model.model.layers")
        with self.jlens.ActivationRecorder(
            self.lens_model.layers, at=range(protocol.MODEL_LAYERS)
        ) as recorder:
            handle_count = len(recorder._handles)
        if handle_count != protocol.MODEL_LAYERS:
            raise protocol.AdapterValidationError("could not register 28 official hooks")
        unembedding_shape = list(self.lens_model._lm_head.weight.shape)
        if len(unembedding_shape) != 2 or unembedding_shape[1] != protocol.MODEL_WIDTH:
            raise protocol.AdapterValidationError(
                f"unexpected unembedding shape: {unembedding_shape}"
            )

        seq_len = protocol.guarded_token_length(self.tokenizer, F2_PROMPT)
        input_ids = self.lens_model.encode(F2_PROMPT, max_length=protocol.MAX_SEQ_LEN)
        if input_ids.shape[1] != seq_len:
            raise protocol.AdapterValidationError("token-length guard disagrees with adapter")
        with self.torch.enable_grad():
            output = self.hf_model(input_ids=input_ids, use_cache=False)
        if not self.torch.isfinite(output.logits).all():
            raise protocol.NumericalValidationError("ordinary model forward is non-finite")
        logits_shape = list(output.logits.shape)
        del output, input_ids
        self.torch.cuda.empty_cache()
        free_bytes, total_bytes = self.torch.cuda.mem_get_info()
        return {
            "model_id": protocol.MODEL_ID,
            "requested_revisions": {
                "config": protocol.MODEL_REVISION,
                "tokenizer": protocol.MODEL_REVISION,
                "model": protocol.MODEL_REVISION,
            },
            "resolved_revisions": {
                "config": getattr(self.hf_config, "_commit_hash", None),
                "tokenizer": tokenizer_revision,
                "model": getattr(self.hf_model.config, "_commit_hash", None),
            },
            "runtime_dtype": protocol.RUNTIME_DTYPE,
            "quantization": None,
            "compile": False,
            "use_cache": False,
            "output_hidden_states": False,
            "gradient_mode_enabled": self.torch.is_grad_enabled(),
            "n_layers": self.lens_model.n_layers,
            "d_model": self.lens_model.d_model,
            "registered_hook_handles": handle_count,
            "layout": {
                "path": self.lens_model.layout.path,
                "layers": self.lens_model.layout.layers,
            },
            "unembedding_shape": unembedding_shape,
            "ordinary_forward_logits_shape": logits_shape,
            "ordinary_forward_finite": True,
            "f2_guarded_seq_len": seq_len,
            "gpu_name": self.torch.cuda.get_device_name(0),
            "gpu_total_bytes": total_bytes,
            "gpu_free_bytes": free_bytes,
            "versions": self.environment["dependencies"]["installed"],
            "representative_layers": self.layers,
            "_metrics": {
                "n_layers": (self.lens_model.n_layers, "count"),
                "d_model": (self.lens_model.d_model, "dimensions"),
                "registered_hook_handles": (handle_count, "count"),
                "gpu_free_bytes": (free_bytes, "bytes"),
            },
        }

    def _valid_prior_artifact(self, stage: str, relative_path: str) -> bool:
        if stage not in self.prior_success:
            return False
        path = self.output_dir / relative_path
        expected = (
            self.results.get(stage, {})
            .get("details", {})
            .get("artifact", {})
            .get("sha256")
        )
        return bool(path.exists() and expected and protocol.sha256_file(path) == expected)

    def _reuse_complete_f3(self) -> bool:
        if "F3" not in self.prior_success:
            return False
        details = self.results.get("F3", {}).get("details", {})
        lens_record = details.get("lens", {})
        checkpoint_record = details.get("checkpoint", {})
        lens_path = self.output_dir / str(lens_record.get("path", ""))
        checkpoint_path = self.output_dir / str(checkpoint_record.get("path", ""))
        if (
            not lens_path.is_file()
            or not checkpoint_path.is_file()
            or protocol.sha256_file(lens_path) != lens_record.get("sha256")
            or protocol.sha256_file(checkpoint_path) != checkpoint_record.get("sha256")
        ):
            return False
        manifest_path = (
            self.output_dir / "checkpoint" / "phase05_jlens_f3_checkpoint.manifest.json"
        )
        if not manifest_path.is_file():
            return False
        controls = protocol.make_checkpoint_controls(
            prompt_order_sha256=self.corpus_sha256,
            source_layers=self.layers["f3_source_layers"],
            target_layer=self.layers["target_layer"],
            dim_batch=int(details["dim_batch"]),
        )
        protocol.validate_checkpoint_manifest(read_json(manifest_path), controls)
        checkpoint_state = self.torch.load(
            checkpoint_path, map_location="cpu", weights_only=True
        )
        if checkpoint_state.get("n_done") != 2:
            raise protocol.CheckpointValidationError(
                "reused F3 checkpoint is not complete"
            )
        jacobians = {
            layer: checkpoint_state["jacobian_sum"][layer] / 2
            for layer in self.layers["f3_source_layers"]
        }
        self.fitted_lens = self.jlens.JacobianLens(
            jacobians=jacobians,
            n_prompts=2,
            d_model=protocol.MODEL_WIDTH,
        )
        self.loaded_lens = self.jlens.JacobianLens.load(str(lens_path))
        self.scaling_plan = details.get("scaling_plan") or self.scaling_plan
        details["resume_reused_complete_artifacts"] = True
        return True

    def run_f2(self) -> dict[str, Any]:
        source_layer = self.layers["f2_source_layer"]
        target_layer = self.layers["target_layer"]
        protocol.ensure_source_before_target(
            [source_layer], target_layer, self.lens_model.n_layers
        )
        guarded_length = protocol.guarded_token_length(self.tokenizer, F2_PROMPT)
        expected_passes = math.ceil(protocol.MODEL_WIDTH / protocol.F2_DIM_BATCH)
        counter = {"calls": 0, "successful_calls": 0}
        original_grad = self.torch.autograd.grad

        def counted_grad(*args: Any, **kwargs: Any) -> Any:
            counter["calls"] += 1
            result = original_grad(*args, **kwargs)
            counter["successful_calls"] += 1
            return result

        self._start_gpu_measurement()
        started = time.monotonic()
        self.torch.autograd.grad = counted_grad
        try:
            jacobians, seq_len, valid_positions = self.jlens.jacobian_for_prompt(
                self.lens_model,
                F2_PROMPT,
                [source_layer],
                target_layer=target_layer,
                dim_batch=protocol.F2_DIM_BATCH,
                max_seq_len=protocol.MAX_SEQ_LEN,
                skip_first=protocol.SKIP_FIRST,
            )
        finally:
            self.torch.autograd.grad = original_grad
        wall_seconds = time.monotonic() - started
        memory = self._finish_gpu_measurement()
        if counter["calls"] != expected_passes or counter["successful_calls"] != expected_passes:
            raise protocol.NumericalValidationError(
                f"expected {expected_passes} true autograd passes, observed {counter}"
            )
        if seq_len != guarded_length:
            raise protocol.NumericalValidationError("official F2 sequence length changed")
        if valid_positions != protocol.valid_position_count(seq_len):
            raise protocol.NumericalValidationError("official valid-position count changed")
        if set(jacobians) != {source_layer}:
            raise protocol.NumericalValidationError("F2 returned an unexpected layer set")
        matrix = jacobians[source_layer]
        norm = float(matrix.norm().item())
        finite = bool(self.torch.isfinite(matrix).all().item())
        protocol.validate_jacobian_summary(
            shape=matrix.shape,
            dtype=str(matrix.dtype),
            finite=finite,
            norm=norm,
        )
        if matrix.device.type != "cpu":
            raise protocol.NumericalValidationError("F2 Jacobian must be on CPU")

        artifact_path = self.output_dir / "checkpoint" / "phase05_jlens_f2_jacobian.pt"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_torch_save(
            self.torch,
            {
                "J": {source_layer: matrix},
                "metadata": {
                    "official_commit": protocol.OFFICIAL_COMMIT,
                    "model_id": protocol.MODEL_ID,
                    "model_revision": protocol.MODEL_REVISION,
                    "source_layer": source_layer,
                    "target_layer": target_layer,
                    "dim_batch": protocol.F2_DIM_BATCH,
                    "max_seq_len": protocol.MAX_SEQ_LEN,
                    "skip_first": protocol.SKIP_FIRST,
                    "seq_len": seq_len,
                    "valid_positions": valid_positions,
                },
            },
            artifact_path,
        )
        artifact = {
            "path": artifact_path.relative_to(self.output_dir).as_posix(),
            "bytes": artifact_path.stat().st_size,
            "sha256": protocol.sha256_file(artifact_path),
        }
        f3_time_guard = protocol.f3_dim1_time_guard(
            elapsed_seconds=self.elapsed_seconds,
            f2_wall_seconds=wall_seconds,
            f2_source_layer=source_layer,
            f3_source_layers=self.layers["f3_source_layers"],
            target_layer=target_layer,
        )
        return {
            "real_official_jacobian": True,
            "prompt_sha256": protocol.sha256_bytes(F2_PROMPT.encode("utf-8")),
            "source_layers": [source_layer],
            "target_layer": target_layer,
            "dim_batch": protocol.F2_DIM_BATCH,
            "max_seq_len": protocol.MAX_SEQ_LEN,
            "skip_first": protocol.SKIP_FIRST,
            "seq_len": seq_len,
            "valid_positions": valid_positions,
            "expected_backward_equivalent_passes": expected_passes,
            "autograd_grad_calls": counter["calls"],
            "successful_autograd_grad_calls": counter["successful_calls"],
            "wall_seconds": wall_seconds,
            "jacobian": {
                "shape": list(matrix.shape),
                "dtype": str(matrix.dtype),
                "device": str(matrix.device),
                "norm": norm,
                "finite": finite,
                "nonzero": norm > 0,
            },
            "memory": memory,
            "f3_time_guard": f3_time_guard,
            "continue_allowed": (
                memory["classification"] != "stop"
                and f3_time_guard["continue_allowed"]
            ),
            "artifact": artifact,
            "_metrics": {
                "seq_len": (seq_len, "tokens"),
                "valid_positions": (valid_positions, "positions"),
                "autograd_grad_calls": (counter["calls"], "calls"),
                "jacobian_norm": (norm, "l2_norm"),
                "jacobian_bytes": (artifact["bytes"], "bytes"),
                "gpu_peak_allocated_bytes": (
                    memory["gpu_peak_allocated_bytes"],
                    "bytes",
                ),
                "gpu_peak_reserved_bytes": (
                    memory["gpu_peak_reserved_bytes"],
                    "bytes",
                ),
                "gpu_free_bytes": (memory["gpu_free_bytes"], "bytes"),
                "host_rss_bytes": (memory["host_rss_bytes"], "bytes"),
            },
        }

    def run_f3(self) -> dict[str, Any]:
        source_layers = self.layers["f3_source_layers"]
        target_layer = self.layers["target_layer"]
        f2_memory = self.results["F2"]["details"]["memory"]
        f2_wall_seconds = float(self.results["F2"]["details"]["wall_seconds"])
        dim_batch = protocol.choose_f3_dim_batch(
            f2_memory, f2_wall_seconds=f2_wall_seconds
        )
        prompts = [record["text"] for record in self.corpus_records]
        if F2_PROMPT in prompts or any(item["text"] in prompts for item in SANITY_PROMPTS):
            raise protocol.Phase05ValidationError(
                "F2, fit, and F4 prompt sets must remain disjoint"
            )
        prompt_token_lengths = [
            protocol.guarded_token_length(self.tokenizer, prompt) for prompt in prompts
        ]
        controls = protocol.make_checkpoint_controls(
            prompt_order_sha256=self.corpus_sha256,
            source_layers=source_layers,
            target_layer=target_layer,
            dim_batch=dim_batch,
        )
        checkpoint_dir = self.output_dir / "checkpoint"
        lens_dir = self.output_dir / "lens"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        lens_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / "phase05_jlens_f3_fit_checkpoint.pt"
        manifest_path = checkpoint_dir / "phase05_jlens_f3_checkpoint.manifest.json"
        initial_n_done = 0
        initial_next_idx = 0
        if checkpoint_path.exists():
            if not manifest_path.exists():
                raise protocol.CheckpointValidationError(
                    "resumable checkpoint has no external controls manifest"
                )
            protocol.validate_checkpoint_manifest(read_json(manifest_path), controls)
            initial_state = self.torch.load(
                checkpoint_path, map_location="cpu", weights_only=True
            )
            initial_n_done = int(initial_state.get("n_done", -1))
            initial_next_idx = int(initial_state.get("next_idx", -1))
            protocol.f3_checkpoint_actions(initial_n_done, initial_next_idx)
            resumed = True
        else:
            if manifest_path.exists():
                protocol.validate_checkpoint_manifest(read_json(manifest_path), controls)
            else:
                manifest = protocol.make_checkpoint_manifest(controls)
                manifest["created_at_utc"] = utc_now()
                atomic_write_json(manifest_path, manifest)
            resumed = False

        actions = protocol.f3_checkpoint_actions(initial_n_done, initial_next_idx)
        self._start_gpu_measurement()
        fit_segments: list[dict[str, Any]] = []
        prompt_1_snapshot: dict[str, Any] | None = None
        if "fit_prompt_1" in actions:
            segment_started = time.monotonic()
            prompt_1_lens = self.jlens.fit(
                self.lens_model,
                prompts=prompts[:1],
                source_layers=source_layers,
                target_layer=target_layer,
                dim_batch=dim_batch,
                max_seq_len=protocol.MAX_SEQ_LEN,
                skip_first=protocol.SKIP_FIRST,
                checkpoint_path=str(checkpoint_path),
                checkpoint_every=1,
                resume=True,
            )
            fit_segments.append(
                {
                    "segment": "prompt_1_prefix",
                    "seconds": time.monotonic() - segment_started,
                    "prompts_computed": 1,
                }
            )
            if prompt_1_lens.n_prompts != 1:
                raise protocol.CheckpointValidationError(
                    "official prompt-1 prefix fit did not produce n_prompts=1"
                )

        if "persist_prompt_1" in actions:
            prompt_1_state = self.torch.load(
                checkpoint_path, map_location="cpu", weights_only=True
            )
            if (
                prompt_1_state.get("n_done") != 1
                or prompt_1_state.get("next_idx") != 1
                or prompt_1_state.get("source_layers") != source_layers
                or prompt_1_state.get("target_layer") != target_layer
            ):
                raise protocol.CheckpointValidationError(
                    "official prompt-1 checkpoint state is invalid"
                )
            prompt_1_progress = {
                "n_done": 1,
                "next_idx": 1,
                "prompt_prefix_count": 1,
                "prompt_prefix_sha256": protocol.canonical_jsonl_sha256(
                    self.corpus_records[:1]
                ),
                "checkpoint": {
                    "path": checkpoint_path.relative_to(self.output_dir).as_posix(),
                    "bytes": checkpoint_path.stat().st_size,
                    "sha256": protocol.sha256_file(checkpoint_path),
                },
            }
            checkpoint_manifest = read_json(manifest_path)
            checkpoint_manifest["progress"] = prompt_1_progress
            checkpoint_manifest["progress_sha256"] = protocol.sha256_bytes(
                protocol.canonical_json_bytes(prompt_1_progress)
            )
            checkpoint_manifest["updated_at_utc"] = utc_now()
            atomic_write_json(manifest_path, checkpoint_manifest)
            self.results["F3"]["details"]["prompt_1_checkpoint"] = prompt_1_progress
            if not self.persist("F3-prompt-1"):
                raise protocol.CheckpointValidationError(
                    "required F3 prompt-1 checkpoint snapshot was not durable"
                )
            prompt_1_snapshot = {
                **prompt_1_progress,
                "blob_persistence": self.upload_history[-1],
            }

        segment_started = time.monotonic()
        self.fitted_lens = self.jlens.fit(
            self.lens_model,
            prompts=prompts,
            source_layers=source_layers,
            target_layer=target_layer,
            dim_batch=dim_batch,
            max_seq_len=protocol.MAX_SEQ_LEN,
            skip_first=protocol.SKIP_FIRST,
            checkpoint_path=str(checkpoint_path),
            checkpoint_every=1,
            resume=True,
        )
        final_segment_seconds = time.monotonic() - segment_started
        fit_segments.append(
            {
                "segment": "full_corpus_resume",
                "seconds": final_segment_seconds,
                "prompts_computed": max(0, 2 - max(1, initial_n_done))
                if "persist_prompt_1" in actions
                else 0,
            }
        )
        fit_seconds = sum(float(item["seconds"]) for item in fit_segments)
        memory = self._finish_gpu_measurement()
        if self.fitted_lens.n_prompts != 2:
            raise protocol.CheckpointValidationError("F3 must fit exactly two prompts")
        if self.fitted_lens.source_layers != source_layers:
            raise protocol.CheckpointValidationError("F3 lens layer set mismatch")
        if len(self.fitted_lens.jacobians) != 3:
            raise protocol.CheckpointValidationError("F3 must contain three matrices")
        matrix_summaries = {}
        for layer in source_layers:
            matrix = self.fitted_lens.jacobians[layer]
            norm = float(matrix.norm().item())
            finite = bool(self.torch.isfinite(matrix).all().item())
            protocol.validate_jacobian_summary(
                shape=matrix.shape,
                dtype=str(matrix.dtype),
                finite=finite,
                norm=norm,
            )
            matrix_summaries[str(layer)] = {
                "shape": list(matrix.shape),
                "dtype": str(matrix.dtype),
                "norm": norm,
                "finite": finite,
            }

        checkpoint_state = self.torch.load(
            checkpoint_path, map_location="cpu", weights_only=True
        )
        if (
            checkpoint_state.get("n_done") != 2
            or checkpoint_state.get("next_idx") != 2
            or checkpoint_state.get("source_layers") != source_layers
            or checkpoint_state.get("target_layer") != target_layer
        ):
            raise protocol.CheckpointValidationError("official checkpoint state is invalid")

        lens_path = lens_dir / "phase05_jlens.pt"
        temporary_lens_path = lens_path.with_name(
            f".{lens_path.name}.tmp.{os.getpid()}"
        )
        self.fitted_lens.save(str(temporary_lens_path))
        os.replace(temporary_lens_path, lens_path)
        self.loaded_lens = self.jlens.JacobianLens.load(str(lens_path))
        if (
            self.loaded_lens.n_prompts != 2
            or self.loaded_lens.source_layers != source_layers
            or self.loaded_lens.d_model != protocol.MODEL_WIDTH
        ):
            raise protocol.CheckpointValidationError("saved lens failed load validation")
        save_load_max_abs = {}
        for layer in source_layers:
            difference = (
                self.fitted_lens.jacobians[layer]
                - self.loaded_lens.jacobians[layer]
            )
            maximum = float(difference.abs().max().item())
            save_load_max_abs[str(layer)] = maximum
            if not self.torch.allclose(
                self.fitted_lens.jacobians[layer],
                self.loaded_lens.jacobians[layer],
                rtol=5e-3,
                atol=5e-3,
            ):
                raise protocol.CheckpointValidationError(
                    f"lens save/load numeric mismatch at layer {layer}"
                )

        checkpoint_manifest = read_json(manifest_path)
        checkpoint_manifest["completed_at_utc"] = utc_now()
        checkpoint_manifest["checkpoint"] = {
            "path": checkpoint_path.relative_to(self.output_dir).as_posix(),
            "bytes": checkpoint_path.stat().st_size,
            "sha256": protocol.sha256_file(checkpoint_path),
            "n_done": checkpoint_state["n_done"],
            "next_idx": checkpoint_state["next_idx"],
        }
        checkpoint_manifest["lens"] = {
            "path": lens_path.relative_to(self.output_dir).as_posix(),
            "bytes": lens_path.stat().st_size,
            "sha256": protocol.sha256_file(lens_path),
        }
        completion_progress = {
            "n_done": checkpoint_state["n_done"],
            "next_idx": checkpoint_state["next_idx"],
            "checkpoint_sha256": checkpoint_manifest["checkpoint"]["sha256"],
            "lens_sha256": checkpoint_manifest["lens"]["sha256"],
        }
        checkpoint_manifest["completion"] = completion_progress
        checkpoint_manifest["completion_sha256"] = protocol.sha256_bytes(
            protocol.canonical_json_bytes(completion_progress)
        )
        atomic_write_json(manifest_path, checkpoint_manifest)
        processed_this_run = 2 - initial_n_done
        if processed_this_run > 0:
            seconds_per_prompt = fit_seconds / processed_this_run
        else:
            seconds_per_prompt = float(
                self.results["F2"]["details"]["wall_seconds"]
            )
            memory["classification"] = "borderline"
            memory["measurement_scope"] = "resume_with_no_new_prompt"
        self.scaling_plan = protocol.measured_scaling_plan(
            seconds_per_prompt=seconds_per_prompt,
            memory_classification=memory["classification"],
            fixed_overhead_seconds=(
                float(self.results["F0"]["duration_seconds"])
                + float(self.results["F1"]["duration_seconds"])
            ),
        )
        return {
            "n_prompts": self.fitted_lens.n_prompts,
            "source_layers": source_layers,
            "target_layer": target_layer,
            "dim_batch": dim_batch,
            "dim_batch_selection": {
                "f2_wall_seconds": f2_wall_seconds,
                "f2_memory_classification": f2_memory["classification"],
                "f2_peak_reserved_ratio": f2_memory["gpu_peak_reserved_ratio"],
                "f2_free_gib": f2_memory["gpu_free_gib"],
                "selected": dim_batch,
            },
            "max_seq_len": protocol.MAX_SEQ_LEN,
            "skip_first": protocol.SKIP_FIRST,
            "checkpoint_every": 1,
            "resume_enabled": True,
            "resumed_checkpoint": resumed,
            "initial_checkpoint_n_done": initial_n_done,
            "initial_checkpoint_next_idx": initial_next_idx,
            "prompts_processed_this_run": processed_this_run,
            "checkpoint_actions": actions,
            "fit_segments": fit_segments,
            "prompt_1_snapshot": prompt_1_snapshot,
            "prompt_order_sha256": self.corpus_sha256,
            "prompt_token_lengths": prompt_token_lengths,
            "fit_seconds": fit_seconds,
            "seconds_per_prompt": seconds_per_prompt,
            "matrices": matrix_summaries,
            "checkpoint_manifest": manifest_path.relative_to(
                self.output_dir
            ).as_posix(),
            "checkpoint": checkpoint_manifest["checkpoint"],
            "lens": checkpoint_manifest["lens"],
            "save_load_max_abs": save_load_max_abs,
            "memory": memory,
            "scaling_plan": self.scaling_plan,
            "_metrics": {
                "fit_prompts": (2, "prompts"),
                "fit_matrices": (3, "matrices"),
                "fit_seconds": (fit_seconds, "seconds"),
                "seconds_per_prompt": (seconds_per_prompt, "seconds_per_prompt"),
                "gpu_peak_allocated_bytes": (
                    memory["gpu_peak_allocated_bytes"],
                    "bytes",
                ),
                "gpu_peak_reserved_bytes": (
                    memory["gpu_peak_reserved_bytes"],
                    "bytes",
                ),
                "host_rss_bytes": (memory["host_rss_bytes"], "bytes"),
            },
        }

    def run_f4(self) -> dict[str, Any]:
        source_layers = self.layers["f3_source_layers"]
        protocol.validate_apply_controls(
            use_jacobian=True,
            layers=source_layers,
        )
        if self.fitted_lens is None or self.loaded_lens is None:
            lens_path = self.output_dir / "lens" / "phase05_jlens.pt"
            self.fitted_lens = self.jlens.JacobianLens.load(str(lens_path))
            self.loaded_lens = self.jlens.JacobianLens.load(str(lens_path))
        top_k_records = []
        all_consistent = True
        for prompt in SANITY_PROMPTS:
            lens_logits, model_logits, input_ids = self.fitted_lens.apply(
                self.lens_model,
                prompt["text"],
                layers=source_layers,
                positions=[-1],
                max_seq_len=protocol.MAX_SEQ_LEN,
                use_jacobian=True,
            )
            reloaded_logits, reloaded_model_logits, reloaded_ids = self.loaded_lens.apply(
                self.lens_model,
                prompt["text"],
                layers=source_layers,
                positions=[-1],
                max_seq_len=protocol.MAX_SEQ_LEN,
                use_jacobian=True,
            )
            if list(lens_logits) != source_layers:
                raise protocol.NumericalValidationError("F4 layer ordering changed")
            if input_ids.numel() == 0 or not self.torch.equal(input_ids, reloaded_ids):
                raise protocol.NumericalValidationError("F4 returned invalid input IDs")
            if (
                model_logits.ndim != 2
                or model_logits.shape[0] != 1
                or model_logits.shape != reloaded_model_logits.shape
                or not self.torch.isfinite(model_logits).all()
                or not self.torch.isfinite(reloaded_model_logits).all()
                or not self.torch.allclose(
                    model_logits, reloaded_model_logits, rtol=1e-5, atol=1e-5
                )
            ):
                raise protocol.NumericalValidationError("F4 model logits are invalid")
            layer_records = []
            for layer in source_layers:
                logits = lens_logits[layer]
                reloaded = reloaded_logits[layer]
                if (
                    logits.shape != model_logits.shape
                    or logits.numel() == 0
                    or not self.torch.isfinite(logits).all()
                ):
                    raise protocol.NumericalValidationError(
                        f"F4 lens logits invalid at layer {layer}"
                    )
                consistent = bool(
                    self.torch.allclose(logits, reloaded, rtol=5e-3, atol=5e-3)
                )
                all_consistent = all_consistent and consistent
                if not consistent:
                    raise protocol.CheckpointValidationError(
                        f"F4 saved/reloaded apply mismatch at layer {layer}"
                    )
                top_values, top_ids = logits[0].topk(5)
                cosine = float(
                    self.torch.nn.functional.cosine_similarity(
                        logits.float(), model_logits.float(), dim=-1
                    )[0].item()
                )
                difference_norm = float((logits - model_logits).norm().item())
                if not protocol.finite_numbers([cosine, difference_norm]):
                    raise protocol.NumericalValidationError(
                        "F4 model-logit relationship is non-finite"
                    )
                layer_records.append(
                    {
                        "layer": layer,
                        "shape": list(logits.shape),
                        "finite": True,
                        "top_k": [
                            {
                                "token_id": int(token_id),
                                "decoded": self.tokenizer.decode(
                                    [int(token_id)], skip_special_tokens=False
                                ),
                                "logit": float(value),
                            }
                            for value, token_id in zip(
                                top_values.tolist(), top_ids.tolist(), strict=True
                            )
                        ],
                        "model_relation": {
                            "cosine_similarity": cosine,
                            "difference_l2_norm": difference_norm,
                            "top1_matches_model": (
                                int(top_ids[0])
                                == int(model_logits[0].argmax().item())
                            ),
                        },
                        "save_load_consistent": consistent,
                    }
                )
            top_k_records.append(
                {
                    **prompt,
                    "position": -1,
                    "input_token_count": int(input_ids.shape[1]),
                    "model_top_k": [
                        {
                            "token_id": int(token_id),
                            "decoded": self.tokenizer.decode(
                                [int(token_id)], skip_special_tokens=False
                            ),
                            "logit": float(value),
                        }
                        for value, token_id in zip(
                            *[
                                tensor.tolist()
                                for tensor in model_logits[0].topk(5)
                            ],
                            strict=True,
                        )
                    ],
                    "layers": layer_records,
                }
            )
        topk_path = self.output_dir / "phase05_jlens_topk_sanity.json"
        atomic_write_json(
            topk_path,
            {
                "schema_version": "phase05-jlens-topk-sanity-v1",
                "generated_at_utc": utc_now(),
                "use_jacobian": True,
                "positions": [-1],
                "source_layers": source_layers,
                "interpretation": "technical_sanity_only_no_semantic_claim",
                "prompts": top_k_records,
            },
        )
        return {
            "n_sanity_prompts": len(top_k_records),
            "source_layers": source_layers,
            "positions": [-1],
            "use_jacobian": True,
            "nonempty_finite_shape_correct": True,
            "layer_ordering_correct": True,
            "save_load_numerical_consistency": all_consistent,
            "topk_artifact": {
                "path": topk_path.relative_to(self.output_dir).as_posix(),
                "bytes": topk_path.stat().st_size,
                "sha256": protocol.sha256_file(topk_path),
            },
            "semantic_claim": None,
            "_metrics": {
                "sanity_prompts": (len(top_k_records), "prompts"),
                "applied_layers": (len(source_layers), "layers"),
                "save_load_consistent": (int(all_consistent), "boolean"),
            },
        }

    def run_f5(self) -> dict[str, Any]:
        f2_memory_class = self.results["F2"]["details"]["memory"]["classification"]
        f3_memory_class = self.results["F3"]["details"]["memory"]["classification"]
        combined_memory_class = (
            "green"
            if f2_memory_class == "green" and f3_memory_class == "green"
            else "borderline"
        )
        guard = protocol.f5_cost_guard(
            elapsed_seconds=self.elapsed_seconds,
            f3_seconds=float(self.results["F3"]["details"]["fit_seconds"]),
            memory_classification=combined_memory_class,
        )
        guard["f2_memory_classification"] = f2_memory_class
        guard["f3_memory_classification"] = f3_memory_class
        if not guard["run"]:
            return {
                "_status": "skipped_cost_guard",
                "cost_guard": guard,
                "failure": False,
                "_metrics": {
                    "cost_guard_run": (0, "boolean"),
                    "projected_completion_seconds": (
                        guard["projected_completion_seconds"],
                        "seconds",
                    ),
                },
            }
        prompts = [record["text"] for record in self.corpus_records]
        source_layers = self.layers["f3_source_layers"]
        target_layer = self.layers["target_layer"]
        dim_batch = self.results["F3"]["details"]["dim_batch"]
        singleton_lenses = []
        self._start_gpu_measurement()
        started = time.monotonic()
        for prompt in prompts:
            singleton_lenses.append(
                self.jlens.fit(
                    self.lens_model,
                    prompts=[prompt],
                    source_layers=source_layers,
                    target_layer=target_layer,
                    dim_batch=dim_batch,
                    max_seq_len=protocol.MAX_SEQ_LEN,
                    skip_first=protocol.SKIP_FIRST,
                    checkpoint_path=None,
                    checkpoint_every=None,
                    resume=False,
                )
            )
        merged = self.jlens.JacobianLens.merge(singleton_lenses)
        compare_seconds = time.monotonic() - started
        memory = self._finish_gpu_measurement()
        direct = self.fitted_lens
        if (
            merged.source_layers != direct.source_layers
            or merged.n_prompts != direct.n_prompts
            or merged.d_model != direct.d_model
        ):
            raise protocol.NumericalValidationError("F5 merge metadata mismatch")
        comparisons = {}
        for layer in source_layers:
            if merged.jacobians[layer].shape != direct.jacobians[layer].shape:
                raise protocol.NumericalValidationError("F5 matrix shape mismatch")
            difference = merged.jacobians[layer] - direct.jacobians[layer]
            max_abs = float(difference.abs().max().item())
            relative = float(
                difference.norm().item()
                / max(direct.jacobians[layer].norm().item(), 1e-12)
            )
            if not protocol.finite_numbers([max_abs, relative]):
                raise protocol.NumericalValidationError("F5 comparison is non-finite")
            if max_abs > 1e-5 or relative > 1e-6:
                raise protocol.NumericalValidationError(
                    f"F5 merge mismatch at layer {layer}"
                )
            comparisons[str(layer)] = {
                "shape": list(difference.shape),
                "max_abs": max_abs,
                "relative_norm": relative,
            }
        return {
            "cost_guard": guard,
            "fit_a_prompts": 1,
            "fit_b_prompts": 1,
            "merged_n_prompts": merged.n_prompts,
            "direct_n_prompts": direct.n_prompts,
            "source_layers": source_layers,
            "comparisons": comparisons,
            "compare_seconds": compare_seconds,
            "memory": memory,
            "_metrics": {
                "cost_guard_run": (1, "boolean"),
                "compare_seconds": (compare_seconds, "seconds"),
            },
        }

    def run(self) -> int:
        if not self.persist("tooling-initial"):
            now = utc_now()
            self.results["F0"] = {
                "status": "failed",
                "started_at_utc": now,
                "finished_at_utc": now,
                "duration_seconds": 0.0,
                "failure_class": "checkpoint_failure",
                "error_type": "BlobPersistenceError",
                "error": "required initial snapshot upload failed",
                "details": {"persistence": self.persistence_status()},
            }
            self.persist("F0-initial-persistence-failed", upload=False)
            self.block_remaining("F0", "required Blob persistence failed")
            return 6
        if self.restore_error is not None:
            now = utc_now()
            self.results["F0"] = {
                "status": "failed",
                "started_at_utc": now,
                "finished_at_utc": now,
                "duration_seconds": 0.0,
                "failure_class": "checkpoint_failure",
                **self.restore_error,
                "details": {"blob_restore": self.restore_record},
            }
            self.persist("F0-restore-failed")
            self.block_remaining("F0", "managed-identity Blob recovery failed")
            return 2
        if not self.execute("F0", self.run_f0):
            self.block_remaining("F0", "F0 dependency/provenance gate failed")
            return 2
        if not self.execute("F1", self.run_f1):
            self.block_remaining("F1", "F1 model/official-adapter gate failed")
            return 2

        f2_relative = "checkpoint/phase05_jlens_f2_jacobian.pt"
        if self._valid_prior_artifact("F2", f2_relative):
            self.results["F2"]["details"]["resume_reused_complete_artifact"] = True
            if not self.persist("F2-resumed"):
                self.block_remaining("F2", "required F2 resume snapshot upload failed")
                return 6
        elif not self.execute("F2", self.run_f2):
            self.block_remaining("F2", "F2 real-Jacobian gate failed")
            return 3
        if not self.results["F2"]["details"].get("continue_allowed", True):
            self.block_remaining(
                "F2", "F2 crossed a preregistered memory/time continuation guard"
            )
            return 4

        try:
            reused_f3 = self._reuse_complete_f3()
        except protocol.CheckpointValidationError:
            reused_f3 = False
        if reused_f3:
            if not self.persist("F3-resumed"):
                self.block_remaining("F3", "required F3 resume snapshot upload failed")
                return 6
        elif not self.execute("F3", self.run_f3):
            self.block_remaining("F3", "F3 fit/checkpoint gate failed")
            return 4
        if protocol.f3_memory_requires_stop(self.results["F3"]):
            self.block_remaining(
                "F3", "F3 crossed the preregistered memory hard-stop threshold"
            )
            return 4
        if not self.execute("F4", self.run_f4):
            self.block_remaining("F4", "F4 save/load/apply gate failed")
            return 4
        self.execute("F5", self.run_f5)
        self.environment["tooling_state"] = "EXECUTED"
        final_persisted = self.persist("final")
        decision = self.decision_document()["decision"]
        print(f"Phase 0.5A complete: {decision}; outputs={self.output_dir}")
        if not final_persisted or not self.persistence_status()["ready"]:
            return 6
        return 0 if decision in {"GREEN", "AMBER"} else 5


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=os.getenv("RESULTS_DIR", str(PROJECT_ROOT / "results" / "runs" / "phase05-jlens")),
    )
    parser.add_argument(
        "--corpus",
        default=str(PROJECT_ROOT / "data" / "jlens_feasibility_prompts.jsonl"),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--authorized-compatibility-fix-attempted",
        action="store_true",
        help="Set only after main separately authorizes and integrates one targeted fix.",
    )
    return parser.parse_args(argv)


def _watchdog_signal(signum: int, _frame: Any) -> None:
    raise protocol.ApplicationTimeoutError(f"received watchdog signal {signum}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    signal.signal(signal.SIGTERM, _watchdog_signal)
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _watchdog_signal)
        signal.alarm(protocol.APPLICATION_WATCHDOG_SECONDS)
    try:
        return Phase05Runner(args).run()
    finally:
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
