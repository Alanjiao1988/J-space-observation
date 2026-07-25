"""Managed-identity Blob transport for the Phase 1.0C headroom calibration pack.

The generic ``blob_export.upload_directory_to_blob`` helper walks the directory
in filesystem order and overwrites, which cannot satisfy the protocol rule that
``artifact_manifest.json`` is written last.  This transport mirrors the audited
``phase05_jlens_feasibility.BlobTransport`` behaviour instead:

* ``DefaultAzureCredential`` with the job's user-assigned managed identity, over
  the account's private endpoint; no account key, connection string or SAS is
  ever read, and their presence in the environment is a hard failure;
* deterministic upload order with the artifact manifest strictly last;
* ``overwrite=False`` so a run can never silently rewrite an earlier pack.

Nothing in this module interprets model output.  It moves bytes only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence


DEFAULT_BLOB_PREFIX = "phase1-headroom-calibration"
MANIFEST_NAME = "artifact_manifest.json"
CREDENTIAL_MODE = "default_credential_managed_identity_only"

FORBIDDEN_ENVIRONMENT = (
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_KEY",
    "AZURE_STORAGE_SAS_TOKEN",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "JSPACE_BLOB_ACCOUNT_KEY",
    "JSPACE_BLOB_SAS",
    "JSPACE_BLOB_SAS_TOKEN",
)


class BlobTransportError(RuntimeError):
    """Raised when the pack cannot be persisted under the required rules."""


def assert_managed_identity_only(environment: Any = None) -> None:
    """Fail closed if any shared-secret Blob credential is present."""

    env = os.environ if environment is None else environment
    present = sorted(name for name in FORBIDDEN_ENVIRONMENT if env.get(name))
    if present:
        raise BlobTransportError(
            "managed identity is the only permitted Blob credential; remove: "
            + ", ".join(present)
        )


def destination_prefix(run_id: str, prefix: str | None = None) -> str:
    """``phase1-headroom-calibration/<run id>`` unless a prefix is supplied."""

    run = str(run_id).strip().strip("/").strip()
    if not run:
        raise BlobTransportError("run id is required to build the blob prefix")
    base = (prefix if prefix is not None else DEFAULT_BLOB_PREFIX).strip("/")
    return f"{base}/{run}" if base else run


def ordered_pack_files(pack_dir: Path) -> list[Path]:
    """Every pack file in a stable order with the artifact manifest last."""

    root = Path(pack_dir)
    if not root.is_dir():
        raise BlobTransportError(f"pack directory not found: {root}")
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
        and ".tmp." not in path.name
    ]
    if not files:
        raise BlobTransportError(f"pack directory is empty: {root}")
    return sorted(
        files,
        key=lambda path: (
            path.relative_to(root).as_posix() == MANIFEST_NAME,
            path.relative_to(root).as_posix(),
        ),
    )


def _credential(client_id: str | None) -> Any:
    from azure.identity import DefaultAzureCredential  # noqa: PLC0415 - lazy

    return DefaultAzureCredential(managed_identity_client_id=client_id)


def _container_client(account: str, container: str, client_id: str | None) -> Any:
    from azure.storage.blob import BlobServiceClient  # noqa: PLC0415 - lazy

    service = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=_credential(client_id),
    )
    return service.get_container_client(container)


def upload_pack(
    pack_dir: Path | str,
    run_id: str,
    *,
    account: str | None = None,
    container: str | None = None,
    prefix: str | None = None,
    client_id: str | None = None,
    require: bool = True,
    client: Any = None,
) -> dict[str, Any]:
    """Upload one artifact pack, writing ``artifact_manifest.json`` last."""

    assert_managed_identity_only()
    account = account if account is not None else os.getenv("JSPACE_BLOB_ACCOUNT", "")
    container = (
        container if container is not None else os.getenv("JSPACE_BLOB_CONTAINER", "")
    )
    prefix = prefix if prefix is not None else os.getenv("JSPACE_BLOB_PREFIX")
    client_id = (
        client_id if client_id is not None else os.getenv("AZURE_CLIENT_ID") or None
    )
    account = (account or "").strip()
    container = (container or "").strip()

    if not account or not container:
        message = (
            "Blob upload skipped: JSPACE_BLOB_ACCOUNT or JSPACE_BLOB_CONTAINER is unset"
        )
        if require:
            raise BlobTransportError(message)
        return {
            "credential_mode": CREDENTIAL_MODE,
            "manifest_uploaded_last": False,
            "prefix": None,
            "status": "not_configured",
            "uploaded": [],
        }

    destination = destination_prefix(run_id, prefix)
    files = ordered_pack_files(Path(pack_dir))
    root = Path(pack_dir)
    if client is None:
        client = _container_client(account, container, client_id)

    uploaded: list[str] = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        blob_name = f"{destination}/{relative}"
        with path.open("rb") as handle:
            client.upload_blob(name=blob_name, data=handle, overwrite=False)
        uploaded.append(blob_name)

    manifest_last = bool(uploaded) and uploaded[-1].endswith(f"/{MANIFEST_NAME}")
    if not manifest_last:
        raise BlobTransportError("artifact manifest was not uploaded last")
    return {
        "account": account,
        "container": container,
        "credential_mode": CREDENTIAL_MODE,
        "manifest_uploaded_last": True,
        "managed_identity_client_id": client_id,
        "prefix": destination,
        "status": "uploaded",
        "uploaded": uploaded,
        "uploaded_count": len(uploaded),
    }


def upload_summary(result: Sequence[Any] | dict[str, Any]) -> str:
    if isinstance(result, dict):
        return (
            f"{result.get('status')} {result.get('uploaded_count', 0)} file(s) -> "
            f"{result.get('prefix')}"
        )
    return str(result)
