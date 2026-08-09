# Study 3 draft-v0.5 bounded operator amendment

Record class: operator amendment. This document is **not** a methods review
and does not adjudicate itself. It is drafted by the party that holds the v0.5
operator authority, and its only legal successor is a fresh-session **fourth
independent methods review of published draft-v0.5 by a party that did not
draft it**.

## 1. Round identity

| field | value |
| --- | --- |
| round | Study 3 draft-v0.5 bounded operator amendment |
| state | `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW` |
| responds to | `studies/study3/reviews/v0_4_independent_methods_review.md` |
| authority | `studies/study3/prompts/study3_v0_5_design_amendment_authority.md` |
| authority sha256 | `b9f0023052c9056de1707ba64a8686a8df05d260cbf7aae0673c31d2dc3aadc6` |
| authority bytes | 27458, 400 LF, 0 CR, trailing newline present |
| starting commit | `79bcc20244ab55045ba1c5d778d829d4caac3dd3` |
| starting tree | `3855a579d0174d2c45587cba248e96d42c319664` |
| evidence ledger | unchanged, still ends at `EV-0016` |

## 2. Scope boundary

This amendment is a design round only. Each of the following is recorded false
in the machine-readable record and is enforced by its schema:

- `accesses_confirmation_material`: **false**
- `authorizes_execution`: **false**
- `begins_the_fourth_review`: **false**
- `creates_a_seed_or_bank`: **false**
- `creates_draft_v0_6`: **false**
- `freezes_study3`: **false**
- `resolves_od2`: **false**
- `resolves_ur_22`: **false**
- `runs_a_tokenizer_or_model`: **false**
- `selects_an_interface`: **false**
- `selects_or_inspects_a_positive_reference`: **false**
- `starts_a_feasibility_pilot`: **false**
- `writes_scientific_evidence`: **false**

Every operation counter is zero, every authority flag is false, and the bank,
seed, result and evidence lists are empty. No tokenizer, checkpoint, model or
confirmation material was accessed.

## 3. Closure matrix for the ten `S3MR3-*` findings

Every row below traces to normative bytes, at least one positive assertion and
at least one relevant negative mutation. The schema of the machine-readable
record refuses a row that cites no normative field, no committed test or no
negative mutation, so no finding can be closed by prose alone.

| finding | severity | closure status |
| --- | --- | --- |
| `S3MR3-001` | BLOCKING | `RESOLVED_BY_NOT_APPLICABLE_REREGISTRATION_AND_FULL_REDERIVATION` |
| `S3MR3-002` | MAJOR | `RESOLVED_BY_COMPONENT_LEVEL_CONFIRMATION_APPLICABILITY` |
| `S3MR3-003` | MAJOR | `RESOLVED_ACTIVE_TEXT_ALIGNED_HISTORY_PRESERVED` |
| `S3MR3-004` | MINOR | `RESOLVED_ENFORCEMENT_SCOPE_MATCHES_REGISTERED_SCOPE` |
| `S3MR3-005` | MINOR | `RESOLVED_S4_I4_REMOVED` |
| `S3MR3-006` | MINOR | `RESOLVED_NON_MACHINE_STATUS_REMOVED_FROM_STOP_STATES` |
| `S3MR3-007` | MINOR | `RESOLVED_NONMONOTONICITY_DISCLOSED_EXACT_N_REQUIRED` |
| `S3MR3-008` | MINOR | `RESOLVED_ROUND_REFERENCES_UPDATED` |
| `S3MR3-009` | MINOR | `RESOLVED_UNION_BOUND_CLAIM_ALIGNED` |
| `S3MR3-010` | MAJOR | `RESOLVED_DETERMINISTIC_RENDERING_SURFACE_REGISTERED` |

### S3MR3-001 (BLOCKING)

**Finding.** The K6-SEP contrast cell has no referent for the option-less selectable profiles S2 and S3, yet is registered applicable, counted and gate-bearing for both

**Starting evidence.** third independent methods review, new_findings[S3MR3-001], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** K6-SEP continues to mean the separator between a DISPLAYED OPTION LABEL and its DISPLAYED OPTION CONTENT. It remains applicable to the label-bearing profiles S1 and S4 and is recorded not_applicable for S2 and S3, which render neither. No profile-specific replacement separator is invented and no R-sep duplicate of R-base is rendered. not_applicable is never a pass, a zero effect, robustness evidence, a gate-bearing cell or a denominator member. S2 and S3 each carry exactly ONE genuine I3 contrast, K6-INSTR, and their per-profile I3 claim ceiling states joint robust correctness for that one registered pair only, subject to S3's existing conditional status. Applicability is now registered PER CONTRAST ID throughout, because family level cannot express the distinction. Every affected applicability list, cell census, gate truth-table row, claim ceiling, sampling and evaluation mapping, operation projection and test was re-derived rather than text-edited.

**Affected normative fields.**

- `i3_contrast_registry.k6_applicability.by_contrast`
- `gate_truth_table.rows[*].I3_K6`
- `interface_profiles[*].transformation_applicability.separator_rendering`
- `i3_contrast_registry.claim_ceiling_by_profile`
- `claim_ceiling.i3_single_genuine_contrast_profiles`

**Affected derived fields.**

- `studies/study3/analysis/design_statistics_tables.json :: gate_bearing_cell_counts`
- `studies/study3/analysis/design_statistics_tables.json :: power_architecture.m_max`
- `studies/study3/analysis/design_statistics_tables.json :: projected_operation_accounting`

**Verification.** the derivation recomputes the census from applicable CONTRAST IDS; S2 and S3 fall from 19 to 16 gate-bearing cells and from 2 to 1 applicable I3 contrast, while S1 -- the selectable profile that attains m_max -- is unchanged at 43, so m_max, the per-cell budget 19/17200, the per-cell target 17181/17200, the profile stage floor 381/400, the end-to-end floor 9/10 and every minimal size and pass count reproduce BY DERIVATION and not by preservation

**Committed tests.**

- `tests/test_study3_design.py :: test_per_profile_i3_applicability_and_claim_ceiling_are_exact`
- `tests/test_study3_design.py :: test_no_duplicate_r_sep_branch_exists_for_the_option_less_profiles`
- `tests/test_study3_design.py :: test_m_max_and_cell_counts_derive_from_the_truth_table`
- `tests/test_study3_rendering_registry_v0_5.py :: test_k6_sep_is_structurally_absent_for_the_option_less_profiles`

**Negative mutations that must be rejected.**

- K6-SEP is re-applied to an option-less profile
- K6 applicability returns to family level
- K6-SEP applicability widens beyond the label-bearing profiles
- an option-less claim ceiling regains K6-SEP
- R-sep is duplicated for an option-less profile
- separator rendering becomes applicable to an option-less profile

**Residual limitation.** S2 and S3 now rest on a single genuine I3 contrast each. That is a narrower evidential base than S1's nine, and it is disclosed rather than compensated: no pooling, rescue or substitute contrast is introduced, and S3 remains conditional under the single-token domain.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-002 (MAJOR)

**Finding.** The drafting derivation table still admits the never-selectable profile S4 to two confirmation rows, so the S3MR2-004 repair is absent from the artifact the protocol names as its derived source

**Starting evidence.** third independent methods review, new_findings[S3MR3-002], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** design_statistics_tables.json is regenerated only from the amended normative inputs, and confirmation applicability is emitted at COMPONENT level rather than as one family-level list. S4 appears in no confirmation applicability field; I1b and K5 confirmation applicability is restricted to S1; K6-SEP confirmation applicability excludes S2 and S3; K6-INSTR reflects the amended protocol exactly; I2 and I4 match the gate hierarchy and the profile contracts. A committed test binds every component-level field to the normative protocol and the rendering registry, and no row can imply that a never-selectable or not-applicable profile reaches confirmation.

**Affected normative fields.**

- `proposed_statistics.confirmation_applicability_rule`
- `proposed_statistics.confirmation_exact_binomial_gates[*].applicable_profiles`
- `proposed_statistics.confirmation_exact_binomial_gates[*].contrast_cell_applicability`

**Affected derived fields.**

- `studies/study3/analysis/design_statistics_tables.json :: confirmation_component_applicability`
- `studies/study3/analysis/design_statistics_tables.json :: confirmation_exact_binomial_components[*].component_applicability`

**Verification.** the derivation raises DesignDefect if S4 reaches any confirmation applicability field, and the committed test compares every published component list against the truth table intersected with the selectable profiles

**Committed tests.**

- `tests/test_study3_design.py :: test_i1b_and_k5_confirmation_applicability_is_limited_to_s1`
- `tests/test_study3_design.py :: test_s4_is_not_i4_applicable_never_selectable_and_absent_from_confirmation`
- `tests/test_study3_design.py :: _semantic_laws (component-level confirmation block)`

**Negative mutations that must be rejected.**

- K6-SEP enters confirmation for an option-less profile
- confirmation applicability returns to family level
- S4 re-enters a confirmation component
- I1b confirmation widened beyond S1

**Residual limitation.** confirmation applicability is still a design registration, not an observation. No confirmation material was accessed and the confirmation split remains physically unread.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-003 (MAJOR)

**Finding.** The retired J_both invariance construct and the withdrawn sample size 256 survive in active charter, README and handoff text, contradicting two explicit protocol claims

**Starting evidence.** third independent methods review, new_findings[S3MR3-003], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** The charter, the repository README, the studies README, the Study 3 README, the handoff, the protocol Markdown companion, the review packet, the status report and the traceability note are brought into one consistent draft-v0.5 vocabulary. Active text no longer describes J_both as current, claims invariance, equivalence or an absent presentation effect, publishes n = 256 or n = 128 as active sizes, or names the second or third review as pending. Superseded passages are retained only inside unambiguous historical records that state the version, its rejection and its non-current status; the review history is preserved and nothing is erased.

**Affected normative fields.**

- `proposed_statistics.active_claim_term_prohibition.scope`
- `proposed_statistics.active_claim_term_prohibition.historical_exemptions`

**Affected derived fields.**

- `reports/current_status.md`
- `studies/study3/README.md`

**Verification.** a committed parametrised test scans every reviewed prose path line by line, exempts only explicitly marked historical, retired, limitation-of-claim and prohibited-claim passages, and fails on any active occurrence of the retired construct, the withdrawn sizes or the prohibited presentation vocabulary

**Committed tests.**

- `tests/test_study3_design.py :: test_reviewed_prose_carries_no_active_retired_or_prohibited_language`
- `tests/test_study3_design.py :: test_the_withdrawn_sample_sizes_appear_in_no_active_field`

**Negative mutations that must be rejected.**

- a mutation moving retired language into active scope is rejected
- a round reference reverts to the second review

**Residual limitation.** append-only ledgers (docs/decision_log.md, docs/run_log.md, paper/methods_ledger.md) retain their original draft-v0.3 and draft-v0.4 entries verbatim. They are marked as superseded by later appended entries rather than rewritten, because rewriting them would destroy provenance.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-004 (MINOR)

**Finding.** The claimed enforcement of the active-claim term prohibition is narrower than the registered scope

**Starting evidence.** third independent methods review, new_findings[S3MR3-004], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** The registered scope is widened to name the research question, success statements, validation-target interpretations, gate questions, what_fails, what_passes, claim ceilings, routing documents, the handoff, the charter, the READMEs, the Markdown companion, the packet and the status report, and the enforcing scan is widened to match it exactly. Exemptions are explicit and auditable rather than a hand-picked subset, and a committed test asserts that the declared enforced path set and the enforced set are the same set.

**Affected normative fields.**

- `proposed_statistics.active_claim_term_prohibition.scope`
- `proposed_statistics.active_claim_term_prohibition.enforced_paths`
- `proposed_statistics.active_claim_term_prohibition.historical_exemptions`

**Verification.** the committed test asserts set equality between the declared enforced paths and the paths the parametrised scan actually visits, and a non-vacuity test proves the scan sees prohibited active language and exempts an explicitly historical passage

**Committed tests.**

- `tests/test_study3_design.py :: test_the_prohibition_enforcement_scope_matches_the_registered_scope`
- `tests/test_study3_design.py :: test_a_mutation_moving_retired_language_into_active_scope_is_rejected`
- `tests/test_study3_design.py :: test_active_claim_text_contains_no_presentation_effect_claim`

**Negative mutations that must be rejected.**

- the prohibition scope narrows to the protocol only
- the prohibition's historical exemptions are removed

**Residual limitation.** the scan is lexical. It enforces the registered vocabulary and the registered retired tokens; it cannot detect a prohibited claim expressed in unregistered words, and it is not a substitute for the independent reviewer's reading.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-005 (MINOR)

**Finding.** S4 still lists I4 among its applicable gates although every decision-bearing field records I4 as not_applicable to S4

**Starting evidence.** third independent methods review, new_findings[S3MR3-005], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** I4 is removed from interface_profiles[S4].applicable_gates. The contradiction is removed rather than qualified away.

**Affected normative fields.**

- `interface_profiles[S4].applicable_gates`

**Verification.** a committed assertion and a negative mutation; the independently derived census already gives S4 zero I4 cells, so no number depended on the stale entry

**Committed tests.**

- `tests/test_study3_design.py :: test_s4_is_not_i4_applicable_never_selectable_and_absent_from_confirmation`
- `tests/test_study3_design.py :: _semantic_laws (S4 gate list)`

**Negative mutations that must be rejected.**

- S4 gains I4 applicability

**Residual limitation.** none. S4 remains a never-selectable diagnostic and is excluded from every success union.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-006 (MINOR)

**Finding.** A stop state is registered in the gate truth table that the total state machine does not contain

**Starting evidence.** third independent methods review, new_findings[S3MR3-006], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** STOP_AWAITING_AUTHORITY is removed from gate_truth_table.legal_stop_states and is NOT added to the registered experimental state machine. The repository's pre-execution governance status is not an experimental stop state.

**Affected normative fields.**

- `gate_truth_table.legal_stop_states`

**Verification.** a committed assertion that the listed stop-state set equals the set of STOP terminals of the registered total state machine

**Committed tests.**

- `tests/test_study3_design.py :: test_the_state_machine_is_total_deterministic_and_fully_reachable`
- `tests/test_study3_design.py :: _semantic_laws (stop-state equality)`

**Negative mutations that must be rejected.**

- a non-machine stop state returns

**Residual limitation.** none. The machine itself was already total, deterministic and fully reachable; only the second artifact disagreed.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-007 (MINOR)

**Finding.** The per-cell power target is not monotone in n immediately above each registered sample size, and this is disclosed nowhere

**Starting evidence.** third independent methods review, new_findings[S3MR3-007], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** The registered smallest unrestricted positive integers and the exact-binomial test definitions are retained after fresh recalculation confirmed them under the amended applicability. Beside the search rule the design now discloses that exact-test power is locally non-monotone in n, and registers that execution must use the EXACT registered cell size and must never read it as 'at least n'. The registered minimum is not replaced by an eventual-monotonicity threshold, because fresh arithmetic shows the design is executable at exact n.

**Affected normative fields.**

- `proposed_statistics.local_power_nonmonotonicity`
- `proposed_statistics.local_power_nonmonotonicity_disclosure_window`
- `proposed_statistics.sample_sizes.search_rule`

**Affected derived fields.**

- `studies/study3/analysis/design_statistics_tables.json :: development_exact_binomial_components[*].local_power_nonmonotonicity`

**Verification.** the derivation enumerates, within a registered disclosure window above each minimum, every size at which the target fails again: 421-425 above n = 413, 215, 216 and 218 above n = 214, and 450-453 and 459 above n = 448. The disclosure is therefore non-vacuous and is asserted to be non-empty.

**Committed tests.**

- `tests/test_study3_design.py :: test_development_sample_sizes_are_the_smallest_meeting_the_target`
- `tests/test_study3_design.py :: _semantic_laws (non-monotonicity block)`

**Negative mutations that must be rejected.**

- an 'at least n' reading becomes permitted
- an eventual-monotonicity threshold replaces the registered minimum

**Residual limitation.** the enumeration is scoped to a registered window above each minimum and is not extrapolated beyond it. No claim is made about arbitrarily large n.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-008 (MINOR)

**Finding.** Active protocol fields still name a second independent methods review as the governing or pending review

**Starting evidence.** third independent methods review, new_findings[S3MR3-008], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** Active round references are updated so that draft-v0.5 awaits a FOURTH independent methods review. The historical question the retired-procedure record posed is marked answered by the completed second review rather than deleted.

**Affected normative fields.**

- `proposed_statistics.unresolved`
- `claim_ceiling.no_self_approval`
- `unresolved_operator_decisions[OD7].disposition`
- `status.review_state`
- `required_next_action`

**Affected derived fields.**

- `studies/study3/analysis/design_statistics_tables.json :: disposition_status`

**Verification.** a committed assertion on each field, plus a negative mutation reverting a round reference to the second review

**Committed tests.**

- `tests/test_study3_design.py :: test_protocol_declares_the_expected_draft_state`
- `tests/test_study3_design.py :: test_the_amendment_does_not_self_approve`

**Negative mutations that must be rejected.**

- a round reference reverts to the second review

**Residual limitation.** this amendment does not perform or prejudge the fourth review.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-009 (MINOR)

**Finding.** The end-to-end conclusion string is narrower than the union-bound argument that supports it

**Starting evidence.** third independent methods review, new_findings[S3MR3-009], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** The end-to-end union-bound conclusion is restated as returning and confirming AN ADEQUATE profile. Where several selectable profiles are adequate, the frozen priority order returns the highest-priority adequate profile. No claim of recovering an externally predesignated profile is made.

**Affected normative fields.**

- `power_architecture_v0_4.union_bound_proof`
- `power_architecture_v0_4.least_favourable_configuration.conditions`

**Affected derived fields.**

- `studies/study3/analysis/design_statistics_tables.json :: power_architecture.union_bound_terms`

**Verification.** a committed assertion on the conclusion string and on the multi-adequate branch, plus the independent recalculation of the three unioned terms under arbitrary dependence

**Committed tests.**

- `tests/test_study3_design.py :: test_the_union_bound_proof_contains_no_independence_assumption`
- `tests/test_study3_design.py :: _semantic_laws (union-bound block)`

**Negative mutations that must be rejected.**

- the union bound claims a predesignated profile

**Residual limitation.** the bound remains a lower bound under the registered least-favourable configuration only, and still covers neither the indifference region nor distribution shift.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

### S3MR3-010 (MAJOR)

**Finding.** The registered generator fixes the sampled parameters but not the deterministic rendering surface, so the two K6 cells are not instantiable without a later substantive design choice

**Starting evidence.** third independent methods review, new_findings[S3MR3-010], at commit 79bcc20244ab55045ba1c5d778d829d4caac3dd3

**Operator decision and repair.** A normative, machine-readable rendering registry and schema are created and registered as BINDING INPUTS, not illustrative examples. They fix UTF-8 encoding, LF and terminal newline policy and NFC normalization; one exact question-stem template for every registered operation family, depth and task stratum that can enter a gate-bearing cell; placeholder names, types, allowed surface forms, ordering, interpolation, escaping and rejection rules; exact option ordering and option-line grammar for S1 and S4; exact label alphabets and label-to-content separators; exact instruction sentences for every applicable (profile, rendering) pair; the exact answer cue and the whitespace convention of every candidate surface; the exact raw-completion prompt template for S1, S2 and S3; the exact pre-wrapper message content for S4 and the boundary to any role-native wrapper; the deterministic tie-break order and the exact scored candidate surfaces; a full (profile, rendering, contrast) applicability table; and a cryptographic identity for the registry and every normative template asset. K6-SEP uses the exact ASCII literals ': ' for R-base and ' = ' for R-sep with every other prompt byte identical; K6-INSTR registers two exact, semantically co-referential instruction strings per applicable profile with the answer cue and every other byte identical.

**Affected normative fields.**

- `rendering_surface_v0_5`
- `counterbalancing_design.k6_renderings.registered_surface`
- `task_strata[K6].registered_surface`

**Verification.** deterministic model-free fixtures instantiate every applicable profile/rendering/contrast branch, prove byte difference within every applicable pair, prove structural absence rather than duplication of K6-SEP for S2 and S3, prove single-factor isolation, and reject byte-identical pairs, unregistered substitutions and missing template branches

**Committed tests.**

- `tests/test_study3_rendering_registry_v0_5.py`
- `tests/test_study3_design.py :: test_no_duplicate_r_sep_branch_exists_for_the_option_less_profiles`

**Negative mutations that must be rejected.**

- the rendering registry is demoted to an illustrative example
- the rendering registry stops being a binding input
- the RP wrapper is filled in by v0.5
- token distinctness is treated as already tested
- a token-distinctness failure becomes a pass

**Residual limitation.** tokenizer distinctness is NOT tested in this round because no checkpoint or tokenizer may be accessed. A fail-closed pre-bank rule is registered instead: once checkpoints and tokenizers are separately authorised and pinned, every gate-bearing pair must produce distinct token-ID sequences for every role to which the cell applies, and failure makes that role/profile/contrast INELIGIBLE rather than a pass. That future rule does not resolve OD2. The RP canonical qualification wrapper remains explicitly null under OD2.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. Self-approved: **no**.

## 4. Carried-forward second-review closure matrix

No resolved item is reopened.

| finding | severity | status | note |
| --- | --- | --- | --- |
| `S3MR2-001` | BLOCKING | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | the J_joint_correct narrowing stands. draft-v0.5 closes the residual ACTIVE-TEXT residue under S3MR3-003 and the residual enforcement-scope gap under S3MR3-004, without reopening S3MR2-001. |
| `S3MR2-002` | BLOCKING | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | the binding end-to-end power architecture stands. draft-v0.5 re-derives every quantity from the amended per-contrast census and adds the local non-monotonicity disclosure under S3MR3-007. |
| `S3MR2-003` | MAJOR | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | the I4 applicability resolution stands. draft-v0.5 removes the single stale location under S3MR3-005 without reopening S3MR2-003. |
| `S3MR2-004` | MAJOR | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | draft-v0.4's repair of the confirmation applicability defect was present in the protocol but absent from its named derived table. draft-v0.5 closes that residual defect under S3MR3-002 without reopening S3MR2-004. |
| `S3MR2-005` | MAJOR | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | closed by draft-v0.4 and not reopened; draft-v0.5 introduces no change to it. |
| `S3MR2-006` | MAJOR | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | closed by draft-v0.4 and not reopened; draft-v0.5 introduces no change to it. |
| `S3MR2-007` | MAJOR | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | closed by draft-v0.4 and not reopened; draft-v0.5 introduces no change to it. |
| `S3MR2-008` | MINOR | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | closed by draft-v0.4 and not reopened; draft-v0.5 introduces no change to it. |
| `S3MR2-009` | MINOR | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | closed by draft-v0.4 and not reopened; draft-v0.5 introduces no change to it. |
| `S3MR2-010` | MAJOR | `CLOSED_BY_DRAFT_V0_4_AND_NOT_REOPENED_BY_DRAFT_V0_5` | the stochastic sampling model stands. draft-v0.5 adds the DETERMINISTIC half of the generator under S3MR3-010 without reopening S3MR2-010. |

## 5. Inherited first-review findings

| finding | severity | status after the second review | v0.5 residual |
| --- | --- | --- | --- |
| `S3MR-001` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-002` | BLOCKING | `PARTIALLY_RESOLVED_BY_DRAFT_V0_3` | still partial. draft-v0.5 is a bounded amendment that closes only the ten S3MR3-* findings; it does not advance this item, and the residual defect remains bounded and non-executable because no execution, bank, seed or confirmation authority exists. |
| `S3MR-003` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-004` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-005` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-006` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-007` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-008` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-009` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-010` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-011` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-012` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-013` | MAJOR | `PARTIALLY_RESOLVED_BY_DRAFT_V0_3` | still partial. draft-v0.5 is a bounded amendment that closes only the ten S3MR3-* findings; it does not advance this item, and the residual defect remains bounded and non-executable because no execution, bank, seed or confirmation authority exists. |
| `S3MR-014` | MAJOR | `PARTIALLY_RESOLVED_BY_DRAFT_V0_3` | still partial. draft-v0.5 is a bounded amendment that closes only the ten S3MR3-* findings; it does not advance this item, and the residual defect remains bounded and non-executable because no execution, bank, seed or confirmation authority exists. |
| `S3MR-015` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-016` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-017` | MAJOR | `PARTIALLY_RESOLVED_BY_DRAFT_V0_3` | still partial. draft-v0.5 is a bounded amendment that closes only the ten S3MR3-* findings; it does not advance this item, and the residual defect remains bounded and non-executable because no execution, bank, seed or confirmation authority exists. |
| `S3MR-018` | MINOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-019` | MINOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |
| `S3MR-020` | MINOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | resolved; draft-v0.5 does not reopen it. |

## 6. Unresolved item dispositions

| id | subject | status |
| --- | --- | --- |
| `UR-01` | I3 primary estimand identifiability | `CARRIED_FORWARD` |
| `UR-02` | I3 primary indicator semantics | `CARRIED_FORWARD` |
| `UR-03` | Family B per-profile alpha implementation | `CARRIED_FORWARD` |
| `UR-04` | false conservativeness assertion | `CARRIED_FORWARD` |
| `UR-05` | paired size control over the nuisance domain | `CARRIED_FORWARD` |
| `UR-06` | I3 primary floor and its feasibility | `CARRIED_FORWARD` |
| `UR-07` | I5 confirmation specification | `CARRIED_FORWARD` |
| `UR-08` | development profile-selection rule | `CARRIED_FORWARD` |
| `UR-09` | Family B denominator membership of S3 | `CARRIED_FORWARD` |
| `UR-10` | unit of every sample-size symbol | `CARRIED_FORWARD` |
| `UR-11` | I1a and I1b power shortfall | `CARRIED_FORWARD` |
| `UR-12` | circular committed verification and the grid test | `CARRIED_FORWARD` |
| `UR-13` | K5 and K6 stale generating-process text | `CARRIED_FORWARD` |
| `UR-14` | S3 projection and the undecomposed projection | `CARRIED_FORWARD` |
| `UR-15` | I4 multiplicity across families and depths | `CARRIED_FORWARD` |
| `UR-16` | residual pooling paths | `CARRIED_FORWARD` |
| `UR-17` | degenerate I3 rejection region | `CARRIED_FORWARD` |
| `UR-18` | paired margin practical-irrelevance justification | `CARRIED_FORWARD` |
| `UR-19` | Clopper-Pearson and uniformity tail conventions | `CARRIED_FORWARD` |
| `UR-20` | positive-reference dossier attribution | `CARRIED_FORWARD` |
| `UR-21` | stale Gate I1 labels | `CARRIED_FORWARD` |
| `UR-22` | external qualification interface for the positive reference | `UNRESOLVED` |

`OD2` and `UR-22` remain open. The `RP` canonical qualification wrapper and the
`RP`-specific `I4` wrapper remain explicitly null under `OD2`.

## 7. The historical narrative count mismatch, carried forward unedited

The second independent methods review's narrative disposition sentence reads
"Two BLOCKING and eight MAJOR methods defects remain". Its structured findings record 2 BLOCKING, 6 MAJOR and 2 MINOR, 
totalling 10. The review was not edited, the narrative sentence is quoted here
exactly once as immutable provenance, and the narrative count is never
propagated as the structured finding count. Status: `NON_DISPOSITIVE_HISTORICAL_NARRATIVE_COUNT_MISMATCH`.

## 8. External-validity bridge

`UM3-05` remains `UNRESOLVED_FUTURE_METHODS_PREREQUISITE`. The third review did not classify generator-local external
validity as a rejection driver. The claim ceiling is preserved:

- a pass applies only to the registered synthetic generator distributions and the named interface and checkpoint roles
- a pass does not establish adequacy on an unregistered substantive task distribution
- before the selected instrument is relied upon outside the generator, a new authority must register a bridge or validation design to the target substantive distribution using physically isolated new data
- descriptive results observed in a future Study 3 run may not be retrospectively upgraded into bridge evidence

No new gate and no new task bank is added in draft-v0.5 on this account.

## 9. Immutable objects this amendment did not edit

- `paper/claim_evidence_matrix.md`
- `paper/evidence_ledger.csv`
- `paper/limitations_ledger.md`
- `studies/study3/analysis/independent_methods_recalculation.py`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`
- `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`
- `studies/study3/analysis/independent_methods_recalculation_tables_v0_4.json`
- `studies/study3/analysis/independent_methods_recalculation_v0_3.py`
- `studies/study3/analysis/independent_methods_recalculation_v0_4.py`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/analysis/independent_methods_review_packet_v0_3.md`
- `studies/study3/design_receipt_v0_3.json`
- `studies/study3/design_receipt_v0_4.json`
- `studies/study3/methods_review_receipt_v0_2.json`
- `studies/study3/methods_review_receipt_v0_3.json`
- `studies/study3/methods_review_receipt_v0_4.json`
- `studies/study3/prompts/study3_v0_2_independent_methods_review_authority.md`
- `studies/study3/prompts/study3_v0_3_design_amendment_authority.md`
- `studies/study3/prompts/study3_v0_3_independent_methods_review_authority.md`
- `studies/study3/prompts/study3_v0_4_design_amendment_authority.md`
- `studies/study3/prompts/study3_v0_4_independent_methods_review_authority.md`
- `studies/study3/reviews/v0_1_operator_review.md`
- `studies/study3/reviews/v0_2_independent_methods_review.json`
- `studies/study3/reviews/v0_2_independent_methods_review.md`
- `studies/study3/reviews/v0_2_independent_methods_review.schema.json`
- `studies/study3/reviews/v0_3_independent_methods_review.json`
- `studies/study3/reviews/v0_3_independent_methods_review.md`
- `studies/study3/reviews/v0_3_independent_methods_review.schema.json`
- `studies/study3/reviews/v0_3_operator_amendment.json`
- `studies/study3/reviews/v0_3_operator_amendment.md`
- `studies/study3/reviews/v0_3_operator_amendment.schema.json`
- `studies/study3/reviews/v0_4_independent_methods_review.json`
- `studies/study3/reviews/v0_4_independent_methods_review.md`
- `studies/study3/reviews/v0_4_independent_methods_review.schema.json`
- `studies/study3/reviews/v0_4_operator_amendment.json`
- `studies/study3/reviews/v0_4_operator_amendment.md`
- `studies/study3/reviews/v0_4_operator_amendment.schema.json`
- `tests/test_study3_methods_review.py`
- `tests/test_study3_methods_review_v0_3.py`
- `tests/test_study3_methods_review_v0_4.py`

## 10. Self-approval prohibition and the sole legal successor

The drafting party does **not** claim draft-v0.5 is correct. Every repair is
recorded as `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`, and the determination belongs to the fourth independent methods reviewer.

All three independent methods reviews remain valid rejections and no review
artifact was edited.

The sole legal successor is a fourth bounded independent methods review of draft-v0.5, conducted in a fresh session by a party that did not draft draft-v0.5.
