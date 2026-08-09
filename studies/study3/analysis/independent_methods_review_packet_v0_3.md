# Study 3 draft-v0.3 independent methods review packet

**State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_3_COMPLETE_AWAITING_SECOND_INDEPENDENT_METHODS_REVIEW`

This packet is the review object for the **second** bounded independent methods
review of the Study 3 interface-calibration protocol. It supersedes
`studies/study3/analysis/independent_methods_review_packet.md`, which remains
committed, unedited, as the exact object the first reviewer reviewed.

Nothing in this packet is a measurement. No model was downloaded, loaded, tokenized,
run, scored, generated from, probed, patched or ablated to produce it. Every operation
counter is exactly zero.

## 0. What the reviewer is asked to do

The first independent methods review returned
`STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` with 6 BLOCKING, 11 MAJOR and
3 MINOR findings. The drafting party has amended the design. The amendment record is
`studies/study3/reviews/v0_3_operator_amendment.md`.

**The drafting party does not claim the amended protocol is correct.** Every repair is
recorded as `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW`. The
determination belongs to the reviewer.

Specific questions the drafting party puts to the reviewer:

1. Does retiring the paired aggregate-equivalence procedure from every decision role fully remove the size-control defect recorded in S3MR-004 and S3MR-005, or does a residual decision path remain anywhere in the amended protocol?
2. Is the base-item contrast cluster with exactly two variants an identifiable unit for the I3 estimand under every registered contrast cell, and does the J_both conjunction estimate what the protocol says it estimates?
3. Is the intersection-union treatment within a profile, combined with a fixed denominator of 3 across profiles and a one-shot confirmation at 1/200 on a physically disjoint split, an adequate multiplicity architecture for the claim the protocol permits?
4. Does the six-stream operation projection make the feasibility question answerable, and is the zero-incremental-cost argument for S3 under a single-token answer domain correct as stated?
5. Are any of the twenty repairs above cosmetic relabelling rather than substantive design change?

## 1. Units

Finding `S3MR-014` recorded that the symbol `n` changed unit between artifacts and
that no artifact declared its unit. Four units are now registered and every `n` in
this packet carries one of them.

| Unit | Definition | Never equals |
| --- | --- | --- |
| `base_item` | one registered question stem with its registered ground truth; the independent sampling unit for I1a, I1b, I2 and I4 | `rendered_row`, `scored_row`, `base_item_contrast_cluster` |
| `base_item_contrast_cluster` | one base item rendered in exactly two registered variants, a registered baseline and one registered content-equivalent transformed presentation; the independent sampling unit for I3 | `base_item`, `rendered_row`, `scored_row` |
| `rendered_row` | one emitted presentation of one variant; a cluster always produces exactly two rendered rows | `base_item`, `base_item_contrast_cluster`, `scored_row` |
| `scored_row` | one rendered row scored under one (interface profile, checkpoint role) pair | `base_item`, `base_item_contrast_cluster`, `rendered_row` |

**Prohibition.** n is always the count of independent units in one atomic cell. It is never a rendered-row count and never a scored-row count. A table that reports n without naming its unit is a defect.

## 2. The exact rational multiplicity policy

Finding `S3MR-003` recorded that the advertised per-profile level existed in no
component rule. The exact rational is now the policy; the decimal is a rendering of it.

| Level | Exact rational | Decimal rendering |
| --- | --- | --- |
| study-level development screening | `1/200` | `0.005` |
| per-profile development component | `1/600` | `0.001666666667` |
| confirmation component | `1/200` | `0.005` |
| target power | `9/10` | `0.9` |

- **Fixed selectable-profile denominator:** `3`, fixed before any data exists and never shrinking, under every outcome including the outcome in which S3 is skipped (finding `S3MR-016`).
- **Identity asserted in exact rational arithmetic:** `per_profile_alpha x 3 == study_alpha`.
- **Within a profile:** intersection-union conjunction over the applicable components. The size of an intersection-union test is bounded by the component level, so **no further within-profile Bonferroni correction is applied**.
- **Confirmation:** one preselected profile, one shot, component level `1/200`, **no across-profile correction**, and the resulting claim is explicitly conditional on the selected profile.

## 3. Development components

Every row carries an explicit null column and an explicit unit column (findings `S3MR-007` and `S3MR-014`).

| Gate | Construct | Null | p1 | n | Unit of n | alpha (exact rational) | Required pass count | Exact null tail at p0 | Exact power at p1 | Meets target power | Degenerate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | trivial content recovery and output validity | p <= 0.9 | 0.97 | 256 | base items per atomic cell | `1/600` | 244 | 0.001491215117 | 0.953040775 | `true` | `false` |
| I1b | explicit content-to-symbol binding | p <= 0.9 | 0.97 | 256 | base items per atomic cell | `1/600` | 244 | 0.001491215117 | 0.953040775 | `true` | `false` |
| I2 | primitive headroom, evaluated separately per family | p <= 0.5 | 0.7 | 128 | base items per primitive-family cell | `1/600` | 82 | 0.000931234262 | 0.938986365 | `true` | `false` |
| I3 | pairwise presentation invariance and correctness, J_both | p <= 0.9 | 0.97 | 256 | base-item contrast clusters per contrast cell | `1/600` | 244 | 0.001491215117 | 0.953040775 | `true` | `false` |
| I4 | positive-reference competence recovery through the profile | p <= 0.8 | 0.9 | 256 | RP base items per operation-family x depth cell per candidate profile | `1/600` | 224 | 0.001081002486 | 0.921083515 | `true` | `false` |

## 4. Confirmation components - gate I5

Finding `S3MR-017` recorded that I5 had no statistical specification anywhere.

- **Covered constructs:** `I0`, `I1a`, `I1b`, `I2`, `I3_J_both`, `I4`
- **Component level:** exact rational `1/200`
- **Threshold logic:** Each covered construct is tested by the same exact one-sided binomial form used on the development split, against the same registered null, at the confirmation component level 1/200, in every applicable atomic cell separately. The constructs form an intersection-union conjunction: every applicable cell of every applicable construct must pass. No threshold, floor, sample size, unit, indicator or applicability rule may be re-tuned after the development split is read.
- **Multiplicity:** no across-profile correction is applied at confirmation, because exactly one profile is selected on the development split before confirmation is entered and no reselection is permitted. The resulting claim is explicitly conditional on that single profile.
- **Selection precondition:** I5 may be entered only after the pre-registered development selection map has returned exactly one selected profile. If the map returns none, the study STOPS and the confirmation split is never opened.
- **One-shot rule:** the confirmation split is read exactly once, for exactly one profile, under exactly one pre-registered analysis. It is spent by that reading. There is no second look, no re-analysis, no rescue path and no re-selection.
- **Accessible before authority:** `false`

| Gate | Construct | Null | p1 | n | Unit of n | alpha (exact rational) | Required pass count | Exact null tail at p0 | Exact power at p1 | Meets target power | Degenerate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | trivial content recovery and output validity | p <= 0.9 | 0.97 | 256 | base items per atomic cell | `1/200` | 243 | 0.003307722347 | 0.976290353 | `true` | `false` |
| I1b | explicit content-to-symbol binding | p <= 0.9 | 0.97 | 256 | base items per atomic cell | `1/200` | 243 | 0.003307722347 | 0.976290353 | `true` | `false` |
| I2 | primitive headroom, evaluated separately per family | p <= 0.5 | 0.7 | 128 | base items per primitive-family cell | `1/200` | 80 | 0.002962603303 | 0.972425829 | `true` | `false` |
| I3 | pairwise presentation invariance and correctness, J_both | p <= 0.9 | 0.97 | 256 | base-item contrast clusters per contrast cell | `1/200` | 243 | 0.003307722347 | 0.976290353 | `true` | `false` |
| I4 | positive-reference competence recovery through the profile | p <= 0.8 | 0.9 | 256 | RP base items per operation-family x depth cell per candidate profile | `1/200` | 222 | 0.003276850097 | 0.963820468 | `true` | `false` |

**Degenerate-region prohibition (finding `S3MR-015`).** No active rejection region
may have a required pass count equal to `n`. The `Degenerate` column above is `false`
in every row, and the derivation script raises before emitting any table if that
condition ever arises.

## 5. Gate I3 - the pairwise contrast design

Findings `S3MR-001` and `S3MR-002` recorded that the I3 estimand was not identifiable
from the published construction and that the primary indicator had two mutually
exclusive definitions.

- **Independent unit:** `base_item_contrast_cluster`
- **Variants per cluster:** `2`
- **No cross-product:** True
- **K5 and K6 are not crossed:** True

### K5 - seven one-factor pairwise contrast cells

| Contrast | Varied factor | Held fixed | Transformation | Variants per cluster |
| --- | --- | --- | --- | --- |
| `K5-P1` | content_position | `correct_symbol_index`, `label_alphabet` | the physical position of the correct content is moved by an offset of 1 modulo 4; the index of the correct displayed symbol and the label alphabet are held byte-identical | `2` |
| `K5-P2` | content_position | `correct_symbol_index`, `label_alphabet` | the physical position of the correct content is moved by an offset of 2 modulo 4; the index of the correct displayed symbol and the label alphabet are held byte-identical | `2` |
| `K5-P3` | content_position | `correct_symbol_index`, `label_alphabet` | the physical position of the correct content is moved by an offset of 3 modulo 4; the index of the correct displayed symbol and the label alphabet are held byte-identical | `2` |
| `K5-S1` | correct_symbol_index | `content_position`, `label_alphabet` | the index of the displayed symbol that carries the correct content is moved by an offset of 1 modulo 4; the physical position of the correct content and the label alphabet are held byte-identical | `2` |
| `K5-S2` | correct_symbol_index | `content_position`, `label_alphabet` | the index of the displayed symbol that carries the correct content is moved by an offset of 2 modulo 4; the physical position of the correct content and the label alphabet are held byte-identical | `2` |
| `K5-S3` | correct_symbol_index | `content_position`, `label_alphabet` | the index of the displayed symbol that carries the correct content is moved by an offset of 3 modulo 4; the physical position of the correct content and the label alphabet are held byte-identical | `2` |
| `K5-A1` | label_alphabet | `content_position`, `correct_symbol_index` | the label alphabet is replaced by the other registered alphabet; the physical position of the correct content and the index of the correct displayed symbol are held byte-identical | `2` |

- **Applicability:** {'applicable_profiles': ['S1', 'S4'], 'not_applicable_profiles': ['S2', 'S3'], 'semantics': 'K5 is recorded as not_applicable for S2 and S3, which render no option list and no label alphabet, so the manipulation has no referent. not_applicable is a third value: it is not a pass, it is not a zero effect, it is not evidence of robustness, and it may never be counted as a satisfied component.'}

### K6 - two disjoint pairwise contrast cells

| Contrast | Baseline | Variant | Varied factor | Held fixed | Variants per cluster |
| --- | --- | --- | --- | --- | --- |
| `K6-SEP` | `R-base` | `R-sep` | the option separator only | `the answer cue`, `every other byte of the prompt`, `the option contents`, `the label alphabet`, `the position of the correct content` | `2` |
| `K6-INSTR` | `R-base` | `R-instr` | the instruction sentence only | `the answer cue`, `every other byte of the prompt`, `the option contents`, `the label alphabet`, `the position of the correct content` | `2` |

- **Applicability:** {'applicable_profiles': ['S1', 'S2', 'S3', 'S4'], 'semantics': 'every profile is rendered, so the rendering contrasts always have a referent'}

### Construction verification

| Check | Result |
| --- | --- |
| `k5_baseline_conditions_balanced_over_a_complete_block` | `true` |
| `k5_complete_block_size` | `32` |
| `k5_contrast_count` | `7` |
| `k5_k6_base_item_identities_disjoint` | `true` |
| `k5_one_factor_per_contrast` | `true` |
| `k5_x_k6_cross_product_exists` | `false` |
| `k6_answer_cue_fixed_within_every_pair` | `true` |
| `k6_contrast_count` | `2` |
| `k6_rendering_set` | `R-base, R-instr, R-sep` |
| `label_alphabets_disjoint_from_answer_domain` | `true` |
| `label_alphabets_mutually_disjoint` | `true` |
| `variants_per_base_item_contrast_cluster` | `2` |

**Randomness:** `none anywhere in this design round; every condition is a fixed function of the registered base-item index and the registered contrast ID, no seed is drawn, and no random draw appears at any point`

### The three indicators

| Indicator | Definition | Role |
| --- | --- | --- |
| `J_inv` | 1 if and only if both variants of the cluster produce valid answer-domain content and the two mapped contents are byte-identical after the registered content mapping; 0 otherwise | reported alongside the gate; never a gate indicator on its own and never a rescue path |
| `J_cor` | 1 if and only if both variants of the cluster are scored correct against the unique registered ground truth of the base item; 0 otherwise | reported alongside the gate; never a gate indicator on its own and never a rescue path |
| `J_both` | J_inv AND J_cor | the PRIMARY gate indicator for I3 |

- **Estimand of the primary indicator:** Pr(J_both = 1) over independently sampled base-item contrast clusters, evaluated separately in every applicable atomic contrast cell
- **Why `J_both` is primary:** finding S3MR-002 recorded that draft-v0.2's I3 indicator scored a stable but WRONG answer as a success, so a model that answered the same incorrect value under every presentation could pass a gate named calibration robustness. Requiring correctness in addition to invariance removes that outcome.
- **Stable invalid or unparseable under `J_inv`:** 0
- **Stable but wrong under `J_cor`:** 0

- **Expected integrity invariant:** under a unique registered ground truth J_cor implies J_inv, because two outputs that both equal the ground truth are necessarily equal to each other. This is recorded here as an expected integrity invariant of the scorer, not as evidence that the two indicators carry independent information. A run in which J_cor = 1 and J_inv = 0 is a scorer defect, and the committed derivation asserts the implication over the enumerated outcome cases.
- **Why the conjunction is retained anyway:** the conjunction is what makes the stable-wrong and stable-invalid cases fail closed at the point of scoring, and it keeps the gate semantics legible without depending on the reader deriving the implication
- **No rescue:** J_inv, J_cor, the descriptive paired summary and any pooled rate may never rescue a failed J_both in any cell

| Case | Variant 1 mapped content | Variant 2 mapped content | `J_inv` | `J_cor` | `J_both` | Scores |
| --- | --- | --- | --- | --- | --- | --- |
| both correct | `7` | `7` | 1 | 1 | 1 | ``true`` |
| stable but wrong | `3` | `3` | 1 | 0 | 0 | ``false`` |
| one correct one wrong | `7` | `3` | 0 | 0 | 0 | ``false`` |
| one wrong one correct | `3` | `7` | 0 | 0 | 0 | ``false`` |
| both wrong and different | `3` | `5` | 0 | 0 | 0 | ``false`` |
| stable but invalid | _invalid_ | _invalid_ | 0 | 0 | 0 | ``false`` |
| one valid one invalid | `7` | _invalid_ | 0 | 0 | 0 | ``false`` |
| one invalid one valid | _invalid_ | `7` | 0 | 0 | 0 | ``false`` |

## 6. The retired paired procedure

- **Status:** `RETIRED FROM EVERY DECISION ROLE`
- **Retired from:**
  - gate authority of any kind
  - the I3 secondary criterion
  - interface profile eligibility
  - development selection
  - confirmation
  - claim language
  - equivalence margins
  - critical values
  - the four-point discordance grid
  - any conservativeness or verified-size statement
  - any rescue path for a failed component
  - any ranking weight
- **Why:** findings S3MR-004 and S3MR-005 recorded that draft-v0.2 asserted the procedure was conservative and had verified size, while the independent recalculation found its exact type-I error exceeded its nominal one-sided level at tested configurations, and that the verification grid tested four points and generalised from them. The operator resolution is removal rather than recalibration: the procedure is not necessary for the primary construct, which is an item-level conjunction, so it is withdrawn from inferential use altogether.
- **False assertion withdrawn:** the draft-v0.2 assertion that the procedure's exact type-I error does not exceed its nominal one-sided level is withdrawn as incorrect. It is not repaired, re-scoped or re-argued; it is withdrawn.
- **What survives:** purely descriptive paired 2x2 summaries with no null, no alpha, no p-value, no critical value, no equivalence margin, no pass or fail, no rescue path and no ranking weight
- **Historical evidence preserved, unedited:**
  - `studies/study3/analysis/independent_methods_recalculation.py`
  - `studies/study3/analysis/independent_methods_recalculation_tables.json`
  - `studies/study3/reviews/v0_2_independent_methods_review.json`
- **Rule:** the reviewer's recalculation is immutable historical evidence and is not edited, re-run, re-derived or superseded by this amendment

**Question for the reviewer.** does retiring the paired aggregate-equivalence procedure from every decision role fully remove the size-control defect recorded in S3MR-004 and S3MR-005, or does a residual decision path remain anywhere in the amended protocol?

## 7. The pre-registered development selection map

Finding `S3MR-017` recorded that the development selection rule was unspecified,
and finding `S3MR-016` recorded that the multiplicity denominator was contingent on a
post-data fact. The map below is total over its enumerated inputs, fixed before any
data exists, and carries the denominator `3` in every row.

| S3 multi-token activated | Applicable components passed | Eligible | Selected | STOP | Denominator |
| --- | --- | --- | --- | --- | --- |
| `false` | S1=false, S2=false, S3=false | _none_ | _none_ | ``true`` | 3 |
| `false` | S1=true, S2=false, S3=false | S1 | `S1` | ``false`` | 3 |
| `false` | S1=false, S2=true, S3=false | S2 | `S2` | ``false`` | 3 |
| `false` | S1=true, S2=true, S3=false | S2, S1 | `S2` | ``false`` | 3 |
| `false` | S1=false, S2=false, S3=true | _none_ | _none_ | ``true`` | 3 |
| `false` | S1=true, S2=false, S3=true | S1 | `S1` | ``false`` | 3 |
| `false` | S1=false, S2=true, S3=true | S2 | `S2` | ``false`` | 3 |
| `false` | S1=true, S2=true, S3=true | S2, S1 | `S2` | ``false`` | 3 |
| `true` | S1=false, S2=false, S3=false | _none_ | _none_ | ``true`` | 3 |
| `true` | S1=true, S2=false, S3=false | S1 | `S1` | ``false`` | 3 |
| `true` | S1=false, S2=true, S3=false | S2 | `S2` | ``false`` | 3 |
| `true` | S1=true, S2=true, S3=false | S2, S1 | `S2` | ``false`` | 3 |
| `true` | S1=false, S2=false, S3=true | S3 | `S3` | ``false`` | 3 |
| `true` | S1=true, S2=false, S3=true | S3, S1 | `S3` | ``false`` | 3 |
| `true` | S1=false, S2=true, S3=true | S2, S3 | `S2` | ``false`` | 3 |
| `true` | S1=true, S2=true, S3=true | S2, S3, S1 | `S2` | ``false`` | 3 |

**No profile is selected in this round.**

## 8. Operation accounting

Findings `S3MR-012` and `S3MR-013` recorded a factor-of-four self-contradiction in
the S3 projection and an undecomposed aggregate that mixed forward passes, sequence
scorings and generations. The projection is now decomposed by work stream and every
stream reports its own units.

| Work stream | Uses a model | Model roles | Rendered rows | Scored rows | Forward passes | Generated tokens (upper bound) |
| --- | --- | --- | --- | --- | --- | --- |
| `deterministic_I0_fixtures` | `false` | `0` | 502 | 502 | 0 | 0 |
| `target_role_development` | `true` | `RT`, `RL`, `RI` | _n/a_ | 20,736 | 20,736 | 0 |
| `positive_reference_external_P3Q` | `true` | `RP` | `null` | `null` | `null` | `null` |
| `RP_I4_under_candidate_profiles` | `true` | `RP` | _n/a_ | 2,048 | 2,048 | 0 |
| `selected_profile_one_shot_confirmation` | `true` | `RT`, `RL`, `RI`, `RP` | 17,152 | 17,152 | 17,152 | 0 |
| `S4_diagnostic_generation` | `true` | `RT`, `RL`, `RI` | 16,128 | 16,128 | `null` | 258,048 |

| Work stream | Scope |
| --- | --- |
| `deterministic_I0_fixtures` | renderer, content mapping, scorer and indicator fixtures |
| `target_role_development` | every applicable development component for each selectable profile, scored on the development split |
| `positive_reference_external_P3Q` | qualification of the positive reference through a canonical interface external to S1-S4, under a later authority |
| `RP_I4_under_candidate_profiles` | the positive reference scored on the registered K4 construct through each candidate profile, separately per operation family and depth |
| `selected_profile_one_shot_confirmation` | every applicable component for the single development-selected profile, on the physically disjoint one-shot confirmation split |
| `S4_diagnostic_generation` | the never-selectable free-generation diagnostic profile |

Every stream reports its own units. `target_role_development` and
`RP_I4_under_candidate_profiles` are further decomposed per interface profile in
`design_statistics_tables.json`, down to the per-component independent-unit type,
independent-unit count, cell count, variants per independent unit and rendered rows,
so no rendered-row figure can be read as a base-item figure.

**Character of the projection:** planning arithmetic only; this authorises nothing, approves no budget and creates no execution authority

- **`positive_reference_external_P3Q` numeric status:** `UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2`. Every quantity is `null`, because a number there would imply a selection that has not been made.
- **Why `null` and not zero:** the checkpoint, the canonical qualification interface, the qualification bank, the floor, n, the multiplicity treatment and the stop rule are all open under OD2; a number here would imply a selection that has not been made
- **S3 additional forward passes beyond S2:** `0`
- **S3 additional sequence-scoring rows beyond S2:** `0`
- **What S3 reuses:** the S2 forward pass and logit read under the same prefix
- **Future multi-token activation:** outside this projection; it requires a new authority, image, scoring contract and cost table

| Dimensional identity | Profile | Component | Holds |
| --- | --- | --- | --- |
| rendered_rows = base_item_contrast_clusters x 2 | `S1` | `I3_K6` | `true` |
| rendered_rows = base_item_contrast_clusters x 2 | `S1` | `I3_K5` | `true` |
| rendered_rows = base_item_contrast_clusters x 2 | `S2` | `I3_K6` | `true` |
| rendered_rows = base_item_contrast_clusters x 2 | `S3` | `I3_K6` | `true` |

**Prohibition carried by this section.** a single undifferentiated total is prohibited; every stream reports its own units

| Executed operation counter | Value |
| --- | --- |
| `activation_extractions` | `0` |
| `bank_rows` | `0` |
| `evidence_rows` | `0` |
| `forward_passes` | `0` |
| `generations` | `0` |
| `gpu_jobs` | `0` |
| `model_downloads` | `0` |
| `provider_calls` | `0` |
| `seeds_drawn` | `0` |
| `sequence_scorings` | `0` |
| `tokenizer_constructions` | `0` |
| `weight_loads` | `0` |

## 9. Descriptive quantities, with their tail conventions named

Finding `S3MR-019` recorded a two-sided convention filed under a one-sided field
name.

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

| n | Unit of n | Labels | Expected per label | Two-sided mass across the band | Acceptance band |
| --- | --- | --- | --- | --- | --- |
| 256 | scored rows in the cell | 4 | 64.0 | 0.001250000000 | 43 to 87 |
| 512 | scored rows in the cell | 4 | 128.0 | 0.001250000000 | 97 to 160 |
| 1024 | scored rows in the cell | 4 | 256.0 | 0.001250000000 | 212 to 301 |

Both tables are `DESCRIPTIVE_ONLY_NO_GATE_AUTHORITY`. The label-uniformity diagnostic
is `DIAGNOSTIC_NUISANCE_REPORT_ONLY` and eliminates no interface profile.

## 10. Derivation, not transcription

Every threshold, exact null tail, power figure and expected pass count in this section is derived by the committed script from the declared assumptions by exact binomial search over exact rational arithmetic. The reviewer-returned planning targets are not present in the script as literals; the committed design test holds them as an independent expectation and additionally asserts by AST inspection that none of the derived pass counts appears as an integer constant in the script. Copying a constant instead of deriving it is a test failure by construction.

- **Derivation script:** `studies/study3/analysis/design_statistics.py`
- **Derivation tables:** `studies/study3/analysis/design_statistics_tables.json`
- **Reproducibility:** the script's --check mode recomputes every table and compares it value-for-value against the committed tables; the committed design test runs that check, and the CPU-only Azure validation runs it again against the exact publication commit

The committed design test holds the reviewer-returned planning targets as an
independent expectation **and** asserts, by AST inspection, that none of the derived
pass counts or tails appears in the derivation script as a literal constant. A script
that reproduced the targets by transcription would fail that test.

## 11. Authority state

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

**Blocking operator decision:** `OD2`. No positive reference is selected, preferred,
pinned, revision-resolved, downloaded, tokenized, loaded or prequalified, and
`UR-22` is recorded `UNRESOLVED_BLOCKING_OPERATOR_DECISION` rather than resolved.

## 12. What this packet does not do

- It does not freeze the design.
- It does not authorize execution, bank construction, a seed draw or any model operation.
- It does not select an interface profile or a positive reference.
- It does not authorize access to the confirmation split.
- It does not declare the amended protocol correct.
