#!/usr/bin/env bash
# Script: 03_run_phase1.sh
# Purpose: Run Phase 1 dry-run as an Azure Container Apps Job.
# This script creates/starts Azure resources only when explicitly run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
VARS_FILE="$SCRIPT_DIR/../variables.env"

if [[ ! -f "$VARS_FILE" ]]; then
    echo "[FAIL] Missing $VARS_FILE"
    exit 1
fi
source "$VARS_FILE"

ACR_LOGIN_SERVER="${AZURE_CONTAINER_REGISTRY}.azurecr.io"
IMAGE_REF="${ACR_LOGIN_SERVER}/${AZURE_IMAGE_NAME}:${AZURE_IMAGE_TAG}"
JOB_NAME="${AZURE_CONTAINER_APP_JOB}-p1dry"
COMMAND="python experiments/phase1_depth_gradient.py --dry-run --output-dir ${RESULTS_DIR}/phase1_dry_run"

echo "================================"
echo "Azure Phase 1 dry run"
echo "================================"
echo "Resource group: ${AZURE_RESOURCE_GROUP}"
echo "Container Apps environment: ${AZURE_CONTAINER_APP_ENV}"
echo "Job: ${JOB_NAME}"
echo "Image: ${IMAGE_REF}"
echo "Command: ${COMMAND}"
echo

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

if ! az containerapp env show --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_CONTAINER_APP_ENV" >/dev/null 2>&1; then
    echo "[CREATE] Container Apps environment ${AZURE_CONTAINER_APP_ENV}"
    az containerapp env create \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$AZURE_CONTAINER_APP_ENV" \
        --location "$AZURE_LOCATION" \
        --enable-workload-profiles true \
        --enable-dedicated-gpu true \
        -o table
fi

PROFILE_COUNT="$(az containerapp env workload-profile list \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --name "$AZURE_CONTAINER_APP_ENV" \
    --query "[?name=='${GPU_WORKLOAD_PROFILE_NAME}'] | length(@)" \
    -o tsv)"
if [[ "$PROFILE_COUNT" == "0" ]]; then
    echo "[CREATE] GPU workload profile ${GPU_WORKLOAD_PROFILE_NAME} (${GPU_WORKLOAD_PROFILE})"
    az containerapp env workload-profile add \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$AZURE_CONTAINER_APP_ENV" \
        --workload-profile-name "$GPU_WORKLOAD_PROFILE_NAME" \
        --workload-profile-type "$GPU_WORKLOAD_PROFILE" \
        --min-nodes 0 \
        --max-nodes 1 \
        -o table
fi

if ! az containerapp job show --resource-group "$AZURE_RESOURCE_GROUP" --name "$JOB_NAME" >/dev/null 2>&1; then
    echo "[CREATE] Container Apps job ${JOB_NAME}"
    az containerapp job create \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$JOB_NAME" \
        --environment "$AZURE_CONTAINER_APP_ENV" \
        --trigger-type Manual \
        --replica-timeout 1800 \
        --replica-retry-limit 0 \
        --replica-completion-count 1 \
        --parallelism 1 \
        --workload-profile-name "$GPU_WORKLOAD_PROFILE_NAME" \
        --image "$IMAGE_REF" \
        --mi-system-assigned \
        --registry-server "$ACR_LOGIN_SERVER" \
        --registry-identity system \
        --cpu 2 \
        --memory 4Gi \
        --env-vars "HF_HOME=${HF_HOME}" "TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE}" "RESULTS_DIR=${RESULTS_DIR}" \
        --command "/bin/bash" \
        --args "-lc" "$COMMAND" \
        -o table
else
    echo "[UPDATE] Container Apps job ${JOB_NAME}"
    az containerapp job update \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$JOB_NAME" \
        --image "$IMAGE_REF" \
        --workload-profile-name "$GPU_WORKLOAD_PROFILE_NAME" \
        --env-vars "HF_HOME=${HF_HOME}" "TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE}" "RESULTS_DIR=${RESULTS_DIR}" \
        --command "/bin/bash" \
        --args "-lc" "$COMMAND" \
        -o table
fi

echo "[START] ${JOB_NAME}"
az containerapp job start --resource-group "$AZURE_RESOURCE_GROUP" --name "$JOB_NAME" -o table

LOG_FILE="$PROJECT_ROOT/docs/run_log.md"
{
    echo ""
    echo "## Azure Phase 1 dry-run job - $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    echo "- Command: \`bash infra/azure/scripts/03_run_phase1.sh\`"
    echo "- Job: ${JOB_NAME}"
    echo "- Image: ${IMAGE_REF}"
    echo "- Container command: \`${COMMAND}\`"
    echo "- Note: This script creates/starts Azure resources when explicitly run."
} >> "$LOG_FILE"

echo "================================"
echo "[OK] Phase 1 dry-run job started"
echo "Check executions:"
echo "az containerapp job execution list -g ${AZURE_RESOURCE_GROUP} -n ${JOB_NAME} -o table"
echo "================================"
