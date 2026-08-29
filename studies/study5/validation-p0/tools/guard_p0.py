"""P-0 sealed-asset guard: lens_A, lens_B and T are never touched.

The guard is deliberately content-addressed as well as name-based. A file can
be renamed; its sha256 cannot. It also scans the tools themselves, not only the
journal, because a read that never reached the journal would be exactly the
kind of omission a journal-only check cannot see.

Prose is not access. A note saying "the lenses were not read" names them
without reading them, and a guard that fired on its own evidence would be
useless. So free-text mentions are surfaced separately and are not violations.

OD-011: failing cases in tests/test_p0_guard.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: EQ1's sealed lens digests, from EQ1's merge report, immutable.
SEALED_LENS_SHA256 = {
    "lens_A": "2910b7bf80784a48f4e0d41f1a6fd002781f1d3f4f6bc3df83fb547848164083",
    "lens_B": "e6d7eec9cb33035edb4b702bc3fae807a48d42c29270f40b9c461e6116ee528a",
}

LENS_PATTERN = re.compile(r"lens_[AB]\b")

#: The protected target, by repository id and by pinned revision.
TARGET_MARKERS = (
    "DeepSeek-R1-Distill-Qwen-7B",
    "916b56a44061fd5cd7d6a8fb632557ed4f724f60",
)

#: An import of the instrument under test. Matched as a STATEMENT rather than
#: as a substring, so that a file which merely names the library - this one, and
#: the OD-017 auditor - is not reported as importing it. A substring match would
#: fire on its own source, and a guard that cannot be written without tripping
#: itself gets silenced rather than fixed.
JLENS_IMPORT = re.compile(r"^\s*(?:import\s+jlens|from\s+jlens\b)", re.MULTILINE)

#: The single file excused from the marker scan, because it cannot perform the
#: scan without containing the markers it scans for.
SELF = "guard_p0.py"

#: Journal fields in which an actual file access is recorded.
ACCESS_FIELDS = ("inputs_sha256", "outputs_sha256", "command_sha256")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def reads_a_sealed_lens(record: dict) -> bool:
    blob = json.dumps([record.get(f) for f in ACCESS_FIELDS], ensure_ascii=False)
    if LENS_PATTERN.search(blob):
        return True
    return any(digest in blob for digest in SEALED_LENS_SHA256.values())


def mentions_in_prose(record: dict) -> bool:
    note = str(record.get("note") or "")
    return bool(LENS_PATTERN.search(note)) or any(
        digest in note for digest in SEALED_LENS_SHA256.values()
    )


def scan_journal(namespace: Path) -> dict:
    records: list[dict] = []
    for path in sorted((namespace / "journal").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    reads = [r.get("step_id") for r in records if reads_a_sealed_lens(r)]
    prose = [
        r.get("step_id")
        for r in records
        if mentions_in_prose(r) and not reads_a_sealed_lens(r)
    ]
    return {
        "records_examined": len(records),
        "lens_reading_records": reads,
        "lens_reading_record_count": len(reads),
        "prose_mentions_not_reads": prose,
    }


def imports_jlens(source: str) -> bool:
    """True when the source contains an actual import statement for jlens.

    Naming the library in a comment, a docstring or a regex is not importing
    it, and treating it as such would make this check impossible to write.
    """
    return bool(JLENS_IMPORT.search(source))


def scan_tools(namespace: Path) -> dict:
    hits: list[dict] = []
    imports: list[str] = []
    scanned: list[str] = []
    for path in sorted((namespace / "tools").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if imports_jlens(text):
            imports.append(path.name)
        if path.name == SELF:
            continue
        scanned.append(path.name)
        for marker in TARGET_MARKERS:
            if marker in text:
                hits.append({"file": path.name, "marker": marker})
        for name, digest in SEALED_LENS_SHA256.items():
            if digest in text or name in text:
                hits.append({"file": path.name, "marker": name})
    return {
        "target_or_lens_references_in_tools": hits,
        "tools_importing_jlens": imports,
        "tools_scanned": scanned,
        "excluded_from_the_marker_scan": [SELF],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    namespace = Path(args.namespace)
    journal = scan_journal(namespace)
    tools = scan_tools(namespace)

    ok = (
        journal["lens_reading_record_count"] == 0
        and not tools["target_or_lens_references_in_tools"]
        and not tools["tools_importing_jlens"]
    )
    report = {
        "schema_version": "study5-p0-guard-v1",
        "phase": "P-0",
        "verdict": "PASS" if ok else "FAIL",
        "journal": journal,
        "tools": tools,
        "sealed_lens_sha256": SEALED_LENS_SHA256,
        "target_markers": list(TARGET_MARKERS),
        "what_counts_as_a_read": (
            "an appearance of a sealed lens name or of its immutable sha256 in "
            "inputs_sha256, outputs_sha256 or command_sha256; a free-text note "
            "naming a lens is surfaced separately and is not a read"
        ),
        "what_counts_as_importing_the_instrument_under_test": (
            "an import statement for jlens; naming the library in a comment, a "
            "docstring or a pattern is not importing it, and a substring rule "
            "would fire on this guard's own source"
        ),
        "why_the_tools_are_scanned_too": (
            "a read that never reached the journal is exactly what a "
            "journal-only check cannot see"
        ),
        "guard_excludes_itself": (
            "guard_p0.py necessarily contains the markers it matches on, so it "
            "is excluded from the marker scan and is the ONLY file so excluded; "
            "it is still scanned for an actual jlens import"
        ),
        "claim_ceiling": "A guard record. It licenses no claim of any kind.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))
    print(json.dumps({k: v for k, v in report.items() if k != "sealed_lens_sha256"}, indent=1))
    if not ok:
        print("P0-CHECK-GUARD FAILED", file=sys.stderr)
        return 1
    print("P0-CHECK-GUARD PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
