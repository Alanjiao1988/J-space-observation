#!/usr/bin/env python3
"""Execute registered full-layer S2 smoke, fit, merge, and diagnostics."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = PROJECT_ROOT / "src" / "jspace_observation"
SCRIPT_ROOT = Path(__file__).resolve().parent
BASE_HELPER_ROOT = Path("/workspace/src/jspace_observation")
BASE_SCRIPT_ROOT = Path("/workspace/scripts")
for entry in (HELPER_ROOT, SCRIPT_ROOT, BASE_HELPER_ROOT, BASE_SCRIPT_ROOT):
    if entry.is_dir() and str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import jlens_s2_protocol as s2  # noqa: E402
import jlens_s2_runtime as runtime  # noqa: E402


WORK_ROOT = Path(os.getenv("RESULTS_DIR", "/workspace/runtime/results"))


def safe_error(error: BaseException) -> str:
    text = re.sub(
        r"(?i)(token|secret|password|sig)=\S+",
        r"\1=<redacted>",
        f"{type(error).__name__}: {error}",
    )
    return text[:4000]


def required_environment() -> dict[str, str]:
    values = {
        "attempt_id": os.getenv("JSPACE_ATTEMPT_ID", "").strip(),
        "code_commit": os.getenv("JSPACE_CODE_COMMIT", "").strip(),
        "image_digest": os.getenv("JSPACE_IMAGE_DIGEST", "").strip(),
        "run_id": os.getenv("JSPACE_S2_RUN_ID", "").strip(),
    }
    missing = sorted(key for key, value in values.items() if not value)
    if missing:
        raise runtime.S2RuntimeError(
            "missing execution environment: " + ", ".join(missing)
        )
    return values


def finalize_pack(
    store: runtime.BlobStore,
    *,
    stage: str,
    directory: Path,
    files: list[Path],
    subprefix: str,
    complete: bool,
) -> dict[str, Any]:
    manifest = runtime.pack_manifest(
        stage=stage,
        files=files,
        root=directory,
        complete=complete,
    )
    manifest_path = directory / "artifact_manifest.json"
    runtime.write_json(manifest_path, manifest)
    return runtime.upload_pack(
        store,
        root=directory,
        files=[*files, manifest_path],
        subprefix=subprefix,
    )


def classify_failure(error: BaseException) -> str:
    message = str(error).lower()
    name = type(error).__name__.lower()
    if "outofmemory" in name or "out of memory" in message:
        return "oom"
    if any(
        fragment in message
        for fragment in (
            "identity mismatch",
            "token ids differ",
            "non-finite",
            "layer set",
            "shape",
            "dtype",
        )
    ):
        return "scientific_failed"
    return "infrastructure_failed"


def run_smoke(args: argparse.Namespace) -> int:
    env = required_environment()
    if args.dim_batch not in s2.DIM_BATCH_CANDIDATES:
        raise runtime.S2RuntimeError("unregistered dim_batch")
    directory = WORK_ROOT / f"smoke-dim-{args.dim_batch}"
    directory.mkdir(parents=True, exist_ok=True)
    store = runtime.runtime_store_from_environment()
    subprefix = args.subprefix.strip("/")
    result: dict[str, Any] = {
        "attempt_id": env["attempt_id"],
        "comparison_to_dim1": [],
        "dim_batch": args.dim_batch,
        "image_digest": env["image_digest"],
        "rows": [],
        "source_layers": list(s2.SOURCE_LAYERS),
        "status": "failed",
        "target_layer": s2.TARGET_LAYER,
    }
    files: list[Path] = []
    try:
        corpus_pack = runtime.load_registered_corpus()
        rows = runtime.role_slice(corpus_pack, "smoke", 1, 2)
        backend = runtime.OfficialBackend(require_gpu=True)
        result["environment"] = backend.prepare()
        result["package_versions"] = runtime.package_versions()
        backend.verify_tokenization(rows)
        for row in rows:
            backend.start_memory()
            started = time.monotonic()
            jacobians, seq_len, valid_positions = backend.jacobian_for_prompt(
                row["raw_text"],
                args.dim_batch,
            )
            seconds = time.monotonic() - started
            memory = backend.finish_memory()
            matrices = runtime.validate_jacobians(backend.torch, jacobians)
            if seq_len != s2.MAX_SEQ_LEN or valid_positions != (
                s2.MAX_SEQ_LEN - s2.SKIP_FIRST - 1
            ):
                raise runtime.S2RuntimeError("smoke token-position identity mismatch")
            lens = backend.lens_from_jacobians(jacobians, 1)
            lens_path = directory / f"smoke-{row['role_index']}.pt"
            _loaded, audit = backend.save_lossless(lens, lens_path)
            files.append(lens_path)
            result["rows"].append(
                {
                    "lens": {
                        "bytes": audit["bytes"],
                        "relative_path": lens_path.name,
                        "sha256": audit["sha256"],
                    },
                    "matrices": matrices,
                    "memory": memory,
                    "role_index": row["role_index"],
                    "row_id": row["row_id"],
                    "seconds": seconds,
                    "sequence_token_ids_sha256": row["token_ids_sha256"],
                    "valid_positions": valid_positions,
                }
            )
        result["finite_float32"] = True
        result["matrix_shapes_valid"] = True
        result["peak_reserved_ratio"] = max(
            row["memory"]["peak_reserved_ratio"] for row in result["rows"]
        )
        result["seconds_per_prompt"] = max(
            row["seconds"] for row in result["rows"]
        )
        result["status"] = "success"
    except Exception as exc:
        result["error"] = safe_error(exc)
        result["failure_class"] = classify_failure(exc)
        result["status"] = (
            "oom" if result["failure_class"] == "oom" else "failed"
        )
        result["traceback"] = traceback.format_exc(limit=20)[-8000:]
    attempt_path = directory / "smoke_attempt.json"
    runtime.write_json(attempt_path, result)
    files.append(attempt_path)
    finalize_pack(
        store,
        stage="S2-T0-smoke",
        directory=directory,
        files=files,
        subprefix=subprefix,
        complete=True,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


def _download_lens(
    store: runtime.BlobStore,
    blob_name: str,
    expected_sha256: str,
    path: Path,
) -> dict[str, Any]:
    downloaded = store.download_absolute_to(blob_name, path)
    if downloaded["sha256"] != expected_sha256:
        raise runtime.S2RuntimeError(f"lens SHA-256 mismatch: {blob_name}")
    return downloaded


def run_fit_shard(args: argparse.Namespace) -> int:
    env = required_environment()
    if args.role not in {"A", "B"}:
        raise runtime.S2RuntimeError("production fit role must be A or B")
    if args.dim_batch not in s2.DIM_BATCH_CANDIDATES:
        raise runtime.S2RuntimeError("unregistered production dim_batch")
    directory = WORK_ROOT / args.shard_id / env["attempt_id"]
    directory.mkdir(parents=True, exist_ok=True)
    store = runtime.runtime_store_from_environment()
    subprefix = args.subprefix.strip("/")
    checkpoint_path = directory / "checkpoint.pt"
    result: dict[str, Any] = {
        "attempt_id": env["attempt_id"],
        "completed_sequence_ids": [],
        "dim_batch": args.dim_batch,
        "end_index": args.end_index,
        "image_digest": env["image_digest"],
        "resumed": bool(args.resume_checkpoint_blob),
        "resume_source": None,
        "role": args.role,
        "shard_id": args.shard_id,
        "start_index": args.start_index,
        "status": "infrastructure_failed",
    }
    initial_next_idx = 0
    mirror: runtime.CheckpointMirror | None = None
    try:
        corpus_pack = runtime.load_registered_corpus()
        rows = runtime.role_slice(
            corpus_pack,
            args.role,
            args.start_index,
            args.end_index,
        )
        backend = runtime.OfficialBackend(require_gpu=True)
        result["environment"] = backend.prepare()
        result["package_versions"] = runtime.package_versions()
        backend.verify_tokenization(rows)
        if args.resume_checkpoint_blob:
            if (
                not args.resume_checkpoint_sha256
                or not args.resume_checkpoint_manifest_blob
                or not args.resume_checkpoint_manifest_sha256
            ):
                raise runtime.S2RuntimeError(
                    "resume requires checkpoint and manifest Blob SHA-256 bindings"
                )
            shard_prefix = (
                f"{store.prefix}/shards/{args.shard_id}/attempts/"
            )
            if (
                not args.resume_checkpoint_blob.startswith(shard_prefix)
                or not args.resume_checkpoint_manifest_blob.startswith(shard_prefix)
            ):
                raise runtime.S2RuntimeError(
                    "resume checkpoint is not bound to the requested shard"
                )
            manifest_bytes = store.download_absolute(
                args.resume_checkpoint_manifest_blob
            )
            if (
                s2.sha256_bytes(manifest_bytes)
                != args.resume_checkpoint_manifest_sha256
            ):
                raise runtime.S2RuntimeError(
                    "resume checkpoint manifest SHA-256 mismatch"
                )
            checkpoint_manifest = json.loads(manifest_bytes)
            if (
                checkpoint_manifest.get("checkpoint", {}).get("blob")
                != args.resume_checkpoint_blob
                or checkpoint_manifest.get("checkpoint", {}).get("sha256")
                != args.resume_checkpoint_sha256
                or checkpoint_manifest.get("source_layers")
                != list(s2.SOURCE_LAYERS)
                or checkpoint_manifest.get("target_layer") != s2.TARGET_LAYER
                or checkpoint_manifest.get("n_done")
                != checkpoint_manifest.get("next_idx")
            ):
                raise runtime.S2RuntimeError(
                    "resume checkpoint manifest identity mismatch"
                )
            receipt = store.download_absolute_to(
                args.resume_checkpoint_blob,
                checkpoint_path,
            )
            if receipt["sha256"] != args.resume_checkpoint_sha256:
                raise runtime.S2RuntimeError("resume checkpoint SHA-256 mismatch")
            state = runtime.load_checkpoint_state(backend.torch, checkpoint_path)
            initial_next_idx = int(state["next_idx"])
            if (
                checkpoint_manifest["n_done"] != initial_next_idx
                or checkpoint_manifest["checkpoint"]["bytes"] != receipt["bytes"]
            ):
                raise runtime.S2RuntimeError(
                    "resume checkpoint bytes or progress mismatch"
                )
            if initial_next_idx >= len(rows):
                raise runtime.S2RuntimeError(
                    "resume checkpoint already completes the shard"
                )
            result["resume_source"] = {
                "checkpoint_blob": args.resume_checkpoint_blob,
                "checkpoint_bytes": receipt["bytes"],
                "checkpoint_manifest_blob": args.resume_checkpoint_manifest_blob,
                "checkpoint_manifest_sha256": (
                    args.resume_checkpoint_manifest_sha256
                ),
                "checkpoint_sha256": args.resume_checkpoint_sha256,
                "n_done": initial_next_idx,
                "sequence_prefix_sha256": s2.sha256_bytes(
                    s2.canonical_jsonl_bytes(
                        {"sequence_id": row["row_id"]}
                        for row in rows[:initial_next_idx]
                    )
                ),
            }
        result["initial_next_idx"] = initial_next_idx
        mirror = runtime.CheckpointMirror(
            torch_module=backend.torch,
            path=checkpoint_path,
            store=store,
            subprefix=subprefix,
            minimum_next_idx=initial_next_idx,
        )
        mirror.start()
        backend.start_memory()
        started = time.monotonic()
        lens = backend.fit(
            [row["raw_text"] for row in rows],
            dim_batch=args.dim_batch,
            checkpoint_path=checkpoint_path,
            resume=bool(args.resume_checkpoint_blob),
        )
        fit_seconds = time.monotonic() - started
        memory = backend.finish_memory()
        checkpoints = mirror.finish()
        mirror = None
        state = runtime.load_checkpoint_state(backend.torch, checkpoint_path)
        if int(state["n_done"]) != len(rows) or int(lens.n_prompts) != len(rows):
            raise runtime.S2RuntimeError("successful shard prompt accounting mismatch")
        matrices = runtime.validate_jacobians(backend.torch, lens.jacobians)
        lens_path = directory / "lens.pt"
        _loaded, audit = backend.save_lossless(lens, lens_path)
        result.update(
            {
                "checkpoint_every": runtime.CHECKPOINT_EVERY,
                "checkpoint_snapshots": checkpoints,
                "completed_sequence_ids": [row["row_id"] for row in rows],
                "fit_seconds": fit_seconds,
                "fit_seconds_per_new_prompt": fit_seconds
                / (len(rows) - initial_next_idx),
                "lens": {
                    "blob": store.name(f"{subprefix}/lens.pt"),
                    "bytes": audit["bytes"],
                    "sha256": audit["sha256"],
                },
                "lens_metadata": runtime.lens_metadata(lens),
                "matrices": matrices,
                "memory": memory,
                "new_prompt_count": len(rows) - initial_next_idx,
                "save_load_max_abs": max(audit["exact_max_abs"].values()),
                "sequence_ids_sha256": s2.sha256_bytes(
                    s2.canonical_jsonl_bytes(
                        {"sequence_id": row["row_id"]} for row in rows
                    )
                ),
                "status": "success",
            }
        )
        receipt_path = directory / "shard_receipt.json"
        runtime.write_json(receipt_path, result)
        finalize_pack(
            store,
            stage="S2-F0-fit-shard",
            directory=directory,
            files=[lens_path, receipt_path],
            subprefix=subprefix,
            complete=True,
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
        return 0
    except Exception as exc:
        if mirror is not None:
            try:
                result["checkpoint_snapshots"] = mirror.finish()
            except Exception as mirror_error:
                result["checkpoint_mirror_error"] = safe_error(mirror_error)
        if checkpoint_path.is_file():
            try:
                torch_module = importlib.import_module("torch")
                state = runtime.load_checkpoint_state(torch_module, checkpoint_path)
                result["completed_sequence_ids"] = [
                    row["row_id"]
                    for row in runtime.role_slice(
                        runtime.load_registered_corpus(),
                        args.role,
                        args.start_index,
                        args.end_index,
                    )[: int(state["next_idx"])]
                ]
                result["last_checkpoint_next_idx"] = int(state["next_idx"])
            except Exception as checkpoint_error:
                result["checkpoint_inspection_error"] = safe_error(checkpoint_error)
        result["error"] = safe_error(exc)
        result["failure_class"] = classify_failure(exc)
        result["status"] = result["failure_class"]
        result["traceback"] = traceback.format_exc(limit=20)[-8000:]
        failure_path = directory / "shard_failure.json"
        runtime.write_json(failure_path, result)
        finalize_pack(
            store,
            stage="S2-F0-fit-shard-failure",
            directory=directory,
            files=[failure_path],
            subprefix=subprefix,
            complete=False,
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
        return 1


def _load_attempt(
    store: runtime.BlobStore,
    dim_batch: int,
) -> dict[str, Any]:
    return json.loads(
        store.download_bytes(f"dim-{dim_batch}/smoke_attempt.json")
    )


def _lens_io():
    torch_module = importlib.import_module("torch")
    jlens_module = importlib.import_module("jlens")
    return torch_module, jlens_module


def run_smoke_select(args: argparse.Namespace) -> int:
    required_environment()
    directory = WORK_ROOT / "smoke-selection"
    directory.mkdir(parents=True, exist_ok=True)
    store = runtime.runtime_store_from_environment()
    attempts = {
        candidate: _load_attempt(store, candidate)
        for candidate in s2.DIM_BATCH_CANDIDATES
    }
    torch_module, jlens_module = _lens_io()
    comparisons: dict[int, list[dict[str, Any]]] = {}
    reference_lenses = {}
    if attempts[1].get("status") == "success":
        for row in (1, 2):
            path = directory / f"dim1-smoke-{row}.pt"
            lens_info = attempts[1]["rows"][row - 1]["lens"]
            _download_lens(
                store,
                store.name(f"dim-1/smoke-{row}.pt"),
                lens_info["sha256"],
                path,
            )
            reference_lenses[row] = jlens_module.JacobianLens.load(str(path))
    for candidate in s2.DIM_BATCH_CANDIDATES:
        attempt = attempts[candidate]
        if attempt.get("status") != "success":
            attempt["comparison_to_dim1"] = []
            continue
        row_comparisons = []
        for row in (1, 2):
            if candidate == 1:
                candidate_lens = reference_lenses[row]
            else:
                path = directory / f"dim{candidate}-smoke-{row}.pt"
                lens_info = attempt["rows"][row - 1]["lens"]
                _download_lens(
                    store,
                    store.name(f"dim-{candidate}/smoke-{row}.pt"),
                    lens_info["sha256"],
                    path,
                )
                candidate_lens = jlens_module.JacobianLens.load(str(path))
            comparison = runtime.compare_tensor_matrices(
                torch_module,
                candidate_lens.jacobians,
                reference_lenses[row].jacobians,
            )
            row_comparisons.append(
                {"role_index": row, **comparison}
            )
        comparisons[candidate] = row_comparisons
        attempt["comparison_to_dim1"] = [
            {
                "cosine": min(
                    row["layers"][str(layer)]["cosine"]
                    for row in row_comparisons
                ),
                "layer": layer,
                "max_abs": max(
                    row["layers"][str(layer)]["max_abs"]
                    for row in row_comparisons
                ),
                "relative_frobenius": max(
                    row["layers"][str(layer)]["relative_frobenius"]
                    for row in row_comparisons
                ),
            }
            for layer in s2.SOURCE_LAYERS
        ]
    status = "selected"
    terminal_state = None
    try:
        selected = s2.choose_dim_batch(attempts)
        seconds_per_prompt = max(
            float(row["seconds"]) for row in attempts[selected]["rows"]
        )
        planner = s2.plan_final_increment(seconds_per_prompt)
    except s2.S2ProtocolError as exc:
        selected = None
        seconds_per_prompt = None
        planner = None
        status = "blocked"
        terminal_state = "BLOCKED_ON_S2_RUNTIME_COMPATIBILITY"
        error = str(exc)
    result = {
        "attempts": attempts,
        "comparison_rows": comparisons,
        "planner": planner,
        "seconds_per_prompt": seconds_per_prompt,
        "selected_dim_batch": selected,
        "status": status,
        "terminal_state": terminal_state,
    }
    if status == "blocked":
        result["error"] = error
    path = directory / "selected_configuration.json"
    runtime.write_json(path, result)
    finalize_pack(
        store,
        stage="S2-T0-selection",
        directory=directory,
        files=[path],
        subprefix=args.subprefix,
        complete=True,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
    return 0 if status == "selected" else 1


def parse_component(value: str) -> dict[str, str]:
    parts = value.split("|")
    if len(parts) != 2 or any(not part.strip() for part in parts):
        raise argparse.ArgumentTypeError(
            "component must be RECEIPT_BLOB|EXPECTED_RECEIPT_SHA256"
        )
    return {"receipt_blob": parts[0], "receipt_sha256": parts[1]}


def run_merge(args: argparse.Namespace) -> int:
    required_environment()
    directory = WORK_ROOT / f"merge-{args.lens_id}"
    directory.mkdir(parents=True, exist_ok=True)
    store = runtime.runtime_store_from_environment()
    torch_module, jlens_module = _lens_io()
    lenses = []
    components = []
    sequence_ids: list[str] = []
    for index, component in enumerate(args.component, start=1):
        receipt_bytes = store.download_absolute(component["receipt_blob"])
        if s2.sha256_bytes(receipt_bytes) != component["receipt_sha256"]:
            raise runtime.S2RuntimeError("component receipt SHA-256 mismatch")
        receipt = json.loads(receipt_bytes)
        lens_row = receipt["lens"]
        provenance = runtime.validate_receipt_transport(
            store,
            receipt_blob=component["receipt_blob"],
            receipt_sha256=component["receipt_sha256"],
            receipt_bytes=receipt_bytes,
            related_files=[lens_row],
        )
        component_ids = list(
            receipt.get("sequence_ids")
            or receipt.get("completed_sequence_ids")
            or []
        )
        if not component_ids:
            raise runtime.S2RuntimeError("component has no sequence identities")
        if set(sequence_ids) & set(component_ids):
            raise runtime.S2RuntimeError("merge component sequence overlap")
        sequence_ids.extend(component_ids)
        lens_path = directory / f"component-{index}.pt"
        _download_lens(
            store,
            lens_row["blob"],
            lens_row["sha256"],
            lens_path,
        )
        lens = jlens_module.JacobianLens.load(str(lens_path))
        if int(lens.n_prompts) != len(component_ids):
            raise runtime.S2RuntimeError("component prompt count mismatch")
        runtime.validate_jacobians(torch_module, lens.jacobians)
        lenses.append(lens)
        components.append(
            {
                "lens": dict(lens_row),
                "receipt_blob": component["receipt_blob"],
                "receipt_sha256": component["receipt_sha256"],
                "sequence_count": len(component_ids),
                "transport_provenance": provenance,
            }
        )
    if len(sequence_ids) != args.expected_n_prompts:
        raise runtime.S2RuntimeError("merged sequence count mismatch")
    started = time.monotonic()
    merged = jlens_module.JacobianLens.merge(lenses)
    merge_seconds = time.monotonic() - started
    if int(merged.n_prompts) != args.expected_n_prompts:
        raise runtime.S2RuntimeError("official merge n_prompts mismatch")
    independent = runtime.independent_weighted_mean(torch_module, lenses)
    merge_comparison = runtime.compare_tensor_matrices(
        torch_module,
        independent,
        merged.jacobians,
    )
    if (
        merge_comparison["max_abs"] > s2.MERGE_MAX_ABS_TOLERANCE
        or merge_comparison["max_relative_frobenius"]
        > s2.MERGE_RELATIVE_FROBENIUS_TOLERANCE
    ):
        raise runtime.S2RuntimeError("official merge differs from weighted mean")
    from phase05_jlens_feasibility import save_lossless_jacobian_lens

    lens_path = directory / f"{args.lens_id}.pt"
    loaded, audit = save_lossless_jacobian_lens(
        torch_module,
        jlens_module,
        merged,
        lens_path,
    )
    matrices = runtime.validate_jacobians(torch_module, loaded.jacobians)
    save_max = max(audit["exact_max_abs"].values())
    if save_max != 0.0:
        raise runtime.S2RuntimeError("lossless lens save/load is not exact")
    manifest = {
        "components": components,
        "lens": {
            "blob": store.name(f"{args.subprefix.strip('/')}/{args.lens_id}.pt"),
            "bytes": audit["bytes"],
            "sha256": audit["sha256"],
        },
        "lens_id": args.lens_id,
        "matrices": matrices,
        "merge": {
            "independent_weighted_recomputation": merge_comparison,
            "seconds": merge_seconds,
        },
        "metadata": {
            **runtime.lens_metadata(loaded),
            "finite": True,
            "save_load_max_abs": save_max,
        },
        "sequence_ids": sequence_ids,
        "sequence_ids_sha256": s2.sha256_bytes(
            s2.canonical_jsonl_bytes(
                {"sequence_id": sequence_id} for sequence_id in sequence_ids
            )
        ),
    }
    manifest_path = directory / "lens_manifest.json"
    runtime.write_json(manifest_path, manifest)
    finalize_pack(
        store,
        stage="S2-M0-merge",
        directory=directory,
        files=[lens_path, manifest_path],
        subprefix=args.subprefix,
        complete=True,
    )
    print(json.dumps(manifest, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


def run_heldout_shard(args: argparse.Namespace) -> int:
    required_environment()
    directory = WORK_ROOT / f"heldout-{args.start_index}-{args.end_index}"
    directory.mkdir(parents=True, exist_ok=True)
    store = runtime.runtime_store_from_environment()
    corpus_pack = runtime.load_registered_corpus()
    rows = runtime.role_slice(
        corpus_pack,
        "heldout",
        args.start_index,
        args.end_index,
    )
    backend = runtime.OfficialBackend(require_gpu=True)
    environment = backend.prepare()
    backend.verify_tokenization(rows)
    lenses = {}
    receipts = {}
    for lens_id, component in (
        ("A600", args.a600),
        ("B600", args.b600),
        ("M1200", args.m1200),
    ):
        receipt_bytes = store.download_absolute(component["receipt_blob"])
        if s2.sha256_bytes(receipt_bytes) != component["receipt_sha256"]:
            raise runtime.S2RuntimeError(f"{lens_id} receipt SHA-256 mismatch")
        receipt = json.loads(receipt_bytes)
        path = directory / f"{lens_id}.pt"
        _download_lens(
            store,
            receipt["lens"]["blob"],
            receipt["lens"]["sha256"],
            path,
        )
        lens = backend.load_lens(path)
        expected = 1200 if lens_id == "M1200" else 600
        if int(lens.n_prompts) != expected:
            raise runtime.S2RuntimeError(f"{lens_id} n_prompts mismatch")
        runtime.validate_jacobians(backend.torch, lens.jacobians)
        lenses[lens_id] = lens
        receipts[lens_id] = component
    metric_rows = []
    backend.start_memory()
    started = time.monotonic()
    for source_row in rows:
        outputs = {}
        for lens_id, lens in lenses.items():
            lens_logits, model_logits, input_ids = lens.apply(
                backend.lens_model,
                source_row["raw_text"],
                layers=list(s2.SOURCE_LAYERS),
                positions=[-1],
                max_seq_len=s2.MAX_SEQ_LEN,
                use_jacobian=True,
            )
            if int(input_ids.shape[-1]) != s2.MAX_SEQ_LEN:
                raise runtime.S2RuntimeError("heldout apply input length drifted")
            if not bool(backend.torch.isfinite(model_logits).all()):
                raise runtime.S2RuntimeError("heldout model logits are non-finite")
            outputs[lens_id] = lens_logits
        for pair, left_id, right_id in (
            ("A600_vs_B600", "A600", "B600"),
            ("A600_vs_M1200", "A600", "M1200"),
            ("B600_vs_M1200", "B600", "M1200"),
        ):
            for layer in s2.SOURCE_LAYERS:
                metrics = runtime.logit_pair_metrics(
                    backend.torch,
                    outputs[left_id][layer],
                    outputs[right_id][layer],
                )
                metric_rows.append(
                    {
                        "finite": True,
                        "layer": layer,
                        "pair": pair,
                        "role_index": source_row["role_index"],
                        "sequence_id": source_row["row_id"],
                        **metrics,
                    }
                )
    seconds = time.monotonic() - started
    memory = backend.finish_memory()
    metrics_path = directory / "heldout_metrics.jsonl"
    runtime.write_jsonl(metrics_path, metric_rows)
    receipt = {
        "end_index": args.end_index,
        "environment": environment,
        "lens_receipts": receipts,
        "memory": memory,
        "metrics": {
            "blob": store.name(
                f"{args.subprefix.strip('/')}/heldout_metrics.jsonl"
            ),
            "bytes": metrics_path.stat().st_size,
            "sha256": s2.sha256_file(metrics_path),
        },
        "metric_row_count": len(metric_rows),
        "seconds": seconds,
        "sequence_count": len(rows),
        "sequence_ids": [row["row_id"] for row in rows],
        "start_index": args.start_index,
        "status": "success",
    }
    receipt_path = directory / "heldout_receipt.json"
    runtime.write_json(receipt_path, receipt)
    finalize_pack(
        store,
        stage="S2-heldout-apply",
        directory=directory,
        files=[metrics_path, receipt_path],
        subprefix=args.subprefix,
        complete=True,
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    smoke = subparsers.add_parser("smoke")
    smoke.add_argument("--dim-batch", type=int, required=True)
    smoke.add_argument("--subprefix", required=True)
    smoke.set_defaults(handler=run_smoke)

    select = subparsers.add_parser("smoke-select")
    select.add_argument("--subprefix", default="selection")
    select.set_defaults(handler=run_smoke_select)

    fit = subparsers.add_parser("fit-shard")
    fit.add_argument("--role", required=True)
    fit.add_argument("--start-index", type=int, required=True)
    fit.add_argument("--end-index", type=int, required=True)
    fit.add_argument("--shard-id", required=True)
    fit.add_argument("--dim-batch", type=int, required=True)
    fit.add_argument("--subprefix", required=True)
    fit.add_argument("--resume-checkpoint-blob", default="")
    fit.add_argument("--resume-checkpoint-sha256", default="")
    fit.add_argument("--resume-checkpoint-manifest-blob", default="")
    fit.add_argument("--resume-checkpoint-manifest-sha256", default="")
    fit.set_defaults(handler=run_fit_shard)

    merge = subparsers.add_parser("merge")
    merge.add_argument("--lens-id", required=True)
    merge.add_argument("--expected-n-prompts", type=int, required=True)
    merge.add_argument("--component", type=parse_component, action="append", required=True)
    merge.add_argument("--subprefix", required=True)
    merge.set_defaults(handler=run_merge)

    heldout = subparsers.add_parser("heldout-shard")
    heldout.add_argument("--start-index", type=int, required=True)
    heldout.add_argument("--end-index", type=int, required=True)
    heldout.add_argument("--a600", type=parse_component, required=True)
    heldout.add_argument("--b600", type=parse_component, required=True)
    heldout.add_argument("--m1200", type=parse_component, required=True)
    heldout.add_argument("--subprefix", required=True)
    heldout.set_defaults(handler=run_heldout_shard)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
