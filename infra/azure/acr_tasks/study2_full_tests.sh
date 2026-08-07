#!/usr/bin/env bash
set -euo pipefail

COMMIT="$1"
mkdir -p /tmp/src
git clone -q /workspace/repo.bundle /tmp/src
cd /tmp/src
git checkout -q "$COMMIT"

echo "BOUND_COMMIT=$(git rev-parse HEAD)"
echo "BOUND_TREE=$(git rev-parse HEAD^{tree})"
echo "DIRTY=$(git status --porcelain | wc -l)"
python -V
pip install -q -r requirements.lock.txt

set +e
python -m pytest -q -rf --no-header -p no:cacheprovider \
  --junitxml=/tmp/study2-full-suite.xml
PYTEST_EXIT=$?
set -e

python - "$PYTEST_EXIT" <<'PY'
import json
import sys
import xml.etree.ElementTree as ET

pytest_exit = int(sys.argv[1])
root = ET.parse("/tmp/study2-full-suite.xml").getroot()
suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
tests = sum(int(suite.attrib["tests"]) for suite in suites)
failures = sum(int(suite.attrib["failures"]) for suite in suites)
errors = sum(int(suite.attrib["errors"]) for suite in suites)
skipped = sum(int(suite.attrib["skipped"]) for suite in suites)
passed = tests - failures - errors - skipped

observed = {
    (case.attrib.get("classname", ""), case.attrib.get("name", ""))
    for suite in suites
    for case in suite.iter("testcase")
    if case.find("failure") is not None or case.find("error") is not None
}
expected_names = {
    "test_seal_writes_twelve_objects_with_the_set_manifest_last",
    "test_seal_refuses_a_non_empty_parent_prefix",
}
if pytest_exit != 1:
    raise SystemExit(f"expected pytest exit 1, observed {pytest_exit}")
if failures != 2 or errors != 0:
    raise SystemExit(f"unexpected failure/error counts: failures={failures} errors={errors}")
if {name for _, name in observed} != expected_names:
    raise SystemExit(f"unexpected failing tests: {sorted(observed)}")
if any(not classname.endswith("test_parser_v3_seal_job") for classname, _ in observed):
    raise SystemExit(f"failure escaped historical parser-seal file: {sorted(observed)}")

print(
    "FULL_SUITE_RESULT="
    + json.dumps(
        {
            "passed": passed,
            "skipped": skipped,
            "failed": failures,
            "errors": errors,
            "pytest_exit": pytest_exit,
            "accepted_historical_failures": sorted(
                f"{classname}::{name}" for classname, name in observed
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
print("FULL_SUITE_ACCEPTED_HISTORICAL_FAILURES_ONLY=1")
PY
