#!/usr/bin/env bash
# Build and lock the Phase 1.0D semantic-review v2 image.
#
#   ACR_NAME=<registry> ./22_build_phase1_0d_review_v2.sh
#
# This is a separate repository, Dockerfile and provenance record from both
# locked Phase 1.0D images.  The ACR QuickRun cannot produce an image unless the
# Dockerfile verifies the frozen generation bundle, the complete v1 review
# bundle, every section-8 v2 instrument binding and the absence of target
# output.  After the build, both the tag and manifest are locked against write
# and delete and re-read to prove the lock took effect.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
IMAGE_REPOSITORY="j-space-observation-phase1-0d-review-v2"
V1_REVIEW_REPOSITORY="j-space-observation-phase1-0d-review"
GENERATION_REPOSITORY="j-space-observation-phase1-0d"
DOCKERFILE="Dockerfile.phase1-0d-review-v2"
PROVENANCE="phase1_0d_review_v2_build_provenance.json"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
BUILD_RECORD_DIR="${REVIEW_V2_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase1-0d-review-v2-build-${PROJECT_SHA}}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] The v2 review build requires clean HEAD == PROJECT_SHA"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Refusing to build a dirty worktree under immutable tag $PROJECT_SHA"
    exit 1
fi
if [[ ! -f "$PROJECT_ROOT/$PROVENANCE" ]]; then
    echo "[FAIL] The committed v2 review build-provenance record is missing"
    exit 1
fi
if [[ "$IMAGE_REPOSITORY" == "$GENERATION_REPOSITORY" \
    || "$IMAGE_REPOSITORY" == "$V1_REVIEW_REPOSITORY" ]]; then
    echo "[FAIL] The v2 image may not share either locked image repository"
    exit 1
fi

# One immutable tag per build commit.  Rebuilding is refused rather than
# silently producing different bytes behind the same name.
if az acr repository show \
    --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --output none 2>/dev/null; then
    echo "[FAIL] ${IMAGE_REPOSITORY}:${PROJECT_SHA} already exists; use a new commit"
    exit 1
fi

mkdir -p "$BUILD_RECORD_DIR"

# `az acr build` submits an ACR Tasks QuickRun.  Its run id remains in ACR and
# the bounded console transcript is retained beside the local control record.
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
echo "[OK] The locked generation and v1 review images were neither rebuilt nor retagged"
echo "[OK] The image is a build artifact only; it establishes nothing about reviewer accuracy"
