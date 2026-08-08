# Study 3 - interface adequacy and label-binding calibration

**State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW`

**Draft version:** draft-v0.2

**Frozen:** `false`  **Execution authorized:** `false`  **Review state:** `awaiting_independent_methods_review`

**Successor authority:** `none`

## How to read this pair of documents

The JSON document interface_calibration_protocol_draft.json is the authoritative record of this design. The Markdown document interface_calibration_protocol_draft.md is a companion rendering of it. Where the two disagree, the JSON governs and the disagreement is a defect. Agreement on every decision-bearing marker is enforced by the committed test at tests/test_study3_design.py. No claim is made that the two documents are generated from a single source of record, because no such generator is committed; what is committed, and therefore what is checked, is the agreement itself.

draft-v0.2 is an amendment produced in response to an operator review that found ten design defects in draft-v0.1 and refused freeze. Nothing here is frozen, nothing here is authorised for execution, and no scientific measurement of any kind was performed to produce it.

## What draft-v0.2 is

draft-v0.2 is an amendment. An operator review of draft-v0.1 found ten design
defects and refused freeze, with disposition
`STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`.
draft-v0.1 is preserved unedited, and its receipt at
`studies/study3/design_receipt.json` is retained verbatim.
The full review record is at `studies/study3/reviews/v0_1_operator_review.md`.

Every item in that review is classified as **design defects in an unfrozen draft; not empirical findings, not measurements, not results**.

| Defect | Summary | Resolution |
| --- | --- | --- |
| D-01 | the Markdown companion contradicted its JSON twin about whether a winner was selected | resolved; JSON declared authoritative, label corrected, parity test committed |
| D-02 | the Markdown made an unsupported single-source provenance claim | resolved; the claim is removed and replaced by an enforced statement |
| D-03 | gate lifecycle contradictions around I4 and I5 | resolved; I4 is part of eligibility, its failure is per interface, I5 covers every construct |
| D-04 | positive-reference circularity and a chance-level floor that is not a capability floor | structurally resolved; floor value blocking as OD5 |
| D-05 | robustness construct mismatch and not_applicable treated as a pass | resolved; item-level consistency is primary and not_applicable is a third value |
| D-06 | the statistics were incomplete | derivations committed and verified; margin and sample size blocking as OD6 |
| D-07 | pooling could mask a failed cell | resolved; atomic cells defined and pooling rescue prohibited |
| D-08 | panel and selection contradiction over S4 and S3 | resolved; S4 never selectable, S3 conditional, ranking replaced by admissibility order |
| D-09 | counterbalancing was ambiguous and the label alphabet collided with the answer domain | resolved; orthogonal construction published, 1/2/3/4 forbidden |
| D-10 | Study 1 overstatement | resolved; the accurate statement is used |
| D-11 | reproducibility gap: the v0.1 checker was ephemeral and missed D-01 | resolved; design-critical checks are committed |

## Research question

Can a pre-specified response and scoring interface recover deliberately trivial, primitive, and independently demonstrated task competence robustly across answer-label permutations, option positions, and prompt renderings for the checkpoint roles relevant to a later J-space study?

- **Question class:** measurement_instrument_validation
- **Unit of analysis:** a (interface, checkpoint role, task stratum, rendering condition) cell
- **What a pass would mean:** A future, separately authorized execution that passed every gate would establish only that the named interface met its pre-registered adequacy and robustness criteria for the named tasks and checkpoint roles.
- **What a fail would mean:** A future execution that failed would establish only that the candidate interface panel did not meet its calibration gates under the registered conditions. It would not establish model incapability.

### What this study is not asking

- **NQ1.** Study 3 does not ask whether the R1-distilled model reasons. _(Reasoning is a theoretical construct that no accuracy-on-a-response-surface measurement can adjudicate. Study 3 measures whether an instrument can register competence that is already independently demonstrated.)_
- **NQ2.** Study 3 does not ask whether the model internalized a chain of thought. _(Internalization is a claim about hidden process. Study 3 deliberately forbids generated rationale on three of its four candidate surfaces and never inspects internal state.)_
- **NQ3.** Study 3 does not ask whether distillation transferred a causal mechanism. _(Causal transfer requires intervention. Study 3 authorizes no patching, no ablation, and no activation access, now or by implication.)_
- **NQ4.** Study 3 does not ask whether a task-defined intermediate variable exists. _(Existence of an intermediate variable is the substantive question a later study might pose. Study 3 only asks whether the measuring instrument is fit to pose it.)_
- **NQ5.** Study 3 does not ask whether J-space or J-lens is valid. _(No lens is loaded, fitted, or applied. J-lens validity is untouched by this study in either direction.)_
- **NQ6.** Study 3 does not ask whether Study 2 Gate A should have passed. _(Study 2 is closed. Its Gate A inputs, thresholds and outcome are frozen and are not re-litigated. Study 3 is prospective and uses new banks and new seeds.)_

## Applicability is a third value

not_applicable is a third value. It is not a pass, it is not a zero effect, it is not evidence of robustness, and it may never be counted as a satisfied gate, averaged into any rate, or used as an input to admissibility. A gate whose transformation is not applicable to a profile is simply not evaluated for that profile, and the profile's eligibility rests on the gates that are applicable to it.

## Interface profiles

draft-v0.1 described each candidate as a scoring formula. A scoring formula is
not enough to decide which calibration transformations even have a referent, so
draft-v0.2 replaces it with a complete profile.

| Profile | Name | Options visible | Labels visible | Selectable status |
| --- | --- | --- | --- | --- |
| S1 | `label_token_logits` | `true` | `true` | `selectable` |
| S2 | `content_token_logits` | `false` | `false` | `selectable_preferred` |
| S3 | `content_sequence_likelihood` | `false` | `false` | `conditionally_selectable` |
| S4 | `free_generation_with_parser` | `true` | `true` | `never_selectable` |

### S1 - label_token_logits

- **Family:** restricted label-token logits over a four-symbol label alphabet
- **Role in panel:** Study 2 legacy comparator, retained for continuity and not privileged
- **Prompt and rendering contract:** Question stem, then four option lines each prefixed by its displayed label symbol and a fixed separator, then a fixed instruction to answer with a single label symbol, then a fixed answer cue ending immediately before the label position.
- **Options visible:** `true`
- **Labels visible:** `true`
- **Scoring formula:** argmax over the four registered label token ids of the next-token logit at the answer position, with ties broken by the registered deterministic order; no renormalisation is applied before argmax and the softmax over the four ids is recorded separately as a descriptive confidence only
- **Tokenizer eligibility rule:** every label surface string, in the exact form emitted by the renderer, must map to exactly one token id under the pinned tokenizer of every required role; the four ids must be pairwise distinct; failure is an eligibility failure of the profile, never a silent fallback
- **Output validity rule:** no text is generated; exactly one logit vector is read at exactly one position, so an invalid output is impossible by construction and the output-validity rate is defined as identically 1 and is not a gate input
- **Applicable gates:** `I0`, `I1a`, `I1b`, `I2`, `I3`, `I4`, `I5`
- **Selectable status:** `selectable`
- **Why:** S1 displays options and labels, so every calibration transformation has a referent and every gate is applicable; it is admissible but ranked last, because it is the surface whose adequacy is under suspicion

**Chat template policy by role**

- `R0`: not applicable; R0 is a deterministic software control and never receives a prompt
- `RC`: not applicable; RC is a deterministic software control and never receives a prompt
- `RT`: no chat template; raw completion surface
- `RL`: no chat template; raw completion surface
- `RI`: no chat template; raw completion surface
- `RP`: deferred to OD2; the RP canonical qualification wrapper is not settled and must be frozen before P3-Q and I4

**Transformations that are `not_applicable` to S1:** none; every
calibration transformation has a referent for this profile.

**Projected operation counts if a later authority permits execution**

- `forward_passes_per_item`: 1
- `generated_tokens_per_item`: 0
- `scored_positions_per_item`: 1
- `logit_reads_per_item`: 1

**Known confounds**

- a label-token frequency prior can substitute for content binding
- position of the correct content is confounded with the displayed symbol unless the counterbalancing design separates them
- label symbols that also occur in the answer domain are ambiguous

**Disqualifying failures**

- any label surface string that is not single-token under a required role
- duplicate label token ids
- failure of I1b, which is the gate that distinguishes binding from prior

### S2 - content_token_logits

- **Family:** restricted content-token logits over the frozen answer domain
- **Role in panel:** primary candidate; the surface that asks the model for the answer itself rather than for a symbol standing for the answer
- **Prompt and rendering contract:** Question stem, then a fixed instruction to state the answer value directly, then a fixed answer cue ending immediately before the answer position. No option list is rendered and no label symbol is displayed.
- **Options visible:** `false`
- **Labels visible:** `false`
- **Scoring formula:** argmax over the registered content token ids of the frozen answer domain of the next-token logit at the answer position, with ties broken by the registered deterministic order; the softmax over the domain is recorded as a descriptive confidence only
- **Tokenizer eligibility rule:** every content surface string of the frozen answer domain, in the exact form emitted by the renderer, must map to exactly one token id under the pinned tokenizer of every required role, and the ids must be pairwise distinct; the current frozen domain is the ten mod-10 residues
- **Output validity rule:** no text is generated; exactly one logit vector is read at exactly one position, so the output-validity rate is identically 1 and is not a gate input
- **Applicable gates:** `I0`, `I1a`, `I2`, `I3`, `I4`, `I5`
- **Selectable status:** `selectable_preferred`
- **Why:** S2 removes the symbol-binding step entirely, so a failure cannot be attributed to label handling; it is preferred whenever the frozen answer domain is jointly single-token eligible for every required role

**Chat template policy by role**

- `R0`: not applicable; R0 is a deterministic software control and never receives a prompt
- `RC`: not applicable; RC is a deterministic software control and never receives a prompt
- `RT`: no chat template; raw completion surface
- `RL`: no chat template; raw completion surface
- `RI`: no chat template; raw completion surface
- `RP`: deferred to OD2; the RP canonical qualification wrapper is not settled and must be frozen before P3-Q and I4

**Transformations that are `not_applicable` to S2**

- `position_permutation`: S2 renders no option list, so there is no physical position for the correct content to occupy and the transformation has no referent
- `label_symbol_permutation`: S2 displays no label symbols, so there is nothing to permute and the transformation has no referent
- `label_set_replacement`: S2 displays no label alphabet, so there is no alphabet to replace

These are `not_applicable`. They are not passes, not zero effects and
not inputs to admissibility.

**Projected operation counts if a later authority permits execution**

- `forward_passes_per_item`: 1
- `generated_tokens_per_item`: 0
- `scored_positions_per_item`: 1
- `logit_reads_per_item`: 1

**Known confounds**

- a content-token frequency prior over the answer domain
- the answer cue wording can bias the first emitted token

**Disqualifying failures**

- any content surface string of the frozen answer domain that is not single-token under a required role
- duplicate content token ids

> Because S2 shows no options and no labels, three of the five calibration transformations are not applicable to it. Under v0.1 those three were scored as passes; under v0.2 they are recorded as not_applicable and contribute nothing.

### S3 - content_sequence_likelihood

- **Family:** length-normalised sequence log-likelihood over candidate answer strings
- **Role in panel:** conditional candidate; currently an integrity check on S2 rather than an independent surface
- **Prompt and rendering contract:** Identical stem, instruction and answer cue to S2. The difference is entirely in scoring: each candidate answer string is scored as a sequence rather than as a single token.
- **Options visible:** `false`
- **Labels visible:** `false`
- **Scoring formula:** argmax over candidate answer strings of the length-normalised sum of token log-probabilities of the candidate continuation, with the normalisation constant, the boundary-token rule and the tie-break order all registered in advance
- **Tokenizer eligibility rule:** candidate answer strings need not be single-token, which is precisely the case S3 exists to cover; but the boundary-token rule must be registered before any scoring, because where the candidate is deemed to start and stop determines the score
- **Output validity rule:** no free text is generated; the candidate set is closed, so an invalid output is impossible and the validity rate is identically 1
- **Applicable gates:** `I0`, `I1a`, `I2`, `I3`, `I4`, `I5`
- **Selectable status:** `conditionally_selectable`
- **Why:** For a single-token answer domain the length-normalised sequence score of a one-token candidate is a monotone function of that token's log probability, so S3's argmax is identical to S2's by construction. S3 is therefore not an independent surface under the current frozen domain. It becomes selectable only when a later authority introduces a multi-token answer domain, a dedicated multi-token stratum, a registered boundary-token rule and a length-confound gate.

**Chat template policy by role**

- `R0`: not applicable; R0 is a deterministic software control and never receives a prompt
- `RC`: not applicable; RC is a deterministic software control and never receives a prompt
- `RT`: no chat template; raw completion surface
- `RL`: no chat template; raw completion surface
- `RI`: no chat template; raw completion surface
- `RP`: deferred to OD2; the RP canonical qualification wrapper is not settled and must be frozen before P3-Q and I4

**Transformations that are `not_applicable` to S3**

- `position_permutation`: S3 renders no option list
- `label_symbol_permutation`: S3 displays no label symbols
- `label_set_replacement`: S3 displays no label alphabet

These are `not_applicable`. They are not passes, not zero effects and
not inputs to admissibility.

**Projected operation counts if a later authority permits execution**

- `forward_passes_per_item`: 1
- `generated_tokens_per_item`: 0
- `scored_positions_per_item`: 1
- `note`: under the current single-token domain S3 reuses the S2 forward pass and its agreement with S2 is recorded as an integrity check; it does not add four separate scorings and must not be budgeted as if it did

**Known confounds**

- length confound: longer candidate strings are penalised or rewarded depending on the normalisation constant
- boundary-token ambiguity: leading-space and end-of-string handling can change the ranking

**Disqualifying failures**

- disagreement with S2 on a single-token domain, which would indicate a scoring implementation defect rather than a model property
- any use of S3 as an independent surface before a multi-token domain, a dedicated stratum, a boundary-token rule and a length-confound gate all exist

> S3's current job is to catch scorer defects, not to compete.

### S4 - free_generation_with_parser

- **Family:** constrained free generation followed by a deterministic parser
- **Role in panel:** diagnostic only; never selectable
- **Prompt and rendering contract:** Question stem, option list, and an instruction permitting a short free response. Each role's native chat template is applied where one exists, and its absence is recorded explicitly where one does not.
- **Options visible:** `true`
- **Labels visible:** `true`
- **Scoring formula:** the model generates at most a registered maximum number of tokens under greedy decoding; a deterministic, version-pinned parser maps the completion to a member of the answer domain or to the explicit value unparseable
- **Tokenizer eligibility rule:** no single-token constraint applies, because S4 generates text; the tokenizer is still pinned and recorded
- **Output validity rule:** an output is valid only if the pinned parser maps it to a member of the answer domain; unparseable is a first-class recorded outcome and is never silently dropped, never imputed and never treated as incorrect without being reported separately
- **Applicable gates:** `I0`, `I1a`, `I1b`, `I2`, `I3`, `I4`, `I5`
- **Selectable status:** `never_selectable`
- **Why:** S4 reintroduces exactly the parser dependence that motivated this study, so allowing it to be selected would make the study's own instrument the thing under suspicion. It is retained because its unparseable rate is the most direct diagnostic of whether a surface is legible to the model at all. It is never selectable under any outcome, it never enters any admissibility comparison, and its results carry no selection authority.

**Chat template policy by role**

- `R0`: not applicable; deterministic software control
- `RC`: not applicable; deterministic software control
- `RT`: each role's native chat template is applied, or its absence is recorded explicitly; no cross-role byte parity is claimed
- `RL`: each role's native chat template is applied, or its absence is recorded explicitly; no cross-role byte parity is claimed
- `RI`: each role's native chat template is applied, or its absence is recorded explicitly; no cross-role byte parity is claimed
- `RP`: deferred to OD2

**Transformations that are `not_applicable` to S4:** none; every
calibration transformation has a referent for this profile.

**Projected operation counts if a later authority permits execution**

- `forward_passes_per_item`: registered maximum generated tokens
- `generated_tokens_per_item`: greater than zero and bounded by the registered maximum
- `scored_positions_per_item`: 0

**Known confounds**

- parser version dependence, which is the confound the study exists to avoid taking on faith
- chat-template differences across roles, which are not byte-comparable

**Disqualifying failures**

- none that would change its status, because its status is already never_selectable; a high unparseable rate is a finding, not a disqualification

> S4 is the only profile that generates text. Its per-item cost is therefore not comparable to S1, S2 or S3.

## Admissibility order

A pre-registered, fail-closed admissibility order replaces the data-dependent ranking used in draft-v0.1. The order is fixed here, before any data exists, so that no outcome can influence which surface is preferred. Data can only remove candidates from the order; it can never reorder them.

- **Eligibility rule:** An interface profile is eligible if and only if every gate that is applicable to it passes in every atomic cell. The applicable gate set is a property of the profile and is listed in the profile. I4 is part of eligibility.
- **Gates required for eligibility:** `I0`, `I1a`, `I1b`, `I2`, `I3`, `I4`
- **I1b applicability:** I1b is required for label-bearing profiles only. For content-only profiles it is not_applicable, which is neither a pass nor a waiver: the profile simply has no symbol-binding step to validate.
- **Never selectable:** `S4`
- **Data-dependent ranking:** `false`
- **The study stops only when** no selectable interface remains eligible. The failure of one interface eliminates that interface and nothing else.

| Rank | Interface | Condition | Why |
| --- | --- | --- | --- |
| 1 | S2 | the frozen answer domain is jointly single-token eligible for every required role | S2 has no symbol-binding step, so a pass cannot be an artefact of label handling and a failure cannot be blamed on it |
| 2 | S3 | a later authority has introduced a multi-token answer domain, a dedicated multi-token stratum, a registered boundary-token rule and a length-confound gate | S3 is the natural surface for a multi-token domain, but it is not independent of S2 for single-token contents |
| 3 | S1 | S1 is eligible | S1 preserves continuity with Study 2 but is the surface whose adequacy is in question, so it is admitted only when no higher-ranked surface is available |

- **No interface is selected in this round.**
- **Proposed disposition only:** `true`
- **Confirmation bank prohibition:** The admissibility order is evaluated on the development split only. The confirmation split is physically inaccessible until an interface has been proposed, the proposal has been sealed, and a separate authority has released it.

## Atomic evaluation cells and the pooling prohibition

- **Sampling unit:** the base item
- **Cluster rule:** Every permutation, label-set replacement and rendering variant derived from one base item belongs to the same correlated cluster as that base item, is assigned to the same split as that base item, and is never treated as an independent observation. Splitting a cluster across splits would leak the confirmation set.

An atomic evaluation cell is one combination of interface profile, checkpoint role, task stratum, operation family, depth, rendering, label or position condition, and split. A gate passes only if it passes in every atomic cell to which it is applicable.

**Cell factors**

- interface profile
- checkpoint role
- task stratum
- operation family
- depth
- rendering
- label or position condition
- split

**Pooling as a rescue is prohibited**

- **pooling K1 with K2** - K1 asks whether the model binds content to a displayed symbol; K2 asks whether it can echo trivially recoverable content at all. A high K2 rate can carry a failed K1 across a threshold, which would let the study report binding it never demonstrated.
- **pooling across primitive operation families** - a family the model handles well can mask a family it cannot handle, so the headroom gate would stop testing headroom
- **pooling K4 depth 2 with depth 3** - depth is the compositional variable of interest; averaging over it destroys the construct
- **pooling across checkpoint roles** - the roles are the contrast the later study depends on
- **pooling across interface profiles** - the interfaces are the object of comparison
- **pooling across renderings** - rendering sensitivity is precisely what K6 measures

Pooled summaries may be reported for readability. They carry no gate authority, may never be substituted for a failed cell, and must be labelled descriptive wherever they appear.

## Counterbalancing

**The defect being corrected.** draft-v0.1 used four cyclic option orders. Under cyclic rotation the physical position of the correct content and the identity of the displayed symbol move together, so the design cannot attribute an effect to one rather than the other. draft-v0.1 also used the label alphabet 1/2/3/4 while the frozen answer domain is the mod-10 residues, so a displayed label could be indistinguishable from a valid answer.

**The requirement.** Counterbalancing must use a deterministic orthogonal design, or an explicitly justified balanced design, that separates three factors: the physical position of the correct content, the identity of the displayed symbol at that position, and the label alphabet in use.

**Factors that must be separated**

- physical position of the correct content
- identity of the displayed symbol carrying the correct content
- label alphabet in use

**Construction algorithm** (published, not merely described; randomness: none; the construction is a deterministic function of the registered base-item index and draws no seed)

1. Enumerate the four physical positions 0, 1, 2, 3.

2. Enumerate the four displayed symbols of the label alphabet in their registered order.

3. Form the 4 x 4 Latin square L[i][j] = (i + j) mod 4, whose rows index the position of the correct content and whose columns index the cyclic offset applied to the symbol assignment.

4. Cross the position factor with the symbol-assignment factor by taking, for each base item, the pair (p, s) where p is the physical position of the correct content and s is the index of the symbol displayed at that position. Because p and s are enumerated independently, every one of the sixteen (p, s) pairs occurs, so position and symbol identity are orthogonal rather than tied.

5. Assign the sixteen pairs to base items by the deterministic rule (p, s) = (k mod 4, (k div 4) mod 4) where k is the registered base-item index; this is a fixed function of the index and uses no random draw.

6. Cross the resulting (p, s) design with the label-alphabet factor so that each alphabet is balanced across positions and symbols.

7. Emit, for every produced variant, the tuple (base item id, position of correct content, displayed symbol at that position, label alphabet id, rendering id) as the recorded condition.

Verification: the construction is checked by the committed design test, which asserts that position and symbol identity are orthogonal over a complete block and that no label symbol collides with the answer domain

**Label alphabets**

- **Requirement:** every label alphabet must be disjoint from the answer domain surface forms
- **Answer domain:** the mod-10 residues 0 through 9 in their registered surface form
- **Forbidden:** `1/2/3/4` - collides with the mod-10 answer domain, so a displayed label cannot be distinguished from a valid answer
- **Forbidden:** `0/1/2/3` - same collision
- **Permitted example:** `A/B/C/D` - disjoint from the mod-10 answer domain
- **Permitted example:** `W/X/Y/Z` - disjoint from the mod-10 answer domain, and disjoint from the first alphabet, so label-set replacement is a real manipulation
- **Label-set replacement:** label-set replacement is crossed and balanced with position, so an effect of changing the alphabet cannot be confounded with an effect of moving the content

**K6 renderings** - exactly 3, one factor at a time, answer cue held constant across all three renderings

- `R-base` varies nothing: the registered baseline rendering
- `R-sep` varies the option separator only: identical to R-base except for the separator string between a label and its option content
- `R-instr` varies the instruction wording only: identical to R-base except for the wording of the instruction sentence; the answer cue is byte-identical to R-base

## Task strata

| Stratum | Name | Uses a model | Gate role |
| --- | --- | --- | --- |
| K0 | deterministic_software_fixtures | `false` | sole input to gate I0; coverage must include every scorer, every profile, every not_applicable branch, every tie path and every invalid-output path |
| K1 | explicit_answer_binding | `true` | sole input to gate I1b, which is applicable to label-bearing profiles only |
| K2 | identity_and_copy_depth0 | `true` | sole input to gate I1a |
| K3 | depth1_primitives | `true` | sole input to gate I2, evaluated per primitive operation family with no pooling across families |
| K4 | depth2_depth3_compositions | `true` | sole input to gate I4, evaluated per operation family and per depth |
| K5 | position_and_permutation_variants | `true` | input to gate I3, applicable to label-bearing profiles only for the position, label-symbol and label-set transformations |
| K6 | rendering_variants | `true` | input to gate I3 for the separator and instruction-wording transformations, which are applicable to every profile |

## Checkpoint and control roles

| Role | Name | Is a model | Identity |
| --- | --- | --- | --- |
| R0 | deterministic_non_model_oracle | `false` | the harness itself, executed on K0 fixtures |
| RC | explicit_answer_binding_condition | `false` | a condition, not a checkpoint: the K1 stratum applied to whichever model role is under test |
| RT | target | `true` | deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B |
| RL | lineage_base | `true` | Qwen/Qwen2.5-Math-1.5B |
| RI | instruction_control | `true` | Qwen/Qwen2.5-Math-1.5B-Instruct |
| RP | positive_capability_reference | `true` | UNSELECTED - operator review item |

## Positive reference

- **Selection status:** NOT SELECTED; candidate dossier only
- **Blocking decision:** `OD2`
- **Dossier:** `studies/study3/references/positive_reference_dossier.md`

**The circularity being corrected.** draft-v0.1 permitted the positive reference to be prequalified through a candidate interface. If a candidate interface is what demonstrates that the reference is capable, the interface's adequacy rests on an argument that presupposes it.

**The requirement.** the positive reference must be prequalified through a separate canonical interface that is not S1, S2, S3 or S4, on items disjoint from those used for gate I4

- **Canonical interface status:** not defined in this round; it must be registered before P3-Q, and it is not a member of the candidate panel
- **Item disjointness:** the P3-Q prequalification items and the K4 I4 items must be disjoint by construction

## Gate hierarchy

| Gate | Name | Part of eligibility | Authorizes mechanistic execution | Fail closed |
| --- | --- | --- | --- | --- |
| I0 | instrument integrity | `true` | `false` | `true` |
| I1a | trivial content recovery and output validity | `true` | `false` | `true` |
| I1b | explicit content-to-symbol binding | `true` | `false` | `true` |
| I2 | primitive headroom | `true` | `false` | `true` |
| I3 | calibration robustness | `true` | `false` | `true` |
| I4 | positive reference adequacy | `true` | `false` | `true` |
| I5 | one-shot confirmation | `false` | `false` | `true` |

### Gate I0 - instrument integrity

**Question.** Does the rendering and scoring software do exactly what it claims to do, on inputs whose correct answer is fixed by construction and requires no model?

- **Inputs:** stratum K0 deterministic software fixtures
- **Model roles:** `R0`, `RC`
- **Applicable profiles:** S1, S2, S3, S4
- **Part of eligibility:** `true`
- **Evaluated per:** interface profile, renderer branch, scorer branch
- **Pooling across cells:** `prohibited`
- **Threshold logic:** 100 percent of fixtures must pass. There is no statistical threshold, because a fixture failure is a software defect, not a sampling outcome.
- **Coverage requirement:** The fixture set must cover every scorer, every interface profile, every not_applicable branch, every tie-break path and every invalid output path. Coverage is asserted by the committed design test; a scorer or branch with no fixture is itself an I0 failure.
- **What passes:** every fixture renders and scores exactly as declared
- **What fails:** any fixture mismatch, or any uncovered scorer, profile, not_applicable branch, tie path or invalid-output path
- **`not_applicable` semantics:** none; I0 applies to every profile
- **Merely descriptive:** none
- **Legal next state on pass:** evaluate I1a
- **Legal next state on fail:** STOP; fix the instrument and restart the gate sequence from I0
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`

### Gate I1a - trivial content recovery and output validity

**Question.** Can the checkpoint recover an answer that is trivially present in the prompt, and does it emit a structurally valid output while doing so?

- **Inputs:** stratum K2 trivial content recovery items
- **Model roles:** `RT`, `RL`, `RI`
- **Applicable profiles:** S1, S2, S3, S4
- **Part of eligibility:** `true`
- **Evaluated per:** interface profile, checkpoint role, split
- **Pooling across cells:** `prohibited`
- **Threshold logic:** exact one-sided binomial test of H0: p <= 0.90 at alpha = 0.005; at n = 192 the acceptance count is 184, that is a rate of 0.9583, with exact null tail 2.362e-03
- **What passes:** the checkpoint recovers trivially present content at a rate exceeding the floor, and its outputs are valid
- **What fails:** the checkpoint cannot echo content that is already in the prompt, in which case nothing downstream is interpretable
- **`not_applicable` semantics:** none; I1a applies to every profile
- **Merely descriptive:** the softmax confidence at the answer position
- **Legal next state on pass:** evaluate I1b where applicable, otherwise I2
- **Legal next state on fail:** eliminate this interface profile for this role; if no selectable profile remains, STOP
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`

### Gate I1b - explicit content-to-symbol binding

**Question.** When a symbol stands for an answer, does the checkpoint bind the correct content to the correct displayed symbol, rather than following a symbol prior?

- **Inputs:** stratum K1 explicit binding items
- **Model roles:** `RT`, `RL`, `RI`
- **Applicable profiles:** S1, S4
- **Part of eligibility:** `true`
- **Evaluated per:** interface profile, checkpoint role, label or position condition, split
- **Pooling across cells:** `prohibited`
- **Threshold logic:** exact one-sided binomial test of H0: p <= 0.90 at alpha = 0.005; at n = 192 the acceptance count is 184, that is a rate of 0.9583
- **What passes:** the correct content is selected through its displayed symbol across the counterbalanced conditions
- **What fails:** the checkpoint tracks the symbol rather than the content, or tracks position rather than either
- **`not_applicable` semantics:** For content-only profiles S2 and S3 this gate is not_applicable. not_applicable is a third value. It is not a pass, it is not a zero effect, it is not evidence of robustness, and it may never be counted as a satisfied gate, averaged into any rate, or used as an input to admissibility. A gate whose transformation is not applicable to a profile is simply not evaluated for that profile, and the profile's eligibility rests on the gates that are applicable to it.
- **Merely descriptive:** the marginal frequency of each displayed symbol
- **Legal next state on pass:** evaluate I2
- **Legal next state on fail:** eliminate this interface profile for this role; if no selectable profile remains, STOP
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`

### Gate I2 - primitive headroom

**Question.** Does the checkpoint have measurable headroom on each single primitive operation family, so that a later compositional failure cannot be explained by inability to do the parts?

- **Inputs:** stratum K3 single primitive items
- **Model roles:** `RT`, `RL`, `RI`
- **Applicable profiles:** S1, S2, S3, S4
- **Part of eligibility:** `true`
- **Evaluated per:** interface profile, checkpoint role, operation family, split
- **Pooling across cells:** `prohibited`
- **Threshold logic:** exact one-sided binomial test of H0: p <= 0.50 at alpha = 0.005, evaluated separately in every operation family; at n = 192 the acceptance count is 115, that is a rate of 0.5990
- **What passes:** every primitive family independently clears the floor
- **What fails:** any single family falls below the floor, regardless of the pooled rate across families
- **`not_applicable` semantics:** none; I2 applies to every profile
- **Merely descriptive:** the pooled rate across families
- **Legal next state on pass:** evaluate I3
- **Legal next state on fail:** eliminate this interface profile for this role; if no selectable profile remains, STOP
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`

### Gate I3 - calibration robustness

**Question.** Does the checkpoint give the same answer to the same question when the presentation changes in ways that do not change the question?

- **Inputs:** stratum K5 counterbalanced presentations, stratum K6 one-factor renderings
- **Model roles:** `RT`, `RL`, `RI`
- **Applicable profiles:** S1, S2, S3, S4
- **Part of eligibility:** `true`
- **Evaluated per:** interface profile, checkpoint role, rendering, label or position condition, split
- **Pooling across cells:** `prohibited`
- **Threshold logic:** the primary item-level criterion and, where applicable, the selected-label uniformity criterion must both pass in every atomic cell; the secondary aggregate criterion is reported alongside and cannot rescue a failed primary
- **Primary criterion:** item-level content consistency - for each base item, the indicator that the answer is identical across every applicable transformed variant of that base item
  - test: exact one-sided binomial test on the per-base-item consistency indicator
  - why primary: aggregate equivalence can be satisfied while a large number of items flip in compensating directions, which is the failure mode this gate exists to exclude; an item-level indicator cannot be satisfied that way
  - floor status: provisional; the floor value is part of blocking decision OD6
- **Secondary criterion:** aggregate equivalence
  - method: Tango (1998) score-based procedure for the difference of paired proportions, applied as two one-sided tests
  - citation: Tango T. Equivalence test and confidence interval for the difference in proportions for the paired-sample design. Statistics in Medicine 1998;17(8):891-908. PMID 9595618.
  - implementation: `studies/study3/analysis/design_statistics.py`
  - decision form: intersection-union; equivalence is declared only when both one-sided nulls are rejected. A non-significant difference is never treated as equivalence.
  - margin status: unresolved; the committed derivation shows that n = 192 does not support a 0.05 margin at 0.90 power at any tested discordance rate, so the margin, the sample size, or both must change. This is blocking decision OD6.
  - verified before use:
    - reduces exactly to McNemar's statistic at a null difference of zero, which is the published special case
    - its closed-form constrained maximum-likelihood estimate agrees with direct numerical maximisation of the constrained likelihood
    - its exact type-I error, computed by enumerating the full joint distribution of the discordant counts, does not exceed its nominal one-sided level
- **Selected-label uniformity:** classified as `gate`, applies to label-bearing profiles only, `not_applicable` to S2, S3. this criterion is a gate for label-bearing profiles and is not_applicable elsewhere; it is never reclassified as diagnostic to avoid a failure
- **What passes:** the same question yields the same answer under presentation changes that do not change the question
- **What fails:** answers move with presentation
- **`not_applicable` semantics:** Position, label-symbol and label-set transformations are not_applicable to S2 and S3, which display neither options nor labels. not_applicable is a third value. It is not a pass, it is not a zero effect, it is not evidence of robustness, and it may never be counted as a satisfied gate, averaged into any rate, or used as an input to admissibility. A gate whose transformation is not applicable to a profile is simply not evaluated for that profile, and the profile's eligibility rests on the gates that are applicable to it.
- **Merely descriptive:** aggregate rate differences without the paired procedure, pooled consistency across cells
- **Legal next state on pass:** evaluate I4
- **Legal next state on fail:** eliminate this interface profile for this role; if no selectable profile remains, STOP
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`

### Gate I4 - positive reference adequacy

**Question.** Does an independently prequalified capable reference succeed through this interface, so that a target failure through the same interface can be attributed to the target rather than to the interface?

- **Inputs:** stratum K4 compositional items at depth 2 and depth 3
- **Model roles:** `RP`
- **Applicable profiles:** S1, S2, S3, S4
- **Part of eligibility:** `true`
- **Evaluated per:** interface profile, operation family, depth
- **Pooling across cells:** `prohibited`
- **Threshold logic:** exact one-sided binomial test of H0: p <= p_floor, evaluated separately in every operation family and at every depth
  - proposed competence floor `p_floor = 0.8` (proposal; the final value is blocking decision OD5)
  - the draft-v0.1 proposal of `p <= 0.25` at n = 128, acceptance count 49, rate 0.3828, is `REJECTED_BY_OPERATOR_REVIEW`: a chance-level null establishes only that the reference beats guessing; it is not a competence floor, and only a competence claim can license the inference that a capable model would have succeeded
- **Prequalification:** the positive reference must be prequalified through a separate canonical interface that is not S1, S2, S3 or S4, on items disjoint from those used for I4
  - why: if a candidate interface were used to establish that the reference is capable, the interface's adequacy would be established by an argument that presupposes it
  - stage: `P3-Q`, status: not executed; RP is not selected and P3-Q is not authorised
- **Consequence of failure:** this interface profile is eliminated, and only this interface profile. The study stops only if no selectable interface profile remains eligible. draft-v0.1 wrote this failure as a global study stop, and separately said a failing interface remained eligible; both statements are withdrawn.
- **What passes:** the prequalified reference clears the competence floor through this interface in every family and at every depth
- **What fails:** the reference does not clear the floor through this interface
- **`not_applicable` semantics:** none; I4 applies to every profile
- **Merely descriptive:** the reference's pooled rate across families and depths
- **Legal next state on pass:** the interface profile is eligible; evaluate the admissibility order
- **Legal next state on fail:** eliminate this interface profile; if no selectable profile remains, STOP
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`

### Gate I5 - one-shot confirmation

**Question.** Do the constructs that passed on the development split hold on a confirmation split that was never inspected?

- **Inputs:** the confirmation split of every gate-bearing stratum, including K4
- **Model roles:** `RT`, `RL`, `RI`, `RP`
- **Applicable profiles:** the single proposed interface profile only
- **Part of eligibility:** `false`
- **Evaluated per:** every gate-bearing construct
- **Pooling across cells:** `prohibited`
- **Threshold logic:** the same pre-registered thresholds as the development split, with no re-tuning of any kind
- **Coverage requirement:** I5 must cover every gate-bearing construct without exception. That explicitly includes I4 evaluated on the positive reference over the K4 stratum. draft-v0.1 omitted the positive-reference construct and the K4 stratum from confirmation; that omission is withdrawn.
- **Covered constructs:** `I0`, `I1a`, `I1b`, `I2`, `I3`, `I4`
- **Accessible before authority:** `false`
- **What passes:** every construct holds on data that was never inspected
- **What fails:** any construct fails to replicate
- **`not_applicable` semantics:** constructs that are not_applicable to the proposed profile are not evaluated and are recorded as not_applicable. not_applicable is a third value. It is not a pass, it is not a zero effect, it is not evidence of robustness, and it may never be counted as a satisfied gate, averaged into any rate, or used as an input to admissibility. A gate whose transformation is not applicable to a profile is simply not evaluated for that profile, and the profile's eligibility rests on the gates that are applicable to it.
- **Merely descriptive:** none
- **Legal next state on pass:** the interface is calibrated; a separate authority is still required before any mechanistic work
- **Legal next state on fail:** STOP; the confirmation split is spent and may not be reused
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`

## Gate truth table and legal stop states

Every gate is fail-closed. No gate authorises mechanistic execution.

| Gate | Eligibility | On pass | On fail | Authorizes mechanism |
| --- | --- | --- | --- | --- |
| I0 | `true` | evaluate I1a | STOP; fix the instrument and restart the gate sequence from I0 | `false` |
| I1a | `true` | evaluate I1b where applicable, otherwise I2 | eliminate this interface profile for this role; if no selectable profile remains, STOP | `false` |
| I1b | `true` | evaluate I2 | eliminate this interface profile for this role; if no selectable profile remains, STOP | `false` |
| I2 | `true` | evaluate I3 | eliminate this interface profile for this role; if no selectable profile remains, STOP | `false` |
| I3 | `true` | evaluate I4 | eliminate this interface profile for this role; if no selectable profile remains, STOP | `false` |
| I4 | `true` | the interface profile is eligible; evaluate the admissibility order | eliminate this interface profile; if no selectable profile remains, STOP | `false` |
| I5 | `false` | the interface is calibrated; a separate authority is still required before any mechanistic work | STOP; the confirmation split is spent and may not be reused | `false` |

**Legal stop states**

- STOP_INSTRUMENT_DEFECT after an I0 failure
- STOP_NO_SELECTABLE_INTERFACE_REMAINS after every selectable profile has been eliminated by I1a, I1b, I2, I3 or I4
- STOP_CONFIRMATION_FAILED after an I5 failure, with the confirmation split spent
- STOP_AWAITING_AUTHORITY, which is the current state

## Proposed statistics

- **Framework:** frequentist, pre-registered, exact where an exact test exists
- **Status of every number below:** proposed design parameters, not measurements
- **Derivation script:** `studies/study3/analysis/design_statistics.py`
- **Derivation tables:** `studies/study3/analysis/design_statistics_tables.json`
- **Reproducibility:** the script's --check mode recomputes every table and compares it value-for-value against the committed tables; the committed design test runs that check
- **Model free:** `true`
- **Study alpha:** `0.005`  **Target power:** `0.9`

### Multiplicity

Two structurally different multiplicity problems are kept apart. Within one interface profile, every gate and every atomic cell must pass; that conjunction is an intersection-union test, whose size is bounded by the level of its individual components, so no inflation correction is applied to the conjunction itself. Across interface profiles, by contrast, the study may proceed if ANY selectable profile qualifies; that is a union event and it does inflate the false-qualification rate, so it is Bonferroni-corrected by the number of selectable profiles.

- **Family A, within a profile** (`intersection_union_conjunctive`): members I1a, I1b, I2, I3_primary, I3_uniformity, I4, per-component alpha `0.005`, correction: none required; IU size is bounded by the component level
- **Family B, across profiles** (`union_selection`): members S1, S2, S3, study alpha `0.005`, per-profile alpha `0.001666666667`, correction: Bonferroni over 3 selectable profiles
- **Excluded from selection:** S4 is never selectable and never enters selection

### Retained exact binomial gates

| Gate | Null | n | alpha | Acceptance count | Rate | Exact null tail |
| --- | --- | --- | --- | --- | --- | --- |
| I1a | p <= 0.9 | 192 | 0.005 | 184 | 0.9583 | 2.362e-03 |
| I1a | p <= 0.9 | 128 | 0.005 | 124 | 0.9688 | 3.072e-03 |
| I1b | p <= 0.9 | 192 | 0.005 | 184 | 0.9583 | 2.362e-03 |
| I1b | p <= 0.9 | 128 | 0.005 | 124 | 0.9688 | 3.072e-03 |
| I2 | p <= 0.5 | 192 | 0.005 | 115 | 0.5990 | 3.709e-03 |
| I2 | p <= 0.5 | 128 | 0.005 | 80 | 0.6250 | 2.963e-03 |

### Gate I4 competence floor

The draft-v0.1 proposal is `REJECTED_BY_OPERATOR_REVIEW`. a chance-level null does not establish a positive-capability floor; clearing 0.25 shows only that the reference is above guessing, which cannot license the inference that the interface is adequate for a capable model It tested `p <= 0.25` at n = 128, giving an acceptance count of 49, a rate of 0.3828.

| n | alpha | Acceptance count | Rate | Power at 0.95 |
| --- | --- | --- | --- | --- |
| 128 | 0.005000 | 114 | 0.8906 | 0.9981 |
| 128 | 0.001667 | 116 | 0.9062 | 0.9879 |
| 128 | 0.001000 | 116 | 0.9062 | 0.9879 |
| 192 | 0.005000 | 168 | 0.8750 | 1.0000 |
| 192 | 0.001667 | 170 | 0.8854 | 0.9999 |
| 192 | 0.001000 | 171 | 0.8906 | 0.9997 |
| 256 | 0.005000 | 222 | 0.8672 | 1.0000 |
| 256 | 0.001667 | 224 | 0.8750 | 1.0000 |
| 256 | 0.001000 | 225 | 0.8789 | 1.0000 |
| 384 | 0.005000 | 328 | 0.8542 | 1.0000 |
| 384 | 0.001667 | 330 | 0.8594 | 1.0000 |
| 384 | 0.001000 | 331 | 0.8620 | 1.0000 |

### Gate I3 primary criterion: item-level content consistency

| Null | n | alpha | Acceptance count | Rate | Power at 0.98 |
| --- | --- | --- | --- | --- | --- |
| p <= 0.9 | 128 | 0.005 | 124 | 0.9688 | 0.8850 |
| p <= 0.9 | 192 | 0.005 | 184 | 0.9583 | 0.9841 |
| p <= 0.9 | 256 | 0.005 | 243 | 0.9492 | 0.9992 |
| p <= 0.9 | 384 | 0.005 | 361 | 0.9401 | 1.0000 |
| p <= 0.95 | 128 | 0.005 | 128 | 1.0000 | 0.0753 |
| p <= 0.95 | 192 | 0.005 | 190 | 0.9896 | 0.2596 |
| p <= 0.95 | 256 | 0.005 | 252 | 0.9844 | 0.4178 |
| p <= 0.95 | 384 | 0.005 | 376 | 0.9792 | 0.6376 |

### Gate I3 secondary criterion: paired equivalence sensitivity

Method: Tango (1998) score-based procedure for the difference of paired proportions, applied as two one-sided tests. Verified before use:

- reduces exactly to McNemar's statistic at a null difference of zero, which is the published special case
- its closed-form constrained maximum-likelihood estimate agrees with direct numerical maximisation of the constrained likelihood
- its exact type-I error, computed by enumerating the full joint distribution of the discordant counts, does not exceed its nominal one-sided level

Verification results: McNemar reduction maximum absolute deviation `0`; constrained MLE maximum absolute deviation `3.39e-09`; exact type-I error at the null boundary `0.0151` (n = 96), `0.0226` (n = 128), `0.0237` (n = 192), all at or below the nominal one-sided level 0.025.

| Margin | n | Discordance | Exact power | Exact type-I at margin | Meets 0.90 power |
| --- | --- | --- | --- | --- | --- |
| 0.05 | 128 | 0.05 | 0.1733 | 0.0109 | `false` |
| 0.05 | 128 | 0.10 | 0.0059 | 0.0028 | `false` |
| 0.05 | 128 | 0.20 | 0.0000 | 0.0000 | `false` |
| 0.05 | 128 | 0.30 | 0.0000 | 0.0000 | `false` |
| 0.05 | 192 | 0.05 | 0.5412 | 0.0122 | `false` |
| 0.05 | 192 | 0.10 | 0.1149 | 0.0158 | `false` |
| 0.05 | 192 | 0.20 | 0.0000 | 0.0000 | `false` |
| 0.05 | 192 | 0.30 | 0.0000 | 0.0000 | `false` |
| 0.05 | 256 | 0.05 | 0.7764 | 0.0107 | `false` |
| 0.05 | 256 | 0.10 | 0.3582 | 0.0223 | `false` |
| 0.05 | 256 | 0.20 | 0.0037 | 0.0011 | `false` |
| 0.05 | 256 | 0.30 | 0.0000 | 0.0000 | `false` |
| 0.05 | 384 | 0.05 | 0.9605 | 0.0146 | `true` |
| 0.05 | 384 | 0.10 | 0.6924 | 0.0225 | `false` |
| 0.05 | 384 | 0.20 | 0.1671 | 0.0174 | `false` |
| 0.05 | 384 | 0.30 | 0.0005 | 0.0001 | `false` |
| 0.10 | 128 | 0.05 | 0.9733 | n/a | `true` |
| 0.10 | 128 | 0.10 | 0.8114 | 0.0235 | `false` |
| 0.10 | 128 | 0.20 | 0.3797 | 0.0226 | `false` |
| 0.10 | 128 | 0.30 | 0.0785 | 0.0118 | `false` |
| 0.10 | 192 | 0.05 | 0.9990 | n/a | `true` |
| 0.10 | 192 | 0.10 | 0.9634 | 0.0255 | `true` |
| 0.10 | 192 | 0.20 | 0.7132 | 0.0235 | `false` |
| 0.10 | 192 | 0.30 | 0.4173 | 0.0237 | `false` |
| 0.10 | 256 | 0.05 | 1.0000 | n/a | `true` |
| 0.10 | 256 | 0.10 | 0.9949 | 0.0236 | `true` |
| 0.10 | 256 | 0.20 | 0.8768 | 0.0239 | `false` |
| 0.10 | 256 | 0.30 | 0.6533 | 0.0246 | `false` |
| 0.10 | 384 | 0.05 | 1.0000 | n/a | `true` |
| 0.10 | 384 | 0.10 | 0.9999 | 0.0175 | `true` |
| 0.10 | 384 | 0.20 | 0.9814 | 0.0243 | `true` |
| 0.10 | 384 | 0.30 | 0.8907 | 0.0247 | `false` |

**Feasibility verdict.** n = 192 does NOT support the v0.1 aggregate equivalence margin of 0.05 at 0.90 power under any tested discordance rate. The margin, the sample size, or both must be revised by the independent methods review. This is why OD5 and OD6 remain blocking.

- Claim under review: v0.1 asserted an aggregate equivalence margin of 0.05 without any paired power analysis
- Margin 0.05 supported at any tested discordance: `false`
- Discordance rates at which margin 0.10 reaches 0.90 power: 0.05, 0.1

**Sample sizes.** n = 192 is provisional for I1a, I1b and I2 only. It is not an I3 justification: the committed derivation shows n = 192 cannot support a 0.05 aggregate equivalence margin at 0.90 power at any of the discordance rates 0.05, 0.10, 0.20 or 0.30 Confirmation size: awaits the reviewed power analysis. I3 size: awaits the reviewed power analysis. Blocking decision: `OD6`.

### Label-selection uniformity bands

| n | Labels | Expected per label | Bonferroni alpha | Acceptance band |
| --- | --- | --- | --- | --- |
| 192 | 4 | 48.0 | 0.001250 | 30 to 68 |
| 384 | 4 | 96.0 | 0.001250 | 69 to 124 |
| 768 | 4 | 192.0 | 0.001250 | 154 to 231 |

These bands apply to label-bearing profiles only. For `S2` and `S3` the construct is `not_applicable`.

## Operations performed in this round

every key in performed_this_round must be exactly zero; any nonzero value, and any key added without a new authority, is a fail-closed violation

| Counter | Value |
| --- | --- |
| `model_downloads` | `0` |
| `model_weight_loads` | `0` |
| `tokenizer_constructions` | `0` |
| `forward_passes` | `0` |
| `generations` | `0` |
| `activation_extractions` | `0` |
| `lens_operations` | `0` |
| `probe_operations` | `0` |
| `patching_operations` | `0` |
| `ablation_operations` | `0` |
| `gpu_jobs` | `0` |
| `provider_calls` | `0` |
| `bank_rows_generated` | `0` |
| `seeds_drawn` | `0` |
| `evidence_rows_created` | `0` |
| `phase_1_0d_operations` | `0` |
| `rq2_s4_operations` | `0` |
| `interfaces_selected` | `0` |
| `positive_references_selected` | `0` |
| `confirmation_split_accesses` | `0` |
| `study1_files_modified` | `0` |
| `study2_files_modified` | `0` |

**All counters zero:** `true`

**Prohibited without a new authority**

- any model download, weight load or tokenizer construction
- any forward pass or generation
- any activation extraction or probe
- any patching, ablation or lens operation
- any GPU job
- any bank generation or seed draw
- any evidence-ledger row
- any Phase 1.0D or RQ2/S4 operation
- any Study 2 state change

## Claim ceiling

- **Maximum pass claim:** The named interface met the registered adequacy and robustness gates for the named tasks and the named checkpoint roles, under the registered conditions, on a sealed held-out bank.
- **Maximum fail claim:** No candidate interface met the registered gates under the registered conditions. This is a statement about the candidate panel and the registered conditions, not about model capability.

**Prohibited claims**

- any claim that the model does or does not reason
- any claim about internalized chain of thought
- any claim that distillation did or did not transfer a causal mechanism
- any claim about the existence of a task-defined intermediate variable
- any claim for or against J-space or J-lens validity
- any claim that Study 2 Gate A should or should not have passed
- any claim of model incapability derived from an interface failure
- any claim that a passing interface validates a later experimental design
- that a not_applicable transformation demonstrates robustness
- that a pooled summary satisfies a gate that failed in an atomic cell
- that parsing caused the Study 1 E0 eligibility collapse

**What a pass does not permit**

- reopening Study 2
- authorizing Study 4 or Study 2 v2
- behavioral confirmation
- activation extraction
- patching
- probes
- ablations
- lens work

## Study 1 and Study 2

Study 1's frozen raw-completion, no-chat-template, single-token E0 surface yielded too few behaviorally eligible items to populate confirmation. Parser-v2 separately failed its locked gate, while parser-v3 remained nonauthoritative. These facts motivate prospective interface validation but do not establish that parsing caused E0's eligibility collapse.

_motivation only; this does not establish that parsing caused the collapse_

Study 2 remains closed and unchanged. Its post-hoc response-pattern diagnostic remains zero-authority motivation only.

_closed and unchanged; zero-authority motivation only_

## Unresolved operator decisions

| Decision | Status | Blocking | Disposition |
| --- | --- | --- | --- |
| OD1 | `resolved` | `false` | retain RT, RL and RI. All three are required for the later distillation, lineage and instruction contrast, and each gate is evaluated per role. |
| OD2 | `unresolved` | `true` | candidate dossier only. No positive reference is selected. The RP canonical qualification wrapper and the RP-specific I4 wrapper must be frozen before P3-Q and I4. |
| OD3 | `resolved` | `false` | retain S4 only as a non-selectable diagnostic. It never enters admissibility and can never be selected. |
| OD4 | `resolved` | `false` | exactly three one-factor renderings: baseline, separator-only and instruction-wording-only. The answer cue is held constant across all three. |
| OD5 | `unresolved` | `true` | the I1 and I2 proposals may remain provisional. The I3 method and margins and the I4 competence floor require independent review. The chance-floor I4 proposal from draft-v0.1 is rejected. |
| OD6 | `unresolved` | `true` | n = 192 may remain a provisional I1 and I2 value. It is not an I3 justification. Confirmation and I3 sizes await the reviewed power analysis. |
| OD7 | `resolved` | `false` | yes. A bounded independent review of the statistics and the gate logic is mandatory before freeze and before any bank construction or seed draw. |
| OD8 | `resolved_in_part` | `false` | no chat template for RT, RL or RI on S1, S2 or S3. S4 uses each role's native template or explicitly records its absence. The RP canonical qualification wrapper and the RP-specific I4 wrapper remain part of OD2 and must be frozen before P3-Q and I4. No cross-role byte parity is claimed where native wrappers differ. |

**Blocking decisions:** `OD2`, `OD5`, `OD6`

## Required next action

bounded independent methods review of the statistical and gate packet

This draft is **not** frozen, **not** authorized for execution, and carries **no** authority for bank construction, seed drawing, tokenizer construction, model download, model loading, forward passes, generation, activation extraction, probing, patching, ablation, lens work or any Gate A or Stage B-D operation.
