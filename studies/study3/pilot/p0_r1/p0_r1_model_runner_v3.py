#!/usr/bin/env python3
"""The generation-3 model pilot entry point: real CLI, real authorization.

This module owns the *wiring* and nothing scientific. Allocation, caps, the
exact smoke criterion, the scoring rules, the parser and every statistic remain
in the generation-2 runner, which this module imports and calls. Not one
registered scientific byte changes; what changes is that the production command
line now builds the authorization that production always required, instead of
calling the science with ``authorization=None`` and refusing itself.

The sequence is fixed and each step is refused before the next begins:

1. read four exact byte inputs -- lock, emitted replay receipt, independent
   reconstruction receipt, published-head proof;
2. build the authorization through the single construction path;
3. prove the private prefix and every reserved object name absent;
4. initialize the Blob-primary journal and read back its first entry; and
5. only then hand control to the executor.

Step 5 is indirected through ``--executor`` so the exact production command can
be exercised end to end by a sentinel that proves the boundary is reached
exactly once while importing no model library, touching no checkpoint and
allocating no GPU. The default executor is the real one; the sentinel must be
requested explicitly and records itself in the journal, so a sentinel run can
never be mistaken for a scientific one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_authorization_v3 as AUTHZ  # noqa: E402
import p0_r1_blob_transport_v3 as BLOB_V3  # noqa: E402
import p0_r1_journal_v3 as JOURNAL  # noqa: E402
import p0_r1_prefix_preflight_v3 as PREFIX  # noqa: E402
import p0_r1_summarize as SUMMARIZE  # noqa: E402
from p0_r1_counters import P0R1Counters  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-model-runner-v3"

SENTINEL_EXECUTOR = "sentinel"
PRODUCTION_EXECUTOR = "production"

STATE_COMPLETE = "STUDY3_P0_R1_COMPLETE_MECHANICALLY_FEASIBLE"
STATE_PARTIAL = "STUDY3_P0_R1_STOPPED_WITH_PARTIAL_RESULT"
STATE_INFRASTRUCTURE = "STUDY3_P0_R1_PILOT_INFRASTRUCTURE_STOP"

RESULT_NAME = "p0_r1_model_pilot_result.json"
RECEIPT_NAME = "p0_r1_model_pilot_receipt.json"
COUNTERS_NAME = "p0_r1_model_pilot_counters.json"
DISPOSITION_NAME = "P0_R1_MODEL_PILOT_DISPOSITION.md"
JOURNAL_NAME = "p0_r1_model_pilot_journal.json"
PILOT_ARTIFACTS = (
    RESULT_NAME, RECEIPT_NAME, COUNTERS_NAME, DISPOSITION_NAME, JOURNAL_NAME)

SENTINEL_LINE = "P0_R1_SENTINEL_EXECUTOR_REACHED=1"

FORBIDDEN_SENTINEL_MODULES = ("transformers", "torch")


class PilotRefused(Exception):
    """A precondition failed. No model operation was performed."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def sentinel_executor(context, stream=None):
    """Prove the authorized boundary is reached without touching a model.

    Asserts that no model library has been imported by the time control
    arrives here, which is the property the seam test actually needs.
    """
    stream = stream if stream is not None else sys.stdout
    imported = [name for name in FORBIDDEN_SENTINEL_MODULES
                if name in sys.modules]
    if imported:
        raise PilotRefused(
            "the sentinel executor was reached with %s already imported; the "
            "no-model boundary was crossed before authorization"
            % ", ".join(sorted(imported)))
    stream.write("%s\n" % SENTINEL_LINE)
    stream.write("P0_R1_SENTINEL_ATTEMPT=%s\n" % context["attempt_id"])
    stream.flush()
    return {
        "state": STATE_COMPLETE,
        "executor": SENTINEL_EXECUTOR,
        "model_operations_performed": 0,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_allocated": False,
        "artifacts": [],
        "reached_authorized_boundary": True,
    }


def validate_execution_authorization(authorization, lock_bytes, receipt_bytes):
    """Re-check exact v3 inputs without re-imposing generation-2 semantics."""
    if authorization.get("schema_version") != AUTHZ.SCHEMA_VERSION:
        raise PilotRefused("the authorization is not a generation-3 document")
    lock = authorization.get("execution_lock")
    receipt = authorization.get("replay_receipt")
    reconstruction = authorization.get("reconstruction_receipt")
    if not isinstance(lock, dict) or lock.get("generation") != 3:
        raise PilotRefused("the production executor requires the v3 lock")
    if not isinstance(receipt, dict) or not isinstance(reconstruction, dict):
        raise PilotRefused(
            "the replay receipt and independent reconstruction are mandatory")
    identities = authorization.get("input_identities") or {}
    if (identities.get("execution_lock") or {}).get("sha256") != \
            _sha256(lock_bytes):
        raise PilotRefused("the runtime lock bytes differ from authorization")
    if (identities.get("replay_receipt") or {}).get("sha256") != \
            _sha256(receipt_bytes):
        raise PilotRefused("the runtime replay receipt bytes differ")
    if not reconstruction.get("complete_byte_recovery_verified") \
            or reconstruction.get("gate_receipt_was_mutated"):
        raise PilotRefused(
            "the reconstruction does not prove unmutated complete-byte recovery")
    attempt = authorization.get("attempt_id")
    if not attempt or receipt.get("attempt_id") != attempt \
            or reconstruction.get("attempt_id") != attempt:
        raise PilotRefused("the authorization inputs bind different attempts")
    if receipt.get("ready_commit") != authorization.get("ready_commit"):
        raise PilotRefused("the replay did not bind the proved ready anchor")
    return {
        "lock": lock,
        "receipt": receipt,
        "attempt_id": attempt,
        "ready_commit": authorization["ready_commit"],
        "image_digest": authorization["image_digest"],
    }


def _dumps(document):
    return (json.dumps(document, indent=1, sort_keys=True,
                       ensure_ascii=True) + "\n").encode("utf-8")


def write_pilot_artifacts(out_dir, state, attempt_id, lock, partial,
                          counters, identities, journal, stop_detail=None,
                          exception=None):
    """Write generation-3 canonical artifacts without discarding partial rows."""
    os.makedirs(out_dir, exist_ok=True)
    body = partial.snapshot()
    summary_defect = None
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
            "schema_version": "study3-p0-r1-summary-unavailable-v3",
            "document_class": "study3_p0_r1_partial_summary_unavailable",
            "descriptive_only": True,
            "rows": len(body["scored_rows"]),
            "s4_completions": len(body["s4_completions"]),
            "exceptions": len(body["exceptions"]),
            "summary_unavailable": summary_defect,
        }
    conservative = journal.conservative_report()
    result = {
        "schema_version": "study3-p0-r1-model-pilot-result-v3",
        "document_class": "study3_p0_r1_model_pilot_result",
        "generation": 3,
        "stage": "P0-R1-MODEL-PILOT",
        "state": state,
        "attempt_id": attempt_id,
        "identities": identities,
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
            "a methods-feasibility continuation observation; it is not Study 3 "
            "evidence and answers no research question"),
    }
    receipt = {
        "schema_version": "study3-p0-r1-model-pilot-receipt-v3",
        "document_class": "study3_p0_r1_model_pilot_receipt",
        "generation": 3,
        "stage": "P0-R1-MODEL-PILOT",
        "state": state,
        "attempt_id": attempt_id,
        "identities": identities,
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
        "# Stage P0-R1 generation-3 model pilot: disposition",
        "",
        "> **Emitted terminal state:** `%s`" % state,
        ">",
        "> Every observed row, completion, exception and cumulative counter is",
        "> retained exactly as observed.",
        "",
        "| field | value |",
        "| --- | --- |",
        "| attempt id | `%s` |" % attempt_id,
        "| ready anchor | `%s` |" % identities.get("ready_commit"),
        "| published head | `%s` |" % identities.get("published_head"),
        "| image digest | `%s` |" % lock["image"]["digest"],
        "| smoke passed | `%s` |" % body["smoke_passed"],
        "| scored rows | `%d` |" % len(body["scored_rows"]),
        "| exceptions | `%d` |" % len(body["exceptions"]),
        "",
    ]).encode("utf-8")
    journal_document = {
        "schema_version": "study3-p0-r1-model-pilot-journal-v3",
        "attempt_id": attempt_id,
        "identities": identities,
        "entries": list(journal.entries),
        "conservative_report": conservative,
    }
    payloads = {
        RESULT_NAME: _dumps(result),
        RECEIPT_NAME: _dumps(receipt),
        COUNTERS_NAME: _dumps(counters),
        DISPOSITION_NAME: disposition,
        JOURNAL_NAME: _dumps(journal_document),
    }
    written = []
    for name, payload in payloads.items():
        path = os.path.join(out_dir, name)
        with open(path, "wb") as handle:
            handle.write(payload)
        with open(path, "rb") as handle:
            if handle.read() != payload:
                raise PilotRefused("%s did not read back byte-exactly" % name)
        written.append({
            "name": name, "bytes": len(payload), "sha256": _sha256(payload)})
    return {
        "state": state, "attempt_id": attempt_id, "result": result,
        "receipt": receipt, "artifacts": written, "out_dir": out_dir,
    }


def production_executor(context, stream=None):
    """Run the registered science behind the generation-3 durable journal.

    The import is deliberately here and not at module scope: importing the
    execution subpackage is the moment a model library can appear, and nothing
    model-shaped may be imported before authorization has been proved.
    """
    import p0_r1_model_runner_v2 as RUNNER_V2
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "execution"))
    import p0_r1_model_execution_v3 as EXEC_V3

    authorization = context["authorization"]
    journal = context["journal"]
    if journal is None:
        raise PilotRefused(
            "the production executor requires the Blob-primary journal; the "
            "container filesystem is a cache, not the record of an "
            "observation")

    counters = P0R1Counters()
    partial = RUNNER_V2.PartialResults()
    authorized = validate_execution_authorization(
        authorization, context["lock_bytes"], context["receipt_bytes"])
    identities = {
        "ready_commit": authorization["ready_commit"],
        "published_head": authorization["published_head"],
        "published_tree": authorization["published_tree"],
        "image_digest": authorization["image_digest"],
        "replay_run_id": authorization["run_id"],
        "output_prefix": context["blob_transport"].prefix,
    }
    state = STATE_PARTIAL
    stop_detail = None
    exception_record = None
    try:
        state = EXEC_V3.execute(
            authorized, counters, partial, journal,
            out_dir=context["out_dir"], root=context["root"],
            identities=identities)
    except BaseException as exc:
        counters.add("exceptions_observed", 1)
        exception_record = {
            "exception": type(exc).__name__,
            "detail": str(exc),
            "reached_the_exception_boundary": True,
        }
        partial.exceptions.append(exception_record)
        partial.stop_reason = (
            "the attempt stopped on %s; all prior observations are retained"
            % type(exc).__name__)
        stop_detail = partial.stop_reason
        state = STATE_PARTIAL
        journal.record_exception(exc, stage="production_executor")
    try:
        counters.reconcile_totals()
    except Exception as exc:
        stop_detail = "%s; counter reconciliation reported %s" % (
            stop_detail or "the attempt completed", exc)
    snapshot = counters.snapshot()
    report = write_pilot_artifacts(
        context["out_dir"], state, context["attempt_id"],
        authorization["execution_lock"], partial, snapshot, identities, journal,
        stop_detail=stop_detail, exception=exception_record)
    report.update({
        "executor": PRODUCTION_EXECUTOR,
        "model_operations_performed": snapshot.get(
            "total_sequence_level_model_evaluation_equivalents", 0),
    })
    return report


EXECUTORS = {
    SENTINEL_EXECUTOR: sentinel_executor,
    PRODUCTION_EXECUTOR: production_executor,
}


def run_pilot(lock_file, replay_receipt, reconstruction_receipt, head_proof,
              out_dir, root=None, attempt_id=None, image_digest=None,
              executor=PRODUCTION_EXECUTOR, backend=None, stream=None,
              blob=True, run_id=None):
    """The exact production path, in order, with every refusal in place."""
    stream = stream if stream is not None else sys.stdout

    authorization = AUTHZ.build_from_files(
        lock_file, replay_receipt, reconstruction_receipt, head_proof,
        attempt_id=attempt_id, image_digest=image_digest, run_id=run_id,
        root=root)
    attempt = authorization["attempt_id"]
    stream.write("P0_R1_AUTHORIZATION_BUILT=1 ATTEMPT=%s\n" % attempt)

    report = PREFIX.probe(attempt, backend=backend)
    stream.write("P0_R1_PREFIX_PREFLIGHT=%s PREFIX=%s\n"
                 % (report.get("outcome"), report.get("prefix")))
    try:
        PREFIX.require_unused(report)
    except PREFIX.PrefixPreflightDefect as exc:
        raise PilotRefused(str(exc))

    journal = None
    transport = None
    if blob:
        transport = BLOB_V3.PrivateBlobTransportV3(attempt, backend=backend)
        journal = JOURNAL.DurableJournal(
            attempt, JOURNAL.BlobJournalSink(transport),
            cache=JOURNAL.LocalJournalCache(os.path.join(out_dir, "cache")),
            stream=stream)
        os.makedirs(out_dir, exist_ok=True)
        journal.start({
            "attempt_id": attempt,
            "image_digest": authorization["image_digest"],
            "executable_code_commit":
                authorization["execution_lock"]["executable_code"]["commit"],
            "ready_anchor": authorization["ready_commit"],
            "published_head": authorization["published_head"],
            "run_id": authorization.get("run_id"),
            "executor": executor,
        })

    with open(lock_file, "rb") as handle:
        lock_bytes = handle.read()
    with open(replay_receipt, "rb") as handle:
        receipt_bytes = handle.read()

    context = {
        "authorization": authorization,
        "attempt_id": attempt,
        "out_dir": out_dir,
        "root": root,
        "lock_bytes": lock_bytes,
        "receipt_bytes": receipt_bytes,
        "blob_transport": transport,
        "journal": journal,
    }

    handler = EXECUTORS.get(executor)
    if handler is None:
        raise PilotRefused("%r is not a registered executor" % (executor,))

    pending_exception = None
    try:
        result = handler(context, stream=stream) if executor == \
            SENTINEL_EXECUTOR else handler(context)
    except Exception as exc:  # noqa: BLE001 - preserved, never swallowed
        # Whenever the process can still write, the most conservative receipt
        # and every prior byte are preserved by both routes before the failure
        # propagates. Generation 2 could reach this point with the journal
        # entries only on an ephemeral filesystem.
        if journal is not None:
            try:
                journal.record_exception(exc, stage="executor")
                journal.interruption()
            except Exception:  # noqa: BLE001 - a sink failure must not mask
                stream.write("P0_R1_DURABILITY_DEGRADED=1\n")
                stream.flush()
        result = {
            "state": STATE_PARTIAL,
            "executor": executor,
            "model_operations_performed": 0,
            "artifacts": [],
        }
        pending_exception = exc

    if journal is not None:
        journal.record("counter_snapshot", {
            "model_operations_performed": result.get(
                "model_operations_performed", 0),
            "executor": executor,
        })
        canonical = []
        for entry in result.get("artifacts") or ():
            name = entry.get("name")
            if not name:
                continue
            with open(os.path.join(out_dir, name), "rb") as handle:
                transport.upload_and_verify(name, handle.read())
            canonical.append(name)

        container_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "container")
        if container_dir not in sys.path:
            sys.path.insert(0, container_dir)
        import p0_r1_infrastructure_receipt_v3 as INFRA
        shell_code = 0 if result.get("state") == STATE_COMPLETE else 4
        infrastructure = INFRA.build(
            shell_code, attempt_id=attempt, out_dir=out_dir,
            lock_sha256=_sha256(lock_bytes),
            detail={"executor": executor, "finalized_by": "model_runner_v3"})
        infrastructure_payload = (
            json.dumps(infrastructure, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        infrastructure_path = os.path.join(out_dir, INFRA.RECEIPT_NAME)
        with open(infrastructure_path, "wb") as handle:
            handle.write(infrastructure_payload)
        transport.upload_and_verify(
            INFRA.RECEIPT_NAME, infrastructure_payload)
        canonical.append(INFRA.RECEIPT_NAME)
        result.setdefault("artifacts", []).append({
            "name": INFRA.RECEIPT_NAME,
            "bytes": len(infrastructure_payload),
            "sha256": _sha256(infrastructure_payload),
        })

        manifest = journal.manifest(
            canonical=canonical,
            extra={"terminal_state": result.get("state"),
                   "executor": executor})
        recursive = transport.write_recursive_manifest({
            "journal_manifest": manifest["manifest_identity"],
            "canonical_artifacts": canonical,
            "terminal_state": result.get("state"),
        })
        with open(os.path.join(out_dir, recursive["name"]), "wb") as handle:
            handle.write(recursive["payload"])
        result["journal_manifest"] = manifest["manifest_identity"]
        result["journal_objects"] = manifest["journal_object_count"]
        result["recursive_manifest"] = {
            key: recursive[key] for key in ("name", "bytes", "sha256")}
        emit_secondary_envelope(
            journal, manifest, recursive, out_dir, canonical, stream=stream)
    if pending_exception is not None:
        raise pending_exception
    return result


def emit_secondary_envelope(journal, manifest, recursive, out_dir, canonical,
                            stream=None):
    """Write the conservative receipt out over the console as complete bytes.

    The second route exists for the case where Blob is unreachable or the
    replica dies before an operator can read it. Generation 2 printed a hash
    here, which proves only that bytes once existed; this emits the bytes.
    """
    stream = stream if stream is not None else sys.stdout
    import p0_r1_transport as TRANSPORT

    payloads = {}
    for name in canonical:
        with open(os.path.join(out_dir, name), "rb") as handle:
            payloads[name] = handle.read()
    for entry in journal.entries:
        name = entry["name"]
        payloads[name.replace("/", "__")] = journal.sink.read(name)
    payloads[JOURNAL.MANIFEST_NAME] = journal.sink.read(JOURNAL.MANIFEST_NAME)
    payloads[recursive["name"]] = recursive["payload"]
    try:
        allowed = tuple(sorted(payloads))
        for line in TRANSPORT.encode(
                journal.attempt_id, payloads, allowed=allowed):
            stream.write(line + "\n")
        stream.write("P0_R1_SECONDARY_ENVELOPE_COMPLETE=1\n")
    except Exception as exc:  # noqa: BLE001 - report, never mask
        stream.write("P0_R1_SECONDARY_ENVELOPE_FAILED=1 %s\n" % exc)
    stream.flush()
    return payloads


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_model_runner_v3.py",
        "executors": sorted(EXECUTORS),
        "mandatory_cli_inputs": [
            "--lock-file", "--replay-receipt", "--reconstruction-receipt",
            "--head-proof", "--out-dir"],
        "builds_authorization_in_production": True,
        "delegates_science_to":
            "execution/p0_r1_model_execution_v3 -> "
            "execution/p0_r1_model_execution_v2.execute",
        "changes_any_scientific_rule": False,
        "journal_primary_sink": "private_blob",
        "closes": "G2-02",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--lock-file")
    parser.add_argument("--replay-receipt")
    parser.add_argument("--reconstruction-receipt")
    parser.add_argument("--head-proof")
    parser.add_argument("--out-dir")
    parser.add_argument("--src")
    parser.add_argument("--attempt")
    parser.add_argument("--run-id")
    parser.add_argument("--image-digest")
    parser.add_argument("--executor", default=PRODUCTION_EXECUTOR,
                        choices=sorted(EXECUTORS))
    parser.add_argument("--no-blob", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if not args.run:
        parser.print_help()
        return 2

    missing = [name for name, value in (
        ("--lock-file", args.lock_file),
        ("--replay-receipt", args.replay_receipt),
        ("--reconstruction-receipt", args.reconstruction_receipt),
        ("--head-proof", args.head_proof),
        ("--out-dir", args.out_dir)) if not value]
    if missing:
        print("FAIL: --run requires %s" % ", ".join(missing), file=sys.stderr)
        return 2

    backend = None
    if os.environ.get("P0_R1_CANARY_IN_MEMORY_BLOB") == "1":
        # A synthetic store is permitted only for the sentinel executor. This
        # is the guard generation 2 lacked: its transport gate ran --dry-run
        # against an in-memory backend on the same path the real run used, so
        # an image that could not reach the storage account passed every gate.
        # Here a fake store and real science are mutually exclusive.
        if args.executor != SENTINEL_EXECUTOR:
            print("FAIL: an in-memory object store is only permitted with the "
                  "sentinel executor; the production executor always writes "
                  "to the registered private account", file=sys.stderr)
            return 2
        import p0_r1_blob_transport as BLOB
        backend = BLOB.InMemoryBackend()

    try:
        result = run_pilot(
            args.lock_file, args.replay_receipt, args.reconstruction_receipt,
            args.head_proof, args.out_dir, root=args.src,
            attempt_id=args.attempt, image_digest=args.image_digest,
            executor=args.executor, blob=not args.no_blob, backend=backend,
            run_id=args.run_id)
    except (AUTHZ.AuthorizationRefused, PilotRefused) as exc:
        print("P0_R1_MODEL_PILOT_REFUSED=1")
        print("  FAIL %s" % exc)
        return 1

    print("P0_R1_MODEL_PILOT_STATE=%s" % result.get("state"))
    print("P0_R1_MODEL_PILOT_EXECUTOR=%s" % args.executor)
    for artifact in result.get("artifacts") or ():
        print("ARTIFACT=%s SHA256=%s BYTES=%d"
              % (artifact.get("name"), artifact.get("sha256"),
                 artifact.get("bytes", 0)))
    return 0 if result.get("state") == STATE_COMPLETE else 4


if __name__ == "__main__":
    sys.exit(main())
