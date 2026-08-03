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
#   * one fixed create-only Blob lock so a new run ID cannot start a rerun

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
GENERATION_LOCK_BLOB="${BLOB_PREFIX}/generation-execution-lock.json"
SMOKE_PREFIX_ROOT="phase1-0d-semantic-review-v2/smoke"
COMMITTED_GATE_ROOT="artifacts/phase1-0d-semantic-review-v2-gate"
IMAGE_REPOSITORY="j-space-observation-phase1-0d"
REVIEW_V2_IMAGE_REPOSITORY="j-space-observation-phase1-0d-review-v2"
LOCKED_IMAGE_TAG="9cde1d95ffda36698a0ddf558a9358f3337dd711"
LOCKED_IMAGE_DIGEST="sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
PROJECT_SHA="${PROJECT_SHA:-$LOCKED_IMAGE_TAG}"
RUN_ID="${JSPACE_CONFIRMATION_RUN_ID:-$(date -u +'%Y%m%dT%H%M%SZ')}"
SMOKE_RUN_ID="${SMOKE_RUN_ID:-}"
SMOKE_RECEIPT_SHA256="${SMOKE_RECEIPT_SHA256:-}"
SMOKE_MANIFEST_SHA256="${SMOKE_MANIFEST_SHA256:-}"
REVIEW_V2_CODE_COMMIT="${REVIEW_V2_CODE_COMMIT:-}"
REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-21600}"
GENERATION_TIMEOUT_SECONDS="${GENERATION_TIMEOUT_SECONDS:-21300}"

# Bind `python` to an authenticated absolute interpreter. On the Linux
# orchestrator that is /usr/bin/python3, and the ownership/permission checks
# are what make "authenticated" mean something there: a world-writable
# interpreter on a shared host could be swapped between the check and the call.
#
# A control-plane workstation without the FHS path cannot offer that guarantee,
# so it says so rather than pretending. The interpreter is still resolved to an
# absolute path and is still only ever used to build a control-plane request
# body and to count job executions; no scientific computation runs here, and
# none may -- every generation, test and analysis runs in Azure.
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
    # A name on PATH is not always an interpreter: on Windows the first
    # "python3" is usually an App Execution Alias that exits non-zero without
    # running anything. Try every candidate and keep the first that actually
    # answers as Python 3, rather than trusting the first name that resolves.
    PYTHON_TRUST="path-resolved-absolute (no /usr/bin/python3 on this host)"
    PYTHON_BIN=""
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

# A path this shell can open is not always a path the Azure CLI can open: on a
# Windows control-plane workstation the CLI is a native binary and does not
# understand a POSIX-style path. Convert only where a converter exists.
native_path() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$1"
    else
        printf '%s' "$1"
    fi
}

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ "$PROJECT_SHA" != "$LOCKED_IMAGE_TAG" ]]; then
    echo "[FAIL] PROJECT_SHA must identify the sole locked generation image"
    exit 1
fi
if [[ ! "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] Run ID must be a UTC stamp of the form YYYYMMDDTHHMMSSZ"
    exit 1
fi
if [[ ! "$SMOKE_RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] SMOKE_RUN_ID must name the sole persisted v2 smoke"
    exit 1
fi
if [[ ! "$SMOKE_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ \
    || ! "$SMOKE_MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Exact smoke receipt and manifest SHA-256 values are required"
    exit 1
fi
if [[ ! "$REVIEW_V2_CODE_COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] REVIEW_V2_CODE_COMMIT must be the full commit baked into the smoke image"
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
if [[ "$REPLICA_TIMEOUT" != "21600" \
    || "$GENERATION_TIMEOUT_SECONDS" != "21300" ]]; then
    echo "[FAIL] Section 11 requires the exact 21600/21300 second timeout envelope"
    exit 1
fi
LAUNCHER_SHA="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Launcher worktree must be clean"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" cat-file -e "${REVIEW_V2_CODE_COMMIT}^{commit}" \
    || ! git -C "$PROJECT_ROOT" merge-base --is-ancestor \
        "$REVIEW_V2_CODE_COMMIT" "$LAUNCHER_SHA"; then
    echo "[FAIL] The smoke review commit is not an ancestor of this launch checkpoint"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    "$REVIEW_V2_CODE_COMMIT" "$LAUNCHER_SHA" -- \
    Dockerfile.phase1-0d-review-v2 \
    docs/phase1_0d_semantic_review_addendum_v2.json \
    docs/phase1_0d_semantic_review_rubric_v2.md \
    docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md \
    phase1_0d_review_v2_build_provenance.json \
    scripts/run_phase1_0d_semantic_review_v2.py \
    scripts/verify_phase1_0d_rv2_gate.py \
    src/jspace_observation/semantic_review_v2; then
    echo "[FAIL] V2 review or gate-verification bytes changed after the smoke image"
    exit 1
fi
ORIGIN_MAIN_SHA="$(git -C "$PROJECT_ROOT" ls-remote --exit-code \
    origin refs/heads/main | awk '{print $1}')"
if [[ "$ORIGIN_MAIN_SHA" != "$LAUNCHER_SHA" ]]; then
    echo "[FAIL] The committed gate checkpoint must be pushed to origin/main"
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
if [[ "$IMAGE_DIGEST" != "$LOCKED_IMAGE_DIGEST" ]]; then
    echo "[FAIL] The locked generation tag does not resolve to its frozen digest"
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

REVIEW_V2_IMAGE_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$REVIEW_V2_IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${REVIEW_V2_CODE_COMMIT}']].digest | [0]" \
    -o tsv)"
if [[ ! "$REVIEW_V2_IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] No digest-pinned v2 smoke image exists for REVIEW_V2_CODE_COMMIT"
    exit 1
fi
REVIEW_V2_TAG_WRITE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${REVIEW_V2_IMAGE_REPOSITORY}:${REVIEW_V2_CODE_COMMIT}" \
    --query changeableAttributes.writeEnabled -o tsv)"
REVIEW_V2_TAG_DELETE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${REVIEW_V2_IMAGE_REPOSITORY}:${REVIEW_V2_CODE_COMMIT}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
REVIEW_V2_MANIFEST_WRITE_ENABLED="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${REVIEW_V2_IMAGE_REPOSITORY}@${REVIEW_V2_IMAGE_DIGEST}" \
    --query changeableAttributes.writeEnabled -o tsv)"
REVIEW_V2_MANIFEST_DELETE_ENABLED="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${REVIEW_V2_IMAGE_REPOSITORY}@${REVIEW_V2_IMAGE_DIGEST}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
if [[ "${REVIEW_V2_TAG_WRITE_ENABLED,,}" != "false" \
    || "${REVIEW_V2_TAG_DELETE_ENABLED,,}" != "false" \
    || "${REVIEW_V2_MANIFEST_WRITE_ENABLED,,}" != "false" \
    || "${REVIEW_V2_MANIFEST_DELETE_ENABLED,,}" != "false" ]]; then
    echo "[FAIL] V2 smoke image is not immutable; refusing target generation"
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

# Section 11 is licensed only by the exact create-only 60/60 receipt.  Require
# the public bytes to have been committed and pushed, then independently fetch
# the Blob originals and run the same exhaustive validation used by formal
# review before checking or claiming any target-generation resource.
COMMITTED_GATE_DIR="${COMMITTED_GATE_ROOT}/${SMOKE_RUN_ID}"
COMMITTED_SMOKE_RECEIPT="${PROJECT_ROOT}/${COMMITTED_GATE_DIR}/00_gate_receipt.json"
COMMITTED_SMOKE_MANIFEST="${PROJECT_ROOT}/${COMMITTED_GATE_DIR}/artifact_manifest.json"
for relative in \
    "${COMMITTED_GATE_DIR}/00_gate_receipt.json" \
    "${COMMITTED_GATE_DIR}/artifact_manifest.json"; do
    if ! git -C "$PROJECT_ROOT" ls-files --error-unmatch "$relative" >/dev/null \
        || ! git -C "$PROJECT_ROOT" cat-file -e "HEAD:${relative}"; then
        echo "[FAIL] The exact v2 smoke gate is not committed at ${relative}"
        exit 1
    fi
done

DOWNLOADED_SMOKE_RECEIPT="$RECORD_DIR/00_gate_receipt.json"
DOWNLOADED_SMOKE_MANIFEST="$RECORD_DIR/artifact_manifest.json"
SMOKE_BLOB_PREFIX="${SMOKE_PREFIX_ROOT}/${SMOKE_RUN_ID}"
az storage blob download \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "${SMOKE_BLOB_PREFIX}/00_gate_receipt.json" \
    --file "$DOWNLOADED_SMOKE_RECEIPT" \
    --overwrite false \
    --only-show-errors \
    --output none
az storage blob download \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "${SMOKE_BLOB_PREFIX}/artifact_manifest.json" \
    --file "$DOWNLOADED_SMOKE_MANIFEST" \
    --overwrite false \
    --only-show-errors \
    --output none
if ! cmp -s "$DOWNLOADED_SMOKE_RECEIPT" "$COMMITTED_SMOKE_RECEIPT" \
    || ! cmp -s "$DOWNLOADED_SMOKE_MANIFEST" "$COMMITTED_SMOKE_MANIFEST"; then
    echo "[FAIL] Committed v2 smoke gate differs from the create-only Blob evidence"
    exit 1
fi
python "$(native_path "$PROJECT_ROOT/scripts/verify_phase1_0d_rv2_gate.py")" \
    --project-root "$(native_path "$PROJECT_ROOT")" \
    --manifest "$(native_path "$DOWNLOADED_SMOKE_MANIFEST")" \
    --receipt "$(native_path "$DOWNLOADED_SMOKE_RECEIPT")" \
    --smoke-run-id "$SMOKE_RUN_ID" \
    --manifest-sha256 "$SMOKE_MANIFEST_SHA256" \
    --receipt-sha256 "$SMOKE_RECEIPT_SHA256" \
    --review-code-commit "$REVIEW_V2_CODE_COMMIT" \
    --review-image-digest "$REVIEW_V2_IMAGE_DIGEST"

# The authority licenses one generation execution in total, not one per run ID.
EXECUTION_LIST_FILE="$RECORD_DIR/existing_executions.json"
if az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output none 2>/dev/null; then
    az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --output json >"$EXECUTION_LIST_FILE"
    echo "[FAIL] The sole Phase 1.0D generation execution is already claimed"
    exit 1
else
    printf '[]\n' >"$EXECUTION_LIST_FILE"
fi
EXECUTION_COUNT="$(python -c 'import json,sys; print(len(json.load(open(sys.argv[1], encoding="utf-8"))))' \
    "$(native_path "$EXECUTION_LIST_FILE")")"

# Prove the exact run-specific target prefix is empty before claiming the
# global execution lock.  The lock is a sibling under BLOB_PREFIX, not target
# output, so it cannot make this check pass or fail.
TARGET_PREFIX="${BLOB_PREFIX}/${RUN_ID}/"
TARGET_OBJECT_COUNT="$(az storage blob list \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --prefix "$TARGET_PREFIX" \
    --query 'length(@)' -o tsv \
    --only-show-errors)"
if [[ ! "$TARGET_OBJECT_COUNT" =~ ^[0-9]+$ || "$TARGET_OBJECT_COUNT" != "0" ]]; then
    echo "[FAIL] Target prefix is not empty: ${TARGET_PREFIX}"
    exit 1
fi

# Claim before provisioning. Two concurrent launchers can both observe an
# absent ACA job, but only one create-only upload can authorize an execution.
GENERATION_LOCK_FILE="$RECORD_DIR/generation_execution_lock.json"
printf '{"artifact":"phase1_0d_generation_execution_lock","project_sha":"%s","image_digest":"%s","generation_run_id":"%s","target_prefix":"%s","rv2_smoke_run_id":"%s","rv2_smoke_receipt_sha256":"%s","rv2_smoke_manifest_sha256":"%s","rv2_review_code_commit":"%s","rv2_review_image_digest":"%s"}\n' \
    "$PROJECT_SHA" "$IMAGE_DIGEST" "$RUN_ID" "$TARGET_PREFIX" \
    "$SMOKE_RUN_ID" "$SMOKE_RECEIPT_SHA256" "$SMOKE_MANIFEST_SHA256" \
    "$REVIEW_V2_CODE_COMMIT" "$REVIEW_V2_IMAGE_DIGEST" \
    >"$GENERATION_LOCK_FILE"
az storage blob upload \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "$GENERATION_LOCK_BLOB" \
    --file "$GENERATION_LOCK_FILE" \
    --overwrite false \
    --only-show-errors \
    --output none

COMMAND="timeout --signal=TERM --kill-after=60s ${GENERATION_TIMEOUT_SECONDS}s python /workspace/scripts/run_phase1_0d_confirmation.py --mode generate --repo-root /workspace --output-root /workspace/runtime/results --upload-blob"

python - "$(native_path "$BODY_FILE")" <<PY
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
    {"name": "JSPACE_RV2_SMOKE_RUN_ID", "value": "$SMOKE_RUN_ID"},
    {"name": "JSPACE_RV2_SMOKE_RECEIPT_SHA256", "value": "$SMOKE_RECEIPT_SHA256"},
    {"name": "JSPACE_RV2_SMOKE_MANIFEST_SHA256", "value": "$SMOKE_MANIFEST_SHA256"},
    {"name": "JSPACE_RV2_REVIEW_CODE_COMMIT", "value": "$REVIEW_V2_CODE_COMMIT"},
    {"name": "JSPACE_RV2_REVIEW_IMAGE_DIGEST", "value": "$REVIEW_V2_IMAGE_DIGEST"},
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
        "rv2-smoke-run-id": "$SMOKE_RUN_ID",
        "rv2-smoke-receipt-sha256": "$SMOKE_RECEIPT_SHA256",
        "rv2-review-code-commit": "$REVIEW_V2_CODE_COMMIT",
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
    --body "@$(native_path "$BODY_FILE")" \
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
python - "$(native_path "$JOB_FILE")" "$RUN_ID" "$PROJECT_SHA" "$IMAGE_DIGEST" \
    "$IMAGE_DIGEST_REF" "$WORKLOAD_PROFILE_NAME" "$SMOKE_RUN_ID" \
    "$SMOKE_RECEIPT_SHA256" "$REVIEW_V2_CODE_COMMIT" "$REPLICA_TIMEOUT" \
    "$COMMAND" "$IDENTITY_CLIENT_ID" "$BLOB_ACCOUNT" "$BLOB_CONTAINER" \
    "$BLOB_PREFIX" "$SMOKE_MANIFEST_SHA256" "$REVIEW_V2_IMAGE_DIGEST" <<'PY'
import json
import sys

(
    path,
    run_id,
    project_sha,
    image_digest,
    image_ref,
    profile,
    smoke_run_id,
    smoke_receipt_sha256,
    review_code_commit,
    replica_timeout,
    expected_command,
    identity_client_id,
    blob_account,
    blob_container,
    blob_prefix,
    smoke_manifest_sha256,
    review_image_digest,
) = sys.argv[1:18]
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
if tags.get("rv2-smoke-run-id") != smoke_run_id:
    failures.append("v2 smoke run tag mismatch")
if tags.get("rv2-smoke-receipt-sha256") != smoke_receipt_sha256:
    failures.append("v2 smoke receipt tag mismatch")
if tags.get("rv2-review-code-commit") != review_code_commit:
    failures.append("v2 review commit tag mismatch")
if properties.get("workloadProfileName") != profile:
    failures.append("workload profile mismatch")
if configuration.get("replicaRetryLimit") != 0:
    failures.append("platform retry is enabled")
if configuration.get("replicaTimeout") != int(replica_timeout):
    failures.append("replica timeout mismatch")
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
    if container.get("command") != ["/bin/sh"] or container.get("args") != [
        "-lc",
        expected_command,
    ]:
        failures.append("container command differs from the registered generation command")
    if container.get("resources") != {"cpu": 8.0, "memory": "56Gi"}:
        failures.append("container resources differ from the registered T4 job")
    env_list = container.get("env") or []
    env = {item.get("name"): item.get("value") for item in env_list}
    if len(env) != len(env_list):
        failures.append("container environment has duplicate names")
    expected_env = {
        "HF_HOME": "/workspace/runtime/hf-cache",
        "HUGGINGFACE_HUB_CACHE": "/workspace/runtime/hf-cache/hub",
        "TRANSFORMERS_CACHE": "/workspace/runtime/hf-cache",
        "RESULTS_DIR": "/workspace/runtime/results",
        "TMPDIR": "/workspace/runtime/cache/tmp",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "PYTHONUNBUFFERED": "1",
        "AZURE_CLIENT_ID": identity_client_id,
        "JSPACE_BLOB_ACCOUNT": blob_account,
        "JSPACE_BLOB_CONTAINER": blob_container,
        "JSPACE_BLOB_PREFIX": blob_prefix,
        "JSPACE_CONFIRMATION_RUN_ID": run_id,
        "JSPACE_CODE_COMMIT": project_sha,
        "JSPACE_IMAGE_DIGEST": image_digest,
        "JSPACE_RV2_SMOKE_RUN_ID": smoke_run_id,
        "JSPACE_RV2_SMOKE_RECEIPT_SHA256": smoke_receipt_sha256,
        "JSPACE_RV2_SMOKE_MANIFEST_SHA256": smoke_manifest_sha256,
        "JSPACE_RV2_REVIEW_CODE_COMMIT": review_code_commit,
        "JSPACE_RV2_REVIEW_IMAGE_DIGEST": review_image_digest,
        "JSPACE_HARDWARE": (
            "Azure Container Apps gpu-t4 workload profile, NVIDIA Tesla T4"
        ),
    }
    if env != expected_env:
        failures.append("container environment differs from the exact registered values")
    forbidden = sorted(
        name
        for name in env
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
    "$(native_path "$RECORD_DIR/executions_after_start.json")")"
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
echo "[OK] rv2_smoke_run_id=$SMOKE_RUN_ID"
echo "[OK] rv2_smoke_receipt_sha256=$SMOKE_RECEIPT_SHA256"
echo "[OK] No platform retry; no Azure Files; managed identity only"
