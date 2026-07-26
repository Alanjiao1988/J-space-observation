"""Derive the parser-v3 isolated worker from the frozen parser-v2 worker.

The worker's hardcoded identity is its security property: a worker that
self-attests which parser it loaded cannot be redirected by its caller. So the
v3 worker is a sibling that pins v3, not a parameterised v2 worker. Deriving it
by exact substitution keeps the two provably identical everywhere else.
"""

from __future__ import annotations

import difflib
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "parser_v2_process_worker.py"
TARGET = ROOT / "scripts" / "parser_v3_process_worker.py"

SUBSTITUTIONS = (
    (
        '"""One-request isolated process for the exact frozen parser-v2 extraction."""',
        '"""One-request isolated process for the exact frozen parser-v3 extraction."""',
    ),
    (
        '_EXPECTED_PARSER_SOURCE_SHA256 = (\n'
        '    "f538add0bdd6e5a3281d0298b374a99fecea962a91a4cbaa5b4a20795d9a6918"\n'
        ')',
        '_EXPECTED_PARSER_SOURCE_SHA256 = (\n'
        '    "76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9"\n'
        ')',
    ),
    (
        '_EXPECTED_PARSER_VERSION = (\n'
        '    "6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86"\n'
        ')',
        '_EXPECTED_PARSER_VERSION = (\n'
        '    "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace"\n'
        ')',
    ),
    (
        'parser_path = source_root / "eval_parsing_v2.py"',
        'parser_path = source_root / "eval_parsing_v3.py"',
    ),
    (
        'parser = _load_module(f"{package_name}.eval_parsing_v2", parser_path)',
        'parser = _load_module(f"{package_name}.eval_parsing_v3", parser_path)',
    ),
    (
        "    return parser.parse_v2\n",
        "    return parser.parse_v3\n",
    ),
)


def main() -> int:
    original = SOURCE.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    text = original.decode("utf-8")
    for old, new in SUBSTITUTIONS:
        found = text.count(old)
        if found != 1:
            print(f"expected 1 occurrence, found {found}: {old[:60]!r}")
            return 1
        text = text.replace(old, new)

    derived = text.encode("utf-8")
    changed = [
        line
        for line in difflib.unified_diff(
            original.decode("utf-8").splitlines(),
            text.splitlines(),
            lineterm="",
            n=0,
        )
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    if len(changed) != 2 * len(SUBSTITUTIONS):
        print(f"unexpected diff size: {len(changed)} changed lines")
        for line in changed:
            print("   ", line)
        return 1

    if "--check" in sys.argv:
        current = TARGET.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if current != derived:
            print("parser_v3_process_worker.py is not the faithful derivation")
            return 1
        print("DERIVATION_FAITHFUL")
    else:
        TARGET.write_bytes(derived)
        print(f"wrote {TARGET.relative_to(ROOT)}")

    print(f"changed lines: {len(changed)}")
    for line in changed:
        print("   ", line)
    print(f"v2 worker sha256: {hashlib.sha256(original).hexdigest()}")
    print(f"v3 worker sha256: {hashlib.sha256(derived).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
