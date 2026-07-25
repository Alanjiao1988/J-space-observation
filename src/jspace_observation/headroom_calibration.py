"""Phase 1.0C Track B bounded capability/headroom calibration.

This module screens the frozen Phase 1 task bank for cells where the target
model has measurable headroom.  It is *task calibration only*.  Nothing in this
module measures, detects, or licenses any claim about hidden reasoning, an
internal workspace, invisible chain-of-thought, or "J-space".  The observable
unit of analysis is the emitted output text and its adjudicated correctness.

Parser v2 is called strictly as a read-only screening tool.  Its formal locked
validation failed on 2026-07-25 (``boxed_final_miss`` 1/20, ``wrong_span``
2/80), therefore it never decides a final calibration label here; a semantic
reviewer adjudicates every row that can influence a selected headroom cell.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence

from .eval_parsing_v2 import (
    PARSER_VERSION as PARSER_V2_VERSION,
    compare_parsed_answer_to_reference,
    parse_v2,
)
from .headroom_candidates import (
    DIFFICULTY_BANDS,
    ITEMS_PER_CELL,
    TASK_FAMILIES,
    candidate_bank_sha256,
    derive_run_seed,
)
from .no_cot import (
    ConditionGenerationConfig,
    construct_r1_style_thinking_prompt,
    construct_visible_cot_prompt,
    validate_phase1_conditions,
)

_WILSON_IMPL: Any = None
_WILSON_IMPL_LOADED = False


def _load_repo_wilson() -> Any:
    """Load the repository Wilson helper lazily (it pulls in numpy and scipy)."""

    global _WILSON_IMPL, _WILSON_IMPL_LOADED
    if not _WILSON_IMPL_LOADED:
        _WILSON_IMPL_LOADED = True
        try:
            from .stats import wilson_ci as repo_wilson_ci

            _WILSON_IMPL = repo_wilson_ci
        except Exception:  # pragma: no cover - stdlib fallback path
            _WILSON_IMPL = None
    return _WILSON_IMPL


# --------------------------------------------------------------------------
# Frozen protocol constants
# --------------------------------------------------------------------------

SCHEMA_VERSION = "phase1-headroom-calibration-v1"
PROTOCOL_VERSION = "phase1-headroom-calibration-protocol-v1"
PHASE = "1.0C"
TRACK = "track-b"

MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
MODEL_REVISION = "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"

CONDITIONS: tuple[str, ...] = ("r1_style_thinking", "visible_cot")
DEFERRED_CONDITIONS: tuple[str, ...] = (
    "answer_prefill",
    "empty_think_prefill",
    "postprocessed",
    "prompt_only_raw_strict",
    "stopped",
)

MAX_NEW_TOKENS = 512
TEMPERATURE = 0.6
TOP_P = 0.95
DO_SAMPLE = True
DECODING_PROFILE = "official_style"
SAMPLES_PER_ITEM = 1
REPLICATE_INDEX = 0

SELECTION_SPLIT = "calibration"
SELECTION_SEED = 20260725
RUN_BASE_SEED = 20260725
EXPECTED_ITEM_COUNT = len(TASK_FAMILIES) * len(DIFFICULTY_BANDS) * ITEMS_PER_CELL
EXPECTED_GENERATION_COUNT = EXPECTED_ITEM_COUNT * len(CONDITIONS)

ACCURACY_BAND_LOW = 0.70
ACCURACY_BAND_HIGH = 0.90
MIN_CORRECT_COUNT = 7
MAX_TRUNCATION_RATE = 0.10
MAX_NO_ANSWER_RATE = 0.10
REQUIRED_CELL_N = ITEMS_PER_CELL

REVIEW_SAMPLE_FRACTION = 0.10
PROVISIONAL_REVIEW_MIN_CORRECT = 6
REVIEW_SAMPLE_DOMAIN = "jspace-headroom-calibration/review-sample/v1"

DEFAULT_BANK_PATH = "data/phase1_task_headroom_candidates.jsonl"
REPO_ROOT = Path(__file__).resolve().parents[2]

MODES: tuple[str, ...] = ("plan", "generate", "finalize", "self-test")

ARTIFACT_FILES: tuple[str, ...] = (
    "00_stage_manifest.json",
    "01_protocol_snapshot.json",
    "02_records.jsonl",
    "03_metrics.csv",
    "04_decision.json",
    "05_summary.md",
    "06_paper_table.csv",
    "07_figure_data.csv",
    "08_deviations.json",
    "artifact_manifest.json",
)

METRICS_HEADER: tuple[str, ...] = (
    "run_id",
    "phase",
    "track",
    "metric",
    "stratum",
    "condition",
    "n",
    "numerator",
    "denominator",
    "value",
    "ci_lower",
    "ci_upper",
    "threshold",
    "passed",
    "not_applicable_reason",
)

SELECTED_CELL_HEADER: tuple[str, ...] = (
    "run_id",
    "cell_id",
    "task_family",
    "difficulty_band",
    "condition",
    "n",
    "correct",
    "accuracy",
    "ci_lower",
    "ci_upper",
    "truncation_rate",
    "no_answer_rate",
    "unresolved_labels",
    "review_coverage_complete",
    "classification",
)

EXCLUDED_CELL_HEADER: tuple[str, ...] = SELECTED_CELL_HEADER + (
    "exclusion_reasons",
)

PAPER_TABLE_HEADER: tuple[str, ...] = (
    "run_id",
    "task_family",
    "difficulty_band",
    "condition",
    "n",
    "correct",
    "accuracy",
    "ci_lower",
    "ci_upper",
    "truncation_rate",
    "no_answer_rate",
    "classification",
)

FIGURE_DATA_HEADER: tuple[str, ...] = (
    "run_id",
    "series",
    "x",
    "y",
    "y_lower",
    "y_upper",
    "n",
    "annotation",
)

EXCLUSION_REASON_CODES: tuple[str, ...] = (
    "accuracy_above_band_control_only",
    "accuracy_below_band_difficulty_boundary",
    "incomplete_cell_n",
    "incomplete_review_coverage",
    "insufficient_correct_count",
    "labels_not_semantically_adjudicated",
    "no_answer_rate_above_threshold",
    "truncation_rate_above_threshold",
    "unresolved_semantic_labels_present",
)

CLASSIFICATIONS: tuple[str, ...] = (
    "control_sanity_high_accuracy",
    "difficulty_boundary_excluded",
    "excluded_quality_gate",
    "not_adjudicated",
    "selected_headroom",
)

# Track B outcome vocabulary. This is a reporting view over the already-frozen
# cell classifications; it adds no rule and changes no threshold. The frozen
# pack `status` vocabulary (BLOCKED / INCONCLUSIVE / COMPLETE / FAIL) is
# unchanged and is emitted alongside it.
TRACK_B_DECISIONS: tuple[str, ...] = (
    "CONTROLS_ONLY",
    "HEADROOM_CELLS_SELECTED",
    "INCONCLUSIVE",
    "NO_USABLE_CELLS",
)

REVIEW_REASON_CODES: tuple[str, ...] = (
    "ambiguous_parse",
    "deterministic_random_sample",
    "no_answer",
    "parse_invalid",
    "provisional_headroom_cell",
    "triage_disagrees_with_registered_answer",
    "truncated_output",
)

PROHIBITED_INTERPRETATIONS: tuple[str, ...] = (
    "Any claim that this run observes, measures, or bounds hidden reasoning.",
    "Any claim about an internal workspace, latent scratchpad, or invisible chain-of-thought.",
    "Any claim about 'J-space' existence, structure, capacity, or dynamics.",
    "Any RQ1 or RQ2 result claim; this is task calibration, not a formal result.",
    "Any pass@k or sampling-capability claim; one sample per item/condition is drawn.",
    "Any claim that parser v2 output is a validated correctness label.",
    "Any generalisation to conditions deferred this round.",
)

SCIENTIFIC_CLAIM_BOUNDARY = (
    "This run estimates observable answer accuracy of a single target model on a "
    "frozen task bank under two visible-reasoning prompt conditions, for the sole "
    "purpose of selecting task cells with measurable headroom. It licenses no claim "
    "about hidden reasoning, internal representations, or 'J-space', and it is not a "
    "formal RQ1/RQ2 result."
)

# The frozen bank questions end with strict "answer only" closings. Visible-CoT
# conditions contradict that closing, so a registered override suffix is appended
# instead of mutating the frozen bank text.
PROMPT_OVERRIDE_ID = "prompt_override_v1"
PROMPT_OVERRIDE_TEXT = (
    "\n\nFormat override for this run (supersedes any earlier instruction in this "
    "prompt that tells you not to explain or to answer only): you may reason first, "
    "then end your reply with a single final line in exactly this form:\n"
    "Final answer: <answer>"
)

class HeadroomCalibrationError(ValueError):
    """Raised when a calibration input or invariant violates the protocol."""


# --------------------------------------------------------------------------
# Deterministic primitives
# --------------------------------------------------------------------------


def canonical_json(payload: Any) -> str:
    """Serialize a payload as stable UTF-8 JSON with sorted keys."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def canonical_jsonl(rows: Sequence[Mapping[str, Any]]) -> str:
    """Serialize rows as stable UTF-8 JSON Lines."""

    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in rows
    )


def canonical_csv(
    header: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> str:
    """Serialize rows as a stable LF-terminated CSV document."""

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(list(header))
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return buffer.getvalue()


def write_text(path: Path, text: str) -> str:
    """Write UTF-8 text with LF newlines and return its SHA256."""

    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    with open(path, "wb") as handle:
        handle.write(data)
    return sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """Return the SHA256 hex digest of UTF-8 encoded text."""

    return sha256(text.encode("utf-8")).hexdigest()


def wilson_ci(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """Return a Wilson score interval, falling back to a stdlib implementation."""

    if total <= 0:
        return 0.0, 0.0
    repo_impl = _load_repo_wilson()
    if repo_impl is not None:  # pragma: no branch - trivial delegation
        lower, upper = repo_impl(successes, total, confidence)
        return float(lower), float(upper)
    if abs(confidence - 0.95) > 1e-9:  # pragma: no cover - only 95% is registered
        raise HeadroomCalibrationError(
            "fallback Wilson interval supports only confidence=0.95"
        )
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1.0 + z * z / total
    centre = proportion + z * z / (2.0 * total)
    spread = math.sqrt(
        proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total)
    )
    lower = (centre - z * spread) / denominator
    upper = (centre + z * spread) / denominator
    return max(0.0, lower), min(1.0, upper)


def _round6(value: float) -> float:
    return float(f"{value:.6f}")


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return _round6(numerator / denominator)


def utc_timestamp(frozen_time: str | None = None) -> str:
    """Return an ISO-8601 UTC timestamp, honouring an injected frozen clock."""

    if frozen_time:
        return frozen_time
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# Task bank loading and deterministic selection
# --------------------------------------------------------------------------


def load_task_bank(path: str | Path) -> list[dict[str, Any]]:
    """Load the frozen candidate bank as a list of records."""

    bank_path = Path(path)
    if not bank_path.is_file():
        raise HeadroomCalibrationError(f"task bank not found: {bank_path}")
    records: list[dict[str, Any]] = []
    with open(bank_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as error:  # pragma: no cover - corrupt input
                raise HeadroomCalibrationError(
                    f"invalid JSON in task bank at line {line_number}: {error}"
                ) from error
    if not records:
        raise HeadroomCalibrationError(f"task bank is empty: {bank_path}")
    return records


def select_calibration_items(
    records: Sequence[Mapping[str, Any]],
    *,
    split: str = SELECTION_SPLIT,
    items_per_cell: int = ITEMS_PER_CELL,
) -> list[dict[str, Any]]:
    """Select the frozen 5 x 3 x 10 calibration sample deterministically.

    The candidate-bank protocol forbids item-level filtering and requires whole
    cells, and the confirmation/mechanistic splits must stay held out.  The
    ``calibration`` split therefore *is* the registered sample: exactly
    ``items_per_cell`` items for each of the five families and three bands.
    Selection is a total order over ``task_id`` so it is reproducible without a
    random number generator; ``SELECTION_SEED`` is still recorded and used for
    downstream deterministic sampling.
    """

    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        if record.get("split") != split:
            continue
        family = record.get("task_family")
        band = record.get("difficulty_band")
        if family not in TASK_FAMILIES or band not in DIFFICULTY_BANDS:
            continue
        by_cell.setdefault((str(family), str(band)), []).append(dict(record))

    selected: list[dict[str, Any]] = []
    for family in TASK_FAMILIES:
        for band in DIFFICULTY_BANDS:
            cell = sorted(
                by_cell.get((family, band), []),
                key=lambda item: str(item["task_id"]),
            )
            if len(cell) != items_per_cell:
                raise HeadroomCalibrationError(
                    "cell "
                    f"{family}/{band}/{split} has {len(cell)} items; "
                    f"expected exactly {items_per_cell}"
                )
            selected.extend(cell)

    expected = len(TASK_FAMILIES) * len(DIFFICULTY_BANDS) * items_per_cell
    if len(selected) != expected:
        raise HeadroomCalibrationError(
            f"selected {len(selected)} items; expected {expected}"
        )
    task_ids = [str(item["task_id"]) for item in selected]
    if len(set(task_ids)) != len(task_ids):
        raise HeadroomCalibrationError("selected items are not unique")
    return selected


def selection_summary(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize a selection by family, band, and family x band."""

    per_family: dict[str, int] = {family: 0 for family in TASK_FAMILIES}
    per_band: dict[str, int] = {band: 0 for band in DIFFICULTY_BANDS}
    per_cell: dict[str, int] = {}
    for item in items:
        family = str(item["task_family"])
        band = str(item["difficulty_band"])
        per_family[family] = per_family.get(family, 0) + 1
        per_band[band] = per_band.get(band, 0) + 1
        key = f"{family}|{band}"
        per_cell[key] = per_cell.get(key, 0) + 1
    task_ids = sorted(str(item["task_id"]) for item in items)
    return {
        "item_count": len(task_ids),
        "per_family": dict(sorted(per_family.items())),
        "per_band": dict(sorted(per_band.items())),
        "per_family_band": dict(sorted(per_cell.items())),
        "selection_seed": SELECTION_SEED,
        "split": SELECTION_SPLIT,
        "task_ids": task_ids,
        "task_ids_sha256": sha256_text("\n".join(task_ids) + "\n"),
    }


# --------------------------------------------------------------------------
# Condition construction
# --------------------------------------------------------------------------


def generation_config(condition: str) -> ConditionGenerationConfig:
    """Return the frozen calibration decoding profile for a condition."""

    validate_phase1_conditions((condition,))
    if condition not in CONDITIONS:
        raise HeadroomCalibrationError(
            f"condition {condition!r} is not enabled for this calibration round"
        )
    return ConditionGenerationConfig(
        max_new_tokens=MAX_NEW_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        do_sample=DO_SAMPLE,
        decoding_profile=DECODING_PROFILE,
    )


def build_condition_prompt(question: str, condition: str) -> str:
    """Build the registered prompt for a calibration condition.

    The frozen bank text is never mutated; a registered override suffix is
    appended so the visible-reasoning conditions are not contradicted by the
    bank's strict "answer only" closing.
    """

    validate_phase1_conditions((condition,))
    if condition == "visible_cot":
        base = construct_visible_cot_prompt(question)
    elif condition == "r1_style_thinking":
        base = construct_r1_style_thinking_prompt(question)
    else:
        raise HeadroomCalibrationError(
            f"condition {condition!r} is not enabled for this calibration round"
        )
    return base + PROMPT_OVERRIDE_TEXT


def record_id_for(task_id: str, condition: str, replicate_index: int = REPLICATE_INDEX) -> str:
    """Return the stable record identifier for one unit of work."""

    return f"{task_id}::{condition}::r{replicate_index}"


@dataclass(frozen=True)
class WorkUnit:
    """One deterministic generation request."""

    record_id: str
    task_id: str
    task_family: str
    difficulty_band: str
    split: str
    answer_type: str
    condition: str
    replicate_index: int
    prompt: str
    prompt_sha256: str
    seed: int
    registered_answer: str
    entity_ids: tuple[str, ...]
    question: str


def _entity_ids(item: Mapping[str, Any]) -> tuple[str, ...]:
    metadata = item.get("metadata") or {}
    raw = metadata.get("entity_ids") or []
    return tuple(sorted({str(value) for value in raw}))


def plan_work_units(
    items: Sequence[Mapping[str, Any]],
    conditions: Sequence[str] = CONDITIONS,
) -> list[WorkUnit]:
    """Expand selected items into the frozen, sorted generation plan."""

    validate_phase1_conditions(conditions)
    ordered_conditions = tuple(sorted(set(conditions)))
    units: list[WorkUnit] = []
    for item in sorted(items, key=lambda entry: str(entry["task_id"])):
        task_id = str(item["task_id"])
        metadata = item.get("metadata") or {}
        answer_type = str(metadata.get("answer_type", ""))
        question = str(item["question"])
        for condition in ordered_conditions:
            prompt = build_condition_prompt(question, condition)
            units.append(
                WorkUnit(
                    record_id=record_id_for(task_id, condition),
                    task_id=task_id,
                    task_family=str(item["task_family"]),
                    difficulty_band=str(item["difficulty_band"]),
                    split=str(item["split"]),
                    answer_type=answer_type,
                    condition=condition,
                    replicate_index=REPLICATE_INDEX,
                    prompt=prompt,
                    prompt_sha256=sha256_text(prompt),
                    seed=derive_run_seed(
                        task_id,
                        condition,
                        MAX_NEW_TOKENS,
                        DECODING_PROFILE,
                        REPLICATE_INDEX,
                    ),
                    registered_answer=str(item["registered_answer"]),
                    entity_ids=_entity_ids(item),
                    question=question,
                )
            )
    return units


# --------------------------------------------------------------------------
# Generation backends (dependency injected; no GPU needed for tests)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class GenerationOutput:
    """A single generation result with the provenance needed downstream."""

    output_text: str
    prompt_token_count: int | None = None
    output_token_count: int | None = None
    hit_token_cap: bool = False
    backend: str = "unspecified"
    error: str | None = None


class GenerationBackend(Protocol):
    """Minimal generation interface so tests never require torch."""

    name: str

    def generate(self, unit: WorkUnit, config: ConditionGenerationConfig) -> GenerationOutput:
        """Return one generation for the supplied work unit."""


@dataclass
class ScriptedBackend:
    """Deterministic offline backend used by ``--self-test`` and unit tests."""

    responses: Mapping[str, str] = field(default_factory=dict)
    default_response: str = "Final answer: UNKNOWN"
    name: str = "scripted_stub_v1"

    def generate(self, unit: WorkUnit, config: ConditionGenerationConfig) -> GenerationOutput:
        text = self.responses.get(unit.record_id, self.default_response)
        token_count = max(1, len(text.split()))
        return GenerationOutput(
            output_text=text,
            prompt_token_count=max(1, len(unit.prompt.split())),
            output_token_count=token_count,
            hit_token_cap=token_count >= config.max_new_tokens,
            backend=self.name,
        )


@dataclass
class SelfTestBackend:
    """Offline backend that fabricates a fixed per-cell accuracy for structure tests.

    Items whose index inside a cell is at or below ``correct_items_per_cell`` return
    the registered answer; the rest return a deliberately wrong answer.  The outputs
    are synthetic fixtures and carry no scientific content.
    """

    correct_items_per_cell: int = 8
    name: str = "self_test_fixed_accuracy_v1"

    def generate(self, unit: WorkUnit, config: ConditionGenerationConfig) -> GenerationOutput:
        index = int(unit.task_id.rsplit("-", 1)[-1])
        if index <= self.correct_items_per_cell:
            answer = unit.registered_answer
        elif unit.answer_type in ENTITY_ANSWER_TYPES:
            alternatives = [
                entity for entity in unit.entity_ids if entity != unit.registered_answer
            ]
            answer = alternatives[0] if alternatives else "NoSuchEntity"
        else:
            answer = "-999999"
        text = (
            "<think>\nCalibration self-test placeholder reasoning.\n</think>\n"
            f"Final answer: {answer}"
        )
        token_count = max(1, len(text.split()))
        return GenerationOutput(
            output_text=text,
            prompt_token_count=max(1, len(unit.prompt.split())),
            output_token_count=token_count,
            hit_token_cap=False,
            backend=self.name,
        )


class TransformersBackend:
    """Real GPU backend; imports torch/transformers lazily at construction."""

    name = "transformers_causal_lm_v1"

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

    def generate(self, unit: WorkUnit, config: ConditionGenerationConfig) -> GenerationOutput:
        torch = self._torch
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
        output_token_count = int(new_tokens.shape[-1])
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return GenerationOutput(
            output_text=text,
            prompt_token_count=prompt_token_count,
            output_token_count=output_token_count,
            hit_token_cap=output_token_count >= config.max_new_tokens,
            backend=self.name,
        )


def run_generations(
    units: Sequence[WorkUnit],
    backend: GenerationBackend,
) -> dict[str, GenerationOutput]:
    """Execute every unit in frozen order and collect outputs by record id."""

    results: dict[str, GenerationOutput] = {}
    for unit in units:
        config = generation_config(unit.condition)
        try:
            results[unit.record_id] = backend.generate(unit, config)
        except Exception as error:  # pragma: no cover - hardware/runtime failures
            results[unit.record_id] = GenerationOutput(
                output_text="",
                backend=getattr(backend, "name", "unknown"),
                error=f"{type(error).__name__}: {error}",
            )
    return results


# --------------------------------------------------------------------------
# Deterministic triage (screening only; never authoritative)
# --------------------------------------------------------------------------

NUMERIC_ANSWER_TYPES: tuple[str, ...] = ("numeric", "numeric_step_code")
ENTITY_ANSWER_TYPES: tuple[str, ...] = ("entity",)

TRIAGE_AUTHORITY = "screening_only_not_locked"
PARSER_V2_LOCKED_VALIDATION_STATUS = (
    "failed_2026-07-25:boxed_final_miss=1/20,wrong_span=2/80"
)
ENTITY_TRIAGE_ENGINE = "entity_surface_match_v1"
NUMERIC_TRIAGE_ENGINE = "parser_v2_read_only"

_THINK_CLOSE = "</think>"


@dataclass(frozen=True)
class TriageResult:
    """Non-authoritative screening verdict for a single generation."""

    engine: str
    engine_version: str
    answer_presence: str
    parse_valid: bool
    parse_ambiguous: bool
    parsed_answer: str | None
    candidate_answers: tuple[str, ...]
    output_quality: str
    failure_reasons: tuple[str, ...]
    matches_registered_answer: bool | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer_presence": self.answer_presence,
            "candidate_answers": list(self.candidate_answers),
            "engine": self.engine,
            "engine_version": self.engine_version,
            "failure_reasons": list(self.failure_reasons),
            "matches_registered_answer": self.matches_registered_answer,
            "output_quality": self.output_quality,
            "parse_ambiguous": self.parse_ambiguous,
            "parse_valid": self.parse_valid,
            "parsed_answer": self.parsed_answer,
            "triage_authority": TRIAGE_AUTHORITY,
        }


def final_segment(output_text: str) -> str:
    """Return the text after the last ``</think>`` marker, else the whole text."""

    if _THINK_CLOSE in output_text:
        return output_text.rsplit(_THINK_CLOSE, 1)[1]
    return output_text


def _entity_pattern(entity: str) -> re.Pattern[str]:
    return re.compile(
        r"(?<![0-9A-Za-z_])" + re.escape(entity) + r"(?![0-9A-Za-z_])",
        re.UNICODE,
    )


def triage_numeric(output_text: str, registered_answer: str) -> TriageResult:
    """Screen a numeric output with parser v2, read-only."""

    result = parse_v2(
        {
            "schema_version": "phase1-parser-v2-request/v1",
            "answer_type": "numeric",
            "output_text": output_text,
        }
    )
    matches: bool | None
    if result.get("parse_valid") and result.get("parsed_answer") is not None:
        matches = bool(compare_parsed_answer_to_reference(result, registered_answer))
    else:
        matches = None
    return TriageResult(
        engine=NUMERIC_TRIAGE_ENGINE,
        engine_version=str(PARSER_V2_VERSION),
        answer_presence=str(result.get("answer_presence", "absent")),
        parse_valid=bool(result.get("parse_valid", False)),
        parse_ambiguous=bool(result.get("parse_ambiguous", False)),
        parsed_answer=(
            None if result.get("parsed_answer") is None else str(result["parsed_answer"])
        ),
        candidate_answers=tuple(str(v) for v in (result.get("candidate_answers") or [])),
        output_quality=str(result.get("output_quality", "empty")),
        failure_reasons=tuple(sorted(str(v) for v in (result.get("failure_reasons") or []))),
        matches_registered_answer=matches,
    )


def triage_entity(
    output_text: str,
    registered_answer: str,
    entity_ids: Sequence[str],
) -> TriageResult:
    """Screen an entity output with a deterministic surface matcher.

    No locked typed-entity evaluator exists yet, so this matcher is explicitly
    non-authoritative and every entity row it cannot settle is escalated to
    semantic review.
    """

    vocabulary = sorted({str(value) for value in entity_ids} | {registered_answer})
    tail = final_segment(output_text)
    lines = [line.strip() for line in tail.splitlines() if line.strip()]
    last_line = lines[-1] if lines else ""

    failure_reasons: list[str] = []
    in_last_line = sorted(
        entity for entity in vocabulary if _entity_pattern(entity).search(last_line)
    )
    anywhere = sorted(
        entity for entity in vocabulary if _entity_pattern(entity).search(tail)
    )

    if not output_text.strip():
        quality = "empty"
    elif not anywhere:
        quality = "malformed_unrecoverable"
    else:
        quality = "complete"

    if in_last_line:
        candidates = in_last_line
    else:
        candidates = anywhere
        if anywhere:
            failure_reasons.append("answer_not_in_final_line")

    ambiguous = len(candidates) > 1
    if ambiguous:
        failure_reasons.append("multiple_entity_candidates")
    if not candidates:
        failure_reasons.append("no_registered_entity_found")

    parsed = candidates[0] if len(candidates) == 1 else None
    presence = "present" if candidates else "absent"
    valid = parsed is not None and not failure_reasons
    matches = None if parsed is None else parsed == registered_answer
    return TriageResult(
        engine=ENTITY_TRIAGE_ENGINE,
        engine_version=ENTITY_TRIAGE_ENGINE,
        answer_presence=presence,
        parse_valid=bool(valid),
        parse_ambiguous=ambiguous,
        parsed_answer=parsed,
        candidate_answers=tuple(candidates),
        output_quality=quality,
        failure_reasons=tuple(sorted(set(failure_reasons))),
        matches_registered_answer=matches,
    )


def triage_output(
    output_text: str,
    answer_type: str,
    registered_answer: str,
    entity_ids: Sequence[str] = (),
) -> TriageResult:
    """Dispatch triage on the registered answer type."""

    if answer_type in NUMERIC_ANSWER_TYPES:
        return triage_numeric(output_text, registered_answer)
    if answer_type in ENTITY_ANSWER_TYPES:
        return triage_entity(output_text, registered_answer, entity_ids)
    raise HeadroomCalibrationError(f"unsupported answer_type: {answer_type!r}")


# --------------------------------------------------------------------------
# Record construction
# --------------------------------------------------------------------------

STATUS_PLANNED = "planned"
STATUS_GENERATED = "generated"
STATUS_GENERATION_ERROR = "generation_error"

LABEL_SOURCE_NOT_ADJUDICATED = "not_adjudicated"
LABEL_SOURCE_TRIAGE_ACCEPTED = "deterministic_triage_accepted"
LABEL_SOURCE_PRIMARY = "primary_reviewer"
LABEL_SOURCE_ARBITER = "arbiter"

SEMANTIC_LABELS: tuple[str, ...] = ("correct", "incorrect", "unresolved")


def cell_id_for(task_family: str, difficulty_band: str, condition: str) -> str:
    """Return the canonical cell identifier (conditions are never pooled)."""

    return f"{task_family}|{difficulty_band}|{condition}"


def build_records(
    run_id: str,
    units: Sequence[WorkUnit],
    outputs: Mapping[str, GenerationOutput] | None = None,
) -> list[dict[str, Any]]:
    """Build one provenance-complete record per unit of work."""

    outputs = outputs or {}
    records: list[dict[str, Any]] = []
    for unit in units:
        config = generation_config(unit.condition)
        result = outputs.get(unit.record_id)
        if result is None:
            status = STATUS_PLANNED
            output_text = None
            output_hash = None
            triage_payload: dict[str, Any] = {
                "answer_presence": "not_evaluated",
                "candidate_answers": [],
                "engine": "not_run",
                "engine_version": "not_run",
                "failure_reasons": [],
                "matches_registered_answer": None,
                "output_quality": "not_evaluated",
                "parse_ambiguous": False,
                "parse_valid": False,
                "parsed_answer": None,
                "triage_authority": TRIAGE_AUTHORITY,
            }
            truncated = False
            no_answer = False
        elif result.error is not None:
            status = STATUS_GENERATION_ERROR
            output_text = ""
            output_hash = sha256_text("")
            triage_payload = {
                "answer_presence": "absent",
                "candidate_answers": [],
                "engine": "not_run",
                "engine_version": "not_run",
                "failure_reasons": ["generation_error"],
                "matches_registered_answer": None,
                "output_quality": "empty",
                "parse_ambiguous": False,
                "parse_valid": False,
                "parsed_answer": None,
                "triage_authority": TRIAGE_AUTHORITY,
            }
            truncated = False
            no_answer = True
        else:
            status = STATUS_GENERATED
            output_text = result.output_text
            output_hash = sha256_text(output_text)
            triage = triage_output(
                output_text,
                unit.answer_type,
                unit.registered_answer,
                unit.entity_ids,
            )
            triage_payload = triage.as_dict()
            truncated = bool(result.hit_token_cap) or triage.output_quality == "truncated"
            no_answer = triage.answer_presence != "present"

        records.append(
            {
                "record_id": unit.record_id,
                "run_id": run_id,
                "phase": PHASE,
                "track": TRACK,
                "source_item_id": unit.task_id,
                "condition": unit.condition,
                "status": status,
                "input_hash": unit.prompt_sha256,
                "output_hash": output_hash,
                "evaluation": {
                    "final_correct": None,
                    "no_answer": no_answer,
                    "provisional_correct": triage_payload["matches_registered_answer"],
                    "review_reasons": [],
                    "review_required": False,
                    "semantic_label": None,
                    "semantic_label_source": LABEL_SOURCE_NOT_ADJUDICATED,
                    "triage": triage_payload,
                    "truncated": truncated,
                },
                "provenance": {
                    "answer_type": unit.answer_type,
                    "backend": None if result is None else result.backend,
                    "cell_id": cell_id_for(
                        unit.task_family, unit.difficulty_band, unit.condition
                    ),
                    "code_module": SCHEMA_VERSION,
                    "decoding_profile": config.decoding_profile,
                    "difficulty_band": unit.difficulty_band,
                    "do_sample": config.do_sample,
                    "generation_error": None if result is None else result.error,
                    "max_new_tokens": config.max_new_tokens,
                    "model_id": MODEL_ID,
                    "model_revision": MODEL_REVISION,
                    "output_token_count": None if result is None else result.output_token_count,
                    "prompt_text": unit.prompt,
                    "prompt_token_count": None if result is None else result.prompt_token_count,
                    "registered_answer": unit.registered_answer,
                    "replicate_index": unit.replicate_index,
                    "seed": unit.seed,
                    "split": unit.split,
                    "task_family": unit.task_family,
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                },
                "output_text": output_text,
            }
        )
    return records


# --------------------------------------------------------------------------
# Bounded, deterministic review-row selection
# --------------------------------------------------------------------------


def _review_sample_key(record_id: str) -> str:
    canonical = "\0".join((REVIEW_SAMPLE_DOMAIN, str(SELECTION_SEED), record_id))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _provisional_cell_correct(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        cell = str(record["provenance"]["cell_id"])
        counts.setdefault(cell, 0)
        if record["evaluation"]["triage"]["matches_registered_answer"] is True:
            counts[cell] += 1
    return counts


def annotate_review_selection(
    records: Sequence[dict[str, Any]],
    *,
    sample_fraction: float = REVIEW_SAMPLE_FRACTION,
    provisional_min_correct: int = PROVISIONAL_REVIEW_MIN_CORRECT,
) -> list[dict[str, Any]]:
    """Flag the bounded set of rows a semantic reviewer must adjudicate.

    Mandatory categories: parse-invalid, ambiguous, truncated/no-answer, triage
    disagreement with the registered answer, every row in a provisionally
    qualifying headroom cell, and a deterministic sample of the remaining clean
    rows.  Nothing else is sent for review.
    """

    provisional = _provisional_cell_correct(records)
    clean: list[dict[str, Any]] = []
    for record in records:
        evaluation = record["evaluation"]
        triage = evaluation["triage"]
        reasons: list[str] = []
        if record["status"] == STATUS_PLANNED:
            evaluation["review_required"] = False
            evaluation["review_reasons"] = []
            continue
        if not triage["parse_valid"]:
            reasons.append("parse_invalid")
        if triage["parse_ambiguous"]:
            reasons.append("ambiguous_parse")
        if evaluation["truncated"]:
            reasons.append("truncated_output")
        if evaluation["no_answer"]:
            reasons.append("no_answer")
        if triage["matches_registered_answer"] is False:
            reasons.append("triage_disagrees_with_registered_answer")
        cell = str(record["provenance"]["cell_id"])
        if provisional.get(cell, 0) >= provisional_min_correct:
            reasons.append("provisional_headroom_cell")
        evaluation["review_reasons"] = sorted(set(reasons))
        evaluation["review_required"] = bool(reasons)
        if not reasons:
            clean.append(record)

    sample_size = math.ceil(sample_fraction * len(clean)) if clean else 0
    ordered = sorted(
        clean,
        key=lambda record: (_review_sample_key(str(record["record_id"])), str(record["record_id"])),
    )
    for record in ordered[:sample_size]:
        record["evaluation"]["review_reasons"] = ["deterministic_random_sample"]
        record["evaluation"]["review_required"] = True
    return list(records)


# --------------------------------------------------------------------------
# Review pack construction and judgment ingestion
# --------------------------------------------------------------------------

REVIEW_ORDER_DOMAIN = "jspace-headroom-calibration/review-order/v1"


def _review_order_key(record_id: str) -> str:
    canonical = "\0".join((REVIEW_ORDER_DOMAIN, str(SELECTION_SEED), record_id))
    return sha256(canonical.encode("utf-8")).hexdigest()


def build_review_pack(
    run_id: str,
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the blinded primary-review pack and its unblinded triage sidecar."""

    flagged = [record for record in records if record["evaluation"]["review_required"]]
    ordered = sorted(
        flagged,
        key=lambda record: (_review_order_key(str(record["record_id"])), str(record["record_id"])),
    )
    review_rows: list[dict[str, Any]] = []
    triage_rows: list[dict[str, Any]] = []
    for index, record in enumerate(ordered, start=1):
        review_id = f"R{index:03d}"
        provenance = record["provenance"]
        evaluation = record["evaluation"]
        review_rows.append(
            {
                "answer_type": provenance["answer_type"],
                "cell_id": provenance["cell_id"],
                "condition": record["condition"],
                "difficulty_band": provenance["difficulty_band"],
                "input_hash": record["input_hash"],
                "model_output": record["output_text"],
                "output_hash": record["output_hash"],
                "prompt_text": provenance["prompt_text"],
                "record_id": record["record_id"],
                "registered_answer": provenance["registered_answer"],
                "required_response": {
                    "notes": "<free text, optional>",
                    "review_id": review_id,
                    "reviewer_id": "<reviewer identifier>",
                    "semantic_label": "<correct|incorrect|unresolved>",
                },
                "review_id": review_id,
                "review_reasons": list(evaluation["review_reasons"]),
                "run_id": run_id,
                "source_item_id": record["source_item_id"],
                "task_family": provenance["task_family"],
            }
        )
        triage_rows.append(
            {
                "cell_id": provenance["cell_id"],
                "deterministic_result": _deterministic_label(evaluation),
                "no_answer": evaluation["no_answer"],
                "record_id": record["record_id"],
                "review_id": review_id,
                "run_id": run_id,
                "triage": evaluation["triage"],
                "truncated": evaluation["truncated"],
            }
        )
    return review_rows, triage_rows


def _deterministic_label(evaluation: Mapping[str, Any]) -> str | None:
    matches = evaluation["triage"]["matches_registered_answer"]
    if matches is True:
        return "correct"
    if matches is False:
        return "incorrect"
    return None


def load_judgments(path: str | Path | None) -> dict[str, dict[str, Any]]:
    """Load reviewer judgments keyed by ``record_id``."""

    if path is None:
        return {}
    judgment_path = Path(path)
    if not judgment_path.is_file():
        raise HeadroomCalibrationError(f"judgment file not found: {judgment_path}")
    judgments: dict[str, dict[str, Any]] = {}
    with open(judgment_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if payload.get("status") == "not_applicable":
                continue
            record_id = payload.get("record_id")
            label = payload.get("semantic_label")
            if not record_id:
                raise HeadroomCalibrationError(
                    f"judgment at line {line_number} is missing record_id"
                )
            if label not in SEMANTIC_LABELS:
                raise HeadroomCalibrationError(
                    f"judgment at line {line_number} has invalid semantic_label {label!r}"
                )
            judgments[str(record_id)] = dict(payload)
    return judgments


def apply_judgments(
    records: Sequence[dict[str, Any]],
    primary: Mapping[str, Mapping[str, Any]] | None = None,
    arbiter: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Resolve the final semantic label for every record.

    A row that was not selected for review inherits the deterministic screening
    verdict.  A reviewed row is decided by the primary reviewer, except where the
    reviewer conflicts with the deterministic verdict, in which case only an
    arbiter judgment can resolve it.
    """

    primary = primary or {}
    arbiter = arbiter or {}
    for record in records:
        evaluation = record["evaluation"]
        deterministic = _deterministic_label(evaluation)
        if record["status"] == STATUS_PLANNED:
            evaluation["semantic_label"] = None
            evaluation["semantic_label_source"] = LABEL_SOURCE_NOT_ADJUDICATED
            evaluation["final_correct"] = None
            evaluation["arbitration_required"] = False
            continue
        if not evaluation["review_required"]:
            label = deterministic or "unresolved"
            evaluation["semantic_label"] = label
            evaluation["semantic_label_source"] = (
                LABEL_SOURCE_TRIAGE_ACCEPTED if deterministic else LABEL_SOURCE_NOT_ADJUDICATED
            )
            evaluation["final_correct"] = _label_to_correct(label)
            evaluation["arbitration_required"] = False
            continue

        judgment = primary.get(str(record["record_id"]))
        if judgment is None:
            evaluation["semantic_label"] = "unresolved"
            evaluation["semantic_label_source"] = LABEL_SOURCE_NOT_ADJUDICATED
            evaluation["final_correct"] = None
            evaluation["arbitration_required"] = False
            continue

        primary_label = str(judgment["semantic_label"])
        conflict = (
            deterministic is not None
            and primary_label in {"correct", "incorrect"}
            and primary_label != deterministic
        )
        evaluation["arbitration_required"] = bool(conflict)
        if not conflict:
            evaluation["semantic_label"] = primary_label
            evaluation["semantic_label_source"] = LABEL_SOURCE_PRIMARY
            evaluation["final_correct"] = _label_to_correct(primary_label)
            continue

        arbiter_judgment = arbiter.get(str(record["record_id"]))
        if arbiter_judgment is None:
            evaluation["semantic_label"] = "unresolved"
            evaluation["semantic_label_source"] = LABEL_SOURCE_NOT_ADJUDICATED
            evaluation["final_correct"] = None
            continue
        arbiter_label = str(arbiter_judgment["semantic_label"])
        evaluation["semantic_label"] = arbiter_label
        evaluation["semantic_label_source"] = LABEL_SOURCE_ARBITER
        evaluation["final_correct"] = _label_to_correct(arbiter_label)
    return list(records)


def _label_to_correct(label: str | None) -> bool | None:
    if label == "correct":
        return True
    if label == "incorrect":
        return False
    return None


def build_arbitration_packet(
    run_id: str,
    records: Sequence[Mapping[str, Any]],
    review_rows: Sequence[Mapping[str, Any]],
    primary: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Emit the arbitration packet for primary/deterministic conflicts only."""

    review_ids = {str(row["record_id"]): str(row["review_id"]) for row in review_rows}
    packet: list[dict[str, Any]] = []
    for record in records:
        evaluation = record["evaluation"]
        if not evaluation.get("arbitration_required"):
            continue
        record_id = str(record["record_id"])
        judgment = primary.get(record_id, {})
        packet.append(
            {
                "deterministic_result": _deterministic_label(evaluation),
                "model_output": record["output_text"],
                "primary_label": judgment.get("semantic_label"),
                "primary_notes": judgment.get("notes"),
                "record_id": record_id,
                "registered_answer": record["provenance"]["registered_answer"],
                "required_response": {
                    "arbiter_id": "<arbiter identifier>",
                    "record_id": record_id,
                    "semantic_label": "<correct|incorrect|unresolved>",
                },
                "review_id": review_ids.get(record_id),
                "run_id": run_id,
                "triage_authority": TRIAGE_AUTHORITY,
            }
        )
    return sorted(packet, key=lambda row: str(row["record_id"]))


# --------------------------------------------------------------------------
# Headroom cell scoring
# --------------------------------------------------------------------------


def score_cells(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Score every family x band x condition cell against the frozen rule.

    Qualification requires n = 10, adjudicated semantic accuracy inside
    ``[0.70, 0.90]`` with at least 7/10 correct, truncation rate <= 0.10,
    no-answer rate <= 0.10, zero unresolved semantic labels, and complete
    semantic review coverage of every row that was flagged for review.
    """

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record["provenance"]["cell_id"]), []).append(record)

    cells: list[dict[str, Any]] = []
    for cell_id in sorted(grouped):
        rows = sorted(grouped[cell_id], key=lambda row: str(row["record_id"]))
        family, band, condition = cell_id.split("|")
        n = len(rows)
        planned = sum(1 for row in rows if row["status"] == STATUS_PLANNED)
        correct = sum(1 for row in rows if row["evaluation"]["final_correct"] is True)
        incorrect = sum(1 for row in rows if row["evaluation"]["final_correct"] is False)
        unresolved = n - correct - incorrect
        truncated = sum(1 for row in rows if row["evaluation"]["truncated"])
        no_answer = sum(1 for row in rows if row["evaluation"]["no_answer"])
        ambiguous = sum(
            1 for row in rows if row["evaluation"]["triage"]["parse_ambiguous"]
        )
        flagged = [row for row in rows if row["evaluation"]["review_required"]]
        adjudicated = [
            row
            for row in flagged
            if row["evaluation"]["semantic_label_source"]
            in {LABEL_SOURCE_PRIMARY, LABEL_SOURCE_ARBITER}
        ]
        review_coverage_complete = len(adjudicated) == len(flagged)

        accuracy = _rate(correct, n) if unresolved == 0 and planned == 0 else None
        truncation_rate = _rate(truncated, n)
        no_answer_rate = _rate(no_answer, n)
        if accuracy is None:
            ci_lower, ci_upper = None, None
        else:
            raw_lower, raw_upper = wilson_ci(correct, n)
            ci_lower, ci_upper = _round6(raw_lower), _round6(raw_upper)

        reasons: list[str] = []
        if n != REQUIRED_CELL_N:
            reasons.append("incomplete_cell_n")
        if planned or unresolved:
            if planned:
                reasons.append("labels_not_semantically_adjudicated")
            if unresolved:
                reasons.append("unresolved_semantic_labels_present")
        if truncation_rate > MAX_TRUNCATION_RATE:
            reasons.append("truncation_rate_above_threshold")
        if no_answer_rate > MAX_NO_ANSWER_RATE:
            reasons.append("no_answer_rate_above_threshold")
        if not review_coverage_complete:
            reasons.append("incomplete_review_coverage")
        if accuracy is not None:
            if accuracy > ACCURACY_BAND_HIGH:
                reasons.append("accuracy_above_band_control_only")
            elif accuracy < ACCURACY_BAND_LOW:
                reasons.append("accuracy_below_band_difficulty_boundary")
            if correct < MIN_CORRECT_COUNT:
                reasons.append("insufficient_correct_count")

        reasons = sorted(set(reasons))
        if not reasons:
            classification = "selected_headroom"
        elif accuracy is None:
            classification = "not_adjudicated"
        elif accuracy > ACCURACY_BAND_HIGH:
            classification = "control_sanity_high_accuracy"
        elif accuracy < ACCURACY_BAND_LOW:
            classification = "difficulty_boundary_excluded"
        else:
            classification = "excluded_quality_gate"

        cells.append(
            {
                "accuracy": accuracy,
                "ambiguous": ambiguous,
                "ambiguous_rate": _rate(ambiguous, n),
                "cell_id": cell_id,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "classification": classification,
                "condition": condition,
                "correct": correct,
                "difficulty_band": band,
                "exclusion_reasons": reasons,
                "incorrect": incorrect,
                "n": n,
                "no_answer": no_answer,
                "no_answer_rate": no_answer_rate,
                "record_ids": [str(row["record_id"]) for row in rows],
                "review_coverage_complete": review_coverage_complete,
                "review_required": len(flagged),
                "reviewed": len(adjudicated),
                "selected": not reasons,
                "task_family": family,
                "truncated": truncated,
                "truncation_rate": truncation_rate,
                "unresolved": unresolved,
            }
        )
    return cells


def supplementary_review_cells(cells: Sequence[Mapping[str, Any]]) -> list[str]:
    """Cells blocked only by missing review coverage need a follow-up pack."""

    return sorted(
        str(cell["cell_id"])
        for cell in cells
        if cell["exclusion_reasons"] == ["incomplete_review_coverage"]
    )


def _cell_row(cell: Mapping[str, Any], run_id: str) -> list[Any]:
    return [
        run_id,
        cell["cell_id"],
        cell["task_family"],
        cell["difficulty_band"],
        cell["condition"],
        cell["n"],
        cell["correct"],
        cell["accuracy"],
        cell["ci_lower"],
        cell["ci_upper"],
        cell["truncation_rate"],
        cell["no_answer_rate"],
        cell["unresolved"],
        str(cell["review_coverage_complete"]).lower(),
        cell["classification"],
    ]


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def _metric_row(
    run_id: str,
    metric: str,
    stratum: str,
    condition: str,
    numerator: int | None,
    denominator: int | None,
    *,
    threshold: Any = None,
    passed: bool | None = None,
    not_applicable_reason: str | None = None,
    with_ci: bool = True,
) -> list[Any]:
    if denominator:
        value = _rate(int(numerator or 0), int(denominator))
        if with_ci:
            lower, upper = wilson_ci(int(numerator or 0), int(denominator))
            ci_lower, ci_upper = _round6(lower), _round6(upper)
        else:
            ci_lower, ci_upper = None, None
    else:
        value, ci_lower, ci_upper = None, None, None
    return [
        run_id,
        PHASE,
        TRACK,
        metric,
        stratum,
        condition,
        denominator,
        numerator,
        denominator,
        value,
        ci_lower,
        ci_upper,
        threshold,
        "" if passed is None else str(bool(passed)).lower(),
        not_applicable_reason or "",
    ]


def build_metrics_rows(
    run_id: str,
    records: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
) -> list[list[Any]]:
    """Build the metric table, including binomial confidence intervals."""

    rows: list[list[Any]] = []
    adjudicated_available = any(cell["accuracy"] is not None for cell in cells)
    na_reason = "" if adjudicated_available else "labels_not_semantically_adjudicated"

    by_condition: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        by_condition.setdefault(str(record["condition"]), []).append(record)

    for condition in sorted(by_condition):
        subset = by_condition[condition]
        n = len(subset)
        correct = sum(1 for row in subset if row["evaluation"]["final_correct"] is True)
        unresolved = sum(
            1 for row in subset if row["evaluation"]["final_correct"] is None
        )
        rows.append(
            _metric_row(
                run_id,
                "semantic_accuracy",
                "all",
                condition,
                correct if unresolved == 0 else None,
                n if unresolved == 0 else None,
                threshold=f"{ACCURACY_BAND_LOW}-{ACCURACY_BAND_HIGH}",
                not_applicable_reason=(
                    "" if unresolved == 0 else "labels_not_semantically_adjudicated"
                ),
            )
        )
        rows.append(
            _metric_row(
                run_id,
                "truncation_rate",
                "all",
                condition,
                sum(1 for row in subset if row["evaluation"]["truncated"]),
                n,
                threshold=MAX_TRUNCATION_RATE,
                passed=_rate(
                    sum(1 for row in subset if row["evaluation"]["truncated"]), n
                )
                <= MAX_TRUNCATION_RATE,
            )
        )
        rows.append(
            _metric_row(
                run_id,
                "no_answer_rate",
                "all",
                condition,
                sum(1 for row in subset if row["evaluation"]["no_answer"]),
                n,
                threshold=MAX_NO_ANSWER_RATE,
                passed=_rate(
                    sum(1 for row in subset if row["evaluation"]["no_answer"]), n
                )
                <= MAX_NO_ANSWER_RATE,
            )
        )
        rows.append(
            _metric_row(
                run_id,
                "triage_parse_valid_rate",
                "all",
                condition,
                sum(1 for row in subset if row["evaluation"]["triage"]["parse_valid"]),
                n,
            )
        )
        rows.append(
            _metric_row(
                run_id,
                "unresolved_label_rate",
                "all",
                condition,
                unresolved,
                n,
                threshold=0.0,
                passed=unresolved == 0,
            )
        )

    for cell in cells:
        rows.append(
            _metric_row(
                run_id,
                "semantic_accuracy",
                f"{cell['task_family']}|{cell['difficulty_band']}",
                str(cell["condition"]),
                cell["correct"] if cell["accuracy"] is not None else None,
                cell["n"] if cell["accuracy"] is not None else None,
                threshold=f"{ACCURACY_BAND_LOW}-{ACCURACY_BAND_HIGH}",
                passed=None if cell["accuracy"] is None else bool(cell["selected"]),
                not_applicable_reason=(
                    "" if cell["accuracy"] is not None else "labels_not_semantically_adjudicated"
                ),
            )
        )
        stratum = f"{cell['task_family']}|{cell['difficulty_band']}"
        condition = str(cell["condition"])
        rows.append(
            _metric_row(
                run_id,
                "truncation_rate",
                stratum,
                condition,
                cell["truncated"],
                cell["n"],
                threshold=MAX_TRUNCATION_RATE,
                passed=cell["truncation_rate"] <= MAX_TRUNCATION_RATE,
            )
        )
        rows.append(
            _metric_row(
                run_id,
                "no_answer_rate",
                stratum,
                condition,
                cell["no_answer"],
                cell["n"],
                threshold=MAX_NO_ANSWER_RATE,
                passed=cell["no_answer_rate"] <= MAX_NO_ANSWER_RATE,
            )
        )
        rows.append(
            _metric_row(
                run_id,
                "ambiguous_rate",
                stratum,
                condition,
                cell["ambiguous"],
                cell["n"],
            )
        )
        rows.append(
            _metric_row(
                run_id,
                "semantic_review_rate",
                stratum,
                condition,
                cell["review_required"],
                cell["n"],
            )
        )
        rows.append(
            _metric_row(
                run_id,
                "unresolved_label_rate",
                stratum,
                condition,
                cell["unresolved"],
                cell["n"],
                threshold=0.0,
                passed=cell["unresolved"] == 0,
            )
        )

    review_required = sum(
        1 for record in records if record["evaluation"]["review_required"]
    )
    reviewed = sum(
        1
        for record in records
        if record["evaluation"]["semantic_label_source"]
        in {LABEL_SOURCE_PRIMARY, LABEL_SOURCE_ARBITER}
    )
    rows.append(
        _metric_row(
            run_id,
            "review_coverage_rate",
            "all",
            "all",
            reviewed,
            review_required,
            threshold=1.0,
            passed=None if not review_required else reviewed == review_required,
            not_applicable_reason=(
                "" if review_required else "no_rows_flagged_for_review"
            ),
        )
    )
    rows.append(
        _metric_row(
            run_id,
            "review_load_fraction",
            "all",
            "all",
            review_required,
            len(records),
            threshold="<=1.0",
        )
    )
    selected = sum(1 for cell in cells if cell["selected"])
    rows.append(
        _metric_row(
            run_id,
            "selected_headroom_cell_count",
            "all",
            "all",
            selected,
            len(cells),
            threshold=1,
            passed=None if not adjudicated_available else selected >= 1,
            not_applicable_reason=na_reason,
            with_ci=False,
        )
    )
    return rows


# --------------------------------------------------------------------------
# Protocol snapshot and provenance
# --------------------------------------------------------------------------

RESEARCH_QUESTION = (
    "Which frozen Phase 1 task cells (task family x difficulty band x visible-reasoning "
    "condition) leave the target model measurable observable-answer headroom, so that "
    "later ablation and activation-patching experiments are not run on saturated or "
    "impossible tasks?"
)

DECISION_RULES: tuple[str, ...] = (
    "A cell qualifies only when n = 10.",
    "A cell qualifies only when adjudicated semantic accuracy lies in [0.70, 0.90].",
    "A cell qualifies only when at least 7 of 10 items are adjudicated correct.",
    "A cell qualifies only when its truncation rate is <= 0.10.",
    "A cell qualifies only when its no-answer rate is <= 0.10.",
    "A cell qualifies only when it has zero unresolved semantic labels.",
    "A cell qualifies only when every row flagged for review has an adjudicated label.",
    "Accuracy > 0.90 makes a cell a sanity/control cell, deprioritized for ablation.",
    "Accuracy < 0.70 excludes a cell from ablation but retains it as a difficulty boundary.",
    "Parser v2 never decides a final label; it screens only.",
)

INCLUSION_RULES: tuple[str, ...] = (
    "Only the frozen calibration split of data/phase1_task_headroom_candidates.jsonl.",
    "Whole cells only: all 10 items of each family x band cell are run.",
    "Only conditions visible_cot and r1_style_thinking this round.",
    "Exactly one sample per item per condition.",
)

EXCLUSION_RULES: tuple[str, ...] = (
    "The confirmation and mechanistic splits stay held out and are not run.",
    "No item-level filtering, dropping, or re-sampling after outputs are seen.",
    "No condition outside the two registered conditions is scored this round.",
    "No pass@k aggregation; a single sample per item/condition is drawn.",
)

STOPPING_RULES: tuple[str, ...] = (
    "Generation stops after exactly 300 units of work (150 items x 2 conditions).",
    "Generation stops early only on an infrastructure fault; partial packs are marked BLOCKED.",
    "No adaptive stopping on observed accuracy is permitted.",
)

RETRY_RULES: tuple[str, ...] = (
    "A unit may be retried only after an infrastructure fault, never after an unwanted result.",
    "A retry reuses the identical frozen seed, prompt, and decoding profile.",
    "Every retry is recorded in 08_deviations.json with its cause.",
    "No prompt, seed, decoding, or scoring parameter may change during a retry.",
)

SECONDARY_METRICS: tuple[str, ...] = (
    "truncation_rate",
    "no_answer_rate",
    "triage_parse_valid_rate",
    "unresolved_label_rate",
    "review_coverage_rate",
    "review_load_fraction",
    "selected_headroom_cell_count",
)


def protocol_snapshot(
    bank_sha256: str,
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the preregistered protocol snapshot for this calibration run."""

    return {
        "conditions": {
            "deferred_this_round": list(DEFERRED_CONDITIONS),
            "enabled": list(CONDITIONS),
            "prompt_override_id": PROMPT_OVERRIDE_ID,
            "prompt_override_sha256": sha256_text(PROMPT_OVERRIDE_TEXT),
            "prompt_override_text": PROMPT_OVERRIDE_TEXT,
        },
        "decision_rules": list(DECISION_RULES),
        "evaluation": {
            "adjudication_authority": "semantic_reviewer",
            "arbiter_trigger": "primary_reviewer_conflicts_with_deterministic_result",
            "entity_triage_engine": ENTITY_TRIAGE_ENGINE,
            "mandatory_review_categories": [
                "parse_invalid",
                "ambiguous_parse",
                "truncated_output",
                "no_answer",
                "triage_disagrees_with_registered_answer",
                "provisional_headroom_cell",
                "deterministic_random_sample",
            ],
            "numeric_triage_engine": NUMERIC_TRIAGE_ENGINE,
            "parser_v2_locked_validation_status": PARSER_V2_LOCKED_VALIDATION_STATUS,
            "parser_v2_version": str(PARSER_V2_VERSION),
            "review_sample_fraction": REVIEW_SAMPLE_FRACTION,
            "triage_authority": TRIAGE_AUTHORITY,
        },
        "exclusion_rules": list(EXCLUSION_RULES),
        "generation_profile": {
            "decoding_profile": DECODING_PROFILE,
            "do_sample": DO_SAMPLE,
            "max_new_tokens": MAX_NEW_TOKENS,
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "samples_per_item_condition": SAMPLES_PER_ITEM,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
        },
        "inclusion_rules": list(INCLUSION_RULES),
        "primary_metric": "semantic_accuracy_per_cell",
        "protocol_version": PROTOCOL_VERSION,
        "research_question": RESEARCH_QUESTION,
        "retry_rules": list(RETRY_RULES),
        "sample_size": {
            "conditions": len(CONDITIONS),
            "generations": EXPECTED_GENERATION_COUNT,
            "items": EXPECTED_ITEM_COUNT,
            "items_per_cell": ITEMS_PER_CELL,
        },
        "schema_version": SCHEMA_VERSION,
        "scientific_claim_boundary": SCIENTIFIC_CLAIM_BOUNDARY,
        "secondary_metrics": list(SECONDARY_METRICS),
        "seeds": {
            "per_generation_seed_rule": (
                "headroom_candidates.derive_run_seed(task_id, condition, "
                f"{MAX_NEW_TOKENS}, '{DECODING_PROFILE}', {REPLICATE_INDEX})"
            ),
            "review_sample_domain": REVIEW_SAMPLE_DOMAIN,
            "run_base_seed": RUN_BASE_SEED,
            "selection_seed": SELECTION_SEED,
        },
        "selection": {
            "item_count": selection["item_count"],
            "per_band": selection["per_band"],
            "per_family": selection["per_family"],
            "per_family_band": selection["per_family_band"],
            "split": selection["split"],
            "task_bank_sha256": bank_sha256,
            "task_ids_sha256": selection["task_ids_sha256"],
        },
        "stopping_rules": list(STOPPING_RULES),
        "thresholds": {
            "accuracy_band_high": ACCURACY_BAND_HIGH,
            "accuracy_band_low": ACCURACY_BAND_LOW,
            "max_no_answer_rate": MAX_NO_ANSWER_RATE,
            "max_truncation_rate": MAX_TRUNCATION_RATE,
            "min_correct_count": MIN_CORRECT_COUNT,
            "required_cell_n": REQUIRED_CELL_N,
        },
    }


def protocol_hash(snapshot: Mapping[str, Any]) -> str:
    """Hash the protocol snapshot, excluding run-specific selection provenance."""

    frozen = {key: value for key, value in snapshot.items() if key != "selection"}
    return sha256_text(canonical_json(frozen))


def resolve_code_commit(repo_root: str | Path) -> str:
    """Resolve HEAD from the git directory without invoking git."""

    git_dir = Path(repo_root) / ".git"
    head_file = git_dir / "HEAD"
    if not head_file.is_file():
        return "unknown"
    head = head_file.read_text(encoding="utf-8").strip()
    if not head.startswith("ref:"):
        return head
    ref = head.split(" ", 1)[1].strip()
    ref_file = git_dir / ref
    if ref_file.is_file():
        return ref_file.read_text(encoding="utf-8").strip()
    packed = git_dir / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    return "unknown"



# --------------------------------------------------------------------------
# Artifact pack emission
# --------------------------------------------------------------------------

REVIEW_PACK_DIR = "review_pack"
CELL_SELECTION_DIR = "cell_selection"


def _display_path(path: Path | str | None, repo_root: Path | str) -> str | None:
    """Render a path repo-relative so packs are portable across machines."""

    if path is None:
        return None
    resolved = Path(path)
    root = Path(repo_root)
    try:
        return resolved.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return resolved.as_posix()


@dataclass(frozen=True)
class RunConfig:
    """All inputs needed to produce one artifact pack."""

    mode: str
    output_root: Path
    bank_path: Path
    repo_root: Path = REPO_ROOT
    run_id: str | None = None
    code_commit: str | None = None
    image_digest: str = "not_recorded"
    hardware: str = "not_recorded"
    frozen_time: str | None = None
    judgments_path: Path | None = None
    arbiter_judgments_path: Path | None = None
    records_path: Path | None = None
    backend: GenerationBackend | None = None

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise HeadroomCalibrationError(f"unknown mode: {self.mode}")
        for field_name in (
            "output_root",
            "bank_path",
            "repo_root",
            "judgments_path",
            "arbiter_judgments_path",
            "records_path",
        ):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, Path):
                object.__setattr__(self, field_name, Path(value))


def load_records(path: str | Path) -> list[dict[str, Any]]:
    """Load a previously emitted ``02_records.jsonl``."""

    records_path = Path(path)
    if not records_path.is_file():
        raise HeadroomCalibrationError(f"records file not found: {records_path}")
    records: list[dict[str, Any]] = []
    with open(records_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if payload.get("status") == "not_applicable":
                continue
            records.append(payload)
    if not records:
        raise HeadroomCalibrationError(f"records file is empty: {records_path}")
    return records


def _not_applicable_csv(reason: str) -> str:
    return canonical_csv(("status", "reason"), [["not_applicable", reason]])


def _not_applicable_jsonl(reason: str) -> str:
    return canonical_jsonl([{"reason": reason, "status": "not_applicable"}])


def _summary_markdown(
    run_id: str,
    config: RunConfig,
    manifest: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    selection: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    review_rows: Sequence[Mapping[str, Any]],
    decision: Mapping[str, Any],
) -> str:
    selected = [cell for cell in cells if cell["selected"]]
    controls = [
        cell for cell in cells if cell["classification"] == "control_sanity_high_accuracy"
    ]
    boundaries = [
        cell for cell in cells if cell["classification"] == "difficulty_boundary_excluded"
    ]
    lines: list[str] = []
    lines.append("# Summary")
    lines.append("")
    lines.append(
        f"Phase {PHASE} Track B bounded capability/headroom calibration, run `{run_id}`, "
        f"mode `{config.mode}`, status **{decision['status']}**."
    )
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(RESEARCH_QUESTION)
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        f"- {selection['item_count']} unique bank items "
        f"({len(TASK_FAMILIES)} families x {len(DIFFICULTY_BANDS)} bands x {ITEMS_PER_CELL} items), "
        f"split `{selection['split']}`."
    )
    lines.append(f"- Conditions run: {', '.join(CONDITIONS)}.")
    lines.append(f"- Conditions deferred: {', '.join(DEFERRED_CONDITIONS)}.")
    lines.append(f"- Total generation units: {EXPECTED_GENERATION_COUNT}.")
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Model: `{MODEL_ID}` at revision `{MODEL_REVISION}`.")
    lines.append(f"- Code commit: `{manifest['code_commit']}`.")
    lines.append(f"- Image digest: `{manifest['image_digest']}`.")
    lines.append(f"- Hardware: `{manifest['hardware']}`.")
    lines.append(f"- Protocol hash: `{manifest['protocol_hash']}`.")
    lines.append(
        f"- Task bank: `{_display_path(config.bank_path, config.repo_root)}` "
        f"(sha256 `{snapshot['selection']['task_bank_sha256']}`)."
    )
    lines.append(f"- Selection seed: `{SELECTION_SEED}`; run base seed `{RUN_BASE_SEED}`.")
    lines.append("")
    lines.append("## Execution")
    lines.append("")
    lines.append(f"- Records emitted: {len(records)}.")
    generated = sum(1 for row in records if row["status"] == STATUS_GENERATED)
    planned = sum(1 for row in records if row["status"] == STATUS_PLANNED)
    errored = sum(1 for row in records if row["status"] == STATUS_GENERATION_ERROR)
    lines.append(f"- Generated: {generated}; planned-only: {planned}; errors: {errored}.")
    lines.append(
        f"- Decoding: max_new_tokens={MAX_NEW_TOKENS}, temperature={TEMPERATURE}, "
        f"top_p={TOP_P}, samples per item/condition={SAMPLES_PER_ITEM}."
    )
    lines.append(
        f"- Rows flagged for semantic review: {len(review_rows)} of {len(records)}."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(f"- Cells scored: {len(cells)}.")
    lines.append(f"- Selected headroom cells: {len(selected)}.")
    lines.append(f"- High-accuracy control cells: {len(controls)}.")
    lines.append(f"- Difficulty-boundary cells: {len(boundaries)}.")
    if selected:
        lines.append("")
        lines.append("| cell | n | correct | accuracy | 95% CI |")
        lines.append("| --- | --- | --- | --- | --- |")
        for cell in selected:
            lines.append(
                f"| `{cell['cell_id']}` | {cell['n']} | {cell['correct']} | "
                f"{cell['accuracy']} | [{cell['ci_lower']}, {cell['ci_upper']}] |"
            )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- Status: **{decision['status']}**.")
    lines.append(f"- Decision: {decision['decision']}")
    lines.append("")
    lines.append("## Deviations and errors")
    lines.append("")
    deviations = decision.get("deviations") or []
    if deviations:
        for deviation in deviations:
            lines.append(f"- {deviation}")
    else:
        lines.append("- None recorded.")
    lines.append("")
    lines.append("## Scientific interpretation")
    lines.append("")
    lines.append(decision["scientific_interpretation"])
    lines.append("")
    for prohibited in PROHIBITED_INTERPRETATIONS:
        lines.append(f"- Prohibited: {prohibited}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- One sample per item/condition; no pass@k or sampling-variance estimate.")
    lines.append("- Parser v2 screening is not locked-validated and is never authoritative.")
    lines.append("- No locked typed-entity evaluator exists; entity rows rely on adjudication.")
    lines.append("- Only two visible-reasoning conditions were run; others are deferred.")
    lines.append("- Cell-level n = 10 gives wide binomial intervals; screening only.")
    lines.append("")
    lines.append("## Paper relevance")
    lines.append("")
    lines.append(
        "Supplies the task-selection appendix: which cells are usable for later ablation "
        "and patching experiments, which are saturated controls, and which are difficulty "
        "boundaries. It contributes no RQ1/RQ2 result."
    )
    lines.append("")
    lines.append("## Next gate")
    lines.append("")
    lines.append(f"- {decision['next_gate']}")
    lines.append("")
    return "\n".join(lines)


REVIEW_INSTRUCTIONS = """# Semantic review instructions (Phase 1.0C Track B)

## What you are deciding

For each row in `review_pack.jsonl`, decide whether the model's emitted output
states the registered answer. Return exactly one `semantic_label`:

- `correct` - the output's final answer matches the registered answer.
- `incorrect` - the output's final answer is present but does not match.
- `unresolved` - you cannot decide (no answer, truncated mid-answer, or genuinely
  ambiguous). Do not guess.

## What you must not do

- Do not judge the reasoning, style, or verbosity. Only the stated final answer matters.
- Do not infer an answer the model did not state.
- Do not make any claim about hidden reasoning, internal state, or "J-space".
  This pack is capability calibration only.

## Blinding

Rows are deliberately blinded to the deterministic screening verdict. The
screening labels live in `deterministic_triage.jsonl` and exist only for audit
and arbitration. Do not read them before you label.

## Output format

Write JSON Lines to a file the orchestrator can ingest. One object per row:

```
{"review_id": "R001", "record_id": "<record id>", "semantic_label": "correct",
 "reviewer_id": "<your id>", "notes": ""}
```

`record_id` is mandatory and must be copied exactly from the review row.

## Arbitration

If your label conflicts with the deterministic screening verdict, the row is
written to `arbitration_packet.jsonl` and an arbiter resolves it. An arbiter is
never invoked otherwise.
"""


ATTESTATION_RECOVERY_EVIDENCE: dict[str, Any] = {
    "checked_sources": {
        "acr": (
            "repositories are exactly j-space-observation, "
            "j-space-observation-jlens and j-space-observation-parser-eval; no "
            "calibration repository exists, and ACR run records do not carry "
            "the attestation payload"
        ),
        "blob_build_artifacts": "no Blob build artifact carries the attestation",
        "git_history": (
            "git log --all -- .semantic_audit_build_provenance.json returns "
            "nothing; the file is gitignored (.gitignore:50) and was never "
            "committed on any branch"
        ),
        "registered_generator": (
            "scripts/prepare_semantic_audit_build_context.py --protocol-commit, "
            "invoked correctly as python -I -S in a clean detached worktree at "
            "a91db884179911329eae3aadee506ab09b3a0e26, exits with 'tracked "
            "behavior file list differs from the frozen list' and writes no "
            "attestation file"
        ),
        "working_tree": (
            "the only *provenance* file present is an unrelated local parser "
            "recovery note"
        ),
    },
    "generator_equality_measurement": {
        "extra_files_not_in_frozen_list": 33,
        "frozen_runtime_files": 30,
        "measured_at_commit": "a91db884179911329eae3aadee506ab09b3a0e26",
        "missing_files_from_tree": 0,
        "scope": (
            "git ls-files -- src scripts infra/azure/scripts Dockerfile "
            "requirements.txt docs/phase1_semantic_review_protocol.md"
        ),
        "tracked_behavior_files": 63,
    },
    "outcome": "unrecoverable_and_unregenerable",
    "verified_by": "main agent (Azure and git-write authority)",
}

EXECUTION_IMPLEMENTATION_CHANGES: tuple[dict[str, str], ...] = (
    {
        "change": (
            "A dedicated calibration container image (Dockerfile.calibration) was "
            "introduced for this run."
        ),
        "effect_on_protocol": "none",
        "reason": (
            "The generic image requires a historical build attestation that is "
            "unrecoverable from git history, ACR and Blob, and is unregenerable "
            "because the registered generator asserts equality against a "
            "30-file frozen list while the repository now tracks 63 behavior "
            "files (33 extra, 0 missing). The calibration image carries its own "
            "pre-committed, deterministic build provenance instead."
        ),
        "scope": "execution_implementation",
    },
    {
        "change": (
            "cell_selection/ additionally emits high_accuracy_controls.csv and "
            "difficulty_boundaries.csv."
        ),
        "effect_on_protocol": "none",
        "reason": (
            "Both files are derived views of rows already classified by the "
            "frozen selection rule; no threshold, gate or classification "
            "changed."
        ),
        "scope": "execution_implementation",
    },
    {
        "change": (
            "The artifact pack is uploaded by headroom_blob_transport, which "
            "writes artifact_manifest.json last."
        ),
        "effect_on_protocol": "none",
        "reason": (
            "The generic directory uploader walks the pack in filesystem order "
            "and cannot guarantee the registered manifest-last rule."
        ),
        "scope": "execution_implementation",
    },
    {
        "change": (
            "04_decision.json additionally carries track_b_decision and "
            "track_b_decision_vocabulary."
        ),
        "effect_on_protocol": "none",
        "reason": (
            "The registered status vocabulary (BLOCKED / INCONCLUSIVE / "
            "COMPLETE / FAIL) is emitted unchanged. track_b_decision is a "
            "deterministic reporting view over the already-frozen cell "
            "classifications and applies no additional rule."
        ),
        "scope": "execution_implementation",
    },
)


def _artifact_entry(
    path: str,
    digest: str,
    size: int,
    status: str = "generated",
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "bytes": size,
        "path": path,
        "reason": reason or "",
        "sha256": digest,
        "status": status,
    }


def _emit(
    root: Path,
    relative: str,
    text: str,
    entries: list[dict[str, Any]],
    status: str = "generated",
    reason: str | None = None,
) -> None:
    digest = write_text(root / relative, text)
    entries.append(
        _artifact_entry(relative, digest, len(text.encode("utf-8")), status, reason)
    )


def run_calibration(config: RunConfig) -> dict[str, Any]:
    """Execute one calibration stage and emit the complete artifact pack."""

    if config.mode not in MODES:
        raise HeadroomCalibrationError(
            f"unknown mode {config.mode!r}; expected one of {', '.join(MODES)}"
        )

    bank_records = load_task_bank(config.bank_path)
    items = select_calibration_items(bank_records)
    selection = selection_summary(items)
    bank_sha = candidate_bank_sha256(bank_records)
    snapshot = protocol_snapshot(bank_sha, selection)
    digest = protocol_hash(snapshot)
    run_id = config.run_id or f"p10c-trackb-{config.mode}-{digest[:12]}"

    units = plan_work_units(items)
    if len(units) != EXPECTED_GENERATION_COUNT:
        raise HeadroomCalibrationError(
            f"planned {len(units)} generations; expected {EXPECTED_GENERATION_COUNT}"
        )

    deviations: list[dict[str, Any]] = []
    primary_judgments: dict[str, dict[str, Any]] = {}
    arbiter_judgments: dict[str, dict[str, Any]] = {}

    if config.mode == "finalize":
        if config.records_path is None:
            raise HeadroomCalibrationError("finalize mode requires --records")
        records = load_records(config.records_path)
        primary_judgments = load_judgments(config.judgments_path)
        arbiter_judgments = load_judgments(config.arbiter_judgments_path)
    elif config.mode == "plan":
        records = build_records(run_id, units, {})
        annotate_review_selection(records)
    else:
        backend = config.backend
        if backend is None:
            if config.mode == "self-test":
                backend = SelfTestBackend()
            else:
                backend = TransformersBackend()
        outputs = run_generations(units, backend)
        records = build_records(run_id, units, outputs)
        annotate_review_selection(records)
        if config.mode == "self-test":
            primary_judgments = {
                str(record["record_id"]): {
                    "record_id": str(record["record_id"]),
                    "reviewer_id": "self_test_synthetic_reviewer",
                    "semantic_label": _deterministic_label(record["evaluation"])
                    or "unresolved",
                }
                for record in records
                if record["evaluation"]["review_required"]
            }
            deviations.append(
                {
                    "deviation": "self-test mode used a scripted offline backend and "
                    "synthetic reviewer labels",
                    "effect": "artifacts are structural fixtures only and carry no "
                    "scientific content",
                    "registered": True,
                }
            )

    for record in records:
        record["run_id"] = run_id

    records = apply_judgments(records, primary_judgments, arbiter_judgments)
    review_rows, triage_rows = build_review_pack(run_id, records)
    arbitration = build_arbitration_packet(run_id, records, review_rows, primary_judgments)
    cells = score_cells(records)
    metrics_rows = build_metrics_rows(run_id, records, cells)
    pending_review_cells = supplementary_review_cells(cells)

    selected_cells = [cell for cell in cells if cell["selected"]]
    unresolved_rows = sum(
        1
        for record in records
        if record["status"] != STATUS_PLANNED
        and record["evaluation"]["final_correct"] is None
    )
    outstanding_reviews = sum(
        1
        for record in records
        if record["evaluation"]["review_required"]
        and record["evaluation"]["semantic_label_source"]
        not in {LABEL_SOURCE_PRIMARY, LABEL_SOURCE_ARBITER}
    )

    decision = _build_decision(
        config.mode,
        records,
        cells,
        selected_cells,
        unresolved_rows,
        outstanding_reviews,
        pending_review_cells,
        arbitration,
        deviations,
    )

    started = utc_timestamp(config.frozen_time)
    code_commit = config.code_commit or resolve_code_commit(config.repo_root)
    root = Path(config.output_root) / run_id
    root.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []

    stage_manifest = {
        "code_commit": code_commit,
        "end_time_utc": utc_timestamp(config.frozen_time),
        "hardware": config.hardware,
        "hypothesis": (
            "At least one family x band x condition cell yields adjudicated accuracy in "
            "[0.70, 0.90] with acceptable truncation and no-answer rates, providing "
            "measurable headroom for later interventions."
        ),
        "image_digest": config.image_digest,
        "inputs": {
            "conditions": list(CONDITIONS),
            "judgments": _display_path(config.judgments_path, config.repo_root),
            "arbiter_judgments": _display_path(
                config.arbiter_judgments_path, config.repo_root
            ),
            "records": _display_path(config.records_path, config.repo_root),
            "task_bank": _display_path(config.bank_path, config.repo_root),
            "task_bank_sha256": bank_sha,
        },
        "mode": config.mode,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "objective": (
            "Screen the frozen Phase 1 task bank for cells with measurable observable "
            "answer headroom under two visible-reasoning conditions."
        ),
        "out_of_scope": list(PROHIBITED_INTERPRETATIONS),
        "output_files": list(ARTIFACT_FILES),
        "phase": PHASE,
        "protocol_hash": digest,
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "scope": [
            "Deterministic 150-item selection from the frozen calibration split.",
            "Two visible-reasoning conditions; 300 single-sample generations.",
            "Deterministic triage plus bounded semantic adjudication.",
            "Headroom cell selection and exclusion with machine-readable reasons.",
        ],
        "start_time_utc": started,
        "status": decision["status"],
        "subagents": [
            {"role": "primary_semantic_reviewer", "invoked": bool(primary_judgments)},
            {"role": "arbiter", "invoked": bool(arbiter_judgments)},
        ],
        "track": TRACK,
    }

    _emit(root, "00_stage_manifest.json", canonical_json(stage_manifest), entries)
    _emit(root, "01_protocol_snapshot.json", canonical_json(snapshot), entries)
    _emit(root, "02_records.jsonl", canonical_jsonl(records), entries)
    _emit(
        root,
        "03_metrics.csv",
        canonical_csv(METRICS_HEADER, metrics_rows),
        entries,
    )
    _emit(root, "04_decision.json", canonical_json(decision), entries)

    scored = [cell for cell in cells if cell["accuracy"] is not None]
    if scored:
        paper_rows = [
            [
                run_id,
                cell["task_family"],
                cell["difficulty_band"],
                cell["condition"],
                cell["n"],
                cell["correct"],
                cell["accuracy"],
                cell["ci_lower"],
                cell["ci_upper"],
                cell["truncation_rate"],
                cell["no_answer_rate"],
                cell["classification"],
            ]
            for cell in scored
        ]
        figure_rows = [
            [
                run_id,
                cell["condition"],
                f"{cell['task_family']}|{cell['difficulty_band']}",
                cell["accuracy"],
                cell["ci_lower"],
                cell["ci_upper"],
                cell["n"],
                cell["classification"],
            ]
            for cell in scored
        ]
        paper_text = canonical_csv(PAPER_TABLE_HEADER, paper_rows)
        figure_text = canonical_csv(FIGURE_DATA_HEADER, figure_rows)
        _emit(root, "06_paper_table.csv", paper_text, entries)
        _emit(root, "07_figure_data.csv", figure_text, entries)
    else:
        reason = "no semantically adjudicated cell accuracy is available yet"
        _emit(
            root,
            "06_paper_table.csv",
            _not_applicable_csv(reason),
            entries,
            "not_applicable",
            reason,
        )
        _emit(
            root,
            "07_figure_data.csv",
            _not_applicable_csv(reason),
            entries,
            "not_applicable",
            reason,
        )

    deviations_payload = {
        "deviations": deviations,
        "effect_on_interpretation": "none" if not deviations else "documented_above",
        "execution_implementation_changes": [
            dict(change) for change in EXECUTION_IMPLEMENTATION_CHANGES
        ],
        "protocol_deviation": "none",
        "semantic_audit_attestation_evidence": deepcopy(
            ATTESTATION_RECOVERY_EVIDENCE
        ),
        "unregistered_changes": [],
    }
    _emit(root, "08_deviations.json", canonical_json(deviations_payload), entries)

    _emit_review_pack(root, run_id, review_rows, triage_rows, arbitration, entries)
    _emit_cell_selection(root, run_id, cells, entries)

    summary_text = _summary_markdown(
        run_id,
        config,
        stage_manifest,
        snapshot,
        selection,
        records,
        cells,
        review_rows,
        decision,
    )
    _emit(root, "05_summary.md", summary_text, entries)

    manifest = {
        "artifact_count": len(entries) + 1,
        "code_commit": code_commit,
        "files": sorted(entries, key=lambda entry: str(entry["path"])),
        "generated_at_utc": utc_timestamp(config.frozen_time),
        "image_digest": config.image_digest,
        "mode": config.mode,
        "phase": PHASE,
        "protocol_hash": digest,
        "required_files": list(ARTIFACT_FILES),
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "status": decision["status"],
        "track": TRACK,
    }
    write_text(root / "artifact_manifest.json", canonical_json(manifest))

    return {
        "cells": cells,
        "decision": decision,
        "manifest": manifest,
        "output_dir": root,
        "records": records,
        "review_rows": review_rows,
        "run_id": run_id,
        "selection": selection,
    }


def _emit_review_pack(
    root: Path,
    run_id: str,
    review_rows: Sequence[Mapping[str, Any]],
    triage_rows: Sequence[Mapping[str, Any]],
    arbitration: Sequence[Mapping[str, Any]],
    entries: list[dict[str, Any]],
) -> None:
    """Emit the bounded review pack as files the main agent can hand to a reviewer."""

    if review_rows:
        pack_text = canonical_jsonl(review_rows)
        triage_text = canonical_jsonl(triage_rows)
        _emit(root, f"{REVIEW_PACK_DIR}/review_pack.jsonl", pack_text, entries)
        _emit(root, f"{REVIEW_PACK_DIR}/deterministic_triage.jsonl", triage_text, entries)
    else:
        reason = "no row met a mandatory review category"
        _emit(
            root,
            f"{REVIEW_PACK_DIR}/review_pack.jsonl",
            _not_applicable_jsonl(reason),
            entries,
            "not_applicable",
            reason,
        )
        _emit(
            root,
            f"{REVIEW_PACK_DIR}/deterministic_triage.jsonl",
            _not_applicable_jsonl(reason),
            entries,
            "not_applicable",
            reason,
        )

    reason_counts: dict[str, int] = {}
    for row in review_rows:
        for reason_code in row["review_reasons"]:
            reason_counts[str(reason_code)] = reason_counts.get(str(reason_code), 0) + 1
    pack_manifest = {
        "arbitration_rows": len(arbitration),
        "blinding": "primary review rows omit the deterministic screening verdict",
        "parser_v2_locked_validation_status": PARSER_V2_LOCKED_VALIDATION_STATUS,
        "review_reason_codes": list(REVIEW_REASON_CODES),
        "review_reason_counts": dict(sorted(reason_counts.items())),
        "review_row_count": len(review_rows),
        "review_sample_fraction": REVIEW_SAMPLE_FRACTION,
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "triage_authority": TRIAGE_AUTHORITY,
    }
    _emit(
        root,
        f"{REVIEW_PACK_DIR}/review_pack_manifest.json",
        canonical_json(pack_manifest),
        entries,
    )
    _emit(root, f"{REVIEW_PACK_DIR}/review_instructions.md", REVIEW_INSTRUCTIONS, entries)

    if arbitration:
        _emit(
            root,
            f"{REVIEW_PACK_DIR}/arbitration_packet.jsonl",
            canonical_jsonl(arbitration),
            entries,
        )
    else:
        reason = "no primary reviewer conflicted with the deterministic result"
        _emit(
            root,
            f"{REVIEW_PACK_DIR}/arbitration_packet.jsonl",
            _not_applicable_jsonl(reason),
            entries,
            "not_applicable",
            reason,
        )


def _emit_classification_view(
    root: Path,
    run_id: str,
    cells: Sequence[Mapping[str, Any]],
    entries: list[dict[str, Any]],
    filename: str,
    classification: str,
    empty_reason: str,
) -> None:
    """Emit a derived per-classification view of the already-scored cells.

    These files are views over ``excluded_cells.csv``; they apply no additional
    rule and change no threshold.
    """

    matching = [cell for cell in cells if cell["classification"] == classification]
    if matching:
        _emit(
            root,
            f"{CELL_SELECTION_DIR}/{filename}",
            canonical_csv(
                EXCLUDED_CELL_HEADER,
                [
                    _cell_row(cell, run_id) + [";".join(cell["exclusion_reasons"])]
                    for cell in matching
                ],
            ),
            entries,
        )
    else:
        _emit(
            root,
            f"{CELL_SELECTION_DIR}/{filename}",
            _not_applicable_csv(empty_reason),
            entries,
            "not_applicable",
            empty_reason,
        )


def _emit_cell_selection(
    root: Path,
    run_id: str,
    cells: Sequence[Mapping[str, Any]],
    entries: list[dict[str, Any]],
) -> None:
    """Emit selected/excluded cell tables and machine-readable exclusion reasons."""

    selected = [cell for cell in cells if cell["selected"]]
    excluded = [cell for cell in cells if not cell["selected"]]

    if selected:
        _emit(
            root,
            f"{CELL_SELECTION_DIR}/selected_headroom_cells.csv",
            canonical_csv(
                SELECTED_CELL_HEADER, [_cell_row(cell, run_id) for cell in selected]
            ),
            entries,
        )
    else:
        reason = "no cell satisfied every headroom qualification rule"
        _emit(
            root,
            f"{CELL_SELECTION_DIR}/selected_headroom_cells.csv",
            _not_applicable_csv(reason),
            entries,
            "not_applicable",
            reason,
        )

    if excluded:
        _emit(
            root,
            f"{CELL_SELECTION_DIR}/excluded_cells.csv",
            canonical_csv(
                EXCLUDED_CELL_HEADER,
                [
                    _cell_row(cell, run_id) + [";".join(cell["exclusion_reasons"])]
                    for cell in excluded
                ],
            ),
            entries,
        )
    else:
        reason = "every scored cell qualified"
        _emit(
            root,
            f"{CELL_SELECTION_DIR}/excluded_cells.csv",
            _not_applicable_csv(reason),
            entries,
            "not_applicable",
            reason,
        )

    _emit_classification_view(
        root,
        run_id,
        cells,
        entries,
        "high_accuracy_controls.csv",
        "control_sanity_high_accuracy",
        "no cell exceeded the 0.90 accuracy band as a high-accuracy control",
    )
    _emit_classification_view(
        root,
        run_id,
        cells,
        entries,
        "difficulty_boundaries.csv",
        "difficulty_boundary_excluded",
        "no cell fell below the 0.70 accuracy band as a difficulty boundary",
    )

    reasons_payload = {
        "cells": {
            str(cell["cell_id"]): {
                "accuracy": cell["accuracy"],
                "classification": cell["classification"],
                "exclusion_reasons": list(cell["exclusion_reasons"]),
                "selected": cell["selected"],
            }
            for cell in cells
        },
        "reason_code_definitions": {
            "accuracy_above_band_control_only": (
                "Accuracy exceeds 0.90; usable as a sanity/control cell but "
                "deprioritized as a main ablation cell because damage headroom is small."
            ),
            "accuracy_below_band_difficulty_boundary": (
                "Accuracy is below 0.70; excluded from main patching/ablation but "
                "retained as a difficulty boundary."
            ),
            "incomplete_cell_n": "The cell does not contain exactly 10 scored items.",
            "incomplete_review_coverage": (
                "At least one row flagged for review has no adjudicated label, so the "
                "cell cannot be selected on screening evidence alone."
            ),
            "insufficient_correct_count": "Fewer than 7 of 10 items were adjudicated correct.",
            "labels_not_semantically_adjudicated": (
                "The cell has rows without a final semantic label (for example a plan-only pack)."
            ),
            "no_answer_rate_above_threshold": "The no-answer rate exceeds 0.10.",
            "truncation_rate_above_threshold": "The truncation rate exceeds 0.10.",
            "unresolved_semantic_labels_present": "At least one row is labelled unresolved.",
        },
        "reason_codes": list(EXCLUSION_REASON_CODES),
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "supplementary_review_required": supplementary_review_cells(cells),
    }
    _emit(
        root,
        f"{CELL_SELECTION_DIR}/cell_exclusion_reasons.json",
        canonical_json(reasons_payload),
        entries,
    )


def _track_b_decision(
    status: str,
    cells: Sequence[Mapping[str, Any]],
    selected_cells: Sequence[Mapping[str, Any]],
) -> str:
    """Map the frozen cell classifications onto the Track B outcome vocabulary."""

    if status != "COMPLETE":
        return "INCONCLUSIVE"
    if selected_cells:
        return "HEADROOM_CELLS_SELECTED"
    if any(
        cell["classification"] == "control_sanity_high_accuracy" for cell in cells
    ):
        return "CONTROLS_ONLY"
    return "NO_USABLE_CELLS"


def _build_decision(
    mode: str,
    records: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    selected_cells: Sequence[Mapping[str, Any]],
    unresolved_rows: int,
    outstanding_reviews: int,
    pending_review_cells: Sequence[str],
    arbitration: Sequence[Mapping[str, Any]],
    deviations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive the stage decision from the frozen rules."""

    criteria_passed: list[str] = []
    criteria_failed: list[str] = []
    criteria_not_applicable: list[dict[str, str]] = []

    planned_rows = sum(1 for record in records if record["status"] == STATUS_PLANNED)
    error_rows = sum(
        1 for record in records if record["status"] == STATUS_GENERATION_ERROR
    )

    if len(records) == EXPECTED_GENERATION_COUNT:
        criteria_passed.append("generation_plan_size_is_300")
    else:
        criteria_failed.append("generation_plan_size_is_300")

    if mode == "plan":
        status = "BLOCKED"
        decision_text = (
            "Plan-only pack. The 150-item selection, the 300-unit generation plan, the "
            "prompts, and the frozen seeds are registered; no model was executed here."
        )
        next_gate = (
            "Main agent executes the registered Azure GPU container job, then reruns this "
            "module in generate mode."
        )
        criteria_not_applicable.extend(
            [
                {
                    "criterion": "semantic_accuracy_per_cell",
                    "reason": "no generations were produced in plan mode",
                },
                {
                    "criterion": "headroom_cell_selection",
                    "reason": "no generations were produced in plan mode",
                },
            ]
        )
    elif mode == "generate":
        status = "INCONCLUSIVE"
        decision_text = (
            "Generations complete and deterministically triaged. Final calibration labels "
            "are withheld until the bounded semantic review pack is adjudicated, because "
            "parser v2 is not locked-validated and may not decide labels."
        )
        next_gate = (
            "Main agent hands review_pack/ to a semantic reviewer agent, then reruns this "
            "module in finalize mode with the returned judgments."
        )
        criteria_not_applicable.append(
            {
                "criterion": "headroom_cell_selection",
                "reason": "semantic adjudication has not been ingested yet",
            }
        )
    else:
        if planned_rows:
            status = "INCONCLUSIVE"
            decision_text = "Pack still contains unexecuted rows."
            next_gate = "Execute the remaining generations before finalizing."
        elif outstanding_reviews or unresolved_rows:
            status = "INCONCLUSIVE"
            decision_text = (
                f"{outstanding_reviews} flagged row(s) lack an adjudicated label and "
                f"{unresolved_rows} row(s) remain unresolved, so cell selection is not final."
            )
            next_gate = (
                "Return the outstanding review rows (and any arbitration packet) for "
                "adjudication, then rerun finalize."
            )
            criteria_failed.append("all_flagged_rows_adjudicated")
        else:
            status = "COMPLETE"
            criteria_passed.append("all_flagged_rows_adjudicated")
            if selected_cells:
                criteria_passed.append("at_least_one_selected_headroom_cell")
                decision_text = (
                    f"{len(selected_cells)} of {len(cells)} cells qualify as bounded "
                    "headroom cells under the frozen rule."
                )
                next_gate = (
                    "Main agent registers the selected cells as the eligible task pool for "
                    "later ablation and patching stages."
                )
            else:
                criteria_failed.append("at_least_one_selected_headroom_cell")
                decision_text = (
                    "No cell satisfied every headroom qualification rule; the task grid "
                    "needs revision or a different difficulty ladder before ablation."
                )
                next_gate = (
                    "Main agent decides whether to extend the task bank or relax the "
                    "registered accuracy band in a new preregistration."
                )

    if pending_review_cells:
        criteria_failed.append("no_cell_blocked_solely_by_review_coverage")
    if error_rows:
        criteria_failed.append("no_generation_errors")
    elif mode != "plan":
        criteria_passed.append("no_generation_errors")

    return {
        "arbitration_rows": len(arbitration),
        "criteria_failed": sorted(set(criteria_failed)),
        "criteria_not_applicable": criteria_not_applicable,
        "criteria_passed": sorted(set(criteria_passed)),
        "decision": decision_text,
        "deviations": list(deviations),
        "next_gate": next_gate,
        "prohibited_interpretations": list(PROHIBITED_INTERPRETATIONS),
        "scientific_interpretation": SCIENTIFIC_CLAIM_BOUNDARY,
        "selected_headroom_cells": [str(cell["cell_id"]) for cell in selected_cells],
        "status": status,
        "supplementary_review_required": list(pending_review_cells),
        "track_b_decision": _track_b_decision(status, cells, selected_cells),
        "track_b_decision_vocabulary": list(TRACK_B_DECISIONS),
        "unresolved_rows": unresolved_rows,
    }
