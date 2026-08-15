#!/usr/bin/env python3
"""CPU-only recovery of a P0-R2 attempt's durable bytes.

Recovery always runs after a terminal execution status, including a hard kill,
and it must be able to tell the difference between "the attempt finished" and
"the attempt stopped mid-row". It therefore reads the durable journal rather
than the container's own summary, verifies the recursive manifest, and
classifies the attempt from what is actually in the private prefix.

Two invariants hold for every path through this module:

* it is CPU-only and asserts that no accelerator is present or requested;
* it never writes, repairs, or deletes an observation. A partial attempt stays
  partial and does not become a retry authorization.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_blob_transport as BLOB  # noqa: E402
import p0_r2_journal_v1 as JOURNAL  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-recovery-v1"
STAGE = "STUDY3-P0-R2"
RECOVERY_JOB = "job-jspace-s3-p0r2-recover-g1"

#: Environment names that would indicate an accelerator was requested.
_ACCELERATOR_MARKERS = (
    "NVIDIA_VISIBLE_DEVICES",
    "CUDA_VISIBLE_DEVICES",
    "NVIDIA_DRIVER_CAPABILITIES",
)


class RecoveryDefect(Exception):
    """Recovery could not complete honestly."""


def assert_model_free(environ=None) -> dict:
    """Refuse to run recovery on anything that looks like a GPU replica."""
    environ = os.environ if environ is None else environ
    requested = sorted(
        name for name in _ACCELERATOR_MARKERS
        if str(environ.get(name, "")).strip() not in ("", "void", "none"))
    if requested:
        raise RecoveryDefect(
            "recovery is CPU-only but the replica exposes %s; refusing to run "
            "recovery on an accelerator replica" % ", ".join(requested))
    if str(environ.get("P0_R2_REQUIRE_ACCELERATOR", "")).strip() == "1":
        raise RecoveryDefect(
            "P0_R2_REQUIRE_ACCELERATOR is set; this is not a CPU recovery")
    return {
        "cpu_only": True,
        "accelerator_env_present": [],
        "gpu_allocations": 0,
    }


def recover(attempt_id: str, *, backend=None, lock_sha256=None,
            environ=None) -> dict:
    """Read back every durable object and classify the attempt honestly."""
    cpu = assert_model_free(environ)
    try:
        prefix = BLOB.attempt_prefix(attempt_id)
    except BLOB.BlobTransportDefect as exc:
        raise RecoveryDefect("the attempt id is invalid: %s" % exc)

    sink = backend if backend is not None else BLOB.AzureManagedIdentityBackend()
    if getattr(sink, "credential_kind", None) != "managed-identity":
        raise RecoveryDefect(
            "recovery accepts a managed-identity backend only")
    try:
        names = sorted(sink.list_names(prefix))
    except Exception as exc:  # noqa: BLE001 - any failure is an ambiguity
        raise RecoveryDefect(
            "the private listing failed (%s); an error is never an absence"
            % exc)
    if not names:
        raise RecoveryDefect(
            "the attempt prefix %s is empty; there is nothing to recover and "
            "no completion may be claimed" % prefix)

    objects = []
    manifest_document = None
    for name in names:
        try:
            payload = sink.download(prefix + name)
        except Exception as exc:  # noqa: BLE001
            raise RecoveryDefect("%s could not be read back: %s" % (name, exc))
        entry = {
            "name": name,
            "bytes": len(payload),
            "sha256": BLOB._sha256(payload),
        }
        objects.append(entry)
        if name.endswith(JOURNAL.MANIFEST_NAME) \
                or name.endswith(BLOB.MANIFEST_NAME):
            try:
                manifest_document = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise RecoveryDefect(
                    "the recursive manifest is unreadable: %s" % exc)

    manifest_verified = False
    manifest_defect = None
    if manifest_document is not None:
        try:
            JOURNAL.verify_manifest(manifest_document, sink)
            manifest_verified = True
        except JOURNAL.JournalDefect as exc:
            manifest_defect = str(exc)

    # A recovered attempt is complete only when the manifest verifies and it
    # was the last object written. Anything else is partial, and partial never
    # authorizes a retry.
    complete = bool(manifest_verified) and manifest_document is not None
    classification = "COMPLETE" if complete else "PARTIAL"

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "attempt_id": attempt_id,
        "prefix": prefix,
        "recovery_job": RECOVERY_JOB,
        "classification": classification,
        "object_count": len(objects),
        "objects": objects,
        "manifest_present": manifest_document is not None,
        "manifest_verified": manifest_verified,
        "manifest_defect": manifest_defect,
        "lock_sha256": lock_sha256,
        "retry_authorized": False,
        "wrote_repaired_or_deleted_any_object": False,
        "cpu_only": cpu["cpu_only"],
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "prefills": 0,
        "generations": 0,
        "scored_rows": 0,
        "evidence_rows_added": 0,
        "gpu_allocations": 0,
        "model_operations_performed": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_recovery_v1.py",
        "stage": STAGE,
        "recovery_job": RECOVERY_JOB,
        "prefix_root": BLOB.PREFIX_ROOT,
        "cpu_only": True,
        "classifications": ["COMPLETE", "PARTIAL"],
        "partial_authorizes_retry": False,
        "repairs_observations": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--recover")
    parser.add_argument("--lock-sha256")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    try:
        report = recover(args.recover, lock_sha256=args.lock_sha256)
    except RecoveryDefect as exc:
        print("P0_R2_RECOVERY_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    print("P0_R2_RECOVERY_CLASSIFICATION=%s" % report["classification"])
    print("P0_R2_RECOVERY_COMPLETE=1")
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
