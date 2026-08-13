# Stage P0-R1 — the repaired feasibility continuation

> **State:** `STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE`
>
> **Generation 3 is the current generation.** The binding object is
> [`p0_r1_execution_lock_v3.json`](p0_r1_execution_lock_v3.json) and the
> operative handoff is [`P0_R1_HANDOFF_V3.md`](P0_R1_HANDOFF_V3.md).
> Generations 1 and 2 are **superseded without consumption**, retained
> byte-for-byte as history, and must not be launched.
>
> P0-R1 is **registered, not executed**. No tokenizer has been constructed, no
> checkpoint downloaded, no weight loaded, no GPU allocated, no forward pass
> performed and no text generated in any round that created or repaired this
> package. Every P0-R1 counter is zero.

Authority: [`../../prompts/study3_v0_6_p0_r1_authority.md`](../../prompts/study3_v0_6_p0_r1_authority.md)
§6 and §7 (registration), then
[`../../prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md`](../../prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md)
(generation-2 transport and exception safety), then
[`../../prompts/study3_p0_r1_generation3_execution_closure_authority.md`](../../prompts/study3_p0_r1_generation3_execution_closure_authority.md)
(generation-3 production-path closure).

## Why there is a P0-R1

Stage P0-T ran once and published
`STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE`. Its own
disposition disclosed two mechanical defects:

* the registered `S2`/`S3` single-position scoring rule is **not implementable**
  under any pinned role tokenizer, because each complete candidate surface is two
  tokens; and
* the gate's eligibility classifier **propagated** a role-level `S2` failure onto
  27 mechanically valid `S1` cells, producing ineligible rows with empty reason
  lists and an over-severe terminal state.

P0-T is single-shot and no fix-and-rerun was authorized, so the defects were
disclosed rather than repaired. draft-v0.6 repairs the scoring boundary and this
package repairs the classifier — both in **new** objects. Not one byte under
`studies/study3/pilot/p0/` is edited.

## What is immutable here

| object | status |
| --- | --- |
| `../p0/results/p0-t/*` | immutable historical observation; read-only input to the replay gate |
| `../p0/corpus/p0_corpus.json` | the frozen 35-cell / 70-member corpus, reused **byte-exactly** |
| `../p0/*.py`, `../p0/container/*` | byte-protected |
| `tests/test_study3_p0_feasibility_pilot.py` | byte-protected |
| the 4,956 historical encodes | cumulative and non-resettable; none is repeated |

## The package

| file | role |
| --- | --- |
| `p0_r1_protocol.py` / `.json` | the state machine, counter ontology, caps, pinned identities and path allowlists |
| `p0_r1_counters.py` | cumulative counters, identity cardinalities, `tokenizer_construction_events`, the aggregate view |
| `p0_r1_factorization.py` | the **replay-only** verifier. Reads the immutable P0-T result, performs **zero** encodes, derives the common-prefix and discriminant token identities |
| `p0_r1_eligibility.py` | the versioned successor classifier |
| `p0_r1_replay_gate.py` | binds the two together; `--derive` for calibration, `--gate` for the successor session |
| `p0_r1_model_runner.py` | the draft-v0.6 scoring contract and the execution shell |
| `p0_r1_schemas.py` | document schemas and the production validators the negative mutations must fail against |
| `p0_r1_summarize.py` | deterministic, lossless summarization |
| `p0_r1_validate.py` | the pre-execution and image-build validation |
| `p0_r1_pre_execution_receipt.json` | binds authority, candidate, corpus, P0-T sources, revisions, container, code blobs, counters and caps |
| `container/` | the digest-pinned image, frozen dependencies and the ACR task |

## The scoring rule, in one paragraph

Every complete `S2`/`S3` candidate factors as
`candidate_d = common_prefix || discriminant_d`. The scoring context is the
registered prompt token IDs **followed by** the verified common-prefix token,
formed by concatenation and never by re-encoding. One ordinary prefill evaluation
is performed on that context, and the next-token logit vector is read only at the
ten verified discriminant token IDs. The deterministic restricted argmax maps
back to the complete registered candidate surface. `S3` reuses that exact vector
on CPU and adds zero model evaluations. `S1` and `S4` are unchanged.

The common prefix is a **teacher-forced candidate prefix**: not a
prompt-rendering change, not a generated token, not a separate sequence-level
evaluation. It is counted explicitly by `common_prefix_tokens_processed`.

## Running it

The calibration session may run only the derivation:

```
python studies/study3/pilot/p0_r1/p0_r1_factorization.py --check
python studies/study3/pilot/p0_r1/p0_r1_replay_gate.py --derive
python studies/study3/pilot/p0_r1/p0_r1_protocol.py --check
python studies/study3/pilot/p0_r1/p0_r1_validate.py --pre-execution
```

`p0_r1_replay_gate.py --gate` **refuses** to run and returns exit code 3. The
registered replay gate is the first action of the successor session.

## The successor session's envelope

Run the replay gate first. It performs no new encode and must verify, from
immutable source artifacts, all five conditions of §3.2 and the corrected
eligibility matrix.

* **If replay fails**, publish a registered stop and perform **no** model
  operation. Do not repair and rerun.
* **If replay passes**, run the repaired model pilot in one Azure containerized
  GPU job, one checkpoint at a time, fp16, evaluation mode, no sampling, no
  gradients, no adapters, no quantization, no hosted inference, no local
  workstation model execution.

Retained allocation and maxima:

| quantity | value |
| --- | --- |
| K2 smoke non-generative prefills | 60 (exact) |
| automatic extension upper bound | 180 prefills |
| `S4` diagnostic generations | 12, at most 4 new tokens each |
| total sequence-level model-evaluation equivalents | ≤ 228 |
| scored rows | 162 `S1` + 18 `S2` + 18 `S3` (CPU reuse) + 12 `S4` = 210 |
| provider calls, seeds, bank rows, positive-reference operations, activations, lenses, probes, patches, interventions, ablations | 0 |

Correctness, accuracy, diversity and discordance are **descriptive only** and are
never smoke-pass criteria. Every valid row, raw `S4` completion, exception,
partial result and counter is preserved. No output-conditioned retry or row
replacement is authorized. One infrastructure retry is allowed only when a signed
receipt proves zero new tokenizer, model-load, prefill, decode, scoring and
generation operations.

## Claim boundary

P0-R1 data are methods-feasibility observations. They do not enter
`paper/evidence_ledger.csv`, choose an interface, estimate a confirmatory effect,
set a threshold or sample size, or answer the research question. `formal_execution_authorized`
is false. `OD2`, `UR-22` and every `RP` object remain unresolved. The complete
`study3-p0-only/` namespace remains permanently excluded from every formal bank.
