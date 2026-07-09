"""Smoke test Azure Blob export using managed identity."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jspace_observation.blob_export import upload_directory_to_blob


def main() -> None:
    smoke_dir = Path("/tmp/jspace-blob-smoke")
    smoke_dir.mkdir(parents=True, exist_ok=True)
    smoke_file = smoke_dir / "smoke.txt"
    smoke_file.write_text(
        f"blob smoke {datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}\n",
        encoding="utf-8",
    )
    uploaded = upload_directory_to_blob(smoke_dir, require=True)
    if uploaded < 1:
        raise RuntimeError("Blob smoke upload produced no files")


if __name__ == "__main__":
    main()

