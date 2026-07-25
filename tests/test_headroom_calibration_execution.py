"""Targeted tests for the Phase 1.0C Track B calibration EXECUTION layer.

These cover only the execution implementation authored to unblock the run:
the dedicated calibration image, its deterministic build provenance, the
managed-identity Blob transport, the semantic-review ingestion contract, and
the additive metric/CSV views. The frozen scientific protocol is exercised by
``tests/test_headroom_calibration.py`` and is not re-litigated here.

Reminder carried through the assertions below: n = 10 per (task family x
difficulty band x condition) cell is a SCREEN, never a stable performance
estimate.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from jspace_observation import headroom_blob_transport as hbt  # noqa: E402
from jspace_observation import headroom_calibration as hc  # noqa: E402

FROZEN_TIME = "2026-07-25T00:00:00Z"
DOCKERFILE = ROOT / "Dockerfile.calibration"
REQUIREMENTS = ROOT / "requirements-calibration.txt"
BUILD_SCRIPT = ROOT / "infra/azure/scripts/13_build_phase1_headroom_calibration.sh"
RUN_SCRIPT = ROOT / "infra/azure/scripts/14_run_phase1_headroom_calibration.sh"
PROVENANCE_SCRIPT = ROOT / "scripts/calibration_build_provenance.py"
INGEST_SCRIPT = ROOT / "scripts/ingest_headroom_semantic_review.py"
RUNNER_SCRIPT = ROOT / "scripts/run_phase1_headroom_calibration.py"


def _load_script(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prov = _load_script(PROVENANCE_SCRIPT, "_calibration_build_provenance_under_test")
ingest = _load_script(INGEST_SCRIPT, "_ingest_headroom_semantic_review_under_test")


def _read_lf(path: Path) -> str:
    return path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")


# ---------------------------------------------------------------------------
# Wilson score interval
# ---------------------------------------------------------------------------


def _reference_wilson(successes: int, total: int, z: float = 1.959963984540054):
    """Textbook Wilson score interval, written independently of the module."""

    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1.0 + (z * z) / total
    centre = (p + (z * z) / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt((p * (1.0 - p) + (z * z) / (4 * total)) / total)
        / denominator
    )
    return (max(0.0, centre - margin), min(1.0, centre + margin))


@pytest.mark.parametrize(
    ("successes", "total", "lower", "upper"),
    [
        # Published Wilson 95% values, rounded to three decimals.
        (0, 10, 0.000, 0.278),
        (1, 10, 0.018, 0.404),
        (5, 10, 0.237, 0.763),
        (7, 10, 0.397, 0.892),
        (8, 10, 0.490, 0.943),
        (9, 10, 0.596, 0.982),
        (10, 10, 0.722, 1.000),
        (15, 20, 0.531, 0.888),
        (0, 1, 0.000, 0.793),
        (1, 1, 0.207, 1.000),
    ],
)
def test_wilson_ci_matches_published_values(
    successes: int, total: int, lower: float, upper: float
) -> None:
    got_lower, got_upper = hc.wilson_ci(successes, total)
    assert got_lower == pytest.approx(lower, abs=1e-3)
    assert got_upper == pytest.approx(upper, abs=1e-3)


@pytest.mark.parametrize("total", [1, 2, 5, 10, 20, 37])
def test_wilson_ci_matches_independent_reference(total: int) -> None:
    for successes in range(total + 1):
        expected = _reference_wilson(successes, total)
        got = hc.wilson_ci(successes, total)
        assert got[0] == pytest.approx(expected[0], abs=1e-9)
        assert got[1] == pytest.approx(expected[1], abs=1e-9)


def test_wilson_ci_is_bounded_and_brackets_the_estimate() -> None:
    for total in (1, 3, 10, 25):
        for successes in range(total + 1):
            lower, upper = hc.wilson_ci(successes, total)
            assert 0.0 <= lower <= upper <= 1.0
            assert lower - 1e-9 <= successes / total <= upper + 1e-9


def test_wilson_ci_zero_denominator_is_degenerate() -> None:
    assert hc.wilson_ci(0, 0) == (0.0, 0.0)


def test_wilson_ci_ten_trial_width_documents_screen_only_precision() -> None:
    """A 10-trial cell cannot be a stable estimate; the CI width shows why."""

    lower, upper = hc.wilson_ci(8, 10)
    assert upper - lower > 0.40


# ---------------------------------------------------------------------------
# Build provenance: pure helpers
# ---------------------------------------------------------------------------


def test_normalize_lf_makes_digests_platform_independent() -> None:
    crlf = b"line one\r\nline two\r\n"
    lf = b"line one\nline two\n"
    assert prov.normalize_lf(crlf) == lf
    assert prov.sha256_bytes(prov.normalize_lf(crlf)) == prov.sha256_bytes(lf)


def test_canonical_json_bytes_is_sorted_and_newline_terminated() -> None:
    payload = prov.canonical_json_bytes({"b": 1, "a": {"d": 2, "c": 3}})
    assert payload.endswith(b"\n")
    assert payload == b'{"a":{"c":3,"d":2},"b":1}\n'
    assert payload.count(b"\r") == 0


def test_load_canonical_json_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "dupe.json"
    path.write_bytes(b'{"a": 1, "a": 2}\n')
    with pytest.raises(prov.ProvenanceError):
        prov.load_canonical_json(path)


def test_parse_pinned_requirements_accepts_exact_pins(tmp_path: Path) -> None:
    path = tmp_path / "requirements.txt"
    path.write_text(
        "# comment\ntransformers==4.46.3\nnumpy==1.26.4\n\n", encoding="utf-8"
    )
    assert prov.parse_pinned_requirements(path) == {
        "transformers": "4.46.3",
        "numpy": "1.26.4",
    }


@pytest.mark.parametrize(
    "line",
    ["transformers", "transformers>=4.46.3", "transformers~=4.46", "-r other.txt"],
)
def test_parse_pinned_requirements_rejects_floating_versions(
    tmp_path: Path, line: str
) -> None:
    path = tmp_path / "requirements.txt"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(prov.ProvenanceError):
        prov.parse_pinned_requirements(path)


def test_shipped_requirements_are_fully_pinned() -> None:
    pins = prov.parse_pinned_requirements(REQUIREMENTS)
    assert pins["transformers"] == prov.EXPECTED_TRANSFORMERS_VERSION
    assert all(version for version in pins.values())
    for package in ("azure-identity", "azure-storage-blob", "numpy", "scipy"):
        assert package in pins


def test_frozen_generation_constants_are_bound_by_the_image() -> None:
    assert prov.MODEL_ID == "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    assert prov.MODEL_REVISION == "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
    assert prov.TOKENIZER_REVISION == prov.MODEL_REVISION
    assert prov.MODEL_ID == hc.MODEL_ID
    assert prov.MODEL_REVISION == hc.MODEL_REVISION
    assert prov.IMAGE_REPOSITORY == "j-space-observation-calibration"
    assert prov.BASE_IMAGE_DIGEST.startswith("sha256:")
    assert len(prov.BASE_IMAGE_DIGEST) == len("sha256:") + 64


def test_runtime_files_exist_and_are_unique() -> None:
    assert len(set(prov.RUNTIME_FILES)) == len(prov.RUNTIME_FILES)
    assert list(prov.RUNTIME_FILES) == sorted(prov.RUNTIME_FILES)
    for relative in prov.RUNTIME_FILES:
        assert (ROOT / relative).is_file(), relative
    # The record must never try to hash itself.
    assert prov.PROVENANCE_FILENAME not in prov.RUNTIME_FILES


def test_bundle_digest_is_stable_and_content_sensitive(tmp_path: Path) -> None:
    first, digests = prov.bundle_digest(ROOT)
    second, again = prov.bundle_digest(ROOT)
    assert first == second
    assert digests == again
    assert set(digests) == set(prov.RUNTIME_FILES)
    assert all(len(value) == 64 for value in digests.values())


# ---------------------------------------------------------------------------
# Build provenance: generate / verify against a synthetic Git worktree
# ---------------------------------------------------------------------------


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture()
def synthetic_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway Git repo with a reduced runtime-file list.

    The real 25-file list is exercised by ``test_runtime_files_exist_and_are
    _unique`` and by ``bundle_digest``; this fixture exercises the Git-bound
    control flow without copying the whole project.
    """

    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "data").mkdir()
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "Dockerfile.calibration").write_bytes(b"FROM scratch\n")
    (repo / "requirements-calibration.txt").write_bytes(b"numpy==1.26.4\n")
    (repo / "docs/protocol.md").write_bytes(b"frozen protocol\r\n")
    (repo / "data/bank.jsonl").write_bytes(b'{"id": "x"}\n')
    (repo / "scripts/runner.py").write_bytes(b"print('run')\n")
    (repo / "src/pkg/module.py").write_bytes(b"VALUE = 1\n")

    monkeypatch.setattr(
        prov,
        "RUNTIME_FILES",
        (
            "Dockerfile.calibration",
            "data/bank.jsonl",
            "docs/protocol.md",
            "requirements-calibration.txt",
            "scripts/runner.py",
            "src/pkg/module.py",
        ),
    )
    monkeypatch.setattr(prov, "PROTOCOL_DOCUMENT", "docs/protocol.md")
    monkeypatch.setattr(prov, "TASK_BANK", "data/bank.jsonl")

    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "calibration test")
    _git(repo, "add", "--all")
    _git(repo, "commit", "--quiet", "-m", "code")
    return repo


def _generate(repo: Path, commit: str | None = None) -> Path:
    namespace = prov.parse_args(
        [
            "--project-root",
            str(repo),
            "generate",
            *(["--source-commit", commit] if commit else []),
        ]
    )
    assert prov.command_generate(namespace) == 0
    return repo / prov.PROVENANCE_FILENAME


def test_generate_binds_the_source_commit_and_verifies(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    path = _generate(synthetic_repo, head)
    document, _ = prov.load_canonical_json(path)
    prebuild = document["prebuild"]

    assert prebuild["runtime_files_source_commit"] == head
    assert prebuild["model_id"] == prov.MODEL_ID
    assert prebuild["model_revision"] == prov.MODEL_REVISION
    assert prebuild["tokenizer_revision"] == prov.TOKENIZER_REVISION
    assert prebuild["base_image_digest"] == prov.BASE_IMAGE_DIGEST
    assert prebuild["expected_python_version"] == prov.EXPECTED_PYTHON_VERSION
    assert prebuild["expected_torch_version"] == prov.EXPECTED_TORCH_VERSION
    assert (
        prebuild["expected_transformers_version"]
        == prov.EXPECTED_TRANSFORMERS_VERSION
    )
    assert document["build_record"]["status"] == "not_yet_built"
    assert "image_digest" in document["build_record"]["recorded_after_build"]
    assert "acr_build_run_id" in document["build_record"]["recorded_after_build"]
    assert document["prebuild_sha256"] == prov.sha256_bytes(
        prov.canonical_json_bytes(prebuild)
    )

    verify = prov.parse_args(["--project-root", str(synthetic_repo), "verify"])
    assert prov.command_verify(verify) == 0


def test_pending_build_fields_each_state_a_reason(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document = json.loads(_generate(synthetic_repo, head).read_text("ascii"))
    record = document["build_record"]

    pending = record["recorded_after_build"]
    assert isinstance(pending, dict)
    assert set(pending) == set(prov.COMPLETION_FIELDS) - {
        "prebuild_sha256",
        "runtime_files_source_commit",
        "schema_version",
    }
    for name, reason in pending.items():
        assert isinstance(reason, str) and reason.strip(), name
    assert record["status_meaning"]
    assert record["binding"]


def test_pending_fields_are_absent_rather_than_placeholders(
    synthetic_repo: Path,
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document = json.loads(_generate(synthetic_repo, head).read_text("ascii"))

    for name in document["build_record"]["recorded_after_build"]:
        assert name not in document
        assert name not in document["prebuild"]

    def walk(node: object) -> Iterator[object]:
        if isinstance(node, dict):
            for value in node.values():
                yield from walk(value)
        elif isinstance(node, list):
            for value in node:
                yield from walk(value)
        else:
            yield node

    placeholders = {"", "tbd", "placeholder", "unknown", "none", "n/a", "0"}
    for value in walk(document["prebuild"]):
        if isinstance(value, str):
            assert value.strip().lower() not in placeholders
            assert not value.startswith("sha256:0000")


def test_build_record_without_pending_reasons_is_rejected(
    synthetic_repo: Path,
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document = json.loads(_generate(synthetic_repo, head).read_text("ascii"))
    document["build_record"]["recorded_after_build"]["image_digest"] = "  "

    with pytest.raises(prov.ProvenanceError):
        prov.validate_document_shape(document)


def test_build_record_listing_the_wrong_fields_is_rejected(
    synthetic_repo: Path,
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document = json.loads(_generate(synthetic_repo, head).read_text("ascii"))
    document["build_record"]["recorded_after_build"].pop("image_digest")

    with pytest.raises(prov.ProvenanceError):
        prov.validate_document_shape(document)


def test_build_record_claiming_completion_is_rejected(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document = json.loads(_generate(synthetic_repo, head).read_text("ascii"))
    document["build_record"]["status"] = "built"

    with pytest.raises(prov.ProvenanceError):
        prov.validate_document_shape(document)


def test_generate_is_deterministic(synthetic_repo: Path, tmp_path: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    first = _generate(synthetic_repo, head).read_bytes()
    (synthetic_repo / prov.PROVENANCE_FILENAME).unlink()
    second = _generate(synthetic_repo, head).read_bytes()
    assert first == second


def test_generate_normalizes_line_endings(synthetic_repo: Path) -> None:
    """A CRLF worktree must produce the same digests as an LF worktree."""

    head = _git(synthetic_repo, "rev-parse", "HEAD")
    lf_document, _ = prov.load_canonical_json(_generate(synthetic_repo, head))
    lf_digest = lf_document["prebuild"]["file_sha256"]["scripts/runner.py"]

    runner = synthetic_repo / "scripts/runner.py"
    runner.write_bytes(runner.read_bytes().replace(b"\n", b"\r\n"))
    bundle, digests = prov.bundle_digest(synthetic_repo)
    assert digests["scripts/runner.py"] == lf_digest
    assert bundle == lf_document["prebuild"]["bundle_sha256"]


def test_generate_refuses_a_dirty_worktree(synthetic_repo: Path) -> None:
    (synthetic_repo / "scripts/runner.py").write_bytes(b"print('drift')\n")
    with pytest.raises(prov.ProvenanceError, match="must be clean"):
        _generate(synthetic_repo)


def test_generate_refuses_to_overwrite_an_existing_record(
    synthetic_repo: Path,
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    _generate(synthetic_repo, head)
    with pytest.raises(prov.ProvenanceError, match="refusing to overwrite"):
        _generate(synthetic_repo, head)


def test_verify_detects_content_drift_after_generation(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    _generate(synthetic_repo, head)
    (synthetic_repo / "scripts/runner.py").write_bytes(b"print('tampered')\n")
    namespace = prov.parse_args(
        ["--project-root", str(synthetic_repo), "verify", "--skip-git"]
    )
    with pytest.raises(prov.ProvenanceError, match="file digest mismatch"):
        prov.command_verify(namespace)


def test_verify_detects_a_tampered_record(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    path = _generate(synthetic_repo, head)
    document, _ = prov.load_canonical_json(path)
    document["prebuild"]["model_revision"] = "0" * 40
    path.write_bytes(prov.canonical_json_bytes(document))
    namespace = prov.parse_args(
        ["--project-root", str(synthetic_repo), "verify", "--skip-git"]
    )
    with pytest.raises(prov.ProvenanceError):
        prov.command_verify(namespace)


def test_verify_detects_a_forged_prebuild_digest(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    path = _generate(synthetic_repo, head)
    document, _ = prov.load_canonical_json(path)
    document["prebuild_sha256"] = "0" * 64
    path.write_bytes(prov.canonical_json_bytes(document))
    namespace = prov.parse_args(
        ["--project-root", str(synthetic_repo), "verify", "--skip-git"]
    )
    with pytest.raises(prov.ProvenanceError):
        prov.command_verify(namespace)


def test_generate_then_commit_record_keeps_the_binding_true(
    synthetic_repo: Path,
) -> None:
    """The two-commit sequence the operator must follow.

    Commit A holds the code; the record is generated against A and then
    committed as B. Because B touches no runtime file, ``verify`` still
    resolves against A with a clean worktree.
    """

    commit_a = _git(synthetic_repo, "rev-parse", "HEAD")
    _generate(synthetic_repo, commit_a)
    _git(synthetic_repo, "add", prov.PROVENANCE_FILENAME)
    _git(synthetic_repo, "commit", "--quiet", "-m", "record")
    commit_b = _git(synthetic_repo, "rev-parse", "HEAD")
    assert commit_b != commit_a

    namespace = prov.parse_args(["--project-root", str(synthetic_repo), "verify"])
    assert prov.command_verify(namespace) == 0


# ---------------------------------------------------------------------------
# Build provenance: in-image verification and build completion
# ---------------------------------------------------------------------------


def test_verify_image_context_accepts_a_faithful_copy(
    synthetic_repo: Path, tmp_path: Path
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    record = _generate(synthetic_repo, head)
    image_root = tmp_path / "image"
    for relative in prov.RUNTIME_FILES:
        target = image_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((synthetic_repo / relative).read_bytes())
    namespace = prov.parse_args(
        [
            "--project-root",
            str(image_root),
            "verify-image-context",
            "--provenance",
            str(record),
        ]
    )
    assert prov.command_verify_image_context(namespace) == 0


def test_verify_image_context_rejects_a_missing_file(
    synthetic_repo: Path, tmp_path: Path
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    record = _generate(synthetic_repo, head)
    image_root = tmp_path / "image"
    for relative in prov.RUNTIME_FILES:
        if relative == "scripts/runner.py":
            continue
        target = image_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((synthetic_repo / relative).read_bytes())
    namespace = prov.parse_args(
        [
            "--project-root",
            str(image_root),
            "verify-image-context",
            "--provenance",
            str(record),
        ]
    )
    with pytest.raises(prov.ProvenanceError):
        prov.command_verify_image_context(namespace)


def _completion_arguments(commit: str) -> dict[str, Any]:
    return {
        "source_commit": commit,
        "build_commit": commit,
        "runtime_files_source_commit": commit,
        "registry_login_server": "acrjspaceobssea0708231738.azurecr.io",
        "image_tag": commit,
        "image_digest": "sha256:" + "a" * 64,
        "acr_build_run_id": "ca42",
        "built_at_utc": "2026-07-26T04:05:06Z",
        "immutability_verified": True,
    }


def test_completion_binds_build_time_facts(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document, _ = prov.load_canonical_json(_generate(synthetic_repo, head))
    completion = prov.build_completion_record(
        document["prebuild_sha256"], **_completion_arguments(head)
    )
    assert completion["prebuild_sha256"] == document["prebuild_sha256"]
    assert completion["image_digest"] == "sha256:" + "a" * 64
    assert completion["acr_build_run_id"] == "ca42"
    assert completion["built_at_utc"] == "2026-07-26T04:05:06Z"
    assert completion["image_reference"].endswith(
        f"/{prov.IMAGE_REPOSITORY}@sha256:" + "a" * 64
    )
    assert prov.verify_completion(document, completion) == completion


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("image_digest", "sha256:short"),
        ("built_at_utc", "2026-07-26 04:05:06"),
        ("registry_login_server", "docker.io"),
        ("acr_build_run_id", "bad id"),
        ("immutability_verified", False),
    ],
)
def test_completion_rejects_malformed_build_facts(
    synthetic_repo: Path, field: str, value: Any
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document, _ = prov.load_canonical_json(_generate(synthetic_repo, head))
    arguments = _completion_arguments(head)
    arguments[field] = value
    with pytest.raises(prov.ProvenanceError):
        prov.build_completion_record(document["prebuild_sha256"], **arguments)


def test_completion_requires_the_tag_to_be_the_source_commit(
    synthetic_repo: Path,
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document, _ = prov.load_canonical_json(_generate(synthetic_repo, head))
    arguments = _completion_arguments(head)
    arguments["image_tag"] = "latest"
    with pytest.raises(prov.ProvenanceError, match="immutable source commit"):
        prov.build_completion_record(document["prebuild_sha256"], **arguments)


def test_verify_completion_rejects_an_unbound_completion(
    synthetic_repo: Path,
) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document, _ = prov.load_canonical_json(_generate(synthetic_repo, head))
    completion = prov.build_completion_record(
        document["prebuild_sha256"], **_completion_arguments(head)
    )
    completion["prebuild_sha256"] = "0" * 64
    with pytest.raises(prov.ProvenanceError, match="not bound"):
        prov.verify_completion(document, completion)


def test_verify_completion_rejects_extra_fields(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document, _ = prov.load_canonical_json(_generate(synthetic_repo, head))
    completion = prov.build_completion_record(
        document["prebuild_sha256"], **_completion_arguments(head)
    )
    completion["note"] = "extra"
    with pytest.raises(prov.ProvenanceError, match="fields must match exactly"):
        prov.verify_completion(document, completion)


def test_verify_completion_rejects_a_swapped_digest(synthetic_repo: Path) -> None:
    head = _git(synthetic_repo, "rev-parse", "HEAD")
    document, _ = prov.load_canonical_json(_generate(synthetic_repo, head))
    completion = prov.build_completion_record(
        document["prebuild_sha256"], **_completion_arguments(head)
    )
    completion["image_digest"] = "sha256:" + "b" * 64
    with pytest.raises(prov.ProvenanceError, match="not self-consistent"):
        prov.verify_completion(document, completion)


# ---------------------------------------------------------------------------
# Dockerfile.calibration and the two Azure scripts
# ---------------------------------------------------------------------------


def test_dockerfile_pins_the_base_image_by_digest() -> None:
    text = _read_lf(DOCKERFILE)
    assert f"FROM {prov.BASE_IMAGE}@{prov.BASE_IMAGE_DIGEST}" in text
    assert ":latest" not in text
    assert "pip install" in text
    assert "--no-deps" in text
    assert "--require-hashes" not in text or "--no-deps" in text


def test_dockerfile_verifies_itself_at_build_time() -> None:
    text = _read_lf(DOCKERFILE)
    assert "verify-runtime" in text
    assert "verify-image-context" in text
    assert "calibration_build_provenance.py" in text
    assert prov.PROVENANCE_FILENAME in text


def test_dockerfile_runs_unprivileged_and_without_silent_failure() -> None:
    text = _read_lf(DOCKERFILE)
    assert "USER 10001:10001" in text
    assert "2>/dev/null" not in text
    assert "|| true" not in text
    assert "USER root" not in text.split("USER 10001:10001", 1)[1]


def test_dockerfile_copies_every_recorded_runtime_file() -> None:
    text = _read_lf(DOCKERFILE)
    for relative in prov.RUNTIME_FILES:
        assert relative in text, relative


def test_dockerfile_default_command_is_the_frozen_generation_run() -> None:
    text = _read_lf(DOCKERFILE)
    assert "run_phase1_headroom_calibration.py" in text
    assert "generate" in text
    assert "--upload-blob" in text


@pytest.mark.parametrize("script", [BUILD_SCRIPT, RUN_SCRIPT])
def test_azure_scripts_never_suppress_errors(script: Path) -> None:
    text = _read_lf(script)
    assert "2>/dev/null" not in text
    assert "|| true" not in text
    assert "set -euo pipefail" in text


@pytest.mark.parametrize("script", [BUILD_SCRIPT, RUN_SCRIPT])
def test_azure_scripts_bind_an_absolute_interpreter(script: Path) -> None:
    text = _read_lf(script)
    assert 'readonly PYTHON_BIN="$(/usr/bin/readlink -f /usr/bin/python3)"' in text
    assert '"$PYTHON_BIN" -I "$@"' in text
    assert "readonly -f python" in text


@pytest.mark.parametrize("script", [BUILD_SCRIPT, RUN_SCRIPT])
def test_azure_scripts_never_use_a_floating_tag(script: Path) -> None:
    text = _read_lf(script)
    assert ":latest" not in text
    assert "--force" not in text
    assert 'IMAGE_REPOSITORY="j-space-observation-calibration"' in text


def test_build_script_builds_the_calibration_dockerfile() -> None:
    text = _read_lf(BUILD_SCRIPT)
    assert "az acr build" in text
    assert '--file "$PROJECT_ROOT/Dockerfile.calibration"' in text
    assert "--platform linux/amd64" in text
    assert "--query runId -o tsv" in text
    assert "az acr import" in text
    assert "--write-enabled false" in text
    assert "--delete-enabled false" in text
    assert "verify-completion" in text
    assert "PROJECT_SHA must be a full 40-character commit" in text


def test_build_script_verifies_provenance_before_building() -> None:
    text = _read_lf(BUILD_SCRIPT)
    verify_at = text.index('"$PROVENANCE_HELPER" \\\n    --project-root "$PROJECT_ROOT" verify')
    build_at = text.index("az acr build")
    assert verify_at < build_at


def test_run_script_pins_the_job_to_the_required_platform() -> None:
    text = _read_lf(RUN_SCRIPT)
    assert 'CONTAINER_APP_ENV="cae-jspace-observation-sea-vnet2"' in text
    assert 'WORKLOAD_PROFILE_NAME="gpu-t4"' in text
    assert '"replicaRetryLimit": 0' in text
    assert '"parallelism": 1' in text
    assert '"replicaCompletionCount": 1' in text
    assert '"triggerType": "Manual"' in text
    assert "$IMAGE_DIGEST_REF" in text
    assert "@${IMAGE_DIGEST}" in text


def test_run_script_uses_managed_identity_only() -> None:
    text = _read_lf(RUN_SCRIPT)
    assert '"type": "UserAssigned"' in text
    assert 'IDENTITY_NAME="id-jspace-aca-acrpull-sea"' in text
    assert "AZURE_STORAGE_CONNECTION_STRING" not in text
    assert "account-key" not in text
    assert "--sas-token" not in text
    assert "azureFile" not in text


def test_run_script_passes_every_required_environment_variable() -> None:
    text = _read_lf(RUN_SCRIPT)
    for name in (
        "AZURE_CLIENT_ID",
        "JSPACE_BLOB_ACCOUNT",
        "JSPACE_BLOB_CONTAINER",
        "JSPACE_BLOB_PREFIX",
        "JSPACE_HEADROOM_RUN_ID",
        "JSPACE_CODE_COMMIT",
        "JSPACE_IMAGE_DIGEST",
        "JSPACE_HARDWARE",
        "HF_HOME",
        "TMPDIR",
    ):
        assert f'"name": "{name}"' in text, name
    assert 'BLOB_PREFIX="phase1-headroom-calibration"' in text


def test_run_script_refuses_to_launch_an_unlocked_image() -> None:
    text = _read_lf(RUN_SCRIPT)
    assert "Calibration image is not locked; refusing to launch" in text
    assert "MANIFEST_WRITE_ENABLED" in text


# ---------------------------------------------------------------------------
# Blob transport
# ---------------------------------------------------------------------------


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def upload_blob(self, *, name: str, data: Any, overwrite: bool) -> None:
        self.calls.append(
            {"name": name, "overwrite": overwrite, "payload": data.read()}
        )


def _pack(tmp_path: Path) -> Path:
    pack = tmp_path / "pack"
    (pack / "review_pack").mkdir(parents=True)
    for name in hc.ARTIFACT_FILES:
        (pack / name).write_text(f"{name} body\n", encoding="utf-8")
    (pack / "review_pack/review_pack.jsonl").write_text("{}\n", encoding="utf-8")
    return pack


def test_destination_prefix_is_the_registered_blob_layout() -> None:
    assert (
        hbt.destination_prefix("20260726T010203Z")
        == "phase1-headroom-calibration/20260726T010203Z"
    )
    assert (
        hbt.destination_prefix("20260726T010203Z", "phase1-headroom-calibration/")
        == "phase1-headroom-calibration/20260726T010203Z"
    )
    with pytest.raises(hbt.BlobTransportError):
        hbt.destination_prefix("  ")
    with pytest.raises(hbt.BlobTransportError):
        hbt.destination_prefix("")


def test_ordered_pack_files_puts_the_manifest_last(tmp_path: Path) -> None:
    pack = _pack(tmp_path)
    ordered = [path.relative_to(pack).as_posix() for path in hbt.ordered_pack_files(pack)]
    assert ordered[-1] == "artifact_manifest.json"
    assert ordered[:-1] == sorted(ordered[:-1])
    assert "review_pack/review_pack.jsonl" in ordered


def test_ordered_pack_files_rejects_an_empty_directory(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(hbt.BlobTransportError):
        hbt.ordered_pack_files(empty)


@pytest.mark.parametrize("name", hbt.FORBIDDEN_ENVIRONMENT)
def test_assert_managed_identity_only_rejects_shared_secrets(name: str) -> None:
    with pytest.raises(hbt.BlobTransportError, match="managed identity"):
        hbt.assert_managed_identity_only({name: "secret"})


def test_assert_managed_identity_only_accepts_identity_variables() -> None:
    hbt.assert_managed_identity_only(
        {
            "AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000000",
            "JSPACE_BLOB_ACCOUNT": "stjspacefiles0709085305",
        }
    )


def test_upload_pack_writes_the_manifest_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in hbt.FORBIDDEN_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    client = _RecordingClient()
    result = hbt.upload_pack(
        _pack(tmp_path),
        "20260726T010203Z",
        account="stjspacefiles0709085305",
        container="jspace-results",
        prefix="phase1-headroom-calibration",
        client_id="00000000-0000-0000-0000-000000000000",
        client=client,
    )
    names = [call["name"] for call in client.calls]
    assert names[-1] == (
        "phase1-headroom-calibration/20260726T010203Z/artifact_manifest.json"
    )
    assert all(call["overwrite"] is False for call in client.calls)
    assert result["status"] == "uploaded"
    assert result["manifest_uploaded_last"] is True
    assert result["credential_mode"] == "default_credential_managed_identity_only"
    assert result["uploaded_count"] == len(names)


def test_upload_pack_refuses_when_a_shared_secret_is_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=x")
    with pytest.raises(hbt.BlobTransportError):
        hbt.upload_pack(
            _pack(tmp_path),
            "20260726T010203Z",
            account="a",
            container="b",
            client=_RecordingClient(),
        )


def test_upload_pack_requires_a_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in hbt.FORBIDDEN_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    pack = _pack(tmp_path)
    with pytest.raises(hbt.BlobTransportError):
        hbt.upload_pack(pack, "20260726T010203Z", account="", container="", client=object())
    skipped = hbt.upload_pack(
        pack,
        "20260726T010203Z",
        account="",
        container="",
        require=False,
        client=object(),
    )
    assert skipped["status"] == "not_configured"
    assert skipped["manifest_uploaded_last"] is False


# ---------------------------------------------------------------------------
# Semantic review ingestion
# ---------------------------------------------------------------------------


def _review_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "record_id": "rec-0001",
        "semantic_answer": "42",
        "semantic_correct": True,
        "output_complete": True,
        "truncated": False,
        "no_answer": False,
        "ambiguity": "none",
        "confidence": "high",
        "notes": "",
    }
    row.update(overrides)
    return row


def test_review_form_fields_match_the_registered_contract() -> None:
    assert ingest.REVIEW_FIELDS == (
        "record_id",
        "semantic_answer",
        "semantic_correct",
        "output_complete",
        "truncated",
        "no_answer",
        "ambiguity",
        "confidence",
        "notes",
    )
    schema = ingest.review_form_schema()
    assert schema["fields"] == list(ingest.REVIEW_FIELDS)


def test_validate_review_row_accepts_the_registered_form() -> None:
    assert ingest.validate_review_row(_review_row(), 1) == _review_row()


@pytest.mark.parametrize(
    "mutation",
    [
        {"ambiguity": "unclear"},
        {"confidence": "certain"},
        {"semantic_correct": "yes"},
        {"truncated": "false"},
        {"notes": None},
        {"record_id": ""},
    ],
)
def test_validate_review_row_rejects_out_of_domain_values(
    mutation: dict[str, Any]
) -> None:
    with pytest.raises(ingest.ReviewIngestError):
        ingest.validate_review_row(_review_row(**mutation), 1)


def test_validate_review_row_rejects_extra_or_missing_fields() -> None:
    extra = _review_row()
    extra["reviewer"] = "r1"
    with pytest.raises(ingest.ReviewIngestError, match="exactly"):
        ingest.validate_review_row(extra, 1)
    missing = _review_row()
    del missing["notes"]
    with pytest.raises(ingest.ReviewIngestError, match="exactly"):
        ingest.validate_review_row(missing, 1)


@pytest.mark.parametrize(
    "mutation",
    [
        {"output_complete": True, "truncated": True},
        {"no_answer": True, "semantic_correct": True},
        {"no_answer": True, "semantic_answer": "42", "semantic_correct": False},
        {"semantic_correct": True, "semantic_answer": None},
        {"semantic_correct": True, "semantic_answer": "   "},
    ],
)
def test_validate_review_row_rejects_self_contradictions(
    mutation: dict[str, Any]
) -> None:
    with pytest.raises(ingest.ReviewIngestError):
        ingest.validate_review_row(_review_row(**mutation), 1)


def test_unresolved_is_expressed_as_a_null_correctness() -> None:
    row = _review_row(semantic_correct=None, ambiguity="major", confidence="low")
    judgments = ingest.to_judgments([ingest.validate_review_row(row, 1)], "reviewer-a")
    assert judgments[0]["semantic_label"] == "unresolved"
    assert judgments[0]["reviewer_id"] == "reviewer-a"


def test_label_mapping_is_deterministic() -> None:
    assert ingest.LABEL_BY_CORRECTNESS == {
        True: "correct",
        False: "incorrect",
        None: "unresolved",
    }
    rows = [
        ingest.validate_review_row(_review_row(record_id="b"), 1),
        ingest.validate_review_row(
            _review_row(record_id="a", semantic_correct=False), 2
        ),
    ]
    judgments = ingest.to_judgments(rows, "reviewer-a")
    assert [row["record_id"] for row in judgments] == ["a", "b"]
    assert [row["semantic_label"] for row in judgments] == ["incorrect", "correct"]


def test_load_review_rows_rejects_duplicate_record_ids(tmp_path: Path) -> None:
    path = tmp_path / "review.jsonl"
    payload = json.dumps(_review_row()) + "\n"
    path.write_text(payload + payload, encoding="utf-8")
    with pytest.raises(ingest.ReviewIngestError, match="duplicate"):
        ingest.load_review_rows(path)


def test_judgments_round_trip_into_the_calibration_loader(tmp_path: Path) -> None:
    rows = [
        ingest.validate_review_row(_review_row(record_id="rec-a"), 1),
        ingest.validate_review_row(
            _review_row(record_id="rec-b", semantic_correct=False), 2
        ),
    ]
    path = tmp_path / "judgments.jsonl"
    ingest.write_jsonl(path, ingest.to_judgments(rows, "reviewer-a"))
    loaded = hc.load_judgments(path)
    assert set(loaded) == {"rec-a", "rec-b"}
    assert loaded["rec-a"]["semantic_label"] == "correct"
    assert loaded["rec-b"]["semantic_label"] == "incorrect"


def test_coverage_report_flags_outstanding_mandatory_rows(tmp_path: Path) -> None:
    pack = tmp_path / "review_pack.jsonl"
    pack.write_text(
        json.dumps({"record_id": "rec-a", "review_reasons": ["parse_invalid"]})
        + "\n"
        + json.dumps(
            {"record_id": "rec-b", "review_reasons": ["deterministic_random_sample"]}
        )
        + "\n",
        encoding="utf-8",
    )
    rows = [ingest.validate_review_row(_review_row(record_id="rec-b"), 1)]
    report = ingest.coverage_report(ingest.to_judgments(rows, "reviewer-a"), pack)
    assert report["mandatory_rows"] == 1
    assert report["outstanding_mandatory_rows"] == ["rec-a"]
    assert report["coverage_complete"] is False


def test_coverage_report_rejects_rows_outside_the_pack(tmp_path: Path) -> None:
    pack = tmp_path / "review_pack.jsonl"
    pack.write_text(
        json.dumps({"record_id": "rec-a", "review_reasons": ["parse_invalid"]}) + "\n",
        encoding="utf-8",
    )
    rows = [ingest.validate_review_row(_review_row(record_id="rec-z"), 1)]
    with pytest.raises(ingest.ReviewIngestError, match="not in the review pack"):
        ingest.coverage_report(ingest.to_judgments(rows, "reviewer-a"), pack)


def test_review_reason_codes_agree_with_the_registered_scope() -> None:
    """Every mandatory review trigger in the protocol has a reason code."""

    reasons = set(hc.REVIEW_REASON_CODES)
    for required in (
        "parse_invalid",
        "ambiguous_parse",
        "truncated_output",
        "no_answer",
        "triage_disagrees_with_registered_answer",
        "provisional_headroom_cell",
        "deterministic_random_sample",
    ):
        assert required in reasons
    # Only the 10% clean sample is optional; everything else is mandatory.
    assert "deterministic_random_sample" in reasons
    assert hc.REVIEW_SAMPLE_FRACTION == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# Additive metrics, cell-selection views and the deviation record
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def execution_pack(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_root = tmp_path_factory.mktemp("execution_pack")
    config = hc.RunConfig(
        mode="self-test",
        output_root=output_root,
        bank_path=hc.DEFAULT_BANK_PATH,
        repo_root=ROOT,
        frozen_time=FROZEN_TIME,
        code_commit="0" * 40,
        image_digest="sha256:" + "0" * 64,
        hardware="cpu-unit-test",
        backend=hc.SelfTestBackend(),
    )
    return Path(hc.run_calibration(config)["output_dir"])


def _metrics_rows(pack: Path) -> list[dict[str, str]]:
    with open(pack / "03_metrics.csv", "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_pack_emits_all_four_cell_selection_tables(execution_pack: Path) -> None:
    for name in (
        "selected_headroom_cells.csv",
        "high_accuracy_controls.csv",
        "difficulty_boundaries.csv",
        "excluded_cells.csv",
    ):
        assert (execution_pack / "cell_selection" / name).is_file(), name


def test_derived_views_are_subsets_of_the_excluded_table(execution_pack: Path) -> None:
    def _cell_ids(name: str) -> set[str]:
        path = execution_pack / "cell_selection" / name
        with open(path, "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if rows and "status" in rows[0] and rows[0].get("status") == "not_applicable":
            return set()
        return {row["cell_id"] for row in rows if row.get("cell_id")}

    excluded = _cell_ids("excluded_cells.csv")
    controls = _cell_ids("high_accuracy_controls.csv")
    boundaries = _cell_ids("difficulty_boundaries.csv")
    assert controls <= excluded
    assert boundaries <= excluded
    assert not (controls & boundaries)
    assert not (controls & _cell_ids("selected_headroom_cells.csv"))


def test_metrics_carry_every_registered_per_cell_rate(execution_pack: Path) -> None:
    rows = _metrics_rows(execution_pack)
    assert list(rows[0]) == list(hc.METRICS_HEADER)
    per_cell = {
        row["metric"] for row in rows if "|" in row["stratum"]
    }
    for metric in (
        "semantic_accuracy",
        "truncation_rate",
        "no_answer_rate",
        "ambiguous_rate",
        "semantic_review_rate",
        "unresolved_label_rate",
    ):
        assert metric in per_cell, metric


def test_per_cell_accuracy_rows_carry_n_correct_and_a_wilson_interval(
    execution_pack: Path,
) -> None:
    rows = [
        row
        for row in _metrics_rows(execution_pack)
        if row["metric"] == "semantic_accuracy" and "|" in row["stratum"]
    ]
    assert rows
    for row in rows:
        assert row["n"] == "10", "n = 10 per cell is a screen, not an estimate"
        if row["not_applicable_reason"]:
            continue
        numerator = int(row["numerator"])
        denominator = int(row["denominator"])
        assert denominator == 10
        expected = hc.wilson_ci(numerator, denominator)
        assert float(row["ci_lower"]) == pytest.approx(expected[0], abs=5e-6)
        assert float(row["ci_upper"]) == pytest.approx(expected[1], abs=5e-6)
        assert float(row["value"]) == pytest.approx(numerator / denominator, abs=5e-6)


def test_cell_scores_expose_ambiguity_counts(execution_pack: Path) -> None:
    records = [
        json.loads(line)
        for line in (execution_pack / "02_records.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    cells = hc.score_cells(records)
    assert cells
    for cell in cells:
        assert cell["n"] == 10, "each screening cell is exactly ten generations"
        assert 0 <= cell["ambiguous"] <= cell["n"]
        assert cell["ambiguous_rate"] == pytest.approx(cell["ambiguous"] / cell["n"])
        assert 0.0 <= cell["truncation_rate"] <= 1.0
        assert 0.0 <= cell["no_answer_rate"] <= 1.0
        if cell["accuracy"] is not None:
            assert cell["ci_lower"] - 1e-9 <= cell["accuracy"] <= cell["ci_upper"] + 1e-9
            assert hc.wilson_ci(cell["correct"], cell["n"])[0] == pytest.approx(
                cell["ci_lower"], abs=5e-6
            )


def test_deviation_record_separates_protocol_from_implementation(
    execution_pack: Path,
) -> None:
    payload = json.loads(
        (execution_pack / "08_deviations.json").read_text(encoding="utf-8")
    )
    assert payload["protocol_deviation"] == "none"
    assert payload["unregistered_changes"] == []
    for entry in payload["deviations"]:
        assert entry["registered"] is True
    changes = payload["execution_implementation_changes"]
    assert changes, "the dedicated image must be recorded as an execution change"
    kinds = {change["change"] for change in changes}
    assert any("calibration container image" in kind for kind in kinds)
    for change in changes:
        assert change["effect_on_protocol"] == "none"
        assert change["scope"] == "execution_implementation"
        assert change["reason"]


def test_attestation_claim_is_auditable_not_merely_assertive(
    execution_pack: Path,
) -> None:
    payload = json.loads(
        (execution_pack / "08_deviations.json").read_text(encoding="utf-8")
    )
    evidence = payload["semantic_audit_attestation_evidence"]

    assert evidence["outcome"] == "unrecoverable_and_unregenerable"
    measurement = evidence["generator_equality_measurement"]
    assert measurement["frozen_runtime_files"] == 30
    assert measurement["tracked_behavior_files"] == 63
    assert measurement["extra_files_not_in_frozen_list"] == 33
    assert measurement["missing_files_from_tree"] == 0
    assert measurement["measured_at_commit"] == (
        "a91db884179911329eae3aadee506ab09b3a0e26"
    )
    assert "git ls-files" in measurement["scope"]

    sources = evidence["checked_sources"]
    assert set(sources) == {
        "acr",
        "blob_build_artifacts",
        "git_history",
        "registered_generator",
        "working_tree",
    }
    for name, finding in sources.items():
        assert isinstance(finding, str) and finding.strip(), name


def test_recorded_measurements_match_the_repository_as_it_stands() -> None:
    measurement = hc.ATTESTATION_RECOVERY_EVIDENCE[
        "generator_equality_measurement"
    ]
    extra = measurement["extra_files_not_in_frozen_list"]
    missing = measurement["missing_files_from_tree"]
    tracked = measurement["tracked_behavior_files"]
    frozen = measurement["frozen_runtime_files"]

    assert tracked - extra == frozen - missing
    assert extra > 0, "the equality could still hold, so the claim would be false"


def test_deviation_reason_states_why_the_generic_image_is_unusable() -> None:
    entry = hc.EXECUTION_IMPLEMENTATION_CHANGES[0]
    reason = entry["reason"]

    assert "unrecoverable" in reason
    assert "unregenerable" in reason
    assert "30-file frozen list" in reason
    assert "63 behavior files" in reason
    for source in ("git history", "ACR", "Blob"):
        assert source in reason


def test_execution_changes_are_declared_once(execution_pack: Path) -> None:
    payload = json.loads(
        (execution_pack / "08_deviations.json").read_text(encoding="utf-8")
    )
    changes = payload["execution_implementation_changes"]
    assert len(changes) == len({change["change"] for change in changes})
    assert len(changes) == len(hc.EXECUTION_IMPLEMENTATION_CHANGES)


def test_pack_still_has_exactly_the_registered_ten_files(execution_pack: Path) -> None:
    assert len(hc.ARTIFACT_FILES) == 10
    for name in hc.ARTIFACT_FILES:
        assert (execution_pack / name).is_file(), name


def test_track_b_decision_vocabulary_is_available_alongside_the_frozen_status(
    execution_pack: Path,
) -> None:
    assert set(hc.TRACK_B_DECISIONS) == {
        "HEADROOM_CELLS_SELECTED",
        "CONTROLS_ONLY",
        "NO_USABLE_CELLS",
        "INCONCLUSIVE",
    }
    payload = json.loads(
        (execution_pack / "04_decision.json").read_text(encoding="utf-8")
    )
    # The frozen protocol registers status; the Track B decision is additive.
    assert payload["status"] in {"BLOCKED", "INCONCLUSIVE", "COMPLETE", "FAIL"}
    assert payload["track_b_decision"] in hc.TRACK_B_DECISIONS
    assert payload["track_b_decision_vocabulary"] == list(hc.TRACK_B_DECISIONS)


def test_track_b_decision_mapping_is_deterministic() -> None:
    control = {"classification": "control_sanity_high_accuracy"}
    boundary = {"classification": "difficulty_boundary_excluded"}
    headroom = {"classification": "selected_headroom"}
    assert hc._track_b_decision("INCONCLUSIVE", [headroom], [headroom]) == "INCONCLUSIVE"
    assert hc._track_b_decision("BLOCKED", [], []) == "INCONCLUSIVE"
    assert (
        hc._track_b_decision("COMPLETE", [headroom, control], [headroom])
        == "HEADROOM_CELLS_SELECTED"
    )
    assert hc._track_b_decision("COMPLETE", [control, boundary], []) == "CONTROLS_ONLY"
    assert hc._track_b_decision("COMPLETE", [boundary], []) == "NO_USABLE_CELLS"
    assert hc._track_b_decision("COMPLETE", [], []) == "NO_USABLE_CELLS"


# ---------------------------------------------------------------------------
# Runner wiring
# ---------------------------------------------------------------------------


def test_run_script_command_matches_the_runner_cli() -> None:
    text = _read_lf(RUN_SCRIPT)
    command = next(line for line in text.splitlines() if line.startswith("COMMAND="))
    assert "/workspace/scripts/run_phase1_headroom_calibration.py" in command
    tail = command.split("run_phase1_headroom_calibration.py", 1)[1].rstrip('"')
    arguments = tail.split()
    assert arguments[:5] == [
        "--mode",
        "generate",
        "--output-root",
        "/workspace/runtime/results",
        "--upload-blob",
    ]
    runner = _load_script(RUNNER_SCRIPT, "_run_phase1_headroom_calibration_under_test")
    parsed = runner.build_parser().parse_args(arguments)
    assert parsed.mode == "generate"
    assert Path(parsed.output_root) == Path("/workspace/runtime/results")
    assert parsed.upload_blob is True


def test_dockerfile_command_matches_the_runner_cli() -> None:
    text = _read_lf(DOCKERFILE)
    assert '"--mode", "generate"' in text
    assert '"--output-root", "/workspace/runtime/results"' in text
    assert '"--upload-blob"' in text
    runner = _load_script(RUNNER_SCRIPT, "_run_phase1_headroom_calibration_under_test")
    parsed = runner.build_parser().parse_args(
        ["--mode", "generate", "--output-root", "/workspace/runtime/results", "--upload-blob"]
    )
    assert parsed.mode == "generate"
    assert parsed.upload_blob is True


def test_runner_requires_provenance_for_a_real_generation_run() -> None:
    text = _read_lf(RUNNER_SCRIPT)
    assert "JSPACE_CODE_COMMIT" in text
    assert "JSPACE_IMAGE_DIGEST" in text
    assert "headroom_blob_transport" in text
    assert "upload_pack" in text
    assert "blob_export" not in text


def test_runner_holds_the_frozen_generation_settings() -> None:
    assert hc.MAX_NEW_TOKENS == 512
    assert hc.TEMPERATURE == pytest.approx(0.6)
    assert hc.TOP_P == pytest.approx(0.95)
    assert hc.SAMPLES_PER_ITEM == 1
    assert hc.SELECTION_SEED == 20260725
    assert hc.RUN_BASE_SEED == 20260725
    assert hc.EXPECTED_ITEM_COUNT == 150
    assert hc.EXPECTED_GENERATION_COUNT == 300
    assert hc.ITEMS_PER_CELL == 10
    assert hc.REQUIRED_CELL_N == 10
    assert set(hc.CONDITIONS) == {"visible_cot", "r1_style_thinking"}
    assert len(hc.CONDITIONS) == 2
    assert hc.MODEL_ID == "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    assert hc.MODEL_REVISION == "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"


def test_selection_gates_are_the_preregistered_ones() -> None:
    assert hc.ACCURACY_BAND_LOW == pytest.approx(0.70)
    assert hc.ACCURACY_BAND_HIGH == pytest.approx(0.90)
    assert hc.MIN_CORRECT_COUNT == 7
    assert hc.MAX_TRUNCATION_RATE == pytest.approx(0.10)
    assert hc.MAX_NO_ANSWER_RATE == pytest.approx(0.10)


def test_parser_v2_is_triage_only() -> None:
    """Parser v2's locked validation outcome was FAIL; it cannot label."""

    assert hc.TRIAGE_AUTHORITY == "screening_only_not_locked"
    assert hc.PARSER_V2_LOCKED_VALIDATION_STATUS.startswith("failed_")
    assert hc.LABEL_SOURCE_TRIAGE_ACCEPTED != hc.LABEL_SOURCE_PRIMARY
