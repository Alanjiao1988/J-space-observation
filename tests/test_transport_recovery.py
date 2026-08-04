"""Prospective invariants for the Phase 1.0D transport recovery."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTHORITY = (
    REPO_ROOT
    / "docs"
    / "prompts"
    / "phase1_0d_review_only_transport_recovery_prompt.md"
)
AUTHORITY_SHA256 = (
    "dc350039f118cb5931dab08fd65e24ed169757c472898b7dbe8d27eb3ce2f92b"
)
V1_ROLLUP = "436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd"
V2_ROLLUP = "ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a"


def _load(module_name: str, relative: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v1 = _load("recovery_v1_protected", "scripts/phase1_0d_protected_bytes.py")
v2 = _load("recovery_v2_protected", "scripts/phase1_0d_rv2_protected_bytes.py")


def test_the_recovery_authority_is_frozen_byte_for_byte():
    assert hashlib.sha256(AUTHORITY.read_bytes()).hexdigest() == AUTHORITY_SHA256


def test_both_protected_records_remain_exact():
    v1_document = v1.load_baseline(REPO_ROOT / v1.BASELINE_FILENAME)
    v2_document = v2.load_baseline(REPO_ROOT / v2.BASELINE_FILENAME)
    assert v1_document["file_count"] == 152
    assert v1_document["rollup_sha256"] == V1_ROLLUP
    assert v2_document["file_count"] == 36
    assert v2_document["rollup_sha256"] == V2_ROLLUP
    assert v1.verify(REPO_ROOT, REPO_ROOT / v1.BASELINE_FILENAME) == []
    assert v2.verify(REPO_ROOT, REPO_ROOT / v2.BASELINE_FILENAME) == []


def test_recovery_records_use_new_ids_without_rewriting_old_records():
    decision = (REPO_ROOT / "docs" / "decision_log.md").read_text(encoding="utf-8")
    limitations = (REPO_ROOT / "paper" / "limitations_ledger.md").read_text(
        encoding="utf-8"
    )
    methods = (REPO_ROOT / "paper" / "methods_ledger.md").read_text(encoding="utf-8")
    assert decision.count("## D28 ") == 1
    assert limitations.count("## L-54 ") == 1
    assert methods.count("## M-18 ") == 1
    assert AUTHORITY_SHA256 in decision
    assert "unquantifiable prior-response resampling exposure" in limitations
    assert "provider_calls=0" in methods


def test_authorization_does_not_advance_cl05():
    matrix = (REPO_ROOT / "paper" / "claim_evidence_matrix.md").read_text(
        encoding="utf-8"
    )
    note = matrix[matrix.index("**2026-08-05 — one capacity-gated") :]
    assert AUTHORITY_SHA256 in note
    assert "CL-05 remains\n`preliminary`" in note
    assert "Authorization is not evidence" in note


def test_the_authority_forbids_pre_certificate_inference_and_a_second_recovery():
    text = AUTHORITY.read_text(encoding="utf-8")
    assert "explicit provider_calls=0" in text
    assert "there is no second recovery execution" in text
    assert "Do not run:" in text
    for forbidden in (
        "provider qualification",
        "the 20-fixture smoke or any subset of it",
        "a one-row target probe",
        "a dry-run chat completion",
    ):
        assert forbidden in text
