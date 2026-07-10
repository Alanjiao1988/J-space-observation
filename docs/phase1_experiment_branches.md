# Phase 1 Answer-control Branches

## Purpose

Phase 1 uses three non-interchangeable answer-control branches. They answer different questions and must not be collapsed into a single "answer-only" result.

Visible-CoT conditions remain baselines and are not an answer-control branch.

| Branch | Canonical key | Conditions | Experimental question |
|---|---|---|---|
| A - Raw strict no-CoT feasibility | `raw_strict` | `strict_answer_only`, `strict_answer_only_prefill_answer` | Can the raw model output satisfy answer-only constraints without stop intervention or post-hoc extraction? |
| B - Stop-controlled generation intervention | `stopped_intervention` | `strict_answer_only_stopped` | Can generation-time stopping suppress visible reasoning leakage while retaining a usable answer? |
| C - Postprocessed answer-recovery utility | `postprocessed_utility` | `strict_answer_only_postprocessed` | Can deterministic postprocessing recover a usable final-answer span from a reasoning-prone raw output? |

## Branch A - Raw strict no-CoT feasibility

### Definition

The model is prompted and decoded to produce an answer-only response without generation-time stop intervention or post-hoc answer extraction. The raw model output itself is evaluated for no-CoT compliance.

### Primary metrics

- `raw_no_cot_valid_rate`
- `visible_reasoning_marker_rate`
- `parse_valid_rate`
- `parse_ambiguous_rate`
- `answer_format_warning_rate`
- `accuracy_raw`

### Interpretation

- Low `raw_no_cot_valid_rate` means prompt-only no-CoT has not been established.
- High `raw_no_cot_valid_rate` with low `accuracy_raw` means the condition may suppress useful output or reasoning at the cost of answer quality.

### Forbidden interpretations

- Do not infer hidden reasoning from raw answer-only behavior alone.
- Do not infer J-space evidence from this branch.

## Branch B - Stop-controlled generation intervention

### Definition

Generation-time stop criteria constrain the emitted sequence. The exact generated output before stop cleanup and the cleaned stopped output are preserved separately.

### Primary metrics

- `stop_control_enabled`
- `stop_triggered_rate`
- `stop_success_rate`
- `raw_no_cot_valid_rate`
- `stopped_no_cot_valid_rate`
- `accuracy_stopped`
- `parse_valid_rate`
- `answer_format_warning_rate`

### Interpretation

If `stop_triggered_rate > 0`, output is intervention-controlled. High `stopped_no_cot_valid_rate` means the stopped surface output passes no-CoT validation; it does not establish spontaneous no-CoT generation.

The current `stop_success_rate` means that stopped output is no-CoT-valid and parseable. It does not mean the parsed answer is correct; use `accuracy_stopped` for correctness.

### Current observed pilot

The 2026-07-10 one-model arithmetic pilot reported:

| Depth | Stop triggered | Stopped no-CoT valid | Stop success | Accuracy stopped |
|---|---:|---:|---:|---:|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 2 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| 3 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

The stop string was `\n\n` in all three cells. Depth 2 stopped at a non-answer placeholder, and depth 3 stopped at a parseable but wrong answer.

### Forbidden interpretations

- Do not call stopped output spontaneous raw no-CoT.
- Do not claim hidden-reasoning evidence.
- Do not claim J-space evidence.

## Branch C - Postprocessed answer-recovery utility

### Definition

The raw model output may contain visible reasoning. A deterministic postprocessor extracts or truncates a final-answer span. This branch measures answer-recovery utility, not no-CoT generation.

### Primary metrics

- `raw_no_cot_valid_rate`
- `postprocessed_no_cot_valid_rate`
- `postprocessing_applied_rate`
- `postprocessing_success_rate`
- `postprocessing_warning_rate`
- `accuracy_raw`
- `accuracy_postprocessed`
- `eval_output_used`

### Interpretation

If raw validity is low while postprocessed validity is high, the model still leaked visible reasoning. The postprocessor only cleaned the surface output.

### Forbidden interpretations

- Do not claim postprocessing proves no-CoT.
- Do not merge postprocessed accuracy with raw strict accuracy.
- Do not claim J-space evidence.

## Branch-specific success criteria

These thresholds are registered before any new limited-scale Phase 1 run. They do not authorize a run or a scale increase. The absolute-accuracy, baseline-validity, and sample-size guards below were added prospectively after the 2026-07-10 criteria-validation pilot exposed weaknesses in the earlier rules. The completed pilot and its persisted summary remain unchanged.

For each reported model x task family x depth x branch result, `n` is the number of observations entering the classification. Missing required metrics fail the corresponding criterion rather than being imputed. Non-applicable metrics remain `NA`. Any later roll-up must preserve branch separation and must not average across answer-control branches.

### Shared evidence guards

Formal success requires:

```text
n >= 3
```

When `n < 3`, clear failures retain their failure label. A result that otherwise passes every success criterion is downgraded to its branch-specific `pilot_only` label. Every classification with `n < 3` is marked provisional.

A matching visible-CoT baseline is valid only when:

```text
visible_cot_n >= 3
visible_cot_parse_valid_rate >= 0.80
visible_cot_accuracy > 0
```

`visible_cot_answer_format_warning_rate` is reported but is not a baseline-validity gate in this revision. Baseline failures are recorded as:

```text
visible_cot_baseline_unavailable
insufficient_visible_cot_samples
visible_cot_parse_invalid
visible_cot_accuracy_unavailable
visible_cot_accuracy_zero
```

If the baseline is invalid, the relative accuracy gate is `NA`, is listed in `criteria_not_applicable`, and is never counted as passed. An invalid relative baseline does not replace or weaken a branch's absolute accuracy floor.

### Branch A - `raw_strict`

`raw_strict_preliminarily_established` requires:

```text
n >= 3
raw_no_cot_valid_rate >= 0.90
visible_reasoning_marker_rate <= 0.10
parse_valid_rate >= 0.80
parse_ambiguous_rate <= 0.20
answer_format_warning_rate <= 0.20
accuracy_raw >= 0.50
```

When the matching visible-CoT baseline is valid, raw strict must additionally satisfy:

```text
accuracy_raw >= 0.70 * visible_cot_accuracy
```

The relative gate cannot substitute for `accuracy_raw >= 0.50`. If the baseline is invalid, the relative gate is `NA` and the absolute floor remains required.

Classification labels:

- `raw_strict_not_established`: raw surface no-CoT criteria fail.
- `surface_answer_only_but_task_failed`: surface criteria pass, but parsing, formatting, or accuracy criteria fail.
- `raw_strict_pilot_only`: every substantive success criterion passes, but `n < 3`.
- `raw_strict_preliminarily_established`: every required criterion passes.

Low raw validity means raw strict no-CoT is not established. High raw validity with collapsed accuracy may be surface-compliant but task-useless. A passing classification remains behavioral only and does not establish hidden reasoning or J-space.

### Branch B - `stopped_intervention`

`stopped_intervention_usable` requires:

```text
n >= 3
stopped_no_cot_valid_rate >= 0.90
stop_success_rate >= 0.80
parse_valid_rate >= 0.80
accuracy_stopped >= 0.50
```

When the matching visible-CoT baseline is valid, stopped intervention must additionally satisfy:

```text
accuracy_stopped >= 0.70 * visible_cot_accuracy
```

If the baseline is invalid, this relative gate is `NA`; the absolute stopped-accuracy floor remains required.

Every report must also include:

```text
stop_triggered_rate
stop_string distribution
raw_no_cot_valid_rate
```

Classification labels:

- `stopped_intervention_not_useful`: stopped validity, stop success, or parse validity fails.
- `stopped_surface_compliant_but_task_failed`: surface and parse criteria pass, but absolute or applicable relative stopped accuracy fails.
- `stopped_intervention_pilot_only`: every substantive success criterion passes, but `n < 3`.
- `stopped_intervention_usable`: every required criterion passes.

If `stop_triggered_rate > 0`, the result is intervention-controlled. High stopped validity does not imply spontaneous no-CoT. Accuracy collapse means the intervention suppresses visible reasoning but is not useful for task performance.

### Branch C - `postprocessed_utility`

`postprocessed_answer_recovery_usable` requires:

```text
n >= 3
postprocessed_no_cot_valid_rate >= 0.90
postprocessing_success_rate >= 0.80
postprocessing_warning_rate <= 0.20
accuracy_postprocessed >= accuracy_raw
accuracy_postprocessed >= 0.50
```

Non-degradation and absolute utility are separate hard gates. `0 >= 0` can pass non-degradation but cannot pass the absolute utility gate. A visible-CoT-relative comparison is reported when the matching baseline is valid, but it is not a hard postprocessed-utility criterion in this revision.

Every report must also include:

```text
raw_no_cot_valid_rate
postprocessing_applied_rate
postprocessing_warning_rate
```

Classification labels:

- `postprocessed_utility_not_useful`: the answer-recovery criteria do not pass.
- `postprocessed_surface_clean_but_task_failed`: postprocessed validity passes, but `accuracy_postprocessed < 0.50`; this task-failure label takes priority over a simultaneous warning-rate failure.
- `postprocessed_surface_clean_but_warning_high`: postprocessed output is surface-clean, its absolute accuracy floor passes, but warning rate exceeds the threshold.
- `postprocessed_utility_pilot_only`: every substantive success criterion passes, but `n < 3`.
- `postprocessed_answer_recovery_usable`: every required criterion passes.

High postprocessed validity means only that the extracted answer span is surface-compliant. It does not mean the raw output was no-CoT. Low raw validity with high postprocessed validity is answer-recovery utility, not no-CoT generation.

### Classification boundary

Branch classifications are behavioral and operational. Success labels require the registered minimum sample size. Results based on fewer than three observations per branch/depth are pilot-level and cannot establish branch reliability. Relative accuracy criteria are applied only when the visible-CoT baseline has sufficient samples, valid parsing, and nonzero accuracy. Non-degradation alone is not answer-recovery success. No classification establishes hidden reasoning, internal workspace behavior, or J-space evidence.

## Required output separation

Every applicable record must preserve:

- `phase1_branch`
- `phase1_branch_label`
- `phase1_branch_interpretation`
- `raw_output`
- `raw_output_before_stop_cleanup`
- `stopped_output`
- `postprocessed_output`
- `eval_output_used`
- `raw_no_cot_valid`
- `stopped_no_cot_valid`
- `postprocessed_no_cot_valid`
- `raw_correctness`
- `stopped_correctness`
- `postprocessed_correctness`
- `stop_control_enabled`
- `stop_triggered`
- `stop_string`
- `stop_reason`
- `stop_mode`
- `postprocessing_applied`
- `postprocessing_strategy`
- `postprocessing_reason`
- `postprocessing_warning`

Aggregated reports must use `NA` for branch metrics that do not apply. The legacy `accuracy` field follows `eval_output_used`; branch comparisons must use `accuracy_raw`, `accuracy_stopped`, or `accuracy_postprocessed`.

## Global scientific boundary

Phase 1 is behavioral and methodological validation. None of these branches alone establishes hidden reasoning or J-space representations.
