#!/usr/bin/env bash
# Create and start the Phase 0.5B J-lens saturation job exactly once.
#
# This launcher is deliberately separate from 08_run_phase05_jlens.sh so the
# Phase 0.5A job definition, its execution history, and its launch-claim
# namespace are left untouched. Exactly-once execution is enforced here by
# refusing to touch a job that already exists, by requiring a zero execution
# count before start, and by verifying the persisted job body before and after
# the single start. Blob uploads additionally use overwrite=false, so a second
# run against the same run id fails loudly instead of replacing evidence.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

readonly PYTHON_BIN="$(/usr/bin/readlink -f /usr/bin/python3)"
readonly PYTHON_MODE="$(/usr/bin/stat -c '%a' "$PYTHON_BIN" 2>/dev/null || true)"
if [[ ! "$PYTHON_BIN" =~ ^/usr/bin/python3([.][0-9]+)?$ \
    || ! -x "$PYTHON_BIN" \
    || "$(/usr/bin/stat -c '%u' "$PYTHON_BIN" 2>/dev/null || true)" != "0" \
    || ! "$PYTHON_MODE" =~ ^[0-7]{3,4}$ ]]; then
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

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
CONTAINER_APP_ENV="cae-jspace-observation-sea-vnet2"
WORKLOAD_PROFILE_NAME="gpu-t4"
JOB_NAME="job-jspace-p05-jlens-saturation"
IDENTITY_NAME="id-jspace-aca-acrpull-sea"
BLOB_ACCOUNT="stjspacefiles0709085305"
BLOB_CONTAINER="jspace-results"
IMAGE_REPOSITORY="j-space-observation-jlens"
PHASE_TAG="0.5B"
TRACK_TAG="track-a"
ATTEMPT_KIND="primary"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
RUN_ID="${JSPACE_PHASE05B_RUN_ID:-$(date -u +'%Y%m%dT%H%M%SZ')}"
DIM_BATCH="${JSPACE_JLENS_DIM_BATCH:-1}"
RECORD_DIR="${JLENS_SATURATION_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase05b-jlens-${RUN_ID}}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ ! "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] RUN_ID must be a UTC stamp like 20260726T031500Z"
    exit 1
fi
if [[ "$DIM_BATCH" != "1" && "$DIM_BATCH" != "2" ]]; then
    echo "[FAIL] DIM_BATCH must be 1 or 2"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Refusing to launch from a dirty worktree"
    exit 1
fi
if [[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] HEAD must equal PROJECT_SHA"
    exit 1
fi

LOGIN_SERVER="$(az acr show --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"
if [[ -z "$LOGIN_SERVER" ]]; then
    echo "[FAIL] Could not resolve ACR login server"
    exit 1
fi

# The image must already exist, tagged with the exact source commit.
IMAGE_DIGEST="$(az acr manifest list-metadata \
    --registry "$ACR_NAME" \
    --name "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" -o tsv)"
if [[ ! "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] No immutable image tagged $PROJECT_SHA in $IMAGE_REPOSITORY"
    exit 1
fi
IMAGE_DIGEST_REF="${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"

IDENTITY_ID="$(az identity show --name "$IDENTITY_NAME" \
    --resource-group "$RESOURCE_GROUP" --query id -o tsv)"
IDENTITY_CLIENT_ID="$(az identity show --name "$IDENTITY_NAME" \
    --resource-group "$RESOURCE_GROUP" --query clientId -o tsv)"
ENVIRONMENT_ID="$(az containerapp env show --name "$CONTAINER_APP_ENV" \
    --resource-group "$RESOURCE_GROUP" --query id -o tsv)"
if [[ -z "$IDENTITY_ID" || -z "$IDENTITY_CLIENT_ID" || -z "$ENVIRONMENT_ID" ]]; then
    echo "[FAIL] Could not resolve identity or environment"
    exit 1
fi
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
API_VERSION="2024-03-01"
JOB_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${JOB_NAME}?api-version=${API_VERSION}"

# Exactly-once: this launcher only ever creates a job that does not exist.
EXISTING_JOB_COUNT="$(az containerapp job list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?name=='${JOB_NAME}'] | length(@)" -o tsv)"
if [[ "$EXISTING_JOB_COUNT" != "0" ]]; then
    echo "[FAIL] Job $JOB_NAME already exists; refusing to overwrite or restart"
    exit 1
fi

BLOB_PREFIX="phase05-jlens-saturation/${RUN_ID}"
COMMAND="timeout --signal=TERM --kill-after=30s 6900s python /workspace/scripts/phase05_jlens_saturation.py --output-dir /workspace/runtime/results --dim-batch ${DIM_BATCH} --resume"

mkdir -p "$RECORD_DIR"
umask 077
BODY_FILE="$RECORD_DIR/job_body.json"
JOB_FILE="$RECORD_DIR/job_persisted.json"

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
    {"name": "AZURE_CLIENT_ID", "value": "$IDENTITY_CLIENT_ID"},
    {"name": "JSPACE_BLOB_ACCOUNT", "value": "$BLOB_ACCOUNT"},
    {"name": "JSPACE_BLOB_CONTAINER", "value": "$BLOB_CONTAINER"},
    {"name": "JSPACE_BLOB_PREFIX", "value": "$BLOB_PREFIX"},
    {"name": "JSPACE_PHASE05_RUN_ID", "value": "$RUN_ID"},
    {"name": "JSPACE_ATTEMPT_ID", "value": "$ATTEMPT_KIND"},
    {"name": "JSPACE_IMAGE_DIGEST", "value": "$IMAGE_DIGEST"},
    {"name": "JSPACE_CODE_COMMIT", "value": "$PROJECT_SHA"},
]
body = {
    "location": "southeastasia",
    "identity": {
        "type": "UserAssigned",
        "userAssignedIdentities": {"$IDENTITY_ID": {}},
    },
    "tags": {
        "project": "jspace-observation",
        "phase": "$PHASE_TAG",
        "track": "$TRACK_TAG",
        "attempt-policy": "one-primary-only",
        "run-id": "$RUN_ID",
        "project-sha": "$PROJECT_SHA",
        "image-project-sha": "$PROJECT_SHA",
        "image-digest": "$IMAGE_DIGEST",
        "launch-attempt": "$ATTEMPT_KIND",
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
Path(sys.argv[1]).write_text(
    json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

az rest --method put --url "$JOB_URL" \
    --headers "Content-Type=application/json" \
    --body "@$BODY_FILE" --output none

PROVISIONING_STATE=""
for _ in $(seq 1 120); do
    PROVISIONING_STATE="$(az rest --method get --url "$JOB_URL" \
        --query properties.provisioningState -o tsv)"
    case "$PROVISIONING_STATE" in
        Succeeded) break ;;
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

verify_job() {
    az rest --method get --url "$JOB_URL" --output json >"$JOB_FILE"
    python - "$JOB_FILE" "$BODY_FILE" "$IMAGE_DIGEST_REF" "$COMMAND" \
        "$WORKLOAD_PROFILE_NAME" <<'PY'
import json
import sys

path, body_path, image_ref, command, profile = sys.argv[1:]
job = json.load(open(path, encoding="utf-8"))
intended = json.load(open(body_path, encoding="utf-8"))
props = job.get("properties", {})
containers = props.get("template", {}).get("containers", [])
if len(containers) != 1:
    raise SystemExit("[FAIL] job must have exactly one container")
container = containers[0]
if container.get("image") != image_ref:
    raise SystemExit("[FAIL] image is not the pinned digest reference")
if container.get("command") != ["/bin/sh"] \
        or container.get("args") != ["-lc", command]:
    raise SystemExit("[FAIL] container command line drifted")
if props.get("workloadProfileName") != profile:
    raise SystemExit("[FAIL] workload profile drifted")
config = props.get("configuration", {})
if config.get("triggerType") != "Manual" \
        or config.get("replicaTimeout") != 7200 \
        or config.get("replicaRetryLimit") != 0:
    raise SystemExit("[FAIL] trigger or retry configuration drifted")
manual = config.get("manualTriggerConfig", {})
if manual.get("replicaCompletionCount") != 1 or manual.get("parallelism") != 1:
    raise SystemExit("[FAIL] manual trigger configuration drifted")
actual_env = {i.get("name"): i.get("value") for i in container.get("env", [])}
intended_env = {
    i["name"]: i["value"]
    for i in intended["properties"]["template"]["containers"][0]["env"]
}
if actual_env != intended_env:
    raise SystemExit("[FAIL] environment drifted from the intended body")
if any("KEY" in k or "SAS" in k or "CONNECTION" in k for k in actual_env):
    raise SystemExit("[FAIL] key/SAS-shaped environment variable present")
actual_tags = job.get("tags") or {}
for key, value in intended["tags"].items():
    if actual_tags.get(key) != value:
        raise SystemExit("[FAIL] tag %s drifted" % key)
print("[OK] job body verified")
PY
}

verify_job
PRE_START_EXECUTIONS="$(az containerapp job execution list \
    --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
    --query 'length(@)' -o tsv)"
if [[ "$PRE_START_EXECUTIONS" != "0" ]]; then
    echo "[FAIL] Job already has $PRE_START_EXECUTIONS executions"
    exit 1
fi

EXECUTION_NAME="$(az containerapp job start --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" --query name -o tsv)"
if [[ -z "$EXECUTION_NAME" ]]; then
    echo "[FAIL] Job start returned no execution name"
    exit 1
fi

MATCHED=0
TOTAL=0
for _ in $(seq 1 60); do
    MATCHED="$(az containerapp job execution list --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?name=='${EXECUTION_NAME}'] | length(@)" -o tsv)"
    TOTAL="$(az containerapp job execution list --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" --query 'length(@)' -o tsv)"
    if [[ "$TOTAL" -gt 1 ]]; then
        echo "[FAIL] Duplicate or concurrent execution appeared after start"
        exit 1
    fi
    if [[ "$MATCHED" -eq 1 && "$TOTAL" -eq 1 ]]; then
        break
    fi
    sleep 2
done
if [[ "$MATCHED" -ne 1 || "$TOTAL" -ne 1 ]]; then
    echo "[FAIL] Started execution name/count could not be verified"
    exit 1
fi
verify_job

python - "$RECORD_DIR/phase05b_jlens_job_start.json" <<PY
import json
import sys
from pathlib import Path

record = {
    "schema_version": "phase05b-jlens-saturation-start-v1",
    "started_at_utc": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "phase": "$PHASE_TAG",
    "track": "$TRACK_TAG",
    "job_name": "$JOB_NAME",
    "execution_name": "$EXECUTION_NAME",
    "attempt": "$ATTEMPT_KIND",
    "run_id": "$RUN_ID",
    "project_sha": "$PROJECT_SHA",
    "image_digest": "$IMAGE_DIGEST",
    "image_ref": "$IMAGE_DIGEST_REF",
    "environment": "$CONTAINER_APP_ENV",
    "workload_profile": "$WORKLOAD_PROFILE_NAME",
    "identity": "$IDENTITY_NAME",
    "blob_account": "$BLOB_ACCOUNT",
    "blob_container": "$BLOB_CONTAINER",
    "blob_prefix": "$BLOB_PREFIX",
    "dim_batch": int("$DIM_BATCH"),
    "command": "$COMMAND",
    "job_preexisting": False,
    "executions_before_start": 0,
    "executions_after_start": 1,
    "account_key_used": False,
    "sas_used": False,
}
Path(sys.argv[1]).write_text(
    json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

echo "[OK] execution=$EXECUTION_NAME"
echo "[OK] image=$IMAGE_DIGEST_REF"
echo "[OK] blob_prefix=$BLOB_PREFIX"
echo "[OK] record=$RECORD_DIR/phase05b_jlens_job_start.json"
