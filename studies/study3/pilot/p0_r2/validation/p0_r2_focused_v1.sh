#!/usr/bin/env bash
# Run the P0-R2 generation-1 execution closure suite against a fresh
# exact-commit Linux checkout, on CPU-only ACR compute, in the dependency
# closure the repository registers in requirements.lock.txt.
#
# This is the direct analogue of the focused run P0-R1 recorded as cmh8.
#
# It performs no tokenizer construction, no checkpoint download, no model weight
# load, no prefill, no generation and no GPU operation. It never runs the replay
# gate and never touches the one-shot envelope.
set -euo pipefail

cd /workspace/src
echo "P0_R2_FOCUSED_STAGE=STUDY3-P0-R2"
echo "GIT=$(git --version)"
echo "BOUND_COMMIT=$(git rev-parse HEAD)"
echo "BOUND_TREE=$(git rev-parse 'HEAD^{tree}')"
echo "DIRTY=$(git status --porcelain | wc -l)"
python3 -c 'import sys; print("PYVER=" + sys.version.split()[0])'

echo "REQUIREMENTS_LOCK_SHA256=$(sha256sum requirements.lock.txt | cut -d' ' -f1)"
python3 -m pip install --quiet --no-cache-dir --only-binary=:all: \
    -r requirements.lock.txt
echo "P0_R2_REGISTERED_CLOSURE_INSTALLED=1"

export CUDA_VISIBLE_DEVICES=""
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONDONTWRITEBYTECODE=1

set +e
python3 -m pytest tests/test_study3_p0_r2_execution_closure.py \
    -q -p no:cacheprovider --color=no -rfE > /workspace/focused.out 2>&1
STATUS=$?
set -e

grep -E '^(FAILED|ERROR) ' /workspace/focused.out || echo "(no FAILED or ERROR lines)"
tail -n 3 /workspace/focused.out
echo "P0_R2_FOCUSED_PYTEST_STATUS=${STATUS}"
echo "P0_R2_FOCUSED_COMPLETE=1"
echo "P0_R2_REPLAY_GATE_RUN=false"
echo "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"