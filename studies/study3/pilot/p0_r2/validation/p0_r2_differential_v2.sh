#!/usr/bin/env bash
# The corrected P0-R2 full differential suite (A9).
#
# The same suite runs twice in one container -- once at the unmodified baseline
# 005aa087, once at the corrected head -- in the one dependency closure
# requirements.lock.txt registers. Running both in the same container removes
# every environmental explanation for a difference between them.
#
# What changes from the v1 harness is what is compared. v1 compared FAILED and
# ERROR *lines*; this compares exact node ids **and** complete normalized
# failure signatures, so "the same four failures" is a proved statement rather
# than a coincidence of names.
#
# pytest's status is captured directly and reconciled against its own printed
# summary. Nothing is piped into anything that could hide an exit status.
#
# Zero tokenizer constructions, zero encodes, zero checkpoint downloads, zero
# model weight loads, zero prefills, zero generations, zero scored rows and zero
# GPU operations. The replay gate is never invoked and the one-shot envelope is
# never opened.
set -euo pipefail

bash /workspace/p0_r2_baseline_signatures_v2.sh BASELINE  /workspace/base
bash /workspace/p0_r2_baseline_signatures_v2.sh CORRECTED /workspace/head

echo "===== differential ====="
python3 /workspace/p0_r2_normalize_signatures_v2.py \
    --compare /workspace/BASELINE.signatures.json \
              /workspace/CORRECTED.signatures.json \
    --out /workspace/differential.json > /dev/null
cat /workspace/differential.json

python3 - <<'PY'
import json
report = json.load(open("/workspace/differential.json", encoding="utf-8"))
base = json.load(open("/workspace/BASELINE.signatures.json", encoding="utf-8"))
head = json.load(open("/workspace/CORRECTED.signatures.json", encoding="utf-8"))

registered = [
    "tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix",
    "tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last",
    "tests/test_phase05_jlens_saturation.py::test_no_artifact_asserts_a_prohibited_claim",
    "tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only",
]

print("P0_R2_NEW_FAILURE_COUNT=%d" % report["new_failure_count"])
print("P0_R2_NEW_FAILURES=%s" % json.dumps(report["new_failures"]))
print("P0_R2_FIXED_FAILURES=%s" % json.dumps(report["fixed_failures"]))
print("P0_R2_SIGNATURES_AGREE=%s" % report["signatures_agree"])
print("P0_R2_SIGNATURE_DISAGREEMENTS=%s"
      % json.dumps(report["signatures_disagreeing_on_shared_failures"]))
print("P0_R2_BASELINE_COLLECTION_ERRORS=%d" % base["collection_error_count"])
print("P0_R2_CORRECTED_COLLECTION_ERRORS=%d" % head["collection_error_count"])
print("P0_R2_BASELINE_COUNTS=%s" % json.dumps(base["counts"], sort_keys=True))
print("P0_R2_CORRECTED_COUNTS=%s" % json.dumps(head["counts"], sort_keys=True))
print("P0_R2_NET_NEW_PASSING=%d"
      % (head["counts"]["passed"] - base["counts"]["passed"]))

problems = []
if report["new_failure_count"]:
    problems.append("a new failure was introduced")
if not report["signatures_agree"]:
    problems.append("a shared failure changed its normalized signature")
if not report["zero_collection_errors"]:
    problems.append("collection errors are not zero")
if base["non_passing_node_ids"] != registered:
    problems.append("the baseline standing failures are not the registered four")
if head["non_passing_node_ids"] != registered:
    problems.append("the corrected standing failures are not the registered four")
if report["fixed_failures"]:
    problems.append("a baseline failure disappeared; deselection must not hide it")

if problems:
    for problem in problems:
        print("P0_R2_DIFFERENTIAL_REFUSED=1 %s" % problem)
    raise SystemExit(1)

print("P0_R2_EXACTLY_THE_FOUR_REGISTERED_STANDING_FAILURES=1")
print("P0_R2_ZERO_NEW_FAILURES=1")
print("P0_R2_ZERO_COLLECTION_ERRORS=1")
PY

echo "P0_R2_FULL_SUITE_DIFFERENTIAL_COMPLETE=1"
echo "P0_R2_REPLAY_GATE_RUN=false"
echo "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
