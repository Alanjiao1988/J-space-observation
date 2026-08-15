#!/usr/bin/env python3
"""The generation-2 P0-R2 image manifest: v2's bindings plus the g2 bytes.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
section 6.4.

Generation 2 changes an image-bound live entry point, so it must build and
publish a **new** image; the generation-1 digest is not reusable as the
generation-2 execution image. This manifest is what makes that image auditable:
every carried byte is bound to the Git blob of the executable commit, and the
in-build audit refuses the push if a single byte drifts.

Like the v2 manifest before it, this module is additive by construction. It
imports the v2 path tuples rather than restating them, so its operational,
scientific and entry-point sets are provably v2's sets plus a named delta, and
no frozen byte is edited to achieve it. The entry count is **derived** from
those tuples, never asserted: section 6.4 forbids hard-coding generation 1's
44-file count when the new manifest has a different derived count.

The science is unchanged: the same P0-R1 generation-3 scientific modules, from
the same commit, verified by SHA-256 before import.

Model-free: this module reads Git objects and hashes bytes.
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
import p0_r2_image_manifest_v2 as V2  # noqa: E402


REPO_ROOT = P0_R2_DIR.parent.parent.parent.parent

SCHEMA_VERSION = "study3-p0-r2-image-manifest-g2"
STAGE = "STUDY3-P0-R2"
GENERATION = 2
MANIFEST_NAME = "p0_r2_image_manifest_g2.json"

IMAGE_ROOT = V2.IMAGE_ROOT
ENTRYPOINT_INSTALL_ROOT = V2.ENTRYPOINT_INSTALL_ROOT

#: Exactly what generation 2 adds to the image, and nothing else.
ADDED_OPERATIONAL_PATHS = (
    "studies/study3/pilot/p0_r2/p0_r2_namespace_g2.py",
    "studies/study3/pilot/p0_r2/p0_r2_prefix_proof_g2.py",
    "studies/study3/pilot/p0_r2/p0_r2_host_submission_g2.py",
    "studies/study3/pilot/p0_r2/p0_r2_image_manifest_g2.py",
    "studies/study3/pilot/p0_r2/p0_r2_execution_lock_g2.py",
    "studies/study3/pilot/p0_r2/p0_r2_closure_binding_g2.py",
    "studies/study3/pilot/p0_r2/p0_r2_host_preflight_g2.py",
    "studies/study3/pilot/p0_r2/p0_r2_replay_gate_g2.py",
    "studies/study3/pilot/p0_r2/p0_r2_hard_kill_g2.py",
)

ADDED_ENTRYPOINT_PATHS = (
    "studies/study3/pilot/p0_r2/container/p0_r2_replay_g2.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_canary_g2.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_recovery_g2.sh",
    "studies/study3/pilot/p0_r2/container/p0_r2_model_pilot_g2.sh",
)

OPERATIONAL_PATHS = tuple(V2.OPERATIONAL_PATHS) + ADDED_OPERATIONAL_PATHS
SCIENTIFIC_PATHS = tuple(V2.SCIENTIFIC_PATHS)
ENTRYPOINT_PATHS = tuple(V2.ENTRYPOINT_PATHS) + ADDED_ENTRYPOINT_PATHS


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
                "added_by_generation2":
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
        "generation": GENERATION,
        "supersedes": V2.MANIFEST_NAME,
        "executable_commit": resolved,
        "executable_tree": tree,
        "image_root": IMAGE_ROOT,
        "entrypoint_install_root": ENTRYPOINT_INSTALL_ROOT,
        "operational_count": len(OPERATIONAL_PATHS),
        "scientific_count": len(SCIENTIFIC_PATHS),
        "entrypoint_count": len(ENTRYPOINT_PATHS),
        "entry_count": len(entries),
        "v2_entry_count": len(V2.OPERATIONAL_PATHS)
        + len(V2.SCIENTIFIC_PATHS) + len(V2.ENTRYPOINT_PATHS),
        "v1_entry_count": len(V1.OPERATIONAL_PATHS)
        + len(V1.SCIENTIFIC_PATHS) + len(V1.ENTRYPOINT_PATHS),
        "entry_count_is_derived_not_asserted": True,
        "added_operational_paths": list(ADDED_OPERATIONAL_PATHS),
        "added_entrypoint_paths": list(ADDED_ENTRYPOINT_PATHS),
        "scientific_paths_unchanged_from_v2":
            list(SCIENTIFIC_PATHS) == list(V2.SCIENTIFIC_PATHS),
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
        raise ImageManifestDefect(
            "the manifest is not a P0-R2 generation-2 image manifest")
    if manifest.get("generation") != GENERATION:
        raise ImageManifestDefect("the manifest is not generation 2")
    entries = manifest.get("entries") or []
    if not entries:
        raise ImageManifestDefect("the manifest binds no path")
    if len(entries) != manifest.get("entry_count"):
        raise ImageManifestDefect(
            "the manifest declares %r entries but carries %d"
            % (manifest.get("entry_count"), len(entries)))
    base = Path(image_root or manifest.get("image_root") or IMAGE_ROOT)
    installed = Path(install_root
                     or manifest.get("entrypoint_install_root")
                     or ENTRYPOINT_INSTALL_ROOT)
    checked, defects = [], []
    for entry in entries:
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
    if len(checked) != len(entries):
        raise ImageManifestDefect(
            "%d of %d bound paths were checked" % (len(checked), len(entries)))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "outcome": "IMAGE_MATCHES_GIT",
        "executable_commit": manifest.get("executable_commit"),
        "executable_tree": manifest.get("executable_tree"),
        "checked_count": len(checked),
        "bound_count": len(entries),
        "entries_sha256": manifest.get("entries_sha256"),
        "mismatches": 0,
        "model_operations_performed": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_image_manifest_g2.py",
        "stage": STAGE,
        "generation": GENERATION,
        "manifest_name": MANIFEST_NAME,
        "supersedes": V2.MANIFEST_NAME,
        "image_root": IMAGE_ROOT,
        "entrypoint_install_root": ENTRYPOINT_INSTALL_ROOT,
        "operational_count": len(OPERATIONAL_PATHS),
        "scientific_count": len(SCIENTIFIC_PATHS),
        "entrypoint_count": len(ENTRYPOINT_PATHS),
        "derived_entry_count": len(OPERATIONAL_PATHS) + len(SCIENTIFIC_PATHS)
        + len(ENTRYPOINT_PATHS),
        "added_operational_paths": list(ADDED_OPERATIONAL_PATHS),
        "added_entrypoint_paths": list(ADDED_ENTRYPOINT_PATHS),
        "derives_its_sets_from_v2": True,
        "edits_v1_or_v2": False,
        "hard_codes_a_file_count": False,
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
        print("P0_R2_G2_IMAGE_MANIFEST_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    if args.audit:
        print("P0_R2_G2_IMAGE_TO_GIT_AUDIT_COMPLETE=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
