#!/usr/bin/env python3
"""The corrected P0-R2 image manifest: v1's bindings plus the corrective bytes.

The v1 manifest binds 33 paths and is correct about them. It simply predates
the corrective closure, so it cannot bind the modules that closure adds: the v2
governance-chain validator, the v2 host preflight, the hard-kill recovery
canary, the attempt ledger and their entry point.

This module is additive by construction. It imports the v1 path tuples rather
than restating them, so the operational and scientific sets it carries are
provably v1's sets plus a named delta, and no v1 byte is edited to achieve it.
The delta is listed explicitly below and is reported in the manifest itself, so
an auditor can see exactly what the corrected image adds.

Everything about the science is unchanged: the same nine P0-R1 generation-3
scientific modules, copied byte-identically from the same commit and verified by
SHA-256 before they are imported.

Model-free: this module reads Git objects and hashes bytes. It constructs no
tokenizer, downloads no checkpoint, loads no weight, allocates no GPU and adds
no evidence row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_image_manifest_v1 as V1  # noqa: E402


REPO_ROOT = P0_R2_DIR.parent.parent.parent.parent

SCHEMA_VERSION = "study3-p0-r2-image-manifest-v2"
STAGE = "STUDY3-P0-R2"
MANIFEST_NAME = "p0_r2_image_manifest_v2.json"

IMAGE_ROOT = V1.IMAGE_ROOT
ENTRYPOINT_INSTALL_ROOT = V1.ENTRYPOINT_INSTALL_ROOT

#: Exactly what the corrective closure adds to the image, and why.
ADDED_OPERATIONAL_PATHS = (
    "studies/study3/pilot/p0_r2/p0_r2_closure_binding_v2.py",
    "studies/study3/pilot/p0_r2/p0_r2_host_preflight_v2.py",
    "studies/study3/pilot/p0_r2/p0_r2_hard_kill_canary_v2.py",
    "studies/study3/pilot/p0_r2/p0_r2_attempt_ledger_v2.py",
    "studies/study3/pilot/p0_r2/p0_r2_execution_lock_v2.py",
    "studies/study3/pilot/p0_r2/p0_r2_image_manifest_v2.py",
)

ADDED_ENTRYPOINT_PATHS = (
    "studies/study3/pilot/p0_r2/container/p0_r2_successor_v2.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_canary_v2.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_replay_v2.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_model_pilot_v2.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_hard_kill_canary_v2.sh",
)

OPERATIONAL_PATHS = tuple(V1.OPERATIONAL_PATHS) + ADDED_OPERATIONAL_PATHS
SCIENTIFIC_PATHS = tuple(V1.SCIENTIFIC_PATHS)
ENTRYPOINT_PATHS = tuple(V1.ENTRYPOINT_PATHS) + ADDED_ENTRYPOINT_PATHS


class ImageManifestDefect(Exception):
    """The image does not carry the bytes the manifest binds."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root)] + list(args), capture_output=True, text=True,
        check=False)
    if result.returncode != 0:
        raise ImageManifestDefect(
            "git %s failed: %s" % (" ".join(args), result.stderr.strip()))
    return result.stdout.strip()


def build(root=None, *, commit="HEAD") -> dict:
    """Bind every carried file to its bytes and its Git blob id."""
    root = Path(root or REPO_ROOT).resolve()
    resolved = _git(root, "rev-parse", commit + "^{commit}")
    tree = _git(root, "rev-parse", commit + "^{tree}")

    entries = []
    for kind, paths in (("operational", OPERATIONAL_PATHS),
                        ("scientific", SCIENTIFIC_PATHS),
                        ("entrypoint", ENTRYPOINT_PATHS)):
        for path in paths:
            payload = subprocess.run(  # noqa: S603 - fixed executable
                ["git", "-C", str(root), "show", "%s:%s" % (resolved, path)],
                capture_output=True, check=False).stdout
            if not payload:
                raise ImageManifestDefect(
                    "%s is absent at %s; the image cannot carry it"
                    % (path, resolved[:12]))
            entry = {
                "kind": kind,
                "path": path,
                "image_path": "%s/%s" % (IMAGE_ROOT, path),
                "bytes": len(payload),
                "sha256": _sha256(payload),
                "git_blob": _git(root, "rev-parse", "%s:%s" % (resolved, path)),
                "added_by_corrective_closure":
                    path in ADDED_OPERATIONAL_PATHS
                    or path in ADDED_ENTRYPOINT_PATHS,
            }
            if kind == "entrypoint":
                entry["install_name"] = path.rsplit("/", 1)[-1]
                entry["image_path"] = "%s/%s" % (ENTRYPOINT_INSTALL_ROOT,
                                                 entry["install_name"])
            entries.append(entry)

    entries.sort(key=lambda entry: entry["path"])
    canonical = json.dumps(entries, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "supersedes": V1.MANIFEST_NAME,
        "executable_commit": resolved,
        "executable_tree": tree,
        "image_root": IMAGE_ROOT,
        "entrypoint_install_root": ENTRYPOINT_INSTALL_ROOT,
        "operational_count": len(OPERATIONAL_PATHS),
        "scientific_count": len(SCIENTIFIC_PATHS),
        "entrypoint_count": len(ENTRYPOINT_PATHS),
        "entry_count": len(entries),
        "v1_entry_count": V1.build(root, commit=commit)["entry_count"],
        "added_operational_paths": list(ADDED_OPERATIONAL_PATHS),
        "added_entrypoint_paths": list(ADDED_ENTRYPOINT_PATHS),
        "scientific_paths_unchanged_from_v1":
            list(SCIENTIFIC_PATHS) == list(V1.SCIENTIFIC_PATHS),
        "entries": entries,
        "entries_sha256": _sha256(canonical),
        "science_is_unchanged_p0_r1_generation3": True,
        "model_operations_performed": 0,
    }


def audit(manifest, *, image_root=None, install_root=None) -> dict:
    """Refuse unless every carried byte in the image matches the manifest."""
    if not isinstance(manifest, dict) \
            or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ImageManifestDefect("the manifest is not a P0-R2 v2 image manifest")
    base = Path(image_root or manifest.get("image_root") or IMAGE_ROOT)
    installed = Path(install_root
                     or manifest.get("entrypoint_install_root")
                     or ENTRYPOINT_INSTALL_ROOT)
    checked, defects = [], []
    for entry in manifest.get("entries") or []:
        if entry.get("kind") == "entrypoint":
            name = entry.get("install_name") or entry["path"].rsplit("/", 1)[-1]
            target, label = installed / name, "%s (installed as %s)" % (
                entry["path"], name)
        else:
            target, label = base / entry["path"], entry["path"]
        if not target.is_file():
            defects.append("%s is missing from the image" % label)
            continue
        payload = target.read_bytes()
        digest = _sha256(payload)
        if digest != entry["sha256"] or len(payload) != entry["bytes"]:
            defects.append(
                "%s carries %s (%d bytes), not the bound %s (%d bytes)"
                % (label, digest[:12], len(payload), entry["sha256"][:12],
                   entry["bytes"]))
            continue
        checked.append(entry["path"])
    if defects:
        raise ImageManifestDefect("; ".join(defects[:8]))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "outcome": "IMAGE_MATCHES_GIT",
        "executable_commit": manifest.get("executable_commit"),
        "executable_tree": manifest.get("executable_tree"),
        "checked_count": len(checked),
        "entries_sha256": manifest.get("entries_sha256"),
        "mismatches": 0,
        "model_operations_performed": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_image_manifest_v2.py",
        "stage": STAGE,
        "manifest_name": MANIFEST_NAME,
        "supersedes": V1.MANIFEST_NAME,
        "image_root": IMAGE_ROOT,
        "entrypoint_install_root": ENTRYPOINT_INSTALL_ROOT,
        "operational_count": len(OPERATIONAL_PATHS),
        "scientific_count": len(SCIENTIFIC_PATHS),
        "entrypoint_count": len(ENTRYPOINT_PATHS),
        "added_operational_paths": list(ADDED_OPERATIONAL_PATHS),
        "added_entrypoint_paths": list(ADDED_ENTRYPOINT_PATHS),
        "derives_its_sets_from_v1": True,
        "edits_v1": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--audit")
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--root")
    parser.add_argument("--image-root")
    parser.add_argument("--install-root")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    try:
        if args.build:
            document = build(args.root, commit=args.commit)
        else:
            manifest = json.loads(Path(args.audit).read_bytes().decode("utf-8"))
            document = audit(manifest, image_root=args.image_root,
                             install_root=args.install_root)
    except ImageManifestDefect as exc:
        print("P0_R2_IMAGE_MANIFEST_V2_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    if args.audit:
        print("P0_R2_IMAGE_TO_GIT_AUDIT_V2_COMPLETE=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
