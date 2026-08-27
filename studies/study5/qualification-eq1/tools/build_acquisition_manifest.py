#!/usr/bin/env python3
"""Build the authoritative acquisition manifest for Study 5-EQ1.

Authority gate Q-2 requires every acquired file to be hashed on the execution
host and matched against *its authoritative value* before use. This tool
produces that authoritative value.

**This tool downloads no file bytes.** It reads HuggingFace API metadata only.
That is an operator requirement -- all byte transfer is performed by the cloud
VM, never by the operator's workstation -- and it is achievable because the
origin publishes an integrity value for every file at a pinned revision:

* **LFS files** (every model shard and every large adapter tensor) publish an
  LFS object id, which *is* the content SHA-256. Recorded directly.
* **Non-LFS files** (configs, tokenizer JSON, the per-layer classification
  JSONs) publish only a git blob id. That is a SHA-1 over
  ``b"blob <len>\\0" + content`` and is emphatically **not** a content SHA-256.
  It is recorded under a differently named field, and the execution host
  verifies it by recomputing the same git blob SHA-1 from the mirrored bytes.

Conflating those two values is exactly the silent mismatch Q-2 exists to catch,
so they are never merged into one field. Every file ends up with an
origin-anchored authority, and the workstation transfers nothing.

The manifest is what makes the mirror route safe: the GPU host cannot reach the
HuggingFace origin, so it fetches through a mirror, and mirrored bytes are only
trustworthy when checked against an authority obtained from the origin.

Nothing here touches Azure, the GPU host, or a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = "study5-eq1-acquisition-manifest"

# Exactly the identities registered in authority section 4.1.
REGISTERED: tuple[dict[str, str], ...] = (
    {
        "role": "base_mlp_donor",
        "repo": "Qwen/Qwen2.5-Math-7B",
        "revision": "b101308fe89651ea5ce025f25317fea6fc07e96e",
        "licence": "apache-2.0",
        "redistributable": "yes",
    },
    {
        "role": "adapter_primary",
        "repo": "nathu0/transcoder-adapters-R1-Distill-Qwen-7B-l1w0.001-l0-1.4",
        "revision": "9033fcd16d2fcb8fbe18efa2e6ed6503b0a784dc",
        "licence": "none",
        "redistributable": "no",
    },
    {
        "role": "adapter_sparsity_sensitivity",
        "repo": "nathu0/transcoder-adapters-R1-Distill-Qwen-7B-l1w0.003-l0-4.3",
        "revision": "89ead0db81b65fa1ed6d433324d100c74bf77edd",
        "licence": "none",
        "redistributable": "no",
    },
)

# Recorded by authority section 4.1 but explicitly NOT acquired here.
RECORDED_NOT_ACQUIRED = {
    "nathu0/transcoder-adapters-R1-Distill-Qwen-7B-l1w0.01-l0-10.3": "0f628036f9522bc8687c7fd09fc5af2cf6c51336",
    "nathu0/transcoder-adapters-R1-Distill-Qwen-7B-l1w0.0003-l0-0.4": "893466285964c27b7b9ecb42d8036fd67686afaa",
    "nathu0/transcoder-adapters-R1-Distill-Qwen-7B-l1w0.0001-l0-0.1": "5846092d62317129ec24af0c5b276c2e5f7dbf0e",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def manifest_for(entry: dict[str, str]) -> dict[str, Any]:
    repo, revision = entry["repo"], entry["revision"]
    tree = _get_json(
        f"https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true"
    )

    files: list[dict[str, Any]] = []
    for node in sorted(tree, key=lambda n: str(n["path"])):
        if node.get("type") != "file":
            continue
        lfs = node.get("lfs") or {}
        oid = lfs.get("oid") or lfs.get("sha256")

        record: dict[str, Any] = {
            "path": str(node["path"]),
            "size_bytes": int(node.get("size") or 0),
            "is_lfs": bool(lfs),
            "authoritative_sha256": None,
            "authoritative_git_blob_sha1": None,
        }
        if oid:
            record["authoritative_sha256"] = str(oid)
            record["authority_kind"] = "lfs_sha256"
            record["authority_source"] = (
                "HuggingFace LFS object id at the pinned revision; this is the "
                "content SHA-256"
            )
        elif node.get("oid"):
            record["authoritative_git_blob_sha1"] = str(node["oid"])
            record["authority_kind"] = "git_blob_sha1"
            record["authority_source"] = (
                "HuggingFace git blob id at the pinned revision; a SHA-1 over "
                "b'blob <len>\\0' + content, NOT a content SHA-256; the execution "
                "host verifies it by recomputing the same construction"
            )
        else:
            record["authority_kind"] = "none"
            record["authority_source"] = "unavailable: origin published no integrity id"
        files.append(record)

    unresolved = [f["path"] for f in files if f["authority_kind"] == "none"]
    return {
        **entry,
        "file_count": len(files),
        "total_bytes": sum(f["size_bytes"] for f in files),
        "lfs_file_count": len([f for f in files if f["is_lfs"]]),
        "non_lfs_file_count": len([f for f in files if not f["is_lfs"]]),
        "files": files,
        "files_without_authority": unresolved,
        "fully_resolved": not unresolved,
    }


def build() -> dict[str, Any]:
    entries = [manifest_for(e) for e in REGISTERED]
    return {
        "schema_version": "study5-eq1-acquisition-manifest-v2",
        "authority_section": "4.1",
        "built_at_utc": utc_now(),
        "built_from": "HuggingFace API metadata only",
        "file_bytes_downloaded_by_this_tool": 0,
        "operator_constraint": (
            "All byte transfer is performed by the cloud VM. The operator's "
            "workstation downloads no file bytes, so this tool reads metadata "
            "only and derives every authority from published integrity ids."
        ),
        "why_this_manifest_exists": (
            "The Mooncake GPU host cannot reach the HuggingFace origin, so bytes "
            "are fetched there through a mirror. Mirrored bytes are only "
            "trustworthy when checked against an authority obtained from the "
            "origin, which is what this manifest supplies."
        ),
        "authority_kinds": {
            "lfs_sha256": "content SHA-256, compared directly against the host-computed digest",
            "git_blob_sha1": "SHA-1 over b'blob <len>\\0' + content, recomputed on the host",
        },
        "targets": entries,
        "target_count": len(entries),
        "total_bytes": sum(e["total_bytes"] for e in entries),
        "total_files": sum(e["file_count"] for e in entries),
        "all_targets_fully_resolved": all(e["fully_resolved"] for e in entries),
        "recorded_but_not_acquired": RECORDED_NOT_ACQUIRED,
        "already_verified_by_predecessor": {
            "role": "target_T",
            "repo": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            "revision": "916b56a44061fd5cd7d6a8fb632557ed4f724f60",
            "note": "byte-verified into the models container by Study 4F-M1; not re-acquired",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    payload = build()
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    print(f"{args.out}  sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    print(
        "file bytes downloaded by this tool: "
        f"{payload['file_bytes_downloaded_by_this_tool']}"
    )
    for entry in payload["targets"]:
        print(
            f"  {entry['role']:<28} {entry['file_count']:>3} files "
            f"({entry['lfs_file_count']} lfs / {entry['non_lfs_file_count']} non-lfs)  "
            f"{entry['total_bytes']:>14,} B  resolved={entry['fully_resolved']}"
        )
        for missing in entry["files_without_authority"]:
            print(f"      UNRESOLVED: {missing}")
    return 0 if payload["all_targets_fully_resolved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
