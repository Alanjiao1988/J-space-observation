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
GHCR_USERNAME="${GHCR_USERNAME:-Alanjiao1988}"
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
TOKEN_TO_USE="$GHCR_PAT"
TOKEN_SOURCE="GHCR_PAT"
if [[ -z "$TOKEN_TO_USE" ]] && command -v gh >/dev/null 2>&1; then
    TOKEN_TO_USE="$(gh auth token 2>/dev/null || true)"
    TOKEN_SOURCE="gh auth token"
fi
if [[ -z "$TOKEN_TO_USE" ]]; then
    echo "[FAIL] No GHCR token available. Set GHCR_PAT in the environment or configure gh auth."
    echo "       Do not paste tokens into chat, logs, or repo files."
    exit 1
fi
echo "GHCR token source: ${TOKEN_SOURCE}"

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
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
ENVIRONMENT_ID="$(az containerapp env show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_APP_ENV" \
    --query id \
    -o tsv)"
JOB_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${CONTAINER_APP_JOB}?api-version=2024-03-01"
BODY_FILE="$(mktemp)"
cleanup() {
    rm -f "$BODY_FILE"
}
trap cleanup EXIT

python - "$BODY_FILE" "$LOCATION" "$ENVIRONMENT_ID" "$IMAGE" "$GHCR_USERNAME" "$TOKEN_TO_USE" "$JOB_COMMAND" "$HF_HOME" "$TRANSFORMERS_CACHE" "$RESULTS_DIR" "$GPU_WORKLOAD_PROFILE_NAME" <<'PY'
import json
import sys

(
    body_file,
    location,
    environment_id,
    image,
    ghcr_username,
    token,
    job_command,
    hf_home,
    transformers_cache,
    results_dir,
    workload_profile,
) = sys.argv[1:]

body = {
    "location": location,
    "tags": {
        "project": "jspace-observation",
        "owner": "alan",
        "purpose": "research-pilot",
        "registry": "ghcr",
        "environment": "dev",
    },
    "properties": {
        "environmentId": environment_id,
        "workloadProfileName": workload_profile,
        "configuration": {
            "triggerType": "Manual",
            "replicaTimeout": 7200,
            "replicaRetryLimit": 0,
            "manualTriggerConfig": {
                "replicaCompletionCount": 1,
                "parallelism": 1,
            },
            "secrets": [
                {"name": "ghcr-pat", "value": token},
            ],
            "registries": [
                {
                    "server": "ghcr.io",
                    "username": ghcr_username,
                    "passwordSecretRef": "ghcr-pat",
                }
            ],
        },
        "template": {
            "containers": [
                {
                    "name": "main",
                    "image": image,
                    "command": ["/bin/sh"],
                    "args": ["-lc", job_command],
                    "env": [
                        {"name": "HF_HOME", "value": hf_home},
                        {"name": "TRANSFORMERS_CACHE", "value": transformers_cache},
                        {"name": "RESULTS_DIR", "value": results_dir},
                    ],
                    "resources": {
                        "cpu": 2,
                        "memory": "4Gi",
                    },
                }
            ],
        },
    },
}

with open(body_file, "w", encoding="utf-8") as f:
    json.dump(body, f)
PY

echo "[CREATE/UPDATE] Container Apps job ${CONTAINER_APP_JOB}"
az rest \
    --method put \
    --url "$JOB_URL" \
    --body "@${BODY_FILE}" \
    --headers "Content-Type=application/json" \
    -o table

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
