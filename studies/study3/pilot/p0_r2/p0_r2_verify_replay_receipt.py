#!/usr/bin/env python3
"""Validate a P0-R2 replay receipt against reconstructed bytes.

A replay receipt only means something when the bytes it describes were rebuilt
from the captured log by ``p0_r2_replay_capture_v1.py``. This validator refuses
a receipt that is internally consistent but unsupported: matching prose is not
evidence, and a receipt is never repaired in place to make it validate.

Model-free. No tokenizer, checkpoint, model, GPU, scoring or evidence activity.
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

import p0_r2_transport as TRANSPORT  # noqa: E402
import p0_r2_replay_capture_v1 as CAPTURE  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-replay-receipt-validation-v1"
STAGE = "STUDY3-P0-R2"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReplayReceiptDefect(Exception):
    """The replay receipt is not supported by reconstructed evidence."""


def _load(path, label):
    try:
        raw = Path(path).read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ReplayReceiptDefect("%s is unreadable: %s" % (label, exc))
    if not isinstance(document, dict):
        raise ReplayReceiptDefect("%s is not a JSON object" % label)
    return document, raw


def validate(*, replay_receipt, reconstruction_receipt, expected_attempt=None,
             expected_image_digest=None, expected_executable_commit=None
             ) -> dict:
    """Require the reconstruction to carry the receipt, not the reverse."""
    receipt, receipt_raw = _load(replay_receipt, "replay receipt")
    rebuilt, rebuilt_raw = _load(reconstruction_receipt,
                                 "reconstruction receipt")

    if rebuilt.get("schema_version") != CAPTURE.SCHEMA_VERSION:
        raise ReplayReceiptDefect(
            "the reconstruction receipt schema %r is not %r"
            % (rebuilt.get("schema_version"), CAPTURE.SCHEMA_VERSION))
    if rebuilt.get("outcome") != "PASS":
        raise ReplayReceiptDefect("the reconstruction receipt is not a pass")
    if rebuilt.get("reconstructed_from_log_alone") is not True:
        raise ReplayReceiptDefect(
            "the reconstruction was not made from the captured log alone")
    if rebuilt.get("emitted_receipt_trusted") is not False:
        raise ReplayReceiptDefect(
            "the reconstruction claims to have trusted the emitted receipt")

    artifacts = {entry.get("name"): entry
                 for entry in rebuilt.get("artifacts") or []
                 if isinstance(entry, dict)}
    if sorted(artifacts) != sorted(TRANSPORT.REPLAY_ARTIFACTS):
        raise ReplayReceiptDefect(
            "the reconstruction covers %r, not the fixed allow-list %r"
            % (sorted(artifacts), sorted(TRANSPORT.REPLAY_ARTIFACTS)))

    # The published replay receipt must be byte-identical to the artifact the
    # reconstruction rebuilt under that exact canonical name.
    rebuilt_entry = artifacts[CAPTURE.REPLAY_RECEIPT_NAME]
    actual_sha = hashlib.sha256(receipt_raw).hexdigest()
    if not _SHA256.fullmatch(str(rebuilt_entry.get("sha256") or "")):
        raise ReplayReceiptDefect(
            "the reconstruction does not carry a usable receipt hash")
    if rebuilt_entry.get("sha256") != actual_sha \
            or rebuilt_entry.get("bytes") != len(receipt_raw):
        raise ReplayReceiptDefect(
            "the published replay receipt (%d bytes, sha256 %s) is not the "
            "artifact reconstructed from the log (%s bytes, sha256 %s); a "
            "receipt is never repaired to make it validate"
            % (len(receipt_raw), actual_sha, rebuilt_entry.get("bytes"),
               rebuilt_entry.get("sha256")))

    counters = rebuilt.get("counters") or {}
    nonzero = sorted(name for name in CAPTURE.ZERO_COUNTERS
                     if int(counters.get(name, 0) or 0) != 0)
    if nonzero:
        raise ReplayReceiptDefect(
            "the reconstruction reports non-zero counters: %s"
            % ", ".join(nonzero))
    if rebuilt.get("model_operations_performed") != 0:
        raise ReplayReceiptDefect(
            "the reconstruction reports a model operation")

    for label, expected, actual in (
            ("attempt", expected_attempt, rebuilt.get("attempt_id")),
            ("image digest", expected_image_digest,
             rebuilt.get("image_digest")),
            ("executable commit", expected_executable_commit,
             rebuilt.get("executable_commit"))):
        if expected and expected != actual:
            raise ReplayReceiptDefect(
                "the reconstruction binds %s %r, not the required %r"
                % (label, actual, expected))

    digest = rebuilt.get("image_digest")
    if not _DIGEST.fullmatch(str(digest or "")):
        raise ReplayReceiptDefect("the reconstruction image digest is invalid")

    try:
        TRANSPORT.validate_attempt_id(rebuilt.get("attempt_id"))
    except TRANSPORT.TransportDefect as exc:
        raise ReplayReceiptDefect("the attempt id is invalid: %s" % exc)

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "outcome": "PASS",
        "attempt_id": rebuilt.get("attempt_id"),
        "acr_run_id": rebuilt.get("acr_run_id"),
        "image_digest": digest,
        "executable_commit": rebuilt.get("executable_commit"),
        "replay_receipt": {
            "bytes": len(receipt_raw),
            "sha256": actual_sha,
            "matches_reconstructed_artifact": True,
        },
        "reconstruction_receipt": {
            "bytes": len(rebuilt_raw),
            "sha256": hashlib.sha256(rebuilt_raw).hexdigest(),
        },
        "replay_outcome_claimed": receipt.get("outcome"),
        "artifact_count": len(artifacts),
        "counters": {name: 0 for name in CAPTURE.ZERO_COUNTERS},
        "model_operations_performed": 0,
        "authorizes_model_pilot": False,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_verify_replay_receipt.py",
        "stage": STAGE,
        "accepts_receipt_without_reconstruction": False,
        "repairs_receipts_in_place": False,
        "artifact_allow_list": list(TRANSPORT.REPLAY_ARTIFACTS),
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument("--replay-receipt")
    parser.add_argument("--reconstruction-receipt")
    parser.add_argument("--attempt")
    parser.add_argument("--image-digest")
    parser.add_argument("--executable-commit")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    if not args.replay_receipt or not args.reconstruction_receipt:
        parser.error("--validate requires --replay-receipt and "
                     "--reconstruction-receipt")
    try:
        result = validate(
            replay_receipt=args.replay_receipt,
            reconstruction_receipt=args.reconstruction_receipt,
            expected_attempt=args.attempt,
            expected_image_digest=args.image_digest,
            expected_executable_commit=args.executable_commit)
    except ReplayReceiptDefect as exc:
        print("P0_R2_REPLAY_RECEIPT_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    print("P0_R2_REPLAY_RECEIPT_VALIDATED=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
