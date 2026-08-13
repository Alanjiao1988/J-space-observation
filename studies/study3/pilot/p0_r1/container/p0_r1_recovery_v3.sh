#!/usr/bin/env bash
# Study 3 P0-R1 generation-3 CPU-only private recovery entry point.
#
# This is the payload of the separately named recovery job. It exists because
# an operator workstation cannot hold the resource's managed identity and is
# outside the private endpoint, so the generation-2 handoff's "instantiate
# ManagedIdentityCredential locally" instruction could never have worked.
#
# It is not a replay and not a model retry. It reads, verifies and re-emits.
set -euo pipefail

SRC="${P0_R1_SRC:-/opt/jspace/src}"
P0_R1_DIR="$SRC/studies/study3/pilot/p0_r1"
RUNTIME_ROOT="${P0_R1_RUNTIME_ROOT:-/workspace/runtime}"
PY="${PYTHON:-python3}"

MODE="${P0_R1_RECOVERY_MODE:-recover}"
ATTEMPT="${P0_R1_ATTEMPT:-}"
LOCK_FILE="${P0_R1_LOCK_FILE:-$RUNTIME_ROOT/p0_r1_execution_lock_v3.json}"

fail() { echo "FAIL: $*" >&2; exit 1; }

[ -n "$ATTEMPT" ] || fail "P0_R1_ATTEMPT is mandatory; recovery is always \
bound to exactly one captured attempt identity"

echo "P0_R1_RECOVERY_JOB_BEGIN=1 MODE=$MODE ATTEMPT=$ATTEMPT"

case "$MODE" in
  prefix-preflight)
    # Proves the attempt prefix and every reserved object name absent, from
    # inside the network, BEFORE any GPU job is created.
    exec "$PY" "$P0_R1_DIR/p0_r1_prefix_preflight_v3.py" --probe \
      --attempt "$ATTEMPT"
    ;;
  recover)
    if [ ! -f "$LOCK_FILE" ]; then
      "$PY" "$P0_R1_DIR/p0_r1_authorization_v3.py" --reconstruct \
        --out-dir "$RUNTIME_ROOT" --require lock \
        || fail "the active generation-3 lock could not be reconstructed"
    fi
    [ -f "$LOCK_FILE" ] || fail "recovery requires the active lock bytes"
    exec "$PY" "$P0_R1_DIR/p0_r1_recovery_v3.py" --recover \
      --attempt "$ATTEMPT" --lock-file "$LOCK_FILE"
    ;;
  *)
    fail "unknown recovery mode $MODE; expected prefix-preflight or recover"
    ;;
esac
