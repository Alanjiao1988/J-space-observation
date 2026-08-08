# Study 2 — causal internal computation under a no-generated-trace interface

## Status

**Terminal state: `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`**

**Documentation state: `STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE`**

Study 2 protocol v1 is closed. The pre-registered, target-only Gate A feasibility
gate failed at the end of Stage B-D, before Stage B-C and before any mechanistic
stage. The original research question was **not answered**, and no evidence about
internal computation, causal mechanism, distillation, J-space or J-lens exists.

Formal methods-review allowance: `SPENT_VERIFIED`

Stage P froze the model-free protocol and public deterministic banks after the single
formal methods review. Stage T sealed the tokenizer and option-alignment gate: all
17,408 frozen prompt rows tokenize under all three registered checkpoints, all four
option continuations are single tokens, all 2,048 mechanistic pairs are jointly
eligible, and all eight selection cells filled to 128 for 1,024 selected pairs. The
three checkpoints produce *identical token IDs* on every prompt row.

Stage B-D then executed the complete 384-item development bank across all three
registered checkpoints, producing 3,072 behavioral rows in 18 shards with zero
retries, and applied Gate A:

| target family | NT correct | n | exact one-sided upper tail | family pass |
| --- | --- | --- | --- | --- |
| `permutation_chain` | 25 | 128 | 0.9403523926144965 | no |
| `affine_mod10` | 33 | 128 | 0.4526854444021635 | no |

Against the frozen threshold X >= 43 at alpha = 0.025, `overall_gate_pass = false`.
The frozen rule permits no rerun, repair, relabel, backfill, threshold change,
cross-family pooling, or control substitution within protocol v1. Stage B-C and every
mechanistic stage were therefore never opened; the confirmation bank was never read.

Study 2 contributed **zero** rows to `paper/evidence_ledger.csv`, which still ends at
`EV-0016`. Cumulatively Study 2 performed 3,072 forward passes, 3 weight loads, 3
tokenizer constructions and 3 model downloads; every other operation counter -
generations, activation operations, probes, patching, ablation, lens operations,
confirmation operations, provider calls, Phase 1.0D and RQ2/S4 operations - is zero.

The Gate A outcome is not an artifact of execution or bookkeeping integrity. It may
still be an artifact of interface or construct validity: protocol v1 never measured
interface adequacy or label binding, so **the data cannot distinguish an incapable
checkpoint from an inadequate interface**. See
[`decisions/study2_stage_bd_interpretation_erratum.md`](decisions/study2_stage_bd_interpretation_erratum.md).

## Research question (not answered)

Does the R1-distilled checkpoint compute and causally use a task-defined
intermediate variable during a single forward pass with zero generated
reasoning tokens, and is that behavior or mechanism stronger than in both its
lineage base checkpoint and a same-family instruction-tuned control?

The phrase “genuine reasoning” is not treated as a primitive label. The
strongest operational claim the design would ever have permitted, had every gate
passed, was:

> The target checkpoint uses a causally load-bearing intermediate variable to
> solve fresh compositional tasks under a controlled no-generated-trace
> interface.

That ceiling was never approached. Gate A failed at the development stage, so no
claim of any strength is supported in either direction.

## Why this is a new study

Study 1 required a raw full-vocabulary greedy next token to equal an
open-ended registered answer. That interface filtered nearly every official
item before lens validity or hidden computation could be tested. Study 2
removes that interface dependency from the primary estimand by reading four
prospectively fixed candidate logits at one answer position, with no generated
text and no semantic parser.

Study 2 is not S3 v1, a replacement batch, or a rerun. It uses new synthetic
tasks, new splits, new controls, new authority, and new terminal states.

## Design skeleton (as frozen; mechanistic parts never executed)

- Task families: `permutation_chain` and `affine_mod10`.
- Depths: 1 as direct control; 2 and 3 as compositional tasks.
- Surfaces: two balanced, semantically equivalent templates.
- Observable: restricted probabilities over four fixed option tokens from one
  forward pass; zero generated tokens.
- Primary mechanism: donor-to-recipient residual patching at the answer
  position. **Never executed.**
- Anti-copy test: patch success must favor the recombinant answer
  `g_recipient(m_donor)`, which is distinct from donor and recipient answers.
  **Never executed.**
- Controls: no-op, same-intermediate, same-answer/different-intermediate,
  random donor, wrong position, early band, motor band, option balance and
  cross-template probe. **Never executed.**
- Comparators: lineage base and same-family instruction checkpoint. Executed at
  the behavioral development stage only, as descriptive rows with zero authority
  over Gate A.
- J-lens: fixed M1200 was target-only and secondary. **Never loaded or applied.**

## Stage boundary

Stage P, Stage T and Stage B-D are complete, and **protocol v1 is closed**.

Stage T resolved tokenizer identity and alignment and sealed the mechanistic pair
selection; it created no scientific evidence and loaded no model weight.

Stage B-D then implemented the frozen behavioral computation, loaded the three
registered 1.5B checkpoints exactly, ran the complete 384-item development bank
under every applicable arm on an Azure T4 (3,072 rows, 18 shards, 0 retries), and
evaluated the pre-registered Gate A feasibility rule. Gate A returned
`overall_gate_pass = false`: on the target model's no-tool arm at depths 2+3, the
`permutation_chain` family scored 25/128 and `affine_mod10` scored 33/128 against
a threshold of 43, with chance at 32/128. The terminal state is
`STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`.

Gate A is a non-scientific feasibility gate. Its failure says nothing about
whether the target reasons internally, internalized a chain of thought, acquired
a causal mechanism through distillation, or about the validity of J-space. It
records only that the frozen interface did not clear the accuracy floor the
protocol required before spending confirmation and mechanistic budget. No
scientific evidence row was created and `paper/evidence_ledger.csv` still ends at
EV-0016.

Stage B-C, mechanistic-cell selection, M-D and M-C were never opened and may not
be opened under this protocol version. Re-running, backfilling, pooling away or
reinterpreting this protocol version is prohibited; any further attempt requires
a new protocol version, a new operator authority, and new task-bank seeds.

## Read next

1. [`terminal_manifest.json`](terminal_manifest.json) — machine-readable terminal record
2. [`STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md`](STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md) — terminal router
3. [`decisions/study2_stage_bd_gate_a_decision.md`](decisions/study2_stage_bd_gate_a_decision.md) — the frozen decision
4. [`decisions/study2_stage_bd_interpretation_erratum.md`](decisions/study2_stage_bd_interpretation_erratum.md) — interpretation control
5. [`analysis/stage_bd_posthoc_interface_diagnostic.md`](analysis/stage_bd_posthoc_interface_diagnostic.md) — descriptive, zero authority, not evidence
6. [`STAGE_BD_FINAL_HANDOFF.md`](STAGE_BD_FINAL_HANDOFF.md)
7. [`STAGE_BD_AUTHORITY_RECEIPT.md`](STAGE_BD_AUTHORITY_RECEIPT.md)
8. [`STAGE_T_FINAL_HANDOFF.md`](STAGE_T_FINAL_HANDOFF.md)
9. [`STAGE_T_AUTHORITY_RECEIPT.md`](STAGE_T_AUTHORITY_RECEIPT.md)
10. [`STAGE_P_FINAL_HANDOFF.md`](STAGE_P_FINAL_HANDOFF.md)
11. [`protocol/stage_p_operator_amendment_required.md`](protocol/stage_p_operator_amendment_required.md)
12. [`prompts/stage_p_protocol_design_prompt.md`](prompts/stage_p_protocol_design_prompt.md)

### Historical records, not current state

These describe the study at opening and deliberately retain their original
lifecycle wording. They are not current authority and were not edited at
terminalization.

- [`RESEARCH_CHARTER.md`](RESEARCH_CHARTER.md)
- [`study2_charter.json`](study2_charter.json)
- [`handoff_receipt.json`](handoff_receipt.json)
- [`NEXT_THREAD_HANDOFF.md`](NEXT_THREAD_HANDOFF.md) — superseded by the terminal handoff
