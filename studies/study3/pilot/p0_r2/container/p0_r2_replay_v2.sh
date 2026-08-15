#!/bin/sh
# The one-shot P0-R2 replay gate for the corrected closure, run inside the
# pinned image.
#
# This is p0_r2_replay_v1.sh with the two things it could not have known fixed.
#
# 1. The v1 script audits /opt/jspace/p0_r2_image_manifest_v1.json. The
#    corrected image is built from the P0-R1 generation-3 base and carries the
#    v2 manifest, so it audits the v2 manifest.
#
# 2. The v1 script defaults --lock-file to
#    /opt/jspace/p0_r2_execution_lock_v1.json, and no Dockerfile ever copied a
#    lock to /opt/jspace. The live path would therefore have refused with an
#    unreadable lock the first time it was ever run -- a defect that could only
#    have been found by running the thing that consumes the envelope.
#
#    The corrected script takes the lock from the place it is actually
#    guaranteed to be: the two-file submission context. The context manifest
#    embeds the exact published lock bytes, and this script extracts them,
#    re-verifies their length and SHA-256 against the manifest's own
#    declaration, and only then hands them to the gate. The lock the gate reads
#    is therefore the lock the host proved it was submitting, not a copy that
#    happened to be baked into an image weeks earlier.
#
# It performs no model operation of any kind. The scientific decision it makes
# is the unchanged P0-R1 generation-3 factorization gate; P0-R2 owns only the
# names, the attempt grammar and the envelope.

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
MANIFEST="${P0_R2_CONTEXT_MANIFEST:-/workspace/context_manifest.json}"

if [ -z "${ATTEMPT}" ]; then
    echo "P0_R2_REPLAY_REFUSED=1 P0_R2_ATTEMPT is required" >&2
    exit 2
fi
if [ -z "${DIGEST}" ]; then
    echo "P0_R2_REPLAY_REFUSED=1 P0_R2_IMAGE_DIGEST is required" >&2
    exit 2
fi

# An absent or unrecognised mode is refused rather than assumed: the packing
# canary and the live replay reach this script by exactly the same route, and
# branching on the mode is the only thing standing between a transport
# rehearsal and an irreversible consumption of the one-shot envelope.
case "${MODE}" in
    packing-canary)
        # A rehearsal of the submission transport only. Nothing here reads or
        # writes the replay envelope, reaches the gate, or touches a model.
        #
        # The prefix absence proof is deliberately not attempted here: it needs
        # Azure credentials this task is not granted, and a probe that cannot
        # reach the control plane can only report ambiguity, never absence. It
        # runs from the host, where the credentials exist, as its own canary.
        env P0_R2_ATTEMPT= P0_R2_RUNTIME_ROOT=/tmp/p0r2-packing-canary \
            /usr/local/bin/p0_r2_canary_v2.sh preflight
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
python3 "${R2}/p0_r2_image_manifest_v2.py" \
    --audit /opt/jspace/p0_r2_image_manifest_v2.json \
    --image-root "${SRC}" \
    --install-root /usr/local/bin \
    --out "${RUNTIME}/image_audit_v2.json"
echo "P0_R2_IMAGE_TO_GIT_AUDIT_V2_COMPLETE=1"

# The active lock comes from the submitted context, verified byte for byte.
LOCK_FILE="${RUNTIME}/p0_r2_execution_lock_v2.json"
python3 - "${MANIFEST}" "${LOCK_FILE}" <<'PY'
import base64
import hashlib
import json
import sys

manifest_path, out_path = sys.argv[1], sys.argv[2]
with open(manifest_path, "rb") as handle:
    manifest = json.loads(handle.read().decode("utf-8"))

entries = [entry for entry in (manifest.get("embedded_governance_objects") or [])
           if entry.get("label") == "execution_lock"]
if len(entries) != 1:
    raise SystemExit(
        "P0_R2_REPLAY_REFUSED=1 the context embeds %d execution_lock objects; "
        "exactly one is required" % len(entries))
entry = entries[0]
payload = base64.b64decode(entry["payload"])
if len(payload) != entry["bytes"]:
    raise SystemExit("P0_R2_REPLAY_REFUSED=1 the embedded lock length disagrees")
digest = hashlib.sha256(payload).hexdigest()
if digest != entry["sha256"]:
    raise SystemExit("P0_R2_REPLAY_REFUSED=1 the embedded lock sha256 disagrees")
with open(out_path, "xb") as handle:
    handle.write(payload)
print("P0_R2_LOCK_FROM_CONTEXT_BYTES=%d" % len(payload))
print("P0_R2_LOCK_FROM_CONTEXT_SHA256=%s" % digest)
print("P0_R2_LOCK_FROM_CONTEXT_PATH=%s" % entry["source_path"])
PY
echo "P0_R2_LOCK_FROM_CONTEXT_VERIFIED=1"

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
    --lock-file "${LOCK_FILE}" \
    --root "${SRC}"

echo "P0_R2_REPLAY_GATE_RUN=true"
echo "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=true"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
echo "P0_R2_REPLAY_COMPLETE=1"
