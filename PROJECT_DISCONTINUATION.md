# Project-level discontinuation decision

> **Decision:** `PROJECT_DISCONTINUATION_2026-08-29`  
> **Status:** `DISCONTINUED — RESEARCH QUESTION UNANSWERED`  
> **Scope:** project-level and terminal

## 1. Operator decision

On 2026-08-29, the operator discontinued the J-space observation project. No Study 6, successor protocol, additional estimand search, model execution, or cloud operation is authorized by this repository.

This is a deliberate project decision, not a temporary pause and not a scientific rejection of the hypothesis.

## 2. Original question

The project sought to determine whether a DeepSeek-R1 distilled checkpoint acquired an observable and causally meaningful internal reasoning process, rather than merely reproducing visible chain-of-thought or answer patterns.

The program did not answer that question.

## 3. Why the project stops

Four constraints now coincide:

1. The completed studies did not reach a valid measurement of the original hypothesis.
2. The J-lens instrument route ended without a qualified positive control and with terminal apparatus failures.
3. Comparisons among public end-state checkpoints can establish, at most, checkpoint-level or distillation-associated differences; they cannot identify what the distillation training caused.
4. A stronger causal claim would require controlled training of matched model groups. The operator has decided that the required time and compute are outside the desired scope, and the weaker checkpoint-only claim is not the result of interest.

Continuing would therefore consume additional resources while lowering or changing the claim rather than answering the question that motivated the project.

## 4. Final claim boundary

The repository supports these statements:

- the original research question remains unanswered;
- Study 1 and Study 2 closed before any valid mechanistic confirmation;
- Study 3 and Study 3R closed without authorized scientific execution;
- Study 4F-M1 found that no natural positive reference qualified within its registered ladder, so the target checkpoint was never run;
- Study 5 terminated its estimand search, measurement route, and J-lens instrument line after six apparatus-level failures;
- the preserved engineering and governance artifacts may be useful independently of the unanswered hypothesis.

The repository does **not** support any claim that:

- J-space exists or does not exist in a DeepSeek-R1 distilled checkpoint;
- the target model has or lacks hidden reasoning;
- distillation did or did not transfer a reasoning mechanism;
- an apparatus failure is evidence for a scientific null;
- a result from a constructed or selected task transfers to real reasoning tasks.

## 5. Authoritative terminal records

| Program component | Terminal record |
|---|---|
| Study 1 | [`studies/study1/README.md`](studies/study1/README.md) |
| Study 2 | [`studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md`](studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md) |
| Study 3 | [`studies/study3/reviews/v0_7_operator_terminal_decision.md`](studies/study3/reviews/v0_7_operator_terminal_decision.md) |
| Study 3R | [`studies/study3r/STUDY3R_TERMINAL_CLOSURE.md`](studies/study3r/STUDY3R_TERMINAL_CLOSURE.md) |
| Study 4F-M1 | [`studies/study4f/execution-m1/M1_FINAL_DISCLOSURE.md`](studies/study4f/execution-m1/M1_FINAL_DISCLOSURE.md) |
| Study 5 | [`studies/study5/closure/STUDY5_CLOSURE.md`](studies/study5/closure/STUDY5_CLOSURE.md) |
| Study 5 surviving assets | [`studies/study5/closure/STUDY5_HANDOFF.md`](studies/study5/closure/STUDY5_HANDOFF.md) |

All historical files and commits remain part of the record. This decision changes the active project routing; it does not rewrite any earlier observation, registration, review, failure, or seal.

## 6. Effect on earlier prospective language

Any earlier file that describes a “next legal action”, awaits operator authority, or proposes a successor is historical provenance only. At project level, this decision withholds that authority and terminates further work.

## 7. Cloud-resource boundary

This repository closure performs no Azure operation. It does not create, delete, start, stop, deallocate, reboot, resize, redeploy, mount, reconfigure, or otherwise modify any Azure Mooncake VM, storage object, network object, identity, role assignment, model blob, OCI blob, seal, or log.

The lifecycle of existing cloud resources is a separate operator decision and is not implied by discontinuing this research project.

## 8. Restart condition

A restart would require a new, explicit project-level operator decision. It must define a new study namespace, a materially new source of identifiability or a validated instrument, a resource authorization, and a claim that is again of substantive interest to the operator. Nothing in this repository grants such authority.
