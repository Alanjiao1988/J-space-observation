# Study 3R

> **State:** `STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`
>
> The Study 3R clean-room protocol candidate v1 is authored. It is **not frozen** and **not executable**: `frozen = false`, `execution_authorized = false`, `formal_execution_authorized = false`. `paper/evidence_ledger.csv` still ends at `EV-0016` and the research question remains unanswered.
>
> The next legal action is **one independent focused methods review**. Any BLOCKING finding terminates Study 3R; no automatic amendment follows.

## Start here

| file | role |
| --- | --- |
| [`protocol/study3r_protocol_current.json`](protocol/study3r_protocol_current.json) | the single unambiguous current pointer |
| [`protocol/study3r_protocol_v1.json`](protocol/study3r_protocol_v1.json) | **the one authoritative protocol candidate** |
| [`protocol/study3r_protocol_v1.md`](protocol/study3r_protocol_v1.md) | its human-readable rendering |
| [`AUTHORING_DISCLOSURE.md`](AUTHORING_DISCLOSURE.md) | the authoring disclosure |
| [`study3r_candidate_manifest_v1.json`](study3r_candidate_manifest_v1.json) | the acyclic candidate reproducibility manifest |
| [`CHARTER.md`](CHARTER.md) | the charter and the sixteen frozen project-level decisions |
| [`study3r_charter.json`](study3r_charter.json) | the machine-readable charter, recorded at authorization time |

## Bundle

| area | contents |
| --- | --- |
| `prompts/` | the single protocol-authoring authority |
| `acquisition/` | the sealed tokenizer-only acquisition record, the frozen byte and token surfaces, and the tokenizer functional-equivalence record |
| `protocol/` | the protocol, its schema and Markdown, the rendering registry, the state machine and the current pointer |
| `analysis/` | the tokenizer probe, the protocol builder, the production design statistics, the independent stdlib-only recalculation and the manifest generator |
| `tasks/` | the clean-room task-population generators |
| `../../tests/test_study3r_protocol_v1.py` | semantic validation and coordinated generator-mutation tests |

## Registered design at a glance

| item | value |
| --- | --- |
| target checkpoint | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` |
| RP-B ladder | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`, `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`, `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` |
| ladder length | `L = 3`, fixed membership and order, no fallback |
| primary estimand | `E0_zero_generated_reasoning_token_expressed_competence` |
| diagnostic | `D0_single_forward_decodability`, never a gate |
| ceiling | `COT_generated_reasoning_ceiling`, `k = 1`, not an interface selector |
| wrapper arms | `W1_RAW_DIRECT` and `W2_ROLE_CANONICAL`, joint adequacy |
| atomic-cell census | `m_max = 58` over 9 gates |
| error budget | `alpha_global = 1/20`, Bonferroni, `alpha_per_cell = 1/1160` |
| power | `9/10` per cell, exact one-sided binomial |
| strata | 1 isomorphic re-instantiation stratum |
| mutations | 24 registered, 24 killed, 0 survivors |

## Predecessor

* Operator terminal decision: [`../study3/reviews/v0_7_operator_terminal_decision.md`](../study3/reviews/v0_7_operator_terminal_decision.md) — `STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION`
* Governing assessment: [`../study3/reviews/v0_7_single_focused_methods_review.md`](../study3/reviews/v0_7_single_focused_methods_review.md) — 12 BLOCKING, 3 MAJOR, 2 MINOR
* Authorizing authority: [`../study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md`](../study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md)

No v0.5, v0.6 or v0.7 artifact is a Study 3R runtime overlay or fallback. The rejected candidate bundle is retained byte-exactly as history and is never consulted at runtime.

## Next legal action

One independent focused methods review, performed by a different, independent party. This authoring session is complete and no second authoring session and no amendment is authorized.

`STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`
