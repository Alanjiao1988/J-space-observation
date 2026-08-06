#!/usr/bin/env python3
"""Validate the model-free full-layer S2 protocol package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_ROOT = PROJECT_ROOT / "src" / "jspace_observation"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

import jlens_s2_protocol as s2  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--require-pre-round-ledger-tail",
        action="store_true",
        help="require EV-0014 to remain the final row (S2-G0/P0 only)",
    )
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    try:
        s2.load_and_validate_protocol(root)
        s2.load_and_validate_corpus_contract(root)
        schemas = s2.validate_auxiliary_schemas(root)
        starting = s2.verify_starting_state(
            root,
            require_pre_round_ledger_tail=args.require_pre_round_ledger_tail,
        )
    except s2.S2ProtocolError as exc:
        print(f"BLOCKED_ON_S2_STARTING_STATE_INTEGRITY: {exc}", file=sys.stderr)
        return 1
    result = {
        "artifact_schema_sha256": schemas["docs/jlens_s2_artifacts.schema.json"],
        "corpus_contract_sha256": s2.sha256_file(
            root / "docs" / "jlens_s2_corpus_source_contract.json"
        ),
        "e0_schema_sha256": schemas["docs/jlens_s3_e0_pack.schema.json"],
        "protocol_sha256": s2.sha256_file(root / "docs" / "jlens_s2_protocol.json"),
        "schema_sha256": s2.sha256_file(
            root / "docs" / "jlens_s2_protocol.schema.json"
        ),
        "starting_state": starting,
        "status": "S2_PROTOCOL_PACKAGE_VALID",
    }
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"STATUS={result['status']}")
        for key in (
            "protocol_sha256",
            "schema_sha256",
            "corpus_contract_sha256",
            "artifact_schema_sha256",
            "e0_schema_sha256",
        ):
            print(f"{key.upper()}={result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
