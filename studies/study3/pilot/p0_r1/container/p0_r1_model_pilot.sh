#!/usr/bin/env bash
# Stage P0-R1 model-pilot entry point. GPU execution session only.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md
#   section 6, over studies/study3/prompts/study3_v0_6_p0_r1_authority.md.
#
# This is the container command of the single Azure Container Apps T4 job. It
# refuses to start unless a byte-valid replay-pass receipt and the matching
# unconsumed execution lock are present, so a prose log line can never authorize
# a model operation.
#
# It runs at most once. The launcher sets replica retry to zero, and the runner
# stops before any registered cap rather than recording an overrun.
set -euo pipefail

COMMIT="$1"
IMAGE_DIGEST="${2:-}"
SRC="${SRC:-/workspace/src}"
OUT_DIR="${RESULTS_DIR:-/workspace/runtime/results}"
RECEIPT="${REPLAY_RECEIPT:-$OUT_DIR/p0_r1_replay_receipt.json}"

echo "=== P0-R1 MODEL PILOT ==="
cd "$SRC"

if [ ! -s "$RECEIPT" ]; then
  echo "FAIL: no replay-pass receipt at $RECEIPT; the replay gate must pass first" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

python - <<'PY'
import torch
print("GPU_COUNT=%d" % torch.cuda.device_count())
print("CUDA_AVAILABLE=%s" % torch.cuda.is_available())
print("TORCH_VERSION=%s" % torch.__version__)
if not torch.cuda.is_available():
    raise SystemExit("FAIL: the P0-R1 model pilot requires one Azure GPU")
print("DEVICE_NAME=%s" % torch.cuda.get_device_name(0))
PY

python - "$SRC" "$OUT_DIR" "$RECEIPT" "$IMAGE_DIGEST" <<'PY'
import json
import os
import sys

src, out_dir, receipt_path, image_digest = sys.argv[1:5]
sys.path.insert(0, os.path.join(src, "studies", "study3", "pilot", "p0_r1"))

import p0_r1_execution_lock as LOCK
import p0_r1_model_runner as RUNNER

with open(receipt_path, "rb") as handle:
    receipt = json.loads(handle.read().decode("utf-8"))

lock = LOCK.load_lock(root=src)
LOCK.verify_binding(lock, image_digest=image_digest or None, root=src)

authorization = {
    "p0_r1_pilot_execution_authorized": True,
    "replay_gate_passed_in_this_session": True,
    "execution_lock": lock,
    "replay_receipt": receipt,
    "attempt_id": receipt["attempt_id"],
}

outcome = RUNNER.run(authorization=authorization, out_dir=out_dir, root=src)
print("P0_R1_MODEL_PILOT_STATE=%s" % outcome["state"])
for artifact in outcome["artifacts"]:
    print("ARTIFACT=%s SHA256=%s BYTES=%d"
          % (artifact["name"], artifact["sha256"], artifact["bytes"]))
PY

echo "P0_R1_MODEL_PILOT_COMPLETE=1"
