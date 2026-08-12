#!/usr/bin/env bash
# Study 3 P0-R1 generation-2 successor-session orchestrator.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md
#   section 9.
#
# THE PREFLIGHT MODE IS THE ONLY MODE AUTHORIZED IN THIS ROUND.
#
# Generation 1 left the successor with a prose handoff describing several
# commands, and prose is exactly where a live replay gate gets confused for a
# dry run. This script replaces that ambiguity with three explicitly named,
# mutually exclusive modes. There is no default mode: invoking this script with
# no mode prints usage and exits non-zero.
#
#   preflight       Model-free. Verifies the published lock, the image binding
#                   and the transport, and touches nothing live. Safe to repeat.
#
#   live-replay     Runs the REGISTERED LIVE REPLAY GATE. This is a real,
#                   state-advancing scientific action that consumes the one-shot
#                   replay envelope. It is NOT a dry run.
#
#   launch-pilot    Starts the ONE model-operating GPU execution. Authorized
#                   only after live-replay passed in this same session.
set -euo pipefail

SRC="${P0_R1_SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)}"
MODE="${1:-}"
shift || true

usage() {
  cat >&2 <<'USAGE'
usage: p0_r1_successor.sh <mode> [options]

modes:
  preflight     --lock-file <path> [--image-digest sha256:<64hex>]
                Model-free verification. Constructs no tokenizer, encodes
                nothing, downloads and loads no checkpoint, allocates no GPU
                workload, performs no model operation and consumes nothing.
                Safe to run repeatedly.

  live-replay   --lock-file <path> --image-digest sha256:<64hex>
                --ready-commit <40hex>
                --confirm-consumes-the-one-shot-replay-envelope
                RUNS THE REGISTERED LIVE REPLAY GATE. This advances state and
                consumes the one-shot envelope. It is not a dry run and it is
                not repeatable.

  launch-pilot  --lock-file <path> --receipt-file <path>
                --image-digest sha256:<64hex> --ready-commit <40hex>
                --confirm-single-model-operating-execution
                Starts the ONE model-operating GPU execution. Authorized only
                after live-replay passed in this same session.

There is no default mode.
USAGE
}

LOCK_FILE=""
RECEIPT_FILE=""
IMAGE_DIGEST=""
READY_COMMIT=""
CONFIRM_REPLAY=""
CONFIRM_PILOT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --lock-file) LOCK_FILE="${2:-}"; shift 2 ;;
    --receipt-file) RECEIPT_FILE="${2:-}"; shift 2 ;;
    --image-digest) IMAGE_DIGEST="${2:-}"; shift 2 ;;
    --ready-commit) READY_COMMIT="${2:-}"; shift 2 ;;
    --src) SRC="${2:-}"; shift 2 ;;
    --confirm-consumes-the-one-shot-replay-envelope) CONFIRM_REPLAY="yes"; shift ;;
    --confirm-single-model-operating-execution) CONFIRM_PILOT="yes"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "FAIL: unknown argument $1" >&2; usage; exit 2 ;;
  esac
done

case "$MODE" in
  preflight)
    echo "=== P0-R1 SUCCESSOR PREFLIGHT (model-free, consumes nothing) ==="
    if [ -z "$LOCK_FILE" ]; then
      echo "FAIL: preflight requires --lock-file" >&2
      exit 2
    fi
    python "$SRC/studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.py" \
      --validate --lock-file "$LOCK_FILE" \
      ${IMAGE_DIGEST:+--image-digest "$IMAGE_DIGEST"}
    python "$SRC/studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.py" \
      --supersession --lock-file "$LOCK_FILE"
    python "$SRC/studies/study3/pilot/p0_r1/p0_r1_transport.py" --self-check
    python "$SRC/studies/study3/pilot/p0_r1/p0_r1_journal.py" --self-check
    echo "TOKENIZER_CONSTRUCTIONS=0"
    echo "TOKENIZER_ENCODES=0"
    echo "CHECKPOINT_DOWNLOADS=0"
    echo "MODEL_OPERATIONS=0"
    echo "GPU_WORKLOAD_ALLOCATED=false"
    echo "ONE_SHOT_ENVELOPE_CONSUMED=false"
    echo "P0_R1_PREFLIGHT_COMPLETE=1"
    echo "Next: p0_r1_successor.sh live-replay --confirm-consumes-the-one-shot-replay-envelope"
    ;;

  live-replay)
    echo "=== P0-R1 REGISTERED LIVE REPLAY GATE ==="
    echo "!!! THIS IS NOT A DRY RUN. It consumes the one-shot replay envelope."
    for pair in "lock-file:$LOCK_FILE" "image-digest:$IMAGE_DIGEST" \
                "ready-commit:$READY_COMMIT"; do
      if [ -z "${pair#*:}" ]; then
        echo "FAIL: --${pair%%:*} is mandatory for live-replay" >&2
        exit 2
      fi
    done
    if [ "$CONFIRM_REPLAY" != "yes" ]; then
      echo "FAIL: --confirm-consumes-the-one-shot-replay-envelope is required;" >&2
      echo "      the live gate is a state-advancing scientific action" >&2
      exit 2
    fi
    LOCK_B64="$(python "$SRC/studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py" \
      --encode --file "$LOCK_FILE")"
    az acr run \
      --registry acrjspaceobssea0708231738 \
      --subscription 943bacdf-8b6e-4e3a-8126-a149f623d32e \
      --platform linux/amd64 \
      -f studies/study3/pilot/p0_r1/container/p0_r1_acr_task_v2.yaml \
      --set IMAGE="acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r1@$IMAGE_DIGEST" \
      --set DIGEST="$IMAGE_DIGEST" \
      --set COMMIT="$READY_COMMIT" \
      --set LOCK_B64="$LOCK_B64" \
      "$SRC"
    echo "P0_R1_LIVE_REPLAY_DISPATCHED=1"
    echo "Recover the complete artifact bytes from the run log with:"
    echo "  python $SRC/studies/study3/pilot/p0_r1/p0_r1_transport.py \\"
    echo "    --recover --log <captured log> --out-dir <local dir>"
    ;;

  launch-pilot)
    echo "=== P0-R1 GPU MODEL PILOT LAUNCH ==="
    if [ -z "$RECEIPT_FILE" ]; then
      echo "FAIL: launch-pilot requires --receipt-file from the passed gate" >&2
      exit 2
    fi
    if [ "$CONFIRM_PILOT" != "yes" ]; then
      echo "FAIL: --confirm-single-model-operating-execution is required" >&2
      exit 2
    fi
    exec bash "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_launch_gpu_pilot_v2.sh" \
      --image-digest "$IMAGE_DIGEST" \
      --ready-commit "$READY_COMMIT" \
      --lock-file "$LOCK_FILE" \
      --receipt-file "$RECEIPT_FILE" \
      --src "$SRC" \
      --confirm-single-model-operating-execution
    ;;

  ""|*)
    echo "FAIL: a mode is required; there is no default" >&2
    usage
    exit 2
    ;;
esac
