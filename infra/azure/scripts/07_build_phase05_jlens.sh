#!/usr/bin/env bash
# Build to a unique staging tag and elect one durable deployment-ticket winner.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
CLAIM_HELPER="$SCRIPT_DIR/phase05_claim_election.py"

# Bind `python` to the authenticated absolute interpreter, as
# 09_build_parser_v2_eval.sh does. Debian 12 ships python3 with no `python`
# alias, so an unqualified `python` is both unportable and PATH-hijackable.
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

ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
IMAGE_REPOSITORY="j-space-observation-jlens"
PROJECT_SHA_INPUT="${PROJECT_SHA:-}"
PROJECT_SHA="${PROJECT_SHA_INPUT:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
FINALIZE_EXISTING_BUILD="${JLENS_FINALIZE_EXISTING_BUILD:-false}"
CLAIM_SETTLE_SECONDS="${CLAIM_SETTLE_SECONDS:-15}"
CLAIM_RECHECK_SECONDS="${CLAIM_RECHECK_SECONDS:-3}"
BUILD_INVOCATION_ID="$(python "$CLAIM_HELPER" new-id)"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ "$FINALIZE_EXISTING_BUILD" != "true" \
    && "$FINALIZE_EXISTING_BUILD" != "false" ]]; then
    echo "[FAIL] JLENS_FINALIZE_EXISTING_BUILD must be true or false"
    exit 1
fi
if [[ ! "$BUILD_INVOCATION_ID" =~ ^[0-9a-f]{32}$ ]]; then
    echo "[FAIL] BUILD_INVOCATION_ID must be a cryptographic 32-hex ID"
    exit 1
fi
if [[ ! "$CLAIM_SETTLE_SECONDS" =~ ^[0-9]+$ \
    || ! "$CLAIM_RECHECK_SECONDS" =~ ^[0-9]+$ ]]; then
    echo "[FAIL] Claim settling intervals must be nonnegative integers"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Refusing to build a dirty worktree under immutable tag $PROJECT_SHA"
    exit 1
fi
CURRENT_HEAD_SHA="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
if [[ "$FINALIZE_EXISTING_BUILD" == "true" ]]; then
    if [[ -z "$PROJECT_SHA_INPUT" ]]; then
        echo "[FAIL] Finalize mode requires explicit historical PROJECT_SHA"
        exit 1
    fi
    if ! git -C "$PROJECT_ROOT" cat-file -e "${PROJECT_SHA}^{commit}"; then
        echo "[FAIL] Historical PROJECT_SHA is not a local git commit"
        exit 1
    fi
else
    if [[ "$CURRENT_HEAD_SHA" != "$PROJECT_SHA" ]]; then
        echo "[FAIL] Normal build requires clean HEAD == PROJECT_SHA"
        exit 1
    fi
fi

LOGIN_SERVER="$(az acr show \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query loginServer -o tsv)"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
IMAGE_TAG="${IMAGE_REPOSITORY}:${PROJECT_SHA}"
IMAGE_REF="${LOGIN_SERVER}/${IMAGE_TAG}"
STAGING_TAG="staging-${PROJECT_SHA}-${BUILD_INVOCATION_ID}"
STAGING_IMAGE_TAG="${IMAGE_REPOSITORY}:${STAGING_TAG}"
STAGING_IMAGE_REF="${LOGIN_SERVER}/${STAGING_IMAGE_TAG}"
PROJECT_CLAIM_KEY="$(printf '%s' "$PROJECT_SHA" | sha256sum | awk '{print substr($1,1,20)}')"
CLAIM_PREFIX="p05b-${PROJECT_CLAIM_KEY}--"
CLAIM_NAME="${CLAIM_PREFIX}${BUILD_INVOCATION_ID}"
CLAIM_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Resources/deployments/${CLAIM_NAME}?api-version=2022-09-01"

confirm_project_tag_absent() {
    local repositories tags
    if ! repositories="$(az acr repository list \
        --name "$ACR_NAME" \
        --output tsv)"; then
        echo "[FAIL] Could not establish ACR repository existence"
        return 2
    fi
    if ! grep -Fxq "$IMAGE_REPOSITORY" <<<"$repositories"; then
        return 0
    fi
    if ! tags="$(az acr repository show-tags \
        --name "$ACR_NAME" \
        --repository "$IMAGE_REPOSITORY" \
        --output tsv)"; then
        echo "[FAIL] Could not establish project-tag existence"
        return 2
    fi
    if grep -Fxq "$PROJECT_SHA" <<<"$tags"; then
        return 1
    fi
    return 0
}

require_confirmed_absence() {
    local result
    if confirm_project_tag_absent; then
        return 0
    else
        result=$?
    fi
    if [[ "$result" -eq 1 ]]; then
        echo "[FAIL] Immutable project tag already exists: $IMAGE_REF"
    else
        echo "[FAIL] Project-tag absence was not confirmed"
    fi
    exit 1
}

RECORD_DIR="${JLENS_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase05-jlens-build-${PROJECT_SHA}}"
mkdir -p "$RECORD_DIR"
SCRATCH_DIR="$(python "$CLAIM_HELPER" scratch-path \
    --record-dir "$RECORD_DIR" \
    --operation build \
    --invocation-id "$BUILD_INVOCATION_ID")"
umask 077
if ! mkdir "$SCRATCH_DIR"; then
    echo "[FAIL] Invocation-specific build scratch already exists"
    exit 1
fi
CLAIM_BODY="$SCRATCH_DIR/image_claim.json"
CLAIMS_FILE="$SCRATCH_DIR/build_claims.json"
FIXED_FILE="$SCRATCH_DIR/build_fixed.json"
WINNER_FILE="$SCRATCH_DIR/build_winner.json"
cleanup_files() {
    rm -rf "$SCRATCH_DIR"
}
trap cleanup_files EXIT
STARTED_AT="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

if [[ "$FINALIZE_EXISTING_BUILD" == "true" ]]; then
    python - "$FIXED_FILE" "$CLAIM_PREFIX" "$PROJECT_SHA" "$IMAGE_REPOSITORY" <<'PY'
import json
import sys
from pathlib import Path

path, prefix, project_sha, repository = sys.argv[1:]
Path(path).write_text(
    json.dumps(
        {
            "operation": "build",
            "claimPrefix": prefix,
            "projectSha": project_sha,
            "imageRepository": repository,
        },
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY
    az deployment group list \
        --resource-group "$RESOURCE_GROUP" \
        --output json >"$CLAIMS_FILE"
    python "$CLAIM_HELPER" elect \
        --claims-json "$CLAIMS_FILE" \
        --prefix "$CLAIM_PREFIX" \
        --fixed-json "$FIXED_FILE" \
        --output "$WINNER_FILE"
    FINALIZE_WINNER_NAME="$(python "$CLAIM_HELPER" get \
        --json "$WINNER_FILE" --field name)"
    FINALIZE_WINNER_TIME="$(python "$CLAIM_HELPER" get \
        --json "$WINNER_FILE" --field server_timestamp)"
    FINALIZE_WINNER_STATE="$(python "$CLAIM_HELPER" get \
        --json "$WINNER_FILE" --field provisioning_state)"
    FINALIZE_INVOCATION_ID="$(python "$CLAIM_HELPER" get \
        --json "$WINNER_FILE" --field outputs.invocationId)"
    FINALIZE_RUN_ID="$(python "$CLAIM_HELPER" get \
        --json "$WINNER_FILE" --field outputs.buildRunId)"
    FINALIZE_DIGEST="$(python "$CLAIM_HELPER" get \
        --json "$WINNER_FILE" --field outputs.imageDigest)"
    FINALIZE_STAGING_TAG="$(python "$CLAIM_HELPER" get \
        --json "$WINNER_FILE" --field outputs.stagingTag)"
    FINALIZE_CANDIDATE_COUNT="$(python "$CLAIM_HELPER" get \
        --json "$WINNER_FILE" --field candidate_count)"
    if [[ "$FINALIZE_WINNER_STATE" != "Succeeded" \
        || "$FINALIZE_WINNER_NAME" != "${CLAIM_PREFIX}${FINALIZE_INVOCATION_ID}" \
        || ! "$FINALIZE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
        echo "[FAIL] Retained durable build claim is invalid"
        exit 1
    fi
    sleep "$CLAIM_RECHECK_SECONDS"
    az deployment group list \
        --resource-group "$RESOURCE_GROUP" \
        --output json >"$CLAIMS_FILE"
    python "$CLAIM_HELPER" elect \
        --claims-json "$CLAIMS_FILE" \
        --prefix "$CLAIM_PREFIX" \
        --fixed-json "$FIXED_FILE" \
        --output "$WINNER_FILE"
    if [[ "$(python "$CLAIM_HELPER" get --json "$WINNER_FILE" --field name)" != "$FINALIZE_WINNER_NAME" \
        || "$(python "$CLAIM_HELPER" get --json "$WINNER_FILE" --field server_timestamp)" != "$FINALIZE_WINNER_TIME" ]]; then
        echo "[FAIL] Retained build claim election changed during finalization"
        exit 1
    fi

    FINALIZE_RUN_STATUS="$(az acr task show-run \
        --registry "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --run-id "$FINALIZE_RUN_ID" \
        --query status -o tsv)"
    FINALIZE_RUN_DIGEST="$(az acr task show-run \
        --registry "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --run-id "$FINALIZE_RUN_ID" \
        --query 'outputImages[0].digest' -o tsv)"
    FINALIZE_TAG_DIGEST="$(az acr repository show-manifests \
        --name "$ACR_NAME" \
        --repository "$IMAGE_REPOSITORY" \
        --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
        -o tsv)"
    if [[ "$FINALIZE_RUN_STATUS" != "Succeeded" \
        || "$FINALIZE_RUN_DIGEST" != "$FINALIZE_DIGEST" \
        || "$FINALIZE_TAG_DIGEST" != "$FINALIZE_DIGEST" ]]; then
        echo "[FAIL] Build run/project tag does not match durable claim"
        exit 1
    fi

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
        --name "${IMAGE_REPOSITORY}@${FINALIZE_DIGEST}" \
        --query changeableAttributes.writeEnabled -o tsv)"
    MANIFEST_DELETE_ENABLED="$(az acr manifest show-metadata \
        --registry "$ACR_NAME" \
        --name "${IMAGE_REPOSITORY}@${FINALIZE_DIGEST}" \
        --query changeableAttributes.deleteEnabled -o tsv)"
    if [[ "${TAG_WRITE_ENABLED,,}" != "false" \
        || "${TAG_DELETE_ENABLED,,}" != "false" \
        || "${MANIFEST_WRITE_ENABLED,,}" != "false" \
        || "${MANIFEST_DELETE_ENABLED,,}" != "false" ]]; then
        echo "[FAIL] Existing image is not fully immutable"
        exit 1
    fi

    FINALIZE_TAGS="$(az acr repository show-tags \
        --name "$ACR_NAME" \
        --repository "$IMAGE_REPOSITORY" \
        --output tsv)"
    STAGING_TAG_REMOVED=true
    STAGING_TAG_RETAINED_IMMUTABLE=false
    if grep -Fxq "$FINALIZE_STAGING_TAG" <<<"$FINALIZE_TAGS"; then
        FINALIZE_STAGING_DIGEST="$(az acr repository show-manifests \
            --name "$ACR_NAME" \
            --repository "$IMAGE_REPOSITORY" \
            --query "[?tags[?@=='${FINALIZE_STAGING_TAG}']].digest | [0]" \
            -o tsv)"
        if [[ "$FINALIZE_STAGING_DIGEST" != "$FINALIZE_DIGEST" ]]; then
            echo "[FAIL] Retained staging alias digest mismatches durable claim"
            exit 1
        fi
        STAGING_TAG_REMOVED=false
        STAGING_TAG_RETAINED_IMMUTABLE=true
    fi

    if ! git -C "$PROJECT_ROOT" cat-file -e "${PROJECT_SHA}:Dockerfile.jlens" \
        || ! git -C "$PROJECT_ROOT" cat-file -e "${PROJECT_SHA}:requirements-jlens.txt"; then
        echo "[FAIL] Historical dependency/image source objects are missing"
        exit 1
    fi
    DOCKERFILE_SHA="$(git -C "$PROJECT_ROOT" cat-file blob \
        "${PROJECT_SHA}:Dockerfile.jlens" | sha256sum | awk '{print $1}')"
    REQUIREMENTS_SHA="$(git -C "$PROJECT_ROOT" cat-file blob \
        "${PROJECT_SHA}:requirements-jlens.txt" | sha256sum | awk '{print $1}')"
    python - "$RECORD_DIR/phase05_jlens_acr_build.json" <<PY
import json
import sys
from pathlib import Path

record = {
    "schema_version": "phase05-jlens-acr-build-v4",
    "started_at_utc": "$STARTED_AT",
    "finished_at_utc": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "project_sha": "$PROJECT_SHA",
    "historical_project_sha": "$PROJECT_SHA",
    "current_head_sha": "$CURRENT_HEAD_SHA",
    "finalize_existing_build": True,
    "recovery_finalization": True,
    "acr_build_skipped": True,
    "image_import_skipped": True,
    "new_claim_skipped": True,
    "unlock_performed": False,
    "build_invocation_id": "$FINALIZE_INVOCATION_ID",
    "claim_prefix": "$CLAIM_PREFIX",
    "claim_name": "$FINALIZE_WINNER_NAME",
    "claim_state": "$FINALIZE_WINNER_STATE",
    "claim_server_timestamp": "$FINALIZE_WINNER_TIME",
    "claim_candidate_count": int("$FINALIZE_CANDIDATE_COUNT"),
    "winner_rechecked": True,
    "claim_deployment_retained": True,
    "dockerfile": "Dockerfile.jlens",
    "dockerfile_sha256": "$DOCKERFILE_SHA",
    "requirements_sha256": "$REQUIREMENTS_SHA",
    "source_hash_mode": "historical_git_objects",
    "image_repository": "$IMAGE_REPOSITORY",
    "image_tag": "$PROJECT_SHA",
    "image_ref": "${LOGIN_SERVER}/${IMAGE_REPOSITORY}:${PROJECT_SHA}",
    "image_digest": "$FINALIZE_DIGEST",
    "staging_tag": "$FINALIZE_STAGING_TAG",
    "staging_tag_removed": "$STAGING_TAG_REMOVED" == "true",
    "staging_tag_retained_immutable": (
        "$STAGING_TAG_RETAINED_IMMUTABLE" == "true"
    ),
    "locked_tag_digest": "$FINALIZE_TAG_DIGEST",
    "acr_build_run_id": "$FINALIZE_RUN_ID",
    "acr_build_status": "$FINALIZE_RUN_STATUS",
    "tag_write_enabled": False,
    "tag_delete_enabled": False,
    "manifest_write_enabled": False,
    "manifest_delete_enabled": False,
    "immutability_verified": True,
    "latest_used": False,
    "overwrite_used": False,
}
Path(sys.argv[1]).write_text(
    json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY
    echo "[OK] Finalized existing immutable build $FINALIZE_RUN_ID"
    echo "[OK] claim=$FINALIZE_WINNER_NAME digest=$FINALIZE_DIGEST"
    echo "[OK] record=$RECORD_DIR/phase05_jlens_acr_build.json"
    exit 0
fi

require_confirmed_absence

echo "[RUN] Building staging image $STAGING_IMAGE_REF from Dockerfile.jlens"
RUN_ID="$(az acr build \
    --registry "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --file "$PROJECT_ROOT/Dockerfile.jlens" \
    --image "$STAGING_IMAGE_TAG" \
    --no-logs \
    --query runId -o tsv \
    "$PROJECT_ROOT")"
if [[ -z "$RUN_ID" ]]; then
    echo "[FAIL] ACR did not return a quick-build run ID"
    exit 1
fi

STATUS=""
for _ in $(seq 1 180); do
    STATUS="$(az acr task show-run \
        --registry "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --run-id "$RUN_ID" \
        --query status -o tsv)"
    if [[ "$STATUS" == "Succeeded" \
        || "$STATUS" == "Failed" \
        || "$STATUS" == "Canceled" \
        || "$STATUS" == "Error" ]]; then
        break
    fi
    sleep 20
done
if [[ "$STATUS" != "Succeeded" ]]; then
    echo "[FAIL] ACR build $RUN_ID ended with status $STATUS"
    exit 1
fi

RUN_OUTPUT_DIGEST="$(az acr task show-run \
    --registry "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --run-id "$RUN_ID" \
    --query 'outputImages[0].digest' -o tsv)"
STAGING_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${STAGING_TAG}']].digest | [0]" \
    -o tsv)"
if [[ ! "$RUN_OUTPUT_DIGEST" =~ ^sha256:[0-9a-f]{64}$ \
    || "$STAGING_DIGEST" != "$RUN_OUTPUT_DIGEST" ]]; then
    echo "[FAIL] Staging tag does not match this ACR build output"
    exit 1
fi
DIGEST="$RUN_OUTPUT_DIGEST"

python - "$CLAIM_BODY" "$CLAIM_PREFIX" "$CLAIM_NAME" "$BUILD_INVOCATION_ID" \
    "$PROJECT_SHA" "$IMAGE_REPOSITORY" "$RUN_ID" "$DIGEST" "$STAGING_TAG" <<'PY'
import json
import sys
from pathlib import Path

(
    path,
    claim_prefix,
    claim_name,
    invocation_id,
    project_sha,
    repository,
    run_id,
    digest,
    staging_tag,
) = sys.argv[1:]
values = {
    "claimPrefix": claim_prefix,
    "claimName": claim_name,
    "invocationId": invocation_id,
    "operation": "build",
    "projectSha": project_sha,
    "imageRepository": repository,
    "buildRunId": run_id,
    "imageDigest": digest,
    "stagingTag": staging_tag,
}
parameters = {key: {"value": value} for key, value in values.items()}
body = {
    "properties": {
        "mode": "Incremental",
        "parameters": parameters,
        "template": {
            "$schema": (
                "https://schema.management.azure.com/schemas/"
                "2019-04-01/deploymentTemplate.json#"
            ),
            "contentVersion": "1.0.0.0",
            "parameters": {key: {"type": "string"} for key in values},
            "resources": [],
            "outputs": {
                key: {"type": "string", "value": f"[parameters('{key}')]"}
                for key in values
            },
        },
    }
}
Path(path).write_text(json.dumps(body, sort_keys=True) + "\n", encoding="utf-8")
PY
python - "$FIXED_FILE" "$CLAIM_PREFIX" "$PROJECT_SHA" "$IMAGE_REPOSITORY" <<'PY'
import json
import sys
from pathlib import Path

path, prefix, project_sha, repository = sys.argv[1:]
Path(path).write_text(
    json.dumps(
        {
            "operation": "build",
            "claimPrefix": prefix,
            "projectSha": project_sha,
            "imageRepository": repository,
        },
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY

# The deployment name is cryptographically unique; no shared resource is updated.
if ! az rest \
    --method put \
    --url "$CLAIM_URL" \
    --headers "Content-Type=application/json" \
    --body "@$CLAIM_BODY" \
    --output none; then
    echo "[FAIL] Unique durable build ticket could not be created"
    exit 1
fi

CLAIM_STATE=""
for _ in $(seq 1 120); do
    CLAIM_STATE="$(az rest \
        --method get \
        --url "$CLAIM_URL" \
        --query properties.provisioningState -o tsv)"
    case "$CLAIM_STATE" in
        Succeeded)
            break
            ;;
        Failed|Canceled|Cancelled|Deleted)
            echo "[FAIL] Build ticket deployment ended in $CLAIM_STATE"
            exit 1
            ;;
    esac
    sleep 5
done
if [[ "$CLAIM_STATE" != "Succeeded" ]]; then
    echo "[FAIL] Timed out creating durable build ticket"
    exit 1
fi

cleanup_own_staging() {
    az acr repository untag \
        --name "$ACR_NAME" \
        --image "${IMAGE_REPOSITORY}:${STAGING_TAG}"
}

elect_build_winner() {
    az deployment group list \
        --resource-group "$RESOURCE_GROUP" \
        --output json >"$CLAIMS_FILE"
    python "$CLAIM_HELPER" elect \
        --claims-json "$CLAIMS_FILE" \
        --prefix "$CLAIM_PREFIX" \
        --fixed-json "$FIXED_FILE" \
        --output "$WINNER_FILE"
}

sleep "$CLAIM_SETTLE_SECONDS"
if ! elect_build_winner; then
    cleanup_own_staging
    echo "[FAIL] Build ticket set is invalid; manual intervention required"
    exit 1
fi
FIRST_WINNER_NAME="$(python "$CLAIM_HELPER" get --json "$WINNER_FILE" --field name)"
FIRST_WINNER_TIME="$(python "$CLAIM_HELPER" get --json "$WINNER_FILE" --field server_timestamp)"
FIRST_WINNER_STATE="$(python "$CLAIM_HELPER" get --json "$WINNER_FILE" --field provisioning_state)"
if [[ "$FIRST_WINNER_NAME" != "$CLAIM_NAME" \
    || "$FIRST_WINNER_STATE" != "Succeeded" ]]; then
    cleanup_own_staging
    echo "[FAIL] Earlier build ticket won or blocks promotion; manual intervention required"
    exit 1
fi

sleep "$CLAIM_RECHECK_SECONDS"
if ! elect_build_winner; then
    cleanup_own_staging
    echo "[FAIL] Build ticket re-election failed; manual intervention required"
    exit 1
fi
SECOND_WINNER_NAME="$(python "$CLAIM_HELPER" get --json "$WINNER_FILE" --field name)"
SECOND_WINNER_TIME="$(python "$CLAIM_HELPER" get --json "$WINNER_FILE" --field server_timestamp)"
if [[ "$SECOND_WINNER_NAME" != "$FIRST_WINNER_NAME" \
    || "$SECOND_WINNER_TIME" != "$FIRST_WINNER_TIME" ]]; then
    cleanup_own_staging
    echo "[FAIL] Build ticket winner changed before promotion"
    exit 1
fi

# Only the durable winner may re-confirm absence and promote without overwrite.
require_confirmed_absence
az acr import \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --source "${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${DIGEST}" \
    --image "$IMAGE_TAG" \
    --output none
CLAIMED_TAG_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
if [[ "$CLAIMED_TAG_DIGEST" != "$DIGEST" ]]; then
    echo "[FAIL] Promoted project tag does not match the elected build output"
    exit 1
fi

# Remove this invocation's staging alias while delete is still enabled.
cleanup_own_staging
REMAINING_TAGS="$(az acr repository show-tags \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --output tsv)"
if grep -Fxq "$STAGING_TAG" <<<"$REMAINING_TAGS"; then
    echo "[FAIL] Staging tag cleanup was not confirmed before lock"
    exit 1
fi

az acr repository update \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --write-enabled false \
    --delete-enabled false \
    --output none
az acr repository update \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}@${DIGEST}" \
    --write-enabled false \
    --delete-enabled false \
    --output none
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
    --name "${IMAGE_REPOSITORY}@${DIGEST}" \
    --query changeableAttributes.writeEnabled -o tsv)"
MANIFEST_DELETE_ENABLED="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${IMAGE_REPOSITORY}@${DIGEST}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
LOCKED_TAG_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
if [[ "${TAG_WRITE_ENABLED,,}" != "false" \
    || "${TAG_DELETE_ENABLED,,}" != "false" \
    || "${MANIFEST_WRITE_ENABLED,,}" != "false" \
    || "${MANIFEST_DELETE_ENABLED,,}" != "false" \
    || "$LOCKED_TAG_DIGEST" != "$DIGEST" ]]; then
    echo "[FAIL] ACR tag/manifest immutability lock verification failed"
    exit 1
fi

CANDIDATE_COUNT="$(python "$CLAIM_HELPER" get \
    --json "$WINNER_FILE" --field candidate_count)"
REQUIREMENTS_SHA="$(sha256sum "$PROJECT_ROOT/requirements-jlens.txt" | awk '{print $1}')"
DOCKERFILE_SHA="$(sha256sum "$PROJECT_ROOT/Dockerfile.jlens" | awk '{print $1}')"
python - "$RECORD_DIR/phase05_jlens_acr_build.json" <<PY
import json
import sys
from pathlib import Path

record = {
    "schema_version": "phase05-jlens-acr-build-v4",
    "started_at_utc": "$STARTED_AT",
    "finished_at_utc": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "project_sha": "$PROJECT_SHA",
    "historical_project_sha": "$PROJECT_SHA",
    "current_head_sha": "$CURRENT_HEAD_SHA",
    "finalize_existing_build": False,
    "recovery_finalization": False,
    "acr_build_skipped": False,
    "image_import_skipped": False,
    "new_claim_skipped": False,
    "unlock_performed": False,
    "build_invocation_id": "$BUILD_INVOCATION_ID",
    "claim_prefix": "$CLAIM_PREFIX",
    "claim_name": "$CLAIM_NAME",
    "claim_state": "$CLAIM_STATE",
    "claim_server_timestamp": "$FIRST_WINNER_TIME",
    "claim_candidate_count": int("$CANDIDATE_COUNT"),
    "winner_rechecked": True,
    "claim_deployment_retained": True,
    "dockerfile": "Dockerfile.jlens",
    "dockerfile_sha256": "$DOCKERFILE_SHA",
    "requirements_sha256": "$REQUIREMENTS_SHA",
    "source_hash_mode": "clean_worktree_files",
    "image_repository": "$IMAGE_REPOSITORY",
    "image_tag": "$PROJECT_SHA",
    "image_ref": "$IMAGE_REF",
    "image_digest": "$DIGEST",
    "staging_tag": "$STAGING_TAG",
    "staging_tag_removed": True,
    "staging_tag_retained_immutable": False,
    "locked_tag_digest": "$LOCKED_TAG_DIGEST",
    "acr_build_run_id": "$RUN_ID",
    "acr_build_status": "$STATUS",
    "tag_write_enabled": False,
    "tag_delete_enabled": False,
    "manifest_write_enabled": False,
    "manifest_delete_enabled": False,
    "immutability_verified": True,
    "latest_used": False,
    "overwrite_used": False,
}
Path(sys.argv[1]).write_text(
    json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

echo "[OK] $IMAGE_REF"
echo "[OK] digest=$DIGEST run_id=$RUN_ID claim=$CLAIM_NAME"
echo "[OK] record=$RECORD_DIR/phase05_jlens_acr_build.json"
