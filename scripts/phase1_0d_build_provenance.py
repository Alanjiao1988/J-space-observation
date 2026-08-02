#!/usr/bin/env python
"""Build provenance for the Phase 1.0D headroom-confirmation image.

Why this exists as a separate tool rather than a reuse of
``calibration_build_provenance.py``: that generator is bound to the Phase 1.0C
file list, image repository and artifact namespace, all of which the authority
forbids overwriting.  Editing it to serve two phases would put a frozen record
and a live one behind the same code path.

What it establishes, stated narrowly:

* the image was built from a declared set of source files whose bytes hash to a
  recorded bundle digest, so no file can be added, removed or edited without
  the build failing;
* the installed runtime matches every pin in the requirements lock, the base
  interpreter and the base torch build;
* the image contains the Phase 1.0D protocol at its frozen ``protocol_sha256``.

What it does not establish: nothing about the model's behaviour, nothing about
whether the run that uses the image is scientifically valid, and nothing about
the base image beyond the digest it was pulled by.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Mapping, Sequence

SCHEMA_VERSION = "phase1-0d-confirmation-build-provenance/v1"
BUNDLE_HASH_DOMAIN = "jspace-phase1-0d/build-bundle/v1"
PROVENANCE_FILENAME = "phase1_0d_build_provenance.json"

IMAGE_REPOSITORY = "j-space-observation-phase1-0d"
DOCKERFILE = "Dockerfile.phase1-0d"
REQUIREMENTS = "requirements-calibration.txt"

BASE_IMAGE = "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"
BASE_IMAGE_DIGEST = (
    "sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126"
)
BASE_IMAGE_PLATFORM = "linux/amd64"

EXPECTED_PYTHON_VERSION = "3.11"
EXPECTED_TORCH_VERSION = "2.4.1"
EXPECTED_TRANSFORMERS_VERSION = "4.46.3"

MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
MODEL_REVISION = "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
TOKENIZER_REVISION = MODEL_REVISION

PROTOCOL_SHA256 = "25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8"

# The whole package is baked, not a hand-maintained subset.  A subset is the
# more fragile choice: it drifts silently the moment an import is added, and it
# invites the "just add one more file" edit that no reviewer can see.  The
# check is over these globs, so it detects any change to, addition of, or
# removal of a file *matching* them; a file of some other kind dropped into the
# image is outside what this record speaks about.
BUNDLE_GLOBS: tuple[str, ...] = (
    DOCKERFILE,
    REQUIREMENTS,
    "scripts/run_phase1_0d_confirmation.py",
    "scripts/phase1_0d_build_provenance.py",
    "src/jspace_observation/*.py",
    "data/phase1_task_headroom_candidates.jsonl",
    "artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/02_records.jsonl",
    "docs/prompts/phase_science_restart_after_parser_closure_prompt.md",
)

CLAIM_BOUNDARY = (
    "build provenance only; establishes what bytes are in the image and "
    "nothing about model behaviour, hidden reasoning, or a 'J-space'"
)

_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class ProvenanceError(RuntimeError):
    """Raised when a build-provenance obligation cannot be met."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve_bundle_files(project_root: Path) -> list[Path]:
    """Expand the declared globs into a sorted, deduplicated file list."""

    resolved: set[Path] = set()
    for pattern in BUNDLE_GLOBS:
        matches = sorted(project_root.glob(pattern))
        if not matches:
            raise ProvenanceError(f"bundle pattern matched no file: {pattern}")
        for match in matches:
            if not match.is_file():
                raise ProvenanceError(f"bundle pattern matched a non-file: {match}")
            resolved.add(match)
    return sorted(resolved, key=lambda path: path.relative_to(project_root).as_posix())


def hash_bundle(project_root: Path) -> tuple[list[dict[str, object]], str]:
    """Hash every declared file, then hash the list of hashes.

    Line endings are normalised to LF before hashing.  The repository is
    developed on Windows and stores LF, so hashing raw bytes would make the
    same commit produce two different bundle digests depending on the checkout.
    """

    files: list[dict[str, object]] = []
    for path in resolve_bundle_files(project_root):
        raw = path.read_bytes()
        normalised = raw.replace(b"\r\n", b"\n")
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
        digest.update(str(entry["path"]).encode("utf-8"))
        digest.update(b" ")
        digest.update(str(entry["sha256"]).encode("utf-8"))
    return files, digest.hexdigest()


def build_document(project_root: Path, code_commit: str) -> dict[str, object]:
    if not _COMMIT_PATTERN.fullmatch(code_commit):
        raise ProvenanceError("code_commit must be a full 40-character commit")
    files, bundle_sha256 = hash_bundle(project_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": "1.0D",
        "track": "B",
        "image_repository": IMAGE_REPOSITORY,
        "dockerfile": DOCKERFILE,
        "requirements": REQUIREMENTS,
        "base_image": BASE_IMAGE,
        "base_image_digest": BASE_IMAGE_DIGEST,
        "base_image_platform": BASE_IMAGE_PLATFORM,
        "expected_python_version": EXPECTED_PYTHON_VERSION,
        "expected_torch_version": EXPECTED_TORCH_VERSION,
        "expected_transformers_version": EXPECTED_TRANSFORMERS_VERSION,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": TOKENIZER_REVISION,
        "protocol_sha256": PROTOCOL_SHA256,
        "code_commit": code_commit,
        "bundle_hash_domain": BUNDLE_HASH_DOMAIN,
        "bundle_sha256": bundle_sha256,
        "file_count": len(files),
        "files": files,
        "claim_boundary": CLAIM_BOUNDARY,
        "not_established": [
            "no statement about model behaviour, accuracy, or hidden reasoning",
            "no statement that a run using this image is scientifically valid",
            "no statement about the base image beyond the digest it is pulled by",
        ],
    }


def canonical(document: Mapping[str, object]) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def load_document(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ProvenanceError(
            f"provenance schema is {document.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION!r}"
        )
    for field in ("bundle_sha256", "protocol_sha256"):
        value = document.get(field)
        if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
            raise ProvenanceError(f"{field} is not a SHA-256 digest")
    if document.get("image_repository") != IMAGE_REPOSITORY:
        raise ProvenanceError("provenance names a different image repository")
    if document.get("protocol_sha256") != PROTOCOL_SHA256:
        raise ProvenanceError(
            "provenance carries a protocol hash this tool does not recognise; "
            "the protocol was refrozen without refreshing the build record"
        )
    return document


def _installed_versions() -> dict[str, str]:
    from importlib import metadata  # noqa: PLC0415 - import only when verifying

    versions: dict[str, str] = {}
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"]
        if name:
            versions[name.lower().replace("_", "-")] = distribution.version
    return versions


def parse_pins(requirements: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in requirements.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if not stripped:
            continue
        if "==" not in stripped:
            raise ProvenanceError(f"requirement is not pinned exactly: {line!r}")
        name, version = stripped.split("==", 1)
        pins[name.strip().lower().replace("_", "-")] = version.strip()
    if not pins:
        raise ProvenanceError("requirements lock declares no pin")
    return pins


def verify_runtime(requirements: Path) -> list[str]:
    """Fail the build if the installed runtime drifts from the lock."""

    failures: list[str] = []
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual_python != EXPECTED_PYTHON_VERSION:
        failures.append(
            f"python is {actual_python}, expected {EXPECTED_PYTHON_VERSION}"
        )

    versions = _installed_versions()
    torch_version = versions.get("torch", "absent").split("+", 1)[0]
    if torch_version != EXPECTED_TORCH_VERSION:
        failures.append(f"torch is {torch_version}, expected {EXPECTED_TORCH_VERSION}")
    transformers_version = versions.get("transformers", "absent")
    if transformers_version != EXPECTED_TRANSFORMERS_VERSION:
        failures.append(
            f"transformers is {transformers_version}, "
            f"expected {EXPECTED_TRANSFORMERS_VERSION}"
        )

    for name, pinned in sorted(parse_pins(requirements).items()):
        installed = versions.get(name)
        if installed is None:
            failures.append(f"{name} is pinned to {pinned} but is not installed")
        elif installed.split("+", 1)[0] != pinned:
            failures.append(f"{name} is {installed}, pinned to {pinned}")
    return failures


def verify_image_context(project_root: Path, provenance: Path) -> list[str]:
    """Fail the build if the baked source differs from the recorded bundle."""

    document = load_document(provenance)
    recorded = {
        str(entry["path"]): str(entry["sha256"])
        for entry in document.get("files", [])  # type: ignore[union-attr]
    }
    files, bundle_sha256 = hash_bundle(project_root)
    present = {str(entry["path"]): str(entry["sha256"]) for entry in files}

    failures: list[str] = []
    for path in sorted(set(recorded) - set(present)):
        failures.append(f"recorded file is absent from the image: {path}")
    for path in sorted(set(present) - set(recorded)):
        failures.append(f"image carries an unrecorded file: {path}")
    for path in sorted(set(recorded) & set(present)):
        if recorded[path] != present[path]:
            failures.append(f"content differs from the recorded bytes: {path}")
    if bundle_sha256 != document["bundle_sha256"]:
        failures.append(
            f"bundle digest is {bundle_sha256}, recorded {document['bundle_sha256']}"
        )
    return failures


def verify_protocol(project_root: Path) -> list[str]:
    """Fail the build if the image does not reproduce the frozen protocol.

    The frozen ``protocol_sha256`` is the hash of the snapshot *including* the
    derived selection and the strict-budget check.  ``protocol_snapshot()``
    called bare produces a different, smaller document and therefore a different
    hash — which is a trap worth naming: a recorded hash that only reproduces
    under undocumented arguments is indistinguishable from a drifted one.  This
    reproduces the full document, so a passing build proves the image carries
    the frozen rules *and* the frozen 300-item selection.
    """

    sys.path.insert(0, str(project_root / "src"))
    from jspace_observation.headroom_calibration import (  # noqa: PLC0415
        load_task_bank,
    )
    from jspace_observation.phase1_0c_defect_audit import (  # noqa: PLC0415
        load_phase_1_0c_records,
    )
    from jspace_observation.phase1_0d_confirmation import (  # noqa: PLC0415
        DEFAULT_BANK_PATH,
        assert_strict_budget_fits_every_answer,
        phase_1_0c_item_ids,
        protocol_snapshot,
        select_confirmation_items,
        selection_summary,
    )

    bank = load_task_bank(project_root / DEFAULT_BANK_PATH)
    used = phase_1_0c_item_ids(load_phase_1_0c_records())
    selected = select_confirmation_items(bank, used)
    snapshot = protocol_snapshot(
        selection=selection_summary(selected, used),
        strict_budget_check=assert_strict_budget_fits_every_answer(selected),
    )
    actual = str(snapshot["protocol_sha256"])
    if actual != PROTOCOL_SHA256:
        return [f"protocol_sha256 is {actual}, frozen at {PROTOCOL_SHA256}"]
    return []


def _report(failures: Sequence[str], success: str) -> int:
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print(f"[OK] {success}")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    emit = subparsers.add_parser("emit", help="print the provenance document")
    emit.add_argument("--code-commit", required=True)

    runtime = subparsers.add_parser("verify-runtime", help="check installed pins")
    runtime.add_argument("--requirements", type=Path, required=True)

    context = subparsers.add_parser("verify-image-context", help="check baked bytes")
    context.add_argument("--provenance", type=Path, required=True)

    subparsers.add_parser("verify-protocol", help="check the frozen protocol hash")

    arguments = parser.parse_args(list(argv) if argv is not None else None)
    root = arguments.project_root

    try:
        if arguments.command == "emit":
            print(canonical(build_document(root, arguments.code_commit)), end="")
            return 0
        if arguments.command == "verify-runtime":
            return _report(
                verify_runtime(arguments.requirements),
                "installed runtime matches every pin",
            )
        if arguments.command == "verify-image-context":
            return _report(
                verify_image_context(root, arguments.provenance),
                "image context matches the recorded bundle",
            )
        return _report(verify_protocol(root), "image carries the frozen protocol")
    except ProvenanceError as error:
        print(f"[FAIL] {error}")
        return 1


if __name__ == "__main__":  # pragma: no cover - build-time entrypoint
    sys.exit(main())
