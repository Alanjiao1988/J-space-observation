# Phase 1 task-headroom candidate bank

## Result

Track D Phase 1.0C produced a deterministic, model-free bank of **450 design
candidates**. No model, tokenizer, parser holdout, Azure resource, network
service, locked fixture, or historical output was used.

This responds to the audit rather than reusing the earlier tasks. The previous
depth-3 0/3 result cannot establish an ability limit because finish/truncation
instrumentation was incomplete, outputs were often incomplete, legacy parsing
was materially faulty, `n` was tiny, decoding was narrow, and construction was
weak. The new relation references are directed paths checked in code; all
relation/factual premises are in the prompt; all names are synthetic.

## Inventory and exact counts

Each row has five template families per split and ten records per split.

| Family | Band | Calibration | Confirmation | Mechanistic | Total |
|---|---:|---:|---:|---:|---:|
| arithmetic | easy | 10 | 10 | 10 | 30 |
| arithmetic | medium | 10 | 10 | 10 | 30 |
| arithmetic | hard | 10 | 10 | 10 | 30 |
| synthetic_relation | easy | 10 | 10 | 10 | 30 |
| synthetic_relation | medium | 10 | 10 | 10 | 30 |
| synthetic_relation | hard | 10 | 10 | 10 | 30 |
| prompt_grounded_two_hop_factual | easy | 10 | 10 | 10 | 30 |
| prompt_grounded_two_hop_factual | medium | 10 | 10 | 10 | 30 |
| prompt_grounded_two_hop_factual | hard | 10 | 10 | 10 | 30 |
| counterfactual_entity_replacement | easy | 10 | 10 | 10 | 30 |
| counterfactual_entity_replacement | medium | 10 | 10 | 10 | 30 |
| counterfactual_entity_replacement | hard | 10 | 10 | 10 | 30 |
| wrong_cot_error_detection | easy | 10 | 10 | 10 | 30 |
| wrong_cot_error_detection | medium | 10 | 10 | 10 | 30 |
| wrong_cot_error_detection | hard | 10 | 10 | 10 | 30 |
| **Total** |  | **150** | **150** | **150** | **450** |

Totals by family are 90 each. The bank has 225 split-specific template-family
IDs (5 per each of 45 family/band/split cells), 450 available clean/corrupt
pairs, and 900 mechanically checked clean/corrupted references.

## Construction summary

| Family | Easy / medium / hard construction | Answer type |
|---|---|---|
| arithmetic | 2 / 3 / 4 explicit integer operations | numeric |
| synthetic_relation | 2 / 3 / 4 directed hops; 1 / 2 / 3 distractor edges | typed entity |
| prompt_grounded_two_hop_factual | two hops throughout; 0 / 2 / 4 distractor paths | typed entity |
| counterfactual_entity_replacement | scoped replacement plus 2 / 3 / 4 links | typed entity |
| wrong_cot_error_detection | 3 / 4 / 5 proposed steps; first-error numeric code | preregistered numeric code |

Within every family/band/split cell, concepts have ten distinct values. Answers
are also ten distinct values except for the intentionally counterbalanced
wrong-CoT step positions: 2 easy labels (5/5), 3 medium labels (maximum
frequency 4), and 4 hard labels (maximum frequency 3). The paired item five
positions away uses the same template family but a different answer and concept,
providing a registered matched-control selector.

All entity-bearing families use split-specific namespaces; no entity is shared
between calibration, confirmation, and mechanistic splits. Template-family IDs
are likewise split-disjoint. Every prompt is strict answer-only and every
factual/relation premise recorded in metadata occurs literally in its clean or
corrupted prompt.

## Method-suitability inventory

These are **design-candidate counts**, not currently eligible or successful
cases:

| Method | Design candidates | Currently eligible | Boundary |
|---|---:|---:|---|
| J-lens | 450 | 0 | 360 RQ2 candidates plus 90 arithmetic sanity candidates |
| Patching | 450 | 0 | all have a one-surface-token, answer-changing pair |
| Ablation | 360 | 0 | arithmetic excluded as sanity-only |
| Ability matching | 360 | 0 | arithmetic excluded as sanity-only |

Current eligibility is zero because future tokenizer registration, behavioral
calibration, strict-baseline correctness, runtime completeness, truncation,
locked evaluator gates, and method controls have not been run.

J-lens entries require a non-final necessary intermediate, one-token frozen
tokenizer registration, matched and prompt-echo controls, strict answer-only
correctness, and readout outside motor/output layers. Patching entries require
token/position-aligned minimal pairs, different answers, both correct baselines,
the full layer × position scan, and controls. Ablation and ability-matching
requirements are frozen in
`docs/phase1_capability_headroom_protocol.md`.

Arithmetic is only a sanity/patching family in inferential role. It is not the
sole RQ2 evidence.

## Evaluator routes

- 90 arithmetic records are numeric parser-v2 candidates.
- 90 wrong-CoT records use a preregistered numeric step code.
- 270 relation/factual/counterfactual records require a separately locked typed
  entity evaluator.

Parser v2 must pass its separately authorized one-shot locked numeric evaluation
before formal numeric metrics. The present parser-v2 protocol is numeric-only;
a parser-v2 PASS would not validate any of the 270 entity records (or any future
boolean record).

## Reproduction and validation

Canonical bank:

- `data/phase1_task_headroom_candidates.jsonl`
- SHA256:
  `acf59ec44b7afb73c03392d2c9b7223eff7311e29e2261ff0d65b38a3a416407`
- exact schema:
  `data/phase1_task_headroom_candidate.schema.json`

Rebuild:

```text
python scripts\generate_phase1_task_headroom_bank.py
```

Verify without rewriting:

```text
python scripts\generate_phase1_task_headroom_bank.py --check
```

The validator checks the exact schema, unique IDs, exact counts, template and
entity split isolation, reference recomputation, literal fact inclusion,
clean/corrupt integrity, answer/concept balance, matched controls, suitability
fields, deterministic bytes, and standard-library-only generation.

## Caveats

- Difficulty bands are construction labels until future visible-reasoning
  calibration confirms semantic accuracy in [0.70, 0.90].
- Concept token counts and patching token alignment are pending registration
  under the frozen target tokenizer; spelling is not treated as evidence.
- Neither clean nor corrupted model baselines have been executed.
- No parser or typed-evaluator locked gate has been run.
- No item is evidence of hidden reasoning, causal mediation, ability
  equivalence, or a model-level limit.
- Future failures must follow the ordered attribution:
  construction, runtime, truncation, parser, decoding-sensitive, underpowered,
  task-specific capability, then model-level limitation.
