#!/usr/bin/env bash
# Study 3 P0-R1 generation-3 model-free canaries.
#
# Every canary here is CPU-only, allocates no accelerator, constructs no
# tokenizer, downloads no checkpoint and performs no model operation. They run
# against the real production paths, because the generation-2 lesson is that a
# gate exercising an in-memory stand-in passes identically whether or not the
# image can reach the storage account.
set -euo pipefail

SRC="${P0_R1_SRC:-/opt/jspace/src}"
P0_R1_DIR="$SRC/studies/study3/pilot/p0_r1"
PY="${PYTHON:-python3}"
ATTEMPT="${P0_R1_ATTEMPT:-g3canary-local}"
MODE="${1:-all}"

echo "P0_R1_G3_CANARY_BEGIN=1 MODE=$MODE ATTEMPT=$ATTEMPT"

canary_layout() {
  echo "--- canary 1: standalone layout, no context mount ---"
  [ -d "$P0_R1_DIR" ] || { echo "FAIL: $P0_R1_DIR absent" >&2; exit 1; }
  for entry in /usr/local/bin/p0_r1_model_pilot_v3.sh \
               /usr/local/bin/p0_r1_replay_v3.sh \
               /usr/local/bin/p0_r1_recovery_v3.sh; do
    [ -x "$entry" ] || { echo "FAIL: entry point $entry missing" >&2; exit 1; }
  done
  "$PY" "$P0_R1_DIR/p0_r1_model_runner_v3.py" --identity >/dev/null
  "$PY" "$P0_R1_DIR/p0_r1_recovery_v3.py" --identity >/dev/null
  echo "P0_R1_G3_STANDALONE_LAYOUT=1"
}

canary_cli_wiring() {
  echo "--- canary 2: the exact shell reaches the authorized boundary once ---"
  "$PY" "$P0_R1_DIR/container/p0_r1_cli_wiring_canary_v3.py" --run
  echo "P0_R1_G3_CLI_WIRING=1"
}

canary_transport() {
  echo "--- canary 3: complete-byte replay transport ---"
  "$PY" "$P0_R1_DIR/p0_r1_transport.py" --self-check
  echo "P0_R1_G3_TRANSPORT=1"
}

canary_journal() {
  echo "--- canary 4: Blob-primary journal, recursive manifest, recovery ---"
  "$PY" "$P0_R1_DIR/p0_r1_journal_v3.py" --self-check
  "$PY" "$P0_R1_DIR/p0_r1_recovery_v3.py" --self-check
  echo "P0_R1_G3_JOURNAL=1"
}

canary_private_blob() {
  echo "--- canary 5: private object store, real managed identity ---"
  "$PY" "$P0_R1_DIR/p0_r1_blob_transport.py" --verify-production-backend
  "$PY" "$P0_R1_DIR/container/p0_r1_private_journal_canary_v3.py" \
    --attempt "$ATTEMPT"
  echo "P0_R1_G3_PRIVATE_BLOB=1"
}

canary_hard_kill() {
  echo "--- canary 6: hard kill leaves the emitted row recoverable ---"
  "$PY" "$P0_R1_DIR/container/p0_r1_hard_kill_canary_v3.py" \
    --attempt "${ATTEMPT}-hardkill"
  echo "P0_R1_G3_HARD_KILL=1"
}

case "$MODE" in
  layout) canary_layout ;;
  cli) canary_cli_wiring ;;
  transport) canary_transport ;;
  journal) canary_journal ;;
  blob) canary_private_blob ;;
  hardkill) canary_hard_kill ;;
  build)
    # The build-time subset: everything that does not need the private VNet.
    canary_layout; canary_cli_wiring; canary_transport; canary_journal ;;
  all)
    canary_layout; canary_cli_wiring; canary_transport; canary_journal
    canary_private_blob; canary_hard_kill ;;
  *) echo "FAIL: unknown canary mode $MODE" >&2; exit 2 ;;
esac

echo "P0_R1_G3_CANARY_COMPLETE=1"
