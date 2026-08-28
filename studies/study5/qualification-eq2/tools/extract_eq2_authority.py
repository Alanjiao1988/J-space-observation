"""Mechanically extract the EQ2 authority from the operator's pasted text.

The authority is never retyped. It is sliced out of the operator's message and
then verified line-for-line against the source, because a transcription error in
a governing document is the kind of fault that is invisible afterwards: the file
would look plausible and would be wrong.

The operator's instruction fixes the boundaries: everything after the separator
that follows the "本节标题与本段说明不属于 authority 正文" note, through the
closing "*End of authority.*" line at the end of the message.

The boundaries are located by anchoring to the document's own structure rather
than by hard-coding line numbers, so that a shifted paste cannot silently
produce a truncated authority.

Usage:
    python extract_eq2_authority.py --source <pasted.txt> --out <authority.md>
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

FIRST_LINE_MUST_BE = "# Study 5-EQ2 — construct adjudication authority"
LAST_LINE_MUST_START_WITH = "*End of authority."
NOTE_MARKER = "authority \u6b63\u6587"


def locate(lines: list[str]) -> tuple[int, int]:
    """Return the inclusive (start, end) indices of the authority body."""
    note_index = next((i for i, line in enumerate(lines) if NOTE_MARKER in line), None)
    if note_index is None:
        raise SystemExit("could not find the instruction note preceding the authority")

    separator_index = next(
        (i for i in range(note_index + 1, len(lines)) if lines[i].strip() == "---"),
        None,
    )
    if separator_index is None:
        raise SystemExit("could not find the separator after the instruction note")

    start = next(
        (i for i in range(separator_index + 1, len(lines)) if lines[i].strip() != ""),
        None,
    )
    if start is None:
        raise SystemExit("no content after the separator")

    ends = [
        i for i, line in enumerate(lines) if line.startswith(LAST_LINE_MUST_START_WITH)
    ]
    if not ends:
        raise SystemExit("could not find the closing End of authority line")
    return start, max(ends)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    raw = source.read_text(encoding="utf-8")
    lines = raw.split("\n")

    start, end = locate(lines)

    if lines[start] != FIRST_LINE_MUST_BE:
        raise SystemExit(
            f"first authority line is {lines[start]!r}, "
            f"expected {FIRST_LINE_MUST_BE!r}"
        )

    extracted = lines[start : end + 1]

    text = "\n".join(extracted) + "\n"
    payload = text.encode("utf-8")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as handle:
        handle.write(payload)

    # Read the file back off disk and compare it to the SOURCE, not to the
    # in-memory copy, so the check exercises the whole write path.
    readback_lines = out.read_bytes().decode("utf-8").split("\n")
    if readback_lines[-1] != "":
        raise SystemExit("file does not end with a newline")
    readback_lines = readback_lines[:-1]

    if len(readback_lines) != end - start + 1:
        raise SystemExit(
            f"line count differs: wrote {len(readback_lines)}, "
            f"source span is {end - start + 1}"
        )

    mismatches = [
        (start + offset + 1, lines[start + offset], written)
        for offset, written in enumerate(readback_lines)
        if lines[start + offset] != written
    ]
    if mismatches:
        for number, expected, actual in mismatches:
            print(f"line {number}: {expected!r} != {actual!r}", file=sys.stderr)
        raise SystemExit(f"{len(mismatches)} line mismatches against the source")

    crlf = b"\r" in payload
    bom = payload.startswith(b"\xef\xbb\xbf")

    print(f"source           {source}")
    print(f"source lines     {start + 1}..{end + 1}")
    print(f"lines written    {len(readback_lines)}")
    print(f"bytes            {len(payload)}")
    print(f"sha256           {hashlib.sha256(payload).hexdigest()}")
    print(f"crlf present     {crlf}")
    print(f"bom present      {bom}")
    print(f"first line       {readback_lines[0]}")
    print(f"last line        {readback_lines[-1]}")
    print(f"mismatches       {len(mismatches)}")
    if crlf or bom:
        raise SystemExit("authority must be LF, UTF-8 without BOM")
    print("EQ2-CHECK-AUTHORITY-EXTRACT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
