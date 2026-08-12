#!/usr/bin/env bash
# Launch the single Study 3 P0-R1 bounded GPU model pilot.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md
#   section 6.
#
# THIS ROUND MAY ONLY COMMIT AND VALIDATE THIS LAUNCHER. It must not create,
# update, start or allocate the job. Creating or updating the dormant job
# definition in a later execution session is not a model operation; starting it
# is.
#
# It reuses the repository's existing route exactly:
#   * Azure Container Apps, workload profile gpu-t4 (Consumption-GPU-NC8as-T4);
#   * managed-identity ACR pull via id-jspace-aca-acrpull-sea;
#   * the image bound by immutable digest, never by tag;
#   * replica retry limit 0, so the platform can never silently re-run a model
#     operation;
#   * at most one model-operating execution.
set -euo pipefail

SUBSCRIPTION="${SUBSCRIPTION:-943bacdf-8b6e-4e3a-8126-a149f623d32e}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
ENVIRONMENT="${ENVIRONMENT:-cae-jspace-observation-sea-vnet2}"
WORKLOAD_PROFILE="${WORKLOAD_PROFILE:-gpu-t4}"
IDENTITY="${IDENTITY:-/subscriptions/943bacdf-8b6e-4e3a-8126-a149f623d32e/resourcegroups/rg-jspace-observation-sea/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-jspace-aca-acrpull-sea}"
REGISTRY="${REGISTRY:-acrjspaceobssea0708231738.azurecr.io}"
JOB_NAME="${JOB_NAME:-job-jspace-study3-p0-r1-pilot}"

IMAGE_DIGEST="${1:-}"
COMMIT="${2:-}"

if [ -z "$IMAGE_DIGEST" ] || [ -z "$COMMIT" ]; then
  echo "usage: $0 <image-digest> <ready-commit>" >&2
  echo "the image is bound by immutable digest; a tag is never sufficient" >&2
  exit 2
fi
case "$IMAGE_DIGEST" in
  sha256:*) ;;
  *) echo "FAIL: the image must be bound by an immutable sha256 digest" >&2
     exit 2 ;;
esac

IMAGE="$REGISTRY/j-space-observation-study3-p0-r1@$IMAGE_DIGEST"

# Refuse to start twice. A model-operating execution is one-shot: if any
# execution of this job already exists, this launcher stops rather than starting
# a second one. Only a signed zero-operation receipt authorizes one further
# infrastructure attempt, and that decision is not automatic.
EXISTING="$(az containerapp job execution list \
  --name "$JOB_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --subscription "$SUBSCRIPTION" \
  --query "length(@)" -o tsv 2>/dev/null || echo 0)"
if [ "${EXISTING:-0}" != "0" ]; then
  echo "REFUSED: $JOB_NAME already has $EXISTING execution(s)." >&2
  echo "The P0-R1 model pilot is one-shot. A further attempt requires a signed" >&2
  echo "receipt proving zero tokenizer, checkpoint, model-load, prefill," >&2
  echo "decode, generation and scored-row operations in the failed attempt." >&2
  exit 3
fi

echo "job         : $JOB_NAME"
echo "image       : $IMAGE"
echo "commit      : $COMMIT"
echo "profile     : $WORKLOAD_PROFILE"
echo "retry limit : 0"

az containerapp job create \
  --name "$JOB_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --subscription "$SUBSCRIPTION" \
  --environment "$ENVIRONMENT" \
  --workload-profile-name "$WORKLOAD_PROFILE" \
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
  --command "/bin/bash" \
  --args "/workspace/p0_r1_model_pilot.sh,$COMMIT,$IMAGE_DIGEST"

az containerapp job start \
  --name "$JOB_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --subscription "$SUBSCRIPTION"

echo "P0_R1_GPU_PILOT_STARTED=1"
