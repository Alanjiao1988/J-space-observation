"""The Study 3 P0-R1 generation-2 replay gate wrapper.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
sections 5, 6 and 7, over the operative
``studies/study3/prompts/study3_v0_6_p0_r1_authority.md``.

The scientific content of the replay gate is **not** re-implemented here. Every
factorization condition, every eligibility classification, every acceptance
threshold, every counter guard and the disposition rendering are imported from
the registered generation-1 gate and executed unchanged. This wrapper changes
exactly three operational things, all of which section 6 requires:

1. it binds the generation-2 execution lock and image digest rather than the
   superseded generation-1 pair, and it validates the ready commit it is given
   instead of ignoring it;
2. it records the identity block every generation-2 artifact must carry: ready
   commit, execution lock identity, replay attempt id, image digest, Azure job
   execution name and output prefix;
3. it transports the four exact artifacts out of the container through the
   verified complete-byte envelope, and **emits no pass authorization until a
   recovery has reproduced all four files byte-for-byte**.

A truncated, reordered, interleaved or partially captured log is therefore not
a replay pass, and a bare printed SHA-256 is never authorization.

This module performs zero tokenizer, checkpoint, model and GPU operations.
"""

import argparse
import hashlib
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

sys.path.insert(0, P0_R1_DIR)

import p0_r1_eligibility as ELIG  # noqa: E402
import p0_r1_execution_lock_v2 as LOCK  # noqa: E402
import p0_r1_factorization as FACT  # noqa: E402
import p0_r1_replay_gate as GATE  # noqa: E402
import p0_r1_runtime_binding as RUNTIME  # noqa: E402
import p0_r1_transport as TRANSPORT  # noqa: E402
from p0_r1_counters import P0R1Counters  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-replay-gate-v2"
GATE_RESULT_SCHEMA_VERSION = "study3-p0-r1-replay-gate-result-v2"
GATE_RECEIPT_SCHEMA_VERSION = "study3-p0-r1-replay-gate-receipt-v2"

#: The same successor-mode token. A calibration or build-time invocation still
#: cannot reach live gate logic by accident.
SUCCESSOR_AUTHORIZATION = GATE.SUCCESSOR_AUTHORIZATION

ROLES = GATE.ROLES
STATE_AFTER_REPLAY_PASS = GATE.STATE_AFTER_REPLAY_PASS
STATE_REPLAY_DEFECT = GATE.STATE_REPLAY_DEFECT

#: The single line a wrapper may treat as authorization, and only after the
#: transport verification line has already been emitted.
PASS_AUTHORIZATION_LINE = "P0_R1_REPLAY_GATE_PASSED_AUTHORIZES_ONE_MODEL_PILOT=1"
TRANSPORT_VERIFIED_LINE = "P0_R1_REPLAY_TRANSPORT_VERIFIED=1"

#: The receipt that proves the artifact bytes survived the container boundary.
#: The successor refuses a pass authorization that this file does not back.
TRANSPORT_RECEIPT_NAME = "p0_r1_replay_transport_receipt.json"
TRANSPORT_RECEIPT_SCHEMA_VERSION = "study3-p0-r1-replay-transport-receipt-v2"


class GateRefused(Exception):
    """A fail-closed replay-gate stop."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def mint_attempt_id(executable_code_commit, now=None):
    """A Blob-prefix-safe generation-2 attempt id."""
    return "gen2-%s-%s" % (executable_code_commit[:12], now or GATE.utc_now())


def _resolve_lock(lock, lock_bytes, root):
    if lock_bytes is not None:
        parsed = json.loads(lock_bytes.decode("utf-8"))
        identity = {
            "path": LOCK.LOCK_PATH,
            "bytes": len(lock_bytes),
            "sha256": _sha256(lock_bytes),
        }
        return (lock if lock is not None else parsed), identity
    if lock is not None:
        payload = LOCK.dumps(lock).encode("utf-8")
        return lock, {"path": LOCK.LOCK_PATH, "bytes": len(payload),
                      "sha256": _sha256(payload)}
    return LOCK.load_lock(root=root), LOCK.lock_identity(root=root)


def gate_run_v2(out_dir, authorization=None, image_digest=None,
                ready_commit=None, lock=None, lock_bytes=None, root=None,
                registry=None, counters=None, execution_name=None,
                blob_prefix=None, now=None):
    """The generation-2 replay gate. Successor session only.

    Writes the four canonical artifacts before returning on both the pass and
    the failure path, then transports and independently recovers them. The
    returned document reports whether the recovery reproduced every byte.
    """
    if authorization != SUCCESSOR_AUTHORIZATION:
        raise GateRefused(
            "the registered P0-R1 replay gate is the first action of the "
            "successor execution session. It requires explicit successor-mode "
            "authorization (%r)." % SUCCESSOR_AUTHORIZATION)
    if not out_dir:
        raise GateRefused(
            "the registered replay gate requires an explicit writable runtime "
            "result directory")
    if not ready_commit or len(str(ready_commit)) != 40 \
            or any(character not in "0123456789abcdef"
                   for character in str(ready_commit)):
        raise GateRefused(
            "the ready commit is a required, validated argument; it is never "
            "accepted and ignored")

    lock, lock_identity = _resolve_lock(lock, lock_bytes, root)
    LOCK.verify_binding(lock, image_digest=image_digest, root=root)
    if lock["generation"] != LOCK.GENERATION:
        raise GateRefused(
            "the generation-2 gate refuses a generation-%r lock"
            % lock.get("generation"))

    counters = counters if counters is not None else P0R1Counters()
    registry = registry if registry is not None else GATE.load_registry()
    started = GATE.utc_now()
    attempt_id = mint_attempt_id(lock["executable_code"]["commit"], now=now)

    try:
        immutable_sources = FACT.verify_immutable_sources(root=root)
        immutable_source_defect = None
    except FACT.FactorizationDefect as exc:
        immutable_sources = []
        immutable_source_defect = str(exc)

    stop_reason = None
    findings = []
    try:
        factorization = FACT.gate(registry, root=root, counters=counters)
    except FACT.FactorizationDefect as exc:
        factorization = {
            "all_roles_eligible": False,
            "common_prefix_token_is_common_to_every_role": False,
            "discriminant_token_ids_are_common_to_every_role": False,
            "defect": str(exc),
        }
        stop_reason = (
            "The replay factorization gate failed on immutable evidence: %s"
            % exc)
        state = STATE_REPLAY_DEFECT
        summary = {
            "cells": 0, "eligible_cells": 0, "ineligible_cells": 0,
            "ineligible_cells_with_an_empty_reason_list": 0,
            "structurally_absent_pairs": 0,
            "executable_genuine_i3_contrasts_per_role": {},
            "roles_without_executable_contrast": list(ROLES),
        }
        corrected = None
    else:
        result = FACT.load_immutable(FACT.RESULT_PATH, root=root)
        corrected = ELIG.classify(
            result["records"], factorization,
            GATE.published_s1_surfaces(result), ROLES)
        ELIG.validate_matrix(corrected["matrix"], roles=ROLES)
        summary = GATE._matrix_summary(corrected)
        findings = GATE.check_corrected_matrix(summary)
        if findings:
            stop_reason = (
                "The corrected eligibility matrix did not reproduce the "
                "registered acceptance conditions:\n\n"
                + "\n".join("* %s" % finding for finding in findings))
            state = (ELIG.STOP_SOME_ROLE_HAS_NO_EXECUTABLE_CONTRAST
                     if summary["roles_without_executable_contrast"]
                     else STATE_REPLAY_DEFECT)
        else:
            state = STATE_AFTER_REPLAY_PASS

    snapshot = counters.snapshot()
    counter_findings = GATE._counter_guard(snapshot)
    if counter_findings and state == STATE_AFTER_REPLAY_PASS:
        stop_reason = (
            "The replay gate counters did not reconcile:\n\n"
            + "\n".join("* %s" % finding for finding in counter_findings))
        state = STATE_REPLAY_DEFECT
        findings = findings + counter_findings

    passed = state == STATE_AFTER_REPLAY_PASS

    identities = RUNTIME.bound_identities(
        lock, {"attempt_id": attempt_id, "execution_lock": lock_identity},
        ready_commit, execution_name=execution_name, blob_prefix=blob_prefix)

    result_document = {
        "schema_version": GATE_RESULT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_replay_gate_result",
        "generation": LOCK.GENERATION,
        "stage": "P0-R1-REPLAY-GATE",
        "state": state,
        "passed": passed,
        "attempt_id": attempt_id,
        "started_utc": started,
        "completed_utc": GATE.utc_now(),
        "identities": identities,
        "ready_commit": ready_commit,
        "authorities": lock["authorities"],
        "corpus_and_p0_t": lock["corpus_and_p0_t"],
        "execution_lock": lock_identity,
        "image_digest": lock["image"]["digest"],
        "executable_code_commit": lock["executable_code"]["commit"],
        "executable_code_tree": lock["executable_code"]["tree"],
        "immutable_sources": immutable_sources,
        "immutable_source_defect": immutable_source_defect,
        "target_roles": list(ROLES),
        "tokenizer_encodes_performed": 0,
        "tokenizer_constructions_performed": 0,
        "model_operations_performed": 0,
        "gpu_allocated": False,
        "factorization": factorization,
        "corrected_matrix": (corrected["matrix"] if corrected else []),
        "structurally_absent": (corrected["structurally_absent"]
                                if corrected else []),
        "executable_genuine_i3_contrasts": (
            corrected["executable_genuine_i3_contrasts"] if corrected else {}),
        "corrected_matrix_summary": summary,
        "acceptance_findings": findings,
        "stop_reason": stop_reason,
        "counters": snapshot,
        "evidence_status": (
            "a methods-feasibility replay observation over immutable evidence. "
            "It is not Study 3 evidence, selects no interface, sets no "
            "threshold and answers no research question."),
    }

    receipt_document = {
        "schema_version": GATE_RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_replay_gate_receipt",
        "generation": LOCK.GENERATION,
        "stage": "P0-R1-REPLAY-GATE",
        "state": state,
        "passed": passed,
        "attempt_id": attempt_id,
        "completed_utc": result_document["completed_utc"],
        "identities": identities,
        "ready_commit": ready_commit,
        "authorities": lock["authorities"],
        "corpus_and_p0_t": lock["corpus_and_p0_t"],
        "execution_lock": lock_identity,
        "image_digest": lock["image"]["digest"],
        "executable_code_commit": lock["executable_code"]["commit"],
        "executable_code_tree": lock["executable_code"]["tree"],
        "result_document": {"name": GATE.GATE_RESULT_NAME},
        "transport": {
            "envelope_version": TRANSPORT.ENVELOPE_VERSION,
            "artifacts": list(TRANSPORT.REPLAY_ARTIFACTS),
            "complete_byte_recovery_verified": False,
        },
        "counters": snapshot,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_allocated": False,
        "model_operations_performed": 0,
        "stop_reason": stop_reason,
        "authorizes_model_pilot": passed,
        "authorization_scope": (
            "exactly one bounded GPU model pilot in this same execution "
            "session, bound to the locked image digest and this attempt id"
            if passed else
            "nothing. A replay failure authorizes no model operation."),
    }

    disposition = GATE._disposition_markdown(
        state, summary, factorization, stop_reason, lock)

    GATE._write_artifacts(
        out_dir, result_document, receipt_document, snapshot, disposition)

    payload = GATE.dumps(result_document).encode("utf-8")
    receipt_document["result_document"] = {
        "name": GATE.GATE_RESULT_NAME,
        "bytes": len(payload),
        "sha256": _sha256(payload),
    }
    written = GATE._write_artifacts(
        out_dir, result_document, receipt_document, snapshot, disposition)

    return {
        "state": state,
        "passed": passed,
        "attempt_id": attempt_id,
        "ready_commit": ready_commit,
        "result": result_document,
        "receipt": receipt_document,
        "artifacts": written,
        "out_dir": out_dir,
        "execution_lock": lock_identity,
        "identities": identities,
    }


def transport_and_verify(out_dir, attempt_id, stream=None, blob_transport=None):
    """Emit the envelope and prove a recovery reproduces every exact byte.

    Returns the reconstruction receipt. Raises on any incomplete recovery, so
    no caller can reach a pass authorization on a truncated capture.
    """
    stream = stream if stream is not None else sys.stdout
    payloads = {}
    for name in TRANSPORT.REPLAY_ARTIFACTS:
        with open(os.path.join(out_dir, name), "rb") as handle:
            payloads[name] = handle.read()

    lines = TRANSPORT.encode(attempt_id, payloads)
    for line in lines:
        stream.write(line + "\n")
    stream.flush()

    recovered = TRANSPORT.recover("\n".join(lines), attempt_id=attempt_id)
    for name, original in payloads.items():
        if recovered.get(name) != original:
            raise GateRefused(
                "the transport recovery did not reproduce %s byte-for-byte; a "
                "truncated or reordered capture is not a replay pass" % name)
    receipt = TRANSPORT.reconstruction_receipt(attempt_id, recovered)
    receipt["verified_against_the_written_artifacts"] = True
    receipt["lines"] = len(lines)
    receipt["total_bytes"] = sum(len(payload) for payload in payloads.values())

    if blob_transport is not None:
        blob_receipt = blob_transport.upload_directory(
            out_dir, list(TRANSPORT.REPLAY_ARTIFACTS))
        receipt["blob"] = blob_receipt

    return receipt


def write_transport_receipt(out_dir, outcome):
    """Persist the transport receipt beside the artifacts it vouches for.

    The successor reads this file to decide whether a pass authorization is
    backed by verified bytes. Writing it is therefore part of the gate, not a
    convenience: without it the authorization is unsupported and refused.
    """
    receipt = outcome["transport"]
    objects = []
    for name in TRANSPORT.REPLAY_ARTIFACTS:
        with open(os.path.join(out_dir, name), "rb") as handle:
            raw = handle.read()
        objects.append({"name": name, "bytes": len(raw),
                        "sha256": _sha256(raw)})
    document = {
        "schema_version": TRANSPORT_RECEIPT_SCHEMA_VERSION,
        "attempt_id": outcome["attempt_id"],
        "state": outcome["state"],
        "verified": bool(receipt.get("verified_against_the_written_artifacts")),
        "authorizes_model_pilot": bool(outcome["passed"]),
        "objects": objects,
        "total_bytes": receipt["total_bytes"],
        "lines": receipt.get("lines"),
        "durable_object_store": receipt.get("blob"),
        "a_log_line_is_not_a_result": True,
    }
    payload = GATE.dumps(document).encode("utf-8")
    path = os.path.join(out_dir, TRANSPORT_RECEIPT_NAME)
    with open(path, "wb") as handle:
        handle.write(payload)
    return {"name": TRANSPORT_RECEIPT_NAME, "bytes": len(payload),
            "sha256": _sha256(payload)}


def run(out_dir, authorization=None, image_digest=None, ready_commit=None,
        lock_bytes=None, root=None, stream=None, blob_factory=None,
        execution_name=None):
    """Gate, transport, verify, and only then authorize."""
    stream = stream if stream is not None else sys.stdout
    import p0_r1_blob_transport as BLOB

    outcome = gate_run_v2(
        out_dir, authorization=authorization, image_digest=image_digest,
        ready_commit=ready_commit, lock_bytes=lock_bytes, root=root,
        execution_name=execution_name)

    blob_transport = None
    if blob_factory is not None:
        blob_transport = blob_factory(outcome["attempt_id"])
        if blob_transport.prefix != BLOB.attempt_prefix(outcome["attempt_id"]):
            raise GateRefused(
                "the durable transport prefix is not the attempt-bound prefix")
        for document in (outcome["result"], outcome["receipt"]):
            document["identities"]["output_prefix"] = blob_transport.prefix
        GATE._write_artifacts(
            out_dir, outcome["result"], outcome["receipt"],
            outcome["result"]["counters"],
            GATE._disposition_markdown(
                outcome["state"], outcome["result"]["corrected_matrix_summary"],
                outcome["result"]["factorization"],
                outcome["result"]["stop_reason"],
                {"image": {"digest": outcome["result"]["image_digest"]},
                 "executable_code": {
                     "commit": outcome["result"]["executable_code_commit"]}}))

    receipt = transport_and_verify(
        out_dir, outcome["attempt_id"], stream=stream,
        blob_transport=blob_transport)
    outcome["transport"] = receipt
    outcome["receipt"]["transport"]["complete_byte_recovery_verified"] = True
    outcome["receipt"]["transport"]["reconstruction"] = {
        "artifacts": receipt["artifacts"],
        "total_bytes": receipt["total_bytes"],
    }

    stream.write("%s\n" % TRANSPORT_VERIFIED_LINE)
    stream.write("P0_R1_REPLAY_STATE=%s\n" % outcome["state"])
    stream.write("P0_R1_REPLAY_ATTEMPT_ID=%s\n" % outcome["attempt_id"])

    written = write_transport_receipt(out_dir, outcome)
    outcome["artifacts"] = list(outcome.get("artifacts") or []) + [written]
    stream.write("ARTIFACT=%s SHA256=%s BYTES=%d\n"
                 % (written["name"], written["sha256"], written["bytes"]))

    if outcome["passed"]:
        stream.write("%s\n" % PASS_AUTHORIZATION_LINE)
    else:
        stream.write("P0_R1_REPLAY_GATE_FAILED_AUTHORIZES_NOTHING=1\n")
    stream.flush()
    return outcome


def implementation_identity(root=None):
    path = os.path.abspath(__file__) if root is None else os.path.join(
        root, "studies", "study3", "pilot", "p0_r1", "p0_r1_replay_gate_v2.py")
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": "studies/study3/pilot/p0_r1/p0_r1_replay_gate_v2.py",
        "bytes": len(raw),
        "sha256": _sha256(raw),
        "scientific_logic_is_imported_unchanged_from":
            "studies/study3/pilot/p0_r1/p0_r1_replay_gate.py",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--authorization")
    parser.add_argument("--successor-authorization", dest="authorization")
    parser.add_argument("--out-dir")
    parser.add_argument("--src")
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-commit")
    parser.add_argument("--lock-file")
    parser.add_argument("--execution-name")
    parser.add_argument("--blob", action="store_true")
    args = parser.parse_args(argv)

    if not args.gate:
        parser.print_help()
        return 2

    lock_bytes = None
    if args.lock_file:
        with open(args.lock_file, "rb") as handle:
            lock_bytes = handle.read()

    blob_transport = None
    if args.blob:
        import p0_r1_blob_transport as BLOB

        def blob_factory(attempt_id):
            return BLOB.PrivateBlobTransport(attempt_id)
    else:
        blob_factory = None

    try:
        outcome = run(
            args.out_dir, authorization=args.authorization,
            image_digest=args.image_digest, ready_commit=args.ready_commit,
            lock_bytes=lock_bytes, execution_name=args.execution_name,
            root=args.src, blob_factory=blob_factory)
    except (GateRefused, LOCK.LockDefect) as exc:
        print("P0_R1_REPLAY_GATE_REFUSED=1")
        print("  FAIL %s" % exc)
        return 1
    return 0 if outcome["passed"] else 3


if __name__ == "__main__":
    sys.exit(main())
