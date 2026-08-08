#!/usr/bin/env bash
# Launch the Study 2 Stage B-D development execution job on the ACA T4 profile.
#
#   ACR_NAME=<registry> IMAGE_DIGEST=sha256:... PROJECT_SHA=<commit> \
#     ./26_run_study2_stage_bd_gpu.sh
#
# The job is addressed by immutable digest, never by tag, so the bytes that run
# are the bytes that were locked at build time.  It runs under the existing
# user-assigned identity, which holds AcrPull for the image and AcrPush for the
# artifact repository it writes its own outputs to.

set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
ENVIRONMENT="${ENVIRONMENT:-cae-jspace-observation-sea}"
WORKLOAD_PROFILE="${WORKLOAD_PROFILE:-gpu-t4}"
IDENTITY_NAME="${IDENTITY_NAME:-id-jspace-aca-acrpull-sea}"
ACR_NAME="${ACR_NAME:?Set ACR_NAME}"
IMAGE_DIGEST="${IMAGE_DIGEST:?Set IMAGE_DIGEST to the locked sha256: digest}"
PROJECT_SHA="${PROJECT_SHA:?Set PROJECT_SHA to the built commit}"
PROJECT_TREE="${PROJECT_TREE:?Set PROJECT_TREE to the built tree}"
IMAGE_REPOSITORY="j-space-observation-study2-stage-bd"
ARTIFACT_REPOSITORY="${ARTIFACT_REPOSITORY:-j-space-observation-study2-stage-bd-artifacts}"
ARTIFACT_TAG="${ARTIFACT_TAG:-shards-${PROJECT_SHA:0:12}}"
JOB_NAME="${JOB_NAME:-job-js-s2-bd-${PROJECT_SHA:0:8}}"
REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-10800}"

if [[ ! "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] IMAGE_DIGEST must be a full sha256: digest"
    exit 1
fi

REGISTRY_SERVER="$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)"
IDENTITY_ID="$(az identity show --name "$IDENTITY_NAME" \
    --resource-group "$RESOURCE_GROUP" --query id -o tsv)"
IDENTITY_CLIENT_ID="$(az identity show --name "$IDENTITY_NAME" \
    --resource-group "$RESOURCE_GROUP" --query clientId -o tsv)"

for attribute in writeEnabled deleteEnabled; do
    VALUE="$(az acr manifest show-metadata \
        --registry "$ACR_NAME" \
        --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
        --query "changeableAttributes.${attribute}" -o tsv)"
    if [[ "${VALUE,,}" != "false" ]]; then
        echo "[FAIL] refusing to run an image whose ${attribute} is still true"
        exit 1
    fi
done
echo "[OK] image manifest is locked against write and delete"

az containerapp job create \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT" \
    --workload-profile-name "$WORKLOAD_PROFILE" \
    --trigger-type Manual \
    --replica-timeout "$REPLICA_TIMEOUT" \
    --replica-retry-limit 0 \
    --parallelism 1 \
    --replica-completion-count 1 \
    --image "${REGISTRY_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --cpu 8 --memory 56Gi \
    --mi-user-assigned "$IDENTITY_ID" \
    --registry-server "$REGISTRY_SERVER" \
    --registry-identity "$IDENTITY_ID" \
    --env-vars \
        "AZURE_CLIENT_ID=${IDENTITY_CLIENT_ID}" \
        "STAGE_BD_SOURCE_COMMIT=${PROJECT_SHA}" \
        "STAGE_BD_SOURCE_TREE=${PROJECT_TREE}" \
        "STAGE_BD_IMAGE_DIGEST=${IMAGE_DIGEST}" \
        "STAGE_BD_REGISTRY=${REGISTRY_SERVER}" \
        "STAGE_BD_ARTIFACT_REPOSITORY=${ARTIFACT_REPOSITORY}" \
        "STAGE_BD_ARTIFACT_TAG=${ARTIFACT_TAG}" \
    --output none

EXECUTION="$(az containerapp job start \
    --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
    --query name -o tsv)"

echo "[OK] job=$JOB_NAME"
echo "[OK] execution=$EXECUTION"
echo "[OK] artifact=${REGISTRY_SERVER}/${ARTIFACT_REPOSITORY}:${ARTIFACT_TAG}"
echo "[OK] The job establishes nothing until its artifact is independently validated"
