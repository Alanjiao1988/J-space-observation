#!/usr/bin/env python3
"""Audit that the bytes inside the image are the bytes in Git.

The P0-R2 image is a *thin* successor: it changes the submission transport and
adds P0-R2 operational modules, and it changes nothing about the science. That
claim is only worth something if it can be checked mechanically, so this module
produces a manifest of every operational and delegated-scientific file that the
image is supposed to carry, keyed by both the SHA-256 of the bytes and the Git
blob id of the same bytes at the executable commit.

Inside the container the same module runs in ``--audit`` mode against the image
filesystem and refuses if a single byte differs from the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent
REPO_ROOT = P0_R2_DIR.parents[3]

#: Repository-relative paths the image carries. Operational bytes are P0-R2's
#: own; scientific bytes are P0-R1 generation-3 and are reused unmodified.
OPERATIONAL_PATHS = (
    "studies/study3/pilot/p0_r2/p0_r2_transport.py",
    "studies/study3/pilot/p0_r2/p0_r2_transport_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_blob_transport.py",
    "studies/study3/pilot/p0_r2/p0_r2_blob_transport_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_journal_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_submission_context.py",
    "studies/study3/pilot/p0_r2/p0_r2_acr_submission.py",
    "studies/study3/pilot/p0_r2/p0_r2_closure_binding_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_azure_query_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_replay_capture_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_verify_replay_receipt.py",
    "studies/study3/pilot/p0_r2/p0_r2_authorization_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_job_spec_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_replay_gate_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_prefix_preflight_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_recovery_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_model_runner_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_image_manifest_v1.py",
    "studies/study3/pilot/p0_r2/p0_r2_execution_lock_v1.py",
)

SCIENTIFIC_PATHS = (
    "studies/study3/pilot/p0_r1/p0_r1_factorization.py",
    "studies/study3/pilot/p0_r1/p0_r1_eligibility.py",
    "studies/study3/pilot/p0_r1/p0_r1_protocol.py",
    "studies/study3/pilot/p0_r1/p0_r1_counters.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_authorization_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_prefix_preflight_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_recovery_v3.py",
)

#: Where the image places the repository. The task file already binds
#: ``P0_R2_SRC=/opt/jspace/src``, so the manifest uses the same root. The
#: container copies the two package directories only; it never carries the
#: whole checkout.
IMAGE_ROOT = "/opt/jspace/src"

#: The entry points are the surface that actually launches everything, and
#: they are the bytes that hold the refusals: no live replay, no envelope
#: consumption, no model operation. Auditing only the Python modules would
#: leave that surface free to drift from Git while the audit still reported
#: success, so the installed scripts are bound too. They are installed flat
#: into ``/usr/local/bin``, not under the image root, so each entry records
#: where it was installed as well as where Git keeps it.
ENTRYPOINT_INSTALL_ROOT = "/usr/local/bin"

ENTRYPOINT_PATHS = (
    "studies/study3/pilot/p0_r2/container/p0_r2_successor_v1.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_canary_v1.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_replay_v1.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_model_pilot_v1.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_recovery_v1.sh",
)

SCHEMA_VERSION = "study3-p0-r2-image-manifest-v1"
STAGE = "STUDY3-P0-R2"
MANIFEST_NAME = "p0_r2_image_manifest_v1.json"


class ImageManifestDefect(Exception):
    """The image does not carry the bytes the manifest binds."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root)] + list(args),
        capture_output=True, text=True, check=False)
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
            payload = subprocess.run(
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
            }
            if kind == "entrypoint":
                # The Dockerfile flattens ``entrypoints/`` into a single
                # directory, so the audited location is the installed name.
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
        "executable_commit": resolved,
        "executable_tree": tree,
        "image_root": IMAGE_ROOT,
        "entrypoint_install_root": ENTRYPOINT_INSTALL_ROOT,
        "operational_count": len(OPERATIONAL_PATHS),
        "scientific_count": len(SCIENTIFIC_PATHS),
        "entrypoint_count": len(ENTRYPOINT_PATHS),
        "entry_count": len(entries),
        "entries": entries,
        "entries_sha256": _sha256(canonical),
        "science_is_unchanged_p0_r1_generation3": True,
        "model_operations_performed": 0,
    }


def audit(manifest, *, image_root=None, install_root=None) -> dict:
    """Refuse unless every carried byte in the image matches the manifest."""
    if not isinstance(manifest, dict) \
            or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ImageManifestDefect("the manifest is not a P0-R2 image manifest")
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
                % (label, digest[:12], len(payload),
                   entry["sha256"][:12], entry["bytes"]))
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
        "module": "p0_r2_image_manifest_v1.py",
        "stage": STAGE,
        "manifest_name": MANIFEST_NAME,
        "image_root": IMAGE_ROOT,
        "entrypoint_install_root": ENTRYPOINT_INSTALL_ROOT,
        "operational_count": len(OPERATIONAL_PATHS),
        "scientific_count": len(SCIENTIFIC_PATHS),
        "entrypoint_count": len(ENTRYPOINT_PATHS),
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
            manifest = json.loads(Path(args.audit).read_text(encoding="utf-8"))
            document = audit(manifest, image_root=args.image_root,
                             install_root=args.install_root)
    except ImageManifestDefect as exc:
        print("P0_R2_IMAGE_MANIFEST_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    if args.audit:
        print("P0_R2_IMAGE_TO_GIT_AUDIT_COMPLETE=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
