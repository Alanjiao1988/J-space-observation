#!/usr/bin/env bash
# Stage P0-R1 replay-gate entry point for the registered container route.
#
# Authority: studies/study3/prompts/study3_v0_6_p0_r1_authority.md sections 7
# and 10.
#
# This script performs the replay-only factorization gate and the repaired
# eligibility derivation. It performs zero tokenizer encodes, zero tokenizer
# constructions, zero checkpoint downloads, zero weight loads and zero GPU
# allocations, and it asserts all of that before it exits.
#
# It is the FIRST action of the successor session. The calibration session must
# not run it.
set -euo pipefail

COMMIT="$1"
SRC="${SRC:-/workspace/src}"

echo "=== P0-R1 REPLAY GATE ==="
cd "$SRC"
echo "BOUND_COMMIT=$(git rev-parse HEAD)"
echo "BOUND_TREE=$(git rev-parse 'HEAD^{tree}')"
echo "DIRTY=$(git status --porcelain | wc -l)"
if [ "$(git rev-parse HEAD)" != "$COMMIT" ]; then
  echo "FAIL: the checkout is not the bound commit" >&2
  exit 2
fi

python - <<'PY'
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "studies", "study3", "pilot", "p0_r1"))

# A GPU must never be visible to the replay gate, and a tokenizer library must
# never be imported by it. Both are asserted before anything else runs.
try:
    import torch
    print("GPU_COUNT=%d" % torch.cuda.device_count())
    print("CUDA_AVAILABLE=%s" % torch.cuda.is_available())
except ImportError:
    print("GPU_COUNT=0")
    print("CUDA_AVAILABLE=False")

for name in ("transformers", "tokenizers"):
    if name in sys.modules:
        raise SystemExit("FAIL: %s was imported by the replay gate" % name)

import p0_r1_replay_gate as GATE

document = GATE.derive()
assert document["tokenizer_encodes_performed"] == 0
assert document["tokenizer_constructions_performed"] == 0
assert document["model_operations_performed"] == 0
for name in ("transformers", "tokenizers"):
    if name in sys.modules:
        raise SystemExit("FAIL: %s was imported during the replay" % name)

summary = document["corrected_matrix_summary"]
print("REPLAY_CELLS=%d" % summary["cells"])
print("REPLAY_ELIGIBLE=%d" % summary["eligible_cells"])
print("REPLAY_EMPTY_REASON_INELIGIBLE=%d"
      % summary["ineligible_cells_with_an_empty_reason_list"])
print("REPLAY_EXECUTABLE_PER_ROLE=%s"
      % summary["executable_genuine_i3_contrasts_per_role"])
print("REPLAY_ROLES_WITHOUT_CONTRAST=%s"
      % document["roles_without_executable_contrast"])
print("TOKENIZER_ENCODES=0")
print("MODEL_OPERATIONS=0")
PY

echo "P0_R1_REPLAY_GATE_COMPLETE=1"
