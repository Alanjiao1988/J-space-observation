#!/bin/sh
# The P0-R2 hard-kill / open-admission CPU recovery canary entry point.
#
# This is the receipt P0-R2 generation 1 was missing. It is CPU-only, uses
# managed identity, writes only synthetic bytes to a disjoint attempt prefix,
# and constructs no tokenizer, downloads no checkpoint, loads no weight and
# allocates no accelerator.
#
# It refuses without an explicit attempt id: a canary that invents its own
# prefix could collide with a real one.

set -eu

STAGE="STUDY3-P0-R2"
SRC="${P0_R2_SRC:-/opt/jspace/src}"
R2="${SRC}/studies/study3/pilot/p0_r2"
PYTHONPATH="${R2}:${SRC}/studies/study3/pilot/p0_r1"
export PYTHONPATH

OUT="${P0_R2_RUNTIME_ROOT:-/tmp/p0r2}/hardkill"
mkdir -p "${OUT}"

ATTEMPT="${P0_R2_ATTEMPT:-}"
if [ -z "${ATTEMPT}" ]; then
    echo "P0_R2_HARD_KILL_CANARY_REFUSED=1 no attempt id was supplied" >&2
    exit 2
fi

echo "P0_R2_STAGE=${STAGE}"
echo "P0_R2_HARD_KILL_ATTEMPT=${ATTEMPT}"

python3 "${R2}/p0_r2_hard_kill_canary_v2.py" --identity

python3 "${R2}/p0_r2_hard_kill_canary_v2.py" \
    --run --attempt "${ATTEMPT}" --rows "${P0_R2_HARD_KILL_ROWS:-2}" \
    --out "${OUT}/hard_kill_receipt.json"

echo "P0_R2_REPLAY_GATE_RUN=false"
echo "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
