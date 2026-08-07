# Study 2 research charter

## 1. Purpose

Study 2 is a prospective behavioral and causal study of intermediate
computation in `DeepSeek-R1-Distill-Qwen-1.5B`. It begins only after Study 1
has been closed and indexed. It does not inherit Study 1's failed eligibility
interface or scientific authority.

## 2. Registered conceptual target

The study asks whether a task-defined intermediate variable is:

1. behaviorally useful in a single forward pass with no generated trace;
2. represented in a way that generalizes across prompt templates;
3. causally load-bearing under donor–recipient recombination;
4. stronger in the R1-distilled checkpoint than in both fixed controls.

The study does not claim to detect an unobserved natural-language chain of
thought. It tests controlled internal computation.

## 3. Fixed checkpoints

| Role | Identity | Revision |
|---|---|---|
| target | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| lineage base | `Qwen/Qwen2.5-Math-1.5B` | `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2` |
| instruction control | `Qwen/Qwen2.5-Math-1.5B-Instruct` | `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35` |

The base control is needed to compare against the named checkpoint lineage.
The instruction control is needed to reduce the alternative explanation that
an apparent target advantage is generic instruction following or post-training.
Neither alone licenses a distillation-associated conclusion.

## 4. Primary behavioral observable

Every prompt ends at a registered answer position. The model generates zero
tokens. The experiment reads the logits for exactly four candidate option
continuations and computes a restricted four-way distribution. Full-vocabulary
rank and top-1 remain diagnostics only.

This measures controlled discriminative preference. It does not measure
spontaneous open-ended generation or normal conversational performance.

## 5. Primary causal observable

For a donor intermediate `m_d`, recipient intermediate `m_r`, donor downstream
map `g_d`, and recipient downstream map `g_r`, construct:

- donor answer `a_d = g_d(m_d)`;
- recipient answer `a_r = g_r(m_r)`;
- recombinant answer `a_x = g_r(m_d)`.

Require `a_d`, `a_r`, and `a_x` to be pairwise distinct and present in one
shared option mapping. Donor-to-recipient patching supports recomputation only
when it moves the recipient toward `a_x` beyond donor-answer copying and all
matched controls.

## 6. Prospective stage order

1. **P — protocol design and task banks.** Model-free. One bounded methods
   review and at most one consolidated correction.
2. **T — identity and tokenization.** Pinned configs/tokenizers only; seal
   exact option tokens, lengths, positions, and eligible mechanistic pairs
   before any model forward.
3. **B-D — behavioral development.** Verify implementation without changing
   frozen scientific choices.
4. **B-C — behavioral confirmation.** Closed row pack and target-defined cell
   selection.
5. **M-D — mechanistic development.** Target-only localization using the
   frozen algorithm.
6. **M-C — mechanistic confirmation.** Fixed-window target and control
   patching, probes, and secondary J-lens axis.

No stage may borrow confirmation information to revise an earlier stage.

## 7. Claim hierarchy

- Behavioral success without causal success is `behavior only`.
- A one-family causal result is explicitly non-generalized.
- A target causal result without positive comparisons against both controls
  cannot be called distillation-associated.
- A validated M1200 axis may support a bounded Study 2 J-space statement, but
  cannot promote the lens-independent causal axis.
- Operational incompleteness is `not estimable`, never a scientific negative.

## 8. Separation from Study 1

- Study 1 item-level outputs cannot select Study 2 tasks, thresholds, layers,
  items, pairs, or controls.
- Study 1 files remain at their historical paths and protected hashes.
- Phase 1.0D remains independently blocked and is outside this authority.
- Existing A600/B600/M1200 may not be opened during Stage P. Their identity may
  be cited only to bind a possible later target-only secondary analysis.

## 9. Current authorization

The next thread may execute only the Stage P authority at
`prompts/stage_p_protocol_design_prompt.md`. It may not start Stage T or any
empirical execution. The successful Stage P endpoint is a frozen protocol,
not a scientific result.
