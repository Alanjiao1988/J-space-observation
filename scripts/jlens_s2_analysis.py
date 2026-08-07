#!/usr/bin/env python3
"""Analyze and independently seal full-layer S2 artifacts."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import statistics
import sys
from collections import defaultdict
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


WORK_ROOT = Path("/workspace/runtime/results")
CANONICAL_LENS_IDS = (
    "A64",
    "A128",
    "A256",
    "A600",
    "B64",
    "B128",
    "B256",
    "B600",
    "M1200",
)


def component(value: str) -> dict[str, str]:
    parts = value.split("|")
    if len(parts) != 2 or any(not part for part in parts):
        raise argparse.ArgumentTypeError("component must be BLOB|SHA256")
    return {"blob": parts[0], "sha256": parts[1]}


def checkpoint(value: str) -> dict[str, Any]:
    parts = value.split("|")
    if len(parts) != 5:
        raise argparse.ArgumentTypeError(
            "checkpoint must be N|A_BLOB|A_SHA256|B_BLOB|B_SHA256"
        )
    return {
        "a": {"blob": parts[1], "sha256": parts[2]},
        "b": {"blob": parts[3], "sha256": parts[4]},
        "n": int(parts[0]),
    }


def lens_component(value: str) -> dict[str, str]:
    parts = value.split("|")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("lens must be ID|RECEIPT_BLOB|SHA256")
    return {"id": parts[0], "blob": parts[1], "sha256": parts[2]}


def load_receipt(
    store: runtime.BlobStore,
    reference: dict[str, str],
) -> tuple[dict[str, Any], bytes]:
    payload = store.download_absolute(reference["blob"])
    if s2.sha256_bytes(payload) != reference["sha256"]:
        raise runtime.S2RuntimeError(
            f"receipt SHA-256 mismatch: {reference['blob']}"
        )
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise runtime.S2RuntimeError("receipt is not an object")
    return document, payload


def receipt_transport(
    store: runtime.BlobStore,
    reference: dict[str, str],
    payload: bytes,
    document: dict[str, Any],
    *,
    expected_source_commit: str | None = None,
    expected_image_digest: str | None = None,
) -> dict[str, Any]:
    related = [document["lens"]] if isinstance(document.get("lens"), dict) else []
    return runtime.validate_receipt_transport(
        store,
        receipt_blob=reference["blob"],
        receipt_sha256=reference["sha256"],
        receipt_bytes=payload,
        related_files=related,
        expected_source_commit=expected_source_commit,
        expected_image_digest=expected_image_digest,
    )


def load_lens(
    store: runtime.BlobStore,
    receipt: dict[str, Any],
    path: Path,
    jlens_module: Any,
) -> Any:
    lens_row = receipt["lens"]
    downloaded = store.download_absolute_to(lens_row["blob"], path)
    if (
        downloaded["sha256"] != lens_row["sha256"]
        or downloaded["bytes"] != lens_row["bytes"]
    ):
        raise runtime.S2RuntimeError("lens bytes differ from receipt")
    return jlens_module.JacobianLens.load(str(path))


def output_pack(
    store: runtime.BlobStore,
    *,
    stage: str,
    directory: Path,
    files: list[Path],
    subprefix: str,
) -> None:
    manifest = runtime.pack_manifest(
        stage=stage,
        files=files,
        root=directory,
        complete=True,
    )
    manifest_path = directory / "artifact_manifest.json"
    runtime.write_json(manifest_path, manifest)
    runtime.upload_pack(
        store,
        root=directory,
        files=[*files, manifest_path],
        subprefix=subprefix,
    )


def run_convergence(args: argparse.Namespace) -> int:
    if sorted(row["n"] for row in args.checkpoint) != list(s2.CHECKPOINTS):
        raise runtime.S2RuntimeError("convergence checkpoints are not exact")
    directory = WORK_ROOT / "convergence"
    directory.mkdir(parents=True, exist_ok=True)
    store = runtime.runtime_store_from_environment()
    torch_module = importlib.import_module("torch")
    jlens_module = importlib.import_module("jlens")
    per_layer = []
    summaries = []
    for row in sorted(args.checkpoint, key=lambda item: item["n"]):
        n = row["n"]
        a_receipt, a_payload = load_receipt(store, row["a"])
        b_receipt, b_payload = load_receipt(store, row["b"])
        a_provenance = receipt_transport(
            store, row["a"], a_payload, a_receipt
        )
        b_provenance = receipt_transport(
            store, row["b"], b_payload, b_receipt
        )
        a = load_lens(
            store, a_receipt, directory / f"A{n}.pt", jlens_module
        )
        b = load_lens(
            store, b_receipt, directory / f"B{n}.pt", jlens_module
        )
        if int(a.n_prompts) != n or int(b.n_prompts) != n:
            raise runtime.S2RuntimeError("convergence lens prompt count mismatch")
        comparison = runtime.compare_tensor_matrices(
            torch_module,
            a.jacobians,
            b.jacobians,
        )
        distances = []
        cosines = []
        for layer in s2.SOURCE_LAYERS:
            metrics = comparison["layers"][str(layer)]
            distances.append(metrics["relative_frobenius"])
            cosines.append(metrics["cosine"])
            per_layer.append(
                {
                    "checkpoint": n,
                    "finite": True,
                    "layer": layer,
                    **metrics,
                }
            )
        summaries.append(
            {
                "checkpoint": n,
                "finite_rate": 1.0,
                "maximum_relative_frobenius": max(distances),
                "mean_cosine": statistics.fmean(cosines),
                "median_relative_frobenius": statistics.median(distances),
                "minimum_cosine": min(cosines),
                "transport_provenance": {
                    "A": a_provenance,
                    "B": b_provenance,
                },
            }
        )
    scaling = s2.fit_scaling_law(
        [row["checkpoint"] for row in summaries],
        [row["maximum_relative_frobenius"] for row in summaries],
    )
    prior = {
        str(n): s2.prior_scaling_prediction(n) for n in s2.CHECKPOINTS
    }
    document = {
        "across_layer_summary": summaries,
        "non_gating": True,
        "per_layer_row_count": len(per_layer),
        "prior_c_1_7_prediction": prior,
        "scaling_primary": "maximum layer relative Frobenius at each checkpoint",
        "scaling_fit": scaling,
    }
    per_layer_path = directory / "convergence_per_layer.jsonl"
    summary_path = directory / "convergence_summary.json"
    runtime.write_jsonl(per_layer_path, per_layer)
    runtime.write_json(summary_path, document)
    document["files"] = {
        "per_layer": {
            "blob": store.name(
                f"{args.subprefix.strip('/')}/convergence_per_layer.jsonl"
            ),
            "bytes": per_layer_path.stat().st_size,
            "sha256": s2.sha256_file(per_layer_path),
        }
    }
    runtime.write_json(summary_path, document)
    output_pack(
        store,
        stage="S2-convergence-analysis",
        directory=directory,
        files=[per_layer_path, summary_path],
        subprefix=args.subprefix,
    )
    print(json.dumps(document, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


def run_heldout_aggregate(args: argparse.Namespace) -> int:
    directory = WORK_ROOT / "heldout-aggregate"
    directory.mkdir(parents=True, exist_ok=True)
    store = runtime.runtime_store_from_environment()
    sequence_ids = []
    metric_rows = []
    components = []
    for index, reference in enumerate(args.component, start=1):
        receipt, receipt_payload = load_receipt(store, reference)
        if receipt.get("status") != "success":
            raise runtime.S2RuntimeError("heldout shard did not succeed")
        provenance = receipt_transport(
            store, reference, receipt_payload, receipt
        )
        ids = list(receipt["sequence_ids"])
        if set(sequence_ids) & set(ids):
            raise runtime.S2RuntimeError("heldout shard sequence overlap")
        sequence_ids.extend(ids)
        metric_ref = receipt["metrics"]
        payload = store.download_absolute(metric_ref["blob"])
        if (
            len(payload) != metric_ref["bytes"]
            or s2.sha256_bytes(payload) != metric_ref["sha256"]
        ):
            raise runtime.S2RuntimeError("heldout metric file identity mismatch")
        rows = [
            json.loads(line)
            for line in payload.decode("utf-8").splitlines()
            if line
        ]
        if len(rows) != receipt["metric_row_count"]:
            raise runtime.S2RuntimeError("heldout metric row count mismatch")
        receipt_ids = set(ids)
        if (
            any(row.get("sequence_id") not in receipt_ids for row in rows)
            or {
                row["sequence_id"] for row in rows
            }
            != receipt_ids
        ):
            raise runtime.S2RuntimeError(
                "heldout metric rows are not bound to their shard sequences"
            )
        metric_rows.extend(rows)
        components.append(
            {
                "index": index,
                "receipt_blob": reference["blob"],
                "receipt_sha256": reference["sha256"],
                "sequence_count": len(ids),
                "transport_provenance": provenance,
            }
        )
    corpus_pack = runtime.load_registered_corpus()
    expected = [row["row_id"] for row in corpus_pack["by_role"]["heldout"]]
    if sorted(sequence_ids) != sorted(expected) or len(sequence_ids) != 200:
        raise runtime.S2RuntimeError("heldout shards do not cover exact 200 rows")
    metric_validation = runtime.validate_heldout_metric_rows(
        metric_rows,
        expected,
    )
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in metric_rows:
        if row.get("finite") is not True:
            raise runtime.S2RuntimeError("heldout metric row is non-finite")
        grouped[(row["pair"], int(row["layer"]))].append(row)
    summary_rows = []
    for (pair, layer), rows in sorted(grouped.items()):
        if len(rows) != 200:
            raise runtime.S2RuntimeError("heldout pair/layer coverage mismatch")
        summary_rows.append(
            {
                "finite_rate": 1.0,
                "layer": layer,
                "logit_cosine_mean": statistics.fmean(
                    row["logit_cosine"] for row in rows
                ),
                "pair": pair,
                "rank_correlation_mean": statistics.fmean(
                    row["rank_correlation"] for row in rows
                ),
                "top10_overlap_mean": statistics.fmean(
                    row["top10_overlap"] for row in rows
                ),
                "top50_overlap_mean": statistics.fmean(
                    row["top50_overlap"] for row in rows
                ),
            }
        )
    summary_path = directory / "heldout_summary.json"
    rows_path = directory / "heldout_summary_rows.jsonl"
    runtime.write_jsonl(rows_path, summary_rows)
    document = {
        "components": components,
        "diagnostic_only": True,
        "metric_row_count": len(metric_rows),
        "metric_key_validation": metric_validation,
        "sequence_count": 200,
        "sequence_ids_sha256": s2.sha256_bytes(
            s2.canonical_jsonl_bytes(
                {"sequence_id": sequence_id} for sequence_id in expected
            )
        ),
        "summary_row_count": len(summary_rows),
    }
    runtime.write_json(summary_path, document)
    document["files"] = {
        "rows": {
            "blob": store.name(
                f"{args.subprefix.strip('/')}/heldout_summary_rows.jsonl"
            ),
            "bytes": rows_path.stat().st_size,
            "sha256": s2.sha256_file(rows_path),
        }
    }
    runtime.write_json(summary_path, document)
    output_pack(
        store,
        stage="S2-heldout-aggregate",
        directory=directory,
        files=[rows_path, summary_path],
        subprefix=args.subprefix,
    )
    print(json.dumps(document, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


def expected_lens_sequences(
    corpus_pack: dict[str, Any],
    lens_id: str,
) -> list[str]:
    if lens_id == "M1200":
        return [
            row["row_id"]
            for role in ("A", "B")
            for row in corpus_pack["by_role"][role]
        ]
    role = lens_id[0]
    n = int(lens_id[1:])
    return [row["row_id"] for row in corpus_pack["by_role"][role][:n]]


def run_verify(args: argparse.Namespace) -> int:
    if {row["id"] for row in args.lens} != set(CANONICAL_LENS_IDS):
        raise runtime.S2RuntimeError("verification lens set is not exact")
    directory = WORK_ROOT / "s2-verification"
    directory.mkdir(parents=True, exist_ok=True)
    store = runtime.runtime_store_from_environment()
    torch_module = importlib.import_module("torch")
    jlens_module = importlib.import_module("jlens")
    corpus_pack = runtime.load_registered_corpus()
    if s2.sha256_file(
        runtime.CORPUS_ROOT / "corpus_manifest.json"
    ) != args.corpus_manifest_sha256:
        raise runtime.S2RuntimeError("corpus manifest SHA-256 mismatch")
    verified_lenses = {}
    loaded = {}
    receipts = {}
    for reference in args.lens:
        lens_id = reference["id"]
        receipt, payload = load_receipt(
            store,
            {"blob": reference["blob"], "sha256": reference["sha256"]},
        )
        transport = receipt_transport(
            store,
            {"blob": reference["blob"], "sha256": reference["sha256"]},
            payload,
            receipt,
            expected_source_commit=args.analysis_source_commit,
            expected_image_digest=args.analysis_image_digest,
        )
        expected_ids = expected_lens_sequences(corpus_pack, lens_id)
        if receipt["sequence_ids"] != expected_ids:
            raise runtime.S2RuntimeError(f"{lens_id} sequence identities mismatch")
        expected_n = 1200 if lens_id == "M1200" else int(lens_id[1:])
        metadata = receipt["metadata"]
        s2.validate_lens_identity(
            {
                "d_model": metadata["d_model"],
                "finite": metadata["finite"],
                "n_prompts": metadata["n_prompts"],
                "save_load_max_abs": metadata["save_load_max_abs"],
                "source_layers": metadata["source_layers"],
                "target_layer": metadata["target_layer"],
            },
            expected_n_prompts=expected_n,
        )
        merge = receipt["merge"]["independent_weighted_recomputation"]
        if (
            merge["max_abs"] > s2.MERGE_MAX_ABS_TOLERANCE
            or merge["max_relative_frobenius"]
            > s2.MERGE_RELATIVE_FROBENIUS_TOLERANCE
        ):
            raise runtime.S2RuntimeError(f"{lens_id} merge gate failed")
        path = directory / f"{lens_id}.pt"
        lens = load_lens(store, receipt, path, jlens_module)
        runtime.validate_jacobians(torch_module, lens.jacobians)
        if int(lens.n_prompts) != expected_n:
            raise runtime.S2RuntimeError(f"{lens_id} loaded prompt count mismatch")
        loaded[lens_id] = lens
        receipts[lens_id] = receipt
        verified_lenses[lens_id] = {
            "lens": receipt["lens"],
            "manifest_blob": reference["blob"],
            "manifest_bytes": len(payload),
            "manifest_sha256": reference["sha256"],
            "metadata": metadata,
            "sequence_ids_sha256": receipt["sequence_ids_sha256"],
            "transport_provenance": transport,
        }
    recomputed_m = runtime.independent_weighted_mean(
        torch_module,
        [loaded["A600"], loaded["B600"]],
    )
    m_check = runtime.compare_tensor_matrices(
        torch_module,
        recomputed_m,
        loaded["M1200"].jacobians,
    )
    if (
        m_check["max_abs"] > s2.MERGE_MAX_ABS_TOLERANCE
        or m_check["max_relative_frobenius"]
        > s2.MERGE_RELATIVE_FROBENIUS_TOLERANCE
    ):
        raise runtime.S2RuntimeError("independent M1200 recomputation failed")

    shard_receipts = []
    shard_documents = {}
    shard_references = {}
    for reference in args.shard:
        receipt, shard_payload = load_receipt(store, reference)
        receipt_transport(
            store,
            reference,
            shard_payload,
            receipt,
            expected_source_commit=args.fit_source_commit,
            expected_image_digest=args.fit_image_digest,
        )
        shard_receipts.append(receipt)
        shard_id = receipt["shard_id"]
        if shard_id in shard_documents:
            raise runtime.S2RuntimeError("duplicate successful shard receipt")
        shard_documents[shard_id] = receipt
        shard_references[shard_id] = {
            "blob": reference["blob"],
            "sha256": reference["sha256"],
        }
    expected_a = [row["row_id"] for row in corpus_pack["by_role"]["A"]]
    expected_b = [row["row_id"] for row in corpus_pack["by_role"]["B"]]
    accounting = {}
    for role, expected in (("A", expected_a), ("B", expected_b)):
        attempts = [
            {
                "completed_sequence_ids": receipt["completed_sequence_ids"],
                "status": receipt["status"],
            }
            for receipt in shard_receipts
            if receipt["role"] == role
        ]
        accounting[role] = s2.account_successful_sequences(expected, attempts)

    attempt_manifest_bytes = store.download_absolute(args.attempt_manifest_blob)
    if s2.sha256_bytes(attempt_manifest_bytes) != args.attempt_manifest_sha256:
        raise runtime.S2RuntimeError("production attempt manifest SHA-256 mismatch")
    attempt_manifest = json.loads(attempt_manifest_bytes)
    production_plan_path = PROJECT_ROOT / "docs" / "jlens_s2_production_plan.json"
    production_plan = s2.load_json(production_plan_path)
    attempt_validation = runtime.validate_production_attempt_manifest(
        store,
        attempt_manifest,
        production_plan=production_plan,
        success_receipts=shard_references,
        success_documents=shard_documents,
        expected_fit_source_commit=args.fit_source_commit,
        expected_fit_image_digest=args.fit_image_digest,
        production_plan_sha256=s2.sha256_file(production_plan_path),
    )

    convergence, convergence_payload = load_receipt(store, args.convergence)
    heldout, heldout_payload = load_receipt(store, args.heldout)
    smoke, smoke_payload = load_receipt(store, args.smoke)
    convergence_transport = receipt_transport(
        store,
        args.convergence,
        convergence_payload,
        convergence,
        expected_source_commit=args.analysis_source_commit,
        expected_image_digest=args.analysis_image_digest,
    )
    heldout_transport = receipt_transport(
        store,
        args.heldout,
        heldout_payload,
        heldout,
        expected_source_commit=args.analysis_source_commit,
        expected_image_digest=args.analysis_image_digest,
    )
    smoke_transport = receipt_transport(
        store,
        args.smoke,
        smoke_payload,
        smoke,
        expected_source_commit=args.fit_source_commit,
        expected_image_digest=args.fit_image_digest,
    )
    if smoke.get("status") != "selected" or not smoke.get("selected_dim_batch"):
        raise runtime.S2RuntimeError("smoke selection is not sealed")
    if heldout.get("sequence_count") != 200:
        raise runtime.S2RuntimeError("heldout aggregate does not cover 200 rows")
    if len(convergence.get("across_layer_summary", [])) != 4:
        raise runtime.S2RuntimeError("convergence summary is incomplete")

    seals = []
    seal_paths = []
    for lens_id in ("A600", "B600", "M1200"):
        seal = {
            "lens": verified_lenses[lens_id]["lens"],
            "lens_id": lens_id,
            "manifest_blob": verified_lenses[lens_id]["manifest_blob"],
            "manifest_sha256": verified_lenses[lens_id]["manifest_sha256"],
            "sealed": True,
        }
        path = directory / f"{lens_id}_seal.json"
        runtime.write_json(path, seal)
        seals.append(seal)
        seal_paths.append(path)
    receipt = {
        "all_operational_gates_pass": True,
        "benchmark_model_operations_before_seal": 0,
        "benchmark_tokenizer_operations_before_seal": 0,
        "canonical_lenses": verified_lenses,
        "convergence_receipt": args.convergence,
        "corpus_manifest_sha256": args.corpus_manifest_sha256,
        "heldout_receipt": args.heldout,
        "heldout_transport": heldout_transport,
        "m1200_independent_recomputation": m_check,
        "sequence_accounting": accounting,
        "production_attempt_manifest": {
            "blob": args.attempt_manifest_blob,
            "sha256": args.attempt_manifest_sha256,
            "validation": attempt_validation,
        },
        "shard_attempt_count": len(shard_receipts),
        "smoke_selection_receipt": args.smoke,
        "smoke_transport": smoke_transport,
        "convergence_transport": convergence_transport,
        "status": "S2-V0-SEALED",
    }
    receipt_path = directory / "s2_verification_receipt.json"
    runtime.write_json(receipt_path, receipt)
    artifact_files = [
        {
            "bytes": path.stat().st_size,
            "create_only": True,
            "media_type": "application/json",
            "readback_verified": True,
            "relative_path": path.name,
            "sha256": s2.sha256_file(path),
            "written_order": index,
        }
        for index, path in enumerate(
            sorted([*seal_paths, receipt_path], key=lambda item: item.name),
            start=1,
        )
    ]
    lens_manifest_rows = []
    for lens_id in CANONICAL_LENS_IDS:
        row = receipts[lens_id]
        metadata = row["metadata"]
        merge = row["merge"]["independent_weighted_recomputation"]
        lens_manifest_rows.append(
            {
                "blob": row["lens"]["blob"],
                "bytes": row["lens"]["bytes"],
                "d_model": metadata["d_model"],
                "finite": metadata["finite"],
                "lens_id": lens_id,
                "merge_max_abs": merge["max_abs"],
                "merge_relative_frobenius": merge[
                    "max_relative_frobenius"
                ],
                "n_prompts": metadata["n_prompts"],
                "save_load_max_abs": metadata["save_load_max_abs"],
                "sha256": row["lens"]["sha256"],
                "source_layers": metadata["source_layers"],
                "target_layer": metadata["target_layer"],
            }
        )
    shard_pack_rows = []
    for row in shard_receipts:
        snapshots = row.get("checkpoint_snapshots") or []
        checkpoint_sha = (
            snapshots[-1]["checkpoint"]["sha256"] if snapshots else None
        )
        shard_pack_rows.append(
            {
                "attempt_id": row["attempt_id"],
                "checkpoint_sha256": checkpoint_sha,
                "completed_sequence_ids": row["completed_sequence_ids"],
                "dim_batch": row["dim_batch"],
                "gpu_name": row["environment"]["gpu_name"],
                "image_digest": row["image_digest"],
                "peak_allocated_bytes": row["memory"][
                    "gpu_peak_allocated_bytes"
                ],
                "peak_reserved_bytes": row["memory"][
                    "gpu_peak_reserved_bytes"
                ],
                "resumed": row["resumed"],
                "seconds": row["fit_seconds"],
                "shard_id": row["shard_id"],
                "status": row["status"],
            }
        )
    smoke_pack_rows = []
    for dim_batch in s2.DIM_BATCH_CANDIDATES:
        row = smoke["attempts"][str(dim_batch)]
        smoke_pack_rows.append(
            {
                "attempt_id": row["attempt_id"],
                "comparison_to_dim1": row["comparison_to_dim1"],
                "dim_batch": dim_batch,
                "finite_float32": row["finite_float32"],
                "gpu_name": row["environment"]["gpu_name"],
                "matrix_shapes_valid": row["matrix_shapes_valid"],
                "peak_allocated_bytes": max(
                    item["memory"]["gpu_peak_allocated_bytes"]
                    for item in row["rows"]
                ),
                "peak_reserved_bytes": max(
                    item["memory"]["gpu_peak_reserved_bytes"]
                    for item in row["rows"]
                ),
                "peak_reserved_ratio": row["peak_reserved_ratio"],
                "seconds": max(item["seconds"] for item in row["rows"]),
                "source_layers": row["source_layers"],
                "status": row["status"],
                "target_layer": row["target_layer"],
            }
        )
    final_pack = {
        "complete": True,
        "corpus_rows": corpus_pack["rows"],
        "create_only": True,
        "exclusions": [],
        "files": artifact_files,
        "heldout_diagnostics": [],
        "image_digest": os.environ["JSPACE_IMAGE_DIGEST"],
        "lens_manifests": lens_manifest_rows,
        "manifest_written_last": True,
        "protocol_sha256": s2.sha256_file(
            PROJECT_ROOT / "docs" / "jlens_s2_protocol.json"
        ),
        "run_id": os.environ["JSPACE_S2_RUN_ID"],
        "schema_version": "jlens-s2-artifact-pack/v1",
        "shard_receipts": shard_pack_rows,
        "smoke_attempts": smoke_pack_rows,
        "source_commit": os.environ["JSPACE_CODE_COMMIT"],
        "stage": "S2-V0",
        "verification": [
            {
                "A600_sealed": True,
                "B600_sealed": True,
                "M1200_sealed": True,
                "all_operational_gates_pass": True,
                "benchmark_model_operations_before_seal": 0,
                "benchmark_tokenizer_operations_before_seal": 0,
                "receipt_sha256": s2.sha256_file(receipt_path),
            }
        ],
    }
    from jlens_s3_protocol import validate_json_schema

    validate_json_schema(
        final_pack,
        s2.load_json(
            PROJECT_ROOT / "docs" / "jlens_s2_artifacts.schema.json"
        ),
    )
    final_pack_path = directory / "zz_s2_artifact_pack.json"
    runtime.write_json(final_pack_path, final_pack)
    s2_manifest = {
        "canonical_seals": seals,
        "corpus_manifest_sha256": args.corpus_manifest_sha256,
        "image_digest": os.environ["JSPACE_IMAGE_DIGEST"],
        "protocol_sha256": s2.sha256_file(
            PROJECT_ROOT / "docs" / "jlens_s2_protocol.json"
        ),
        "source_commit": os.environ["JSPACE_CODE_COMMIT"],
        "status": "S2-V0-SEALED",
        "artifact_pack_sha256": s2.sha256_file(final_pack_path),
        "verification_receipt_sha256": s2.sha256_file(receipt_path),
    }
    s2_manifest_path = directory / "s2_manifest.json"
    runtime.write_json(s2_manifest_path, s2_manifest)
    output_pack(
        store,
        stage="S2-V0-independent-verification",
        directory=directory,
        files=[
            *seal_paths,
            receipt_path,
            s2_manifest_path,
            final_pack_path,
        ],
        subprefix=args.subprefix,
    )
    result = {
        **s2_manifest,
        "s2_manifest_sha256": s2.sha256_file(s2_manifest_path),
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    convergence = subparsers.add_parser("convergence")
    convergence.add_argument(
        "--checkpoint", type=checkpoint, action="append", required=True
    )
    convergence.add_argument("--subprefix", required=True)
    convergence.set_defaults(handler=run_convergence)

    heldout = subparsers.add_parser("heldout-aggregate")
    heldout.add_argument(
        "--component", type=component, action="append", required=True
    )
    heldout.add_argument("--subprefix", required=True)
    heldout.set_defaults(handler=run_heldout_aggregate)

    verify = subparsers.add_parser("verify-s2")
    verify.add_argument("--lens", type=lens_component, action="append", required=True)
    verify.add_argument("--shard", type=component, action="append", required=True)
    verify.add_argument("--convergence", type=component, required=True)
    verify.add_argument("--heldout", type=component, required=True)
    verify.add_argument("--smoke", type=component, required=True)
    verify.add_argument("--corpus-manifest-sha256", required=True)
    verify.add_argument("--fit-source-commit", required=True)
    verify.add_argument("--fit-image-digest", required=True)
    verify.add_argument("--analysis-source-commit", required=True)
    verify.add_argument("--analysis-image-digest", required=True)
    verify.add_argument("--attempt-manifest-blob", required=True)
    verify.add_argument("--attempt-manifest-sha256", required=True)
    verify.add_argument("--subprefix", required=True)
    verify.set_defaults(handler=run_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
