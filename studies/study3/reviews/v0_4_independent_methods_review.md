# Study 3 draft-v0.4 - third independent methods review

**State:** `STUDY3_DRAFT_V0_4_THIRD_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`

**Disposition:** **`STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED`**

**Legal successor action:** `OPERATOR_BOUNDED_AMENDMENT_ROUND_FOR_DRAFT_V0_5`

This review is not a scientific result and is not an execution authority. It creates no freeze, no execution, no amendment and no pilot authority.

---

## 1. Binding of the reviewed object

| field | value |
| --- | --- |
| reviewed commit | `e865be51da6c7e1a7a4f5b1fcad0efc513bd0f43` |
| reviewed tree | `86c5a5ec0e475090c14654cff27605f883495a48` |
| published pre-amendment base | `bc98e5c98a2d4e273142c91497b7600ce751bade` |
| change-set paths | 6 added, 20 modified, 26 total |

The 26-path change set was reconstructed from Git and contains no deletion, rename, copy or type change. Every reviewed path and every core prior-review blob is bound by byte count and SHA-256 in the machine-readable review under `reviewed_artifact_identities`; the committed test re-derives each identity from the committed blob rather than from working-tree bytes.

### Core reviewed blobs

| path | bytes | sha256 |
| --- | --- | --- |
| `studies/study3/protocol/interface_calibration_protocol_draft.json` | 390029 | `6a89e02555a6e98b24fa6a5570ebab3bdee14eb9ae7346863246f2982a0f20cb` |
| `studies/study3/protocol/interface_calibration_protocol_draft.md` | 113490 | `1d700b1e0a7a4990568aba954f48c8c42e3f5ac0a11ac7d7c24ab67382998f79` |
| `studies/study3/protocol/interface_calibration_protocol.schema.json` | 121676 | `0743419b5e3d09b2ee88ef6ef61f29b605c4eeaafc3855426b21823ba2c10854` |
| `studies/study3/analysis/design_statistics.py` | 55893 | `9348bd615b7d51959b97f3fdab9d1ba74ca55cdd49e37f09ef0bbb43f793469c` |
| `studies/study3/analysis/design_statistics_tables.json` | 37108 | `96274e8c4eec3eac699a1cd0c53ea78beb29787e447a52de27c5749a69ae6985` |
| `studies/study3/analysis/independent_methods_review_packet_v0_4.md` | 14857 | `2900615281d05dee6d346876b29130c950efbc17486f28e2437a378ade0142dc` |
| `studies/study3/reviews/v0_4_operator_amendment.json` | 49874 | `451089a70f4fc9b26e6e67399f413854e612a2b6f233c7fb7ec0a565e585eb57` |
| `studies/study3/design_receipt_v0_4.json` | 17959 | `209d4045a082763b48bee8154c78410984476444ce2106bc9d294bab252a4ef2` |
| `tests/test_study3_design.py` | 162410 | `596755be5341cbd794f1df1c698ba8a13ed98384b3b846dd3010da0ab855d862` |
| `tests/test_study3_methods_review.py` | 60781 | `331d2a7644ee3256d7a145fa8ba83d0b02dcfd1faa1ed8989b726c1c656509ba` |
| `tests/test_study3_methods_review_v0_3.py` | 44821 | `a1676d31ed32225c8e8a3dba40b4ee6f01d5d3490619eeb35d385efb4ea48c61` |

### Authority identity

| field | source | committed |
| --- | --- | --- |
| bytes | 47885 | 47885 |
| LF / CR | 940 / 0 | same |
| trailing newline | false | same |
| sha256 | `c756ba2e5ad147cfc19edc4a451c2d919e51643d19dda7d95469c21786dcdc86` | `c756ba2e5ad147cfc19edc4a451c2d919e51643d19dda7d95469c21786dcdc86` |

Observed source path: `C:\Users\alanjiao\.copilot\workspaces\4f9087c8-ebef-4dba-a9b4-a2b620ce1ecd\attachments\pasted-text-6fe3b48d-0969-4986-a94e-f56f33ea93cf.txt`. The committed authority at `studies/study3/prompts/study3_v0_4_independent_methods_review_authority.md` is byte-identical to it: no header, footer, wrapper, commentary, normalisation or change of trailing-newline state was applied.

## 2. Independence and ordering

Procedural separation is recorded above and is treated as necessary but not sufficient. Every decision-bearing statistical calculation, construction audit and logical derivation in this review was implemented independently in studies/study3/analysis/independent_methods_recalculation_v0_4.py from the registered inputs of the authoritative protocol JSON and from the English-language primary statistical sources, and was committed before any drafting output was opened.

| ordering step | commit |
| --- | --- |
| independent extraction, derivation and emitted table | `76ab1bab8fe947a26390a0c6c6d46c7f9af51842` |
| first commit that opens any drafting output | `8a30067d3094a2e62828536c1bbaa8e704c988e8` |

Commit 76ab1bab committed the independent parameter extraction, the derivation and the emitted table with no reference to any drafting output. Commit 8a30067d, a strict descendant, added the field-by-field comparison and is the first commit in which design_statistics.py or design_statistics_tables.json is read. The ordering is therefore provable from history rather than asserted. A later commit f4e3b73a repaired a platform-dependent path rendering in the reviewer's own module after a clean ACR run rejected it; no derived quantity changed.

**Prohibited-source audit.** The committed review test proves by AST inspection that the independent module contains no import, no import-from, no __import__, no importlib call, no exec, no eval, no runpy call and no subprocess invocation naming any prohibited source, and that no reviewer-returned planning target appears in its reachable source literals. The single repository artifact the module opens for registered inputs is the authoritative protocol JSON; the drafting table is opened only inside the comparison function that was added in a strictly later commit.

Agreement with the drafting bytes is not treated as validation anywhere in this review. The independent module validates itself against closed-form identities, exhaustive small-case enumeration and published examples for each statistical family: the binomial total-mass identity, the Clopper-Pearson beta duality checked over 220 cases by exact polynomial integration, the exact one-sided sign-test tails 7/128 at n = 10 and 5425/262144 at n = 20, and exhaustive enumeration of the union bound, its disjoint equality witness, the Frechet intersection lower bound and the intersection-union size bound over 1716 finite joint distributions covering arbitrary dependence.

## 3. Adjudication of the ten inherited findings

Each finding is adjudicated exactly once. `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW` is treated as a claim, never as proof.

| finding | original | status | repair |
| --- | --- | --- | --- |
| `S3MR2-001` | BLOCKING | **PARTIALLY_RESOLVED** | substantive_but_incompletely_propagated |
| `S3MR2-002` | BLOCKING | **VERIFIED_RESOLVED** | substantive |
| `S3MR2-003` | MAJOR | **PARTIALLY_RESOLVED** | substantive_but_incompletely_propagated |
| `S3MR2-004` | MAJOR | **PARTIALLY_RESOLVED** | substantive_but_incompletely_propagated |
| `S3MR2-005` | MAJOR | **VERIFIED_RESOLVED** | substantive |
| `S3MR2-006` | MAJOR | **VERIFIED_RESOLVED** | substantive |
| `S3MR2-007` | MAJOR | **VERIFIED_RESOLVED** | substantive |
| `S3MR2-008` | MINOR | **PARTIALLY_RESOLVED** | substantive_but_incompletely_propagated |
| `S3MR2-009` | MINOR | **VERIFIED_RESOLVED** | substantive |
| `S3MR2-010` | MAJOR | **PARTIALLY_RESOLVED** | substantive_but_incompletely_propagated |

### `S3MR2-001` - PARTIALLY_RESOLVED

**Drafting party's claim.** I3 is narrowed to J_joint_correct, a level over the registered item-generating distribution; the construct strings, the gate question, the claim ceiling and the research question are narrowed and a prohibited-term list is registered and enforced.

**Reviewer's evidence.** The repair is real and correct inside the authoritative protocol. The reviewer independently enumerated the ordered 4x4 lattice and confirms exactly one of sixteen cases scores, that J_cor implies J_inv under a unique ground truth, and that J_both is identically J_cor, so the narrowed indicator is the quantity the design actually identifies. The repair is nevertheless not propagated to reviewed narrative paths. RESEARCH_CHARTER_DRAFT.md section 2 still states the research question in the draft-v0.3 form the protocol itself classifies as a presentation-effect question, and section 4 commitment 3 still names J_both and defines it as requiring invariance across the two variants. studies/README.md still describes the primary indicator as requiring both invariance and correctness, studies/study3/README.md repeats it, and NEXT_THREAD_HANDOFF.md still names J_both the primary gate indicator. The claim that no active claim asserts invariance is therefore false in four reviewed paths.

**Closes the original defect:** false. **Creates a new defect:** false.

Evidence fields: `proposed_statistics.i3_indicators.J_joint_correct`, `proposed_statistics.active_claim_term_prohibition`, `RESEARCH_CHARTER_DRAFT.md section 2 What Study 3 asks`, `RESEARCH_CHARTER_DRAFT.md section 4 design commitment 3`, `studies/README.md primary indicator description`, `studies/study3/README.md What draft-v0.3 changed about the gates`, `NEXT_THREAD_HANDOFF.md Three I3 indicators, one primary`

### `S3MR2-002` - VERIFIED_RESOLVED

**Drafting party's claim.** A binding end-to-end power design is registered: a per-stage profile false-negative budget divided across m_max gives a per-cell budget and target, a profile stage floor and a study end-to-end floor, all by union bound under arbitrary dependence.

**Reviewer's evidence.** The reviewer derived the whole ladder independently from the registered per-stage budget and the independently recomputed cell census, without reading the drafting values. m_max is 43 over the selectable profiles only; the per-cell budget is 19/17200; the per-cell target is 17181/17200; the profile stage floor is 381/400 and equals one minus the per-stage budget exactly; the panel bound is the fixed denominator three times the per-component level 1/600, giving 1/200; and the end-to-end floor is 9/10. Every step is a union bound. The union bound was separately validated by exhaustive enumeration over 1716 finite joint distributions covering arbitrary dependence, with a disjoint witness attaining equality, so no independence assumption is needed or used. Per-cell, profile-stage, selection-return and end-to-end quantities are named separately and the protocol prohibits relabelling one as another.

**Closes the original defect:** true. **Creates a new defect:** false.

Evidence fields: `power_architecture_v0_4.type_ii_allocation`, `power_architecture_v0_4.union_bound_proof`, `power_architecture_v0_4.power_vocabulary`, `error_budget_ladder`, `method_validation.multiplicity_and_arbitrary_dependence`

### `S3MR2-003` - PARTIALLY_RESOLVED

**Drafting party's claim.** I4 applies only to S1, S2 and S3; S4 is not_applicable for I4 in the exact-binomial rows, the gate hierarchy, the gate truth table, the stage-1 component lists, the statistics tables and the operation projection, and the truth table records that the contradiction is resolved in favour of not_applicable in every location.

**Reviewer's evidence.** Every decision-bearing field is now consistent: gate_hierarchy I4 lists S1, S2 and S3; the development I4 exact-binomial row lists S1, S2 and S3; the gate truth table records I4 not_applicable for S4; the independently derived cell census gives S4 zero I4 cells; and the independently derived RP I4 projection of 3584 rendered rows follows from two scoring streams over four cells at n = 448 with no S4 contribution. One location was not updated: interface_profiles[S4].applicable_gates still contains I4. The universal claim in gate_truth_table.i4_applicability_note is therefore false, although no number or decision depends on the stale entry.

**Closes the original defect:** false. **Creates a new defect:** false.

Evidence fields: `interface_profiles[S4].applicable_gates`, `gate_truth_table.i4_applicability_note`, `gate_truth_table.rows[S4].I4`, `gate_hierarchy[I4].applicable_profiles`, `gate_bearing_cell_census.by_profile.S4.cells_at_i4_floor`

### `S3MR2-004` - PARTIALLY_RESOLVED

**Drafting party's claim.** S4 is removed from every confirmation applicability list, confirmation applicability is the intersection of a component's selectable profiles with the single selected profile, and I1b and K5 confirmation apply only to S1. The committed schema rejects any confirmation row containing S4.

**Reviewer's evidence.** The repair is complete and correct in the authoritative protocol: all five confirmation rows list only selectable profiles, I1b lists S1 alone, the K5 contrast applicability lists S1 alone, and the protocol schema constrains confirmation applicable_profiles to the enum S1, S2, S3 so a protocol row carrying S4 is rejected. The repair was not propagated to the derived table the protocol names as its source. design_statistics_tables.json confirmation_exact_binomial_components still lists S1, S2, S3 and S4 in the I1_I3 family row and in the I2 family row, which is the original defect verbatim. The table's gate-family row shape also cannot represent the I1b-only-for-S1 and K5-only-for-S1 repair, so that part of the repair is absent from the derived table entirely. No committed test asserts the applicable_profiles field of any table confirmation row, which is why the residue survived validation.

**Closes the original defect:** false. **Creates a new defect:** false.

Evidence fields: `design_statistics_tables.json :: confirmation_exact_binomial_components[I1_I3_joint_correctness_floor].applicable_profiles`, `design_statistics_tables.json :: confirmation_exact_binomial_components[I2_headroom_floor].applicable_profiles`, `proposed_statistics.confirmation_exact_binomial_gates[*].applicable_profiles`, `proposed_statistics.confirmation_applicability_rule`

### `S3MR2-005` - VERIFIED_RESOLVED

**Drafting party's claim.** operation_ontology_v0_4 registers nine distinct units including prefill evaluations, incremental decode evaluations and total sequence-level model-evaluation equivalents, prohibits equating a sequence-level evaluation with a runtime batched forward call, and the S4 stream publishes a non-null forward cost.

**Reviewer's evidence.** The reviewer recomputed the S4 stream from primitives rather than reading it. S4's applicable cell structure yields 1254 base items and 3717 contrast clusters per role, hence 8688 rendered rows per role and 26064 over the three target roles. With the registered bound of 16 new tokens, autoregressive decoding gives 26064 generation calls, 26064 prefill evaluations, at most 26064 x 15 = 390960 incremental decode evaluations, at most 417024 total sequence-level evaluation equivalents and at most 417024 generated tokens. All five figures reproduce exactly. The runtime batched forward call is registered as a separate unit and is left null, and the P3-Q stream remains null rather than zero with no grand total published.

**Closes the original defect:** true. **Creates a new defect:** false.

Evidence fields: `operation_ontology_v0_4.units`, `operation_boundaries.projected_future_operations.work_streams.S4_diagnostic_generation`, `operation_projection.S4_diagnostic_generation`

### `S3MR2-006` - VERIFIED_RESOLVED

**Drafting party's claim.** state_machine_v0_4 publishes one total deterministic graph in which I0 is a global precondition and an I0 failure, error or ambiguity maps only to STOP_INSTRUMENT_DEFECT, with a separately registered development integrity stop.

**Reviewer's evidence.** The reviewer reconstructed the transition system from the registered states without reading the drafting state-machine section. There are ten states, six terminal, eleven transitions. No state-event pair carries two next states, every transition target is a registered state, the entry state Q0_INSTRUMENT is unique, every non-terminal state has at least one outgoing transition, and every one of the six terminal states is reachable from the entry state. The three non-pass events at Q0_INSTRUMENT all map to STOP_INSTRUMENT_DEFECT and to nothing else, and that terminal state's registered claim states that nothing was measured about any interface. The machine is total and deterministic as claimed.

**Closes the original defect:** true. **Creates a new defect:** false.

Evidence fields: `state_machine_v0_4.states`, `state_machine_v0_4.total`, `transition_system.machine_is_total_and_deterministic`, `transition_system.i0_failure_maps_to_exactly_one_terminal`

### `S3MR2-007` - VERIFIED_RESOLVED

**Drafting party's claim.** The binding ordering constraint P3Q >= 19/20 > I4 p1 = 9/10 > I4 p0 = 4/5 is registered for the later OD2 authority, together with the list of fields that authority must still freeze, and OD2 remains unresolved.

**Reviewer's evidence.** The ordering constraint is registered and the reviewer confirms in exact rational arithmetic that 19/20 > 9/10 > 4/5, so a positive reference qualified at or above the P3-Q floor is required to be strictly more capable than the I4 alternative it must clear, which is what makes an I4 failure attributable to the interface rather than to the reference. The constraint is stated as a requirement on a later authority and no document treats it as completed qualification: the I4 prequalification record states the stage is not executed, RP is not selected and P3-Q is not authorised. No checkpoint, revision, wrapper or bank is selected anywhere.

**Closes the original defect:** true. **Creates a new defect:** false.

Evidence fields: `gate_hierarchy[I4].p3q_ordering_constraint`, `gate_hierarchy[I4].prequalification`, `unresolved_operator_decisions[OD2]`, `positive_reference_candidates`

### `S3MR2-008` - PARTIALLY_RESOLVED

**Drafting party's claim.** The I3 claim ceiling is qualified per profile: S1 carries seven K5 pairs and two K6 pairs, S2 and S3 carry only the two K6 pairs, and S4 is descriptive only.

**Reviewer's evidence.** The K5 half of the overstatement is genuinely removed and the reviewer's independent census confirms that S2 and S3 contribute no K5 cell. The repair simultaneously introduces a new and stronger overstatement on the K6 half. By positively registering both K6 pairs as applicable to S2 and S3, draft-v0.4 asserts that the separator contrast has a referent for two profiles that render no option list and no label. R-sep is registered as differing from R-base only in the separator string between a label and its option content, so for S2 and S3 the two variants of the K6-SEP cluster are byte-identical and, under the registered deterministic scorer, J_joint_correct in that cell collapses to a single marginal correctness indicator. The per-profile ceiling for S2 and S3 therefore still claims more than a pass can support, and it now does so for a cell that is counted and can be passed. This is recorded as new finding S3MR3-001.

**Closes the original defect:** false. **Creates a new defect:** true.

Evidence fields: `claim_ceiling.i3_claim_ceiling_by_profile.S2`, `claim_ceiling.i3_claim_ceiling_by_profile.S3`, `i3_contrast_registry.k6_applicability.applicable_profiles`, `counterbalancing_design.k6_renderings.renderings[R-sep].description`, `interface_profiles[S2].prompt_and_rendering_contract`

### `S3MR2-009` - VERIFIED_RESOLVED

**Drafting party's claim.** The I0 fixture stream registers 232 clusters, 232 cluster-derived base items, 464 cluster rendered rows, 38 non-cluster rows and 502 rendered rows, with the dimensional identity that cluster rows equal clusters times variants per cluster.

**Reviewer's evidence.** The reviewer recomputed the accounting from the registered fixture breakdown alone. The 448 K5 constructor fixtures plus 16 K6 constructor fixtures give 464 cluster-derived rendered rows, which is a whole number of clusters at two variants each, giving 232 clusters and therefore 232 cluster-derived base items rather than 464. The 16 indicator truth-table fixtures, 14 not-applicable branch fixtures and 8 scorer branch fixtures give 38 non-cluster rows, and the total is 502. The unit confusion the finding recorded is gone and the derivation fails closed if the cluster-derived rows are ever not a whole number of clusters.

**Closes the original defect:** true. **Creates a new defect:** false.

Evidence fields: `proposed_statistics.i0_fixture_breakdown`, `proposed_statistics.i0_fixture_unit_rule`, `operation_projection.deterministic_I0_fixtures`

### `S3MR2-010` - PARTIALLY_RESOLVED

**Drafting party's claim.** sampling_frame_v0_4 registers an executable stochastic specification for every gate-bearing atomic cell, with named supports, exact rational weights summing to one, deterministic pre-draw validity predicates, a rejection probability of zero by construction, with-replacement draws, retained duplicates and disjoint split namespaces, and retires the deterministic complete-block assignment.

**Reviewer's evidence.** The stochastic half of the repair is real and complete, and it is the repair the exact binomial actually needed. The reviewer revalidated all 34 sampling cells independently: every sampled parameter's weights sum to exactly one, every registered joint support equals the product of its parameter supports, every joint weight closes to one, every draw rule is with replacement, every cell declares that its parameters are independently drawn per draw ordinal, all 34 namespaces are pairwise distinct and the development and confirmation namespace sets are disjoint. No template-level clustering was found: no cell draws a template once and generates a batch beneath it. The K5 nuisance support is 32 states at exactly 1/32 and the multiple-of-32 restriction is retired everywhere in the reviewer's own unrestricted integer search. The registered rejection probability of zero follows from deterministic, pre-model, satisfied-by-construction predicates rather than from assertion. What the repair does not supply is the deterministic half. No byte-exact stem, option-line format, option separator, instruction sentence or answer cue is registered anywhere, so the generator cannot yet be instantiated and the two K6 cells in particular have no registered manipulated string. That gap is recorded as new finding S3MR3-010, and it is the reason the K6-SEP referent defect was not visible to anyone reading only the prose.

**Closes the original defect:** false. **Creates a new defect:** false.

Evidence fields: `sampling_frame_v0_4.binding_stochastic_model`, `sampling_frame_v0_4.development_sampling_cells`, `sampling_frame_v0_4.confirmation_sampling_cells`, `sampling_frame_v0_4.rejection_contract`, `sampling_frame_reconstruction`, `counterbalancing_design.k6_renderings.renderings`

## 4. Earlier-review non-regression matrix

Eighteen of the twenty first-review findings are not reopened and twenty-one of the twenty-two unresolved items are not reopened, with UR-22 correctly remaining an open blocking operator decision. S3MR-001 and S3MR-002 are partially reopened by the K6-SEP referent defect, which restores in one cell the very condition those findings closed: a single registered floor applied to a cell whose estimand is not the estimand the floor was derived for. This matrix rewrites neither prior review.

| first-review finding | non-regression status |
| --- | --- |
| `S3MR-001` | PARTIALLY_REOPENED |
| `S3MR-002` | PARTIALLY_REOPENED |
| `S3MR-003` | NOT_REOPENED |
| `S3MR-004` | NOT_REOPENED |
| `S3MR-005` | NOT_REOPENED |
| `S3MR-006` | NOT_REOPENED |
| `S3MR-007` | NOT_REOPENED |
| `S3MR-008` | NOT_REOPENED |
| `S3MR-009` | NOT_REOPENED |
| `S3MR-010` | NOT_REOPENED |
| `S3MR-011` | NOT_REOPENED |
| `S3MR-012` | NOT_REOPENED |
| `S3MR-013` | NOT_REOPENED |
| `S3MR-014` | NOT_REOPENED |
| `S3MR-015` | NOT_REOPENED |
| `S3MR-016` | NOT_REOPENED |
| `S3MR-017` | NOT_REOPENED |
| `S3MR-018` | NOT_REOPENED |
| `S3MR-019` | NOT_REOPENED |
| `S3MR-020` | NOT_REOPENED |

| unresolved item | non-regression status |
| --- | --- |
| `UR-01` | NOT_REOPENED |
| `UR-02` | NOT_REOPENED |
| `UR-03` | NOT_REOPENED |
| `UR-04` | NOT_REOPENED |
| `UR-05` | NOT_REOPENED |
| `UR-06` | NOT_REOPENED |
| `UR-07` | NOT_REOPENED |
| `UR-08` | NOT_REOPENED |
| `UR-09` | NOT_REOPENED |
| `UR-10` | NOT_REOPENED |
| `UR-11` | NOT_REOPENED |
| `UR-12` | NOT_REOPENED |
| `UR-13` | NOT_REOPENED |
| `UR-14` | NOT_REOPENED |
| `UR-15` | NOT_REOPENED |
| `UR-16` | NOT_REOPENED |
| `UR-17` | NOT_REOPENED |
| `UR-18` | NOT_REOPENED |
| `UR-19` | NOT_REOPENED |
| `UR-20` | NOT_REOPENED |
| `UR-21` | NOT_REOPENED |
| `UR-22` | REMAINS_UNRESOLVED_BLOCKING_OPERATOR_DECISION |

This matrix verifies that draft-v0.4 did not reopen a previously resolved issue. It rewrites neither prior review; both remain valid immutable rejections.

## 5. New findings

| id | severity | fundamental | title |
| --- | --- | --- | --- |
| `S3MR3-001` | **BLOCKING** | false | The K6-SEP contrast cell has no referent for the option-less selectable profiles S2 and S3, yet is registered applicable, counted and gate-bearing for both |
| `S3MR3-002` | **MAJOR** | false | The drafting derivation table still admits the never-selectable profile S4 to two confirmation rows, so the S3MR2-004 repair is absent from the artifact the protocol names as its derived source |
| `S3MR3-003` | **MAJOR** | false | The retired J_both invariance construct and the withdrawn sample size 256 survive in active charter, README and handoff text, contradicting two explicit protocol claims |
| `S3MR3-004` | **MINOR** | false | The claimed enforcement of the active-claim term prohibition is narrower than the registered scope |
| `S3MR3-005` | **MINOR** | false | S4 still lists I4 among its applicable gates although every decision-bearing field records I4 as not_applicable to S4 |
| `S3MR3-006` | **MINOR** | false | A stop state is registered in the gate truth table that the total state machine does not contain |
| `S3MR3-007` | **MINOR** | false | The per-cell power target is not monotone in n immediately above each registered sample size, and this is disclosed nowhere |
| `S3MR3-008` | **MINOR** | false | Active protocol fields still name a second independent methods review as the governing or pending review |
| `S3MR3-009` | **MINOR** | false | The end-to-end conclusion string is narrower than the union-bound argument that supports it |
| `S3MR3-010` | **MAJOR** | false | The registered generator fixes the sampled parameters but not the deterministic rendering surface, so the two K6 cells are not instantiable without a later substantive design choice |

### `S3MR3-001` - BLOCKING (fundamental: false)

**The K6-SEP contrast cell has no referent for the option-less selectable profiles S2 and S3, yet is registered applicable, counted and gate-bearing for both**

draft-v0.4 registers both K6 contrast cells as applicable to every interface profile, on the stated ground that every profile is rendered so a rendering contrast always has a referent. That ground fails for K6-SEP under S2 and S3. The variant rendering R-sep is registered as identical to R-base except for the separator string between a label and its option content, and S2 and S3 render no option list and no label symbol at all.

**Rationale.** With no label and no option content there is no separator between them, so under S2 and S3 the two registered variants of a K6-SEP cluster are byte-identical. The protocol registers the S2 and S3 scoring surfaces as deterministic argmaxes over a restricted vocabulary at one position with a registered deterministic tie-break, and states that model sampling contributes no randomness and that the model is a deterministic measurement device. An identical prompt therefore yields an identical score, so J_joint_correct in that cell is identically the marginal correctness indicator of a single scoring of the baseline. The cell is not a presentation pair; it is a self-comparison whose estimand is a plain marginal accuracy against a floor derived for a joint-correctness estimand.

**Consequence.** A gate-bearing atomic cell can be passed without testing the construct it is registered to test, for two of the three selectable profiles. The effect is concentrated exactly where it matters most: S2 is the preferred profile and the first in the frozen selection order, and K6-SEP is one of only two I3 cells S2 and S3 possess, so half of the joint-correctness evidence behind the design's preferred outcome is a self-comparison. The registered per-profile claim ceiling for S2 and S3, which states joint robust correctness for the two applicable K6 pairs, therefore claims more than a pass can support. This is also the design's own prohibited case: the protocol states that a transformation with no referent must be recorded not_applicable, that not_applicable is never a pass, and that claiming a not_applicable transformation demonstrates robustness is a prohibited claim.

**Successor implication.** A bounded amendment must decide, as a substantive design act, either to record separator_rendering as not_applicable for S2 and S3 and re-derive their cell census and claim ceiling, or to register a separator factor that actually exists in the option-less prompt, or to state explicitly that S2 and S3 carry a single genuine I3 contrast. It must not be closed by editing the claim text alone.

**A required repair alters:** `applicability`, `atomic_cell`, `claim_ceiling`

Evidence paths: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_review_packet_v0_4.md`

Evidence fields: `i3_contrast_registry.k6_applicability.applicable_profiles`, `i3_contrast_registry.k6_applicability.semantics`, `counterbalancing_design.k6_renderings.renderings[R-sep].description`, `counterbalancing_design.k6_contrasts[K6-SEP].varied_factor`, `interface_profiles[S2].prompt_and_rendering_contract`, `interface_profiles[S3].prompt_and_rendering_contract`, `interface_profiles[S2].transformation_applicability.separator_rendering`, `interface_profiles[S3].transformation_applicability.separator_rendering`, `gate_truth_table.rows[S2].I3_K6`, `gate_truth_table.rows[S3].I3_K6`, `claim_ceiling.i3_claim_ceiling_by_profile.S2.applicable_cells`, `claim_ceiling.i3_claim_ceiling_by_profile.S3.applicable_cells`

### `S3MR3-002` - MAJOR (fundamental: false)

**The drafting derivation table still admits the never-selectable profile S4 to two confirmation rows, so the S3MR2-004 repair is absent from the artifact the protocol names as its derived source**

The amended protocol removes S4 from every confirmation applicability list and its schema constrains confirmation applicable_profiles to S1, S2 and S3. The committed derivation table, which the protocol registers as its derivation_tables and as the single structured source for these values, still lists S1, S2, S3 and S4 in the confirmation I1_I3 family row and in the confirmation I2 family row.

**Rationale.** The reviewer's independent comparison classified this difference after reproducing every binding number in the same rows without disagreement, so the defect is isolated to applicability metadata rather than to arithmetic. It survived because no committed test asserts the applicable_profiles field of any table row, and because the table's gate-family row shape cannot represent per-component applicability at all: the repair confining I1b and K5 confirmation to S1 has no place to live in the table and is simply absent.

**Consequence.** The protocol asserts that the draft-v0.3 defect of listing S4 in every confirmation row is repaired, while the derived artifact it names as its source still exhibits that defect verbatim. Any consumer that follows the protocol's own pointer to the derivation table reads the unrepaired applicability, and the confirmation lifecycle guarantee that a never-selectable profile can never appear is not actually enforced end to end.

**Successor implication.** Regenerate the derivation table from the amended protocol so that confirmation applicability agrees, give the table a per-component row shape or an explicit per-component applicability field, and add a committed assertion that binds it.

**A required repair alters:** `derived_table_only`, `committed_test_only`

Evidence paths: `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/protocol/interface_calibration_protocol_draft.json`, `tests/test_study3_design.py`

Evidence fields: `design_statistics_tables.json :: confirmation_exact_binomial_components[I1_I3_joint_correctness_floor].applicable_profiles`, `design_statistics_tables.json :: confirmation_exact_binomial_components[I2_headroom_floor].applicable_profiles`, `proposed_statistics.derivation_tables`, `proposed_statistics.confirmation_applicability_rule.s4_can_never_appear`, `proposed_statistics.confirmation_applicability_rule.v0_3_defect_repaired`

### `S3MR3-003` - MAJOR (fundamental: false)

**The retired J_both invariance construct and the withdrawn sample size 256 survive in active charter, README and handoff text, contradicting two explicit protocol claims**

draft-v0.4 states that the withdrawn sample sizes appear in no active field and that no active claim asserts invariance, equivalence or an absent presentation effect. Both statements are false in reviewed paths. The charter still asks the draft-v0.3 research question, still names J_both as the primary indicator requiring invariance across the two variants, still records the resolution of OD6 as a single I3 floor at power at least 0.90 giving n = 256, still carries a draft version row reading draft-v0.3, and still names a second independent methods review as the legal next action in two places. Both READMEs and the handoff repeat the invariance construct, and the READMEs repeat n = 256.

**Rationale.** The v0.4 amendment touched the charter only to update the state row, rename one disposition string and append a summary section; sections 1 to 9 still describe draft-v0.3 in the present tense. The READMEs prepend a versioned banner and leave the older body in place, so a single document states two mutually exclusive primary indicators and two mutually exclusive sample sizes with nothing marking the older text as historical. S3MR2-001 was a finding about claim language, so claim language outside the protocol JSON is squarely within its scope.

**Consequence.** A reader of the charter is told that Study 3 asks a presentation-effect question and that the primary indicator requires invariance, which is exactly the estimand and claim mismatch the second review recorded as blocking. The protocol's own universal statements about withdrawn values and prohibited terms are falsified by reviewed paths.

**Successor implication.** Bring the charter, both READMEs and the handoff into conformance with the registered v0.4 design, or mark the superseded passages unambiguously as historical narrative.

**A required repair alters:** `narrative_text_only`

Evidence paths: `studies/study3/RESEARCH_CHARTER_DRAFT.md`, `studies/README.md`, `studies/study3/README.md`, `studies/study3/NEXT_THREAD_HANDOFF.md`, `studies/study3/protocol/interface_calibration_protocol_draft.json`

Evidence fields: `RESEARCH_CHARTER_DRAFT.md draft version row`, `RESEARCH_CHARTER_DRAFT.md section 2 What Study 3 asks`, `RESEARCH_CHARTER_DRAFT.md section 4 design commitment 3`, `RESEARCH_CHARTER_DRAFT.md section 8 open decisions, OD6 resolution`, `RESEARCH_CHARTER_DRAFT.md legal next action statements`, `studies/README.md primary indicator and n = 256 sentences`, `studies/study3/README.md Sizing and multiplicity paragraph`, `studies/study3/NEXT_THREAD_HANDOFF.md Three I3 indicators, one primary`, `proposed_statistics.sample_sizes.n_256_and_128_status`, `proposed_statistics.active_claim_term_prohibition.scope`

### `S3MR3-004` - MINOR (fundamental: false)

**The claimed enforcement of the active-claim term prohibition is narrower than the registered scope**

The protocol registers the prohibited-term scope as covering active claim text, success statements, validation-target interpretations, gate questions and what_fails and what_passes clauses, and names tests/test_study3_design.py as its enforcer. The enforcing helper assembles its candidate strings from a hand-picked subset of protocol JSON fields only.

**Rationale.** The scan never reaches the charter, the handoff, either README, the protocol Markdown companion, the review packet or the status report. It also never reaches research_question.draft_question inside the protocol itself. The enforcement therefore cannot detect the residue recorded in S3MR3-003, which is why that residue survived a passing suite.

**Consequence.** A registered prohibition is advertised as enforced while its enforcement covers a strict subset of its declared scope, so a passing test suite is not evidence that the prohibition holds.

**Successor implication.** Either widen the scan to the declared scope or narrow the registered scope and the enforced_by claim to what is actually checked.

**A required repair alters:** `committed_test_only`

Evidence paths: `tests/test_study3_design.py`, `studies/study3/protocol/interface_calibration_protocol_draft.json`

Evidence fields: `tests/test_study3_design.py :: _active_claim_strings`, `tests/test_study3_design.py :: test_active_claim_text_contains_no_presentation_effect_claim`, `proposed_statistics.active_claim_term_prohibition.enforced_by`, `proposed_statistics.active_claim_term_prohibition.scope`

### `S3MR3-005` - MINOR (fundamental: false)

**S4 still lists I4 among its applicable gates although every decision-bearing field records I4 as not_applicable to S4**

The gate truth table records that the draft-v0.3 I4 applicability contradiction is resolved in favour of not_applicable in every location. interface_profiles[S4].applicable_gates still contains I4.

**Rationale.** The reviewer's independently derived cell census gives S4 zero I4 cells, and the independently derived RP I4 projection follows from the selectable profiles alone, so no number depends on the stale entry. The defect is that a universal claim of resolution is made while one location was not updated.

**Consequence.** One artifact still asserts an applicability that the design forbids, and the accompanying claim that the contradiction is resolved everywhere is false.

**Successor implication.** Remove I4 from S4's applicable gate list or qualify the universal claim.

**A required repair alters:** `narrative_text_only`

Evidence paths: `studies/study3/protocol/interface_calibration_protocol_draft.json`

Evidence fields: `interface_profiles[S4].applicable_gates`, `gate_truth_table.i4_applicability_note`, `gate_truth_table.rows[S4].I4`, `gate_hierarchy[I4].applicable_profiles`, `proposed_statistics.retained_exact_binomial_gates[I4].applicable_profiles`

### `S3MR3-006` - MINOR (fundamental: false)

**A stop state is registered in the gate truth table that the total state machine does not contain**

gate_truth_table.legal_stop_states enumerates six stop states including STOP_AWAITING_AUTHORITY, described as the current state. The registered total state machine contains ten states, six of them terminal, and STOP_AWAITING_AUTHORITY is not among them.

**Rationale.** The reviewer independently reconstructed the transition system and confirms it is total, deterministic and fully reachable exactly as registered. The defect is that a second artifact names a legal stop state outside it, which weakens the totality claim as a cross-artifact property even though the machine itself is sound.

**Consequence.** Two artifacts disagree about the registered stop-state set.

**Successor implication.** Either register the pre-execution awaiting-authority state in the state machine or remove it from the legal stop-state list.

**A required repair alters:** `narrative_text_only`

Evidence paths: `studies/study3/protocol/interface_calibration_protocol_draft.json`

Evidence fields: `gate_truth_table.legal_stop_states`, `state_machine_v0_4.states`

### `S3MR3-007` - MINOR (fundamental: false)

**The per-cell power target is not monotone in n immediately above each registered sample size, and this is disclosed nowhere**

The registered sizes are the smallest unrestricted positive integers meeting the per-cell power target, which the reviewer verified by exhaustive search over every positive integer up to the registered ceiling. The target is not monotone above them: it fails again for a short run of larger n before holding for every n.

**Rationale.** Discreteness of the exact binomial rejection region makes realized power non-monotone in n at a fixed level. The registered claim is true as stated, and the reviewer confirms it, but no artifact records that the target is not met for every n at or above the registered size.

**Consequence.** A reader could reasonably infer that any n at or above the registered size satisfies the target. It does not, so a realized cell size that drifted upward by a few units would silently fall below the registered target.

**Successor implication.** Disclose the non-monotonicity beside the search rule, or register the smallest n from which the target holds for every larger n.

**A required repair alters:** `narrative_text_only`

Evidence paths: `studies/study3/analysis/independent_methods_recalculation_tables_v0_4.json`, `studies/study3/protocol/interface_calibration_protocol_draft.json`

Evidence fields: `minimal_sample_size_searches`, `proposed_statistics.sample_sizes.search_rule`, `proposed_statistics.retained_exact_binomial_gates[*].n_is_smallest_unrestricted_positive_integer_meeting_the_target`

### `S3MR3-008` - MINOR (fundamental: false)

**Active protocol fields still name a second independent methods review as the governing or pending review**

Several active fields still refer to the second independent methods review as the review that will adjudicate draft-v0.4.

**Rationale.** The round these fields describe has completed and its disposition is already recorded elsewhere in the same document, so the fields are internally inconsistent with the registered state.

**Consequence.** Round provenance is ambiguous in active fields of the authoritative document.

**Successor implication.** Update the round references.

**A required repair alters:** `narrative_text_only`

Evidence paths: `studies/study3/protocol/interface_calibration_protocol_draft.json`

Evidence fields: `claim_ceiling.no_self_approval`, `proposed_statistics.unresolved[1]`, `proposed_statistics.descriptive_paired_summary.retired_procedure.second_reviewer_question`, `unresolved_operator_decisions[OD7].disposition`

### `S3MR3-009` - MINOR (fundamental: false)

**The end-to-end conclusion string is narrower than the union-bound argument that supports it**

The registered conclusion states that the study returns the designated adequate profile and confirms it. The three union-bound terms establish that an adequate profile is qualified, selected and confirmed, not that a particular designated one is.

**Rationale.** When two or more selectable profiles are adequate, the frozen order returns the highest-priority one, which need not be the profile a reader would call designated. The reviewer re-derived the bound and confirms it is sound for the claim that an adequate profile is returned and confirmed, and that it is also sound for the designated profile if designated is defined as the highest-priority adequate profile. No registered field supplies that definition.

**Consequence.** The published guarantee reads as stronger than what the registered argument proves, in the multi-adequate branch only.

**Successor implication.** Define designated as the highest-priority adequate profile, or restate the conclusion over an adequate profile.

**A required repair alters:** `narrative_text_only`

Evidence paths: `studies/study3/protocol/interface_calibration_protocol_draft.json`

Evidence fields: `power_architecture_v0_4.union_bound_proof.conclusion`, `power_architecture_v0_4.least_favourable_configuration.conditions`

### `S3MR3-010` - MAJOR (fundamental: false)

**The registered generator fixes the sampled parameters but not the deterministic rendering surface, so the two K6 cells are not instantiable without a later substantive design choice**

sampling_frame_v0_4 completely registers the stochastic half of the item generator. No artifact registers a byte-exact question stem, option-line format, option separator, instruction sentence or answer cue for any profile or rendering. The renderings R-base, R-sep and R-instr are defined only by prose descriptions of what they vary.

**Rationale.** For every other cell the unregistered surface strings are nuisance, because the manipulated factor is a sampled parameter with a registered support. For K6-SEP and K6-INSTR the unregistered string is the manipulated factor itself, so the estimand of those cells is not determined by anything currently registered. A later seed or bank authority cannot instantiate the registered distribution without choosing them, and the choice determines what the gate tests.

**Consequence.** The sampling and generator model is not complete enough to instantiate later without a substantive design choice, which section 8 requires for acceptance. It is also the mechanism by which S3MR3-001 went undetected: with no byte-exact templates, nobody could observe that R-sep and R-base coincide under the option-less profiles.

**Successor implication.** Register the byte-exact rendering surface for every profile and rendering, and re-derive the K6 applicability from the registered strings rather than from prose.

**A required repair alters:** `generator_distribution`, `atomic_cell`, `applicability`

Evidence paths: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/protocol/interface_calibration_protocol_draft.md`

Evidence fields: `counterbalancing_design.k6_renderings.renderings`, `i3_contrast_registry.k6`, `interface_profiles[*].prompt_and_rendering_contract`, `bank_construction_policy`, `sampling_frame_v0_4.future_seed_lifecycle`

## 6. Mandatory audit answers

Every question posed by section 6 of the review authority is answered below and in the machine-readable review under `mandatory_audit_answers`. Reviewed fact, reviewer inference and recommendation are distinguished in each answer: a statement about what a registered field says is reviewed fact; a statement beginning with the reviewer's derivation or conclusion is reviewer inference; a statement under **Successor implication** is a recommendation and binds nothing; and an operator decision is named as such and is never resolved here.

**`6.1.a_j_joint_correct_lattice`**

*Re-derive J_joint_correct for every ordered pair in the registered lattice and confirm exactly which cases score 1.*

The reviewer enumerated all sixteen ordered pairs over correct, wrong_a, wrong_b and invalid independently. Exactly one case scores: both variants correct. The remaining fifteen fall into stable wrong, stable invalid, mixed correctness, two different wrong answers and mixed valid and invalid.

**`6.1.b_algebraic_identity`**

*Confirm the algebraic relationship between the historical indicators and the active one.*

Over the full lattice J_cor implies J_inv, so the retired J_both is identically J_cor and identically J_joint_correct. The reviewer verified this by enumeration rather than accepting the assertion.

**`6.1.c_q_parameterisation`**

*Express the joint distribution as q11, q10, q01, q00 and derive p_joint, d and the identity p_joint + d <= 1 with its one-way implications.*

p_joint = q11 and d = q10 + q01 are two functionals of one joint law on four atoms, verified over a rational grid. p_joint + d <= 1 holds identically, and p_joint <= min of the two marginals. A high p_joint therefore forces a small d, while a small d forces nothing about p_joint because q00 absorbs the remaining mass. They are not independent parameters and q11 is not in general the product of the marginals.

**`6.1.d_level_not_contrast`**

*Verify that J_joint_correct is a level, not a contrast.*

Confirmed. It identifies neither the direction, the magnitude nor the existence of a presentation effect, does not distinguish different wrong answers when both variants are wrong, does not distinguish invalid from wrong movement, and is not a general answer-invariance statement.

**`6.1.e_residual_claim_search`**

*Search every active claim, gate question, what_fails clause, validation target, success statement, charter objective, handoff and downstream routing field for residual or implied invariance, equivalence, stability or no-presentation-effect claims.*

Inside the authoritative protocol JSON, the schema, the derived tables and the packet the search is clean: prohibited vocabulary appears only in prohibited-claim lists, retired-procedure records and clearly labelled historical narrative. Outside it the search is not clean. The charter objective, a charter design commitment, both READMEs and the handoff still assert the retired invariance construct in active text. Recorded as S3MR3-003.

**`6.1.f_descriptive_leakage`**

*Verify that every quantity derived from discordance or the broader outcome lattice is descriptive only and cannot leak into a later decision.*

Confirmed. The paired 2x2 table, its off-diagonal counts, the discordance count and rate, the paired accuracy difference and the historical indicators all carry DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY, and none carries a null, alpha, p-value, pass or fail, ranking, rescue, eligibility, selection, confirmation or claim role. The reviewer independently reconstructed the selection map and confirms eligibility is a function of the component pass pattern and the activation condition alone, so no descriptive quantity has a reachable decision path.

**`6.1.g_discordance_gate_not_required`**

*Decide whether a presentation-sensitivity gate is necessary, without requiring one merely because d is available at zero extra forwards.*

Not necessary for the registered purpose. The decision Study 3 must inform is whether an interface reliably registers competence that is present, which is a level question, and p_joint + d <= 1 already bounds correctness-state discordance from above whenever the gate passes. The reviewer therefore does not invent a delta0, a d1 or a power claim, and does not classify the absence of a d gate as a defect.

**`6.1.h_internal_validity_of_the_narrowed_claim`**

*Is the narrowed J_joint_correct design internally valid for its exact registered generator-local claim?*

Yes for every cell whose registered transformation has a referent, and the statistical machinery supporting it was independently reproduced with no numeric disagreement. No for the K6-SEP cell under S2 and S3, where the transformation is null and the cell tests a marginal accuracy against a joint-correctness floor.

**`6.1.i_sufficiency_for_purpose`**

*Is the narrowed claim still sufficient to serve Study 3's interface-calibration purpose and the planned downstream mechanistic study?*

Yes in kind, subject to one bounded repair in degree. A level of joint correctness across a registered presentation pair is the right quantity for deciding whether an instrument reads out competence that is present, and it is strictly more informative than a marginal accuracy because it requires correctness under both members of the pair. The insufficiency is local: the preferred profile retains only one genuine presentation pair once the K6-SEP defect is corrected, which is thin evidence for the profile the design most wants to select.

**`6.1.j_strongest_permitted_claims`**

*State the strongest permitted claim for S1, S2, S3 and non-selectable S4.*

Recorded field by field in i3_estimand_decision.strongest_permitted_claim_by_profile. None expands beyond cell-wise joint robust correctness on the registered generator distribution, and S4 carries no selection or confirmation claim at all.

**`6.2.a_generator_tuples`**

*For every one of the 34 sampling cells, reconstruct the generator tuple, support, exact weights, validity predicate, independent unit, with-replacement rule and output-to-Bernoulli mapping.*

Done independently for all 34. Every sampled parameter's weights sum to exactly one, every registered joint support equals the product of its parameter supports, every joint weight closes to one, every cell declares the base item or the base-item contrast cluster as its independent unit, and every draw rule is with replacement.

**`6.2.b_draw_ordinal_and_template_clustering`**

*Verify that every draw ordinal independently draws the complete registered generator tuple, and detect any template-level clustering.*

Every cell registers that its parameters are independently drawn per draw ordinal. No cell draws a template once and generates a batch beneath it, and the protocol explicitly warns that differing identifiers do not imply independence, which is why the template family and every nuisance condition are themselves sampled parameters. No template-level clustering was found.

**`6.2.c_weights_and_duplicates`**

*Verify all exact weights sum to one including the 32 K5 nuisance states at 1/32, and that duplicate draws are retained.*

Confirmed. The K5 nuisance support is 4 x 4 x 2 = 32 states at exactly 1/32, closing to one. Duplicates must be retained, redrawing for uniqueness or balance is prohibited, and the draft-v0.3 duplicate-rejection text is withdrawn and reversed.

**`6.2.d_rejection_probability`**

*Verify the registered rejection probability of zero follows from deterministic pre-model support validity rather than from an untested assertion.*

Confirmed. All four validity predicates are deterministic, evaluated before any model operation, and satisfied by construction: the correct answer is drawn from the answer domain, distractors are drawn without replacement from the domain minus the correct answer, both alphabets are disjoint from the domain, and ground truth is computed by the harness. The predicates are retained as fail-closed guards rather than as an active rejection step, and the conditional target distribution is registered for the counterfactual case.

**`6.2.e_sampling_versus_evaluation_cell`**

*Distinguish a sampling cell from an evaluation cell and verify that item-stream reuse preserves marginal iid validity while inducing permitted cross-cell dependence.*

A sampling cell excludes interface profile and checkpoint role; an evaluation cell is a sampling cell crossed with one applicable profile and one applicable role. One iid stream per sampling cell is reused across its evaluation cells, so each evaluation cell is marginally iid Bernoulli and cells sharing items may be dependent. That dependence is permitted only because every binding joint bound is a union bound valid under arbitrary dependence, which the reviewer verified by exhaustive enumeration.

**`6.2.f_namespace_separation`**

*Verify physical and identity separation between development and confirmation namespaces, between target and positive-reference roles, and wherever disjointness is claimed.*

Confirmed. All 34 namespaces are pairwise distinct and the development and confirmation namespace sets are disjoint. The split is a field of the generator key, so the D, C and P3Q supports are physically disjoint by construction, the partition is outcome-blind and frozen before any seed draw, and cross-split reuse is prohibited. Contrast cells draw disjoint base-item identities.

**`6.2.g_instantiability`**

*Determine whether the future generator implementation, seed authority and bank authority can instantiate the registered distribution without a substantive missing choice.*

No. The stochastic half is complete; the deterministic rendering surface is not registered at all, and for the two K6 cells the unregistered string is the manipulated factor. Recorded as S3MR3-010. Null is correctly not treated as zero and nothing is treated as already frozen.

**`6.2.h_external_validity_ceiling`**

*State the external-validity ceiling explicitly and decide whether it is acceptable for the next scientific stage.*

The ceiling is generator-local: passing supports only the registered synthetic generator distributions for the named tasks and roles. It is stated explicitly in the maximum pass claim, the permitted I3 statement and the research question. It is acceptable for the registered next decision, which is only whether to design a later substantive protocol, and it is not silently generalized anywhere. No bridge to natural task distributions is registered, which is recorded as an unresolved methods item rather than a rejection driver because the design does not claim a bridge.

**`6.3.a_recomputation`**

*For I1a, I1b, I2, I3 and I4, separately for development and confirmation, recompute p0, p1, exact alpha, n, pass count, exact null tail and exact power from exact rationals.*

Done independently in exact integer and exact-rational arithmetic with no floating point in any decision. All ten component characterisations reproduce the registered values exactly, including every published twelve-digit decimal.

**`6.3.b_unrestricted_search`**

*Search every unrestricted positive integer n up to the registered ceiling and confirm the multiple-of-32 restriction does not survive.*

Every positive integer from 1 to the registered ceiling of 4096 was tested for each component with no divisibility restriction of any kind. The registered development sizes 413, 214 and 448 are the smallest positive integers meeting the per-cell target. The retired multiple-of-32 restriction plays no role in the reviewer's search and none of the three sizes is a multiple of 32.

**`6.3.c_pass_counts_and_minimality`**

*Verify the development pass counts 389, 129 and 383, the confirmation pass counts 388, 127 and 381, and the claimed minimality and non-degeneracy.*

All six reproduce exactly. Each pass count is minimal at its level, verified by confirming that the tail one below it exceeds the level, and no rejection region is degenerate because every pass count is strictly less than its n.

**`6.3.d_cell_counts_and_m_max`**

*Reconstruct the exact gate-bearing cell counts for every profile and verify m_max = 43 is taken only over selectable profiles and that S4's diagnostic cells never enter selection or confirmation power.*

Reconstructed from applicability rather than read: S1 has 33 + 6 + 4 = 43, S2 and S3 have 9 + 6 + 4 = 19, and S4 has 33 + 6 + 0 = 39 and is never selectable. m_max = 43 is the maximum over the selectable profiles only, and S4's 39 cells enter no budget, no union and no confirmation.

**`6.3.e_budget_ladder`**

*Independently derive the per-stage budget 19/400, the per-cell budget 19/17200, the per-cell target 17181/17200, the profile-stage floor 381/400, the panel bound 1/200 and the end-to-end floor 9/10.*

The per-stage budget is a registered design input. Everything else was derived: 19/400 divided by m_max = 43 gives 19/17200; one minus that gives 17181/17200; one minus 43 times 19/17200 gives 381/400 and equals one minus 19/400 exactly; the fixed denominator 3 times the per-component level 1/600 gives 1/200; and one minus 19/400 minus 1/200 minus 19/400 gives 9/10.

**`6.3.f_arbitrary_dependence`**

*Verify every binding inequality under arbitrary dependence and confirm no independence product strengthens any binding claim.*

Every binding bound is a union bound and therefore valid under arbitrary dependence. The reviewer verified the union bound, its tightness under a disjoint witness, the Frechet intersection lower bound and the intersection-union size bound by exhaustive enumeration over 1716 finite joint distributions, which covers comonotone and countermonotone extremes. No independence assumption appears in any binding step, and the protocol confines independence products to explicitly labelled sensitivity analysis with no authority.

**`6.3.g_least_favourable_configuration`**

*Verify the registered least-favourable configuration is sufficient for the end-to-end guarantee, including higher-priority inadequate profiles, selection order, one-shot confirmation and the confirmation-generating distribution.*

Sufficient. Given the configuration, if the designated adequate profile qualifies and no selectable profile lying in its null is falsely qualified, then any higher-priority qualified profile must itself be adequate, so the profile entering confirmation is adequate and the third term bounds its confirmation failure. The only imprecision is the wording of the conclusion string, recorded as S3MR3-009.

**`6.3.h_exclusions`**

*Verify the indifference regions, I0 failure, distribution shift, invalid sampling frame and protocol deviations are excluded from the guarantee rather than hidden inside it.*

All five are listed explicitly as not covered by the power guarantee, in the protocol and in the packet. They are excluded openly rather than absorbed.

**`6.3.i_power_labels`**

*Distinguish per-cell power, profile-stage power, probability of correct selection and full development-plus-confirmation power in every artifact.*

The four are named and scoped separately in the registered power vocabulary, the selection-return characteristic is explicitly never called power, and relabelling per-cell power as any of the others is prohibited. The reviewer found no artifact that conflates them.

**`6.4.a_formal_hypotheses`**

*Write formal null and alternative sets for each atomic cell, the within-profile conjunction, the union over the three selectable profiles, development selection and the one confirmed profile.*

Written in multiplicity_and_selection_decisions.formal_null_sets. The within-profile null is the union of the cell nulls and the test is an intersection-union test; the across-profile event is a union and is Bonferroni-corrected by a denominator fixed before data.

**`6.4.b_intersection_union`**

*Verify intersection-union logic matches the exact profile claim and that a per-component development alpha of 1/600 bounds a falsely qualified profile without an extra within-profile correction.*

Correct. A profile qualifies only when every applicable cell rejects, so under any profile null at least one applicable cell is at or below its p0 and the probability that all cells reject is at most that cell's level. The reviewer verified the underlying result by exhaustive enumeration and confirms that the protocol's assumptions satisfy the conditions Berger and Hsu require. No further within-profile correction is needed and none is applied.

**`6.4.c_fixed_denominator`**

*Verify the fixed three-profile union bound gives 1/200 and is never data-dependently reduced.*

Confirmed. All sixteen branches of the independently reconstructed selection map carry a denominator of exactly 3, including every branch in which S3's activation condition is not met, and shrinking it is registered as prohibited.

**`6.4.d_selection_map`**

*Reconstruct the full selection map including inapplicability, tie, no-eligible-profile, error and ambiguity cases, and verify S3 cannot be selected outside its registered applicability condition.*

Reconstructed independently from the frozen order and the activation condition, producing all sixteen rows with no disagreement against the registered map on eligible set, selected profile or stop flag. The order resolves every tie deterministically, the empty-eligible case maps to a stop, and S3 is selected in no branch in which its activation condition is false. Error and ambiguity are handled by the state machine rather than the map, which is where they belong.

**`6.4.e_confirmation_applicability`**

*Verify confirmation applicability is the intersection of the selected profile with component applicability, that S4 never appears, and that I1b and K5 apply only to S1.*

Correct in the authoritative protocol and its schema. Not correct in the derived statistics table, which still lists S4 in two confirmation rows and cannot express the I1b and K5 restriction at all. Recorded as S3MR3-002.

**`6.4.f_confirmation_lifecycle`**

*Verify confirmation is physically disjoint, separately authorized, read once, spent on error or ambiguity, and cannot be retried, retuned, rescued or used to select another profile.*

Confirmed in every respect. The split is a field of the generator key so it is physically disjoint; it is reachable only through a gated state requiring a later authority; it is read exactly once for exactly one preselected profile; error or ambiguity spends it and maps to a dedicated terminal state; and reselection, substitution and rescue are all prohibited.

**`6.4.g_no_rescue`**

*Verify no descriptive lattice statistic, S4 result, label diagnostic, pooled statistic or confidence interval can rescue a failed gate.*

Confirmed. Pooling is prohibited as a rescue in thirteen registered ways, S4 is excluded from every success union, and every descriptive family is registered without gate, eligibility, selection, confirmation or rescue authority. The independently reconstructed selection map takes no descriptive input.

**`6.5.a_state_machine`**

*Reconstruct the state machine independently and prove it is total and deterministic, with every registered event carrying exactly one next state and every terminal state reachable.*

Ten states, six terminal, eleven transitions. No state-event pair carries two next states, every target is a registered state, the entry state is unique, every non-terminal state has an outgoing transition and all six terminal states are reachable from the entry state. Total and deterministic as claimed.

**`6.5.b_i0_mapping`**

*Verify I0 failure, error or ambiguity maps only to STOP_INSTRUMENT_DEFECT and makes no interface claim.*

All three non-pass events at the instrument state map to STOP_INSTRUMENT_DEFECT and to nothing else, and that terminal state's registered claim states the instrument is defective and that nothing was measured about any interface. I0 is a global precondition and is not part of profile adequacy.

**`6.5.c_i0_fixture_accounting`**

*Reconstruct I0 fixture accounting and resolve units explicitly.*

448 K5 plus 16 K6 constructor fixtures give 464 cluster-derived rendered rows, a whole number of clusters at two variants each, hence 232 clusters and 232 cluster-derived base items. 16 truth-table plus 14 not-applicable plus 8 scorer fixtures give 38 non-cluster rows. The total is 502 rendered rows and zero model operations.

**`6.5.d_i4_structure`**

*Verify I4's p0 = 4/5, p1 = 9/10, four operation-family-by-depth cells, applicability, conjunction and disjointness from external P3-Q.*

Confirmed. Two registered operation families crossed with two registered depths give exactly four cells per candidate profile, evaluated at the positive-reference role only, applicable to the three selectable profiles and not to S4, combined as an intersection-union conjunction. P3-Q is a separate external stage on items disjoint from the I4 items and through an interface that is not S1, S2, S3 or S4.

**`6.5.e_od2_boundary`**

*Verify unresolved OD2 does not make the generic I4 method internally undefined, and list every field a later OD2 authority must freeze.*

The generic method is internally defined: the null, the alternative, the level, the sample size, the pass count, the cell structure, the unit and the conjunction rule are all registered and were independently reproduced, and none of them depends on the identity of the reference. Only the instantiation is deferred. The fields a later authority must freeze are enumerated in i4_p3q_od2_decision, and this review selects, prefers, pins, ranks, resolves, downloads, tokenizes, loads, runs, prequalifies and substitutes nothing.

**`6.5.f_ordering_constraint`**

*Verify the ordering constraint P3Q >= 19/20 > I4 p1 = 9/10 > I4 p0 = 4/5 is mathematically and procedurally sufficient, and that no document treats it as completed qualification.*

Mathematically the inequalities hold in exact rational arithmetic. Procedurally the constraint is sufficient for the generic design because it guarantees that any admissible reference is required to be strictly more capable than the floor it must clear through the candidate interface, which is what makes an I4 failure attributable to the interface. No document treats it as completed qualification: the prequalification record states the stage is not executed, RP is not selected and P3-Q is not authorised.

**`6.6.a_work_streams`**

*Recompute every work stream from primitive counts and units rather than copying totals.*

All six recomputed from applicability, sample sizes, variants per cluster, role count and the registered token bound. Deterministic I0 fixtures 502 rendered rows; target-role development 33,543 rendered rows and sequence-level evaluations; external P3-Q null; RP I4 3,584; selected-profile one-shot confirmation upper bound 27,856 under S1; S4 26,064 generation calls, 26,064 prefill evaluations, at most 390,960 incremental decode evaluations, at most 417,024 sequence-level evaluation equivalents and at most 417,024 generated tokens. Every figure reproduces exactly.

**`6.6.b_unit_distinctions`**

*Verify the distinction between a sequence-level evaluation, prefill evaluation, incremental decode evaluation, generation call, generated token and runtime batched model call.*

All six are registered as distinct units with distinct definitions, and equating a sequence-level evaluation with a runtime batched forward call is prohibited. The runtime batched forward call is left null because batch packing is a future execution property.

**`6.6.c_null_not_zero`**

*Verify external P3-Q quantities are null rather than zero while OD2 is unresolved, and that no grand total is legal while a cost-bearing stream is null.*

Confirmed. Every P3-Q quantity is null with an explicit unresolved status and a stated reason that zero would assert a reference needs no qualification work. No grand total is published and treating the null as zero in a total is registered as prohibited.

**`6.6.d_s4_headroom_scope`**

*Assess the headroom scope of the S4 composite and decide whether excluding every generation-enabled profile from the selectable set leaves a purpose-critical gap.*

S4 changes chat template, free generation, output length, decoding and parser simultaneously, so its success while S1 to S3 fail supports only that a generation-enabled composite shows headroom the restricted interfaces lack; it identifies no cause. The exclusion is nevertheless the direct implementation of the Study 1 lesson and is the right choice for a downstream mechanistic study, and S4 is retained and fully costed as a diagnostic. The reviewer does not classify the absent generation axis as a purpose-critical gap and does not create S5.

**`6.7.a_harness_diff`**

*Diff the v0.3 historical-review module before and after the erratum and verify the semantic change is limited to anchoring and snapshot isolation.*

The change adds a declared historical-input list, a forbidden-current-bytes list, an AST-based reader of the generator's own declared inputs, and a snapshot materialiser; it repoints two tests at the reviewed commit. The collected node-ID set is identical at 35 before and after, no skip, xfail or bare except is introduced, assertion count rises from 133 to 136, fail-closed pytest.fail sites rise from 1 to 3, and no expected scientific value changes.

**`6.7.b_harness_invariants`**

*Verify commit anchoring, snapshot isolation, input-coverage assertion, unchanged node-ID set, unchanged v0.3 recalculation bytes and results, and non-vacuity.*

The anchor is the v0.3 reviewed commit and is reachable from the publication candidate. Historical blobs are read through git rather than from the working tree, so no line-ending conversion can corrupt them. The snapshot asserts that every input the generator declares is present and that nine named current-draft artifacts are absent. The immutable v0.3 recalculation script and table are unchanged at 58,317 bytes and 66,631 bytes with their registered digests. Non-vacuity is demonstrated by bound ACR probes.

**`6.7.c_registry_history`**

*Verify AR-0246 and AR-0269 preserve history without creating two contradictory claims about the current blob.*

The harness identity was unchanged across the published base and the two draft-v0.4 commits preceding the erratum, and changed only in the erratum commit. AR-0246 records the pre-erratum identity and AR-0269 the current one, with AR-0269 stating explicitly that AR-0246 retains the pre-erratum identity. There is no unregistered intermediate state and no contradiction.

**`6.7.d_counters_versus_mutations`**

*Reconcile counters and flags with actual repository mutations, so that provenance statements do not deny an authorized historical-harness edit that actually occurred.*

Every empirical and model operation counter is zero and every authority flag is false, which the reviewer verified against the reviewed object. The historical-harness edit is disclosed as a scope erratum in the amendment record, in the run log, in the handoff and in a new artifact row, so no provenance statement denies it. The two classes are kept apart correctly.

**`6.8.a_internal_validity_verdict`**

*Return METHOD_INTERNAL_VALIDITY_VERDICT.*

ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR. The statistical machinery is valid and fully reproduced; the shortfall is a registered applicability that does not match what two selectable profiles render, plus an unregistered rendering surface.

**`6.8.b_purpose_verdict`**

*Return STUDY3_PURPOSE_AND_CONSTRUCT_RELEVANCE_VERDICT, reached separately.*

ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR. The narrowed level estimand does serve the instrument-calibration purpose and the downstream study, and the generation exclusion is correct. The shortfall is that the preferred profile retains only one genuine presentation pair once the K6-SEP defect is corrected.

## 7. Statistical tables

All values below are **proposed design parameters, not measurements**. Every one was derived independently in exact integer and exact-rational arithmetic before any drafting output was opened.

### 7.1 Exact-binomial components - development

| gate | null | p1 | alpha | n | unit of n | pass count | exact null tail | exact power at p1 | degenerate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `I1a` | `p <= 9/10` | `97/100` | `1/600` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | 389 | 0.001664632930 | 0.999129439838 | false |
| `I1b` | `p <= 9/10` | `97/100` | `1/600` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | 389 | 0.001664632930 | 0.999129439838 | false |
| `I2` | `p <= 1/2` | `7/10` | `1/600` | 214 | base items per primitive-family cell | 129 | 0.001597676081 | 0.999042859186 | false |
| `I3` | `p <= 9/10` | `97/100` | `1/600` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | 389 | 0.001664632930 | 0.999129439838 | false |
| `I4` | `p <= 4/5` | `9/10` | `1/600` | 448 | RP base items per operation-family x depth cell per candidate profile | 383 | 0.001620609599 | 0.999005509196 | false |

### 7.2 Exact-binomial components - confirmation

| gate | null | p1 | alpha | n | pass count | exact null tail | exact power at p1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `I1a` | `p <= 9/10` | `97/100` | `1/200` | 413 | 388 | 0.003020762720 | 0.999609916012 |
| `I1b` | `p <= 9/10` | `97/100` | `1/200` | 413 | 388 | 0.003020762720 | 0.999609916012 |
| `I2` | `p <= 1/2` | `7/10` | `1/200` | 214 | 127 | 0.003765544908 | 0.999646587923 |
| `I3` | `p <= 9/10` | `97/100` | `1/200` | 413 | 388 | 0.003020762720 | 0.999609916012 |
| `I4` | `p <= 4/5` | `9/10` | `1/200` | 448 | 381 | 0.003582895662 | 0.999626931069 |

Confirmation sizes are conservative reuse of the development sizes, not minimal confirmation sizes. Confirmation applicability is the intersection of a component's selectable profiles with the single selected profile, so `S4` can never appear and `I1b` and `K5` are confined to `S1` - correctly in the protocol, and incorrectly in the derived table, which is finding `S3MR3-002`.

### 7.3 Unrestricted positive-integer sample-size search

| gate | search restriction | ceiling | first admissible n | registered n | smallest n admissible for every larger n |
| --- | --- | --- | --- | --- | --- |
| `I1a` | none; every positive integer in [1, ceiling] was tested | 4096 | **413** | 413 | 426 |
| `I1b` | none; every positive integer in [1, ceiling] was tested | 4096 | **413** | 413 | 426 |
| `I2` | none; every positive integer in [1, ceiling] was tested | 4096 | **214** | 214 | 219 |
| `I3` | none; every positive integer in [1, ceiling] was tested | 4096 | **413** | 413 | 426 |
| `I4` | none; every positive integer in [1, ceiling] was tested | 4096 | **448** | 448 | 460 |

The registered sizes are confirmed to be the smallest unrestricted positive integers meeting the per-cell target. The retired multiple-of-32 restriction plays no part in this search and none of the three sizes is a multiple of 32. The final column records the non-monotonicity reported as finding `S3MR3-007`.

### 7.4 Gate-bearing cell census and the error-budget ladder

| quantity | exact rational | scope |
| --- | --- | --- |
| `m_max` | 43 | maximum gate-bearing cells over the **selectable** profiles only |
| per-stage profile false-negative budget | `19/400` | one profile, one stage |
| per-cell false-negative budget | `19/17200` | per atomic evaluation cell |
| per-cell power target | `17181/17200` | per atomic evaluation cell |
| profile stage power floor | `381/400` | union-bound lower bound under arbitrary dependence |
| panel false-qualification bound | `1/200` | fixed denominator 3 times the per-component level `1/600` |
| study end-to-end power floor | `9/10` | development selection plus one-shot confirmation |

No independence is used in any binding bound. Independence products may appear only as explicitly labelled sensitivity analysis with no authority.

### 7.5 Selection map and state machine

- The selection map is total and deterministic over its 16 registered branches, and the independently reconstructed map disagrees with the registered map on no branch.
- The selectable denominator is `3` in every branch, including every branch in which `S3`'s activation condition is false.
- `S3` is selected in no branch outside its registered single-token applicability condition.
- The state machine has 10 states, 6 of them terminal, and eleven transitions. Every event carries exactly one next state and every terminal state is reachable.
- An `I0` failure, error or ambiguity maps only to `STOP_INSTRUMENT_DEFECT`, whose registered claim states that nothing was measured about any interface.
- `I0` fixtures: 232 clusters, 232 cluster-derived base items, 464 cluster rendered rows, 38 non-cluster rows, 502 rows in total.
- `STOP_AWAITING_AUTHORITY` is registered as a legal stop state in the gate truth table but is absent from the state machine, which is finding `S3MR3-006`.

### 7.6 Operation projection, derived from primitive counts

| work stream | rendered rows | sequence-level evaluations | generation calls | generated tokens |
| --- | --- | --- | --- | --- |
| `deterministic_I0_fixtures` | 502 | 0 | 0 | 0 |
| `target_role_development` | 33543 | 33543 | 0 | 0 |
| `positive_reference_external_P3Q` | `null` | `null` | `null` | `null` |
| `RP_I4_under_candidate_profiles` | 3584 | 3584 | 0 | 0 |
| `selected_profile_one_shot_confirmation` | 27856 | 27856 | 0 | 0 |
| `S4_diagnostic_generation` | 26,064 | 417024 | 26064 | 417024 |

`S4` prefill evaluations: **26064**; incremental decode evaluations upper bound: **390960**. A sequence-level evaluation is never equated with a runtime batched forward call, which remains `null` because batch packing is a future execution property. No grand total is published, because the `P3-Q` stream is `null` and not zero.

## 8. Historical-review harness erratum

The repaired draft-v0.3 historical-regression harness was audited independently; a passing harness was not treated as self-validating.

| property | value |
| --- | --- |
| anchors mutable historical inputs to | `2b36f5321d830ea6f70fff2b7bbca3cb93394046` |
| collected node identifiers before / after | 35 / 35 |
| node-identifier set unchanged | true |
| assertions weakened | false |
| skips or xfails added | 0 / 0 |
| exceptions swallowed | false |
| expected scientific values changed | false |
| input-coverage assertion present | true |
| snapshot isolation asserted | true |
| immutable v0.3 recalculation identities unchanged | true |
| amends any v0.3 finding or disposition | false |

**Non-vacuity probes**, all run in clean CPU-only Azure Container Registry tasks bound to an exact commit:

| probe | expected | observed | bound run |
| --- | --- | --- | --- |
| pristine reviewed snapshot of the draft-v0.3 historical inputs | pass | **pass** | `ca5k` |
| substitution of the live draft-v0.4 protocol into the snapshot | fail | **fail** | `ca5k` |
| perturbation of the committed historical recalculation table | fail | **fail** | `ca5k` |

`AR-0246` retains the pre-erratum harness identity `3e8b50610fc052123c9196a584364a4a10575ac8b7ea33c58a31a369d24f9c60` and `AR-0269` records the corrected current identity `a1676d31ed32225c8e8a3dba40b4ee6f01d5d3490619eeb35d385efb4ea48c61`. The harness was unchanged across the published base and both draft-v0.4 commits preceding the erratum and changed only in the erratum commit, so there is no unregistered intermediate state and the two rows do not contradict each other.

## 9. Cross-artifact consistency

| id | status | candidate |
| --- | --- | --- |
| `CI-01` | **CONFIRMED_MAJOR** | Whether J_joint_correct is described identically as a level and never as a presentation effect in every active claim field across the JSON, the Markdown, the schema, the packet and the routing documents. |
| `CI-02` | **NOT_CONFIRMED** | Whether the descriptive b, c and d lattice quantities have any reachable decision path into eligibility, selection, confirmation, ranking or rescue. |
| `CI-03` | **NOT_CONFIRMED** | Whether p_joint and the correctness-state discordance d are anywhere treated as independent parameters or as a product of marginals. |
| `CI-04` | **NOT_CONFIRMED** | Whether every gate-bearing cell has a complete registered generator distribution with exact weights summing to one and a with-replacement draw of the full tuple per draw ordinal. |
| `CI-05` | **NOT_CONFIRMED** | Whether any cell draws a template once and generates a batch beneath it, which would introduce template-level clustering incompatible with iid Bernoulli. |
| `CI-06` | **CONFIRMED_MAJOR** | Whether the deterministic rendering surface needed to instantiate the registered generator is registered anywhere. |
| `CI-07` | **NOT_CONFIRMED** | Whether the generator-local external-validity ceiling is stated explicitly wherever a pass claim is made. |
| `CI-08` | **NOT_CONFIRMED** | Whether per-cell power is ever labelled family, profile, selection, confirmation or end-to-end power, and whether the arbitrary-dependence proof is stated wherever a joint bound is published. |
| `CI-09` | **CONFIRMED_BLOCKING** | Whether the K6 contrast applicability recorded for the option-less profiles is consistent with what those profiles render. |
| `CI-10` | **CONFIRMED_MAJOR** | Whether the confirmation applicability recorded in the derived statistics table agrees with the amended protocol and its schema. |
| `CI-11` | **NOT_CONFIRMED** | Whether S4's diagnostic-only authority, its composite causal ambiguity and its exclusion from every success union are stated consistently. |
| `CI-12` | **CONFIRMED_MINOR** | Whether the gate applicability of I4 to S4 is recorded consistently in every artifact that states it. |
| `CI-13` | **CONFIRMED_MINOR** | Whether the registered stop-state set is the same in the state machine and in the gate truth table. |
| `CI-14` | **NOT_CONFIRMED** | Whether every operation quantity is derived from primitive counts and whether any null stream is treated as zero or folded into a grand total. |
| `CI-15` | **CONFIRMED_MAJOR** | Whether the ten inherited repair claims are matched by the artifacts they name as their locations. |
| `CI-16` | **NOT_CONFIRMED** | Whether the historical-harness erratum left the collected node-ID set, the expected scientific values and the immutable v0.3 recalculation identities unchanged. |
| `CI-17` | **NOT_CONFIRMED** | Whether AR-0246 and AR-0269 record two contradictory claims about the current harness blob. |
| `CI-18` | **CONFIRMED_MAJOR** | Whether the withdrawn sample sizes appear in any active field despite the protocol asserting they do not. |
| `CI-19` | **NOT_CONFIRMED** | Whether the evidence ledger, the operation counters and the authority flags record any operation, result or evidence row for this design. |
| `CI-20` | **CONFIRMED_MINOR** | Whether the active round references in the protocol name the correct review round. |

## 10. The two verdicts

### `METHOD_INTERNAL_VALIDITY_VERDICT`

**Verdict: `ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR`.**

The statistical machinery is sound and was independently reproduced without a single numeric disagreement across seventy exact-binomial fields, sixteen cell-census fields, eleven power-architecture fields and fifteen operation-projection fields. The exact binomial model, the intersection-union logic, the fixed-denominator union correction, the arbitrary-dependence type-II ladder, the total deterministic state machine, the selection map, the confirmation lifecycle and the operation ontology are all valid as registered, and every joint bound was verified to hold under arbitrary dependence with no independence assumption anywhere. Internal validity nonetheless falls short of adequate for one reason that is not statistical: a gate-bearing atomic cell is registered as applicable to two selectable profiles for which its transformation has no referent, so that cell can be passed without testing the construct the floor was derived for. Once that applicability is corrected and the deterministic rendering surface is registered, the internal validity of the design is adequate.

### `STUDY3_PURPOSE_AND_CONSTRUCT_RELEVANCE_VERDICT`

**Verdict: `ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR`.**

This verdict was reached separately and is not inferred from internal validity. The narrowed J_joint_correct estimand does serve Study 3's purpose. Study 3 exists because two predecessors died on the instrument, and the decision it must inform is whether an interface reliably registers competence that is present. That is a level question, not a contrast question, so narrowing to a level is the right move rather than a retreat; and because p_joint + d <= 1, a passing joint-correctness gate bounds correctness-state discordance from above without claiming to estimate it. Excluding generation from the selectable set is likewise the direct implementation of the Study 1 lesson and does not leave a purpose-critical gap, since S4 is retained as a costed diagnostic with an explicit causal-ambiguity ceiling. Construct relevance nevertheless falls short of adequate for the preferred profile specifically: S2 and S3 have only two registered I3 cells each, one of which is a self-comparison under the registered rendering definition, so the joint-correctness evidence supporting the profile the design most wants to select is half of what the claim ceiling states. That is a bounded repair, not a redefinition of what Study 3 measures.

The second verdict was reached separately and is not inferred from the first. Statistical validity without construct relevance would not have been acceptance, and the design is not accepted merely because its wording was narrowed.

## 11. Operator decisions

| item | status |
| --- | --- |
| `OD2` | `UNRESOLVED_BLOCKING_OPERATOR_DECISION` |
| `UR-22` | `UNRESOLVED_BLOCKING_OPERATOR_DECISION` |
| `OD8-residual` | `UNRESOLVED_NON_BLOCKING_OPERATOR_DECISION` |

`OD2` remains a blocking operator decision. This review assessed whether its boundary and the generic `P3-Q`/`I4` method are sufficiently specified and concluded that they are; it selected, preferred, pinned, ranked, revision-resolved, downloaded, tokenized, loaded, ran, prequalified and substituted no checkpoint. Methods blockers are kept strictly separate from `OD2`: the disposition of this review is driven by `S3MR3-001` and `S3MR3-010`, neither of which depends on `OD2`, and `OD2` remaining open would not by itself have prevented acceptance.

## 12. Disposition and the round limit

**Disposition: `STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED`.**

One BLOCKING and three MAJOR methods defects remain, so acceptance as specified is unavailable. The blocking defect S3MR3-001 and the major defect S3MR3-010 cannot be repaired by a bounded conformance edit, because closing them necessarily changes registered applicability, the gate-bearing atomic cell set of two of the three selectable profiles, the generator specification and the per-profile claim ceiling; section 8 excludes exactly those from an accepted-with-conformance disposition. No rejection-driving defect is fundamental: every required repair is a localized design choice that leaves the estimand, the interface panel, the task strata, the difficulty, the model roles and the feasibility strategy intact, and none of them requires first learning whether any cell approaches the registered success floor. The correct disposition is therefore a bounded amendment.

Acceptance as specified is unavailable because a blocking and three major methods defects remain. Acceptance with required conformance changes is unavailable because closing `S3MR3-001` and `S3MR3-010` necessarily alters registered applicability, the atomic cell set of two selectable profiles, the generator specification and the per-profile claim ceiling, all of which section 8 excludes from a conformance disposition. A fundamental rejection is not earned: the narrowed estimand does serve the purpose Study 3 exists for, the generation exclusion is correct rather than a gap, the generator-local ceiling is adequate for the registered next decision, and no repair requires a wholesale redesign of the estimand, the interface panel, the tasks, the difficulty, the model roles or the feasibility strategy. Each required repair is a localized design choice.

**Legal successor action: `OPERATOR_BOUNDED_AMENDMENT_ROUND_FOR_DRAFT_V0_5`, followed by a further independent methods review. No freeze.**

## 13. Claim ceiling and boundary restatement

Study 3 remains an unfrozen design. Nothing in this review is a scientific result. No interface profile and no positive reference is selected. No bank, seed, model operation, gate result, confirmation access or evidence row exists, and every empirical and model operation counter is exactly zero. The strongest claim any future pass could support is cell-wise joint robust correctness on the registered synthetic generator distributions for the named tasks, checkpoint roles and registered presentation pairs. The original research question remains unanswered, and this review creates no freeze, execution, amendment or pilot authority.

| flag | value |
| --- | --- |
| `bank_authorized` | `false` |
| `confirmation_access_authorized` | `false` |
| `execution_authorized` | `false` |
| `frozen` | `false` |
| `model_operations_authorized` | `false` |
| `positive_reference_selected` | `false` |
| `seed_authorized` | `false` |
| `winner_selected` | `false` |

| counter | value |
| --- | --- |
| `ablation_operations` | `0` |
| `activation_extractions` | `0` |
| `bank_accesses` | `0` |
| `bank_rows_generated` | `0` |
| `confirmation_split_accesses` | `0` |
| `decision_bearing_local_statistical_runs` | `0` |
| `decode_steps` | `0` |
| `evidence_rows_created` | `0` |
| `forward_passes` | `0` |
| `generations` | `0` |
| `gpu_jobs` | `0` |
| `interfaces_selected` | `0` |
| `lens_operations` | `0` |
| `local_pytest_runs` | `0` |
| `model_downloads` | `0` |
| `model_weight_loads` | `0` |
| `patching_operations` | `0` |
| `phase_1_0d_operations` | `0` |
| `positive_references_selected` | `0` |
| `probe_operations` | `0` |
| `provider_calls` | `0` |
| `revision_resolutions` | `0` |
| `rq2_s4_operations` | `0` |
| `seeds_drawn` | `0` |
| `sequence_scorings` | `0` |
| `study1_files_modified` | `0` |
| `study2_files_modified` | `0` |
| `tokenizer_constructions` | `0` |

- Study 1 remains closed at `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`.
- Study 2 remains closed at `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`.
- Study 3 remains unfrozen.
- No interface profile and no positive reference is selected.
- No bank, seed, model operation, gate result, confirmation access or evidence row exists.
- The original research question remains unanswered.
- No freeze, execution, amendment or pilot authority was created by this review.
