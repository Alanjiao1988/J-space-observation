# Phase 0.5B: J-lens saturation and merge validation protocol

## Status and boundary

Preregistered. Track A, engineering feasibility only.

Phase 0.5A established that the pinned official Jacobian lens can fit two
prompts across three source layers on one T4 (`reports/phase05_jlens_feasibility.md`).
Phase 0.5B asks a strictly larger *engineering* question: does the same
pipeline still work at 10 and at 25 prompts, does a sharded fit followed by
the official merge reproduce a direct fit, and do the resulting matrices and
applied logits stay numerically stable.

This protocol produces **no** scientific, semantic, or interpretive result.
The following statements are prohibited for every artifact this run emits:

- "workspace found"
- "J-space validated"
- "hidden reasoning observed"
- "internal workspace"
- "invisible chain-of-thought"
- treating top-k overlap or rank correlation as semantic evidence

Top-k overlap and Spearman rank correlation appear only as **technical
stability statistics** comparing two fitted linear operators. They say
nothing about model cognition.

## Research question

Can the pinned official Jacobian lens be fit at 10 prompts and at 25 prompts
(sharded 10/10/5 then merged) on one T4 inside the registered time and memory
envelope, with finite matrices, exact fp32 serialization, merge/direct-subset
agreement within tolerance, and measurable convergence and apply stability
between the 10-prompt and the 25-prompt lens?

## Immutable provenance

| Item | Value |
|---|---|
| Official source | `https://github.com/anthropics/jacobian-lens` |
| Official commit | `581d398613e5602a5af361e1c34d3a92ea82ba8e` |
| Distribution / import name | `jlens` 0.1.0 |
| Target model | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` |
| Model revision | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| Runtime dtype | `float16` |
| Lens serialization dtype | `float32` |
| Source layers | `[6, 13, 20]` |
| Target layer | `27` |
| `max_seq_len` | `32` |
| `skip_first` | `16` |
| `dim_batch` | `1` by default |

Every value above is inherited unchanged from Phase 0.5A
(`src/jspace_observation/phase05_jlens.py`). No parser file, evaluator set,
locked artifact, or behavioral candidate is read, written, or referenced.

`dim_batch` may be raised to `2` only by passing `--dim-batch 2`. That path
records a deviation in `08_deviations.json` citing the Phase 0.5A F2
measurement (peak reserved 3 808 428 032 of 16 704 405 504 bytes, ratio
0.2280, classification green) and the completed F3 fit at `dim_batch=2`.
Any other value is rejected by the CLI.

## Fit corpus

`data/jlens_saturation_prompts.jsonl` — 50 deterministic generic prompts.

| Property | Value |
|---|---|
| Records | 50 |
| File SHA-256 | `41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b` |
| Canonical JSONL SHA-256 | `41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b` |
| Bytes | 13 452 |
| Newlines | LF only, UTF-8, one JSON object per line |
| Fields | `id`, `role`, `text` only — no answers, no labels |
| Roles | `fit` 25, `heldout` 10, `reserve` 15 |
| Proxy token range | 38–44 |
| Proxy tokenizer | `regex_word_punctuation_proxy_v1` (`\w+|[^\w\s]`) |

The proxy tokenizer is used because the Hugging Face tokenizer is not
available off-container. It is a lower bound in practice: every prompt has at
least 33 proxy units, which guarantees the container-side
`guarded_token_length` truncation to `max_seq_len = 32` is deterministic and
identical for every prompt. The container additionally records the real
guarded tokenizer length for every fit and held-out prompt in
`02_records.jsonl` (metric `corpus_token_count`).

Provenance of the corpus:

- Written independently for this track; not drawn from
  `data/phase1_task_headroom_candidates.jsonl` (verified zero text overlap),
  not from `data/jlens_feasibility_prompts.jsonl`, not from any parser
  fixture, and not from anything under `evaluator_sets/`.
- No prompt contains any of the forbidden cues `phase1`, `phase 1`,
  `evaluator`, `locked`, `reference answer`, `answer-only`; the loader
  rejects the corpus if one appears.
- Every prompt is a neutral third-person description of a mundane process.
  None asks for a scored answer.

### Per-prompt registration

| ID | Role | Proxy tokens | Characters | Text SHA-256 (first 16) |
|---|---|---:|---:|---|
| `sat-fit-001` | fit | 44 | 222 | `badb59206d9ab3d7` |
| `sat-fit-002` | fit | 41 | 205 | `7af747b7ea7ae6d4` |
| `sat-fit-003` | fit | 40 | 220 | `9d1da25ea9eebda7` |
| `sat-fit-004` | fit | 42 | 219 | `bf0fd8e1f750952f` |
| `sat-fit-005` | fit | 41 | 223 | `bc8a6afb421c4784` |
| `sat-fit-006` | fit | 43 | 228 | `a2286fbde4a5d415` |
| `sat-fit-007` | fit | 43 | 231 | `3d1fe5e36d4741bd` |
| `sat-fit-008` | fit | 44 | 206 | `b72b9864bc2066e0` |
| `sat-fit-009` | fit | 40 | 225 | `2656371f793c290f` |
| `sat-fit-010` | fit | 42 | 238 | `895873feebbb92f5` |
| `sat-fit-011` | fit | 42 | 219 | `99cea7603f3d4554` |
| `sat-fit-012` | fit | 41 | 227 | `c532f97f1e814ebc` |
| `sat-fit-013` | fit | 40 | 215 | `8ecdc1cffd21ab18` |
| `sat-fit-014` | fit | 40 | 220 | `d4bdd3945b625504` |
| `sat-fit-015` | fit | 41 | 216 | `11aedfcfcd229df2` |
| `sat-fit-016` | fit | 40 | 217 | `168f864184b9233b` |
| `sat-fit-017` | fit | 41 | 224 | `5ee3c83a3491a8d0` |
| `sat-fit-018` | fit | 42 | 236 | `03255fd6d4d0acbc` |
| `sat-fit-019` | fit | 42 | 211 | `eb19f883a5efb753` |
| `sat-fit-020` | fit | 40 | 219 | `1896679aacefe68b` |
| `sat-fit-021` | fit | 42 | 224 | `0351d0f104f636bb` |
| `sat-fit-022` | fit | 44 | 223 | `4262d6ad882e525e` |
| `sat-fit-023` | fit | 40 | 228 | `97ae72ef5d60b6ed` |
| `sat-fit-024` | fit | 42 | 220 | `0ee1b07783f02351` |
| `sat-fit-025` | fit | 42 | 217 | `01e068dca9cd837a` |
| `sat-heldout-001` | heldout | 40 | 216 | `ef675c6bfbc316b4` |
| `sat-heldout-002` | heldout | 41 | 225 | `9df397009389d78b` |
| `sat-heldout-003` | heldout | 42 | 217 | `7cf545ac10030d94` |
| `sat-heldout-004` | heldout | 43 | 227 | `f7c041395a3f8277` |
| `sat-heldout-005` | heldout | 41 | 224 | `c7bbbcc90b5138c1` |
| `sat-heldout-006` | heldout | 43 | 215 | `be7e27bc0666ed3e` |
| `sat-heldout-007` | heldout | 42 | 213 | `1dffc00c4923c4fc` |
| `sat-heldout-008` | heldout | 40 | 225 | `88aea1071bd61156` |
| `sat-heldout-009` | heldout | 40 | 199 | `6fe6f58635603ace` |
| `sat-heldout-010` | heldout | 40 | 229 | `0be29443a13a7b66` |
| `sat-reserve-001` | reserve | 42 | 200 | `7d068ebc3c900beb` |
| `sat-reserve-002` | reserve | 42 | 211 | `12b504d127d1fce2` |
| `sat-reserve-003` | reserve | 42 | 228 | `97c95babbd41c8bb` |
| `sat-reserve-004` | reserve | 41 | 215 | `e68271bf92d89111` |
| `sat-reserve-005` | reserve | 43 | 220 | `75b7e1560bb305ea` |
| `sat-reserve-006` | reserve | 44 | 231 | `c9e260d33514cc42` |
| `sat-reserve-007` | reserve | 41 | 229 | `cd918a88b0f41c36` |
| `sat-reserve-008` | reserve | 42 | 238 | `5748b6e6e5d5905b` |
| `sat-reserve-009` | reserve | 42 | 231 | `bef53949d2f82858` |
| `sat-reserve-010` | reserve | 42 | 234 | `6dfd20853575ccbf` |
| `sat-reserve-011` | reserve | 42 | 228 | `2f1932b1de16ba3c` |
| `sat-reserve-012` | reserve | 38 | 217 | `77521854e829250d` |
| `sat-reserve-013` | reserve | 40 | 210 | `3927161cf676754e` |
| `sat-reserve-014` | reserve | 42 | 212 | `e686ff96b382f4e1` |
| `sat-reserve-015` | reserve | 42 | 225 | `f13eafc42f58f7e9` |

## Fit plan

Prompts are consumed in declared file order. No shuffling and no sampling.

| Unit | Prompts | IDs |
|---|---|---|
| `fit_a_direct` | 10 | `sat-fit-001` … `sat-fit-010` |
| `fit_b_shard_1` | 10 | `sat-fit-001` … `sat-fit-010` |
| `fit_b_shard_2` | 10 | `sat-fit-011` … `sat-fit-020` |
| `fit_b_shard_3` | 5 | `sat-fit-021` … `sat-fit-025` |
| `fit_b_merged` | 25 | merge of the three shards |
| `control_shard_1` | 3 | `sat-fit-021` … `sat-fit-023` |
| `control_shard_2` | 2 | `sat-fit-024`, `sat-fit-025` |
| `control_merged` | 5 | merge of the two control shards |
| `control_direct` | 5 | `fit_b_shard_3`, refitted directly in one call |
| `heldout_apply` | 10 | `sat-heldout-001` … `sat-heldout-010` |

Design notes:

- `fit_b_shard_1` intentionally repeats the `fit_a_direct` prompt set. The
  comparison is a free fit-repeatability control at zero extra design cost.
- The merge control is deliberately the smallest sound one: the five-prompt
  subset `fit_b_shard_3` is already fitted directly, so the control adds only
  two small shard fits and a merge. That is what "direct-subset control" means
  in `04_decision.json`.
- The 10 `role=heldout` prompts are disjoint from every fit set by
  construction, and the loader raises if that is ever violated.
- The 15 `role=reserve` prompts are unused by this run and exist so a later
  run can extend the fit set without touching a fitted or evaluated prompt.

Total prompt-fits: 10 + 10 + 10 + 5 + 3 + 2 = 40, plus 4 merges, plus 30
apply calls (3 lenses × 10 held-out prompts).

## Sample size and cost projection

Phase 0.5A measured 26.84 s per prompt at `dim_batch=2` and an implied fixed
overhead of about 41 s per fit call. A pessimistic `dim_batch=1` rate of
53.68 s per prompt is assumed for admission checks when `dim_batch=1`.

| Assumption | Estimated fitting seconds |
|---|---|
| Registered 26.84 s/prompt | ≈ 1 320 s |
| Pessimistic 53.68 s/prompt | ≈ 2 393 s |

Both are inside `PLANNING_BUDGET_SECONDS = 6120`. The application watchdog is
`APPLICATION_WATCHDOG_SECONDS = 6900` and the platform timeout is 7 200 s, so
the artifact pack is always exported before the platform kills the replica.

## Seeds and determinism

| Seed | Value |
|---|---|
| `python` | 0 |
| `numpy` | 0 |
| `torch` | 0 |

Determinism is structural rather than statistical: prompts are consumed in
declared file order, layers in ascending order, JSON is canonical with sorted
keys, CSV rows are emitted in generation order with a fixed header, all files
are UTF-8 with LF newlines, and the fit itself is a deterministic Jacobian
accumulation with no sampling and no generation.

## Stages

| Stage | Purpose | Predecessor |
|---|---|---|
| `S0_environment` | provenance, source pin, corpus registration | — |
| `S1_model` | model, tokenizer, adapter, guarded token lengths | `S0_environment` |
| `S2_fit_a10` | Fit A: 10 prompts, layers [6,13,20] → 27 | `S1_model` |
| `S3_fit_b25_sharded_merge` | Fit B: shards 10/10/5, merge, weighting cross-check, repeatability | `S2_fit_a10` |
| `S4_merge_control` | direct-subset control: merge([3,2]) vs direct 5 | `S3_fit_b25_sharded_merge` |
| `S5_convergence` | 10-vs-25 relative Frobenius, cosine, finite rate, save/load | `S3_fit_b25_sharded_merge` |
| `S6_apply_stability` | held-out apply, top-k overlap, rank correlation | `S3_fit_b25_sharded_merge` |

A stage whose predecessor did not succeed is recorded `blocked`. A stage that
fails records the error and the run still exports the pack. A stage that
cannot be admitted by `f3_segment_time_guard` is recorded
`skipped_time_guard`.

## Metrics

Primary metric: `convergence_relative_frobenius_10_vs_25` — the worst
layer-wise relative Frobenius difference between the 10-prompt lens and the
merged 25-prompt lens.

Secondary metrics: `convergence_cosine_10_vs_25`,
`shard_merge_vs_direct_max_abs`,
`shard_merge_vs_direct_relative_frobenius`,
`weighted_recombination_vs_direct_max_abs`, `fit_repeatability_max_abs`,
`matrix_finite_rate`, `matrix_norm`, `lens_save_load_max_abs`,
`apply_save_load_consistency`, `heldout_topk_overlap_mean`,
`heldout_rank_correlation_mean`, `heldout_logit_cosine_mean`,
`fit_wall_clock_seconds`, `fit_wall_clock_seconds_per_prompt`,
`gpu_peak_allocated_bytes`, `gpu_peak_reserved_bytes`, `checkpoint_bytes`,
`lens_bytes`.

Definitions:

- relative Frobenius: `‖A − B‖_F / max(‖B‖_F, 1e-12)`, reported per layer, with
  the maximum across layers used for the criterion.
- cosine: flattened `⟨A, B⟩ / (‖A‖·‖B‖)`, per layer, minimum across layers used
  for the criterion.
- top-k overlap: `|top_k(a) ∩ top_k(b)| / k` at `k = 10`, with `k = 50` also
  recorded. Ties break on ascending index so the statistic is deterministic.
- rank correlation: Spearman ρ with average ranks over the full logit vector.
- `matrix_finite_rate`: finite matrices ÷ total matrices across every fitted
  and merged lens.
- `apply_save_load_consistency`: 1.0 only if every held-out apply on the
  reloaded merged lens matches the in-memory merged lens within
  `rtol = atol = 5e-3`.

## Decision rules

Registered thresholds:

| Criterion | Family | Direction | Threshold |
|---|---|---|---|
| `matrix_finite_rate` | stability | ≥ | 1.0 |
| `lens_save_load_max_abs` | stability | ≤ | 0.0 |
| `shard_merge_vs_direct_max_abs` | stability | ≤ | 1e-5 |
| `shard_merge_vs_direct_relative_frobenius` | stability | ≤ | 1e-6 |
| `apply_save_load_consistency` | stability | ≥ | 1.0 |
| `convergence_relative_frobenius_10_vs_25` | convergence | ≤ | 0.10 |
| `convergence_cosine_10_vs_25` | convergence | ≥ | 0.99 |
| `heldout_topk_overlap_mean` | convergence | ≥ | 0.80 |
| `heldout_rank_correlation_mean` | convergence | ≥ | 0.95 |

The merge tolerances are inherited from the Phase 0.5A F5 control. The
convergence thresholds are new and deliberately conservative; they are a
registered *engineering* line for "more prompts stopped moving the lens", not
a scientific criterion.

Mapping to `04_decision.json`:

| Situation | `status` | `decision` |
|---|---|---|
| any stability criterion fails | `FAIL` | `ENGINEERING_UNSTABLE` |
| self-test backend, unfinished stage, or any not-applicable criterion | `INCONCLUSIVE` | `INCONCLUSIVE` |
| run blocked before a complete measurement | `BLOCKED` | `INCONCLUSIVE` |
| stability passes, a convergence criterion fails | `COMPLETE` | `ENGINEERING_IMPROVING` |
| all criteria pass | `PASS` | `ENGINEERING_STABLE` |

`ENGINEERING_IMPROVING` is an expected and acceptable outcome. It means the
pipeline is sound and 25 prompts are still not enough to stop the estimator
moving. It is not a failure and it is not evidence of anything semantic.

## Inclusion, exclusion, stopping, and retry rules

Inclusion:

- Only prompts registered in `data/jlens_saturation_prompts.jsonl` are used.
- Fit prompts are `role=fit` in declared file order; apply-stability prompts
  are `role=heldout` and are disjoint from every fit set.
- Every fit uses source layers `[6, 13, 20]` and target layer `27`.

Exclusion:

- No behavioral candidate-bank prompt, parser fixture, evaluator-set item, or
  answer label may enter any fit or apply set.
- `role=reserve` prompts are not used by this run.

Stopping:

- A stage that cannot finish inside the registered planning budget is recorded
  `skipped_time_guard` and the run exports what it measured.
- A stop-classified memory measurement blocks further fitting.
- The application watchdog fires before the platform timeout so the artifact
  pack is always exported.

Retry:

- Official checkpoint/resume only; one job re-execution may resume from the
  newest manifest-complete Blob snapshot.
- No parser, corpus, threshold, or interpretation may change on retry.

## Merge semantics caveat

`JacobianLens.merge(lenses)` takes only a list of lenses; its weighting
semantics are not part of the public signature. The runner therefore does not
assume them. It independently computes an `n_prompts`-weighted recombination
of the shard matrices and compares it with the official merge
(`weighted_recombination_vs_direct_max_abs`). A mismatch is recorded as a
deviation and an observation, never as a hard failure — the registered
stability criterion is the direct-subset control, which compares the official
merge against an official direct fit on the same prompts.

## Outputs

The runner writes exactly ten files into
`<output-dir>/phase05-jlens-saturation/track-a/<run_id>/`, with
`artifact_manifest.json` written last:

`00_stage_manifest.json`, `01_protocol_snapshot.json`, `02_records.jsonl`,
`03_metrics.csv`, `04_decision.json`, `05_summary.md`, `06_paper_table.csv`,
`07_figure_data.csv`, `08_deviations.json`, `artifact_manifest.json`.

Lens binaries and official checkpoints are written to the sibling directory
`<run_id>-work/` so the artifact pack itself stays exactly ten files. Files
with no applicable content are still generated, carrying
`status = not_applicable` and a `reason`.

## Reproduction

- Off-GPU verification: `python scripts/phase05_jlens_saturation.py --self-test`.
  The synthetic backend exercises every stage, the whole artifact pack, and
  the decision logic without `torch`, a GPU, or the model. Its numbers are
  synthetic and any run that uses it is forced to `INCONCLUSIVE`.
- Container execution: see `docs/phase05_jlens_saturation_run.md`.
- Tests: `python -m pytest tests/test_phase05_jlens_saturation.py -q`.

## Scientific claim boundary

Engineering feasibility only. This run measures whether the pinned official
Jacobian lens can be fit at 10 and 25 prompts, sharded, merged, serialized,
reloaded, and applied with stable numerics on one T4. Top-k overlap and rank
correlation are technical stability evidence about transport and
serialization. They are not semantic evidence and support no claim about a
workspace, hidden reasoning, an internal chain-of-thought, or J-space.
