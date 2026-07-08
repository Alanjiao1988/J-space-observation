#!/usr/bin/env bash
# Script: 06_run_job_acr_mi.sh
# Purpose: Create/update and start an Azure Container Apps Job using an ACR image
# with a user-assigned managed identity and AcrPull. No registry passwords.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
CONTAINER_APP_ENV="${CONTAINER_APP_ENV:-${CONTAINERAPPS_ENVIRONMENT:-cae-jspace-observation-sea}}"
WORKLOAD_PROFILE_NAME="${WORKLOAD_PROFILE_NAME:-gpu-t4}"
ACR_NAME="${ACR_NAME:-}"
ACR_LOGIN_SERVER="${ACR_LOGIN_SERVER:-}"
ACR_IMAGE="${ACR_IMAGE:-}"
IDENTITY_NAME="${IDENTITY_NAME:-id-jspace-aca-acrpull-sea}"
IDENTITY_ID="${IDENTITY_ID:-}"
JOB_NAME="${JOB_NAME:-job-jspace-acr-smoke}"
JOB_COMMAND="${JOB_COMMAND:-python -m pytest tests/ -q}"
REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-1800}"
LOCATION="${LOCATION:-southeastasia}"
CPU_CORES="${CPU_CORES:-2}"
MEMORY="${MEMORY:-4Gi}"
HF_HOME="${HF_HOME:-/tmp/models/huggingface}"
TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/tmp/models/huggingface}"
RESULTS_DIR="${RESULTS_DIR:-/tmp/results}"

if [[ -z "$ACR_LOGIN_SERVER" && -n "$ACR_NAME" ]]; then
    ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"
fi
if [[ -z "$ACR_IMAGE" ]]; then
    echo "[FAIL] ACR_IMAGE is required, e.g. <registry>.azurecr.io/j-space-observation:<tag>"
    exit 1
fi
if [[ -z "$ACR_LOGIN_SERVER" ]]; then
    ACR_LOGIN_SERVER="${ACR_IMAGE%%/*}"
fi
if [[ -z "$IDENTITY_ID" ]]; then
    IDENTITY_ID="$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)"
fi

echo "================================"
echo "Azure Container Apps Job (ACR managed identity)"
echo "================================"
echo "Resource group: ${RESOURCE_GROUP}"
echo "Environment: ${CONTAINER_APP_ENV}"
echo "Job: ${JOB_NAME}"
echo "Image: ${ACR_IMAGE}"
echo "Registry server: ${ACR_LOGIN_SERVER}"
echo "Identity: ${IDENTITY_NAME}"
echo "Command: ${JOB_COMMAND}"
echo "CPU: ${CPU_CORES}"
echo "Memory: ${MEMORY}"
echo

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
ENVIRONMENT_ID="$(az containerapp env show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_APP_ENV" \
    --query id \
    -o tsv)"
JOB_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${JOB_NAME}?api-version=2024-03-01"
BODY_FILE="$(mktemp)"
cleanup() {
    rm -f "$BODY_FILE"
}
trap cleanup EXIT

python - "$BODY_FILE" "$LOCATION" "$ENVIRONMENT_ID" "$ACR_IMAGE" "$ACR_LOGIN_SERVER" "$IDENTITY_ID" "$JOB_COMMAND" "$WORKLOAD_PROFILE_NAME" "$REPLICA_TIMEOUT" "$CPU_CORES" "$MEMORY" "$HF_HOME" "$TRANSFORMERS_CACHE" "$RESULTS_DIR" <<'PY'
import json
import sys

(
    body_file,
    location,
    environment_id,
    image,
    registry_server,
    identity_id,
    job_command,
    workload_profile,
    replica_timeout,
    cpu_cores,
    memory,
    hf_home,
    transformers_cache,
    results_dir,
) = sys.argv[1:]

body = {
    "location": location,
    "identity": {
        "type": "UserAssigned",
        "userAssignedIdentities": {
            identity_id: {}
        },
    },
    "tags": {
        "project": "jspace-observation",
        "owner": "alan",
        "purpose": "research-pilot",
        "registry": "acr",
        "environment": "dev",
    },
    "properties": {
        "environmentId": environment_id,
        "workloadProfileName": workload_profile,
        "configuration": {
            "triggerType": "Manual",
            "replicaTimeout": int(replica_timeout),
            "replicaRetryLimit": 0,
            "manualTriggerConfig": {
                "replicaCompletionCount": 1,
                "parallelism": 1,
            },
            "registries": [
                {
                    "server": registry_server,
                    "identity": identity_id,
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
                        "cpu": float(cpu_cores),
                        "memory": memory,
                    },
                }
            ],
        },
    },
}

with open(body_file, "w", encoding="utf-8") as f:
    json.dump(body, f)
PY

echo "[CREATE/UPDATE] Container Apps job ${JOB_NAME}"
az rest \
    --method put \
    --url "$JOB_URL" \
    --body "@${BODY_FILE}" \
    --headers "Content-Type=application/json" \
    -o table

echo "[START] ${JOB_NAME}"
az containerapp job start --resource-group "$RESOURCE_GROUP" --name "$JOB_NAME" -o table

LOG_FILE="$PROJECT_ROOT/docs/run_log.md"
{
    echo ""
    echo "## Azure ACR managed-identity job - $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    echo "- Command: \`bash infra/azure/scripts/06_run_job_acr_mi.sh\`"
    echo "- Job: ${JOB_NAME}"
    echo "- Image: ${ACR_IMAGE}"
    echo "- Registry: ${ACR_LOGIN_SERVER} via user-assigned managed identity"
    echo "- Container command: \`${JOB_COMMAND}\`"
} >> "$LOG_FILE"

echo "================================"
echo "[OK] ACR managed-identity job started"
echo "Check executions:"
echo "az containerapp job execution list -g ${RESOURCE_GROUP} -n ${JOB_NAME} -o table"
echo "================================"
