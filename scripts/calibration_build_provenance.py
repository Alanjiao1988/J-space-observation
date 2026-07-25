#!/usr/bin/env python3
"""Deterministic build provenance for the Phase 1.0C calibration image.

The generic semantic-audit image cannot be built at any current commit: its
attestation is bound to a frozen 32-file behaviour list that no longer matches
the repository.  This module produces a *dedicated* calibration-image
provenance record instead.  It never invents a fact:

* the pre-build record binds only content that exists in the worktree and in
  Git, and is byte-stable, so it can be committed before the image is built;
* the build-time facts (ACR run id, image digest, timestamps) are recorded in a
  separate completion artifact after the build, and that artifact is verified
  against the pre-build record's digest.

Nothing here changes the frozen scientific protocol.  It is execution
infrastructure only.
"""

from __future__ import annotations

import sys

if __name__ == "__main__" and not sys.flags.isolated:
    print(
        "[FAIL] Calibration build provenance requires an isolated interpreter "
        "(python -I)",
        file=sys.stderr,
    )
    raise SystemExit(1)

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence


PROVENANCE_FILENAME = "calibration_build_provenance.json"
COMPLETION_FILENAME = "calibration_build_completion.json"
PREBUILD_SCHEMA_VERSION = "phase1-headroom-calibration-build-provenance/v1"
COMPLETION_SCHEMA_VERSION = "phase1-headroom-calibration-build-completion/v1"
BUNDLE_HASH_DOMAIN = "jspace-headroom-calibration/build-bundle/v1"

IMAGE_REPOSITORY = "j-space-observation-calibration"
BASE_IMAGE = "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"
BASE_IMAGE_DIGEST = (
    "sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126"
)
BASE_IMAGE_PLATFORM = "linux/amd64"
EXPECTED_PYTHON_VERSION = "3.11"
EXPECTED_TORCH_VERSION = "2.4.1"
EXPECTED_TRANSFORMERS_VERSION = "4.46.3"

MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
MODEL_REVISION = "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
TOKENIZER_REVISION = MODEL_REVISION

DOCKERFILE = "Dockerfile.calibration"
REQUIREMENTS = "requirements-calibration.txt"
PROTOCOL_DOCUMENT = "docs/phase1_headroom_calibration_protocol.md"
TASK_BANK = "data/phase1_task_headroom_candidates.jsonl"

# Every file copied into the calibration image.  The provenance file itself is
# deliberately absent: a record cannot hash itself.
RUNTIME_FILES: tuple[str, ...] = (
    "Dockerfile.calibration",
    "data/phase1_task_headroom_candidates.jsonl",
    "docs/phase1_headroom_calibration_protocol.md",
    "requirements-calibration.txt",
    "scripts/calibration_build_provenance.py",
    "scripts/ingest_headroom_semantic_review.py",
    "scripts/run_phase1_headroom_calibration.py",
    "src/jspace_observation/__init__.py",
    "src/jspace_observation/blob_export.py",
    "src/jspace_observation/config.py",
    "src/jspace_observation/eval_parsing.py",
    "src/jspace_observation/eval_parsing_v2.py",
    "src/jspace_observation/eval_parsing_v3.py",
    "src/jspace_observation/evaluator_validation.py",
    "src/jspace_observation/headroom_blob_transport.py",
    "src/jspace_observation/headroom_calibration.py",
    "src/jspace_observation/headroom_candidates.py",
    "src/jspace_observation/jlens_utils.py",
    "src/jspace_observation/model_loader.py",
    "src/jspace_observation/no_cot.py",
    "src/jspace_observation/phase1_branches.py",
    "src/jspace_observation/postprocess.py",
    "src/jspace_observation/prompt_sets.py",
    "src/jspace_observation/run_logging.py",
    "src/jspace_observation/stats.py",
)

PREBUILD_FIELDS = frozenset(
    {
        "base_image",
        "base_image_digest",
        "base_image_platform",
        "base_image_reference",
        "bundle_hash_domain",
        "bundle_sha256",
        "dockerfile",
        "dockerfile_sha256",
        "expected_python_version",
        "expected_torch_version",
        "expected_transformers_version",
        "file_sha256",
        "generated_from_clean_git",
        "image_repository",
        "model_id",
        "model_revision",
        "protocol_document",
        "protocol_document_sha256",
        "requirements",
        "requirements_sha256",
        "runtime_files",
        "runtime_files_source_commit",
        "task_bank",
        "task_bank_sha256",
        "tokenizer_revision",
    }
)
PROVENANCE_FIELDS = frozenset(
    {"schema_version", "prebuild", "prebuild_sha256", "build_record"}
)
COMPLETION_FIELDS = frozenset(
    {
        "acr_build_run_id",
        "build_commit",
        "built_at_utc",
        "image_digest",
        "image_reference",
        "image_tag",
        "immutability_verified",
        "prebuild_sha256",
        "registry_login_server",
        "runtime_files_source_commit",
        "schema_version",
        "source_commit",
    }
)

_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_LOGIN_SERVER_PATTERN = re.compile(r"[a-z0-9][a-z0-9.-]*\.azurecr\.io\Z")
_ACR_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}\Z")


class ProvenanceError(RuntimeError):
    """Raised when a build provenance record cannot be trusted."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProvenanceError(f"duplicate provenance key: {key}")
        result[key] = value
    return result


def load_canonical_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        data = path.read_bytes()
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ProvenanceError(f"non-finite provenance value: {token}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"provenance file is missing or malformed: {path}") from exc
    if not isinstance(value, dict):
        raise ProvenanceError(f"provenance file must be a JSON object: {path}")
    if canonical_json_bytes(value) != data:
        raise ProvenanceError(f"provenance file is not canonical JSON: {path}")
    return value, data


def _validate_commit(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _COMMIT_PATTERN.fullmatch(value)
        or value == "0" * 40
    ):
        raise ProvenanceError(f"{label} must be a nonzero lowercase 40-character commit")
    return value


def _validate_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _SHA256_PATTERN.fullmatch(value)
        or value == "0" * 64
    ):
        raise ProvenanceError(f"{label} must be a nonzero lowercase SHA-256")
    return value


def normalize_lf(data: bytes) -> bytes:
    """Return the LF form of a text file so digests are platform independent.

    Every file copied into the image is text.  The Windows worktree is checked
    out with CRLF (``core.autocrlf=true``) while the Linux build context and
    the image both carry LF, so the record binds the normalized content and is
    identical on either platform.
    """

    return data.replace(b"\r\n", b"\n")


def bundle_digest(root: Path) -> tuple[str, dict[str, str]]:
    """Domain-separated digest over every file copied into the image."""

    digest = hashlib.sha256()
    digest.update(BUNDLE_HASH_DOMAIN.encode("ascii"))
    digest.update(b"\0")
    file_digests: dict[str, str] = {}
    for relative in RUNTIME_FILES:
        path = root.joinpath(*relative.split("/"))
        try:
            data = normalize_lf(path.read_bytes())
        except OSError as exc:
            raise ProvenanceError(f"runtime file is unavailable: {relative}") from exc
        encoded = relative.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        file_digests[relative] = sha256_bytes(data)
    return digest.hexdigest(), file_digests


def listed_image_files(root: Path) -> set[str]:
    """Every file the image is allowed to carry under the copied roots."""

    files: set[str] = set()
    for relative_root in ("data", "docs", "scripts", "src"):
        directory = root.joinpath(relative_root)
        if not directory.is_dir():
            raise ProvenanceError(f"image root is unavailable: {relative_root}")
        for path in directory.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                files.add(path.relative_to(root).as_posix())
    for relative in (DOCKERFILE, REQUIREMENTS):
        if root.joinpath(relative).is_file():
            files.add(relative)
    return files


def parse_pinned_requirements(path: Path) -> dict[str, str]:
    """Read ``name==version`` pins; anything unpinned is a hard error."""

    pins: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ProvenanceError(f"requirements file is unavailable: {path}") from exc
    for number, raw in enumerate(lines, start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "==" not in line:
            raise ProvenanceError(
                f"requirement at line {number} is not pinned with '==': {line}"
            )
        name, _, version = line.partition("==")
        name = name.strip()
        version = version.strip()
        if not name or not version:
            raise ProvenanceError(f"requirement at line {number} is malformed: {line}")
        pins[name] = version
    if not pins:
        raise ProvenanceError("requirements file declares no pinned dependency")
    return pins


def command_verify_runtime(args: argparse.Namespace) -> int:
    """Assert the installed interpreter and dependency versions in the image."""

    import importlib.metadata as metadata  # noqa: PLC0415 - needs site packages

    observed_python = f"{sys.version_info[0]}.{sys.version_info[1]}"
    if observed_python != EXPECTED_PYTHON_VERSION:
        raise ProvenanceError(
            f"python {EXPECTED_PYTHON_VERSION} expected; found {observed_python}"
        )
    try:
        torch_version = metadata.version("torch").split("+", 1)[0]
        transformers_version = metadata.version("transformers")
    except metadata.PackageNotFoundError as exc:
        raise ProvenanceError(f"required distribution is missing: {exc}") from exc
    if torch_version != EXPECTED_TORCH_VERSION:
        raise ProvenanceError(
            f"torch {EXPECTED_TORCH_VERSION} expected; found {torch_version}"
        )
    if transformers_version != EXPECTED_TRANSFORMERS_VERSION:
        raise ProvenanceError(
            f"transformers {EXPECTED_TRANSFORMERS_VERSION} expected; "
            f"found {transformers_version}"
        )
    mismatched: list[str] = []
    for name, version in sorted(parse_pinned_requirements(args.requirements).items()):
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            mismatched.append(f"{name}: missing")
            continue
        if installed != version:
            mismatched.append(f"{name}: {installed} != {version}")
    if mismatched:
        raise ProvenanceError("dependency pin mismatch: " + ", ".join(mismatched))
    print(
        json.dumps(
            {
                "python_version": observed_python,
                "torch_version": torch_version,
                "transformers_version": transformers_version,
            },
            sort_keys=True,
        )
    )
    return 0


def _run_git(root: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _require_git(root: Path, arguments: Sequence[str], label: str) -> str:
    result = _run_git(root, arguments)
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise ProvenanceError(f"{label} failed" + (f": {detail}" if detail else ""))
    return result.stdout.strip()


def assert_runtime_files_match_commit(root: Path, commit: str) -> None:
    """Every copied file must be byte-identical to the recorded commit."""

    _require_git(root, ["cat-file", "-e", f"{commit}^{{commit}}"], "source commit lookup")
    for relative in RUNTIME_FILES:
        committed = _require_git(
            root,
            ["rev-parse", f"{commit}:{relative}"],
            f"reading committed object {relative}",
        )
        working = _require_git(
            root,
            ["hash-object", f"--path={relative}", relative],
            f"hashing worktree file {relative}",
        )
        if committed != working:
            raise ProvenanceError(
                f"runtime file differs from {commit[:12]}: {relative}"
            )


def assert_clean_worktree(root: Path) -> None:
    for arguments, label in (
        (["diff", "--quiet", "--exit-code"], "tracked working tree"),
        (["diff", "--cached", "--quiet", "--exit-code"], "Git index"),
    ):
        if _run_git(root, arguments).returncode != 0:
            raise ProvenanceError(f"{label} must be clean")


def build_prebuild_record(root: Path, source_commit: str) -> dict[str, Any]:
    """Assemble the byte-stable pre-build record from committed content."""

    root = root.resolve()
    top = _require_git(root, ["rev-parse", "--show-toplevel"], "locating Git worktree")
    if Path(top).resolve() != root:
        raise ProvenanceError("project root must equal the Git worktree root")
    commit = _validate_commit(source_commit, "runtime files source commit")
    assert_runtime_files_match_commit(root, commit)
    bundle, file_digests = bundle_digest(root)
    return {
        "base_image": BASE_IMAGE,
        "base_image_digest": BASE_IMAGE_DIGEST,
        "base_image_platform": BASE_IMAGE_PLATFORM,
        "base_image_reference": f"{BASE_IMAGE}@{BASE_IMAGE_DIGEST}",
        "bundle_hash_domain": BUNDLE_HASH_DOMAIN,
        "bundle_sha256": bundle,
        "dockerfile": DOCKERFILE,
        "dockerfile_sha256": file_digests[DOCKERFILE],
        "expected_python_version": EXPECTED_PYTHON_VERSION,
        "expected_torch_version": EXPECTED_TORCH_VERSION,
        "expected_transformers_version": EXPECTED_TRANSFORMERS_VERSION,
        "file_sha256": dict(sorted(file_digests.items())),
        "generated_from_clean_git": True,
        "image_repository": IMAGE_REPOSITORY,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "protocol_document": PROTOCOL_DOCUMENT,
        "protocol_document_sha256": file_digests[PROTOCOL_DOCUMENT],
        "requirements": REQUIREMENTS,
        "requirements_sha256": file_digests[REQUIREMENTS],
        "runtime_files": list(RUNTIME_FILES),
        "runtime_files_source_commit": commit,
        "task_bank": TASK_BANK,
        "task_bank_sha256": file_digests[TASK_BANK],
        "tokenizer_revision": TOKENIZER_REVISION,
    }


PENDING_FIELD_REASONS: dict[str, str] = {
    "acr_build_run_id": (
        "assigned by ACR when the build task is queued; it does not exist "
        "while the source tree is being committed"
    ),
    "build_commit": (
        "the commit actually checked out by the build agent; recorded from the "
        "build context so it can be compared against source_commit"
    ),
    "built_at_utc": (
        "the wall-clock instant the image manifest was produced; recording it "
        "before the build would be a fabricated timestamp"
    ),
    "image_digest": (
        "not knowable until the ACR build emits its output manifest, because "
        "the digest covers layers that do not exist yet"
    ),
    "image_reference": (
        "the digest-pinned reference; it embeds image_digest and therefore "
        "cannot be formed before the build"
    ),
    "image_tag": (
        "the immutable <SOURCE_SHA> tag is only bound to a manifest once the "
        "push succeeds"
    ),
    "immutability_verified": (
        "asserts that the tag was locked after the push; it is the outcome of "
        "a post-build check, not a property of the source tree"
    ),
    "registry_login_server": (
        "the registry that actually accepted the push, recorded from the build "
        "result rather than assumed"
    ),
    "source_commit": (
        "echoed back from the build invocation so the completion record can be "
        "cross-checked against the pre-build record it claims to complete"
    ),
}


def build_document(prebuild: dict[str, Any]) -> dict[str, Any]:
    return {
        "build_record": {
            "binding": (
                "the completion artifact is bound to this record by "
                "prebuild_sha256; a completion whose prebuild_sha256 differs "
                "does not describe this source tree"
            ),
            "completion_artifact": COMPLETION_FILENAME,
            "recorded_after_build": dict(PENDING_FIELD_REASONS),
            "status": "not_yet_built",
            "status_meaning": (
                "no image has been built from this record yet; the fields in "
                "recorded_after_build are pending rather than unknown, and are "
                "deliberately absent instead of placeholder values"
            ),
        },
        "prebuild": prebuild,
        "prebuild_sha256": sha256_bytes(canonical_json_bytes(prebuild)),
        "schema_version": PREBUILD_SCHEMA_VERSION,
    }


def _validate_build_record(document: dict[str, Any]) -> None:
    record = document.get("build_record")
    if not isinstance(record, dict):
        raise ProvenanceError("build_record must be an object")
    expected = {
        "binding",
        "completion_artifact",
        "recorded_after_build",
        "status",
        "status_meaning",
    }
    if set(record) != expected:
        raise ProvenanceError("build_record fields must match exactly")
    if record["status"] != "not_yet_built":
        raise ProvenanceError("build_record status must be not_yet_built")
    if record["completion_artifact"] != COMPLETION_FILENAME:
        raise ProvenanceError("build_record completion artifact mismatch")
    pending = record["recorded_after_build"]
    if not isinstance(pending, dict):
        raise ProvenanceError("recorded_after_build must map fields to reasons")
    if set(pending) != set(COMPLETION_FIELDS) - {
        "prebuild_sha256",
        "runtime_files_source_commit",
        "schema_version",
    }:
        raise ProvenanceError(
            "recorded_after_build must list exactly the build-time completion "
            "fields"
        )
    for name, reason in sorted(pending.items()):
        if not isinstance(reason, str) or not reason.strip():
            raise ProvenanceError(f"pending field {name} lacks a stated reason")


def validate_document_shape(document: dict[str, Any]) -> dict[str, Any]:
    if set(document) != set(PROVENANCE_FIELDS):
        raise ProvenanceError("provenance fields must match exactly")
    if document.get("schema_version") != PREBUILD_SCHEMA_VERSION:
        raise ProvenanceError("provenance schema mismatch")
    _validate_build_record(document)
    prebuild = document.get("prebuild")
    if not isinstance(prebuild, dict) or set(prebuild) != set(PREBUILD_FIELDS):
        raise ProvenanceError("pre-build fields must match exactly")
    if sha256_bytes(canonical_json_bytes(prebuild)) != document.get("prebuild_sha256"):
        raise ProvenanceError("prebuild_sha256 does not bind the pre-build record")
    if prebuild.get("runtime_files") != list(RUNTIME_FILES):
        raise ProvenanceError("pre-build runtime file list mismatch")
    file_digests = prebuild.get("file_sha256")
    if not isinstance(file_digests, dict) or list(file_digests) != sorted(RUNTIME_FILES):
        raise ProvenanceError("pre-build file digest list mismatch")
    for relative in RUNTIME_FILES:
        _validate_sha256(file_digests.get(relative), f"{relative} digest")
    for field, expected in (
        ("base_image", BASE_IMAGE),
        ("base_image_digest", BASE_IMAGE_DIGEST),
        ("base_image_platform", BASE_IMAGE_PLATFORM),
        ("base_image_reference", f"{BASE_IMAGE}@{BASE_IMAGE_DIGEST}"),
        ("bundle_hash_domain", BUNDLE_HASH_DOMAIN),
        ("dockerfile", DOCKERFILE),
        ("expected_python_version", EXPECTED_PYTHON_VERSION),
        ("expected_torch_version", EXPECTED_TORCH_VERSION),
        ("expected_transformers_version", EXPECTED_TRANSFORMERS_VERSION),
        ("image_repository", IMAGE_REPOSITORY),
        ("model_id", MODEL_ID),
        ("model_revision", MODEL_REVISION),
        ("protocol_document", PROTOCOL_DOCUMENT),
        ("requirements", REQUIREMENTS),
        ("task_bank", TASK_BANK),
        ("tokenizer_revision", TOKENIZER_REVISION),
    ):
        if prebuild.get(field) != expected:
            raise ProvenanceError(f"pre-build {field} mismatch")
    if prebuild.get("generated_from_clean_git") is not True:
        raise ProvenanceError("pre-build record lacks the clean-Git assertion")
    _validate_commit(
        prebuild.get("runtime_files_source_commit"), "runtime files source commit"
    )
    _validate_sha256(prebuild.get("bundle_sha256"), "bundle digest")
    for field in ("dockerfile_sha256", "requirements_sha256", "task_bank_sha256"):
        if prebuild[field] != file_digests[prebuild[field.replace("_sha256", "")]]:
            raise ProvenanceError(f"pre-build {field} is not the recorded file digest")
    if prebuild["protocol_document_sha256"] != file_digests[PROTOCOL_DOCUMENT]:
        raise ProvenanceError("pre-build protocol_document_sha256 mismatch")
    return prebuild


def verify_content(root: Path, document: dict[str, Any]) -> dict[str, Any]:
    """Verify the record against the files actually present under ``root``."""

    prebuild = validate_document_shape(document)
    actual_bundle, actual_digests = bundle_digest(Path(root))
    if prebuild["file_sha256"] != actual_digests:
        differing = sorted(
            relative
            for relative in RUNTIME_FILES
            if prebuild["file_sha256"].get(relative) != actual_digests[relative]
        )
        raise ProvenanceError(
            "pre-build file digest mismatch: " + ", ".join(differing)
        )
    if prebuild["bundle_sha256"] != actual_bundle:
        raise ProvenanceError("pre-build bundle digest mismatch")
    return prebuild


def build_completion_record(
    prebuild_sha256: str,
    *,
    source_commit: str,
    build_commit: str,
    runtime_files_source_commit: str,
    registry_login_server: str,
    image_tag: str,
    image_digest: str,
    acr_build_run_id: str,
    built_at_utc: str,
    immutability_verified: bool,
) -> dict[str, Any]:
    _validate_sha256(prebuild_sha256, "prebuild digest")
    _validate_commit(source_commit, "source commit")
    _validate_commit(build_commit, "build commit")
    _validate_commit(runtime_files_source_commit, "runtime files source commit")
    if not _LOGIN_SERVER_PATTERN.fullmatch(registry_login_server):
        raise ProvenanceError("registry login server must be an azurecr.io host")
    if image_tag != source_commit:
        raise ProvenanceError("image tag must be the immutable source commit")
    if not _DIGEST_PATTERN.fullmatch(image_digest):
        raise ProvenanceError("image digest must be sha256:<64 hex>")
    if not _ACR_RUN_ID_PATTERN.fullmatch(acr_build_run_id):
        raise ProvenanceError("ACR build run id is malformed")
    if not _TIMESTAMP_PATTERN.fullmatch(built_at_utc):
        raise ProvenanceError("build timestamp must be YYYY-MM-DDTHH:MM:SSZ")
    if immutability_verified is not True:
        raise ProvenanceError(
            "completion may only be recorded once tag immutability is verified"
        )
    return {
        "acr_build_run_id": acr_build_run_id,
        "build_commit": build_commit,
        "built_at_utc": built_at_utc,
        "image_digest": image_digest,
        "image_reference": (
            f"{registry_login_server}/{IMAGE_REPOSITORY}@{image_digest}"
        ),
        "image_tag": image_tag,
        "immutability_verified": True,
        "prebuild_sha256": prebuild_sha256,
        "registry_login_server": registry_login_server,
        "runtime_files_source_commit": runtime_files_source_commit,
        "schema_version": COMPLETION_SCHEMA_VERSION,
        "source_commit": source_commit,
    }


def verify_completion(
    document: dict[str, Any], completion: dict[str, Any]
) -> dict[str, Any]:
    prebuild = validate_document_shape(document)
    if set(completion) != set(COMPLETION_FIELDS):
        raise ProvenanceError("completion fields must match exactly")
    if completion.get("schema_version") != COMPLETION_SCHEMA_VERSION:
        raise ProvenanceError("completion schema mismatch")
    if completion.get("prebuild_sha256") != document["prebuild_sha256"]:
        raise ProvenanceError("completion is not bound to this pre-build record")
    if (
        completion.get("runtime_files_source_commit")
        != prebuild["runtime_files_source_commit"]
    ):
        raise ProvenanceError("completion runtime-file source commit mismatch")
    rebuilt = build_completion_record(
        document["prebuild_sha256"],
        source_commit=str(completion.get("source_commit")),
        build_commit=str(completion.get("build_commit")),
        runtime_files_source_commit=str(
            completion.get("runtime_files_source_commit")
        ),
        registry_login_server=str(completion.get("registry_login_server")),
        image_tag=str(completion.get("image_tag")),
        image_digest=str(completion.get("image_digest")),
        acr_build_run_id=str(completion.get("acr_build_run_id")),
        built_at_utc=str(completion.get("built_at_utc")),
        immutability_verified=completion.get("immutability_verified") is True,
    )
    if rebuilt != completion:
        raise ProvenanceError("completion record is not self-consistent")
    return completion


def _write_new_file(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
    except FileExistsError as exc:
        raise ProvenanceError(f"refusing to overwrite an existing file: {path}") from exc


def command_generate(args: argparse.Namespace) -> int:
    root = args.project_root.resolve()
    assert_clean_worktree(root)
    commit = args.source_commit or _require_git(root, ["rev-parse", "HEAD"], "reading HEAD")
    prebuild = build_prebuild_record(root, commit)
    document = build_document(prebuild)
    validate_document_shape(document)
    output = args.output or (root / PROVENANCE_FILENAME)
    _write_new_file(output, canonical_json_bytes(document))
    verify_content(root, load_canonical_json(output)[0])
    print(output)
    return 0


def command_verify(args: argparse.Namespace) -> int:
    root = args.project_root.resolve()
    path = args.provenance or (root / PROVENANCE_FILENAME)
    document, _ = load_canonical_json(path)
    prebuild = verify_content(root, document)
    if not args.skip_git:
        assert_clean_worktree(root)
        assert_runtime_files_match_commit(
            root, prebuild["runtime_files_source_commit"]
        )
    print(document["prebuild_sha256"])
    return 0


def command_verify_image_context(args: argparse.Namespace) -> int:
    """In-image verification: file digests only, because there is no Git."""

    root = args.project_root.resolve()
    document, _ = load_canonical_json(args.provenance.resolve())
    verify_content(root, document)
    present = listed_image_files(root)
    if present != set(RUNTIME_FILES):
        unexpected = sorted(present - set(RUNTIME_FILES))
        missing = sorted(set(RUNTIME_FILES) - present)
        raise ProvenanceError(
            "image file membership mismatch; unexpected: "
            + (", ".join(unexpected) or "none")
            + "; missing: "
            + (", ".join(missing) or "none")
        )
    print(document["prebuild_sha256"])
    return 0


def command_complete(args: argparse.Namespace) -> int:
    root = args.project_root.resolve()
    provenance_path = args.provenance or (root / PROVENANCE_FILENAME)
    document, _ = load_canonical_json(provenance_path)
    prebuild = validate_document_shape(document)
    completion = build_completion_record(
        document["prebuild_sha256"],
        source_commit=args.source_commit,
        build_commit=args.build_commit,
        runtime_files_source_commit=prebuild["runtime_files_source_commit"],
        registry_login_server=args.registry_login_server,
        image_tag=args.image_tag,
        image_digest=args.image_digest,
        acr_build_run_id=args.acr_build_run_id,
        built_at_utc=args.built_at_utc,
        immutability_verified=args.immutability_verified == "true",
    )
    verify_completion(document, completion)
    _write_new_file(args.output.resolve(), canonical_json_bytes(completion))
    print(args.output.resolve())
    return 0


def command_verify_completion(args: argparse.Namespace) -> int:
    root = args.project_root.resolve()
    provenance_path = args.provenance or (root / PROVENANCE_FILENAME)
    document, _ = load_canonical_json(provenance_path)
    completion, _ = load_canonical_json(args.completion.resolve())
    verify_completion(document, completion)
    print(completion["image_reference"])
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--source-commit")
    generate.add_argument("--output", type=Path)
    generate.set_defaults(handler=command_generate)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--provenance", type=Path)
    verify.add_argument("--skip-git", action="store_true")
    verify.set_defaults(handler=command_verify)

    image = subparsers.add_parser("verify-image-context")
    image.add_argument("--provenance", type=Path, required=True)
    image.set_defaults(handler=command_verify_image_context)

    runtime = subparsers.add_parser("verify-runtime")
    runtime.add_argument("--requirements", type=Path, required=True)
    runtime.set_defaults(handler=command_verify_runtime)

    complete = subparsers.add_parser("complete")
    complete.add_argument("--provenance", type=Path)
    complete.add_argument("--source-commit", required=True)
    complete.add_argument("--build-commit", required=True)
    complete.add_argument("--registry-login-server", required=True)
    complete.add_argument("--image-tag", required=True)
    complete.add_argument("--image-digest", required=True)
    complete.add_argument("--acr-build-run-id", required=True)
    complete.add_argument("--built-at-utc", required=True)
    complete.add_argument(
        "--immutability-verified", choices=("true", "false"), required=True
    )
    complete.add_argument("--output", type=Path, required=True)
    complete.set_defaults(handler=command_complete)

    verify_done = subparsers.add_parser("verify-completion")
    verify_done.add_argument("--provenance", type=Path)
    verify_done.add_argument("--completion", type=Path, required=True)
    verify_done.set_defaults(handler=command_verify_completion)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProvenanceError as error:
        print(f"[FAIL] {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
