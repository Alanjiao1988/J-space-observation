# Phase 1.0C Track B — bounded capability/headroom calibration protocol

Protocol version: `phase1-headroom-calibration-protocol-v1`
Schema version: `phase1-headroom-calibration-v1`
Phase: `1.0C`  Track: `track-b`
Preregistered: 2026-07-25 (before any target-model generation for this track)

## 1. Status and claim boundary

This document preregisters an **actual target-model run**, but that run is **task
calibration, not a formal RQ1/RQ2 result**. Its only purpose is to find task cells
where the target model has measurable observable-answer headroom, so that later
ablation and activation-patching experiments are not run on cells that are already
saturated or already impossible.

**Scientific claim boundary (registered, copied verbatim into
`01_protocol_snapshot.json`):**

> This run estimates observable answer accuracy of a single target model on a frozen
> task bank under two visible-reasoning prompt conditions, for the sole purpose of
> selecting task cells with measurable headroom. It licenses no claim about hidden
> reasoning, internal representations, or "J-space", and it is not a formal RQ1/RQ2
> result.

**Prohibited interpretations (registered; also emitted in `04_decision.json`):**

1. Any claim that this run observes, measures, or bounds hidden reasoning.
2. Any claim about an internal workspace, latent scratchpad, or invisible
   chain-of-thought.
3. Any claim about "J-space" existence, structure, capacity, or dynamics.
4. Any RQ1 or RQ2 result claim; this is task calibration, not a formal result.
5. Any pass@k or sampling-capability claim; one sample per item/condition is drawn.
6. Any claim that parser v2 output is a validated correctness label.
7. Any generalisation to conditions deferred this round.

Additionally, a low-accuracy cell is a task-difficulty screening signal only and
never evidence of model inability; a high-accuracy cell is never evidence of a
capability ceiling.

This protocol is consistent with, and subordinate to,
`docs/phase1_capability_headroom_protocol.md` (Track D). Where the two disagree, the
Track D split discipline and evaluator gate win.

## 2. Research question

> Which frozen Phase 1 task cells (task family × difficulty band × visible-reasoning
> condition) leave the target model measurable observable-answer headroom, so that
> later ablation and activation-patching experiments are not run on saturated or
> impossible tasks?

This is a screening question about *tasks*, not a question about the model's
internals.

## 3. Target model and code

| Field | Value |
| --- | --- |
| `model_id` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` |
| `model_revision` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| implementation | `src/jspace_observation/headroom_calibration.py` |
| entrypoint | `scripts/run_phase1_headroom_calibration.py` |
| `code_commit` | resolved at runtime from `.git` and recorded in `00_stage_manifest.json` |
| `image_digest` | supplied by the main agent at run time and recorded verbatim |

The revision is pinned. A run whose resolved revision differs from the pinned value
must be recorded as a deviation and its cells must not be used for selection.

## 4. Item selection (deterministic, no RNG draw)

Source bank: `data/phase1_task_headroom_candidates.jsonl` (frozen, 450 records,
`task_bank_sha256 = acf59ec44b7afb73c03392d2c9b7223eff7311e29e2261ff0d65b38a3a416407`).

The required sample is 5 task families × 3 difficulty bands × 10 items = **150 unique
items**. The bank already stores exactly 10 items per family × band in the
`calibration` split, and Track D mandates whole-cell retention with no item-level
filtering. The registered selection rule is therefore:

> Select every bank record whose `split == "calibration"`, then order by `task_id`
> under a stable total order.

This is a *complete* selection of the calibration split, so no random draw is taken
and no item can be silently dropped. `SELECTION_SEED = 20260725` is still registered
and recorded because it seeds the deterministic review sampling and the review-ID
ordering; it is not used to choose items.

Selection is verified at run time by `select_calibration_items()`, which asserts
150 unique IDs, 30 per family, 50 per band and 10 per family × band, and by
`selection_summary()`, which records:

| Field | Value |
| --- | --- |
| `split` | `calibration` |
| `item_count` | 150 |
| per family | 30 each for `arithmetic`, `synthetic_relation`, `prompt_grounded_two_hop_factual`, `counterfactual_entity_replacement`, `wrong_cot_error_detection` |
| per band | 50 each for `easy`, `medium`, `hard` |
| per family × band | 10 each (15 cells) |
| `task_ids_sha256` | `d5120ea87f610ee3c990e00078ea48d7cbcadf3c3c363d95b65c649ed078e53a` |

`task_ids_sha256` is the SHA-256 of the newline-joined sorted selected `task_id`
list. Any change to the bank or the selection rule changes this digest and
invalidates the pack.

The `confirmation` and `mechanistic` splits stay held out. They are not read, not
prompted, and not scored in this round.

## 5. Conditions

Run this round (2 conditions × 150 items = **300 generations**):

- `visible_cot`
- `r1_style_thinking`

**Deferred, explicitly not run this round** (registered in
`01_protocol_snapshot.json` under `conditions.deferred`):

- `prompt_only_raw_strict`
- `empty_think_prefill`
- `answer_prefill`
- `stopped`
- `postprocessed`

Deferral is a scope decision, not a result. No comparison involving a deferred
condition may be made from this pack.

### 5.1 Registered prompt override (`prompt_override_v1`)

The frozen bank questions end with strict answer-only closings (for example
"Return only the integer; do not explain."). Those closings contradict both
visible-reasoning conditions. The bank is frozen and **must not be mutated**, so the
registered resolution is an *additive suffix* appended after the condition prompt
built by `no_cot.construct_visible_cot_prompt()` /
`no_cot.construct_r1_style_thinking_prompt()`:

- override id: `prompt_override_v1`
- effect: supersedes the item's answer-only instruction for this run only, and
  requires the model to end with a single line `Final answer: <answer>`
- the exact override text and its SHA-256 are stored in
  `01_protocol_snapshot.json` and are hashed into `protocol_hash`

The final line marker is what makes the deterministic triage layer able to locate a
candidate answer without guessing a span.

## 6. Generation profile (frozen and registered)

| Field | Value |
| --- | --- |
| `max_new_tokens` | 512 |
| `temperature` | 0.6 |
| `top_p` | 0.95 |
| `do_sample` | `true` |
| `decoding_profile` | `official_style` |
| samples per item × condition | 1 |
| `replicate_index` | 0 |
| `run_base_seed` | 20260725 |
| per-generation seed | `headroom_candidates.derive_run_seed(task_id, condition, 512, "official_style", 0)` |

One sample per item per condition is deliberate: the goal is **task screening**, not
pass@k estimation. No pass@k statistic may be computed or reported from this pack.

`no_cot.validate_phase1_conditions()` is still called so the condition names stay
consistent with the repository registry. Note that
`no_cot.get_generation_config_for_condition()` returns the repository's
`default_greedy` profile (temperature 1.0, top_p 1.0, `do_sample=False`) for these
conditions; this run intentionally overrides it with the `official_style` sampling
profile above, and that override is registered in `generation_profile` rather than
applied silently.

## 7. Metrics

**Primary metric**

- `semantic_accuracy_per_cell` — adjudicated correct / 10, computed per
  cell = task family × difficulty band × condition (30 cells). Cells are never
  pooled across conditions or bands for the selection decision.

**Secondary metrics**

- `truncation_rate` per cell
- `no_answer_rate` per cell
- `triage_parse_valid_rate` per cell
- `unresolved_label_rate` per cell
- `review_coverage_rate` (rows with an adjudicated label / rows flagged for review)
- `review_load_fraction` (rows flagged for review / 300)
- `selected_headroom_cell_count` (selected cells / 30)

All rate metrics are reported in `03_metrics.csv` with two-sided 95% Wilson score
confidence intervals. The repository helper `stats.wilson_ci` is used when it is
importable; otherwise a numerically identical stdlib implementation
(z = 1.959963984540054) is used, and which one was used is recorded.

With n = 10 per cell the intervals are wide (for example 8/10 → [0.490, 0.943]).
That width is expected and is exactly why the selection rule below is a screening
rule and not an estimate of true ability.

## 8. Evaluation and adjudication

### 8.1 Deterministic triage is screening only

Parser v2 (`src/jspace_observation/eval_parsing_v2.py`) is used **read-only** as an
automatic triage tool for `numeric` and `numeric_step_code` answer types. Its formal
locked validation **FAILED** on 2026-07-25 (`boxed_final_miss` 1/20, `wrong_span`
2/80). That status is recorded in the pack as
`parser_v2_locked_validation_status = "failed_2026-07-25:boxed_final_miss=1/20,wrong_span=2/80"`
and `triage_authority = "screening_only_not_locked"`.

**Parser v2 alone must never decide a final calibration label.**

For `entity` answer types the repository has no locked evaluator, so this run uses a
deliberately weak, explicitly non-authoritative surface matcher
`entity_surface_match_v1`: word-boundary matching of registered entity ids in the
text after the last `</think>`, preferring the final non-empty line, marking more
than one distinct candidate as ambiguous and marking a match found only earlier in
the output as ambiguous with reason `answer_not_in_final_line`. It exists to route
rows to review, never to score them.

### 8.2 Bounded semantic review

The primary label for every scored row comes from a **semantic reviewer**, not from
triage. Full review of all 300 rows is *not* required. A row is sent to review when
it falls into any mandatory category, or when it is drawn in the deterministic
random sample:

1. `parse_invalid` — triage could not produce a valid parse
2. `ambiguous_parse` — triage found more than one plausible answer span
3. `truncated_output` — the generation hit the token budget or ended mid-answer
4. `no_answer` — no answer was located at all
5. `triage_disagrees_with_registered_answer` — triage parsed an answer that differs
   from the registered reference answer
6. `provisional_headroom_cell` — every row of any cell whose provisional correct
   count is at least `PROVISIONAL_REVIEW_MIN_CORRECT = 6`, i.e. every cell that could
   still land in or above the headroom band
7. `deterministic_random_sample` — `ceil(0.10 × n)` of the remaining clean rows,
   chosen by sorting on
   `sha256("jspace-headroom-calibration/review-sample/v1\0{SELECTION_SEED}\0{record_id}")`

Categories 1–6 implement the required "review everything questionable and everything
heading into a selected cell" rule; category 7 implements the required deterministic
10% audit of the remainder.

Rows shown to the primary reviewer are **blinded** to the triage verdict: the triage
result lives in `review_pack/deterministic_triage.jsonl`, not in
`review_pack/review_pack.jsonl`. Review IDs `R001…Rnnn` are assigned by a
deterministic hash order so the pack is stable across re-emission.

### 8.3 Arbitration

An arbiter is invoked **only** when the primary reviewer's label conflicts with a
definite deterministic verdict for the same row. Rows with no conflict are resolved
by the primary reviewer alone. A conflicted row stays `unresolved` until an arbiter
judgment is supplied, and any cell containing an unresolved row cannot be selected.
`review_pack/arbitration_packet.jsonl` lists exactly the conflicted rows.

### 8.4 Known review-load tension (registered)

Requirement 5 ("review all rows heading into selected headroom cells") and the 10%
sampling requirement interact: if many cells are provisionally in band, the mandatory
categories can escalate toward reviewing all 300 rows. This is a deliberate
consequence of preferring adjudicated labels over parser output for every cell that
could be selected. The pack always reports `review_load_fraction` so the load is
visible before review is commissioned, and the
`supplementary_review_required` block of
`cell_selection/cell_exclusion_reasons.json` lists cells blocked *only* by
incomplete review coverage so review can be extended cell-by-cell instead of
wholesale.

## 9. Headroom cell selection rule (implemented in code)

Implemented in `headroom_calibration.score_cells()`. A cell = task family ×
difficulty band × condition; there are 30 cells. A cell **qualifies as a selected
headroom cell** when all of the following hold:

| Gate | Threshold |
| --- | --- |
| `n` | exactly 10 |
| adjudicated accuracy | within `[0.70, 0.90]` |
| adjudicated correct count | at least 7 |
| truncation rate | ≤ 0.10 |
| no-answer rate | ≤ 0.10 |
| unresolved semantic labels | exactly 0 |
| review coverage | complete for every mandatory row in the cell |

Classification of non-qualifying cells:

- accuracy > 0.90 → `control_sanity_high_accuracy` — usable as a sanity/control cell
  but deprioritized as a main ablation cell, because there is little damage headroom
- accuracy < 0.70 → `difficulty_boundary_excluded` — excluded from main
  patching/ablation, retained as a difficulty boundary
- any quality gate failed → `excluded_quality_gate`
- adjudication incomplete → `not_adjudicated`

Machine-readable exclusion reason codes: `accuracy_above_band_control_only`,
`accuracy_below_band_difficulty_boundary`, `incomplete_cell_n`,
`incomplete_review_coverage`, `insufficient_correct_count`,
`labels_not_semantically_adjudicated`, `no_answer_rate_above_threshold`,
`truncation_rate_above_threshold`, `unresolved_semantic_labels_present`.

Outputs: `cell_selection/selected_headroom_cells.csv`,
`cell_selection/excluded_cells.csv`, and
`cell_selection/cell_exclusion_reasons.json`. Every excluded row carries its
reason codes.

Selection is **descriptive screening**. A selected cell means "this cell shows
measurable observable headroom in this calibration run", not "the model can or
cannot do this task".

## 10. Decision rules

Registered in `01_protocol_snapshot.json` under `decision_rules` and evaluated in
`04_decision.json`:

1. Every one of the 300 registered work units must be attempted.
2. Every scored row must carry an adjudicated label or be counted as unresolved.
3. A cell may be selected only if all seven gates in §9 pass.
4. Parser v2 output may never be the final label for any row.
5. Accuracy above 0.90 demotes a cell to control/sanity, never to selected.
6. Accuracy below 0.70 excludes a cell from ablation but retains it as a boundary.
7. Any deviation from the frozen generation profile invalidates affected cells.
8. Any change to the task bank digest or selected-ID digest invalidates the pack.
9. A pack with outstanding mandatory reviews is `INCONCLUSIVE`, never `COMPLETE`.
10. No decision in this pack may be promoted into an RQ1/RQ2 claim.

**Status values** (`04_decision.json.status`):

| Mode | Status | Meaning |
| --- | --- | --- |
| `plan` | `BLOCKED` | Pack is fully specified; awaiting main-agent Azure GPU execution |
| `generate` | `INCONCLUSIVE` | Real generations exist; awaiting semantic review |
| `finalize` | `COMPLETE` | Review applied, cells scored |
| `finalize` | `INCONCLUSIVE` | Outstanding mandatory reviews or unresolved labels remain |
| any | `FAIL` | A registered gate that must hold did not hold |

## 11. Inclusion rules

1. Only the frozen `calibration` split of `data/phase1_task_headroom_candidates.jsonl`.
2. Whole cells only: all 10 items of each family × band cell are run.
3. Only conditions `visible_cot` and `r1_style_thinking` this round.
4. Exactly one sample per item per condition.

## 12. Exclusion rules

1. The `confirmation` and `mechanistic` splits stay held out and are not run.
2. No item-level filtering, dropping, or re-sampling after outputs are seen.
3. No condition outside the two registered conditions is scored this round.
4. No pass@k aggregation; a single sample per item/condition is drawn.

## 13. Stopping rules

1. Generation stops after exactly 300 units of work (150 items × 2 conditions).
2. Generation stops early only on an infrastructure fault; partial packs are marked
   `BLOCKED`.
3. No adaptive stopping on observed accuracy is permitted.

## 14. Retry rules

1. A unit may be retried only after an infrastructure fault, never after an unwanted
   result.
2. A retry reuses the identical frozen seed, prompt, and decoding profile.
3. Every retry is recorded in `08_deviations.json` with its cause.
4. No prompt, seed, decoding, or scoring parameter may change during a retry.

## 15. Artifact pack

Emitted into `phase1-headroom-calibration/track-b/<run_id>/`. `artifact_manifest.json`
is always written **last** and lists every other file with its SHA-256 and byte size.

| File | Content |
| --- | --- |
| `00_stage_manifest.json` | schema_version, phase, track, run_id, status, start/end time, objective, hypothesis, scope, out_of_scope, model_id, model_revision, code_commit, image_digest, hardware, subagents, inputs, protocol_hash, output_files |
| `01_protocol_snapshot.json` | this protocol in machine-readable form |
| `02_records.jsonl` | one line per generation with record_id, run_id, phase, track, source_item_id, condition, status, input_hash, output_hash, evaluation |
| `03_metrics.csv` | run_id, phase, track, metric, stratum, condition, n, numerator, denominator, value, ci_lower, ci_upper, threshold, passed, not_applicable_reason |
| `04_decision.json` | status, decision, criteria_passed, criteria_failed, criteria_not_applicable, deviations, scientific_interpretation, prohibited_interpretations, next_gate |
| `05_summary.md` | fixed section order: Summary, Objective, Scope, Provenance, Execution, Results, Decision, Deviations and errors, Scientific interpretation, Limitations, Paper relevance, Next gate |
| `06_paper_table.csv` | per-cell table for the paper |
| `07_figure_data.csv` | tidy per-cell figure data |
| `08_deviations.json` | `{"deviations": [], "unregistered_changes": [], "effect_on_interpretation": "none"}` when empty |
| `artifact_manifest.json` | written last; digests of all of the above |

Two subdirectories carry the review and selection payloads required by this
protocol. They are additional to, not substitutes for, the ten canonical files:

- `review_pack/` — `review_pack_manifest.json`, `review_pack.jsonl` (blinded),
  `deterministic_triage.jsonl`, `arbitration_packet.jsonl`, `review_instructions.md`
- `cell_selection/` — `selected_headroom_cells.csv`, `excluded_cells.csv`,
  `cell_exclusion_reasons.json`

Every file is generated even when it has no applicable content; in that case it
carries `status = "not_applicable"` and a `reason`.

**Provenance rule:** no output text is ever emitted without provenance. Every record
line carries `input_hash` and `output_hash`, and no free-standing generation dump is
produced.

## 16. Determinism requirements

- Fixed seeds; sorted iteration everywhere; stable JSON key ordering
  (`sort_keys=True`, `indent=2`, `ensure_ascii=False`, trailing newline).
- JSONL uses compact separators; CSV uses `lineterminator="\n"`.
- All files are written as UTF-8 bytes with LF newlines, on Windows and Linux alike.
- `--frozen-time` / `JSPACE_FROZEN_TIME` injects the clock so packs are
  byte-reproducible.
- `code_commit` is read directly from `.git` metadata; the tool never shells out to
  git and never mutates the repository.

Byte-level reproducibility is verified by re-emitting a pack with the same inputs and
comparing SHA-256 digests of every file.

## 17. Execution modes

| Mode | Purpose | GPU |
| --- | --- | --- |
| `plan` (`--dry-run`) | Emit the fully specified pack with no model call | no |
| `generate` | Real target-model generation in the Azure GPU container | yes |
| `finalize` | Apply reviewer/arbiter judgments to an existing `02_records.jsonl` and score cells | no |
| `self-test` | Deterministic synthetic backend for CI; emits a registered deviation stating the outputs are fixtures | no |

`finalize` requires `--records` pointing at a prior `02_records.jsonl`. Review flags
are read from that file and never recomputed, so review IDs stay stable across the
generate → review → finalize sequence.

Backends are dependency-injected (`GenerationBackend` protocol), so unit tests run on
CPU without `torch`, without `transformers`, and without downloading the model.

## 18. Deferred work

- The five deferred conditions in §5 remain unrun and unscored.
- No mechanistic or patching experiment is authorized by this pack.
- Any future use of a selected cell must re-check the cell against the then-current
  evaluator gate before it is used for an RQ1/RQ2 claim.

## 19. Related documents

- `docs/phase1_capability_headroom_protocol.md` — Track D bank and gate design
- `docs/phase1_semantic_review_protocol.md` — semantic review conventions
- `docs/phase1_headroom_calibration_run.md` — the Azure run specification
- `reports/phase1_task_headroom_candidate_bank.md` — bank construction report

