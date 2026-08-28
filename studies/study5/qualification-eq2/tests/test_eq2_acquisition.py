"""OD-011 failing cases for the EQ2 external acquisition checks.

OD-011 exists because IMG-001 and DC-003 were both checks that COULD NOT FAIL:
one never executed its assertions at all, the other asserted a Python attribute
assignment had succeeded, which it always has. OD-003 proves a check ran. Only a
demonstrated failing case proves it can fail.

So every test below feeds deliberately wrong input and proves the check reports
FAIL. A test that only shows the happy path would leave exactly the hole OD-011
was written to close.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "eq2_acquire", _TOOLS / "acquire_external.py"
)
assert _SPEC is not None and _SPEC.loader is not None
acq = importlib.util.module_from_spec(_SPEC)
sys.modules["eq2_acquire"] = acq
_SPEC.loader.exec_module(acq)

PAYLOAD = b"the registered artifact bytes\n"
TAMPERED = b"the registered artifact bytes!\n"


def true_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def true_git_blob(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


# --------------------------------------------------------------------------
# positive path: the check passes on correct input
# --------------------------------------------------------------------------


def test_lfs_anchor_accepts_the_correct_bytes() -> None:
    record = acq.verify_against_origin(
        PAYLOAD, lfs_oid=true_sha256(PAYLOAD), git_oid=None, path="x.pt"
    )
    assert record["verified"] is True
    assert record["method"] == "lfs_sha256"


def test_git_blob_anchor_accepts_the_correct_bytes() -> None:
    record = acq.verify_against_origin(
        PAYLOAD, lfs_oid=None, git_oid=true_git_blob(PAYLOAD), path="config.yaml"
    )
    assert record["verified"] is True
    assert record["method"] == "git_blob_sha1"


# --------------------------------------------------------------------------
# OD-011 failing cases: the check must REJECT wrong input
# --------------------------------------------------------------------------


def test_lfs_anchor_rejects_tampered_bytes() -> None:
    """A single changed byte must be caught."""

    with pytest.raises(acq.AcquisitionError) as excinfo:
        acq.verify_against_origin(
            TAMPERED, lfs_oid=true_sha256(PAYLOAD), git_oid=None, path="x.pt"
        )
    assert "does not match the origin-published" in str(excinfo.value)


def test_git_blob_anchor_rejects_tampered_bytes() -> None:
    with pytest.raises(acq.AcquisitionError):
        acq.verify_against_origin(
            TAMPERED, lfs_oid=None, git_oid=true_git_blob(PAYLOAD), path="config.yaml"
        )


def test_a_file_with_no_origin_anchor_is_rejected_not_waved_through() -> None:
    """An unanchored file is unverifiable, which is a stop.

    The dangerous alternative is treating "nothing to compare against" as
    "nothing wrong", which would silently accept whatever the transport
    returned.
    """

    with pytest.raises(acq.AcquisitionError) as excinfo:
        acq.verify_against_origin(PAYLOAD, lfs_oid=None, git_oid=None, path="x.pt")
    assert "cannot be verified" in str(excinfo.value)


def test_a_git_blob_id_is_not_accepted_as_though_it_were_a_sha256() -> None:
    """The two anchor kinds must not be conflated.

    Passing the git blob id in the lfs_oid slot must fail, because the bytes do
    not hash to it under SHA-256. If the tool ever compared 'whichever id we
    have' against 'whichever digest we computed', this would pass.
    """

    with pytest.raises(acq.AcquisitionError):
        acq.verify_against_origin(
            PAYLOAD, lfs_oid=true_git_blob(PAYLOAD), git_oid=None, path="x.pt"
        )


def test_sha256_of_fetched_bytes_is_never_used_as_the_anchor() -> None:
    """The circularity guard.

    For a non-LFS file the record does carry a sha256 of the fetched bytes, but
    it must be labelled as a description, not as the value the file was checked
    against. Verifying an object against a digest computed from that same object
    proves nothing.
    """

    record = acq.verify_against_origin(
        PAYLOAD, lfs_oid=None, git_oid=true_git_blob(PAYLOAD), path="config.yaml"
    )
    assert record["authoritative_sha256"] is None
    assert "sha256_of_fetched_bytes_not_an_anchor" in record
    assert record["method"] == "git_blob_sha1"


def test_truncated_bytes_are_rejected() -> None:
    """The short-read case that actually occurred in EQ1's P-1 side track."""

    with pytest.raises(acq.AcquisitionError):
        acq.verify_against_origin(
            PAYLOAD[:-5], lfs_oid=true_sha256(PAYLOAD), git_oid=None, path="x.pt"
        )


def test_empty_bytes_are_rejected() -> None:
    """A zero-length response must not pass; an empty file has a valid digest of
    its own and would sail through a naive 'did we get a digest?' check."""

    with pytest.raises(acq.AcquisitionError):
        acq.verify_against_origin(
            b"", lfs_oid=true_sha256(PAYLOAD), git_oid=None, path="x.pt"
        )


# --------------------------------------------------------------------------
# registration integrity
# --------------------------------------------------------------------------


def test_the_registered_revision_is_the_one_the_authority_pins() -> None:
    assert acq.REVISION == "0731326edff4ae730ffc5356fe1a4728c748b3a6"
    assert acq.REPO == "neuronpedia/jacobian-lens"


def test_every_registered_role_carries_a_lens_a_config_and_a_convergence_csv() -> None:
    for role, paths in acq.REGISTERED_FILES.items():
        assert any(p.endswith(".pt") for p in paths), role
        assert any(p.endswith("config.yaml") for p in paths), role
        assert any(p.endswith("_convergence.csv") for p in paths), role


def test_the_three_roles_are_exactly_the_registered_ones() -> None:
    assert set(acq.REGISTERED_FILES) == {
        "positive_control",
        "negative_control",
        "depth_test",
    }


def test_content_address_layout_matches_the_committed_scheme() -> None:
    digest = "ab" + "c" * 62
    assert acq.content_address(digest) == f"sha256/ab/{digest}"
