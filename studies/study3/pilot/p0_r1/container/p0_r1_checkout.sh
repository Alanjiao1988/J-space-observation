#!/usr/bin/env bash
# Stage P0-R1 checkout step for the registered container route.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md
#
# The P0-R1 science image carries no git, which is correct for a science image.
# A dedicated git-bearing step therefore owns the clone and records the binding
# it observed; the science step asserts that binding and re-proves it from
# content. This mirrors the route the consumed P0-T round validated.
#
# It clones the exact published commit from an uploaded bundle, so no local
# working tree can leak into the run. It performs no tokenizer, checkpoint,
# model or GPU operation.
set -euo pipefail

COMMIT="$1"
DEST="${DEST:-/workspace/src}"

mkdir -p "$DEST"
git clone -q /workspace/repo.bundle "$DEST"
cd "$DEST"
git checkout -q "$COMMIT"

echo "BOUND_COMMIT=$(git rev-parse HEAD)"
echo "BOUND_TREE=$(git rev-parse 'HEAD^{tree}')"
echo "DIRTY=$(git status --porcelain | wc -l)"

if [ "$(git rev-parse HEAD)" != "$COMMIT" ]; then
  echo "FAIL: the checkout is not the requested commit" >&2
  exit 2
fi
if [ "$(git status --porcelain | wc -l)" != "0" ]; then
  echo "FAIL: the checkout is dirty" >&2
  exit 2
fi

# Strip the .git directory so the science step cannot mutate the lineage, while
# leaving a plain-text record of the binding it must assert.
cat > "$DEST/P0_R1_BINDING" <<EOF
COMMIT=$COMMIT
TREE=$(git rev-parse 'HEAD^{tree}')
EOF

echo "P0_R1_CHECKOUT_COMPLETE=1"
