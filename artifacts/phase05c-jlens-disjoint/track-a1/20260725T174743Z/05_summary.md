# Summary

- Phase: `phase05c-jlens-disjoint` / track `track-a1`
- Run: `20260725T174743Z`
- Status: **COMPLETE**
- Decision: **REPLICATE_IMPROVING**
- Mode: container

## Objective

Measure independent-fit estimator variability: fit a 25-prompt J-lens on a prompt set disjoint from the executed Phase 0.5B 25-prompt fit, merge the two with the official weighted merge into a 50-prompt lens, and record the numerical difference between all three operators on held-out apply.

Engineering hypothesis only: a second 25-prompt sharded fit completes inside the T4 time and memory envelope, the official weighted merge of the two 25-prompt lenses is a well-formed 50-prompt lens, every matrix stays finite, fp32 serialization stays exact, and the disagreement between the two independent fits is measurable.

## Scope

In scope:
- load-and-verify the already-fitted Phase 0.5B 25-prompt lens (25A)
- 25-prompt sharded fit on the disjoint reserve block (25B) with official merge
- official weighted merge of 25A and 25B into a 50-prompt lens (50M)
- matrix-level 25A/25B/50M comparison: relative Frobenius and cosine
- held-out apply comparison for all three lens pairs
- fp32 save/load exactness and apply save/load consistency
- wall-clock per prompt and peak GPU memory measurement

Out of scope:
- any semantic, interpretive, or scientific validity claim
- any claim that a lens produced here is scientifically usable
- hidden reasoning, internal workspace, invisible chain-of-thought, J-space, or semantic convergence claims
- lens quality, calibration, or behavioral evaluation
- re-fitting the Phase 0.5B 25-prompt lens
- a direct 50-prompt fit; the Phase 0.5B direct-subset merge control already demonstrated merge/direct numerical equivalence
- parser, evaluator-set, or locked-artifact material

## Provenance

- Official source: `https://github.com/anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`
- Target model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B@ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` in float16
- Lens serialization dtype: `float32`
- Source layers: `[6, 13, 20]`; target layer: `27`
- max_seq_len: `32`; skip_first: `16`; dim_batch: `1`
- Fit corpus: `/workspace/data/jlens_saturation_prompts.jsonl` (file SHA-256 `dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa`, canonical SHA-256 `dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa`)
- Code commit: `39dc6e09d0ccc2431bd3c695666033b0eeeb302d`; image digest: `sha256:1fdf406fa34d76f228bd8a3570e9564c0a63baadda8e5b3e58f9c0e1b9ad3a37`
- Corpus revision: `r2-60` ({'fit': 25, 'heldout': 10, 'reserve': 25})
- Existing 25A lens: `/workspace/runtime/staged/fit_b_merged_lens.pt` from run `20260725T122016Z`; re-fitted: no
- Direct 50-prompt fit: not performed; the Phase 0.5B direct-subset merge control is reused

## Execution

| Stage | Status | Duration (s) |
|---|---|---:|
| S0_environment | success | 0.30 |
| S1_model | success | 36.72 |
| S2_load_existing_25a | success | 3.74 |
| S3_fit_25b_sharded_merge | success | 1289.91 |
| S4_merge_50 | success | 0.06 |
| S5_serialization | success | 0.38 |
| S6_heldout_apply | success | 85.88 |
| S7_replicate_variability | success | 0.07 |

## Results

| Metric | Value | Threshold | Passed |
|---|---:|---:|:--:|
| matrix_finite_rate | 1 | 1 | yes |
| save_load_max_abs | 0 | 0 | yes |
| apply_save_load_consistency | 1 | 1 | yes |
| 25A_vs_25B_relative_frobenius | 0.483067 | 0.1 | no |
| 25A_vs_25B_cosine | 0.878119 | 0.99 | no |

Top-k overlap and rank correlation are technical stability statistics for fitted linear operators. They are not semantic, behavioral, or interpretive evidence, and they do not indicate that any lens is scientifically usable.

## Decision

- Status: **COMPLETE**
- Decision: **REPLICATE_IMPROVING**
- Reason: The numerical transport gates passed, the two independent 25-prompt fits did not meet the registered replicate thresholds (25A_vs_25B_relative_frobenius, 25A_vs_25B_cosine), and the merged 50-prompt lens met the preregistered held-out apply improvement margin against both single fits. This is an engineering numerics observation only and licenses no scientific claim.
- Next gate: Main-agent review of the executed independent-fit variability numbers. No behavioral, semantic, or scientific gate is opened by any outcome of this run.

## Deviations and errors

- not_applicable

## Scientific interpretation

Engineering numerics only. This run measures how far two independently fitted same-size (n=25) Jacobian lenses differ on disjoint prompt samples, and whether the official weighted merge of the two behaves numerically like a well-formed lens on held-out apply. Top-k overlap and rank correlation are technical stability statistics for fitted linear operators. They are not semantic evidence and support no claim about a workspace, hidden reasoning, an internal chain-of-thought, J-space, semantic convergence, or any lens being scientifically usable.

Prohibited interpretations of this artifact pack:
- workspace found
- J-space validated
- hidden reasoning observed
- internal workspace
- invisible chain-of-thought
- top-k overlap treated as semantic evidence
- any lens produced here described as scientifically usable

## Limitations

- One GPU, one model, one revision, one prompt corpus, one pair of fits.
- The two fits are disjoint prompt samples of size 25 from the same corpus; two samples give one difference measurement, not a distribution.
- 25A was fitted in a previous run and is loaded from its fp32 checkpoint; this run re-verifies its metadata and digest but does not re-fit it.
- No direct 50-prompt fit is performed, so the merged lens is compared against its own inputs and against the Phase 0.5B merge control only.
- Held-out apply uses 10 generic prompts at the final position only.
- No lens-quality, calibration, or semantic validation was attempted and none of these numbers supports any scientific claim.

## Paper relevance

- Supplies the independent-fit estimator variability row: how far two same-size J-lenses fitted on disjoint prompt samples differ numerically.
- Supplies the engineering cost row for a second 25-prompt fit: wall-clock per prompt, peak GPU memory, checkpoint and lens sizes.
- Supplies no behavioral, semantic, or workspace result of any kind.

## Next gate

Main-agent review of the executed independent-fit variability numbers. No behavioral, semantic, or scientific gate is opened by any outcome of this run.
