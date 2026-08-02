#!/usr/bin/env bash
set -euo pipefail
COMMIT="$1"
SCRIPT="$2"
mkdir -p /tmp/src
git clone -q /workspace/repo.bundle /tmp/src
cd /tmp/src
git checkout -q "$COMMIT"
echo "BOUND_COMMIT=$(git rev-parse HEAD)"
echo "BOUND_TREE=$(git rev-parse HEAD^{tree})"
echo "DIRTY=$(git status --porcelain | wc -l)"
pip install -q -r requirements.lock.txt
echo "=== BEGIN SCRIPT OUTPUT ==="
python "$SCRIPT"
echo "=== END SCRIPT OUTPUT ==="
echo "REPO_SCRIPT_COMPLETE=1"