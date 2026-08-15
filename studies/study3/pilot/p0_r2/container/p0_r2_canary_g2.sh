#!/bin/sh
# Study 3 P0-R2 generation-2 model-free canary.
#
# Authority: studies/study3/prompts/
# study3_p0_r2_generation2_successor_and_conditional_execution_authority.md
# sections 6.3 and 7.3.
#
# This rehearses everything the live path does except the replay gate itself.
# It never imports or invokes the gate, never consumes an envelope, never
# constructs a tokenizer, never touches a checkpoint or a weight, and never
# allocates a GPU.
#
# Identity documents are written to files rather than stdout on purpose. An
# identity dump that quoted a marker string would make the execution log look as
# though a marker occurred more than once, and the packing canary is required to
# prove that each marker occurs exactly once.

set -eu

STAGE="STUDY3-P0-R2"
SRC="${P0_R2_SRC:-/opt/jspace/src}"
R2="${SRC}/studies/study3/pilot/p0_r2"
PYTHONPATH="${R2}:${SRC}/studies/study3/pilot/p0_r1"
export PYTHONPATH

MODE="${1:-preflight}"
OUT="${P0_R2_RUNTIME_ROOT:-/workspace/runtime}/canary_g2"
mkdir -p "${OUT}"

echo "P0_R2_G2_CANARY_MODE=${MODE}"
echo "P0_R2_G2_GENERATION=2"
echo "P0_R2_STAGE=${STAGE}"

emit_identity() {
    for module in \
        p0_r2_namespace_g2 \
        p0_r2_prefix_proof_g2 \
        p0_r2_image_manifest_g2 \
        p0_r2_execution_lock_g2 \
        p0_r2_closure_binding_g2 \
        p0_r2_replay_gate_g2 \
        p0_r2_transport \
        p0_r2_transport_v1 \
        p0_r2_blob_transport_v1 \
        p0_r2_journal_v1 \
        p0_r2_recovery_v1 \
        p0_r2_replay_gate_v1 \
        p0_r2_model_runner_v1
    do
        python3 "${R2}/${module}.py" --identity > "${OUT}/${module}.identity.json"
        echo "P0_R2_G2_IDENTITY_OK=${module}"
    done
    python3 "${R2}/p0_r2_namespace_g2.py" --self-check > "${OUT}/namespace_self_check.txt"
    echo "P0_R2_G2_SELF_CHECK_OK=p0_r2_namespace_g2"
    python3 -c "import p0_r2_blob_transport" \
        && echo "P0_R2_G2_IMPORT_OK=p0_r2_blob_transport"
}

audit_image() {
    python3 "${R2}/p0_r2_image_manifest_g2.py" \
        --audit /opt/jspace/p0_r2_image_manifest_g2.json \
        --image-root "${SRC}" \
        --install-root /usr/local/bin \
        --out "${OUT}/image_audit_g2.json" > /dev/null
    echo "P0_R2_G2_IMAGE_AUDIT_OK=1"
}

transport_roundtrip() {
    python3 - "${OUT}" <<'PYTHON'
import json
import os
import sys

import p0_r2_namespace_g2 as NS

out = sys.argv[1]
attempt = "%stransport-roundtrip" % NS.CANARY_ATTEMPT_PREFIX
transport = NS.transport()
decoder = NS.strict_decoder()

fixture = transport.canary_fixture(attempt)
emitted = sum(len(payload) for payload in fixture.values())
assert emitted >= transport.CANARY_MINIMUM_TOTAL_BYTES, emitted

log = "\n".join(transport.encode(attempt, fixture))
recovered, repairs = decoder.recover_with_report(log, attempt)
assert repairs == [], repairs
assert sorted(recovered) == sorted(transport.REPLAY_ARTIFACTS), sorted(recovered)
for name, payload in fixture.items():
    assert recovered[name] == payload, name
total = sum(len(payload) for payload in recovered.values())
assert total == emitted, (total, emitted)

# The generation-1 namespace must still refuse a generation-2 attempt.
import p0_r2_transport as G1

try:
    G1.validate_attempt_id(attempt)
except G1.TransportDefect:
    disjoint = True
else:
    raise AssertionError("generation 1 accepted a generation-2 attempt")

with open(os.path.join(out, "transport_roundtrip_g2.json"), "w") as handle:
    json.dump({"attempt_id": attempt, "emitted_bytes": emitted,
               "recovered_bytes": total, "repairs_applied": len(repairs),
               "artifacts": sorted(recovered), "byte_identical": True,
               "namespaces_disjoint": disjoint,
               "outcome": "PASS", "model_operations_performed": 0},
              handle, indent=2, sort_keys=True)
print("P0_R2_G2_TRANSPORT_ROUNDTRIP_BYTES=%d" % total)
print("P0_R2_G2_TRANSPORT_ROUNDTRIP_COMPLETE=1")
PYTHON
}

no_storage_reachback() {
    # The generation-2 container must not attempt a managed-identity token
    # request, a Storage listing or a private-endpoint connection. Proving that
    # by absence of a call is weak, so the canary instead proves the container
    # path has no code route to one: the only prefix entry point it carries
    # refuses without a bound host receipt.
    python3 - <<'PYTHON'
import p0_r2_prefix_proof_g2 as PP

identity = PP.implementation_identity()
assert identity["shared_by_canary_and_live"] is True
assert identity["separate_canary_and_live_validators"] is False
assert identity["query_error_is_absence"] is False
assert identity["writes_objects"] is False
try:
    PP.validate_bound_receipt({}, attempt_id="p0r2-g2-live-x", mode="live")
except PP.PrefixProofDefect:
    pass
else:
    raise AssertionError("a missing receipt was accepted")
print("P0_R2_G2_NO_IN_CONTAINER_STORAGE_CALL=1")
PYTHON
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
        no_storage_reachback
        echo "P0_R2_G2_PREFLIGHT_COMPLETE=1"
        ;;
    *)
        echo "P0_R2_G2_CANARY_REFUSED=1 unrecognised mode ${MODE}" >&2
        exit 2
        ;;
esac

echo "P0_R2_G2_CANARY_GATE_RUN=false"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
echo "P0_R2_G2_CANARY_COMPLETE=1"
