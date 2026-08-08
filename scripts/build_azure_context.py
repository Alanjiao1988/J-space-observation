#!/usr/bin/env python
"""Materialize an Azure build/run context from committed git blobs.

A context assembled with ordinary file copies on Windows carries CRLF endings,
and a shell script with CRLF fails at ``set -euo pipefail`` inside a Linux
container.  Reading the blobs from the object database instead gives the exact
committed bytes regardless of the checkout's line-ending policy, which is also
what makes the ``cmp`` self-checks inside the tasks meaningful.

    python scripts/build_azure_context.py --commit <sha> --dest <dir> \
        --bundle repo.bundle \
        --file infra/azure/acr_tasks/study2_full_tests.sh:study2_full_tests.sh
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--bundle", default=None, help="write a git bundle of the commit")
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        metavar="REPO_PATH[:CONTEXT_NAME]",
        help="copy one committed blob into the context",
    )
    args = parser.parse_args()

    dest = Path(args.dest)
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"refusing to reuse a non-empty context: {dest}")
    dest.mkdir(parents=True, exist_ok=True)

    if args.bundle:
        subprocess.run(
            ["git", "bundle", "create", str(dest / args.bundle), args.commit],
            check=True,
            capture_output=True,
        )

    for spec in args.file:
        repo_path, _, name = spec.partition(":")
        name = name or Path(repo_path).name
        blob = subprocess.run(
            ["git", "cat-file", "blob", f"{args.commit}:{repo_path}"],
            check=True,
            capture_output=True,
        ).stdout
        if b"\r\n" in blob:
            raise SystemExit(f"committed blob has CRLF endings: {repo_path}")
        (dest / name).write_bytes(blob)
        print(f"{len(blob):>9}  {hashlib.sha256(blob).hexdigest()}  {name}")

    print(f"CONTEXT={dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
