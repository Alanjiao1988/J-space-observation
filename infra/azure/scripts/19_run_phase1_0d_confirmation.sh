#!/usr/bin/env bash
# Launch the Phase 1.0D Track B headroom-confirmation generation run
# as a one-shot GPU Container Apps job.
#
# What this run produces: unlabelled generations. Section 4.3 makes a semantic
# label the only thing that may decide correctness, so the emitted pack reports
# AWAITING_SEMANTIC_REVIEW and carries no headroom number. Finalizing the
# decision is a separate step that needs the reviewer judgments.
#
# Phase 1.0C run 20260725T170041Z is untouched by this: different job, different
# image repository, different blob prefix, different artifact namespace.
#
# Execution posture (mirrors 08_run_phase05_jlens.sh):
#   * image referenced by digest only, never by tag, never a floating tag
#   * user-assigned managed identity for both ACR pull and Blob write
#   * no storage account key, no SAS, no connection string, no Azure Files
#   * replicaRetryLimit 0 so the platform never silently re-runs generation
#   * parallelism 1 / replicaCompletionCount 1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
CONTAINER_APP_ENV="cae-jspace-observation-sea-vnet2"
WORKLOAD_PROFILE_NAME="gpu-t4"
JOB_NAME="job-jspace-p10d-confirmation"
IDENTITY_NAME="id-jspace-aca-acrpull-sea"
BLOB_ACCOUNT="stjspacefiles0709085305"
BLOB_CONTAINER="jspace-results"
BLOB_PREFIX="phase1-headroom-confirmation"
IMAGE_REPOSITORY="j-space-observation-phase1-0d"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
RUN_ID="${JSPACE_CONFIRMATION_RUN_ID:-$(date -u +'%Y%m%dT%H%M%SZ')}"
REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-10800}"
GENERATION_TIMEOUT_SECONDS="${GENERATION_TIMEOUT_SECONDS:-10500}"

# Bind `python` to the authenticated absolute interpreter: the orchestrator VM
# has no `python` on PATH, only /usr/bin/python3.
readonly PYTHON_BIN="$(/usr/bin/readlink -f /usr/bin/python3)"
if [[ ! "$PYTHON_BIN" =~ ^/usr/bin/python3([.][0-9]+)?$ || ! -x "$PYTHON_BIN" ]]; then
    echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
    exit 1
fi
readonly PYTHON_OWNER="$(/usr/bin/stat -c '%u' "$PYTHON_BIN")"
readonly PYTHON_MODE="$(/usr/bin/stat -c '%a' "$PYTHON_BIN")"
if [[ "$PYTHON_OWNER" != "0" || ! "$PYTHON_MODE" =~ ^[0-7]{3,4}$ ]]; then
    echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
    exit 1
fi
if (( (8#$PYTHON_MODE & 8#022) != 0 )); then
    echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
    exit 1
fi
python() {
    "$PYTHON_BIN" -I "$@"
}
readonly -f python

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ ! "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] Run ID must be a UTC stamp of the form YYYYMMDDTHHMMSSZ"
    exit 1
fi
if [[ ! "$REPLICA_TIMEOUT" =~ ^[0-9]+$ \
    || ! "$GENERATION_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
    echo "[FAIL] Timeouts must be nonnegative integers"
    exit 1
fi
if (( GENERATION_TIMEOUT_SECONDS >= REPLICA_TIMEOUT )); then
    echo "[FAIL] In-container timeout must fire before the replica timeout"
    exit 1
fi
LAUNCHER_SHA="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Launcher worktree must be clean"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" cat-file -e "${PROJECT_SHA}^{commit}"; then
    echo "[FAIL] Image PROJECT_SHA must exist in local git history"
    exit 1
fi

LOGIN_SERVER="$(az acr show \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query loginServer -o tsv)"
if [[ -z "$LOGIN_SERVER" ]]; then
    echo "[FAIL] Could not resolve the registry login server"
    exit 1
fi
IMAGE_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
if [[ ! "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] No immutable Phase 1.0D image is tagged $PROJECT_SHA"
    exit 1
fi
IMAGE_DIGEST_REF="${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"

TAG_WRITE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --query changeableAttributes.writeEnabled -o tsv)"
TAG_DELETE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
MANIFEST_WRITE_ENABLED="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --query changeableAttributes.writeEnabled -o tsv)"
MANIFEST_DELETE_ENABLED="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
if [[ "${TAG_WRITE_ENABLED,,}" != "false" \
    || "${TAG_DELETE_ENABLED,,}" != "false" \
    || "${MANIFEST_WRITE_ENABLED,,}" != "false" \
    || "${MANIFEST_DELETE_ENABLED,,}" != "false" ]]; then
    echo "[FAIL] Phase 1.0D image is not locked; refusing to launch"
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
if [[ -z "$IDENTITY_ID" || -z "$IDENTITY_CLIENT_ID" ]]; then
    echo "[FAIL] Could not resolve the user-assigned managed identity"
    exit 1
fi
ENVIRONMENT_ID="$(az containerapp env show \
    --name "$CONTAINER_APP_ENV" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv)"
if [[ -z "$ENVIRONMENT_ID" ]]; then
    echo "[FAIL] Could not resolve the Container Apps environment"
    exit 1
fi
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
API_VERSION="2024-03-01"
JOB_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${JOB_NAME}?api-version=${API_VERSION}"

RECORD_DIR="${CONFIRMATION_RUN_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase1-0d-confirmation-${RUN_ID}}"
mkdir -p "$RECORD_DIR"
BODY_FILE="$RECORD_DIR/job_body.json"
JOB_FILE="$RECORD_DIR/job_state.json"

# One generation run per run ID. If the job already carries executions, the
# operator must supply a fresh run ID rather than silently overwrite evidence.
EXECUTION_LIST_FILE="$RECORD_DIR/existing_executions.json"
if az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output none; then
    az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --output json >"$EXECUTION_LIST_FILE"
    EXISTING_RUN_IDS="$(az containerapp job show \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'tags."run-id"' -o tsv)"
    if [[ "$EXISTING_RUN_IDS" == "$RUN_ID" ]]; then
        echo "[FAIL] Job already provisioned for run ID $RUN_ID; use a new run ID"
        exit 1
    fi
else
    printf '[]\n' >"$EXECUTION_LIST_FILE"
fi
EXECUTION_COUNT="$(python -c 'import json,sys; print(len(json.load(open(sys.argv[1], encoding="utf-8"))))' \
    "$EXECUTION_LIST_FILE")"

COMMAND="timeout --signal=TERM --kill-after=60s ${GENERATION_TIMEOUT_SECONDS}s python /workspace/scripts/run_phase1_0d_confirmation.py --mode generate --repo-root /workspace --output-root /workspace/runtime/results --upload-blob"

python - "$BODY_FILE" <<PY
import json
import sys
from pathlib import Path

environment = [
    {"name": "HF_HOME", "value": "/workspace/runtime/hf-cache"},
    {"name": "HUGGINGFACE_HUB_CACHE", "value": "/workspace/runtime/hf-cache/hub"},
    {"name": "TRANSFORMERS_CACHE", "value": "/workspace/runtime/hf-cache"},
    {"name": "RESULTS_DIR", "value": "/workspace/runtime/results"},
    {"name": "TMPDIR", "value": "/workspace/runtime/cache/tmp"},
    {"name": "HF_HUB_DISABLE_TELEMETRY", "value": "1"},
    {"name": "TOKENIZERS_PARALLELISM", "value": "false"},
    {"name": "PYTHONUNBUFFERED", "value": "1"},
    {"name": "AZURE_CLIENT_ID", "value": "$IDENTITY_CLIENT_ID"},
    {"name": "JSPACE_BLOB_ACCOUNT", "value": "$BLOB_ACCOUNT"},
    {"name": "JSPACE_BLOB_CONTAINER", "value": "$BLOB_CONTAINER"},
    {"name": "JSPACE_BLOB_PREFIX", "value": "$BLOB_PREFIX"},
    {"name": "JSPACE_CONFIRMATION_RUN_ID", "value": "$RUN_ID"},
    {"name": "JSPACE_CODE_COMMIT", "value": "$PROJECT_SHA"},
    {"name": "JSPACE_IMAGE_DIGEST", "value": "$IMAGE_DIGEST"},
    {"name": "JSPACE_HARDWARE", "value": "Azure Container Apps gpu-t4 workload profile, NVIDIA Tesla T4"},
]
body = {
    "location": "southeastasia",
    "identity": {
        "type": "UserAssigned",
        "userAssignedIdentities": {"$IDENTITY_ID": {}},
    },
    "tags": {
        "project": "jspace-observation",
        "phase": "1.0D",
        "track": "B",
        "stage": "headroom-confirmation-generation",
        "run-id": "$RUN_ID",
        "project-sha": "$PROJECT_SHA",
        "image-project-sha": "$PROJECT_SHA",
        "launcher-sha": "$LAUNCHER_SHA",
        "image-digest": "$IMAGE_DIGEST",
    },
    "properties": {
        "environmentId": "$ENVIRONMENT_ID",
        "workloadProfileName": "$WORKLOAD_PROFILE_NAME",
        "configuration": {
            "triggerType": "Manual",
            "replicaTimeout": $REPLICA_TIMEOUT,
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
                    "name": "confirmation",
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
Path(sys.argv[1]).write_text(
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
    echo "[FAIL] Timed out waiting for job provisioning"
    exit 1
fi

az rest --method get --url "$JOB_URL" --output json >"$JOB_FILE"
python - "$JOB_FILE" "$RUN_ID" "$PROJECT_SHA" "$IMAGE_DIGEST" \
    "$IMAGE_DIGEST_REF" "$WORKLOAD_PROFILE_NAME" <<'PY'
import json
import sys

path, run_id, project_sha, image_digest, image_ref, profile = sys.argv[1:7]
job = json.loads(open(path, encoding="utf-8").read())
tags = job.get("tags") or {}
properties = job.get("properties") or {}
configuration = properties.get("configuration") or {}
manual = configuration.get("manualTriggerConfig") or {}
template = properties.get("template") or {}
containers = template.get("containers") or []
identity = job.get("identity") or {}

failures = []
if tags.get("run-id") != run_id:
    failures.append("run-id tag mismatch")
if tags.get("project-sha") != project_sha:
    failures.append("project-sha tag mismatch")
if tags.get("image-digest") != image_digest:
    failures.append("image-digest tag mismatch")
if properties.get("workloadProfileName") != profile:
    failures.append("workload profile mismatch")
if configuration.get("replicaRetryLimit") != 0:
    failures.append("platform retry is enabled")
if configuration.get("triggerType") != "Manual":
    failures.append("trigger type is not Manual")
if manual.get("parallelism") != 1 or manual.get("replicaCompletionCount") != 1:
    failures.append("job is not a single-replica single-completion job")
if identity.get("type") != "UserAssigned":
    failures.append("job identity is not user-assigned")
if len(containers) != 1:
    failures.append("expected exactly one container")
else:
    container = containers[0]
    if container.get("image") != image_ref:
        failures.append("container image is not the pinned digest reference")
    env_names = {item.get("name") for item in container.get("env") or []}
    required = {
        "AZURE_CLIENT_ID",
        "JSPACE_BLOB_ACCOUNT",
        "JSPACE_BLOB_CONTAINER",
        "JSPACE_BLOB_PREFIX",
        "JSPACE_CONFIRMATION_RUN_ID",
        "JSPACE_CODE_COMMIT",
        "JSPACE_IMAGE_DIGEST",
    }
    missing = sorted(required - env_names)
    if missing:
        failures.append("missing environment variables: " + ", ".join(missing))
    forbidden = sorted(
        name
        for name in env_names
        if name
        and (
            "ACCOUNT_KEY" in name
            or "SAS" in name
            or "CONNECTION_STRING" in name
        )
    )
    if forbidden:
        failures.append("credential-bearing variables present: " + ", ".join(forbidden))
if template.get("volumes"):
    failures.append("job mounts volumes; managed identity to Blob only is required")

if failures:
    for failure in failures:
        print("[FAIL] " + failure)
    sys.exit(1)
print("[OK] Provisioned job matches the recorded launch parameters")
PY

EXECUTION_NAME="$(az containerapp job start \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query name -o tsv)"
if [[ -z "$EXECUTION_NAME" ]]; then
    echo "[FAIL] Job start returned no execution name"
    exit 1
fi

az containerapp job execution list \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output json >"$RECORD_DIR/executions_after_start.json"
EXECUTION_COUNT_AFTER="$(python -c 'import json,sys; print(len(json.load(open(sys.argv[1], encoding="utf-8"))))' \
    "$RECORD_DIR/executions_after_start.json")"
if (( EXECUTION_COUNT_AFTER != EXECUTION_COUNT + 1 )); then
    echo "[FAIL] Expected exactly one new execution after start"
    exit 1
fi

printf '%s\n' "$EXECUTION_NAME" >"$RECORD_DIR/execution_name.txt"
echo "[OK] job_name=$JOB_NAME"
echo "[OK] execution_name=$EXECUTION_NAME"
echo "[OK] run_id=$RUN_ID"
echo "[OK] image=$IMAGE_DIGEST_REF"
echo "[OK] blob_prefix=${BLOB_PREFIX}/${RUN_ID}"
echo "[OK] No platform retry; no Azure Files; managed identity only"
