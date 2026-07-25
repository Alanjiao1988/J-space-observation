# Summary

- Phase: `phase05c-jlens-disjoint` / track `track-a1`
- Run: `PENDING`
- Status: **BLOCKED**
- Decision: **INCONCLUSIVE**
- Mode: pre_run_scaffold

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
- Fit corpus: `data/jlens_saturation_prompts.jsonl` (file SHA-256 `dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa`, canonical SHA-256 ``)
- Code commit: `PENDING`; image digest: `None`
- Corpus revision: `r2-60`
- Existing 25A lens: `jspace-results/phase05-jlens-saturation/20260725T122016Z/attempts/primary/01-lens-binaries/fit_b_merged_lens.pt` from run `20260725T122016Z`; re-fitted: no
- Direct 50-prompt fit: not performed; the Phase 0.5B direct-subset merge control is reused
- pre-run scaffold: the Phase 0.5C container job has not executed, so no measured value exists yet

## Execution

| Stage | Status | Duration (s) |
|---|---|---:|
| S0_environment | not_run |  |
| S1_model | not_run |  |
| S2_load_existing_25a | not_run |  |
| S3_fit_25b_sharded_merge | not_run |  |
| S4_merge_50 | not_run |  |
| S5_serialization | not_run |  |
| S6_heldout_apply | not_run |  |
| S7_replicate_variability | not_run |  |

## Results

| Metric | Value | Threshold | Passed |
|---|---:|---:|:--:|
| matrix_finite_rate | not_applicable | 1 | n/a |
| save_load_max_abs | not_applicable | 0 | n/a |
| apply_save_load_consistency | not_applicable | 1 | n/a |
| 25A_vs_25B_relative_frobenius | not_applicable | 0.1 | n/a |
| 25A_vs_25B_cosine | not_applicable | 0.99 | n/a |

pre-run scaffold: the Phase 0.5C container job has not executed, so no measured value exists yet

## Decision

- Status: **BLOCKED**
- Decision: **INCONCLUSIVE**
- Reason: The run was blocked before a complete measurement: pre-run scaffold: the Phase 0.5C container job has not executed, so no measured value exists yet. No engineering conclusion about independent-fit variability is available.
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
