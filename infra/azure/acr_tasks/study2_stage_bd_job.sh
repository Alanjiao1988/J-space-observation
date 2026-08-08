#!/usr/bin/env bash
# Container entry point for the Study 2 Stage B-D development execution job.
#
# Runs the three registered checkpoints over all eighteen shards, then hands the
# resulting artifacts back over the container registry.  Both storage accounts in
# this subscription are private-endpoint-only, so the registry is the transport;
# the payload is opaque to it and every byte is re-verified against the sealed
# manifest before anything downstream admits it.
#
# The job writes only to its work root.  It never writes into the image's tree,
# so the commit it was built from remains exactly what it was.

set -euo pipefail

# The GPU workload profile does not grant write access to the container root, so
# the work root is chosen at start rather than assumed.  Nothing scientific
# depends on the location: every output is hashed and re-verified downstream.
WORK_ROOT="${STAGE_BD_WORK_DIR:-}"
if [[ -z "$WORK_ROOT" ]]; then
    if mkdir -p /work/stage-bd 2>/dev/null; then
        WORK_ROOT="/work/stage-bd"
    else
        WORK_ROOT="${TMPDIR:-/tmp}/stage-bd"
    fi
fi
mkdir -p "$WORK_ROOT"
echo "WORK_ROOT=${WORK_ROOT}"

OUTPUT_DIR="${WORK_ROOT}/shards"
CACHE_DIR="${WORK_ROOT}/cache"

: "${STAGE_BD_SOURCE_COMMIT:?}"
: "${STAGE_BD_SOURCE_TREE:?}"
: "${STAGE_BD_IMAGE_DIGEST:?}"
: "${STAGE_BD_REGISTRY:?}"
: "${STAGE_BD_ARTIFACT_REPOSITORY:?}"
: "${STAGE_BD_ARTIFACT_TAG:?}"

mkdir -p "$OUTPUT_DIR" "$CACHE_DIR"
test -z "$(ls -A "$OUTPUT_DIR")"
test -z "$(ls -A "$CACHE_DIR")"
echo "OUTPUT_EMPTY_BEFORE_RUN=1"
echo "CACHE_EMPTY_BEFORE_RUN=1"

# Reference point for the source-tree check below.  Comparing against a marker
# created now is the only correct comparison: every file in the image predates
# the job, whereas comparing against a checked-out file depends on the order git
# happened to write the tree.
MARKER="${WORK_ROOT}/.started"
: > "$MARKER"

cd /opt/study2-src
echo "SOURCE_COMMIT=${STAGE_BD_SOURCE_COMMIT}"
echo "IMAGE_DIGEST=${STAGE_BD_IMAGE_DIGEST}"
nvidia-smi || true

export HF_HOME="$CACHE_DIR/hf"
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export PYTHONHASHSEED=0

python scripts/run_study2_stage_bd_gpu.py \
    --output "$OUTPUT_DIR" \
    --cache "$CACHE_DIR" \
    --source-commit "$STAGE_BD_SOURCE_COMMIT" \
    --source-tree "$STAGE_BD_SOURCE_TREE" \
    --image-digest "$STAGE_BD_IMAGE_DIGEST"

# The source tree must be exactly what the image was built from.  A job that
# modified its own checkout could not be trusted to have measured the pinned
# commit, so this is checked rather than assumed.
test -z "$(find /opt/study2-src -newer "$MARKER" -type f \
    -not -path '*/__pycache__/*' -print -quit)" \
    || { echo "[FAIL] the source tree was modified during execution"; exit 1; }
echo "SOURCE_TREE_UNMODIFIED=1"

OUTPUT_DIR="$OUTPUT_DIR" python - <<'PY'
import json
import os
import pathlib
import sys

sys.path.insert(0, "src/jspace_observation")
import study2_stage_bd as bd

root = pathlib.Path("/opt/study2-src")
present = [p for p in bd.CONFIRMATION_PATHS if (root / p).exists()]
if present:
    raise SystemExit(f"[FAIL] confirmation objects reachable: {present}")
receipt = json.loads(
    pathlib.Path(os.environ["OUTPUT_DIR"], "stage_bd_execution_receipt.json").read_text("utf-8")
)
print("SHARDS_COMPLETE=%d" % receipt["execution"]["shards_complete"])
print("RETRIES=%d" % receipt["execution"]["retries"])
print("SHARD_MANIFEST_SHA256=%s" % receipt["shard_manifest_sha256"])
print("CONFIRMATION_PATHS_PRESENT=0")
PY

python scripts/oci_artifact.py \
    --registry "$STAGE_BD_REGISTRY" \
    --repository "$STAGE_BD_ARTIFACT_REPOSITORY" \
    push --source "$OUTPUT_DIR" --tag "$STAGE_BD_ARTIFACT_TAG"

echo "STUDY2_STAGE_BD_EXECUTION_COMPLETE=1"
