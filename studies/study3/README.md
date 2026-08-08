# Study 3 - Interface Adequacy and Label-Binding Calibration

> **DESIGN DRAFT v0.2 - AWAITING INDEPENDENT METHODS REVIEW**
>
> State: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW`
>
> Nothing here is frozen. Nothing here authorizes execution. Zero model operations have been
> performed for this study: no download, no weight load, no tokenizer construction, no forward
> pass, no generation, no activation extraction, no probe, no patch, no ablation, no lens
> operation, no GPU job. No seed has been drawn and no task-bank row exists.
>
> draft-v0.1 was reviewed by the operator, who found ten design defects and refused freeze
> (`STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`). draft-v0.2 is the
> amendment. The defects and their resolutions are recorded in `reviews/v0_1_operator_review.md`.
>
> **The JSON protocol document is authoritative.** The Markdown is a companion rendering of it.
> Where they disagree the JSON governs and the disagreement is a defect; agreement is enforced by
> the committed test `tests/test_study3_design.py`.

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
| `protocol/interface_calibration_protocol_draft.json` | **authoritative** machine-readable design |
| `protocol/interface_calibration_protocol_draft.md` | companion rendering of the authoritative JSON |
| `protocol/interface_calibration_protocol.schema.json` | fail-closed structural schema for the JSON |
| `reviews/v0_1_operator_review.md` | the ten draft-v0.1 defects and their v0.2 resolutions |
| `analysis/design_statistics.py` | committed model-free derivation of every proposed number |
| `analysis/design_statistics_tables.json` | the derived tables the draft quotes |
| `analysis/independent_methods_review_packet.md` | bounded packet for the independent reviewer |
| `analysis/study2_to_study3_design_traceability.md` | what came from Study 2, and with what authority |
| `references/methods_sources.md` | primary sources with limitations of application |
| `references/positive_reference_dossier.md` | candidate evaluation for OD2; selects nothing |
| `NEXT_THREAD_HANDOFF.md` | the eight open operator decisions |
| `design_receipt.json` | cryptographic binding of the draft-v0.1 round |
| `design_receipt_v0_2.json` | cryptographic binding of the draft-v0.2 amendment round |
| `prompts/study3_interface_calibration_design_authority.md` | the v0.1 operator authority, verbatim |
| `prompts/study3_v0_2_design_amendment_authority.md` | the v0.2 amendment authority, verbatim |

The one dedicated test lives outside this directory, at `tests/test_study3_design.py`, so it runs
with the repository suite.

## Design at a glance

**Four interface profiles**, none selected. `selectable_status` is a pre-registered property of
the profile, not an outcome:

| id | profile | reads | selectable status |
| --- | --- | --- | --- |
| `S1` | restricted label-token logits | one position, label tokens (Study 2 legacy comparator) | `selectable` |
| `S2` | restricted content-token logits | one position, content tokens | `selectable_preferred` |
| `S3` | length-normalised sequence log-likelihood | full continuation, teacher-forced | `conditionally_selectable` |
| `S4` | constrained generation plus deterministic parser | generated span, calibration reference only | `never_selectable` |

**No interface is selected in this round.** The admissibility order is fixed in advance
(`S2`, then `S3` under its condition, then `S1`; `S4` never) and may not be reordered after seeing
data.

**Seven fail-closed gates**, none evaluated:

| gate | asks | part of eligibility |
| --- | --- | --- |
| `I0` | is the renderer, mapping, scorer and ground truth correct, with no model involved? | yes |
| `I1a` | can each role recover an answer stated verbatim in the prompt, with a valid output? | yes |
| `I1b` | does each role bind the correct content to the correct displayed symbol? | yes, where labels exist |
| `I2` | does each role clear a depth-1 primitive by a usable margin, per operation family? | yes |
| `I3` | does the reading stay inside a pre-specified margin when only irrelevant things change? | yes |
| `I4` | can an independently prequalified reference clear the compositional strata here? | yes |
| `I5` | do the constructs reproduce on a sealed, never-inspected confirmation bank? | no; it is the confirmation |

draft-v0.1 fused trivial recovery with symbol binding into a single `I1`, which made a binding
failure indistinguishable from a recovery failure; v0.2 splits them into `I1a` and `I1b`.

Gate `I4` is the direct structural response to Study 2's central limitation: without a positive
control on a different checkpoint, a null cannot be interpreted. Its failure eliminates **that
interface profile only** - it is not a global study stop, and it never leaves a failing profile
eligible. `I5` covers every gate-bearing construct, `I4` included.

**Not applicable is a third value.** A transformation that has no referent for a profile - there
are no label symbols to permute on `S2` - is recorded `not_applicable`. That is not a pass and not
a zero effect, and it may never be averaged into a rate or counted as a satisfied gate.

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

**Bounded independent methods review.** See `analysis/independent_methods_review_packet.md` for the
estimands, hypotheses, truth table, multiplicity logic, margins, power tables, the eight unresolved
statistical choices and the reviewer checklist; see `NEXT_THREAD_HANDOFF.md` for the operator
decisions. Three of the eight open decisions still block progress: the positive reference (`OD2`),
the thresholds (`OD5`) and the sample sizes (`OD6`).

The amendment did not close them. It made them answerable: every proposed number is now derived by
a committed model-free script, and the derivation shows - for instance - that `n = 192` does **not**
support the aggregate equivalence margin draft-v0.1 asserted, at any discordance rate tested.

No freeze prompt and no execution prompt exist. The only authority that may follow this document is
an independent methods review.
