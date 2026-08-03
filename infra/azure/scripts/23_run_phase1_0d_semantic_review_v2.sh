#!/usr/bin/env bash
# Launch one stage of the Phase 1.0D semantic-review v2 route.
#
#   ACR_NAME=<registry> REVIEW_MODE=qualify ./23_run_phase1_0d_semantic_review_v2.sh
#   ACR_NAME=<registry> REVIEW_MODE=smoke QUALIFICATION_RUN_ID=<utc> \
#       ./23_run_phase1_0d_semantic_review_v2.sh
#   ACR_NAME=<registry> REVIEW_MODE=review QUALIFICATION_RUN_ID=<utc> \
#       SMOKE_RUN_ID=<utc> GENERATION_RUN_ID=<utc> \
#       ./23_run_phase1_0d_semantic_review_v2.sh
#
# qualify writes a create-only 3-call receipt.  smoke reads only that receipt,
# makes exactly the 60 registered calls, writes its complete receipt even on a
# mismatch, and may be executed at most once.  review reads the persisted 60/60
# receipt before it receives a generation-pack prefix.
#
# Execution posture:
#   * image referenced by digest only, never by tag
#   * user-assigned managed identity for ACR pull, Blob and every model call
#   * no key, SAS, connection string or Azure Files mount
#   * replicaRetryLimit 0, parallelism 1, replicaCompletionCount 1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
CONTAINER_APP_ENV="cae-jspace-observation-sea-vnet2"
WORKLOAD_PROFILE_NAME="Consumption"
IDENTITY_NAME="id-jspace-p10d-review-sea"
BLOB_ACCOUNT="stjspacefiles0709085305"
BLOB_CONTAINER="jspace-results"
GENERATION_PREFIX="phase1-headroom-confirmation"
REVIEW_PREFIX="phase1-headroom-confirmation-review-v2"
QUALIFICATION_PREFIX="phase1-0d-semantic-review-v2/qualification"
SMOKE_PREFIX="phase1-0d-semantic-review-v2/smoke"
SMOKE_LOCK_BLOB="phase1-0d-semantic-review-v2/smoke-round-lock.json"
IMAGE_REPOSITORY="j-space-observation-phase1-0d-review-v2"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
REVIEW_MODE="${REVIEW_MODE:?Set REVIEW_MODE to qualify, smoke or review}"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
RUN_ID="${JSPACE_REVIEW_RUN_ID:-$(date -u +'%Y%m%dT%H%M%SZ')}"
QUALIFICATION_RUN_ID="${QUALIFICATION_RUN_ID:-}"
SMOKE_RUN_ID="${SMOKE_RUN_ID:-}"
GENERATION_RUN_ID="${GENERATION_RUN_ID:-}"
REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-10800}"
REVIEW_TIMEOUT_SECONDS="${REVIEW_TIMEOUT_SECONDS:-10500}"
JOB_NAME="job-jspace-p10d-review-v2-${REVIEW_MODE}"

case "$REVIEW_MODE" in
    qualify|smoke|review) ;;
    *)
        echo "[FAIL] REVIEW_MODE must be qualify, smoke or review"
        exit 1
        ;;
esac
if [[ "$REVIEW_MODE" =~ ^(smoke|review)$ \
    && ! "$QUALIFICATION_RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] smoke and review require QUALIFICATION_RUN_ID as a UTC stamp"
    exit 1
fi
if [[ "$REVIEW_MODE" == "review" \
    && ! "$SMOKE_RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] review mode requires SMOKE_RUN_ID as a UTC stamp"
    exit 1
fi
if [[ "$REVIEW_MODE" == "review" \
    && ! "$GENERATION_RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] review mode requires GENERATION_RUN_ID as a UTC stamp"
    exit 1
fi
if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ ! "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] Run ID must be a UTC stamp of the form YYYYMMDDTHHMMSSZ"
    exit 1
fi
if [[ ! "$REPLICA_TIMEOUT" =~ ^[0-9]+$ \
    || ! "$REVIEW_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
    echo "[FAIL] Timeouts must be nonnegative integers"
    exit 1
fi
if (( REVIEW_TIMEOUT_SECONDS >= REPLICA_TIMEOUT )); then
    echo "[FAIL] In-container timeout must fire before the replica timeout"
    exit 1
fi
LAUNCHER_SHA="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Launcher worktree must be clean"
    exit 1
fi

# Used only to form and audit the Azure control-plane request.  Scientific
# computation remains inside the digest-pinned ACA job.
PYTHON_BIN=""
PYTHON_TRUST="fhs-root-owned"
if [[ -x /usr/bin/python3 ]]; then
    PYTHON_BIN="$(/usr/bin/readlink -f /usr/bin/python3)"
    if [[ ! "$PYTHON_BIN" =~ ^/usr/bin/python3([.][0-9]+)?$ || ! -x "$PYTHON_BIN" ]]; then
        echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
        exit 1
    fi
    PYTHON_OWNER="$(/usr/bin/stat -c '%u' "$PYTHON_BIN")"
    PYTHON_MODE="$(/usr/bin/stat -c '%a' "$PYTHON_BIN")"
    if [[ "$PYTHON_OWNER" != "0" || ! "$PYTHON_MODE" =~ ^[0-7]{3,4}$ ]]; then
        echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
        exit 1
    fi
    if (( (8#$PYTHON_MODE & 8#022) != 0 )); then
        echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
        exit 1
    fi
else
    PYTHON_TRUST="path-resolved-absolute (no /usr/bin/python3 on this host)"
    while IFS= read -r candidate; do
        [[ -n "$candidate" ]] || continue
        absolute="$(cd "$(dirname "$candidate")" && pwd)/$(basename "$candidate")"
        if [[ -x "$absolute" ]] \
            && "$absolute" -I -c 'import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)' \
                >/dev/null 2>&1; then
            PYTHON_BIN="$absolute"
            break
        fi
    done < <(type -aP python3 python 2>/dev/null)
    if [[ -z "$PYTHON_BIN" ]]; then
        echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
        exit 1
    fi
    echo "[NOTE] interpreter trust is reduced: $PYTHON_TRUST"
fi
readonly PYTHON_BIN PYTHON_TRUST
python() {
    "$PYTHON_BIN" -I "$@"
}
readonly -f python

native_path() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$1"
    else
        printf '%s' "$1"
    fi
}

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
    echo "[FAIL] No immutable v2 review image is tagged $PROJECT_SHA"
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
    echo "[FAIL] V2 review image is not locked; refusing to launch"
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

RECORD_DIR="${REVIEW_RUN_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase1-0d-review-v2-${REVIEW_MODE}-${RUN_ID}}"
mkdir -p "$RECORD_DIR"
BODY_FILE="$RECORD_DIR/job_body.json"
JOB_FILE="$RECORD_DIR/job_state.json"
EXECUTION_LIST_FILE="$RECORD_DIR/existing_executions.json"
JOB_EXISTS=0
if az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output none 2>/dev/null; then
    JOB_EXISTS=1
    az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --output json >"$EXECUTION_LIST_FILE"
else
    printf '[]\n' >"$EXECUTION_LIST_FILE"
fi
EXECUTION_COUNT="$(python -c 'import json,sys; print(len(json.load(open(sys.argv[1], encoding="utf-8"))))' \
    "$(native_path "$EXECUTION_LIST_FILE")")"
if [[ "$REVIEW_MODE" == "smoke" && "$JOB_EXISTS" != "0" ]]; then
    echo "[FAIL] The v2 smoke one-round ceiling is already spent; no RV3 is authorised"
    exit 1
fi
if [[ "$REVIEW_MODE" == "smoke" ]]; then
    # Atomic service-side one-round lock.  Two concurrent launchers may both
    # observe no ACA job, but only one create-only Blob upload can succeed.  The
    # lock is retained permanently and is claimed before any job is provisioned.
    SMOKE_LOCK_FILE="$RECORD_DIR/smoke_round_lock.json"
    printf '{"artifact":"phase1_0d_rv2_smoke_round_lock","project_sha":"%s","image_digest":"%s","qualification_run_id":"%s","smoke_run_id":"%s"}\n' \
        "$PROJECT_SHA" "$IMAGE_DIGEST" "$QUALIFICATION_RUN_ID" "$RUN_ID" \
        >"$SMOKE_LOCK_FILE"
    az storage blob upload \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --name "$SMOKE_LOCK_BLOB" \
        --file "$SMOKE_LOCK_FILE" \
        --overwrite false \
        --only-show-errors \
        --output none
fi

ARGS="--project-root /workspace --out-dir /workspace/runtime/results"
ARGS="$ARGS --run-id $RUN_ID --client-id $IDENTITY_CLIENT_ID"
ARGS="$ARGS --blob-account $BLOB_ACCOUNT --blob-container $BLOB_CONTAINER"
ARGS="$ARGS --code-commit $PROJECT_SHA --image-digest $IMAGE_DIGEST"
ARGS="$ARGS --execution-timeout-seconds $REVIEW_TIMEOUT_SECONDS"
case "$REVIEW_MODE" in
    qualify)
        ARGS="$ARGS --gate-blob-prefix ${QUALIFICATION_PREFIX}/${RUN_ID}"
        ;;
    smoke)
        ARGS="$ARGS --qualification-receipt-prefix ${QUALIFICATION_PREFIX}/${QUALIFICATION_RUN_ID}"
        ARGS="$ARGS --gate-blob-prefix ${SMOKE_PREFIX}/${RUN_ID}"
        ;;
    review)
        ARGS="$ARGS --qualification-receipt-prefix ${QUALIFICATION_PREFIX}/${QUALIFICATION_RUN_ID}"
        ARGS="$ARGS --gate-receipt-prefix ${SMOKE_PREFIX}/${SMOKE_RUN_ID}"
        ARGS="$ARGS --pack-blob-prefix ${GENERATION_PREFIX}/${GENERATION_RUN_ID}"
        ARGS="$ARGS --out-blob-prefix ${REVIEW_PREFIX}/${RUN_ID}"
        ;;
esac
COMMAND="timeout --signal=TERM --kill-after=60s ${REVIEW_TIMEOUT_SECONDS}s python /workspace/scripts/run_phase1_0d_semantic_review_v2.py ${REVIEW_MODE} ${ARGS}"

python - "$(native_path "$BODY_FILE")" <<PY
import json
import sys
from pathlib import Path

environment = [
    {"name": "RESULTS_DIR", "value": "/workspace/runtime/results"},
    {"name": "TMPDIR", "value": "/workspace/runtime/cache/tmp"},
    {"name": "PYTHONUNBUFFERED", "value": "1"},
    {"name": "AZURE_CLIENT_ID", "value": "$IDENTITY_CLIENT_ID"},
    {"name": "JSPACE_BLOB_ACCOUNT", "value": "$BLOB_ACCOUNT"},
    {"name": "JSPACE_BLOB_CONTAINER", "value": "$BLOB_CONTAINER"},
    {"name": "JSPACE_REVIEW_RUN_ID", "value": "$RUN_ID"},
    {"name": "JSPACE_REVIEW_MODE", "value": "$REVIEW_MODE"},
    {"name": "JSPACE_CODE_COMMIT", "value": "$PROJECT_SHA"},
    {"name": "JSPACE_IMAGE_DIGEST", "value": "$IMAGE_DIGEST"},
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
        "round": "v2",
        "stage": "semantic-review-$REVIEW_MODE",
        "run-id": "$RUN_ID",
        "project-sha": "$PROJECT_SHA",
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
                    "name": "review-v2",
                    "image": "$IMAGE_DIGEST_REF",
                    "command": ["/bin/sh"],
                    "args": ["-lc", "$COMMAND"],
                    "env": environment,
                    "resources": {"cpu": 2.0, "memory": "4Gi"},
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
    --body "@$(native_path "$BODY_FILE")" \
    --output none

PROVISIONING_STATE=""
for _ in $(seq 1 120); do
    PROVISIONING_STATE="$(az rest \
        --method get \
        --url "$JOB_URL" \
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

az rest --method get --url "$JOB_URL" --output json >"$JOB_FILE"
python - "$(native_path "$JOB_FILE")" "$RUN_ID" "$PROJECT_SHA" "$IMAGE_DIGEST" \
    "$IMAGE_DIGEST_REF" "$WORKLOAD_PROFILE_NAME" "$REVIEW_MODE" <<'PY'
import json
import sys

path, run_id, project_sha, image_digest, image_ref, profile, mode = sys.argv[1:8]
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
if tags.get("round") != "v2":
    failures.append("round tag mismatch")
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
    missing = sorted({"AZURE_CLIENT_ID", "JSPACE_REVIEW_RUN_ID"} - env_names)
    if missing:
        failures.append("missing environment variables: " + ", ".join(missing))
    forbidden = sorted(
        name
        for name in env_names
        if name
        and ("ACCOUNT_KEY" in name or "SAS" in name or "CONNECTION_STRING" in name)
    )
    if forbidden:
        failures.append("credential-bearing variables present: " + ", ".join(forbidden))
    command = " ".join(container.get("args") or [])
    if mode in {"qualify", "smoke"} and "--pack-blob-prefix" in command:
        failures.append("a synthetic gate stage received a target pack prefix")
if template.get("volumes"):
    failures.append("job mounts volumes; managed identity to Blob only is required")

if failures:
    for failure in failures:
        print("[FAIL] " + failure)
    sys.exit(1)
print("[OK] Provisioned v2 job matches the recorded launch parameters")
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
    "$(native_path "$RECORD_DIR/executions_after_start.json")")"
if (( EXECUTION_COUNT_AFTER != EXECUTION_COUNT + 1 )); then
    echo "[FAIL] Expected exactly one new execution after start"
    exit 1
fi

printf '%s\n' "$EXECUTION_NAME" >"$RECORD_DIR/execution_name.txt"
echo "[OK] job_name=$JOB_NAME"
echo "[OK] execution_name=$EXECUTION_NAME"
echo "[OK] mode=$REVIEW_MODE"
echo "[OK] run_id=$RUN_ID"
echo "[OK] image=$IMAGE_DIGEST_REF"
echo "[OK] interpreter_trust=$PYTHON_TRUST"
echo "[OK] No platform retry; no Azure Files; managed identity only"
echo "[OK] Qualification and smoke are synthetic and count towards no scientific total"
