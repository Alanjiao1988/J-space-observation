#!/usr/bin/env bash
# Clone one or two exact commits from the uploaded one-file git bundle.
#
# A bundle is one file, so the Azure CLI packer never walks a repository tree
# and never meets the long native Windows path that stopped P0-R1. The clones
# are the only source the suite steps may read, so no byte of any local working
# tree can reach the run.
#
# The .git directory is deliberately KEPT: a large part of this repository's
# suite is governance that binds a commit, a tree or a file's committed bytes
# by shelling out to git. Removing .git turns those tests into collection
# errors that say nothing about the code under test.
#
# The binding file is written OUTSIDE both trees so neither checkout is dirty.
#
# This step performs no tokenizer, checkpoint, model, GPU, scoring or evidence
# operation.
set -euo pipefail

BASELINE="${1:?name the baseline commit}"
CORRECTED="${2:-}"

clone_at () {
  local sha="$1" dest="$2"
  mkdir -p "$dest"
  git clone -q /workspace/repo.bundle "$dest"
  cd "$dest"
  git checkout -q "$sha"
  if [ "$(git rev-parse HEAD)" != "$sha" ]; then
    echo "P0_R2_CHECKOUT_REFUSED=1 the checkout is not $sha" >&2; exit 2
  fi
  if [ "$(git status --porcelain | wc -l)" != "0" ]; then
    echo "P0_R2_CHECKOUT_REFUSED=1 checkout $sha is dirty" >&2; exit 2
  fi
  echo "CHECKOUT $dest COMMIT=$(git rev-parse HEAD) TREE=$(git rev-parse 'HEAD^{tree}') DIRTY=0"
}

clone_at "$BASELINE" /workspace/base
{
  echo "BASELINE=$BASELINE"
} > /workspace/P0_R2_BINDING

if [ -n "$CORRECTED" ]; then
  clone_at "$CORRECTED" /workspace/head
  echo "CORRECTED=$CORRECTED" >> /workspace/P0_R2_BINDING
fi

echo "P0_R2_CHECKOUT_COMPLETE=1"
