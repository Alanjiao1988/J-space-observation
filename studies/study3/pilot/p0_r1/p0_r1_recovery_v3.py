#!/usr/bin/env python3
"""CPU-only, managed-identity recovery of a P0-R1 attempt from private Blob.

The generation-2 handoff told the operator to recover results by constructing
``ManagedIdentityCredential`` on their own workstation. That instruction cannot
work, for two independent reasons:

* a workstation is not the Azure resource and does not hold its user-assigned
  managed identity, so the credential has nothing to present; and
* the results account has public network access disabled and is reachable only
  through a private endpoint inside the virtual network, so even a valid token
  would arrive on a route the account refuses.

The generation-2 authority had already required a separately named CPU-only
managed-identity recovery job for exactly this case. Generation 2 shipped no
such job, which means a completed GPU pilot could have written perfect evidence
that no one outside the network could read.

This module is that job's payload. It is emphatically **not** a replay and
**not** a model retry: it accepts an attempt identity and the active lock,
reads the immutable manifest and every object it lists through the private
route, verifies bytes, digests, counts, sequence continuity, attempt binding
and manifest-last status, and then re-emits the verified bytes through the same
bounded console envelope so the operator can reconstruct them from the captured
execution log alone.

It constructs no tokenizer, downloads no checkpoint, loads no weights,
allocates no accelerator, draws no seed and touches no bank.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_blob_transport as BLOB  # noqa: E402
import p0_r1_blob_transport_v3 as BLOB_V3  # noqa: E402
import p0_r1_journal_v3 as JOURNAL  # noqa: E402
import p0_r1_transport as TRANSPORT  # noqa: E402
import p0_r1_transport_v3 as TRANSPORT_V3  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-recovery-v3"

RECOVERY_RECEIPT_NAME = "p0_r1_recovery_receipt_v3.json"

FORBIDDEN_MODULES = ("transformers", "torch")

NAMES_MARKER = "P0_R1_RECOVERY_NAMES="


class RecoveryDefect(Exception):
    """The stored evidence could not be verified. Nothing is repaired."""


def assert_model_free():
    """Refuse to run if a model library is present in this process."""
    imported = [name for name in FORBIDDEN_MODULES if name in sys.modules]
    if imported:
        raise RecoveryDefect(
            "the recovery job imported %s; recovery is model-free by "
            "construction and is never a retry" % ", ".join(sorted(imported)))


def _partial_journal_payloads(attempt_id, sink):
    """Recover a killed attempt that never reached either final manifest."""
    names = sorted(name for name in sink.list_names()
                   if name.startswith(JOURNAL.JOURNAL_DIRECTORY + "/"))
    if not names:
        raise RecoveryDefect(
            "the attempt has neither a final manifest nor journal objects")
    payloads = {}
    expected = 1
    objects = []
    for name in names:
        raw = sink.read(name)
        try:
            entry = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise RecoveryDefect(
                "partial journal object %r is not readable JSON: %s"
                % (name, exc))
        if entry.get("attempt_id") != attempt_id:
            raise RecoveryDefect(
                "partial journal object %r belongs to attempt %r"
                % (name, entry.get("attempt_id")))
        if entry.get("sequence") != expected:
            raise RecoveryDefect(
                "partial journal sequence jumps from %d at %r"
                % (expected, name))
        expected += 1
        payloads[name.replace("/", "__")] = raw
        objects.append({
            "name": name, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    return payloads, objects


def recover(attempt_id, backend=None, lock_sha256=None, stream=None):
    """Read, verify and re-emit an attempt's complete durable evidence."""
    assert_model_free()
    stream = stream if stream is not None else sys.stdout

    transport = BLOB_V3.PrivateBlobTransportV3(attempt_id, backend=backend)
    sink = JOURNAL.BlobJournalSink(transport)

    raw = None
    try:
        raw = sink.read(JOURNAL.MANIFEST_NAME)
    except Exception:  # a hard kill legitimately has no final manifest
        raw = None

    if raw is None:
        payloads, objects = _partial_journal_payloads(attempt_id, sink)
        verified = {
            "verified_objects": len(objects),
            "objects": objects,
            "sequence_continuous": True,
            "manifest_written_last": False,
        }
        canonical = []
        recursive = None
        partial = True
    else:
        partial = False
        recursive_defect = None
        try:
            recursive = transport.verify_recursive_manifest()
        except BLOB.BlobTransportDefect as exc:
            recursive = None
            recursive_defect = str(exc)
            partial = True
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise RecoveryDefect(
                "the journal manifest is not readable JSON: %s" % exc)

        if manifest.get("attempt_id") != attempt_id:
            raise RecoveryDefect(
                "the stored manifest binds attempt %r, not the requested %r"
                % (manifest.get("attempt_id"), attempt_id))

        try:
            verified = JOURNAL.verify_manifest(manifest, sink)
        except JOURNAL.JournalDefect as exc:
            raise RecoveryDefect(str(exc))

        payloads = {JOURNAL.MANIFEST_NAME: raw}
        for entry in verified["objects"]:
            payloads[entry["name"].replace("/", "__")] = sink.read(
                entry["name"])

        canonical = []
        for name in manifest.get("canonical_artifacts") or ():
            if not name:
                continue
            try:
                payloads[name] = sink.read(name)
                canonical.append(name)
            except Exception as exc:  # noqa: BLE001
                raise RecoveryDefect(
                    "the manifest lists canonical artifact %r which cannot be "
                    "read: %s" % (name, exc))
        if recursive is not None:
            payloads[BLOB_V3.MANIFEST_NAME] = recursive["payload"]

    emitted_name_map = {}
    for entry in verified["objects"]:
        emitted_name_map[entry["name"].replace("/", "__")] = entry["name"]
    for name in canonical:
        emitted_name_map[name] = name
    if raw is not None:
        emitted_name_map[JOURNAL.MANIFEST_NAME] = JOURNAL.MANIFEST_NAME
    if recursive is not None:
        emitted_name_map[BLOB_V3.MANIFEST_NAME] = BLOB_V3.MANIFEST_NAME

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": attempt_id,
        "prefix": transport.prefix,
        "journal_objects_verified": verified["verified_objects"],
        "sequence_continuous": verified["sequence_continuous"],
        "manifest_written_last": (
            verified["manifest_written_last"] and bool(recursive)),
        "recursive_manifest_verified": bool(recursive),
        "recursive_objects_verified": (
            recursive["verified_objects"] if recursive else 0),
        "recursive_manifest_defect": (
            recursive_defect if raw is not None else
            "the attempt ended before either final manifest"),
        "partial_attempt": partial,
        "canonical_artifacts": canonical,
        "lock_sha256": lock_sha256,
        "is_a_replay": False,
        "is_a_model_retry": False,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_allocated": False,
        "authorizes_a_retry": False,
        "total_recovered_bytes": sum(len(v) for v in payloads.values()),
        "objects": verified["objects"],
        "emitted_name_map": emitted_name_map,
    }

    stream.write("P0_R1_RECOVERY_BEGIN=1 ATTEMPT=%s PREFIX=%s\n"
                 % (attempt_id, transport.prefix))
    allowed = tuple(sorted(payloads)) + (RECOVERY_RECEIPT_NAME,)
    # A recovery envelope carries journal object names, which are discovered
    # from the manifest and so are not the fixed replay allow-list. The reader
    # cannot validate a name it was never told about, so the allow-list is
    # published on its own line ahead of the envelope. It is an assertion of
    # what follows, not a grant: every name is still validated on decode, and a
    # name absent from this line is refused.
    stream.write("%s%s\n" % (NAMES_MARKER, " ".join(allowed)))
    body = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")
    payloads[RECOVERY_RECEIPT_NAME] = body
    for line in TRANSPORT.encode(attempt_id, payloads, allowed=allowed):
        stream.write(line + "\n")
    stream.write("P0_R1_RECOVERY_COMPLETE=1 OBJECTS=%d BYTES=%d\n"
                 % (len(payloads), receipt["total_recovered_bytes"]))
    stream.flush()
    return receipt, payloads


def declared_names(log_text):
    """Read the allow-list a recovery run published ahead of its envelope.

    Returns the last declaration in the log, so a captured log containing more
    than one recovery run decodes against the run whose envelope it ends with.
    """
    found = None
    for line in log_text.splitlines():
        line = line.strip()
        if line.startswith(NAMES_MARKER):
            found = tuple(part for part in
                          line[len(NAMES_MARKER):].split(" ") if part)
    if not found:
        raise RecoveryDefect(
            "the log carries no %s declaration, so its envelope cannot be "
            "decoded" % NAMES_MARKER)
    return found


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_recovery_v3.py",
        "cpu_only": True,
        "credential": "user-assigned managed identity, inside the VNet",
        "is_a_replay": False,
        "is_a_model_retry": False,
        "verifies": ["bytes", "sha256", "counts", "sequence_continuity",
                     "attempt_binding", "manifest_last"],
        "secondary_route": "bounded complete-byte console envelope",
        "closes": "G2-09",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--decode-log", action="store_true")
    parser.add_argument("--log")
    parser.add_argument("--out-dir")
    parser.add_argument("--attempt")
    parser.add_argument("--lock-file")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.self_check:
        backend = BLOB.InMemoryBackend()
        attempt = "p0-r1-recovery-v3-self-check"
        transport = BLOB_V3.PrivateBlobTransportV3(attempt, backend=backend)
        journal = JOURNAL.DurableJournal(attempt,
                                         JOURNAL.BlobJournalSink(transport))
        journal.start({"self_check": True})
        token = journal.admit("prefill_evaluation", {"slice": "smoke"})
        journal.complete(token, {"position": 60, "logits": [0.5]})
        journal.record("scored_row", {"row_id": "S1-001", "raw": "Answer: 7"})
        journal.manifest(canonical=[])
        transport.write_recursive_manifest({"self_check": True})
        receipt, payloads = recover(attempt, backend=backend)
        print("P0_R1_RECOVERY_V3_SELF_CHECK=passed OBJECTS=%d"
              % receipt["journal_objects_verified"])
        return 0

    if args.decode_log:
        if not args.log or not args.out_dir or not args.attempt:
            print("FAIL: --decode-log requires --log, --out-dir and --attempt",
                  file=sys.stderr)
            return 2
        try:
            with open(args.log, "r", encoding="utf-8",
                      errors="replace") as handle:
                text = handle.read()
            allowed = declared_names(text)
            recovered = TRANSPORT_V3.recover(
                text, attempt_id=args.attempt, allowed=allowed)
            written = TRANSPORT.write_recovered(
                recovered, args.out_dir, allowed=allowed)
        except (OSError, RecoveryDefect, TRANSPORT.TransportDefect) as exc:
            print("P0_R1_RECOVERY_LOG_REFUSED=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        for entry in written:
            print("RECOVERED=%s BYTES=%d SHA256=%s"
                  % (entry["name"], entry["bytes"], entry["sha256"]))
        print("P0_R1_RECOVERY_LOG_DECODED=1")
        return 0

    if args.recover:
        if not args.attempt:
            print("FAIL: --recover requires --attempt", file=sys.stderr)
            return 2
        lock_sha = None
        if args.lock_file:
            import hashlib
            with open(args.lock_file, "rb") as handle:
                lock_sha = hashlib.sha256(handle.read()).hexdigest()
        try:
            recover(args.attempt, lock_sha256=lock_sha)
        except RecoveryDefect as exc:
            print("P0_R1_RECOVERY_REFUSED=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
