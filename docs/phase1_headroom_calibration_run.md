# Phase 1.0C Track B — Azure run specification

Owner of execution: **main agent**. Agent B does not run Azure CLI, does not build
images, and does not start jobs. This document is the executable specification.

Related: `docs/phase1_headroom_calibration_protocol.md` (preregistration),
`docs/azure_runbook.md` (general Azure conventions).

## 1. What this run does

Runs the target model `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` at revision
`ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` over 150 frozen calibration items × 2
visible-reasoning conditions = **300 generations**, then emits a fully provenanced
artifact pack plus a bounded semantic-review pack.

It is **task calibration**, not an RQ1/RQ2 result. It licenses no claim about hidden
reasoning, internal state, or "J-space".

## 2. Is a new image build required?

**Yes.** The run introduces new source files that are not in any existing image:

- `src/jspace_observation/headroom_calibration.py`
- `scripts/run_phase1_headroom_calibration.py`

No new Python dependency is introduced. The module needs only the stdlib plus the
already-present `torch` / `transformers` (used lazily, only in `generate` mode) and
optionally `scipy` via `stats.wilson_ci` (with a stdlib fallback if unavailable).
The existing GPU Dockerfile therefore needs no dependency change — only a rebuild so
the new sources are present.

Dedicated image name (do not reuse a shared tag):

```
j-space-observation-calibration:<source-sha>
```

`<source-sha>` is the full 40-character git commit SHA of the source tree that is
built. Record both the tag and the resulting digest; the digest goes into
`--image-digest`.

## 3. Azure targets

| Item | Value |
| --- | --- |
| Resource group | `rg-jspace-observation-sea` |
| Region | `southeastasia` |
| Container Apps environment | `cae-jspace-observation-sea-vnet2` |
| Workload profile | `gpu-t4` |
| Registry | `acrjspaceobssea0708231738.azurecr.io` |
| Registry auth | managed identity `id-jspace-aca-acrpull-sea` with `AcrPull`; admin credentials disabled |
| Managed identity client id | `479d9229-632e-4490-ad92-854a34dfddf8` |
| Storage account | `stjspacefiles0709085305` |
| Blob container | `jspace-results` |
| Blob prefix | `phase1-headroom-calibration/<run_id>` |
| Blob auth | managed identity + private endpoint `pe-stjspacefiles-blob-sea` only. **No account key. No SAS. Public network access disabled.** |

`<run_id>` for the registered generate run is `p10c-trackb-generate-d778736ff8a2`
(`p10c-trackb-<mode>-<protocol_hash[:12]>`). Confirm it from the job's stdout summary
before creating the blob prefix.

## 4. Environment variables

| Variable | Value | Purpose |
| --- | --- | --- |
| `AZURE_CLIENT_ID` | `479d9229-632e-4490-ad92-854a34dfddf8` | user-assigned managed identity |
| `JSPACE_BLOB_ACCOUNT` | `stjspacefiles0709085305` | blob export target |
| `JSPACE_BLOB_CONTAINER` | `jspace-results` | blob export target |
| `JSPACE_BLOB_PREFIX` | `phase1-headroom-calibration/<run_id>` | required prefix |
| `JSPACE_CODE_COMMIT` | `<source-sha>` | recorded in `00_stage_manifest.json` |
| `JSPACE_IMAGE_DIGEST` | `sha256:<digest>` | recorded in `00_stage_manifest.json` |
| `JSPACE_HARDWARE` | `aca-gpu-t4` | recorded in `00_stage_manifest.json` |
| `HF_HOME` | `/tmp/models/huggingface` | model cache (container-local) |
| `TRANSFORMERS_CACHE` | `/tmp/models/huggingface` | model cache (container-local) |
| `RESULTS_DIR` | `/tmp/results` | pack output root |
| `PYTHONPATH` | `/workspace/src` | repository import path |
| `HF_HUB_DISABLE_TELEMETRY` | `1` | no telemetry |
| `TOKENIZERS_PARALLELISM` | `false` | deterministic tokenizer behaviour |

Do **not** set `JSPACE_FROZEN_TIME` for the real generate run; the pack must record
real wall-clock start/end times. `JSPACE_FROZEN_TIME` is for reproducibility checks
only.

## 5. Stage 1 — generate (GPU, main agent)

Container command:

```
python scripts/run_phase1_headroom_calibration.py \
  --mode generate \
  --bank /workspace/data/phase1_task_headroom_candidates.jsonl \
  --output-root /tmp/results \
  --code-commit "$JSPACE_CODE_COMMIT" \
  --image-digest "$JSPACE_IMAGE_DIGEST" \
  --hardware "$JSPACE_HARDWARE" \
  --upload-blob
```

As a single-line `JOB_COMMAND` for `infra/azure/scripts/06_run_job_acr_mi.sh`:

```
JOB_COMMAND='python scripts/run_phase1_headroom_calibration.py --mode generate --bank /workspace/data/phase1_task_headroom_candidates.jsonl --output-root /tmp/results --code-commit "$JSPACE_CODE_COMMIT" --image-digest "$JSPACE_IMAGE_DIGEST" --hardware "$JSPACE_HARDWARE" --upload-blob'
```

Working directory inside the container: `/workspace`.

Resource expectations:

- 1 × T4 GPU, ~8 GiB GPU memory for a 1.5B model in bf16/fp16.
- 300 generations × up to 512 new tokens. Budget 45–90 minutes; set the job timeout
  to at least 3 hours so a slow run is never truncated mid-pack.
- The model is downloaded once at the pinned revision into `HF_HOME`.

Expected stdout (single JSON line):

```json
{"cells_scored": 30, "mode": "generate", "output_dir": "/tmp/results/p10c-trackb-generate-...", "records": 300, "review_rows": <n>, "run_id": "p10c-trackb-generate-...", "selected_headroom_cells": [], "status": "INCONCLUSIVE"}
```

`INCONCLUSIVE` at this stage is **correct and expected**: labels are not yet
adjudicated, so no cell may be selected.

### Post-conditions to verify before stage 2

1. `02_records.jsonl` has exactly 300 lines, every line `status = "generated"`.
2. `00_stage_manifest.json` `model_revision` equals the pinned revision.
3. `artifact_manifest.json` digests match the uploaded blobs.
4. The blob prefix is exactly `phase1-headroom-calibration/<run_id>`.

## 6. Stage 2 — bounded semantic review (no GPU)

Hand `review_pack/` to a semantic reviewer agent:

- `review_pack/review_pack.jsonl` — the blinded rows to adjudicate
- `review_pack/review_instructions.md` — the adjudication rules
- `review_pack/deterministic_triage.jsonl` — **withhold from the primary reviewer**;
  it is the sidecar used to detect conflicts
- `review_pack/arbitration_packet.jsonl` — only the rows where the primary label
  conflicts with a definite deterministic verdict

Primary reviewer output (one JSON object per line):

```json
{"review_id": "R001", "record_id": "...", "semantic_label": "correct", "reviewer_id": "reviewer-a", "notes": ""}
```

Arbiter output uses the same shape with the arbiter's `reviewer_id`.

Parser v2 output must never be pasted in as a label. `review_load_fraction` in
`03_metrics.csv` shows how many of the 300 rows require review before commissioning.

## 7. Stage 3 — finalize (no GPU, CPU container or local)

```
python scripts/run_phase1_headroom_calibration.py \
  --mode finalize \
  --records <path>/02_records.jsonl \
  --judgments <path>/primary_judgments.jsonl \
  --arbiter-judgments <path>/arbiter_judgments.jsonl \
  --output-root /tmp/results \
  --code-commit "$JSPACE_CODE_COMMIT" \
  --image-digest "$JSPACE_IMAGE_DIGEST" \
  --hardware "$JSPACE_HARDWARE" \
  --upload-blob
```

`--arbiter-judgments` may be omitted when `arbitration_packet.jsonl` is empty.

Expected status: `COMPLETE` when every flagged row has an adjudicated label and no
unresolved labels remain; otherwise `INCONCLUSIVE` with the outstanding cells listed
under `supplementary_review_required` in
`cell_selection/cell_exclusion_reasons.json`.

Final selection outputs:

- `cell_selection/selected_headroom_cells.csv`
- `cell_selection/excluded_cells.csv`
- `cell_selection/cell_exclusion_reasons.json`

## 8. Dry runs that need no Azure resources

```
python scripts/run_phase1_headroom_calibration.py --mode plan --frozen-time 2026-07-25T00:00:00Z
python scripts/run_phase1_headroom_calibration.py --mode self-test --frozen-time 2026-07-25T00:00:00Z
```

`plan` emits the registered selection and generation plan with status `BLOCKED` and
never loads a model. `self-test` exercises the whole pipeline against a deterministic
synthetic backend and registers a deviation saying the outputs are fixtures. Both are
safe on CPU and are what CI runs.

## 9. Failure handling

| Symptom | Action |
| --- | --- |
| Job OOM or CUDA fault | Retry the whole job with the identical command; seeds are derived per unit so the retry is bit-identical in intent. Record the retry in `08_deviations.json`. |
| Fewer than 300 generated rows | Do not patch the pack. Re-run generate. A partial pack stays `BLOCKED`/`INCONCLUSIVE`. |
| Model revision mismatch | Stop. The pinned revision is part of the protocol hash; a mismatch invalidates every cell. |
| Blob upload failure | Re-run the upload only; never regenerate to "fix" an upload. `--upload-blob` uses `require=True` and fails loudly rather than silently skipping. |
| Reviewer disagreement | Route to the arbiter via `arbitration_packet.jsonl`; never overwrite the primary label. |

## 10. Explicit non-goals for this run

- No `prompt_only_raw_strict`, empty-think prefill, answer-prefill, stopped, or
  postprocessed condition.
- No pass@k, no multi-sample estimation.
- No mechanistic, patching, or ablation experiment.
- No claim about hidden reasoning, internal representations, or "J-space".
