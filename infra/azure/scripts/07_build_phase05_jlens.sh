#!/usr/bin/env bash
# Build to a unique staging tag, CAS-claim the project tag, then lock both.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
IMAGE_REPOSITORY="j-space-observation-jlens"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
BUILD_INVOCATION_ID="${BUILD_INVOCATION_ID:-$(date -u +'%Y%m%d%H%M%S')-$$-${RANDOM}}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ ! "$BUILD_INVOCATION_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "[FAIL] BUILD_INVOCATION_ID contains invalid tag characters"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Refusing to build a dirty worktree under immutable tag $PROJECT_SHA"
    exit 1
fi
if [[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] PROJECT_SHA does not equal the checked-out commit"
    exit 1
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
CLAIM_NAME="jlens-image-${PROJECT_SHA}"
CLAIM_URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Resources/deployments/${CLAIM_NAME}?api-version=2022-09-01"

confirm_project_tag_absent() {
    local repositories tags
    if ! repositories="$(az acr repository list \
        --name "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
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

require_confirmed_absence

RECORD_DIR="${JLENS_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase05-jlens-build-${PROJECT_SHA}}"
mkdir -p "$RECORD_DIR"
CLAIM_BODY="$RECORD_DIR/.azure_phase05_jlens_image_claim.json"
cleanup_claim_body() {
    rm -f "$CLAIM_BODY"
}
trap cleanup_claim_body EXIT
STARTED_AT="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

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

# Both contenders may have built, so re-check immediately before the CAS claim.
require_confirmed_absence

python - "$CLAIM_BODY" "$PROJECT_SHA" "$BUILD_INVOCATION_ID" "$RUN_ID" "$DIGEST" <<'PY'
import json
import sys
from pathlib import Path

path, project_sha, invocation_id, run_id, digest = sys.argv[1:]
parameters = {
    "projectSha": {"value": project_sha},
    "invocationId": {"value": invocation_id},
    "buildRunId": {"value": run_id},
    "imageDigest": {"value": digest},
}
template_parameters = {
    key: {"type": "string"} for key in parameters
}
outputs = {
    key: {"type": "string", "value": f"[parameters('{key}')]"}
    for key in parameters
}
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
            "parameters": template_parameters,
            "resources": [],
            "outputs": outputs,
        },
    }
}
Path(path).write_text(json.dumps(body, sort_keys=True) + "\n", encoding="utf-8")
PY

if ! az rest \
    --method put \
    --url "$CLAIM_URL" \
    --headers "Content-Type=application/json" "If-None-Match=*" \
    --body "@$CLAIM_BODY" \
    --output none; then
    echo "[FAIL] Distributed image claim lost or could not be established (409/412/unknown)"
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
            echo "[FAIL] Image claim deployment ended in $CLAIM_STATE"
            exit 1
            ;;
    esac
    sleep 5
done
if [[ "$CLAIM_STATE" != "Succeeded" ]]; then
    echo "[FAIL] Timed out establishing distributed image claim"
    exit 1
fi
CLAIMED_INVOCATION="$(az rest \
    --method get --url "$CLAIM_URL" \
    --query properties.outputs.invocationId.value -o tsv)"
CLAIMED_RUN_ID="$(az rest \
    --method get --url "$CLAIM_URL" \
    --query properties.outputs.buildRunId.value -o tsv)"
CLAIMED_DIGEST="$(az rest \
    --method get --url "$CLAIM_URL" \
    --query properties.outputs.imageDigest.value -o tsv)"
CLAIMED_PROJECT_SHA="$(az rest \
    --method get --url "$CLAIM_URL" \
    --query properties.outputs.projectSha.value -o tsv)"
if [[ "$CLAIMED_INVOCATION" != "$BUILD_INVOCATION_ID" \
    || "$CLAIMED_RUN_ID" != "$RUN_ID" \
    || "$CLAIMED_DIGEST" != "$DIGEST" \
    || "$CLAIMED_PROJECT_SHA" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] Distributed image claim provenance mismatch"
    exit 1
fi

# The claim is held; any tag appearing now is foreign and must not be overwritten.
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
    echo "[FAIL] Claimed project tag does not match this build output"
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
    --query writeEnabled -o tsv)"
TAG_DELETE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --query deleteEnabled -o tsv)"
MANIFEST_WRITE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}@${DIGEST}" \
    --query writeEnabled -o tsv)"
MANIFEST_DELETE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}@${DIGEST}" \
    --query deleteEnabled -o tsv)"
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

# Remove only this invocation's staging tag after the final claim is locked.
az acr repository untag \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${STAGING_TAG}"
REMAINING_TAGS="$(az acr repository show-tags \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --output tsv)"
if grep -Fxq "$STAGING_TAG" <<<"$REMAINING_TAGS"; then
    echo "[FAIL] Staging tag cleanup was not confirmed"
    exit 1
fi

REQUIREMENTS_SHA="$(sha256sum "$PROJECT_ROOT/requirements-jlens.txt" | awk '{print $1}')"
DOCKERFILE_SHA="$(sha256sum "$PROJECT_ROOT/Dockerfile.jlens" | awk '{print $1}')"
python - "$RECORD_DIR/phase05_jlens_acr_build.json" <<PY
import json
from pathlib import Path

record = {
    "schema_version": "phase05-jlens-acr-build-v2",
    "started_at_utc": "$STARTED_AT",
    "finished_at_utc": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "project_sha": "$PROJECT_SHA",
    "build_invocation_id": "$BUILD_INVOCATION_ID",
    "claim_name": "$CLAIM_NAME",
    "claim_state": "$CLAIM_STATE",
    "dockerfile": "Dockerfile.jlens",
    "dockerfile_sha256": "$DOCKERFILE_SHA",
    "requirements_sha256": "$REQUIREMENTS_SHA",
    "image_repository": "$IMAGE_REPOSITORY",
    "image_tag": "$PROJECT_SHA",
    "image_ref": "$IMAGE_REF",
    "image_digest": "$DIGEST",
    "staging_tag": "$STAGING_TAG",
    "staging_tag_removed": True,
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
Path("$RECORD_DIR/phase05_jlens_acr_build.json").write_text(
    json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

echo "[OK] $IMAGE_REF"
echo "[OK] digest=$DIGEST run_id=$RUN_ID claim=$CLAIM_NAME"
echo "[OK] record=$RECORD_DIR/phase05_jlens_acr_build.json"
