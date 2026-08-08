# Study 3 - research charter (DRAFT)

**Status: DRAFT. Not frozen. Not an execution authority.**

| field | value |
| --- | --- |
| study id | `jspace-study3-interface-calibration` |
| name | Study 3 - Interface Adequacy and Label-Binding Calibration |
| namespace | `studies/study3` |
| state | `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW` |
| draft version | `draft-v0.2` |
| frozen | no |
| execution authorized | no |
| operations performed | zero |

This charter is a draft. It is deliberately **not** named `RESEARCH_CHARTER.md`, because that name
is reserved in this repository for frozen, protected documents. Nothing in this file may be cited
as a commitment until an operator reviews it, amends it, and freezes it under a separate authority.

**Amendment history.** draft-v0.1 was reviewed by the operator, who recorded ten design defects and
refused freeze under `STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`.
draft-v0.2 is the resulting amendment. The defects and their resolutions are in
`reviews/v0_1_operator_review.md`. The amendment changed the design; it did not perform any
measurement, and it did not close any blocking decision.

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
3. **Robustness as equivalence.** A reading that moves when only an irrelevant transformation
   changes is not measuring the intended quantity. Demonstrating robustness requires an interval
   inside a pre-specified margin, never a failure to detect a difference.
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

**Has happened.** A design draft was written and then amended after operator review; statistical
tables were derived by model-free arithmetic in a committed script; design invariants were expressed
as a committed test; and primary sources were consulted and cited, including the paired-equivalence
methods literature and the model cards behind the positive-reference dossier.

**Has not happened.** No model was downloaded, loaded or tokenized. No forward pass, no generation,
no activation extraction, no probe, no patch, no ablation, no lens operation, and no GPU job was
run. No seed was drawn. No bank row was generated. No evidence row was created. No interface was
selected.

## 8. Open decisions before any freeze

Eight decisions remain open and are listed with recommendations and trade-offs in
`NEXT_THREAD_HANDOFF.md`. Three block progress: the positive reference (`OD2`, which blocks Gate
`I4`), the thresholds (`OD5`), and the sample sizes (`OD6`).

The v0.2 amendment strengthened the basis for answering them without answering any of them. In
particular the committed derivation shows that the sample size draft-v0.1 proposed does not support
the aggregate equivalence margin it asserted, at any discordance rate tested, which is why `OD6`
remains blocking rather than being quietly resolved in the drafting party's favour.

The legal next action is a **bounded independent methods review**; the packet for it is
`analysis/independent_methods_review_packet.md`.

## 9. Governing documents

| document | purpose |
| --- | --- |
| `protocol/interface_calibration_protocol_draft.json` | **authoritative** machine-readable design |
| `protocol/interface_calibration_protocol_draft.md` | companion rendering of the authoritative JSON |
| `protocol/interface_calibration_protocol.schema.json` | fail-closed structural schema |
| `reviews/v0_1_operator_review.md` | the ten draft-v0.1 defects and their resolutions |
| `analysis/design_statistics.py` | committed model-free derivation of every proposed number |
| `analysis/design_statistics_tables.json` | the derived tables the draft quotes |
| `analysis/independent_methods_review_packet.md` | bounded packet for the independent reviewer |
| `analysis/study2_to_study3_design_traceability.md` | what came from Study 2 and with what authority |
| `references/methods_sources.md` | primary sources |
| `references/positive_reference_dossier.md` | candidate evaluation for `OD2`; selects nothing |
| `tests/test_study3_design.py` | committed design invariants and negative mutations |
| `NEXT_THREAD_HANDOFF.md` | operator decisions and the legal next action |
| `design_receipt.json` | cryptographic binding of the draft-v0.1 round |
| `design_receipt_v0_2.json` | cryptographic binding of the draft-v0.2 amendment round |
| `prompts/study3_interface_calibration_design_authority.md` | the v0.1 operator authority, verbatim |
| `prompts/study3_v0_2_design_amendment_authority.md` | the v0.2 amendment authority, verbatim |

---

**The only legal next action is operator review.**
