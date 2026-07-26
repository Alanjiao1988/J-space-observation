#!/usr/bin/env python3
"""Create canonical, authorization-specific parser-v2 runtime records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APPROVED_ORIGIN_URL = (
    "https://github.com/Alanjiao1988/J-space-observation.git"
)
SELF_RELATIVE_PATH = "scripts/create_parser_v2_runtime_config.py"
CORE_RELATIVE_PATH = (
    "src/jspace_observation/parser_v2_locked_evaluation.py"
)
FROZEN_VALIDATION_RELATIVE_PATH = (
    "src/jspace_observation/evaluator_validation.py"
)
DEFAULT_EVALUATION_PROFILE = "parser-v2-v1"
SUPPORTED_EVALUATION_PROFILES = ("parser-v2-v1", "parser-v3-v1")


def _load_module_from_git_bytes(
    name: str,
    source: bytes,
    *,
    git_blob_oid: str,
    relative_path: str,
    profile_id: str | None = None,
) -> ModuleType:
    source_name = f"<git-blob:{git_blob_oid}:{relative_path}>"
    module = ModuleType(name)
    module.__file__ = source_name
    module.__package__ = ""
    if profile_id is not None:
        # The profile has to exist in the module namespace before the first
        # statement executes: the core resolves and locks it at import time and
        # refuses to be re-pointed afterwards.
        module.__dict__["_PRESEEDED_PARSER_PROFILE_ID"] = profile_id
    sys.modules[name] = module
    try:
        exec(compile(source, source_name, "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(name, None)
        raise RuntimeError(
            f"cannot load authenticated committed helper: {relative_path}"
        ) from None
    return module


def _git_text(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(PROJECT_ROOT), *arguments],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("required committed Git binding is unavailable")
    try:
        value = completed.stdout.decode("ascii").replace("\r", "").strip()
    except UnicodeDecodeError:
        raise RuntimeError("Git returned a non-ASCII scalar") from None
    if not value or "\n" in value:
        raise RuntimeError("Git returned a non-scalar binding")
    return value


def _git_blob_binding(commit: str, relative_path: str) -> dict[str, Any]:
    oid, data = _git_blob_bytes(commit, relative_path)
    return {
        "git_blob_oid": oid,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }


def _git_blob_bytes(commit: str, relative_path: str) -> tuple[str, bytes]:
    oid = _git_text("rev-parse", f"{commit}:{relative_path}")
    if _git_text("cat-file", "-t", oid) != "blob":
        raise RuntimeError("runtime source binding is not a Git blob")
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(PROJECT_ROOT),
            "cat-file",
            "blob",
            oid,
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("cannot read committed runtime source bytes")
    return oid, completed.stdout


def _load_core(commit: str, profile_id: str = DEFAULT_EVALUATION_PROFILE) -> ModuleType:
    core_oid, core_source = _git_blob_bytes(commit, CORE_RELATIVE_PATH)
    validation_oid, validation_source = _git_blob_bytes(
        commit, FROZEN_VALIDATION_RELATIVE_PATH
    )
    core_module = _load_module_from_git_bytes(
        f"_jspace_parser_v2_runtime_core_{core_oid}_{profile_id}",
        core_source,
        git_blob_oid=core_oid,
        relative_path=CORE_RELATIVE_PATH,
        profile_id=profile_id,
    )
    if core_module.ACTIVE_PARSER_PROFILE_ID != profile_id:
        raise RuntimeError("locked-evaluation core ignored the requested profile")
    if "_PRESEEDED_PARSER_PROFILE_ID" in core_module.__dict__:
        raise RuntimeError("locked-evaluation core leaked its profile seed")
    normalized_validation = (
        validation_source.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    )
    if (
        hashlib.sha256(normalized_validation).hexdigest()
        != core_module._FROZEN_EVALUATOR_VALIDATION_SHA256
    ):
        raise RuntimeError("committed frozen validator digest mismatch")
    validation_module = _load_module_from_git_bytes(
        f"_jspace_parser_v2_runtime_validation_{validation_oid}",
        validation_source,
        git_blob_oid=validation_oid,
        relative_path=FROZEN_VALIDATION_RELATIVE_PATH,
    )
    expected_state_model = (
        tuple(validation_module.CONSTRUCTION_STATES),
        tuple(validation_module.EVALUATION_STATES),
        {
            state: frozenset(bindings)
            for state, bindings in (
                validation_module.STATE_AUTHORIZED_ARTIFACT_BINDINGS.items()
            )
        },
    )
    actual_state_model = (
        core_module.CONSTRUCTION_STATE_SEQUENCE,
        core_module.EVALUATION_STATE_SEQUENCE,
        core_module.STATE_AUTHORIZED_ARTIFACT_BINDINGS,
    )
    if expected_state_model != actual_state_model:
        raise RuntimeError("committed frozen state-model binding mismatch")
    core_module._load_frozen_validation = lambda: validation_module
    return core_module


def _fetch_approved_origin() -> None:
    if _git_text("remote", "get-url", "origin") != APPROVED_ORIGIN_URL:
        raise RuntimeError("runtime records require the approved Git origin")
    environment = dict(os.environ)
    environment.update(
        {
            "GCM_INTERACTIVE": "Never",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(PROJECT_ROOT),
            "fetch",
            "--quiet",
            "--no-tags",
            APPROVED_ORIGIN_URL,
            "+refs/heads/main:refs/remotes/origin/main",
        ],
        check=False,
        capture_output=True,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError("approved origin/main fetch failed")


def _stable_read(path: Path) -> bytes:
    try:
        before_path = path.lstat()
        descriptor = os.open(
            path, os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
    except OSError:
        raise RuntimeError("immutable image binding is unavailable") from None
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_ISLNK(before_path.st_mode)
            or (
                before_path.st_dev,
                before_path.st_ino,
                before_path.st_size,
                before_path.st_mtime_ns,
            )
            != (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            )
        ):
            raise RuntimeError("immutable image binding is not a stable regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if before_identity != after_identity:
        raise RuntimeError("immutable image binding changed while being read")
    data = b"".join(chunks)
    if len(data) != before.st_size:
        raise RuntimeError("immutable image binding read is incomplete")
    return data


def _write_once_or_verify(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"existing immutable record differs: {path.name}")
        return
    with path.open("xb") as stream:
        stream.write(data)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--parent-prefix", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--subscription-id", required=True)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--container-apps-environment-name", required=True)
    parser.add_argument("--container-apps-environment-resource-id", required=True)
    parser.add_argument("--container-apps-job-name", required=True)
    parser.add_argument("--container-apps-job-resource-id", required=True)
    parser.add_argument("--managed-identity-name", required=True)
    parser.add_argument("--managed-identity-resource-id", required=True)
    parser.add_argument("--managed-identity-client-id", required=True)
    parser.add_argument("--managed-identity-principal-id", required=True)
    parser.add_argument("--storage-account-name", required=True)
    parser.add_argument("--storage-account-resource-id", required=True)
    parser.add_argument("--blob-endpoint", required=True)
    parser.add_argument("--blob-container", required=True)
    parser.add_argument("--vnet-resource-id", required=True)
    parser.add_argument("--infrastructure-subnet-resource-id", required=True)
    parser.add_argument("--private-endpoint-subnet-resource-id", required=True)
    parser.add_argument("--private-endpoint-resource-id", required=True)
    parser.add_argument("--private-endpoint-name", required=True)
    parser.add_argument("--private-endpoint-resource-group", required=True)
    parser.add_argument("--private-link-connection-name", required=True)
    parser.add_argument(
        "--storage-private-endpoint-connection-name", required=True
    )
    parser.add_argument(
        "--storage-private-endpoint-connection-resource-id", required=True
    )
    parser.add_argument("--private-link-group-id", required=True)
    parser.add_argument("--private-link-subresource", required=True)
    parser.add_argument(
        "--private-endpoint-nic-private-ip", action="append", required=True
    )
    parser.add_argument("--private-dns-zone-name", required=True)
    parser.add_argument("--private-dns-zone-resource-id", required=True)
    parser.add_argument("--private-dns-zone-group-name", required=True)
    parser.add_argument("--private-dns-vnet-link-name", required=True)
    parser.add_argument(
        "--coordination-private-dns-zone-name", required=True
    )
    parser.add_argument(
        "--coordination-private-dns-zone-resource-id", required=True
    )
    parser.add_argument(
        "--coordination-private-dns-zone-location", required=True
    )
    parser.add_argument(
        "--coordination-private-dns-zone-internal-id", required=True
    )
    parser.add_argument(
        "--coordination-private-dns-api-version", required=True
    )
    parser.add_argument("--coordination-record-ttl", type=int, required=True)
    parser.add_argument(
        "--coordination-expected-vnet-link-count", type=int, required=True
    )
    parser.add_argument("--coordination-lock-name", required=True)
    parser.add_argument("--coordination-lock-resource-id", required=True)
    parser.add_argument("--coordination-lock-level", required=True)
    parser.add_argument(
        "--coordination-management-lock-api-version", required=True
    )
    parser.add_argument("--acr-name", required=True)
    parser.add_argument("--acr-resource-id", required=True)
    parser.add_argument("--acr-login-server", required=True)
    parser.add_argument("--acr-repository", required=True)
    parser.add_argument("--image-binding", type=Path, required=True)
    parser.add_argument("--image-binding-sha256", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--base-image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--implementation-manifest-output", type=Path, required=True
    )
    parser.add_argument(
        "--evaluation-profile",
        default=DEFAULT_EVALUATION_PROFILE,
        choices=SUPPORTED_EVALUATION_PROFILES,
        help=(
            "Parser evaluation profile fixed in the core at import time, "
            "before any input is read."
        ),
    )
    return parser


def _destination(
    args: argparse.Namespace,
    image_binding: dict[str, Any],
    core_module: ModuleType,
) -> dict[str, Any]:
    image_digest = image_binding["image_digest"]
    base_image = image_binding["base_image"]
    if args.acr_repository != core_module.EVAL_IMAGE_REPOSITORY:
        raise core_module.LockedEvaluationError(
            "acr repository does not match the active evaluation profile"
        )
    image_ref = f"{args.acr_login_server}/{args.acr_repository}@{image_digest}"
    return {
        "subscription_id": args.subscription_id,
        "resource_group": args.resource_group,
        "location": args.location,
        "container_apps": {
            "environment_name": args.container_apps_environment_name,
            "environment_resource_id": (
                args.container_apps_environment_resource_id
            ),
            "job_name": args.container_apps_job_name,
            "job_resource_id": args.container_apps_job_resource_id,
            "workload_profile": "Consumption",
        },
        "managed_identity": {
            "name": args.managed_identity_name,
            "resource_id": args.managed_identity_resource_id,
            "client_id": args.managed_identity_client_id,
            "principal_id": args.managed_identity_principal_id,
        },
        "storage": {
            "account_name": args.storage_account_name,
            "resource_id": args.storage_account_resource_id,
            "blob_endpoint": args.blob_endpoint,
            "container": args.blob_container,
            "public_network_access": "Disabled",
            "shared_key_access": False,
            "allow_blob_public_access": False,
            "container_public_access": None,
        },
        "network": {
            "vnet_resource_id": args.vnet_resource_id,
            "infrastructure_subnet_resource_id": (
                args.infrastructure_subnet_resource_id
            ),
            "private_endpoint_subnet_resource_id": (
                args.private_endpoint_subnet_resource_id
            ),
            "private_endpoint_resource_id": args.private_endpoint_resource_id,
            "private_endpoint_name": args.private_endpoint_name,
            "private_endpoint_resource_group": (
                args.private_endpoint_resource_group
            ),
            "private_link_connection_name": args.private_link_connection_name,
            "storage_private_endpoint_connection_name": (
                args.storage_private_endpoint_connection_name
            ),
            "storage_private_endpoint_connection_resource_id": (
                args.storage_private_endpoint_connection_resource_id
            ),
            "private_link_group_id": args.private_link_group_id,
            "private_link_subresource": args.private_link_subresource,
            "private_endpoint_nic_private_ips": sorted(
                args.private_endpoint_nic_private_ip
            ),
            "private_dns_zone_name": args.private_dns_zone_name,
            "private_dns_zone_resource_id": args.private_dns_zone_resource_id,
            "private_dns_zone_group_name": args.private_dns_zone_group_name,
            "private_dns_vnet_link_name": args.private_dns_vnet_link_name,
        },
        "coordination": {
            "schema_version": (
                core_module.COORDINATION_BINDING_SCHEMA_VERSION
            ),
            "zone_name": args.coordination_private_dns_zone_name,
            "zone_resource_id": (
                args.coordination_private_dns_zone_resource_id
            ),
            "zone_location": args.coordination_private_dns_zone_location,
            "zone_internal_id": (
                args.coordination_private_dns_zone_internal_id
            ),
            "private_dns_api_version": (
                args.coordination_private_dns_api_version
            ),
            "record_ttl": args.coordination_record_ttl,
            "expected_vnet_link_count": (
                args.coordination_expected_vnet_link_count
            ),
            "lock_name": args.coordination_lock_name,
            "lock_resource_id": args.coordination_lock_resource_id,
            "lock_level": args.coordination_lock_level,
            "management_lock_api_version": (
                args.coordination_management_lock_api_version
            ),
        },
        "registry": {
            "name": args.acr_name,
            "resource_id": args.acr_resource_id,
            "login_server": args.acr_login_server,
            "repository": args.acr_repository,
        },
        "image": {
            "digest": image_digest,
            "reference": image_ref,
            "base_image": base_image,
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _fetch_approved_origin()
    if _git_text("rev-parse", "HEAD") != args.source_commit:
        raise RuntimeError("source commit must equal local HEAD")
    if _git_text("rev-parse", "refs/remotes/origin/main") != args.source_commit:
        raise RuntimeError("source commit must equal origin/main")
    status = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(PROJECT_ROOT),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        check=False,
        capture_output=True,
    )
    if status.returncode != 0 or status.stdout:
        raise RuntimeError("runtime records require a clean committed worktree")

    _, committed_self = _git_blob_bytes(
        args.source_commit, SELF_RELATIVE_PATH
    )
    if _stable_read(Path(__file__).resolve()) != committed_self:
        raise RuntimeError(
            "executing runtime generator differs from its committed Git blob"
        )
    core = _load_core(args.source_commit, args.evaluation_profile)
    image_binding_bytes = _stable_read(args.image_binding)
    image_binding = core.validate_image_binding(
        image_binding_bytes,
        expected_sha256=args.image_binding_sha256,
        expected_source_commit=args.source_commit,
        expected_acr_resource_id=args.acr_resource_id,
        expected_login_server=args.acr_login_server,
        expected_repository=args.acr_repository,
    )
    if (
        image_binding["image_digest"] != args.image_digest
        or image_binding["base_image"] != args.base_image
        or image_binding["build_provenance"]["acr"]["login_server"]
        != args.acr_login_server.casefold()
        or image_binding["build_provenance"]["acr"]["repository"]
        != args.acr_repository
        or image_binding["build_provenance"]["acr"]["resource_id"]
        != args.acr_resource_id.casefold()
        or image_binding["build_provenance"]["acr"]["login_server"]
        != f"{args.acr_name.casefold()}.azurecr.io"
    ):
        raise RuntimeError(
            "caller image/ACR values differ from the immutable image binding"
        )
    committed_image_sources = {
        path: _git_blob_binding(args.source_commit, path)
        for path in core.IMAGE_BINDING_SOURCE_PATHS
    }
    if image_binding["files"] != committed_image_sources:
        raise RuntimeError(
            "image binding source blobs differ from the exact source commit"
        )
    source_bindings = {
        path: {
            "git_blob_oid": committed_image_sources[path]["git_blob_oid"],
            "sha256": committed_image_sources[path]["sha256"],
        }
        for path in core.RUNTIME_SOURCE_BINDING_PATHS
    }
    launcher = source_bindings[core.EVAL_RUNTIME_LAUNCHER_PATH]
    record = core.build_runtime_configuration(
        source_commit=args.source_commit,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        launcher_sha256=launcher["sha256"],
        launcher_git_blob_oid=launcher["git_blob_oid"],
        source_bindings=source_bindings,
        azure_destination=_destination(args, image_binding, core),
        image_binding=image_binding,
        image_binding_sha256=args.image_binding_sha256,
    )
    data = core.canonical_json_bytes(record)
    implementation = {
        "schema_version": core.IMPLEMENTATION_MANIFEST_SCHEMA_VERSION,
        "implementation_commit": args.source_commit,
        "image_digest": record["azure_destination"]["image"]["digest"],
        "config_sha256": core.sha256_bytes(data),
    }
    implementation_data = core.canonical_json_bytes(implementation)
    core.validate_implementation_manifest(implementation_data)
    _write_once_or_verify(args.output, data)
    _write_once_or_verify(
        args.implementation_manifest_output, implementation_data
    )
    print(
        json.dumps(
            {
                "config_sha256": core.sha256_bytes(data),
                "implementation_manifest_sha256": core.sha256_bytes(
                    implementation_data
                ),
                "image_binding_sha256": args.image_binding_sha256,
                "azure_destination_sha256": record[
                    "azure_destination_sha256"
                ],
                "output": str(args.output),
                "implementation_manifest_output": str(
                    args.implementation_manifest_output
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
