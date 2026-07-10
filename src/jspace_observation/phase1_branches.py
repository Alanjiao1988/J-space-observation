"""Phase 1 answer-control branch taxonomy and report rendering."""

from __future__ import annotations

from dataclasses import dataclass
import math
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

PHASE1_BRANCH_CLASSIFICATION_WARNING = (
    "Branch classifications are behavioral and operational. They do not establish "
    "hidden reasoning, internal workspace behavior, or J-space evidence."
)

BRANCH_INTERPRETATION_WARNINGS = {
    RAW_STRICT_BRANCH: (
        "Raw strict classification evaluates behavioral surface compliance and task utility only; "
        "it does not establish hidden reasoning, internal workspace behavior, or J-space evidence."
    ),
    STOPPED_INTERVENTION_BRANCH: (
        "Generation-time stopping is an intervention; stopped validity is not spontaneous no-CoT "
        "and does not establish hidden reasoning, internal workspace behavior, or J-space evidence."
    ),
    POSTPROCESSED_UTILITY_BRANCH: (
        "Postprocessing measures answer recovery; postprocessed validity is not raw no-CoT and does "
        "not establish hidden reasoning, internal workspace behavior, or J-space evidence."
    ),
}


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


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.upper() == "NA":
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def classify_branch_result(branch: str, metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one answer-control branch against preregistered thresholds."""
    passed: list[str] = []
    failed: list[str] = []

    def check(metric: str, operator: str, threshold: float) -> bool:
        actual = _as_float(metrics.get(metric))
        success = (
            actual is not None
            and (actual >= threshold if operator == ">=" else actual <= threshold)
        )
        criterion = (
            f"{metric} {operator} {threshold:.2f} "
            f"(actual={_format_metric(actual)})"
        )
        (passed if success else failed).append(criterion)
        return success

    if branch == RAW_STRICT_BRANCH:
        surface_checks = (
            check("raw_no_cot_valid_rate", ">=", 0.90),
            check("visible_reasoning_marker_rate", "<=", 0.10),
        )
        task_checks = (
            check("parse_valid_rate", ">=", 0.80),
            check("parse_ambiguous_rate", "<=", 0.20),
            check("answer_format_warning_rate", "<=", 0.20),
        )
        accuracy_raw = _as_float(metrics.get("accuracy_raw"))
        visible_cot_accuracy = _as_float(metrics.get("visible_cot_accuracy"))
        accuracy_pass = (
            accuracy_raw is not None
            and (
                accuracy_raw >= 0.50
                or (
                    visible_cot_accuracy is not None
                    and accuracy_raw >= 0.70 * visible_cot_accuracy
                )
            )
        )
        accuracy_criterion = (
            "accuracy_raw >= 0.50 OR accuracy_raw >= 0.70 * visible_cot_accuracy "
            f"(accuracy_raw={_format_metric(accuracy_raw)}, "
            f"visible_cot_accuracy={_format_metric(visible_cot_accuracy)})"
        )
        (passed if accuracy_pass else failed).append(accuracy_criterion)

        if all(surface_checks) and all(task_checks) and accuracy_pass:
            classification = "raw_strict_preliminarily_established"
        elif not all(surface_checks):
            classification = "raw_strict_not_established"
        else:
            classification = "surface_answer_only_but_task_failed"

    elif branch == STOPPED_INTERVENTION_BRANCH:
        surface_checks = (
            check("stopped_no_cot_valid_rate", ">=", 0.90),
            check("stop_success_rate", ">=", 0.80),
            check("parse_valid_rate", ">=", 0.80),
        )
        accuracy_pass = check("accuracy_stopped", ">=", 0.50)

        if all(surface_checks) and accuracy_pass:
            classification = "stopped_intervention_usable"
        elif all(surface_checks):
            classification = "stopped_surface_compliant_but_task_failed"
        else:
            classification = "stopped_intervention_not_useful"

    elif branch == POSTPROCESSED_UTILITY_BRANCH:
        validity_pass = check("postprocessed_no_cot_valid_rate", ">=", 0.90)
        success_pass = check("postprocessing_success_rate", ">=", 0.80)
        warning_pass = check("postprocessing_warning_rate", "<=", 0.20)
        accuracy_postprocessed = _as_float(metrics.get("accuracy_postprocessed"))
        accuracy_raw = _as_float(metrics.get("accuracy_raw"))
        accuracy_pass = (
            accuracy_postprocessed is not None
            and accuracy_raw is not None
            and accuracy_postprocessed >= accuracy_raw
        )
        accuracy_criterion = (
            "accuracy_postprocessed >= accuracy_raw "
            f"(accuracy_postprocessed={_format_metric(accuracy_postprocessed)}, "
            f"accuracy_raw={_format_metric(accuracy_raw)})"
        )
        (passed if accuracy_pass else failed).append(accuracy_criterion)

        if validity_pass and success_pass and warning_pass and accuracy_pass:
            classification = "postprocessed_answer_recovery_usable"
        elif (
            validity_pass
            and not warning_pass
            and _as_float(metrics.get("postprocessing_warning_rate")) is not None
        ):
            classification = "postprocessed_surface_clean_but_warning_high"
        else:
            classification = "postprocessed_utility_not_useful"

    else:
        return {
            "branch": branch,
            "classification": "not_applicable",
            "criteria_passed": [],
            "criteria_failed": [],
            "interpretation_warning": PHASE1_BRANCH_CLASSIFICATION_WARNING,
        }

    return {
        "branch": branch,
        "classification": classification,
        "criteria_passed": passed,
        "criteria_failed": failed,
        "interpretation_warning": BRANCH_INTERPRETATION_WARNINGS[branch],
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


def render_branch_success_classification_table(
    metric_rows: Sequence[Mapping[str, Any]],
) -> str:
    """Render preregistered classifications for answer-control branches."""
    answer_control_branches = {
        RAW_STRICT_BRANCH,
        STOPPED_INTERVENTION_BRANCH,
        POSTPROCESSED_UTILITY_BRANCH,
    }
    classified_rows = []
    for row in metric_rows:
        condition = str(row.get("condition", ""))
        branch = str(row.get("branch") or get_phase1_branch(condition))
        if branch not in answer_control_branches:
            continue
        result = classify_branch_result(branch, row)
        classified_rows.append({
            **row,
            **result,
            "criteria_passed": "; ".join(result["criteria_passed"]) or "NA",
            "criteria_failed": "; ".join(result["criteria_failed"]) or "NA",
        })

    if not classified_rows:
        return "No answer-control branch classifications were produced."

    columns = (
        "model",
        "task_family",
        "depth",
        "branch",
        "condition",
        "classification",
        "raw_no_cot_valid_rate",
        "stopped_no_cot_valid_rate",
        "postprocessed_no_cot_valid_rate",
        "accuracy_raw",
        "accuracy_stopped",
        "accuracy_postprocessed",
        "visible_cot_accuracy",
        "stop_triggered_rate",
        "stop_string_distribution",
        "postprocessing_applied_rate",
        "postprocessing_warning_rate",
        "criteria_passed",
        "criteria_failed",
        "interpretation_warning",
    )
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in classified_rows:
        lines.append(
            "| " + " | ".join(_format_metric(row.get(column)) for column in columns) + " |"
        )
    return "\n".join(lines)


def render_branch_success_classification_section(
    metric_rows: Sequence[Mapping[str, Any]],
) -> str:
    """Render the mandatory warning and branch classification table."""
    return (
        f"{PHASE1_BRANCH_CLASSIFICATION_WARNING}\n\n"
        f"{render_branch_success_classification_table(metric_rows)}"
    )
