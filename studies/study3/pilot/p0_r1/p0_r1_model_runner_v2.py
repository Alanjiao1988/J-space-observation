"""The Study 3 P0-R1 generation-2 model-pilot runner. Model-free by construction.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
sections 5 and 8, over the operative
``studies/study3/prompts/study3_v0_6_p0_r1_authority.md``.

Generation 1 wrote every artifact only after the full three-role loop returned
and re-raised the first row-level exception out of the executor. A failure at
any point therefore destroyed every valid row already produced, every raw S4
completion, every observed exception and every cumulative counter, and left the
attempt with no byte-valid receipt at all. It also advanced counters *after* the
call they described, so an interruption under-reported operations that had in
fact been started.

This runner closes that. It owns three things generation 1 did not have:

* a durable attempt journal that is initialized and readable back **before** any
  model library is imported;
* a mutable partial-result collector that lives outside the executor, so the
  rows already produced survive the executor's own stack;
* a top-level exception boundary that, on *any* exception including a hard one,
  writes the conservative counters, every partial row, every completion, every
  exception and a canonical stopped receipt before the process exits.

No scoring rule, cap, allocation, smoke criterion or terminal-state meaning is
changed. ``STUDY3_P0_R1_STOPPED_WITH_PARTIAL_RESULT`` is not a re-interpretation
of an existing state; it is the state generation 1 simply had no way to emit.

This module performs zero tokenizer, checkpoint, model and GPU operations and
names no model library. Every byte that can touch a checkpoint stays in the
``execution`` subpackage, behind the authorization check that runs first.
"""

import argparse
import hashlib
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

sys.path.insert(0, P0_R1_DIR)

import p0_r1_execution_lock_v2 as LOCK  # noqa: E402
import p0_r1_journal as JOURNAL  # noqa: E402
import p0_r1_model_runner as RUNNER  # noqa: E402
import p0_r1_runtime_binding as RUNTIME  # noqa: E402
import p0_r1_summarize as SUMMARIZE  # noqa: E402
from p0_r1_counters import P0R1Counters  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-model-pilot-result-v2"
RECEIPT_SCHEMA_VERSION = "study3-p0-r1-model-pilot-receipt-v2"

RESULT_NAME = "p0_r1_model_pilot_result.json"
RECEIPT_NAME = "p0_r1_model_pilot_receipt.json"
COUNTERS_NAME = "p0_r1_model_pilot_counters.json"
DISPOSITION_NAME = "P0_R1_MODEL_PILOT_DISPOSITION.md"
JOURNAL_NAME = "p0_r1_model_pilot_journal.json"

PILOT_ARTIFACTS = (RESULT_NAME, RECEIPT_NAME, COUNTERS_NAME, DISPOSITION_NAME,
                   JOURNAL_NAME)

#: Reused unchanged from the registered generation-1 runner.
STATE_COMPLETE = RUNNER.STATE_COMPLETE
STATE_STOPPED_ON_SMOKE = RUNNER.STATE_STOPPED_ON_SMOKE

#: The state generation 1 could not emit: a run that stopped with real partial
#: results that must be preserved exactly as observed.
STATE_STOPPED_WITH_PARTIAL_RESULT = JOURNAL.STATE_PARTIAL

REPLAY_RECEIPT_SCHEMAS = RUNTIME.REPLAY_RECEIPT_SCHEMAS


class ExecutionRefused(RUNNER.ExecutionRefused):
    """A fail-closed generation-2 execution stop."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True,
                      ensure_ascii=True) + "\n"


class PartialResults(object):
    """Every observation produced so far, owned outside the executor's stack.

    The executor appends here as it goes, so an exception inside the executor
    cannot take the rows with it.
    """

    def __init__(self):
        self.scored_rows = []
        self.s4_completions = []
        self.exceptions = []
        self.resources = []
        self.smoke_passed = False
        self.smoke_closed = False
        self.stop_reason = None

    def snapshot(self):
        return {
            "scored_rows": list(self.scored_rows),
            "s4_completions": list(self.s4_completions),
            "exceptions": list(self.exceptions),
            "resources": list(self.resources),
            "smoke_passed": self.smoke_passed,
            "smoke_closed": self.smoke_closed,
            "stop_reason": self.stop_reason,
        }


def validate_execution_authorization(authorization, root=None,
                                     lock_bytes=None, receipt_bytes=None,
                                     ready_commit=None, image_digest=None):
    """Refuse unless an unconsumed generation-2 lock and a pass receipt agree.

    Every generation-1 check is kept and three are added: the lock must be the
    generation-2 lock, the receipt must be a generation-2 receipt recovered by
    the verified complete-byte transport, and the ready commit must be present
    and agree. A prose log line, a printed SHA-256 or a bare hash is never
    authorization.
    """
    if not authorization or not isinstance(authorization, dict):
        raise ExecutionRefused(
            "the P0-R1 model pilot requires an execution authorization mapping "
            "carrying the execution lock and the replay-pass receipt")
    if not authorization.get("p0_r1_pilot_execution_authorized"):
        raise ExecutionRefused(
            "the P0-R1 model pilot requires the narrow, not-yet-consumed "
            "p0_r1_pilot_execution_authorized flag")
    if not authorization.get("replay_gate_passed_in_this_session"):
        raise ExecutionRefused(
            "the registered replay-only factorization gate must pass first; "
            "if replay fails, publish a registered stop and perform no model "
            "operation")

    lock = authorization.get("execution_lock")
    receipt = authorization.get("replay_receipt")
    if not isinstance(lock, dict) or not isinstance(receipt, dict):
        raise ExecutionRefused(
            "the model pilot requires the execution lock and the replay-pass "
            "receipt as documents; a prose log line is not authorization")

    ready_commit = ready_commit or authorization.get("ready_commit")
    image_digest = image_digest or authorization.get("image_digest") \
        or lock.get("image", {}).get("digest")

    try:
        RUNTIME.validate_launch_inputs(
            lock, receipt, image_digest, ready_commit,
            lock_bytes=lock_bytes, receipt_bytes=receipt_bytes,
            lock_module=LOCK, root=root)
    except RUNTIME.RuntimeBindingDefect as exc:
        raise ExecutionRefused(str(exc))

    if lock["legal_status"].get("p0_r1_pilot_execution_consumed"):
        raise ExecutionRefused(
            "the execution lock is already consumed; the P0-R1 envelope is "
            "one-shot and is never re-armed")

    attempt = authorization.get("attempt_id")
    if not attempt or attempt != receipt.get("attempt_id"):
        raise ExecutionRefused(
            "the model pilot attempt id %r does not match the replay attempt "
            "id %r; the receipt must come from the same authorized attempt"
            % (attempt, receipt.get("attempt_id")))
    if not receipt.get("transport", {}).get("complete_byte_recovery_verified"):
        raise ExecutionRefused(
            "the replay receipt does not record a verified complete-byte "
            "recovery; a truncated or partially captured replay is not a pass")

    return {
        "lock": lock,
        "receipt": receipt,
        "attempt_id": attempt,
        "ready_commit": ready_commit,
        "image_digest": image_digest,
    }


def write_pilot_artifacts(out_dir, state, attempt_id, lock, partial, counters,
                          identities, journal=None, summary=None,
                          stop_detail=None, exception=None):
    """Write every canonical artifact, on the clean and the exceptional path.

    This is reachable with an empty partial-result set, a half-finished smoke
    slice or a full run. It never discards a row to make a clean report.
    """
    os.makedirs(out_dir, exist_ok=True)
    body = partial.snapshot()
    summary_defect = None
    if summary is None:
        # A summariser is a reporting convenience; the rows are the observation.
        # Generation 1 would have lost every row here, because a half-formed
        # partial set from a real crash is exactly the input a summariser is
        # most likely to reject. The rows are therefore preserved regardless and
        # the refusal is published as evidence rather than swallowed.
        try:
            summary = SUMMARIZE.summarize(
                body["scored_rows"], s4_completions=body["s4_completions"],
                exceptions=body["exceptions"])
        except BaseException as exc:
            summary_defect = {
                "summariser_refused": True,
                "exception": type(exc).__name__,
                "detail": str(exc),
                "no_row_was_discarded_to_obtain_a_summary": True,
            }
            summary = {
                "schema_version": "study3-p0-r1-summary-unavailable-v2",
                "document_class": "study3_p0_r1_partial_summary_unavailable",
                "descriptive_only": True,
                "rows": len(body["scored_rows"]),
                "s4_completions": len(body["s4_completions"]),
                "exceptions": len(body["exceptions"]),
                "summary_unavailable": summary_defect,
            }
    conservative = journal.conservative_report() if journal is not None else {}

    result = {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_r1_model_pilot_result",
        "generation": LOCK.GENERATION,
        "stage": "P0-R1-MODEL-PILOT",
        "state": state,
        "attempt_id": attempt_id,
        "identities": dict(identities or {}),
        "image_digest": lock["image"]["digest"],
        "executable_code_commit": lock["executable_code"]["commit"],
        "executable_code_tree": lock["executable_code"]["tree"],
        "roles": lock["roles"],
        "smoke_passed": body["smoke_passed"],
        "smoke_closed": body["smoke_closed"],
        "scored_rows": body["scored_rows"],
        "s4_completions": body["s4_completions"],
        "exceptions": body["exceptions"],
        "counters": counters,
        "resources": body["resources"],
        "summary": summary,
        "summary_unavailable": summary_defect,
        "stop_reason": body["stop_reason"] or stop_detail,
        "terminating_exception": exception,
        "conservative_report": conservative,
        "every_valid_row_and_partial_result_is_retained": True,
        "no_counter_was_reset_and_no_row_was_repaired": True,
        "evidence_status": (
            "a methods-feasibility continuation observation. It is not Study 3 "
            "evidence, selects no interface, sets no threshold, estimates no "
            "confirmatory effect and answers no research question."),
    }
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_model_pilot_receipt",
        "generation": LOCK.GENERATION,
        "stage": "P0-R1-MODEL-PILOT",
        "state": state,
        "attempt_id": attempt_id,
        "identities": dict(identities or {}),
        "image_digest": lock["image"]["digest"],
        "counters": counters,
        "smoke_passed": body["smoke_passed"],
        "scored_row_count": len(body["scored_rows"]),
        "s4_completion_count": len(body["s4_completions"]),
        "exception_count": len(body["exceptions"]),
        "stop_reason": body["stop_reason"] or stop_detail,
        "terminating_exception": exception,
        "conservative_report": conservative,
        "authorizes_retry": False,
        "retry_requires_a_separate_operator_decision": True,
    }
    disposition = "\n".join([
        "# Stage P0-R1 model pilot: disposition",
        "",
        "> **Emitted terminal state:** `%s`" % state,
        ">",
        "> Published exactly as emitted. Every valid row, raw S4 completion,",
        "> exception, partial result and cumulative counter is retained.",
        "",
        "| field | value |",
        "| --- | --- |",
        "| attempt id | `%s` |" % attempt_id,
        "| ready commit | `%s` |" % (identities or {}).get("ready_commit"),
        "| image digest | `%s` |" % lock["image"]["digest"],
        "| azure job execution | `%s` |"
        % (identities or {}).get("azure_job_execution_name"),
        "| output prefix | `%s` |" % (identities or {}).get("output_prefix"),
        "| smoke passed | `%s` |" % body["smoke_passed"],
        "| scored rows | `%d` |" % len(body["scored_rows"]),
        "| exceptions | `%d` |" % len(body["exceptions"]),
        "",
        "Correctness, accuracy, diversity and discordance are descriptive only",
        "and were not smoke criteria.",
        "",
    ])
    journal_document = {
        "schema_version": "study3-p0-r1-model-pilot-journal-v2",
        "attempt_id": attempt_id,
        "identities": dict(identities or {}),
        "entries": journal.entries() if journal is not None else [],
        "conservative_report": conservative,
        "restart_report": (
            JOURNAL.restart_report(attempt_id, journal.entries())
            if journal is not None else None),
    }

    written = []
    for name, payload in (
            (RESULT_NAME, dumps(result).encode("utf-8")),
            (RECEIPT_NAME, dumps(receipt).encode("utf-8")),
            (COUNTERS_NAME, dumps(counters).encode("utf-8")),
            (DISPOSITION_NAME, disposition.encode("utf-8")),
            (JOURNAL_NAME, dumps(journal_document).encode("utf-8"))):
        path = os.path.join(out_dir, name)
        with open(path, "wb") as handle:
            handle.write(payload)
        with open(path, "rb") as handle:
            if handle.read() != payload:
                raise ExecutionRefused("%s did not read back exactly" % name)
        written.append({
            "name": name,
            "bytes": len(payload),
            "sha256": _sha256(payload),
        })
    return {
        "state": state,
        "attempt_id": attempt_id,
        "result": result,
        "receipt": receipt,
        "artifacts": written,
        "out_dir": out_dir,
    }


def _load_executor():
    execution_dir = os.path.join(P0_R1_DIR, "execution")
    if execution_dir not in sys.path:
        sys.path.insert(0, execution_dir)
    import p0_r1_model_execution_v2 as EXECUTION
    return EXECUTION


def run(authorization=None, counters=None, out_dir=None, root=None,
        device=None, corpus_rows=None, sinks=None, identities=None,
        executor=None, lock_bytes=None, receipt_bytes=None, ready_commit=None,
        image_digest=None, blob_transport=None):
    """Execute the bounded P0-R1 model pilot behind a real exception boundary.

    Returns the written-artifact report on every path. The only way this
    function raises is a refusal *before* the journal exists, which by
    construction is also before any irreversible operation.
    """
    authorized = validate_execution_authorization(
        authorization, root=root, lock_bytes=lock_bytes,
        receipt_bytes=receipt_bytes, ready_commit=ready_commit,
        image_digest=image_digest)

    lock = authorized["lock"]
    attempt_id = authorized["attempt_id"]
    counters = counters if counters is not None else P0R1Counters()
    if not out_dir:
        raise ExecutionRefused(
            "the P0-R1 model pilot requires an explicit writable runtime "
            "result directory")

    identities = dict(identities or RUNTIME.bound_identities(
        lock, authorized["receipt"], authorized["ready_commit"]))

    sinks = list(sinks or [JOURNAL.LocalSequenceSink(
        os.path.join(out_dir, "journal"))])
    if blob_transport is not None:
        sinks.append(JOURNAL.BlobSequenceSink(blob_transport))

    # The journal exists, and is readable back, before any model library is
    # imported. Everything after this point is inside the exception boundary.
    journal = JOURNAL.AttemptJournal(attempt_id, sinks,
                                     bound_identities=identities,
                                     counters=counters)
    journal.open_attempt(detail={"out_dir": out_dir})

    partial = PartialResults()
    state = STATE_STOPPED_WITH_PARTIAL_RESULT
    stop_detail = None
    exception_record = None
    try:
        module = executor if executor is not None else _load_executor()
        state = module.execute(
            authorized, counters, partial, journal, out_dir=out_dir, root=root,
            device=device, corpus_rows=corpus_rows, identities=identities)
    except BaseException as exc:  # the exception boundary. Nothing escapes it.
        counters.add("exceptions_observed", 1)
        exception_record = {
            "exception": type(exc).__name__,
            "detail": str(exc),
            "reached_the_exception_boundary": True,
        }
        stop_detail = (
            "the attempt stopped on %s; every row, completion, exception and "
            "cumulative counter observed before the stop is retained exactly "
            "as observed" % type(exc).__name__)
        state = STATE_STOPPED_WITH_PARTIAL_RESULT
        try:
            journal.record("attempt_exception", payload=exception_record)
        except Exception:  # a sink failure must not lose the artifacts
            pass

    try:
        counters.reconcile_totals()
    except Exception as exc:
        stop_detail = "%s; counter reconciliation reported %s" % (
            stop_detail or "the attempt completed", exc)
    snapshot = counters.snapshot()

    report = write_pilot_artifacts(
        out_dir, state, attempt_id, lock, partial, snapshot, identities,
        journal=journal, stop_detail=stop_detail, exception=exception_record)

    if blob_transport is not None:
        try:
            report["blob"] = blob_transport.upload_directory(
                out_dir, required_names=PILOT_ARTIFACTS)
        except Exception as exc:
            report["blob_error"] = str(exc)
    return report


def implementation_identity(root=None):
    path = os.path.abspath(__file__) if root is None else os.path.join(
        root, "studies", "study3", "pilot", "p0_r1", "p0_r1_model_runner_v2.py")
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": "studies/study3/pilot/p0_r1/p0_r1_model_runner_v2.py",
        "bytes": len(raw),
        "sha256": _sha256(raw),
        "names_no_model_library": True,
        "artifacts": list(PILOT_ARTIFACTS),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--lock-file")
    parser.add_argument("--receipt-file")
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-commit")
    parser.add_argument("--attempt")
    parser.add_argument("--src")
    parser.add_argument("--out-dir")
    parser.add_argument("--blob", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.run:
        if not args.lock_file or not args.receipt_file or not args.out_dir:
            print("--run requires --lock-file, --receipt-file and --out-dir")
            return 2
        with open(args.lock_file, "rb") as handle:
            lock_bytes = handle.read()
        with open(args.receipt_file, "rb") as handle:
            receipt_bytes = handle.read()

        blob_transport = None
        if args.blob:
            import p0_r1_blob_transport as BLOB
            attempt_id = args.attempt or json.loads(
                receipt_bytes.decode("utf-8"))["attempt_id"]
            blob_transport = BLOB.PrivateBlobTransport(attempt_id)

        try:
            report = run(
                out_dir=args.out_dir, root=args.src, lock_bytes=lock_bytes,
                receipt_bytes=receipt_bytes, ready_commit=args.ready_commit,
                image_digest=args.image_digest, blob_transport=blob_transport)
        except ExecutionRefused as exc:
            print("P0_R1_MODEL_PILOT_REFUSED=1")
            print("  FAIL %s" % exc)
            return 1

        print("P0_R1_MODEL_PILOT_STATE=%s" % report["state"])
        for artifact in report["artifacts"]:
            print("ARTIFACT=%s SHA256=%s BYTES=%d"
                  % (artifact["name"], artifact["sha256"], artifact["bytes"]))
        # A stop with a retained partial result is a real, reportable outcome.
        # It is not an error to be swallowed, and it is not a success either.
        return 0 if report["state"] == STATE_COMPLETE else 4

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
