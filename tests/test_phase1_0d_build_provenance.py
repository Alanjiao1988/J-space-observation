"""Tests for the Phase 1.0D build-provenance tool.

These establish that the tool detects drift.  They establish nothing about
whether any image was ever built, and nothing about the model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import phase1_0d_build_provenance as provenance  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
COMMIT = "0" * 40


def _fixture(root: Path) -> Path:
    """Build a miniature repository that satisfies every declared glob."""

    for pattern in provenance.BUNDLE_GLOBS:
        if "*" in pattern:
            target = root / pattern.replace("*", "sample")
        else:
            target = root / pattern
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"content of {target.name}\n", encoding="utf-8")
    return root


def test_every_declared_glob_matches_something_in_the_real_repository():
    """A pattern that matches nothing is a silently empty provenance record."""

    files = provenance.resolve_bundle_files(REPO_ROOT)
    assert len(files) == len(set(files))
    names = {path.relative_to(REPO_ROOT).as_posix() for path in files}
    assert provenance.DOCKERFILE in names
    assert "scripts/run_phase1_0d_confirmation.py" in names
    assert "src/jspace_observation/phase1_0d_generation.py" in names
    assert "src/jspace_observation/phase1_0d_confirmation.py" in names


def test_a_missing_pattern_is_an_error_not_an_empty_list(tmp_path):
    with pytest.raises(provenance.ProvenanceError, match="matched no file"):
        provenance.resolve_bundle_files(tmp_path)


def test_the_bundle_digest_is_stable_across_repeated_hashing(tmp_path):
    _fixture(tmp_path)
    first = provenance.hash_bundle(tmp_path)[1]
    second = provenance.hash_bundle(tmp_path)[1]
    assert first == second


def test_the_bundle_digest_ignores_the_checkout_line_endings(tmp_path):
    lf = _fixture(tmp_path / "lf")
    crlf = _fixture(tmp_path / "crlf")
    for path in provenance.resolve_bundle_files(crlf):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert provenance.hash_bundle(lf)[1] == provenance.hash_bundle(crlf)[1]


def test_editing_one_byte_changes_the_bundle_digest(tmp_path):
    _fixture(tmp_path)
    before = provenance.hash_bundle(tmp_path)[1]
    target = tmp_path / "scripts" / "run_phase1_0d_confirmation.py"
    target.write_text("edited\n", encoding="utf-8")
    assert provenance.hash_bundle(tmp_path)[1] != before


def test_the_document_names_what_it_does_not_establish(tmp_path):
    document = provenance.build_document(_fixture(tmp_path), COMMIT)
    assert document["not_established"]
    assert "hidden reasoning" in document["claim_boundary"]
    assert document["protocol_sha256"] == provenance.PROTOCOL_SHA256
    assert document["code_commit"] == COMMIT
    assert document["file_count"] == len(document["files"])


def test_a_short_commit_is_refused(tmp_path):
    with pytest.raises(provenance.ProvenanceError, match="40-character"):
        provenance.build_document(_fixture(tmp_path), "abc123")


def test_an_unchanged_context_verifies(tmp_path):
    root = _fixture(tmp_path)
    record = tmp_path / "record.json"
    record.write_text(
        provenance.canonical(provenance.build_document(root, COMMIT)), encoding="utf-8"
    )
    assert provenance.verify_image_context(root, record) == []


def test_an_added_file_is_reported(tmp_path):
    root = _fixture(tmp_path)
    record = tmp_path / "record.json"
    record.write_text(
        provenance.canonical(provenance.build_document(root, COMMIT)), encoding="utf-8"
    )
    (root / "src" / "jspace_observation" / "extra.py").write_text("x\n", encoding="utf-8")
    failures = provenance.verify_image_context(root, record)
    assert any("unrecorded file" in failure for failure in failures)


def test_a_removed_file_is_reported(tmp_path):
    root = _fixture(tmp_path)
    record = tmp_path / "record.json"
    record.write_text(
        provenance.canonical(provenance.build_document(root, COMMIT)), encoding="utf-8"
    )
    (root / "data" / "phase1_task_headroom_candidates.jsonl").unlink()
    with pytest.raises(provenance.ProvenanceError, match="matched no file"):
        provenance.verify_image_context(root, record)


def test_an_edited_file_is_reported_with_its_path(tmp_path):
    root = _fixture(tmp_path)
    record = tmp_path / "record.json"
    record.write_text(
        provenance.canonical(provenance.build_document(root, COMMIT)), encoding="utf-8"
    )
    (root / "scripts" / "run_phase1_0d_confirmation.py").write_text("x\n", encoding="utf-8")
    failures = provenance.verify_image_context(root, record)
    assert any("scripts/run_phase1_0d_confirmation.py" in failure for failure in failures)


def test_a_record_for_a_different_image_is_refused(tmp_path):
    root = _fixture(tmp_path)
    document = provenance.build_document(root, COMMIT)
    document["image_repository"] = "j-space-observation-calibration"
    record = tmp_path / "record.json"
    record.write_text(provenance.canonical(document), encoding="utf-8")
    with pytest.raises(provenance.ProvenanceError, match="different image repository"):
        provenance.verify_image_context(root, record)


def test_a_record_carrying_a_stale_protocol_hash_is_refused(tmp_path):
    """The build must fail if the protocol was refrozen after the record."""

    root = _fixture(tmp_path)
    document = provenance.build_document(root, COMMIT)
    document["protocol_sha256"] = "f" * 64
    record = tmp_path / "record.json"
    record.write_text(provenance.canonical(document), encoding="utf-8")
    with pytest.raises(provenance.ProvenanceError, match="refrozen"):
        provenance.verify_image_context(root, record)


def test_the_committed_record_is_the_hash_of_the_committed_source():
    """The point of the whole tool: the record must describe this repository."""

    record = REPO_ROOT / provenance.PROVENANCE_FILENAME
    if not record.exists():
        pytest.skip("the provenance record has not been emitted from Azure yet")
    assert provenance.verify_image_context(REPO_ROOT, record) == []


def test_the_committed_record_matches_the_frozen_protocol():
    record = REPO_ROOT / provenance.PROVENANCE_FILENAME
    if not record.exists():
        pytest.skip("the provenance record has not been emitted from Azure yet")
    document = json.loads(record.read_text(encoding="utf-8"))
    assert document["protocol_sha256"] == provenance.PROTOCOL_SHA256


def test_the_bare_snapshot_hash_is_not_the_frozen_hash():
    """Name the trap: the frozen hash only reproduces with the selection in it."""

    from jspace_observation.phase1_0d_confirmation import protocol_snapshot

    assert protocol_snapshot()["protocol_sha256"] != provenance.PROTOCOL_SHA256


def test_verify_protocol_reads_the_real_frozen_protocol():
    assert provenance.verify_protocol(REPO_ROOT) == []


def test_an_unpinned_requirement_is_refused(tmp_path):
    lock = tmp_path / "requirements.txt"
    lock.write_text("transformers>=4\n", encoding="utf-8")
    with pytest.raises(provenance.ProvenanceError, match="not pinned exactly"):
        provenance.parse_pins(lock)


def test_comments_and_blank_lines_are_not_requirements(tmp_path):
    lock = tmp_path / "requirements.txt"
    lock.write_text("# note\n\ntransformers==4.46.3  # why\n", encoding="utf-8")
    assert provenance.parse_pins(lock) == {"transformers": "4.46.3"}


def test_the_real_lock_pins_every_line_exactly():
    pins = provenance.parse_pins(REPO_ROOT / provenance.REQUIREMENTS)
    assert pins["transformers"] == provenance.EXPECTED_TRANSFORMERS_VERSION


def test_a_missing_install_is_reported_rather_than_assumed(tmp_path):
    lock = tmp_path / "requirements.txt"
    lock.write_text("a-package-that-is-not-installed==1.2.3\n", encoding="utf-8")
    failures = provenance.verify_runtime(lock)
    assert any("is not installed" in failure for failure in failures)


def test_the_dockerfile_verifies_the_context_the_protocol_and_the_runtime():
    text = (REPO_ROOT / provenance.DOCKERFILE).read_text(encoding="utf-8")
    assert "verify-runtime" in text
    assert "verify-image-context" in text
    assert "verify-protocol" in text
    assert provenance.BASE_IMAGE_DIGEST in text
    assert provenance.PROTOCOL_SHA256 in text


def test_the_dockerfile_default_command_cannot_touch_the_model():
    text = (REPO_ROOT / provenance.DOCKERFILE).read_text(encoding="utf-8")
    command = text.split("CMD ", 1)[1]
    assert '"--mode", "plan"' in command
    assert "generate" not in command


def test_the_dockerfile_copies_every_file_the_bundle_records():
    """A recorded file the Dockerfile never copies fails only at build time."""

    text = (REPO_ROOT / provenance.DOCKERFILE).read_text(encoding="utf-8")
    copied = "\n".join(
        line for line in text.splitlines() if line.startswith(("COPY", "     "))
    )
    for path in provenance.resolve_bundle_files(REPO_ROOT):
        relative = path.relative_to(REPO_ROOT).as_posix()
        parent = str(Path(relative).parent.as_posix())
        assert relative in copied or f"{parent}/" in copied, relative


def test_the_image_is_not_the_calibration_image():
    """Phase 1.0C must not be overwritten or reinterpreted by this work."""

    assert provenance.IMAGE_REPOSITORY != "j-space-observation-calibration"
    text = (REPO_ROOT / provenance.DOCKERFILE).read_text(encoding="utf-8")
    assert "must not be overwritten" in text
