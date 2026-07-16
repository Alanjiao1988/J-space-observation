# Phase 1 Answer-control Branches

## Purpose

Phase 1 branch records are versioned. Missing `branch_taxonomy_version` means historical `v1`; prospective work must write `v2`. Historical mappings, classifications, reports, and stored records are immutable.

Visible-CoT conditions remain baselines and are not an answer-control branch.

## Prospective taxonomy `v2`

| Branch | Canonical key | Conditions | Experimental question |
|---|---|---|---|
| Prompt-only raw strict no-CoT | `prompt_only_raw_strict` | `strict_answer_only` | Can the raw model satisfy answer-only constraints from instructions alone? |
| Prefill intervention | `prefill_intervention` | `strict_answer_only_prefill_answer`, `strict_answer_only_empty_think_prefill` | What happens under an answer-prefix or structural empty-think intervention? |
| Stop-controlled generation intervention | `stopped_intervention` | `strict_answer_only_stopped` | Can generation-time stopping suppress visible reasoning leakage while retaining a usable answer? |
| Postprocessed answer-recovery utility | `postprocessed_utility` | `strict_answer_only_postprocessed` | Can deterministic postprocessing recover a usable final-answer span from a reasoning-prone raw output? |
| Visible-reasoning baseline | `visible_reasoning_baseline` | `visible_cot`, `r1_style_thinking` | What is performance when visible reasoning is allowed? |

Only `prompt_only_raw_strict` supports the strongest discussion of spontaneous surface no-CoT behavior. It remains behavioral evidence and does not itself establish hidden reasoning.

## Historical taxonomy `v1`

| Condition | Historical `v1` branch |
|---|---|
| `strict_answer_only` | `raw_strict` |
| `strict_answer_only_prefill_answer` | `raw_strict` |
| `strict_answer_only_empty_think_prefill` | `unclassified` |
| `strict_answer_only_stopped` | `stopped_intervention` |
| `strict_answer_only_postprocessed` | `postprocessed_utility` |
| `visible_cot`, `r1_style_thinking` | `visible_reasoning_baseline` |

Historical answer-prefill results remain `raw_strict` only as legacy history. They must not be reclassified in stored Blob data, old reports, historical logs, hashes, or labels.

Every new record includes:

- `branch_taxonomy_version`
- `legacy_phase1_branch`
- `prospective_phase1_branch`
- deprecated `phase1_branch`, always equal to `legacy_phase1_branch`

## `prompt_only_raw_strict`

### Definition

The model is prompted and decoded to produce an answer-only response without prefill, generation-time stop intervention, or post-hoc answer extraction. `strict_answer_only` uses the same prompt-only construction for every model and contains no think tags.

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

## `prefill_intervention`

### Definition

This branch contains two distinct interventions:

- `strict_answer_only_prefill_answer`: answer-prefix intervention ending at the answer cue.
- `strict_answer_only_empty_think_prefill`: structural assistant prefill with raw content exactly `<think>\n</think>`.

Empty-think is selected only by its explicit condition, never by model-name routing. The tokenizer/chat-template rendering record preserves the raw prefill, rendered chat text, token IDs, decoded tokens, and assistant-prefix boundary.

### Interpretation boundary

Prefill results are not raw prompt-only behavior. They may at most support an internal-representation study under structural suppression; they never support a spontaneous hidden-reasoning claim.

Prospective `prefill_intervention` has no preregistered success criteria. Reports must show `not_applicable`/`NA`, not historical `raw_strict` classifications.

## Branch B - Stop-controlled generation intervention

### Definition

Generation-time stop criteria constrain a prompt-only emitted sequence. The exact generated output before stop cleanup and the cleaned stopped output are preserved separately. This condition does not add a prefill intervention.

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

The prompt-only raw model output may contain visible reasoning. A deterministic postprocessor extracts or truncates a final-answer span. This branch measures post-hoc answer-recovery utility, not no-CoT generation, and does not add a prefill intervention.

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

The criteria below are historical `v1` raw/stopped/postprocessed classifier semantics. They are retained exactly for audit recomputation and do not authorize a run or scale increase. The absolute-accuracy, baseline-validity, and sample-size guards were added after the 2026-07-10 criteria-validation pilot exposed weaknesses in the earlier rules. The completed pilot and its persisted summary remain unchanged.

When the `v1` raw criteria are explicitly shown for a prospective `prompt_only_raw_strict` row, reports identify `classification_criteria_version=v1` and `classification_criteria_branch=raw_strict`. They are not silently applied to `prefill_intervention`; that branch reports `not_applicable`/`NA`.

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

- `branch_taxonomy_version`
- `legacy_phase1_branch`
- `prospective_phase1_branch`
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
