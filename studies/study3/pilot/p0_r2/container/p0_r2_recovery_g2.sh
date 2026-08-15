#!/bin/sh
# CPU-only recovery for a terminated P0-R2 generation-2 attempt.
#
# Authority: studies/study3/prompts/
# study3_p0_r2_generation2_successor_and_conditional_execution_authority.md
# section 16.
#
# Recovery runs after any terminal status, including a hard kill. It reads the
# durable create-only journal and the recursive manifest from the generation-2
# private prefix and classifies the attempt as COMPLETE or PARTIAL. It never
# repairs, replaces or deletes an observation, and a PARTIAL classification
# never authorizes a retry.
#
# It requests no accelerator, neutralises the accelerator markers the CUDA base
# image sets, and refuses to run on a replica that still looks accelerated.

set -eu

STAGE="STUDY3-P0-R2"
SRC="${P0_R2_SRC:-/opt/jspace/src}"
R2="${SRC}/studies/study3/pilot/p0_r2"
PYTHONPATH="${R2}:${SRC}/studies/study3/pilot/p0_r1"
export PYTHONPATH

RUNTIME="${P0_R2_RUNTIME_ROOT:-/workspace/runtime}"
ATTEMPT="${P0_R2_ATTEMPT:-}"

if [ -z "${ATTEMPT}" ]; then
    echo "P0_R2_G2_RECOVERY_REFUSED=1 P0_R2_ATTEMPT is required" >&2
    exit 2
fi

mkdir -p "${RUNTIME}"

echo "P0_R2_STAGE=${STAGE}"
echo "P0_R2_G2_GENERATION=2"
echo "P0_R2_ATTEMPT=${ATTEMPT}"
echo "P0_R2_G2_RECOVERY_CPU_ONLY=1"
echo "P0_R2_G2_NVIDIA_VISIBLE_DEVICES=${NVIDIA_VISIBLE_DEVICES:-unset}"
echo "P0_R2_G2_CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"

python3 - "${ATTEMPT}" "${RUNTIME}/p0_r2_g2_recovery_report.json" <<'PYTHON'
import json
import sys

import p0_r2_namespace_g2 as NS

attempt, out_path = sys.argv[1], sys.argv[2]
recovery = NS.recovery()

# The generation-2 recovery job name must be the one this namespace binds.
if recovery.RECOVERY_JOB != NS.RECOVERY_JOB:
    raise SystemExit(
        "P0_R2_G2_RECOVERY_REFUSED=1 the recovery job is not the generation-2 job")

recovery.assert_model_free()
report = recovery.recover(attempt)
payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
with open(out_path, "w", encoding="utf-8") as handle:
    handle.write(payload)
print(payload, end="")
print("P0_R2_G2_RECOVERY_CLASSIFICATION=%s" % report.get("classification"))
print("P0_R2_G2_RECOVERY_COMPLETE=1")
PYTHON

echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
