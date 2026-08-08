#!/usr/bin/env bash
# Study 2 Stage T pinned config/tokenizer gate, executed only in Azure ACR.
#
# This file is not run from a local working tree.  It is uploaded as a
# standalone source context together with a `repo.bundle` produced by
# `git bundle create repo.bundle HEAD`, so the build agent clones the exact
# commit itself and no laptop state can leak into the run:
#
#   az acr run --registry <registry> --platform linux/amd64 \
#     -f study2_stage_t.yaml \
#     --set COMMIT=<sha> --set TREE=<tree> \
#     --set ATTEMPT_ID=<id> --set HASH_SEED=<int> --set OUTPUT_TAG=<tag> \
#     <context-dir>
#
# Stage T resolves configuration and tokenizer assets only.  The cache is
# asserted empty before acquisition and asserted weight-free afterwards, so a
# passing run is positive evidence that no model weight was ever fetched.
set -euo pipefail

COMMIT="$1"
TREE="$2"
ATTEMPT_ID="$3"
HASH_SEED="$4"
SOURCE_ROOT="/workspace/study2-src"
CACHE_ROOT="/workspace/stage-t-cache"

test ! -e "$SOURCE_ROOT"
test ! -e "$CACHE_ROOT"
git clone -q /workspace/repo.bundle "$SOURCE_ROOT"
cd "$SOURCE_ROOT"
git checkout -q "$COMMIT"

test "$(git rev-parse HEAD)" = "$COMMIT"
test "$(git rev-parse HEAD^{tree})" = "$TREE"
test -z "$(git status --porcelain)"
cmp /workspace/study2_stage_t.sh infra/azure/acr_tasks/study2_stage_t.sh
cmp /workspace/study2_stage_t.yaml infra/azure/acr_tasks/study2_stage_t.yaml
cmp /workspace/study2_stage_t_output.Dockerfile \
  infra/azure/acr_tasks/study2_stage_t_output.Dockerfile

echo "BOUND_COMMIT=$COMMIT"
echo "BOUND_TREE=$TREE"
echo "RUN_TYPE=QuickRun"
echo "RUN_ID=${ACR_RUN_ID}"
echo "ATTEMPT_ID=$ATTEMPT_ID"
echo "PYTHONHASHSEED=$HASH_SEED"
python -V
pip install -q -r requirements.lock.txt

mkdir -p "$CACHE_ROOT"
test -z "$(ls -A "$CACHE_ROOT")"
echo "CACHE_EMPTY_BEFORE_ACQUISITION=1"

export HF_HOME="$CACHE_ROOT/hf"
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export TRANSFORMERS_NO_ADVISORY_WARNINGS=1
export STAGE_T_SOURCE_COMMIT="$COMMIT"
export STAGE_T_SOURCE_TREE="$TREE"

PYTHONHASHSEED="$HASH_SEED" python scripts/run_study2_stage_t.py \
  --cache-root "$CACHE_ROOT" \
  --attempt-id "$ATTEMPT_ID" \
  --run-id "${ACR_RUN_ID}"

find "$CACHE_ROOT" -type f \
  \( -name '*.safetensors' -o -name '*.bin' -o -name '*.gguf' -o -name '*.pt' \
     -o -name '*.pth' -o -name '*.h5' -o -name '*.msgpack' -o -name '*.ot' \) \
  -print > /tmp/stage_t_weight_scan.txt
test ! -s /tmp/stage_t_weight_scan.txt
echo "CACHE_WEIGHT_FILES_AFTER_ACQUISITION=$(wc -l < /tmp/stage_t_weight_scan.txt)"
echo "CACHE_BYTES=$(du -sb "$CACHE_ROOT" | cut -f1)"

PYTHONHASHSEED="$HASH_SEED" python scripts/validate_study2_stage_t.py --json

test -z "$(git diff --name-only)"
test -z "$(git diff --cached --name-only)"
echo "TRACKED_FILES_MODIFIED=0"
echo "UNTRACKED_AFTER_GATE=$(git status --porcelain | wc -l)"

python - "$COMMIT" "$TREE" "${ACR_RUN_ID}" "$ATTEMPT_ID" "$HASH_SEED" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

commit, tree, run_id, attempt_id, hash_seed = sys.argv[1:6]
root = Path("studies/study2/stage_t")
manifest = json.loads((root / "stage_t_core_manifest.json").read_text(encoding="utf-8"))

for name, row in sorted(manifest["files"].items()):
    data = (root / name).read_bytes()
    assert len(data) == row["bytes"], name
    assert hashlib.sha256(data).hexdigest() == row["sha256"], name
    print(f"OUTPUT|{name}|rows={row['rows']}|bytes={row['bytes']}|sha256={row['sha256']}")

core = (root / "stage_t_core_manifest.json").read_bytes()
core_sha = hashlib.sha256(core).hexdigest()
print(f"OUTPUT|stage_t_core_manifest.json|bytes={len(core)}|sha256={core_sha}")

binding = {
    "schema_version": "jspace-study2-acr-stage-t-export/v1",
    "attempt_id": attempt_id,
    "core_manifest_bytes": len(core),
    "core_manifest_sha256": core_sha,
    "files": manifest["files"],
    "joint_eligible_pairs": manifest["joint_eligible_pairs"],
    "prompt_row_count_per_model": manifest["prompt_row_count_per_model"],
    "python_hash_seed": int(hash_seed),
    "run_id": run_id,
    "run_type": "QuickRun",
    "selected_total": manifest["selection"]["selected_total"],
    "source_commit": commit,
    "source_tree": tree,
    "terminal_state": manifest["terminal_state"],
}
Path(".study2_stage_t_binding.json").write_text(
    json.dumps(binding, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
print(f"CORE_MANIFEST_SHA256={core_sha}")
print(f"TERMINAL_STATE={manifest['terminal_state']}")
PY

echo "STUDY2_STAGE_T_COMPLETE=1"
