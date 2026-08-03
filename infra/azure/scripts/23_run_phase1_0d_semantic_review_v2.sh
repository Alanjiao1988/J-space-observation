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
# receipt before it receives a generation-pack prefix and is likewise guarded
# by a permanent create-only one-execution lock.
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
COMMITTED_GATE_ROOT="artifacts/phase1-0d-semantic-review-v2-gate"
COMMITTED_GENERATION_ROOT="artifacts/phase1-0d-confirmation"
SMOKE_LOCK_BLOB="phase1-0d-semantic-review-v2/smoke-round-lock.json"
REVIEW_LOCK_BLOB="phase1-0d-semantic-review-v2/formal-review-lock.json"
IMAGE_REPOSITORY="j-space-observation-phase1-0d-review-v2"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
REVIEW_MODE="${REVIEW_MODE:?Set REVIEW_MODE to qualify, smoke or review}"
REQUESTED_PROJECT_SHA="${PROJECT_SHA:-}"
PROJECT_SHA=""
RUN_ID="${JSPACE_REVIEW_RUN_ID:-$(date -u +'%Y%m%dT%H%M%SZ')}"
QUALIFICATION_RUN_ID="${QUALIFICATION_RUN_ID:-}"
SMOKE_RUN_ID="${SMOKE_RUN_ID:-}"
GENERATION_RUN_ID="${GENERATION_RUN_ID:-}"
SOURCE_MANIFEST_SHA256=""
EXPECTED_REVIEW_IMAGE_DIGEST=""
QUALIFICATION_RECEIPT_SHA256=""
QUALIFICATION_MANIFEST_SHA256=""
SMOKE_RECEIPT_SHA256=""
SMOKE_MANIFEST_SHA256=""
SMOKE_REQUIRED_SECONDS=5709
FORMAL_REVIEW_REQUIRED_SECONDS=611517
if [[ "$REVIEW_MODE" == "review" ]]; then
    REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-612300}"
    REVIEW_TIMEOUT_SECONDS="${REVIEW_TIMEOUT_SECONDS:-612000}"
else
    REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-10800}"
    REVIEW_TIMEOUT_SECONDS="${REVIEW_TIMEOUT_SECONDS:-10500}"
fi
case "$REVIEW_MODE" in
    qualify) JOB_MODE="q" ;;
    smoke) JOB_MODE="s" ;;
    review) JOB_MODE="r" ;;
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
if [[ "$REVIEW_MODE" == "smoke" ]] \
    && (( REVIEW_TIMEOUT_SECONDS < SMOKE_REQUIRED_SECONDS )); then
    echo "[FAIL] Smoke timeout cannot cover frozen calls, retries and persistence"
    exit 1
fi
if [[ "$REVIEW_MODE" == "review" ]] \
    && (( REVIEW_TIMEOUT_SECONDS < FORMAL_REVIEW_REQUIRED_SECONDS )); then
    echo "[FAIL] Formal review timeout cannot cover frozen calls, retries and persistence"
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

JOB_NONCE="$(python -c 'import secrets; print(secrets.token_hex(8))')"
if [[ ! "$JOB_NONCE" =~ ^[0-9a-f]{16}$ ]]; then
    echo "[FAIL] Could not create a collision-resistant ACA job identity"
    exit 1
fi
JOB_NAME="job-p10d-rv2-${JOB_MODE}-${JOB_NONCE}"
if (( ${#JOB_NAME} > 32 )); then
    echo "[FAIL] ACA job name exceeds the 32-character service limit"
    exit 1
fi
readonly JOB_NONCE JOB_NAME

ORIGIN_MAIN_SHA="$(git -C "$PROJECT_ROOT" ls-remote --exit-code \
    origin refs/heads/main | awk '{print $1}')"
if [[ "$ORIGIN_MAIN_SHA" != "$LAUNCHER_SHA" ]]; then
    echo "[FAIL] The v2 execution checkpoint must be pushed to origin/main"
    exit 1
fi

if [[ "$REVIEW_MODE" == "review" ]]; then
    mapfile -t COMMITTED_GATE_RECEIPTS < <(
        git -C "$PROJECT_ROOT" ls-tree -r --name-only \
            "$LAUNCHER_SHA" -- "$COMMITTED_GATE_ROOT" \
            | grep -E "^${COMMITTED_GATE_ROOT}/[0-9]{8}T[0-9]{6}Z/00_gate_receipt\\.json$" \
            || true
    )
    EXPECTED_GATE_RECEIPT="${COMMITTED_GATE_ROOT}/${SMOKE_RUN_ID}/00_gate_receipt.json"
    if (( ${#COMMITTED_GATE_RECEIPTS[@]} != 1 )) \
        || [[ "${COMMITTED_GATE_RECEIPTS[0]}" != "$EXPECTED_GATE_RECEIPT" ]]; then
        echo "[FAIL] Formal review requires the sole committed v2 smoke receipt"
        exit 1
    fi
    COMMITTED_GATE_DIR="${COMMITTED_GATE_ROOT}/${SMOKE_RUN_ID}"
    COMMITTED_SMOKE_MANIFEST_REL="${COMMITTED_GATE_DIR}/artifact_manifest.json"
    if ! git -C "$PROJECT_ROOT" cat-file -e \
        "${LAUNCHER_SHA}:${COMMITTED_SMOKE_MANIFEST_REL}"; then
        echo "[FAIL] The committed v2 smoke receipt has no committed manifest"
        exit 1
    fi
    mapfile -t GATE_BINDINGS < <(
        python - \
            "$(native_path "$PROJECT_ROOT")" \
            "$LAUNCHER_SHA" \
            "$EXPECTED_GATE_RECEIPT" \
            "$COMMITTED_SMOKE_MANIFEST_REL" <<'PY'
import hashlib
import json
import subprocess
import sys

project_root, commit, receipt_path, manifest_path = sys.argv[1:5]
def git_blob(path):
    return subprocess.check_output(
        ["git", "-C", project_root, "cat-file", "blob", f"{commit}:{path}"]
    )

receipt_bytes = git_blob(receipt_path)
manifest_bytes = git_blob(manifest_path)
receipt = json.loads(receipt_bytes)
print(hashlib.sha256(receipt_bytes).hexdigest())
print(hashlib.sha256(manifest_bytes).hexdigest())
print(receipt.get("review_code_commit", ""))
print(receipt.get("review_image_digest", ""))
parent = receipt.get("qualification_parent") or {}
print(parent.get("run_id", ""))
PY
    )
    if (( ${#GATE_BINDINGS[@]} != 5 )); then
        echo "[FAIL] Could not derive the committed v2 smoke bindings"
        exit 1
    fi
    SMOKE_RECEIPT_SHA256="${GATE_BINDINGS[0]}"
    SMOKE_MANIFEST_SHA256="${GATE_BINDINGS[1]}"
    PROJECT_SHA="${GATE_BINDINGS[2]}"
    EXPECTED_REVIEW_IMAGE_DIGEST="${GATE_BINDINGS[3]}"
    COMMITTED_QUALIFICATION_RUN_ID="${GATE_BINDINGS[4]}"
    if [[ ! "$SMOKE_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ \
        || ! "$SMOKE_MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ \
        || ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ \
        || ! "$EXPECTED_REVIEW_IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ \
        || ! "$COMMITTED_QUALIFICATION_RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ \
        || "$QUALIFICATION_RUN_ID" != "$COMMITTED_QUALIFICATION_RUN_ID" ]]; then
        echo "[FAIL] The committed v2 smoke bindings are malformed"
        exit 1
    fi
    if [[ -n "$REQUESTED_PROJECT_SHA" \
        && "$REQUESTED_PROJECT_SHA" != "$PROJECT_SHA" ]]; then
        echo "[FAIL] PROJECT_SHA differs from the committed smoke image"
        exit 1
    fi
    if ! git -C "$PROJECT_ROOT" merge-base --is-ancestor \
        "$PROJECT_SHA" "$LAUNCHER_SHA"; then
        echo "[FAIL] The smoke image commit is not an ancestor of formal review"
        exit 1
    fi
    if ! git -C "$PROJECT_ROOT" diff --quiet \
        "$PROJECT_SHA" "$LAUNCHER_SHA" -- \
        Dockerfile.phase1-0d-review-v2 \
        docs/phase1_0d_protocol_snapshot.json \
        docs/phase1_0d_rv2_protected_bytes.json \
        docs/phase1_0d_semantic_review_addendum_v2.json \
        docs/phase1_0d_semantic_review_rubric_v2.md \
        docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md \
        infra/azure/scripts/23_run_phase1_0d_semantic_review_v2.sh \
        phase1_0d_review_v2_build_provenance.json \
        scripts/phase1_0d_review_v2_build_provenance.py \
        scripts/phase1_0d_rv2_protected_bytes.py \
        scripts/run_phase1_0d_semantic_review.py \
        scripts/run_phase1_0d_semantic_review_v2.py \
        scripts/verify_phase1_0d_rv2_gate.py \
        src/jspace_observation/__init__.py \
        src/jspace_observation/phase1_0d_confirmation.py \
        src/jspace_observation/phase1_0d_generation.py \
        src/jspace_observation/semantic_review \
        src/jspace_observation/semantic_review_v2; then
        echo "[FAIL] Review or verification bytes changed after the smoke image"
        exit 1
    fi
else
    PROJECT_SHA="${REQUESTED_PROJECT_SHA:-$LAUNCHER_SHA}"
    if [[ "$PROJECT_SHA" != "$LAUNCHER_SHA" ]]; then
        echo "[FAIL] Qualification and smoke must use this exact pushed image commit"
        exit 1
    fi
fi
if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
python "$(native_path "$PROJECT_ROOT/scripts/phase1_0d_protected_bytes.py")" \
    verify --project-root "$(native_path "$PROJECT_ROOT")"
python "$(native_path "$PROJECT_ROOT/scripts/phase1_0d_rv2_protected_bytes.py")" \
    verify --project-root "$(native_path "$PROJECT_ROOT")"
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Protected-byte verification changed the launcher worktree"
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
    echo "[FAIL] No immutable v2 review image is tagged $PROJECT_SHA"
    exit 1
fi
if [[ "$REVIEW_MODE" == "review" \
    && "$IMAGE_DIGEST" != "$EXPECTED_REVIEW_IMAGE_DIGEST" ]]; then
    echo "[FAIL] Committed smoke digest differs from the locked review image"
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

RECORD_ROOT="${REVIEW_RUN_RECORD_DIR:-$PROJECT_ROOT/results/runs}"
RECORD_DIR="${RECORD_ROOT%/}/phase1-0d-review-v2-${REVIEW_MODE}-${RUN_ID}-${JOB_NONCE}"
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
if [[ "$JOB_EXISTS" != "0" ]]; then
    echo "[FAIL] This v2 run id already has an ACA job; duplicate execution is forbidden"
    exit 1
fi
if [[ "$REVIEW_MODE" == "smoke" ]]; then
    QUALIFICATION_RECEIPT="$RECORD_DIR/qualification_00_gate_receipt.json"
    QUALIFICATION_MANIFEST="$RECORD_DIR/qualification_artifact_manifest.json"
    QUALIFICATION_OBJECTS="$RECORD_DIR/qualification_objects.json"
    QUALIFICATION_BLOB_PREFIX="${QUALIFICATION_PREFIX}/${QUALIFICATION_RUN_ID}"
    az storage blob download \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --name "${QUALIFICATION_BLOB_PREFIX}/00_gate_receipt.json" \
        --file "$QUALIFICATION_RECEIPT" \
        --overwrite false --only-show-errors --output none
    az storage blob download \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --name "${QUALIFICATION_BLOB_PREFIX}/artifact_manifest.json" \
        --file "$QUALIFICATION_MANIFEST" \
        --overwrite false --only-show-errors --output none
    az storage blob list \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --prefix "${QUALIFICATION_BLOB_PREFIX}/" \
        --only-show-errors --output json >"$QUALIFICATION_OBJECTS"
    python - "$QUALIFICATION_OBJECTS" "$QUALIFICATION_BLOB_PREFIX" <<'PY'
import json
import sys

objects_path, prefix = sys.argv[1:3]
expected = {
    f"{prefix}/00_gate_receipt.json",
    f"{prefix}/artifact_manifest.json",
}
observed = {
    item.get("name")
    for item in json.load(open(objects_path, encoding="utf-8"))
}
if observed != expected:
    raise SystemExit("[FAIL] Qualification Blob prefix is not the exact evidence pack")
print("[OK] Qualification Blob prefix has the exact persisted file set")
PY
    QUALIFICATION_RECEIPT_SHA256="$(python -c \
        'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' \
        "$(native_path "$QUALIFICATION_RECEIPT")")"
    QUALIFICATION_MANIFEST_SHA256="$(python -c \
        'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' \
        "$(native_path "$QUALIFICATION_MANIFEST")")"
    python "$(native_path "$PROJECT_ROOT/scripts/verify_phase1_0d_rv2_gate.py")" \
        --project-root "$(native_path "$PROJECT_ROOT")" \
        --manifest "$(native_path "$QUALIFICATION_MANIFEST")" \
        --receipt "$(native_path "$QUALIFICATION_RECEIPT")" \
        --qualification-run-id "$QUALIFICATION_RUN_ID" \
        --manifest-sha256 "$QUALIFICATION_MANIFEST_SHA256" \
        --receipt-sha256 "$QUALIFICATION_RECEIPT_SHA256" \
        --review-code-commit "$PROJECT_SHA" \
        --review-image-digest "$IMAGE_DIGEST"
fi
if [[ "$REVIEW_MODE" == "review" ]]; then
    COMMITTED_SOURCE_MANIFEST_REL="${COMMITTED_GENERATION_ROOT}/${GENERATION_RUN_ID}/artifact_manifest.json"
    if ! git -C "$PROJECT_ROOT" ls-files --error-unmatch \
        "$COMMITTED_SOURCE_MANIFEST_REL" >/dev/null \
        || ! git -C "$PROJECT_ROOT" cat-file -e \
            "${LAUNCHER_SHA}:${COMMITTED_SOURCE_MANIFEST_REL}"; then
        echo "[FAIL] Formal review requires the committed generation manifest"
        exit 1
    fi
    COMMITTED_SMOKE_RECEIPT="$RECORD_DIR/committed_00_gate_receipt.json"
    COMMITTED_SMOKE_MANIFEST="$RECORD_DIR/committed_smoke_artifact_manifest.json"
    COMMITTED_SOURCE_MANIFEST="$RECORD_DIR/committed_generation_artifact_manifest.json"
    git -C "$PROJECT_ROOT" cat-file blob \
        "${LAUNCHER_SHA}:${EXPECTED_GATE_RECEIPT}" \
        >"$COMMITTED_SMOKE_RECEIPT"
    git -C "$PROJECT_ROOT" cat-file blob \
        "${LAUNCHER_SHA}:${COMMITTED_SMOKE_MANIFEST_REL}" \
        >"$COMMITTED_SMOKE_MANIFEST"
    git -C "$PROJECT_ROOT" cat-file blob \
        "${LAUNCHER_SHA}:${COMMITTED_SOURCE_MANIFEST_REL}" \
        >"$COMMITTED_SOURCE_MANIFEST"
    SOURCE_MANIFEST_SHA256="$(python -c \
        'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' \
        "$(native_path "$COMMITTED_SOURCE_MANIFEST")")"
    if [[ ! "$SOURCE_MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
        echo "[FAIL] Could not hash the committed generation manifest"
        exit 1
    fi

    DOWNLOADED_SMOKE_RECEIPT="$RECORD_DIR/00_gate_receipt.json"
    DOWNLOADED_SMOKE_MANIFEST="$RECORD_DIR/smoke_artifact_manifest.json"
    DOWNLOADED_SOURCE_MANIFEST="$RECORD_DIR/generation_artifact_manifest.json"
    az storage blob download \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --name "${SMOKE_PREFIX}/${SMOKE_RUN_ID}/00_gate_receipt.json" \
        --file "$DOWNLOADED_SMOKE_RECEIPT" \
        --overwrite false --only-show-errors --output none
    az storage blob download \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --name "${SMOKE_PREFIX}/${SMOKE_RUN_ID}/artifact_manifest.json" \
        --file "$DOWNLOADED_SMOKE_MANIFEST" \
        --overwrite false --only-show-errors --output none
    az storage blob download \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --name "${GENERATION_PREFIX}/${GENERATION_RUN_ID}/artifact_manifest.json" \
        --file "$DOWNLOADED_SOURCE_MANIFEST" \
        --overwrite false --only-show-errors --output none
    if ! cmp -s "$DOWNLOADED_SMOKE_RECEIPT" "$COMMITTED_SMOKE_RECEIPT" \
        || ! cmp -s "$DOWNLOADED_SMOKE_MANIFEST" "$COMMITTED_SMOKE_MANIFEST" \
        || ! cmp -s "$DOWNLOADED_SOURCE_MANIFEST" "$COMMITTED_SOURCE_MANIFEST"; then
        echo "[FAIL] Committed licenses differ from their Blob evidence"
        exit 1
    fi
    python "$(native_path "$PROJECT_ROOT/scripts/verify_phase1_0d_rv2_gate.py")" \
        --project-root "$(native_path "$PROJECT_ROOT")" \
        --manifest "$(native_path "$DOWNLOADED_SMOKE_MANIFEST")" \
        --receipt "$(native_path "$DOWNLOADED_SMOKE_RECEIPT")" \
        --smoke-run-id "$SMOKE_RUN_ID" \
        --manifest-sha256 "$SMOKE_MANIFEST_SHA256" \
        --receipt-sha256 "$SMOKE_RECEIPT_SHA256" \
        --review-code-commit "$PROJECT_SHA" \
        --review-image-digest "$IMAGE_DIGEST"

    SOURCE_OBJECTS_FILE="$RECORD_DIR/generation_objects.json"
    az storage blob list \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --prefix "${GENERATION_PREFIX}/${GENERATION_RUN_ID}/" \
        --only-show-errors --output json >"$SOURCE_OBJECTS_FILE"
    SOURCE_FILES=(
        00_protocol_snapshot.json
        01_selection.json
        02_records.jsonl
        03_review_form.jsonl
        04_generation_summary.json
        05_decision.json
        09_summary.md
    )
    python - \
        "$(native_path "$COMMITTED_SOURCE_MANIFEST")" \
        "$(native_path "$SOURCE_OBJECTS_FILE")" \
        "${GENERATION_PREFIX}/${GENERATION_RUN_ID}" \
        "$GENERATION_RUN_ID" <<'PY'
import json
import re
import sys

manifest_path, objects_path, prefix, run_id = sys.argv[1:5]
expected_files = [
    "00_protocol_snapshot.json",
    "01_selection.json",
    "02_records.jsonl",
    "03_review_form.jsonl",
    "04_generation_summary.json",
    "05_decision.json",
    "09_summary.md",
]
manifest = json.load(open(manifest_path, encoding="utf-8"))
if (
    manifest.get("run_id") != run_id
    or manifest.get("artifact") != "phase1_0d_confirmation_pack"
    or manifest.get("manifest_written_last") is not True
):
    raise SystemExit("[FAIL] Committed generation manifest has invalid identity")
entries = manifest.get("files")
if (
    not isinstance(entries, list)
    or manifest.get("file_count") != len(expected_files)
    or [entry.get("name") for entry in entries] != expected_files
    or any(
        set(entry) != {"name", "sha256"}
        or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", "")))
        for entry in entries
    )
):
    raise SystemExit("[FAIL] Committed generation manifest has invalid entries")
expected = {f"{prefix}/{name}" for name in expected_files}
expected.add(f"{prefix}/artifact_manifest.json")
objects = json.load(open(objects_path, encoding="utf-8"))
observed = {item.get("name") for item in objects}
if observed != expected:
    raise SystemExit("[FAIL] Generation Blob prefix is not the exact complete pack")
print("[OK] Generation Blob prefix has the exact committed file set")
PY
    SOURCE_PACK_DIR="$RECORD_DIR/source-pack"
    mkdir -p "$SOURCE_PACK_DIR"
    for name in "${SOURCE_FILES[@]}"; do
        az storage blob download \
            --auth-mode login \
            --account-name "$BLOB_ACCOUNT" \
            --container-name "$BLOB_CONTAINER" \
            --name "${GENERATION_PREFIX}/${GENERATION_RUN_ID}/${name}" \
            --file "$SOURCE_PACK_DIR/$name" \
            --overwrite false --only-show-errors --output none
    done
    python - \
        "$(native_path "$COMMITTED_SOURCE_MANIFEST")" \
        "$(native_path "$SOURCE_PACK_DIR")" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

manifest_path, pack_dir = sys.argv[1:3]
manifest = json.load(open(manifest_path, encoding="utf-8"))
expected = {entry["name"]: entry["sha256"] for entry in manifest["files"]}
for name, digest in expected.items():
    observed = hashlib.sha256((Path(pack_dir) / name).read_bytes()).hexdigest()
    if observed != digest:
        raise SystemExit(f"[FAIL] Generation Blob bytes differ for {name}")
print("[OK] Committed generation license binds every source-pack byte")
PY
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
        ARGS="$ARGS --qualification-manifest-sha256 ${QUALIFICATION_MANIFEST_SHA256}"
        ARGS="$ARGS --qualification-receipt-sha256 ${QUALIFICATION_RECEIPT_SHA256}"
        ARGS="$ARGS --gate-blob-prefix ${SMOKE_PREFIX}/${RUN_ID}"
        ;;
    review)
        ARGS="$ARGS --qualification-receipt-prefix ${QUALIFICATION_PREFIX}/${QUALIFICATION_RUN_ID}"
        ARGS="$ARGS --gate-receipt-prefix ${SMOKE_PREFIX}/${SMOKE_RUN_ID}"
        ARGS="$ARGS --gate-manifest-sha256 ${SMOKE_MANIFEST_SHA256}"
        ARGS="$ARGS --gate-receipt-sha256 ${SMOKE_RECEIPT_SHA256}"
        ARGS="$ARGS --pack-blob-prefix ${GENERATION_PREFIX}/${GENERATION_RUN_ID}"
        ARGS="$ARGS --source-manifest-sha256 ${SOURCE_MANIFEST_SHA256}"
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
    {"name": "JSPACE_GENERATION_RUN_ID", "value": "$GENERATION_RUN_ID"},
    {"name": "JSPACE_SOURCE_MANIFEST_SHA256", "value": "$SOURCE_MANIFEST_SHA256"},
    {"name": "JSPACE_QUALIFICATION_RECEIPT_SHA256", "value": "$QUALIFICATION_RECEIPT_SHA256"},
    {"name": "JSPACE_QUALIFICATION_MANIFEST_SHA256", "value": "$QUALIFICATION_MANIFEST_SHA256"},
    {"name": "JSPACE_SMOKE_RECEIPT_SHA256", "value": "$SMOKE_RECEIPT_SHA256"},
    {"name": "JSPACE_SMOKE_MANIFEST_SHA256", "value": "$SMOKE_MANIFEST_SHA256"},
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
        "generation-run-id": "$GENERATION_RUN_ID",
        "source-manifest-sha256": "$SOURCE_MANIFEST_SHA256",
        "qualification-receipt-sha256": "$QUALIFICATION_RECEIPT_SHA256",
        "qualification-manifest-sha256": "$QUALIFICATION_MANIFEST_SHA256",
        "smoke-receipt-sha256": "$SMOKE_RECEIPT_SHA256",
        "smoke-manifest-sha256": "$SMOKE_MANIFEST_SHA256",
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
    "$IMAGE_DIGEST_REF" "$WORKLOAD_PROFILE_NAME" "$REVIEW_MODE" \
    "$REPLICA_TIMEOUT" "$COMMAND" "$IDENTITY_CLIENT_ID" "$BLOB_ACCOUNT" \
    "$BLOB_CONTAINER" "$GENERATION_RUN_ID" "$SOURCE_MANIFEST_SHA256" \
    "$LAUNCHER_SHA" "$QUALIFICATION_RECEIPT_SHA256" \
    "$QUALIFICATION_MANIFEST_SHA256" "$SMOKE_RECEIPT_SHA256" \
    "$SMOKE_MANIFEST_SHA256" <<'PY'
import json
import sys

(
    path,
    run_id,
    project_sha,
    image_digest,
    image_ref,
    profile,
    mode,
    replica_timeout,
    expected_command,
    identity_client_id,
    blob_account,
    blob_container,
    generation_run_id,
    source_manifest_sha256,
    launcher_sha,
    qualification_receipt_sha256,
    qualification_manifest_sha256,
    smoke_receipt_sha256,
    smoke_manifest_sha256,
) = sys.argv[1:20]
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
if tags.get("launcher-sha") != launcher_sha:
    failures.append("launcher-sha tag mismatch")
if tags.get("generation-run-id") != generation_run_id:
    failures.append("generation-run-id tag mismatch")
if tags.get("source-manifest-sha256") != source_manifest_sha256:
    failures.append("source-manifest-sha256 tag mismatch")
if tags.get("qualification-receipt-sha256") != qualification_receipt_sha256:
    failures.append("qualification-receipt-sha256 tag mismatch")
if tags.get("qualification-manifest-sha256") != qualification_manifest_sha256:
    failures.append("qualification-manifest-sha256 tag mismatch")
if tags.get("smoke-receipt-sha256") != smoke_receipt_sha256:
    failures.append("smoke-receipt-sha256 tag mismatch")
if tags.get("smoke-manifest-sha256") != smoke_manifest_sha256:
    failures.append("smoke-manifest-sha256 tag mismatch")
if tags.get("round") != "v2":
    failures.append("round tag mismatch")
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
        failures.append("container command differs from the registered review command")
    if container.get("resources") != {"cpu": 2.0, "memory": "4Gi"}:
        failures.append("container resources differ from the registered review job")
    env_list = container.get("env") or []
    env = {item.get("name"): item.get("value") for item in env_list}
    if len(env) != len(env_list):
        failures.append("container environment has duplicate names")
    expected_env = {
        "RESULTS_DIR": "/workspace/runtime/results",
        "TMPDIR": "/workspace/runtime/cache/tmp",
        "PYTHONUNBUFFERED": "1",
        "AZURE_CLIENT_ID": identity_client_id,
        "JSPACE_BLOB_ACCOUNT": blob_account,
        "JSPACE_BLOB_CONTAINER": blob_container,
        "JSPACE_REVIEW_RUN_ID": run_id,
        "JSPACE_REVIEW_MODE": mode,
        "JSPACE_CODE_COMMIT": project_sha,
        "JSPACE_IMAGE_DIGEST": image_digest,
        "JSPACE_GENERATION_RUN_ID": generation_run_id,
        "JSPACE_SOURCE_MANIFEST_SHA256": source_manifest_sha256,
        "JSPACE_QUALIFICATION_RECEIPT_SHA256": qualification_receipt_sha256,
        "JSPACE_QUALIFICATION_MANIFEST_SHA256": qualification_manifest_sha256,
        "JSPACE_SMOKE_RECEIPT_SHA256": smoke_receipt_sha256,
        "JSPACE_SMOKE_MANIFEST_SHA256": smoke_manifest_sha256,
    }
    if env != expected_env:
        failures.append("container environment differs from the exact registered values")
    forbidden = sorted(
        name
        for name in env
        if name
        and ("ACCOUNT_KEY" in name or "SAS" in name or "CONNECTION_STRING" in name)
    )
    if forbidden:
        failures.append("credential-bearing variables present: " + ", ".join(forbidden))
    if mode in {"qualify", "smoke"} and "--pack-blob-prefix" in expected_command:
        failures.append("a synthetic gate stage received a target pack prefix")
if template.get("volumes"):
    failures.append("job mounts volumes; managed identity to Blob only is required")

if failures:
    for failure in failures:
        print("[FAIL] " + failure)
    sys.exit(1)
print("[OK] Provisioned v2 job matches the recorded launch parameters")
PY

if [[ "$REVIEW_MODE" == "smoke" ]]; then
    # Jobs are unique per run id, so concurrent launchers cannot mutate each
    # other's command.  Claim the global one-round lock only after qualification
    # bytes and the provisioned job are fully verified, immediately before calls.
    SMOKE_LOCK_FILE="$RECORD_DIR/smoke_round_lock.json"
    printf '{"artifact":"phase1_0d_rv2_smoke_round_lock","job_name":"%s","project_sha":"%s","image_digest":"%s","qualification_run_id":"%s","qualification_receipt_sha256":"%s","qualification_manifest_sha256":"%s","smoke_run_id":"%s"}\n' \
        "$JOB_NAME" "$PROJECT_SHA" "$IMAGE_DIGEST" "$QUALIFICATION_RUN_ID" \
        "$QUALIFICATION_RECEIPT_SHA256" "$QUALIFICATION_MANIFEST_SHA256" \
        "$RUN_ID" >"$SMOKE_LOCK_FILE"
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
if [[ "$REVIEW_MODE" == "review" ]]; then
    # The unique job is inert until this create-only global lock succeeds.
    REVIEW_LOCK_FILE="$RECORD_DIR/formal_review_lock.json"
    printf '{"artifact":"phase1_0d_rv2_formal_review_lock","job_name":"%s","project_sha":"%s","image_digest":"%s","qualification_run_id":"%s","smoke_run_id":"%s","generation_run_id":"%s","source_manifest_sha256":"%s","review_run_id":"%s"}\n' \
        "$JOB_NAME" "$PROJECT_SHA" "$IMAGE_DIGEST" "$QUALIFICATION_RUN_ID" "$SMOKE_RUN_ID" \
        "$GENERATION_RUN_ID" "$SOURCE_MANIFEST_SHA256" "$RUN_ID" >"$REVIEW_LOCK_FILE"
    az storage blob upload \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --name "$REVIEW_LOCK_BLOB" \
        --file "$REVIEW_LOCK_FILE" \
        --overwrite false \
        --only-show-errors \
        --output none
fi

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
