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
AZURE_CLIENT_ID="${AZURE_CLIENT_ID:-}"
JSPACE_BLOB_ACCOUNT="${JSPACE_BLOB_ACCOUNT:-}"
JSPACE_BLOB_CONTAINER="${JSPACE_BLOB_CONTAINER:-}"
JSPACE_BLOB_PREFIX="${JSPACE_BLOB_PREFIX:-}"
JSPACE_RESULTS_ROOT="${JSPACE_RESULTS_ROOT:-}"
PYTHONPATH_VALUE="${PYTHONPATH_VALUE:-/workspace/src}"
ENABLE_RESULTS_MOUNT="${ENABLE_RESULTS_MOUNT:-false}"
STORAGE_MOUNT_NAME="${STORAGE_MOUNT_NAME:-jspace-results-storage}"
RESULTS_MOUNT_PATH="${RESULTS_MOUNT_PATH:-/mnt/results}"

if [[ "$ENABLE_RESULTS_MOUNT" == "true" && "${RESULTS_DIR:-/tmp/results}" == "/tmp/results" ]]; then
    RESULTS_DIR="$RESULTS_MOUNT_PATH"
fi

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
echo "Results mount enabled: ${ENABLE_RESULTS_MOUNT}"
echo "Blob export configured: $([[ -n "$JSPACE_BLOB_ACCOUNT" && -n "$JSPACE_BLOB_CONTAINER" ]] && echo yes || echo no)"
if [[ "$ENABLE_RESULTS_MOUNT" == "true" ]]; then
    echo "Storage mount name: ${STORAGE_MOUNT_NAME}"
    echo "Results mount path: ${RESULTS_MOUNT_PATH}"
fi
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

python - "$BODY_FILE" "$LOCATION" "$ENVIRONMENT_ID" "$ACR_IMAGE" "$ACR_LOGIN_SERVER" "$IDENTITY_ID" "$JOB_COMMAND" "$WORKLOAD_PROFILE_NAME" "$REPLICA_TIMEOUT" "$CPU_CORES" "$MEMORY" "$HF_HOME" "$TRANSFORMERS_CACHE" "$RESULTS_DIR" "$AZURE_CLIENT_ID" "$JSPACE_BLOB_ACCOUNT" "$JSPACE_BLOB_CONTAINER" "$JSPACE_BLOB_PREFIX" "$JSPACE_RESULTS_ROOT" "$PYTHONPATH_VALUE" "$ENABLE_RESULTS_MOUNT" "$STORAGE_MOUNT_NAME" "$RESULTS_MOUNT_PATH" <<'PY'
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
    azure_client_id,
    blob_account,
    blob_container,
    blob_prefix,
    results_root,
    pythonpath_value,
    enable_results_mount,
    storage_mount_name,
    results_mount_path,
) = sys.argv[1:]

use_results_mount = enable_results_mount.lower() == "true"
container = {
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
optional_env = {
    "AZURE_CLIENT_ID": azure_client_id,
    "JSPACE_BLOB_ACCOUNT": blob_account,
    "JSPACE_BLOB_CONTAINER": blob_container,
    "JSPACE_BLOB_PREFIX": blob_prefix,
    "JSPACE_RESULTS_ROOT": results_root,
    "PYTHONPATH": pythonpath_value,
}
for key, value in optional_env.items():
    if value:
        container["env"].append({"name": key, "value": value})
volumes = []
if use_results_mount:
    container["volumeMounts"] = [
        {
            "volumeName": "results",
            "mountPath": results_mount_path,
        }
    ]
    volumes.append(
        {
            "name": "results",
            "storageType": "AzureFile",
            "storageName": storage_mount_name,
        }
    )

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
            "containers": [container],
        },
    },
}
if volumes:
    body["properties"]["template"]["volumes"] = volumes

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
