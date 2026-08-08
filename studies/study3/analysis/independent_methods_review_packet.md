# Study 3 - bounded independent-methods-review packet

- **Document class:** independent methods review packet
- **Draft under review:** `draft-v0.2`
- **State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW`
- **Status of every number below:** proposed design parameters, not measurements
- **Derivation script:** `studies/study3/analysis/design_statistics.py`
- **Derivation tables:** `studies/study3/analysis/design_statistics_tables.json`

This packet is deliberately bounded. It contains only the eight sections
required for an independent statistical review: estimands and atomic units,
the hypotheses, the gate truth table and stop states, the multiplicity and
selection logic, the proposed margins and floors, the power and sample-size
sensitivity tables, the unresolved statistical choices, and the reviewer
checklist. It contains no results, no bank rows, no model outputs and no
narrative that is not needed to evaluate the statistics. Every table here is
rendered from committed artifacts; the script's `--check` mode recomputes
them value-for-value.

---

## 1. Estimands and atomic units

- **Sampling unit:** the base item
- **Atomic evaluation cell:** An atomic evaluation cell is one combination of interface profile, checkpoint role, task stratum, operation family, depth, rendering, label or position condition, and split. A gate passes only if it passes in every atomic cell to which it is applicable.
- **Cell factors (the full index of one observation):**

  - interface profile
  - checkpoint role
  - task stratum
  - operation family
  - depth
  - rendering
  - label or position condition
  - split

- **Cluster rule:** Every permutation, label-set replacement and rendering variant derived from one base item belongs to the same correlated cluster as that base item, is assigned to the same split as that base item, and is never treated as an independent observation. Splitting a cluster across splits would leak the confirmation set.
- **Pooling:** `no_pooling_rescue = true`. Pooling may not be used to rescue
  a failing cell. The following pooling operations are prohibited:


| Prohibited pooling | Why |
| --- | --- |
| pooling K1 with K2 | K1 asks whether the model binds content to a displayed symbol; K2 asks whether it can echo trivially recoverable content at all. A high K2 rate can carry a failed K1 across a threshold, which would let the study report binding it never demonstrated. |
| pooling across primitive operation families | a family the model handles well can mask a family it cannot handle, so the headroom gate would stop testing headroom |
| pooling K4 depth 2 with depth 3 | depth is the compositional variable of interest; averaging over it destroys the construct |
| pooling across checkpoint roles | the roles are the contrast the later study depends on |
| pooling across interface profiles | the interfaces are the object of comparison |
| pooling across renderings | rendering sensitivity is precisely what K6 measures |

**Estimands.** Each gate estimand is a probability defined over a single
atomic cell class, not over a pooled mixture:

| Gate | Estimand | Evaluated per |
| --- | --- | --- |
| I0 | Does the rendering and scoring software do exactly what it claims to do, on inputs whose correct answer is fixed by construction and requires no model? | interface profile, renderer branch, scorer branch |
| I1a | Can the checkpoint recover an answer that is trivially present in the prompt, and does it emit a structurally valid output while doing so? | interface profile, checkpoint role, split |
| I1b | When a symbol stands for an answer, does the checkpoint bind the correct content to the correct displayed symbol, rather than following a symbol prior? | interface profile, checkpoint role, label or position condition, split |
| I2 | Does the checkpoint have measurable headroom on each single primitive operation family, so that a later compositional failure cannot be explained by inability to do the parts? | interface profile, checkpoint role, operation family, split |
| I3 | Does the checkpoint give the same answer to the same question when the presentation changes in ways that do not change the question? | interface profile, checkpoint role, rendering, label or position condition, split |
| I4 | Does an independently prequalified capable reference succeed through this interface, so that a target failure through the same interface can be attributed to the target rather than to the interface? | interface profile, operation family, depth |
| I5 | Do the constructs that passed on the development split hold on a confirmation split that was never inspected? | every gate-bearing construct |

**Not-applicable is a third value.** not_applicable is a third value. It is not a pass, it is not a zero effect, it is not evidence of robustness, and it may never be counted as a satisfied gate, averaged into any rate, or used as an input to admissibility. A gate whose transformation is not applicable to a profile is simply not evaluated for that profile, and the profile's eligibility rests on the gates that are applicable to it.

---

## 2. Null and alternative hypotheses

All gate hypotheses are one-sided lower-bound hypotheses on a per-cell
proportion unless stated otherwise. The alternative is the complement of the
stated null. Rejection of the null is what a **pass** means; failure to
reject is a **fail**, and fail-closed means the failure propagates.

| Gate | Null hypothesis | Alternative | n | alpha | Reject when successes >= |
| --- | --- | --- | --- | --- | --- |
| I1a | `p <= 0.9` | `p > 0.9` | 192 | 0.005 | 184 |
| I1a | `p <= 0.9` | `p > 0.9` | 128 | 0.005 | 124 |
| I1b | `p <= 0.9` | `p > 0.9` | 192 | 0.005 | 184 |
| I1b | `p <= 0.9` | `p > 0.9` | 128 | 0.005 | 124 |
| I2 | `p <= 0.5` | `p > 0.5` | 192 | 0.005 | 115 |
| I2 | `p <= 0.5` | `p > 0.5` | 128 | 0.005 | 80 |

**I3 primary (per-base-item consistency).** The unit is the base item; the
indicator is 1 when every counterbalanced variant of that base item is
scored correct. Null `p <= 0.9`, alternative `p > 0.9`, exact binomial.

| n | alpha | Reject when successes >= | Exact null tail |
| --- | --- | --- | --- |
| 128 | 0.005 | 124 | 0.003072 |
| 192 | 0.005 | 184 | 0.002362 |
| 256 | 0.005 | 243 | 0.003308 |
| 384 | 0.005 | 361 | 0.003608 |
| 128 | 0.005 | 128 | 0.001408 |
| 192 | 0.005 | 190 | 0.00327 |
| 256 | 0.005 | 252 | 0.003666 |
| 384 | 0.005 | 376 | 0.002867 |

**I3 secondary (aggregate paired equivalence).** Two one-sided nulls
`H01: delta <= -margin` and `H02: delta >= +margin` on the paired difference
of correctness proportions between a transformed condition and its base
condition. The equivalence claim is the intersection-union rejection of both.
Method: Tango 1998 score interval, two one-sided tests.

**I4 (positive-reference competence).** Null `p <= 0.8` against
alternative `p > 0.8`, exact binomial. The chance-level null used in
draft-v0.1 is **rejected**; see section 5.

**Label-selection uniformity (part of I3).** For each label position the
null is that the selection rate equals the uniform expectation; the two-sided
acceptance band is given in section 6. This is a nuisance-symmetry check, not
a competence claim.

**Descriptive quantities.** The Clopper-Pearson lower bounds in section 6
are descriptive interval statements. They are not hypothesis tests and carry
no gate authority.

---

## 3. Gate truth table and legal stop states

Every gate is fail-closed. No gate authorises mechanistic execution.

| Gate | Part of eligibility | On pass | On fail | Authorises mechanistic execution | Fail-closed |
| --- | --- | --- | --- | --- | --- |
| I0 | `true` | evaluate I1a | STOP; fix the instrument and restart the gate sequence from I0 | `false` | `true` |
| I1a | `true` | evaluate I1b where applicable, otherwise I2 | eliminate this interface profile for this role; if no selectable profile remains, STOP | `false` | `true` |
| I1b | `true` | evaluate I2 | eliminate this interface profile for this role; if no selectable profile remains, STOP | `false` | `true` |
| I2 | `true` | evaluate I3 | eliminate this interface profile for this role; if no selectable profile remains, STOP | `false` | `true` |
| I3 | `true` | evaluate I4 | eliminate this interface profile for this role; if no selectable profile remains, STOP | `false` | `true` |
| I4 | `true` | the interface profile is eligible; evaluate the admissibility order | eliminate this interface profile; if no selectable profile remains, STOP | `false` | `true` |
| I5 | `false` | the interface is calibrated; a separate authority is still required before any mechanistic work | STOP; the confirmation split is spent and may not be reused | `false` | `true` |

**Legal stop states.** These are the only terminal states this design may
reach. There is no state in which a failure is absorbed and execution
continues.

- STOP_INSTRUMENT_DEFECT after an I0 failure
- STOP_NO_SELECTABLE_INTERFACE_REMAINS after every selectable profile has been eliminated by I1a, I1b, I2, I3 or I4
- STOP_CONFIRMATION_FAILED after an I5 failure, with the confirmation split spent
- STOP_AWAITING_AUTHORITY, which is the current state

**Applicability and selectability.** A gate that is not applicable to a
profile is recorded NA and the profile is judged on the gates that do apply.

| Profile | Selectable status | Applicable gates | Non-applicable transformations |
| --- | --- | --- | --- |
| S1 | `selectable` | I0, I1a, I1b, I2, I3, I4, I5 | none |
| S2 | `selectable_preferred` | I0, I1a, I2, I3, I4, I5 | label_set_replacement, label_symbol_permutation, position_permutation |
| S3 | `conditionally_selectable` | I0, I1a, I2, I3, I4, I5 | label_set_replacement, label_symbol_permutation, position_permutation |
| S4 | `never_selectable` | I0, I1a, I1b, I2, I3, I4, I5 | none |

**Admissibility order (pre-registered, fail-closed).** An interface profile is eligible if and only if every gate that is applicable to it passes in every atomic cell. The applicable gate set is a property of the profile and is listed in the profile. I4 is part of eligibility.

| Rank | Interface | Condition | Why |
| --- | --- | --- | --- |
| 1 | S2 | the frozen answer domain is jointly single-token eligible for every required role | S2 has no symbol-binding step, so a pass cannot be an artefact of label handling and a failure cannot be blamed on it |
| 2 | S3 | a later authority has introduced a multi-token answer domain, a dedicated multi-token stratum, a registered boundary-token rule and a length-confound gate | S3 is the natural surface for a multi-token domain, but it is not independent of S2 for single-token contents |
| 3 | S1 | S1 is eligible | S1 preserves continuity with Study 2 but is the surface whose adequacy is in question, so it is admitted only when no higher-ranked surface is available |

Never selectable: S4. `no_data_dependent_ranking = true`: the order above is
fixed in advance and may not be reordered after seeing any data.

`no_winner_this_round = true`. No interface is selected in this round.

---

## 4. Multiplicity and selection logic

**Principle.** Two structurally different multiplicity problems are kept apart. Within one interface profile, every gate and every atomic cell must pass; that conjunction is an intersection-union test, whose size is bounded by the level of its individual components, so no inflation correction is applied to the conjunction itself. Across interface profiles, by contrast, the study may proceed if ANY selectable profile qualifies; that is a union event and it does inflate the false-qualification rate, so it is Bonferroni-corrected by the number of selectable profiles.

### Family A - within one profile

- **type:** intersection_union_conjunctive
- **members:** I1a, I1b, I2, I3_primary, I3_uniformity, I4
- **correction:** none required; IU size is bounded by the component level
- **per component alpha:** 0.005
- **note:** each atomic cell inside a gate is itself a conjunctive member; a failed cell fails the gate and no pooled summary may rescue it

### Family B - across selectable profiles

- **type:** union_selection
- **members:** S1, S2, S3
- **excluded:** S4 is never selectable and never enters selection
- **correction:** Bonferroni over 3 selectable profiles
- **per profile alpha:** 0.001667

### Family C - descriptive

- **type:** descriptive_only
- **members:** pooled summaries, softmax confidences, per-cell Clopper-Pearson intervals
- **correction:** simultaneous Clopper-Pearson bounds are reported for readability; they carry no gate authority

**Why Family A needs no correction.** Family A is an intersection-union
family: the profile is declared adequate only if *every* component null is
rejected. The type-I error of the conjunction is bounded by the level of any
single component, so no inflation occurs and no correction is applied.

**Why Family B does need a correction.** Family B is a union/selection
event: the round would report success if *any* selectable profile is
declared adequate. That is a maximum over 3 surfaces, so the per-profile
level is Bonferroni-divided by 3.

**S4 is excluded from the selection family.** S4 is `never_selectable`, so
it can never be the surface that produces a reported success and does not
enter the multiplicity count.

**Unresolved.** the final alpha allocation is a v0.2 proposal and is part of the blocking OD5 decision

---

## 5. Proposed margins and floors

### 5.1 The rejected draft-v0.1 chance null for I4

- Status: `REJECTED_BY_OPERATOR_REVIEW`
- draft-v0.1 null: `p <= 0.25` at n = 128, alpha = 0.001, giving an acceptance count of
  49, i.e. an acceptance rate of 0.382812.
- Why rejected: a chance-level null does not establish a positive-capability floor; clearing 0.25 shows only that the reference is above guessing, which cannot license the inference that the interface is adequate for a capable model

### 5.2 Proposed I4 competence floor

The floor is a competence floor of `p0 = 0.8`, not chance.

| n | alpha | Reject when successes >= | Acceptance rate | Exact null tail | Power at 0.90 | Power at 0.95 |
| --- | --- | --- | --- | --- | --- | --- |
| 128 | 0.005 | 114 | 0.890625 | 0.004707 | 0.701983 | 0.998087 |
| 128 | 0.001667 | 116 | 0.90625 | 0.000911 | 0.480533 | 0.987934 |
| 128 | 0.001 | 116 | 0.90625 | 0.000911 | 0.480533 | 0.987934 |
| 192 | 0.005 | 168 | 0.875 | 0.004324 | 0.89595 | 0.999987 |
| 192 | 0.001667 | 170 | 0.885417 | 0.001203 | 0.78993 | 0.999897 |
| 192 | 0.001 | 171 | 0.890625 | 0.000591 | 0.717503 | 0.999727 |
| 256 | 0.005 | 222 | 0.867188 | 0.003277 | 0.96382 | 1 |
| 256 | 0.001667 | 224 | 0.875 | 0.001081 | 0.921084 | 0.999999 |
| 256 | 0.001 | 225 | 0.878906 | 0.000591 | 0.888306 | 0.999998 |
| 384 | 0.005 | 328 | 0.854167 | 0.003745 | 0.998248 | 1 |
| 384 | 0.001667 | 330 | 0.859375 | 0.001582 | 0.995536 | 1 |
| 384 | 0.001 | 331 | 0.861979 | 0.000998 | 0.993074 | 1 |

### 5.3 Proposed I3 margins

- Claim under review: v0.1 asserted an aggregate equivalence margin of 0.05 without any paired power analysis
- At n = 192 and target power 0.9:
  - margin 0.05 supported at any tested discordance rate: `false`
  - margin 0.10 supported at discordance rates: 0.05, 0.1
- **Conclusion:** n = 192 does NOT support the v0.1 aggregate equivalence margin of 0.05 at 0.90 power under any tested discordance rate. The margin, the sample size, or both must be revised by the independent methods review. This is why OD5 and OD6 remain blocking.

### 5.4 Label-selection uniformity bands

| Applies to | n | Labels | Expected per label | Bonferroni alpha | Acceptance band |
| --- | --- | --- | --- | --- | --- |
| label-bearing profiles only; NA for content-only profiles | 192 | 4 | 48 | 0.00125 | [30, 68] |
| label-bearing profiles only; NA for content-only profiles | 384 | 4 | 96 | 0.00125 | [69, 124] |
| label-bearing profiles only; NA for content-only profiles | 768 | 4 | 192 | 0.00125 | [154, 231] |

---

## 6. Power and sample-size sensitivity

### 6.1 Retained exact binomial gates

| Gate | Construct | n | alpha | Reject at | Power at lowest alternative | Meets 0.90 power there |
| --- | --- | --- | --- | --- | --- | --- |
| I1a | trivial content recovery and output validity | 192 | 0.005 | 184 | 0.87425 (p = 0.97) | `false` |
| I1a | trivial content recovery and output validity | 128 | 0.005 | 124 | 0.660555 (p = 0.97) | `false` |
| I1b | explicit content-to-symbol binding | 192 | 0.005 | 184 | 0.87425 (p = 0.97) | `false` |
| I1b | explicit content-to-symbol binding | 128 | 0.005 | 124 | 0.660555 (p = 0.97) | `false` |
| I2 | primitive headroom, per family | 192 | 0.005 | 115 | 0.998888 (p = 0.7) | `true` |
| I2 | primitive headroom, per family | 128 | 0.005 | 80 | 0.972426 (p = 0.7) | `true` |

Note for the reviewer: at n = 192 and alpha = 0.005 the I1a/I1b thresholds
do **not** reach 0.90 power against the nearest alternative p = 0.97; power
there is 0.87425. They reach 0.90 only from p = 0.98 upward. This is disclosed
rather than hidden, and it is one of the unresolved choices in section 7.

### 6.2 Paired equivalence sensitivity (I3 secondary)

Exact enumeration of the trinomial distribution of the discordant pair
counts. `Type-I at margin` is the exact rejection probability when the true
difference sits on the null boundary.

| n | Margin | Discordance rate | True difference | One-sided alpha | Exact power | Meets 0.9 power | Exact type-I at boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 128 | 0.05 | 0.05 | 0 | 0.025 | 0.173256 | `false` | 0.010894 |
| 128 | 0.05 | 0.1 | 0 | 0.025 | 0.00586 | `false` | 0.002787 |
| 128 | 0.05 | 0.2 | 0 | 0.025 | 0 | `false` | 0 |
| 128 | 0.05 | 0.3 | 0 | 0.025 | 0 | `false` | 0 |
| 192 | 0.05 | 0.05 | 0 | 0.025 | 0.541197 | `false` | 0.012216 |
| 192 | 0.05 | 0.1 | 0 | 0.025 | 0.114881 | `false` | 0.015768 |
| 192 | 0.05 | 0.2 | 0 | 0.025 | 0.000035 | `false` | 0.000019 |
| 192 | 0.05 | 0.3 | 0 | 0.025 | 0 | `false` | 0 |
| 256 | 0.05 | 0.05 | 0 | 0.025 | 0.776425 | `false` | 0.01072 |
| 256 | 0.05 | 0.1 | 0 | 0.025 | 0.358216 | `false` | 0.022272 |
| 256 | 0.05 | 0.2 | 0 | 0.025 | 0.003664 | `false` | 0.001093 |
| 256 | 0.05 | 0.3 | 0 | 0.025 | 0 | `false` | 0 |
| 384 | 0.05 | 0.05 | 0 | 0.025 | 0.9605 | `true` | 0.014578 |
| 384 | 0.05 | 0.1 | 0 | 0.025 | 0.692423 | `false` | 0.022519 |
| 384 | 0.05 | 0.2 | 0 | 0.025 | 0.167119 | `false` | 0.017435 |
| 384 | 0.05 | 0.3 | 0 | 0.025 | 0.000476 | `false` | 0.000131 |
| 128 | 0.1 | 0.05 | 0 | 0.025 | 0.97327 | `true` | not defined |
| 128 | 0.1 | 0.1 | 0 | 0.025 | 0.811431 | `false` | 0.023487 |
| 128 | 0.1 | 0.2 | 0 | 0.025 | 0.37971 | `false` | 0.022592 |
| 128 | 0.1 | 0.3 | 0 | 0.025 | 0.078535 | `false` | 0.011778 |
| 192 | 0.1 | 0.05 | 0 | 0.025 | 0.99904 | `true` | not defined |
| 192 | 0.1 | 0.1 | 0 | 0.025 | 0.963405 | `true` | 0.025501 |
| 192 | 0.1 | 0.2 | 0 | 0.025 | 0.713243 | `false` | 0.023542 |
| 192 | 0.1 | 0.3 | 0 | 0.025 | 0.417343 | `false` | 0.023677 |
| 256 | 0.1 | 0.05 | 0 | 0.025 | 0.999972 | `true` | not defined |
| 256 | 0.1 | 0.1 | 0 | 0.025 | 0.994856 | `true` | 0.023601 |
| 256 | 0.1 | 0.2 | 0 | 0.025 | 0.876815 | `false` | 0.023881 |
| 256 | 0.1 | 0.3 | 0 | 0.025 | 0.653297 | `false` | 0.024552 |
| 384 | 0.1 | 0.05 | 0 | 0.025 | 1 | `true` | not defined |
| 384 | 0.1 | 0.1 | 0 | 0.025 | 0.999909 | `true` | 0.017524 |
| 384 | 0.1 | 0.2 | 0 | 0.025 | 0.981367 | `true` | 0.024284 |
| 384 | 0.1 | 0.3 | 0 | 0.025 | 0.8907 | `false` | 0.024727 |

`not defined` marks a configuration in which the null boundary is
unreachable: when the margin exceeds the total discordance rate, the
boundary configuration would require a negative cell probability, so no
type-I error exists to report. This is a property of the parameter space,
not a gap in the computation.

### 6.3 Verification of the paired method implementation

The implementation is verified three ways before any table above is emitted.
If any check fails the script exits non-zero and writes nothing.

- **Reduction to McNemar at margin 0:** maximum absolute deviation 0.
  Tango's procedure collapses algebraically to `(n12 - n21) / sqrt(n12 + n21)`
  at a zero-difference null; this is the published special case and is used
  here as a closed-form correctness proof rather than a numerical opinion.
- **Constrained MLE against direct numerical maximisation:** maximum
  absolute deviation 0.000000003392.
- **Normal quantile routine:** maximum absolute deviation 0 against the
  reference value of the two-sided 0.05 critical point, 1.959963984540054.
- **Exact type-I at the null boundary:**

  | n | Margin | Discordance | Exact type-I |
  | --- | --- | --- | --- |
  | 96 | 0.1 | 0.2 | 0.015065 |
  | 128 | 0.1 | 0.2 | 0.022592 |
  | 192 | 0.1 | 0.3 | 0.023677 |

  These three configurations are at or below the nominal one-sided level
  of 0.025. That is **not** a general guarantee; see the exceedance below.

### 6.3.1 Disclosed anti-conservatism at the null boundary

The word *exact* in this packet describes the **enumeration**, not the
test. Power and type-I are obtained by exhaustively enumerating the
trinomial distribution of the discordant pair counts, so there is no
simulation error and no normal approximation to the sampling distribution.
The decision rule itself is Tango's asymptotic score procedure, which is
not guaranteed to hold the nominal level at finite n. This packet
therefore does not claim an exact paired TOST.

Across the 28 configurations in section 6.2 whose null boundary is
reachable, 1 exceeds the nominal one-sided level of 0.025:

| n | Margin | Discordance | Exact type-I | Relative excess |
| --- | --- | --- | --- | --- |
| 192 | 0.1 | 0.1 | 0.025501 | +2.00% |

The largest observed level is 0.025501 against a nominal 0.025.
The excess is small and is a known finite-sample property of score-based
procedures, but it is disclosed rather than absorbed, and the reviewer
must decide whether it is acceptable or whether the critical value must
be adjusted so that the realised level never exceeds the nominal one.

### 6.4 Descriptive Clopper-Pearson lower bounds

| Cells | n | Successes | Simultaneous alpha | Lower bound |
| --- | --- | --- | --- | --- |
| 4 | 192 | 184 | 0.00125 | 0.890112 |
| 4 | 192 | 176 | 0.00125 | 0.833418 |
| 4 | 128 | 120 | 0.00125 | 0.83815 |
| 8 | 192 | 184 | 0.000625 | 0.885178 |
| 8 | 192 | 176 | 0.000625 | 0.82775 |
| 8 | 128 | 120 | 0.000625 | 0.831111 |
| 12 | 192 | 184 | 0.000417 | 0.882352 |
| 12 | 192 | 176 | 0.000417 | 0.824521 |
| 12 | 128 | 120 | 0.000417 | 0.827088 |
| 24 | 192 | 184 | 0.000208 | 0.877611 |
| 24 | 192 | 176 | 0.000208 | 0.819131 |
| 24 | 128 | 120 | 0.000208 | 0.820356 |

---

## 7. Unresolved statistical choices

These are the questions the independent reviewer is being asked to settle.
They are unresolved on purpose; none of them may be closed by the drafting
party.

**U1. The I3 equivalence margin.**

n = 192 does not support a 0.05 aggregate margin at 0.90 power at any tested discordance rate, and supports a 0.10 margin only at discordance 0.05 and 0.10. The reviewer must choose between accepting a wider margin, increasing n, or demoting the aggregate criterion permanently. OD6 stays blocking until this is settled.

**U2. The I4 competence floor value.**

0.80 is proposed as a floor that is meaningfully above chance while remaining attainable by a 4B-class positive reference. It is not derived from any measurement, because no model has been run. The reviewer must confirm or replace it.

**U3. The I1a/I1b power shortfall at the nearest alternative.**

At n = 192 and alpha = 0.005 power is 0.874 at p = 0.97. Either the nearest alternative of interest is genuinely 0.98, in which case the design is adequate, or n must rise. The reviewer must state which.

**U4. The alpha allocation between Family A and Family B.**

The Bonferroni division by the selectable-surface count is conservative and simple, but a reviewer may prefer a sequential or hierarchical allocation that spends less alpha on surfaces that are ordered by preference in advance.

**U5. The unit of the I3 primary criterion.**

The per-base-item consistency indicator treats a base item as failing if any of its variants fails. This is deliberately strict. The reviewer must confirm that strictness is the intended estimand rather than an artefact.

**U6. Every sample size other than the provisional I1/I2 value.**

The confirmation-split size, the I3 size and the I4 size are proposals. OD5 stays blocking until the reviewer fixes them.

**U7. Whether the discordance-rate grid is wide enough.**

Rates 0.05, 0.10, 0.20 and 0.30 are covered. If plausible discordance exceeds 0.30 the sensitivity table must be extended before freeze.

**U8. The disclosed boundary type-I exceedance.**

Tango's score procedure is asymptotic, and exact enumeration shows one configuration in section 6.2 whose realised one-sided level is 0.025501 against a nominal 0.025. The reviewer must decide whether to accept the excess, to adjust the critical value so the realised level is never exceeded, or to replace the procedure with one that is conservative by construction.

The corresponding blocking operator decisions are: `OD2`, `OD5`, `OD6`.

---

## 8. Checklist for the independent reviewer

Please answer every item. An unanswered item is treated as unresolved and
keeps the draft unfrozen.

1. Are the atomic evaluation cells defined finely enough that no gate can be passed by averaging over a heterogeneous mixture?
2. Are the six pooling prohibitions sufficient, and is any additional pooling route still open?
3. Is the not-applicable third value handled correctly everywhere, in particular never counted as a pass and never counted as a zero effect?
4. Is the intersection-union treatment of Family A correct, and is the claim that it needs no multiplicity correction accepted?
5. Is Bonferroni division by the selectable-surface count the right treatment of Family B, or should a different allocation be used?
6. Is the exclusion of the never-selectable profile from the multiplicity count correct?
7. Is the per-base-item consistency indicator the right primary I3 estimand?
8. Is the demotion of aggregate paired equivalence to a secondary criterion acceptable, given the power finding in section 5.3?
9. Is the named paired method acceptable, and is the three-way verification in section 6.3 sufficient evidence that it is implemented correctly?
10. Is the exact type-I behaviour at the null boundary acceptable, including the single disclosed configuration whose realised level is 0.025501 against a nominal 0.025?
11. Is it clear and acceptable that *exact* here describes the enumeration and not a conservative-by-construction test?
12. Is the proposed I4 competence floor of 0.80 defensible before any model has been observed?
13. Is the rejection of the draft-v0.1 chance-level I4 null accepted?
14. Is the I1a/I1b power shortfall at p = 0.97 acceptable, or must n increase?
15. Are the proposed sample sizes adequate for every gate, including the confirmation split?
16. Is the discordance-rate grid wide enough?
17. Are the label-selection uniformity bands the right symmetry check, and is the Bonferroni level within them correct?
18. Are the descriptive Clopper-Pearson bounds clearly separated from the gate decisions?
19. Is any quantity in this packet presented as a measurement rather than as a proposed design parameter?
20. Is there any hypothesis in the protocol that is not stated in section 2?
21. Does any gate in section 3 authorise mechanistic execution, and is every failure route fail-closed?
22. Should any additional statistical choice be added to section 7 before this draft may be frozen?

**Reviewer disposition.** Please return exactly one of:

- `STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED`
- `STUDY3_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CHANGES`
- `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`

No disposition has been returned. This draft is therefore not frozen and no
execution authority exists.

