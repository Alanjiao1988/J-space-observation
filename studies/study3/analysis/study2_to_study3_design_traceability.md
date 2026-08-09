# Study 2 to Study 3 design traceability

This document explains what in Study 3's design came from Study 2, and - more importantly - with
what epistemic status each input travelled.

It is organised into five deliberately separated tiers. The separation is the point. Study 2's
sealed results, its zero-authority post-hoc observations, published literature, Study 3's
prospective requirements, and the choices that remain unresolved are **not** interchangeable, and
collapsing them is the specific failure this document exists to prevent.

**Study 2 is closed.** Nothing here reopens it, revises it, reinterprets its Gate A outcome, or
changes any of its states. Study 2 remains at `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`
with documentation state `STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE`.

---

## Tier 1 - Sealed Study 2 facts

These are frozen, published, independently validated results. They may be cited as facts.

| fact | value |
| --- | --- |
| Gate A target family `permutation_chain` | 25 correct of 128 |
| Gate A target family `affine_mod10` | 33 correct of 128 |
| Gate A pass threshold | X >= 43 |
| Gate A alpha | 0.025 |
| Gate A null rate p0 | 0.25 |
| Chance level at 128 forced-choice items | 32 |
| Gate A overall outcome | `overall_gate_pass: false` |
| Combined Gate A input digest | `1433f8119b2d8e377be7ede2735430ab55006c3737ebd2bf9e0c85c486b93cf7` |
| Forward passes performed | 3072 |
| Weight loads / tokenizer constructions / model downloads | 3 / 3 / 3 |
| Generations, activations, probes, patches, ablations, lens operations | 0 |
| Behavioral confirmation | never opened |
| Stage T prompt rows per model | 17408 |
| Stage T option token ids | A=362, B=425, C=356, D=422 |
| Stage T token-id identity across all three checkpoints | identical |
| Jointly eligible pairs / selected | 2048 / 1024 |

**What these facts establish.** Study 2 executed a pre-registered gate honestly, on a sealed bank,
with an independent finalizer, and did not pass it. Its *integrity* is not in question and is not
the reason Study 3 exists.

**What these facts do not establish.** They do not establish that the target checkpoint lacks the
measured competence, because the design could not separate a competence shortfall from an interface
that could not express competence. Study 2's own terminal documents say so. That inability to
separate is the sole legitimate inheritance Study 3 takes from Study 2.

### The one structural lesson that transfers

Study 2's Gate A had no positive control capable of demonstrating that the interface could register
success on the compositional tasks at all. Consequently a null was consistent with at least two
incompatible explanations, and the study correctly declined to choose between them.

This is why Gate `I4` exists in the Study 3 draft, why it is evaluated on a *different* checkpoint
from the target, and why a failure of `I4` stops the study rather than being absorbed into a
narrative.

---

## Tier 2 - Post-hoc, zero-authority Study 2 observations

The following come from `studies/study2/analysis/stage_bd_posthoc_interface_diagnostic.md`. That
document is explicitly marked as carrying **zero evidential authority**. The observations were made
after the outcome was known, were not pre-registered, were not corrected for multiplicity, and
generated no evidence rows.

They are reproduced here **only** to record what motivated a design question. They are not findings,
not hypotheses under test, and not premises of any Study 3 gate.

| observation (zero authority) | value |
| --- | --- |
| Gate A no-template slice, depths 2 and 3 | 256 items, 58 correct, selections A=106 B=66 C=0 D=84 |
| All no-template items | 384 items, 92 correct, selections A=162 B=99 C=0 D=123 |
| Plain-template items | 256 items, 67 correct, selections A=12 B=162 C=5 D=77 |
| Short-template items | 128 items, 34 correct, selections A=2 B=77 C=4 D=45 |
| Worked-template items | 256 items, 70 correct, selections A=16 B=158 C=6 D=76 |
| Depth-1 no-template | 34 correct of 128 |
| Slice accuracies | NT 0.2396, PT 0.2617, ST 0.2656, WT 0.2734; Gate A slice 0.2266 |

### Explicit non-inference

Option C was selected zero times in the no-template condition.

**This document does not convert that observation into a Study 3 hypothesis, a Study 3 result, or
evidence that a label-binding defect occurred.** It cannot support any of those readings, for
reasons that are worth stating plainly rather than gesturing at:

- The observation is post-hoc and was one of many response-pattern comparisons available after the
  outcome was known. No multiplicity control was applied and none could be applied retroactively.
- The selection distribution across conditions is not stable in a way that supports a single
  mechanism: C is near-absent under no-template but nonzero under the other three templates, and
  the modal label itself changes between conditions.
- A skewed selection distribution is compatible with several explanations - a token prior, a
  position effect, an artifact of how items were balanced, or an ordinary consequence of a model
  performing near chance - and the design that produced it cannot distinguish among them.
- Most fundamentally: this data came from a bank and a run that were not designed to answer this
  question. Asking it of them afterwards is not a weaker version of a measurement; it is not a
  measurement.

What the observation legitimately did is much narrower, and is sufficient: it made "is the response
interface adequate?" a question worth designing a study around. A question worth asking is not a
finding, and Study 3 tests it prospectively with new seeds, new disjoint banks, pre-registered
thresholds and a positive control - none of which Study 2 had for this purpose.

### The 44/128 cell

The Study 2 lineage-base control reached 44 of 128 in one family, above the 43 threshold, with a
family pass flag of true.

**This must not be treated as a positive control for Study 3 and is not used as one anywhere in the
draft.** It carries zero authority. It arose among multiple observed control comparisons, it is a
multiplicity artifact, and treating it as a demonstration that the interface can register
compositional competence would be precisely the kind of after-the-fact promotion this document
exists to block. Gate `I4` therefore requires a checkpoint justified on independent grounds, and
`checkpoint_roles.RL` in the draft carries this warning inline.

---

## Tier 3 - Literature-motivated risks

These come from published primary sources, catalogued with full citations in
`references/methods_sources.md`. They are external to this repository and say nothing about its
checkpoints.

| risk | source | design consequence |
| --- | --- | --- |
| Option order changes accuracy substantially | Pezeshkpour and Hruschka 2024; Zhou et al. 2024; Li et al. 2024 | stratum `K5`; Gate `I3` maximum position effect |
| Option-ID tokens carry a prior token bias | Zheng et al. 2024 | surfaces `S2` and `S3` avoid label tokens; `I3` label-uniformity band |
| First-token probability can disagree with generated text | Wang et al. 2024 | surface `S4` retained; `VT8` agreement target |
| Multiple-choice and open surfaces measure different behavior | Li et al. 2024 | no pooling across surfaces or strata |
| Symbol binding is a distinct, model-varying ability | Robinson, Rytting and Wingate 2023 | stratum `K1`; Gate `I1` |
| Smaller and pretrained checkpoints are least stable under rewrites | Zhou et al. 2024 | stratum `K6`; equivalence framing of `I3` |

**Boundary.** These sources justify *looking* for a risk. They do not predict what will be found on
these checkpoints, and no Study 3 threshold was set from any number in them.

---

## Tier 4 - Study 3 prospective design requirements

What the above jointly requires of the Study 3 design. Every item is prospective: it constrains a
future, separately authorized execution, and none of it has been executed.

1. **A positive control on a different checkpoint.** Gate `I4`. Without it, a null is
   uninterpretable - the Study 2 situation exactly.
2. **Binding measured separately from competence.** Stratum `K1` and Gate `I1`. The correct content
   is stated in the prompt so that only the mapping to a label remains.
3. **Multiple surfaces, never pooled.** Four families, evaluated per cell, with disagreement treated
   as diagnostic rather than as noise.
4. **Robustness as an item-level conjunction, not an aggregate equivalence test.** Gate `I3` is
   evaluated on pre-registered **base-item contrast clusters with exactly two variants each**, and
   its primary indicator `J_both` requires that a cluster be both invariant across its two variants
   and correct against the registered ground truth. A stable but wrong answer scores `0`; a stable
   invalid or unparseable answer scores `0`. A non-significant difference is never accepted as
   invariance. draft-v0.1 and draft-v0.2 stated this requirement as an aggregate paired-equivalence
   interval inside a pre-specified margin; draft-v0.3 retires that aggregate procedure from every
   decision role after findings `S3MR-004` and `S3MR-005`.
5. **Counterbalance by construction.** Positions and labels are balanced in the bank, not corrected
   afterwards.
6. **New seeds and disjoint banks.** No Study 2 item identity, frozen bank row, selected template
   outcome, or confirmation content may be reused.
7. **One-way selection, then a hard stop.** The surface is chosen on development data only, the
   choice is published, and confirmation requires a separate operator authority.
8. **Ground truth computed, never parsed.** The Study 1 failure was a parsing-and-eligibility
   failure; only `S4` inspects model text at all, and only under a fixed normalization with no
   fallback parser.
9. **Thresholds fixed before banks exist.** Frozen at protocol freeze and hashed into the sealed
   manifest, so threshold shopping is not available.
10. **A claim ceiling in both directions.** Pre-registered before any measurement, so neither a pass
    nor a fail can be written as evidence about reasoning, distillation, J-space or J-lens.

---

## Tier 5 - Choices that remain unresolved

These are open. They are listed in full with recommendations and trade-offs in
`protocol/interface_calibration_protocol_draft.json` (authoritative), its Markdown companion, and
`NEXT_THREAD_HANDOFF.md`. The dispositions below are the draft-v0.2 dispositions; draft-v0.1 left
all eight open without dispositions.

| id | unresolved choice | blocking? |
| --- | --- | --- |
| `OD1` | whether to retain all three Study 2 checkpoint roles | no |
| `OD2` | which positive-capability reference model is defensible and T4-feasible | **yes - blocks Gate `I4`** |
| `OD3` | whether bounded final-answer generation belongs in the panel | no |
| `OD4` | which prompt-rendering variants are methodologically necessary | no |
| `OD5` | acceptable accuracy, robustness, equivalence and multiplicity thresholds | resolved in the draft-v0.3 operator amendment; still subject to the second independent methods review |
| `OD6` | development and confirmation sample sizes | resolved in the draft-v0.3 operator amendment; still subject to the second independent methods review |
| `OD7` | whether a bounded independent methods review is required before freeze | no |
| `OD8` | whether and where a chat template is applied | no |

**draft-v0.2 dispositions.** `OD1`, `OD3`, `OD4` and `OD7` are resolved; `OD8` is resolved in part;
`OD2`, `OD5` and `OD6` remain unresolved and blocking. Resolving `OD7` in the affirmative is what
makes the bounded independent methods review the legal next action rather than a freeze.

**draft-v0.3 dispositions.** The operator amendment authority resolves `OD5` and `OD6`. `OD5` fixes
an exact-rational multiplicity policy: a study-level development screening alpha of `1/200`, a
per-profile development component alpha of `1/600`, an intersection-union conjunction within a
profile so that no further within-profile Bonferroni applies, and a **fixed** selectable-profile
denominator `K = 3` that never shrinks on a post-data fact. `OD6` fixes a single I3 floor at
`p0 = 0.90` against `p1 = 0.97` with power at least `0.90`, giving `n = 256` base-item contrast
clusters per applicable contrast cell; the second floor `p0 = 0.95` is deleted from every active
protocol, table and packet field and survives only in clearly labelled historical narrative.
**`OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`** and is not touched. Resolving `OD5` and
`OD6` does not make the design correct; it makes it reviewable. The determination belongs to the
second independent methods review.

**`OD2` is still the one that can stop the study before it starts, and draft-v0.3 does not move
it.** If no positive-capability reference
can be justified within the Tesla T4 envelope without empirical screening, then Gate `I4` cannot be
evaluated, and a Study 3 null would be as uninterpretable as Study 2's was. The draft's proposed
answer is a separate prequalification stage that never inspects the Study 3 confirmation bank.
draft-v0.2 adds `references/positive_reference_dossier.md`, which evaluates named candidates against
the registered compute envelope from primary sources. The dossier selects nothing and pins nothing;
`OD2` stays blocking. draft-v0.3 restates every dossier candidate as `UNSELECTED` and corrects the
dossier's two back-references from defect `D-07`, the pooling defect, to defect `D-04`, the
positive-reference circularity and chance-level-floor defect, per finding `S3MR-020`. No checkpoint
was selected, preferred, pinned, revision-resolved, downloaded, tokenized, loaded or prequalified in
the draft-v0.3 round.

**`OD5` and `OD6` were answerable, and draft-v0.3 answers them.** draft-v0.2 derived its proposed
numbers in a committed model-free script, `analysis/design_statistics.py`, but the v0.2 independent
methods review recorded that the resulting architecture was not usable: a per-profile alpha stated
but implemented nowhere (`S3MR-003`), a false conservativeness assertion (`S3MR-004`), an
insufficient discordance grid (`S3MR-005`), two I3 floors of which one was unreachable at any
admissible sample size (`S3MR-006`), underpowered `I1a`/`I1b` at `n = 192` (`S3MR-008`) and a
degenerate rejection region whose pass count equalled `n` (`S3MR-015`). draft-v0.3 replaces the
whole architecture with an exact-binomial primary design in exact rational arithmetic, re-derives
every planning target rather than transcribing it, and forbids any active rejection region whose
pass count equals `n`. The script's committed test asserts by AST inspection that the
reviewer-returned targets appear nowhere in the script as literal constants.

---

## Summary of epistemic flow

```
Tier 1  sealed Study 2 facts ......... may be cited as facts
                                       |
                                       +--> the structural lesson: no positive control
                                            => Gate I4 exists

Tier 2  post-hoc observations ........ ZERO authority
                                       |
                                       +--> motivated a question only
                                            => never a hypothesis, never a result,
                                               never evidence of a defect

Tier 3  published literature .......... external; motivates risks
                                       |
                                       +--> strata K5/K6, gates I1a/I1b/I3, profile panel
                                       +--> paired-equivalence method (Tango 1998, Liu 2002)
                                            => draft-v0.2: the executable I3 secondary criterion
                                            => draft-v0.3: RETAINED AS BIBLIOGRAPHY,
                                               NO_DECISION_ROLE

Tier 4  prospective requirements ...... constrain a FUTURE authorized execution

Tier 5  unresolved choices ............ draft-v0.2: OD2, OD5, OD6 blocking
                                       draft-v0.3: OD5 and OD6 resolved by operator
                                       amendment, subject to review; OD2 still blocking

Tier 6  draft-v0.1 operator review .... internal, about a document; licenses amendment only

Tier 7  draft-v0.2 independent methods review
                                       |
                                       +--> external to the drafting party, internal to the
                                            repository; 20 findings; licenses amendment only
                                       +--> its recalculation is immutable historical evidence
                                       +--> it does NOT license any claim, measurement or freeze
```

Nothing in Tier 2 is permitted to move upward into Tier 1, and nothing in Tier 4 has been executed.

---

## Tier 6 - the draft-v0.1 operator review

The operator review of draft-v0.1 is a **sixth** kind of input, and it is important not to file it
under any of the five above.

- It is **not** a Tier 1 sealed fact: it is about a document, not about a measurement.
- It is **not** a Tier 2 post-hoc observation: it carries full authority over the draft.
- It is **not** a Tier 3 external risk: it is internal to this repository.
- It is **not** an empirical finding at all. The ten defects are defects in an unfrozen design
  document. They are recorded in `reviews/v0_1_operator_review.md`, and deliberately **not** in
  `paper/limitations_ledger.md`, which this repository reserves for limitations of executed
  measurement. Filing a review defect as a limitation would misrepresent a drafting error as a
  finding about the world.

What the review licenses is exactly one thing: amending the draft. It does not license any claim,
any measurement, any freeze, or any relaxation of a blocking decision.

---

## Tier 7 - the draft-v0.2 independent methods review

The independent methods review of draft-v0.2 is a **seventh** kind of input and must not be filed
under any of the six above.

- It is **not** a Tier 1 sealed fact: it is about a document, not about a measurement.
- It is **not** a Tier 2 post-hoc observation: it carries full authority over the draft.
- It is **not** a Tier 3 external risk: it was performed against this repository's own artifacts.
- It is **not** a Tier 6 operator review: the operator review was performed by the party that holds
  the authority, whereas this review was performed independently of the drafting party and returned
  a disposition the drafting party did not choose.
- It is **not** an empirical finding. Its 20 findings are defects in an unfrozen design document.
  They are recorded in `reviews/v0_2_independent_methods_review.md` and its JSON and schema
  companions, and deliberately **not** in `paper/evidence_ledger.csv` or
  `paper/limitations_ledger.md`, which this repository reserves for executed measurement.

The disposition was `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`: 6 BLOCKING, 11 MAJOR and
3 MINOR findings, with 22 unresolved items and 22 answered checklist questions.

One product of that review **is** evidence of a kind, and is treated as immutable: the reviewer's
independent exact recalculation at `analysis/independent_methods_recalculation.py` and
`analysis/independent_methods_recalculation_tables.json`. It is evidence about the *arithmetic of a
proposed procedure*, not about any checkpoint, and draft-v0.3 neither edits, re-runs, re-derives nor
supersedes it. It is preserved precisely because it is the record that draft-v0.2's conservativeness
assertion was false.

### What the draft-v0.3 amendment licenses, and what it does not

The amendment licenses exactly one thing: amending the draft again and submitting it for a
**second** independent methods review. It does not license any claim, any measurement, any freeze,
any bank, any seed, any model operation, any interface selection, any positive-reference selection
or any confirmation access.

**The drafting party does not claim the amended design is correct.** Every repair in
`reviews/v0_3_operator_amendment.md` is recorded as
`PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`. draft-v0.2 was found defensible by
the party that wrote it and was then rejected by an independent reviewer with 6 blocking findings;
that is the specific failure mode the draft-v0.3 round is required to avoid repeating.

### The one structural lesson Tier 7 adds

Tier 1 taught that a null without a positive control is uninterpretable. Tier 7 teaches the
document-level analogue: **a design that has only been checked by the party that wrote it is
uninterpretable as evidence that the design is sound.** Independent review is to a protocol what
Gate `I4` is to a measurement. That is why `OD7` was resolved in the affirmative, why a second
review is the legal next action after this amendment, and why the amendment record is forbidden
from self-approving.
