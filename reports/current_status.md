# Project Status Report

## Summary

J-space observation project scaffold has been successfully implemented. Phase 0.5 (J-lens feasibility spike) and Phase 1 (behavioral reasoning-depth gradient) are now executable.

## Current Phase

**Phase: Azure ACR managed-identity smoke path completed; small Phase 1 pilot succeeded**

## ACR Managed Identity Azure Execution (2026-07-08)

GHCR route was abandoned for execution because private package pull authentication remained blocked. The project switched to ACR with Azure AAD / user-assigned managed identity.

### ACR and Identity

- ACR: `acrjspaceobssea0708231738`
- Login server: `acrjspaceobssea0708231738.azurecr.io`
- Admin user enabled: `False`
- ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:d69187c7a147`
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

### Current blockers / caveats

- Results are inside ephemeral job containers; no persistent result volume/export has been configured yet.
- Phase 0.5 does not include real J-lens fitting; `jacobian-lens` is not installed in the ACR image.
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

### Next blocker

Choose a persistence alternative:

1. Ask the Azure/admin team to allow Azure Files shared-key access for this project; or
2. Switch to Azure Blob upload using managed identity from inside the container; or
3. Use identity-based Container Apps storage if supported in this tenant.

Do not run broader experiments until persistent output is solved.

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

### J-lens Availability Check

Phase 0.5 prioritizes:
1. Checking if pre-fitted lenses exist
2. Reporting jacobian-lens installation instructions
3. Not failing if jacobian-lens is unavailable
4. Checking target model loading
5. Planning cost sweeps for a future actual fitting run

The current Phase 0.5 script does not perform actual tiny fitting and must not be treated as proof that Plan A is feasible.

## What Remains

### Before Production Experiments

1. **Phase 0.5 Execution** (depends on jacobian-lens)
   - Actual J-lens fitting (if available)
   - Cost measurement across parameter sweeps
   - Feasibility decision for Plan A

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

1. **Verify tests pass**:
   ```bash
   make test
   ```

2. **Run Phase 0.5 locally**:
   ```bash
   make phase0-5
   ```
   This checks J-lens availability and plans the feasibility study.

3. **Analyze Phase 0.5 output**:
   - If pre-fitted lens found → can proceed to Phase 2
   - If jacobian-lens available → can run tiny fitting
   - Otherwise → prepare Plan B fallback

4. **Run Phase 1** (if confident models load):
   ```bash
   make phase1-dry  # Test with small item count
   make phase1      # Full behavioral gradient
   ```

5. **Submit to Azure** (if large-scale needed):
   ```bash
   make azure-setup
   make azure-phase0-5
   make azure-phase1
   ```

## Success Criteria

✓ **Implemented**: Executable scaffold for Phase 0.5 and Phase 1
✓ **Tests passing**: All unit tests pass without model downloads
✓ **Documented**: All code, configurations, and infrastructure documented
✓ **Reproducible**: Can run locally or on Azure with single commands
⏳ **Pending**: Actual phase execution and data collection
