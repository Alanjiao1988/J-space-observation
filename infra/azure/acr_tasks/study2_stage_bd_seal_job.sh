#!/usr/bin/env bash
# Container entry point for the Study 2 Stage B-D pre-inference seal.
#
# Runs the execution image on CPU with no GPU allocated and no model library
# touched, writes the seal and the shard manifest, and hands them back over the
# container registry.  It exists as a separate job because the seal must be
# committed and published before the first weight load, and a job that could
# also run forwards could not prove that ordering.

set -euo pipefail

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

OUTPUT_DIR="${WORK_ROOT}/seal"

: "${STAGE_BD_SOURCE_COMMIT:?}"
: "${STAGE_BD_SOURCE_TREE:?}"
: "${STAGE_BD_IMAGE_DIGEST:?}"
: "${STAGE_BD_REGISTRY:?}"
: "${STAGE_BD_ARTIFACT_REPOSITORY:?}"
: "${STAGE_BD_ARTIFACT_TAG:?}"

mkdir -p "$OUTPUT_DIR"
test -z "$(ls -A "$OUTPUT_DIR")"
echo "OUTPUT_EMPTY_BEFORE_RUN=1"

# Reference point for the source-tree check below.  Comparing against a marker
# created now is the only correct comparison: every file in the image predates
# the job, whereas comparing against a checked-out file depends on the order git
# happened to write the tree.
MARKER="${WORK_ROOT}/.started"
: > "$MARKER"

cd /opt/study2-src
echo "SOURCE_COMMIT=${STAGE_BD_SOURCE_COMMIT}"
echo "IMAGE_DIGEST=${STAGE_BD_IMAGE_DIGEST}"

# No accelerator is requested for this job.  Recording the absence is cheaper
# than arguing about it later.
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    echo "GPU_VISIBLE=1"
else
    echo "GPU_VISIBLE=0"
fi

export PYTHONHASHSEED=0

python scripts/seal_study2_stage_bd.py \
    --root /opt/study2-src \
    --output "$OUTPUT_DIR" \
    --source-commit "$STAGE_BD_SOURCE_COMMIT" \
    --source-tree "$STAGE_BD_SOURCE_TREE" \
    --image-digest "$STAGE_BD_IMAGE_DIGEST"

test -z "$(find /opt/study2-src -newer "$MARKER" -type f \
    -not -path '*/__pycache__/*' -print -quit)" \
    || { echo "[FAIL] the source tree was modified during sealing"; exit 1; }
echo "SOURCE_TREE_UNMODIFIED=1"

python scripts/oci_artifact.py \
    --registry "$STAGE_BD_REGISTRY" \
    --repository "$STAGE_BD_ARTIFACT_REPOSITORY" \
    push --source "$OUTPUT_DIR" --tag "$STAGE_BD_ARTIFACT_TAG"

echo "STUDY2_STAGE_BD_SEAL_COMPLETE=1"
