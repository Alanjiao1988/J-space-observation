#!/usr/bin/env python3
"""Run the exact production model shell and prove it reaches the boundary once.

This is the canary that would have caught G2-02 and G2-03 before publication.
It does not inspect the shell for substrings and it does not call an internal
function with a pre-built authorization. It writes a valid, internally
consistent set of the four mandatory inputs, invokes
``p0_r1_model_pilot_v3.sh`` exactly as the GPU job will, and requires that the
sentinel executor line appears exactly once with no model library imported.

If the shell forgets an argument, if the runner CLI stops constructing the
authorization, if the gate receipt is required to self-attest again, or if the
prefix preflight is bypassed, this canary fails in the image build rather than
on the single GPU attempt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

CONTAINER_DIR = os.path.dirname(os.path.abspath(__file__))
P0_R1_DIR = os.path.dirname(CONTAINER_DIR)
sys.path.insert(0, P0_R1_DIR)

import p0_r1_transport as TRANSPORT  # noqa: E402
import p0_r1_authorization_v3 as AUTHZ  # noqa: E402
import p0_r1_execution_lock_v3 as LOCK_V3  # noqa: E402

SENTINEL_LINE = "P0_R1_SENTINEL_EXECUTOR_REACHED=1"

ATTEMPT = "g3cliwiring-000000000000"

#: The image deliberately does NOT contain the execution lock: the lock binds
#: the image digest, so it necessarily postdates the image and the Dockerfile
#: removes it. The canary therefore synthesizes a structurally valid lock
#: rather than reading one. That is the honest arrangement -- this canary
#: tests the shell-to-CLI authorization wiring, not the authenticity of a
#: lock, and a canary that could only run when a real lock happened to be
#: present would not run at build time at all.
def _lock_document(lock_path):
    """Read the active lock when present, otherwise synthesize one."""
    if lock_path and os.path.exists(lock_path):
        with open(lock_path, "rb") as handle:
            return json.loads(handle.read().decode("utf-8")), lock_path
    root = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))
    canaries = {name: {"passed": True, "synthetic": True}
                for name in LOCK_V3.CANARY_NAMES}
    lock = LOCK_V3.build(
        root=root, executable_commit="c" * 40, executable_tree="d" * 40,
        ready_anchor_parent="a" * 40,
        image_digest="sha256:" + "1" * 64,
        base_digest="sha256:" + "2" * 64,
        canary_receipts=canaries)
    return lock, None


def _synthetic_inputs(work, lock_path):
    """Build four consistent documents the production path will accept."""
    lock, _actual = _lock_document(lock_path)

    executable = lock["executable_code"]
    relationship = lock["ready_commit_relationship"]
    # The lock deliberately records no anchor commit: a commit cannot contain
    # its own hash, so the successor computes it at run time. The canary
    # supplies a synthetic one, which is exactly what the real proof does.
    anchor = relationship.get("ready_anchor_commit") or "b" * 40
    digest = lock["image"]["digest"]

    receipt = {
        "schema_version": "study3-p0-r1-replay-gate-receipt-v3",
        "attempt_id": ATTEMPT,
        "ready_commit": anchor,
        "image_digest": digest,
        "executable_code_commit": executable["commit"],
        "executable_code_tree": executable["tree"],
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "model_operations_performed": 0,
        "gpu_allocated": False,
        "transport": {"complete_byte_recovery_verified": False},
    }
    reconstruction = {
        "schema_version": "study3-p0-r1-replay-reconstruction-v3",
        "attempt_id": ATTEMPT,
        "run_id": "cli-wiring-canary",
        "independent_of_the_gate_process": True,
        "gate_receipt_was_mutated": False,
        "complete_byte_recovery_verified": True,
        "gate": {
            "state":
                "STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT",
            "passed": True,
            "image_digest": digest,
            "executable_code_commit": executable["commit"],
            "executable_code_tree": executable["tree"],
            "ready_commit": anchor,
        },
    }
    lock_payload = (
        json.dumps(lock, indent=1, sort_keys=True) + "\n").encode("utf-8")
    proof = {
        "schema_version": "study3-p0-r1-ready-anchor-v3",
        "published_head": {"commit": "f" * 40, "tree": "e" * 40},
        "ready_anchor": {
            "commit": anchor, "tree": "d" * 40,
            "parent": relationship["ready_anchor_parent"],
        },
        "executable_code": {"commit": executable["commit"],
                            "tree": executable["tree"]},
        "head_equals_published": True,
        "worktree_clean": True,
        "all_changes_are_governance_only": True,
        "bound_paths_changed_after_image_build": [],
        "execution_lock": {
            "path": LOCK_V3.LOCK_NAME.rsplit("/", 1)[-1]
            if "/" in LOCK_V3.LOCK_NAME else
            "studies/study3/pilot/p0_r1/" + LOCK_V3.LOCK_NAME,
            "bytes": len(lock_payload),
            "sha256": hashlib.sha256(lock_payload).hexdigest(),
        },
    }
    paths = {}
    for name, document in (("p0_r1_replay_receipt.json", receipt),
                           ("p0_r1_replay_reconstruction_receipt_v3.json",
                            reconstruction),
                           ("p0_r1_head_proof_v3.json", proof)):
        path = os.path.join(work, name)
        with open(path, "wb") as handle:
            handle.write((json.dumps(document, indent=2, sort_keys=True)
                          + "\n").encode("utf-8"))
        paths[name] = path

    # When no real lock exists (inside the image, by design), write the
    # synthetic one so the shell has a concrete file to pass through.
    if not (lock_path and os.path.exists(lock_path)):
        synthetic = os.path.join(work, "p0_r1_execution_lock_v3.json")
        with open(synthetic, "wb") as handle:
            handle.write(lock_payload)
        paths["p0_r1_execution_lock_v3.json"] = synthetic
    return paths


def _bash_path(path):
    """Translate Windows paths only when the available bash is Git/MSYS bash."""
    if os.name != "nt":
        return path
    try:
        return subprocess.check_output(
            ["cygpath", "-u", path], text=True,
            encoding="utf-8", errors="strict").strip()
    except (OSError, subprocess.CalledProcessError):
        return path


def run(lock_path=None, shell=None, stream=None):
    stream = stream if stream is not None else sys.stdout
    lock_path = lock_path or os.path.join(
        P0_R1_DIR, "p0_r1_execution_lock_v3.json")
    shell = shell or os.path.join(CONTAINER_DIR, "p0_r1_model_pilot_v3.sh")

    work = tempfile.mkdtemp(prefix="p0r1-cliwiring-")
    source = os.path.join(work, "source")
    runtime = os.path.join(work, "runtime")
    os.makedirs(source)
    paths = _synthetic_inputs(source, lock_path)
    effective_lock = paths.get("p0_r1_execution_lock_v3.json", lock_path)

    environment = dict(os.environ)
    environment.update({
        "P0_R1_SRC": _bash_path(os.path.abspath(os.path.join(
            P0_R1_DIR, "..", "..", "..", ".."))),
        "P0_R1_RUNTIME_ROOT": _bash_path(runtime),
        "P0_R1_OUT_DIR": _bash_path(os.path.join(runtime, "result")),
        "PYTHON": _bash_path(sys.executable),
        "P0_R1_EXECUTOR": "sentinel",
        "P0_R1_ATTEMPT": ATTEMPT,
        "P0_R1_CANARY_IN_MEMORY_BLOB": "1",
    })
    injections = {
        "P0_R1_LOCK_V3_B64": effective_lock,
        "P0_R1_REPLAY_RECEIPT_V3_B64":
            paths["p0_r1_replay_receipt.json"],
        "P0_R1_RECONSTRUCTION_RECEIPT_V3_B64":
            paths["p0_r1_replay_reconstruction_receipt_v3.json"],
        "P0_R1_HEAD_PROOF_V3_B64": paths["p0_r1_head_proof_v3.json"],
    }
    for env_name, path in injections.items():
        with open(path, "rb") as handle:
            environment[env_name] = AUTHZ.encode_injection(handle.read())

    completed = subprocess.run(  # noqa: S603 - fixed script
        ["bash", shell], env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    output = (completed.stdout or "") + (completed.stderr or "")
    reached = output.count(SENTINEL_LINE)

    stream.write("P0_R1_CLI_WIRING_EXIT=%d\n" % completed.returncode)
    stream.write("P0_R1_CLI_WIRING_SENTINEL_COUNT=%d\n" % reached)
    if reached != 1:
        stream.write((completed.stdout or "")[-3000:])
        stream.write((completed.stderr or "")[-3000:])
        raise SystemExit(
            "the production model shell did not reach the authorized executor "
            "boundary exactly once (saw %d)" % reached)
    if output.count("P0_R1_INJECTED=") != 4:
        raise SystemExit(
            "the production shell did not reconstruct all four exact inputs")
    if "P0_R1_PILOT_SHELL_TRAP_COMPLETE=1" not in output \
            or "P0_R1_FINALIZED_RECEIPT_REEMITTED=1" not in output:
        raise SystemExit("the production shell EXIT durability trap did not run")
    for forbidden in ("transformers", "torch"):
        if "import %s" % forbidden in output:
            raise SystemExit(
                "the wiring canary imported %s; the boundary must be reached "
                "with no model library" % forbidden)
    stream.write("P0_R1_CLI_WIRING_CANARY=passed\n")
    stream.flush()
    return completed.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--lock-file")
    parser.add_argument("--shell")
    args = parser.parse_args(argv)
    if args.run:
        run(lock_path=args.lock_file, shell=args.shell)
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
