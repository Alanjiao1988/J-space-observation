#!/usr/bin/env python3
"""Build the generation-3 model-pilot authorization from exact injected bytes.

Generation 2 had a production runner CLI that read the lock and the receipt and
then called ``run(...)`` without passing an ``authorization`` argument at all,
so the very first production check refused every real invocation with::

    the P0-R1 model pilot requires an execution authorization mapping carrying
    the execution lock and the replay-pass receipt

That refusal was never observed before publication because the unit tests
called the internal ``run()`` with a hand-built authorization mapping that
production code never constructs. The tests exercised a function; the GPU job
would have exercised the CLI. Nothing connected them.

This module is that missing connection, and it is deliberately the *only* way
to build an authorization. Both the launcher on the workstation and the model
shell inside the container call ``build()`` with the same four exact byte
inputs, so there is one contract and one failure mode instead of two paths that
drift apart:

1. the active generation-3 execution lock;
2. the exact replay receipt the gate emitted, unmodified;
3. the independent reconstruction receipt built from the captured raw log; and
4. the published-head proof.

Any test that wants an authorization must produce these four documents, which
means a test cannot accidentally prove a seam that production does not have.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_ready_anchor_v3 as ANCHOR  # noqa: E402
import p0_r1_replay_capture_v3 as CAPTURE  # noqa: E402
import p0_r1_execution_lock_v3 as LOCK_V3  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-model-authorization-v3"
INJECTION_VERSION = "study3-p0-r1-runtime-injection-v3"
MAX_INJECTION_BYTES = 262144
INJECTION_TARGETS = {
    "lock": ("P0_R1_LOCK_V3_B64", "p0_r1_execution_lock_v3.json"),
    "replay_receipt": (
        "P0_R1_REPLAY_RECEIPT_V3_B64", "p0_r1_replay_receipt.json"),
    "reconstruction_receipt": (
        "P0_R1_RECONSTRUCTION_RECEIPT_V3_B64",
        "p0_r1_replay_reconstruction_receipt_v3.json"),
    "head_proof": (
        "P0_R1_HEAD_PROOF_V3_B64", "p0_r1_head_proof_v3.json"),
}


class AuthorizationRefused(Exception):
    """The four inputs do not agree, so no model operation is authorized."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def encode_injection(payload):
    """Encode exact bytes with an independently checked length and digest."""
    if not isinstance(payload, bytes) or not payload:
        raise AuthorizationRefused(
            "an injected authorization input must be non-empty raw bytes")
    if len(payload) > MAX_INJECTION_BYTES:
        raise AuthorizationRefused(
            "an injected input of %d bytes exceeds the %d-byte ceiling"
            % (len(payload), MAX_INJECTION_BYTES))
    return "%s|%d|%s|%s" % (
        INJECTION_VERSION, len(payload), _sha256(payload),
        base64.b64encode(payload).decode("ascii"))


def decode_injection(encoded):
    """Decode one exact-byte envelope, refusing truncation or substitution."""
    parts = encoded.split("|") if isinstance(encoded, str) else []
    if len(parts) != 4 or parts[0] != INJECTION_VERSION \
            or not parts[1].isdigit():
        raise AuthorizationRefused("an injected authorization input is malformed")
    try:
        payload = base64.b64decode(parts[3].encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        raise AuthorizationRefused(
            "an injected authorization input is not lossless base64")
    if len(payload) != int(parts[1]) or _sha256(payload) != parts[2]:
        raise AuthorizationRefused(
            "an injected authorization input fails its byte identity")
    return payload


def reconstruct_injections(out_dir, required=None, environ=None):
    """Rebuild required inputs in the writable runtime namespace."""
    environ = os.environ if environ is None else environ
    required = tuple(required or sorted(INJECTION_TARGETS))
    unknown = [name for name in required if name not in INJECTION_TARGETS]
    if unknown:
        raise AuthorizationRefused(
            "unknown injection target(s): %s" % ", ".join(sorted(unknown)))
    os.makedirs(out_dir, exist_ok=True)
    written = {}
    for target in required:
        env_name, file_name = INJECTION_TARGETS[target]
        encoded = environ.get(env_name)
        if not encoded:
            raise AuthorizationRefused(
                "%s was not injected; no authorization input has a default"
                % env_name)
        payload = decode_injection(encoded)
        path = os.path.join(out_dir, file_name)
        with open(path, "wb") as handle:
            handle.write(payload)
        with open(path, "rb") as handle:
            if handle.read() != payload:
                raise AuthorizationRefused(
                    "%s did not read back byte-exactly" % file_name)
        written[target] = {
            "path": path, "bytes": len(payload), "sha256": _sha256(payload)}
    return written


def _document(raw, label):
    if isinstance(raw, dict):
        payload = (json.dumps(raw, sort_keys=True)).encode("utf-8")
        return raw, payload
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, (bytes, bytearray)):
        raise AuthorizationRefused(
            "%s must be supplied as exact bytes or a document" % label)
    try:
        return json.loads(bytes(raw).decode("utf-8")), bytes(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise AuthorizationRefused("%s is not readable JSON: %s"
                                   % (label, exc))


def build(lock_bytes, replay_receipt_bytes, reconstruction_receipt_bytes,
          head_proof_bytes, attempt_id=None, image_digest=None, run_id=None,
          root=None):
    """Return an authorization mapping, or refuse with the exact disagreement.

    Every cross-check is between two independently produced documents. No
    field is taken on the word of a single one of them.
    """
    lock, lock_raw = _document(lock_bytes, "the execution lock")
    receipt, receipt_raw = _document(replay_receipt_bytes,
                                     "the emitted replay receipt")
    reconstruction, reconstruction_raw = _document(
        reconstruction_receipt_bytes, "the reconstruction receipt")
    proof, proof_raw = _document(head_proof_bytes, "the published-head proof")

    generation = lock.get("generation")
    if generation != 3:
        raise AuthorizationRefused(
            "the model pilot requires the generation-3 execution lock; this "
            "lock declares generation %r" % (generation,))
    try:
        LOCK_V3.validate(lock, root=root)
    except (LOCK_V3.LockDefect, KeyError, TypeError) as exc:
        raise AuthorizationRefused(
            "the generation-3 execution lock is invalid: %s" % exc)

    legal = lock.get("legal_status") or {}
    if not legal.get("p0_r1_pilot_execution_authorized"):
        raise AuthorizationRefused(
            "the execution lock does not carry the narrow "
            "p0_r1_pilot_execution_authorized flag")
    if legal.get("p0_r1_pilot_execution_consumed"):
        raise AuthorizationRefused(
            "the execution lock is already consumed; the P0-R1 envelope is "
            "one-shot and is never re-armed")

    try:
        pair = CAPTURE.validate_authorization_pair(
            receipt, reconstruction, attempt_id=attempt_id, run_id=run_id)
    except CAPTURE.ReplayCaptureDefect as exc:
        raise AuthorizationRefused(str(exc))

    executable = lock.get("executable_code") or {}
    relationship = lock.get("ready_commit_relationship") or {}
    try:
        ANCHOR.validate_proof(
            proof, executable_commit=executable.get("commit"),
            executable_tree=executable.get("tree"),
            ready_anchor_parent=relationship.get("ready_anchor_parent"),
            lock_sha256=_sha256(lock_raw))
    except ANCHOR.ReadyAnchorDefect as exc:
        raise AuthorizationRefused(str(exc))

    locked_digest = (lock.get("image") or {}).get("digest")
    image_digest = image_digest or locked_digest
    if not locked_digest or image_digest != locked_digest:
        raise AuthorizationRefused(
            "the requested image %r is not the locked image %r"
            % (image_digest, locked_digest))

    gate = reconstruction.get("gate") or {}
    for field, locked_value, label in (
            ("image_digest", locked_digest, "image digest"),
            ("executable_code_commit", executable.get("commit"),
             "executable commit"),
            ("executable_code_tree", executable.get("tree"),
             "executable tree")):
        recovered = gate.get(field)
        if recovered and locked_value and recovered != locked_value:
            raise AuthorizationRefused(
                "the recovered replay binds %s %r, but the active lock binds "
                "%r" % (label, recovered, locked_value))
    ready_anchor = proof["ready_anchor"]["commit"]
    if receipt.get("ready_commit") != ready_anchor \
            or gate.get("ready_commit") != ready_anchor:
        raise AuthorizationRefused(
            "the replay receipt/reconstruction do not bind the proved ready "
            "anchor %s" % ready_anchor)

    receipt_digest = receipt.get("execution_lock") or {}
    lock_sha = receipt_digest.get("sha256") if isinstance(receipt_digest, dict) \
        else None
    if lock_sha and lock_sha != _sha256(lock_raw):
        raise AuthorizationRefused(
            "the replay ran against execution lock %s but the injected lock "
            "hashes to %s" % (lock_sha, _sha256(lock_raw)))

    for field in ("tokenizer_constructions", "tokenizer_encodes",
                  "checkpoint_downloads", "model_weight_loads",
                  "model_operations_performed"):
        value = receipt.get(field)
        if value not in (None, 0):
            raise AuthorizationRefused(
                "the replay receipt records %s = %r; a replay that performed a "
                "model operation is not a replay" % (field, value))
    if receipt.get("gpu_allocated"):
        raise AuthorizationRefused(
            "the replay receipt records a GPU allocation; the replay gate is "
            "CPU-only")

    return {
        "schema_version": SCHEMA_VERSION,
        "p0_r1_pilot_execution_authorized": True,
        "replay_gate_passed_in_this_session": True,
        "attempt_id": pair["attempt_id"],
        "run_id": pair["run_id"],
        "ready_commit": proof["ready_anchor"]["commit"],
        "published_head": proof["published_head"]["commit"],
        "published_tree": proof["published_head"]["tree"],
        "image_digest": image_digest,
        "execution_lock": lock,
        "replay_receipt": receipt,
        "reconstruction_receipt": reconstruction,
        "head_proof": proof,
        "input_identities": {
            "execution_lock": {"bytes": len(lock_raw),
                               "sha256": _sha256(lock_raw)},
            "replay_receipt": {"bytes": len(receipt_raw),
                               "sha256": _sha256(receipt_raw)},
            "reconstruction_receipt": {"bytes": len(reconstruction_raw),
                                       "sha256": _sha256(reconstruction_raw)},
            "head_proof": {"bytes": len(proof_raw),
                           "sha256": _sha256(proof_raw)},
        },
        "authorizes": "exactly one bounded GPU model pilot for this attempt",
    }


def build_from_files(lock_file, replay_receipt_file,
                     reconstruction_receipt_file, head_proof_file,
                     attempt_id=None, image_digest=None, run_id=None,
                     root=None):
    """Read four exact files and build the authorization from their bytes."""
    payloads = []
    for path, label in ((lock_file, "--lock-file"),
                        (replay_receipt_file, "--replay-receipt"),
                        (reconstruction_receipt_file,
                         "--reconstruction-receipt"),
                        (head_proof_file, "--head-proof")):
        if not path:
            raise AuthorizationRefused(
                "%s is mandatory; the generation-3 pilot has no default "
                "authorization input" % label)
        if not os.path.exists(path):
            raise AuthorizationRefused("%s %s does not exist" % (label, path))
        with open(path, "rb") as handle:
            payloads.append(handle.read())
    return build(payloads[0], payloads[1], payloads[2], payloads[3],
                 attempt_id=attempt_id, image_digest=image_digest,
                 run_id=run_id, root=root)


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_authorization_v3.py",
        "mandatory_inputs": ["execution_lock", "replay_receipt",
                             "reconstruction_receipt", "head_proof"],
        "single_construction_path": True,
        "tests_may_bypass_the_cli": False,
        "closes": "G2-02",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--encode", action="store_true")
    parser.add_argument("--reconstruct", action="store_true")
    parser.add_argument("--file")
    parser.add_argument("--require", action="append",
                        choices=sorted(INJECTION_TARGETS))
    parser.add_argument("--lock-file")
    parser.add_argument("--replay-receipt")
    parser.add_argument("--reconstruction-receipt")
    parser.add_argument("--head-proof")
    parser.add_argument("--attempt")
    parser.add_argument("--image-digest")
    parser.add_argument("--out")
    parser.add_argument("--out-dir")
    parser.add_argument("--src")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.encode:
        if not args.file:
            print("FAIL: --encode requires --file", file=sys.stderr)
            return 2
        try:
            with open(args.file, "rb") as handle:
                print(encode_injection(handle.read()))
        except (OSError, AuthorizationRefused) as exc:
            print("P0_R1_INJECTION_REFUSED=1 %s" % exc, file=sys.stderr)
            return 3
        return 0

    if args.reconstruct:
        if not args.out_dir:
            print("FAIL: --reconstruct requires --out-dir", file=sys.stderr)
            return 2
        try:
            written = reconstruct_injections(
                args.out_dir, required=args.require)
        except AuthorizationRefused as exc:
            print("P0_R1_INJECTION_REFUSED=1 %s" % exc, file=sys.stderr)
            return 3
        for name in sorted(written):
            print("P0_R1_INJECTED=%s BYTES=%d SHA256=%s"
                  % (name, written[name]["bytes"], written[name]["sha256"]))
        return 0

    if args.build:
        try:
            authorization = build_from_files(
                args.lock_file, args.replay_receipt,
                args.reconstruction_receipt, args.head_proof,
                attempt_id=args.attempt, image_digest=args.image_digest,
                root=args.src)
        except AuthorizationRefused as exc:
            print("P0_R1_MODEL_AUTHORIZATION_REFUSED=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        payload = json.dumps(authorization, indent=2, sort_keys=True) + "\n"
        if args.out:
            with open(args.out, "wb") as handle:
                handle.write(payload.encode("utf-8"))
        print("P0_R1_MODEL_AUTHORIZATION_BUILT=1 ATTEMPT=%s"
              % authorization["attempt_id"])
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
