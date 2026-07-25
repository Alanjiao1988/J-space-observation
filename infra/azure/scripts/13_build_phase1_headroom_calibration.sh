#!/usr/bin/env bash
# Build the dedicated Phase 1.0C Track B calibration image under an immutable
# project-SHA tag, then record the build-time provenance completion artifact.
#
# The generic semantic-audit image cannot be built: its attestation generator
# only accepts a repository whose behaviour-file set equals a frozen 32-file
# list, no reachable commit satisfies that list, and the attestation was never
# committed. This script builds Dockerfile.calibration instead, which carries
# its own pre-committed deterministic provenance record.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
PROVENANCE_HELPER="$PROJECT_ROOT/scripts/calibration_build_provenance.py"

# Bind `python` to the authenticated absolute interpreter, as
# 07_build_phase05_jlens.sh does. Debian 12 ships python3 with no `python`
# alias, so an unqualified `python` is both unportable and PATH-hijackable.
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

ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
IMAGE_REPOSITORY="j-space-observation-calibration"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
BUILD_RECORD_DIR="${CALIBRATION_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase1-calibration-build-${PROJECT_SHA}}"
BUILD_POLL_SECONDS="${BUILD_POLL_SECONDS:-20}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
CURRENT_HEAD_SHA="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
if [[ "$CURRENT_HEAD_SHA" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] The calibration build requires clean HEAD == PROJECT_SHA"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Refusing to build a dirty worktree under immutable tag $PROJECT_SHA"
    exit 1
fi
if [[ ! -f "$PROJECT_ROOT/calibration_build_provenance.json" ]]; then
    echo "[FAIL] calibration_build_provenance.json must be committed before the build"
    exit 1
fi

# Fails closed if any copied file drifted from the recorded digests or from the
# commit the record binds.
PREBUILD_SHA256="$(python "$PROVENANCE_HELPER" \
    --project-root "$PROJECT_ROOT" verify)"
if [[ ! "$PREBUILD_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Pre-build provenance verification did not return a digest"
    exit 1
fi
echo "[OK] Pre-build provenance verified: $PREBUILD_SHA256"

LOGIN_SERVER="$(az acr show \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query loginServer -o tsv)"
if [[ -z "$LOGIN_SERVER" ]]; then
    echo "[FAIL] Could not resolve the registry login server"
    exit 1
fi
IMAGE_TAG="${IMAGE_REPOSITORY}:${PROJECT_SHA}"
IMAGE_REF="${LOGIN_SERVER}/${IMAGE_TAG}"
STAGING_TAG="staging-${PROJECT_SHA}-$(date -u +'%Y%m%dT%H%M%SZ')"
STAGING_IMAGE_TAG="${IMAGE_REPOSITORY}:${STAGING_TAG}"

confirm_project_tag_absent() {
    local repositories tags
    if ! repositories="$(az acr repository list --name "$ACR_NAME" --output tsv)"; then
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

mkdir -p "$BUILD_RECORD_DIR"

echo "[RUN] Building staging image ${LOGIN_SERVER}/${STAGING_IMAGE_TAG} from Dockerfile.calibration"
BUILD_RUN_ID="$(az acr build \
    --registry "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --file "$PROJECT_ROOT/Dockerfile.calibration" \
    --image "$STAGING_IMAGE_TAG" \
    --platform linux/amd64 \
    --no-logs \
    --query runId -o tsv \
    "$PROJECT_ROOT")"
if [[ -z "$BUILD_RUN_ID" ]]; then
    echo "[FAIL] ACR did not return a quick-build run ID"
    exit 1
fi

STATUS=""
for _ in $(seq 1 180); do
    STATUS="$(az acr task show-run \
        --registry "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --run-id "$BUILD_RUN_ID" \
        --query status -o tsv)"
    if [[ "$STATUS" == "Succeeded" \
        || "$STATUS" == "Failed" \
        || "$STATUS" == "Canceled" \
        || "$STATUS" == "Cancelled" \
        || "$STATUS" == "Error" \
        || "$STATUS" == "Timeout" ]]; then
        break
    fi
    sleep "$BUILD_POLL_SECONDS"
done
if [[ "$STATUS" != "Succeeded" ]]; then
    echo "[FAIL] ACR build $BUILD_RUN_ID ended with status $STATUS"
    exit 1
fi

RUN_OUTPUT_DIGEST="$(az acr task show-run \
    --registry "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --run-id "$BUILD_RUN_ID" \
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
IMAGE_DIGEST="$RUN_OUTPUT_DIGEST"

require_confirmed_absence
az acr import \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --source "${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --image "$IMAGE_TAG"

PROMOTED_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
if [[ "$PROMOTED_DIGEST" != "$IMAGE_DIGEST" ]]; then
    echo "[FAIL] Promoted project tag does not carry the built digest"
    exit 1
fi

az acr repository update \
    --name "$ACR_NAME" \
    --image "$IMAGE_TAG" \
    --write-enabled false \
    --delete-enabled false \
    --output none
az acr repository update \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --write-enabled false \
    --delete-enabled false \
    --output none

TAG_WRITE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "$IMAGE_TAG" \
    --query changeableAttributes.writeEnabled -o tsv)"
TAG_DELETE_ENABLED="$(az acr repository show \
    --name "$ACR_NAME" \
    --image "$IMAGE_TAG" \
    --query changeableAttributes.deleteEnabled -o tsv)"
MANIFEST_WRITE_ENABLED="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --query changeableAttributes.writeEnabled -o tsv)"
MANIFEST_DELETE_ENABLED="$(az acr manifest show-metadata \
    --registry "$ACR_NAME" \
    --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
LOCKED_TAG_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
IMMUTABILITY_VERIFIED="false"
if [[ "${TAG_WRITE_ENABLED,,}" == "false" \
    && "${TAG_DELETE_ENABLED,,}" == "false" \
    && "${MANIFEST_WRITE_ENABLED,,}" == "false" \
    && "${MANIFEST_DELETE_ENABLED,,}" == "false" \
    && "$LOCKED_TAG_DIGEST" == "$IMAGE_DIGEST" ]]; then
    IMMUTABILITY_VERIFIED="true"
fi
if [[ "$IMMUTABILITY_VERIFIED" != "true" ]]; then
    echo "[FAIL] Image immutability could not be confirmed for $IMAGE_REF"
    exit 1
fi

az acr repository untag \
    --name "$ACR_NAME" \
    --image "$STAGING_IMAGE_TAG"

BUILT_AT_UTC="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
COMPLETION_FILE="$BUILD_RECORD_DIR/calibration_build_completion.json"
python "$PROVENANCE_HELPER" \
    --project-root "$PROJECT_ROOT" complete \
    --source-commit "$PROJECT_SHA" \
    --build-commit "$CURRENT_HEAD_SHA" \
    --registry-login-server "$LOGIN_SERVER" \
    --image-tag "$PROJECT_SHA" \
    --image-digest "$IMAGE_DIGEST" \
    --acr-build-run-id "$BUILD_RUN_ID" \
    --built-at-utc "$BUILT_AT_UTC" \
    --immutability-verified "$IMMUTABILITY_VERIFIED" \
    --output "$COMPLETION_FILE"
python "$PROVENANCE_HELPER" \
    --project-root "$PROJECT_ROOT" verify-completion \
    --completion "$COMPLETION_FILE"

echo "[OK] image_digest=$IMAGE_DIGEST"
echo "[OK] image_reference=${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"
echo "[OK] immutability_verified=$IMMUTABILITY_VERIFIED"
echo "[OK] build_completion=$COMPLETION_FILE"
