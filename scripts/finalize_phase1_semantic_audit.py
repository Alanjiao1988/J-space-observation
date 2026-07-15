#!/usr/bin/env python3
"""Prepare arbitration or privately finalize the two-stage semantic audit."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import sysconfig
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
EXPECTED_RECORD_COUNT = 45
PROTOCOL_COMMIT_ENV = "JSPACE_SEMANTIC_PROTOCOL_COMMIT"
BUILD_ATTESTATION_SCHEMA_VERSION = "phase1-semantic-audit-build-provenance/v1"
BAKED_BUILD_ATTESTATION_PATH = Path(
    "/opt/jspace/semantic-audit-build-provenance.json"
)
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
RELEASE_MANIFEST_FILENAMES = {
    "stage1": "all45_stage1_release_manifest.json",
    "stage2": "all45_stage2_release_manifest.json",
}
RELEASE_RESERVATION_FILENAME = ".semantic_audit_release_reservation.json"
STAGE1_PACKET_FILENAME = "all45_review_packet_blinded.jsonl"
STAGE2_PACKET_FILENAME = "all45_review_packet_stage2.jsonl"
_RUNTIME_LOADED = False
_RUNTIME_VERIFIED = False


class SemanticAuditBootstrapError(RuntimeError):
    """Raised before a sensitive finalizer may import project code."""


SemanticAuditError = SemanticAuditBootstrapError

_STDLIB_MODULE_NAMES = (
    "argparse",
    "copy",
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
        if getattr(spec, "origin", None) in {"built-in", "frozen"}:
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


def _canonical_bootstrap_bytes(value: Any) -> bytes:
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


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SemanticAuditBootstrapError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _validate_commit(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not _COMMIT_PATTERN.fullmatch(value)
        or value == "0" * 40
    ):
        raise SemanticAuditBootstrapError("invalid semantic protocol commit")
    return value


def _validate_digest(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not _SHA256_PATTERN.fullmatch(value)
        or value == "0" * 64
    ):
        raise SemanticAuditBootstrapError("invalid semantic protocol digest")
    return value


def _git(
    root: Path, arguments: Sequence[str], *, text: bool = True
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=text,
        check=False,
    )


def _git_lines(root: Path, arguments: Sequence[str], label: str) -> list[str]:
    result = _git(root, arguments)
    if result.returncode:
        raise SemanticAuditBootstrapError(f"{label} failed")
    return result.stdout.splitlines()


def _preverify_bootstrap_module(
    environment: Mapping[str, str],
    *,
    project_root: Path = PROJECT_ROOT,
    baked_attestation_path: Path = BAKED_BUILD_ATTESTATION_PATH,
) -> ModuleType:
    root = project_root.resolve()
    requested = environment.get(PROTOCOL_COMMIT_ENV)
    if requested is not None:
        requested = _validate_commit(requested)
    protected = (
        "scripts/export_phase1_semantic_review_pack.py",
        "scripts/finalize_phase1_semantic_audit.py",
    )
    if (root / ".git").exists():
        head = _git(root, ["rev-parse", "HEAD"])
        if head.returncode:
            raise SemanticAuditBootstrapError("failed to read local Git HEAD")
        commit = _validate_commit(head.stdout.strip())
        if requested is not None and requested != commit:
            raise SemanticAuditBootstrapError(
                "requested protocol commit differs from local HEAD"
            )
        if _git(root, ["cat-file", "-e", f"{commit}^{{commit}}"]).returncode:
            raise SemanticAuditBootstrapError("local protocol commit does not exist")
        for arguments, label in (
            (["diff", "--quiet", "--exit-code"], "tracked working tree"),
            (["diff", "--cached", "--quiet", "--exit-code"], "Git index"),
        ):
            if _git(root, arguments).returncode:
                raise SemanticAuditBootstrapError(f"{label} must be clean")
        tracked = set(
            _git_lines(
                root,
                ["ls-files", "--", *_BEHAVIOR_ROOTS],
                "listing tracked behavior files",
            )
        )
        if tracked != set(PROTOCOL_RUNTIME_FILES):
            raise SemanticAuditBootstrapError("frozen behavior file list mismatch")
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
                _git_lines(root, arguments, "checking untracked behavior files")
            )
        if untracked:
            raise SemanticAuditBootstrapError(
                "untracked behavior/import file(s): " + ", ".join(sorted(untracked))
            )
        for relative in protected:
            committed = _git(root, ["show", f"{commit}:{relative}"], text=False)
            if committed.returncode or committed.stdout != root.joinpath(
                *relative.split("/")
            ).read_bytes():
                raise SemanticAuditBootstrapError(
                    f"protected bootstrap file differs from commit: {relative}"
                )
    else:
        try:
            data = baked_attestation_path.resolve().read_bytes()
            attestation = json.loads(
                data.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
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
            or _canonical_bootstrap_bytes(attestation) != data
            or attestation.get("schema_version")
            != BUILD_ATTESTATION_SCHEMA_VERSION
            or attestation.get("runtime_files") != list(PROTOCOL_RUNTIME_FILES)
            or attestation.get("generated_from_clean_git") is not True
        ):
            raise SemanticAuditBootstrapError("baked build attestation is invalid")
        commit = _validate_commit(attestation.get("protocol_commit"))
        _validate_digest(attestation.get("protocol_bundle_sha256"))
        if requested is not None and requested != commit:
            raise SemanticAuditBootstrapError(
                "requested protocol commit differs from baked attestation"
            )
        file_sha256 = attestation.get("file_sha256")
        if not isinstance(file_sha256, dict) or set(file_sha256) != set(
            PROTOCOL_RUNTIME_FILES
        ):
            raise SemanticAuditBootstrapError("baked file digest list mismatch")
        for relative in protected:
            expected = _validate_digest(file_sha256.get(relative))
            actual = hashlib.sha256(
                root.joinpath(*relative.split("/")).read_bytes()
            ).hexdigest()
            if actual != expected:
                raise SemanticAuditBootstrapError(
                    f"protected bootstrap digest mismatch: {relative}"
                )

    path = root / "scripts" / "export_phase1_semantic_review_pack.py"
    spec = importlib.util.spec_from_file_location(
        "_verified_semantic_audit_bootstrap", path
    )
    if spec is None or spec.loader is None:
        raise SemanticAuditBootstrapError("cannot load verified bootstrap module")
    module = importlib.util.module_from_spec(spec)
    previous_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous_dont_write
    if tuple(module.PROTOCOL_RUNTIME_FILES) != PROTOCOL_RUNTIME_FILES:
        raise SemanticAuditBootstrapError("bootstrap runtime file constants disagree")
    return module


def _verify_frozen_module_origins() -> None:
    expected: dict[str, Path] = {}
    prefix = "src/jspace_observation/"
    for relative in PROTOCOL_RUNTIME_FILES:
        if relative.startswith(prefix) and relative.endswith(".py"):
            filename = relative[len(prefix) :]
            name = (
                "jspace_observation"
                if filename == "__init__.py"
                else f"jspace_observation.{filename[:-3].replace('/', '.')}"
            )
            expected[name] = PROJECT_ROOT.joinpath(*relative.split("/")).resolve()
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
        "ARBITRATION_PACKET_SCHEMA_VERSION",
        "EXPECTED_RECORD_COUNT",
        "MANDATORY_BOUNDARY_TEXT",
        "PROTOCOL_COMMIT_ENV",
        "PROTOCOL_RUNTIME_FILES",
        "RELEASE_MANIFEST_FILENAMES",
        "RELEASE_RESERVATION_FILENAME",
        "REVIEW_MANIFEST_FILENAME",
        "SOURCE_ARTIFACT_HASHES",
        "STAGE1_PACKET_FILENAME",
        "STAGE2_PACKET_FILENAME",
        "SemanticAuditError",
        "SealedSubmission",
        "_build_restricted_records",
        "build_blinded_arbitration_packet",
        "build_final_machine_outputs",
        "canonical_json_bytes",
        "canonical_json_text",
        "canonical_jsonl_bytes",
        "combine_staged_submission",
        "compute_reviewer_agreement",
        "determine_arbitration_triggers",
        "enrich_final_adjudications",
        "ensure_distinct_reviewer_identities",
        "merge_final_judgments",
        "parse_json_object_strict",
        "parse_jsonl_strict",
        "sha256_bytes",
        "validate_protocol_provenance_record",
        "validate_stage_release",
        "validate_stage_release_files",
        "validate_submission_artifact",
    )
    for name in names:
        globals()[name] = getattr(module, name)
    _semantic_audit_module = module
    _RUNTIME_LOADED = True


def _load_runtime_after_bootstrap(
    bootstrap_module: ModuleType, provenance: Mapping[str, Any]
) -> None:
    global _RUNTIME_VERIFIED
    preloaded = sorted(
        name
        for name in sys.modules
        if name == "jspace_observation" or name.startswith("jspace_observation.")
    )
    if preloaded:
        raise SemanticAuditBootstrapError(
            f"refusing preloaded jspace_observation modules: {preloaded}"
        )
    sys.path[:] = _trusted_interpreter_sys_path()
    sys.path.insert(0, str(SRC_ROOT.resolve()))
    module = importlib.import_module("jspace_observation.semantic_audit")
    if tuple(module.PROTOCOL_RUNTIME_FILES) != PROTOCOL_RUNTIME_FILES:
        raise SemanticAuditBootstrapError("semantic runtime file constants disagree")
    _install_semantic_runtime(module)
    _verify_frozen_module_origins()
    module.validate_protocol_provenance_record(provenance)
    _RUNTIME_VERIFIED = True


def _load_runtime_for_tests() -> None:
    """Install project helpers for model-free tests; production main rejects it."""
    if _RUNTIME_LOADED:
        return
    if str(SRC_ROOT.resolve()) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT.resolve()))
    _install_semantic_runtime(
        importlib.import_module("jspace_observation.semantic_audit")
    )

ARBITRATION_PACKET_FILENAME = "all45_arbitration_packet_blinded.jsonl"
ARBITRATION_PREPARATION_MANIFEST_FILENAME = (
    "all45_arbitration_preparation_manifest.json"
)


def resolve_protocol_provenance(
    environ: Mapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
    baked_attestation_path: Path = BAKED_BUILD_ATTESTATION_PATH,
) -> dict[str, Any]:
    environment = os.environ if environ is None else environ
    bootstrap = _preverify_bootstrap_module(
        environment,
        project_root=project_root,
        baked_attestation_path=baked_attestation_path,
    )
    return bootstrap._bootstrap_verify_provenance(
        environment,
        project_root=project_root,
        baked_attestation_path=baked_attestation_path,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("prepare-arbitration", "finalize"), required=True
    )
    parser.add_argument("--stage1-release-dir", required=True)
    parser.add_argument("--stage2-release-dir", required=True)
    parser.add_argument("--stage1-reviewer-a", required=True)
    parser.add_argument("--stage1-reviewer-a-seal", required=True)
    parser.add_argument("--stage1-reviewer-b", required=True)
    parser.add_argument("--stage1-reviewer-b-seal", required=True)
    parser.add_argument("--stage2-reviewer-a", required=True)
    parser.add_argument("--stage2-reviewer-a-seal", required=True)
    parser.add_argument("--stage2-reviewer-b", required=True)
    parser.add_argument("--stage2-reviewer-b-seal", required=True)
    parser.add_argument("--source-generations", required=True)
    parser.add_argument("--source-evaluations", required=True)
    parser.add_argument("--arbiter")
    parser.add_argument("--arbiter-seal")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--print-arbitration-packet", action="store_true")
    args = parser.parse_args(argv)
    if bool(args.arbiter) != bool(args.arbiter_seal):
        parser.error("--arbiter and --arbiter-seal must be supplied together")
    return args


def _require_new_output_dir(root: Path) -> None:
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise SemanticAuditError("finalizer output directory must be new or empty")


def _write_verified_new(
    root: Path, files: Mapping[str, bytes], *, manifest_last: str
) -> None:
    _require_new_output_dir(root)
    if manifest_last not in files:
        raise SemanticAuditError("manifest-last output is missing its marker")
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".semantic-finalizer.lock"
    try:
        with lock.open("xb") as stream:
            stream.write(b"finalization-in-progress\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise SemanticAuditError(
            "another finalizer owns the output directory"
        ) from exc
    try:
        if {path.name for path in root.iterdir()} != {lock.name}:
            raise SemanticAuditError("finalizer output directory changed before writing")
        order = [name for name in files if name != manifest_last] + [manifest_last]
        for name in order:
            path = root / name
            try:
                with path.open("xb") as stream:
                    stream.write(files[name])
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise SemanticAuditError(
                    f"output destination already exists: {name}"
                ) from exc
            if sha256_bytes(path.read_bytes()) != sha256_bytes(files[name]):
                raise SemanticAuditError(f"failed to verify written output {name}")
        if {path.name for path in root.iterdir()} != {
            lock.name,
            *files.keys(),
        }:
            raise SemanticAuditError("finalizer output directory changed during writing")
    finally:
        lock.unlink(missing_ok=True)


def _read_release(
    root: Path,
    stage: str,
    *,
    stage1_release_files: Mapping[str, bytes] | None = None,
    stage1_submission_artifacts: Sequence[tuple[bytes, bytes]] = (),
) -> tuple[
    bytes,
    dict[str, Any],
    bytes,
    list[dict[str, Any]],
    dict[str, bytes],
]:
    manifest_name = RELEASE_MANIFEST_FILENAMES[stage]
    packet_name = (
        STAGE1_PACKET_FILENAME if stage == "stage1" else STAGE2_PACKET_FILENAME
    )
    expected_names = {
        RELEASE_RESERVATION_FILENAME,
        manifest_name,
        packet_name,
    }
    if not root.is_dir() or {path.name for path in root.iterdir()} != expected_names:
        raise SemanticAuditError(
            f"{stage} release directory must contain exactly its packet and manifest"
        )
    files = {
        RELEASE_RESERVATION_FILENAME: (
            root / RELEASE_RESERVATION_FILENAME
        ).read_bytes(),
        packet_name: (root / packet_name).read_bytes(),
        manifest_name: (root / manifest_name).read_bytes(),
    }
    validated = validate_stage_release_files(
        files,
        expected_stage=stage,
        stage1_release_files=stage1_release_files,
        stage1_submission_artifacts=stage1_submission_artifacts,
    )
    return (
        validated["manifest_bytes"],
        validated["manifest"],
        validated["packet_bytes"],
        validated["records"],
        files,
    )


def _read_sealed(
    submission_path: str,
    seal_path: str,
    *,
    expected_stage: str,
    expected_packet_sha256: str,
    stage1_submission: SealedSubmission | None = None,
    stage2_records: list[dict[str, Any]] | None = None,
    expected_ids: list[str] | None = None,
    reviewer_ids: tuple[str, ...] = (),
) -> SealedSubmission:
    return validate_submission_artifact(
        Path(submission_path).read_bytes(),
        Path(seal_path).read_bytes(),
        expected_stage=expected_stage,
        expected_packet_sha256=expected_packet_sha256,
        stage1_submission=stage1_submission,
        stage2_records=stage2_records or (),
        expected_ids=expected_ids,
        reviewer_ids=reviewer_ids,
    )


def _read_exact_local_source(path: Path, expected_name: str) -> bytes:
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or len(data) != before.st_size
    ):
        raise SemanticAuditError(f"{expected_name} changed during private read")
    if sha256_bytes(data) != SOURCE_ARTIFACT_HASHES[expected_name]:
        raise SemanticAuditError(f"{expected_name} failed its preregistered SHA-256")
    return data


def _private_pack_from_validated_releases(
    stage1_release: Mapping[str, Any],
    stage2_release: Mapping[str, Any],
) -> dict[str, Any]:
    stage1_manifest = stage1_release["manifest"]
    stage2_manifest = stage2_release["manifest"]
    private_manifest = deepcopy(stage1_manifest)
    for field in (
        "release_manifest_schema_version",
        "release_stage",
        "release_complete",
        "manifest_uploaded_last",
        "stage1_gate",
        "reservation",
    ):
        private_manifest.pop(field, None)
    private_manifest["packet_files"] = {
        STAGE1_PACKET_FILENAME: deepcopy(
            stage1_manifest["packet_files"][STAGE1_PACKET_FILENAME]
        ),
        STAGE2_PACKET_FILENAME: deepcopy(
            stage2_manifest["packet_files"][STAGE2_PACKET_FILENAME]
        ),
    }
    return {
        "manifest": private_manifest,
        "packet_records": {
            STAGE1_PACKET_FILENAME: stage1_release["records"],
            STAGE2_PACKET_FILENAME: stage2_release["records"],
        },
        "packet_bytes": {
            STAGE1_PACKET_FILENAME: stage1_release["packet_bytes"],
            STAGE2_PACKET_FILENAME: stage2_release["packet_bytes"],
        },
    }


def _construct_private_records(
    generations: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
    *,
    stage1_release_files: Mapping[str, bytes],
    stage2_release_files: Mapping[str, bytes],
    stage1_submission_artifacts: Sequence[tuple[bytes, bytes]],
    stage2_submission_artifacts: Sequence[tuple[bytes, bytes]],
) -> tuple[
    list[dict[str, Any]],
    SealedSubmission,
    SealedSubmission,
    SealedSubmission,
    SealedSubmission,
]:
    if (
        len(stage1_submission_artifacts) != 2
        or len(stage2_submission_artifacts) != 2
    ):
        raise SemanticAuditError(
            "restricted private integration requires two Stage-1 and two Stage-2 seals"
        )
    stage1_release = validate_stage_release_files(
        stage1_release_files, expected_stage="stage1"
    )
    stage1_release_files = stage1_release["files"]
    stage2_release = validate_stage_release_files(
        stage2_release_files,
        expected_stage="stage2",
        stage1_release_files=stage1_release_files,
        stage1_submission_artifacts=stage1_submission_artifacts,
    )
    pack = _private_pack_from_validated_releases(stage1_release, stage2_release)
    stage1_packet_sha256 = sha256_bytes(stage1_release["packet_bytes"])
    stage2_packet_sha256 = sha256_bytes(stage2_release["packet_bytes"])
    stage2_records = stage2_release["records"]
    stage1 = [
        validate_submission_artifact(
            submission_bytes,
            seal_bytes,
            expected_stage="stage1",
            expected_packet_sha256=stage1_packet_sha256,
        )
        for submission_bytes, seal_bytes in stage1_submission_artifacts
    ]
    ensure_distinct_reviewer_identities(*stage1)
    stage2 = [
        validate_submission_artifact(
            submission_bytes,
            seal_bytes,
            expected_stage="stage2",
            expected_packet_sha256=stage2_packet_sha256,
            stage1_submission=first,
            stage2_records=stage2_records,
        )
        for (submission_bytes, seal_bytes), first in zip(
            stage2_submission_artifacts, stage1
        )
    ]
    ensure_distinct_reviewer_identities(*stage2)
    records = _build_restricted_records(
        generations,
        evaluations,
        pack,
        stage1_a=stage1[0],
        stage1_b=stage1[1],
        stage2_a=stage2[0],
        stage2_b=stage2[1],
    )
    return records, stage1[0], stage1[1], stage2[0], stage2[1]


def _verify_stage2_gate(
    stage2_manifest: Mapping[str, Any],
    stage1_a: SealedSubmission,
    stage1_b: SealedSubmission,
) -> None:
    gate = stage2_manifest.get("stage1_gate")
    reviewers = gate.get("reviewers") if isinstance(gate, Mapping) else None
    if not isinstance(reviewers, list):
        raise SemanticAuditError("Stage-2 release has no sealed Stage-1 gate")
    actual = {
        str(item.get("reviewer_id")): {
            "submission_sha256": item.get("submission_sha256"),
            "seal_sha256": item.get("seal_sha256"),
        }
        for item in reviewers
        if isinstance(item, Mapping)
    }
    expected = {
        submission.reviewer_id: {
            "submission_sha256": submission.submission_sha256,
            "seal_sha256": sha256_bytes(canonical_json_bytes(submission.seal)),
        }
        for submission in (stage1_a, stage1_b)
    }
    if actual != expected:
        raise SemanticAuditError(
            "Stage-2 release gate does not match the supplied Stage-1 seals"
        )


def _print_arbitration(records: list[dict[str, Any]]) -> None:
    print("=== BLINDED ARBITRATION PACKET BEGIN ===")
    for record in records:
        print(canonical_json_text(record))
    print("=== BLINDED ARBITRATION PACKET END ===")


def incomplete_arbitration_status(
    triggers: list[dict[str, Any]], arbitration_packet_sha256: str
) -> tuple[int, dict[str, Any]]:
    if not triggers:
        raise SemanticAuditError("incomplete arbitration requires at least one trigger")
    return 2, {
        "status": "incomplete_awaiting_arbitration",
        "trigger_count": len(triggers),
        "trigger_ids": [str(trigger["review_id"]) for trigger in triggers],
        "arbitration_packet_sha256": arbitration_packet_sha256,
        "final_metrics_emitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    if _RUNTIME_LOADED and not _RUNTIME_VERIFIED:
        raise SemanticAuditBootstrapError(
            "production main refuses an unverified test runtime"
        )
    _require_secure_interpreter(os.environ)
    _verify_stdlib_import_origins()
    bootstrap = _preverify_bootstrap_module(os.environ)
    bootstrap_provenance = bootstrap._bootstrap_verify_provenance(
        os.environ,
        project_root=PROJECT_ROOT,
        baked_attestation_path=BAKED_BUILD_ATTESTATION_PATH,
    )
    _load_runtime_after_bootstrap(bootstrap, bootstrap_provenance)
    provenance = validate_protocol_provenance_record(bootstrap_provenance)
    args = parse_args(argv)
    output_root = Path(args.output_dir)
    _require_new_output_dir(output_root)
    stage1_root = Path(args.stage1_release_dir).resolve()
    stage2_root = Path(args.stage2_release_dir).resolve()
    resolved_output = output_root.resolve()
    release_and_output_paths = [stage1_root, stage2_root, resolved_output]
    for index, left in enumerate(release_and_output_paths):
        for right in release_and_output_paths[index + 1 :]:
            if left == right or left in right.parents or right in left.parents:
                raise SemanticAuditError(
                    "Stage-1, Stage-2, and private output directories must be disjoint"
                )

    (
        stage1_manifest_bytes,
        stage1_manifest,
        stage1_packet_bytes,
        stage1_records,
        stage1_release_files,
    ) = _read_release(stage1_root, "stage1")
    stage1_hash = sha256_bytes(stage1_packet_bytes)

    submission_paths = [
        Path(value).resolve()
        for value in (
            args.stage1_reviewer_a,
            args.stage1_reviewer_b,
            args.stage2_reviewer_a,
            args.stage2_reviewer_b,
        )
    ]
    seal_paths = [
        Path(value).resolve()
        for value in (
            args.stage1_reviewer_a_seal,
            args.stage1_reviewer_b_seal,
            args.stage2_reviewer_a_seal,
            args.stage2_reviewer_b_seal,
        )
    ]
    if len(set([*submission_paths, *seal_paths])) != 8:
        raise SemanticAuditError(
            "all reviewer submission and seal files must be distinct"
        )
    stage1_submission_artifacts = (
        (submission_paths[0].read_bytes(), seal_paths[0].read_bytes()),
        (submission_paths[1].read_bytes(), seal_paths[1].read_bytes()),
    )
    stage2_submission_artifacts = (
        (submission_paths[2].read_bytes(), seal_paths[2].read_bytes()),
        (submission_paths[3].read_bytes(), seal_paths[3].read_bytes()),
    )
    (
        stage2_manifest_bytes,
        stage2_manifest,
        stage2_packet_bytes,
        stage2_records,
        stage2_release_files,
    ) = _read_release(
        stage2_root,
        "stage2",
        stage1_release_files=stage1_release_files,
        stage1_submission_artifacts=stage1_submission_artifacts,
    )
    stage2_hash = sha256_bytes(stage2_packet_bytes)
    stage1_gate = stage2_manifest.get("stage1_gate")
    if (
        not isinstance(stage1_gate, Mapping)
        or stage1_gate.get("stage1_release_manifest_sha256")
        != sha256_bytes(stage1_manifest_bytes)
    ):
        raise SemanticAuditError(
            "Stage-2 release is not bound to this Stage-1 release manifest"
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
        if stage1_manifest.get(field) != stage2_manifest.get(field):
            raise SemanticAuditError(f"staged release manifests disagree on {field}")
    if (
        stage1_manifest["protocol_commit"] != provenance["protocol_commit"]
        or stage1_manifest["protocol_bundle_sha256"]
        != provenance["protocol_bundle_sha256"]
    ):
        raise SemanticAuditError("finalizer runtime provenance differs from releases")

    stage1_a = validate_submission_artifact(
        *stage1_submission_artifacts[0],
        expected_stage="stage1",
        expected_packet_sha256=stage1_hash,
    )
    stage1_b = validate_submission_artifact(
        *stage1_submission_artifacts[1],
        expected_stage="stage1",
        expected_packet_sha256=stage1_hash,
    )
    ensure_distinct_reviewer_identities(stage1_a, stage1_b)
    _verify_stage2_gate(stage2_manifest, stage1_a, stage1_b)
    stage2_a = validate_submission_artifact(
        *stage2_submission_artifacts[0],
        expected_stage="stage2",
        expected_packet_sha256=stage2_hash,
        stage1_submission=stage1_a,
        stage2_records=stage2_records,
    )
    stage2_b = validate_submission_artifact(
        *stage2_submission_artifacts[1],
        expected_stage="stage2",
        expected_packet_sha256=stage2_hash,
        stage1_submission=stage1_b,
        stage2_records=stage2_records,
    )
    ensure_distinct_reviewer_identities(stage2_a, stage2_b)

    generation_bytes = _read_exact_local_source(
        Path(args.source_generations), "phase1_generations.jsonl"
    )
    evaluation_bytes = _read_exact_local_source(
        Path(args.source_evaluations), "phase1_eval_records.jsonl"
    )
    generations = parse_jsonl_strict(
        generation_bytes, "phase1_generations.jsonl"
    )
    evaluations = parse_jsonl_strict(
        evaluation_bytes, "phase1_eval_records.jsonl"
    )
    private_manifest = deepcopy(stage1_manifest)
    private_manifest.pop("release_manifest_schema_version", None)
    private_manifest.pop("release_stage", None)
    private_manifest.pop("release_complete", None)
    private_manifest.pop("manifest_uploaded_last", None)
    private_manifest.pop("stage1_gate", None)
    private_manifest.pop("reservation", None)
    private_manifest["packet_files"] = {
        STAGE1_PACKET_FILENAME: deepcopy(
            stage1_manifest["packet_files"][STAGE1_PACKET_FILENAME]
        ),
        STAGE2_PACKET_FILENAME: deepcopy(
            stage2_manifest["packet_files"][STAGE2_PACKET_FILENAME]
        ),
    }
    (
        unblinded,
        stage1_a,
        stage1_b,
        stage2_a,
        stage2_b,
    ) = _construct_private_records(
        generations,
        evaluations,
        stage1_release_files=stage1_release_files,
        stage2_release_files=stage2_release_files,
        stage1_submission_artifacts=stage1_submission_artifacts,
        stage2_submission_artifacts=stage2_submission_artifacts,
    )
    reviewer_a = combine_staged_submission(stage1_a, stage2_a)
    reviewer_b = combine_staged_submission(stage1_b, stage2_b)
    agreement = compute_reviewer_agreement(reviewer_a, reviewer_b)
    triggers = determine_arbitration_triggers(reviewer_a, reviewer_b, unblinded)
    arbitration_packet = build_blinded_arbitration_packet(
        stage1_records, stage2_records, reviewer_a, reviewer_b, triggers
    )
    arbitration_packet_bytes = canonical_jsonl_bytes(arbitration_packet)
    arbitration_hash = sha256_bytes(arbitration_packet_bytes)

    if args.mode == "prepare-arbitration":
        preparation_manifest = {
            "schema_version": ARBITRATION_PACKET_SCHEMA_VERSION,
            "status": "arbitration_prepared",
            "arbitration_packet_sha256": arbitration_hash,
            "trigger_count": len(triggers),
            "trigger_ids": [str(trigger["review_id"]) for trigger in triggers],
            "stage1_release_manifest_sha256": sha256_bytes(stage1_manifest_bytes),
            "stage2_release_manifest_sha256": sha256_bytes(stage2_manifest_bytes),
            "restricted_packet_released": False,
            "model_inference_performed": False,
            "mandatory_boundary": MANDATORY_BOUNDARY_TEXT,
        }
        files = {
            ARBITRATION_PACKET_FILENAME: arbitration_packet_bytes,
            ARBITRATION_PREPARATION_MANIFEST_FILENAME: canonical_json_bytes(
                preparation_manifest
            ),
        }
        _write_verified_new(
            output_root,
            files,
            manifest_last=ARBITRATION_PREPARATION_MANIFEST_FILENAME,
        )
        if args.print_arbitration_packet:
            _print_arbitration(arbitration_packet)
        print("=== SEMANTIC AUDIT FINALIZATION STATUS ===")
        print(canonical_json_text(preparation_manifest))
        return 0

    if triggers and not args.arbiter:
        exit_code, status = incomplete_arbitration_status(
            triggers, arbitration_hash
        )
        print("=== SEMANTIC AUDIT FINALIZATION STATUS ===")
        print(canonical_json_text(status))
        return exit_code
    if not triggers and args.arbiter:
        raise SemanticAuditError("arbiter submission is forbidden when no trigger exists")

    if triggers:
        arbiter_sealed = _read_sealed(
            args.arbiter,
            args.arbiter_seal,
            expected_stage="arbitration",
            expected_packet_sha256=arbitration_hash,
            stage2_records=stage2_records,
            expected_ids=[str(trigger["review_id"]) for trigger in triggers],
            reviewer_ids=(stage1_a.reviewer_id, stage1_b.reviewer_id),
        )
        arbiter = list(arbiter_sealed.rows)
    else:
        arbiter_sealed = None
        arbiter = []
    final_judgments = merge_final_judgments(
        reviewer_a,
        reviewer_b,
        arbiter,
        [str(trigger["review_id"]) for trigger in triggers],
    )
    final_records = enrich_final_adjudications(final_judgments, unblinded)
    final_manifest = {
        **private_manifest,
        "final_integration": {
            "stage1_release_manifest_sha256": sha256_bytes(stage1_manifest_bytes),
            "stage2_release_manifest_sha256": sha256_bytes(stage2_manifest_bytes),
            "stage1_submission_sha256": [
                stage1_a.submission_sha256,
                stage1_b.submission_sha256,
            ],
            "stage2_submission_sha256": [
                stage2_a.submission_sha256,
                stage2_b.submission_sha256,
            ],
            "arbitration_packet_sha256": arbitration_hash,
            "arbiter_submission_sha256": (
                None if arbiter_sealed is None else arbiter_sealed.submission_sha256
            ),
            "restricted_packet_released": False,
            "private_source_hashes_reverified": True,
            "official_history_modified": False,
            "manifest_excluded_from_self_hash": True,
        },
    }
    preliminary_files = build_final_machine_outputs(
        manifest_bytes=canonical_json_bytes(final_manifest),
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        arbiter=arbiter,
        final_records=final_records,
        agreement=agreement,
        triggers=triggers,
        unblinded_records=unblinded,
    )
    bound_output_hashes = {
        name: sha256_bytes(data)
        for name, data in sorted(preliminary_files.items())
        if name != REVIEW_MANIFEST_FILENAME
    }
    final_manifest["final_integration"]["final_output_files"] = bound_output_hashes
    final_files = build_final_machine_outputs(
        manifest_bytes=canonical_json_bytes(final_manifest),
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        arbiter=arbiter,
        final_records=final_records,
        agreement=agreement,
        triggers=triggers,
        unblinded_records=unblinded,
    )
    if {
        name: sha256_bytes(data)
        for name, data in sorted(final_files.items())
        if name != REVIEW_MANIFEST_FILENAME
    } != bound_output_hashes:
        raise SemanticAuditError("final output hashes changed while binding the manifest")
    _write_verified_new(
        output_root, final_files, manifest_last=REVIEW_MANIFEST_FILENAME
    )
    unresolved = sum(
        row.get("derived_parser_label") == "not_assessable" for row in final_records
    )
    print("=== SEMANTIC AUDIT FINALIZATION STATUS ===")
    print(
        canonical_json_text(
            {
                "status": (
                    "completed_with_unresolved"
                    if unresolved
                    else "completed_zero_unresolved"
                ),
                "record_count": EXPECTED_RECORD_COUNT,
                "arbitration_trigger_count": len(triggers),
                "unresolved_count": unresolved,
                "full_metrics_emitted": unresolved == 0,
                "model_inference_performed": False,
                "official_stored_metrics_or_classifications_modified": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("=== SEMANTIC AUDIT FINALIZATION STATUS ===")
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
