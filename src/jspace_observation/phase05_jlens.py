"""Model-free controls for the Phase 0.5A Jacobian-lens feasibility run."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

OFFICIAL_REPOSITORY = "https://github.com/anthropics/jacobian-lens"
OFFICIAL_COMMIT = "581d398613e5602a5af361e1c34d3a92ea82ba8e"
OFFICIAL_UV_LOCK_SHA256 = (
    "981e580531e517be1bd1a3fef98ac12822f40d626ba8f365e59973ff258f36ea"
)
JLENS_DISTRIBUTION = "jlens"
JLENS_IMPORT_NAME = "jlens"
JLENS_VERSION = "0.1.0"

MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
MODEL_REVISION = "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
MODEL_ARCHITECTURE = "Qwen2ForCausalLM"
MODEL_LAYERS = 28
MODEL_WIDTH = 1536
CHECKPOINT_DTYPE = "bfloat16"
RUNTIME_DTYPE = "float16"

STAGES = ("F0", "F1", "F2", "F3", "F4", "F5")
REQUIRED_PREDECESSOR = {
    "F0": None,
    "F1": "F0",
    "F2": "F1",
    "F3": "F2",
    "F4": "F3",
    "F5": "F4",
}
TERMINAL_STAGE_STATUSES = {
    "success",
    "failed",
    "blocked",
    "skipped_cost_guard",
}
FAILURE_TAXONOMY = {
    "dependency_failure",
    "adapter_failure",
    "unsupported_autograd",
    "cuda_oom",
    "timeout",
    "numerical_failure",
    "checkpoint_failure",
    "unknown",
}

MAX_SEQ_LEN = 32
SKIP_FIRST = 16
F2_DIM_BATCH = 1
PLATFORM_TIMEOUT_SECONDS = 7200
APPLICATION_WATCHDOG_SECONDS = 6900
PLANNING_BUDGET_SECONDS = 6120
EXPORT_RESERVE_SECONDS = 300
GIB = 1024**3

EXPECTED_DEPENDENCIES = {
    "jlens": JLENS_VERSION,
    "torch": "2.12.0",
    "transformers": "5.9.0",
    "huggingface-hub": "1.16.1",
    "numpy": "2.4.6",
}

METRICS_COLUMNS = (
    "stage",
    "status",
    "metric",
    "value",
    "unit",
    "recorded_at_utc",
)
REQUIRED_OUTPUT_FILENAMES = (
    "phase05_jlens_environment.json",
    "phase05_jlens_stage_results.json",
    "phase05_jlens_metrics.csv",
    "phase05_jlens_decision.json",
    "phase05_jlens_report.md",
    "phase05_jlens_artifact_manifest.json",
)


class Phase05ValidationError(ValueError):
    """A preregistered Phase 0.5A control was violated."""


class DependencyValidationError(Phase05ValidationError):
    """The pinned runtime or provenance is not exact."""


class AdapterValidationError(Phase05ValidationError):
    """The official HF adapter did not match the target architecture."""


class NumericalValidationError(Phase05ValidationError):
    """A required numeric result was non-finite, zero, or malformed."""


class CheckpointValidationError(Phase05ValidationError):
    """A checkpoint or its external controls manifest was invalid."""


class ApplicationTimeoutError(TimeoutError):
    """The application watchdog expired before the platform timeout."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable UTF-8 JSON bytes for hashing and manifests."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_jsonl_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    """Hash JSONL in its declared order; prompt order is part of the control."""

    payload = b"".join(canonical_json_bytes(dict(record)) for record in records)
    return sha256_bytes(payload)


def validate_source_pin(specification: str) -> str:
    """Require the official repository and the exact immutable commit."""

    normalized = specification.strip()
    floating_fragments = (
        "@main",
        "/main",
        "refs/heads/main",
        "jacobian-lens.git@HEAD",
    )
    if any(fragment.lower() in normalized.lower() for fragment in floating_fragments):
        raise DependencyValidationError("floating J-lens source refs are forbidden")
    if OFFICIAL_REPOSITORY not in normalized:
        raise DependencyValidationError("unexpected J-lens repository")
    if OFFICIAL_COMMIT not in normalized:
        raise DependencyValidationError("exact J-lens commit is required")
    return OFFICIAL_COMMIT


def validate_import_name(name: str) -> str:
    if name != JLENS_IMPORT_NAME:
        raise DependencyValidationError(
            f"J-lens must be imported only as {JLENS_IMPORT_NAME!r}"
        )
    return name


def validate_dependency_versions(installed: Mapping[str, str]) -> None:
    mismatches = {
        name: {"expected": expected, "actual": installed.get(name)}
        for name, expected in EXPECTED_DEPENDENCIES.items()
        if installed.get(name) != expected
    }
    if mismatches:
        raise DependencyValidationError(
            f"dependency versions do not match the lock: {mismatches}"
        )


def validate_model_controls(
    *,
    model_id: str,
    revision: str,
    dtype: str,
    trust_remote_code: bool,
    quantized: bool = False,
    compile_model: bool = False,
) -> None:
    errors: list[str] = []
    if model_id != MODEL_ID:
        errors.append("model_id")
    if revision != MODEL_REVISION:
        errors.append("revision")
    if dtype != RUNTIME_DTYPE:
        errors.append("dtype")
    if trust_remote_code:
        errors.append("trust_remote_code")
    if quantized:
        errors.append("quantization")
    if compile_model:
        errors.append("compile")
    if errors:
        raise DependencyValidationError(
            f"target model controls are not exact: {', '.join(errors)}"
        )


def validate_config_metadata(metadata: Mapping[str, Any]) -> None:
    architectures = metadata.get("architectures") or []
    observed_dtype = str(metadata.get("checkpoint_dtype", "")).replace("torch.", "")
    expected = {
        "architecture": MODEL_ARCHITECTURE,
        "n_layers": MODEL_LAYERS,
        "d_model": MODEL_WIDTH,
        "checkpoint_dtype": CHECKPOINT_DTYPE,
        "resolved_revision": MODEL_REVISION,
    }
    actual = {
        "architecture": architectures[0] if len(architectures) == 1 else architectures,
        "n_layers": metadata.get("n_layers"),
        "d_model": metadata.get("d_model"),
        "checkpoint_dtype": observed_dtype,
        "resolved_revision": metadata.get("resolved_revision"),
    }
    if actual != expected:
        raise DependencyValidationError(
            f"target config metadata mismatch: expected={expected}, actual={actual}"
        )


def representative_layers(n_layers: int) -> dict[str, Any]:
    """Choose deterministic source layers relative to the observed depth."""

    if n_layers < 5:
        raise Phase05ValidationError("at least five layers are required")
    target = n_layers - 1
    middle = target // 2
    selected = sorted({target // 4, middle, (3 * target) // 4})
    if len(selected) != 3:
        raise Phase05ValidationError("could not choose three distinct source layers")
    ensure_source_before_target(selected, target, n_layers)
    return {
        "target_layer": target,
        "f2_source_layer": middle,
        "f3_source_layers": selected,
    }


def ensure_source_before_target(
    source_layers: Sequence[int], target_layer: int, n_layers: int
) -> None:
    if (
        not source_layers
        or target_layer < 1
        or target_layer >= n_layers
        or len(set(source_layers)) != len(source_layers)
        or any(layer < 0 or layer >= target_layer for layer in source_layers)
    ):
        raise Phase05ValidationError(
            f"source layers must be unique and below target {target_layer}"
        )


def _token_ids(encoded: Any) -> Any:
    if isinstance(encoded, Mapping):
        ids = encoded["input_ids"]
    else:
        ids = encoded.input_ids
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    if ids and isinstance(ids[0], (list, tuple)):
        ids = ids[0]
    return ids


def guarded_token_length(
    tokenizer: Any,
    text: str,
    *,
    minimum: int = 24,
    maximum: int = MAX_SEQ_LEN,
) -> int:
    encoded = tokenizer(
        text,
        truncation=True,
        max_length=maximum,
        add_special_tokens=True,
    )
    length = len(_token_ids(encoded))
    if not minimum <= length <= maximum:
        raise Phase05ValidationError(
            f"tokenized prompt length {length} is outside [{minimum}, {maximum}]"
        )
    if length <= SKIP_FIRST + 1:
        raise Phase05ValidationError("prompt leaves no valid Jacobian positions")
    return length


def valid_position_count(seq_len: int, *, skip_first: int = SKIP_FIRST) -> int:
    count = seq_len - skip_first - 1
    if count <= 0:
        raise Phase05ValidationError("no valid source positions remain")
    return count


def finite_numbers(values: Iterable[Any]) -> bool:
    try:
        return all(math.isfinite(float(value)) for value in values)
    except (TypeError, ValueError):
        return False


def validate_jacobian_summary(
    *,
    shape: Sequence[int],
    dtype: str,
    finite: bool,
    norm: float,
) -> None:
    if list(shape) != [MODEL_WIDTH, MODEL_WIDTH]:
        raise NumericalValidationError(f"unexpected Jacobian shape: {list(shape)}")
    if dtype not in {"torch.float32", "float32"}:
        raise NumericalValidationError(f"unexpected Jacobian dtype: {dtype}")
    if not finite or not math.isfinite(norm) or norm <= 0:
        raise NumericalValidationError("Jacobian must be finite and nonzero")


def validate_apply_controls(*, use_jacobian: bool, layers: Sequence[int]) -> None:
    if not use_jacobian:
        raise Phase05ValidationError(
            "vanilla logit-lens substitution is forbidden for F4"
        )
    if not layers:
        raise Phase05ValidationError("F4 must apply fitted Jacobian layers")


def can_start_stage(stage: str, results: Mapping[str, Mapping[str, Any]]) -> bool:
    if stage not in REQUIRED_PREDECESSOR:
        raise Phase05ValidationError(f"unknown stage: {stage}")
    predecessor = REQUIRED_PREDECESSOR[stage]
    return predecessor is None or results.get(predecessor, {}).get("status") == "success"


def stages_after_failure(
    failed_stage: str, results: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    del results
    index = STAGES.index(failed_stage)
    return list(STAGES[index + 1 :])


def classify_failure(error: BaseException, stage: str) -> str:
    name = type(error).__name__.lower()
    message = str(error).lower()
    if isinstance(error, ApplicationTimeoutError) or "timeout" in name:
        return "timeout"
    if isinstance(error, CheckpointValidationError) or "checkpoint" in name:
        return "checkpoint_failure"
    if isinstance(error, AdapterValidationError):
        return "adapter_failure"
    if isinstance(error, DependencyValidationError) or isinstance(
        error, (ImportError, ModuleNotFoundError)
    ):
        return "dependency_failure"
    if stage == "F0":
        return "dependency_failure"
    if "outofmemory" in name or "out of memory" in message or "cuda oom" in message:
        return "cuda_oom"
    if (
        "autograd" in message
        or "derivative for" in message
        or "does not require grad" in message
        or "not implemented" in message
    ):
        return "unsupported_autograd"
    if isinstance(error, NumericalValidationError) or any(
        fragment in message
        for fragment in ("non-finite", "not finite", "nan", "infinite", "nonzero")
    ):
        return "numerical_failure"
    if stage == "F1" and any(
        fragment in message
        for fragment in ("layout", "layer", "unembed", "adapter", "hook")
    ):
        return "adapter_failure"
    return "unknown"


def classify_memory(
    *,
    gpu_peak_reserved_bytes: int,
    gpu_total_bytes: int,
    gpu_free_bytes: int,
    host_rss_bytes: int,
    host_total_bytes: int,
) -> dict[str, Any]:
    if gpu_total_bytes <= 0 or host_total_bytes <= 0:
        raise Phase05ValidationError("memory totals must be positive")
    gpu_ratio = gpu_peak_reserved_bytes / gpu_total_bytes
    host_ratio = host_rss_bytes / host_total_bytes
    hard_stop = (
        gpu_peak_reserved_bytes * 100 >= gpu_total_bytes * 92
        or gpu_free_bytes < GIB
        or host_ratio >= 0.90
    )
    green = (
        not hard_stop
        and gpu_peak_reserved_bytes * 100 <= gpu_total_bytes * 85
        and gpu_free_bytes >= 2 * GIB
        and host_ratio <= 0.75
    )
    classification = "stop" if hard_stop else ("green" if green else "borderline")
    return {
        "classification": classification,
        "gpu_peak_reserved_ratio": gpu_ratio,
        "gpu_free_gib": gpu_free_bytes / GIB,
        "host_rss_ratio": host_ratio,
        "thresholds": {
            "gpu_green_max_ratio": 0.85,
            "gpu_stop_min_ratio": 0.92,
            "gpu_green_min_free_gib": 2,
            "gpu_stop_below_free_gib": 1,
            "host_green_max_ratio": 0.75,
            "host_stop_min_ratio": 0.90,
        },
    }


def choose_f3_dim_batch(
    memory: Mapping[str, Any], *, f2_wall_seconds: float
) -> int:
    return (
        2
        if memory.get("classification") == "green"
        and float(memory.get("gpu_peak_reserved_ratio", 1.0)) <= 0.65
        and float(memory.get("gpu_free_gib", 0.0)) >= 4.0
        and math.isfinite(f2_wall_seconds)
        and 0 < f2_wall_seconds < APPLICATION_WATCHDOG_SECONDS
        else 1
    )


def f3_dim1_time_guard(
    *,
    elapsed_seconds: float,
    f2_wall_seconds: float,
    f2_source_layer: int,
    f3_source_layers: Sequence[int],
    target_layer: int,
    prompt_count: int = 2,
) -> dict[str, Any]:
    """Conservatively scale F2 time by prompt count and backward layer span."""

    ensure_source_before_target([f2_source_layer], target_layer, target_layer + 1)
    ensure_source_before_target(f3_source_layers, target_layer, target_layer + 1)
    if prompt_count < 1 or not math.isfinite(f2_wall_seconds) or f2_wall_seconds <= 0:
        raise Phase05ValidationError("invalid F3 time-guard inputs")
    f2_span = target_layer - f2_source_layer
    f3_span = target_layer - min(f3_source_layers)
    layer_span_ratio = f3_span / f2_span
    multiplier = prompt_count * max(1.0, layer_span_ratio)
    projected_fit_seconds = f2_wall_seconds * multiplier
    projected_completion = (
        elapsed_seconds + projected_fit_seconds + EXPORT_RESERVE_SECONDS
    )
    return {
        "f2_source_layer": f2_source_layer,
        "f3_earliest_source_layer": min(f3_source_layers),
        "target_layer": target_layer,
        "f2_layer_span": f2_span,
        "f3_earliest_layer_span": f3_span,
        "layer_span_ratio": layer_span_ratio,
        "prompt_count": prompt_count,
        "conservative_multiplier": multiplier,
        "projected_fit_seconds": projected_fit_seconds,
        "projected_completion_seconds": projected_completion,
        "planning_budget_seconds": PLANNING_BUDGET_SECONDS,
        "continue_allowed": projected_completion <= PLANNING_BUDGET_SECONDS,
    }


def f3_checkpoint_actions(n_done: int, next_idx: int) -> list[str]:
    """Return the required official-fit/persistence actions for a checkpoint."""

    if (n_done, next_idx) not in {(0, 0), (1, 1), (2, 2)}:
        raise CheckpointValidationError(
            f"invalid F3 checkpoint progress: n_done={n_done}, next_idx={next_idx}"
        )
    if n_done == 0:
        return ["fit_prompt_1", "persist_prompt_1", "fit_full_resume"]
    if n_done == 1:
        return ["persist_prompt_1", "fit_full_resume"]
    return ["load_full_resume"]


def f3_memory_requires_stop(f3_result: Mapping[str, Any]) -> bool:
    return (
        f3_result.get("details", {})
        .get("memory", {})
        .get("classification")
        == "stop"
    )


def f5_cost_guard(
    *,
    elapsed_seconds: float,
    f3_seconds: float,
    memory_classification: str,
    export_reserve_seconds: int = EXPORT_RESERVE_SECONDS,
) -> dict[str, Any]:
    projected_seconds = elapsed_seconds + f3_seconds + export_reserve_seconds
    allowed = (
        memory_classification == "green"
        and projected_seconds <= PLANNING_BUDGET_SECONDS
        and projected_seconds < APPLICATION_WATCHDOG_SECONDS
    )
    return {
        "run": allowed,
        "status": "eligible" if allowed else "skipped_cost_guard",
        "elapsed_seconds": elapsed_seconds,
        "projected_completion_seconds": projected_seconds,
        "planning_budget_seconds": PLANNING_BUDGET_SECONDS,
        "application_watchdog_seconds": APPLICATION_WATCHDOG_SECONDS,
        "export_reserve_seconds": export_reserve_seconds,
        "memory_classification": memory_classification,
    }


def measured_scaling_plan(
    *,
    seconds_per_prompt: float,
    memory_classification: str,
    fixed_overhead_seconds: float = 0.0,
) -> dict[str, Any]:
    def path(prompt_count: int, slices: list[int]) -> dict[str, Any]:
        longest_slice = max(slices)
        estimated_longest = (
            fixed_overhead_seconds
            + longest_slice * seconds_per_prompt
            + EXPORT_RESERVE_SECONDS
        )
        return {
            "prompt_count": prompt_count,
            "slices": slices,
            "seconds_per_prompt_measured": seconds_per_prompt,
            "fixed_environment_and_load_seconds_measured": fixed_overhead_seconds,
            "estimated_longest_job_seconds": estimated_longest,
            "measured_projection": True,
            "executable": (
                memory_classification == "green"
                and estimated_longest <= PLANNING_BUDGET_SECONDS
                and estimated_longest < APPLICATION_WATCHDOG_SECONDS
            ),
        }

    return {
        "ten_prompt": path(10, [10]),
        "sliced_25_prompt": path(25, [10, 10, 5]),
    }


def make_checkpoint_controls(
    *,
    prompt_order_sha256: str,
    source_layers: Sequence[int],
    target_layer: int,
    dim_batch: int,
) -> dict[str, Any]:
    ensure_source_before_target(source_layers, target_layer, MODEL_LAYERS)
    return {
        "schema_version": "phase05-jlens-checkpoint-controls-v1",
        "official_repository": OFFICIAL_REPOSITORY,
        "official_commit": OFFICIAL_COMMIT,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "prompt_order_sha256": prompt_order_sha256,
        "source_layers": list(source_layers),
        "target_layer": target_layer,
        "dim_batch": dim_batch,
        "max_seq_len": MAX_SEQ_LEN,
        "skip_first": SKIP_FIRST,
        "runtime_dtype": RUNTIME_DTYPE,
        "jacobian_dtype": "float32",
        "backend": "official-jlens-fit",
        "checkpoint_every": 1,
        "resume": True,
    }


def make_checkpoint_manifest(controls: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(controls)
    return {
        "controls": normalized,
        "controls_sha256": sha256_bytes(canonical_json_bytes(normalized)),
    }


def validate_checkpoint_manifest(
    manifest: Mapping[str, Any], expected_controls: Mapping[str, Any]
) -> None:
    controls = manifest.get("controls")
    expected = dict(expected_controls)
    if controls != expected:
        raise CheckpointValidationError("checkpoint controls do not match this run")
    expected_hash = sha256_bytes(canonical_json_bytes(expected))
    if manifest.get("controls_sha256") != expected_hash:
        raise CheckpointValidationError("checkpoint controls hash is invalid")


def validate_blob_auth_config(config: Mapping[str, Any]) -> None:
    if config.get("credential_mode") != "default_credential_managed_identity_only":
        raise Phase05ValidationError("Blob auth must use managed identity only")
    forbidden_fragments = ("secret", "password", "token", "sas", "sharedkey", "accountkey")
    for key, value in config.items():
        normalized = str(key).lower().replace("_", "")
        if key == "managed_identity_client_id":
            continue
        if any(fragment in normalized for fragment in forbidden_fragments) and value:
            raise Phase05ValidationError(f"secret-bearing Blob field forbidden: {key}")


def persistence_summary(
    upload_history: Sequence[Mapping[str, Any]], *, configured: bool
) -> dict[str, Any]:
    """Evaluate the required Blob persistence transaction history."""

    if not configured:
        return {
            "configured": False,
            "required": False,
            "ready": True,
            "status": "not_configured",
            "required_uploads": 0,
            "failed_uploads": [],
            "final_manifest_completion_confirmed": False,
        }
    required = [dict(item) for item in upload_history if item.get("required")]
    failed = [
        item
        for item in required
        if item.get("status") != "confirmed"
        or not item.get("manifest_uploaded_last")
    ]
    final_confirmed = any(
        item.get("stage_label") == "final"
        and item.get("status") == "confirmed"
        and item.get("manifest_uploaded_last") is True
        for item in required
    )
    ready = not failed and final_confirmed
    if failed:
        status = "checkpoint_failure"
    elif not final_confirmed:
        status = "awaiting_final_manifest_completion"
    else:
        status = "confirmed"
    return {
        "configured": True,
        "required": True,
        "ready": ready,
        "status": status,
        "failure_class": None if ready else "checkpoint_failure",
        "required_uploads": len(required),
        "failed_uploads": failed,
        "final_manifest_completion_confirmed": final_confirmed,
    }


def derive_decision(
    results: Mapping[str, Mapping[str, Any]],
    *,
    authorized_compatibility_fix_attempted: bool,
    scaling_plan: Mapping[str, Any] | None,
    persistence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    f0 = results.get("F0", {})
    f1 = results.get("F1", {})
    f2 = results.get("F2", {})
    f3 = results.get("F3", {})
    f4 = results.get("F4", {})

    if f0.get("status") != "success" or f1.get("status") != "success":
        decision = {
            "decision": "UNRATED",
            "gate_status": "BLOCKED",
            "reason": "Pinned dependency/provenance or F1 adapter gate is blocked.",
            "plan_b_triggered": False,
        }
    elif f2.get("status") != "success":
        if authorized_compatibility_fix_attempted and f2.get("status") == "failed":
            decision = {
                "decision": "RED",
                "gate_status": "COMPLETE",
                "reason": "The minimal real Jacobian failed after one authorized compatibility fix.",
                "plan_b_triggered": False,
            }
        else:
            decision = {
                "decision": "UNRATED",
                "gate_status": "BLOCKED",
                "reason": "F2 failed; RED requires one separately authorized compatibility fix.",
                "plan_b_triggered": False,
            }
    elif f3.get("status") != "success" or f4.get("status") != "success":
        decision = {
            "decision": "AMBER",
            "gate_status": "COMPLETE",
            "reason": "Real F2 worked, but fit/checkpoint/apply did not complete safely.",
            "plan_b_triggered": False,
        }
    else:
        memory_classes = [
            f2.get("details", {}).get("memory", {}).get("classification"),
            f3.get("details", {}).get("memory", {}).get("classification"),
        ]
        scaling_ready = bool(
            scaling_plan
            and scaling_plan.get("ten_prompt", {}).get("executable")
            and scaling_plan.get("sliced_25_prompt", {}).get("executable")
        )
        if any(item != "green" for item in memory_classes) or not scaling_ready:
            decision = {
                "decision": "AMBER",
                "gate_status": "COMPLETE",
                "reason": "F0-F4 worked, but measured memory or scaling margin is borderline.",
                "plan_b_triggered": False,
            }
        else:
            decision = {
                "decision": "GREEN",
                "gate_status": "COMPLETE",
                "reason": "F0-F4, save/load/apply, memory, and measured scaling gates passed.",
                "plan_b_triggered": False,
            }

    if persistence and persistence.get("required") and not persistence.get("ready"):
        scientific_decision = decision["decision"]
        after_real_f2 = f2.get("status") == "success"
        return {
            "decision": "AMBER" if after_real_f2 else "UNRATED",
            "gate_status": "BLOCKED",
            "reason": (
                "Required Blob persistence is incomplete or failed; "
                "checkpoint/manifest durability is not established."
            ),
            "plan_b_triggered": False,
            "scientific_decision_before_persistence_gate": scientific_decision,
            "persistence_failure_class": "checkpoint_failure",
        }
    return decision


def build_artifact_manifest(
    output_dir: str | Path,
    *,
    generated_at_utc: str,
    exclude_names: Sequence[str] = ("phase05_jlens_artifact_manifest.json",),
) -> dict[str, Any]:
    root = Path(output_dir)
    entries = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative_path = path.relative_to(root)
        if (
            not path.is_file()
            or path.name in exclude_names
            or any(part.startswith(".") for part in relative_path.parts)
            or ".tmp." in path.name
        ):
            continue
        relative = relative_path.as_posix()
        entries.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": "phase05-jlens-artifact-manifest-v1",
        "generated_at_utc": generated_at_utc,
        "artifacts": entries,
        "manifest_order": [entry["path"] for entry in entries],
    }


def validate_output_schema(
    *,
    environment: Mapping[str, Any],
    stage_results: Mapping[str, Any],
    decision: Mapping[str, Any],
    metrics_header: Sequence[str],
    manifest: Mapping[str, Any],
) -> None:
    if environment.get("schema_version") != "phase05-jlens-environment-v1":
        raise Phase05ValidationError("invalid environment schema")
    if stage_results.get("schema_version") != "phase05-jlens-stage-results-v1":
        raise Phase05ValidationError("invalid stage-results schema")
    if decision.get("decision") not in {"GREEN", "AMBER", "RED", "UNRATED"}:
        raise Phase05ValidationError("invalid decision")
    if tuple(metrics_header) != METRICS_COLUMNS:
        raise Phase05ValidationError("invalid metrics CSV schema")
    paths = [entry.get("path") for entry in manifest.get("artifacts", [])]
    if paths != sorted(paths):
        raise Phase05ValidationError("artifact manifest is not path-sorted")
