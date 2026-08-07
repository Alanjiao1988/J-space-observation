#!/usr/bin/env python3
"""Build the deterministic, model-free Study 2 public task banks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "jspace_observation"))

import study2_protocol as protocol  # noqa: E402
import study2_task_bank as task_bank  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--output-root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    output = Path(args.output_root).resolve() if args.output_root else None
    try:
        protocol.load_and_validate_protocol(root)
        result = task_bank.generate_all(root, output)
    except (protocol.ProtocolError, OSError, RuntimeError, ValueError) as exc:
        print(f"BLOCKED_ON_STUDY2_PREREGISTRATION_INTEGRITY: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print("STATUS=STUDY2_MODEL_FREE_BANKS_GENERATED")
        if isinstance(result, dict) and "files" in result:
            for role, row in result["files"].items():
                print(f"BANK={role} rows={row['rows']} bytes={row['bytes']} sha256={row['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
