# Phase 0.5A: real J-lens feasibility protocol

## Status and boundary

This file preregisters Track A Phase 0.5A tooling. Tooling alone is
**UNRATED**. Main will build and execute it after integration. This track does
not download or run the target model, use GPU/Azure/ACR, inspect locked
evaluator material, change parser-v2 labels, or trigger Plan B.

The run asks only whether the official Jacobian-lens implementation can
compute, checkpoint, reload, and technically apply a small real Jacobian lens
on one T4. F4 token rankings are a technical sanity check, not semantic or
hidden-workspace evidence.

## Immutable provenance

- Official repository:
  `https://github.com/anthropics/jacobian-lens`
- Exact source commit:
  `581d398613e5602a5af361e1c34d3a92ea82ba8e`
- Distribution/import: `jlens` / `jlens`
- Version/license/Python: `0.1.0`, Apache-2.0, Python 3.11
- Official `uv.lock` at that commit:
  SHA256 `981e580531e517be1bd1a3fef98ac12822f40d626ba8f365e59973ff258f36ea`
- Floating `main`, `HEAD`, an unpinned Git install, and the nonexistent
  `jacobian_lens` import are forbidden.

The exact VCS requirement is:

```text
jlens @ git+https://github.com/anthropics/jacobian-lens.git@581d398613e5602a5af361e1c34d3a92ea82ba8e
```

`requirements-jlens.txt` reproduces the official Python >=3.11 core
resolution, including torch 2.12.0, transformers 5.9.0,
huggingface-hub 1.16.1, numpy 2.4.6, its Linux CUDA/Triton branch, and
important transitive dependencies. It adds exact Azure managed-identity Blob
SDK and `psutil` pins; those additions are the only intentional divergence
from the official lock. The Docker build installs the exact VCS source rather
than vendoring or modifying it. Its Python 3.11.14 slim-bookworm base is pinned
to OCI index digest
`sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d`.

F0 verifies installed `direct_url.json`, commit, package path, distribution
metadata, API signatures, dependency versions, and runtime freeze. It also
records SHA256 hashes of `requirements-jlens.txt`, `Dockerfile.jlens`, and the
corpus. A mismatch is `dependency_failure`, stops the run, and remains
UNRATED/BLOCKED.

## Immutable target

- Model/config/tokenizer:
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
- Revision:
  `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`
- Expected config: `Qwen2ForCausalLM`, 28 layers, residual width 1536
- Checkpoint metadata dtype: bfloat16
- T4 runtime dtype: float16
- `trust_remote_code=False` for config, tokenizer, and model
- One CUDA device; no quantization, device sharding, compilation, or remote
  architecture code
- `use_cache=False`, `output_hidden_states=False`, eval mode

The same pinned revision is passed to all three Hugging Face loads. F0 may
retrieve config metadata only. Model and tokenizer loading begins in F1.

## Official interface boundary

Only the public pinned implementation is used:

```python
jlens.from_hf(
    hf_model, tokenizer, layout=None, text_module=None,
    compile=False, force_bos=True,
)
jlens.jacobian_for_prompt(
    model, prompt, source_layers, target_layer=target,
    dim_batch=1, max_seq_len=32, skip_first=16,
)
jlens.fit(
    model, prompts, source_layers=layers, target_layer=target,
    dim_batch=dim_batch, max_seq_len=32, skip_first=16,
    checkpoint_path=path, checkpoint_every=1, resume=True,
)
jlens.JacobianLens.load(path)
lens.save(path)
lens.apply(
    model, prompt, layers=fitted_layers, positions=[-1],
    max_seq_len=32, use_jacobian=True,
)
jlens.JacobianLens.merge(lenses)
```

The likely direct Qwen2 `model.layers` layout must be selected by the official
auto-layout. This track contains no source fork, vendored implementation, or
preemptive architecture adapter. Only a real F1/F2 failure may motivate one
targeted compatibility change, and main must authorize that separately.

## Stages and recovery

The runner writes the JSON/Markdown/CSV snapshots at stage entry and stage
completion. Prior successful stages survive later failures. F3 uses the
official atomic checkpoint and an external controls manifest. `--resume`
validates the model, revision, ordered-corpus hash, layers, estimator controls,
dtype, backend, and controls hash before allowing official resume.

When Blob variables are configured, each snapshot is uploaded with
`DefaultAzureCredential` restricted to managed identity. Blob writes use
`overwrite=False`; the artifact manifest is last. An operational retry can set
`JSPACE_BLOB_RESUME_PREFIX` to restore the newest prior snapshot before
continuing. Upload failure is explicit in local stage/environment output.

Stage ordering is strict: F0 → F1 → F2 → F3 → F4, then optional F5. A failed
prerequisite blocks all later stages.

### F0 — import, provenance, and environment

F0 does not load model weights. It:

1. validates the official source/distribution/version/license/API;
2. validates exact important dependency versions and records `pip freeze`;
3. loads pinned config metadata and checks architecture, layers, width,
   checkpoint dtype, and resolved commit;
4. requires Python 3.11, exactly one visible T4, and CUDA;
5. performs a finite nonzero fp16 toy CUDA backward;
6. records CUDA/cuDNN, GPU identity/memory, host memory/RSS, disk, corpus hash,
   and requirements/Dockerfile/corpus hashes.

Any mismatch is `dependency_failure` and is not RED.

### F1 — exact target plus official adapter

F1 loads the exact config/tokenizer/model revision to `cuda:0` in float16,
sets eval/no-cache/no-hidden-state controls, and leaves gradient mode enabled.
It calls the official `jlens.from_hf` with `compile=False`.

It requires 28 layers, width 1536, direct `model.layers`, 28 registrable
official hook handles, a width-compatible unembedding, and a finite ordinary
forward. It records requested/resolved revisions, versions, GPU identity and
memory. It performs no fitting.

### F2 — first true gate

F2 uses one deterministic generic prompt separate from the fit corpus and F4
sanity prompts. Tokenization is guarded to 24–32 tokens after truncation and
must leave positions after `skip_first=16`.

It selects the observed middle source layer (13 for 28 layers), target layer
27, `dim_batch=1`, and `max_seq_len=32`. It calls the real official
`jacobian_for_prompt`. A temporary wrapper counts actual
`torch.autograd.grad` calls without changing official source. Success requires
`ceil(1536/1)=1536` successful calls and a finite, nonzero
`[1536,1536]` fp32 CPU matrix.

F2 records wall time, peak allocated/reserved VRAM, free/total VRAM, host RSS,
sequence length, valid positions, passes, layers, shape/dtype/norm, and saves a
hashed F2 artifact. Before F3, a conservative two-prompt projection at the
measured F2 rate plus export reserve must remain inside the 6120-second
planning budget.

### F3 — two-prompt, three-layer fit

F3 runs only after F2. Dynamic source layers are the observed
early-middle/middle/late-middle layers (6, 13, 20 for this target), excluding
final target layer 27. `dim_batch=2` is allowed only when F2 is green with
peak reserved at most 65% and at least 4 GiB free; otherwise it remains 1.

The ordered two-prompt generic corpus is
`data/jlens_feasibility_prompts.jsonl`. Its parsed canonical JSONL SHA256 is
recorded. It contains no Phase 1 tasks, answers, answer-only output, reference
answers, or evaluator fixtures.

The official `fit` call uses `checkpoint_every=1` and `resume=True`. Success
requires `n_prompts=2`, exactly three finite fp32 `[1536,1536]` matrices, valid
official checkpoint state, an external controls manifest, successful
`JacobianLens.save/load`, hashes, and bounded fp16 save/load numerical error.

Measured F0/F1 environment/model-load overhead plus per-prompt fit time
produces two explicit scaling projections:

- one 10-prompt job;
- a 25-prompt path sliced `[10,10,5]`, followed by weighted merge.

Both must fit the planning/watchdog and green-memory controls for GREEN.

### F4 — technical apply sanity

F4 uses three separate prompts: entity completion, one-step concept, and a
technical ordering completion. These are distinct from F2 and the fit corpus.
It calls `lens.apply` at `positions=[-1]`, only for fitted layers, with
`use_jacobian=True`.

Success requires nonempty finite shape-correct logits, sorted layer order,
finite relations to the official model logits, top-k IDs/decoded text, and
numerically consistent output from the saved/reloaded lens. The top-k artifact
states `technical_sanity_only_no_semantic_claim`.

A forward/logit lens or `use_jacobian=False` is never a substitute.

### F5 — optional merge equivalence

F5 reuses F3 as direct `fit(A,B)`, separately fits A and B, merges with
`JacobianLens.merge`, and compares layer sets, prompt count, shapes, maximum
absolute error, and relative norm.

It runs only when projected completion including 300 seconds of export reserve
is within the 6120-second planning budget and 6900-second application
watchdog, with green memory. Otherwise its terminal status is
`skipped_cost_guard`, not failure.

## Resource gates

- Platform timeout: 7200 seconds
- Application watchdog: 6900 seconds
- Planning budget: 6120 seconds
- Export reserve: 300 seconds
- GPU green: peak reserved ≤85% total **and** free ≥2 GiB
- GPU borderline: >85% to <92%, or free 1–2 GiB
- GPU hard stop: peak reserved ≥92% or free <1 GiB
- Host green: process RSS ≤75% physical memory
- Host hard stop: process RSS ≥90%

The F2/F3 peak/free measurements, not nominal model size, control continuation
and the final decision.

## Failure and decision taxonomy

Failure classes are:

`dependency_failure`, `adapter_failure`, `unsupported_autograd`, `cuda_oom`,
`timeout`, `numerical_failure`, `checkpoint_failure`, and `unknown`.

- **GREEN**: F0–F4 succeed, memory is green, checkpoint/save/load/apply pass,
  and measured 10-prompt plus `[10,10,5]` scaling paths are executable.
- **AMBER**: real F2 works, but F3/F4 or measured scaling/memory is
  incomplete/borderline.
- **RED**: pinned dependencies and F1 adapter were checked and minimal F2 still
  fails after exactly one separately authorized compatibility-fix attempt.
- **UNRATED/BLOCKED**: tooling before execution, dependency/F1 block, or an F2
  failure that has not received the one authorized compatibility attempt.

No result automatically starts Plan B.

## Outputs

The local output root contains:

- `phase05_jlens_environment.json`
- `phase05_jlens_stage_results.json`
- `phase05_jlens_metrics.csv`
- `phase05_jlens_decision.json`
- `phase05_jlens_report.md`
- `phase05_jlens_artifact_manifest.json`
- `checkpoint/phase05_jlens_f2_jacobian.pt` after F2
- F3 official checkpoint and external manifest after F3
- `lens/phase05_jlens.pt` after F3
- `phase05_jlens_topk_sanity.json` after F4

The artifact manifest is path-sorted and records bytes/SHA256. Blob prefixes
are `phase05-jlens-feasibility/<UTC timestamp>/attempts/<attempt>/...`.

## Isolated image and Azure procedure

`Dockerfile.jlens` is Python 3.11, nonroot, and has separate writable HF cache,
results, checkpoint, cache, and temporary paths under `/workspace/runtime`.
It copies no model cache and does not depend on semantic-audit attestation.

Build exactly once under the immutable project commit:

```bash
ACR_NAME=<private-acr> \
  bash infra/azure/scripts/07_build_phase05_jlens.sh
```

The repository/tag is exactly
`j-space-observation-jlens:<PROJECT_SHA>`; `:latest` and tag overwrite are
rejected. The script records ACR run ID, image reference/digest, project SHA,
and requirements/Dockerfile hashes under ignored `results/runs/`.

Start the primary execution:

```bash
ACR_NAME=<private-acr> ATTEMPT_KIND=primary \
JSPACE_PHASE05_RUN_ID=<UTC timestamp> \
  bash infra/azure/scripts/08_run_phase05_jlens.sh
```

The script fixes:

- job `job-jspace-p05-jlens`;
- environment `cae-jspace-observation-sea-vnet2`;
- workload profile `gpu-t4`, one replica/one T4;
- timeout 7200 and application watchdog 6900;
- identity `id-jspace-aca-acrpull-sea`;
- Blob account/container
  `stjspacefiles0709085305` / `jspace-results`;
- managed identity, private Blob (`publicNetworkAccess=Disabled`), no
  key/SAS, no public network, and no Azure Files;
- `replicaRetryLimit=0`.

At most one operational correction is permitted. It must reuse the primary
run timestamp and document the correction:

```bash
ACR_NAME=<private-acr> ATTEMPT_KIND=operational-fix \
JSPACE_PHASE05_RUN_ID=<same UTC timestamp> \
OPERATIONAL_FIX_NOTE='<documented operational correction>' \
  bash infra/azure/scripts/08_run_phase05_jlens.sh
```

The run script queries prior executions and rejects a second primary, a retry
without exactly one prior execution, or any third execution. It never retries
the job automatically. If and only if main separately authorized a targeted
J-lens compatibility change, add
`AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED=true`; the primary attempt rejects
that flag.
