#!/usr/bin/env python3
"""Download and manifest the exact model snapshot without loading it."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
MODEL_REVISION = "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import HfApi, snapshot_download

    info = HfApi().model_info(MODEL_ID, revision=MODEL_REVISION, files_metadata=True)
    if str(info.sha) != MODEL_REVISION:
        raise RuntimeError("immutable model revision readback mismatch")
    snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=output,
    )
    cache = output / ".cache"
    if cache.exists():
        shutil.rmtree(cache)
    files = []
    for path in sorted(
        (path for path in output.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(output).as_posix(),
    ):
        if path.name == "MODEL_SNAPSHOT_MANIFEST.json":
            continue
        files.append(
            {
                "bytes": path.stat().st_size,
                "path": path.relative_to(output).as_posix(),
                "sha256": sha256_file(path),
            }
        )
    if not any(row["path"].endswith(".safetensors") for row in files):
        raise RuntimeError("model snapshot contains no safetensors weights")
    document = {
        "complete": True,
        "files": files,
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "source": f"https://huggingface.co/{MODEL_ID}/tree/{MODEL_REVISION}",
    }
    (output / "MODEL_SNAPSHOT_MANIFEST.json").write_bytes(canonical_json(document))
    print(
        json.dumps(
            {
                "file_count": len(files),
                "manifest_sha256": sha256_file(
                    output / "MODEL_SNAPSHOT_MANIFEST.json"
                ),
                "model_id": MODEL_ID,
                "revision": MODEL_REVISION,
                "total_bytes": sum(row["bytes"] for row in files),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
