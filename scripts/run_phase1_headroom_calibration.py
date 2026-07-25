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
    MODEL_ID,
    MODEL_REVISION,
    MODES,
    RunConfig,
    SelfTestBackend,
    run_calibration,
)


DEFAULT_OUTPUT_ROOT = ROOT / "phase1-headroom-calibration" / "track-b"


def _optional_path(value: str | None) -> Path | None:
    return None if value in (None, "") else Path(value)


def runtime_environment() -> dict[str, object]:
    """Report the observed runtime versions so the pack's claims are checkable."""

    environment: dict[str, object] = {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "python_version": (
            f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
        ),
    }
    import importlib  # noqa: PLC0415 - keeps the module import-light on CPU hosts

    for label, module_name in (("torch", "torch"), ("transformers", "transformers")):
        try:
            module = importlib.import_module(module_name)
            environment[f"{label}_version"] = getattr(module, "__version__", "unknown")
        except Exception as error:  # pragma: no cover - absent on CPU test hosts
            environment[f"{label}_version"] = f"unavailable: {type(error).__name__}"
    try:
        import torch  # noqa: PLC0415

        environment["cuda_available"] = bool(torch.cuda.is_available())
        environment["cuda_device_name"] = (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        )
    except Exception as error:  # pragma: no cover - absent on CPU test hosts
        environment["cuda_available"] = f"unavailable: {type(error).__name__}"
        environment["cuda_device_name"] = None
    return environment


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
    parser.add_argument("--run-id", default=os.environ.get("JSPACE_HEADROOM_RUN_ID"))
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
        help=(
            "Upload the emitted pack with the managed-identity transport, "
            "writing artifact_manifest.json last."
        ),
    )
    parser.add_argument(
        "--blob-prefix",
        default=None,
        help="Blob prefix; defaults to JSPACE_BLOB_PREFIX or the registered root.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode = "plan" if args.dry_run else args.mode

    environment = runtime_environment()
    print(json.dumps({"runtime_environment": environment}, sort_keys=True))

    if mode == "generate" and not args.code_commit:
        print(
            "[FAIL] generate mode requires --code-commit or JSPACE_CODE_COMMIT",
            file=sys.stderr,
        )
        return 1
    if mode == "generate" and args.image_digest == "not_recorded":
        print(
            "[FAIL] generate mode requires --image-digest or JSPACE_IMAGE_DIGEST",
            file=sys.stderr,
        )
        return 1

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

    upload: dict[str, object] | None = None
    if args.upload_blob:
        from jspace_observation.headroom_blob_transport import upload_pack  # noqa: PLC0415

        upload = upload_pack(
            result["output_dir"],
            str(result["run_id"]),
            prefix=args.blob_prefix,
            require=True,
        )

    summary = {
        "cells_scored": len(result["cells"]),
        "mode": mode,
        "output_dir": str(result["output_dir"]),
        "records": len(result["records"]),
        "review_rows": len(result["review_rows"]),
        "run_id": result["run_id"],
        "runtime_environment": environment,
        "selected_headroom_cells": result["decision"]["selected_headroom_cells"],
        "status": result["decision"]["status"],
        "upload": upload,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
