"""Generate or verify the deterministic Phase 1 capability-headroom bank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jspace_observation.headroom_candidates import (  # noqa: E402
    candidate_bank_sha256,
    candidate_count_matrix,
    candidate_schema,
    generate_candidate_bank,
    method_suitability_counts,
    serialize_candidate_bank,
    validate_candidate_bank,
    write_candidate_bank,
)


DEFAULT_OUTPUT = ROOT / "data" / "phase1_task_headroom_candidates.jsonl"
DEFAULT_SCHEMA = ROOT / "data" / "phase1_task_headroom_candidate.schema.json"


def _check_file(path: Path, expected: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing generated file: {path}")
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        raise SystemExit(f"Generated file is stale: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify checked-in files instead of rewriting them.",
    )
    args = parser.parse_args()

    records = generate_candidate_bank()
    validate_candidate_bank(records)
    if args.check:
        _check_file(args.output, serialize_candidate_bank(records))
        expected_schema = (
            json.dumps(candidate_schema(), indent=2, ensure_ascii=False) + "\n"
        )
        _check_file(args.schema, expected_schema)
    else:
        write_candidate_bank(args.output, args.schema)

    summary = {
        "records": len(records),
        "sha256": candidate_bank_sha256(records),
        "counts": candidate_count_matrix(records),
        "method_design_candidates": method_suitability_counts(records),
        "mode": "checked" if args.check else "written",
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
