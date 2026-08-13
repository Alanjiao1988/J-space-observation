#!/usr/bin/env bash
# Study 3 P0-R1 generation-3 model pilot entry point.
#
# This is the exact command the GPU job runs, and it is exercised end to end by
# a seam test with a sentinel executor. Generation 2's equivalent invoked the
# runner without an authorization and without --blob, so the real job would
# have refused itself and, had it not, would have journaled only to a
# filesystem that dies with the replica.
#
# Everything here is mandatory. There is no default lock, no default receipt,
# no optional durability and no path that reaches a model with an argument
# missing.
set -euo pipefail

SRC="${P0_R1_SRC:-/opt/jspace/src}"
P0_R1_DIR="$SRC/studies/study3/pilot/p0_r1"
RUNTIME_ROOT="${P0_R1_RUNTIME_ROOT:-/workspace/runtime}"
OUT_DIR="${P0_R1_OUT_DIR:-$RUNTIME_ROOT/result}"
PY="${PYTHON:-python3}"

LOCK_FILE="${P0_R1_LOCK_FILE:-$RUNTIME_ROOT/p0_r1_execution_lock_v3.json}"
REPLAY_RECEIPT="${P0_R1_REPLAY_RECEIPT:-$RUNTIME_ROOT/p0_r1_replay_receipt.json}"
RECONSTRUCTION_RECEIPT="${P0_R1_RECONSTRUCTION_RECEIPT:-$RUNTIME_ROOT/p0_r1_replay_reconstruction_receipt_v3.json}"
HEAD_PROOF="${P0_R1_HEAD_PROOF:-$RUNTIME_ROOT/p0_r1_head_proof_v3.json}"
EXECUTOR="${P0_R1_EXECUTOR:-production}"

fail() { echo "FAIL: $*" >&2; exit 1; }

# The EXIT trap is a real durability boundary, not a decoration. It serializes
# the most conservative receipt it can build and pushes it out over BOTH
# routes: the private object store and the bounded console envelope. Generation
# 2's trap wrote one file to an ephemeral directory and printed a hash.
on_exit() {
  local code=$?
  set +e
  echo "P0_R1_PILOT_SHELL_EXIT=$code"
  "$PY" "$P0_R1_DIR/p0_r1_infrastructure_receipt_v3.py" \
    --emit --exit-code "$code" --out-dir "$OUT_DIR" \
    --attempt "${P0_R1_ATTEMPT:-unknown}" \
    --lock-file "$LOCK_FILE" 2>&1 || echo "P0_R1_DURABILITY_DEGRADED=1"
  echo "P0_R1_PILOT_SHELL_TRAP_COMPLETE=1"
  exit "$code"
}
trap on_exit EXIT

mkdir -p "$OUT_DIR"

for required in "$LOCK_FILE" "$REPLAY_RECEIPT" "$RECONSTRUCTION_RECEIPT" \
                "$HEAD_PROOF"; do
  [ -f "$required" ] || fail "the injected input $required is missing; the \
generation-3 pilot has no default authorization input"
done

echo "P0_R1_PILOT_INPUTS_PRESENT=1"
echo "P0_R1_PILOT_EXECUTOR=$EXECUTOR"

# Every input is passed explicitly. The runner builds the authorization from
# these exact bytes; there is no in-process shortcut a test could take that
# production does not.
exec "$PY" "$P0_R1_DIR/p0_r1_model_runner_v3.py" --run \
  --lock-file "$LOCK_FILE" \
  --replay-receipt "$REPLAY_RECEIPT" \
  --reconstruction-receipt "$RECONSTRUCTION_RECEIPT" \
  --head-proof "$HEAD_PROOF" \
  --out-dir "$OUT_DIR" \
  --src "$SRC" \
  --executor "$EXECUTOR" \
  ${P0_R1_ATTEMPT:+--attempt "$P0_R1_ATTEMPT"} \
  ${P0_R1_IMAGE_DIGEST:+--image-digest "$P0_R1_IMAGE_DIGEST"}
