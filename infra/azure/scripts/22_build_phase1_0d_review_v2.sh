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
BLOB_ACCOUNT="stjspacefiles0709085305"
BLOB_CONTAINER="jspace-results"
BUILD_LOCK_PREFIX="phase1-0d-semantic-review-v2/build-locks"
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
if [[ -n "$(git -C "$PROJECT_ROOT" status --porcelain --untracked-files=all)" ]]; then
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

# Atomically claim this immutable build commit in public Blob using Entra login.
# A concurrent launcher can no longer pass a read-before-write tag check and
# race us to the same ACR tag.  The lock is intentionally retained.
BUILD_LOCK_FILE="$BUILD_RECORD_DIR/build_lock.json"
printf '{"artifact":"phase1_0d_review_v2_build_lock","project_sha":"%s"}\n' \
    "$PROJECT_SHA" >"$BUILD_LOCK_FILE"
az storage blob upload \
    --auth-mode login \
    --account-name "$BLOB_ACCOUNT" \
    --container-name "$BLOB_CONTAINER" \
    --name "${BUILD_LOCK_PREFIX}/${PROJECT_SHA}.json" \
    --file "$BUILD_LOCK_FILE" \
    --overwrite false \
    --only-show-errors \
    --output none

# Submit exactly the committed tree, never the mutable working directory.  In
# particular, an ignored or untracked Python file cannot be copied broadly by
# the Dockerfile while the image is labelled with PROJECT_SHA.
BUILD_CONTEXT="$(mktemp -d "$BUILD_RECORD_DIR/committed-context.XXXXXX")"
cleanup() {
    if [[ -n "${BUILD_CONTEXT:-}" \
        && "$BUILD_CONTEXT" == "$BUILD_RECORD_DIR"/committed-context.* \
        && -d "$BUILD_CONTEXT" ]]; then
        rm -rf -- "$BUILD_CONTEXT"
    fi
}
trap cleanup EXIT
git -C "$PROJECT_ROOT" archive --format=tar "$PROJECT_SHA" \
    | tar -xf - -C "$BUILD_CONTEXT"

# `az acr build` submits an ACR Tasks QuickRun.  Its run id remains in ACR and
# the bounded console transcript is retained beside the local control record.
az acr build \
    --registry "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${PROJECT_SHA}" \
    --file "$DOCKERFILE" \
    --platform linux/amd64 \
    "$BUILD_CONTEXT" \
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

LOCKED_TAG_DIGEST="$(az acr repository show-manifests \
    --name "$ACR_NAME" \
    --repository "$IMAGE_REPOSITORY" \
    --query "[?tags[?@=='${PROJECT_SHA}']].digest | [0]" \
    -o tsv)"
if [[ "$LOCKED_TAG_DIGEST" != "$IMAGE_DIGEST" ]]; then
    echo "[FAIL] The locked tag no longer resolves to the digest this run built"
    exit 1
fi

printf '%s\n' "$IMAGE_DIGEST" >"$BUILD_RECORD_DIR/image_digest.txt"
printf '%s\n' "$PROJECT_SHA" >"$BUILD_RECORD_DIR/project_sha.txt"
echo "[OK] image=${IMAGE_REPOSITORY}:${PROJECT_SHA}"
echo "[OK] digest=$IMAGE_DIGEST"
echo "[OK] Tag and manifest are locked against write and delete"
echo "[OK] The locked generation and v1 review images were neither rebuilt nor retagged"
echo "[OK] The image is a build artifact only; it establishes nothing about reviewer accuracy"
