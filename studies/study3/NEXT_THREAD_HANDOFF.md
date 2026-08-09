# Study 3 - next thread handoff

**State:
`STUDY3_DRAFT_V0_3_SECOND_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`**

**Draft version: `draft-v0.3`, amended, unfrozen, SECOND independent methods review
complete.**

**Second independent methods review disposition:
`STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`**, returned against the
reviewed commit `2b36f5321d830ea6f70fff2b7bbca3cb93394046`, tree
`98d71cb35cca7b55d8f96f131064a5b9654dd3c7`.

The review adjudicated all 20 inherited findings (`S3MR-001` through `S3MR-020`) and
all 22 unresolved items (`UR-01` through `UR-22`) on independent evidence, and recorded
10 new findings `S3MR2-001` through `S3MR2-010`: 2 BLOCKING, 6 MAJOR, 2 MINOR. It
independently reproduced every registered exact-binomial threshold, tail and power, the
sixteen-row selection map, the construction laws and every operation total, and it
confirmed that the Tango paired aggregate-equivalence procedure is retired from every
decision role with no residual decision path.

**The only legal next action is `OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_4`, followed by
another independent methods review. Not a freeze. Not `P3-Q`. Not a bank, a seed, model
execution, a development round, a confirmation access or any mechanistic work.**

`OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`. The review neither resolves nor
advances it, and no positive reference is selected, preferred, pinned, revision-resolved,
downloaded, tokenized, loaded or prequalified.

| authority flag | value |
| --- | --- |
| `frozen` | `false` |
| `execution_authorized` | `false` |
| `bank_authorized` | `false` |
| `seed_authorized` | `false` |
| `model_operations_authorized` | `false` |
| `winner_selected` | `false` |
| `positive_reference_selected` | `false` |
| `confirmation_access_authorized` | `false` |

Sections 1 through 8 below are the historical record of the draft-v0.2 round and
are unchanged. Section 9 records the first review's outcome. Where section 5 asks
what the independent methods review should check, section 9 records what it found.
**Section 10 records the draft-v0.3 operator amendment round and supersedes any
draft-v0.2 statement it contradicts.**

---

## 1. What this round did

This round was a single design-amendment round. It produced draft-v0.2 in
response to an operator review that found ten defects in draft-v0.1 and
refused freeze under
`STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`.

- Recorded the ten defects and their resolutions additively in
  `reviews/v0_1_operator_review.md`. The draft-v0.1 artifacts were not
  rewritten to hide them, and `design_receipt.json` was left untouched as the
  historical v0.1 receipt.
- Rewrote the protocol as draft-v0.2. The **JSON is now authoritative** and the
  Markdown is a companion rendering; the unsupported claim that both were
  generated from one source of record was removed, because no such generator is
  committed.
- Replaced `candidate_interfaces` with `interface_profiles` carrying a
  pre-registered `selectable_status`, an explicit applicability map, and a
  declared list of transformations that have no referent for that profile.
- Replaced the data-dependent selection rule with a published `admissibility_order`
  fixed in advance, and stated plainly that no interface is selected in this
  round. draft-v0.1 contained a direct contradiction on this point.
- Made `not_applicable` a real third value that is neither a pass nor a zero
  effect.
- Split the old fused `I1` into `I1a` (trivial content recovery and output
  validity) and `I1b` (explicit content-to-symbol binding), so a binding failure
  can no longer be mistaken for a recovery failure.
- Made `I4` part of eligibility, failing **per interface profile** rather than
  stopping the whole study, and extended `I5` to cover every gate-bearing
  construct including `I4`.
- Derived every proposed number in a **committed** model-free script,
  `analysis/design_statistics.py`, with a `--check` mode that recomputes the
  committed tables value-for-value.
- Committed the design invariants as a real test, `tests/test_study3_design.py`,
  including a negative-mutation battery. In draft-v0.1 the equivalent checker
  was ephemeral and missed a defect; that process failure is itself recorded.
- Built the bounded independent-methods-review packet and the positive-reference
  candidate dossier from primary sources.

### The substantive statistical finding of this round

draft-v0.1 asserted an aggregate paired-equivalence margin of 0.05 without any
paired power analysis. Exact enumeration now shows that at `n = 192` and a
target power of 0.9:

- margin 0.05 is supported at **no** tested discordance rate;
- margin 0.10 is supported only at discordance 0.05, 0.1.

The drafting party is not permitted to fix this by widening the margin until it
fits the sample size. The aggregate criterion was therefore demoted to a
secondary one, an exact per-base-item consistency criterion was made primary,
and `OD6` was left blocking for the reviewer.

A second finding is disclosed rather than absorbed: the named paired method is
Tango's asymptotic score procedure, and exact enumeration finds one
configuration whose realised one-sided level is 0.025501 against a nominal
0.025. See section 6.3.1 of the review packet.

## 2. What this round did not do

| operation | count |
| --- | --- |
| `model_downloads` | 0 |
| `model_weight_loads` | 0 |
| `tokenizer_constructions` | 0 |
| `forward_passes` | 0 |
| `generations` | 0 |
| `activation_extractions` | 0 |
| `lens_operations` | 0 |
| `probe_operations` | 0 |
| `patching_operations` | 0 |
| `ablation_operations` | 0 |
| `gpu_jobs` | 0 |
| `provider_calls` | 0 |
| `bank_rows_generated` | 0 |
| `seeds_drawn` | 0 |
| `evidence_rows_created` | 0 |
| `phase_1_0d_operations` | 0 |
| `rq2_s4_operations` | 0 |
| `interfaces_selected` | 0 |
| `positive_references_selected` | 0 |
| `confirmation_split_accesses` | 0 |
| `study1_files_modified` | 0 |
| `study2_files_modified` | 0 |

No interface was selected. No positive reference was selected or pinned. No
threshold was frozen. No bank exists. No seed was drawn. No evidence row was
created. Study 1 and Study 2 were not modified in any way, and neither
protected Phase 1.0D rollup changed.

The amendment resolved four of the eight open decisions and part of a fifth. It
resolved **none** of the three blocking ones.

## 3. Decisions the operator must make

| id | decision | blocking | draft-v0.2 disposition |
| --- | --- | --- | --- |
| `OD1` | Should all three target checkpoint roles RT, RL and RI be retained, or should the panel be narrowed? | no | retain RT, RL and RI. All three are required for the later distillation, lineage and instruction contrast, and each gate is evaluated per role. |
| `OD2` | Which model serves as the positive reference, and what canonical qualification wrapper does it use? | **yes** | candidate dossier only. No positive reference is selected. The RP canonical qualification wrapper and the RP-specific I4 wrapper must be frozen before P3-Q and I4. |
| `OD3` | Should the free-generation surface S4 be retained in the panel? | no | retain S4 only as a non-selectable diagnostic. It never enters admissibility and can never be selected. |
| `OD4` | How many rendering variants should the K6 stratum carry, and what may each vary? | no | exactly three one-factor renderings: baseline, separator-only and instruction-wording-only. The answer cue is held constant across all three. |
| `OD5` | What are the statistical thresholds for I3 and I4? | **yes** | the I1 and I2 proposals may remain provisional. The I3 method and margins and the I4 competence floor require independent review. The chance-floor I4 proposal from draft-v0.1 is rejected. |
| `OD6` | What sample sizes does the design require? | **yes** | n = 192 may remain a provisional I1 and I2 value. It is not an I3 justification. Confirmation and I3 sizes await the reviewed power analysis. |
| `OD7` | Is independent review required before freeze? | no | yes. A bounded independent review of the statistics and the gate logic is mandatory before freeze and before any bank construction or seed draw. |
| `OD8` | What chat-template policy applies to each role on each surface? | no | no chat template for RT, RL or RI on S1, S2 or S3. S4 uses each role's native template or explicitly records its absence. The RP canonical qualification wrapper and the RP-specific I4 wrapper remain part of OD2 and must be frozen before P3-Q and I4. No cross-role byte parity is claimed where native wrappers differ. |

Blocking decisions: `OD2`, `OD5`, `OD6`.

## 4. The three blocking decisions, in the order they bite

### `OD2` - the positive reference

This is the one that can stop the study before it starts. Without a checkpoint
independently expected to succeed, a Study 3 null would be exactly as
uninterpretable as Study 2's was, which is the whole reason `I4` exists.

`references/positive_reference_dossier.md` now evaluates named candidates from
primary sources against the registered Tesla T4 envelope. It **selects nothing**
and **pins nothing**. Its conclusion is that a 4B-class Apache-2.0 instruction
model is the only examined option that both fits the registered route in fp16
with real headroom and is plausibly capable on the compositional strata, and
that using it would require registering a **new image**, because it needs a
newer transformers than the Study 2 image provides.

Whatever authority resolves `OD2` must preregister exactly one candidate with
its immutable revision, runtime, dtype, wrapper, qualification interface, bank,
floor, sample size and stopping rule, before any model operation. There is no
automatic fallback to a larger model: if the preregistered candidate fails, the
prequalification stage stops. That rule is what removes adaptive reference
shopping, where the 'positive control' silently becomes whichever model
happened to pass.

Quantizing a larger model to force a fit is prohibited, because the interfaces
read logits and quantization changes exactly the quantity being measured.

### `OD5` - the thresholds

The `I1a`/`I1b`/`I2` proposals may remain provisional. The `I3` method and
margins and the `I4` competence floor require independent review. The
chance-level `I4` null proposed in draft-v0.1 is **rejected**: a positive
reference that merely beats chance is not a positive control, because a model
scoring just above chance cannot demonstrate that a working interface would
register competence. The replacement is a competence floor of 0.8.

### `OD6` - the sample sizes

`n = 192` may remain a provisional `I1`/`I2` value. It is **not** an `I3`
justification, for the reason in section 1. The confirmation-split size and the
`I3` size await the reviewed power analysis.

## 5. What the independent methods review should check

The bounded packet is `analysis/independent_methods_review_packet.md`. It
contains the estimands and atomic units, every null and alternative, the gate
truth table and legal stop states, the multiplicity and selection logic, the
proposed margins and floors, the power and sample-size sensitivity tables, eight
unresolved statistical choices, and a numbered reviewer checklist with three
permitted dispositions.

The reviewer is specifically asked to rule on:

1. whether the atomic cell is fine enough that no gate can be passed by
   averaging over a heterogeneous mixture;
2. whether the intersection-union treatment within a profile, and the Bonferroni
   treatment across selectable profiles, are the right split;
3. whether the per-base-item consistency criterion is the right primary `I3`
   estimand and whether demoting aggregate equivalence is acceptable;
4. whether the disclosed boundary type-I exceedance is acceptable or the
   critical value must be adjusted;
5. whether the `I4` competence floor is defensible before any model is observed;
6. whether the `I1a`/`I1b` power shortfall at the nearest alternative requires a
   larger n.

## 6. What a future authorized execution would need, in order

1. An independent methods review disposition.
2. Operator resolution of `OD2`, `OD5` and `OD6`.
3. A freeze authority for the amended protocol. **No freeze prompt exists and
   this document does not constitute one.**
4. A separate authority registering the image and runtime for the positive
   reference.
5. A separate prequalification authority for stage P3-Q.
6. A separate authority for bank construction and the seed draw.
7. A separate authority for development execution.
8. A separate authority, after the development result is sealed, for the
   one-shot confirmation.

Each step is a distinct authority. None of them is implied by the previous one.

## 7. Boundaries that remain in force

- Nothing in `studies/study3` is frozen and nothing authorizes execution.
- No Study 1 or Study 2 file, seal, bank, manifest or decision was modified, and
  neither study was reopened or reinterpreted.
- No evidence row was added; `paper/evidence_ledger.csv` still ends at its
  previous final row.
- The ten review defects are recorded as defects in an unfrozen design document,
  **not** as limitations in `paper/limitations_ledger.md`, which this repository
  reserves for limitations of executed measurement.
- The claim ceiling is unchanged in both directions: a future pass would
  establish only that the named interface met its registered gates for the named
  tasks and roles; a future fail would establish only that no candidate profile
  met them under the registered conditions, and specifically **not** that the
  model is incapable. Neither direction is evidence about reasoning,
  distillation, J-space or J-lens.

## 8. Status of the other studies

**Study 1.** Study 1's frozen raw-completion, no-chat-template, single-token E0 surface yielded too few behaviorally eligible items to populate confirmation. Parser-v2 separately failed its locked gate, while parser-v3 remained nonauthoritative. These facts motivate prospective interface validation but do not establish that parsing caused E0's eligibility collapse.

*Classification: motivation only; this does not establish that parsing caused the collapse.*

**Study 2.** Study 2 remains closed and unchanged. Its post-hoc response-pattern diagnostic remains zero-authority motivation only.

*Classification: closed and unchanged; zero-authority motivation only.*

## 9. Independent methods review of draft-v0.2 - outcome

The bounded independent methods review authorised after the draft-v0.2 round is
complete. It was carried out in a fresh session by a party that did not write the
design, and it re-derived every design statistic from the cited primary sources in
an implementation that never reaches `analysis/design_statistics.py`.

**Disposition: `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`.** draft-v0.2
is not approved for freeze and not approved for execution.

Six blocking findings:

- **S3MR-001** the `I3` primary estimand is not identifiable. `I3` is defined over
  the variants of a base item, but the committed counterbalancing construction
  assigns exactly one `(position, symbol)` pair per base item and no field states
  how many variants a base item has for any profile. The denominator does not
  exist in the document.
- **S3MR-002** the `I3` primary indicator has two incompatible definitions: the
  authoritative JSON scores identical-answer-across-variants, the review packet
  scores all-variants-correct. A stably wrong answer passes one and fails the
  other.
- **S3MR-003** the Family B per-profile `alpha = 0.001666666667` is asserted while
  every retained component rule is computed at `alpha = 0.005`. The union bound
  over three selectable profiles at the implemented level is `0.015`.
- **S3MR-004** the authoritative JSON asserts that exact enumeration does not
  exceed the nominal one-sided level, while the packet and the methods ledger
  disclose a realised `0.025501`. The independent enumeration reproduces
  `0.025501092`, so the enumeration is right and the claim about it is wrong.
- **S3MR-005** the four discordance values are a sensitivity grid, not proof of
  size control. Maximising over the full feasible null boundary finds
  `0.025073` at `n = 384`, `margin = 0.10`, discordance about `0.478`, which the
  grid never evaluates.
- **S3MR-006** the `I3` floor at `p0 = 0.95` is unreachable: no admissible sample
  size up to 768 attains target power `0.90` at the stated per-profile level.

Eleven further findings are MAJOR and three are MINOR. Seventeen candidate
cross-artifact inconsistencies were adjudicated: six `CONFIRMED_BLOCKING`, eight
`CONFIRMED_NONBLOCKING`, one `NOT_CONFIRMED`, two `QUALIFIED`.

**What the review did not do.** It selected no interface and no positive
reference; `OD2` remains entirely an operator decision and no checkpoint was
named, pinned, downloaded, tokenized, loaded, run, prequalified or substituted.
It supplied explicit methods recommendations for `OD5` and `OD6` but **did not
adopt them**; they are reviewer recommendations, not protocol. It did not repair
the review object: where the committed design test itself encodes a circular
verification, that was recorded as finding S3MR-009 and
`tests/test_study3_design.py` was left untouched. All 22 operation counters
remain zero.

Read `reviews/v0_2_independent_methods_review.md` for the full audit, the 22
answered checklist questions, the reviewed parameter table, the executable
multiplicity decision graph and the projected operation table;
`reviews/v0_2_independent_methods_review.json` is its authoritative machine-readable
form; `methods_review_receipt_v0_2.json` binds the round.

---

## 10. The draft-v0.3 operator amendment round - outcome

The operator amendment round authorised after the review in section 9 is complete.
It repaired the design against all 20 findings and all 22 unresolved items and
published an amended, **still unfrozen** draft for a second independent methods
review. It performed **zero** empirical and zero model operations of any kind.

**Sections 1 through 9 are historical. Where section 3 or section 4 states an
`OD5` or `OD6` disposition, section 10 supersedes it.**

### 10.1 What the amendment adopted

| decision | draft-v0.2 state | draft-v0.3 state |
| --- | --- | --- |
| `OD5` thresholds and multiplicity | open, blocking | **resolved**, subject to the second review |
| `OD6` sample sizes | open, blocking | **resolved**, subject to the second review |
| `OD2` positive reference | open, blocking | **still `UNRESOLVED_BLOCKING_OPERATOR_DECISION`** |

**`I3` is now a pre-registered pairwise design.** The independent unit is a
`base_item_contrast_cluster` carrying exactly **2** variants. There is no
cross-product and no factorial multiplication of variants; `K5` and `K6` are not
crossed and use disjoint base-item identities. `K5` is exactly seven one-factor
contrasts - `K5-P1`, `K5-P2`, `K5-P3` for content-position offsets `+1`, `+2`,
`+3` modulo 4; `K5-S1`, `K5-S2`, `K5-S3` for correct-displayed-symbol-index
offsets `+1`, `+2`, `+3` modulo 4; and `K5-A1` for label-alphabet replacement,
using two label alphabets disjoint from the answer domain with digits forbidden.
`K5` is `not_applicable` for `S2` and `S3` rather than passing. `K6` is two
disjoint pairwise cells, `K6-SEP` and `K6-INSTR`, drawn from the three renderings
`R-base`, `R-sep` and `R-instr`, with the answer cue and every other byte held
fixed. Balancing is deterministic over complete blocks with bijective
option-to-label mappings; **no random draw occurs anywhere in this design round.**

**Three `I3` indicators, one primary.** `J_inv` is invariance across the two
variants, `J_cor` is correctness against the registered ground truth, and
`J_both` is their conjunction and the **primary gate indicator**. A stable but
**wrong** answer scores `0`; a stable invalid or unparseable answer scores `0`.
That `J_cor` implies `J_inv` under a unique ground truth is recorded as an
expected integrity invariant rather than presented as independence.

**`OD5`: an exact-binomial primary design in exact rational arithmetic.** A
study-level development screening alpha of `1/200`; a per-profile development
component alpha of `1/600`; an intersection-union conjunction within a profile, so
no further within-profile Bonferroni applies; and a **fixed** selectable-profile
denominator `K = 3` that never shrinks on a post-data fact. Decimal fields are
renderings of the exact rational policy and are never the source of truth.

**`OD6`: one `I3` floor.** `p0 = 0.90` against `p1 = 0.97` at power at least
`0.90`, giving `n = 256` base-item contrast clusters per applicable contrast cell.
The floor `p0 = 0.95` is **deleted** from every active protocol, table and packet
field and is permitted only in clearly labelled historical narrative, because the
review established it was unreachable at any admissible sample size. No active
rejection region has a pass count equal to `n`.

**Every symbol `n` carries a unit.** Four units are registered - `base_item`,
`base_item_contrast_cluster`, `rendered_row`, `scored_row` - at their definitions
and in every table, and one `n` is never reused across them.

**The paired aggregate-equivalence procedure is retired from every decision
role.** It supplies no gate, eligibility rule, selection rule, confirmation rule,
claim language, equivalence margin, critical value, discordance grid,
conservativeness statement, rescue path or ranking weight. Only purely descriptive
paired 2x2 summaries survive, with no null, no alpha, no p-value and no pass or
fail. The reviewer's independent recalculation is preserved unedited as immutable
historical evidence, and the second reviewer is **explicitly asked to adjudicate
whether retirement fully removes the size-control defect.**

**Operation accounting is decomposed.** Under the current single-token answer
domain, `S3` adds exactly **0** forward passes and **0** sequence-scoring rows
beyond `S2`. The projection is decomposed into six named work streams with
per-stream units; a single undifferentiated total is prohibited.

**Derivation, not transcription.** The reviewer-returned development and
confirmation target tables are planning targets that the committed script
**independently derives**. The committed test asserts by AST inspection that those
targets appear nowhere in the script as literal constants.

### 10.2 What the amendment did not do

- It did not freeze the design and did not approve it for execution.
- It did not select, prefer, pin, revision-resolve, download, tokenize, load or
  prequalify any positive-reference checkpoint. `OD2` and `UR-22` remain
  `UNRESOLVED_BLOCKING_OPERATOR_DECISION`, and the dossier says `UNSELECTED`.
- It did not select an interface profile, draw a seed, create a bank row, create
  an evidence row or add a limitations row.
- It did not perform a single model download, revision resolution by downloading,
  tokenizer construction, tokenization, weight load, forward pass, sequence
  scoring, generation, activation extraction, hook, lens, probe, patch, ablation,
  provider API call or GPU job. Every operation counter is exactly zero.
- It did not touch any Study 1 or Study 2 path, `paper/evidence_ledger.csv`,
  `paper/limitations_ledger.md`, `paper/claim_evidence_matrix.md`, any dependency,
  lockfile, Dockerfile, runtime, model source, infrastructure or workflow.
- It did not edit any v0.2 review object. All three
  `reviews/v0_2_independent_methods_review.*` files,
  `methods_review_receipt_v0_2.json`, both
  `analysis/independent_methods_recalculation*` files, the v0.2 review authority
  copy, `analysis/independent_methods_review_packet.md` and
  `design_receipt_v0_2.json` are byte-identical to the reviewed round.
- **It did not declare the amended protocol correct**, and it did not execute or
  predeclare the disposition of the second independent methods review.

### 10.3 The legal next action

A **second** bounded independent methods review of draft-v0.3. Its review object
is `analysis/independent_methods_review_packet_v0_3.md`, with
`protocol/interface_calibration_protocol_draft.json` authoritative and
`reviews/v0_3_operator_amendment.md` recording the disposition of every finding
and every unresolved item.

Questions the drafting party puts to that reviewer:

1. Does retiring the paired aggregate-equivalence procedure from every decision
   role fully remove the size-control defect recorded in `S3MR-004` and
   `S3MR-005`, or does a residual decision path remain anywhere in the amended
   protocol?
2. Is the base-item contrast cluster with exactly two variants an identifiable
   unit for the `I3` estimand under every registered contrast cell, and does
   `J_both` estimate what the protocol says it estimates?
3. Is the intersection-union treatment within a profile, combined with a fixed
   denominator of `3` across profiles and a one-shot confirmation at `1/200` on a
   physically disjoint split, an adequate multiplicity architecture for the claim
   the protocol permits?
4. Does the six-stream operation projection make the feasibility question
   answerable, and is the zero-incremental-cost argument for `S3` under a
   single-token answer domain correct as stated?
5. Are any of the twenty repairs cosmetic relabelling rather than substantive
   design change?

No freeze prompt, no `P3-Q` prompt, no bank prompt, no seed prompt, no model
prompt, no GPU prompt, no development prompt, no confirmation prompt and no
mechanistic-execution prompt exists, and none may be produced by this round.
