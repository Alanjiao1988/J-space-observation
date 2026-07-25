"""Main-agent cross-checks required before the parser-v3-v1 seal.

Reproduces the manifest fingerprint functions from the Track D builder and
tests every corpus the main agent can reach for overlap with the locked set.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from build_parser_v3_validation_set import fingerprints  # noqa: E402

FIELDS = ("exact_sha256", "normalized_sha256", "numeric_normalized_sha256")


def locked_fingerprints() -> dict[str, set[str]]:
    manifest = json.loads(
        (REPO / "evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json")
        .read_text(encoding="utf-8")
    )
    records = manifest.get("records") or manifest.get("cases") or []
    out = {f: set() for f in FIELDS}
    for row in records:
        marks = row.get("fingerprints", row)
        for f in FIELDS:
            if marks.get(f):
                out[f].add(marks[f])
    return out


def texts_from_jsonl(path: Path, keys: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        for key in keys:
            value = row.get(key)
            if isinstance(value, str) and value:
                found.append(value)
    return found


def compare(name: str, texts: list[str], locked: dict[str, set[str]]) -> bool:
    hits: dict[str, list[str]] = {f: [] for f in FIELDS}
    for text in texts:
        marks = fingerprints(text)
        for f in FIELDS:
            if marks[f] in locked[f]:
                hits[f].append(marks[f])
    clean = all(not v for v in hits.values())
    print(f"--- {name}: {len(texts)} output-bearing strings")
    for f in FIELDS:
        print(f"    {f}: {len(hits[f])} collisions")
    return clean


def main() -> int:
    locked = locked_fingerprints()
    print("locked set fingerprints loaded:",
          {f: len(locked[f]) for f in FIELDS})
    if any(len(locked[f]) != 120 for f in FIELDS):
        print("[FAIL] expected 120 distinct fingerprints per field")
        return 1

    checks: list[tuple[str, Path, tuple[str, ...]]] = [
        (
            "parser-v3 public adversarial development set",
            REPO / "evaluator_sets/parser_v3_v1/adversarial_development_cases.jsonl",
            ("output_text", "text", "model_output"),
        ),
        (
            "parser-v2 public development set",
            REPO / "evaluator_sets/parser_v2_v1/development_cases.jsonl",
            ("output_text", "text", "model_output"),
        ),
        (
            "18-record ambiguous audit extract",
            REPO / "artifacts/record_audit/ambiguous_records_for_review.jsonl",
            ("output_text", "text", "model_output", "generation", "completion"),
        ),
    ]

    all_clean = True
    for name, path, keys in checks:
        if not path.exists():
            print(f"--- {name}: SKIPPED, not present at {path}")
            all_clean = False
            continue
        texts = texts_from_jsonl(path, keys)
        if not texts:
            print(
                f"--- {name}: VACUOUS, no output-bearing field present, "
                "so it cannot collide with locked output text"
            )
            continue
        all_clean &= compare(name, texts, locked)

    print("ALL_INTERSECTIONS_EMPTY:", all_clean)
    return 0 if all_clean else 2


if __name__ == "__main__":
    raise SystemExit(main())
