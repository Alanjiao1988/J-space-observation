#!/usr/bin/env python3
"""Capture a P0-R2 replay run and rebuild its bytes independently.

The emitted receipt inside a run is a *claim*. This module never promotes a
claim to a fact. It takes only the raw log that the host captured from its
first byte, rebuilds the four canonical artifacts from the ``P0R2TX*`` envelope
alone, and then compares the rebuilt bytes with what the run said it produced.
If the run's own receipt disagrees with the bytes reconstructed from the log,
the reconstruction wins and the capture stops.

Nothing here consumes the replay envelope; the envelope is spent by whoever
invoked the run. This module is model-free and touches no model, tokenizer,
checkpoint, GPU, score, or evidence row.
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
import p0_r2_transport_v1 as ACRLOG  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-replay-capture-v1"
RECEIPT_NAME = "p0_r2_replay_reconstruction_receipt_v1.json"
STAGE = "STUDY3-P0-R2"

RESULT_NAME = "p0_r2_replay_result.json"
REPLAY_RECEIPT_NAME = "p0_r2_replay_receipt.json"
COUNTERS_NAME = "p0_r2_replay_counters.json"
DISPOSITION_NAME = "P0_R2_REPLAY_DISPOSITION.md"

_RUN_ID = re.compile(r"^[a-z0-9]{1,64}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA40 = re.compile(r"^[0-9a-f]{40}$")

#: Every counter that must still be zero after a replay-only run.
ZERO_COUNTERS = (
    "tokenizer_constructions",
    "tokenizer_encodes",
    "checkpoint_downloads",
    "checkpoint_loads",
    "model_weight_loads",
    "prefills",
    "generations",
    "scored_rows",
    "evidence_rows_added",
    "gpu_allocations",
)


class CaptureDefect(Exception):
    """The replay could not be independently rebuilt from its own log."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(payload: bytes, name: str) -> dict:
    return {"name": name, "bytes": len(payload), "sha256": _sha256(payload)}


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise CaptureDefect(
            "%s already exists; a capture is never rewritten in place" % path
        ) from exc


def reconstruct(raw_log: bytes, *, attempt: str, run_id: str, exit_code: int,
                executable_commit: str, image_digest: str,
                stderr: bytes = b"", out_dir: Path | None = None) -> dict:
    """Rebuild the four artifacts from the log alone and receipt the result."""
    if not isinstance(raw_log, (bytes, bytearray)):
        raise CaptureDefect("the raw log must be captured as exact bytes")
    raw_log = bytes(raw_log)
    if not raw_log:
        raise CaptureDefect(
            "the captured raw log is empty; there is nothing to reconstruct "
            "and no reconstruction may be claimed")
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise CaptureDefect("the ACR run id %r is not a single token" % run_id)
    if not _DIGEST.fullmatch(image_digest or ""):
        raise CaptureDefect("the image digest must be sha256:<64 hex>")
    if not _SHA40.fullmatch(executable_commit or ""):
        raise CaptureDefect("the executable commit must be a 40-hex Git id")
    try:
        TRANSPORT.validate_attempt_id(attempt)
    except TRANSPORT.TransportDefect as exc:
        raise CaptureDefect("the replay attempt id is invalid: %s" % exc)
    if int(exit_code) != 0:
        raise CaptureDefect(
            "the replay exited %d; publish the stop and reconstruct nothing "
            "as a pass" % int(exit_code))

    text = raw_log.decode("utf-8", "replace")
    # ACR interleaves its own prefixes into streamed output. The strict decoder
    # is tried first; only a checksum-proved split is ever repaired, and the
    # repair is reported rather than silently applied.
    try:
        recovered, repair_report = ACRLOG.recover_with_report(
            text, attempt_id=attempt)
    except TRANSPORT.TransportDefect as exc:
        raise CaptureDefect(
            "the four canonical artifacts could not be rebuilt from the "
            "captured log: %s" % exc) from exc

    names = sorted(recovered)
    if tuple(names) != tuple(sorted(TRANSPORT.REPLAY_ARTIFACTS)):
        raise CaptureDefect(
            "the log yielded %r, not the fixed four-artifact allow-list %r"
            % (names, sorted(TRANSPORT.REPLAY_ARTIFACTS)))

    written = []
    if out_dir is not None:
        out_dir = Path(out_dir)
        written = TRANSPORT.write_recovered(recovered, out_dir)

    # The run's own receipt is now checked against the rebuilt bytes.
    claimed = recovered[REPLAY_RECEIPT_NAME]
    try:
        claimed_document = json.loads(claimed.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise CaptureDefect(
            "the reconstructed replay receipt is not readable JSON: %s" % exc)
    counters_document = {}
    try:
        counters_document = json.loads(
            recovered[COUNTERS_NAME].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise CaptureDefect(
            "the reconstructed counters are not readable JSON: %s" % exc)

    nonzero = sorted(
        name for name in ZERO_COUNTERS
        if int((counters_document or {}).get(name, 0) or 0) != 0)
    if nonzero:
        raise CaptureDefect(
            "the replay reported non-zero model counters %s; a replay gate "
            "performs no model operation" % ", ".join(nonzero))

    for field, expected in (("attempt_id", attempt),
                            ("image_digest", image_digest),
                            ("executable_commit", executable_commit)):
        actual = claimed_document.get(field)
        if actual is not None and actual != expected:
            raise CaptureDefect(
                "the emitted replay receipt binds %s %r, but the capture was "
                "made for %r" % (field, actual, expected))

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "outcome": "PASS",
        "attempt_id": attempt,
        "acr_run_id": run_id,
        "exit_code": int(exit_code),
        "executable_commit": executable_commit,
        "image_digest": image_digest,
        "raw_log": _identity(raw_log, "p0_r2_replay_raw_log.txt"),
        "stderr": _identity(bytes(stderr or b""), "p0_r2_replay_stderr.txt"),
        "acr_fragment_repair": repair_report,
        "reconstructed_from_log_alone": True,
        "emitted_receipt_trusted": False,
        "artifacts": [
            dict(_identity(recovered[name], name),
                 written=str(out_dir / name) if out_dir is not None else None)
            for name in sorted(TRANSPORT.REPLAY_ARTIFACTS)
        ],
        "artifact_count": len(recovered),
        "artifact_allow_list": list(TRANSPORT.REPLAY_ARTIFACTS),
        "written_paths": [str(path) for path in written],
        "counters": {name: 0 for name in ZERO_COUNTERS},
        "model_operations_performed": 0,
        "authorizes_model_pilot": False,
    }
    return receipt


def capture(*, raw_log_path: Path, out_dir: Path, attempt: str, run_id: str,
            exit_code: int, executable_commit: str, image_digest: str,
            stderr_path: Path | None = None) -> dict:
    raw_log_path = Path(raw_log_path)
    try:
        raw_log = raw_log_path.read_bytes()
    except OSError as exc:
        raise CaptureDefect("the raw log is unreadable: %s" % exc)
    stderr = b""
    if stderr_path is not None and Path(stderr_path).exists():
        stderr = Path(stderr_path).read_bytes()
    receipt = reconstruct(
        raw_log, attempt=attempt, run_id=run_id, exit_code=int(exit_code),
        executable_commit=executable_commit, image_digest=image_digest,
        stderr=stderr, out_dir=Path(out_dir))
    payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")
    _write_exclusive(Path(out_dir) / RECEIPT_NAME, payload)
    return receipt


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_replay_capture_v1.py",
        "stage": STAGE,
        "artifact_allow_list": list(TRANSPORT.REPLAY_ARTIFACTS),
        "reconstructs_from_log_alone": True,
        "trusts_emitted_receipt": False,
        "rewrites_receipts_in_place": False,
        "consumes_replay_envelope": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--reconstruct", action="store_true")
    parser.add_argument("--raw-log")
    parser.add_argument("--out-dir")
    parser.add_argument("--attempt")
    parser.add_argument("--run-id")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--executable-commit")
    parser.add_argument("--image-digest")
    parser.add_argument("--stderr-file")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    missing = [name for name in
               ("raw_log", "out_dir", "attempt", "run_id",
                "executable_commit", "image_digest")
               if not getattr(args, name)]
    if missing:
        parser.error("--%s required" % ", --".join(
            name.replace("_", "-") for name in missing))
    try:
        receipt = capture(
            raw_log_path=args.raw_log, out_dir=args.out_dir,
            attempt=args.attempt, run_id=args.run_id,
            exit_code=args.exit_code,
            executable_commit=args.executable_commit,
            image_digest=args.image_digest, stderr_path=args.stderr_file)
    except (CaptureDefect, OSError) as exc:
        print("P0_R2_REPLAY_CAPTURE_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print("P0_R2_REPLAY_RECONSTRUCTED=1")
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
