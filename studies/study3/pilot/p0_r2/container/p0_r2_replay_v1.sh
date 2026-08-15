#!/bin/sh
# The one-shot P0-R2 replay gate, run inside the pinned image.
#
# This is the only script in the image that consumes the replay envelope, and
# it may run exactly once for a given attempt. It emits the four canonical
# artifacts through the P0-R2 transport envelope so that they can be recovered
# from the ACR log alone, and it writes them durably to the attempt-bound
# private prefix.
#
# It performs no model operation of any kind. The scientific decision it makes
# is the unchanged P0-R1 generation-3 factorization gate; P0-R2 owns only the
# names, the attempt grammar, and the envelope.

set -eu

STAGE="STUDY3-P0-R2"
SRC="${P0_R2_SRC:-/opt/jspace/src}"
R2="${SRC}/studies/study3/pilot/p0_r2"
PYTHONPATH="${R2}:${SRC}/studies/study3/pilot/p0_r1"
export PYTHONPATH

RUNTIME="${P0_R2_RUNTIME_ROOT:-/workspace/runtime}"
RESULTS="${RESULTS_DIR:-${RUNTIME}/results}"
ATTEMPT="${P0_R2_ATTEMPT:-}"
DIGEST="${P0_R2_IMAGE_DIGEST:-}"

if [ -z "${ATTEMPT}" ]; then
    echo "P0_R2_REPLAY_REFUSED=1 P0_R2_ATTEMPT is required" >&2
    exit 2
fi
if [ -z "${DIGEST}" ]; then
    echo "P0_R2_REPLAY_REFUSED=1 P0_R2_IMAGE_DIGEST is required" >&2
    exit 2
fi

mkdir -p "${RESULTS}"

echo "P0_R2_STAGE=${STAGE}"
echo "P0_R2_ATTEMPT=${ATTEMPT}"
echo "P0_R2_IMAGE_DIGEST=${DIGEST}"

# The image must carry exactly the bytes Git holds before it decides anything.
python3 "${R2}/p0_r2_image_manifest_v1.py" \
    --audit /opt/jspace/p0_r2_image_manifest_v1.json \
    --image-root "${SRC}" \
    --out "${RUNTIME}/image_audit.json"
echo "P0_R2_IMAGE_TO_GIT_AUDIT_COMPLETE=1"

# The prefix must be entirely unused before a single observation is written.
python3 "${R2}/p0_r2_prefix_preflight_v1.py" --probe "${ATTEMPT}" \
    --out "${RUNTIME}/prefix_preflight.json"

# The gate itself. It verifies the delegated P0-R1 scientific bytes by SHA-256
# before importing them, then delegates the decision unchanged.
python3 "${R2}/p0_r2_replay_gate_v1.py" \
    --run \
    --out-dir "${RESULTS}" \
    --attempt "${ATTEMPT}" \
    --image-digest "${DIGEST}" \
    --ready-anchor "${P0_R2_READY_COMMIT:-}" \
    --lock-file "${P0_R2_LOCK_FILE:-/opt/jspace/p0_r2_execution_lock_v1.json}" \
    --root "${SRC}"

echo "P0_R2_REPLAY_GATE_RUN=true"
echo "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=true"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
echo "P0_R2_REPLAY_COMPLETE=1"
