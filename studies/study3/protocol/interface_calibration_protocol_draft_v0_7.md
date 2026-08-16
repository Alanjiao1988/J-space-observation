# Study 3 - interface adequacy and label-binding calibration, draft-v0.7

> **State:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_7_COMPLETE_AWAITING_SINGLE_FOCUSED_METHODS_REVIEW`
>
> draft-v0.7 is **not** reviewed, **not** frozen, **not** selected and
> **not** formally executable. `frozen = false` and
> `execution_authorized = false`. The determination belongs to a party
> that did not draft it.

The JSON protocol is normative. This Markdown is its companion and
agrees with every decision-bearing JSON marker below.

Normative JSON:
[`interface_calibration_protocol_draft_v0_7.json`](interface_calibration_protocol_draft_v0_7.json).

## How this document is bound to the JSON

Each section carries a decision marker of the form `V07-Dnn`. Every
marker occurs exactly once here and exactly once in
`decision_markers_v0_7`, and each names a real top-level JSON key. The
committed tests fail if a marker is missing, duplicated or unresolvable.

| marker | decision | JSON key |
| --- | --- | --- |
| `V07-D01` | Dual estimands E0 and D0, and the claim ceiling | `estimands_v0_7` |
| `V07-D02` | E0 answer surfaces, parser and decoding contract | `e0_answer_and_decoding_contract` |
| `V07-D03` | Full-context tokenization and D0 diagnostics | `full_context_tokenization_and_d0_diagnostics` |
| `V07-D04` | The registered I1a/I1b/I2 competence-floor battery is retained | `competence_floor_battery_v0_7` |
| `V07-D05` | Wrapper-only matched contrast and joint adequacy | `wrapper_matched_contrast_v0_7` |
| `V07-D06` | Canonical generated-CoT ceiling | `generated_cot_ceiling_v0_7` |
| `V07-D07` | Q0 prequalification and the RP-B ladder | `q0_and_rp_b_v0_7` |
| `V07-D08` | RP-B and RP-M are separate constructs | `rp_b_and_rp_m_separation_v0_7` |
| `V07-D09` | Per-checkpoint functional equivalence | `checkpoint_functional_equivalence_v0_7` |
| `V07-D10` | Engineering shakedown authority and its numeric bounds | `engineering_shakedown_authority_v0_7` |
| `V07-D11` | Recursive-manifest seal | `recursive_manifest_seal_v0_7` |
| `V07-D12` | Activation and causal-claim boundary | `activation_and_causal_claim_boundary_v0_7` |
| `V07-D13` | Copy-on-write protocol placement | `protocol_placement_v0_7` |
| `V07-D14` | Deterministically deferred values and their fail-closed states | `deterministic_deferrals_v0_7` |

## Placement, and why draft-v0.7 is a new bundle `[V07-D13]`

The operator selected `OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL`.

The immutable P0 corpus manifest byte-binds the legacy protocol JSON, so
a single changed byte makes `p0_freeze_corpus.py --check` fail. draft-v0.7
is therefore a **new, self-contained bundle** written beside the legacy
files, which keep status `HISTORICAL_P0_BINDING_ONLY_NOT_CURRENT_PROTOCOL`
and are unchanged. The P0 corpus manifest was not regenerated and the
frozen-corpus test was not retired, weakened or waived.

Every legacy top-level key is carried forward, so an executor reads one
protocol plus the exact subordinate assets it names, and never layers
v0.5, v0.6 and v0.7 by hand.

## Estimands `[V07-D01]`

**E0** - `E0_zero_generated_reasoning_token_expressed_competence` is the
primary behavioral endpoint: the model emits a correct registered answer
surface **without emitting generated reasoning tokens**. For multi-token
answers, answer-token autoregression is explicitly part of the estimand.
E0 does not establish absence of internal computation and is never
described as one forward pass or as proof that reasoning was absent.

**D0** - `D0_single_forward_decodability` is a secondary conditional
mechanism claim, permitted only as: under the frozen counterfactual
readout, discriminant information was decodable from one registered logit
read. D0 covers only the registered discriminant, enters neither Q0 nor
the RP-B gate, and is reported separately from E0.

## E0 answer and decoding contract `[V07-D02]`

| item | value |
| --- | --- |
| legal surfaces | `" 0"`..`" 9"`, one leading U+0020 each |
| matching | full-sequence exact match; prefix match prohibited |
| `7 because...` | incorrect |
| unparseable or out-of-domain | incorrect, never dropped |
| `do_sample` | `false`, the actual deterministic switch |
| sampling-only parameters | recorded `INACTIVE_do_sample_false` |
| `max_new_tokens` | 3 |
| EOS margin | 1 token |
| batch size / padding side | 1 / left |
| reproducibility | byte-exact, tolerance 0 |

Temperature alone is never the switch. Exact reproducibility is defined
operationally: every decision-bearing artifact must reproduce with an
identical SHA-256 under the sealed recursive manifest.

## Full-context tokenization and D0 diagnostics `[V07-D03]`

All eligibility and scoring proofs use the actual complete context,
`rendered_prompt_bytes + candidate_surface_bytes`. Full-context
tokenization is never inferred from candidate-only encoding.

Restricted accuracy, full-vocabulary answer-set probability mass,
complete candidate joint log-likelihood, full-vocabulary rank and
short-generation validity are pre-registered and always reported
**descriptively**. No uncalibrated probability-mass threshold is
registered, and no diagnostic can rescue a failed E0 gate.

## The registered competence-floor battery `[V07-D04]`

The existing I1a/I1b/I2 structure is retained. No new MDE is registered
and no 400-cluster design is created. Every number below is regenerated
by `design_statistics.py` and compared, never transcribed.

| stage | gates | null p0 | alternative p1 | alpha | n | pass |
| --- | --- | --- | --- | --- | ---: | ---: |
| development | I1a, I1b, I3 | `9/10` | `97/100` | `1/600` | 413 | 389 |
| development | I2 | `1/2` | `7/10` | `1/600` | 214 | 129 |
| development | I4 | `4/5` | `9/10` | `1/600` | 448 | 383 |
| confirmation | I1a, I1b, I3 | `9/10` | `97/100` | `1/200` | 413 | 388 |
| confirmation | I2 | `1/2` | `7/10` | `1/200` | 214 | 127 |
| confirmation | I4 | `4/5` | `9/10` | `1/200` | 448 | 381 |

| power quantity | exact rational |
| --- | --- |
| `m_max` | 43 |
| per-cell false-negative budget | `19/17200` |
| per-cell power target | `17181/17200` |
| profile stage power floor | `381/400` |
| study end-to-end power floor | `9/10` |

A change to the scientific null, the competence floor or the meaning of
the existing floor test is outside this amendment and requires
`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`.

## Wrapper-only matched contrast `[V07-D05]`

Within each role, a registered common **raw** wrapper is compared with
that role's registered **canonical** wrapper. RL has no canonical chat
template, so its canonical arm is a deterministic few-shot
completion-format wrapper; chat versus raw is not the same intervention
across roles.

The gate is **joint adequacy**: both renderings must meet their
competence floors. No template-effect, equivalence or invariance claim is
registered. The only permitted positive wording is that both registered
renderings met their competence floors.

Paired discordance and risk difference are always reported
descriptively. The registered descriptive bandwidth is
`7/100`, derived as the distance between the null floor and the lowest
alternative of interest. Exceeding it triggers a fixed limitation
paragraph and has **no gate effect**.

## Canonical generated-CoT ceiling `[V07-D06]`

A separate execution-precondition gate. It is not an interface selector
and it is not S4; S4 remains a short answer-only generation diagnostic
with its existing 16-token bound and is never selectable.

| frozen item | value |
| --- | --- |
| route marker | `<think>`, required |
| `do_sample` | `false` |
| `k` | 1 |
| aggregation | `per_item_single_response_full_sequence_exact_match` |
| `theta` | `1/2` |
| alternative | `7/10` |
| alpha | `1/600` |
| n / pass | 214 / 129 |
| maximum generation length | deterministic per item, `DEFER-03` |
| granularity | per immutable checkpoint revision |

`theta` is not invented: the ceiling is a **task-headroom** gate, so it
reuses the registered I2 primitive-headroom construct exactly - same
null, same lowest alternative of interest, same alpha, same exact
one-sided binomial, same regenerated `n` and pass count.

`k = 1` with deterministic decoding, so exactly one estimand is
registered before data and the pass@1 versus majority-vote@k choice
cannot arise at execution time. Majority-vote@k is **not** registered.
The statistical unit is the item; `n x k` responses are never treated as
independent items. Failure yields
`NO_CANONICAL_TASK_HEADROOM_FOR_TARGET_ROUTE`. A pass establishes
generated-CoT task competence only and cannot select an interface.

## Q0 and the RP-B ladder `[V07-D07]`

Q0 is a one-way prequalification layer: a pass is interpretable, a
failure is not evidence that the interface is invalid or that the
construct does not exist. Q0 must contain an E0 expressed-competence
component, and D0 alone can never qualify a candidate.

The ladder is ordered by predeclared observable metadata - parameter
count ascending, publication time as the sole tie-break. Result-informed
ordering is prohibited. Same-tokenizer natural candidates come first;
training-constructed implicit-CoT or direct-answer models appear only as
a separately identified fallback stratum whose claim ceiling is that the
isomorphic interface construction is valid, never that the exact RT byte
interface is valid.

Development and confirmation sets are physically and logically
item-disjoint, confirmation is frozen before development access, there is
one confirmation attempt per candidate, no tuning or rerun after a
confirmation failure, selection is first-confirmed-pass, and the scan
stops immediately after the first confirmed pass.

Because the scan continues past failures, classical fixed-sequence
protection does not apply. The candidate-level Bonferroni allocation uses
the **full** predeclared ladder length `L` regardless of how many
candidates are visited, and the within-candidate component allocation is
preserved separately. `L` is deterministically deferred as `DEFER-02`.

If no candidate qualifies the terminal state is exactly
`NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_THE_REGISTERED_LADDER`,
whose claim ceiling is restricted to the registered family, size range,
checkpoint revisions and interface set.

## RP-B and RP-M `[V07-D08]`

`RP-B` is a behavioral reference for expressed competence and interface
readout. `RP-M` is a ground-truth mechanism reference for patching
validation. They are never combined into one gate or one claim. RP-M need
not share RT's tokenizer because it validates intervention methodology;
RP-B transfer claims remain subject to tokenizer and interface
equivalence.

## Per-checkpoint functional equivalence `[V07-D09]`

Tokenizer equivalence is never inferred from model names. For every
immutable checkpoint revision and every registered candidate surface,
bytes, token IDs in full context, common prefix and discriminant position
must all be equal. File hashes are provenance; the four-part functional
test is the decision criterion. A checkpoint failing any equality is an
`isomorphic_reinstantiation` and is analysed as a separate stratum.

## Engineering shakedown authority `[V07-D10]`

Disjoint from formal calibration authority, and not run in this session.

| limit | value |
| --- | ---: |
| max fix-and-rerun cycles | 3 |
| max total attempts | 3 |
| max wall-clock minutes | 240 |
| max CPU core-hours | 16 |
| max GPU hours | 0 |
| max cloud jobs | 6 |

These are engineering ceilings with no scientific content and no gate
effect. Any discovery that would change an estimand, interface,
threshold, item bank, answer surface, candidate ladder, task definition
or gate logic is outside shakedown authority and produces
`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`.

The negative control is quantitative: its exact one-sided upper
confidence bound must lie strictly below `17/100`.
"Not significantly above chance" is not an equivalence demonstration.

## Recursive-manifest seal `[V07-D11]`

The seal covers all decision-bearing bytes, seals both inclusion globs
and an explicit exclusion list, and includes and hashes the
manifest-generation script itself. The construction is **two-level**:
level one hashes every included byte and produces the manifest, level two
writes the root hash into the terminal record. Neither file contains its
own hash, so there is no fixed point and the construction is not
self-referential.

## Activation and causal-claim boundary `[V07-D12]`

Activation collection, J-lens fitting, patching, ablation and mechanism
inference remain unauthorized until every listed condition passes,
including RP-M method validation before any natural-model patch claim.
Checkpoint differences may be described only as checkpoint-level
associations; a causal claim requires a separate future design with
matched training interventions and independent seeds.

## Deterministic deferrals `[V07-D14]`

No decision-bearing `TBD` exists. Three values legitimately cannot exist
before the pre-execution seal, and each carries a deterministic
acquisition rule and a fail-closed absent state.

| id | value | fail-closed absent state |
| --- | --- | --- |
| `DEFER-01` | immutable checkpoint revision hashes | `STUDY3_V0_7_CHECKPOINT_REVISION_UNSEALED` |
| `DEFER-02` | RP-B ladder membership and its length L | `STUDY3_V0_7_RP_B_LADDER_UNSEALED` |
| `DEFER-03` | canonical generated-CoT maximum generation length | `CANONICAL_COT_CEILING_CONTEXT_WINDOW_UNAVAILABLE` |

## Boundary

`formal_execution_authorized` is `false`. Study 3 is unfrozen,
unselected and unexecuted. No seed, bank, development result,
confirmation access, interface, positive reference or evidence row
exists. `paper/evidence_ledger.csv` still ends at `EV-0016`. The research
question remains unanswered.

The only legal next action is one fresh independent single focused
methods review of draft-v0.7 by a party that did not draft it.
