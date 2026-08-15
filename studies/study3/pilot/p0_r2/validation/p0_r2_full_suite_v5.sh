#!/usr/bin/env bash
# Run the full repository suite twice in one container -- once at the unmodified
# baseline, once at the executable commit -- in the dependency closure the
# repository registers in requirements.lock.txt.
#
# Running both in the same container removes every environmental explanation for
# a difference between them. Whatever fails at the baseline is not this change's
# doing; whatever fails only at the executable commit is.
#
# It performs no tokenizer construction, no checkpoint download, no model weight
# load, no prefill, no generation and no GPU operation. It never runs the replay
# gate and never touches the one-shot envelope.
set -euo pipefail

cat /workspace/P0_R2_BINDING
echo "GIT=$(git --version)"
python3 -c 'import sys; print("PYVER=" + sys.version.split()[0])'

cd /workspace/src
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
    raise SystemExit("P0_R2_FULL_SUITE_REFUSED=1 installed closure is not the registered lock")
print("P0_R2_INSTALLED_CLOSURE_MATCHES_LOCK=1 packages=%d" % len(expected))
PY

export CUDA_VISIBLE_DEVICES=""
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONDONTWRITEBYTECODE=1

run_suite () {
  local label="$1" dir="$2" out="$3"
  cd "$dir"
  echo "===== ${label} ====="
  echo "${label}_COMMIT=$(git rev-parse HEAD)"
  echo "${label}_DIRTY=$(git status --porcelain | wc -l)"
  set +e
  python3 -m pytest -q -p no:cacheprovider --color=no -rfE --tb=no > "$out" 2>&1
  local status=$?
  set -e
  grep -E '^(FAILED|ERROR) ' "$out" | sed 's/ - .*//' | sort > "${out}.set"
  echo "${label}_STATUS=${status}"
  echo "${label}_COUNTS=$(tail -n 1 "$out")"
  echo "${label}_NONPASSING:"
  cat "${out}.set"
}

run_suite BASELINE /workspace/base /workspace/base.out
run_suite EXECUTABLE /workspace/src /workspace/exec.out

echo "===== attribution ====="
echo "NEW_FAILURES_INTRODUCED_BY_THIS_CHANGE:"
comm -13 /workspace/base.out.set /workspace/exec.out.set | tee /workspace/new.set
echo "FAILURES_PRESENT_AT_BASELINE_AND_STILL_PRESENT:"
comm -12 /workspace/base.out.set /workspace/exec.out.set
echo "FAILURES_FIXED_BY_THIS_CHANGE:"
comm -23 /workspace/base.out.set /workspace/exec.out.set

echo "P0_R2_NEW_FAILURE_COUNT=$(wc -l < /workspace/new.set)"
echo "P0_R2_FULL_SUITE_COMPLETE=1"
echo "P0_R2_REPLAY_GATE_RUN=false"
echo "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false"
echo "P0_R2_MODEL_OPERATIONS_PERFORMED=0"