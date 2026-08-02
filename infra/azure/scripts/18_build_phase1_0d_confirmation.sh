#!/usr/bin/env bash
# Build and lock the Phase 1.0D headroom-confirmation image.
#
# This is the exact path that produced the recorded image, not an idealised one:
#
#   ACR_NAME=<registry> ./18_build_phase1_0d_confirmation.sh
#
# The build itself is the verification. Dockerfile.phase1-0d runs
# `verify-runtime`, `verify-image-context` and `verify-protocol`, so the image
# cannot be produced unless every pin matches the lock, the baked bytes hash to
# the committed bundle digest, and the image reproduces the frozen Phase 1.0D
# protocol_sha256 including its 300-item selection. A green build is the
# evidence; there is no separate attestation to trust.
#
# Phase 1.0C's image, provenance generator and artifact namespace are untouched.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
IMAGE_REPOSITORY="j-space-observation-phase1-0d"
DOCKERFILE="Dockerfile.phase1-0d"
PROVENANCE="phase1_0d_build_provenance.json"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
BUILD_RECORD_DIR="${CONFIRMATION_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase1-0d-build-${PROJECT_SHA}}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] The Phase 1.0D build requires clean HEAD == PROJECT_SHA"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Refusing to build a dirty worktree under immutable tag $PROJECT_SHA"
    exit 1
fi
if [[ ! -f "$PROJECT_ROOT/$PROVENANCE" ]]; then
    echo "[FAIL] The committed build-provenance record is missing"
    exit 1
fi

# One immutable tag per commit. Rebuilding the same commit is refused rather
# than silently producing a second image behind the same name.
if az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --output none 2>/dev/null; then
    echo "[FAIL] ${IMAGE_REPOSITORY}:${PROJECT_SHA} already exists; use a new commit"
    exit 1
fi

mkdir -p "$BUILD_RECORD_DIR"

az acr build \
    --registry "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --file "$DOCKERFILE" \
    --platform linux/amd64 \
    "$PROJECT_ROOT" \
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

# Lock tag and manifest. The run launcher refuses to start unless all four
# attributes are false, so an image whose bytes could still change can never
# become the provenance of a scientific result.
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
echo "[OK] image=${IMAGE_REPOSITORY}:${PROJECT_SHA}"
echo "[OK] digest=$IMAGE_DIGEST"
echo "[OK] Tag and manifest are locked against write and delete"
echo "[OK] The image is a build artifact only; it establishes nothing about the model"
