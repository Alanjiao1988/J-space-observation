# Study 3 - Interface Adequacy and Label-Binding Calibration

## Interface-calibration protocol - DESIGN DRAFT

| field | value |
| --- | --- |
| study id | `jspace-study3-interface-calibration` |
| namespace | `studies/study3` |
| draft version | `draft-v0.1` |
| state | `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW` |
| document class | `design_draft` |
| frozen | `false` |
| execution authorized | `false` |
| review state | `awaiting_operator_review` |
| successor authority | `none` |
| machine-readable twin | `protocol/interface_calibration_protocol_draft.json` |
| structural schema | `protocol/interface_calibration_protocol.schema.json` |

> This document is a reviewable design draft. It is not a frozen protocol, not a pre-registration of record, and not authority to execute any model operation. Every numeric value in it is proposed, derived, or unresolved.

This Markdown document and its JSON twin are generated from one source of record and agree exactly on study identity, research question, non-questions, candidate interfaces, task strata, model and control roles, split lifecycle, gate hierarchy, proposed statistics, operation boundaries, claim ceiling, unresolved operator decisions, and state name. Where the two ever disagree, that is a defect and the disagreement itself is the finding.

### Predecessors

- **`jspace-study1`** - terminal state `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`.
  Study 1 stopped because behavioral eligibility collapsed to 2/93, 2/55 and 5/90 and produced zero confirmation runs. That collapse is the single strongest motivation for treating the response interface as an object of study in its own right.
- **`jspace-study2`** - terminal state `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`.
  Study 2 executed its Gate A honestly and did not pass it. Its integrity is not in question. What remains unresolved is whether the A/B/C/D label-token interface it used was adequate to express competence at all.

---

## 1. Research question

> Can a pre-specified response and scoring interface recover deliberately trivial, primitive, and independently demonstrated task competence robustly across answer-label permutations, option positions, and prompt renderings for the checkpoint roles relevant to a later J-space study?

- **Question class.** measurement_instrument_validation
- **Unit of analysis.** a (interface, checkpoint role, task stratum, rendering condition) cell
- **A pass would mean.** A future, separately authorized execution that passed every gate would establish only that the named interface met its pre-registered adequacy and robustness criteria for the named tasks and checkpoint roles.
- **A fail would mean.** A future execution that failed would establish only that the candidate interface panel did not meet its calibration gates under the registered conditions. It would not establish model incapability.

### 1.1 What Study 3 does not ask

These are not hedges. They are boundaries, and a future result that is written as though it answered any of them is out of protocol.

**NQ1.** Study 3 does not ask whether the R1-distilled model reasons.

> Reasoning is a theoretical construct that no accuracy-on-a-response-surface measurement can adjudicate. Study 3 measures whether an instrument can register competence that is already independently demonstrated.

**NQ2.** Study 3 does not ask whether the model internalized a chain of thought.

> Internalization is a claim about hidden process. Study 3 deliberately forbids generated rationale on three of its four candidate surfaces and never inspects internal state.

**NQ3.** Study 3 does not ask whether distillation transferred a causal mechanism.

> Causal transfer requires intervention. Study 3 authorizes no patching, no ablation, and no activation access, now or by implication.

**NQ4.** Study 3 does not ask whether a task-defined intermediate variable exists.

> Existence of an intermediate variable is the substantive question a later study might pose. Study 3 only asks whether the measuring instrument is fit to pose it.

**NQ5.** Study 3 does not ask whether J-space or J-lens is valid.

> No lens is loaded, fitted, or applied. J-lens validity is untouched by this study in either direction.

**NQ6.** Study 3 does not ask whether Study 2 Gate A should have passed.

> Study 2 is closed. Its Gate A inputs, thresholds and outcome are frozen and are not re-litigated. Study 3 is prospective and uses new banks and new seeds.

---

## 2. Validation targets

Interface adequacy is not one construct. The draft separates the following, because a single pooled accuracy number cannot distinguish among them, and Study 1 and Study 2 each terminated in a place where that distinction mattered.

### VT1 - scoring-pipeline correctness

- **Why it is needed.** If the renderer, the option-to-label mapping, or the scorer is wrong, every downstream number is uninterpretable. Study 1 and Study 2 both show that instrument faults are cheap to introduce and expensive to detect late.
- **What it cannot prove.** Correct plumbing says nothing about whether any model can use the interface.

### VT2 - answer-content to label binding

- **Why it is needed.** A model may know the answer content and still fail to emit the symbol that denotes it. Robinson, Rytting and Wingate call this multiple choice symbol binding and show it varies greatly by model.
- **What it cannot prove.** Successful binding on explicit-answer items does not show binding survives when the answer must also be computed.

### VT3 - output-surface adequacy

- **Why it is needed.** Restricted label logits, content logits, sequence log-likelihood and bounded generation are different measurement devices. Wang et al. show first-token probabilities and text answers can disagree, and that the disagreement is systematic rather than noise.
- **What it cannot prove.** Agreement among surfaces does not make any of them correct.

### VT4 - primitive task headroom

- **Why it is needed.** If a checkpoint cannot clear a depth-1 primitive under a surface, that surface cannot support a later compositional study using the same checkpoint.
- **What it cannot prove.** Headroom on primitives does not predict headroom on compositions, which is exactly why a separate positive-control gate exists.

### VT5 - compositional task headroom in an independently capable positive control

- **Why it is needed.** Without a checkpoint that is known on independent grounds to be able to do the compositional tasks, a null result is uninterpretable: instrument failure and model incapability are perfectly confounded. This confound is the specific reason Study 2 could not interpret its own Gate A outcome.
- **What it cannot prove.** A capable reference clearing the tasks does not show the Study 2 target can, and must not be read as a statement about the target.

### VT6 - robustness to answer-position and label permutation

- **Why it is needed.** Pezeshkpour and Hruschka report accuracy gaps of roughly 13 to 85 percent under option reordering; Zheng et al. attribute much of this to a prior token bias over option-ID tokens. An instrument whose reading moves that much with an irrelevant transformation is not measuring the intended quantity.
- **What it cannot prove.** Position robustness does not imply content sensitivity.

### VT7 - robustness to a small, pre-specified rendering set

- **Why it is needed.** Zhou et al. find individual-question accuracy is unstable under knowledge-equivalent rewrites, particularly for models below roughly 30B and for pretrained checkpoints. The Study 2 target is a 1.5B checkpoint.
- **What it cannot prove.** Stability over a small registered rendering set does not generalize to arbitrary prompts, and the set must stay small to keep multiplicity honest.

### VT8 - agreement or disagreement among scoring surfaces

- **Why it is needed.** Disagreement is diagnostic: it localizes whether a failure is in binding, in content access, or in generation control. Li et al. report low correlation between multiple-choice answers and long-form answers for identical questions.
- **What it cannot prove.** The surface that agrees with the others most is not thereby the most valid; agreement is descriptive and must not be promoted into a selection rule on its own.

---

## 3. Candidate response and scoring surfaces

Four families are compared. **No winner is selected in this round.** The panel exists so that a later, separately authorized execution can choose between them by a rule that was fixed before any data existed.

### S1 - `label_token_logits`

*restricted label-token logits over A/B/C/D*

**Role in the panel.** Study 2 legacy comparator, retained for continuity, not privileged

| aspect | specification |
| --- | --- |
| prompt contract | Question stem, then four options each on its own line prefixed by its label and a fixed separator, then a fixed instruction to answer with a single label, then a fixed answer cue ending immediately before the label position. |
| answer position | the single token immediately following the fixed answer cue |
| permitted output | no generated text; logits are read at one position only |
| scoring equation | argmax over the four registered label token ids of the next-token logit at the answer position; ties broken by the registered deterministic tie-break order; no renormalization is applied before argmax, and the softmax over the four ids is recorded separately as a descriptive confidence only |
| tokenization assumptions | each of the four label strings, in the exact surface form produced by the renderer, must map to exactly one token id; Study 2 established ids A=362, B=425, C=356, D=422 for the Qwen2.5 tokenizer, and a future tokenizer gate must re-derive them rather than assume them |
| abstention / invalid output | not expressible: the surface is forced-choice by construction, so it cannot distinguish 'no answer' from 'wrong answer'. This is a recorded limitation, not a defect to be patched. |
| chat template | no chat template on base and distilled checkpoints; a registered chat template is an option only if applied to every role identically, which is an unresolved operator decision |
| fairness across checkpoints | identical rendered bytes for all roles; no role-specific prompt tuning; any template applied to one role is applied to all |
| future operation counts | one forward pass per rendering; no generation |

**Known confounds.**

- option-ID token prior bias (Zheng et al.)
- position bias concentrated when the model is uncertain between the top two or three options (Pezeshkpour and Hruschka)
- first-token probability need not match what the model would write (Wang et al.)

**Disqualifying failures.**

- fails Gate I1 on explicit-answer items
- selected-label distribution outside the registered uniformity band on balanced banks
- any label string that is not single-token under the pinned tokenizer revision

### S2 - `answer_content_logits`

*direct answer-content logits over exact single-token answer contents*

**Role in the panel.** removes the label indirection while keeping a single-position read

| aspect | specification |
| --- | --- |
| prompt contract | Question stem and a fixed instruction to answer with the value only, then a fixed answer cue. Options are not shown, so no label mapping exists to be biased. |
| answer position | the single token immediately following the fixed answer cue |
| permitted output | no generated text; logits are read at one position only |
| scoring equation | argmax over the registered candidate-content token ids for that item (the correct content plus the registered distractor contents); correct if the argmax id equals the ground-truth content id |
| tokenization assumptions | every candidate content for an item must be single-token eligible under the pinned tokenizer revision, verified by a future tokenizer gate; items whose contents are not single-token eligible are excluded from this surface before any measurement, and the exclusion set is recorded |
| abstention / invalid output | not expressible over the restricted set; an unrestricted-vocabulary variant that records whether the global argmax lies outside the candidate set is proposed as an additional descriptive diagnostic |
| chat template | same policy as S1 |
| fairness across checkpoints | identical rendered bytes and identical candidate id sets for all roles |
| future operation counts | one forward pass per rendering; no generation |

**Known confounds.**

- single-token eligibility silently restricts the answer space and can make the stratum easier than intended
- frequency priors over content tokens are not removed by restriction
- without options shown, the task is open-response scored closed, which is a different task from S1 and must not be pooled with it

**Disqualifying failures.**

- insufficient single-token eligible items to reach the registered per-cell sample size
- fails Gate I2 on depth-1 primitives for the roles a later study needs

### S3 - `content_conditional_loglikelihood`

*conditional log-likelihood of exact option contents*

**Role in the panel.** the standard cloze-style comparator; the only surface that handles multi-token answers

| aspect | specification |
| --- | --- |
| prompt contract | Question stem and a fixed continuation cue, scored once per candidate content. Options are not enumerated in the prompt, so the score is independent of option order by construction. |
| answer position | the full candidate-content continuation after the cue |
| permitted output | no generated text; teacher-forced scoring only |
| scoring equation | for each candidate c, sum of log P(token_i | prefix, tokens_<i) over the tokens of c; the registered primary variant divides by the token count of c (mean log-likelihood) and the unnormalized sum is recorded as a registered secondary; both are computed from the same forward passes so no extra operations are needed; argmax over candidates |
| length handling | length normalization is a known confound that changes which candidate wins. The draft registers mean-per-token as primary and the raw sum as secondary, requires both to be reported, and requires that any stratum where the two disagree on more than a registered fraction of items be flagged as length-confounded rather than scored |
| tokenization assumptions | no single-token requirement; candidate contents must be tokenized in isolation from the prefix boundary in a registered, documented way, because leading-space handling changes token counts and therefore the normalized score |
| abstention / invalid output | not expressible; forced choice over the candidate set |
| chat template | same policy as S1 |
| fairness across checkpoints | identical prefixes, identical candidate strings, identical normalization for all roles |
| future operation counts | one teacher-forced sequence scoring per (rendering, candidate) pair, so four times the S1 cost at four candidates; no generation |

**Known confounds.**

- length and token-count asymmetry among candidates
- surface-form frequency priors
- leading-whitespace and tokenizer boundary effects
- the option set is never shown, so this surface cannot detect a comparison failure that only appears when options are visible

**Disqualifying failures.**

- primary and secondary normalizations disagree beyond the registered fraction on a gate-bearing stratum
- candidate token counts cannot be balanced or covaried within a stratum

### S4 - `bounded_minimal_generation`

*bounded minimal-answer generation, final answer only, no rationale*

**Role in the panel.** calibration reference only. It is explicitly not assumed to be the surface a later causal study would use, because free generation reintroduces the parsing dependence that ended Study 1.

| aspect | specification |
| --- | --- |
| prompt contract | Question stem, options if the stratum shows them, a fixed instruction that the reply must contain only the final answer, and a fixed answer cue. |
| answer position | the generated span, truncated at the registered maximum new-token budget |
| permitted output | at most a registered small number of new tokens, greedy decoding, temperature fixed at 0, no sampling, hard stop at a registered stop string; any generated rationale is a protocol violation for this surface and is scored as invalid rather than parsed |
| scoring equation | exact match of the normalized generated span against the ground-truth content or label after a registered, deterministic normalization (strip whitespace, case-fold, strip a registered set of trailing punctuation); no fuzzy matching, no regex rescue, no second-chance parse |
| tokenization assumptions | none beyond the pinned tokenizer; multi-token answers are permitted |
| abstention / invalid output | expressible and recorded as a distinct outcome. Invalid, empty, over-budget and off-format outputs are counted separately and are never silently mapped to a wrong answer; output validity is itself an input to Gate I1 |
| chat template | the instruction-tuned role plausibly requires its registered chat template for this surface to be meaningful, while the base role has none. This asymmetry is unresolved and is an operator-review item. |
| fairness across checkpoints | cannot be made perfectly fair across base and instruction-tuned checkpoints; the draft records this as a structural limitation of S4 rather than claiming parity |
| future operation counts | one generation per rendering, each up to the registered new-token budget; the most expensive surface in the panel |

**Known confounds.**

- format compliance is confounded with task competence
- instruction tuning advantages S4 independently of task ability
- normalization choices silently decide borderline cases
- Li et al. show multiple-choice and long-form answers correlate weakly, so S4 and S1 disagreeing is expected and is not by itself evidence that either is broken

**Disqualifying failures.**

- output-validity rate below the registered floor on explicit-answer items
- any need for a parser more permissive than the registered normalization, which would repeat the Study 1 failure

### 3.5 Selection rule (development only, one-way)

- **Principle.** one-way, development-only, pre-registered before any confirmation access
- **Eligibility.** an interface is eligible only if it passes Gates I0, I1, I2 and I3 on the development bank for every checkpoint role the later study requires
- **Confirmation-bank prohibition.** the held-out confirmation bank must never be used to choose, rank, tune or eliminate a surface, and must be physically excluded from the execution image until selection is sealed
- **A winner is selected in this round:** `true` (that is, no winner is selected)

Ranking among eligible interfaces, applied in order:

- 1. highest registered lower confidence bound on explicit-answer binding accuracy (Gate I1)
- 2. smallest registered maximum position-or-permutation effect (Gate I3)
- 3. fewest excluded items caused by the surface's own eligibility restrictions
- 4. lowest projected future operation count

**Deterministic tie-breaker.** if two interfaces remain tied after all four ranking criteria, select the lower interface id in the fixed registered order S1 < S2 < S3 < S4. The order is fixed in this draft, before any data exists, precisely so that it cannot be chosen later to favour an observed outcome.

---

## 4. Task strata

Strata are disjoint. Gates are evaluated per stratum; pooling across strata to rescue a failing gate is forbidden.

### K0 - `deterministic_software_fixtures`

| aspect | specification |
| --- | --- |
| depth | not applicable |
| uses a model | no |
| data-generating process | hand-written and programmatically enumerated fixtures covering every renderer branch, every label permutation, every option position, and every scorer outcome including invalid output |
| ground-truth function | the fixture declares its own expected rendering and expected score |
| duplicate and leakage prevention | fixtures are non-evidential and are excluded from every bank by construction; fixture content may never appear in the development or confirmation banks |
| balance invariants | every label appears as the correct answer an equal number of times |
| expected failure mode | an off-by-one in permutation application or a mislabelled ground truth |
| role in a gate | sole input to Gate I0 |

### K1 - `explicit_answer_binding`

| aspect | specification |
| --- | --- |
| depth | 0 |
| uses a model | yes |
| data-generating process | the correct content is stated verbatim in the stem, for example 'The value is 7.' followed by options containing 7 and three registered distractors; the only remaining task is to map a stated content to its label |
| ground-truth function | the stated content, by construction |
| duplicate and leakage prevention | item identity is the tuple of stem content and distractor set; duplicates are rejected at draw time and development and confirmation draws are disjoint by identity |
| balance invariants | correct answer appears in each of the four positions equally often; each label is correct equally often |
| expected failure mode | a model that knows the content but cannot emit the symbol, which is precisely the multiple choice symbol binding failure |
| role in a gate | primary input to Gate I1 |

### K2 - `identity_and_copy_depth0`

| aspect | specification |
| --- | --- |
| depth | 0 |
| uses a model | yes |
| data-generating process | identity, copy, and single-element selection items over the same value domain as the primitive strata, with no arithmetic required |
| ground-truth function | deterministic identity or projection function |
| duplicate and leakage prevention | same identity-tuple rule as K1; disjoint from K1 content |
| balance invariants | balanced correct-answer position and label |
| expected failure mode | surface or formatting failure rather than task failure |
| role in a gate | supporting input to Gate I1 and a floor for Gate I2 |

### K3 - `depth1_primitives`

| aspect | specification |
| --- | --- |
| depth | 1 |
| uses a model | yes |
| data-generating process | a single application of one registered primitive operation family to registered inputs; operation families may be reused from Study 2 at the abstract level only, never as item identities |
| ground-truth function | the deterministic primitive itself, computed in the harness, never parsed from text |
| duplicate and leakage prevention | no Study 2 item identity, frozen bank row, selected template outcome or confirmation content may be reused; new seeds are mandatory |
| balance invariants | balanced positions, labels, and operand distributions within the family |
| expected failure mode | genuine primitive-competence shortfall, or a surface that cannot express it |
| role in a gate | primary input to Gate I2 |

### K4 - `depth2_depth3_compositions`

| aspect | specification |
| --- | --- |
| depth | 2 and 3 |
| uses a model | yes |
| data-generating process | composition of two or three registered primitives with a deterministic intermediate value that is computed but never shown; included only where the positive-control rationale and the power analysis justify the cost |
| ground-truth function | deterministic composition computed in the harness |
| duplicate and leakage prevention | same as K3, plus exclusion of any composition whose intermediate collides with a K3 item identity |
| balance invariants | balanced positions and labels; intermediate values balanced across the registered range |
| expected failure mode | for the positive control, none expected; for the 1.5B roles, failure here is uninformative about the interface and must not be read as one |
| role in a gate | sole input to Gate I4; explicitly not an input to Gate I2 |

### K5 - `position_and_permutation_variants`

| aspect | specification |
| --- | --- |
| depth | inherited |
| uses a model | yes |
| data-generating process | each base item from K1, K2 and K3 is rendered under a counterbalanced set of label permutations and correct-answer positions; the registered default is the four cyclic permutations of the option order, which places the correct content in each of the four positions exactly once, plus one registered label-set replacement (A/B/C/D to 1/2/3/4) |
| ground-truth function | inherited from the base item and transformed by the applied permutation |
| duplicate and leakage prevention | variants of one base item always travel together into the same split; a base item may never straddle development and confirmation |
| balance invariants | exact counterbalance by construction, verified in Gate I0 fixtures |
| expected failure mode | position bias and option-ID token prior bias |
| role in a gate | primary input to Gate I3 |

### K6 - `rendering_variants`

| aspect | specification |
| --- | --- |
| depth | inherited |
| uses a model | yes |
| data-generating process | a deliberately small registered set of knowledge-equivalent renderings of the same item: the registered default is three renderings differing only in the separator, the instruction sentence, and the answer cue. The set is kept small because every additional rendering multiplies the multiplicity correction. |
| ground-truth function | unchanged by rendering, by construction |
| duplicate and leakage prevention | renderings of one base item travel together into the same split |
| balance invariants | every rendering is applied to every included base item |
| expected failure mode | rendering-sensitive accuracy of the kind Zhou et al. report for smaller models |
| role in a gate | secondary input to Gate I3 |

### 4.8 Bank construction, seeds and reuse

- **Bank rows generated in this round:** 0
- **Seeds drawn in this round:** 0
- **Future seed draw.** Seeds are drawn only under a separate future operator authority, from a registered entropy source, recorded in the run log before any item is generated, and bound into a sealed manifest together with the generator source digest. A seed that has been observed producing a bank may never be redrawn or re-rolled.
- **Future bank sealing.** Generate, then hash every bank file, then record the hashes and row counts in an immutable manifest, then commit and publish the manifest, and only then is the bank usable. The confirmation bank is sealed and physically excluded from the execution image until selection is complete and a separate authority releases it.
- **Study 2 reuse rule.** Study 3 may reuse abstract operation families only where justified in the traceability document. It may not reuse any Study 2 item identity, frozen bank row, selected template outcome, or confirmation content. New future seeds and disjoint development and confirmation banks are mandatory.
- **Parser dependence.** Ground truth is always computed by the harness from the generating parameters. Natural language is never parsed to establish ground truth. Only S4 parses model output at all, and only with the registered deterministic normalization.

---

## 5. Checkpoint roles and controls

| id | role | model? | identity | revision | gate role |
| --- | --- | --- | --- | --- | --- |
| `R0` | deterministic_non_model_oracle | no | `the harness itself, executed on K0 fixtures` | n/a | Gate I0 |
| `RC` | explicit_answer_binding_condition | no | `a condition, not a checkpoint: the K1 stratum applied to whichever model role is under test` | n/a | Gate I1 |
| `RT` | target | yes | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` | Gates I1, I2, I3, I5 |
| `RL` | lineage_base | yes | `Qwen/Qwen2.5-Math-1.5B` | `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2` | Gates I1, I2, I3 |
| `RI` | instruction_control | yes | `Qwen/Qwen2.5-Math-1.5B-Instruct` | `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35` | Gates I1, I2, I3 |
| `RP` | positive_capability_reference | yes | `UNSELECTED - operator review item` | `UNSELECTED` | Gate I4 only |

**`R0` - deterministic_non_model_oracle.** establishes renderer, mapping, scorer and ground-truth integrity with no model involved

> if R0 fails, no model measurement may proceed and the round stops

**`RC` - explicit_answer_binding_condition.** isolates symbol binding from task competence

> listed separately because it is a control by design, not by choice of checkpoint

**`RT` - target.** the checkpoint any later target-centered causal study would use

> The draft takes the position that the target itself must clear I1 and I2 for an interface to be useful in a later target-centered causal study. An interface that cannot register the target's competence on trivial and primitive items cannot support a causal claim about the target. This is kept logically distinct from I4.

**`RL` - lineage_base.** lineage comparison; a base checkpoint with no instruction tuning

> Its Study 2 cell that reached 44/128 must not be treated as a positive control. That cell has zero authority, arose among multiple observed control comparisons, and is a multiplicity artifact, not a demonstration of capability.

**`RI` - instruction_control.** instruction-tuning comparison; the only 1.5B role with a native chat template

> the only role for which S4 is straightforwardly meaningful, which is itself a finding about S4

**`RP` - positive_capability_reference.** a checkpoint independently expected to be able to perform the K4 compositional strata, so that a null there can be attributed to the interface rather than confounded with model incapability

> No candidate is downloaded, loaded, tokenized or benchmarked in this round. Selection requires either a defensible published-capability argument or a separate prequalification stage that never inspects the Study 3 confirmation bank.

### 5.7 Positive-capability reference: unselected

**Selection status: unselected; operator-review item.**

Hard requirements:

- pinned repository identity and immutable revision hash
- license permitting research use and redistribution of derived measurements
- must not be qualified, tuned or selected on the Study 3 confirmation bank
- must be runnable on the registered Azure GPU route

#### Tesla T4 feasibility

| aspect | assessment |
| --- | --- |
| device | Tesla T4, 16 GiB, no bfloat16 tensor-core path, fp16 supported |
| reference point | a 1.5B checkpoint in fp16 needs roughly 3.1 GiB of weights and runs comfortably |
| class 3b | roughly 6.2 GiB in fp16; fits with ample activation headroom; lowest risk |
| class 7b | roughly 15.2 GiB in fp16, which does not leave dependable headroom for activations and KV cache on a 16 GiB T4; would require either short sequences and small batches with measured margin, or quantization |
| class 8b and above | does not fit in fp16 on a T4 |
| quantization note | int8 or 4-bit quantization changes the numerics of the very logits the interfaces read. If quantization is used it must be registered as part of the checkpoint identity and the positive control must be described as 'quantized checkpoint X', not as X. |
| alternative | a larger GPU SKU on the registered Azure route removes the constraint at higher cost |

#### Candidate families for operator consideration

| family | T4 fit | argument | risk |
| --- | --- | --- | --- |
| 3B-class instruction-tuned general model | comfortable in fp16 | cheapest defensible option; capability on depth-2 arithmetic compositions is plausible but not established here | may itself fail K4, which would leave Gate I4 unsatisfied and stop the study |
| 7B-class instruction-tuned general or math model | tight in fp16; needs measured headroom or quantization | substantially more likely to clear depth-2 and depth-3 compositions | T4 memory margin and, if quantized, altered logit numerics |
| hosted or larger-SKU reference | not applicable | removes capability doubt | cost, and a provider call is currently outside the registered route |

No candidate was downloaded, loaded, tokenized or benchmarked in this round.

#### Proposed prequalification stage

- **Name.** Stage P3-Q, positive-reference prequalification
- **Authority.** separate operator authority, not granted by this draft
- **Isolation rule.** runs only on K4-shaped items drawn from a prequalification seed that is disjoint from both the development and the confirmation seeds; the confirmation bank is physically absent from the image
- **Output.** a pass or fail per candidate on a pre-registered capability floor, and nothing else
- **Prohibition.** may not be reported as a Study 3 result and may not influence interface selection

---

## 6. Splits, selection and confirmation

| split | name | evidential | content | freely inspectable | purpose |
| --- | --- | --- | --- | --- | --- |
| `F` | implementation_fixtures | no | K0 only | yes | renderer, mapping and scorer verification |
| `D` | development_bank | yes | K1, K2, K3, K5, K6 and, if authorized, K4 | yes | all interface comparison, all surface selection, all diagnostics |
| `C` | confirmation_bank | yes | disjoint draws from the same strata as D | no | one-shot confirmation of the single development-selected interface |

**Ordering.** `F` -> `D` -> `surface_selection` -> `hard_stop` -> `C`

**Surface selection.** Uses development bank only. One-way: true. Sealed before confirmation: true. Recorded artifact: a published selection record naming the interface and the ranking values that produced it.

**Hard stop before confirmation.** Required: true. Authority needed: a separate operator authority issued after the selection record is published. Rationale: prevents the selection and the confirmation from being decided in one uninterruptible run

### 6.4 Confirmation isolation rule

| rule | value |
| --- | --- |
| required | true |
| one shot | true |
| single interface only | true |
| physical exclusion before authorization | the confirmation bank files are absent from the execution image until the selection record is published and the separate authority is issued |
| no reuse after observation | once the confirmation bank has been observed under any interface it is spent; a second confirmation requires a newly generated, newly sealed bank |
| fail closed | any error, any ambiguity, any deviation from the sealed plan, or any missing counter causes the confirmation to be recorded as failed rather than retried |

### 6.5 Failure modes this lifecycle is designed to prevent

| failure mode | prevention |
| --- | --- |
| trying several surfaces on confirmation and reporting the best | exactly one interface is admitted to confirmation, named in a published record beforehand |
| changing answer mappings after observing accuracy | the option-to-label mapping is fixed in the sealed bank manifest and is hashed |
| replacing failed positive controls | the positive reference is pinned by revision before Gate I4 runs; a failed I4 stops the study and is reported as a failed gate |
| threshold shopping | thresholds are frozen at protocol freeze, before any bank is generated, and are hashed into the sealed manifest |
| cross-stratum pooling rescue | gates are evaluated per stratum and per role; pooling across strata is forbidden and pooled numbers are descriptive only |
| prompt-template rescue | the rendering set is registered and small; adding a rendering after seeing results invalidates the round |
| reusing Study 2 outcomes as Study 3 selection data | Study 2 outcomes are frozen history and are excluded from every Study 3 decision rule by construction |

---

## 7. Proposed gate hierarchy

The hierarchy is fail-closed and conjunctive. No gate authorizes mechanistic execution.

### Gate I0 - deterministic integrity

**Do the renderer, the option-to-label mapping, the ground-truth function and the scorer behave exactly as specified, with no model involved?**

| aspect | specification |
| --- | --- |
| inputs | `K0 fixtures` |
| model roles | `R0` |
| threshold logic | every fixture must match its declared expectation exactly. There is no tolerance, no sampling and no statistic: the required pass rate is 100 percent of a finite enumerated set. |
| what passes | all fixtures match; the instrument is internally consistent |
| what fails | any single mismatch |
| merely descriptive | fixture timing and coverage counts |
| legal next state on pass | proceed to I1 |
| legal next state on fail | stop; repair the harness; regenerate fixtures; rerun from I0 |
| authorizes mechanistic execution | false |
| fail closed | true |

### Gate I1 - explicit answer-to-label binding and output validity

**When the correct content is stated in the prompt, can each required checkpoint role emit the label that denotes it, and does it emit a valid output at all?**

| aspect | specification |
| --- | --- |
| inputs | `K1`, `K2` |
| model roles | `RT`, `RL`, `RI` |
| threshold logic | two conjunctive conditions per (interface, role) cell. First, an output-validity floor: the proportion of renderings producing a well-formed, in-set response must meet the registered floor; for S1, S2 and S3 this is 1.0 by construction and is therefore a check on the harness, while for S4 it is a substantive measurement. Second, a binding-accuracy floor tested as an exact one-sided binomial against H0: p <= 0.90 at the registered per-cell alpha. |
| what passes | both conditions hold for that (interface, role) cell |
| what fails | either condition fails; the interface is ineligible for that role |
| merely descriptive | which distractor absorbs the errors, and the selected-label distribution |
| legal next state on pass | the cell proceeds to I2 |
| legal next state on fail | the cell is eliminated from the panel for that role. If every interface fails for a role the later study requires, the study stops and reports interface inadequacy. |
| authorizes mechanistic execution | false |
| fail closed | true |

Proposed numbers (all **proposed, not frozen**):

| quantity | value |
| --- | --- |
| null hypothesis | `p <= 0.90` |
| recommended n per cell | `192` |
| recommended alpha per cell | `0.005` |
| derived rejection threshold X | `184` |
| derived threshold accuracy | `0.9583333333333334` |
| derived exact p at threshold | `0.002362` |
| derived power at true 0 98 | `0.9841` |
| derived power at true 0 99 | `0.9998` |
| s4 output validity floor | `0.95` |
| status | `proposed, not frozen` |

### Gate I2 - primitive-task headroom on content-based surfaces

**Does each required role clear a depth-1 primitive by a margin large enough that a later compositional design has room to detect an effect?**

| aspect | specification |
| --- | --- |
| inputs | `K3` |
| model roles | `RT`, `RL`, `RI` |
| threshold logic | exact one-sided binomial against H0: p <= 0.50 at the registered per-cell alpha. The null is deliberately far above the 0.25 forced-choice chance level, because clearing chance is not headroom; the requirement is a usable margin. |
| what passes | the role clears the primitive margin under that interface |
| what fails | it does not |
| merely descriptive | per-operation-family breakdown within K3 |
| legal next state on pass | the cell proceeds to I3 |
| legal next state on fail | the interface is ineligible for that role. A failure here is jointly attributable to interface and role and must not be reported as a capability claim about the role. |
| authorizes mechanistic execution | false |
| fail closed | true |

Proposed numbers (all **proposed, not frozen**):

| quantity | value |
| --- | --- |
| null hypothesis | `p <= 0.50` |
| recommended n per cell | `192` |
| recommended alpha per cell | `0.005` |
| derived rejection threshold X | `115` |
| derived threshold accuracy | `0.5989583333333334` |
| derived exact p at threshold | `0.003709` |
| derived power at true 0 75 | `1.0` |
| derived power at true 0 80 | `1.0` |
| status | `proposed, not frozen` |

### Gate I3 - position, permutation and rendering robustness

**Does the reading stay within a pre-specified margin when only irrelevant transformations change?**

| aspect | specification |
| --- | --- |
| inputs | `K5`, `K6` |
| model roles | `RT`, `RL`, `RI` |
| threshold logic | robustness is tested as equivalence, never as a failure to reject a difference. Three conjunctive conditions. (a) Paired equivalence across permutation conditions: for each pair of conditions over the same base items, an exact paired two-one-sided-test on the discordant pairs must place the accuracy difference inside the registered margin delta. (b) Maximum spread: the largest minus smallest per-condition accuracy must not exceed the registered maximum position-or-permutation effect. (c) Selected-label uniformity: on banks balanced by construction, the count of each selected label must fall inside a simultaneous exact acceptance band. |
| what passes | all three conditions hold |
| what fails | any one fails |
| merely descriptive | the direction of any position preference and the identity of the favoured label |
| legal next state on pass | the interface is eligible for selection |
| legal next state on fail | the interface is ineligible; a non-significant difference is never accepted as invariance |
| authorizes mechanistic execution | false |
| fail closed | true |

Proposed numbers (all **proposed, not frozen**):

| quantity | value |
| --- | --- |
| equivalence margin delta | `0.05` |
| maximum position or permutation effect | `0.05` |
| secondary margin for rendering variants | `0.075` |
| recommended n per condition | `192` |
| family alpha | `0.005` |
| multiplicity method | `Bonferroni over the number of (interface, role, condition) cells` |
| worked simultaneous bounds | `{'cells': 4, 'per_cell_alpha': 0.00125, 'n': 192, 'X': 184, 'clopper_pearson_lower': 0.8952}, {'cells': 8, 'per_cell_alpha': 0.000625, 'n': 192, 'X': 184, 'clopper_pearson_lower': 0.8901}, {'cells': 12, 'per_cell_alpha': 0.0004166666666666667, 'n': 192, 'X': 184, 'clopper_pearson_lower': 0.8872}, {'cells': 24, 'per_cell_alpha': 0.0002083333333333333, 'n': 192, 'X': 184, 'clopper_pearson_lower': 0.8824}` |
| label uniformity bands | `{'n': 192, 'per_label_alpha': 0.00125, 'accept_count_low': 31, 'accept_count_high': 68, 'accept_share_low': 0.16145833333333334, 'accept_share_high': 0.3541666666666667}, {'n': 384, 'per_label_alpha': 0.00125, 'accept_count_low': 71, 'accept_count_high': 123, 'accept_share_low': 0.18489583333333334, 'accept_share_high': 0.3203125}, {'n': 768, 'per_label_alpha': 0.00125, 'accept_count_low': 156, 'accept_count_high': 230, 'accept_share_low': 0.203125, 'accept_share_high': 0.2994791666666667}` |
| status | `proposed, not frozen` |

### Gate I4 - positive-control compositional headroom

**On the compositional strata a later study would need, does an independently capable reference checkpoint clear the task under the interface?**

| aspect | specification |
| --- | --- |
| inputs | `K4` |
| model roles | `RP` |
| threshold logic | exact one-sided binomial against H0: p <= 0.25, the forced-choice chance level, at a stricter registered alpha because this gate carries the whole interpretability of a later null. |
| what passes | the reference clears chance by the registered margin on K4 under the interface |
| what fails | it does not, or no positive reference was selected |
| merely descriptive | the reference's accuracy on K1 to K3 |
| legal next state on pass | the interface remains eligible for selection |
| legal next state on fail | the study stops and reports that no interface could be shown adequate for compositional strata. Replacing a failed positive control with a different checkpoint after seeing the result is forbidden. |
| authorizes mechanistic execution | false |
| fail closed | true |

Proposed numbers (all **proposed, not frozen**):

| quantity | value |
| --- | --- |
| null hypothesis | `p <= 0.25` |
| recommended n per cell | `128` |
| recommended alpha per cell | `0.001` |
| derived rejection threshold X | `49` |
| derived threshold accuracy | `0.3828125` |
| derived exact p at threshold | `0.0006161` |
| derived power at true 0 50 | `0.997` |
| derived power at true 0 60 | `1.0` |
| alternative n 256 alpha 0 001 | `X=87, accuracy=0.33984375, exact_p=0.0008124` |
| status | `proposed, not frozen; conditional on a positive reference being selected` |

> **Separation from target capability.** I4 is deliberately evaluated on a different checkpoint from the target. It asks whether the interface can register compositional competence in something, not whether the target has it. Passing I4 says nothing about the target. Failing I4 means a later null on the target would be uninterpretable, so the study stops rather than proceeding.

### Gate I5 - one-shot held-out confirmation

**Does the single development-selected interface reproduce its I1, I2 and I3 outcomes on a sealed, never-inspected confirmation bank?**

| aspect | specification |
| --- | --- |
| inputs | `confirmation bank draws of K1, K2, K3, K5, K6` |
| model roles | `RT`, `RL`, `RI` |
| threshold logic | the same registered thresholds as I1, I2 and I3, applied once, to one interface, on a bank observed for the first and only time. No re-selection, no second interface, no retry. |
| what passes | every reused threshold holds on the confirmation bank |
| what fails | any threshold fails, any counter is missing, or any deviation from the sealed plan occurs |
| merely descriptive | the numerical gap between development and confirmation accuracy |
| legal next state on pass | STUDY3_INTERFACE_CALIBRATION_CONFIRMED for the named interface, tasks and roles, which is a new operator decision point and nothing more |
| legal next state on fail | STUDY3_INTERFACE_CALIBRATION_NOT_CONFIRMED; the bank is spent; no retry |
| authorizes mechanistic execution | false |
| fail closed | true |

Proposed numbers (all **proposed, not frozen**):

| quantity | value |
| --- | --- |
| reuses | `I1, I2, I3` |
| n per cell | `operator decision; the development sizes are the proposed default` |
| status | `proposed, not frozen` |

### 7.7 Must the target itself pass I1 and I2?

**Position: yes, for a later target-centered causal study.**

A later study built on this interface would make claims about the target checkpoint. If the interface cannot register the target's competence on items where the answer is stated outright (I1) or on a single primitive (I2), then any later null on the target is uninterpretable in exactly the way Study 2's Gate A was. Requiring the target to clear I1 and I2 is therefore a precondition of interpretability, not a capability claim.

**Distinctness from Gate I4.** I4 is evaluated on a different checkpoint and asks a different question: can the interface register compositional competence at all. The target may legitimately fail K4 while the interface remains adequate. Conflating the two would smuggle a capability claim about the target into an instrument validation.

**If the target fails I1 or I2 under every interface.** The study reports that no candidate interface was shown adequate for the target, which is a statement about the measurement panel and the target jointly, and is not evidence of model incapability.

---

## 8. Statistical design

**Framework.** exact binomial methods throughout; no normal approximation is used for a gate decision

**Status of every number in this section: proposed or derived; none is frozen.**

### 8.1 Sample sizes

| quantity | value |
| --- | --- |
| development per cell (default) | 192 |
| confirmation per cell (default) | 192 |
| Gate I4 per cell (default) | 128 |

**Rationale.** 192 is divisible by 4, so a four-way counterbalance over label and position is exact with 48 items per position, and it is divisible by 3 so the three-rendering set is also exact at 64 items per rendering. 128 for I4 reflects the higher per-item cost of compositional items.

### 8.2 Confidence intervals and multiplicity

- **Interval method.** Clopper-Pearson exact intervals
- **Reported for.** every gate-bearing cell
- **Simultaneous coverage.** Bonferroni-adjusted per-cell alpha as tabulated in Gate I3
- **Multiplicity families.** interfaces, checkpoint roles, conditions within I3
- **Multiplicity method.** Bonferroni within each gate family; gates themselves are conjunctive, so no correction is applied across gates

> conjunctive gates make the overall false-pass rate smaller than any single gate's alpha, and make the false-fail rate larger. The draft accepts that asymmetry deliberately: a false fail costs a redesign, a false pass costs an invalid later study.

### 8.3 Equivalence, not absence of evidence

- **Method.** two one-sided tests, exact, on paired discordant counts
- **Margin delta.** `0.05`
- **Minimum practically important accuracy margin.** `0.1`
- **Minimum practically important robustness margin.** `0.05`

**Principle.** a non-significant difference is never reported as invariance. Robustness must be demonstrated by an interval falling inside the margin, not by a failure to detect.

**Rationale for the margins.** an interface whose reading moves by more than five accuracy points under a pure relabelling is not measuring the intended quantity; ten points of accuracy headroom is the smallest gap that leaves room for a later design to detect an effect without ceiling or floor artifacts.

### 8.4 Power

- **Reported at.** the registered alternatives shown in each gate's proposed_numbers
- **Worst case in the panel.** Gate I1 at n=192, alpha=0.005 has power 0.9841 against a true rate of 0.98; the same gate at n=128 falls to 0.8850, which is why 192 is the recommended default rather than 128
- **Assurance.** no prior distribution over true rates is assumed; only point-alternative power is reported

### 8.5 Deterministic tie-breaking

- **Among interfaces.** the four ranking criteria then the fixed order S1 < S2 < S3 < S4
- **Within scoring.** argmax ties broken by the registered label or candidate order, fixed before any measurement
- **Principle.** no tie is ever broken by a value observed during the round

### 8.6 Reproducible formulas

Standard library only (`Python standard library only; no third-party dependency`). Every derived number above can be recomputed with these:

```python
from math import comb

# sf(x, n, p)
def sf(x, n, p):
    return sum(comb(n, k) * p**k * (1-p)**(n-k) for k in range(x, n+1))

# smallest x in 0..n such that sf(x, n, p0) <= alpha
def exact_threshold(n, p0, alpha):
    return min(x for x in range(n+1) if sf(x, n, p0) <= alpha)

# sf(x_threshold, n, p1)
def power(x_threshold, n, p1):
    return sf(x_threshold, n, p1)

# the p solving sf(x, n, p) = alpha, obtained by bisection on (0, 1)
def clopper_pearson_lower(x, n, alpha):
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if sf(x, n, mid) > alpha else (mid, hi)
    return lo
```

> every derived number in this draft was produced by these formulas and can be recomputed without any model, any GPU and any network access

---

## 9. Operation boundaries

### 9.1 Operations performed in this design round

| counter | value |
| --- | --- |
| `model_downloads` | 0 |
| `weight_loads` | 0 |
| `tokenizer_constructions` | 0 |
| `forward_passes` | 0 |
| `generations` | 0 |
| `activation_operations` | 0 |
| `probe_fits` | 0 |
| `patching_operations` | 0 |
| `ablation_operations` | 0 |
| `lens_loads` | 0 |
| `lens_fits` | 0 |
| `lens_applies` | 0 |
| `gpu_jobs` | 0 |
| `provider_calls` | 0 |
| `bank_rows_generated` | 0 |
| `seeds_drawn` | 0 |
| `scientific_evidence_rows` | 0 |

Every counter is zero. This round produced a document and nothing else.

### 9.2 Prohibited without new operator authority

- any model download, weight load or tokenizer construction
- any forward pass or generation
- any activation extraction or probe
- any patching, ablation or lens operation
- any GPU job
- any bank generation or seed draw
- any evidence-ledger row
- any Phase 1.0D or RQ2/S4 operation
- any Study 2 state change

### 9.3 Projected future operations

**PROJECTION ONLY - not an authorization, not a budget approval**

*Assumptions.* 192 base items each for K1 and K3, 128 for K2, four permutation conditions from K5 and three renderings from K6 applied to a 128-item subset; four candidate interfaces; four checkpoint roles

| projection | value |
| --- | --- |
| renderings | 2432 |
| S1 forward passes | 2432 |
| S2 forward passes | 2432 |
| S3 sequence scorings | 9728 |
| S4 generations | 2432 |
| development total across 4 roles and 4 surfaces | 68096 |
| confirmation projection | roughly 1024 renderings per role for the selected surface only |

> these are arithmetic projections from the proposed sample sizes. They will change with every operator decision and must be recomputed at freeze time.

---

## 10. Compute and reproducibility plan

**These are design proposals only in this round: design proposals only in this round.**

| aspect | proposal |
| --- | --- |
| route | Azure Container Registry build and Azure containerized GPU execution, as already registered |
| workstation role | inspection, editing, Git, hashing and Azure submission only |
| github actions | not used |
| model and tokenizer pinning | immutable revision hashes recorded in the sealed manifest before any load |
| image and dependency locking | image digest pinned; dependency lock file hashed into the manifest |
| pre inference sealing | protocol, thresholds, banks and mapping are hashed and published before the first forward pass |
| operation counters | every prohibited and permitted operation family has an explicit counter emitted by the job and validated independently; a missing counter is a failure |
| independent finalization and validation | a finalize step recomputes every gate from raw records and must agree exactly with the job's own report |
| confirmation bank physical exclusion | confirmation files are absent from the build context until the separate release authority is issued |
| publication | fast-forward-only push with an explicit refspec; never a force push |
| post push verification | re-fetch and verify HEAD equals origin main, tree identity, clean worktree, and unchanged protected rollups |
| branch name handling | local branch and worktree names are observational metadata only. Commit, tree and protected-byte identity are the authoritative gates. A branch-name-only change triggers revalidation and logging, never a block. |
| newline corruption prevention | all authored files are written as LF bytes; recorded digests are always computed from the committed Git blob rather than the working-tree file; commits are made with core.autocrlf disabled for the operation. This is a real hazard in this repository: several protected files appear to differ locally under core.autocrlf=true while their committed blobs are byte-identical, and any check that reads the working tree instead of the blob will produce a false mismatch. |

---

## 11. Interpretation and claim ceiling

### 11.1 Maximum future conclusion, both directions

**On a pass:** The named interface met the registered adequacy and robustness gates for the named tasks and the named checkpoint roles, under the registered conditions, on a sealed held-out bank.

**On a fail:** No candidate interface met the registered gates under the registered conditions. This is a statement about the candidate panel and the registered conditions, not about model capability.

Neither direction may be written as evidence for or against hidden reasoning, distillation, causal internal computation, J-space, or J-lens.

### 11.2 Prohibited claims

- any claim that the model does or does not reason
- any claim about internalized chain of thought
- any claim that distillation did or did not transfer a causal mechanism
- any claim about the existence of a task-defined intermediate variable
- any claim for or against J-space or J-lens validity
- any claim that Study 2 Gate A should or should not have passed
- any claim of model incapability derived from an interface failure
- any claim that a passing interface validates a later experimental design

### 11.3 What a pass would and would not permit

**Would permit:** only a new operator decision about whether to design a later substantive protocol.

**Would not permit:**

- reopening Study 2
- authorizing Study 4 or Study 2 v2
- behavioral confirmation
- activation extraction
- patching
- probes
- ablations
- lens work

**Relationship to Study 2.** Study 3 neither reopens nor revises Study 2; Study 2 remains closed at its terminal state

---

## 12. Unresolved operator decisions

These are genuine decisions. Each has a recommendation and a trade-off, and each remains open. None of them is buried as a silent default in the JSON twin.

### OD1 - Should Study 3 retain all three Study 2 checkpoint roles?

- **Recommendation.** retain all three
- **Trade-off.** retaining all three roughly triples measurement cost and widens the multiplicity correction, but dropping the lineage base or the instruction control removes the only available contrast for distinguishing an interface effect from an instruction-tuning effect. Dropping the target is not an option if a later study is target-centered.
- **Status.** `unresolved`

### OD2 - Which positive-capability reference model is defensible and T4-feasible?

- **Recommendation.** do not select one on paper; authorize the separate Stage P3-Q prequalification with a 3B-class candidate first and a 7B-class fallback
- **Trade-off.** a 3B-class model fits a T4 comfortably but may itself fail the compositional strata, which would stop the study; a 7B-class model is far more likely to clear them but is tight in fp16 on 16 GiB and may require quantization that alters the logits the interfaces read. Selecting without prequalification risks discovering the failure only after the gate matters.
- **Status.** `unresolved, blocking Gate I4`

### OD3 - Does bounded final-answer generation (S4) belong in the calibration panel?

- **Recommendation.** keep it, but strictly as a calibration reference and never as the default later surface
- **Trade-off.** S4 is the only surface that can express abstention and the only one that measures what the model would actually write, and Wang et al. give a direct reason to care about that divergence. Against it: it cannot be made fair across base and instruction-tuned checkpoints, it is the most expensive surface, and any relaxation of its normalization would reproduce the parser dependence that ended Study 1.
- **Status.** `unresolved`

### OD4 - Which prompt-rendering variants are methodologically necessary?

- **Recommendation.** exactly three: the registered baseline plus one separator change and one instruction-wording change
- **Trade-off.** more renderings give a better robustness estimate and a stronger claim, but each one multiplies both cost and the multiplicity correction, and an over-large set invites the appearance of prompt shopping. Fewer than three cannot distinguish a rendering effect from noise.
- **Status.** `unresolved`

### OD5 - What accuracy, robustness, equivalence and multiplicity thresholds are acceptable?

- **Recommendation.** I1 null p<=0.90, I2 null p<=0.50, I4 null p<=0.25, equivalence margin 0.05, per-cell alpha 0.005 with Bonferroni within each gate family
- **Trade-off.** stricter thresholds reduce the chance of certifying an inadequate interface but raise the chance of discarding a usable one and increase required sample sizes. The proposed values are deliberately conservative because the cost of a false pass is an uninterpretable later study.
- **Status.** `unresolved`

### OD6 - What development and confirmation sample sizes should be used?

- **Recommendation.** 192 per cell for development and confirmation, 128 for Gate I4
- **Trade-off.** 192 gives power 0.98 at Gate I1 against a true rate of 0.98 and permits exact four-way and three-way counterbalancing; 128 drops I1 power to 0.885, which risks discarding an adequate interface; 256 buys little additional power at substantially higher cost.
- **Status.** `unresolved`

### OD7 - Is a bounded independent methods review required before freeze?

- **Recommendation.** yes, bounded to the statistical design and the gate logic, before any bank is generated
- **Trade-off.** a review costs calendar time and must be scoped tightly to avoid becoming an open-ended redesign. Against that, both prior studies terminated on instrument-level problems that a design-stage reviewer could plausibly have flagged, which is a strong argument for paying that cost once.
- **Status.** `unresolved`

### OD8 - Should a chat template be applied, and to which roles?

- **Recommendation.** no chat template for S1, S2 and S3 on any role; for S4, apply each role's native template or record its absence
- **Trade-off.** uniform treatment is cleaner for comparability but disadvantages the instruction-tuned role on generation; native templates are fairer per role but make cross-role comparison partly a comparison of templates. This asymmetry cannot be fully resolved and must be declared either way.
- **Status.** `unresolved`

---

## 13. State

```
STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW
```

This draft is complete as a draft. It is not frozen, it authorizes nothing, and the only legal next action is operator review.
