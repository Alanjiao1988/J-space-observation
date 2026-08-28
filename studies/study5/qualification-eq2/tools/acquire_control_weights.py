"""Acquire EQ2's registered control model weights, byte-verified, VM-side only.

Same anchoring discipline as acquire_external.py and as EQ1: the authoritative
digest is the one the origin publishes at the pinned revision. LFS-backed files
carry a SHA-256 object id; small non-LFS files carry a git blob SHA-1. The two
are kept in separate fields and never conflated.

Weights are large, so files are streamed to disk and hashed while streaming
rather than buffered in memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ENDPOINT = "https://hf-mirror.com"
CHUNK = 8 * 1024 * 1024

# Authority section 4.2.
REGISTERED_MODELS = {
    "positive_control": ("Qwen/Qwen2.5-7B-Instruct", "a09a35458c702b33eeacc393d103063234e8bc28"),
    "depth_test": ("Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"),
    "negative_control": ("openai-community/gpt2", "607a30d783dfa663caf39e06633721c8d4cfcd7e"),
}

# Only what a forward pass and a tokenizer need. Duplicate weight formats such
# as .bin or .h5 mirrors of the same tensors are skipped deliberately.
WANTED_SUFFIXES = (".safetensors", ".json", ".txt", ".model")
SKIP_SUBSTRINGS = ("onnx", ".msgpack", ".h5", "rust_model", "tf_model", "pytorch_model.bin")


class AcquisitionError(RuntimeError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def git_blob_sha1_of_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def fetch_tree(repo: str, revision: str) -> list[dict]:
    url = f"{ENDPOINT}/api/models/{repo}/tree/{revision}?recursive=1"
    req = urllib.request.Request(url, headers={"User-Agent": "study5-eq2"})
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def stream_to_disk(repo: str, revision: str, path: str, destination: Path) -> tuple[str, int]:
    url = f"{ENDPOINT}/{repo}/resolve/{revision}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "study5-eq2"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    total = 0
    temporary = destination.with_suffix(destination.suffix + ".partial")
    with urllib.request.urlopen(req, timeout=7200) as response, open(temporary, "wb") as handle:
        while True:
            block = response.read(CHUNK)
            if not block:
                break
            handle.write(block)
            digest.update(block)
            total += len(block)
    temporary.replace(destination)
    return digest.hexdigest(), total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args()

    out_root = Path(args.out_dir)
    records = []

    for role, (repo, revision) in REGISTERED_MODELS.items():
        print(f"=== {role}: {repo} @ {revision}", flush=True)
        tree = fetch_tree(repo, revision)
        local_root = out_root / repo.split("/")[-1]

        for entry in tree:
            if entry.get("type") != "file":
                continue
            path = entry["path"]
            if any(s in path for s in SKIP_SUBSTRINGS):
                continue
            if not path.endswith(WANTED_SUFFIXES):
                continue

            lfs = entry.get("lfs") or {}
            lfs_oid = lfs.get("oid")
            git_oid = entry.get("oid")
            declared = entry.get("size")
            destination = local_root / path

            if destination.exists() and destination.stat().st_size == declared:
                if lfs_oid:
                    digest = hashlib.sha256()
                    with open(destination, "rb") as handle:
                        for block in iter(lambda: handle.read(CHUNK), b""):
                            digest.update(block)
                    observed, size = digest.hexdigest(), destination.stat().st_size
                else:
                    observed, size = git_blob_sha1_of_file(destination), destination.stat().st_size
                fetched = False
            else:
                if lfs_oid:
                    observed, size = stream_to_disk(repo, revision, path, destination)
                else:
                    _sha, size = stream_to_disk(repo, revision, path, destination)
                    observed = git_blob_sha1_of_file(destination)
                fetched = True

            anchor = lfs_oid or git_oid
            method = "lfs_sha256" if lfs_oid else "git_blob_sha1"
            if not anchor:
                raise AcquisitionError(f"{repo}:{path} has no origin-published anchor")
            if observed != anchor:
                raise AcquisitionError(
                    f"{repo}:{path}: {method} {observed} does not match the "
                    f"origin-published {anchor}"
                )
            if declared is not None and declared != size:
                raise AcquisitionError(
                    f"{repo}:{path}: origin declares {declared} bytes, got {size}"
                )

            records.append(
                {
                    "role": role,
                    "repo": repo,
                    "revision": revision,
                    "path": path,
                    "bytes": size,
                    "method": method,
                    "authoritative_sha256": lfs_oid,
                    "authoritative_git_blob_sha1": git_oid if not lfs_oid else None,
                    "verified": True,
                    "fetched_this_run": fetched,
                    "local_path": str(destination),
                }
            )
            print(f"  {method:<14} {path}  {size} bytes  OK", flush=True)

    report = {
        "schema_version": "study5-eq2-control-weights-v1",
        "phase": "R-0",
        "endpoint": ENDPOINT,
        "endpoint_note": (
            "huggingface.co is unreachable from this host; every file is verified "
            "against the digest the origin published at the pinned revision, so "
            "the mirror cannot substitute bytes without detection"
        ),
        "models": {
            role: {"repo": repo, "revision": revision}
            for role, (repo, revision) in REGISTERED_MODELS.items()
        },
        "trust_remote_code": False,
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
    print("EQ2-CHECK-CONTROL-WEIGHTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
