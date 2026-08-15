#!/usr/bin/env python3
"""The P0-R2 one-shot replay gate: a wrapper, not a reimplementation.

P0-R2 is an infrastructure successor. Its science must be *the same bytes* that
P0-R1 generation 3 ran, so this module deliberately owns almost nothing:

* it verifies, by SHA-256, that each P0-R1 scientific module on disk is the
  exact blob the lock binds, and refuses before importing anything otherwise;
* it then delegates the factorization replay to unchanged
  ``p0_r1_factorization`` -- no copy, no edit, no "cleaned up" variant;
* it owns only the P0-R2 identities: the four canonical artifact names, the
  ``p0r2-g1-`` attempt grammar, and the ``P0R2TX*`` envelope.

The gate is one-shot. It refuses to run in a directory that already holds a
result, so a second invocation cannot quietly overwrite the first outcome.

Calling this module performs no model operation: the factorization replay reads
published P0-T evidence and constructs no tokenizer, downloads no checkpoint,
loads no weight, allocates no GPU, and adds no evidence row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys


P0_R2_DIR = Path(__file__).resolve().parent
P0_R1_DIR = P0_R2_DIR.parent / "p0_r1"
for _candidate in (P0_R2_DIR, P0_R1_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

import p0_r2_transport as TRANSPORT  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-replay-gate-v1"
RESULT_SCHEMA_VERSION = "study3-p0-r2-replay-gate-result-v1"
RECEIPT_SCHEMA_VERSION = "study3-p0-r2-replay-gate-receipt-v1"
STAGE = "STUDY3-P0-R2"

RESULT_NAME = "p0_r2_replay_result.json"
RECEIPT_NAME = "p0_r2_replay_receipt.json"
COUNTERS_NAME = "p0_r2_replay_counters.json"
DISPOSITION_NAME = "P0_R2_REPLAY_DISPOSITION.md"

#: Only a successor session that says this exact phrase may spend the envelope.
SUCCESSOR_AUTHORIZATION = "p0-r2-generation-1-successor-session"

#: The exact P0-R1 scientific modules P0-R2 reuses. Delegation targets only.
DELEGATED_SCIENTIFIC_MODULES = (
    "studies/study3/pilot/p0_r1/p0_r1_factorization.py",
    "studies/study3/pilot/p0_r1/p0_r1_eligibility.py",
    "studies/study3/pilot/p0_r1/p0_r1_protocol.py",
    "studies/study3/pilot/p0_r1/p0_r1_counters.py",
)

ZERO_COUNTERS = (
    "tokenizer_constructions", "tokenizer_encodes", "checkpoint_downloads",
    "checkpoint_loads", "model_weight_loads", "prefills", "generations",
    "scored_rows", "evidence_rows_added", "gpu_allocations",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class GateRefused(Exception):
    """The replay gate refuses; no envelope is spent and nothing is written."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _dumps(document) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")


def verify_delegated_science(bound: dict, *, root=None) -> list:
    """Refuse before importing if any scientific byte is not the bound byte."""
    root = Path(root or (P0_R2_DIR.parent.parent.parent.parent)).resolve()
    if not isinstance(bound, dict) or not bound:
        raise GateRefused(
            "the lock does not bind any P0-R1 scientific module; P0-R2 may "
            "not invent its own science")
    verified = []
    for relative in DELEGATED_SCIENTIFIC_MODULES:
        expected = bound.get(relative)
        if not isinstance(expected, dict):
            raise GateRefused(
                "%s is not bound by the lock; refusing to delegate to an "
                "unbound scientific module" % relative)
        path = root / relative
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise GateRefused("%s is unreadable: %s" % (relative, exc))
        actual = {"bytes": len(payload), "sha256": _sha256(payload)}
        if not _SHA256.fullmatch(str(expected.get("sha256") or "")):
            raise GateRefused("%s has a malformed bound sha256" % relative)
        if actual["sha256"] != expected["sha256"] \
                or actual["bytes"] != expected.get("bytes"):
            raise GateRefused(
                "%s is %d bytes sha256 %s, not the bound %s bytes sha256 %s; "
                "P0-R2 must run the exact P0-R1 generation-3 science"
                % (relative, actual["bytes"], actual["sha256"],
                   expected.get("bytes"), expected.get("sha256")))
        verified.append(dict(actual, path=relative,
                             git_blob=expected.get("git_blob")))
    return verified


def run(out_dir, *, authorization=None, attempt_id=None, image_digest=None,
        ready_anchor=None, lock_bytes=None, root=None, registry=None,
        counters=None, stream=None) -> dict:
    """Run the delegated factorization replay under P0-R2 identities."""
    if authorization != SUCCESSOR_AUTHORIZATION:
        raise GateRefused(
            "the P0-R2 replay gate requires explicit successor authorization")
    if not out_dir:
        raise GateRefused("the replay gate requires a writable result directory")
    out_dir = Path(out_dir)
    for name in (RESULT_NAME, RECEIPT_NAME, COUNTERS_NAME, DISPOSITION_NAME):
        if (out_dir / name).exists():
            raise GateRefused(
                "%s already exists; the one-shot gate is never rerun in place"
                % name)
    try:
        TRANSPORT.validate_attempt_id(attempt_id)
    except TRANSPORT.TransportDefect as exc:
        raise GateRefused("the P0-R2 attempt id is invalid: %s" % exc)
    if not isinstance(lock_bytes, (bytes, bytearray)) or not lock_bytes:
        raise GateRefused("the exact generation-1 lock bytes are mandatory")
    try:
        lock = json.loads(bytes(lock_bytes).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise GateRefused("the lock is unreadable: %s" % exc)
    if lock.get("image", {}).get("digest") != image_digest:
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
        "generation": 1,
        "attempt_id": attempt_id,
        "outcome": "PASS" if passed else "STOP",
        "stop_reason": stop_reason,
        "image_digest": image_digest,
        "ready_anchor": ready_anchor,
        "executable_commit": (lock.get("executable_code") or {}).get("commit"),
        "delegated_scientific_modules": verified,
        "science_is_unchanged_p0_r1_generation3": True,
        "immutable_sources": immutable_sources,
        "factorization": factorization,
    }
    counters_document = {name: 0 for name in ZERO_COUNTERS}
    counters_document.update({
        "schema_version": "study3-p0-r2-replay-counters-v1",
        "stage": STAGE,
        "attempt_id": attempt_id,
        "model_operations_performed": 0,
    })
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "stage": STAGE,
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
        "# P0-R2 replay disposition\n\n"
        "- attempt: `%s`\n- outcome: **%s**\n- image digest: `%s`\n"
        "- ready anchor: `%s`\n- science: unchanged P0-R1 generation-3 "
        "modules, verified by SHA-256 before import\n"
        "- model operations performed: 0\n\n"
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

    # The complete-byte envelope is what a host can independently rebuild.
    envelope = TRANSPORT.encode(attempt_id, artifacts)
    target = stream if stream is not None else sys.stdout
    for line in envelope:
        print(line, file=target)
    print("P0_R2_REPLAY_ATTEMPT_ID=%s" % attempt_id, file=target)
    print("P0_R2_REPLAY_OUTCOME=%s" % result["outcome"], file=target)
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0", file=target)

    if not passed:
        raise GateRefused(
            "the replay gate stopped: %s. Publish the stop and perform no "
            "model operation; never rerun the gate." % stop_reason)
    return {"result": result, "receipt": receipt,
            "counters": counters_document, "artifacts": list(artifacts)}


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_replay_gate_v1.py",
        "stage": STAGE,
        "delegated_scientific_modules": list(DELEGATED_SCIENTIFIC_MODULES),
        "copies_or_edits_science": False,
        "verifies_science_by_sha256_before_import": True,
        "one_shot": True,
        "reruns_in_place": False,
        "artifact_allow_list": list(TRANSPORT.REPLAY_ARTIFACTS),
        "attempt_prefix": TRANSPORT.ATTEMPT_ID_PREFIX,
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
            or os.environ.get("P0_R2_GATE_AUTHORIZATION"),
            attempt_id=args.attempt, image_digest=args.image_digest,
            ready_anchor=args.ready_anchor, lock_bytes=lock_bytes,
            root=args.root)
    except (GateRefused, OSError) as exc:
        print("P0_R2_REPLAY_GATE_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
