#!/usr/bin/env python
"""Build-time verification for the Study 2 Stage B-D images.

Run inside the image build, so a drifted frozen input or a reachable
confirmation object fails the build rather than a GPU allocation. The check is
the evidence: an image that prints these lines could not have been produced from
anything but the registered bytes.

``--require-model-free`` additionally asserts that no model library is installed,
which is how the finalization image proves it cannot load weights.
``--require-confirmation-absent`` asserts the six confirmation objects were
removed from the execution image.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, "src/jspace_observation")

import study2_stage_bd as bd  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-model-free", action="store_true")
    parser.add_argument("--require-confirmation-absent", action="store_true")
    args = parser.parse_args()

    if args.require_model_free:
        for name in ("torch", "transformers"):
            if importlib.util.find_spec(name) is not None:
                raise SystemExit(f"{name} must not be present in this image")
        print("MODEL_FREE_IMAGE=1")

    root = Path(".")
    present = [path for path in bd.CONFIRMATION_PATHS if (root / path).exists()]
    if args.require_confirmation_absent:
        if present:
            raise SystemExit(f"confirmation objects are reachable: {present}")
        receipt = bd.assert_confirmation_unaddressable(root)
        print(f"DEVELOPMENT_ONLY_RECEIPT={receipt['schema_version']}")
    print(f"CONFIRMATION_PATHS_PRESENT={len(present)}")

    frozen = bd.verify_frozen_inputs(root)
    items = bd.load_development_bank(root)
    manifest = bd.build_shard_manifest(items)
    if len(items) != bd.DEVELOPMENT_ITEMS:
        raise SystemExit(f"development bank holds {len(items)} items")
    if len(manifest["shards"]) != bd.SHARD_COUNT:
        raise SystemExit(f"shard manifest holds {len(manifest['shards'])} shards")

    print(f"FROZEN_INPUTS_VERIFIED={len(frozen)}")
    print(f"DEVELOPMENT_ITEMS={len(items)}")
    print(f"EXPECTED_ROWS={bd.TOTAL_ROWS}")
    print(f"SHARD_MANIFEST_SHA256={manifest['shard_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
