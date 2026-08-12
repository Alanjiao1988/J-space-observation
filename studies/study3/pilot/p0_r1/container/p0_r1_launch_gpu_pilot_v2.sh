#!/usr/bin/env bash
# Study 3 P0-R1 generation-2 GPU model-pilot launcher.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md
#   section 9.
#
# THIS SCRIPT IS NOT AUTHORIZED TO RUN IN THIS ROUND. It is committed and
# validated now so that the successor session has one unambiguous path to the
# single model-operating execution, instead of assembling an `az` invocation by
# hand under time pressure.
#
# Every input is mandatory. There is no default digest, no default commit, no
# default lock and no default receipt, because a default is exactly how a job
# gets launched against something other than what was published.
#
# The script validates every input in Python BEFORE it creates or starts
# anything, refuses if an execution already exists, and pins retry to zero.
set -euo pipefail

SRC="${P0_R1_SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)}"
IMAGE_DIGEST=""
READY_COMMIT=""
LOCK_FILE=""
RECEIPT_FILE=""
CONFIRM=""

usage() {
  cat >&2 <<'USAGE'
usage: p0_r1_launch_gpu_pilot_v2.sh
         --image-digest sha256:<64hex>
         --ready-commit <40hex>
         --lock-file    <path to p0_r1_execution_lock_v2.json>
         --receipt-file <path to p0_r1_replay_receipt.json>
         --confirm-single-model-operating-execution

Every argument is mandatory. This launcher starts the ONE model-operating
execution of stage P0-R1 and is authorized only in the successor session,
only after the live replay gate has passed in that same session.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --image-digest) IMAGE_DIGEST="${2:-}"; shift 2 ;;
    --ready-commit) READY_COMMIT="${2:-}"; shift 2 ;;
    --lock-file) LOCK_FILE="${2:-}"; shift 2 ;;
    --receipt-file) RECEIPT_FILE="${2:-}"; shift 2 ;;
    --confirm-single-model-operating-execution) CONFIRM="yes"; shift ;;
    --src) SRC="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "FAIL: unknown argument $1" >&2; usage; exit 2 ;;
  esac
done

for pair in "image-digest:$IMAGE_DIGEST" "ready-commit:$READY_COMMIT" \
            "lock-file:$LOCK_FILE" "receipt-file:$RECEIPT_FILE"; do
  if [ -z "${pair#*:}" ]; then
    echo "FAIL: --${pair%%:*} is mandatory; this launcher has no defaults" >&2
    usage
    exit 2
  fi
done

if [ "$CONFIRM" != "yes" ]; then
  echo "FAIL: --confirm-single-model-operating-execution is required" >&2
  exit 2
fi

SUBSCRIPTION="943bacdf-8b6e-4e3a-8126-a149f623d32e"
RESOURCE_GROUP="rg-jspace-observation-sea"
ENVIRONMENT="cae-jspace-observation-sea-vnet2"
JOB_NAME="job-jspace-study3-p0-r1-pilot-g2"
REGISTRY="acrjspaceobssea0708231738.azurecr.io"
REPOSITORY="j-space-observation-study3-p0-r1"
IDENTITY="/subscriptions/$SUBSCRIPTION/resourcegroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-jspace-aca-acrpull-sea"

echo "=== P0-R1 GPU MODEL PILOT LAUNCH (generation 2) ==="

# Validate every launch input together, before anything is created. The same
# module the container uses on the inside runs here on the outside, so the two
# cannot drift.
python "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_prestart_guard.py" \
  --lock-file "$LOCK_FILE" \
  --receipt-file "$RECEIPT_FILE" \
  --image-digest "$IMAGE_DIGEST" \
  --ready-commit "$READY_COMMIT" \
  --src "$SRC"

ATTEMPT_ID="$(python "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_prestart_guard.py" \
  --receipt-file "$RECEIPT_FILE" --print-attempt-id)"
echo "ATTEMPT_ID=$ATTEMPT_ID"

# One model-operating execution, ever. If the job already has an execution
# history, this launcher stops rather than adding to it.
EXISTING="$(az containerapp job execution list \
  --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
  --subscription "$SUBSCRIPTION" --query "length(@)" -o tsv 2>/dev/null || echo "absent")"
if [ "$EXISTING" != "absent" ] && [ "$EXISTING" != "0" ]; then
  echo "FAIL: $JOB_NAME already has $EXISTING execution(s); the P0-R1 pilot is" >&2
  echo "      a one-shot and this launcher will not add another" >&2
  exit 2
fi

LOCK_B64="$(python "$SRC/studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py" \
  --encode --file "$LOCK_FILE")"
RECEIPT_B64="$(python "$SRC/studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py" \
  --encode --file "$RECEIPT_FILE")"

IMAGE="$REGISTRY/$REPOSITORY@$IMAGE_DIGEST"
echo "IMAGE=$IMAGE"
echo "COMMAND=/usr/local/bin/p0_r1_model_pilot_v2.sh"

if [ "$EXISTING" = "absent" ]; then
  az containerapp job create \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --subscription "$SUBSCRIPTION" \
    --environment "$ENVIRONMENT" \
    --workload-profile-name gpu-t4 \
    --trigger-type Manual \
    --replica-timeout 7200 \
    --replica-retry-limit 0 \
    --parallelism 1 \
    --replica-completion-count 1 \
    --image "$IMAGE" \
    --cpu 8 --memory 56Gi \
    --mi-user-assigned "$IDENTITY" \
    --registry-server "$REGISTRY" \
    --registry-identity "$IDENTITY" \
    --command "/usr/local/bin/p0_r1_model_pilot_v2.sh" \
    --args "$IMAGE_DIGEST" "$READY_COMMIT" \
    --env-vars \
      "P0_R1_SRC=/opt/jspace/src" \
      "RESULTS_DIR=/workspace/runtime/results" \
      "INJECTED_DIR=/workspace/runtime/injected" \
      "P0_R1_ATTEMPT_ID=$ATTEMPT_ID" \
      "P0_R1_LOCK_V2_B64=$LOCK_B64" \
      "P0_R1_REPLAY_RECEIPT_B64=$RECEIPT_B64" \
      "P0_R1_RESULT_ACCOUNT=stjspacefiles0709085305" \
      "P0_R1_RESULT_CONTAINER=jspace-results" \
      "HF_HUB_DISABLE_TELEMETRY=1" \
      "TOKENIZERS_PARALLELISM=false"
fi

az containerapp job start \
  --name "$JOB_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --subscription "$SUBSCRIPTION"

echo "P0_R1_MODEL_PILOT_LAUNCHED=1"
echo "P0_R1_RETRY_LIMIT=0"
echo "P0_R1_RESULT_PREFIX=study3/p0_r1/gen2/$ATTEMPT_ID/"
echo "Recover the result with:"
echo "  python $SRC/studies/study3/pilot/p0_r1/p0_r1_blob_transport.py \\"
echo "    --recover --attempt $ATTEMPT_ID --out-dir <local dir>"
