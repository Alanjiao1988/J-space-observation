#!/usr/bin/env python3
"""Execute exactly the frozen lens-free S3 Stage E0."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = PROJECT_ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import jlens_s2_protocol as s2  # noqa: E402
import jlens_s3_e0_runtime as e0  # noqa: E402
import jlens_s3_protocol as s3  # noqa: E402


MODEL_ROOT = Path("/workspace/model")
RESULTS_ROOT = Path(os.getenv("RESULTS_DIR", "/workspace/runtime/results"))
VENDORED = (
    PROJECT_ROOT
    / "third_party"
    / "jacobian-lens"
    / s2.JLENS_COMMIT
)
BENCHMARK_PATHS = {
    "multihop": "data/evaluations/lens-eval-multihop.json",
    "order_ops": "data/evaluations/lens-eval-order-ops.json",
    "causal_swap": "data/experiments/probe-swap.json",
}


class BlobStore:
    def __init__(self, prefix: str) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        account = os.environ["JSPACE_BLOB_ACCOUNT"]
        container = os.environ["JSPACE_BLOB_CONTAINER"]
        credential = DefaultAzureCredential(
            managed_identity_client_id=os.getenv("AZURE_CLIENT_ID") or None
        )
        service = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=credential,
        )
        self.client = service.get_container_client(container)
        self.prefix = prefix.strip("/")

    def name(self, relative: str) -> str:
        clean = relative.strip("/")
        if not clean or ".." in clean.split("/"):
            raise e0.E0RuntimeError("invalid E0 Blob path")
        return f"{self.prefix}/{clean}"

    def download_absolute(self, name: str) -> bytes:
        return self.client.download_blob(name.strip("/")).readall()

    def upload(self, relative: str, payload: bytes) -> dict[str, Any]:
        name = self.name(relative)
        self.client.upload_blob(name=name, data=payload, overwrite=False)
        observed = self.client.download_blob(name).readall()
        if observed != payload:
            raise e0.E0RuntimeError(f"E0 Blob readback mismatch: {name}")
        return {
            "blob": name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }


def canonical_json(value: Any) -> bytes:
    return s2.canonical_json_bytes(value)


def canonical_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return s2.canonical_jsonl_bytes(rows)


def load_lock() -> tuple[dict[str, Any], bytes]:
    prelock_store = BlobStore("e0-precondition-read-only")
    blob = os.environ["JSPACE_E0_LOCK_BLOB"]
    expected = os.environ["JSPACE_E0_LOCK_SHA256"]
    payload = prelock_store.download_absolute(blob)
    if hashlib.sha256(payload).hexdigest() != expected:
        raise e0.E0RuntimeError("E0 lock SHA-256 mismatch")
    lock = json.loads(payload)
    e0.validate_e0_lock(lock)
    e0.verify_locked_local_bytes(PROJECT_ROOT, lock)
    if lock["e0_image_digest"] != os.environ["JSPACE_IMAGE_DIGEST"]:
        raise e0.E0RuntimeError("executing E0 image differs from lock")
    if lock["e0_manifest_destination"] != os.environ["JSPACE_BLOB_PREFIX"]:
        raise e0.E0RuntimeError("E0 output prefix differs from lock")
    return lock, payload


def model_snapshot_identity() -> dict[str, Any]:
    manifest_path = MODEL_ROOT / "MODEL_SNAPSHOT_MANIFEST.json"
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        document.get("model_id") != s2.MODEL_ID
        or document.get("revision") != s2.MODEL_REVISION
        or document.get("complete") is not True
    ):
        raise e0.E0RuntimeError("E0 model snapshot manifest mismatch")
    for row in document["files"]:
        path = MODEL_ROOT / row["path"]
        if path.stat().st_size != row["bytes"] or s2.sha256_file(path) != row["sha256"]:
            raise e0.E0RuntimeError(f"E0 model snapshot drift: {row['path']}")
    return document


def decoded_vocabulary(tokenizer: Any) -> dict[int, str]:
    return {
        token_id: tokenizer.decode(
            [token_id],
            clean_up_tokenization_spaces=False,
            skip_special_tokens=False,
        )
        for token_id in range(len(tokenizer))
    }


def load_official_items() -> dict[str, list[dict[str, Any]]]:
    rows = {}
    for distribution in e0.DISTRIBUTION_ORDER:
        path = VENDORED / BENCHMARK_PATHS[distribution]
        document = s3.load_json(path)
        items = document["items"]
        if len(items) != e0.EXPECTED_ITEM_COUNTS[distribution]:
            raise e0.E0RuntimeError(f"{distribution} item count drifted")
        rows[distribution] = items
    return rows


def artifact_manifest_rows(
    *,
    files: list[tuple[str, bytes]],
    protocol_sha256: str,
    schema_sha256: str,
) -> list[dict[str, Any]]:
    rows = []
    for index, (relative, payload) in enumerate(files, start=1):
        row = {
            "artifact_id": f"E0::{relative}",
            "bytes": len(payload),
            "complete": True,
            "create_only": True,
            "image_digest": os.environ["JSPACE_IMAGE_DIGEST"],
            "opened_at_utc": None,
            "protocol_sha256": protocol_sha256,
            "relative_path": relative,
            "schema_sha256": schema_sha256,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "source_commit": os.environ["JSPACE_CODE_COMMIT"],
            "stage": "E0",
            "written_order": index,
        }
        protocol = s3.load_and_validate_protocol(PROJECT_ROOT)
        s3.validate_output_row(protocol, "artifact_manifest", row)
        rows.append(row)
    return rows


def execute_e0(lock: dict[str, Any]) -> dict[str, Any]:
    protocol = s3.load_and_validate_protocol(PROJECT_ROOT)
    model_snapshot_identity()
    import torch
    import transformers

    tokenizer = transformers.AutoTokenizer.from_pretrained(
        str(MODEL_ROOT),
        local_files_only=True,
        trust_remote_code=False,
    )
    if (
        getattr(tokenizer, "bos_token_id", None) is not None
        and hasattr(tokenizer, "add_bos_token")
    ):
        tokenizer.add_bos_token = True
    if getattr(tokenizer, "add_bos_token", None) is not True:
        raise e0.E0RuntimeError("E0 force_bos=true could not be applied")
    config = transformers.AutoConfig.from_pretrained(
        str(MODEL_ROOT),
        local_files_only=True,
        trust_remote_code=False,
    )
    config.use_cache = False
    model = transformers.AutoModelForCausalLM.from_pretrained(
        str(MODEL_ROOT),
        config=config,
        dtype=torch.float16,
        local_files_only=True,
        trust_remote_code=False,
    )
    model.to(torch.device("cuda:0"))
    model.eval()
    floating = {
        str(parameter.dtype)
        for parameter in model.parameters()
        if parameter.is_floating_point()
    }
    if floating != {"torch.float16"}:
        raise e0.E0RuntimeError(f"E0 model dtype drift: {floating}")

    vocabulary = decoded_vocabulary(tokenizer)
    vocabulary_decode_count = len(vocabulary)
    raw_items = load_official_items()
    item_rows: list[dict[str, Any]] = []
    surface_rows: list[dict[str, Any]] = []
    tokenizer_calls = 0
    model_calls = 0
    started = time.monotonic()
    for distribution in e0.DISTRIBUTION_ORDER:
        for item in raw_items[distribution]:
            surfaces = e0.build_surface_rows(
                distribution=distribution,
                item=item,
                decoded_vocabulary=vocabulary,
            )
            encoded = tokenizer(
                str(item["prompt"]),
                add_special_tokens=True,
                return_attention_mask=False,
                return_tensors="pt",
                truncation=False,
            )
            tokenizer_calls += 1
            input_ids = encoded.input_ids.to(torch.device("cuda:0"))
            decoded_spans = [
                tokenizer.decode(
                    [int(token_id)],
                    clean_up_tokenization_spaces=False,
                    skip_special_tokens=False,
                )
                for token_id in input_ids[0].tolist()
            ]
            with torch.inference_mode():
                logits = model(input_ids=input_ids, use_cache=False).logits[0, -1]
            model_calls += 1
            clean_top1 = int(torch.argmax(logits).item())
            row = e0.build_item_row(
                distribution=distribution,
                item=item,
                input_token_ids=[int(token_id) for token_id in input_ids[0].tolist()],
                decoded_position_spans=decoded_spans,
                surface_rows=surfaces,
                clean_top1_token_id=clean_top1,
                model_id=s2.MODEL_ID,
                model_revision=s2.MODEL_REVISION,
                tokenizer_revision=s2.MODEL_REVISION,
                parameter_dtype=s2.MODEL_DTYPE,
            )
            item_rows.append(row)
            surface_rows.extend(surfaces)
    if tokenizer_calls != 238 or model_calls != 238:
        raise e0.E0RuntimeError("E0 exact tokenizer/model call count failed")
    e0.assign_sealed_splits(raw_items=raw_items, item_rows=item_rows)
    counts = e0.e0_counts(item_rows)
    for row in item_rows:
        s3.validate_output_row(protocol, "e0_item", row)
    for row in surface_rows:
        s3.validate_output_row(protocol, "e0_surface", row)

    item_bytes = canonical_jsonl(item_rows)
    surface_bytes = canonical_jsonl(surface_rows)
    exclusion_counts = {
        "multi_token": sum(row["multi_token_removed_count"] for row in item_rows),
        "no_control_position": sum(
            "no_control_position" in row["exclusion_reasons"] for row in item_rows
        ),
        "over_length": sum(
            "over_length" in row["exclusion_reasons"] for row in item_rows
        ),
        "prompt_surface": sum(
            row["prompt_surface_removed_count"] for row in item_rows
        ),
        "target_overlap": sum(
            row["target_overlap_removed_count"] for row in item_rows
        ),
    }
    eligibility = {
        "artifact_manifest_destination": os.environ["JSPACE_BLOB_PREFIX"],
        "benchmark_item_tokenizer_calls": tokenizer_calls,
        "benchmark_model_forward_calls": model_calls,
        "distribution_counts": counts["distribution_counts"],
        "e0_item_sha256": hashlib.sha256(item_bytes).hexdigest(),
        "e0_surface_sha256": hashlib.sha256(surface_bytes).hexdigest(),
        "e1_outputs": 0,
        "e2_outputs": 0,
        "exclusion_counts": exclusion_counts,
        "floor_booleans": counts["floor_booleans"],
        "lens_imports": 0,
        "lens_operations": 0,
        "lock_sha256": os.environ["JSPACE_E0_LOCK_SHA256"],
        "manifest_written_last": True,
        "pre_lock_benchmark_model_operations": 0,
        "pre_lock_benchmark_tokenizer_operations": 0,
        "terminal_state": counts["terminal_state"],
        "vocabulary_token_decodes": vocabulary_decode_count,
    }
    eligibility_bytes = canonical_json(eligibility)
    schema = s3.load_json(PROJECT_ROOT / "docs" / "jlens_s3_e0_pack.schema.json")
    s3.validate_json_schema(
        {
            "artifact_files": [
                {
                    "bytes": len(item_bytes),
                    "create_only": True,
                    "relative_path": "e0_item.jsonl",
                    "sha256": hashlib.sha256(item_bytes).hexdigest(),
                    "written_order": 1,
                },
                {
                    "bytes": len(surface_bytes),
                    "create_only": True,
                    "relative_path": "e0_surface.jsonl",
                    "sha256": hashlib.sha256(surface_bytes).hexdigest(),
                    "written_order": 2,
                },
                {
                    "bytes": len(eligibility_bytes),
                    "create_only": True,
                    "relative_path": "eligibility_split_manifest.json",
                    "sha256": hashlib.sha256(eligibility_bytes).hexdigest(),
                    "written_order": 3,
                },
            ],
            "complete": True,
            "e0_items": item_rows,
            "e0_surfaces": surface_rows,
            "eligibility_split_manifest": eligibility,
            "s2_manifest_sha256": lock["s2_manifest"]["sha256"],
            "s3_protocol_sha256": s2.S3_PROTOCOL_SHA256,
            "s3_schema_sha256": s2.S3_SCHEMA_SHA256,
            "schema_version": "jlens-s3-e0-pack/v1",
        },
        schema,
    )
    elapsed = time.monotonic() - started
    return {
        "eligibility": eligibility,
        "eligibility_bytes": eligibility_bytes,
        "elapsed_seconds": elapsed,
        "item_bytes": item_bytes,
        "item_rows": item_rows,
        "surface_bytes": surface_bytes,
        "surface_rows": surface_rows,
    }


def publish_complete(result: dict[str, Any]) -> dict[str, Any]:
    store = BlobStore(os.environ["JSPACE_BLOB_PREFIX"])
    protocol_sha = s2.sha256_file(
        PROJECT_ROOT / "docs" / "jlens_s3_validity_protocol.json"
    )
    schema_sha = s2.sha256_file(
        PROJECT_ROOT / "docs" / "jlens_s3_e0_pack.schema.json"
    )
    files = [
        ("e0_item.jsonl", result["item_bytes"]),
        ("e0_surface.jsonl", result["surface_bytes"]),
        ("eligibility_split_manifest.json", result["eligibility_bytes"]),
    ]
    manifest_rows = artifact_manifest_rows(
        files=files,
        protocol_sha256=protocol_sha,
        schema_sha256=schema_sha,
    )
    manifest_bytes = canonical_jsonl(manifest_rows)
    uploaded = []
    for relative, payload in files:
        uploaded.append(store.upload(relative, payload))
    uploaded.append(store.upload("artifact_manifest.jsonl", manifest_bytes))
    return {
        "artifact_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "elapsed_seconds": result["elapsed_seconds"],
        "item_count": len(result["item_rows"]),
        "status": "S3-E0-SEALED",
        "surface_count": len(result["surface_rows"]),
        "terminal_state": result["eligibility"]["terminal_state"],
        "uploaded": uploaded,
    }


def publish_partial(error: BaseException) -> None:
    partial_prefix = os.environ["JSPACE_E0_PARTIAL_PREFIX"]
    store = BlobStore(partial_prefix)
    receipt = {
        "classification": None,
        "error": f"{type(error).__name__}: {error}"[:4000],
        "lens_operations": 0,
        "status": "BLOCKED_ON_JLENS_S3_E0_EXECUTION_INTEGRITY",
        "traceback": traceback.format_exc(limit=30)[-12000:],
    }
    store.upload("partial_receipt.json", canonical_json(receipt))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        lock, _lock_bytes = load_lock()
        result = execute_e0(lock)
        published = publish_complete(result)
        print(json.dumps(published, sort_keys=True, separators=(",", ":")), flush=True)
        return 0
    except Exception as exc:
        publish_partial(exc)
        print(
            json.dumps(
                {
                    "classification": None,
                    "error": f"{type(exc).__name__}: {exc}"[:4000],
                    "status": "BLOCKED_ON_JLENS_S3_E0_EXECUTION_INTEGRITY",
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
