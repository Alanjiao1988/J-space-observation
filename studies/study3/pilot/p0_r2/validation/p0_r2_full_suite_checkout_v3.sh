#!/usr/bin/env bash
# Clone two exact commits from the uploaded one-file git bundle: the unmodified
# baseline this work started from, and the executable commit under test.
#
# Both are needed because the only honest way to say "this change introduced no
# new failure" is to run the same suite, in the same container, in the same
# dependency closure, against both commits and compare the two outcome sets.
#
# The binding files are written OUTSIDE the trees so neither checkout is dirty.
set -euo pipefail

BASELINE="$1"
COMMIT="$2"

clone_at () {
  local sha="$1" dest="$2"
  mkdir -p "$dest"
  git clone -q /workspace/repo.bundle "$dest"
  cd "$dest"
  git checkout -q "$sha"
  if [ "$(git rev-parse HEAD)" != "$sha" ]; then
    echo "FAIL: checkout is not $sha" >&2; exit 2
  fi
  if [ "$(git status --porcelain | wc -l)" != "0" ]; then
    echo "FAIL: checkout $sha is dirty" >&2; exit 2
  fi
  echo "CHECKOUT $dest COMMIT=$(git rev-parse HEAD) TREE=$(git rev-parse 'HEAD^{tree}') DIRTY=0"
}

clone_at "$BASELINE" /workspace/base
clone_at "$COMMIT"   /workspace/src

cat > /workspace/P0_R2_BINDING <<EOF
BASELINE=$BASELINE
COMMIT=$COMMIT
EOF

echo "P0_R2_CHECKOUT_COMPLETE=1"