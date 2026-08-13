#!/usr/bin/env bash
# Study 3 P0-R1 generation-3 replay entry point (CPU-only, model-free).
#
# Runs the registered replay-only factorization gate inside the locked image
# and emits every canonical artifact through the complete-byte console
# envelope, so the operator can reconstruct the four files from the captured
# run log alone.
#
# It deliberately does NOT rewrite its own receipt to say that a later recovery
# succeeded. The emitted receipt is the exact byte sequence the gate produced;
# proof of recovery is a separate document, built afterwards by a different
# process from the captured log.
set -euo pipefail

SRC="${P0_R1_SRC:-/opt/jspace/src}"
P0_R1_DIR="$SRC/studies/study3/pilot/p0_r1"
RUNTIME_ROOT="${P0_R1_RUNTIME_ROOT:-/workspace/runtime}"
OUT_DIR="${P0_R1_OUT_DIR:-$RUNTIME_ROOT/replay}"
PY="${PYTHON:-python3}"

LOCK_FILE="${P0_R1_LOCK_FILE:-$RUNTIME_ROOT/p0_r1_execution_lock_v3.json}"

fail() { echo "FAIL: $*" >&2; exit 1; }

on_exit() {
  local code=$?
  set +e
  echo "P0_R1_REPLAY_SHELL_EXIT=$code"
  "$PY" "$P0_R1_DIR/container/p0_r1_infrastructure_receipt_v3.py" \
    --emit --exit-code "$code" --out-dir "$OUT_DIR" \
    --attempt "${P0_R1_ATTEMPT:-unknown}" --lock-file "$LOCK_FILE" \
    2>&1 || echo "P0_R1_DURABILITY_DEGRADED=1"
  exit "$code"
}
trap on_exit EXIT

mkdir -p "$OUT_DIR"
[ -f "$LOCK_FILE" ] || fail "the injected execution lock $LOCK_FILE is missing"

echo "P0_R1_REPLAY_BEGIN=1"
echo "P0_R1_REPLAY_IMAGE_DIGEST=${P0_R1_IMAGE_DIGEST:-unset}"

exec "$PY" "$P0_R1_DIR/p0_r1_replay_gate_v3.py" --gate \
  --lock-file "$LOCK_FILE" \
  --out-dir "$OUT_DIR" \
  --src "$SRC" \
  ${P0_R1_IMAGE_DIGEST:+--image-digest "$P0_R1_IMAGE_DIGEST"} \
  ${P0_R1_READY_COMMIT:+--ready-commit "$P0_R1_READY_COMMIT"}
