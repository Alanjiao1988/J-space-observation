# Study 3 - research charter (DRAFT)

**Status: DRAFT. Not frozen. Not an execution authority.**

| field | value |
| --- | --- |
| study id | `jspace-study3-interface-calibration` |
| name | Study 3 - Interface Adequacy and Label-Binding Calibration |
| namespace | `studies/study3` |
| state | `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_4_COMPLETE_AWAITING_THIRD_INDEPENDENT_METHODS_REVIEW` |
| draft version | `draft-v0.3` |
| frozen | no |
| execution authorized | no |
| bank authorized | no |
| seed authorized | no |
| model operations authorized | no |
| winner selected | no |
| positive reference selected | no |
| confirmation access authorized | no |
| operations performed | zero |

This charter is a draft. It is deliberately **not** named `RESEARCH_CHARTER.md`, because that name
is reserved in this repository for frozen, protected documents. Nothing in this file may be cited
as a commitment until an operator reviews it, amends it, and freezes it under a separate authority.

**Amendment history.** draft-v0.1 was reviewed by the operator, who recorded ten design defects and
refused freeze under `STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`.
draft-v0.2 is the resulting amendment. The defects and their resolutions are in
`reviews/v0_1_operator_review.md`.

draft-v0.2 was then submitted to a **bounded independent methods review**, which returned
`STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` with 6 BLOCKING, 11 MAJOR and 3 MINOR findings
and 22 unresolved items. draft-v0.3 is the operator amendment answering all of them; the
finding-by-finding dispositions are in `reviews/v0_3_operator_amendment.md`.

**No amendment in this history performed any measurement or closed any blocking decision.**

**The drafting party does not claim draft-v0.3 is correct.** Every repair is recorded as
`PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`. draft-v0.2 was found defensible by
the party that wrote it and was then independently rejected with six blocking findings; a design
checked only by its author is not evidence that the design is sound. That determination belongs to
the third independent methods review.

---

## 1. Why this study exists

Two studies in this repository have now terminated for reasons that were at least partly about the
*measuring instrument* rather than about the phenomenon.

**Study 1** terminated at `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`. Behavioral eligibility
collapsed to 2 of 93, 2 of 55 and 5 of 90, and zero confirmation runs were ever produced. The
proximate cause was an interface and parsing pipeline that could not reliably extract an answer.

**Study 2** terminated at `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`. Its Gate A was
executed honestly on a sealed bank with an independent finalizer and did not pass. Its integrity is
not in question. But its design could not separate two explanations for the null: the target may
lack the measured competence, or the A/B/C/D label-token interface may have been unable to express
competence that was present. Study 2's own terminal documents record that it could not choose
between these.

Both terminations share a shape: a substantive question was asked through an instrument that had
never been shown adequate to ask it. Study 3 inverts the order. It makes the instrument the object
of study, and it does so on tasks chosen to be so easy that a failure cannot plausibly be blamed on
the task.

## 2. What Study 3 asks

> Can a pre-specified response and scoring interface recover deliberately trivial, primitive, and
> independently demonstrated task competence robustly across answer-label permutations, option
> positions, and prompt renderings for the checkpoint roles relevant to a later J-space study?

## 3. What Study 3 does not ask

Study 3 does not ask whether the R1-distilled model reasons; whether it internalized a chain of
thought; whether distillation transferred a causal mechanism; whether a task-defined intermediate
variable exists; whether J-space or J-lens is valid; or whether Study 2's Gate A should have passed.

These are boundaries, not modesty. A future write-up that reads as though it answered any of them
is out of protocol regardless of what the numbers say.

## 4. Design commitments (proposed)

1. **Instrument first.** Tasks are chosen to be trivial. If the instrument fails on a task where the
   answer is stated in the prompt, no harder task can be interpreted.
2. **A positive control on a different checkpoint.** Without a checkpoint independently expected to
   succeed, a null cannot distinguish instrument failure from model incapability. This is the single
   most important structural lesson from Study 2.
3. **Robustness as a pre-registered item-level conjunction.** A reading that moves when only an
   irrelevant transformation changes is not measuring the intended quantity, and a reading that is
   stably **wrong** is not measuring it either. Robustness is therefore evaluated on
   `base_item_contrast_clusters` of exactly **two** variants, under a primary indicator `J_both`
   that requires invariance across the two variants **and** correctness against the registered
   ground truth. A stable but wrong answer scores `0`; a stable invalid or unparseable answer scores
   `0`. A failure to detect a difference is never accepted as invariance. draft-v0.1 and draft-v0.2
   stated this as an aggregate paired-equivalence interval inside a pre-specified margin; the
   independent methods review found that procedure's realised size exceeded its nominal level, and
   draft-v0.3 retires it from **every** decision role rather than recalibrating it.
4. **Multiple surfaces, never pooled.** Four interface profiles are compared per atomic cell. Their
   disagreement is diagnostic information, not noise to be averaged away. Pooling may never be used
   to rescue a failing cell.
5. **Admissibility is ordered in advance, not selected from data.** The order is published before
   any observation and may not be reordered afterwards. One profile is `never_selectable` by
   construction. Confirmation needs a separate operator authority.
6. **Ground truth is computed, never parsed.** The Study 1 failure mode is structurally excluded.
7. **A claim ceiling fixed in advance, in both directions.**
8. **Not applicable is a third value.** A transformation with no referent for a profile is recorded
   `not_applicable`, which is neither a pass nor a zero effect and may never be averaged into a rate.
9. **Every design-critical check is committed.** The statistical derivation is a committed script and
   the design invariants are a committed test with a negative-mutation battery. An ephemeral checker
   that is not committed cannot be relied on, and in draft-v0.1 one such checker missed a defect.
10. **Derivation, never transcription.** Every proposed sample size, pass count, tail mass and power
    figure is derived from first principles in **exact rational arithmetic** by the committed
    script. The committed test additionally asserts, by AST inspection, that the reviewer-returned
    planning targets appear nowhere in the script as literal constants, so a script that reproduced
    them by transcription would fail.
11. **Every `n` carries a unit.** Four units are registered - `base_item`,
    `base_item_contrast_cluster`, `rendered_row`, `scored_row` - and one `n` is never reused across
    them. The independent methods review found that the symbol `n` changed unit between artifacts
    with no unit declared anywhere.
12. **Multiplicity is exact and its denominator is fixed before data.** A study-level development
    screening alpha of `1/200` and a per-profile development component alpha of `1/600`, both exact
    rationals, with an intersection-union conjunction within a profile and a **fixed**
    selectable-profile denominator `K = 3` that never shrinks on a post-data fact. Decimal fields
    are renderings of the exact rational policy, never the source of truth.
13. **Independent review is to a protocol what a positive control is to a measurement.** A design
    that has only been checked by the party that wrote it cannot be cited as a sound design.

## 5. Claim ceiling

**A future pass would establish only** that the named interface met its registered adequacy and
robustness gates for the named tasks and checkpoint roles, under the registered conditions, on a
sealed held-out bank.

**A future fail would establish only** that no candidate interface met those gates under those
conditions. It would not establish model incapability.

Neither direction is evidence for or against hidden reasoning, distillation, causal internal
computation, J-space, or J-lens.

A pass would permit exactly one thing: a new operator decision about whether to design a later
substantive protocol. It would not reopen Study 2 and would not authorize Study 4, Study 2 v2,
behavioral confirmation, activation extraction, patching, probes, ablations, or lens work.

## 6. Relationship to Studies 1 and 2

Study 3 does not reopen, revise or reinterpret either predecessor. Study 1 remains closed at
`INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`. Study 2 remains closed at
`STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`. Study 3 inherits one structural lesson from
Study 2 - the need for a positive control - and one from Study 1 - never depend on a permissive
parser. It inherits no data, no bank, no seed, no item identity, and no result.

## 7. What has and has not happened

**Has happened.** A design draft was written, amended after operator review, submitted to a bounded
independent methods review that rejected it with six blocking findings, and amended again in
response; statistical tables were derived by model-free exact rational arithmetic in a committed
script; design invariants were expressed as a committed test; and primary sources were consulted and
cited, including the paired-equivalence methods literature - now retained as bibliography with
`NO_DECISION_ROLE` - and the model cards behind the positive-reference dossier.

**Has not happened.** No model was downloaded, loaded or tokenized. No forward pass, no generation,
no activation extraction, no probe, no patch, no ablation, no lens operation, and no GPU job was
run. No seed was drawn. No bank row was generated. No evidence row was created. No interface was
selected. No positive reference was selected, preferred, pinned, revision-resolved, downloaded,
tokenized, loaded or prequalified. No confirmation access was authorized. Every operation counter is
exactly zero.

## 8. Open decisions before any freeze

The open decisions are listed with recommendations and trade-offs in `NEXT_THREAD_HANDOFF.md`.

The draft-v0.3 operator amendment authority **resolves `OD5` and `OD6`**, subject to the second
independent methods review. `OD5` fixes the exact-rational multiplicity policy above. `OD6` fixes a
single `I3` floor, `p0 = 0.90` against `p1 = 0.97` at power at least `0.90`, giving `n = 256`
base-item contrast clusters per applicable contrast cell; the second floor `p0 = 0.95` is deleted
from every active protocol, table and packet field and survives only in clearly labelled historical
narrative, because the review established it was unreachable at any admissible sample size.

**`OD2` remains open and blocking.** No positive reference is selected, preferred, pinned,
revision-resolved, downloaded, tokenized, loaded or prequalified, and unresolved item `UR-22` stays
`UNRESOLVED_BLOCKING_OPERATOR_DECISION`. `OD2` still blocks Gate `I4`.

The legal next action is a **second bounded independent methods review**; the packet for it is
`analysis/independent_methods_review_packet_v0_3.md`.

## 9. Governing documents

| document | purpose |
| --- | --- |
| `protocol/interface_calibration_protocol_draft.json` | **authoritative** machine-readable design |
| `protocol/interface_calibration_protocol_draft.md` | companion rendering of the authoritative JSON |
| `protocol/interface_calibration_protocol.schema.json` | fail-closed structural schema |
| `reviews/v0_1_operator_review.md` | the ten draft-v0.1 defects and their resolutions |
| `analysis/design_statistics.py` | committed model-free derivation of every proposed number |
| `analysis/design_statistics_tables.json` | the derived tables the draft quotes |
| `analysis/independent_methods_review_packet.md` | bounded packet for the **first** independent reviewer, preserved unedited |
| `analysis/independent_methods_review_packet_v0_3.md` | bounded packet for the **second** independent reviewer |
| `reviews/v0_2_independent_methods_review.md` | the independent methods review of draft-v0.2 |
| `reviews/v0_3_operator_amendment.md` | the draft-v0.3 amendment record: all 20 findings, all 22 unresolved items |
| `analysis/study2_to_study3_design_traceability.md` | what came from Study 2 and with what authority |
| `references/methods_sources.md` | primary sources |
| `references/positive_reference_dossier.md` | candidate evaluation for `OD2`; selects nothing |
| `tests/test_study3_design.py` | committed design invariants and negative mutations |
| `NEXT_THREAD_HANDOFF.md` | operator decisions and the legal next action |
| `design_receipt.json` | cryptographic binding of the draft-v0.1 round |
| `design_receipt_v0_2.json` | cryptographic binding of the draft-v0.2 amendment round |
| `design_receipt_v0_3.json` | cryptographic binding of the draft-v0.3 amendment round |
| `prompts/study3_interface_calibration_design_authority.md` | the v0.1 operator authority, verbatim |
| `prompts/study3_v0_2_design_amendment_authority.md` | the v0.2 amendment authority, verbatim |
| `prompts/study3_v0_3_design_amendment_authority.md` | the v0.3 amendment authority, verbatim |

---

**The only legal next action is a second bounded independent methods review.** No freeze prompt, no
`P3-Q` prompt, no bank prompt, no seed prompt, no model prompt, no GPU prompt, no development prompt,
no confirmation prompt and no mechanistic-execution prompt exists.

## draft-v0.4 amendment summary

draft-v0.4 answers the second bounded independent methods review, which returned
`STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` with two BLOCKING, six MAJOR and two MINOR
structured findings. The charter-level consequences are:

- **The research question is narrowed.** Study 3 asks whether a pre-specified interface registers
  competence at a high **joint-correctness** rate across registered presentation *pairs*. It does not
  ask, and cannot answer, whether a presentation change has an effect. Every invariance, equivalence
  and presentation-effect claim is prohibited in active text.
- **The design now carries a binding end-to-end operating characteristic**, not a per-cell one. The
  per-cell power target is derived from a per-stage profile false-negative budget divided across the
  maximum selectable-profile cell count, and every joint bound is a union bound valid under arbitrary
  dependence.
- **The instrument gate is separated from interface adequacy.** An `I0` failure means nothing was
  measured about any interface, and it can no longer be reported as "no candidate interface passed".
- **A stochastic item-sampling model is registered**, so the exact binomial inference has a stated
  warrant. No seed is drawn and no bank exists.

The charter remains a **draft**. It is not frozen, it authorises no execution, it selects no
interface and no positive reference, and the original research question remains unanswered. The only
legal next action is a third bounded independent methods review of draft-v0.4, conducted in a fresh
session by a party that did not draft it.
