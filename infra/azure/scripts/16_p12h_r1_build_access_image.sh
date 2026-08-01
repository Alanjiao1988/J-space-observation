#!/usr/bin/env bash
# Script: 16_p12h_r1_build_access_image.sh
# Purpose: Build the Phase 1.2H-R1 byte-only access image with an ACR Task, from
#          a pinned commit, and report the resulting immutable digest.
#
# The build runs in ACR, not locally. The operator's machine cannot sustain a
# container build, and more importantly a cloud build from a pinned commit is
# the only build whose inputs a reviewer can reconstruct later.
#
# The image tag records the freeze commit. The digest is what actually gets
# deployed: tags are mutable, digests are not, and a receipt that cites a tag
# proves nothing about what ran.

set -euo pipefail

SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-943bacdf-8b6e-4e3a-8126-a149f623d32e}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
ACR_NAME="${ACR_NAME:-acrjspaceobssea0708231738}"
IMAGE_REPO="${IMAGE_REPO:-j-space-observation}"
DOCKERFILE="${DOCKERFILE:-Dockerfile.phase1-2h-r1-access}"
FREEZE_COMMIT="${FREEZE_COMMIT:-}"
GIT_REMOTE="${GIT_REMOTE:-https://github.com/Alanjiao1988/J-space-observation.git}"

log() { printf '[16_p12h_r1_build_access_image] %s\n' "$*"; }
fail() { printf '[16_p12h_r1_build_access_image] ERROR: %s\n' "$*" >&2; exit 1; }

command -v az >/dev/null 2>&1 || fail "az CLI not found"
[[ -n "${FREEZE_COMMIT}" ]] || fail "FREEZE_COMMIT is required (full 40-character SHA)"
[[ "${#FREEZE_COMMIT}" -eq 40 ]] || fail "FREEZE_COMMIT must be the full 40-character SHA, got ${#FREEZE_COMMIT} characters"

SHORT_SHA="${FREEZE_COMMIT:0:7}"
IMAGE_TAG="${IMAGE_REPO}:phase1-2h-r1-access-${SHORT_SHA}"

log "subscription:  ${SUBSCRIPTION_ID}"
log "registry:      ${ACR_NAME}"
log "freeze commit: ${FREEZE_COMMIT}"
log "image tag:     ${IMAGE_TAG}"

az account set --subscription "${SUBSCRIPTION_ID}"

# --- 1. Refuse to overwrite an existing tag --------------------------------
# An immutable tag is the only way a receipt's image reference stays meaningful.

if az acr repository show --name "${ACR_NAME}" --image "${IMAGE_TAG}" >/dev/null 2>&1; then
    fail "tag ${IMAGE_TAG} already exists. Refusing to overwrite: the receipt from the earlier build would silently start referring to different bytes."
fi

# --- 2. Build provenance ----------------------------------------------------
# The Dockerfile requires a 64-hex build-provenance value and fails the build
# without one. Bind it to the freeze commit so the label is meaningful.

BUILD_PROVENANCE_SHA256="$(printf '%s' "${FREEZE_COMMIT}" | sha256sum | cut -d' ' -f1)"
log "build provenance: ${BUILD_PROVENANCE_SHA256}"

# --- 3. Build in ACR from the pinned commit --------------------------------
# The remote build context is the public repository at the exact freeze commit.
# No local working tree participates, so an uncommitted local edit cannot reach
# the image.

log "starting ACR task build (this runs on ACR compute, not locally)"
# NOTE: --no-logs is a store_true switch. Passing it a value ("--no-logs false")
# makes the CLI treat the positional source location as an unrecognised
# argument and exit 2, so the build could never have run as first frozen.
# Independent Audit A raised this as A-05 and independent Audit B as B-05.
# Streaming logs is already the default; the switch is simply omitted.
az acr build \
    --registry "${ACR_NAME}" \
    --image "${IMAGE_TAG}" \
    --file "${DOCKERFILE}" \
    --build-arg "BUILD_PROVENANCE_SHA256=${BUILD_PROVENANCE_SHA256}" \
    --platform linux/amd64 \
    "${GIT_REMOTE}#${FREEZE_COMMIT}"

# --- 4. Resolve the immutable digest ---------------------------------------

DIGEST="$(az acr repository show \
    --name "${ACR_NAME}" \
    --image "${IMAGE_TAG}" \
    --query digest --output tsv)"

[[ -n "${DIGEST}" ]] || fail "could not resolve the image digest after build"

LOGIN_SERVER="$(az acr show --name "${ACR_NAME}" --query loginServer --output tsv)"

cat <<EOF

Phase 1.2H-R1 access image built.

  IMAGE_TAG    = ${LOGIN_SERVER}/${IMAGE_TAG}
  IMAGE_DIGEST = ${DIGEST}
  PINNED_IMAGE = ${LOGIN_SERVER}/${IMAGE_REPO}@${DIGEST}

Deploy by digest, never by tag. Record IMAGE_DIGEST in the execution ledger.

EOF
