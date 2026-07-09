"""Tests for optional Azure Blob export helper."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.blob_export import upload_directory_to_blob


def test_blob_export_skips_without_config(monkeypatch, tmp_path):
    monkeypatch.delenv("JSPACE_BLOB_ACCOUNT", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_CONTAINER", raising=False)

    source = tmp_path / "results"
    source.mkdir()
    (source / "summary.md").write_text("ok", encoding="utf-8")

    assert upload_directory_to_blob(source, require=False) == 0


def test_blob_export_requires_config(monkeypatch, tmp_path):
    monkeypatch.delenv("JSPACE_BLOB_ACCOUNT", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_CONTAINER", raising=False)

    with pytest.raises(RuntimeError):
        upload_directory_to_blob(tmp_path, require=True)
