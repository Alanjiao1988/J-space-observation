#!/usr/bin/env python3
"""Kill a real subprocess mid-run and recover the row it had already emitted.

Generation 2's hard-kill test wrote to a local temporary directory and killed a
process, which proves that a local directory survives a local kill -- something
that was never in question and is exactly what Container Apps teardown breaks.

This canary is the real thing. A child process:

1. opens a durable journal against the private object store;
2. admits an irreversible operation and completes it with its full payload;
3. emits a complete scored row; and
4. is then killed with an uncatchable signal, with no cleanup, no flush and no
   opportunity to write anything further.

The parent then recovers from the store alone and requires that both the last
open admission and the row's **exact bytes** are present. If the journal had
stored a row identifier rather than the row -- generation 2's behaviour -- this
canary fails, because an identifier does not compare equal to a row.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile

CONTAINER_DIR = os.path.dirname(os.path.abspath(__file__))
P0_R1_DIR = os.path.dirname(CONTAINER_DIR)
sys.path.insert(0, P0_R1_DIR)

CHILD_SOURCE = '''
import json, os, sys, time
sys.path.insert(0, %(p0_r1)r)
import p0_r1_blob_transport_v3 as BLOB_V3
import p0_r1_journal_v3 as JOURNAL

attempt = %(attempt)r
transport = BLOB_V3.PrivateBlobTransportV3(attempt)
journal = JOURNAL.DurableJournal(attempt, JOURNAL.BlobJournalSink(transport))
journal.start({"canary": "hard_kill_v3"})
admission = journal.admit("prefill_evaluation", {"slice": "hardkill"})
journal.complete(admission, {"position": 60, "logits": [0.25]})
journal.record("scored_row", json.loads(%(row)r))
# Admitted and never closed: this is what an interrupted forward pass looks
# like, and the operator must be able to see it.
journal.admit("generation_call", {"slice": "hardkill", "row": "KILL-0002"})
sys.stdout.write("CHILD_READY\\n")
sys.stdout.flush()
time.sleep(120)
'''


def run(attempt_id, stream=None):
    stream = stream if stream is not None else sys.stdout
    row = {
        "row_id": "KILL-0001",
        "role": "RL",
        "surface": "S4",
        "raw_completion": "Answer: 3",
        "parsed": 3,
        "score": 1,
        "filler": "k" * 2048,
    }
    source = CHILD_SOURCE % {
        "p0_r1": P0_R1_DIR,
        "attempt": attempt_id,
        "row": json.dumps(row),
    }
    script = os.path.join(tempfile.mkdtemp(prefix="p0r1-hardkill-"),
                          "child.py")
    with open(script, "w", encoding="utf-8") as handle:
        handle.write(source)

    child = subprocess.Popen(  # noqa: S603 - generated child, fixed interpreter
        [sys.executable, script], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    ready = child.stdout.readline()
    if "CHILD_READY" not in ready:
        child.kill()
        raise SystemExit("the hard-kill child never reached its ready point: "
                         "%r" % ready)

    # SIGKILL on POSIX; the Windows equivalent is equally uncatchable. There is
    # no handler, no atexit, no finally and no flush after this line.
    child.kill()
    child.wait(timeout=60)
    stream.write("P0_R1_G3_HARD_KILL_SIGNAL=%s CHILD_RC=%s\n"
                 % (getattr(signal, "SIGKILL", "TerminateProcess"),
                    child.returncode))

    import p0_r1_blob_transport_v3 as BLOB_V3
    import p0_r1_journal_v3 as JOURNAL

    transport = BLOB_V3.PrivateBlobTransportV3(attempt_id)
    sink = JOURNAL.BlobJournalSink(transport)
    names = [name for name in sink.list_names()
             if name.startswith(JOURNAL.JOURNAL_DIRECTORY + "/")]
    if not names:
        raise SystemExit(
            "nothing survived the hard kill; the journal was not durable")

    recovered_row = None
    open_admission = None
    for name in sorted(names):
        entry = json.loads(sink.read(name).decode("utf-8"))
        if entry.get("kind") == "scored_row":
            recovered_row = entry.get("payload")
        if entry.get("kind") == "admission" and entry.get("state") == \
                JOURNAL.ADMITTED:
            open_admission = entry

    stream.write("P0_R1_G3_HARD_KILL_OBJECTS=%d\n" % len(names))
    if recovered_row != row:
        raise SystemExit(
            "the emitted row's exact bytes did not survive the hard kill; "
            "recovered %r" % (recovered_row,))
    if open_admission is None:
        raise SystemExit(
            "no open admission survived; an interrupted irreversible "
            "operation must remain visible as unknown, not vanish")

    stream.write("P0_R1_G3_HARD_KILL_ROW_RECOVERED=1 ROW_ID=%s\n"
                 % recovered_row["row_id"])
    stream.write("P0_R1_G3_HARD_KILL_OPEN_ADMISSION=%s\n"
                 % open_admission.get("operation"))
    stream.write("P0_R1_G3_HARD_KILL_CANARY=passed\n")
    stream.flush()
    return {"objects": len(names), "row_id": recovered_row["row_id"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args(argv)
    run(args.attempt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
