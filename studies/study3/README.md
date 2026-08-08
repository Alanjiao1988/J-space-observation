# Study 3 - Interface Adequacy and Label-Binding Calibration

> **DESIGN DRAFT - AWAITING OPERATOR REVIEW**
>
> State: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW`
>
> Nothing here is frozen. Nothing here authorizes execution. Zero model operations have been
> performed for this study: no download, no weight load, no tokenizer construction, no forward
> pass, no generation, no activation extraction, no probe, no patch, no ablation, no lens
> operation, no GPU job. No seed has been drawn and no task-bank row exists.

## What this study is

Study 3 treats the **response and scoring interface** as the object of measurement, rather than as
background machinery. It asks whether a pre-specified interface can register competence that is
deliberately trivial - in some strata the correct answer is stated verbatim in the prompt - robustly
across answer-label permutations, option positions and prompt renderings.

## Why it exists

Study 1 ended when behavioral eligibility collapsed to 2/93, 2/55 and 5/90 and produced zero
confirmation runs; the proximate cause was an interface and parser that could not reliably extract
an answer. Study 2 ended at a Gate A that was executed honestly and did not pass, but whose design
could not separate "the target lacks this competence" from "the A/B/C/D label interface could not
express it".

Two studies have now terminated for reasons at least partly about the instrument. Study 3 validates
the instrument first, on tasks easy enough that failure cannot be blamed on difficulty.

## What it does not ask

Whether the model reasons. Whether it internalized a chain of thought. Whether distillation
transferred a causal mechanism. Whether a task-defined intermediate variable exists. Whether J-space
or J-lens is valid. Whether Study 2's Gate A should have passed.

## Contents

| path | what it is |
| --- | --- |
| `RESEARCH_CHARTER_DRAFT.md` | draft charter - scope, commitments, claim ceiling |
| `protocol/interface_calibration_protocol_draft.md` | the full design draft |
| `protocol/interface_calibration_protocol_draft.json` | machine-readable twin of the draft |
| `protocol/interface_calibration_protocol.schema.json` | fail-closed structural schema for the twin |
| `analysis/study2_to_study3_design_traceability.md` | what came from Study 2, and with what authority |
| `references/methods_sources.md` | six primary sources with limitations of application |
| `NEXT_THREAD_HANDOFF.md` | the eight open operator decisions |
| `design_receipt.json` | cryptographic binding of this design round |
| `prompts/study3_interface_calibration_design_authority.md` | the operator authority, verbatim |

## Design at a glance

**Four candidate surfaces**, none selected:

| id | surface | reads |
| --- | --- | --- |
| `S1` | restricted A/B/C/D label-token logits | one position, label tokens (Study 2 legacy comparator) |
| `S2` | direct answer-content logits | one position, content tokens |
| `S3` | conditional log-likelihood of option contents | full continuation, teacher-forced |
| `S4` | bounded minimal-answer generation | generated span, calibration reference only |

**Six fail-closed gates**, none evaluated:

| gate | asks |
| --- | --- |
| `I0` | is the renderer, mapping, scorer and ground truth correct, with no model involved? |
| `I1` | can each role emit the label for an answer that is stated in the prompt? |
| `I2` | does each role clear a depth-1 primitive by a usable margin? |
| `I3` | does the reading stay inside a pre-specified margin when only irrelevant things change? |
| `I4` | can an independently capable reference clear the compositional strata under this interface? |
| `I5` | does the one selected interface reproduce on a sealed, never-inspected bank? |

Gate `I4` is the direct structural response to Study 2's central limitation: without a positive
control on a different checkpoint, a null cannot be interpreted.

## Claim ceiling

A future pass would establish only that the named interface met its registered gates for the named
tasks and roles. A future fail would establish only that no candidate interface met them under the
registered conditions - **not** that the model is incapable. Neither direction is evidence about
reasoning, distillation, J-space, or J-lens.

## Relationship to the other studies

Study 3 does not reopen or revise either predecessor. Study 1 remains closed at
`INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`; Study 2 remains closed at
`STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`. Study 3 reuses no Study 2 item identity,
bank row, template outcome, confirmation content, seed, or result.

## Next action

**Operator review.** See `NEXT_THREAD_HANDOFF.md`. Three of the eight open decisions block progress:
the positive-reference model (`OD2`), the thresholds (`OD5`), and the sample sizes (`OD6`).
