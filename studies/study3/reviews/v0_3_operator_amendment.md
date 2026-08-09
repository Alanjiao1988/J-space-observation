# Study 3 draft-v0.3 operator amendment record

**State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_3_COMPLETE_AWAITING_SECOND_INDEPENDENT_METHODS_REVIEW`

**Document class:** operator amendment record. This is the drafting party's response to
the independent methods review of draft-v0.2. It is **not** a review, it is **not** an
adjudication, and it does **not** declare the amended protocol correct.

## What this record responds to

| Field | Value |
| --- | --- |
| Review | `studies/study3/reviews/v0_2_independent_methods_review.md` |
| Review JSON | `studies/study3/reviews/v0_2_independent_methods_review.json` |
| Review receipt | `studies/study3/methods_review_receipt_v0_2.json` |
| Reviewed commit (draft-v0.2 design bytes) | `8a2c4a0b2a73c5d802988333f11ea6c22828f6f5` |
| Review-output commit | `e4bcda3a487ea9c9a085e3943103a07501014431` |
| Disposition returned | `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` |
| Findings | 6 BLOCKING + 11 MAJOR + 3 MINOR = 20 |
| Unresolved items | 22 |

## The self-approval prohibition

This record is written by the drafting party. It does not adjudicate its own repairs. Every repair below is recorded as PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW, which asserts that a repair was made and published, not that the repaired protocol is correct. The drafting party of draft-v0.2 found its own design defensible and an independent reviewer then rejected it with six blocking findings; that outcome is the reason this record may not adjudicate itself.

| Marker | Value |
| --- | --- |
| The amendment declares the protocol correct | `false` |
| Adjudication belongs to | the second independent methods reviewer |

Two dispositions are used in this record and only two:

| Disposition | Meaning |
| --- | --- |
| `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` | A repair was made and published. Whether the repair is adequate is for the second independent methods reviewer to determine. |
| `UNRESOLVED_BLOCKING_OPERATOR_DECISION` | The item depends on operator decision OD2, which is not resolved in this round. The item is **not** relabelled resolved. |

## Closure matrix - all 20 findings

Every finding `S3MR-001` through `S3MR-020` appears exactly once below, with a real
disposition.

| Finding | Severity | Title | Disposition |
| --- | --- | --- | --- |
| `S3MR-001` | BLOCKING | The I3 primary estimand is not identifiable from the published counterbalancing construction | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-002` | BLOCKING | The I3 primary indicator has two mutually exclusive definitions across the authoritative JSON, the companion Markdown and the review packet | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-003` | BLOCKING | The Family B per-profile alpha is stated but implemented nowhere; the committed component rules deliver three times the stated study alpha | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-004` | BLOCKING | The authoritative JSON asserts a conservativeness property that the same draft's own disclosure contradicts | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-005` | BLOCKING | The four-value discordance grid is a sensitivity check, and maximising over the feasible null boundary finds an undisclosed exceedance at a planned configuration | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-006` | BLOCKING | The I3 primary floor is left in two mutually exclusive versions, and the higher one is unreachable at every admissible sample size reviewed | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-007` | MAJOR | The packet's I3 primary table presents two different nulls under one stated hypothesis with no null column | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-008` | MAJOR | I1a and I1b are underpowered at every proposed sample size against the draft's own lowest declared alternative | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-009` | MAJOR | The committed verification of the paired method is circular and the committed design test entrenches the insufficient grid | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-010` | MAJOR | The K5 stratum retains draft-v0.1 generating-process text that the same file elsewhere forbids | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-011` | MAJOR | The K6 stratum retains draft-v0.1 generating-process text that contradicts the resolved answer-cue decision | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-012` | MAJOR | The S3 projected operation accounting contradicts itself by a factor of four | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-013` | MAJOR | The projection is not decomposed into the work streams a feasibility review requires and its role multiplier is not reconcilable | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-014` | MAJOR | The sample-size symbol n changes unit between artifacts and no artifact declares its unit | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-015` | MAJOR | The I3 rejection region is degenerate at one proposed configuration | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-016` | MAJOR | S3's membership in the Family B multiplicity denominator is contingent on a post-data fact | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-017` | MAJOR | The confirmation gate I5 and the development profile-selection rule have no statistical specification anywhere | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-018` | MINOR | Checkpoint role records carry gate labels that predate the I1a/I1b split | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-019` | MINOR | The Clopper-Pearson bounds and the label-uniformity bands use a two-sided tail convention under a one-sided field name | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `S3MR-020` | MINOR | The positive-reference dossier attributes its own obligation to the wrong prior defect | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |

### S3MR-001 - BLOCKING

**The I3 primary estimand is not identifiable from the published counterbalancing construction**

- **Reviewer required change:** Publish an explicit variants-per-base-item factor for every interface profile and reconcile the construction algorithm with the cluster rule, or restate I3 on a unit the published construction actually produces.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** I3 is restated on a unit the construction actually produces. The independent unit is the base-item contrast cluster, which holds exactly two variants: one baseline presentation and one registered content-equivalent transformed presentation of the same base item. The cross-product reading is deleted; there is no 32 x 3 factorial and no undefined variants-per-base-item factor, because the variants-per-cluster factor is fixed at 2 for every profile and every contrast cell.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (i3_contrast_registry, atomic_evaluation_cells.i3_sampling_unit)`
  - `studies/study3/protocol/interface_calibration_protocol_draft.md`
  - `studies/study3/analysis/design_statistics.py`
- **Verification:** tests/test_study3_design.py asserts the unit is base_item_contrast_cluster, that variants_per_cluster == 2 everywhere, and that rendered rows equal clusters x 2 in every I3 component.

### S3MR-002 - BLOCKING

**The I3 primary indicator has two mutually exclusive definitions across the authoritative JSON, the companion Markdown and the review packet**

- **Reviewer required change:** Publish two indicators - invariance of the chosen content and correctness under every variant - and their explicit conjunction, then reconcile all three artifacts to the published definition and recompute every I3 threshold under it.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** Three indicators are published with disjoint definitions and one of them is named the gate: J_inv (both variants valid and byte-identical after the registered content mapping), J_cor (both variants scored correct against the unique registered ground truth), and J_both = J_inv AND J_cor, which is the primary gate indicator. A stable but wrong answer scores 0 and a stable invalid or unparseable output scores 0. The estimand is the same in the JSON, the Markdown and the v0.3 packet.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (proposed_statistics.i3_indicators)`
  - `studies/study3/protocol/interface_calibration_protocol_draft.md`
  - `studies/study3/analysis/independent_methods_review_packet_v0_3.md`
  - `studies/study3/analysis/design_statistics.py`
- **Verification:** An eight-case indicator truth table is derived by the committed script and asserted by tests/test_study3_design.py, including the stable-wrong and stable-invalid cases.

### S3MR-003 - BLOCKING

**The Family B per-profile alpha is stated but implemented nowhere; the committed component rules deliver three times the stated study alpha**

- **Reviewer required change:** Either implement the per-profile alpha in every component rule and republish every affected threshold, power figure and sample size, or withdraw the 0.001666666667 claim and state the study-level guarantee that alpha 0.005 components actually deliver.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** The exact rational is now the policy and the decimal is a rendering of it. The study-level development screening level is 1/200; the per-profile development component level is 1/600 = (1/200) / 3; the confirmation component level is 1/200. Every component rule in the committed derivation uses the exact rational level it advertises, and the identity per_profile_alpha x 3 == study_alpha is asserted in exact rational arithmetic inside the derivation script rather than narrated.
- **Where:**
  - `studies/study3/analysis/design_statistics.py`
  - `studies/study3/analysis/design_statistics_tables.json`
  - `studies/study3/protocol/interface_calibration_protocol_draft.json`
- **Verification:** The derivation script raises if the rational identity fails; tests/test_study3_design.py re-checks it independently with fractions.Fraction.

### S3MR-004 - BLOCKING

**The authoritative JSON asserts a conservativeness property that the same draft's own disclosure contradicts**

- **Reviewer required change:** Withdraw the conservativeness assertion, restate the decision rule as asymptotic with an empirically maximised realised level, and record the maximised level rather than a grid maximum.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** The conservativeness assertion is WITHDRAWN, not repaired and not re-scoped. The paired aggregate-equivalence procedure is retired from every decision role, so no claim about its size is made anywhere in the active protocol. The reviewer's exceedance finding stands unchallenged and is preserved as immutable historical evidence.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (retired_procedures.tango_paired_equivalence)`
  - `studies/study3/protocol/interface_calibration_protocol_draft.md`
  - `studies/study3/references/methods_sources.md`
- **Verification:** tests/test_study3_design.py asserts that no gate, eligibility, selection or confirmation path references the retired procedure and that the withdrawal record is present.

### S3MR-005 - BLOCKING

**The four-value discordance grid is a sensitivity check, and maximising over the feasible null boundary finds an undisclosed exceedance at a planned configuration**

- **Reviewer required change:** Replace the grid with a justified nuisance maximisation over the feasible null boundary, a critical value calibrated over the full registered domain, or a conservative-by-construction exact procedure such as the unconditional exact approach of Hsueh, Liu and Chen (2001); register the optimisation domain, tolerance, bracketing rule, convergence-failure behaviour and an independent validation.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** The four-value discordance grid is REMOVED and the procedure it supported is retired from every decision role. No nuisance maximisation is substituted, because no paired aggregate-equivalence decision remains to calibrate. What survives is a purely descriptive paired 2x2 summary with no null, no alpha, no p-value, no critical value, no equivalence margin, no pass or fail, no rescue path and no ranking weight.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (retired_procedures)`
  - `studies/study3/analysis/design_statistics.py`
- **Verification:** The committed script no longer emits any paired critical value or equivalence margin; tests/test_study3_design.py asserts the descriptive summary carries none of the decision fields.

### S3MR-006 - BLOCKING

**The I3 primary floor is left in two mutually exclusive versions, and the higher one is unreachable at every admissible sample size reviewed**

- **Reviewer required change:** Register one I3 primary floor and one substantively justified alternative, and demonstrate that the pair is separable at an admissible n at the implemented alpha; if it is not, revise the scientific claim rather than the alternative.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** Exactly one I3 floor is active: p0 = 0.90 (exact rational 9/10) against p1 = 0.97 (97/100) at power >= 0.90 with n = 256 base-item contrast clusters per contrast cell. p0 = 0.95 is deleted from every active protocol, table and packet field and is permitted only in clearly labelled historical narrative describing what draft-v0.2 did.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (proposed_statistics.i3_floor)`
  - `studies/study3/analysis/design_statistics_tables.json`
  - `studies/study3/analysis/independent_methods_review_packet_v0_3.md`
- **Verification:** tests/test_study3_design.py asserts active_floor_count == 1, asserts the achieved power at the registered configuration exceeds the target, and asserts that no active numeric field carries 0.95.

### S3MR-007 - MAJOR

**The packet's I3 primary table presents two different nulls under one stated hypothesis with no null column**

- **Reviewer required change:** Add an explicit null column, or split the table, and state the registered floor once.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** Every threshold table in the v0.3 packet, the protocol Markdown and the committed tables artifact carries an explicit null column naming p0, and there is only one registered I3 floor to name. No table mixes two nulls under one stated hypothesis.
- **Where:**
  - `studies/study3/analysis/independent_methods_review_packet_v0_3.md`
  - `studies/study3/analysis/design_statistics_tables.json`
  - `studies/study3/protocol/interface_calibration_protocol_draft.md`
- **Verification:** tests/test_study3_design.py asserts every emitted binomial row carries a null_hypothesis field and that the set of distinct I3 nulls has size 1.

### S3MR-008 - MAJOR

**I1a and I1b are underpowered at every proposed sample size against the draft's own lowest declared alternative**

- **Reviewer required change:** Raise n to the smallest admissible size meeting the reviewed target at the implemented alpha, or lower the target power explicitly and justify it; do not move p1.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** n = 192 is withdrawn from every active field. I1a and I1b are sized at n = 256 base items per atomic cell, which attains exact power 0.953040775 against p1 = 0.97 at the implemented development component level 1/600, above the 0.90 target. p1 was not moved and the target power was not lowered.
- **Where:**
  - `studies/study3/analysis/design_statistics.py`
  - `studies/study3/analysis/design_statistics_tables.json`
  - `studies/study3/protocol/interface_calibration_protocol_draft.json`
- **Verification:** The derivation script raises if any active component fails to meet the target power; tests/test_study3_design.py holds the reviewer-returned targets as an independent expectation.

### S3MR-009 - MAJOR

**The committed verification of the paired method is circular and the committed design test entrenches the insufficient grid**

- **Reviewer required change:** Replace the recorded-rows assertion with a maximisation over the registered nuisance domain, and replace the fixed-grid coverage test with a test of the registered maximisation contract. This change belongs to the amendment round, not to this review.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** The circular verification is deleted with the procedure it verified. design_statistics.py no longer contains verify_paired_method and no longer asserts a bound over rows it recorded itself. The fixed four-value grid test is removed from tests/test_study3_design.py and replaced by an independent expectation of the exact-binomial rules plus a verification of the pairwise construction (complete-block balance, bijective option and label mappings, disjoint base-item identities, no random draw).
- **Where:**
  - `studies/study3/analysis/design_statistics.py`
  - `tests/test_study3_design.py`
- **Verification:** tests/test_study3_design.py contains an AST test asserting that the derived pass counts and tails appear nowhere in the script as literals, so the script cannot pass by transcription.

### S3MR-010 - MAJOR

**The K5 stratum retains draft-v0.1 generating-process text that the same file elsewhere forbids**

- **Reviewer required change:** Rewrite task_strata[5].data_generating_process to the orthogonal construction actually adopted.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** task_strata K5 data_generating_process is rewritten to the seven one-factor pairwise contrasts actually adopted: K5-P1/P2/P3 (content position offsets +1, +2, +3 mod 4), K5-S1/S2/S3 (correct displayed-symbol index offsets +1, +2, +3 mod 4) and K5-A1 (label alphabet replacement between two alphabets that are disjoint from each other and from the answer domain). The four-cyclic-permutation text and the 1/2/3/4 label-set replacement are gone; digits are forbidden as labels.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (task_strata, counterbalancing_design, i3_contrast_registry)`
- **Verification:** tests/test_study3_design.py asserts the K5 contrast set is exactly the seven registered IDs, that no alphabet intersects the answer domain, and that the forbidden v0.1 text does not reappear.

### S3MR-011 - MAJOR

**The K6 stratum retains draft-v0.1 generating-process text that contradicts the resolved answer-cue decision**

- **Reviewer required change:** Rewrite task_strata[6].data_generating_process to state that only the separator and the instruction sentence vary.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** task_strata K6 data_generating_process is rewritten to say that only the separator and the instruction sentence vary and that the answer cue is held byte-identical. K6 is registered as two disjoint pairwise contrast cells drawn from the three renderings: K6-SEP (R-base versus R-sep) and K6-INSTR (R-base versus R-instr). A three-way comparison is prohibited.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (task_strata, counterbalancing_design.k6_contrasts)`
- **Verification:** tests/test_study3_design.py asserts exactly two K6 cells, two variants each, byte-identical answer cue, and disjoint base-item identities across cells.

### S3MR-012 - MAJOR

**The S3 projected operation accounting contradicts itself by a factor of four**

- **Reviewer required change:** Decide whether S3 scores one sequence or four per item, correct the projection, and republish the totals.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** Under the registered single-token answer domain S3 adds exactly 0 additional forward passes and exactly 0 additional sequence-scoring rows beyond S2, because the length-normalised sequence score of a one-token candidate is a monotone function of that token's log-probability under the same prefix, so S3's ranking is analytically identical to S2's and is computed from the same distribution. The 9728 figure is withdrawn.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (operation_boundaries.projected_future_operations)`
  - `studies/study3/analysis/design_statistics.py`
- **Verification:** The derivation script raises if S3's incremental forward passes or incremental sequence-scoring rows are anything other than zero.

### S3MR-013 - MAJOR

**The projection is not decomposed into the work streams a feasibility review requires and its role multiplier is not reconcilable**

- **Reviewer required change:** Republish the projection decomposed by work stream, with base items, derived variants and scored rows separated, and with the role multiplier stated per gate.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** The projection is decomposed into six named work streams, each reporting its own units: deterministic_I0_fixtures, target_role_development, positive_reference_external_P3Q, RP_I4_under_candidate_profiles, selected_profile_one_shot_confirmation and S4_diagnostic_generation. Base items, contrast clusters, rendered rows, scored rows, forward passes and generated tokens are separate columns. A single undifferentiated total is prohibited, and the role multiplier is stated per gate rather than as one global factor.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json`
  - `studies/study3/analysis/design_statistics_tables.json`
  - `studies/study3/analysis/independent_methods_review_packet_v0_3.md`
- **Verification:** tests/test_study3_design.py asserts all six streams are present, that no_single_undifferentiated_total is true, and that generations are reported separately from forward passes.

### S3MR-014 - MAJOR

**The sample-size symbol n changes unit between artifacts and no artifact declares its unit**

- **Reviewer required change:** Declare the unit of every sample-size symbol at the point of definition and hold it constant across all artifacts.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** A unit registry is published with four distinct units - base_item, base_item_contrast_cluster, rendered_row and scored_row - and every symbol n carries its unit at its definition and in every table in every artifact. Rendered rows and scored rows are never called n. One n is never reused across base items, contrast clusters, rendered rows and scored rows.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (unit_registry)`
  - `studies/study3/protocol/interface_calibration_protocol_draft.md`
  - `studies/study3/analysis/design_statistics_tables.json`
  - `studies/study3/analysis/independent_methods_review_packet_v0_3.md`
- **Verification:** tests/test_study3_design.py asserts every gate record and every emitted binomial row carries a non-empty unit_of_n and that the unit strings partition by gate as registered.

### S3MR-015 - MAJOR

**The I3 rejection region is degenerate at one proposed configuration**

- **Reviewer required change:** Exclude degenerate rejection regions explicitly, or raise n so that the rejection count is strictly below n at the registered floor and alpha.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** No active rejection region may have a required pass count equal to n. The prohibition is enforced by a raise inside the derivation script rather than asserted in prose, and the configuration that produced the degenerate region (n = 128 at p0 = 0.95) is removed from the active design along with p0 = 0.95 itself.
- **Where:**
  - `studies/study3/analysis/design_statistics.py`
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (proposed_statistics.i3_floor.no_degenerate_rejection_region)`
- **Verification:** tests/test_study3_design.py asserts pass_count < n for every emitted development and confirmation component.

### S3MR-016 - MAJOR

**S3's membership in the Family B multiplicity denominator is contingent on a post-data fact**

- **Reviewer required change:** Register S3's contribution to the Family B denominator before any data, and state it as a fixed number rather than as a condition.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** The selectable-profile denominator is FIXED at K = 3 before any data exists and never shrinks, under every outcome, including the outcome in which S3's multi-token activation condition is not met and S3 is skipped. It is registered as a number, not as a condition. A sixteen-row pre-registered development selection map enumerates every combination and carries the denominator 3 in every row.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (development_selection_and_confirmation_plan.stage_2_selection)`
  - `studies/study3/analysis/design_statistics_tables.json`
- **Verification:** tests/test_study3_design.py asserts the denominator is the integer 3 in every row of the selection map and that no row reduces it.

### S3MR-017 - MAJOR

**The confirmation gate I5 and the development profile-selection rule have no statistical specification anywhere**

- **Reviewer required change:** Publish the full I5 specification - null, alternative, n, alpha, rejection rule and multiplicity treatment - and the development selection rule including tie-breaking, both fixed before any data; state the development and confirmation error roles separately rather than applying one alpha statement to both.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** I5 is fully specified: covered constructs I0, I1a, I1b, I2, I3_J_both and I4; component-level exact rational 1/200; per-component nulls, alternatives, sample sizes with units and rejection counts derived by the committed script; intersection-union conjunction across components; no across-profile correction because exactly one profile is selected on development before confirmation is entered; one-shot; reselection and re-tuning prohibited. The development selection rule is published as an executable sixteen-row map with a fixed admissibility order and a deterministic tie-break, fixed before any data. Development and confirmation error roles are stated separately.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (gate_hierarchy I5, development_selection_and_confirmation_plan)`
  - `studies/study3/analysis/design_statistics.py`
  - `studies/study3/analysis/independent_methods_review_packet_v0_3.md`
- **Verification:** tests/test_study3_design.py asserts I5 carries a component for every covered construct with a derived pass count, and that the selection map is total over its enumerated inputs.

### S3MR-018 - MINOR

**Checkpoint role records carry gate labels that predate the I1a/I1b split**

- **Reviewer required change:** Update every role record to the post-split gate names and state applicability per profile.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** Every checkpoint-role record is updated to the post-split gate names. RC is recorded against Gates I1a and I1b, and every role record states applicability per profile. No record names a gate called I1.
- **Where:**
  - `studies/study3/protocol/interface_calibration_protocol_draft.json (checkpoint_roles)`
  - `studies/study3/protocol/interface_calibration_protocol_draft.md`
- **Verification:** tests/test_study3_design.py asserts no checkpoint-role record contains the token 'Gate I1' followed by a non-alphanumeric character.

### S3MR-019 - MINOR

**The Clopper-Pearson bounds and the label-uniformity bands use a two-sided tail convention under a one-sided field name**

- **Reviewer required change:** Rename the field and state the tail convention explicitly at the point of tabulation.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** Every interval and band now names the mass it actually consumes. The reported Clopper-Pearson quantity is a LOWER bound consuming HALF of a two-sided simultaneous mass, and the label-uniformity bands are stated as two-sided masses across the band. The field named simultaneous_alpha is renamed to two_sided_simultaneous_mass and the consumed tail is tabulated beside it.
- **Where:**
  - `studies/study3/analysis/design_statistics.py`
  - `studies/study3/analysis/design_statistics_tables.json`
  - `studies/study3/protocol/interface_calibration_protocol_draft.md`
- **Verification:** tests/test_study3_design.py asserts the emitted rows carry both two_sided_simultaneous_mass and lower_tail_mass_consumed_by_this_bound and that the latter is exactly half the former.

### S3MR-020 - MINOR

**The positive-reference dossier attributes its own obligation to the wrong prior defect**

- **Reviewer required change:** Correct both references to D-04.
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Repair:** Both back-references in the positive-reference dossier are corrected from D-07 to D-04. D-07 is the parser-v2 gate decision; D-04 is the decision that records the positive-reference circularity and the chance-level floor issue. The dossier also states explicitly that no candidate is selected.
- **Where:**
  - `studies/study3/references/positive_reference_dossier.md`
- **Verification:** tests/test_study3_design.py asserts the dossier contains no D-07 reference in the positive-reference obligation context and that it declares UNSELECTED.

## Unresolved-item dispositions - all 22 items

Every item `UR-01` through `UR-22` appears exactly once below, with a real
disposition.

| Item | Reviewer state | Subject | Findings | Disposition |
| --- | --- | --- | --- | --- |
| `UR-01` | `UNRESOLVED_BLOCKING` | I3 primary estimand identifiability | `S3MR-001` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-02` | `UNRESOLVED_BLOCKING` | I3 primary indicator semantics across JSON, Markdown and packet | `S3MR-002` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-03` | `UNRESOLVED_BLOCKING` | Family B per-profile alpha not implemented | `S3MR-003` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-04` | `UNRESOLVED_BLOCKING` | false conservativeness assertion in the authoritative JSON | `S3MR-004` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-05` | `UNRESOLVED_BLOCKING` | paired size control over the feasible nuisance domain | `S3MR-005` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-06` | `UNRESOLVED_BLOCKING` | I3 primary floor 0.90 versus 0.95 and its feasibility | `S3MR-006` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-07` | `UNRESOLVED_REQUIRED_CHANGE` | I5 confirmation specification | `S3MR-017` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-08` | `UNRESOLVED_REQUIRED_CHANGE` | development profile-selection rule | `S3MR-017` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-09` | `UNRESOLVED_REQUIRED_CHANGE` | Family B denominator membership of S3 | `S3MR-016` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-10` | `UNRESOLVED_REQUIRED_CHANGE` | unit of every sample-size symbol | `S3MR-014` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-11` | `UNRESOLVED_REQUIRED_CHANGE` | I1a and I1b power shortfall | `S3MR-008` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-12` | `UNRESOLVED_REQUIRED_CHANGE` | circular committed verification and the entrenched four-value grid test | `S3MR-009` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-13` | `UNRESOLVED_REQUIRED_CHANGE` | K5 and K6 stale generating-process text | `S3MR-010`, `S3MR-011` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-14` | `UNRESOLVED_REQUIRED_CHANGE` | S3 projection self-contradiction and the undecomposed projection | `S3MR-012`, `S3MR-013` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-15` | `UNRESOLVED_REQUIRED_CHANGE` | I4 multiplicity across operation families and depths | `S3MR-017` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-16` | `UNRESOLVED_REQUIRED_CHANGE` | residual pooling paths across label alphabets and position-symbol cells | _none_ | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-17` | `UNRESOLVED_REQUIRED_CHANGE` | degenerate I3 rejection region at n 128, p0 0.95 | `S3MR-015` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-18` | `UNRESOLVED_REQUIRED_CHANGE` | paired margin practical-irrelevance justification | `S3MR-005` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-19` | `UNRESOLVED_MINOR` | Clopper-Pearson and uniformity tail-convention naming | `S3MR-019` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-20` | `UNRESOLVED_MINOR` | positive-reference dossier D-07 versus D-04 attribution | `S3MR-020` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-21` | `UNRESOLVED_MINOR` | stale Gate I1 labels in checkpoint role records | `S3MR-018` | `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` |
| `UR-22` | `UNRESOLVED_REQUIRED_CHANGE` | external-qualification-interface requirement for the positive reference | _none_ | `UNRESOLVED_BLOCKING_OPERATOR_DECISION` |

### UR-01 - I3 primary estimand identifiability

- **Reviewer state:** `UNRESOLVED_BLOCKING`
- **Reviewer said resolution requires:** publishing a variants-per-base-item factor per profile and reconciling the construction algorithm with the cluster rule, or restating I3 on a unit the construction produces
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** I3 is restated on the base-item contrast cluster, a unit the published construction produces, with exactly two variants per cluster. See S3MR-001.

### UR-02 - I3 primary indicator semantics across JSON, Markdown and packet

- **Reviewer state:** `UNRESOLVED_BLOCKING`
- **Reviewer said resolution requires:** publishing J_inv, J_cor and their conjunction, and reconciling all three artifacts
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** Three indicators are published with a single named gate indicator, J_both, and all artifacts are reconciled to it. See S3MR-002.

### UR-03 - Family B per-profile alpha not implemented

- **Reviewer state:** `UNRESOLVED_BLOCKING`
- **Reviewer said resolution requires:** recomputing every component rule at 0.001666666667 and republishing every affected threshold, power and sample size, or withdrawing the claim
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** The per-profile development component level 1/600 is implemented in every component rule as an exact rational. See S3MR-003.

### UR-04 - false conservativeness assertion in the authoritative JSON

- **Reviewer state:** `UNRESOLVED_BLOCKING`
- **Reviewer said resolution requires:** withdrawing the assertion and recording the maximised realised level
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** The conservativeness assertion is withdrawn and the procedure is retired from every decision role. See S3MR-004.

### UR-05 - paired size control over the feasible nuisance domain

- **Reviewer state:** `UNRESOLVED_BLOCKING`
- **Reviewer said resolution requires:** adopting one of the four admissible remedies and registering the optimisation contract
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** The paired procedure is retired rather than recalibrated, so no size-control claim over the nuisance domain is made. The second reviewer is asked explicitly to adjudicate whether retirement fully removes the defect. See S3MR-005.

### UR-06 - I3 primary floor 0.90 versus 0.95 and its feasibility

- **Reviewer state:** `UNRESOLVED_BLOCKING`
- **Reviewer said resolution requires:** registering one floor and demonstrating separability at an admissible n, or revising the claim
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** One floor is registered: p0 = 0.90 against p1 = 0.97 at n = 256 contrast clusters per cell, separable at the implemented level with exact power 0.953040775. See S3MR-006.

### UR-07 - I5 confirmation specification

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** publishing null, alternative, n, alpha, rejection rule and multiplicity treatment
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** I5 is fully specified with per-component nulls, sizes, units, levels and rejection counts. See S3MR-017.

### UR-08 - development profile-selection rule

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** publishing the selection map including tie-breaking and the no-profile-passes branch, fixed before any data
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** The development selection rule is published as an executable sixteen-row pre-registered map with a fixed order and deterministic tie-break. See S3MR-017.

### UR-09 - Family B denominator membership of S3

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** fixing the denominator as a number before any data
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** The Family B denominator is fixed at 3 before data and never shrinks. See S3MR-016.

### UR-10 - unit of every sample-size symbol

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** declaring the unit at every point of definition, which is itself blocked until UR-01 fixes the atomic cell
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** A unit registry is published and every n carries its unit at definition and in every table. See S3MR-014.

### UR-11 - I1a and I1b power shortfall

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** raising n to 256 at the corrected alpha, or explicitly lowering and justifying the target power
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** n = 256 base items per atomic cell attains 0.953040775 power at the implemented level; n = 192 is withdrawn and p1 was not moved. See S3MR-008.

### UR-12 - circular committed verification and the entrenched four-value grid test

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** replacing the recorded-rows assertion and the fixed-grid coverage test in the amendment round; RECORDED here, not repaired, because tests/test_study3_design.py is part of the review object
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** The circular verification and the fixed-grid coverage test are both deleted with the procedure they supported, and replaced by an independent expectation plus an anti-transcription AST test. See S3MR-009.

### UR-13 - K5 and K6 stale generating-process text

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** rewriting both data_generating_process fields to the resolved constructions
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** Both K5 and K6 data_generating_process fields are rewritten to the constructions actually adopted. See S3MR-010 and S3MR-011.

### UR-14 - S3 projection self-contradiction and the undecomposed projection

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** deciding one or four S3 scorings per item and republishing the projection decomposed by work stream
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** S3's incremental cost is fixed at zero in the current domain and the projection is decomposed into six work streams with per-stream units. See S3MR-012 and S3MR-013.

### UR-15 - I4 multiplicity across operation families and depths

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** publishing either a per-family-per-depth level or a registered pooled evaluation
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** I4 is evaluated per operation family and per depth as separate atomic cells with pooling prohibited, and the components form an intersection-union conjunction within the profile at the registered component level, so no further within-profile correction is applied. See S3MR-017.

### UR-16 - residual pooling paths across label alphabets and position-symbol cells

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** naming both paths in the pooling prohibitions
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** The pooling prohibition is extended explicitly to pooling across label alphabets, across position and symbol contrast cells, across the three I3 indicators and across splits. Label-set replacement is itself a registered manipulation (K5-A1), so averaging over the alphabet would average over the manipulation.

### UR-17 - degenerate I3 rejection region at n 128, p0 0.95

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** excluding degenerate regions explicitly or raising n
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** No active rejection region may have a pass count equal to n; the prohibition is enforced by a raise in the derivation script and the degenerate configuration is removed from the active design. See S3MR-015.

### UR-18 - paired margin practical-irrelevance justification

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** stating the largest presentation effect considered practically irrelevant, before any data
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** No equivalence margin survives, because the paired aggregate-equivalence decision is retired; there is therefore no margin to justify as practically irrelevant. See S3MR-005.

### UR-19 - Clopper-Pearson and uniformity tail-convention naming

- **Reviewer state:** `UNRESOLVED_MINOR`
- **Reviewer said resolution requires:** renaming the field and stating the convention; no number changes
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** Both the Clopper-Pearson bounds and the uniformity bands now name the tail convention at the point of tabulation. See S3MR-019.

### UR-20 - positive-reference dossier D-07 versus D-04 attribution

- **Reviewer state:** `UNRESOLVED_MINOR`
- **Reviewer said resolution requires:** correcting both references to D-04
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** Both dossier back-references are corrected to D-04. See S3MR-020.

### UR-21 - stale Gate I1 labels in checkpoint role records

- **Reviewer state:** `UNRESOLVED_MINOR`
- **Reviewer said resolution requires:** updating every role record to the post-split names with per-profile applicability
- **Disposition:** `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`
- **Note:** Every checkpoint-role record uses the post-split gate names with per-profile applicability. See S3MR-018.

### UR-22 - external-qualification-interface requirement for the positive reference

- **Reviewer state:** `UNRESOLVED_REQUIRED_CHANGE`
- **Reviewer said resolution requires:** requiring the qualification interface to be external to the candidate panel, not merely the bank to be isolated
- **Disposition:** `UNRESOLVED_BLOCKING_OPERATOR_DECISION`
- **Note:** The external canonical qualification interface for the positive reference cannot be registered without deciding which checkpoint the positive reference is, and that decision is OD2. OD2 is not resolved in draft-v0.3 and no candidate is selected, preferred, pinned, revision-resolved, downloaded, tokenized, loaded or prequalified. The requirement itself is restated in the protocol - the reference must be prequalified through a separate canonical interface that is not S1, S2, S3 or S4, on items disjoint from those used for I4 - but the interface cannot be registered in this round. This item is NOT relabelled resolved.

## Operator decisions in this round

| Decision | Status | Blocking | Note |
| --- | --- | --- | --- |
| `OD2` | `unresolved` | `true` | No positive reference is selected. Every unresolved item that depends on OD2 remains UNRESOLVED_BLOCKING_OPERATOR_DECISION and is not relabelled resolved. |
| `OD5` | `resolved_subject_to_independent_review` | `false` | Exact-binomial primary design; study-level development screening level 1/200; per-profile development component level 1/600; intersection-union within profile; fixed selectable-profile denominator 3. |
| `OD6` | `resolved_subject_to_independent_review` | `false` | One I3 floor: p0 = 0.90, p1 = 0.97, power >= 0.90, n = 256 base-item contrast clusters per applicable contrast cell. p0 = 0.95 deleted from every active field. |

`OD2` remains unresolved and blocking. No checkpoint has been selected, preferred,
pinned, revision-resolved, downloaded, tokenized, loaded or prequalified in this
round, and `UR-22` is recorded as `UNRESOLVED_BLOCKING_OPERATOR_DECISION` rather than resolved.

## Questions put to the second independent methods reviewer

1. Does retiring the paired aggregate-equivalence procedure from every decision role fully remove the size-control defect recorded in S3MR-004 and S3MR-005, or does a residual decision path remain anywhere in the amended protocol?
2. Is the base-item contrast cluster with exactly two variants an identifiable unit for the I3 estimand under every registered contrast cell, and does the J_both conjunction estimate what the protocol says it estimates?
3. Is the intersection-union treatment within a profile, combined with a fixed denominator of 3 across profiles and a one-shot confirmation at 1/200 on a physically disjoint split, an adequate multiplicity architecture for the claim the protocol permits?
4. Does the six-stream operation projection make the feasibility question answerable, and is the zero-incremental-cost argument for S3 under a single-token answer domain correct as stated?
5. Are any of the twenty repairs above cosmetic relabelling rather than substantive design change?

## Immutable objects this amendment did not edit

- `studies/study3/reviews/v0_2_independent_methods_review.md`
- `studies/study3/reviews/v0_2_independent_methods_review.json`
- `studies/study3/reviews/v0_2_independent_methods_review.schema.json`
- `studies/study3/methods_review_receipt_v0_2.json`
- `studies/study3/analysis/independent_methods_recalculation.py`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`
- `studies/study3/prompts/study3_v0_2_independent_methods_review_authority.md`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/design_receipt_v0_2.json`
- `studies/study3/reviews/v0_1_operator_review.md`
- `studies/study3/design_receipt.json`

The reviewer's independent recalculation is preserved as immutable historical
evidence. It was not re-run, not re-derived, not edited and not superseded.

## Operation counters

| Counter | Value |
| --- | --- |
| `ablation_operations` | `0` |
| `activation_extractions` | `0` |
| `bank_rows_generated` | `0` |
| `confirmation_split_accesses` | `0` |
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

**All counters zero:** `true`

## Authority flags

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

## Next legal action

second bounded independent methods review of the amended statistical, contrast, selection and confirmation packet at studies/study3/analysis/independent_methods_review_packet_v0_3.md

Nothing in this record freezes the design, authorizes execution, authorizes bank
construction, authorizes a seed draw, authorizes any model operation, selects an
interface, selects a positive reference or authorizes access to the confirmation
split.
