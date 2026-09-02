# Claim and evidence audit for `REPORT.md`

This audit applies to the evidence-based report added after the experimental program closed. It does not alter the historical `evidence_ledger.csv`, whose frozen Study 1 scope ends at `EV-0016`.

## 1. Claim matrix

| Claim ID | Report claim | Supporting experiment | Primary data / file | Independent report check | Confidence | Claim ceiling |
|---|---|---|---|---|---|---|
| RC-01 | no study reached a valid mechanistic test of the original target hypothesis | Studies 1–5 | [project discontinuation](../PROJECT_DISCONTINUATION.md), [study index](../studies/README.md) | terminal states compared with operation counters and unopened-stage receipts | High | archive lifecycle fact only |
| RC-02 | Study 1 E0 produced 9 development-eligible and 0 confirmation rows from 238 items | S1-S3-E0 | [terminal manifest](../studies/study1/terminal_manifest.json) | `analysis/reproduce_report.py` checks counts and zero lens operations | High | raw-interface eligibility only |
| RC-03 | Study 2 target Gate A failed at 25/128 and 33/128 with exact tails 0.940352 and 0.452685 | S2-BD | [summary rows](../studies/study2/stage_bd/stage_bd_development_summaries.jsonl), [decision](../studies/study2/stage_bd/stage_bd_gate_a_decision.json) | counts and binomial tails recomputed from rows | High | feasibility rule only; construct validity unresolved |
| RC-04 | Study 3 v0.7 and Study 3R were rejected before scientific execution | S3-v0.7, S3R-v1 | [Study 3 decision](../studies/study3/reviews/v0_7_operator_terminal_decision.md), [Study 3R closure](../studies/study3r/STUDY3R_TERMINAL_CLOSURE.md) | operation/state records and review totals cross-checked | High | protocol-review result only |
| RC-05 | paired 7B/14B CoT cells scored 93.3%–100%, while all 240 raw-direct continuations were unparseable | S4F-M1 | [cell results](../studies/study4f/execution-m1/cell_results.json) | rates, totals, and Wilson intervals recomputed | High for stored cells | developmental interface observation; no target or mechanism claim |
| RC-06 | two objects showed bfloat16 mean batch-width shifts of 0.623730 and 0.110938 logits; repaired registered no-op means were zero | S5-P0-prime, S5-P0c-2 | [P-0-prime bf16](../studies/study5/validation-p0-prime/out/baseline_bf16.json), [P-0-prime fp32](../studies/study5/validation-p0-prime/out/baseline_fp32.json), [P-0c-2 bf16](../studies/study5/validation-p0c2/out/baseline_bf16.json), [P-0c-2 fp32](../studies/study5/validation-p0c2/out/baseline_fp32.json) | ratios and zero fields recomputed; verifier source inspected | High for recorded implementation | two objects and one narrow stack; no universal magnitude claim |
| RC-07 | P-0c-2 established its constructed object at 0.840625 clean and 0.10625 ablated accuracy | S5-P0c-2 | [object proof](../studies/study5/validation-p0c2/out/object_proof.json) | thresholds, difference, and item count recomputed | High for registered criteria | selection-set engineering asset only |
| RC-08 | the four-candidate estimand shortlist was exhausted before a real target measurement | S5-P0c-2 | [OD-022 sweep](../studies/study5/validation-p0c2/out/od022_sweep.json), [C1 non-vacuity](../studies/study5/validation-p0c2/measurement/out/c1_nonvacuity.json), [closure](../studies/study5/closure/STUDY5_CLOSURE.md) | case maxima and pass flags read from committed JSON | Medium-high | closed list of four only |

## 2. Fact, interpretation, and hypothesis separation

### Observed results

- Exact committed counts, rates, hashes, gate states, and zero-operation counters.
- First-token regularities in Study 4F-M1 and exact no-op deviations in Study 5.
- Protocol-review finding counts and terminal rejection states.

### Evidence-supported interpretations

- Output interface was a binding qualification variable in Study 4F-M1.
- Batch-consistent baseline/cache/chunk shapes were necessary for exact no-ops in the recorded implementation.
- The original hypothesis was not reached by the experiment chain.

### Unverified hypotheses

- Study 4F-M1 raw-direct failure was caused by a learned chat or reasoning-format prior.
- Different batch shapes selected different low-level reduction orders or kernels and thereby caused the measured offset.
- A per-patch matched control would yield a valid destruction-adjusted estimand.
- The constructed letter is represented as, or causally used as, an internal intermediate.

The report labels these as alternative explanations or future work and does not present them as findings.

## 3. Causality audit

| Tempting causal statement | Evidence actually available | Report treatment |
|---|---|---|
| distillation transferred or failed to transfer a reasoning mechanism | public end-state checkpoint observations only; no matched training intervention | explicitly excluded |
| raw-direct prompting caused loss of reasoning | bundled route comparison with different prompt, decoding, token budget, and parser | described as association / qualification discrepancy |
| bfloat16 caused the entire baseline error | two dtype records with different or limited unit counts; repair bundle not component-ablated | described as a precision- and batch-shape-associated apparatus observation |
| J-lens is invalid | one route without a passing positive control at tested scale | explicitly excluded |
| the model uses the constructed letter internally | clean and ablated task performance only; no valid real patch measurement | explicitly excluded |

## 4. Claims intentionally not made

1. **“J-space exists” or “J-space does not exist.”** No target mechanistic confirmation ran.
2. **“The target has no hidden reasoning.”** Behavioral/interface gate failures cannot identify internal capability.
3. **“Distillation did not transfer reasoning.”** No controlled training comparison exists.
4. **“The raw-direct interface is invalid.”** Study 4F-M1 shows failure under its exact contract, not validity under an external criterion.
5. **“CoT accuracy proves genuine reasoning.”** The archive measures exact task correctness, not faithfulness or mechanism.
6. **“bfloat16 activation patching is generally uninterpretable.”** The observed magnitude is limited to two objects and a narrow stack; the report instead requires same-shape no-op validation for effects at this scale.
7. **“C1 showed significant non-monotonicity.”** The registered monotonicity condition was not established; the opposite was not tested as a confirmatory claim.
8. **“A class of estimands was refuted.”** Only a closed list of four candidates was exhausted.
9. **“Hop 2 never fails” or “hop-1 accuracy decays with position.”** These are post-hoc patterns and not registered findings.
10. **“The J-lens late layers are architecturally identical to the logit lens.”** The observed near-identity/readout behavior is descriptive and control-specific.
11. **“The report establishes novelty.”** The literature review is targeted, not systematic.

## 5. Overclaiming vocabulary audit

The following rules were applied to `REPORT.md`:

- **prove / proven:** used only for named historical artifact labels such as `object_proof.json` or to describe exact no-op integrity already encoded by the source; not used for the scientific hypothesis.
- **demonstrate:** avoided for target mechanism claims; low-level causes remain interpretations.
- **confirm / confirmed:** restricted to engineering or lifecycle facts with committed evidence.
- **significant:** used only when denying an unsupported significance claim or quoting a preregistered future wording; no new significance result is asserted.
- **always / never:** `never` is used only for operation/lifecycle facts established by counters and terminal records, such as the target checkpoint never being run.
- **causal:** retained in the original research question, method names, and explicitly rejected causal inferences; no correlation is rewritten as causation.
- **general / generalize:** accompanied by an explicit limitation or excluded claim.

## 6. Reviewer verdict

The archive supports publication as a small empirical methods or reproducibility report if the contribution is framed as measurement-gate behavior and intervention-integrity failure. It does not support a paper claiming a discovery about J-space, hidden reasoning, or causal distillation. The strongest additional evidence needed for a mechanism paper is a qualified positive reference, a factorially validated interface, a numerically exact intervention apparatus with independent replication, and matched controlled training if the word “distillation” is to carry causal meaning.
