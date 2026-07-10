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
