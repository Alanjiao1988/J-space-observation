#!/bin/sh
# Model-free P0-R2 canaries for the corrected image, run against the pinned
# digest.
#
# This is p0_r2_canary_v1.sh with exactly one thing changed: the image-to-Git
# audit reads the v2 manifest, because the corrected image carries the v2
# manifest and not the v1 one. Pointing the v1 canary at a manifest the image
# does not carry would have failed loudly, which is correct; quietly copying the
# v2 manifest to the v1 name so the old canary "passed" would have been the
# dishonest repair.
#
# Every check here is safe to repeat. Nothing constructs a tokenizer, downloads
# or loads a checkpoint, loads a model weight, performs a prefill or a
# generation, scores a row, writes an evidence row, or allocates a GPU.
#
# Modes:
#   preflight    identity, v2 image-to-Git audit, transport self-test and
#                prefix absence proof.
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
echo "P0_R2_CANARY_REVISION=2"
echo "P0_R2_STAGE=${STAGE}"

emit_identity() {
    for module in p0_r2_transport_v1 p0_r2_blob_transport_v1 p0_r2_journal_v1 \
                  p0_r2_submission_context p0_r2_acr_submission \
                  p0_r2_closure_binding_v1 p0_r2_closure_binding_v2 \
                  p0_r2_azure_query_v1 \
                  p0_r2_replay_capture_v1 p0_r2_verify_replay_receipt \
                  p0_r2_authorization_v1 p0_r2_job_spec_v1 \
                  p0_r2_replay_gate_v1 p0_r2_prefix_preflight_v1 \
                  p0_r2_recovery_v1 p0_r2_model_runner_v1 \
                  p0_r2_image_manifest_v1 p0_r2_image_manifest_v2 \
                  p0_r2_execution_lock_v1 p0_r2_execution_lock_v2 \
                  p0_r2_host_preflight_v2 p0_r2_hard_kill_canary_v2 \
                  p0_r2_attempt_ledger_v2; do
        python3 "${R2}/${module}.py" --identity > "${OUT}/${module}.identity.json"
        echo "P0_R2_IDENTITY_OK=${module}"
    done
    for module in p0_r2_transport p0_r2_journal_v1; do
        python3 "${R2}/${module}.py" --self-check > "${OUT}/${module}.selfcheck.json"
        echo "P0_R2_SELF_CHECK_OK=${module}"
    done
    python3 -c "import p0_r2_blob_transport" \
        && echo "P0_R2_IMPORT_OK=p0_r2_blob_transport"
}

audit_image() {
    python3 "${R2}/p0_r2_image_manifest_v2.py" \
        --audit /opt/jspace/p0_r2_image_manifest_v2.json \
        --image-root "${SRC}" \
        --install-root /usr/local/bin \
        --out "${OUT}/image_audit_v2.json"
}

transport_roundtrip() {
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
