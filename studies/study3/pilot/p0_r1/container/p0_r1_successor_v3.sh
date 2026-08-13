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

SRC="${P0_R1_SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)}"
P0_R1_DIR="$SRC/studies/study3/pilot/p0_r1"
PY="${PYTHON:-python3}"

SUBSCRIPTION="${P0_R1_SUBSCRIPTION:-943bacdf-8b6e-4e3a-8126-a149f623d32e}"
RESOURCE_GROUP="${P0_R1_RESOURCE_GROUP:-rg-jspace-observation-sea}"
REGISTRY="${P0_R1_REGISTRY:-acrjspaceobssea0708231738}"
REGISTRY_SERVER="${P0_R1_REGISTRY_SERVER:-$REGISTRY.azurecr.io}"
REPOSITORY="${P0_R1_REPOSITORY:-j-space-observation-study3-p0-r1}"
GPU_JOB="${P0_R1_GPU_JOB:-job-jspace-s3-p0r1-pilot-g3}"
RECOVERY_JOB="${P0_R1_RECOVERY_JOB:-job-jspace-s3-p0r1-recover-g3}"
ENVIRONMENT="${P0_R1_ENVIRONMENT:-cae-jspace-observation-sea-vnet2}"
IDENTITY="/subscriptions/$SUBSCRIPTION/resourcegroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-jspace-aca-acrpull-sea"
LOG_WORKSPACE="${P0_R1_LOG_WORKSPACE:-8daddd67-1cfd-47c5-857e-af3c4a4e3787}"

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

monitor_execution() {
  local job="$1" execution="$2" timeout_seconds="$3"
  local elapsed=0 status=""
  while [ "$elapsed" -lt "$timeout_seconds" ]; do
    set +e
    status="$(az containerapp job execution show --name "$job" \
      --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
      --job-execution-name "$execution" --query properties.status -o tsv \
      2>"$WORK_DIR/${execution}-status.stderr")"
    local query_code=$?
    set -e
    [ "$query_code" -eq 0 ] || fail \
      "status query for exact execution $execution failed"
    case "$status" in
      Succeeded|Failed|Stopped) printf '%s\n' "$status"; return 0 ;;
    esac
    sleep 10
    elapsed=$((elapsed + 10))
  done
  fail "exact execution $execution did not reach a terminal state"
}

capture_execution_log() {
  local execution="$1" out="$2" marker="$3" timeout_seconds="$4"
  local elapsed=0 query=""
  query="ContainerAppConsoleLogs_CL | where ContainerGroupName_s startswith '$execution' | order by time_t asc, _timestamp_d asc | project Log_s"
  while [ "$elapsed" -lt "$timeout_seconds" ]; do
    az monitor log-analytics query --workspace "$LOG_WORKSPACE" \
      --analytics-query "$query" --query '[].Log_s' -o tsv \
      >"$out" 2>"$out.stderr" \
      || fail "Log Analytics query failed for $execution"
    if grep -q "$marker" "$out"; then
      return 0
    fi
    sleep 10
    elapsed=$((elapsed + 10))
  done
  fail "complete log marker $marker was not retained for $execution"
}

configure_recovery_job() {
  local mode="$1" attempt="$2" image="$3"
  local lock_b64="${4:-not-required-in-prefix-preflight}"
  local presence="$WORK_DIR/p0_r1_recovery_job_presence.json"
  "$PY" "$P0_R1_DIR/p0_r1_azure_query_v3.py" \
    --job-presence "$RECOVERY_JOB" --resource-group "$RESOURCE_GROUP" \
    --subscription "$SUBSCRIPTION" >"$presence" \
    || fail "recovery job presence query failed"
  if grep -q '"outcome": "PROVED_ABSENT"' "$presence"; then
    az containerapp job create --name "$RECOVERY_JOB" \
      --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
      --environment "$ENVIRONMENT" --workload-profile-name Consumption \
      --trigger-type Manual --replica-timeout 1800 --replica-retry-limit 0 \
      --parallelism 1 --replica-completion-count 1 --image "$image" \
      --cpu 1 --memory 2Gi --mi-user-assigned "$IDENTITY" \
      --registry-server "$REGISTRY_SERVER" --registry-identity "$IDENTITY" \
      --command /usr/local/bin/p0_r1_recovery_v3.sh --env-vars \
        "P0_R1_SRC=/opt/jspace/src" \
        "P0_R1_RUNTIME_ROOT=/workspace/runtime" \
        "P0_R1_RECOVERY_MODE=$mode" "P0_R1_ATTEMPT=$attempt" \
        "P0_R1_LOCK_V3_B64=$lock_b64" \
        "AZURE_CLIENT_ID=479d9229-632e-4490-ad92-854a34dfddf8" \
      >"$WORK_DIR/p0_r1_recovery_job_create.json" \
      || fail "the CPU-only recovery job could not be created"
  else
    grep -q '"outcome": "PROVED_PRESENT"' "$presence" \
      || fail "recovery job presence was ambiguous"
    az containerapp job update --name "$RECOVERY_JOB" \
      --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
      --image "$image" --command /usr/local/bin/p0_r1_recovery_v3.sh \
      --set-env-vars "P0_R1_SRC=/opt/jspace/src" \
        "P0_R1_RUNTIME_ROOT=/workspace/runtime" \
        "P0_R1_RECOVERY_MODE=$mode" "P0_R1_ATTEMPT=$attempt" \
        "P0_R1_LOCK_V3_B64=$lock_b64" \
        "AZURE_CLIENT_ID=479d9229-632e-4490-ad92-854a34dfddf8" \
      >"$WORK_DIR/p0_r1_recovery_job_update.json" \
      || fail "the CPU-only recovery job could not be updated"
  fi
}

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

  local head context context_dir raw_log run_id replay_attempt
  local locked_digest executable_commit image_ref lock_b64 ready_anchor
  head="$(git -C "$SRC" rev-parse HEAD)"
  [ "$head" = "$(git -C "$SRC" rev-parse origin/main)" ] \
    || fail "HEAD is not origin/main; refusing to replay a local variant"
  [ -z "$(git -C "$SRC" status --porcelain)" ] \
    || fail "the working tree is not clean; refusing to replay uncommitted bytes"

  "$PY" "$P0_R1_DIR/p0_r1_execution_lock_v3.py" --validate \
    --lock-file "$LOCK_FILE" >/dev/null \
    || fail "the active generation-3 lock is invalid"
  "$PY" "$P0_R1_DIR/p0_r1_ready_anchor_v3.py" --prove \
    --lock-file "$LOCK_FILE" --root "$SRC" \
    --out "$WORK_DIR/p0_r1_head_proof_v3.json" >/dev/null \
    || fail "the published head could not be proved before replay"
  locked_digest="$("$PY" -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["image"]["digest"])' \
    "$LOCK_FILE")"
  executable_commit="$("$PY" -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["executable_code"]["commit"])' \
    "$LOCK_FILE")"
  if [ -n "$IMAGE_DIGEST" ] && [ "$IMAGE_DIGEST" != "$locked_digest" ]; then
    fail "the requested image digest is not the locked digest"
  fi
  image_ref="$REGISTRY_SERVER/$REPOSITORY@$locked_digest"
  lock_b64="$("$PY" "$P0_R1_DIR/p0_r1_authorization_v3.py" \
    --encode --file "$LOCK_FILE")"
  ready_anchor="$("$PY" -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["ready_anchor"]["commit"])' \
    "$WORK_DIR/p0_r1_head_proof_v3.json")"

  # The context is built from committed objects, never from the mutable
  # working directory. This is what generation 2 did not do.
  context="$WORK_DIR/context-$head.tar"
  context_dir="$WORK_DIR/context-$head"
  [ ! -e "$context" ] && [ ! -e "$context_dir" ] \
    || fail "the replay work directory already contains a context; refusing a rerun"
  git -C "$SRC" archive --format=tar -o "$context" "$head"
  echo "P0_R1_REPLAY_CONTEXT=$context SHA256=$(sha256sum "$context" | cut -d' ' -f1)"
  mkdir "$context_dir"
  tar -xf "$context" -C "$context_dir"

  raw_log="$WORK_DIR/p0_r1_replay_raw_log.txt"
  [ ! -e "$raw_log" ] || fail "a replay raw log already exists; refusing a rerun"
  set +e
  az acr run --registry "$REGISTRY" --subscription "$SUBSCRIPTION" \
    --file studies/study3/pilot/p0_r1/container/p0_r1_acr_task_v3.yaml \
    --set "IMAGE=$image_ref" --set "LOCK_B64=$lock_b64" \
    --set "DIGEST=$locked_digest" --set "READY_ANCHOR=$ready_anchor" \
    --set "MODE=live" --set "ATTEMPT=live-gate-mints-attempt" \
    "$context_dir" >"$raw_log" 2>"$WORK_DIR/p0_r1_replay_stderr.txt"
  local code=$?
  set -e
  echo "P0_R1_REPLAY_EXIT_CODE=$code"
  if [ "$code" -ne 0 ]; then
    fail "the replay submission exited $code; publish the registered stop and perform no model operation"
  fi

  [ "$(grep -cE 'Run ID: [a-z0-9]+' "$raw_log")" -eq 1 ] || fail \
    "the ACR run ID could not be captured unambiguously; refusing to proceed"
  run_id="$(grep -oE 'Run ID: [a-z0-9]+' "$raw_log" | awk '{print $3}')"
  echo "P0_R1_REPLAY_RUN_ID=$run_id"
  [ "$(grep -cE 'P0_R1_REPLAY_ATTEMPT_ID=gen3-[0-9A-Za-z-]+' "$raw_log")" -eq 1 ] \
    || fail "the replay attempt id was absent or ambiguous"
  replay_attempt="$(grep -oE 'P0_R1_REPLAY_ATTEMPT_ID=gen3-[0-9A-Za-z-]+' \
    "$raw_log" | cut -d= -f2)"
  if [ -n "$ATTEMPT" ] && [ "$ATTEMPT" != "$replay_attempt" ]; then
    fail "the emitted replay attempt differs from --attempt"
  fi
  echo "P0_R1_REPLAY_ATTEMPT=$replay_attempt"

  "$PY" "$P0_R1_DIR/p0_r1_replay_capture_v3.py" --reconstruct \
    --raw-log "$raw_log" --run-id "$run_id" --out-dir "$WORK_DIR" \
    --attempt "$replay_attempt" --exit-code "$code" \
    --executable-commit "$executable_commit" --image-digest "$locked_digest" \
    --stderr-file "$WORK_DIR/p0_r1_replay_stderr.txt" \
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
    --src "$SRC" \
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

  local authorization="$WORK_DIR/p0_r1_authorization_v3.json"
  local attempt image lock_b64 receipt_b64 reconstruction_b64 proof_b64
  local prefix_execution prefix_status prefix_container prefix_log
  local gpu_execution gpu_status gpu_container recovery_execution
  local recovery_status recovery_container recovery_log
  attempt="$("$PY" -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["attempt_id"])' \
    "$authorization")"
  image="$REGISTRY_SERVER/$REPOSITORY@$("$PY" -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["image_digest"])' \
    "$authorization")"
  lock_b64="$("$PY" "$P0_R1_DIR/p0_r1_authorization_v3.py" \
    --encode --file "$LOCK_FILE")"

  # The exact prefix is proved absent from inside the VNet before GPU creation.
  configure_recovery_job prefix-preflight "$attempt" "$image" ""
  prefix_execution="$(az containerapp job start --name "$RECOVERY_JOB" \
    --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
    --query name -o tsv)" \
    || fail "the prefix-preflight execution could not be started"
  [ -n "$prefix_execution" ] || fail "prefix-preflight returned no execution id"
  prefix_status="$(monitor_execution "$RECOVERY_JOB" "$prefix_execution" 1800)"
  [ "$prefix_status" = "Succeeded" ] \
    || fail "prefix-preflight execution $prefix_execution did not succeed"
  prefix_log="$WORK_DIR/p0_r1_prefix_preflight_raw_log.txt"
  capture_execution_log "$prefix_execution" "$prefix_log" \
    "P0_R1_PREFIX_PREFLIGHT_PROVED_ABSENT=1" 600
  grep -q 'P0_R1_PREFIX_PREFLIGHT_PROVED_ABSENT=1' "$prefix_log" \
    || fail "the private prefix was not proved absent"

  # Re-query immediately before the one authorized mutation.
  "$PY" "$P0_R1_DIR/p0_r1_azure_query_v3.py" --job-presence "$GPU_JOB" \
    --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
    >"$WORK_DIR/p0_r1_gpu_job_presence_after_prefix.json" \
    || fail "the final GPU-job absence query failed"
  grep -q '"outcome": "PROVED_ABSENT"' \
    "$WORK_DIR/p0_r1_gpu_job_presence_after_prefix.json" \
    || fail "$GPU_JOB is no longer proved absent"

  receipt_b64="$("$PY" "$P0_R1_DIR/p0_r1_authorization_v3.py" \
    --encode --file "$REPLAY_RECEIPT")"
  reconstruction_b64="$("$PY" "$P0_R1_DIR/p0_r1_authorization_v3.py" \
    --encode --file "$RECONSTRUCTION_RECEIPT")"
  proof_b64="$("$PY" "$P0_R1_DIR/p0_r1_authorization_v3.py" \
    --encode --file "$HEAD_PROOF")"

  az containerapp job create --name "$GPU_JOB" \
    --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
    --environment "$ENVIRONMENT" --workload-profile-name gpu-t4 \
    --trigger-type Manual --replica-timeout 7200 --replica-retry-limit 0 \
    --parallelism 1 --replica-completion-count 1 --image "$image" \
    --cpu 4 --memory 28Gi --mi-user-assigned "$IDENTITY" \
    --registry-server "$REGISTRY_SERVER" --registry-identity "$IDENTITY" \
    --command /usr/local/bin/p0_r1_model_pilot_v3.sh --env-vars \
      "P0_R1_SRC=/opt/jspace/src" \
      "P0_R1_RUNTIME_ROOT=/workspace/runtime" \
      "P0_R1_OUT_DIR=/workspace/runtime/result" \
      "P0_R1_EXECUTOR=production" "P0_R1_ATTEMPT=$attempt" \
      "P0_R1_IMAGE_DIGEST=${image##*@}" \
      "P0_R1_LOCK_V3_B64=$lock_b64" \
      "P0_R1_REPLAY_RECEIPT_V3_B64=$receipt_b64" \
      "P0_R1_RECONSTRUCTION_RECEIPT_V3_B64=$reconstruction_b64" \
      "P0_R1_HEAD_PROOF_V3_B64=$proof_b64" \
      "AZURE_CLIENT_ID=479d9229-632e-4490-ad92-854a34dfddf8" \
    >"$WORK_DIR/p0_r1_gpu_job_create.json" \
    || fail "the one GPU job could not be created"

  gpu_execution="$(az containerapp job start --name "$GPU_JOB" \
    --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
    --query name -o tsv)" || fail "the one GPU execution could not be started"
  [ -n "$gpu_execution" ] || fail "GPU start returned no execution identity"
  echo "P0_R1_GPU_EXECUTION=$gpu_execution"
  gpu_status="$(monitor_execution "$GPU_JOB" "$gpu_execution" 7200)"

  # Recovery is model-free and always runs after the captured terminal status.
  configure_recovery_job recover "$attempt" "$image" "$lock_b64"
  recovery_execution="$(az containerapp job start --name "$RECOVERY_JOB" \
    --resource-group "$RESOURCE_GROUP" --subscription "$SUBSCRIPTION" \
    --query name -o tsv)" || fail "the recovery execution could not be started"
  recovery_status="$(monitor_execution "$RECOVERY_JOB" "$recovery_execution" 1800)"
  [ "$recovery_status" = "Succeeded" ] \
    || fail "the recovery execution did not succeed"
  recovery_log="$WORK_DIR/p0_r1_recovery_raw_log.txt"
  capture_execution_log "$recovery_execution" "$recovery_log" \
    "P0_R1_RECOVERY_COMPLETE=1" 900
  "$PY" "$P0_R1_DIR/p0_r1_recovery_v3.py" --decode-log \
    --log "$recovery_log" --attempt "$attempt" \
    --out-dir "$WORK_DIR/recovered" \
    || fail "the recovery envelope could not be decoded"
  # A hard kill may have no shell-trap marker. Its log is useful but never a
  # precondition for the Blob recovery that must run first.
  local gpu_query
  gpu_query="ContainerAppConsoleLogs_CL | where ContainerGroupName_s startswith '$gpu_execution' | order by time_t asc, _timestamp_d asc | project Log_s"
  az monitor log-analytics query --workspace "$LOG_WORKSPACE" \
    --analytics-query "$gpu_query" --query '[].Log_s' -o tsv \
    >"$WORK_DIR/p0_r1_gpu_execution_log.txt" \
    2>"$WORK_DIR/p0_r1_gpu_execution_log.stderr" || true
  echo "P0_R1_GPU_TERMINAL_STATUS=$gpu_status"
  echo "P0_R1_RECOVERY_EXECUTION=$recovery_execution"
  echo "P0_R1_TERMINAL_PUBLICATION_REQUIRED=1"
  [ "$gpu_status" = "Succeeded" ] || return 4
}

case "$MODE" in
  preflight) run_preflight ;;
  live-replay) run_live_replay ;;
  launch-pilot) run_launch_pilot ;;
  *) usage; exit 2 ;;
esac
