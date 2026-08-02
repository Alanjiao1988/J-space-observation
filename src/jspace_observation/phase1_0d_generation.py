"""Phase 1.0D generation driver — the only module here that touches a model.

The frozen rules live in :mod:`jspace_observation.phase1_0d_confirmation` and
are applied by :mod:`jspace_observation.phase1_0d_execution`.  This module adds
the two things those modules deliberately do not have: a real model backend, and
a pack emitter that turns one run into the artifacts the authority requires.

The mode boundary is the point of the design:

``plan``       registers the selection and every rendered prompt.  No model.
``self-test``  runs the whole pipeline against a fabricated backend on CPU.
``generate``   runs the pinned model once and emits **unlabelled** rows.
``finalize``   ingests semantic labels and only then computes cell metrics.

``generate`` never emits a decision object.  Under ``DR-01`` an automatic
evaluator may not decide correctness, so a cell metric cannot exist until a
semantic reviewer has labelled the rows.  A pack that reported a result at
generation time would be reporting the triage router's opinion.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .headroom_calibration import (
    MODEL_ID,
    MODEL_REVISION,
    canonical_json,
    canonical_jsonl,
    load_task_bank,
    sha256_text,
    utc_timestamp,
    write_text,
)
from .phase1_0c_defect_audit import load_phase_1_0c_records
from .phase1_0d_confirmation import (
    ARTIFACT_ROOT,
    AUTHORITY_PROMPT_PATH,
    AUTHORITY_PROMPT_SHA256,
    AUTHORITY_SECTIONS,
    DEFAULT_BANK_PATH,
    PHASE,
    PROTOCOL_CONSEQUENCES,
    PROTOCOL_NOT_ESTABLISHED,
    PROTOCOL_VERSION,
    RUN_BASE_SEED,
    SELECTION_SEED,
    TRACK,
    VISIBLE_CONTROL_ARM,
    Phase1_0DError,
    assert_strict_budget_fits_every_answer,
    generation_config,
    phase_1_0c_item_ids,
    protocol_snapshot,
    select_confirmation_items,
    selection_summary,
)
from .phase1_0d_execution import (
    GenerationOutput,
    SelfTestBackend,
    WorkUnit,
    annotate_review_selection,
    apply_judgments,
    build_decision,
    build_records,
    build_review_form_rows,
    ingest_judgments,
    review_agreement,
)

MODES: tuple[str, ...] = ("plan", "self-test", "generate", "finalize")

#: A generation-only pack carries this instead of a result.
AWAITING_REVIEW = "AWAITING_SEMANTIC_REVIEW"

#: Emitted last, so a truncated upload is detectable rather than plausible.
MANIFEST_NAME = "artifact_manifest.json"


class Phase1_0DRunError(Phase1_0DError):
    """A run could not be executed as registered."""


# --------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------


@dataclass
class GenerationTelemetry:
    """Per-row execution facts that are provenance, not measurement."""

    record_id: str
    backend: str
    prompt_token_count: int | None = None
    output_token_count: int | None = None
    wall_seconds: float | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "backend": self.backend,
            "prompt_token_count": self.prompt_token_count,
            "output_token_count": self.output_token_count,
            "wall_seconds": self.wall_seconds,
            "error": self.error,
        }


class TransformersBackend:
    """The pinned target model.  Imports torch lazily so CPU hosts stay clean.

    No generation-time stop is registered.  The authority permits a stop only
    after a complete registered final-answer surface, and a stop that fires
    mid-surface would silently truncate the model's own output.  Declining to
    stop early always satisfies that rule, and the arm's registered token budget
    remains the only bound.  Nothing is ever clipped after the fact and then
    reported as the model output.
    """

    is_real_model = True
    name = "phase1_0d_transformers_causal_lm_v1"

    def __init__(
        self,
        model_id: str = MODEL_ID,
        revision: str = MODEL_REVISION,
        device: str | None = None,
    ) -> None:
        import torch  # noqa: PLC0415 - deliberately lazy
        from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

        self._torch = torch
        self.model_id = model_id
        self.revision = revision
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        )
        self.model.to(self.device)
        self.model.eval()

    def describe(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "is_real_model": True,
            "model_id": self.model_id,
            "model_revision": self.revision,
            "device": self.device,
        }

    def generate(self, unit: WorkUnit) -> GenerationOutput:
        torch = self._torch
        config = generation_config(unit.arm)
        torch.manual_seed(unit.seed % (2**63 - 1))
        encoded = self.tokenizer(unit.prompt, return_tensors="pt").to(self.device)
        prompt_token_count = int(encoded["input_ids"].shape[-1])
        with torch.no_grad():
            generated = self.model.generate(
                **encoded,
                max_new_tokens=config.max_new_tokens,
                do_sample=config.do_sample,
                temperature=config.temperature,
                top_p=config.top_p,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        new_tokens = generated[0][prompt_token_count:]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        self._last_prompt_token_count = prompt_token_count
        return GenerationOutput(text, int(new_tokens.shape[-1]))


def describe_backend(backend: Any) -> dict[str, Any]:
    """Describe a backend without assuming it implements ``describe``."""

    if hasattr(backend, "describe"):
        return dict(backend.describe())
    return {
        "backend": getattr(backend, "name", type(backend).__name__),
        "is_real_model": bool(getattr(backend, "is_real_model", False)),
    }


def run_generations(
    units: Sequence[WorkUnit],
    backend: Any,
) -> tuple[dict[str, GenerationOutput], list[GenerationTelemetry]]:
    """Execute every unit in frozen order.

    A unit that raises is recorded as an empty output with the error preserved.
    The row still exists, so a failed generation cannot quietly shrink a cell:
    it reaches semantic review and is labelled there like any other row.
    """

    import time  # noqa: PLC0415 - only needed when a run actually executes

    outputs: dict[str, GenerationOutput] = {}
    telemetry: list[GenerationTelemetry] = []
    backend_name = str(describe_backend(backend).get("backend", "unknown"))
    for unit in units:
        started = time.monotonic()
        try:
            output = backend.generate(unit)
            error = None
        except Exception as failure:  # pragma: no cover - hardware/runtime faults
            output = GenerationOutput("", 0)
            error = f"{type(failure).__name__}: {failure}"
        outputs[unit.record_id] = output
        telemetry.append(
            GenerationTelemetry(
                record_id=unit.record_id,
                backend=backend_name,
                prompt_token_count=getattr(backend, "_last_prompt_token_count", None),
                output_token_count=output.output_token_count,
                wall_seconds=round(time.monotonic() - started, 6),
                error=error,
            )
        )
    return outputs, telemetry


# --------------------------------------------------------------------------
# Run configuration and pack emission
# --------------------------------------------------------------------------


@dataclass
class RunConfig:
    """Everything one Phase 1.0D run needs, with nothing inferred at runtime."""

    mode: str
    output_root: Path
    repo_root: Path
    bank_path: Path | None = None
    run_id: str | None = None
    code_commit: str | None = None
    image_digest: str = "not_recorded"
    hardware: str = "not_recorded"
    frozen_time: str | None = None
    records_path: Path | None = None
    judgments_path: Path | None = None
    backend: Any = None
    runtime_environment: Mapping[str, Any] = field(default_factory=dict)

    def resolved_bank_path(self) -> Path:
        return self.bank_path or (self.repo_root / DEFAULT_BANK_PATH)


def runtime_environment() -> dict[str, Any]:
    """Report observed versions so a pack's provenance claims are checkable."""

    environment: dict[str, Any] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    import importlib  # noqa: PLC0415 - keeps the module import-light on CPU hosts

    for module_name in ("torch", "transformers"):
        try:
            module = importlib.import_module(module_name)
            environment[f"{module_name}_version"] = getattr(
                module, "__version__", "unknown"
            )
        except Exception as error:  # pragma: no cover - absent on CPU test hosts
            environment[f"{module_name}_version"] = f"unavailable: {type(error).__name__}"
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


def _load_records(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def selection_and_snapshot(config: RunConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Recompute the frozen selection and protocol from the committed bank."""

    bank = load_task_bank(config.resolved_bank_path())
    used = phase_1_0c_item_ids(load_phase_1_0c_records())
    selected = select_confirmation_items(bank, used)
    snapshot = protocol_snapshot(
        selection=selection_summary(selected, used),
        strict_budget_check=assert_strict_budget_fits_every_answer(selected),
    )
    return selected, snapshot


def _provenance(config: RunConfig, backend: Any, snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authority": {
            "prompt": AUTHORITY_PROMPT_PATH,
            "prompt_sha256": AUTHORITY_PROMPT_SHA256,
            "section": AUTHORITY_SECTIONS,
        },
        "backend": describe_backend(backend) if backend is not None else None,
        "code_commit": config.code_commit or "not_recorded",
        "hardware": config.hardware,
        "image_digest": config.image_digest,
        "mode": config.mode,
        "phase": PHASE,
        "protocol_sha256": snapshot["protocol_sha256"],
        "protocol_version": PROTOCOL_VERSION,
        "runtime_environment": dict(config.runtime_environment),
        "run_base_seed": RUN_BASE_SEED,
        "selection_seed": SELECTION_SEED,
        "track": TRACK,
    }


def _generation_summary(telemetry: Sequence[GenerationTelemetry]) -> dict[str, Any]:
    errors = [item for item in telemetry if item.error]
    durations = [item.wall_seconds for item in telemetry if item.wall_seconds is not None]
    return {
        "generations": len(telemetry),
        "failed_generations": len(errors),
        "failed_record_ids": sorted(item.record_id for item in errors),
        "wall_seconds_total": round(sum(durations), 3) if durations else None,
        "wall_seconds_max": round(max(durations), 3) if durations else None,
    }


def _summary_markdown(
    run_id: str,
    config: RunConfig,
    provenance: Mapping[str, Any],
    generation: Mapping[str, Any] | None,
    decision: Mapping[str, Any] | None,
) -> str:
    lines = [
        f"# Phase {PHASE} confirmation pack {run_id}",
        "",
        f"- mode: `{config.mode}`",
        f"- protocol: `{provenance['protocol_version']}`",
        f"- protocol_sha256: `{provenance['protocol_sha256']}`",
        f"- code_commit: `{provenance['code_commit']}`",
        f"- image_digest: `{provenance['image_digest']}`",
        f"- hardware: `{provenance['hardware']}`",
        "",
    ]
    if generation is not None:
        lines += [
            "## Generation",
            "",
            f"- generations: {generation['generations']}",
            f"- failed generations: {generation['failed_generations']}",
            "",
        ]
    if decision is None:
        lines += [
            "## Result",
            "",
            f"Status `{AWAITING_REVIEW}`. This pack carries **no** cell metric and",
            "**no** headroom result. Every row is unlabelled: under `DR-01` the",
            "automatic triage router may route a row but may never decide whether",
            "it is correct, so no accuracy exists until a semantic reviewer has",
            "labelled the rows through the registered closed form.",
            "",
        ]
    else:
        lines += [
            "## Result",
            "",
            f"- result: `{decision['result']}`",
            f"- cells reported: {decision['cell_count']}",
            f"- RQ2 pilot candidate cells: {len(decision['rq2_pilot_candidates'])}",
            "",
        ]
    lines += ["## What this pack does not establish", ""]
    lines += [f"- {item}" for item in PROTOCOL_NOT_ESTABLISHED]
    lines += ["", "## Consequences fixed before inference", ""]
    lines += [f"- {item}" for item in PROTOCOL_CONSEQUENCES]
    lines.append("")
    return "\n".join(lines)


def _manifest(entries: Mapping[str, str], run_id: str) -> dict[str, Any]:
    return {
        "artifact": "phase1_0d_confirmation_pack",
        "run_id": run_id,
        "artifact_root": ARTIFACT_ROOT,
        "files": [
            {"name": name, "sha256": digest}
            for name, digest in sorted(entries.items())
        ],
        "file_count": len(entries),
        "manifest_written_last": True,
    }


def run_phase1_0d(config: RunConfig) -> dict[str, Any]:
    """Execute one Phase 1.0D run and emit its pack.  Returns a small summary."""

    if config.mode not in MODES:
        raise Phase1_0DRunError(f"unregistered mode {config.mode!r}")
    if config.mode == "generate":
        if not config.code_commit:
            raise Phase1_0DRunError("generate mode requires the code commit")
        if config.image_digest == "not_recorded":
            raise Phase1_0DRunError("generate mode requires the image digest")
        if config.backend is None or not getattr(config.backend, "is_real_model", False):
            raise Phase1_0DRunError(
                "generate mode requires a real model backend; a fabricated "
                "backend may never produce a pack labelled as a generation run"
            )
    if config.mode == "self-test" and getattr(config.backend, "is_real_model", False):
        raise Phase1_0DRunError("self-test mode must not run the real model")

    run_id = config.run_id or utc_timestamp(config.frozen_time)
    output_dir = Path(config.output_root) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    selected, snapshot = selection_and_snapshot(config)
    units = _plan(selected, snapshot)
    question_by_task = {str(item["task_id"]): str(item["question"]) for item in selected}

    backend = config.backend
    if config.mode == "self-test" and backend is None:
        backend = SelfTestBackend()
    provenance = _provenance(config, backend, snapshot)

    entries: dict[str, str] = {}

    def emit(name: str, text: str) -> None:
        entries[name] = write_text(output_dir / name, text)

    emit("00_protocol_snapshot.json", canonical_json(snapshot))
    emit(
        "01_selection.json",
        canonical_json(
            {
                "items": selected,
                "item_count": len(selected),
                "work_unit_count": len(units),
                "prompts": [
                    {
                        "record_id": unit.record_id,
                        "arm_id": unit.arm_id,
                        "prompt_text": unit.prompt,
                        "prompt_sha256": sha256_text(unit.prompt),
                        "max_new_tokens": unit.max_new_tokens,
                    }
                    for unit in units
                ],
                "provenance": provenance,
            }
        ),
    )

    if config.mode == "plan":
        emit("09_summary.md", _summary_markdown(run_id, config, provenance, None, None))
        emit(MANIFEST_NAME, canonical_json(_manifest(entries, run_id)))
        return {
            "mode": config.mode,
            "output_dir": str(output_dir),
            "run_id": run_id,
            "status": "PLAN_ONLY",
            "work_units": len(units),
        }

    if config.mode == "finalize":
        if config.records_path is None or config.judgments_path is None:
            raise Phase1_0DRunError(
                "finalize mode requires prior records and a reviewer judgment file"
            )
        records = _load_records(Path(config.records_path))
        judgments = json.loads(Path(config.judgments_path).read_text(encoding="utf-8"))
        records = ingest_judgments(records, judgments)
        records = annotate_review_selection(records)
        records = apply_judgments(records)
        decision = build_decision(records)
        agreement = review_agreement(records)
        emit("02_records.jsonl", canonical_jsonl(records))
        emit("04_review_agreement.json", canonical_json(agreement))
        emit("05_decision.json", canonical_json({**decision, "provenance": provenance}))
        emit(
            "09_summary.md",
            _summary_markdown(run_id, config, provenance, None, decision),
        )
        emit(MANIFEST_NAME, canonical_json(_manifest(entries, run_id)))
        return {
            "mode": config.mode,
            "output_dir": str(output_dir),
            "records": len(records),
            "result": decision["result"],
            "run_id": run_id,
            "rq2_pilot_candidates": decision["rq2_pilot_candidates"],
        }

    outputs, telemetry = run_generations(units, backend)
    records = build_records(units, outputs)
    generation = _generation_summary(telemetry)
    questions = {
        unit.record_id: question_by_task[unit.task_id] for unit in units
    }

    emit("02_records.jsonl", canonical_jsonl(records))
    emit("03_review_form.jsonl", canonical_jsonl(build_review_form_rows(records, questions)))
    emit(
        "04_generation_summary.json",
        canonical_json(
            {
                **generation,
                "telemetry": [item.as_dict() for item in telemetry],
                "provenance": provenance,
            }
        ),
    )
    emit(
        "05_decision.json",
        canonical_json(
            {
                "result": AWAITING_REVIEW,
                "reason": (
                    "no row carries a semantic label, so no cell metric exists; "
                    "DR-01 forbids the automatic triage router from deciding "
                    "correctness"
                ),
                "rows_awaiting_primary_review": len(records),
                "provenance": provenance,
            }
        ),
    )
    emit(
        "09_summary.md",
        _summary_markdown(run_id, config, provenance, generation, None),
    )
    emit(MANIFEST_NAME, canonical_json(_manifest(entries, run_id)))
    return {
        "generations": generation["generations"],
        "failed_generations": generation["failed_generations"],
        "mode": config.mode,
        "output_dir": str(output_dir),
        "records": len(records),
        "run_id": run_id,
        "status": AWAITING_REVIEW,
    }


def _plan(selected: Sequence[Mapping[str, Any]], snapshot: Mapping[str, Any]) -> list[WorkUnit]:
    from .phase1_0d_execution import plan_work_units  # noqa: PLC0415 - avoids a cycle

    units = plan_work_units(selected, base_seed=RUN_BASE_SEED)
    expected = len(selected) * len(snapshot["arms"])
    if len(units) != expected:
        raise Phase1_0DRunError(
            f"planned {len(units)} work units for {len(selected)} items; "
            f"the frozen design requires {expected}"
        )
    visible = [unit for unit in units if unit.arm_id == VISIBLE_CONTROL_ARM.arm_id]
    if len(visible) != len(selected):
        raise Phase1_0DRunError("every item must carry exactly one visible control")
    return units


def main(argv: Sequence[str] | None = None) -> int:
    """Container entrypoint.  Kept here so the script file stays a thin shim."""

    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        description=(
            "Run Phase 1.0D headroom confirmation. This is task calibration "
            "only; it licenses no claim about hidden reasoning, internal "
            "representations, or a 'J-space'."
        )
    )
    parser.add_argument("--mode", choices=list(MODES), default="plan")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--bank", type=Path, default=None)
    parser.add_argument("--run-id", default=os.environ.get("JSPACE_CONFIRMATION_RUN_ID"))
    parser.add_argument("--code-commit", default=os.environ.get("JSPACE_CODE_COMMIT"))
    parser.add_argument(
        "--image-digest", default=os.environ.get("JSPACE_IMAGE_DIGEST", "not_recorded")
    )
    parser.add_argument(
        "--hardware", default=os.environ.get("JSPACE_HARDWARE", "not_recorded")
    )
    parser.add_argument("--frozen-time", default=os.environ.get("JSPACE_FROZEN_TIME"))
    parser.add_argument("--records", type=Path, default=None)
    parser.add_argument("--judgments", type=Path, default=None)
    parser.add_argument("--upload-blob", action="store_true")
    parser.add_argument("--blob-prefix", default=None)
    arguments = parser.parse_args(list(argv) if argv is not None else None)

    environment = runtime_environment()
    print(json.dumps({"runtime_environment": environment}, sort_keys=True))

    backend = None
    if arguments.mode == "generate":
        backend = TransformersBackend()
    elif arguments.mode == "self-test":
        backend = SelfTestBackend()

    config = RunConfig(
        mode=arguments.mode,
        output_root=arguments.output_root,
        repo_root=arguments.repo_root,
        bank_path=arguments.bank,
        run_id=arguments.run_id,
        code_commit=arguments.code_commit,
        image_digest=arguments.image_digest,
        hardware=arguments.hardware,
        frozen_time=arguments.frozen_time,
        records_path=arguments.records,
        judgments_path=arguments.judgments,
        backend=backend,
        runtime_environment=environment,
    )
    result = run_phase1_0d(config)

    if arguments.upload_blob:
        from .headroom_blob_transport import upload_pack  # noqa: PLC0415

        result["upload"] = upload_pack(
            Path(result["output_dir"]),
            str(result["run_id"]),
            prefix=arguments.blob_prefix,
            require=True,
        )

    print(json.dumps(result, default=str, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - container entrypoint
    sys.exit(main())
