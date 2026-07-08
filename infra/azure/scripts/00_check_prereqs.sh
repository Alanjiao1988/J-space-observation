#!/usr/bin/env bash
# Script: 00_check_prereqs.sh
# Purpose: Azure-first readiness check. This script does not create resources.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

echo "================================"
echo "Azure readiness check"
echo "================================"
echo

if ! command -v az >/dev/null 2>&1; then
    echo "[FAIL] Azure CLI is not installed or not on PATH."
    echo "Install Azure CLI, then run: az login"
    exit 1
fi

echo "[OK] Azure CLI found"
az version --query '"azure-cli"' -o tsv
echo

echo "Checking Azure login..."
if ! az account show >/dev/null 2>&1; then
    echo "[FAIL] Azure CLI is not logged in."
    echo "Run: az login"
    exit 1
fi

SUBSCRIPTION_NAME="$(az account show --query name -o tsv)"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
SUBSCRIPTION_STATE="$(az account show --query state -o tsv)"
echo "[OK] Logged in"
echo "Subscription name: ${SUBSCRIPTION_NAME}"
echo "Subscription id: ${SUBSCRIPTION_ID}"
echo "Subscription state: ${SUBSCRIPTION_STATE}"
echo

echo "Checking provider registrations..."
APP_STATE="$(az provider show -n Microsoft.App --query registrationState -o tsv)"
ACR_STATE="$(az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv)"
echo "Microsoft.App: ${APP_STATE}"
echo "Microsoft.ContainerRegistry: ${ACR_STATE}"
if [[ "$APP_STATE" != "Registered" ]]; then
    echo "[FAIL] Microsoft.App is not Registered. Do not create Container Apps resources yet."
    exit 1
fi
if [[ "$ACR_STATE" != "Registered" ]]; then
    echo "[FAIL] Microsoft.ContainerRegistry is not Registered. Do not create ACR resources yet."
    exit 1
fi
echo

echo "Checking Container Apps extension..."
if az extension show --name containerapp >/dev/null 2>&1; then
    CONTAINERAPP_VERSION="$(az extension show --name containerapp --query version -o tsv)"
    echo "[OK] containerapp extension installed: ${CONTAINERAPP_VERSION}"
else
    echo "[FAIL] containerapp extension is not installed."
    echo "Run: az extension add --name containerapp --upgrade"
    exit 1
fi
echo

echo "GPU quota check instructions:"
echo "1. Confirm region and workload profile from infra/azure/variables.env."
echo "2. In Azure Portal: Subscription -> Usage + quotas -> filter by provider Microsoft.App and region."
echo "3. Verify quota for Container Apps GPU T4 workload profile, e.g. Consumption-GPU-NC8as-T4."
echo "4. If quota is missing or zero, stop and request quota before running jobs."
echo "5. Do not fall back to local model inference."
echo

echo "No Azure resources were created by this readiness check."

LOG_FILE="$PROJECT_ROOT/docs/run_log.md"
if [[ -f "$LOG_FILE" ]]; then
    {
        echo ""
        echo "## Azure readiness script check - $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        echo ""
        echo "- Command: \`bash infra/azure/scripts/00_check_prereqs.sh\`"
        echo "- Subscription: ${SUBSCRIPTION_NAME} (${SUBSCRIPTION_ID})"
        echo "- Microsoft.App registration: ${APP_STATE}"
        echo "- Microsoft.ContainerRegistry registration: ${ACR_STATE}"
        echo "- containerapp extension: installed (${CONTAINERAPP_VERSION})"
        echo "- Azure resources created: none"
    } >> "$LOG_FILE"
fi

echo "================================"
echo "[OK] Azure readiness check completed"
echo "================================"
