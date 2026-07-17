#!/usr/bin/env bash
# Run one primary Phase 0.5A attempt or its sole documented operational retry.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
CONTAINER_APP_ENV="cae-jspace-observation-sea-vnet2"
WORKLOAD_PROFILE_NAME="gpu-t4"
JOB_NAME="job-jspace-p05-jlens"
IDENTITY_NAME="id-jspace-aca-acrpull-sea"
BLOB_ACCOUNT="stjspacefiles0709085305"
BLOB_CONTAINER="jspace-results"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
PRIMARY_PROJECT_SHA_INPUT="${PRIMARY_PROJECT_SHA:-}"
IMAGE_REPOSITORY="j-space-observation-jlens"
ATTEMPT_KIND="${ATTEMPT_KIND:-primary}"
RUN_ID_INPUT="${JSPACE_PHASE05_RUN_ID:-}"
RUN_ID="${RUN_ID_INPUT:-$(date -u +'%Y%m%dT%H%M%SZ')}"
OPERATIONAL_FIX_NOTE="${OPERATIONAL_FIX_NOTE:-}"
AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED="${AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED:-false}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ "$ATTEMPT_KIND" != "primary" && "$ATTEMPT_KIND" != "operational-fix" ]]; then
    echo "[FAIL] ATTEMPT_KIND must be primary or operational-fix"
    exit 1
fi
if [[ "$ATTEMPT_KIND" == "primary" ]]; then
    if [[ -n "$PRIMARY_PROJECT_SHA_INPUT" \
        && "$PRIMARY_PROJECT_SHA_INPUT" != "$PROJECT_SHA" ]]; then
        echo "[FAIL] Primary PRIMARY_PROJECT_SHA must equal PROJECT_SHA"
        exit 1
    fi
    PRIMARY_PROJECT_SHA="$PROJECT_SHA"
else
    if [[ ! "$PRIMARY_PROJECT_SHA_INPUT" =~ ^[0-9a-f]{40}$ ]]; then
        echo "[FAIL] Operational retry requires the primary 40-hex PRIMARY_PROJECT_SHA"
        exit 1
    fi
    PRIMARY_PROJECT_SHA="$PRIMARY_PROJECT_SHA_INPUT"
fi
if [[ "$AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED" != "true" \
    && "$AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED" != "false" ]]; then
    echo "[FAIL] AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED must be true or false"
    exit 1
fi
if [[ "$ATTEMPT_KIND" == "primary" \
    && "$AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED" == "true" ]]; then
    echo "[FAIL] A compatibility fix cannot be declared on the primary attempt"
    exit 1
fi
if [[ ! "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] JSPACE_PHASE05_RUN_ID must be a UTC timestamp like 20260716T080000Z"
    exit 1
fi

LOGIN_SERVER="$(az acr show \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query loginServer -o tsv)"
IMAGE_TAG_REF="${LOGIN_SERVER}/${IMAGE_REPOSITORY}:${PROJECT_SHA}"
IMAGE_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
if [[ ! "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Exact project-SHA image does not exist: $IMAGE_TAG_REF"
    exit 1
fi
IMAGE_DIGEST_REF="${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"
TAG_WRITE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --query writeEnabled -o tsv)"
TAG_DELETE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --query deleteEnabled -o tsv)"
MANIFEST_WRITE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --query writeEnabled -o tsv)"
MANIFEST_DELETE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --query deleteEnabled -o tsv)"
if [[ "${TAG_WRITE_ENABLED,,}" != "false" \
    || "${TAG_DELETE_ENABLED,,}" != "false" \
    || "${MANIFEST_WRITE_ENABLED,,}" != "false" \
    || "${MANIFEST_DELETE_ENABLED,,}" != "false" ]]; then
    echo "[FAIL] Refusing to run an unlocked ACR tag or manifest"
    exit 1
fi

PUBLIC_NETWORK="$(az storage account show \
    --name "$BLOB_ACCOUNT" \
    --query publicNetworkAccess -o tsv)"
if [[ "$PUBLIC_NETWORK" != "Disabled" ]]; then
    echo "[FAIL] Blob account public network access must be Disabled"
    exit 1
fi

IDENTITY_ID="$(az identity show \
    --name "$IDENTITY_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv)"
IDENTITY_CLIENT_ID="$(az identity show \
    --name "$IDENTITY_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query clientId -o tsv)"
ENVIRONMENT_ID="$(az containerapp env show \
    --name "$CONTAINER_APP_ENV" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv)"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"

JOB_EXISTS=false
PRIMARY_EXECUTION_STATUS=""
if az containerapp job show \
    --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    JOB_EXISTS=true
    EXECUTION_COUNT="$(az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'length(@)' -o tsv)"
else
    EXECUTION_COUNT=0
fi
if [[ "$ATTEMPT_KIND" == "primary" && "$EXECUTION_COUNT" -ne 0 ]]; then
    echo "[FAIL] Primary attempt is allowed only before any job execution"
    exit 1
fi
if [[ "$ATTEMPT_KIND" == "operational-fix" ]]; then
    if [[ -z "$RUN_ID_INPUT" ]]; then
        echo "[FAIL] Operational retry must set the primary JSPACE_PHASE05_RUN_ID"
        exit 1
    fi
    if [[ "$EXECUTION_COUNT" -ne 1 ]]; then
        echo "[FAIL] The sole operational retry requires exactly one prior execution"
        exit 1
    fi
    if [[ -z "$OPERATIONAL_FIX_NOTE" ]]; then
        echo "[FAIL] OPERATIONAL_FIX_NOTE must document the operational correction"
        exit 1
    fi
    if [[ "$JOB_EXISTS" != "true" ]]; then
        echo "[FAIL] Operational retry requires the existing primary job"
        exit 1
    fi
    PRIMARY_EXECUTION_STATUS="$(az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query '[0].properties.status' -o tsv)"
    case "$PRIMARY_EXECUTION_STATUS" in
        Failed|Stopped|Canceled|Cancelled)
            ;;
        Succeeded)
            echo "[FAIL] A succeeded primary execution must never be retried"
            exit 1
            ;;
        *)
            echo "[FAIL] Primary execution is not a failed terminal execution: $PRIMARY_EXECUTION_STATUS"
            exit 1
            ;;
    esac
    EXISTING_RUN_ID="$(az containerapp job show \
        --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
        --query 'properties.template.containers[0].env[?name==`JSPACE_PHASE05_RUN_ID`].value | [0]' \
        -o tsv)"
    EXISTING_ATTEMPT="$(az containerapp job show \
        --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
        --query 'properties.template.containers[0].env[?name==`JSPACE_ATTEMPT_ID`].value | [0]' \
        -o tsv)"
    EXISTING_PROJECT_TAG="$(az containerapp job show \
        --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
        --query 'tags.project' -o tsv)"
    EXISTING_PHASE_TAG="$(az containerapp job show \
        --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
        --query 'tags.phase' -o tsv)"
    EXISTING_POLICY_TAG="$(az containerapp job show \
        --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
        --query 'tags."attempt-policy"' -o tsv)"
    EXISTING_RUN_TAG="$(az containerapp job show \
        --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
        --query 'tags."run-id"' -o tsv)"
    EXISTING_PROJECT_SHA_TAG="$(az containerapp job show \
        --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
        --query 'tags."project-sha"' -o tsv)"
    EXISTING_PRIMARY_SHA_TAG="$(az containerapp job show \
        --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
        --query 'tags."primary-project-sha"' -o tsv)"
    if [[ "$EXISTING_RUN_ID" != "$RUN_ID" \
        || "$EXISTING_ATTEMPT" != "primary" \
        || "$EXISTING_PROJECT_TAG" != "jspace-observation" \
        || "$EXISTING_PHASE_TAG" != "0.5A" \
        || "$EXISTING_POLICY_TAG" != "one-primary-one-operational-fix" \
        || "$EXISTING_RUN_TAG" != "$RUN_ID" \
        || "$EXISTING_PROJECT_SHA_TAG" != "$PRIMARY_PROJECT_SHA" \
        || "$EXISTING_PRIMARY_SHA_TAG" != "$PRIMARY_PROJECT_SHA" ]]; then
        echo "[FAIL] Existing job does not match the sole primary provenance"
        exit 1
    fi
fi
if [[ "$EXECUTION_COUNT" -ge 2 ]]; then
    echo "[FAIL] Maximum one primary plus one operational-fix retry has been reached"
    exit 1
fi

BLOB_PREFIX="phase05-jlens-feasibility/${RUN_ID}"
RESUME_PREFIX=""
if [[ "$ATTEMPT_KIND" == "operational-fix" ]]; then
    RESUME_PREFIX="${BLOB_PREFIX}/attempts/primary"
fi
COMPATIBILITY_FLAG=""
if [[ "$AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED" == "true" ]]; then
    COMPATIBILITY_FLAG=" --authorized-compatibility-fix-attempted"
fi
COMMAND="timeout --signal=TERM --kill-after=30s 6900s python /workspace/scripts/phase05_jlens_feasibility.py --output-dir /workspace/runtime/results --resume${COMPATIBILITY_FLAG}"
JOB_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${JOB_NAME}?api-version=2024-03-01"
RECORD_DIR="${JLENS_RUN_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase05-jlens-${RUN_ID}}"
mkdir -p "$RECORD_DIR"
BODY_FILE="$RECORD_DIR/.azure_phase05_jlens_job_body.json"
cleanup_body() {
    rm -f "$BODY_FILE"
}
trap cleanup_body EXIT

python - "$BODY_FILE" <<PY
import json
from pathlib import Path

environment = [
    {"name": "HF_HOME", "value": "/workspace/runtime/hf-cache"},
    {"name": "HUGGINGFACE_HUB_CACHE", "value": "/workspace/runtime/hf-cache/hub"},
    {"name": "TRANSFORMERS_CACHE", "value": "/workspace/runtime/hf-cache"},
    {"name": "RESULTS_DIR", "value": "/workspace/runtime/results"},
    {"name": "TMPDIR", "value": "/workspace/runtime/cache/tmp"},
    {"name": "AZURE_CLIENT_ID", "value": "$IDENTITY_CLIENT_ID"},
    {"name": "JSPACE_BLOB_ACCOUNT", "value": "$BLOB_ACCOUNT"},
    {"name": "JSPACE_BLOB_CONTAINER", "value": "$BLOB_CONTAINER"},
    {"name": "JSPACE_BLOB_PREFIX", "value": "$BLOB_PREFIX"},
    {"name": "JSPACE_PHASE05_RUN_ID", "value": "$RUN_ID"},
    {"name": "JSPACE_ATTEMPT_ID", "value": "$ATTEMPT_KIND"},
]
if "$RESUME_PREFIX":
    environment.append(
        {"name": "JSPACE_BLOB_RESUME_PREFIX", "value": "$RESUME_PREFIX"}
    )

body = {
    "location": "southeastasia",
    "identity": {
        "type": "UserAssigned",
        "userAssignedIdentities": {"$IDENTITY_ID": {}},
    },
    "tags": {
        "project": "jspace-observation",
        "phase": "0.5A",
        "attempt-policy": "one-primary-one-operational-fix",
        "run-id": "$RUN_ID",
        "project-sha": "$PROJECT_SHA",
        "primary-project-sha": "$PRIMARY_PROJECT_SHA",
    },
    "properties": {
        "environmentId": "$ENVIRONMENT_ID",
        "workloadProfileName": "$WORKLOAD_PROFILE_NAME",
        "configuration": {
            "triggerType": "Manual",
            "replicaTimeout": 7200,
            "replicaRetryLimit": 0,
            "manualTriggerConfig": {
                "replicaCompletionCount": 1,
                "parallelism": 1,
            },
            "registries": [
                {"server": "$LOGIN_SERVER", "identity": "$IDENTITY_ID"}
            ],
        },
        "template": {
            "containers": [
                {
                    "name": "jlens",
                    "image": "$IMAGE_DIGEST_REF",
                    "command": ["/bin/sh"],
                    "args": ["-lc", "$COMMAND"],
                    "env": environment,
                    "resources": {"cpu": 8.0, "memory": "56Gi"},
                }
            ]
        },
    },
}
Path("$BODY_FILE").write_text(
    json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

az rest \
    --method put \
    --url "$JOB_URL" \
    --headers "Content-Type=application/json" \
    --body "@$BODY_FILE" \
    --output none
PROVISIONING_STATE=""
for _ in $(seq 1 120); do
    PROVISIONING_STATE="$(az rest \
        --method get \
        --url "$JOB_URL" \
        --query properties.provisioningState -o tsv)"
    case "$PROVISIONING_STATE" in
        Succeeded)
            break
            ;;
        Failed|Canceled|Cancelled|Deleted)
            echo "[FAIL] Job provisioning ended in $PROVISIONING_STATE"
            exit 1
            ;;
    esac
    sleep 5
done
if [[ "$PROVISIONING_STATE" != "Succeeded" ]]; then
    echo "[FAIL] Timed out waiting for job provisioningState=Succeeded"
    exit 1
fi
EXECUTION_NAME="$(az containerapp job start \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query name -o tsv)"
rm -f "$BODY_FILE"

python - "$RECORD_DIR/phase05_jlens_job_start.json" "$OPERATIONAL_FIX_NOTE" <<PY
import json
import sys
from pathlib import Path

record = {
    "schema_version": "phase05-jlens-job-start-v1",
    "started_at_utc": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "run_id": "$RUN_ID",
    "attempt": "$ATTEMPT_KIND",
    "operational_fix_note": sys.argv[2],
    "authorized_compatibility_fix_attempted": (
        "$AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED" == "true"
    ),
    "job_name": "$JOB_NAME",
    "execution_name": "$EXECUTION_NAME",
    "environment": "$CONTAINER_APP_ENV",
    "workload_profile": "$WORKLOAD_PROFILE_NAME",
    "replicas": 1,
    "gpu_type": "T4",
    "gpu_count": 1,
    "timeout_seconds": 7200,
    "application_watchdog_seconds": 6900,
    "platform_retry_limit": 0,
    "provisioning_state_before_start": "$PROVISIONING_STATE",
    "primary_execution_status": "$PRIMARY_EXECUTION_STATUS",
    "identity": "$IDENTITY_NAME",
    "blob_account": "$BLOB_ACCOUNT",
    "blob_container": "$BLOB_CONTAINER",
    "blob_prefix": "$BLOB_PREFIX",
    "blob_public_network_access": "$PUBLIC_NETWORK",
    "azure_files_used": False,
    "image": "$IMAGE_DIGEST_REF",
    "image_tag_ref": "$IMAGE_TAG_REF",
    "image_digest_ref": "$IMAGE_DIGEST_REF",
    "image_digest": "$IMAGE_DIGEST",
    "project_sha": "$PROJECT_SHA",
    "primary_project_sha": "$PRIMARY_PROJECT_SHA",
}
Path("$RECORD_DIR/phase05_jlens_job_start.json").write_text(
    json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

echo "[OK] Started $EXECUTION_NAME ($ATTEMPT_KIND)"
echo "[OK] Blob prefix: $BLOB_PREFIX"
echo "[OK] No platform retry; no Azure Files; managed identity only"
echo "[OK] Record: $RECORD_DIR/phase05_jlens_job_start.json"
