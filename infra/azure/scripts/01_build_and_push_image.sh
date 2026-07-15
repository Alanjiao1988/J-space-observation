#!/usr/bin/env bash
# Script: 01_build_and_push_image.sh
# Purpose: Build the experiment image in Azure Container Registry.
# This script creates/uses Azure resources only when explicitly run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
VARS_FILE="$SCRIPT_DIR/../variables.env"

if [[ ! -f "$VARS_FILE" ]]; then
    echo "[FAIL] Missing $VARS_FILE"
    echo "Copy infra/azure/variables.example.env to infra/azure/variables.env and fill placeholders."
    exit 1
fi
source "$VARS_FILE"

if [[ -z "${AZURE_CONTAINER_REGISTRY:-}" ]]; then
    echo "[FAIL] AZURE_CONTAINER_REGISTRY is empty in variables.env"
    exit 1
fi
if [[ -z "${JSPACE_SEMANTIC_PROTOCOL_COMMIT:-}" ]]; then
    echo "[FAIL] JSPACE_SEMANTIC_PROTOCOL_COMMIT must be the explicit clean HEAD commit"
    exit 1
fi

ATTESTATION_PATH="$PROJECT_ROOT/.semantic_audit_build_provenance.json"
cleanup_attestation() {
    rm -f "$ATTESTATION_PATH"
}
trap cleanup_attestation EXIT

env -u PYTHONPATH python -I -S \
    "$PROJECT_ROOT/scripts/prepare_semantic_audit_build_context.py" \
    --project-root "$PROJECT_ROOT" \
    --protocol-commit "$JSPACE_SEMANTIC_PROTOCOL_COMMIT"

ACR_LOGIN_SERVER="${AZURE_CONTAINER_REGISTRY}.azurecr.io"
IMAGE_REF="${ACR_LOGIN_SERVER}/${AZURE_IMAGE_NAME}:${AZURE_IMAGE_TAG}"

echo "================================"
echo "Build and push image with ACR"
echo "================================"
echo "Resource group: ${AZURE_RESOURCE_GROUP}"
echo "Location: ${AZURE_LOCATION}"
echo "ACR: ${AZURE_CONTAINER_REGISTRY}"
echo "Image: ${IMAGE_REF}"
echo

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

if ! az group show --name "$AZURE_RESOURCE_GROUP" >/dev/null 2>&1; then
    echo "[CREATE] Resource group ${AZURE_RESOURCE_GROUP}"
    az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" -o table
fi

if ! az acr show --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_CONTAINER_REGISTRY" >/dev/null 2>&1; then
    echo "[CREATE] Azure Container Registry ${AZURE_CONTAINER_REGISTRY}"
    az acr create \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$AZURE_CONTAINER_REGISTRY" \
        --sku Basic \
        --location "$AZURE_LOCATION" \
        -o table
fi

echo "[RUN] az acr build"
az acr build \
    --registry "$AZURE_CONTAINER_REGISTRY" \
    --image "${AZURE_IMAGE_NAME}:${AZURE_IMAGE_TAG}" \
    "$PROJECT_ROOT"

LOG_FILE="$PROJECT_ROOT/docs/run_log.md"
{
    echo ""
    echo "## Azure image build - $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    echo "- Command: \`bash infra/azure/scripts/01_build_and_push_image.sh\`"
    echo "- Resource group: ${AZURE_RESOURCE_GROUP}"
    echo "- Registry: ${AZURE_CONTAINER_REGISTRY}"
    echo "- Image: ${IMAGE_REF}"
    echo "- Note: This command creates/uses Azure resources when explicitly run."
} >> "$LOG_FILE"

echo "================================"
echo "[OK] Image build submitted/completed"
echo "Image: ${IMAGE_REF}"
echo "================================"
