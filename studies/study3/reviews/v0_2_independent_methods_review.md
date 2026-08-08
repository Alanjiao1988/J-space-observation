# Study 3 draft-v0.2 - independent methods review

This document is the human-readable half of an independent methods review of the Study 3 interface calibration protocol, draft v0.2. It is rendered from `studies/study3/reviews/v0_2_independent_methods_review.json` so that the two cannot drift, and `tests/test_study3_methods_review.py` asserts the parity. The reviewer did not write the design under review, did not repair it, and did not adopt any operator decision.

## Disposition

**`STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`**

Documentation state: `STUDY3_DRAFT_V0_2_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`

Three independent rejection triggers are met. (1) The I3 primary estimand is not identifiable from the published counterbalancing construction, so the indicator that carries the study's central invariance claim cannot be computed from the design as written. (2) Valid type-I error control cannot be specified from the committed artifacts: the Family B per-profile level is stated but not implemented anywhere, the paired secondary procedure's size is not controlled over its own feasible null boundary, and the I3 primary floor is left in two mutually exclusive versions of which one is unreachable at every admissible sample size reviewed. (3) Repairing (1) would require inventing design structure that does not exist in the draft - a variants-per-base-item factor for the label-bearing profile, a redefined atomic cell, a redefined unit for n, and a re-derived projection - which the ACCEPTED_WITH_REQUIRED_CHANGES disposition explicitly forbids. The reviewer can supply candidate values for several missing parameters and has done so, but the authority forbids treating that ability as grounds for acceptance.

The permitted dispositions for this round were `STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED`, `STUDY3_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CHANGES` and `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`. Exactly one is returned, and it was earned by the review rather than prescribed by the authority that commissioned it.

### Triggering conditions

- The I3 primary estimand is not identifiable from the published counterbalancing construction: the indicator quantifies over the applicable transformed variants of a base item while counterbalancing_design.construction_algorithm.steps[4] assigns exactly one (position, symbol) pair per base item, and no variants-per-base-item field exists in any Study 3 artifact.
- The I3 primary indicator carries two mutually exclusive definitions across the authoritative JSON, the companion Markdown and the review packet, and the two disagree on whether a stable but wrong answer passes.
- Valid type-I error control cannot be specified from the committed artifacts: the Family B per-profile level 0.001666666667 is stated but implemented by no committed component rule, every one of which is computed at 0.005, so the delivered union bound is 0.015.
- The paired secondary procedure's size is not controlled over its own feasible null boundary: maximising over the full domain finds an undisclosed exceedance of 0.025073 at n 384 and margin 0.10, at a discordance of 0.4782 that lies far outside the registered four-value grid, at a configuration the design proposes to use and reports as compliant.
- The authoritative JSON records under gate_hierarchy I3.secondary_criterion.verified_before_use that exact enumeration shows the realised type-I error does not exceed the nominal one-sided level, which the same draft's own disclosure of 0.025501 contradicts.
- The I3 primary floor is left in two mutually exclusive versions, 0.90 and 0.95, and at 0.95 against the draft's own lowest declared alternative 0.97 no admissible n up to 768 attains the declared target power.

### Why not accepted as specified

The committed specification does not suffice on its own terms. Six blocking findings remain unresolved, an authoritative verification field asserts the opposite of the draft's own disclosure, and twenty-two items remain in an unresolved state. The operator authority is explicit that a design with unresolved parameter values may not be accepted as specified merely because the reviewer can imagine or supply values that would work. This review does supply such values - sample sizes, rejection counts, exact powers, calibrated critical values and a decomposed projection - and that ability is precisely what the authority forbids treating as grounds for acceptance. An unresolved checklist item is never acceptance.

### Why not accepted with required changes

Acceptance with required changes presupposes that the changes can be expressed against the design as written. They cannot here. Repairing the I3 primary estimand requires publishing a variants-per-base-item factor that exists nowhere, which in turn redefines the atomic evaluation cell, redefines the unit of n, invalidates every I3 threshold, and forces the whole projection to be re-derived. That is inventing design structure rather than amending it, and it alters the core of the design. The same is true of the Family B level: implementing it changes every committed threshold, power figure and sample size in the packet. A change set of that reach is an amendment round, not a required-changes annotation.

## What was reviewed

Reviewed commit `8a2c4a0b2a73c5d802988333f11ea6c22828f6f5`, tree `7e9077a32903adfdaa3bede95beba8752fcb5133`. The review object is unmodified by this round: yes.

| Path | Bytes | sha256 | Role |
| --- | ---: | --- | --- |
| `studies/study3/protocol/interface_calibration_protocol_draft.json` | 129382 | `4648e0386457f17b4d013ebe44b5f47d6ccd9c77bf87d6014eb1cd1e7b8344e8` | authoritative review object |
| `studies/study3/protocol/interface_calibration_protocol_draft.md` | 59684 | `deb9238d565feea3a748e20313be8d45f8384f3bc50bb89c77caf13b23a37e5c` | companion narrative |
| `studies/study3/protocol/interface_calibration_protocol.schema.json` | 33167 | `ff60f1f2f3a8a09797c3dcfe7bb2ee6314aaece152f8cd8069fcd870865a1785` | protocol schema |
| `studies/study3/analysis/independent_methods_review_packet.md` | 28113 | `d438b5c4b0008d6afc63cf77cb5ed0858ef958fe8f18acbf97f50c32f698c5e3` | review packet and 22-item checklist |
| `studies/study3/analysis/design_statistics.py` | 28026 | `462a86d62e4c53d12a23c5615de2423da1ea9c49b40819bcb26f25f5e9149f94` | drafting implementation; never imported by this review |
| `studies/study3/analysis/design_statistics_tables.json` | 26713 | `48524f066b3f96cdb96b60008318294e2ee883a407ed12e1d8b7a3d0fc60b85f` | drafting derivation tables; compared only after independent values existed |
| `studies/study3/references/methods_sources.md` | 18534 | `0bb1962326c4d65e9fe077eefb7b960ee1b9ac0eb4661893e59c6aa0a64ad4af` | methods sources ledger |
| `studies/study3/references/positive_reference_dossier.md` | 9923 | `bdde6514d7431e24f6b3ad4df5e510357850c4fb9289a8b11ad62e0bea35ef39` | positive-reference dossier |
| `studies/study3/reviews/v0_1_operator_review.md` | 15303 | `24e659d41588fe2b6239b7340a67516d13faf352147096313c04ef357cca8b54` | prior operator review |
| `studies/study3/design_receipt_v0_2.json` | 14403 | `d7ac6aee782be8a9c9ef88bec1c2e05785e5b25d010e84665019a9ef12969b63` | drafting design receipt |
| `studies/study3/analysis/study2_to_study3_design_traceability.md` | 14548 | `dda6be22936c1db8c1b4da2f14e877c095a00d8d83526ae29a96f3e69d2a85ac` | traceability note |
| `tests/test_study3_design.py` | 33894 | `98bb923d0c835e1a816d3805930bc6319db07905d13276fb99a2f2d7c7369ebf` | committed design test; recorded, not modified |

Every hash above was computed from the committed Git blob, not from working-tree bytes. `tests/test_study3_design.py` appears in this table because it is part of the review object: finding S3MR-009 records a defect in it, and the committed guard asserts the file still carries that defect rather than having been quietly repaired by its reviewer.

## Independence procedure

The reviewer wrote the reviewed design: no.

The independent implementation is `studies/study3/analysis/independent_methods_recalculation.py` and its output is `studies/study3/analysis/independent_methods_recalculation_tables.json`. It does not import the drafting implementation (yes), does not exec or dynamically load it (yes), and does not copy functions from it (yes).

Enforcement: The independent module parses its own source with ast at import time and raises if any Import, ImportFrom, __import__, importlib, exec, eval, compile, runpy, or open() reference resolves to design_statistics. The committed test re-runs the same assertion from a separate process and additionally scans the committed source bytes.

Execution venue: All calculation and test evidence was produced by CPU-only Azure Container Registry tasks against a clean exact-commit clone. Nothing in this review was calculated on the operator workstation.

**Formulas were re-derived from these primary sources.**

- Tango, T. (1998). Equivalence test and confidence interval for the difference in proportions for the paired-sample design. Statistics in Medicine 17(8):891-908. PMID 9595618. Verified via NCBI esummary.
- Hsueh, H.-M., Liu, J.-P., Chen, J. J. (2001). Unconditional exact tests for equivalence or noninferiority for paired binary endpoints. Biometrics 57(2):478-483. PMID 11414572. Verified via NCBI esummary.
- Berger, R. L., Hsu, J. C. (1996). Bioequivalence trials, intersection-union tests and equivalence confidence sets. Statistical Science 11(4):283-319. DOI 10.1214/ss/1032280304. Verified via Crossref.
- Clopper, C. J., Pearson, E. S. (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. Biometrika 26(4):404-413.
- The committed Study 3 protocol JSON definitions of the gates, strata, profiles, roles, and splits.

**Structural differences from the drafting implementation.**

- The drafting script is organised as gate-shaped table builders; the independent module is organised as four statistical families (binomial tail family, interval family, paired score family, multiplicity family) with family-level validators.
- All internal function names differ: the independent module uses upper_tail_mass, tail_threshold_count, exact_detection_probability, cp_lower_limit_by_inversion, tango_constrained_nuisance, tango_score_value, paired_joint_lattice_mass, boundary_size_supremum and golden_section_maximise.
- Binomial tails are accumulated by exact integer-ratio recursion on Fraction-free floating multipliers with an ascending-order summation, not by a library survival function.
- Clopper-Pearson limits are obtained by monotone bisection on the exact binomial tail rather than by a beta quantile call, and are then cross-checked against the beta identity.
- The paired null law is enumerated on the full (n12, n21) lattice with a windowed mass filter and an exhaustive cross-check, rather than over a fixed truncated range.

**Agreement is not validation.** Every closed-form check above is independent of the drafting implementation. Agreement with design_statistics_tables.json was examined only after the independent values existed, and is reported as a comparison, never as evidence of correctness.

**Independent closed-form and published-example checks, by statistical family.** Each was run before any comparison with the drafting numbers.

- *binomial tail family*
  - all-successes tail equals p^n exactly: max absolute deviation 0.0
  - at-least-one-success tail equals 1-(1-p)^n exactly: max absolute deviation 0.0
  - tail symmetry at p = 1/2 about n/2: max absolute deviation exactly 0
  - regularised incomplete beta identity for the binomial tail: max absolute deviation 3.34e-14
- *enumeration family*
  - windowed lattice enumeration versus exhaustive enumeration of the paired null law: max absolute deviation 0.0
  - total lattice mass equals one: max absolute deviation 8.37e-14
- *interval family*
  - Clopper-Pearson lower limit recovers the defining tail equation under inversion: max absolute deviation 2.46e-16
  - monotonicity of the lower limit in the observed count at fixed n: max violation 0.0
- *paired score family*
  - at margin zero the Tango constrained-score statistic reduces algebraically to the McNemar score statistic: max absolute deviation 0.0
  - the constrained nuisance root satisfies the published quadratic to 6.01e-17 and the score equation to 1.53e-14
  - standard-normal quantiles used for the critical value reproduce their defining tail to 6.66e-16
  - 2778 interior roots, 122 boundary roots, 0 infeasible roots over the reviewed configuration set

## The 22 registered checklist questions

Answered in the order the review packet registers them. Every item has a verdict and a substantive answer; an unanswered item would be a defect in this review, not a neutral omission.

### 1. Are the atomic evaluation cells defined finely enough that no gate can be passed by averaging over a heterogeneous mixture?

**Verdict: NO.**

Not as published. Two separate problems. First, the cell factorisation in atomic_evaluation_cells lists operation family, depth, rendering, label set, label position, role, profile and split, and its cluster_rule presupposes that a base item generates a cluster of applicable variants; but counterbalancing_design.construction_algorithm.steps[4] assigns exactly one (position, symbol) pair to each base item by the deterministic rule (p, s) = (k mod 4, (k div 4) mod 4). A base item therefore appears in exactly one label-position cell, so the cluster the rule averages over does not exist as constructed. Second, the label alphabet and the K6 rendering are cell coordinates for I1a, I1b and I2 but are the very factors the I3 indicator quantifies over, so I3 necessarily averages across cells that the other gates hold fixed. Whether that is a heterogeneous mixture cannot be decided from the draft because the number of applicable variants per base item is never stated.

Findings: `S3MR-001`, `S3MR-014`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: counterbalancing_design.construction_algorithm.steps[4]`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: atomic_evaluation_cells.cluster_rule`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: atomic_evaluation_cells.cell_factors`

### 2. Are the six pooling prohibitions sufficient, and is any additional pooling route still open?

**Verdict: NO.**

The six prohibitions are individually correct and each closes a real route, but at least two rescue paths remain open. Route one: because the number of applicable variants per base item differs by profile - 96 derived variants for the label-bearing S1 and S4 against 3 for the content-only S2 and S3 - an all-variants indicator is a materially different functional across profiles, yet nothing forbids reporting the resulting proportions in a common I3 denominator or comparing them as if they estimated the same quantity. Route two: S3 carries the status conditionally_selectable and its registered activation condition is not met, so the Family B denominator can be reduced from three to two after outcomes are seen. A prohibition on post-hoc reduction of the multiplicity denominator exists for not_applicable cells but not for profile selectability. Both are recorded as required changes rather than repaired here.

Findings: `S3MR-001`, `S3MR-016`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: pooling_prohibitions`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: interface_profiles[S3].selectability`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: projected_cells_and_operations.variants_per_base_item_by_profile`

### 3. Is the not-applicable third value handled correctly everywhere, in particular never counted as a pass and never counted as a zero effect?

**Verdict: QUALIFIED.**

The explicit rules are correct. not_applicable is barred from becoming a pass, from becoming a zero effect, from entering a denominator, and from reducing a multiplicity denominator after data are observed. The gap is elsewhere. Family A is an intersection over every retained component, and I1b is not applicable to the content-only profiles S2 and S3 because they display no label alphabet. The draft never states the applicable component set per profile, so the conjunction over components is undefined for S2 and S3 and can be read as vacuously satisfied for the missing component. That is a not_applicable silently behaving as a pass at the family level rather than at the cell level. The required change is to publish the applicable component set for each profile explicitly and to state that the conjunction ranges over that set only.

Findings: `S3MR-014`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: scoring_model.not_applicable_rules`
- `studies/study3/analysis/independent_methods_review_packet.md :: section 4 profile table, S2 and S3 rows omit I1b`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: proposed_statistics.hypothesis_families.family_A_within_profile`

### 4. Is the intersection-union treatment of Family A correct, and is the claim that it needs no multiplicity correction accepted?

**Verdict: QUALIFIED.**

The argument is accepted as an argument and rejected as implemented. Independently re-derived from Berger and Hsu (1996): if each component test has level alpha_j and the family null is the union of the component nulls, then the intersection-union test that rejects only when every component rejects has size bounded by max_j alpha_j, with no correction needed. That is exactly the draft's claim and the reviewer confirms it. What the draft then does with it is not accepted. The bound is max over the component levels actually implemented, and every committed component table is computed at alpha 0.005, so Family A delivers 0.005 within a profile and cannot deliver the 0.001666666667 the draft attributes to it. The correct statement is that Family A needs no correction for the number of components, not that it needs no correction at all.

Findings: `S3MR-003`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: proposed_statistics.hypothesis_families.family_A_within_profile.per_component_alpha`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: multiplicity_decision.family_A_within_profile`

### 5. Is Bonferroni division by the selectable-surface count the right treatment of Family B, or should a different allocation be used?

**Verdict: NO.**

Division by the selectable-surface count is a defensible allocation, and the reviewer does not require a different one. It is nevertheless not the right treatment as written, because it is not implemented. The JSON states per_profile_alpha 0.001666666667 with correction Bonferroni over 3 selectable profiles against study_alpha 0.005, but every retained component rule in design_statistics_tables.json and every threshold in packet section 2 is computed at alpha 0.005. The union bound delivered by the committed component rules is therefore 3 x 0.005 = 0.015, three times the stated study alpha. Independently recomputing the affected rejection counts at 0.001666666667 changes them: I1a and I1b at n 192 move from 184 to 185, I2 at n 192 moves from 115 to 117, and I4 at n 192 moves from 168 to 170. A stated per-profile level that no committed rule achieves is not a multiplicity treatment. Either implement it and republish every affected threshold and sample size, or withdraw it and state the guarantee the committed rules actually deliver.

Findings: `S3MR-003`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: proposed_statistics.hypothesis_families.family_B_across_profiles.per_profile_alpha`
- `studies/study3/analysis/design_statistics_tables.json :: every retained component table alpha field`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: multiplicity_decision.family_B_across_profiles.rejection_counts_at_each_level`

### 6. Is the exclusion of the never-selectable profile from the multiplicity count correct?

**Verdict: QUALIFIED.**

Correct for S4 and unresolved for S3. Excluding S4 is right: it carries the registered status never_selectable, it is barred from every success union, and it can therefore contribute no selection event to inflate the family-wise error rate while still receiving diagnostic scoring with zero selection authority. That is exactly the correct asymmetry and the reviewer accepts it. S3 is a different matter. It carries conditionally_selectable, its registered activation condition is not met, and the draft records that on a single-token answer domain its argmax is identical to S2's. Its membership in the denominator of three is therefore contingent on a fact that will be known only after the development split is scored, which is precisely the after-outcomes choice the draft elsewhere forbids. The rule may be conservative - keeping the denominator at three regardless - but it must be fixed before any data.

Findings: `S3MR-016`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: interface_profiles[S4].selectability = never_selectable`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: interface_profiles[S3].selectability = conditionally_selectable`

### 7. Is the per-base-item consistency indicator the right primary I3 estimand?

**Verdict: NO.**

It is the right kind of estimand and it is not identifiable from the design as published. A per-base-item indicator is the correct choice in principle because it makes the base item the independent unit and refuses to let a marginal proportion hide item-level instability. But the indicator quantifies over every applicable transformed variant of a base item, and the published construction assigns exactly one (position, symbol) pair per base item. No field named variants_per_base_item, or any synonym, exists anywhere in the protocol JSON, the companion Markdown, the schema, or the packet. The set the indicator ranges over is therefore undefined for the label-bearing profile, and the derived quantity cannot be computed from the design as written. This is the single most consequential defect in the draft and it is the primary reason for a rejecting disposition. Additionally the draft overloads one indicator with two distinct scientific questions - invariance of the chosen content and correctness under every variant - which must be split into two indicators and their explicit conjunction.

Findings: `S3MR-001`, `S3MR-002`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: gate_hierarchy I3.primary_indicator`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: counterbalancing_design.construction_algorithm.steps[4]`
- `grep of all Study 3 protocol artifacts for variants_per_base_item and synonyms: zero matches`

### 8. Is the demotion of aggregate paired equivalence to a secondary criterion acceptable, given the power finding in section 5.3?

**Verdict: QUALIFIED.**

The demotion is accepted and it does not cure the defect. Demoting the aggregate paired contrast is right on the merits: a marginal difference of correctness proportions between a transformed and a base condition can be arbitrarily small while every individual base item flips its answer, so the aggregate contrast cannot carry a per-item invariance claim and should not have gate authority. What is not accepted is the treatment of the demoted criterion. It is still asserted in the JSON to have been verified before use, it is still reported with rejection counts and realised levels, and a secondary inferential criterion whose size is not controlled is still an uncontrolled inferential statement. Demotion changes how much weight a defective procedure carries; it does not make the procedure correct.

Findings: `S3MR-004`, `S3MR-005`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: gate_hierarchy I3.secondary_criterion.verified_before_use`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: paired_equivalence.size_over_feasible_null_boundary`

### 9. Is the named paired method acceptable, and is the three-way verification in section 6.3 sufficient evidence that it is implemented correctly?

**Verdict: QUALIFIED.**

The method is acceptable and the verification is not sufficient. Tango's (1998) constrained-score procedure is correctly named and correctly transcribed: re-deriving the constrained maximum-likelihood nuisance root from the published quadratic 2 n q^2 - [(n12 + n21) - d0 (2n - n12 + n21)] q - n21 d0 (1 - d0) = 0 and taking the larger root reproduces the draft's rejection region, and the independent enumeration reproduces the draft's realised levels to nine decimal places, including the disclosed 0.025501. The verification is nevertheless circular in two ways. First, the three ways are three evaluations of the same formula, so they establish transcription fidelity and nothing about size. Second, design_statistics.py::verify_paired_method raises only if the three recorded rows exceed the nominal level, and tests/test_study3_design.py::test_paired_method_was_verified_before_use asserts the bound over those same three rows, while test_paired_sensitivity_covers_the_required_discordance_rates enforces the four-value grid as adequate. A test that checks the rows the script chose to record cannot detect a supremum outside them, and the reviewer has demonstrated that such a supremum exists. Per the operator authority this is recorded, not repaired.

Findings: `S3MR-005`, `S3MR-009`.

Evidence:

- `studies/study3/analysis/design_statistics.py :: verify_paired_method, lines 313-362, check at line 348`
- `tests/test_study3_design.py :: test_paired_method_was_verified_before_use, lines 741-749`
- `tests/test_study3_design.py :: test_paired_sensitivity_covers_the_required_discordance_rates, lines 772-777`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: paired_equivalence.rejection_rule`

### 10. Is the exact type-I behaviour at the null boundary acceptable, including the single disclosed configuration whose realised level is 0.025501 against a nominal 0.025?

**Verdict: NO.**

No, and the disclosed configuration is not the worst one. The independent enumeration reproduces the drafting number: at n 192 and margin 0.10 the realised one-sided level is 0.025501092 against a nominal 0.025, so the drafting enumeration is arithmetically correct. The defect is in the claim made about it, and in the search that produced it. Maximising the exact level over the full feasible null-boundary nuisance domain rather than over four hand-chosen discordance values finds a second exceedance the draft never reports: at n 384 and margin 0.10 the supremum is 0.025073 attained at discordance 0.4782, whereas the drafting grid rows at that configuration are 0.017524, 0.024284 and 0.024727 with the 0.05 row infeasible, so the grid maximum 0.024727 looks compliant. A configuration the design plans to use is therefore reported as compliant while its true size exceeds the nominal level. An exceedance of roughly 2 percent of alpha is small in magnitude but it is not the point; the point is that the search was not capable of finding it, so the absence of further exceedances is not evidence.

Findings: `S3MR-004`, `S3MR-005`.

Evidence:

- `studies/study3/analysis/independent_methods_recalculation_tables.json :: paired_equivalence.size_over_feasible_null_boundary`
- `studies/study3/analysis/design_statistics_tables.json :: paired sensitivity rows`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: gate_hierarchy I3.secondary_criterion.verified_before_use[2]`

### 11. Is it clear and acceptable that exact here describes the enumeration and not a conservative-by-construction test?

**Verdict: NO.**

It is not clear, and where it is stated it is stated wrongly. The methods sources ledger and the packet do distinguish the two senses in prose. But the authoritative JSON, at gate_hierarchy I3.secondary_criterion.verified_before_use, records that exact enumeration of the paired method shows the realised type-I error does not exceed its nominal one-sided level - a conservativeness claim - in the same draft whose packet discloses 0.025501 against 0.025. Enumerating the null distribution exactly makes the reported number accurate; it does not make an asymptotic score rule conservative, and the reviewer's own maximisation confirms it is not. The word exact must be confined to the enumeration and the decision rule must be described as asymptotic with an empirically maximised realised level, or the rule must be replaced by a conservative-by-construction procedure.

Findings: `S3MR-004`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: gate_hierarchy I3.secondary_criterion.verified_before_use[2]`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: paired_equivalence.rejection_rule.exactness_scope`

### 12. Is the proposed I4 competence floor of 0.80 defensible before any model has been observed?

**Verdict: YES.**

Yes, as a floor, and it is defensible precisely because it is not a chance level. On a four-option stratum the chance rate is 0.25 and on the primitive stratum the draft restates the floor as 0.50; a null at either would let a barely-above-chance reader qualify as a competent positive reference, which was the draft-v0.1 defect. A floor of 0.80 asserts that a checkpoint already independently qualified on the K4 construct should recover the answer through a working interface on at least four items in five, which is a substantive and pre-registerable competence statement that does not depend on any observation. The reviewer accepts 0.80 and requires that it be paired with a predeclared alternative; the draft's own lowest declared alternative 0.90 is retained unchanged so that the resulting sample-size verdict cannot be attributed to the reviewer moving the alternative. Two conditions attach: passing must not be read as sufficient for the capability claim (see item 13 and finding S3MR-006 context), and the alpha at which the floor is tested must be the corrected Family B level rather than 0.005.

Findings: `S3MR-003`.

Evidence:

- `studies/study3/analysis/independent_methods_review_packet.md :: section 2, I4 null p <= 0.8`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: reviewed_parameter_recommendations, gate I4_competence_floor`

### 13. Is the rejection of the draft-v0.1 chance-level I4 null accepted?

**Verdict: YES.**

Accepted without qualification. A chance-level null tests whether the positive reference is doing anything at all, not whether it is competent, so rejecting it establishes only that the checkpoint is above random. Since the entire purpose of the positive reference is to distinguish an interface that cannot be read from a checkpoint that cannot do the task, a chance-level null makes the control uninformative in exactly the case it exists to adjudicate. The draft-v0.1 formulation is correctly rejected. The reviewer records one consequence the draft does not draw: rejecting a floor at 0.80 is necessary but not sufficient for the claim that the reference is capable on the registered K4 construct, because a one-sided binomial rejection bounds the probability only from below and says nothing about the operation families and depths on which the failures fell. Sufficiency requires the separate external P3-Q qualification, which must not share a bank, an observation, or a candidate-panel outcome with I4.

Findings: `S3MR-020`.

Evidence:

- `studies/study3/reviews/v0_1_operator_review.md :: defect D-04`
- `studies/study3/analysis/independent_methods_review_packet.md :: section 2, chance-level null rejected`
- `studies/study3/references/positive_reference_dossier.md`

### 14. Is the I1a/I1b power shortfall at p = 0.97 acceptable, or must n increase?

**Verdict: NO.**

Not acceptable; n must increase. The draft's own table records meets_target_power_0_90_at_lowest_alternative false at both n 128 and n 192, and the disclosed power 0.87425 at n 192, p1 0.97 and alpha 0.005 is reproduced independently. Running a gate at 0.874 power against the design's own lowest alternative of interest means roughly one interface in eight that truly meets the standard is discarded, and because Family A is a conjunction that shortfall compounds across components. Searching the full admissible grid rather than the four sizes the draft examined, the smallest admissible n reaching 0.90 power is 224 at alpha 0.005 and 256 at the corrected Family B alpha 0.001666666667, where the exact power is 0.953040775 with a rejection count of 244 out of 256. Discreteness was accounted for: exact-binomial power is not monotone in n across a rejection-count change, so the recalculation additionally records the smallest admissible n that holds the target thereafter rather than only the first n that touches it.

Findings: `S3MR-008`.

Evidence:

- `studies/study3/analysis/design_statistics_tables.json :: meets_target_power_0_90_at_lowest_alternative`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: smallest_admissible_n_reaching_target_power`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: reviewed_parameter_recommendations`

### 15. Are the proposed sample sizes adequate for every gate, including the confirmation split?

**Verdict: NO.**

No. Four distinct inadequacies. First, I1a and I1b are underpowered at every proposed size, as item 14 sets out. Second, I3 primary is unresolved between two floors and, at the higher one, unreachable: at p0 0.95 with p1 0.97 and the corrected alpha there is no admissible n up to 768 reaching 0.90 power, because the alternative sits only two points above the floor. Third, the I3 rejection region is degenerate at n 128 with p0 0.95 and alpha 0.005, where the acceptance count is 128 and every single base item must be correct - a rule with no tolerance for a single scoring artefact. Fourth, the confirmation split has no proposed sample size at all: packet section 2 states no I5 hypothesis, no n, no alpha and no rejection rule, and the profile table merely lists I5 among the gates each profile must clear. A sample size cannot be adequate when it does not exist.

Findings: `S3MR-006`, `S3MR-008`, `S3MR-015`, `S3MR-017`.

Evidence:

- `studies/study3/analysis/independent_methods_recalculation_tables.json :: reviewed_parameter_recommendations, gate I3_primary_consistency_p0_095`
- `studies/study3/analysis/independent_methods_review_packet.md :: section 2 lines 68-118`
- `studies/study3/analysis/independent_methods_review_packet.md :: section 4 profile table lines 148-151`

### 16. Is the discordance-rate grid wide enough?

**Verdict: NO.**

No, and width is the wrong frame. Under the null boundary delta = -margin the nuisance parameter q = pi21 ranges over the closed interval from 0 to (1 - margin)/2, so the total discordance rate 2q + margin ranges over the whole interval from the margin to 1. The registered grid 0.05, 0.10, 0.20, 0.30 covers at most 30 percent of that domain and, at margin 0.10 with n 384, the supremum falls at discordance 0.4782 - outside the grid by a wide margin. The logical point is decisive and independent of any particular number: a finite grid bounds a supremum only from below, so an exceedance the grid finds is real while an exceedance it misses is invisible. Four evaluations are a sensitivity check, never proof of global size control. Widening the grid is not the fix. The fix is one of the four remedies the operator authority enumerates: a justified nuisance maximisation over the feasible null boundary, a calibrated conservative critical value over the full registered domain, a conservative-by-construction exact procedure, or leaving the method unresolved and returning a non-accepting disposition.

Findings: `S3MR-005`.

Evidence:

- `studies/study3/analysis/independent_methods_recalculation_tables.json :: paired_equivalence.size_over_feasible_null_boundary, fields feasible_discordance_range, discordance_at_supremum, drafting_grid_rows, supremum_is_a_lower_bound`
- `tests/test_study3_design.py :: test_paired_sensitivity_covers_the_required_discordance_rates, lines 772-777`

### 17. Are the label-selection uniformity bands the right symmetry check, and is the Bonferroni level within them correct?

**Verdict: QUALIFIED.**

The check is the right one and its level is mislabelled. Testing, for each label position, whether the selection rate departs from the uniform expectation is the correct nuisance-symmetry diagnostic, and treating it as a nuisance check rather than a competence claim is correct: a uniform selection rate is neither necessary nor sufficient for a working interface, and a failure indicates a position artefact rather than incapacity. Recomputing all three bands independently shows they match a two-sided interval convention that places alpha/2 in each tail, not the one-sided reading their field name suggests. The convention is applied consistently across all three bands and is defensible for a two-sided symmetry check; only the naming is wrong. Recorded as QUALIFIED and MINOR, with the required change being to rename the field and state the tail convention explicitly rather than to change any number.

Findings: `S3MR-019`.

Evidence:

- `studies/study3/analysis/independent_methods_recalculation_tables.json :: label_selection_uniformity_bands`
- `studies/study3/analysis/design_statistics.py :: simultaneous_alpha, line 467`

### 18. Are the descriptive Clopper-Pearson bounds clearly separated from the gate decisions?

**Verdict: QUALIFIED.**

Separated in substance, blurred in labelling. The packet states in terms that the Clopper-Pearson lower bounds are descriptive interval statements carrying no gate authority, no gate rule references them, and the reviewer confirms that no decision path consumes them. That separation is correct and is accepted. The blur is that all twelve committed bounds are computed at half of the field named simultaneous_alpha - the two-sided interval convention - while the field name and surrounding text read as a one-sided simultaneous level. The bounds are therefore internally consistent and defensible, and merely misdescribed. One further presentational risk: a descriptive lower bound at the same nominal level as a gate invites a reader to treat the bound as if it were the test. The required change is to rename the field, state the tail convention, and label the bounds as descriptive at the point of tabulation.

Findings: `S3MR-019`.

Evidence:

- `studies/study3/analysis/independent_methods_review_packet.md :: section 2 descriptive quantities paragraph, lines 114-116`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: descriptive_clopper_pearson_lower_bounds`

### 19. Is any quantity in this packet presented as a measurement rather than as a proposed design parameter?

**Verdict: QUALIFIED.**

No quantity is presented as a measurement of a model, and the reviewer confirms that no model has been observed anywhere in the draft: the operation counters are zero throughout and the drafting tables are pure sampling-distribution arithmetic. One class of quantity is nevertheless presented as an established property when it is a claim that fails. The JSON records that the paired method's realised type-I error does not exceed its nominal one-sided level, phrased as a verified fact rather than as a proposal, and that statement is false against the draft's own disclosed 0.025501 and against the reviewer's independent maximisation. Similarly, verified_before_use asserts a verification status that the underlying check cannot deliver. These are misstated verification claims rather than misrepresented measurements, but they occupy the same rhetorical position and must be corrected.

Findings: `S3MR-004`.

Evidence:

- `studies/study3/protocol/interface_calibration_protocol_draft.json :: gate_hierarchy I3.secondary_criterion.verified_before_use`
- `studies/study3/design_receipt_v0_2.json :: operation counters, all zero`

### 20. Is there any hypothesis in the protocol that is not stated in section 2?

**Verdict: YES.**

Yes, at least two hypothesis-bearing decisions with gate authority are absent from packet section 2. First, I5. Section 2 states nulls, alternatives, sample sizes, alphas and rejection counts for I1a, I1b, I2, I3 primary, I3 secondary and I4, and it states the label-uniformity null - but I5 appears only as a prose question in the gate table at line 62, as a fail-closed route at line 132, and as a column entry in the profile table at lines 148 to 151. It has no null, no alternative, no n, no alpha and no rejection rule anywhere. Second, the development profile-selection decision. Choosing one profile out of the selectable set on the development split is a data-dependent inferential act that determines what is confirmed, and it is what Family B exists to protect, yet section 2 states no selection rule, no tie-breaking rule and no error statement for it. A further presentational defect compounds this: the I3 primary table at packet lines 88 to 97 has no null column and lists eight rows under a single stated null p <= 0.9, but the last four rows are computed at p0 0.95, as the reviewer's independent recomputation confirms.

Findings: `S3MR-007`, `S3MR-017`.

Evidence:

- `studies/study3/analysis/independent_methods_review_packet.md :: section 2, lines 68-118`
- `studies/study3/analysis/independent_methods_review_packet.md :: line 62, line 132, lines 148-151`
- `studies/study3/analysis/independent_methods_recalculation_tables.json :: exact_binomial_gate_grid`

### 21. Does any gate in section 3 authorise mechanistic execution, and is every failure route fail-closed?

**Verdict: YES.**

No gate authorises mechanistic execution, and the fail-closed structure is correct. Every gate row terminates in a calibration outcome; the I5 row states explicitly that a pass calibrates the interface and that a separate authority is still required before any mechanistic work; every failure routes to a STOP state; and STOP_CONFIRMATION_FAILED spends the confirmation split irreversibly, which is the correct one-shot discipline. The reviewer traced each route and found no path by which a gate outcome creates mechanistic or causal authority, and none by which a confirmation outcome could select a different interface. Two qualifications that do not change the verdict: the fail-closed guarantee is only as good as the gate definitions it propagates, and the I3 primary gate is currently not computable, so the route from I3 is fail-closed but not well-defined; and because I5 has no rejection rule, the input to its fail-closed route is undetermined.

Findings: `S3MR-001`, `S3MR-017`.

Evidence:

- `studies/study3/analysis/independent_methods_review_packet.md :: section 3 gate table, lines 120-141`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: gate_hierarchy failure routes`

### 22. Should any additional statistical choice be added to section 7 before this draft may be frozen?

**Verdict: YES.**

Yes. Ten additions are required before a freeze may be considered: the number of applicable derived variants per base item for every profile, published as an explicit field; two separate I3 indicators - invariance of the chosen content and correctness under every variant - together with their explicit conjunction; the applicable component set per profile for the Family A intersection; the implemented component alpha for every gate, consistent with whatever Family B level is claimed; a nuisance-maximisation, calibration or conservative-by-construction rule for the paired secondary criterion, together with its registered domain, tolerance, bracketing rule, convergence-failure behaviour and an independent validation; a single I3 primary floor with a demonstration that it is reachable at an admissible n; the full I5 confirmation specification - null, alternative, n, alpha, rejection rule and multiplicity treatment; the development profile-selection rule including tie-breaking, fixed before any data; the statistical fields a later OD2 authority must freeze for the positive reference; and an explicit unit for every sample-size symbol, since n currently changes meaning between files.

Findings: `S3MR-001`, `S3MR-002`, `S3MR-003`, `S3MR-005`, `S3MR-006`, `S3MR-014`, `S3MR-017`.

Evidence:

- `studies/study3/analysis/independent_methods_review_packet.md :: section 7 unresolved items U1-U8`
- `studies/study3/protocol/interface_calibration_protocol_draft.json :: unresolved_operator_decisions`

## Findings

20 findings: 6 BLOCKING, 11 MAJOR, 3 MINOR.

| ID | Severity | Title |
| --- | --- | --- |
| `S3MR-001` | BLOCKING | The I3 primary estimand is not identifiable from the published counterbalancing construction |
| `S3MR-002` | BLOCKING | The I3 primary indicator has two mutually exclusive definitions across the authoritative JSON, the companion Markdown and the review packet |
| `S3MR-003` | BLOCKING | The Family B per-profile alpha is stated but implemented nowhere; the committed component rules deliver three times the stated study alpha |
| `S3MR-004` | BLOCKING | The authoritative JSON asserts a conservativeness property that the same draft's own disclosure contradicts |
| `S3MR-005` | BLOCKING | The four-value discordance grid is a sensitivity check, and maximising over the feasible null boundary finds an undisclosed exceedance at a planned configuration |
| `S3MR-006` | BLOCKING | The I3 primary floor is left in two mutually exclusive versions, and the higher one is unreachable at every admissible sample size reviewed |
| `S3MR-007` | MAJOR | The packet's I3 primary table presents two different nulls under one stated hypothesis with no null column |
| `S3MR-008` | MAJOR | I1a and I1b are underpowered at every proposed sample size against the draft's own lowest declared alternative |
| `S3MR-009` | MAJOR | The committed verification of the paired method is circular and the committed design test entrenches the insufficient grid |
| `S3MR-010` | MAJOR | The K5 stratum retains draft-v0.1 generating-process text that the same file elsewhere forbids |
| `S3MR-011` | MAJOR | The K6 stratum retains draft-v0.1 generating-process text that contradicts the resolved answer-cue decision |
| `S3MR-012` | MAJOR | The S3 projected operation accounting contradicts itself by a factor of four |
| `S3MR-013` | MAJOR | The projection is not decomposed into the work streams a feasibility review requires and its role multiplier is not reconcilable |
| `S3MR-014` | MAJOR | The sample-size symbol n changes unit between artifacts and no artifact declares its unit |
| `S3MR-015` | MAJOR | The I3 rejection region is degenerate at one proposed configuration |
| `S3MR-016` | MAJOR | S3's membership in the Family B multiplicity denominator is contingent on a post-data fact |
| `S3MR-017` | MAJOR | The confirmation gate I5 and the development profile-selection rule have no statistical specification anywhere |
| `S3MR-018` | MINOR | Checkpoint role records carry gate labels that predate the I1a/I1b split |
| `S3MR-019` | MINOR | The Clopper-Pearson bounds and the label-uniformity bands use a two-sided tail convention under a one-sided field name |
| `S3MR-020` | MINOR | The positive-reference dossier attributes its own obligation to the wrong prior defect |

### `S3MR-001` (BLOCKING) - The I3 primary estimand is not identifiable from the published counterbalancing construction

The I3 primary indicator quantifies over the set of applicable transformed variants of a base item, but the published construction assigns exactly one (position, symbol) pair to each base item, and no field stating the number of applicable derived variants per base item exists in any Study 3 artifact. The set the indicator ranges over is therefore undefined for the label-bearing profile and the derived quantity cannot be computed from the design as written.

**Rationale.** A one-to-one assignment of base items to (position, symbol) cells and an indicator that quantifies over multiple variants of the same base item cannot both be true of the same construction. Exhaustive search of the protocol JSON, the companion Markdown, the schema, the packet, the drafting statistics script and its tables found no field named variants_per_base_item or any synonym, so the missing factor cannot be recovered by reading. The reviewer can propose a resolution but cannot derive one, because the choice between replicating each base item across all sixteen position-symbol cells and redefining the unit of I3 changes the atomic cell, the unit of n, every I3 threshold and the whole projection.

**Quoted fields.**

- `counterbalancing_design.construction_algorithm.steps[4]: assigns (p, s) = (k mod 4, (k div 4) mod 4) to base item k`
- `atomic_evaluation_cells.cluster_rule: presupposes a cluster of applicable variants per base item`
- `gate_hierarchy I3.primary_indicator: the answer is identical across every applicable transformed variant`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/protocol/interface_calibration_protocol_draft.md`
- `studies/study3/analysis/independent_methods_review_packet.md`

**Required change.** Publish an explicit variants-per-base-item factor for every interface profile and reconcile the construction algorithm with the cluster rule, or restate I3 on a unit the published construction actually produces.

**Reviewer supplied value would be.** inventing design structure that does not exist, which the ACCEPTED_WITH_REQUIRED_CHANGES disposition forbids

### `S3MR-002` (BLOCKING) - The I3 primary indicator has two mutually exclusive definitions across the authoritative JSON, the companion Markdown and the review packet

The authoritative JSON and the companion Markdown define the I3 primary item indicator as the answer being identical across every applicable transformed variant. The review packet defines it as every counterbalanced variant of that base item being scored correct. These are different estimands and they disagree on the case that matters most.

**Rationale.** A base item on which the interface returns the same wrong answer under every variant scores 1 under the identical-answer definition and 0 under the scored-correct definition. The identical-answer definition therefore measures invariance and admits stable incompetence; the scored-correct definition measures correctness under every presentation and cannot separate a presentation artefact from an incapacity. Because the JSON is the authoritative artifact and the Markdown agrees with it, the packet is the outlier - but the packet is the document the reviewer was asked to review, and the drafting party's own power tables are ambiguous between the two. A review may not silently choose one.

**Quoted fields.**

- `interface_calibration_protocol_draft.json line 1295: the answer is identical across every applicable transformed variant`
- `interface_calibration_protocol_draft.md line 503: the answer is identical across every applicable transformed variant`
- `independent_methods_review_packet.md section 2, line 85: the indicator is 1 when every counterbalanced variant of that base item is scored correct`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/protocol/interface_calibration_protocol_draft.md`
- `studies/study3/analysis/independent_methods_review_packet.md`

**Required change.** Publish two indicators - invariance of the chosen content and correctness under every variant - and their explicit conjunction, then reconcile all three artifacts to the published definition and recompute every I3 threshold under it.

**Stable but wrong answer analysis.** passes the JSON and Markdown definition, fails the packet definition; this is the exact case the two definitions disagree on and it is not an edge case, because a systematically mis-keyed or mis-parsed option is precisely the failure mode an interface calibration exists to detect

### `S3MR-003` (BLOCKING) - The Family B per-profile alpha is stated but implemented nowhere; the committed component rules deliver three times the stated study alpha

The protocol states a per-profile alpha of 0.001666666667 obtained by Bonferroni over three selectable profiles against a study alpha of 0.005, but every retained component rule in the committed derivation tables and every threshold in packet section 2 is computed at alpha 0.005. The union bound actually delivered is 3 x 0.005 = 0.015.

**Rationale.** Family A is an intersection-union test, so its size is bounded by the maximum component level, which is the level actually implemented. Implementing every component at 0.005 gives each profile a level of 0.005, and the union over three profiles is bounded by 0.015, three times the stated study alpha. Independently recomputing the affected exact-binomial rejection counts at 0.001666666667 changes them at every gate - I1a and I1b at n 192 from 184 to 185, I2 at n 192 from 115 to 117, I4 at n 192 from 168 to 170 - which demonstrates that the stated level is not merely unlabelled but genuinely unimplemented. Retaining tables computed at 0.005 while claiming control at 0.001666666667 is exactly what the operator authority forbids.

**Quoted fields.**

- `proposed_statistics.hypothesis_families.family_B_across_profiles.per_profile_alpha = 0.001666666667`
- `proposed_statistics.hypothesis_families.family_B_across_profiles.correction = Bonferroni over 3 selectable profiles`
- `proposed_statistics.hypothesis_families.family_B_across_profiles.study_alpha = 0.005`
- `proposed_statistics.hypothesis_families.family_A_within_profile.per_component_alpha = 0.005`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Either implement the per-profile alpha in every component rule and republish every affected threshold, power figure and sample size, or withdraw the 0.001666666667 claim and state the study-level guarantee that alpha 0.005 components actually deliver.

### `S3MR-004` (BLOCKING) - The authoritative JSON asserts a conservativeness property that the same draft's own disclosure contradicts

The gate-hierarchy verification record states that exact enumeration of the paired method shows its realised type-I error does not exceed its nominal one-sided level. The same draft's review packet and methods ledger disclose one configuration with a realised level of 0.025501 against a nominal 0.025.

**Rationale.** This is a direct contradiction inside one draft, not a difference of emphasis. The independent enumeration confirms the disclosed number to nine decimal places - 0.025501092 at n 192 and margin 0.10 - so the drafting arithmetic is right and the assertion built on it is wrong. It matters beyond bookkeeping because the assertion is recorded in the authoritative artifact under a field named verified_before_use, which is the field a later freeze authority would rely on. A verification record that asserts the opposite of the disclosure it summarises cannot support acceptance as specified.

**Quoted fields.**

- `gate_hierarchy I3.secondary_criterion.verified_before_use[2]: exact enumeration shows the realised type-I error does not exceed its nominal one-sided level`
- `independent_methods_review_packet.md: realised level 0.025501 against nominal 0.025`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/references/methods_sources.md`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Withdraw the conservativeness assertion, restate the decision rule as asymptotic with an empirically maximised realised level, and record the maximised level rather than a grid maximum.

### `S3MR-005` (BLOCKING) - The four-value discordance grid is a sensitivity check, and maximising over the feasible null boundary finds an undisclosed exceedance at a planned configuration

The registered discordance values 0.05, 0.10, 0.20 and 0.30 span at most the lower third of the feasible nuisance domain. Maximising the exact level over the full feasible null boundary finds a second exceedance the draft does not report: at n 384 and margin 0.10 the supremum is 0.025073 at discordance 0.4782, while the drafting grid maximum at that configuration is 0.024727 and looks compliant.

**Rationale.** Under the null boundary the nuisance parameter q ranges over the closed interval from 0 to (1 - margin)/2, so the total discordance rate ranges over the whole interval from the margin to 1. A finite grid bounds a supremum only from below: an exceedance the grid finds is real, but the absence of one is never evidence of size control. The demonstration is decisive because it is not hypothetical - n 384 at margin 0.10 is a configuration the design proposes to use, and it is reported as compliant while its true size exceeds the nominal level. Two exceedances are now known where the draft discloses one, and the search that produced the draft's number was structurally incapable of finding the second.

**Quoted fields.**

- `paired_equivalence.size_over_feasible_null_boundary.feasible_discordance_range`
- `paired_equivalence.size_over_feasible_null_boundary.discordance_at_supremum = 0.4782 at n 384, margin 0.10`
- `paired_equivalence.size_over_feasible_null_boundary.size_supremum_over_feasible_boundary = 0.025073 at n 384, margin 0.10`
- `paired_equivalence.size_over_feasible_null_boundary.drafting_grid_rows at n 384, margin 0.10: 0.05 infeasible, 0.10 -> 0.017524, 0.20 -> 0.024284, 0.30 -> 0.024727`
- `tests/test_study3_design.py::test_paired_sensitivity_covers_the_required_discordance_rates enforces the four-value grid as adequate`

**Evidence paths.**

- `studies/study3/analysis/independent_methods_recalculation_tables.json`
- `studies/study3/analysis/design_statistics_tables.json`
- `tests/test_study3_design.py`

**Required change.** Replace the grid with a justified nuisance maximisation over the feasible null boundary, a critical value calibrated over the full registered domain, or a conservative-by-construction exact procedure such as the unconditional exact approach of Hsueh, Liu and Chen (2001); register the optimisation domain, tolerance, bracketing rule, convergence-failure behaviour and an independent validation.

### `S3MR-006` (BLOCKING) - The I3 primary floor is left in two mutually exclusive versions, and the higher one is unreachable at every admissible sample size reviewed

The draft carries I3 primary threshold tables at both p0 0.90 and p0 0.95 without resolving which is the registered floor. At p0 0.95 with the draft's own lowest declared alternative p1 0.97 and the corrected Family B alpha, no admissible n up to 768 attains 0.90 power.

**Rationale.** A gate cannot have two floors. The choice is substantive rather than cosmetic: at p0 0.90 the gate is reachable at n 256 with rejection count 244 and power 0.953040775, whereas at p0 0.95 the alternative of interest sits only two percentage points above the floor and the exact test cannot separate them at any admissible size the counterbalancing divisors allow. The draft therefore contains a gate specification that is either underdetermined or infeasible, and the reviewer cannot resolve it by choosing, because widening the alternative to make a preferred sample size pass is precisely what the operator authority forbids.

**Quoted fields.**

- `independent_methods_review_packet.md section 2, I3 primary table lines 88-97: eight rows under one stated null p <= 0.9, the last four computed at p0 0.95`
- `reviewed_parameter_recommendations, gate I3_primary_consistency_p0_095: recommended_n null, recommended_n_reachable_within_reviewed_grid false`

**Evidence paths.**

- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Register one I3 primary floor and one substantively justified alternative, and demonstrate that the pair is separable at an admissible n at the implemented alpha; if it is not, revise the scientific claim rather than the alternative.

### `S3MR-007` (MAJOR) - The packet's I3 primary table presents two different nulls under one stated hypothesis with no null column

Packet section 2 states the I3 primary null as p <= 0.9 and then tabulates eight rows with columns n, alpha, rejection count and exact null tail, and no null column. Independent recomputation shows the first four rows are computed at p0 0.90 and the last four at p0 0.95.

**Rationale.** A reader of the packet, which is the document the independent reviewer was handed, sees eight rows offered as thresholds for a single hypothesis. Four of them are thresholds for a different hypothesis. This is how the unresolved floor of finding S3MR-006 became invisible, and it is a presentational defect with inferential consequences.

**Quoted fields.**

- `independent_methods_review_packet.md lines 84-97`
- `exact_binomial_gate_grid: at alpha 0.005 the rejection counts at p0 0.90 are 124, 184, 243, 361 for n 128, 192, 256, 384 and at p0 0.95 are 128, 190, 252, 376`

**Evidence paths.**

- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Add an explicit null column, or split the table, and state the registered floor once.

### `S3MR-008` (MAJOR) - I1a and I1b are underpowered at every proposed sample size against the draft's own lowest declared alternative

At n 192, p1 0.97 and alpha 0.005 the exact power is 0.87425 against a target of 0.90, and the drafting tables themselves record meets_target_power_0_90_at_lowest_alternative false at both n 128 and n 192.

**Rationale.** Running a gate at 0.874 power against the design's own lowest alternative discards roughly one qualifying interface in eight, and because Family A is a conjunction the shortfall compounds across components. Searching the full admissible grid rather than the four sizes the draft examined gives the smallest admissible n as 224 at alpha 0.005 and 256 at the corrected Family B alpha. Exact-binomial power is not monotone in n across a rejection-count change, so the recalculation also records the smallest admissible n that holds the target thereafter.

**Quoted fields.**

- `design_statistics_tables.json :: meets_target_power_0_90_at_lowest_alternative = false at n 128 and n 192`
- `smallest_admissible_n_reaching_target_power :: gate I1a_trivial_recovery`
- `reviewed_parameter_recommendations :: I1a_trivial_recovery recommended_n 256, rejection_count 244, exact_power_at_p1 0.953040775`

**Evidence paths.**

- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Raise n to the smallest admissible size meeting the reviewed target at the implemented alpha, or lower the target power explicitly and justify it; do not move p1.

### `S3MR-009` (MAJOR) - The committed verification of the paired method is circular and the committed design test entrenches the insufficient grid

design_statistics.py::verify_paired_method raises only if the three rows the same script recorded exceed the nominal level, and tests/test_study3_design.py asserts the bound over those same three rows while a second test enforces the four-value discordance grid as adequate coverage.

**Rationale.** A check that validates the rows the checked script chose to emit cannot detect a supremum outside them, and the reviewer has demonstrated that such a supremum exists at a planned configuration. Worse, the second test converts the insufficient grid into a committed requirement, so a future contributor who widened the search would be told by the test suite that four values are the correct coverage. Recorded rather than repaired, per the operator authority: the existing design test exposes a defect and must not be edited to make this review pass.

**Quoted fields.**

- `design_statistics.py lines 313-362, check at line 348`
- `tests/test_study3_design.py::test_paired_method_was_verified_before_use, lines 741-749`
- `tests/test_study3_design.py::test_paired_sensitivity_covers_the_required_discordance_rates, lines 772-777`

**Evidence paths.**

- `studies/study3/analysis/design_statistics.py`
- `tests/test_study3_design.py`

**Required change.** Replace the recorded-rows assertion with a maximisation over the registered nuisance domain, and replace the fixed-grid coverage test with a test of the registered maximisation contract. This change belongs to the amendment round, not to this review.

### `S3MR-010` (MAJOR) - The K5 stratum retains draft-v0.1 generating-process text that the same file elsewhere forbids

task_strata[5].data_generating_process still registers the four cyclic permutations of the option order plus one label-set replacement from A/B/C/D to 1/2/3/4 as the default, although the same file records the cyclic order as the v0.1 defect, records the resolution as an orthogonal construction with 1/2/3/4 forbidden, and lists 1/2/3/4 in forbidden_alphabets.

**Rationale.** The authoritative artifact simultaneously registers a generating process as the default and forbids its components. An implementer reading the stratum definition would build the forbidden design. This is a stale-text defect rather than a statistical one, but it sits in the authoritative file and a freeze would freeze it.

**Quoted fields.**

- `task_strata[5].data_generating_process`
- `task_strata[5].v0_1_defect`
- `operator_review_v0_1.defects[8] (D-09) resolution: resolved; orthogonal construction published, 1/2/3/4 forbidden`
- `counterbalancing_design.forbidden_alphabets[0].alphabet = ["1","2","3","4"], lines 565-573`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`

**Required change.** Rewrite task_strata[5].data_generating_process to the orthogonal construction actually adopted.

### `S3MR-011` (MAJOR) - The K6 stratum retains draft-v0.1 generating-process text that contradicts the resolved answer-cue decision

task_strata[6].data_generating_process still describes three renderings differing only in the separator, the instruction sentence and the answer cue, although varying the answer cue was the v0.1 defect, rendering[2] is recorded as byte-identical to R-base in its answer cue, and the operator disposition holds the answer cue constant across all three renderings.

**Rationale.** Same class as S3MR-010 and with a sharper consequence: the answer cue is the channel through which K6 could confound a rendering effect with a cue effect, which is why holding it constant was the resolution. Text that reinstates it as a varying factor would reintroduce the confound if implemented.

**Quoted fields.**

- `task_strata[6].data_generating_process`
- `task_strata[6].renderings.v0_1_defect`
- `task_strata[6].renderings[2].description: the answer cue is byte-identical to R-base`
- `unresolved_operator_decisions[3].disposition: The answer cue is held constant across all three.`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`

**Required change.** Rewrite task_strata[6].data_generating_process to state that only the separator and the instruction sentence vary.

### `S3MR-012` (MAJOR) - The S3 projected operation accounting contradicts itself by a factor of four

The S3 profile record states one forward pass per item and warns that S3 does not add four separate scorings and must not be budgeted as if it did, while the operation-boundaries projection budgets 9728 S3 sequence scorings, which is exactly four times the 2432 budgeted for each other surface.

**Rationale.** The development total of 68096 is (2432 + 2432 + 9728 + 2432) x 4 roles, so the four-times figure is load-bearing in the published total. One of the two statements must be wrong, and the projection is the arithmetic a later cost or feasibility decision would rest on.

**Quoted fields.**

- `interface_profiles[S3].projected_operation_counts_if_later_authorized.forward_passes_per_item = 1`
- `interface_profiles[S3].projected_operation_counts_if_later_authorized.note: it does not add four separate scorings and must not be budgeted as if it did`
- `operation_boundaries.projected_future_operations.per_role_per_surface.S3_sequence_scorings = 9728`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`

**Required change.** Decide whether S3 scores one sequence or four per item, correct the projection, and republish the totals.

### `S3MR-013` (MAJOR) - The projection is not decomposed into the work streams a feasibility review requires and its role multiplier is not reconcilable

The published projection reports per-role-per-surface scoring counts and a development total, but does not separate positive-reference prequalification work, positive-reference I4 work, target development work, selected-profile confirmation work and S4 diagnostic work, and its multiplier of four roles cannot be reconciled with the three target-bearing model roles plus a positive-reference role that carries only I4.

**Rationale.** Multiplying every surface by four roles charges the positive reference for gates it does not carry and charges the target roles for the positive-reference bank. The independent projection separates the five streams and reports 269568 development scored rows, 258048 confirmation scored rows, 24576 positive-reference I4 rows and 258048 S4 diagnostic rows for a total of 810240, all with zero executed operations. The point is not that one total is right and the other wrong; it is that a single undifferentiated total cannot support the feasibility judgement it is offered for.

**Quoted fields.**

- `operation_boundaries.projected_future_operations.per_role_per_surface`
- `checkpoint_roles: RT, RL, RI are model roles bearing targets; RP is a model role recorded as Gate I4 only`
- `projected_cells_and_operations.work_streams in the independent recalculation`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Republish the projection decomposed by work stream, with base items, derived variants and scored rows separated, and with the role multiplier stated per gate.

### `S3MR-014` (MAJOR) - The sample-size symbol n changes unit between artifacts and no artifact declares its unit

No Study 3 artifact attaches a unit to any sample-size symbol. The gate tables use n as base items per atomic cell, the counterbalancing discussion uses it as a count that must be divisible by the number of derived presentation variants, and the projection totals count scored rows. The same symbol therefore denotes three different quantities.

**Rationale.** Unit ambiguity in a sample-size symbol is not pedantry when the independent unit is contested, as it is here by finding S3MR-001. A reader cannot tell whether n 192 means 192 base items, 192 rendered presentations or 192 scored rows, and the three differ by up to a factor of 96 for the label-bearing profile. Every power statement in the draft is uninterpretable until this is fixed.

**Quoted fields.**

- `independent_methods_review_packet.md section 2 gate tables, column n`
- `counterbalancing_design divisors`
- `operation_boundaries.projected_future_operations totals`
- `projected_cells_and_operations.unit_definitions.n_symbol_meaning in the independent recalculation`

**Evidence paths.**

- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Declare the unit of every sample-size symbol at the point of definition and hold it constant across all artifacts.

### `S3MR-015` (MAJOR) - The I3 rejection region is degenerate at one proposed configuration

At n 128 with p0 0.95 and alpha 0.005 the exact rejection count equals 128, so every base item must be scored correct for the gate to pass.

**Rationale.** A rule with no tolerance for a single scoring artefact is not a statistical test in any useful sense: its power against any alternative below one decays as p1 to the power 128, and a single ambiguous parse fails the gate regardless of the interface's quality. The configuration appears in the draft's own tables and would be a legal choice under the unresolved floor.

**Quoted fields.**

- `exact_binomial_gate_grid: n 128, p0 0.95, alpha 0.005, rejection count 128`

**Evidence paths.**

- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Exclude degenerate rejection regions explicitly, or raise n so that the rejection count is strictly below n at the registered floor and alpha.

### `S3MR-016` (MAJOR) - S3's membership in the Family B multiplicity denominator is contingent on a post-data fact

S3 carries the status conditionally_selectable, its registered activation condition is not met, and the draft records that on a single-token answer domain its selection rule reduces to S2's. Whether the Bonferroni denominator is three or two therefore depends on an outcome that will not be known until the development split has been scored.

**Rationale.** The draft elsewhere forbids reducing a multiplicity denominator after data are observed, which is the correct rule. Leaving S3's membership contingent creates exactly that route, and it is not cured by intending to be conservative, because the intention is not registered. The rule may be conservative - fix the denominator at three regardless - but it must be fixed before any data.

**Quoted fields.**

- `interface_profiles[S3].selectability = conditionally_selectable`
- `proposed_statistics.hypothesis_families.family_B_across_profiles.correction = Bonferroni over 3 selectable profiles`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`

**Required change.** Register S3's contribution to the Family B denominator before any data, and state it as a fixed number rather than as a condition.

### `S3MR-017` (MAJOR) - The confirmation gate I5 and the development profile-selection rule have no statistical specification anywhere

Packet section 2 states nulls, alternatives, sample sizes, alphas and rejection counts for every gate except I5, which appears only as a prose question, a fail-closed route and a column in the profile table. The development profile-selection rule, which determines what is confirmed and is what Family B exists to protect, is likewise unspecified.

**Rationale.** The scientific calibration claim is made on the confirmation split, so the confirmation gate is the one gate whose error rate the claim actually depends on. Leaving it unspecified means the draft's alpha statements describe only the development screen. The selection rule is the second half of the same gap: a data-dependent choice with no registered rule cannot be given an error guarantee, conservative or otherwise.

**Quoted fields.**

- `independent_methods_review_packet.md line 62: I5 gate table row`
- `independent_methods_review_packet.md line 132: I5 fail-closed route`
- `independent_methods_review_packet.md lines 148-151: I5 listed per profile`
- `independent_methods_review_packet.md section 2, lines 68-118: no I5 hypothesis, n, alpha or rejection rule`

**Evidence paths.**

- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/protocol/interface_calibration_protocol_draft.json`

**Required change.** Publish the full I5 specification - null, alternative, n, alpha, rejection rule and multiplicity treatment - and the development selection rule including tie-breaking, both fixed before any data; state the development and confirmation error roles separately rather than applying one alpha statement to both.

### `S3MR-018` (MINOR) - Checkpoint role records carry gate labels that predate the I1a/I1b split

The checkpoint_roles records still name Gate I1 and gate sets containing I1, although I1 was split into I1a and I1b in this draft.

**Rationale.** Stale labelling. It matters slightly more than cosmetics because I1b is not applicable to the content-only profiles, so a role record naming an undivided I1 leaves the applicable component set ambiguous for exactly the profiles where it is contested.

**Quoted fields.**

- `checkpoint_roles[1].gate_role = Gate I1`
- `checkpoint_roles[2].gate_role = Gates I1, I2, I3, I5`
- `checkpoint_roles[3].gate_role = Gates I1, I2, I3`
- `checkpoint_roles[4].gate_role = Gates I1, I2, I3`

**Evidence paths.**

- `studies/study3/protocol/interface_calibration_protocol_draft.json`

**Required change.** Update every role record to the post-split gate names and state applicability per profile.

### `S3MR-019` (MINOR) - The Clopper-Pearson bounds and the label-uniformity bands use a two-sided tail convention under a one-sided field name

All twelve committed Clopper-Pearson lower bounds and all three label-uniformity acceptance bands are reproduced exactly by placing half of the field named simultaneous_alpha in each tail, not by a one-sided tail at that level.

**Rationale.** The convention is applied consistently across all fifteen quantities and is defensible for a two-sided symmetry band and for a descriptive interval. This is a naming and documentation defect, not an arithmetic one, and it is classified QUALIFIED rather than as an error precisely because the reviewer could reproduce every number under one coherent reading.

**Quoted fields.**

- `design_statistics.py line 467: simultaneous_alpha`
- `descriptive_clopper_pearson_lower_bounds and label_selection_uniformity_bands in the independent recalculation`

**Evidence paths.**

- `studies/study3/analysis/design_statistics.py`
- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`

**Required change.** Rename the field and state the tail convention explicitly at the point of tabulation.

### `S3MR-020` (MINOR) - The positive-reference dossier attributes its own obligation to the wrong prior defect

The dossier attributes the positive-reference obligation to defect D-07 in two places, but the authoritative record lists D-07 as pooling could mask a failed cell and assigns the positive-reference circularity and chance-level floor issue to D-04.

**Rationale.** A traceability defect. It matters because the dossier is the document a later OD2 authority would read to learn what the positive reference must satisfy, and a wrong back-reference sends that reader to the pooling defect instead of to the circularity defect the dossier exists to close.

**Quoted fields.**

- `positive_reference_dossier.md lines 17 and 193: D-07`
- `operator_review_v0_1.defects: D-07 = pooling could mask a failed cell`
- `operator_review_v0_1.defects: D-04 = positive-reference circularity and a chance-level floor that is not a capability floor`

**Evidence paths.**

- `studies/study3/references/positive_reference_dossier.md`
- `studies/study3/protocol/interface_calibration_protocol_draft.json`

**Required change.** Correct both references to D-04.

## Cross-artifact consistency adjudications

Every decision-bearing statement in the authoritative JSON was compared against the companion Markdown, the review packet, the drafting derivation tables, the study README and the thread handoff. Each candidate inconsistency below carries exactly one status.

Each candidate inconsistency receives exactly one status from `CONFIRMED_BLOCKING`, `CONFIRMED_NONBLOCKING`, `NOT_CONFIRMED` or `QUALIFIED`.

| ID | Status | Candidate |
| --- | --- | --- |
| `CI-01` | **CONFIRMED_BLOCKING** | The authoritative JSON defines the I3 primary item indicator as the answer being identical across every applicable variant; the review packet defines it as every variant being scored correct. |
| `CI-02` | **CONFIRMED_BLOCKING** | Whether a stable but WRONG answer passes either I3 definition. |
| `CI-03` | **CONFIRMED_BLOCKING** | The JSON gate-hierarchy verification text says exact enumeration of the paired method does not exceed the nominal one-sided level; the packet and methods ledger disclose a realised 0.025501 against nominal 0.025. |
| `CI-04` | **CONFIRMED_BLOCKING** | Family B per-profile alpha 0.001666666667 versus retained component rules computed at alpha 0.005. |
| `CI-05` | **CONFIRMED_BLOCKING** | Whether the four discordance values 0.05, 0.10, 0.20 and 0.30 are a sensitivity grid rather than proof of global size control. |
| `CI-06` | **CONFIRMED_NONBLOCKING** | Whether every hypothesis with gate authority is stated in packet section 2, including label-uniformity, confirmation, and any profile-selection decision. |
| `CI-07` | **CONFIRMED_NONBLOCKING** | Whether every sample-size symbol has one unambiguous unit across files: base items per atomic cell, derived variants, or total calls. |
| `CI-08` | **NOT_CONFIRMED** | Whether the three permitted review dispositions are operationally distinguishable, and specifically whether a design with unresolved parameter values may be accepted as specified because the reviewer can imagine values that would work. |
| `CI-09` | **CONFIRMED_NONBLOCKING** | K5 registers the four cyclic permutations and the 1/2/3/4 label set as its default generating process while the same file forbids both. |
| `CI-10` | **CONFIRMED_NONBLOCKING** | K6 registers the answer cue as a varying factor while the same file holds it constant and records varying it as the v0.1 defect. |
| `CI-11` | **CONFIRMED_NONBLOCKING** | S3 is recorded as one forward pass per item with an explicit warning against budgeting four scorings, while the projection budgets 9728 S3 sequence scorings, four times every other surface. |
| `CI-12` | **CONFIRMED_NONBLOCKING** | Checkpoint role records name Gate I1 after I1 was split into I1a and I1b. |
| `CI-13` | **QUALIFIED** | The Clopper-Pearson bounds and the label-uniformity bands are described as one-sided at simultaneous_alpha but are computed at half that level in each tail. |
| `CI-14` | **CONFIRMED_NONBLOCKING** | The positive-reference dossier attributes the positive-reference obligation to defect D-07, while the authoritative record assigns that obligation to D-04. |
| `CI-15` | **QUALIFIED** | The draft cites Hsueh, Liu and Chen (2001) for unconditional exact paired equivalence testing while implementing Tango's (1998) asymptotic score procedure. |
| `CI-16` | **CONFIRMED_BLOCKING** | The I3 primary floor appears as both 0.90 and 0.95 across the packet tables and the drafting derivation tables without a resolution. |
| `CI-17` | **CONFIRMED_NONBLOCKING** | The drafting tables record that I1a and I1b do not meet the target power at the lowest declared alternative while the packet presents n 192 as a proposed operating size. |

### `CI-01` - CONFIRMED_BLOCKING

The authoritative JSON defines the I3 primary item indicator as the answer being identical across every applicable variant; the review packet defines it as every variant being scored correct.

**Rationale.** These are not the same estimand. Identity of the answer measures invariance and is satisfied by a stably wrong answer; correctness under every variant measures competence under presentation change and cannot distinguish a presentation artefact from an incapacity. The JSON and Markdown agree with each other and the packet is the outlier, but the packet is the review object the drafting party submitted and its own power tables do not disambiguate. Blocking because the primary gate of the study cannot have two definitions.

Files and exact field names:

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/protocol/interface_calibration_protocol_draft.md`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `gate_hierarchy I3.primary_indicator (JSON line 1295): the answer is identical across every applicable transformed variant`
- `interface_calibration_protocol_draft.md line 503: identical (same wording as the JSON)`
- `independent_methods_review_packet.md section 2 line 85: every counterbalanced variant of that base item is scored correct`

Findings: `S3MR-002`.

### `CI-02` - CONFIRMED_BLOCKING

Whether a stable but WRONG answer passes either I3 definition.

**Rationale.** Explicit adjudication as required. A base item on which the interface returns the same wrong answer under every applicable variant scores 1 under the JSON and Markdown definition and 0 under the packet definition. The two definitions therefore differ on the single case that decides what I3 measures, and it is not a rare corner: a systematically mis-keyed option or a mis-parsed answer cue produces exactly this pattern, and it is the pattern an interface calibration exists to detect. Blocking, and the reason the draft must publish two indicators and their conjunction rather than one overloaded indicator.

Files and exact field names:

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `gate_hierarchy I3.primary_indicator: identical across every applicable transformed variant`
- `independent_methods_review_packet.md section 2 line 85: scored correct`

Findings: `S3MR-002`.

### `CI-03` - CONFIRMED_BLOCKING

The JSON gate-hierarchy verification text says exact enumeration of the paired method does not exceed the nominal one-sided level; the packet and methods ledger disclose a realised 0.025501 against nominal 0.025.

**Rationale.** A direct contradiction within one draft. The independent enumeration confirms 0.025501092 at n 192 and margin 0.10, so the disclosure is right and the assertion built on it is wrong. It invalidates acceptance as specified because the false assertion is recorded in the authoritative artifact under the field a later freeze authority would rely on.

Files and exact field names:

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/references/methods_sources.md`
- `gate_hierarchy I3.secondary_criterion.verified_before_use[2]`
- `packet and methods ledger disclosure of 0.025501 against nominal 0.025`

Findings: `S3MR-004`.

### `CI-04` - CONFIRMED_BLOCKING

Family B per-profile alpha 0.001666666667 versus retained component rules computed at alpha 0.005.

**Rationale.** Shown mathematically rather than asserted. Family A is an intersection-union test whose size is bounded by the maximum implemented component level, which is 0.005; the union over three profiles is therefore bounded by 0.015, three times the stated study alpha. The stated per-profile level is achieved by no committed rule. Independently recomputing the rejection counts at 0.001666666667 changes them at every gate - I1a and I1b at n 192 from 184 to 185, I2 from 115 to 117, I4 from 168 to 170 - which proves the level is unimplemented rather than merely undocumented. A required change, not a labelling fix.

Files and exact field names:

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `family_B_across_profiles.per_profile_alpha = 0.001666666667`
- `family_B_across_profiles.correction = Bonferroni over 3 selectable profiles`
- `family_B_across_profiles.study_alpha = 0.005`
- `family_A_within_profile.per_component_alpha = 0.005`

Findings: `S3MR-003`.

### `CI-05` - CONFIRMED_BLOCKING

Whether the four discordance values 0.05, 0.10, 0.20 and 0.30 are a sensitivity grid rather than proof of global size control.

**Rationale.** Confirmed both logically and by counterexample. Logically, the feasible discordance domain under the null boundary is the whole interval from the margin to 1, so four points bound the supremum only from below and their compliance is never evidence. By counterexample, at n 384 and margin 0.10 the supremum is 0.025073 at discordance 0.4782 while the grid maximum is 0.024727 and reports compliance - an exceedance at a planned configuration that the registered grid is structurally incapable of finding.

Files and exact field names:

- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`
- `tests/test_study3_design.py`
- `paired sensitivity rows at discordance 0.05, 0.10, 0.20, 0.30`
- `paired_equivalence.size_over_feasible_null_boundary.discordance_at_supremum`
- `tests/test_study3_design.py::test_paired_sensitivity_covers_the_required_discordance_rates`

Findings: `S3MR-005`.

### `CI-06` - CONFIRMED_NONBLOCKING

Whether every hypothesis with gate authority is stated in packet section 2, including label-uniformity, confirmation, and any profile-selection decision.

**Rationale.** Label-uniformity is stated, so that part of the candidate is not confirmed. Confirmation and profile selection are not stated, so the candidate is confirmed in substance. Classified non-blocking only because it is an omission that an amendment round can close by publishing specifications, rather than a contradiction that requires redesigning an estimand; it is nevertheless a required change and it is the reason item 15 cannot be answered affirmatively.

Files and exact field names:

- `studies/study3/analysis/independent_methods_review_packet.md`
- `section 2 lines 109-112: label-selection uniformity null IS stated`
- `section 2 lines 68-118: no I5 null, alternative, n, alpha or rejection rule`
- `section 2 lines 68-118: no development profile-selection rule`

Findings: `S3MR-017`.

### `CI-07` - CONFIRMED_NONBLOCKING

Whether every sample-size symbol has one unambiguous unit across files: base items per atomic cell, derived variants, or total calls.

**Rationale.** Confirmed: no artifact declares a unit for any sample-size symbol, and the same symbol denotes base items in the gate tables, a divisibility-constrained count in the counterbalancing discussion and scored rows in the projection. Non-blocking as a category because declaring units is a documentation act that changes no number, but it interacts with the blocking finding S3MR-001, because the correct unit cannot even be chosen until the independent unit of I3 is settled.

Files and exact field names:

- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `packet section 2 gate tables, column n`
- `counterbalancing_design divisors`
- `operation_boundaries.projected_future_operations totals`

Findings: `S3MR-014`.

### `CI-08` - NOT_CONFIRMED

Whether the three permitted review dispositions are operationally distinguishable, and specifically whether a design with unresolved parameter values may be accepted as specified because the reviewer can imagine values that would work.

**Rationale.** No inconsistency found. The three dispositions are operationally distinguishable and the reviewer applied them as distinct: accepted as specified requires that the committed specification already suffice; accepted with required changes requires that the changes be expressible without inventing new design structure; rejected applies when the estimand is not identifiable, type-I control cannot be specified, or the repair would alter the core design. This review is a worked demonstration of the distinction, since the reviewer can and does supply candidate values for several missing parameters and nevertheless does not accept, exactly as the authority requires.

Files and exact field names:

- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/prompts/study3_v0_2_independent_methods_review_authority.md`
- `independent_methods_review_packet.md lines 459-466: the three permitted dispositions`
- `operator authority section 7 disposition rules`

### `CI-09` - CONFIRMED_NONBLOCKING

K5 registers the four cyclic permutations and the 1/2/3/4 label set as its default generating process while the same file forbids both.

**Rationale.** Confirmed by direct quotation from a single file. Non-blocking because the resolved construction is published elsewhere in the same file and the defect is stale text rather than an unresolved design question; it must nevertheless be corrected before a freeze, since a freeze would freeze the contradiction.

Files and exact field names:

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `task_strata[5].data_generating_process`
- `task_strata[5].v0_1_defect`
- `operator_review_v0_1.defects[8] (D-09) resolution`
- `counterbalancing_design.forbidden_alphabets[0].alphabet = ["1","2","3","4"] (lines 565-573)`

Findings: `S3MR-010`.

### `CI-10` - CONFIRMED_NONBLOCKING

K6 registers the answer cue as a varying factor while the same file holds it constant and records varying it as the v0.1 defect.

**Rationale.** Confirmed by direct quotation. Non-blocking on the same reasoning as CI-09, with the note that the consequence of implementing the stale text would be a genuine confound between rendering and cue rather than merely an inconsistent record.

Files and exact field names:

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `task_strata[6].data_generating_process`
- `task_strata[6].renderings.v0_1_defect`
- `task_strata[6].renderings[2].description: the answer cue is byte-identical to R-base`
- `unresolved_operator_decisions[3].disposition: The answer cue is held constant across all three.`

Findings: `S3MR-011`.

### `CI-11` - CONFIRMED_NONBLOCKING

S3 is recorded as one forward pass per item with an explicit warning against budgeting four scorings, while the projection budgets 9728 S3 sequence scorings, four times every other surface.

**Rationale.** Confirmed: 9728 = 4 x 2432 and the development total 68096 = (2432 + 2432 + 9728 + 2432) x 4, so the factor of four is load-bearing in the published total and directly contradicts the profile record. Non-blocking because it affects planning arithmetic rather than an inferential guarantee, but it must be resolved because a feasibility or cost decision would rest on it.

Files and exact field names:

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `interface_profiles[S3].projected_operation_counts_if_later_authorized.forward_passes_per_item = 1`
- `interface_profiles[S3].projected_operation_counts_if_later_authorized.note`
- `operation_boundaries.projected_future_operations.per_role_per_surface.S3_sequence_scorings = 9728`

Findings: `S3MR-012`.

### `CI-12` - CONFIRMED_NONBLOCKING

Checkpoint role records name Gate I1 after I1 was split into I1a and I1b.

**Rationale.** Confirmed stale labelling. Non-blocking, with the qualification that it leaves the applicable component set ambiguous for the content-only profiles to which I1b does not apply, which is the same ambiguity checklist item 3 identifies at the family level.

Files and exact field names:

- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `checkpoint_roles[1].gate_role = Gate I1`
- `checkpoint_roles[2].gate_role = Gates I1, I2, I3, I5`
- `checkpoint_roles[3].gate_role = Gates I1, I2, I3`
- `checkpoint_roles[4].gate_role = Gates I1, I2, I3`

Findings: `S3MR-018`.

### `CI-13` - QUALIFIED

The Clopper-Pearson bounds and the label-uniformity bands are described as one-sided at simultaneous_alpha but are computed at half that level in each tail.

**Rationale.** Qualified rather than confirmed as an error because the reviewer reproduced all fifteen committed quantities exactly under one coherent convention - a two-sided interval placing alpha/2 in each tail - which is the standard and defensible convention for a symmetry band and a descriptive interval. Nothing is arithmetically wrong; the field name and the surrounding prose describe a different convention from the one implemented. The required change is naming and documentation only, and no number changes.

Files and exact field names:

- `studies/study3/analysis/design_statistics.py`
- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`
- `design_statistics.py line 467: simultaneous_alpha`
- `all twelve descriptive Clopper-Pearson rows`
- `all three label-uniformity acceptance bands`

Findings: `S3MR-019`.

### `CI-14` - CONFIRMED_NONBLOCKING

The positive-reference dossier attributes the positive-reference obligation to defect D-07, while the authoritative record assigns that obligation to D-04.

**Rationale.** Confirmed by direct comparison of the two records. Non-blocking because it is a traceability error that changes no statistical content, but it should be corrected because the dossier is what a later OD2 authority would read.

Files and exact field names:

- `studies/study3/references/positive_reference_dossier.md`
- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `positive_reference_dossier.md lines 17 and 193: D-07`
- `operator_review_v0_1.defects: D-07 = pooling could mask a failed cell`
- `operator_review_v0_1.defects: D-04 = positive-reference circularity and a chance-level floor that is not a capability floor`

Findings: `S3MR-020`.

### `CI-15` - QUALIFIED

The draft cites Hsueh, Liu and Chen (2001) for unconditional exact paired equivalence testing while implementing Tango's (1998) asymptotic score procedure.

**Rationale.** Qualified, not confirmed as a citation error. Both citations were verified independently against NCBI esummary and both are accurate in author list, journal, volume, pages and year, and both are genuinely relevant. What the draft does not disclose is that the cited exact procedure is not the procedure implemented: Hsueh, Liu and Chen describe an unconditional exact test that would be conservative by construction, whereas the implemented rule is Tango's asymptotic score statistic whose realised level is enumerated but not bounded. The defect is an omission of that distinction, and it is the same omission that produces finding S3MR-004; the citations themselves are sound and the unconditional exact procedure is in fact one of the admissible remedies.

Files and exact field names:

- `studies/study3/references/methods_sources.md`
- `studies/study3/protocol/interface_calibration_protocol_draft.json`
- `methods_sources.md: Hsueh, Liu and Chen (2001), Biometrics 57:478-483, PMID 11414572`
- `methods_sources.md: Tango (1998), Statistics in Medicine 17:891-908, PMID 9595618`

Findings: `S3MR-004`, `S3MR-005`.

### `CI-16` - CONFIRMED_BLOCKING

The I3 primary floor appears as both 0.90 and 0.95 across the packet tables and the drafting derivation tables without a resolution.

**Rationale.** Confirmed and blocking. A gate cannot have two floors, and the choice is not cosmetic: at p0 0.90 the gate is reachable at n 256 with power 0.953040775, while at p0 0.95 against the draft's own lowest declared alternative 0.97 no admissible n up to 768 reaches 0.90 power. The draft therefore contains a gate that is either underdetermined or infeasible, and the reviewer may not resolve it by moving the alternative to fit a preferred sample size.

Files and exact field names:

- `studies/study3/analysis/independent_methods_review_packet.md`
- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_recalculation_tables.json`
- `independent_methods_review_packet.md lines 84-97: null stated as p <= 0.9 above a table whose last four rows are computed at p0 0.95`
- `reviewed_parameter_recommendations: gate I3_primary_consistency_p0_095, recommended_n null`

Findings: `S3MR-006`, `S3MR-007`.

### `CI-17` - CONFIRMED_NONBLOCKING

The drafting tables record that I1a and I1b do not meet the target power at the lowest declared alternative while the packet presents n 192 as a proposed operating size.

**Rationale.** Confirmed: the draft discloses the shortfall and proposes the size anyway. Non-blocking because it is fully disclosed and mechanically repairable by raising n - the reviewer supplies the smallest admissible sizes - rather than by redesigning anything. It is nevertheless a required change, since running a conjunctive family at 0.874 component power is not an acceptable operating point at the draft's own declared target.

Files and exact field names:

- `studies/study3/analysis/design_statistics_tables.json`
- `studies/study3/analysis/independent_methods_review_packet.md`
- `meets_target_power_0_90_at_lowest_alternative = false at n 128 and n 192`
- `packet section 2 gate table rows at n 192`

Findings: `S3MR-008`.

## Mandatory audit targets

Every target in section 5 of the controlling authority is answered below, in order.

### 5.1 Cross-artifact semantic consistency

#### Mandatory adjudications

**Dispositions operationally distinguishable.** Yes, and this review is a worked demonstration. The reviewer supplies candidate values for several parameters the draft omits - sample sizes, rejection counts, powers, a calibrated critical value, a decomposed projection - and nevertheless does not accept, because supplying values is not the same as the specification already sufficing, and because the repair of the I3 estimand would require inventing design structure that does not exist. Recorded as CI-08, NOT_CONFIRMED.

**Enumeration contradiction.** Yes, a direct contradiction. The JSON asserts under gate_hierarchy I3.secondary_criterion.verified_before_use that exact enumeration shows the realised type-I error does not exceed the nominal one-sided level; the packet and the methods ledger of the same draft disclose 0.025501 against nominal 0.025. Independent enumeration reproduces the disclosed value as 0.025501092 at n 192 and margin 0.10, so the drafting arithmetic is correct and the assertion built on it is false. It invalidates acceptance as specified, because a verification field in the authoritative artifact asserts the opposite of the draft's own disclosure and that field is what a later freeze authority would rely on. Recorded as CI-03, CONFIRMED_BLOCKING, finding S3MR-004.

**Every gate bearing hypothesis stated in packet section 2.** No. Label-selection uniformity IS stated at packet section 2 lines 109 to 112, so that part of the target is satisfied. The confirmation gate I5 has no null, no alternative, no n, no alpha and no rejection rule anywhere in section 2 - it appears only as a prose question at line 62, as a fail-closed route at line 132 and as a column in the profile table at lines 148 to 151. The development profile-selection rule is likewise absent. Recorded as CI-06, CONFIRMED_NONBLOCKING, finding S3MR-017.

**I3 indicator same estimand.** No. The JSON and the Markdown define the primary indicator as the answer being identical across every applicable transformed variant; the packet defines it as every counterbalanced variant being scored correct. These are different estimands. Recorded as CI-01, CONFIRMED_BLOCKING, finding S3MR-002.

**Sample size symbol units.** No symbol carries a declared unit in any artifact, and n denotes at least three different quantities: base items per atomic cell in the gate tables, a divisibility-constrained count in the counterbalancing discussion, and scored rows in the projection totals. For the label-bearing profile these differ by a factor of up to 96. Recorded as CI-07, CONFIRMED_NONBLOCKING, finding S3MR-014. The reviewer's own tables declare a unit on every parameter row precisely because the draft does not.

**Stable but wrong answer.** A base item on which the interface returns the same wrong answer under every applicable variant scores 1 under the JSON and Markdown definition and 0 under the packet definition. The two definitions therefore disagree on precisely the case an interface calibration exists to detect, and neither definition alone is adequate: the identical-answer form admits stable incompetence, and the scored-correct form cannot separate a presentation artefact from an incapacity. Recorded as CI-02, CONFIRMED_BLOCKING. The reviewer does not choose between them; the required change is to publish both indicators and their explicit conjunction.

**Method.** Field-by-field reading of the authoritative JSON with targeted cross-file searches on every gate name, every hypothesis symbol, every alpha value, every sample size, every stratum identifier and every operator-decision identifier. Seventeen candidate inconsistencies were carried into the adjudication table, each with exactly one status.

**Outcome.** Seventeen candidate inconsistencies adjudicated: six CONFIRMED_BLOCKING, eight CONFIRMED_NONBLOCKING, one NOT_CONFIRMED, two QUALIFIED.

**Scope.** Every decision-bearing statement in the authoritative protocol JSON was compared against the companion Markdown, the protocol schema, the independent methods review packet, the drafting derivation script and its tables, the study README, the positive-reference dossier, the v0.1 operator review, the design receipt, the traceability note and the thread handoff.

### 5.2 Estimands, atomic cells, and pooling

**Base item is the independent unit.** The draft's arithmetic treats the base item as the independent unit and that is the right choice, because repeated presentations of one base item are neither independent nor exchangeable with presentations of different base items. But the choice is not stated anywhere as an assumption, and the published construction assigns exactly one position-symbol pair per base item, which contradicts the existence of repeated presentations of the same base item at all. The unit is therefore correct in intent and unsupported by the published construction. This is the core of blocking finding S3MR-001.

**Conjunctive roles and null family.** The conjunctive treatment of the checkpoint roles is correct for the future claim, because the claim is that the interface is adequate for every role that will bear a target, and an interface adequate for two of three roles does not support it. The null family does match that logic for the roles: an intersection-union structure over roles is the correct formalisation of a conjunctive claim and needs no alpha adjustment across the conjuncts. The mismatch is elsewhere - the same intersection-union reasoning is applied within a profile at alpha 0.005 per component while the study claims a per-profile level of 0.001666666667, which is where finding S3MR-003 arises.

**Factor separation.** Operation family, depth, rendering, label set, label position, role, profile and split are separated at defensible levels, and the reviewer found no undefined cell arising from the separation itself. Two defects arise from the interaction of separation with applicability. Label set and label position are undefined for the content-only profiles, which is correct, but the checkpoint role records still name an undivided Gate I1 and therefore leave the applicable component set ambiguous for exactly those profiles - finding S3MR-018. And S3's cells are defined only conditionally on an activation condition that is not met, so the S3 stratum is presently an empty cell that nonetheless occupies a slot in the multiplicity denominator - finding S3MR-016.

**I3 invariance or correctness or both.** Both are required, and neither alone is adequate. Invariance alone admits a stably wrong answer; correctness under every variant conflates a presentation artefact with an incapacity, because an interface that is simply unable to do the task fails the indicator for reasons that have nothing to do with presentation. The reviewer's recommendation is that the draft publish two indicators - invariance of the chosen content across applicable variants, and correctness under every applicable variant - together with their explicit conjunction, and register which one carries gate authority. The draft currently overloads a single indicator and defines it two different ways in two different files.

**Not applicable never converted.** The draft states the prohibition explicitly and states it well: not_applicable may not become a pass, a zero effect, a denominator entry, or a post-data reduction in a multiplicity denominator. The reviewer confirms the first three are closed by the published rules. The fourth is not closed in practice, because S3's conditional selectability creates a route by which a not-applicable profile reduces the Bonferroni denominator from three to two after the development split is scored. The prohibition is correctly written and incompletely enforced.

**Six pooling prohibitions close every rescue path.** The six registered prohibitions are well drawn and close the obvious paths: no pooling across profiles, roles, strata, renderings, label sets or splits to rescue a failed cell. Three residual paths remain open and are recorded as required changes rather than edits. First, pooling across the two label alphabets within one profile is not named, and the alphabets are the very factor the counterbalancing exists to separate. Second, pooling across position-symbol cells within one alphabet is not named. Third, and most consequential, the prohibitions govern pooling but not the multiplicity denominator: nothing forbids the Family B denominator from shrinking from three to two if S3's selectability condition fails, which is the same rescue achieved by arithmetic rather than by pooling. See finding S3MR-016.

**Two indicators and conjunction.** Required change, stated rather than adopted. The reviewer specifies: J_inv(b) = 1 when the extracted answer is byte-identical across every applicable transformed variant of base item b; J_cor(b) = 1 when every applicable transformed variant of b is scored correct; J_both(b) = J_inv(b) AND J_cor(b). Note that J_cor implies J_inv only when the correct answer is itself invariant under the transformation, which is the design's intent but is a property of the construction and must be stated, not assumed.

**Variants per profile materially different.** Yes, materially. The label-bearing construction crosses 16 position-symbol cells by 2 label alphabets by 3 renderings, giving 96 applicable variants per base item, while the content-only profiles S2 and S3 have 3. An all-variants conjunction over 96 draws is a far more severe indicator than the same conjunction over 3: under an independent-draw idealisation with per-variant success 0.99 the base-item indicator has expectation 0.38 at 96 variants and 0.97 at 3. Comparing profiles on a single threshold applied to indicators of such different severity is not a like-for-like comparison, and the draft applies one I3 threshold table across profiles. This is a required change independent of the blocking identifiability defect.

### 5.3 Multiplicity and selection

**Development and confirmation error roles specified separately.** Currently they are not. The draft applies one alpha statement to both. The required change is to specify both: a development screening level chosen for its operating characteristics, and a confirmation level that carries the inferential guarantee for the single selected profile. Absent that separation the study cannot say what its alpha 0.005 protects.

**Does development need familywise control.** Not for the scientific claim, if that claim is made only on an independent one-shot confirmation bank. The development screen's error role is operational: a false positive there costs a wasted confirmation split and a false negative discards a usable interface. That is a decision-theoretic cost, not an inferential one. Applying confirmatory family-wise control to development is not wrong, but it is not required by the claim, and the draft's single alpha statement obscures which role it is playing. The reviewer's recommendation is to state a screening error budget for development, justified by the cost of a spent confirmation split, and a separate confirmatory alpha for the confirmation split, rather than one alpha statement covering both.

**Family a intersection union validity.** Valid in form, and the correct structure for the profile claim. An intersection-union test of a conjunctive claim rejects only when every component rejects, and its size is bounded by the maximum component level with no adjustment needed across components. The draft's use of it is sound. The defect is that the level actually implemented in every component is 0.005, so each profile is tested at 0.005 and not at the stated 0.001666666667.

**Family b bonferroni implemented.** No. Shown mathematically rather than asserted. Let A denote the per-component level. Family A is an intersection-union test, so P(reject profile j | H0j) is bounded by A. Family B takes the union over the selectable profiles, so P(any profile rejects | global null) is bounded by 3A. With A = 0.005 as implemented in every committed component rule, the bound is 0.015, which is three times the stated study alpha of 0.005. To achieve the stated per-profile level of 0.001666666667 every component rule must be computed at that level, which no committed table is. The independent recomputation demonstrates the difference is real and not notional: at n 192 the exact rejection count moves from 184 to 185 for I1a and I1b, from 115 to 117 for I2, and from 168 to 170 for I4. Recorded as a required change, finding S3MR-003.

**Multiplicity decision graph.** Returned in full under the multiplicity_decision_graph key of this document, in executable step form.

**S3 in the selection denominator.** The rule is not fixed and must be. S3 is registered conditionally_selectable, its activation condition is not met, and the draft records that on a single-token answer domain its selection rule reduces to S2's. The denominator therefore depends on a fact that will not be known until the development split has been scored, which is exactly the post-data denominator reduction the draft's own prohibition forbids. The reviewer's recommendation, stated as a required change and not adopted, is to fix the denominator at three before any data - the conservative choice, and legitimate precisely because it is registered in advance. Finding S3MR-016.

**S4 excluded from every success union.** Yes, and correctly. S4 is registered never_selectable and does not appear in any success union or in the Family B denominator, while still receiving diagnostic checks. The reviewer verified that no gate outcome on S4 can promote it to selection and that its diagnostic rows carry no selection authority. The one caution recorded is arithmetic rather than inferential: S4 nevertheless contributes 258048 scored rows to the reviewer's independent projection, which is a third of the projected total, so it is expensive diagnostics rather than a free check.

### 5.4 Exact-binomial gates and power

**Counterbalancing divisor.** An n is admissible when it is a multiple of 32, which is the least common multiple of the label-bearing divisor 32 - itself 16 position-symbol cells by 2 label alphabets - and the minimum balance divisor 16, and is compatible with the 3 renderings at the base-item level. The reviewed grid is the 24 multiples of 32 from 32 to 768.

**Discreteness accounted for.** Yes, and it is not a formality. Exact-binomial power is not monotone in n across a rejection-count change, so the reviewer searched the whole admissible grid rather than reporting the first n that passes, and records both the smallest admissible n reaching the target and the smallest admissible n that holds it for every larger admissible size. The draft examined only 128, 192, 256 and 384.

**Independent reproduction.** Exact upper tails, rejection counts and power were re-derived for I1a, I1b, I2, I3 primary at both candidate floors, and I4, across the full admissible n grid at both alpha 0.005 and alpha 0.001666666667. The implementation uses a regularised-incomplete-beta tail with an independently validated continued-fraction evaluation, structurally unrelated to the drafting script, and was validated against closed forms before any comparison: the all-successes tail, the at-least-one tail, the symmetry identity at p = 0.5 which returns exactly zero, and a beta-binomial identity agreeing to 3.34e-14.

**Is 0 87425 acceptable.** No. Running a conjunctive family at 0.874 component power against the design's own lowest declared alternative discards roughly one qualifying interface in eight per component, and the shortfall compounds across the conjunction. The drafting tables themselves record meets_target_power_0_90_at_lowest_alternative as false at both n 128 and n 192, so the draft discloses the shortfall and proposes the size anyway. The smallest admissible n meeting the reviewed target is 224 at alpha 0.005 and 256 at the corrected Family B alpha; the reviewer recommends 256 so that one size serves both alpha regimes. Finding S3MR-008.

**Parameters defined per gate and split.** Returned in full under the reviewed_gate_parameters key, one row per gate with p0, p1, alpha, alpha basis, target power, recommended n, rejection count, exact null tail, exact power, the unit of n, the applicable splits and the substantive justification for p0 and p1.

**Recomputation at the corrected alpha.** Every affected threshold and sample size was recomputed at 0.001666666667 and is reported at that level in the reviewed parameter table, with the alpha_basis field on every row recording which level the row is computed at. No table computed at 0.005 is presented as evidence of control at 0.001666666667.

**Substantive justification of p0 and p1.** Every p0 is taken from the draft's own registered floor and every p1 from the draft's own lowest declared alternative. The reviewer deliberately did not choose either, because choosing a floor or widening a margin to make a preferred sample size pass is the specific failure the authority prohibits. Where the draft's own pair is infeasible - I3 primary at p0 0.95 against p1 0.97 - the reviewer reports infeasibility rather than moving p1.

### 5.5 I3 robustness and paired equivalence

**Estimand resolved first.** It could not be resolved, and that is the finding. The I3 primary estimand is not identifiable from the published construction - the indicator quantifies over applicable variants of a base item while the construction assigns exactly one position-symbol pair per base item, and no variants-per-base-item field exists in any artifact - and it is defined two incompatible ways across the JSON, the Markdown and the packet. The reviewer therefore reviewed the threshold machinery conditionally and reports that the threshold cannot be registered until the estimand is published. Findings S3MR-001 and S3MR-002.

**Exact enumeration language.** The reviewer records the misuse explicitly. Enumerating the exact null distribution of an asymptotic statistic measures its realised level; it does not make the rule exact and does not make it conservative. The draft's verified_before_use text uses the enumeration as if it established conservativeness, and the same draft's disclosure of 0.025501 refutes that reading. Finding S3MR-004.

**Grid versus size control.** The four discordance values are a sensitivity grid. Under the null boundary the nuisance parameter q ranges over the closed interval from 0 to (1 - margin)/2, so total discordance ranges over the whole interval from the margin to 1, and the registered grid spans at most its lower third. A finite grid bounds a supremum only from below. The reviewer supplied the first of the four admissible remedies - a justified nuisance maximisation over the feasible null boundary - and found an exceedance the grid cannot see.

**I3 sample size recommendation.** The current information cannot justify one for the primary criterion. The primary estimand is not identifiable and its floor is unresolved between 0.90 and 0.95, and at 0.95 against the draft's own lowest alternative no admissible n up to 768 reaches 0.90 power. The reviewer therefore returns a conditional recommendation only: n 256 with rejection count 244 and power 0.953040775 if and only if the floor is registered at 0.90 and the estimand is published; no recommendation at 0.95. For the paired secondary criterion the reviewer returns the calibrated critical values above rather than a sample size, because a sample size for an uncalibrated rule would be meaningless.

**Is the exceedance acceptable.** No. Two exceedances are now established where the draft discloses one. At n 192 and margin 0.10 the supremum is 0.025501 at discordance 0.10, matching the disclosure to nine decimals. At n 384 and margin 0.10 the supremum is 0.025073 at discordance 0.4782, while the drafting grid maximum at that configuration is 0.024727 and reports compliance. The second case is decisive because it is a configuration the design proposes to use and the registered search was structurally incapable of finding it. The reviewer returns the corrected rule: a conservative critical value calibrated over the full feasible boundary, z = 1.97269 at n 192 giving supremum 0.023988, and z = 1.961978 at n 384 giving supremum 0.024905, with calibration_required true in both cases and the resulting power reported at the calibrated value rather than at the nominal one.

**Margin justification.** The registered margins 0.05 and 0.10 are not accompanied by any statement of what presentation effect is considered practically irrelevant. A margin without such a statement is a free parameter, and the reviewer specifically did not widen it to make any sample size pass. Required change: state the practical-irrelevance criterion that fixes the margin, before any data.

**Maximisation registration.** The optimisation is fully registered in the recalculation tables: domain is the closed feasible null-boundary interval for q; a uniform grid of max(64, 2n) points is followed by golden-section refinement on the bracketing triple around the grid argmax; tolerance 1e-9 on the nuisance coordinate; on convergence failure the procedure falls back to the grid maximum and sets a recorded flag rather than reporting a refined value; and the whole procedure is independently validated by exhaustive lattice enumeration whose windowed and exhaustive totals agree to 0.0 with total lattice mass agreeing to 8.37e-14.

**Non significance is not equivalence.** Confirmed as a reviewed principle. The draft does use an equivalence formulation rather than a failure to reject a difference, which is correct, and the reviewer records that the draft gets this right.

**Status of aggregate paired equivalence.** Secondary inferential status at most, and on the present evidence descriptive status only. The reviewer's determination is that it must not carry gate authority in its current form, for three independent reasons: its realised level exceeds the nominal level at two configurations including one the design proposes to use; its critical value is not calibrated over the registered nuisance domain; and its margin is not derived from a stated practical-irrelevance criterion.

**Tango rule reproduced.** Yes, independently. Under the null boundary with delta = d0, writing p21 = q and p12 = q + d0, the constrained maximum-likelihood nuisance estimate solves 2n q^2 - [(n12 + n21) - d0 (2n - n12 + n21)] q - n21 d0 (1 - d0) = 0 and is the larger root; the null variance is n [2q + d0(1 - d0)] and the statistic is (n12 - n21 - n d0) divided by its square root. The re-derivation was validated by four independent checks before any comparison with the drafting numbers: reduction to McNemar at d0 = 0 agreeing to 0.0, quadratic residual 6.01e-17, score-equation residual 1.53e-14, and a boundary census of 2778 interior and 122 boundary solutions with zero infeasible.

### 5.6 I4 and the positive reference

**Circularity check.** The draft's positive-reference dossier recognises the circularity risk and states bank isolation, which is the right instinct. Two gaps remain. The dossier does not state that the qualification interface must be external to the candidate panel, only that the banks differ, so a candidate interface could in principle serve as the qualification interface and validate itself. And the dossier attributes its own obligation to defect D-07 when the authoritative record assigns the circularity and chance-floor issue to D-04, which sends a later reader to the wrong prior finding - finding S3MR-020.

**Competence floor and alternative.** The generic floor p0 0.80 is reviewed as substantively defensible for a competence floor on the registered K4 construct: it is well above any chance level for the answer domain and it is not so high as to be unreachable by a genuinely capable checkpoint. The draft's predeclared alternative p1 0.90 is likewise defensible as the smallest competence level worth distinguishing. The reviewer adopts the draft's own pair rather than proposing its own, and reports that at the corrected Family B alpha the smallest admissible n reaching 0.90 power is 256 with rejection count 224 and exact power 0.921084.

**Fields a later od2 authority must freeze.** Enumerated as a methods recommendation and not adopted here: the qualification floor and its justification; the predeclared alternative p1; the alpha and its multiplicity basis across operation families and depths; n and its unit; the exact rejection count; the family and depth treatment including whether I4 is one decision or many; the stopping rule, which must forbid extending the bank after seeing outcomes; and the bank-isolation rule naming the qualification bank, the I4 bank and every Study 3 development and confirmation bank as mutually disjoint.

**Is p above 0 80 sufficient for the capability claim.** No, not by itself. Passing a floor of 0.80 through a candidate interface establishes that the checkpoint is not incapable through that interface; it does not establish that the checkpoint is capable on the registered K4 construct independently of the interface, because a single measurement through one interface cannot separate checkpoint capability from interface adequacy. That separation is exactly what the prequalification step exists to provide, which is why the two must remain distinct.

**Od2 untouched.** No checkpoint was selected, named as preferred, pinned, downloaded, tokenized, loaded, run, prequalified or substituted. Neither Qwen3-4B-Instruct-2507 nor Qwen2.5-Math-7B-Instruct nor any other model was chosen. Candidate identity, immutable revision, runtime, dtype and wrappers remain entirely with the operator.

**Sample size and alpha per family and depth.** The draft states I4 thresholds but does not state a multiplicity treatment across operation families and depths. If I4 is evaluated separately per family and depth, the number of I4 decisions is the product of families and depths and the per-decision level must reflect that; if it is evaluated once on a pooled bank, the pooling must be registered and it interacts with the pooling prohibitions. Neither is stated. Recorded as a required change within finding S3MR-017's family of specification gaps.

**Separation of prequalification and i4.** The reviewer's determination, stated as a methods requirement: P3-Q prequalification establishes through an external canonical qualification interface, on a bank isolated from every Study 3 bank, that the checkpoint is capable on the construct. I4 then establishes that the already-qualified checkpoint succeeds through each candidate Study 3 interface. The first is a property of the checkpoint; the second is a property of the interface conditional on the checkpoint. They may not share a bank, a model observation, or a candidate-panel outcome, and neither may be inferred from the other.

### 5.7 Confirmation and one-shot lifecycle

**Confirmation error spends the split.** The draft states this and states it correctly: a confirmation error or ambiguity spends the split and cannot be retried. The reviewer confirms the rule is unambiguous and adds one required strengthening - the rule must also cover the case where the confirmation run is technically incomplete, so that an infrastructure failure cannot become a licence to re-run.

**Confirmation n alpha thresholds multiplicity.** Absent from the draft; the reviewer states what must be published rather than supplying binding values for a gate whose estimand is unresolved. Required: n and its unit for each confirmed construct; the confirmation alpha and whether it is the study alpha or a separate confirmatory level; the exact rejection count for each construct at that alpha; and the multiplicity treatment across the conjuncts, which under an intersection-union reading needs no adjustment but must be stated as such rather than assumed. The reviewer notes that if the confirmation conjunction is evaluated at the same component level as development, the confirmation level is the maximum component level and not their product.

**Confirmation pass creates no mechanistic authority.** Confirmed and endorsed. A confirmation pass creates interface-calibration evidence only: it licenses the statement that the selected interface is adequate for the registered constructs and roles, and it licenses no mechanistic, representational or causal claim whatsoever. The reviewer records that the draft's claim ceiling on this point is correctly drawn and should be preserved verbatim through any amendment.

**No confirmation result can reselect.** Confirmed. The draft forbids a confirmation outcome from selecting a different interface, and the reviewer found no route by which a failed confirmation could promote another profile. This is one of the draft's better-specified boundaries.

**One profile confirmation without across profile correction.** Permitted, under conditions that must be registered in advance. The conditions are: the development bank and the confirmation bank are disjoint and neither is reused; the selection rule that maps development outcomes to a single profile is fixed before any data, including its tie-breaking; exactly one profile enters confirmation and the choice cannot be revisited after confirmation outcomes are seen; and the inferential claim is stated conditionally on the selected profile rather than as an unconditional claim about the best profile. Under those conditions the confirmation error rate is the nominal one for the selected profile. The draft satisfies none of them in published form, because the selection rule itself is unpublished - finding S3MR-017.

**What i5 confirms.** The reviewer's specification, stated as a required change because the draft contains none: I5 confirms, for the single development-selected profile and on the independent one-shot confirmation bank, every gate-bearing construct that profile carries - I1a, I1b where applicable, I2, I3 primary and, where the positive reference is in scope, the RP/I4/K4 construct - as a conjunction. A confirmation pass is a pass of the conjunction, not of a majority or of a best subset.

### 5.8 Feasibility and operation accounting

**Discrepancies against the draft.** Three are recorded. The draft's projection multiplies every surface by four roles, which charges the positive reference for gates it does not carry and charges the target roles for the positive-reference bank; the draft budgets 9728 S3 sequence scorings against its own record of one forward pass per item and its own warning not to budget four; and the draft publishes a single undifferentiated development total that cannot be decomposed into the streams a feasibility judgement needs. Findings S3MR-012 and S3MR-013.

**Distinctions made.** Base items per atomic cell; derived presentation variants per base item, which is 96 for the label-bearing profiles and 3 for the content-only profiles; rows scored per role, profile, stratum, family, depth, rendering and split; positive-reference prequalification work; positive-reference I4 work; target development work; selected-profile confirmation work; and S4 diagnostic work.

**Planning not authorization.** The table is planning arithmetic. It authorizes nothing, and no cost figure in it was used to weaken any required scientific contrast. Where the reviewer's corrections increase projected work - for example by raising I1a and I1b to n 256 - the increase is reported and the contrast is not weakened to avoid it.

**Table returned.** A model-free projected cell and operation table is returned under the projected_cells_and_operations key of the independent recalculation tables and reproduced under the projected_work key of this document.

**Totals.** Development 269568 scored rows, confirmation 258048, positive-reference I4 24576, S4 diagnostic 258048, total 810240 scored rows. Total forward passes zero and total generations zero in this round, and every executed-operation counter is zero.

## Estimand decisions

#### Atomic cell

**Definition in draft.** atomic_evaluation_cells with a cluster rule presupposing a cluster of applicable variants per base item

**Reviewer determination.** The cell definition and the construction algorithm are mutually inconsistent, which is the same defect viewed from the cell side rather than the indicator side. Resolving it changes the atomic cell, and therefore the unit of n, every gate threshold, and the whole projection - which is why the repair is a redesign rather than an amendment.

#### I3 primary

**Cross profile severity.** 96 applicable variants for S1 and S4 against 3 for S2 and S3; an all-variants conjunction is materially more severe at 96 and a single shared threshold is not a like-for-like comparison

**Identifiability defect.** The indicator quantifies over the applicable transformed variants of a base item, but counterbalancing_design.construction_algorithm.steps[4] assigns exactly one (position, symbol) pair to each base item, and no field stating the number of applicable derived variants per base item exists in the protocol JSON, the Markdown, the schema, the packet, the drafting script or its tables.

**Independent unit.** the base item, correctly, but unsupported by a construction that assigns one presentation per base item

**Published definitions.**

- authoritative JSON, gate_hierarchy I3.primary_indicator: the answer is identical across every applicable transformed variant
- companion Markdown line 503: identical wording
- review packet section 2 line 85: every counterbalanced variant of that base item is scored correct

##### Required indicators

**J both.** the explicit conjunction of J_inv and J_cor

**J cor.** 1 when every applicable transformed variant of the base item is scored correct

**J inv.** 1 when the extracted answer is byte-identical across every applicable transformed variant of the base item

**Reviewer determination.** Not identifiable from the published construction, and defined two incompatible ways across the artifacts.

**Stable but wrong answer.** passes J_inv, fails J_cor; passes the JSON and Markdown definition, fails the packet definition

**Status.** BLOCKING, findings S3MR-001 and S3MR-002

#### Pooling

**Closed.** pooling across profiles, roles, strata, renderings, label sets and splits to rescue a failed cell

**Recorded as.** required changes, not edits to the draft

**Registered prohibitions reviewed.** 6

**Residual paths.**

- pooling across the two label alphabets within one profile is not named
- pooling across position-symbol cells within one alphabet is not named
- the multiplicity denominator can shrink from three to two post-data when S3's activation condition fails, which achieves a rescue by arithmetic rather than by pooling

#### Units

**Defect.** no artifact declares a unit for any sample-size symbol

**Observed meanings.**

- base items per atomic cell, in the packet gate tables
- a divisibility-constrained presentation count, in the counterbalancing discussion
- scored rows, in the projection totals

**Reviewer practice.** every parameter row published by this review carries an explicit unit_of_n field

**Status.** MAJOR, finding S3MR-014

## Multiplicity and selection

### Formal null and alternative sets

#### all retained roles families depths renderings

**Alternative.** the intersection of the component alternatives

**Null.** the global null is the intersection over every retained role, family, depth and rendering of the corresponding component nulls; adequacy is claimed only if every retained combination rejects its component null

**Size.** bounded by the number of selectable profiles times the maximum component level

**Structure.** a nested intersection-union: conjunctive within a profile across roles, families, depths and renderings, and a union across selectable profiles at the Family B level

#### conjunction of cells within one profile

**Alternative.** H1(profile j) = intersection over c in C(j) of {pi_jc > p0_c}

**Note.** the union null and intersection alternative are the correct orientation for a conjunctive claim; the draft has this right

**Null.** H0(profile j) = union over components c in C(j) of H0jc, where H0jc states that component c of profile j fails its registered floor: for a binomial component, pi_jc <= p0_c

**Size.** bounded by A, with no adjustment across components

**Test.** intersection-union: reject H0(profile j) only if every component test rejects at level A

#### development selection

**Null.** not a hypothesis test; selection is a decision rule mapping development outcomes to at most one profile

**Requirement.** the map, including tie-breaking and the behaviour when no profile passes, must be fixed before any data

**Status.** unpublished in the draft, finding S3MR-017

#### label uniformity nuisance check

**Alternative.** H1(U) = it is not uniform

**Note.** the bands are computed with half of simultaneous_alpha in each tail, which is defensible and mislabelled - CI-13, QUALIFIED

**Null.** H0(U) = the label-selection distribution is uniform over the registered label positions

**Test.** two-sided acceptance band; a nuisance check with no gate authority, correctly

#### positive reference cells

**Alternative.** pi_RP,f,d > 0.80, with the predeclared alternative of interest at 0.90

**Gap.** the multiplicity treatment across families f and depths d is unstated

**Null.** H0(I4, family f, depth d) = pi_RP,f,d <= 0.80 on the registered K4 construct through the candidate interface

**Test.** exact binomial upper-tail

#### single selected confirmation profile

**Alternative.** intersection over c of {pi_jc* > p0_c} on the confirmation bank

**Null.** H0(C) = union over components c in C(j*) of {pi_jc* <= p0_c} evaluated on the independent confirmation bank, where j* is the development-selected profile

**Status.** n, alpha and rejection counts unpublished

**Test.** intersection-union at the confirmation level, no across-profile correction, valid under the registered conditions listed in the confirmation section

#### union over selectable profiles

**Alternative.** H1(B) = union over selectable profiles j of H1(profile j)

**Note.** with A = 0.005 as implemented and a denominator of 3, the bound is 0.015 and not the stated 0.005

**Null.** H0(B) = intersection over selectable profiles j of H0(profile j), that is, no selectable profile is adequate

**Size.** bounded by (number of selectable profiles) x A

**Test.** reject H0(B) if any profile rejects; Bonferroni over the registered denominator

### Adjudications

**Development and confirmation roles separated.** no

**Development needs confirmatory fwer.** not for the scientific claim; a separate screening error budget should be stated

**Family a valid.** yes

**Family b delivered bound.** 0.015

**Family b implemented.** no

**Family b stated study alpha.** 0.005

**S3 denominator fixed before data.** no

**S4 correctly excluded.** yes

### Executable multiplicity decision graph

Executable without interpretation. Every branch is decided before any data are observed. No step reads an outcome to decide a denominator.

**Step 1.** Fix the selectable profile set P before any data. Register its cardinality K = |P| as a number, not as a condition. S3 counts in K whether or not its activation condition is later met.

  - *on failure*: STOP: the multiplicity denominator is not registered and no error statement is available.

**Step 2.** Fix the study alpha S and set the per-profile level B = S / K.

  - *value in the draft*: S = 0.005, K = 3, B = 0.001666666667

**Step 3.** For each profile j in P, fix the component set C(j) from the registered applicability table, including the post-split I1a and I1b names and their applicability per profile.

  - *on failure*: STOP: component applicability is ambiguous; see finding S3MR-018.

**Step 4.** Compute every component rejection rule for profile j at level B, not at S. Family A is intersection-union, so the per-profile size is bounded by the maximum component level, which must therefore be B.

  - *check*: if any committed component table is computed at a level other than B, the Family B statement is unimplemented; this is the present state of the draft.

**Step 5.** Evaluate the development split. For each j, profile j passes development if and only if every component in C(j) rejects its component null at level B.

  - *note*: development error role is operational, not inferential; state its screening budget separately.

**Step 6.** Apply the pre-registered selection map to the development pass set to obtain at most one profile j*. The map, its tie-breaking, and its no-profile-passes branch are all fixed at step 0 and may not consult confirmation data.

  - *on failure*: STOP and fail closed: no confirmation is run, and no profile is selected.

**Step 7.** Evaluate the confirmation split for j* only, on the independent one-shot bank, as an intersection-union over C(j*) at the registered confirmation level.

  - *no across profile correction*: valid because exactly one profile enters confirmation under a rule fixed before any data, and the claim is stated conditionally on j*.

**Step 8.** A confirmation error, ambiguity or technically incomplete run spends the split. Do not retry, do not extend the bank, do not select a different profile.

  - *terminal*: yes

**Step 9.** S4 is evaluated diagnostically at every stage and enters no success union, no selection map and no multiplicity denominator at any step.

  - *terminal*: yes

**Step 10.** A confirmation pass licenses an interface-calibration claim conditional on j* and licenses no mechanistic authority.

  - *terminal*: yes

## Reviewed parameter table

**These are reviewer recommendations, not adopted protocol.** PROPOSED_REVIEW_PARAMETERS_NOT_ADOPTED_NOT_FROZEN. These are the reviewer's recommendations. They bind nothing, authorize nothing, and select nothing. Adoption is an operator act.

**Provenance.** Every row below is copied verbatim from studies/study3/analysis/independent_methods_recalculation_tables.json, key reviewed_parameter_recommendations, which was produced by the independent recalculation script under CPU-only Azure ACR against a clean exact-commit clone. No value in this section was computed by the assembly step.

**Alpha policy.** Rows are computed at the corrected Family B per-profile level 0.001666666667, not at the component level 0.005 that every committed drafting table uses. No table computed at 0.005 is offered here as evidence of control at 0.001666666667.

**p0 and p1 policy.** Every p0 is the draft's own registered floor and every p1 the draft's own lowest declared alternative. The reviewer chose neither, because choosing a floor or widening a margin so that a preferred sample size passes is exactly the failure this review exists to catch. Where the draft's own pair is infeasible the reviewer reports infeasibility rather than moving p1.

**Discreteness policy.** Exact-binomial power is not monotone in n across a rejection-count change, so the full admissible grid was searched rather than the four sizes the draft examined. An n is admissible when it is a multiple of 32, the least common multiple of the label-bearing divisor 32 and the minimum balance divisor 16; the reviewed grid is the 24 multiples of 32 from 32 to 768.

| Gate | Estimand | Unit of n | p0 or margin | p1 | alpha | n | Rejection rule | Power at p1 | Splits | Applicability | Authority status |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- | --- | --- |
| I1a_trivial_recovery | per-base-item probability that the interface recovers the answer that is explicitly bound in the prompt | base items per atomic cell | 0.9 | 0.97 | 0.001666666667 | 256 | reject the null and pass the gate when the observed success count is at least 244 out of 256 | 0.953040775 | development, confirmation | every interface profile; label-bearing and content-only | reviewer recommendation only; not adopted protocol and not an execution authority |
| I1b_symbol_binding | per-base-item probability that the interface binds the answer to the correct label symbol | base items per atomic cell | 0.9 | 0.97 | 0.001666666667 | 256 | reject the null and pass the gate when the observed success count is at least 244 out of 256 | 0.953040775 | development, confirmation | label-bearing profiles only; not applicable to S2 or S3, which display no label alphabet | reviewer recommendation only; not adopted protocol and not an execution authority |
| I2_primitive_headroom | per-base-item probability of a correct answer on the primitive stratum, against a four-option chance floor restated as 0.50 by the draft | base items per atomic cell | 0.5 | 0.7 | 0.001666666667 | 128 | reject the null and pass the gate when the observed success count is at least 82 out of 128 | 0.938986365 | development, confirmation | every interface profile | reviewer recommendation only; not adopted protocol and not an execution authority |
| I3_primary_consistency_p0_090 | per-base-item probability that the item satisfies the I3 primary indicator, under the 0.90 floor variant of the null that the authoritative JSON registers | base items per atomic cell | 0.9 | 0.97 | 0.001666666667 | 256 | reject the null and pass the gate when the observed success count is at least 244 out of 256 | 0.953040775 | development, confirmation | every interface profile, but the number of applicable variants per base item differs by profile | reviewer recommendation only; not adopted protocol and not an execution authority |
| I3_primary_consistency_p0_095 | the same indicator under the 0.95 floor variant of the null that the same committed table also registers | base items per atomic cell | 0.95 | 0.97 | 0.001666666667 | none | no admissible n at or below 768 reaches the target power at this p0 and p1 | none | development, confirmation | every interface profile; retained here only to show the consequence of the unresolved floor | reviewer recommendation only; not adopted protocol and not an execution authority |
| I4_competence_floor | per-base-item probability that the positive reference answers correctly on the registered K4 construct | base items per atomic cell | 0.8 | 0.9 | 0.001666666667 | 256 | reject the null and pass the gate when the observed success count is at least 224 out of 256 | 0.921083515 | development | the positive-reference role only; the checkpoint identity remains an operator decision | reviewer recommendation only; not adopted protocol and not an execution authority |
| I3 secondary, paired equivalence | aggregate paired equivalence of the correlated proportions | base items per atomic cell | margin 0.05 and 0.10 | n/a | nominal one-sided 0.025 | see calibration |  | see calibration table | development and confirmation | label-bearing and content-only | reviewer recommendation only; not adopted protocol and not an execution authority |

**Alternative justification, gate by gate.** Every p0 below is the draft's own registered floor and every p1 the draft's own lowest declared alternative. The reviewer chose neither.

- `I1a_trivial_recovery`: the drafting party's own lowest declared alternative for this gate; retained unchanged so the power verdict cannot be attributed to the reviewer moving the alternative
- `I1b_symbol_binding`: the drafting party's own lowest declared alternative for this gate; retained unchanged
- `I2_primitive_headroom`: the drafting party's own lowest declared alternative for this gate; retained unchanged
- `I3_primary_consistency_p0_090`: the drafting party's own lowest declared alternative for this gate; retained unchanged
- `I3_primary_consistency_p0_095`: the drafting party's own lowest declared alternative for this gate; retained unchanged
- `I4_competence_floor`: the drafting party's own lowest declared alternative for this gate; retained unchanged

### Paired equivalence: size over the feasible null boundary

The paired criterion is parameterised by an equivalence margin rather than by a null proportion p0, so it is reported separately rather than forced into the exact-binomial row shape. It is returned as a calibrated critical value and not as a sample size, because a sample size for a rule whose size is not controlled would be meaningless.

| margin | size supremum over feasible boundary | discordance at supremum | exceeds nominal one sided alpha |
| --- | --- | --- | --- |
| 0.05 | 0.016041371 | 0.059004 | no |
| 0.05 | 0.018880712 | 0.080336 | no |
| 0.05 | 0.022281167 | 0.101226 | no |
| 0.05 | 0.022963992 | 0.126046 | no |
| 0.1 | 0.023486529 | 0.1 | no |
| 0.1 | 0.025501092 | 0.1 | yes |
| 0.1 | 0.02477389 | 0.351428 | no |
| 0.1 | 0.025072683 | 0.478225 | yes |

### Paired equivalence: conservative critical-value calibration

| bisection iterations | calibrated critical value | calibration required | margin | n base items per atomic cell | nominal critical value | nominal one sided alpha | power at calibrated critical value | size supremum at calibrated critical value | size supremum at nominal critical value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 14 | 1.97269 | yes | 0.1 | 192 | 1.95996398454 | 0.025 | [{'discordance_rate': 0.05, 'exact_power': 0.998932004}, {'discordance_rate': 0.1, 'exact_power': 0.963392287}, {'discordance_rate': 0.2, 'exact_power': 0.71320166}, {'discordance_rate': 0.3, 'exact_power': 0.401986779}] | 0.023987562 | 0.025501092 |
| 14 | 1.961978 | yes | 0.1 | 384 | 1.95996398454 | 0.025 | [{'discordance_rate': 0.05, 'exact_power': 0.999999987}, {'discordance_rate': 0.1, 'exact_power': 0.999904121}, {'discordance_rate': 0.2, 'exact_power': 0.981367386}, {'discordance_rate': 0.3, 'exact_power': 0.89010201}] | 0.024905268 | 0.025072683 |

## Paired method decision

**Admissible remedies.**

- justified nuisance maximisation over the feasible null boundary, with the registration fields above
- a conservative critical value calibrated over the full registered domain, as returned here
- a conservative-by-construction exact procedure such as the unconditional exact test of Hsueh, Liu and Chen (2001), Biometrics 57:478-483, PMID 11414572
- leaving the method unresolved and returning a non-accepting disposition

**Agreement with the drafting enumeration.** The independent enumeration reproduces the drafting number at n 192 and margin 0.10 as 0.025501092 against the disclosed 0.025501. The drafting enumeration is therefore arithmetically correct. The defect is entirely in the claim made about it, not in the computation.

#### Closed form validations

**Boundary census.** 2778 interior solutions, 122 boundary solutions, 0 infeasible

**Lattice enumeration windowed vs exhaustive.** 0.0

**Mcnemar reduction at d0 zero.** 0.0

**Quadratic residual.** 6.01e-17

**Score equation residual.** 1.53e-14

**Standard normal quantile identity.** 6.66e-16

**Total lattice mass.** 8.37e-14

**Corrected rule returned.** Conservative critical values calibrated over the full feasible boundary: z = 1.97269 at n 192 and margin 0.10 giving supremum 0.023988; z = 1.961978 at n 384 and margin 0.10 giving supremum 0.024905. Both rows carry calibration_required true.

#### Independent rederivation

**Constrained mle equation.** 2 n q^2 - [(n12 + n21) - d0 (2 n - n12 + n21)] q - n21 d0 (1 - d0) = 0, larger root

**Feasible null boundary domain.** q in [0, (1 - margin)/2], equivalently total discordance 2q + margin in [margin, 1]

**Null variance.** n [2 q + d0 (1 - d0)]

**Source.** Tango (1998), Statistics in Medicine 17:891-908, PMID 9595618, re-derived from the primary source rather than from the drafting implementation

**Statistic.** (n12 - n21 - n d0) / sqrt(n [2 q + d0 (1 - d0)])

**Margin justification missing.** Neither 0.05 nor 0.10 is accompanied by a statement of the largest presentation effect considered practically irrelevant. The reviewer did not widen either margin.

#### Optimisation registration

**Convergence failure behaviour.** fall back to the grid maximum and set a recorded flag; never report a refined value that did not converge

**Domain.** closed feasible null-boundary interval for the nuisance parameter q

**Independent validation.** exhaustive lattice enumeration, windowed against exhaustive agreeing to 0.0 and total mass to 8.37e-14

**Refinement.** golden-section on the bracketing triple around the grid argmax

**Resolution.** uniform grid of max(64, 2n) points

**Tolerance.** 1e-09

**Rule as implemented by the draft.** Tango (1998) asymptotic score statistic for the paired difference of correlated proportions, one-sided at nominal 0.025, with the null nuisance parameter at its constrained maximum-likelihood value.

**Sample size recommendation.** None for the paired criterion. A sample size for an uncalibrated rule would be meaningless; the calibrated critical values are returned instead.

**Status determination.** Secondary inferential status at most; on present evidence descriptive only. It must not carry gate authority in its current form.

**Supremum over the full feasible boundary.** Reported row by row in the recalculation tables. Two configurations exceed the nominal one-sided 0.025: n 192 at margin 0.10 with supremum 0.025501 at discordance 0.1000, which the draft discloses; and n 384 at margin 0.10 with supremum 0.025073 at discordance 0.4782, which the draft does not disclose and whose grid maximum of 0.024727 reports compliance. All four margin-0.05 configurations and the remaining margin-0.10 configurations are within the nominal level.

**Why the second exceedance matters.** It is not a hypothetical. n 384 at margin 0.10 is a configuration the design proposes to use; the registered four-value grid spans at most the lower third of the feasible domain; and the argmax at 0.4782 lies far outside it. A finite grid bounds a supremum only from below, so the grid's compliance at that configuration is not evidence of anything.

## Positive-reference statistical requirements

**Circularity findings.**

- the dossier states bank isolation but does not require the qualification interface to be external to the candidate panel, so a candidate interface could in principle qualify the checkpoint that then validates it
- the dossier attributes its own obligation to defect D-07 while the authoritative record assigns the circularity and chance-floor issue to D-04 - finding S3MR-020

#### Competence floor

**Chosen by.** the draft, adopted rather than replaced by the reviewer

**P0.** 0.8

**Reviewed.** substantively defensible for the registered K4 construct

**Fields a later od2 authority must freeze.**

- qualification floor and its substantive justification
- predeclared alternative p1
- alpha and its multiplicity basis across operation families and depths
- n and its declared unit
- exact rejection count
- family and depth treatment, including whether I4 is one decision or many
- stopping rule, forbidding any bank extension after outcomes are seen
- bank isolation naming the qualification bank, the I4 bank and every Study 3 development and confirmation bank as mutually disjoint

**Is the floor sufficient for the capability claim.** No. Passing 0.80 through a candidate interface shows the checkpoint is not incapable through that interface; it cannot separate checkpoint capability from interface adequacy. That separation is the purpose of prequalification.

**Multiplicity across families and depths.** unstated in the draft; must be published as either a per-family-per-depth decision with a level reflecting the number of decisions, or a registered pooled evaluation whose pooling is reconciled with the pooling prohibitions

**Od2 state.** untouched; no checkpoint selected, named as preferred, pinned, downloaded, tokenized, loaded, run, prequalified or substituted

#### Predeclared alternative

**P1.** 0.9

**Reviewed.** defensible as the smallest competence level worth distinguishing

#### Reviewed sample size

**Alpha basis.** Family B per-profile alpha 0.001666666667

**Exact power at p1.** 0.921084

**N.** 256

**Rejection count.** 224

**Unit of n.** base items per atomic cell

#### Separation required

**I4.** establishes that the already-qualified checkpoint succeeds through each candidate Study 3 interface; a property of the interface conditional on the checkpoint

**P3 Q prequalification.** establishes capability on the construct through an external canonical qualification interface, on a bank isolated from every Study 3 bank; a property of the checkpoint

**Prohibition.** no shared bank, no shared model observation, no shared candidate-panel outcome; neither may be inferred from the other

## Confirmation decision

#### Claim ceiling preserved

**Reviewed.** correctly drawn; a confirmation pass creates interface-calibration evidence only and no mechanistic, representational or causal authority. This wording should be preserved verbatim through any amendment.

**Stated by draft.** yes

**Conditions satisfied by the draft.** no

#### Error spends the split

**Required strengthening.** extend the rule to technically incomplete runs so that an infrastructure failure cannot become a licence to re-run

**Reviewed.** correct

**Stated by draft.** yes

#### No reselection after confirmation

**Reviewed.** confirmed; no route found by which a failed confirmation promotes another profile

**Stated by draft.** yes

**One profile confirmation conditions.**

- the development and confirmation banks are disjoint and neither is reused
- the selection map from development outcomes to a single profile is fixed before any data, including tie-breaking and the no-profile-passes branch
- exactly one profile enters confirmation and the choice is not revisited after confirmation outcomes are seen
- the claim is stated conditionally on the selected profile rather than unconditionally about the best profile

**Published state.** The draft publishes no I5 null, alternative, n, alpha or rejection rule. I5 appears only as a prose question, a fail-closed route and a profile-table column.

**Reason.** the selection map itself is unpublished

**Required publication.**

- n and its unit for each confirmed construct
- the confirmation alpha and whether it is the study alpha or a separate confirmatory level
- the exact rejection count for each construct at that alpha
- the multiplicity treatment across the conjuncts, stated rather than assumed

**Reviewer note on conjunction level.** Under an intersection-union reading the confirmation level is the maximum component level, not the product; this must be stated explicitly because the opposite intuition is common.

**What i5 confirms.** For the single development-selected profile, on the independent one-shot confirmation bank: every gate-bearing construct that profile carries - I1a, I1b where applicable, I2, I3 primary, and the RP/I4/K4 construct where the positive reference is in scope - evaluated as a conjunction.

## Projected cell and operation table

**Provenance.** Copied verbatim from studies/study3/analysis/independent_methods_recalculation_tables.json, key projected_cells_and_operations, produced under CPU-only Azure ACR.

**Character.** Planning arithmetic, not an execution authorization. Cost is reported and was not used to weaken any required scientific contrast: where the reviewer's corrections increase projected work, the increase is reported rather than avoided.

### Unit definitions

**base item.** one registered question stem; the sampling unit and the independent unit for every derived variant

**derived variant.** one rendered presentation of a base item under one (position, symbol, alphabet, rendering) condition

**n symbol meaning.** throughout this review, n always means base items per atomic cell, never derived variants and never total calls

**scored row.** one derived variant scored under one (profile, role)

### Derived presentation variants per base item, by profile

| Profile | Variants per base item |
| --- | ---: |
| S1_label_bearing | {'applicable_variants_per_base_item': 96, 'label_alphabet_variants_per_base_item': 2, 'position_and_symbol_variants_per_base_item': 16, 'rendering_variants_per_base_item': 3} |
| S2_content_only | {'applicable_variants_per_base_item': 3, 'label_alphabet_variants_per_base_item': 0, 'position_and_symbol_variants_per_base_item': 0, 'rendering_variants_per_base_item': 3} |
| S3_content_only | {'applicable_variants_per_base_item': 3, 'label_alphabet_variants_per_base_item': 0, 'position_and_symbol_variants_per_base_item': 0, 'rendering_variants_per_base_item': 3} |
| S4_diagnostic_never_selectable | {'applicable_variants_per_base_item': 96, 'label_alphabet_variants_per_base_item': 2, 'position_and_symbol_variants_per_base_item': 16, 'rendering_variants_per_base_item': 3} |

### Work streams

#### S4 diagnostic

- *scope*: never-selectable diagnostic profile
- *scored rows*: 258048
- *selection authority*: none; excluded from every success union

#### positive reference I4

- *n base items per atomic cell*: 256
- *reviewer note*: the drafting projection budgets zero K4 items, so this entire stream is missing from it
- *roles*: 1
- *scope*: the already-qualified reference scored on the registered K4 construct through each candidate Study 3 interface
- *scored rows on the label bearing profile*: 24576

#### positive reference prequalification P3Q

- *authority*: operator decision OD2; not selected here
- *reviewer note*: cannot be projected in this round because the qualification bank, floor, n and interface are all still open under OD2; the review specifies the statistical fields that must be frozen, not the checkpoint
- *scope*: external canonical qualification interface, outside the Study 3 candidate panel
- *scored rows*: none

#### selected profile confirmation

- *profile note*: the label-bearing profile is used here only because it is the most expensive case; no profile is selected by this review
- *profile used for this projection*: S1_label_bearing
- *scope*: the single development-selected profile on the disjoint confirmation split
- *scored rows*: 258048

#### target development

- *model roles scored*: 3
- *roles note*: RT, RL and RI carry gate authority on the target constructs; R0 and RC are deterministic non-model controls and consume no forward pass; RP is scoped to gate I4 only
- *scope*: every gate-bearing construct for each selectable profile on the development split
- *scored rows*: 269568
- *scored rows by profile*:
  - S1_label_bearing: 258048
  - S2_content_only: 5760
  - S3_content_only: 5760

### Totals

| Quantity | Value |
| --- | ---: |
| all streams scored rows | 810240 |
| confirmation scored rows single selected profile | 258048 |
| development scored rows over selectable profiles | 269568 |
| diagnostic scored rows zero selection authority | 258048 |
| forward passes executed this round | 0 |
| generations executed this round | 0 |
| positive reference scored rows | 24576 |

### Discrepancies against the drafting projection

- **`S3_budgeted_as_four_scorings`** - drafting field `operation_boundaries.projected_future_operations.per_role_per_surface.S3_sequence_scorings` = 9728; 9728 is exactly 4 x 2432, which is the budgeting the same document forbids; the registered per-item forward-pass count for S3 is 1, and under the current single-token domain S3 reuses the S2 pass entirely
- **`K4_absent_from_the_projection`** - drafting field `operation_boundaries.projected_future_operations.assumptions` = 192 base items each for K1 and K3, 128 for K2, four permutation conditions from K5 and three renderings from K6; K4 carries gate I4 and is the only construct the positive reference is scored on, yet it receives no budgeted items, so the projected I4 work is zero while I4 is a required gate
- **`positive_reference_multiplied_through_every_construct`** - drafting field `operation_boundaries.projected_future_operations.development_total_across_4_roles_and_4_surfaces` = 68096; the total multiplies four model roles uniformly across every construct, but RP has gate_role 'Gate I4 only', so RP should not be budgeted on K1, K2, K3, K5 or K6 at all

### Executed operation counts

Every counter below is zero. The projection is planning arithmetic and authorizes nothing.

| Operation | Executed this round |
| --- | ---: |
| activation extractions | 0 |
| bank rows read | 0 |
| evidence rows created | 0 |
| forward passes | 0 |
| generations | 0 |
| gpu jobs | 0 |
| model downloads | 0 |
| network calls | 0 |
| prior result reads | 0 |
| provider calls | 0 |
| seeds drawn | 0 |
| tokenizer constructions | 0 |
| weight loads | 0 |

this is planning arithmetic only; it authorises nothing and every executed operation count below remains zero

## Operator decisions after review

This review adopts no operator decision. OD2 remains entirely operator-controlled. OD5 and OD6 receive explicit methods recommendations that are NOT adopted by this round.

### OD2 - positive-reference checkpoint identity, immutable revision, runtime, dtype and wrappers

**Review action: NONE - operator-controlled.**

Adopted by this round: no.

**Reviewer state.** no checkpoint selected, named as preferred, pinned, downloaded, tokenized, loaded, run, prequalified or substituted; specifically neither Qwen3-4B-Instruct-2507 nor Qwen2.5-Math-7B-Instruct nor any other model was chosen

**What the reviewer did supply.** the list of statistical fields a later OD2 authority must freeze, and the prequalification-versus-I4 separation requirement; both are methods requirements that constrain any checkpoint equally and select none

### OD5 - the paired equivalence decision rule and its size control

**Review action: RECOMMENDATION_ONLY.**

Adopted by this round: no.

**Recommendation (not adopted).** Do not retain the nominal Tango rule with a four-value sensitivity grid. Adopt one of: a registered nuisance maximisation over the feasible null boundary with the domain, tolerance, bracketing rule, convergence-failure behaviour and independent validation published; the conservative calibrated critical values returned by this review, z = 1.97269 at n 192 and z = 1.961978 at n 384 for margin 0.10; or the unconditional exact procedure of Hsueh, Liu and Chen (2001). Whichever is adopted, demote the paired criterion from gate authority until its size is controlled, and state the practical-irrelevance criterion that fixes the margin.

### OD6 - the I3 primary floor and the I3 sample size

**Review action: RECOMMENDATION_ONLY.**

Adopted by this round: no.

**Recommendation (not adopted).** Register exactly one I3 primary floor. If it is 0.90, n 256 with rejection count 244 gives exact power 0.953040775 at the draft's own lowest alternative 0.97 and the corrected Family B alpha 0.001666666667. If it is 0.95, no admissible n up to 768 reaches 0.90 power against 0.97, so the scientific claim must be revised rather than the alternative widened. Neither option is available until the I3 estimand is published, because the unit of n is not determined until the atomic cell is.

## Unresolved items

Items the draft self-disclosed as unresolved (U1 through U8 in packet section 7) are adjudicated here alongside items this review found unresolved. An unresolved item is never acceptance.

| ID | State | Owner | Subject | Resolution requires |
| --- | --- | --- | --- | --- |
| `UR-01` | UNRESOLVED_BLOCKING | drafting party | I3 primary estimand identifiability | publishing a variants-per-base-item factor per profile and reconciling the construction algorithm with the cluster rule, or restating I3 on a unit the construction produces |
| `UR-02` | UNRESOLVED_BLOCKING | drafting party | I3 primary indicator semantics across JSON, Markdown and packet | publishing J_inv, J_cor and their conjunction, and reconciling all three artifacts |
| `UR-03` | UNRESOLVED_BLOCKING | drafting party | Family B per-profile alpha not implemented | recomputing every component rule at 0.001666666667 and republishing every affected threshold, power and sample size, or withdrawing the claim |
| `UR-04` | UNRESOLVED_BLOCKING | drafting party | false conservativeness assertion in the authoritative JSON | withdrawing the assertion and recording the maximised realised level |
| `UR-05` | UNRESOLVED_BLOCKING | operator via OD5 | paired size control over the feasible nuisance domain | adopting one of the four admissible remedies and registering the optimisation contract |
| `UR-06` | UNRESOLVED_BLOCKING | operator via OD6 | I3 primary floor 0.90 versus 0.95 and its feasibility | registering one floor and demonstrating separability at an admissible n, or revising the claim |
| `UR-07` | UNRESOLVED_REQUIRED_CHANGE | drafting party | I5 confirmation specification | publishing null, alternative, n, alpha, rejection rule and multiplicity treatment |
| `UR-08` | UNRESOLVED_REQUIRED_CHANGE | drafting party | development profile-selection rule | publishing the selection map including tie-breaking and the no-profile-passes branch, fixed before any data |
| `UR-09` | UNRESOLVED_REQUIRED_CHANGE | drafting party | Family B denominator membership of S3 | fixing the denominator as a number before any data |
| `UR-10` | UNRESOLVED_REQUIRED_CHANGE | drafting party | unit of every sample-size symbol | declaring the unit at every point of definition, which is itself blocked until UR-01 fixes the atomic cell |
| `UR-11` | UNRESOLVED_REQUIRED_CHANGE | drafting party | I1a and I1b power shortfall | raising n to 256 at the corrected alpha, or explicitly lowering and justifying the target power |
| `UR-12` | UNRESOLVED_REQUIRED_CHANGE | drafting party | circular committed verification and the entrenched four-value grid test | replacing the recorded-rows assertion and the fixed-grid coverage test in the amendment round; RECORDED here, not repaired, because tests/test_study3_design.py is part of the review object |
| `UR-13` | UNRESOLVED_REQUIRED_CHANGE | drafting party | K5 and K6 stale generating-process text | rewriting both data_generating_process fields to the resolved constructions |
| `UR-14` | UNRESOLVED_REQUIRED_CHANGE | drafting party | S3 projection self-contradiction and the undecomposed projection | deciding one or four S3 scorings per item and republishing the projection decomposed by work stream |
| `UR-15` | UNRESOLVED_REQUIRED_CHANGE | drafting party | I4 multiplicity across operation families and depths | publishing either a per-family-per-depth level or a registered pooled evaluation |
| `UR-16` | UNRESOLVED_REQUIRED_CHANGE | drafting party | residual pooling paths across label alphabets and position-symbol cells | naming both paths in the pooling prohibitions |
| `UR-17` | UNRESOLVED_REQUIRED_CHANGE | drafting party | degenerate I3 rejection region at n 128, p0 0.95 | excluding degenerate regions explicitly or raising n |
| `UR-18` | UNRESOLVED_REQUIRED_CHANGE | drafting party | paired margin practical-irrelevance justification | stating the largest presentation effect considered practically irrelevant, before any data |
| `UR-19` | UNRESOLVED_MINOR | drafting party | Clopper-Pearson and uniformity tail-convention naming | renaming the field and stating the convention; no number changes |
| `UR-20` | UNRESOLVED_MINOR | drafting party | positive-reference dossier D-07 versus D-04 attribution | correcting both references to D-04 |
| `UR-21` | UNRESOLVED_MINOR | drafting party | stale Gate I1 labels in checkpoint role records | updating every role record to the post-split names with per-profile applicability |
| `UR-22` | UNRESOLVED_REQUIRED_CHANGE | operator via OD2 | external-qualification-interface requirement for the positive reference | requiring the qualification interface to be external to the candidate panel, not merely the bank to be isolated |

## Claim ceiling and zero-operation boundaries

Nothing in Study 3, at any disposition, licenses a mechanistic or causal claim. A passing interface calibration establishes only that a measurement interface can be read reliably enough to carry a later contrast. It does not establish that any internal representation was located, that any feature is causally responsible for any behaviour, or that any capability generalises beyond the registered banks.

**This review creates.**

- a methods verdict on draft-v0.2
- a set of reviewer-recommended candidate design parameters that are explicitly not adopted
- an independent recalculation table of proposed design quantities

**This review does not create.**

- any empirical result
- any measurement
- any interface selection
- any positive-reference selection
- any freeze
- any execution authority
- any mechanistic or causal authority
- any Study 1 or Study 2 change

**Every number in this review is** a proposed design parameter or a property of a hypothetical sampling distribution, never a measurement of any model

This review confers no execution authority of any kind. Draft-v0.2 remains unfrozen. No bank may be constructed, no checkpoint may be downloaded or loaded, no seed may be drawn, no gate may be evaluated against a model, and no confirmation split may be accessed as a consequence of this document.

Downstream authority required before any execution: ['an operator amendment round resolving every BLOCKING finding', 'a subsequent independent methods review of the amended draft', 'an explicit operator freeze authority', 'an explicit operator execution authority', 'resolution of OD2 by the operator']

### Operation counters for this round

Zero experimental operations were performed. No model or tokenizer was downloaded or constructed, no weights were loaded, no forward pass or generation was run, no activations were extracted, no probe was fitted, no patching, ablation or lens operation was performed, no experimental provider was called, no GPU job was submitted, no bank row was created or read, no seed was drawn, no gate was evaluated against a model, and the confirmation split was never accessed.

| Counter | Value |
| --- | ---: |
| ablation operations | 0 |
| activation extractions | 0 |
| bank rows created | 0 |
| bank rows read | 0 |
| confirmation split accesses | 0 |
| evidence rows created | 0 |
| forward passes | 0 |
| gate evaluations against a model | 0 |
| generations | 0 |
| gpu jobs | 0 |
| lens operations | 0 |
| model downloads | 0 |
| patching operations | 0 |
| prior result reads | 0 |
| probe fits | 0 |
| provider calls | 0 |
| seeds drawn | 0 |
| tokenizer constructions | 0 |
| weight loads | 0 |

### Selection state

This review selects nothing. Interface selection is a later development-split outcome and the positive-reference checkpoint remains operator decision OD2.

| Field | Value |
| --- | --- |
| selected interface profile | none |
| selected positive reference checkpoint | none |
| selected model | none |

### Authority flags

| Flag | Value |
| --- | --- |
| bank construction authorized | no |
| execution authorized | no |
| freeze authorized | no |
| frozen | no |
| gpu authorized | no |
| mechanistic authority created | no |
| model selection authorized | no |

## Next legal action

**`OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_3`**

The operator must open an amendment round producing draft-v0.3 that resolves every BLOCKING finding, and must then obtain a further independent methods review of the amended draft. Draft-v0.2 may not be frozen and may not be executed.

Routes directly to freeze: no. Routes directly to execution: no.

**Prohibited next actions.**

- freezing draft-v0.2
- issuing an execution authority on draft-v0.2
- constructing any item bank
- selecting or downloading any positive-reference checkpoint
- any P3-Q prequalification run
- any Azure GPU job
- accessing the confirmation split

**Minimum content of the amendment round.**

- resolve the I3 primary estimand by publishing an explicit variants-per-base-item factor for every profile, or by restating I3 on a unit the published construction actually produces
- publish a single I3 primary indicator definition and reconcile the authoritative JSON, the companion Markdown, and the review packet to it
- either implement the Family B per-profile alpha in every component rule and republish every affected threshold and sample size, or withdraw the 0.001666666667 claim and restate the study-level guarantee that the committed alpha 0.005 components actually deliver
- replace the four-value discordance sensitivity grid with a justified nuisance maximisation over the feasible null boundary, a calibrated conservative critical value, or a conservative-by-construction exact procedure, and withdraw the claim that exact enumeration bounds the level
- resolve the I3 primary floor to one value and demonstrate that it is reachable at an admissible sample size at the corrected alpha
- fix the unit of every sample-size symbol and republish the projection decomposed by work stream
