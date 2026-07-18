# Phase 0.5A real Jacobian Lens T4 feasibility

## Result

Phase 0.5A is **GREEN / COMPLETE for bounded technical feasibility only** on
one Tesla T4.

The pinned official `jlens` package imported and wrapped the target model, one
real Jacobian was computed, three Jacobian matrices were fit from two generic
prompts, and the saved fp32 lens reloaded and technically applied to three
sanity prompts. The final result followed one authorized serialization-only
operational retry that reused F2/F3 without recomputation.

This result does **not** validate lens scientific quality, hidden reasoning,
internal CoT, an internal workspace, or J-space. F5 and actual 10- or 25-prompt
fits were not run.

## Run identity

| Field | Value |
|---|---|
| Run ID | `20260718T184445Z` |
| Target model | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` |
| Model/config/tokenizer revision | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| Architecture | `Qwen2ForCausalLM`, 28 layers, width 1536 |
| Checkpoint metadata dtype | `torch.bfloat16` |
| Runtime dtype | `float16` |
| GPU | Tesla T4, 16,704,405,504 bytes |
| Azure environment | `cae-jspace-observation-sea-vnet2` |
| Workload profile | `gpu-t4` / `Consumption-GPU-NC8as-T4` |
| Job | `job-jspace-p05-jlens` |
| Blob root | `phase05-jlens-feasibility/20260718T184445Z` |
| Final snapshot | `attempts/operational-fix/snapshots/11-final` |

## Immutable provenance

| Component | Pinned value |
|---|---|
| Official repository | `https://github.com/anthropics/jacobian-lens` |
| Official commit | `581d398613e5602a5af361e1c34d3a92ea82ba8e` |
| Package / version | `jlens==0.1.0` |
| License | Apache-2.0 |
| Official lock SHA-256 | `981e580531e517be1bd1a3fef98ac12822f40d626ba8f365e59973ff258f36ea` |
| Core runtime | Python 3.11.14; torch 2.12.0; transformers 5.9.0; huggingface-hub 1.16.1; numpy 2.4.6 |
| CUDA / cuDNN | 13.0 / 92000 |
| Fit corpus | 2 generic prompts; canonical SHA-256 `2e421ed4fc806fe1d7e6e09e2b1dfc946295d8f0cf90a844f06e88c312b09290` |

The official source was installed from the exact Git commit and was not
modified. Project code supplied only the model adapter, staged controls,
checkpoint bindings, persistence, and reporting.

Two immutable images were used:

| Attempt | Source commit | ACR run | Digest |
|---|---|---|---|
| Primary | `86922df02143d191dfa3d9fcf1d92adfaffc0062` | `cmh` | `sha256:d3ffaba4fea1d4ee9b03dc5dd369f5b2c5100c84d183f7a729f609d2187bb22f` |
| Operational fix | `5d4945b6ec477b6da485d19d90daeeb274b919e7` | `cmj` | `sha256:345dde4f70235af3ad2542f79ea1445b66f4f53abe6fd569cd0818b8c4e8db35` |

Both tags and manifests were write/delete disabled. `latest` was not used.
The retry was launched by digest with launcher commit
`be997eefbaec410107045dac7c50423f7297c633`.

## Attempt history

| Attempt | Execution | F0 | F1 | F2 | F3 | F4 | F5 | Outcome |
|---|---|---|---|---|---|---|---|---|
| Primary | `job-jspace-p05-jlens-l7tipil` | success | success | success | success | failed | blocked | AMBER / BLOCKED |
| Operational fix | `job-jspace-p05-jlens-m1sazlr` | success | success | reused | reused | success | skipped | GREEN / COMPLETE |

The primary F4 error was:

```text
phase05_jlens.CheckpointValidationError:
F4 saved/reloaded apply mismatch at layer 13
```

Official `JacobianLens.save` had used its default fp16 serialization. Relative
to the fitted fp32 matrices, the saved/reloaded maximum absolute errors were
`0.0003093481`, `0.0004719496`, and `0.00048828125` for layers 6, 13,
and 20. The mismatch appeared after Jacobian transport and unembedding even
though ordinary model logits matched.

An independent review classified this as checkpoint serialization rather than
a scientific result. The sole authorized retry:

1. restored the completed F3 checkpoint from the primary final blocked
   snapshot;
2. verified all checkpoint, prompt-prefix, control, and old-lens hashes;
3. reconstructed the exact fp32 fitted means;
4. used official `JacobianLens.save(..., dtype=torch.float32)`;
5. retained the original F4 `rtol=atol=5e-3` gate; and
6. prohibited F2, F3, and F5 recomputation.

The primary artifacts remain immutable audit provenance.

## Stage results

### F0 — import and provenance

- Result: success.
- Official source commit and `direct_url.json` matched the registered pin.
- The expected package, license, API signatures, and dependency versions
  matched.
- The fp16 toy backward check passed.
- F0 performed metadata/config checks and did not load the target model.

### F1 — model wrapping

- Result: success.
- Model/config/tokenizer all resolved to the registered revision.
- `n_layers=28`; `d_model=1536`.
- Official `from_hf` registered 28 hook handles using `model.layers`.
- Ordinary forward logits had shape `[1, 32, 151936]` and were finite.
- Gradient mode was enabled; cache and compilation were disabled.

### F2 — minimal real Jacobian

- Result: success on the primary attempt and reused unchanged on retry.
- Source layer 13; target layer 27.
- Sequence length 32; `skip_first=16`; valid positions 15.
- `dim_batch=1`.
- Exactly 1536 attempted and 1536 successful `torch.autograd.grad` calls.
- Jacobian: `[1536,1536]`, fp32 CPU, finite and nonzero.
- Norm: `45.54924392700195`.
- Compute time: `34.9569s`; stage time: `35.0547s`.
- Peak GPU allocated/reserved:
  `3,613,836,800 / 3,808,428,032` bytes.
- Free GPU memory: `12,748,193,792` bytes (`11.8727 GiB`).
- Memory classification: green.
- Artifact SHA-256:
  `e30e93b9bf317293a892cb75e550d278affddbb2c260c2501ff31cda6aea6907`.

### F3 — two-prompt, three-layer fit

- Result: success on the primary attempt and reused unchanged on retry.
- Prompts: 2; source layers `[6,13,20]`; target layer 27.
- `dim_batch=2`; sequence length 32.
- Fit time: `53.6796s`; stage time: `55.0273s`.
- Peak GPU reserved: `3,812,622,336` bytes; free:
  `12,741,902,336` bytes.
- Memory classification: green.
- The prompt-1 prefix checkpoint was persisted before prompt 2.
- Completed checkpoint SHA-256:
  `16cde88ecaac54deceaa911617b8add269460d4f4be937c893df320fd4cbd051`.
- Final fp32 lens SHA-256:
  `8551dea7d3eba03930765ad65d108dec79a022a779755a3aec63f3c0da716318`.
- Reloaded matrices were exactly equal to the fitted matrices at all three
  layers; maximum absolute error was zero.

F2/F3 timing, memory, and fit counts in the final aggregate artifact are
historical primary measurements. They are not retry computations.

### F4 — technical apply sanity

- Result: success after the serialization-only retry.
- Three disjoint technical sanity prompts and three fitted layers.
- `positions=[-1]`; `use_jacobian=true`.
- Output logits were nonempty, finite, and shape-correct.
- Layer ordering and saved/reloaded output consistency passed.
- Top-k artifact SHA-256:
  `f57b21cba414b41478ce7e59360e3bb2072f8fbe82ea7731950e5c27bcd42e68`.
- Duration: `1.8287s`.
- Semantic claim: none.

The top-k output is retained only as a transport/application sanity artifact.
Its tokens, rankings, decoded strings, and logit relationships are not
semantic evidence.

### F5 — optional merge equivalence

- Performed: no.
- Recorded status: `skipped_cost_guard`.
- Actual reason: the authorized retry prohibited every additional Jacobian
  fit or recomputation.
- F5 is optional and did not convert an otherwise successful F0-F4 result into
  failure.

## Scaling and feasibility decision

Measured F0/F1 overhead and F3 per-prompt time produced:

- one 10-prompt projection: executable;
- one 25-prompt `[10,10,5]` sliced projection: executable;
- estimated longest job: `609.4661s`.

These are measured **projections**, not executed 10- or 25-prompt fits and not
lens-quality validation.

The registered GREEN gate passed because F0-F4 succeeded, memory stayed green,
checkpoint/save/load/apply checks passed, final persistence completed, and
both registered projections fit the time controls. GREEN permits only a
separately reviewed Plan A engineering decision. It does not authorize a full
experiment, establish lens quality, or automatically trigger Plan B.

## Persistence and security

- Final decision: `GREEN`.
- Gate status: `COMPLETE`.
- Final manifest was uploaded last.
- Final persistence status: confirmed; failed uploads: none.
- Final manifest contains 12 declared artifacts; the completed snapshot has
  those artifacts plus the manifest.
- Blob access used `ManagedIdentityCredential` through
  `id-jspace-aca-acrpull-sea` and the private endpoint.
- Storage public access remained disabled and shared-key access remained
  false.
- No key, SAS, public Storage path, or Azure Files mount was used.

The two CPU-only artifact readers
`job-jspace-p05-artifact-read-sq8pyw3` and
`job-jspace-p05-artifact-read-0g9i4bz` performed read-only text retrieval.
They loaded no model, used no GPU, and wrote no Blob object.

## Post-run reviews

Seven independent `gpt-5.6-sol/max` reviews completed:

| Review | Result |
|---|---|
| J-lens provenance | PASS |
| J-lens runtime | PASS |
| J-lens method | PASS |
| Parser-v2 public development isolation | PASS |
| Prospective no-CoT taxonomy | PASS |
| Capability/headroom protocol | PASS |
| Scientific boundaries | PASS after stale publication text was corrected |

No runtime, provenance, method, parser, taxonomy, or headroom blocker remained.

## Scientific boundary

- Real official Jacobian Lens was used.
- The tiny lens is not scientifically validated.
- No new formal behavioral dataset, higher-n result, or locked parser
  evaluation was produced.
- The stopped branch remains an intervention.
- Answer/empty-think prefill remains an intervention.
- Postprocessing remains answer-recovery utility, not raw no-CoT.
- There is no hidden-reasoning, internal-CoT, internal-workspace, or J-space
  claim.
- Plan B was not triggered.

The next registered gate is a separately authorized, one-shot parser-v2 locked
evaluation. It is not part of this Phase 0.5 result.
