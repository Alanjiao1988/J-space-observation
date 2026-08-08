#!/usr/bin/env bash
# Build, pin and lock the Study 2 Stage B-D model-free finalization image.
#
#   ACR_NAME=<registry> ./25b_build_study2_stage_bd_finalize.sh
#
# The build refuses to complete if torch or transformers is importable, so the
# stage that computes Gate A cannot load a model even by mistake.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
IMAGE_REPOSITORY="j-space-observation-study2-stage-bd-finalize"
DOCKERFILE="infra/azure/acr_tasks/study2_stage_bd_finalize.Dockerfile"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
PROJECT_TREE="$(git -C "$PROJECT_ROOT" rev-parse "${PROJECT_SHA}^{tree}")"
BUILD_RECORD_DIR="${STAGE_BD_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/study2-stage-bd-finalize-build-${PROJECT_SHA}}"
CONTEXT_DIR="$(mktemp -d)"
trap 'rm -rf "$CONTEXT_DIR"' EXIT

if [[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] The build requires clean HEAD == PROJECT_SHA"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Refusing to build a dirty worktree under immutable tag $PROJECT_SHA"
    exit 1
fi
if az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --output none 2>/dev/null; then
    echo "[FAIL] ${IMAGE_REPOSITORY}:${PROJECT_SHA} already exists; use a new commit"
    exit 1
fi

git -C "$PROJECT_ROOT" bundle create "$CONTEXT_DIR/repo.bundle" HEAD
cp "$PROJECT_ROOT/$DOCKERFILE" "$CONTEXT_DIR/Dockerfile"

mkdir -p "$BUILD_RECORD_DIR"
az acr build \
    --registry "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --file Dockerfile \
    --platform linux/amd64 \
    --build-arg "SOURCE_COMMIT=${PROJECT_SHA}" \
    --build-arg "SOURCE_TREE=${PROJECT_TREE}" \
    "$CONTEXT_DIR" \
    | tee "$BUILD_RECORD_DIR/acr_build.log"

IMAGE_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
if [[ ! "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] The build produced no resolvable digest"
    exit 1
fi

az acr repository update \
    --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --write-enabled false --delete-enabled false --output none
az acr manifest update-metadata \
    --registry "$ACR_NAME" --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --write-enabled false --delete-enabled false --output none

printf '%s\n' "$IMAGE_DIGEST" >"$BUILD_RECORD_DIR/image_digest.txt"
printf '%s\n' "$PROJECT_SHA" >"$BUILD_RECORD_DIR/project_sha.txt"
echo "[OK] image=${IMAGE_REPOSITORY}:${PROJECT_SHA}"
echo "[OK] digest=$IMAGE_DIGEST"
echo "[OK] Tag and manifest are locked against write and delete"
