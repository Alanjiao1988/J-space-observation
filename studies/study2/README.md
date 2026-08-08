# Study 2 — causal internal computation under a no-generated-trace interface

## Status

Coordination state:
`NONTERMINAL_CHECKPOINT_STUDY2_STAGE_T_TOKENIZER_GATE_SEALED_AWAITING_BD_AUTHORITY`

Canonical protocol lifecycle: `STAGE_T_SEALED_AWAITING_BD_AUTHORITY`

Formal methods-review allowance: `SPENT_VERIFIED`

The model-free protocol and public deterministic banks are frozen after the
single formal methods review and final ACR validation. Focused run `cmcc`
passed 41 tests, full run `cmcd` returned 3,537 passed / 15 skipped / only the
two disclosed historical parser-seal failures, and validator `cmce` passed the
complete frozen package and protected-byte checks. An operator-directed
pre-review check identified
a material feasibility-gate question. The operator selected Gate A and authorized
the additive amendment at
[`prompts/stage_p_gate_a_operator_amendment.md`](prompts/stage_p_gate_a_operator_amendment.md).
The retained gap analysis is
[`protocol/stage_p_operator_amendment_required.md`](protocol/stage_p_operator_amendment_required.md).
The freeze decision is
[`decisions/reasoning_internalization_protocol_freeze.md`](decisions/reasoning_internalization_protocol_freeze.md).

Stage T is complete. The tokenizer gate passed cleanly: all 17,408 frozen
prompt rows tokenize under all three registered checkpoints, all four option
continuations are single tokens, all 2,048 mechanistic pairs are jointly
eligible, and all eight selection cells filled to 128 for 1,024 selected pairs
with no shortfall. The three checkpoints produce *identical token IDs* on every
prompt row, so downstream mechanistic comparisons run on the same token
sequences. The gate decision is
[`../../docs/decisions/study2_stage_t_tokenizer_gate.md`](../../docs/decisions/study2_stage_t_tokenizer_gate.md).

No model weight, lens, activation, probe, patching, ablation, semantic-review
provider, GPU Job, or scientific row has been produced under Study 2. A frozen
protocol, model-free task-bank generation, and a tokenizer gate are not
empirical evidence.

## Research question

Does the R1-distilled checkpoint compute and causally use a task-defined
intermediate variable during a single forward pass with zero generated
reasoning tokens, and is that behavior or mechanism stronger than in both its
lineage base checkpoint and a same-family instruction-tuned control?

The phrase “genuine reasoning” is not treated as a primitive label. The
strongest permitted operational claim, if every future gate passes, is:

> The target checkpoint uses a causally load-bearing intermediate variable to
> solve fresh compositional tasks under a controlled no-generated-trace
> interface.

## Why this is a new study

Study 1 required a raw full-vocabulary greedy next token to equal an
open-ended registered answer. That interface filtered nearly every official
item before lens validity or hidden computation could be tested. Study 2
removes that interface dependency from the primary estimand by reading four
prospectively fixed candidate logits at one answer position, with no generated
text and no semantic parser.

Study 2 is not S3 v1, a replacement batch, or a rerun. It uses new synthetic
tasks, new splits, new controls, new authority, and new terminal states.

## Design skeleton

- Task families: `permutation_chain` and `affine_mod10`.
- Depths: 1 as direct control; 2 and 3 as compositional tasks.
- Surfaces: two balanced, semantically equivalent templates.
- Observable: restricted probabilities over four fixed option tokens from one
  forward pass; zero generated tokens.
- Primary mechanism: donor-to-recipient residual patching at the answer
  position.
- Anti-copy test: patch success must favor the recombinant answer
  `g_recipient(m_donor)`, which is distinct from donor and recipient answers.
- Controls: no-op, same-intermediate, same-answer/different-intermediate,
  random donor, wrong position, early band, motor band, option balance and
  cross-template probe.
- Comparators: lineage base and same-family instruction checkpoint.
- J-lens: fixed M1200 is target-only and secondary; it cannot select or rescue
  the lens-independent result.

## Stage boundary

Stage P and Stage T are complete. Stage T resolved tokenizer identity and
alignment and sealed the mechanistic pair selection; it created no scientific
evidence and loaded no model weight. Gate A and Gate B-D remain unopened. A
separate operator authority is required before any model weight download,
forward pass, generation, activation extraction, probe, patching, ablation, or
J-lens operation.

## Read next

1. [`RESEARCH_CHARTER.md`](RESEARCH_CHARTER.md)
2. [`study2_charter.json`](study2_charter.json)
3. [`NEXT_THREAD_HANDOFF.md`](NEXT_THREAD_HANDOFF.md)
4. [`prompts/stage_p_protocol_design_prompt.md`](prompts/stage_p_protocol_design_prompt.md)
5. [`protocol/stage_p_operator_amendment_required.md`](protocol/stage_p_operator_amendment_required.md)
6. [`STAGE_P_FINAL_HANDOFF.md`](STAGE_P_FINAL_HANDOFF.md)
7. [`STAGE_T_FINAL_HANDOFF.md`](STAGE_T_FINAL_HANDOFF.md)
8. [`STAGE_T_AUTHORITY_RECEIPT.md`](STAGE_T_AUTHORITY_RECEIPT.md)
