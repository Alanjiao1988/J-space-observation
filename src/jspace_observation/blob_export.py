"""Upload experiment result directories to Azure Blob Storage."""

from __future__ import annotations

import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


def upload_directory_to_blob(local_dir: str | Path, *, require: bool = False) -> int:
    """Upload all files in a directory to Azure Blob Storage.

    Configuration comes from environment variables:
    - JSPACE_BLOB_ACCOUNT
    - JSPACE_BLOB_CONTAINER
    - JSPACE_BLOB_PREFIX
    - AZURE_CLIENT_ID (optional user-assigned managed identity client ID)

    Returns the number of files uploaded. If config is absent, returns 0 unless
    ``require`` is true.
    """
    account = os.getenv("JSPACE_BLOB_ACCOUNT")
    container = os.getenv("JSPACE_BLOB_CONTAINER")
    prefix = os.getenv("JSPACE_BLOB_PREFIX", "").strip("/")
    client_id = os.getenv("AZURE_CLIENT_ID")

    if not account or not container:
        msg = "Blob export skipped: JSPACE_BLOB_ACCOUNT or JSPACE_BLOB_CONTAINER not set"
        print(msg)
        if require:
            raise RuntimeError(msg)
        return 0

    local_path = Path(local_dir)
    if not local_path.exists():
        msg = f"Blob export source not found: {local_path}"
        print(msg)
        if require:
            raise FileNotFoundError(msg)
        return 0

    credential = (
        DefaultAzureCredential(managed_identity_client_id=client_id)
        if client_id
        else DefaultAzureCredential()
    )
    service = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=credential,
    )

    uploaded = 0
    for file_path in local_path.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(local_path).as_posix()
        blob_name = f"{prefix}/{rel}" if prefix else rel
        blob_client = service.get_blob_client(container=container, blob=blob_name)
        with file_path.open("rb") as handle:
            blob_client.upload_blob(handle, overwrite=True)
        uploaded += 1
        print(f"Uploaded blob: {blob_name}")

    print(f"Blob export complete: {uploaded} files")
    return uploaded

