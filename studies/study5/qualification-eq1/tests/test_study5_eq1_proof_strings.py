"""Tests for the OD-003 execution proof-string verifier.

OD-003 exists because IMG-001 showed that a verification step can silently not
run and still exit 0. The tests below are therefore mostly about the *absence*
of evidence, which is the failure mode that matters: a check with no proof
string must fail exactly as loudly as a check whose assertion failed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "study5_eq1_proofs", _TOOLS / "verify_proof_strings.py"
)
assert _SPEC is not None and _SPEC.loader is not None
proofs = importlib.util.module_from_spec(_SPEC)
sys.modules["study5_eq1_proofs"] = proofs
_SPEC.loader.exec_module(proofs)

EXPECTED = ["S1.A", "S1.B", "S1.C"]


def test_all_proof_strings_present_passes() -> None:
    log = "noise\nP1-CHECK-S1.A PASSED\nP1-CHECK-S1.B PASSED\nP1-CHECK-S1.C PASSED\n"
    result = proofs.judge(log, EXPECTED)
    assert result["verdict"] == "PASS"
    assert result["missing_proof_strings"] == []


def test_a_missing_proof_string_is_a_fail() -> None:
    """The IMG-001 case: the check never ran, so nothing was emitted."""

    log = "P1-CHECK-S1.A PASSED\nP1-CHECK-S1.C PASSED\n"
    result = proofs.judge(log, EXPECTED)
    assert result["verdict"] == "FAIL"
    assert result["missing_proof_strings"] == ["S1.B"]
    verdicts = {c["check_id"]: c["verdict"] for c in result["checks"]}
    assert verdicts["S1.B"] == "FAIL"


def test_an_empty_log_fails_every_check() -> None:
    """A step that produced no output at all must not read as success."""

    result = proofs.judge("", EXPECTED)
    assert result["verdict"] == "FAIL"
    assert result["missing_proof_strings"] == EXPECTED


def test_an_explicit_failure_line_is_a_fail() -> None:
    log = "P1-CHECK-S1.A PASSED\nP1-CHECK-S1.B FAILED: tensors differ\nP1-CHECK-S1.C PASSED\n"
    result = proofs.judge(log, EXPECTED)
    assert result["verdict"] == "FAIL"
    assert result["explicit_failures"] == ["S1.B"]


def test_a_failure_line_beats_a_passed_line_for_the_same_check() -> None:
    """A check that reported both cannot be treated as having passed."""

    log = "P1-CHECK-S1.A PASSED\nP1-CHECK-S1.A FAILED: later contradiction\n"
    result = proofs.judge(log, ["S1.A"])
    assert result["verdict"] == "FAIL"


def test_a_duplicated_proof_string_is_a_fail() -> None:
    """Two identical proofs mean the log cannot identify which run passed."""

    log = "P1-CHECK-S1.A PASSED\nP1-CHECK-S1.A PASSED\n"
    result = proofs.judge(log, ["S1.A"])
    assert result["verdict"] == "FAIL"
    assert result["duplicated_proof_strings"] == ["S1.A"]


def test_expected_checks_are_enumerated_in_advance() -> None:
    """A silently deleted check must be caught, not simply never looked for."""

    log = "P1-CHECK-S1.A PASSED\n"
    result = proofs.judge(log, EXPECTED)
    assert result["expected_check_count"] == 3
    assert set(result["missing_proof_strings"]) == {"S1.B", "S1.C"}


def test_an_unexpected_proof_string_is_surfaced_but_not_fatal() -> None:
    log = "\n".join(f"P1-CHECK-{c} PASSED" for c in EXPECTED) + "\nP1-CHECK-EXTRA PASSED\n"
    result = proofs.judge(log, EXPECTED)
    assert result["verdict"] == "PASS"
    assert result["unexpected_proof_strings"] == ["EXTRA"]


def test_a_near_miss_string_does_not_count_as_a_proof() -> None:
    """Prose mentioning a check is not the check emitting its own proof."""

    for line in (
        "we would expect P1-CHECK-S1.A PASSED here",
        "P1-CHECK-S1.A PASS",
        "P1-CHECK-S1.A  passed",
        "# P1-CHECK-S1.A PASSED",
    ):
        assert proofs.judge(line + "\n", ["S1.A"])["verdict"] == "FAIL", line


def test_the_report_records_that_exit_code_was_not_used() -> None:
    log = "\n".join(f"P1-CHECK-{c} PASSED" for c in EXPECTED)
    result = proofs.judge(log, EXPECTED)
    assert result["exit_code_used_as_evidence_of_execution"] is False
    assert result["rule"] == "OD-003"
