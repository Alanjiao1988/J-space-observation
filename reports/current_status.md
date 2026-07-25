# Project Status Report

## Summary

The critical-path reset is complete through bounded real-Jacobian technical
feasibility. The historical bounded n=3 record remains frozen, prospective
parser v2 was implemented from the 60-case public development set, and the
single authorized one-shot parser-v2 locked evaluation has now been executed
and closed. Its formal outcome is **FAIL**, and the 120-case locked holdout is
spent and retired. The model-free Phase 1.2B tooling delivered one-shot Azure
coordination, authenticated crash recovery, and deterministic post-label
`CLOSED/INVALID` closure, all of which were exercised in the real run. The
no-CoT taxonomy v2 and 450-item headroom candidate bank are design artifacts;
no new behavioral calibration was run.

## Current Phase

**Phase: Phase 0.5A GREEN; parser-v2 locked evaluation CLOSED with formal outcome FAIL; locked holdout retired**

## Phase 1.2B parser-v2 locked evaluation result (2026-07-25)

- Formal decision: **FAIL**, decided `2026-07-25T08:01:34Z`, formal evaluation
  ordinal 1, manual override no.
- Holdout retired and spent; parser was not re-run; metric retry and prediction
  re-run are both disallowed by the sealed attestation.
- 34 mandatory gates: 32 passed, 2 failed, 0 NA/invalid.
  - `boxed_final_miss`: 1/20 against a limit of 0 errors.
  - `wrong_span`: 2/80 against a limit of 1 error.
- Report-only aggregates: typed agreement 116/120, 4 mismatched cases, 1
  material-error case, across 120 cases in 12 strata.
- The state chain reached `CLOSED` (`12_closed_receipt.json`,
  `outcome = FAIL`), and the single authorized post-result review agreed with
  the sealed artifacts on all 38 independent checks.
- Exactly three container executions ran: one Stage-P prediction run, one
  Stage-E attempt rejected for an infrastructure reason before any label
  access, and one successful `scorer_infrastructure` retry that opened, scored,
  and retired the holdout once.
- Full record, including every authenticated artifact hash:
  `reports/phase1_parser_v2_locked_evaluation.md`.
- Boundary: this is evaluator validation, not model evaluation. No target model
  was downloaded, loaded, or run, and no GPU was used. No hidden-reasoning,
  invisible-CoT, internal-workspace, or J-space claim follows.

## Historical prerelease snapshot — superseded (2026-07-23)

> The content below describes the historical state *before* the formal locked
> evaluation was executed. It has been superseded by the 2026-07-25 CLOSED/FAIL
> result recorded above. Statements such as "no VM has been provisioned",
> "audits are pending", and "no Azure command … occurred" were accurate on
> 2026-07-23 and are retained verbatim as a point-in-time record; they no longer
> describe the current state. Nothing in this section has been renumbered or
> back-dated.

- Stage P remains label-blind and Stage E remains parser-free.
- Private DNS TXT create-only records provide separate build, launch, and
  dispatch capabilities; recovery cannot recreate a PUT/start capability.
- ACA dispatch is delayed until the exact immutable Job reaches authenticated
  `Succeeded` provisioning state.
- Bootstrap authenticates pending primary or scorer-retry attempts without
  rereading locked inputs or labels.
- Complete immutable predictions can be adopted without rerunning a parser.
- Any authenticated post-label attempt lacking one intact score transaction
  closes deterministically as `CLOSED/INVALID` without labels reread, scoring,
  parser invocation, or metric/decision acceptance.
- Score payloads are checked against both their manifest and the original
  scoring transaction, including coordinated payload/manifest/attestation
  replacement attempts.
- The launcher is restricted to a private Debian 12 VNet orchestrator with
  separate control-plane and runtime data identities. No such VM has been
  provisioned; explicit approval is still required before cost-bearing
  infrastructure creation.
- Focused locked-evaluation validation: `162 passed`.
- Complete repository validation: `759 passed, 2 warnings`.
- Python compilation, both Azure Bash syntax checks, `git diff --check`,
  changed-file credential scan, 10 MiB size gate, and frozen
  parser/gate/data-path checks passed.
- Four independent release audits are pending.
- No Azure command, image build, private holdout read, label read, parser
  evaluation, model load, GPU use, or scientific observation occurred in this
  tooling step.

## Authoritative Phase 0.5A result (2026-07-18)

- Target: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` at
  `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`.
- Official source:
  `anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`.
- Run ID: `20260718T184445Z`.
- Primary execution `job-jspace-p05-jlens-l7tipil` completed F0-F3 and failed
  F4 because official default-fp16 lens serialization did not preserve the
  fitted fp32 transport output.
- The sole authorized retry `job-jspace-p05-jlens-m1sazlr` restored and reused
  F2/F3, losslessly reserialized the exact lens as fp32, passed the unchanged
  F4 gate, and completed final manifest-last Blob persistence.
- Final decision: **GREEN / COMPLETE for bounded technical feasibility only**.
- F5 and actual 10-/25-prompt fits were not run; the scaling results are
  measured projections.
- No new formal behavioral observations or locked parser evaluation were
  produced. No hidden-reasoning, internal-workspace, or J-space claim is
  supported.
- Final model-free validation: `597 passed, 2 warnings`.

Detailed report: `reports/phase05_jlens_feasibility.md`.

## ACR Managed Identity Azure Execution (2026-07-08)

GHCR route was abandoned for execution because private package pull authentication remained blocked. The project switched to ACR with Azure AAD / user-assigned managed identity.

### ACR and Identity

- ACR: `acrjspaceobssea0708231738`
- Login server: `acrjspaceobssea0708231738.azurecr.io`
- Admin user enabled: `False`
- ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:359643b7b5eb`
- ACR build: succeeded via `az acr build`
- Managed identity: `id-jspace-aca-acrpull-sea`
- Principal ID: `78d4348b-57eb-4fb9-aaa7-99148b303292`
- AcrPull assigned: yes

### Azure Resources

- Resource group: `rg-jspace-observation-sea`
- Log Analytics workspace: `law-jspace-observation-sea`
- Container Apps environment: `cae-jspace-observation-sea`
- Workload profile: `gpu-t4` / `Consumption-GPU-NC8as-T4`
- Jobs:
  - `job-jspace-acr-smoke`
  - `job-jspace-phase05-acr`
  - `job-jspace-phase1-dryrun-acr`
  - `job-jspace-phase1-pilot-acr`

### Execution Results

- Smoke job: `Succeeded`
  - Execution: `job-jspace-acr-smoke-9b9wb4z`
  - Logs: `41 passed, 2 warnings`
- Phase 0.5 `--skip-fit`: `Succeeded`
  - Successful execution: `job-jspace-phase05-acr-i110lnu`
  - Both configured 1.5B models loaded successfully on Azure `Tesla T4`.
  - `jacobian-lens` not installed in the image.
  - Actual tiny fitting: not attempted.
  - Output path: `/workspace/results/runs/20260708_153600`
- Phase 1 dry-run: `Succeeded`
  - Execution: `job-jspace-phase1-dryrun-acr-v0j1bkd`
  - Total cells: 54
  - No real generation.
  - Output path: `/workspace/results/runs/20260708_154052`
- Small Phase 1 pilot: `Succeeded`
  - Execution: `job-jspace-phase1-pilot-acr-lhuvwbf`
  - Scope: DeepSeek-R1-Distill-Qwen-1.5B, arithmetic only, depths 1/2/3, three conditions, `--items-per-cell 1`, `--max-new-tokens 64`
  - Output path: `/workspace/results/runs/20260708_154330`

### Current caveats

- Blob persistence is now configured and has persisted the small Phase 1 pilot outputs.
- At this historical 2026-07-08 execution, Phase 0.5 did not include real
  fitting and its general-purpose ACR image lacked `jacobian-lens`. This was
  superseded by the dedicated pinned Phase 0.5A run recorded above.
- The small Phase 1 pilot is behavioral only and is not J-space evidence.
- Review exported logs/metrics before broadening the run.

## Persistent Storage Attempt (2026-07-09)

Goal: configure Azure Files persistence before broader Phase 1 runs.

### Result

- Azure Files persistence path is currently blocked.
- Both storage accounts created in this attempt have `allowSharedKeyAccess=False`, even when `--allow-shared-key-access true` was specified during creation.
- Azure Files data-plane operations with account key fail with:
  - `KeyBasedAuthenticationNotPermitted`
  - `Key based authentication is not permitted on this storage account.`

### Storage resources

- `stjspaceobssea07090835`: created, key-based auth disabled by policy
- `stjspacefiles0709085305`: created with explicit shared-key flag, but key-based auth still disabled by policy
- File share `jspace-results` was created through ARM management plane on the first storage account, but key-based Azure Files access remains unusable for Container Apps mount.

### Container Apps mount attempt

- Environment storage `jspace-results-storage` was registered, but the smoke job using `/mnt/results` hung.
- Stuck execution: `job-jspace-storage-smoke-acr-1s1g5d8`
- Cleanup completed:
  - stopped the stuck execution
  - deleted `job-jspace-storage-smoke-acr`
  - removed `jspace-results-storage` from the Container Apps environment
- No environment storage is currently registered.

### Script status

- `infra/azure/scripts/06_run_job_acr_mi.sh` now supports Azure Files volume mounting (`ENABLE_RESULTS_MOUNT`, `STORAGE_MOUNT_NAME`, `RESULTS_MOUNT_PATH`), but this should not be used until a working storage backend is available.

### Historical next blocker (resolved)

Choose a persistence alternative:

1. Ask the Azure/admin team to allow Azure Files shared-key access for this project; or
2. Switch to Azure Blob upload using managed identity from inside the container; or
3. Use identity-based Container Apps storage if supported in this tenant.

Resolved by switching to Azure Blob upload with managed identity; see the Blob persistence success section below.

## Blob Persistence Success (2026-07-09)

Azure Blob upload with managed identity is now the working persistence route.

### Storage and identity

- Storage account: `stjspacefiles0709085305`
- Blob container: `jspace-results`
- Shared key used: no
- `allowSharedKeyAccess`: `False`
- Managed identity: `id-jspace-aca-acrpull-sea`
- Managed identity role: `Storage Blob Data Contributor`

### Code/image

- Added `src/jspace_observation/blob_export.py`
- Added `scripts/blob_export_smoke.py`
- Added `azure-identity` and `azure-storage-blob`
- Added Blob export hooks to Phase 0.5 and Phase 1
- ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:afd647a6b53e`

### Blob smoke

- Job: `job-jspace-blob-smoke-acr`
- Successful execution: `job-jspace-blob-smoke-acr-o7kl7s2`
- Blob prefix: `smoke/20260709T013310Z`
- Verified file: `smoke/20260709T013310Z/smoke.txt`

### Persistent Phase 1 pilot

- Job: `job-jspace-phase1-pilot-blob-acr`
- Execution: `job-jspace-phase1-pilot-blob-acr-9voxpdm`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot/20260709T014336Z`
- Files uploaded:
  - `phase1_eval_records.jsonl`
  - `phase1_generations.jsonl`
  - `phase1_metrics.csv`
  - `phase1_summary.md`

### Pilot review

- Expected files present: yes
- Cells completed: 9
- Strict answer-only no-CoT validity is overestimated by current validator.
- Obvious bug: strict answer-only outputs can contain visible reasoning such as `Step-by-step explanation` and `follow these steps`, but the validator did not flag them.
- Numeric parser can be misled by truncated reasoning and last-number selection.
- Scientific conclusion: infrastructure + behavioral sanity only; no J-space claim.

### Next action

Fix no-CoT visible-reasoning validation before any broader Phase 1 run.

## Validator Hardening Success (2026-07-09)

The no-CoT validator and parser warning layer were hardened and rerun on the same minimal persistent Phase 1 pilot scope.

### Code changes

- `src/jspace_observation/no_cot.py`: stricter visible-reasoning detection and explicit no-CoT violation reasons.
- `src/jspace_observation/eval_parsing.py`: parser ambiguity and answer-format warning fields.
- `experiments/phase1_depth_gradient.py`: richer generation/eval records and metrics.
- Tests expanded for known false negatives and ambiguous parsing.

### Test result

- `python -m pytest tests/ -q` -> `54 passed, 2 warnings`

### New image and rerun

- ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:937288cfb8ef`
- ACR build run: `cm4`
- Digest: `sha256:c3dcbdd7360ff1f1462263446ee8865132dd854df3a29f4f57b8e7d6ae348094`
- Azure job: `job-jspace-p1-validator`
- Execution: `job-jspace-p1-validator-xkqro3f`
- Blob prefix: `phase1-pilot-validator/20260709T022001Z`
- Files: generation JSONL, eval JSONL, metrics CSV, summary MD

### Rerun pilot review

- Cells completed: 9.
- strict_answer_only no-CoT valid rate: `0.0000` for depths 1, 2, and 3.
- strict_answer_only visible reasoning marker rate: `1.0000` for depths 1, 2, and 3.
- parse_ambiguous_rate: `1.0000` for all 9 cells.
- answer_format_warning_rate: `1.0000` for all 9 cells.
- Summary warnings now explicitly report:
  - strict_answer_only no-CoT invalid count: `3/3`
  - strict_answer_only visible reasoning marker count: `3/3`
  - parse ambiguous count: `9/9`

### Current decision

- The known validator false negative is fixed.
- The pilot reveals that current strict-answer-only prompting/decoding still produces visible reasoning, so strict no-CoT-valid samples are absent in this tiny arithmetic pilot.
- Do not expand to broader Phase 1 until strict-answer-only prompting/decoding and parser policy are reviewed.
- Scientific conclusion remains infrastructure + behavioral sanity only; no J-space claim.

## Strict Answer-only Prompt/Decoding Rerun (2026-07-09)

### Changes

- Added `strict_answer_only_prefill_answer`.
- Tightened `strict_answer_only` prompt with explicit no-explanation/no-steps/no-reasoning instruction.
- Added strict condition decoding profiles:
  - `strict_answer_only`: `max_new_tokens=12`
  - `strict_answer_only_prefill_answer`: `max_new_tokens=8`
- Kept `visible_cot` and `r1_style_thinking` unchanged.
- Added `alright`, `hmm`, and `wait` as visible/meta-reasoning markers after the first strictfix rerun exposed them.

### Tests and image

- Tests: `62 passed, 2 warnings`
- Final ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:9b5895db173f`
- Build run: `cm6`
- Digest: `sha256:267e422baaad24b577ac103af9c9ca2af56295780eaa0804161aa4ff6d4fe189`

### Azure rerun

- First strictfix job: `job-jspace-p1-strictfix`, execution `job-jspace-p1-strictfix-sq17fi0`
- Final strictfix2 job: `job-jspace-p1-strictfix2`
- Final execution: `job-jspace-p1-strictfix2-1sjj2n5`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot-strictfix2/20260709T025356Z`

### Review

- Cells completed: 12.
- `strict_answer_only`: no-CoT valid rate `0.0000` for depths 1/2/3; visible reasoning marker rate `1.0000`.
- `strict_answer_only_prefill_answer`:
  - depth 1: no-CoT valid `1.0000`, visible reasoning marker `0.0000`, parse ambiguity `0.0000`, accuracy `0.0000`.
  - depths 2/3: still no-CoT invalid due meta-reasoning markers (`Alright`, `Wait`).
- `visible_cot` and `r1_style_thinking`: no-CoT validity reported as `NA`, not judged as strict no-CoT.

### Current decision

- Direct `Answer:` prefill improves visible-reasoning suppression on the easiest item but produces incomplete/wrong answers and still leaks meta-reasoning on harder items.
- Prompt-only strict no-CoT is still not established for this model/task setup.
- Do not expand Phase 1 yet.
- Next step should test a carefully labeled stop-sequence / post-processing experiment while preserving raw-output validation.
- Scientific conclusion remains infrastructure + behavioral sanity only; no J-space claim.

## Raw-vs-Postprocessed Answer-only Evaluation (2026-07-09)

### Main fix

- Added `strict_answer_only_postprocessed`.
- Raw output is preserved.
- Postprocessed output is stored separately.
- Raw no-CoT validity and postprocessed answer validity are reported separately.
- Postprocessing does not count as genuine raw no-CoT compliance.

### Code and tests

- Added `src/jspace_observation/postprocess.py`.
- Extended Phase 1 records and metrics with postprocessing fields.
- Tests: `68 passed, 2 warnings`.

### ACR image and job

- Final ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:9342ef130d46`
- Build run: `cm8`
- Digest: `sha256:3fc9e9d58b0ce6d5ea8a260cb7c172aa7cebfbe31427f94ee8cdae8d3b2a9ed1`
- Job: `job-jspace-p1-postprocess`
- Successful execution: `job-jspace-p1-postprocess-gor0o1r`
- Blob prefix: `phase1-pilot-postprocess/20260709T044224Z`
- Files: generation JSONL, eval JSONL, metrics CSV, summary MD

### Rerun review

- Cells completed: 12.
- `strict_answer_only_postprocessed` raw no-CoT valid rate: `0.0000` for all depths.
- `strict_answer_only_postprocessed` postprocessed no-CoT valid rate: `1.0000` for all depths.
- Postprocessing applied rate: `1.0000` for all depths.
- Postprocessing success rate:
  - depth 1: `1.0000`
  - depth 2: `0.0000`
  - depth 3: `1.0000`
- Accuracy postprocessed:
  - depth 1: `1.0000`
  - depth 2: `0.0000`
  - depth 3: `0.0000`

### Current decision

- Postprocessing can recover a clean correct answer in the easiest cell, but raw output still violates no-CoT.
- Postprocessing is useful as an answer-recovery analysis, not as evidence of no-CoT generation.
- Do not claim hidden reasoning or J-space evidence.
- Next step: decide whether to test stop-sequence generation controls or keep postprocessing as a separate answer-recovery analysis only.

## Private Blob Path + Stop-controlled Pilot (2026-07-10)

### Stop-control implementation

- Condition: `strict_answer_only_stopped`
- Code/image commit: `c29852ab97b5`
- Tests: `73 passed, 2 warnings`
- ACR build: `cm9`
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:c29852ab97b5`
- Digest: `sha256:2919bfa04dbcef0998cd9d770ffc91992958840d52ad512ab8b20b41dd434098`

The condition preserves:

- `raw_output_before_stop_cleanup`
- `raw_output`
- `stopped_output`
- raw, stopped, and postprocessed no-CoT validity separately
- stop trigger, string, reason, mode, and warning

### Private network

- VNet: `vnet-jspace-observation-sea`
- Active ACA subnet: `snet-aca-jspace-sea-v2` (`10.80.4.0/23`)
- Private endpoint subnet: `snet-pe-jspace-sea` (`10.80.2.0/27`)
- Blob private endpoint: `pe-stjspacefiles-blob-sea`
- Private endpoint state: `Succeeded` / `Approved`
- Private IP: `10.80.2.4`
- Private DNS zone: `privatelink.blob.core.windows.net`
- DNS link: `link-vnet-jspace-observation-sea-blob`
- Active environment: `cae-jspace-observation-sea-vnet2`
- Active environment state: `Succeeded`
- Workload profile: `gpu-t4` / `Consumption-GPU-NC8as-T4`

The first environment, `cae-jspace-observation-sea-vnet`, was created before the subscription feature `Microsoft.Network/AllowBringYourOwnPublicIpAddress` was registered. It reports `Succeeded` at the resource layer but cannot start containers. It was retained and is not the active environment.

### Blob network smoke

- Job: `job-jspace-blob-net-smoke-v2`
- Execution: `job-jspace-blob-net-smoke-v2-l02nljz`
- Status: `Succeeded`
- Prefix: `network-smoke-v2/20260710T071144Z`
- Uploaded: `smoke.txt`
- Authentication: user-assigned managed identity only
- Storage key/SAS/public network: not used

### Stop-control rerun

- Job: `job-jspace-p1-stopcontrol-vnet`
- Execution: `job-jspace-p1-stopcontrol-vnet-b55p4c6`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot-stopcontrol-vnet/20260710T072107Z`
- Files uploaded: 4
- Cells: 15

`strict_answer_only_stopped` results:

| Depth | Raw no-CoT valid | Stopped no-CoT valid | Stop triggered | Stop success | Accuracy stopped | Parse ambiguous |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| 2 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

Representative outputs:

- Depth 1 raw: `7 + 5 = \boxed{12}\n\n`; stopped: `7 + 5 = \boxed{12}`; correct.
- Depth 2 raw: `__________\n\n`; stopped: `__________`; parse failed.
- Depth 3 raw: `\boxed{12}\n\n`; stopped: `\boxed{12}`; parsed but wrong.

All three stops were triggered by `\n\n`. In this run, the generation-time criterion prevented any subsequent reasoning marker from being emitted, so raw and stopped no-CoT validity were both `1.0000`. This is still an intervention: stop-controlled validity does not establish spontaneous raw no-CoT reasoning.

### Current decision

- Do not expand the experiment yet.
- Treat raw strict, stopped, and postprocessed conditions as distinct branches.
- Stop control preserves answer quality only in the easiest cell and destroys or fails to recover useful answers at depths 2/3.
- No hidden-reasoning or J-space claim is supported.

## Phase 1 Branch Taxonomy and Reporting Semantics (2026-07-10)

Phase 1 answer-control conditions are now divided into three non-interchangeable branches:

| Branch | Canonical key | Conditions |
|---|---|---|
| Raw strict no-CoT feasibility | `raw_strict` | `strict_answer_only`, `strict_answer_only_prefill_answer` |
| Stop-controlled generation intervention | `stopped_intervention` | `strict_answer_only_stopped` |
| Postprocessed answer-recovery utility | `postprocessed_utility` | `strict_answer_only_postprocessed` |

Report/schema updates:

- Records include stable branch metadata.
- Raw, stopped, and postprocessed outputs, no-CoT validity, and correctness remain separate.
- Metrics CSV includes branch labels and branch-specific accuracy columns.
- Summaries include a branch-level table and use `NA` for non-applicable metrics.
- The legacy `accuracy` field follows `eval_output_used` and must not be used for cross-branch comparisons.

Interpretation boundaries:

- Stopped validity is generation-time intervention output, not spontaneous no-CoT.
- Postprocessed validity is extracted-surface validity, not raw no-CoT.
- No Phase 1 branch by itself is hidden-reasoning or J-space evidence.

Local validation:

```text
python -m pytest tests\ -q
80 passed, 2 warnings
```

Azure state:

- Rerun performed for this update: no.
- Active environment: `cae-jspace-observation-sea-vnet2`.
- Inactive retained environment: `cae-jspace-observation-sea-vnet`.
- Latest stop-control execution: `job-jspace-p1-stopcontrol-vnet-b55p4c6`.
- Active persisted result prefix: `phase1-pilot-stopcontrol-vnet/20260710T072107Z`.
- Private Blob network path: fixed and operational.

Current blocker: none.

## Phase 1 Branch-specific Success Criteria (2026-07-10)

The criteria in `docs/phase1_experiment_branches.md` are fixed before any new data collection:

| Branch | Passing classification | Core gate |
|---|---|---|
| `raw_strict` | `raw_strict_preliminarily_established` | `n >= 3`, surface/parsing/format gates, absolute accuracy `>= 0.50`, plus the relative gate when the visible-CoT baseline is valid. |
| `stopped_intervention` | `stopped_intervention_usable` | `n >= 3`, stopped validity, stop success, parse validity, absolute accuracy `>= 0.50`, plus the relative gate when the baseline is valid. |
| `postprocessed_utility` | `postprocessed_answer_recovery_usable` | `n >= 3`, validity/recovery/warning gates, non-degradation, and absolute accuracy `>= 0.50`. |

Report changes:

- Every reported branch result includes sample-size sufficiency and provisional status.
- Missing required metrics fail their criterion; non-applicable metrics remain `NA`.
- Visible-CoT relative gates require baseline `n >= 3`, parse-valid rate `>= 0.80`, and accuracy `> 0`; otherwise they are `NA`.
- Reports include criteria passed/failed/not-applicable, matching baseline fields, stop-trigger rate, stop-string distribution, and postprocessing warning/application rates.
- The mandatory warning states that classifications are behavioral and operational, not hidden-reasoning, internal-workspace, or J-space evidence.

Local validation:

```text
python -m pytest tests\ -q
109 passed, 2 warnings
```

Execution state:

- Historical fixed-scope Azure validation run performed: yes.
- Azure rerun for gate hardening: no.
- Local model inference for gate hardening: no.
- ACR rebuild for gate hardening: no.
- Active environment: `cae-jspace-observation-sea-vnet2`.
- Active Blob prefix: `phase1-pilot-criteria-validation/20260710T135655Z`.
- Current infrastructure blocker: none.

## Phase 1 Criteria-validation Pilot (2026-07-10)

Provenance:

- ACR build: `cma`.
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:f94e889ef608`.
- Digest: `sha256:f27cc0e4cea0ae9569dbb384598fb391f3b923022ce9257f8301684c9dc23806`.
- Job: `job-jspace-p1-criteria-val`.
- Execution: `job-jspace-p1-criteria-val-6s8p15p`.
- Status: `Succeeded`.
- Cells: `15`.
- Blob files: `4`.

Approved scope:

- One model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- One task family: `arithmetic`.
- Depths: `1,2,3`.
- Five conditions.
- Items per cell: `1`.
- No model, task, depth, or item-count expansion.

Classification result:

| Depth | Raw strict | Stopped intervention | Postprocessed utility |
|---|---|---|---|
| 1 | `surface_answer_only_but_task_failed` | `stopped_intervention_usable` | `postprocessed_answer_recovery_usable` |
| 2 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_warning_high` |
| 3 | `raw_strict_not_established` | `stopped_surface_compliant_but_task_failed` | `postprocessed_answer_recovery_usable` |

Key depth 1/2/3 metrics:

- Raw-strict `raw_no_cot_valid_rate`: `1.0000 / 0.0000 / 0.0000`.
- Raw-strict `accuracy_raw`: `0.0000 / 0.0000 / 0.0000`.
- Stopped `raw_no_cot_valid_rate`: `1.0000 / 1.0000 / 1.0000`.
- `stopped_no_cot_valid_rate`: `1.0000 / 1.0000 / 1.0000`.
- `stop_triggered_rate`: `1.0000 / 1.0000 / 1.0000`.
- `accuracy_stopped`: `1.0000 / 0.0000 / 0.0000`.
- Postprocessed `raw_no_cot_valid_rate`: `0.0000 / 0.0000 / 0.0000`.
- `postprocessed_no_cot_valid_rate`: `1.0000 / 1.0000 / 1.0000`.
- `postprocessing_success_rate`: `1.0000 / 0.0000 / 1.0000`.
- `postprocessing_warning_rate`: `0.0000 / 1.0000 / 0.0000`.
- `accuracy_postprocessed`: `1.0000 / 0.0000 / 0.0000`.

Validation outcome:

- The real summary includes branch classifications, criteria passed/failed, interpretation warnings, and stop-string distribution.
- The stop string distribution is `"\n\n"=1` at each stopped depth.
- Depth 3 postprocessed utility is mechanically usable because `accuracy_postprocessed >= accuracy_raw` is `0 >= 0`; this is not task success.
- The depth 3 raw relative-accuracy criterion also passes against a zero visible-CoT baseline, while raw surface criteria correctly fail.
- These limitations require a prospective criteria decision before another run; this run is not reclassified.
- Results are behavioral and operational only.
- Stop-controlled validity is not spontaneous no-CoT.
- Postprocessed validity is not raw no-CoT.
- No hidden-reasoning, internal-workspace, or J-space claim is supported.

## Phase 1 Branch-gate Hardening (2026-07-10)

Prospective rules:

- Formal success labels require `n >= 3`; otherwise an otherwise-passing result becomes `raw_strict_pilot_only`, `stopped_intervention_pilot_only`, or `postprocessed_utility_pilot_only`.
- Explicit metric failures retain failure labels below the minimum sample size.
- Raw and stopped branches always require absolute accuracy `>= 0.50`.
- Their relative gate is applied only when matching visible-CoT `n >= 3`, parse-valid rate `>= 0.80`, and accuracy `> 0`; otherwise it is `NA`.
- Postprocessed utility requires non-degradation and `accuracy_postprocessed >= 0.50`.
- Postprocessed visible-CoT comparison is report-only.

Historical regression interpretation:

- The completed Blob summary remains unchanged under the earlier criteria.
- Depth-1 stopped and postprocessed rows would now be `pilot_only` because `n=1`.
- The depth-3 postprocessed `0 >= 0` case now becomes `postprocessed_surface_clean_but_task_failed`.
- The pilot's matching visible-CoT rows have `n=1`, so relative gates are unavailable rather than passed.

No Azure job, model inference, model download, ACR rebuild, or scale increase occurred during hardening. Results remain behavioral and operational only. Stopped output remains intervention-controlled, postprocessed output remains distinct from raw no-CoT, and no hidden-reasoning or J-space claim is supported.

## Bounded Phase 1 n=3 Validation (2026-07-10)

Scope and provenance:

- Starting commit: `d1750a9d51e102c644933d8c41b7d65432f8bdfa`.
- Source commit: `359643b7b5eb8f95c13cca2e60fa753df8701282`.
- Tests: `111 passed, 2 warnings`.
- Dry-run: `configuration_cells=15`, `items_per_cell=3`, `total_observations=45`.
- ACR build: `cmb`.
- Image digest: `sha256:004ec8bff66fbc8a23b122660aeb58914b2ee3cedfc5246429046eef252c9069`.
- Job: `job-jspace-p1-n3-gates`.
- Sole execution: `job-jspace-p1-n3-gates-02ilmgm`; status `Succeeded`; retries `0`.
- Blob prefix: `phase1-limited-n3-gates/20260710T152820Z`.
- Artifacts: four files; 45 generation records, 45 eval records, 15 metric rows, every row `n=3`.

Visible-CoT baseline:

| Depth | n | Accuracy | Parse valid | Baseline valid | Failure reason |
|---|---:|---:|---:|---|---|
| 1 | 3 | 0.3333 | 1.0000 | true | `NA` |
| 2 | 3 | 0.6667 | 1.0000 | true | `NA` |
| 3 | 3 | 0.0000 | 1.0000 | false | `visible_cot_accuracy_zero` |

Branch classifications:

| Depth | Raw strict | Stopped intervention | Postprocessed utility |
|---|---|---|---|
| 1 | `raw_strict_not_established` | `stopped_intervention_usable` | `postprocessed_answer_recovery_usable` |
| 2 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_task_failed` |
| 3 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_task_failed` |

Key interpretation:

- All nine rows meet the registered sample-count gate; this means registered-gate sufficiency only, not statistical stability.
- Raw strict was not established at any depth.
- Stopped depth-1 usability is intervention utility; it is not spontaneous no-CoT.
- Postprocessed depth-1 usability is answer-recovery utility; it is not raw no-CoT.
- Depth-3 postprocessed non-degradation is `0 >= 0`, but absolute accuracy fails, so it is not usable.
- Depth-3 relative gates are `NA`, not passed or failed.
- Classification audit independently recomputed all nine rows with zero mismatches.
- Count/aggregate audits passed. The subsequent private-path record audit found zero duplicate, missing, membership, common-field, transformation, parser, metric, or classification mismatches.
- No hidden-reasoning, internal-workspace, genuine invisible-reasoning, or J-space claim is supported.

This decision was superseded by the completed all-45 semantic audit below.

## Phase 1 All-45 Semantic Parser Audit (2026-07-15)

The preregistered two-stage blinded review of all 45 historical arithmetic
records from `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` is complete.

Provenance:

```text
protocol/tooling commit: cfa99fc6e204db5cf1076a13a8975e13db226931
source writer commit: 359643b7b5eb8f95c13cca2e60fa753df8701282
source prefix: phase1-limited-n3-gates/20260710T152820Z
semantic parent prefix: phase1-semantic-audits/all45-parser-underflag-20260715T094500Z
image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:cfa99fc6e204
digest: sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac
environment/profile: cae-jspace-observation-sea-vnet2 / Consumption
resources/GPU: 2 CPU / 4Gi / none
```

Review completion:

- Two independent `gpt-5.6-sol/max` reviewers completed 45 Stage-1 and 45
  Stage-2 rows each.
- Four records (`R002`, `R009`, `R018`, `R022`) required blinded arbitration
  by a distinct `gpt-5.6-sol/max` arbiter.
- Final unresolved count is zero.
- Semantic category, presence, and status exact agreement were `0.9556`,
  `0.9778`, and `0.9778`.

Audit-only result:

- true multiple-candidate ambiguity: `0`;
- parser overflags: `18`, all in visible-reasoning conditions;
- parser underflags: `0`;
- observed extraction errors: `14`;
- material correctness errors: `2` (`R019`, `R038`, both `visible_cot`
  depth 1);
- material evaluator issues: `19`;
- official stored metrics/classifications modified: no.

The audit-only `visible_cot` depth-1 accuracy is `1.0000`, versus stored
`0.3333`. The audit-only depth-2 visible-CoT parse-valid rate is `0.6667`, so
that baseline becomes invalid and associated relative gates become `NA`.
Four baseline/gate fields change, but none of the nine final branch
classification labels changes.

Decision: preregistered **Path C**. Higher-n replication remains paused.
The next action is a locked evaluator validation set and prospective parser-v2
protocol before any new model run. No parser or historical artifact was
changed.

Detailed report: `reports/phase1_n3_all45_semantic_audit.md`.

Persistent outputs:

```text
final machine prefix:
phase1-semantic-audits/all45-parser-underflag-20260715T094500Z/final

machine upload execution:
job-jspace-p1-all45-pack-vi79nml

report prefix:
phase1-semantic-audits/all45-parser-underflag-20260715T094500Z/report

report upload execution:
job-jspace-p1-all45-pack-61s3ggf
```

Both executions succeeded through the private managed-identity path. The nine
machine artifacts used exact membership, manifest-last upload, and per-file
download/hash verification. The report was kept outside that membership and
was independently downloaded and hash-verified. All five independent post-run
checks passed. The transport secret was removed and the job is idle.

## Path C Phase 1.2A Evaluator Validation Set (2026-07-16)

Phase 1.2A preregistered, constructed, independently labeled, validated, and
privately sealed the prospective parser-v2 evaluator set.

Frozen provenance:

```text
starting commit: 58d299bb66c5536a0f1b7d0617204472fbb8c212
final protocol commit: cc93ffe603ab8338ed860586a52b1911af4b3277
tooling/development commit: e7a95a458d05d4ef211bb6902c2a20cb5f16bf60
sealed no-Git validation commit: 9b4262a9d35e6342935b8d2f72887a56c5f98486
protocol bundle: 5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666
acceptance gates: a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988
```

Dataset:

- Development: 60, exactly five per S01-S12.
- Locked: 120, exactly ten per S01-S12.
- Locked support: 80 present, 10 ambiguous, 30 no answer.
- Locked critical/material cases: 80/68.
- Exact, normalized, cross-set template, and historical hard overlaps: zero.
- Reviewed near-duplicate findings: 37, all dispositioned.
- Public development SHA-256:
  `bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27`.

Independent labeling:

- Stage-1 A/B: 120/120 each, reference-blind.
- Stage-1 arbitration: 57; Stage-2 arbitration: 0.
- Stage-2 A/B correctness agreement: 120/120, kappa 1.
- Final labels: 120; unresolved: 0.
- Seven review seals validate.
- Labels are LLM operational consensus references, not human ground truth.

Private release:

```text
parent: phase1-evaluator-validation/parser-v2-v1/20260716T024856Z
artifacts: 26
final labels: 44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af
locked-label manifest: aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6
overall manifest: f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260
validation report: 5b3daf44553a7c99d57c8d5a117ef82de113c4b5cde74ef13dd218c11c56b641
```

Azure persistence:

- ACR build `cmf` failed safely against the frozen all-45 Docker attestation;
  no image, execution, or Blob write resulted.
- Encrypted overlay build `cmg` used immutable base digest
  `sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac`.
- The sole CPU execution, `job-jspace-parser-v2-set-ib7uc0e`, succeeded in
  `cae-jspace-observation-sea-vnet2` on Consumption with 2 CPU / 4 GiB and no
  GPU.
- Managed identity, private Blob, `overwrite=false`, reservation-first,
  manifest-last, exact 26-object membership, and per-object re-download
  verification were enforced.
- The job is reset to the immutable base with `/bin/true`; secrets and secret
  references are zero.
- The temporary transport tag/digest and local encrypted build context were
  deleted.

All five independent post-sealing reviews passed. Final model-free tests:
`460 passed, 2 warnings`.

The holdout is `SEALED`, not evaluated. At sealing time parser v2 was not
implemented; it was subsequently developed from only the public set. Locked
inputs have not been exposed for evaluation, and no acceptance-gate result
exists. No target-model download/load/inference, higher-n run, new behavioral
evidence, hidden-reasoning claim, or J-space claim occurred during sealing.

Detailed report: `reports/phase1_parser_v2_validation_set.md`.

## Phase 1 n=3 Record-Level Artifact Audit (2026-07-11)

Provenance:

```text
starting commit: a4bbf8911e0f758eb10230e52c6e953ef8df9cee
audit implementation commit: 9537ed8e0b5da95b68714b73fa11236b48ee046a
tests: 139 passed, 2 warnings
ACR build: cmc
image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:9537ed8e0b5d
digest: sha256:90adfc1b6be6fbb7a17a878bed7970ffd71c62b72263a36b41110ba6f19b169b
environment/profile: cae-jspace-observation-sea-vnet2 / Consumption
job: job-jspace-p1-record-audit
execution: job-jspace-p1-record-audit-d9q5uy8
status: Succeeded
GPU used: no
model inference: no
new observations: no
```

Source and output:

```text
source: phase1-limited-n3-gates/20260710T152820Z
audit output: phase1-audits/n3-gates-20260710T152820Z/20260711T010339Z
source modified: no
audit files uploaded: 8
```

Deterministic result:

- 45/45 generation records and 45/45 eval records are valid JSONL.
- Composite key: `model_name, task_family, depth, condition, task_id`.
- 45 unique keys per side; zero duplicates or one-sided keys.
- All 15 cells contain exactly three registered, unique items.
- Registered answers, common fields, selected-output transformations, parser
  replay, and correctness aliases have zero mismatches.
- All 15 metric rows match with maximum absolute difference `0.0`.
- All nine branch classifications and criteria lists match.
- Depth-3 postprocessed `0 >= 0` remains task-failed because the absolute floor
  fails.
- Before/after source Blob properties are unchanged.

Ambiguous-parse review:

- Two independent `gpt-5.6-sol/max` reviewers audited all 18 flagged records.
- Exact category agreement: `17/18`; Cohen's kappa: `0.6471`.
- Any field-level disagreement triggered arbitration: `14` records.
- Arbiter unresolved records: `0`.
- Final audit opinion: `17` parser overflags and `1` true multiple-candidate
  ambiguity.
- Final answer statuses: `6` correct, `1` incorrect, `1` ambiguous, and `10`
  with no answer.
- Stored parser/correctness fields are mechanically consistent for all 18.
  Records 2 and 3 expose semantic answer-extraction limitations rather than
  artifact corruption.
- Reviewing only flagged records cannot rule out underflags among the other 27.

Detailed report: `reports/phase1_n3_record_audit.md`.

## GHCR Workflow Run + T4 Quota Findings (2026-07-08 22:00 +08:00)

- Baseline: read `docs/thread_handoff.md`; repo was synced to `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Workflow file installed: `.github/workflows/build-ghcr.yml` exists and matches `infra/ci/build-ghcr.yml`.
- Installation note: the local `gh` token still lacks GitHub `workflow` OAuth scope, but the workflow was successfully installed through the GitHub connector / GitHub App path in commit `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Workflow trigger: `gh workflow run build-ghcr.yml -R Alanjiao1988/J-space-observation --ref main -f push_latest=true`.
- Workflow run: `28947916765`, completed successfully.
- Workflow URL: `https://github.com/Alanjiao1988/J-space-observation/actions/runs/28947916765`
- GHCR image pushed:
  - `ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66`
  - `ghcr.io/alanjiao1988/j-space-observation:latest`
- Package API note: current `gh` token lacks `read:packages`, so package version API checks return 403; the workflow logs confirm both image tags were pushed.
- Diff from image commit `c07db5c...` to latest repo commit `c10afdd...`: documentation-only (`docs/*.md`, `reports/current_status.md`); image rebuild not required.
- Providers: `Microsoft.App` = `Registered`, `Microsoft.ContainerRegistry` = `Registered`, `Microsoft.Quota` = `Registered`.
- Azure resource check: no `jspace` / `j-space` resource groups found.
- T4 GPU workload profile type availability: `Consumption-GPU-NC8as-T4` is offered in `southeastasia`.
- `az quota list` and `az quota usage list` for `Microsoft.App` / `southeastasia` returned `ManagedEnvironmentCount`, `SessionPools`, `SubscriptionDedicatedNCA100Gpus`, and `ExpressEnvironmentCount`, but did **not** expose a T4 / NC8as-T4 / Managed Environment Consumption T4 quota item.
- **T4 GPU quota (subscription): still unknown via CLI.** Use Azure Portal Usage + quotas or Azure support to confirm/request Container Apps Managed Environment Consumption T4 GPUs in `southeastasia`.
- Azure resources created: none.

### Remaining blocker

1. Confirm Container Apps **T4 GPU quota in southeastasia** via Azure Portal (Usage + quotas) or Azure support. CLI quota query did not expose the required T4 quota item.

## Azure GHCR Smoke Path Attempt (2026-07-08)

Alan explicitly approved minimal Azure resource creation to validate the deployment path instead of continuing to block on invisible quota.

### Resources Created

- Resource group: `rg-jspace-observation-sea` (`southeastasia`)
- Log Analytics workspace: `law-jspace-observation-sea`
- Container Apps environment: `cae-jspace-observation-sea`
- Workload profile: `gpu-t4` (`Consumption-GPU-NC8as-T4`)
- Jobs: none created successfully

### T4 / Quota Validation

- `Consumption-GPU-NC8as-T4` workload profile creation succeeded.
- No quota error occurred during environment/profile creation.
- GPU job execution has not yet succeeded, because GHCR image pull was blocked before job creation.

### Errors Encountered

1. Container Apps environment with `--enable-dedicated-gpu true` failed:
   - Error code: `WorkloadProfileInvalidType`
   - Message: `Workload profile type 'NC24_A100' is invalid.`
   - Fix: create environment without `--enable-dedicated-gpu true`.
2. Adding T4 profile with `--min-nodes/--max-nodes` failed:
   - Error code: `WorkloadProfilePropertyNotSupported`
   - Message: `Workload Profile property 'MinimumCount' is not supported for CONSUMPTION_GPU_NC8AS_T4`
   - Fix: omit min/max for the consumption GPU profile.
3. GHCR smoke job creation failed before execution:
   - Error code: `InvalidParameterValueInContainerTemplate`
   - Message includes: `UNAUTHORIZED: authentication required`
   - Classification: GHCR private package / registry authentication required

### Current Blocker

Azure Container Apps cannot pull the GHCR image anonymously. Next step is one of:

1. Make the GHCR package public; or
2. Provide GHCR credentials through a secure path (`GHCR_USERNAME` + `GHCR_PAT` with minimal `read:packages`), then create the registry secret / rerun `job-jspace-ghcr-smoke`.

Do not send token values in chat and do not commit them.

### GHCR Auth Retry Result

- `GHCR_PAT`: not set.
- `GHCR_USERNAME`: defaulted to `Alanjiao1988`.
- `gh auth token`: available and used as an Azure registry secret for a retry (token value not printed/logged).
- Job creation still failed:
  - Error code: `InvalidParameterValueInContainerTemplate`
  - Message includes: `DENIED: requested access to the resource is denied`
  - Classification: available `gh auth token` is insufficient for Azure to pull the private GHCR image.
- Jobs created successfully: none.
- Phase 0.5 / Phase 1 dry-run / small pilot: not attempted.

Current actionable options:

1. Make the GHCR package public; or
2. Provide a classic PAT with `read:packages` through a secure local environment variable (`GHCR_PAT`) or an approved Azure secret path. Do not send the token in chat.

### GHCR Auth Preflight Update

- `GHCR_PAT` is still not set.
- Current `gh auth token` was tested against the GHCR package versions API.
- Result: `403` with message `You need at least read:packages scope to get a package's versions.`
- Decision: do not retry Azure job creation with the known-insufficient token.
- No new Azure resources were created in this step.

### GHCR_PAT Visibility Update

- Alan set `GHCR_USERNAME` / `GHCR_PAT` in a local PowerShell shell, but the Copilot tool process could not see them.
- Checked Process/User/Machine environment scopes:
  - `GHCR_USERNAME`: not visible
  - `GHCR_PAT`: not visible
- No package-read preflight or Azure job retry was attempted in this step.
- Existing Azure resources remain unchanged.

To retry, set the variables in Windows User environment (not only shell-local), then start a new request:

```powershell
[Environment]::SetEnvironmentVariable("GHCR_USERNAME", "Alanjiao1988", "User")
[Environment]::SetEnvironmentVariable("GHCR_PAT", "<classic PAT with read:packages>", "User")
```

Do not paste the token into chat.

### GHCR_PAT Visibility Retry

- Alan reported setting `GHCR_USERNAME` / `GHCR_PAT` as Windows User environment variables and restarting VS Code / Copilot agent / terminal.
- Copilot re-checked Process/User/Machine environment scopes.
- `GHCR_USERNAME`: still not visible.
- `GHCR_PAT`: still not visible.
- GHCR package-read preflight was not run because no PAT was visible.
- Azure smoke job was not retried.
- Existing Azure resources remain unchanged.

Current blocker remains: the agent process cannot read a valid `GHCR_PAT`. Next action is to provide a secure token path visible to the agent or make the GHCR package public.

### Script Update

`infra/azure/scripts/05_run_job_ghcr.sh` has been updated to match the actual Azure resource names and the live CLI findings:

- defaults now use `rg-jspace-observation-sea`, `cae-jspace-observation-sea`, and `job-jspace-ghcr-smoke`;
- removed `--enable-dedicated-gpu true` from environment creation;
- removed `--min-nodes/--max-nodes` from the T4 workload profile add command;
- uses ARM REST job creation/update to avoid Azure CLI `--args -lc ...` parsing issues;
- places `workloadProfileName` at `properties.workloadProfileName`, which is the schema position validated by live Azure errors;
- falls back to `gh auth token` only when `GHCR_PAT` is absent;
- supports Alan's requested env var aliases: `JOB_NAME`, `CONTAINERAPPS_ENVIRONMENT`, and `WORKLOAD_PROFILE_NAME`;
- no longer passes the GHCR token as a Python command-line argument while generating the ARM body;
- added project tags to resources created by the script.

## GHCR + T4 Quota Path Status (2026-07-08 21:34 +08:00)

- Read-only provider re-check: `Microsoft.ContainerRegistry` = `Registered`, `Microsoft.App` = `Registered`.
- **Decision locked:** GHCR is the **primary** registry path; ACR is a **secondary fallback** only (used if GHCR fails). Rationale: git-SHA image provenance, GitHub-hosted builds, and decoupling from ACR provider timing.
- GHCR workflow template `infra/ci/build-ghcr.yml`: **valid**.
- GHCR Azure job script `infra/azure/scripts/05_run_job_ghcr.sh`: **valid** (parameterized; `JOB_COMMAND` override).
- Runbook now includes a gated **Planned Azure command sequence**: T4 quota -> resource group -> Container Apps env + GPU profile -> GHCR image smoke test -> Phase 0.5 `--skip-fit` -> Phase 1 `--dry-run` -> small Phase 1 pilot.
- GHCR workflow installed and run successfully.
- Next Azure gate: **confirm T4 GPU quota in southeastasia**.
- Local checks: `41 passed, 2 warnings`; Phase 1 dry-run `54` cells.
- Azure resources created: **none**.

### Next step

Confirm Azure Container Apps **T4 GPU quota for southeastasia** before any GPU job (portal, support request, or approved `Microsoft.Quota` registration and read-only quota query).

## Azure-first Policy (2026-07-08)

- Local validation is complete.
- Local PC is now limited to orchestration, tests, dry-runs, documentation, Git, and Azure CLI commands.
- Heavy execution must run on Azure GPU containers:
  - model download
  - model loading
  - Phase 0.5 fitting / model loading
  - Phase 1 real generation
  - later J-lens, patching, and ablation experiments
- Do not run real Phase 1, model downloads, or J-lens fitting locally.
- Do not silently fall back to local inference if Azure is blocked.

## Azure Readiness Status (2026-07-08)

- Azure CLI: available (`2.83.0`).
- Active subscription: `MCAPS-Hybrid-REQ-125620-2025-alanjiao`.
- Subscription state: `Enabled`.
- Microsoft.App provider: `Registered`.
- Microsoft.ContainerRegistry provider: `Registered`.
- containerapp extension: installed (`1.3.0b4`).
- Azure resources created: none.
- Azure scripts are prepared for:
  - no-resource readiness checks;
  - ACR build/push;
  - Phase 0.5 Azure availability/model-loading job;
  - Phase 1 Azure dry-run job;
  - small real Phase 1 pilot job.

## Azure Blockers Before Execution

- Verify Azure Container Apps GPU T4 quota for `southeastasia` and workload profile `Consumption-GPU-NC8as-T4`.
- Do not run real inference or model loading locally as a fallback.

## Historical Azure Readiness Gate Re-check (2026-07-08; superseded)

- Microsoft.ContainerRegistry: `Registering`.
- Microsoft.App: `Registered`.
- T4 GPU quota status: not checked because `Microsoft.ContainerRegistry` is still not `Registered`.
- Readiness script: not run.
- Azure resources created: none.
- Current status has superseded this: `Microsoft.ContainerRegistry` is now `Registered`.

## Historical Azure Provider Gate Re-check (2026-07-08 18:39 +08:00; superseded)

- Microsoft.ContainerRegistry: `Registering`.
- Microsoft.App: `Registered`.
- T4 GPU quota status: not checked because the provider gate remains blocked.
- Readiness script: not run.
- Azure resources created: none.
- Current status has superseded this: `Microsoft.ContainerRegistry` is now `Registered`.

## Historical Azure Provider Gate Re-check (2026-07-08 18:41 +08:00; superseded)

- Microsoft.ContainerRegistry: `Registering`.
- Microsoft.App: `Registered`.
- T4 GPU quota status: not checked because the provider gate remains blocked.
- Readiness script: not run.
- Azure resources created: none.
- Current status has superseded this: `Microsoft.ContainerRegistry` is now `Registered`.

## Next Command

After `Microsoft.ContainerRegistry` is registered and GPU quota is confirmed:

```powershell
.\infra\azure\scripts\00_check_prereqs.ps1
```

or:

```bash
bash infra/azure/scripts/00_check_prereqs.sh
```

## Latest Local Validation (2026-07-08)

### Validation Results

- Repository state: `main` synced with `origin/main` before validation.
- Tests: `python -m pytest tests/ -v` -> `41 passed, 2 warnings`.
- Phase 0.5 availability/model-loading check: completed.
  - Output directory: `results/runs/20260708_181325`
  - Summary: `results/runs/20260708_181325/phase0_5_summary.md`
  - Pre-fitted lenses found locally/configured: no.
  - jacobian-lens installed/importable: no / no.
  - Model loading attempted: yes.
  - Model loading succeeded: no. Both configured models failed because `accelerate` is required for `device_map`.
  - Actual tiny J-lens fitting attempted: no.
  - Actual tiny J-lens fitting success: not attempted.
- Phase 1 dry run: completed.
  - Conditions included `strict_answer_only`, `visible_cot`, and `r1_style_thinking`.
  - Total cells: 54.
  - No model download or generation was performed by the dry run.
- Azure resources created: none.

## Local Environment Validation (2026-07-08)

### Environment Results

- Active Python executable: `C:\Users\alanjiao\AppData\Local\Programs\Python\Python313\python.exe`
- Core dependencies installed/importable: yes.
- `accelerate` is now installed/importable.
- External jacobian-lens install path: `C:\Users\alanjiao\external\jacobian-lens`
- jacobian-lens import result: yes, via `import jlens`.
- The project J-lens helper now recognizes the installed `jlens` module.

### Re-run Results

- Tests: `python -m pytest tests/ -v` -> `41 passed, 2 warnings`.
- Phase 0.5 availability/model-loading check:
  - Output directory: `results/runs/20260708_182022`
  - Summary: `results/runs/20260708_182022/phase0_5_summary.md`
  - Pre-fitted lenses found locally/configured: no.
  - jacobian-lens installed/importable: yes / yes.
  - Model loading succeeded for both configured models on CPU.
  - Actual tiny J-lens fitting attempted: no.
  - Actual tiny J-lens fitting success: not attempted.
- Phase 1 dry run:
  - Completed successfully.
  - Conditions included `strict_answer_only`, `visible_cot`, and `r1_style_thinking`.
  - Total cells: 54.
  - No generation was performed by dry run.
- Azure resources created: none.

### Blockers

- Real tiny J-lens fitting has not been attempted yet.
- No pre-fitted lenses were found locally/configured.
- Models load on CPU locally; real generation may be slow without GPU.

### Previous Local Pilot Command (superseded by Azure-first policy)

The equivalent small real Phase 1 pilot must be run via Azure, not locally:

```bash
bash infra/azure/scripts/04_run_phase1_pilot.sh
```

## What Has Been Implemented

### Core Python Modules

1. **config.py** - Configuration classes for models and experiments
   - `ModelConfig`: dtype, device_map, output_hidden_states
   - `NoCoTConfig`: Generation parameters and validation thresholds
   - `ExperimentConfig`: Directory management

2. **model_loader.py** - Hugging Face model loading
   - Loads models with proper dtype and device handling
   - Collects model info (layers, hidden size, GPU info)
   - Provides logging utilities

3. **no_cot.py** - Strict no-CoT prompt utilities
   - `construct_empty_think_prefill_prompt()`: For R1-Distill
   - `construct_answer_only_prompt()`: For other models
   - `validate_no_cot_output()`: Checks for think tags and reasoning
   - `create_generation_record()`: Structured record creation

4. **prompt_sets.py** - Pilot prompt datasets
   - ArithmeticPromptSet: 1-op, 2-op, 3-op tasks
   - SyntheticRelationPromptSet: 1-hop, 2-hop, 3-hop tasks
   - FactualCounterfactualPromptSet: Factual and counterfactual reasoning
   - ~15 total pilot items (scales to 50-100 in production)

5. **eval_parsing.py** - Answer evaluation
   - `parse_numeric_answer()`: Numbers including negatives and floats
   - `parse_entity_answer()`: Short string answers
   - `parse_yes_no_answer()`: Boolean questions
   - `evaluate_answer()`: Correctness scoring with numeric tolerance

6. **stats.py** - Statistical utilities
   - `wilson_ci()`: Confidence intervals for rates
   - `bootstrap_ci()`: Confidence intervals for continuous metrics
   - `compute_slope()`: Linear regression for depth gradients
   - `cot_gain_by_depth()`: CoT gain analysis

7. **run_logging.py** - Experiment tracking
   - `RunLogger`: Timestamped run directory creation
   - `SummaryBuilder`: Markdown summary generation
   - `create_run_metadata()`: Metadata JSON generation
   - `record_resource_usage()`: Wall-clock time and GPU memory

8. **jlens_utils.py** - J-lens utilities
   - `check_jacobian_lens_installed()`: Package availability
   - `check_prefitted_lens_locally()`: Pre-fitted lens search
   - `JacobianLensWrapper`: Unified interface

### Experiment Scripts

1. **experiments/phase0_5_jlens_spike.py**
   - Searches for pre-fitted J-lenses locally and online
   - Checks jacobian-lens package availability
   - Plans cost sweeps (prompt counts, sequence lengths, layer modes)
   - Validates model loading
   - Outputs: metadata.json, sweep configs, summary.md
   - Usage: `python experiments/phase0_5_jlens_spike.py --skip-fit`

2. **experiments/phase1_depth_gradient.py**
   - Runs generation experiments across models, tasks, depths, and conditions
   - Supports conditions: strict_answer_only, visible_cot, r1_style_thinking
   - Parses and evaluates answers
   - Computes accuracy, parse validity, no-CoT validity, latency
   - Outputs: generation records (JSONL), eval records (JSONL), metrics (CSV), summary (MD)
   - Usage: `python experiments/phase1_depth_gradient.py --items-per-cell 3`

### Unit Tests

All tests pass without requiring model downloads:

- **test_no_cot.py** (9 tests)
  - Prompt construction
  - No-CoT validation
  - Think tag detection
  - Visible reasoning detection
  - Token budget checking
  - Answer extraction

- **test_eval_parsing.py** (18 tests)
  - Numeric parsing (simple, negative, float, multiple)
  - Entity parsing
  - Yes/no parsing
  - Answer evaluation with tolerance

- **test_stats.py** (13 tests)
  - Wilson confidence intervals
  - Bootstrap CI
  - Slope computation
  - CoT gain calculation

### Azure Infrastructure

1. **infra/azure/scripts/00_check_prereqs.sh**
   - Verifies Azure CLI, Docker, Python packages
   - Checks Azure login and resource group
   - Creates resource group if needed

2. **infra/azure/scripts/01_build_and_push_image.sh**
   - Builds Docker image
   - Creates ACR if needed
   - Pushes to Azure Container Registry

3. **infra/azure/scripts/02_run_phase0_5.sh**
   - Submits Phase 0.5 job to Azure Container Instances
   - Logs to run_log.md

4. **infra/azure/scripts/03_run_phase1.sh**
   - Submits Phase 1 job to Azure Container Instances
   - Logs to run_log.md

### Build Automation

- **Makefile** with targets:
  - `make install`: Install project dependencies
  - `make test`: Run unit tests
  - `make phase0-5`: Run Phase 0.5 locally
  - `make phase1`: Run Phase 1 locally
  - `make phase1-dry`: Dry-run Phase 1
  - `make azure-setup`: Setup Azure infrastructure
  - `make azure-phase0-5`: Submit Phase 0.5 to Azure
  - `make azure-phase1`: Submit Phase 1 to Azure

## How to Run

### Setup (one-time)

```bash
cd J-space-observation
make install
```

### Run Tests

```bash
make test
```

### Run Phase 0.5 (J-lens feasibility spike)

```bash
make phase0-5
```

Output:
- `results/runs/<timestamp>/phase0_5_summary.md`
- `results/runs/<timestamp>/phase0_5_sweep_configs.json`
- `results/runs/<timestamp>/metadata.json`

### Run Phase 1 (behavioral depth gradient) - Dry Run

```bash
make phase1-dry
```

### Run Phase 1 (behavioral depth gradient) - Full

```bash
make phase1
```

Output:
- `results/runs/<timestamp>/phase1_generations.jsonl`
- `results/runs/<timestamp>/phase1_eval_records.jsonl`
- `results/runs/<timestamp>/phase1_metrics.csv`
- `results/runs/<timestamp>/phase1_summary.md`

### Run on Azure

```bash
make azure-setup
make azure-phase0-5
make azure-phase1
```

## Key Design Decisions

### No-CoT Implementation

- **For R1-Distill**: Uses empty-think prefill
  ```
  [question]

  <think>
  </think>

  Answer:
  ```
  This keeps the model in distribution while closing the thinking block before final answer generation.

- **For Qwen2.5-Math**: Uses standard answer-only prompts
  No empty-think tag needed since this model doesn't have <think> training.

### Validation Rules

- A generation is marked `no_cot_valid=true` only if:
  - No generated <think> tags with content
  - No visible reasoning keywords (step, then, therefore, etc.)
  - Output is within token budget

### Pilot Dataset Scope

- Small enough for rapid iteration (~15 items)
- Structured to scale to 50-100 items per task family
- Covers three task families:
  - Arithmetic (1-3 ops)
  - Synthetic relations (1-3 hops, facts in prompt)
  - Factual/counterfactual (1-2 hops)

### Historical J-lens availability scaffold (superseded)

The original `experiments/phase0_5_jlens_spike.py` checked package/model
availability and did not perform fitting. The dedicated pinned runner
`scripts/phase05_jlens_feasibility.py` subsequently completed the bounded real
Jacobian run described in the authoritative 2026-07-18 section. The resulting
GREEN status is technical feasibility only, not Plan A scientific validation.

## What Remains

### Before Production Experiments

1. **Post-Phase-0.5 decision**
   - Phase 0.5A bounded technical feasibility is complete.
   - Any larger fit or scientific lens validation requires a new registered
     design and explicit authorization.
   - Actual 10-/25-prompt fitting was not performed.

2. **Phase 1.5: Layer Taxonomy**
   - Empirically identify sensory/workspace/motor layers
   - Prerequisite for Phase 2 J-lens readout

### For Full J-space Observation (Plan A)

3. **Phase 2: J-lens workspace readout**
   - Load fitted J-lens
   - Check intermediate concept readout in workspace layers
   - Sanity checks (not just output layer, not just prompt echo)

4. **Phase 3: Distill vs Base comparison**
   - Ability-matched task selection
   - Activation patching effect size
   - Cross-template probing

5. **Phase 4: Activation patching**
   - Layer × position heatmap
   - Control groups (random, wrong layer, etc.)
   - Alignment with J-lens readout peaks

6. **Phase 5: Ablation DoD**
   - Workspace region ablation
   - Damage on distill answer-only performance
   - Controls and headroom gates

### Fallback Path (Plan B)

If J-lens is infeasible:
- Use logit lens + target token probing
- Activation patching (lens-independent)
- Report only "hidden representation evidence" (weaker conclusion)

## Documentation

- **docs/experiment_plan.md**: Full project plan (Chinese, 548 lines)
- **docs/implementation_notes.md**: Implementation specifics (Chinese)
- **docs/decision_log.md**: Design decisions and status
- **docs/run_log.md**: Command history and Azure resources
- **reports/current_status.md**: This file
- **infra/azure/README.md**: Azure infrastructure guide

## File Structure

```
J-space-observation/
├── src/jspace_observation/
│   ├── __init__.py
│   ├── config.py
│   ├── model_loader.py
│   ├── no_cot.py
│   ├── prompt_sets.py
│   ├── eval_parsing.py
│   ├── stats.py
│   ├── run_logging.py
│   └── jlens_utils.py
├── experiments/
│   ├── phase0_5_jlens_spike.py
│   └── phase1_depth_gradient.py
├── tests/
│   ├── __init__.py
│   ├── test_no_cot.py
│   ├── test_eval_parsing.py
│   └── test_stats.py
├── infra/azure/
│   ├── README.md
│   ├── variables.example.env
│   └── scripts/
│       ├── 00_check_prereqs.sh
│       ├── 01_build_and_push_image.sh
│       ├── 02_run_phase0_5.sh
│       └── 03_run_phase1.sh
├── docs/
│   ├── experiment_plan.md
│   ├── implementation_notes.md
│   ├── decision_log.md
│   ├── run_log.md
│   └── ...
├── reports/
│   └── current_status.md (this file)
├── Makefile
├── requirements.txt
├── pyproject.toml
└── Dockerfile
```

## Next Immediate Actions

1. Treat the parser-v2 locked evaluation as finished. Do not re-score, re-read,
   or reuse the retired 120-case holdout under any circumstance.
2. If parser v2 is to be revised, first fix the span-recovery failures behind
   `wrong_span` and `boxed_final_miss` using only public development cases.
3. Construct and privately seal a new locked holdout before any further locked
   validation; a modified parser may not be validated on the retired set.
4. Keep higher-n and every new target-model behavioral run paused.
5. Treat any larger J-lens fit as a separate preregistered decision.

## Success Criteria

✓ **Implemented**: Executable scaffold for Phase 0.5 and Phase 1
✓ **Tests passing**: All unit tests pass without model downloads
✓ **Infrastructure**: ACR managed identity and private Blob persistence are operational
✓ **Pilot**: Small stop-controlled Phase 1 run persisted successfully
✓ **Reporting**: Raw strict, stopped intervention, and postprocessed utility are separate
✓ **Criteria**: Branch-specific thresholds preregistered before further runs
✓ **Path C Phase 1.2A**: 60/120 evaluator set validated and privately sealed
✓ **Isolation**: Locked inputs/labels remain outside Git; five post-sealing reviews passed
✓ **Parser v2**: Public-development-only prospective implementation frozen; locked labels not accessed before sealing
✓ **Locked evaluation**: One-shot evaluation executed once and closed; holdout retired
✗ **Parser v2 locked acceptance**: Formal outcome **FAIL** (32/34 mandatory gates; `boxed_final_miss` and `wrong_span` failed)
✓ **Phase 0.5A**: Real official J-lens bounded T4 technical feasibility GREEN
⏳ **Pending**: Scientific lens-quality validation; not implied by Phase 0.5A
⏳ **Pending**: A new locked holdout before any revised parser can be validated
