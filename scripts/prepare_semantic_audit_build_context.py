#!/usr/bin/env python3
"""Create or validate the immutable semantic-audit image attestation."""

from __future__ import annotations

import sys

if __name__ == "__main__" and (
    not sys.flags.isolated or not sys.flags.no_site
):
    print(
        "[FAIL] Build attestation preparation requires python -I -S",
        file=sys.stderr,
    )
    raise SystemExit(1)

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence


ATTESTATION_FILENAME = ".semantic_audit_build_provenance.json"
ATTESTATION_SCHEMA_VERSION = "phase1-semantic-audit-build-provenance/v1"
BUNDLE_HASH_DOMAIN = b"jspace-semantic-audit/protocol-bundle/v1\0"
RUNTIME_FILES = (
    ".dockerignore",
    ".gitignore",
    "Dockerfile",
    "docs/phase1_semantic_review_protocol.md",
    "infra/azure/scripts/00_check_prereqs.ps1",
    "infra/azure/scripts/00_check_prereqs.sh",
    "infra/azure/scripts/01_build_and_push_image.sh",
    "infra/azure/scripts/02_run_phase0_5.sh",
    "infra/azure/scripts/03_run_phase1.sh",
    "infra/azure/scripts/04_run_phase1_pilot.sh",
    "infra/azure/scripts/05_run_job_ghcr.sh",
    "infra/azure/scripts/06_run_job_acr_mi.sh",
    "requirements.txt",
    "scripts/audit_phase1_blob_run.py",
    "scripts/blob_export_smoke.py",
    "scripts/export_phase1_semantic_review_pack.py",
    "scripts/finalize_phase1_semantic_audit.py",
    "scripts/prepare_semantic_audit_build_context.py",
    "src/jspace_observation/__init__.py",
    "src/jspace_observation/blob_export.py",
    "src/jspace_observation/config.py",
    "src/jspace_observation/eval_parsing.py",
    "src/jspace_observation/jlens_utils.py",
    "src/jspace_observation/model_loader.py",
    "src/jspace_observation/no_cot.py",
    "src/jspace_observation/phase1_branches.py",
    "src/jspace_observation/postprocess.py",
    "src/jspace_observation/prompt_sets.py",
    "src/jspace_observation/record_audit.py",
    "src/jspace_observation/run_logging.py",
    "src/jspace_observation/semantic_audit.py",
    "src/jspace_observation/stats.py",
)
BEHAVIOR_ROOTS = (
    "src",
    "scripts",
    "infra/azure/scripts",
    "Dockerfile",
    "requirements.txt",
    "docs/phase1_semantic_review_protocol.md",
    ".dockerignore",
    ".gitignore",
)
ATTESTATION_FIELDS = frozenset(
    {
        "schema_version",
        "protocol_commit",
        "protocol_bundle_sha256",
        "bundle_hash_domain",
        "runtime_files",
        "file_sha256",
        "generated_from_clean_git",
    }
)
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class PreparationError(RuntimeError):
    """Raised when a build context cannot be trusted."""


def _canonical_json_bytes(value: Any) -> bytes:
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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_commit(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not _COMMIT_PATTERN.fullmatch(value)
        or value == "0" * 40
    ):
        raise PreparationError(
            "protocol commit must be a nonzero lowercase 40-character Git commit"
        )
    return value


def _validate_digest(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _SHA256_PATTERN.fullmatch(value)
        or value == "0" * 64
    ):
        raise PreparationError(f"{label} must be a nonzero lowercase SHA-256")
    return value


def _run_git(
    root: Path, arguments: Sequence[str], *, text: bool = True
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=text,
        check=False,
    )


def _require_git_success(
    root: Path, arguments: Sequence[str], label: str, *, text: bool = True
) -> subprocess.CompletedProcess[Any]:
    result = _run_git(root, arguments, text=text)
    if result.returncode != 0:
        detail = result.stderr.strip() if text else ""
        raise PreparationError(f"{label} failed" + (f": {detail}" if detail else ""))
    return result


def _bundle_sha256(root: Path) -> tuple[str, dict[str, str]]:
    digest = hashlib.sha256()
    digest.update(BUNDLE_HASH_DOMAIN)
    file_digests: dict[str, str] = {}
    for relative in RUNTIME_FILES:
        path = root.joinpath(*relative.split("/"))
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise PreparationError(f"runtime file is unavailable: {relative}") from exc
        encoded = relative.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        file_digests[relative] = _sha256(data)
    return digest.hexdigest(), file_digests


def _listed_behavior_files(root: Path) -> set[str]:
    files: set[str] = set()
    for relative_root in ("src", "scripts", "infra/azure/scripts"):
        directory = root.joinpath(*relative_root.split("/"))
        if not directory.is_dir():
            raise PreparationError(f"behavior root is unavailable: {relative_root}")
        for path in directory.rglob("*"):
            if path.is_file():
                files.add(path.relative_to(root).as_posix())
    for relative in (
        "Dockerfile",
        "requirements.txt",
        "docs/phase1_semantic_review_protocol.md",
        ".dockerignore",
        ".gitignore",
    ):
        if root.joinpath(*relative.split("/")).is_file():
            files.add(relative)
    return files


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError(f"duplicate attestation key: {key}")
        result[key] = value
    return result


def validate_attestation(root: Path, attestation_path: Path) -> dict[str, Any]:
    """Validate the exact file list, every digest, and the canonical bundle."""
    root = root.resolve()
    try:
        data = attestation_path.read_bytes()
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                PreparationError(f"non-finite attestation value: {token}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreparationError("build attestation is missing or malformed") from exc
    if not isinstance(value, dict) or set(value) != set(ATTESTATION_FIELDS):
        raise PreparationError("build attestation fields must match exactly")
    if _canonical_json_bytes(value) != data:
        raise PreparationError("build attestation is not canonical JSON")
    if value.get("schema_version") != ATTESTATION_SCHEMA_VERSION:
        raise PreparationError("build attestation schema mismatch")
    commit = _validate_commit(value.get("protocol_commit"))
    expected_bundle = _validate_digest(
        value.get("protocol_bundle_sha256"), "protocol bundle"
    )
    if value.get("bundle_hash_domain") != BUNDLE_HASH_DOMAIN.decode("ascii").rstrip(
        "\0"
    ):
        raise PreparationError("build attestation bundle domain mismatch")
    if value.get("runtime_files") != list(RUNTIME_FILES):
        raise PreparationError("build attestation runtime file list mismatch")
    file_digests = value.get("file_sha256")
    if not isinstance(file_digests, dict) or list(file_digests) != sorted(RUNTIME_FILES):
        raise PreparationError("build attestation file digest list mismatch")
    if value.get("generated_from_clean_git") is not True:
        raise PreparationError("build attestation lacks the clean-Git assertion")
    if _listed_behavior_files(root) != set(RUNTIME_FILES):
        raise PreparationError("build context behavior file membership mismatch")
    actual_bundle, actual_digests = _bundle_sha256(root)
    for relative in RUNTIME_FILES:
        _validate_digest(file_digests.get(relative), f"{relative} digest")
    if file_digests != actual_digests:
        raise PreparationError("build attestation file digest mismatch")
    if expected_bundle != actual_bundle:
        raise PreparationError("build attestation bundle digest mismatch")
    return {
        **value,
        "protocol_commit": commit,
        "protocol_bundle_sha256": actual_bundle,
    }


def prepare_build_context(root: Path, protocol_commit: str) -> Path:
    """Generate the attestation only from an exact clean committed context."""
    root = root.resolve()
    commit = _validate_commit(protocol_commit)
    top = _require_git_success(
        root, ["rev-parse", "--show-toplevel"], "locating Git worktree"
    ).stdout.strip()
    if Path(top).resolve() != root:
        raise PreparationError("project root must equal the Git worktree root")
    _require_git_success(
        root, ["cat-file", "-e", f"{commit}^{{commit}}"], "protocol commit lookup"
    )
    head = _require_git_success(root, ["rev-parse", "HEAD"], "reading HEAD").stdout.strip()
    if head != commit:
        raise PreparationError("HEAD must equal the explicit protocol commit")
    for arguments, label in (
        (["diff", "--quiet", "--exit-code"], "tracked working tree"),
        (["diff", "--cached", "--quiet", "--exit-code"], "Git index"),
    ):
        result = _run_git(root, arguments)
        if result.returncode != 0:
            raise PreparationError(f"{label} must be clean")

    tracked = set(
        _require_git_success(
            root,
            ["ls-files", "--", *BEHAVIOR_ROOTS],
            "listing tracked behavior files",
        ).stdout.splitlines()
    )
    if tracked != set(RUNTIME_FILES):
        raise PreparationError("tracked behavior file list differs from the frozen list")
    untracked: set[str] = set()
    for arguments in (
        ["ls-files", "--others", "--exclude-standard", "--", *BEHAVIOR_ROOTS],
        [
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--",
            *BEHAVIOR_ROOTS,
        ],
    ):
        untracked.update(
            _require_git_success(
                root, arguments, "checking untracked behavior files"
            ).stdout.splitlines()
        )
    if untracked:
        raise PreparationError(
            "untracked files are forbidden in behavior/import roots: "
            + ", ".join(sorted(untracked))
        )

    for relative in RUNTIME_FILES:
        committed_object = _require_git_success(
            root,
            ["rev-parse", f"{commit}:{relative}"],
            f"reading committed runtime object {relative}",
        ).stdout.strip()
        working_object = _require_git_success(
            root,
            ["hash-object", f"--path={relative}", relative],
            f"hashing filtered runtime file {relative}",
        ).stdout.strip()
        if committed_object != working_object:
            raise PreparationError(f"runtime file differs from commit: {relative}")

    bundle, file_digests = _bundle_sha256(root)
    attestation = {
        "schema_version": ATTESTATION_SCHEMA_VERSION,
        "protocol_commit": commit,
        "protocol_bundle_sha256": bundle,
        "bundle_hash_domain": BUNDLE_HASH_DOMAIN.decode("ascii").rstrip("\0"),
        "runtime_files": list(RUNTIME_FILES),
        "file_sha256": dict(sorted(file_digests.items())),
        "generated_from_clean_git": True,
    }
    output = root / ATTESTATION_FILENAME
    try:
        with output.open("xb") as stream:
            stream.write(_canonical_json_bytes(attestation))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise PreparationError(
            "generated attestation path must not already exist"
        ) from exc
    validate_attestation(root, output)
    return output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--protocol-commit")
    mode.add_argument("--validate-attestation", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.project_root.resolve()
    if args.protocol_commit is not None:
        path = prepare_build_context(root, args.protocol_commit)
        print(path)
    else:
        validate_attestation(root, args.validate_attestation.resolve())
        print(args.validate_attestation.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
