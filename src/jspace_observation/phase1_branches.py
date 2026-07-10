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

MIN_BRANCH_CLASSIFICATION_N = 3
MIN_VISIBLE_COT_BASELINE_N = 3
MIN_VISIBLE_COT_PARSE_VALID_RATE = 0.80
BRANCH_ABSOLUTE_ACCURACY_FLOOR = 0.50
VISIBLE_COT_RELATIVE_ACCURACY_RATIO = 0.70


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

PHASE1_BRANCH_SAMPLE_SIZE_WARNING = (
    "Success labels require the registered minimum sample size. Results based on "
    "fewer than three observations per branch/depth are pilot-level and cannot "
    "establish branch reliability."
)

PHASE1_VISIBLE_COT_BASELINE_WARNING = (
    "Relative accuracy criteria are applied only when the visible-CoT baseline has "
    "sufficient samples, valid parsing, and nonzero accuracy. Otherwise the relative "
    "gate is reported as NA."
)

PHASE1_POSTPROCESSING_ACCURACY_WARNING = (
    "Non-degradation alone is not answer-recovery success. Postprocessed utility "
    "also requires an absolute accuracy floor."
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


def _as_nonnegative_int(value: Any) -> int | None:
    numeric = _as_float(value)
    if numeric is None or numeric < 0 or not numeric.is_integer():
        return None
    return int(numeric)


def evaluate_visible_cot_baseline(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate whether a matching visible-CoT baseline supports relative accuracy."""
    visible_cot_n = _as_nonnegative_int(metrics.get("visible_cot_n"))
    visible_cot_accuracy = _as_float(metrics.get("visible_cot_accuracy"))
    visible_cot_parse_valid_rate = _as_float(
        metrics.get("visible_cot_parse_valid_rate")
    )
    visible_cot_answer_format_warning_rate = _as_float(
        metrics.get("visible_cot_answer_format_warning_rate")
    )
    baseline_available = any(
        value is not None
        for value in (
            visible_cot_n,
            visible_cot_accuracy,
            visible_cot_parse_valid_rate,
            visible_cot_answer_format_warning_rate,
        )
    )
    failure_reasons: list[str] = []

    if not baseline_available:
        failure_reasons.append("visible_cot_baseline_unavailable")
    else:
        if visible_cot_n is None or visible_cot_n < MIN_VISIBLE_COT_BASELINE_N:
            failure_reasons.append("insufficient_visible_cot_samples")
        if (
            visible_cot_parse_valid_rate is None
            or visible_cot_parse_valid_rate < MIN_VISIBLE_COT_PARSE_VALID_RATE
        ):
            failure_reasons.append("visible_cot_parse_invalid")
        if visible_cot_accuracy is None:
            failure_reasons.append("visible_cot_accuracy_unavailable")
        elif visible_cot_accuracy <= 0:
            failure_reasons.append("visible_cot_accuracy_zero")

    return {
        "baseline_available": baseline_available,
        "baseline_valid": baseline_available and not failure_reasons,
        "baseline_failure_reasons": failure_reasons,
        "visible_cot_n": visible_cot_n,
        "visible_cot_accuracy": visible_cot_accuracy,
        "visible_cot_parse_valid_rate": visible_cot_parse_valid_rate,
        "visible_cot_answer_format_warning_rate": (
            visible_cot_answer_format_warning_rate
        ),
    }


def classify_branch_result(branch: str, metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one answer-control branch against preregistered thresholds."""
    passed: list[str] = []
    failed: list[str] = []
    not_applicable: list[str] = []
    sample_size = _as_nonnegative_int(
        metrics.get("n", metrics.get("sample_size"))
    )
    sample_size_sufficient = (
        sample_size is not None and sample_size >= MIN_BRANCH_CLASSIFICATION_N
    )
    sample_size_criterion = (
        f"n >= {MIN_BRANCH_CLASSIFICATION_N} "
        f"(actual={_format_metric(sample_size)})"
    )
    (passed if sample_size_sufficient else failed).append(sample_size_criterion)
    baseline = evaluate_visible_cot_baseline(metrics)
    absolute_accuracy_passed = False
    relative_accuracy_gate_applicable = baseline["baseline_valid"]
    relative_accuracy_gate_required = branch in {
        RAW_STRICT_BRANCH,
        STOPPED_INTERVENTION_BRANCH,
    }
    relative_accuracy_gate_passed: bool | None = None

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

    def check_relative_accuracy(metric: str) -> bool:
        nonlocal relative_accuracy_gate_passed
        if not relative_accuracy_gate_applicable:
            not_applicable.append("relative_accuracy_gate")
            return True

        actual = _as_float(metrics.get(metric))
        visible_cot_accuracy = baseline["visible_cot_accuracy"]
        threshold = (
            VISIBLE_COT_RELATIVE_ACCURACY_RATIO * visible_cot_accuracy
            if visible_cot_accuracy is not None
            else None
        )
        relative_accuracy_gate_passed = (
            actual is not None
            and threshold is not None
            and actual >= threshold
        )
        criterion = (
            f"{metric} >= {VISIBLE_COT_RELATIVE_ACCURACY_RATIO:.2f} * "
            "visible_cot_accuracy "
            f"({metric}={_format_metric(actual)}, "
            f"visible_cot_accuracy={_format_metric(visible_cot_accuracy)})"
        )
        if relative_accuracy_gate_required:
            (
                passed if relative_accuracy_gate_passed else failed
            ).append(criterion)
            return relative_accuracy_gate_passed
        return True

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
        absolute_accuracy_passed = check(
            "accuracy_raw",
            ">=",
            BRANCH_ABSOLUTE_ACCURACY_FLOOR,
        )
        relative_accuracy_passed = check_relative_accuracy("accuracy_raw")
        success_criteria_passed = (
            all(surface_checks)
            and all(task_checks)
            and absolute_accuracy_passed
            and relative_accuracy_passed
        )

        if not all(surface_checks):
            classification = "raw_strict_not_established"
        elif not success_criteria_passed:
            classification = "surface_answer_only_but_task_failed"
        elif not sample_size_sufficient:
            classification = "raw_strict_pilot_only"
        else:
            classification = "raw_strict_preliminarily_established"

    elif branch == STOPPED_INTERVENTION_BRANCH:
        surface_checks = (
            check("stopped_no_cot_valid_rate", ">=", 0.90),
            check("stop_success_rate", ">=", 0.80),
            check("parse_valid_rate", ">=", 0.80),
        )
        absolute_accuracy_passed = check(
            "accuracy_stopped",
            ">=",
            BRANCH_ABSOLUTE_ACCURACY_FLOOR,
        )
        relative_accuracy_passed = check_relative_accuracy("accuracy_stopped")
        success_criteria_passed = (
            all(surface_checks)
            and absolute_accuracy_passed
            and relative_accuracy_passed
        )

        if not all(surface_checks):
            classification = "stopped_intervention_not_useful"
        elif not success_criteria_passed:
            classification = "stopped_surface_compliant_but_task_failed"
        elif not sample_size_sufficient:
            classification = "stopped_intervention_pilot_only"
        else:
            classification = "stopped_intervention_usable"

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
        absolute_accuracy_passed = check(
            "accuracy_postprocessed",
            ">=",
            BRANCH_ABSOLUTE_ACCURACY_FLOOR,
        )
        check_relative_accuracy("accuracy_postprocessed")
        success_criteria_passed = (
            validity_pass
            and success_pass
            and warning_pass
            and accuracy_pass
            and absolute_accuracy_passed
        )

        if not validity_pass:
            classification = "postprocessed_utility_not_useful"
        elif not absolute_accuracy_passed:
            classification = "postprocessed_surface_clean_but_task_failed"
        elif (
            not warning_pass
            and _as_float(metrics.get("postprocessing_warning_rate")) is not None
        ):
            classification = "postprocessed_surface_clean_but_warning_high"
        elif not success_criteria_passed:
            classification = "postprocessed_utility_not_useful"
        elif not sample_size_sufficient:
            classification = "postprocessed_utility_pilot_only"
        else:
            classification = "postprocessed_answer_recovery_usable"

    else:
        return {
            "branch": branch,
            "sample_size": sample_size,
            "minimum_sample_size": MIN_BRANCH_CLASSIFICATION_N,
            "sample_size_sufficient": sample_size_sufficient,
            "absolute_accuracy_floor": BRANCH_ABSOLUTE_ACCURACY_FLOOR,
            "absolute_accuracy_passed": False,
            **baseline,
            "relative_accuracy_gate_applicable": False,
            "relative_accuracy_gate_required": False,
            "relative_accuracy_gate_passed": None,
            "classification": "not_applicable",
            "classification_is_provisional": False,
            "criteria_passed": [],
            "criteria_failed": [],
            "criteria_not_applicable": ["relative_accuracy_gate"],
            "interpretation_warning": PHASE1_BRANCH_CLASSIFICATION_WARNING,
        }

    interpretation_warnings = [BRANCH_INTERPRETATION_WARNINGS[branch]]
    if not sample_size_sufficient:
        interpretation_warnings.append(PHASE1_BRANCH_SAMPLE_SIZE_WARNING)
    if (
        not baseline["baseline_valid"]
    ):
        reasons = ", ".join(baseline["baseline_failure_reasons"])
        interpretation_warnings.append(
            f"Relative accuracy comparison is unavailable ({reasons})."
        )
    if branch == POSTPROCESSED_UTILITY_BRANCH:
        interpretation_warnings.append(PHASE1_POSTPROCESSING_ACCURACY_WARNING)

    return {
        "branch": branch,
        "sample_size": sample_size,
        "minimum_sample_size": MIN_BRANCH_CLASSIFICATION_N,
        "sample_size_sufficient": sample_size_sufficient,
        "absolute_accuracy_floor": BRANCH_ABSOLUTE_ACCURACY_FLOOR,
        "absolute_accuracy_passed": absolute_accuracy_passed,
        **baseline,
        "relative_accuracy_gate_applicable": relative_accuracy_gate_applicable,
        "relative_accuracy_gate_required": relative_accuracy_gate_required,
        "relative_accuracy_gate_passed": relative_accuracy_gate_passed,
        "classification": classification,
        "classification_is_provisional": not sample_size_sufficient,
        "criteria_passed": passed,
        "criteria_failed": failed,
        "criteria_not_applicable": not_applicable,
        "interpretation_warning": " ".join(interpretation_warnings),
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
            "n": result["sample_size"],
            "minimum_n": result["minimum_sample_size"],
            "provisional": result["classification_is_provisional"],
            "visible_cot_baseline_valid": result["baseline_valid"],
            "relative_accuracy_gate": (
                "NA"
                if result["relative_accuracy_gate_passed"] is None
                else (
                    (
                        "passed"
                        if result["relative_accuracy_gate_passed"]
                        else "failed"
                    )
                    if result["relative_accuracy_gate_required"]
                    else (
                        "reported_passed"
                        if result["relative_accuracy_gate_passed"]
                        else "reported_failed"
                    )
                )
            ),
            "baseline_failure_reasons": (
                "; ".join(result["baseline_failure_reasons"]) or "NA"
            ),
            "criteria_passed": "; ".join(result["criteria_passed"]) or "NA",
            "criteria_failed": "; ".join(result["criteria_failed"]) or "NA",
            "criteria_not_applicable": (
                "; ".join(result["criteria_not_applicable"]) or "NA"
            ),
        })

    if not classified_rows:
        return "No answer-control branch classifications were produced."

    columns = (
        "model",
        "task_family",
        "depth",
        "branch",
        "condition",
        "n",
        "minimum_n",
        "sample_size_sufficient",
        "classification",
        "provisional",
        "absolute_accuracy_passed",
        "visible_cot_n",
        "visible_cot_accuracy",
        "visible_cot_parse_valid_rate",
        "visible_cot_answer_format_warning_rate",
        "visible_cot_baseline_valid",
        "baseline_failure_reasons",
        "relative_accuracy_gate",
        "raw_no_cot_valid_rate",
        "stopped_no_cot_valid_rate",
        "postprocessed_no_cot_valid_rate",
        "accuracy_raw",
        "accuracy_stopped",
        "accuracy_postprocessed",
        "stop_triggered_rate",
        "stop_string_distribution",
        "postprocessing_applied_rate",
        "postprocessing_warning_rate",
        "criteria_passed",
        "criteria_failed",
        "criteria_not_applicable",
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
        f"{PHASE1_BRANCH_SAMPLE_SIZE_WARNING}\n\n"
        f"{PHASE1_VISIBLE_COT_BASELINE_WARNING}\n\n"
        f"{PHASE1_POSTPROCESSING_ACCURACY_WARNING}\n\n"
        f"{render_branch_success_classification_table(metric_rows)}"
    )
