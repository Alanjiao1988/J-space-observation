"""Container entrypoint for Phase 1.0C Track B headroom calibration."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jspace_observation.headroom_calibration import (  # noqa: E402
    DEFAULT_BANK_PATH,
    MODES,
    RunConfig,
    SelfTestBackend,
    run_calibration,
)


DEFAULT_OUTPUT_ROOT = ROOT / "phase1-headroom-calibration" / "track-b"


def _optional_path(value: str | None) -> Path | None:
    return None if value in (None, "") else Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run bounded capability/headroom calibration for Phase 1.0C Track B. "
            "This is task calibration only; it licenses no claim about hidden "
            "reasoning, internal state, or 'J-space'."
        )
    )
    parser.add_argument(
        "--mode",
        choices=list(MODES),
        default="plan",
        help=(
            "plan: register the selection and generation plan without a model. "
            "generate: run the target model on GPU. "
            "finalize: ingest semantic judgments and select cells. "
            "self-test: run the whole pipeline against a scripted offline backend."
        ),
    )
    parser.add_argument("--bank", type=Path, default=ROOT / DEFAULT_BANK_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--code-commit", default=os.environ.get("JSPACE_CODE_COMMIT"))
    parser.add_argument(
        "--image-digest",
        default=os.environ.get("JSPACE_IMAGE_DIGEST", "not_recorded"),
    )
    parser.add_argument(
        "--hardware",
        default=os.environ.get("JSPACE_HARDWARE", "not_recorded"),
    )
    parser.add_argument("--frozen-time", default=os.environ.get("JSPACE_FROZEN_TIME"))
    parser.add_argument("--records", default=None, help="Prior 02_records.jsonl for finalize mode.")
    parser.add_argument("--judgments", default=None, help="Primary reviewer JSONL.")
    parser.add_argument("--arbiter-judgments", default=None, help="Arbiter JSONL.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias for --mode plan; performs no model execution.",
    )
    parser.add_argument(
        "--upload-blob",
        action="store_true",
        help="Upload the emitted pack with the repository managed-identity exporter.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode = "plan" if args.dry_run else args.mode

    config = RunConfig(
        mode=mode,
        output_root=Path(args.output_root),
        bank_path=Path(args.bank),
        repo_root=ROOT,
        run_id=args.run_id,
        code_commit=args.code_commit,
        image_digest=args.image_digest,
        hardware=args.hardware,
        frozen_time=args.frozen_time,
        judgments_path=_optional_path(args.judgments),
        arbiter_judgments_path=_optional_path(args.arbiter_judgments),
        records_path=_optional_path(args.records),
        backend=SelfTestBackend() if mode == "self-test" else None,
    )
    result = run_calibration(config)

    if args.upload_blob:
        from jspace_observation.blob_export import upload_directory_to_blob  # noqa: PLC0415

        upload_directory_to_blob(str(result["output_dir"]), require=True)

    summary = {
        "cells_scored": len(result["cells"]),
        "mode": mode,
        "output_dir": str(result["output_dir"]),
        "records": len(result["records"]),
        "review_rows": len(result["review_rows"]),
        "run_id": result["run_id"],
        "selected_headroom_cells": result["decision"]["selected_headroom_cells"],
        "status": result["decision"]["status"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
