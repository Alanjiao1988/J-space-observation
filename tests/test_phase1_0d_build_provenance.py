"""Tests for the Phase 1.0D build-provenance tool.

These establish that the tool detects drift.  They establish nothing about
whether any image was ever built, and nothing about the model.
"""

from __future__ import annotations

import json
import shutil
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


def test_the_committed_record_is_the_hash_of_the_committed_source(tmp_path):
    """Recorded bytes stay exact while authorized later files fail closed."""

    record = REPO_ROOT / provenance.PROVENANCE_FILENAME
    if not record.exists():
        pytest.skip("the provenance record has not been emitted from Azure yet")

    context = tmp_path / "recorded-phase1-0d-context"
    document = json.loads(record.read_text(encoding="utf-8"))
    for entry in document["files"]:
        relative = Path(entry["path"])
        source = REPO_ROOT / relative
        target = context / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    assert provenance.verify_image_context(context, record) == []

    current_failures = provenance.verify_image_context(REPO_ROOT, record)
    authorized_later_modules = {
        "src/jspace_observation/jlens_s2_corpus.py",
        "src/jspace_observation/jlens_s2_protocol.py",
        "src/jspace_observation/jlens_s2_runtime.py",
        "src/jspace_observation/jlens_s3_e0_runtime.py",
        "src/jspace_observation/jlens_s3_protocol.py",
        "src/jspace_observation/study2_protocol.py",
        "src/jspace_observation/study2_stage_t.py",
        "src/jspace_observation/study2_task_bank.py",
    }
    expected_file_failures = {
        f"image carries an unrecorded file: {path}"
        for path in authorized_later_modules
    }
    observed_file_failures = {
        failure
        for failure in current_failures
        if failure.startswith("image carries an unrecorded file: ")
    }
    assert observed_file_failures == expected_file_failures
    assert len(current_failures) == len(expected_file_failures) + 1
    assert sum(
        failure.startswith("bundle digest is ") for failure in current_failures
    ) == 1


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


BUILD_SCRIPT = REPO_ROOT / "infra/azure/scripts/18_build_phase1_0d_confirmation.sh"
RUN_SCRIPT = REPO_ROOT / "infra/azure/scripts/19_run_phase1_0d_confirmation.sh"


def _script(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_neither_launcher_touches_the_phase_1_0c_namespace():
    for path in (BUILD_SCRIPT, RUN_SCRIPT):
        text = _script(path)
        assert "j-space-observation-calibration" not in text
        assert "phase1-headroom-calibration" not in text
        assert "job-jspace-p10c-headroom" not in text


def test_the_run_launcher_starts_the_phase_1_0d_entrypoint_in_generate_mode():
    text = _script(RUN_SCRIPT)
    assert "run_phase1_0d_confirmation.py --mode generate" in text
    assert "--repo-root /workspace" in text
    assert provenance.IMAGE_REPOSITORY in text
    assert 'REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-21600}"' in text
    assert (
        'GENERATION_TIMEOUT_SECONDS="${GENERATION_TIMEOUT_SECONDS:-21300}"'
        in text
    )
    assert "exact 21600/21300 second timeout envelope" in text
    assert "container command differs from the registered generation command" in text
    assert "container environment differs from the exact registered values" in text


def test_the_run_launcher_uses_the_existing_locked_generation_image():
    text = _script(RUN_SCRIPT)
    assert (
        'LOCKED_IMAGE_TAG="9cde1d95ffda36698a0ddf558a9358f3337dd711"'
        in text
    )
    assert (
        'LOCKED_IMAGE_DIGEST="sha256:'
        '1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4"'
        in text
    )
    assert 'PROJECT_SHA="${PROJECT_SHA:-$LOCKED_IMAGE_TAG}"' in text
    assert '[[ "$PROJECT_SHA" != "$LOCKED_IMAGE_TAG" ]]' in text
    assert '[[ "$IMAGE_DIGEST" != "$LOCKED_IMAGE_DIGEST" ]]' in text


def test_the_run_launcher_refuses_a_platform_retry_or_a_second_replica():
    text = _script(RUN_SCRIPT)
    assert '"replicaRetryLimit": 0' in text
    assert '"parallelism": 1' in text
    assert '"replicaCompletionCount": 1' in text


def test_the_run_launcher_enforces_one_generation_execution():
    text = _script(RUN_SCRIPT)
    assert (
        'GENERATION_LOCK_BLOB="${BLOB_PREFIX}/generation-execution-lock.json"'
        in text
    )
    assert '"artifact":"phase1_0d_generation_execution_lock"' in text
    assert "--overwrite false" in text
    assert "only one create-only upload can authorize an execution" in text
    assert "sole Phase 1.0D generation execution is already claimed" in text
    assert "use a new run ID" not in text


def test_the_run_launcher_requires_the_exact_committed_v2_smoke_license():
    text = _script(RUN_SCRIPT)
    for binding in (
        "SMOKE_RUN_ID",
        "SMOKE_RECEIPT_SHA256",
        "SMOKE_MANIFEST_SHA256",
        "REVIEW_V2_CODE_COMMIT",
        "REVIEW_V2_IMAGE_DIGEST",
    ):
        assert binding in text
    assert "verify_phase1_0d_rv2_gate.py" in text
    assert "Exactly one committed v2 gate receipt must license generation" in text
    assert 'cat-file", "blob"' in text
    assert "cat-file blob" in text
    assert "phase1_0d_protected_bytes.py" in text
    assert "phase1_0d_rv2_protected_bytes.py" in text
    assert "V2 review or gate-verification bytes changed after the smoke image" in text
    assert "The committed gate checkpoint must be pushed to origin/main" in text
    assert "Committed v2 smoke gate differs from the create-only Blob evidence" in text
    assert '"rv2_smoke_receipt_sha256":"%s"' in text


def test_the_run_launcher_requires_an_empty_target_prefix():
    text = _script(RUN_SCRIPT)
    assert 'TARGET_PREFIX="${BLOB_PREFIX}/${RUN_ID}/"' in text
    assert "--prefix \"$TARGET_PREFIX\"" in text
    assert "--query 'length(@)'" in text
    assert "Target prefix is not empty" in text


def test_the_run_launcher_refuses_an_unlocked_image():
    text = _script(RUN_SCRIPT)
    assert "Phase 1.0D image is not locked" in text
    for attribute in ("TAG_WRITE_ENABLED", "TAG_DELETE_ENABLED",
                      "MANIFEST_WRITE_ENABLED", "MANIFEST_DELETE_ENABLED"):
        assert attribute in text


def test_the_run_launcher_carries_no_storage_credential():
    """Blob access is managed identity only; a key would make the run deniable."""

    text = _script(RUN_SCRIPT)
    assert "AZURE_CLIENT_ID" in text
    assert "credential-bearing variables present" in text
    environment_block = text.split("environment = [", 1)[1].split("]", 1)[0]
    for forbidden in ("ACCOUNT_KEY", "SAS", "CONNECTION_STRING"):
        assert forbidden not in environment_block.upper()


def test_the_build_script_locks_the_image_and_verifies_the_lock():
    text = _script(BUILD_SCRIPT)
    assert "--write-enabled false --delete-enabled false" in text
    assert "is still enabled after locking" in text


def test_the_build_script_refuses_a_dirty_tree_and_a_reused_tag():
    text = _script(BUILD_SCRIPT)
    assert "Refusing to build a dirty worktree" in text
    assert "already exists; use a new commit" in text


def test_the_build_script_requires_the_committed_provenance_record():
    text = _script(BUILD_SCRIPT)
    assert provenance.PROVENANCE_FILENAME in text
    assert "build-provenance record is missing" in text


def test_both_launchers_state_what_the_artifact_does_not_establish():
    assert "establishes nothing about the model" in _script(BUILD_SCRIPT)
    assert "AWAITING_SEMANTIC_REVIEW" in _script(RUN_SCRIPT)
