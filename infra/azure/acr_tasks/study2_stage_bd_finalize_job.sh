#!/usr/bin/env bash
# Container entry point for Study 2 Stage B-D finalization and validation.
#
# Runs on a CPU-only Consumption profile from an image that has no torch and no
# transformers installed at all.  Model-freeness is therefore a property of the
# image rather than a promise in the code, and the runtime assertion in both
# Python entry points is a second lock on the same door.
#
# The pack this produces is not authoritative because this job wrote it.  It
# becomes admissible only after scripts/validate_study2_stage_bd.py, which shares
# no writing code path, certifies the complete 3,072-row pack.

set -euo pipefail

SHARD_ROOT="/work/shards"
PACK_ROOT="/work/pack"

: "${STAGE_BD_REGISTRY:?}"
: "${STAGE_BD_ARTIFACT_REPOSITORY:?}"
: "${STAGE_BD_ARTIFACT_TAG:?}"
: "${STAGE_BD_SOURCE_COMMIT:?}"

mkdir -p "$SHARD_ROOT" "$PACK_ROOT"
test -z "$(ls -A "$SHARD_ROOT")"
test -z "$(ls -A "$PACK_ROOT")"

cd /opt/study2-src
export PYTHONHASHSEED=0
echo "SOURCE_COMMIT=${STAGE_BD_SOURCE_COMMIT}"
python -V

python - <<'PY'
import importlib.util
for name in ("torch", "transformers"):
    if importlib.util.find_spec(name) is not None:
        raise SystemExit(f"[FAIL] {name} is installed in a model-free image")
print("MODEL_FREE_IMAGE=1")
PY

python scripts/oci_artifact.py \
    --registry "$STAGE_BD_REGISTRY" \
    --repository "$STAGE_BD_ARTIFACT_REPOSITORY" \
    pull --reference "$STAGE_BD_ARTIFACT_TAG" --dest "$SHARD_ROOT"

python scripts/finalize_study2_stage_bd.py --shards "$SHARD_ROOT" --output "$PACK_ROOT"
python scripts/validate_study2_stage_bd.py --pack "$PACK_ROOT"

python - "$PACK_ROOT" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

pack = Path(sys.argv[1])
manifest = json.loads((pack / "stage_bd_core_manifest.json").read_text(encoding="utf-8"))
for entry in manifest["files"]:
    data = (pack / entry["path"]).read_bytes()
    assert len(data) == entry["bytes"], entry["path"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["path"]
    print(
        f"OUTPUT|{entry['path']}|rows={entry['rows']}|bytes={entry['bytes']}"
        f"|sha256={entry['sha256']}"
    )
core = (pack / "stage_bd_core_manifest.json").read_bytes()
print(f"OUTPUT|stage_bd_core_manifest.json|bytes={len(core)}"
      f"|sha256={hashlib.sha256(core).hexdigest()}")
print(f"CORE_MANIFEST_SHA256={hashlib.sha256(core).hexdigest()}")
print(f"TERMINAL_STATE={manifest['terminal_state']}")
print(f"OVERALL_GATE_PASS={manifest['overall_gate_pass']}")
PY

python scripts/oci_artifact.py \
    --registry "$STAGE_BD_REGISTRY" \
    --repository "$STAGE_BD_ARTIFACT_REPOSITORY" \
    push --source "$PACK_ROOT" --tag "pack-${STAGE_BD_ARTIFACT_TAG}"

echo "STUDY2_STAGE_BD_FINALIZE_COMPLETE=1"
