# Study 3R — clean-room successor charter

> **State:** `STUDY3R_CLEAN_ROOM_PROTOCOL_AUTHORIZED_AWAITING_SINGLE_AUTHORING_SESSION`
>
> Study 3R is a **clean-room successor**. It is not v0.8, not v0.7.1, and not a
> copy-on-write continuation of the legacy Study 3 protocol. No protocol text,
> structure, schema, registry, statistics table, manifest generator or test is
> carried forward from draft-v0.7 or from any earlier Study 3 draft.
>
> This charter contains **no protocol**, no task-bank realization, no checkpoint
> download, no tokenizer output, no selected interface, no numerical gate
> calculation and no execution authorization.

| item | value |
| --- | --- |
| machine-readable charter | [`study3r_charter.json`](study3r_charter.json) |
| charter schema | [`study3r_charter.schema.json`](study3r_charter.schema.json) |
| authorizing authority | [`../study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md`](../study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md) |
| predecessor decision | [`../study3/reviews/v0_7_operator_terminal_decision.md`](../study3/reviews/v0_7_operator_terminal_decision.md) — `STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION` |

## Why a clean room

draft-v0.7 failed its single allowed independent focused review with twelve
BLOCKING and three MAJOR findings. Several of those findings were not v0.7
defects at all: they were defects inherited verbatim from the legacy structure,
including a contradictory K6-SEP applicability carried forward byte-identically
in `gate_hierarchy`, `gate_truth_table` and `operation_boundaries`, a state
machine that was the legacy v0.5 machine unchanged, and fifteen active fields
still assigning adjudication to a review round that had already happened.

An incremental repair would have to keep that structure in order to remain
incremental. Study 3R therefore starts from an empty namespace.

## Frozen project-level decisions

These sixteen decisions are frozen by the operator and are inputs to the single
Study 3R authoring session. They are project-level commitments, not a protocol.

| id | decision |
| --- | --- |
| `S3R-D01` | The primary headline estimand is `E0_zero_generated_reasoning_token_expressed_competence`. |
| `S3R-D02` | `D0_single_forward_decodability` is a conditional diagnostic only. It is never an RP-B gate and never qualifies a candidate. |
| `S3R-D03` | The natural RP-B ladder has fixed membership and fixed order, `L = 3`. |
| `S3R-D04` | Immutable checkpoint revisions must be resolved and sealed before protocol freeze. |
| `S3R-D05` | Q0 uses E0 as its primary gate, item-disjoint development and confirmation sets, first-confirmed-pass selection, and multiplicity correction over the full registered `L = 3`. |
| `S3R-D06` | Wrapper qualification remains a two-arm joint-adequacy gate. Both arms must appear in the atomic-cell census and in the multiplicity calculation. `m_max = 43` may not be reused without independent re-derivation. |
| `S3R-D07` | Wrapper bytes, roles, separators, BOS/EOS behavior, answer cues, few-shot examples and template revisions must be frozen exactly. |
| `S3R-D08` | The negative control must use an executable one-sided upper-bound or equivalence design with a registered unit, chance level, margin, sample size, alpha, exact construction and multiplicity family. |
| `S3R-D09` | E0 legal answer surfaces and token sequences are checkpoint-revision-specific. `max_new_tokens` is derived per checkpoint as the longest frozen legal answer surface plus the registered termination margin. The universal value 3 is not inherited. |
| `S3R-D10` | Tokenizer-functional inequality creates an explicitly separate isomorphic-reinstantiation stratum and may never be pooled as the same frozen interface. |
| `S3R-D11` | The generated-CoT ceiling is a per-checkpoint execution precondition with `k = 1` and a frozen task population, bank relationship, parser, context and generation bound, and total resource bound. It is not an interface selector. |
| `S3R-D12` | Study 3R covers behavioral and interface qualification only. |
| `S3R-D13` | RP-M, activation patching and mechanism claims are outside Study 3R and are not authorized. They may be considered later as a separate Study 3M, only after all Study 3R gates pass. |
| `S3R-D14` | The Study 3R state machine, schema, registry, statistics, manifest generator and semantic tests must be written cleanly from scratch. The legacy 40-key protocol structure is not carried forward. |
| `S3R-D15` | Every decision-bearing schema field must be constrained. Validation must include coordinated generator-mutation tests, not only artifact-versus-generator byte equality. |
| `S3R-D16` | Study 3R receives one protocol-authoring session and one independent focused review. If that review returns any BLOCKING finding, Study 3R terminates and no automatic amendment follows. |

### The registered RP-B ladder

Fixed membership, fixed order, ordered by parameter count ascending:

1. `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`
2. `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`
3. `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`

`L = 3`. There is no fallback candidate and no post-result expansion. The
candidate-level multiplicity correction is taken over the full registered `L = 3`
regardless of how many candidates are actually visited.

Naming these three repositories fixes the ladder membership. It resolves no
revision, downloads nothing, constructs no tokenizer and selects no candidate.

## What the authoring session must do differently

Each item below answers a specific BLOCKING finding against draft-v0.7. They are
requirements on the future protocol, not statements about it.

* **One normative source.** Exactly one top-level normative document, with every
  transitively normative asset reachable from the sealed active bundle by exact
  path and hash. No field may name a different authoritative artifact.
* **One total state machine.** Every gate — E0, D0's diagnostic branch, Q0, the
  wrapper joint-adequacy gate, the generated-CoT ceiling, the negative control
  and the shakedown exit — must be a state or guard in one machine, with exactly
  one legal transition per complete outcome and no identifier reused for two
  constructs.
* **A census that matches the gates.** The atomic-cell census, `m_max`, the
  per-cell power target and every sample size must be re-derived from the actual
  gate set, including both wrapper arms.
* **A sealed manifest with real paths.** A named manifest-generator path and
  deterministic path rules that map every inclusion category to concrete files,
  including the pointer, every normative registry, and parser, renderer, runner
  and scoring code.
* **Schemas that constrain values.** Enumerations, constants and exact rationals
  on decision-bearing fields, not bare `{}` property schemas.
* **Validation that survives a coordinated edit.** At least one validator must
  be independent of the artifact generator, and the suite must include
  coordinated generator-mutation tests.

## Boundary

Study 3R is authorized; its protocol is not written. Nothing in this charter
freezes a protocol, selects an interface, realizes a bank, resolves a revision or
authorizes execution. All model, tokenizer, cloud, GPU, scoring, generation,
task-bank, interface-selection and patching counters are zero.

`formal_execution_authorized` remains `false`, `paper/evidence_ledger.csv` still
ends at `EV-0016`, and the research question remains unanswered.

The next legal action is **one Study 3R protocol-authoring session** under a
separate authority.

`STUDY3R_CLEAN_ROOM_PROTOCOL_AUTHORIZED_AWAITING_SINGLE_AUTHORING_SESSION`
