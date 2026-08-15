#!/bin/sh
# The bounded P0-R2 model pilot for the corrected closure.
#
# It refuses unless everything is already true. It cannot be run by accident: it
# demands an authorization document that can only be built from a completed
# replay receipt, a verified reconstruction receipt, a published head proof and
# the pinned lock.
#
# This is p0_r2_model_pilot_v1.sh with the same two defects fixed that the v1
# replay path carried: it audits the v2 image manifest, and it takes the active
# lock from the submitted context or from an explicitly supplied path rather
# than from /opt/jspace/p0_r2_execution_lock_v1.json, which no Dockerfile ever
# wrote. Both would have refused on the one invocation that matters.
#
# The science is the unchanged P0-R1 generation-3 runner. P0-R2 contributes the
# transport and the refusals, nothing else.

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
LOCK="${P0_R2_LOCK_FILE:-${RUNTIME}/p0_r2_execution_lock_v2.json}"

refuse() {
    echo "P0_R2_PILOT_REFUSED=1 $*" >&2
    echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0" >&2
    exit 3
}

[ -n "${ATTEMPT}" ] || refuse "P0_R2_ATTEMPT is required"
[ -n "${DIGEST}" ] || refuse "P0_R2_IMAGE_DIGEST is required"
[ -f "${LOCK}" ] || refuse "the execution lock ${LOCK} is not readable"
[ -n "${P0_R2_REPLAY_RECEIPT:-}" ] || refuse "a replay receipt is required"
[ -n "${P0_R2_RECONSTRUCTION_RECEIPT:-}" ] \
    || refuse "a reconstruction receipt is required"
[ -n "${P0_R2_HEAD_PROOF:-}" ] || refuse "a published head proof is required"
[ "${P0_R2_PILOT_AUTHORIZED:-0}" = "1" ] \
    || refuse "P0_R2_PILOT_AUTHORIZED=1 must be set explicitly"

mkdir -p "${RESULTS}"

echo "P0_R2_STAGE=${STAGE}"
echo "P0_R2_PILOT_REVISION=2"
echo "P0_R2_ATTEMPT=${ATTEMPT}"
echo "P0_R2_IMAGE_DIGEST=${DIGEST}"

python3 "${R2}/p0_r2_image_manifest_v2.py" \
    --audit /opt/jspace/p0_r2_image_manifest_v2.json \
    --image-root "${SRC}" \
    --install-root /usr/local/bin \
    --out "${RUNTIME}/image_audit_v2.json"

python3 "${R2}/p0_r2_execution_lock_v2.py" --validate --lock-file "${LOCK}"

# Build the authorization. This performs zero Azure operations and refuses
# unless every input agrees with every other input.
python3 "${R2}/p0_r2_authorization_v1.py" \
    --build \
    --lock "${LOCK}" \
    --replay-receipt "${P0_R2_REPLAY_RECEIPT}" \
    --reconstruction-receipt "${P0_R2_RECONSTRUCTION_RECEIPT}" \
    --head-proof "${P0_R2_HEAD_PROOF}" \
    --attempt "${ATTEMPT}" \
    --image-digest "${DIGEST}" \
    --out "${RUNTIME}/p0_r2_pilot_authorization.json"

python3 "${R2}/p0_r2_prefix_preflight_v1.py" --probe "${ATTEMPT}" \
    --out "${RUNTIME}/prefix_preflight.json"

echo "P0_R2_AUTHORIZATION_BUILT=1"

# Only now is the model runner allowed to consider running.
python3 "${R2}/p0_r2_model_runner_v1.py" --sentinel --attempt "${ATTEMPT}"

echo "P0_R2_PILOT_COMPLETE=1"
