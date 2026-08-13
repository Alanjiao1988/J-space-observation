#!/usr/bin/env python3
"""A create-only, Blob-primary journal whose entries survive a hard kill.

Generation 2 had a journal, and on the production command it wrote nowhere
durable. The model shell invoked the runner without ``--blob``, so the only
sink was ``LocalSequenceSink`` under the container's ephemeral result
directory. Container Apps tears that filesystem down with the replica. The
hard-kill test used a local temporary directory and therefore proved that a
local directory survives a local kill, which was never in doubt.

The second half of the defect is subtler and matters more. Even with a Blob
transport injected, the entries recorded *operation names and row identifiers*
rather than the observations themselves. Recovering "row S1-014 was admitted"
from a killed run tells an operator that something existed and is now gone. The
row is the evidence; its name is not.

Generation 3 therefore fixes three things at once:

* Blob is the **primary** sink on the production path and the container
  filesystem is a cache. If Blob is unreachable the run reports durability
  degradation rather than quietly continuing on local disk.
* Every entry carries the **complete payload** of what it describes -- the
  actual scored row, the reused S2 vector, the raw S4 completion text, the
  exception with its traceback, the smoke transition, the resource observation
  and the cumulative counter snapshot.
* Entries are written **create-only** under monotonically increasing immutable
  sequence numbers and read back immediately. An observation is never
  overwritten, resumed, repaired, replaced or rerun; a duplicate sequence
  number is a defect, not a retry.

Admission is recorded *before* the external call, so a kill during a forward
pass leaves an open admission that the operator can see, and the counter is
never smaller than what actually happened.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCHEMA_VERSION = "study3-p0-r1-durable-journal-v3"

JOURNAL_DIRECTORY = "journal"
MANIFEST_NAME = "p0_r1_journal_manifest_v3.json"

ADMITTED = "admitted"
COMPLETED = "completed"
FAILED = "failed"

# Operation kinds whose admission must precede the external call, because each
# is irreversible the instant it starts.
IRREVERSIBLE_KINDS = (
    "tokenizer_construction",
    "tokenizer_encode",
    "checkpoint_download",
    "model_weight_load",
    "cuda_initialization",
    "prefill_evaluation",
    "generation_call",
)

PAYLOAD_BEARING_KINDS = (
    "scored_row",
    "s2_vector_reuse",
    "s4_raw_completion",
    "exception",
    "smoke_transition",
    "resource_observation",
    "counter_snapshot",
    "parser_call",
)


class JournalDefect(Exception):
    """The journal cannot guarantee that an observation is recoverable."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ")


def sequence_name(index, kind):
    """Immutable, ordered, collision-proof object name for one entry."""
    if not isinstance(index, int) or index < 1:
        raise JournalDefect("a journal sequence number must be >= 1")
    safe = "".join(character if character.isalnum() or character in "-_"
                   else "-" for character in str(kind))[:48]
    return "%s/%06d-%s.json" % (JOURNAL_DIRECTORY, index, safe)


class BlobJournalSink(object):
    """Create-only journal entries in the attempt-bound private prefix."""

    kind = "blob"
    durable = True

    def __init__(self, transport):
        if transport is None:
            raise JournalDefect(
                "the production journal requires a private Blob transport; "
                "the container filesystem is a cache, not the record")
        self.transport = transport
        self.written = []

    @property
    def prefix(self):
        return getattr(self.transport, "prefix", None)

    def write(self, name, payload):
        """Upload create-only and read the bytes back before returning."""
        receipt = self.transport.upload_and_verify(name, payload)
        self.written.append(receipt)
        return receipt

    def read(self, name):
        return self.transport.backend.download("%s%s" % (self.prefix, name))

    def list_names(self):
        prefix = self.prefix or ""
        names = self.transport.backend.list_names(prefix)
        return sorted(name[len(prefix):] if name.startswith(prefix) else name
                      for name in names)


class LocalJournalCache(object):
    """A best-effort local mirror. Never the record of an observation."""

    kind = "local"
    durable = False

    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.written = []

    def write(self, name, payload):
        path = os.path.join(self.out_dir, name.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            raise JournalDefect(
                "journal entry %s already exists; entries are create-only"
                % name)
        with open(path, "wb") as handle:
            handle.write(payload)
        receipt = {"name": name, "bytes": len(payload),
                   "sha256": _sha256(payload)}
        self.written.append(receipt)
        return receipt

    def read(self, name):
        path = os.path.join(self.out_dir, name.replace("/", os.sep))
        with open(path, "rb") as handle:
            return handle.read()

    def list_names(self):
        found = []
        for base, _dirs, files in os.walk(self.out_dir):
            for filename in files:
                full = os.path.join(base, filename)
                found.append(os.path.relpath(full, self.out_dir).replace(
                    os.sep, "/"))
        return sorted(found)


class DurableJournal(object):
    """The append-only record of everything the pilot observed."""

    def __init__(self, attempt_id, sink, cache=None, stream=None,
                 identities=None):
        if not attempt_id:
            raise JournalDefect("the journal must be bound to an attempt id")
        self.attempt_id = attempt_id
        self.sink = sink
        self.cache = cache
        self.stream = stream
        self.identities = dict(identities or {})
        self.index = 0
        self.entries = []
        self.open_admissions = {}
        self.counters = {}
        self.degraded = not getattr(sink, "durable", False)

    # -- writing ---------------------------------------------------------

    def _emit(self, kind, body):
        self.index += 1
        name = sequence_name(self.index, kind)
        entry = {
            "schema_version": SCHEMA_VERSION,
            "sequence": self.index,
            "kind": kind,
            "attempt_id": self.attempt_id,
            "recorded_at": _utc(),
        }
        entry.update(body)
        payload = (json.dumps(entry, indent=2, sort_keys=True,
                              default=str) + "\n").encode("utf-8")
        receipt = self.sink.write(name, payload)

        # Read back immediately: an upload that cannot be re-read is not a
        # durable record, and finding that out now is far cheaper than finding
        # it out during recovery.
        recovered = self.sink.read(name)
        if recovered != payload:
            raise JournalDefect(
                "journal entry %s did not read back byte-for-byte" % name)

        if self.cache is not None:
            try:
                self.cache.write(name, payload)
            except Exception:  # noqa: BLE001 - a cache failure is not a loss
                pass

        record = {"name": name, "sequence": self.index, "kind": kind,
                  "bytes": len(payload), "sha256": receipt.get("sha256")}
        self.entries.append(record)
        if self.stream is not None:
            self.stream.write("P0R1JRN seq=%d kind=%s name=%s sha256=%s\n"
                              % (self.index, kind, name, record["sha256"]))
            self.stream.flush()
        return record

    def start(self, bound_identities=None):
        """Record the attempt and every bound identity before any work."""
        return self._emit("attempt_start", {
            "identities": dict(bound_identities or self.identities),
            "durable_sink": getattr(self.sink, "kind", "unknown"),
            "durability_degraded": self.degraded,
        })

    def admit(self, kind, detail=None):
        """Count and record an irreversible operation *before* it starts."""
        if kind not in IRREVERSIBLE_KINDS:
            raise JournalDefect(
                "%r is not a registered irreversible operation kind" % (kind,))
        self.counters[kind] = self.counters.get(kind, 0) + 1
        record = self._emit("admission", {
            "operation": kind,
            "state": ADMITTED,
            "ordinal": self.counters[kind],
            "detail": detail or {},
        })
        self.open_admissions[record["sequence"]] = {
            "operation": kind, "ordinal": self.counters[kind]}
        return record["sequence"]

    def complete(self, admission, payload=None):
        """Close an admission and store the complete observed payload."""
        opened = self.open_admissions.pop(admission, None)
        if opened is None:
            raise JournalDefect(
                "admission %r is not open; a completion must follow exactly "
                "one admission" % (admission,))
        return self._emit("completion", {
            "operation": opened["operation"],
            "state": COMPLETED,
            "admission_sequence": admission,
            "payload": payload,
        })

    def fail(self, admission, error, payload=None):
        opened = self.open_admissions.pop(admission, None)
        return self._emit("completion", {
            "operation": (opened or {}).get("operation"),
            "state": FAILED,
            "admission_sequence": admission,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "payload": payload,
        })

    def record(self, kind, payload):
        """Store a complete observation. The payload is the evidence."""
        if kind not in PAYLOAD_BEARING_KINDS:
            raise JournalDefect(
                "%r is not a registered payload-bearing kind" % (kind,))
        if payload is None:
            raise JournalDefect(
                "a %r entry must carry its complete payload; a row identifier "
                "is not the row" % (kind,))
        return self._emit(kind, {"payload": payload})

    def record_exception(self, exc, stage=None):
        return self._emit("exception", {"payload": {
            "stage": stage,
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }})

    def interruption(self):
        """Record every admission still open when the run was interrupted."""
        if not self.open_admissions:
            return None
        return self._emit("interruption", {"payload": {
            "open_admissions": [
                {"sequence": sequence, "operation": value["operation"],
                 "ordinal": value["ordinal"]}
                for sequence, value in sorted(self.open_admissions.items())],
            "meaning": "these operations were admitted and never closed; "
                       "their outcome is unknown, which is not zero",
        }})

    # -- manifest --------------------------------------------------------

    def manifest(self, canonical=None, extra=None):
        """Enumerate every journal object recursively, written last.

        Generation 2 enumerated the output directory with ``os.listdir``, which
        returns only top-level names and therefore silently excluded the whole
        nested journal. A manifest that cannot see the evidence cannot verify
        it.
        """
        names = self.sink.list_names()
        journal_objects = sorted(
            name for name in names
            if name.startswith(JOURNAL_DIRECTORY + "/"))
        recorded = sorted(entry["name"] for entry in self.entries)
        missing = [name for name in recorded if name not in journal_objects]
        if missing:
            raise JournalDefect(
                "the store is missing %d recorded journal object(s): %s"
                % (len(missing), ", ".join(missing[:5])))
        unexpected = [name for name in journal_objects if name not in recorded]
        if unexpected:
            raise JournalDefect(
                "the store holds %d journal object(s) this run did not write: "
                "%s" % (len(unexpected), ", ".join(unexpected[:5])))

        sequences = sorted(entry["sequence"] for entry in self.entries)
        if sequences != list(range(1, len(sequences) + 1)):
            raise JournalDefect(
                "the journal sequence is not continuous from 1; a gap means a "
                "lost observation")

        document = {
            "schema_version": SCHEMA_VERSION,
            "attempt_id": self.attempt_id,
            "written_last": True,
            "recursive_enumeration": True,
            "journal_directory": JOURNAL_DIRECTORY,
            "journal_object_count": len(journal_objects),
            "journal_objects": [
                {"name": entry["name"], "sequence": entry["sequence"],
                 "kind": entry["kind"], "bytes": entry["bytes"],
                 "sha256": entry["sha256"]}
                for entry in sorted(self.entries,
                                    key=lambda item: item["sequence"])],
            "canonical_artifacts": list(canonical or ()),
            "open_admissions": len(self.open_admissions),
            "durability_degraded": self.degraded,
            "counters": dict(self.counters),
        }
        if extra:
            document.update(extra)
        payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode(
            "utf-8")
        receipt = self.sink.write(MANIFEST_NAME, payload)
        document["manifest_identity"] = {
            "name": MANIFEST_NAME, "bytes": len(payload),
            "sha256": receipt.get("sha256") or _sha256(payload)}
        return document


def verify_manifest(manifest, sink):
    """Re-read every listed object and refuse any discrepancy.

    Refuses a missing, extra, reordered, overwritten or hash-mismatched
    object. This is the function the CPU-only recovery job runs.
    """
    if not isinstance(manifest, dict):
        raise JournalDefect("the journal manifest must be a document")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise JournalDefect(
            "the journal manifest schema %r is not %r"
            % (manifest.get("schema_version"), SCHEMA_VERSION))
    listed = manifest.get("journal_objects") or []
    present = set(sink.list_names())

    expected_sequence = 1
    verified = []
    for entry in listed:
        name = entry.get("name")
        if name not in present:
            raise JournalDefect("journal object %r is missing from the store"
                                % (name,))
        if entry.get("sequence") != expected_sequence:
            raise JournalDefect(
                "journal object %r has sequence %r where %d was required; a "
                "reordered journal is not a record"
                % (name, entry.get("sequence"), expected_sequence))
        expected_sequence += 1
        payload = sink.read(name)
        if len(payload) != entry.get("bytes"):
            raise JournalDefect(
                "journal object %r is %d bytes, not the recorded %r"
                % (name, len(payload), entry.get("bytes")))
        digest = _sha256(payload)
        if digest != entry.get("sha256"):
            raise JournalDefect(
                "journal object %r hashes to %s, not the recorded %s; the "
                "object was overwritten" % (name, digest, entry.get("sha256")))
        verified.append({"name": name, "bytes": len(payload),
                         "sha256": digest})

    stored_journal = sorted(name for name in present
                            if name.startswith(JOURNAL_DIRECTORY + "/"))
    if stored_journal != sorted(entry["name"] for entry in listed):
        raise JournalDefect(
            "the store holds journal objects the manifest does not list; an "
            "unlisted observation is an unverifiable one")
    return {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": manifest.get("attempt_id"),
        "verified_objects": len(verified),
        "objects": verified,
        "sequence_continuous": True,
        "manifest_written_last": bool(manifest.get("written_last")),
    }


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_journal_v3.py",
        "primary_sink": "private_blob",
        "local_filesystem_is": "cache_only",
        "create_only": True,
        "records_complete_payloads": True,
        "irreversible_kinds": list(IRREVERSIBLE_KINDS),
        "payload_bearing_kinds": list(PAYLOAD_BEARING_KINDS),
        "manifest_enumerates_recursively": True,
        "closes": "G2-07, G2-08",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.self_check:
        import p0_r1_blob_transport as BLOB
        import p0_r1_blob_transport_v3 as BLOB_V3
        transport = BLOB_V3.PrivateBlobTransportV3(
            "p0-r1-journal-v3-self-check", backend=BLOB.InMemoryBackend())
        journal = DurableJournal("p0-r1-journal-v3-self-check",
                                 BlobJournalSink(transport))
        journal.start({"self_check": True})
        admission = journal.admit("prefill_evaluation", {"slice": "smoke"})
        journal.complete(admission, {"logits": [0.1, 0.2], "position": 60})
        journal.record("scored_row", {"row_id": "S1-001", "score": 1,
                                      "raw": "Answer: 7"})
        manifest = journal.manifest(canonical=[])
        verified = verify_manifest(manifest, journal.sink)
        print("P0_R1_JOURNAL_V3_SELF_CHECK=passed OBJECTS=%d SEQUENCES=%d"
              % (verified["verified_objects"], journal.index))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
