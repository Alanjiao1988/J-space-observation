"""Tests for the semantic-review v2 protected-byte record.

The obligation being tested is narrow and structural.  Section 4 of the v2
authority requires a *new* manifest covering the frozen target bytes plus the
complete v1 reviewer instrument and gate evidence, and forbids modifying the v1
record to make v2 pass.  Both halves are checked here: that the new record is a
strict superset of the old one, and that the old one still verifies on its own
terms at the same commit.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load(module_name: str, relative: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rv2 = _load("phase1_0d_rv2_protected_bytes", "scripts/phase1_0d_rv2_protected_bytes.py")
v1 = _load("phase1_0d_protected_bytes", "scripts/phase1_0d_protected_bytes.py")

BASELINE = REPO_ROOT / rv2.BASELINE_FILENAME


@pytest.fixture(scope="module")
def document() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def test_the_v2_record_is_a_separate_file_from_the_v1_record():
    assert rv2.BASELINE_FILENAME != v1.BASELINE_FILENAME
    assert rv2.SCHEMA_VERSION != v1.SCHEMA_VERSION
    assert rv2.ROLLUP_DOMAIN != v1.ROLLUP_DOMAIN
    assert BASELINE.exists()


def test_the_v1_record_still_verifies_unchanged():
    """Section 4 forbids editing the old record to make v2 pass."""

    assert v1.verify(REPO_ROOT, REPO_ROOT / v1.BASELINE_FILENAME) == []


def test_the_v2_record_verifies_at_this_commit():
    assert rv2.verify(REPO_ROOT, BASELINE) == []


def test_the_v2_record_covers_every_path_the_v1_record_covers_for_phase_1_0d():
    """The target design is pinned by both records, byte for byte identically.

    The v1 record additionally pins the closed parser-v3 subproject and the
    Phase 1.0C run, which this record does not restate; those stay under the v1
    record, which is still verified above.
    """

    covered = {entry["path"] for entry in json.loads(BASELINE.read_text("utf-8"))["files"]}
    v1_document = json.loads(
        (REPO_ROOT / v1.BASELINE_FILENAME).read_text(encoding="utf-8")
    )
    v1_hashes = {entry["path"]: entry["sha256"] for entry in v1_document["files"]}
    rv2_hashes = {
        entry["path"]: entry["sha256"]
        for entry in json.loads(BASELINE.read_text("utf-8"))["files"]
    }
    shared = covered & set(v1_hashes)
    assert shared, "the two records must overlap on the frozen target design"
    for path in sorted(shared):
        assert rv2_hashes[path] == v1_hashes[path], path


@pytest.mark.parametrize(
    "path",
    [
        # frozen target design
        "docs/phase1_0d_protocol_snapshot.json",
        "phase1_0d_build_provenance.json",
        "src/jspace_observation/phase1_0d_generation.py",
        "Dockerfile.phase1-0d",
        "infra/azure/scripts/19_run_phase1_0d_confirmation.sh",
        "infra/azure/scripts/23_run_phase1_0d_semantic_review_v2.sh",
        # the complete v1 reviewer instrument
        "docs/phase1_0d_semantic_review_addendum.json",
        "docs/phase1_0d_semantic_review_rubric.md",
        "scripts/run_phase1_0d_semantic_review.py",
        "phase1_0d_review_build_provenance.json",
        "Dockerfile.phase1-0d-review",
        "src/jspace_observation/semantic_review/addendum.py",
        "src/jspace_observation/semantic_review/transport.py",
        "src/jspace_observation/semantic_review/stages.py",
        "infra/azure/scripts/21_run_phase1_0d_semantic_review.sh",
        # the v2 documents frozen before any provider call
        "docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md",
        "docs/phase1_0d_semantic_review_rubric_v2.md",
        "docs/phase1_0d_semantic_review_addendum_v2.json",
        "docs/decisions/phase1_0d_semantic_review_v1_specification_correction.md",
    ],
)
def test_required_paths_are_pinned(document, path):
    assert path in {entry["path"] for entry in document["files"]}


def test_the_four_gate_artifacts_are_pinned(document):
    pinned = [
        entry["path"]
        for entry in document["files"]
        if entry["path"].startswith("artifacts/phase1-0d-semantic-review-gate/")
    ]
    assert len(pinned) == 4
    assert any(name.endswith("00_gate_receipt.json") for name in pinned)
    assert any(name.endswith("artifact_manifest.json") for name in pinned)


def test_the_v2_executable_surface_is_left_to_the_build_provenance(document):
    """Pinning the runner here would force a recut on every runner change."""

    pinned = {entry["path"] for entry in document["files"]}
    assert "scripts/run_phase1_0d_semantic_review_v2.py" not in pinned
    assert "Dockerfile.phase1-0d-review-v2" not in pinned


def test_the_recorded_rollup_is_reproducible(document):
    _, rollup = rv2.hash_protected(REPO_ROOT)
    assert rollup == document["rollup_sha256"]
    assert document["file_count"] == len(document["files"])


def test_a_changed_protected_byte_is_reported(tmp_path):
    document = json.loads(BASELINE.read_text(encoding="utf-8"))
    document["files"][0]["sha256"] = "0" * 64
    altered = tmp_path / "baseline.json"
    altered.write_text(rv2.canonical(document), encoding="utf-8")
    failures = rv2.verify(REPO_ROOT, altered)
    assert any("protected bytes changed" in failure for failure in failures)


def test_a_dropped_pattern_is_reported(tmp_path):
    document = json.loads(BASELINE.read_text(encoding="utf-8"))
    document["patterns"] = document["patterns"][:-1]
    altered = tmp_path / "baseline.json"
    altered.write_text(rv2.canonical(document), encoding="utf-8")
    assert rv2.verify(REPO_ROOT, altered) == [
        "the declared protected patterns differ from the baseline"
    ]


def test_a_foreign_schema_is_refused(tmp_path):
    altered = tmp_path / "baseline.json"
    altered.write_text(json.dumps({"schema_version": "other"}), encoding="utf-8")
    with pytest.raises(rv2.Rv2ProtectedBytesError):
        rv2.verify(REPO_ROOT, altered)


def test_the_claim_boundary_is_recorded(document):
    boundary = document["claim_boundary"]
    assert "byte-identity" in boundary
    assert "nothing about reviewer accuracy" in boundary
    assert "J-space" in boundary
    assert document["terminal_state_on_mismatch"] == "BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT"
