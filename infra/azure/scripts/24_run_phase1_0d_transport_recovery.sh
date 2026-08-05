#!/usr/bin/env bash
# Launch the sole capacity-certified Phase 1.0D review-only recovery.
#
# This script has no mode switch and reads no target identity from arguments or
# environment variables. It must run from the pushed repository inside the
# existing private Container Apps network. A blocked certificate exits before
# any Job, lock, execution, or provider request can exist.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

readonly RESOURCE_GROUP="rg-jspace-observation-sea"
readonly CONTAINER_APP_ENV="cae-jspace-observation-sea-vnet2"
readonly IDENTITY_NAME="id-jspace-p10d-review-sea"
readonly V2_IMAGE_REPOSITORY="j-space-observation-phase1-0d-review-v2"
readonly V2_IMAGE_TAG="1b56f775b5457e2e11124559052ad4caf028fdad"
readonly V2_IMAGE_DIGEST="sha256:b3cf2c5933fe296c6a4d59eba9d73c3f10fc42bdddc494b25b679ca679b449dd"
readonly BLOB_ACCOUNT="stjspacefiles0709085305"
readonly BLOB_CONTAINER="jspace-results"
readonly CAPACITY_ARTIFACT_ROOT="artifacts/phase1-0d-semantic-review-v2-transport-capacity"
readonly CAPACITY_BLOB_PREFIX="phase1-0d-semantic-review-v2/transport-recovery/capacity"
readonly CAPACITY_CERTIFICATE_NAME="00_capacity_certificate.json"
readonly CAPACITY_MANIFEST_NAME="artifact_manifest.json"
readonly RECOVERY_LOCK_BLOB="phase1-0d-semantic-review-v2/transport-recovery/formal-review-lock.json"
readonly RECOVERY_RESULT_ROOT="phase1-headroom-confirmation-review-v2-transport-recovery"
readonly SOURCE_PREFIX="phase1-headroom-confirmation/20260804T154518Z"
readonly SOURCE_MANIFEST_REPO_PATH="artifacts/phase1-0d-confirmation/20260804T154518Z/artifact_manifest.json"
readonly GENERATION_JOB_NAME="job-jspace-p10d-confirmation"
readonly GENERATION_EXECUTION="job-jspace-p10d-confirmation-pdlhmah"
readonly OLD_RESULT_PREFIX="phase1-headroom-confirmation-review-v2/20260804T181247Z"
readonly OLD_LOCK_BLOB="phase1-0d-semantic-review-v2/formal-review-lock.json"
readonly OLD_LOCK_SHA256="d7b184b486e757ba0a7702c41300157627e03616b873555d87ea27ada7d7e93f"
readonly OLD_FORMAL_JOB_NAME="job-p10d-rv2-r-d4a84a59bc28a91f"
readonly OLD_FORMAL_EXECUTION="job-p10d-rv2-r-d4a84a59bc28a91f-tjzwlse"
readonly OLD_TERMINAL_ARCHIVE_REPO_PATH="artifacts/phase1-0d-semantic-review-v2-formal/20260804T181247Z/artifact_manifest.json"
readonly OLD_TERMINAL_ARCHIVE_SHA256="41694a6b9593756d3cbed3014367887567f5e785840dce86bceb2da41a39c204"
readonly SOURCE_MANIFEST_SHA256="76accb0f675130989f3db698ecfeaa8736f288980026cdaca0e8413c05234536"
readonly API_VERSION="2024-03-01"
readonly TERMINAL_AMBIGUITY="BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_LAUNCH_AMBIGUITY"
readonly STARTING_STATE_MISMATCH="BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_STARTING_STATE_MISMATCH"
readonly CAPACITY_BLOCKED="BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY"

if (( $# != 0 )); then
    echo "[FAIL] The recovery launcher accepts no arguments"
    exit 1
fi

LAUNCHER_SHA="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
ORIGIN_MAIN_SHA="$(git -C "$PROJECT_ROOT" ls-remote --exit-code \
    origin refs/heads/main | awk '{print $1}')"
if [[ "$LAUNCHER_SHA" != "$ORIGIN_MAIN_SHA" ]]; then
    echo "[FAIL] Recovery launcher commit is not origin/main"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Recovery launcher worktree is not clean"
    exit 1
fi

PYTHON_BIN="$(command -v python3)"
PYTHON_BIN="$(readlink -f "$PYTHON_BIN")"
if [[ ! "$PYTHON_BIN" =~ ^/usr/bin/python3([.][0-9]+)?$ \
    || ! -x "$PYTHON_BIN" \
    || "$(stat -c '%u' "$PYTHON_BIN")" != "0" ]]; then
    echo "[FAIL] A root-owned /usr/bin/python3 is required"
    exit 1
fi

mapfile -t CAPACITY_MANIFESTS < <(
    git -C "$PROJECT_ROOT" ls-tree -r --name-only "$LAUNCHER_SHA" \
        -- "$CAPACITY_ARTIFACT_ROOT" \
        | grep -E "/${CAPACITY_MANIFEST_NAME}$" || true
)
PASSING_CAPACITY_MANIFESTS=()
for manifest in "${CAPACITY_MANIFESTS[@]}"; do
    if git -C "$PROJECT_ROOT" cat-file blob \
        "${LAUNCHER_SHA}:${manifest}" \
        | "$PYTHON_BIN" -I -c \
            'import json,sys; raise SystemExit(0 if json.load(sys.stdin).get("capacity_gate_passed") is True else 1)'
    then
        PASSING_CAPACITY_MANIFESTS+=("$manifest")
    fi
done
if (( ${#PASSING_CAPACITY_MANIFESTS[@]} != 1 )); then
    echo "[FAIL] Exactly one committed passing capacity certificate is required"
    exit 1
fi
CAPACITY_MANIFEST_REL="${PASSING_CAPACITY_MANIFESTS[0]}"
CAPACITY_DIR_REL="${CAPACITY_MANIFEST_REL%/$CAPACITY_MANIFEST_NAME}"
CAPACITY_CERTIFICATE_REL="${CAPACITY_DIR_REL}/${CAPACITY_CERTIFICATE_NAME}"
RUN_ID="${CAPACITY_DIR_REL##*/}"
if [[ "$CAPACITY_DIR_REL" != "${CAPACITY_ARTIFACT_ROOT}/${RUN_ID}" \
    || ! "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    echo "[FAIL] Capacity certificate directory is not one exact UTC run"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" cat-file -e \
    "${LAUNCHER_SHA}:${CAPACITY_CERTIFICATE_REL}"; then
    echo "[FAIL] Capacity certificate member is absent"
    exit 1
fi

RECORD_DIR="$PROJECT_ROOT/results/runs/phase1-0d-transport-recovery-${RUN_ID}"
mkdir -p "$RECORD_DIR"
CAPACITY_CERTIFICATE="$RECORD_DIR/$CAPACITY_CERTIFICATE_NAME"
CAPACITY_MANIFEST="$RECORD_DIR/$CAPACITY_MANIFEST_NAME"
git -C "$PROJECT_ROOT" cat-file blob \
    "${LAUNCHER_SHA}:${CAPACITY_CERTIFICATE_REL}" >"$CAPACITY_CERTIFICATE"
git -C "$PROJECT_ROOT" cat-file blob \
    "${LAUNCHER_SHA}:${CAPACITY_MANIFEST_REL}" >"$CAPACITY_MANIFEST"

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
if [[ -z "$IDENTITY_ID" || "$IDENTITY_CLIENT_ID" != \
    "67d9b724-e00b-4a87-a1ce-fce2308685a2" || -z "$ENVIRONMENT_ID" ]]; then
    echo "[FAIL] Fixed identity or environment readback differs"
    exit 1
fi

# Reauthenticate the committed certificate against its create-only Blob copy.
CAPACITY_OBJECTS="$RECORD_DIR/capacity_objects.json"
az storage blob list \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --prefix "${CAPACITY_BLOB_PREFIX}/${RUN_ID}/" \
    --only-show-errors -o json >"$CAPACITY_OBJECTS"
"$PYTHON_BIN" -I - "$CAPACITY_OBJECTS" "$RUN_ID" <<'PY'
import json
import sys

names = {item["name"] for item in json.load(open(sys.argv[1], encoding="utf-8"))}
expected = {
    f"phase1-0d-semantic-review-v2/transport-recovery/capacity/{sys.argv[2]}/"
    "00_capacity_certificate.json",
    f"phase1-0d-semantic-review-v2/transport-recovery/capacity/{sys.argv[2]}/"
    "artifact_manifest.json",
}
if names != expected:
    raise SystemExit("[FAIL] Capacity Blob prefix differs from the exact two-object pack")
PY
for name in "$CAPACITY_CERTIFICATE_NAME" "$CAPACITY_MANIFEST_NAME"; do
    az storage blob download \
        --auth-mode login \
        --account-name "$BLOB_ACCOUNT" \
        --container-name "$BLOB_CONTAINER" \
        --name "${CAPACITY_BLOB_PREFIX}/${RUN_ID}/${name}" \
        --file "$RECORD_DIR/blob-${name}" \
        --overwrite false --only-show-errors --output none
    if ! cmp -s "$RECORD_DIR/$name" "$RECORD_DIR/blob-$name"; then
        echo "[FAIL] Committed capacity bytes differ from create-only Blob bytes"
        exit 1
    fi
done

# The Job must not exist until after all fixed-state and certificate checks pass.
RECOVERY_JOB_COUNT="$(az containerapp job list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?tags.round=='v2-transport-recovery'] | length(@)" -o tsv)"
RECOVERY_LOCK_EXISTS="$(az storage blob exists \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "$RECOVERY_LOCK_BLOB" \
    --query exists -o tsv --only-show-errors)"
SOURCE_OBJECTS="$RECORD_DIR/source_objects.json"
az storage blob list \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --prefix "${SOURCE_PREFIX}/" \
    --only-show-errors -o json >"$SOURCE_OBJECTS"
OLD_RESULT_COUNT="$(az storage blob list \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --prefix "${OLD_RESULT_PREFIX}/" \
    --query 'length(@)' -o tsv --only-show-errors)"
RECOVERY_RESULT_OBJECT_COUNT="$(az storage blob list \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --prefix "${RECOVERY_RESULT_ROOT}/" \
    --query 'length(@)' -o tsv --only-show-errors)"

COMMITTED_SOURCE_MANIFEST="$RECORD_DIR/committed_source_manifest.json"
BLOB_SOURCE_MANIFEST="$RECORD_DIR/blob_source_manifest.json"
SOURCE_REVIEW_FORM="$RECORD_DIR/03_review_form.jsonl"
OLD_TERMINAL_ARCHIVE="$RECORD_DIR/old_terminal_archive_manifest.json"
git -C "$PROJECT_ROOT" cat-file blob \
    "${LAUNCHER_SHA}:${SOURCE_MANIFEST_REPO_PATH}" >"$COMMITTED_SOURCE_MANIFEST"
git -C "$PROJECT_ROOT" cat-file blob \
    "${LAUNCHER_SHA}:${OLD_TERMINAL_ARCHIVE_REPO_PATH}" >"$OLD_TERMINAL_ARCHIVE"
az storage blob download \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "${SOURCE_PREFIX}/artifact_manifest.json" \
    --file "$BLOB_SOURCE_MANIFEST" \
    --overwrite false --only-show-errors --output none
az storage blob download \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "${SOURCE_PREFIX}/03_review_form.jsonl" \
    --file "$SOURCE_REVIEW_FORM" \
    --overwrite false --only-show-errors --output none
az storage blob download \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "$OLD_LOCK_BLOB" \
    --file "$RECORD_DIR/old_formal_review_lock.json" \
    --overwrite false --only-show-errors --output none
OBSERVED_OLD_LOCK_SHA256="$(sha256sum \
    "$RECORD_DIR/old_formal_review_lock.json" | awk '{print $1}')"
OBSERVED_SOURCE_MANIFEST_SHA256="$(sha256sum \
    "$COMMITTED_SOURCE_MANIFEST" | awk '{print $1}')"
OBSERVED_OLD_TERMINAL_ARCHIVE_SHA256="$(sha256sum \
    "$OLD_TERMINAL_ARCHIVE" | awk '{print $1}')"

GENERATION_EXECUTIONS="$RECORD_DIR/generation_executions.json"
OLD_FORMAL_EXECUTIONS="$RECORD_DIR/old_formal_executions.json"
az containerapp job execution list \
    --name "$GENERATION_JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query '[].{name:name,status:properties.status}' \
    -o json >"$GENERATION_EXECUTIONS"
az containerapp job execution list \
    --name "$OLD_FORMAL_JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query '[].{name:name,status:properties.status}' \
    -o json >"$OLD_FORMAL_EXECUTIONS"

if ! "$PYTHON_BIN" -I - \
    "$SOURCE_OBJECTS" "$GENERATION_EXECUTIONS" "$OLD_FORMAL_EXECUTIONS" \
    "$SOURCE_PREFIX" "$GENERATION_EXECUTION" "$OLD_FORMAL_EXECUTION" <<'PY'
import json
import sys

(
    source_objects_path,
    generation_executions_path,
    formal_executions_path,
    source_prefix,
    generation_execution,
    formal_execution,
) = sys.argv[1:]
members = (
    "00_protocol_snapshot.json",
    "01_selection.json",
    "02_records.jsonl",
    "03_review_form.jsonl",
    "04_generation_summary.json",
    "05_decision.json",
    "09_summary.md",
    "artifact_manifest.json",
)
expected_objects = {f"{source_prefix}/{member}" for member in members}
observed_objects = {
    item["name"]
    for item in json.load(open(source_objects_path, encoding="utf-8"))
}
if observed_objects != expected_objects:
    raise SystemExit("[FAIL] Exact source Blob membership differs")
generation = json.load(open(generation_executions_path, encoding="utf-8"))
formal = json.load(open(formal_executions_path, encoding="utf-8"))
if generation != [{"name": generation_execution, "status": "Succeeded"}]:
    raise SystemExit("[FAIL] Generation execution identity/count/status differs")
if formal != [{"name": formal_execution, "status": "Failed"}]:
    raise SystemExit("[FAIL] Old formal execution identity/count/status differs")
PY
then
    echo "$STARTING_STATE_MISMATCH"
    exit 1
fi

if [[ "$RECOVERY_JOB_COUNT" != "0" \
    || "${RECOVERY_LOCK_EXISTS,,}" != "false" \
    || "$OLD_RESULT_COUNT" != "0" \
    || "$RECOVERY_RESULT_OBJECT_COUNT" != "0" \
    || "$OBSERVED_OLD_LOCK_SHA256" != "$OLD_LOCK_SHA256" \
    || "$OBSERVED_SOURCE_MANIFEST_SHA256" != "$SOURCE_MANIFEST_SHA256" \
    || "$OBSERVED_OLD_TERMINAL_ARCHIVE_SHA256" != \
        "$OLD_TERMINAL_ARCHIVE_SHA256" ]] \
    || ! cmp -s "$COMMITTED_SOURCE_MANIFEST" "$BLOB_SOURCE_MANIFEST"; then
    echo "$STARTING_STATE_MISMATCH"
    echo "[FAIL] Pre-Job recovery state differs"
    exit 1
fi

VERIFY_JSON="$("$PYTHON_BIN" -I \
    "$PROJECT_ROOT/scripts/phase1_0d_transport_recovery.py" \
    verify-certificate \
    --certificate "$CAPACITY_CERTIFICATE" \
    --manifest "$CAPACITY_MANIFEST" \
    --review-form "$SOURCE_REVIEW_FORM" \
    --project-root "$PROJECT_ROOT" \
    --require-passing)"
CAPACITY_CERTIFICATE_SHA256="$("$PYTHON_BIN" -I -c \
    'import json,sys; print(json.load(sys.stdin)["certificate_sha256"])' \
    <<<"$VERIFY_JSON")"
CAPACITY_MANIFEST_SHA256="$("$PYTHON_BIN" -I -c \
    'import json,sys; print(json.load(sys.stdin)["manifest_sha256"])' \
    <<<"$VERIFY_JSON")"
if ! "$PYTHON_BIN" -I \
    "$PROJECT_ROOT/scripts/phase1_0d_transport_recovery.py" \
    verify-freshness \
    --certificate "$CAPACITY_CERTIFICATE" \
    --max-age-seconds 600 >/dev/null
then
    echo "$CAPACITY_BLOCKED"
    echo "[FAIL] Capacity evidence is no longer fresh"
    exit 1
fi
JOB_NAME="job-p10d-rv2-tr-${CAPACITY_CERTIFICATE_SHA256:0:8}"
if [[ ! "$JOB_NAME" =~ ^job-p10d-rv2-tr-[0-9a-f]{8}$ ]]; then
    echo "[FAIL] Could not form the certificate-bound Job identity"
    exit 1
fi

V2_TAG_DIGEST="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${V2_IMAGE_REPOSITORY}:${V2_IMAGE_TAG}" \
    --query digest -o tsv)"
V2_TAG_WRITE="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${V2_IMAGE_REPOSITORY}:${V2_IMAGE_TAG}" \
    --query changeableAttributes.writeEnabled -o tsv)"
V2_TAG_DELETE="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${V2_IMAGE_REPOSITORY}:${V2_IMAGE_TAG}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
V2_MANIFEST_WRITE="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${V2_IMAGE_REPOSITORY}@${V2_IMAGE_DIGEST}" \
    --query changeableAttributes.writeEnabled -o tsv)"
V2_MANIFEST_DELETE="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${V2_IMAGE_REPOSITORY}@${V2_IMAGE_DIGEST}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
if [[ "$V2_TAG_DIGEST" != "$V2_IMAGE_DIGEST" \
    || "${V2_TAG_WRITE,,}" != "false" \
    || "${V2_TAG_DELETE,,}" != "false" \
    || "${V2_MANIFEST_WRITE,,}" != "false" \
    || "${V2_MANIFEST_DELETE,,}" != "false" ]]; then
    echo "$STARTING_STATE_MISMATCH"
    echo "[FAIL] Locked v2 review image identity or immutability differs"
    exit 1
fi

RESULT_PREFIX="${RECOVERY_RESULT_ROOT}/${RUN_ID}"
JOB_BODY="$RECORD_DIR/job_body.json"
"$PYTHON_BIN" -I - \
    "$PROJECT_ROOT" "$RUN_ID" "$JOB_NAME" "$LAUNCHER_SHA" \
    "$CAPACITY_CERTIFICATE_SHA256" "$CAPACITY_MANIFEST_SHA256" \
    "$IDENTITY_ID" "$ENVIRONMENT_ID" "$JOB_BODY" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

(
    root,
    run_id,
    job_name,
    launcher_commit,
    certificate_sha,
    manifest_sha,
    identity_id,
    environment_id,
    output,
) = sys.argv[1:]
spec = importlib.util.spec_from_file_location(
    "transport_recovery", Path(root) / "scripts/phase1_0d_transport_recovery.py"
)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
body = module.build_recovery_job(
    run_id=run_id,
    job_name=job_name,
    launcher_commit=launcher_commit,
    capacity_certificate_sha256=certificate_sha,
    capacity_manifest_sha256=manifest_sha,
    identity_resource_id=identity_id,
    environment_resource_id=environment_id,
)
Path(output).write_bytes(module.canonical_json_bytes(body))
PY

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
JOB_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${JOB_NAME}?api-version=${API_VERSION}"
ACCESS_TOKEN="$(az account get-access-token \
    --resource https://management.azure.com/ --query accessToken -o tsv)"
EXISTING_JOB_BODY="$RECORD_DIR/job_before_create.json"
set +e
EXISTING_JOB_STATUS="$(curl --silent --show-error --max-redirs 0 \
    --connect-timeout 30 --max-time 120 \
    --request GET \
    --header "Authorization: Bearer ${ACCESS_TOKEN}" \
    --output "$EXISTING_JOB_BODY" \
    --write-out '%{http_code}' \
    "$JOB_URL")"
EXISTING_JOB_CURL_STATUS=$?
set -e
if (( EXISTING_JOB_CURL_STATUS != 0 )) || [[ "$EXISTING_JOB_STATUS" != "404" ]]; then
    unset ACCESS_TOKEN
    echo "[FAIL] Certificate-bound recovery Job is not provably absent"
    exit 1
fi

JOB_CREATE_RESPONSE="$RECORD_DIR/job_create_response.json"
set +e
JOB_CREATE_STATUS="$(curl --silent --show-error --max-redirs 0 \
    --connect-timeout 30 --max-time 180 \
    --request PUT \
    --header "Authorization: Bearer ${ACCESS_TOKEN}" \
    --header "Content-Type: application/json" \
    --header "If-None-Match: *" \
    --data-binary "@$JOB_BODY" \
    --output "$JOB_CREATE_RESPONSE" \
    --write-out '%{http_code}' \
    "$JOB_URL")"
JOB_CREATE_CURL_STATUS=$?
set -e
unset ACCESS_TOKEN
if (( JOB_CREATE_CURL_STATUS != 0 )) \
    || [[ ! "$JOB_CREATE_STATUS" =~ ^20[01]$ ]]; then
    echo "$TERMINAL_AMBIGUITY"
    echo "[FAIL] Create-only recovery Job provisioning was not established"
    exit 2
fi

PROVISIONING_STATE=""
for _ in $(seq 1 120); do
    PROVISIONING_STATE="$(az rest --method get --url "$JOB_URL" \
        --query properties.provisioningState -o tsv)"
    case "$PROVISIONING_STATE" in
        Succeeded) break ;;
        Failed|Canceled|Cancelled|Deleted)
            echo "[FAIL] Recovery Job provisioning ended in $PROVISIONING_STATE"
            exit 1
            ;;
    esac
    sleep 5
done
if [[ "$PROVISIONING_STATE" != "Succeeded" ]]; then
    echo "[FAIL] Recovery Job provisioning did not stabilize"
    exit 1
fi

JOB_READBACK="$RECORD_DIR/job_readback.json"
az rest --method get --url "$JOB_URL" -o json >"$JOB_READBACK"
"$PYTHON_BIN" -I - \
    "$PROJECT_ROOT" "$RUN_ID" "$JOB_NAME" "$LAUNCHER_SHA" \
    "$CAPACITY_CERTIFICATE_SHA256" "$CAPACITY_MANIFEST_SHA256" \
    "$IDENTITY_ID" "$ENVIRONMENT_ID" "$JOB_READBACK" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

(
    root,
    run_id,
    job_name,
    launcher_commit,
    certificate_sha,
    manifest_sha,
    identity_id,
    environment_id,
    readback,
) = sys.argv[1:]
spec = importlib.util.spec_from_file_location(
    "transport_recovery", Path(root) / "scripts/phase1_0d_transport_recovery.py"
)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
module.verify_recovery_job(
    json.load(open(readback, encoding="utf-8")),
    run_id=run_id,
    job_name=job_name,
    launcher_commit=launcher_commit,
    capacity_certificate_sha256=certificate_sha,
    capacity_manifest_sha256=manifest_sha,
    identity_resource_id=identity_id,
    environment_resource_id=environment_id,
)
PY

RECOVERY_JOBS="$RECORD_DIR/recovery_jobs_after_create.json"
az containerapp job list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?tags.round=='v2-transport-recovery'].name" \
    -o json >"$RECOVERY_JOBS"
BEFORE_EXECUTIONS="$RECORD_DIR/executions_before.json"
az containerapp job execution list \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" -o json >"$BEFORE_EXECUTIONS"
if ! "$PYTHON_BIN" -I - \
    "$RECOVERY_JOBS" "$BEFORE_EXECUTIONS" "$JOB_NAME" <<'PY'
import json
import sys

jobs_path, executions_path, job_name = sys.argv[1:]
jobs = json.load(open(jobs_path, encoding="utf-8"))
executions = json.load(open(executions_path, encoding="utf-8"))
if jobs != [job_name]:
    raise SystemExit("[FAIL] Recovery Job inventory is not exactly the pinned Job")
if executions:
    raise SystemExit("[FAIL] Recovery Job is not inert")
PY
then
    echo "[FAIL] Recovery Job is not inert"
    exit 1
fi

if ! "$PYTHON_BIN" -I \
    "$PROJECT_ROOT/scripts/phase1_0d_transport_recovery.py" \
    verify-freshness \
    --certificate "$CAPACITY_CERTIFICATE" \
    --max-age-seconds 600 >/dev/null
then
    echo "$CAPACITY_BLOCKED"
    echo "[FAIL] Capacity evidence expired before recovery lock creation"
    exit 1
fi

LOCK_FILE="$RECORD_DIR/transport_recovery_lock.json"
"$PYTHON_BIN" -I - \
    "$PROJECT_ROOT" "$RUN_ID" "$JOB_NAME" "$LAUNCHER_SHA" \
    "$CAPACITY_CERTIFICATE_SHA256" "$CAPACITY_MANIFEST_SHA256" \
    "$CAPACITY_CERTIFICATE" "$LOCK_FILE" <<'PY'
import importlib.util
import json
import os
import sys
from pathlib import Path

(
    root,
    run_id,
    job_name,
    launcher_commit,
    certificate_sha,
    manifest_sha,
    certificate_path,
    output,
) = sys.argv[1:]
spec = importlib.util.spec_from_file_location(
    "transport_recovery", Path(root) / "scripts/phase1_0d_transport_recovery.py"
)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
certificate = json.load(open(certificate_path, encoding="utf-8"))
lock = module.build_recovery_lock(
    run_id=run_id,
    job_name=job_name,
    launcher_commit=launcher_commit,
    capacity_certificate_sha256=certificate_sha,
    capacity_manifest_sha256=manifest_sha,
    request_body_rollups_value=certificate["evidence"]["request_body_rollups"],
)
descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "wb") as stream:
    stream.write(module.canonical_json_bytes(lock))
PY
if ! az storage blob upload \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "$RECOVERY_LOCK_BLOB" \
    --file "$LOCK_FILE" \
    --overwrite false --only-show-errors --output none
then
    echo "$TERMINAL_AMBIGUITY"
    echo "[FAIL] Create-only recovery lock was not established"
    exit 2
fi

# Exactly one non-retrying start request. Any transport or response ambiguity
# is followed only by execution inventory; this call site is never revisited.
START_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${JOB_NAME}/start?api-version=${API_VERSION}"
ACCESS_TOKEN="$(az account get-access-token \
    --resource https://management.azure.com/ --query accessToken -o tsv)"
START_BODY="$RECORD_DIR/start_response.json"
set +e
START_STATUS="$(curl --silent --show-error --max-redirs 0 \
    --connect-timeout 30 --max-time 120 \
    --request POST \
    --header "Authorization: Bearer ${ACCESS_TOKEN}" \
    --header "Content-Length: 0" \
    --output "$START_BODY" \
    --write-out '%{http_code}' \
    "$START_URL")"
START_CURL_STATUS=$?
set -e
unset ACCESS_TOKEN

RESPONSE_EXECUTION_NAME=""
if (( START_CURL_STATUS == 0 )) && [[ "$START_STATUS" =~ ^2[0-9][0-9]$ ]]; then
    RESPONSE_EXECUTION_NAME="$("$PYTHON_BIN" -I -c \
        'import json,sys
try:
 print(json.load(open(sys.argv[1])).get("name",""))
except Exception:
 print("")' "$START_BODY")"
fi

AFTER_EXECUTIONS="$RECORD_DIR/executions_after.json"
for _ in $(seq 1 24); do
    az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" -o json >"$AFTER_EXECUTIONS"
    AFTER_COUNT="$("$PYTHON_BIN" -I -c \
        'import json,sys; print(len(json.load(open(sys.argv[1]))))' \
        "$AFTER_EXECUTIONS")"
    if [[ "$AFTER_COUNT" != "0" ]]; then
        break
    fi
    sleep 5
done

CLASSIFICATION="$("$PYTHON_BIN" -I - \
    "$PROJECT_ROOT" "$RESPONSE_EXECUTION_NAME" "$AFTER_EXECUTIONS" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

root, response_name, after_path = sys.argv[1:]
spec = importlib.util.spec_from_file_location(
    "transport_recovery", Path(root) / "scripts/phase1_0d_transport_recovery.py"
)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
after = json.load(open(after_path, encoding="utf-8"))
names = [item["name"] for item in after]
print(json.dumps(module.classify_start([], response_name or None, names)))
PY
)"
CLASSIFICATION_STATE="$("$PYTHON_BIN" -I -c \
    'import json,sys; print(json.load(sys.stdin)["state"])' <<<"$CLASSIFICATION")"
if [[ "$CLASSIFICATION_STATE" != "EXECUTION_ESTABLISHED" ]]; then
    echo "$TERMINAL_AMBIGUITY"
    echo "$CLASSIFICATION"
    exit 2
fi

EXECUTION_NAME="$("$PYTHON_BIN" -I -c \
    'import json,sys; print(json.load(sys.stdin)["execution_name"])' \
    <<<"$CLASSIFICATION")"
echo "[OK] recovery_job=$JOB_NAME"
echo "[OK] recovery_execution=$EXECUTION_NAME"
echo "[OK] recovery_run_id=$RUN_ID"
echo "[OK] recovery_result_prefix=$RESULT_PREFIX"
echo "[OK] start_request_count=1"
echo "[OK] start_may_be_retried=false"
