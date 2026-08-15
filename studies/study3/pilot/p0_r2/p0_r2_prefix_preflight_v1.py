#!/usr/bin/env python3
"""Prove a P0-R2 attempt prefix is entirely unused, from inside the VNet.

This runs before any bounded pilot creates anything. It answers exactly one
question: does ``study3/p0_r2/g1/<attempt>/`` already carry an object?

Two answers are acceptable: ``PROVED_UNUSED`` (the listing succeeded and was
empty) and a refusal. A listing that fails is not an absence, and a listing
that returns objects means a previous attempt already owns that prefix, so the
attempt id must be minted again rather than reused.

Model-free. Constructs no tokenizer, downloads no checkpoint, loads no weight,
allocates no GPU, and writes nothing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_blob_transport as BLOB  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-prefix-preflight-v1"
STAGE = "STUDY3-P0-R2"


class PrefixPreflightDefect(Exception):
    """The prefix could not be proved unused."""


def probe(attempt_id: str, *, backend=None) -> dict:
    try:
        prefix = BLOB.attempt_prefix(attempt_id)
    except BLOB.BlobTransportDefect as exc:
        raise PrefixPreflightDefect("the attempt id is invalid: %s" % exc)

    sink = backend if backend is not None else BLOB.AzureManagedIdentityBackend()
    if getattr(sink, "credential_kind", None) != "managed-identity":
        raise PrefixPreflightDefect(
            "the prefix preflight accepts a managed-identity backend only")
    try:
        names = sorted(sink.list_names(prefix))
    except Exception as exc:  # noqa: BLE001 - any failure is an ambiguity
        raise PrefixPreflightDefect(
            "the private listing failed (%s); a query error is never an "
            "absence" % exc)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "attempt_id": attempt_id,
        "prefix": prefix,
        "outcome": "PROVED_UNUSED" if not names else "PROVED_IN_USE",
        "object_count": len(names),
        "objects": names[:16],
        "collisions": len(names),
        "wrote_any_object": False,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_allocations": 0,
        "model_operations_performed": 0,
    }


def require_unused(report: dict) -> dict:
    if not isinstance(report, dict) or report.get("outcome") != "PROVED_UNUSED":
        raise PrefixPreflightDefect(
            "the attempt prefix is not proved unused: %r"
            % (report or {}).get("outcome"))
    if report.get("object_count") != 0:
        raise PrefixPreflightDefect(
            "the attempt prefix already carries %s object(s)"
            % report.get("object_count"))
    return report


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_prefix_preflight_v1.py",
        "stage": STAGE,
        "prefix_root": BLOB.PREFIX_ROOT,
        "query_error_is_absence": False,
        "writes_objects": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--probe")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    try:
        report = require_unused(probe(args.probe))
    except PrefixPreflightDefect as exc:
        print("P0_R2_PREFIX_PREFLIGHT_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    print("P0_R2_PREFIX_PREFLIGHT_PROVED_ABSENT=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
