#!/usr/bin/env bash
# Study 3 P0-R1 generation-3 successor wrapper.
#
# Generation 2 called its equivalent a wrapper, but `live-replay` was a
# dispatcher: it ran `az acr run` against the mutable current directory, threw
# away the run identity, printed a suggestion that the operator might like to
# capture the log themselves, and returned. `launch-pilot` did not monitor the
# execution it started, recover any byte, reconcile any counter, or publish any
# disposition. Those were mandatory duties, not operator prose, and a one-shot
# envelope cannot be spent on a best-effort dispatcher.
#
# This wrapper has three explicit modes and no default. Choosing nothing does
# nothing; there is no path where an omitted argument starts a GPU job.
#
#   preflight     model-free, read-only. Safe to run any number of times.
#   live-replay   spends the replay half of the envelope. Requires --i-am-sure.
#   launch-pilot  spends the model half. Requires a recovered replay pass, an
#                 independent reconstruction receipt, and --i-am-sure.
#
# In the generation-3 publication round only `preflight` may be run.
set -euo pipefail

SRC="${P0_R1_SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"
P0_R1_DIR="$SRC/studies/study3/pilot/p0_r1"
PY="${PYTHON:-python3}"

SUBSCRIPTION="${P0_R1_SUBSCRIPTION:-943bacdf-8b6e-4e3a-8126-a149f623d32e}"
RESOURCE_GROUP="${P0_R1_RESOURCE_GROUP:-rg-jspace-observation-sea}"
REGISTRY="${P0_R1_REGISTRY:-acrjspaceobssea0708231738}"
GPU_JOB="${P0_R1_GPU_JOB:-job-jspace-s3-p0r1-pilot-g3}"
RECOVERY_JOB="${P0_R1_RECOVERY_JOB:-job-jspace-s3-p0r1-recover-g3}"

usage() {
  cat >&2 <<'USAGE'
usage: p0_r1_successor_v3.sh <mode> [options]

modes (no default; one must be named explicitly):

  preflight
      --lock-file <path>                 the active generation-3 lock
      [--image-digest sha256:<64hex>]    cross-check the locked digest
      [--work-dir <path>]                where proofs are written

  live-replay
      --lock-file <path> --work-dir <path> --i-am-sure
      Builds an ACR context from committed Git objects only, submits exactly
      one CPU-only replay, captures the run ID and the complete raw log from
      its first byte, reconstructs and verifies the four canonical artifacts
      from that log alone, and writes an independent reconstruction receipt.

  launch-pilot
      --lock-file <path> --work-dir <path> --replay-receipt <path>
      --reconstruction-receipt <path> --head-proof <path> --i-am-sure
      Proves the prefix unused through the private route, refuses any stale or
      foreign job configuration, starts exactly one execution, captures its
      exact name, monitors only that execution, and recovers its bytes.

Every mode fails closed. An Azure query error is never read as an absence.
USAGE
}

fail() { echo "FAIL: $*" >&2; exit 1; }

require_arg() {
  # A missing value must not silently become the next flag.
  case "${2:-}" in
    ""|--*) fail "$1 requires a value" ;;
  esac
}

MODE="${1:-}"
[ -n "$MODE" ] || { usage; exit 2; }
shift || true

LOCK_FILE=""
WORK_DIR=""
IMAGE_DIGEST=""
REPLAY_RECEIPT=""
RECONSTRUCTION_RECEIPT=""
HEAD_PROOF=""
ATTEMPT=""
CONFIRMED=0

while [ $# -gt 0 ]; do
  case "$1" in
    --lock-file) require_arg "$1" "${2:-}"; LOCK_FILE="$2"; shift 2 ;;
    --work-dir) require_arg "$1" "${2:-}"; WORK_DIR="$2"; shift 2 ;;
    --image-digest) require_arg "$1" "${2:-}"; IMAGE_DIGEST="$2"; shift 2 ;;
    --replay-receipt) require_arg "$1" "${2:-}"; REPLAY_RECEIPT="$2"; shift 2 ;;
    --reconstruction-receipt) require_arg "$1" "${2:-}"
      RECONSTRUCTION_RECEIPT="$2"; shift 2 ;;
    --head-proof) require_arg "$1" "${2:-}"; HEAD_PROOF="$2"; shift 2 ;;
    --attempt) require_arg "$1" "${2:-}"; ATTEMPT="$2"; shift 2 ;;
    --i-am-sure) CONFIRMED=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unrecognized argument $1" ;;
  esac
done

[ -n "$LOCK_FILE" ] || fail "$MODE requires --lock-file"
[ -f "$LOCK_FILE" ] || fail "lock file $LOCK_FILE does not exist"

# ---------------------------------------------------------------- preflight --
run_preflight() {
  local work="${WORK_DIR:-$(mktemp -d)}"
  mkdir -p "$work"

  echo "P0_R1_PREFLIGHT_BEGIN=1"

  # 1. The lock validates against its own bytes and schema.
  "$PY" "$P0_R1_DIR/p0_r1_execution_lock_v3.py" --validate \
    --lock-file "$LOCK_FILE" || fail "the generation-3 lock did not validate"

  # 2. HEAD == origin/main, clean status, ancestry, governance-only drift, and
  #    zero bound-byte changes after the image build.
  "$PY" "$P0_R1_DIR/p0_r1_ready_anchor_v3.py" --prove \
    --lock-file "$LOCK_FILE" --root "$SRC" \
    --out "$work/p0_r1_head_proof_v3.json" >/dev/null \
    || fail "the published head could not be proved against the ready anchor"
  echo "P0_R1_HEAD_PROOF=$work/p0_r1_head_proof_v3.json"

  # 3. Generations 1 and 2 are unconsumed, superseded and not launchable.
  "$PY" "$P0_R1_DIR/p0_r1_execution_lock_v3.py" --supersession \
    --lock-file "$LOCK_FILE" >"$work/p0_r1_supersession_v3.json" \
    || fail "the supersession record could not be produced"

  # 4. The image digest the lock binds is the one the operator intends.
  if [ -n "$IMAGE_DIGEST" ]; then
    "$PY" "$P0_R1_DIR/p0_r1_execution_lock_v3.py" --validate \
      --lock-file "$LOCK_FILE" --image-digest "$IMAGE_DIGEST" \
      >/dev/null || fail "the supplied image digest is not the locked digest"
  fi

  # 5. Read-only Azure control plane, fail-closed. A query error stops here.
  "$PY" "$P0_R1_DIR/p0_r1_azure_query_v3.py" \
    --job-presence "$GPU_JOB" --resource-group "$RESOURCE_GROUP" \
    --subscription "$SUBSCRIPTION" >"$work/p0_r1_gpu_job_presence.json" \
    || fail "the generation-3 GPU job presence query did not reach a proved outcome"
  grep -q '"outcome": "PROVED_ABSENT"' "$work/p0_r1_gpu_job_presence.json" \
    || fail "$GPU_JOB is not proved absent; refusing to continue"

  echo "P0_R1_GPU_JOB_PROVED_ABSENT=1 JOB=$GPU_JOB"
  echo "P0_R1_PREFLIGHT_COMPLETE=1"
  echo "P0_R1_STATE=STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE"
  echo "P0_R1_NEXT=an explicit operator decision is required before"\
       "live-replay; preflight never spends the envelope"
}

# -------------------------------------------------------------- live-replay --
run_live_replay() {
  [ "$CONFIRMED" -eq 1 ] || fail \
    "live-replay spends the one-shot replay envelope and requires --i-am-sure"
  [ -n "$WORK_DIR" ] || fail "live-replay requires --work-dir"
  mkdir -p "$WORK_DIR"

  local head context raw_log run_id
  head="$(git -C "$SRC" rev-parse HEAD)"
  [ "$head" = "$(git -C "$SRC" rev-parse origin/main)" ] \
    || fail "HEAD is not origin/main; refusing to replay a local variant"
  [ -z "$(git -C "$SRC" status --porcelain)" ] \
    || fail "the working tree is not clean; refusing to replay uncommitted bytes"

  # The context is built from committed objects, never from the mutable
  # working directory. This is what generation 2 did not do.
  context="$WORK_DIR/context-$head.tar"
  git -C "$SRC" archive --format=tar -o "$context" "$head"
  echo "P0_R1_REPLAY_CONTEXT=$context SHA256=$(sha256sum "$context" | cut -d' ' -f1)"

  raw_log="$WORK_DIR/p0_r1_replay_raw_log.txt"
  set +e
  az acr run --registry "$REGISTRY" --subscription "$SUBSCRIPTION" \
    --file studies/study3/pilot/p0_r1/container/p0_r1_acr_task_v3.yaml \
    "$context" >"$raw_log" 2>"$WORK_DIR/p0_r1_replay_stderr.txt"
  local code=$?
  set -e
  echo "P0_R1_REPLAY_EXIT_CODE=$code"
  if [ "$code" -ne 0 ]; then
    fail "the replay submission exited $code; publish the registered stop and perform no model operation"
  fi

  run_id="$(grep -oE 'Run ID: [a-z0-9]+' "$raw_log" | tail -1 | awk '{print $3}')"
  [ -n "$run_id" ] || fail \
    "the ACR run ID could not be captured unambiguously; refusing to proceed"
  echo "P0_R1_REPLAY_RUN_ID=$run_id"

  "$PY" "$P0_R1_DIR/p0_r1_replay_capture_v3.py" --reconstruct \
    --raw-log "$raw_log" --run-id "$run_id" --out-dir "$WORK_DIR" \
    --exit-code "$code" \
    || fail "the replay artifacts could not be reconstructed from the captured log"

  echo "P0_R1_REPLAY_CAPTURED=1"
  echo "P0_R1_NEXT=publish the raw log, run identity, recovered bytes and"\
       "reconstruction receipt by non-force fast-forward before any model job"
}

# ------------------------------------------------------------- launch-pilot --
run_launch_pilot() {
  [ "$CONFIRMED" -eq 1 ] || fail \
    "launch-pilot spends the one-shot model envelope and requires --i-am-sure"
  [ -n "$WORK_DIR" ] || fail "launch-pilot requires --work-dir"
  [ -n "$REPLAY_RECEIPT" ] || fail "launch-pilot requires --replay-receipt"
  [ -n "$RECONSTRUCTION_RECEIPT" ] || fail \
    "launch-pilot requires --reconstruction-receipt; the emitted replay receipt alone never authorizes a model operation"
  [ -n "$HEAD_PROOF" ] || fail "launch-pilot requires --head-proof"

  # The authorization must build before anything is created in Azure.
  "$PY" "$P0_R1_DIR/p0_r1_authorization_v3.py" --build \
    --lock-file "$LOCK_FILE" --replay-receipt "$REPLAY_RECEIPT" \
    --reconstruction-receipt "$RECONSTRUCTION_RECEIPT" \
    --head-proof "$HEAD_PROOF" --out "$WORK_DIR/p0_r1_authorization_v3.json" \
    || fail "the model authorization did not build; no Azure object was touched"

  # The GPU job must not already exist. A zero-execution but stale or foreign
  # job refuses rather than being started or updated into compliance.
  "$PY" "$P0_R1_DIR/p0_r1_azure_query_v3.py" --job-presence "$GPU_JOB" \
    --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
    >"$WORK_DIR/p0_r1_gpu_job_presence.json" \
    || fail "the GPU job presence query did not reach a proved outcome"
  grep -q '"outcome": "PROVED_ABSENT"' \
    "$WORK_DIR/p0_r1_gpu_job_presence.json" \
    || fail "$GPU_JOB is not proved absent; refusing to reuse or update a job"

  # The private prefix is proved unused from inside the network, before the
  # GPU job is created, by the separately named CPU-only preflight job.
  echo "P0_R1_PREFIX_PREFLIGHT_JOB=$RECOVERY_JOB"
  fail "launch-pilot is not authorized in this publication round"
}

case "$MODE" in
  preflight) run_preflight ;;
  live-replay) run_live_replay ;;
  launch-pilot) run_launch_pilot ;;
  *) usage; exit 2 ;;
esac
