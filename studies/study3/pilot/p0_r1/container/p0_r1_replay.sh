#!/usr/bin/env bash
# Stage P0-R1 replay-gate entry point for the registered container route.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md
#   section 5, over studies/study3/prompts/study3_v0_6_p0_r1_authority.md.
#
# This script runs the REGISTERED LIVE REPLAY GATE. It calls
# p0_r1_replay_gate.py --gate with explicit successor-mode authorization and a
# writable runtime result directory. It deliberately does NOT call derive():
# derive() is the calibration derivation, it advances no state and writes no
# receipt, so treating its successful exit as a replay-gate pass would be
# invalid.
#
# The gate performs zero tokenizer constructions, zero encodes, zero checkpoint
# downloads, zero weight loads and zero GPU operations, and this script asserts
# all of that before and after it runs.
#
# It is the FIRST action of the successor execution session.
set -euo pipefail

COMMIT="$1"
IMAGE_DIGEST="${2:-}"
SRC="${SRC:-/workspace/src}"
OUT_DIR="${RESULTS_DIR:-/workspace/runtime/results}"

echo "=== P0-R1 REPLAY GATE ==="
cd "$SRC"

if [ -f "$SRC/P0_R1_BINDING" ]; then
  # shellcheck disable=SC1090
  . "$SRC/P0_R1_BINDING"
  echo "BOUND_COMMIT=$COMMIT"
  echo "BOUND_TREE=$TREE"
else
  echo "FAIL: the checkout recorded no binding" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
if [ ! -w "$OUT_DIR" ]; then
  echo "FAIL: $OUT_DIR is not writable; /workspace/studies is read-only" >&2
  exit 2
fi

python - <<'PY'
import sys
try:
    import torch
    count = torch.cuda.device_count()
    available = torch.cuda.is_available()
except ImportError:
    count, available = 0, False
print("GPU_COUNT=%d" % count)
print("CUDA_AVAILABLE=%s" % available)
if count or available:
    raise SystemExit("FAIL: a GPU is visible to the replay gate")
for name in ("transformers", "tokenizers"):
    if name in sys.modules:
        raise SystemExit("FAIL: %s was imported before the replay gate" % name)
PY

set +e
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_replay_gate.py" \
  --gate \
  --successor-authorization "p0-r1-successor-session" \
  --image-digest "$IMAGE_DIGEST" \
  --out-dir "$OUT_DIR"
GATE_EXIT=$?
set -e

# The result and receipt bytes are written by the gate before it returns, on
# both the pass and the failure path. A non-zero gate exit is preserved only
# after those bytes exist, so a stop is never lost.
for artifact in p0_r1_replay_result.json p0_r1_replay_receipt.json \
                p0_r1_replay_counters.json P0_R1_REPLAY_DISPOSITION.md; do
  if [ ! -s "$OUT_DIR/$artifact" ]; then
    echo "FAIL: the replay gate did not write $artifact" >&2
    exit 2
  fi
  echo "ARTIFACT=$artifact SHA256=$(sha256sum "$OUT_DIR/$artifact" | cut -d' ' -f1) BYTES=$(stat -c%s "$OUT_DIR/$artifact")"
done

python - "$OUT_DIR" <<'PY'
import json
import sys

out_dir = sys.argv[1]
with open("%s/p0_r1_replay_receipt.json" % out_dir, "rb") as handle:
    receipt = json.loads(handle.read().decode("utf-8"))
for field in ("tokenizer_encodes", "tokenizer_constructions",
              "checkpoint_downloads", "model_weight_loads",
              "model_operations_performed"):
    if receipt.get(field):
        raise SystemExit("FAIL: the replay receipt records %s=%r"
                         % (field, receipt[field]))
if receipt.get("gpu_allocated"):
    raise SystemExit("FAIL: the replay receipt records a GPU allocation")
print("REPLAY_STATE=%s" % receipt["state"])
print("REPLAY_PASSED=%s" % receipt["passed"])
print("REPLAY_ATTEMPT_ID=%s" % receipt["attempt_id"])
print("AUTHORIZES_MODEL_PILOT=%s" % receipt["authorizes_model_pilot"])
PY

echo "TOKENIZER_ENCODES=0"
echo "MODEL_OPERATIONS=0"
echo "P0_R1_REPLAY_GATE_COMPLETE=1"
exit "$GATE_EXIT"
