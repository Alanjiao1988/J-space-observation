# Research index

The repository contains three scientifically distinct studies. This index is an
organizational layer; it does not move, rename, or mutate historical evidence.

Two are closed. The third exists only as a design draft and has performed zero
model operations.

| Study | Scope | State | Empirical disposition |
|---|---|---|---|
| [Study 1](study1/README.md) | Original J-space observation program, including Phase 0.5, Phase 1, S2 and frozen S3 E0 | `CLOSED` | `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`; original question not tested |
| [Study 2](study2/README.md) | Single-forward behavioral and causal test of task-defined intermediate computation with base and instruction controls | `CLOSED` | `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`; the pre-registered development feasibility gate failed, the original question was not answered, and no mechanistic stage was ever opened |
| [Study 3](study3/README.md) | Interface adequacy and label-binding calibration: whether a pre-specified response and scoring interface can recover deliberately trivial and primitive competence robustly across label permutations, option positions and renderings | `DESIGN DRAFT v0.2, REVIEWED AND REJECTED` | `STUDY3_DRAFT_V0_2_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`; the independent methods review returned `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` with six blocking findings; nothing frozen, nothing authorized, all 22 operation counters zero, no bank, no seed, no interface selected, no positive reference selected |

Study 3's draft-v0.1 was reviewed by the operator, found to contain ten design
defects, and refused freeze under
`STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`.
draft-v0.2 is the amendment; the defects and their resolutions are recorded in
[`study3/reviews/v0_1_operator_review.md`](study3/reviews/v0_1_operator_review.md).

draft-v0.2 was then submitted to a bounded independent methods review, carried
out by a party that did not write the design and that re-derived every design
statistic from the cited primary sources without importing, executing, or
reading `study3/analysis/design_statistics.py`. That review returned
`STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`: twenty findings, six of them
blocking. The `I3` primary estimand is not identifiable from the published
counterbalancing construction, the Family B per-profile alpha is asserted but not
implemented, and the four-value discordance grid cannot establish size control.
The review reproduced the drafting party's realised level of `0.025501`, so the
enumeration is correct and the defect lies in the claim made about it. The full
audit is in
[`study3/reviews/v0_2_independent_methods_review.md`](study3/reviews/v0_2_independent_methods_review.md).
The only legal next action is an operator amendment round producing draft-v0.3.
In draft-v0.2 the JSON protocol document is authoritative and the Markdown is a
companion rendering of it, and the design-critical checks are committed
artifacts rather than ephemeral scripts.

## Cross-study rule

Study 2 may cite Study 1 as motivation and may bind the identity of the sealed
M1200 artifact for a later secondary diagnostic. It may not reuse Study 1
item-level outcomes for task, template, threshold, layer, sample, or control
selection. It may not modify Study 1 terminal states or reopen Phase 1.0D.

Study 3 may cite Study 1 and Study 2 as motivation and may inherit structural
lessons from them, in particular the need for a positive control and the need to
avoid permissive output parsing. It may not reuse any Study 2 item identity,
frozen bank row, selected template outcome, confirmation content, seed, or
result as Study 3 selection data. It may not modify, reopen, revise, or
reinterpret the terminal state of either predecessor. Study 2 post-hoc
observations carry zero authority in Study 3 and may motivate a question but may
never serve as a premise, a hypothesis result, or evidence of a defect.
