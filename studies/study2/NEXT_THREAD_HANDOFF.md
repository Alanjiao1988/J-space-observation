# Study 2 next-thread handoff

## Current state

`NONTERMINAL_CHECKPOINT_STUDY2_OPENED_AWAITING_STAGE_P`

Study 1 is closed. Study 2 is open, but Stage P has not been executed. This
handoff authorizes the next thread to execute **Stage P only**: prospective
protocol design, deterministic model-free task-bank construction, one bounded
methods review, at most one consolidated correction, freeze, validation,
ledgers, and a Stage P handoff.

It does not authorize tokenizer, model, lens, activation, probe, patching,
ablation, semantic-review, GPU, behavioral-confirmation, mechanistic, or RQ2
execution.

## Exact identities

| Identity | Value |
|---|---|
| Study 1 terminal commit | `6409d2c6d665187e4459d94d490a20d7b085e8af` |
| Study 1 terminal tree | `bc8b80cb0e66f9426dcdedd52b624c892caa3fc9` |
| Study 1 state | `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` |
| Study 2 bootstrap authority commit | `db8c100db0c16306a702d348a49a90480f440629` |
| Study 2 bootstrap authority tree | `032109e20e32f43126ade0d45c0abffa5c2de85f` |
| Stage P prompt SHA-256 | `1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37` |
| Stage P prompt size | 53,018 bytes / 1,124 lines |
| Stage P review allowance | unspent |
| Study 2 evidence rows | 0 |

The exact final `origin/main` commit and tree containing this handoff are
supplied in the operator's new-thread message. A file cannot embed the SHA of
the commit that contains itself. Treat the operator-supplied values as binding,
then require the bootstrap authority commit above to be their ancestor.

## Required reading order

Read each file completely before acting:

1. `studies/study1/README.md`
2. `studies/study1/terminal_manifest.json`
3. `studies/study2/RESEARCH_CHARTER.md`
4. `studies/study2/study2_charter.json`
5. `studies/study2/handoff_receipt.json`
6. `studies/study2/prompts/stage_p_protocol_design_prompt.md`
7. `docs/jlens_s2_s3_e0_final_handoff.md`, only for protected Study 1
   identities and interpretation boundaries

The Stage P prompt is the controlling authority. This handoff summarizes it but
does not narrow or expand it.

## First actions in the new thread

1. Fetch `origin/main` without rebasing.
2. Require it to equal the exact commit/tree supplied by the operator.
3. Require a clean worktree and preserve any unrelated change.
4. Validate `handoff_receipt.json`, the bootstrap authority ancestry, the
   53,018-byte prompt hash, all protected Study 1 anchors, and EV-0016 as the
   evidence tail.
5. Execute the Stage P prompt exactly. Do not improvise Stage T or run a
   “small diagnostic” tokenizer/model pass.

If any identity differs, stop as
`BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY`. Do not repair a mismatch under
Stage P authority.

## Research question

Does the R1-distilled checkpoint compute and causally use a task-defined
intermediate variable during a single forward pass with zero generated
reasoning tokens, and is that behavior or mechanism stronger than in both its
lineage base checkpoint and a same-family instruction-tuned control?

## Design center

- Primary behavior is a four-option logit vector from one forward pass with
  zero generated tokens.
- Primary mechanism is donor-to-recipient residual patching.
- The desired patched answer is the recombinant value
  `g_recipient(m_donor)`, distinct from donor and recipient answers.
- The same target-defined task cells and layer window apply to both controls.
- M1200 is target-only secondary evidence and cannot select or rescue the
  lens-independent result.

## Study 1 boundary

Study 1's valid E0 floor failure did not answer the original research question.
Do not rerun or reinterpret it. Do not use its item-level outcomes to select a
Study 2 task, prompt, threshold, layer, pair, or control. Phase 1.0D remains
independently `BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY` and is outside
this authority.

## Expected Stage P endpoint

The normal successful endpoint is:

`NONTERMINAL_CHECKPOINT_STUDY2_PROTOCOL_FROZEN_AWAITING_TOKENIZER_GATE_AND_EXECUTION`

That endpoint is still not empirical evidence. Stage T and every behavioral or
mechanistic run require later, separate authority.
