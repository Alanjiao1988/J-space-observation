"""Independent v2 recomputation from generations and sealed judgments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..headroom_calibration import load_task_bank
from ..phase1_0c_defect_audit import (
    PHASE_1_0C_RECORDS_PATH,
    load_phase_1_0c_records,
)
from ..phase1_0d_confirmation import (
    ARTIFACT_ROOT,
    AUTHORITY_PROMPT_PATH,
    AUTHORITY_PROMPT_SHA256,
    AUTHORITY_SECTIONS,
    DEFAULT_BANK_PATH,
    PHASE,
    PROTOCOL_VERSION,
    RUN_BASE_SEED,
    SELECTION_SEED,
    TRACK,
    assert_strict_budget_fits_every_answer,
    phase_1_0c_item_ids,
    protocol_snapshot,
    select_confirmation_items,
    selection_summary,
)
from ..phase1_0d_execution import (
    GenerationOutput,
    annotate_review_selection,
    apply_judgments,
    build_decision,
    build_records,
    build_review_form_rows,
    ingest_judgments,
    plan_work_units,
)
from ..semantic_review.addendum import canonical_json, sha256_text
from ..semantic_review import stages

GENERATION_CODE_COMMIT = "9cde1d95ffda36698a0ddf558a9358f3337dd711"
GENERATION_HARDWARE = (
    "Azure Container Apps gpu-t4 workload profile, NVIDIA Tesla T4"
)
FINALIZATION_HARDWARE = (
    "Azure Container Apps Consumption workload profile, CPU only"
)
EXPECTED_SOURCE_FILES = (
    "00_protocol_snapshot.json",
    "01_selection.json",
    "02_records.jsonl",
    "03_review_form.jsonl",
    "04_generation_summary.json",
    "05_decision.json",
    "09_summary.md",
)


class IndependentVerificationError(RuntimeError):
    """The finalized pack differs from an independent frozen recomputation."""


def _read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise IndependentVerificationError(f"{path.name} is not a JSON object")
    return document


def _expected_selection(project_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bank = load_task_bank(project_root / DEFAULT_BANK_PATH)
    prior = load_phase_1_0c_records(project_root / PHASE_1_0C_RECORDS_PATH)
    used = phase_1_0c_item_ids(prior)
    selected = select_confirmation_items(bank, used)
    snapshot = protocol_snapshot(
        selection=selection_summary(selected, used),
        strict_budget_check=assert_strict_budget_fits_every_answer(selected),
    )
    return selected, snapshot


def _validate_generation_provenance(
    provenance: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> None:
    expected = {
        "authority": {
            "prompt": AUTHORITY_PROMPT_PATH,
            "prompt_sha256": AUTHORITY_PROMPT_SHA256,
            "section": AUTHORITY_SECTIONS,
        },
        "backend": {
            "backend": "phase1_0d_transformers_causal_lm_v1",
            "is_real_model": True,
            "model_id": stages.MODEL_ID,
            "model_revision": stages.MODEL_REVISION,
            "device": "cuda",
        },
        "code_commit": GENERATION_CODE_COMMIT,
        "hardware": GENERATION_HARDWARE,
        "image_digest": stages.GENERATION_IMAGE_DIGEST,
        "mode": "generate",
        "phase": PHASE,
        "protocol_sha256": snapshot["protocol_sha256"],
        "protocol_version": PROTOCOL_VERSION,
        "run_base_seed": RUN_BASE_SEED,
        "selection_seed": SELECTION_SEED,
        "track": TRACK,
    }
    expected_keys = set(expected) | {"runtime_environment"}
    if set(provenance) != expected_keys:
        raise IndependentVerificationError(
            "generation provenance fields differ from the frozen generator"
        )
    for key, value in expected.items():
        if canonical_json(provenance.get(key)) != canonical_json(value):
            raise IndependentVerificationError(
                f"generation provenance moved frozen field {key}"
            )
    runtime = provenance.get("runtime_environment")
    if (
        not isinstance(runtime, Mapping)
        or runtime.get("cuda_available") is not True
        or "T4" not in str(runtime.get("cuda_device_name", ""))
    ):
        raise IndependentVerificationError(
            "generation provenance does not describe the registered CUDA T4 runtime"
        )


def verify_source_pack(
    *,
    pack_dir: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Rebuild the frozen selection, work units and immutable record metadata."""

    base = stages.verify_generation_pack(pack_dir)
    manifest = _read_json(pack_dir / stages.MANIFEST_NAME)
    entries = manifest.get("files")
    names = [
        str(entry.get("name"))
        for entry in entries
        if isinstance(entry, Mapping)
    ] if isinstance(entries, list) else []
    if (
        names != list(EXPECTED_SOURCE_FILES)
        or manifest.get("file_count") != len(EXPECTED_SOURCE_FILES)
        or manifest.get("artifact") != "phase1_0d_confirmation_pack"
        or manifest.get("artifact_root") != ARTIFACT_ROOT
        or manifest.get("manifest_written_last") is not True
    ):
        raise IndependentVerificationError(
            "generation manifest is not the exact frozen seven-file pack"
        )
    actual_files = sorted(
        path.relative_to(pack_dir).as_posix()
        for path in pack_dir.rglob("*")
        if path.is_file()
    )
    if actual_files != sorted((*EXPECTED_SOURCE_FILES, stages.MANIFEST_NAME)):
        raise IndependentVerificationError(
            "generation pack contains missing, extra or nested files"
        )

    selected, expected_snapshot = _expected_selection(project_root)
    observed_snapshot = _read_json(pack_dir / "00_protocol_snapshot.json")
    if canonical_json(observed_snapshot) != canonical_json(expected_snapshot):
        raise IndependentVerificationError(
            "protocol snapshot differs from a clean frozen recomputation"
        )

    units = plan_work_units(selected, base_seed=RUN_BASE_SEED)
    expected_prompts = [
        {
            "record_id": unit.record_id,
            "arm_id": unit.arm_id,
            "prompt_text": unit.prompt,
            "prompt_sha256": sha256_text(unit.prompt),
            "max_new_tokens": unit.max_new_tokens,
        }
        for unit in units
    ]
    selection = _read_json(pack_dir / "01_selection.json")
    if set(selection) != {
        "items",
        "item_count",
        "work_unit_count",
        "prompts",
        "provenance",
    }:
        raise IndependentVerificationError(
            "selection object fields differ from the frozen generator"
        )
    if canonical_json(selection.get("items")) != canonical_json(selected):
        raise IndependentVerificationError(
            "selected items differ from the committed deterministic selection"
        )
    if (
        selection.get("item_count") != len(selected)
        or selection.get("work_unit_count") != len(units)
        or canonical_json(selection.get("prompts")) != canonical_json(expected_prompts)
    ):
        raise IndependentVerificationError(
            "work units or prompts differ from the frozen plan"
        )
    provenance = selection.get("provenance")
    if not isinstance(provenance, Mapping):
        raise IndependentVerificationError("selection carries no generation provenance")
    _validate_generation_provenance(provenance, expected_snapshot)

    records = stages.load_records(pack_dir / "02_records.jsonl")
    expected_ids = [unit.record_id for unit in units]
    if [str(row.get("record_id")) for row in records] != expected_ids:
        raise IndependentVerificationError(
            "generation records do not follow the exact frozen work-unit order"
        )
    outputs: dict[str, GenerationOutput] = {}
    for unit, row in zip(units, records, strict=True):
        record_provenance = row.get("provenance")
        if not isinstance(record_provenance, Mapping):
            raise IndependentVerificationError(
                f"{unit.record_id} carries no record provenance"
            )
        token_count = record_provenance.get("output_token_count")
        output_text = row.get("output_text")
        if (
            type(token_count) is not int
            or token_count < 0
            or token_count > unit.max_new_tokens
            or not isinstance(output_text, str)
        ):
            raise IndependentVerificationError(
                f"{unit.record_id} carries an invalid generation output"
            )
        outputs[unit.record_id] = GenerationOutput(output_text, token_count)
    rebuilt_records = build_records(units, outputs)
    if canonical_json(records) != canonical_json(rebuilt_records):
        raise IndependentVerificationError(
            "record metadata, triage, compliance or empty-label state differs "
            "from the frozen work units"
        )

    question_by_task = {
        str(item["task_id"]): str(item["question"]) for item in selected
    }
    expected_form = build_review_form_rows(
        rebuilt_records,
        {
            unit.record_id: question_by_task[unit.task_id]
            for unit in units
        },
    )
    form = stages.load_records(pack_dir / "03_review_form.jsonl")
    if canonical_json(form) != canonical_json(expected_form):
        raise IndependentVerificationError(
            "review form differs from the frozen records and questions"
        )

    generation = _read_json(pack_dir / "04_generation_summary.json")
    if set(generation) != {
        "generations",
        "failed_generations",
        "failed_record_ids",
        "wall_seconds_total",
        "wall_seconds_max",
        "telemetry",
        "provenance",
    }:
        raise IndependentVerificationError(
            "generation summary fields differ from the frozen emitter"
        )
    if canonical_json(generation.get("provenance")) != canonical_json(provenance):
        raise IndependentVerificationError(
            "generation summary provenance differs from selection provenance"
        )
    telemetry = generation.get("telemetry")
    if not isinstance(telemetry, list) or len(telemetry) != len(units):
        raise IndependentVerificationError("generation telemetry does not cover 900 rows")
    failures: list[str] = []
    durations: list[float] = []
    for unit, row, item in zip(units, records, telemetry, strict=True):
        if not isinstance(item, Mapping) or set(item) != {
            "record_id",
            "backend",
            "prompt_token_count",
            "output_token_count",
            "wall_seconds",
            "error",
        }:
            raise IndependentVerificationError(
                f"{unit.record_id} has malformed generation telemetry"
            )
        duration = item.get("wall_seconds")
        if (
            item.get("record_id") != unit.record_id
            or item.get("backend") != "phase1_0d_transformers_causal_lm_v1"
            or type(item.get("prompt_token_count")) is not int
            or int(item["prompt_token_count"]) <= 0
            or item.get("output_token_count")
            != row["provenance"]["output_token_count"]
            or isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or duration < 0
            or (
                item.get("error") is not None
                and not isinstance(item.get("error"), str)
            )
        ):
            raise IndependentVerificationError(
                f"{unit.record_id} telemetry differs from its frozen work unit"
            )
        durations.append(float(duration))
        if item.get("error") is not None:
            failures.append(unit.record_id)
            if row["output_text"] != "" or row["provenance"]["output_token_count"] != 0:
                raise IndependentVerificationError(
                    f"{unit.record_id} failed but was not retained as an empty row"
                )
    if (
        generation.get("generations") != len(units)
        or generation.get("failed_generations") != len(failures)
        or generation.get("failed_record_ids") != sorted(failures)
        or generation.get("wall_seconds_total") != round(sum(durations), 3)
        or generation.get("wall_seconds_max") != round(max(durations), 3)
    ):
        raise IndependentVerificationError(
            "generation aggregate does not recompute from per-row telemetry"
        )

    decision = _read_json(pack_dir / "05_decision.json")
    expected_decision = {
        "result": stages.AWAITING_REVIEW,
        "reason": (
            "no row carries a semantic label, so no cell metric exists; "
            "DR-01 forbids the automatic triage router from deciding correctness"
        ),
        "rows_awaiting_primary_review": len(units),
        "provenance": provenance,
    }
    if canonical_json(decision) != canonical_json(expected_decision):
        raise IndependentVerificationError(
            "generation decision is not the exact metric-free awaiting-review object"
        )

    return {
        **base,
        "exact_manifest_file_set": True,
        "selection_recomputed": True,
        "work_units_recomputed": len(units),
        "records_rebuilt": len(rebuilt_records),
        "review_form_rebuilt": len(expected_form),
        "generation_aggregates_recomputed": True,
    }


def _expected_final_provenance(
    code_commit: str,
    image_digest: str,
) -> dict[str, Any]:
    return {
        "authority": {
            "prompt": AUTHORITY_PROMPT_PATH,
            "prompt_sha256": AUTHORITY_PROMPT_SHA256,
            "section": AUTHORITY_SECTIONS,
        },
        "backend": None,
        "code_commit": code_commit,
        "hardware": FINALIZATION_HARDWARE,
        "image_digest": image_digest,
        "mode": "finalize",
        "phase": PHASE,
        "protocol_sha256": stages.FROZEN_PROTOCOL_SHA256,
        "protocol_version": PROTOCOL_VERSION,
        "runtime_environment": {},
        "run_base_seed": RUN_BASE_SEED,
        "selection_seed": SELECTION_SEED,
        "track": TRACK,
    }


def _counts(values: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def verify_final_result(
    *,
    source_records: Sequence[Mapping[str, Any]],
    finalized_records: Sequence[Mapping[str, Any]],
    decision: Mapping[str, Any],
    combined: Sequence[Mapping[str, Any]],
    required_secondary: Sequence[str],
    required_third: Sequence[str],
    expected_code_commit: str,
    expected_image_digest: str,
) -> dict[str, Any]:
    """Rebuild labels, cell metrics, gates, candidates and decision from inputs."""

    failures: list[str] = []
    source_ids = [str(row["record_id"]) for row in source_records]
    if len(source_ids) != len(set(source_ids)):
        failures.append("source records contain duplicate record IDs")

    by_role: dict[str, dict[str, str]] = {
        "primary": {},
        "secondary": {},
        "third": {},
    }
    for item in combined:
        role = str(item.get("role"))
        record_id = str(item.get("record_id"))
        if role not in by_role:
            failures.append(f"judgment has an unknown role: {role}")
            continue
        if record_id in by_role[role]:
            failures.append(f"duplicate {role} judgment for {record_id}")
            continue
        by_role[role][record_id] = str(item.get("label"))

    expected_coverage = {
        "primary": set(source_ids),
        "secondary": set(str(value) for value in required_secondary),
        "third": set(str(value) for value in required_third),
    }
    for role, expected in expected_coverage.items():
        actual = set(by_role[role])
        if actual != expected:
            failures.append(f"{role} judgments differ from the registered coverage")
    if failures:
        raise IndependentVerificationError("; ".join(failures))

    ingested = ingest_judgments(source_records, combined)
    selected = annotate_review_selection(ingested)
    recomputed_secondary = sorted(
        str(row["record_id"])
        for row in selected
        if row["evaluation"]["secondary_review_required"]
    )
    if recomputed_secondary != sorted(str(value) for value in required_secondary):
        raise IndependentVerificationError(
            "secondary selection differs from independent recomputation"
        )

    recomputed_third = sorted(
        record_id
        for record_id, secondary_label in by_role["secondary"].items()
        if by_role["primary"][record_id] != secondary_label
    )
    if recomputed_third != sorted(str(value) for value in required_third):
        raise IndependentVerificationError(
            "third-review disagreements differ from independent recomputation"
        )

    recomputed_records = apply_judgments(selected)
    pending = [
        str(row["record_id"])
        for row in recomputed_records
        if row["evaluation"].get("arbitration_pending") is True
    ]
    if pending:
        raise IndependentVerificationError(
            f"{len(pending)} rows remain pending after registered arbitration"
        )
    if canonical_json(list(finalized_records)) != canonical_json(recomputed_records):
        raise IndependentVerificationError(
            "finalized records differ from independent judgment ingestion and arbitration"
        )

    recomputed_decision = build_decision(recomputed_records)
    observed_decision = dict(decision)
    provenance = observed_decision.pop("provenance", None)
    expected_provenance = _expected_final_provenance(
        expected_code_commit,
        expected_image_digest,
    )
    if (
        not isinstance(provenance, Mapping)
        or canonical_json(provenance) != canonical_json(expected_provenance)
    ):
        raise IndependentVerificationError(
            "final decision provenance differs from the exact review execution binding"
        )
    if canonical_json(observed_decision) != canonical_json(recomputed_decision):
        raise IndependentVerificationError(
            "final decision differs from independent metric and gate recomputation"
        )

    labels = [
        str(row["evaluation"]["final_label"]) for row in recomputed_records
    ]
    return {
        "records": len(recomputed_records),
        "final_label_counts": _counts(labels),
        "cell_count": recomputed_decision["cell_count"],
        "cells_sha256": sha256_text(
            canonical_json({"cells": recomputed_decision["cells"]})
        ),
        "decision_result": recomputed_decision["result"],
        "rq2_pilot_candidates": recomputed_decision["rq2_pilot_candidates"],
        "rq2_pilot_candidate_count": len(
            recomputed_decision["rq2_pilot_candidates"]
        ),
        "records_sha256": sha256_text(canonical_json(recomputed_records)),
        "judgments_sha256": sha256_text(canonical_json(list(combined))),
        "decision_sha256": sha256_text(canonical_json(dict(decision))),
        "provenance_sha256": sha256_text(canonical_json(provenance)),
        "recomputed_decision_sha256": sha256_text(
            canonical_json(recomputed_decision)
        ),
        "recomputed_only": True,
        "changed_nothing": True,
    }
