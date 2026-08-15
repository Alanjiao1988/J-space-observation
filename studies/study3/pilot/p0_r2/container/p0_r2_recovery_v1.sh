#!/bin/sh
# CPU-only recovery for a terminated P0-R2 attempt.
#
# Recovery runs after any terminal status, including a hard kill. It reads the
# durable journal and the recursive manifest from the private prefix and
# classifies the attempt as COMPLETE or PARTIAL. It never repairs, replaces, or
# deletes an observation, and a PARTIAL classification never authorizes a retry.
#
# It requests no accelerator and refuses to run on a replica that has one.

set -eu

STAGE="STUDY3-P0-R2"
SRC="${P0_R2_SRC:-/opt/jspace/src}"
R2="${SRC}/studies/study3/pilot/p0_r2"
PYTHONPATH="${R2}:${SRC}/studies/study3/pilot/p0_r1"
export PYTHONPATH

RUNTIME="${P0_R2_RUNTIME_ROOT:-/workspace/runtime}"
ATTEMPT="${P0_R2_ATTEMPT:-}"

if [ -z "${ATTEMPT}" ]; then
    echo "P0_R2_RECOVERY_REFUSED=1 P0_R2_ATTEMPT is required" >&2
    exit 2
fi

mkdir -p "${RUNTIME}"

echo "P0_R2_STAGE=${STAGE}"
echo "P0_R2_ATTEMPT=${ATTEMPT}"
echo "P0_R2_RECOVERY_CPU_ONLY=1"

python3 "${R2}/p0_r2_recovery_v1.py" --recover "${ATTEMPT}" \
    --lock-sha256 "${P0_R2_LOCK_SHA256:-}" \
    --out "${RUNTIME}/p0_r2_recovery_report.json"
