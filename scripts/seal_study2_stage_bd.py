#!/usr/bin/env python
"""Emit the Study 2 Stage B-D pre-inference seal.

Runs inside the execution image, on CPU, before any weight is loaded.  The image
is the one that will later run the forwards, and it is the only place where the
six confirmation objects are genuinely absent, so the seal's
``confirmation_unopened`` receipt is a statement about the filesystem rather than
a promise about behaviour.

The seal is the record that fixes the row space, the shard partition, the option
token IDs, the frozen inputs and the core source *before* any measurement exists
to be influenced by.  It is committed and published before the execution job is
started; the commit order is the proof.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "src/jspace_observation")

import study2_stage_bd as bd  # noqa: E402


def blob_identity(root: Path, relative: str) -> dict[str, object]:
    payload = (root / relative).read_bytes()
    return {
        "bytes": len(payload),
        "path": relative,
        "sha256": bd.sha256_bytes(payload),
    }


SEALED_SOURCE_PATHS = (
    "src/jspace_observation/study2_stage_bd.py",
    "scripts/run_study2_stage_bd_gpu.py",
    "scripts/finalize_study2_stage_bd.py",
    "scripts/validate_study2_stage_bd.py",
    "scripts/seal_study2_stage_bd.py",
    "tests/test_study2_stage_bd.py",
    "studies/study2/protocol/stage_bd_pack.schema.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--image-digest", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    # No weight, no forward, no confirmation object: assert all three before the
    # seal is built rather than describing them afterwards.
    for module in ("torch", "transformers"):
        if module in sys.modules:
            raise SystemExit(f"{module} must not be imported while sealing")
    confirmation = bd.assert_confirmation_unaddressable(root)

    frozen = bd.verify_frozen_inputs(root)
    items = bd.load_development_bank(root)
    index = bd.load_stage_t_development_index(root)
    tokens = bd.option_token_ids(index)
    expected_keys = bd.expected_row_keys(items)
    manifest = bd.build_shard_manifest(items)

    missing = [key for key in expected_keys if key not in index]
    if missing:
        raise SystemExit(f"{len(missing)} planned rows have no Stage T prompt identity")

    seal = bd.build_preinference_seal(
        frozen=frozen,
        shard_manifest=manifest,
        expected_keys=expected_keys,
        source=blob_identity(root, "src/jspace_observation/study2_stage_bd.py"),
        schema=blob_identity(root, "studies/study2/protocol/stage_bd_pack.schema.json"),
        confirmation=confirmation,
        tokens=tokens,
    )

    schema = json.loads(
        (root / "studies/study2/protocol/stage_bd_pack.schema.json").read_text("utf-8")
    )
    defs = schema["$defs"]
    bd.s2.validate_json_schema(seal, {**defs["preinference_seal"], "$defs": defs})

    seal_written = bd.write_json(output / bd.SEAL_NAME, seal)
    manifest_written = bd.write_json(output / bd.SHARD_MANIFEST_NAME, manifest)

    # The three scripts and the test suite are not fields of the registered seal
    # schema, so their identities are emitted here for the receipt and the run
    # log.  The seal itself binds the core module and the schema cryptographically.
    for relative in SEALED_SOURCE_PATHS:
        blob = blob_identity(root, relative)
        print(f"SEALED_SOURCE={blob['sha256']} {blob['bytes']:>8} {blob['path']}")

    print(f"IMAGE_DIGEST={args.image_digest}")
    print(f"SOURCE_COMMIT={args.source_commit}")
    print(f"SOURCE_TREE={args.source_tree}")
    print("CONFIRMATION_PATHS_PRESENT=0")
    print(f"FROZEN_INPUTS_VERIFIED={len(frozen)}")
    print(f"EXPECTED_ROW_COUNT={seal['expected_row_count']}")
    print(f"EXPECTED_PRIMARY_KEYS_SHA256={seal['expected_primary_keys_sha256']}")
    print(f"SHARD_MANIFEST_SHA256={manifest['shard_manifest_sha256']}")
    print(f"OPTION_TOKEN_IDS={json.dumps(tokens, sort_keys=True)}")
    print(f"OUTPUT|{bd.SEAL_NAME}|{seal_written['bytes']}|{seal_written['sha256']}")
    print(
        f"OUTPUT|{bd.SHARD_MANIFEST_NAME}|{manifest_written['bytes']}"
        f"|{manifest_written['sha256']}"
    )
    print("STUDY2_STAGE_BD_PREINFERENCE_SEAL_WRITTEN=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
