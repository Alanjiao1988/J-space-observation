# Study 2 — causal internal computation under a no-generated-trace interface

## Status

Coordination state: `FROZEN_PENDING_FINAL_ACR_VALIDATION`

Canonical protocol lifecycle: `FROZEN_AWAITING_STAGE_T`

Formal methods-review allowance: `SPENT_VERIFIED`

The model-free protocol and public deterministic banks are frozen after the
single formal methods review. An operator-directed pre-review check identified
a material feasibility-gate question. The operator selected Gate A and authorized
the additive amendment at
[`prompts/stage_p_gate_a_operator_amendment.md`](prompts/stage_p_gate_a_operator_amendment.md).
The retained gap analysis is
[`protocol/stage_p_operator_amendment_required.md`](protocol/stage_p_operator_amendment_required.md).
The freeze decision is
[`decisions/reasoning_internalization_protocol_freeze.md`](decisions/reasoning_internalization_protocol_freeze.md).

No tokenizer, model, lens, activation, probe, patching, ablation,
semantic-review provider, GPU Job, or scientific row has been produced under
Study 2. A candidate protocol and model-free task-bank generation are not
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

Only Stage P is authorized for the next thread. Stage P may create and review
the prospective protocol and deterministic public task banks. It must perform
zero tokenizer/model/lens/activation operation. Later Stage T, behavioral, and
mechanistic execution each require separate authority.

## Read next

1. [`RESEARCH_CHARTER.md`](RESEARCH_CHARTER.md)
2. [`study2_charter.json`](study2_charter.json)
3. [`NEXT_THREAD_HANDOFF.md`](NEXT_THREAD_HANDOFF.md)
4. [`prompts/stage_p_protocol_design_prompt.md`](prompts/stage_p_protocol_design_prompt.md)
5. [`protocol/stage_p_operator_amendment_required.md`](protocol/stage_p_operator_amendment_required.md)
