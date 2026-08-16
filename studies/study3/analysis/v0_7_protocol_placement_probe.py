#!/usr/bin/env python3
"""Determine which Study 3 protocol files can still be amended.

Authority:
``studies/study3/prompts/study3_v0_7_consolidated_amendment_authority.md``
sections 3, 5 and 8.

Section 5 of the v0.7 authority requires updating three active normative
protocol files. Section 3 forbids altering historical P0 manifests. Section 8
forbids publishing a passing state with a waived decision-bearing test.

Those three requirements are not jointly satisfiable for every file, and this
probe establishes exactly which ones, mechanically, rather than by reading the
v0.6 amendment's prose account of the same constraint.

Method, per protocol file:

1. record its committed SHA-256;
2. search every immutable P0/artifact byte for that digest, so a binding is
   found rather than assumed;
3. perturb the file by one benign trailing space, run the committed
   regeneration checks, and record their exit codes;
4. restore the original bytes and verify the restoration by SHA-256.

The perturbation is performed in the working tree because both committed
checks resolve their inputs from module-level absolute paths, so a temporary
copy would not be the file they read. The probe therefore refuses to run on a
dirty worktree, restores in a ``finally`` block, and fails loudly if the
restored bytes are not byte-identical.

CPU-only and deterministic. No tokenizer, checkpoint, model, GPU, network or
cloud operation. Writes nothing except its own report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent

SCHEMA_VERSION = "study3-v0-7-protocol-placement-probe"

PROTOCOL_FILES = {
    "protocol_json": "studies/study3/protocol/interface_calibration_protocol_draft.json",
    "protocol_md": "studies/study3/protocol/interface_calibration_protocol_draft.md",
    "protocol_schema": "studies/study3/protocol/interface_calibration_protocol.schema.json",
}

#: The committed regeneration checks that decide whether a historical P0
#: artifact still reproduces byte-exactly.
COMMITTED_CHECKS = (
    ("p0_freeze_corpus", "studies/study3/pilot/p0/p0_freeze_corpus.py"),
    ("p0_protocol", "studies/study3/pilot/p0/p0_protocol.py"),
)

#: Roots whose bytes the authority treats as historically immutable.
IMMUTABLE_ROOTS = (
    "studies/study3/pilot/p0/",
    "studies/study3/pilot/p0_r1/",
    "studies/study3/pilot/p0_r2/",
    "artifacts/",
)


class ProbeDefect(Exception):
    """The probe could not run honestly."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(document) -> bytes:
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _git(root, args):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        check=False)
    if completed.returncode:
        raise ProbeDefect("git %s refused: %s"
                          % (" ".join(args), completed.stderr.strip()))
    return completed.stdout


def require_clean_worktree(root) -> None:
    status = _git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if status.strip():
        raise ProbeDefect(
            "the worktree is dirty; this probe perturbs tracked files and will "
            "not run where it cannot prove it restored them")


def run_committed_checks(root) -> dict:
    outcomes = {}
    for name, relative in COMMITTED_CHECKS:
        completed = subprocess.run(  # noqa: S603 - fixed executable
            [sys.executable, str(Path(root) / relative), "--check"],
            capture_output=True, text=True, check=False, cwd=str(root))
        outcomes[name] = {
            "exit_code": completed.returncode,
            "reproduces": completed.returncode == 0,
            "last_line": (completed.stdout or completed.stderr).strip()
            .splitlines()[-1] if (completed.stdout or completed.stderr).strip()
            else "",
        }
    return outcomes


def immutable_references(root, digest, relative) -> list:
    """Every immutable committed file that embeds this digest or path."""
    found = []
    for name in _git(root, ["ls-files"]).split("\n"):
        name = name.strip()
        if not name or not name.startswith(IMMUTABLE_ROOTS):
            continue
        try:
            payload = (Path(root) / name).read_bytes()
        except OSError:
            continue
        text = payload.decode("utf-8", "replace")
        if digest in text:
            found.append({"path": name, "binds": "sha256"})
        elif relative in text:
            found.append({"path": name, "binds": "path-only"})
    return found


def probe_file(root, label, relative, *, baseline) -> dict:
    target = Path(root) / relative
    original = target.read_bytes()
    digest = _sha256(original)

    perturbed_outcomes = None
    try:
        target.write_bytes(original[:-1] + b" \n")
        perturbed_outcomes = run_committed_checks(root)
    finally:
        target.write_bytes(original)
        restored = target.read_bytes()
        if _sha256(restored) != digest:
            raise ProbeDefect(
                "%s was not restored byte-exactly; refusing to continue"
                % relative)

    broken = sorted(name for name, outcome in perturbed_outcomes.items()
                    if not outcome["reproduces"]
                    and baseline[name]["reproduces"])
    return {
        "label": label,
        "path": relative,
        "bytes": len(original),
        "sha256": digest,
        "immutable_references": immutable_references(root, digest, relative),
        "checks_when_perturbed": perturbed_outcomes,
        "checks_broken_by_one_benign_byte": broken,
        "amendable": not broken,
        "restored_byte_exactly": True,
    }


def probe(root=None) -> dict:
    root = Path(root or REPO_ROOT).resolve()
    require_clean_worktree(root)
    head = _git(root, ["rev-parse", "HEAD"]).strip()

    baseline = run_committed_checks(root)
    if not all(outcome["reproduces"] for outcome in baseline.values()):
        raise ProbeDefect(
            "a committed regeneration check does not reproduce before any "
            "perturbation; the starting state is not intact")

    files = [probe_file(root, label, relative, baseline=baseline)
             for label, relative in sorted(PROTOCOL_FILES.items())]

    amendable = sorted(entry["path"] for entry in files if entry["amendable"])
    frozen = sorted(entry["path"] for entry in files if not entry["amendable"])

    require_clean_worktree(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "STUDY3-V0-7",
        "head": head,
        "baseline_checks": baseline,
        "files": files,
        "amendable_paths": amendable,
        "byte_frozen_paths": frozen,
        "all_three_amendable": not frozen,
        "worktree_restored_clean": True,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "prefills": 0,
        "generations": 0,
        "scored_rows": 0,
        "gpu_operations": 0,
        "cloud_operations": 0,
        "evidence_rows_added": 0,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    try:
        document = probe(args.root)
    except ProbeDefect as exc:
        print("STUDY3_V0_7_PLACEMENT_PROBE_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = canonical_bytes(document)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload)
    print(payload.decode("utf-8"), end="")
    for entry in document["files"]:
        print("STUDY3_V0_7_%s=%s"
              % ("AMENDABLE" if entry["amendable"] else "BYTE_FROZEN",
                 entry["path"]))
    print("STUDY3_V0_7_ALL_THREE_AMENDABLE=%d"
          % (1 if document["all_three_amendable"] else 0))
    print("STUDY3_V0_7_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
