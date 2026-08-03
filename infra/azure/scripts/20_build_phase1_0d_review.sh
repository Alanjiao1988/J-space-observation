#!/usr/bin/env bash
# Build and lock the Phase 1.0D semantic-review image.
#
#   ACR_NAME=<registry> ./20_build_phase1_0d_review.sh
#
# The build is the verification. Dockerfile.phase1-0d-review runs the frozen
# `verify-runtime`, `verify-image-context` and `verify-protocol` over the frozen
# science bytes, then the sibling review tool's `verify-image-context` and
# `verify-addendum`. The image cannot be produced unless the pins match, the
# baked frozen bytes are identical to the locked generation image's recorded
# bundle, the protocol reproduces its frozen sha256, the review bundle matches
# its own record, and the addendum and rubric hash to the committed values.
#
# The locked target-generation image is never rebuilt or retagged here. This is
# a different repository, a different Dockerfile and a different provenance
# record.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
IMAGE_REPOSITORY="j-space-observation-phase1-0d-review"
GENERATION_REPOSITORY="j-space-observation-phase1-0d"
DOCKERFILE="Dockerfile.phase1-0d-review"
PROVENANCE="phase1_0d_review_build_provenance.json"
PROJECT_SHA="${PROJECT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD)}"
BUILD_RECORD_DIR="${REVIEW_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/phase1-0d-review-build-${PROJECT_SHA}}"

if [[ ! "$PROJECT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[FAIL] PROJECT_SHA must be a full 40-character commit"
    exit 1
fi
if [[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$PROJECT_SHA" ]]; then
    echo "[FAIL] The review build requires clean HEAD == PROJECT_SHA"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet; then
    echo "[FAIL] Refusing to build a dirty worktree under immutable tag $PROJECT_SHA"
    exit 1
fi
if [[ ! -f "$PROJECT_ROOT/$PROVENANCE" ]]; then
    echo "[FAIL] The committed review build-provenance record is missing"
    exit 1
fi
if [[ "$IMAGE_REPOSITORY" == "$GENERATION_REPOSITORY" ]]; then
    echo "[FAIL] The review image may not share the locked generation repository"
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
echo "[OK] The locked generation image was neither rebuilt nor retagged"
echo "[OK] The image is a build artifact only; it establishes nothing about reviewer accuracy"
