#!/usr/bin/env python3
"""Build model-free parser-v2 validation drafts from sealed curator inputs."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_validation_module() -> ModuleType:
    name = "_jspace_evaluator_validation_build"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = PROJECT_ROOT / "src" / "jspace_observation" / "evaluator_validation.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load evaluator validation tooling")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validation = _load_validation_module()
ValidationSetError = validation.ValidationSetError


def _read_regular_bytes(path: str | Path, name: str) -> bytes:
    source = Path(path)
    if not source.is_file() or source.is_symlink():
        raise ValidationSetError(f"{name} must be a regular file")
    return source.read_bytes()


def _read_jsonl(path: str | Path, name: str) -> list[dict[str, Any]]:
    raw = _read_regular_bytes(path, name)
    rows = validation.parse_jsonl_strict(raw, name)
    if validation.canonical_jsonl_bytes(rows) != raw:
        raise ValidationSetError(f"{name} must be canonical ASCII JSONL")
    return rows


def _read_json(path: str | Path, name: str) -> dict[str, Any]:
    raw = _read_regular_bytes(path, name)
    value = validation.parse_json_strict(raw, name)
    if validation.canonical_json_bytes(value) != raw:
        raise ValidationSetError(f"{name} must be canonical ASCII JSON")
    return value


def _read_authoritative_historical_bytes(
    generation_path: str | Path, evaluation_path: str | Path
) -> dict[str, bytes]:
    paths = {
        "phase1_generations.jsonl": Path(generation_path),
        "phase1_eval_records.jsonl": Path(evaluation_path),
    }
    result: dict[str, bytes] = {}
    for expected_name, path in paths.items():
        if (
            path.name != expected_name
            or not path.is_file()
            or path.is_symlink()
        ):
            raise ValidationSetError(
                f"historical artifact must be the exact named file {expected_name}"
            )
        result[expected_name] = path.read_bytes()
    return result


def _single_curator_id(
    rows: Sequence[Mapping[str, Any]], pool_name: str
) -> str:
    identities = {
        row.get("curator_id")
        for row in rows
        if isinstance(row.get("curator_id"), str)
    }
    if len(identities) != 1:
        raise ValidationSetError(f"{pool_name} must have one curator identity")
    return next(iter(identities))


def build_validation_drafts(
    curator_a: Sequence[Mapping[str, Any]],
    curator_b: Sequence[Mapping[str, Any]],
    curator_a_seal: Mapping[str, Any],
    curator_b_seal: Mapping[str, Any],
    selection_plan: Mapping[str, Any],
    private_salts: Mapping[str, Any],
    historical_source_bytes: Mapping[str, bytes],
) -> dict[str, bytes]:
    """Validate inputs fully and return deterministic artifact bytes."""
    historical_generations, historical_evaluations = (
        validation.validate_authoritative_historical_corpus(
            historical_source_bytes
        )
    )
    curator_a_id = _single_curator_id(curator_a, "curator A pool")
    curator_b_id = _single_curator_id(curator_b, "curator B pool")
    if curator_a_id == curator_b_id:
        raise ValidationSetError("the two curator pools must be independent")
    validation.validate_curator_pool_seal(
        curator_a_seal, curator_a, expected_curator_id=curator_a_id
    )
    validation.validate_curator_pool_seal(
        curator_b_seal, curator_b, expected_curator_id=curator_b_id
    )
    selected = validation.validate_selection_plan(
        selection_plan,
        curator_a,
        curator_b,
        curator_a_seal,
        curator_b_seal,
    )
    materialized = validation.materialize_selection(selected, private_salts)
    composition = validation.validate_dataset_composition(
        materialized["development"], materialized["locked_draft_labels"]
    )

    historical = validation.historical_output_fingerprints(
        historical_generations, historical_evaluations
    )
    overlap = validation.detect_fixture_overlaps(
        selected["development"],
        selected["locked"],
        historical_fingerprints=historical,
    )
    validation.require_no_hard_overlaps(overlap)
    near = validation.near_duplicate_report(
        selected["development"], selected["locked"]
    )
    validation.validate_near_duplicate_dispositions(
        near, selected["near_duplicate_dispositions"]
    )
    if any(
        item["decision"] != "keep"
        for item in selected["near_duplicate_dispositions"]
    ):
        raise ValidationSetError(
            "a selected near-duplicate pair cannot have a reject disposition"
        )
    overlap["near_duplicates"] = near
    overlap["near_duplicate_dispositions"] = list(
        selected["near_duplicate_dispositions"]
    )
    overlap["near_duplicate_dispositions_complete"] = True

    mapping = validation.build_case_mapping(
        materialized,
        private_salts,
        selected["selection_plan_sha256"],
        curator_c_id=selected["curator_c_id"],
        custodian_id=validation.REGISTERED_CUSTODIAN_ID,
        curator_pool_seals=selected["curator_pool_seals"],
    )
    development_bytes = validation.canonical_jsonl_bytes(
        materialized["development"]
    )
    locked_input_bytes = validation.canonical_jsonl_bytes(
        materialized["locked_inputs"]
    )
    mapping_bytes = validation.canonical_json_bytes(mapping)
    draft_label_bytes = validation.canonical_jsonl_bytes(
        materialized["locked_draft_labels"]
    )
    overlap_bytes = validation.canonical_json_bytes(overlap)
    public_receipt = {
        "schema_version": "phase1-parser-v2-build-receipt/v1",
        "protocol_commit": validation.FROZEN_PROTOCOL_COMMIT,
        "development_count": composition["development_count"],
        "locked_count": composition["locked_count"],
        "development_sha256": validation.sha256_bytes(development_bytes),
        "locked_inputs_sha256": validation.sha256_bytes(locked_input_bytes),
        "locked_mapping_sha256": validation.sha256_bytes(mapping_bytes),
        "selection_plan_sha256": selected["selection_plan_sha256"],
        "overlap_hard_failure_count": overlap["hard_failure_count"],
        "near_duplicate_count": len(near),
        "model_inference_performed": False,
        "legacy_parser_used_for_selection_or_labels": False,
    }
    return {
        "development_cases.jsonl": development_bytes,
        "build_receipt.json": validation.canonical_json_bytes(public_receipt),
        "private/locked_inputs.jsonl": locked_input_bytes,
        "private/locked_case_mapping.json": mapping_bytes,
        "private/curator_label_drafts.jsonl": draft_label_bytes,
        "private/overlap_report.json": overlap_bytes,
    }


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_external_private_path(
    value: str | Path, *, name: str = "private path"
) -> Path:
    """Require a path outside the repository, every Git worktree, and Docker contexts."""
    raw = Path(value)
    lexical = raw.absolute()
    resolved = raw.resolve(strict=False)
    project = PROJECT_ROOT.resolve()
    if _path_is_within(lexical, project) or _path_is_within(resolved, project):
        raise ValidationSetError(
            f"{name} must be outside the repository, including ignored paths"
        )
    for component in (lexical, *lexical.parents):
        if component.exists() and component.is_symlink():
            raise ValidationSetError(f"{name} may not traverse a symbolic link")
    existing = resolved
    while not existing.exists():
        if existing.parent == existing:
            raise ValidationSetError(f"{name} has no existing ancestor")
        existing = existing.parent
    if existing.is_symlink():
        raise ValidationSetError(f"{name} may not traverse a symbolic link")
    probe = existing if existing.is_dir() else existing.parent
    if not probe.is_dir() or probe.is_symlink():
        raise ValidationSetError(f"{name} ancestor is invalid")
    completed = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        worktree = Path(completed.stdout.strip()).resolve()
        if _path_is_within(resolved, worktree):
            raise ValidationSetError(
                f"{name} must be outside every Git worktree"
            )
    for ancestor in (probe, *probe.parents):
        if (ancestor / "Dockerfile").is_file():
            raise ValidationSetError(
                f"{name} must be outside every Docker context"
            )
    return resolved


def validate_external_staging_root(output_root: str | Path) -> Path:
    """Require a new staging root outside every Git worktree and Docker context."""
    return validate_external_private_path(
        output_root, name="private staging root"
    )


def write_new_output_root(
    output_root: str | Path, files: Mapping[str, bytes]
) -> list[str]:
    """Write only into a new external root, using exclusive file creation."""
    root = validate_external_staging_root(output_root)
    expected = {
        "development_cases.jsonl",
        "build_receipt.json",
        "private/locked_inputs.jsonl",
        "private/locked_case_mapping.json",
        "private/curator_label_drafts.jsonl",
        "private/overlap_report.json",
    }
    if set(files) != expected:
        raise ValidationSetError("builder output membership is not registered")
    if root.exists():
        raise ValidationSetError("output root must be a new external directory")
    root.mkdir(parents=True)
    if validate_external_staging_root(root) != root:
        raise ValidationSetError("private staging root changed during creation")
    private = root / "private"
    private.mkdir()
    written: list[str] = []
    for relative in (
        "development_cases.jsonl",
        "build_receipt.json",
        "private/locked_inputs.jsonl",
        "private/locked_case_mapping.json",
        "private/curator_label_drafts.jsonl",
        "private/overlap_report.json",
    ):
        target = root.joinpath(*relative.split("/"))
        with target.open("xb") as handle:
            handle.write(files[relative])
        if target.read_bytes() != files[relative]:
            raise ValidationSetError(f"local write verification failed: {relative}")
        written.append(relative)
    return written


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build model-free Phase 1.2A validation-set drafts"
    )
    parser.add_argument("--curator-a-pool", required=True)
    parser.add_argument("--curator-a-seal", required=True)
    parser.add_argument("--curator-b-pool", required=True)
    parser.add_argument("--curator-b-seal", required=True)
    parser.add_argument("--selection-plan", required=True)
    parser.add_argument("--curator-c-summary", required=True)
    parser.add_argument("--private-salts", required=True)
    parser.add_argument("--historical-generations", required=True)
    parser.add_argument("--historical-evaluations", required=True)
    parser.add_argument("--output-root", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        validate_external_staging_root(args.output_root)
        for value, name in (
            (args.curator_a_pool, "curator A pool"),
            (args.curator_a_seal, "curator A seal"),
            (args.curator_b_pool, "curator B pool"),
            (args.curator_b_seal, "curator B seal"),
            (args.selection_plan, "selection plan"),
            (args.curator_c_summary, "Curator-C summary"),
            (args.private_salts, "private salts"),
            (args.historical_generations, "historical generations"),
            (args.historical_evaluations, "historical evaluations"),
        ):
            validate_external_private_path(value, name=name)
        production = validation.validate_eligible_production_bundle(
            {
                "curator_a_candidate_jsonl": _read_regular_bytes(
                    args.curator_a_pool, "curator A pool"
                ),
                "curator_a_pool_seal": _read_regular_bytes(
                    args.curator_a_seal, "curator A seal"
                ),
                "curator_b_candidate_jsonl": _read_regular_bytes(
                    args.curator_b_pool, "curator B pool"
                ),
                "curator_b_pool_seal": _read_regular_bytes(
                    args.curator_b_seal, "curator B seal"
                ),
                "curator_c_selection": _read_regular_bytes(
                    args.selection_plan, "selection plan"
                ),
                "curator_c_summary": _read_regular_bytes(
                    args.curator_c_summary, "Curator-C summary"
                ),
            }
        )
        historical_source_bytes = _read_authoritative_historical_bytes(
            args.historical_generations, args.historical_evaluations
        )
        files = build_validation_drafts(
            production["curator_a"],
            production["curator_b"],
            production["curator_a_seal"],
            production["curator_b_seal"],
            production["selection"],
            _read_json(args.private_salts, "private salts"),
            historical_source_bytes,
        )
        written = write_new_output_root(args.output_root, files)
    except Exception:
        print(
            "validation-set build failed; no artifact data emitted",
            file=sys.stderr,
        )
        return 2
    print(
        f"validated model-free drafts: development=60 locked=120 "
        f"files={len(written)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
