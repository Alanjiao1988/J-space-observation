#!/usr/bin/env bash
# Stage P0-T checkout step for the registered Azure container route.
#
# Authority: studies/study3/prompts/study3_p0_feasibility_pilot_authority.md
# section 7.
#
# This step owns the clone. It runs in a git-bearing image, clones the exact
# published commit from the uploaded bundle, and records the binding it observed
# so the science step can assert it without needing git.
#
# It performs no tokenizer, model, GPU, scoring or generation operation.

set -euo pipefail

COMMIT="$1"

rm -rf /workspace/src
git clone -q /workspace/repo.bundle /workspace/src
cd /workspace/src
git checkout -q "$COMMIT"

BOUND_COMMIT="$(git rev-parse HEAD)"
BOUND_TREE="$(git rev-parse "HEAD^{tree}")"
BOUND_DIRTY="$(git status --porcelain | wc -l | tr -d ' ')"

if [[ "$BOUND_COMMIT" != "$COMMIT" ]]; then
    echo "[FAIL] checkout resolved to ${BOUND_COMMIT}, not ${COMMIT}"
    exit 1
fi
if [[ "$BOUND_DIRTY" != "0" ]]; then
    echo "[FAIL] the checkout is not clean"
    exit 1
fi

printf '%s' "$BOUND_COMMIT" > /workspace/BOUND_COMMIT
printf '%s' "$BOUND_TREE" > /workspace/BOUND_TREE
printf '%s' "$BOUND_DIRTY" > /workspace/BOUND_DIRTY

echo "CHECKOUT_COMMIT=${BOUND_COMMIT}"
echo "CHECKOUT_TREE=${BOUND_TREE}"
echo "CHECKOUT_DIRTY=${BOUND_DIRTY}"
echo "CHECKOUT_COMPLETE=1"
