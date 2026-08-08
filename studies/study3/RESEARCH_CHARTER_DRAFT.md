# Study 3 - research charter (DRAFT)

**Status: DRAFT. Not frozen. Not an execution authority.**

| field | value |
| --- | --- |
| study id | `jspace-study3-interface-calibration` |
| name | Study 3 - Interface Adequacy and Label-Binding Calibration |
| namespace | `studies/study3` |
| state | `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW` |
| frozen | no |
| execution authorized | no |
| operations performed | zero |

This charter is a draft. It is deliberately **not** named `RESEARCH_CHARTER.md`, because that name
is reserved in this repository for frozen, protected documents. Nothing in this file may be cited
as a commitment until an operator reviews it, amends it, and freezes it under a separate authority.

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
4. **Multiple surfaces, never pooled.** Four candidate families are compared per cell. Their
   disagreement is diagnostic information, not noise to be averaged away.
5. **One-way selection, then a hard stop.** The surface is chosen on development data only, the
   choice is published, and confirmation needs a separate operator authority.
6. **Ground truth is computed, never parsed.** The Study 1 failure mode is structurally excluded.
7. **A claim ceiling fixed in advance, in both directions.**

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

**Has happened.** A design draft was written, statistical tables were derived by model-free
arithmetic, and six primary sources were consulted and cited.

**Has not happened.** No model was downloaded, loaded or tokenized. No forward pass, no generation,
no activation extraction, no probe, no patch, no ablation, no lens operation, and no GPU job was
run. No seed was drawn. No bank row was generated. No evidence row was created. No interface was
selected.

## 8. Open decisions before any freeze

Eight decisions remain open and are listed with recommendations and trade-offs in
`NEXT_THREAD_HANDOFF.md`. Three block progress: the positive-reference model (`OD2`, which blocks
Gate `I4`), the thresholds (`OD5`), and the sample sizes (`OD6`).

## 9. Governing documents

| document | purpose |
| --- | --- |
| `protocol/interface_calibration_protocol_draft.md` | the full design draft |
| `protocol/interface_calibration_protocol_draft.json` | machine-readable twin |
| `protocol/interface_calibration_protocol.schema.json` | fail-closed structural schema |
| `analysis/study2_to_study3_design_traceability.md` | what came from Study 2 and with what authority |
| `references/methods_sources.md` | primary sources |
| `NEXT_THREAD_HANDOFF.md` | operator decisions and the legal next action |
| `design_receipt.json` | cryptographic binding of this design round |
| `prompts/study3_interface_calibration_design_authority.md` | the operator authority, verbatim |

---

**The only legal next action is operator review.**
