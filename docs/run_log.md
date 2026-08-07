# Run Log

本文件记录所有实验命令、Azure 资源、运行结果和错误。

## 2026-07-08 — Repository reset

Action:

- Replaced existing repository contents with the final experiment plan and Copilot execution prompt.

No Azure resources were created in this step.

Next expected runs:

1. Phase 0.5 J-lens feasibility and saturation spike.
2. Phase 1 behavioral reasoning-depth gradient.

## 2026-07-08 — Executable scaffold implementation

Action:

- Implemented Phase 0.5 and Phase 1 executable scaffold
- Created all core Python modules:
  - `src/jspace_observation/config.py`: Configuration management
  - `src/jspace_observation/model_loader.py`: Hugging Face model loading
  - `src/jspace_observation/no_cot.py`: Strict no-CoT utilities with empty-think prefill
  - `src/jspace_observation/prompt_sets.py`: Pilot prompt generation (arithmetic, synthetic relation, factual/counterfactual)
  - `src/jspace_observation/eval_parsing.py`: Answer parsing and evaluation
  - `src/jspace_observation/stats.py`: Wilson CI and bootstrap utilities
  - `src/jspace_observation/run_logging.py`: Run tracking and metadata
  - `src/jspace_observation/jlens_utils.py`: J-lens availability checking
- Implemented experiment scripts:
  - `experiments/phase0_5_jlens_spike.py`: J-lens feasibility spike
  - `experiments/phase1_depth_gradient.py`: Behavioral reasoning-depth gradient
- Created unit tests (tests/test_no_cot.py, test_eval_parsing.py, test_stats.py)
- Set up Azure infrastructure:
  - `infra/azure/scripts/00_check_prereqs.sh`: Prerequisites checking
  - `infra/azure/scripts/01_build_and_push_image.sh`: Docker build and push
  - `infra/azure/scripts/02_run_phase0_5.sh`: Phase 0.5 job submission
  - `infra/azure/scripts/03_run_phase1.sh`: Phase 1 job submission
- Created Makefile for common operations
- All changes committed to git

Next action:

- Run `make test` to verify unit tests pass
- Run `make phase0-5` for local Phase 0.5 spike
- Run `make phase1-dry` for Phase 1 dry-run
- Setup Azure and submit jobs if needed

## 2026-07-08 — Scaffold sync verification before GitHub push

Action:

- Verified local branch state before pushing: `main` was ahead of `origin/main` by one implementation commit.
- Verified required implementation files exist locally, including all core modules, Phase 0.5/Phase 1 scripts, tests, Makefile, and Azure scripts.
- Implementation summary:
  - Phase 0.5 J-lens feasibility scaffold is implemented in `experiments/phase0_5_jlens_spike.py`.
  - Phase 1 behavioral depth-gradient scaffold is implemented in `experiments/phase1_depth_gradient.py`.
  - Strict no-CoT utilities, prompt sets, parsing, stats, run logging, model loading, and J-lens availability helpers are implemented under `src/jspace_observation/`.
  - Lightweight tests are implemented under `tests/`.

Test command:

- Requested command: `make test`
- Result: not executable in this Windows environment because `make` is not installed.
- Equivalent Makefile target command run: `python -m pytest tests/ -v`
- Test result: `41 passed, 2 warnings`

Azure:

- No Azure resources were created in this step.

## 2026-07-10 — Private Blob network path and stop-controlled pilot

Starting state:

- Code/image commit: `c29852ab97b5`.
- Tests: `python -m pytest tests/ -q` -> `73 passed, 2 warnings`.
- ACR build: `cm9`.
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:c29852ab97b5`.
- Digest: `sha256:2919bfa04dbcef0998cd9d770ffc91992958840d52ad512ab8b20b41dd434098`.
- Previous execution `job-jspace-p1-stopcontrol-0w0svmg` completed model inference and local result writing but failed Blob upload:
  - code: `AuthorizationFailure`
  - message: `This request is not authorized to perform this operation.`
  - root cause: storage `publicNetworkAccess=Disabled` with no VNet/private endpoint path.
- `Storage Blob Data Contributor` was confirmed for principal `78d4348b-57eb-4fb9-aaa7-99148b303292`.

Private network resources:

- VNet: `vnet-jspace-observation-sea` (`10.80.0.0/16`).
- First ACA subnet: `snet-aca-jspace-sea` (`10.80.0.0/23`), delegated to `Microsoft.App/environments`.
- Active ACA subnet: `snet-aca-jspace-sea-v2` (`10.80.4.0/23`), delegated to `Microsoft.App/environments`.
- Private endpoint subnet: `snet-pe-jspace-sea` (`10.80.2.0/27`).
- Blob private endpoint: `pe-stjspacefiles-blob-sea`.
- Private endpoint connection: `pec-stjspacefiles-blob-sea`.
- Private endpoint state: `Succeeded`; connection state: `Approved`.
- Blob private IP: `10.80.2.4`.
- Private DNS zone: `privatelink.blob.core.windows.net`.
- VNet link: `link-vnet-jspace-observation-sea-blob`.
- DNS A record: `stjspacefiles0709085305 -> 10.80.2.4`.
- Storage public network remained disabled; no storage key or SAS was used.

Environment provisioning:

- Initial environment: `cae-jspace-observation-sea-vnet`.
- Initial environment write reported:
  - code: `SubscriptionNotRegisteredForFeature`
  - required feature: `Microsoft.Network/AllowBringYourOwnPublicIpAddress`
- The feature was registered and `Microsoft.Network` was re-registered.
- The first environment continued to fail before container creation for both ACR and public MCR images. It was retained and not deleted.
- A fresh delegated subnet and environment were therefore created after feature registration:
  - active environment: `cae-jspace-observation-sea-vnet2`
  - state: `Succeeded`
  - profiles: `Consumption`, `gpu-t4 / Consumption-GPU-NC8as-T4`
- Runtime smoke:
  - job: `job-jspace-vnet2-runtime-smoke`
  - execution: `job-jspace-vnet2-runtime-smoke-1rrcsmi`
  - status: `Succeeded`
  - log: `runtime-smoke-ok`

Blob network smoke:

- Job: `job-jspace-blob-net-smoke-v2`.
- Execution: `job-jspace-blob-net-smoke-v2-l02nljz`.
- Status: `Succeeded`.
- Prefix: `network-smoke-v2/20260710T071144Z`.
- Log:
  - `Uploaded blob: network-smoke-v2/20260710T071144Z/smoke.txt`
  - `Blob export complete: 1 files`

Stop-control pilot:

- First VNet pilot execution: `job-jspace-p1-stopcontrol-vnet-kegu1ln`.
- Status: `Failed` before model execution.
- Error: `/bin/sh: 1: Syntax error: "&&" unexpected`.
- Cause: invalid `find -exec` terminator in the appended log-printing command.
- Corrected execution: `job-jspace-p1-stopcontrol-vnet-b55p4c6`.
- Status: `Succeeded`.
- Environment: `cae-jspace-observation-sea-vnet2`.
- Workload profile: `gpu-t4`.
- Blob prefix: `phase1-pilot-stopcontrol-vnet/20260710T072107Z`.
- Cells: 15.
- Uploaded files:
  - `phase1_eval_records.jsonl`
  - `phase1_generations.jsonl`
  - `phase1_metrics.csv`
  - `phase1_summary.md`
- Upload log: `Blob export complete: 4 files`.

`strict_answer_only_stopped` metrics:

| Depth | Raw no-CoT valid | Stopped no-CoT valid | Stop triggered | Stop success | Accuracy stopped | Parse valid | Parse ambiguous |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| 2 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 |

VNet result review:

- Job: `job-jspace-stop-review-vnet`.
- Execution: `job-jspace-stop-review-vnet-m7grppm`.
- Status: `Succeeded`.
- Blob count: 4.
- Representative stopped records:
  - depth 1 raw: `7 + 5 = \boxed{12}\n\n`; stopped: `7 + 5 = \boxed{12}`; correct.
  - depth 2 raw: `__________\n\n`; stopped: `__________`; parse failed.
  - depth 3 raw: `\boxed{12}\n\n`; stopped: `\boxed{12}`; parsed but wrong.
- All three stop triggers were `\n\n`.
- Summary warning: stop-controlled answer-only validity does not imply spontaneous raw no-CoT compliance.

Scientific boundary:

- Stop control is a generation intervention.
- Raw, stopped, and postprocessed validity remain separate.
- The result does not prove spontaneous no-CoT reasoning.
- No J-space claim is made.
- Do not expand Phase 1 yet.

## 2026-07-10 — Phase 1 branch taxonomy and report semantics

Scope:

- Documentation, metrics schema, summary generation, and local unit tests only.
- Baseline repository commit verified: `0aa536b3b239eb163740e1188e0a2adaaebc011b`.
- No model inference, Azure job, ACR build, J-lens fitting, activation patching, or experiment scaling was performed.

Implementation:

- Added `src/jspace_observation/phase1_branches.py`.
- Added `docs/phase1_experiment_branches.md`.
- Mapped raw strict, stopped intervention, and postprocessed utility conditions to stable branch labels.
- Added branch metadata and explicit raw/stopped/postprocessed correctness aliases to Phase 1 records.
- Added branch columns to the metrics CSV.
- Added a branch-level metrics table with `NA` for non-applicable metrics.
- Added mandatory summary warnings that stopped validity is not spontaneous no-CoT, postprocessed validity is not raw no-CoT, and Phase 1 is not J-space evidence.

Local commands:

```text
python -m py_compile src\jspace_observation\phase1_branches.py src\jspace_observation\__init__.py experiments\phase1_depth_gradient.py
python -m pytest tests\ -q
```

Result:

```text
80 passed, 2 warnings
```

Azure:

- Rerun performed: no.
- Active environment remains `cae-jspace-observation-sea-vnet2`.
- Latest successful stop-control execution remains `job-jspace-p1-stopcontrol-vnet-b55p4c6`.
- Latest stop-control Blob prefix remains `phase1-pilot-stopcontrol-vnet/20260710T072107Z`.

Decision:

- Current blocker: none.
- Keep scaling paused.
- Review and approve branch-specific success criteria before any new model run.

## 2026-07-10 — preregister Phase 1 branch success criteria

Scope:

- Methodology, classification helper, report template, tests, and documentation only.
- Repository baseline: `a9c8e29ebab6dd4fbf1ec3803de3bcc300c80d3a`.
- No model inference, Azure job, ACR build, scale increase, model addition, task-family addition, J-lens fitting, or activation patching was performed.

Implementation:

- Added deterministic `classify_branch_result()` logic for all three answer-control branches.
- Added raw strict absolute and matching visible-CoT relative accuracy gates.
- Added stopped-intervention surface, stop-success, parsing, and accuracy gates.
- Added postprocessed validity, recovery-success, warning, and relative accuracy gates.
- Added a `Branch success classification` report section with per-branch labels, failed/passed criteria, stop-string distribution, and mandatory scientific warnings.
- Preserved `NA` for non-applicable metrics and did not change validator behavior.

Local commands:

```text
python -m py_compile src\jspace_observation\phase1_branches.py src\jspace_observation\__init__.py experiments\phase1_depth_gradient.py
python -m pytest tests\test_phase1_branches.py -q
python -m pytest tests\ -q
```

Result:

```text
targeted: 19 passed, 2 warnings
full suite: 92 passed, 2 warnings
```

Azure:

- Rerun performed: no.
- Active environment remains `cae-jspace-observation-sea-vnet2`.
- Active Blob prefix remains `phase1-pilot-stopcontrol-vnet/20260710T072107Z`.
- Latest successful stop-control execution remains `job-jspace-p1-stopcontrol-vnet-b55p4c6`.

Decision:

- Criteria are preregistered before any new data collection.
- Current blocker: none.
- The next run requires explicit approval and must remain limited scale.

## 2026-07-08 — Local environment validation for Phase 0.5

Active Python environment:

- Python version: `Python 3.13.14`
- Python executable: `C:\Users\alanjiao\AppData\Local\Programs\Python\Python313\python.exe`
- pip: `pip 26.1.2`

Commands executed:

- `python --version`
- `python -c "import sys; print(sys.executable)"`
- `python -m pip --version`
- `python -m pip list | findstr /I "torch transformers accelerate safetensors sentencepiece"`
- `python -m pip install --upgrade pip`
- `python -m pip install -r requirements.txt`
- `python -c "import torch, transformers, accelerate, safetensors, sentencepiece; print('core deps ok')"`
- `cd C:\Users\alanjiao`
- `if not exist external mkdir external`
- `cd external`
- `if not exist jacobian-lens git clone https://github.com/anthropics/jacobian-lens.git`
- `cd jacobian-lens`
- `python -m pip install -e .`
- `python -c "import jlens; print('jlens import ok')"`
- `python -m pytest tests/ -v`
- `python experiments\phase0_5_jlens_spike.py --skip-fit`
- `python experiments\phase1_depth_gradient.py --dry-run`

Dependency install results:

- `requirements.txt` installed successfully in the active Python environment.
- Core dependency import check passed: `core deps ok`.
- `accelerate` is now installed/importable.
- External jacobian-lens clone/install path: `C:\Users\alanjiao\external\jacobian-lens`
- jacobian-lens import result: `import jlens` succeeded.
- The project helper was updated to recognize the package's installed import name, `jlens`.

Validation results:

- Test result: `41 passed, 2 warnings`.
- Phase 0.5 output directory: `results/runs/20260708_182022`
- Phase 0.5 summary path: `results/runs/20260708_182022/phase0_5_summary.md`
- Phase 0.5 findings:
  - Pre-fitted lenses found locally/configured: `false`
  - jacobian-lens installed/importable: `true` / `true`
  - Model loading attempted: `true`
  - Model loading success for all models: `true`
  - DeepSeek-R1-Distill-Qwen-1.5B loaded on CPU; 28 layers, hidden size 1536, 1.78B parameters.
  - Qwen2.5-Math-1.5B loaded on CPU; 28 layers, hidden size 1536, 1.54B parameters.
  - Actual tiny fitting attempted: `no`
  - Actual tiny fitting success: `not attempted`
- Phase 1 dry-run result:
  - Conditions: `strict_answer_only`, `visible_cot`, `r1_style_thinking`
  - Total cells: `54`
  - No model generation was performed by dry run.

Azure:

- Azure resources created: none.

## 2026-07-08 — Azure-first workflow preparation

Policy update:

- Local validation is complete.
- From this point, the local PC is orchestration-only.
- Heavy execution must happen on Azure GPU containers:
  - model download
  - model loading
  - Phase 0.5 fitting / model loading
  - Phase 1 real generation
  - later J-lens, patching, and ablation experiments
- Do not silently fall back to local inference if Azure is blocked.

Lightweight Azure CLI checks executed:

- `az version`
- `az account show --query "{name:name,id:id,state:state,isDefault:isDefault,tenantId:tenantId}" -o json`
- `az extension list -o table`
- `az provider show -n Microsoft.App --query registrationState -o tsv`
- `az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv`
- `az extension show --name containerapp --query "{name:name,version:version,preview:preview}" -o json`

Azure CLI results:

- Azure CLI: `2.83.0`
- Active subscription: `MCAPS-Hybrid-REQ-125620-2025-alanjiao`
- Subscription state: `Enabled`
- Microsoft.App registration: `Registered`
- Microsoft.ContainerRegistry registration: `Registering`
- containerapp extension: installed, version `1.3.0b4`
- `az extension add --name containerapp --upgrade` was not run because the extension is already installed.

Repository updates:

- Updated `docs/azure_runbook.md` with Azure-first policy, readiness checks, GPU quota gate, and stop rules.
- Updated `infra/azure/variables.example.env` with Azure Container Apps GPU placeholders.
- Updated `infra/azure/scripts/00_check_prereqs.sh` to be a no-resource readiness check.
- Added `infra/azure/scripts/00_check_prereqs.ps1`.
- Updated Azure scripts for ACR build, Phase 0.5 Azure job, Phase 1 Azure dry-run job, and small Phase 1 pilot job.

Azure:

- Azure resources created: none.
- Blocker before resource creation: wait for `Microsoft.ContainerRegistry` to become `Registered` and verify Container Apps GPU T4 quota.

Local validation after Azure-first updates:

- `python -m pytest tests/ -v` -> `41 passed, 2 warnings`
- `python experiments\phase1_depth_gradient.py --dry-run` -> completed, total cells `54`
- Phase 1 dry-run conditions: `strict_answer_only`, `visible_cot`, `r1_style_thinking`
- No local model inference, model download, or J-lens fitting was run.
- Azure resources created: none.

## 2026-07-08 — Azure readiness gate re-check

Commands executed:

- `az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv`
- `az provider show -n Microsoft.App --query registrationState -o tsv`
- `az account show --query "{name:name,id:id,state:state,isDefault:isDefault}" -o json`

Results:

- Subscription: `MCAPS-Hybrid-REQ-125620-2025-alanjiao`
- Subscription state: `Enabled`
- Microsoft.ContainerRegistry registration: `Registering`
- Microsoft.App registration: `Registered`
- Azure Container Apps T4 GPU quota status: not checked because provider gate failed first.
- Readiness script result: not run because `Microsoft.ContainerRegistry` is not yet `Registered`.
- Azure resources created: none.

Decision:

- Stop before any Azure resource creation.
- Re-run provider gate later; only proceed to GPU quota confirmation after `Microsoft.ContainerRegistry` becomes `Registered`.

## 2026-07-08 — Azure provider gate re-check

Commands executed:

- `az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv`
- `az provider show -n Microsoft.App --query registrationState -o tsv`

Results:

- Microsoft.ContainerRegistry registration: `Registering`
- Microsoft.App registration: `Registered`
- T4 GPU quota status: not checked because provider gate is still blocked.
- Readiness script result: not run.
- Azure resources created: none.

Decision:

- Stop. Re-check provider registration later before any quota check or readiness script.

## 2026-07-08 — Azure provider gate re-check (first recheck)

Commands executed:

- `az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv`
- `az provider show -n Microsoft.App --query registrationState -o tsv`

Results:

- Microsoft.ContainerRegistry registration: `Registering`
- Microsoft.App registration: `Registered`
- T4 GPU quota status: not checked because `Microsoft.ContainerRegistry` remains `Registering`.
- Readiness script result: not run.
- Azure resources created: none.

Decision:

- Stop. Re-check provider registration later before any quota check or readiness script.

## 2026-07-08 — Container Registry provider retry + GHCR fallback

Commands executed:

- `az provider register --namespace Microsoft.ContainerRegistry --wait`
- `az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv`
- `az provider show -n Microsoft.App --query registrationState -o tsv`

Results:

- `az provider register --namespace Microsoft.ContainerRegistry --wait` returned exit code `0`, but registration state remained `Registering` after the command completed and after a follow-up re-check.
- Microsoft.ContainerRegistry registration: `Registering` (still blocked after retry)
- Microsoft.App registration: `Registered`
- T4 GPU quota status: not checked; blocked by registry provider gate.
- Readiness script result: not run.
- Azure resources created: none.

Decision:

- ACR path is treated as blocked because `Microsoft.ContainerRegistry` did not reach `Registered` even after an explicit `--wait` retry that took several hours in total.
- Adopt GHCR (GitHub Container Registry) as the fallback image registry for Azure Container Apps.
- Prepared GHCR fallback assets (no Azure resources created):
  - `infra/ci/build-ghcr.yml`: GitHub Actions workflow definition to build/push image to GHCR (see note below on installation).
  - `infra/azure/scripts/05_run_job_ghcr.sh`: parameterized Azure Container Apps Job script using a GHCR image; secrets provided only via environment/Azure secret, never committed.
  - `docs/azure_runbook.md`: new "GHCR fallback when Microsoft.ContainerRegistry is blocked" section.
  - `.dockerignore`: prevents secrets, results, and Hugging Face caches from entering the image.
- Note: The Git credential used by the CLI lacks the `workflow` OAuth scope, so pushing files under `.github/workflows/` was rejected by GitHub (`refusing to allow an OAuth App to create or update workflow ... without workflow scope`). The workflow file is therefore stored at `infra/ci/build-ghcr.yml` and must be installed into `.github/workflows/build-ghcr.yml` via the GitHub web UI or a `workflow`-scoped token.
- Microsoft.App provider and Azure Container Apps T4 GPU quota (southeastasia) are still required before any GPU job.
- Do not fall back to local model inference if T4 quota is unavailable.

Local validation:

- `python -m pytest tests/ -v` -> `41 passed, 2 warnings`
- `python experiments\phase1_depth_gradient.py --dry-run` -> completed, total cells `54`

Azure:

- Azure resources created: none.

## 2026-07-08 — GHCR + T4 quota path focus; ACR now Registered

Commands executed (read-only + local):

- `az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv`
- `az provider show -n Microsoft.App --query registrationState -o tsv`
- `python -m pytest tests/ -v`
- `python experiments\phase1_depth_gradient.py --dry-run`

Results:

- Microsoft.ContainerRegistry registration: `Registered` (state has now flipped from `Registering` to `Registered`).
- Microsoft.App registration: `Registered`.
- GHCR workflow template `infra/ci/build-ghcr.yml` reviewed and valid:
  - uses `workflow_dispatch`;
  - builds the repo `Dockerfile`;
  - pushes to GHCR;
  - tags image with git SHA and optionally `latest`;
  - does not download models or bake HF cache;
  - requires only `contents: read` + `packages: write` with `GITHUB_TOKEN`.
- GHCR Azure job script `infra/azure/scripts/05_run_job_ghcr.sh` reviewed and valid:
  - parameterized; no hardcoded token;
  - reads `GHCR_PAT` from environment and passes it as a Container Apps secret;
  - uses a GHCR image path;
  - supports command override via `JOB_COMMAND` (Phase 0.5 skip-fit, Phase 1 dry-run, small Phase 1 pilot);
  - creates resources only when explicitly invoked.
- Test result: `41 passed, 2 warnings`.
- Phase 1 dry-run: completed, total cells `54`.
- T4 GPU quota status: not yet confirmed; documented portal + support-request steps in `docs/azure_runbook.md`.
- Azure resources created: none.

Decision:

- ACR is now `Registered`, so the ACR path is technically unblocked again. Per Alan's instruction, the primary container path remains GHCR for now; ACR scripts remain available as an alternative.
- Manual installation of `.github/workflows/build-ghcr.yml` via the GitHub web UI is still required because the CLI credential lacks `workflow` scope.
- Next Azure gate: confirm Container Apps T4 GPU quota in `southeastasia`.

## 2026-07-08 — Keep GHCR primary after ACR provider recovery

Commands executed (read-only + local):

- `az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv`
- `az provider show -n Microsoft.App --query registrationState -o tsv`
- `python -m pytest tests/ -v`
- `python experiments\phase1_depth_gradient.py --dry-run`

Results:

- Microsoft.ContainerRegistry registration: `Registered` (confirmed again).
- Microsoft.App registration: `Registered`.
- Test result: `41 passed, 2 warnings`.
- Phase 1 dry-run: completed, total cells `54`.
- T4 GPU quota status: not yet confirmed (next Azure gate).
- Azure resources created: none.

Decision:

- ACR provider is now `Registered`, but GHCR remains the **primary** container registry path; ACR is the **secondary fallback** only.
- Reason: GHCR aligns better with git-SHA image provenance and GitHub workflow-based builds, and avoids re-coupling the pipeline to ACR provider timing.
- Documented registry strategy, planned Azure command sequence, and T4 quota confirmation steps in `docs/azure_runbook.md`.
- Manual installation of `.github/workflows/build-ghcr.yml` remains required (CLI credential lacks `workflow` scope).

## 2026-07-08 — Workflow install attempt + read-only Azure gate checks

Baseline: read `docs/thread_handoff.md`; confirmed `origin/main` HEAD = `dd1b24301407955b1d0de90e9e96a4035d87b183` (matches expected).

Workflow installation attempts (both failed as expected):

- `gh auth status`: two accounts on github.com:
  - `Alanjiao1988` (active, repo owner): scopes `gist, read:org, repo` — **no `workflow` scope**.
  - `alanjiao_microsoft`: scopes include `workflow`, but **404 (no access)** to `Alanjiao1988/J-space-observation`.
- Tried Contents API install with the owner account:
  - `gh api -X PUT repos/Alanjiao1988/J-space-observation/contents/.github/workflows/build-ghcr.yml` -> `404 Not Found` (GitHub masks the `workflow`-scope restriction as 404).
- Conclusion: `.github/workflows/build-ghcr.yml` **cannot** be installed programmatically with available credentials. Manual GitHub web UI install by Alan remains required. Switched active `gh` account back to `Alanjiao1988`.

Read-only Azure checks (no resources created):

- `az group list` filtered for `jspace`: `[]` (no project resource groups exist).
- `az containerapp env workload-profile list-supported -l southeastasia`: the profile `Consumption-GPU-NC8as-T4` **is offered in southeastasia** (regional availability confirmed).
- `az quota list --scope /subscriptions/<sub>/providers/Microsoft.App/locations/southeastasia`: failed with `MissingRegistrationForResourceProvider: Microsoft.Quota`. Did not register `Microsoft.Quota` (avoiding another multi-hour provider registration without approval).

Status after checks:

- Microsoft.App: `Registered`. Microsoft.ContainerRegistry: `Registered`.
- T4 GPU workload profile TYPE available in `southeastasia`: **yes**.
- Actual T4 GPU QUOTA for the subscription: **still not confirmed** (needs portal Usage+quotas or a support request; `az quota` blocked by unregistered `Microsoft.Quota`).
- Azure resources created: **none** (verified).

Decision:

- Workflow install stays a manual UI action for Alan.
- Do not create Azure resources; T4 quota confirmation remains the gate.
- Did not register `Microsoft.Quota` — will ask Alan before triggering any further provider registration.

## 2026-07-08 — GHCR workflow triggered and image published

Repository sync:

- Pulled remote `main`; workflow install commit present: `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- `.github/workflows/build-ghcr.yml` exists.
- `infra/ci/build-ghcr.yml` and `.github/workflows/build-ghcr.yml` have no diff.

GitHub workflow checks:

- `gh auth status -h github.com`: active account `Alanjiao1988`, repo access `ADMIN`.
- `gh workflow list -R Alanjiao1988/J-space-observation`: `Build and push image to GHCR` is active.
- Trigger command: `gh workflow run build-ghcr.yml -R Alanjiao1988/J-space-observation --ref main -f push_latest=true`.
- Trigger method: `gh workflow run` by file name.

Workflow run:

- Run id: `28947916765`
- Status: `completed`
- Conclusion: `success`
- URL: `https://github.com/Alanjiao1988/J-space-observation/actions/runs/28947916765`
- Head SHA: `c07db5c9625a9f9ad96c55f77385c078e11d4a66`

GHCR image:

- `ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66`
- `ghcr.io/alanjiao1988/j-space-observation:latest`
- Workflow logs confirm both manifests were pushed.
- Package API note: current `gh` token lacks `read:packages`, so user package version API returns `403`; repo package endpoint returns `404`. This does not invalidate the push because the workflow completed successfully and logs include pushed manifests.

Azure read-only status:

- Microsoft.App: `Registered`
- Microsoft.ContainerRegistry: `Registered`
- Microsoft.Quota: `NotRegistered`
- `az group list --query "[?contains(name, 'jspace') || contains(name, 'j-space')].{name:name, location:location}" -o table`: no matching resource groups.
- Azure resources created: none.

T4 quota:

- T4 workload profile type `Consumption-GPU-NC8as-T4` is offered in `southeastasia`.
- Subscription quota remains **not confirmed** because `Microsoft.Quota` is `NotRegistered`; do not register it without Alan approval.
- Next gate: confirm Azure Container Apps T4 quota in `southeastasia` before any Azure GPU job.

## 2026-07-08 — GHCR image/current commit check and quota CLI attempt

Repository/image diff:

- Repo latest commit at start: `c10afdd1d0817b0cf3c773b54a91d81d65f2ed05`.
- GHCR image commit: `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Changed files between image commit and latest commit:
  - `docs/azure_runbook.md`
  - `docs/decision_log.md`
  - `docs/run_log.md`
  - `docs/thread_handoff.md`
  - `reports/current_status.md`
- Classification: documentation-only. Rebuild not required.
- Rebuild performed: no.

GHCR image status:

- Existing image retained: `ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66`
- `latest` tag: yes, workflow logs confirm it was pushed.
- Package API:
  - repo-scoped endpoint: `404`
  - user-scoped endpoint: `403` because current token lacks `read:packages`
  - workflow logs confirm pushed manifests for both SHA tag and `latest`.

Azure read-only checks:

- `az account show --query "{name:name, id:id, state:state}" -o table`: subscription `MCAPS-Hybrid-REQ-125620-2025-alanjiao`, `Enabled`.
- Microsoft.App: `Registered`
- Microsoft.ContainerRegistry: `Registered`
- Microsoft.Quota before registration: `NotRegistered`
- Project resource groups: none (`az group list` query returned no `jspace` / `j-space` groups).

Microsoft.Quota registration:

- Alan's current instruction allowed registering `Microsoft.Quota` only for quota read access.
- Command run: `az provider register --namespace Microsoft.Quota` (no `--wait`).
- Initial short polling: `Registering`.
- Final follow-up provider status: `Registered`.
- Azure resources created: none.

Quota read attempts:

- `az quota list --scope /subscriptions/<sub>/providers/Microsoft.App/locations/southeastasia -o json`
- `az quota usage list --scope /subscriptions/<sub>/providers/Microsoft.App/locations/southeastasia -o json`
- Returned quota/usage entries:
  - `ManagedEnvironmentCount`: limit 50, usage 0
  - `SessionPools`: limit 50, usage 0
  - `SubscriptionDedicatedNCA100Gpus`: limit 0, usage -1, `isQuotaApplicable=false`
  - `ExpressEnvironmentCount`: limit 500, usage 0, `isQuotaApplicable=false`
- No `Consumption-GPU-NC8as-T4`, T4, NC8as, or managed environment Consumption T4 quota item was returned.

T4 quota conclusion:

- Region/workload profile availability: yes (`Consumption-GPU-NC8as-T4` is offered in `southeastasia`).
- Subscription T4 quota: still unknown via CLI.
- Exact blocker: Microsoft.App quota API does not expose a T4/NC8as-T4 quota item for this subscription/region.
- Next action: use Azure Portal Usage + quotas or Azure support to confirm/request Container Apps Managed Environment Consumption T4 GPUs in `southeastasia`.
- Do not create Azure GPU jobs and do not fall back to local inference.

## 2026-07-08 — Azure GHCR smoke path: resource creation and first pull failure

Scope:

- Alan explicitly approved entering the Azure resource creation and GHCR smoke-test phase.
- Still prohibited: local model inference/downloads, local Phase 1 generation, local J-lens fitting, secrets in repo/logs.

Image/build decision:

- Repo HEAD at start: `ed1872c5347cb525af262e77348e167818dc7b10`.
- Validated GHCR image: `ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Diff from image commit to HEAD was documentation-only:
  - `docs/azure_runbook.md`
  - `docs/decision_log.md`
  - `docs/run_log.md`
  - `docs/thread_handoff.md`
  - `reports/current_status.md`
- Image rebuild: not required.

Scripts reviewed:

- `docs/azure_runbook.md`
- `docs/thread_handoff.md`
- `reports/current_status.md`
- `infra/azure/scripts/`
- `infra/azure/scripts/05_run_job_ghcr.sh`

Azure sanity checks:

- Subscription: `MCAPS-Hybrid-REQ-125620-2025-alanjiao`
- Microsoft.App: `Registered`
- Microsoft.ContainerRegistry: `Registered`
- Microsoft.Quota: `Registered`
- Existing project resource groups before creation: none.

Resources created:

- Resource group:
  - name: `rg-jspace-observation-sea`
  - location: `southeastasia`
  - tags: `project=jspace-observation owner=alan purpose=research-pilot registry=ghcr environment=dev`
  - provisioning: `Succeeded`
- Log Analytics workspace:
  - name: `law-jspace-observation-sea`
  - resource group: `rg-jspace-observation-sea`
  - location: `southeastasia`
  - provisioning: `Succeeded`
  - customerId: `8daddd67-1cfd-47c5-857e-af3c4a4e3787`
  - key acquired: yes (value not logged)
- Container Apps environment:
  - name: `cae-jspace-observation-sea`
  - resource group: `rg-jspace-observation-sea`
  - location: `Southeast Asia`
  - provisioning: `Succeeded`
  - default domain: `ambitiouspebble-6a6974cf.southeastasia.azurecontainerapps.io`
- Workload profiles:
  - `Consumption`
  - `gpu-t4` (`Consumption-GPU-NC8as-T4`)

Container Apps environment command notes:

- Failed command:
  - `az containerapp env create ... --enable-workload-profiles true --enable-dedicated-gpu true ...`
  - error code: `WorkloadProfileInvalidType`
  - exact message: `Workload profile type 'NC24_A100' is invalid.`
  - classification: CLI/preview parameter issue; `--enable-dedicated-gpu true` defaults toward an invalid A100 profile for this region/path.
  - fix: create the workload-profile environment without `--enable-dedicated-gpu true`.
- Failed command:
  - `az containerapp env workload-profile add ... --workload-profile-type Consumption-GPU-NC8as-T4 --min-nodes 0 --max-nodes 1`
  - error code: `WorkloadProfilePropertyNotSupported`
  - exact message: `Workload Profile property 'MinimumCount' is not supported for CONSUMPTION_GPU_NC8AS_T4`
  - classification: CLI/service syntax for consumption GPU profile.
  - fix: omit `--min-nodes/--max-nodes`.
- Successful command:
  - `az containerapp env workload-profile add ... --workload-profile-name gpu-t4 --workload-profile-type Consumption-GPU-NC8as-T4`
  - result: `gpu-t4` profile added.

Effective T4 quota validation:

- `Consumption-GPU-NC8as-T4` workload profile was successfully added to the environment.
- No quota error occurred during resource group, Log Analytics, environment, or GPU workload profile creation.
- GPU job execution has not yet succeeded; GHCR pull/auth blocked the smoke job before execution.

GHCR authentication check:

- Local environment variables:
  - `GHCR_PAT`: not set
  - `GHCR_USERNAME`: not set
- First smoke-test job attempted unauthenticated GHCR pull.
- Job name attempted: `job-jspace-ghcr-smoke`
- Image: `ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66`
- Intended smoke command: `python -m pytest tests/ -q` (not executed due pull/auth failure)
- Job was not created.
- Error code: `InvalidParameterValueInContainerTemplate`
- Exact error message:
  - `Field 'template.containers.job-jspace-ghcr-smoke.image' is invalid with details: 'Invalid value: "ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66": GET https:?scope=repository%3Aalanjiao1988%2Fj-space-observation%3Apull&service=ghcr.io: UNAUTHORIZED: authentication required';.`
- Classification: GHCR private package / registry authentication required.

Current stop reason:

- Need GHCR pull credentials or make package public before Azure Container Apps can create/run the GHCR job.
- Do not send token in chat. Provide `GHCR_PAT` through environment variable or Azure secret path only.
- No model inference, Phase 0.5, Phase 1 dry-run, or Phase 1 pilot was run in Azure yet.

Script maintenance:

- Updated `infra/azure/scripts/05_run_job_ghcr.sh` after the live Azure attempt:
  - defaults now match actual resource names: `rg-jspace-observation-sea`, `cae-jspace-observation-sea`, `job-jspace-ghcr-smoke`;
  - resource group / environment / job creation includes project tags;
  - removed `--enable-dedicated-gpu true` from environment creation because it caused `WorkloadProfileInvalidType: NC24_A100 invalid`;
  - removed `--min-nodes/--max-nodes` from `Consumption-GPU-NC8as-T4` workload profile creation because it caused `WorkloadProfilePropertyNotSupported`.

## 2026-07-08 — GHCR auth retry with gh token, still blocked

GHCR token handling:

- Local env check:
  - `GHCR_PAT`: not set
  - `GHCR_USERNAME`: not set; defaulted to `Alanjiao1988`
  - `gh auth token`: available
- Token values were not printed or committed.
- Used `gh auth token` as the Azure registry secret value for a retry because no `GHCR_PAT` was available.

Job creation method:

- Switched to `az rest` / ARM body to avoid `az containerapp job create --args -lc ...` CLI parsing problems.
- Discovered correct ARM schema placement for job workload profile:
  - invalid: `properties.template.workloadProfileName`
  - invalid: `properties.configuration.workloadProfileName`
  - valid: `properties.workloadProfileName`
- Updated `infra/azure/scripts/05_run_job_ghcr.sh` accordingly.

Failed schema attempts:

- Error: `Unknown properties workloadProfileName in ContainerAppsJobTemplate are not supported`
- Error: `Unknown properties workloadProfileName in ContainerAppsJobConfiguration are not supported`
- Classification: ARM schema placement issue; fixed by moving `workloadProfileName` to `properties.workloadProfileName`.

GHCR auth retry result:

- Job attempted: `job-jspace-ghcr-smoke`
- Image: `ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66`
- Intended smoke command: `python -m pytest tests/ -q`
- Error code: `InvalidParameterValueInContainerTemplate`
- Exact error message:
  - `Field 'template.containers.main.image' is invalid with details: 'Invalid value: "ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66": GET https:: DENIED: requested access to the resource is denied';.`
- Classification: GHCR private package / token insufficient for package pull. The available `gh auth token` is not sufficient for Azure to pull this private GHCR image.

Resource state after retry:

- Jobs: none.
- Resource group remains: `rg-jspace-observation-sea`.
- Log Analytics workspace remains: `law-jspace-observation-sea`.
- Container Apps environment remains: `cae-jspace-observation-sea`.
- Workload profile remains: `gpu-t4` (`Consumption-GPU-NC8as-T4`).

Current stop reason:

- Need either:
  1. Make GHCR package public; or
  2. Provide `GHCR_USERNAME` + classic PAT with `read:packages` via secure environment variable / Azure secret path.
- Do not paste the token in chat. Do not commit it. Do not print it.
- Phase 0.5 / Phase 1 dry-run / small pilot were not attempted.

## 2026-07-08 — GHCR auth preflight: no usable package-read token

Scope:

- Alan requested resolving GHCR private image pull authentication and rerunning the smoke job.
- Existing Azure resources were verified; no new resource creation was attempted in this step because credentials were not usable.

Existing Azure resources:

- Resource group: `rg-jspace-observation-sea` (`Succeeded`)
- Log Analytics workspace: `law-jspace-observation-sea` (`Succeeded`)
- Container Apps environment: `cae-jspace-observation-sea` (`Succeeded`)
- Workload profile: `gpu-t4` / `Consumption-GPU-NC8as-T4`
- Jobs: none

GHCR token preflight:

- `GHCR_USERNAME`: defaulted to `Alanjiao1988`
- `GHCR_PAT`: not set
- `gh auth token`: available
- Package read test using current `gh auth token`:
  - endpoint: `gh api users/Alanjiao1988/packages/container/j-space-observation/versions`
  - result: `403`
  - message: `You need at least read:packages scope to get a package's versions.`
- Token value was not printed or committed.

Decision:

- Do not retry Azure job creation with the known-insufficient `gh auth token`.
- Current blocker remains GHCR private image pull authentication.
- Required next step: either make the GHCR package public or set a secure `GHCR_PAT` classic PAT with `read:packages` in the local environment / approved Azure secret path.

Script maintenance:

- Updated `infra/azure/scripts/05_run_job_ghcr.sh` to:
  - support aliases requested by Alan: `JOB_NAME`, `CONTAINERAPPS_ENVIRONMENT`, `WORKLOAD_PROFILE_NAME`;
  - keep `CONTAINER_APP_JOB`, `CONTAINER_APP_ENV`, and `GPU_WORKLOAD_PROFILE_NAME` compatibility;
  - avoid passing the GHCR token as a Python command-line argument when generating the ARM request body;
  - continue using `GHCR_PAT` first and `gh auth token` fallback only when `GHCR_PAT` is absent.

Azure:

- Azure resources created in this step: none.
- Smoke job rerun: not attempted due missing usable package-read token.
- Phase 0.5 / Phase 1 dry-run / pilot: not attempted.

## 2026-07-08 — GHCR_PAT not visible to agent environment

Scope:

- Alan indicated `GHCR_USERNAME` and `GHCR_PAT` were set in a local PowerShell shell.
- The Copilot tool process runs commands in fresh child processes and did not inherit those shell-local variables.

Checks executed (token values not printed):

- `git fetch origin`
- `git checkout main`
- `git pull --ff-only origin main`
- Checked `GHCR_USERNAME` and `GHCR_PAT` presence in:
  - Process environment
  - User environment
  - Machine environment

Results:

- Repo synced at `033a52d80d91647809bf37f09851a47be0eee55f`.
- `GHCR_USERNAME`: not visible in Process/User/Machine environment.
- `GHCR_PAT`: not visible in Process/User/Machine environment.
- GHCR package-read preflight: not run because no token was visible.
- Azure job retry: not attempted.
- Azure resources created in this step: none.
- Existing Azure resources unchanged:
  - `rg-jspace-observation-sea`
  - `law-jspace-observation-sea`
  - `cae-jspace-observation-sea`
  - `gpu-t4`

Next required action:

- Make the PAT visible to the agent without pasting it into chat. Recommended local command for Alan to run in a separate PowerShell, replacing `<token>` locally:
  - `[Environment]::SetEnvironmentVariable("GHCR_USERNAME", "Alanjiao1988", "User")`
  - `[Environment]::SetEnvironmentVariable("GHCR_PAT", "<classic PAT with read:packages>", "User")`
- After that, ask Copilot to retry. Copilot will verify presence via `User` scope without printing the token.

## 2026-07-08 — GHCR_PAT retry after reported environment reset still not visible

Scope:

- Alan reported setting `GHCR_USERNAME` / `GHCR_PAT` as Windows User environment variables and restarting VS Code / Copilot agent / terminal.
- Copilot re-synced the repo and re-checked all environment scopes.

Checks executed:

- `git fetch origin`
- `git checkout main`
- `git pull --ff-only origin main`
- `git status -sb`
- `git log --oneline -5`
- Checked `GHCR_USERNAME` / `GHCR_PAT` presence in Process, User, and Machine environment scopes.
- Confirmed existing Azure resources:
  - `rg-jspace-observation-sea`: `Succeeded`
  - `law-jspace-observation-sea`: `Succeeded`
  - `cae-jspace-observation-sea`: `Succeeded`
  - workload profile `gpu-t4` / `Consumption-GPU-NC8as-T4`: present

Results:

- `GHCR_USERNAME`: not visible in Process/User/Machine environment.
- `GHCR_PAT`: not visible in Process/User/Machine environment.
- GHCR package-read preflight: not run because no PAT was visible.
- Azure smoke job retry: not attempted.
- Token printed: no.
- Secret committed: no.
- Azure resources created in this step: none.

Decision:

- Stop. The current agent process still cannot read the GHCR PAT.
- Do not retry Azure job creation with `gh auth token`, because previous preflight showed it lacks `read:packages`.
- Required next action: expose a classic PAT with `read:packages` through a mechanism visible to this agent process, or make the GHCR package public.

## 2026-07-08 — Switch to ACR managed identity and complete Azure pilot chain

Decision:

- Stop pursuing GHCR private package authentication.
- Activate ACR as the registry path using Azure AAD / user-assigned managed identity, no ACR admin password.

Repository:

- Starting commit: `d69187c7a14782121d8d90c983ce7033b29967dd`.
- Diff from GHCR image commit `c07db5c...` to HEAD included docs plus `infra/azure/scripts/05_run_job_ghcr.sh`, so ACR image was rebuilt from current HEAD.

ACR:

- Name: `acrjspaceobssea0708231738`
- Login server: `acrjspaceobssea0708231738.azurecr.io`
- SKU: `Basic`
- Admin user enabled: `False`
- ARM audience token auth: `enabled`
- Image repository: `j-space-observation`
- Image tags:
  - `d69187c7a147`
  - `latest`
- Full image used by jobs: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:d69187c7a147`
- Build command: `az acr build --registry acrjspaceobssea0708231738 --image j-space-observation:d69187c7a147 --image j-space-observation:latest --file Dockerfile .`
- Build result: success; digest `sha256:c41aa98e7316b9f153eb107647bcf5bb683a43097d224d70d8237d44d4d17c94`

Managed identity:

- Name: `id-jspace-aca-acrpull-sea`
- Identity ID: `/subscriptions/943bacdf-8b6e-4e3a-8126-a149f623d32e/resourcegroups/rg-jspace-observation-sea/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-jspace-aca-acrpull-sea`
- Principal ID: `78d4348b-57eb-4fb9-aaa7-99148b303292`
- AcrPull assignment: yes, scoped to ACR `acrjspaceobssea0708231738`

Azure resources now present:

- Resource group: `rg-jspace-observation-sea`
- Log Analytics workspace: `law-jspace-observation-sea`
- Container Apps environment: `cae-jspace-observation-sea`
- Workload profile: `gpu-t4` / `Consumption-GPU-NC8as-T4`
- ACR: `acrjspaceobssea0708231738`
- User-assigned managed identity: `id-jspace-aca-acrpull-sea`
- Jobs:
  - `job-jspace-acr-smoke`
  - `job-jspace-phase05-acr`
  - `job-jspace-phase1-dryrun-acr`
  - `job-jspace-phase1-pilot-acr`

Smoke job:

- Job: `job-jspace-acr-smoke`
- Image pull/auth: success via user-assigned managed identity and AcrPull.
- Execution: `job-jspace-acr-smoke-9b9wb4z`
- Status: `Succeeded`
- Command: `python -m pytest tests/ -q`
- Logs summary: `41 passed, 2 warnings in 4.93s`
- No model download/inference occurred.

Phase 0.5:

- Job: `job-jspace-phase05-acr`
- First execution: `job-jspace-phase05-acr-i5qd9yo`
  - Status: `Succeeded` at job level, but internal model loading failed due `/mnt/models` permission error.
  - Fix: reran with writable cache env: `HF_HOME=/tmp/models/huggingface`, `TRANSFORMERS_CACHE=/tmp/models/huggingface`, `RESULTS_DIR=/tmp/results`; increased resources to `cpu=4`, `memory=16Gi`.
- Successful execution: `job-jspace-phase05-acr-i110lnu`
- Status: `Succeeded`
- Logs summary:
  - `jacobian-lens package installed: False`
  - pre-fitted lenses: not found locally
  - model loading check attempted: true
  - both models loaded successfully on `cuda:0`, GPU `Tesla T4`, GPU memory `16.70 GB`
  - actual tiny fitting attempted: no
  - actual tiny fitting success: not attempted
- Output path inside container: `/workspace/results/runs/20260708_153600`

Phase 1 dry-run:

- Job: `job-jspace-phase1-dryrun-acr`
- Execution: `job-jspace-phase1-dryrun-acr-v0j1bkd`
- Status: `Succeeded`
- Command: `python experiments/phase1_depth_gradient.py --dry-run`
- Logs summary:
  - models: DeepSeek-R1-Distill-Qwen-1.5B and Qwen2.5-Math-1.5B
  - task families: arithmetic, synthetic_relation, factual_counterfactual
  - depths: 1,2,3
  - conditions: strict_answer_only, visible_cot, r1_style_thinking
  - total cells: 54
  - no real generation
- Output path inside container: `/workspace/results/runs/20260708_154052`

Small Phase 1 pilot:

- Job: `job-jspace-phase1-pilot-acr`
- Execution: `job-jspace-phase1-pilot-acr-lhuvwbf`
- Status: `Succeeded`
- Command:
  - `python experiments/phase1_depth_gradient.py --models deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B --task-families arithmetic --depths 1,2,3 --conditions strict_answer_only,visible_cot,r1_style_thinking --max-new-tokens 64 --items-per-cell 1`
- Logs summary:
  - model loaded on `cuda:0`, GPU `Tesla T4`
  - task family: arithmetic only
  - depths: 1,2,3
  - conditions: strict_answer_only, visible_cot, r1_style_thinking
  - pilot completed, results written
  - example cell metrics observed in logs:
    - depth 1 strict_answer_only accuracy 1.000, no-CoT valid 1.000
    - depth 2 visible_cot accuracy 1.000, no-CoT valid 0.000
    - depth 3 r1_style_thinking accuracy 1.000, no-CoT valid 0.000
- Output path inside container: `/workspace/results/runs/20260708_154330`

Important scientific note:

- The small Phase 1 pilot is behavioral only.
- It is not J-space evidence and does not prove Plan A.

Scripts:

- Added `infra/azure/scripts/06_run_job_acr_mi.sh` for ACR image jobs with user-assigned managed identity and AcrPull.
- Added `.azure_*.tmp` to `.gitignore` so local Azure context files are not committed.

## 2026-07-09 — Azure Files persistence attempt blocked by shared-key policy

Goal:

- Configure persistent result export/storage before broader Phase 1 runs.
- Use Azure Files as the first persistence path for Container Apps Jobs.

Storage resources attempted:

- Storage account 1: `stjspaceobssea07090835`
  - resource group: `rg-jspace-observation-sea`
  - location: `southeastasia`
  - provisioning: `Succeeded`
  - `allowSharedKeyAccess`: `False`
  - Created file share through ARM management plane: `jspace-results`
  - Data-plane key operations failed.
- Storage account 2: `stjspacefiles0709085305`
  - created with explicit `--allow-shared-key-access true`
  - provisioning: `Succeeded`
  - `allowSharedKeyAccess`: still `False`
  - Data-plane key operations failed.

Exact storage errors:

- `KeyBasedAuthenticationNotPermitted`
- Message: `Key based authentication is not permitted on this storage account.`

Container Apps environment storage:

- Registered `jspace-results-storage` initially, but storage was not usable because Azure Files key-based auth was blocked.
- Storage smoke execution:
  - job: `job-jspace-storage-smoke-acr`
  - execution: `job-jspace-storage-smoke-acr-1s1g5d8`
  - status: stuck/running, then stopped
  - likely cause: Azure Files mount blocked/hanging due unusable storage key path
- Cleanup:
  - deleted `job-jspace-storage-smoke-acr`
  - removed `jspace-results-storage` from Container Apps environment
  - storage accounts retained for audit; no environment storage is currently registered

Script update:

- Patched `infra/azure/scripts/06_run_job_acr_mi.sh` to support:
  - `ENABLE_RESULTS_MOUNT`
  - `STORAGE_MOUNT_NAME`
  - `RESULTS_MOUNT_PATH`
  - `RESULTS_DIR=/mnt/results` when mount is enabled
  - volume + volumeMount ARM payload when storage is available

Current persistence status:

- Azure Files share/mount persistence: failed due organization/subscription policy disabling shared-key access.
- Persistent pilot rerun: not attempted.
- Optional persistent Phase 0.5 rerun: not attempted.
- No local model execution occurred.

Next action:

- Choose an alternative persistence strategy:
  1. Ask admin to allow Azure Files shared-key access for this storage account / project scope; or
  2. Switch to Azure Blob output upload using managed identity / Azure CLI SDK inside the container; or
  3. Use Container Apps supported identity-based storage if available in this tenant/CLI version.
- Do not run broader experiments until results can be persisted.

## 2026-07-09 — Blob persistence via managed identity succeeded

Code and image:

- Added Blob export support:
  - `src/jspace_observation/blob_export.py`
  - `scripts/blob_export_smoke.py`
  - `azure-identity`, `azure-storage-blob` dependencies
  - Phase 0.5 / Phase 1 `--require-blob-export` hooks
  - ACR job env support for Blob variables
- Local tests: `43 passed, 2 warnings`
- ACR build run: `cm3`
- New ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:afd647a6b53e`
- Digest: `sha256:ecb9a70dc9e11eb59e3ba0f9777d19bfbf7a5e2b6567e7993f586be6d44e84f3`

Blob storage:

- Storage account used: `stjspacefiles0709085305`
- Blob container: `jspace-results`
- Shared key used: no
- `allowSharedKeyAccess`: `False`
- Managed identity: `id-jspace-aca-acrpull-sea`
- Managed identity role: `Storage Blob Data Contributor`
- Current signed-in user role for verification: `Storage Blob Data Reader`

Blob smoke:

- Job: `job-jspace-blob-smoke-acr`
- First execution: `job-jspace-blob-smoke-acr-qalz3t9`
  - Status: `Failed`
  - Error: `ModuleNotFoundError: No module named 'jspace_observation'`
  - Fix: add `src` to `sys.path` in `scripts/blob_export_smoke.py` and pass `PYTHONPATH=/workspace/src`
- Successful execution: `job-jspace-blob-smoke-acr-o7kl7s2`
- Status: `Succeeded`
- Blob prefix: `smoke/20260709T013310Z`
- Verified blob: `smoke/20260709T013310Z/smoke.txt`

Persistent Phase 1 pilot:

- Job: `job-jspace-phase1-pilot-blob-acr`
- Execution: `job-jspace-phase1-pilot-blob-acr-9voxpdm`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot/20260709T014336Z`
- Files uploaded:
  - `phase1_eval_records.jsonl`
  - `phase1_generations.jsonl`
  - `phase1_metrics.csv`
  - `phase1_summary.md`
- Download/review location (not committed): `C:\Users\alanjiao\.copilot\session-state\41000e7a-c709-4082-9452-b0c72ff481d8\files\azure_blob_pilot_review`

Pilot review:

- Expected files present: yes, 4 files.
- Cells completed: 9 (depths 1/2/3 x strict_answer_only, visible_cot, r1_style_thinking).
- Parse/eval records present: yes.
- Metrics sanity:
  - strict_answer_only no-CoT validity was reported as 1.0 for depths 1/2/3.
  - visible_cot / r1_style_thinking no-CoT validity was often 0.0 for depth 2/3 as expected.
- Obvious bug before scaling:
  - strict_answer_only outputs contain visible reasoning phrases such as `Step-by-step explanation` and `follow these steps`, but current no-CoT validator did not flag them.
  - The pilot therefore reveals a validation bug; strict no-CoT validity is overestimated.
  - Numeric parsing can be misled by truncated reasoning outputs and last-number selection.
- Scientific conclusion: infrastructure + behavioral sanity only. No J-space claim.

Optional persistent Phase 0.5:

- Not attempted. Existing non-persistent Phase 0.5 already succeeded; next priority is no-CoT validation correctness before scaling.

Next action:

- Fix no-CoT visible-reasoning validation before any broader Phase 1 run.
- Use `JSPACE_RESULTS_ROOT=/workspace/results` for future runs to avoid doubled path `/workspace/results/runs/runs/...`.

## 2026-07-09 — Tighten strict answer-only prompting and rerun minimal pilot

Goal:

- Keep validator strict.
- Add a direct answer-prefill strict variant and condition-specific decoding.
- Rerun the same minimal persistent pilot only.

Code changes:

- Added `strict_answer_only_prefill_answer` condition.
- Added `construct_prefill_answer_prompt()`.
- Tightened existing `strict_answer_only` prompt with explicit no-explanation/no-steps/no-reasoning instruction.
- Added condition-specific decoding metadata:
  - `strict_answer_only`: `max_new_tokens=12`, `temperature=0`, greedy, profile `strict_empty_think_answer_only_max12`
  - `strict_answer_only_prefill_answer`: `max_new_tokens=8`, `temperature=0`, greedy, profile `strict_prefill_answer_only_max8`
  - `visible_cot` and `r1_style_thinking`: unchanged default budget/profile
- Added reasoning markers for `alright`, `hmm`, and `wait` after first strictfix run exposed those as leakage markers.

Tests:

- Command: `python -m pytest tests/ -q`
- Result before extra marker pass: `60 passed, 2 warnings`
- Result after extra marker pass: `62 passed, 2 warnings`

ACR builds:

- Build run `cm5`: image `acrjspaceobssea0708231738.azurecr.io/j-space-observation:b91bc335caf1`
- Digest `cm5`: `sha256:97c43f11d0bdc409bd09e9c8f904ceeafb7150d0fcbd14e348dfb13a376c7aa6`
- Build run `cm6`: image `acrjspaceobssea0708231738.azurecr.io/j-space-observation:9b5895db173f`
- Digest `cm6`: `sha256:267e422baaad24b577ac103af9c9ca2af56295780eaa0804161aa4ff6d4fe189`

First strictfix rerun:

- Job: `job-jspace-p1-strictfix`
- Execution: `job-jspace-p1-strictfix-sq17fi0`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot-strictfix/20260709T024358Z`
- Result:
  - `strict_answer_only` remained no-CoT invalid for all depths.
  - `strict_answer_only_prefill_answer` improved visible reasoning on depth 1 but exposed new marker leaks (`Alright`, `Wait`) on deeper items.

Final strictfix2 rerun:

- Job: `job-jspace-p1-strictfix2`
- Execution: `job-jspace-p1-strictfix2-1sjj2n5`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot-strictfix2/20260709T025356Z`
- Files uploaded:
  - `phase1_eval_records.jsonl`
  - `phase1_generations.jsonl`
  - `phase1_metrics.csv`
  - `phase1_summary.md`

Final strictfix2 review:

- Cells completed: 12 (depths 1/2/3 x strict_answer_only, strict_answer_only_prefill_answer, visible_cot, r1_style_thinking).
- `strict_answer_only`:
  - no-CoT valid rate: `0.0000` for depths 1/2/3
  - visible reasoning marker rate: `1.0000` for depths 1/2/3
  - accuracy: `0.0000` for depths 1/2/3
- `strict_answer_only_prefill_answer`:
  - depth 1: no-CoT valid `1.0000`, visible reasoning marker `0.0000`, parse ambiguous `0.0000`, accuracy `0.0000`
  - depth 2: no-CoT valid `0.0000`, visible reasoning marker `1.0000`, parse valid `0.0000`, accuracy `0.0000`
  - depth 3: no-CoT valid `0.0000`, visible reasoning marker `1.0000`, parse ambiguous `0.0000`, accuracy `0.0000`
- parse_ambiguous_rate:
  - all original strict_answer_only rows: `1.0000`
  - all visible_cot / r1_style rows: `1.0000`
  - strict_answer_only_prefill_answer rows: `0.0000`
- representative strict outputs:
  - `strict_answer_only`: still emits `Step-by-step explanation`
  - `strict_answer_only_prefill_answer` depth 1: `7 + 5 = \boxed` (no visible reasoning, but incomplete/wrong)
  - `strict_answer_only_prefill_answer` depth 2: `__________\n\nAlright, so I have` (flagged invalid)
  - `strict_answer_only_prefill_answer` depth 3: `\boxed{12}\n\nWait,` (flagged invalid)

Decision:

- Direct `Answer:` prefill reduces visible reasoning for the easiest item but does not establish a useful strict answer-only condition.
- Tiny token budget causes incomplete/wrong answers.
- The model still leaks visible reasoning on harder arithmetic even with direct answer prefill.
- Do not broaden Phase 1 yet.
- Next step should try a different strict decoding/prompting strategy, e.g. stop criteria around newline/explanation markers or a post-processing experiment clearly labeled as post-processed.
- This remains behavioral/infrastructure sanity only. No J-space claim.

## 2026-07-09 — Raw-vs-postprocessed answer-only pilot

Goal:

- Stop trying prompt-only variants in this round.
- Add an explicitly labeled raw-vs-postprocessed condition.
- Preserve raw output and report raw no-CoT validity separately from postprocessed answer validity.

Code changes:

- Added `src/jspace_observation/postprocess.py`.
- Added `strict_answer_only_postprocessed` condition.
- Added postprocessing fields:
  - `raw_output_before_postprocess`
  - `postprocessed_output`
  - `postprocessing_applied`
  - `postprocessing_strategy`
  - `postprocessing_reason`
  - `postprocessing_warning`
  - `raw_no_cot_valid`
  - `postprocessed_no_cot_valid`
  - `postprocessed_answer_like`
  - `eval_output_used`
- Added metrics:
  - `raw_no_cot_valid_rate`
  - `postprocessed_no_cot_valid_rate`
  - `postprocessing_applied_rate`
  - `postprocessing_success_rate`
  - `postprocessing_warning_rate`
  - `accuracy_raw`
  - `accuracy_postprocessed`
- Added unit tests for explicit answer extraction, boxed extraction, incomplete boxed warning, reasoning-marker truncation, and entity final-answer extraction.

Tests:

- Command: `python -m pytest tests/ -q`
- Result after postprocessing implementation: `68 passed, 2 warnings`
- Result after bug fix / final run: local tests remained passing before build; final code is covered by the added tests.

ACR image:

- Build run `cm7`: image `acrjspaceobssea0708231738.azurecr.io/j-space-observation:a15575e7dbad`
- Build run `cm8`: final image `acrjspaceobssea0708231738.azurecr.io/j-space-observation:9342ef130d46`
- Digest `cm8`: `sha256:3fc9e9d58b0ce6d5ea8a260cb7c172aa7cebfbe31427f94ee8cdae8d3b2a9ed1`

First postprocess pilot attempt:

- Job: `job-jspace-p1-postprocess`
- Execution: `job-jspace-p1-postprocess-uooxev9`
- Status: `Failed`
- Error: `TypeError: create_eval_record() got multiple values for keyword argument 'eval_output_used'`
- Fix: removed duplicate `eval_output_used` from the postprocessing record expansion.

Final postprocess pilot:

- Job: `job-jspace-p1-postprocess`
- Execution: `job-jspace-p1-postprocess-gor0o1r`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot-postprocess/20260709T044224Z`
- Files uploaded:
  - `phase1_eval_records.jsonl`
  - `phase1_generations.jsonl`
  - `phase1_metrics.csv`
  - `phase1_summary.md`

Review:

- Cells completed: 12.
- `strict_answer_only_prefill_answer`
  - raw/no-postprocess condition
  - no-CoT valid rates: depth 1 `1.0000`, depth 2 `0.0000`, depth 3 `0.0000`
  - accuracy: `0.0000` all depths
- `strict_answer_only_postprocessed`
  - raw no-CoT valid rate: `0.0000` all depths
  - postprocessed no-CoT valid rate: `1.0000` all depths
  - postprocessing applied rate: `1.0000` all depths
  - postprocessing success rate: depth 1 `1.0000`, depth 2 `0.0000`, depth 3 `1.0000`
  - postprocessing warning rate: depth 1 `0.0000`, depth 2 `1.0000`, depth 3 `0.0000`
  - accuracy_raw: depth 1 `1.0000`, depth 2 `0.0000`, depth 3 `0.0000`
  - accuracy_postprocessed: depth 1 `1.0000`, depth 2 `0.0000`, depth 3 `0.0000`
- Representative raw/postprocessed outputs:
  - depth 1 raw: `7 + 5 = \boxed{12}\n\nWait...`; postprocessed: `\boxed{12}`; correct after postprocess
  - depth 2 raw: `__________\n\nAlright...`; postprocessed: `__________`; no answer-like span
  - depth 3 raw: `\boxed{12}\n\nWait...`; postprocessed: `\boxed{12}`; wrong answer
- `visible_cot` and `r1_style_thinking` remain raw-output evaluation conditions.

Scientific boundary:

- Postprocessed answer validity does not imply raw no-CoT compliance.
- Raw output still leaks visible reasoning under the postprocessed condition.
- This is an evaluation/postprocessing sanity check only, not evidence of hidden reasoning or J-space.

Decision:

- Postprocessing can recover a clean/correct answer for the easiest arithmetic item.
- It does not establish strict no-CoT generation.
- Do not use postprocessed output as proof of no-CoT.
- Next step: decide whether to develop raw stop-sequence generation controls or keep postprocessing as a separate answer-recovery analysis only.

## 2026-07-09 — Harden no-CoT validation and parse warnings

Goal:

- Fix strict-answer-only validation before any broader Phase 1 run.
- Keep the rerun scope minimal: one model, arithmetic only, depths 1/2/3, three conditions, one item per cell.

Code changes:

- `src/jspace_observation/no_cot.py`
  - Added explicit violation reasons.
  - Added detection for reasoning headings, stepwise markers, explanation markers, multi-line reasoning, and excessive answer-only length.
  - `no_cot_validity` now applies only to strict answer-only methods; visible_cot and r1_style_thinking get `no_cot_validity = null`.
- `src/jspace_observation/eval_parsing.py`
  - Added `parse_ambiguous`, `parse_strategy`, `candidate_answers`, and `answer_format_warning`.
  - Numeric parser records when last-number extraction is used.
- `experiments/phase1_depth_gradient.py`
  - Generation/eval records now include no-CoT violation reasons and parser ambiguity fields.
  - Metrics now include parse ambiguity rate, visible reasoning marker rate, answer format warning rate, and condition-appropriate no-CoT validity.
  - Summary now includes validation warnings.
- Tests added/updated for known false negatives and ambiguous parsing.

Local tests:

- Command: `python -m pytest tests/ -q`
- Result: `54 passed, 2 warnings`

ACR image:

- Build run: `cm4`
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:937288cfb8ef`
- Digest: `sha256:c3dcbdd7360ff1f1462263446ee8865132dd854df3a29f4f57b8e7d6ae348094`

Azure rerun:

- Job: `job-jspace-p1-validator`
- Execution: `job-jspace-p1-validator-xkqro3f`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot-validator/20260709T022001Z`
- Files uploaded:
  - `phase1_eval_records.jsonl`
  - `phase1_generations.jsonl`
  - `phase1_metrics.csv`
  - `phase1_summary.md`

Rerun validation review:

- Cells completed: 9.
- strict_answer_only no-CoT valid rate:
  - depth 1: `0.0000`
  - depth 2: `0.0000`
  - depth 3: `0.0000`
- strict_answer_only visible reasoning marker rate:
  - depth 1: `1.0000`
  - depth 2: `1.0000`
  - depth 3: `1.0000`
- parse_ambiguous_rate: `1.0000` for all 9 cells.
- answer_format_warning_rate: `1.0000` for all 9 cells.
- Summary warning counts:
  - strict_answer_only no-CoT invalid count: `3/3`
  - strict_answer_only visible reasoning marker count: `3/3`
  - parse ambiguous count: `9/9`

Decision:

- Validator now correctly flags the known strict-answer-only visible reasoning false negatives.
- Accuracy and no-CoT compliance are separated.
- Parser ambiguity is explicit rather than hidden.
- Do not expand the run yet; review whether prompts/decoding should be tightened to reduce strict-answer-only reasoning leakage.
- Scientific conclusion remains infrastructure + behavioral sanity only. No J-space or hidden reasoning claim.

## 2026-07-08 — Local validation sequence
- Latest commits:
  - `00349b7 Fix strict no-CoT prefill and Phase 1 defaults`
  - `30f770c Record scaffold sync verification`
  - `ff6a351 Implement Phase 0.5 and Phase 1 executable scaffold`
- Test result: `41 passed, 2 warnings`.
- Phase 0.5 availability/model-loading check completed after replacing non-ASCII runtime status symbols with ASCII-safe labels.
- Phase 0.5 output directory: `results/runs/20260708_181325`
- Phase 0.5 summary path: `results/runs/20260708_181325/phase0_5_summary.md`
- Phase 0.5 findings:
  - Pre-fitted lenses found locally/configured: `false`
  - jacobian-lens installed/importable: `false` / `false`
  - Model loading attempted: `true`
  - Model loading success for all models: `false`
  - Model loading failure reason: `accelerate` is required for `device_map`
  - Actual tiny fitting attempted: `no`
  - Actual tiny fitting success: `not attempted`
- Phase 1 dry-run result:
  - Models: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`, `Qwen/Qwen2.5-Math-1.5B`
  - Task families: `arithmetic`, `synthetic_relation`, `factual_counterfactual`
  - Depths: `1`, `2`, `3`
  - Conditions: `strict_answer_only`, `visible_cot`, `r1_style_thinking`
  - Total cells: `54`
  - No model download/generation was performed by dry run.

Azure:

- Azure resources created: none.

## 2026-07-08 — Strict no-CoT and Phase 0.5 clarification fixes

Action:

- Moved R1-Distill strict no-CoT empty-think prefill after the base prompt and before an `Answer:` cue:
  - `{base_prompt}`
  - `<think>\n</think>`
  - `Answer:`
- Added `r1_style_thinking` to the default Phase 1 conditions.
- Clarified Phase 0.5 script status as an availability/model-loading check only.
- Clarified Phase 0.5 summary fields for pre-fitted lens search, jacobian-lens availability, model loading, and actual tiny fitting attempted/success.

Test command:

- `python -m pytest tests/ -v`
- Test result: `41 passed, 2 warnings`

Azure:

- No Azure resources were created in this step.

## Azure ACR managed-identity job - 2026-07-10T13:57:22Z

- Command: `bash infra/azure/scripts/06_run_job_acr_mi.sh`
- Job: job-jspace-p1-criteria-val
- Image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:f94e889ef608
- Registry: acrjspaceobssea0708231738.azurecr.io via user-assigned managed identity
- Container command: `python experiments/phase1_depth_gradient.py --models deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B --task-families arithmetic --depths 1,2,3 --conditions strict_answer_only_prefill_answer,strict_answer_only_stopped,strict_answer_only_postprocessed,visible_cot,r1_style_thinking --max-new-tokens 64 --items-per-cell 1 --require-blob-export && echo "=== PHASE1 SUMMARY ===" && find /workspace/results/runs -name phase1_summary.md -print -exec cat {} \; && echo "=== PHASE1 METRICS CSV ===" && find /workspace/results/runs -name phase1_metrics.csv -print -exec cat {} \;`

## 2026-07-10 — limited Phase 1 criteria-validation run

Approval and scope:

- One limited validation run was explicitly approved.
- Model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- Task family: `arithmetic`.
- Depths: `1,2,3`.
- Conditions: `strict_answer_only_prefill_answer`, `strict_answer_only_stopped`, `strict_answer_only_postprocessed`, `visible_cot`, `r1_style_thinking`.
- Items per cell: `1`.
- Total cells: `15`.
- No local model inference, model download, J-lens fitting, activation patching, or scope expansion occurred.

Local gate:

```text
python -m pytest tests\ -q
92 passed, 2 warnings
```

ACR provenance:

- Source commit: `f94e889ef6089aab8f651a2d14c42341440625a3`.
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:f94e889ef608`.
- Build run: `cma`.
- Build status: `Succeeded`.
- Digest: `sha256:f27cc0e4cea0ae9569dbb384598fb391f3b923022ce9257f8301684c9dc23806`.

Infrastructure verification:

- Environment: `cae-jspace-observation-sea-vnet2`; provisioning state `Succeeded`.
- Workload profile: `gpu-t4 / Consumption-GPU-NC8as-T4`.
- ACA subnet: `snet-aca-jspace-sea-v2`.
- Managed identity: `id-jspace-aca-acrpull-sea`.
- Roles confirmed: `AcrPull`, `Storage Blob Data Contributor`.
- Storage public network access: `Disabled`.
- Storage shared-key access: `False`.
- No key, SAS, GHCR, old environment, or public Storage route was used.

Setup errors before job creation:

1. `bash` resolved to the Windows WSL launcher, but no WSL distribution was installed. No Azure job was created.
2. Git Bash initially rewrote the Azure environment resource ID to a `C:/Program Files/Git/...` path. Azure returned `LinkedInvalidPropertyId`; no job was created. Setting `MSYS_NO_PATHCONV=1` and `MSYS2_ARG_CONV_EXCL=*` fixed this.
3. The requested name `job-jspace-p1-criteria-validation` is 33 characters; Container Apps Jobs allow at most 32. Azure returned `ContainerAppInvalidName`; no job was created. The closest valid name, `job-jspace-p1-criteria-val`, was used.

Successful execution:

- Job: `job-jspace-p1-criteria-val`.
- Execution: `job-jspace-p1-criteria-val-6s8p15p`.
- Start: `2026-07-10T13:57:24Z`.
- End: `2026-07-10T14:00:15Z`.
- Status: `Succeeded`.
- Execution count for this job: `1`.
- Blob prefix: `phase1-pilot-criteria-validation/20260710T135655Z`.
- Container output directory: `/workspace/results/runs/runs/20260710_135907`.
- Exported files:
  - `phase1_eval_records.jsonl`
  - `phase1_generations.jsonl`
  - `phase1_metrics.csv`
  - `phase1_summary.md`
- Blob export: `4 files`, complete.
- Generation records: `15`.

Depth-wise classifications:

| Depth | Raw strict | Stopped intervention | Postprocessed utility |
|---|---|---|---|
| 1 | `surface_answer_only_but_task_failed` | `stopped_intervention_usable` | `postprocessed_answer_recovery_usable` |
| 2 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_warning_high` |
| 3 | `raw_strict_not_established` | `stopped_surface_compliant_but_task_failed` | `postprocessed_answer_recovery_usable` |

Criteria summary:

- Raw depth 1 passed raw validity, visible-marker, parse-valid, and parse-ambiguity criteria; it failed format-warning and absolute/relative accuracy criteria.
- Raw depth 2 passed ambiguity and format-warning criteria; it failed raw validity, visible-marker, parse-valid, and accuracy criteria.
- Raw depth 3 passed parse, ambiguity, format-warning, and relative-accuracy criteria; it failed raw validity and visible-marker criteria.
- Stopped depth 1 passed all four criteria.
- Stopped depth 2 passed stopped validity only; it failed stop success, parse validity, and accuracy.
- Stopped depth 3 passed stopped validity, stop success, and parse validity; it failed accuracy.
- Postprocessed depth 1 passed all four criteria.
- Postprocessed depth 2 passed postprocessed validity and non-degradation; it failed recovery success and warning rate.
- Postprocessed depth 3 passed all four preregistered criteria, including `0.0000 >= 0.0000` accuracy non-degradation.

Scientific boundary:

- Classifications are behavioral and operational only.
- Stop-controlled validity is intervention-controlled, not spontaneous no-CoT.
- Postprocessed validity is not raw no-CoT.
- No hidden-reasoning, internal-workspace, or J-space claim is made.
- No rerun or scale increase is authorized.

## 2026-07-10 — Phase 1 branch gate hardening

Purpose:

- Correct the criteria weaknesses found by the completed 15-cell validation pilot without collecting new data.
- Preserve the completed Azure execution and Blob artifacts as historical outputs under the earlier registered criteria.

Code and report changes:

- Added `accuracy_postprocessed >= 0.50` as a hard gate in addition to non-degradation.
- Added visible-CoT baseline validation: `visible_cot_n >= 3`, parse-valid rate `>= 0.80`, and accuracy `> 0`.
- Invalid or unavailable visible-CoT baselines now make the relative gate `NA` and add a failure reason.
- Added `n >= 3` for formal branch success and branch-specific `pilot_only` labels.
- Clear failures remain visible below the minimum sample size.
- Added sample-size, absolute-floor, baseline-validity, relative-gate, provisional, and not-applicable fields to the classification table.
- Added mandatory sample-size, visible-CoT baseline, and postprocessing absolute-floor warnings.

Historical metric regression:

- The completed Blob summary is unchanged and remains an audit artifact of the earlier criteria.
- Under the hardened deterministic classifier, depth-1 stopped success would be `stopped_intervention_pilot_only` because `n=1`.
- Under the hardened deterministic classifier, depth-1 postprocessed success would be `postprocessed_utility_pilot_only` because `n=1`.
- The depth-3 postprocessed `0 >= 0` case is now `postprocessed_surface_clean_but_task_failed`, not `postprocessed_answer_recovery_usable`.
- The matching visible-CoT rows in the pilot have `n=1`, so their relative gates are `NA`.

Local validation:

```text
python -m pytest tests\ -q
109 passed, 2 warnings
```

Execution boundary:

- Azure rerun performed: no.
- Model inference performed: no.
- Model downloaded: no.
- ACR rebuild performed: no.
- Experiment scale changed: no.
- Active environment remains `cae-jspace-observation-sea-vnet2`.
- Latest successful execution remains `job-jspace-p1-criteria-val-6s8p15p`.
- No hidden-reasoning or J-space claim is made.

## Azure ACR managed-identity job - 2026-07-10T15:28:44Z

- Command: `bash infra/azure/scripts/06_run_job_acr_mi.sh`
- Job: job-jspace-p1-n3-gates
- Image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:359643b7b5eb
- Registry: acrjspaceobssea0708231738.azurecr.io via user-assigned managed identity
- Container command: `python experiments/phase1_depth_gradient.py --models deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B --task-families arithmetic --depths 1,2,3 --conditions strict_answer_only_prefill_answer,strict_answer_only_stopped,strict_answer_only_postprocessed,visible_cot,r1_style_thinking --max-new-tokens 64 --items-per-cell 3 --require-blob-export && echo "=== PHASE1 SUMMARY ===" && find /workspace/results/runs -name phase1_summary.md -print -exec cat {} \; && echo "=== PHASE1 METRICS CSV ===" && find /workspace/results/runs -name phase1_metrics.csv -print -exec cat {} \;`

## 2026-07-10 — bounded Phase 1 n=3 validation

Authorization and scope:

- Run type: bounded minimum-evidence validation.
- Starting commit: `d1750a9d51e102c644933d8c41b7d65432f8bdfa`.
- Model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- Task family: `arithmetic`.
- Depths: `1,2,3`.
- Conditions: `strict_answer_only_prefill_answer`, `strict_answer_only_stopped`, `strict_answer_only_postprocessed`, `visible_cot`, `r1_style_thinking`.
- Configuration cells: `15`.
- Items per cell: `3`.
- Total observations: `45`.
- No second model, task family, depth, condition, or item above the approved count was added.

Parallel pre-run audits:

- Requested model: `gpt-5.6 soil`; actual model: `gpt-5.6-sol`; reasoning: `max`.
- Agents: `n3-method-audit`, `n3-code-audit`, `n3-azure-audit`.
- All three initially returned `NO-RUN` because arithmetic prompt capacity was `3/3/2`.
- Azure infrastructure itself passed; the helper was confirmed to create/update and automatically start the job.
- Alan explicitly approved one unique third depth-3 arithmetic prompt. No threshold or branch semantics changed.

Pre-run fix and local validation:

- Added `arith_3op_003`: `((9 - 3) * 4) + 2 = 26`.
- Made dry-run compute observations from real prompt capacity and fail on shortfall.
- Source commit: `359643b7b5eb8f95c13cca2e60fa753df8701282`.

```text
python -m pytest tests\ -q
111 passed, 2 warnings

configuration_cells = 15
items_per_cell = 3
total_observations = 45
```

ACR provenance:

- Build run: `cmb`.
- Status: `Succeeded`.
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:359643b7b5eb`.
- Digest: `sha256:004ec8bff66fbc8a23b122660aeb58914b2ee3cedfc5246429046eef252c9069`.
- `latest` points to the same digest.

Private infrastructure verification:

- Environment: `cae-jspace-observation-sea-vnet2`; state `Succeeded`.
- Workload profile: `gpu-t4 / Consumption-GPU-NC8as-T4`.
- Managed identity: `id-jspace-aca-acrpull-sea`.
- Roles: `AcrPull`, `Storage Blob Data Contributor`.
- Storage public network access: `Disabled`.
- Shared-key access: `False`.
- Blob private endpoint: `pe-stjspacefiles-blob-sea`; state `Succeeded`, connection `Approved`.
- Git Bash used `MSYS_NO_PATHCONV=1` and `MSYS2_ARG_CONV_EXCL=*`.

Execution:

- Job: `job-jspace-p1-n3-gates`.
- All execution IDs: `job-jspace-p1-n3-gates-02ilmgm`.
- Start: `2026-07-10T15:28:47Z`.
- End: `2026-07-10T15:32:31Z`.
- Status: `Succeeded`.
- Full execution attempts: `1`.
- Retry count: `0`.
- Failed execution IDs: none.
- Blob prefix: `phase1-limited-n3-gates/20260710T152820Z`.

Persistence and counts:

- `phase1_generations.jsonl`: `45` records.
- `phase1_eval_records.jsonl`: `45` records; `18` parse-ambiguous.
- `phase1_metrics.csv`: `15` data rows; every row has `n=3`; aggregate `sum(n)=45`.
- `phase1_summary.md`: branch table and mandatory warnings present.
- Blob upload: `4` files, complete.
- Answer-control classification rows: `9`.
- Stop-string distribution: `"\n\n"=3` at every stopped depth.

Visible-CoT baseline:

| Depth | n | Accuracy | Parse valid | Format warning | Baseline valid | Failure reason |
|---|---:|---:|---:|---:|---|---|
| 1 | 3 | 0.3333 | 1.0000 | 1.0000 | true | `NA` |
| 2 | 3 | 0.6667 | 1.0000 | 1.0000 | true | `NA` |
| 3 | 3 | 0.0000 | 1.0000 | 1.0000 | false | `visible_cot_accuracy_zero` |

Raw strict:

| Depth | Classification | Accuracy | Absolute | Relative | Criteria passed | Criteria failed | Criteria NA |
|---|---|---:|---|---|---|---|---|
| 1 | `raw_strict_not_established` | 0.6667 | pass | pass | n; parse valid; ambiguity; absolute; relative | raw validity; reasoning marker; format warning | none |
| 2 | `raw_strict_not_established` | 0.3333 | fail | fail | n; ambiguity; format warning | raw validity; reasoning marker; parse valid; absolute; relative | none |
| 3 | `raw_strict_not_established` | 0.0000 | fail | `NA` | n; ambiguity; format warning | raw validity; reasoning marker; parse valid; absolute | relative gate |

Stopped intervention:

| Depth | Classification | Validity | Stop success | Triggered | Accuracy | Absolute | Relative | Criteria passed | Criteria failed | Criteria NA |
|---|---|---:|---:|---:|---:|---|---|---|---|---|
| 1 | `stopped_intervention_usable` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | pass | pass | all | none | none |
| 2 | `stopped_intervention_not_useful` | 1.0000 | 0.3333 | 1.0000 | 0.3333 | fail | fail | n; validity | stop success; parse valid; absolute; relative | none |
| 3 | `stopped_intervention_not_useful` | 1.0000 | 0.3333 | 1.0000 | 0.0000 | fail | `NA` | n; validity | stop success; parse valid; absolute | relative gate |

Postprocessed utility:

| Depth | Classification | Validity | Success | Warning | Raw accuracy | Postprocessed accuracy | Non-degradation | Absolute | Criteria passed | Criteria failed | Criteria NA |
|---|---|---:|---:|---:|---:|---:|---|---|---|---|---|
| 1 | `postprocessed_answer_recovery_usable` | 1.0000 | 1.0000 | 0.0000 | 0.3333 | 1.0000 | pass | pass | all | none | none |
| 2 | `postprocessed_surface_clean_but_task_failed` | 1.0000 | 0.3333 | 0.6667 | 0.0000 | 0.3333 | pass | fail | n; validity; non-degradation | success; warning; absolute | none |
| 3 | `postprocessed_surface_clean_but_task_failed` | 1.0000 | 0.3333 | 0.6667 | 0.0000 | 0.0000 | pass (`0 >= 0`) | fail | n; validity; non-degradation | success; warning; absolute | relative gate |

Parallel post-run audits:

- Requested model: `gpt-5.6 soil`; actual model: `gpt-5.6-sol`; reasoning: `max`.
- Agents: `n3-artifact-audit`, `n3-classification-audit`, `n3-science-audit`.
- Classification audit: `PASS`; all nine rows independently recomputed with zero mismatches.
- Artifact count audit: generation/eval/metrics/Blob counts `PASS`.
- Record-level duplicate IDs, exact item membership, and raw/stopped/postprocessed field equality: `INCONCLUSIVE` because local Entra Blob access was blocked by private network rules. Metric-cell keys had zero duplicates and all nine source task IDs are unique.
- Scientific audit found no mechanistic overclaim. `sample_size_sufficient=true` means registered-gate sufficiency only, not statistical stability.

Operational errors and handling:

1. Pre-run audit found `3/3/2` prompt capacity. No Azure job existed. Fixed with the explicitly approved unique depth-3 item and revalidated `45` observations.
2. The first log command omitted the CLI-required container name. Queried replica `job-jspace-p1-n3-gates-02ilmgm-dxdmc` and container `main`, then retrieved logs without rerunning.
3. Local Entra Blob listing was blocked by Storage network rules. No key, SAS, or network-policy change was attempted.
4. Three stopped classification log lines are invalid outer JSON because of escaped `"\n\n"` values; raw log text retained all lines and the audit recovered them.

Scientific boundary:

- `n=3` is the registered minimum only; it does not demonstrate stability, robustness, or generalizability.
- Branch classifications are behavioral and operational.
- Raw strict success would not prove hidden reasoning; raw strict was not established here.
- Stopped depth-1 usability is intervention utility, not spontaneous no-CoT.
- Postprocessed depth-1 usability is answer-recovery utility, not raw no-CoT.
- No hidden-reasoning, internal-workspace, genuine invisible-reasoning, or J-space claim is made.

## Azure ACR managed-identity job - 2026-07-11T01:04:00Z

- Command: `bash infra/azure/scripts/06_run_job_acr_mi.sh`
- Job: job-jspace-p1-record-audit
- Image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:9537ed8e0b5d
- Registry: acrjspaceobssea0708231738.azurecr.io via user-assigned managed identity
- Container command: `python scripts/audit_phase1_blob_run.py --storage-account "$JSPACE_BLOB_ACCOUNT" --container "$JSPACE_BLOB_CONTAINER" --source-prefix "$JSPACE_AUDIT_SOURCE_PREFIX" --audit-output-prefix "$JSPACE_AUDIT_OUTPUT_PREFIX" --download-dir /tmp/jspace-record-audit --require-exact-generation-count 45 --require-exact-eval-count 45 --expected-items-per-cell 3 --emit-ambiguous-records --upload-audit-report`

## 2026-07-11 — read-only bounded n=3 record audit

Authorization and boundaries:

- Audit existing source prefix
  `phase1-limited-n3-gates/20260710T152820Z`.
- Read source through the existing private endpoint and managed identity.
- Write only under
  `phase1-audits/n3-gates-20260710T152820Z/20260711T010339Z`.
- No model loading, model generation, new observation, threshold change, parser
  retuning, source overwrite, key, SAS, or public-network change.

Parallel pre-run design audits:

- Requested model: `gpt-5.6 soil`; actual model: `gpt-5.6-sol`; reasoning:
  `max`.
- Agents: `record-schema-audit`, `record-metrics-audit`,
  `record-ambiguity-audit`.
- Pairing key selected:
  `model_name, task_family, depth, condition, task_id`.
- The metric audit identified `avg_latency_s` as requiring generation records;
  the audit therefore used paired generation/eval artifacts.
- The ambiguity audit established that flagged-only review can identify
  overflags but cannot exclude underflags among unflagged records.

Implementation and review:

- Starting commit: `a4bbf8911e0f758eb10230e52c6e953ef8df9cee`.
- Audit implementation commit:
  `9537ed8e0b5da95b68714b73fa11236b48ee046a`.
- Added `record_audit.py`, Blob audit CLI, 28 audit tests, and CPU audit helper
  guards.
- Full test command: `python -m pytest tests\ -q`.
- Result: `139 passed, 2 warnings`.
- Read-only implementation reviews: `record-implementation-review` and
  `record-fix-review`, both `gpt-5.6-sol/max`.
- Review fixes covered strict JSONL/CSV syntax, key types, registered answers,
  parser aliases, summary multiplicity, zero-specific D3 regression,
  bidirectional prefix isolation, direct CLI import, CPU guard, selected-output
  transformation replay, malformed-key handling, and empty JSONL.

ACR:

- Build command: `az acr build` from implementation commit.
- Build run: `cmc`; status `Succeeded`.
- Image:
  `acrjspaceobssea0708231738.azurecr.io/j-space-observation:9537ed8e0b5d`.
- Digest:
  `sha256:90adfc1b6be6fbb7a17a878bed7970ffd71c62b72263a36b41110ba6f19b169b`.
- `latest` resolved to the same digest.

Private infrastructure:

- Environment: `cae-jspace-observation-sea-vnet2`; state `Succeeded`.
- CPU profile: `Consumption`.
- GPU profile remained available but was not used.
- Managed identity: `id-jspace-aca-acrpull-sea`.
- Roles: `AcrPull` on ACR and `Storage Blob Data Contributor` on the Blob
  account.
- Storage public network access: `Disabled`.
- Shared-key access: `False`.
- Private endpoint `pe-stjspacefiles-blob-sea`: `Succeeded / Approved`.

Execution:

- Job: `job-jspace-p1-record-audit`.
- Suggested `1 CPU / 4Gi` create request failed before job/execution creation
  because Consumption requires a supported paired shape.
- Successful shape: `2 CPU / 4Gi`; GPU: none.
- All execution IDs: `job-jspace-p1-record-audit-d9q5uy8`.
- Start: `2026-07-11T01:03:59Z`.
- End: `2026-07-11T01:05:25Z`.
- Status: `Succeeded`.
- Execution retries: `0`.
- The helper automatically started the sole execution; no duplicate start was
  issued.

Source manifest:

| Artifact | Bytes | Lines | SHA-256 | ETag | Unchanged |
|---|---:|---:|---|---|---|
| `phase1_generations.jsonl` | 138133 | 45 | `b45c972af6f8a2be771e308d943ff793bdafd44c486a4eae9ea8a4e7f1ec11a0` | `"0x8DEDE985A8ECD24"` | true |
| `phase1_eval_records.jsonl` | 84824 | 45 | `57aee97ef98a9be14e489bf6aa4a6e09a80fd5ceedb2df8fadc8d991be98538b` | `"0x8DEDE985A8CF8AF"` | true |
| `phase1_metrics.csv` | 4223 | 16 | `14df044221ed34320d797c66aee17948e756aacb316c882e36cdf84ab496a3d1` | `"0x8DEDE985A918BD4"` | true |
| `phase1_summary.md` | 15814 | 98 | `fcc8a33efd8462e39b4f3d9fb704379bf740e0fc2cb7593d087f6de0b4c76173` | `"0x8DEDE985A933949"` | true |

Audit outputs:

- Eight files uploaded with `overwrite=False`: manifest, JSON/Markdown report,
  pairing mismatches, ambiguous records, deterministic ambiguous review,
  recomputed metrics, and recomputed classifications.
- Source prefix was not modified.

Deterministic result:

- Overall: `completed_clean`.
- JSONL syntax: generation `45/45`, eval `45/45`; no invalid or blank lines.
- Pairing: 45/45; duplicate and one-sided keys `0`.
- Membership: 15/15 cells; each has three registered unique items.
- Registered-answer mismatches: `0`.
- Common-field and selected-output transformation mismatches: `0`.
- Current parser and correctness replay mismatches: `0`.
- Metrics: `15/15` rows; max absolute difference `0.0`; no latency field was
  skipped.
- Branches: `9/9`; classification and criterion-list mismatches `0`.
- Depth-3 `0 >= 0` absolute-floor regression: `PASS`.

Parallel post-run reviews:

- Requested model: `gpt-5.6 soil`; actual model: `gpt-5.6-sol`; reasoning:
  `max`.
- Agents: `record-integrity-review`, `metrics-classification-review`,
  `ambiguous-review-a`, `ambiguous-review-b`, `science-boundary-review`.
- Record-integrity verdict: `PASS`, evidence-bounded.
- Metrics/classification verdict: classification `PASS`; independent
  row-by-row metrics inspection `INCONCLUSIVE` because recovered stdout
  contained aggregate comparison results rather than all 15 row payloads.
- Science review required completion of the then-pending documentation and the
  flagged-only underflag caveat; no mechanistic overclaim was found.

Ambiguous review and arbitration:

- Records reviewed independently: `18 / 18`.
- Category agreement: `17/18`; Cohen's kappa `0.6471`.
- Answer-status agreement: `17/18`; Cohen's kappa `0.9082`.
- Best-answer agreement: `18/18`.
- Exact issue-set agreement: `4/18`; mean Jaccard `0.7565`.
- Any field-level disagreement triggered arbitration: `14` records.
- Arbiter: `ambiguous-review-arbiter`, `gpt-5.6-sol/max`.
- Unresolved after arbitration: `0`.
- Final categories: 17 `parser_overflag`, one
  `true_multiple_candidate_ambiguity`.
- Final answer statuses: six correct, one incorrect, one ambiguous, ten with no
  answer.
- Mechanical stored parser/correctness consistency: `18/18`.
- Records 2 and 3 contain unique correct semantic claims missed by the
  last-number parser; this is evaluator limitation, not data corruption.
- Parser underflags among the other 27 records were not assessed.

Operational errors and handling:

1. `az acr run show --run-id` was unsupported. Existing build `cmc` was checked
   with `az acr task show-run`; no rebuild occurred.
2. `1 CPU / 4Gi` was rejected before job/execution creation. The valid
   `2 CPU / 4Gi` shape was used.
3. A local JMESPath polling expression was split by Windows command parsing.
   The Azure execution continued; no duplicate start occurred.
4. The completed replica was cleaned before direct log retrieval. The same
   execution's 43 rows were recovered from Log Analytics; no rerun occurred.
5. One large branch JSON console event was transport-split and reconstructed
   from two ordered Log Analytics rows.

Scientific boundary:

- The audit evaluates artifact integrity and evaluator consistency only.
- It generated no new behavioral evidence.
- `n=3` is not stability, robustness, or generalizability evidence.
- Stopped remains intervention-controlled.
- Postprocessed remains answer-recovery utility, not raw no-CoT.
- LLM review is audit opinion, not human ground truth.
- Flagged-only review cannot exclude underflags.
- No hidden-reasoning, internal-workspace, or J-space claim is made.

## 2026-07-13 — all-45 semantic audit protocol/tooling implementation

Scope:

- Froze protocol v1 before packet review.
- Added local, model-free packet construction, staged review validation,
  agreement, arbitration, confusion, material-impact, and audit-only
  sensitivity tooling.
- Added secure in-memory source export and a local finalizer.
- Preregistered clean-Git build attestation, stdlib-first import verification,
  exact source-byte evidence, immutable submission/seal revalidation, strict
  integer bindings, and atomic release-prefix reservation.
- Preserved the exact experimental target
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`; reviewer identity remains
  separately `gpt-5.6-sol` with reasoning effort `max`.

Execution boundary:

- Azure, ACR, and Blob commands executed: none.
- Model download/load/generation executed: none.
- Source artifacts opened or modified locally: none.
- Semantic review performed: none.
- Results claimed: none.
- Only synthetic local no-model tests are authorized for this implementation
  step.

Planned local validation:

- Run only model-free synthetic/unit tests and shell syntax checks.
- Do not open source records, run models, or execute Azure/ACR/Blob commands.
- This entry preregisters tooling and reports no semantic-audit result.

## 2026-07-15 — all-45 semantic audit image build

Protocol/build provenance:

- Initial preregistration commit:
  `68feeaee237fd9f1603093f2bdd282c7bde37c4e`.
- Build-control follow-up commit:
  `cfa99fc6e204db5cf1076a13a8975e13db226931`.
- The follow-up removed Docker/ACR-consumed `.dockerignore` and `.gitignore`
  from the runtime bundle while retaining clean-Git control.
- Local no-model validation: `217 passed, 2 warnings`.

ACR:

- Registry: `acrjspaceobssea0708231738`.
- Failed build run `cmd`: stopped during Docker attestation membership
  validation; no image was published.
- Successful build run `cme`.
- Image:
  `acrjspaceobssea0708231738.azurecr.io/j-space-observation:cfa99fc6e204`.
- Digest:
  `sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac`.
- Model inference/download/load: none.

## 2026-07-15 — all-45 two-stage semantic parser audit

Scope:

- Experimental target in the historical records:
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- Engineering reviewers: `gpt-5.6-sol`, reasoning effort `max`.
- Source writer commit:
  `359643b7b5eb8f95c13cca2e60fa753df8701282`.
- Immutable source:
  `phase1-limited-n3-gates/20260710T152820Z`.
- Semantic parent prefix:
  `phase1-semantic-audits/all45-parser-underflag-20260715T094500Z`.
- New model inference or behavioral observations: none.

Azure configuration:

- Environment: `cae-jspace-observation-sea-vnet2`.
- Profile/resources: `Consumption`, 2 CPU / 4Gi.
- GPU: none.
- Job: `job-jspace-p1-all45-pack`.
- Identity: `id-jspace-aca-acrpull-sea`.
- Storage authentication: managed identity only; no key/SAS/public network.
- Replica retry limit: zero.

Executions:

| Execution | Status | Purpose |
|---|---|---|
| `job-jspace-p1-all45-pack-2f0w7do` | Succeeded | Stage-1 append-only private release |
| `job-jspace-p1-all45-pack-yfn9b09` | Failed | Read-only print used a non-writable directory; no Blob write |
| `job-jspace-p1-all45-pack-k5jb2g8` | Succeeded | Deterministic Stage-1 packet print |
| `job-jspace-p1-all45-pack-t2vz2b1` | Succeeded | Stage-1 release-byte verification |
| `job-jspace-p1-all45-pack-kuw8801` | Succeeded | Stage-2 append-only release and print |
| `job-jspace-p1-all45-pack-kc3kot4` | Succeeded | Private immutable-source byte verification |

Operational notes:

- The first Git Bash ARM PUT was rejected before job creation because MSYS
  rewrote the `/subscriptions/...` resource ID. Native PowerShell ARM payloads
  were used after that; no execution was created by the failed PUT.
- The failed print execution wrote nothing to Blob. Its retry used the
  registered `/tmp/results` writable root.
- Local Entra Blob listing remained blocked by network rules, as expected.
  Packet/release/source bytes were transported through the private ACA job
  logs and accepted only after exact SHA-256 verification.

Release provenance:

- Stage-1 packet: 45 records, SHA-256
  `4e6b9b5085fcd859d03cbd5ddccd3749904af19edd875c12c1965f713476f622`.
- Stage-2 packet: 45 records, SHA-256
  `06f1d5b5a95e7cd39fb692a4ce798fa64747b362aaefcbb6532c6630db73ed3d`.
- Stage-1 manifest SHA-256:
  `bb0e4a5c8a78b04e623cf6970ef28c92bdf12221e1a14100df64003198ed71b8`.
- Stage-2 manifest SHA-256:
  `0d423f9bbb40c1f87eb936fd88b5386745d4422f8a18965bb184855f2b027371`.
- Source generation/evaluation hashes exactly matched the registered values;
  Blob properties remained unchanged and no source write was attempted.

Review:

- Reviewer A and B each completed 45 Stage-1 and 45 Stage-2 rows with exact
  IDs and sealed bindings.
- Arbitration triggers: `R002`, `R009`, `R018`, `R022`.
- Distinct arbiter rows: 4.
- Unresolved rows: 0.

Result:

- True ambiguity: 0.
- Parser overflags: 18.
- Parser underflags: 0.
- Observed extraction errors: 14.
- Material correctness errors: 2 (`R019`, `R038`).
- Material evaluator issues: 19.
- Final branch classification labels changed: 0.
- Official stored metrics/classifications modified: no.
- Decision: Path C; higher-n remains paused pending a locked evaluator
  validation set and prospective parser-v2 protocol.
- Detailed report: `reports/phase1_n3_all45_semantic_audit.md`.

Scientific boundary:

- This is a post hoc audit of stored outputs, not human ground truth.
- Every experimental cell remains `n=3`.
- Stopped remains intervention-controlled.
- Postprocessed remains answer-recovery utility, not raw no-CoT.
- No hidden-reasoning, internal-workspace, invisible-CoT, or J-space claim is
  made.

Final persistence:

- Machine-artifact execution:
  `job-jspace-p1-all45-pack-vi79nml`, Succeeded.
- Exact machine prefix:
  `phase1-semantic-audits/all45-parser-underflag-20260715T094500Z/final`.
- Nine manifest-bound files uploaded with `overwrite=false`; the manifest was
  uploaded last. Every file was downloaded again, SHA-256 checked, and exact
  prefix membership verified.
- Report execution:
  `job-jspace-p1-all45-pack-61s3ggf`, Succeeded.
- Separate report prefix:
  `phase1-semantic-audits/all45-parser-underflag-20260715T094500Z/report`.
- Report SHA-256:
  `a521e3f05242beb62b41698b272597fc2320b8a44dc2478198201a7270e01521`.
- The report was downloaded again and hash/membership verified.
- The temporary payload secret and environment reference were removed after
  transport. Current job secret count is zero and its command is the
  side-effect-free `echo semantic-audit-transport-idle`.

Independent post-run checks:

| Check | Agent | Model / effort | Result |
|---|---|---|---|
| integrity and provenance | `all45-integrity-review` | `gpt-5.6-sol` / `max` | PASS |
| reviewer agreement | `all45-agreement-review` | `gpt-5.6-sol` / `max` | PASS |
| confusion matrices | `all45-confusion-review` | `gpt-5.6-sol` / `max` | PASS |
| material impact | `all45-material-impact-review` | `gpt-5.6-sol` / `max` | PASS |
| scientific boundaries | `all45-science-boundary-review` | `gpt-5.6-sol` / `max` | PASS |

Final local validation:

```text
python -m pytest tests\ -q
217 passed, 2 warnings
```

## 2026-07-15 to 2026-07-16 — Phase 1.2A evaluator-set construction

Scope:

- Selected preregistered Path C.
- Froze the prospective parser-v2 protocol, evaluator-set design, acceptance
  gates, independent labeling workflow, sealing layout, and one-shot policy
  before eligible construction.
- Historical experimental target:
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- Engineering, curation, review, and arbitration agents:
  `gpt-5.6-sol`, reasoning effort `max`.

Protocol:

```text
final protocol commit: cc93ffe603ab8338ed860586a52b1911af4b3277
protocol bundle: 5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666
acceptance gates: a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988
tooling/development commit: e7a95a458d05d4ef211bb6902c2a20cb5f16bf60
production-ingress commit: 297420abfebb65c9f3702c56f28fe5a193913cd0
no-Git validation commit: 9b4262a9d35e6342935b8d2f72887a56c5f98486
```

Construction:

- Curator A and B independently produced 144 post-freeze candidates each.
- Curator C selected exactly 60 development and 120 locked cases.
- Development and locked quotas are exactly 5/10 for every S01-S12 stratum.
- Locked support: 80 present, 10 ambiguous, 30 no answer.
- Historical hard overlaps: 0.
- Near-duplicate findings: 37, all dispositioned.

Labeling:

- Stage-1 A/B: 120/120 each; 57 disagreements and 57 arbitration rows.
- Stage-1 consensus: 120; unresolved: 0.
- Stage-2 A/B: 120/120 each; disagreements/arbitrations: 0.
- Final operational labels: 120; unresolved: 0.
- Seven immutable review seals passed.
- These are LLM operational consensus references, not human ground truth.

Local release:

```text
parent: phase1-evaluator-validation/parser-v2-v1/20260716T024856Z
artifacts: 26
development: 60
locked: 120
final labels: 44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af
locked-label manifest: aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6
overall manifest: f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260
validation report: 5b3daf44553a7c99d57c8d5a117ef82de113c4b5cde74ef13dd218c11c56b641
```

Execution boundary:

- Target-model download/load/inference: none.
- Parser-v2 implementation: none.
- Locked evaluation: none.
- Higher-n run: none.
- GPU: none.

## 2026-07-16 — Phase 1.2A CPU-only private Blob sealing

Read-only preflight:

- Environment `cae-jspace-observation-sea-vnet2`: Succeeded.
- Workload profile: Consumption.
- Storage public network: Disabled.
- Blob private endpoint and private DNS: present.
- Shared-key access: disabled.
- Managed identity `id-jspace-aca-acrpull-sea`: `AcrPull` and
  `Storage Blob Data Contributor`.
- Fixed job `job-jspace-parser-v2-set`: absent before creation.
- Stale `parser-v2-seal-*` ACR tags: none.

Failed safe build:

```text
ACR run: cmf
status: Failed
start: 2026-07-16T04:05:15Z
finish: 2026-07-16T04:07:55Z
```

The direct full-repository build stopped on the frozen all-45 Docker attestation
because new Phase 1.2A behavior files are intentionally outside that image
contract. No image was published, no Container Apps execution was created, and
no Blob was written. The frozen attestation was not weakened.

Secure transport:

- Independent reviewer: `secure-persistence-review`,
  `gpt-5.6-sol/max`, PASS.
- Exact implementation commit:
  `9b4262a9d35e6342935b8d2f72887a56c5f98486`.
- Immutable base:
  `acrjspaceobssea0708231738.azurecr.io/j-space-observation@sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac`.
- Encrypted overlay build: `cmg`, Succeeded.
- Build start/finish:
  `2026-07-16T04:58:14Z` / `2026-07-16T05:00:29Z`.
- Temporary digest:
  `sha256:cd7371b7959b4eb577f75d40f0a5a7c71b585109c5ca5a072dfaccc6492efa54`.
- Sealing-code manifest:
  `1e6100a97cfc914b587cc6e4a1b11f3ce4483da45ae96543cc5c0c237aaf3c59`.

Azure execution:

```text
Date: 2026-07-16
Command: one manual CPU-only parser-v2 validation-set persistence start
Resource: job-jspace-parser-v2-set
Region: Southeast Asia
Environment: cae-jspace-observation-sea-vnet2
SKU / workload profile: Consumption
Resources: 2 CPU / 4Gi
GPU: none
Run ID / job execution: job-jspace-parser-v2-set-ib7uc0e
Start time: 2026-07-16T05:02:37Z
End time: 2026-07-16T05:04:04Z
Status: Succeeded
Blob parent: phase1-evaluator-validation/parser-v2-v1/20260716T024856Z
Authentication: ManagedIdentityCredential
Overwrite: false
```

Persistence result:

- Exact registered membership: 26 objects.
- Reservations were first; every leaf manifest and the overall manifest were
  last.
- Exact membership was checked before and after each manifest.
- All 26 objects were downloaded again and verified by size, SHA-256, and ETag
  before the container returned success.
- Source prefixes were not opened for write or modified.

Cleanup:

- Actual execution count: 1; all executions terminal.
- Job reset to the immutable base image and `/bin/true`.
- Job secret count: 0; secret-reference count: 0.
- Temporary ACR tag and digest: deleted and absence verified.
- Local encrypted build context: deleted.
- Stop/cost note: one 87-second Consumption execution; no GPU and no retry.

Post-sealing reviews:

| Check | Agent | Result |
|---|---|---|
| integrity | `postseal-integrity` | PASS |
| strata | `postseal-strata` | PASS |
| label agreement | `postseal-agreement` | PASS |
| sealing / one-shot | `postseal-one-shot` | PASS |
| scientific boundaries | `postseal-boundaries` | PASS |

Final local model-free validation:

```text
python -m pytest tests\ -q
460 passed, 2 warnings
```

Scientific boundary:

- Phase state is `SEALED`, not evaluated.
- No parser-v2 PASS/FAIL exists.
- No target model was loaded, downloaded, or run.
- No new behavioral observation or higher-n cell was created.
- No human-ground-truth, hidden-reasoning, internal-workspace, or J-space claim
  is made.

## 2026-07-18 — Phase 0.5A official real-Jacobian T4 feasibility

Scope and authorization:

- One primary GPU execution and at most one separately reviewed operational
  retry.
- Target:
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B@ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`.
- Official source:
  `https://github.com/anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`.
- Generic two-prompt fit corpus only; no Phase 1 task fixture, locked evaluator
  material, higher-n behavior, patching, or ablation.

### Dedicated image build and immutable finalization

Command family:

```text
bash infra/azure/scripts/07_build_phase05_jlens.sh
```

Primary image:

```text
source: 86922df02143d191dfa3d9fcf1d92adfaffc0062
ACR run: cmh
image: acrjspaceobssea0708231738.azurecr.io/j-space-observation-jlens:86922df02143d191dfa3d9fcf1d92adfaffc0062
digest: sha256:d3ffaba4fea1d4ee9b03dc5dd369f5b2c5100c84d183f7a729f609d2187bb22f
status: Succeeded
latest used: no
tag/manifest write enabled: false/false
tag/manifest delete enabled: false/false
```

The image built successfully. The first local metadata check then failed
safely because it read top-level ACR lock properties instead of
`changeableAttributes.*`. No rebuild or unlock occurred. Commit `b3e07bb`
fixed metadata interpretation; commit `d7bde7f` fixed Windows Git-Bash path
transport. Historical finalization verified and locked the existing digest.
Its immutable staging alias remains retained as build provenance.

### Primary execution

Command:

```text
bash infra/azure/scripts/08_run_phase05_jlens.sh
```

Execution:

```text
Date: 2026-07-18
Resource: job-jspace-p05-jlens
Region: Southeast Asia
Environment: cae-jspace-observation-sea-vnet2
Workload profile: gpu-t4 / Consumption-GPU-NC8as-T4
Resources: 1 T4 / 8 CPU / 56Gi
Run ID: 20260718T184445Z
Execution: job-jspace-p05-jlens-l7tipil
Status: Failed
Exit code: 4
Blob root: phase05-jlens-feasibility/20260718T184445Z
Primary final blocked snapshot: attempts/primary/snapshots/13-F4-blocked
```

Stage result:

- F0/F1/F2/F3: success.
- F2: 1536/1536 successful autograd calls; `[1536,1536]` fp32 CPU
  Jacobian; `35.0547s`; green memory.
- F3: two prompts, layers `[6,13,20]`, target 27; `55.0273s`; green
  memory; prompt-1 and complete checkpoints persisted.
- F4: failed after `1.2089s`.
- Exact error:
  `phase05_jlens.CheckpointValidationError: F4 saved/reloaded apply mismatch at layer 13`.
- F5: blocked.
- Decision: AMBER / BLOCKED because no completed final transaction existed.

### First CPU-only artifact reader

```text
Job/execution: job-jspace-p05-artifact-read-sq8pyw3
Profile: Consumption
GPU: none
Access: managed identity / private Blob / read-only
Blob writes: none
Model load/inference: none
Purpose: retrieve primary text artifacts for failure diagnosis
Status: Succeeded
```

The reader confirmed that official default-fp16 lens serialization introduced
matrix errors of approximately `0.000309`, `0.000472`, and `0.000488`.
The error was operational checkpoint fidelity, not a scientific finding.

### Authorized operational fix and image

An independent `gpt-5.6-sol/max` review authorized exactly one
serialization-only retry and rejected tolerance widening or comparing two
identically reloaded objects.

Implementation:

```text
commit: 5d4945b6ec477b6da485d19d90daeeb274b919e7
validation: 597 passed, 2 warnings
ACR run: cmj
image: acrjspaceobssea0708231738.azurecr.io/j-space-observation-jlens:5d4945b6ec477b6da485d19d90daeeb274b919e7
digest: sha256:345dde4f70235af3ad2542f79ea1445b66f4f53abe6fd569cd0818b8c4e8db35
status: Succeeded
staging tag removed: yes
latest used: no
tag/manifest write enabled: false/false
tag/manifest delete enabled: false/false
```

Two launcher invocations then failed before creating a retry ticket, updating
the Job, or starting an execution:

1. ARM `/jobs` list pagination omitted the singleton job. Commit `03fbf48`
   switched to auto-paginated CLI listing and local exact counting.
2. Windows Python emitted CRLF into Bash `mapfile` fields. Commit `be997ee`
   normalized carriage returns.

These were launcher-only failures and did not consume the authorized retry.

### Sole operational retry

Command:

```text
bash infra/azure/scripts/08_run_phase05_jlens.sh
```

Execution:

```text
Date: 2026-07-18
Resource: job-jspace-p05-jlens
Region: Southeast Asia
Environment: cae-jspace-observation-sea-vnet2
Workload profile: gpu-t4 / Consumption-GPU-NC8as-T4
Resources: 1 T4 / 8 CPU / 56Gi
Run ID: 20260718T184445Z
Execution: job-jspace-p05-jlens-m1sazlr
Start: 2026-07-18T20:21:53Z
Status: Succeeded
Platform retry limit: 0
Image: acrjspaceobssea0708231738.azurecr.io/j-space-observation-jlens@sha256:345dde4f70235af3ad2542f79ea1445b66f4f53abe6fd569cd0818b8c4e8db35
Blob root: phase05-jlens-feasibility/20260718T184445Z
Final snapshot: attempts/operational-fix/snapshots/11-final
```

Retry behavior and result:

- F0/F1 reran.
- Restored primary `13-F4-blocked` with verified `n_done=2`,
  `next_idx=2`, checkpoint hashes, control bindings, and old fp16 lens audit.
- F2/F3 were reused; no Jacobian recomputation occurred.
- F3 was losslessly reserialized with official
  `JacobianLens.save(..., dtype=torch.float32)`.
- Final fitted/reloaded matrices were exactly equal; max absolute error zero.
- F4 passed on three technical prompts and three fitted layers with the
  unchanged tolerance.
- F5 recorded `skipped_cost_guard`; actual reason was the no-recomputation
  retry rule.
- Final decision: GREEN / COMPLETE.
- Final manifest uploaded last; persistence confirmed; failed uploads zero.
- Plan B not triggered.

### Final CPU-only artifact reader

```text
Job/execution: job-jspace-p05-artifact-read-0g9i4bz
Profile: Consumption
GPU: none
Access: managed identity / private Blob / read-only
Blob writes: none
Model load/inference: none
Purpose: retrieve final text artifacts for review/publication
Status: Succeeded
```

Both readers were operational retrieval only and produced no behavioral or
mechanistic observation.

### Post-run reviews and publication boundary

Seven `gpt-5.6-sol/max` reviews covered provenance, runtime, method,
parser-v2 isolation, no-CoT taxonomy, headroom protocol, and scientific
boundaries. All passed after stale publication text was corrected.

Final boundary:

- Real official Jacobian Lens: yes.
- Tiny lens scientifically validated: no.
- Actual 10-/25-prompt fits: no; projections only.
- New behavioral observations: none.
- Locked parser-v2 evaluation: not performed.
- Hidden reasoning/internal workspace/J-space claim: none.
- Further Azure/model run authorized: no.

Final local publication validation:

```text
python -m pytest tests\ -q
597 passed, 2 warnings in 354.19s
```

`git diff --check` passed. The pre-commit tracked-file scan found no
credential-like assignment, account key, SAS signature, or file larger than
10 MiB. The final scientific-boundary re-review returned PASS.

## 2026-07-23 — Phase 1.2B one-shot and crash-closure hardening

Scope:

- Model-free tooling, provenance, Azure control flow, tests, and
  documentation only.
- No private holdout payload, locked labels, target model, GPU, Azure
  evaluation, image build, Job start, resource creation, commit, or push.

Implemented:

- Replaced unsupported Azure ETag assumptions with dedicated Private DNS TXT
  create-only build, launch, and dispatch capabilities.
- Bound ACR construction to one deterministic named TaskRun PUT with GET-only
  recovery and authenticated official ARM response variants.
- Delayed dispatch until the exact immutable ACA Job is fully provisioned and
  its protected projection is authenticated.
- Required both launch and dispatch proof for GET/list-only execution
  recovery; recovery has no Job PUT or start path.
- Cleared stale coordination, topology, image, and execution-baseline evidence
  before reads and explicitly propagated failures across Bash conditional and
  command-substitution contexts.
- Added parser-disabled prediction adoption for complete immutable Stage P
  artifacts.
- Added authenticated pending Stage E recovery for primary and
  scorer-infrastructure attempts.
- Added closure-only `CLOSED/INVALID` recovery for incomplete or tampered
  post-label scoring without labels reread, rescoring, parser invocation, or
  metric acceptance.
- Bound scorer-retry labels-open and `LABELS_READ` provenance to the
  authenticated retry receipt rather than the original prediction receipt.
- Required downloaded score bytes to match both the score manifest and the
  original scoring transaction.
- Documented a private Debian 12 VNet orchestrator with separate control-plane
  and runtime data identities. Provisioning remains approval-gated.

Validation commands:

```text
python -m py_compile scripts/bootstrap_parser_v2_locked_evaluation.py scripts/finalize_parser_v2_locked_evaluation.py tests/test_parser_v2_locked_evaluation.py
bash -n infra/azure/scripts/09_build_parser_v2_eval.sh
bash -n infra/azure/scripts/10_run_parser_v2_locked_eval.sh
python -m pytest tests/test_parser_v2_locked_evaluation.py -q
```

Result:

```text
162 passed
```

Adversarial coverage includes pending labels-open bootstrap, scorer-retry
predecessor recovery, complete coordinated score replacement, forged
labels-open provenance, closure-only no-reread behavior, stale/failed
coordination reads, asynchronous Job provisioning before dispatch, exact
dispatch-required recovery, GET/list-only adoption, and official TaskRun shape
handling.

Release status:

- Complete repository tests passed:

```text
python -m pytest tests -q
759 passed, 2 warnings in 785.86s
```

- Python compilation, both Azure Bash syntax checks, `git diff --check`,
  changed-file credential scan, untracked-file 10 MiB size gate, and frozen
  parser/gate/data-path checks passed.
- Four independent release audits are running.
- The locked holdout remains sealed and unevaluated.

## 2026-07-25 — Phase 1.2B parser-v2 locked evaluation (one-shot, CLOSED/FAIL)

Action:

- Executed the single authorized one-shot parser-v2 locked evaluation against
  the frozen implementation `654f3bb463fedc33b0638b77fefdd9b2b9d1c9c2` and the
  frozen acceptance gates.
- Sealed 120 parser-v2 and 120 legacy predictions before any label access, then
  opened, scored, and retired the 120-case locked holdout exactly once.

Azure resources:

- Subscription `943bacdf-8b6e-4e3a-8126-a149f623d32e`, region `southeastasia`.
- Orchestrator VM `rg-jspace-observation-sea / vm-pv2-orchestrator-sea`
  (private Debian 12, control-plane identity `id-jspace-parser-v2-control-sea`).
- Container Apps environment `cae-jspace-observation-sea-vnet2`, job
  `job-jspace-parser-v2-locked-eval`, runtime identity
  `id-jspace-aca-acrpull-sea`.
- Image `acrjspaceobssea0708231738.azurecr.io/j-space-observation-parser-eval@sha256:7ef281187f04692fa17a476c2a3265de051de2300bcd8c3242639b8b4ca6a489`.
- Results storage `stjspacefiles0709085305`, container `jspace-results`,
  parent prefix `phase1-evaluator-validation/parser-v2-v1/20260716T024856Z`.

Model and parameters:

- No model. No target model was downloaded, loaded, or run; no GPU was used.
- Each execution used 2 vCPU / 4 GiB, `parallelism=1`, `completions=1`,
  automatic `retry=0`, and an immutable Job body bound by DNS TXT launch and
  dispatch claims.

Runtime:

- Stage P `pv2-p-76a4018ffd782aa1e8398853-mqmkmxg`, completed
  `2026-07-25T04:15:48Z`: `PREDICTIONS_VERIFIED`, `input_count=120`,
  `parser_v2_prediction_count=120`, `legacy_prediction_count=120`,
  `labels_accessed=false`.
- Stage E primary `pv2-e-66f225af8c562425fe168b8c-8tgogbi`,
  `2026-07-25T06:28:32Z`: `STAGE_E_ERROR:EXECUTION_REJECTED:RuntimeError`.
- Stage E `scorer_infrastructure` retry
  `pv2-e-f2fcd3f9456d44ff15224f25-l33zhbh`,
  `2026-07-25T08:01:07Z`–`08:01:42Z`: `Succeeded`.

Results:

- Blob prefixes `.../state/pv2-locked-654f3bb-66588c8b-canon` and
  `.../scores/pv2-locked-654f3bb-66588c8b-canon/attempts/scorer_infrastructure/78ddfd37791611e08c59c834221608357212def40de544925137a8dc2d08442a`.
- Formal decision **FAIL**; state chain closed at `12_closed_receipt.json`
  (`state=CLOSED`, `outcome=FAIL`, `holdout_retired=true`).
- 34 mandatory gates: 32 passed, 2 failed, 0 NA/invalid. Failing gates are
  `boxed_final_miss` (1/20) and `wrong_span` (2/80).
- Report-only: typed agreement 116/120, 4 mismatched cases, 1 material-error
  case.
- `locked_evaluation_metrics.json`
  `7e735622f89ef50d725a60d389f74ab83e6dccaef84e8024bd5e8e84c7a8a521`;
  `scoring_ledger.jsonl`
  `c8ace06e413f7915188eb2ff3d0ee6f0b857bc8b79a77bce13c8be298c674eeb`
  (650946 bytes, 120 rows).
- Full result record: `reports/phase1_parser_v2_locked_evaluation.md`.

Errors:

- The primary Stage-E attempt was rejected before any label access or
  scientific write. After the frozen finalizer installed its subprocess audit
  guard, a lazy Azure Identity import called `platform.platform()`, which
  shells out to `uname -p`; the guard blocked it. It is recorded as an
  abandoned attempt and consumed the single `scorer_infrastructure` retry.
- Two infrastructure-only workarounds were applied outside the repository on
  the orchestrator host: pre-importing Azure SDK modules before guard
  activation, and accepting the authenticated label manifest's additional
  reviewer/consensus/arbitration metadata. Neither changed parser bytes,
  holdout bytes, metric semantics, gates, or PASS/FAIL behaviour.

Independent post-result verification:

```text
38 of 38 checks agree (recomputed from scoring_ledger.jsonl and
docs/phase1_parser_v2_acceptance_gates.json)
```

Post-result handling (same day):

- The formal record was committed as `e88a6df` and pushed to `origin/main`.
- Post-result authentication required a temporary `Storage Blob Data Reader`
  role for the control identity `id-jspace-parser-v2-control-sea`, scoped to
  the `jspace-results` container only. It was removed after the artifact hashes
  were verified, and removal was confirmed: the container scope now carries no
  role assignments and the identity holds no blob-data role anywhere in the
  subscription.
- The locally downloaded copy of the retired evaluation artifact graph was
  shredded from the orchestrator host, including the only on-host file holding
  label bytes (`scoring_ledger.jsonl`, 120 `label_record_base64` values). Its
  identity was confirmed against
  `c8ace06e413f7915188eb2ff3d0ee6f0b857bc8b79a77bce13c8be298c674eeb`
  immediately before deletion. The immutable originals remain in Blob storage.
- Retained unchanged: the immutable claims, DNS TXT records, the three ACA
  Jobs, seals, decisions, coordination evidence, build and runtime records,
  and the orchestrator VM.

## 2026-07-25 — Phase 1.2C parser-v3 failure-directed development (Track C)

Action:

- Diagnosed the two failed parser-v2 gates and built parser v3 as a standalone
  reference-blind extractor, then evaluated it against preregistered
  development gates. No locked holdout was read, opened, or scored.

Azure resources:

- None. This track ran entirely on local CPU. No Azure CLI command, no image,
  no job, no Blob access.

Model and parameters:

- No model. `model_id`, `model_revision`, `image_digest`, and `hardware` are
  recorded `not_applicable` throughout the artifact pack.

Runtime:

- Run `phase1-parser-v3-track-c-20260725T114448Z`, local, deterministic.

Results:

- Status **COMPLETE as development**. Parser v3 is **not validated**; it has no
  formal result and no locked-holdout evidence of any kind.
- Development gates: 60/60 field-exact non-regression on the frozen 60-case
  public development set, 60/60 typed agreement, 65/65 typed agreement on the
  new 65-case adversarial development fixtures, `boxed_final_miss` 0/29,
  `wrong_span` 0/88, `last_number_trap` 0/9, material-correctness errors 0/125.
- Reference-blind extraction is structurally enforced and verified by AST plus
  `co_names`/`co_varnames` inspection, so v3 cannot read a registered answer
  while extracting.
- The frozen parsers are byte-identical to `bc6d7b7`: `git diff` on
  `src/jspace_observation/eval_parsing.py` and
  `src/jspace_observation/eval_parsing_v2.py` returned empty output, and the
  v3 suite independently pins their LF-normalized SHA-256 values.
- The gate covering the four retired mismatch cases is recorded
  **NOT_APPLICABLE**: their case text is in the retired holdout and was not
  read, so only structural explanations were possible.
- Parser v2 scores 50/65 on the same adversarial fixtures. All 15 differences
  are v2 fail-closed recall losses that v3 recovers; there is no case where v2
  is correct and v3 is not.
- Tests: `python -m pytest tests/test_eval_parsing_v3.py tests/test_eval_parsing_v2.py tests/test_eval_parsing.py -q`
  → 144 passed (v3 87, v2 36, legacy 21).
- Report: `reports/phase1_parser_v3_development.md`.
- Boundary: the 65 adversarial fixtures were authored by the same agent that
  wrote parser v3, so 65/65 is a development signal and not an independent
  oracle. No hidden-reasoning, invisible-CoT, internal-workspace, or J-space
  claim follows from any of it.


## 2026-07-25 — Phase 0.5B J-lens saturation (Track A), executed on GPU

- Job: `job-jspace-p05-jlens-saturation` execution `job-jspace-p05-jlens-saturation-jxkk7fk`;
  exactly one execution was ever created.
- Run id `20260725T122016Z`; blob prefix `phase05-jlens-saturation/20260725T122016Z`;
  attempt `primary`. Started 2026-07-25T12:21:57Z, ended 2026-07-25T12:58:16Z
  (36m19s wall on one Tesla T4, 15,637,086,208 bytes total GPU memory).
- Code commit `408cd00540d5ded2b94ba75fc3616f8702e85465`; image digest
  `sha256:a15016dfd025cb4e5dc166638129cc4abf7895cdddbbc1b7638672aab7a3524f`.
  The image tag, the `project-sha` label, and `JSPACE_CODE_COMMIT` all agree.
- Fit corpus `data/jlens_saturation_prompts.jsonl`, file and canonical SHA-256 both
  `41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b`
  (25 fit / 10 held-out / 15 reserve). Protocol hash
  `b4422756bec723534b78981d79837f3cf9422244f4c1bf40eba205fcce29d32e`.
- All seven stages succeeded: S0_environment 0.33 s, S1_model 36.36 s,
  S2_fit_a10 528.62 s, S3_fit_b25_sharded_merge 1317.65 s, S4_merge_control 263.92 s,
  S5_convergence 0.03 s, S6_apply_stability 28.73 s.
- Outcome: **status COMPLETE, decision ENGINEERING_IMPROVING**. Seven of nine
  registered criteria passed; two failed.
  - Passed: matrix_finite_rate 1.0 (limit 1.0); lens_save_load_max_abs 0.0 (limit 0.0);
    shard_merge_vs_direct_max_abs 2.384e-07 (limit 1e-05);
    shard_merge_vs_direct_relative_frobenius 4.862e-08 (limit 1e-06);
    apply_save_load_consistency 1.0 (limit 1.0);
    heldout_topk_overlap_mean 0.82 (limit 0.80);
    heldout_rank_correlation_mean 0.9691 (limit 0.95).
  - Failed: convergence_relative_frobenius_10_vs_25 0.4170 (limit 0.10);
    convergence_cosine_10_vs_25 0.9205 (limit 0.99).
- Interpretation, stated exactly as the pack states it: numerics, sharding, merge,
  serialization and apply were stable, but the 10-to-25-prompt comparison has not
  reached the registered convergence thresholds. More fit prompts still change the
  lens. `ENGINEERING_IMPROVING` is a legitimate preregistered outcome and is
  recorded as the result, not as a partial success.
- Resource measurements: Fit A (10 prompts) 528.47 s total / 52.85 s per prompt,
  3,829,399,552 bytes peak reserved, 28,314,032-byte lens. Fit B (25 prompts, 3 shards
  merged) 1316.87 s total / 52.67 s per prompt, 3,774,873,600 bytes peak reserved,
  84,942,315-byte checkpoint and a 28,314,032-byte merged lens. Cost per prompt is
  essentially flat between the two configurations.
- `08_deviations.json` records `{"deviations": [], "unregistered_changes": [],
  "effect_on_interpretation": "none"}`. There were no deviations, and in particular
  no `merge-weighting-differs` deviation was raised.
- Upload: 23 objects (13 lens binaries under `attempts/primary/01-lens-binaries/`,
  10 artifact-pack files under `attempts/primary/02-artifact-pack/`).
  The uploader reported `manifest_uploaded_last: false` for both groups. This is a
  **stale reporting flag, not an ordering deviation**: the transport is inherited from
  Phase 0.5A and tests for the filename `phase05_jlens_artifact_manifest.json`, while
  the 0.5B pack writes `artifact_manifest.json`. The pack's own
  `manifest_written_last` is `true` and the independently re-run validator confirms
  the manifest is last in `manifest_order`. The lens-binaries group has no manifest at
  all, so the flag is vacuous there by construction.
- Retrieval: a temporary `Storage Blob Data Reader` assignment was created on the
  `jspace-results` container for principal `1ec93a23-1126-4058-a537-4f1016b8c325`,
  conditioned (ABAC v2.0) to the prefix `phase05-jlens-saturation/20260725T122016Z/`.
  Note for future runs: an ABAC condition written only against
  `blobs:path` denies `List Blobs`, which evaluates `blobs:prefix` instead; the
  condition needed both clauses.
- The 10 pack files were downloaded on the VM, packed to a deterministic tarball
  (SHA-256 `05ff5453781cbd1764298e7afc962d373b364de167658a882eb1c7a976e28f1f`),
  transferred in 14 base64 chunks, and the tarball digest was re-verified on arrival
  before extraction, so the local copy is provably byte-identical to what the job wrote.
- `phase05_jlens_saturation.validate_artifact_pack` was re-run locally against the
  downloaded pack and passed: 10 files, 22 records, 184 metric rows,
  `manifest_written_last` true, status COMPLETE, decision ENGINEERING_IMPROVING.
- The temporary role assignment was then deleted and removal was verified twice: the
  container-scope assignment list for that principal is empty, and a subscription-wide
  query for any role whose name contains `Blob` also returns empty.
- Pack committed to `artifacts/phase05b-jlens-saturation/track-a/20260725T122016Z/`.
- Boundary: top-k overlap and rank correlation are technical stability statistics about
  two fitted linear operators. They are not semantic, behavioural, or interpretive
  evidence, and nothing here supports a workspace, hidden-reasoning, invisible-CoT, or
  J-space claim. The 10-prompt fit set is nested inside the 25-prompt set, so the
  convergence comparison measures estimator movement, not independent replication.

## 2026-07-25 — Phase 1.0C capability headroom calibration (Track B), preregistered only

- Artifact pack `artifacts/phase1-headroom-calibration/track-b/p10c-trackb-plan-d778736ff8a2`
  (17 files), protocol hash
  `d778736ff8a2f0c7e82ee14a529abc05afb44ce3c8a9b2b47fd02771c405719d`.
  Design, protocol, selection rules and analysis code are complete; 100 tests pass.
- The emitted pack status is **BLOCKED**, which is the correct and honest status: no
  model was run, so there is no measurement.
- Reason the GPU run was not executed: the main `Dockerfile` runs
  `scripts/prepare_semantic_audit_build_context.py --validate-attestation`, which
  requires `.semantic_audit_build_provenance.json`. That file is gitignored
  (`.gitignore:50`) and is absent from the worktree, so the
  `j-space-observation` image cannot be rebuilt from this commit. No
  `j-space-observation-calibration` repository exists in the registry either.
  Executing Track B therefore requires new build infrastructure, which is out of
  scope for this round. This is deferred, not silently dropped.
- Boundary: n=10 per cell is a screening design, not an estimation design. Nothing in
  this pack is a measurement of the model.

## 2026-07-25 — Phase 1.2C parser-v3 locked holdout construction (Track D), constructed, NOT sealed

- Artifact pack
  `artifacts/phase1-evaluator-validation/track-d/20260725T121557Z-track-d-parser-v3-locked-set`;
  protocol hash `27becc4e7731e6326e1bfbea39dd2734110a131ab307f72253714406ac76fcba`.
- Composition: 120 cases across 12 strata (10 per stratum), 80 of them critical
  (strata outside S01, S02, S03, S12).
- Labeling: two reference-blind reviewers each covered all 120 cases independently.
  Whole-row exact agreement was 113/120 before arbitration; 7 disagreement rows were
  arbitrated; **0 labels remain unresolved**, which was the required threshold.
  Per-field agreement ranged from 117/120 to 119/120
  (answer_presence kappa 0.9787, output_quality kappa 0.9434,
  candidate_answers mean Jaccard 0.9917, failure_reasons mean Jaccard 0.9833).
- Independence cross-checks, re-run by the main agent via
  `scripts/crosscheck_parser_v3_locked_set.py`: **zero** exact collisions, **zero**
  normalized collisions and **zero** numeric-normalized collisions against both the
  65-case parser-v3 adversarial fixture set and the 60-case parser-v2 public
  development set.
- One registered cross-check is recorded as vacuous rather than passed: the 18-record
  historical audit extract `artifacts/record_audit/ambiguous_records_for_review.jsonl`
  contains no output-bearing field, so it cannot collide with anything by construction.
- **The set was NOT sealed to immutable storage this round.** Sealing was not performed
  because (a) the registered pre-seal cross-check against the retired parser-v2 locked
  inputs in Blob was not executed, and (b) writing the 12-object seal requires a
  `Storage Blob Data Contributor` grant that was not created. Until the seal exists,
  the holdout is not locked and **no parser-v3 evaluation may be run against it**.
- The locked inputs and labels are deliberately kept out of git (`.gitignore` rules
  38-47). Reviewability is via the committed fingerprint manifests
  `manifests/inputs_manifest.json`, `manifests/labels_manifest.json` and
  `manifests/set_manifest.json`.
- Boundary: reviewer agreement is LLM operational consensus, not human ground truth.
  Isolation between set construction and parser-v3 development is procedural, not
  security-enforced, and both happened in the same worktree during the same round.

## 2026-07-25 — Parser-v3 pre-seal cross-check 1 attempted and BLOCKED

- Objective: execute the one outstanding registered pre-seal check, namely whether
  any case in the new `parser-v3-v1` locked set collides with the **retired**
  parser-v2 locked inputs held at
  `phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/`.
- Design of the attempt, so it can be repeated: the comparison was to run entirely on
  the orchestrator VM using only one-way hashes. The committed
  `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json` carries the locked
  set's fingerprints and nothing else, so only hashes would have left this machine,
  and only collision counts would have come back. The retired inputs would have been
  read for **diagnosis only**; no rescoring, and no label material touched.
- A temporary `Storage Blob Data Reader` assignment was created for principal
  `1ec93a23-1126-4058-a537-4f1016b8c325`, ABAC-conditioned to the prefix
  `phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/`.
- **Outcome: NOT PERFORMED.** The Azure VM Run Command extension entered a wedged
  `Conflict: Run command extension execution is in progress` state during payload
  staging and did not clear across roughly 25 minutes of retries, including on a
  trivial `echo` probe. This is an infrastructure fault on the transport, not a
  scientific result, and it must not be reported as a passed check.
- The temporary role assignment was deleted immediately and removal was verified
  twice: the container-scope list for that principal is empty, and a
  subscription-wide query for any role whose name contains `Blob` also returns
  empty. No standing privilege was left behind.
- Consequence: the parser-v3-v1 seal remains **NOT PERFORMED**, and cross-check 1
  remains outstanding. The set is not locked and no parser-v3 evaluation may be run
  against it.
- To resume: clear the Run Command extension on `vm-pv2-orchestrator-sea`, re-create
  the same prefix-conditioned read grant, stage
  `scripts/build_parser_v3_validation_set.py` and the inputs manifest, run the
  fingerprint comparison, then remove the grant again and record the result.

## 2026-07-25 — Parser-v3-v1 pre-seal cross-check PASSED and the holdout is SEALED

- Objective: execute the one outstanding registered pre-seal check, then seal the
  120-case `parser-v3-v1` holdout if and only if that check passed.
- Transport: the check did **not** run on the orchestrator VM. It ran as a
  short-lived Azure Container Apps CPU job, `job-jspace-parser-v3-seal`, in the
  VNet-integrated environment `cae-jspace-observation-sea-vnet2` on the
  `Consumption` profile, 2 CPU / 4Gi, no GPU. Storage
  `stjspacefiles0709085305` has public network access `Disabled`, so managed
  identity inside the VNet was the only reachable path. No account key and no SAS
  were created, referenced or logged. The VM was separately repaired during this
  round, but it was not used for this work.
- **Cross-check 1 result: PASS.** New set 120 records, retired set 120 records,
  exact collisions 0, normalised collisions 0, numeric-normalised collisions 0.
  Decision `PROCEED_TO_SEAL`. The retired object hashed to its registered digest
  `2d60483e7f7a2ce1883acca2dcf9a6771f84b54d596ab2e02ed4a39d937c4e3e`
  (26651 bytes), so provenance matched.
- Isolation actually exercised: of the three objects under the retired
  locked-inputs leaf, only `locked_inputs.jsonl` was read.
  `.locked_inputs_reservation.json` and `locked_inputs_manifest.json` were listed
  and not read. The report records `label_material_touched: false`,
  `score_material_touched: false`, `rescoring_performed: false`. No retired input
  text left the container; only counts and one-way digests did.
- Guards that had to pass before any comparison was allowed: the registered
  fingerprint functions `fingerprints`, `normalize_text` and
  `numeric_normalized_text` were imported from
  `scripts/build_parser_v3_validation_set.py` and reproduced 5 pinned
  known-answer vectors, and reproduced all 120 records of the committed
  `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json`.
- **Seal: 12 objects at `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/`.**
  `overwrite=false` on every write; size, SHA-256 and ETag round-trip verified for
  all 12; exact membership 12 of 12; `manifests/set_manifest.json` written last at
  order 12. The cross-check report and the seal record are in the sibling prefix
  `20260725T160340Z-runlog/`, which keeps the sealed parent at exactly 12 objects.
- Membership was verified independently of the job: a separate listing under a
  separate identity returned exactly 12 objects in the parent, with byte counts
  matching the staged payload one for one, and 2 objects in the sibling runlog.
- Executions: `job-jspace-parser-v3-seal-57w51qd` (crosscheck, Succeeded),
  `job-jspace-parser-v3-seal-0fz4tkj` (seal attempt 1, Failed by design),
  `job-jspace-parser-v3-seal-61zgric` (seal, Succeeded). Image digest
  `sha256:f13220aed82c320150a63868e4519ec8d3d4dae7331ae4d421257f191c7d2388` for
  both tags; base `python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d`.
- **Deviation: the first seal attempt aborted, and that was correct.** Under
  timestamp `20260725T155224Z` the recommended dry pass had already written
  `crosscheck_report.json`; seal mode re-runs the cross-check and re-writes that
  report, so the upload hit its own `overwrite=false` guard with
  `ResourceExistsError` and the job failed closed with
  `state=BLOCKED_INFRASTRUCTURE`. No seal object was written under that timestamp
  and nothing was overwritten. The timestamp was rotated to `20260725T160340Z`,
  the stale write grant was deleted, a fresh grant was pinned to the new
  timestamp, and mode `seal` ran exactly once.
- **Deviation: no rebuild for the rotation.** The existing image was imported to
  the new tag, so the bytes that sealed the set are provably the bytes that were
  reviewed and that ran the passing cross-check.
- **Deviation, and the one that matters: the ABAC grants enforced nothing.**
  Teardown measured subscription-wide Blob roles for the sealing identity
  `id-jspace-aca-acrpull-sea` (principal
  `78d4348b-57eb-4fb9-aaa7-99148b303292`) as **1, not 0**: an unconditioned
  `Storage Blob Data Contributor` at account scope on
  `stjspacefiles0709085305`, created 2026-07-09, sixteen days before this round.
  Because that assignment was already unconditioned and account-scoped, the two
  temporary prefix-conditioned grants created for this run did not narrow the
  identity's effective permissions at all. The isolation of the retired parser-v2
  labels, scores and scoring ledger therefore rested on the payload's code path,
  on the Track D tests that pin that code path, and on the report's own
  attestations — not on RBAC. The standing assignment was **not** removed: it
  pre-dates this round and other Container Apps jobs depend on it to write
  results. This is recorded as deviation D13 and as limitation L-17.
- Teardown, with actual outputs: both temporary grants deleted; container-scope
  assignments for any principal `0`; control identity
  `1ec93a23-1126-4058-a537-4f1016b8c325` blob-data roles `0`; sealing identity
  blob-data roles `1` (the standing assignment above); job reset to base image
  `j-space-observation@sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac`
  with command `/bin/true`; job secrets `0` and secret references `0`; storage
  `publicNetworkAccess` still `Disabled`; the single-use repository
  `j-space-observation-pv3seal` deleted from ACR; staging context removed.
- Artifact pack:
  `artifacts/phase1-evaluator-validation/track-d1/20260725T160340Z-track-d1-parser-v3-seal/`,
  final state `SEALED`. It is built from the two durable Blob objects rather than
  from the in-container summary, which was ephemeral and is gone; the generator
  re-verifies the seal record's pinned report digest, the verdict and the three
  collision counts across both objects, and every sealed object's digest, byte
  count and order against the registered staging pins.
- Boundary, unchanged: **sealing validates nothing.** No parser-v3 evaluation was
  run, no parser-v3 prediction exists, nothing was scored, and no parser was
  imported. The sealed labels are a two-reviewer-plus-arbiter LLM operational
  consensus, not human ground truth. Isolation between holdout construction and
  parser-v3 development remains procedural, not security-enforced, and this round
  produced a concrete instance of that.

## 2026-07-25 — Phase 0.5C J-lens disjoint-fit replication (Track A1), executed on GPU

- Question, registered before the run and stated as engineering only: how far do
  two independently fitted same-size (n=25) J-lenses on disjoint prompt samples
  differ numerically, and does their official weighted merge behave numerically
  like a well-formed lens on held-out apply.
- **D14 — the fit corpus was amended to make the question answerable.** The
  round brief assumed a disjoint 25-prompt fit sample already existed inside the
  frozen Phase 0.5B corpus. It did not: that corpus is 25 fit, 15 reserve and 10
  held-out, and all 25 fit prompts were consumed by Phase 0.5B. Ten new
  `role=reserve` prompts `sat-reserve-016` … `sat-reserve-025` were appended
  under the identical registered generation constraints, giving corpus revision
  `r2-60`, 60 records, 16,087 B, SHA-256 `dd5d9749…62fa`. The amendment is
  append-only and proven so: `sha256(bytes[:13452])` is still `41e104ef…62b4b`,
  so every Phase 0.5B fit and held-out prompt is byte-identical and in unchanged
  order, and every Phase 0.5B number remains reproducible.
  `scripts/verify_jlens_corpus_amendment.py` re-checks it: 84 checks, 0 failed,
  with 0 exact and 0 normalised overlaps against 22,460 strings from four other
  corpora. This is recorded as a **round-level** change, not a runtime deviation:
  it was registered in the Phase 0.5C protocol before the run, so the executed
  pack's `08_deviations.json` is legitimately empty. See L-19 for the residual
  provenance asymmetry it creates.
- Provenance: commit `39dc6e09d0ccc2431bd3c695666033b0eeeb302d`; image rebuilt as
  required because the previous J-lens image contained neither the Phase 0.5C
  modules nor the 60-record corpus — ACR run `cm10`, digest
  `sha256:1fdf406fa34d76f228bd8a3570e9564c0a63baadda8e5b3e58f9c0e1b9ad3a37`;
  protocol hash `49059665f6c0c720beb712f99941f6cbf3a7a0207bac3e94cc4ac73f5af11980`.
- Execution: job `job-jspace-p05c-jlens-disjoint`, execution
  `job-jspace-p05c-jlens-disjoint-nfrnhcr`, run `20260725T174743Z`, `gpu-t4`
  Tesla T4, parallelism 1, completions 1, platform retry 0, managed identity
  only, blob prefix `phase05c-jlens-disjoint/20260725T174743Z`. Succeeded.
  17:49:26Z to 18:13:07Z, 23m41s. GPU serialised behind Track B1.
- **25A was loaded, never re-fitted.** The job read
  `phase05-jlens-saturation/20260725T122016Z/attempts/primary/01-lens-binaries/fit_b_merged_lens.pt`
  with its own job identity over the private endpoint and verified SHA-256
  `cb17a634…949d` and 28,314,032 B **before** deserialising. Launcher preflight
  logged `[OK] 25A lens preflight: … (28314032 bytes)` under a single temporary
  ABAC grant scoped by `blobs:path` to that one blob, deleted afterwards;
  container-scope assignments 0, control identity blob-data roles 0.
  `existing_lens_refitted: false`, `direct_50_fit_performed: false`.
- Result: status COMPLETE, decision **REPLICATE_IMPROVING**. All eight stages
  `success`. Transport gates passed (`matrix_finite_rate` 1.0,
  `save_load_max_abs` 0.0, `apply_save_load_consistency` 1.0). **Both replicate
  criteria failed**: `25A_vs_25B_relative_frobenius` 0.4831 against 0.10, and
  `25A_vs_25B_cosine` 0.8781 against 0.99. Merged comparisons 0.2565246384 and
  0.2565246556 relative Frobenius, cosines 0.9673 and 0.9710. Held-out apply
  overall: logit cosine 0.9858, rank correlation 0.9775, top-k overlap 0.8200.
  Preregistered merged improvement met on both statistics: top-k +0.1200 against
  a 0.02 margin, rank correlation +0.0330 against a 0.005 margin. Cost: 1289.78 s
  for 25B, 51.59 s/prompt, peak reserved 3,829,399,552 B.
- Verification: `scripts/analyze_phase05c_jlens_disjoint.py --write` run twice
  produced byte-identical output. Corpus verifier and the two targeted test
  modules were run before commit: 84 checks / 0 failed, and 104 tests passed.
- Boundary: **this is not good news about lens quality.** Both registered
  replicate criteria failed. `REPLICATE_IMPROVING` means the numerical transport
  worked, two independent fits disagree substantially, and the merge lands
  between them — and a weighted mean must lie between its inputs, which is why
  the two merged-versus-input distances agree to 1.7e-08. Recorded as L-18.
  Nothing here licenses a claim about semantic validity, scientific usability, a
  workspace, hidden reasoning, an internal chain-of-thought, J-space, or semantic
  convergence.

## 2026-07-25 — Phase 1.0C Track B headroom calibration executed on GPU, adjudicated, INCONCLUSIVE

- Scope: bounded capability/headroom calibration, protocol hash
  `d778736ff8a2f0c7e82ee14a529abc05afb44ce3c8a9b2b47fd02771c405719d`, executed
  unchanged. Same 150 item IDs, 300 generation units, task families, difficulty
  bands, conditions, generation settings, selection thresholds and semantic
  review rules as preregistered.
- Build: the generic image could not be used. `.semantic_audit_build_provenance.json`
  is gitignored (`.gitignore:50`), was never committed on any branch, and is
  absent from ACR and Blob. It is also unregenerable:
  `scripts/prepare_semantic_audit_build_context.py` asserts that the tracked
  behavior-file set equals a frozen 30-entry `RUNTIME_FILES` list, while the
  repository now tracks 63 such files (33 extra, 0 missing), so the generator
  fails by construction. A dedicated `Dockerfile.calibration` plus a
  deterministic two-part `calibration_build_provenance.json` was introduced.
  Commit A `5d18b708304984ce82f72028f335d7a970afa5b8` (code), commit B
  `661eff7803d33d3be7be516f76eaf8dcb9e50d4f` (provenance, generated at a
  verified-clean detached checkout of commit A, prebuild digest
  `a0dae9ec81baada7001ba2a752d8e7798c891a48f5e56528077de50a89212c8b`).
  ACR run `cmy`, immutable tag
  `j-space-observation-calibration:661eff7803d33d3be7be516f76eaf8dcb9e50d4f`,
  digest `sha256:c65795e1ab7233d4f2b362d7da339ce8d10de23d83a750947239d155c7ee0ce9`,
  `immutability_verified=true`.
- Execution: job `job-jspace-p10c-headroom`, execution
  `job-jspace-p10c-headroom-0pdexaa`, run ID `20260725T170041Z`, environment
  `cae-jspace-observation-sea-vnet2`, profile `gpu-t4`, NVIDIA Tesla T4,
  parallelism 1, completions 1, platform retry 0, managed identity only over the
  private endpoint, no storage key and no SAS. Blob prefix
  `phase1-headroom-calibration/20260725T170041Z`. Status Succeeded, wall clock
  approximately 36 minutes. 300 records emitted, 300 generated, 0 planned-only,
  0 errors, 30 cells scored.
- Adjudication: deterministic triage flagged 225 of 300 rows under the registered
  scope (reason counts: `parse_invalid` 112, `triage_disagrees_with_registered_answer`
  84, `truncated_output` 79, `no_answer` 57, `ambiguous_parse` 55,
  `provisional_headroom_cell` 30, `deterministic_random_sample` 9; rows carry
  multiple reasons). A single primary semantic reviewer labelled all 225 in the
  registered nine-field form while blinded to the deterministic verdicts.
  Coverage complete, 0 outstanding mandatory rows. Reviewer totals: 81 correct,
  100 incorrect, 44 unresolved.
- Reviewer versus screen: 112 of 225 rows agreed outright (30 correct, 82
  incorrect). There were **zero** direct correctness contradictions — no row
  where the screen said correct and the reviewer said incorrect, or the reverse.
  111 rows carried no deterministic verdict at all; on those the reviewer read a
  matching stated answer on 51, a non-matching stated answer on 18, and agreed
  the row was unresolvable on 42. Two rows (`R039`, `R151`) had a decisive
  screening verdict of `incorrect` where the reviewer recorded `unresolved`,
  which is the more conservative direction. **Zero rows met the registered
  arbitration trigger**, so no arbiter was invoked.
- Flag agreement: the reviewer's `truncated` flag matched the objective
  512-token-cap signal on all 225 rows (79 at the cap, 0 disagreements in either
  direction). The `no_answer` flag disagreed on 62 rows: on 38 the parser
  reported no answer where the reviewer read a stated answer, and on 24 the
  parser reported an answer where the reviewer judged nothing was designated.
- Result: final labels across 300 rows are 156 correct, 100 incorrect, 44
  unresolved (225 from the primary reviewer, 75 inherited from screening on rows
  never flagged). Two cells classified `selected_headroom`:
  `prompt_grounded_two_hop_factual|hard|r1_style_thinking` and
  `synthetic_relation|hard|r1_style_thinking`, both 7/10, accuracy 0.70, Wilson
  95% CI `[0.396778, 0.892209]`. One high-accuracy control
  (`arithmetic|hard|visible_cot`, 10/10), four difficulty boundaries, three
  excluded on quality gates, twenty `not_adjudicated` because they contain at
  least one unresolved row. Track B decision **INCONCLUSIVE**.
- Verification: `--mode finalize` run twice with `--frozen-time` produced
  byte-identical output across all 20 pack files. Targeted suites 308 passed;
  parser suites 144 passed; `eval_parsing_v3.py` LF SHA-256 re-verified as
  `dd729c3c23771fb112811e382bf7e55f531ce534cbbd1cfec4f0527056c8908e`, unchanged.
- Boundary: **n = 10 per cell is a screen, never a stable performance estimate.**
  A 7/10 cell's 95% interval spans `[0.397, 0.892]`. The two selected cells are
  candidate ablation substrates, not cells with established headroom. 79 of 225
  reviewed rows hit the token cap, so truncation reflects the 512-token budget
  rather than model competence. Adjudication was single-reviewer, and the zero
  arbitration count is an absence of contradiction with a deterministic screen,
  not an inter-reviewer agreement statistic. Parser v2 was automated triage only
  and never produced a final label. Nothing here licenses a claim about hidden
  reasoning, an internal workspace, invisible chain-of-thought, or a J-space.

## 2026-07-25 — Main-agent provenance corrections to the Track B pack and the artifact index

- Scope: corrections applied by the main agent while reviewing the Track B
  artifact pack and the paper ledgers before commit. No metric, threshold,
  gate, label or classification changed. The finalize stage was re-run and its
  scientific content is byte-identical to the independently produced pack:
  `04_decision.json` agrees on all 16 keys, and `03_metrics.csv`,
  `06_paper_table.csv`, `07_figure_data.csv` and all four `cell_selection/`
  CSVs are byte-identical. 17 of the 20 files matched exactly; the 3 that
  differ are `00_stage_manifest.json`, `05_summary.md` and
  `artifact_manifest.json`, which are precisely the files that carry
  provenance.

- **The generate and finalize stages are now stored as separate packs.**
  `artifacts/phase1-headroom-calibration/track-b/20260725T170041Z-generate/`
  holds the pack exactly as the GPU job wrote and uploaded it, and
  `artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/` holds the
  finalize pack. Both carry run id `20260725T170041Z`, because they are two
  stages of one run.

- **Reason: the stage manifest's `hardware` and `image_digest` fields are
  stage-scoped, not run-scoped.** The repository's own precedent settles this:
  the plan-stage manifest records `image_digest: not_recorded` and
  `hardware: aca-gpu-t4-pending`, describing the stage's own execution rather
  than the run's intended target. The finalize stage ran on a local x86-64
  Windows CPU host, outside any container image, under code that postdates the
  image. Recording `NVIDIA Tesla T4` and the calibration image digest against
  `mode: finalize` would have asserted three false things: that the stage ran
  on a T4, that it ran inside that image, and that commit `661eff78` computed
  the metrics. The finalize manifest now records `image_digest: not_recorded`,
  the local CPU host, and the commit that actually contains the finalize code.
  The generation provenance is not lost: it is stated truthfully in the
  generate pack's own manifest, and `inputs.records` in the finalize manifest
  points at that pack by repository-relative path.

- The finalize manifest's `inputs` previously contained absolute local
  Windows paths. They are now repository-relative.

- Finalize was run twice from the committed inputs and produced byte-identical
  output both times, so the pack is reproducible from what is in the
  repository. Reproduction requires `--frozen-time`; without it `start_time_utc`
  becomes wall-clock and every manifest digest drifts.

- **The finalize pack is not in Blob.** Only the generate pack was uploaded, at
  prefix `phase1-headroom-calibration/20260725T170041Z`. Storage has public
  network access Disabled and is reachable only from inside the VNet, and the
  finalize stage ran outside it. The finalize pack is a deterministic function
  of the generate pack and of the reviewer labels, both of which are committed,
  so it is reproducible without the Blob copy. `EV-0004.artifact_prefix` refers
  to the generate pack.

- **`AR-0028` was re-pinned to an immutable commit.** It registers the J-lens
  fit corpus as Phase 0.5B consumed it, digest
  `41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b`, 13452
  bytes. The Track A1 corpus amendment (`D14`) changed the file at that path in
  commit `39dc6e0`, so the row stopped verifying against the working tree even
  though it was correct for its own run. Its `storage_location` now pins commit
  `f97ea59c5826d7195602189f9d31f93c91066ee5`. The digest and byte count are
  unchanged. The current corpus is registered separately as `AR-0039`.
  All 27 repository-backed rows of `paper/artifact_index.csv` now verify
  against either the working tree or the pinned blob.

- **Defect recorded, not corrected in place: commit `422d379` silently
  included two Track B ledger edits its message does not describe.**
  `EV-0004` moved from `REGISTERED_NOT_RUN` to `COMPLETE_INCONCLUSIVE` and
  `L-16` was rewritten from "registered but unmeasured" to the measured
  result. The Track B agent wrote those two files into the working tree
  between that commit's status check and its staging step. Both edits are
  correct and are retained. History was not rewritten and nothing was
  force-pushed.

- Process note for later rounds: subagents were instructed to make no git
  writes, and none did, but they did write working-tree files concurrently
  with the main agent's staging. Working-tree writes by a concurrent agent are
  functionally a race against `git add`. Future rounds should either have
  subagents write drafts outside the repository or have the main agent stage
  by explicit path immediately after a fresh status check.


## Phase 1.2D - parser-v3 locked evaluation preregistration (commit `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea`)

Preregistration commit `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea` was pushed to
`Alanjiao1988/J-space-observation` **before** any parser-v3 prediction was
generated and **before** any parser-v3 locked label was read. At that commit:

```text
holdout touched         no
predictions generated   no
locked labels accessed  no
working tree            clean
local HEAD == origin/main
full test suite         1320 passed
targeted suites         240 passed
```

The commit freezes the candidate parser, the derived gate contract, the
three-stream Stage P / Stage E orchestration, the runtime evaluation profile,
and the evaluation image source.

### Candidate and comparator identities

```text
candidate                parser v3
algorithm_id             jspace-parser-v3-reference-blind-extraction/v1
parser_version           0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace
source_sha256            76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9
implementation_commit    310277bcadd67ca9e77986fc292fae47dc5ceda2

comparator_1 (gating)    parser v2
parser_version           6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86

comparator_2 (reporting) legacy parser
source_sha256            4b07b91859aca33b51af9c15b08f07026f11b0141f1300fd3f942138b731177e
```

### Derivation evidence

```text
gate contract            docs/phase1_parser_v3_acceptance_gates.json
                         2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7
numeric threshold changes   0
metric semantic changes     0
population changes          0
verdict                     DERIVATION_FAITHFUL

candidate worker         scripts/parser_v3_process_worker.py
substitutions               6
unexpected diffs            0
entrypoint derivations      1 changed line each
```

### Safety defect found and fixed before preregistration

Stage E's parser-import prohibition initially omitted parser v3 from several
exact-match deny lists and probes (`FORBIDDEN_FILENAMES`, the `.pyc` stem set,
`_FORBIDDEN_CODE_NAMES`, and the source probe). Two independent read-only
preflight reviews (`claude-opus-5`, `reasoning=max`) then found four further
CRITICAL defects in the three-stream wiring:

1. Stage P assembled its upload payload in construction order rather than in
   registered member order, so the manifest-last write would have failed
   **after** all 360 parser invocations.
2. Three validators hardcoded the parser-v2 prediction member name, guaranteeing
   a `KeyError` under the parser-v3 profile.
3. `load_frozen_gate_bytes` asked Git for the v3 contract at a frozen protocol
   commit that predates the file, so Stage E could not load its own gates.
4. The scoring ledger applied the legacy-row validator to the parser-v2 gating
   comparator, which carries parser envelopes; this would have raised **after**
   the label download, spending the holdout and forcing `INVALID`.

```text
Found and fixed before:
  preregistration
  prediction generation
  holdout access
  label access

Impact on formal evaluation:
  none
```

All four, plus six HIGH and two MEDIUM findings, were fixed and covered by
regression tests before the preregistration commit. This is recorded rather
than hidden because it is reproducibility and safety-boundary evidence.

### Execution environment blocker

The preregistered build and run launchers
(`infra/azure/scripts/09_build_parser_v3_eval.sh`,
`infra/azure/scripts/10_run_parser_v3_locked_eval.sh`) are hardened POSIX shell
scripts that re-exec under `env -i` with `PATH=/usr/local/bin:/usr/bin:/bin`
and resolve `/usr/bin/python3`. The development machine is Windows with only an
MSYS/MINGW64 bash, no `/usr/bin/python3` and no `/usr/local/bin`, and WSL has no
distribution installed. Earlier Azure phases in this project were driven by
Python scripts and so were unaffected.

No parser-evaluation image has ever been built. Stage P and Stage E are
therefore **not yet executed**; the round is paused at the preregistration
freeze rather than at a scientific result. The freeze itself is complete and
irreversible, so execution can resume from `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea` on any POSIX host without
re-deriving anything.


### Post-freeze commits and the build source SHA

The preregistration freeze is commit `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea`.
Commits made after it in this round touch **documentation only** and never touch
any path in `RUNTIME_SOURCE_BINDING_PATHS` (24 paths) or
`IMAGE_BINDING_SOURCE_PATHS` (31 paths). Verified: the intersection of the
edited set and both binding sets is empty.

The build script derives its source SHA from `HEAD` at build time, so the
image tag may name a later commit than the preregistration commit. That is
audit-visible and intended. The invariant that matters is that every bound
source path is byte-identical to its state at the freeze, which the image
binding hashes prove independently of the commit name. No parser, gate
contract, orchestrator semantic, profile binding or membership rule may change
after the freeze, and none has.


### Build-host recovery and one stranded build claim (parser v3)

The preregistered build launcher requires a POSIX host. It was executed on the
pre-existing orchestrator VM `vm-pv2-orchestrator-sea`
(`rg-jspace-observation-sea`, Debian 12, `/usr/bin/python3` -> 
`/usr/bin/python3.11`, root-owned, mode 755), which is the same class of host
used for the parser-v2 round. No new infrastructure was created.

The first attempt was run as the unprivileged operator account and failed:

`	ext
PermissionError: [Errno 13] Permission denied:
  .../build-<invocation>/acr_task_run_body.json
`

Cause: the launcher writes `acr_task_run_body.json`, then `chmod 400` s it,
then writes the same path a second time after the durable build claim is
authenticated. Under a non-root operator the second write fails with `EACCES`;
under root it succeeds because root bypasses the permission bits. The identical
sequence is present in the frozen parser-v2 launcher at the corresponding
lines, so this is inherited behaviour and **not** a parser-v3 derivation defect.
It also implies the parser-v2 round was executed as root.

Consequence. The failed attempt died **after** creating its durable build TXT
claim in the coordination zone and **before** the one-shot ACR TaskRun PUT. Only
the process that wins the claim with a `201` create may start the TaskRun; any
later process gets `412` and is restricted to GET-only adoption. The build for
source commit `c2ab05c94398dc6c8a8c9df8db746712b95dc216` is therefore
permanently stranded and can never be completed. Coordination-zone record sets
went from 15 to 16; the extra record is that stranded claim. It is retained, not
deleted.

Recovery. A build claim's domain is derived from the source commit, so a
different source commit yields a different claim name and a fresh one-shot
build. A rehearsal was then run as root at the stranded commit to prove the
environment: it passed every environment, snapshot, LF, source-binding, ACR,
coordination-zone, provenance, claim-envelope and ACR-task-run-body stage,
reported `[INFO] Build TXT create returned 412; GET-only recovery` exactly as
predicted, and entered the TaskRun discovery loop. It was then stopped, because
its claim has no TaskRun and never will. That rehearsal consumed no new claim
and produced no image.

Scientific impact: none. No locked input was read, no prediction was generated,
no label was accessed, and no evaluation semantics changed. The event is
recorded because a stranded durable claim is a permanent, publicly visible
artifact of the coordination zone.


### Second pre-execution defect: the v3 Azure helper validated against the v2 profile

The first real one-shot build (source commit
`1c5ace45bfb8b6641ebaa5e184cfb14f04309a15`) created its durable claim, started
its ACR TaskRun, **built and pushed the image successfully**, and then failed at
the final gate:

`	ext
[FAIL] immutable image binding is invalid
[FAIL] Final immutable image binding validation failed
`

Cause. `scripts/parser_v3_azure_contract.py` loaded the locked-evaluation core
with raw `importlib` and never seeded the parser-v3 profile, so the helper
resolved the **default parser-v2 profile**. It therefore demanded
`Dockerfile.parser-v2-eval` and `j-space-observation-parser-eval` while the
binding correctly carried the parser-v3 Dockerfile and repository. Validating the
same binding directly against a v3-profile core returned `VALIDATION_OK`,
which isolated the fault to the helper rather than to the image.

The helper had been derived from the parser-v2 helper, where loading the default
profile is correct because parser v2 *is* the default. The derivation was an
exact substitution and so faithfully reproduced a line that is right for v2 and
wrong for v3.

Scope. This is a **build-and-runtime provenance validation** defect. It does not
touch parser bytes, the gate contract, prediction semantics or scoring
semantics. It would also have broken Stage P and Stage E, because the runtime
launcher validates the runtime configuration and the prediction seals through
the same helper, and those validators are profile-scoped by member name and
binding path. Finding it at the build gate prevented a later failure during
prediction generation.

Fix. `_load_core` now seeds `_PRESEEDED_PARSER_PROFILE_ID = "parser-v3-v1"`
before `exec_module` and asserts both that the profile took effect and that
the seed did not leak, matching `scripts/load_locked_evaluation_core.py`. The
parser-v2 helper is unchanged and still resolves the parser-v2 profile. Three
regression tests were added; the full suite is 1323 passing.

Consequences for the freeze. `scripts/parser_v3_azure_contract.py` is a bound
image-binding source path, so this fix changes the image binding and requires a
new source commit and a new build. The semantic freeze established by
`e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea` is unaffected: parser v3, the
candidate worker, the gate contract, the profile table, Stage P prediction
semantics, Stage E scoring semantics and the membership rules are all
byte-identical. The build at `1c5ace45` is abandoned with its claim stranded;
its image is not used.

No locked input was read, no prediction was generated and no label was accessed
at any point.


### Parser-v3 evaluation image built (source commit `ec3801d3`)

`	ext
source commit      ec3801d39677f1568e6940c5593a7af07999a8f3
repository         j-space-observation-parser-v3-eval
tag                ec3801d39677f1568e6940c5593a7af07999a8f3
image digest       sha256:2d85fc9be656d5af992d2ec28e4749583c6c4873ce0c0c38b0e6e811d3fb1ad8
image binding      c9f82d9253650f57bbe0e945027cb4c74c1ce6d29369b453d02871c022203cfb
registry           acrjspaceobssea0708231738.azurecr.io
base image         python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
`

Launcher output:

`	ext
[OK] acrjspaceobssea0708231738.azurecr.io/j-space-observation-parser-v3-eval@sha256:2d85fc9be656d5af992d2ec28e4749583c6c4873ce0c0c38b0e6e811d3fb1ad8
[OK] Image binding SHA-256: c9f82d9253650f57bbe0e945027cb4c74c1ce6d29369b453d02871c022203cfb
[OK] CPU-only image and source tag are immutable; no latest tag
`

The tag is the immutable source commit; there is no `latest` tag; Stage P and
Stage E share this one digest and differ only by hardcoded entrypoint.

Build host: `vm-pv2-orchestrator-sea` in `rg-jspace-observation-sea`, the
pre-existing parser-v2 orchestrator VM, running as root with the user-assigned
identity `id-jspace-parser-v2-control-sea`. As in the parser-v2 round, the
build record files remain on the orchestrator host, outside the committed tree,
at `/home/jspaceadmin/J-space-observation/results/runs/parser-v3-eval-build-ec3801d39677f1568e6940c5593a7af07999a8f3`
(`build_provenance.json`, `image_binding.json`, `image_binding.sha256`).
Their authoritative digests are recorded above.

Three build claims now exist in the coordination zone for parser v3: two
stranded (`c2ab05c9` and `1c5ace45`) and one completed (`ec3801d3`). Only
the completed one has an image, and only that image may be used.

Holdout state after the build: still `SEALED`. No locked input was read, no
prediction was generated, no label was accessed.

## Phase 1.2D parser-v3 locked evaluation (2026-07-25) — HALTED, NOT RUN

```
Outcome:                          HALTED before preregistration
Formal PASS/FAIL:                 none produced
Preregistration commit:           none created this round
Holdout state:                    SEALED, unspent (15 objects)
Locked labels read:               0
Predictions generated:            0
Authorization lock:               not created
State chain:                      not bootstrapped
ACA job:                          not created
Formal evaluation ordinal:        0
```

The round was stopped in preflight. The sealed parser-v3 validation set, the
frozen scoring instrument and the parser-v3 acceptance gates are three
artifacts that do not describe the same thing. Nine findings (`H1`-`H9`) are
recorded in `docs/phase1_parser_v3_locked_evaluation_protocol.md` §15.

The decisive one is `H9` and it involves no instrument. The gate contract
`docs/phase1_parser_v3_acceptance_gates.json` admits three typed-decision
labels and declares `typed_decision_support = {ambiguous: 10, no_answer: 30,
present: 80}`. The sealed set contains a fourth class,
`present_unextractable` (4 cases), which `null_collapse_prohibited: true`
forbids collapsing, and its real support is `{present: 91, no_answer: 23,
ambiguous: 6}`. Strata are correct at 12 × 10 = 120. Because the `ambiguity`,
`no_answer`, `answer_presence_macro_f1` and `overall_exact_typed_decision`
gates are calibrated against the declared support, no instrument can score
this set against these gates.

Root cause: the v3 gate contract was derived from v2 by substitution rather
than re-derived from the v3 set — the `last_number_trap` blocks in the two
contracts are byte-identical, including an `error_definition` naming a
registered distractor span the v3 set does not contain. In parallel the set
was built to its own conventions. No artifact-level agreement test existed
between the two.

Two preflight instruments found all nine and are now standing requirements:
the **write-blocked dry run** (real bootstrap, real storage,
`upload_blob_once` replaced by a sentinel `BaseException`, zero side effects)
and the **projection probe** (project the set into the frozen schema and let
the *frozen* validator judge it).

Six normalisations (`N1`-`N6`, §15.4) were validated and are kept for reuse.
They lift the frozen-valid projection from 22 to 105 of 120 with all 105
typed decisions preserved, and they make the mandatory `last_number_trap`
gate non-vacuous on all 10 S06 cases — without them that gate would have
passed unconditionally while appearing to be enforced (`H3`). They cannot
reach the remaining 15 records, which differ semantically (`H8`).

Nothing irreplaceable was spent. Parser v3 is unchanged and frozen at source
SHA-256 `76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9`.
Because no preregistration commit was created, the parser, gate contract,
profile binding and membership rules remain editable — which the remediation
in §15.8 requires.

**Next gate:** re-derive the parser-v3 gate contract from the parser-v3 set,
resolve `present_unextractable` explicitly, reconcile the span convention
across the set and all three parsers, and add a mechanical preregistration
check that reproduces every declared support count, gate denominator and enum
vocabulary from sealed bytes before any image is built.

---

## Phase 1.2E — parser-v3 evaluation ontology repair, tooling-only round

**Status: BLOCKED on acceptance thresholds. No private data read, no prediction
generated, no formal evaluation performed.**

A public round. It built the protocol and tooling for a future independently
curated `parser-v3-v2` set, and touched nothing private.

**Access ledger for the round.** Sealed locked inputs read `0`. Sealed locked
labels read `0`. Local private curator files read `0`. Predictions generated
`0`. Parser invocations on locked data `0`. Azure writes or resource changes
`0`. Formal evaluation ordinal remains `0`.

**Old set disposition.** `parser-v3-v1` is recorded `SEALED / UNSPENT /
UNSCORABLE / RETIRED_AS_INELIGIBLE`. `UNSPENT` records the absence of label
access and is not a licence to reuse the set. Bytes, provenance, `H1`-`H9` and
`N1`-`N6` are preserved unchanged, and the historical gate contract is
preserved byte-for-byte as the artifact found defective rather than amended in
place.

**New finding, publicly restatable.** `evaluator_sets/parser_v3_v1/strata_definitions.md`
is a tracked public file. The sealed set violates its own public specification,
not merely the v2-inherited contract: `S10` is publicly registered `no_answer`
but its cases are labelled `present`; the public quota table asserts 80/30/10;
the public rule that every `S11` case carries at least two distinct canonical
candidates is violated; and the public statement that no `empty` output is
exercised is violated. The root cause of `H9` is therefore broader than
contract substitution from v2 — there was no agreement test between the set,
its own public specification, and its gate contract.

**Count erratum.** `sealed_object_count = 12`, `total_case_count = 120`,
`residual_semantic_case_count = 15`. The Phase 1.2D line `Holdout objects 15`
conflated the first and third and is corrected by an erratum in
`reports/phase1_parser_v3_locked_evaluation.md`. A recursive listing of
`parser_v3_v1/` does return 15 entries, but they are a different 15: the 12
sealed members, plus 2 objects in the sibling `…160340Z-runlog/` prefix, plus 1
orphaned `crosscheck_report.json` under the aborted `…155224Z-runlog/` prefix
(`…track-d1-parser-v3-seal/05_summary.md:43` and deviation `D10` of the same
pack). That reconciliation is inferred from Phase 1.2D records, not observed
this round — no Blob listing was performed. A regression test now fails if the
counts are conflated again.

**Delivered.** A three-class truth table with a fail-closed record and set
validator; `N1`-`N6` as pure, deterministic, idempotent, parser-free
functions (statically scanned, and proved differentially at runtime rather than
by an unachievable absolute claim)
that quarantine rather than coerce; a set-derived facts builder; an agreement
validator whose rejection codes are the historical defect labels
`H1/H2/H3/H5/H8/H9`; a byte-stable contract compiler that refuses to overwrite
and refuses to compile from an unresolved policy; a read-only CLI; the
prospective policy `docs/phase1_parser_v3_v2_evaluation_policy.json`; and
`tests/test_parser_v3_repair.py`.

**Test results.** Focused `tests/test_parser_v3_repair.py`: 122 passed. Full
repository suite: 1497 passed (baseline 1375 + 122 new). No existing test or
gate was weakened. The first implementation pass passed 93 self-authored
tests and still contained two critical defects; see the audit record below.

**Independent audit.** After the first implementation was complete and green, a
separate read-only review agent audited the round against the frozen instrument,
the 1.2D record, the public strata and the 1.2D sealing artifacts, ran the
focused suite itself, verified the eleven protected digests against `45a18f4`,
and probed the tooling adversarially. It found **ten defects: two critical, five
major, three minor.** All ten were fixed and re-tested.

The two critical findings deserve recording in full, because both are the same
error this phase exists to prevent.

1. The `ambiguous` truth-table row declared `parse_valid = false`. The frozen
   instrument requires `true` — a correctly detected ambiguity is a *valid*
   parse whose outcome is "two or more candidates". Under the original table,
   **every `S11` case in a sealed `parser-v3-v2` would have been unscorable by
   construction**, which is exactly the condition that retired `parser-v3-v1`.
2. The set-facts manifest was bound to nothing: `set_sha256` digested the
   manifest itself. The auditor compiled a fully provenance-bearing contract from
   a manifest typed by hand describing a set that had never been built.

Both had one root cause: the repair tooling *restated* the frozen instrument's
invariants instead of *binding* to them — the same defect as `H9`, which arose
because the v3 gate contract was copied from v2. The structural fixes are
`_bind_to_scoring_instrument`, which routes every accepted record through the
frozen `_validate_extraction_fields` and `derive_typed_decision` and requires
agreement, and `SetSource` / `_require_derivable`, which re-derives every facts
manifest from the labels and inputs it claims to describe and requires
byte-equality before any comparison runs. The remaining eight findings and their
fixes are recorded in `reports/phase1_2e_parser_v3_repair.md` §6.

The lesson is recorded deliberately: 93 self-authored tests passed against code
containing a defect fatal to a tenth of the future set, because the fixtures
encoded the same misunderstanding as the code. Self-authored tests are not
independent validation.

**Second audit round.** The remediation was itself re-audited, which was the
right call. The reviewer confirmed eight of the ten fixes as structural — a
4 490-mutant differential sweep found zero records the ontology accepts and the
frozen instrument rejects — and found **five further defects, four of them
introduced by the remediation**. One was major: the decision-preservation fix
compared a whitelist of projected fields, and seven fields the scorer reads were
invisible to it, so three constructed cases normalised "successfully" instead of
quarantining. `normalize_record` now validates its own output against the formal
ontology before returning, which subsumes the whitelist because the ontology
binds to the instrument. The other four were one-line defects in the new code: an
`isinstance` guard a `SetSource` subclass could defeat, `agreement_findings`
exported as public API when it accepts unverified input, an untested
`allow_overwrite` flag contradicting the protocol's own never-amend invariant,
and a bare `KeyError` plus substring-matched quarantine codes in the normalizer.
All five are fixed; `NormalizationError` now carries its own reason code.

Two observations were accepted without code change and recorded as limitation
`L-32` instead: `sealed_object_count` and the member list are operator
*assertions*, not derived facts, because no offline tool can list a blob, and a
self-consistent misstatement of both is undetectable here. The fixture was also
extended so the whole-set idempotence properties actually exercise `N1` and
`N6`, which previously applied zero times.

**Why BLOCKED.** The numeric acceptance thresholds cannot be justified in this
round: Phase 1.0C headroom calibration has not been run, importing the
parser-v2 constants would carry over an unjustified number of exactly the kind
this phase exists to eliminate, and deriving a threshold from any parser-v3
observation would select the threshold against the measurement it bounds. They
are marked `REVIEW_REQUIRED` and the compiler refuses to compile while any is
open. Everything else in the round is complete.

> **Erratum E-1.2F-01, appended 2026-07-26 (Phase 1.2F).** The original text
> above is retained verbatim as the historical record, including its error. The
> clause "Phase 1.0C headroom calibration has not been run" was **false when
> written**: Phase 1.0C executed and finalized `INCONCLUSIVE` at `06eec993`,
> recorded in this log at the 2026-07-25 entry "Phase 1.0C Track B headroom
> calibration executed on GPU, adjudicated, INCONCLUSIVE". It entered this entry
> from a stale current-state summary that had never been updated after the run.
> The clause is also a category error: Phase 1.0C screens target-model
> observable-answer task headroom, not parser extraction fidelity, so it could
> never have supplied a parser acceptance threshold.

**Not claimed.** Parser v3 is not validated, not non-regressive, not improved,
not accepted. The tooling has synthetic-test evidence only. No J-space,
hidden-reasoning, internal-workspace or invisible-CoT conclusion follows.

**Next gate:** resolve the acceptance thresholds, either by running Phase 1.0C
headroom calibration or by registering an explicit reviewed rationale for a
threshold family that does not depend on it. No `parser-v3-v2` construction,
review, sealing, preregistration, image build, Stage P or Stage E may begin
before that gate passes.

> **Erratum E-1.2F-01 (continued).** The "next gate" above is superseded. Phase
> 1.0C cannot be a gate for a parser threshold. Phase 1.2F audited all four
> thresholds and left one non-vacuous criterion,
> `residual_critical_exact_budget` over `S04`/`S05`/`S09`, blocked on a
> downstream parser-error budget the scientific plan does not register.

---

## 2026-07-26 - Phase 1.2G: post-audit consistency remediation and conformance-policy finalization

**Round.** Phase 1.2G. Repository audit, methodological decision, policy and
tooling correction, testing, documentation, and — on completion — commit and
push. No experiment ran.

**Baseline.** `origin/main` at `3d519e1`. Working tree clean at start. Full
suite green at baseline: **1624 passed**.

**What was decided.** The scientific question Phase 1.2F left open - whether the
designed-failure strata `S04`, `S05`, `S06`, `S09` admit any exact
typed-decision error tolerance - was settled by operator decision as **strict
finite-suite conformance**. The future `parser-v3-v2` set is a finite
conformance suite, not a sample. Every case admitted to it is admitted because a
correct instrument must handle it, so every case is a mandatory conformance
example and a mismatch on any one of them is unacceptable instrument behaviour.
Zero residual tolerance follows as a `LOGICAL_INVARIANT`.

The derivation is constrained. It does not appeal to determinism, non-IID
sampling, the absence of calibration, conservatism, tidiness, parser-v2
precedent, or any expectation about parser-v3 performance, and a regression test
scans the derivation text to keep it that way. The premise is recorded with its
falsifier: admitting a case a correct instrument is not required to handle would
refute it.

**What was remediated.** Ten seed defects, `G-01` to `G-10`, all consistency
failures between artifacts rather than new scientific findings, and deliberately
not numbered into the historical `H1`-`H9` series. In summary: stale 90/30
coverage figures and a "pinned" `S06` in the stratum policy; stale population
figures in the calibration protocol; a next-gate ordering inversion in the
Phase 1.2F report; a stale synthetic fixture; a withdrawn comparator argument
still asserted live in `paper/methods_ledger.md`; an audit report claiming fixes
the artifacts contradicted; a focused-suite total recorded as 242/201 where the
transcript shows 249; a per-stratum cap stated only in prose; and a
protected-digest count of 11 where the registry holds 12.

**Threshold dispositions.** `residual_critical_exact_budget` is `KEEP_HARD`,
binding, pooled maximum errors `0` and per-stratum maximum errors `0` for each
of `S04`, `S05`, `S06`, `S09`, on a `LOGICAL_INVARIANT` basis.
`overall_exact_typed_decision_minimum` is `REPLACE_HARD` and
`critical_stratum_floor` is `MERGE_WITH_EXISTING_GATE`.
`answer_presence_macro_f1_minimum` and
`non_regression_margin_vs_parser_v2` are `REPORT_ONLY`. The prospective
acceptance policy is now `FINAL`.

**Instruments changed.** The policy JSON is declared the canonical
machine-readable source of truth and moves to schema `/v3`. Exact-typed-decision
coverage is now computed by one production derivation,
`parser_v3_repair_contract.derive_gate_coverage`, consumed by both validation
and compilation; the policy's coverage block is a restatement the validator
requires to agree with it. `GATE_ERROR_DEFINITIONS` is a closed, code-owned
registry of what each gate's error definition means. A new deterministic
generator, `scripts/generate_current_state.py`, renders the current-state block
from the policy and compares bytes under `--check`.

**Two defects in this round's own new code were found by this round's own new
tests.** A comparator margin of `0` was silently admitted as "no margin",
because `0 == False` in Python, when a zero margin is the substantive rule
"must not be worse than parser v2". And the superseded-figure scanner's
negation guard exempted the withdrawn comparator argument, whose own wording
contains a negation. Both are fixed and pinned by tests.

**Not claimed.** Parser v3 is not validated, not non-regressive, not improved,
not accepted. A `FINAL` policy is a settled rule for judging a future
evaluation; it is not a result and says nothing about any parser. The policy
became stricter in this round, not more permissive. No J-space,
hidden-reasoning, internal-workspace or invisible-CoT conclusion follows.

**Private-access ledger.** Sealed inputs read `0`. Sealed labels read `0`.
Private curator files read `0`. Predictions generated `0`. Parser runs `0`.
Azure writes or resource changes `0`. Formal evaluation ordinal `0`.
`parser-v3-v1` unchanged and still
`SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`.

**Next gate:** a separately authorized independent set-repair round for
`parser-v3-v2`. No construction, migration, replacement review, manifest
generation, sealing, authorization lock, image build, preregistration, Stage P
or Stage E is authorized by this round.

## 2026-07-26 — Phase 1.2H: independent `parser-v3-v2` set repair — BLOCKED ON SOURCE ACCESS

**Baseline:** `origin/main` at `0480f4f`.
**Terminal status:** `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`.
**Protocol:** `docs/phase1_2h_independent_set_repair_protocol.md` (registered, `UNEXECUTED`).
**Report:** `reports/phase1_2h_blocked_set_repair.md`.
**Audit record:** `reports/phase1_2h_audit_findings.md`.
**Live state:** `docs/phase1_2h_execution_access_ledger.json`.

**What was authorized.** Read-only custodial access to the retired
`parser-v3-v1` sealed inputs and labels; one-way import under a new
`parser-v3-v2` identity; `N1`-`N6` normalization; blind semantic review by
isolated reviewers with an arbiter; replacement curation; construction of
exactly one 120-case set; pre-seal audits; create-only sealing.

**What happened.** The round terminated at the first hard precondition. The
authoritative sealed source was resolved from committed evidence and probed for
reachability at the control plane and container-metadata layer only. The storage
account reports `publicNetworkAccess = Disabled` and the data plane refused the
request under its network rules. The registered read path is a user-assigned
managed identity exercised from in-network compute, which is unobtainable from
the workstation this round ran on. The authorization forbids substituting an
unverified local copy when the sealed source is unavailable, so the round
blocked.

Standing up in-network compute was considered and rejected: the blind semantic
review executes as reviewing agents outside that network, so reading private
content inside the boundary in order to ship it out would defeat the isolation
the network rules encode.

**What the round did produce.**

1. **Audit F** — the independent re-review Phase 1.2G had honestly disclosed as
   missing. It found **all six** Audit E remediations incomplete (0 blockers,
   5 majors), with a working counterexample for each. All six were fixed and
   regression-pinned.
2. **A live execution/access ledger** and its validator, separating live access
   state from the `FINAL` policy's finalization snapshot, bound to the policy by
   both a full-file hash and a `policy_semantics_sha256` computed with
   `execution_state` projected out.
3. **A registered, explicitly unexecuted protocol** that states what was
   deliberately *not* frozen, and why.

**Private-access ledger.** Retired-v1 sealed inputs semantically read `0`.
Sealed labels semantically read `0`. Private curator files read `0`. Labels
opened for scoring `0`. Byte-only integrity verifications `2`. Cases constructed
`0`. Cases reviewed `0`. Sets sealed `0`. Listing witnesses `0`. Final contracts
`0`. Parser invocations `0`. Candidate predictions `0`. Comparator predictions
`0`. Preregistrations `0`. Formal evaluations `0`. Azure control-plane reads `6`;
data-plane content reads `0`; data-plane writes `0`; resource creations or
changes `0`; job executions `0`.

Because no semantic read occurred, the `REPAIR_ACCESSED` transition did not
happen. `parser-v3-v1` remains `SEALED / UNSPENT / UNSCORABLE /
RETIRED_AS_INELIGIBLE`, unqualified and byte-unchanged. `parser-v3-v2` does not
exist; its `sealed_object_count` is `null`, not `0`, because under `L-32` that
quantity requires an authenticated seal-time observation.

**Not claimed.** Parser v3 remains unvalidated. Phase 1.0C was executed and
finalized `INCONCLUSIVE`; it is target-model task/headroom screening, not parser
calibration. No formal evaluation has occurred. No J-space, hidden-reasoning,
internal-workspace or invisible-CoT conclusion follows.

**Next gate:** a separately authorized round whose sole objective is to
establish authenticated, read-only, in-network access to the retired sealed
source under a boundary in which semantic review also occurs inside the network.
That round is not preregistration, not evaluation, not construction and not
sealing.


## Phase 1.2H — Audit G final-state re-review and remediation

Audit G reviewed the remediated Phase 1.2H state and returned **1 blocker, 4
majors and 1 minor**. All six were reproduced with the auditor's counterexample,
fixed, and re-checked.

The blocker (`G-01`) is the serious one. The ledger's `retired_v1_state` and
`successor_set_state` blocks were rendered into the current-state documents and
validated by nothing. The auditor set them to a fully constructed 120-case
sealed set while `sets_sealed` stayed `0` and the status stayed blocked; the
ledger validated and the generator published it. A `retired_v1_semantic_read`
event was accepted with both read counters at zero, and succession accepted a
status-only jump to `SEALED_READY_FOR_PREREGISTRATION`.

The remediation closes the schemas for the ledger top level, both state blocks
and every event; reconciles each narrated field against the counter that
measures the same thing; requires every access event to be counter-backed;
rejects the three event kinds this phase never authorises; validates both
records before comparing them for succession; and validates the ledger before
the generator renders it.

`G-04` narrowed the semantic projection. Excluding the whole `execution_state`
block also excluded its free-text `final_policy_is_not_a_result` statement, so
that statement could assert "a formal evaluation was run and parser v3 was
validated" without moving the hash the ledger binds. Only the five mutable
counters are now excluded, and the statement is constrained against asserting a
result. The policy's top-level key set was also closed, because a top-level
`parser_v3_v2_evaluations_run` had validated cleanly.

`G-02`, `G-03` and `G-05` tightened the consistency scanner and the
parser-isolation check. `G-06` withdrew an unsupported convergence claim from
`L-38`.

**Unchanged by all of this.** No private access occurred, no parser ran, no
prediction was generated, no set was constructed or sealed, and the terminal
status remains `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`. The policy's threshold, gate,
ontology, population, comparator and status blocks are byte-identical to Phase
1.2G.
---

## Phase 1.2H-R1 — cloud-first private-source access restoration

**Terminal status:** `BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY`.

**What changed, in one sentence.** Phase 1.2H concluded the sealed source was
unreachable; R1 established that it was unreachable *from outside the virtual
network*, went inside, and streamed every byte of it to a digest without
decoding one.

**The provisioned boundary.** A user-assigned identity
`id-jspace-p12h-r1-read-sea` holding exactly two role assignments
(`Storage Blob Data Reader` scoped to the single container `jspace-results`;
`AcrPull` scoped to the registry), a digest-pinned image built by ACR Tasks,
and a VNet-injected Container Apps job with `replicaRetryLimit: 0`. No role
granting write, delete, `Storage Blob Delegator` or role-assignment read was
requested. Every heavy step ran in Azure; the operator's machine did editing,
`git` and control-plane calls only.

**The gate.** Execution `p12h-r1-access-gate-003` (ACA execution `0fqre0m`,
image `sha256:f2cf1701…`) passed: one list over the exact registered prefix,
12 members matching the committed public manifest as a set, 12 objects streamed,
396,613 bytes, every per-object digest and size matching, and an aggregate
digest of
`e1364afcac87516813d33a4e9fb3e370769487ab2f3ca47a08a3b4059db14e71` —
the value already committed publicly before the round ran. Twelve invariants
checked, none failed.

**The refusal that came first.** Execution `dlv8kmc` refused with
`FORBIDDEN_ENV_VAR` before authenticating. The probe's own denylist named
`MSI_ENDPOINT` and `MSI_SECRET`, which are exactly how Container Apps
supplies the managed identity the protocol requires; the rule was
self-contradictory and impossible to satisfy. It is recorded rather than quietly
fixed because it is evidence the pre-flight guard fires on a real error, at the
cost of a real run.

**Why the round is still blocked.** Set repair needs *semantic* review of private
material, and the executable boundary assessment scores 0 of 13 conditions
passed, 5 failed and 8 not assessable ⇒ `DOES_NOT_QUALIFY`.
`rg-jspace-observation-sea` in `southeastasia` contains zero
`Microsoft.CognitiveServices` accounts and zero ML workspaces; the only
same-region AI account belongs to an unrelated project, has
`publicNetworkAccess: Enabled` and no private endpoint; and the worker subnet
has no egress control attached. Under protocol §10 read with §8 this is decisive
**because** the byte-only gate passed: the states are ordered, and only a round
that reached the source can be blocked at the boundary. The evidence covers that
resource group and region, which is the scope of the claim; no statement is made
about other resource groups in the subscription.

**Two claims deliberately not made.** `public_network_access` is recorded as
`"Unknown"` — the probe holds no reader role on the account resource, and the
receipt schema now refuses any other value. `effective_read_only_verdict` is
`NOT_CONFIRMED_IN_JOB` — reading one's own role assignments requires a role the
identity deliberately does not hold, and granting it to fill in a field would
have increased privilege for a cosmetic gain. An earlier draft returned
`READ_ONLY_CONFIRMED` unconditionally; both independent audits caught it.

**Unchanged by all of this.** No semantic read occurred, no parser ran, no
prediction was generated, no set was constructed or sealed, and no formal
evaluation took place. `parser-v3-v1` remains
`SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`, byte-unchanged; the
transition to `REPAIR_ACCESSED` did **not** occur, because streaming bytes to a
digest is not a repair read. The policy's threshold, gate, ontology, population,
comparator and status blocks are byte-identical to Phase 1.2G, and
`policy_semantics_sha256` remains `ae375481…`.

---

## Phase 1.2H-R2 — Phase A public protocol freeze gate

**Terminal status:** `BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE`.

**Exact candidate.** The remediated public candidate was commit
`423d16a7b486b8c22fa58a733ffa6a03b389f0fe`, tree
`3080241e68dc007e91f49967beebbd80ff1d4ec6`. ACR run `cm3q` passed 463
targeted controls and compiled the boundary Bicep. A clean exact-commit checkout
under `/tmp/src` in run `cm3u` produced 2873 passed, 15 skipped, and only the
two disclosed pre-existing failures; `main.bicep` and every module compiled.

**Final permitted audits.** Independent Audit A (`gpt-5.6-terra`, run `cm3v`)
returned three BLOCKER findings: duplicate Stage E case IDs can replace an
omitted case (`A-01`), one-shot/create-only controls still trust caller-supplied
nonexistence (`A-02`), and the historical 105/15 target guard remains a
key-name heuristic (`A-03`). Independent Audit B (`gpt-5.6-luna`, run `cm3w`)
returned one BLOCKER and one MAJOR: identifier-bearing schema arrays do not
enforce keyed-ID uniqueness (`B-01`), and the existing Blob account's
public-network-disabled state is neither configured nor mechanically checked
by the Bicep (`B-02`).

The exact reports are
`docs/audits/phase_a_public_audit_a_round2_report.json`
(`f5a40d3a88f1977de6afb098b9c7109832e2b32679ef3d513018cedddec2d0f5`)
and `docs/audits/phase_a_public_audit_b_round2_report.json`
(`4be4cf1ee04976ff69b9fc666287fd5304cd13520ae742e1acb3a9dca8b6d364`).
The content-free terminal receipt is
`docs/phase1_2h_r2_phase_a_public_audit_terminal_receipt.json`.

**Mandatory stop.** This was audit/remediation cycle two of the maximum two
allowed by the controlling prompt section 5.4. Because material findings remain,
no third remediation/audit cycle is attempted, Phase A is not frozen, and Phase
B is not authorized. A new public-protocol redesign requires separate authority
and a new bounded audit plan.

**Unchanged scientific record.** No private semantic or label read occurred, no
prediction was generated, no set was constructed or sealed, no preregistration
lock was created, no Stage P or Stage E run occurred, and no formal evaluation
or private-boundary deployment took place.

---

## Scientific mainline restart — S0 parser closure (2026-08-02)

**Project state:** `SCIENTIFIC_MAINLINE_RESTART_AUTHORIZED`.
**Parser subproject state:** `CLOSED_NONAUTHORITATIVE_TRIAGE_ONLY`.

**Authority.** A new operator prompt, saved verbatim at
`docs/prompts/phase_science_restart_after_parser_closure_prompt.md`
(SHA-256 `5bc137c42c68e1b85b4cad1d45e1b4bf54fb68e2899f27bc6338dae61e9ef162`,
25,313 bytes), executed at the required starting commit
`ea2bce81defe9063bde2be58ada0e747d2a34c03`. `origin/main` was verified equal to
that commit before any file was written. The prompt and the decision record were
committed and pushed as `ac9e0327d82bbc2d0451e7fca09b504660ce579d` **before**
implementation began, because executing the prompt is the operator authorization
for the scope.

**What S0 changed.** Three new records — the verbatim prompt, the machine-readable
authority object `docs/phase_science_restart_authority.json`, and the closure
decision `docs/decisions/parser_v3_locked_evaluation_closure.md` — plus
consistent entries in this log, `docs/decision_log.md`, `README.md`,
`paper/limitations_ledger.md` (`L-01` elevated; `L-41` and `L-42` added),
`paper/claim_evidence_matrix.md` (`CL-06` withdrawn as pursuable, `CL-07` opened
for J-lens functional validity) and `paper/methods_ledger.md`.

**What S0 deliberately did not change.** No parser implementation, parser test,
parser schema, or parser IaC file was touched. No receipt or report byte was
edited. No row of `paper/evidence_ledger.csv` was rewritten: the closure is a
scope decision, not new evidence, and the historical records of what was built
stand exactly as they were. Eight preserved artifact digests are pinned in the
closure record so that any later drift is detectable.

**Next scientific gate.** Work package S1: reproduce the Phase 1.0C
generation-profile defect facts from committed artifacts, then freeze the Phase
1.0D protocol before any target-model inference.

## 2026-08-02 — Phase 1.0C generation-profile defect audit (S1)

Action:

- Recomputed the controlling prompt's §4.1 factual claims about Phase 1.0C run
  `20260725T170041Z` directly from the committed record pack, instead of
  restating them.

Azure execution (no analysis ran on the laptop):

- ACR Tasks multi-step run `cm3y` on `acrjspaceobssea0708231738`,
  platform `linux/amd64`, base image `python:3.11-bookworm` (Python 3.11.15),
  dependency closure `requirements.lock.txt`.
- Bound commit `8333ccaefb0955d892aef18a6df4d4bc3bfe0aae`,
  tree `03835f211de4ac9666448e23d6b226071817c66b`, DIRTY=0.
- `tests/test_phase1_0c_defect_audit.py`: 24 passed.
- The immediately preceding run `cm3x` failed 1 of 24. The failure was in a
  synthetic mutation control, not in the audit: it mutated record 0, which
  already contained the literal placeholder, so the mutation changed no count.
  Fixed by mutating the first record whose output lacks the placeholder. No
  audit logic and no authority fact was altered.

Result — every §4.1 fact reproduces exactly:

| Fact | Authority | Recomputed |
| --- | --- | --- |
| Records | 300 | 300 |
| Prompts carrying the literal `Final answer: <answer>` line | 300 | 300 |
| Outputs containing the literal `<answer>` | 31 | 31 |
| Outputs echoing the whole format line | 5 | 5 |
| Rows flagged for review | 225 | 225 |
| Reviewed rows at the 512-token cap | 79 | 79 |
| Semantically unresolved rows | 44 | 44 |

New fact not stated by the authority — the joint partition of the 44 unresolved
rows over the two defects: 38 token-cap only, 4 both, 1 placeholder only,
1 neither. Placeholder alone therefore accounts for 5 of 44 and the token cap
alone for 42 of 44, so no single cause explains the Phase 1.0C outcome. The
recorded `evaluation.truncated` flag agreed with the recomputed token count on
all 300 rows (0 disagreements).

Artifact: `docs/phase1_0c_generation_profile_defects.json`.

Not established: this says nothing about whether repairing the defects changes
the Phase 1.0C conclusion, and it licenses no headroom claim. Phase 1.0C keeps
its `COMPLETE_INCONCLUSIVE` status and not one record was re-scored.

Next expected run: the Phase 1.0D confirmation protocol (S1 continued).

Confirmation of the committed artifact:

- ACR run `cm43` at commit `f9e1c7f789804dd9fd501de935d0b5765e78f8f4`,
  25 passed, including a test asserting that the committed
  `docs/phase1_0c_generation_profile_defects.json` equals the receipt
  recomputed from the pack. The artifact is therefore self-verifying and will
  fail the suite if the pack or the audit ever drifts from it.

Method defect found and fixed during this work (recorded because it would have
silently manufactured evidence):

- Runs `cm40`, `cm41`, and `cm42` used an ACR task context whose shell script had
  been flattened to a single line by a PowerShell pipeline write. Everything
  after the shebang became a comment, so the container executed nothing.
  `cm42` reported **success in 21 seconds with no test output at all**.
- A passing ACR run is therefore not evidence by itself. The runner now prints
  `TARGETED_TESTS_COMPLETE=1` as its last line, and a run without both the
  pytest summary and that sentinel is to be treated as no evidence.
- The task YAML must also keep `version:` as its first line. With a leading
  comment, ACR either runs zero steps (`cm40`) or fails to deserialize (`cm41`).

## 2026-08-02 — Phase 1.0D protocol freeze (S1)

Action:

- Froze the Phase 1.0D confirmation protocol — selection, prompt rendering,
  decoding, adjudication, and the cell gate — before any target-model
  generation. Nothing was generated. Phase 1.0C is untouched.

Azure runs (no analysis on the laptop):

| Run | Commit | What it did | Result |
| --- | --- | --- | --- |
| `cm44` | `73566c7d` | `tests/test_phase1_0d_confirmation.py` | 46 passed |
| `cm45` | `7e9e3f86` | `infra/azure/scripts/emit_phase1_0d_protocol.py` | snapshot emitted |
| `cm46` | `d5d898ea` | protocol tests incl. committed-snapshot check | 47 passed |
| `cm47` | `d5d898ea` | full suite | 2945 passed / 15 skipped / 2 failed |

The 2 failures in `cm47` are the disclosed pre-existing
`tests/test_parser_v3_seal_job.py` failures carried since the `a99d1e83`
baseline. Test count went 2873 -> 2945 (+72) with zero new failures.

Split feasibility — the bank supports the registered design exactly, with no
slack:

- bank = 450 items; Phase 1.0C consumed the 150 `calibration` items, verified
  against the `source_item_id` values in the 1.0C records rather than against
  the split label alone;
- eligible pool = 300 items, and every one of the 15 family x band cells holds
  exactly 20;
- the selection is therefore all 300 remaining items: 150 `confirmation` and
  150 `mechanistic`, disjoint from Phase 1.0C, `task_ids_sha256`
  `0d3fe6add211a381a321ea974502d262faf65312dc504e2acceb7c6556b1f524`;
- protocol snapshot hash
  `fd52f2d58b59198512aff43eb826250dbadf9675306d8231af5809d3b763c84c`.

Registered budgets: 1024 new tokens for the visible-reasoning control, 32 for
both strict arms. The strict budget was verified, not assumed: the longest
registered answer in the selection is 15 UTF-8 bytes
(`p1hd-fact2-easy-confirmation-01`), and byte-level BPE guarantees
`token_count <= utf8_byte_length`, so 32 tokens is provably sufficient with 17
tokens to spare — and still far too few to emit a chain of thought. No
tokenizer download was needed for that proof.

Prompt rendering was checked on real material, not samples: all 300 items x 3
arms were rendered and asserted free of the literal `<answer>`, of any
`{slot}`-shaped leftover, and of any other angle-bracket placeholder. The
spontaneous strict arm was additionally asserted free of think tags, of the
empty-think prefill, and of any model-name-dependent text.

Artifact: `docs/phase1_0d_protocol_snapshot.json`.

Not established: nothing was generated, so no accuracy, no headroom, and no
capability statement exists. The next scientific gate is the Phase 1.0D
generation run itself, which needs GPU capacity that this work package did not
provision.
## 2026-08-02 - Phase 1.0D preregistration review and the single consolidated correction

The one bounded preregistration review of authority section 7 was performed
against the frozen protocol at commit `b07b90dba5b8b15a17516ba32a8c0be5f6cfa0af`
by two independent reviewers, before any Phase 1.0D generation existed. Neither
returned a FATAL finding. Four MATERIAL findings were corrected once; four
NONFATAL findings were recorded as L-45, L-46, L-47 and an enforced test guard.
The full record is `docs/audits/phase1_0d_preregistration_review.md`.

Both reviewers independently found the same primary defect: the arbitration rule
escalated a reviewer disagreement to a third adjudication that no code path
could ever supply, so a single routine disagreement permanently failed a cell
gate for a mechanical reason.

Azure runs, all ACR Tasks, `linux/amd64`, `python:3.11-bookworm`, dependency
closure `requirements.lock.txt`, source cloned from a git bundle so the build
agent checks out the exact commit itself:

| Run | Commit | Purpose | Result |
| --- | --- | --- | --- |
| `cm48` | `847d8a54` | Phase 1.0D execution pipeline, targeted | 25 passed |
| `cm49` | `b07b90db` | Cell-coverage reporting made a computed fact | 26 passed |
| `cm4a` | `b07b90db` | Full suite before the correction | 2971 passed, 15 skipped, 2 pre-existing failures |
| `cm4b` | `fa863d07` | Registry test path, mistyped | failed, no such test file |
| `cm4c` | `24464c3f` | Corrected protocol, targeted | 65 passed, 1 failed as designed |
| `cm4d` | `24464c3f` | Snapshot emit, body only | successful |
| `cm4e` | `95db5eb3` | Snapshot emit with disclosures | successful |
| `cm4f` | `4caafa96` | Snapshot emit naming its own run | successful |
| `cm4g` | `8c76b6ec` | Corrected protocol, targeted | 66 passed |
| `cm4h` | `8c76b6ec` | Corrected execution pipeline, targeted | 33 passed |

`cm4c` is the useful failure. The committed protocol snapshot carries a test
asserting it equals the recomputed protocol, so changing the protocol broke it
immediately and by name rather than leaving a stale preregistration in `docs/`.
That is the behaviour the self-verifying artifact was added for.

`cm4d` exposed a real defect in this operator's method rather than in the
repository. The emit script printed only the protocol body, and writing that
transcript over `docs/phase1_0d_protocol_snapshot.json` destroyed the
hand-authored wrapper carrying the authority binding, the consequences, and the
`not_established` disclosures. The fix was not to restore the wrapper by hand.
`PROTOCOL_CONSEQUENCES` and `PROTOCOL_NOT_ESTABLISHED` now live in the protocol
module and the emit script prints the whole artifact, so no part of a scientific
artifact is hand-authored and the disclosures cannot drift from the code they
describe. `cm4f` additionally reads `ACR_RUN_ID` from the task environment, so
the transcript names the run that produced it instead of being annotated
afterwards.

The correction moved `protocol_sha256` from `fd52f2d5...` to `25e96401...` and
the arbitration rule from `phase1_0d_arbitration_v1` to
`phase1_0d_arbitration_v2`. The item selection was untouched:
`task_ids_sha256` is still
`0d3fe6add211a381a321ea974502d262faf65312dc504e2acceb7c6556b1f524`.

All scientific counters remain zero. No Phase 1.0D generation has been run.

## 2026-08-02 - A registry integrity test found five malformed rows in the paper registries

Authority section 10 requires every scientific result to be registered in the
paper ledgers. Registering the section 4 results exposed that nothing in the
repository had ever validated those CSVs, so `tests/test_paper_registries.py`
was added: it refuses a row whose column count differs from the header, a
missing or duplicate identifier, an evidence row with no limitations, and an
artifact row that does not declare its privacy status.

It immediately failed on committed history rather than on the new rows.

| Registry | Row | Columns found | Columns declared |
| --- | --- | --- | --- |
| `table_registry.csv` | TAB-001 | 10 | 9 |
| `table_registry.csv` | TAB-003 | 10 | 9 |
| `table_registry.csv` | TAB-004 | 11 | 9 |
| `table_registry.csv` | TAB-005 | 10 | 9 |
| `figure_registry.csv` | FIG-003 | 11 | 9 |

Cause: the trailing `limitations` field of those rows contains commas and was
not quoted, so `csv.reader` split one field into several.

Scope of the damage, stated precisely rather than reassuringly. The overflow is
tail-only in all five rows: the identifier still matches its pattern, `status`
still reads `available`, and `generation_script` still names a `.py` file,
which could not be true if a leading field had shifted. So no recorded value had
moved onto a wrong header, and the repair quotes the field without altering a
character of the recorded text. What was actually at risk is a consumer that
reads these registries positionally: it would have read a truncated limitations
string for five exhibits, that is, an understated statement of what those
exhibits do not establish.

The test was also extended: every registered figure and table must now state
what it does not establish, not only every evidence row.

| Run | Commit | Purpose | Result |
| --- | --- | --- | --- |
| `cm4j` | `8c76b6ec` | Full suite after the preregistration correction | 3005 passed, 15 skipped, 4 failed: the 2 disclosed pre-existing failures plus the 2 registry defects above |
| `cm4k` | `109766da` | Full suite after the registry repair | 3009 passed, 15 skipped, 2 failed, both disclosed pre-existing |

Baseline for this work package was 2945 passed. The package adds 64 tests and
introduces no new failure.

Not established: this is a records-integrity repair. No measurement was taken,
no artifact was regenerated, and no scientific counter moved.

## 2026-08-02 — Phase 1.0D generation driver (code only, no generation run)

The frozen Phase 1.0D protocol and the pipeline that applies it both existed,
but nothing connected them to a model. This adds that connector:
`src/jspace_observation/phase1_0d_generation.py` plus the registered entrypoint
`scripts/run_phase1_0d_confirmation.py`, in four modes — `plan`, `self-test`,
`generate`, `finalize`.

What it emits is a pack, not a number. `00_protocol_snapshot.json`,
`01_selection.json`, `02_records.jsonl`, `03_review_form.jsonl`,
`04_generation_summary.json`, `05_decision.json`, `09_summary.md`, and
`artifact_manifest.json` written last and hashing every other file including
itself. In `generate` mode `05_decision.json` and the summary both carry
`AWAITING_SEMANTIC_REVIEW`: no headroom figure exists until the section 4.3
primary labels arrive, and the artifacts say so in those words rather than
reporting a provisional value.

Two real defects were found by writing this, and both were in code that already
existed and already passed its tests:

1. `compute_cell_outcomes` and `build_decision` treated a row with no
   `final_label` as resolved-and-incorrect. An unreviewed run would therefore
   have reported `HEADROOM_NOT_ESTABLISHED` with a clean-looking 0% — a review
   that never happened would have been indistinguishable from a model that
   failed every item. Both now raise on an unlabelled row.
2. The pipeline's own documented order was unexecutable.
   `annotate_review_selection` was documented as running before semantic review,
   but its forced component is defined by the primary label and it raises
   without one. The order is now recorded as it must actually run:
   `build_records` -> primary review -> `ingest_judgments` ->
   `annotate_review_selection` -> secondary review -> `apply_judgments`.

No generation-time stop sequence is registered. Section 4.2 permits a stop only
after a complete registered final-answer surface; declining to stop early always
satisfies that rule and cannot truncate a surface mid-write. The arm's
registered token budget is the only bound, and nothing is clipped afterwards.

| Run | Commit | Purpose | Result |
| --- | --- | --- | --- |
| `cm4m` | `5afba955` | Targeted generation-driver tests | Collection `ModuleNotFoundError`: the new test module lacked the `src` path insert every other module carries |
| `cm4n` | `0a160269` | Targeted, after the import fix | 16 passed, 7 failed, one cause: review selection called before any review existed |
| `cm4p` | `6c20078f` | Targeted, after the ordering fix | 24 passed |
| `cm4q` | `6c20078f` | Full suite | 3033 passed, 15 skipped, 2 failed, both disclosed pre-existing |

Baseline for this increment was 3009 passed. It adds 24 tests and introduces no
new failure.

Not established: **no generation has been run.** This is a driver that has been
exercised against a deterministic stub backend on CPU, which proves the pack is
well-formed and the accounting is honest — not that the model produces anything.
The Phase 1.0D headroom question remains open and no scientific counter moved.

## 2026-08-02 — Phase 1.0D confirmation image built and locked

The generation run needed a container image, and the Phase 1.0C image could not
be reused: reusing it would put a frozen historical record and a live one behind
the same repository, tag namespace and provenance generator. So Phase 1.0D got
its own — `Dockerfile.phase1-0d`, image repository
`j-space-observation-phase1-0d`, and its own build-provenance tool.

The design decision worth recording is that **the build is the verification**.
`Dockerfile.phase1-0d` runs three checks and cannot produce an image if any
fails:

1. `verify-runtime` — every pin in `requirements-calibration.txt` must match the
   installed distribution, plus the interpreter, the base torch and transformers;
2. `verify-image-context` — the baked source must hash to the committed bundle
   digest, file by file, with line endings normalised so a Windows checkout and
   a Linux one agree;
3. `verify-protocol` — the image must reproduce the frozen Phase 1.0D
   `protocol_sha256`, **including its 300-item selection**.

A near-miss worth recording. The first `verify-protocol` failed, reporting
`ef782fea…` against the frozen `25e96401…`. That looks exactly like a drifted
preregistration. It was not: the frozen hash covers a snapshot built *with* the
derived selection and the strict-budget check, and calling `protocol_snapshot()`
bare produces a smaller document. Reproducing the full document returned
`25e96401…` exactly. A test now pins both facts — that the full document
reproduces the frozen hash, and that the bare one does not — so the next reader
meets the trap as a documented fact rather than as a false alarm.

`.dockerignore` gained one narrowly scoped exception. The disjoint confirmation
split is defined against the item ids Phase 1.0C actually generated on, not
against a split label, so `02_records.jsonl` from run 20260725T170041Z must
travel in the image. Section 4.3 states every prompt and output in this work
package is public scientific data; the file carries no reviewer identity and no
private review material. The exception names that one file.

| Run | Commit | Purpose | Result |
| --- | --- | --- | --- |
| `cm4r` | `1497f74e` | Build-provenance tests | 21 passed, 2 skipped, 1 failed: the bare-snapshot protocol mismatch above |
| `cm4s` | `24e0d2e0` | Same tests after reproducing the full snapshot | 23 passed, 2 skipped |
| `cm4t` | `24e0d2e0` | Emit the provenance record | Failed: CRLF in the uploaded task script |
| `cm4u` | `24e0d2e0` | Emit the provenance record | Emitted 44 files, bundle `d1c0145f7aa22c509045073a5b31c8b470573c3338b5a3d540f11ca74b6f02b0` |
| `cm4v` | `9cde1d95` | Verify the committed record against a clean clone | 25 passed, 0 skipped |
| `cm4w` | `9cde1d95` | `az acr build` of `Dockerfile.phase1-0d` | Image built and pushed, digest `sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4` |
| `cm4x` | `dc6b5056` | Launcher-script tests | 34 passed |
| `cm4y` | `dc6b5056` | Full suite | 3067 passed, 15 skipped, 2 failed, both disclosed pre-existing |

The image tag and manifest are locked against write and delete, so the bytes
behind that digest can no longer change. Cleanup action: **retained
deliberately and permanently**; an image that could be deleted or overwritten
cannot serve as the provenance of a result.

Baseline for this increment was 3033 passed. It adds 34 tests and introduces no
new failure.

Not established: **the generation run still has not been performed.** A built
image proves what bytes are in it and nothing about the model. What remains
before a run is an ACA GPU job execution, and after it, the section 4.3 primary
semantic labels without which no cell metric may exist. No scientific counter
moved.
## 2026-08-03 — Phase 1.0D semantic-review provider gate

Final state: **`BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION`**.
No target generation run was performed, before or after this gate.

The section 3.1 rule is prospective: the registered reviewers must be deployed
and smoke-tested *before* any target inference. They were. One of eighteen
calls disagreed with its committed expected label, and the addendum's
`on_label_mismatch` rule makes that terminal.

| Azure run | Commit | What ran | Result |
| --- | --- | --- | --- |
| `cm52` | `5f56535d` | Protected-byte baseline tests | 11 passed |
| `cm53` | `91e12c8` | Semantic-review module | 71 passed, 1 failed: a credential guard matched "task-family" |
| `cm54` | `e7a1c7a` | Same module after narrowing the guard | 72 passed |
| `cm55` | `e7a1c7a` | Full suite | 3150 passed, 15 skipped, 2 failed, both disclosed pre-existing |
| `cm56` | `1baa683` | Review-image, provenance and launcher tests | 34 passed |
| `cm57` | `1baa683` | Full suite | 3184 passed, 15 skipped, 2 failed, both disclosed pre-existing |
| `cm58` | `1baa683` | Emit the review build-provenance record | 12 files, bundle `d1fbd985f959648ec178480ce26caf696152520f26f96bc8b4458cb6881f3b49` |
| `cm59` | `bda9b3b` | Verify the committed record against a clean clone | `REVIEW_IMAGE_CONTEXT_OK=1` |
| `cm5a` | `bda9b3b` | Verify the baked addendum and rubric | `REVIEW_ADDENDUM_OK=1` |
| `cm5b` | `bda9b3b` | `az acr build` of `Dockerfile.phase1-0d-review` | Digest `sha256:d9e887e68cccf7472e956785cda3ad7cf5f3902daea9287fc7b72c357f473e10`, tag and manifest locked |

| ACA execution | Mode | Result |
| --- | --- | --- |
| `job-jspace-p10d-review-qualify-d9e24fa` | qualify | Succeeded. All three roles answered on `/openai/v1/chat/completions`; no api-version parameter was needed. Receipt `efb94aed3e33b518f5e3703c3f7bd0c27534444a871e324e5d2a32fbca3d5048`. |
| `job-jspace-p10d-review-smoke-ifz4l7z` | smoke | Failed by design. 17 of 18 label matches. Receipt `eba6e2e48d3b7c30c61779629facc523975740b4a1f2d2be9e833b75fc7dda8e`. |

The one mismatch: fixture `smoke_unresolved`, role `primary`, deployment
`gpt-5-6-sol-global`, expected `unresolved`, observed `incorrect`. The fixture
shows an output that commits to two different final answers and explicitly
refuses to prefer either. The secondary and third reviewers both returned
`unresolved`.

Zero transport failures, zero malformed responses, zero schema failures, zero
4xx faults. That matters, because the addendum treats a route, api-version or
authentication fault as an ordinary defect to fix and rerun, and a semantic
label mismatch as terminal. This was the second kind.

Refused, in order, and recorded because each was available and each would have
been wrong: changing the fixture, changing its expected label, retuning the
rubric, substituting a reviewer model, adding a fallback or majority vote over
the mismatch, rerunning the gate after seeing its output, and starting the
target generation run anyway.

Evidence export: the in-container receipt JSON was hashed by the job and left
on the job's ephemeral filesystem. The job mounts no writable share and never
reached its upload stage, so the exported record is the Container Apps console
transcript from the environment's Log Analytics workspace, which carries the
hashes the job computed. Re-running either stage purely to export a file would
be a second inference attempt at a gate whose output has been seen.

Baseline for this increment was 3150 passed. It adds 34 tests and introduces no
new failure.

Not established: nothing about reviewer accuracy in general, nothing about the
other two reviewers, nothing about model capability, and nothing about the
Phase 1.0D task bank, which was never generated on. No scientific counter
moved. `AWAITING_SEMANTIC_REVIEW` remains the honest status of Phase 1.0D.

### Closing verification for the gate round

| Azure run | Commit | What ran | Result |
| --- | --- | --- | --- |
| `cm5c` | `2e343e2` | `scripts/phase1_0d_protected_bytes.py verify` | 152 files, rollup `436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd`, `PROTECTED_BYTES_OK=1` — unchanged from the baseline |
| `cm5d` | `2e343e2` | Full suite | 3185 passed, 15 skipped, 2 failed, both the disclosed pre-existing `tests/test_parser_v3_seal_job.py` cases |

The suite is one test larger than `cm57` (3184) because the launcher interpreter
resolver gained a regression test: on this Windows host `command -v python3`
returns the Microsoft Store App Execution Alias, which exits 49 without running
Python, so both launchers now walk `type -aP python3 python` and keep the first
candidate that actually answers as Python 3. Against the older 3067-passed
figure recorded for `cm4y`, this round is +118 tests and no new failure.

Nothing in the gate round touched a protected byte: the new artifact prefix
`artifacts/phase1-0d-semantic-review-gate/**` matches no protected glob, and the
rollup confirms it.

## 2026-08-03 — Phase 1.0D semantic-review v2 round

Authority: `docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md`,
SHA-256 `7b93c90a299ff4e77b83d4633624053f8ce53afcd04279ca3050c5ab14428e19`.
It authorizes a forensic correction of the v1 interpretation, exactly one
re-frozen v2 reviewer instrument, exactly one v2 qualification and smoke, and —
only on a 60/60 smoke pass — the single already-preregistered Phase 1.0D
generation, review and finalization. There is no RV3.

Starting state verified before any edit: `origin/main`
`4668ef371b89162a45cbccb57939f9f68571c9f7`, tree
`811ec140c82bcd190d49de9686d426cec3991f89`, worktree clean,
`5ae85cb838ff2c8d296ee90b10f1ca2e9f885b0a` still an ancestor, and Azure run
`cm5e` reproducing the protected rollup `436ed331…` over 152 files.

| Azure run | Commit | What ran | Result |
| --- | --- | --- | --- |
| `cm5e` | `4668ef3` | `scripts/phase1_0d_protected_bytes.py verify` | 152 files, `436ed331…`, `PROTECTED_BYTES_OK=1` |

**Forensic correction first, because it changes what the v2 instrument has to
fix.** The v1 stop stands as procedurally correct and terminal, but its recorded
cause was wrong: the frozen rubric's rule 3 selects the last complete literal
`Final answer:` surface, rule 4 fires only "with no rule selecting one", and the
fixture `smoke_unresolved` registers `unresolved` on the strength of prose that
appears after that surface. `incorrect` is what strict in-order execution
returns. Recorded as `EV-0013`, `D26`, `L-52`, `M-16` and
`docs/decisions/phase1_0d_semantic_review_v1_specification_correction.md`, with
dated pointers appended to `D25` and `L-50` and no original byte rewritten.

### Pre-execution qualification attempt 1 — inert Azure readback mismatch

ACR QuickRun `cm82` built commit
`c7d5848b71bc546a2bd5c55fd224c4ed7b7caed1` as
`j-space-observation-phase1-0d-review-v2@sha256:5e1d6c63df5cd5866b7b8b2d81c073167cb62b3801460d917b2d3189eba352ae`.
Both its tag and manifest were locked against write and delete.

Qualification run ID `20260803T223953Z` provisioned the unique inert ACA Job
`job-p10d-rv2-q-30e62394facd117d`, then stopped before `job start`. The Azure
resource provider added `"ephemeralStorage": ""` to the returned container
resource object; the launcher compared that service readback to an object
containing only CPU and memory and failed closed. The Job has zero executions,
so this attempt made zero provider calls, obtained zero semantic responses,
wrote no qualification receipt, and consumed neither the smoke lock nor a
scientific counter.

Section 10.1 permits repair of a transport/configuration defect that produces
no valid semantic response before smoke. The repair accepts only the platform's
absent-or-empty ephemeral-storage field while retaining exact CPU and memory
checks; a non-empty value or any other extra resource field remains terminal.
The locked `cm82` image is retained unchanged. No model, version, route
candidate, request profile, rubric, fixture, expected label, or retry rule
changed.

### Pre-generation control-plane readback preflight

After the v2 qualification and sole 60-call smoke passed, but before any
generation lock or generation Job existed, an inert control-plane-only probe
provisioned `job-p10d-gen-rb-09a2a2507a2e` with the exact registered
`gpu-t4`, 8 CPU and 56Gi resource request. It was never started and has zero
executions. The current `2024-03-01` ARM readback returned:

`{"cpu":8.0,"ephemeralStorage":"","memory":"56Gi"}`

This proves the frozen generation launcher's literal two-key resource
comparison would fail after its create-only permanent generation lock, before
`job start`. No target prefix, target output, model call, scientific counter,
generation Job, or generation lock was created by the probe.

The authority forbids changing the target experiment and the v2 protected-byte
record pins launcher `19`; both remain unchanged. An additive operational shim
therefore executes the exact frozen launcher and intercepts only its one final,
unqueried GET of `job-jspace-p10d-confirmation`. It requires the exact Job name,
`gpu-t4`, one container, 8 CPU and 56Gi, accepts only absent or empty
platform-owned `ephemeralStorage`, rejects every other resource shape, removes
only that empty field, and delegates every other Azure CLI call unchanged.

Azure targeted run `cm8r` verified commit `b966f14` with 90/90 tests, including
the compatibility-shim tests, generation-launcher provenance tests, and both
v1/v2 protected-byte suites. Private preflight execution
`job-p10d-gen-pre-caa913346f28-jpqlx2w` independently observed
`generation-execution-lock.json` absent and zero objects under
`phase1-headroom-confirmation/`; it also confirmed `/usr/bin/az`,
`/usr/bin/python3.11`, the unchanged launcher SHA-256, and the exact
absent-or-empty normalization behavior.

### Pre-generation operator attempt 1 — inert missing `cmp`

Run ID `20260804T152940Z` was presented to private orchestrator execution
`job-p10d-gen-orch-48f38b1280d8-0h7z3av`. Its separate control-plane
authorization probe provisioned successfully with zero executions. The frozen
launcher then reverified both protected rollups and downloaded the exact
committed and create-only Blob smoke evidence, but the operator helper image
lacked the `cmp` utility required for the byte comparison at launcher line 432.
It stopped before the global generation lock, target Job provisioning, or
`job start`.

Post-failure private execution
`job-p10d-gen-pre-caa913346f28-8899hc0` reconfirmed lock absent, target-root
object count zero, and target Job absent. The orchestrator identity's temporary
Reader, Container Apps Jobs Contributor, and Managed Identity Operator
assignments were all revoked; remaining temporary role count was zero.

This is an operator-image dependency defect, not a target or review-instrument
change. ACR build `cm8s` added only Azure Linux `diffutils` to the prior locked
helper and verified `cmp`, trusted Python, Azure CLI, and pinned containerapp
extension paths during the build. The replacement helper is
`j-space-observation-operator@sha256:9bfa04ea63086aaabccd3bd1d31eb0dcf1f883a68e31e34d838914bbae534a4c`;
its tag and manifest are both locked against write and delete.

### Sole Phase 1.0D generation

Replacement-helper private preflight
`job-p10d-gen-pre-f5998a9a235b-26w5jfn` verified `cmp`, exact pushed commit
`45bb96a`, lock absent and target-root object count zero. Private orchestrator
`job-p10d-gen-orch-2a8a43cd1ac9-fend5zv` then passed its separate zero-execution
control-plane authorization probe, reverified the v1 and v2 protected rollups,
verified the exact committed 60/60 gate against create-only Blob bytes,
normalized only Azure's empty `ephemeralStorage` readback, and started the sole
GPU execution:

| Field | Exact value |
| --- | --- |
| generation run | `20260804T154518Z` |
| ACA execution | `job-jspace-p10d-confirmation-pdlhmah` |
| profile / GPU | `gpu-t4` / one Tesla T4 |
| image | `j-space-observation-phase1-0d@sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4` |
| timeout envelope | replica 21600s / in-container 21300s |
| start / end | `2026-08-04T23:50:12+08:00` / `2026-08-05T01:52:42+08:00` |
| terminal state | `Succeeded` |
| Blob prefix | `phase1-headroom-confirmation/20260804T154518Z/` |
| manifest SHA-256 | `76accb0f675130989f3db698ecfeaa8736f288980026cdaca0e8413c05234536` |

Exactly one target execution exists. The temporary Reader, Container Apps Jobs
Contributor and generation-identity Managed Identity Operator assignments were
removed immediately after child start; remaining temporary role count is zero.

Private verification execution
`job-p10d-gen-verify-db2fc9df0da4-g8jqbue` observed the exact eight-object
manifest-last prefix and independently ran the frozen v2 source-pack verifier:
300 selected items, 900 ordered records, 900 rebuilt work units, 900 rebuilt
review-form rows, exact raw member hashes, recomputed selection and telemetry
aggregates, and status `AWAITING_SEMANTIC_REVIEW`. No semantic label or cell
metric exists at this stage. The exact create-only manifest is committed under
`artifacts/phase1-0d-confirmation/20260804T154518Z/`.

### Sole formal v2 semantic review — terminal transport failure

The committed source manifest licensed exactly one formal-review launch.
Private orchestrator `job-p10d-rvo-9f4cc351a79a-bvysm2t` passed the frozen
source-license checks, created the permanent formal-review lock, started the
child, and revoked all three temporary launcher grants:

| Field | Exact value |
| --- | --- |
| review run | `20260804T181247Z` |
| ACA job | `job-p10d-rv2-r-d4a84a59bc28a91f` |
| ACA execution | `job-p10d-rv2-r-d4a84a59bc28a91f-tjzwlse` |
| start | `2026-08-05T02:17:39+08:00` |
| image | `j-space-observation-phase1-0d-review-v2@sha256:b3cf2c5933fe296c6a4d59eba9d73c3f10fc42bdddc494b25b679ca679b449dd` |
| source verification | 8 files; 900 records rebuilt |
| terminal status | `Failed` |
| exact registered terminal state | `BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT` |

The primary-review stage raised the registered terminal exception:

`TransportError: primary exhausted 8 identical attempts; last status 429 error None`

No rerun, deployment substitution, quota workaround, concurrency change,
rubric edit, fixture edit, role change, target-pack change, or parser restart
was made. Concurrent primary requests were already in flight, so the console
trace does not establish an exact aggregate provider-call count or whether
another row received a valid response. No partial judgments were sealed, and
none are reconstructed or counted.

Independent private inventory
`job-p10d-review-state-183db2bc-9bc4h8l` subsequently established:

- the permanent formal-review lock exists and hashes to
  `d7b184b486e757ba0a7702c41300157627e03616b873555d87ea27ada7d7e93f`;
- the source generation prefix still contains exactly eight objects;
- `phase1-headroom-confirmation-review-v2/20260804T181247Z/` contains zero
  objects.

Therefore no result manifest, final semantic label, cell metric, candidate
cell, cost/latency aggregate, or scientific decision exists. The generation
pack remains immutable with status `AWAITING_SEMANTIC_REVIEW`; its 900 rows are
licensed for review but did not complete primary review. The sanitized
terminal archive is
`artifacts/phase1-0d-semantic-review-v2-formal/20260804T181247Z/`.

### Closing-verification transition correction

ACR runs `cm8t` and `cm8u` were inert task-context failures: both uploaded
temporary shell scripts with CRLF and stopped at `set -o pipefail` before
cloning the repository or running any check. The scripts were normalized to LF
without changing the committed tree.

At commit `73ac00c`, ACR run `cm8w` then passed both protected-byte verifiers
and the terminal-archive verifier:

- v1: 152 files, rollup `436ed331…`, unchanged;
- v2: 36 files, rollup `ef5a417c…`, unchanged;
- terminal archive: four members, manifest SHA-256
  `41694a6b9593756d3cbed3014367887567f5e785840dce86bceb2da41a39c204`.

Full-suite run `cm8v` produced the two disclosed parser-seal failures plus one
new failure in `test_no_target_output_is_present_in_the_build_context`. The
underlying provenance guard was correct when the v2 review image was built:
its locked build bundle contained no target output. The test incorrectly
applied that pre-generation invariant to the live repository after the
authorized generation manifest had been committed. The correction reconstructs
the locked build bundle's path set from its verified provenance record and
tests the no-target-output guard there; a separate assertion pins the live
repository to the one authorized generation manifest. No protected byte,
image, target output, reviewer instrument, or scientific datum changes.

At correction commit `b6e1b3e`, the Azure closing gates were:

| ACR run | Scope | Result |
| --- | --- | --- |
| `cm8y` | v1/v2 protected bytes plus terminal archive | 152-file `436ed331…` and 36-file `ef5a417c…` rollups unchanged; archive manifest `41694a6b…`; passed |
| `cm90` | v2 review-image focused module | 64 passed |
| `cm8x` | full suite | 3336 passed, 15 skipped, 2 failed; both are the disclosed pre-existing `tests/test_parser_v3_seal_job.py` cases |

Against the required 3185 passed / 15 skipped / 2 disclosed-failure baseline,
the final suite is +151 passed / +0 skipped / +0 failures. There is no new
failure.

### Exact retention state

Read-only Azure inspection after the terminal archive confirmed that the
generation image, v1 review image, v2 review image, and replacement operator
helper manifest all have `writeEnabled=false` and `deleteEnabled=false`.
Every Phase 1.0D gate, probe, orchestrator, generation, verification, formal
review, and partial-state-capture Job remains retained. The target generation
Job has exactly one execution, succeeded; the formal-review Job has exactly
one execution, failed.

The retained `AIServices` account
`aif-jspace-p10d-review-eastus2`, review UAMI
`id-jspace-p10d-review-sea`, and registered deployments remain live. The three
temporary formal-review launcher assignment IDs each have count zero. No Job,
Blob, image, deployment, identity, lock, or scientific artifact was deleted.
ACR QuickRuns are the only ephemeral resources.

Final scientific state:
**`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT`**. The smallest next gate is an
operator recovery decision about the registered transport capacity. It is not
authorization to rerun, change concurrency, substitute a deployment, edit the
instrument or target pack, start an RQ2 pilot, run J-lens, or restart parser
work.

## 2026-08-05 - Phase 1.0D review-only transport recovery authorized

The independent recovery authority was frozen unchanged at
`docs/prompts/phase1_0d_review_only_transport_recovery_prompt.md`, SHA-256
`dc350039f118cb5931dab08fd65e24ed169757c472898b7dbe8d27eb3ce2f92b`.
D28, L-54, and M-18 define the one-execution boundary, the permanent
unquantifiable prior-response resampling exposure, and the capacity-only
method. No scientific evidence item was created for this authorization.

The starting-state gate reauthenticated:

- `origin/main` `d145b1c79db8b6866fadaa8875c2374a813a7e31`, tree
  `b4329a4062415cf7cb3b058d3defe6da7c14f25c`, clean, with `5ae85cb...`
  retained as an ancestor;
- v1 152-file rollup
  `436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd`
  and v2 36-file rollup
  `ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a`;
- all three immutable review/generation image digests and write/delete locks;
- the 60/60 v2 gate, exact eight-object 900-row source license, sole generation
  execution, sole failed formal execution, old terminal receipt/archive, and
  old formal lock.

Retained private verifier
`job-p10d-review-state-183db2bc-c4jlgqz` succeeded and freshly observed source
object count 8, old result object count 0, and old lock SHA-256
`d7b184b486e757ba0a7702c41300157627e03616b873555d87ea27ada7d7e93f`.
A second retained read-only verifier execution,
`job-p10d-gen-verify-db2fc9df0da4-3c0826z`, failed closed at its obsolete
hard-coded Git-HEAD assertion before reaching Blob verification. Neither
execution contains an inference command or changed a Blob. No provider call,
capacity mutation, recovery Job, recovery lock, or recovery result exists at
this checkpoint.

## 2026-08-05 - Phase 1.0D transport recovery stopped at capacity

### Recovery tooling and Azure verification

The fail-closed recovery tooling, public certificate schema, fixed launcher and
36 focused controls were pushed in three fast-forward checkpoints:

- `db873b465ed841798a091b5c4b4a423bdf22ec44`;
- `83d7a8ad3d761e205fb5217e9a6899a4351f4022`;
- `34404a89a3e63c4eea808485c353e6c7f49f8c49`.

At `34404a89`, authoritative Azure run `cm9c` passed all 36 focused controls.
Full-suite run `cm9b` returned 3372 passed / 15 skipped / 2 failed; both
failures are the disclosed pre-existing
`tests/test_parser_v3_seal_job.py` cases. This is +36 passed / +0 skipped /
+0 failures against the 3336 / 15 / 2 baseline. Protected-byte runs `cm9d`
and `cm9e` reproduced the v1
`436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd`
and v2
`ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a`
rollups. Earlier `cm93`-`cm99` attempts were non-authoritative context,
line-ending or unpinned-test-dependency failures and made no Azure AI call.

### Private state and capacity evidence

Retained non-provider collector Job `job-p10d-tr-cap-34404a89` ran under
`id-jspace-aca-acrpull-sea`, which has zero Cognitive Services roles.
Executions `3o0clkb` and `fucpyxy` independently observed:

- exact source object count 8 and manifest
  `76accb0f675130989f3db698ecfeaa8736f288980026cdaca0e8413c05234536`;
- old result object count 0 and old formal-lock hash
  `d7b184b486e757ba0a7702c41300157627e03616b873555d87ea27ada7d7e93f`;
- recovery lock absent, recovery result object count 0 and recovery Job count 0;
- exact 900-row request-body rollups `7347d134...`, `f3348c56...` and
  `ddd2ed53...`, with ordered record-ID hash `4cc29857...`.

The final evidence window ended with these exact deployment readbacks:

| role | capacity before/after | TPM / RPM | floor TPM / RPM | usage | exact available model capacity | mutation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| primary | 36 / 36 | 36,000 / 36 | 1,000,000 / 1,000 | 1,000 / 1,000 | 0 | none |
| secondary | 50 / 50 | 50,000 / 50 | 500,000 / 500 | 50 / 1,000 | 950 | none |
| third | 50 / 50 | 50,000 / 50 | 1,000,000 / 500 | 50 / 1,000 | 950 | none |

The primary allocation cannot reach its floor under existing quota. Mutating
secondary or third cannot make the overall gate pass, so no deployment was
changed. Exact 60-minute deployment-filtered Monitor queries returned 0
requests, 0 HTTP 429s, 0 prompt tokens and 0 generated tokens for every role.
All four role metric timeseries were empty and are recorded as such. The final
15-minute account-wide quiet window returned 0 registered and 0 non-project
requests.

### Create-only blocked certificate

The final non-provider sealer image was ACR-built in `cm9k`, verified during
build against the frozen reviewer profiles and exact Git-blob source/archive
hashes, and locked at
`sha256:1c04065228bf57f042069e32b8f05e613c2e7e536a8c98ba755a804bfc2d1d32`.
Earlier build runs `cm9f`, `cm9g`, `cm9h` and `cm9j` are retained. Their image
tags and manifests are also write- and delete-disabled.

The retained Job `job-p10d-tr-seal-34404a89` has four executions:

| execution suffix | result | boundary |
| --- | --- | --- |
| `ripscxe` | Failed | Python package path; before Blob |
| `z9uam21` | Failed | eager `torch` import; before Blob |
| `sfbyzvb` | Failed | worktree CRLF differed from exact Git manifest bytes; read-only Blob access, before any write |
| `jyi7tki` | Succeeded | canonical create-only seal and exact readback |

Every execution used the non-provider identity and issued zero Azure AI
inference calls. The successful execution sealed exactly two objects under
`phase1-0d-semantic-review-v2/transport-recovery/capacity/20260805T180417Z/`:

- `00_capacity_certificate.json`, SHA-256
  `20e486e05a5f076b720ca12db3459b5a1c2c42e95684977dfdcff19d6da055d3`;
- `artifact_manifest.json`, SHA-256
  `23016ad15430b1720e4b37033a3638bf45e817ac00513292d138d26e0ed0a834`.

The 38 mechanical gates passed 35 and failed only
`primary.capacity_floor`, `secondary.capacity_floor` and
`third.capacity_floor`. `provider_calls=0`; capacity mutation, recovery Job,
recovery lock, recovery execution and recovery result object counts are all
zero. No temporary role assignment was created, so the teardown-ID list is
empty.

Exact state:
**`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`**. This is operational
evidence only. No evidence-ledger row, semantic label, cell metric, candidate
cell or scientific decision was created. The smallest next scientific gate is
unchanged: J-lens S3 validity-protocol design can proceed independently. The
same transport-recovery authority can resume only after an operator
independently makes sufficient quota available on the same deployments.

### Final launcher repair and closing verification

The final integrity pass found one launcher defect after the blocked
certificate was already sealed: the source-manifest `cmp` command was placed
inside a Bash `[[ ... ]]` expression. Bash printed `conditional binary
operator expected`, but `bash -n` returned zero for this construct, so the
original syntax test had produced a false pass. ACR run `cm9r` exposed the
diagnostic. Commit `9287b86c1eb5a051c7a7223f4e72631cb649351e` moved `cmp`
outside the conditional expression and added a structural regression
assertion. The repair changes no recovery identity, image, source, reviewer,
request, capacity, lock, result, or execution contract.

Runs `cm9m`, `cm9n` and `cm9p` uploaded an incorrect context root and therefore
did not execute repository checks; they are non-authoritative context
failures. `cm9q` and `cm9s` reconfirmed the focused and full-suite baselines
while the launcher diagnostic was investigated. The final authoritative runs
at `9287b86` were:

- `cm9t`: capacity-pack and protected-byte integrity succeeded;
- `cm9u`: all 36 focused transport-recovery controls passed;
- `cm9v`: 3372 passed / 15 skipped / 2 failed, with only the two disclosed
  pre-existing `tests/test_parser_v3_seal_job.py` failures.

The final read-only collector attempt
`job-p10d-tr-cap-34404a89-bq7yh0q` failed before Blob access because its
retained command still required cloned `main` to equal `34404a89` after the
later fast-forward pushes. The Job command was changed only to check out that
exact frozen ancestor before running the same verifier. Execution
`job-p10d-tr-cap-34404a89-zpno3bl` then succeeded under the same identity with
zero Cognitive Services roles. Its bounded readback observed source object
count 8, capacity object count 2, old result object count 0, the unchanged old
lock hash, no recovery lock, no recovery result object, and the same three
900-row request-body rollups. It issued no provider call, made no capacity
mutation and wrote no Blob.

Final ACR inventory reconfirmed write- and delete-disabled tags and manifests
for the generation image
`sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4`,
v1 review image
`sha256:d9e887e68cccf7472e956785cda3ad7cf5f3902daea9287fc7b72c357f473e10`,
v2 review image
`sha256:b3cf2c5933fe296c6a4d59eba9d73c3f10fc42bdddc494b25b679ca679b449dd`,
and final capacity-sealer image
`sha256:1c04065228bf57f042069e32b8f05e613c2e7e536a8c98ba755a804bfc2d1d32`.
The exact terminal state remains
**`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`**.

## 2026-08-06 — J-lens S3 validity protocol design and freeze

This was a design-only Stage P run under
`docs/prompts/phase_s3_jlens_validity_protocol_design_prompt.md`
(SHA-256
`5d39859bc3d75143f3fdcb469de1d199ad7f831d474509b605569cdc9c1814b8`).
The required starting commit
`31e8fc87cb560d141bada0aeb7d3b60c45f30081` and tree
`6132b43523c97c98722c094216c914f96b9dcd50` remained ancestors and protected
Phase 1.0D bytes were not edited.

### Public inputs and candidate

The six allowed upstream files were vendored byte-for-byte from
`anthropics/jacobian-lens` commit
`581d398613e5602a5af361e1c34d3a92ea82ba8e`. Model-free validation reproduced
93 multihop, 55 order-operations, 90 causal-swap items, 29 oriented
counterparts, and 24 unique unordered pairs.

The complete candidate package was added in `f84cbef`, followed by the
`token_ids` output-type fix in `cd061d7` and deterministic duplicate-base-triple
counterpart tie-break in `36b5482`. ACR run `cma2` bound commit `36b5482` /
tree `632b99f91daa4b071a1f1ebaee19b03c17796fc3`, returned protocol SHA-256
`eed211b11020851651bdcc4142e0e0c0d402e9814e9c7ede510667d425f897d4`,
reproduced 29/24 counterparts, and passed all 52 focused tests.

Non-authoritative setup failures are retained: `cm9w` failed on a CRLF shell
context before repository validation, and `cma1` failed because a Windows
absolute task-file path was interpreted inside the ACR workspace. `cm9x` and
`cm9y` were useful fail-closed candidate diagnostics; `cma0` was a bounded,
model-free counterpart diagnostic. None loaded or executed a model or lens.

### Single methods review and correction

The one bounded review targeted exact candidate commit `36b5482`, tree
`632b99f9`, and protocol hash `eed211b1...`. It asked only the six registered
questions and returned 0 FATAL / 2 MATERIAL / 0 MINOR. The one consolidated
correction commit `3954e6e`:

- qualified official role-row identity by immutable source distribution and
  explicitly allowed, but never merged, cross-distribution content overlap;
- replaced the noncomputable synonym wording with an exact row-level
  `hard_surface_rule` over `e0_item`, `e0_surface`, and true-label
  `readout_rank`.

ACR run `cma3` bound `3954e6e` / tree
`dbb275b3ae7e0cd41af365dbac14b103c18ee0a7`, reproduced protocol SHA-256
`bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625`
and schema SHA-256
`5d6e2fc33771b427130bd1dbe94c79cdf6d5827288b96929352c0caa793acbf1`,
and passed all 55 focused tests. Same-checklist verification resolved both
findings, introduced no contradiction, and closed at 0 FATAL / 0 MATERIAL /
0 MINOR. The S3 methods-review allowance is spent.

### Frozen result and zero-operation boundary

The freeze record is
`docs/decisions/jlens_s3_validity_protocol_freeze.md`. It binds the canonical
protocol, schema, Markdown crosswalk, completed review, provenance manifest,
authority, and validator source bundle to exact committed-byte SHA-256 values.

No target-model or tokenizer load, real lens load/fit/apply/inspection,
target-model inference, clean-behavior screening, activation extraction,
coordinate swap, ablation, patching, GPU Job, semantic-review provider call,
scientific evidence row, or RQ2 run occurred. `paper/evidence_ledger.csv`
therefore still ends at `EV-0014`. The design result is
**`NONTERMINAL_CHECKPOINT_JLENS_S3_VALIDITY_PROTOCOL_FROZEN_AWAITING_S2_LENSES_AND_EXECUTION`**.
Phase 1.0D simultaneously remains
**`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`**.

### Final ACR verification and historical-image integration

Final focused run `cma5` bound ledger commit `4aa7b34` / tree
`adf61339a397047038c936e27764ed026ce574d9`, reproduced every frozen hash and
29/24 counterpart count, passed all 55 S3 tests, confirmed `EV-0014` remained
the final evidence row, and verified D30, M-20, L-56--L-61, AR-0067--AR-0082,
claim states, review closure, source-bundle bytes, and both simultaneous project
states.

The first full run, `cma4`, correctly exposed one new integration failure:
the historical Phase 1.0D build-provenance test treated the newly authorized
top-level S3 module as if it had existed in the old frozen image. An attempted
`.dockerignore` isolation at `0e068ee` was rejected: although focused `cma6`
passed, full run `cma7` proved `.dockerignore` itself is frozen in the v2 review
image context. That input was restored byte-for-byte.

Commit `32f14af` instead changed only the non-protected historical provenance
test. It now:

- rebuilds the old image-context projection from the record's exact 44 files
  and verifies every recorded byte;
- requires the unchanged old build verifier to reject the current repository
  only for the authorized later
  `src/jspace_observation/jlens_s3_protocol.py` addition and consequent bundle
  digest drift.

Thus no old Dockerfile, provenance record, manifest, protocol, generation/
review/capacity source, or other protected byte changed, and any attempted old
image rebuild from the expanded current context still fails closed.

Full-suite run `cma8` bound commit
`32f14afb41140666dd54a79dd2c03b970eaabf75` / tree
`2f04862f59ca5516e1179f8bc6def35285fe2a54` and completed with:

- 3427 passed;
- 15 skipped;
- exactly the two disclosed historical
  `tests/test_parser_v3_seal_job.py` failures;
- delta from the 3372 / 15 / 2 authority baseline:
  **+55 passed / +0 skipped / +0 failed**.

## 2026-08-06 to 2026-08-07 - Full-layer J-lens S2 execution and seal

The run followed S2-G0 through S2-V0 in order under
`docs/prompts/jlens_s2_full_layer_and_s3_e0_execution_prompt.md`. Starting
commit `72336f822a8ffdbd2e0caf40f4a62c68cce68156` and tree
`d0592ae0b0edb62b4f082c0a12a9bcafe5693ee5` remained ancestors. Frozen S3,
Phase 1.0D, D25--D30, and `.dockerignore` bytes were not changed.

The canonical S2 protocol fixed model revision
`ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`, upstream J-lens commit
`581d398613e5602a5af361e1c34d3a92ea82ba8e`, layers 0--26 to target 27,
128 tokens, `skip_first=16`, and exact 600/600/200/2 roles. Azure resolved
WikiText revision `b08601e7c05d0c1b2f9d4a6039cf782e095e8629`, scanned 1,801,350 rows,
found 378,511 eligible unique sequences, and sealed the first 1,402 by the
frozen role key.

Four full-layer T4 smoke Jobs measured `dim_batch` 1, 2, 4, and 8. Every job
returned all 27 finite matrices and stayed below the memory ceiling. Only
`dim_batch=1` met the 1e-5 max-absolute and relative-Frobenius equivalence
limits, so production used 1. The deterministic wall-time planner split the
final 344-sequence increment into 59/59/59/59/59/49.

Eighteen primary shard starts against quota five produced four successes and
14 infrastructure failures. Exact checkpoint resumes and from-scratch retries
eventually produced all 18 successful registered shard states. In total there
were 33 attempts, 18 successes, 15 failures, and six checkpoint-bearing
partials. Every registered A/B contribution appears once in the successful
lens states. The exact number of computations repeated after an unpersisted
timeout suffix is unknowable; the registered bound is zero through 42.

Official cumulative merges produced A64/A128/A256/A600 and
B64/B128/B256/B600. M1200 was produced only as the official equal-weight
600:600 merge of A600 and B600. All merge-vs-independent and lossless
save/load maximum absolute differences were zero. A/B maximum across-layer
relative Frobenius distances were 0.217365, 0.157403, 0.112630, and 0.073860;
the non-gating fitted exponent was 0.482675. Five heldout Jobs covered all 200
registered sequences and the aggregate verified all 16,200 expected finite
pair-layer metric rows.

Two verification attempts were retained as operational failures: the first
rejected a CRLF-derived production-plan hash, and the second stopped on a
missing verifier `os` import before writing seals. The corrected immutable
verifier image
`sha256:e0fec8e76a98be692d0f1f8631ca14c3978897fe765edc07db96ee97a5eae757`
then independently verified the complete input graph and wrote the canonical
seals and manifest create-only. A read-only export independently reconstructed
and SHA-checked every small seal object.

The S2 manifest is
`9d10a4b07a8133b7241ce9067649ebf1de48429cf7c04e0495b4c3fe90e58e47`;
the closed pack is
`2dfc9bee037673f7bf33dddd863a3ce77cbe64482c72f06fd689c519a4041ddc`.
No official S3 benchmark tokenization or model pass preceded the seal. The
state is
**`NONTERMINAL_CHECKPOINT_JLENS_S2_SEALED_AWAITING_S3_E0`**.

## 2026-08-07 - Frozen S3 E0 execution and terminal verification

The exact E0 source bundle was frozen at SHA-256
`95b8cede932e1ed298e5f675075530a8b1560c0aa9049abfa0c6feebf38f9085`.
The distinct image build `cmbk` produced immutable digest
`sha256:17d664e13d67d79d99e7bf521bce9b7aefa946d33e25ec5ebe4cc7bc0aeff6cc`.
The empty-prefix preflight and read-only image verifier passed with zero
benchmark operations.

Three non-scientific harness failures are retained. ACR run `cmbh` interpreted
a Windows absolute task-file path inside its workspace and ran no test. Image
verifier runs `cmbm` and `cmbn` failed respectively on CRLF in the external
shell wrapper and because the ACR source mount hid the image workspace. The
corrected read-only Container Apps verifier
`job-js-e0-imgverify-67b72c2-5lg12he` recomputed all source, protocol, schema,
and benchmark hashes. None of these attempts tokenized a benchmark item or
called the model.

Lock creation `job-js-e0-lock-081017-1kglmch` wrote one create-only 2,561-byte
object with SHA-256
`8417ec21a512f51dac094facd3e7769f0d00b8b8ee896a7e11aeb4a7acb44c1b`.
Independent readback `job-js-e0-lock-read-081017-27xh0q6` verified the lock,
image-local bytes, S2 manifest, three lens seals, one-object namespace, zero
pre-lock benchmark operations, and zero authorized lens operations.

The sole execution was started once as
`job-js-e0-run-081017-yi5acvy`. The client-side wait was interrupted after the
start, but the Azure execution continued unchanged and succeeded; no second
start was issued. It ran from 08:22:10Z through 08:28:52Z, with 254 observed
GPU-container seconds and 234.9299 core E0 seconds.

The execution sealed:

- `e0_item.jsonl`: 250,605 bytes,
  SHA-256 `698bfaa830c5f19c41a79ed4059d848464d09d47c73dede72eba678c2e45cfd4`;
- `e0_surface.jsonl`: 339,433 bytes,
  SHA-256 `0b0c6d8393c8eb5ed4495b3d555790666ccd5381cb32313a911ed1f74f5f9a86`;
- `eligibility_split_manifest.json`: 1,585 bytes,
  SHA-256 `aaa8ac7526824da3ea5bfe1e07508ccfbb490d939d32ca9105d7a39847ec89c1`;
- manifest-last `artifact_manifest.jsonl`: 1,726 bytes,
  SHA-256 `6d11b09b39bbeead9b38fdb23be47a4247245fb55e6b6b665b817241519df60f`.

Independent S3-V0 Job `job-js-e0-verify-081017-5bsodon` downloaded the exact
five-object lock/output set, found zero partial objects, validated 238 item
rows and 962 surface rows, reconstructed the frozen rules and splits, and
reproduced every count and floor. The first optional S2 final-diagnostic export
Job `job-js-s2-final-export-081017-wb2188g` failed read-only on an incorrect
assumption that checkpoint manifests carried `fit_seconds`; it wrote nothing.
Corrected read-only export
`job-js-s2-final-export2-081017-r02w5ku` succeeded and preserved the exact
per-layer and heldout diagnostic rows plus all six partial checkpoint
manifests.

E0 performed 151,665 vocabulary-token decodes, exactly 238 item tokenizations,
and exactly 238 model forwards. It performed zero lens imports or operations,
zero E1/E2 outputs, and zero intervention, ablation, patching, or RQ2
operations.

Behavioral eligibility was 2 multihop, 2 order-operations and 5 causal-swap
items. All nine were assigned to development by the prospectively frozen
development-first split, leaving confirmation counts 0/0/0 and pooled readout
confirmation 0. Every floor failed. The exact terminal state is:

**`INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`**.

### Final ACR and protected-byte verification

The terminal evidence commit
`30c0dee7194446040da2a542ea763b1fdbad3d55`, tree
`af63a170f6b6f659b41ab1e503122d10d5343763`, was tested from an exact Git
bundle in ACR.

- Initial focused run `cmbp` passed 17 tests but was non-authoritative because
  the external runner retained only the first of multiple positional
  selectors.
- Corrected focused run `cmbr` passed all 311 selected S2, S3, E0, registry,
  protected-byte, and historical-image controls.
- Full run `cmbq` completed at 3,485 passed / 15 skipped / exactly the two
  authority-disclosed historical `tests/test_parser_v3_seal_job.py` failures.
  Relative to the 3,427 / 15 / 2 baseline, the delta is
  **+58 passed / +0 skipped / +0 failed**.
- Independent integrity run `cmbs` rehashed every frozen S3 and Phase 1.0D
  anchor, both protected-byte manifests, D25-D30 and EV-0014 prefixes, the S2
  seals, E0 lock, complete E0 pack, and terminal receipt. It returned
  `FINAL-INTEGRITY-PASS`, confirmed EV-0016 as the evidence tail, confirmed
  D25-D32, and proved the starting commit remains an ancestor.

The exhaustive operator handoff is
`docs/jlens_s2_s3_e0_final_handoff.md`.

## 2026-08-07 - Study 1 closure index and Study 2 bootstrap

The completed repository through commit
`6409d2c6d665187e4459d94d490a20d7b085e8af`, tree
`bc8b80cb0e66f9426dcdedd52b624c892caa3fc9`, was reorganized logically rather
than physically. No historical evidence path was moved or renamed. A new
`studies/study1/` index records the terminal state, exact protected anchors,
authoritative reading order, asset map, measured question, and the explicit
fact that Study 1 did not answer the original hidden-reasoning question.

The root README and stable `docs/thread_handoff.md` entrypoint now route readers
through the Study 1 closure and the new Study 2 namespace instead of presenting
the superseded July handoff as current. The old handoff bytes remain available
in Git history at the Study 1 terminal commit and are identified by SHA-256.

Study 2 was opened at `OPEN_AWAITING_STAGE_P`. Its charter fixes the research
question, target and two control identities, no-generated-trace four-option
observable, recombinant-answer causal test, stage order, claim ceiling, and
cross-study protection rules. The Stage P prompt is precommitted as the sole
next authority and will be bound to an exact transition commit/tree and prompt
hash in a separate handoff receipt.

This bootstrap performed zero tokenizer constructions, model downloads, weight
loads, forward passes, generations, lens operations, activation operations,
probes, patching, ablations, semantic-review calls, GPU Jobs, Phase 1.0D
operations, or scientific evidence rows. It is a research-boundary and
authority transition, not an empirical run.

### Bootstrap handoff seal

The Study 2 organizational/authority commit is
`db8c100db0c16306a702d348a49a90480f440629`, tree
`032109e20e32f43126ade0d45c0abffa5c2de85f`. A separate fast-forward handoff
commit adds the machine-readable receipt, detailed next-thread handoff, and
copy-ready start prompt. The receipt binds the exact Stage P authority prompt
at SHA-256
`1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37`
and 53,018 bytes.

No Stage P implementation, task generation, methods review, ACR validation, or
scientific operation occurred while sealing the handoff. The new thread must
begin by verifying the exact final head supplied by the operator and the
authority ancestry, then execute Stage P only.
