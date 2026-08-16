# Study 3 draft-v0.7 operator amendment: the consolidated amendment

> **Disposition:** every decision below is recorded
> `PROPOSED_RESOLVED_SUBJECT_TO_SINGLE_FOCUSED_REVIEW`.
>
> The drafting party does **not** claim draft-v0.7 is correct.
> draft-v0.7 is **not** reviewed, **not** frozen, **not** selected and
> **not** formally executable.

State: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_7_COMPLETE_AWAITING_SINGLE_FOCUSED_METHODS_REVIEW`

Machine-readable form: [`v0_7_operator_amendment.json`](v0_7_operator_amendment.json).

Normative protocol:
[`../protocol/interface_calibration_protocol_draft_v0_7.json`](../protocol/interface_calibration_protocol_draft_v0_7.json).

## 1. The operator decision this amendment executes

The operator selected `OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL` and
explicitly rejected Options A, B and C. draft-v0.7 is therefore a new,
versioned, self-contained normative bundle, and the legacy v0.5 trio is
preserved byte-exactly as historical P0 input.

| legacy file | sha256 | status |
| --- | --- | --- |
| `interface_calibration_protocol.schema.json` | `79a8a68a51c68601…` | `HISTORICAL_P0_BINDING_ONLY_NOT_CURRENT_PROTOCOL` |
| `interface_calibration_protocol_draft.json` | `1197e08779f6360a…` | `HISTORICAL_P0_BINDING_ONLY_NOT_CURRENT_PROTOCOL` |
| `interface_calibration_protocol_draft.md` | `0376c7d5c659fe55…` | `HISTORICAL_P0_BINDING_ONLY_NOT_CURRENT_PROTOCOL` |

The P0 corpus manifest was **not** regenerated. The frozen-corpus test
was **not** retired, weakened, waived or re-scoped.

## 2. The new bundle

| artifact | bytes | sha256 |
| --- | ---: | --- |
| `interface_calibration_protocol_draft_v0_7.json` | 461502 | `775d3add8dd368bc…` |
| `interface_calibration_protocol_draft_v0_7.schema.json` | 9266 | `dde4b2b1b68dda1d…` |
| `interface_calibration_protocol_draft_v0_7.md` | 13925 | `c220e429a43c8971…` |
| `interface_calibration_rendering_registry_v0_7.json` | 3243 | `8bc27e4ebb2e3146…` |
| `interface_calibration_rendering_registry_v0_7.schema.json` | 2392 | `93fbcd721a40b79f…` |
| `interface_calibration_protocol_current.json` | 3237 | `9a51d1ba3bacf2db…` |
| `interface_calibration_protocol_current.schema.json` | 4505 | `e26a57a9e1cd97e8…` |

The current pointer fails closed: a missing, mismatched or invalid v0.7
file must not cause a loader to fall back to the legacy v0.5 protocol.

## 3. The decisions

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

Each is stated normatively in the protocol and its companion Markdown.
This amendment records them; it does not restate them a third time.

## 4. What changed in the numbers, and what did not

**Unchanged, by regeneration.** The registered I1a/I1b/I2 battery, its
nulls, alternatives, alphas, sample sizes, pass counts, `m_max` and every
power floor are byte-compared against `design_statistics.py` output. No
number is copied forward for continuity, and no new MDE is registered.

**New, and derived rather than chosen.**

| constant | value | derivation |
| --- | --- | --- |
| generated-CoT `theta` | `1/2` | the registered I2 headroom null |
| generated-CoT `k` | 1 | deterministic decoding; removes the pass@1 versus majority-vote choice |
| negative-control bound | `17/100` | restricted chance plus the registered alternative gap |
| wrapper bandwidth | `7/100` | the registered alternative gap |
| E0 `max_new_tokens` | 3 | two answer tokens plus a one-token EOS margin |
| reproducibility tolerance | 0 | the decision statistic is an integer count |

**Deterministically deferred.** Three values legitimately cannot exist
before the pre-execution seal. Each has a deterministic acquisition rule
and a fail-closed absent state, and none is a `TBD`.

| id | value | fail-closed absent state |
| --- | --- | --- |
| `DEFER-01` | immutable checkpoint revision hashes | `STUDY3_V0_7_CHECKPOINT_REVISION_UNSEALED` |
| `DEFER-02` | RP-B ladder membership and its length L | `STUDY3_V0_7_RP_B_LADDER_UNSEALED` |
| `DEFER-03` | canonical generated-CoT maximum generation length | `CANONICAL_COT_CEILING_CONTEXT_WINDOW_UNAVAILABLE` |

`DEFER-02` remains blocked on `OD2`, which this amendment does not
resolve: it freezes the eligibility predicate and the ordering rule, and
leaves ladder membership to the pre-execution seal.

## 5. Inherited P0-R2 disposition

Recorded without repair as
`P0_R2_G2_TERMINAL_VERIFIED_WITH_AUDIT_EXCEPTIONS`: the generation-2 live
replay mechanically passed and was independently reconstructed, bounded
pilot authorization failed, no GPU job was created or started, model,
tokenizer, scoring and GPU counters remained zero, the evidence ledger
remained at `EV-0016` and the research question remained unanswered.

The four governance audit exceptions are recorded verbatim in the
machine-readable form. This amendment does not write "full authority
compliance verified" or "zero force-pushes verified", and it treats no
P0 infrastructure result as scientific evidence.

## 6. Boundary

`formal_execution_authorized = false`. Study 3 is unfrozen, unselected
and unexecuted. Every prohibited operation counter is zero.
`paper/evidence_ledger.csv` is byte-identical and still ends at
`EV-0016`. The research question remains unanswered.

## 7. The only legal next action

One fresh, independent, single focused methods review of draft-v0.7 by a
party that did not draft it. It may return only its registered acceptance
state or `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`, and it may
not automatically draft v0.8.
