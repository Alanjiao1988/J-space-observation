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
targeted architecture compatibility change, and main must authorize that
separately. The sole separately authorized operational retry described below
is checkpoint serialization only and does not modify official source.

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
continuing. Upload history is explicit and every stage/final write is required.
A required failure is `checkpoint_failure`, makes the decision BLOCKED, and
forces nonzero exit. Before real F2 that is UNRATED; after real F2 it is AMBER.
The final snapshot keeps local outputs BLOCKED while a sibling completion
payload is staged, is valid only when its manifest upload is confirmed last,
and promotes identical bytes locally after confirmation with the same snapshot
timestamp. Unconfigured local runs do not require Blob.

Restore does not trust the newest artifact-complete snapshot blindly. It scans
manifest-complete snapshots newest to oldest, validates registered controls and
the semantic F3 checkpoint/lens bindings, and restores the newest valid state.
A newer failure snapshot containing an unbound `n_done=2` working checkpoint is
rejected in favor of the immutable older prompt-1 state; rejection reason and
selected source prefix are recorded.

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
hashed F2 artifact. Before F3, the dim-1 projection scales measured F2 time by
both prompt count and the backward layer span. For this layout, F2 spans
13→27 while F3's earliest layer spans 6→27, so the conservative multiplier is
`2 × (21/14) = 3`. That projection plus export reserve must remain inside the
6120-second planning budget.

### F3 — two-prompt, three-layer fit

F3 runs only after F2. Dynamic source layers are the observed
early-middle/middle/late-middle layers (6, 13, 20 for this target), excluding
final target layer 27. `dim_batch=2` is allowed only when F2 is green with
peak reserved at most 65% and at least 4 GiB free; otherwise it remains 1.

The ordered two-prompt generic corpus is
`data/jlens_feasibility_prompts.jsonl`. Its parsed canonical JSONL SHA256 is
recorded. It contains no Phase 1 tasks, answers, answer-only output, reference
answers, or evaluator fixtures.

Official `fit` always uses `checkpoint_every=1` and `resume=True`. From state
0/0 it first fits the one-prompt prefix, verifies `n_done=next_idx=1`, updates
and hashes the external progress manifest, and persists the versioned
`F3-prompt-1` snapshot. State 1/1 re-persists that checkpoint; state 2/2 loads
the completed checkpoint. It then resumes official fit over both prompts.
Success requires `n_prompts=2`, exactly three finite fp32 `[1536,1536]`
matrices, valid official checkpoint state, an external controls manifest,
successful `JacobianLens.save/load`, and hashes. The saved F4 lens is explicitly
serialized through the official `save(..., dtype=torch.float32)` option. Its
raw payload must contain only fp32 `J` tensors with exact metadata, and official
reload must be `torch.equal` to every fitted matrix (recorded max-abs exactly
zero). Any other `(n_done,next_idx)` pair or lossy save is a checkpoint failure.

Official checkpoints do not contain prompt identity, so resume additionally
requires the external binding. State 1/1 must match the current controls hash,
the exact registered first-prompt canonical hash, and the actual checkpoint
file SHA256. State 2/2 must match the controls hash, complete ordered-corpus
SHA256, actual checkpoint SHA256, and actual saved-lens SHA256 through a hashed
completion record. Missing, stale, or mismatched progress/completion fields
fail closed before official state is averaged or reused. State 0/0 accepts only
a controls-only manifest with no checkpoint file or stale progress/completion
binding. Prompt-1 checkpoint and manifest are copied atomically to immutable
paths before the working checkpoint can advance. State 2/2 must also validate
that exact durable prefix checkpoint SHA and progress hash, and its completion
record binds both.

The F2 projection is only preregistration input, not a reusable admission
boolean. Immediately before each official F3 fit segment the runner samples
fresh monotonic elapsed time and recomputes projected remaining fit plus export
reserve against the 6120-second admission boundary. After prompt-1 persistence,
segment 2 uses the more conservative of measured prompt-1 time and the
registered F2/layer-span estimate. A slow upload can therefore leave the valid
prefix checkpoint durable while blocking segment 2 and all later stages.

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
F4 requires two independent objects: the reconstructed/fresh in-memory fp32
fitted lens and an independently official-loaded saved lens. It never loads the
same file twice as both sides of the fidelity gate, and its existing
`rtol=atol=5e-3` output gate is unchanged.

### Authorized serialization-only operational retry

The primary run completed F0–F3, but official default-fp16 lens serialization
introduced fitted-vs-loaded Jacobian max-abs differences of
`0.000309/0.000472/0.000488`; F4 then diverged after transport/unembedding even
though model logits matched. The single authorized retry may therefore
reconstruct the exact fp32 means from the already validated complete F3
checkpoint and atomically reserialize only the lens with official
`dtype=torch.float32`.

This retry validates old stage-detail hashes, checkpoint sums/metadata,
immutable prefix bindings, completion binding, and old fp16 lens audit before
replacement. It updates lens/completion hashes atomically, revalidates all
actual files, persists/uploads `F3-resumed` manifest-last, and then reruns real
F4 forwards. Missing/tampered F2 or F3 artifacts block with
`checkpoint_failure`; F2/F3/F5 fitting is never recomputed. This registration
does not claim that the retry or F4 has succeeded.

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
and the final decision. A successful F3 measurement classified `stop`
immediately blocks F4/F5 and exits nonzero.

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

Finalize an already-built historical immutable image without build/import or
unlock:

```bash
ACR_NAME=<private-acr> \
PROJECT_SHA=<historical-full-sha> \
JLENS_FINALIZE_EXISTING_BUILD=true \
  bash infra/azure/scripts/07_build_phase05_jlens.sh
```

The repository/tag is exactly
`j-space-observation-jlens:<PROJECT_SHA>`; `:latest` and tag overwrite are
rejected. Repository/tag listing must successfully prove absence; lookup
errors are never treated as absence. Each build writes only a unique staging
tag and binds its ACR run output digest. It then creates a cryptographically
unique, no-op ARM deployment ticket under a deterministic prefix derived from
the full project SHA. All tickets under that exact prefix remain durable.
After a settling interval, every ticket (including failed/in-progress tickets)
is validated by the shared `phase05_claim_election.py` helper and ordered by
ARM's server timestamp then name. Missing timestamps/outputs, duplicate names,
prefix/provenance mismatches, or ambiguity fail closed. An earlier stale
ticket blocks safely. Only the elected ticket is re-elected on a second read,
reconfirms tag absence, and imports by digest without a force/overwrite option.
It compares the final digest, disables and verifies write/delete on both tag
and manifest. In normal builds, its own staging alias is removed and verified
after project-tag digest verification but before either tag/manifest is made
immutable. Lock verification reads the ACR CLI's nested
`changeableAttributes.writeEnabled/deleteEnabled` fields (repository metadata
for the tag and manifest metadata for the digest). The script records ticket,
ACR run, digest, locks, project SHA, and requirements/Dockerfile hashes under
ignored `results/runs/`.

Every build invocation keeps claim body/list/fixed/winner files in a
cryptographically invocation-specific mode-0700 scratch directory under its
record directory; its trap removes only that directory. `az acr repository`
commands use their supported registry/image/repository shapes and all lookup
failures remain fatal.

`JLENS_FINALIZE_EXISTING_BUILD=true` is a fail-closed recovery path for a build
that already promoted and locked successfully but failed local metadata
verification. It requires an explicit historical `PROJECT_SHA`, a clean
worktree, and a locally existing commit, while allowing launcher HEAD to be
newer. It creates no build/import/claim and performs no unlock or deletion. It
re-elects the retained durable claim, verifies claim outputs, ACR run/digest,
project tag, and nested immutable attributes, then hashes
`Dockerfile.jlens`/`requirements-jlens.txt` from that historical git object.
An already-immutable staging alias is validated against the digest and recorded
as retained; it is never unlocked merely for cleanup.

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

The job template uses the immutable `repository@sha256:...` image reference
while recording both tag and digest references. After ARM PUT, the run script
polls `properties.provisioningState` to `Succeeded` and will not call
`job start` on terminal failure or timeout.

Launch uses the same durable ticket election rather than conditional Job API
semantics. Primary and operational-retry prefixes are global to the singleton
`job-jspace-p05-jlens`, not scoped by run ID. Each ticket still binds exact run
ID, attempt, primary/current SHA, image digest, and job. Thus a later primary
for a different run ID encounters the durable global primary ticket and blocks
before Job PUT/start; conflicting provenance fails closed. A retry must match
the globally elected primary ticket's run ID and the sole failed terminal
primary execution before entering the distinct global retry election. After
settling, all prefix tickets are validated and the earliest server
`(timestamp, name)` wins. Two separated reads must elect the same current
ticket before Job PUT. The durable ticket name/timestamp/invocation are stored
in job tags. Execution count/status and provenance are then revalidated, and a
third election plus job-tag check occurs immediately before start. Retry first
proves the existing failed primary job matches the durable elected primary
ticket, then elects under a distinct retry prefix. The returned execution name
and total count must be observed after start. Missing/invalid outputs or server
timestamps, stale/failed/in-progress earlier tickets, changed winners, a
running/succeeded primary, or unverifiable execution fail closed. A crashed
earliest ticket remains a manual-intervention block instead of permitting a
duplicate launch.

Like builds, every launcher uses a cryptographically invocation-specific
scratch directory and removes only its own scratch. Only an elected winner can
write the shared durable build/start record.

Image and launcher provenance are distinct. `PROJECT_SHA` identifies the
possibly historical immutable image and must exist in local git history;
`launcher_sha` is the current clean HEAD running these controls. Both are bound
into launch-ticket outputs, job tags, validation, and the local launch record,
alongside the immutable image digest.

At most one operational correction is permitted. It must reuse the primary
run timestamp and document the correction:

```bash
ACR_NAME=<private-acr> ATTEMPT_KIND=operational-fix \
JSPACE_PHASE05_RUN_ID=<same UTC timestamp> \
PRIMARY_PROJECT_SHA=<primary 40-hex project SHA> \
OPERATIONAL_FIX_NOTE='<documented operational correction>' \
  bash infra/azure/scripts/08_run_phase05_jlens.sh
```

The run script requires exactly one prior execution and refuses retry unless it
is terminal and failed (never running or succeeded). Before overwriting the job
template it verifies the existing run-ID/primary-attempt environment plus
project, phase, policy, run-ID, primary SHA, and project-SHA tags.
`PRIMARY_PROJECT_SHA` is mandatory even when the retry uses the same SHA; a
different retry SHA is allowed only after matching the stored primary SHA.
Any third execution is rejected and no job is retried automatically. If and
only if main separately authorized a targeted J-lens compatibility change, add
`AUTHORIZED_COMPATIBILITY_FIX_ATTEMPTED=true`; the primary attempt rejects
that flag.
