"""Study 3 P0-R1 generation-2 durable attempt journal.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
section 8.

Generation 1 called its canonical artifact writer only after every checkpoint
load, the smoke, the extension and the S4 work had completed. Any failure before
that point exited with no result, no receipt, no disposition and no durable
counter snapshot, and row-level exceptions were appended in memory and
immediately re-raised. A crash could therefore make a possibly-started
irreversible operation look like a zero-operation non-attempt.

This module makes the evidence survive the failure instead.

* Every irreversible operation is **admitted before it is called**. The counter
  advances and the journal record lands first, so a crash during the external
  call can only ever over-report, never under-report.
* The journal is an immutable sequence. A sequence number is written once; a
  second write to the same object refuses rather than replacing an observation.
* A restart may inspect and report the journal. It may not resume, repair,
  replace or rerun a scientific operation, and :func:`restart_report` says so in
  the record it produces.
* Any admitted operation with no durable completion is conservatively reported
  as *possibly started*, which is exactly the state that refuses an
  infrastructure retry.

This module performs zero tokenizer, checkpoint, model and GPU operations and
imports only the standard library.
"""

import argparse
import hashlib
import json
import os
import sys

JOURNAL_SCHEMA_VERSION = "study3-p0-r1-attempt-journal-v2"
RECEIPT_SCHEMA_VERSION = "study3-p0-r1-partial-attempt-receipt-v2"
INFRASTRUCTURE_RECEIPT_SCHEMA_VERSION = (
    "study3-p0-r1-infrastructure-attempt-receipt-v2")

JOURNAL_OBJECT_PREFIX = "journal"

#: The irreversible operations that must be counted at admission. Each name is
#: the operation, not the counter: one admission may advance several counters.
IRREVERSIBLE_OPERATIONS = (
    "tokenizer_construction",
    "prompt_encode",
    "checkpoint_download_or_load",
    "prefill",
    "generation_or_decode",
    "parser_call",
    "scored_row",
)

#: Terminal-ish states this module may record. The scientific terminal states
#: stay owned by the model runner; these describe the attempt's durability.
STATE_STARTED = "STUDY3_P0_R1_ATTEMPT_STARTED"
STATE_PARTIAL = "STUDY3_P0_R1_STOPPED_WITH_PARTIAL_RESULT"
STATE_INFRASTRUCTURE = "STUDY3_P0_R1_STOPPED_ON_INFRASTRUCTURE_FAILURE"

#: The counters that must be provably zero before one additional infrastructure
#: attempt may even be considered.
ZERO_OPERATION_COUNTERS = (
    "tokenizer_construction_events",
    "tokenizer_encoded_sequences",
    "distinct_checkpoint_identities_downloaded",
    "model_weight_loads",
    "non_generative_prefill_evaluations",
    "s4_prefill_evaluations",
    "s4_incremental_decode_evaluations",
    "s4_generation_calls",
    "parser_calls",
    "total_scored_rows",
)


class JournalDefect(Exception):
    """A fail-closed durability stop."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True,
                      ensure_ascii=True) + "\n"


class LocalSequenceSink(object):
    """An immutable-sequence sink on a writable local runtime directory."""

    kind = "local-directory"

    def __init__(self, directory):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def _path(self, object_name):
        if "/" in object_name:
            head, tail = object_name.rsplit("/", 1)
            target = os.path.join(self.directory, *head.split("/"))
            os.makedirs(target, exist_ok=True)
            return os.path.join(target, tail)
        return os.path.join(self.directory, object_name)

    def write(self, object_name, payload):
        path = self._path(object_name)
        if os.path.exists(path):
            raise JournalDefect(
                "%s already exists; a journal sequence number is written once "
                "and an earlier observation is never overwritten" % object_name)
        with open(path, "wb") as handle:
            handle.write(payload)
        with open(path, "rb") as handle:
            echoed = handle.read()
        if echoed != payload:
            raise JournalDefect("%s did not read back exactly" % object_name)
        return {"sink": self.kind, "object": object_name,
                "bytes": len(payload), "sha256": _sha256(payload)}

    def read(self, object_name):
        with open(self._path(object_name), "rb") as handle:
            return handle.read()

    def names(self):
        found = []
        for root, _dirs, files in os.walk(self.directory):
            for name in files:
                relative = os.path.relpath(os.path.join(root, name),
                                           self.directory)
                found.append(relative.replace(os.sep, "/"))
        return sorted(found)


class BlobSequenceSink(object):
    """An immutable-sequence sink on the registered private Blob prefix."""

    kind = "private-blob"

    def __init__(self, transport):
        self.transport = transport

    def write(self, object_name, payload):
        target = self.transport.prefix + object_name
        if self.transport.backend.exists(target):
            raise JournalDefect(
                "%s already exists in the attempt prefix; an earlier "
                "observation is never overwritten" % object_name)
        self.transport.backend.upload(target, payload, overwrite=False)
        echoed = self.transport.backend.download(target)
        if echoed != payload:
            raise JournalDefect("%s did not read back exactly" % object_name)
        return {"sink": self.kind, "object": target, "bytes": len(payload),
                "sha256": _sha256(payload)}

    def read(self, object_name):
        return self.transport.backend.download(
            self.transport.prefix + object_name)

    def names(self):
        prefix = self.transport.prefix
        return sorted(name[len(prefix):] for name
                      in self.transport.backend.list_names(prefix))


class AdmissionToken(object):
    """The record of an operation that was counted before it was attempted."""

    __slots__ = ("sequence", "operation", "detail", "closed")

    def __init__(self, sequence, operation, detail):
        self.sequence = sequence
        self.operation = operation
        self.detail = detail
        self.closed = False


class AttemptJournal(object):
    """An append-only, immutable-sequence record of one P0-R1 attempt."""

    def __init__(self, attempt_id, sinks, bound_identities=None,
                 counters=None):
        if not attempt_id:
            raise JournalDefect("an attempt journal requires an attempt id")
        if not sinks:
            raise JournalDefect(
                "an attempt journal requires at least one durable sink; a "
                "journal that cannot be read back is not evidence")
        self.attempt_id = attempt_id
        self.sinks = list(sinks)
        self.counters = counters
        self._sequence = 0
        self._entries = []
        self._open = {}
        self._written = []
        self._mirror_failures = []
        self.bound_identities = dict(bound_identities or {})

    # -- primitives --------------------------------------------------------

    @property
    def sequence(self):
        return self._sequence

    def entries(self):
        return [dict(entry) for entry in self._entries]

    def written_objects(self):
        return [dict(record) for record in self._written]

    def mirror_failures(self):
        """Sinks after the primary that could not be written.

        A remote mirror is redundancy, not the evidence itself. Losing it
        degrades durability and is published as such; it never destroys the
        local journal or the artifacts, which is what generation 1 did.
        """
        return [dict(record) for record in self._mirror_failures]

    def _counter_snapshot(self):
        if self.counters is None:
            return None
        return self.counters.snapshot()

    def record(self, event, payload=None, counters=None):
        """Write one immutable journal entry and read it back."""
        sequence = self._sequence
        self._sequence += 1
        entry = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "attempt_id": self.attempt_id,
            "sequence": sequence,
            "event": event,
            "payload": payload if payload is not None else {},
            "counters": counters if counters is not None
            else self._counter_snapshot(),
        }
        raw = dumps(entry).encode("utf-8")
        object_name = "%s/%06d-%s.json" % (JOURNAL_OBJECT_PREFIX, sequence,
                                           _safe(event))
        for index, sink in enumerate(self.sinks):
            if index == 0:
                # The primary sink is the evidence. If it cannot be written and
                # read back there is no journal, so the attempt refuses here --
                # which is still before any irreversible operation.
                self._written.append(sink.write(object_name, raw))
                continue
            try:
                self._written.append(sink.write(object_name, raw))
            except BaseException as exc:
                self._mirror_failures.append({
                    "sequence": sequence,
                    "event": event,
                    "object": object_name,
                    "sink": getattr(sink, "kind", type(sink).__name__),
                    "exception": type(exc).__name__,
                    "detail": str(exc),
                    "the_primary_journal_and_the_artifacts_are_unaffected": True,
                })
        self._entries.append(entry)
        return entry

    # -- admission ---------------------------------------------------------

    def open_attempt(self, detail=None):
        """Initialize the durable journal before any model library is loaded.

        Section 8 requires that the attempt is already recoverable *before* the
        first irreversible operation, so this is the executor's first action
        after authorization and before any import of a model library.
        """
        if self._entries:
            raise JournalDefect(
                "the attempt journal is already open; an attempt is never "
                "reopened or re-armed")
        return self.record("attempt_opened", payload={
            "state": STATE_STARTED,
            "identities": dict(self.bound_identities),
            "detail": detail or {},
            "opened_before_any_model_library_load": True,
        })

    def admit(self, operation, counter_updates=None, identity_updates=None,
              detail=None):
        """Count and journal an irreversible operation *before* calling it.

        ``counter_updates`` maps a registered counter to its increment and
        ``identity_updates`` maps an identity-cardinality counter to the
        identity being observed. Both are applied here, before the external
        call, so a crash cannot make a possibly-started operation appear as
        zero.
        """
        if operation not in IRREVERSIBLE_OPERATIONS:
            raise JournalDefect(
                "%r is not a registered irreversible operation" % operation)
        if self.counters is not None:
            for name, identity in sorted((identity_updates or {}).items()):
                self.counters.observe_identity(name, identity)
            for name, amount in sorted((counter_updates or {}).items()):
                self.counters.add(name, amount)
        entry = self.record("admitted:%s" % operation, payload={
            "operation": operation,
            "detail": detail or {},
            "counter_updates": dict(counter_updates or {}),
            "identity_updates": dict(identity_updates or {}),
            "counted_before_the_external_call": True,
        })
        token = AdmissionToken(entry["sequence"], operation, detail or {})
        self._open[entry["sequence"]] = token
        return token

    def complete(self, token, outcome=None):
        """Journal the completion of an admitted operation."""
        if not isinstance(token, AdmissionToken):
            raise JournalDefect("a completion requires an admission token")
        if token.closed:
            raise JournalDefect(
                "admission %d was already closed; an observation is never "
                "rewritten" % token.sequence)
        token.closed = True
        self._open.pop(token.sequence, None)
        return self.record("completed:%s" % token.operation, payload={
            "operation": token.operation,
            "admission_sequence": token.sequence,
            "outcome": outcome if outcome is not None else {},
        })

    def failed(self, token, exception):
        if not isinstance(token, AdmissionToken):
            raise JournalDefect("a failure requires an admission token")
        token.closed = True
        self._open.pop(token.sequence, None)
        if self.counters is not None:
            self.counters.add("exceptions_observed", 1)
        return self.record("failed:%s" % token.operation, payload={
            "operation": token.operation,
            "admission_sequence": token.sequence,
            "exception": type(exception).__name__,
            "detail": str(exception),
        })

    def open_admissions(self):
        """Every admitted operation with no durable completion or failure."""
        return [
            {"sequence": token.sequence, "operation": token.operation,
             "detail": token.detail}
            for token in sorted(self._open.values(),
                                key=lambda item: item.sequence)
        ]

    # -- conservative reporting -------------------------------------------

    def conservative_report(self):
        """The most conservative reading of what this attempt may have done."""
        open_admissions = self.open_admissions()
        admitted = {}
        for entry in self._entries:
            if entry["event"].startswith("admitted:"):
                operation = entry["payload"]["operation"]
                admitted[operation] = admitted.get(operation, 0) + 1
        return {
            "attempt_id": self.attempt_id,
            "journal_entries": len(self._entries),
            "admitted_operations": admitted,
            "operations_possibly_started_without_a_durable_completion":
                open_admissions,
            "counters": self._counter_snapshot(),
            "durable_mirror_degraded": bool(self._mirror_failures),
            "mirror_failures": self.mirror_failures(),
            "counter_interpretation": (
                "an admitted operation is counted before the external call, so "
                "a counter may over-report a crashed attempt and can never "
                "under-report one"),
        }


def _safe(event):
    return "".join(character if character.isalnum() or character in "-_"
                   else "-" for character in event)[:64]


def partial_receipt(attempt_id, state, journal, bound_identities=None,
                    exceptions=None, detail=None, scored_rows=None,
                    s4_completions=None, smoke_state=None, resources=None):
    """The canonical stopped/partial receipt written on a recoverable exit."""
    report = journal.conservative_report() if journal is not None else {}
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_partial_attempt_receipt",
        "stage": "P0-R1-MODEL-PILOT",
        "state": state,
        "attempt_id": attempt_id,
        "bound_identities": dict(bound_identities or {}),
        "conservative_report": report,
        "counters": report.get("counters"),
        "exceptions": list(exceptions or []),
        "scored_rows": list(scored_rows or []),
        "scored_row_count": len(scored_rows or []),
        "s4_completions": list(s4_completions or []),
        "s4_completion_count": len(s4_completions or []),
        "smoke_state": smoke_state,
        "resources": list(resources or []),
        "detail": detail or "",
        "every_valid_row_and_partial_result_is_retained": True,
        "no_counter_was_reset_and_no_row_was_repaired": True,
        "authorizes_model_pilot": False,
        "authorizes_retry": False,
    }


def infrastructure_receipt(attempt_id, stage, detail, job_started=True,
                           gpu_allocated=None, execution_name=None,
                           image_digest=None, ready_commit=None,
                           runner_reached=False):
    """A byte-valid receipt for a failure between job start and the runner.

    An allocated job is never silently reported as a zero-event non-attempt:
    the receipt states explicitly that the Azure job started, that the GPU
    workload profile was allocated, and separately that no tokenizer, checkpoint
    or model operation was reached.
    """
    return {
        "schema_version": INFRASTRUCTURE_RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_infrastructure_attempt_receipt",
        "stage": "P0-R1-MODEL-PILOT",
        "state": STATE_INFRASTRUCTURE,
        "attempt_id": attempt_id,
        "failed_stage": stage,
        "detail": detail,
        "azure_job_started": bool(job_started),
        "gpu_workload_allocated": (bool(job_started) if gpu_allocated is None
                                   else bool(gpu_allocated)),
        "python_runner_reached": bool(runner_reached),
        "azure_execution_name": execution_name,
        "image_digest": image_digest,
        "ready_commit": ready_commit,
        "tokenizer_construction_events": 0,
        "tokenizer_encoded_sequences": 0,
        "distinct_checkpoint_identities_downloaded": 0,
        "model_weight_loads": 0,
        "non_generative_prefill_evaluations": 0,
        "s4_prefill_evaluations": 0,
        "s4_incremental_decode_evaluations": 0,
        "s4_generation_calls": 0,
        "parser_calls": 0,
        "total_scored_rows": 0,
        "an_allocated_job_is_not_a_zero_event_non_attempt": True,
        "authorizes_model_pilot": False,
        "authorizes_retry": False,
        "retry_requires_a_separate_operator_decision": True,
    }


def restart_report(attempt_id, journal_entries):
    """A restart may inspect and report the journal. It may not resume it."""
    admitted = [entry for entry in journal_entries
                if entry.get("event", "").startswith("admitted:")]
    closed = {entry["payload"].get("admission_sequence")
              for entry in journal_entries
              if entry.get("event", "").startswith(("completed:", "failed:"))}
    dangling = [entry for entry in admitted
                if entry["sequence"] not in closed]
    return {
        "schema_version": "study3-p0-r1-attempt-restart-report-v2",
        "attempt_id": attempt_id,
        "journal_entries": len(journal_entries),
        "admitted_operations": len(admitted),
        "last_admitted_operation": (admitted[-1]["payload"]["operation"]
                                    if admitted else None),
        "last_admitted_sequence": (admitted[-1]["sequence"]
                                   if admitted else None),
        "operations_possibly_started_without_a_durable_completion":
            [{"sequence": entry["sequence"],
              "operation": entry["payload"]["operation"],
              "detail": entry["payload"].get("detail"),
              "durable_completion_observed": False}
             for entry in dangling],
        "resume_authorized": False,
        "repair_authorized": False,
        "replace_authorized": False,
        "rerun_authorized": False,
        "note": ("a process restart may inspect and report this journal; it "
                 "may not resume, repair, replace or rerun a scientific "
                 "operation"),
    }


def validate_infrastructure_retry(journal_entries=None, receipt=None,
                                  azure_execution_record=None):
    """One further infrastructure attempt, and only on proven zero operations.

    The conservative value of missing or ambiguous evidence is nonzero/unknown,
    so an absent journal, an absent receipt, an absent Azure execution record or
    a dangling admission refuses.
    """
    findings = []
    if receipt is None:
        findings.append(
            "no byte-valid receipt was recovered; a missing receipt is not a "
            "zero-operation proof")
    else:
        if receipt.get("schema_version") not in (
                INFRASTRUCTURE_RECEIPT_SCHEMA_VERSION, RECEIPT_SCHEMA_VERSION):
            findings.append("the recovered receipt has an unknown schema")
        for name in ZERO_OPERATION_COUNTERS:
            value = receipt.get(name)
            if value is None:
                counters = receipt.get("counters") or {}
                value = counters.get(name)
            if value is None:
                findings.append(
                    "the recovered receipt does not carry %s; a missing counter "
                    "is not a zero-operation proof" % name)
            elif value != 0:
                findings.append(
                    "the failed attempt recorded %s=%r; it is not a "
                    "zero-operation attempt and no output-conditioned retry is "
                    "authorized" % (name, value))
    if journal_entries is None:
        findings.append(
            "no durable journal was recovered; the conservative value of "
            "missing evidence is nonzero/unknown")
    else:
        report = restart_report(receipt.get("attempt_id") if receipt else None,
                               journal_entries)
        if report["admitted_operations"]:
            findings.append(
                "the journal admits %d irreversible operation(s); an admitted "
                "operation may have started"
                % report["admitted_operations"])
        if report["operations_possibly_started_without_a_durable_completion"]:
            findings.append(
                "the journal carries admissions with no durable completion")
    if azure_execution_record is None:
        findings.append(
            "no Azure execution record was supplied; job start and GPU "
            "allocation must be established from the platform record")
    if findings:
        raise JournalDefect("; ".join(findings))
    return True


def implementation_identity(root=None):
    path = os.path.abspath(__file__) if root is None else os.path.join(
        root, "studies", "study3", "pilot", "p0_r1", "p0_r1_journal.py")
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": "studies/study3/pilot/p0_r1/p0_r1_journal.py",
        "bytes": len(raw),
        "sha256": _sha256(raw),
        "journal_schema_version": JOURNAL_SCHEMA_VERSION,
        "partial_receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "infrastructure_receipt_schema_version":
            INFRASTRUCTURE_RECEIPT_SCHEMA_VERSION,
    }


def self_check():
    """Exercise the durability guarantees on a scratch sink.

    The image build runs this. It proves inside the image that an admission
    lands before its completion, that a duplicate sequence refuses rather than
    replacing an observation, that a dangling admission is reported as possibly
    started, and that a restart authorizes no scientific continuation.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as scratch:
        journal = AttemptJournal("selfcheck", [LocalSequenceSink(scratch)])
        journal.open_attempt("self check")
        token = journal.admit("prompt_encode", {"row": 1})
        journal.complete(token, {"ok": True})
        journal.admit("scored_row", {"row": 2})

        report = journal.conservative_report()
        dangling = report[
            "operations_possibly_started_without_a_durable_completion"]
        if len(dangling) != 1 or dangling[0]["operation"] != "scored_row":
            raise AssertionError(
                "a dangling admission must be reported as possibly started")

        restart = restart_report("selfcheck", journal.entries())
        for key in ("resume_authorized", "repair_authorized",
                    "replace_authorized", "rerun_authorized"):
            if restart[key] is not False:
                raise AssertionError(
                    "a restart must not authorize %s" % key)

        sink = LocalSequenceSink(scratch)
        names = [name for name in sink.names()
                 if name.startswith(JOURNAL_OBJECT_PREFIX + "/")]
        if len(names) < 4:
            raise AssertionError(
                "every admission and completion must be durable")
        try:
            sink.write(names[0], b"replacement")
        except JournalDefect:
            pass
        else:
            raise AssertionError(
                "a second write to a sequence number must refuse")

    print("P0_R1_JOURNAL_SELF_CHECK=passed OPERATIONS=%d"
          % len(IRREVERSIBLE_OPERATIONS))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--infrastructure-receipt", action="store_true")
    parser.add_argument("--restart-report", action="store_true")
    parser.add_argument("--attempt", required=False)
    parser.add_argument("--stage", default="unknown")
    parser.add_argument("--detail", default="")
    parser.add_argument("--execution-name")
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-commit")
    parser.add_argument("--runner-reached", action="store_true")
    parser.add_argument("--journal-dir")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.self_check:
        return self_check()

    if args.infrastructure_receipt:
        if not args.attempt or not args.out:
            print("--infrastructure-receipt requires --attempt and --out")
            return 2
        document = infrastructure_receipt(
            args.attempt, args.stage, args.detail,
            execution_name=args.execution_name,
            image_digest=args.image_digest, ready_commit=args.ready_commit,
            runner_reached=args.runner_reached)
        payload = dumps(document).encode("utf-8")
        with open(args.out, "wb") as handle:
            handle.write(payload)
        print("P0_R1_INFRASTRUCTURE_RECEIPT=%s SHA256=%s BYTES=%d"
              % (args.out, _sha256(payload), len(payload)))
        return 0

    if args.restart_report:
        if not args.journal_dir or not args.attempt:
            print("--restart-report requires --journal-dir and --attempt")
            return 2
        sink = LocalSequenceSink(args.journal_dir)
        entries = []
        for name in sink.names():
            if not name.startswith(JOURNAL_OBJECT_PREFIX + "/"):
                continue
            entries.append(json.loads(sink.read(name).decode("utf-8")))
        entries.sort(key=lambda entry: entry.get("sequence", -1))
        document = restart_report(args.attempt, entries)
        payload = dumps(document).encode("utf-8")
        if args.out:
            with open(args.out, "wb") as handle:
                handle.write(payload)
        print(payload.decode("utf-8"), end="")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
