"""Restore the committed line-ending convention, and verify the diff is exactly the reorder.

The reorder tool read the file in text mode and wrote it back with LF, which
silently converted 186 CRLF pairs. The substance proof was unaffected, but the
byte-level claim would have been wrong: the file would have differed from its
committed form in 186 places that have nothing to do with the rearrangement.

This restores CRLF, and then makes a check that is only possible because the
rearrangement is pure: the three ordinal changes are all single digits, so if
nothing else moved, THE BYTE COUNT MUST BE UNCHANGED. A byte-count match against
the committed version is therefore a strong, cheap confirmation that the diff
contains the reorder and nothing else.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent.parent.parent
DOC = ROOT / "STUDY5_CLOSURE.md"
RELATIVE = "studies/study5/closure/STUDY5_CLOSURE.md"


def main() -> int:
    committed = subprocess.run(
        ["git", "show", f"HEAD:{RELATIVE}"], cwd=REPO, capture_output=True
    ).stdout
    current_lf = DOC.read_bytes()
    if b"\r\n" in current_lf:
        raise SystemExit("the working file already contains CRLF; nothing to restore")

    restored = current_lf.replace(b"\n", b"\r\n")
    DOC.write_bytes(restored)

    same_length = len(restored) == len(committed)
    committed_lines = sorted(
        line for line in committed.decode("utf-8").splitlines()
        if not line.startswith("## ")
    )
    restored_lines = sorted(
        line for line in restored.decode("utf-8").splitlines()
        if not line.startswith("## ")
    )
    lines_identical = committed_lines == restored_lines

    committed_headings = [
        line for line in committed.decode("utf-8").splitlines()
        if line.startswith("## ")
    ]
    restored_headings = [
        line for line in restored.decode("utf-8").splitlines()
        if line.startswith("## ")
    ]

    report = {
        "schema_version": "study5-closure-eol-restore-v1",
        "why": (
            "the reorder tool read in text mode and wrote back with LF, silently "
            "converting 186 CRLF pairs; the substance proof was unaffected but the "
            "byte-level claim would have been wrong"
        ),
        "crlf_pairs_restored": restored.count(b"\r\n"),
        "committed_bytes": len(committed),
        "restored_bytes": len(restored),
        "byte_count_unchanged": same_length,
        "why_the_byte_count_must_match": (
            "the three ordinal changes are all single digits, so if nothing but the "
            "order moved, the byte count is necessarily identical; a match is a "
            "cheap and strong confirmation that the diff contains the reorder and "
            "nothing else"
        ),
        "multiset_of_non_heading_lines_unchanged_vs_committed": lines_identical,
        "headings_committed": committed_headings,
        "headings_now": restored_headings,
        "sha256_committed_superseded": hashlib.sha256(committed).hexdigest(),
        "sha256_now": hashlib.sha256(restored).hexdigest(),
        "claim_ceiling": "A byte-level verification record. It licenses no claim.",
    }
    (ROOT / "CLOSURE_EOL_RESTORE.json").write_bytes(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )

    print(f"CRLF pairs restored              : {report['crlf_pairs_restored']}")
    print(f"committed bytes                  : {len(committed)}")
    print(f"restored bytes                   : {len(restored)}")
    print(f"byte count unchanged             : {same_length}")
    print(f"non-heading lines identical      : {lines_identical}")
    print()
    print("headings now:")
    for heading in restored_headings:
        print(f"  {heading}")
    print()
    print(f"sha256 committed (SUPERSEDED): {report['sha256_committed_superseded']}")
    print(f"sha256 now                   : {report['sha256_now']}")
    if not (same_length and lines_identical):
        raise SystemExit("the diff is not a pure reorder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
