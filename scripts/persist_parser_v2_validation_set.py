#!/usr/bin/env python3
"""Persist exact Phase 1.2A artifacts with managed identity and full verification."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CONTAINER_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?\Z")
_ACCOUNT_HOST_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9-]{1,22}[a-z0-9]\.blob\.core\.windows\.net\Z"
)
_PROHIBITED_CREDENTIAL_ENV = (
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_KEY",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_SAS_TOKEN",
    "AZURE_SAS_TOKEN",
)


def _load_validation_module() -> ModuleType:
    name = "_jspace_evaluator_validation_persist"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = PROJECT_ROOT / "src" / "jspace_observation" / "evaluator_validation.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load evaluator validation tooling")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validation = _load_validation_module()
ValidationSetError = validation.ValidationSetError


def validate_managed_identity_configuration(
    account_url: str, environment: Mapping[str, str]
) -> tuple[str, str]:
    """Reject keys, SAS, HTTP, userinfo, and non-Blob/public URL paths."""
    if not isinstance(account_url, str) or not account_url:
        raise ValidationSetError("account URL must be a non-empty string")
    normalized_environment = {
        key.upper(): value
        for key, value in environment.items()
        if isinstance(key, str)
    }
    for name in _PROHIBITED_CREDENTIAL_ENV:
        if normalized_environment.get(name):
            raise ValidationSetError(f"prohibited key/SAS credential is set: {name}")
    client_id = normalized_environment.get("AZURE_CLIENT_ID")
    if not isinstance(client_id, str) or not client_id:
        raise ValidationSetError("AZURE_CLIENT_ID is required")
    parsed = urlsplit(account_url)
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port not in {None, 443}
    ):
        raise ValidationSetError(
            "account URL must be a credential-free HTTPS Blob service root"
        )
    hostname = parsed.hostname or ""
    if not _ACCOUNT_HOST_PATTERN.fullmatch(hostname):
        raise ValidationSetError(
            "account URL must use the registered Azure Blob service endpoint"
        )
    return account_url.rstrip("/"), client_id


def create_blob_service(
    account_url: str, environment: Mapping[str, str] | None = None
) -> Any:
    """Lazily import Azure SDK modules and use only ManagedIdentityCredential."""
    active_environment = os.environ if environment is None else environment
    normalized_url, client_id = validate_managed_identity_configuration(
        account_url, active_environment
    )
    identity_module = importlib.import_module("azure.identity")
    blob_module = importlib.import_module("azure.storage.blob")
    credential = identity_module.ManagedIdentityCredential(client_id=client_id)
    return blob_module.BlobServiceClient(
        account_url=normalized_url, credential=credential
    )


def _validate_container(container: str) -> str:
    if (
        not isinstance(container, str)
        or not _CONTAINER_PATTERN.fullmatch(container)
        or "--" in container
    ):
        raise ValidationSetError("container name is invalid")
    return container


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_external_local_root(local_root: str | Path) -> Path:
    """Reject repository, Git-worktree, Docker-context, and symlink roots."""
    raw = Path(local_root)
    lexical = raw.absolute()
    resolved = raw.resolve(strict=False)
    if _path_is_within(
        lexical, PROJECT_ROOT.resolve()
    ) or _path_is_within(resolved, PROJECT_ROOT.resolve()):
        raise ValidationSetError(
            "local artifact root must be outside the repository, including ignored paths"
        )
    for component in (lexical, *lexical.parents):
        if component.exists() and component.is_symlink():
            raise ValidationSetError(
                "local artifact root may not traverse a symbolic link"
            )
    existing = resolved
    while not existing.exists():
        if existing.parent == existing:
            raise ValidationSetError("local artifact root has no existing ancestor")
        existing = existing.parent
    if existing.is_symlink():
        raise ValidationSetError("local artifact root may not be a symbolic link")
    probe = existing if existing.is_dir() else existing.parent
    completed = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        worktree = Path(completed.stdout.strip()).resolve()
        if _path_is_within(resolved, worktree):
            raise ValidationSetError(
                "local artifact root must be outside every Git worktree"
            )
    for ancestor in (probe, *probe.parents):
        if (ancestor / "Dockerfile").is_file():
            raise ValidationSetError(
                "local artifact root must be outside every Docker context"
            )
    return resolved


def validate_external_input_path(
    value: str | Path, local_root: str | Path, *, name: str
) -> Path:
    """Require one regular private input outside the release root and repository."""
    resolved = validate_external_local_root(value)
    release_root = Path(local_root).resolve(strict=False)
    if (
        not resolved.is_file()
        or resolved.is_symlink()
        or _path_is_within(resolved, release_root)
    ):
        raise ValidationSetError(
            f"{name} must be a regular external file outside the local release root"
        )
    return resolved


def _blob_name(item: Any) -> str:
    if isinstance(item, Mapping):
        value = item.get("name")
    else:
        value = getattr(item, "name", None)
    if not isinstance(value, str):
        raise ValidationSetError("Blob listing returned an invalid member")
    return value


def _list_exact(service: Any, container: str, prefix: str) -> set[str]:
    try:
        client = service.get_container_client(container)
        return {
            _blob_name(item)
            for item in client.list_blobs(name_starts_with=f"{prefix}/")
        }
    except ValidationSetError:
        raise
    except Exception as exc:
        raise ValidationSetError("cannot verify exact remote membership") from exc


def _property_value(properties: Any, *names: str) -> Any:
    for name in names:
        if isinstance(properties, Mapping) and name in properties:
            return properties[name]
        value = getattr(properties, name, None)
        if value is not None:
            return value
    return None


def _capture_properties(blob: Any, blob_name: str, expected_size: int) -> str:
    try:
        properties = blob.get_blob_properties()
    except Exception as exc:
        raise ValidationSetError(
            f"cannot read uploaded Blob properties: {blob_name}"
        ) from exc
    size = _property_value(properties, "size", "blob_size")
    etag = _property_value(properties, "etag")
    if type(size) is not int or size != expected_size:
        raise ValidationSetError(f"uploaded Blob size mismatch: {blob_name}")
    if not isinstance(etag, str) or not etag:
        raise ValidationSetError(f"uploaded Blob ETag is unavailable: {blob_name}")
    return etag


def _upload_one(
    service: Any,
    container: str,
    blob_name: str,
    data: bytes,
) -> str:
    blob = service.get_blob_client(container=container, blob=blob_name)
    try:
        blob.upload_blob(data, overwrite=False)
    except Exception as exc:
        raise ValidationSetError(
            f"overwrite-false upload failed: {blob_name}"
        ) from exc
    return _capture_properties(blob, blob_name, len(data))


def _verify_one(
    service: Any,
    container: str,
    blob_name: str,
    expected: bytes,
    expected_etag: str,
) -> None:
    blob = service.get_blob_client(container=container, blob=blob_name)
    try:
        downloaded = blob.download_blob().readall()
    except Exception as exc:
        raise ValidationSetError(
            f"cannot re-download uploaded Blob: {blob_name}"
        ) from exc
    if not isinstance(downloaded, bytes):
        downloaded = bytes(downloaded)
    if len(downloaded) != len(expected):
        raise ValidationSetError(f"re-downloaded Blob size mismatch: {blob_name}")
    if validation.sha256_bytes(downloaded) != validation.sha256_bytes(expected):
        raise ValidationSetError(f"re-downloaded Blob SHA-256 mismatch: {blob_name}")
    actual_etag = _capture_properties(blob, blob_name, len(expected))
    if actual_etag != expected_etag:
        raise ValidationSetError(f"uploaded Blob ETag changed: {blob_name}")


def persist_authorization_lock_once(
    service: Any,
    container: str,
    record: Mapping[str, Any],
    implementation_manifest_bytes: bytes,
) -> dict[str, str]:
    """Create and verify the fixed holdout authorization lock exactly once."""
    container = _validate_container(container)
    manifest = validation.validate_implementation_manifest(
        implementation_manifest_bytes
    )
    checked_lock = validation.validate_authorization_lock(record)
    if (
        checked_lock["implementation_manifest_sha256"]
        != validation.sha256_bytes(implementation_manifest_bytes)
        or checked_lock["implementation_commit"]
        != manifest["implementation_commit"]
        or checked_lock["image_digest"] != manifest["image_digest"]
        or checked_lock["config_sha256"] != manifest["config_sha256"]
    ):
        raise ValidationSetError(
            "authorization lock differs from the implementation manifest"
        )
    data = validation.canonical_json_bytes(dict(record))
    blob_name = validation.authorization_lock_blob_name(record)
    etag = _upload_one(service, container, blob_name, data)
    _verify_one(service, container, blob_name, data, etag)
    return {
        "blob_name": blob_name,
        "sha256": validation.sha256_bytes(data),
        "etag": etag,
    }


def persist_registered_artifacts(
    service: Any,
    container: str,
    parent_prefix: str,
    files: Mapping[str, bytes],
    *,
    source_prefixes: Sequence[str],
    production_artifact_bytes: Mapping[str, bytes],
    historical_fingerprint_jsonl: bytes,
    historical_fingerprint_summary: bytes,
) -> dict[str, Any]:
    """Upload reservation-first/manifest-last and verify exact remote bytes."""
    container = _validate_container(container)
    parent = validation.validate_registered_parent_prefix(parent_prefix)
    validation.validate_prefix_isolation(source_prefixes, [parent])
    expected_relative = [
        f"{leaf}/{filename}"
        for leaf, names in validation.REGISTERED_LEAF_MEMBERS.items()
        for filename in names
    ]
    if set(files) != set(expected_relative):
        raise ValidationSetError(
            "local file mapping must have exact registered membership"
        )
    for name, data in files.items():
        if not isinstance(data, bytes):
            raise ValidationSetError(f"local artifact is not bytes: {name}")
    production_binding = validation.validate_release_against_eligible_production(
        files, production_artifact_bytes
    )
    historical_fingerprints = (
        validation.validate_historical_fingerprint_bundle(
            historical_fingerprint_jsonl,
            historical_fingerprint_summary,
        )
    )
    semantic = validation.validate_release_artifacts(
        files,
        parent,
        project_root=PROJECT_ROOT,
        historical_fingerprints=historical_fingerprints,
        registered_draft_labels=production_binding["registered_draft_labels"],
        source_prefixes=source_prefixes,
    )
    if _list_exact(service, container, parent):
        raise ValidationSetError("output parent prefix must be entirely new")

    uploaded: set[str] = set()
    etags: dict[str, str] = {}
    for leaf, names in validation.REGISTERED_LEAF_MEMBERS.items():
        leaf_prefix = f"{parent}/{leaf}"
        manifest_name = names[-1]
        reservation_name = names[0]
        if not reservation_name.startswith("."):
            raise AssertionError("registered leaf must begin with a reservation")
        if "manifest" not in manifest_name:
            raise AssertionError("registered leaf must end with a manifest")

        for filename in names[:-1]:
            relative = f"{leaf}/{filename}"
            blob_name = f"{parent}/{relative}"
            etags[blob_name] = _upload_one(
                service, container, blob_name, files[relative]
            )
            uploaded.add(blob_name)
        actual_before_manifest = _list_exact(service, container, leaf_prefix)
        expected_before_manifest = {
            f"{parent}/{leaf}/{filename}" for filename in names[:-1]
        }
        if actual_before_manifest != expected_before_manifest:
            raise ValidationSetError(
                f"exact leaf membership failed before manifest: {leaf}"
            )
        if _list_exact(service, container, parent) != uploaded:
            raise ValidationSetError(
                "exact parent membership failed before leaf manifest"
            )

        relative_manifest = f"{leaf}/{manifest_name}"
        manifest_blob = f"{parent}/{relative_manifest}"
        etags[manifest_blob] = _upload_one(
            service, container, manifest_blob, files[relative_manifest]
        )
        uploaded.add(manifest_blob)
        expected_leaf = {
            f"{parent}/{leaf}/{filename}" for filename in names
        }
        if _list_exact(service, container, leaf_prefix) != expected_leaf:
            raise ValidationSetError(
                f"exact leaf membership failed after manifest: {leaf}"
            )
        if _list_exact(service, container, parent) != uploaded:
            raise ValidationSetError(
                "exact parent membership failed after leaf manifest"
            )

    expected_parent = validation.expected_parent_membership(parent)
    if uploaded != set(expected_parent):
        raise ValidationSetError("uploaded membership differs from exact plan")
    if _list_exact(service, container, parent) != set(expected_parent):
        raise ValidationSetError("final parent membership verification failed")
    for relative in expected_relative:
        blob_name = f"{parent}/{relative}"
        _verify_one(
            service,
            container,
            blob_name,
            files[relative],
            etags[blob_name],
        )
    return {
        "artifact_count": len(expected_relative),
        "verified_count": len(expected_relative),
        "manifest_uploaded_last": True,
        "overwrite": False,
        "parent_prefix": parent,
        "production_binding": {
            "selection_plan_sha256": production_binding[
                "selection_plan_sha256"
            ],
            "development_count": production_binding["development_count"],
            "locked_count": production_binding["locked_count"],
        },
        "semantic_validation": semantic,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist exact parser-v2 validation artifacts"
    )
    parser.add_argument("--account-url", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--parent-prefix", required=True)
    parser.add_argument("--source-prefix", action="append", required=True)
    parser.add_argument("--local-root", required=True)
    parser.add_argument("--historical-fingerprints", required=True)
    parser.add_argument("--historical-fingerprint-summary", required=True)
    parser.add_argument("--curator-a-pool", required=True)
    parser.add_argument("--curator-a-seal", required=True)
    parser.add_argument("--curator-b-pool", required=True)
    parser.add_argument("--curator-b-seal", required=True)
    parser.add_argument("--selection-plan", required=True)
    parser.add_argument("--curator-c-summary", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        validate_managed_identity_configuration(args.account_url, os.environ)
        local_root = validate_external_local_root(args.local_root)
        fingerprint_path = validate_external_input_path(
            args.historical_fingerprints,
            local_root,
            name="historical fingerprints",
        )
        fingerprint_summary_path = validate_external_input_path(
            args.historical_fingerprint_summary,
            local_root,
            name="historical fingerprint summary",
        )
        production_paths = {
            "curator_a_candidate_jsonl": validate_external_input_path(
                args.curator_a_pool,
                local_root,
                name="curator A candidate pool",
            ),
            "curator_a_pool_seal": validate_external_input_path(
                args.curator_a_seal,
                local_root,
                name="curator A pool seal",
            ),
            "curator_b_candidate_jsonl": validate_external_input_path(
                args.curator_b_pool,
                local_root,
                name="curator B candidate pool",
            ),
            "curator_b_pool_seal": validate_external_input_path(
                args.curator_b_seal,
                local_root,
                name="curator B pool seal",
            ),
            "curator_c_selection": validate_external_input_path(
                args.selection_plan,
                local_root,
                name="Curator-C selection",
            ),
            "curator_c_summary": validate_external_input_path(
                args.curator_c_summary,
                local_root,
                name="Curator-C summary",
            ),
        }
        external_inputs = [
            fingerprint_path,
            fingerprint_summary_path,
            *production_paths.values(),
        ]
        if len(set(external_inputs)) != len(external_inputs):
            raise ValidationSetError(
                "all private persistence inputs must be distinct files"
            )
        fingerprint_bytes = fingerprint_path.read_bytes()
        fingerprint_summary_bytes = fingerprint_summary_path.read_bytes()
        production_artifact_bytes = {
            name: path.read_bytes() for name, path in production_paths.items()
        }
        validation.validate_historical_fingerprint_bundle(
            fingerprint_bytes, fingerprint_summary_bytes
        )
        files = validation.validate_registered_local_membership(local_root)
        validation.validate_prefix_isolation(
            args.source_prefix, [args.parent_prefix]
        )
        service = create_blob_service(args.account_url)
        result = persist_registered_artifacts(
            service,
            args.container,
            args.parent_prefix,
            files,
            source_prefixes=args.source_prefix,
            production_artifact_bytes=production_artifact_bytes,
            historical_fingerprint_jsonl=fingerprint_bytes,
            historical_fingerprint_summary=fingerprint_summary_bytes,
        )
    except Exception:
        print(
            "validation-set persistence failed; no artifact data emitted",
            file=sys.stderr,
        )
        return 2
    print(
        f"persisted and verified artifacts={result['artifact_count']} "
        f"manifest_last=true overwrite=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
