#!/usr/bin/env bash
# Stage P0-R1 generation-2 model-pilot entry point. GPU execution session only.
#
# Authority:
#   studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md
#   sections 5, 7, 8 and 9, over the two prior P0-R1 authorities.
#
# Installed at /usr/local/bin/p0_r1_model_pilot_v2.sh. This is the Container Apps
# job command, and unlike generation 1's /workspace/p0_r1_model_pilot.sh it is a
# path that exists in the image.
#
# Generation 1 could exit before its only artifact writer ran, which would have
# left a possibly-started irreversible operation indistinguishable from a
# non-attempt. This entry point installs a trap first, so an infrastructure
# failure at any point still produces a durable receipt describing what may have
# started. The receipt refuses the retry; it does not authorize one.
#
# It runs at most once. The launcher sets replica retry to zero and the runner
# stops before any registered cap rather than recording an overrun.
set -euo pipefail

IMAGE_DIGEST="${1:-${P0_R1_IMAGE_DIGEST:-}}"
READY_COMMIT="${2:-${P0_R1_READY_COMMIT:-}}"
SRC="${P0_R1_SRC:-/opt/jspace/src}"
OUT_DIR="${RESULTS_DIR:-/workspace/runtime/results}"
INJECTED="${INJECTED_DIR:-/workspace/runtime/injected}"
ATTEMPT_ID="${P0_R1_ATTEMPT_ID:-unknown-attempt}"
STAGE="startup"

mkdir -p "$OUT_DIR" "$INJECTED"

# Installed before anything else can fail. Any premature exit writes a durable
# infrastructure receipt naming the stage that was in flight.
on_premature_exit() {
  local code=$?
  if [ "$code" -eq 0 ]; then
    return 0
  fi
  echo "P0_R1_PREMATURE_EXIT=1 STAGE=$STAGE CODE=$code" >&2
  python "$SRC/studies/study3/pilot/p0_r1/p0_r1_journal.py" \
    --infrastructure-receipt \
    --attempt "$ATTEMPT_ID" \
    --stage "$STAGE" \
    --detail "the entry point exited with code $code" \
    --execution-name "${CONTAINER_APP_JOB_EXECUTION_NAME:-unknown}" \
    --image-digest "$IMAGE_DIGEST" \
    --ready-commit "$READY_COMMIT" \
    --out "$OUT_DIR/p0_r1_infrastructure_receipt.json" >&2 || true
  echo "P0_R1_RETRY_AUTHORIZED=false" >&2
  return 0
}
trap on_premature_exit EXIT

echo "=== P0-R1 MODEL PILOT (generation 2) ==="
echo "SRC=$SRC"
echo "OUT_DIR=$OUT_DIR"

STAGE="standalone_layout_verification"
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py" \
  --verify-layout --src "$SRC"

STAGE="runtime_injection"
# The lock and the replay receipt arrive as injected bytes, size-checked and
# hash-checked. Neither is baked into the image, so the image stays free of any
# outcome-conditioned byte.
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py" \
  --reconstruct --require lock --require receipt --out-dir "$INJECTED"

RECEIPT="$INJECTED/p0_r1_replay_receipt.json"
LOCK="$INJECTED/p0_r1_execution_lock_v2.json"

if [ ! -s "$RECEIPT" ]; then
  echo "FAIL: no replay-pass receipt at $RECEIPT; the gate must pass first" >&2
  exit 2
fi
if [ ! -s "$LOCK" ]; then
  echo "FAIL: no generation-2 execution lock at $LOCK" >&2
  exit 2
fi

STAGE="pre_start_validation"
# Every launch input is validated together, before a model library is imported
# and before an accelerator is touched. A refusal here costs nothing.
python "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_prestart_guard.py" \
  --lock-file "$LOCK" \
  --receipt-file "$RECEIPT" \
  --image-digest "$IMAGE_DIGEST" \
  --ready-commit "$READY_COMMIT" \
  --src "$SRC"

ATTEMPT_ID="$(python "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_prestart_guard.py" \
  --receipt-file "$RECEIPT" --print-attempt-id)"
echo "P0_R1_ATTEMPT_ID=$ATTEMPT_ID"

STAGE="accelerator_probe"
python "$SRC/studies/study3/pilot/p0_r1/container/p0_r1_require_accelerator.py"

STAGE="model_pilot"
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_model_runner_v2.py" \
  --run \
  --lock-file "$LOCK" \
  --receipt-file "$RECEIPT" \
  --image-digest "$IMAGE_DIGEST" \
  --ready-commit "$READY_COMMIT" \
  --attempt "$ATTEMPT_ID" \
  --src "$SRC" \
  --out-dir "$OUT_DIR"

STAGE="artifact_persistence"
# The artifacts are persisted and read back before the container is allowed to
# exit successfully. Generation 1 wrote them to an ephemeral filesystem that the
# job teardown reclaimed.
python "$SRC/studies/study3/pilot/p0_r1/p0_r1_blob_transport.py" \
  --persist --attempt "$ATTEMPT_ID" --in-dir "$OUT_DIR" \
  --receipt "$OUT_DIR/p0_r1_persistence_receipt.json"

trap - EXIT
echo "P0_R1_MODEL_PILOT_COMPLETE=1"
