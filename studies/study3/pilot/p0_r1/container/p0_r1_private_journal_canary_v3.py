#!/usr/bin/env python3
"""Exercise the real private object store as the primary journal sink.

This canary runs inside the virtual network, authenticates with the resource's
user-assigned managed identity, and writes a complete journal -- admissions,
completions with full payloads, a scored row, a counter snapshot and the
recursive manifest written last -- to the real account under a unique
generation-3 prefix. It then reads every object back through the recovery path
and verifies bytes, digests, sequence continuity and manifest-last status.

Nothing about it is a stand-in. The generation-2 build passed its transport
gate against an in-memory backend and shipped an image with no client for this
account at all; that failure is the reason this canary exists and the reason it
must run on the real path before any lock is created.

It constructs no tokenizer, downloads no checkpoint, loads no weights and
allocates no accelerator.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

CONTAINER_DIR = os.path.dirname(os.path.abspath(__file__))
P0_R1_DIR = os.path.dirname(CONTAINER_DIR)
sys.path.insert(0, P0_R1_DIR)

import p0_r1_blob_transport_v3 as BLOB_V3  # noqa: E402
import p0_r1_journal_v3 as JOURNAL  # noqa: E402
import p0_r1_recovery_v3 as RECOVERY  # noqa: E402

# A row large enough that a truncating sink cannot accidentally pass.
ROW_PAYLOAD_BYTES = 4096


def run(attempt_id, backend=None, stream=None):
    stream = stream if stream is not None else sys.stdout
    transport = BLOB_V3.PrivateBlobTransportV3(attempt_id, backend=backend)
    sink = JOURNAL.BlobJournalSink(transport)
    journal = JOURNAL.DurableJournal(attempt_id, sink, stream=None)

    stream.write("P0_R1_G3_JOURNAL_PREFIX=%s\n" % transport.prefix)

    journal.start({"canary": "private_journal_v3", "attempt_id": attempt_id})

    admission = journal.admit("prefill_evaluation",
                              {"slice": "canary", "position": 60})
    journal.complete(admission, {
        "position": 60,
        "restricted_logits": [round(0.01 * index, 4) for index in range(10)],
        "note": "a completion stores the observation, not only its name",
    })

    row = {
        "row_id": "CANARY-0001",
        "role": "RT",
        "surface": "S1",
        "raw_completion": "Answer: 7",
        "parsed": 7,
        "score": 1,
        "filler": "x" * ROW_PAYLOAD_BYTES,
    }
    journal.record("scored_row", row)
    journal.record("counter_snapshot", {"scored_rows": 1,
                                        "model_operations_performed": 0})

    manifest = journal.manifest(canonical=[])
    stream.write("P0_R1_G3_JOURNAL_OBJECTS=%d\n"
                 % manifest["journal_object_count"])
    stream.write("P0_R1_G3_JOURNAL_MANIFEST=%s SHA256=%s BYTES=%d\n"
                 % (manifest["manifest_identity"]["name"],
                    manifest["manifest_identity"]["sha256"],
                    manifest["manifest_identity"]["bytes"]))

    receipt, payloads = RECOVERY.recover(attempt_id, backend=backend,
                                         stream=stream)
    recovered_row = None
    for name, payload in payloads.items():
        if not name.startswith("journal"):
            continue
        try:
            entry = json.loads(payload.decode("utf-8"))
        except ValueError:
            continue
        if entry.get("kind") == "scored_row":
            recovered_row = entry.get("payload")

    if recovered_row != row:
        raise SystemExit(
            "the scored row did not survive the round trip byte-for-byte; a "
            "journal that stores a row id instead of the row is not evidence")

    for entry in manifest["journal_objects"]:
        stream.write("JOURNAL=%s BYTES=%d SHA256=%s\n"
                     % (entry["name"], entry["bytes"], entry["sha256"]))

    stream.write("P0_R1_G3_PRIVATE_JOURNAL_CANARY=passed OBJECTS=%d "
                 "ROW_BYTES=%d\n"
                 % (receipt["journal_objects_verified"],
                    len(json.dumps(recovered_row))))
    stream.flush()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    backend = None
    if args.dry_run:
        import p0_r1_blob_transport as BLOB
        backend = BLOB.InMemoryBackend()
    run(args.attempt, backend=backend)
    return 0


if __name__ == "__main__":
    sys.exit(main())
