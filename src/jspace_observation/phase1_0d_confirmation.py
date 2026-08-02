"""Phase 1.0D confirmation protocol — repaired headroom + strict-no-CoT calibration.

Phase 1.0C (``artifacts/phase1-headroom-calibration/track-b/20260725T170041Z``)
is preserved unchanged and keeps its ``COMPLETE_INCONCLUSIVE`` status.  This
module is a *new* protocol in a *new* artifact namespace.  It repairs the two
recomputed generation-profile defects recorded in
``docs/phase1_0c_generation_profile_defects.json``:

``P10C-D1``
    every 1.0C prompt carried the literal format line ``Final answer: <answer>``,
    so a model that copied the format emitted the placeholder instead of a value;

``P10C-D2``
    every 1.0C condition ran at ``max_new_tokens=512``, so a row that reached the
    cap had no final-answer surface to read.

Nothing here measures hidden reasoning, an internal workspace, invisible
chain-of-thought, or "J-space".  The unit of analysis is the emitted output text
and its semantically adjudicated correctness.  The count gates in this module
select substrates for a later mechanistic pilot; they are not population
performance claims.

Every rule that could bias a result — item selection, prompt rendering, decoding,
adjudication, and the cell decision — is frozen in this module *before* any
target-model generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .headroom_calibration import (
    MODEL_ID,
    MODEL_REVISION,
    canonical_json,
    sha256_text,
    wilson_ci,
)
from .headroom_candidates import (
    DIFFICULTY_BANDS,
    TASK_FAMILIES,
)
from .no_cot import (
    ConditionGenerationConfig,
    construct_answer_only_prompt,
    construct_empty_think_prefill_prompt,
    construct_r1_style_thinking_prompt,
    get_generation_config_for_condition,
    validate_phase1_conditions,
)
from .phase1_branches import (
    PREFILL_INTERVENTION_BRANCH,
    PROMPT_ONLY_RAW_STRICT_BRANCH,
    VISIBLE_REASONING_BASELINE_BRANCH,
)

# --------------------------------------------------------------------------
# Frozen protocol identity
# --------------------------------------------------------------------------

SCHEMA_VERSION = "phase1-headroom-confirmation-v1"
PROTOCOL_VERSION = "phase1-headroom-confirmation-protocol-v1"
PHASE = "1.0D"
TRACK = "track-b"

#: The 1.0C namespace this protocol must never write into.
PRESERVED_PHASE_1_0C_PACK = (
    "artifacts/phase1-headroom-calibration/track-b/20260725T170041Z"
)
#: The new namespace.  A run stamps its own UTC run id underneath this root.
ARTIFACT_ROOT = "artifacts/phase1-headroom-confirmation/track-b"

DEFAULT_BANK_PATH = "data/phase1_task_headroom_candidates.jsonl"
REPO_ROOT = Path(__file__).resolve().parents[2]

#: Phase 1.0C consumed the ``calibration`` split.  1.0D must be disjoint from it.
PHASE_1_0C_SPLIT = "calibration"
#: Splits eligible for the confirmation sample, in the order they are drawn.
ELIGIBLE_SPLITS: tuple[str, ...] = ("confirmation", "mechanistic")

ITEMS_PER_CELL = 20
EXPECTED_CELL_COUNT = len(TASK_FAMILIES) * len(DIFFICULTY_BANDS)
EXPECTED_ITEM_COUNT = EXPECTED_CELL_COUNT * ITEMS_PER_CELL

SELECTION_SEED = 20260802
RUN_BASE_SEED = 20260802
REPLICATE_INDEX = 0
SAMPLES_PER_ITEM = 1


class Phase1_0DError(ValueError):
    """Raised when a Phase 1.0D input or invariant violates the frozen protocol."""


class Phase1_0DBankShortage(Phase1_0DError):
    """Raised when the public bank cannot supply the registered disjoint split.

    Per the controlling authority this stops the run *before* inference.  It is a
    recorded shortage, never a licence to shrink a cell, reuse a Phase 1.0C item,
    or select a replacement using model or lens output.
    """


# --------------------------------------------------------------------------
# Frozen condition arms
# --------------------------------------------------------------------------

#: Text appended to the visible-reasoning control only.
#:
#: It supersedes the frozen bank's "answer only" closing, and — unlike the Phase
#: 1.0C override — it never shows a placeholder to copy.  The anti-placeholder
#: sentence is part of the registered instruction, not a post hoc filter.
VISIBLE_REASONING_OVERRIDE_ID = "phase1_0d_visible_override_v1"
VISIBLE_REASONING_OVERRIDE_TEXT = (
    "\n\nFormat override for this run (supersedes any earlier instruction in this "
    "prompt that tells you not to explain or to answer only): you may reason "
    "first, then end your reply with a single final line that starts with "
    "'Final answer:' followed by the answer value itself.\n"
    "Write the value, not a description of it. Do not write angle brackets. Do "
    "not write a placeholder. Do not write an XML or HTML tag. Do not write the "
    "word 'answer' in place of the value. If the answer is the number 42, the "
    "final line is exactly:\n"
    "Final answer: 42"
)

#: A generation-time stop may only fire after a complete registered final-answer
#: surface.  Text is never clipped after the fact and called the model output.
FINAL_ANSWER_PREFIX = "Final answer:"

VISIBLE_MAX_NEW_TOKENS = 1024
STRICT_MAX_NEW_TOKENS = 32

#: Why 32 is provably enough for the answer and provably too little for CoT.
#:
#: The pinned tokenizer is byte-level BPE, so no token ever covers less than one
#: UTF-8 byte and the token count of a string is bounded above by its byte
#: length.  ``assert_strict_budget_fits_every_answer`` checks every registered
#: answer in the bank against this bound, which makes the budget verifiable
#: without downloading the tokenizer.  32 tokens is at the same time far too few
#: for the step-by-step reasoning the strict conditions must not be able to emit.
STRICT_BUDGET_RATIONALE = (
    "byte-level BPE guarantees token_count <= utf8_byte_length, so a budget that "
    "exceeds the longest registered answer in bytes is sufficient for the answer; "
    "32 new tokens is simultaneously far below any visible chain of thought"
)


@dataclass(frozen=True)
class ConditionArm:
    """One frozen experimental arm."""

    arm_id: str
    condition: str
    branch: str
    role: str
    max_new_tokens: int
    renderer: str
    permits_visible_reasoning: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "branch": self.branch,
            "condition": self.condition,
            "max_new_tokens": self.max_new_tokens,
            "permits_visible_reasoning": self.permits_visible_reasoning,
            "renderer": self.renderer,
            "role": self.role,
        }


VISIBLE_CONTROL_ARM = ConditionArm(
    arm_id="visible_reasoning_control",
    condition="r1_style_thinking",
    branch=VISIBLE_REASONING_BASELINE_BRANCH,
    role="visible-reasoning capability control",
    max_new_tokens=VISIBLE_MAX_NEW_TOKENS,
    renderer="construct_r1_style_thinking_prompt + phase1_0d_visible_override_v1",
    permits_visible_reasoning=True,
)

STRUCTURAL_NO_COT_ARM = ConditionArm(
    arm_id="structural_no_cot",
    condition="strict_answer_only_empty_think_prefill",
    branch=PREFILL_INTERVENTION_BRANCH,
    role="primary structural no-CoT condition",
    max_new_tokens=STRICT_MAX_NEW_TOKENS,
    renderer="render_empty_think_prefill_metadata (chat template)",
    permits_visible_reasoning=False,
)

SPONTANEOUS_NO_COT_ARM = ConditionArm(
    arm_id="spontaneous_no_cot",
    condition="strict_answer_only",
    branch=PROMPT_ONLY_RAW_STRICT_BRANCH,
    role="primary spontaneous surface no-CoT condition",
    max_new_tokens=STRICT_MAX_NEW_TOKENS,
    renderer="construct_answer_only_prompt",
    permits_visible_reasoning=False,
)

ARMS: tuple[ConditionArm, ...] = (
    VISIBLE_CONTROL_ARM,
    STRUCTURAL_NO_COT_ARM,
    SPONTANEOUS_NO_COT_ARM,
)
ARMS_BY_ID: dict[str, ConditionArm] = {arm.arm_id: arm for arm in ARMS}
CONDITIONS: tuple[str, ...] = tuple(arm.condition for arm in ARMS)

#: All three arms use the project's registered greedy decoding profile
#: (``temperature=0.0``/``1.0`` as registered, ``do_sample=False``).  The arms
#: therefore differ only in renderer and token budget, not in sampling
#: behaviour, so a paired difference between them is not a decoding artifact.
DECODING_MATCHED_GREEDY = True


# --------------------------------------------------------------------------
# Prohibited prompt content
# --------------------------------------------------------------------------

LITERAL_ANSWER_PLACEHOLDER = "<answer>"
#: ``{slot}``-shaped text that survived template expansion.
UNEXPANDED_TEMPLATE_TOKEN = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
#: Any angle-bracketed placeholder standing in for a value.
ANGLE_BRACKET_PLACEHOLDER = re.compile(r"<[A-Za-z_][A-Za-z0-9_ -]*>")
EMPTY_THINK_MARKERS: tuple[str, ...] = ("<think>", "</think>")


def prompt_defects(prompt: str, arm: ConditionArm) -> list[str]:
    """Return the frozen prohibitions a rendered prompt violates.

    The visible control is allowed to name ``<think>`` because its registered
    renderer offers R1-style thinking; it is never allowed to show a value
    placeholder.  The spontaneous strict arm may contain neither.
    """

    defects: list[str] = []
    if LITERAL_ANSWER_PLACEHOLDER in prompt:
        defects.append("literal_answer_placeholder")
    if UNEXPANDED_TEMPLATE_TOKEN.search(prompt):
        defects.append("unexpanded_template_token")

    allowed_angle = set(EMPTY_THINK_MARKERS) if arm is not SPONTANEOUS_NO_COT_ARM else set()
    for match in ANGLE_BRACKET_PLACEHOLDER.findall(prompt):
        if match not in allowed_angle:
            defects.append(f"angle_bracket_placeholder:{match}")

    if arm is SPONTANEOUS_NO_COT_ARM:
        for marker in EMPTY_THINK_MARKERS:
            if marker in prompt:
                defects.append(f"think_tag_in_raw_strict:{marker}")
    if not arm.permits_visible_reasoning:
        if VISIBLE_REASONING_OVERRIDE_TEXT.strip() and (
            VISIBLE_REASONING_OVERRIDE_ID in prompt
            or "Format override for this run" in prompt
        ):
            defects.append("visible_reasoning_override_leaked_into_strict_arm")
    return defects


def render_prompt(question: str, arm: ConditionArm) -> str:
    """Render the frozen prompt for one item under one arm.

    The frozen bank text is never mutated.  Strict arms use the project's
    existing registered no-CoT renderers and never inherit the visible override.
    """

    validate_phase1_conditions((arm.condition,))
    if arm is VISIBLE_CONTROL_ARM:
        return construct_r1_style_thinking_prompt(question) + VISIBLE_REASONING_OVERRIDE_TEXT
    if arm is STRUCTURAL_NO_COT_ARM:
        return construct_empty_think_prefill_prompt(question)
    if arm is SPONTANEOUS_NO_COT_ARM:
        return construct_answer_only_prompt(question)
    raise Phase1_0DError(f"arm {arm.arm_id!r} is not registered for Phase 1.0D")


def generation_config(arm: ConditionArm) -> ConditionGenerationConfig:
    """Return the arm's decoding profile with the Phase 1.0D budget registered.

    The decoding parameters come from the project's registered per-condition
    configuration so the arms stay decoding-matched.  Only the token budget is
    re-registered for 1.0D, and the profile is renamed so a 1.0D config can never
    be mistaken for the 8- or 12-token profile it replaces.
    """

    base = get_generation_config_for_condition(arm.condition, arm.max_new_tokens)
    return ConditionGenerationConfig(
        max_new_tokens=arm.max_new_tokens,
        temperature=base.temperature,
        top_p=base.top_p,
        do_sample=base.do_sample,
        decoding_profile=f"phase1_0d_{arm.arm_id}_max{arm.max_new_tokens}",
    )


def assert_strict_budget_fits_every_answer(
    items: Iterable[Mapping[str, Any]],
    *,
    budget: int = STRICT_MAX_NEW_TOKENS,
) -> dict[str, Any]:
    """Verify the strict budget can hold every registered answer.

    Uses the byte-length upper bound on byte-level BPE token counts, so the check
    needs no tokenizer download and cannot be wrong in the permissive direction.
    """

    longest = 0
    longest_task_id = ""
    for item in items:
        answer = str(item["registered_answer"])
        byte_length = len(answer.encode("utf-8"))
        if byte_length > longest:
            longest = byte_length
            longest_task_id = str(item["task_id"])
    if longest >= budget:
        raise Phase1_0DError(
            f"registered answer for {longest_task_id!r} needs up to {longest} "
            f"tokens but the strict budget is {budget}"
        )
    return {
        "budget": budget,
        "longest_answer_bytes": longest,
        "longest_answer_task_id": longest_task_id,
        "bound": "token_count <= utf8_byte_length for byte-level BPE",
        "headroom_tokens": budget - longest,
    }


# --------------------------------------------------------------------------
# Deterministic disjoint confirmation split
# --------------------------------------------------------------------------


def phase_1_0c_item_ids(records: Iterable[Mapping[str, Any]]) -> set[str]:
    """Return the item ids Phase 1.0C actually generated on."""

    used: set[str] = set()
    for record in records:
        item_id = record.get("source_item_id")
        if item_id:
            used.add(str(item_id))
    return used


def eligible_items(
    bank: Sequence[Mapping[str, Any]],
    used_item_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Return bank items that Phase 1.0D may use.

    An item is eligible only if it is outside the Phase 1.0C split *and* absent
    from the ids 1.0C actually generated on.  Both conditions are checked; the
    split label alone is a claim, the record ids are the evidence.
    """

    used = set(used_item_ids)
    eligible: list[dict[str, Any]] = []
    for item in bank:
        if str(item.get("split")) == PHASE_1_0C_SPLIT:
            continue
        if str(item.get("task_id")) in used:
            continue
        if item.get("task_family") not in TASK_FAMILIES:
            continue
        if item.get("difficulty_band") not in DIFFICULTY_BANDS:
            continue
        eligible.append(dict(item))
    return eligible


def _split_rank(split: str) -> int:
    try:
        return ELIGIBLE_SPLITS.index(split)
    except ValueError:  # pragma: no cover - filtered earlier
        return len(ELIGIBLE_SPLITS)


def cell_availability(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Return the eligible item count for every family x band cell."""

    counts = {
        f"{family}|{band}": 0 for family in TASK_FAMILIES for band in DIFFICULTY_BANDS
    }
    for item in items:
        key = f"{item['task_family']}|{item['difficulty_band']}"
        if key in counts:
            counts[key] += 1
    return counts


def select_confirmation_items(
    bank: Sequence[Mapping[str, Any]],
    used_item_ids: Iterable[str],
    *,
    items_per_cell: int = ITEMS_PER_CELL,
) -> list[dict[str, Any]]:
    """Select the frozen 5 x 3 x 20 confirmation sample deterministically.

    Ordering is total and reproducible without a random number generator: within
    a cell, ``confirmation`` items come before ``mechanistic`` items, and ties
    break on ``task_id``.  ``SELECTION_SEED`` is registered for downstream
    deterministic sampling only; it never influences which items are chosen.

    Raises ``Phase1_0DBankShortage`` if any cell cannot supply the full count.
    """

    eligible = eligible_items(bank, used_item_ids)
    availability = cell_availability(eligible)
    shortages = {
        cell: count for cell, count in availability.items() if count < items_per_cell
    }
    if shortages:
        raise Phase1_0DBankShortage(
            "the public bank cannot supply "
            f"{items_per_cell} disjoint items for: "
            + ", ".join(f"{cell}={count}" for cell, count in sorted(shortages.items()))
        )

    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in eligible:
        key = (str(item["task_family"]), str(item["difficulty_band"]))
        by_cell.setdefault(key, []).append(item)

    selected: list[dict[str, Any]] = []
    for family in TASK_FAMILIES:
        for band in DIFFICULTY_BANDS:
            cell = sorted(
                by_cell[(family, band)],
                key=lambda item: (_split_rank(str(item["split"])), str(item["task_id"])),
            )
            selected.extend(cell[:items_per_cell])

    task_ids = [str(item["task_id"]) for item in selected]
    if len(set(task_ids)) != len(task_ids):
        raise Phase1_0DError("selected confirmation items are not unique")
    if len(selected) != EXPECTED_CELL_COUNT * items_per_cell:
        raise Phase1_0DError(
            f"selected {len(selected)} items; expected "
            f"{EXPECTED_CELL_COUNT * items_per_cell}"
        )
    return selected


def selection_summary(
    items: Sequence[Mapping[str, Any]],
    used_item_ids: Iterable[str],
) -> dict[str, Any]:
    """Summarize the selection and prove disjointness from Phase 1.0C."""

    used = set(used_item_ids)
    task_ids = sorted(str(item["task_id"]) for item in items)
    per_split: dict[str, int] = {}
    for item in items:
        split = str(item["split"])
        per_split[split] = per_split.get(split, 0) + 1
    return {
        "item_count": len(task_ids),
        "items_per_cell": ITEMS_PER_CELL,
        "per_family_band": cell_availability(items),
        "per_split": dict(sorted(per_split.items())),
        "phase_1_0c_item_count": len(used),
        "overlap_with_phase_1_0c": sorted(set(task_ids) & used),
        "disjoint_from_phase_1_0c": not (set(task_ids) & used),
        "selection_seed": SELECTION_SEED,
        "task_ids": task_ids,
        "task_ids_sha256": sha256_text("\n".join(task_ids) + "\n"),
    }


# --------------------------------------------------------------------------
# Frozen adjudication rules (section 4.3)
# --------------------------------------------------------------------------

SEMANTIC_LABELS: tuple[str, ...] = (
    "correct",
    "incorrect",
    "no_answer",
    "invalid",
    "unresolved",
)

#: A parser may route a row.  It may never decide final correctness.
PARSER_ROLE = "routing_only"

SECONDARY_REVIEW_SAMPLE_FRACTION = 0.20
SECONDARY_REVIEW_DOMAIN = "jspace-phase1-0d/secondary-review/v1"


def requires_secondary_review(
    record_id: str,
    *,
    primary_label: str,
    parser_agrees_with_primary: bool,
    sample_fraction: float = SECONDARY_REVIEW_SAMPLE_FRACTION,
) -> bool:
    """Return whether a row must receive an isolated secondary review.

    Frozen rule: every primary ``unresolved``/``invalid`` row, every
    parser/reviewer disagreement, and a deterministic stratified sample of the
    remainder.  The sample is a hash of the record id, so it is fixed before any
    label exists and cannot be steered by an outcome.
    """

    if primary_label in {"unresolved", "invalid"}:
        return True
    if not parser_agrees_with_primary:
        return True
    digest = sha256_text(f"{SECONDARY_REVIEW_DOMAIN}|{record_id}")
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket < sample_fraction


ARBITRATION_RULE_ID = "phase1_0d_arbitration_v1"


def arbitrate(primary_label: str, secondary_label: str | None) -> dict[str, Any]:
    """Apply the frozen arbitration rule to one row.

    Agreement stands.  Disagreement is never averaged, never resolved toward the
    parser, and never resolved toward ``correct``: it escalates to an explicit
    third adjudication and stays ``unresolved`` until that adjudication exists.
    """

    for label in (primary_label, secondary_label):
        if label is not None and label not in SEMANTIC_LABELS:
            raise Phase1_0DError(f"label {label!r} is not a registered semantic label")
    if secondary_label is None:
        return {
            "rule": ARBITRATION_RULE_ID,
            "final_label": primary_label,
            "agreement": None,
            "arbitration_required": False,
        }
    if primary_label == secondary_label:
        return {
            "rule": ARBITRATION_RULE_ID,
            "final_label": primary_label,
            "agreement": True,
            "arbitration_required": False,
        }
    return {
        "rule": ARBITRATION_RULE_ID,
        "final_label": "unresolved",
        "agreement": False,
        "arbitration_required": True,
    }


# --------------------------------------------------------------------------
# Frozen metrics and cell gate (section 4.4)
# --------------------------------------------------------------------------

GATE_ID = "phase1_0d_rq2_pilot_candidate_v1"
GATE_REQUIRED_RESOLVED = ITEMS_PER_CELL
GATE_MIN_VISIBLE_CORRECT = 14
GATE_STRICT_CORRECT_LOW = 8
GATE_STRICT_CORRECT_HIGH = 18
GATE_MAX_TRUNCATION_RATE = 0.10
GATE_MAX_INVALID_RATE = 0.10

GATE_INTERPRETATION = (
    "These count gates select substrates for a later mechanistic pilot. They are "
    "not population performance claims, and a cell that fails the gate is still "
    "reported."
)

NO_HEADROOM_RESULT = "HEADROOM_NOT_ESTABLISHED"


@dataclass(frozen=True)
class CellOutcome:
    """The frozen per-cell summary for one condition arm."""

    task_family: str
    difficulty_band: str
    arm_id: str
    resolved: int
    correct: int
    truncated: int
    invalid: int
    no_answer: int
    placeholder: int
    unresolved: int
    loop_repetition: int

    @property
    def cell_id(self) -> str:
        return f"{self.task_family}|{self.difficulty_band}|{self.arm_id}"

    def as_dict(self) -> dict[str, Any]:
        total = self.resolved + self.unresolved
        low, high = wilson_ci(self.correct, self.resolved) if self.resolved else (0.0, 0.0)
        return {
            "arm_id": self.arm_id,
            "cell_id": self.cell_id,
            "correct": self.correct,
            "difficulty_band": self.difficulty_band,
            "accuracy": round(self.correct / self.resolved, 6) if self.resolved else None,
            "wilson_95_low": round(low, 6),
            "wilson_95_high": round(high, 6),
            "invalid_rate": round(self.invalid / total, 6) if total else 0.0,
            "loop_repetition_rate": round(self.loop_repetition / total, 6) if total else 0.0,
            "no_answer_rate": round(self.no_answer / total, 6) if total else 0.0,
            "placeholder_rate": round(self.placeholder / total, 6) if total else 0.0,
            "resolved": self.resolved,
            "row_count": total,
            "task_family": self.task_family,
            "truncation_rate": round(self.truncated / total, 6) if total else 0.0,
            "unresolved": self.unresolved,
        }


def evaluate_cell_gate(
    visible: CellOutcome,
    strict: CellOutcome,
) -> dict[str, Any]:
    """Apply the frozen RQ2 pilot-candidate gate to one family x band cell.

    Every criterion is reported whether it passes or fails, so a failing cell is
    a recorded result rather than a silently dropped one.
    """

    if (visible.task_family, visible.difficulty_band) != (
        strict.task_family,
        strict.difficulty_band,
    ):
        raise Phase1_0DError("gate compares arms from different cells")
    if visible.arm_id != VISIBLE_CONTROL_ARM.arm_id:
        raise Phase1_0DError("the first gate argument must be the visible control")
    if strict.arm_id == VISIBLE_CONTROL_ARM.arm_id:
        raise Phase1_0DError("the second gate argument must be a strict no-CoT arm")

    visible_rows = visible.resolved + visible.unresolved
    strict_rows = strict.resolved + strict.unresolved
    criteria = {
        "all_visible_rows_resolved": visible.resolved == GATE_REQUIRED_RESOLVED
        and visible.unresolved == 0,
        "all_strict_rows_resolved": strict.resolved == GATE_REQUIRED_RESOLVED
        and strict.unresolved == 0,
        "visible_control_correct_at_least_14": visible.correct >= GATE_MIN_VISIBLE_CORRECT,
        "strict_correct_within_8_to_18": (
            GATE_STRICT_CORRECT_LOW <= strict.correct <= GATE_STRICT_CORRECT_HIGH
        ),
        "visible_truncation_within_10_percent": visible_rows > 0
        and visible.truncated / visible_rows <= GATE_MAX_TRUNCATION_RATE,
        "strict_truncation_within_10_percent": strict_rows > 0
        and strict.truncated / strict_rows <= GATE_MAX_TRUNCATION_RATE,
        "visible_invalid_within_10_percent": visible_rows > 0
        and visible.invalid / visible_rows <= GATE_MAX_INVALID_RATE,
        "strict_invalid_within_10_percent": strict_rows > 0
        and strict.invalid / strict_rows <= GATE_MAX_INVALID_RATE,
    }
    return {
        "gate": GATE_ID,
        "task_family": visible.task_family,
        "difficulty_band": visible.difficulty_band,
        "strict_arm_id": strict.arm_id,
        "criteria": criteria,
        "rq2_pilot_candidate": all(criteria.values()),
        "failed_criteria": sorted(name for name, ok in criteria.items() if not ok),
        "interpretation": GATE_INTERPRETATION,
    }


def paired_difference(
    visible_correct_by_item: Mapping[str, bool],
    strict_correct_by_item: Mapping[str, bool],
) -> dict[str, Any]:
    """Return the paired visible-minus-strict difference on shared items."""

    shared = sorted(set(visible_correct_by_item) & set(strict_correct_by_item))
    if not shared:
        raise Phase1_0DError("paired difference requires at least one shared item")
    both = sum(
        1
        for item in shared
        if visible_correct_by_item[item] and strict_correct_by_item[item]
    )
    visible_only = sum(
        1
        for item in shared
        if visible_correct_by_item[item] and not strict_correct_by_item[item]
    )
    strict_only = sum(
        1
        for item in shared
        if not visible_correct_by_item[item] and strict_correct_by_item[item]
    )
    neither = len(shared) - both - visible_only - strict_only
    return {
        "paired_items": len(shared),
        "both_correct": both,
        "visible_only_correct": visible_only,
        "strict_only_correct": strict_only,
        "neither_correct": neither,
        "difference": round((visible_only - strict_only) / len(shared), 6),
    }


# --------------------------------------------------------------------------
# Protocol snapshot
# --------------------------------------------------------------------------


def protocol_snapshot(
    *,
    selection: Mapping[str, Any] | None = None,
    strict_budget_check: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the frozen protocol, safe to write before any inference."""

    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "phase": PHASE,
        "track": TRACK,
        "artifact_root": ARTIFACT_ROOT,
        "preserved_phase_1_0c_pack": PRESERVED_PHASE_1_0C_PACK,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "bank_path": DEFAULT_BANK_PATH,
        "phase_1_0c_split": PHASE_1_0C_SPLIT,
        "eligible_splits": list(ELIGIBLE_SPLITS),
        "items_per_cell": ITEMS_PER_CELL,
        "expected_item_count": EXPECTED_ITEM_COUNT,
        "selection_seed": SELECTION_SEED,
        "run_base_seed": RUN_BASE_SEED,
        "samples_per_item": SAMPLES_PER_ITEM,
        "arms": [arm.as_dict() for arm in ARMS],
        "visible_override_id": VISIBLE_REASONING_OVERRIDE_ID,
        "visible_override_sha256": sha256_text(VISIBLE_REASONING_OVERRIDE_TEXT),
        "strict_budget_rationale": STRICT_BUDGET_RATIONALE,
        "decoding_matched_greedy": DECODING_MATCHED_GREEDY,
        "parser_role": PARSER_ROLE,
        "semantic_labels": list(SEMANTIC_LABELS),
        "secondary_review_sample_fraction": SECONDARY_REVIEW_SAMPLE_FRACTION,
        "arbitration_rule": ARBITRATION_RULE_ID,
        "gate": {
            "id": GATE_ID,
            "required_resolved": GATE_REQUIRED_RESOLVED,
            "min_visible_correct": GATE_MIN_VISIBLE_CORRECT,
            "strict_correct_low": GATE_STRICT_CORRECT_LOW,
            "strict_correct_high": GATE_STRICT_CORRECT_HIGH,
            "max_truncation_rate": GATE_MAX_TRUNCATION_RATE,
            "max_invalid_rate": GATE_MAX_INVALID_RATE,
            "interpretation": GATE_INTERPRETATION,
            "no_headroom_result": NO_HEADROOM_RESULT,
        },
        "repairs": {
            "P10C-D1": "no condition contains the literal answer placeholder, and "
            "every rendered prompt is asserted free of it before inference",
            "P10C-D2": "budgets are registered per arm: 1024 new tokens for the "
            "visible control, 32 for the strict arms",
        },
        "licenses_no_claim_about": [
            "hidden reasoning",
            "internal representations",
            "invisible chain-of-thought",
            "J-space",
        ],
    }
    if selection is not None:
        snapshot["selection"] = dict(selection)
    if strict_budget_check is not None:
        snapshot["strict_budget_check"] = dict(strict_budget_check)
    snapshot["protocol_sha256"] = sha256_text(canonical_json(snapshot))
    return snapshot
