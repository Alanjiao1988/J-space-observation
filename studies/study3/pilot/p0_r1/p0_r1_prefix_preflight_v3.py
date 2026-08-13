#!/usr/bin/env python3
"""Prove the attempt prefix unused before a one-shot GPU job is created.

Generation 2 derived the private prefix and printed it, then created and
started the GPU job. ``assert_prefix_unused`` was reached much later, during
bulk persistence -- that is, after tokenizers, checkpoints, weights and forward
passes had already happened. For a unique, no-overwrite, one-shot attempt that
ordering is useless: by the time the collision is detected the irreversible
work is done and the envelope is spent.

There is a second, physical problem. The results account is private: public
network access is disabled, shared keys are disabled, and it is reachable only
through a private endpoint inside the virtual network. An operator workstation
therefore *cannot* answer the question "is this prefix empty?" -- it cannot
even authenticate as the resource's managed identity. Generation 2's answer
was to run the check from the workstation anyway, where it could only ever
fail or be skipped.

This module is the check itself, and it is designed to run **inside** the
network as a small CPU-only Container Apps job so the answer is real. It
distinguishes proved-absent from proved-present from error, and only
proved-absent may continue.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_blob_transport as BLOB  # noqa: E402
import p0_r1_blob_transport_v3 as BLOB_V3  # noqa: E402
import p0_r1_journal_v3 as JOURNAL  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-prefix-preflight-v3"

PROVED_ABSENT = "PROVED_ABSENT"
PROVED_PRESENT = "PROVED_PRESENT"
ERROR = "ERROR"

# Names the pilot will write. Every one must be absent before the GPU starts,
# not merely the prefix as a whole, because a partial prior attempt could have
# left exactly one of them.
RESERVED_FINAL_NAMES = (
    "p0_r1_pilot_result.json",
    "p0_r1_pilot_receipt.json",
    "p0_r1_pilot_disposition.md",
    "p0_r1_pilot_counters.json",
    "p0_r1_infrastructure_receipt.json",
    BLOB.MANIFEST_NAME,
    JOURNAL.MANIFEST_NAME,
)


class PrefixPreflightDefect(Exception):
    """The prefix could not be proved unused, so no GPU job may start."""


def probe(attempt_id, backend=None, reserved=None):
    """Return a three-outcome report for the attempt prefix.

    An exception from the data plane becomes ``ERROR`` with the exact message
    preserved. It never becomes ``PROVED_ABSENT``.
    """
    reserved = tuple(reserved or RESERVED_FINAL_NAMES)
    prefix = BLOB_V3.attempt_prefix(attempt_id)
    report = {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": attempt_id,
        "prefix": prefix,
        "reserved_names": list(reserved),
        "checked_from": "inside the registered private endpoint",
    }
    try:
        transport = BLOB_V3.PrivateBlobTransportV3(attempt_id, backend=backend)
        existing = sorted(transport.backend.list_names(prefix))
    except Exception as exc:  # noqa: BLE001 - any failure is an error outcome
        report.update({
            "outcome": ERROR,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "meaning": "the private data plane did not answer; an error is "
                       "not evidence that the prefix is empty",
        })
        return report

    collisions = []
    for name in reserved:
        full = "%s%s" % (prefix, name)
        try:
            if transport.backend.exists(full):
                collisions.append(name)
        except Exception as exc:  # noqa: BLE001
            report.update({
                "outcome": ERROR,
                "error": "%s: %s" % (type(exc).__name__, exc),
                "failed_on": name,
            })
            return report

    report["objects_under_prefix"] = len(existing)
    report["existing_names"] = existing[:32]
    report["reserved_collisions"] = collisions
    if existing or collisions:
        report.update({
            "outcome": PROVED_PRESENT,
            "meaning": "the attempt prefix is already in use; a one-shot "
                       "attempt never overwrites, resumes or reuses a prefix",
        })
    else:
        report.update({
            "outcome": PROVED_ABSENT,
            "meaning": "the attempt prefix and every reserved object name are "
                       "absent; the bounded pilot may be created",
        })
    return report


def require_unused(report):
    """Continue only on a proved absence."""
    outcome = (report or {}).get("outcome")
    if outcome == PROVED_ABSENT:
        return report
    if outcome == PROVED_PRESENT:
        raise PrefixPreflightDefect(
            "the attempt prefix %s is already in use (%d object(s), %d "
            "reserved collision(s)); refusing to create the GPU job"
            % (report.get("prefix"), report.get("objects_under_prefix", 0),
               len(report.get("reserved_collisions") or ())))
    raise PrefixPreflightDefect(
        "the attempt prefix %s could not be proved unused: %s"
        % (report.get("prefix"), report.get("error", "unknown error")))


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_prefix_preflight_v3.py",
        "runs_before_gpu_create_or_start": True,
        "outcomes": [PROVED_ABSENT, PROVED_PRESENT, ERROR],
        "reserved_final_names": list(RESERVED_FINAL_NAMES),
        "error_is_not_absence": True,
        "closes": "G2-06",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--attempt")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="probe an in-memory backend, for build gates")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.probe:
        if not args.attempt:
            print("FAIL: --probe requires --attempt", file=sys.stderr)
            return 2
        backend = BLOB.InMemoryBackend() if args.dry_run else None
        report = probe(args.attempt, backend=backend)
        print(json.dumps(report, indent=2, sort_keys=True))
        try:
            require_unused(report)
        except PrefixPreflightDefect as exc:
            print("P0_R1_PREFIX_PREFLIGHT_REFUSED=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        print("P0_R1_PREFIX_PREFLIGHT_PROVED_ABSENT=1 PREFIX=%s"
              % report["prefix"])
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
