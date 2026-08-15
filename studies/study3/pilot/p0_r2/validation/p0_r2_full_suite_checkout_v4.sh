#!/usr/bin/env bash
# Clone the exact executable commit from an uploaded git bundle.
#
# A bundle is one file, so the Azure CLI packer never walks a repository tree
# and never meets the long Windows path that stopped P0-R1. The clone is the
# only source the suite step is allowed to read, so no byte of the local
# working tree can reach the run.
#
# The .git directory is deliberately KEPT. A large part of this repository's
# suite is governance: tests that bind a commit, a tree, or a file's committed
# bytes by shelling out to git. Deleting .git does not make those tests safer,
# it makes them error, which is how an earlier attempt produced 194 collection
# errors that said nothing about the code under test.
#
# This step performs no tokenizer, checkpoint, model or GPU operation.
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

cat > /workspace/P0_R2_BINDING <<EOF
COMMIT=$COMMIT
EOF

echo "P0_R2_CHECKOUT_COMPLETE=1"