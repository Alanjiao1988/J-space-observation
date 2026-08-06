#!/usr/bin/env python3
"""Validate the model-free J-lens S3 protocol package and vendored bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "jspace_observation"))

import jlens_s3_protocol as protocol  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--json", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    try:
        document = protocol.load_and_validate_protocol(root)
        source_report = protocol.verify_vendored_sources(root, document)
    except protocol.ProtocolError as exc:
        print(f"BLOCKED_ON_PREREGISTRATION_INTEGRITY: {exc}", file=sys.stderr)
        return 1

    result = {
        "counterparts": source_report["counterparts"],
        "protocol_sha256": _sha256(root / "docs" / "jlens_s3_validity_protocol.json"),
        "schema_sha256": _sha256(
            root / "docs" / "jlens_s3_validity_protocol.schema.json"
        ),
        "status": "JLENS_S3_VALIDITY_PROTOCOL_CANDIDATE_VALID",
        "upstream_files": source_report["files"],
    }
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"STATUS={result['status']}")
        print(f"PROTOCOL_SHA256={result['protocol_sha256']}")
        print(f"SCHEMA_SHA256={result['schema_sha256']}")
        print(
            "COUNTERPARTS="
            f"{source_report['counterparts']['oriented_matches']} oriented / "
            f"{source_report['counterparts']['unique_unordered_pairs']} unordered"
        )
        for path, row in source_report["files"].items():
            print(
                f"UPSTREAM={path} bytes={row['bytes']} "
                f"sha256={row['sha256']} items={row['item_count']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
