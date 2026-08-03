#!/usr/bin/env python
"""Drift check for the bytes the semantic-review v2 round must not change.

``docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md`` section 4
requires "a new protected-byte manifest that includes all frozen target bytes
plus the complete v1 reviewer instrument and gate evidence", and in the same
breath forbids modifying the old record "merely to make v2 pass".  So this is a
sibling of :mod:`scripts.phase1_0d_protected_bytes`, not a revision of it.  The
v1 record keeps its own patterns, its own 152 files and its own rollup, and it
must keep passing unchanged; this one covers a strictly larger set.

Why a larger set is the point.  The v1 record protected the target design but
not the reviewer instrument, which is exactly the surface that failed: a rubric
and a fixture bank could have been edited between the gate run and the handoff
without any check noticing.  They cannot be now.  The v1 addendum, rubric,
runner, provenance, Dockerfile, launchers, reviewer package and the four gate
artifacts are all pinned here, together with the v2 documents frozen before any
v2 provider call.

Deliberately *not* covered:

``scripts/run_phase1_0d_semantic_review_v2.py`` and
``Dockerfile.phase1-0d-review-v2``
    The image-baked v2 surface is held by
    ``phase1_0d_review_v2_build_provenance.json``, which additionally proves
    what went into the image.  The external ACA launcher is different: it is
    not baked into the image, so it is pinned below by this record.

Azure-side objects
    the locked image tag and manifest are held immutable by the registry.

What this establishes, stated narrowly: that the named files hold the same
bytes now as when this baseline was cut.  It says nothing about whether those
bytes were correct -- the v1 round is the standing proof that they can be
internally contradictory and still hash perfectly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = "phase1-0d-rv2-protected-bytes/v1"
ROLLUP_DOMAIN = "jspace-phase1-0d/rv2-protected-bytes/v1"
BASELINE_FILENAME = "docs/phase1_0d_rv2_protected_bytes.json"

AUTHORITY_PROMPT = "docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md"

# Every pattern is required to match at least one file.  A pattern that stops
# matching is itself drift: it means a protected path was renamed or deleted.
PROTECTED_GLOBS: tuple[str, ...] = (
    # -- the frozen Phase 1.0D target design --------------------------------
    "docs/phase1_0d_protocol_snapshot.json",
    "phase1_0d_build_provenance.json",
    "scripts/phase1_0d_build_provenance.py",
    "scripts/run_phase1_0d_confirmation.py",
    "src/jspace_observation/phase1_0d_confirmation.py",
    "src/jspace_observation/phase1_0d_execution.py",
    "src/jspace_observation/phase1_0d_generation.py",
    "Dockerfile.phase1-0d",
    "data/phase1_task_headroom_candidates.jsonl",
    "infra/azure/scripts/18_build_phase1_0d_confirmation.sh",
    "infra/azure/scripts/19_run_phase1_0d_confirmation.sh",
    # This control-plane launcher is not baked into the review image.
    "infra/azure/scripts/23_run_phase1_0d_semantic_review_v2.sh",
    "docs/prompts/phase_science_restart_after_parser_closure_prompt.md",
    # -- the complete v1 reviewer instrument --------------------------------
    "docs/prompts/phase1_0d_generation_semantic_review_execution_prompt.md",
    "docs/phase1_0d_semantic_review_addendum.json",
    "docs/phase1_0d_semantic_review_rubric.md",
    "docs/phase1_0d_protected_bytes.json",
    "scripts/phase1_0d_protected_bytes.py",
    "scripts/run_phase1_0d_semantic_review.py",
    "scripts/phase1_0d_review_build_provenance.py",
    "phase1_0d_review_build_provenance.json",
    "Dockerfile.phase1-0d-review",
    "src/jspace_observation/semantic_review/*.py",
    "infra/azure/scripts/20_build_phase1_0d_review.sh",
    "infra/azure/scripts/21_run_phase1_0d_semantic_review.sh",
    # -- the v1 terminal gate evidence --------------------------------------
    "artifacts/phase1-0d-semantic-review-gate/**/*",
    # -- the v2 documents frozen before any v2 provider call ----------------
    "docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md",
    "docs/decisions/phase1_0d_semantic_review_v1_specification_correction.md",
    "docs/phase1_0d_semantic_review_rubric_v2.md",
    "docs/phase1_0d_semantic_review_addendum_v2.json",
)

CLAIM_BOUNDARY = (
    "byte-identity of the declared protected paths only; establishes nothing "
    "about their scientific correctness, nothing about paths outside the "
    "declared patterns, nothing about reviewer accuracy, and nothing about "
    "model behaviour or a 'J-space'"
)

TERMINAL_STATE_ON_MISMATCH = "BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT"


class Rv2ProtectedBytesError(RuntimeError):
    """Raised when the v2 protected-byte obligation cannot be met."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve_protected_files(project_root: Path) -> list[Path]:
    """Expand the declared patterns into a sorted, deduplicated file list."""

    resolved: set[Path] = set()
    for pattern in PROTECTED_GLOBS:
        matches = [match for match in project_root.glob(pattern) if match.is_file()]
        if not matches:
            raise Rv2ProtectedBytesError(
                f"protected pattern matched no file: {pattern}"
            )
        resolved.update(matches)
    return sorted(resolved, key=lambda path: path.relative_to(project_root).as_posix())


def hash_protected(project_root: Path) -> tuple[list[dict[str, object]], str]:
    """Hash every protected file, then hash the list of hashes.

    Line endings are normalised to LF first, for the same reason the v1 record
    and both build-provenance records normalise them: the repository is
    developed on Windows and stores LF, so raw bytes would differ between
    checkouts of one commit.
    """

    files: list[dict[str, object]] = []
    for path in resolve_protected_files(project_root):
        normalised = path.read_bytes().replace(b"\r\n", b"\n")
        files.append(
            {
                "path": path.relative_to(project_root).as_posix(),
                "sha256": sha256_bytes(normalised),
                "bytes": len(normalised),
            }
        )
    payload = "\n".join(f"{entry['path']} {entry['sha256']}" for entry in files)
    rollup = sha256_bytes(f"{ROLLUP_DOMAIN}\n{payload}\n".encode("utf-8"))
    return files, rollup


def canonical(document: dict[str, object]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def build_document(project_root: Path, code_commit: str) -> dict[str, object]:
    if len(code_commit) != 40 or any(c not in "0123456789abcdef" for c in code_commit):
        raise Rv2ProtectedBytesError(
            f"code_commit must be a full sha1: {code_commit!r}"
        )
    files, rollup = hash_protected(project_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "authority_prompt": AUTHORITY_PROMPT,
        "supersedes_nothing": (
            "docs/phase1_0d_protected_bytes.json remains in force unchanged; "
            "this record is additive and covers a strictly larger set"
        ),
        "code_commit": code_commit,
        "patterns": list(PROTECTED_GLOBS),
        "file_count": len(files),
        "files": files,
        "rollup_sha256": rollup,
        "claim_boundary": CLAIM_BOUNDARY,
        "terminal_state_on_mismatch": TERMINAL_STATE_ON_MISMATCH,
    }


def load_baseline(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != SCHEMA_VERSION:
        raise Rv2ProtectedBytesError(
            f"baseline schema is {document.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION!r}"
        )
    return document


def verify(project_root: Path, baseline: Path) -> list[str]:
    """Return one line per protected-byte difference; empty means unchanged."""

    document = load_baseline(baseline)
    recorded = {
        str(entry["path"]): str(entry["sha256"])
        for entry in document.get("files", [])  # type: ignore[union-attr]
    }
    if list(document.get("patterns", [])) != list(PROTECTED_GLOBS):
        return ["the declared protected patterns differ from the baseline"]

    files, rollup = hash_protected(project_root)
    present = {str(entry["path"]): str(entry["sha256"]) for entry in files}

    failures: list[str] = []
    for path in sorted(set(recorded) - set(present)):
        failures.append(f"protected file is gone: {path}")
    for path in sorted(set(present) - set(recorded)):
        failures.append(f"a new file appeared under a protected pattern: {path}")
    for path in sorted(set(recorded) & set(present)):
        if recorded[path] != present[path]:
            failures.append(f"protected bytes changed: {path}")
    if rollup != document["rollup_sha256"]:
        failures.append(
            f"rollup is {rollup}, baseline recorded {document['rollup_sha256']}"
        )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("emit", "verify"))
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--code-commit", default="")
    parser.add_argument("--baseline", default="")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    baseline = Path(args.baseline) if args.baseline else root / BASELINE_FILENAME

    if args.mode == "emit":
        document = build_document(root, args.code_commit)
        baseline.write_text(canonical(document), encoding="utf-8")
        print(f"RV2_PROTECTED_FILE_COUNT={document['file_count']}")
        print(f"RV2_PROTECTED_ROLLUP_SHA256={document['rollup_sha256']}")
        return 0

    failures = verify(root, baseline)
    for failure in failures:
        print(f"RV2_PROTECTED_BYTES_DRIFT: {failure}")
    if failures:
        print(TERMINAL_STATE_ON_MISMATCH)
        return 1
    document = load_baseline(baseline)
    print(f"RV2_PROTECTED_FILE_COUNT={document['file_count']}")
    print(f"RV2_PROTECTED_ROLLUP_SHA256={document['rollup_sha256']}")
    print("RV2_PROTECTED_BYTES_OK=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
