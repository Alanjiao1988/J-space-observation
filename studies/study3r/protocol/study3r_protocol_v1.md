# Study 3R protocol candidate v1

> **State:** `STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`
>
> `frozen = false`, `execution_authorized = false`, `formal_execution_authorized = false`.
>
> This document is the human-readable rendering of [`study3r_protocol_v1.json`](study3r_protocol_v1.json), which is the single authoritative artifact. No runtime overlay and no fallback protocol is permitted.

Authority: [`studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md`](../../../studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md)

## 1. Roles and immutable revisions

| role | repository | immutable revision | tokenizer | vocab | context |
| --- | --- | --- | --- | --- | --- |
| `RT` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` | `Qwen2Tokenizer` | 151643 | 131072 |
| `RP_B1` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | `916b56a44061fd5cd7d6a8fb632557ed4f724f60` | `Qwen2Tokenizer` | 151643 | 131072 |
| `RP_B2` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | `1df8507178afcc1bef68cd8c393f61a886323761` | `Qwen2Tokenizer` | 151643 | 131072 |
| `RP_B3` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | `711ad2ea6aa40cfca18895e8aca02ab92df1a746` | `Qwen2Tokenizer` | 151643 | 131072 |

`RT` is the sole target checkpoint. The natural positive-reference ladder has fixed membership and fixed order with `L = 3`; there is no fallback candidate, no substitution, no reordering and no post-result expansion.

## 2. Estimands

### 2.1 `E0_zero_generated_reasoning_token_expressed_competence` (primary)

Greedy decoding with `do_sample = false`. Scoring is full-sequence exact match against the frozen legal answer surfaces for that checkpoint revision. Prefix matching is prohibited. An unparseable generation, an empty generation, any rationale or any extra emitted token is scored incorrect.

| role | legal surfaces | longest surface (tokens) | margin | `max_new_tokens` |
| --- | --- | --- | --- | --- |
| `RT` | `A`=[32], `B`=[33], `C`=[34], `D`=[35] | 1 | 1 | 2 |
| `RP_B1` | `A`=[32], `B`=[33], `C`=[34], `D`=[35] | 1 | 1 | 2 |
| `RP_B2` | `A`=[32], `B`=[33], `C`=[34], `D`=[35] | 1 | 1 | 2 |
| `RP_B3` | `A`=[32], `B`=[33], `C`=[34], `D`=[35] | 1 | 1 | 2 |

Answer-set mass, full-vocabulary rank and complete-candidate joint likelihood are registered as descriptive diagnostics only and may never determine a gate.

### 2.2 `D0_single_forward_decodability` (diagnostic only)

D0_single_forward_decodability proves only conditional discriminant decodability at a frozen position under a frozen counterfactual surface. It never demonstrates natural expression, never demonstrates complete-answer competence, is never an RP-B gate and never qualifies a candidate.

Tie rule: An exact tie between two or more candidate scores is resolved as D0_UNDECIDED and scored incorrect. No label ordering, no lowest token id and no random draw is used to break a tie.

### 2.3 Generated-CoT ceiling

`k = 1`, item as the statistical unit, parser `P1_FINAL_ANSWER_LAST_LINE`, unparseable output scored incorrect.

| role | context window | prompt tokens | `max_new_tokens` | worst-case sequence | fits |
| --- | --- | --- | --- | --- | --- |
| `RT` | 131072 | 88 | 4096 | 4184 | true |
| `RP_B1` | 131072 | 88 | 4096 | 4184 | true |
| `RP_B2` | 131072 | 88 | 4096 | 4184 | true |
| `RP_B3` | 131072 | 88 | 4096 | 4184 | true |

A generated-CoT ceiling pass proves only that the checkpoint has generated-CoT headroom on the registered ceiling bank. Neither a pass nor a failure selects an interface, selects a wrapper arm, or demonstrates no-CoT capability.

## 3. Wrapper arms and tokenizer strata

| arm | envelope | checkpoint specific | message roles | few-shot |
| --- | --- | --- | --- | --- |
| `W1_RAW_DIRECT` | raw_plaintext_direct_answer | false | none | 0 |
| `W2_ROLE_CANONICAL` | checkpoint_revision_specific_role_canonical | true | ['user'] | 0 |

The single field that differs between the matched arms is `envelope`. The wrapper gate is joint adequacy: both arms must independently clear the registered competence floor. Study 3R does not claim template invariance and does not estimate a template effect. Paired discordance is reported descriptively for every checkpoint and stratum, in both directions.

Verified tuple: `(bytes, token IDs, common prefix, discriminant position)`. A checkpoint whose (bytes, token IDs, common prefix, discriminant position) tuple differs from the reference in any element is an isomorphic re-instantiation stratum and is never pooled as the same frozen byte/token interface.

| role | stratum |
| --- | --- |
| `RT` | `STRATUM_01` |
| `RP_B1` | `STRATUM_01` |
| `RP_B2` | `STRATUM_01` |
| `RP_B3` | `STRATUM_01` |

## 4. Task populations

Operation ontology: `ADD` = `+`, `MUL` = `*`, `SUB` = `-`. Operands are drawn from `[0, 9]`; evaluated values lie in `[0, 999]`.

| bank | families | gate | n |
| --- | --- | --- | --- |
| `D2_D3_CEILING_BANK` | `D2`, `D3` | `G01_COT_CEILING` | 128 |
| `REC` | `REC` | `G02_CONTROL_RECOVERY` | 110 |
| `BIND` | `BIND` | `G03_CONTROL_BINDING` | 110 |
| `PRIM` | `PRIM` | `G04_CONTROL_PRIMITIVE` | 110 |
| `NEG` | `NEG` | `G05_NEGATIVE_CONTROL` | 416 |
| `D2_ADEQUACY_BANK` | `D2` | `G06_WRAPPER_JOINT_ADEQUACY` | 74 |
| `D2_D3_DEVELOPMENT_BANK` | `D2`, `D3` | `G07_RPB_DEVELOPMENT` | 74 |
| `D2_D3_CONFIRMATION_BANK` | `D2`, `D3` | `G08_RPB_CONFIRMATION` | 74 |
| `D2_D3_TARGET_BANK` | `D2`, `D3` | `G09_RT_E0_QUALIFICATION` | 74 |

Neither the execution seed nor any scientific bank is realized in the authoring session. Tokenizer fixtures are literal constants carrying `is_scientific_item = false` and never enter a bank.

## 5. Statistical closure

Global one-sided error budget `1/20`, single multiplicity family `F_GLOBAL_STUDY3R`, Bonferroni equal allocation over `m_max = 58` gate-bearing atomic cells, giving `alpha_per_cell = 1/1160`. Power target `9/10` per cell. All arithmetic is exact integer binomial arithmetic.

| gate | cells | direction | floor / margin | alternative | n | pass boundary | exact power |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `G01_COT_CEILING` | 4 | greater_than_floor | `3/4` | `9/10` | 128 | k >= 111 | 0.912498598878 |
| `G02_CONTROL_RECOVERY` | 8 | greater_than_floor | `9/10` | `99/100` | 110 | k >= 108 | 0.901331394239 |
| `G03_CONTROL_BINDING` | 8 | greater_than_floor | `9/10` | `99/100` | 110 | k >= 108 | 0.901331394239 |
| `G04_CONTROL_PRIMITIVE` | 8 | greater_than_floor | `9/10` | `99/100` | 110 | k >= 108 | 0.901331394239 |
| `G05_NEGATIVE_CONTROL` | 8 | less_than_upper_margin | `35/100` | `1/4` | 416 | k <= 115 | 0.902527305436 |
| `G06_WRAPPER_JOINT_ADEQUACY` | 8 | greater_than_floor | `1/2` | `3/4` | 74 | k >= 51 | 0.907835037241 |
| `G07_RPB_DEVELOPMENT` | 6 | greater_than_floor | `1/2` | `3/4` | 74 | k >= 51 | 0.907835037241 |
| `G08_RPB_CONFIRMATION` | 6 | greater_than_floor | `1/2` | `3/4` | 74 | k >= 51 | 0.907835037241 |
| `G09_RT_E0_QUALIFICATION` | 2 | greater_than_floor | `1/2` | `3/4` | 74 | k >= 51 | 0.907835037241 |

The RP-B ladder scans past failures until the first confirmed pass. Study 3R does not claim classical fixed-sequence protection: multiplicity is corrected over the full registered `L = 3` regardless of where scanning stops, and each candidate receives at most one development evaluation and one item-disjoint confirmation evaluation.

## 6. State machine

| state | kind | gates | outcomes |
| --- | --- | --- | --- |
| `S00_AUTHORED` | initial | none | `execution_authorization_granted` &rarr; `S01_SEALED_ENGINEERING_SHAKEDOWN`; `execution_authorization_absent` &rarr; `T00_NOT_EXECUTED` |
| `S01_SEALED_ENGINEERING_SHAKEDOWN` | operational | none | `shakedown_reproduced_every_sealed_surface` &rarr; `S02_CHECKPOINT_TOKENIZER_FUNCTIONAL_EQUIVALENCE`; `shakedown_failed_to_reproduce_a_sealed_surface` &rarr; `T01_SHAKEDOWN_FAILED` |
| `S02_CHECKPOINT_TOKENIZER_FUNCTIONAL_EQUIVALENCE` | operational | none | `every_registered_tuple_verified_and_stratified` &rarr; `S03_GENERATED_COT_CEILING`; `a_registered_tuple_could_not_be_verified` &rarr; `T02_TOKENIZER_EQUIVALENCE_FAILED` |
| `S03_GENERATED_COT_CEILING` | statistical | `G01_COT_CEILING` | `every_checkpoint_cell_passed` &rarr; `S04_COMPETENCE_CONTROLS`; `at_least_one_checkpoint_cell_failed` &rarr; `T03_COT_CEILING_FAILED` |
| `S04_COMPETENCE_CONTROLS` | statistical | `G02_CONTROL_RECOVERY`, `G03_CONTROL_BINDING`, `G04_CONTROL_PRIMITIVE` | `every_control_cell_passed` &rarr; `S05_NEGATIVE_CONTROL`; `at_least_one_control_cell_failed` &rarr; `T04_COMPETENCE_CONTROL_FAILED` |
| `S05_NEGATIVE_CONTROL` | statistical | `G05_NEGATIVE_CONTROL` | `every_negative_control_cell_passed` &rarr; `S06_TWO_WRAPPER_JOINT_ADEQUACY`; `at_least_one_negative_control_cell_failed` &rarr; `T05_NEGATIVE_CONTROL_FAILED` |
| `S06_TWO_WRAPPER_JOINT_ADEQUACY` | statistical | `G06_WRAPPER_JOINT_ADEQUACY` | `both_arms_cleared_the_floor_for_every_checkpoint` &rarr; `S07_RPB_LADDER_DEVELOPMENT_AND_CONFIRMATION`; `at_least_one_arm_failed_for_at_least_one_checkpoint` &rarr; `T06_WRAPPER_ADEQUACY_FAILED` |
| `S07_RPB_LADDER_DEVELOPMENT_AND_CONFIRMATION` | statistical | `G07_RPB_DEVELOPMENT`, `G08_RPB_CONFIRMATION` | `a_candidate_passed_development_and_confirmation_on_both_arms` &rarr; `S08_RPB_FIRST_CONFIRMED_PASS_FREEZE`; `the_full_registered_ladder_was_scanned_without_a_confirmed_pass` &rarr; `T07_NO_QUALIFIED_REFERENCE` |
| `S08_RPB_FIRST_CONFIRMED_PASS_FREEZE` | operational | none | `freeze_record_written` &rarr; `S09_RT_E0_BEHAVIORAL_QUALIFICATION`; `freeze_record_could_not_be_written` &rarr; `T08_RPB_FREEZE_RECORD_FAILED` |
| `S09_RT_E0_BEHAVIORAL_QUALIFICATION` | statistical | `G09_RT_E0_QUALIFICATION` | `rt_cleared_the_floor_on_both_arms` &rarr; `S10_D0_DIAGNOSTIC_REPORT`; `rt_failed_at_least_one_arm` &rarr; `S10_D0_DIAGNOSTIC_REPORT` |
| `S10_D0_DIAGNOSTIC_REPORT` | diagnostic | none | `diagnostic_readout_reported` &rarr; `S11_TERMINAL_DISPOSITION`; `diagnostic_readout_unavailable_and_recorded_as_such` &rarr; `S11_TERMINAL_DISPOSITION` |
| `S11_TERMINAL_DISPOSITION` | disposition | none | `carried_outcome_is_rt_cleared_the_floor_on_both_arms` &rarr; `T10_STUDY3R_COMPLETE_RT_QUALIFIED`; `carried_outcome_is_rt_failed_at_least_one_arm` &rarr; `T09_RT_NOT_QUALIFIED` |

| terminal | meaning |
| --- | --- |
| `T00_NOT_EXECUTED` | The candidate protocol was never executed. This is the currently active terminal outcome. |
| `T01_SHAKEDOWN_FAILED` | The sealed engineering shakedown did not reproduce a sealed surface. No scientific measurement is taken. |
| `T02_TOKENIZER_EQUIVALENCE_FAILED` | A registered (bytes, token IDs, common prefix, discriminant position) tuple could not be verified. |
| `T03_COT_CEILING_FAILED` | At least one checkpoint lacked generated-CoT headroom on the registered ceiling bank. |
| `T04_COMPETENCE_CONTROL_FAILED` | At least one trivial-recovery, binding or single-primitive control cell fell below its floor. |
| `T05_NEGATIVE_CONTROL_FAILED` | At least one negative-control cell failed its one-sided upper-bound rule. |
| `T06_WRAPPER_ADEQUACY_FAILED` | At least one E0 wrapper arm failed to clear the competence floor for at least one checkpoint. |
| `T07_NO_QUALIFIED_REFERENCE` | T07_NO_QUALIFIED_REFERENCE is bounded to the registered ladder membership at the registered immutable revisions, the registered task populations and item banks, and the two registered E0 wrapper arms. It makes no claim about other models, other revisions, other task populations, other interfaces, or restricted-logit interfaces in general. |
| `T08_RPB_FREEZE_RECORD_FAILED` | The first-confirmed-pass RP-B freeze record could not be written. |
| `T09_RT_NOT_QUALIFIED` | RT did not clear the E0 competence floor on both registered wrapper arms, bounded to the registered revisions, task populations and interfaces. |
| `T10_STUDY3R_COMPLETE_RT_QUALIFIED` | RT cleared the E0 competence floor on both registered wrapper arms against a first-confirmed-pass RP-B reference. |

## 7. Boundary

No model weights, adapters or activations were acquired. No model load, prefill, forward pass, logit read, scoring operation or generation was performed. No cloud or GPU job was created. No scientific bank was realized, no RP-B candidate was selected, no evidence-ledger row was written and no scientific claim was made. Activation patching, RP-M and every Study 3M artifact are absent and unauthorized.

`formal_execution_authorized` remains `false`.

`STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`
