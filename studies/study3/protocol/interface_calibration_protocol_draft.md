# Study 3 - interface adequacy and label-binding calibration

**State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW`

**Draft version:** draft-v0.5

**Frozen:** `false`  **Execution authorized:** `false`  **Review state:** `awaiting_fourth_independent_methods_review`

**Successor authority:** `none`

**This document does not declare its own protocol correct.** Every repair recorded here is
`PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. The drafting party of draft-v0.2 found its own design defensible and an independent
reviewer then rejected it with six blocking findings; that outcome is the reason this
document may not adjudicate itself.


## How to read this pair of documents

The JSON document interface_calibration_protocol_draft.json is the authoritative record of this design. The Markdown document interface_calibration_protocol_draft.md is a companion rendering of it. Where the two disagree, the JSON governs and the disagreement is a defect. Agreement on every decision-bearing marker is enforced by the committed test at tests/test_study3_design.py. No claim is made that the two documents are generated from a single source of record, because no such generator is committed; what is committed, and therefore what is checked, is the agreement itself.

draft-v0.2 is an amendment produced in response to an operator review that found ten design defects in draft-v0.1 and refused freeze. Nothing here is frozen, nothing here is authorised for execution, and no scientific measurement of any kind was performed to produce it.

## What draft-v0.5 is

draft-v0.5 is a bounded operator amendment produced in response to the **third** bounded
independent methods review, which returned `STUDY3_V0_4_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`
against commit `79bcc20244ab55045ba1c5d778d829d4caac3dd3` with one BLOCKING, three MAJOR and six
MINOR structured findings. All three independent reviews remain valid rejections and none was
edited. The determination on this amendment belongs to a **fourth independent methods review**,
conducted in a fresh session by a party that did not draft draft-v0.5.

### `S3MR3-001`: `K6-SEP` is not applicable to the option-less profiles

`K6-SEP` varies the separator between a **displayed option label** and its **displayed option
content**. `S1` and `S4` render labelled option lists, so the factor has a referent for them. `S2`
and `S3` render neither an option label nor an option content, so the factor has no referent and the
two members of the pair would be byte-identical. Under the registered deterministic scorer an
identical prompt yields an identical score, so such a cell would be a self-comparison whose estimand
is a plain marginal accuracy rather than a joint-correctness level over a registered presentation
pair.

`K6-SEP` is therefore recorded `not_applicable` for `S2` and `S3` in every location.
`not_applicable` is a third value: it is not a pass, not a zero effect, not robustness evidence, not
a gate-bearing cell and not a denominator member. No profile-specific replacement separator is
invented, and no `R-sep` duplicate of `R-base` is rendered for an option-less profile.

**`S2` and `S3` each carry exactly ONE genuine `I3` contrast: `K6-INSTR`.** Their per-profile `I3`
claim ceiling states joint robust correctness for that single registered pair only, subject to
`S3`'s separately registered conditional status. `S1` retains its seven `K5` pairs plus both `K6`
pairs, and `S4` retains the same contrast availability for diagnostic description only.

Applicability is now registered **per contrast ID**, because family-level registration cannot
express this distinction.

### The re-derived census, and the numbers that did not change

| profile | `I1a` | `I1b` | `I2` | `K5` | `K6` | `I4` | total | applicable `I3` contrasts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `S1` | 3 | 3 | 6 | 21 | 6 | 4 | **43** | 9 |
| `S2` | 3 | 0 | 6 | 0 | 3 | 4 | **16** | 1 |
| `S3` | 3 | 0 | 6 | 0 | 3 | 4 | **16** | 1 |
| `S4` | 3 | 3 | 6 | 21 | 6 | 0 | **39** | 9 |

`S2` and `S3` fall from 19 gate-bearing cells to 16. `m_max` is the maximum total over the
**selectable** profiles, so it is still `S1`'s **43**: it is unchanged because the profile that
attains it is unchanged, not because the value was preserved for continuity. By derivation and not
by transcription, the per-cell false-negative budget is `19/17200`, the per-cell power target is
`17181/17200`, the profile stage power floor is `381/400`, the study end-to-end power floor is
`9/10`, the development component alpha is `1/600`, the confirmation component alpha is `1/200`, and
the development sizes and pass counts remain `413`/`389`, `214`/`129` and `448`/`383`, with
confirmation pass counts `388`, `127` and `381`.

### `S3MR3-002`: confirmation applicability is component level

The derivation table is regenerated only from the amended normative inputs and now expresses
applicability **per component**. `S4` appears in no confirmation applicability field. `I1b` and `K5`
confirmation applicability is restricted to `S1`; `K6-SEP` confirmation applicability excludes `S2`
and `S3`; `K6-INSTR` confirmation applicability is `S1`, `S2` and `S3`. No row can imply that a
never-selectable or not-applicable profile reaches confirmation.

### `S3MR3-007`: the power target is locally non-monotone in `n`

The registered sizes are the smallest unrestricted positive integers meeting the per-cell target.
The target is **not** monotone above them: within the registered disclosure window it fails again at
`421`-`425` above `n = 413`, at `215`, `216` and `218` above `n = 214`, and at `450`-`453` and `459`
above `n = 448`. Execution must use the **exact** registered cell size; the registered size never
means "at least `n`". The registered minimum is retained rather than replaced by an
eventual-monotonicity threshold, because fresh arithmetic confirms the design is executable at exact
`n`.

### `S3MR3-009`: what the union bound actually establishes

The end-to-end conclusion is restated over **an adequate profile**: the three unioned terms
establish that an adequate profile is qualified, selected and confirmed. Where several selectable
profiles are adequate, the frozen priority order returns the highest-priority adequate profile. No
claim of recovering an externally predesignated profile is made.

### `S3MR3-010`: the deterministic rendering surface is registered

`studies/study3/protocol/interface_calibration_rendering_registry_v0_5.json` and its schema are
**binding normative inputs, not illustrative examples**. They fix the encoding, newline and
normalization policy; one exact question-stem template per gate-bearing generator branch;
placeholder, interpolation and escaping rules; the option-line grammar and ordering; the label
alphabets and the exact separator literals `": "` for `R-base` and `" = "` for `R-sep`; two exact,
semantically co-referential instruction strings per applicable profile for `K6-INSTR`; the answer
cue and the whitespace convention of every scored candidate surface; the deterministic tie-break
order; the `S4` pre-wrapper message boundary; the full `(profile, rendering, contrast)` applicability
table; and a cryptographic identity for the registry and every normative template asset.

Tokenizer distinctness is **not** tested in this round, because no checkpoint or tokenizer may be
accessed. A future fail-closed pre-bank rule is registered instead: once checkpoints and tokenizers
are separately authorised and pinned, every gate-bearing pair must produce distinct token-ID
sequences for every role to which the cell applies, and failure makes that role/profile/contrast
`INELIGIBLE` rather than a pass. That rule does not resolve `OD2`, and the `RP` canonical
qualification wrapper remains explicitly null.

### The remaining minor repairs

`I4` is removed from `S4`'s applicable gate list; `STOP_AWAITING_AUTHORITY` is removed from the
legal stop states and is not added to the registered state machine, because the repository's
pre-execution governance status is not an experimental stop state; and active round references now
name the fourth independent methods review.

## What draft-v0.4 is

draft-v0.4 is an operator amendment produced in response to the **second** bounded independent
methods review, which returned `STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` against
commit `2b36f5321d830ea6f70fff2b7bbca3cb93394046` with two BLOCKING, six MAJOR and two MINOR
structured findings. Both independent reviews remain valid rejections and neither was edited.

**The drafting party does not claim draft-v0.4 is correct.** Every repair is recorded as
`PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. The determination belongs to the
third independent reviewer.

What the amendment adopted:

- **`I3` is narrowed to joint robust correctness.** The sole gate-bearing indicator is
  `J_joint_correct`, which is 1 exactly when BOTH registered variants of the cluster are scored
  correct. The estimand `p_joint` is a joint-correctness **level**, not a contrast, and it
  identifies no presentation effect. Every invariance, equivalence and presentation-effect claim
  is prohibited in active text (`S3MR2-001`, `S3MR2-008`).
- **The stochastic item-sampling model is registered.** Within each gate-bearing cell, units are
  independent draws **with replacement** from a registered finite generator distribution with
  exact rational weights. Duplicates are legitimate draws and must be retained. The K5
  deterministic complete-block assignment is retired in favour of an iid nuisance draw at exact
  weight `1/32` per state (`S3MR2-010`).
- **Family, profile and end-to-end power are registered**, not per-cell power alone. Every joint
  bound is a union bound valid under **arbitrary dependence** (`S3MR2-002`).
- **`S4` is `not_applicable` for `I4`** everywhere, and no confirmation applicability list
  contains it (`S3MR2-003`, `S3MR2-004`).
- **`I0` is separated from profile adequacy**, so `STOP_INSTRUMENT_DEFECT` is reachable and every
  event has exactly one legal next state (`S3MR2-006`).
- **A decode/prefill/sequence-evaluation ontology is registered**, so the `S4` generative stream's
  cost is bounded rather than null, and the `I0` fixture units are repaired (`S3MR2-005`,
  `S3MR2-009`).
- **The `P3-Q`/`I4` ordering constraint is registered** while `OD2` remains unresolved
  (`S3MR2-007`).

Nothing here is frozen. Nothing here authorizes execution. Zero model operations have been
performed. No seed has been drawn and no bank row exists.

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
- **I3 applicability:** the seven K5 contrast cells are `not_applicable` to S2 and S3; the two K6 contrast cells are applicable to every profile. `not_applicable` is never a pass.
- **Never selectable:** `S4`
- **Data-dependent ranking:** `false`
- **The study stops only when** no selectable interface remains eligible. The failure of one interface eliminates that interface and nothing else.

| Rank | Interface | Condition | Why |
| --- | --- | --- | --- |
| 1 | S2 | the frozen answer domain is jointly single-token eligible for every required role | S2 has no symbol-binding step, so a pass cannot be an artefact of label handling and a failure cannot be blamed on it |
| 2 | S3 | a later authority has introduced a multi-token answer domain, a dedicated multi-token stratum, a registered boundary-token rule and a length-confound gate | S3 is the natural surface for a multi-token domain, but it is not independent of S2 for single-token contents |
| 3 | S1 | S1 is eligible | S1 preserves continuity with Study 2 but is the surface whose adequacy is in question, so it is admitted only when no higher-ranked surface is available |

**The Family B denominator is fixed at 3 and never shrinks.**
Finding `S3MR-016` recorded that draft-v0.2 corrected over 3 selectable profiles while also
declaring S3 conditionally unavailable, so if S3 were unavailable the study would have
tested 2 profiles at a level computed for 3. In draft-v0.4 the denominator is 3 under
**every** outcome, including the outcome in which S3's multi-token activation condition is
not met and S3 is skipped. Shrinking the denominator after seeing which profiles are
available would be a data-dependent relaxation of the level and is prohibited.

**The selection rule is executable and enumerated before any data exists.** Walk the order
S2, then S3, then S1; select the first profile that passed every applicable component and
whose applicability condition is met; if none is both eligible and applicable, **STOP** and
never open the confirmation split. The rule is implemented as
`development_selection` in `studies/study3/analysis/design_statistics.py`, and all 16
pre-data scenarios are enumerated in `design_statistics_tables.json` under
`development_selection_map`.

- **No interface is selected in this round.**
- **Proposed disposition only:** `true`
- **Confirmation bank prohibition:** The admissibility order is evaluated on the development split only. The confirmation split is physically inaccessible until an interface has been proposed, the proposal has been sealed, and a separate authority has released it.


## Atomic evaluation cells and the pooling prohibition

- **Sampling unit:** the **base item** for I1a, I1b, I2 and I4; the **base-item contrast cluster** for I3. The two are different units and are never interchanged.
- **Cluster rule:** Every variant derived from one base item belongs to the same correlated cluster as that base item, is assigned to the same split as that base item, and is never treated as an independent observation. Splitting a cluster across splits would leak the confirmation set.

### Unit registry

Finding `S3MR-014` recorded that draft-v0.2 used the bare symbol `n` for four structurally
different things and changed its referent between artifacts without declaring the change
anywhere. In draft-v0.4 **every `n` carries its unit at the point of definition and in
every table that reports it**, and no single `n` is reused across unit types.

| Unit | Definition | Never equals |
| --- | --- | --- |
| `base_item` | one registered question stem with its registered ground truth; the independent sampling unit for I1a, I1b, I2 and I4 | rendered row, scored row, contrast cluster |
| `base_item_contrast_cluster` | one base item rendered in **exactly two** registered variants, a registered baseline and one registered content-equivalent transformed presentation; the independent sampling unit for I3 | base item, rendered row, scored row |
| `rendered_row` | one emitted presentation of one variant; a cluster always produces exactly two rendered rows | base item, contrast cluster, scored row |
| `scored_row` | one rendered row scored under one (interface profile, checkpoint role) pair | base item, contrast cluster, rendered row |

`n` is always the count of independent units in one atomic cell. It is never a rendered-row
count and never a scored-row count. A table that reports `n` without naming its unit is a
defect.

### The I3 sampling unit

An I3 base-item contrast cluster holds **exactly two** variants: the registered baseline
for that contrast cell, and one registered content-equivalent transformed presentation of
the same base item. Fixing the cluster at two variants makes the estimand identical in
every cell, so one floor is meaningful everywhere.

- **No cross-product.** K5 and K6 are not crossed with each other and no contrast is crossed with any other contrast. There is no 32 x 3 and no 96-variant factorial expansion anywhere in this design.
- **Disjoint base items.** Each contrast cell draws base-item identities disjoint from every other contrast cell, so no base item contributes to two cells and the cells are not correlated through a shared stem.

An atomic evaluation cell is one combination of interface profile, checkpoint role, task stratum, contrast family, contrast ID, operation family, depth, rendering, label alphabet and split, restricted to the factors that are applicable to the gate being evaluated. A gate passes only if it passes in every atomic cell to which it is applicable.

**Cell factors**

- interface profile
- checkpoint role
- task stratum
- contrast family
- contrast ID
- operation family
- depth
- rendering
- label alphabet
- split

**Pooling as a rescue is prohibited**

- **pooling K1 with K2** - K1 asks whether the model binds content to a displayed symbol; K2 asks whether it can echo trivially recoverable content at all. A high K2 rate can carry a failed K1 across a threshold, which would let the study report binding it never demonstrated.
- **pooling across primitive operation families** - a family the model handles well can mask a family it cannot handle, so the headroom gate would stop testing headroom
- **pooling K4 depth 2 with depth 3** - depth is the compositional variable of interest; averaging over it destroys the construct
- **pooling across checkpoint roles** - the roles are the contrast the later study depends on
- **pooling across interface profiles** - the interfaces are the object of comparison
- **pooling across renderings** - rendering sensitivity is precisely what K6 measures
- **pooling K5 with K6** - K5 varies what is inside the option list; K6 varies how the whole prompt is rendered. They are different constructs with disjoint base items, and a strong result on one would otherwise carry a failure on the other across a threshold.
- **pooling contrast IDs within K5 or within K6** - each contrast ID is a separately registered one-factor manipulation; pooling them would let an insensitive factor mask a sensitive one, which is precisely the failure I3 exists to find
- **pooling the K5 content-position cells with the K5 correct-symbol-index cells** - separating the physical position of the correct content from the identity of the displayed symbol is the entire reason the v0.1 cyclic design was withdrawn; pooling them re-creates the confound
- **pooling the two label alphabets** - label-set replacement is itself a registered manipulation (K5-A1), so averaging over the alphabet would average over the manipulation
- **pooling J_joint_correct with any descriptive summary** - `J_joint_correct` is the sole gate indicator; J_inv, J_cor and the descriptive paired table are reported alongside it and may never rescue a failed J_both
- **pooling across splits** - the confirmation split is a separate error role on data that was never inspected; pooling it with development would spend it

Pooled summaries may be reported for readability. They carry no gate authority, may never be substituted for a failed cell, and must be labelled descriptive wherever they appear.


## Counterbalancing

**The defect being corrected.** draft-v0.2 published a 4 x 4 x 2 orthogonal construction and
then defined the I3 indicator over "every applicable transformed variant", which implied a
cross-product of 32 counterbalanced conditions with 3 renderings and left the number of
variants per base item undefined and profile-dependent. Findings `S3MR-001` and `S3MR-002`
recorded that the estimand therefore changed from cell to cell while a single floor was
applied to all of them.

**The requirement.** Counterbalancing must produce pre-registered **pairwise** contrasts.
Each contrast cell holds base-item contrast clusters of **exactly two** variants: one
registered baseline and one registered one-factor transformation of it. No cross-product of
factors is formed anywhere, K5 and K6 are not crossed, and base-item identities are disjoint
across contrast cells.

**Factors that are separated**

- physical position of the correct content
- identity of the displayed symbol carrying the correct content
- label alphabet in use

### K5 - seven one-factor pairwise contrast cells

| Contrast | Varied factor | Held byte-identical | Transformation |
| --- | --- | --- | --- |
| `K5-P1` | content_position | correct_symbol_index, label_alphabet | the physical position of the correct content is moved by an offset of 1 modulo 4; the index of the correct displayed symbol and the label alphabet are held byte-identical |
| `K5-P2` | content_position | correct_symbol_index, label_alphabet | the physical position of the correct content is moved by an offset of 2 modulo 4; the index of the correct displayed symbol and the label alphabet are held byte-identical |
| `K5-P3` | content_position | correct_symbol_index, label_alphabet | the physical position of the correct content is moved by an offset of 3 modulo 4; the index of the correct displayed symbol and the label alphabet are held byte-identical |
| `K5-S1` | correct_symbol_index | content_position, label_alphabet | the index of the displayed symbol that carries the correct content is moved by an offset of 1 modulo 4; the physical position of the correct content and the label alphabet are held byte-identical |
| `K5-S2` | correct_symbol_index | content_position, label_alphabet | the index of the displayed symbol that carries the correct content is moved by an offset of 2 modulo 4; the physical position of the correct content and the label alphabet are held byte-identical |
| `K5-S3` | correct_symbol_index | content_position, label_alphabet | the index of the displayed symbol that carries the correct content is moved by an offset of 3 modulo 4; the physical position of the correct content and the label alphabet are held byte-identical |
| `K5-A1` | label_alphabet | content_position, correct_symbol_index | the label alphabet is replaced by the other registered alphabet; the physical position of the correct content and the index of the correct displayed symbol are held byte-identical |

Each cell holds base-item contrast clusters of exactly **2** variants. K5 is applicable to
the label-bearing profiles `S1` and `S4`, and is recorded `not_applicable` - never a pass -
for `S2` and `S3`, which render neither an option list nor a label alphabet.

### K6 - two disjoint pairwise contrast cells

| Contrast | Pair | Varied factor |
| --- | --- | --- |
| `K6-SEP` | `R-base` vs `R-sep` | the option separator only |
| `K6-INSTR` | `R-base` vs `R-instr` | the instruction sentence only |

The three registered renderings are **never compared as a three-way set**. They enter I3
only through these two disjoint pairwise cells. Within each pair the answer cue and every
other byte of the prompt are held fixed. K6 is applicable to every profile.

**Construction algorithm** (published and executable in the committed derivation script; randomness: **none anywhere in this design round** - every condition is a fixed function of the registered base-item index and the registered contrast ID, no seed is drawn, and no random draw appears at any point)

1. Derive the baseline condition of base-item index k as the triple (position, symbol index, alphabet index) = (k mod 4, (k div 4) mod 4, (k div 16) mod 2). Because the three factors cycle at different rates, every one of the 32 conditions occurs exactly once in each complete block of 32 consecutive base-item indices.

2. Place the correct content at the baseline position and fill the remaining three slots with the registered distractors in ascending slot order. This map from slots to content roles is a bijection.

3. Assign displayed symbols by the rotation slot -> (slot + shift) mod 4, where shift = (symbol index - position) mod 4. A rotation is a bijection on the four slots, so every displayed symbol is used exactly once and the correct content carries the intended symbol.

4. Emit the baseline variant as variant 1 of the cluster.

5. Apply the ONE registered factor of the contrast ID to the baseline triple: an offset modulo 4 on the position for K5-P1/P2/P3, an offset modulo 4 on the correct symbol index for K5-S1/S2/S3, or replacement of the alphabet for K5-A1. Re-render by steps 2 and 3 and emit the result as variant 2 of the cluster.

6. For K6, hold the entire condition triple fixed and change only the registered rendering factor, emitting R-base as variant 1 and R-sep or R-instr as variant 2.

7. Record, for each variant, the tuple (base item id, contrast family, contrast ID, position of correct content, index of the correct displayed symbol, label alphabet id, rendering id).

Deterministic balancing: each of the 32 baseline conditions appears exactly once per
complete block of 32 base-item indices in every contrast cell.

Verification: the committed derivation script asserts, and the committed design test re-checks, that every cluster holds exactly two variants, that every contrast changes exactly one registered factor, that option/label maps are bijections, that ground truth is preserved, that baseline conditions are balanced over a complete block, and that K5 and K6 share no base-item identity

**Label alphabets**

- **Requirement:** every label alphabet must be disjoint from the answer domain surface forms
- **Answer domain:** the mod-10 residues 0 through 9 in their registered surface form
- **Registered alphabet 1:** `A/B/C/D`
- **Registered alphabet 2:** `W/X/Y/Z`
- **Digits are forbidden as label symbols:** no label alphabet may contain a digit, because the registered answer domain is the mod-10 residues in decimal surface form and a digit label could not be distinguished from a valid answer
- **The two alphabets are mutually disjoint,** so replacing one is a real manipulation
- **Forbidden:** `1/2/3/4` and `0/1/2/3` - both collide with the mod-10 answer domain
- **Label-set replacement:** label-set replacement is a registered one-factor contrast in its own right (K5-A1) in which the position of the correct content and the index of the correct displayed symbol are held byte-identical, so the alphabet effect is not confounded with movement of the content


## Task strata

| Stratum | Name | Uses a model | Gate role |
| --- | --- | --- | --- |
| K0 | deterministic_software_fixtures | `false` | sole input to gate I0; coverage must include every scorer, every profile, every not_applicable branch, every tie path and every invalid-output path |
| K1 | explicit_answer_binding | `true` | sole input to gate I1b, which is applicable to label-bearing profiles only |
| K2 | identity_and_copy_depth0 | `true` | sole input to gate I1a |
| K3 | depth1_primitives | `true` | sole input to gate I2, evaluated per primitive operation family with no pooling across families |
| K4 | depth2_depth3_compositions | `true` | sole input to gate I4, evaluated per operation family and per depth |
| K5 | position_and_permutation_variants | `true` | input to gate I3 through seven disjoint pairwise contrast cells; applicable to label-bearing profiles only, and recorded as not_applicable rather than as a pass for S2 and S3 |
| K6 | rendering_variants | `true` | input to gate I3 through two disjoint pairwise contrast cells, applicable to every profile |

**K5 data-generating process.** Each K5 contrast cell draws its own disjoint set of base items from K1, K2 and K3 and renders each base item as a base-item contrast cluster of exactly TWO variants: the registered baseline condition for that base-item index, and one registered one-factor transformation of that baseline. Seven contrast cells are registered: K5-P1, K5-P2 and K5-P3 move only the physical position of the correct content by offsets of 1, 2 and 3 modulo 4; K5-S1, K5-S2 and K5-S3 move only the index of the correct displayed symbol by offsets of 1, 2 and 3 modulo 4; K5-A1 replaces only the label alphabet. In every cell the two factors that are not varied are held byte-identical. There is no cross-product of factors, no cyclic four-order set, and no random draw: the baseline condition is the fixed function (k mod 4, (k div 4) mod 4, (k div 16) mod 2) of the registered base-item index k, which balances all three factors over each complete block of 32 base items. The two registered label alphabets are A/B/C/D and W/X/Y/Z, both disjoint from the mod-10 answer domain and from each other; digits are forbidden as label symbols.

**K6 data-generating process.** Three renderings are registered: R-base, which is the baseline; R-sep, which is identical to R-base except for the separator string between a label and its option content; and R-instr, which is identical to R-base except for the wording of the instruction sentence. The answer cue is byte-identical across all three. These renderings enter gate I3 as exactly TWO disjoint pairwise contrast cells and never as a three-way comparison: K6-SEP pairs R-base with R-sep, and K6-INSTR pairs R-base with R-instr. Each cell draws its own disjoint set of base items and renders each as a base-item contrast cluster of exactly two variants, with the entire condition triple and every other byte of the prompt held fixed within the pair.

_Findings `S3MR-010` and `S3MR-011` recorded that draft-v0.2 carried stale v0.1 text in both
of these fields: K5 still described four cyclic permutations and a label-set replacement to
`1/2/3/4`, and K6 still said the renderings differ in the answer cue while the adjacent field
said the cue is held constant. Both fields above are now the single governing description._


## Checkpoint and control roles

| Role | Name | Is a model | Identity | Gate role |
| --- | --- | --- | --- | --- |
| R0 | deterministic_non_model_oracle | `false` | the harness itself, executed on K0 fixtures | Gate I0 |
| RC | explicit_answer_binding_condition | `false` | a condition, not a checkpoint: the K1 stratum applied to whichever model role is under test | Gates I1a and I1b |
| RT | target | `true` | deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B | Gates I1a, I1b, I2, I3, I5 |
| RL | lineage_base | `true` | Qwen/Qwen2.5-Math-1.5B | Gates I1a, I1b, I2, I3 |
| RI | instruction_control | `true` | Qwen/Qwen2.5-Math-1.5B-Instruct | Gates I1a, I1b, I2, I3 |
| RP | positive_capability_reference | `true` | `UNSELECTED` - operator review item | Gate I4 only |

_Finding `S3MR-018` recorded that draft-v0.2 still labelled the RC and target roles with
"Gate I1" after I1 had been split into I1a and I1b, so the document referred to a gate that
no longer exists. The labels above are corrected._


## Positive reference

- **Selection status:** `UNSELECTED. Candidate dossier only. No candidate is selected, preferred, pinned, ranked, downloaded, tokenized, loaded or prequalified.`
- **Blocking decision:** `OD2`
- **Dossier:** `studies/study3/references/positive_reference_dossier.md`
- **Candidate families retained for a future operator decision:** 3 (families, not selections)

**No positive reference is selected in draft-v0.4, and none may be selected without a new
operator authority.** No checkpoint has been selected, preferred, pinned, revision-resolved,
downloaded, tokenized, loaded or prequalified. The dossier retains candidates for a future
operator decision and records each of them as `UNSELECTED`.

**The circularity being corrected.** draft-v0.1 permitted the positive reference to be
prequalified through a candidate interface. If a candidate interface is what demonstrates
that the reference is capable, the interface's adequacy rests on an argument that presupposes
it.

**The requirement.** the positive reference must be prequalified through a separate canonical interface that is not S1, S2, S3 or S4, on items disjoint from those used for gate I4

- **Canonical interface status:** not defined in this round; it must be registered before P3-Q, and it is not a member of the candidate panel
- **Item disjointness:** the P3-Q prequalification items and the K4 I4 items must be disjoint by construction
- **Provenance correction:** finding `S3MR-020` recorded that the dossier attributed the exclusion of the target's own lineage base to `D-07`, when `D-07` is the parser-v2 gate decision and the governing decision is `D-04`. Both back-references in the dossier are corrected to `D-04`.


## Gate hierarchy

| Gate | Name | Part of eligibility | Authorizes mechanistic execution | Fail closed |
| --- | --- | --- | --- | --- |
| I0 | instrument integrity | `true` | `false` | `true` |
| I1a | trivial content recovery and output validity | `true` | `false` | `true` |
| I1b | explicit content-to-symbol binding | `true` | `false` | `true` |
| I2 | primitive headroom | `true` | `false` | `true` |
| I3 | joint robust correctness across a registered presentation pair | `true` | `false` | `true` |
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
- **Independent unit:** `base items per atomic cell`
- **n:** `256` base items per atomic cell
- **Threshold logic:** exact one-sided binomial test against the null p <= 9/10 at the per-component development level 1/600, in every applicable atomic cell separately; the component passes a cell when at least 389 of 413 base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 succeed. On the confirmation split the same form is used at level 1/200 with a pass count of 388.

| Split | Null | p1 | n | Unit of n | alpha (exact rational) | Required pass count | Exact null tail at p0 | Exact power at p1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | p <= 0.9 | 0.97 | 256 | base items per atomic cell | `1/600` | 244 | 0.001491215117 | 0.953040775 |
| confirmation | p <= 0.9 | 0.97 | 256 | base items per atomic cell | `1/200` | 243 | 0.003307722347 | 0.976290353 |
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
- **Independent unit:** `base items per atomic cell`
- **n:** `256` base items per atomic cell
- **Threshold logic:** exact one-sided binomial test against the null p <= 9/10 at the per-component development level 1/600, in every applicable atomic cell separately; the component passes a cell when at least 389 of 413 base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 succeed. On the confirmation split the same form is used at level 1/200 with a pass count of 388.

| Split | Null | p1 | n | Unit of n | alpha (exact rational) | Required pass count | Exact null tail at p0 | Exact power at p1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | p <= 0.9 | 0.97 | 256 | base items per atomic cell | `1/600` | 244 | 0.001491215117 | 0.953040775 |
| confirmation | p <= 0.9 | 0.97 | 256 | base items per atomic cell | `1/200` | 243 | 0.003307722347 | 0.976290353 |
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
- **Independent unit:** `base items per primitive-family cell`
- **n:** `128` base items per primitive-family cell
- **Threshold logic:** exact one-sided binomial test against the null p <= 1/2 at the per-component development level 1/600, in every applicable atomic cell separately; the component passes a cell when at least 129 of 214 base items per primitive-family cell succeed. On the confirmation split the same form is used at level 1/200 with a pass count of 127.

| Split | Null | p1 | n | Unit of n | alpha (exact rational) | Required pass count | Exact null tail at p0 | Exact power at p1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | p <= 0.5 | 0.7 | 128 | base items per primitive-family cell | `1/600` | 82 | 0.000931234262 | 0.938986365 |
| confirmation | p <= 0.5 | 0.7 | 128 | base items per primitive-family cell | `1/200` | 80 | 0.002962603303 | 0.972425829 |
- **What passes:** every primitive family independently clears the floor
- **What fails:** any single family falls below the floor, regardless of the pooled rate across families
- **`not_applicable` semantics:** none; I2 applies to every profile
- **Merely descriptive:** the pooled rate across families
- **Legal next state on pass:** evaluate I3
- **Legal next state on fail:** eliminate this interface profile for this role; if no selectable profile remains, STOP
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`

### Gate I3 - joint robust correctness across a registered presentation pair

**Question.** Does the joint-correctness probability under both registered presentations of the same base item exceed the registered floor in this contrast cell?

**Primary indicator.** `J_joint_correct` = 1 if and only if BOTH registered variants of the
base-item contrast cluster are scored correct against the same unique registered ground truth.

**Estimand.** `p_joint` = Pr(`J_joint_correct` = 1) over the registered item-generating
distribution for that atomic contrast cell. This is a **level**, not a contrast. It does not
identify the direction, magnitude or existence of a presentation effect.

| Field | Value |
| --- | --- |
| null hypothesis | `p <= 9/10` |
| p0 | `9/10` |
| p1 | `97/100` |
| n | 413 |
| unit of n | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 |
| development alpha | `1/600` |
| development pass count | 389 |
| exact null tail at p0 | 0.001664632930 |
| exact power at p1 | 0.999129439838 |

**What passes.** the registered joint-correctness floor was cleared for this applicable pairwise cell, and nothing more

**What fails.** the joint-correctness probability under the registered presentation pair does not clear the registered floor. This localises inadequate joint robust correctness for the named pair. It does not identify the direction, the magnitude or the existence of a presentation effect.

#### The full ordered outcome lattice

Over the alphabet `correct`, `wrong_a`, `wrong_b`, `invalid` for the two variants there are 16 ordered cases. Exactly
1 case family passes the primary indicator: both variants correct.

| Variant 1 | Variant 2 | `J_joint_correct` | Scores |
| --- | --- | --- | --- |
| `correct` | `correct` | 1 | `true` |
| `correct` | `wrong_a` | 0 | `false` |
| `correct` | `wrong_b` | 0 | `false` |
| `correct` | `invalid` | 0 | `false` |
| `wrong_a` | `correct` | 0 | `false` |
| `wrong_a` | `wrong_a` | 0 | `false` |
| `wrong_a` | `wrong_b` | 0 | `false` |
| `wrong_a` | `invalid` | 0 | `false` |
| `wrong_b` | `correct` | 0 | `false` |
| `wrong_b` | `wrong_a` | 0 | `false` |
| `wrong_b` | `wrong_b` | 0 | `false` |
| `wrong_b` | `invalid` | 0 | `false` |
| `invalid` | `correct` | 0 | `false` |
| `invalid` | `wrong_a` | 0 | `false` |
| `invalid` | `wrong_b` | 0 | `false` |
| `invalid` | `invalid` | 0 | `false` |

Stable wrong, stable invalid, mixed correctness and two different wrong answers all fail.

#### Historical indicators

`J_inv`, `J_cor` and the retired conjunction `J_both` survive only as historical names and
descriptive audit quantities with status `DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY`. They carry no
gate, eligibility, selection, confirmation, ranking, rescue or claim authority and no reachable
decision path. Under a unique registered ground truth `J_cor` implies `J_inv`, so the retired
`J_both` was identically `J_cor` and is identically `J_joint_correct`; the active name makes the
identity explicit.

#### Claim ceiling, by profile

| Profile | Applicable cells | Claim |
| --- | --- | --- |
| `S1` | 9 | joint robust correctness for each of the seven applicable K5 pairs and the two applicable K6 pairs, separately |
| `S2` | 2 | joint robust correctness for the two applicable K6 pairs only; the seven K5 pairs are not_applicable and are never counted as passes or as evidence |
| `S3` | 2 | joint robust correctness for the two applicable K6 pairs only, and only while S3's separately registered single-token applicability condition holds |
| `S4` | 9 | descriptive only; S4 is never selectable and never enters an interface-selection or confirmation claim |

Passing an applicable cell supports only this statement:

> Under the registered item-generating distribution for this named contrast cell, the probability that both the baseline and the named transformed presentation are scored correct exceeded the registered floor.

It supports no statement that the two marginal accuracies are equal and no statement that the
transformation has no effect.

### Gate I4 - positive reference adequacy

**Question.** Does an independently prequalified capable reference succeed through this interface, so that a target failure through the same interface can be attributed to the target rather than to the interface?

- **Inputs:** stratum K4 compositional items at depth 2 and depth 3
- **Model roles:** `RP`
- **Applicable profiles:** S1, S2, S3, S4
- **Part of eligibility:** `true`
- **Independent unit:** `base_item`
- **n:** `256` RP base items per operation-family x depth cell per candidate profile
- **Evaluated per:** interface profile, operation family, depth
- **Pooling across cells:** `prohibited`
- **Threshold logic:** exact one-sided binomial test against the null p <= 4/5 at the per-component development level 1/600, in every applicable atomic cell separately; the component passes a cell when at least 383 of 448 RP base items per operation-family x depth cell per candidate profile succeed. On the confirmation split the same form is used at level 1/200 with a pass count of 381.

| Split | Null | p1 | n | Unit of n | alpha (exact rational) | Required pass count | Exact null tail at p0 | Exact power at p1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | p <= 0.8 | 0.9 | 256 | RP base items per operation-family x depth cell per candidate profile | `1/600` | 224 | 0.001081002486 | 0.921083515 |
| confirmation | p <= 0.8 | 0.9 | 256 | RP base items per operation-family x depth cell per candidate profile | `1/200` | 222 | 0.003276850097 | 0.963820468 |

- The draft-v0.1 proposal of `p <= 0.25` at n = 128, acceptance count 49, rate 0.3828, remains `REJECTED_BY_OPERATOR_REVIEW`: a chance-level null establishes only that the reference beats guessing; it is not a competence floor, and only a competence claim can license the inference that a capable model would have succeeded.
- **Prequalification:** the positive reference must be prequalified through a separate canonical interface that is not S1, S2, S3 or S4, on items disjoint from those used for I4. Stage `P3-Q`, status: **not authorised, not executed**; `RP` is `UNSELECTED`.
- **`OD2` remains unresolved and blocking.** Every quantity in the positive-reference qualification work stream is published as `null` with status `UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2`, because a number there would imply a selection that has not been made.
- **Consequence of failure:** this interface profile is eliminated, and only this interface profile. The study stops only if no selectable interface profile remains eligible.
- **What passes:** the prequalified reference clears the competence floor through this interface in every family and at every depth
- **What fails:** the reference does not clear the floor through this interface
- **`not_applicable` semantics:** I4 is applicable to S1, S2 and S3. It is `not_applicable` to S4, which is never selectable and therefore never enters eligibility.
- **Merely descriptive:** the reference's pooled rate across families and depths
- **Legal next state on pass:** the interface profile is eligible; evaluate the admissibility order
- **Legal next state on fail:** eliminate this interface profile; if no selectable profile remains, STOP
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`


### Gate I5 - one-shot confirmation

**Question.** Do the constructs that passed on the development split hold on a confirmation split that was never inspected?

- **Inputs:** the confirmation split of every gate-bearing stratum, including K4
- **Model roles:** `RT`, `RL`, `RI`, `RP`
- **Applicable profiles:** the single **development-selected** interface profile only
- **Part of eligibility:** `false`
- **Covered constructs:** `I0`, `I1a`, `I1b`, `I2`, `I3_J_joint_correct`, `I4`
- **Component alpha:** exact rational `1/200`
- **Pooling across cells:** `prohibited`
- **Accessible before authority:** `false`

**The defect being corrected.** finding S3MR-017 recorded that draft-v0.2 named I5 the one-shot confirmation gate but published no confirmation sample size, no confirmation threshold and no confirmation multiplicity treatment, so the gate could not be executed as written. This section now publishes all three.

#### Confirmation components

| Component | Null | n | Unit of n | alpha (exact rational) | Required pass count | Exact null tail at p0 | Exact power at p1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | p <= 0.9 | 256 | base items per atomic cell | `1/200` | 243 | 0.003307722347 | 0.976290353 |
| I1b | p <= 0.9 | 256 | base items per atomic cell | `1/200` | 243 | 0.003307722347 | 0.976290353 |
| I2 | p <= 0.5 | 128 | base items per primitive-family cell | `1/200` | 80 | 0.002962603303 | 0.972425829 |
| I3 | p <= 0.9 | 256 | base-item contrast clusters per contrast cell | `1/200` | 243 | 0.003307722347 | 0.976290353 |
| I4 | p <= 0.8 | 256 | RP base items per operation-family x depth cell per candidate profile | `1/200` | 222 | 0.003276850097 | 0.963820468 |

- **Threshold logic:** each covered construct is tested by the same exact one-sided binomial form used on the development split, against the same registered null, at the confirmation component level 1/200, in every applicable atomic cell separately. The applicable cells form an intersection-union conjunction. Confirmation applicability is the intersection of the component's registered SELECTABLE profiles with the single development-selected profile, so S4 can never appear. No threshold, floor, sample size, unit, indicator or applicability rule may be re-tuned after the development split is read.
- **Multiplicity:** no across-profile correction is applied at confirmation, because exactly one profile is selected on the development split before confirmation is entered and no reselection is permitted. The resulting claim is explicitly conditional on that single profile.
- **Selection precondition:** I5 may be entered only after the pre-registered development selection map has returned exactly one selected profile. If the map returns none, the study STOPS and the confirmation split is never opened.
- **One-shot rule:** the confirmation split is read exactly once, for exactly one profile, under exactly one pre-registered analysis. It is spent by that reading. There is no second look, no re-analysis, no rescue path and no re-selection.
- **Reselection prohibited:** `true`
- **Re-tuning prohibited:** no threshold, floor, sample size, unit, indicator or applicability rule may change after the development split is read
- **What passes:** every construct holds on data that was never inspected
- **What fails:** any applicable cell of any covered construct fails to replicate at its registered threshold
- **`not_applicable` semantics:** constructs that are not_applicable to the selected profile are not evaluated and are recorded as `not_applicable`, which is a third value and never a pass.
- **Legal next state on pass:** the interface is calibrated; a separate authority is still required before any mechanistic work
- **Legal next state on fail:** STOP. The confirmation split is spent and may not be reused, and no other profile may be substituted.
- **Authorizes mechanistic execution:** `false`
- **Fail closed:** `true`


## Gate truth table and legal stop states

Every gate is fail-closed. No gate authorises mechanistic execution.

### Gate applicability by interface profile

This table enumerates the applicability of each gate to each interface profile. The operator amendment authority, section 4.1, requires that K5 be recorded not_applicable for S2 and S3 and never counted as a pass; the draft-v0.2 table showed the K5 transformations as PASSING for those profiles, which contradicts the not_applicable semantics the same document declares. The rows are corrected: K5 is not_applicable for S2 and S3, and not_applicable is a third value that is never a pass.

| Profile | Label bearing | I0 | I1a | I1b | I2 | I3 K5 | I3 K6 | I4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | `true` | `applicable` | `applicable` | `applicable` | `applicable` | `applicable` | `applicable` | `applicable` |
| S2 | `false` | `applicable` | `applicable` | `not_applicable` | `applicable` | `not_applicable` | `applicable` | `applicable` |
| S3 | `false` | `applicable` | `applicable` | `not_applicable` | `applicable` | `not_applicable` | `applicable` | `applicable` |
| S4 | `true` | `applicable` | `applicable` | `applicable` | `applicable` | `applicable` | `applicable` | `not_applicable` |

- `S1` selectable: `true`
- `S2` selectable: `true`
- `S3` selectable: `true`
- `S4` selectable: `false` - S4 is a never-selectable diagnostic and is excluded from every success union

**This table records applicability only.** It records no outcome, because no gate has been
evaluated and no data exists.

| Value | Meaning |
| --- | --- |
| `applicable` | the gate is evaluated for this profile and must pass in every atomic cell |
| `not_applicable` | the construct has no referent for this profile, so the gate is not evaluated. This is a third value: it is not a pass, it is not a zero effect, it is not evidence of robustness, and it may never be counted as a satisfied gate, averaged into any rate, or used as an input to admissibility. |

_The operator amendment authority, section 4.1, requires that K5 be recorded
`not_applicable` for S2 and S3 and never counted as a pass. The draft-v0.2 table showed
the K5 transformations as **passing** for those profiles, which contradicts the `not_applicable` semantics the same document
declares. The rows above are corrected._

### Gate lifecycle

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

- **Framework:** frequentist, pre-registered, exact-binomial primary; every level is an exact rational and every decimal in this document is a rendering of it
- **Status of every number below:** proposed design parameters, not measurements
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`
- **Derivation script:** `studies/study3/analysis/design_statistics.py`
- **Derivation tables:** `studies/study3/analysis/design_statistics_tables.json`
- **Reproducibility:** the script's --check mode recomputes every table and compares it value-for-value against the committed tables; the committed design test runs that check, and the CPU-only Azure validation runs it again against the exact publication commit
- **Model free:** `true`

**Derivation, not transcription.** Every threshold, exact null tail, power figure and expected pass count in this section is derived by the committed script from the declared assumptions by exact binomial search over exact rational arithmetic. The reviewer-returned planning targets are not present in the script as literals; the committed design test holds them as an independent expectation and additionally asserts by AST inspection that none of the derived pass counts appears as an integer constant in the script. Copying a constant instead of deriving it is a test failure by construction.

### The exact rational policy

The **exact rational is the policy**; the decimal is a rendering of it and is never the
source of truth. Finding `S3MR-003` recorded that draft-v0.2 declared a per-profile alpha of
`0.001666666667` in one field and then implemented `0.005` in every component that actually
derived a threshold, so the advertised across-profile correction did not exist anywhere in
the computation. Carrying the rational form beside every decimal makes that class of
divergence detectable by inspection.

| Level | Exact rational | Decimal rendering |
| --- | --- | --- |
| study-level development screening alpha | `1/200` | `0.005` |
| per-profile development component alpha | `1/600` | `0.001666666667` |
| confirmation component alpha | `1/200` | `0.005` |
| target power | `9/10` | `0.9` |

### Multiplicity

Two structurally different multiplicity problems are kept apart. Within one interface profile every applicable component must pass; that conjunction is an intersection-union test whose size is bounded by the level of its individual components, so no further within-profile correction is applied to the conjunction itself. Across interface profiles the study may proceed if ANY selectable profile qualifies; that is a union event, it inflates the false-qualification rate, and it is Bonferroni-corrected by a denominator fixed before any data exists.

- **Family A, within a profile** (`intersection_union_conjunctive`): members I1a, I1b, I2, I3_J_joint_correct, I4; per-component alpha exact rational `1/600`; correction: **none within the profile** - the intersection-union size is bounded by the component level, so no further within-profile Bonferroni correction is applied
- **Family B, across profiles** (`union_selection`): members S1, S2, S3; study-level screening alpha exact rational `1/200`; **fixed** selectable-profile denominator `3`, fixed before data and never shrinking; per-profile alpha exact rational `1/600`; `per_profile_alpha x 3 = study_alpha` exactly, asserted in the derivation script
- **Family D, confirmation** (`single_preselected_profile_one_shot`): component alpha exact rational `1/200`; **no across-profile correction**, because exactly one profile is selected on the development split before confirmation is entered, no reselection is permitted, and the resulting claim is explicitly conditional on that profile
- **Family C, descriptive:** pooled summaries, softmax confidences, per-cell Clopper-Pearson intervals, the paired 2x2 discordance summary and the selected-label uniformity diagnostic; reported for readability, carrying **no** gate, eligibility, selection or confirmation authority anywhere
- **Excluded from selection:** S4 is never selectable and never enters selection

### Development exact-binomial components

| Gate | Construct | Null | p1 | n | Unit of n | alpha | Pass count | Exact null tail | Exact power at p1 | Degenerate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | trivial content recovery, explicit content-to-symbol binding, and joint robust correctness across a registered presentation pair | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/600` | 389 | 0.001664632930 | 0.999129439838 | `false` |
| I1b | trivial content recovery, explicit content-to-symbol binding, and joint robust correctness across a registered presentation pair | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/600` | 389 | 0.001664632930 | 0.999129439838 | `false` |
| I2 | primitive headroom, evaluated separately per registered operation family | `p <= 1/2` | `7/10` | 214 | base items per primitive-family cell | `1/600` | 129 | 0.001597676081 | 0.999042859186 | `false` |
| I3 | joint robust correctness across a registered presentation pair | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/600` | 389 | 0.001664632930 | 0.999129439838 | `false` |
| I4 | positive-reference competence recovery through the candidate interface | `p <= 4/5` | `9/10` | 448 | RP base items per operation-family x depth cell per candidate profile | `1/600` | 383 | 0.001620609599 | 0.999005509196 | `false` |

Each development `n` is the **smallest unrestricted positive integer** that reaches the registered
per-cell power target at its registered `p1` and alpha. draft-v0.3 restricted admissible `n` to
multiples of the complete-block size 32; that restriction is retired with the deterministic block
assignment it came from. Each pass count is the smallest count controlling its registered null.

### Confirmation exact-binomial components

| Gate | Construct | Null | p1 | n | Unit of n | alpha | Pass count | Exact null tail | Exact power at p1 | Degenerate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | trivial content recovery, explicit content-to-symbol binding, and joint robust correctness across a registered presentation pair | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/200` | 388 | 0.003020762720 | 0.999609916012 | `false` |
| I1b | trivial content recovery, explicit content-to-symbol binding, and joint robust correctness across a registered presentation pair | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/200` | 388 | 0.003020762720 | 0.999609916012 | `false` |
| I2 | primitive headroom, evaluated separately per registered operation family | `p <= 1/2` | `7/10` | 214 | base items per primitive-family cell | `1/200` | 127 | 0.003765544908 | 0.999646587923 | `false` |
| I3 | joint robust correctness across a registered presentation pair | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/200` | 388 | 0.003020762720 | 0.999609916012 | `false` |
| I4 | positive-reference competence recovery through the candidate interface | `p <= 4/5` | `9/10` | 448 | RP base items per operation-family x depth cell per candidate profile | `1/200` | 381 | 0.003582895662 | 0.999626931069 | `false` |

Confirmation applicability is the **intersection** of each component's registered selectable
profiles with the single development-selected profile, so `S4` can never appear. `I1b` and the seven
`K5` pairs are label-bearing only, so their confirmation applicability is `S1` alone; for `S2` and
`S3` they are `not_applicable` and never a pass.

The confirmation sizes are **conservative reuse** of the development sizes, not minimal confirmation
sizes.

### Power architecture

Per-cell power alone does not describe this design's operating characteristics. The
type-II allocation below is binding and every joint bound is a union bound valid under
**arbitrary dependence**; no independence between cells, profiles, roles or stages is used.

| Quantity | Exact rational | Scope |
| --- | --- | --- |
| maximum selectable-profile cell count `m_max` | 43 | over `S1`, `S2`, `S3`; `S4` is excluded |
| per-stage profile false-negative budget | `19/400` | one profile, one stage |
| per-cell false-negative budget | `19/17200` | per atomic evaluation cell |
| per-cell power target | `17181/17200` | **PER ATOMIC EVALUATION CELL** |
| profile stage power floor | `381/400` | one profile, one stage; union-bound lower bound |
| confirmation conjunction power floor | `381/400` | one-shot confirmation conjunction |
| panel false-qualification budget | `1/200` | across the fixed three-profile denominator |
| study end-to-end power floor | `9/10` | development selection plus one-shot confirmation |

**Cell counts by profile.**

| Profile | Cells at the I1/I3 floor | Cells at the I2 floor | Cells at the I4 floor | Total | Selectable |
| --- | --- | --- | --- | --- | --- |
| `S1` | 33 | 6 | 4 | 43 | `true` |
| `S2` | 9 | 6 | 4 | 19 | `true` |
| `S3` | 9 | 6 | 4 | 19 | `true` |
| `S4` | 33 | 6 | 0 | 39 | `false` |

**The union-bound proof.** Pr(the study returns the designated adequate profile and confirms it) >= 1 - 19/400 - 1/200 - 19/400 = 9/10 The unioned failure events are:

- the designated adequate profile fails to qualify in development, bounded by 19/400 as the sum over its at most m_max applicable cells of the per-cell false-negative budget 19/17200
- a higher-priority profile that lies in its registered profile null is falsely qualified, bounded by the panel false-qualification budget 1/200
- the selected adequate profile fails the confirmation conjunction, bounded by 19/400 by the same per-cell allocation on the confirmation split

**The binding claim holds only under this least-favourable configuration.**

- I0 passes
- at least one selectable profile has every applicable atomic-cell success probability at or above that cell's registered p1
- any higher-priority profile that is not adequate lies in its registered profile null, meaning at least one of its required cells is at or below that cell's p0
- development and confirmation follow the frozen selection order with no rescue and no substitution
- the selected adequate profile remains at or above p1 on the confirmation-generating distribution

**Not covered by the power guarantee.**

- profiles whose cell success probabilities lie in the indifference region strictly between p0 and p1
- distribution shift between the development and confirmation generating distributions
- I0 failure
- an invalid or unregistered sampling frame
- protocol deviations of any kind

**Vocabulary.** `target_power` is per atomic cell. `profile_stage_power_floor` is a
union-bound lower bound under arbitrary cell dependence.
`study_end_to_end_power_floor` carries the stated least-favourable configuration.
Selection-return and confirmation operating characteristics are named separately and are
never called power. a STOP outcome reports the realized registered gate outcome in that run. It is not a proof that no population-level adequate interface exists and is never a model-capability conclusion.

### The registered sampling frame

within each gate-bearing atomic cell, base-item units or base-item contrast-cluster units are independent draws WITH REPLACEMENT from that cell's registered generator distribution; the deterministic model and scorer map each independently drawn unit to exactly one Bernoulli success indicator.

| Level | Identified by | Excludes |
| --- | --- | --- |
| sampling cell | split, gate or component, stratum or operation-family x depth, contrast ID where applicable | interface profile, checkpoint role |
| evaluation cell | one sampling cell x one applicable profile x one applicable role | - |

One iid item stream is drawn per sampling cell and reused across its applicable
evaluation cells. Every evaluation cell is therefore marginally iid Bernoulli, while
evaluation cells sharing sampled items may be dependent. That dependence is expressly
allowed and is handled by the arbitrary-dependence bounds above.

- Development sampling cells: **17**; confirmation sampling cells: **17**.
- Draws are **with replacement**. Duplicate generator tuples are legitimate draws and
  **must be retained**; redrawing for uniqueness, difficulty, balance or model response
  is prohibited.
- Every sampled parameter carries an exact rational weight and every parameter's weights
  sum to exactly one.
- Validity predicates are deterministic and evaluated before any model operation; every
  registered support satisfies them by construction, so the registered rejection
  probability is exactly `0`.
- Development, confirmation and future `P3-Q` supports are physically disjoint by the
  registered outcome-blind namespace partition of the generator key, frozen before any
  seed draw.
- The K5 baseline nuisance state has a **32**-state support with exact weight
  `1/32` per state, drawn iid with replacement. `n` is no longer required
  to be a multiple of the support size.
- **No seed exists and no bank row exists.** Seed values, the generator implementation
  blob and the realized bank are `null`, meaning *not yet selected*, not zero.

**Exact-binomial validity holds exactly under these conditions.**

- the n units of the evaluation cell are the images of n iid draws from that cell's registered generator distribution
- the scorer is a deterministic function of the drawn unit and the pinned checkpoint, so each unit yields exactly one Bernoulli indicator with a common success probability
- no unit is redrawn, filtered, deduplicated or reordered on any post-draw property
- the null and the alternative are statements about that cell's registered generating distribution
- the split namespace of the cell is disjoint from every other split

if any gate-bearing atomic cell lacks a complete generator distribution, or would require an adaptive post-draw choice, the design fails closed for that cell. It is not silently downgraded to descriptive and no exact-binomial validity is claimed for it.

### The total state machine

`I0` is a **global precondition**, evaluated before and outside profile adequacy. Every
event has exactly one legal next state and every registered terminal state is reachable.

| From | Event | Next |
| --- | --- | --- |
| `Q0_INSTRUMENT` | all fixtures pass | `Q1_DEVELOPMENT` |
| `Q0_INSTRUMENT` | any fixture fails | `STOP_INSTRUMENT_DEFECT` |
| `Q0_INSTRUMENT` | error | `STOP_INSTRUMENT_DEFECT` |
| `Q0_INSTRUMENT` | ambiguity | `STOP_INSTRUMENT_DEFECT` |
| `Q1_DEVELOPMENT` | completed validly | `Q2_SELECTION` |
| `Q1_DEVELOPMENT` | protocol or integrity error | `STOP_DEVELOPMENT_INTEGRITY_ERROR` |
| `Q2_SELECTION` | a profile is selected | `Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY` |
| `Q2_SELECTION` | no profile is eligible and applicable | `STOP_NO_SELECTABLE_INTERFACE_REMAINS` |
| `Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY` | authority granted and conjunction passes | `CALIBRATED_PENDING_SEPARATE_SUBSTANTIVE_AUTHORITY` |
| `Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY` | authority granted and any applicable cell fails | `STOP_CONFIRMATION_FAILED` |
| `Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY` | authority granted and an error or ambiguity occurs | `STOP_CONFIRMATION_SPENT_ON_ERROR` |

| Terminal state | Claim |
| --- | --- |
| `STOP_INSTRUMENT_DEFECT` | the instrument is defective. NOTHING was measured about any interface. This is never a statement about any interface or any model. |
| `STOP_DEVELOPMENT_INTEGRITY_ERROR` | a protocol or integrity error occurred during development. This is a fail-closed integrity stop and is never reinterpreted as a scientific gate failure. |
| `STOP_NO_SELECTABLE_INTERFACE_REMAINS` | no candidate profile passed the registered development gates in that realized run. It is not a proof that no population-level adequate interface exists and is never a model-capability conclusion. |
| `STOP_CONFIRMATION_FAILED` | the selected profile did not replicate on the confirmation split. The split is spent and no substitution or reselection is permitted. |
| `STOP_CONFIRMATION_SPENT_ON_ERROR` | the confirmation split was spent on an error or ambiguity. It may not be re-read. |
| `CALIBRATED_PENDING_SEPARATE_SUBSTANTIVE_AUTHORITY` | the named interface cleared the registered gates for the named tasks and roles, conditional on the single selected profile. No mechanistic authority is created. |

The sixteen-row profile-eligibility map is retained as the `Q2_SELECTION` subtable that
applies only once `I0` has passed. It is not the whole state machine.

### Power architecture

Per-cell power alone does not describe this design's operating characteristics. The
type-II allocation below is binding and every joint bound is a union bound valid under
**arbitrary dependence**; no independence between cells, profiles, roles or stages is used.

| Quantity | Exact rational | Scope |
| --- | --- | --- |
| maximum selectable-profile cell count `m_max` | 43 | over `S1`, `S2`, `S3`; `S4` is excluded |
| per-stage profile false-negative budget | `19/400` | one profile, one stage |
| per-cell false-negative budget | `19/17200` | per atomic evaluation cell |
| per-cell power target | `17181/17200` | **PER ATOMIC EVALUATION CELL** |
| profile stage power floor | `381/400` | one profile, one stage; union-bound lower bound |
| confirmation conjunction power floor | `381/400` | one-shot confirmation conjunction |
| panel false-qualification budget | `1/200` | across the fixed three-profile denominator |
| study end-to-end power floor | `9/10` | development selection plus one-shot confirmation |

**Cell counts by profile.**

| Profile | Cells at the I1/I3 floor | Cells at the I2 floor | Cells at the I4 floor | Total | Selectable |
| --- | --- | --- | --- | --- | --- |
| `S1` | 33 | 6 | 4 | 43 | `true` |
| `S2` | 9 | 6 | 4 | 19 | `true` |
| `S3` | 9 | 6 | 4 | 19 | `true` |
| `S4` | 33 | 6 | 0 | 39 | `false` |

**The union-bound proof.** Pr(the study returns the designated adequate profile and confirms it) >= 1 - 19/400 - 1/200 - 19/400 = 9/10 The unioned failure events are:

- the designated adequate profile fails to qualify in development, bounded by 19/400 as the sum over its at most m_max applicable cells of the per-cell false-negative budget 19/17200
- a higher-priority profile that lies in its registered profile null is falsely qualified, bounded by the panel false-qualification budget 1/200
- the selected adequate profile fails the confirmation conjunction, bounded by 19/400 by the same per-cell allocation on the confirmation split

**The binding claim holds only under this least-favourable configuration.**

- I0 passes
- at least one selectable profile has every applicable atomic-cell success probability at or above that cell's registered p1
- any higher-priority profile that is not adequate lies in its registered profile null, meaning at least one of its required cells is at or below that cell's p0
- development and confirmation follow the frozen selection order with no rescue and no substitution
- the selected adequate profile remains at or above p1 on the confirmation-generating distribution

**Not covered by the power guarantee.**

- profiles whose cell success probabilities lie in the indifference region strictly between p0 and p1
- distribution shift between the development and confirmation generating distributions
- I0 failure
- an invalid or unregistered sampling frame
- protocol deviations of any kind

**Vocabulary.** `target_power` is per atomic cell. `profile_stage_power_floor` is a
union-bound lower bound under arbitrary cell dependence.
`study_end_to_end_power_floor` carries the stated least-favourable configuration.
Selection-return and confirmation operating characteristics are named separately and are
never called power. a STOP outcome reports the realized registered gate outcome in that run. It is not a proof that no population-level adequate interface exists and is never a model-capability conclusion.

### The registered sampling frame

within each gate-bearing atomic cell, base-item units or base-item contrast-cluster units are independent draws WITH REPLACEMENT from that cell's registered generator distribution; the deterministic model and scorer map each independently drawn unit to exactly one Bernoulli success indicator.

| Level | Identified by | Excludes |
| --- | --- | --- |
| sampling cell | split, gate or component, stratum or operation-family x depth, contrast ID where applicable | interface profile, checkpoint role |
| evaluation cell | one sampling cell x one applicable profile x one applicable role | - |

One iid item stream is drawn per sampling cell and reused across its applicable
evaluation cells. Every evaluation cell is therefore marginally iid Bernoulli, while
evaluation cells sharing sampled items may be dependent. That dependence is expressly
allowed and is handled by the arbitrary-dependence bounds above.

- Development sampling cells: **17**; confirmation sampling cells: **17**.
- Draws are **with replacement**. Duplicate generator tuples are legitimate draws and
  **must be retained**; redrawing for uniqueness, difficulty, balance or model response
  is prohibited.
- Every sampled parameter carries an exact rational weight and every parameter's weights
  sum to exactly one.
- Validity predicates are deterministic and evaluated before any model operation; every
  registered support satisfies them by construction, so the registered rejection
  probability is exactly `0`.
- Development, confirmation and future `P3-Q` supports are physically disjoint by the
  registered outcome-blind namespace partition of the generator key, frozen before any
  seed draw.
- The K5 baseline nuisance state has a **32**-state support with exact weight
  `1/32` per state, drawn iid with replacement. `n` is no longer required
  to be a multiple of the support size.
- **No seed exists and no bank row exists.** Seed values, the generator implementation
  blob and the realized bank are `null`, meaning *not yet selected*, not zero.

**Exact-binomial validity holds exactly under these conditions.**

- the n units of the evaluation cell are the images of n iid draws from that cell's registered generator distribution
- the scorer is a deterministic function of the drawn unit and the pinned checkpoint, so each unit yields exactly one Bernoulli indicator with a common success probability
- no unit is redrawn, filtered, deduplicated or reordered on any post-draw property
- the null and the alternative are statements about that cell's registered generating distribution
- the split namespace of the cell is disjoint from every other split

if any gate-bearing atomic cell lacks a complete generator distribution, or would require an adaptive post-draw choice, the design fails closed for that cell. It is not silently downgraded to descriptive and no exact-binomial validity is claimed for it.

### The total state machine

`I0` is a **global precondition**, evaluated before and outside profile adequacy. Every
event has exactly one legal next state and every registered terminal state is reachable.

| From | Event | Next |
| --- | --- | --- |
| `Q0_INSTRUMENT` | all fixtures pass | `Q1_DEVELOPMENT` |
| `Q0_INSTRUMENT` | any fixture fails | `STOP_INSTRUMENT_DEFECT` |
| `Q0_INSTRUMENT` | error | `STOP_INSTRUMENT_DEFECT` |
| `Q0_INSTRUMENT` | ambiguity | `STOP_INSTRUMENT_DEFECT` |
| `Q1_DEVELOPMENT` | completed validly | `Q2_SELECTION` |
| `Q1_DEVELOPMENT` | protocol or integrity error | `STOP_DEVELOPMENT_INTEGRITY_ERROR` |
| `Q2_SELECTION` | a profile is selected | `Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY` |
| `Q2_SELECTION` | no profile is eligible and applicable | `STOP_NO_SELECTABLE_INTERFACE_REMAINS` |
| `Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY` | authority granted and conjunction passes | `CALIBRATED_PENDING_SEPARATE_SUBSTANTIVE_AUTHORITY` |
| `Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY` | authority granted and any applicable cell fails | `STOP_CONFIRMATION_FAILED` |
| `Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY` | authority granted and an error or ambiguity occurs | `STOP_CONFIRMATION_SPENT_ON_ERROR` |

| Terminal state | Claim |
| --- | --- |
| `STOP_INSTRUMENT_DEFECT` | the instrument is defective. NOTHING was measured about any interface. This is never a statement about any interface or any model. |
| `STOP_DEVELOPMENT_INTEGRITY_ERROR` | a protocol or integrity error occurred during development. This is a fail-closed integrity stop and is never reinterpreted as a scientific gate failure. |
| `STOP_NO_SELECTABLE_INTERFACE_REMAINS` | no candidate profile passed the registered development gates in that realized run. It is not a proof that no population-level adequate interface exists and is never a model-capability conclusion. |
| `STOP_CONFIRMATION_FAILED` | the selected profile did not replicate on the confirmation split. The split is spent and no substitution or reselection is permitted. |
| `STOP_CONFIRMATION_SPENT_ON_ERROR` | the confirmation split was spent on an error or ambiguity. It may not be re-read. |
| `CALIBRATED_PENDING_SEPARATE_SUBSTANTIVE_AUTHORITY` | the named interface cleared the registered gates for the named tasks and roles, conditional on the single selected profile. No mechanistic authority is created. |

The sixteen-row profile-eligibility map is retained as the `Q2_SELECTION` subtable that
applies only once `I0` has passed. It is not the whole state machine.

### The paired equivalence procedure is retired

The Tango (1998) score-based procedure for the difference of paired proportions is
**`RETIRED FROM EVERY DECISION ROLE`**. It carries no gate authority, is not the I3 secondary
criterion, and plays no part in profile eligibility, development selection, confirmation,
claim language, equivalence margins, critical values, the four-point discordance grid, any
rescue path or any ranking weight.

- **Why.** Findings `S3MR-004` and `S3MR-005` recorded that draft-v0.2 asserted the procedure was conservative and had verified size, while the independent recalculation found its exact type-I error **exceeded** its nominal one-sided level at tested configurations, and that the verification grid tested four points and generalised from them.
- **The operator resolution is removal, not recalibration.** The procedure is not necessary for the primary construct, which is an item-level conjunction, so it is withdrawn from inferential use altogether.
- **The false assertion is withdrawn.** The draft-v0.2 claim that the procedure's exact type-I error does not exceed its nominal one-sided level is withdrawn as incorrect. It is not repaired, re-scoped or re-argued; it is withdrawn.
- **What survives.** Purely **descriptive** paired 2x2 summaries: the paired table of variant-1 correctness by variant-2 correctness, the raw discordance count and rate, and the paired accuracy difference. These carry no null, no alpha, no p-value, no critical value, no equivalence margin, no pass or fail, no rescue path and no ranking weight.
- **Historical evidence is preserved unedited** at `studies/study3/analysis/independent_methods_recalculation.py`, its committed tables, and `studies/study3/reviews/v0_2_independent_methods_review.json`. The reviewer's recalculation is immutable historical evidence and is not edited, re-run, re-derived or superseded by this amendment.
- **Question for the second reviewer.** Does retiring the paired aggregate-equivalence procedure from every decision role fully remove the size-control defect recorded in `S3MR-004` and `S3MR-005`, or does a residual decision path remain anywhere in the amended protocol?
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`

### The pre-registered development selection map

Fixed before any data exists and enumerated exhaustively. `S4` is never selectable under any
outcome. The denominator is `3` in every row.

| S3 multi-token activated | All applicable components passed | Eligible | Selected | STOP | Denominator |
| --- | --- | --- | --- | --- | --- |
| `false` | S1=false, S2=false, S3=false | _none_ | _none_ | `true` | 3 |
| `false` | S1=true, S2=false, S3=false | S1 | `S1` | `false` | 3 |
| `false` | S1=false, S2=true, S3=false | S2 | `S2` | `false` | 3 |
| `false` | S1=true, S2=true, S3=false | S2, S1 | `S2` | `false` | 3 |
| `false` | S1=false, S2=false, S3=true | _none_ | _none_ | `true` | 3 |
| `false` | S1=true, S2=false, S3=true | S1 | `S1` | `false` | 3 |
| `false` | S1=false, S2=true, S3=true | S2 | `S2` | `false` | 3 |
| `false` | S1=true, S2=true, S3=true | S2, S1 | `S2` | `false` | 3 |
| `true` | S1=false, S2=false, S3=false | _none_ | _none_ | `true` | 3 |
| `true` | S1=true, S2=false, S3=false | S1 | `S1` | `false` | 3 |
| `true` | S1=false, S2=true, S3=false | S2 | `S2` | `false` | 3 |
| `true` | S1=true, S2=true, S3=false | S2, S1 | `S2` | `false` | 3 |
| `true` | S1=false, S2=false, S3=true | S3 | `S3` | `false` | 3 |
| `true` | S1=true, S2=false, S3=true | S3, S1 | `S3` | `false` | 3 |
| `true` | S1=false, S2=true, S3=true | S2, S3 | `S2` | `false` | 3 |
| `true` | S1=true, S2=true, S3=true | S2, S3, S1 | `S2` | `false` | 3 |

**No interface profile is selected in draft-v0.4.** The map is published so that the
selection is determined before any data exists; running it requires data that does not exist
and an authority that has not been granted.

### Label-selection uniformity - diagnostic only

| n | Unit of n | Labels | Expected per label | Two-sided mass | Acceptance band |
| --- | --- | --- | --- | --- | --- |
| 256 | scored rows in the cell | 4 | 64.0 | 0.001250000000 | 43 to 87 |
| 512 | scored rows in the cell | 4 | 128.0 | 0.001250000000 | 97 to 160 |
| 1024 | scored rows in the cell | 4 | 256.0 | 0.001250000000 | 212 to 301 |

`DIAGNOSTIC_NUISANCE_REPORT_ONLY`. This criterion carries no gate authority, no eligibility
authority, no selection authority and no confirmation authority. The operator amendment authority, section 5, records
that draft-v0.2 declared it a gate and simultaneously said it must never be reclassified as
diagnostic, while its own components table omitted it from the gate list, so the document
contradicted itself about whether a profile could be eliminated by it. draft-v0.4 resolves
the contradiction in the direction that **eliminates no profile on a nuisance criterion**.
It applies to label-bearing profiles only and is `not_applicable` to `S2` and `S3`.

### Descriptive Clopper-Pearson bounds - tail convention named

Finding `S3MR-019` recorded that draft-v0.2 filed a two-sided convention under a field named
one-sided. Every bound below names the mass it actually consumes: the reported quantity is a
**lower** bound consuming **half** of a two-sided simultaneous mass.

| Simultaneous cells | n | Unit of n | Successes | Two-sided simultaneous mass | Lower-tail mass consumed | Lower bound |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | 256 | independent units in the cell | 250 | 0.001250000000 | 0.000625000000 | 0.928608 |
| 4 | 256 | independent units in the cell | 245 | 0.001250000000 | 0.000625000000 | 0.900046 |
| 4 | 128 | independent units in the cell | 120 | 0.001250000000 | 0.000625000000 | 0.838150 |
| 8 | 256 | independent units in the cell | 250 | 0.000625000000 | 0.000312500000 | 0.925020 |
| 8 | 256 | independent units in the cell | 245 | 0.000625000000 | 0.000312500000 | 0.895992 |
| 8 | 128 | independent units in the cell | 120 | 0.000625000000 | 0.000312500000 | 0.831111 |
| 12 | 256 | independent units in the cell | 250 | 0.000416666667 | 0.000208333333 | 0.922957 |
| 12 | 256 | independent units in the cell | 245 | 0.000416666667 | 0.000208333333 | 0.893672 |
| 12 | 128 | independent units in the cell | 120 | 0.000416666667 | 0.000208333333 | 0.827088 |
| 24 | 256 | independent units in the cell | 250 | 0.000208333333 | 0.000104166667 | 0.919488 |
| 24 | 256 | independent units in the cell | 245 | 0.000208333333 | 0.000104166667 | 0.889786 |
| 24 | 128 | independent units in the cell | 120 | 0.000208333333 | 0.000104166667 | 0.820356 |

`DESCRIPTIVE_ONLY_NO_GATE_AUTHORITY`.

### Sample sizes, each with its unit

| Gate | n | Unit of n |
| --- | --- | --- |
| I1a | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 |
| I1b | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 |
| I2 | 214 | base items per primitive-family cell |
| I3 | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 |
| I4 | 448 | RP base items per operation-family x depth cell per candidate profile |

- **Confirmation sizes.** conservative reuse of the development sizes at the confirmation component level, on the physically disjoint one-shot split; they are NOT minimal confirmation sizes
- **Withdrawn.** WITHDRAWN. The draft immediately preceding this one carried n = 256 and n = 128 against a per-cell power target of 9/10. This draft registers a per-cell target derived from the binding end-to-end design (S3MR2-002), which requires larger sizes. The withdrawn values appear in no active field.
- **Search rule.** every positive integer is searched; draft-v0.3 restricted admissible n to multiples of the complete-block size 32, and that restriction is retired with the deterministic block assignment it came from (S3MR2-010)

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
| `sequence_scorings` | `0` |
| `local_pytest_runs` | `0` |
| `decision_bearing_local_statistical_runs` | `0` |

**All counters zero:** `true`

**Local operations disclosure.** No local `pytest` run and no local decision-bearing
statistical calculation was performed in this round. The derivation script was executed
locally in `--emit` mode to assemble the committed tables artifact, and in `--check` mode as
a non-authoritative syntax and self-consistency check. Neither local run is evidence. All
committed validation evidence comes from clean CPU-only Azure Container Registry jobs bound
to exact commits.

**Prohibited without a new authority**

- any model download, weight load or tokenizer construction
- any forward pass, sequence scoring or generation
- any activation extraction or probe
- any patching, ablation or lens operation
- any GPU job
- any bank generation or seed draw
- any evidence-ledger row
- any Phase 1.0D or RQ2/S4 operation
- any Study 2 state change
- any interface selection or positive-reference selection
- any confirmation-split access

### Projected future operations, by work stream

Planning arithmetic only. This authorises nothing, approves no budget and creates no execution
authority. Every count is derived by `studies/study3/analysis/design_statistics.py` from the
registered sample sizes and cell structure; no total is hand-copied.

| Work stream | Rendered rows | Scored rows | Sequence-level evaluations | Generation calls | Generated tokens |
| --- | --- | --- | --- | --- | --- |
| `deterministic_I0_fixtures` | 502 | 502 | 0 | 0 | 0 |
| `target_role_development` | 33,543 | 33,543 | 33,543 | 0 | 0 |
| `positive_reference_external_P3Q` | `null` | `null` | `null` | `null` | `null` |
| `RP_I4_under_candidate_profiles` | 3,584 | 3,584 | 3,584 | 0 | 0 |
| `selected_profile_one_shot_confirmation` | 27,856 | 27,856 | 27,856 | 0 | 0 |
| `S4_diagnostic_generation` | 26,064 | 26,064 | 417,024 | 26,064 | 417,024 |

**Per-profile target-role development.**

| Profile | Base items | Contrast clusters | Rows per target role | Target roles | Rows |
| --- | --- | --- | --- | --- | --- |
| `S1` | 1,254 | 3,717 | 8,688 | 3 | 26,064 |
| `S2` | 841 | 826 | 2,493 | 3 | 7,479 |
| `S3` (0 incremental; reuses the S2 logits) | 841 | 826 | 2,493 | 3 | 7,479 |

`S3` adds **0** incremental rendered rows, scored rows and sequence evaluations, and that holds
only under the registered conditions:

- a jointly single-token registered answer domain
- an identical prompt prefix to S2
- reuse of the identical restricted-vocabulary logit vector S2 already read
- a CPU-only rescoring contract that performs no additional model evaluation

**`S4` generative cost is mapped, not null.** a generation of up to the registered token bound is not zero model evaluation. Autoregressive decoding performs one prefill evaluation and up to one incremental decode evaluation per additional emitted token. draft-v0.3 published a null forward-pass count for this stream (S3MR2-005).

- generation calls: **26,064**
- registered maximum new tokens per generation: **16**
- generated-token upper bound: **417,024**
- sequence-level prefill evaluations: **26,064**
- incremental decode evaluations upper bound: **390,960**
- total sequence-level model-evaluation equivalents upper bound: **417,024**

A sequence-level evaluation is **never** equated with a runtime batched forward call; batch
packing is a future execution property measured separately.

**`I0` fixture units.** one base_item_contrast_cluster is ONE base item rendered in exactly two variants, so the cluster-derived base-item count equals the cluster count and the rendered-row count is the cluster count times the variants per cluster. draft-v0.3 filed the rendered-row count under the base_item unit (S3MR2-009).

- base-item contrast clusters: **232**
- cluster-derived base items: **232**
- cluster rendered rows: **464**
- non-cluster fixture rows: **38**
- rendered rows = scored rows: **502**

**No grand total is published.** the positive-reference P3-Q stream is unresolved under OD2 and is null, not zero. A grand total would silently treat that null as zero.

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

**What a pass permits**

- o
- n
- l
- y
-  
- a
-  
- n
- e
- w
-  
- o
- p
- e
- r
- a
- t
- o
- r
-  
- d
- e
- c
- i
- s
- i
- o
- n
-  
- a
- b
- o
- u
- t
-  
- w
- h
- e
- t
- h
- e
- r
-  
- t
- o
-  
- d
- e
- s
- i
- g
- n
-  
- a
-  
- l
- a
- t
- e
- r
-  
- s
- u
- b
- s
- t
- a
- n
- t
- i
- v
- e
-  
- p
- r
- o
- t
- o
- c
- o
- l

**What a pass does not permit**

- reopening Study 2
- authorizing Study 4 or Study 2 v2
- behavioral confirmation
- activation extraction
- patching
- probes
- ablations
- lens work

**The I3 claim ceiling.** Gate I3 registers nine one-factor pairwise contrast cells. Passing all of them supports a claim about each registered presentation factor SEPARATELY and supports no claim about combined or interacting presentation changes, which are outside the Study 3 claim ceiling.

**The confirmation claim is conditional.** the confirmation claim is explicitly conditional on the single development-selected interface profile and makes no statement about the profiles that were not selected.

**No self-approval.** this document does not declare its own protocol correct. Every repair is proposed resolved subject to a third independent methods review.


## Study 1 and Study 2

Study 1's frozen raw-completion, no-chat-template, single-token E0 surface yielded too few behaviorally eligible items to populate confirmation. Parser-v2 separately failed its locked gate, while parser-v3 remained nonauthoritative. These facts motivate prospective interface validation but do not establish that parsing caused E0's eligibility collapse.

_motivation only; this does not establish that parsing caused the collapse_

Study 2 remains closed and unchanged. Its post-hoc response-pattern diagnostic remains zero-authority motivation only.

_closed and unchanged; zero-authority motivation only_

## Unresolved operator decisions

| Decision | Status | Blocking | Disposition |
| --- | --- | --- | --- |
| OD1 | `resolved` | `false` | retain RT, RL and RI. All three are required for the later distillation, lineage and instruction contrast, and each gate is evaluated per role. |
| OD2 | `unresolved` | `true` | UNRESOLVED. Candidate dossier only. No positive reference is selected, preferred, pinned, downloaded, tokenized, loaded, prequalified or ranked. The RP canonical qualification interface and the RP-specific I4 wrapper must be registered by a separate operator authority before P3-Q and before I4. draft-v0.4 makes no progress on OD2 and does not attempt to. It registers only the binding P3-Q/I4 ordering constraint that the later OD2 authority must respect. |
| OD3 | `resolved` | `false` | retain S4 only as a non-selectable diagnostic. It never enters admissibility and can never be selected. |
| OD4 | `resolved` | `false` | exactly three one-factor renderings: baseline, separator-only and instruction-wording-only. The answer cue is held constant across all three. |
| OD5 | `resolved_subject_to_independent_review` | `false` | Exact-binomial primary design throughout. The study-level development screening level is the exact rational 1/200. The per-profile development component level is the exact rational 1/600, obtained by dividing the study-level level by the fixed selectable-profile denominator 3. Within a profile the components form an intersection-union conjunction, so no further within-profile Bonferroni correction is applied. The confirmation component level is the exact rational 1/200 on a physically disjoint one-shot split entered by exactly one pre-selected profile, so it carries no across-profile correction. Every decimal in the protocol is a rendering of the exact rational, which is the policy. The Tango paired aggregate-equivalence procedure is retired from every decision role, so no equivalence margin, critical value or discordance grid remains to be chosen. The I4 competence floor is p0 = 0.8 with p1 = 0.9. |
| OD6 | `resolved_subject_to_third_independent_review` | `false` | Exactly one I3 floor is active: p0 = 9/10, with p1 = 97/100 as the lowest alternative of interest, a per-cell power target derived from the binding end-to-end design, and n = 413 base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3. p0 = 0.95 is deleted from every active field. draft-v0.4 additionally narrows the indicator to J_joint_correct, so the floor is a joint-correctness level and not a presentation contrast. |
| OD7 | `resolved` | `false` | yes, and it has been carried out once. The independent methods review of draft-v0.2 returned STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED. A THIRD independent methods review of draft-v0.4 is now mandatory before freeze and before any bank construction or seed draw. The drafting party may not adjudicate its own amendment. |
| OD8 | `resolved_in_part` | `false` | no chat template for RT, RL or RI on S1, S2 or S3. S4 uses each role's native template or explicitly records its absence. The RP canonical qualification wrapper and the RP-specific I4 wrapper remain part of OD2 and must be frozen before P3-Q and I4. No cross-role byte parity is claimed where native wrappers differ. |

**Blocking decisions:** `OD2`

**`OD5` and `OD6` are resolved by this amendment; `OD2` is not.** `OD5` and `OD6` were
operator decisions about statistical policy, and the operator has now made them: an
exact-binomial primary design with a fixed selectable-profile denominator, and a single I3
floor. `OD2` is a decision about which external checkpoint to use as the positive capability
reference. Making it would be a selection, and no selection is authorised in this round, so
`OD2` remains `unresolved` and `blocking`.


## Required next action

second bounded independent methods review of the amended statistical, contrast, selection and confirmation packet at studies/study3/analysis/independent_methods_review_packet_v0_3.md

This draft is **not** frozen, **not** authorized for execution, and carries **no** authority
for bank construction, seed drawing, tokenizer construction, model download, model loading,
forward passes, generation, activation extraction, probing, patching, ablation, lens work or
any Gate A or Stage B-D operation.

| Flag | Value |
| --- | --- |
| `frozen` | `false` |
| `execution_authorized` | `false` |
| `bank_authorized` | `false` |
| `seed_authorized` | `false` |
| `model_operations_authorized` | `false` |
| `winner_selected` | `false` |
| `positive_reference_selected` | `false` |
| `confirmation_access_authorized` | `false` |

**State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW`

**No self-approval.** This document is the drafting party's amendment. It states that repairs
are **proposed resolved subject to independent review**. It does not, anywhere, declare the
amended protocol correct. That determination belongs to the second independent methods
reviewer.


## The draft-v0.6 scoring boundary

This section is an **additive amendment**. It supersedes nothing in the sections above and
edits no draft-v0.5 field. The draft-v0.5 rendering registry is preserved byte-for-byte as
history, and the state, draft version and routing recorded above are unchanged. The
authoritative record of this amendment is the `scoring_boundary_v0_6` block of
interface_calibration_protocol_draft.json, and its operator record is at
studies/study3/reviews/v0_6_operator_amendment.md.

Authority: studies/study3/prompts/study3_v0_6_p0_r1_authority.md.
Disposition: `PROPOSED_RESOLVED_SUBJECT_TO_FINAL_FOCUSED_REVIEW`. This document does not
declare the amended scoring boundary correct.

### Why the boundary moved

Stage P0-T published an immutable observation: under every pinned role tokenizer, each
registered `S2`/`S3` candidate surface `" 0"` through `" 9"` is **two** tokens, not one. The
draft-v0.5 rule read one next-token logit vector at the single position immediately after
the answer cue and restricted it to ten registered content token IDs. That rule is not
implementable as written. draft-v0.6 changes where the decision statistic is read, and
changes no visible byte a model would see.

### The registered rule

Every complete candidate factors as `candidate_d = common_prefix || discriminant_d`. The
candidate set is eligible only if all five registered conditions hold: every complete
candidate is exactly two tokens; the first token is identical for all ten candidates; that
common token decodes byte-exactly to the registered leading U+0020; the second token IDs are
pairwise distinct and map byte-exactly to `0` through `9` in registered order; and no BOS,
EOS, chat template, normalization, padding, truncation or implicit whitespace transformation
participates in the factorization.

For `S2`, the scoring context is the registered prompt token IDs followed by the verified
common-prefix token, formed by concatenation and never by re-encoding a concatenated string.
One ordinary prefill evaluation is performed on that context and the next-token logit vector
is read only at the ten verified discriminant token IDs. The deterministic restricted argmax
is mapped back to the complete registered candidate surface. For `S3`, the exact `S2`
discriminant-position logit vector is reused on CPU, adding zero model evaluations. `S1` and
`S4` are unchanged.

The common-prefix token is a **teacher-forced candidate prefix**. It is not a
prompt-rendering change, it is not a generated token, and it is not a separate
sequence-level model evaluation. Scoring the shared first token, treating the two-token
candidate as one token, summing unrelated positions, using free generation and introducing a
new calibration parameter are all **prohibited**.

### The ranking identity

For every prompt `x` and candidate digit `d`, with `u` the common token and `v_d` the unique
digit token, `P(u, v_d | x) = P(u | x) * P(v_d | x, u)`. Because `P(u | x)` does not depend
on `d`, it is a strictly positive common factor of all ten complete-candidate probabilities
and cancels from the restricted ranking, so
`argmax_d P(u, v_d | x) = argmax_d P(v_d | x, u)`. This is an exact factor cancellation and
not an approximation. It is asserted mechanically on every scored two-token row.

The identity **must not** be extended to arbitrary multi-token candidates, to candidates of
unequal length, to candidates without a common prefix, to summed or length-normalised log
probabilities, to free generation, or to any tokenizer that is not separately pinned and
verified. The registered digit-order tie break is preserved unchanged.

### The token identities are derived, not transcribed

The common-prefix token and the ten discriminant token IDs are recovered from the immutable
published P0-T result and the frozen pilot corpus by
studies/study3/pilot/p0_r1/p0_r1_factorization.py, which performs **zero** tokenizer encodes
and imports no tokenizer library, and they are required to be uniquely determined by that
evidence.

### Token accounting

Both `registered_prompt_token_count` and `scoring_context_token_count` are recorded for `S2`
and `S3`. The extra teacher-forced token changes token processing, not the number of
sequence-level prefill evaluations. No registered sample size, pass count, budget, floor or
operation projection moves, because the new boundary changes no cell, no contrast
applicability, no independent unit, no null, no alternative, no alpha and no decision rule.
Every such quantity is recomputed from studies/study3/analysis/design_statistics.py rather
than carried forward, and the two quantities that do change are surfaced separately in the
operator amendment record.
