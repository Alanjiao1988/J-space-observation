#!/bin/bash
# Script: 03_run_phase1.sh
# Purpose: Submit Phase 1 job to Azure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

echo "================================"
echo "Phase 1: Behavioral Depth Gradient"
echo "================================"
echo

# Source variables
source "$SCRIPT_DIR/../variables.env"

JOB_NAME="phase1-$(date +%s)"
COMMAND="python experiments/phase1_depth_gradient.py --task-families $PHASE1_TASK_FAMILIES --depths $PHASE1_DEPTHS --items-per-cell 3"

echo "Job: $JOB_NAME"
echo "Command: $COMMAND"
echo

# Create container instance
echo "Submitting job to Azure..."
az container create \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --name "$JOB_NAME" \
    --image "$FULL_IMAGE" \
    --command-line "$COMMAND" \
    --cpu 4 \
    --memory 16 \
    --restart-policy Never

echo "✓ Job submitted: $JOB_NAME"
echo

# Monitor job
echo "Monitoring job..."
sleep 5
az container show \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --name "$JOB_NAME" \
    --query "containers[0].instanceView.currentState"

echo

# Log to run log
LOG_FILE="$PROJECT_ROOT/docs/run_log.md"
mkdir -p "$(dirname "$LOG_FILE")"
echo "" >> "$LOG_FILE"
echo "## Phase 1 Submission - $(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$LOG_FILE"
echo "**Status**: Submitted to Azure" >> "$LOG_FILE"
echo "**Job**: $JOB_NAME" >> "$LOG_FILE"
echo "**Command**: \`$COMMAND\`" >> "$LOG_FILE"
echo "**Check logs**: \`az container logs --name $JOB_NAME -g $AZURE_RESOURCE_GROUP\`" >> "$LOG_FILE"

echo "================================"
echo "✓ Phase 1 submitted"
echo "Check status with:"
echo "  az container show --name $JOB_NAME -g $AZURE_RESOURCE_GROUP"
echo "View logs with:"
echo "  az container logs --name $JOB_NAME -g $AZURE_RESOURCE_GROUP"
echo "================================"
