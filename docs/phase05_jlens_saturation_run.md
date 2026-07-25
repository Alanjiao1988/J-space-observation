# Phase 0.5B J-lens saturation — Azure run specification

Owner of execution: **main agent**. Track A (Agent A) prepared the code,
corpus, protocol, and this specification but ran no Azure command, built no
image, and started no job.

Read `docs/phase05_jlens_saturation_protocol.md` first. That document is the
preregistration; this document is only the execution recipe.

## 1. Image: a rebuild is REQUIRED

The Phase 0.5A image cannot be reused.

- Phase 0.5A digest (from `docs/run_log.md`):
  `acrjspaceobssea0708231738.azurecr.io/j-space-observation-jlens@sha256:345dde4f70235af3ad2542f79ea1445b66f4f53abe6fd569cd0818b8c4e8db35`
- Reason: `Dockerfile.jlens` copies an explicit allow-list of files and then
  makes `/workspace/scripts`, `/workspace/src`, and `/workspace/data`
  read-only (`chmod -R a-w`). The 0.5A image contains only
  `phase05_jlens_feasibility.py`, `phase05_jlens.py`, and
  `jlens_feasibility_prompts.jsonl`. The three new files this run needs —
  `scripts/phase05_jlens_saturation.py`,
  `src/jspace_observation/phase05_jlens_saturation.py`, and
  `data/jlens_saturation_prompts.jsonl` — are not in it and cannot be added
  at runtime.

`Dockerfile.jlens` has already been updated with the three additional `COPY`
lines. Nothing else in the image changed:

- same base digest `python:3.11.14-slim-bookworm@sha256:65a93d69…`
- same `requirements-jlens.txt` (unchanged; `psutil`, `azure-identity`,
  `azure-storage-blob` are already pinned there)
- same pinned `jlens` commit `581d398613e5602a5af361e1c34d3a92ea82ba8e`
- same non-root user `10001:10001`, same read-only code paths, same `tini`
  entrypoint
- `CMD` still points at the 0.5A feasibility script, so a 0.5A re-run is
  unaffected; the saturation job overrides `args` explicitly

Rebuild with the existing script, unchanged:

```bash
ACR_NAME=acrjspaceobssea0708231738 \
  bash infra/azure/scripts/07_build_phase05_jlens.sh
```

Record the new digest in `docs/run_log.md` before launching, and use the
digest — never a tag — in the job body.

## 2. Environment

| Setting | Value |
|---|---|
| Subscription | the existing project subscription |
| Resource group | `rg-jspace-observation-sea` |
| Location | `southeastasia` |
| ACA environment | `cae-jspace-observation-sea-vnet2` |
| Workload profile | `gpu-t4` (Consumption-GPU-NC8as-T4, Tesla T4 16 GB) |
| Job name | `job-jspace-p05-jlens-saturation` |
| User-assigned identity | `id-jspace-aca-acrpull-sea` |
| Registry | `acrjspaceobssea0708231738.azurecr.io` |
| Repository | `j-space-observation-jlens` |
| Storage account | `stjspacefiles0709085305` |
| Blob container | `jspace-results` |
| Blob prefix | `phase05-jlens-saturation/<run_id>` |

A separate job name keeps the 0.5A job definition and its launch-claim
history intact. If you prefer to reuse `job-jspace-p05-jlens`, that is
acceptable, but then the 0.5A job body is overwritten and the 0.5A tags are
lost — do not do that without recording it in `docs/decision_log.md`.

All Blob access is **managed identity + private endpoint only**. No account
key, no SAS, no connection string. The runner constructs
`DefaultAzureCredential(managed_identity_client_id=AZURE_CLIENT_ID, …)` with
every non-managed-identity credential source excluded, exactly as Phase 0.5A
does, and `phase05_jlens.validate_blob_auth_config` rejects any other mode
before the first network call.

## 3. Container command line

```
timeout --signal=TERM --kill-after=30s 6900s \
  python /workspace/scripts/phase05_jlens_saturation.py \
    --output-dir /workspace/runtime/results \
    --dim-batch 1 \
    --resume
```

Run as `["/bin/sh", "-lc", "<the command above on one line>"]`, matching the
0.5A launcher.

Argument reference:

| Argument | Default | Notes |
|---|---|---|
| `--output-dir` | `$RESULTS_DIR` | must be `/workspace/runtime/results` (the only writable code-adjacent path) |
| `--corpus` | `/workspace/data/jlens_saturation_prompts.jsonl` | leave at the default |
| `--dim-batch` | `1` | `1` or `2` only; `2` writes a deviation entry citing the 0.5A F2 headroom measurement |
| `--run-id` | `$JSPACE_PHASE05_RUN_ID`, else a UTC stamp | keep empty and set the env var instead |
| `--resume` | off | pass it; enables official jlens checkpoint resume |
| `--self-test` / `--dry-run` | off | **never** pass these in the container; they force `INCONCLUSIVE` |

Exit codes: `0` = `PASS` or `COMPLETE`; `1` = `FAIL`; `3` = `INCONCLUSIVE` or
`BLOCKED` in container mode. The artifact pack is exported in every case.

## 4. Environment variables

| Name | Value |
|---|---|
| `HF_HOME` | `/workspace/runtime/hf-cache` |
| `HUGGINGFACE_HUB_CACHE` | `/workspace/runtime/hf-cache/hub` |
| `TRANSFORMERS_CACHE` | `/workspace/runtime/hf-cache` |
| `RESULTS_DIR` | `/workspace/runtime/results` |
| `TMPDIR` | `/workspace/runtime/cache/tmp` |
| `AZURE_CLIENT_ID` | client ID of `id-jspace-aca-acrpull-sea` |
| `JSPACE_BLOB_ACCOUNT` | `stjspacefiles0709085305` |
| `JSPACE_BLOB_CONTAINER` | `jspace-results` |
| `JSPACE_BLOB_PREFIX` | `phase05-jlens-saturation/<run_id>` |
| `JSPACE_PHASE05_RUN_ID` | `<run_id>` (UTC stamp, e.g. `20260726T031500Z`) |
| `JSPACE_ATTEMPT_ID` | `primary` |
| `JSPACE_IMAGE_DIGEST` | the `sha256:…` digest of the rebuilt image |
| `JSPACE_CODE_COMMIT` | the commit the image was built from |
| `JSPACE_BLOB_RESUME_PREFIX` | optional; only for an authorized second attempt |
| `JSPACE_JLENS_DIM_BATCH` | optional; overrides the `--dim-batch` default |

`JSPACE_IMAGE_DIGEST` and `JSPACE_CODE_COMMIT` are new for this track. They
are optional — the runner records `null` if they are absent — but setting
them makes `00_stage_manifest.json` self-describing without a lookup.

## 5. Job body template

Substitute `<…>` and PUT with `az rest --method put --url "$JOB_URL"
--body @body.json`, reusing the 0.5A launch-claim election in
`infra/azure/scripts/08_run_phase05_jlens.sh` if you want the same
single-winner guarantee.

```json
{
  "location": "southeastasia",
  "identity": {
    "type": "UserAssigned",
    "userAssignedIdentities": { "<identity-resource-id>": {} }
  },
  "tags": {
    "project": "jspace-observation",
    "phase": "0.5B",
    "track": "track-a",
    "run-id": "<run_id>",
    "project-sha": "<code-commit>",
    "image-digest": "<sha256:...>",
    "launch-attempt": "primary"
  },
  "properties": {
    "environmentId": "<resource-id of cae-jspace-observation-sea-vnet2>",
    "workloadProfileName": "gpu-t4",
    "configuration": {
      "triggerType": "Manual",
      "replicaTimeout": 7200,
      "replicaRetryLimit": 0,
      "manualTriggerConfig": { "replicaCompletionCount": 1, "parallelism": 1 },
      "registries": [
        {
          "server": "acrjspaceobssea0708231738.azurecr.io",
          "identity": "<identity-resource-id>"
        }
      ]
    },
    "template": {
      "containers": [
        {
          "name": "jlens",
          "image": "acrjspaceobssea0708231738.azurecr.io/j-space-observation-jlens@<sha256:...>",
          "command": ["/bin/sh"],
          "args": [
            "-lc",
            "timeout --signal=TERM --kill-after=30s 6900s python /workspace/scripts/phase05_jlens_saturation.py --output-dir /workspace/runtime/results --dim-batch 1 --resume"
          ],
          "env": [
            { "name": "HF_HOME", "value": "/workspace/runtime/hf-cache" },
            { "name": "HUGGINGFACE_HUB_CACHE", "value": "/workspace/runtime/hf-cache/hub" },
            { "name": "TRANSFORMERS_CACHE", "value": "/workspace/runtime/hf-cache" },
            { "name": "RESULTS_DIR", "value": "/workspace/runtime/results" },
            { "name": "TMPDIR", "value": "/workspace/runtime/cache/tmp" },
            { "name": "AZURE_CLIENT_ID", "value": "<identity-client-id>" },
            { "name": "JSPACE_BLOB_ACCOUNT", "value": "stjspacefiles0709085305" },
            { "name": "JSPACE_BLOB_CONTAINER", "value": "jspace-results" },
            { "name": "JSPACE_BLOB_PREFIX", "value": "phase05-jlens-saturation/<run_id>" },
            { "name": "JSPACE_PHASE05_RUN_ID", "value": "<run_id>" },
            { "name": "JSPACE_ATTEMPT_ID", "value": "primary" },
            { "name": "JSPACE_IMAGE_DIGEST", "value": "<sha256:...>" },
            { "name": "JSPACE_CODE_COMMIT", "value": "<code-commit>" }
          ],
          "resources": { "cpu": 8.0, "memory": "56Gi" }
        }
      ]
    }
  }
}
```

## 6. Expected cost and duration

| Item | Value |
|---|---|
| Prompt-fits | 40 (10 + 10 + 10 + 5 + 3 + 2) |
| Merges | 4 |
| Apply calls | 30 (3 lenses × 10 held-out prompts) |
| Estimate at the 0.5A rate (26.84 s/prompt) | ≈ 1 320 s of fitting |
| Estimate at a pessimistic 2× rate | ≈ 2 393 s of fitting |
| Model download + load | ≈ 120–300 s cold |
| Planning budget | 6 120 s |
| Application watchdog | 6 900 s |
| `replicaTimeout` | 7 200 s |

Each stage is admitted by `phase05_jlens.f3_segment_time_guard` before it
starts. A stage that would cross the planning boundary is recorded
`skipped_time_guard` and the pack still exports.

Peak GPU memory should stay close to the 0.5A F2/F3 measurements
(≈ 3.6 GB allocated, ≈ 3.8 GB reserved of 16.7 GB) because `dim_batch`,
`max_seq_len`, and the layer set are unchanged; only the prompt count grows,
and prompts are processed one at a time.

## 7. Blob layout

```
jspace-results/
  phase05-jlens-saturation/<run_id>/attempts/primary/
    01-lens-binaries/          # checkpoints and fp32 lens tensors
    02-artifact-pack/
      00_stage_manifest.json
      01_protocol_snapshot.json
      02_records.jsonl
      03_metrics.csv
      04_decision.json
      05_summary.md
      06_paper_table.csv
      07_figure_data.csv
      08_deviations.json
      artifact_manifest.json   # uploaded last, and written last on disk
```

Lens binaries upload first so that `artifact_manifest.json` is the final blob
written for the whole run. Uploads use `overwrite=False`, so a re-run with the
same `run_id` and attempt fails loudly instead of silently replacing evidence.

Local layout inside the container mirrors this:
`/workspace/runtime/results/phase05-jlens-saturation/track-a/<run_id>/` for
the pack and `…/<run_id>-work/` for the binaries.

## 8. Pre-flight checklist

1. `git status` is clean and the commit to be built is the one recorded.
2. `python -m pytest tests/test_phase05_jlens_saturation.py tests/test_phase05_jlens_feasibility.py -q` passes.
3. `python scripts/phase05_jlens_saturation.py --self-test` exits 0 and writes ten files.
4. `data/jlens_saturation_prompts.jsonl` SHA-256 is
   `41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b`.
5. Image rebuilt; new digest recorded in `docs/run_log.md`.
6. `<run_id>` chosen and used identically in `JSPACE_PHASE05_RUN_ID` and
   `JSPACE_BLOB_PREFIX`.
7. The blob prefix `phase05-jlens-saturation/<run_id>` does not already exist.

## 9. Post-run checklist

1. Download the pack and re-run
   `phase05_jlens_saturation.validate_artifact_pack(<dir>)`; it verifies file
   presence, required fields, CSV headers, summary section order, manifest
   hashes, and that no extra file leaked into the pack.
2. Read `04_decision.json`. `decision` must be one of `ENGINEERING_STABLE`,
   `ENGINEERING_IMPROVING`, `ENGINEERING_UNSTABLE`, `INCONCLUSIVE`.
   `ENGINEERING_IMPROVING` is a legitimate, expected outcome.
3. Check `08_deviations.json` for a `merge-weighting-differs` entry. If it is
   present, the official `JacobianLens.merge` is not an `n`-weighted mean; that
   is an observation, not a failure, and the registered merge control
   (`shard_merge_vs_direct_*`) is the criterion that matters.
4. Copy the measured numbers into `docs/run_log.md` and the paper ledgers.
5. Do not restate any top-k or rank-correlation number as semantic,
   behavioral, or workspace evidence anywhere.

## 10. Prohibited

- No Azure CLI, image build, or job start by any agent other than main.
- No account key or SAS anywhere in the job body, environment, or code.
- No parser file, evaluator set, or locked artifact touched by this run.
- No claim of "workspace found", "J-space validated", "hidden reasoning
  observed", "internal workspace", or "invisible chain-of-thought" derived
  from any artifact this job produces.
