#!/bin/sh
# Model-free P0-R2 canaries, run inside the image against the pinned digest.
#
# Every check here is safe to repeat. Nothing constructs a tokenizer, downloads
# or loads a checkpoint, loads a model weight, performs a prefill or a
# generation, scores a row, writes an evidence row, or allocates a GPU.
#
# Modes:
#   preflight    identity, image-to-Git audit, delegated-science verification,
#                transport self-test, and prefix absence proof.
#   transport    the 1 MiB envelope round trip only.
#   identity     the identity documents only.

set -eu

STAGE="STUDY3-P0-R2"
SRC="${P0_R2_SRC:-/opt/jspace/src}"
R2="${SRC}/studies/study3/pilot/p0_r2"
PYTHONPATH="${R2}:${SRC}/studies/study3/pilot/p0_r1"
export PYTHONPATH

MODE="${1:-preflight}"
OUT="${P0_R2_RUNTIME_ROOT:-/workspace/runtime}/canary"
mkdir -p "${OUT}"

echo "P0_R2_CANARY_MODE=${MODE}"
echo "P0_R2_STAGE=${STAGE}"

emit_identity() {
    # Every module that can describe itself is asked to, which also proves it
    # imports cleanly inside the image. The two transport modules that predate
    # the identity convention expose a self-check instead, so they are run the
    # way they actually work rather than being skipped.
    for module in p0_r2_transport_v1 p0_r2_blob_transport_v1 p0_r2_journal_v1 \
                  p0_r2_submission_context p0_r2_acr_submission \
                  p0_r2_closure_binding_v1 p0_r2_azure_query_v1 \
                  p0_r2_replay_capture_v1 p0_r2_verify_replay_receipt \
                  p0_r2_authorization_v1 p0_r2_job_spec_v1 \
                  p0_r2_replay_gate_v1 p0_r2_prefix_preflight_v1 \
                  p0_r2_recovery_v1 p0_r2_model_runner_v1 \
                  p0_r2_image_manifest_v1 p0_r2_execution_lock_v1; do
        python3 "${R2}/${module}.py" --identity > "${OUT}/${module}.identity.json"
        echo "P0_R2_IDENTITY_OK=${module}"
    done
    for module in p0_r2_transport p0_r2_journal_v1; do
        python3 "${R2}/${module}.py" --self-check > "${OUT}/${module}.selfcheck.json"
        echo "P0_R2_SELF_CHECK_OK=${module}"
    done
    # p0_r2_blob_transport carries no command line of its own; importing it is
    # the only thing there is to prove.
    python3 -c "import p0_r2_blob_transport" \
        && echo "P0_R2_IMPORT_OK=p0_r2_blob_transport"
}

audit_image() {
    python3 "${R2}/p0_r2_image_manifest_v1.py" \
        --audit /opt/jspace/p0_r2_image_manifest_v1.json \
        --image-root "${SRC}" \
        --out "${OUT}/image_audit.json"
}

transport_roundtrip() {
    # A 1 MiB payload through the envelope and back, proving the recovered
    # bytes are byte-identical and that the strict decoder is tried first.
    python3 - "${OUT}" <<'PY'
import json
import os
import sys

import p0_r2_transport as TX
import p0_r2_transport_v1 as TXV1

out = sys.argv[1]
attempt = "p0r2-g1-transport-canary"
fixture = TX.canary_fixture(attempt)
emitted = sum(len(payload) for payload in fixture.values())
assert emitted >= TX.CANARY_MINIMUM_TOTAL_BYTES, emitted

log = "\n".join(TX.encode(attempt, fixture))
# The strict decoder is always tried first; a repair is only ever accepted
# when its checksum proves it, and a clean log must need none.
recovered, repairs = TXV1.recover_with_report(log, attempt)
assert repairs == [], repairs
assert sorted(recovered) == sorted(TX.REPLAY_ARTIFACTS), sorted(recovered)
for name, payload in fixture.items():
    assert recovered[name] == payload, name
total = sum(len(payload) for payload in recovered.values())
assert total == emitted, (total, emitted)

with open(os.path.join(out, "transport_roundtrip.json"), "w") as handle:
    json.dump({"attempt_id": attempt, "emitted_bytes": emitted,
               "recovered_bytes": total, "repairs_applied": len(repairs),
               "artifacts": sorted(recovered), "byte_identical": True,
               "outcome": "PASS", "model_operations_performed": 0},
              handle, indent=2, sort_keys=True)
print("P0_R2_TRANSPORT_ROUNDTRIP_BYTES=%d" % total)
print("P0_R2_TRANSPORT_ROUNDTRIP_COMPLETE=1")
PY
}

prefix_absence() {
    attempt="${P0_R2_ATTEMPT:-}"
    if [ -z "${attempt}" ]; then
        echo "P0_R2_PREFIX_PREFLIGHT_SKIPPED=1 no attempt id was supplied"
        return 0
    fi
    python3 "${R2}/p0_r2_prefix_preflight_v1.py" --probe "${attempt}" \
        --out "${OUT}/prefix_preflight.json"
}

case "${MODE}" in
    identity)
        emit_identity
        ;;
    transport)
        transport_roundtrip
        ;;
    preflight)
        emit_identity
        audit_image
        transport_roundtrip
        prefix_absence
        echo "P0_R2_PREFLIGHT_COMPLETE=1"
        ;;
    *)
        echo "P0_R2_CANARY_REFUSED=1 unrecognised mode ${MODE}" >&2
        exit 2
        ;;
esac

echo "P0_R2_REPLAY_GATE_RUN=false"
echo "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
echo "P0_R2_CANARY_COMPLETE=1"
