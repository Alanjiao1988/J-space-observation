#!/usr/bin/env bash
set -euo pipefail

COMMIT="$1"
TREE="$2"
SOURCE_ROOT="/workspace/study2-src"
REPEAT_ROOT="/workspace/study2-repeat"

test ! -e "$SOURCE_ROOT"
test ! -e "$REPEAT_ROOT"
git clone -q /workspace/repo.bundle "$SOURCE_ROOT"
cd "$SOURCE_ROOT"
git checkout -q "$COMMIT"

test "$(git rev-parse HEAD)" = "$COMMIT"
test "$(git rev-parse HEAD^{tree})" = "$TREE"
test -z "$(git status --porcelain)"
cmp /workspace/study2_generate_banks.sh infra/azure/acr_tasks/study2_generate_banks.sh
cmp /workspace/study2_generate_banks.yaml infra/azure/acr_tasks/study2_generate_banks.yaml
cmp /workspace/study2_bank_output.Dockerfile infra/azure/acr_tasks/study2_bank_output.Dockerfile

echo "BOUND_COMMIT=$COMMIT"
echo "BOUND_TREE=$TREE"
echo "RUN_TYPE=QuickRun"
echo "RUN_ID=${ACR_RUN_ID}"
python -V

PYTHONHASHSEED=1 python scripts/build_study2_task_bank.py --json
mkdir -p "$REPEAT_ROOT"
PYTHONHASHSEED=777 python scripts/build_study2_task_bank.py \
  --output-root "$REPEAT_ROOT" \
  --json

for filename in \
  development.jsonl \
  behavioral_confirmation.jsonl \
  mechanistic_development_candidate_pairs.jsonl \
  mechanistic_candidate_pairs.jsonl
do
  cmp "studies/study2/data/$filename" "$REPEAT_ROOT/$filename"
done

python scripts/validate_study2_protocol.py --allow-dirty --json

python - "$COMMIT" "$TREE" "${ACR_RUN_ID}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

commit, tree, run_id = sys.argv[1:]
root = Path("studies/study2/data")
manifest = json.loads((root / "task_bank_manifest.json").read_text(encoding="utf-8"))
binding = {
    "schema_version": "jspace-study2-acr-bank-export/v1",
    "run_id": run_id,
    "run_type": "QuickRun",
    "source_commit": commit,
    "source_tree": tree,
    "python_hash_seeds_compared": [1, 777],
    "repeat_byte_identical": True,
    "files": manifest["files"],
}
Path(".study2_acr_generation_binding.json").write_text(
    json.dumps(binding, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
for role, row in manifest["files"].items():
    data = (Path(row["path"])).read_bytes()
    assert len(data) == row["bytes"]
    assert hashlib.sha256(data).hexdigest() == row["sha256"]
    print(f"OUTPUT|{role}|rows={row['rows']}|bytes={row['bytes']}|sha256={row['sha256']}")
print("GENERATION_REPEAT_BYTE_IDENTICAL=1")
PY

echo "DIRTY_AFTER_GENERATION=$(git status --porcelain | wc -l)"
echo "STUDY2_BANK_GENERATION_COMPLETE=1"
