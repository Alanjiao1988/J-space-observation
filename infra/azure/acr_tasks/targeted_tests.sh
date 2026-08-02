#!/usr/bin/env bash
# Targeted test runner for ACR Tasks.
#
# This file is not run from a repository checkout. It is uploaded as a
# standalone source context together with a `repo.bundle` produced by
# `git bundle create repo.bundle HEAD`, so the build agent clones the exact
# commit itself and no local working tree can leak into the run.
#
#   az acr run --registry <registry> --platform linux/amd64 \
#     -f targeted_tests.yaml --set COMMIT=<sha> --set TESTS=<paths> <context-dir>
#
# The checkout goes to /tmp/src, not /workspace: a Phase 0.5 saturation
# self-test asserts the string "workspace" never appears in an artifact path.
set -euo pipefail
COMMIT="$1"
TESTS="$2"
mkdir -p /tmp/src
git clone -q /workspace/repo.bundle /tmp/src
cd /tmp/src
git checkout -q "$COMMIT"
echo "BOUND_COMMIT=$(git rev-parse HEAD)"
echo "BOUND_TREE=$(git rev-parse HEAD^{tree})"
echo "DIRTY=$(git status --porcelain | wc -l)"
python -V
pip install -q -r requirements.lock.txt
echo "=== TARGETED TESTS ==="
python -m pytest $TESTS -q --no-header -p no:cacheprovider
echo "TARGETED_TESTS_COMPLETE=1"
