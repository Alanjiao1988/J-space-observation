# Study 3 draft-v0.4 operator amendment record

**State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_4_COMPLETE_AWAITING_THIRD_INDEPENDENT_METHODS_REVIEW`

**Responds to:** `STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`, returned against the reviewed commit `2b36f5321d830ea6f70fff2b7bbca3cb93394046` and published at `bc98e5c98a2d4e273142c91497b7600ce751bade`.

**The drafting party does not claim draft-v0.4 is correct.** Every repair below is recorded as
`PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`. The determination belongs to the third independent reviewer.

**Both independent reviews remain valid rejections and neither was edited.** Every review artifact,
receipt, recalculation, authority copy and historical test module listed in this record is immutable
in this round and is unchanged.

## 1. The historical narrative count mismatch, recorded exactly

- Structured findings in the second review: **10** = 2 BLOCKING + 6 MAJOR + 2 MINOR.
- The immutable `disposition_basis` sentence says: "Two BLOCKING and eight MAJOR methods defects remain".
- Status: `NON_DISPOSITIVE_HISTORICAL_NARRATIVE_COUNT_MISMATCH`.
- Both blocking findings and the substantive sampling-model defect independently require amendment, so the disposition stands on either reading.
- The review is **not** edited to repair the mismatch, and the narrative MAJOR
  count in that sentence is **not propagated** as the structured finding count
  anywhere in draft-v0.4.

## 2. Closure matrix for the ten second-review findings

| Finding | Severity | Kind | Disposition |
| --- | --- | --- | --- |
| `S3MR2-001` | BLOCKING | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-002` | BLOCKING | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-003` | MAJOR | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-004` | MAJOR | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-005` | MAJOR | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-006` | MAJOR | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-007` | MAJOR | operator_decision_input | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-008` | MINOR | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-009` | MINOR | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |
| `S3MR2-010` | MAJOR | method | `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` |

### `S3MR2-001` - BLOCKING

**Reviewer finding.** The I3 primary indicator is mathematically identical to joint correctness and identifies no presentation effect, while the protocol's registered constructs, gate question and claim ceiling require a presentation-effect estimand

**Repair.** I3 is narrowed to JOINT ROBUST CORRECTNESS. The sole gate-bearing indicator is J_joint_correct, which is 1 exactly when both registered variants of the base-item contrast cluster are scored correct against the same unique registered ground truth. The estimand is p_joint = Pr(J_joint_correct = 1) over the registered item-generating distribution for that atomic contrast cell, which is a LEVEL and not a contrast. The null remains p_joint <= 9/10 and the lowest alternative of interest remains 97/100. No equivalence test, paired-effect test, non-inferiority margin, Tango procedure or discordance grid is introduced. The construct string, the gate question, the what_fails clause, VT6, VT7, the research question and the maximum pass claim are all rewritten to the quantity the design identifies, and the terms invariance, equivalence, no presentation effect, presentation-effect size, stable and unaffected by presentation are prohibited in every active claim, gate question, what_fails clause, validation-target interpretation and success statement. They survive only in clearly labelled historical, retired-procedure, limitation-of-claim and prohibited-claim text. J_inv, J_cor and the retired conjunction J_both remain only as historical names and descriptive audit quantities with status DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY and no reachable decision path.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (proposed_statistics.i3_indicators, i3_floor, i3_contrast_registry, claim_ceiling, validation_targets VT6 and VT7, research_question, gate_hierarchy I3)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/protocol/interface_calibration_protocol.schema.json`, `studies/study3/analysis/design_statistics.py`, `studies/study3/analysis/design_statistics_tables.json`

**Verification.** the committed derivation publishes the full ordered 4x4 outcome lattice and asserts that exactly one case family passes; the committed design test re-derives all 16 cases, asserts the descriptive-only status of the historical indicators, and asserts that no prohibited term appears in any active claim field

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-002` - BLOCKING

**Reviewer finding.** Profile-level, selection-level and confirmation-level power are neither derived nor registered anywhere, while an unqualified study-level target power of 9/10 is published and every component row asserts that it is met

**Repair.** A binding end-to-end power design is registered in power_architecture_v0_4. The type-I architecture is unchanged: study-level bound 1/200, fixed selectable-profile denominator 3, per-profile component level 1/600, intersection-union within a profile, one-shot confirmation at 1/200, S4 excluded from every success union. The type-II allocation is new: a per-stage profile false-negative budget of 19/400, divided across the registered maximum selectable-profile cell count m_max = 43, gives a per-cell false-negative budget of 19/17200 and a per-cell power target of 17181/17200. The profile stage power floor is 381/400 and the confirmation-conjunction floor is 381/400, both as union-bound LOWER BOUNDS under ARBITRARY cell dependence. With the panel false-qualification budget of 1/200 the study end-to-end power floor is 1 - 19/400 - 1/200 - 19/400 = 9/10. No independence between cells, profiles, roles or stages is used for any binding bound; any independence-based product is a labelled sensitivity analysis with no authority. The sample sizes are re-derived against the new per-cell target over every positive integer, retiring the 32-multiple admissibility restriction. The power vocabulary is corrected everywhere so that a per-cell target can never be read as family, profile, selection, confirmation or end-to-end power, the least-favourable configuration is stated, the uncovered indifference region is stated, and a STOP outcome is explicitly not a proof that no adequate interface exists.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (power_architecture_v0_4, proposed_statistics.target_power, retained_exact_binomial_gates, confirmation_exact_binomial_gates, sample_sizes)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/protocol/interface_calibration_protocol.schema.json`, `studies/study3/analysis/design_statistics.py`, `studies/study3/analysis/design_statistics_tables.json`

**Verification.** the committed derivation computes m_max from the truth table, derives 19/17200, 17181/17200, 381/400 and 9/10 in exact rational arithmetic, and derives each sample size as the smallest unrestricted positive integer meeting the target; the committed design test re-derives all of them and asserts the union-bound proof contains no independence assumption

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-003` - MAJOR

**Reviewer finding.** Gate I4's applicability to the never-selectable profile S4 is asserted in three artifacts and denied in two, and the operation projection silently follows the denial

**Repair.** I4 applies only to the selectable profiles S1, S2 and S3. S4 is not_applicable for I4 in the exact-binomial gate rows, the gate hierarchy, the gate truth table, the stage-1 component lists, the statistics tables and the operation projection. The projection is recomputed from the amended sample sizes so that the accounted RP I4 rows and the registered applicability agree by construction rather than by coincidence.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (retained_exact_binomial_gates I4, gate_hierarchy I4, gate_truth_table, development_selection_and_confirmation_plan.stage_1_component_evaluation, operation_boundaries.projected_future_operations)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/analysis/design_statistics_tables.json`

**Verification.** the committed design test asserts S4 is not_applicable for I4 in every location and that the RP I4 projection derives from the registered applicable profiles

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-004` - MAJOR

**Reviewer finding.** Every confirmation exact-binomial row admits the never-selectable profile S4, and I1b's confirmation row admits S4, although confirmation is entered only by a development-selected profile

**Repair.** S4 is removed from every confirmation applicability list, and the applicability rule is made explicit: confirmation applicability is the INTERSECTION of each component's registered SELECTABLE profiles with the single profile selected on the development split. I1b confirmation applies only to the label-bearing selectable profile S1, and the seven K5 pairs likewise apply only to S1. For S2 and S3 both remain not_applicable and are never a pass.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (confirmation_exact_binomial_gates, confirmation_applicability_rule, gate_hierarchy I5, development_selection_and_confirmation_plan.stage_3_confirmation)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/protocol/interface_calibration_protocol.schema.json`

**Verification.** the committed schema rejects any confirmation row containing S4 and the committed design test asserts the intersection rule and the S1-only applicability of I1b and K5 at confirmation

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-005` - MAJOR

**Reviewer finding.** The S4 diagnostic generation stream publishes a null forward-pass count beside 16,128 generations and a 258,048 generated-token bound, so the dominant cost of the only generative stream is unmapped

**Repair.** operation_ontology_v0_4 registers nine distinct operation units, including sequence-level prefill evaluations, incremental decode evaluations and total sequence-level model-evaluation equivalents, and prohibits equating a sequence-level evaluation with a runtime batched forward call. The S4 stream now publishes a non-null bound: generation calls, a registered maximum of 16 new tokens per generation, a generated-token upper bound, a prefill count, an incremental-decode upper bound and the total sequence-level model-evaluation upper bound. The unresolved P3-Q stream remains null with an explicit OD2 status, and publishing a grand total that treats that null as zero is prohibited.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (operation_ontology_v0_4, operation_boundaries.projected_future_operations)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/analysis/design_statistics_tables.json`

**Verification.** the committed derivation computes every S4 quantity from the registered token bound and cell structure; the committed design test re-derives them and asserts the S4 forward cost is not null and that no grand total is published

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-006` - MAJOR

**Reviewer finding.** An I0 failure has two different registered legal next states, and the published executable selection map cannot return the registered stop state STOP_INSTRUMENT_DEFECT

**Repair.** state_machine_v0_4 publishes one total, deterministic finite-state graph. I0 is a GLOBAL PRECONDITION evaluated before and outside profile adequacy, and it is removed from every profile's stage-1 component list. Q0_INSTRUMENT maps a pass to Q1_DEVELOPMENT and a fail, error or ambiguity to STOP_INSTRUMENT_DEFECT and nothing else. Q1_DEVELOPMENT maps a valid completion to Q2_SELECTION and a protocol or integrity error to the separately registered STOP_DEVELOPMENT_INTEGRITY_ERROR, which is never reinterpreted as a scientific gate failure. Q2_SELECTION maps a selection to Q3_CONFIRMATION_PENDING_SEPARATE_AUTHORITY and no selection to STOP_NO_SELECTABLE_INTERFACE_REMAINS. Q3 is enterable only under a later confirmation authority and maps to CALIBRATED_PENDING_SEPARATE_SUBSTANTIVE_AUTHORITY, STOP_CONFIRMATION_FAILED or STOP_CONFIRMATION_SPENT_ON_ERROR. The sixteen-row profile-eligibility map is retained as the Q2_SELECTION subtable that applies only once I0 has passed. STOP_INSTRUMENT_DEFECT states that nothing was measured about any interface; STOP_NO_SELECTABLE_INTERFACE_REMAINS states only the realized run outcome.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (state_machine_v0_4, gate_hierarchy I0, development_selection_and_confirmation_plan.stage_1_component_evaluation)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/protocol/interface_calibration_protocol.schema.json`, `studies/study3/analysis/design_statistics.py`, `studies/study3/analysis/design_statistics_tables.json`

**Verification.** the committed derivation raises if any event has two next states or if any registered terminal state is unreachable, and asserts that an I0 failure maps only to STOP_INSTRUMENT_DEFECT; the committed design test re-derives the whole graph

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-007` - MAJOR

**Reviewer finding.** Gate I4's null is registered as a fixed number while the P3-Q competence floor that makes it interpretable is deferred to OD2, and no ordering constraint between them is registered

**Repair.** The binding ordering constraint is registered for the later OD2 authority: the P3-Q one-sided competence lower bound must be at or above 19/20, which is strictly greater than the I4 alternative 9/10, which is strictly greater than the I4 null 4/5. A later authority may choose a stronger P3-Q floor but not a weaker one, and it must still freeze the checkpoint identity and immutable revision, a canonical qualification interface external to S1-S4, the RP-specific I4 wrapper, a physically isolated P3-Q bank and seed, exact n, alpha and rejection rule, the operation-family and depth treatment, the stop rule and the provenance record. OD2 remains UNRESOLVED_BLOCKING_OPERATOR_DECISION and no checkpoint, revision, tokenizer, wrapper or candidate is selected.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (positive_reference_candidates.p3q_i4_ordering_constraint, gate_hierarchy I4, unresolved_operator_decisions OD2)`, `studies/study3/references/positive_reference_dossier.md`, `studies/study3/protocol/interface_calibration_protocol_draft.md`

**Verification.** the committed design test reconstructs 19/20 > 9/10 > 4/5 in exact rational arithmetic and asserts that OD2 is unresolved and that no checkpoint or model revision is selected

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-008` - MINOR

**Reviewer finding.** The registered I3 claim ceiling is stated over nine contrast cells and overstates what a non-label-bearing profile can support

**Repair.** The I3 claim ceiling is qualified per profile. S1 carries the seven applicable K5 pairs and the two applicable K6 pairs; S2 and S3 carry only the two applicable K6 pairs, with S3 additionally subject to its separately registered single-token applicability condition; S4 is descriptive only and never part of an interface-selection or confirmation claim.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (claim_ceiling.i3_claim_ceiling_by_profile, i3_contrast_registry.claim_ceiling_by_profile, gate_hierarchy I3)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`

**Verification.** the committed design test asserts the per-profile applicable cell sets and that a not_applicable cell is never counted as evidence

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-009` - MINOR

**Reviewer finding.** The deterministic I0 fixture stream files a rendered-row count under the base_item unit, contrary to the unit registry introduced to repair S3MR-014

**Repair.** The I0 fixture stream registers base_item_contrast_clusters = 232, cluster-derived base_items = 232 rather than 464, cluster_rendered_rows = 464, noncluster_fixture_rows = 38 and rendered_rows = scored_rows = 502, with zero model operations. The unit registry and the dimensional identities are extended so that every stream reporting clusters proves cluster_rendered_rows = clusters x variants_per_cluster while non-cluster fixture rows are named separately.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (proposed_statistics.i0_fixture_breakdown, i0_fixture_unit_rule, operation_boundaries.projected_future_operations)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/analysis/design_statistics_tables.json`

**Verification.** the committed derivation raises if the cluster-derived fixture rows are not a whole number of clusters, and the committed design test re-derives 232, 232, 464, 38 and 502

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

### `S3MR2-010` - MAJOR

**Reviewer finding.** No artifact states the stochastic model that makes the exact binomial test valid, and the registered construction is deterministic with no draw mechanism, so the superpopulation warrant does not yet exist

**Repair.** sampling_frame_v0_4 registers a normative, executable specification for every gate-bearing atomic cell: the named finite item-generating support, the generator family and version, every sampled parameter and its support, exact rational weights that sum to exactly one, deterministic pre-draw validity predicates with a fail-closed rejection contract whose registered rejection probability is 0 by construction, the independent unit, the split namespace, the gate, profile, role, operation-family, depth and contrast namespaces, the draw-with-replacement rule, the cross-role and cross-profile reuse rule, the cross-cell and cross-split partition rule, the future seed lifecycle, the induced estimand and the precise conditions under which exact-binomial inference is valid. Two levels are separated so item reuse can never be confused with the independent sampling unit: a sampling cell excludes interface profile and checkpoint role, and an evaluation cell is a sampling cell crossed with one applicable profile and one applicable role. One iid stream is drawn per sampling cell and reused across its evaluation cells, so every evaluation cell is marginally iid Bernoulli while cells sharing items may be dependent, which is expressly allowed and handled by the arbitrary-dependence bounds. Duplicate generator tuples are legitimate iid draws and must be retained; the draft-v0.3 duplicate-rejection rule is withdrawn and reversed. For K5 the deterministic complete-block assignment is replaced by an iid nuisance draw over the exhaustive 32-state support at exact weight 1/32 per state, and n is no longer required to be a multiple of 32; exhaustive fixture and support enumeration is retained as a design-time correctness check and is explicitly not a bank sample. The future seed lifecycle registers a first-draw-only 256-bit master seed per split from a cryptographic source under a separate authority, immediate commitment, no redraw or substitution, domain-separated key encoding, a frozen expansion algorithm with test vectors, confirmation-seed isolation and later disclosure sufficient to regenerate the bank. Seed values, the generator implementation blob and the realized bank are null, meaning not yet selected rather than zero. Any cell lacking a complete generator distribution fails closed.

**Where.** `studies/study3/protocol/interface_calibration_protocol_draft.json (sampling_frame_v0_4, atomic_evaluation_cells, counterbalancing_design, task_strata K1-K5, bank_construction_policy)`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/protocol/interface_calibration_protocol.schema.json`, `studies/study3/analysis/design_statistics.py`, `studies/study3/analysis/design_statistics_tables.json`

**Verification.** the committed derivation validates every sampling cell's parameter weights, joint weights, draw rule, namespace disjointness and profile exclusion, and raises on any violation; the committed design test re-checks the weights, the with-replacement rule, the duplicate prohibition, the outcome-blind partition, the null seed state and the fail-closed rule

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` - not self-approved.

## 3. The twenty inherited first-review findings

No inherited finding is erased and none is silently moved into an operator decision to avoid repair.

| Finding | Severity | Status after the second review | Note |
| --- | --- | --- | --- |
| `S3MR-001` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the I3 estimand is identifiable from the published construction; carried forward unchanged in draft-v0.4, whose sampling frame additionally registers the distribution the unit is drawn from |
| `S3MR-002` | BLOCKING | `PARTIALLY_RESOLVED_BY_DRAFT_V0_3` | the second reviewer found the artifacts reconciled but the named indicator redundant. draft-v0.4 proposes full resolution by narrowing the indicator to J_joint_correct through S3MR2-001; this remains review-pending |
| `S3MR-003` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the exact rational 1/600 derives every development threshold and 1/600 x 3 = 1/200 holds; unchanged |
| `S3MR-004` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the false conservativeness assertion is withdrawn; draft-v0.4 introduces no paired procedure |
| `S3MR-005` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the four-point discordance grid is removed and no size-control claim over a nuisance domain is made |
| `S3MR-006` | BLOCKING | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | exactly one I3 floor is active and 0.95 appears in no active field; the floor is retained in draft-v0.4 with the indicator narrowed |
| `S3MR-007` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | every emitted binomial row carries an explicit null column; unchanged |
| `S3MR-008` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the reviewer confirmed the sizes were minimal under the then-registered target; draft-v0.4 re-derives them against the new per-cell target and they change accordingly |
| `S3MR-009` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the circular verification and the fixed-grid test are gone; the anti-transcription AST audit is retained and strengthened in draft-v0.4 |
| `S3MR-010` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the K5 generating-process text describes the seven one-factor contrasts actually adopted; draft-v0.4 replaces its deterministic block assignment with an iid draw |
| `S3MR-011` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | K6 is two disjoint pairwise cells with the answer cue held byte-identical; unchanged |
| `S3MR-012` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | S3's incremental cost is zero under the four registered preconditions; recomputed in draft-v0.4 |
| `S3MR-013` | MAJOR | `PARTIALLY_RESOLVED_BY_DRAFT_V0_3` | the six-stream decomposition was accepted but the S4 forward cost was left unmapped. draft-v0.4 proposes full resolution through the operation ontology in S3MR2-005; this remains review-pending |
| `S3MR-014` | MAJOR | `PARTIALLY_RESOLVED_BY_DRAFT_V0_3` | the unit registry was accepted but the I0 fixture stream violated it. draft-v0.4 proposes full resolution through S3MR2-009; this remains review-pending |
| `S3MR-015` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | pass_count < n strictly in every active row; re-derived and re-asserted in draft-v0.4 |
| `S3MR-016` | MAJOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the selectable-profile denominator is the pre-data integer 3 in every branch; unchanged |
| `S3MR-017` | MAJOR | `PARTIALLY_RESOLVED_BY_DRAFT_V0_3` | I5 and the selection map were accepted but I0 was folded into profile adequacy and the confirmation applicability admitted S4. draft-v0.4 proposes full resolution through S3MR2-006 and S3MR2-004; this remains review-pending |
| `S3MR-018` | MINOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | checkpoint-role records use post-split gate names; unchanged |
| `S3MR-019` | MINOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | every interval and band names the mass it consumes; unchanged |
| `S3MR-020` | MINOR | `VERIFIED_RESOLVED_BY_THE_SECOND_REVIEW` | the dossier obligation is attributed to D-04 and declares UNSELECTED; draft-v0.4 adds the P3-Q ordering constraint without selecting anything |

The four findings the second reviewer marked `PARTIALLY_RESOLVED` are proposed fully resolved only
through the corresponding draft-v0.4 repair, and they remain review-pending.

## 4. The twenty-two unresolved items

| Item | Subject | Disposition |
| --- | --- | --- |
| `UR-01` | I3 primary estimand identifiability | `CARRIED_RESOLVED` |
| `UR-02` | I3 primary indicator semantics | `PROPOSED_RESOLVED_IN_V0_4_VIA_S3MR2_001` |
| `UR-03` | Family B per-profile alpha implementation | `CARRIED_RESOLVED` |
| `UR-04` | false conservativeness assertion | `CARRIED_RESOLVED` |
| `UR-05` | paired size control over the nuisance domain | `CARRIED_RESOLVED` |
| `UR-06` | I3 primary floor and its feasibility | `CARRIED_RESOLVED` |
| `UR-07` | I5 confirmation specification | `PROPOSED_RESOLVED_IN_V0_4_VIA_S3MR2_004_AND_S3MR2_002` |
| `UR-08` | development profile-selection rule | `PROPOSED_RESOLVED_IN_V0_4_VIA_S3MR2_006` |
| `UR-09` | Family B denominator membership of S3 | `CARRIED_RESOLVED` |
| `UR-10` | unit of every sample-size symbol | `PROPOSED_RESOLVED_IN_V0_4_VIA_S3MR2_009` |
| `UR-11` | I1a and I1b power shortfall | `CARRIED_RESOLVED_AND_RESIZED_IN_V0_4` |
| `UR-12` | circular committed verification and the grid test | `CARRIED_RESOLVED` |
| `UR-13` | K5 and K6 stale generating-process text | `CARRIED_RESOLVED` |
| `UR-14` | S3 projection and the undecomposed projection | `PROPOSED_RESOLVED_IN_V0_4_VIA_S3MR2_005` |
| `UR-15` | I4 multiplicity across families and depths | `CARRIED_RESOLVED` |
| `UR-16` | residual pooling paths | `CARRIED_RESOLVED` |
| `UR-17` | degenerate I3 rejection region | `CARRIED_RESOLVED` |
| `UR-18` | paired margin practical-irrelevance justification | `CARRIED_RESOLVED` |
| `UR-19` | Clopper-Pearson and uniformity tail conventions | `CARRIED_RESOLVED` |
| `UR-20` | positive-reference dossier attribution | `CARRIED_RESOLVED` |
| `UR-21` | stale Gate I1 labels | `CARRIED_RESOLVED` |
| `UR-22` | external qualification interface for the positive reference | `UNRESOLVED_BLOCKING_OPERATOR_DECISION` |

`UR-22` and `OD2` remain unresolved blocking operator decisions. draft-v0.4 registers only the
binding P3-Q/I4 ordering constraint and selects no checkpoint, revision, tokenizer, wrapper or
candidate.

## 5. Separation of kinds

| Kind | Content |
| --- | --- |
| `empirical_result` | none; no measurement of any kind exists |
| `exact_deterministic_derivation` | every sample size, threshold, tail, power, cell count, joint bound and operation total, derived by studies/study3/analysis/design_statistics.py |
| `future_implementation_requirement` | the seed authority, the bank construction authority and the OD2/P3-Q authority |
| `operator_design_choice` | the narrow I3 repair path, the 19/400 per-stage budget, the iid-with-replacement sampling model, the P3-Q ordering constraint and the state-machine separation |
| `reviewed_fact` | the second review's findings, severities and evidence bindings, quoted unedited |
| `reviewer_recommendation_adopted_here` | the per-profile I3 claim-ceiling qualification, the S4 I4 not_applicable reading, the confirmation intersection rule and the decode-step ontology |
| `unresolved_operator_choice` | OD2 and UR-22 |

## 6. Derived design parameters

| Quantity | Value |
| --- | --- |
| maximum selectable-profile cell count | 43 |
| per-cell power target | `17181/17200` |
| profile stage power floor | `381/400` |
| study end-to-end power floor | `9/10` |
| uses independence | `false` |

| Gate family | n | Development pass count | Confirmation pass count |
| --- | --- | --- | --- |
| `I1_I3_joint_correctness_floor` | 413 | 389 | 388 |
| `I2_headroom_floor` | 214 | 129 | 127 |
| `I4_positive_reference_floor` | 448 | 383 | 381 |

Every value above is derived by `studies/study3/analysis/design_statistics.py` from the protocol's
registered exact rational inputs. None is transcribed.

## 7. Boundary

| Counter | Value |
| --- | --- |
| `ablation_operations` | `0` |
| `activation_extractions` | `0` |
| `bank_rows_generated` | `0` |
| `confirmation_split_accesses` | `0` |
| `decode_steps` | `0` |
| `evidence_rows_created` | `0` |
| `forward_passes` | `0` |
| `generations` | `0` |
| `gpu_jobs` | `0` |
| `interfaces_selected` | `0` |
| `lens_operations` | `0` |
| `model_downloads` | `0` |
| `model_weight_loads` | `0` |
| `patching_operations` | `0` |
| `phase_1_0d_operations` | `0` |
| `positive_references_selected` | `0` |
| `probe_operations` | `0` |
| `provider_calls` | `0` |
| `rq2_s4_operations` | `0` |
| `seeds_drawn` | `0` |
| `study1_files_modified` | `0` |
| `study2_files_modified` | `0` |
| `tokenizer_constructions` | `0` |

| Flag | Value |
| --- | --- |
| `bank_authorized` | `false` |
| `confirmation_access_authorized` | `false` |
| `execution_authorized` | `false` |
| `frozen` | `false` |
| `model_operations_authorized` | `false` |
| `positive_reference_selected` | `false` |
| `seed_authorized` | `false` |
| `winner_selected` | `false` |

No result, evidence row, bank row or seed exists. Study 1 remains closed. Study 2 remains closed.
Study 3 remains unfrozen. No interface and no positive reference is selected. The original research
question remains unanswered.

**Next legal action.** a third bounded independent methods review of draft-v0.4, conducted in a fresh session by a party that did not draft draft-v0.4.

## 8. Historical-review test-harness scope erratum

This section records a defect in a **committed test harness**, not a change to the second
independent methods review. The review's findings, its disposition
`STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`, its reviewed-artifact identities and
every expected scientific result stand exactly as committed.

**The defect.** Two checks in `tests/test_study3_methods_review_v0_3.py` were written to validate
draft-v0.3 against its reviewed historical inputs, but read live index or working-tree bytes.
That silently rescoped them onto whichever draft was checked out:

- `test_the_reviewer_did_not_edit_either_existing_study3_test_module` compared
  `tests/test_study3_design.py` with the live file rather than with its committed blob at
  `REVIEWED_COMMIT`, so the authorized draft-v0.4 enlargement of that module broke it;
- `test_independent_recalculation_check_mode_reproduces_the_committed_tables` executed the v0.3
  recalculation generator inside the live repository, so it consumed the amended draft-v0.4
  protocol instead of the reviewed draft-v0.3 protocol.

**The repair.** Both checks are now anchored to `REVIEWED_COMMIT`
`2b36f5321d830ea6f70fff2b7bbca3cb93394046`. The first compares committed blobs at that commit.
The second materialises the reviewed protocol and design inputs into an isolated snapshot and runs
the **unchanged** generator and **unchanged** committed table there; because the generator resolves
every path it reads from its own `__file__`, that snapshot root is its entire repository, and the
check asserts that no current-draft byte is reachable from it.

No assertion was deleted or weakened. No `skip`, `xfail`, warning-only behaviour or exception
swallowing was introduced. No expected hash or value was changed to accept live draft-v0.4 bytes.
Neither immutable v0.3 recalculation file was modified. The module keeps exactly its 35 node IDs.

**Disclosed earlier runs.** These are disclosed, not erased and not relabelled. On candidate
`3c229017d85259af2e2e3a6654b66b4383c064a0` the module returned **33 passed, 2 failed**, and a direct
live-input `--check` returned `FAIL: recomputed tables differ from the committed tables`. Both
outcomes were produced by the scope error above. With the inputs pinned to `REVIEWED_COMMIT`, the
unchanged generator reproduces the unchanged committed table exactly and the module returns
**35 passed**.

**Supplemental operator authority, recorded verbatim.** 5,938 bytes, SHA-256
`165acb770db3f25c0403a7d376a81b569fff11d623610a802e135633ec9c503b`. No additional authority file was
added, and `studies/study3/prompts/study3_v0_4_design_amendment_authority.md` remains byte-identical
at 46,543 bytes with SHA-256
`230c57f4bfb874ad724c9448e8cfc1e58b0ff5970159e6741ce61de8104cd173`.

```markdown
# Supplemental operator authority — Study 3 draft-v0.4 historical-regression harness erratum

I select operator option 1, narrowly construed.

This authority resolves only the proven historical-regression harness contradiction. It does not amend the Study 3 scientific design, statistics, sampling frame, estimands, thresholds, claims, state machine, operation projection, or review disposition.

## 1. Starting point

Continue from the exact local candidate:

- commit: `3c229017d85259af2e2e3a6654b66b4383c064a0`
- tree: `ac4acd703ca1169dbbf5016c2b0796f625ef2196`
- published base: `bc98e5c98a2d4e273142c91497b7600ce751bade`

Require a clean worktree and verify that the candidate remains a strict descendant of the published base before making any change.

## 2. Sole path exception

The only newly authorized path is:

`tests/test_study3_methods_review_v0_3.py`

The final changed-path set relative to `bc98e5c…` must therefore be exactly:

- 26 paths;
- 6 added;
- 20 modified;
- no deletion, rename, copy, or type change.

No 27th path is authorized.

The existing 25 paths may be updated only where necessary to record this disclosed erratum, update path counts, hashes, receipts, registry metadata, and validation results. They must not receive any substantive scientific or statistical redesign.

The original committed authority:

`studies/study3/prompts/study3_v0_4_design_amendment_authority.md`

must remain byte-identical at 46,543 bytes with SHA-256 `230c57f4…d173`. Record this supplemental authority verbatim, or with its complete text and byte identity, inside an already-authorized v0.4 amendment record. Do not add another authority file.

## 3. Required semantic repair

Repair the historical regression harness so that its implementation matches its existing stated purpose: validating draft-v0.3 against its reviewed historical inputs.

Specifically:

1. `test_the_reviewer_did_not_edit_either_existing_study3_test_module` must compare the relevant files with their committed blobs at:
`REVIEWED_COMMIT = 2b36f5321d830ea6f70fff2b7bbca3cb93394046`
It must not compare them with the candidate’s live index or working-tree bytes.
2. The v0.3 independent recalculation check must execute the unchanged v0.3 recalculation script and unchanged committed v0.3 table against an isolated historical snapshot whose mutable protocol/design inputs come from `REVIEWED_COMMIT`.
3. The isolated check must not consume the live draft-v0.4 protocol, design statistics, test file, or other mutable current-draft bytes.
4. Do not modify either immutable v0.3 recalculation file, any review finding, review disposition, reviewed-artifact identity, expected scientific result, or historical commit.

This authority forbids:

- deleting or weakening either failing assertion;
- adding `skip`, `xfail`, warning-only behavior, or exception swallowing;
- changing expected hashes or values to accept live v0.4 bytes;
- treating the two failures as allowed failures;
- changing the two existing registered `test_parser_v3_seal_job` failures;
- changing any v0.4 scientific content.

The repair must be recorded as a historical-review test-harness scope erratum, not as an amendment to the v0.3 review itself.

## 4. Required validation

Run the complete clean CPU-only ACR validation envelope on the new final candidate commit, with `GPU_COUNT=0`, `CUDA_AVAILABLE=False`, and a clean worktree.

At minimum require:

- `tests/test_study3_design.py`: 197 passed;
- `tests/test_study3_methods_review.py`: 78 passed;
- `tests/test_study3_methods_review_v0_3.py`: 35 passed;
- the unchanged v0.3 recalculation script reproduces its committed table exactly when run against the isolated reviewed snapshot;
- `DESIGN_STATISTICS_CHECK_OK sections=19`;
- all previously required Study 2 and protected-byte regressions unchanged;
- static publication audit: exactly 26 paths, 6 added and 20 modified;
- full suite: exactly 3,974 passed, 15 skipped, and only the same two registered `test_parser_v3_seal_job` failures with unchanged node IDs and signatures.

The arithmetic must reconcile as:

`3,886 baseline passes + 88 net new design tests = 3,974 passes`.

Disclose the earlier candidate-bound 33-passed/2-failed v0.3 review run, the earlier direct live-input recalculation failure, and how the corrected historical-snapshot execution resolves their scope error. Do not erase or relabel those earlier runs.

Recompute and report every affected artifact identity and registry tail. `paper/evidence_ledger.csv` must remain untouched and end at `EV-0016`. No scientific evidence, method result, bank, seed, model operation, interface selection, positive reference, or confirmation access is authorized.

## 5. Publication

Only after the corrected candidate passes the full validation envelope:

1. fetch remote `main`;
2. require it to remain exactly `bc98e5c98a2d4e273142c91497b7600ce751bade`;
3. require it to be a strict ancestor of the corrected candidate;
4. publish only by non-force fast-forward:
`git push origin HEAD:refs/heads/main`
5. fetch again and verify `HEAD == origin/main`, the exact final tree, clean worktree, the exact 26-path set, protected bytes, artifact identities, and unchanged `EV-0016`.

If remote `main` moved, another path is required, historical scientific/review content must change, or any validation result differs from the registered expectations, stop and report without publishing.

## 6. Final state

After successful publication, use the original §9 completion heading and provide the complete amended handoff.

The state must remain:

- `frozen=false`;
- `execution_authorized=false`;
- every empirical/model counter zero;
- no bank, seed, checkpoint, winner, RP, or confirmation access;
- OD2 unresolved.

The only legal successor remains a fresh-session third independent methods review of published draft-v0.4. Do not begin that review, a v0.5 amendment, or any feasibility pilot in this session.
```
