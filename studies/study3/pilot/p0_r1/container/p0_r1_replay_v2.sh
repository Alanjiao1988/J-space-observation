#!/usr/bin/env bash
# Stage P0-R1 generation-2 replay-gate entry point.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md
#   sections 5 and 6, over the two prior P0-R1 authorities.
#
# Installed at /usr/local/bin/p0_r1_replay_v2.sh, an absolute path inside the
# image. Generation 1's equivalent lived at /workspace/p0_r1_replay.sh, which is
# not a path in the image, and defaulted SRC to /workspace/src, which exists only
# under an ACR context mount. Neither assumption is made here.
#
# This runs the REGISTERED LIVE REPLAY GATE. It deliberately does not call
# derive(): derive() advances no state and writes no receipt, so treating its
# exit as a gate pass would be invalid.
#
# The gate performs zero tokenizer constructions, zero encodes, zero checkpoint
# downloads, zero weight loads and zero GPU operations, and this script asserts
# that before and after.
#
# It emits the complete artifact bytes over the verified transport, and it
# authorizes the model pilot only after the transport has been verified. A
# truncated log can no longer be mistaken for a result.
set -euo pipefail

IMAGE_DIGEST="${1:-${P0_R1_IMAGE_DIGEST:-}}"
READY_COMMIT="${2:-${P0_R1_READY_COMMIT:-}}"
SRC="${P0_R1_SRC:-/opt/jspace/src}"
OUT_DIR="${RESULTS_DIR:-/workspace/runtime/results}"

echo "=== P0-R1 REPLAY GATE (generation 2) ==="
echo "SRC=$SRC"
echo "OUT_DIR=$OUT_DIR"

# The image must be able to invoke its own job command before anything runs.
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py" \
  --verify-layout --src "$SRC"

if [ -z "$IMAGE_DIGEST" ]; then
  echo "FAIL: the replay gate requires the immutable image digest it runs as" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
if [ ! -w "$OUT_DIR" ]; then
  echo "FAIL: $OUT_DIR is not writable; the image source root is read-only" >&2
  exit 2
fi

python "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_no_accelerator_probe.py"

# The generation-2 lock is injected, never baked: the image is built before the
# lock exists, so an image that carried it would be outcome-conditioned.
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py" \
  --reconstruct --require lock --out-dir "${INJECTED_DIR:-/workspace/runtime/injected}"

set +e
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_replay_gate_v2.py" \
  --gate \
  --successor-authorization "p0-r1-successor-session" \
  --image-digest "$IMAGE_DIGEST" \
  --ready-commit "$READY_COMMIT" \
  --lock-file "${INJECTED_DIR:-/workspace/runtime/injected}/p0_r1_execution_lock_v2.json" \
  --src "$SRC" \
  --out-dir "$OUT_DIR"
GATE_EXIT=$?
set -e

# The gate writes its bytes before it returns on both the pass and the failure
# path. A non-zero exit is preserved only after those bytes exist, so a stop is
# recorded rather than lost.
for artifact in p0_r1_replay_result.json p0_r1_replay_receipt.json \
                p0_r1_replay_counters.json P0_R1_REPLAY_DISPOSITION.md \
                p0_r1_replay_transport_receipt.json; do
  if [ ! -s "$OUT_DIR/$artifact" ]; then
    echo "FAIL: the replay gate did not write $artifact" >&2
    exit 2
  fi
  echo "ARTIFACT=$artifact SHA256=$(sha256sum "$OUT_DIR/$artifact" | cut -d' ' -f1) BYTES=$(stat -c%s "$OUT_DIR/$artifact")"
done

python "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_verify_replay_receipt.py" \
  --out-dir "$OUT_DIR"

echo "TOKENIZER_ENCODES=0"
echo "MODEL_OPERATIONS=0"
echo "P0_R1_REPLAY_GATE_COMPLETE=1"
exit "$GATE_EXIT"
