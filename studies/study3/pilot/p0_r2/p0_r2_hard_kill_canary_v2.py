#!/usr/bin/env python3
"""The P0-R2 hard-kill / open-admission CPU recovery canary (A6).

P0-R1 recorded a hard-kill CPU recovery canary. P0-R2 generation 1 did not
reproduce it, and its own handoff said so: "the recovery path is implemented and
its job shape is pinned, but no generation-1 receipt exists for a killed child."
An implemented recovery path with no receipt is a claim, not evidence, and the
property it claims -- that an operation admitted immediately before an
irreversible step is still visible after the replica dies -- is the single
property that makes an unrepeatable one-shot run safe to attempt at all.

This canary produces the missing receipt. It runs CPU-only, uses managed
identity, writes only synthetic bytes to a disjoint attempt prefix, and never
touches a tokenizer, a checkpoint, a model weight or an accelerator.

The shape is deliberate:

1. a **child process** opens the durable journal and records an admission for a
   synthetic irreversible operation *before* performing it;
2. the child then stores the complete synthetic row payload and a counter
   snapshot -- the payload itself, never merely its name;
3. the child signals readiness and then blocks forever, so the admission it
   opened is still open;
4. the parent kills it with **SIGKILL**, a real hard termination the child
   cannot catch, mask or clean up after;
5. an **independent** CPU recovery process -- a fresh backend, a fresh listing,
   no in-memory state from the child -- reads the private prefix back;
6. recovery must find the open admission and every committed payload byte;
7. the journal sequence must be continuous and create-only;
8. a recursive recovery manifest is written **last** and re-verified;
9. every recovered observation is compared against independently regenerated
   payload bytes, so nothing is ever inferred from a name or a hash alone.

The synthetic row is derived deterministically from the attempt id, so the
recovery side can regenerate the exact bytes it must find without ever having
been told them by the process that died. That is what makes step 9 a proof
rather than a restatement.

One honest note about the journal: ``p0_r2_journal_v1.admit`` accepts only the
registered irreversible operation kinds, all of which name real model
operations. This canary must admit something irreversible without performing
any model operation, so it registers one additional purely synthetic kind
``synthetic_irreversible_operation`` **in its own process only**. No byte of the
committed journal module changes, the production kinds are untouched, and the
receipt records that the extension happened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_blob_transport as BLOB  # noqa: E402
import p0_r2_journal_v1 as JOURNAL  # noqa: E402
import p0_r2_recovery_v1 as RECOVERY  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-hard-kill-canary-v2"
RECEIPT_SCHEMA_VERSION = "study3-p0-r2-hard-kill-recovery-receipt-v2"
STAGE = "STUDY3-P0-R2"

SYNTHETIC_KIND = "synthetic_irreversible_operation"
ATTEMPT_PREFIX = "p0r2-g1-hardkill-canary-"
RECOVERY_MANIFEST_NAME = "p0_r2_hard_kill_recovery_manifest_v2.json"

#: How long the parent waits for the child to become recoverable before it
#: treats the canary as inconclusive. An inconclusive canary is a stop; it is
#: never quietly retried into a pass.
READY_TIMEOUT_SECONDS = 300
DEATH_TIMEOUT_SECONDS = 60


class HardKillCanaryDefect(Exception):
    """The hard-kill recovery property could not be proved."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def register_synthetic_kind() -> bool:
    """Allow one synthetic irreversible kind in this process only."""
    if SYNTHETIC_KIND in JOURNAL.IRREVERSIBLE_KINDS:
        return False
    JOURNAL.IRREVERSIBLE_KINDS = tuple(JOURNAL.IRREVERSIBLE_KINDS) + (
        SYNTHETIC_KIND,)
    return True


def synthetic_row(attempt_id: str, ordinal: int) -> dict:
    """A complete, deterministic synthetic observation.

    Deterministic on purpose: the recovery side regenerates these exact bytes
    from the attempt id alone, so a recovered payload can be compared against
    an independently produced expectation instead of against something the
    dead process asserted.
    """
    seed = hashlib.sha256(
        ("%s|%d" % (attempt_id, ordinal)).encode("utf-8")).hexdigest()
    body = "".join(seed[index % len(seed)] for index in range(1024))
    return {
        "synthetic": True,
        "attempt_id": attempt_id,
        "ordinal": ordinal,
        "row_id": "SYN-%04d" % ordinal,
        "seed": seed,
        "body": body,
        "body_bytes": len(body.encode("utf-8")),
        "body_sha256": _sha256(body.encode("utf-8")),
        "contains_model_bytes": False,
        "contains_corpus_bytes": False,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }


def synthetic_counter_snapshot(attempt_id: str) -> dict:
    return {
        "synthetic": True,
        "attempt_id": attempt_id,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "checkpoint_loads": 0,
        "model_weight_loads": 0,
        "prefills": 0,
        "generations": 0,
        "scored_rows": 0,
        "evidence_rows_added": 0,
        "gpu_allocations": 0,
        "model_operations_performed": 0,
    }


def _backend():
    RECOVERY.assert_model_free()
    return BLOB.AzureManagedIdentityBackend()


# ---------------------------------------------------------------------------
# child
# ---------------------------------------------------------------------------

def run_child(attempt_id: str, ready_path: str, *, rows: int = 2,
              backend=None) -> int:
    """Open an admission, store complete payloads, then block until killed."""
    register_synthetic_kind()
    transport = BLOB.PrivateBlobTransport(attempt_id, backend=backend
                                          or _backend())
    journal = JOURNAL.DurableJournal(
        attempt_id, JOURNAL.BlobJournalSink(transport), stream=sys.stdout,
        identities={"canary": SCHEMA_VERSION, "stage": STAGE,
                    "synthetic": True})
    journal.start()

    journal.record("counter_snapshot", synthetic_counter_snapshot(attempt_id))

    # The admission is written and read back *before* the synthetic
    # irreversible operation begins. That ordering is the whole property.
    admission = journal.admit(SYNTHETIC_KIND, {
        "synthetic": True,
        "why": "a killed replica must still show that this was started",
        "model_operations_performed": 0,
    })
    print("P0R2HK_OPEN_ADMISSION_SEQUENCE=%d" % admission)
    sys.stdout.flush()

    for ordinal in range(1, rows + 1):
        journal.record("scored_row", synthetic_row(attempt_id, ordinal))

    print("P0R2HK_CHILD_RECOVERABLE=1")
    sys.stdout.flush()
    Path(ready_path).write_text(
        json.dumps({"pid": os.getpid(), "admission_sequence": admission,
                    "entries": journal.entries}, indent=2, sort_keys=True),
        encoding="utf-8")

    # Block forever. The admission stays open, no completion is written, and no
    # manifest is sealed -- exactly the state a hard kill produces in
    # production.
    while True:
        time.sleep(3600)


# ---------------------------------------------------------------------------
# recovery
# ---------------------------------------------------------------------------

def recover_independently(attempt_id: str, *, rows: int = 2,
                          backend=None) -> dict:
    """Read the prefix back with no state from the process that died."""
    RECOVERY.assert_model_free()
    sink = backend if backend is not None else _backend()
    if getattr(sink, "credential_kind", None) != "managed-identity":
        raise HardKillCanaryDefect(
            "hard-kill recovery accepts a managed-identity backend only")
    prefix = BLOB.attempt_prefix(attempt_id)
    try:
        names = sorted(sink.list_names(prefix))
    except Exception as exc:  # noqa: BLE001 - any failure is an ambiguity
        raise HardKillCanaryDefect(
            "the private listing failed (%s); an error is never an absence"
            % exc)
    if not names:
        raise HardKillCanaryDefect(
            "the attempt prefix %s is empty; the child wrote nothing durable "
            "and the hard-kill property is disproved, not waived" % prefix)

    objects = []
    entries = {}
    for name in names:
        relative = name[len(prefix):] if name.startswith(prefix) else name
        payload = sink.download(name)
        record = {"name": relative, "bytes": len(payload),
                  "sha256": _sha256(payload)}
        objects.append(record)
        if relative.startswith(JOURNAL.JOURNAL_DIRECTORY + "/"):
            document = json.loads(payload.decode("utf-8"))
            sequence = document.get("sequence")
            if sequence in entries:
                raise HardKillCanaryDefect(
                    "sequence %r appears twice; the journal is not create-only"
                    % (sequence,))
            expected_name = JOURNAL.sequence_name(sequence, document.get("kind"))
            if expected_name != relative:
                raise HardKillCanaryDefect(
                    "%s does not match its sequence and kind" % relative)
            entries[sequence] = {"document": document, "record": record}

    sequences = sorted(entries)
    if sequences != list(range(1, len(sequences) + 1)):
        raise HardKillCanaryDefect(
            "the recovered journal sequence %r is not continuous from 1; a gap "
            "is a lost observation" % (sequences,))

    admissions = {sequence: item["document"] for sequence, item in entries.items()
                  if item["document"].get("kind") == "admission"}
    completions = {item["document"].get("admission_sequence")
                   for item in entries.values()
                   if item["document"].get("kind") == "completion"}
    open_admissions = sorted(set(admissions) - completions)
    if len(open_admissions) != 1:
        raise HardKillCanaryDefect(
            "expected exactly one open admission after a hard kill, recovered "
            "%d: %r" % (len(open_admissions), open_admissions))
    open_sequence = open_admissions[0]
    open_document = admissions[open_sequence]
    if open_document.get("state") != JOURNAL.ADMITTED \
            or open_document.get("operation") != SYNTHETIC_KIND:
        raise HardKillCanaryDefect(
            "the recovered open admission is not the synthetic admission")

    # Regenerate the payloads independently and require byte agreement. This is
    # the step that makes the recovery a recovery of observations rather than
    # of names.
    recovered_rows = []
    by_ordinal = {}
    for sequence, item in sorted(entries.items()):
        document = item["document"]
        if document.get("kind") != "scored_row":
            continue
        payload = document.get("payload") or {}
        by_ordinal[payload.get("ordinal")] = payload
    for ordinal in range(1, rows + 1):
        expected = synthetic_row(attempt_id, ordinal)
        actual = by_ordinal.get(ordinal)
        if actual is None:
            raise HardKillCanaryDefect(
                "synthetic row %d was not recovered" % ordinal)
        expected_bytes = json.dumps(expected, sort_keys=True).encode("utf-8")
        actual_bytes = json.dumps(actual, sort_keys=True).encode("utf-8")
        if expected_bytes != actual_bytes:
            raise HardKillCanaryDefect(
                "recovered synthetic row %d does not equal the independently "
                "regenerated row" % ordinal)
        recovered_rows.append({
            "ordinal": ordinal,
            "row_id": actual.get("row_id"),
            "payload_bytes": len(actual_bytes),
            "payload_sha256": _sha256(actual_bytes),
            "body_sha256": actual.get("body_sha256"),
            "byte_exact_against_independent_regeneration": True,
        })

    snapshots = [item["document"].get("payload") for item in entries.values()
                 if item["document"].get("kind") == "counter_snapshot"]
    if not snapshots:
        raise HardKillCanaryDefect("no counter snapshot was recovered")

    manifest_present_before_recovery = any(
        item["name"].endswith(JOURNAL.MANIFEST_NAME)
        or item["name"].endswith(BLOB.MANIFEST_NAME)
        or item["name"] == RECOVERY_MANIFEST_NAME for item in objects)
    if manifest_present_before_recovery:
        raise HardKillCanaryDefect(
            "a manifest already exists; the child was not killed mid-attempt "
            "and this canary would prove nothing")

    # The recursive recovery manifest is written LAST, after every object has
    # been read back, and it enumerates the whole prefix recursively.
    manifest = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "stage": STAGE,
        "attempt_id": attempt_id,
        "prefix": prefix,
        "written_last": True,
        "recursive_enumeration": True,
        "object_count": len(objects),
        "objects": sorted(objects, key=lambda item: item["name"]),
        "journal_entry_count": len(entries),
        "journal_sequence_continuous": True,
        "journal_is_create_only": True,
        "open_admission_sequence": open_sequence,
        "open_admission_operation": SYNTHETIC_KIND,
        "recovered_rows": recovered_rows,
        "counter_snapshots": snapshots,
        "no_observation_overwritten": True,
        "no_observation_inferred_from_name_or_hash_alone": True,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")
    sink.upload(prefix + RECOVERY_MANIFEST_NAME, payload, overwrite=False)
    readback = sink.download(prefix + RECOVERY_MANIFEST_NAME)
    if readback != payload:
        raise HardKillCanaryDefect(
            "the recovery manifest did not read back byte-for-byte")

    after = sorted(sink.list_names(prefix))
    if len(after) != len(names) + 1:
        raise HardKillCanaryDefect(
            "the prefix changed unexpectedly during recovery: %d objects "
            "before, %d after" % (len(names), len(after)))
    if (prefix + RECOVERY_MANIFEST_NAME) not in after:
        raise HardKillCanaryDefect("the recovery manifest is not in the prefix")

    manifest["manifest_identity"] = {
        "name": RECOVERY_MANIFEST_NAME,
        "bytes": len(payload),
        "sha256": _sha256(payload),
    }
    manifest["prefix_object_names_after_recovery"] = [
        name[len(prefix):] if name.startswith(prefix) else name
        for name in after]
    return manifest


# ---------------------------------------------------------------------------
# parent
# ---------------------------------------------------------------------------

def run_canary(attempt_id: str, *, rows: int = 2, python=None,
               module=None) -> dict:
    """Start the child, kill it hard, then recover independently."""
    if not attempt_id.startswith(ATTEMPT_PREFIX):
        raise HardKillCanaryDefect(
            "the hard-kill canary attempt id must begin with %r, got %r"
            % (ATTEMPT_PREFIX, attempt_id))
    RECOVERY.assert_model_free()
    JOURNAL.validate_attempt_id(attempt_id)

    ready = Path(os.environ.get("P0_R2_RUNTIME_ROOT", "/tmp")) / (
        "%s.ready.json" % attempt_id)
    if ready.exists():
        raise HardKillCanaryDefect(
            "the readiness file already exists; this canary is create-only")
    ready.parent.mkdir(parents=True, exist_ok=True)

    command = [python or sys.executable, module or str(Path(__file__).resolve()),
               "--child", "--attempt", attempt_id, "--ready-file", str(ready),
               "--rows", str(rows)]
    child = subprocess.Popen(  # noqa: S603 - fixed executable
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    deadline = time.time() + READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        if ready.exists():
            break
        if child.poll() is not None:
            raise HardKillCanaryDefect(
                "the child exited with %r before it became recoverable; the "
                "canary is inconclusive and is not retried into a pass"
                % child.returncode)
        time.sleep(1)
    else:
        child.kill()
        raise HardKillCanaryDefect(
            "the child did not become recoverable within %d seconds"
            % READY_TIMEOUT_SECONDS)

    handshake = json.loads(ready.read_text(encoding="utf-8"))

    # A real hard termination: SIGKILL cannot be caught, blocked or handled, so
    # the child gets no chance to close its admission or seal a manifest.
    os.kill(child.pid, signal.SIGKILL)
    killed_at = time.time()
    try:
        child.wait(timeout=DEATH_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise HardKillCanaryDefect(
            "the child survived SIGKILL; this is not a hard termination")
    child_log = child.stdout.read() if child.stdout else ""
    returncode = child.returncode
    if returncode != -int(signal.SIGKILL):
        raise HardKillCanaryDefect(
            "the child exited %r rather than by SIGKILL; the kill was not the "
            "hard termination this canary requires" % returncode)

    recovery = recover_independently(attempt_id, rows=rows)

    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "stage": STAGE,
        "canary": "hard-kill-open-admission-cpu-recovery",
        "attempt_id": attempt_id,
        "prefix": recovery["prefix"],
        "outcome": "PASS",
        "child": {
            "pid": handshake.get("pid"),
            "declared_admission_sequence": handshake.get("admission_sequence"),
            "entries_written_before_kill": handshake.get("entries"),
            "log": child_log,
            "log_bytes": len(child_log.encode("utf-8")),
            "log_sha256": _sha256(child_log.encode("utf-8")),
        },
        "kill": {
            "classification": "HARD_TERMINATION_SIGKILL",
            "signal": int(signal.SIGKILL),
            "signal_name": "SIGKILL",
            "catchable": False,
            "child_returncode": returncode,
            "killed_at_epoch": killed_at,
            "child_was_given_no_chance_to_clean_up": True,
        },
        "recovery": recovery,
        "recovery_is_independent_process_state": True,
        "open_admission_recovered": True,
        "all_committed_payload_bytes_recovered": True,
        "journal_sequence_continuous_and_create_only": True,
        "recursive_manifest_written_last": True,
        "no_observation_overwritten_or_inferred": True,
        "synthetic_kind_registered_at_runtime": SYNTHETIC_KIND,
        "journal_module_bytes_unchanged": True,
        "accelerator_requested": False,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "prefills": 0,
        "generations": 0,
        "scored_rows": 0,
        "gpu_operations": 0,
        "gpu_allocations": 0,
        "model_operations_performed": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_hard_kill_canary_v2.py",
        "stage": STAGE,
        "attempt_prefix": ATTEMPT_PREFIX,
        "synthetic_kind": SYNTHETIC_KIND,
        "kill_signal": "SIGKILL",
        "kill_is_catchable": False,
        "recovery_is_independent": True,
        "recovery_manifest_name": RECOVERY_MANIFEST_NAME,
        "writes_model_or_corpus_bytes": False,
        "requests_accelerator": False,
        "waivable": False,
        "reproduces": "the P0-R1 hard-kill CPU recovery canary P0-R2 omitted",
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--child", action="store_true")
    mode.add_argument("--recover-only", action="store_true")
    parser.add_argument("--attempt")
    parser.add_argument("--ready-file")
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.child:
        if not args.attempt or not args.ready_file:
            parser.error("--child requires --attempt and --ready-file")
        return run_child(args.attempt, args.ready_file, rows=args.rows) or 0

    if not args.attempt:
        parser.error("name --attempt")

    try:
        if args.recover_only:
            receipt = recover_independently(args.attempt, rows=args.rows)
        else:
            receipt = run_canary(args.attempt, rows=args.rows)
    except (HardKillCanaryDefect, RECOVERY.RecoveryDefect,
            JOURNAL.JournalDefect, BLOB.BlobTransportDefect) as exc:
        print("P0_R2_HARD_KILL_CANARY_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    print("P0_R2_HARD_KILL_CANARY_COMPLETE=1")
    print("P0_R2_HARD_KILL_OPEN_ADMISSION_RECOVERED=1")
    print("P0_R2_HARD_KILL_RECOVERY_BYTE_EXACT=1")
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
