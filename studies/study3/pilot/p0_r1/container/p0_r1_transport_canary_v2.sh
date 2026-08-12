#!/usr/bin/env bash
# Stage P0-R1 generation-2 model-free transport canary entry point.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md
#   sections 7 and 11.
#
# Installed at /usr/local/bin/p0_r1_transport_canary_v2.sh. This is the ONLY
# authorized in-cluster execution of this round.
#
# It proves the repaired transport works on the real infrastructure without
# touching the science: it verifies the standalone layout, exercises the log
# envelope end to end, and writes and reads back real objects in the private
# storage account over the managed-identity route.
#
# It constructs no tokenizer, encodes nothing, downloads and loads no checkpoint,
# allocates no GPU workload, performs no model operation, runs no replay gate,
# and consumes no one-shot envelope. It writes only to a canary prefix that is
# disjoint from every attempt prefix.
set -euo pipefail

ATTEMPT_ID="${1:-${P0_R1_CANARY_ATTEMPT:-}}"
SRC="${P0_R1_SRC:-/opt/jspace/src}"
OUT_DIR="${RESULTS_DIR:-/workspace/runtime/results}"

if [ -z "$ATTEMPT_ID" ]; then
  echo "FAIL: the canary requires a unique attempt identifier" >&2
  exit 2
fi

echo "=== P0-R1 TRANSPORT CANARY (generation 2, model-free) ==="
echo "SRC=$SRC"
echo "CANARY_ATTEMPT=$ATTEMPT_ID"

mkdir -p "$OUT_DIR"

echo "--- canary 1 of 3: standalone layout ---"
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py" \
  --verify-layout --src "$SRC"

echo "--- canary 2 of 3: replay transport envelope ---"
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_transport.py" --self-check

echo "--- canary 3 of 3: private object store, real route ---"
python "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_no_accelerator_probe.py"
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_blob_transport.py" \
  --canary --attempt "$ATTEMPT_ID" \
  --receipt "$OUT_DIR/p0_r1_blob_canary_receipt.json"

echo "TOKENIZER_CONSTRUCTIONS=0"
echo "TOKENIZER_ENCODES=0"
echo "CHECKPOINT_DOWNLOADS=0"
echo "MODEL_OPERATIONS=0"
echo "GPU_WORKLOAD_ALLOCATED=false"
echo "REPLAY_GATE_RUN=false"
echo "ONE_SHOT_ENVELOPE_CONSUMED=false"
echo "P0_R1_TRANSPORT_CANARY_COMPLETE=1"
