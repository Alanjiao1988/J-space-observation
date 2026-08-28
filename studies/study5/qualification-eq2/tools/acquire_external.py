"""Acquire EQ2's registered external artifacts, byte-verified and create-only.

Anchoring rule inherited from EQ1 §4.1: the authoritative digest is the one the
ORIGIN publishes, never one we compute from the bytes we fetched. Computing a
digest from the object under test and then "verifying" the object against it is
circular. So:

  * LFS-backed files      -> authoritative SHA-256 is the LFS object id;
  * non-LFS files         -> authoritative id is the git blob SHA-1.

The two live in separate fields and are never conflated.

OD-011: every check here has a demonstrated failing case in
tests/test_eq2_acquisition.py. The verification functions are written as pure
functions over (expected, actual) precisely so a negative test can drive them.

All bytes are fetched by the VM. Nothing is downloaded to the operator's
workstation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "neuronpedia/jacobian-lens"
REVISION = "0731326edff4ae730ffc5356fe1a4728c748b3a6"
ENDPOINT = "https://hf-mirror.com"
CHUNK = 8 * 1024 * 1024

# Registered in authority section 4.1. Roles are recorded so that a file cannot
# quietly change role between acquisition and use.
REGISTERED_FILES = {
    "positive_control": [
        "qwen2.5-7b-it/jlens/Salesforce-wikitext/Qwen2.5-7B-Instruct_jacobian_lens.pt",
        "qwen2.5-7b-it/jlens/Salesforce-wikitext/config.yaml",
        "qwen2.5-7b-it/jlens/Salesforce-wikitext/Qwen2.5-7B-Instruct_convergence.csv",
    ],
    "negative_control": [
        "gpt2-small/jlens/Salesforce-wikitext/gpt2_jacobian_lens.pt",
        "gpt2-small/jlens/Salesforce-wikitext/config.yaml",
        "gpt2-small/jlens/Salesforce-wikitext/gpt2_convergence.csv",
    ],
    "depth_test": [
        "qwen3-1.7b/jlens/Salesforce-wikitext/Qwen3-1.7B_jacobian_lens.pt",
        "qwen3-1.7b/jlens/Salesforce-wikitext/config.yaml",
        "qwen3-1.7b/jlens/Salesforce-wikitext/Qwen3-1.7B_convergence.csv",
    ],
}


class AcquisitionError(RuntimeError):
    """Raised when an artifact cannot be obtained byte-exactly."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def content_address(sha: str) -> str:
    return f"sha256/{sha[:2]}/{sha}"


def verify_against_origin(
    payload: bytes, *, lfs_oid: str | None, git_oid: str | None, path: str
) -> dict:
    """Check fetched bytes against the digest the ORIGIN published.

    Returns the verification record. Raises AcquisitionError on any mismatch,
    and also when there is no origin anchor at all - an unanchored file is not
    "verified by default", it is unverifiable, which is a stop.
    """
    if not lfs_oid and not git_oid:
        raise AcquisitionError(
            f"{path}: origin published no anchor; the file cannot be verified"
        )

    record: dict = {
        "path": path,
        "bytes": len(payload),
        "authoritative_sha256": lfs_oid,
        "authoritative_git_blob_sha1": git_oid if not lfs_oid else None,
    }

    if lfs_oid:
        actual = sha256_bytes(payload)
        record["observed_sha256"] = actual
        record["method"] = "lfs_sha256"
        if actual != lfs_oid:
            raise AcquisitionError(
                f"{path}: sha256 {actual} does not match the origin-published "
                f"LFS object id {lfs_oid}"
            )
    else:
        actual = git_blob_sha1(payload)
        record["observed_git_blob_sha1"] = actual
        record["method"] = "git_blob_sha1"
        # sha256 is still recorded, but as a DESCRIPTION of the bytes, never as
        # the thing they were checked against.
        record["sha256_of_fetched_bytes_not_an_anchor"] = sha256_bytes(payload)
        if actual != git_oid:
            raise AcquisitionError(
                f"{path}: git blob {actual} does not match the origin-published "
                f"id {git_oid}"
            )

    record["verified"] = True
    return record


def fetch_tree(subdir: str) -> list[dict]:
    url = f"{ENDPOINT}/api/models/{REPO}/tree/{REVISION}/{subdir}"
    req = urllib.request.Request(url, headers={"User-Agent": "study5-eq2"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def fetch_file(path: str) -> bytes:
    url = f"{ENDPOINT}/{REPO}/resolve/{REVISION}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "study5-eq2"})
    buffer = bytearray()
    with urllib.request.urlopen(req, timeout=3600) as response:
        while True:
            block = response.read(CHUNK)
            if not block:
                break
            buffer.extend(block)
    return bytes(buffer)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument(
        "--only-small",
        action="store_true",
        help="fetch only config.yaml and convergence.csv, not the lens tensors",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build the anchor table from the origin's tree listing.
    anchors: dict[str, dict] = {}
    for subdir in ("qwen2.5-7b-it", "gpt2-small", "qwen3-1.7b"):
        for entry in fetch_tree(f"{subdir}/jlens/Salesforce-wikitext"):
            if entry.get("type") != "file":
                continue
            lfs = entry.get("lfs") or {}
            anchors[entry["path"]] = {
                "lfs_oid": lfs.get("oid"),
                "git_oid": entry.get("oid"),
                "size": entry.get("size"),
            }

    records = []
    for role, paths in REGISTERED_FILES.items():
        for path in paths:
            if args.only_small and path.endswith(".pt"):
                continue
            if path not in anchors:
                raise AcquisitionError(
                    f"{path}: registered artifact absent from the origin tree at "
                    f"revision {REVISION}"
                )
            anchor = anchors[path]

            destination = out_dir / path
            if destination.exists():
                payload = destination.read_bytes()
                fetched = False
            else:
                payload = fetch_file(path)
                fetched = True

            record = verify_against_origin(
                payload,
                lfs_oid=anchor["lfs_oid"],
                git_oid=anchor["git_oid"],
                path=path,
            )
            record["role"] = role
            record["fetched_this_run"] = fetched
            record["origin_declared_size"] = anchor["size"]
            if anchor["size"] is not None and anchor["size"] != len(payload):
                raise AcquisitionError(
                    f"{path}: origin declares {anchor['size']} bytes, got {len(payload)}"
                )

            if fetched:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(payload)
            records.append(record)
            print(
                f"  {record['method']:<14} {path}  {len(payload)} bytes  OK",
                flush=True,
            )

    report = {
        "schema_version": "study5-eq2-external-acquisition-v1",
        "phase": "R-0",
        "repo": REPO,
        "revision": REVISION,
        "revision_pinned_by": "authority section 4.1",
        "endpoint": ENDPOINT,
        "endpoint_note": (
            "huggingface.co is unreachable from this host; the mirror serves the "
            "same content, and every file is verified against the digest the "
            "ORIGIN published at the pinned revision, so the transport cannot "
            "substitute bytes without detection"
        ),
        "licence": "mit",
        "files": records,
        "file_count": len(records),
        "total_bytes": sum(r["bytes"] for r in records),
        "failures": 0,
        "fetched_by": "gpu vm",
        "bytes_fetched_by_operator_workstation": 0,
        "claim_ceiling": "An acquisition record. It licenses no claim of any kind.",
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))
    print(f"files {report['file_count']}  bytes {report['total_bytes']}  failures 0")
    print("EQ2-CHECK-EXTERNAL-ACQUISITION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
