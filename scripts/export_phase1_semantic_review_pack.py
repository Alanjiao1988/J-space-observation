#!/usr/bin/env python3
"""Release one provenance-bound stage of the preregistered semantic review."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import sysconfig
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
EXPECTED_RECORD_COUNT = 45
FROZEN_SHUFFLE_SEED = 20260711
PROTOCOL_COMMIT_ENV = "JSPACE_SEMANTIC_PROTOCOL_COMMIT"
BUILD_ATTESTATION_SCHEMA_VERSION = "phase1-semantic-audit-build-provenance/v1"
BAKED_BUILD_ATTESTATION_PATH = Path(
    "/opt/jspace/semantic-audit-build-provenance.json"
)
PROTOCOL_BUNDLE_HASH_DOMAIN = b"jspace-semantic-audit/protocol-bundle/v1\0"
PROTOCOL_RUNTIME_FILES = (
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
SOURCE_ARTIFACT_HASHES = {
    "phase1_generations.jsonl": (
        "b45c972af6f8a2be771e308d943ff793bdafd44c486a4eae9ea8a4e7f1ec11a0"
    ),
    "phase1_eval_records.jsonl": (
        "57aee97ef98a9be14e489bf6aa4a6e09a80fd5ceedb2df8fadc8d991be98538b"
    ),
}
STAGE1_PACKET_FILENAME = "all45_review_packet_blinded.jsonl"
STAGE2_PACKET_FILENAME = "all45_review_packet_stage2.jsonl"
RELEASE_MANIFEST_FILENAMES = {
    "stage1": "all45_stage1_release_manifest.json",
    "stage2": "all45_stage2_release_manifest.json",
}
RELEASE_RESERVATION_FILENAME = ".semantic_audit_release_reservation.json"
_BEHAVIOR_ROOTS = (
    "src",
    "scripts",
    "infra/azure/scripts",
    "Dockerfile",
    "requirements.txt",
    "docs/phase1_semantic_review_protocol.md",
    ".dockerignore",
    ".gitignore",
)
_ATTESTATION_FIELDS = {
    "schema_version",
    "protocol_commit",
    "protocol_bundle_sha256",
    "bundle_hash_domain",
    "runtime_files",
    "file_sha256",
    "generated_from_clean_git",
}
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_RUNTIME_LOADED = False
_RUNTIME_VERIFIED = False


class SemanticAuditBootstrapError(RuntimeError):
    """Raised before any project or Azure import is allowed."""


SemanticAuditError = SemanticAuditBootstrapError

_STDLIB_MODULE_NAMES = (
    "argparse",
    "hashlib",
    "importlib",
    "json",
    "os",
    "pathlib",
    "re",
    "subprocess",
    "sysconfig",
    "types",
    "typing",
)


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolved_sysconfig_roots(*names: str) -> tuple[Path, ...]:
    paths = sysconfig.get_paths()
    roots: list[Path] = []
    for name in names:
        raw = paths.get(name)
        if not isinstance(raw, str) or not raw:
            raise SemanticAuditBootstrapError(
                f"interpreter sysconfig path is unavailable: {name}"
            )
        try:
            root = Path(raw).resolve(strict=True)
        except OSError as exc:
            raise SemanticAuditBootstrapError(
                f"interpreter sysconfig path is unavailable: {name}"
            ) from exc
        if root not in roots:
            roots.append(root)
    return tuple(roots)


def _protected_import_roots() -> tuple[Path, ...]:
    roots = (
        PROJECT_ROOT.resolve(),
        Path.cwd().resolve(),
        Path(__file__).resolve().parent,
        SRC_ROOT.resolve(),
    )
    return tuple(dict.fromkeys(roots))


def _require_secure_interpreter(
    environment: Mapping[str, str], flags: Any | None = None
) -> None:
    if environment.get("PYTHONPATH", ""):
        raise SemanticAuditBootstrapError(
            "semantic audit rejects every nonempty external PYTHONPATH"
        )
    active_flags = sys.flags if flags is None else flags
    if (
        getattr(active_flags, "isolated", 0) != 1
        or getattr(active_flags, "safe_path", False) is not True
        or getattr(active_flags, "no_site", 0) != 1
    ):
        raise SemanticAuditBootstrapError(
            "semantic audit must be invoked with isolated safe-path Python: "
            "python -I -S"
        )


def _verify_stdlib_import_origins() -> None:
    stdlib_roots = _resolved_sysconfig_roots("stdlib", "platstdlib")
    package_roots = _resolved_sysconfig_roots("purelib", "platlib")
    protected_roots = _protected_import_roots()
    for name in _STDLIB_MODULE_NAMES:
        module = sys.modules.get(name)
        if module is None:
            raise SemanticAuditBootstrapError(
                f"required stdlib module is not loaded: {name}"
            )
        spec = getattr(module, "__spec__", None)
        spec_origin = getattr(spec, "origin", None)
        if spec_origin in {"built-in", "frozen"}:
            continue
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str):
            raise SemanticAuditBootstrapError(f"{name} has no stdlib import origin")
        try:
            path = Path(origin).resolve(strict=True)
        except OSError as exc:
            raise SemanticAuditBootstrapError(
                f"{name} stdlib import origin is unavailable"
            ) from exc
        if (
            not any(_path_is_within(path, root) for root in stdlib_roots)
            or any(_path_is_within(path, root) for root in package_roots)
            or any(_path_is_within(path, root) for root in protected_roots)
        ):
            raise SemanticAuditBootstrapError(
                f"{name} was not imported from the interpreter stdlib: {path}"
            )


def _trusted_interpreter_sys_path() -> list[str]:
    package_roots = _resolved_sysconfig_roots("purelib", "platlib")
    data_roots = _resolved_sysconfig_roots("data")
    protected_roots = _protected_import_roots()
    trusted: list[Path] = []
    for item in sys.path:
        if not item:
            continue
        resolved = Path(item).resolve()
        is_exact_package_root = resolved in package_roots
        is_interpreter_path = any(
            _path_is_within(resolved, root) for root in data_roots
        ) and not any(
            _path_is_within(resolved, root) and resolved != root
            for root in package_roots
        )
        if (
            (is_exact_package_root or is_interpreter_path)
            and not any(
                _path_is_within(resolved, root) for root in protected_roots
            )
            and resolved not in trusted
        ):
            trusted.append(resolved)
    for root in (*_resolved_sysconfig_roots("stdlib", "platstdlib"), *package_roots):
        if root not in trusted:
            trusted.append(root)
    return [str(path) for path in trusted]


def _bootstrap_canonical_json_bytes(value: Any) -> bytes:
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


def _bootstrap_reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SemanticAuditBootstrapError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _bootstrap_validate_commit(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _COMMIT_PATTERN.fullmatch(value)
        or value == "0" * 40
    ):
        raise SemanticAuditBootstrapError(
            f"{label} must be a nonzero lowercase 40-character Git commit"
        )
    return value


def _bootstrap_validate_digest(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _SHA256_PATTERN.fullmatch(value)
        or value == "0" * 64
    ):
        raise SemanticAuditBootstrapError(
            f"{label} must be a nonzero lowercase SHA-256"
        )
    return value


def _bootstrap_bundle(root: Path) -> tuple[str, dict[str, str]]:
    digest = hashlib.sha256(PROTOCOL_BUNDLE_HASH_DOMAIN)
    file_digests: dict[str, str] = {}
    for relative in PROTOCOL_RUNTIME_FILES:
        try:
            data = root.joinpath(*relative.split("/")).read_bytes()
        except OSError as exc:
            raise SemanticAuditBootstrapError(
                f"protocol runtime file is unavailable: {relative}"
            ) from exc
        encoded = relative.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        file_digests[relative] = hashlib.sha256(data).hexdigest()
    return digest.hexdigest(), dict(sorted(file_digests.items()))


def _bootstrap_behavior_files(root: Path) -> set[str]:
    files: set[str] = set()
    for relative_root in ("src", "scripts", "infra/azure/scripts"):
        directory = root.joinpath(*relative_root.split("/"))
        if not directory.is_dir():
            raise SemanticAuditBootstrapError(
                f"behavior root is unavailable: {relative_root}"
            )
        files.update(
            path.relative_to(root).as_posix()
            for path in directory.rglob("*")
            if path.is_file()
        )
    for relative in _BEHAVIOR_ROOTS[3:]:
        if root.joinpath(*relative.split("/")).is_file():
            files.add(relative)
    return files


def _bootstrap_git(
    root: Path, arguments: Sequence[str], *, text: bool = True
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=text,
        check=False,
    )


def _bootstrap_git_lines(
    root: Path, arguments: Sequence[str], label: str
) -> list[str]:
    result = _bootstrap_git(root, arguments)
    if result.returncode != 0:
        raise SemanticAuditBootstrapError(f"{label} failed")
    return result.stdout.splitlines()


def _bootstrap_provenance_record(
    commit: str,
    bundle: str,
    file_sha256: Mapping[str, str],
    verification_mode: str,
    git_checks_performed: bool,
) -> dict[str, Any]:
    return {
        "protocol_commit": commit,
        "protocol_bundle_sha256": bundle,
        "bundle_hash_domain": PROTOCOL_BUNDLE_HASH_DOMAIN.decode("ascii").rstrip(
            "\0"
        ),
        "runtime_files": list(PROTOCOL_RUNTIME_FILES),
        "file_sha256": dict(sorted(file_sha256.items())),
        "attestation_schema_version": BUILD_ATTESTATION_SCHEMA_VERSION,
        "generated_from_clean_git": True,
        "verification_mode": verification_mode,
        "git_checks_performed": git_checks_performed,
        "verified": True,
    }


def _bootstrap_verify_provenance(
    environment: Mapping[str, str],
    *,
    project_root: Path,
    baked_attestation_path: Path = BAKED_BUILD_ATTESTATION_PATH,
) -> dict[str, Any]:
    root = project_root.resolve()
    requested = environment.get(PROTOCOL_COMMIT_ENV)
    if requested is not None:
        requested = _bootstrap_validate_commit(requested, PROTOCOL_COMMIT_ENV)
    if (root / ".git").exists():
        head_result = _bootstrap_git(root, ["rev-parse", "HEAD"])
        if head_result.returncode != 0:
            raise SemanticAuditBootstrapError("failed to read local Git HEAD")
        commit = _bootstrap_validate_commit(head_result.stdout.strip(), "Git HEAD")
        if requested is not None and requested != commit:
            raise SemanticAuditBootstrapError(
                "requested protocol commit differs from local HEAD"
            )
        if _bootstrap_git(
            root, ["cat-file", "-e", f"{commit}^{{commit}}"]
        ).returncode:
            raise SemanticAuditBootstrapError("local protocol commit does not exist")
        for arguments, label in (
            (["diff", "--quiet", "--exit-code"], "tracked working tree"),
            (["diff", "--cached", "--quiet", "--exit-code"], "Git index"),
        ):
            if _bootstrap_git(root, arguments).returncode:
                raise SemanticAuditBootstrapError(f"{label} must be clean")
        tracked = set(
            _bootstrap_git_lines(
                root,
                ["ls-files", "--", *_BEHAVIOR_ROOTS],
                "listing tracked behavior files",
            )
        )
        if tracked != set(PROTOCOL_RUNTIME_FILES):
            raise SemanticAuditBootstrapError(
                "tracked behavior files differ from the frozen list"
            )
        untracked: set[str] = set()
        for arguments in (
            [
                "ls-files",
                "--others",
                "--exclude-standard",
                "--",
                *_BEHAVIOR_ROOTS,
            ],
            [
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "--",
                *_BEHAVIOR_ROOTS,
            ],
        ):
            untracked.update(
                _bootstrap_git_lines(
                    root, arguments, "checking untracked behavior files"
                )
            )
        if untracked:
            raise SemanticAuditBootstrapError(
                "untracked behavior/import file(s): " + ", ".join(sorted(untracked))
            )
        for relative in PROTOCOL_RUNTIME_FILES:
            committed = _bootstrap_git(
                root, ["show", f"{commit}:{relative}"], text=False
            )
            if committed.returncode != 0 or committed.stdout != root.joinpath(
                *relative.split("/")
            ).read_bytes():
                raise SemanticAuditBootstrapError(
                    f"runtime file differs from commit: {relative}"
                )
        bundle, file_sha256 = _bootstrap_bundle(root)
        return _bootstrap_provenance_record(
            commit,
            bundle,
            file_sha256,
            "local_git_and_bundle",
            True,
        )

    try:
        attestation_bytes = baked_attestation_path.resolve().read_bytes()
        attestation = json.loads(
            attestation_bytes.decode("utf-8"),
            object_pairs_hook=_bootstrap_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                SemanticAuditBootstrapError(
                    f"non-finite attestation value: {token}"
                )
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticAuditBootstrapError(
            "baked build attestation is missing or malformed"
        ) from exc
    if (
        not isinstance(attestation, dict)
        or set(attestation) != _ATTESTATION_FIELDS
        or _bootstrap_canonical_json_bytes(attestation) != attestation_bytes
        or attestation.get("schema_version") != BUILD_ATTESTATION_SCHEMA_VERSION
        or attestation.get("runtime_files") != list(PROTOCOL_RUNTIME_FILES)
        or attestation.get("bundle_hash_domain")
        != PROTOCOL_BUNDLE_HASH_DOMAIN.decode("ascii").rstrip("\0")
        or attestation.get("generated_from_clean_git") is not True
    ):
        raise SemanticAuditBootstrapError("baked build attestation is invalid")
    commit = _bootstrap_validate_commit(
        attestation.get("protocol_commit"), "baked protocol commit"
    )
    if requested is not None and requested != commit:
        raise SemanticAuditBootstrapError(
            "requested protocol commit differs from baked attestation"
        )
    expected_bundle = _bootstrap_validate_digest(
        attestation.get("protocol_bundle_sha256"), "baked bundle"
    )
    expected_files = attestation.get("file_sha256")
    if not isinstance(expected_files, dict) or set(expected_files) != set(
        PROTOCOL_RUNTIME_FILES
    ):
        raise SemanticAuditBootstrapError("baked file digest list mismatch")
    for relative in PROTOCOL_RUNTIME_FILES:
        _bootstrap_validate_digest(
            expected_files.get(relative), f"baked digest for {relative}"
        )
    if _bootstrap_behavior_files(root) != set(PROTOCOL_RUNTIME_FILES):
        raise SemanticAuditBootstrapError("baked behavior file membership mismatch")
    actual_bundle, actual_files = _bootstrap_bundle(root)
    if expected_files != actual_files or expected_bundle != actual_bundle:
        raise SemanticAuditBootstrapError("baked runtime differs from attestation")
    return _bootstrap_provenance_record(
        commit,
        actual_bundle,
        actual_files,
        "baked_image_attestation",
        False,
    )


def _require_interpreter_package_origin(module: ModuleType, name: str) -> None:
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str):
        raise SemanticAuditBootstrapError(f"{name} has no import origin")
    try:
        path = Path(origin).resolve(strict=True)
    except OSError as exc:
        raise SemanticAuditBootstrapError(
            f"{name} import origin is unavailable"
        ) from exc
    package_roots = _resolved_sysconfig_roots("purelib", "platlib")
    protected_roots = _protected_import_roots()
    if not any(_path_is_within(path, root) for root in package_roots):
        raise SemanticAuditBootstrapError(
            f"{name} was not imported from an exact interpreter package root: {path}"
        )
    if any(_path_is_within(path, root) for root in protected_roots):
        raise SemanticAuditBootstrapError(
            f"{name} was imported from a protected project/cwd/script root: {path}"
        )


def _verify_frozen_module_origins() -> None:
    expected: dict[str, Path] = {}
    prefix = "src/jspace_observation/"
    for relative in PROTOCOL_RUNTIME_FILES:
        if relative.startswith(prefix) and relative.endswith(".py"):
            filename = relative[len(prefix) :]
            module_name = (
                "jspace_observation"
                if filename == "__init__.py"
                else f"jspace_observation.{filename[:-3].replace('/', '.')}"
            )
            expected[module_name] = PROJECT_ROOT.joinpath(
                *relative.split("/")
            ).resolve()
    for name, module in list(sys.modules.items()):
        if name != "jspace_observation" and not name.startswith(
            "jspace_observation."
        ):
            continue
        origin = getattr(module, "__file__", None)
        if (
            name not in expected
            or origin is None
            or Path(origin).resolve() != expected[name]
        ):
            raise SemanticAuditBootstrapError(
                f"unexpected frozen-module origin for {name}: {origin}"
            )


def _install_semantic_runtime(module: ModuleType) -> None:
    global _RUNTIME_LOADED, _semantic_audit_module
    names = (
        "EXPECTED_RECORD_COUNT",
        "FROZEN_SHUFFLE_SEED",
        "PROTOCOL_COMMIT_ENV",
        "PROTOCOL_RUNTIME_FILES",
        "RELEASE_MANIFEST_FILENAMES",
        "RELEASE_RESERVATION_FILENAME",
        "SOURCE_ARTIFACT_HASHES",
        "STAGE1_PACKET_FILENAME",
        "STAGE2_PACKET_FILENAME",
        "SemanticAuditError",
        "_mint_verified_source_evidence_for_exporter",
        "build_release_files",
        "build_review_pack",
        "canonical_json_bytes",
        "canonical_json_text",
        "normalize_blob_prefix",
        "parse_json_object_strict",
        "parse_jsonl_strict",
        "sha256_bytes",
        "validate_semantic_audit_prefixes",
        "validate_stage_release",
        "validate_stage_release_files",
        "validate_submission_artifact",
        "validate_protocol_provenance_record",
    )
    for name in names:
        globals()[name] = getattr(module, name)
    _semantic_audit_module = module
    _RUNTIME_LOADED = True


def _load_runtime_after_bootstrap(provenance: Mapping[str, Any]) -> None:
    global _RUNTIME_VERIFIED
    prohibited = sorted(
        name
        for name in sys.modules
        if name == "jspace_observation"
        or name.startswith("jspace_observation.")
        or name == "azure.identity"
        or name.startswith("azure.identity.")
        or name == "azure.storage.blob"
        or name.startswith("azure.storage.blob.")
    )
    if prohibited:
        raise SemanticAuditBootstrapError(
            f"refusing preloaded protected modules: {prohibited}"
        )
    sys.path[:] = _trusted_interpreter_sys_path()
    identity_module = importlib.import_module("azure.identity")
    blob_module = importlib.import_module("azure.storage.blob")
    _require_interpreter_package_origin(identity_module, "azure.identity")
    _require_interpreter_package_origin(blob_module, "azure.storage.blob")
    globals()["ManagedIdentityCredential"] = identity_module.ManagedIdentityCredential
    globals()["BlobServiceClient"] = blob_module.BlobServiceClient
    core_module = importlib.import_module("azure.core")
    _require_interpreter_package_origin(core_module, "azure.core")
    globals()["MatchConditions"] = core_module.MatchConditions
    sys.path.insert(0, str(SRC_ROOT.resolve()))
    module = importlib.import_module("jspace_observation.semantic_audit")
    if tuple(module.PROTOCOL_RUNTIME_FILES) != PROTOCOL_RUNTIME_FILES:
        raise SemanticAuditBootstrapError("runtime file constants disagree")
    _install_semantic_runtime(module)
    _verify_frozen_module_origins()
    module.validate_protocol_provenance_record(provenance)
    _RUNTIME_VERIFIED = True


def _load_runtime_for_tests() -> None:
    """Install project helpers for model-free unit tests; production main rejects it."""
    if _RUNTIME_LOADED:
        return
    if str(SRC_ROOT.resolve()) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT.resolve()))
    _install_semantic_runtime(
        importlib.import_module("jspace_observation.semantic_audit")
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-stage", choices=("stage1", "stage2"), required=True)
    parser.add_argument("--storage-account", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--source-prefix", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--expected-records", type=int, default=EXPECTED_RECORD_COUNT)
    parser.add_argument("--shuffle-seed", type=int, default=FROZEN_SHUFFLE_SEED)
    parser.add_argument("--output-dir")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--print-blinded-packet", action="store_true")
    parser.add_argument("--print-stage2-packet", action="store_true")
    parser.add_argument("--stage1-reviewer-a")
    parser.add_argument("--stage1-reviewer-a-seal")
    parser.add_argument("--stage1-reviewer-b")
    parser.add_argument("--stage1-reviewer-b-seal")
    stage1_release = parser.add_mutually_exclusive_group()
    stage1_release.add_argument("--stage1-release-dir")
    stage1_release.add_argument("--stage1-release-prefix")
    args = parser.parse_args(argv)
    if type(args.expected_records) is not int or args.expected_records != EXPECTED_RECORD_COUNT:
        parser.error("--expected-records must be exactly 45")
    if type(args.shuffle_seed) is not int or args.shuffle_seed != FROZEN_SHUFFLE_SEED:
        parser.error(f"--shuffle-seed must be exactly {FROZEN_SHUFFLE_SEED}")
    stage1_inputs = (
        args.stage1_reviewer_a,
        args.stage1_reviewer_a_seal,
        args.stage1_reviewer_b,
        args.stage1_reviewer_b_seal,
    )
    if args.release_stage == "stage2" and not all(stage1_inputs):
        parser.error("Stage-2 release requires two Stage-1 submissions and their seals")
    if args.release_stage == "stage2" and not (
        args.stage1_release_dir or args.stage1_release_prefix
    ):
        parser.error("Stage-2 release requires a completed Stage-1 release")
    if args.release_stage == "stage1" and any(stage1_inputs):
        parser.error("Stage-1 release cannot accept reviewer submissions")
    if args.release_stage == "stage1" and (
        args.stage1_release_dir or args.stage1_release_prefix
    ):
        parser.error("Stage-1 release cannot accept a prior release")
    if args.release_stage == "stage1" and args.print_stage2_packet:
        parser.error("Stage-1 release cannot print Stage-2 references")
    if args.release_stage == "stage2" and args.print_blinded_packet:
        parser.error("Stage-2 release cannot print the Stage-1 packet")
    if not args.output_dir and not args.upload:
        parser.error("a release requires --output-dir or --upload")
    return args


def resolve_protocol_provenance(
    environ: Mapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
    baked_attestation_path: Path = BAKED_BUILD_ATTESTATION_PATH,
) -> dict[str, Any]:
    environment = os.environ if environ is None else environ
    provenance = _bootstrap_verify_provenance(
        environment,
        project_root=project_root,
        baked_attestation_path=baked_attestation_path,
    )
    if _RUNTIME_LOADED:
        return validate_protocol_provenance_record(provenance)
    return provenance


def _property_snapshot(properties: Any) -> dict[str, Any]:
    size = getattr(properties, "size", None)
    if size is None:
        size = getattr(properties, "content_length", None)
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise SemanticAuditError("Blob properties contain an invalid content length")
    last_modified = getattr(properties, "last_modified", None)
    return {
        "content_length": size,
        "etag": str(getattr(properties, "etag", "")),
        "last_modified": (
            last_modified.isoformat()
            if hasattr(last_modified, "isoformat")
            else None
            if last_modified is None
            else str(last_modified)
        ),
        "version_id": getattr(properties, "version_id", None),
    }


def _source_properties_equal(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> bool:
    return all(
        type(before.get(field)) is type(after.get(field))
        and before.get(field) == after.get(field)
        for field in ("content_length", "etag", "last_modified", "version_id")
    )


def _download_with_etag(blob: Any, etag: str) -> tuple[bytes, bool]:
    match_conditions = globals().get("MatchConditions")
    if match_conditions is None:
        stream = blob.download_blob(max_concurrency=1)
        return stream.readall(), False
    try:
        stream = blob.download_blob(
            etag=etag,
            match_condition=match_conditions.IfNotModified,
            max_concurrency=1,
        )
        return stream.readall(), True
    except TypeError:
        stream = blob.download_blob(max_concurrency=1)
        return stream.readall(), False


def _download_exact_sources_with_verified_evidence(
    service: Any,
    container: str,
    source_prefix: str,
) -> tuple[dict[str, bytes], Any]:
    """Download only the two exact source names in memory with hash/ETag checks."""
    prefix = normalize_blob_prefix(source_prefix)
    artifacts: dict[str, bytes] = {}
    source_manifest: list[dict[str, Any]] = []
    tracked_blobs: list[tuple[Any, dict[str, Any], dict[str, Any]]] = []
    for name, expected_hash in SOURCE_ARTIFACT_HASHES.items():
        blob_name = f"{prefix}/{name}"
        blob = service.get_blob_client(container=container, blob=blob_name)
        before = _property_snapshot(blob.get_blob_properties())
        if not before["etag"]:
            raise SemanticAuditError(f"{name} has no before-read ETag")
        data, conditional_supported = _download_with_etag(blob, before["etag"])
        if len(data) != before["content_length"]:
            raise SemanticAuditError(f"{name} byte count differs from Blob properties")
        actual_hash = sha256_bytes(data)
        if actual_hash != expected_hash:
            raise SemanticAuditError(f"{name} failed the preregistered SHA-256 check")
        after = _property_snapshot(blob.get_blob_properties())
        if not _source_properties_equal(before, after):
            raise SemanticAuditError(f"{name} properties changed across the read")
        artifacts[name] = data
        entry = {
            "name": name,
            "sha256": actual_hash,
            "before_read": before,
            "after_read": after,
            "conditional_etag_read": conditional_supported,
            "unchanged": True,
        }
        source_manifest.append(entry)
        tracked_blobs.append((blob, before, entry))
    for blob, before, entry in tracked_blobs:
        final_properties = _property_snapshot(blob.get_blob_properties())
        if not _source_properties_equal(before, final_properties):
            raise SemanticAuditError(
                f"{entry['name']} properties changed after all source reads"
            )
        entry["after_all_source_reads"] = final_properties
    source_immutability = {
        "confirmed_unchanged": True,
        "comparison_fields": [
            "content_length",
            "etag",
            "last_modified",
            "version_id",
        ],
        "source_write_attempted": False,
        "evidence_mode": "verified_source_bytes",
    }
    return (
        artifacts,
        _mint_verified_source_evidence_for_exporter(
            artifacts, source_manifest, source_immutability
        ),
    )


def _blob_service(storage_account: str) -> Any:
    client_id = os.getenv("AZURE_CLIENT_ID")
    if not client_id:
        raise SemanticAuditError("AZURE_CLIENT_ID is required")
    credential = ManagedIdentityCredential(client_id=client_id)
    return BlobServiceClient(
        account_url=f"https://{storage_account}.blob.core.windows.net",
        credential=credential,
    )


def planned_release_uploads(output_prefix: str, release_stage: str) -> list[str]:
    prefix = normalize_blob_prefix(output_prefix)
    packet_name = (
        STAGE1_PACKET_FILENAME if release_stage == "stage1" else STAGE2_PACKET_FILENAME
    )
    try:
        manifest_name = RELEASE_MANIFEST_FILENAMES[release_stage]
    except KeyError as exc:
        raise SemanticAuditError("release_stage must be stage1 or stage2") from exc
    return [
        f"{prefix}/{RELEASE_RESERVATION_FILENAME}",
        f"{prefix}/{packet_name}",
        f"{prefix}/{manifest_name}",
    ]


def upload_release(
    service: Any,
    container: str,
    output_prefix: str,
    release_stage: str,
    files: Mapping[str, bytes],
) -> list[dict[str, Any]]:
    """Atomically reserve a prefix, upload manifest last, and verify exact membership."""
    planned = planned_release_uploads(output_prefix, release_stage)
    expected_names = [path.rsplit("/", 1)[-1] for path in planned]
    if list(files) != expected_names or set(files) != set(expected_names):
        raise SemanticAuditError("release file set/order violates the staged contract")
    prefix = normalize_blob_prefix(output_prefix)
    container_client = service.get_container_client(container)

    def prefix_members() -> set[str]:
        names: set[str] = set()
        for item in container_client.list_blobs(name_starts_with=f"{prefix}/"):
            name = item.get("name") if isinstance(item, Mapping) else item.name
            names.add(str(name))
        return names

    if prefix_members():
        raise SemanticAuditError("release Blob prefix must be entirely new and empty")
    blobs = {
        name: service.get_blob_client(container=container, blob=blob_name)
        for name, blob_name in zip(expected_names, planned)
    }
    reservation_name, packet_name, manifest_name = expected_names
    reservation_blob = blobs[reservation_name]
    uploaded: list[dict[str, Any]] = []
    lease = None
    try:
        try:
            reservation_blob.upload_blob(files[reservation_name], overwrite=False)
        except Exception as exc:
            raise SemanticAuditError(
                "release prefix reservation already exists or could not be created"
            ) from exc
        acquire_lease = getattr(reservation_blob, "acquire_lease", None)
        if callable(acquire_lease):
            try:
                lease = acquire_lease()
            except (AttributeError, TypeError):
                lease = None
        if prefix_members() != {planned[0]}:
            raise SemanticAuditError(
                "release prefix changed while acquiring its reservation"
            )

        for name in (reservation_name, packet_name):
            if name == packet_name:
                blobs[name].upload_blob(files[name], overwrite=False)
            verification = blobs[name].download_blob(max_concurrency=1).readall()
            if sha256_bytes(verification) != sha256_bytes(files[name]):
                raise SemanticAuditError(
                    f"uploaded SHA-256 verification failed for {name}"
                )
            uploaded.append(
                {
                    "name": name,
                    "destination": planned[expected_names.index(name)],
                    "sha256": sha256_bytes(files[name]),
                    "verified": True,
                }
            )
        if prefix_members() != set(planned[:2]):
            raise SemanticAuditError(
                "release prefix membership changed before manifest upload"
            )

        blobs[manifest_name].upload_blob(files[manifest_name], overwrite=False)
        if prefix_members() != set(planned):
            raise SemanticAuditError(
                "release prefix membership is not exact after manifest upload"
            )
        for name, blob_name in zip(expected_names, planned):
            verification = blobs[name].download_blob(max_concurrency=1).readall()
            if sha256_bytes(verification) != sha256_bytes(files[name]):
                raise SemanticAuditError(
                    f"final uploaded SHA-256 verification failed for {name}"
                )
            if name == manifest_name:
                uploaded.append(
                    {
                        "name": name,
                        "destination": blob_name,
                        "sha256": sha256_bytes(files[name]),
                        "verified": True,
                    }
                )
        if prefix_members() != set(planned):
            raise SemanticAuditError(
                "release prefix membership changed during final verification"
            )
        return uploaded
    finally:
        release = getattr(lease, "release", None)
        if callable(release):
            release()


def _write_release(output_dir: str, files: Mapping[str, bytes]) -> list[str]:
    root = Path(output_dir)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise SemanticAuditError("release output directory must be new or empty")
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".semantic-release.lock"
    try:
        with lock.open("xb") as stream:
            stream.write(b"release-in-progress\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise SemanticAuditError("another release writer owns the output directory") from exc
    written: list[str] = []
    try:
        if {path.name for path in root.iterdir()} != {lock.name}:
            raise SemanticAuditError("release output directory changed before writing")
        for name, data in files.items():
            path = root / name
            try:
                with path.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise SemanticAuditError(
                    f"release destination already exists: {name}"
                ) from exc
            if sha256_bytes(path.read_bytes()) != sha256_bytes(data):
                raise SemanticAuditError(f"local release verification failed for {name}")
            written.append(str(path))
        if {path.name for path in root.iterdir()} != {
            lock.name,
            *files.keys(),
        }:
            raise SemanticAuditError("release output directory changed during writing")
        return written
    finally:
        lock.unlink(missing_ok=True)


def _read_seal(path: str) -> dict[str, Any]:
    data = Path(path).read_bytes()
    seal = parse_json_object_strict(data, Path(path).name)
    if canonical_json_bytes(seal) != data:
        raise SemanticAuditError("submission seal is not canonically serialized")
    return seal


def _read_completed_stage1_release(
    args: argparse.Namespace,
    service: Any,
) -> tuple[
    bytes,
    dict[str, Any],
    bytes,
    list[dict[str, Any]],
    dict[str, bytes],
]:
    manifest_name = RELEASE_MANIFEST_FILENAMES["stage1"]
    expected_names = {
        RELEASE_RESERVATION_FILENAME,
        STAGE1_PACKET_FILENAME,
        manifest_name,
    }
    if args.stage1_release_dir:
        root = Path(args.stage1_release_dir)
        if not root.is_dir() or {path.name for path in root.iterdir()} != expected_names:
            raise SemanticAuditError(
                "Stage-1 release directory must contain exactly its packet and manifest"
            )
        packet_bytes = (root / STAGE1_PACKET_FILENAME).read_bytes()
        reservation_bytes = (root / RELEASE_RESERVATION_FILENAME).read_bytes()
        manifest_bytes = (root / manifest_name).read_bytes()
    else:
        prefix = normalize_blob_prefix(args.stage1_release_prefix)
        container_client = service.get_container_client(args.container)

        def blob_names() -> set[str]:
            names: set[str] = set()
            for item in container_client.list_blobs(
                name_starts_with=f"{prefix}/"
            ):
                name = item.get("name") if isinstance(item, Mapping) else item.name
                names.add(str(name))
            return names

        expected_blob_names = {
            f"{prefix}/{RELEASE_RESERVATION_FILENAME}",
            f"{prefix}/{STAGE1_PACKET_FILENAME}",
            f"{prefix}/{manifest_name}",
        }
        if blob_names() != expected_blob_names:
            raise SemanticAuditError(
                "Stage-1 Blob prefix must contain exactly its packet and manifest"
            )
        packet_bytes = service.get_blob_client(
            container=args.container,
            blob=f"{prefix}/{STAGE1_PACKET_FILENAME}",
        ).download_blob(max_concurrency=1).readall()
        reservation_bytes = service.get_blob_client(
            container=args.container,
            blob=f"{prefix}/{RELEASE_RESERVATION_FILENAME}",
        ).download_blob(max_concurrency=1).readall()
        manifest_bytes = service.get_blob_client(
            container=args.container,
            blob=f"{prefix}/{manifest_name}",
        ).download_blob(max_concurrency=1).readall()
        if blob_names() != expected_blob_names:
            raise SemanticAuditError("Stage-1 Blob prefix changed during validation")
    release_files = {
        RELEASE_RESERVATION_FILENAME: reservation_bytes,
        STAGE1_PACKET_FILENAME: packet_bytes,
        manifest_name: manifest_bytes,
    }
    validated = validate_stage_release_files(
        release_files, expected_stage="stage1"
    )
    manifest = validated["manifest"]
    records = validated["records"]
    if args.stage1_release_prefix and manifest.get("output_prefix") != prefix:
        raise SemanticAuditError(
            "Stage-1 release manifest does not match its Blob prefix"
        )
    return manifest_bytes, manifest, packet_bytes, records, release_files


def main(argv: list[str] | None = None) -> int:
    if _RUNTIME_LOADED and not _RUNTIME_VERIFIED:
        raise SemanticAuditBootstrapError(
            "production main refuses an unverified test runtime"
        )
    _require_secure_interpreter(os.environ)
    _verify_stdlib_import_origins()
    bootstrap_provenance = _bootstrap_verify_provenance(
        os.environ,
        project_root=PROJECT_ROOT,
        baked_attestation_path=BAKED_BUILD_ATTESTATION_PATH,
    )
    _load_runtime_after_bootstrap(bootstrap_provenance)
    provenance = validate_protocol_provenance_record(bootstrap_provenance)
    args = parse_args(argv)
    source_prefix, output_prefix = validate_semantic_audit_prefixes(
        args.source_prefix, args.output_prefix
    )
    service = _blob_service(args.storage_account)
    source_bytes, source_evidence = _download_exact_sources_with_verified_evidence(
        service, args.container, source_prefix
    )
    pack = build_review_pack(
        source_bytes["phase1_generations.jsonl"],
        source_bytes["phase1_eval_records.jsonl"],
        source_prefix=source_prefix,
        output_prefix=output_prefix,
        protocol_provenance=provenance,
        source_evidence=source_evidence,
        expected_records=args.expected_records,
        shuffle_seed=args.shuffle_seed,
    )

    stage1_submission_artifacts: tuple[tuple[bytes, bytes], ...] = ()
    if args.release_stage == "stage2":
        if Path(args.stage1_reviewer_a).resolve() == Path(
            args.stage1_reviewer_b
        ).resolve() or Path(args.stage1_reviewer_a_seal).resolve() == Path(
            args.stage1_reviewer_b_seal
        ).resolve():
            raise SemanticAuditError("reviewer A and B must use distinct files")
        (
            stage1_release_manifest_bytes,
            stage1_release_manifest,
            released_stage1_packet,
            _,
            stage1_release_files,
        ) = _read_completed_stage1_release(args, service)
        if released_stage1_packet != pack["packet_bytes"][STAGE1_PACKET_FILENAME]:
            raise SemanticAuditError(
                "completed Stage-1 release differs from the reconstructed packet"
            )
        for field in (
            "protocol_commit",
            "protocol_bundle_sha256",
            "source_writer_commit",
            "source_prefix",
            "source_artifacts",
            "source_immutability",
            "source_evidence_mode",
            "source_evidence_sha256",
            "shuffle",
            "mandatory_boundary",
        ):
            if stage1_release_manifest.get(field) != pack["manifest"].get(field):
                raise SemanticAuditError(
                    f"completed Stage-1 release differs on {field}"
                )
        validate_semantic_audit_prefixes(
            str(stage1_release_manifest["output_prefix"]), output_prefix
        )
        if args.output_dir and args.stage1_release_dir:
            prior = Path(args.stage1_release_dir).resolve()
            destination = Path(args.output_dir).resolve()
            if (
                prior == destination
                or prior in destination.parents
                or destination in prior.parents
            ):
                raise SemanticAuditError(
                    "Stage-1 and Stage-2 local release directories must be disjoint"
                )
        stage1_submission_artifacts = (
            (
                Path(args.stage1_reviewer_a).read_bytes(),
                Path(args.stage1_reviewer_a_seal).read_bytes(),
            ),
            (
                Path(args.stage1_reviewer_b).read_bytes(),
                Path(args.stage1_reviewer_b_seal).read_bytes(),
            ),
        )
    release = build_release_files(
        pack,
        args.release_stage,
        stage1_submission_artifacts=stage1_submission_artifacts,
        stage1_release_files=(
            stage1_release_files if args.release_stage == "stage2" else None
        ),
    )
    files = release["files"]
    written = _write_release(args.output_dir, files) if args.output_dir else []
    uploaded = (
        upload_release(
            service, args.container, output_prefix, args.release_stage, files
        )
        if args.upload
        else []
    )

    should_print = (
        args.print_blinded_packet
        if args.release_stage == "stage1"
        else args.print_stage2_packet
    )
    if should_print:
        print(
            "=== STAGE1 BLINDED PACKET BEGIN ==="
            if args.release_stage == "stage1"
            else "=== STAGE2 REFERENCE PACKET BEGIN ==="
        )
        for record in release["packet_records"]:
            print(canonical_json_text(record))
        print(
            "=== STAGE1 BLINDED PACKET END ==="
            if args.release_stage == "stage1"
            else "=== STAGE2 REFERENCE PACKET END ==="
        )
    print("=== SEMANTIC REVIEW RELEASE STATUS ===")
    print(
        canonical_json_text(
            {
                "status": "completed",
                "release_stage": args.release_stage,
                "packet_printed": should_print,
                "record_count": EXPECTED_RECORD_COUNT,
                "uploaded": bool(args.upload),
                "uploaded_files": uploaded,
                "local_release_files": written,
                "model_inference_performed": False,
                "new_behavioral_observations_generated": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("=== SEMANTIC REVIEW RELEASE STATUS ===")
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        raise SystemExit(1)
