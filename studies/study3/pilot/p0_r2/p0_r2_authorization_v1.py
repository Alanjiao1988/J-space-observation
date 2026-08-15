#!/usr/bin/env python3
"""Build the conditional P0-R2 pilot authorization, or refuse to.

Authorization is *derived*, never asserted. It exists only when all four
independent objects agree:

1. the active generation-1 lock;
2. a replay receipt that a reconstruction actually carries;
3. that independent reconstruction receipt;
4. a current governance-chain proof over the published head.

Building this document performs no Azure operation. It is the gate that must
succeed *before* anything is created, so that a refusal costs nothing.

This module never authorizes anything by default: absent any one input, it
raises. It is model-free and performs no model, tokenizer, checkpoint, GPU,
scoring or evidence operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_closure_binding_v1 as CLOSURE  # noqa: E402
import p0_r2_verify_replay_receipt as VERIFY  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-pilot-authorization-v1"
STAGE = "STUDY3-P0-R2"
GPU_JOB = "job-jspace-s3-p0r2-pilot-g1"
ATTEMPT_PREFIX = "p0r2-g1-"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class AuthorizationDefect(Exception):
    """The bounded pilot cannot be authorized from the published evidence."""


def _load(path, label):
    if not path:
        raise AuthorizationDefect("%s is required" % label)
    try:
        raw = Path(path).read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise AuthorizationDefect("%s is unreadable: %s" % (label, exc))
    if not isinstance(document, dict):
        raise AuthorizationDefect("%s is not a JSON object" % label)
    return document, raw


def build(*, lock_file, replay_receipt, reconstruction_receipt, head_proof,
          attempt=None) -> dict:
    lock, lock_raw = _load(lock_file, "execution lock")
    if lock.get("state") != "STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE":
        raise AuthorizationDefect(
            "the lock state %r is not the ready-awaiting-replay state"
            % lock.get("state"))
    if lock.get("superseded") is not False:
        raise AuthorizationDefect("the lock is superseded")

    image = lock.get("image") or {}
    digest = image.get("digest")
    if not _DIGEST.fullmatch(str(digest or "")):
        raise AuthorizationDefect("the lock does not bind a pinned digest")
    executable = lock.get("executable_code") or {}
    executable_commit = executable.get("commit")

    proof, proof_raw = _load(head_proof, "governance chain proof")
    try:
        CLOSURE.validate_proof(proof, executable_commit=executable_commit)
    except CLOSURE.ClosureBindingDefect as exc:
        raise AuthorizationDefect(
            "the current head proof is not valid: %s" % exc) from exc

    try:
        validation = VERIFY.validate(
            replay_receipt=replay_receipt,
            reconstruction_receipt=reconstruction_receipt,
            expected_image_digest=digest,
            expected_executable_commit=executable_commit)
    except VERIFY.ReplayReceiptDefect as exc:
        raise AuthorizationDefect(
            "the replay evidence does not authorize a pilot: %s" % exc
        ) from exc

    replay_attempt = validation.get("attempt_id")
    if attempt:
        pilot_attempt = attempt
    elif isinstance(replay_attempt, str):
        pilot_attempt = replay_attempt.replace("live-", "pilot-", 1)
    else:
        pilot_attempt = None
    if not isinstance(pilot_attempt, str) \
            or not pilot_attempt.startswith(ATTEMPT_PREFIX):
        raise AuthorizationDefect(
            "the pilot attempt %r does not use the %r namespace"
            % (pilot_attempt, ATTEMPT_PREFIX))

    caps = lock.get("caps") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "outcome": "AUTHORIZED",
        "attempt_id": pilot_attempt,
        "replay_attempt_id": replay_attempt,
        "acr_run_id": validation.get("acr_run_id"),
        "image_digest": digest,
        "image": image.get("reference"),
        "executable_commit": executable_commit,
        "executable_tree": executable.get("tree"),
        "gpu_job": GPU_JOB,
        "evidence": {
            "lock": {"bytes": len(lock_raw),
                     "sha256": hashlib.sha256(lock_raw).hexdigest()},
            "head_proof": {"bytes": len(proof_raw),
                           "sha256": hashlib.sha256(proof_raw).hexdigest()},
            "replay_receipt": validation["replay_receipt"],
            "reconstruction_receipt": validation["reconstruction_receipt"],
        },
        "caps": {
            "max_smoke_prefills_before_extension": caps.get(
                "max_smoke_prefills_before_extension"),
            "max_non_generative_prefills": caps.get(
                "max_non_generative_prefills"),
            "max_s4_generations": caps.get("max_s4_generations"),
            "max_model_evaluation_equivalents": caps.get(
                "max_model_evaluation_equivalents"),
            "possible_scored_rows": caps.get("possible_scored_rows"),
        },
        "authorizes_exactly_one_execution": True,
        "authorizes_job_update": False,
        "azure_operations_performed": 0,
        "model_operations_performed_building_this_document": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_authorization_v1.py",
        "stage": STAGE,
        "requires": ["lock", "replay_receipt", "reconstruction_receipt",
                     "head_proof"],
        "authorizes_without_reconstruction": False,
        "performs_azure_operations": False,
        "gpu_job": GPU_JOB,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--build", action="store_true")
    parser.add_argument("--lock-file")
    parser.add_argument("--replay-receipt")
    parser.add_argument("--reconstruction-receipt")
    parser.add_argument("--head-proof")
    parser.add_argument("--attempt")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    try:
        document = build(
            lock_file=args.lock_file, replay_receipt=args.replay_receipt,
            reconstruction_receipt=args.reconstruction_receipt,
            head_proof=args.head_proof, attempt=args.attempt)
    except AuthorizationDefect as exc:
        print("P0_R2_PILOT_AUTHORIZATION_REFUSED=1", file=sys.stderr)
        print("  %s" % exc, file=sys.stderr)
        return 3
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    print("P0_R2_PILOT_AUTHORIZED=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
