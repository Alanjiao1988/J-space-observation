#!/usr/bin/env python3
"""Generation-3 replay gate: same science, honest receipt, both routes.

The registered replay-only factorization gate is unchanged and is imported from
the generation-2 implementation. Not one scientific byte differs: the same
immutable P0-T artifacts are read, the same factorization is derived with zero
tokenizer encodes, and the same pass/stop boundary applies.

Two wiring properties change.

First, the emitted receipt is never rewritten. Generation 2 wrote the receipt
with ``transport.complete_byte_recovery_verified = false``, transported those
bytes, and then set the field to ``true`` on an in-memory copy that nobody
downstream ever saw. The recovered receipt therefore always said ``false`` and
the launcher always required ``true``. Generation 3 leaves the field ``false``
and says so explicitly in the document, because the gate genuinely cannot know
whether a future operator recovery will succeed. That proof lives in the
independent reconstruction receipt.

Second, the gate is bound to the generation-3 lock and emits its complete bytes
through the console envelope before it reports a pass, so a pass is never
reported for artifacts that could not be transported.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_replay_gate_v2 as GATE_V2  # noqa: E402
import p0_r1_transport as TRANSPORT  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-replay-gate-v3"

GateRefused = GATE_V2.GateRefused

PASS_STATE = "STUDY3_P0_R1_REPLAY_GATE_PASSED"
TRANSPORT_VERIFIED_LINE = GATE_V2.TRANSPORT_VERIFIED_LINE
PASS_AUTHORIZATION_LINE = GATE_V2.PASS_AUTHORIZATION_LINE

RECEIPT_NAME = "p0_r1_replay_receipt.json"


def annotate_receipt_honestly(receipt):
    """State plainly why the recovery flag is false in the emitted bytes."""
    transport = receipt.setdefault("transport", {})
    transport["complete_byte_recovery_verified"] = False
    transport["self_attestation_refused"] = (
        "this document is the exact byte sequence the gate emitted. It cannot "
        "claim that its own later recovery succeeded, because that had not "
        "happened when these bytes were fixed. Proof of complete-byte "
        "recovery is the separate reconstruction receipt built from the "
        "captured raw log by an independent reader.")
    transport["recovery_proof_document"] = (
        "p0_r1_replay_reconstruction_receipt_v3.json")
    return receipt


def run(out_dir, lock_bytes=None, image_digest=None, ready_commit=None,
        root=None, stream=None, blob_factory=None, execution_name=None):
    """Gate, annotate honestly, transport complete bytes, then report."""
    stream = stream if stream is not None else sys.stdout

    outcome = GATE_V2.gate_run_v2(
        out_dir, authorization=None, image_digest=image_digest,
        ready_commit=ready_commit, lock_bytes=lock_bytes, root=root,
        execution_name=execution_name)

    annotate_receipt_honestly(outcome["receipt"])
    GATE_V2.GATE._write_artifacts(
        out_dir, outcome["result"], outcome["receipt"],
        outcome["result"]["counters"],
        GATE_V2.GATE._disposition_markdown(
            outcome["state"], outcome["result"]["corrected_matrix_summary"],
            outcome["result"]["factorization"],
            outcome["result"]["stop_reason"],
            {"image": {"digest": outcome["result"]["image_digest"]},
             "executable_code": {
                 "commit": outcome["result"]["executable_code_commit"]}}))

    payloads = {}
    for name in TRANSPORT.REPLAY_ARTIFACTS:
        with open(os.path.join(out_dir, name), "rb") as handle:
            payloads[name] = handle.read()

    lines = TRANSPORT.encode(outcome["attempt_id"], payloads)
    for line in lines:
        stream.write(line + "\n")

    recovered = TRANSPORT.recover("\n".join(lines),
                                  attempt_id=outcome["attempt_id"])
    for name, original in payloads.items():
        if recovered.get(name) != original:
            raise GateRefused(
                "the emitted envelope does not reproduce %s byte-for-byte; "
                "a pass is never reported for untransportable artifacts"
                % name)

    stream.write("%s\n" % TRANSPORT_VERIFIED_LINE)
    stream.write("P0_R1_REPLAY_STATE=%s\n" % outcome["state"])
    stream.write("P0_R1_REPLAY_ATTEMPT_ID=%s\n" % outcome["attempt_id"])
    stream.write("P0_R1_REPLAY_RECEIPT_SELF_ATTESTATION=refused\n")
    if outcome["passed"]:
        stream.write("%s\n" % PASS_AUTHORIZATION_LINE)
        stream.write("P0_R1_REPLAY_PASS_REQUIRES_RECONSTRUCTION_RECEIPT=1\n")
    else:
        stream.write("P0_R1_REPLAY_GATE_FAILED_AUTHORIZES_NOTHING=1\n")
    stream.flush()
    return outcome


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_replay_gate_v3.py",
        "delegates_science_to": "p0_r1_replay_gate_v2.gate_run_v2",
        "changes_any_scientific_rule": False,
        "rewrites_its_own_receipt": False,
        "emitted_receipt_claims_its_own_recovery": False,
        "recovery_proof_document":
            "p0_r1_replay_reconstruction_receipt_v3.json",
        "closes": "G2-03",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--lock-file")
    parser.add_argument("--out-dir")
    parser.add_argument("--src")
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-commit")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.gate:
        if not args.lock_file or not args.out_dir:
            print("FAIL: --gate requires --lock-file and --out-dir",
                  file=sys.stderr)
            return 2
        with open(args.lock_file, "rb") as handle:
            lock_bytes = handle.read()
        try:
            outcome = run(args.out_dir, lock_bytes=lock_bytes,
                          image_digest=args.image_digest,
                          ready_commit=args.ready_commit, root=args.src)
        except GateRefused as exc:
            print("P0_R1_REPLAY_GATE_REFUSED=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        return 0 if outcome["passed"] else 4

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
