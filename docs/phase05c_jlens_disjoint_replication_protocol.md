# Phase 0.5C: J-lens disjoint-replication protocol

## Status and boundary

Preregistered. Track A1, engineering numerics only.

Phase 0.5B fitted a 25-prompt Jacobian lens on `role=fit` prompts, proved the
sharded-fit/official-merge path reproduces a direct fit, and measured a nested
10-vs-25 convergence gap (`docs/phase05_jlens_saturation_protocol.md`,
`docs/phase05_jlens_saturation_run.md`). Phase 0.5C asks a different and
strictly *engineering* question: how far apart are two same-size lenses when
they are fitted on **disjoint** prompt samples, and what happens numerically
when the official merge combines them.

This protocol produces **no** scientific, semantic, or interpretive result.
The following statements are prohibited for every artifact this run emits:

- "workspace found"
- "J-space validated"
- "hidden reasoning observed"
- "internal workspace"
- "invisible chain-of-thought"
- "semantic convergence"
- treating top-k overlap or rank correlation as semantic evidence
- describing any lens produced here as scientifically usable

Top-k overlap and Spearman rank correlation appear only as **technical
stability statistics** comparing two fitted linear operators. They say nothing
about model cognition.

## Research question

How much do two independently fitted same-size (n = 25) Jacobian lenses,
fitted on disjoint prompt samples drawn from the same registered corpus,
differ numerically; and does the official weighted merge of the two behave
numerically like a well-formed lens on held-out apply?

Operationally this is a measurement of **independent-fit estimator
variability**: 0.5B measured how much a lens moves when the *same* prompt set
grows from 10 to 25 (nested); 0.5C measures how much two lenses disagree when
each sees a *different* 25-prompt sample of the same size (disjoint). The two
questions are not interchangeable and the 0.5B numbers are not evidence about
this one.

## Out of scope

This run does **not**, and no artifact it emits may be read to:

- establish or support any claim about hidden reasoning, an internal
  workspace, an invisible chain-of-thought, or J-space;
- establish or support any claim of semantic convergence, semantic agreement,
  or shared meaning between two lenses;
- establish that any lens produced by this run, by Phase 0.5B, or by any
  earlier phase is scientifically usable, validated, or interpretable;
- make any statement about model behavior, model capability, or model
  cognition;
- open any behavioral, evaluator, or Phase 1 gate.

Every number produced here is a property of fitted `float32` matrices and of
the transport code that writes and reads them.

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

Every value above is inherited unchanged from Phase 0.5A / 0.5B
(`src/jspace_observation/phase05_jlens.py`). No parser file, evaluator set,
locked artifact, or behavioral candidate is read, written, or referenced.

`dim_batch` may be raised to `2` only by passing `--dim-batch 2`. That path
records a deviation in `08_deviations.json` citing the Phase 0.5A F2
measurement (peak reserved 3 808 428 032 of 16 704 405 504 bytes, ratio
0.2280, classification green) and the completed F3 fit at `dim_batch=2`. Any
other value is rejected by the CLI.

## Reused Phase 0.5B lens (25A)

25A is **loaded, never re-fitted**. Its Azure location and digest were measured
by the main agent and are registered here before the run.

| Item | Value |
|---|---|
| Source run | `20260725T122016Z` (Phase 0.5B, track A) |
| Source unit | `fit_b_merged` |
| Storage account | `stjspacefiles0709085305` (RG `rg-jspace-observation-sea`) |
| Container | `jspace-results` |
| Blob name | `phase05-jlens-saturation/20260725T122016Z/attempts/primary/01-lens-binaries/fit_b_merged_lens.pt` |
| Lens SHA-256 | `cb17a634e46e4b219b6dc16b98662ba82e986abbcc154fd650e5a8a5b828949d` |
| Lens bytes | 28314032 |
| Prompt-order SHA-256 | `99e097f32b81cadca4964f710580bce73432b5378793872815fb87329e049df7` |
| Code commit | `408cd00540d5ded2b94ba75fc3616f8702e85465` |
| Image digest | `sha256:a15016dfd025cb4e5dc166638129cc4abf7895cdddbbc1b7638672aab7a3524f` |

The Blob prefix is `phase05-jlens-saturation/<run id>`. The spelling `05b`
occurs only in the local artifact directory
`artifacts/phase05b-jlens-saturation/track-a/20260725T122016Z/` and must never
be used to infer the Blob prefix. Of the thirteen objects under
`01-lens-binaries/`, only `fit_b_merged_lens.pt` is 25A; `28314032` bytes is
exactly the `lens_bytes` metric Phase 0.5B recorded for the merged 25-prompt
lens, which independently confirms the object identity.

### Registered read path

**The job replica reads the blob itself, with its own user-assigned managed
identity, over the private endpoint.** There is no staging hop through a
workstation, no account key, no SAS, and no public network path: the account
has public network access disabled. Concretely:

- the launcher passes `--existing-lens-blob <container-relative name>` and
  `--existing-lens-path /workspace/runtime/staged/fit_b_merged_lens.pt`;
- the launcher performs a read-only existence and content-length preflight with
  `--auth-mode login` and refuses to create the job if the object is absent or
  is not 28314032 bytes;
- inside the replica, stage S2 downloads the blob to the local path when the
  path is not already populated, authenticating with
  `DefaultAzureCredential(managed_identity_client_id=$AZURE_CLIENT_ID)`. The
  launcher sets `AZURE_CLIENT_ID` explicitly because the environment carries
  multiple user-assigned identities; a bare identity login would be ambiguous.
  The same mechanism is used for the artifact-pack uploads.

### Mandatory integrity gate

Before the file is deserialised, stage S2 recomputes both the SHA-256 and the
byte count of the local object and requires

```
sha256 == cb17a634e46e4b219b6dc16b98662ba82e986abbcc154fd650e5a8a5b828949d
bytes  == 28314032
```

If either disagrees the stage is recorded `failed`, every dependent stage is
recorded `blocked`, and the run stops. It does **not** continue silently and it
does **not** fall back to re-fitting 25A: re-fitting 25A is not an available
behaviour of this runner under any argument. The verified digest and byte count
are written into the S2 record, into `00_stage_manifest.json` provenance, and
the registered expectation is carried in `01_protocol_snapshot.json` under
`reused_lens_25a`, so the merged 50M lens is traceable to the exact 25A object.

After the structural checks the runner also verifies `n_prompts = 25`,
`source_layers = [6, 13, 20]` and `d_model = 1536`, and fails the stage if any
of those disagree.

### Emitted digests

Stage S5 saves and reloads all three lenses and records the SHA-256 and byte
count of each produced artifact — 25A as loaded, the merged 25B lens, and the
merged 50M lens — in `02_records.jsonl` and in the `produced_lens_digests`
provenance block of `00_stage_manifest.json`.

The runner independently recomputes the prompt-order SHA-256 of the 25
`role=fit` prompts from the amended corpus and refuses to start if it is not
the value above. That is what allows a lens fitted against corpus revision
`r1-50` to be attributed inside corpus revision `r2-60`.

## Fit corpus

`data/jlens_saturation_prompts.jsonl`, corpus revision `r2-60`.

| Property | Value |
|---|---|
| Records | 60 |
| File SHA-256 | `dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa` |
| Canonical JSONL SHA-256 | `dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa` |
| Bytes | 16 087 |
| Newlines | LF only, UTF-8, one JSON object per line |
| Fields | `id`, `role`, `text` only — no answers, no labels |
| Roles | `fit` 25, `heldout` 10, `reserve` 25 |
| Proxy token range | 38–44 |
| Proxy tokenizer | `regex_word_punctuation_proxy_v1` (`\w+|[^\w\s]`) |

The proxy tokenizer is used because the Hugging Face tokenizer is not
available off-container. It is a lower bound in practice: every prompt has at
least 33 proxy units, which guarantees the container-side
`guarded_token_length` truncation to `max_seq_len = 32` is deterministic and
identical for every prompt. The container additionally records the real
guarded tokenizer length for every corpus prompt in `02_records.jsonl`
(metric `corpus_token_count`).

### Corpus amendment (revision `r1-50` → `r2-60`)

Rationale. The frozen 50-record corpus is `fit` 25 + `reserve` 15 + `heldout`
10, not 50 fit prompts. All 25 `fit` prompts were consumed by 25A, so a
disjoint same-size sample did not exist. Ten new `reserve` prompts were
registered so that `role=reserve` becomes a 25-prompt block, provably disjoint
from the 25 `fit` prompts and from the 10 `heldout` prompts.

The amendment is **append-only**. The first 50 records are byte-for-byte
unchanged and remain in their original order; the 10 new records are appended
at the end of the file.

| Property | Revision `r1-50` | Revision `r2-60` |
|---|---|---|
| Records | 50 | 60 |
| Bytes | 13 452 | 16 087 |
| File SHA-256 | `41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b` | `dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa` |
| Roles | `fit` 25 / `heldout` 10 / `reserve` 15 | `fit` 25 / `heldout` 10 / `reserve` 25 |

Proof that the first 50 records are unchanged:

```
sha256(new_file_bytes[:13452]) == 41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b
```

`load_saturation_corpus` enforces this at load time for every superseding
revision (`CORPUS_REVISIONS` in
`src/jspace_observation/phase05_jlens_saturation.py`): if the prefix bytes
ever stop matching, the corpus is rejected. `S0_environment` re-verifies it
and records the result in `02_records.jsonl` under
`corpus::registration`.

The 10 new prompts were written under the identical registered generation
constraints as the original 50: neutral third-person descriptions of mundane,
non-reasoning processes; none asks for a scored answer; none has a right
answer; ASCII only; proxy token count in 38–44; at least 33 proxy units;
character count inside the existing 199–238 band; none contains any of the
forbidden cues `phase1`, `phase 1`, `evaluator`, `locked`, `reference answer`,
`answer-only` (the authoritative list is `FORBIDDEN_CORPUS_CUES` in
`src/jspace_observation/phase05_jlens_saturation.py`); zero exact-text and
normalised-text overlap with `data/phase1_task_headroom_candidates.jsonl`,
`data/jlens_feasibility_prompts.jsonl`, any parser fixture, and anything under
`evaluator_sets/`; and pairwise distinct from each other and from all 50
existing prompts.

`scripts/verify_jlens_corpus_amendment.py` re-checks every one of those
properties deterministically and prints a PASS/FAIL report.

Phase 0.5B's own preregistration and run record are historical documents and
are **not** rewritten. They continue to cite corpus revision `r1-50` and its
SHA-256, which is the corpus 0.5B actually ran against. The revision registry
records that `r2-60` supersedes `r1-50` by appending only.

### Per-prompt registration (10 new records)

| ID | Role | Proxy tokens | Characters | Text SHA-256 (first 16) |
|---|---|---:|---:|---|
| `sat-reserve-016` | reserve | 42 | 212 | `94fad9ec255c04d2` |
| `sat-reserve-017` | reserve | 43 | 208 | `c020c02fed485ce4` |
| `sat-reserve-018` | reserve | 41 | 219 | `2092e8b3484ae879` |
| `sat-reserve-019` | reserve | 43 | 210 | `90275f9ec421e22f` |
| `sat-reserve-020` | reserve | 40 | 210 | `32c868f8798fd96b` |
| `sat-reserve-021` | reserve | 42 | 207 | `e07b81aac64fad07` |
| `sat-reserve-022` | reserve | 43 | 206 | `8cd34234e4108861` |
| `sat-reserve-023` | reserve | 43 | 213 | `76d855e97ce6c5cb` |
| `sat-reserve-024` | reserve | 44 | 216 | `c80f31b0a1a80a60` |
| `sat-reserve-025` | reserve | 43 | 214 | `bd693dcfda5cc435` |

The registration table for the 50 pre-existing records is unchanged and lives
in `docs/phase05_jlens_saturation_protocol.md`.

## Fit plan

Prompts are consumed in declared file order. No shuffling and no sampling.

| Unit | Prompts | IDs | Action |
|---|---|---|---|
| `lens_25a` | 25 | `sat-fit-001` … `sat-fit-025` | **loaded** from the Phase 0.5B checkpoint, never re-fitted |
| `lens_25b_shard_1` | 10 | `sat-reserve-001` … `sat-reserve-010` | fitted |
| `lens_25b_shard_2` | 10 | `sat-reserve-011` … `sat-reserve-020` | fitted |
| `lens_25b_shard_3` | 5 | `sat-reserve-021` … `sat-reserve-025` | fitted |
| `lens_25b` | 25 | merge of the three shards | official merge |
| `lens_50m` | 50 | merge of `lens_25a` and `lens_25b` | official merge, weights 25/25 |
| `heldout_apply` | 10 | `sat-heldout-001` … `sat-heldout-010` | apply only |

Design notes:

- The 25B shard sizes 10/10/5 deliberately mirror the Phase 0.5B 25-prompt
  fit, so the fit cost and memory numbers are directly comparable.
- 25A ∩ 25B = ∅ by construction (`role=fit` vs `role=reserve`); the runner
  asserts the intersection is empty before fitting.
- The 10 `role=heldout` prompts are disjoint from both fit sets by
  construction, and the loader raises if that is ever violated.
- `lens_50m` is the official weighted merge of the two 25-prompt lenses, which
  carry equal `n_prompts`, so the merge weights are 25 and 25.

**No direct 50-prompt fit is performed.** It is deliberately omitted: Phase
0.5B already ran the direct-subset merge control and measured the official
merge to be numerically identical to a direct fit on the same prompts —
`shard_merge_vs_direct_max_abs = 2.384e-07` against a `1e-05` limit and
`shard_merge_vs_direct_relative_frobenius = 4.862e-08` against a `1e-06`
limit, with `weighted_recombination_vs_direct_max_abs = 0.0`. Repeating that
control at n = 50 would cost a second full 50-prompt fit and could not change
the conclusion. `04_decision.json` records
`direct_50_fit_performed = false` together with the reused 0.5B numbers.

Total prompt-fits: 10 + 10 + 5 = 25, plus 4 merges (3 shards → 25B, then 25A +
25B → 50M), plus 60 apply calls (3 in-memory lenses + 3 reloaded lenses × 10
held-out prompts).

## Sample size and cost projection

Phase 0.5B measured 52.674683 s per prompt at `dim_batch=1` for its 25-prompt
fit (1 316.87 s total). A pessimistic 53.68 s per prompt plus about 41 s fixed
overhead per fit call is assumed for admission checks when `dim_batch=1`.

| Assumption | Estimated fitting seconds |
|---|---|
| Phase 0.5B measured 52.67 s/prompt | ≈ 1 317 s |
| Pessimistic 53.68 s/prompt + overhead | ≈ 1 383 s |

Both are inside `PLANNING_BUDGET_SECONDS = 6120`. The application watchdog is
`APPLICATION_WATCHDOG_SECONDS = 6900` and the platform timeout is 7 200 s, so
the artifact pack is always exported before the platform kills the replica.
0.5C fits half as many prompts as 0.5B because 25A is loaded rather than
re-fitted.

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
| `S0_environment` | provenance, source pin, corpus registration, amendment prefix proof | — |
| `S1_model` | model, tokenizer, adapter, guarded token lengths | `S0_environment` |
| `S2_load_existing_25a` | load and verify the Phase 0.5B 25-prompt lens; no fit | `S1_model` |
| `S3_fit_25b_sharded_merge` | 25B: shards 10/10/5 on `role=reserve`, official merge | `S2_load_existing_25a` |
| `S4_merge_50` | 50M = official merge of 25A and 25B, weights 25/25 | `S3_fit_25b_sharded_merge` |
| `S5_serialization` | fp32 save/load round-trip for 25A, 25B and 50M | `S4_merge_50` |
| `S6_heldout_apply` | held-out apply for all three lenses, in-memory and reloaded | `S5_serialization` |
| `S7_replicate_variability` | pairwise matrix comparisons, finite rate, merged-improvement test | `S6_heldout_apply` |

A stage whose predecessor did not succeed is recorded `blocked`. A stage that
fails records the error and the run still exports the pack. A stage that
cannot be admitted by `f3_segment_time_guard` is recorded
`skipped_time_guard`.

## Metrics

Primary metric: `25A_vs_25B_relative_frobenius` — the worst layer-wise
relative Frobenius difference between the two independently fitted 25-prompt
lenses.

Registered metrics, exactly these thirteen:

| Metric | What it compares | Aggregation |
|---|---|---|
| `25A_vs_25B_relative_frobenius` | 25A vs 25B Jacobian matrices | per layer; **max** across layers is the criterion value |
| `25A_vs_25B_cosine` | 25A vs 25B Jacobian matrices | per layer; **min** across layers is the criterion value |
| `25A_vs_50M_relative_frobenius` | 25A vs 50M Jacobian matrices | per layer; max across layers |
| `25B_vs_50M_relative_frobenius` | 25B vs 50M Jacobian matrices | per layer; max across layers |
| `25A_vs_50M_cosine` | 25A vs 50M Jacobian matrices | per layer; min across layers |
| `25B_vs_50M_cosine` | 25B vs 50M Jacobian matrices | per layer; min across layers |
| `heldout_apply_logit_cosine` | applied logit vectors, per lens pair | mean over layers, then over prompts, then over pairs |
| `heldout_topk_overlap` | applied logit vectors, per lens pair | mean over layers, then over prompts, then over pairs |
| `heldout_rank_correlation` | applied logit vectors, per lens pair | mean over layers, then over prompts, then over pairs |
| `matrix_finite_rate` | every registered lens matrix | finite ÷ total |
| `save_load_max_abs` | fp32 save/load round-trip | max over lenses and layers |
| `wall_clock_per_prompt` | 25B fit cost | fit seconds ÷ 25 |
| `peak_gpu_memory` | 25B fit cost | max `gpu_peak_reserved_bytes` across the three shards |

Definitions — reused verbatim from Phase 0.5B wherever the statistic already
existed there:

- relative Frobenius: `‖A − B‖_F / max(‖B‖_F, 1e-12)`, reported per layer,
  with the maximum across layers used for the criterion. The right-hand lens
  is the reference: for `25A_vs_25B` the reference is 25B, for `25A_vs_50M`
  and `25B_vs_50M` the reference is 50M. Each `02_records.jsonl` comparison
  record carries an explicit `reference` field.
- cosine: flattened `⟨A, B⟩ / (‖A‖·‖B‖)`, per layer, minimum across layers
  used for the criterion.
- top-k overlap: `|top_k(a) ∩ top_k(b)| / k` at `k = 10`, with `k = 50` also
  recorded as `heldout_topk_overlap_secondary`. Ties break on ascending index
  so the statistic is deterministic.
- rank correlation: Spearman ρ with average ranks over the full logit vector.
- `matrix_finite_rate`: finite matrices ÷ total matrices across every lens
  registered by this run. The denominator is 6 lenses × 3 layers = 18: the
  loaded 25A, the three 25B shards, the merged 25B, and 50M.
- `save_load_max_abs`: the largest absolute elementwise difference between a
  lens matrix and the same matrix after an fp32 save and reload, maximised
  over the three lenses and the three layers. Phase 0.5B recorded this
  statistic as `lens_save_load_max_abs`; the definition is unchanged.
- `apply_save_load_consistency`: 1.0 only if every held-out apply on a
  reloaded lens matches the in-memory lens within `rtol = atol = 5e-3`, for
  all three lenses, all ten prompts and all three layers.
- `wall_clock_per_prompt`: 25B fit seconds summed over the three shards,
  divided by 25. Merge time is reported separately as `merge_seconds`.
- `peak_gpu_memory`: `torch.cuda.max_memory_reserved()` sampled per shard fit,
  maximised across the three shards.

The three held-out apply statistics are reported at four granularities:
per pair per prompt (`stratum = pair::<pair>::<prompt_id>`), per pair
(`stratum = pair::<pair>`), per lens (`stratum = lens::25A|25B|50M`, the mean
of the two pairs that contain that lens), and overall (`stratum = all`, the
mean of the three pairs). The overall value is the one the decision rules use.

Supporting observations, recorded for auditability and explicitly **not**
criteria: `apply_save_load_consistency` (a criterion in the transport family,
listed here for completeness of the record),
`merge_weighting_cross_check_max_abs`, `merged_apply_improvement_topk`,
`merged_apply_improvement_rank_correlation`, `heldout_topk_overlap_secondary`,
`matrix_norm`, `lens_bytes`, `checkpoint_bytes`, `merge_seconds`,
`fit_wall_clock_seconds`, `gpu_peak_allocated_bytes`,
`gpu_peak_reserved_bytes`, `corpus_proxy_token_count`, `corpus_token_count`.

## Decision rules

Registered thresholds:

| Criterion | Family | Direction | Threshold |
|---|---|---|---|
| `matrix_finite_rate` | transport | ≥ | 1.0 |
| `save_load_max_abs` | transport | ≤ | 0.0 |
| `apply_save_load_consistency` | transport | ≥ | 1.0 |
| `25A_vs_25B_relative_frobenius` | replication | ≤ | 0.10 |
| `25A_vs_25B_cosine` | replication | ≥ | 0.99 |

### Frozen definition of "merged-50 apply stability improves"

Let, for a held-out apply statistic `S`:

```
a = S[pair 25A_vs_25B]
b = S[pair 25A_vs_50M]
c = S[pair 25B_vs_50M]
improvement(S) = mean(b, c) - a
```

Merged-50 apply stability **improves** if and only if **both** hold
simultaneously:

```
improvement(heldout_topk_overlap)      >= 0.02
improvement(heldout_rank_correlation)  >= 0.005
```

Justification, frozen before the run:

- The quantity is exactly "the merged lens agrees with each single fit more
  than the two single fits agree with each other". That is the only sense in
  which a merge can be said to stabilise held-out apply without appealing to a
  ground truth, and no ground truth exists here.
- It uses the same statistics, the same `k = 10`, the same tie-break, and the
  same aggregation order as the registered held-out metrics, so no new
  definition is introduced.
- Margin for `heldout_topk_overlap`: with 10 held-out prompts × 3 source
  layers = 30 comparisons at `k = 10`, the arithmetic resolution of the mean
  is `1 / (30 × 10) = 0.00333`. A margin of 0.02 is six times that resolution,
  so a "pass" cannot be produced by a single element moving in or out of a
  top-10 set.
- Margin for `heldout_rank_correlation`: 0.005 is far above `float32` noise on
  a Spearman ρ over the full logit vector and matches the four-decimal
  precision at which Phase 0.5B reported ρ (0.9691).
- Both margins are **one-sided and strict-improvement**: a merge that leaves
  the statistics unchanged does not pass.

Mapping to `04_decision.json`:

| Situation | `status` | `decision` |
|---|---|---|
| any transport criterion fails (finite rate, fp32 save/load exactness, apply save/load consistency) | `FAIL` | `FAILED` |
| self-test backend, unfinished stage, or any not-applicable criterion | `INCONCLUSIVE` | `INCONCLUSIVE` |
| run blocked before a complete measurement | `BLOCKED` | `INCONCLUSIVE` |
| transport passes, both replicate criteria pass | `PASS` | `REPLICATE_STABLE` |
| transport passes, a replicate criterion fails, merged-50 improvement holds | `COMPLETE` | `REPLICATE_IMPROVING` |
| transport passes, a replicate criterion fails, merged-50 improvement does not hold | `COMPLETE` | `REPLICATE_UNSTABLE` |

Written out as the four registered outcomes:

- **`REPLICATE_STABLE`** — `25A_vs_25B_relative_frobenius <= 0.10` **and**
  `25A_vs_25B_cosine >= 0.99`.
- **`REPLICATE_IMPROVING`** — all numerical gates pass, the replicate
  stability thresholds fail, **and** merged-50 held-out apply stability
  improves by the frozen definition above.
- **`REPLICATE_UNSTABLE`** — all numerical gates pass, independent-fit
  disagreement stays large, and there is no merged improvement.
- **`FAILED`** — any fit, merge, save, load, or apply numerical gate fails.

All four outcomes are **engineering** decisions about numerics. None of them
licenses a scientific, semantic, or interpretive claim. In particular
`REPLICATE_STABLE` would mean only that two matrices are numerically close;
it would not mean that a lens is valid, meaningful, or usable, and
`REPLICATE_UNSTABLE` would mean only that they are not close.

## Inclusion, exclusion, stopping, and retry rules

Inclusion:

- Only prompts registered in `data/jlens_saturation_prompts.jsonl` corpus
  revision `r2-60` are used.
- 25A is `role=fit` in declared file order and is loaded from the Phase 0.5B
  checkpoint; it is never re-fitted.
- 25B is `role=reserve` in declared file order and is provably disjoint from
  25A.
- Held-out apply prompts are `role=heldout` and are disjoint from both fits.
- Every fit uses source layers `[6, 13, 20]` and target layer `27`.

Exclusion:

- No behavioral candidate-bank prompt, parser fixture, evaluator-set item, or
  answer label may enter any fit or apply set.
- No direct 50-prompt fit is performed; the Phase 0.5B direct-subset merge
  control already demonstrated merge/direct equivalence.
- The Phase 0.5B 25-prompt lens is not re-fitted under any circumstance.

Stopping:

- A stage that cannot finish inside the registered planning budget is recorded
  `skipped_time_guard` and the run exports what it measured.
- A stop-classified memory measurement blocks further fitting.
- The application watchdog fires before the platform timeout so the artifact
  pack is always exported.
- A stage whose predecessor did not succeed is recorded `blocked`.

Retry:

- Official checkpoint/resume only; one job re-execution may resume from the
  newest manifest-complete Blob snapshot.
- No corpus, threshold, metric definition, or interpretation may change on
  retry.
- A retry may not re-fit 25A and may not introduce a direct 50-prompt fit.

## Merge semantics caveat

`JacobianLens.merge(lenses)` takes only a list of lenses; its weighting
semantics are not part of the public signature. Phase 0.5B measured them
rather than assuming them, and found the official merge to be exactly the
`n_prompts`-weighted mean of the input matrices:
`weighted_recombination_vs_direct_max_abs = 0.0` (bit-exact), with the
direct-subset control agreeing to `2.384e-07`.

0.5C therefore obtains the "weights 25 and 25" merge by calling
`JacobianLens.merge([lens_25a, lens_25b])` where both inputs carry
`n_prompts = 25`. Because the two weights are equal, the merge reduces to the
unweighted mean, and `lens_50m.n_prompts` must be 50 — the runner fails the
stage if it is not.

`S4_merge_50` still recomputes an independent 25/25-weighted recombination of
the two matrix sets and compares it with the official merge
(`merge_weighting_cross_check_max_abs`). A mismatch above `1e-5` is recorded
as a deviation and an observation, never as a hard failure: this run's
registered transport criteria are the finite rate, the fp32 save/load
exactness, and the apply save/load consistency. The merge/direct equivalence
control itself is **not** repeated — it is cited from Phase 0.5B.

## Outputs

The runner writes exactly ten files into
`<output-dir>/phase05c-jlens-disjoint/track-a1/<run_id>/`, with
`artifact_manifest.json` written last:

`00_stage_manifest.json`, `01_protocol_snapshot.json`, `02_records.jsonl`,
`03_metrics.csv`, `04_decision.json`, `05_summary.md`, `06_paper_table.csv`,
`07_figure_data.csv`, `08_deviations.json`, `artifact_manifest.json`.

Lens binaries and official checkpoints are written to the sibling directory
`<run_id>-work/` so the artifact pack itself stays exactly ten files. Files
with no applicable content are still generated, carrying
`status = not_applicable` and a `reason`.

Blob prefix: `phase05c-jlens-disjoint/<UTC run ID>`, container
`jspace-results`, managed identity and private endpoint only.

## Protocol hash

The registered protocol hash is the SHA-256 of the canonical JSON encoding of
the protocol snapshot, which is exactly the bytes written to
`01_protocol_snapshot.json`. This is the same method Phase 0.5B used.

```
sha256(canonical_json_bytes(build_protocol_snapshot(sample_size=default_sample_size())))
= 49059665f6c0c720beb712f99941f6cbf3a7a0207bac3e94cc4ac73f5af11980
```

`tests/test_phase05c_jlens_disjoint.py` pins that value, so any change to the
registered question, metrics, thresholds, decision rules, sample sizes, or
claim boundary breaks the test rather than silently re-registering the
protocol.

## Reproduction

- Off-GPU verification:
  `python scripts/phase05c_jlens_disjoint.py --self-test`. The synthetic
  backend exercises every stage, the load-existing-lens path, the whole
  artifact pack, and the decision logic without `torch`, a GPU, or the model.
  Its numbers are synthetic and any run that uses it is forced to
  `INCONCLUSIVE`.
- Corpus amendment verification:
  `python scripts/verify_jlens_corpus_amendment.py`.
- Post-run analysis: `python scripts/analyze_phase05c_jlens_disjoint.py
  --pack-dir <executed pack>`.
- Container execution:
  `bash infra/azure/scripts/12_run_phase05c_jlens_disjoint.sh`.
- Tests: `python -m pytest tests/test_phase05c_jlens_disjoint.py -q`.

## Scientific claim boundary

Engineering numerics only. This run measures how far two independently fitted
same-size (n = 25) Jacobian lenses differ on disjoint prompt samples, and
whether the official weighted merge of the two behaves numerically like a
well-formed lens on held-out apply. Top-k overlap and rank correlation are
technical stability statistics for fitted linear operators. They are not
semantic evidence and support no claim about a workspace, hidden reasoning, an
internal chain-of-thought, J-space, semantic convergence, or any lens being
scientifically usable.
