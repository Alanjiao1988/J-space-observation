#!/usr/bin/env bash
# Build, pin and lock the Study 2 Stage B-D development-execution image.
#
#   ACR_NAME=<registry> ./25_build_study2_stage_bd_gpu.sh
#
# The build is itself the verification.  The Dockerfile clones one exact commit
# from a bundle, asserts commit/tree/clean, deletes the six confirmation objects
# and asserts their absence, then verifies all twenty frozen inputs and
# reconstructs the sealed shard manifest inside the image.  A green build is the
# evidence; a drifted input cannot produce an image.
#
# One immutable tag per commit.  Rebuilding the same commit is refused rather
# than silently producing a second image behind the same name.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
IMAGE_REPOSITORY="j-space-observation-study2-stage-bd"
DOCKERFILE="infra/azure/acr_tasks/study2_stage_bd_gpu.Dockerfile"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
PROJECT_TREE="$(git -C "$PROJECT_ROOT" rev-parse "${PROJECT_SHA}^{tree}")"
BUILD_RECORD_DIR="${STAGE_BD_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/study2-stage-bd-build-${PROJECT_SHA}}"
CONTEXT_DIR="$(mktemp -d)"
trap 'rm -rf "$CONTEXT_DIR"' EXIT

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] The Stage B-D build requires clean HEAD == PROJECT_SHA"
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

# The build context is a bundle plus the Dockerfile and nothing else, so no
# untracked laptop state can reach the image.
git -C "$PROJECT_ROOT" bundle create "$CONTEXT_DIR/repo.bundle" HEAD
# Read the committed blob rather than copying the checkout, so a CRLF worktree
# cannot change the bytes that are built.
git -C "$PROJECT_ROOT" cat-file blob "${PROJECT_SHA}:${DOCKERFILE}" \
    >"$CONTEXT_DIR/Dockerfile"

mkdir -p "$BUILD_RECORD_DIR"
# ``az acr build`` resolves ``--file`` against the working directory before the
# context, so running it from the repository root packs the repository's own
# top-level Dockerfile over this one and silently builds the wrong image.  Run
# it from inside the context directory, where ``Dockerfile`` is unambiguous.
(
    cd "$CONTEXT_DIR"
    az acr build \
        --registry "$ACR_NAME" \
        --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
        --file Dockerfile \
        --platform linux/amd64 \
        --build-arg "SOURCE_COMMIT=${PROJECT_SHA}" \
        --build-arg "SOURCE_TREE=${PROJECT_TREE}" \
        .
) | tee "$BUILD_RECORD_DIR/acr_build.log"

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
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --write-enabled false --delete-enabled false --output none
az acr manifest update-metadata \
    --registry "$ACR_NAME" \
    --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
    --write-enabled false --delete-enabled false --output none

for attribute in writeEnabled deleteEnabled; do
    TAG_VALUE="$(az acr repository show \
        --name "$ACR_NAME" \
        --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
        --query "changeableAttributes.${attribute}" -o tsv)"
    MANIFEST_VALUE="$(az acr manifest show-metadata \
        --registry "$ACR_NAME" \
        --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
        --query "changeableAttributes.${attribute}" -o tsv)"
    if [[ "${TAG_VALUE,,}" != "false" || "${MANIFEST_VALUE,,}" != "false" ]]; then
        echo "[FAIL] ${attribute} is still enabled after locking"
        exit 1
    fi
done

printf '%s\n' "$IMAGE_DIGEST" >"$BUILD_RECORD_DIR/image_digest.txt"
printf '%s\n' "$PROJECT_SHA" >"$BUILD_RECORD_DIR/project_sha.txt"
printf '%s\n' "$PROJECT_TREE" >"$BUILD_RECORD_DIR/project_tree.txt"
echo "[OK] image=${IMAGE_REPOSITORY}:${PROJECT_SHA}"
echo "[OK] digest=$IMAGE_DIGEST"
echo "[OK] Tag and manifest are locked against write and delete"
echo "[OK] The image is a build artifact only; it establishes nothing about the model"
