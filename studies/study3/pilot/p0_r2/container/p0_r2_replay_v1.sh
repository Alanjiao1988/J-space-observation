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
MODE="${P0_R2_REPLAY_MODE:-}"

if [ -z "${ATTEMPT}" ]; then
    echo "P0_R2_REPLAY_REFUSED=1 P0_R2_ATTEMPT is required" >&2
    exit 2
fi
if [ -z "${DIGEST}" ]; then
    echo "P0_R2_REPLAY_REFUSED=1 P0_R2_IMAGE_DIGEST is required" >&2
    exit 2
fi

# The registered task file passes the submission mode straight through, and the
# packing canary and the live replay reach this script by exactly the same
# route. Branching on the mode is therefore the only thing standing between a
# transport rehearsal and an irreversible consumption of the one-shot envelope,
# so an absent or unrecognised mode is refused rather than assumed.
case "${MODE}" in
    packing-canary)
        # A rehearsal of the submission transport only. Nothing here reads or
        # writes the replay envelope, reaches the gate, or touches a model.
        #
        # The prefix absence proof is deliberately not attempted here: it needs
        # Azure credentials that this task is not granted, and a probe that
        # cannot reach the control plane can only report ambiguity, never
        # absence. It is run from the host, where the credentials exist, as its
        # own canary.
        env P0_R2_ATTEMPT= P0_R2_RUNTIME_ROOT=/tmp/p0r2-packing-canary \
            /usr/local/bin/p0_r2_canary_v1.sh preflight
        echo "P0_R2_PACKING_CANARY_ATTEMPT=${ATTEMPT}"
        echo "P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1"
        echo "P0_R2_PACKING_CANARY_COMPLETE=1"
        exit 0
        ;;
    live)
        : # fall through to the gate below
        ;;
    "")
        echo "P0_R2_REPLAY_REFUSED=1 P0_R2_REPLAY_MODE is required" >&2
        exit 2
        ;;
    *)
        echo "P0_R2_REPLAY_REFUSED=1 unrecognised mode ${MODE}" >&2
        exit 2
        ;;
esac

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
