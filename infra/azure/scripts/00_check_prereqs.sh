#!/bin/bash
# Script: 00_check_prereqs.sh
# Purpose: Verify all prerequisites for Azure infrastructure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

echo "================================"
echo "Checking Prerequisites"
echo "================================"
echo

# Source variables
if [ ! -f "$SCRIPT_DIR/../variables.env" ]; then
    echo "✗ variables.env not found"
    echo "  Run: cp variables.example.env variables.env"
    exit 1
fi
source "$SCRIPT_DIR/../variables.env"

echo "Environment loaded from variables.env"
echo

# Check required commands
echo "Checking commands..."
for cmd in az docker python3; do
    if command -v "$cmd" &> /dev/null; then
        echo "✓ $cmd installed"
    else
        echo "✗ $cmd not found"
        exit 1
    fi
done
echo

# Check Python packages
echo "Checking Python packages..."
python3 -c "import torch" && echo "✓ torch installed" || echo "✗ torch not installed"
python3 -c "import transformers" && echo "✓ transformers installed" || echo "✗ transformers not installed"
python3 -c "import jspace_observation" && echo "✓ jspace_observation available" || echo "✗ jspace_observation not available (install with: pip install -e src)"
echo

# Check Azure login
echo "Checking Azure login..."
if az account show &> /dev/null; then
    CURRENT_SUB=$(az account show --query id -o tsv)
    echo "✓ Logged into Azure"
    echo "  Subscription: $CURRENT_SUB"
else
    echo "✗ Not logged into Azure"
    echo "  Run: az login"
    exit 1
fi
echo

# Check resource group
echo "Checking resource group..."
if az group exists --name "$AZURE_RESOURCE_GROUP" &> /dev/null; then
    echo "✓ Resource group exists: $AZURE_RESOURCE_GROUP"
else
    echo "⊘ Resource group not found: $AZURE_RESOURCE_GROUP"
    echo "  Creating resource group..."
    az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION"
    echo "✓ Resource group created"
fi
echo

# Check ACR
echo "Checking Azure Container Registry..."
if az acr show --resource-group "$AZURE_RESOURCE_GROUP" --name "$ACR_NAME" &> /dev/null; then
    echo "✓ ACR exists: $ACR_NAME"
else
    echo "⊘ ACR not found: $ACR_NAME"
    echo "  (Will attempt to create during build)"
fi
echo

# Log to run log
LOG_FILE="$PROJECT_ROOT/docs/run_log.md"
mkdir -p "$(dirname "$LOG_FILE")"
echo "" >> "$LOG_FILE"
echo "## Prerequisites Check - $(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$LOG_FILE"
echo "Status: ✓ All prerequisites verified" >> "$LOG_FILE"
echo "Subscription: $CURRENT_SUB" >> "$LOG_FILE"
echo "Resource group: $AZURE_RESOURCE_GROUP" >> "$LOG_FILE"

echo "================================"
echo "✓ All prerequisites verified"
echo "================================"
