"""Tests for the section 2.3 protected-byte baseline.

These are drift tests, not correctness tests: they establish that the files the
authority forbids changing still hold the bytes recorded when the baseline was
cut, and that the checker actually notices when they do not.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

_SPEC = importlib.util.spec_from_file_location(
    "phase1_0d_protected_bytes", REPO_ROOT / "scripts" / "phase1_0d_protected_bytes.py"
)
assert _SPEC and _SPEC.loader
protected = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(protected)

BASELINE = REPO_ROOT / protected.BASELINE_FILENAME


def _tiny_tree(root: Path) -> None:
    """A miniature repository carrying one file per declared pattern."""

    for pattern in protected.PROTECTED_GLOBS:
        relative = pattern.replace("**/*", "sample.json").replace("*", "sample")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"content of {relative}\n", encoding="utf-8")


def test_the_committed_baseline_still_describes_this_repository():
    """The whole point: protected bytes have not moved."""

    assert protected.verify(REPO_ROOT, BASELINE) == []


def test_the_baseline_names_what_it_does_not_establish():
    document = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert "establishes nothing about their scientific correctness" in str(
        document["claim_boundary"]
    )
    assert document["terminal_state_on_mismatch"] == "BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT"


def test_every_protected_file_named_by_the_authority_is_covered():
    document = json.loads(BASELINE.read_text(encoding="utf-8"))
    covered = {str(entry["path"]) for entry in document["files"]}
    for required in (
        "docs/phase1_0d_protocol_snapshot.json",
        "phase1_0d_build_provenance.json",
        "src/jspace_observation/phase1_0d_confirmation.py",
        "src/jspace_observation/phase1_0d_execution.py",
        "src/jspace_observation/phase1_0d_generation.py",
        "scripts/run_phase1_0d_confirmation.py",
        "artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/02_records.jsonl",
        "tests/test_parser_v3_seal_job.py",
    ):
        assert required in covered, required


def test_the_frozen_build_bundle_source_is_protected_too():
    """It hashes itself into the protected record, so it cannot be edited."""

    document = json.loads(BASELINE.read_text(encoding="utf-8"))
    covered = {str(entry["path"]) for entry in document["files"]}
    assert "scripts/phase1_0d_build_provenance.py" in covered
    assert (
        "docs/prompts/phase_science_restart_after_parser_closure_prompt.md" in covered
    )


def test_the_new_semantic_review_code_is_not_inside_the_frozen_build_bundle():
    """A guard against reintroducing the trap this layout exists to avoid.

    ``phase1_0d_build_provenance.json`` is protected and records a bundle
    resolved from ``src/jspace_observation/*.py``.  Any new module placed
    directly in that directory would change the bundle digest and break a
    protected record that must not be re-emitted, so the semantic-review code
    lives in a subpackage instead.
    """

    spec = importlib.util.spec_from_file_location(
        "phase1_0d_build_provenance",
        REPO_ROOT / "scripts" / "phase1_0d_build_provenance.py",
    )
    assert spec and spec.loader
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)

    baked = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in build.resolve_bundle_files(REPO_ROOT)
    }
    review = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "src" / "jspace_observation" / "semantic_review").glob(
            "*.py"
        )
    }
    assert review, "the semantic-review subpackage should exist"
    assert baked.isdisjoint(review)


def test_an_edited_protected_file_is_reported(tmp_path):
    _tiny_tree(tmp_path)
    document = protected.build_document(tmp_path, "0" * 40)
    baseline = tmp_path / "baseline.json"
    baseline.write_text(protected.canonical(document), encoding="utf-8")
    assert protected.verify(tmp_path, baseline) == []

    victim = tmp_path / "docs" / "phase1_0d_protocol_snapshot.json"
    victim.write_text("tampered\n", encoding="utf-8")
    failures = protected.verify(tmp_path, baseline)
    assert any("protected bytes changed" in line for line in failures)
    assert any("rollup is" in line for line in failures)


def test_a_deleted_protected_file_is_reported(tmp_path):
    _tiny_tree(tmp_path)
    document = protected.build_document(tmp_path, "0" * 40)
    baseline = tmp_path / "baseline.json"
    baseline.write_text(protected.canonical(document), encoding="utf-8")

    (tmp_path / "phase1_0d_build_provenance.json").unlink()
    with pytest.raises(protected.ProtectedBytesError, match="matched no file"):
        protected.verify(tmp_path, baseline)


def test_a_new_file_under_a_protected_pattern_is_reported(tmp_path):
    _tiny_tree(tmp_path)
    document = protected.build_document(tmp_path, "0" * 40)
    baseline = tmp_path / "baseline.json"
    baseline.write_text(protected.canonical(document), encoding="utf-8")

    intruder = tmp_path / "tests" / "test_parser_v3_smuggled.py"
    intruder.write_text("# added later\n", encoding="utf-8")
    failures = protected.verify(tmp_path, baseline)
    assert any("a new file appeared" in line for line in failures)


def test_line_endings_do_not_change_the_rollup(tmp_path):
    lf = tmp_path / "lf"
    crlf = tmp_path / "crlf"
    _tiny_tree(lf)
    _tiny_tree(crlf)
    for path in crlf.rglob("*"):
        if path.is_file():
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert protected.hash_protected(lf)[1] == protected.hash_protected(crlf)[1]


def test_a_short_commit_is_refused(tmp_path):
    _tiny_tree(tmp_path)
    with pytest.raises(protected.ProtectedBytesError, match="full sha1"):
        protected.build_document(tmp_path, "abc123")


def test_the_cli_exits_nonzero_on_drift(tmp_path, capsys):
    _tiny_tree(tmp_path)
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        protected.canonical(protected.build_document(tmp_path, "0" * 40)),
        encoding="utf-8",
    )
    argv = ["verify", "--project-root", str(tmp_path), "--baseline", str(baseline)]
    assert protected.main(argv) == 0
    assert "PROTECTED_BYTES_OK=1" in capsys.readouterr().out

    (tmp_path / "Dockerfile.phase1-0d").write_text("tampered\n", encoding="utf-8")
    assert protected.main(argv) == 1
    assert "BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT" in capsys.readouterr().out
