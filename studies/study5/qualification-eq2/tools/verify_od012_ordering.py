"""OD-012 guard: prove no lens read happened before the convention was committed.

OD-012 blocks "compute both conventions and keep the one with a band" by
construction rather than by intention. The structural claim it makes is:

    every journal record that references lens_A or lens_B carries a timestamp
    later than the convention-commit record.

This tool decides that claim from committed evidence. Hard blocker 5 makes an
early read a stop, so this returns FAIL rather than repairing anything.

Two failure modes are treated as FAIL, not as "nothing found":

  * the convention-commit record is absent - then there is nothing for reads to
    be later than, and the ordering claim is unsupported;
  * a lens-referencing record has no timestamp - an unordered record cannot be
    shown to be later than anything.

OD-011: the failing cases are demonstrated in tests/test_eq2_od012_guard.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LENS_PATTERN = re.compile(r"lens_[AB]\b")
CONVENTION_STEP_ID = "R1-CONVENTION-COMMIT"

#: EQ1's sealed lens digests, committed in EQ1's merge report and immutable.
#: Matching on the digest is stronger than matching on a filename, because a
#: file can be renamed but the content address cannot be.
SEALED_LENS_SHA256 = {
    "lens_A": "2910b7bf80784a48f4e0d41f1a6fd002781f1d3f4f6bc3df83fb547848164083",
    "lens_B": "e6d7eec9cb33035edb4b702bc3fae807a48d42c29270f40b9c461e6116ee528a",
}

#: Fields in which an actual file access is recorded. A read that happened MUST
#: appear here, because the journal schema requires the hashes of everything a
#: step consumed or produced.
ACCESS_FIELDS = ("inputs_sha256", "outputs_sha256", "command_sha256")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def record_reads_a_sealed_lens(record: dict) -> bool:
    """True if this record shows an actual access to a sealed lens.

    Only the structured provenance fields count. A note saying "the lenses have
    not been read" references the lenses without reading them, and treating that
    as a violation would make the guard fire on its own evidence.

    Both the name and the immutable content address are matched, so renaming the
    file does not evade the check.
    """
    blob = json.dumps([record.get(f) for f in ACCESS_FIELDS], ensure_ascii=False)
    if LENS_PATTERN.search(blob):
        return True
    return any(digest in blob for digest in SEALED_LENS_SHA256.values())


def record_mentions_a_sealed_lens_in_prose(record: dict) -> bool:
    """True if the free-text note names a sealed lens.

    Surfaced rather than treated as a violation: prose is not access. It is
    still reported, because a read recorded ONLY in prose would be a journal
    completeness failure that a reader should see rather than have hidden.
    """
    note = str(record.get("note") or "")
    return bool(LENS_PATTERN.search(note)) or any(
        digest in note for digest in SEALED_LENS_SHA256.values()
    )


def judge(records: list[dict]) -> dict:
    convention = [r for r in records if r.get("step_id") == CONVENTION_STEP_ID]

    lens_records = [
        r
        for r in records
        if r.get("step_id") != CONVENTION_STEP_ID and record_reads_a_sealed_lens(r)
    ]
    prose_only = [
        r.get("step_id")
        for r in records
        if r.get("step_id") != CONVENTION_STEP_ID
        and record_mentions_a_sealed_lens_in_prose(r)
        and not record_reads_a_sealed_lens(r)
    ]

    if not convention:
        return {
            "verdict": "FAIL",
            "reason": (
                "no convention-commit record found; the ordering claim OD-012 "
                "makes is unsupported, so it cannot be reported as satisfied"
            ),
            "convention_commit_present": False,
            "lens_reading_records": [r.get("step_id") for r in lens_records],
            "lens_reading_record_count": len(lens_records),
            "prose_mentions_not_reads": prose_only,
            "violations": [],
        }

    if len(convention) > 1:
        return {
            "verdict": "FAIL",
            "reason": (
                f"{len(convention)} convention-commit records found; with more "
                "than one there is no single boundary to be later than"
            ),
            "convention_commit_present": True,
            "violations": [],
        }

    boundary = convention[0].get("ts_start_utc")
    if not boundary:
        return {
            "verdict": "FAIL",
            "reason": "the convention-commit record carries no timestamp",
            "convention_commit_present": True,
            "violations": [],
        }

    violations = []
    undated = []
    for record in lens_records:
        stamp = record.get("ts_start_utc")
        if not stamp:
            undated.append(record.get("step_id"))
            continue
        if stamp <= boundary:
            violations.append(
                {
                    "step_id": record.get("step_id"),
                    "ts_start_utc": stamp,
                    "convention_commit_ts": boundary,
                }
            )

    ok = not violations and not undated
    return {
        "verdict": "PASS" if ok else "FAIL",
        "reason": (
            "every record that reads a sealed lens is later than the "
            "convention-commit record"
            if ok
            else "a sealed lens was read at or before the convention commit, "
            "or by a record with no timestamp"
        ),
        "convention_commit_present": True,
        "convention_commit_ts": boundary,
        "lens_reading_records": [r.get("step_id") for r in lens_records],
        "lens_reading_record_count": len(lens_records),
        "prose_mentions_not_reads": prose_only,
        "violations": violations,
        "records_without_timestamp": undated,
        "what_counts_as_a_read": (
            "an appearance of the lens name or of its immutable sha256 in "
            "inputs_sha256, outputs_sha256 or command_sha256; a free-text note "
            "naming a lens is surfaced separately and is not a read"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    records: list[dict] = []
    for journal in args.journal:
        path = Path(journal)
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))

    report = judge(records)
    report["schema_version"] = "study5-eq2-od012-guard-v1"
    report["rule"] = "OD-012"
    report["hard_blocker_if_failed"] = 5
    report["journals"] = list(args.journal)
    report["records_examined"] = len(records)

    Path(args.out).write_bytes(canonical_json_bytes(report))
    print(json.dumps(report, indent=1))
    if report["verdict"] != "PASS":
        print("EQ2-CHECK-OD012-ORDERING FAILED", file=sys.stderr)
        return 1
    print("EQ2-CHECK-OD012-ORDERING PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
