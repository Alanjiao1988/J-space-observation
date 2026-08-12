# Study 3 - next thread handoff

> **P0-R1 IS EXECUTION READY - THE REPLAY GATE IS THE ONE NEXT SESSION**
>
> States: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_6_COMPLETE_AWAITING_FINAL_FOCUSED_METHODS_REVIEW`
> and `STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE`.
>
> **The successor ordering is sequential, not a choice.** An earlier revision of
> this handoff presented the final focused methods review and P0-R1 execution as
> two interchangeable immediate successors. That was wrong: the controlling
> authority requires the final focused review only **after** P0-R1 reaches a
> terminal mechanically feasible disposition. The corrected order is:
>
> 1. **Execution-completion publication.** Done: the live replay gate, the
>    canonical result/receipt/disposition writers, the complete bounded model
>    runner, the Azure Container Apps T4 launcher and the immutable image digest
>    now exist. **Superseded by generation 2**, which additionally binds every
>    bound source by its bytes rather than by its path, transports complete
>    result bytes by two independent routes, injects the replay receipt into the
>    compute job, preserves completed partial results through any exception, and
>    validates all of it against the production route on the real
>    infrastructure. The binding object is now
>    `studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json`, pinned to image
>    digest
>    `sha256:5f964edb414b8a22682693d8314063693daca3b915398094ec008d2c03308827`.
>    Generation 1 is superseded **without consumption** and must not be launched.
> 2. **The fresh-session P0-R1 replay gate.** Continue from the published ready
>    commit `c7e02b43e1dbf811d1b35ae0fc0fe9d1a1d12947`, not from an older
>    baseline. The gate is replay-only: it reads the immutable P0-T artifacts and
>    performs zero new encodes and zero model operations. If it fails, publish
>    the registered stop and perform **no** model operation — do not repair and
>    rerun.
> 3. **Only if replay passes,** the single bounded GPU pilot, in that same
>    execution session, bound to the locked image digest and the replay-pass
>    receipt.
> 4. **Only after a mechanically feasible terminal P0-R1 disposition,** one
>    fresh, focused final methods review of draft-v0.6, scoped by authority
>    section 11 to the first-discriminative-token factorization, the classifier
>    repair, the affected accounting and the consistency of the resulting
>    candidate. It is **not** another general review and it **must not** reopen
>    unrelated resolved findings without a concrete contradiction in live v0.6
>    bytes. Start from
>    `studies/study3/analysis/final_focused_review_packet_v0_6.md`.
>
> Start from `studies/study3/pilot/p0_r1/P0_R1_HANDOFF_V2.md`, which is the
> corrected generation-2 handoff. `P0_R1_HANDOFF.md` is retained unedited as
> generation-1 history and its commands must not be used.
>
> **What the next thread may not do.** No freeze, no seed, no bank, no interface
> selection, no positive reference, no confirmation access, no `OD2` or `UR-22`
> resolution, and no evidence-ledger row. It **may never** edit a byte under
> `studies/study3/pilot/p0/` or `tests/test_study3_p0_feasibility_pilot.py`,
> rewrite the historical terminal state, or widen the pilot.
>
> Every P0-R1 counter is zero, the immutable P0-T counters are untouched, the
> evidence ledger still ends at `EV-0016`, and the original research question
> remains unanswered.


> **STUDY 3-P0 STAGE P0-T RAN AND STOPPED**
>
> State: `STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE`
>
> The CPU-only tokenizer and renderer census executed in the registered Azure
> container route and returned a registered fail-closed stop, published exactly
> as emitted. Stage P0-M was **not** begun: no checkpoint downloaded, no weight
> loaded, no GPU allocated, no forward pass, no generation.
>
> Findings: the independent renderer instantiated every applicable surface and
> all 4,902 member encodes round-tripped byte-exactly, so no unregistered
> normalization was in effect; **zero** byte-distinct pairs produced identical
> token-ID sequences anywhere in the 32-state census for any role; `S1`'s four
> label surfaces are distinct single tokens under both alphabets for all three
> roles; but `S2` and `S3` are `INELIGIBLE_TOKEN_IDS` for all three roles
> because each registered content surface `" 0"`..`" 9"` is **two** tokens
> (`[220, digit]`), so the registered single-position restricted-logit rule is
> not implementable as written.
>
> A defect in the gate's own eligibility classifier is disclosed rather than
> repaired: it propagated the role-level `S2` failure onto the `S1` cells, which
> made the emitted state more severe than this run's evidence supports. It is
> not fixed in this round, because stage P0-T is single-shot and no fix-and-rerun
> is authorized. See
> `studies/study3/pilot/p0/results/p0-t/P0_T_DISPOSITION.md`.
>
> `formal_execution_authorized = false`; `p0_pilot_execution_authorized` is now
> false because the one-shot authority is consumed. draft-v0.5 remains an
> unreviewed, unfrozen candidate; `OD2`, `UR-22` and every `RP` object remain
> unresolved; no seed, bank, winner or evidence row exists; the evidence ledger
> remains byte-identical through `EV-0016`.

> **STUDY 3-P0 FEASIBILITY PILOT REGISTERED - AWAITING THE TOKENIZER GATE**
>
> **State:** `STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE`
>
> The next thread does **not** begin the fourth independent methods review, and does **not** begin
> formal execution. A narrow operator decision authorizes one physically isolated, tightly capped
> feasibility pilot first, on `RT`, `RL` and `RI` only. Read
> [`prompts/study3_p0_feasibility_pilot_authority.md`](prompts/study3_p0_feasibility_pilot_authority.md)
> and [`pilot/p0/README.md`](pilot/p0/README.md) before anything else.
>
> **What is already done.** The authority copy is committed byte-identically and precedes every P0
> drafting artifact. The frozen corpus (35 contrast cells, 70 rendered members) is published before
> any tokenizer call and is immutable. The P0 protocol, counter ontology, schemas, tokenizer-gate,
> model-run, summarization and validation code, the digest-pinned container definition and 105
> negative and positive tests are registered. Registered targeted suites retained 276
> design/rendering and 88 v0.4-review passes.
>
> **What the next thread may do.** Exactly one thing: run stage **P0-T**, the CPU-only tokenizer and
> renderer gate, in the registered Azure container route, from the exact published pre-execution
> commit. If it passes, publish its result and receipt by non-force fast-forward and enter
> `STUDY3_P0_TOKENIZER_GATE_PASSED_AWAITING_MODEL_PILOT`, then run stage **P0-M** as one Azure
> containerized GPU job bound to that exact commit and tree.
>
> **What the next thread may not do.** Select an interface, set or revise a confirmatory threshold,
> answer the research question, resolve `OD2` or `UR-22`, freeze Study 3, authorize formal
> development or confirmation, draw a seed, build a bank, touch any `RP` object, write an evidence
> row, or change any prompt, parser, scoring, tokenizer, item, allocation, checkpoint or dependency
> in response to an observed P0 result.
>
> `formal_execution_authorized = false` throughout. P0 measurements are methods-feasibility
> observations, never Study 3 evidence. `paper/evidence_ledger.csv` remains byte-identical through
> `EV-0016`, and the original research question remains unanswered.

> **Study 3 draft-v0.5 bounded operator amendment - published, awaiting a FOURTH independent methods review**
>
> **State (superseded as the active state by the P0 round above, and otherwise unchanged):** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW`
>
> draft-v0.5 answers the ten `S3MR3-*` findings of the third independent methods review. Its
> blocking repair records `K6-SEP` as `not_applicable` for the option-less profiles `S2` and `S3`,
> which render neither an option label nor an option content, so each of them now carries exactly
> **one** genuine `I3` contrast, `K6-INSTR`. A byte-exact deterministic rendering registry is
> registered as a binding input. Re-derived: `S2` and `S3` fall from 19 gate-bearing cells to 16
> while `S1` stays at 43, so `m_max` remains 43 by derivation and the sizes `413`/`214`/`448` and
> their pass counts reproduce.
>
> **The only legal next action is a fresh-session fourth bounded independent methods review of
> published draft-v0.5, by a party that did not draft it.** Nothing is frozen, nothing is
> authorized, every operation counter is zero, no bank or seed exists, no interface and no positive
> reference is selected, and `OD2`, `UR-22` and the `RP` wrappers remain unresolved.

> **THIRD INDEPENDENT METHODS REVIEW COMPLETE - BOUNDED AMENDMENT REQUIRED**
>
> State: `STUDY3_DRAFT_V0_4_THIRD_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`
>
> Disposition: **`STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED`**, returned against reviewed commit
> `e865be51da6c7e1a7a4f5b1fcad0efc513bd0f43`, tree `86c5a5ec0e475090c14654cff27605f883495a48`.
>
> The third bounded independent methods review of draft-v0.4 verified 5 of the 10 inherited
> second-review findings resolved and 5 partially resolved, and recorded 1 BLOCKING,
> 3 MAJOR and 6 MINOR new findings (`S3MR3-001` through `S3MR3-010`), none of them
> fundamental. Every binding statistical number in the drafting derivation was independently
> reproduced with zero numeric disagreement.
>
> The blocking finding is that the `K6-SEP` contrast cell has no referent for the option-less
> selectable profiles `S2` and `S3`: `R-sep` differs from `R-base` only in the separator between a
> label and its option content, which neither profile renders, so under the registered
> deterministic scorer that cell is a self-comparison rather than a presentation pair. The major
> findings are that the derived statistics table still admits the never-selectable profile `S4` to
> two confirmation rows, that the retired `J_both` invariance construct and the withdrawn sample
> size `256` survive in active charter, README and handoff text, and that the deterministic
> rendering surface is unregistered so the two `K6` cells cannot be instantiated.
>
> Both construct verdicts are `ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR`. The narrowed
> `J_joint_correct` estimand does serve Study 3's instrument-calibration purpose, and excluding
> generation from the selectable set is correct rather than a gap. Read
> `reviews/v0_4_independent_methods_review.md`.
>
> The only legal next action is `OPERATOR_BOUNDED_AMENDMENT_ROUND_FOR_DRAFT_V0_5`, followed by a further independent methods
> review. **Not a freeze. Not `P3-Q`. Not a bank, a seed, model execution, a development round, a
> confirmation access, a feasibility pilot or any mechanistic work.**
>
> `OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`. The review neither resolves nor advances
> it, and the disposition is not driven by it.
>
> Study 3 remains unfrozen. No interface or positive reference is selected. No bank, seed, model
> operation, gate result, confirmation access or evidence row exists. Every operation counter is
> zero. The original research question remains unanswered.

## What the bounded amendment round must decide

The successor round is `OPERATOR_BOUNDED_AMENDMENT_ROUND_FOR_DRAFT_V0_5`. It is an operator amendment round, not a freeze and not an
execution authority. The reviewer does not design it; the following are the review findings it must
close, restated as the decisions they require.

1. `S3MR3-001` (BLOCKING). Decide, as a substantive design act, how the separator-rendering
   contrast applies to profiles that render no option list: record it `not_applicable` for `S2` and
   `S3` and re-derive their cell census and per-profile claim ceiling, or register a separator
   factor that exists in the option-less prompt, or state explicitly that those profiles carry a
   single genuine `I3` contrast. It may not be closed by editing claim text alone.
2. `S3MR3-010` (MAJOR). Register the byte-exact rendering surface - stem, option-line format,
   `R-base` and `R-sep` separators, `R-base` and `R-instr` instruction sentences, and the answer
   cue for each profile - and re-derive `K6` applicability from the registered strings.
3. `S3MR3-002` (MAJOR). Regenerate the derived statistics table so its confirmation applicability
   agrees with the amended protocol, give it a per-component row shape, and bind that field in a
   committed assertion.
4. `S3MR3-003` (MAJOR). Bring the charter, both READMEs and this handoff into conformance with the
   registered v0.4 design, or mark the superseded passages unambiguously as historical narrative.
5. `S3MR3-004` through `S3MR3-009` (MINOR). Widen or narrow the prohibited-term enforcement to
   match its declared scope; remove `I4` from `S4`'s applicable gate list; reconcile the registered
   stop-state sets; disclose the sample-size non-monotonicity; correct the stale round references;
   and either define `designated` as the highest-priority adequate profile or restate the
   end-to-end conclusion over an adequate profile.

`OD2` is untouched and remains a blocking operator decision. No positive reference is selected,
preferred, pinned, revision-resolved, downloaded, tokenized, loaded or prequalified.

A fundamental rejection was considered and not earned, so the round limit rule does not apply and
no feasibility-pilot authority exists. No successor prompt was created by this review.

**State: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_4_COMPLETE_AWAITING_THIRD_INDEPENDENT_METHODS_REVIEW`**

**Draft version: `draft-v0.4`, amended, unfrozen, awaiting the THIRD independent
methods review.**

draft-v0.4 is the operator amendment answering the ten findings of the second
independent methods review (`S3MR2-001` through `S3MR2-010`: 2 BLOCKING, 6 MAJOR,
2 MINOR), together with the twenty inherited first-review findings and the twenty-two
unresolved items. The record is `reviews/v0_4_operator_amendment.md` and the review
object is `analysis/independent_methods_review_packet_v0_4.md`.

**The drafting party does not claim draft-v0.4 is correct.** Every repair is recorded
as `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`. Both independent reviews remain
valid rejections and neither was edited.

**The only legal next action is a THIRD bounded independent methods review of
draft-v0.4, conducted in a fresh session by a party that did not draft it. Not a
freeze. Not `P3-Q`. Not a bank, a seed, model execution, a development round, a
confirmation access or any mechanistic work.**

`OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`. No positive reference is
selected, preferred, pinned, revision-resolved, downloaded, tokenized, loaded or
prequalified. draft-v0.4 registers only the binding ordering constraint
`P3Q >= 19/20 > I4 p1 = 9/10 > I4 p0 = 4/5`.

**Section 11 records the draft-v0.4 operator amendment round and supersedes any
earlier section where they disagree.**

---

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
   *(Historical record only: the six questions above were posed to the FIRST
   independent methods reviewer of draft-v0.2 and were answered by that completed
   review. They are retained verbatim as immutable provenance, they name no
   pending review, and they describe no current design.)*

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

**Three `I3` indicators, one primary.** *Historical record only: this paragraph
describes draft-v0.3, which the second independent methods review rejected and
which draft-v0.4 and then draft-v0.5 superseded. The construct named here is
withdrawn and is not current; the active indicator is `J_joint_correct`.* `J_inv`
is invariance across the two variants, `J_cor` is correctness against the
registered ground truth, and `J_both` is their conjunction and the then primary
gate indicator. A stable but **wrong** answer scores `0`; a stable invalid or
unparseable answer scores `0`. That `J_cor` implies `J_inv` under a unique ground
truth is recorded as an expected integrity property rather than presented as
independence.

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


## 11. The draft-v0.4 operator amendment round - outcome

This round answered the second independent methods review and published an amended,
**still unfrozen** draft for a third independent methods review. It selected nothing,
froze nothing, authorised nothing and measured nothing.

| finding | severity | repair |
| --- | --- | --- |
| `S3MR2-001` | BLOCKING | the gate indicator becomes `J_joint_correct`, an explicit level over the registered item-generating distribution; invariance, equivalence and presentation-effect language is removed from every active claim field and the per-profile claim ceiling is made exact |
| `S3MR2-002` | BLOCKING | an arbitrary-dependence union-bound type-II architecture with `m_max = 43`, per-cell budget `19/17200`, per-cell target `17181/17200`, profile stage floor `381/400` and end-to-end floor `9/10`, each with an explicit scope label |
| `S3MR2-003` | MAJOR | every development size re-derived as the smallest unrestricted positive integer meeting the per-cell target: `413`, `214`, `448`, with minimal pass counts `389/129/383` and `388/127/381` |
| `S3MR2-004` | MAJOR | confirmation applicability becomes the intersection of a component's selectable profiles with the single selected profile; `S4` never appears and `I1b` and `K5` are confined to `S1` |
| `S3MR2-005` | MAJOR | the `S4` diagnostic stream carries a derived forward cost: `26,064` generation calls and prefills, `390,960` incremental decode evaluations and a `417,024` sequence-evaluation upper bound |
| `S3MR2-006` | MAJOR | a total, deterministic state machine with one next state per event, every terminal reachable, and an `I0` failure mapping only to `STOP_INSTRUMENT_DEFECT` |
| `S3MR2-007` | MAJOR | the 32-state `K5` support is drawn iid with replacement at exact weight `1/32`; the deterministic complete-block assignment and the multiple-of-32 size restriction are retired |
| `S3MR2-008` | MAJOR | the `I0` fixture accounting is reconstructed from a registered breakdown: `232` clusters, `232` base items, `464` cluster rows, `38` non-cluster rows, `502` total |
| `S3MR2-009` | MINOR | the binding ordering constraint `P3Q >= 19/20 > I4 p1 = 9/10 > I4 p0 = 4/5` is registered without selecting any candidate |
| `S3MR2-010` | MINOR | a binding sampling frame for all 34 sampling cells licenses the exact-binomial estimand in every gate-bearing atomic cell |

The four first-review findings the second reviewer marked `PARTIALLY_RESOLVED`
(`S3MR-002`, `S3MR-013`, `S3MR-014`, `S3MR-017`) are proposed fully resolved only through
the corresponding draft-v0.4 repair and remain review-pending.

**Preserved without repair.** The second review's `disposition_basis` sentence says
"Two BLOCKING and eight MAJOR methods defects remain" while its structured findings are
2 BLOCKING, 6 MAJOR and 2 MINOR. That mismatch is recorded as
`NON_DISPOSITIVE_HISTORICAL_NARRATIVE_COUNT_MISMATCH`. The review is **not** edited, and
the narrative MAJOR count is never propagated as the structured finding count.

**Boundary.** Every operation counter is exactly zero. No bank, seed, model operation,
gate result, confirmation access, result row or evidence row exists. Nothing is frozen
and no execution is authorised. The evidence-ledger tail remains `EV-0016`. Study 1 and
Study 2 remain closed and untouched, and the original research question remains
unanswered.

## 12. Historical-review test-harness scope erratum

Before draft-v0.4 was published, the committed draft-v0.3 regression module
`tests/test_study3_methods_review_v0_3.py` was found to contain a scope defect: two of its checks
read live index or working-tree bytes although their stated purpose is to validate draft-v0.3
against its reviewed historical inputs. The authorized draft-v0.4 amendment therefore broke them,
which is the harness misbehaving rather than the draft.

Both checks are now anchored to `REVIEWED_COMMIT` `2b36f5321d830ea6f70fff2b7bbca3cb93394046`.
The recalculation check runs the **unchanged** v0.3 generator and **unchanged** committed v0.3 table
inside an isolated snapshot built from that commit, and asserts that no current-draft byte is
reachable from it.

This is a test-harness erratum, **not** an amendment to the second independent methods review. Its
findings, its rejection disposition and every reviewed-artifact identity are untouched, and no
draft-v0.4 scientific content changed. The module keeps exactly its 35 node IDs; no assertion was
deleted, weakened, skipped or xfailed.

The third independent methods review of draft-v0.4 should treat
`tests/test_study3_methods_review_v0_3.py` as an amended path in the published set, read section 8
of `studies/study3/reviews/v0_4_operator_amendment.md` for the full record including the verbatim
supplemental authority, and note that `AR-0246` deliberately retains the pre-erratum identity of
that module while the new row records the corrected one.
