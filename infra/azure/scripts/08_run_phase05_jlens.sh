#!/usr/bin/env bash
# CAS-claim and start one primary Phase 0.5A job or its sole operational retry.

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
LAUNCH_INVOCATION_ID="${LAUNCH_INVOCATION_ID:-$(date -u +'%Y%m%d%H%M%S')-$$-${RANDOM}}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ "$ATTEMPT_KIND" != "primary" && "$ATTEMPT_KIND" != "operational-fix" ]]; then
    echo "[FAIL] ATTEMPT_KIND must be primary or operational-fix"
    exit 1
fi
if [[ ! "$LAUNCH_INVOCATION_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "[FAIL] LAUNCH_INVOCATION_ID contains invalid tag characters"
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
if [[ "$ATTEMPT_KIND" == "operational-fix" ]]; then
    if [[ -z "$RUN_ID_INPUT" || -z "$OPERATIONAL_FIX_NOTE" ]]; then
        echo "[FAIL] Retry requires the primary run ID and OPERATIONAL_FIX_NOTE"
        exit 1
    fi
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
if [[ "$PRIMARY_PROJECT_SHA" == "$PROJECT_SHA" ]]; then
    PRIMARY_IMAGE_DIGEST="$IMAGE_DIGEST"
else
    PRIMARY_IMAGE_DIGEST="$(az acr repository show-manifests \
        --name "$ACR_NAME" \
        --repository "$IMAGE_REPOSITORY" \
        --query "[?tags[?@=='${PRIMARY_PROJECT_SHA}']].digest | [0]" \
        -o tsv)"
fi
if [[ ! "$PRIMARY_IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Primary project-SHA image digest could not be resolved"
    exit 1
fi
PRIMARY_IMAGE_DIGEST_REF="${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${PRIMARY_IMAGE_DIGEST}"
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

API_VERSION="2024-03-01"
JOBS_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs?api-version=${API_VERSION}"
JOB_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${JOB_NAME}?api-version=${API_VERSION}"
RECORD_DIR="${JLENS_RUN_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase05-jlens-${RUN_ID}}"
mkdir -p "$RECORD_DIR"
BODY_FILE="$RECORD_DIR/.azure_phase05_jlens_job_body.json"
EXISTING_JOB_FILE="$RECORD_DIR/.azure_phase05_jlens_existing_job.json"
CLAIMED_JOB_FILE="$RECORD_DIR/.azure_phase05_jlens_claimed_job.json"
cleanup_files() {
    rm -f "$BODY_FILE" "$EXISTING_JOB_FILE" "$CLAIMED_JOB_FILE"
}
trap cleanup_files EXIT

JOB_COUNT="$(az rest \
    --method get \
    --url "$JOBS_URL" \
    --query "length(value[?name=='${JOB_NAME}'])" -o tsv)"
if [[ "$JOB_COUNT" != "0" && "$JOB_COUNT" != "1" ]]; then
    echo "[FAIL] Could not establish unique Container Apps job existence"
    exit 1
fi

EXECUTION_COUNT=0
PRIMARY_EXECUTION_STATUS=""
CAS_HEADER=""
if [[ "$ATTEMPT_KIND" == "primary" ]]; then
    if [[ "$JOB_COUNT" != "0" ]]; then
        echo "[FAIL] Existing job/launch claim requires manual intervention"
        exit 1
    fi
    CAS_HEADER="If-None-Match=*"
else
    if [[ "$JOB_COUNT" != "1" ]]; then
        echo "[FAIL] Operational retry requires exactly one existing primary job"
        exit 1
    fi
    az rest --method get --url "$JOB_URL" --output json >"$EXISTING_JOB_FILE"
    mapfile -t EXISTING_FIELDS < <(python - "$EXISTING_JOB_FILE" <<'PY'
import json
import sys

job = json.load(open(sys.argv[1], encoding="utf-8"))
tags = job.get("tags") or {}
containers = job.get("properties", {}).get("template", {}).get("containers", [])
container = containers[0] if containers else {}
environment = {
    item.get("name"): item.get("value") for item in container.get("env", [])
}
fields = [
    job.get("etag"),
    environment.get("JSPACE_PHASE05_RUN_ID"),
    environment.get("JSPACE_ATTEMPT_ID"),
    tags.get("project"),
    tags.get("phase"),
    tags.get("attempt-policy"),
    tags.get("run-id"),
    tags.get("project-sha"),
    tags.get("primary-project-sha"),
    tags.get("launch-attempt"),
    tags.get("launch-state"),
    tags.get("launch-invocation-id"),
    tags.get("image-digest"),
    container.get("image"),
    tags.get("prior-execution-status"),
]
for field in fields:
    print("" if field is None else field)
PY
)
    if [[ "${#EXISTING_FIELDS[@]}" -ne 15 ]]; then
        echo "[FAIL] Existing job claim fields could not be parsed"
        exit 1
    fi
    EXISTING_ETAG="${EXISTING_FIELDS[0]}"
    EXISTING_RUN_ID="${EXISTING_FIELDS[1]}"
    EXISTING_ATTEMPT="${EXISTING_FIELDS[2]}"
    EXISTING_PROJECT_TAG="${EXISTING_FIELDS[3]}"
    EXISTING_PHASE_TAG="${EXISTING_FIELDS[4]}"
    EXISTING_POLICY_TAG="${EXISTING_FIELDS[5]}"
    EXISTING_RUN_TAG="${EXISTING_FIELDS[6]}"
    EXISTING_PROJECT_SHA_TAG="${EXISTING_FIELDS[7]}"
    EXISTING_PRIMARY_SHA_TAG="${EXISTING_FIELDS[8]}"
    EXISTING_LAUNCH_ATTEMPT="${EXISTING_FIELDS[9]}"
    EXISTING_LAUNCH_STATE="${EXISTING_FIELDS[10]}"
    EXISTING_LAUNCH_INVOCATION="${EXISTING_FIELDS[11]}"
    EXISTING_IMAGE_DIGEST_TAG="${EXISTING_FIELDS[12]}"
    EXISTING_IMAGE_REF="${EXISTING_FIELDS[13]}"
    EXISTING_PRIOR_STATUS_TAG="${EXISTING_FIELDS[14]}"
    if [[ -z "$EXISTING_ETAG" \
        || -z "$EXISTING_LAUNCH_INVOCATION" \
        || "$EXISTING_RUN_ID" != "$RUN_ID" \
        || "$EXISTING_ATTEMPT" != "primary" \
        || "$EXISTING_PROJECT_TAG" != "jspace-observation" \
        || "$EXISTING_PHASE_TAG" != "0.5A" \
        || "$EXISTING_POLICY_TAG" != "one-primary-one-operational-fix" \
        || "$EXISTING_RUN_TAG" != "$RUN_ID" \
        || "$EXISTING_PROJECT_SHA_TAG" != "$PRIMARY_PROJECT_SHA" \
        || "$EXISTING_PRIMARY_SHA_TAG" != "$PRIMARY_PROJECT_SHA" \
        || "$EXISTING_LAUNCH_ATTEMPT" != "primary" \
        || "$EXISTING_LAUNCH_STATE" != "claimed-for-start" \
        || "$EXISTING_IMAGE_DIGEST_TAG" != "$PRIMARY_IMAGE_DIGEST" \
        || "$EXISTING_IMAGE_REF" != "$PRIMARY_IMAGE_DIGEST_REF" \
        || "$EXISTING_PRIOR_STATUS_TAG" != "none" ]]; then
        echo "[FAIL] Existing job is not the matching primary launch claim"
        exit 1
    fi
    EXECUTION_COUNT="$(az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'length(@)' -o tsv)"
    if [[ "$EXECUTION_COUNT" -ne 1 ]]; then
        echo "[FAIL] Retry requires exactly one primary execution"
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
            echo "[FAIL] Primary is not a failed terminal execution: $PRIMARY_EXECUTION_STATUS"
            exit 1
            ;;
    esac
    CAS_HEADER="If-Match=${EXISTING_ETAG}"
fi

BLOB_PREFIX="phase05-jlens-feasibility/${RUN_ID}"
if [[ -z "$CAS_HEADER" ]]; then
    echo "[FAIL] Distributed launch CAS header was not established"
    exit 1
fi
RESUME_PREFIX=""
if [[ "$ATTEMPT_KIND" == "operational-fix" ]]; then
    RESUME_PREFIX="${BLOB_PREFIX}/attempts/primary"
fi
COMPATIBILITY_FLAG=""
if [[ "$AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED" == "true" ]]; then
    COMPATIBILITY_FLAG=" --authorized-compatibility-fix-attempted"
fi
COMMAND="timeout --signal=TERM --kill-after=30s 6900s python /workspace/scripts/phase05_jlens_feasibility.py --output-dir /workspace/runtime/results --resume${COMPATIBILITY_FLAG}"
PRIOR_STATUS_TAG="${PRIMARY_EXECUTION_STATUS:-none}"

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
        "launch-attempt": "$ATTEMPT_KIND",
        "launch-state": "claimed-for-start",
        "launch-invocation-id": "$LAUNCH_INVOCATION_ID",
        "image-digest": "$IMAGE_DIGEST",
        "prior-execution-status": "$PRIOR_STATUS_TAG",
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

if ! az rest \
    --method put \
    --url "$JOB_URL" \
    --headers "Content-Type=application/json" "$CAS_HEADER" \
    --body "@$BODY_FILE" \
    --output none; then
    echo "[FAIL] Distributed launch claim lost or failed (409/412/stale/unknown)"
    exit 1
fi

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
            echo "[FAIL] Job claim provisioning ended in $PROVISIONING_STATE"
            exit 1
            ;;
    esac
    sleep 5
done
if [[ "$PROVISIONING_STATE" != "Succeeded" ]]; then
    echo "[FAIL] Timed out waiting for claimed job provisioning"
    exit 1
fi

verify_claimed_job() {
    local file="$1"
    az rest --method get --url "$JOB_URL" --output json >"$file"
    python - "$file" "$RUN_ID" "$ATTEMPT_KIND" "$PROJECT_SHA" \
        "$PRIMARY_PROJECT_SHA" "$LAUNCH_INVOCATION_ID" "$IMAGE_DIGEST" \
        "$IMAGE_DIGEST_REF" "$PRIOR_STATUS_TAG" <<'PY'
import json
import sys

(
    path,
    run_id,
    attempt,
    project_sha,
    primary_sha,
    invocation_id,
    image_digest,
    image_ref,
    prior_status,
) = sys.argv[1:]
job = json.load(open(path, encoding="utf-8"))
tags = job.get("tags") or {}
containers = job.get("properties", {}).get("template", {}).get("containers", [])
if len(containers) != 1:
    raise SystemExit("claimed job must have exactly one container")
container = containers[0]
environment = {
    item.get("name"): item.get("value") for item in container.get("env", [])
}
expected_tags = {
    "project": "jspace-observation",
    "phase": "0.5A",
    "attempt-policy": "one-primary-one-operational-fix",
    "run-id": run_id,
    "project-sha": project_sha,
    "primary-project-sha": primary_sha,
    "launch-attempt": attempt,
    "launch-state": "claimed-for-start",
    "launch-invocation-id": invocation_id,
    "image-digest": image_digest,
    "prior-execution-status": prior_status,
}
actual_tags = {key: tags.get(key) for key in expected_tags}
if actual_tags != expected_tags:
    raise SystemExit(f"claimed launch tag mismatch: {actual_tags}")
if environment.get("JSPACE_PHASE05_RUN_ID") != run_id:
    raise SystemExit("claimed run ID mismatch")
if environment.get("JSPACE_ATTEMPT_ID") != attempt:
    raise SystemExit("claimed attempt mismatch")
if container.get("image") != image_ref:
    raise SystemExit("claimed image digest mismatch")
if not job.get("etag"):
    raise SystemExit("claimed job ETag missing")
print(job["etag"])
PY
}

CLAIMED_ETAG="$(verify_claimed_job "$CLAIMED_JOB_FILE")"
POST_CLAIM_EXECUTION_COUNT="$(az containerapp job execution list \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query 'length(@)' -o tsv)"
if [[ "$POST_CLAIM_EXECUTION_COUNT" -ne "$EXECUTION_COUNT" ]]; then
    echo "[FAIL] Execution count changed while launch claim was established"
    exit 1
fi
if [[ "$ATTEMPT_KIND" == "operational-fix" ]]; then
    REVALIDATED_PRIMARY_STATUS="$(az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query '[0].properties.status' -o tsv)"
    if [[ "$REVALIDATED_PRIMARY_STATUS" != "$PRIMARY_EXECUTION_STATUS" ]]; then
        echo "[FAIL] Primary execution status changed under retry claim"
        exit 1
    fi
fi

# A second GET immediately before start must retain the exact CAS winner.
PRESTART_ETAG="$(verify_claimed_job "$CLAIMED_JOB_FILE")"
if [[ "$PRESTART_ETAG" != "$CLAIMED_ETAG" ]]; then
    echo "[FAIL] Claimed job changed before start; manual intervention required"
    exit 1
fi

EXECUTION_NAME="$(az containerapp job start \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query name -o tsv)"
if [[ -z "$EXECUTION_NAME" ]]; then
    echo "[FAIL] Job start returned no execution name"
    exit 1
fi
EXPECTED_EXECUTION_COUNT=$((EXECUTION_COUNT + 1))
STARTED_EXECUTION_COUNT=0
ACTUAL_EXECUTION_COUNT=0
for _ in $(seq 1 60); do
    STARTED_EXECUTION_COUNT="$(az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?name=='${EXECUTION_NAME}'] | length(@)" -o tsv)"
    ACTUAL_EXECUTION_COUNT="$(az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'length(@)' -o tsv)"
    if [[ "$ACTUAL_EXECUTION_COUNT" -gt "$EXPECTED_EXECUTION_COUNT" ]]; then
        echo "[FAIL] Concurrent or duplicate execution appeared after start"
        exit 1
    fi
    if [[ "$STARTED_EXECUTION_COUNT" -eq 1 \
        && "$ACTUAL_EXECUTION_COUNT" -eq "$EXPECTED_EXECUTION_COUNT" ]]; then
        break
    fi
    sleep 2
done
if [[ "$STARTED_EXECUTION_COUNT" -ne 1 \
    || "$ACTUAL_EXECUTION_COUNT" -ne "$EXPECTED_EXECUTION_COUNT" ]]; then
    echo "[FAIL] Started execution name/count could not be verified"
    exit 1
fi
POSTSTART_ETAG="$(verify_claimed_job "$CLAIMED_JOB_FILE")"

python - "$RECORD_DIR/phase05_jlens_job_start.json" "$OPERATIONAL_FIX_NOTE" <<PY
import json
import sys
from pathlib import Path

record = {
    "schema_version": "phase05-jlens-job-start-v2",
    "started_at_utc": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "run_id": "$RUN_ID",
    "attempt": "$ATTEMPT_KIND",
    "launch_invocation_id": "$LAUNCH_INVOCATION_ID",
    "launch_claim_etag": "$CLAIMED_ETAG",
    "post_start_job_etag": "$POSTSTART_ETAG",
    "launch_state": "claimed-for-start",
    "operational_fix_note": sys.argv[2],
    "authorized_compatibility_fix_attempted": (
        "$AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED" == "true"
    ),
    "job_name": "$JOB_NAME",
    "execution_name": "$EXECUTION_NAME",
    "execution_name_verified": True,
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

rm -f "$BODY_FILE" "$EXISTING_JOB_FILE" "$CLAIMED_JOB_FILE"
echo "[OK] Started and verified $EXECUTION_NAME ($ATTEMPT_KIND)"
echo "[OK] Launch claim: $LAUNCH_INVOCATION_ID etag=$CLAIMED_ETAG"
echo "[OK] Blob prefix: $BLOB_PREFIX"
echo "[OK] No platform retry; no Azure Files; managed identity only"
echo "[OK] Record: $RECORD_DIR/phase05_jlens_job_start.json"
