#!/usr/bin/env python3
"""Stage the parser-v3-v1 seal payload into an out-of-tree build context.

The seal has to upload private holdout material that is gitignored and exists
only on the curator's disk, so the container image must carry it.  The repo's
``.dockerignore`` excludes ``evaluator_sets/``, ``artifacts/`` and every locked
filename, which is correct and must not be weakened.  This script therefore
builds a **separate** context directory outside the repository, verifies every
byte against the Track D digests, and writes the Dockerfile next to it.

It performs no Azure call, no git call and no network access.  It refuses to
write inside the repository or inside any Git worktree.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from parser_v3_seal_job import (  # noqa: E402
    SEAL_OBJECTS,
    canonical_json_bytes,
    sha256_bytes,
)

BASE_IMAGE = (
    "python:3.11.14-slim-bookworm@sha256:"
    "65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d"
)
REQUIREMENTS_SOURCE = "requirements-parser-v2-eval.txt"
REQUIREMENTS_NAME = "requirements-parser-v3-seal.txt"
CODE_SOURCES = (
    "scripts/parser_v3_seal_job.py",
    "scripts/build_parser_v3_validation_set.py",
)

DOCKERFILE = """\
# Temporary, single-use image for the parser-v3-v1 seal.
# It carries private holdout material.  Delete the manifest from ACR after the
# sole execution and reset the job to the immutable base image with /bin/true.
FROM {base_image}

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONHASHSEED=0 \\
    HOME=/nonexistent \\
    TMPDIR=/runtime/work \\
    LANG=C.UTF-8 \\
    LC_ALL=C.UTF-8 \\
    PATH=/usr/local/bin:/usr/bin:/bin

WORKDIR /payload

RUN ! grep -Eq '^[^:]+:[^:]*:10002:' /etc/group \\
    && ! grep -Eq '^[^:]+:[^:]*:10002:' /etc/passwd \\
    && printf '%s\\n' 'seal:x:10002:' >> /etc/group \\
    && printf '%s\\n' 'seal:x:10002:10002::/nonexistent:/bin/false' >> /etc/passwd \\
    && install -d -o seal -g seal -m 0700 /runtime /runtime/work

COPY {requirements_name} /tmp/{requirements_name}
RUN /usr/local/bin/python3.11 -I -m pip install --no-cache-dir \\
    --only-binary=:all: --require-hashes -r /tmp/{requirements_name} \\
    && rm -f /tmp/{requirements_name}

COPY payload/ /payload/

RUN /usr/local/bin/python3.11 -I -m py_compile \\
       /payload/parser_v3_seal_job.py \\
       /payload/build_parser_v3_validation_set.py \\
    && find /payload -type d -name __pycache__ -prune -exec rm -rf {{}} + \\
    && chown -R 0:0 /payload \\
    && chmod -R a-w /payload

USER seal

CMD ["/usr/local/bin/python3.11", "-I", "/payload/parser_v3_seal_job.py", \\
     "--mode", "preflight", "--payload-dir", "/payload"]
"""


class StagingError(RuntimeError):
    """The staging target or a payload byte is not acceptable."""


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_external_context(target: str | Path) -> Path:
    """Reject repository, Git-worktree and symlinked staging roots."""
    raw = Path(target)
    lexical = raw.absolute()
    resolved = raw.resolve(strict=False)
    repo = PROJECT_ROOT.resolve()
    for candidate in (lexical, resolved):
        if _is_within(candidate, repo) or candidate == repo:
            raise StagingError(
                "the staging context must live outside the repository, because the "
                "payload carries gitignored holdout material"
            )
    if resolved.exists():
        raise StagingError("the staging context must be a new directory")
    for parent in [resolved, *resolved.parents]:
        if (parent / ".git").exists():
            raise StagingError("the staging context must not sit inside a Git worktree")
        if parent == parent.parent:
            break
    return resolved


def payload_plan() -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for item in SEAL_OBJECTS:
        plan.append(
            {
                "role": "seal_object",
                "order": int(item["order"]),
                "source": str(item["source"]),
                "name": str(item["name"]),
                "sha256": str(item["sha256"]),
                "bytes": int(item["bytes"]),
            }
        )
    for source in CODE_SOURCES:
        plan.append(
            {
                "role": "code",
                "order": None,
                "source": source,
                "name": Path(source).name,
                "sha256": None,
                "bytes": None,
            }
        )
    return plan


def stage(target: str | Path, *, repo_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    context = validate_external_context(target)
    payload_dir = context / "payload"
    payload_dir.mkdir(parents=True)
    staged: list[dict[str, Any]] = []
    for entry in payload_plan():
        source = Path(repo_root) / entry["source"]
        if not source.is_file():
            raise StagingError(f"payload source is missing: {entry['source']}")
        data = source.read_bytes()
        digest = sha256_bytes(data)
        if entry["sha256"] is not None and digest != entry["sha256"]:
            raise StagingError(f"payload digest mismatch: {entry['source']}")
        if entry["bytes"] is not None and len(data) != entry["bytes"]:
            raise StagingError(f"payload byte count mismatch: {entry['source']}")
        destination = payload_dir / entry["name"]
        if destination.exists():
            raise StagingError(f"payload name collision: {entry['name']}")
        destination.write_bytes(data)
        if destination.read_bytes() != data:
            raise StagingError(f"payload write-back mismatch: {entry['name']}")
        staged.append(
            {
                "role": entry["role"],
                "order": entry["order"],
                "source": entry["source"],
                "payload_name": entry["name"],
                "sha256": digest,
                "bytes": len(data),
            }
        )
    requirements = Path(repo_root) / REQUIREMENTS_SOURCE
    if not requirements.is_file():
        raise StagingError("the hash-pinned requirements file is missing")
    shutil.copyfile(requirements, context / REQUIREMENTS_NAME)
    dockerfile = DOCKERFILE.format(
        base_image=BASE_IMAGE, requirements_name=REQUIREMENTS_NAME
    )
    (context / "Dockerfile").write_bytes(dockerfile.encode("utf-8"))
    manifest: dict[str, Any] = {
        "schema_version": "phase1-parser-v3-seal-payload/v1",
        "base_image": BASE_IMAGE,
        "context": str(context),
        "requirements": REQUIREMENTS_NAME,
        "requirements_sha256": sha256_bytes(requirements.read_bytes()),
        "dockerfile_sha256": sha256_bytes(dockerfile.encode("utf-8")),
        "files": staged,
        "seal_object_count": sum(1 for row in staged if row["role"] == "seal_object"),
        "content_disclosure": (
            "this context carries private holdout inputs and labels; it must never "
            "be committed, and the built image must be deleted after the sole run"
        ),
    }
    (context / "payload_manifest.json").write_bytes(canonical_json_bytes(manifest))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="new directory outside the repository")
    args = parser.parse_args(argv)
    try:
        manifest = stage(args.target)
    except StagingError as error:
        print(f"[ABORT] {error}")
        return 3
    print(f"staged {manifest['seal_object_count']} seal objects at {manifest['context']}")
    print(f"dockerfile sha256 {manifest['dockerfile_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
