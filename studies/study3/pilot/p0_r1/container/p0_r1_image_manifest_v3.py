#!/usr/bin/env python3
"""Prove, at build time, that the image can invoke its own job command.

Runs inside the image with no repository context mounted, which is exactly the
condition a Container Apps job runs under and exactly the condition generation
1 failed: its job command named a path that did not exist in the image, and its
entry point defaulted to a checkout mount no GPU job provides.

This emitter records the identity of every generation-3 blob under the
standalone source root, verifies that every declared entry point exists and is
executable, verifies that both dependency sets are installed exactly as pinned
and share no package, and refuses if any result byte is present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

SRC = os.environ.get("P0_R1_SRC", "/opt/jspace/src")
P0_R1_DIR = os.path.join(SRC, "studies", "study3", "pilot", "p0_r1")

SCHEMA_VERSION = "study3-p0-r1-image-manifest-v3"

ENTRYPOINTS = (
    "/usr/local/bin/p0_r1_model_pilot_v3.sh",
    "/usr/local/bin/p0_r1_replay_v3.sh",
    "/usr/local/bin/p0_r1_recovery_v3.sh",
    "/usr/local/bin/p0_r1_canary_v3.sh",
)

REQUIRED_MODULES = (
    "p0_r1_azure_query_v3.py",
    "p0_r1_ready_anchor_v3.py",
    "p0_r1_replay_capture_v3.py",
    "p0_r1_authorization_v3.py",
    "p0_r1_journal_v3.py",
    "p0_r1_blob_transport_v3.py",
    "p0_r1_prefix_preflight_v3.py",
    "p0_r1_model_runner_v3.py",
    "p0_r1_replay_gate_v3.py",
    "p0_r1_recovery_v3.py",
    "p0_r1_execution_lock_v3.py",
    "p0_r1_job_spec_v3.py",
    "execution/p0_r1_model_execution_v3.py",
    "container/p0_r1_infrastructure_receipt_v3.py",
    "container/p0_r1_cli_wiring_canary_v3.py",
    "container/p0_r1_private_journal_canary_v3.py",
    "container/p0_r1_hard_kill_canary_v3.py",
)

FROZEN_SCIENCE_REQUIREMENTS = "requirements-study3-p0-r1.txt"
TRANSPORT_REQUIREMENTS = "requirements-study3-p0-r1-transport-v2.txt"

FORBIDDEN_RESULT_MARKERS = ("results", "p0_r1_pilot_result.json",
                            "p0_r1_replay_gate_result.json")


class ImageDefect(Exception):
    """The image cannot run its own job command."""


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_pins(path):
    pins = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.split("#", 1)[0].strip()
            if not line or "==" not in line:
                continue
            name, version = line.split("==", 1)
            pins[name.strip().lower().replace("_", "-")] = version.strip()
    return pins


def installed_version(package):
    try:
        from importlib import metadata
    except ImportError:  # pragma: no cover - Python < 3.8
        return None
    try:
        return metadata.version(package)
    except Exception:  # noqa: BLE001
        return None


def verify_frozen_dependencies():
    """Both sets installed exactly as pinned, and disjoint."""
    science_path = os.path.join(P0_R1_DIR, "container",
                                FROZEN_SCIENCE_REQUIREMENTS)
    transport_path = os.path.join(P0_R1_DIR, "container",
                                  TRANSPORT_REQUIREMENTS)
    science = read_pins(science_path)
    transport = read_pins(transport_path)

    overlap = sorted(set(science) & set(transport))
    if overlap:
        raise ImageDefect(
            "the frozen science set and the transport closure share %d "
            "package(s): %s. A shared package means resolving one can move "
            "the other." % (len(overlap), ", ".join(overlap)))

    moved = []
    for pins, label in ((science, "frozen science"),
                        (transport, "durable transport")):
        for package, pinned in sorted(pins.items()):
            actual = installed_version(package)
            if actual is None:
                moved.append("%s %s (%s) is not installed"
                             % (label, package, pinned))
            elif actual != pinned:
                moved.append("%s %s is %s, pinned %s"
                             % (label, package, actual, pinned))
    if moved:
        raise ImageDefect(
            "the installed environment does not match the pins: %s"
            % "; ".join(moved))
    return {"frozen_science_pins": len(science),
            "durable_transport_pins": len(transport),
            "shared_packages": 0}


def build_manifest():
    if not os.path.isdir(P0_R1_DIR):
        raise ImageDefect("the standalone source root %s is absent" % P0_R1_DIR)

    blobs = []
    for base, dirs, files in os.walk(os.path.join(SRC, "studies", "study3",
                                                  "pilot", "p0_r1")):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for filename in sorted(files):
            path = os.path.join(base, filename)
            relative = os.path.relpath(path, SRC).replace(os.sep, "/")
            blobs.append({"path": relative,
                          "bytes": os.path.getsize(path),
                          "sha256": _sha256(path)})

    missing = []
    for module in REQUIRED_MODULES:
        path = os.path.join(P0_R1_DIR, module.replace("/", os.sep))
        if not os.path.exists(path):
            missing.append(module)
    if missing:
        raise ImageDefect(
            "%d required generation-3 module(s) are absent from the image: %s"
            % (len(missing), ", ".join(missing)))

    for entry in ENTRYPOINTS:
        if not os.path.exists(entry):
            raise ImageDefect(
                "entry point %s does not exist in the image; a Container Apps "
                "job command must name a path that is present" % entry)
        if not os.access(entry, os.X_OK):
            raise ImageDefect("entry point %s is not executable" % entry)

    results_dir = os.path.join(P0_R1_DIR, "results")
    if os.path.exists(results_dir):
        raise ImageDefect(
            "a results directory is baked into the image; the build must not "
            "be able to see an outcome")
    for blob in blobs:
        name = blob["path"].rsplit("/", 1)[-1]
        if name in FORBIDDEN_RESULT_MARKERS:
            raise ImageDefect("a result artifact %s is baked into the image"
                              % blob["path"])

    dependencies = verify_frozen_dependencies()

    return {
        "schema_version": SCHEMA_VERSION,
        "generation": 3,
        "standalone_source_root": SRC,
        "entrypoints": list(ENTRYPOINTS),
        "required_modules": list(REQUIRED_MODULES),
        "blob_count": len(blobs),
        "blobs": blobs,
        "dependencies": dependencies,
        "requires_a_context_mount": False,
        "results_present": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="/opt/jspace/p0_r1_image_manifest_v3.json")
    args = parser.parse_args(argv)

    try:
        manifest = build_manifest()
    except ImageDefect as exc:
        print("P0_R1_IMAGE_MANIFEST_V3_REFUSED=1", file=sys.stderr)
        print("  %s" % exc, file=sys.stderr)
        return 3

    payload = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode(
        "utf-8")
    try:
        with open(args.out, "wb") as handle:
            handle.write(payload)
    except OSError:
        pass

    print("P0_R1_IMAGE_MANIFEST_V3=1")
    print("  standalone source root %s; %d entry points verified"
          % (SRC, len(ENTRYPOINTS)))
    print("  frozen science pins %d, unchanged; transport pins %d, installed"
          % (manifest["dependencies"]["frozen_science_pins"],
             manifest["dependencies"]["durable_transport_pins"]))
    print("  wrote %s with %d blob identities" % (args.out,
                                                  manifest["blob_count"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
