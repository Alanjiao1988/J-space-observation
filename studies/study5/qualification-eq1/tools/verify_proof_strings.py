#!/usr/bin/env python3
"""Execution proof-string verifier for Study 5-EQ1 (OD-003).

OD-003 makes one rule standing for the rest of this invocation: a check that
cannot be shown to have executed did not pass. Every verification emits a unique
``P1-CHECK-<id> PASSED`` line on its success path, and this tool decides the
verdict by reading those lines out of a committed log.

The rule exists because of IMG-001, where a build verification layer exited 0
having executed nothing: the heredoc body was never delivered, ``python -`` read
empty stdin and terminated successfully. A success exit code was returned by a
process that performed no verification, so exit status cannot distinguish
"passed" from "never happened".

Two properties follow, and both are enforced here rather than assumed:

* the expected check ids are **enumerated in advance**, so a check that is
  silently deleted is reported as MISSING rather than simply never looked for;
* a proof string that appears more than once is an error, not a convenience. A
  duplicate means either the log was concatenated from two runs or an id was
  reused, and in both cases "this specific check passed" is no longer a claim
  the log can support.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROOF_RE = re.compile(r"^P1-CHECK-([A-Za-z0-9_.\-]+)\s+PASSED\s*$")
FAIL_RE = re.compile(r"^P1-CHECK-([A-Za-z0-9_.\-]+)\s+FAILED\b")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan(log_text: str) -> tuple[dict[str, int], dict[str, int]]:
    passed: dict[str, int] = {}
    failed: dict[str, int] = {}
    for line in log_text.splitlines():
        line = line.strip()
        match = PROOF_RE.match(line)
        if match:
            passed[match.group(1)] = passed.get(match.group(1), 0) + 1
            continue
        match = FAIL_RE.match(line)
        if match:
            failed[match.group(1)] = failed.get(match.group(1), 0) + 1
    return passed, failed


def judge(log_text: str, expected: list[str]) -> dict[str, Any]:
    passed, failed = scan(log_text)

    missing = [c for c in expected if c not in passed]
    duplicated = sorted(c for c, n in passed.items() if n > 1)
    unexpected = sorted(c for c in passed if c not in expected)
    explicit_failures = sorted(failed)

    checks = []
    for check in expected:
        count = passed.get(check, 0)
        if check in failed:
            verdict = "FAIL"
            reason = "the check emitted an explicit FAILED line"
        elif count == 0:
            verdict = "FAIL"
            reason = (
                "no execution proof string was found; under OD-003 a missing "
                "proof string is a FAIL, identical to an assertion failure"
            )
        elif count > 1:
            verdict = "FAIL"
            reason = (
                f"the proof string appeared {count} times; a duplicate means the "
                "log cannot support the claim that this specific check passed"
            )
        else:
            verdict = "PASS"
            reason = "unique execution proof string present"
        checks.append({"check_id": check, "verdict": verdict, "reason": reason})

    all_passed = all(c["verdict"] == "PASS" for c in checks)
    return {
        "schema_version": "study5-eq1-proof-verification-v1",
        "rule": "OD-003",
        "verified_at_utc": utc_now(),
        "expected_check_count": len(expected),
        "expected_checks_enumerated_in_advance": True,
        "checks": checks,
        "missing_proof_strings": missing,
        "duplicated_proof_strings": duplicated,
        "explicit_failures": explicit_failures,
        "unexpected_proof_strings": unexpected,
        "exit_code_used_as_evidence_of_execution": False,
        "all_checks_passed": all_passed,
        "verdict": "PASS" if all_passed else "FAIL",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, help="committed log to read")
    parser.add_argument(
        "--expect",
        required=True,
        help="JSON file listing the expected check ids, enumerated in advance",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    log_path = Path(args.log)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    expected = json.loads(Path(args.expect).read_text(encoding="utf-8"))
    if isinstance(expected, dict):
        expected = expected["expected_checks"]

    report = judge(log_text, list(expected))
    report["log"] = str(args.log)
    report["log_sha256"] = hashlib.sha256(log_path.read_bytes()).hexdigest()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=1) + "\n"
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    print(f"{args.out}  sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    for check in report["checks"]:
        print(f"  {check['verdict']:<4} {check['check_id']}: {check['reason']}")
    print(f"VERDICT: {report['verdict']}")
    return 0 if report["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
