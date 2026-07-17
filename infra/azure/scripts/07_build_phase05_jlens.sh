#!/usr/bin/env bash
# Build the isolated Phase 0.5A image. This script permits only a project-SHA tag.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
IMAGE_REPOSITORY="j-space-observation-jlens"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
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
IMAGE_TAG="${IMAGE_REPOSITORY}:${PROJECT_SHA}"
IMAGE_REF="${LOGIN_SERVER}/${IMAGE_TAG}"

EXISTING_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv 2>/dev/null || true)"
if [[ -n "$EXISTING_DIGEST" ]]; then
    echo "[FAIL] Immutable image tag already exists; refusing overwrite: $IMAGE_REF"
    exit 1
fi

RECORD_DIR="${JLENS_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase05-jlens-build-${PROJECT_SHA}}"
mkdir -p "$RECORD_DIR"
STARTED_AT="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

echo "[RUN] Building $IMAGE_REF from Dockerfile.jlens"
RUN_ID="$(az acr build \
    --registry "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --file "$PROJECT_ROOT/Dockerfile.jlens" \
    --image "$IMAGE_TAG" \
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
DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
if [[ ! "$DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Could not resolve the built image digest"
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

REQUIREMENTS_SHA="$(sha256sum "$PROJECT_ROOT/requirements-jlens.txt" | awk '{print $1}')"
DOCKERFILE_SHA="$(sha256sum "$PROJECT_ROOT/Dockerfile.jlens" | awk '{print $1}')"
python - "$RECORD_DIR/phase05_jlens_acr_build.json" <<PY
import json
from pathlib import Path

record = {
    "schema_version": "phase05-jlens-acr-build-v1",
    "started_at_utc": "$STARTED_AT",
    "finished_at_utc": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "project_sha": "$PROJECT_SHA",
    "dockerfile": "Dockerfile.jlens",
    "dockerfile_sha256": "$DOCKERFILE_SHA",
    "requirements_sha256": "$REQUIREMENTS_SHA",
    "image_repository": "$IMAGE_REPOSITORY",
    "image_tag": "$PROJECT_SHA",
    "image_ref": "$IMAGE_REF",
    "image_digest": "$DIGEST",
    "locked_tag_digest": "$LOCKED_TAG_DIGEST",
    "acr_build_run_id": "$RUN_ID",
    "acr_build_status": "$STATUS",
    "tag_write_enabled": False,
    "tag_delete_enabled": False,
    "manifest_write_enabled": False,
    "manifest_delete_enabled": False,
    "immutability_verified": True,
    "latest_used": False,
}
Path("$RECORD_DIR/phase05_jlens_acr_build.json").write_text(
    json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

echo "[OK] $IMAGE_REF"
echo "[OK] digest=$DIGEST run_id=$RUN_ID"
echo "[OK] record=$RECORD_DIR/phase05_jlens_acr_build.json"
