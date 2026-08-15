#!/bin/sh
# The bounded P0-R2 generation-2 model pilot.
#
# Authority: studies/study3/prompts/
# study3_p0_r2_generation2_successor_and_conditional_execution_authority.md
# sections 14 and 15.
#
# It refuses unless everything is already true. It cannot be run by accident: it
# demands an authorization document that can only be built mechanically from a
# completed replay receipt, a verified reconstruction receipt, a published
# head proof and the pinned generation-2 lock.
#
# The science is the unchanged P0-R1 generation-3 runner. Generation 2
# contributes the namespace, the transport and the refusals, nothing else. The
# bounded maxima are enforced by the runner, not reported by this script.

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
LOCK="${P0_R2_LOCK_FILE:-${RUNTIME}/p0_r2_execution_lock_g2.json}"

refuse() {
    echo "P0_R2_G2_PILOT_REFUSED=1 $*" >&2
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
[ -n "${P0_R2_PREFIX_RECEIPT:-}" ] \
    || refuse "a fresh in-VNet pilot prefix receipt is required"
[ "${P0_R2_PILOT_AUTHORIZED:-0}" = "1" ] \
    || refuse "P0_R2_PILOT_AUTHORIZED=1 must be set explicitly"

case "${ATTEMPT}" in
    p0r2-g2-pilot-*) ;;
    *) refuse "the pilot attempt must begin p0r2-g2-pilot-" ;;
esac

mkdir -p "${RESULTS}"

echo "P0_R2_STAGE=${STAGE}"
echo "P0_R2_G2_GENERATION=2"
echo "P0_R2_ATTEMPT=${ATTEMPT}"
echo "P0_R2_IMAGE_DIGEST=${DIGEST}"

python3 "${R2}/p0_r2_image_manifest_g2.py" \
    --audit /opt/jspace/p0_r2_image_manifest_g2.json \
    --image-root "${SRC}" \
    --install-root /usr/local/bin \
    --out "${RUNTIME}/image_audit_g2.json" > /dev/null
echo "P0_R2_G2_IMAGE_TO_GIT_AUDIT_COMPLETE=1"

python3 "${R2}/p0_r2_execution_lock_g2.py" --validate --lock-file "${LOCK}" \
    > /dev/null
echo "P0_R2_G2_LOCK_VALIDATED=1"

# The pilot prefix must have been proved unused by a fresh in-VNet CPU proof.
# This container validates the bound receipt; it never lists Storage itself.
python3 "${R2}/p0_r2_prefix_proof_g2.py" \
    --validate \
    --receipt "${P0_R2_PREFIX_RECEIPT}" \
    --attempt "${ATTEMPT}" \
    --replay-mode live \
    --out "${RUNTIME}/pilot_prefix_validation_g2.json" > /dev/null
echo "P0_R2_G2_PILOT_PREFIX_VALIDATED=1"

# Build the authorization mechanically under the generation-2 identities. This
# performs zero Azure operations and refuses unless every input agrees.
python3 - "${LOCK}" "${ATTEMPT}" "${DIGEST}" \
        "${RUNTIME}/p0_r2_g2_pilot_authorization.json" <<'PYTHON'
import json
import sys

import p0_r2_namespace_g2 as NS

lock_file, attempt, digest, out_path = sys.argv[1:5]
auth = NS.authorization()
if auth.GPU_JOB != NS.GPU_JOB:
    raise SystemExit(
        "P0_R2_G2_PILOT_REFUSED=1 the authorization does not name the "
        "generation-2 GPU job")
import os

document = auth.build(
    lock_file=lock_file,
    replay_receipt=os.environ["P0_R2_REPLAY_RECEIPT"],
    reconstruction_receipt=os.environ["P0_R2_RECONSTRUCTION_RECEIPT"],
    head_proof=os.environ["P0_R2_HEAD_PROOF"],
    attempt=attempt)
if document.get("outcome") != "AUTHORIZED":
    raise SystemExit(
        "P0_R2_G2_PILOT_REFUSED=1 the authorization is %r"
        % document.get("outcome"))
payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
with open(out_path, "w", encoding="utf-8") as handle:
    handle.write(payload)
print("P0_R2_G2_AUTHORIZATION_BUILT=1")
PYTHON

# Only now may the model runner consider running. It enforces the bounded
# maxima itself; nothing here may raise them.
python3 "${R2}/p0_r2_model_runner_v1.py" --sentinel --attempt "${ATTEMPT}"

echo "P0_R2_G2_PILOT_COMPLETE=1"
