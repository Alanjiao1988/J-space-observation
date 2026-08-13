#!/usr/bin/env python3
"""Recover v2 envelopes after checksum-verifiable ACR log interleaving."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import p0_r1_transport as BASE  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-acr-log-recovery-v3"
_BASE64 = frozenset(string.ascii_letters + string.digits + "+/=")


def _valid_chunk(payload, declared_size, declared_sha):
    try:
        raw = base64.b64decode(payload.encode("ascii"), validate=True)
    except Exception:  # noqa: BLE001
        return False
    return len(raw) == declared_size \
        and hashlib.sha256(raw).hexdigest() == declared_sha


def repair_acr_fragments(log_text):
    """Repair only fragments whose reconstructed raw chunk matches its SHA."""
    lines = log_text.splitlines()
    consumed = set()
    repairs = []
    for index, original in enumerate(lines):
        marker = original.find(BASE.CHUNK_MARKER + "|")
        if marker < 0:
            continue
        line = original[marker:]
        if "|d=" not in line:
            continue
        prefix, data = line.split("|d=", 1)
        fields = {}
        try:
            for part in prefix.split("|")[1:]:
                key, value = part.split("=", 1)
                fields[key] = value
            byte_count = int(fields["b"])
            chunk_index = int(fields["i"])
            declared_sha = fields["s"]
        except (KeyError, ValueError):
            continue
        raw_size = min(
            BASE.RAW_CHUNK_BYTES,
            max(0, byte_count - chunk_index * BASE.RAW_CHUNK_BYTES))
        encoded_size = 4 * ((raw_size + 2) // 3)
        if len(data) == encoded_size \
                and _valid_chunk(data, raw_size, declared_sha):
            continue

        for fragment_index in range(index + 1, min(len(lines), index + 8)):
            fragment = lines[fragment_index].strip()
            if not fragment or any(character not in _BASE64
                                   for character in fragment):
                continue
            keep = encoded_size - len(fragment)
            if keep < 0 or len(data) < keep:
                continue
            reconstructed = data[:keep] + fragment
            if not _valid_chunk(reconstructed, raw_size, declared_sha):
                continue
            lines[index] = original[:marker] + prefix + "|d=" + reconstructed
            consumed.add(fragment_index)
            repairs.append({
                "chunk_index": chunk_index,
                "fragment_line": fragment_index + 1,
                "source_line": index + 1,
            })
            break
    repaired = "\n".join(
        line for index, line in enumerate(lines) if index not in consumed)
    return repaired, repairs


def recover_with_report(log_text, attempt_id=None, allowed=None):
    """Use the base decoder first; repair only a checksum-proved split."""
    try:
        return BASE.recover(
            log_text, attempt_id=attempt_id, allowed=allowed), []
    except BASE.TransportDefect as original:
        repaired, repairs = repair_acr_fragments(log_text)
        if not repairs:
            raise original
        recovered = BASE.recover(
            repaired, attempt_id=attempt_id, allowed=allowed)
        return recovered, repairs


def recover(log_text, attempt_id=None, allowed=None):
    return recover_with_report(
        log_text, attempt_id=attempt_id, allowed=allowed)[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--log")
    parser.add_argument("--attempt")
    parser.add_argument("--out-dir")
    parser.add_argument("--receipt")
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    if args.identity:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "module": "p0_r1_transport_v3.py",
            "base_envelope": BASE.ENVELOPE_VERSION,
            "repair_requires_chunk_sha256": True,
            "repair_requires_exact_decoded_length": True,
        }, indent=2, sort_keys=True))
        return 0
    if not args.recover or not args.log or not args.out_dir:
        parser.print_help()
        return 2
    try:
        raw = open(args.log, "rb").read()
        recovered, repairs = recover_with_report(
            raw.decode("utf-8", "replace"), attempt_id=args.attempt)
        written = BASE.write_recovered(recovered, args.out_dir)
        receipt = BASE.reconstruction_receipt(
            args.attempt, recovered,
            log_identity={
                "path": args.log, "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            run_id=args.run_id)
        receipt["acr_fragment_repairs"] = repairs
        receipt["acr_fragment_repair_count"] = len(repairs)
        if args.receipt:
            with open(args.receipt, "wb") as handle:
                handle.write((json.dumps(receipt, indent=2, sort_keys=True)
                              + "\n").encode("utf-8"))
    except (OSError, BASE.TransportDefect) as exc:
        print("P0_R1_TRANSPORT_V3_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    for entry in written:
        print("RECOVERED=%s BYTES=%d SHA256=%s"
              % (entry["name"], entry["bytes"], entry["sha256"]))
    print("P0_R1_TRANSPORT_V3_RECOVERY_COMPLETE=1 REPAIRS=%d" % len(repairs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
