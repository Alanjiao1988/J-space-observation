# Study 3R

> **State:** `STUDY3R_TERMINAL_CLOSURE_COMPLETE_RESEARCH_QUESTION_UNANSWERED` — this supersedes and retires the former prospective state `STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`, which is now rejected candidate history and is no longer a routing instruction.
>
> Study 3R is **terminally closed**. The authoritative lifecycle router is
> [`STATUS.json`](STATUS.json); the human-readable terminal record is
> [`STUDY3R_TERMINAL_CLOSURE.md`](STUDY3R_TERMINAL_CLOSURE.md). Read those two first.
>
> Second, read the governing methods disposition: Study 3R received exactly
> **one independent focused methods review**,
> [`reviews/study3r_protocol_v1_single_focused_review.md`](reviews/study3r_protocol_v1_single_focused_review.md)
> — `STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION`, 4 BLOCKING, 5 MAJOR, 2 MINOR.
>
> Protocol v1 is **rejected candidate history**. It is not frozen, not selected, not executable and
> not amendable: `frozen = false`, `execution_authorized = false`, `formal_execution_authorized = false`.
> **There is no active Study 3R protocol**, and `active_protocol` is `null`.
>
> ⚠️ [`protocol/study3r_protocol_current.json`](protocol/study3r_protocol_current.json) is a
> **candidate-internal** pointer of the rejected candidate. It describes the historical candidate
> state at the moment it was reviewed. It is **not** an active lifecycle pointer and prospective
> readers must not resolve it.
>
> **No successor is authorized** — not by this study and not by its closure. `paper/evidence_ledger.csv`
> still ends at `EV-0016`, no scientific result exists, and the research question remains
> **unanswered**. Any future restart requires a fresh explicit project-level operator decision issued
> outside the terminal Study 3R authority.

## Start here

| file | role |
| --- | --- |
| [`STATUS.json`](STATUS.json) | **the authoritative lifecycle router** |
| [`STUDY3R_TERMINAL_CLOSURE.md`](STUDY3R_TERMINAL_CLOSURE.md) | the terminal closure report |
| [`study3r_terminal_closure.json`](study3r_terminal_closure.json) | the machine-readable closure record |
| [`reviews/study3r_protocol_v1_single_focused_review.md`](reviews/study3r_protocol_v1_single_focused_review.md) | the governing independent focused review |
| [`prompts/study3r_terminal_closure_authority.md`](prompts/study3r_terminal_closure_authority.md) | the terminal-closure authority |
| [`CHARTER.md`](CHARTER.md) | the charter and the sixteen frozen project-level decisions |

## Rejected candidate history

Retained byte-exactly. None of it is an active protocol, a runtime overlay or a fallback.

| file | role |
| --- | --- |
| [`protocol/study3r_protocol_v1.json`](protocol/study3r_protocol_v1.json) | the rejected protocol candidate |
| [`protocol/study3r_protocol_v1.md`](protocol/study3r_protocol_v1.md) | its human-readable rendering |
| [`protocol/study3r_protocol_current.json`](protocol/study3r_protocol_current.json) | candidate-internal pointer — **not** a lifecycle authority |
| [`AUTHORING_DISCLOSURE.md`](AUTHORING_DISCLOSURE.md) | the authoring disclosure |
| [`study3r_candidate_manifest_v1.json`](study3r_candidate_manifest_v1.json) | the acyclic candidate reproducibility manifest |
| [`study3r_charter.json`](study3r_charter.json) | the machine-readable charter, recorded at authorization time |

## Bundle

| area | contents |
| --- | --- |
| `prompts/` | the protocol-authoring authority, the focused-review authority and the terminal-closure authority |
| `acquisition/` | the sealed tokenizer-only acquisition record, the frozen byte and token surfaces, and the tokenizer functional-equivalence record |
| `protocol/` | the rejected protocol candidate, its schema and Markdown, the rendering registry, the state machine and the candidate-internal pointer |
| `analysis/` | the tokenizer probe, the protocol builder, the production design statistics, the independent stdlib-only recalculation and the manifest generator |
| `reviews/` | the single independent focused review, its schema, receipt, recalculation, tokenizer reconstruction, mutation audit and test module |
| `tasks/` | the clean-room task-population generators |
| `closure/` | the terminal-closure test module |
| `../../tests/test_study3r_protocol_v1.py` | semantic validation and coordinated generator-mutation tests |

## Registered candidate design at a glance

Recorded as rejected-candidate history only. None of it is executable.

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
| mutations | 24 registered, 24 killed; **7 coordinated adversarial mutations survived** (F-09) |

## Predecessor

* Operator terminal decision: [`../study3/reviews/v0_7_operator_terminal_decision.md`](../study3/reviews/v0_7_operator_terminal_decision.md) — `STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION`
* Governing assessment: [`../study3/reviews/v0_7_single_focused_methods_review.md`](../study3/reviews/v0_7_single_focused_methods_review.md) — 12 BLOCKING, 3 MAJOR, 2 MINOR
* Authorizing authority: [`../study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md`](../study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md)

No v0.5, v0.6 or v0.7 artifact is a Study 3R runtime overlay or fallback. The rejected candidate bundle is retained byte-exactly as history and is never consulted at runtime.

## Next legal action

None within Study 3R. This study is closed, there is no active protocol and no successor is
authorized. Any future restart requires a fresh explicit project-level operator decision issued
outside the terminal Study 3R authority.

`STUDY3R_TERMINAL_CLOSURE_COMPLETE_RESEARCH_QUESTION_UNANSWERED`
