"""Phase 1 answer-control branch taxonomy and report rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


RAW_STRICT_BRANCH = "raw_strict"
STOPPED_INTERVENTION_BRANCH = "stopped_intervention"
POSTPROCESSED_UTILITY_BRANCH = "postprocessed_utility"
VISIBLE_REASONING_BASELINE_BRANCH = "visible_reasoning_baseline"
UNCLASSIFIED_BRANCH = "unclassified"


@dataclass(frozen=True)
class Phase1BranchDefinition:
    """Stable reporting definition for a Phase 1 condition branch."""

    key: str
    label: str
    conditions: tuple[str, ...]
    interpretation: str


BRANCH_DEFINITIONS: dict[str, Phase1BranchDefinition] = {
    RAW_STRICT_BRANCH: Phase1BranchDefinition(
        key=RAW_STRICT_BRANCH,
        label="Raw strict no-CoT feasibility",
        conditions=("strict_answer_only", "strict_answer_only_prefill_answer"),
        interpretation="Raw output is evaluated without stop intervention or post-hoc extraction.",
    ),
    STOPPED_INTERVENTION_BRANCH: Phase1BranchDefinition(
        key=STOPPED_INTERVENTION_BRANCH,
        label="Stop-controlled generation intervention",
        conditions=("strict_answer_only_stopped",),
        interpretation="Generation-time stopping is an intervention; stopped validity is not spontaneous no-CoT.",
    ),
    POSTPROCESSED_UTILITY_BRANCH: Phase1BranchDefinition(
        key=POSTPROCESSED_UTILITY_BRANCH,
        label="Postprocessed answer-recovery utility",
        conditions=("strict_answer_only_postprocessed",),
        interpretation="Postprocessing measures answer recovery, not raw no-CoT compliance.",
    ),
    VISIBLE_REASONING_BASELINE_BRANCH: Phase1BranchDefinition(
        key=VISIBLE_REASONING_BASELINE_BRANCH,
        label="Visible-reasoning baseline",
        conditions=("visible_cot", "r1_style_thinking"),
        interpretation="Visible-reasoning baselines are not answer-control branches.",
    ),
    UNCLASSIFIED_BRANCH: Phase1BranchDefinition(
        key=UNCLASSIFIED_BRANCH,
        label="Unclassified condition",
        conditions=(),
        interpretation="Condition is not registered in the Phase 1 branch taxonomy.",
    ),
}

CONDITION_TO_BRANCH = {
    condition: definition.key
    for definition in BRANCH_DEFINITIONS.values()
    for condition in definition.conditions
}


PHASE1_INTERPRETATION_BOUNDARIES = """This run includes multiple answer-control branches:
1. Raw strict no-CoT feasibility
2. Stop-controlled generation intervention
3. Postprocessed answer-recovery utility

Metrics from these branches are not interchangeable.

High stopped_no_cot_valid_rate means the stopped output satisfies surface no-CoT constraints after generation-time intervention. It does not prove spontaneous no-CoT.

High postprocessed_no_cot_valid_rate means the extracted answer span satisfies surface no-CoT constraints. It does not prove the raw model output was no-CoT.

The legacy accuracy field follows eval_output_used. Use accuracy_raw, accuracy_stopped, and accuracy_postprocessed for branch-specific comparisons.

No result in this Phase 1 pilot is hidden-reasoning or J-space evidence."""


BRANCH_METRIC_COLUMNS = (
    "raw_no_cot_valid_rate",
    "stopped_no_cot_valid_rate",
    "postprocessed_no_cot_valid_rate",
    "stop_triggered_rate",
    "postprocessing_applied_rate",
    "accuracy_raw",
    "accuracy_stopped",
    "accuracy_postprocessed",
)


def get_phase1_branch(condition: str) -> str:
    """Return the stable branch key for a condition."""
    return CONDITION_TO_BRANCH.get(condition, UNCLASSIFIED_BRANCH)


def get_phase1_branch_definition(condition: str) -> Phase1BranchDefinition:
    """Return the complete branch definition for a condition."""
    return BRANCH_DEFINITIONS[get_phase1_branch(condition)]


def get_phase1_branch_metadata(condition: str) -> dict[str, str]:
    """Return record-ready branch metadata."""
    definition = get_phase1_branch_definition(condition)
    return {
        "phase1_branch": definition.key,
        "phase1_branch_label": definition.label,
        "phase1_branch_interpretation": definition.interpretation,
    }


def _format_metric(value: Any) -> str:
    if value is None or value == "":
        return "NA"
    if isinstance(value, str):
        return "NA" if value.upper() == "NA" else value
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_branch_metrics_table(metric_rows: Sequence[Mapping[str, Any]]) -> str:
    """Render a Markdown table that keeps branch-specific metrics separate."""
    if not metric_rows:
        return "No branch-level metrics were produced."

    columns = (
        "model",
        "task_family",
        "depth",
        "branch",
        "condition",
        *BRANCH_METRIC_COLUMNS,
        "interpretation",
    )
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]

    for row in metric_rows:
        condition = str(row.get("condition", ""))
        definition = get_phase1_branch_definition(condition)
        values = {
            **row,
            "branch": row.get("branch") or definition.key,
            "interpretation": definition.interpretation,
        }
        lines.append("| " + " | ".join(_format_metric(values.get(column)) for column in columns) + " |")

    return "\n".join(lines)
