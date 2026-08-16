# Study 4F

> **State:** `STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`
>
> Study 4F is a **developmental, non-confirmatory behavioral-feasibility pilot**. It published a
> complete, mechanically validated instrument and then stopped at the section 4 resource-route proof:
> no accelerator on this host can hold the 32B checkpoint, the maximum registered KV cache and the
> fixed safety reserve without offloading, and quantizing or sharding to proceed is prohibited.
>
> **No bank was realized, no execution seal exists, no weight was acquired and no model was called.**
> Zero of the sixteen registered cells were executed, so Study 4F produced **no scientific result**.
> `paper/evidence_ledger.csv` still ends at `EV-0016`.
>
> Study 4F makes **no** claim about J-space, about any checkpoint's competence, or about whether the
> interface is valid. It identified **no** RP-B developmental candidate and confirmed nothing.

## Start here

| file | role |
| --- | --- |
| [`STATUS.json`](STATUS.json) | **the authoritative lifecycle router** |
| [`STUDY4F_TERMINAL_DISCLOSURE.md`](STUDY4F_TERMINAL_DISCLOSURE.md) | the terminal disclosure, including the predecessor-execution audit |
| [`shakedown/study4f_shakedown_disposition.json`](shakedown/study4f_shakedown_disposition.json) | the bounded shakedown and its resource-route proof |
| [`protocol/study4f_protocol_v1.json`](protocol/study4f_protocol_v1.json) | the registered protocol |
| [`prompts/study4f_minimal_behavioral_feasibility_authority.md`](prompts/study4f_minimal_behavioral_feasibility_authority.md) | the project-level authority, published alone |

## The registered question

> Under one frozen raw direct-answer interface, does at least one member of the registered natural
> Qwen-tokenizer ladder demonstrate generated-CoT task headroom and zero-generated-reasoning-token
> expressed competence separately on both D2 and D3, thereby providing a developmentally qualified
> natural positive-reference candidate for later confirmation?

**It is unanswered.** No cell ran.

## The instrument

| area | contents |
| --- | --- |
| `prompts/` | the single project-level authority, published alone as the first Study 4F commit |
| `protocol/` | the registered protocol and its restrictive schema |
| `analysis/` | task banks, interfaces and parsers, design statistics, the state machine, the semantic validators and the resource-route proof |
| `shakedown/` | the bounded engineering shakedown disposition |
| `tests/` | the mechanical preflight and the coordinated mutation audit |

Run the preflight explicitly — it is outside the repository's default `testpaths`:

```
python -m pytest studies/study4f/tests/test_study4f_behavioral_feasibility.py
```

## Registered design at a glance

| item | value |
| --- | --- |
| target checkpoint | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` @ `ad9f0ae0…` |
| ladder | `…-Qwen-7B` @ `916b56a4…` → `…-Qwen-14B` @ `1df85071…` → `…-Qwen-32B` @ `711ad2ea…` |
| banks | `D2_DEVELOPMENT_BANK` and `D3_DEVELOPMENT_BANK`, 104 items each, single-family, disjoint |
| label allocation | 26 per label per bank; 15 per label in the deterministic first 60 |
| primary route | `W1_RAW_DIRECT` — no chat template, no forced `</think>` closure |
| headroom route | `C1_LONG_GENERATED_COT_HEADROOM` — a precondition only, never an interface selector |
| cells | `m_max = 16`, Bonferroni over all 16 regardless of how many are reached |
| error budget | `alpha_global = 1/20`, `alpha_per_cell = 1/320`, power `9/10` |
| CoT gate | `n = 104`, pass iff correct `≥ 90`; exact size `0.0029878`, exact power `0.9055` |
| E0 gate | `n = 60`, pass iff correct `≥ 41`; exact size `0.0031088`, exact power `0.9075` |
| depth pooling | prohibited — D2 and D3 are always separate cells |
| ladder semantics | candidate-local; a failure by `RP_B1` never blocks `RP_B2` or `RP_B3` |
| best attainable outcome | `RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION` — never a confirmation |

## Relationship to Study 3R

Study 4F is a **fresh project-level operator decision** issued outside the terminal Study 3R
authority, exactly as [`../study3r/STATUS.json`](../study3r/STATUS.json) requires of any restart. It
does not amend, repair or reactivate Study 3R, and it derives no authority from it.

Verified bytes and algorithms are **copied** into this namespace with recorded provenance. No
rejected Study 3R protocol or pointer is ever resolved at runtime. Every Study 3R byte is identical
to the closure head `ee8a852…`, which a Study 4F test asserts over the whole `studies/study3r/` tree.

The seven coordinated mutations that survived the Study 3R semantic validator are each killed or
rendered structurally inapplicable here, and tested as such.

## Prohibited conclusions

Study 4F never supports any of: *J-space does not exist*; *J-space is unobservable*; *the model
cannot reason internally*; *single-forward reasoning was demonstrated*; *RP-B was confirmed*; *the
result generalizes beyond the registered checkpoints, depths and interface*.

## Next legal action

Resuming requires one accelerator able to hold the 32B checkpoint, the maximum registered KV cache
and the fixed safety reserve without offloading. The published instrument may then be reused
unchanged from the shakedown step. Quantizing, sharding or offloading to proceed is prohibited and
would not be the registered study.

`STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`
