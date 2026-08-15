#!/usr/bin/env python3
"""Study 3 P0-R2 generation-2 replay gate.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
sections 5, 11 and 12.

Section 5 forbids changing the replay factorization logic, the scientific
semantics, the artifact schemas beyond additive generation identity, and the
scientific bytes. This gate changes none of them: it delegates to exactly the
same unchanged P0-R1 generation-3 modules the generation-1 gate delegates to,
verifies them by SHA-256 before importing them, and emits exactly the same four
canonical artifacts through exactly the same envelope format.

What it changes is identity and namespace, which section 4 requires: the attempt
belongs to ``p0r2-g2-``, the envelope is encoded under the generation-2
transport instance, and the emitted documents declare generation 2.

It is one-shot. It refuses if any of the four artifacts already exists, and it
never reruns in place.

Model-free with respect to P0-R2 itself: this module constructs no tokenizer,
downloads no checkpoint, loads no weight and allocates no GPU.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_namespace_g2 as NS  # noqa: E402
import p0_r2_replay_gate_v1 as G1  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-replay-gate-g2"
RESULT_SCHEMA_VERSION = "study3-p0-r2-replay-result-g2"
RECEIPT_SCHEMA_VERSION = "study3-p0-r2-replay-receipt-g2"
COUNTERS_SCHEMA_VERSION = "study3-p0-r2-replay-counters-g2"
STAGE = "STUDY3-P0-R2"
GENERATION = 2

#: The generation-2 successor session authorization. Disjoint from generation 1
#: so a generation-1 authorization string can never open this gate.
SUCCESSOR_AUTHORIZATION = "p0-r2-generation-2-successor-session"

RESULT_NAME = G1.RESULT_NAME
RECEIPT_NAME = G1.RECEIPT_NAME
COUNTERS_NAME = G1.COUNTERS_NAME
DISPOSITION_NAME = G1.DISPOSITION_NAME

DELEGATED_SCIENTIFIC_MODULES = tuple(G1.DELEGATED_SCIENTIFIC_MODULES)
ZERO_COUNTERS = tuple(G1.ZERO_COUNTERS)


class GateRefused(Exception):
    """The gate refuses; no envelope is spent and nothing is written."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _dumps(document) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")


def verify_delegated_science(bound: dict, *, root=None) -> list:
    """Delegated verbatim to the generation-1 implementation, unchanged."""
    try:
        return G1.verify_delegated_science(bound, root=root)
    except G1.GateRefused as exc:
        raise GateRefused(str(exc))


def run(out_dir, *, authorization=None, attempt_id=None, image_digest=None,
        ready_anchor=None, lock_bytes=None, root=None, registry=None,
        counters=None, stream=None) -> dict:
    """Run the delegated factorization replay under generation-2 identities."""
    if authorization != SUCCESSOR_AUTHORIZATION:
        raise GateRefused(
            "the generation-2 replay gate requires explicit generation-2 "
            "successor authorization")
    if not out_dir:
        raise GateRefused("the replay gate requires a writable result directory")
    out_dir = Path(out_dir)
    for name in (RESULT_NAME, RECEIPT_NAME, COUNTERS_NAME, DISPOSITION_NAME):
        if (out_dir / name).exists():
            raise GateRefused(
                "%s already exists; the one-shot gate is never rerun in place"
                % name)

    transport = NS.transport()
    try:
        transport.validate_attempt_id(attempt_id)
    except transport.TransportDefect as exc:
        raise GateRefused("the generation-2 attempt id is invalid: %s" % exc)
    if not str(attempt_id).startswith(NS.LIVE_ATTEMPT_PREFIX):
        raise GateRefused(
            "the live replay attempt must begin %r" % NS.LIVE_ATTEMPT_PREFIX)

    if not isinstance(lock_bytes, (bytes, bytearray)) or not lock_bytes:
        raise GateRefused("the exact generation-2 lock bytes are mandatory")
    try:
        lock = json.loads(bytes(lock_bytes).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise GateRefused("the lock is unreadable: %s" % exc)
    if lock.get("generation") != GENERATION:
        raise GateRefused(
            "the lock is for generation %r; this gate is generation %d"
            % (lock.get("generation"), GENERATION))
    if (lock.get("image") or {}).get("digest") != image_digest:
        raise GateRefused(
            "the supplied image digest is not the digest the lock binds")

    bound = {entry["path"]: entry
             for entry in (lock.get("delegated_scientific_modules") or [])
             if isinstance(entry, dict) and entry.get("path")}
    verified = verify_delegated_science(bound, root=root)

    # Only now is unchanged P0-R1 science imported and delegated to.
    import p0_r1_factorization as FACT  # noqa: E402
    import p0_r1_replay_gate as GATE  # noqa: E402
    from p0_r1_counters import P0R1Counters  # noqa: E402

    counters = counters if counters is not None else P0R1Counters()
    registry = registry if registry is not None else GATE.load_registry()

    stop_reason = None
    try:
        immutable_sources = FACT.verify_immutable_sources(root=root)
    except FACT.FactorizationDefect as exc:
        immutable_sources = []
        stop_reason = "immutable P0-R1/P0-T sources did not verify: %s" % exc

    factorization = None
    if stop_reason is None:
        try:
            factorization = FACT.gate(registry, root=root, counters=counters)
        except FACT.FactorizationDefect as exc:
            stop_reason = "the replay factorization gate failed: %s" % exc

    passed = stop_reason is None
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "attempt_id": attempt_id,
        "outcome": "PASS" if passed else "STOP",
        "stop_reason": stop_reason,
        "image_digest": image_digest,
        "ready_anchor": ready_anchor,
        "executable_commit": (lock.get("image_executable") or {}).get("commit")
        or (lock.get("executable_code") or {}).get("commit"),
        "authority_sha256": (lock.get("authority") or {}).get("sha256"),
        "delegated_scientific_modules": verified,
        "science_is_unchanged_p0_r1_generation3": True,
        "replay_factorization_logic_changed": False,
        "immutable_sources": immutable_sources,
        "factorization": factorization,
    }
    counters_document = {name: 0 for name in ZERO_COUNTERS}
    counters_document.update({
        "schema_version": COUNTERS_SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "attempt_id": attempt_id,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    })
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "attempt_id": attempt_id,
        "outcome": result["outcome"],
        "image_digest": image_digest,
        "executable_commit": result["executable_commit"],
        "ready_anchor": ready_anchor,
        "lock": {"bytes": len(bytes(lock_bytes)),
                 "sha256": _sha256(bytes(lock_bytes))},
        "result": {"name": RESULT_NAME},
        "one_shot_envelope_consumed": True,
        "authorizes_model_pilot": False,
        "authorization_requires_independent_reconstruction": True,
        "model_operations_performed": 0,
    }
    disposition = (
        "# P0-R2 generation-2 replay disposition\n\n"
        "- generation: **2**\n- attempt: `%s`\n- outcome: **%s**\n"
        "- image digest: `%s`\n- ready anchor: `%s`\n"
        "- science: unchanged P0-R1 generation-3 modules, verified by SHA-256 "
        "before import\n- model operations performed: 0\n\n"
        "This receipt authorizes no model operation. A bounded pilot requires "
        "an independent reconstruction of these bytes from the captured raw "
        "log plus a current published-head proof.\n"
        % (attempt_id, result["outcome"], image_digest, ready_anchor))

    artifacts = {
        RESULT_NAME: _dumps(result),
        RECEIPT_NAME: _dumps(receipt),
        COUNTERS_NAME: _dumps(counters_document),
        DISPOSITION_NAME: disposition.encode("utf-8"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        with (out_dir / name).open("xb") as handle:
            handle.write(payload)

    envelope = transport.encode(attempt_id, artifacts)
    target = stream if stream is not None else sys.stdout
    for line in envelope:
        print(line, file=target)
    print("P0_R2_G2_REPLAY_ATTEMPT_ID=%s" % attempt_id, file=target)
    print("P0_R2_G2_REPLAY_OUTCOME=%s" % result["outcome"], file=target)
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0", file=target)

    if not passed:
        raise GateRefused(
            "the replay gate stopped: %s. Publish the stop and perform no "
            "model operation; never rerun the gate." % stop_reason)
    return {"result": result, "receipt": receipt,
            "counters": counters_document, "artifacts": list(artifacts)}


def implementation_identity() -> dict:
    transport = NS.transport()
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_replay_gate_g2.py",
        "stage": STAGE,
        "generation": GENERATION,
        "delegated_scientific_modules": list(DELEGATED_SCIENTIFIC_MODULES),
        "delegates_to_generation1_verification": True,
        "copies_or_edits_science": False,
        "replay_factorization_logic_changed": False,
        "verifies_science_by_sha256_before_import": True,
        "one_shot": True,
        "reruns_in_place": False,
        "artifact_allow_list": list(transport.REPLAY_ARTIFACTS),
        "attempt_prefix": transport.ATTEMPT_ID_PREFIX,
        "live_attempt_prefix": NS.LIVE_ATTEMPT_PREFIX,
        "authorizes_model_pilot": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--out-dir")
    parser.add_argument("--attempt")
    parser.add_argument("--lock-file")
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-anchor")
    parser.add_argument("--root")
    parser.add_argument("--authorization")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    try:
        lock_bytes = Path(args.lock_file).read_bytes() if args.lock_file else b""
        run(args.out_dir,
            authorization=args.authorization
            or os.environ.get("P0_R2_G2_GATE_AUTHORIZATION"),
            attempt_id=args.attempt, image_digest=args.image_digest,
            ready_anchor=args.ready_anchor, lock_bytes=lock_bytes,
            root=args.root)
    except (GateRefused, OSError) as exc:
        print("P0_R2_G2_REPLAY_GATE_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
