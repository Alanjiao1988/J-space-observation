#!/usr/bin/env python3
"""Emit the most conservative receipt over both durable routes.

Generation 2's shell EXIT trap wrote ``p0_r1_infrastructure_receipt.json`` into
the container's ephemeral result directory and printed a digest of it. When the
replica is torn down, the file is gone and the digest proves only that bytes
once existed somewhere. That is the failure mode the whole round exists to
close: an operator cannot re-derive an observation from its hash.

This module is what the trap actually calls. Whenever the process can still
write, it produces a receipt describing exactly what is known -- including
"almost nothing", which is a legitimate and useful thing to record -- and gets
it out by both routes:

* the private object store, create-only, under the attempt-bound prefix; and
* the bounded complete-byte console envelope, so the receipt is recoverable
  from the captured execution log even if the store is unreachable.

If the store is unreachable it reports durability degradation explicitly rather
than exiting successfully, because a silent single-route write is how evidence
disappears.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import p0_r1_transport as TRANSPORT  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-infrastructure-receipt-v3"

RECEIPT_NAME = "p0_r1_infrastructure_receipt.json"

STATE_INFRASTRUCTURE = "STUDY3_P0_R1_PILOT_INFRASTRUCTURE_STOP"
STATE_SHELL_CLEAN = "STUDY3_P0_R1_PILOT_SHELL_EXITED_CLEAN"


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def build(exit_code, attempt_id=None, out_dir=None, lock_sha256=None,
          detail=None):
    """Describe what is known, conservatively, without inventing anything."""
    known = {}
    if out_dir and os.path.isdir(out_dir):
        for name in sorted(os.listdir(out_dir)):
            path = os.path.join(out_dir, name)
            if os.path.isfile(path):
                with open(path, "rb") as handle:
                    payload = handle.read()
                known[name] = {"bytes": len(payload),
                               "sha256": _sha256(payload)}
    return {
        "schema_version": SCHEMA_VERSION,
        "state": STATE_SHELL_CLEAN if exit_code == 0
        else STATE_INFRASTRUCTURE,
        "attempt_id": attempt_id,
        "shell_exit_code": exit_code,
        "recorded_at": datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "execution_lock_sha256": lock_sha256,
        "local_artifacts_observed": known,
        "local_artifact_count": len(known),
        "meaning": (
            "this receipt is emitted by the shell exit boundary. It is the "
            "most conservative statement available at that point and it makes "
            "no claim about work it did not observe. Missing or ambiguous "
            "evidence is unknown, not zero, and authorizes no retry."),
        "authorizes_a_retry": False,
        "detail": detail or {},
    }


def emit(exit_code, attempt_id=None, out_dir=None, lock_sha256=None,
         backend=None, stream=None, detail=None):
    """Write the receipt by both routes and report degradation honestly."""
    stream = stream if stream is not None else sys.stdout
    document = build(exit_code, attempt_id=attempt_id, out_dir=out_dir,
                     lock_sha256=lock_sha256, detail=detail)
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")

    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, RECEIPT_NAME), "wb") as handle:
                handle.write(payload)
        except Exception as exc:  # noqa: BLE001 - cache only
            stream.write("P0_R1_LOCAL_RECEIPT_FAILED=1 %s\n" % exc)

    durable = False
    recursive = None
    if attempt_id and attempt_id != "unknown":
        try:
            import p0_r1_blob_transport_v3 as BLOB_V3
            transport = BLOB_V3.PrivateBlobTransportV3(
                attempt_id, backend=backend)
            transport.upload_and_verify(RECEIPT_NAME, payload)
            recursive = transport.write_recursive_manifest({
                "terminal_receipt": RECEIPT_NAME,
                "shell_exit_code": exit_code,
            })
            durable = True
            stream.write("P0_R1_INFRASTRUCTURE_RECEIPT_DURABLE=1 PREFIX=%s\n"
                         % transport.prefix)
        except Exception as exc:  # noqa: BLE001 - degradation is reportable
            stream.write("P0_R1_DURABILITY_DEGRADED=1 %s: %s\n"
                         % (type(exc).__name__, exc))

    # The secondary route runs unconditionally. Even when Blob succeeded, the
    # complete bytes belong in the captured log so a single store failure at
    # read time is not a second single point of failure.
    try:
        envelope = {RECEIPT_NAME: payload}
        if recursive is not None:
            envelope[recursive["name"]] = recursive["payload"]
        allowed = tuple(sorted(envelope))
        for line in TRANSPORT.encode(
                attempt_id or "p0-r1-infrastructure",
                envelope, allowed=allowed):
            stream.write(line + "\n")
        stream.write("P0_R1_SECONDARY_ENVELOPE_COMPLETE=1\n")
    except Exception as exc:  # noqa: BLE001
        stream.write("P0_R1_SECONDARY_ENVELOPE_FAILED=1 %s\n" % exc)

    stream.write("P0_R1_INFRASTRUCTURE_RECEIPT=%s BYTES=%d SHA256=%s "
                 "DURABLE=%s\n"
                 % (RECEIPT_NAME, len(payload), _sha256(payload),
                    "1" if durable else "0"))
    stream.flush()
    return document, payload, durable


def reemit_existing(path, attempt_id, stream=None):
    """Re-emit the exact receipt already finalized before the shell exits."""
    stream = stream if stream is not None else sys.stdout
    with open(path, "rb") as handle:
        payload = handle.read()
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("the finalized infrastructure receipt is invalid: %s"
                         % exc)
    if document.get("attempt_id") != attempt_id:
        raise ValueError(
            "the finalized receipt binds attempt %r, not %r"
            % (document.get("attempt_id"), attempt_id))
    for line in TRANSPORT.encode(
            attempt_id, {RECEIPT_NAME: payload}, allowed=(RECEIPT_NAME,)):
        stream.write(line + "\n")
    stream.write("P0_R1_FINALIZED_RECEIPT_REEMITTED=1\n")
    stream.flush()
    return document, payload


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "container/p0_r1_infrastructure_receipt_v3.py",
        "routes": ["private_blob", "bounded_console_envelope"],
        "emits_complete_bytes_not_a_hash": True,
        "reports_durability_degradation": True,
        "closes": "G2-08",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--reemit-existing")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--attempt")
    parser.add_argument("--out-dir")
    parser.add_argument("--lock-file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.emit:
        lock_sha = None
        if args.lock_file and os.path.exists(args.lock_file):
            with open(args.lock_file, "rb") as handle:
                lock_sha = _sha256(handle.read())
        backend = None
        if args.dry_run:
            import p0_r1_blob_transport as BLOB
            backend = BLOB.InMemoryBackend()
        emit(args.exit_code, attempt_id=args.attempt, out_dir=args.out_dir,
             lock_sha256=lock_sha, backend=backend)
        return 0

    if args.reemit_existing:
        if not args.attempt:
            print("FAIL: --reemit-existing requires --attempt",
                  file=sys.stderr)
            return 2
        try:
            reemit_existing(args.reemit_existing, args.attempt)
        except (OSError, ValueError) as exc:
            print("P0_R1_EXISTING_RECEIPT_REFUSED=1 %s" % exc,
                  file=sys.stderr)
            return 3
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
