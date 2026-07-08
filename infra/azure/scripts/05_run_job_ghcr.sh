#!/usr/bin/env bash
# Script: 05_run_job_ghcr.sh
# Purpose: Run an Azure Container Apps Job using a GHCR image (ACR fallback path).
# This script creates/starts Azure resources only when explicitly run.
#
# Secrets policy:
# - GHCR_PAT must be provided via environment variable only.
# - The PAT is passed to Azure as a Container Apps secret at deployment time.
# - The PAT value is never printed, logged, or committed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

# ---- Required configuration (override via environment) ----
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
LOCATION="${LOCATION:-southeastasia}"
CONTAINER_APP_ENV="${CONTAINER_APP_ENV:-cae-jspace-observation-sea}"
CONTAINER_APP_JOB="${CONTAINER_APP_JOB:-job-jspace-ghcr-smoke}"
GPU_WORKLOAD_PROFILE="${GPU_WORKLOAD_PROFILE:-Consumption-GPU-NC8as-T4}"
GPU_WORKLOAD_PROFILE_NAME="${GPU_WORKLOAD_PROFILE_NAME:-gpu-t4}"

# GHCR image, for example: ghcr.io/alanjiao1988/j-space-observation:<git-sha>
IMAGE="${IMAGE:-}"

# GHCR auth: username + PAT with read:packages. PAT via env var only.
GHCR_USERNAME="${GHCR_USERNAME:-}"
GHCR_PAT="${GHCR_PAT:-}"

# Command to run inside the container.
JOB_COMMAND="${JOB_COMMAND:-python experiments/phase1_depth_gradient.py --dry-run}"

# Mounted/runtime paths inside the container.
HF_HOME="${HF_HOME:-/mnt/models/huggingface}"
TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/mnt/models/huggingface}"
RESULTS_DIR="${RESULTS_DIR:-/mnt/results}"

echo "================================"
echo "Azure Container Apps Job (GHCR image)"
echo "================================"
echo "Resource group: ${RESOURCE_GROUP}"
echo "Location: ${LOCATION}"
echo "Environment: ${CONTAINER_APP_ENV}"
echo "Job: ${CONTAINER_APP_JOB}"
echo "Image: ${IMAGE}"
echo "GHCR username: ${GHCR_USERNAME:+<set>}"
echo "GHCR PAT: ${GHCR_PAT:+<provided>}"
echo "Command: ${JOB_COMMAND}"
echo

if [[ -z "$IMAGE" ]]; then
    echo "[FAIL] IMAGE is empty. Set IMAGE=ghcr.io/alanjiao1988/j-space-observation:<git-sha>"
    exit 1
fi
if [[ -z "$GHCR_USERNAME" ]]; then
    echo "[FAIL] GHCR_USERNAME is empty."
    exit 1
fi
if [[ -z "$GHCR_PAT" ]]; then
    echo "[FAIL] GHCR_PAT is empty. Provide it via environment variable only."
    exit 1
fi

# Provider gate: Container Apps still requires Microsoft.App registered.
APP_STATE="$(az provider show -n Microsoft.App --query registrationState -o tsv)"
if [[ "$APP_STATE" != "Registered" ]]; then
    echo "[FAIL] Microsoft.App is not Registered (state: ${APP_STATE}). Stop."
    exit 1
fi

if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
    echo "[CREATE] Resource group ${RESOURCE_GROUP}"
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --tags project=jspace-observation owner=alan purpose=research-pilot registry=ghcr environment=dev \
        -o table
fi

if ! az containerapp env show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_APP_ENV" >/dev/null 2>&1; then
    echo "[CREATE] Container Apps environment ${CONTAINER_APP_ENV}"
    az containerapp env create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_APP_ENV" \
        --location "$LOCATION" \
        --enable-workload-profiles true \
        --tags project=jspace-observation owner=alan purpose=research-pilot registry=ghcr environment=dev \
        -o table
fi

PROFILE_COUNT="$(az containerapp env workload-profile list \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_APP_ENV" \
    --query "[?name=='${GPU_WORKLOAD_PROFILE_NAME}'] | length(@)" \
    -o tsv)"
if [[ "$PROFILE_COUNT" == "0" ]]; then
    echo "[CREATE] GPU workload profile ${GPU_WORKLOAD_PROFILE_NAME} (${GPU_WORKLOAD_PROFILE})"
    az containerapp env workload-profile add \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_APP_ENV" \
        --workload-profile-name "$GPU_WORKLOAD_PROFILE_NAME" \
        --workload-profile-type "$GPU_WORKLOAD_PROFILE" \
        -o table
fi

# GHCR registry secret is passed as a Container Apps secret. The value is never echoed.
if ! az containerapp job show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_APP_JOB" >/dev/null 2>&1; then
    echo "[CREATE] Container Apps job ${CONTAINER_APP_JOB}"
    az containerapp job create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_APP_JOB" \
        --environment "$CONTAINER_APP_ENV" \
        --trigger-type Manual \
        --replica-timeout 7200 \
        --replica-retry-limit 0 \
        --replica-completion-count 1 \
        --parallelism 1 \
        --workload-profile-name "$GPU_WORKLOAD_PROFILE_NAME" \
        --image "$IMAGE" \
        --secrets "ghcr-pat=${GHCR_PAT}" \
        --registry-server "ghcr.io" \
        --registry-username "$GHCR_USERNAME" \
        --registry-password "secretref:ghcr-pat" \
        --cpu 2 \
        --memory 4Gi \
        --env-vars "HF_HOME=${HF_HOME}" "TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE}" "RESULTS_DIR=${RESULTS_DIR}" \
        --command "/bin/bash" \
        --args "-lc" "$JOB_COMMAND" \
        --tags project=jspace-observation owner=alan purpose=research-pilot registry=ghcr environment=dev \
        -o table
else
    echo "[UPDATE] Container Apps job ${CONTAINER_APP_JOB}"
    az containerapp job secret set \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_APP_JOB" \
        --secrets "ghcr-pat=${GHCR_PAT}" \
        -o none
    az containerapp job update \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_APP_JOB" \
        --image "$IMAGE" \
        --workload-profile-name "$GPU_WORKLOAD_PROFILE_NAME" \
        --env-vars "HF_HOME=${HF_HOME}" "TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE}" "RESULTS_DIR=${RESULTS_DIR}" \
        --command "/bin/bash" \
        --args "-lc" "$JOB_COMMAND" \
        -o table
fi

echo "[START] ${CONTAINER_APP_JOB}"
az containerapp job start --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_APP_JOB" -o table

LOG_FILE="$PROJECT_ROOT/docs/run_log.md"
{
    echo ""
    echo "## Azure GHCR job - $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    echo "- Command: \`bash infra/azure/scripts/05_run_job_ghcr.sh\`"
    echo "- Job: ${CONTAINER_APP_JOB}"
    echo "- Image: ${IMAGE}"
    echo "- Registry: ghcr.io (username set, PAT provided via secret; value not logged)"
    echo "- Container command: \`${JOB_COMMAND}\`"
    echo "- Note: This script creates/starts Azure resources when explicitly run."
} >> "$LOG_FILE"

echo "================================"
echo "[OK] GHCR job started"
echo "Check executions:"
echo "az containerapp job execution list -g ${RESOURCE_GROUP} -n ${CONTAINER_APP_JOB} -o table"
echo "================================"
