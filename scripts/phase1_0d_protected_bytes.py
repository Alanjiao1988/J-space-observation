#!/usr/bin/env python
"""Baseline and drift check for the bytes section 2.3 forbids changing.

The controlling prompt
``docs/prompts/phase1_0d_generation_semantic_review_execution_prompt.md``
names a set of files that must not be edited or regenerated while the Phase
1.0D generation and semantic review are executed, and requires their SHA-256 to
be recorded before implementation, rechecked before the target run, and
rechecked again in the final handoff.  A mismatch is a terminal state
(``BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT``), not something to reconcile.

What this establishes, stated narrowly: that the named files hold the same
bytes now as when the baseline was cut.  It says nothing about whether those
bytes were correct in the first place, nothing about files outside the declared
patterns, and nothing about the Azure-side objects (the locked image tag and
manifest) which are held immutable by the registry rather than by this tool.

Two entries are protected here that section 2.3 does not name literally:

``scripts/phase1_0d_build_provenance.py``
    it hashes *itself* into the frozen bundle recorded by
    ``phase1_0d_build_provenance.json``, so editing it would break the
    protected record even though the record is what the prompt names.

``docs/prompts/phase_science_restart_after_parser_closure_prompt.md``
    the same frozen bundle covers it, for the same reason.

Recording them here makes that coupling visible instead of leaving it as a trap
for the next person who reaches for the file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA_VERSION = "phase1-0d-protected-bytes/v1"
ROLLUP_DOMAIN = "jspace-phase1-0d/protected-bytes/v1"
BASELINE_FILENAME = "docs/phase1_0d_protected_bytes.json"

AUTHORITY_PROMPT = (
    "docs/prompts/phase1_0d_generation_semantic_review_execution_prompt.md"
)

# Every pattern is required to match at least one file.  A pattern that stops
# matching is itself drift: it means a protected path was renamed or deleted.
PROTECTED_GLOBS: tuple[str, ...] = (
    # -- the frozen Phase 1.0D design ---------------------------------------
    "docs/phase1_0d_protocol_snapshot.json",
    "phase1_0d_build_provenance.json",
    "scripts/phase1_0d_build_provenance.py",
    "scripts/run_phase1_0d_confirmation.py",
    "src/jspace_observation/phase1_0d_confirmation.py",
    "src/jspace_observation/phase1_0d_execution.py",
    "src/jspace_observation/phase1_0d_generation.py",
    "Dockerfile.phase1-0d",
    "docs/prompts/phase_science_restart_after_parser_closure_prompt.md",
    # -- the Phase 1.0C run 20260725T170041Z --------------------------------
    "artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/**/*",
    "artifacts/phase1-headroom-calibration/track-b/20260725T170041Z-generate/**/*",
    "artifacts/phase1-headroom-calibration/track-b/20260725T170041Z-semantic-review/**/*",
    # -- parser-v3: code, tests, schemas, IaC, reports, sealed objects -------
    "Dockerfile.parser-v3-eval",
    "artifacts/phase1-evaluator-validation/**/*",
    "artifacts/phase1-parser-v3/**/*",
    "docs/decisions/parser_v3_locked_evaluation_closure.md",
    "docs/*parser_v3*",
    "evaluator_sets/parser_v3_v1/**/*",
    "infra/azure/parser_v3_v2_boundary/**/*",
    "infra/azure/scripts/09_build_parser_v3_eval.sh",
    "infra/azure/scripts/10_run_parser_v3_locked_eval.sh",
    "reports/*parser_v3*",
    "scripts/*parser_v3*",
    "src/jspace_observation/parser_v3_*",
    "tests/test_parser_v3_*",
)

CLAIM_BOUNDARY = (
    "byte-identity of the declared protected paths only; establishes nothing "
    "about their scientific correctness, nothing about paths outside the "
    "declared patterns, and nothing about model behaviour or a 'J-space'"
)


class ProtectedBytesError(RuntimeError):
    """Raised when the protected-byte obligation cannot be met."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve_protected_files(project_root: Path) -> list[Path]:
    """Expand the declared patterns into a sorted, deduplicated file list."""

    resolved: set[Path] = set()
    for pattern in PROTECTED_GLOBS:
        matches = [match for match in project_root.glob(pattern) if match.is_file()]
        if not matches:
            raise ProtectedBytesError(f"protected pattern matched no file: {pattern}")
        resolved.update(matches)
    return sorted(resolved, key=lambda path: path.relative_to(project_root).as_posix())


def hash_protected(project_root: Path) -> tuple[list[dict[str, object]], str]:
    """Hash every protected file, then hash the list of hashes.

    Line endings are normalised to LF first, for the same reason the build
    provenance normalises them: the repository is developed on Windows and
    stores LF, so raw bytes would differ between checkouts of one commit.
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
        raise ProtectedBytesError(f"code_commit must be a full sha1: {code_commit!r}")
    files, rollup = hash_protected(project_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "authority_prompt": AUTHORITY_PROMPT,
        "code_commit": code_commit,
        "patterns": list(PROTECTED_GLOBS),
        "file_count": len(files),
        "files": files,
        "rollup_sha256": rollup,
        "claim_boundary": CLAIM_BOUNDARY,
        "terminal_state_on_mismatch": "BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT",
    }


def load_baseline(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ProtectedBytesError(
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
        print(f"PROTECTED_FILE_COUNT={document['file_count']}")
        print(f"PROTECTED_ROLLUP_SHA256={document['rollup_sha256']}")
        return 0

    failures = verify(root, baseline)
    for failure in failures:
        print(f"PROTECTED_BYTES_DRIFT: {failure}")
    if failures:
        print("BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT")
        return 1
    document = load_baseline(baseline)
    print(f"PROTECTED_FILE_COUNT={document['file_count']}")
    print(f"PROTECTED_ROLLUP_SHA256={document['rollup_sha256']}")
    print("PROTECTED_BYTES_OK=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
