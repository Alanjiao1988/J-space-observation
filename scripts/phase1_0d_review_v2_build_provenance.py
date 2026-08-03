#!/usr/bin/env python
"""Build provenance for the Phase 1.0D semantic-review **v2** image.

A third sibling, disjoint from both existing records.
``scripts/phase1_0d_build_provenance.py`` covers the frozen generation science;
``scripts/phase1_0d_review_build_provenance.py`` covers the v1 review surface.
Both of those records are protected bytes and neither may move, so the v2
surface gets its own generator, its own bundle and its own record.  The three
bundles do not overlap, which is why adding v2 changes neither of the first two
digests.

Section 8 of the v2 authority lists eleven things the build must verify inside
the image.  This tool implements them as three subcommands the Dockerfile
chains together, so a build cannot succeed while any of them is false:

``verify-image-context``
    the source bundle re-hashes to the recorded digest;
``verify-instrument``
    the v2 authority prompt, addendum, rubric and 20-fixture bank hash to their
    frozen values; the base protocol and task-id hashes are unchanged; the
    generation-image binding is unchanged; the three reviewer identities and
    request profiles are the registered ones; and the v1 artifacts named as
    historical parents still hash to what the addendum records;
``verify-no-target-output``
    no target generation record, judgment, metric or result pack is baked in.

The last one is the reason the image can be trusted to run a *prospective*
gate: the smoke stage cannot peek at an experiment that is not in the image and
that it holds no capability to fetch.

What the record establishes: exactly which repository bytes were baked into the
v2 review image.  What it does not establish: anything about reviewer accuracy,
model behaviour, hidden reasoning, or a "J-space".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

DOCKERFILE = "Dockerfile.phase1-0d-review-v2"
REQUIREMENTS = "requirements-calibration.txt"
RECORD_PATH = "phase1_0d_review_v2_build_provenance.json"

PHASE = "1.0D"
TRACK = "b"
SCHEMA = "phase1-0d-review-v2-build-provenance/v1"
BUNDLE_HASH_DOMAIN = "jspace-phase1-0d-review-v2/build-bundle/v1"

BASE_IMAGE = "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"
BASE_IMAGE_DIGEST = (
    "sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126"
)

AUTHORITY_PROMPT = "docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md"
AUTHORITY_PROMPT_SHA256 = (
    "7b93c90a299ff4e77b83d4633624053f8ce53afcd04279ca3050c5ab14428e19"
)
PROTOCOL_SHA256 = "25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8"
TASK_IDS_SHA256 = "0d3fe6add211a381a321ea974502d262faf65312dc504e2acceb7c6556b1f524"
GENERATION_IMAGE_DIGEST = (
    "sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4"
)
GENERATION_IMAGE_BUILD_COMMIT = "9cde1d95ffda36698a0ddf558a9358f3337dd711"
V1_GATE_ROOT = "artifacts/phase1-0d-semantic-review-gate/20260803T031343Z"

RUBRIC_SHA256 = "91f687087fbd56cb07369da7a4c28beddb49d822f2d6fa1832cb3849a26f60e3"
ADDENDUM_SHA256 = (
    "20e5f30455f90a95c07e05e080e51443511c957e09d4ce97a42bd118bd9268e4"
)
FIXTURE_BANK_SHA256 = (
    "41adb246ec36d5ac7b16f5144c466351b93abe8b3f56dc811e58a789b197e75f"
)

#: The v2 surface only.  The frozen science and the v1 review surface are
#: covered by their own records, which this image also verifies during the
#: build, so the three bundles stay disjoint.
BUNDLE_GLOBS: tuple[str, ...] = (
    ".dockerignore",
    DOCKERFILE,
    "scripts/run_phase1_0d_semantic_review_v2.py",
    "scripts/phase1_0d_review_v2_build_provenance.py",
    "scripts/phase1_0d_rv2_protected_bytes.py",
    "docs/phase1_0d_rv2_protected_bytes.json",
    "docs/phase1_0d_protocol_snapshot.json",
    "docs/phase1_0d_semantic_review_addendum_v2.json",
    "docs/phase1_0d_semantic_review_rubric_v2.md",
    "docs/decisions/phase1_0d_semantic_review_v1_specification_correction.md",
    "src/jspace_observation/semantic_review_v2/*.py",
    AUTHORITY_PROMPT,
)

#: Paths that must not exist inside the image.  Target output is not merely
#: unused here; it is absent, so "the smoke stage cannot see the experiment" is
#: a property of the filesystem rather than of the control flow.
FORBIDDEN_TARGET_GLOBS: tuple[str, ...] = (
    "artifacts/phase1-0d-confirmation/**/*",
    "artifacts/phase1-0d-semantic-review-v2/**/*",
    "runtime/**/02_records.jsonl",
    "runtime/**/03_review_form.jsonl",
    "runtime/**/04_metrics.json",
    "runtime/**/05_decision.json",
    "runtime/**/all_judgments.json",
)

CLAIM_BOUNDARY = (
    "build provenance only; establishes which bytes are in the v2 review image "
    "and nothing about reviewer accuracy, instrument validity, model behaviour, "
    "hidden reasoning, or a 'J-space'"
)

_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")

REPO_ROOT = Path(__file__).resolve().parent.parent


class ReviewV2ProvenanceError(RuntimeError):
    """Raised when a v2 build-provenance obligation cannot be met."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve_bundle_files(project_root: Path) -> list[Path]:
    resolved: set[Path] = set()
    for pattern in BUNDLE_GLOBS:
        matches = sorted(project_root.glob(pattern))
        if not matches:
            raise ReviewV2ProvenanceError(f"bundle pattern matched no file: {pattern}")
        for match in matches:
            if not match.is_file():
                raise ReviewV2ProvenanceError(
                    f"bundle pattern matched a non-file: {match}"
                )
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
        digest.update(
            f"{entry['path']}:{entry['sha256']}:{entry['bytes']}".encode("utf-8")
        )
    return files, digest.hexdigest()


def load_instrument(project_root: Path) -> dict[str, Any]:
    """Read the v2 instrument through its own loader, so validation runs too."""

    sys.path.insert(0, str(project_root / "src"))
    from jspace_observation.semantic_review_v2 import addendum_v2  # noqa: PLC0415

    book = addendum_v2.load_addendum_v2(project_root)
    document = book.document
    bank_sha = addendum_v2.fixture_bank_sha256(book.smoke_fixtures)
    return {
        "addendum_sha256": book.sha256,
        "rubric_sha256": book.rubric_sha256,
        "fixture_bank_sha256": bank_sha,
        "fixture_count": len(book.smoke_fixtures),
        "registered_calls": addendum_v2.REQUIRED_CALLS,
        "base_protocol_sha256": str(document["base_protocol_sha256"]),
        "task_ids_sha256": str(document["task_ids_sha256"]),
        "generation_image_digest": str(document["generation_image_digest"]),
        "generation_image_build_commit": str(document["generation_image_build_commit"]),
        "reviewer_ids": {
            role: book.roles[role].reviewer_id
            for role in ("primary", "secondary", "third")
        },
        "request_profile_sha256": {
            role: book.roles[role].request_profile_sha256()
            for role in ("primary", "secondary", "third")
        },
        "historical_parents": dict(document["historical_parents"]),
    }


def _frozen_expectations() -> dict[str, str]:
    return {
        "addendum_sha256": ADDENDUM_SHA256,
        "rubric_sha256": RUBRIC_SHA256,
        "fixture_bank_sha256": FIXTURE_BANK_SHA256,
        "base_protocol_sha256": PROTOCOL_SHA256,
        "task_ids_sha256": TASK_IDS_SHA256,
        "generation_image_digest": GENERATION_IMAGE_DIGEST,
        "generation_image_build_commit": GENERATION_IMAGE_BUILD_COMMIT,
    }


def verify_manifest_tree(root: Path, manifest_path: Path) -> dict[str, Any]:
    """Verify every payload named by one immutable artifact manifest."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("files")
    if (
        not isinstance(entries, list)
        or manifest.get("file_count") != len(entries)
        or manifest.get("manifest_written_last") is not True
    ):
        raise ReviewV2ProvenanceError(
            f"{manifest_path} is not a complete manifest-last artifact"
        )
    names: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise ReviewV2ProvenanceError(
                f"{manifest_path} contains a malformed file entry"
            )
        name = str(entry["name"])
        if name in names or "/" in name or "\\" in name:
            raise ReviewV2ProvenanceError(
                f"{manifest_path} contains duplicate or non-local name {name!r}"
            )
        names.append(name)
        candidate = root / name
        if not candidate.is_file():
            raise ReviewV2ProvenanceError(
                f"{manifest_path} names missing historical evidence {candidate}"
            )
        normalised = candidate.read_bytes().replace(b"\r\n", b"\n")
        actual_hash = sha256_bytes(normalised)
        if actual_hash != entry.get("sha256") or len(normalised) != entry.get("bytes"):
            raise ReviewV2ProvenanceError(
                f"historical evidence {candidate} does not match its manifest"
            )
    actual_names = {
        path.name
        for path in root.iterdir()
        if path.is_file() and path.name != manifest_path.name
    }
    if actual_names != set(names):
        raise ReviewV2ProvenanceError(
            f"historical evidence tree has unexpected or missing files: "
            f"manifest={sorted(names)} actual={sorted(actual_names)}"
        )
    return {"file_count": len(names), "files": sorted(names)}


def verify_instrument(project_root: Path, provenance: Path | None) -> dict[str, Any]:
    """Section 8's semantic obligations, checked against frozen constants.

    Deliberately independent of the record file: the constants above are inside
    this tool, which is inside its own bundle, so a build cannot satisfy this
    check by editing the record it is being checked against.
    """

    observed = load_instrument(project_root)
    for key, expected in _frozen_expectations().items():
        if observed[key] != expected:
            raise ReviewV2ProvenanceError(
                f"{key} in the image is {observed[key]}, frozen value is {expected}"
            )

    authority = project_root / AUTHORITY_PROMPT
    authority_sha = sha256_bytes(authority.read_bytes().replace(b"\r\n", b"\n"))
    if authority_sha != AUTHORITY_PROMPT_SHA256:
        raise ReviewV2ProvenanceError(
            f"the v2 authority prompt hashes to {authority_sha}, expected "
            f"{AUTHORITY_PROMPT_SHA256}"
        )

    parents = observed["historical_parents"]
    for path_key, hash_key in (
        ("v1_authority_prompt", "v1_authority_prompt_sha256"),
        ("v1_addendum", "v1_addendum_sha256"),
        ("v1_rubric", "v1_rubric_sha256"),
    ):
        candidate = project_root / str(parents[path_key])
        if not candidate.exists():
            raise ReviewV2ProvenanceError(
                f"the v1 historical parent is missing from the image: {candidate}"
            )
        actual = sha256_bytes(candidate.read_bytes().replace(b"\r\n", b"\n"))
        if actual != parents[hash_key]:
            raise ReviewV2ProvenanceError(
                f"{parents[path_key]} hashes to {actual}, the v2 addendum names "
                f"{parents[hash_key]} as its historical parent"
            )

    v1_provenance_path = project_root / str(
        parents["v1_review_build_provenance"]
    )
    if not v1_provenance_path.exists():
        raise ReviewV2ProvenanceError(
            f"the v1 review provenance is missing: {v1_provenance_path}"
        )
    v1_provenance = json.loads(v1_provenance_path.read_text(encoding="utf-8"))
    if v1_provenance.get("bundle_sha256") != parents["v1_review_bundle_sha256"]:
        raise ReviewV2ProvenanceError(
            "the v1 review bundle hash no longer matches the v2 historical parent"
        )

    gate_root = project_root / str(parents["v1_gate_artifact_root"])
    gate_receipt_path = gate_root / "00_gate_receipt.json"
    gate_manifest_path = gate_root / "artifact_manifest.json"
    for candidate in (gate_receipt_path, gate_manifest_path):
        if not candidate.exists():
            raise ReviewV2ProvenanceError(
                f"the v1 terminal gate parent is missing: {candidate}"
            )
    gate_receipt_sha = sha256_bytes(
        gate_receipt_path.read_bytes().replace(b"\r\n", b"\n")
    )
    gate_manifest_sha = sha256_bytes(
        gate_manifest_path.read_bytes().replace(b"\r\n", b"\n")
    )
    if gate_receipt_sha != parents["v1_gate_receipt_sha256"]:
        raise ReviewV2ProvenanceError(
            f"the v1 gate receipt hashes to {gate_receipt_sha}, historical parent "
            f"is {parents['v1_gate_receipt_sha256']}"
        )
    if gate_manifest_sha != parents["v1_gate_manifest_sha256"]:
        raise ReviewV2ProvenanceError(
            f"the v1 gate manifest hashes to {gate_manifest_sha}, historical parent "
            f"is {parents['v1_gate_manifest_sha256']}"
        )
    gate_tree = verify_manifest_tree(gate_root, gate_manifest_path)
    if gate_tree["file_count"] != 3:
        raise ReviewV2ProvenanceError(
            "the frozen v1 gate must contain its receipt and two transcripts"
        )
    gate_receipt = json.loads(gate_receipt_path.read_text(encoding="utf-8"))
    if (
        gate_receipt["qualification"]["in_container_receipt_sha256"]
        != parents["v1_qualification_receipt_sha256"]
    ):
        raise ReviewV2ProvenanceError(
            "the v1 qualification receipt hash moved inside the terminal receipt"
        )
    if (
        gate_receipt["smoke"]["in_container_receipt_sha256"]
        != parents["v1_smoke_receipt_sha256"]
    ):
        raise ReviewV2ProvenanceError(
            "the v1 smoke receipt hash moved inside the terminal receipt"
        )
    if gate_receipt["review_image"]["digest"] != parents["v1_review_image_digest"]:
        raise ReviewV2ProvenanceError(
            "the v1 review image digest moved inside the terminal receipt"
        )

    if provenance is not None and provenance.exists():
        record = json.loads(provenance.read_text(encoding="utf-8"))
        for key in (
            "addendum_sha256",
            "rubric_sha256",
            "fixture_bank_sha256",
            "base_protocol_sha256",
            "task_ids_sha256",
            "generation_image_digest",
            "generation_image_build_commit",
            "reviewer_ids",
            "request_profile_sha256",
            "historical_parents",
        ):
            if record.get(key) != observed[key]:
                raise ReviewV2ProvenanceError(
                    f"{key} in the image is {observed[key]}, record says "
                    f"{record.get(key)}"
                )
    return observed


def find_target_output(project_root: Path) -> list[str]:
    """Return any baked path that would let the gate see target output."""

    found: set[str] = set()
    for pattern in FORBIDDEN_TARGET_GLOBS:
        for match in project_root.glob(pattern):
            if not match.is_file():
                continue
            found.add(match.relative_to(project_root).as_posix())
    return sorted(found)


def verify_no_target_output(project_root: Path) -> dict[str, Any]:
    found = find_target_output(project_root)
    if found:
        raise ReviewV2ProvenanceError(
            f"target output is baked into the v2 review image: {found[:8]}"
        )
    return {"forbidden_patterns": len(FORBIDDEN_TARGET_GLOBS), "found": 0}


def build_record(project_root: Path, code_commit: str) -> dict[str, Any]:
    if not _COMMIT_PATTERN.match(code_commit):
        raise ReviewV2ProvenanceError(
            f"code commit must be a full 40-character sha: {code_commit!r}"
        )
    files, digest = hash_bundle(project_root)
    observed = verify_instrument(project_root, None)
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "artifact": "phase1_0d_review_v2_build_provenance",
        "phase": PHASE,
        "track": TRACK,
        "round": "v2",
        "authority_prompt": AUTHORITY_PROMPT,
        "authority_prompt_sha256": AUTHORITY_PROMPT_SHA256,
        "base_image": BASE_IMAGE,
        "base_image_digest": BASE_IMAGE_DIGEST,
        "bundle_hash_domain": BUNDLE_HASH_DOMAIN,
        "bundle_sha256": digest,
        "code_commit": code_commit,
        "dockerfile": DOCKERFILE,
        "file_count": len(files),
        "files": files,
        "requirements": REQUIREMENTS,
        "requirements_note": (
            "the v2 review job is standard-library only; the pinned calibration "
            "requirements are installed and verified by the frozen generation "
            "provenance tool so this image's environment is the same "
            "already-pinned environment rather than a third unpinned one"
        ),
        "disjoint_from": [
            "phase1_0d_build_provenance.json",
            "phase1_0d_review_build_provenance.json",
        ],
        "no_target_output_baked": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    record.update(observed)
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
            path
            for path in set(actual) & set(recorded)
            if actual[path] != recorded[path]
        )
        raise ReviewV2ProvenanceError(
            f"baked v2 review bytes hash to {digest}, record says "
            f"{record.get('bundle_sha256')}; added={added} removed={removed} "
            f"changed={changed}"
        )
    return {"bundle_sha256": digest, "file_count": len(files)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser("emit", help="write the v2 review build-provenance record")
    emit.add_argument("--code-commit", required=True)
    emit.add_argument("--output", default="")

    context = sub.add_parser("verify-image-context", help="recompute the baked bundle")
    context.add_argument("--provenance", default="")

    instrument = sub.add_parser(
        "verify-instrument", help="recheck the frozen v2 instrument inside the image"
    )
    instrument.add_argument("--provenance", default="")

    sub.add_parser(
        "verify-no-target-output", help="refuse any baked Phase 1.0D target output"
    )

    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()

    if args.command == "emit":
        record = build_record(root, args.code_commit)
        text = canonical_json(record)
        if args.output:
            Path(args.output).write_bytes(text.encode("utf-8"))
        sys.stdout.write(text)
        return 0

    if args.command == "verify-no-target-output":
        result = verify_no_target_output(root)
        print(f"FORBIDDEN_PATTERNS={result['forbidden_patterns']}")
        print("NO_TARGET_OUTPUT_BAKED=1")
        return 0

    provenance = Path(args.provenance) if args.provenance else root / RECORD_PATH
    if args.command == "verify-image-context":
        result = verify_image_context(root, provenance)
        print(f"REVIEW_V2_BUNDLE_SHA256={result['bundle_sha256']}")
        print(f"REVIEW_V2_BUNDLE_FILES={result['file_count']}")
        print("REVIEW_V2_IMAGE_CONTEXT_OK=1")
        return 0

    observed = verify_instrument(root, provenance)
    print(f"V2_ADDENDUM_SHA256={observed['addendum_sha256']}")
    print(f"V2_RUBRIC_SHA256={observed['rubric_sha256']}")
    print(f"V2_FIXTURE_BANK_SHA256={observed['fixture_bank_sha256']}")
    print(f"BASE_PROTOCOL_SHA256={observed['base_protocol_sha256']}")
    print(f"TASK_IDS_SHA256={observed['task_ids_sha256']}")
    print(f"GENERATION_IMAGE_DIGEST={observed['generation_image_digest']}")
    for role, reviewer in sorted(observed["reviewer_ids"].items()):
        print(f"REVIEWER {role}={reviewer}")
    print("REVIEW_V2_INSTRUMENT_OK=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
