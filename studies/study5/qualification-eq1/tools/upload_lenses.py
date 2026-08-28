"""Upload P-2 lens blobs to the existing container, create-only.

Reuses the BlobClient from acquire_and_upload.py rather than duplicating the
upload path, so the create-only If-None-Match semantics and the block staging
are literally the same code that P-0 used.

Section 2 forbids creating containers, so this writes into the existing
``models`` container under a P-2 prefix. Lens bytes never enter Git; only the
digest, the byte count and the blob path are committed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "study5_eq1_acquire", _TOOLS / "acquire_and_upload.py"
)
assert _SPEC is not None and _SPEC.loader is not None
acquire = importlib.util.module_from_spec(_SPEC)
sys.modules["study5_eq1_acquire"] = acquire
_SPEC.loader.exec_module(acquire)

PREFIX = "runs/study5-eq1/p2/lenses"


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--file", action="append", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args()

    blob = acquire.BlobClient(args.account, acquire.ManagedIdentity())
    records = []

    for raw in args.file:
        path = Path(raw)
        digest, size = acquire.sha256_file(path)
        name = f"{PREFIX}/{acquire.content_address(digest)}"

        already, remote_size = blob.exists(name)
        if already:
            # Content addressing means an existing blob with this name already
            # holds these exact bytes. Re-uploading would trip the create-only
            # precondition, so this is recorded rather than retried.
            records.append(
                {
                    "local_path": str(path),
                    "sha256": digest,
                    "bytes": size,
                    "blob_path": f"{acquire.CONTAINER}/{name}",
                    "uploaded": False,
                    "already_present": True,
                    "remote_bytes": remote_size,
                }
            )
            print(f"already present: {name}")
            continue

        if size > acquire.SINGLE_PUT_CEILING:
            blocks = blob.put_blocks(name, path, size)
        else:
            blob.put_small(name, path.read_bytes())
            blocks = 1

        # Round-trip verification: read the blob back and re-hash it, so the
        # committed digest describes the bytes that are actually stored.
        readback_digest, readback_size = blob.download_sha256(name)
        if readback_digest != digest or readback_size != size:
            raise RuntimeError(
                f"round trip mismatch for {name}: "
                f"uploaded {digest}/{size}, read back {readback_digest}/{readback_size}"
            )

        records.append(
            {
                "local_path": str(path),
                "sha256": digest,
                "bytes": size,
                "blob_path": f"{acquire.CONTAINER}/{name}",
                "uploaded": True,
                "already_present": False,
                "blocks": blocks,
                "round_trip_verified": True,
            }
        )
        print(f"uploaded and verified: {name} ({size} bytes)")

    report = {
        "schema_version": "study5-eq1-p2-lens-upload-v1",
        "phase": "P-2",
        "container": acquire.CONTAINER,
        "prefix": PREFIX,
        "containers_created": 0,
        "sas_tokens_used": 0,
        "account_keys_used": 0,
        "create_only": True,
        "overwrites": 0,
        "records": records,
        "lens_bytes_committed_to_git": False,
        "claim_ceiling": "This is a storage record. It licenses no claim.",
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))
    print("P2-CHECK-LENS-UPLOAD PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
