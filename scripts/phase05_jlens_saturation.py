#!/usr/bin/env python3
"""Phase 0.5B J-lens saturation runner: 10-prompt fit, sharded 25-prompt fit.

Engineering feasibility only. The stages measure fit cost, numerical
stability, shard/merge equivalence, serialization exactness, and held-out
apply stability. Nothing here is behavioral, semantic, or interpretive
evidence; top-k overlap is a technical stability statistic only.
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
import phase05_jlens_saturation as protocol  # noqa: E402

DIM_BATCH_2_JUSTIFICATION = (
    "Phase 0.5A F2 measured a green memory classification at dim_batch=1 "
    "(peak reserved 3808428032 of 16704405504 bytes, ratio 0.2280) and F3 "
    "completed at dim_batch=2, so dim_batch=2 has recorded headroom."
)

REGISTERED_SECONDS_PER_PROMPT = 26.84
REGISTERED_FIXED_OVERHEAD_SECONDS = 41.0
PESSIMISTIC_SECONDS_PER_PROMPT = 53.68


class SaturationBlobTransport(feasibility.BlobTransport):
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
            raise base.DependencyValidationError("the saturation run requires a GPU")
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

    def save_lens(self, lens: Any, path: Path) -> tuple[Any, dict[str, Any]]:
        return feasibility.save_lossless_jacobian_lens(
            self.torch, self.jlens, lens, Path(path)
        )

    def apply(self, lens: Any, text: str) -> tuple[dict[int, list[float]], list[float], int]:
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

    def checkpoint_state(self, path: Path) -> dict[str, Any]:
        state = self.torch.load(path, map_location="cpu", weights_only=True)
        return {
            "n_done": state.get("n_done"),
            "next_idx": state.get("next_idx"),
            "source_layers": state.get("source_layers"),
            "target_layer": state.get("target_layer"),
        }

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


class SaturationRunner:
    """Executes S0-S6 and always exports the standard artifact pack."""

    def __init__(self, args: argparse.Namespace, backend: Any | None = None) -> None:
        self.args = args
        self.output_dir = Path(args.output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.started_monotonic = time.monotonic()
        self.start_time_utc = feasibility.utc_now()
        self.run_id = (
            str(args.run_id).strip()
            or os.getenv("JSPACE_PHASE05_RUN_ID", "").strip()
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
            raise protocol.SaturationValidationError(
                f"dim_batch must be one of {list(protocol.ALLOWED_DIM_BATCH)}"
            )
        self.corpus = protocol.load_saturation_corpus(args.corpus)
        self.plan = protocol.build_fit_plan(self.corpus)
        self.backend = backend or (
            protocol.SelfTestBackend() if self.self_test else RealBackend(output_dir=self.work_dir)
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
        self.lenses: dict[str, Any] = {}
        self.state: dict[str, Any] = {}
        self.blob: Any = None
        if not self.self_test:
            self.blob = SaturationBlobTransport(self.blob_prefix, self.attempt_id)
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
    # fitting helpers
    # ------------------------------------------------------------------
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
        jacobians = _jacobians(self.backend, lens)
        matrices = {}
        finite_total = 0
        for layer in protocol.SOURCE_LAYERS:
            stats = self.math.matrix_stats(jacobians[layer])
            matrices[str(layer)] = stats
            finite_total += int(bool(stats["finite"]))
        lens_path = self.work_dir / f"{unit['unit']}_lens.pt"
        reloaded, audit = self.backend.save_lens(lens, lens_path)
        save_load_max_abs = max(
            float(value) for value in audit["exact_max_abs"].values()
        )
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
            "matrices": matrices,
            "matrix_finite_layers": finite_total,
            "matrix_layers": len(protocol.SOURCE_LAYERS),
            "checkpoint_bytes": checkpoint_bytes,
            "checkpoint_sha256": (
                base.sha256_file(checkpoint_path) if checkpoint_path.is_file() else None
            ),
            "lens_bytes": int(audit["bytes"]),
            "lens_sha256": audit["sha256"],
            "lens_save_dtype": audit.get("lens_save_dtype", protocol.LENS_SERIALIZATION_DTYPE),
            "lens_save_load_max_abs": save_load_max_abs,
        }
        self.lenses[unit["unit"]] = lens
        self.lenses[f"{unit['unit']}__reloaded"] = reloaded
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
            "fit_wall_clock_seconds_per_prompt",
            seconds / unit["prompt_count"],
            condition=condition,
            n=unit["prompt_count"],
            numerator=seconds,
            denominator=unit["prompt_count"],
            stratum=unit["unit"],
        )
        self.add_metric(
            "gpu_peak_allocated_bytes",
            memory.get("gpu_peak_allocated_bytes"),
            condition=condition,
            stratum=unit["unit"],
        )
        self.add_metric(
            "gpu_peak_reserved_bytes",
            memory.get("gpu_peak_reserved_bytes"),
            condition=condition,
            stratum=unit["unit"],
        )
        self.add_metric(
            "checkpoint_bytes", checkpoint_bytes, condition=condition, stratum=unit["unit"]
        )
        self.add_metric(
            "lens_bytes", int(audit["bytes"]), condition=condition, stratum=unit["unit"]
        )
        for layer in protocol.SOURCE_LAYERS:
            self.add_metric(
                "matrix_norm",
                matrices[str(layer)]["norm"],
                condition=condition,
                stratum=f"{unit['unit']}::layer_{layer}",
            )
        return detail

    def register_fit_figures(self, detail: dict[str, Any], series: str) -> None:
        self.add_figure_row(
            figure_id="fig_fit_cost",
            series=series,
            x_label="n_prompts",
            x_value=detail["prompt_count"],
            y_label="fit_wall_clock_seconds",
            y_value=detail["fit_seconds"],
        )
        self.add_figure_row(
            figure_id="fig_fit_memory",
            series=series,
            x_label="n_prompts",
            x_value=detail["prompt_count"],
            y_label="gpu_peak_reserved_bytes",
            y_value=detail["memory"].get("gpu_peak_reserved_bytes"),
        )
        for label, key, unit_name in (
            ("fit_wall_clock", "fit_seconds", "seconds"),
            ("fit_wall_clock_per_prompt", "fit_seconds_per_prompt", "seconds"),
            ("checkpoint_size", "checkpoint_bytes", "bytes"),
            ("lens_size", "lens_bytes", "bytes"),
        ):
            self.add_paper_row(
                row_label=label,
                condition=detail["condition"],
                n_prompts=detail["prompt_count"],
                metric=key,
                value=detail[key],
                unit=unit_name,
            )
        self.add_paper_row(
            row_label="gpu_peak_reserved",
            condition=detail["condition"],
            n_prompts=detail["prompt_count"],
            metric="gpu_peak_reserved_bytes",
            value=detail["memory"].get("gpu_peak_reserved_bytes"),
            unit="bytes",
        )

    def compare_units(
        self, left_unit: str, right_unit: str, *, condition: str, record_id: str
    ) -> dict[str, Any]:
        comparison = protocol.compare_lens_matrices(
            self.math,
            _jacobians(self.backend, self.lenses[left_unit]),
            _jacobians(self.backend, self.lenses[right_unit]),
        )
        comparison["left"] = left_unit
        comparison["right"] = right_unit
        self.add_record(
            record_id=record_id,
            source_item_id=f"{left_unit}|{right_unit}",
            condition=condition,
            status="success",
            input_payload={"left": left_unit, "right": right_unit},
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
        corpus_payload = {
            "path": self.corpus["path"],
            "file_sha256": self.corpus["file_sha256"],
            "canonical_sha256": self.corpus["canonical_sha256"],
            "bytes": self.corpus["bytes"],
            "counts": self.corpus["counts"],
            "proxy_tokenizer": self.corpus["proxy_tokenizer"],
            "proxy_token_min": self.corpus["proxy_token_min"],
            "proxy_token_max": self.corpus["proxy_token_max"],
        }
        self.add_record(
            record_id="corpus::registration",
            source_item_id=self.corpus["canonical_sha256"],
            condition="corpus_registration",
            status="success",
            input_payload=corpus_payload,
            evaluation={
                **corpus_payload,
                "fit_prompt_ids": list(self.corpus["roles"]["fit"]),
                "heldout_prompt_ids": list(self.corpus["roles"]["heldout"]),
                "reserve_prompt_ids": list(self.corpus["roles"]["reserve"]),
                "fit_a_prompt_ids": list(self.plan["fit_a"]["prompt_ids"]),
                "fit_b_shard_prompt_ids": [
                    list(shard["prompt_ids"]) for shard in self.plan["fit_b_shards"]
                ],
                "control_prompt_ids": list(self.plan["control_direct"]["prompt_ids"]),
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
            if record["role"] == "reserve":
                continue
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

    def stage_s2_fit_a10(self) -> dict[str, Any]:
        admission = self.time_admission("S2_fit_a10", protocol.FIT_A_PROMPTS)
        if not admission["admitted"]:
            return {
                "_status": "skipped_time_guard",
                "time_admission": admission,
            }
        detail = self.fit_unit(self.plan["fit_a"], "fit_a_direct")
        self.register_fit_figures(detail, "fit_a_direct")
        return {"time_admission": admission, "fit": detail}

    def stage_s3_fit_b25(self) -> dict[str, Any]:
        admission = self.time_admission("S3_fit_b25_sharded_merge", protocol.FIT_B_PROMPTS)
        if not admission["admitted"]:
            return {"_status": "skipped_time_guard", "time_admission": admission}
        shard_details = []
        for shard in self.plan["fit_b_shards"]:
            index = shard["unit"].rsplit("_", 1)[-1]
            shard_details.append(self.fit_unit(shard, f"fit_b_shard_{index}"))
        self.backend.start_memory()
        started = time.monotonic()
        merged = self.backend.merge(
            [self.lenses[shard["unit"]] for shard in self.plan["fit_b_shards"]]
        )
        merge_seconds = time.monotonic() - started
        merge_memory = self.backend.finish_memory()
        metadata = _lens_metadata(self.backend, merged)
        if metadata["n_prompts"] != protocol.FIT_B_PROMPTS:
            raise base.NumericalValidationError(
                f"merged lens reports {metadata['n_prompts']} prompts, expected "
                f"{protocol.FIT_B_PROMPTS}"
            )
        self.lenses["fit_b_merged"] = merged
        merged_jacobians = _jacobians(self.backend, merged)
        matrices = {}
        finite_layers = 0
        for layer in protocol.SOURCE_LAYERS:
            stats = self.math.matrix_stats(merged_jacobians[layer])
            matrices[str(layer)] = stats
            finite_layers += int(bool(stats["finite"]))
            self.add_metric(
                "matrix_norm",
                stats["norm"],
                condition="fit_b_merged",
                stratum=f"fit_b_merged::layer_{layer}",
            )
        merged_lens_path = self.work_dir / "fit_b_merged_lens.pt"
        reloaded, audit = self.backend.save_lens(merged, merged_lens_path)
        self.lenses["fit_b_merged__reloaded"] = reloaded
        merged_save_load_max_abs = max(
            float(value) for value in audit["exact_max_abs"].values()
        )
        total_fit_seconds = sum(item["fit_seconds"] for item in shard_details)
        detail = {
            "unit": "fit_b_merged",
            "condition": "fit_b_merged",
            "prompt_ids": list(self.plan["fit_b_prompt_ids"]),
            "prompt_count": protocol.FIT_B_PROMPTS,
            "prompt_order_sha256": self.plan["fit_b_prompt_order_sha256"],
            "shards": [item["unit"] for item in shard_details],
            "shard_sizes": list(protocol.FIT_B_SHARDS),
            "dim_batch": self.dim_batch,
            "fit_seconds": total_fit_seconds,
            "fit_seconds_per_prompt": total_fit_seconds / protocol.FIT_B_PROMPTS,
            "merge_seconds": merge_seconds,
            "memory": merge_memory,
            "shard_peak_reserved_bytes": max(
                int(item["memory"].get("gpu_peak_reserved_bytes") or 0)
                for item in shard_details
            ),
            "lens_metadata": metadata,
            "matrices": matrices,
            "matrix_finite_layers": finite_layers,
            "matrix_layers": len(protocol.SOURCE_LAYERS),
            "checkpoint_bytes": sum(item["checkpoint_bytes"] for item in shard_details),
            "lens_bytes": int(audit["bytes"]),
            "lens_sha256": audit["sha256"],
            "lens_save_load_max_abs": merged_save_load_max_abs,
        }
        self.state.setdefault("fits", {})["fit_b_merged"] = detail
        self.add_record(
            record_id="fit::fit_b_merged",
            source_item_id=self.plan["fit_b_prompt_order_sha256"],
            condition="fit_b_merged",
            status="success",
            input_payload={
                "shards": [list(shard["prompt_ids"]) for shard in self.plan["fit_b_shards"]],
                "source_layers": list(protocol.SOURCE_LAYERS),
                "target_layer": protocol.TARGET_LAYER,
                "dim_batch": self.dim_batch,
            },
            evaluation=detail,
        )
        for metric, value in (
            ("fit_wall_clock_seconds", total_fit_seconds),
            ("fit_wall_clock_seconds_per_prompt", total_fit_seconds / protocol.FIT_B_PROMPTS),
            ("merge_seconds", merge_seconds),
            ("checkpoint_bytes", detail["checkpoint_bytes"]),
            ("lens_bytes", detail["lens_bytes"]),
            ("gpu_peak_reserved_bytes", detail["shard_peak_reserved_bytes"]),
            (
                "gpu_peak_allocated_bytes",
                max(
                    int(item["memory"].get("gpu_peak_allocated_bytes") or 0)
                    for item in shard_details
                ),
            ),
        ):
            self.add_metric(
                metric,
                value,
                condition="fit_b_merged",
                n=protocol.FIT_B_PROMPTS,
                stratum="fit_b_merged",
            )
        self.register_fit_figures(detail, "fit_b_merged")
        for item in shard_details:
            self.add_figure_row(
                figure_id="fig_fit_cost",
                series="fit_b_shards",
                x_label="n_prompts",
                x_value=item["prompt_count"],
                y_label="fit_wall_clock_seconds",
                y_value=item["fit_seconds"],
            )

        weighted_comparison = self.weighted_recombination_check(merged_jacobians)

        repeatability = None
        if "fit_a_direct" in self.lenses:
            repeatability = self.compare_units(
                "fit_b_shard_1",
                "fit_a_direct",
                condition="fit_repeatability",
                record_id="comparison::fit_repeatability",
            )
            self.values["fit_repeatability_max_abs"] = repeatability["max_abs"]
            self.add_metric(
                "fit_repeatability_max_abs",
                repeatability["max_abs"],
                condition="fit_repeatability",
                n=protocol.FIT_A_PROMPTS,
            )

        finite_rate_units = [detail] + shard_details
        if "fit_a_direct" in self.state.get("fits", {}):
            finite_rate_units.append(self.state["fits"]["fit_a_direct"])
        finite_numerator = sum(item["matrix_finite_layers"] for item in finite_rate_units)
        finite_denominator = sum(item["matrix_layers"] for item in finite_rate_units)
        self.state["finite_numerator"] = finite_numerator
        self.state["finite_denominator"] = finite_denominator
        return {
            "time_admission": admission,
            "shards": shard_details,
            "merged": detail,
            "weighted_recombination": weighted_comparison,
            "fit_repeatability": repeatability,
        }

    def weighted_recombination_check(
        self, merged_jacobians: dict[int, Any]
    ) -> dict[str, Any]:
        """Compare the official merge with our own n-weighted recombination."""

        recombined = {}
        for layer in protocol.SOURCE_LAYERS:
            recombined[layer] = self.math.matrix_weighted_mean(
                [
                    (
                        _jacobians(self.backend, self.lenses[shard["unit"]])[layer],
                        shard["prompt_count"],
                    )
                    for shard in self.plan["fit_b_shards"]
                ]
            )
        comparison = protocol.compare_lens_matrices(
            self.math, recombined, merged_jacobians
        )
        comparison["left"] = "weighted_recombination"
        comparison["right"] = "fit_b_merged"
        comparison["weights"] = list(protocol.FIT_B_SHARDS)
        self.values["weighted_recombination_vs_direct_max_abs"] = comparison["max_abs"]
        self.add_metric(
            "weighted_recombination_vs_direct_max_abs",
            comparison["max_abs"],
            condition="weighted_recombination_vs_direct",
            n=protocol.FIT_B_PROMPTS,
        )
        self.add_record(
            record_id="comparison::weighted_recombination_vs_merge",
            source_item_id="fit_b_merged",
            condition="weighted_recombination_vs_direct",
            status="success",
            input_payload={"weights": list(protocol.FIT_B_SHARDS)},
            evaluation=comparison,
        )
        if comparison["max_abs"] > protocol.MERGE_MAX_ABS_TOLERANCE:
            self.deviations.append(
                {
                    "id": "merge-weighting-differs",
                    "description": (
                        "JacobianLens.merge does not equal an n-prompt-weighted "
                        "recombination of the shard matrices "
                        f"(max_abs={comparison['max_abs']:.6g})."
                    ),
                    "justification": (
                        "Recorded as an observation; the registered stability "
                        "criterion is the shard-merge vs direct-subset control."
                    ),
                    "effect_on_interpretation": "none",
                }
            )
        return comparison

    def stage_s4_merge_control(self) -> dict[str, Any]:
        admission = self.time_admission("S4_merge_control", protocol.CONTROL_SUBSET_SIZE)
        if not admission["admitted"]:
            return {"_status": "skipped_time_guard", "time_admission": admission}
        control_details = []
        for shard in self.plan["control_shards"]:
            index = shard["unit"].rsplit("_", 1)[-1]
            control_details.append(self.fit_unit(shard, f"control_shard_{index}"))
        merged = self.backend.merge(
            [self.lenses[shard["unit"]] for shard in self.plan["control_shards"]]
        )
        self.lenses["control_merged"] = merged
        metadata = _lens_metadata(self.backend, merged)
        if metadata["n_prompts"] != protocol.CONTROL_SUBSET_SIZE:
            raise base.NumericalValidationError(
                "control merge prompt accounting mismatch"
            )
        direct_unit = self.plan["control_direct"]["unit"]
        direct_key = "fit_b_shard_3" if direct_unit == "control_direct" else direct_unit
        if direct_key not in self.lenses:
            direct_key = "fit_b_shard_3"
        comparison = self.compare_units(
            "control_merged",
            direct_key,
            condition="shard_merge_vs_direct",
            record_id="comparison::shard_merge_vs_direct",
        )
        self.values["shard_merge_vs_direct_max_abs"] = comparison["max_abs"]
        self.values["shard_merge_vs_direct_relative_frobenius"] = comparison[
            "max_relative_frobenius"
        ]
        self.add_metric(
            "shard_merge_vs_direct_max_abs",
            comparison["max_abs"],
            condition="shard_merge_vs_direct",
            n=protocol.CONTROL_SUBSET_SIZE,
            threshold=protocol.MERGE_MAX_ABS_TOLERANCE,
            passed=comparison["max_abs"] <= protocol.MERGE_MAX_ABS_TOLERANCE,
        )
        self.add_metric(
            "shard_merge_vs_direct_relative_frobenius",
            comparison["max_relative_frobenius"],
            condition="shard_merge_vs_direct",
            n=protocol.CONTROL_SUBSET_SIZE,
            threshold=protocol.MERGE_RELATIVE_TOLERANCE,
            passed=comparison["max_relative_frobenius"]
            <= protocol.MERGE_RELATIVE_TOLERANCE,
        )
        self.add_paper_row(
            row_label="shard_merge_vs_direct",
            condition="shard_merge_vs_direct",
            n_prompts=protocol.CONTROL_SUBSET_SIZE,
            metric="max_abs",
            value=comparison["max_abs"],
            unit="abs",
        )
        return {
            "time_admission": admission,
            "control_shards": control_details,
            "comparison": comparison,
            "direct_reference": direct_key,
        }

    def stage_s5_convergence(self) -> dict[str, Any]:
        if "fit_a_direct" not in self.lenses or "fit_b_merged" not in self.lenses:
            return {
                "_status": "blocked",
                "reason": "both the 10-prompt and 25-prompt lenses are required",
            }
        comparison = self.compare_units(
            "fit_a_direct",
            "fit_b_merged",
            condition="convergence_10_vs_25",
            record_id="comparison::convergence_10_vs_25",
        )
        self.values["convergence_relative_frobenius_10_vs_25"] = comparison[
            "max_relative_frobenius"
        ]
        self.values["convergence_cosine_10_vs_25"] = comparison["min_cosine"]
        self.add_metric(
            "convergence_relative_frobenius_10_vs_25",
            comparison["max_relative_frobenius"],
            condition="convergence_10_vs_25",
            n=protocol.FIT_B_PROMPTS,
            threshold=protocol.CONVERGENCE_RELATIVE_FROBENIUS_MAX,
            passed=comparison["max_relative_frobenius"]
            <= protocol.CONVERGENCE_RELATIVE_FROBENIUS_MAX,
        )
        self.add_metric(
            "convergence_cosine_10_vs_25",
            comparison["min_cosine"],
            condition="convergence_10_vs_25",
            n=protocol.FIT_B_PROMPTS,
            threshold=protocol.CONVERGENCE_COSINE_MIN,
            passed=comparison["min_cosine"] >= protocol.CONVERGENCE_COSINE_MIN,
        )
        for layer, values in sorted(comparison["layers"].items()):
            self.add_metric(
                "convergence_relative_frobenius_10_vs_25",
                values["relative_frobenius"],
                condition="convergence_10_vs_25",
                stratum=f"layer_{layer}",
                n=protocol.FIT_B_PROMPTS,
            )
            self.add_figure_row(
                figure_id="fig_convergence",
                series=f"layer_{layer}",
                x_label="n_prompts_reference",
                x_value=protocol.FIT_B_PROMPTS,
                y_label="relative_frobenius_vs_10",
                y_value=values["relative_frobenius"],
            )
            self.add_figure_row(
                figure_id="fig_convergence_cosine",
                series=f"layer_{layer}",
                x_label="n_prompts_reference",
                x_value=protocol.FIT_B_PROMPTS,
                y_label="cosine_vs_10",
                y_value=values["cosine"],
            )
        self.add_paper_row(
            row_label="convergence_10_vs_25",
            condition="convergence_10_vs_25",
            n_prompts=protocol.FIT_B_PROMPTS,
            metric="relative_frobenius",
            value=comparison["max_relative_frobenius"],
            unit="ratio",
        )
        self.add_paper_row(
            row_label="convergence_10_vs_25",
            condition="convergence_10_vs_25",
            n_prompts=protocol.FIT_B_PROMPTS,
            metric="cosine",
            value=comparison["min_cosine"],
            unit="cosine",
        )
        finite_numerator = self.state.get("finite_numerator", 0)
        finite_denominator = self.state.get("finite_denominator", 0)
        if finite_denominator:
            rate = finite_numerator / finite_denominator
            self.values["matrix_finite_rate"] = rate
            self.add_metric(
                "matrix_finite_rate",
                rate,
                condition="fit_b_merged",
                n=finite_denominator,
                numerator=finite_numerator,
                denominator=finite_denominator,
                threshold=protocol.FINITE_RATE_MIN,
                passed=rate >= protocol.FINITE_RATE_MIN,
            )
        save_load = [
            item["lens_save_load_max_abs"]
            for item in self.state.get("fits", {}).values()
            if item.get("lens_save_load_max_abs") is not None
        ]
        if save_load:
            worst = max(save_load)
            self.values["lens_save_load_max_abs"] = worst
            self.add_metric(
                "lens_save_load_max_abs",
                worst,
                condition="fit_b_merged",
                n=len(save_load),
                threshold=protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
                passed=worst <= protocol.SAVE_LOAD_MAX_ABS_TOLERANCE,
            )
        return {"comparison": comparison}

    def stage_s6_apply_stability(self) -> dict[str, Any]:
        if "fit_a_direct" not in self.lenses or "fit_b_merged" not in self.lenses:
            return {
                "_status": "blocked",
                "reason": "both the 10-prompt and 25-prompt lenses are required",
            }
        heldout = self.plan["heldout"]
        overlaps: list[float] = []
        correlations: list[float] = []
        cosines: list[float] = []
        consistent = True
        per_prompt: list[dict[str, Any]] = []
        for prompt_id, text in zip(heldout["prompt_ids"], heldout["texts"], strict=True):
            logits_a, model_logits_a, seq_len = self.backend.apply(
                self.lenses["fit_a_direct"], text
            )
            logits_b, model_logits_b, _ = self.backend.apply(
                self.lenses["fit_b_merged"], text
            )
            reloaded_logits, _, _ = self.backend.apply(
                self.lenses["fit_b_merged__reloaded"], text
            )
            prompt_overlaps = []
            prompt_correlations = []
            prompt_cosines = []
            layers_payload: dict[str, Any] = {}
            for layer in protocol.SOURCE_LAYERS:
                comparison = protocol.compare_logit_vectors(
                    logits_a[layer], logits_b[layer]
                )
                layer_consistent = self.math.allclose(
                    logits_b[layer], reloaded_logits[layer]
                )
                consistent = consistent and layer_consistent
                prompt_overlaps.append(comparison["top_k"]["fraction"])
                prompt_correlations.append(comparison["rank_correlation"])
                prompt_cosines.append(comparison["cosine"])
                layers_payload[str(layer)] = {
                    **comparison,
                    "save_load_apply_consistent": layer_consistent,
                }
            prompt_overlap = protocol.mean(prompt_overlaps)
            prompt_correlation = protocol.mean(prompt_correlations)
            prompt_cosine = protocol.mean(prompt_cosines)
            overlaps.append(prompt_overlap)
            correlations.append(prompt_correlation)
            cosines.append(prompt_cosine)
            evaluation = {
                "prompt_id": prompt_id,
                "sequence_length": seq_len,
                "model_logit_dimension": len(model_logits_a),
                "model_logits_match_dimension": len(model_logits_a)
                == len(model_logits_b),
                "layers": layers_payload,
                "topk_overlap_mean": prompt_overlap,
                "rank_correlation_mean": prompt_correlation,
                "logit_cosine_mean": prompt_cosine,
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
                },
                evaluation=evaluation,
            )
            self.add_metric(
                "heldout_topk_overlap",
                prompt_overlap,
                condition="heldout_apply",
                stratum=prompt_id,
                n=protocol.TOP_K,
            )
            self.add_metric(
                "heldout_rank_correlation",
                prompt_correlation,
                condition="heldout_apply",
                stratum=prompt_id,
            )
            self.add_figure_row(
                figure_id="fig_heldout_apply_stability",
                series="topk_overlap",
                x_label="heldout_prompt_id",
                x_value=prompt_id,
                y_label="topk_overlap_10_vs_25",
                y_value=prompt_overlap,
            )
            self.add_figure_row(
                figure_id="fig_heldout_apply_stability",
                series="rank_correlation",
                x_label="heldout_prompt_id",
                x_value=prompt_id,
                y_label="rank_correlation_10_vs_25",
                y_value=prompt_correlation,
            )
        overlap_mean = protocol.mean(overlaps)
        correlation_mean = protocol.mean(correlations)
        cosine_mean = protocol.mean(cosines)
        self.values["heldout_topk_overlap_mean"] = overlap_mean
        self.values["heldout_rank_correlation_mean"] = correlation_mean
        self.values["apply_save_load_consistency"] = 1.0 if consistent else 0.0
        self.add_metric(
            "heldout_topk_overlap_mean",
            overlap_mean,
            condition="apply_stability",
            n=len(overlaps),
            threshold=protocol.TOPK_OVERLAP_MIN,
            passed=overlap_mean >= protocol.TOPK_OVERLAP_MIN,
        )
        self.add_metric(
            "heldout_rank_correlation_mean",
            correlation_mean,
            condition="apply_stability",
            n=len(correlations),
            threshold=protocol.RANK_CORRELATION_MIN,
            passed=correlation_mean >= protocol.RANK_CORRELATION_MIN,
        )
        self.add_metric(
            "heldout_logit_cosine_mean",
            cosine_mean,
            condition="apply_stability",
            n=len(cosines),
        )
        self.add_metric(
            "apply_save_load_consistency",
            1.0 if consistent else 0.0,
            condition="apply_stability",
            n=len(per_prompt),
            threshold=1.0,
            passed=consistent,
        )
        for label, value, unit_name in (
            ("heldout_topk_overlap", overlap_mean, "ratio"),
            ("heldout_rank_correlation", correlation_mean, "rho"),
            ("heldout_logit_cosine", cosine_mean, "cosine"),
        ):
            self.add_paper_row(
                row_label=label,
                condition="apply_stability",
                n_prompts=len(per_prompt),
                metric=f"{label}_mean",
                value=value,
                unit=unit_name,
            )
        self.result_notes.append(
            "Top-k overlap and rank correlation are technical stability "
            "statistics for two fitted linear operators. They are not "
            "semantic, behavioral, or interpretive evidence."
        )
        return {
            "heldout_prompts": len(per_prompt),
            "topk_overlap_mean": overlap_mean,
            "rank_correlation_mean": correlation_mean,
            "logit_cosine_mean": cosine_mean,
            "apply_save_load_consistency": consistent,
            "per_prompt": per_prompt,
        }

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
        )

    def export(self, decision: dict[str, Any]) -> dict[str, Any]:
        end_time_utc = feasibility.utc_now()
        status = decision["status"]
        sample_size = {
            "corpus_prompts": protocol.CORPUS_TOTAL,
            "fit_a_prompts": protocol.FIT_A_PROMPTS,
            "fit_b_prompts": protocol.FIT_B_PROMPTS,
            "fit_b_shards": list(protocol.FIT_B_SHARDS),
            "control_subset_prompts": protocol.CONTROL_SUBSET_SIZE,
            "control_subset_shards": list(protocol.CONTROL_SUBSET_SHARDS),
            "heldout_prompts": protocol.HELDOUT_PROMPTS,
            "reserve_prompts": protocol.RESERVE_PROMPTS,
            "source_layers": list(protocol.SOURCE_LAYERS),
            "target_layer": protocol.TARGET_LAYER,
        }
        snapshot = protocol.build_protocol_snapshot(sample_size=sample_size)
        protocol_hash = base.sha256_bytes(base.canonical_json_bytes(snapshot))
        inputs = {
            "corpus_path": self.corpus["path"],
            "corpus_file_sha256": self.corpus["file_sha256"],
            "corpus_canonical_sha256": self.corpus["canonical_sha256"],
            "corpus_counts": self.corpus["counts"],
            "fit_a_prompt_ids": list(self.plan["fit_a"]["prompt_ids"]),
            "fit_b_shard_prompt_ids": [
                list(shard["prompt_ids"]) for shard in self.plan["fit_b_shards"]
            ],
            "control_prompt_ids": list(self.plan["control_direct"]["prompt_ids"]),
            "heldout_prompt_ids": list(self.plan["heldout"]["prompt_ids"]),
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
            status=status,
            start_time_utc=self.start_time_utc,
            end_time_utc=end_time_utc,
            code_commit=code_commit(),
            image_digest=os.getenv("JSPACE_IMAGE_DIGEST", "").strip() or None,
            hardware=hardware,
            inputs=inputs,
            protocol_hash=protocol_hash,
            subagents=[
                {
                    "name": "agent-a-track-a",
                    "role": "phase 0.5B saturation implementation",
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
            ("S2_fit_a10", self.stage_s2_fit_a10),
            ("S3_fit_b25_sharded_merge", self.stage_s3_fit_b25),
            ("S4_merge_control", self.stage_s4_merge_control),
            ("S5_convergence", self.stage_s5_convergence),
            ("S6_apply_stability", self.stage_s6_apply_stability),
        )
        try:
            for name, function in sequence:
                self.execute(name, function)
        except base.ApplicationTimeoutError as error:
            self.blocked_reason = feasibility.safe_error(error)
        except (KeyboardInterrupt, SystemExit) as error:  # pragma: no cover - signal path
            self.blocked_reason = f"interrupted: {type(error).__name__}"
        if self.errors and self.blocked_reason is None:
            failed = sorted({item["stage"] for item in self.errors})
            if "S0_environment" in failed or "S1_model" in failed:
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
            "RESULTS_DIR", str(PROJECT_ROOT / "results" / "runs" / "phase05-jlens-saturation")
        ),
    )
    parser.add_argument(
        "--corpus",
        default=str(PROJECT_ROOT / "data" / "jlens_saturation_prompts.jsonl"),
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
    return parser.parse_args(argv)


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
        return SaturationRunner(args).run()
    finally:
        if not (args.self_test or args.dry_run) and hasattr(signal, "SIGALRM"):
            signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
