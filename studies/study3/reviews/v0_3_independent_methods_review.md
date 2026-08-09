# Study 3 draft-v0.3 second independent methods review

**State:** `STUDY3_DRAFT_V0_3_SECOND_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`

**Disposition:** **STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED**

**Only legal successor action:** `OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_4`

This document is a bounded, CPU-only, model-free methods review of an unfrozen design draft. It is not an amendment, a protocol freeze, a preregistration, a positive-reference selection, a bank construction, a seed draw, a model execution or a mechanistic result. Neither the documentation state nor the disposition is a scientific result or an execution authority.

## 0. Binding

| Binding | Value |
| --- | --- |
| reviewed commit | `2b36f5321d830ea6f70fff2b7bbca3cb93394046` |
| reviewed tree | `98d71cb35cca7b55d8f96f131064a5b9654dd3c7` |
| parent review commit | `e4bcda3a487ea9c9a085e3943103a07501014431` |
| reviewed draft-v0.2 commit | `8a2c4a0b2a73c5d802988333f11ea6c22828f6f5` |
| review object | 26 paths, 6 added, 20 modified, 0 deletions/renames/copies/type changes |
| reviewer edited any reviewed path | `false` |
| source authority | 40907 bytes, SHA-256 `d58ec53b29846d26e3f4a7f1f45b4b8625a4d59147c9cd5f687f4f86d6f20e62`, LF-only, no trailing newline |
| committed authority | `studies/study3/prompts/study3_v0_3_independent_methods_review_authority.md`, 40907 bytes, SHA-256 `d58ec53b29846d26e3f4a7f1f45b4b8625a4d59147c9cd5f687f4f86d6f20e62` |
| authority byte identity | `true` |

### Reviewed artifact identities

| Path | Bytes | SHA-256 |
| --- | --- | --- |
| `studies/study3/analysis/design_statistics.py` | 69226 | `8e279bbbd7e7322c8d823dc807bcdbc5d6a80c4e3f7e4a9385dd37e9b7eae4c5` |
| `studies/study3/analysis/design_statistics_tables.json` | 53100 | `a185b0145707b59d8c0a7da6438fc2f718f59175d37fdf40b4d38e98c79035c2` |
| `studies/study3/analysis/independent_methods_review_packet_v0_3.md` | 29040 | `62016c0f0512b616b5342e0a3be0e578dbeb4c97086b91e3618745e525aaa397` |
| `studies/study3/analysis/study2_to_study3_design_traceability.md` | 21049 | `17037a5ca04354db3bdd489d89653056f99960942e7979fbf8a3ecfba7aee620` |
| `studies/study3/design_receipt_v0_3.json` | 26342 | `9067313a671a318fbedc75b6c486bb55015dbb337d09690f73fddbd573dc9e27` |
| `studies/study3/prompts/study3_v0_3_design_amendment_authority.md` | 34682 | `de85aeff25e827e49d3e7c60d517b50cc69649d66190995a804ab2bc44308667` |
| `studies/study3/protocol/interface_calibration_protocol.schema.json` | 140007 | `1f15d2434133f24dfd7b1add908c9f5904b83e9317d17cc51c13c430743f4f89` |
| `studies/study3/protocol/interface_calibration_protocol_draft.json` | 206696 | `db2d51cce9971e916b3a02a5da0bb1a1e6a1c271bb79162e3c8515836db60a09` |
| `studies/study3/protocol/interface_calibration_protocol_draft.md` | 97393 | `670968eac4ec78f45e6eaaa270a4666957df5c7127dc7e4d7dfe4e71dac41633` |
| `studies/study3/references/methods_sources.md` | 20916 | `7efa77c33c3b8dae406efe4aa3f8b57c644fa4242140d72c1a3ff2528d37ef9a` |
| `studies/study3/references/positive_reference_dossier.md` | 11734 | `f300a4cbad9d809b0d5e878e9de43ddd0eb85bdb6737b0a8a3bbbcc650323e24` |
| `studies/study3/reviews/v0_3_operator_amendment.json` | 46502 | `29a1b33dde48d6969edea49fcc73e56003d5ebc24233883728a295b9ec265271` |
| `studies/study3/reviews/v0_3_operator_amendment.md` | 50720 | `7d0014ff111974f13dca683e0cebf62f60a6b52e8f40c78bcfb90b3ebd2f7f96` |
| `studies/study3/reviews/v0_3_operator_amendment.schema.json` | 22608 | `a7411718527397fb8ea5177032cdcea1274e0fc6a2591b6bb052c50ecdae0edf` |
| `tests/test_study3_design.py` | 93590 | `4b7f831878b2c58e98be13db44af560c4d8a2b31301a168e47c68c4b1250a633` |
| `tests/test_study3_methods_review.py` | 60781 | `331d2a7644ee3256d7a145fa8ba83d0b02dcfd1faa1ed8989b726c1c656509ba` |

## 1. Independence

- Independent implementation: `studies/study3/analysis/independent_methods_recalculation_v0_3.py`
- Independent tables: `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`
- Prohibited sources, none of which is imported, executed, dynamically loaded, copied through a reachable source literal, or used as a control-flow source:
  - `studies/study3/analysis/design_statistics.py`
  - `studies/study3/analysis/independent_methods_recalculation.py`

**Ordering.** Registered exact-rational parameters were extracted from the reviewed protocol object only. Every derivation in the independent implementation was authored and committed at commit 47ace671ebfc9e0e2270fc2025909d53e25d3adf BEFORE the reviewing session opened design_statistics.py or design_statistics_tables.json. The field-by-field comparison was performed only after that commit existed.

**Disclosed deviation.** After opening the drafting implementation the reviewer noticed that one helper in the independent implementation shared the name baseline_condition with a drafting function. It was renamed to registered_baseline_triple in a later commit purely to remove the appearance of convergence. The rename is value-neutral and was proved so: the emitted table is byte-identical before and after, SHA-256 ea11c345b611c72120a2deb6abac6764bf2abe94653d100a2123d3db8250bace.

**Local operations disclosure.** The reviewing session performed local read-only Git inspection, blob hashing, JSON parsing, static text audits and local execution of its own independent recalculation in emit and check modes. No local pytest run and no local decision-bearing statistical calculation is treated as review evidence. Three ephemeral operator-side helpers were used and are disclosed: a preflight blob-identity checker and two authoring serializers for the review JSON. None is committed, none carries decision authority, and no conclusion depends on them; every binding they touch is re-derived by the committed test and the committed recalculation.

The implementation derives its formulas from the English-language primary sources rather than from any committed implementation: Clopper and Pearson (1934) for the binomial sampling model and the exact one-sided tail; Berger and Hsu (1996) for intersection-union logic; and Tango (1998), Hsueh, Liu and Chen (2001) and Liu et al. (2002) used only to verify that the previously defective paired procedure is genuinely retired from decision authority. Every statistical family carries at least one closed-form identity, exhaustive enumeration or published-example check, and all of them pass:

| Check | Result |
| --- | --- |
| `all_identity_checks_passed` | `true` |
| `binomial_masses_sum_to_one_exactly` | `true` |
| `bonferroni_union_bound_reconstructs_study_level` | `true` |
| `clopper_pearson_boundary_closed_form` | `true` |
| `clopper_pearson_x_equals_n_lower_limit_solves_p_to_the_n_equals_alpha` | `true` |
| `complement_identity` | `true` |
| `exhaustive_sequence_enumeration_matches_closed_form` | `true` |
| `frechet_lower_bound_is_bonferroni_complement` | `true` |
| `frechet_upper_bound_is_min_component_power` | `true` |
| `intersection_union_size_bound` | `true` |
| `reflection_identity` | `true` |
| `tail_at_full_success_is_p_to_the_n` | `true` |
| `tail_at_zero_is_one` | `true` |
| `tail_monotone_in_p` | `true` |
| `tail_monotone_justifies_sup_at_p0` | `true` |

Agreement with the drafting bytes is not treated as validation anywhere in this review. Every reported agreement below is agreement between the reviewed object and a value the reviewer derived first.

## 2. Exact-binomial recalculation

Method: integer-only exact binomial tail arithmetic over the registered exact rationals; decimal policy renderings are refused as arithmetic inputs by a fail-closed parser. Size justification: the upper tail is non-decreasing in p, verified on a rational grid, so the exact size of {X >= c} against H0: p <= p0 is Pr_{p0}(X >= c).

### Development components

| Gate | p0 | p1 | alpha | n | Pass count | Exact null tail at p0 | Exact power at p1 | Minimal | Degenerate | Registered | Agrees |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | `9/10` | `97/100` | `1/600` | 256 | 244 | 0.001491215117 | 0.953040775212 | `true` | `false` | 244 | `true` |
| I1b | `9/10` | `97/100` | `1/600` | 256 | 244 | 0.001491215117 | 0.953040775212 | `true` | `false` | 244 | `true` |
| I2 | `1/2` | `7/10` | `1/600` | 128 | 82 | 0.000931234262 | 0.938986365033 | `true` | `false` | 82 | `true` |
| I3 | `9/10` | `97/100` | `1/600` | 256 | 244 | 0.001491215117 | 0.953040775212 | `true` | `false` | 244 | `true` |
| I4 | `4/5` | `9/10` | `1/600` | 256 | 224 | 0.001081002486 | 0.921083514878 | `true` | `false` | 224 | `true` |

### Confirmation components

| Gate | p0 | p1 | alpha | n | Pass count | Exact null tail at p0 | Exact power at p1 | Minimal | Degenerate | Registered | Agrees |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | `9/10` | `97/100` | `1/200` | 256 | 243 | 0.003307722347 | 0.976290353161 | `true` | `false` | 243 | `true` |
| I1b | `9/10` | `97/100` | `1/200` | 256 | 243 | 0.003307722347 | 0.976290353161 | `true` | `false` | 243 | `true` |
| I2 | `1/2` | `7/10` | `1/200` | 128 | 80 | 0.002962603303 | 0.972425828510 | `true` | `false` | 80 | `true` |
| I3 | `9/10` | `97/100` | `1/200` | 256 | 243 | 0.003307722347 | 0.976290353161 | `true` | `false` | 243 | `true` |
| I4 | `4/5` | `9/10` | `1/200` | 256 | 222 | 0.003276850097 | 0.963820467566 | `true` | `false` | 222 | `true` |

### Admissible sample-size search

the K5 baseline conditions are balanced over complete blocks of 32 consecutive base-item indices, so an admissible per-cell n is a positive multiple of 32.

| Family | Smallest admissible n | Pass count | Power | Smallest unrestricted n | Registered n is the smallest admissible |
| --- | --- | --- | --- | --- | --- |
| `I1a_I1b_I3_development` | 256 | 244 | 0.953040775212 | 227 | `true` |
| `I2_development` | 128 | 82 | 0.938986365033 | 110 | `true` |
| `I4_development` | 256 | 224 | 0.921083514878 | 233 | `true` |
| `I1a_I1b_I3_confirmation` | 224 | 213 | 0.960766898001 | 181 | `false` |
| `I2_confirmation` | 128 | 80 | 0.972425828510 | 92 | `true` |
| `I4_confirmation` | 224 | 195 | 0.938680486614 | 191 | `false` |

**Verdict.** 256 and 128 are justified at the development level: they are exactly the smallest admissible sizes meeting the 9/10 per-cell target at 1/600. At the confirmation level the registered sizes exceed the smallest admissible sizes because confirmation deliberately reuses the development sizes; that is conservative, raises power and is not a defect.

**Substantive basis for p0 and p1.** The reviewer accepts p0 = 9/10 for I1a, I1b and I3 and p0 = 1/2 for I2 as substantively argued: I1a and I1b test trivially recoverable content and explicit binding, where a floor near ceiling is the point, and I2's null is a headroom floor. p0 = 4/5 for I4 is NOT independently justifiable at this time, because the competence floor that would give it meaning is deferred to OD2; see finding S3MR2-007. In no case did the reviewer find the value justified merely because it makes a preferred n pass.

## 3. The I3 estimand and the claim ceiling

- Identified estimand: Pr(both variants of the base-item contrast cluster are scored correct against the unique registered ground truth), per applicable atomic contrast cell
- `J_both` equals `J_cor`: `true`
- Is a joint robust-correctness floor: `true`
- Is a presentation-invariance or equivalence claim: `false`
- Protocol claim language exceeds the identified estimand: `true`

**Permitted claim ceiling.** at most: in each applicable registered contrast cell, the joint correctness rate under the registered baseline AND the registered one-factor transformed presentation exceeds the registered floor. No claim, in either direction, that a registered presentation factor does or does not move the instrument's reading.

The reviewer enumerated the full ordered outcome lattice rather than re-checking the eight cases the drafting party tabulates. Over `{correct, wrong_a, wrong_b, invalid}` for each of the two variants there are 16 ordered cases, and in every case where `J_cor = 1` it is also true that `J_inv = 1`.

| Property | Result |
| --- | --- |
| `j_cor_implies_j_inv` | `true` |
| `j_both_is_mathematically_identical_to_j_cor` | `true` |
| `j_both_is_mathematically_identical_to_j_inv` | `false` |
| `j_both_is_a_redundant_conjunction` | `true` |
| `stable_wrong_cases_all_fail` | `true` |
| `stable_invalid_cases_all_fail` | `true` |
| `mixed_correctness_cases_all_fail` | `true` |
| `estimand_is_a_joint_correctness_floor` | `true` |
| `estimand_is_a_presentation_effect_or_equivalence_contrast` | `false` |

### Counterexamples

| Case | Baseline | Transformed | Decrement | Pr(J_both = 1) | Exceeds p0 = 0.90 | Reaches p1 = 0.97 |
| --- | --- | --- | --- | --- | --- | --- |
| `nested_failures_baseline_1_00_transformed_0_91` | 1.0000 | 0.9100 | 0.0900 | 0.9100 | `true` | `false` |
| `nested_failures_baseline_1_00_transformed_0_98` | 1.0000 | 0.9800 | 0.0200 | 0.9800 | `true` | `true` |
| `perfect_invariance_but_low_correctness` | 0.8500 | 0.8500 | 0.0000 | 0.8500 | `false` | `false` |
| `no_presentation_effect_high_correctness` | 0.9700 | 0.9700 | 0.0000 | 0.9700 | `true` | `true` |

A process with a real presentation decrement can exceed the registered null and can reach the registered lowest alternative of interest, while a process with zero presentation effect and lower competence fails. The gate therefore orders processes by joint correctness, not by presentation stability.

## 4. Construction, multiplicity and the selection graph

| Construction law | Result |
| --- | --- |
| `k5_contrast_count` | `7` |
| `k6_contrast_count` | `2` |
| `k5_complete_block_size` | `32` |
| `k5_block_is_a_complete_replicate` | `true` |
| `k5_every_baseline_condition_occurs_exactly_once_per_block` | `true` |
| `slot_to_symbol_map_is_a_bijection` | `true` |
| `exactly_one_correct_content_per_render` | `true` |
| `correct_content_carries_the_intended_symbol` | `true` |
| `k5_all_contrasts_are_one_factor` | `true` |
| `k5_x_k6_cross_product_exists` | `false` |
| `randomness_used` | `none` |

| Selection-map property | Result |
| --- | --- |
| `enumerated_states` | `16` |
| `map_is_total_over_enumerated_inputs` | `true` |
| `map_is_deterministic_one_legal_next_state` | `true` |
| `denominator_is_constant_3` | `true` |
| `s3_selectable_without_multi_token_authority` | `false` |
| `stop_states` | `3` |

Adjudications required by the review authority:

| Question | Answer |
| --- | --- |
| `intersection_union_logic_matches_the_profile_claim` | `true` |
| `per_component_1_600_bounds_a_false_qualified_profile_without_within_profile_correction` | `true` |
| `union_over_the_fixed_three_profile_denominator_is_bounded_by_1_200_under_arbitrary_dependence` | `true` |
| `denominator_3_when_S3_is_inactive_is_pre_data_and_conservative` | `true` |
| `selection_map_is_total_deterministic_and_consistent_with_S2_S3_S1` | `true` |
| `S3_impossible_to_select_under_the_current_single_token_domain` | `true` |
| `S3_cannot_become_selectable_without_a_new_multi_token_authority` | `true` |
| `one_shot_confirmation_at_1_200_needs_no_across_profile_correction` | `true` |
| `every_state_has_exactly_one_legal_next_state` | `false` |
| `any_descriptive_quantity_can_rescue_a_failed_gate_or_influence_selection` | `false` |

**Why the state machine is not total in the required sense.** an I0 failure has one registered next state under gate_hierarchy (global instrument STOP with restart) and a different one under stage 1 and the selection map (per-profile elimination); two of the four registered legal stop states are unreachable from the published map

### Reviewer-authored decision graph

| State | Rule or gate | On pass | On fail |
| --- | --- | --- | --- |
| `Q0_INSTRUMENT` | I0 | `Q1_DEVELOPMENT` | `STOP_INSTRUMENT_DEFECT` |
| `Q1_DEVELOPMENT` | evaluate every applicable component of every selectable profile in every applicable atomic cell at component level 1/600; a profile is eligible only if every applicable cell rejects | `Q2_SELECTION` | `-` |
| `Q2_SELECTION` | walk S2, then S3, then S1; select the first profile that is eligible AND applicable; S3 is applicable only if a later authority has activated a multi-token answer domain; the denominator remains 3 regardless | `Q3_CONFIRMATION` | `STOP_NO_SELECTABLE_INTERFACE_REMAINS` |
| `Q3_CONFIRMATION` | I5 | `CALIBRATED_PENDING_SEPARATE_AUTHORITY` | `STOP_CONFIRMATION_FAILED` |
| `STOP_INSTRUMENT_DEFECT` | the instrument is defective; nothing was measured about any interface | `-` | `-` |
| `STOP_NO_SELECTABLE_INTERFACE_REMAINS` | no candidate interface met the registered gates under the registered conditions | `-` | `-` |
| `STOP_CONFIRMATION_FAILED` | the selected profile did not replicate; the confirmation split is spent and no substitution is permitted | `-` | `-` |
| `CALIBRATED_PENDING_SEPARATE_AUTHORITY` | the named interface met the registered gates for the named tasks and roles, conditional on the single selected profile; no mechanistic authority is created | `-` | `-` |

the reviewer's graph and the reviewed sixteen-row map agree on every selection and stop-no-selectable outcome; they differ only in that the reviewer's graph separates I0 so that STOP_INSTRUMENT_DEFECT is reachable. Rescue paths: none. Quantities with no selection authority: `J_inv considered alone`, `J_cor considered alone`, `the descriptive paired 2x2 summary`, `any pooled rate`, `per-cell Clopper-Pearson bands`, `the selected-label uniformity diagnostic`, `every S4 observation`.

## 5. Per-cell, family, profile, selection and confirmation power

| Profile | Cells at n=256, p0=9/10 | Cells at n=128, p0=1/2 | Cells at n=256, p0=4/5 | Total |
| --- | --- | --- | --- | --- |
| S1 | 33 | 6 | 4 | 43 |
| S2 | 9 | 6 | 4 | 19 |
| S3 | 9 | 6 | 4 | 19 |
| S4 | 33 | 6 | 0 | 39 |

**Assumption.** values labelled 'under independence' assume the gate-bearing cells are independent. The reviewer does NOT assert that assumption; disjoint base-item identities do not imply independence across cells that share checkpoints, templates, strata, operation families or depths. Bounds valid under arbitrary dependence are given alongside.

| Quantity | Under independence | Frechet lower bound under arbitrary dependence |
| --- | --- | --- |
| `S1_development_eligibility` | 0.100885944 | 0.000000000 |
| `S2_development_eligibility` | 0.320003768 | 0.000000000 |
| `S3_development_eligibility` | 0.320003768 | 0.000000000 |
| `S1_confirmation_conjunction` | 0.330544875 | 0.000000000 |
| `S2_confirmation_conjunction` | 0.587941985 | 0.476450020 |
| `S3_confirmation_conjunction` | 0.587941985 | 0.476450020 |
| `S1_development_then_confirmation` | 0.033347332 | not applicable |
| `S2_development_then_confirmation` | 0.188143651 | not applicable |
| `S3_development_then_confirmation` | 0.188143651 | not applicable |

| Power level | Registered in the reviewed object |
| --- | --- |
| `full_confirmation_power` | the probability that the one-shot confirmation conjunction rejects in every applicable cell; not registered anywhere |
| `gate_family_power` | the probability that every cell of one gate rejects; not registered anywhere |
| `per_cell_power` | the probability that one atomic cell rejects at exactly p1; registered and met |
| `probability_selection_map_returns_a_winner` | determined by the profile-eligibility events and the registered order; not registered anywhere |
| `profile_eligibility_power` | the probability that every applicable cell of every applicable component of one profile rejects; not registered anywhere |

**Does the protocol label per-cell power as overall power?** `true`. Locations: `proposed_statistics.target_power`, `declared_assumptions.target_power`, `interface_calibration_protocol_draft.md exact-rational policy table row 'target power'`.

**Decision.** MISSTATED. The 9/10 target is published as an unqualified study-level policy parameter beside scope-qualified alpha levels, and is implemented and verified only per atomic cell. No artifact derives gate-family, profile, selection or confirmation power.

**Blocking or not.** BLOCKING as a feasibility and labelling defect; recorded as S3MR2-002.

**Bounded recommendation.** The reviewer does not choose a family-level target and does not inflate n or weaken any gate. The amendment must either register a family-level power target and re-derive sizes or structure against it, or register the per-cell scope of the 9/10 target explicitly together with the derived profile, selection and confirmation operating characteristics, and accept them on the record.

## 6. Independently derived operation table

| Work stream | Published | Reviewer reconstruction | Agrees |
| --- | --- | --- | --- |
| `deterministic_I0_fixtures` | 502 | 502 | `true` |
| `target_role_development` | 20736 | 20736 | `true` |
| `RP_I4_under_candidate_profiles` | 2048 | 2048 | `true` |
| `selected_profile_one_shot_confirmation` | 17152 | 17152 | `true` |
| `S4_diagnostic_generation` (generations) | 16128 | 16128 | `true` |
| `S4_diagnostic_generation` (generated tokens) | 258048 | 258048 | `true` |
| `S4_diagnostic_generation` (forward passes) | `null` | unmapped | `false` |
| `positive_reference_external_P3Q` | `null` | `null` | `true` |

**S4 decode-step mapping.** autoregressive decoding costs at least one forward pass per generated token, implying an upper bound of 258,048 decode-step forward evaluations for this stream alone; the repository operation ontology has no decode-step category

**Is the external P3-Q null correct rather than zero?** `true`. a zero would assert that a selected positive reference needs no qualification work; a null records that no checkpoint, interface, bank, floor, n, multiplicity treatment or stop rule has been chosen

**Does any document incorrectly say that Study 3 adds zero forward passes when the intended subject is the S3 interface profile?** `false`. The reviewer searched every protocol, packet, amendment and routing artifact and found no such statement; the subject is the S3 profile in every occurrence and the S3-versus-S2 scope is explicit.

**Do the totals distinguish rendered rows, scored rows, logit reads, forward passes, generation calls and generated tokens consistently?** `false`.

This is planning arithmetic only. It authorises nothing, approves no budget and creates no execution authority.

## 7. Tango retirement

| Question | Answer |
| --- | --- |
| `retired_from_every_decision_role` | `true` |
| `residual_decision_path_found` | `false` |
| `false_conservativeness_assertion_withdrawn` | `true` |
| `historical_evidence_immutable` | `true` |
| `descriptive_remnants_carry_no_authority` | `true` |

**Decision.** VERIFIED. The retirement is complete and is the reviewer's answer to the drafting party's first question.

YES. Retiring the procedure from every decision role fully removes the size-control defect recorded in S3MR-004 and S3MR-005. No residual decision path remains anywhere in the amended protocol.

## 8. Binomial sampling model

- Registered anywhere in the reviewed object: `false`
- Randomness present in the current design round: none
- Required elements that are missing:
  - superpopulation or generating process
  - draw mechanism and seed authority
  - with-or-without-replacement rule
  - template, family and depth clustering treatment
  - reuse across roles and profiles
  - exchangeability argument

What a later bank or seed authority must do:
- register the superpopulation or generating process for each stratum
- register the draw mechanism, its seed authority and the with-or-without-replacement rule
- register whether base items are reused across target roles and across interface profiles
- register the template, operation-family and depth clustering treatment
- demonstrate that the registered independent unit is exchangeable within every atomic cell

If the future bank is a fixed finite census or a deterministic set: binomial inference is NOT justified; a finite-population, stratified, clustered or explicitly descriptive interpretation would be required.

**Decision.** NOT EXECUTABLE WITHOUT SUBSTANTIVE AMENDMENT. See S3MR2-010.

## 9. I4, S4 and OD2

- I4 floor, alpha, n and cells verified: `true`
- Parameters support the narrow claim that an already qualified reference works through a candidate interface: `false` - the narrow claim requires the competence floor at which the RP was qualified to be known and to stand in a registered relation to I4's p0 and p1; that floor is deferred to OD2 and no relation is registered
- P3-Q and I4 use physically disjoint items, interfaces, decisions and authority: `true`
- No circular qualification: `true`

**S4 I4 applicability.** CONTESTED AND UNRECONCILED. retained_exact_binomial_gates[I4], the confirmation gate row and gate_hierarchy[I4] assert S4 is applicable; gate_truth_table.rows[S4].I4 and stage_1_component_evaluation.components_by_profile.S4 deny it; the operation projection accounts only S1, S2 and S3. The reviewer does not choose for the operator, but records that the not-applicable reading is the coherent one and that the arithmetic gap is 1,024 scored rows and 1,024 forward passes.

**Can OD2 remain unresolved without making the generic I4 method internally undefined?** `true`

A later OD2 authority must freeze exactly:
- checkpoint identity and immutable revision hash
- the canonical qualification interface, which must not be S1, S2, S3 or S4
- the RP-specific I4 wrapper and chat-template policy
- prequalification bank identity and its isolation from the development and confirmation seeds
- the P3-Q competence floor AND its registered relation to I4's p0 and p1
- p0
- p1
- alpha
- n
- the rejection rule
- the operation-family and depth treatment
- the stopping rule
- the provenance record

No checkpoint is selected, preferred, pinned, revision-resolved, downloaded, tokenized, loaded, run or prequalified by this review: `checkpoint_selected_by_this_review = false`.

## 10. I5 confirmation lifecycle

| Question | Answer |
| --- | --- |
| `a_pass_supports_only_the_registered_interface_calibration_claim_and_creates_no_mechanistic_authority` | `true` |
| `cannot_be_accessed_before_separate_authority` | `true` |
| `cannot_be_retried_retuned_rescued_or_used_to_select_another_profile` | `true` |
| `confirmation_thresholds_and_exact_alpha_independently_verified` | `true` |
| `covers_I0_I1a_I1b_I2_I3_J_both_and_I4_in_every_applicable_atomic_cell_for_one_preselected_profile` | `true` |
| `full_conjunction_confirmation_power_evaluated` | `true` |
| `physically_disjoint` | `true` |
| `read_once` | `true` |
| `spent_on_error_or_ambiguity` | `true` |

**Full-conjunction confirmation power.** 0.330544875 for S1 and 0.587941985 for S2 or S3 under independence, with a Frechet lower bound of 0.000000000 for S1 and 0.476450020 for S2 or S3; not registered anywhere in the reviewed object

**Defect.** the confirmation applicability rows admit the never-selectable profile S4.

**Decision.** SPECIFIED BUT NOT ACCEPTABLE AS WRITTEN. See S3MR2-004 and S3MR2-002.

## 11. Inherited-repair audit: all twenty findings

Each row is adjudicated on independent evidence. The drafting party's `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` label is not accepted as proof anywhere.

| Finding | Original severity | Status | Repair | Closes without creating a new defect | New defect |
| --- | --- | --- | --- | --- | --- |
| `S3MR-001` | BLOCKING | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-002` | BLOCKING | `PARTIALLY_RESOLVED` | substantive | `false` | S3MR2-001 |
| `S3MR-003` | BLOCKING | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-004` | BLOCKING | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-005` | BLOCKING | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-006` | BLOCKING | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-007` | MAJOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-008` | MAJOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-009` | MAJOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-010` | MAJOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-011` | MAJOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-012` | MAJOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-013` | MAJOR | `PARTIALLY_RESOLVED` | substantive | `false` | S3MR2-005 |
| `S3MR-014` | MAJOR | `PARTIALLY_RESOLVED` | substantive | `false` | S3MR2-009 |
| `S3MR-015` | MAJOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-016` | MAJOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-017` | MAJOR | `PARTIALLY_RESOLVED` | substantive | `false` | S3MR2-006, S3MR2-004 |
| `S3MR-018` | MINOR | `VERIFIED_RESOLVED` | cosmetic | `true` | - |
| `S3MR-019` | MINOR | `VERIFIED_RESOLVED` | substantive | `true` | - |
| `S3MR-020` | MINOR | `VERIFIED_RESOLVED` | cosmetic | `true` | - |

**`S3MR-001` - `VERIFIED_RESOLVED`.** The I3 estimand is now identifiable from the published construction. The reviewer re-implemented the registered construction algorithm independently from its seven published steps and confirmed, without reading the drafting implementation, that the baseline triple (k mod 4, (k div 4) mod 4, (k div 16) mod 2) makes every one of the 32 baseline conditions occur exactly once in each complete block of 32 consecutive base-item indices, that the slot-to-symbol rotation is a bijection on four slots, that exactly one correct content is placed per render, that the correct content carries the intended displayed symbol, that each of the seven K5 contrast IDs changes exactly one registered factor with a single change signature over the whole block, and that the cluster holds exactly two variants everywhere. The cross-product reading is gone and no 32 x 3 or 96-variant expansion exists.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `i3_contrast_registry.independent_unit`, `i3_contrast_registry.variants_per_cluster`, `atomic_evaluation_cells.i3_sampling_unit`, `counterbalancing_design.construction_algorithm.steps`, `i3_construction_laws`.

**`S3MR-002` - `PARTIALLY_RESOLVED`.** The original defect is closed: three indicators now carry disjoint definitions, exactly one of them (J_both) is named the gate indicator, and all four artifacts agree on that definition, so the two mutually exclusive readings of draft-v0.2 no longer coexist. The repair nevertheless creates a new defect. The reviewer enumerated the full ordered 4 x 4 outcome lattice over {correct, wrong_a, wrong_b, invalid} - strictly larger than the eight cases the drafting party tabulates - and established that J_cor = 1 implies J_inv = 1 in every case, hence J_both is identically equal to J_cor and the primary indicator is mathematically the event that both variants are correct. Requiring correctness inside the conjunction removed the stable-wrong pass, which is what the finding demanded, but it simultaneously removed all invariance content from the statistic. That is recorded as new BLOCKING finding S3MR2-001.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/analysis/independent_methods_review_packet_v0_3.md`, `studies/study3/analysis/design_statistics_tables.json`. Fields: `proposed_statistics.i3_indicators.J_inv.definition`, `proposed_statistics.i3_indicators.J_cor.definition`, `proposed_statistics.i3_indicators.J_both.definition`, `proposed_statistics.i3_indicators.J_both.estimand`, `proposed_statistics.i3_indicators.expected_integrity_invariant`, `gate_hierarchy[I3].primary_criterion`.

**`S3MR-003` - `VERIFIED_RESOLVED`.** The advertised per-profile level is now the level that actually derives every threshold. The reviewer re-derived all five development thresholds from the exact rational 1/600 and all five confirmation thresholds from the exact rational 1/200, using integer-only binomial tail arithmetic and refusing any decimal rendering as an arithmetic input, and reproduced 244, 244, 82, 244, 224 and 243, 243, 80, 243, 222 exactly. The reviewer also verified in exact rational arithmetic that 1/600 x 3 = 1/200, so the declared and implemented levels cannot diverge. Every derived threshold is additionally minimal at its level: the tail at pass_count - 1 exceeds alpha in all ten rows.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `proposed_statistics.development_component_alpha_exact_rational`, `proposed_statistics.study_development_screening_alpha_exact_rational`, `proposed_statistics.confirmation_component_alpha_exact_rational`, `hypothesis_families.family_B_across_profiles.exact_reconstruction`, `development_exact_binomial_components[*].alpha_exact_rational`.

**`S3MR-004` - `VERIFIED_RESOLVED`.** The conservativeness assertion is withdrawn rather than reworded. The reviewer searched the protocol JSON, the protocol Markdown, the protocol schema, the packet and both amendment artifacts and found no surviving assertion that the paired procedure's exact type-I error does not exceed its nominal level, and no restatement of that claim in weaker language. The withdrawal is recorded as incorrect rather than re-scoped, and the first reviewer's exceedance finding stands unchallenged.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics.py`, `studies/study3/references/methods_sources.md`. Fields: `retired_procedures.tango_paired_equivalence.status`, `retired_procedures.tango_paired_equivalence.false_assertion_withdrawn`, `retired_procedures.tango_paired_equivalence.retired_from`.

**`S3MR-005` - `VERIFIED_RESOLVED`.** The four-point grid is removed and the procedure it supported carries no decision role anywhere. The reviewer confirmed by static audit that design_statistics.py contains no critical value, no equivalence margin, no paired p-value and no function verify_paired_method, that every remaining mention of Tango, discordance, equivalence or margin in that file occurs either in the retirement narrative or inside an explicit prohibition list, and that the surviving paired 2x2 summary is published with status DESCRIPTIVE_ONLY_NO_DECISION_AUTHORITY and an explicit carries_no list covering null, alpha, p-value, critical value, equivalence margin, pass or fail, rescue path and ranking weight.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics.py`, `studies/study3/analysis/design_statistics_tables.json`. Fields: `retired_procedures.four_point_discordance_grid.status`, `retired_procedures.tango_paired_equivalence.retired_from`, `descriptive_paired_summary.carries_no`, `descriptive_paired_summary.status`.

**`S3MR-006` - `VERIFIED_RESOLVED`.** Exactly one I3 floor is active. The reviewer confirmed that no active numeric field in the protocol JSON carries the value 0.95 anywhere, that active_floor_count is 1, and that the single registered pair p0 = 9/10 against p1 = 97/100 is separable at an admissible n: the independently derived threshold 244 of 256 attains exact power 0.953040775212 at the implemented level 1/600, above the 9/10 target, with a non-degenerate rejection region.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_review_packet_v0_3.md`. Fields: `proposed_statistics.i3_floor.active_floor_count`, `proposed_statistics.i3_floor.p0_exact_rational`, `proposed_statistics.i3_floor.p0_0_95_status`.

**`S3MR-007` - `VERIFIED_RESOLVED`.** Every emitted binomial row carries an explicit null column, and the set of distinct I3 nulls has size 1 in both the development and the confirmation table. No table mixes two nulls under one stated hypothesis.

Evidence: `studies/study3/analysis/independent_methods_review_packet_v0_3.md`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/protocol/interface_calibration_protocol_draft.md`. Fields: `development_exact_binomial_components[*].null_hypothesis`, `confirmation_exact_binomial_components[*].null_hypothesis`.

**`S3MR-008` - `VERIFIED_RESOLVED`.** n = 192 appears in no active field and n = 256 attains exact power 0.953040775212 per cell at 1/600. The reviewer additionally ran the full admissible-n search implied by the registered balancing rule, over multiples of the complete-block size 32, and independently confirmed that 256 is the SMALLEST admissible per-cell size meeting the 9/10 target for I1a, I1b, I3 and I4 at the development level, and that 128 is the smallest admissible size for I2. The registered sizes are therefore justified rather than merely sufficient. p1 was not moved and the target power was not lowered.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `proposed_statistics.sample_sizes.I1a.n`, `proposed_statistics.sample_sizes.n_192_status`, `admissible_sample_size_searches.I1a_development`.

**`S3MR-009` - `VERIFIED_RESOLVED`.** The circular verification is deleted with the procedure it verified: design_statistics.py no longer defines verify_paired_method and no longer asserts a size bound over rows it recorded itself. The fixed four-value grid coverage test is gone and an AST-based anti-transcription audit is present in the committed design test. The reviewer did not modify either existing Study 3 test module.

Evidence: `studies/study3/analysis/design_statistics.py`, `tests/test_study3_design.py`. Fields: `design_statistics.py::verify_paired_method (absent)`, `tests/test_study3_design.py AST literal audit`.

**`S3MR-010` - `VERIFIED_RESOLVED`.** The K5 generating-process text now states the seven one-factor pairwise contrasts actually adopted. The reviewer independently confirmed the contrast set is exactly {K5-P1, K5-P2, K5-P3, K5-S1, K5-S2, K5-S3, K5-A1}, that each changes exactly one registered factor, and that the two registered label alphabets are mutually disjoint and disjoint from the answer domain.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`. Fields: `task_strata[K5].data_generating_process`, `counterbalancing_design.k5_contrasts`, `i3_contrast_registry.k5`.

**`S3MR-011` - `VERIFIED_RESOLVED`.** K6 is registered as exactly two disjoint pairwise contrast cells, K6-SEP and K6-INSTR, each with two variants, each varying only the separator or only the instruction sentence, with the answer cue and every other prompt byte held fixed. The reviewer independently confirmed the cell count and the one-factor property.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`. Fields: `task_strata[K6].data_generating_process`, `counterbalancing_design.k6_contrasts`, `i3_pairwise_construction_verification.k6_answer_cue_fixed_within_every_pair`.

**`S3MR-012` - `VERIFIED_RESOLVED`.** The factor-of-four self-contradiction is gone. S3's incremental forward passes and incremental sequence-scoring rows are exactly zero, and the reviewer independently confirmed the argument is sound under the registered conditions: with a jointly single-token answer domain, an identical prefix and reuse of the identical logit vector, a length-normalised sequence score of a one-token candidate is a strictly monotone function of that token's log-probability, so the S3 argmax equals the S2 argmax by construction and the comparison is CPU arithmetic on logits S2 already recorded. The four stated preconditions are registered and are each necessary.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `operation_boundaries.projected_future_operations.s3_current_domain_accounting.additional_forward_passes`, `operation_boundaries.projected_future_operations.work_streams.target_role_development.by_profile.S3`.

**`S3MR-013` - `PARTIALLY_RESOLVED`.** The decomposition is substantive and correct. The projection is now six named work streams, each with its own units, and the reviewer reconstructed every published total from primitive cell counts without copying: 5,376 rendered rows per target role for S1 and 1,536 for S2, hence 16,128 and 4,608 across three roles and 20,736 for target-role development; 1,024 RP rows per accounted profile hence 2,048; and 16,128 + 1,024 = 17,152 as the S1-bounded confirmation figure. The specific complaint that forward passes, sequence scorings and generations were silently mixed nevertheless survives in one stream: S4_diagnostic_generation publishes forward_passes = null while publishing 16,128 generations and a 258,048 generated-token upper bound, so the dominant cost term of that stream is still unmapped. That is recorded as new MAJOR finding S3MR2-005.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `operation_boundaries.projected_future_operations.work_streams`, `operation_boundaries.projected_future_operations.work_streams.S4_diagnostic_generation.forward_passes`, `operation_boundaries.projected_future_operations.work_streams.S4_diagnostic_generation.generated_tokens_upper_bound`.

**`S3MR-014` - `PARTIALLY_RESOLVED`.** The unit registry is published with four disjoint units and every gate record and every emitted binomial row carries a non-empty unit_of_n that partitions by gate exactly as registered, which is the substantive part of the repair. One stream still violates the registry it introduced: deterministic_I0_fixtures publishes base_items = 464, which is 232 clusters times 2 variants, i.e. a rendered-row count filed under the base_item unit. The registered dimensional identity rendered_rows = clusters x 2 is asserted only for the four I3 components, so this stream escapes the check that would have caught it. Recorded as new MINOR finding S3MR2-009.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_review_packet_v0_3.md`. Fields: `unit_registry.units`, `unit_registry.prohibition`, `operation_boundaries.projected_future_operations.work_streams.deterministic_I0_fixtures.base_items`.

**`S3MR-015` - `VERIFIED_RESOLVED`.** The reviewer independently confirmed pass_count < n strictly in all ten active rows, so no active rejection region requires every unit to succeed. The degenerate configuration n = 128 at p0 = 0.95 is removed from the active design together with p0 = 0.95 itself, and the prohibition is enforced by a raise in the derivation rather than asserted in prose.

Evidence: `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `development_exact_binomial_components[*].degenerate_rejection_region`, `confirmation_exact_binomial_components[*].degenerate_rejection_region`.

**`S3MR-016` - `VERIFIED_RESOLVED`.** The denominator is a pre-data integer, not a condition. The reviewer independently enumerated all sixteen pre-data scenarios with an independently authored resolver and confirmed the denominator is the constant 3 in every row, including every row in which S3 is skipped. Retaining 3 when only two profiles can be selected is conservative rather than data-dependent: the realised union bound is then 2/600 = 1/300, which is strictly below the study-level 1/200.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `development_selection_and_confirmation_plan.stage_2_selection.fixed_selectable_profile_denominator`, `development_selection_map[*].fixed_selectable_profile_denominator`.

**`S3MR-017` - `PARTIALLY_RESOLVED`.** I5 now has a complete statistical specification - covered constructs, component level 1/200, per-component nulls, sizes with units and independently reproduced rejection counts, intersection-union conjunction, one-shot rule, reselection prohibition and access authority - and the development selection rule is a published, total, deterministic sixteen-row map whose every row the reviewer reproduced with an independently authored resolver. Two defects remain. The map's input vector aggregates I0, whose registered failure semantics is a global instrument STOP with a restart from I0, together with the interface-adequacy gates, whose failure semantics is per-profile elimination, so the same event has two different registered legal next states and the registered stop state STOP_INSTRUMENT_DEFECT is unreachable from the published map. Separately, all five confirmation rows list the never-selectable profile S4 in applicable_profiles although confirmation is entered only by a development-selected profile. Recorded as new findings S3MR2-006 and S3MR2-004.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`. Fields: `development_selection_and_confirmation_plan.stage_3_confirmation`, `development_selection_and_confirmation_plan.stage_2_selection.rule`, `gate_hierarchy[I0].legal_next_state_on_fail`, `confirmation_exact_binomial_components[*].applicable_profiles`.

**`S3MR-018` - `VERIFIED_RESOLVED`.** No checkpoint-role record names a gate called I1; every record uses the post-split I1a/I1b names and states applicability per profile. The repair is cosmetic by nature, which is appropriate: the finding was a labelling defect and no number or decision depended on it.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/protocol/interface_calibration_protocol_draft.md`. Fields: `checkpoint_roles[*]`.

**`S3MR-019` - `VERIFIED_RESOLVED`.** Every interval and band now names the mass it consumes at the point of tabulation, the misleading field name simultaneous_alpha is gone, and the lower-tail mass is exactly half the two-sided simultaneous mass in all twelve Clopper-Pearson rows. The repair is substantive rather than cosmetic because it changes what the published number means, even though no number changed.

Evidence: `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/design_statistics.py`, `studies/study3/protocol/interface_calibration_protocol_draft.md`. Fields: `descriptive_clopper_pearson_lower_bounds[*].two_sided_simultaneous_mass`, `descriptive_clopper_pearson_lower_bounds[*].lower_tail_mass_consumed_by_this_bound`, `descriptive_clopper_pearson_lower_bounds[*].tail_convention`, `selected_label_uniformity_diagnostic[*].two_sided_mass_across_the_band`.

**`S3MR-020` - `VERIFIED_RESOLVED`.** The obligation back-reference is corrected: the dossier discharges the obligation attached to D-04, and the surviving occurrences of D-07 appear only in the narrative that explains the correction and explicitly disambiguates D-07 as a different, pooling-related defect. The dossier also declares UNSELECTED. No candidate is selected, preferred, pinned or prequalified.

Evidence: `studies/study3/references/positive_reference_dossier.md`. Fields: `positive_reference_dossier.md obligation back-references`.

## 12. Unresolved-item audit: all twenty-two UR items

| Item | Subject | Status |
| --- | --- | --- |
| `UR-01` | I3 primary estimand identifiability | `VERIFIED_RESOLVED` |
| `UR-02` | I3 primary indicator semantics across JSON, Markdown and packet | `PARTIALLY_RESOLVED` |
| `UR-03` | Family B per-profile alpha not implemented | `VERIFIED_RESOLVED` |
| `UR-04` | false conservativeness assertion in the authoritative JSON | `VERIFIED_RESOLVED` |
| `UR-05` | paired size control over the feasible nuisance domain | `VERIFIED_RESOLVED` |
| `UR-06` | I3 primary floor 0.90 versus 0.95 and its feasibility | `VERIFIED_RESOLVED` |
| `UR-07` | I5 confirmation specification | `PARTIALLY_RESOLVED` |
| `UR-08` | development profile-selection rule | `PARTIALLY_RESOLVED` |
| `UR-09` | Family B denominator membership of S3 | `VERIFIED_RESOLVED` |
| `UR-10` | unit of every sample-size symbol | `PARTIALLY_RESOLVED` |
| `UR-11` | I1a and I1b power shortfall | `VERIFIED_RESOLVED` |
| `UR-12` | circular committed verification and the entrenched four-value grid test | `VERIFIED_RESOLVED` |
| `UR-13` | K5 and K6 stale generating-process text | `VERIFIED_RESOLVED` |
| `UR-14` | S3 projection self-contradiction and the undecomposed projection | `PARTIALLY_RESOLVED` |
| `UR-15` | I4 multiplicity across operation families and depths | `VERIFIED_RESOLVED` |
| `UR-16` | residual pooling paths across label alphabets and position-symbol cells | `VERIFIED_RESOLVED` |
| `UR-17` | degenerate I3 rejection region at n 128, p0 0.95 | `VERIFIED_RESOLVED` |
| `UR-18` | paired margin practical-irrelevance justification | `VERIFIED_RESOLVED` |
| `UR-19` | Clopper-Pearson and uniformity tail-convention naming | `VERIFIED_RESOLVED` |
| `UR-20` | positive-reference dossier D-07 versus D-04 attribution | `VERIFIED_RESOLVED` |
| `UR-21` | stale Gate I1 labels in checkpoint role records | `VERIFIED_RESOLVED` |
| `UR-22` | external-qualification-interface requirement for the positive reference | `CORRECTLY_RETAINED_AS_BLOCKING_OPERATOR_DECISION` |

**`UR-01` - `VERIFIED_RESOLVED`.** Closed with S3MR-001. The unit is the base-item contrast cluster with exactly two variants and the construction produces it; independently re-implemented and verified.

**`UR-02` - `PARTIALLY_RESOLVED`.** The three artifacts are reconciled to one named indicator, but the named indicator is identically J_cor, so the reconciliation settled the wording and not the construct. See S3MR2-001.

**`UR-03` - `VERIFIED_RESOLVED`.** 1/600 derives every development threshold and 1/200 every confirmation threshold; all ten reproduced independently from exact rationals, and 1/600 x 3 = 1/200 holds exactly.

**`UR-04` - `VERIFIED_RESOLVED`.** Withdrawn, not reworded; no surviving size claim in any artifact.

**`UR-05` - `VERIFIED_RESOLVED`.** Retirement rather than recalibration fully removes the size-control defect, because no paired aggregate-equivalence decision remains whose size could be uncontrolled. The reviewer answers the drafting party's first question in the affirmative: no residual decision path remains.

**`UR-06` - `VERIFIED_RESOLVED`.** One active floor; 0.95 absent from every active numeric field; separable at n = 256 with power 0.953040775212 and a non-degenerate region.

**`UR-07` - `PARTIALLY_RESOLVED`.** I5 is fully specified and its thresholds were independently reproduced, but its applicability rows admit the never-selectable profile S4 and its joint operating characteristic is unstated. See S3MR2-004 and S3MR2-002.

**`UR-08` - `PARTIALLY_RESOLVED`.** The map is published, total, deterministic and independently reproduced in all sixteen rows, but it cannot return STOP_INSTRUMENT_DEFECT and conflicts with the registered I0 failure semantics. See S3MR2-006.

**`UR-09` - `VERIFIED_RESOLVED`.** Fixed at the integer 3 before data, constant across all sixteen enumerated rows, conservative when S3 is skipped.

**`UR-10` - `PARTIALLY_RESOLVED`.** The registry exists and every binomial row carries its unit, but the I0 fixture stream files a rendered-row count under the base_item unit. See S3MR2-009.

**`UR-11` - `VERIFIED_RESOLVED`.** n = 256 is independently confirmed to be the smallest admissible size meeting the per-cell target at 1/600; n = 192 is withdrawn; p1 unmoved.

**`UR-12` - `VERIFIED_RESOLVED`.** Both deleted with the procedure they supported; an AST anti-transcription audit replaces the grid test. The reviewer modified neither existing Study 3 test module.

**`UR-13` - `VERIFIED_RESOLVED`.** Both data_generating_process fields now describe the constructions actually adopted; independently verified against the re-implemented construction.

**`UR-14` - `PARTIALLY_RESOLVED`.** S3's zero incremental cost is correct under the four registered preconditions and the six-stream decomposition reconstructs from primitives, but the S4 stream still leaves forward passes unmapped. See S3MR2-005.

**`UR-15` - `VERIFIED_RESOLVED`.** I4 is evaluated in four separate operation-family x depth cells with pooling prohibited, and the cells enter the within-profile intersection-union conjunction at the registered component level.

**`UR-16` - `VERIFIED_RESOLVED`.** Twelve pooling prohibitions are registered and explicitly name pooling across label alphabets, pooling the K5 position cells with the K5 symbol cells, pooling contrast IDs, pooling the three I3 indicators and pooling across splits.

**`UR-17` - `VERIFIED_RESOLVED`.** pass_count < n strictly in all ten active rows; the degenerate configuration is removed from the active design.

**`UR-18` - `VERIFIED_RESOLVED`.** No equivalence margin survives in any decision role, so there is no margin left to justify. The obligation is discharged by removal.

**`UR-19` - `VERIFIED_RESOLVED`.** Both tables name their tail convention at the point of tabulation and the lower-tail mass is exactly half the two-sided simultaneous mass.

**`UR-20` - `VERIFIED_RESOLVED`.** The obligation is attributed to D-04; remaining D-07 mentions are disambiguating narrative.

**`UR-21` - `VERIFIED_RESOLVED`.** Every role record uses post-split gate names with per-profile applicability.

**`UR-22` - `CORRECTLY_RETAINED_AS_BLOCKING_OPERATOR_DECISION`.** The canonical qualification interface cannot be registered without deciding which checkpoint the positive reference is, and that decision is OD2, which draft-v0.3 deliberately does not attempt. The circularity requirement itself is registered - the qualification interface must not be S1, S2, S3 or S4 and the P3-Q items must be disjoint from the I4 items - so what remains open is the operator choice, not a missing methods definition. This is the only item for which this status is used.

## 13. New findings

| Finding | Severity | Title |
| --- | --- | --- |
| `S3MR2-001` | BLOCKING | The I3 primary indicator is mathematically identical to joint correctness and identifies no presentation effect, while the protocol's registered constructs, gate question and claim ceiling require a presentation-effect estimand |
| `S3MR2-002` | BLOCKING | Profile-level, selection-level and confirmation-level power are neither derived nor registered anywhere, while an unqualified study-level target power of 9/10 is published and every component row asserts that it is met |
| `S3MR2-003` | MAJOR | Gate I4's applicability to the never-selectable profile S4 is asserted in three artifacts and denied in two, and the operation projection silently follows the denial |
| `S3MR2-004` | MAJOR | Every confirmation exact-binomial row admits the never-selectable profile S4, and I1b's confirmation row admits S4, although confirmation is entered only by a development-selected profile |
| `S3MR2-005` | MAJOR | The S4 diagnostic generation stream publishes a null forward-pass count beside 16,128 generations and a 258,048 generated-token bound, so the dominant cost of the only generative stream is unmapped |
| `S3MR2-006` | MAJOR | An I0 failure has two different registered legal next states, and the published executable selection map cannot return the registered stop state STOP_INSTRUMENT_DEFECT |
| `S3MR2-007` | MAJOR | Gate I4's null is registered as a fixed number while the P3-Q competence floor that makes it interpretable is deferred to OD2, and no ordering constraint between them is registered |
| `S3MR2-008` | MINOR | The registered I3 claim ceiling is stated over nine contrast cells and overstates what a non-label-bearing profile can support |
| `S3MR2-009` | MINOR | The deterministic I0 fixture stream files a rendered-row count under the base_item unit, contrary to the unit registry introduced to repair S3MR-014 |
| `S3MR2-010` | MAJOR | No artifact states the stochastic model that makes the exact binomial test valid, and the registered construction is deterministic with no draw mechanism, so the superpopulation warrant does not yet exist |

### `S3MR2-001` - BLOCKING

**The I3 primary indicator is mathematically identical to joint correctness and identifies no presentation effect, while the protocol's registered constructs, gate question and claim ceiling require a presentation-effect estimand**

The reviewer enumerated the full ordered 4 x 4 outcome lattice over {correct, wrong_a, wrong_b, invalid} and established that J_cor = 1 implies J_inv = 1 in every case, because two outputs that both equal a unique registered ground truth are necessarily valid and necessarily equal to each other. J_both is therefore identically J_cor, and the registered estimand Pr(J_both = 1) is exactly the probability that both variants of a cluster are answered correctly. That quantity is a LEVEL of joint correctness. It is not a contrast, a difference, a ratio or an equivalence statement between the baseline and the transformed presentation, so it cannot identify a presentation effect in either direction. The protocol nevertheless registers constructs that are explicitly about movement: VT6 is justified by accuracy gaps of roughly 13 to 85 percent under option reordering and states that an instrument whose reading MOVES that much with an irrelevant transformation is not measuring the intended quantity; VT7 is justified by individual-question accuracy being UNSTABLE under knowledge-equivalent rewrites; the I3 gate question asks whether the checkpoint gives the same correct answer when one presentation aspect changes; the I3 what_fails clause names 'answers move with presentation' as a failure mode; and the research question asks whether competence is recovered ROBUSTLY ACROSS permutations, positions and renderings. The reviewer's counterexamples show the two are not the same quantity. A process with baseline accuracy 1.00 and transformed accuracy 0.98 under nested failures has Pr(J_both = 1) = 0.98, which reaches the registered lowest alternative of interest p1 = 0.97 and passes comfortably, despite a real two-point presentation decrement. A process with baseline 1.00 and transformed 0.91 has Pr(J_both = 1) = 0.91, which already falsifies the registered null p <= 0.90, despite a nine-point decrement. Conversely a process with perfect invariance and zero presentation effect at accuracy 0.85 has Pr(J_both = 1) = 0.85 and fails. The gate therefore passes processes that do move with presentation and fails processes that do not, which is the opposite of the registered construct. Retiring all paired effect and equivalence inference in response to S3MR-004 and S3MR-005 was correct for size control, but it left the presentation-effect construct with no estimand at all, and the conjunction that replaced it is redundant rather than compensating. The drafting party discloses the implication J_cor implies J_inv in expected_integrity_invariant and defends the conjunction as legibility, which is candid, but legibility does not restore an estimand.

**Consequence.** The permitted claim ceiling is narrower than the claim language the protocol uses. What Pr(J_both = 1) supports is a joint robust-correctness floor: 'in this contrast cell, at least this proportion of base items were answered correctly under BOTH the registered baseline and the registered transformed presentation.' It does not support any claim that a registered presentation factor does or does not move the instrument's reading, and it does not support the VT6 or VT7 constructs as those are justified in the protocol. Because the study's decision unit is an interface profile whose adequacy is defined partly by presentation robustness, this is not a labelling nicety: an interface can be certified adequate while carrying exactly the sensitivity the study exists to detect.

**Repair class.** SUBSTANTIVE_REDESIGN_REQUIRED: either register a presentation-effect or equivalence estimand with its own size-controlled procedure, which is a new statistical family and must not silently reinstate the retired paired procedure, or narrow VT6, VT7, the research question, the I3 gate question, the I3 what_fails clause and the i3_claim_ceiling to a joint robust-correctness floor. Either path changes the estimand or the claim ceiling, so neither is a bounded conformance edit.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/analysis/independent_methods_review_packet_v0_3.md`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `proposed_statistics.i3_indicators.J_both.definition`, `proposed_statistics.i3_indicators.J_both.estimand`, `gate_hierarchy[I3].question`, `gate_hierarchy[I3].what_fails`, `claim_ceiling.i3_claim_ceiling`, `validation_targets[VT6].why_needed`, `validation_targets[VT7].why_needed`, `research_question.draft_question`, `i3_outcome_lattice.j_both_is_mathematically_identical_to_j_cor`.

### `S3MR2-002` - BLOCKING

**Profile-level, selection-level and confirmation-level power are neither derived nor registered anywhere, while an unqualified study-level target power of 9/10 is published and every component row asserts that it is met**

The protocol publishes target power in the same exact-rational policy table as the study-level screening level and the per-profile component level. Every other row in that table carries an explicit scope word - 'study-level', 'per-profile', 'confirmation component' - and the target power row carries none. Its only implementation anywhere is a per-cell assertion: design_statistics.py defines a single TARGET_POWER and checks it once per emitted row, and there is no function, field, table or artifact in the reviewed object that derives the power of a gate family, of a profile's eligibility conjunction, of the selection map returning a winner, or of the one-shot confirmation conjunction. The reviewer therefore derived them independently. Counting gate-bearing cells from the registered evaluated_per factor structure gives, per selectable profile and split, 33 cells at n = 256 against p0 = 9/10 for S1 (3 I1a, 3 I1b, 27 I3 over three target roles and nine contrast cells), 6 I2 cells and 4 I4 cells, for 43 cells; and 9, 6 and 4 for S2 and S3, for 19 cells. Because the within-profile rule is an intersection-union conjunction, an eligible profile must reject in EVERY one of those cells. At exactly the registered lowest alternative of interest in every cell, the illustrative joint probabilities under an explicitly stated independence assumption are 0.100885944 for S1 development and 0.320003768 for S2 and S3 development, and 0.330544875 and 0.587941985 for the corresponding confirmation conjunctions, giving end-to-end development-then-confirmation success probabilities of 0.033347332 and 0.188143651. Under arbitrary dependence only the Frechet bounds are available and they are wider still: the worst-case lower bound is 0.000000000 for S1 development and for S1 confirmation, and 0.476450020 for the S2 and S3 confirmation conjunction, with an upper bound of 0.921083515 given by the weakest single cell. The reviewer does not assume independence; both the bound and the illustrative value are reported, and neither reaches 9/10.

**Consequence.** The published operating characteristic is wrong by an order of magnitude at the level at which the study actually decides. A reader of the exact-rational policy table is told the design has power 9/10; the design's probability of qualifying a genuinely adequate interface at the registered alternative is between 0.10 and 0.32 at development, and its probability of completing development and confirmation is between 0.03 and 0.19. A study with those characteristics will most often return STOP_NO_SELECTABLE_INTERFACE_REMAINS even when a registered-adequate interface exists, and under the registered claim ceiling that outcome would be reported as 'no candidate interface met the registered gates', which is a materially misleading statement about the panel. The defect is a feasibility defect, not only a labelling defect.

**Repair class.** SUBSTANTIVE_REDESIGN_REQUIRED: the amendment must choose and register a family-level power target and re-derive sizes or gate structure against it, or explicitly register the per-cell scope of the 9/10 target together with the derived profile-level, selection-level and confirmation-level operating characteristics and accept them on the record. The first changes sample sizes; the second changes the registered power semantics and the claim the study may make about a stop outcome. The reviewer does not choose between them and does not inflate n or weaken any gate.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/protocol/interface_calibration_protocol_draft.md`, `studies/study3/analysis/design_statistics.py`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `proposed_statistics.target_power`, `declared_assumptions.target_power`, `development_exact_binomial_components[*].meets_target_power`, `confirmation_exact_binomial_components[*].meets_target_power`, `power_structure.profile_level`, `gate_bearing_cell_counts`.

### `S3MR2-003` - MAJOR

**Gate I4's applicability to the never-selectable profile S4 is asserted in three artifacts and denied in two, and the operation projection silently follows the denial**

retained_exact_binomial_gates[I4].applicable_profiles lists S1, S2, S3 and S4; the confirmation row lists the same four; and gate_hierarchy[I4] both lists all four profiles and states explicitly 'none; I4 applies to every profile' as its not_applicable semantics. Against that, gate_truth_table.rows records I4 as not_applicable for S4 with the note that S4 is a never-selectable diagnostic excluded from every success union, and stage_1_component_evaluation.components_by_profile.S4.applicable lists I0, I1a, I1b, I2, I3_K5 and I3_K6 and omits I4 entirely. The operation projection follows the denial without saying so: RP_I4_under_candidate_profiles.by_profile contains S1, S2 and S3 only. The reviewer derived the arithmetic consequence independently from primitive counts: four operation-family x depth cells at n = 256 give 1,024 RP rows per profile, so the published 2,048 accounts for S1 and S2 with S3 free-riding on S2, whereas genuine S4 applicability would require 3,072, a difference of 1,024 scored rows and 1,024 forward passes. This is not a single stray field; the contradiction is duplicated across the authoritative JSON's gate hierarchy, both exact-binomial tables and the derived tables artifact.

**Consequence.** Applicability is a decision-bearing field: it determines which atomic cells a profile must pass and which cells enter the intersection-union conjunction. Because S4 can never be selected, no selection outcome changes either way, so the reviewer does not classify this as blocking. It nevertheless leaves the feasibility projection unreconcilable against the registered applicability, and it leaves a reader unable to determine from the authoritative artifact whether an S4 I4 cell exists.

**Repair class.** BOUNDED_CONFORMANCE_EDIT_IF_TAKEN_ALONE: choose one reading and reconcile all five locations plus the projection. The reviewer notes that the not-applicable reading is the coherent one, because I4 exists to license attributing a target failure to the target rather than the interface, which is meaningless for a profile that can never be selected.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `retained_exact_binomial_gates[I4].applicable_profiles`, `confirmation_exact_binomial_gates[I4].applicable_profiles`, `gate_hierarchy[I4].applicable_profiles`, `gate_hierarchy[I4].not_applicable_semantics`, `gate_truth_table.rows[S4].I4`, `development_selection_and_confirmation_plan.stage_1_component_evaluation.components_by_profile.S4.applicable`, `operation_boundaries.projected_future_operations.work_streams.RP_I4_under_candidate_profiles.by_profile`.

### `S3MR2-004` - MAJOR

**Every confirmation exact-binomial row admits the never-selectable profile S4, and I1b's confirmation row admits S4, although confirmation is entered only by a development-selected profile**

All five confirmation rows in both the protocol and the derived tables carry applicable_profiles containing S4, and the confirmation I1b row carries ['S1', 'S4']. The confirmation lifecycle states the opposite in three places: stage_3_confirmation.entered_by is 'exactly one profile, returned by stage 2', stage_2_selection.never_selectable is ['S4'], and gate_hierarchy[I5].applicable_profiles is 'the single development-selected interface profile only'. No S4 confirmation cell can exist under any outcome of the sixteen-row map, which the reviewer independently enumerated and confirmed never returns S4.

**Consequence.** The confirmation applicability fields describe cells that are unreachable by construction. The error cannot change an error rate, because the unreachable cells are never evaluated, but it makes the confirmation coverage requirement ambiguous: I5 must cover every gate-bearing construct in every applicable atomic cell, and an applicability list that includes an impossible profile leaves the required cell set undetermined on its face.

**Repair class.** BOUNDED_CONFORMANCE_EDIT_IF_TAKEN_ALONE: remove S4 from every confirmation applicability list, or register explicitly that confirmation applicability is the intersection of the listed profiles with the single selected profile.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`. Fields: `confirmation_exact_binomial_gates[*].applicable_profiles`, `confirmation_exact_binomial_components[*].applicable_profiles`, `gate_hierarchy[I5].applicable_profiles`, `development_selection_and_confirmation_plan.stage_2_selection.never_selectable`, `development_selection_and_confirmation_plan.stage_3_confirmation.entered_by`.

### `S3MR2-005` - MAJOR

**The S4 diagnostic generation stream publishes a null forward-pass count beside 16,128 generations and a 258,048 generated-token bound, so the dominant cost of the only generative stream is unmapped**

The stream declares uses_model true, 16,128 rendered rows, 16,128 generations, a registered bound of 16 generated tokens per row and a 258,048 generated-token upper bound, which the reviewer reconstructed independently as 5,376 rendered rows per target role times three roles times 16 tokens. It then declares forward_passes = null. Autoregressive decoding is not free of forward passes: emitting t tokens costs at least t forward evaluations of the model, so a bound of 16 tokens per row implies an upper bound of 258,048 decode-step forward evaluations for this stream alone, against 20,736 for all of target-role development. A null in that field is not the same statement as the correctly-null P3-Q stream, where null records an undecided operator choice; here every input needed to bound the quantity is already published. The repository operation ontology has no category that maps a decoding step onto a forward pass, which is why the quantity could be left unmapped rather than bounded.

**Consequence.** The feasibility question the projection exists to answer cannot be answered for the stream that dominates it. This is the specific defect S3MR-013 recorded - forward passes, sequence scorings and generations being different operations with different costs - surviving in one stream, so the six-stream decomposition is not yet sufficient for the next operator decision.

**Repair class.** BOUNDED_CONFORMANCE_EDIT_IF_TAKEN_ALONE: publish either a decode-step count or an explicit forward-pass-equivalent bound for the S4 stream, and register a decode-step category in the operation ontology so that generations, generated tokens and forward passes are reconcilable rather than merely reported side by side.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_review_packet_v0_3.md`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `operation_boundaries.projected_future_operations.work_streams.S4_diagnostic_generation.forward_passes`, `operation_boundaries.projected_future_operations.work_streams.S4_diagnostic_generation.generations`, `operation_boundaries.projected_future_operations.work_streams.S4_diagnostic_generation.generated_tokens_upper_bound`, `operation_boundaries.projected_future_operations.work_streams.S4_diagnostic_generation.registered_generated_token_bound_per_row`, `operation_projection.S4_diagnostic_generation.forward_pass_accounting_gap`.

### `S3MR2-006` - MAJOR

**An I0 failure has two different registered legal next states, and the published executable selection map cannot return the registered stop state STOP_INSTRUMENT_DEFECT**

gate_hierarchy[I0] registers the instrument-integrity gate with legal_next_state_on_fail = 'STOP; fix the instrument and restart the gate sequence from I0', which is a global halt with a restart. stage_1_component_evaluation lists I0 among the applicable components of every profile and rules that a profile passes stage 1 only if every applicable component passes, which makes an I0 failure a per-profile elimination. The published sixteen-row selection map takes a single aggregated boolean per profile - 'all applicable components passed' - so an I0 failure is indistinguishable from an adequacy failure once it enters the map. The reviewer's independently authored resolver reproduces all sixteen rows and confirms the map is total and deterministic over its enumerated inputs, but its entire output range is {select S1, select S2, select S3, STOP_NO_SELECTABLE_INTERFACE_REMAINS}: two of the four registered legal stop states, STOP_INSTRUMENT_DEFECT and STOP_AWAITING_AUTHORITY, are unreachable from it, and STOP_CONFIRMATION_FAILED belongs to a later stage.

**Consequence.** The requirement that every selection, stop, inapplicability and error state has exactly one legal next state does not hold: the single event 'I0 fails for profile S1' has one next state under gate_hierarchy and a different one under stage 1 and the map. The scientific consequence is a wrong published conclusion in a reachable branch: a broken renderer or scorer would be reported through the map as STOP_NO_SELECTABLE_INTERFACE_REMAINS, whose registered claim is 'no candidate interface met the registered gates', when the correct statement is that the instrument is defective and nothing about the interfaces was measured.

**Repair class.** BOUNDED_CONFORMANCE_EDIT_IF_TAKEN_ALONE: separate I0 from the stage-1 adequacy conjunction and give the map an explicit instrument-defect input and an explicit STOP_INSTRUMENT_DEFECT output, so that the four registered stop states are reachable and each event has exactly one next state.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/design_statistics_tables.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `gate_hierarchy[I0].legal_next_state_on_fail`, `development_selection_and_confirmation_plan.stage_1_component_evaluation.rule`, `development_selection_and_confirmation_plan.stage_1_component_evaluation.components_by_profile.S1.applicable`, `gate_truth_table.legal_stop_states`, `development_selection_map[*]`, `development_selection_map.map_is_deterministic_one_legal_next_state`.

### `S3MR2-007` - MAJOR

**Gate I4's null is registered as a fixed number while the P3-Q competence floor that makes it interpretable is deferred to OD2, and no ordering constraint between them is registered**

I4 registers p0 = 4/5 and p1 = 9/10 with n = 256 per operation-family x depth cell, and the reviewer independently reproduced its threshold 224 of 256 and power 0.921083514878. The generic method is therefore internally defined without OD2: nothing in the exact binomial computation depends on which checkpoint the positive reference is. What is not defined is the relation between that null and the prequalification floor. The protocol states that the competence floor for stage P3-Q 'is carried by OD2 together with the canonical qualification interface, and is not set by draft-v0.3', and that the draft-v0.1 chance-level floor is rejected and not reinstated. No registered constraint ties the two numbers together. If a later OD2 authority qualifies a reference at a floor at or below 0.80 on the K4 construct through the canonical interface, then a reference can be 'independently prequalified' and still be structurally unable to exceed p0 = 0.80 through ANY candidate interface, in which case an I4 failure measures the reference rather than the interface and inverts the construct the gate exists to serve. If the floor is set far above 0.90 the gate becomes close to vacuous.

**Consequence.** OD2 remaining open does not by itself make I4 undefined and the reviewer does not treat it as blocking. But the gate's interpretability, and therefore the attribution licence that the whole positive-control design rests on, depends on a relation that no artifact registers. The later OD2 authority must freeze at minimum: the checkpoint identity and immutable revision; the canonical qualification interface, which must not be S1, S2, S3 or S4; the RP-specific I4 wrapper; the prequalification bank and its isolation from both the development and the confirmation seeds; the P3-Q competence floor and its relation to I4's p0 and p1; n; alpha; the rejection rule; the operation-family and depth treatment; the stopping rule; and the provenance record. No checkpoint is selected, preferred, pinned, revision-resolved, downloaded, tokenized, loaded, run or prequalified by this review.

**Repair class.** OPERATOR_DECISION_INPUT: register the ordering constraint between the P3-Q floor and I4's p0 and p1 as part of the OD2 resolution. Choosing the constraint is a substantive decision and is not a conformance edit.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`. Fields: `retained_exact_binomial_gates[I4].p0_exact_rational`, `retained_exact_binomial_gates[I4].p1_exact_rational`, `positive_reference_candidates.prequalification_stage_proposal.floor`, `positive_reference_candidates.circularity_rule.canonical_interface_status`, `unresolved_operator_decisions[OD2].blocks`.

### `S3MR2-008` - MINOR

**The registered I3 claim ceiling is stated over nine contrast cells and overstates what a non-label-bearing profile can support**

The claim ceiling states that gate I3 registers nine one-factor pairwise contrast cells and that passing all of them supports a claim about each registered presentation factor separately. For S2 and S3 the seven K5 cells are not_applicable, so only the two K6 cells - separator and instruction wording - are ever evaluated. A passing S2 or S3 therefore supports a claim about two registered presentation factors, not about each of them, and the protocol's own not_applicable semantics forbid reading the seven unevaluated cells as evidence of robustness. The claim ceiling as written does not carry the per-profile qualification that the applicability rules require.

**Consequence.** A reader could take a passing non-label-bearing profile to have demonstrated position and symbol-permutation robustness that was never evaluated for it, which is precisely the not_applicable-as-pass error the protocol elsewhere prohibits.

**Repair class.** BOUNDED_CONFORMANCE_EDIT: qualify the I3 claim ceiling per profile, stating that it covers the applicable contrast cells of the profile in question and naming which those are.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/protocol/interface_calibration_protocol_draft.md`. Fields: `claim_ceiling.i3_claim_ceiling`, `gate_hierarchy[I3].claim_ceiling`, `i3_contrast_registry.k5_applicability`, `gate_truth_table.rows[S2].I3_K5`.

### `S3MR2-009` - MINOR

**The deterministic I0 fixture stream files a rendered-row count under the base_item unit, contrary to the unit registry introduced to repair S3MR-014**

The stream publishes base_item_contrast_clusters = 232 and base_items = 464. Under the registered unit definitions one base_item_contrast_cluster is ONE base item rendered in exactly two variants, so 232 clusters imply 232 base items and 464 rendered rows. The reviewer confirmed the arithmetic from the published breakdown: the k5 and k6 constructor fixtures are 448 + 16 = 464, which is exactly 232 x 2, and the remaining 38 scorer, not_applicable and indicator fixtures bring the stream to its declared 502 rendered rows. The value 464 is therefore a rendered-row count carrying the base_item label. The convention used by every other stream is the opposite: S1 publishes base_items = 768, which is exactly the 256 + 256 + 256 independent units of the base_item-typed components, and counts its clusters separately. The registered dimensional identity rendered_rows = clusters x 2 is asserted only for the four I3 components, so this stream escapes the check that would have detected it.

**Consequence.** No decision, threshold, level or gate outcome depends on this stream, which is deterministic, model-free and carries no statistical test, so the consequence is confined to the unit discipline that S3MR-014 was raised to establish.

**Repair class.** BOUNDED_CONFORMANCE_EDIT: publish base_items = 232 for the cluster-derived fixtures and account the 38 non-cluster fixture rows separately, or extend the dimensional-identity assertion to every stream that reports clusters.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `operation_boundaries.projected_future_operations.work_streams.deterministic_I0_fixtures.base_items`, `operation_boundaries.projected_future_operations.work_streams.deterministic_I0_fixtures.base_item_contrast_clusters`, `unit_registry.units`, `unit_registry.prohibition`, `operation_boundaries.projected_future_operations.dimensional_identities`.

### `S3MR2-010` - MAJOR

**No artifact states the stochastic model that makes the exact binomial test valid, and the registered construction is deterministic with no draw mechanism, so the superpopulation warrant does not yet exist**

An exact one-sided binomial test of H0: p <= p0 is licensed by the Clopper and Pearson (1934) sampling model: the n units in a cell are independent Bernoulli trials with a common success probability p, or a justified worst-case reduction to that case. The reviewer looked for the registered warrant for that model and found none. The protocol registers the test, the level, the size and the rejection rule, but no artifact states the superpopulation from which base items are drawn, the draw mechanism, the with-or-without-replacement rule, or the exchangeability argument. What it does state points the other way: the construction algorithm declares 'randomness: none anywhere in this design round; every condition is a fixed function of the registered base-item index and the registered contrast ID, no seed is drawn, and no random draw appears at any point', and bank_construction_policy records zero rows generated, zero seeds drawn and defers the seed draw to a separate future operator authority. The model side is deterministic too: on S1, S2 and S3 the score is an argmax over a restricted vocabulary at one position with a registered deterministic tie-break, so a given item under a given checkpoint yields a fixed outcome with no sampling variability. The ONLY possible source of the randomness the binomial model requires is therefore the item draw, and that draw does not yet exist. If the future bank is enumerated as a fixed finite census of the registered strata, or generated as a deterministic function of item indices in the same way the conditions are, then there is no random draw at all, every reported rate is a population quantity rather than an estimate, and binomial inference has no warrant: the correct reading would be finite-population, or descriptive, not a hypothesis test. A further threat is clustering that the current unit definitions do not neutralise. The registered cluster rule keeps a base item and all its variants in one split, which is correct, and the protocol claims base-item identities are disjoint across contrast cells; the reviewer verified the counts are consistent with that claim, since S1 needs 768 base-item units for I1a, I1b and I2 plus 2,304 distinct cluster stems for the nine I3 cells. But base items generated from shared templates, shared operation families, shared depth or shared strata are not thereby independent, nothing registers a template-level or family-level independence requirement, and no artifact states whether items are reused across the three target roles or across interface profiles, which are the comparisons the study is built on.

**Consequence.** Every threshold, level, size and power figure in the design is conditional on a sampling model that is not registered anywhere, so the exact-binomial architecture is not yet executable as an inference. The Bonferroni union bound across profiles is unaffected, because it holds under arbitrary dependence, and the intersection-union bound within a profile is unaffected for the same reason; what is affected is the component-level size and power of every individual cell, which is the foundation both bounds sit on.

**Repair class.** SUBSTANTIVE_AMENDMENT_REQUIRED: the amendment must register the stochastic model explicitly - the superpopulation or generating process, the independent unit, the draw mechanism and its seed authority, the with-or-without-replacement rule, the template, family and depth clustering treatment, and whether items are reused across roles and profiles - or, if the bank is to be a fixed finite census or a deterministic enumeration, replace the binomial hypothesis tests with a finite-population, clustered or explicitly descriptive treatment. Choosing between these is a substantive design decision and is not a conformance edit. It must be settled before freeze, not at freeze.

Evidence: `studies/study3/protocol/interface_calibration_protocol_draft.json`, `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`. Fields: `bank_construction_policy.rows_generated_this_round`, `bank_construction_policy.seeds_drawn_this_round`, `bank_construction_policy.future_seed_draw_procedure`, `counterbalancing_design.construction_algorithm.randomness`, `atomic_evaluation_cells.i3_sampling_unit.disjoint_base_items`, `proposed_statistics.framework`, `split_lifecycle.splits`.

## 14. Cross-artifact consistency

| Candidate | Status | Findings |
| --- | --- | --- |
| J_both semantics and claim language | `CONFIRMED_BLOCKING` | S3MR2-001 |
| per-cell versus joint power labels | `CONFIRMED_BLOCKING` | S3MR2-002 |
| S4 I4 applicability versus accounting | `CONFIRMED_MAJOR` | S3MR2-003 |
| S4 forward-pass null versus token and generation bounds | `CONFIRMED_MAJOR` | S3MR2-005 |
| S3 profile versus Study 3 wording in the zero-incremental-cost statement | `NOT_CONFIRMED` | - |
| sample-frame and binomial assumptions | `CONFIRMED_MAJOR` | S3MR2-010 |
| all 20 inherited repair claims | `QUALIFIED` | - |
| all 22 UR dispositions | `QUALIFIED` | - |
| OD2 blocking state | `CONFIRMED_NONBLOCKING` | S3MR2-007 |
| zero-operation and no-evidence boundaries | `CONFIRMED_NONBLOCKING` | - |
| I0 failure next state | `CONFIRMED_MAJOR` | S3MR2-006 |
| confirmation applicability admits a never-selectable profile | `CONFIRMED_MAJOR` | S3MR2-004 |
| I3 claim ceiling stated over nine cells for every profile | `CONFIRMED_MINOR` | S3MR2-008 |
| I0 fixture stream unit discipline | `CONFIRMED_MINOR` | S3MR2-009 |
| exact-binomial thresholds, tails and powers across protocol, tables, packet and Markdown | `NOT_CONFIRMED` | - |
| sixteen-row selection map across protocol and derived tables | `NOT_CONFIRMED` | - |

- **J_both semantics and claim language** - `CONFIRMED_BLOCKING`. The estimand field is accurate; the construct string, gate question, what_fails clause and claim ceiling describe a presentation contrast the estimand does not identify.
- **per-cell versus joint power labels** - `CONFIRMED_BLOCKING`. An unqualified study-level target power row sits beside scope-qualified alpha rows and is verified only per cell; no artifact derives any joint power.
- **S4 I4 applicability versus accounting** - `CONFIRMED_MAJOR`. Three artifacts assert applicability, two deny it, and the projection follows the denial; the arithmetic gap is 1,024 scored rows.
- **S4 forward-pass null versus token and generation bounds** - `CONFIRMED_MAJOR`. Every input needed to bound the quantity is published, so the null is an unmapped cost rather than an undecided operator choice.
- **S3 profile versus Study 3 wording in the zero-incremental-cost statement** - `NOT_CONFIRMED`. The reviewer searched every routing, protocol, packet and amendment artifact for a statement that Study 3 adds zero forward passes and found none. The subject is the S3 interface profile in every occurrence, and the S3-versus-S2 scope is stated explicitly. This candidate is not confirmed.
- **sample-frame and binomial assumptions** - `CONFIRMED_MAJOR`. See the binomial_sampling_model decision; the superpopulation warrant is deferred to a bank authority that does not yet exist.
- **all 20 inherited repair claims** - `QUALIFIED`. Fourteen of the twenty are verified resolved on independent evidence; four are partially resolved; none is adjudicated on the drafting party's PROPOSED_RESOLVED label. Two of the six inherited BLOCKING items are not verified resolved.
- **all 22 UR dispositions** - `QUALIFIED`. Sixteen verified resolved, five partially resolved, one correctly retained as a blocking operator decision.
- **OD2 blocking state** - `CONFIRMED_NONBLOCKING`. OD2 is consistently recorded unresolved and blocking in every artifact, no candidate is selected, and every dependent quantity is null rather than zero. The state is correct; the unregistered relation between the P3-Q floor and I4's null is recorded separately.
- **zero-operation and no-evidence boundaries** - `CONFIRMED_NONBLOCKING`. All 22 counters are zero, all eight authority flags are false, results, bank_rows and seeds are empty, and the evidence ledger is byte-identical at 25,241 bytes with 16 rows ending EV-0016.
- **I0 failure next state** - `CONFIRMED_MAJOR`. Two registered next states for one event; two of four registered stop states unreachable from the published map.
- **confirmation applicability admits a never-selectable profile** - `CONFIRMED_MAJOR`. Confirmation rows list S4 although the map can never return S4.
- **I3 claim ceiling stated over nine cells for every profile** - `CONFIRMED_MINOR`. Only two of the nine cells are applicable to S2 and S3.
- **I0 fixture stream unit discipline** - `CONFIRMED_MINOR`. 464 is a rendered-row count under the base_item label.
- **exact-binomial thresholds, tails and powers across protocol, tables, packet and Markdown** - `NOT_CONFIRMED`. All ten rows agree across all four artifacts and all ten reproduce exactly under the reviewer's independent integer-only derivation. No inconsistency exists here.
- **sixteen-row selection map across protocol and derived tables** - `NOT_CONFIRMED`. All sixteen rows agree and all sixteen are reproduced by the reviewer's independently authored resolver, including the three STOP rows and the constant denominator 3.

## 15. What is reviewed fact, reviewer inference, recommendation and open operator choice

- **Reviewed fact.** Every byte identity in section 0; every registered parameter quoted from the reviewed object; the presence or absence of a field, a decision path or a next-state rule.
- **Reviewer inference.** The independently derived thresholds, tails, powers, cell counts, joint-power values and operation reconstructions; the mathematical identity of `J_both` with `J_cor`; the unreachability of `STOP_INSTRUMENT_DEFECT` from the published map. These follow from the reviewed parameters by exact arithmetic and enumeration, and were derived before the drafting outputs were opened.
- **Recommendation.** The repair classes recorded with each finding. The reviewer does not choose a family-level power target, does not choose a presentation-effect estimand, does not inflate any sample size, does not weaken any gate and does not select a checkpoint.
- **Unresolved operator choice.** OD2 and UR-22, and the ordering constraint between the P3-Q competence floor and I4's null recorded in `S3MR2-007`.

## 16. Unresolved items, kept separate

### Unresolved methods items

| Item | Severity | Owner | Requires |
| --- | --- | --- | --- |
| `S3MR2-001` | BLOCKING | drafting party | a presentation-effect estimand with a size-controlled procedure, or a narrowed claim ceiling, gate question, what_fails clause and VT6/VT7 statement |
| `S3MR2-002` | BLOCKING | drafting party | a registered family-level power target with re-derived sizes or structure, or an explicit per-cell scoping of the 9/10 target together with the derived joint operating characteristics |
| `S3MR2-010` | MAJOR | drafting party | a registered stochastic model, or replacement of the binomial architecture with a finite-population, clustered or descriptive treatment |
| `S3MR2-003` | MAJOR | drafting party | one reading of S4 I4 applicability reconciled across five locations and the projection |
| `S3MR2-004` | MAJOR | drafting party | removal of S4 from every confirmation applicability list, or an explicit intersection rule |
| `S3MR2-005` | MAJOR | drafting party | a decode-step or forward-pass-equivalent bound for the S4 stream and a decode-step category in the operation ontology |
| `S3MR2-006` | MAJOR | drafting party | separation of I0 from the stage-1 adequacy conjunction and an explicit STOP_INSTRUMENT_DEFECT output in the selection map |
| `S3MR2-008` | MINOR | drafting party | a per-profile qualification of the I3 claim ceiling |
| `S3MR2-009` | MINOR | drafting party | base_items = 232 for the cluster-derived fixtures, or an extended dimensional identity |

### Unresolved operator items

| Item | Status | Owner | Subject |
| --- | --- | --- | --- |
| `OD2` | `UNRESOLVED_BLOCKING_OPERATOR_DECISION` | operator | which checkpoint serves as the positive reference and what canonical qualification wrapper it uses |
| `UR-22` | `UNRESOLVED_BLOCKING_OPERATOR_DECISION` | operator via OD2 | external canonical qualification interface for the positive reference |
| `S3MR2-007` | `OPERATOR_DECISION_INPUT` | operator via OD2 | the unregistered relation between the P3-Q competence floor and I4's p0 and p1 |

`OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`. It is not resolved, not advanced and not prejudged by this review, and it is deliberately not counted among the methods blockers.

## 17. Disposition

The three permitted dispositions are `STUDY3_V0_3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED`, `STUDY3_V0_3_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CHANGES` and `STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`. This review returns exactly one of them.

**STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED**

Two BLOCKING and eight MAJOR methods defects remain, and two of the six inherited BLOCKING findings are not verified resolved. Every valid repair identified by this review requires a substantive choice rather than a bounded conformance edit: S3MR2-001 requires either a new presentation-effect estimand or a narrowed claim ceiling; S3MR2-002 requires either a registered family-level power target with re-derived sizes or a re-registered per-cell power semantics; S3MR2-010 requires registering a stochastic model or replacing the binomial architecture. Under the review authority these are exactly the conditions that require an amendment round rather than acceptance with required changes.

Acceptance as specified is unavailable because two inherited BLOCKING items are not verified resolved and because blocking and major methods defects remain. Acceptance with required changes is unavailable because the required changes are not bounded and non-discretionary: they alter the estimand, the claim ceiling, the registered power semantics or the sampling frame, and the review authority reserves those for an amendment round.

**Only legal successor action:** `OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_4`, then a further independent methods review. The only legal successor action under this disposition is an operator amendment round producing draft-v0.4, followed by another independent methods review. No freeze, no P3-Q, no bank construction, no seed draw, no model execution, no development, no confirmation access and no mechanistic work is authorized by this review, and this review creates no execution authority.

No successor prompt is created in this round.

## 18. Claim ceiling, state and operation boundary

- Study 1 remains closed at `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`.
- Study 2 remains closed at `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`.
- Study 3 remains unfrozen.
- No interface or positive reference is selected.
- No bank, seed, model operation, gate result, confirmation access or evidence row exists.
- The original research question remains unanswered.
- No freeze or execution authority was created by this review.

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

Study 3 remains an unfrozen design. No interface profile and no positive reference is selected. No bank, seed, model operation, gate result, confirmation access or evidence row exists. Every operation counter is zero and every authority flag is false. The original research question remains unanswered. Neither this documentation state nor this disposition is a scientific result or an execution authority.
