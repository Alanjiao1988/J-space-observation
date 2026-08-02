"""Phase 1.0D execution pipeline — work units, records, adjudication, decision.

The frozen rules live in :mod:`jspace_observation.phase1_0d_confirmation`.  This
module only *applies* them, so nothing here may introduce a selection, a label,
or a threshold that the frozen protocol does not already contain.

The pipeline seam is deliberate:

``plan_work_units`` -> ``build_records`` -> (primary semantic review happens
outside this module) -> ``ingest_judgments`` -> ``annotate_review_selection``
-> (secondary review, also outside) -> ``apply_judgments``
-> ``compute_cell_outcomes`` -> ``build_decision``

``annotate_review_selection`` sits *after* primary review because the forced
component of the secondary sample is defined by the primary label.  A row cannot
be marked for isolated re-review before anyone has reviewed it once.

Automatic triage appears only in ``build_records`` and only as routing metadata.
It never becomes a final label: ``DR-01`` forbids an automatic evaluator from
deciding correctness, and every row that can move a cell metric carries a
semantic label instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .headroom_calibration import sha256_text
from .phase1_0d_confirmation import (
    ARMS,
    ARMS_BY_ID,
    FINAL_ANSWER_PREFIX,
    LITERAL_ANSWER_PLACEHOLDER,
    NO_COT_COMPLIANCE_ID,
    NO_HEADROOM_RESULT,
    REPLICATE_INDEX,
    REVIEW_FORM_ID,
    REVIEW_FORM_PRESENTED_FIELDS,
    REVIEW_ROLES,
    SPONTANEOUS_NO_COT_ARM,
    STRUCTURAL_NO_COT_ARM,
    VISIBLE_CONTROL_ARM,
    CellOutcome,
    ConditionArm,
    Phase1_0DError,
    arbitrate,
    evaluate_cell_gate,
    forces_secondary_review,
    generation_config,
    paired_difference,
    prompt_defects,
    render_prompt,
    stratified_secondary_sample,
    strict_output_compliance,
    validate_judgment_set,
)

#: Repetition diagnostic: a shingle of this many words repeated this many times.
LOOP_SHINGLE_WORDS = 8
LOOP_MIN_REPEATS = 3

#: Triage routes a row; it never labels one.
TRIAGE_ROUTES: tuple[str, ...] = (
    "candidate_correct",
    "candidate_incorrect",
    "no_final_answer_surface",
    "placeholder_echo",
    "truncated_at_budget",
    "possible_loop",
)


def record_id_for(task_id: str, arm_id: str, replicate_index: int = REPLICATE_INDEX) -> str:
    """Return the stable record identifier for one unit of work."""

    return f"{task_id}::{arm_id}::r{replicate_index}"


@dataclass(frozen=True)
class WorkUnit:
    """One deterministic generation request."""

    record_id: str
    task_id: str
    task_family: str
    difficulty_band: str
    split: str
    arm_id: str
    condition: str
    branch: str
    prompt: str
    registered_answer: str
    max_new_tokens: int
    seed: int

    @property
    def arm(self) -> ConditionArm:
        return ARMS_BY_ID[self.arm_id]


def plan_work_units(
    items: Sequence[Mapping[str, Any]],
    *,
    base_seed: int,
) -> list[WorkUnit]:
    """Expand the frozen selection into one work unit per item x arm.

    Every rendered prompt is checked against the frozen prohibitions here, before
    the unit can reach a backend.  A prompt defect stops the plan; it is never
    repaired silently at generation time.
    """

    units: list[WorkUnit] = []
    for item in items:
        question = str(item["question"])
        for arm in ARMS:
            prompt = render_prompt(question, arm)
            defects = prompt_defects(prompt, arm)
            if defects:
                raise Phase1_0DError(
                    f"rendered prompt for {item['task_id']}/{arm.arm_id} "
                    f"violates the frozen protocol: {', '.join(defects)}"
                )
            config = generation_config(arm)
            units.append(
                WorkUnit(
                    record_id=record_id_for(str(item["task_id"]), arm.arm_id),
                    task_id=str(item["task_id"]),
                    task_family=str(item["task_family"]),
                    difficulty_band=str(item["difficulty_band"]),
                    split=str(item["split"]),
                    arm_id=arm.arm_id,
                    condition=arm.condition,
                    branch=arm.branch,
                    prompt=prompt,
                    registered_answer=str(item["registered_answer"]),
                    max_new_tokens=config.max_new_tokens,
                    seed=base_seed,
                )
            )
    record_ids = [unit.record_id for unit in units]
    if len(set(record_ids)) != len(record_ids):
        raise Phase1_0DError("work units are not uniquely identified")
    return units


@dataclass(frozen=True)
class GenerationOutput:
    """What a backend must return for one unit."""

    output_text: str
    output_token_count: int


class SelfTestBackend:
    """Deterministic backend for CPU self-tests.

    It never loads a model.  It fabricates one output per arm that exercises the
    triage routes, so the pipeline can be validated end to end without a GPU and
    without pretending the fabricated rows are evidence.
    """

    is_real_model = False

    def generate(self, unit: WorkUnit) -> GenerationOutput:
        index = int(sha256_text(unit.task_id)[:8], 16)
        if unit.arm_id == VISIBLE_CONTROL_ARM.arm_id:
            if index % 7 == 0:
                text = "Let me think about it " * 40
                return GenerationOutput(text, unit.max_new_tokens)
            body = "I work through the steps carefully.\n"
            return GenerationOutput(
                f"{body}{FINAL_ANSWER_PREFIX} {unit.registered_answer}", 24
            )
        if index % 5 == 0:
            return GenerationOutput("", 1)
        if index % 3 == 0:
            return GenerationOutput("not the value", 4)
        return GenerationOutput(unit.registered_answer, 3)


def looks_like_a_loop(text: str) -> bool:
    """Deterministic repetition diagnostic.  Never a correctness label."""

    words = text.split()
    if len(words) < LOOP_SHINGLE_WORDS * LOOP_MIN_REPEATS:
        return False
    counts: dict[str, int] = {}
    for start in range(len(words) - LOOP_SHINGLE_WORDS + 1):
        shingle = " ".join(words[start : start + LOOP_SHINGLE_WORDS])
        counts[shingle] = counts.get(shingle, 0) + 1
        if counts[shingle] >= LOOP_MIN_REPEATS:
            return True
    return False


def final_answer_surface(text: str, arm: ConditionArm) -> str | None:
    """Return the registered final-answer surface, or ``None`` if absent.

    The visible control must end with the registered prefix.  The strict arms
    have no prefix: their whole output is the surface.  Nothing is clipped and
    then reported as the model's output.
    """

    if arm is VISIBLE_CONTROL_ARM:
        matches = list(re.finditer(re.escape(FINAL_ANSWER_PREFIX), text))
        if not matches:
            return None
        return text[matches[-1].end() :].strip() or None
    return text.strip() or None


def triage(unit: WorkUnit, output: GenerationOutput) -> dict[str, Any]:
    """Route a row.  This decides nothing about correctness."""

    truncated = output.output_token_count >= unit.max_new_tokens
    placeholder = LITERAL_ANSWER_PLACEHOLDER in output.output_text
    loop = looks_like_a_loop(output.output_text)
    surface = final_answer_surface(output.output_text, unit.arm)

    if placeholder:
        route = "placeholder_echo"
    elif surface is None:
        route = "no_final_answer_surface"
    elif truncated:
        route = "truncated_at_budget"
    elif loop:
        route = "possible_loop"
    elif surface == unit.registered_answer:
        route = "candidate_correct"
    else:
        route = "candidate_incorrect"
    if route not in TRIAGE_ROUTES:  # pragma: no cover - defensive
        raise Phase1_0DError(f"unregistered triage route {route!r}")
    return {
        "route": route,
        "final_answer_surface_present": surface is not None,
        "surface_matches_registered_answer": surface == unit.registered_answer,
        "truncated_at_budget": truncated,
        "placeholder_echo": placeholder,
        "possible_loop": loop,
        "decides_correctness": False,
    }


def build_records(
    units: Sequence[WorkUnit],
    outputs: Mapping[str, GenerationOutput],
) -> list[dict[str, Any]]:
    """Build one row record per work unit."""

    records: list[dict[str, Any]] = []
    for unit in units:
        if unit.record_id not in outputs:
            raise Phase1_0DError(f"no generation output for {unit.record_id}")
        output = outputs[unit.record_id]
        records.append(
            {
                "record_id": unit.record_id,
                "task_id": unit.task_id,
                "task_family": unit.task_family,
                "difficulty_band": unit.difficulty_band,
                "split": unit.split,
                "arm_id": unit.arm_id,
                "condition": unit.condition,
                "branch": unit.branch,
                "registered_answer": unit.registered_answer,
                "output_text": output.output_text,
                "provenance": {
                    "prompt_text": unit.prompt,
                    "max_new_tokens": unit.max_new_tokens,
                    "output_token_count": output.output_token_count,
                    "seed": unit.seed,
                    "cell_id": f"{unit.task_family}|{unit.difficulty_band}|{unit.arm_id}",
                },
                "triage": triage(unit, output),
                "compliance": (
                    strict_output_compliance(output.output_text)
                    if unit.arm_id != VISIBLE_CONTROL_ARM.arm_id
                    else {
                        "check": NO_COT_COMPLIANCE_ID,
                        "compliant": None,
                        "violations": [],
                        "markers_found": [],
                        "line_count": len(
                            [line for line in output.output_text.strip().splitlines() if line.strip()]
                        ),
                        "decides_correctness": False,
                    }
                ),
                "evaluation": {
                    "primary_label": None,
                    "secondary_label": None,
                    "final_label": None,
                    "secondary_review_required": None,
                    "arbitration_required": None,
                },
            }
        )
    return records


def annotate_review_selection(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Mark which rows need an isolated secondary review.

    Called after primary review.  The forced component depends on the primary
    label; the sampled component is a hash-ranked 20% *within every stratum*, so
    no cell can end up with zero sampled reviews while the global rate still
    looks right.
    """

    rows: list[dict[str, Any]] = []
    for record in records:
        row = {key: dict(value) if isinstance(value, dict) else value
               for key, value in record.items()}
        if row["evaluation"].get("primary_label") is None:
            raise Phase1_0DError(
                f"{row['record_id']} has no primary label; every row is reviewed first"
            )
        rows.append(row)

    strata: dict[tuple[str, ...], list[str]] = {}
    for row in rows:
        key = (str(row["task_family"]), str(row["difficulty_band"]), str(row["arm_id"]))
        strata.setdefault(key, []).append(str(row["record_id"]))
    sampled = stratified_secondary_sample(strata)

    for row in rows:
        evaluation = row["evaluation"]
        parser_agrees = _parser_agrees(row)
        forced = forces_secondary_review(
            primary_label=str(evaluation["primary_label"]),
            parser_agrees_with_primary=parser_agrees,
        )
        in_sample = str(row["record_id"]) in sampled
        evaluation["parser_agrees_with_primary"] = parser_agrees
        evaluation["secondary_review_forced"] = forced
        evaluation["secondary_review_sampled"] = in_sample
        evaluation["secondary_review_required"] = forced or in_sample
    return rows


def _parser_agrees(record: Mapping[str, Any]) -> bool:
    triage_row = record["triage"]
    primary = record["evaluation"]["primary_label"]
    if primary == "correct":
        return bool(triage_row["surface_matches_registered_answer"])
    if primary == "incorrect":
        return (
            bool(triage_row["final_answer_surface_present"])
            and not triage_row["surface_matches_registered_answer"]
        )
    if primary == "no_answer":
        return not triage_row["final_answer_surface_present"]
    return False


def apply_judgments(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Resolve every row through the frozen arbitration rule."""

    resolved: list[dict[str, Any]] = []
    for record in records:
        row = {key: dict(value) if isinstance(value, dict) else value
               for key, value in record.items()}
        evaluation = row["evaluation"]
        if evaluation.get("secondary_review_required") is None:
            raise Phase1_0DError(
                f"{row['record_id']} was not passed through review selection"
            )
        if evaluation["secondary_review_required"] and evaluation.get("secondary_label") is None:
            raise Phase1_0DError(
                f"{row['record_id']} requires a secondary review that is missing"
            )
        outcome = arbitrate(
            str(evaluation["primary_label"]),
            evaluation.get("secondary_label"),
            evaluation.get("third_label"),
        )
        evaluation["final_label"] = outcome["final_label"]
        evaluation["agreement"] = outcome["agreement"]
        evaluation["arbitration_required"] = outcome["arbitration_required"]
        evaluation["arbitration_pending"] = outcome["arbitration_pending"]
        evaluation["arbitration_rule"] = outcome["rule"]
        resolved.append(row)
    return resolved


def ingest_judgments(
    records: Sequence[Mapping[str, Any]],
    judgments: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach a validated judgment set to the records it belongs to.

    This is the registered path from a closed reviewer form to a decision, so an
    independent party holding the generations and the judgments can reproduce the
    result without inventing a review process.
    """

    validated = validate_judgment_set(judgments)
    known = {str(record["record_id"]) for record in records}
    unknown = sorted({j["record_id"] for j in validated} - known)
    if unknown:
        raise Phase1_0DError(f"judgments reference unknown records: {unknown}")

    by_record: dict[str, dict[str, dict[str, Any]]] = {}
    for judgment in validated:
        by_record.setdefault(judgment["record_id"], {})[judgment["role"]] = judgment

    rows: list[dict[str, Any]] = []
    for record in records:
        row = {key: dict(value) if isinstance(value, dict) else value
               for key, value in record.items()}
        evaluation = row["evaluation"]
        roles = by_record.get(str(row["record_id"]), {})
        for role in REVIEW_ROLES:
            judgment = roles.get(role)
            evaluation[f"{role}_label"] = judgment["label"] if judgment else None
            evaluation[f"{role}_reviewer_id"] = judgment["reviewer_id"] if judgment else None
        evaluation["review_form"] = REVIEW_FORM_ID
        rows.append(row)
    return rows


def build_review_form_rows(
    records: Sequence[Mapping[str, Any]],
    questions: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Build exactly what a reviewer is shown, and nothing else."""

    rows: list[dict[str, Any]] = []
    for record in records:
        record_id = str(record["record_id"])
        if record_id not in questions:
            raise Phase1_0DError(f"no question text for {record_id}")
        rows.append(
            {
                "record_id": record_id,
                "question": questions[record_id],
                "registered_answer": str(record["registered_answer"]),
                "output_text": str(record["output_text"]),
            }
        )
    for row in rows:
        if set(row) != set(REVIEW_FORM_PRESENTED_FIELDS):
            raise Phase1_0DError("a review row must present exactly the registered fields")
    return rows


def review_agreement(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Report reviewer agreement.  Parser agreement is reported separately."""

    reviewed = [
        record
        for record in records
        if record["evaluation"].get("secondary_label") is not None
    ]
    agree = sum(1 for record in reviewed if record["evaluation"]["agreement"] is True)
    return {
        "double_reviewed_rows": len(reviewed),
        "reviewer_agreements": agree,
        "reviewer_disagreements": len(reviewed) - agree,
        "reviewer_agreement_rate": round(agree / len(reviewed), 6) if reviewed else None,
        "parser_agreement_is_not_reviewer_agreement": True,
        "parser_agreements": sum(
            1
            for record in records
            if record["evaluation"].get("parser_agrees_with_primary") is True
        ),
    }


def compute_cell_outcomes(records: Sequence[Mapping[str, Any]]) -> list[CellOutcome]:
    """Aggregate resolved rows into the frozen per-cell summary.

    Every row must already carry a semantic ``final_label``.  Without this guard
    an unlabelled row would be counted as resolved-and-incorrect, so a run that
    had merely not been reviewed yet would report ``HEADROOM_NOT_ESTABLISHED``
    as though the model had failed.  A missing label is a missing measurement,
    not a negative result.
    """

    unlabelled = [
        str(record["record_id"])
        for record in records
        if record["evaluation"].get("final_label") is None
    ]
    if unlabelled:
        raise Phase1_0DError(
            f"{len(unlabelled)} row(s) carry no semantic final label, "
            f"starting with {unlabelled[0]}; a cell metric may not be computed "
            "from unreviewed rows"
        )

    buckets: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for record in records:
        key = (
            str(record["task_family"]),
            str(record["difficulty_band"]),
            str(record["arm_id"]),
        )
        buckets.setdefault(key, []).append(record)

    outcomes: list[CellOutcome] = []
    for (family, band, arm_id), rows in sorted(buckets.items()):
        labels = [str(row["evaluation"]["final_label"]) for row in rows]
        unresolved = sum(1 for label in labels if label == "unresolved")
        outcomes.append(
            CellOutcome(
                task_family=family,
                difficulty_band=band,
                arm_id=arm_id,
                resolved=len(labels) - unresolved,
                correct=sum(1 for label in labels if label == "correct"),
                truncated=sum(
                    1 for row in rows if row["triage"]["truncated_at_budget"]
                ),
                invalid=sum(1 for label in labels if label == "invalid"),
                no_answer=sum(1 for label in labels if label == "no_answer"),
                placeholder=sum(1 for row in rows if row["triage"]["placeholder_echo"]),
                unresolved=unresolved,
                loop_repetition=sum(1 for row in rows if row["triage"]["possible_loop"]),
                no_cot_violations=sum(
                    1 for row in rows if row["compliance"]["compliant"] is False
                ),
                arbitration_pending=sum(
                    1
                    for row in rows
                    if row["evaluation"].get("arbitration_pending") is True
                ),
            )
        )
    return outcomes


def _correct_by_item(
    records: Iterable[Mapping[str, Any]],
    family: str,
    band: str,
    arm_id: str,
) -> dict[str, bool]:
    return {
        str(record["task_id"]): record["evaluation"]["final_label"] == "correct"
        for record in records
        if record["task_family"] == family
        and record["difficulty_band"] == band
        and record["arm_id"] == arm_id
    }


def build_decision(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute the frozen decision object.

    Every cell is reported, whether or not it passes.  If nothing passes, the
    result is ``HEADROOM_NOT_ESTABLISHED`` — a scientific result, not a defect to
    be repaired by lowering the gate.
    """

    outcomes = compute_cell_outcomes(records)
    by_key = {
        (outcome.task_family, outcome.difficulty_band, outcome.arm_id): outcome
        for outcome in outcomes
    }
    cells: list[dict[str, Any]] = []
    candidates: list[str] = []
    for (family, band, arm_id), outcome in sorted(by_key.items()):
        if arm_id == VISIBLE_CONTROL_ARM.arm_id:
            continue
        visible = by_key.get((family, band, VISIBLE_CONTROL_ARM.arm_id))
        if visible is None:
            raise Phase1_0DError(
                f"cell {family}|{band} has no visible-reasoning control"
            )
        gate = evaluate_cell_gate(visible, outcome)
        gate["visible_metrics"] = visible.as_dict()
        gate["strict_metrics"] = outcome.as_dict()
        gate["paired"] = paired_difference(
            _correct_by_item(records, family, band, VISIBLE_CONTROL_ARM.arm_id),
            _correct_by_item(records, family, band, arm_id),
        )
        cells.append(gate)
        if gate["rq2_pilot_candidate"]:
            candidates.append(f"{family}|{band}|{arm_id}")

    observed_pairs = {
        (str(record["task_family"]), str(record["difficulty_band"]))
        for record in records
    }
    reported_pairs = {(cell["task_family"], cell["difficulty_band"]) for cell in cells}
    expected_cells = len(observed_pairs) * len(
        (STRUCTURAL_NO_COT_ARM.arm_id, SPONTANEOUS_NO_COT_ARM.arm_id)
    )
    all_reported = reported_pairs == observed_pairs and len(cells) == expected_cells

    return {
        "cells": cells,
        "cell_count": len(cells),
        "rq2_pilot_candidates": sorted(candidates),
        "result": "RQ2_PILOT_CANDIDATE_CELLS_FOUND" if candidates else NO_HEADROOM_RESULT,
        "all_cells_reported": all_reported,
        "unreported_cells": sorted(
            f"{family}|{band}" for family, band in observed_pairs - reported_pairs
        ),
        "strict_arms": [
            STRUCTURAL_NO_COT_ARM.arm_id,
            SPONTANEOUS_NO_COT_ARM.arm_id,
        ],
        "licenses_no_claim_about": [
            "hidden reasoning",
            "internal representations",
            "invisible chain-of-thought",
            "J-space",
        ],
    }
