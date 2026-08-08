# Study 2 protocol v1 terminal handoff

**Primary terminal state: `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`**

**Documentation state: `STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE`**

Study 2 protocol v1 is closed. It did not answer its research question. This document
is the read-only router for anyone arriving at Study 2 for the first time or
returning to it later.

Read `studies/study2/terminal_manifest.json` alongside this document. Where a machine
value is needed, the manifest is authoritative.

## 1. What Study 2 asked, and what it actually measured

**Original research question.** Does the R1-distilled checkpoint compute and causally
use a task-defined intermediate variable during a single forward pass with zero
generated reasoning tokens, and is that behavior or mechanism stronger than in both
its lineage base checkpoint and a same-family instruction-tuned control?

**This question was not answered.** No evidence bearing on it exists.

**What was actually measured** is much narrower: whether the complete, integrity-valid,
frozen four-option / no-generated-trace interface cleared its pre-registered,
target-only development feasibility gate on the frozen 384-item development bank under
the three registered 1.5B checkpoints.

It did not. That is the entire empirical content of Study 2 protocol v1.

Answering the narrow question in the negative closes the protocol. It produces no
evidence about internal computation, causal mechanism, distillation, J-space, J-lens,
or hidden reasoning.

## 2. Stage lifecycle

| stage | state | opened |
| --- | --- | --- |
| Stage P - prospective design and freeze | complete, frozen | yes |
| Stage T - tokenizer and option-alignment gate | complete, sealed | yes |
| Stage B-D - development execution and Gate A | complete, **Gate A failed** | yes |
| Stage B-C - behavioral confirmation | **never opened**, unavailable under v1 | no |
| Mechanistic cell selection | **never opened**, unavailable under v1 | no |
| Stage M-D - mechanistic development | **never opened**, unavailable under v1 | no |
| Stage M-C - mechanistic confirmation | **never opened**, unavailable under v1 | no |

The confirmation bank was never read, tokenized, or forwarded, and all six registered
confirmation paths were physically absent from the execution image. No activation was
extracted, no probe was fit, no patching, ablation, or lens operation ever ran.

## 3. The decision that closed the study

Gate A is a pre-registered, non-scientific **feasibility** gate. It was frozen before
measurement and did not move afterward.

Design: target model only, NT arm only, depths 2 and 3, 64 rows per depth, n = 128 per
family, null accuracy 0.25, alpha = 0.025, exact one-sided binomial upper tail,
threshold X >= 43. Gate A passes only if **both** target families pass.

| family | target NT correct | n | exact upper tail | family pass |
| --- | --- | --- | --- | --- |
| `permutation_chain` | 25 | 128 | 0.9403523926144965 | no |
| `affine_mod10` | 33 | 128 | 0.4526854444021635 | no |

`overall_gate_pass = false`.
`gate_inputs_sha256 = 1433f8119b2d8e377be7ede2735430ab55006c3737ebd2bf9e0c85c486b93cf7`.

The outcome is not marginal. Reaching the threshold would have required 18 more
correct rows in `permutation_chain` and 10 more in `affine_mod10`. Chance is 32.

**Controls carry zero authority.** The full six-cell family table is retained in the
manifest because the protocol requires it. One control cell - `lineage_base` /
`affine_mod10`, 44/128, upper tail 0.011190410208704914 - does clear the family
threshold. It is **not a finding and must not be reported as one**: the frozen rule
derives `overall_gate_pass` exclusively from the two target families, and one cell at
p = 0.011 out of six computed cells is exactly the multiplicity artifact that
pre-registration exists to prevent. Substituting a control for the target is not a
permitted operation.

## 4. How to interpret the outcome, and how not to

The Gate A decision document and the Stage B-D final handoff say the result "is not a
measurement artifact". That wording is too broad and is narrowed by
`studies/study2/decisions/study2_stage_bd_interpretation_erratum.md`. Both frozen
documents keep their exact bytes; only the interpretation is controlled.

The corrected statement:

> The outcome is not an artifact of **execution or bookkeeping integrity**. The row
> space is complete and correct, prompt and token identities match the Stage T seal,
> option token IDs are identical across checkpoints, decision inputs were registered
> before measurement, and the frozen rule did not move. It remains entirely possible
> that the outcome is an artifact of **interface or construct validity**. Protocol v1
> did not measure interface adequacy or label binding, so **the data cannot
> distinguish an incapable checkpoint from an inadequate interface**. No claim in
> either direction is supported.

Do not write "the result is not a measurement artifact" about Study 2 without that
qualification.

Specifically, Study 2 does **not** support, and does not contradict:

- that the distilled checkpoint does or does not internally compute the intermediate
  variable;
- that distillation does or does not change internal computation;
- anything about J-space or J-lens validity;
- anything about hidden or internalized reasoning.

Each of these is unmeasured, not negative.

## 5. Post-hoc diagnostic - descriptive only

`studies/study2/analysis/stage_bd_posthoc_interface_diagnostic.md` re-aggregates the
already-committed target development rows. It is labeled
`POST_HOC_DESCRIPTIVE_ZERO_AUTHORITY_NOT_SCIENTIFIC_EVIDENCE`, it was not
pre-registered, it is not a test, and it is not an evidence row.

It records that option C is selected in **zero of 384** target NT rows, that the modal
option shifts from A in the no-trace arm to B in all three trace-conditioned arms, and
that every arm's accuracy stays near the 0.25 restricted-choice chance level
(NT 0.2396, PT 0.2617, ST 0.2656, WT 0.2734).

That pattern is *consistent with* an interface or label-binding concern. It is also
consistent with several other explanations, and **the cause is not identified**.
Protocol v1 contains no manipulation that could isolate it. The diagnostic is
recorded as a limitation (L-89), never as a result.

## 6. What is permanently closed

Under protocol v1 the following are not permitted: rerunning, repairing, relabeling,
backfilling, or rescoring any v1 artifact; changing a threshold; pooling across
families; substituting a control; reinterpreting the failed gate as a positive or
negative scientific result; opening Stage B-C; opening mechanistic selection or any
mechanistic stage; promoting a control cell or the post-hoc diagnostic to a finding.

## 7. What is not authorized

This terminalization is documentation and interpretation control only. It grants **no
execution authority** and creates no scientific evidence.

Not authorized by this document or by anything in this round: protocol v2 design,
interface calibration or redesign, a label-binding or interface-adequacy study, new
task banks, new thresholds, Stage B-C, mechanistic work of any kind, any model
download, weight load, tokenizer construction, forward pass, generation, activation
extraction, probe, patch, ablation, or lens operation, any GPU job, any provider call,
any Phase 1.0D or RQ2/S4 operation, and any new evidence row.

Any later attempt at the original research question requires a separately authorized
**new protocol version**, with its own operator authority and its own task-bank seeds.

## 8. Repository identity

| item | value |
| --- | --- |
| measurement-terminal commit | `43411e09de425dfae0ee74ba46c68a389311e9a7` |
| measurement-terminal tree | `c393f395fd499716f5caae6515045483745975bb` |
| closed at (UTC) | `2026-08-08T08:01:45Z` |
| development rows | 3,072 (3 models x 1,024), 18 shards, 0 retries |
| forward passes / weight loads / tokenizer constructions / model downloads | 3072 / 3 / 3 / 3 |
| every other operation counter | 0 |
| `paper/evidence_ledger.csv` | ends at `EV-0016`; Study 2 contributed 0 evidence rows |
| Phase 1.0D rollup | `436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd` (152 files) |
| Phase 1.0D review v2 rollup | `ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a` (36 files) |

The documentation commit containing this file is deliberately not embedded here; a
file cannot carry the SHA of the commit that contains it. The publishing operator
reports it separately.

Local branch names, session names, and worktree paths are observational metadata
only. Commit, tree, and blob identity are authoritative.

## 9. Read next

1. `studies/study2/terminal_manifest.json` - machine-readable terminal record
2. `studies/study2/decisions/study2_stage_bd_gate_a_decision.md` - the frozen decision
3. `studies/study2/decisions/study2_stage_bd_interpretation_erratum.md` - interpretation control
4. `studies/study2/analysis/stage_bd_posthoc_interface_diagnostic.md` - descriptive, zero authority
5. `studies/study2/STAGE_BD_FINAL_HANDOFF.md` - full execution record
6. `paper/limitations_ledger.md` - L-85 through L-89

Historical records, not current state: `studies/study2/RESEARCH_CHARTER.md`,
`studies/study2/study2_charter.json`, and `studies/study2/handoff_receipt.json`
describe the study at opening and retain their original lifecycle wording by design.
`studies/study2/NEXT_THREAD_HANDOFF.md` is superseded by this document.
