#!/usr/bin/env python
"""Build provenance for the Phase 1.0D semantic-review image.

A deliberate sibling of ``scripts/phase1_0d_build_provenance.py``, not an
extension of it.  That tool's record is a protected byte of the frozen
generation image: its bundle includes the tool itself, so any edit would
invalidate an immutable record.  The review image therefore gets its own
generator, its own bundle and its own record, and the two never touch.

What the record establishes: exactly which repository bytes were baked into the
review image, and that the addendum and rubric inside the image are the
committed ones.  What it does not establish: anything about reviewer accuracy,
model behaviour, hidden reasoning, or a "J-space".

Editing this file changes its own recorded hash, because it is inside its own
bundle.  That is intended: re-emit the record in Azure and commit both.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

DOCKERFILE = "Dockerfile.phase1-0d-review"
REQUIREMENTS = "requirements-calibration.txt"
RECORD_PATH = "phase1_0d_review_build_provenance.json"

PHASE = "1.0D"
TRACK = "b"
SCHEMA = "phase1-0d-review-build-provenance/v1"
BUNDLE_HASH_DOMAIN = "jspace-phase1-0d-review/build-bundle/v1"

BASE_IMAGE = "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"
BASE_IMAGE_DIGEST = (
    "sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126"
)

AUTHORITY_PROMPT = "docs/prompts/phase1_0d_generation_semantic_review_execution_prompt.md"
AUTHORITY_PROMPT_SHA256 = (
    "61f04923e4afaa3e6fd9f66d7b91a1316852de11b41dc6d3380ee827f5065d87"
)
PROTOCOL_SHA256 = "25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8"

#: The review surface only.  The frozen science bytes are covered by the frozen
#: tool's own record, which this image also verifies during the build, so the
#: two bundles stay disjoint and neither can quietly absorb the other.
BUNDLE_GLOBS: tuple[str, ...] = (
    DOCKERFILE,
    "scripts/run_phase1_0d_semantic_review.py",
    "scripts/phase1_0d_review_build_provenance.py",
    "scripts/phase1_0d_protected_bytes.py",
    "docs/phase1_0d_protected_bytes.json",
    "docs/phase1_0d_semantic_review_addendum.json",
    "docs/phase1_0d_semantic_review_rubric.md",
    "src/jspace_observation/semantic_review/*.py",
    AUTHORITY_PROMPT,
)

CLAIM_BOUNDARY = (
    "build provenance only; establishes which bytes are in the review image and "
    "nothing about reviewer accuracy, model behaviour, hidden reasoning, or a "
    "'J-space'"
)

_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")

REPO_ROOT = Path(__file__).resolve().parent.parent


class ReviewProvenanceError(RuntimeError):
    """A review-image provenance obligation cannot be met."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve_bundle_files(project_root: Path) -> list[Path]:
    resolved: set[Path] = set()
    for pattern in BUNDLE_GLOBS:
        matches = sorted(project_root.glob(pattern))
        if not matches:
            raise ReviewProvenanceError(f"bundle pattern matched no file: {pattern}")
        for match in matches:
            if not match.is_file():
                raise ReviewProvenanceError(f"bundle pattern matched a non-file: {match}")
            resolved.add(match)
    return sorted(resolved, key=lambda path: path.relative_to(project_root).as_posix())


def hash_bundle(project_root: Path) -> tuple[list[dict[str, Any]], str]:
    """Hash every declared file with LF-normalised bytes, then hash the list."""

    files: list[dict[str, Any]] = []
    for path in resolve_bundle_files(project_root):
        normalised = path.read_bytes().replace(b"\r\n", b"\n")
        files.append(
            {
                "path": path.relative_to(project_root).as_posix(),
                "sha256": sha256_bytes(normalised),
                "bytes": len(normalised),
            }
        )
    digest = hashlib.sha256()
    digest.update(BUNDLE_HASH_DOMAIN.encode("utf-8"))
    for entry in files:
        digest.update(b"\n")
        digest.update(f"{entry['path']}:{entry['sha256']}:{entry['bytes']}".encode("utf-8"))
    return files, digest.hexdigest()


def load_addendum_hashes(project_root: Path) -> dict[str, str]:
    """Read the addendum through its own loader, so validation runs too."""

    sys.path.insert(0, str(project_root / "src"))
    from jspace_observation.semantic_review.addendum import load_addendum  # noqa: PLC0415

    book = load_addendum(project_root)
    return {
        "addendum_sha256": book.sha256,
        "rubric_sha256": book.rubric_sha256,
        "base_protocol_sha256": str(book.document["base_protocol_sha256"]),
        "generation_image_digest": str(book.document["generation_image_digest"]),
        "reviewer_ids": {
            role: book.roles[role].reviewer_id for role in ("primary", "secondary", "third")
        },
        "request_profile_sha256": {
            role: book.roles[role].request_profile_sha256()
            for role in ("primary", "secondary", "third")
        },
    }


def build_record(project_root: Path, code_commit: str) -> dict[str, Any]:
    if not _COMMIT_PATTERN.match(code_commit):
        raise ReviewProvenanceError(
            f"code commit must be a full 40-character sha: {code_commit!r}"
        )
    files, digest = hash_bundle(project_root)
    authority = project_root / AUTHORITY_PROMPT
    authority_sha = sha256_bytes(authority.read_bytes().replace(b"\r\n", b"\n"))
    if authority_sha != AUTHORITY_PROMPT_SHA256:
        raise ReviewProvenanceError(
            f"the authority prompt hashes to {authority_sha}, expected "
            f"{AUTHORITY_PROMPT_SHA256}"
        )
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "artifact": "phase1_0d_review_build_provenance",
        "phase": PHASE,
        "track": TRACK,
        "authority_prompt": AUTHORITY_PROMPT,
        "authority_prompt_sha256": AUTHORITY_PROMPT_SHA256,
        "base_image": BASE_IMAGE,
        "base_image_digest": BASE_IMAGE_DIGEST,
        "base_protocol_sha256": PROTOCOL_SHA256,
        "bundle_hash_domain": BUNDLE_HASH_DOMAIN,
        "bundle_sha256": digest,
        "code_commit": code_commit,
        "dockerfile": DOCKERFILE,
        "file_count": len(files),
        "files": files,
        "requirements": REQUIREMENTS,
        "requirements_note": (
            "the review job is standard-library only; the pinned calibration "
            "requirements are installed and verified by the frozen generation "
            "provenance tool so the review image's environment is the same "
            "already-pinned environment rather than a second unpinned one"
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    record.update(load_addendum_hashes(project_root))
    return record


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def verify_image_context(project_root: Path, provenance: Path) -> dict[str, Any]:
    """Recompute the bundle inside the image and refuse any drift."""

    record = json.loads(provenance.read_text(encoding="utf-8"))
    files, digest = hash_bundle(project_root)
    if record.get("bundle_sha256") != digest:
        recorded = {entry["path"]: entry["sha256"] for entry in record.get("files", [])}
        actual = {entry["path"]: entry["sha256"] for entry in files}
        added = sorted(set(actual) - set(recorded))
        removed = sorted(set(recorded) - set(actual))
        changed = sorted(
            path for path in set(actual) & set(recorded) if actual[path] != recorded[path]
        )
        raise ReviewProvenanceError(
            f"baked review bytes hash to {digest}, record says "
            f"{record.get('bundle_sha256')}; added={added} removed={removed} "
            f"changed={changed}"
        )
    return {"bundle_sha256": digest, "file_count": len(files)}


def verify_addendum(project_root: Path, provenance: Path) -> dict[str, Any]:
    record = json.loads(provenance.read_text(encoding="utf-8"))
    observed = load_addendum_hashes(project_root)
    for key in ("addendum_sha256", "rubric_sha256", "base_protocol_sha256"):
        if record.get(key) != observed[key]:
            raise ReviewProvenanceError(
                f"{key} in the image is {observed[key]}, record says {record.get(key)}"
            )
    if observed["base_protocol_sha256"] != PROTOCOL_SHA256:
        raise ReviewProvenanceError("the addendum no longer binds the frozen protocol")
    return observed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser("emit", help="write the review build-provenance record")
    emit.add_argument("--code-commit", required=True)
    emit.add_argument("--output", default="")

    context = sub.add_parser("verify-image-context", help="recompute the baked bundle")
    context.add_argument("--provenance", default="")

    addendum = sub.add_parser("verify-addendum", help="recheck the addendum and rubric")
    addendum.add_argument("--provenance", default="")

    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()

    if args.command == "emit":
        record = build_record(root, args.code_commit)
        text = canonical_json(record)
        if args.output:
            Path(args.output).write_bytes(text.encode("utf-8"))
        sys.stdout.write(text)
        return 0

    provenance = Path(args.provenance) if args.provenance else root / RECORD_PATH
    if args.command == "verify-image-context":
        result = verify_image_context(root, provenance)
        print(f"REVIEW_BUNDLE_SHA256={result['bundle_sha256']}")
        print(f"REVIEW_BUNDLE_FILES={result['file_count']}")
        print("REVIEW_IMAGE_CONTEXT_OK=1")
        return 0

    result = verify_addendum(root, provenance)
    print(f"ADDENDUM_SHA256={result['addendum_sha256']}")
    print(f"RUBRIC_SHA256={result['rubric_sha256']}")
    print(f"BASE_PROTOCOL_SHA256={result['base_protocol_sha256']}")
    print("REVIEW_ADDENDUM_OK=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
