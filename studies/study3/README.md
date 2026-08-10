# Study 3 - Interface Adequacy and Label-Binding Calibration

> **STUDY 3-P0 STAGE P0-T RAN AND STOPPED**
>
> State: `STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE`
>
> The CPU-only tokenizer and renderer census executed in the registered Azure
> container route and returned a registered fail-closed stop, published exactly
> as emitted. Stage P0-M was **not** begun: no checkpoint downloaded, no weight
> loaded, no GPU allocated, no forward pass, no generation.
>
> Findings: the independent renderer instantiated every applicable surface and
> all 4,902 member encodes round-tripped byte-exactly, so no unregistered
> normalization was in effect; **zero** byte-distinct pairs produced identical
> token-ID sequences anywhere in the 32-state census for any role; `S1`'s four
> label surfaces are distinct single tokens under both alphabets for all three
> roles; but `S2` and `S3` are `INELIGIBLE_TOKEN_IDS` for all three roles
> because each registered content surface `" 0"`..`" 9"` is **two** tokens
> (`[220, digit]`), so the registered single-position restricted-logit rule is
> not implementable as written.
>
> A defect in the gate's own eligibility classifier is disclosed rather than
> repaired: it propagated the role-level `S2` failure onto the `S1` cells, which
> made the emitted state more severe than this run's evidence supports. It is
> not fixed in this round, because stage P0-T is single-shot and no fix-and-rerun
> is authorized. See
> `studies/study3/pilot/p0/results/p0-t/P0_T_DISPOSITION.md`.
>
> `formal_execution_authorized = false`; `p0_pilot_execution_authorized` is now
> false because the one-shot authority is consumed. draft-v0.5 remains an
> unreviewed, unfrozen candidate; `OD2`, `UR-22` and every `RP` object remain
> unresolved; no seed, bank, winner or evidence row exists; the evidence ledger
> remains byte-identical through `EV-0016`.

> **STUDY 3-P0 FEASIBILITY PILOT REGISTERED - AWAITING THE TOKENIZER GATE**
>
> **State:** `STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE`
>
> A narrow operator decision supersedes draft-v0.5's clause naming a fourth independent methods
> review as the only legal successor, and authorizes **one** physically isolated, tightly capped
> feasibility pilot on the already named target roles `RT`, `RL` and `RI`. The pilot tests only
> whether the registered rendering, tokenization, scoring, parsing, execution, accounting and
> resource pipeline is **runnable**. See
> [`pilot/p0/README.md`](pilot/p0/README.md) and
> [`prompts/study3_p0_feasibility_pilot_authority.md`](prompts/study3_p0_feasibility_pilot_authority.md).
>
> `formal_execution_authorized = false` throughout. draft-v0.5 remains an **unreviewed, unfrozen
> candidate protocol**; P0 does not declare it correct, does not reverse or relabel any prior
> review disposition, and does **not** waive the final independent methods review. P0 measurements
> are methods-feasibility observations, never Study 3 evidence, and are counted in a separate,
> cumulative, non-resettable pilot namespace. `OD2`, `UR-22` and every `RP` object remain
> unresolved and untouched; no seed, bank, winner or evidence row exists; the evidence ledger
> remains byte-identical through `EV-0016`.

> **Study 3 draft-v0.5 bounded operator amendment - published, awaiting a FOURTH independent methods review**
>
> **State (superseded as the active state by the P0 round above, and otherwise unchanged):** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW`
>
> draft-v0.5 answers the ten `S3MR3-*` findings of the third independent methods review. Its
> blocking repair records `K6-SEP` as `not_applicable` for the option-less profiles `S2` and `S3`,
> which render neither an option label nor an option content, so each of them now carries exactly
> **one** genuine `I3` contrast, `K6-INSTR`. A byte-exact deterministic rendering registry is
> registered as a binding input. Re-derived: `S2` and `S3` fall from 19 gate-bearing cells to 16
> while `S1` stays at 43, so `m_max` remains 43 by derivation and the sizes `413`/`214`/`448` and
> their pass counts reproduce.
>
> **The legal next action is the registered P0 feasibility pilot, after which a fresh-session
> operator calibration round and then one focused fresh-session independent methods review of the
> surviving candidate are required.** Nothing is frozen, nothing is
> authorized for formal execution, every formal operation counter is zero, no bank or seed exists,
> no interface and no positive reference is selected, and `OD2`, `UR-22` and the `RP` wrappers
> remain unresolved.

> **THIRD INDEPENDENT METHODS REVIEW COMPLETE - BOUNDED AMENDMENT REQUIRED**
>
> State: `STUDY3_DRAFT_V0_4_THIRD_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`
>
> Disposition: **`STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED`**, returned against reviewed commit
> `e865be51da6c7e1a7a4f5b1fcad0efc513bd0f43`, tree `86c5a5ec0e475090c14654cff27605f883495a48`.
>
> The third bounded independent methods review of draft-v0.4 verified 5 of the 10 inherited
> second-review findings resolved and 5 partially resolved, and recorded 1 BLOCKING,
> 3 MAJOR and 6 MINOR new findings (`S3MR3-001` through `S3MR3-010`), none of them
> fundamental. Every binding statistical number in the drafting derivation was independently
> reproduced with zero numeric disagreement.
>
> The blocking finding is that the `K6-SEP` contrast cell has no referent for the option-less
> selectable profiles `S2` and `S3`: `R-sep` differs from `R-base` only in the separator between a
> label and its option content, which neither profile renders, so under the registered
> deterministic scorer that cell is a self-comparison rather than a presentation pair. The major
> findings are that the derived statistics table still admits the never-selectable profile `S4` to
> two confirmation rows, that the retired `J_both` invariance construct and the withdrawn sample
> size `256` survive in active charter, README and handoff text, and that the deterministic
> rendering surface is unregistered so the two `K6` cells cannot be instantiated.
>
> Both construct verdicts are `ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR`. The narrowed
> `J_joint_correct` estimand does serve Study 3's instrument-calibration purpose, and excluding
> generation from the selectable set is correct rather than a gap. Read
> `reviews/v0_4_independent_methods_review.md`.
>
> The only legal next action is `OPERATOR_BOUNDED_AMENDMENT_ROUND_FOR_DRAFT_V0_5`, followed by a further independent methods
> review. **Not a freeze. Not `P3-Q`. Not a bank, a seed, model execution, a development round, a
> confirmation access, a feasibility pilot or any mechanistic work.**
>
> `OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`. The review neither resolves nor advances
> it, and the disposition is not driven by it.
>
> Study 3 remains unfrozen. No interface or positive reference is selected. No bank, seed, model
> operation, gate result, confirmation access or evidence row exists. Every operation counter is
> zero. The original research question remains unanswered.

> **DRAFT-V0.4 OPERATOR AMENDMENT COMPLETE - AWAITING THE THIRD INDEPENDENT METHODS REVIEW**
>
> State: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_4_COMPLETE_AWAITING_THIRD_INDEPENDENT_METHODS_REVIEW`
>
> draft-v0.4 answers all ten findings of the second independent methods review
> (`S3MR2-001` through `S3MR2-010`: 2 BLOCKING, 6 MAJOR, 2 MINOR), together with the twenty
> inherited first-review findings and the twenty-two unresolved items. The record is
> `reviews/v0_4_operator_amendment.md`; the review object is
> `analysis/independent_methods_review_packet_v0_4.md`.
>
> **The drafting party does not claim draft-v0.4 is correct.** Every repair is recorded as
> `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`. Both independent reviews remain valid
> rejections and neither was edited.
>
> Principal changes. The gate-bearing `I3` indicator is `J_joint_correct`, a level over a
> registered item-generating distribution, and no active claim asserts invariance, equivalence
> or an absent presentation effect. A binding sampling frame registers iid draws WITH
> replacement from exact-rational generator distributions in all 34 sampling cells, retires the
> deterministic complete-block assignment of the 32-state `K5` support in favour of iid draws at
> weight `1/32`, and requires duplicates to be retained. The type-II architecture becomes an
> arbitrary-dependence union bound: per-cell budget `19/17200`, per-cell target `17181/17200`,
> profile stage floor `381/400`, study end-to-end floor `9/10`, with `m_max = 43` derived over
> the selectable profiles only. Development sizes are re-derived as the smallest unrestricted
> positive integers meeting that target: `413`, `214` and `448`. Confirmation applicability
> becomes the intersection of a component's selectable profiles with the single selected
> profile, so `S4` never appears and `I1b` and `K5` are confined to `S1`. The `S4` diagnostic
> stream carries a derived, non-null forward cost. The state machine is total and deterministic
> and an `I0` failure maps only to `STOP_INSTRUMENT_DEFECT`.
>
> The only legal next action is a **third** bounded independent methods review of draft-v0.4,
> conducted in a fresh session by a party that did not draft it. **Not a freeze. Not `P3-Q`.
> Not a bank, a seed, model execution, a development round, a confirmation access or any
> mechanistic work.**
>
> `OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`: no positive reference is selected,
> preferred, pinned, revision-resolved, downloaded, tokenized, loaded or prequalified.
> draft-v0.4 registers only the binding ordering constraint
> `P3Q >= 19/20 > I4 p1 = 9/10 > I4 p0 = 4/5`.
>
> Study 3 remains unfrozen. No interface or positive reference is selected. No bank, seed, model
> operation, gate result, confirmation access or evidence row exists. Every operation counter is
> zero. The original research question remains unanswered.

> **SECOND INDEPENDENT METHODS REVIEW COMPLETE - AMENDMENT REQUIRED**
>
> State: `STUDY3_DRAFT_V0_3_SECOND_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`
>
> Disposition: **`STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`**, returned against the reviewed commit
> `2b36f5321d830ea6f70fff2b7bbca3cb93394046`, tree `98d71cb35cca7b55d8f96f131064a5b9654dd3c7`.
>
> The second bounded independent methods review of draft-v0.3 verified 16 of the 20 inherited
> findings resolved and 4 partially resolved, and recorded 10 new findings: 2 BLOCKING, 6 MAJOR
> and 2 MINOR (`S3MR2-001` through `S3MR2-010`). The two blocking findings are that the `I3`
> primary indicator `J_both` is mathematically identical to joint correctness and identifies no
> presentation effect while the protocol's registered constructs and claim language require one,
> and that profile-level, selection-level and confirmation-level power are registered nowhere
> while an unqualified study-level target power of `9/10` is published and verified only per cell.
> Read `reviews/v0_3_independent_methods_review.md`.
>
> The only legal next action is `OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_4`, followed by a
> further independent methods review. **Not a freeze. Not `P3-Q`. Not a bank, a seed, model
> execution, a development round, a confirmation access or any mechanistic work.**
>
> `OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`: no positive reference is selected,
> preferred, pinned, revision-resolved, downloaded, tokenized, loaded or prequalified. The review
> neither resolves nor advances it.
>
> Study 3 remains unfrozen. No interface or positive reference is selected. No bank, seed, model
> operation, gate result, confirmation access or evidence row exists. Every operation counter is
> zero. The original research question remains unanswered.

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
| `reviews/v0_4_operator_amendment.md` | **the draft-v0.4 amendment record: all 10 second-review findings, all 20 inherited findings and all 22 unresolved items** |
| `reviews/v0_4_operator_amendment.json` | authoritative machine-readable form of the draft-v0.4 amendment record |
| `reviews/v0_4_operator_amendment.schema.json` | fail-closed schema for the draft-v0.4 amendment record |
| `analysis/independent_methods_review_packet_v0_4.md` | **the review object for the third independent methods review** |
| `prompts/study3_v0_4_design_amendment_authority.md` | the operator authority for the draft-v0.4 amendment round, committed verbatim |
| `design_receipt_v0_4.json` | committed-blob receipt for the draft-v0.4 round |
| `reviews/v0_3_operator_amendment.md` | **the draft-v0.3 amendment record: all 20 findings and all 22 unresolved items** |
| `reviews/v0_3_operator_amendment.json` | authoritative machine-readable form of the amendment record |
| `reviews/v0_3_operator_amendment.schema.json` | fail-closed schema for the amendment record |
| `analysis/design_statistics.py` | committed model-free derivation of every proposed number |
| `analysis/design_statistics_tables.json` | the derived tables the draft quotes |
| `analysis/independent_methods_review_packet.md` | bounded packet for the **first** independent reviewer, preserved unedited |
| `analysis/independent_methods_review_packet_v0_3.md` | bounded packet for the **second** independent reviewer |
| `analysis/study2_to_study3_design_traceability.md` | what came from Study 2, and with what authority |
| `references/methods_sources.md` | primary sources with limitations of application |
| `references/positive_reference_dossier.md` | candidate evaluation for OD2; selects nothing |
| `NEXT_THREAD_HANDOFF.md` | the eight open operator decisions |
| `design_receipt.json` | cryptographic binding of the draft-v0.1 round |
| `design_receipt_v0_2.json` | cryptographic binding of the draft-v0.2 amendment round |
| `design_receipt_v0_3.json` | cryptographic binding of the draft-v0.3 amendment round |
| `prompts/study3_interface_calibration_design_authority.md` | the v0.1 operator authority, verbatim |
| `prompts/study3_v0_2_design_amendment_authority.md` | the v0.2 amendment authority, verbatim |
| `reviews/v0_2_independent_methods_review.md` | **the independent methods review of draft-v0.2** |
| `reviews/v0_2_independent_methods_review.json` | authoritative machine-readable form of that review |
| `reviews/v0_2_independent_methods_review.schema.json` | fail-closed schema for the review JSON |
| `analysis/independent_methods_recalculation.py` | the reviewer's own derivation, independent of `design_statistics.py` |
| `analysis/independent_methods_recalculation_tables.json` | the reviewer's own tables |
| `methods_review_receipt_v0_2.json` | cryptographic binding of the independent review round |
| `prompts/study3_v0_2_independent_methods_review_authority.md` | the review authority, verbatim |
| `prompts/study3_v0_3_design_amendment_authority.md` | the v0.3 amendment authority, verbatim |

The two dedicated tests live outside this directory, at `tests/test_study3_design.py` and
`tests/test_study3_methods_review.py`, so they run with the repository suite.

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
| `I3` | on a base-item contrast cluster of exactly two variants, is the reading both invariant across the two variants and correct? | yes |
| `I4` | can an independently prequalified reference clear the compositional strata here? | yes |
| `I5` | do the constructs reproduce on a sealed, never-inspected confirmation bank? | no; it is the confirmation |

draft-v0.1 fused trivial recovery with symbol binding into a single `I1`, which made a binding
failure indistinguishable from a recovery failure; v0.2 splits them into `I1a` and `I1b`.

**What draft-v0.3 changed about the gates.** `I3` is now a pre-registered **pairwise** design over
`base_item_contrast_clusters` with exactly **2** variants each - no cross-product, no factorial
multiplication, `K5` and `K6` not crossed and drawn from disjoint base-item identities. `K5` is
exactly seven one-factor contrasts (`K5-P1`/`P2`/`P3` content-position offsets, `K5-S1`/`S2`/`S3`
correct-symbol-index offsets, `K5-A1` label-alphabet replacement) and is `not_applicable` for `S2`
and `S3` rather than passing. `K6` is two disjoint pairwise cells, `K6-SEP` and `K6-INSTR`, with the
answer cue and every other byte held fixed. The primary indicator is `J_both`, the conjunction of
invariance and correctness: a stable but **wrong** answer scores `0`, and a stable invalid or
unparseable answer scores `0`.

**Sizing and multiplicity.** *Historical record only: the sizing paragraph below
describes draft-v0.3, which the second independent methods review rejected. The
sizes named here are withdrawn and are not current; the active development sizes
are `413`, `214` and `448`, derived from the binding end-to-end power design.*
Every gate is sized by an exact-binomial rule in exact rational
arithmetic: a study-level development screening alpha of `1/200`, a per-profile development component
alpha of `1/600`, an intersection-union conjunction within a profile, and a **fixed** selectable-profile
denominator `K = 3` that never shrinks on a post-data fact. There is exactly **one** `I3` floor,
`p0 = 0.90` against `p1 = 0.97` at power at least `0.90`, giving `n = 256` base-item contrast clusters
per applicable contrast cell. No active rejection region has a pass count equal to `n`.

**Units.** Four units are registered - `base_item`, `base_item_contrast_cluster`, `rendered_row`,
`scored_row` - and every symbol `n` carries its unit at its definition and in every table. One `n`
is never reused across them.

**The paired aggregate-equivalence procedure is retired from every decision role.** It supplies no
gate, eligibility rule, selection rule, confirmation rule, claim language, equivalence margin,
critical value, discordance grid, conservativeness statement, rescue path or ranking weight. Only
purely descriptive paired 2x2 summaries survive, with no null, alpha, p-value or pass/fail.

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

**A second bounded independent methods review of draft-v0.3.** The operator amendment round is
complete. draft-v0.3 is **not** frozen, **not** approved for freeze and **not** approved for
execution.

The review object is `analysis/independent_methods_review_packet_v0_3.md`, with
`protocol/interface_calibration_protocol_draft.json` authoritative and
`reviews/v0_3_operator_amendment.md` recording the disposition of every one of the 20 findings and
every one of the 22 unresolved items. The first review's own artifacts, including the reviewer's
independent recalculation, are preserved unedited as immutable historical evidence.

Specific questions put to the second reviewer:

1. Does retiring the paired aggregate-equivalence procedure from every decision role fully remove
   the size-control defect recorded in `S3MR-004` and `S3MR-005`, or does a residual decision path
   remain anywhere in the amended protocol?
2. Is the base-item contrast cluster with exactly two variants an identifiable unit for the `I3`
   estimand under every registered contrast cell, and does `J_both` estimate what the protocol says
   it estimates?
3. Is the intersection-union treatment within a profile, combined with a fixed denominator of `3`
   across profiles and a one-shot confirmation at `1/200` on a physically disjoint split, an
   adequate multiplicity architecture for the claim the protocol permits?
4. Does the six-stream operation projection make the feasibility question answerable, and is the
   zero-incremental-cost argument for `S3` under a single-token answer domain correct as stated?
5. Are any of the twenty repairs cosmetic relabelling rather than substantive design change?

**`OD2` remains open and blocking.** No positive reference is selected, preferred, pinned,
revision-resolved, downloaded, tokenized, loaded or prequalified, and unresolved item `UR-22` stays
`UNRESOLVED_BLOCKING_OPERATOR_DECISION`.

No freeze prompt, no `P3-Q` prompt, no bank prompt, no seed prompt, no model prompt, no GPU prompt,
no development prompt, no confirmation prompt and no execution prompt exists. The only authority
that may follow this document is a second bounded independent methods review.
