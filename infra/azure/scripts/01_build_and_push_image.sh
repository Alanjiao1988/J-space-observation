#!/bin/bash
# Script: 01_build_and_push_image.sh
# Purpose: Build Docker image and push to Azure Container Registry

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

echo "================================"
echo "Building and Pushing Image"
echo "================================"
echo

# Source variables
source "$SCRIPT_DIR/../variables.env"

# Create ACR if it doesn't exist
echo "Checking ACR..."
if ! az acr show --resource-group "$AZURE_RESOURCE_GROUP" --name "$ACR_NAME" &> /dev/null; then
    echo "Creating ACR: $ACR_NAME"
    az acr create \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$ACR_NAME" \
        --sku Basic
    echo "✓ ACR created"
else
    echo "✓ ACR exists"
fi
echo

# Authenticate Docker with ACR
echo "Authenticating Docker with ACR..."
az acr login --name "$ACR_NAME"
echo "✓ Docker authenticated"
echo

# Build image
echo "Building Docker image..."
echo "Tag: $FULL_IMAGE"
docker build -t "$FULL_IMAGE" "$PROJECT_ROOT"
echo "✓ Image built"
echo

# Push image
echo "Pushing image to ACR..."
docker push "$FULL_IMAGE"
echo "✓ Image pushed"
echo

# Log to run log
LOG_FILE="$PROJECT_ROOT/docs/run_log.md"
mkdir -p "$(dirname "$LOG_FILE")"
echo "" >> "$LOG_FILE"
echo "## Docker Build - $(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$LOG_FILE"
echo "**Command**: \`docker build -t $FULL_IMAGE $PROJECT_ROOT && docker push $FULL_IMAGE\`" >> "$LOG_FILE"
echo "**Status**: ✓ Image built and pushed" >> "$LOG_FILE"
echo "**Image**: $FULL_IMAGE" >> "$LOG_FILE"

echo "================================"
echo "✓ Build and push complete"
echo "================================"
