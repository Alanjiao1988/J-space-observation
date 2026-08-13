#!/usr/bin/env python3
"""Capture a replay run's raw log and rebuild its artifacts independently.

Generation 2 could not authorize its own pilot, and the reason is worth stating
plainly because it is a design lesson rather than a typo.

The generation-2 gate wrote ``p0_r1_replay_receipt.json`` to disk with
``transport.complete_byte_recovery_verified = false``, transported those exact
on-disk bytes, and then set the same field to ``true`` on the *in-memory* copy
only. The launcher required the field to be true on the receipt it recovered.
The recovered receipt is the on-disk one. So the recovered receipt said false,
the launcher required true, and no real replay could ever have authorized the
pilot. Every test that "proved" this worked had hand-built a receipt with the
field already true.

The instinctive repair -- rewrite the receipt after transport -- is worse. It
makes the canonical artifact claim that its own future recovery has already
succeeded, which is circular: the document attests to an event that had not
happened when its bytes were fixed, and the operator can no longer tell a
genuine capture from a re-emitted one.

Generation 3 does the opposite. The gate receipt keeps its honest ``false``
and is never rewritten. Proof of complete-byte recovery lives in a *separate*
reconstruction receipt built by this module from the raw captured log, after
the run, by an independent reader. Authorization is then the agreement of two
documents produced by two different processes at two different times, plus the
lock and the head proof, rather than one document vouching for itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_transport as TRANSPORT  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-replay-reconstruction-v3"

RECONSTRUCTION_RECEIPT_NAME = "p0_r1_replay_reconstruction_receipt_v3.json"
RAW_LOG_NAME = "p0_r1_replay_raw_log.txt"

GATE_RECEIPT_NAME = "p0_r1_replay_receipt.json"
GATE_RESULT_NAME = "p0_r1_replay_result.json"

PASS_STATE = "STUDY3_P0_R1_REPLAY_GATE_PASSED"


class ReplayCaptureDefect(Exception):
    """The capture cannot be trusted to represent the run that produced it."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ReplayCaptureDefect("%s is required and must be a string" % label)
    return value


def reconstruct(raw_log, run_id, attempt_id=None, executable_commit=None,
                image_digest=None, command=None, exit_code=0, stderr=None):
    """Rebuild the four canonical artifacts from a captured raw log.

    The gate is **not** invoked. Nothing is recomputed from live sources: the
    only input is the bytes the run actually emitted, so a receipt produced
    here proves the operator can recover the artifacts from the log alone.
    """
    _require_text(run_id, "run_id")
    if isinstance(raw_log, bytes):
        raw_bytes = raw_log
        text = raw_log.decode("utf-8", "replace")
    else:
        text = _require_text(raw_log, "raw_log")
        raw_bytes = text.encode("utf-8")

    if exit_code != 0:
        raise ReplayCaptureDefect(
            "the replay run %s exited %s; a failed run is a registered stop "
            "and authorizes no reconstruction" % (run_id, exit_code))

    try:
        recovered = TRANSPORT.recover(text, attempt_id=attempt_id)
    except TRANSPORT.TransportDefect as exc:
        raise ReplayCaptureDefect(
            "the captured log of run %s does not contain a complete transport "
            "envelope: %s" % (run_id, exc))

    missing = [name for name in TRANSPORT.REPLAY_ARTIFACTS
               if name not in recovered]
    if missing:
        raise ReplayCaptureDefect(
            "the captured log of run %s is missing %d canonical artifact(s): "
            "%s" % (run_id, len(missing), ", ".join(sorted(missing))))
    extra = [name for name in recovered if name not in TRANSPORT.REPLAY_ARTIFACTS]
    if extra:
        raise ReplayCaptureDefect(
            "the captured log of run %s carries unexpected artifact(s): %s"
            % (run_id, ", ".join(sorted(extra))))

    try:
        gate_receipt = json.loads(recovered[GATE_RECEIPT_NAME].decode("utf-8"))
        gate_result = json.loads(recovered[GATE_RESULT_NAME].decode("utf-8"))
    except (KeyError, ValueError) as exc:
        raise ReplayCaptureDefect(
            "the recovered gate documents are not readable JSON: %s" % exc)

    recovered_attempt = gate_receipt.get("attempt_id")
    if attempt_id and recovered_attempt != attempt_id:
        raise ReplayCaptureDefect(
            "the recovered receipt binds attempt %r, not the captured %r"
            % (recovered_attempt, attempt_id))

    base = TRANSPORT.reconstruction_receipt(
        recovered_attempt, recovered,
        log_identity={"run_id": run_id, "bytes": len(raw_bytes),
                      "sha256": _sha256(raw_bytes)})

    receipt = dict(base)
    receipt.update({
        "schema_version": SCHEMA_VERSION,
        "produced_by": "p0_r1_replay_capture_v3.reconstruct",
        "independent_of_the_gate_process": True,
        "gate_receipt_was_mutated": False,
        "run_id": run_id,
        "attempt_id": recovered_attempt,
        "command": list(command or ()),
        "exit_code": exit_code,
        "stderr_bytes": len((stderr or "").encode("utf-8")),
        "raw_log": {
            "name": RAW_LOG_NAME,
            "bytes": len(raw_bytes),
            "sha256": _sha256(raw_bytes),
            "captured_from_first_byte": True,
            "tail_limited": False,
        },
        "gate": {
            "state": gate_result.get("state"),
            "passed": gate_result.get("state") == PASS_STATE,
            "ready_commit": gate_receipt.get("ready_commit"),
            "image_digest": gate_receipt.get("image_digest"),
            "executable_code_commit": gate_receipt.get(
                "executable_code_commit"),
            "executable_code_tree": gate_receipt.get("executable_code_tree"),
        },
        "complete_byte_recovery_verified": True,
        "recovered_from_the_raw_log_alone": True,
    })

    if executable_commit and receipt["gate"]["executable_code_commit"] \
            and receipt["gate"]["executable_code_commit"] != executable_commit:
        raise ReplayCaptureDefect(
            "the recovered receipt binds executable commit %r, not the "
            "expected %r" % (receipt["gate"]["executable_code_commit"],
                             executable_commit))
    if image_digest and receipt["gate"]["image_digest"] \
            and receipt["gate"]["image_digest"] != image_digest:
        raise ReplayCaptureDefect(
            "the recovered receipt binds image %r, not the expected %r"
            % (receipt["gate"]["image_digest"], image_digest))

    for name, payload in sorted(recovered.items()):
        entry = next((item for item in receipt["artifacts"]
                      if item.get("name") == name), None)
        if entry is None:
            raise ReplayCaptureDefect(
                "the reconstruction receipt does not describe %r" % name)
        if entry.get("bytes") != len(payload) \
                or entry.get("sha256") != _sha256(payload):
            raise ReplayCaptureDefect(
                "the reconstruction receipt disagrees with the recovered "
                "bytes of %r" % name)

    return receipt, recovered


def validate_authorization_pair(gate_receipt, reconstruction,
                                attempt_id=None, run_id=None):
    """Require the emitted receipt and the independent reconstruction to agree.

    Neither document alone authorizes anything. The gate receipt is trusted for
    what the gate concluded; the reconstruction receipt is trusted for what the
    operator can actually recover. A pilot needs both.
    """
    if not isinstance(gate_receipt, dict) or not isinstance(reconstruction,
                                                            dict):
        raise ReplayCaptureDefect(
            "authorization requires both the emitted replay receipt and the "
            "independent reconstruction receipt as documents")
    if reconstruction.get("schema_version") != SCHEMA_VERSION:
        raise ReplayCaptureDefect(
            "the reconstruction receipt schema %r is not %r"
            % (reconstruction.get("schema_version"), SCHEMA_VERSION))
    if not reconstruction.get("independent_of_the_gate_process"):
        raise ReplayCaptureDefect(
            "the reconstruction receipt does not claim independence from the "
            "gate process; a self-attested capture is not a proof")
    if reconstruction.get("gate_receipt_was_mutated"):
        raise ReplayCaptureDefect(
            "the gate receipt was mutated after emission; the canonical "
            "artifact must remain the exact emitted byte sequence")
    if not reconstruction.get("complete_byte_recovery_verified"):
        raise ReplayCaptureDefect(
            "the reconstruction receipt does not record a verified "
            "complete-byte recovery")

    gate_attempt = gate_receipt.get("attempt_id")
    recon_attempt = reconstruction.get("attempt_id")
    if not gate_attempt or gate_attempt != recon_attempt:
        raise ReplayCaptureDefect(
            "the emitted receipt binds attempt %r but the reconstruction "
            "binds %r" % (gate_attempt, recon_attempt))
    if attempt_id and attempt_id != gate_attempt:
        raise ReplayCaptureDefect(
            "the requested attempt %r is not the replayed attempt %r"
            % (attempt_id, gate_attempt))
    if run_id and reconstruction.get("run_id") != run_id:
        raise ReplayCaptureDefect(
            "the reconstruction receipt was built from run %r, not the "
            "captured run %r" % (reconstruction.get("run_id"), run_id))

    gate = reconstruction.get("gate") or {}
    if not gate.get("passed"):
        raise ReplayCaptureDefect(
            "the recovered gate state %r is not a pass; a replay failure "
            "authorizes no model operation" % (gate.get("state"),))

    for field, label in (("image_digest", "image digest"),
                         ("executable_code_commit", "executable commit"),
                         ("executable_code_tree", "executable tree")):
        emitted = gate_receipt.get(field)
        recovered = gate.get(field)
        if emitted and recovered and emitted != recovered:
            raise ReplayCaptureDefect(
                "the emitted receipt and the reconstruction disagree on the "
                "%s: %r vs %r" % (label, emitted, recovered))

    # The emitted receipt is expected to say false here, and that is correct:
    # the gate genuinely could not know whether a later operator recovery would
    # succeed. Requiring true would force the circular self-attestation this
    # module exists to remove.
    emitted_claim = (gate_receipt.get("transport") or {}).get(
        "complete_byte_recovery_verified")
    return {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": gate_attempt,
        "run_id": reconstruction.get("run_id"),
        "gate_state": gate.get("state"),
        "emitted_receipt_self_claim": bool(emitted_claim),
        "recovery_proved_by": RECONSTRUCTION_RECEIPT_NAME,
        "authorizes_one_bounded_model_pilot": True,
    }


def write_capture(out_dir, run_id, raw_log, attempt_id=None, command=None,
                  exit_code=0, stderr=None, executable_commit=None,
                  image_digest=None):
    """Persist the raw log, every recovered artifact and the receipt."""
    os.makedirs(out_dir, exist_ok=True)
    receipt, recovered = reconstruct(
        raw_log, run_id, attempt_id=attempt_id, command=command,
        exit_code=exit_code, stderr=stderr,
        executable_commit=executable_commit, image_digest=image_digest)

    raw_bytes = raw_log if isinstance(raw_log, bytes) \
        else raw_log.encode("utf-8")
    with open(os.path.join(out_dir, RAW_LOG_NAME), "wb") as handle:
        handle.write(raw_bytes)

    written = TRANSPORT.write_recovered(recovered, out_dir)
    payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")
    with open(os.path.join(out_dir, RECONSTRUCTION_RECEIPT_NAME), "wb") as fh:
        fh.write(payload)
    written.append({"name": RECONSTRUCTION_RECEIPT_NAME,
                    "bytes": len(payload), "sha256": _sha256(payload)})
    written.append({"name": RAW_LOG_NAME, "bytes": len(raw_bytes),
                    "sha256": _sha256(raw_bytes)})
    return receipt, written


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_replay_capture_v3.py",
        "reconstruction_receipt": RECONSTRUCTION_RECEIPT_NAME,
        "raw_log": RAW_LOG_NAME,
        "rewrites_the_gate_receipt": False,
        "authorization_requires_both_receipts": True,
        "closes": "G2-03",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--reconstruct", action="store_true")
    parser.add_argument("--raw-log")
    parser.add_argument("--run-id")
    parser.add_argument("--attempt")
    parser.add_argument("--out-dir")
    parser.add_argument("--exit-code", type=int, default=0)
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.reconstruct:
        if not args.raw_log or not args.run_id or not args.out_dir:
            print("FAIL: --reconstruct requires --raw-log, --run-id and "
                  "--out-dir", file=sys.stderr)
            return 2
        with open(args.raw_log, "rb") as handle:
            raw = handle.read()
        try:
            receipt, written = write_capture(
                args.out_dir, args.run_id, raw, attempt_id=args.attempt,
                exit_code=args.exit_code)
        except ReplayCaptureDefect as exc:
            print("P0_R1_REPLAY_RECONSTRUCTION_REFUSED=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        for entry in written:
            print("RECOVERED=%s BYTES=%d SHA256=%s"
                  % (entry["name"], entry["bytes"], entry["sha256"]))
        print("P0_R1_REPLAY_RECONSTRUCTED=1 RUN=%s ATTEMPT=%s"
              % (receipt["run_id"], receipt["attempt_id"]))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
