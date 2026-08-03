#!/usr/bin/env python
"""Verify the persisted v2 smoke license before target generation."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_phase1_0d_semantic_review_v2 as runner  # noqa: E402
from jspace_observation.semantic_review_v2 import addendum_v2  # noqa: E402


class GateLicenseError(RuntimeError):
    """The supplied files do not license the irreversible target run."""


class _StaticGateClient:
    def __init__(self, prefix: str, manifest: bytes, receipt: bytes) -> None:
        self._objects = {
            f"{prefix}/artifact_manifest.json": manifest,
            f"{prefix}/00_gate_receipt.json": receipt,
        }

    def get(self, name: str) -> bytes:
        try:
            return self._objects[name]
        except KeyError as error:
            raise GateLicenseError(f"gate verifier refuses undeclared object {name}") from error


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_gate_files(
    *,
    project_root: Path,
    manifest_path: Path,
    receipt_path: Path,
    smoke_run_id: str,
    expected_manifest_sha256: str,
    expected_receipt_sha256: str,
    expected_review_code_commit: str,
    expected_review_image_digest: str,
) -> dict[str, Any]:
    """Validate exact persisted bytes through the same checks used by review."""

    if not runner.UTC_RUN_ID.fullmatch(smoke_run_id):
        raise GateLicenseError("smoke run id is not one exact UTC stamp")
    if not runner.SHA1.fullmatch(expected_review_code_commit):
        raise GateLicenseError("review code commit is not a full SHA-1")
    if not runner.SHA256_DIGEST.fullmatch(expected_review_image_digest):
        raise GateLicenseError("review image is not digest-pinned")
    for name, value in (
        ("manifest", expected_manifest_sha256),
        ("receipt", expected_receipt_sha256),
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise GateLicenseError(f"expected {name} SHA-256 is malformed")

    manifest = manifest_path.read_bytes()
    receipt = receipt_path.read_bytes()
    if _sha256(manifest) != expected_manifest_sha256:
        raise GateLicenseError("persisted smoke manifest hash differs from the license")
    if _sha256(receipt) != expected_receipt_sha256:
        raise GateLicenseError("persisted smoke receipt hash differs from the license")

    prefix = f"{runner.SMOKE_PREFIX_ROOT}/{smoke_run_id}"
    book = addendum_v2.load_addendum_v2(project_root)
    gate = runner._load_gate_receipt(
        _StaticGateClient(prefix, manifest, receipt),
        prefix,
        book,
    )
    if gate.get("run_id") != smoke_run_id:
        raise GateLicenseError("smoke receipt run id differs from its Blob prefix")
    if gate.get("review_code_commit") != expected_review_code_commit:
        raise GateLicenseError("smoke receipt came from a different review commit")
    if gate.get("review_image_digest") != expected_review_image_digest:
        raise GateLicenseError("smoke receipt came from a different review image")
    if gate.get("_receipt_sha256") != expected_receipt_sha256:
        raise GateLicenseError("validated receipt hash differs from the launch license")

    return {
        "smoke_run_id": smoke_run_id,
        "smoke_prefix": prefix,
        "manifest_sha256": expected_manifest_sha256,
        "receipt_sha256": expected_receipt_sha256,
        "review_code_commit": expected_review_code_commit,
        "review_image_digest": expected_review_image_digest,
        "exact_expected_label_matches": gate["counts"][
            "exact_expected_label_matches"
        ],
        "licensed": True,
    }


def verify_qualification_files(
    *,
    project_root: Path,
    manifest_path: Path,
    receipt_path: Path,
    qualification_run_id: str,
    expected_manifest_sha256: str,
    expected_receipt_sha256: str,
    expected_review_code_commit: str,
    expected_review_image_digest: str,
) -> dict[str, Any]:
    """Validate the exact 3/3 qualification bytes before claiming the smoke lock."""

    if not runner.UTC_RUN_ID.fullmatch(qualification_run_id):
        raise GateLicenseError("qualification run id is not one exact UTC stamp")
    if not runner.SHA1.fullmatch(expected_review_code_commit):
        raise GateLicenseError("review code commit is not a full SHA-1")
    if not runner.SHA256_DIGEST.fullmatch(expected_review_image_digest):
        raise GateLicenseError("review image is not digest-pinned")
    for name, value in (
        ("manifest", expected_manifest_sha256),
        ("receipt", expected_receipt_sha256),
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise GateLicenseError(f"expected {name} SHA-256 is malformed")

    manifest = manifest_path.read_bytes()
    receipt = receipt_path.read_bytes()
    if _sha256(manifest) != expected_manifest_sha256:
        raise GateLicenseError(
            "persisted qualification manifest hash differs from the license"
        )
    if _sha256(receipt) != expected_receipt_sha256:
        raise GateLicenseError(
            "persisted qualification receipt hash differs from the license"
        )

    prefix = f"{runner.QUALIFICATION_PREFIX_ROOT}/{qualification_run_id}"
    book = addendum_v2.load_addendum_v2(project_root)
    qualification = runner._load_qualification_receipt(
        _StaticGateClient(prefix, manifest, receipt),
        prefix,
        book,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_receipt_sha256=expected_receipt_sha256,
    )
    if qualification.get("run_id") != qualification_run_id:
        raise GateLicenseError(
            "qualification receipt run id differs from its Blob prefix"
        )
    if qualification.get("review_code_commit") != expected_review_code_commit:
        raise GateLicenseError(
            "qualification receipt came from a different review commit"
        )
    if qualification.get("review_image_digest") != expected_review_image_digest:
        raise GateLicenseError(
            "qualification receipt came from a different review image"
        )
    if qualification.get("_receipt_sha256") != expected_receipt_sha256:
        raise GateLicenseError(
            "validated qualification hash differs from the launch license"
        )

    return {
        "qualification_run_id": qualification_run_id,
        "qualification_prefix": prefix,
        "manifest_sha256": expected_manifest_sha256,
        "receipt_sha256": expected_receipt_sha256,
        "review_code_commit": expected_review_code_commit,
        "review_image_digest": expected_review_image_digest,
        "valid_expected_label_matches": qualification["counts"][
            "valid_expected_label_matches"
        ],
        "licensed": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    run_id = parser.add_mutually_exclusive_group(required=True)
    run_id.add_argument("--smoke-run-id")
    run_id.add_argument("--qualification-run-id")
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--review-code-commit", required=True)
    parser.add_argument("--review-image-digest", required=True)
    args = parser.parse_args(argv)

    common = {
        "project_root": args.project_root.resolve(),
        "manifest_path": args.manifest.resolve(),
        "receipt_path": args.receipt.resolve(),
        "expected_manifest_sha256": args.manifest_sha256,
        "expected_receipt_sha256": args.receipt_sha256,
        "expected_review_code_commit": args.review_code_commit,
        "expected_review_image_digest": args.review_image_digest,
    }
    if args.qualification_run_id:
        result = verify_qualification_files(
            qualification_run_id=args.qualification_run_id,
            **common,
        )
        print(
            "RV2_QUALIFICATION_RUN_ID="
            f"{result['qualification_run_id']}"
        )
        print(
            "RV2_QUALIFICATION_RECEIPT_SHA256="
            f"{result['receipt_sha256']}"
        )
        print(
            "RV2_QUALIFICATION_MANIFEST_SHA256="
            f"{result['manifest_sha256']}"
        )
        print("RV2_QUALIFICATION_3_OF_3_LICENSE_VERIFIED=1")
    else:
        result = verify_gate_files(
            smoke_run_id=args.smoke_run_id,
            **common,
        )
        print(f"RV2_SMOKE_RUN_ID={result['smoke_run_id']}")
        print(f"RV2_SMOKE_RECEIPT_SHA256={result['receipt_sha256']}")
        print(f"RV2_SMOKE_MANIFEST_SHA256={result['manifest_sha256']}")
        print("RV2_SMOKE_60_OF_60_LICENSE_VERIFIED=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
