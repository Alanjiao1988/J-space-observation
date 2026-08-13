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
MODE="${P0_R1_REPLAY_MODE:-}"

LOCK_FILE="${P0_R1_LOCK_FILE:-$RUNTIME_ROOT/p0_r1_execution_lock_v3.json}"

fail() { echo "FAIL: $*" >&2; exit 1; }

on_exit() {
  local code=$?
  set +e
  echo "P0_R1_REPLAY_SHELL_EXIT=$code"
  if [ "$MODE" = "transport-canary" ]; then
    echo "P0_R1_REPLAY_CANARY_TRAP=skipped-no-live-attempt"
    exit "$code"
  fi
  if [ "$code" -eq 0 ]; then
    echo "P0_R1_REPLAY_SUCCESS_TRAP=skipped-gate-envelope-is-complete"
    exit 0
  fi
  local attempt=""
  if [ -f "$OUT_DIR/p0_r1_replay_receipt.json" ]; then
    attempt="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["attempt_id"])' \
      "$OUT_DIR/p0_r1_replay_receipt.json" 2>/dev/null)"
  fi
  attempt="${attempt:-${P0_R1_ATTEMPT:-}}"
  attempt="${attempt:-unknown}"
  "$PY" "$P0_R1_DIR/container/p0_r1_infrastructure_receipt_v3.py" \
    --emit --exit-code "$code" --out-dir "$OUT_DIR" \
    --attempt "$attempt" --lock-file "$LOCK_FILE" \
    2>&1 || echo "P0_R1_DURABILITY_DEGRADED=1"
  exit "$code"
}
trap on_exit EXIT

case "$MODE" in
  live|transport-canary) ;;
  *) fail "P0_R1_REPLAY_MODE must be live or transport-canary" ;;
esac

mkdir -p "$OUT_DIR" "$RUNTIME_ROOT/cache/tmp" "$RUNTIME_ROOT/injected"
if [ ! -f "$LOCK_FILE" ]; then
  "$PY" "$P0_R1_DIR/p0_r1_authorization_v3.py" --reconstruct \
    --out-dir "$RUNTIME_ROOT" --require lock \
    || fail "the exact generation-3 lock could not be reconstructed"
fi
[ -f "$LOCK_FILE" ] || fail "the injected execution lock $LOCK_FILE is missing"

echo "P0_R1_REPLAY_BEGIN=1 MODE=$MODE"
echo "P0_R1_REPLAY_IMAGE_DIGEST=${P0_R1_IMAGE_DIGEST:-unset}"

if [ "$MODE" = "transport-canary" ]; then
  case "${P0_R1_ATTEMPT:-}" in
    gen3-transport-canary-*) ;;
    *) fail "transport-canary requires a disjoint gen3-transport-canary-* id" ;;
  esac
  "$PY" "$P0_R1_DIR/p0_r1_execution_lock_v3.py" --validate \
    --lock-file "$LOCK_FILE" \
    ${P0_R1_IMAGE_DIGEST:+--image-digest "$P0_R1_IMAGE_DIGEST"} \
    >/dev/null || fail "the injected canary lock is invalid"
  fixture="$OUT_DIR/fixture"
  mkdir -p "$fixture"
  "$PY" "$P0_R1_DIR/p0_r1_transport.py" --canary-fixture \
    --attempt "$P0_R1_ATTEMPT" --out-dir "$fixture"
  "$PY" "$P0_R1_DIR/p0_r1_transport.py" --emit \
    --attempt "$P0_R1_ATTEMPT" --in-dir "$fixture"
  echo "P0_R1_REPLAY_GATE_RUN=false"
  echo "P0_R1_ONE_SHOT_ENVELOPE_CONSUMED=false"
  echo "P0_R1_EXACT_ACR_TASK_CANARY=passed"
  exit 0
fi

"$PY" "$P0_R1_DIR/p0_r1_replay_gate_v3.py" --gate \
  --lock-file "$LOCK_FILE" --out-dir "$OUT_DIR" --src "$SRC" \
  ${P0_R1_IMAGE_DIGEST:+--image-digest "$P0_R1_IMAGE_DIGEST"} \
  ${P0_R1_READY_COMMIT:+--ready-commit "$P0_R1_READY_COMMIT"}
