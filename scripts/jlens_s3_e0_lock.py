#!/usr/bin/env python3
"""Create and independently read back the one formal S3-E0 lock."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = PROJECT_ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import jlens_s2_protocol as s2  # noqa: E402
import jlens_s3_e0_runtime as e0  # noqa: E402


BENCHMARKS = {
    "causal_swap": {
        "bytes": 26567,
        "item_count": 90,
        "sha256": "a0edd27ca23f7b4d0fbe90448c2ddcc7457a3d812121bf024ed12a032ff86796",
    },
    "multihop": {
        "bytes": 21869,
        "item_count": 93,
        "sha256": "50b7e4c9255291c0ca2a8e94615be9f44531fa57bb1a844e4f9616056d987416",
    },
    "order_ops": {
        "bytes": 9589,
        "item_count": 55,
        "sha256": "b203206d16ff628152cc86f3838604e06cb54776f3e14fa1c34f150db8bc7560",
    },
}


def blob_client() -> Any:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    account = os.environ["JSPACE_BLOB_ACCOUNT"]
    credential = DefaultAzureCredential(
        managed_identity_client_id=os.getenv("AZURE_CLIENT_ID") or None
    )
    service = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=credential,
    )
    return service.get_container_client(os.environ["JSPACE_BLOB_CONTAINER"])


def download_checked(client: Any, blob: str, sha256: str) -> tuple[dict, bytes]:
    payload = client.download_blob(blob).readall()
    if hashlib.sha256(payload).hexdigest() != sha256:
        raise e0.E0RuntimeError(f"lock input SHA-256 mismatch: {blob}")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise e0.E0RuntimeError(f"lock input is not an object: {blob}")
    return document, payload


def main() -> int:
    client = blob_client()
    s2_manifest, _ = download_checked(
        client,
        os.environ["JSPACE_S2_MANIFEST_BLOB"],
        os.environ["JSPACE_S2_MANIFEST_SHA256"],
    )
    if s2_manifest.get("status") != "S2-V0-SEALED":
        raise e0.E0RuntimeError("S2 manifest is not sealed")
    references = json.loads(os.environ["JSPACE_CANONICAL_SEALS_JSON"])
    if {row["lens_id"] for row in references} != {"A600", "B600", "M1200"}:
        raise e0.E0RuntimeError("canonical seal references are not exact")
    canonical = {}
    for reference in references:
        seal, _ = download_checked(
            client,
            reference["blob"],
            reference["sha256"],
        )
        if seal.get("lens_id") != reference["lens_id"] or seal.get("sealed") is not True:
            raise e0.E0RuntimeError("canonical lens seal identity mismatch")
        canonical[reference["lens_id"]] = {
            "bytes": seal["lens"]["bytes"],
            "seal_sha256": reference["sha256"],
            "sealed": True,
            "sha256": seal["lens"]["sha256"],
        }
    lock = {
        "canonical_lenses": canonical,
        "e0_image_digest": os.environ["JSPACE_E0_IMAGE_DIGEST"],
        "e0_manifest_destination": os.environ["JSPACE_E0_OUTPUT_PREFIX"],
        "e0_output_schema_sha256": s2.sha256_file(
            PROJECT_ROOT / "docs" / "jlens_s3_e0_pack.schema.json"
        ),
        "e0_source_bundle_sha256": os.environ["JSPACE_E0_SOURCE_BUNDLE_SHA256"],
        "expected_item_counts": dict(e0.EXPECTED_ITEM_COUNTS),
        "lens_operations_authorized": 0,
        "model": {
            "id": s2.MODEL_ID,
            "parameter_dtype": s2.MODEL_DTYPE,
            "revision": s2.MODEL_REVISION,
            "tokenizer_revision": s2.MODEL_REVISION,
        },
        "pre_lock_benchmark_model_operations": 0,
        "pre_lock_benchmark_tokenizer_operations": 0,
        "row_order": list(e0.DISTRIBUTION_ORDER),
        "s2_manifest": {
            "blob": os.environ["JSPACE_S2_MANIFEST_BLOB"],
            "sha256": os.environ["JSPACE_S2_MANIFEST_SHA256"],
        },
        "s3_protocol_sha256": s2.S3_PROTOCOL_SHA256,
        "s3_schema_sha256": s2.S3_SCHEMA_SHA256,
        "schema_version": "jlens-s3-e0-lock/v1",
        "vendored_benchmarks": BENCHMARKS,
    }
    e0.validate_e0_lock(lock)
    payload = s2.canonical_json_bytes(lock)
    prefix = os.environ["JSPACE_E0_LOCK_PREFIX"].strip("/")
    blob = f"{prefix}/e0_lock.json"
    client.upload_blob(name=blob, data=payload, overwrite=False)
    observed = client.download_blob(blob).readall()
    if observed != payload:
        raise e0.E0RuntimeError("E0 lock readback mismatch")
    result = {
        "blob": blob,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "status": "S3-E0-LOCK-SEALED",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
