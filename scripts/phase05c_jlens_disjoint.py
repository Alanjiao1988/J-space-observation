#!/usr/bin/env python3
"""Phase 0.5C J-lens disjoint-replication runner.

Loads the already-fitted Phase 0.5B 25-prompt lens (25A), fits a second
25-prompt lens (25B) on the prompt-disjoint reserve block in 10/10/5 shards,
merges the two with the official weighted merge into a 50-prompt lens (50M),
and measures the numerical difference between the three operators.

Engineering numerics only. The 25-prompt Phase 0.5B lens is never re-fitted and
no direct 50-prompt fit is performed. Top-k overlap and rank correlation are
technical stability statistics; they are never semantic evidence and support no
claim about a workspace, hidden reasoning, an internal chain-of-thought,
J-space, semantic convergence, or any lens being scientifically usable.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import os
import platform
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = PROJECT_ROOT / "src" / "jspace_observation"
SCRIPT_ROOT = Path(__file__).resolve().parent
for _entry in (str(HELPER_ROOT), str(SCRIPT_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import phase05_jlens as base  # noqa: E402
import phase05_jlens_feasibility as feasibility  # noqa: E402
import phase05_jlens_saturation as sat  # noqa: E402
import phase05c_jlens_disjoint as protocol  # noqa: E402

DIM_BATCH_2_JUSTIFICATION = (
    "Phase 0.5A F2 measured a green memory classification at dim_batch=1 "
    "(peak reserved 3808428032 of 16704405504 bytes, ratio 0.2280) and F3 "
    "completed at dim_batch=2, so dim_batch=2 has recorded headroom."
)

REGISTERED_SECONDS_PER_PROMPT = 26.84
REGISTERED_FIXED_OVERHEAD_SECONDS = 41.0
# Phase 0.5B measured 52.674683 s/prompt at dim_batch=1 for the 25-prompt fit.
MEASURED_SECONDS_PER_PROMPT = 52.68
PESSIMISTIC_SECONDS_PER_PROMPT = 53.68

DEFAULT_EXISTING_LENS_PATH = "/workspace/runtime/staged/fit_b_merged_lens.pt"


class DisjointBlobTransport(feasibility.BlobTransport):
    """Artifact-pack transport that always uploads the manifest last."""

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
                path.name == protocol.MANIFEST_FILENAME,
                path.relative_to(output_dir).as_posix(),
            ),
        )

    def snapshot_destination(self, stage: str, sequence: int) -> str:
        return f"{self.run_prefix}/attempts/{self.attempt_id}/{sequence:02d}-{stage}"

    def download_to(self, blob_name: str, destination: Path) -> dict[str, Any]:
        """Read-only fetch of one already-existing blob (managed identity)."""

        if not self.configured:
            raise protocol.ExistingLensValidationError(
                "Blob staging requested without account/container configuration"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        client = self._client()
        stream = client.download_blob(blob_name.strip("/"))
        temporary = destination.with_name(f".{destination.name}.tmp.{os.getpid()}")
        try:
            with temporary.open("wb") as handle:
                stream.readinto(handle)
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {
            "blob": blob_name.strip("/"),
            "container": self.container,
            "account": self.account,
            "path": destination.as_posix(),
            "bytes": destination.stat().st_size,
            "sha256": base.sha256_file(destination),
        }


class RealBackend:
    """Official torch/transformers/jlens backend used inside the GPU container."""

    is_synthetic = False
    name = "official_jlens"

    def __init__(self, *, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.torch = importlib.import_module("torch")
        self.transformers = importlib.import_module("transformers")
        self.jlens = importlib.import_module("jlens")
        self.math = protocol.TorchLensMath(self.torch)
        self.source_layers = list(protocol.SOURCE_LAYERS)
        self.target_layer = protocol.TARGET_LAYER
        self.tokenizer: Any = None
        self.hf_model: Any = None
        self.lens_model: Any = None
        self.d_model = protocol.MODEL_WIDTH

    def environment(self) -> dict[str, Any]:
        installed = {}
        for name in ("torch", "transformers", "jlens", "accelerate", "safetensors"):
            try:
                installed[name] = importlib.metadata.version(name)
            except Exception:  # noqa: BLE001 - optional dependency probe
                installed[name] = None
        cuda_available = bool(self.torch.cuda.is_available())
        payload: dict[str, Any] = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "installed": installed,
            "cuda_available": cuda_available,
            "source_pin": base.validate_source_pin(
                f"{base.OFFICIAL_REPOSITORY}@{base.OFFICIAL_COMMIT}"
            ),
        }
        if cuda_available:
            free_bytes, total_bytes = self.torch.cuda.mem_get_info()
            payload["gpu_name"] = self.torch.cuda.get_device_name(0)
            payload["gpu_total_bytes"] = total_bytes
            payload["gpu_free_bytes"] = free_bytes
        return payload

    def prepare(self) -> dict[str, Any]:
        base.validate_model_controls(
            model_id=base.MODEL_ID,
            revision=base.MODEL_REVISION,
            dtype=base.RUNTIME_DTYPE,
            trust_remote_code=False,
            quantized=False,
            compile_model=False,
        )
        if not self.torch.cuda.is_available():
            raise base.DependencyValidationError("the disjoint run requires a GPU")
        self.torch.manual_seed(protocol.SEEDS["torch"])
        self.torch.set_grad_enabled(True)
        config = self.transformers.AutoConfig.from_pretrained(
            base.MODEL_ID, revision=base.MODEL_REVISION, trust_remote_code=False
        )
        config.use_cache = False
        config.output_hidden_states = False
        self.tokenizer = self.transformers.AutoTokenizer.from_pretrained(
            base.MODEL_ID, revision=base.MODEL_REVISION, trust_remote_code=False
        )
        self.hf_model = self.transformers.AutoModelForCausalLM.from_pretrained(
            base.MODEL_ID,
            revision=base.MODEL_REVISION,
            config=config,
            dtype=self.torch.float16,
            trust_remote_code=False,
        )
        self.hf_model.to(self.torch.device("cuda:0"))
        self.hf_model.eval()
        self.hf_model.config.use_cache = False
        self.hf_model.config.output_hidden_states = False
        if getattr(self.hf_model.config, "_commit_hash", None) != base.MODEL_REVISION:
            raise base.DependencyValidationError("loaded model revision mismatch")
        floating = {
            str(parameter.dtype)
            for parameter in self.hf_model.parameters()
            if parameter.is_floating_point()
        }
        if floating != {"torch.float16"}:
            raise base.DependencyValidationError(
                f"model parameter dtype mismatch: {floating}"
            )
        self.lens_model = self.jlens.from_hf(
            self.hf_model,
            self.tokenizer,
            layout=None,
            text_module=None,
            compile=False,
            force_bos=True,
        )
        if self.lens_model.n_layers != base.MODEL_LAYERS:
            raise base.AdapterValidationError("adapter layer count mismatch")
        if self.lens_model.d_model != base.MODEL_WIDTH:
            raise base.AdapterValidationError("adapter residual width mismatch")
        self.d_model = int(self.lens_model.d_model)
        return {
            "model_id": base.MODEL_ID,
            "model_revision": base.MODEL_REVISION,
            "runtime_dtype": base.RUNTIME_DTYPE,
            "n_layers": self.lens_model.n_layers,
            "d_model": self.lens_model.d_model,
            "layout_path": self.lens_model.layout.path,
            "source_layers": list(self.source_layers),
            "target_layer": self.target_layer,
            "max_seq_len": protocol.MAX_SEQ_LEN,
            "skip_first": protocol.SKIP_FIRST,
        }

    def token_count(self, text: str) -> int:
        return base.guarded_token_length(self.tokenizer, text)

    def fit(
        self,
        prompts: list[str],
        *,
        checkpoint_path: Path | None = None,
        dim_batch: int = protocol.DEFAULT_DIM_BATCH,
        resume: bool = False,
    ) -> Any:
        return self.jlens.fit(
            self.lens_model,
            prompts=list(prompts),
            source_layers=list(self.source_layers),
            target_layer=self.target_layer,
            dim_batch=dim_batch,
            max_seq_len=protocol.MAX_SEQ_LEN,
            skip_first=protocol.SKIP_FIRST,
            checkpoint_path=None if checkpoint_path is None else str(checkpoint_path),
            checkpoint_every=None if checkpoint_path is None else 1,
            resume=bool(resume and checkpoint_path is not None),
        )

    def merge(self, lenses: list[Any]) -> Any:
        return self.jlens.JacobianLens.merge(list(lenses))

    def load_lens(self, path: str | Path) -> Any:
        return self.jlens.JacobianLens.load(str(path))

    def save_lens(self, lens: Any, path: Path) -> tuple[Any, dict[str, Any]]:
        return feasibility.save_lossless_jacobian_lens(
            self.torch, self.jlens, lens, Path(path)
        )

    def apply(
        self, lens: Any, text: str
    ) -> tuple[dict[int, list[float]], list[float], int]:
        lens_logits, model_logits, input_ids = lens.apply(
            self.lens_model,
            text,
            layers=list(self.source_layers),
            positions=[-1],
            max_seq_len=protocol.MAX_SEQ_LEN,
            use_jacobian=True,
        )
        if list(lens_logits) != list(self.source_layers):
            raise base.NumericalValidationError("apply layer ordering changed")
        if not self.torch.isfinite(model_logits).all():
            raise base.NumericalValidationError("apply model logits are non-finite")
        logits = {}
        for layer in self.source_layers:
            tensor = lens_logits[layer]
            if not self.torch.isfinite(tensor).all():
                raise base.NumericalValidationError(
                    f"apply lens logits are non-finite at layer {layer}"
                )
            logits[int(layer)] = self.math.to_list(tensor)
        return logits, self.math.to_list(model_logits), int(input_ids.shape[-1])

    def lens_metadata(self, lens: Any) -> dict[str, Any]:
        return {
            "n_prompts": int(lens.n_prompts),
            "source_layers": [int(layer) for layer in lens.source_layers],
            "d_model": int(lens.d_model),
        }

    def jacobians(self, lens: Any) -> dict[int, Any]:
        return {int(layer): lens.jacobians[layer] for layer in self.source_layers}

    def start_memory(self) -> None:
        self.torch.cuda.synchronize()
        self.torch.cuda.empty_cache()
        self.torch.cuda.reset_peak_memory_stats()

    def finish_memory(self) -> dict[str, Any]:
        self.torch.cuda.synchronize()
        free_bytes, total_bytes = self.torch.cuda.mem_get_info()
        psutil = importlib.import_module("psutil")
        process = psutil.Process()
        virtual = psutil.virtual_memory()
        peak_allocated = int(self.torch.cuda.max_memory_allocated())
        peak_reserved = int(self.torch.cuda.max_memory_reserved())
        memory = base.classify_memory(
            gpu_peak_reserved_bytes=peak_reserved,
            gpu_total_bytes=total_bytes,
            gpu_free_bytes=free_bytes,
            host_rss_bytes=process.memory_info().rss,
            host_total_bytes=virtual.total,
        )
        return {
            **memory,
            "gpu_peak_allocated_bytes": peak_allocated,
            "gpu_peak_reserved_bytes": peak_reserved,
            "gpu_total_bytes": int(total_bytes),
            "gpu_free_bytes": int(free_bytes),
            "host_rss_bytes": int(process.memory_info().rss),
            "host_total_bytes": int(virtual.total),
        }


def _self_test_backend_metadata(backend: Any) -> dict[str, Any]:
    return {
        "model_id": "synthetic-self-test",
        "model_revision": "synthetic",
        "runtime_dtype": "float64",
        "n_layers": protocol.MODEL_LAYERS,
        "d_model": backend.d_model,
        "layout_path": "not_applicable",
        "source_layers": list(backend.source_layers),
        "target_layer": backend.target_layer,
        "max_seq_len": protocol.MAX_SEQ_LEN,
        "skip_first": protocol.SKIP_FIRST,
    }


def _lens_metadata(backend: Any, lens: Any) -> dict[str, Any]:
    if hasattr(backend, "lens_metadata"):
        return backend.lens_metadata(lens)
    return {
        "n_prompts": int(lens.n_prompts),
        "source_layers": [int(layer) for layer in lens.source_layers],
        "d_model": int(lens.d_model),
    }


def _jacobians(backend: Any, lens: Any) -> dict[int, Any]:
    if hasattr(backend, "jacobians"):
        return backend.jacobians(lens)
    return {int(layer): lens.jacobians[layer] for layer in backend.source_layers}


def code_commit() -> str | None:
    env_commit = os.getenv("JSPACE_CODE_COMMIT", "").strip()
    if env_commit:
        return env_commit
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - provenance probe only
        return None


class DisjointRunner:
    """Executes S0-S7 and always exports the standard artifact pack."""

    def __init__(self, args: argparse.Namespace, backend: Any | None = None) -> None:
        self.args = args
        self.output_dir = Path(args.output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.started_monotonic = time.monotonic()
        self.start_time_utc = feasibility.utc_now()
        self.run_id = (
            str(args.run_id).strip()
            or os.getenv("JSPACE_PHASE05C_RUN_ID", "").strip()
            or feasibility.utc_stamp()
        )
        self.attempt_id = os.getenv("JSPACE_ATTEMPT_ID", "primary").strip() or "primary"
        prefix = os.getenv("JSPACE_BLOB_PREFIX", "").strip()
        self.blob_prefix = prefix or f"{protocol.PHASE}/{self.run_id}"
        self.pack_dir = self.output_dir / protocol.PHASE / protocol.TRACK / self.run_id
        self.work_dir = (
            self.output_dir / protocol.PHASE / protocol.TRACK / f"{self.run_id}-work"
        )
        self.self_test = bool(args.self_test or args.dry_run)
        self.dry_run = bool(args.dry_run)
        self.dim_batch = int(args.dim_batch)
        if self.dim_batch not in protocol.ALLOWED_DIM_BATCH:
            raise protocol.DisjointValidationError(
                f"dim_batch must be one of {list(protocol.ALLOWED_DIM_BATCH)}"
            )
        self.corpus = protocol.load_disjoint_corpus(args.corpus)
        self.plan = protocol.build_disjoint_fit_plan(self.corpus)
        self.existing_lens_path = Path(
            str(args.existing_lens_path).strip()
            or os.getenv("JSPACE_EXISTING_LENS_PATH", "").strip()
            or DEFAULT_EXISTING_LENS_PATH
        )
        self.existing_lens_blob = (
            str(args.existing_lens_blob).strip()
            or os.getenv("JSPACE_EXISTING_LENS_BLOB", "").strip()
            or ("" if self.self_test else protocol.EXISTING_LENS_BLOB)
        )
        self.existing_lens_sha256 = (
            str(args.existing_lens_sha256).strip()
            or protocol.EXISTING_LENS_SHA256
        )
        self.backend = backend or (
            protocol.DisjointSelfTestBackend()
            if self.self_test
            else RealBackend(output_dir=self.work_dir)
        )
        self.math = self.backend.math
        self.stages: dict[str, dict[str, Any]] = {}
        self.records: list[dict[str, Any]] = []
        self.metrics: list[dict[str, Any]] = []
        self.paper_rows: list[dict[str, Any]] = []
        self.figure_rows: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.deviations: list[dict[str, Any]] = []
        self.unregistered_changes: list[dict[str, Any]] = []
        self.values: dict[str, Any] = {}
        self.result_notes: list[str] = []
        self.blocked_reason: str | None = None
        self.merged_improvement: dict[str, Any] | None = None
        self.lenses: dict[str, Any] = {}
        self.state: dict[str, Any] = {"finite_numerator": 0, "finite_denominator": 0}
        self.blob: Any = None
        if not self.self_test:
            self.blob = DisjointBlobTransport(self.blob_prefix, self.attempt_id)
        if self.dim_batch != protocol.DEFAULT_DIM_BATCH:
            self.deviations.append(
                {
                    "id": "dim-batch-raised",
                    "description": (
                        f"dim_batch={self.dim_batch} instead of the protocol default "
                        f"{protocol.DEFAULT_DIM_BATCH}."
                    ),
                    "justification": DIM_BATCH_2_JUSTIFICATION,
                    "effect_on_interpretation": "none",
                }
            )
        if not self.plan["lens_25a_matches_phase05b_order"]:
            raise protocol.DisjointValidationError(
                "the role=fit prompt order does not reproduce the Phase 0.5B "
                "25-prompt fit order; the staged lens cannot be attributed"
            )

    # ------------------------------------------------------------------
    # bookkeeping helpers
    # ------------------------------------------------------------------
    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_monotonic

    def add_metric(self, metric: str, value: Any, **kwargs: Any) -> None:
        self.metrics.append(
            protocol.make_metric_row(run_id=self.run_id, metric=metric, value=value, **kwargs)
        )

    def add_paper_row(self, **kwargs: Any) -> None:
        self.paper_rows.append(protocol.make_paper_row(run_id=self.run_id, **kwargs))

    def add_figure_row(self, **kwargs: Any) -> None:
        self.figure_rows.append(protocol.make_figure_row(run_id=self.run_id, **kwargs))

    def add_record(self, **kwargs: Any) -> None:
        self.records.append(protocol.make_record(run_id=self.run_id, **kwargs))

    def execute(self, stage: str, function: Any) -> bool:
        predecessor = protocol.REQUIRED_PREDECESSOR[stage]
        if predecessor and self.stages.get(predecessor, {}).get("status") != "success":
            self.stages[stage] = {
                "status": "blocked",
                "duration_seconds": 0.0,
                "started_at_utc": feasibility.utc_now(),
                "finished_at_utc": feasibility.utc_now(),
                "details": {"blocked_by": predecessor},
            }
            return False
        started_utc = feasibility.utc_now()
        started = time.monotonic()
        try:
            details = function()
        except BaseException as error:  # noqa: BLE001 - always export the pack
            duration = time.monotonic() - started
            message = feasibility.safe_error(error)
            self.errors.append(
                {
                    "stage": stage,
                    "error_type": type(error).__name__,
                    "error": message,
                    "traceback_tail": traceback.format_exc()[-1200:],
                }
            )
            self.stages[stage] = {
                "status": "failed",
                "duration_seconds": duration,
                "started_at_utc": started_utc,
                "finished_at_utc": feasibility.utc_now(),
                "details": {"error_type": type(error).__name__, "error": message},
            }
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            return False
        duration = time.monotonic() - started
        status = str(details.pop("_status", "success"))
        self.stages[stage] = {
            "status": status,
            "duration_seconds": duration,
            "started_at_utc": started_utc,
            "finished_at_utc": feasibility.utc_now(),
            "details": details,
        }
        return status == "success"

    def time_admission(self, stage: str, prompts: int) -> dict[str, Any]:
        per_prompt = (
            PESSIMISTIC_SECONDS_PER_PROMPT
            if self.dim_batch == 1
            else REGISTERED_SECONDS_PER_PROMPT
        )
        estimate = REGISTERED_FIXED_OVERHEAD_SECONDS + per_prompt * prompts
        admission = base.f3_segment_time_guard(
            elapsed_seconds=self.elapsed_seconds,
            estimated_remaining_fit_seconds=estimate,
        )
        admission["stage"] = stage
        admission["prompts"] = prompts
        admission["seconds_per_prompt_assumed"] = per_prompt
        return admission

    # ------------------------------------------------------------------
    # lens helpers
    # ------------------------------------------------------------------
    def register_matrices(self, label: str, lens: Any, condition: str) -> dict[str, Any]:
        jacobians = _jacobians(self.backend, lens)
        matrices = {}
        finite_layers = 0
        for layer in protocol.SOURCE_LAYERS:
            stats = self.math.matrix_stats(jacobians[layer])
            matrices[str(layer)] = stats
            finite_layers += int(bool(stats["finite"]))
            self.add_metric(
                "matrix_norm",
                stats["norm"],
                condition=condition,
                stratum=f"{label}::layer_{layer}",
            )
        self.state["finite_numerator"] += finite_layers
        self.state["finite_denominator"] += len(protocol.SOURCE_LAYERS)
        return {
            "matrices": matrices,
            "matrix_finite_layers": finite_layers,
            "matrix_layers": len(protocol.SOURCE_LAYERS),
        }

    def fit_unit(self, unit: dict[str, Any], condition: str) -> dict[str, Any]:
        checkpoint_path = self.work_dir / f"{unit['unit']}_checkpoint.pt"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.backend.start_memory()
        started = time.monotonic()
        lens = self.backend.fit(
            list(unit["texts"]),
            checkpoint_path=checkpoint_path,
            dim_batch=self.dim_batch,
            resume=bool(self.args.resume),
        )
        seconds = time.monotonic() - started
        memory = self.backend.finish_memory()
        metadata = _lens_metadata(self.backend, lens)
        if metadata["n_prompts"] != unit["prompt_count"]:
            raise base.CheckpointValidationError(
                f"{unit['unit']} fitted {metadata['n_prompts']} prompts, expected "
                f"{unit['prompt_count']}"
            )
        self.lenses[unit["unit"]] = lens
        matrix_detail = self.register_matrices(unit["unit"], lens, condition)
        checkpoint_bytes = (
            checkpoint_path.stat().st_size if checkpoint_path.is_file() else 0
        )
        detail = {
            "unit": unit["unit"],
            "condition": condition,
            "prompt_ids": list(unit["prompt_ids"]),
            "prompt_count": unit["prompt_count"],
            "prompt_order_sha256": unit["prompt_order_sha256"],
            "dim_batch": self.dim_batch,
            "fit_seconds": seconds,
            "fit_seconds_per_prompt": seconds / unit["prompt_count"],
            "memory": memory,
            "lens_metadata": metadata,
            "checkpoint_bytes": checkpoint_bytes,
            "checkpoint_sha256": (
                base.sha256_file(checkpoint_path) if checkpoint_path.is_file() else None
            ),
            **matrix_detail,
        }
        self.state.setdefault("fits", {})[unit["unit"]] = detail
        self.add_record(
            record_id=f"fit::{unit['unit']}",
            source_item_id=unit["prompt_order_sha256"],
            condition=condition,
            status="success",
            input_payload={
                "prompt_ids": list(unit["prompt_ids"]),
                "source_layers": list(protocol.SOURCE_LAYERS),
                "target_layer": protocol.TARGET_LAYER,
                "dim_batch": self.dim_batch,
                "max_seq_len": protocol.MAX_SEQ_LEN,
                "skip_first": protocol.SKIP_FIRST,
            },
            evaluation=detail,
        )
        self.add_metric(
            "fit_wall_clock_seconds",
            seconds,
            condition=condition,
            n=unit["prompt_count"],
            stratum=unit["unit"],
        )
        self.add_metric(
            "wall_clock_per_prompt",
            seconds / unit["prompt_count"],
            condition=condition,
            n=unit["prompt_count"],
            numerator=seconds,
            denominator=unit["prompt_count"],
            stratum=unit["unit"],
        )
        for metric in ("gpu_peak_allocated_bytes", "gpu_peak_reserved_bytes"):
            self.add_metric(
                metric,
                memory.get(metric),
                condition=condition,
                stratum=unit["unit"],
            )
        self.add_metric(
            "checkpoint_bytes",
            checkpoint_bytes,
            condition=condition,
            stratum=unit["unit"],
        )
        self.add_figure_row(
            figure_id="fig_fit_cost",
            series="lens_25b_shards",
            x_label="n_prompts",
            x_value=unit["prompt_count"],
            y_label="fit_wall_clock_seconds",
            y_value=seconds,
        )
        return detail

    def save_and_reload(self, label: str, condition: str) -> dict[str, Any]:
        lens = self.lenses[label]
        path = self.work_dir / f"{label}_lens.pt"
        reloaded, audit = self.backend.save_lens(lens, path)
        self.lenses[f"{label}__reloaded"] = reloaded
        max_abs = max(float(value) for value in audit["exact_max_abs"].values())
        detail = {
            "label": label,
            "path": path.as_posix(),
            "lens_bytes": int(audit["bytes"]),
            "lens_sha256": audit["sha256"],
            "lens_save_dtype": audit.get(
                "lens_save_dtype", protocol.LENS_SERIALIZATION_DTYPE
            ),
            "save_load_max_abs": max_abs,
        }
        self.state.setdefault("serialization", {})[label] = detail
        self.add_record(
            record_id=f"serialization::{label}",
            source_item_id=label,
            condition=condition,
            status="success",
            input_payload={"label": label, "dtype": protocol.LENS_SERIALIZATION_DTYPE},
            evaluation=detail,
        )
        self.add_metric(
            "save_load_max_abs",
            max_abs,
            condition=condition,
            stratum=label,
            threshold=protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
            passed=max_abs <= protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
        )
        self.add_metric(
            "lens_bytes", int(audit["bytes"]), condition=condition, stratum=label
        )
        return detail

    def compare_labels(
        self, left: str, right: str, *, pair: str, condition: str
    ) -> dict[str, Any]:
        comparison = protocol.compare_lens_matrices(
            self.math,
            _jacobians(self.backend, self.lenses[left]),
            _jacobians(self.backend, self.lenses[right]),
        )
        comparison["left"] = left
        comparison["right"] = right
        comparison["pair"] = pair
        comparison["reference"] = right
        comparison["interpretation"] = "technical_stability_only_no_semantic_claim"
        self.add_record(
            record_id=f"comparison::{pair}",
            source_item_id=f"{left}|{right}",
            condition=condition,
            status="success",
            input_payload={"left": left, "right": right, "pair": pair},
            evaluation=comparison,
        )
        return comparison

    # ------------------------------------------------------------------
    # stages
    # ------------------------------------------------------------------
    def stage_s0_environment(self) -> dict[str, Any]:
        if self.self_test:
            environment: dict[str, Any] = {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "installed": {},
                "cuda_available": False,
                "source_pin": base.validate_source_pin(
                    f"{base.OFFICIAL_REPOSITORY}@{base.OFFICIAL_COMMIT}"
                ),
                "backend": self.backend.name,
            }
        else:
            if sys.version_info[:2] != (3, 11):
                raise base.DependencyValidationError(
                    "the pinned J-lens image requires Python 3.11"
                )
            environment = self.backend.environment()
            environment["backend"] = self.backend.name
            base.validate_import_name("jlens")
        raw = Path(self.corpus["path"]).read_bytes()
        amendment = protocol.sat.CORPUS_REVISIONS[protocol.CORPUS_REVISION]
        corpus_payload = {
            "path": self.corpus["path"],
            "file_sha256": self.corpus["file_sha256"],
            "canonical_sha256": self.corpus["canonical_sha256"],
            "bytes": self.corpus["bytes"],
            "revision": self.corpus["revision"],
            "counts": self.corpus["counts"],
            "proxy_tokenizer": self.corpus["proxy_tokenizer"],
            "proxy_token_min": self.corpus["proxy_token_min"],
            "proxy_token_max": self.corpus["proxy_token_max"],
            "amendment": {
                "supersedes": amendment["supersedes"],
                "prefix_bytes": amendment["prefix_bytes"],
                "prefix_sha256": amendment["prefix_sha256"],
                "prefix_sha256_verified": base.sha256_bytes(
                    raw[: amendment["prefix_bytes"]]
                )
                == amendment["prefix_sha256"],
                "appended_ids": list(amendment["appended_ids"]),
            },
        }
        if not corpus_payload["amendment"]["prefix_sha256_verified"]:
            raise sat.CorpusValidationError(
                "the amended corpus does not preserve the superseded prefix bytes"
            )
        self.add_record(
            record_id="corpus::registration",
            source_item_id=self.corpus["canonical_sha256"],
            condition="corpus_registration",
            status="success",
            input_payload=corpus_payload,
            evaluation={
                **corpus_payload,
                "lens_25a_prompt_ids": list(self.plan["lens_25a"]["prompt_ids"]),
                "lens_25b_prompt_ids": list(self.plan["lens_25b"]["prompt_ids"]),
                "lens_25b_shard_prompt_ids": [
                    list(shard["prompt_ids"]) for shard in self.plan["lens_25b_shards"]
                ],
                "heldout_prompt_ids": list(self.plan["heldout"]["prompt_ids"]),
                "lens_25a_prompt_order_sha256": self.plan["lens_25a"][
                    "prompt_order_sha256"
                ],
                "lens_25a_matches_phase05b_order": self.plan[
                    "lens_25a_matches_phase05b_order"
                ],
                "fit_sets_disjoint": True,
            },
        )
        for record in self.corpus["records"]:
            self.add_metric(
                "corpus_proxy_token_count",
                record["proxy_token_count"],
                condition="corpus_registration",
                stratum=record["id"],
            )
        return {"environment": environment, "corpus": corpus_payload}

    def stage_s1_model(self) -> dict[str, Any]:
        if self.self_test:
            metadata = _self_test_backend_metadata(self.backend)
        else:
            metadata = self.backend.prepare()
        token_counts = {}
        for record in self.corpus["records"]:
            token_counts[record["id"]] = int(self.backend.token_count(record["text"]))
        self.state["token_counts"] = token_counts
        for prompt_id, count in sorted(token_counts.items()):
            self.add_metric(
                "corpus_token_count",
                count,
                condition="corpus_registration",
                stratum=prompt_id,
            )
        return {"model": metadata, "token_counts": token_counts}

    def stage_s2_load_existing_25a(self) -> dict[str, Any]:
        staging: dict[str, Any] = {"source": "preexisting_file"}
        if self.self_test and not self.existing_lens_path.is_file():
            # The synthetic backend must still exercise the load path, so it
            # writes a synthetic 25-prompt lens and then loads it back.
            self.existing_lens_path = self.work_dir / "self_test_lens_25a.json"
            synthetic = self.backend.fit(list(self.plan["lens_25a"]["texts"]))
            self.backend.save_lens(synthetic, self.existing_lens_path)
            staging = {"source": "self_test_synthetic"}
        elif self.existing_lens_blob and not self.existing_lens_path.is_file():
            if self.blob is None:
                raise protocol.ExistingLensValidationError(
                    "Blob staging requested without a configured transport"
                )
            staging = {
                "source": "blob_download",
                **self.blob.download_to(
                    self.existing_lens_blob, self.existing_lens_path
                ),
            }
        if not self.existing_lens_path.is_file():
            raise protocol.ExistingLensValidationError(
                f"the staged Phase 0.5B lens is missing at {self.existing_lens_path}"
            )
        # Integrity gate runs BEFORE deserialisation: a wrong, truncated or
        # substituted object never reaches the backend, and the only permitted
        # outcome of a mismatch is a failed stage, never a refit of 25A.
        integrity = protocol.verify_existing_lens_file(
            self.existing_lens_path,
            require_registered_digest=not (
                self.self_test or self.args.allow_unregistered_lens_digest
            ),
        )
        file_sha256 = integrity["file_sha256"]
        file_bytes = integrity["file_bytes"]
        lens = self.backend.load_lens(self.existing_lens_path)
        metadata = _lens_metadata(self.backend, lens)
        audit = protocol.validate_existing_lens(
            path=self.existing_lens_path,
            metadata=metadata,
            file_sha256=file_sha256,
            file_bytes=file_bytes,
            require_registered_digest=not (
                self.self_test or self.args.allow_unregistered_lens_digest
            ),
            expected_d_model=None if self.self_test else protocol.MODEL_WIDTH,
        )
        if not audit["digest_matches_registered"] and not self.self_test:
            self.deviations.append(
                {
                    "id": "existing-lens-digest-unregistered",
                    "description": (
                        "the staged Phase 0.5B lens SHA-256 "
                        f"{file_sha256} is not the registered "
                        f"{protocol.EXISTING_LENS_SHA256}"
                    ),
                    "justification": (
                        "explicitly allowed with --allow-unregistered-lens-digest"
                    ),
                    "effect_on_interpretation": "provenance of 25A is unverified",
                }
            )
        self.lenses[protocol.LENS_A] = lens
        matrix_detail = self.register_matrices(
            protocol.LENS_A, lens, "existing_lens_25a"
        )
        detail = {
            **audit,
            **matrix_detail,
            "staging": staging,
            "file_integrity": integrity,
            "provenance": dict(protocol.EXISTING_LENS_PROVENANCE),
            "prompt_ids": list(self.plan["lens_25a"]["prompt_ids"]),
            "prompt_order_sha256": self.plan["lens_25a"]["prompt_order_sha256"],
            "prompt_order_matches_phase05b": self.plan[
                "lens_25a_matches_phase05b_order"
            ],
            "refit_performed": False,
        }
        self.state["existing_lens"] = detail
        self.add_record(
            record_id="lens::25a_loaded",
            source_item_id=self.plan["lens_25a"]["prompt_order_sha256"],
            condition="existing_lens_25a",
            status="success",
            input_payload={
                "path": self.existing_lens_path.as_posix(),
                "blob": self.existing_lens_blob or None,
                "expected_sha256": self.existing_lens_sha256,
            },
            evaluation=detail,
        )
        self.add_metric(
            "lens_bytes",
            file_bytes,
            condition="existing_lens_25a",
            stratum=protocol.LENS_A,
        )
        return {"existing_lens": detail}

    def stage_s3_fit_25b(self) -> dict[str, Any]:
        admission = self.time_admission(
            "S3_fit_25b_sharded_merge", protocol.FIT_B_PROMPTS
        )
        if not admission["admitted"]:
            return {"_status": "skipped_time_guard", "time_admission": admission}
        shard_details = []
        for shard in self.plan["lens_25b_shards"]:
            index = shard["unit"].rsplit("_", 1)[-1]
            shard_details.append(self.fit_unit(shard, f"fit_25b_shard_{index}"))
        self.backend.start_memory()
        started = time.monotonic()
        merged = self.backend.merge(
            [self.lenses[shard["unit"]] for shard in self.plan["lens_25b_shards"]]
        )
        merge_seconds = time.monotonic() - started
        merge_memory = self.backend.finish_memory()
        metadata = _lens_metadata(self.backend, merged)
        if metadata["n_prompts"] != protocol.FIT_B_PROMPTS:
            raise base.NumericalValidationError(
                f"the merged 25B lens reports {metadata['n_prompts']} prompts, "
                f"expected {protocol.FIT_B_PROMPTS}"
            )
        self.lenses[protocol.LENS_B] = merged
        matrix_detail = self.register_matrices(
            protocol.LENS_B, merged, "fit_25b_merged"
        )
        total_fit_seconds = sum(item["fit_seconds"] for item in shard_details)
        peak_reserved = max(
            int(item["memory"].get("gpu_peak_reserved_bytes") or 0)
            for item in shard_details
        )
        peak_allocated = max(
            int(item["memory"].get("gpu_peak_allocated_bytes") or 0)
            for item in shard_details
        )
        detail = {
            "unit": protocol.LENS_B,
            "condition": "fit_25b_merged",
            "prompt_ids": list(self.plan["lens_25b"]["prompt_ids"]),
            "prompt_count": protocol.FIT_B_PROMPTS,
            "prompt_order_sha256": self.plan["lens_25b"]["prompt_order_sha256"],
            "shards": [item["unit"] for item in shard_details],
            "shard_sizes": list(protocol.FIT_B_SHARDS),
            "dim_batch": self.dim_batch,
            "fit_seconds": total_fit_seconds,
            "fit_seconds_per_prompt": total_fit_seconds / protocol.FIT_B_PROMPTS,
            "merge_seconds": merge_seconds,
            "memory": merge_memory,
            "shard_peak_reserved_bytes": peak_reserved,
            "shard_peak_allocated_bytes": peak_allocated,
            "lens_metadata": metadata,
            "checkpoint_bytes": sum(item["checkpoint_bytes"] for item in shard_details),
            "disjoint_from_lens_25a": True,
            **matrix_detail,
        }
        self.state.setdefault("fits", {})[protocol.LENS_B] = detail
        self.values["wall_clock_per_prompt"] = detail["fit_seconds_per_prompt"]
        self.values["peak_gpu_memory"] = peak_reserved
        self.add_record(
            record_id="fit::lens_25b",
            source_item_id=self.plan["lens_25b"]["prompt_order_sha256"],
            condition="fit_25b_merged",
            status="success",
            input_payload={
                "shards": [
                    list(shard["prompt_ids"]) for shard in self.plan["lens_25b_shards"]
                ],
                "source_layers": list(protocol.SOURCE_LAYERS),
                "target_layer": protocol.TARGET_LAYER,
                "dim_batch": self.dim_batch,
            },
            evaluation=detail,
        )
        for metric, value, threshold in (
            ("fit_wall_clock_seconds", total_fit_seconds, ""),
            ("wall_clock_per_prompt", detail["fit_seconds_per_prompt"], ""),
            ("merge_seconds", merge_seconds, ""),
            ("checkpoint_bytes", detail["checkpoint_bytes"], ""),
            ("peak_gpu_memory", peak_reserved, ""),
            ("gpu_peak_reserved_bytes", peak_reserved, ""),
            ("gpu_peak_allocated_bytes", peak_allocated, ""),
        ):
            self.add_metric(
                metric,
                value,
                condition="fit_25b_merged",
                n=protocol.FIT_B_PROMPTS,
                stratum=protocol.LENS_B,
                threshold=threshold,
            )
        for label, key, unit_name in (
            ("fit_wall_clock", "fit_seconds", "seconds"),
            ("wall_clock_per_prompt", "fit_seconds_per_prompt", "seconds"),
            ("checkpoint_size", "checkpoint_bytes", "bytes"),
        ):
            self.add_paper_row(
                row_label=label,
                condition="fit_25b_merged",
                n_prompts=protocol.FIT_B_PROMPTS,
                metric=key,
                value=detail[key],
                unit=unit_name,
            )
        self.add_paper_row(
            row_label="peak_gpu_memory",
            condition="fit_25b_merged",
            n_prompts=protocol.FIT_B_PROMPTS,
            metric="gpu_peak_reserved_bytes",
            value=peak_reserved,
            unit="bytes",
        )
        self.add_figure_row(
            figure_id="fig_fit_cost",
            series="lens_25b_merged",
            x_label="n_prompts",
            x_value=protocol.FIT_B_PROMPTS,
            y_label="fit_wall_clock_seconds",
            y_value=total_fit_seconds,
        )
        return {
            "time_admission": admission,
            "shards": shard_details,
            "merged": detail,
        }

    def stage_s4_merge_50(self) -> dict[str, Any]:
        started = time.monotonic()
        merged = self.backend.merge(
            [self.lenses[protocol.LENS_A], self.lenses[protocol.LENS_B]]
        )
        merge_seconds = time.monotonic() - started
        metadata = _lens_metadata(self.backend, merged)
        if metadata["n_prompts"] != protocol.MERGED_PROMPTS:
            raise base.NumericalValidationError(
                f"the merged 50-prompt lens reports {metadata['n_prompts']} "
                f"prompts, expected {protocol.MERGED_PROMPTS}"
            )
        self.lenses[protocol.LENS_M] = merged
        matrix_detail = self.register_matrices(protocol.LENS_M, merged, "merge_50")
        merged_jacobians = _jacobians(self.backend, merged)
        recombined = {
            layer: self.math.matrix_weighted_mean(
                [
                    (
                        _jacobians(self.backend, self.lenses[protocol.LENS_A])[layer],
                        protocol.MERGE_WEIGHTS[0],
                    ),
                    (
                        _jacobians(self.backend, self.lenses[protocol.LENS_B])[layer],
                        protocol.MERGE_WEIGHTS[1],
                    ),
                ]
            )
            for layer in protocol.SOURCE_LAYERS
        }
        cross_check = protocol.compare_lens_matrices(
            self.math, recombined, merged_jacobians
        )
        cross_check["left"] = "weighted_recombination_25_25"
        cross_check["right"] = protocol.LENS_M
        cross_check["weights"] = list(protocol.MERGE_WEIGHTS)
        cross_check["note"] = (
            "arithmetic cross-check of the official merge weighting on already "
            "fitted matrices; not a fit and not a registered criterion"
        )
        self.add_record(
            record_id="comparison::merge_weighting_cross_check",
            source_item_id=protocol.LENS_M,
            condition="merge_weighting_cross_check",
            status="success",
            input_payload={"weights": list(protocol.MERGE_WEIGHTS)},
            evaluation=cross_check,
        )
        self.add_metric(
            "merge_weighting_cross_check_max_abs",
            cross_check["max_abs"],
            condition="merge_weighting_cross_check",
            n=protocol.MERGED_PROMPTS,
        )
        if cross_check["max_abs"] > protocol.MERGE_WEIGHTING_MAX_ABS_TOLERANCE:
            self.deviations.append(
                {
                    "id": "merge-weighting-differs",
                    "description": (
                        "JacobianLens.merge does not equal the n-prompt-weighted "
                        "recombination of the two 25-prompt lenses "
                        f"(max_abs={cross_check['max_abs']:.6g})."
                    ),
                    "justification": (
                        "Recorded as an observation. Phase 0.5B already "
                        "demonstrated merge/direct-subset equivalence "
                        "(max_abs 2.384e-07 against a 1e-05 limit); this run "
                        "does not repeat that control."
                    ),
                    "effect_on_interpretation": "none",
                }
            )
        detail = {
            "unit": protocol.LENS_M,
            "condition": "merge_50",
            "inputs": [protocol.LENS_A, protocol.LENS_B],
            "weights": list(protocol.MERGE_WEIGHTS),
            "prompt_count": protocol.MERGED_PROMPTS,
            "merge_seconds": merge_seconds,
            "lens_metadata": metadata,
            "weighting_cross_check_max_abs": cross_check["max_abs"],
            "direct_50_fit_performed": False,
            "reused_phase05b_merge_control": dict(protocol.EXISTING_MERGE_CONTROL),
            **matrix_detail,
        }
        self.state.setdefault("fits", {})[protocol.LENS_M] = detail
        self.add_record(
            record_id="merge::lens_50m",
            source_item_id=f"{protocol.LENS_A}|{protocol.LENS_B}",
            condition="merge_50",
            status="success",
            input_payload={
                "lenses": [protocol.LENS_A, protocol.LENS_B],
                "weights": list(protocol.MERGE_WEIGHTS),
            },
            evaluation=detail,
        )
        self.add_metric(
            "merge_seconds",
            merge_seconds,
            condition="merge_50",
            n=protocol.MERGED_PROMPTS,
            stratum=protocol.LENS_M,
        )
        return {"merged": detail, "weighting_cross_check": cross_check}

    def stage_s5_serialization(self) -> dict[str, Any]:
        details = {}
        for label in (protocol.LENS_A, protocol.LENS_B, protocol.LENS_M):
            details[label] = self.save_and_reload(label, "serialization")
        self.state["serialization"] = details
        worst = max(item["save_load_max_abs"] for item in details.values())
        self.values["save_load_max_abs"] = worst
        self.add_metric(
            "save_load_max_abs",
            worst,
            condition="serialization",
            n=len(details),
            threshold=protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
            passed=worst <= protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
        )
        self.add_paper_row(
            row_label="save_load_max_abs",
            condition="serialization",
            n_prompts=protocol.MERGED_PROMPTS,
            metric="save_load_max_abs",
            value=worst,
            unit="abs",
        )
        for label, item in sorted(details.items()):
            self.add_paper_row(
                row_label="lens_size",
                condition="serialization",
                n_prompts=(
                    protocol.MERGED_PROMPTS
                    if label == protocol.LENS_M
                    else protocol.FIT_A_PROMPTS
                ),
                metric="lens_bytes",
                value=item["lens_bytes"],
                unit="bytes",
            )
        return {"serialization": details, "save_load_max_abs": worst}

    def stage_s6_heldout_apply(self) -> dict[str, Any]:
        heldout = self.plan["heldout"]
        pair_prompt_values: dict[str, dict[str, list[float]]] = {
            name: {
                "heldout_apply_logit_cosine": [],
                "heldout_topk_overlap": [],
                "heldout_topk_overlap_secondary": [],
                "heldout_rank_correlation": [],
            }
            for name, _left, _right in protocol.APPLY_PAIRS
        }
        consistent = True
        per_prompt: list[dict[str, Any]] = []
        for prompt_id, text in zip(
            heldout["prompt_ids"], heldout["texts"], strict=True
        ):
            logits: dict[str, dict[int, list[float]]] = {}
            reloaded_logits: dict[str, dict[int, list[float]]] = {}
            sequence_length = None
            model_dimension = None
            for label in protocol.LENS_LABELS:
                lens_logits, model_logits, seq_len = self.backend.apply(
                    self.lenses[label], text
                )
                logits[label] = lens_logits
                sequence_length = seq_len
                model_dimension = len(model_logits)
                reloaded = self.lenses.get(f"{label}__reloaded")
                if reloaded is None:
                    raise base.NumericalValidationError(
                        f"the reloaded lens for {label} is missing"
                    )
                reloaded_logits[label], _, _ = self.backend.apply(reloaded, text)
            consistency: dict[str, bool] = {}
            for label in protocol.LENS_LABELS:
                label_consistent = all(
                    self.math.allclose(
                        logits[label][layer], reloaded_logits[label][layer]
                    )
                    for layer in protocol.SOURCE_LAYERS
                )
                consistency[label] = bool(label_consistent)
                consistent = consistent and label_consistent
            pairs_payload: dict[str, Any] = {}
            for name, left, right in protocol.APPLY_PAIRS:
                layer_payload: dict[str, Any] = {}
                cosines: list[float] = []
                overlaps: list[float] = []
                overlaps_secondary: list[float] = []
                correlations: list[float] = []
                for layer in protocol.SOURCE_LAYERS:
                    comparison = protocol.compare_logit_vectors(
                        logits[left][layer], logits[right][layer]
                    )
                    layer_payload[str(layer)] = comparison
                    cosines.append(comparison["cosine"])
                    overlaps.append(comparison["top_k"]["fraction"])
                    overlaps_secondary.append(
                        comparison["top_k_secondary"]["fraction"]
                    )
                    correlations.append(comparison["rank_correlation"])
                values = {
                    "heldout_apply_logit_cosine": protocol.mean(cosines),
                    "heldout_topk_overlap": protocol.mean(overlaps),
                    "heldout_topk_overlap_secondary": protocol.mean(
                        overlaps_secondary
                    ),
                    "heldout_rank_correlation": protocol.mean(correlations),
                }
                for metric, value in values.items():
                    pair_prompt_values[name][metric].append(value)
                pairs_payload[name] = {"layers": layer_payload, **values}
                for metric in (
                    "heldout_apply_logit_cosine",
                    "heldout_topk_overlap",
                    "heldout_rank_correlation",
                ):
                    self.add_metric(
                        metric,
                        values[metric],
                        condition="heldout_apply",
                        stratum=f"pair::{name}::{prompt_id}",
                        n=protocol.TOP_K,
                    )
            evaluation = {
                "prompt_id": prompt_id,
                "sequence_length": sequence_length,
                "model_logit_dimension": model_dimension,
                "pairs": pairs_payload,
                "save_load_apply_consistent": consistency,
                "interpretation": "technical_stability_only_no_semantic_claim",
            }
            per_prompt.append(evaluation)
            self.add_record(
                record_id=f"apply::{prompt_id}",
                source_item_id=prompt_id,
                condition="heldout_apply",
                status="success",
                input_payload={
                    "prompt_id": prompt_id,
                    "positions": [-1],
                    "layers": list(protocol.SOURCE_LAYERS),
                    "use_jacobian": True,
                    "lenses": list(protocol.LENS_LABELS),
                },
                evaluation=evaluation,
            )
            for name, _left, _right in protocol.APPLY_PAIRS:
                self.add_figure_row(
                    figure_id="fig_heldout_apply_stability",
                    series=name,
                    x_label="heldout_prompt_id",
                    x_value=prompt_id,
                    y_label="heldout_topk_overlap",
                    y_value=pairs_payload[name]["heldout_topk_overlap"],
                )
        pair_means = {
            name: {
                metric: protocol.mean(series)
                for metric, series in metrics.items()
            }
            for name, metrics in pair_prompt_values.items()
        }
        for name, metrics in sorted(pair_means.items()):
            for metric, value in sorted(metrics.items()):
                self.add_metric(
                    metric,
                    value,
                    condition="apply_stability",
                    stratum=f"pair::{name}",
                    n=protocol.HELDOUT_PROMPTS,
                )
        lens_means: dict[str, dict[str, Any]] = {}
        for label, pair_names in protocol.PAIRS_BY_LENS.items():
            lens_means[label] = {
                metric: protocol.mean(
                    [pair_means[name][metric] for name in pair_names]
                )
                for metric in (
                    "heldout_apply_logit_cosine",
                    "heldout_topk_overlap",
                    "heldout_topk_overlap_secondary",
                    "heldout_rank_correlation",
                )
            }
            for metric, value in sorted(lens_means[label].items()):
                self.add_metric(
                    metric,
                    value,
                    condition="apply_stability",
                    stratum=f"lens::{protocol.LENS_DISPLAY[label]}",
                    n=protocol.HELDOUT_PROMPTS,
                )
        overall = {
            metric: protocol.mean(
                [pair_means[name][metric] for name, _l, _r in protocol.APPLY_PAIRS]
            )
            for metric in (
                "heldout_apply_logit_cosine",
                "heldout_topk_overlap",
                "heldout_topk_overlap_secondary",
                "heldout_rank_correlation",
            )
        }
        for metric, value in sorted(overall.items()):
            self.values[metric] = value
            self.add_metric(
                metric,
                value,
                condition="apply_stability",
                stratum="all",
                n=len(protocol.APPLY_PAIRS),
            )
            self.add_paper_row(
                row_label=metric,
                condition="apply_stability",
                n_prompts=protocol.HELDOUT_PROMPTS,
                metric=f"{metric}_mean",
                value=value,
                unit="ratio",
            )
        self.values["apply_save_load_consistency"] = 1.0 if consistent else 0.0
        self.add_metric(
            "apply_save_load_consistency",
            1.0 if consistent else 0.0,
            condition="apply_stability",
            n=len(per_prompt) * len(protocol.LENS_LABELS),
            threshold=protocol.APPLY_CONSISTENCY_MIN,
            passed=consistent,
        )
        self.state["pair_means"] = pair_means
        self.state["lens_means"] = lens_means
        self.state["apply_overall"] = overall
        self.result_notes.append(
            "Top-k overlap and rank correlation are technical stability "
            "statistics for fitted linear operators. They are not semantic, "
            "behavioral, or interpretive evidence, and they do not indicate "
            "that any lens is scientifically usable."
        )
        return {
            "heldout_prompts": len(per_prompt),
            "pair_means": pair_means,
            "lens_means": lens_means,
            "overall": overall,
            "apply_save_load_consistency": consistent,
        }

    def stage_s7_replicate_variability(self) -> dict[str, Any]:
        comparisons = {}
        for pair, left, right, frobenius_metric, cosine_metric in (
            (
                protocol.PAIR_AB,
                protocol.LENS_A,
                protocol.LENS_B,
                "25A_vs_25B_relative_frobenius",
                "25A_vs_25B_cosine",
            ),
            (
                protocol.PAIR_AM,
                protocol.LENS_A,
                protocol.LENS_M,
                "25A_vs_50M_relative_frobenius",
                "25A_vs_50M_cosine",
            ),
            (
                protocol.PAIR_BM,
                protocol.LENS_B,
                protocol.LENS_M,
                "25B_vs_50M_relative_frobenius",
                "25B_vs_50M_cosine",
            ),
        ):
            comparison = self.compare_labels(
                left, right, pair=pair, condition="replicate_variability"
            )
            comparisons[pair] = comparison
            self.values[frobenius_metric] = comparison["max_relative_frobenius"]
            self.values[cosine_metric] = comparison["min_cosine"]
            threshold = protocol.CRITERIA.get(frobenius_metric, {}).get("threshold", "")
            self.add_metric(
                frobenius_metric,
                comparison["max_relative_frobenius"],
                condition="replicate_variability",
                stratum="all",
                n=protocol.FIT_A_PROMPTS,
                threshold=threshold,
                passed=(
                    comparison["max_relative_frobenius"] <= float(threshold)
                    if threshold != ""
                    else ""
                ),
            )
            cosine_threshold = protocol.CRITERIA.get(cosine_metric, {}).get(
                "threshold", ""
            )
            self.add_metric(
                cosine_metric,
                comparison["min_cosine"],
                condition="replicate_variability",
                stratum="all",
                n=protocol.FIT_A_PROMPTS,
                threshold=cosine_threshold,
                passed=(
                    comparison["min_cosine"] >= float(cosine_threshold)
                    if cosine_threshold != ""
                    else ""
                ),
            )
            for layer, layer_values in sorted(comparison["layers"].items()):
                self.add_metric(
                    frobenius_metric,
                    layer_values["relative_frobenius"],
                    condition="replicate_variability",
                    stratum=f"layer_{layer}",
                )
                self.add_metric(
                    cosine_metric,
                    layer_values["cosine"],
                    condition="replicate_variability",
                    stratum=f"layer_{layer}",
                )
                self.add_figure_row(
                    figure_id="fig_replicate_variability",
                    series=f"{pair}::layer_{layer}",
                    x_label="lens_pair",
                    x_value=pair,
                    y_label="relative_frobenius",
                    y_value=layer_values["relative_frobenius"],
                )
                self.add_figure_row(
                    figure_id="fig_replicate_cosine",
                    series=f"{pair}::layer_{layer}",
                    x_label="lens_pair",
                    x_value=pair,
                    y_label="cosine",
                    y_value=layer_values["cosine"],
                )
            self.add_paper_row(
                row_label=pair,
                condition="replicate_variability",
                n_prompts=protocol.FIT_A_PROMPTS,
                metric="relative_frobenius",
                value=comparison["max_relative_frobenius"],
                unit="ratio",
            )
            self.add_paper_row(
                row_label=pair,
                condition="replicate_variability",
                n_prompts=protocol.FIT_A_PROMPTS,
                metric="cosine",
                value=comparison["min_cosine"],
                unit="cosine",
            )
        numerator = self.state.get("finite_numerator", 0)
        denominator = self.state.get("finite_denominator", 0)
        rate = protocol.finite_rate(numerator, denominator)
        if rate is not None:
            self.values["matrix_finite_rate"] = rate
            self.add_metric(
                "matrix_finite_rate",
                rate,
                condition="replicate_variability",
                n=denominator,
                numerator=numerator,
                denominator=denominator,
                threshold=protocol.FINITE_RATE_MIN,
                passed=rate >= protocol.FINITE_RATE_MIN,
            )
        improvement = protocol.merged_apply_improvement(
            self.state.get("pair_means", {})
        )
        self.merged_improvement = improvement
        for metric, value in sorted(improvement["margins_measured"].items()):
            self.add_metric(
                f"merged_apply_improvement_{'topk' if metric.endswith('overlap') else 'rank_correlation'}",
                value,
                condition="replicate_variability",
                stratum=metric,
                threshold=improvement["margins"][metric],
                passed=(
                    ""
                    if value is None
                    else value >= improvement["margins"][metric]
                ),
            )
        self.add_record(
            record_id="replicate::merged_apply_improvement",
            source_item_id=protocol.LENS_M,
            condition="replicate_variability",
            status="success",
            input_payload={"pair_means": self.state.get("pair_means", {})},
            evaluation=improvement,
        )
        return {"comparisons": comparisons, "merged_apply_improvement": improvement}

    # ------------------------------------------------------------------
    # export
    # ------------------------------------------------------------------
    def build_decision(self) -> dict[str, Any]:
        return protocol.evaluate_decision(
            self.values,
            stages=self.stages,
            self_test=self.self_test,
            blocked_reason=self.blocked_reason,
            deviations=self.deviations,
            merged_improvement=self.merged_improvement,
        )

    def export(self, decision: dict[str, Any]) -> dict[str, Any]:
        end_time_utc = feasibility.utc_now()
        snapshot = protocol.build_protocol_snapshot(
            sample_size=protocol.default_sample_size()
        )
        protocol_hash = base.sha256_bytes(base.canonical_json_bytes(snapshot))
        inputs = {
            "corpus_path": self.corpus["path"],
            "corpus_file_sha256": self.corpus["file_sha256"],
            "corpus_canonical_sha256": self.corpus["canonical_sha256"],
            "corpus_revision": self.corpus["revision"],
            "corpus_counts": self.corpus["counts"],
            "lens_25a_prompt_ids": list(self.plan["lens_25a"]["prompt_ids"]),
            "lens_25b_prompt_ids": list(self.plan["lens_25b"]["prompt_ids"]),
            "lens_25b_shard_prompt_ids": [
                list(shard["prompt_ids"]) for shard in self.plan["lens_25b_shards"]
            ],
            "heldout_prompt_ids": list(self.plan["heldout"]["prompt_ids"]),
            "existing_lens_path": self.existing_lens_path.as_posix(),
            "existing_lens_blob": self.existing_lens_blob or None,
            "existing_lens_container": protocol.EXISTING_BLOB_CONTAINER,
            "existing_lens_storage_account": protocol.EXISTING_STORAGE_ACCOUNT,
            "existing_lens_expected_sha256": self.existing_lens_sha256,
            "existing_lens_expected_bytes": protocol.EXISTING_LENS_BYTES,
            "existing_lens_verified_sha256": (
                self.state.get("existing_lens", {})
                .get("file_integrity", {})
                .get("file_sha256")
            ),
            "existing_lens_verified_bytes": (
                self.state.get("existing_lens", {})
                .get("file_integrity", {})
                .get("file_bytes")
            ),
            "existing_lens_source_run_id": protocol.EXISTING_RUN_ID,
            "existing_lens_refitted": False,
            "produced_lens_digests": {
                label: {
                    "sha256": item.get("lens_sha256"),
                    "bytes": item.get("lens_bytes"),
                }
                for label, item in sorted(
                    self.state.get("serialization", {}).items()
                )
            },
            "direct_50_fit_performed": False,
            "dim_batch": self.dim_batch,
            "max_seq_len": protocol.MAX_SEQ_LEN,
            "skip_first": protocol.SKIP_FIRST,
            "official_source": f"{base.OFFICIAL_REPOSITORY}@{base.OFFICIAL_COMMIT}",
            "backend": self.backend.name,
            "mode": "self_test" if self.self_test else "container",
            "blob_prefix": self.blob_prefix,
            "attempt_id": self.attempt_id,
            "resume_requested": bool(self.args.resume),
        }
        hardware = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "gpu": self.stages.get("S0_environment", {})
            .get("details", {})
            .get("environment", {})
            .get("gpu_name"),
            "gpu_total_bytes": self.stages.get("S0_environment", {})
            .get("details", {})
            .get("environment", {})
            .get("gpu_total_bytes"),
            "expected_workload_profile": "gpu-t4",
        }
        stage_manifest = protocol.build_stage_manifest(
            run_id=self.run_id,
            status=decision["status"],
            start_time_utc=self.start_time_utc,
            end_time_utc=end_time_utc,
            code_commit=code_commit(),
            image_digest=os.getenv("JSPACE_IMAGE_DIGEST", "").strip() or None,
            hardware=hardware,
            inputs=inputs,
            protocol_hash=protocol_hash,
            subagents=[
                {
                    "name": "agent-a-track-a1",
                    "role": "phase 0.5C disjoint-replication implementation",
                    "model_access": "none",
                }
            ],
        )
        stage_manifest["stages"] = {
            name: {
                "status": self.stages.get(name, {}).get("status", "not_run"),
                "duration_seconds": self.stages.get(name, {}).get("duration_seconds"),
                "started_at_utc": self.stages.get(name, {}).get("started_at_utc"),
                "finished_at_utc": self.stages.get(name, {}).get("finished_at_utc"),
            }
            for name in protocol.STAGES
        }
        stage_manifest["stage_details"] = {
            name: self.stages.get(name, {}).get("details", {})
            for name in protocol.STAGES
        }
        stage_manifest["errors"] = list(self.errors)
        deviations_document = {
            "deviations": list(self.deviations),
            "unregistered_changes": list(self.unregistered_changes),
            "effect_on_interpretation": "none" if not self.deviations else "recorded",
        }
        summary = protocol.render_summary_markdown(
            {
                "run_id": self.run_id,
                "mode": "self_test" if self.self_test else "container",
                "dim_batch": self.dim_batch,
                "corpus_path": self.corpus["path"],
                "corpus_file_sha256": self.corpus["file_sha256"],
                "corpus_canonical_sha256": self.corpus["canonical_sha256"],
                "code_commit": stage_manifest["code_commit"],
                "image_digest": stage_manifest["image_digest"],
                "extra_provenance": [
                    f"Corpus revision: `{self.corpus['revision']}` "
                    f"({self.corpus['counts']})",
                    f"Existing 25A lens: `{self.existing_lens_path.as_posix()}` "
                    f"from run `{protocol.EXISTING_RUN_ID}`; re-fitted: no",
                    "Direct 50-prompt fit: not performed; the Phase 0.5B "
                    "direct-subset merge control is reused",
                ],
                "stages": self.stages,
                "decision": decision,
                "deviations": deviations_document,
                "errors": self.errors,
                "result_notes": self.result_notes,
            }
        )
        manifest = protocol.write_artifact_pack(
            self.pack_dir,
            run_id=self.run_id,
            stage_manifest=stage_manifest,
            protocol_snapshot=snapshot,
            records=self.records,
            metrics=self.metrics,
            decision=decision,
            summary_markdown=summary,
            paper_rows=self.paper_rows,
            figure_rows=self.figure_rows,
            deviations=deviations_document,
            generated_at_utc=end_time_utc,
        )
        protocol.validate_artifact_pack(self.pack_dir)
        return manifest

    def upload(self) -> dict[str, Any]:
        if self.blob is None or not self.blob.configured:
            return {"status": "not_configured", "uploaded": 0}
        results: dict[str, Any] = {}
        try:
            results["lens_binaries"] = self.blob.upload_snapshot(
                self.work_dir, "lens-binaries", 1
            )
            results["artifact_pack"] = self.blob.upload_snapshot(
                self.pack_dir, "artifact-pack", 2
            )
        except Exception as error:  # noqa: BLE001 - transport must never lose the pack
            results["status"] = "failed"
            results["error"] = feasibility.safe_error(error)
            return results
        results["status"] = "uploaded"
        results["uploaded"] = sum(
            int(item.get("uploaded", 0))
            for item in results.values()
            if isinstance(item, dict)
        )
        return results

    def run(self) -> int:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        sequence = (
            ("S0_environment", self.stage_s0_environment),
            ("S1_model", self.stage_s1_model),
            ("S2_load_existing_25a", self.stage_s2_load_existing_25a),
            ("S3_fit_25b_sharded_merge", self.stage_s3_fit_25b),
            ("S4_merge_50", self.stage_s4_merge_50),
            ("S5_serialization", self.stage_s5_serialization),
            ("S6_heldout_apply", self.stage_s6_heldout_apply),
            ("S7_replicate_variability", self.stage_s7_replicate_variability),
        )
        try:
            for name, function in sequence:
                self.execute(name, function)
        except base.ApplicationTimeoutError as error:
            self.blocked_reason = feasibility.safe_error(error)
        except (KeyboardInterrupt, SystemExit) as error:  # pragma: no cover
            self.blocked_reason = f"interrupted: {type(error).__name__}"
        if self.errors and self.blocked_reason is None:
            failed = sorted({item["stage"] for item in self.errors})
            if {"S0_environment", "S1_model", "S2_load_existing_25a"} & set(failed):
                self.blocked_reason = f"stage failure before any fit: {failed}"
        decision = self.build_decision()
        manifest = self.export(decision)
        upload = self.upload()
        self.state["upload"] = upload
        print(
            protocol.canonical_json_bytes(
                {
                    "phase": protocol.PHASE,
                    "track": protocol.TRACK,
                    "run_id": self.run_id,
                    "status": decision["status"],
                    "decision": decision["decision"],
                    "pack_dir": self.pack_dir.as_posix(),
                    "artifacts": len(manifest["artifacts"]) + 1,
                    "upload": upload,
                }
            ).decode("utf-8"),
            end="",
        )
        if decision["status"] in {"PASS", "COMPLETE"}:
            return 0
        if decision["status"] == "INCONCLUSIVE":
            return 0 if self.self_test else 3
        return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=os.getenv(
            "RESULTS_DIR",
            str(PROJECT_ROOT / "results" / "runs" / "phase05c-jlens-disjoint"),
        ),
    )
    parser.add_argument(
        "--corpus",
        default=str(PROJECT_ROOT / "data" / "jlens_saturation_prompts.jsonl"),
    )
    parser.add_argument(
        "--existing-lens-path",
        default="",
        help=(
            "Path to the already-fitted Phase 0.5B 25-prompt lens. It is loaded "
            "and never re-fitted."
        ),
    )
    parser.add_argument(
        "--existing-lens-blob",
        default="",
        help=(
            "Optional Blob name of the Phase 0.5B lens; downloaded with the "
            "managed identity when --existing-lens-path does not exist yet."
        ),
    )
    parser.add_argument(
        "--existing-lens-sha256",
        default="",
        help="Expected SHA-256 of the staged lens; defaults to the registered value.",
    )
    parser.add_argument(
        "--allow-unregistered-lens-digest",
        action="store_true",
        help="Record a deviation instead of failing on an unregistered lens digest.",
    )
    parser.add_argument(
        "--dim-batch",
        type=int,
        default=int(os.getenv("JSPACE_JLENS_DIM_BATCH", protocol.DEFAULT_DIM_BATCH)),
        choices=list(protocol.ALLOWED_DIM_BATCH),
    )
    parser.add_argument("--run-id", default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run the whole stage sequence on the synthetic torch-free backend.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias for --self-test; never touches the GPU or the model.",
    )
    args = parser.parse_args(argv)
    if args.dim_batch not in protocol.ALLOWED_DIM_BATCH:  # pragma: no cover
        parser.error(f"--dim-batch must be one of {list(protocol.ALLOWED_DIM_BATCH)}")
    digest = str(args.existing_lens_sha256).strip()
    if digest and (len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)):
        parser.error("--existing-lens-sha256 must be a lowercase 64-hex digest")
    return args


def _watchdog_signal(signum: int, _frame: Any) -> None:
    raise base.ApplicationTimeoutError(f"received watchdog signal {signum}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not (args.self_test or args.dry_run):
        signal.signal(signal.SIGTERM, _watchdog_signal)
        if hasattr(signal, "SIGALRM"):
            signal.signal(signal.SIGALRM, _watchdog_signal)
            signal.alarm(base.APPLICATION_WATCHDOG_SECONDS)
    try:
        return DisjointRunner(args).run()
    finally:
        if not (args.self_test or args.dry_run) and hasattr(signal, "SIGALRM"):
            signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
