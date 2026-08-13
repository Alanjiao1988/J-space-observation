#!/usr/bin/env python3
"""Generation-3 replay gate: same science, honest receipt, both routes.

The registered replay-only factorization gate is unchanged and is imported from
the generation-2 implementation. Not one scientific byte differs: the same
immutable P0-T artifacts are read, the same factorization is derived with zero
tokenizer encodes, and the same pass/stop boundary applies.

Two wiring properties change.

First, the emitted receipt is never rewritten. Generation 2 wrote the receipt
with ``transport.complete_byte_recovery_verified = false``, transported those
bytes, and then set the field to ``true`` on an in-memory copy that nobody
downstream ever saw. The recovered receipt therefore always said ``false`` and
the launcher always required ``true``. Generation 3 leaves the field ``false``
and says so explicitly in the document, because the gate genuinely cannot know
whether a future operator recovery will succeed. That proof lives in the
independent reconstruction receipt.

Second, the gate is bound to the generation-3 lock and emits its complete bytes
through the console envelope before it reports a pass, so a pass is never
reported for artifacts that could not be transported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_replay_gate_v2 as GATE_V2  # noqa: E402
import p0_r1_transport as TRANSPORT  # noqa: E402
import p0_r1_execution_lock_v3 as LOCK  # noqa: E402
import p0_r1_factorization as FACT  # noqa: E402
import p0_r1_eligibility as ELIG  # noqa: E402
import p0_r1_replay_gate as GATE  # noqa: E402
import p0_r1_runtime_binding as RUNTIME  # noqa: E402
from p0_r1_counters import P0R1Counters  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-replay-gate-v3"
GATE_RESULT_SCHEMA_VERSION = "study3-p0-r1-replay-gate-result-v3"
GATE_RECEIPT_SCHEMA_VERSION = "study3-p0-r1-replay-gate-receipt-v3"

GateRefused = GATE_V2.GateRefused

PASS_STATE = GATE_V2.STATE_AFTER_REPLAY_PASS
TRANSPORT_VERIFIED_LINE = GATE_V2.TRANSPORT_VERIFIED_LINE
PASS_AUTHORIZATION_LINE = GATE_V2.PASS_AUTHORIZATION_LINE

RECEIPT_NAME = "p0_r1_replay_receipt.json"


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def mint_attempt_id(executable_code_commit, now=None):
    return "gen3-%s-%s" % (
        executable_code_commit[:12], now or GATE.utc_now())


def gate_run_v3(out_dir, authorization=None, image_digest=None,
                ready_commit=None, lock_bytes=None, root=None, registry=None,
                counters=None, execution_name=None, now=None):
    """Run unchanged factorization science under the generation-3 bindings."""
    if authorization != GATE_V2.SUCCESSOR_AUTHORIZATION:
        raise GateRefused(
            "the replay gate requires explicit successor-session authorization")
    if not out_dir:
        raise GateRefused("the replay gate requires a writable result directory")
    if not ready_commit or len(str(ready_commit)) != 40 \
            or any(character not in "0123456789abcdef"
                   for character in str(ready_commit)):
        raise GateRefused("the proved ready anchor is mandatory")
    if not isinstance(lock_bytes, bytes):
        raise GateRefused("the exact generation-3 lock bytes are mandatory")
    try:
        lock = json.loads(lock_bytes.decode("utf-8"))
        LOCK.validate(lock, root=root, image_digest=image_digest)
    except (UnicodeDecodeError, ValueError, LOCK.LockDefect,
            KeyError, TypeError) as exc:
        raise GateRefused("the generation-3 lock is invalid: %s" % exc)
    lock_identity = {
        "path": "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v3.json",
        "bytes": len(lock_bytes),
        "sha256": _sha256(lock_bytes),
    }

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
        state = GATE_V2.STATE_REPLAY_DEFECT
        summary = {
            "cells": 0, "eligible_cells": 0, "ineligible_cells": 0,
            "ineligible_cells_with_an_empty_reason_list": 0,
            "structurally_absent_pairs": 0,
            "executable_genuine_i3_contrasts_per_role": {},
            "roles_without_executable_contrast": list(GATE_V2.ROLES),
        }
        corrected = None
    else:
        result = FACT.load_immutable(FACT.RESULT_PATH, root=root)
        corrected = ELIG.classify(
            result["records"], factorization,
            GATE.published_s1_surfaces(result), GATE_V2.ROLES)
        ELIG.validate_matrix(corrected["matrix"], roles=GATE_V2.ROLES)
        summary = GATE._matrix_summary(corrected)
        findings = GATE.check_corrected_matrix(summary)
        if findings:
            stop_reason = (
                "The corrected eligibility matrix did not reproduce the "
                "registered acceptance conditions:\n\n"
                + "\n".join("* %s" % finding for finding in findings))
            state = (ELIG.STOP_SOME_ROLE_HAS_NO_EXECUTABLE_CONTRAST
                     if summary["roles_without_executable_contrast"]
                     else GATE_V2.STATE_REPLAY_DEFECT)
        else:
            state = PASS_STATE

    snapshot = counters.snapshot()
    counter_findings = GATE._counter_guard(snapshot)
    if counter_findings and state == PASS_STATE:
        stop_reason = (
            "The replay gate counters did not reconcile:\n\n"
            + "\n".join("* %s" % finding for finding in counter_findings))
        state = GATE_V2.STATE_REPLAY_DEFECT
        findings += counter_findings
    passed = state == PASS_STATE
    identities = RUNTIME.bound_identities(
        lock, {"attempt_id": attempt_id, "execution_lock": lock_identity},
        ready_commit, execution_name=execution_name)

    result_document = {
        "schema_version": GATE_RESULT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_replay_gate_result",
        "generation": 3,
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
        "target_roles": list(GATE_V2.ROLES),
        "tokenizer_encodes_performed": 0,
        "tokenizer_constructions_performed": 0,
        "model_operations_performed": 0,
        "gpu_allocated": False,
        "factorization": factorization,
        "corrected_matrix": corrected["matrix"] if corrected else [],
        "structurally_absent": (
            corrected["structurally_absent"] if corrected else []),
        "executable_genuine_i3_contrasts": (
            corrected["executable_genuine_i3_contrasts"]
            if corrected else {}),
        "corrected_matrix_summary": summary,
        "acceptance_findings": findings,
        "stop_reason": stop_reason,
        "counters": snapshot,
        "evidence_status": (
            "a methods-feasibility replay observation over immutable evidence; "
            "it selects no interface and answers no research question"),
    }
    receipt_document = {
        "schema_version": GATE_RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_replay_gate_receipt",
        "generation": 3,
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
            "exactly one bounded GPU model pilot for this attempt"
            if passed else "nothing"),
    }
    disposition = GATE._disposition_markdown(
        state, summary, factorization, stop_reason, lock)
    result_payload = GATE.dumps(result_document).encode("utf-8")
    receipt_document["result_document"] = {
        "name": GATE.GATE_RESULT_NAME,
        "bytes": len(result_payload),
        "sha256": _sha256(result_payload),
    }
    annotate_receipt_honestly(receipt_document)
    written = GATE._write_artifacts(
        out_dir, result_document, receipt_document, snapshot, disposition)
    return {
        "state": state, "passed": passed, "attempt_id": attempt_id,
        "ready_commit": ready_commit, "result": result_document,
        "receipt": receipt_document, "artifacts": written,
        "out_dir": out_dir, "execution_lock": lock_identity,
        "identities": identities,
    }


def annotate_receipt_honestly(receipt):
    """State plainly why the recovery flag is false in the emitted bytes."""
    transport = receipt.setdefault("transport", {})
    transport["complete_byte_recovery_verified"] = False
    transport["self_attestation_refused"] = (
        "this document is the exact byte sequence the gate emitted. It cannot "
        "claim that its own later recovery succeeded, because that had not "
        "happened when these bytes were fixed. Proof of complete-byte "
        "recovery is the separate reconstruction receipt built from the "
        "captured raw log by an independent reader.")
    transport["recovery_proof_document"] = (
        "p0_r1_replay_reconstruction_receipt_v3.json")
    return receipt


def run(out_dir, lock_bytes=None, image_digest=None, ready_commit=None,
        root=None, stream=None, blob_factory=None, execution_name=None):
    """Gate, annotate honestly, transport complete bytes, then report."""
    stream = stream if stream is not None else sys.stdout

    outcome = gate_run_v3(
        out_dir, authorization=GATE_V2.SUCCESSOR_AUTHORIZATION,
        image_digest=image_digest,
        ready_commit=ready_commit, lock_bytes=lock_bytes, root=root,
        execution_name=execution_name)

    payloads = {}
    for name in TRANSPORT.REPLAY_ARTIFACTS:
        with open(os.path.join(out_dir, name), "rb") as handle:
            payloads[name] = handle.read()

    lines = TRANSPORT.encode(outcome["attempt_id"], payloads)
    for line in lines:
        stream.write(line + "\n")

    recovered = TRANSPORT.recover("\n".join(lines),
                                  attempt_id=outcome["attempt_id"])
    for name, original in payloads.items():
        if recovered.get(name) != original:
            raise GateRefused(
                "the emitted envelope does not reproduce %s byte-for-byte; "
                "a pass is never reported for untransportable artifacts"
                % name)

    stream.write("%s\n" % TRANSPORT_VERIFIED_LINE)
    stream.write("P0_R1_REPLAY_STATE=%s\n" % outcome["state"])
    stream.write("P0_R1_REPLAY_ATTEMPT_ID=%s\n" % outcome["attempt_id"])
    stream.write("P0_R1_REPLAY_RECEIPT_SELF_ATTESTATION=refused\n")
    if outcome["passed"]:
        stream.write("%s\n" % PASS_AUTHORIZATION_LINE)
        stream.write("P0_R1_REPLAY_PASS_REQUIRES_RECONSTRUCTION_RECEIPT=1\n")
    else:
        stream.write("P0_R1_REPLAY_GATE_FAILED_AUTHORIZES_NOTHING=1\n")
    stream.flush()
    return outcome


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_replay_gate_v3.py",
        "delegates_science_to":
            "p0_r1_factorization + p0_r1_eligibility + p0_r1_replay_gate",
        "changes_any_scientific_rule": False,
        "rewrites_its_own_receipt": False,
        "emitted_receipt_claims_its_own_recovery": False,
        "recovery_proof_document":
            "p0_r1_replay_reconstruction_receipt_v3.json",
        "closes": "G2-03",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--lock-file")
    parser.add_argument("--out-dir")
    parser.add_argument("--src")
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-commit")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.gate:
        if not args.lock_file or not args.out_dir:
            print("FAIL: --gate requires --lock-file and --out-dir",
                  file=sys.stderr)
            return 2
        with open(args.lock_file, "rb") as handle:
            lock_bytes = handle.read()
        try:
            outcome = run(args.out_dir, lock_bytes=lock_bytes,
                          image_digest=args.image_digest,
                          ready_commit=args.ready_commit, root=args.src)
        except GateRefused as exc:
            print("P0_R1_REPLAY_GATE_REFUSED=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        return 0 if outcome["passed"] else 4

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
