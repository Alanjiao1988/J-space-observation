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

SCHEMA_VERSION = "study3-p0-r1-model-runner-v3"

SENTINEL_EXECUTOR = "sentinel"
PRODUCTION_EXECUTOR = "production"

STATE_COMPLETE = "STUDY3_P0_R1_PILOT_COMPLETE"
STATE_PARTIAL = "STUDY3_P0_R1_PILOT_STOPPED_WITH_RETAINED_PARTIAL_RESULT"
STATE_INFRASTRUCTURE = "STUDY3_P0_R1_PILOT_INFRASTRUCTURE_STOP"

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

    counters = RUNNER_V2.RUNNER.P0R1Counters() \
        if hasattr(RUNNER_V2.RUNNER, "P0R1Counters") else None
    partial = RUNNER_V2.PartialResults()
    authorized = RUNNER_V2.validate_execution_authorization(
        authorization, root=context["root"],
        lock_bytes=context["lock_bytes"],
        receipt_bytes=context["receipt_bytes"],
        ready_commit=authorization["ready_commit"],
        image_digest=authorization["image_digest"])

    state = EXEC_V3.execute(
        authorized, counters, partial, journal,
        out_dir=context["out_dir"], root=context["root"],
        identities=None)
    return {
        "state": state,
        "executor": PRODUCTION_EXECUTOR,
        "artifacts": [],
        "partial": partial.snapshot(),
    }


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
        attempt_id=attempt_id, image_digest=image_digest, run_id=run_id)
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
                manifest = journal.manifest(
                    canonical=[], extra={"terminated_by": "exception"})
                emit_secondary_envelope(journal, manifest, stream=stream)
            except Exception:  # noqa: BLE001 - a sink failure must not mask
                stream.write("P0_R1_DURABILITY_DEGRADED=1\n")
                stream.flush()
        raise

    if journal is not None:
        journal.record("counter_snapshot", {
            "model_operations_performed": result.get(
                "model_operations_performed", 0),
            "executor": executor,
        })
        manifest = journal.manifest(
            canonical=[entry.get("name") for entry in
                       (result.get("artifacts") or [])])
        result["journal_manifest"] = manifest["manifest_identity"]
        result["journal_objects"] = manifest["journal_object_count"]
        emit_secondary_envelope(journal, manifest, stream=stream)
    return result


def emit_secondary_envelope(journal, manifest, stream=None):
    """Write the conservative receipt out over the console as complete bytes.

    The second route exists for the case where Blob is unreachable or the
    replica dies before an operator can read it. Generation 2 printed a hash
    here, which proves only that bytes once existed; this emits the bytes.
    """
    stream = stream if stream is not None else sys.stdout
    import p0_r1_transport as TRANSPORT

    payload = (json.dumps(manifest, indent=2, sort_keys=True,
                          default=str) + "\n").encode("utf-8")
    try:
        for line in TRANSPORT.encode(
                journal.attempt_id, {JOURNAL.MANIFEST_NAME: payload},
                allowed=(JOURNAL.MANIFEST_NAME,)):
            stream.write(line + "\n")
        stream.write("P0_R1_SECONDARY_ENVELOPE_COMPLETE=1\n")
    except Exception as exc:  # noqa: BLE001 - report, never mask
        stream.write("P0_R1_SECONDARY_ENVELOPE_FAILED=1 %s\n" % exc)
    stream.flush()
    return payload


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
