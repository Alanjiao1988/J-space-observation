#!/bin/sh
# Study 3 P0-R2 generation-2 replay entry point.
#
# Authority: studies/study3/prompts/
# study3_p0_r2_generation2_successor_and_conditional_execution_authority.md
# sections 6.2, 6.3 and 11.
#
# Generation 1 failed here. Its live branch called the in-container prefix
# preflight, which needs a managed identity and a route into the VNet that an
# ACR Tasks agent does not have, and its canary branch skipped that step
# entirely. The canary therefore could not rehearse the only step that mattered.
#
# Generation 2 removes the asymmetry. Both modes run exactly the same
# admission sequence against exactly the same bound host receipt, through the
# one shared validator, and only then does the mode select what happens next.
# Nothing in this script contacts Storage, requests a managed-identity token,
# or opens a private endpoint.

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
RECEIPT_SHA="${P0_R2_PREFIX_RECEIPT_SHA256:-}"

if [ -z "${ATTEMPT}" ]; then
    echo "P0_R2_G2_REPLAY_REFUSED=1 P0_R2_ATTEMPT is required" >&2
    exit 2
fi
if [ -z "${DIGEST}" ]; then
    echo "P0_R2_G2_REPLAY_REFUSED=1 P0_R2_IMAGE_DIGEST is required" >&2
    exit 2
fi
if [ -z "${MODE}" ]; then
    echo "P0_R2_G2_REPLAY_REFUSED=1 P0_R2_REPLAY_MODE is required" >&2
    exit 2
fi

case "${MODE}" in
    canary|live) ;;
    *)
        echo "P0_R2_G2_REPLAY_REFUSED=1 unrecognised mode ${MODE}" >&2
        exit 2
        ;;
esac

mkdir -p "${RUNTIME}" "${RESULTS}"

echo "P0_R2_STAGE=${STAGE}"
echo "P0_R2_G2_GENERATION=2"
echo "P0_R2_G2_MODE=${MODE}"
echo "P0_R2_ATTEMPT=${ATTEMPT}"
echo "P0_R2_IMAGE_DIGEST=${DIGEST}"

# 1. Image-to-Git audit. Every bound byte in this image must equal the Git blob
#    the generation-2 manifest names.
python3 "${R2}/p0_r2_image_manifest_g2.py" \
    --audit /opt/jspace/p0_r2_image_manifest_g2.json \
    --image-root "${SRC}" \
    --install-root /usr/local/bin \
    --out "${RUNTIME}/image_audit_g2.json"
echo "P0_R2_G2_IMAGE_TO_GIT_AUDIT_COMPLETE=1"

# 2. Take the execution lock from the submitted context, not from the image.
LOCK_FILE="${RUNTIME}/p0_r2_execution_lock_g2.json"
python3 - "${MANIFEST}" "${LOCK_FILE}" <<'PYTHON'
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
        "P0_R2_G2_REPLAY_REFUSED=1 the context embeds %d execution_lock "
        "objects; exactly one is required" % len(entries))
entry = entries[0]
payload = base64.b64decode(entry["payload"])
if len(payload) != entry["bytes"]:
    raise SystemExit("P0_R2_G2_REPLAY_REFUSED=1 the embedded lock length disagrees")
digest = hashlib.sha256(payload).hexdigest()
if digest != entry["sha256"]:
    raise SystemExit("P0_R2_G2_REPLAY_REFUSED=1 the embedded lock sha256 disagrees")
with open(out_path, "xb") as handle:
    handle.write(payload)
print("P0_R2_G2_LOCK_FROM_CONTEXT_BYTES=%d" % len(payload))
print("P0_R2_G2_LOCK_FROM_CONTEXT_SHA256=%s" % digest)
print("P0_R2_G2_LOCK_FROM_CONTEXT_PATH=%s" % entry["source_path"])
PYTHON
echo "P0_R2_G2_LOCK_FROM_CONTEXT_VERIFIED=1"

# 3. The one shared prefix-receipt validation. Identical arguments in both
#    modes, identical implementation, and it prints the deferral marker exactly
#    once. There is no in-container Storage listing and no token request.
python3 "${R2}/p0_r2_prefix_proof_g2.py" \
    --validate-bound \
    --context-manifest "${MANIFEST}" \
    --attempt "${ATTEMPT}" \
    --replay-mode "${MODE}" \
    --out "${RUNTIME}/prefix_validation_g2.json"

if [ -n "${RECEIPT_SHA}" ]; then
    python3 - "${RUNTIME}/prefix_validation_g2.json" "${RECEIPT_SHA}" <<'PYTHON'
import json
import sys

with open(sys.argv[1], "rb") as handle:
    report = json.loads(handle.read().decode("utf-8"))
if report.get("receipt_sha256") != sys.argv[2]:
    raise SystemExit(
        "P0_R2_G2_REPLAY_REFUSED=1 the bound prefix receipt %s is not the "
        "receipt the host submitted (%s)"
        % (report.get("receipt_sha256"), sys.argv[2]))
print("P0_R2_G2_PREFIX_RECEIPT_MATCHES_SUBMISSION=1")
PYTHON
fi
echo "P0_R2_G2_PREFIX_RECEIPT_VALIDATED=1"

if [ "${MODE}" = "canary" ]; then
    # The canary rehearses everything above and then stops. It never imports or
    # invokes the replay gate, and it consumes no envelope.
    /usr/local/bin/p0_r2_canary_g2.sh preflight
    echo "P0_R2_G2_PACKING_CANARY_ATTEMPT=${ATTEMPT}"
    echo "P0_R2_G2_REPLAY_GATE_RUN=false"
    echo "P0_R2_G2_ONE_SHOT_ENVELOPE_CONSUMED=false"
    echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
    echo "P0_R2_G2_PACKING_CANARY_COMPLETE=1"
    exit 0
fi

# 4. Live only: invoke the registered replay gate exactly once.
python3 "${R2}/p0_r2_replay_gate_v1.py" \
    --run \
    --out-dir "${RESULTS}" \
    --attempt "${ATTEMPT}" \
    --image-digest "${DIGEST}" \
    --ready-anchor "${P0_R2_READY_COMMIT:-}" \
    --lock-file "${LOCK_FILE}" \
    --root "${SRC}"

echo "P0_R2_G2_REPLAY_GATE_RUN=true"
echo "P0_R2_G2_ONE_SHOT_ENVELOPE_CONSUMED=true"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
echo "P0_R2_G2_REPLAY_COMPLETE=1"
