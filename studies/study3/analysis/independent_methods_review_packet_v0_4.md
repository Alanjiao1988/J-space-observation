# Study 3 draft-v0.4 independent methods review packet

**State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_4_COMPLETE_AWAITING_THIRD_INDEPENDENT_METHODS_REVIEW`

This packet is the review object for the **third** bounded independent methods review of the Study 3
interface-calibration protocol. It supersedes
`studies/study3/analysis/independent_methods_review_packet_v0_3.md`, which remains committed and
unedited as the exact object the second reviewer reviewed.

Nothing in this packet is a measurement. No model was downloaded, loaded, tokenized, run, scored,
generated from, probed, patched or ablated to produce it. No seed was drawn and no bank row exists.
Every operation counter is exactly zero.

## 0. What the reviewer is asked to do

The second independent methods review returned `STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`
with 2 BLOCKING, 6 MAJOR and 2 MINOR structured findings. The drafting party has amended the design.
The amendment record is `studies/study3/reviews/v0_4_operator_amendment.md`.

**The drafting party does not claim the amended protocol is correct.** Every repair is recorded as
`PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`. The determination belongs to the reviewer.

Specific questions the drafting party puts to the third reviewer:

1. Does narrowing I3 to `J_joint_correct` remove the estimand/claim mismatch recorded in `S3MR2-001`,
   or does residual presentation-effect language or an implied effect claim survive anywhere in an
   active field?
2. Is the registered `sampling_frame_v0_4` sufficient to license exact-binomial inference in every
   gate-bearing atomic cell, and is any cell left without a complete generator distribution?
3. Is the union-bound type-II architecture correct, and does the end-to-end floor of `9/10` actually
   follow from the registered budgets under arbitrary dependence and the stated least-favourable
   configuration?
4. Is the total state machine genuinely total and deterministic, with every registered terminal state
   reachable and no event carrying two next states?
5. Does the operation ontology now map every cost-bearing quantity, and is the S4 sequence-evaluation
   bound correct and correctly distinguished from a runtime batched call?

## 1. The I3 estimand

The sole gate-bearing indicator is `J_joint_correct`: 1 exactly when **both** registered variants of
the base-item contrast cluster are scored correct against the same unique registered ground truth.

- **Estimand:** `p_joint` = Pr(`J_joint_correct` = 1) over the registered item-generating
  distribution for that atomic contrast cell.
- **This is a level, not a contrast.** It does not identify the direction, magnitude or existence of
  a presentation effect.
- **Null:** `p_joint <= 9/10`. **Lowest alternative of interest:** `97/100`.

The full ordered outcome lattice over ['correct', 'wrong_a', 'wrong_b', 'invalid'] for the two variants has
16 cases, of which exactly 1 family passes.

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

**Prohibited in every active claim, gate question, `what_fails` clause, validation-target
interpretation and success statement:** invariance, equivalence, no presentation effect,
presentation-effect size, stable across presentations, unaffected by presentation and their semantic
equivalents. They are permitted only in clearly labelled historical, retired-procedure,
limitation-of-claim and prohibited-claim text.

**Claim ceiling, by profile.**

| Profile | Applicable cells | Claim |
| --- | --- | --- |
| `S1` | 9 | joint robust correctness for each of the seven applicable K5 pairs and the two applicable K6 pairs, separately |
| `S2` | 2 | joint robust correctness for the two applicable K6 pairs only; the seven K5 pairs are not_applicable and are never counted as passes or as evidence |
| `S3` | 2 | joint robust correctness for the two applicable K6 pairs only, and only while S3's separately registered single-token applicability condition holds |
| `S4` | 9 | descriptive only; S4 is never selectable and never enters an interface-selection or confirmation claim |

## 2. The registered sampling frame

within each gate-bearing atomic cell, base-item units or base-item contrast-cluster units are independent draws WITH REPLACEMENT from that cell's registered generator distribution; the deterministic model and scorer map each independently drawn unit to exactly one Bernoulli success indicator.

- Development sampling cells: **17**; confirmation sampling
  cells: **17**.
- A **sampling cell** excludes interface profile and checkpoint role. An **evaluation cell** is a
  sampling cell crossed with one applicable profile and one applicable role.
- One iid stream per sampling cell is reused across its evaluation cells, so each evaluation cell is
  marginally iid Bernoulli while cells sharing items may be dependent. That dependence is expressly
  allowed and is handled by the arbitrary-dependence bounds.
- Draws are **with replacement**; duplicates are legitimate and **must be retained**.
- Every sampled parameter carries an exact rational weight summing to exactly one.
- Validity predicates are deterministic and pre-model; the registered rejection probability is `0`
  because every support satisfies them by construction.
- The K5 nuisance support has 32 states at exact
  weight `1/32` each, drawn iid.
  The deterministic complete-block assignment is retired and `n` need not be a multiple of 32.
- **No seed and no bank exists.** Seed values, the generator implementation blob and the realized
  bank are `null`, meaning not yet selected.

## 3. Power architecture

| Quantity | Exact rational | Scope |
| --- | --- | --- |
| `m_max` | 43 | maximum gate-bearing cells over the selectable profiles |
| per-stage profile false-negative budget | `19/400` | one profile, one stage |
| per-cell false-negative budget | `19/17200` | per atomic evaluation cell |
| per-cell power target | `17181/17200` | **per atomic evaluation cell** |
| profile stage power floor | `381/400` | union-bound lower bound under arbitrary dependence |
| study end-to-end power floor | `9/10` | development selection plus one-shot confirmation |

| Profile | I1/I3 cells | I2 cells | I4 cells | Total | Selectable |
| --- | --- | --- | --- | --- | --- |
| `S1` | 33 | 6 | 4 | 43 | `true` |
| `S2` | 9 | 6 | 4 | 19 | `true` |
| `S3` | 9 | 6 | 4 | 19 | `true` |
| `S4` | 33 | 6 | 0 | 39 | `false` |

**No independence is used for any binding bound.** Pr(the study returns the designated adequate profile and confirms it) >= 1 - 19/400 - 1/200 - 19/400 = 9/10

**Least-favourable configuration.**

- I0 passes
- at least one selectable profile has every applicable atomic-cell success probability at or above that cell's registered p1
- any higher-priority profile that is not adequate lies in its registered profile null, meaning at least one of its required cells is at or below that cell's p0
- development and confirmation follow the frozen selection order with no rescue and no substitution
- the selected adequate profile remains at or above p1 on the confirmation-generating distribution

**Not covered by the guarantee.**

- profiles whose cell success probabilities lie in the indifference region strictly between p0 and p1
- distribution shift between the development and confirmation generating distributions
- I0 failure
- an invalid or unregistered sampling frame
- protocol deviations of any kind

## 4. Exact-binomial components

### Development

| Gate | Null | p1 | n | Unit of n | alpha | Pass count | Exact null tail | Exact power at p1 | Applicable profiles |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/600` | 389 | 0.001664632930 | 0.999129439838 | S1, S2, S3, S4 |
| I1b | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/600` | 389 | 0.001664632930 | 0.999129439838 | S1, S4 |
| I2 | `p <= 1/2` | `7/10` | 214 | base items per primitive-family cell | `1/600` | 129 | 0.001597676081 | 0.999042859186 | S1, S2, S3, S4 |
| I3 | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/600` | 389 | 0.001664632930 | 0.999129439838 | S1, S2, S3, S4 |
| I4 | `p <= 4/5` | `9/10` | 448 | RP base items per operation-family x depth cell per candidate profile | `1/600` | 383 | 0.001620609599 | 0.999005509196 | S1, S2, S3 |

### Confirmation

| Gate | Null | p1 | n | Unit of n | alpha | Pass count | Exact null tail | Exact power at p1 | Applicable profiles |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1a | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/200` | 388 | 0.003020762720 | 0.999609916012 | S1, S2, S3 |
| I1b | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/200` | 388 | 0.003020762720 | 0.999609916012 | S1 |
| I2 | `p <= 1/2` | `7/10` | 214 | base items per primitive-family cell | `1/200` | 127 | 0.003765544908 | 0.999646587923 | S1, S2, S3 |
| I3 | `p <= 9/10` | `97/100` | 413 | base items per atomic cell for I1a and I1b; base-item contrast clusters per contrast cell for I3 | `1/200` | 388 | 0.003020762720 | 0.999609916012 | S1, S2, S3 |
| I4 | `p <= 4/5` | `9/10` | 448 | RP base items per operation-family x depth cell per candidate profile | `1/200` | 381 | 0.003582895662 | 0.999626931069 | S1, S2, S3 |

Each development `n` is the smallest unrestricted positive integer meeting the per-cell target; each
pass count is minimal at its level; no rejection region is degenerate. Confirmation sizes are
**conservative reuse** of the development sizes, not minimal confirmation sizes. Confirmation
applicability is the intersection of the component's selectable profiles with the single selected
profile, so `S4` never appears, and `I1b` and `K5` apply only to `S1`.

## 5. The total state machine

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

`I0` is a global precondition; its failure maps only to `STOP_INSTRUMENT_DEFECT`, which states that
nothing was measured about any interface. Every registered terminal state is reachable and no event
has two next states.

## 6. Operation projection

| Work stream | Rendered rows | Sequence-level evaluations | Generation calls | Generated tokens |
| --- | --- | --- | --- | --- |
| `deterministic_I0_fixtures` | 502 | 0 | 0 | 0 |
| `target_role_development` | 33,543 | 33,543 | 0 | 0 |
| `positive_reference_external_P3Q` | `null` | `null` | `null` | `null` |
| `RP_I4_under_candidate_profiles` | 3,584 | 3,584 | 0 | 0 |
| `selected_profile_one_shot_confirmation` | 27,856 | 27,856 | 0 | 0 |
| `S4_diagnostic_generation` | 26,064 | 417,024 | 26,064 | 417,024 |

`S4` prefill evaluations: **26,064**; incremental decode
evaluations upper bound: **390,960**. A sequence-level
evaluation is never equated with a runtime batched forward call.

`I0` fixtures: **232** clusters, **232** cluster-derived base items, **464** cluster rendered rows,
**38** non-cluster rows, **502** rendered rows in total, zero model operations.

**No grand total is published**, because the unresolved P3-Q stream is `null` and not zero.

## 7. Authority state

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

**Blocking operator decision:** `OD2`. No positive reference is selected, preferred, pinned,
revision-resolved, downloaded, tokenized, loaded or prequalified, and `UR-22` remains
`UNRESOLVED_BLOCKING_OPERATOR_DECISION`. draft-v0.4 registers only the binding ordering constraint
`P3Q >= 19/20 > I4 p1 = 9/10 > I4 p0 = 4/5`.

## 8. What this packet does not do

- It does not freeze the design.
- It does not authorize execution, bank construction, a seed draw or any model operation.
- It does not select an interface profile or a positive reference.
- It does not authorize access to the confirmation split.
- It does not declare the amended protocol correct.

