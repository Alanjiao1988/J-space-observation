"""Tests for the OD-008 retokenisation helpers.

The git blob id is what anchors the tokenizer on disk to the revision the
authority pins, so it is tested against values computed independently by git
itself rather than against the tool's own output.

DC-003 is the reason the BOS handling is tested at all: the first run of this
tool produced BOS-free sequences, exited 0, and printed its proof string.
"""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "study5_eq1_retok", _TOOLS / "retokenise_corpus.py"
)
assert _SPEC is not None and _SPEC.loader is not None
retok = importlib.util.module_from_spec(_SPEC)
sys.modules["study5_eq1_retok"] = retok
_SPEC.loader.exec_module(retok)


def test_git_blob_sha1_matches_git_hash_object(tmp_path) -> None:
    """Verified against git itself, not against our own implementation."""

    payload = b"the quick brown fox\n\x00\xff binary too"
    path = tmp_path / "sample.bin"
    path.write_bytes(payload)

    ours = retok.git_blob_sha1(path)

    try:
        theirs = subprocess.run(
            ["git", "hash-object", "--", str(path)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover
        # git absent: fall back to the documented blob construction.
        header = f"blob {len(payload)}\0".encode("ascii")
        theirs = hashlib.sha1(header + payload).hexdigest()

    assert ours == theirs


def test_git_blob_sha1_of_empty_file_is_the_well_known_constant(tmp_path) -> None:
    path = tmp_path / "empty"
    path.write_bytes(b"")
    assert retok.git_blob_sha1(path) == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def test_token_ids_bytes_matches_the_frozen_corpus_encoding() -> None:
    """The corpus froze token_ids_sha256 over this exact byte encoding.

    If the separators or the type handling drifted, every reproduced hash in
    step 1 would silently stop matching.
    """

    assert retok.token_ids_bytes([1, 2, 3]) == b"[1,2,3]"
    digest = retok.sha256_bytes(retok.token_ids_bytes([151646, 3385]))
    assert digest == hashlib.sha256(b"[151646,3385]").hexdigest()


def test_token_ids_bytes_rejects_bools_and_empty_sequences() -> None:
    """bool is a subclass of int, so it would encode as true/false and change
    the digest without any type error."""

    for bad in ([], [1, True, 3], [1, None]):
        try:
            retok.token_ids_bytes(bad)  # type: ignore[arg-type]
        except retok.RetokeniseError:
            continue
        raise AssertionError(f"{bad!r} should have been rejected")


def test_verify_tokenizer_bytes_rejects_a_file_whose_blob_id_differs(tmp_path) -> None:
    """The anchor must reject substituted bytes, which is its whole purpose."""

    (tmp_path / "tokenizer.json").write_bytes(b"not the real tokenizer")
    (tmp_path / "tokenizer_config.json").write_bytes(b"nor this")
    try:
        retok.verify_tokenizer_bytes(tmp_path)
    except retok.RetokeniseError as exc:
        assert "does not match the registered" in str(exc)
        return
    raise AssertionError("substituted tokenizer bytes were accepted")


def test_verify_tokenizer_bytes_reports_a_missing_file(tmp_path) -> None:
    try:
        retok.verify_tokenizer_bytes(tmp_path)
    except retok.RetokeniseError as exc:
        assert "missing" in str(exc)
        return
    raise AssertionError("a missing tokenizer file was accepted")


def test_the_stop_threshold_is_the_registered_value() -> None:
    """OD-008 stops if either fitting half falls below 400 survivors."""

    assert retok.MIN_SURVIVORS_PER_FIT_HALF == 400
    assert retok.MAX_SEQ_LEN == 128


def test_the_registered_tokenizer_revision_is_the_7b_target() -> None:
    assert retok.TOKENIZER_REVISION == "916b56a44061fd5cd7d6a8fb632557ed4f724f60"
    assert retok.TOKENIZER_ID.endswith("DeepSeek-R1-Distill-Qwen-7B")
