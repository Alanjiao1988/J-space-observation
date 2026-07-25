# Summary

- Phase: `phase05-jlens-saturation` / track `track-a`
- Run: `20260725T122016Z`
- Status: **COMPLETE**
- Decision: **ENGINEERING_IMPROVING**
- Mode: container

## Objective

Advance Phase 0.5 from a 2-prompt technical feasibility result to an executed 10-prompt fit, an executed 25-prompt sharded fit with merge, a direct-subset merge control, and measured convergence and apply stability.

Engineering hypothesis only: a 10-prompt and a sharded 25-prompt J-lens fit complete inside the T4 time and memory envelope, the merged sharded lens reproduces a direct fit on the same prompts within tolerance, and the fitted matrices and applied logits stay finite and numerically stable across save/load.

## Scope

In scope:
- 10-prompt direct fit
- 25-prompt sharded fit with official merge
- direct-subset merge control
- shard weighting cross-check
- 10-vs-25 matrix comparison
- held-out apply stability, top-k overlap, rank correlation
- wall-clock, memory, checkpoint and lens size measurement

Out of scope:
- any semantic or interpretability claim
- lens quality validation
- behavioral evaluation or parser work
- locked evaluator material
- Plan B
- hidden reasoning, internal workspace, or J-space claims

## Provenance

- Official source: `https://github.com/anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`
- Target model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B@ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` in float16
- Lens serialization dtype: `float32`
- Source layers: `[6, 13, 20]`; target layer: `27`
- max_seq_len: `32`; skip_first: `16`; dim_batch: `1`
- Fit corpus: `/workspace/data/jlens_saturation_prompts.jsonl` (file SHA-256 `41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b`, canonical SHA-256 `41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b`)
- Code commit: `408cd00540d5ded2b94ba75fc3616f8702e85465`; image digest: `sha256:a15016dfd025cb4e5dc166638129cc4abf7895cdddbbc1b7638672aab7a3524f`

## Execution

| Stage | Status | Duration (s) |
|---|---|---:|
| S0_environment | success | 0.33 |
| S1_model | success | 36.36 |
| S2_fit_a10 | success | 528.62 |
| S3_fit_b25_sharded_merge | success | 1317.65 |
| S4_merge_control | success | 263.92 |
| S5_convergence | success | 0.03 |
| S6_apply_stability | success | 28.73 |

## Results

| Metric | Value | Threshold | Passed |
|---|---:|---:|:--:|
| matrix_finite_rate | 1 | 1 | yes |
| lens_save_load_max_abs | 0 | 0 | yes |
| shard_merge_vs_direct_max_abs | 2.38419e-07 | 1e-05 | yes |
| shard_merge_vs_direct_relative_frobenius | 4.8615e-08 | 1e-06 | yes |
| apply_save_load_consistency | 1 | 1 | yes |
| convergence_relative_frobenius_10_vs_25 | 0.41701 | 0.1 | no |
| convergence_cosine_10_vs_25 | 0.920481 | 0.99 | no |
| heldout_topk_overlap_mean | 0.82 | 0.8 | yes |
| heldout_rank_correlation_mean | 0.969068 | 0.95 | yes |

Top-k overlap and rank correlation are technical stability statistics for two fitted linear operators. They are not semantic, behavioral, or interpretive evidence.

## Decision

- Status: **COMPLETE**
- Decision: **ENGINEERING_IMPROVING**
- Reason: Numerics, sharding, merge, serialization, and apply were stable, but the 10-to-25-prompt comparison has not yet reached the registered convergence thresholds (convergence_relative_frobenius_10_vs_25, convergence_cosine_10_vs_25). More fit prompts still change the lens. This is an engineering observation only.
- Next gate: Main-agent review of the executed saturation measurements before any larger fit is authorized. No behavioral or semantic gate is opened.

## Deviations and errors

- not_applicable

## Scientific interpretation

Engineering feasibility only. This run measures whether the pinned official Jacobian lens can be fit at 10 and 25 prompts, sharded, merged, serialized, reloaded, and applied with stable numerics on one T4. Top-k overlap and rank correlation are technical stability evidence about transport and serialization. They are not semantic evidence and support no claim about a workspace, hidden reasoning, an internal chain-of-thought, or J-space.

Prohibited interpretations of this artifact pack:
- workspace found
- J-space validated
- hidden reasoning observed
- internal workspace
- invisible chain-of-thought
- top-k overlap treated as semantic evidence

## Limitations

- One GPU, one model, one revision, one prompt corpus.
- Fit sets are nested (the 10-prompt set is a subset of the 25-prompt set), so the 10-vs-25 comparison measures estimator movement, not independent replication.
- Held-out apply stability uses 10 generic prompts at the final position only.
- No lens-quality, calibration, or semantic validation was attempted.

## Paper relevance

- Supplies the engineering feasibility row for J-lens scaling: measured wall-clock, memory, checkpoint and lens sizes at 10 and 25 prompts.
- Supplies the sharded-fit-plus-merge equivalence control.
- Supplies no behavioral, semantic, or workspace result.

## Next gate

Main-agent review of the executed saturation measurements before any larger fit is authorized. No behavioral or semantic gate is opened.
