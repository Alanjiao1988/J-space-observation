# Phase 1 no-CoT Conditions

## Versioning

Prospective records use `branch_taxonomy_version: v2`. Readers treat a missing version as historical `v1`.

Each new record carries `legacy_phase1_branch`, `prospective_phase1_branch`, and deprecated `phase1_branch`. The alias `phase1_branch` always equals `legacy_phase1_branch`; it exists only for compatibility. Historical records, labels, hashes, reports, logs, and Blob objects are never rewritten.

## Condition registry

| Condition | `v2` branch | Intervention stage | Interpretation |
|---|---|---|---|
| `strict_answer_only` | `prompt_only_raw_strict` | None; instruction only | The only condition eligible for the strongest spontaneous surface no-CoT discussion. |
| `strict_answer_only_prefill_answer` | `prefill_intervention` | Answer-prefix prefill | Intervention-controlled, not raw or spontaneous. |
| `strict_answer_only_empty_think_prefill` | `prefill_intervention` | Structural assistant prefill | Intervention-controlled structural suppression. |
| `strict_answer_only_stopped` | `stopped_intervention` | Generation-time stopping | Stopped validity is not spontaneous validity. |
| `strict_answer_only_postprocessed` | `postprocessed_utility` | Post-hoc extraction/truncation | Measures answer-recovery utility only. |
| `visible_cot` | `visible_reasoning_baseline` | Visible reasoning allowed | Behavioral baseline. |
| `r1_style_thinking` | `visible_reasoning_baseline` | Visible R1-style reasoning allowed | Behavioral baseline. |

Unknown conditions are rejected before run-directory creation, model loading, generation, or upload.

## Prompt-only condition

`strict_answer_only` uses one model-independent prompt constructor. It never contains `<think>` or `</think>` and is never rerouted according to model name.

## Prefill interventions

### Answer prefix

`strict_answer_only_prefill_answer` ends at an answer cue. It is an answer-prefix intervention and must not be grouped with raw prompt-only behavior.

### Empty think

`strict_answer_only_empty_think_prefill` uses raw assistant-prefill content exactly:

```text
<think>
</think>
```

It is selected only by the explicit condition. The tokenizer-only helper receives the tokenizer and optional chat template, then records:

- `raw_prefill`
- `rendered_chat_text`
- `token_ids`
- `decoded_tokens`
- `assistant_prefix_boundary` with character and token indices
- the rendered assistant prefix and its token IDs

The helper calls the supplied chat template for both text rendering and tokenization. It does not tokenize the rendered string as a substitute. Generation consumes the captured input token IDs.

Prefill evidence may at most support an internal-representation study under structural suppression. It never establishes spontaneous hidden reasoning.

## Classification

Historical `v1` raw/stopped/postprocessed classifier results remain unchanged. Prospective `prefill_intervention` has no preregistered success criteria and therefore reports:

```text
classification: not_applicable
criteria: NA
```

Historical `raw_strict` thresholds must not be reused for prefill rows.

## Dry-run

`experiments/phase1_depth_gradient.py --dry-run` validates condition names first and prints the `v2` crosswalk for every selected condition. It may enumerate model-free prompt capacity, but it does not create a run directory, load a model, generate, or upload.
