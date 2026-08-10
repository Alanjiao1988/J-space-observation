#!/usr/bin/env bash
# Stage P0-T runner for the registered Azure container route.
#
# Authority: studies/study3/prompts/study3_p0_feasibility_pilot_authority.md
# section 7.
#
# This script is CPU-only. It allocates no GPU, downloads no model weights,
# loads no checkpoint, performs no forward pass and generates no text. It runs
# the tokenizer and renderer census and then packs the result and receipt onto
# the job log through the committed self-verifying transport.
#
# It is not run from a working tree. It is uploaded as a standalone source
# context together with a repo.bundle produced by
# `git bundle create repo.bundle HEAD`, so the agent clones the exact published
# commit itself and no local working tree can leak into the run. That is what
# binds the stage to the exact published pre-execution lineage required by
# section 7.
#
# Usage inside the task:
#   bash /workspace/p0_t_stage.sh <commit> [--dry-run]

set -euo pipefail

COMMIT="$1"
shift || true
EXTRA_ARGS=("$@")

SRC=/tmp/src
OUT=/tmp/p0out

export HOME=/tmp/p0home
export XDG_CACHE_HOME=/tmp/p0cache
export HF_HOME=/tmp/p0cache/huggingface
export TMPDIR=/tmp/p0tmp
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_TELEMETRY=1
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$HF_HOME" "$TMPDIR" "$OUT"

echo "=== STAGE P0-T BINDING ==="
if [[ -d "$SRC/.git" ]]; then
    echo "reusing the checkout produced by the preceding step"
else
    mkdir -p "$SRC"
    git clone -q /workspace/repo.bundle "$SRC"
fi
cd "$SRC"
git checkout -q "$COMMIT"
echo "BOUND_COMMIT=$(git rev-parse HEAD)"
echo "BOUND_TREE=$(git rev-parse HEAD^{tree})"
echo "DIRTY=$(git status --porcelain | wc -l)"

echo "=== ENVIRONMENT IDENTITY ==="
python -V
python - <<'PY'
import json
import platform
import sys

record = {
    "python_version": platform.python_version(),
    "platform": platform.platform(),
    "executable": sys.executable,
}
try:
    import torch
    record["torch_version"] = torch.__version__
    record["cuda_available"] = bool(torch.cuda.is_available())
    record["cuda_device_count"] = int(torch.cuda.device_count())
except Exception as exc:  # noqa: BLE001
    record["torch_import_error"] = str(exc)
try:
    import transformers
    record["transformers_version"] = transformers.__version__
except Exception as exc:  # noqa: BLE001
    record["transformers_import_error"] = str(exc)
try:
    import tokenizers
    record["tokenizers_version"] = tokenizers.__version__
except Exception as exc:  # noqa: BLE001
    record["tokenizers_import_error"] = str(exc)
print("STAGE_ENVIRONMENT=" + json.dumps(record, sort_keys=True))
PY

echo "=== CPU-ONLY GUARD ==="
python - <<'PY'
import sys

try:
    import torch
except Exception as exc:  # noqa: BLE001
    print("torch unavailable: %s" % exc)
    sys.exit(0)
if torch.cuda.is_available() or torch.cuda.device_count() > 0:
    sys.exit("[FAIL] stage P0-T is CPU-only; a GPU is visible to this container")
print("[OK] no GPU is visible to this container")
PY

echo "=== FROZEN INPUT RE-DERIVATION ==="
python "$SRC/studies/study3/pilot/p0/p0_freeze_corpus.py" --check
python "$SRC/studies/study3/pilot/p0/p0_protocol.py" --check

echo "=== STAGE P0-T ==="
set +e
python "$SRC/studies/study3/pilot/p0/p0_tokenizer_gate.py" \
    --out-dir "$OUT" "${EXTRA_ARGS[@]}"
GATE_EXIT=$?
set -e
echo "P0_T_GATE_EXIT=${GATE_EXIT}"

echo "=== NO MODEL ARTIFACT WAS FETCHED ==="
python - "$HF_HOME" <<'PY'
import os
import sys

root = sys.argv[1]
weights = []
for dirpath, _dirnames, filenames in os.walk(root):
    for name in filenames:
        if name.endswith((".safetensors", ".bin", ".pt", ".pth", ".gguf",
                          ".msgpack", ".h5")):
            weights.append(os.path.join(dirpath, name))
if weights:
    sys.exit("[FAIL] a model weight artifact was fetched: %s" % weights[:5])
print("[OK] no model weight artifact is present in the cache")
PY

echo "=== TRANSPORT ==="
# The transport always runs, including after a fail-closed stop, because the
# authority requires actual counters and partial outcomes to be preserved and
# published rather than discarded.
python "$SRC/studies/study3/pilot/p0/p0_transport.py" pack --source-dir "$OUT"

echo "P0_T_STAGE_COMPLETE=1"
exit "${GATE_EXIT}"
