#!/usr/bin/env bash
# Register the truthful standing-failure baseline at one exact commit (A3).
#
# This runs the whole repository suite once, at the unmodified baseline, in the
# exact registered closure: the dependency set requirements.lock.txt pins, on
# python:3.11-bookworm, from a fresh clean clone of one exact commit. It
# captures the exact node id and the complete failure text of every non-passing
# test, then normalizes that text into a comparable signature.
#
# pytest's status is captured directly from the process. It is never piped into
# anything that could hide it, and the summary it prints is reconciled against
# the independently captured record rather than trusted.
#
# It performs no tokenizer construction, no encode, no checkpoint download, no
# model weight load, no prefill, no generation, no scoring and no GPU
# operation. It never runs the replay gate and never touches the one-shot
# envelope.
set -euo pipefail

LABEL="${1:?name the label}"
DIR="${2:?name the checkout directory}"

cat /workspace/P0_R2_BINDING
echo "GIT=$(git --version)"
python3 -c 'import sys; print("PYVER=" + sys.version.split()[0])'
python3 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else "P0_R2_BASELINE_REFUSED=1 python is not 3.11")'

cd "$DIR"
echo "${LABEL}_COMMIT=$(git rev-parse HEAD)"
echo "${LABEL}_TREE=$(git rev-parse 'HEAD^{tree}')"
echo "${LABEL}_DIRTY=$(git status --porcelain | wc -l)"
if [ "$(git status --porcelain | wc -l)" != "0" ]; then
  echo "P0_R2_BASELINE_REFUSED=1 the checkout is dirty" >&2; exit 2
fi

echo "REQUIREMENTS_LOCK_SHA256=$(sha256sum requirements.lock.txt | cut -d' ' -f1)"
python3 -m pip install --quiet --no-cache-dir --only-binary=:all: \
    -r requirements.lock.txt
echo "P0_R2_REGISTERED_CLOSURE_INSTALLED=1"

python3 - <<'PY'
import importlib.metadata as md
expected = {}
for raw in open("requirements.lock.txt", encoding="utf-8"):
    line = raw.strip()
    if not line or line.startswith("#") or "==" not in line:
        continue
    name, version = line.split("==", 1)
    expected[name.strip().lower().replace("_", "-")] = version.strip()
drift = []
for name, version in sorted(expected.items()):
    try:
        got = md.version(name)
    except md.PackageNotFoundError:
        drift.append((name, version, "ABSENT")); continue
    if got != version:
        drift.append((name, version, got))
for name, want, got in drift:
    print(f"LOCK_DRIFT {name} want={want} got={got}")
if drift:
    raise SystemExit("P0_R2_BASELINE_REFUSED=1 installed closure is not the registered lock")
print("P0_R2_INSTALLED_CLOSURE_MATCHES_LOCK=1 packages=%d" % len(expected))
PY

export CUDA_VISIBLE_DEVICES=""
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/workspace
export P0_R2_SIGNATURE_LABEL="${LABEL}"
export P0_R2_SIGNATURE_OUT="/workspace/${LABEL}.capture.json"

set +e
python3 -m pytest -q -p no:cacheprovider -p p0_r2_signature_plugin_v2 \
    --color=no -rfE --tb=long > "/workspace/${LABEL}.out" 2>&1
STATUS=$?
set -e
echo "${LABEL}_PYTEST_STATUS=${STATUS}"
tail -n 3 "/workspace/${LABEL}.out"

python3 /workspace/p0_r2_normalize_signatures_v2.py \
    --summarize "/workspace/${LABEL}.capture.json" \
    --out "/workspace/${LABEL}.signatures.json" > /dev/null

python3 - "$LABEL" "$STATUS" <<'PY'
import json, sys
label, status = sys.argv[1], int(sys.argv[2])
sig = json.load(open(f"/workspace/{label}.signatures.json", encoding="utf-8"))
tail = open(f"/workspace/{label}.out", encoding="utf-8").read().strip().splitlines()[-1]
print(f"{label}_SUMMARY_LINE={tail}")
print(f"{label}_CAPTURED_EXITSTATUS={sig['exitstatus']}")
print(f"{label}_PROCESS_EXITSTATUS={status}")
if sig["exitstatus"] != status:
    raise SystemExit("P0_R2_BASELINE_REFUSED=1 captured and process status disagree")
print(f"{label}_COLLECTION_ERRORS={sig['collection_error_count']}")
print(f"{label}_NON_PASSING_COUNT={sig['non_passing_count']}")
print(f"{label}_COUNTS={json.dumps(sig['counts'], sort_keys=True)}")
print(f"{label}_SIGNATURE_SET_SHA256={sig['signature_set_sha256']}")
for item in sig["signatures"]:
    print(f"{label}_NONPASSING {item['nodeid']} {item['kind']} "
          f"sha256={item['normalized_sha256']} bytes={item['normalized_bytes']}")
# Reconcile the independently captured record against pytest's own summary.
import re
counts = {}
for token, name in re.findall(r"(\d+) (passed|failed|skipped|error|errors)", tail):
    counts[name.rstrip("s")] = int(token)
print(f"{label}_SUMMARY_PARSED={json.dumps(counts, sort_keys=True)}")
if counts.get("failed", 0) != sig["counts"]["failed"]:
    raise SystemExit("P0_R2_BASELINE_REFUSED=1 summary and record disagree on failures")
print(f"{label}_SUMMARY_RECONCILED=1")
PY

echo "P0_R2_BASELINE_SIGNATURES_COMPLETE=1"
echo "P0_R2_REPLAY_GATE_RUN=false"
echo "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"
