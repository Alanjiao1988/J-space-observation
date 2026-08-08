#!/usr/bin/env python
"""Execute the Study 2 Stage T pinned config/tokenizer gate.

This entry point is the only place Stage T touches Hugging Face.  It resolves
*configuration and tokenizer assets only*, under an explicit allowlist, at the
exact immutable revisions registered in the frozen protocol, and refuses to
continue if a single model-weight or adapter-weight file reaches the staged
snapshot.  No ``AutoModel*`` class is imported or instantiated anywhere in this
file, and no forward path exists to call.

Deterministic core artifacts never contain a run ID, image digest, timestamp,
or cache path.  Those live in the separate attempt receipt, which the final
handoff binds by hash.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Import the Stage T modules as top-level modules, exactly as every other Study 2
# entry point does.  Importing the ``jspace_observation`` package would execute
# its ``__init__``, which pulls in ``model_loader`` and therefore ``AutoModel*``
# and ``torch`` -- both forbidden in Stage T.
sys.path.insert(0, str(REPO_ROOT / "src" / "jspace_observation"))

import study2_protocol as s2  # noqa: E402
import study2_stage_t as st  # noqa: E402

FORBIDDEN_MODULES = ("torch", "accelerate", "jlens", "jacobian_lens")

# Importing either of these is the operation that could load a weight tensor.
# Their absence after tokenizer construction is the machine-checkable statement
# that Stage T never entered a modelling path.
WEIGHT_PATH_MODULES = (
    "transformers.modeling_utils",
    "transformers.models.auto.modeling_auto",
)


def _refuse_model_classes() -> None:
    """Fail closed if a model class ever becomes reachable from this module."""

    import transformers

    leaked = sorted(
        name
        for name in dir(transformers)
        if name.startswith("AutoModel") and name in globals()
    )
    if leaked:
        raise st.StageTError(f"model classes leaked into this module: {leaked}")


def _assert_no_weight_path() -> None:
    reached = sorted(name for name in WEIGHT_PATH_MODULES if name in sys.modules)
    if reached:
        raise st.StageTError(f"a weight-loading module was imported: {reached}")


def stage_snapshot(
    model_id: str,
    revision: str,
    cache_root: Path,
) -> dict[str, object]:
    """Download only allowlisted config/tokenizer files at a pinned revision."""

    from huggingface_hub import HfApi, snapshot_download

    info = HfApi().repo_info(repo_id=model_id, revision=revision, files_metadata=False)
    resolved = str(info.sha)
    if resolved != revision:
        raise st.StageTError(
            f"{model_id} resolved revision {resolved} != pinned {revision}"
        )

    local_dir = cache_root / model_id.replace("/", "__")
    snapshot_download(
        repo_id=model_id,
        revision=revision,
        allow_patterns=list(st.TOKENIZER_FILE_ALLOWLIST),
        local_dir=str(local_dir),
        cache_dir=str(cache_root / "_hub"),
    )

    present = sorted(
        path for path in local_dir.rglob("*") if path.is_file() and ".cache" not in path.parts
    )
    names = [path.relative_to(local_dir).as_posix() for path in present]
    weights = st.classify_weight_files(names)
    if weights:
        raise st.StageTError(f"{model_id} snapshot contains weight files: {weights}")
    unexpected = sorted(set(names) - set(st.TOKENIZER_FILE_ALLOWLIST))
    if unexpected:
        raise st.StageTError(f"{model_id} snapshot contains unallowlisted files: {unexpected}")

    files = [
        {
            "bytes": path.stat().st_size,
            "name": path.relative_to(local_dir).as_posix(),
            "sha256": st.sha256_bytes(path.read_bytes()),
        }
        for path in present
    ]
    return {
        "files": files,
        "local_dir": local_dir,
        "model_id": model_id,
        "requested_revision": revision,
        "resolved_revision": resolved,
    }


def build_tokenizer(local_dir: Path) -> tuple[object, object]:
    """Construct one tokenizer offline, with remote code disabled."""

    from transformers import AutoConfig, AutoTokenizer

    config = AutoConfig.from_pretrained(
        str(local_dir), trust_remote_code=False, local_files_only=True
    )
    tokenizer = AutoTokenizer.from_pretrained(
        str(local_dir), trust_remote_code=False, local_files_only=True, use_fast=True
    )
    return config, tokenizer


def core_environment(root: Path) -> dict[str, object]:
    """Deterministic, repo-derived environment identity for the core manifest."""

    lock = (root / "requirements.lock.txt").read_bytes().replace(b"\r\n", b"\n")
    pins: dict[str, str] = {}
    for line in lock.decode("utf-8").splitlines():
        if "==" in line and not line.startswith("#"):
            name, _, version = line.partition("==")
            pins[name.strip().lower()] = version.strip()
    return {
        "base_image_reference": "python:3.11-bookworm",
        "dependency_lock_sha256": st.sha256_bytes(lock),
        "huggingface_hub_pin": pins.get("huggingface-hub", pins.get("huggingface_hub", "")),
        "tokenizers_pin": pins.get("tokenizers", ""),
        "transformers_pin": pins.get("transformers", ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--image-digest", default="")
    args = parser.parse_args(argv)

    for name in FORBIDDEN_MODULES:
        if name in sys.modules:
            raise st.StageTError(f"forbidden module already imported: {name}")

    root = Path(args.project_root).resolve()
    cache_root = Path(args.cache_root).resolve()
    output_dir = Path(args.output_dir) if args.output_dir else root / st.OUTPUT_DIR

    started = time.monotonic()
    st.verify_frozen_inputs(root)
    s2.verify_protected_anchors(root)
    _refuse_model_classes()

    snapshots: dict[str, dict[str, object]] = {}
    tokenizers: dict[str, object] = {}
    config_types: dict[str, str] = {}
    for role, model_id, revision in s2.MODEL_IDENTITIES:
        snapshot = stage_snapshot(model_id, revision, cache_root)
        config, tokenizer = build_tokenizer(Path(str(snapshot["local_dir"])))
        config_types[role] = str(getattr(config, "model_type", ""))
        snapshot["config_model_type"] = config_types[role]
        snapshot.pop("local_dir")
        snapshots[role] = snapshot
        tokenizers[role] = tokenizer
        print(f"STAGE_T_TOKENIZER_READY|{role}|{model_id}|{revision}")

    if "torch" in sys.modules:
        print("STAGE_T_NOTE|torch entered sys.modules transitively; no weight path used")
    _assert_no_weight_path()
    _refuse_model_classes()

    result = st.run_gate(root, tokenizers)
    written = st.write_pack(output_dir, result, core_environment(root), snapshots)
    manifest = written["manifest"]
    elapsed = time.monotonic() - started

    receipt = {
        "attempt_id": args.attempt_id,
        "core_manifest_sha256": written["manifest_entry"]["sha256"],
        "elapsed_seconds_bucket": int(elapsed // 60),
        "image_digest": args.image_digest,
        "platform_machine": platform.machine(),
        "python_version": platform.python_version(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED", ""),
        "run_id": args.run_id,
        "schema_version": st.ATTEMPT_RECEIPT_VERSION,
        "source_commit": os.environ.get("STAGE_T_SOURCE_COMMIT", ""),
        "source_tree": os.environ.get("STAGE_T_SOURCE_TREE", ""),
        "torch_imported": "torch" in sys.modules,
        "weight_path_modules_imported": sorted(
            name for name in WEIGHT_PATH_MODULES if name in sys.modules
        ),
    }
    receipt_path = output_dir / f"{st.ATTEMPT_RECEIPT_PREFIX}{args.attempt_id}.json"
    st.write_json(receipt_path, receipt)

    for name, row in sorted(manifest["files"].items()):
        print(f"STAGE_T_FILE|{name}|bytes={row['bytes']}|rows={row['rows']}|sha256={row['sha256']}")
    entry = written["manifest_entry"]
    print(
        f"STAGE_T_FILE|{st.CORE_MANIFEST_NAME}|bytes={entry['bytes']}"
        f"|rows={entry['rows']}|sha256={entry['sha256']}"
    )
    print(f"STAGE_T_ATTEMPT_RECEIPT|{st.sha256_bytes(receipt_path.read_bytes())}")
    print(
        "STAGE_T_SUMMARY="
        + json.dumps(
            {
                "joint_eligible_pairs": manifest["joint_eligible_pairs"],
                "prompt_row_count_per_model": manifest["prompt_row_count_per_model"],
                "selected_total": manifest["selection"]["selected_total"],
                "shortfalls": manifest["selection"]["shortfalls"],
                "terminal_state": manifest["terminal_state"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    if manifest["terminal_state"] != st.TERMINAL_STATE:
        print("BLOCKED_ON_STUDY2_MECHANISTIC_TOKEN_SUPPORT")
        return 1
    print("STAGE_T_GATE_COMPLETE=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
