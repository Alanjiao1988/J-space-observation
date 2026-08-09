# Decision Log

## 2026-07-08 — Reset repository to final experiment plan

Decision:

- 删除既有仓库内容，用当前最终实验方案重建文档。
- Plan A 仍为主路径：使用真实 Jacobian Lens 做 J-space observation。
- Plan B 只作为保险路径：如果 J-lens 不可行，则降级为 hidden representation probe，不能声称直接 J-space observation。
- 立即执行优先级为：Phase 0.5 J-lens feasibility spike 和 Phase 1 behavioral reasoning-depth gradient。

Key constraints:

- R1-Distill strict no-CoT 主方法为 empty-think prefill。
- RQ3 主证据使用 lens-independent patching/probe。
- Phase 5 ablation 必须使用 DoD，并受 Phase 1 headroom gate 控制。
- Probe 必须跨模板泛化。

Next action:

- 由 GitHub Copilot / Copilot Agent 根据 `docs/copilot_prompt.md` 实现脚手架、Phase 0.5 和 Phase 1。

## 2026-07-08 — Executable scaffold implementation complete

Status: ✓ Implemented

What was built:

1. **Core modules** (src/jspace_observation/):
   - config.py: Model and experiment configuration
   - model_loader.py: HuggingFace model loading with device/dtype management
   - no_cot.py: Strict no-CoT utilities (empty-think prefill for R1-Distill, answer-only for Qwen)
   - prompt_sets.py: Pilot prompt generation with small datasets
   - eval_parsing.py: Numeric, entity, yes/no answer parsing
   - stats.py: Wilson CI and bootstrap confidence intervals
   - run_logging.py: Run directory creation and metadata tracking
   - jlens_utils.py: J-lens availability checking and reporting

2. **Experiment scripts**:
   - phase0_5_jlens_spike.py: J-lens feasibility check
   - phase1_depth_gradient.py: Behavioral depth gradient experiments

3. **Tests** (tests/):
   - test_no_cot.py: No-CoT validation tests
   - test_eval_parsing.py: Answer parsing tests
   - test_stats.py: Statistics utility tests
   - All tests pass without requiring model downloads

4. **Infrastructure** (infra/azure/):
   - Bash scripts for Azure job submission
   - Variables template for configuration
   - README with usage instructions

5. **Build automation**:
   - Makefile for common operations (install, test, run experiments)

Key decisions:

- No-CoT validation checks for think tags and visible reasoning patterns
- Pilot prompts kept small for rapid iteration
- Phase 0.5 prioritizes checking pre-fitted lens availability before attempting fitting
- Phase 1 focuses on behavioral metrics and does not yet attempt mechanistic interpretation
- All runs logged to docs/run_log.md and docs/decision_log.md

What remains:

- Actual Phase 0.5 execution (requires jacobian-lens package)
- Actual Phase 1 execution (generates behavioral metrics)
- Phase 1.5 layer taxonomy characterization
- Phase 2 J-lens workspace readout (if J-lens feasible)
- Phase 3 distill vs base comparison
- Phase 4 activation patching

How to proceed:

1. Test: `make test`
2. Local spike: `make phase0-5` or `make phase1-dry`
3. Full Phase 1: `make phase1`
4. Azure submission: `make azure-setup && make azure-phase0-5`

## 2026-07-08 — GitHub sync decision for executable scaffold

Status: Ready to push

Decision:

- Phase 0.5 and Phase 1 executable scaffold is implemented locally.
- Required implementation files are present under `src/jspace_observation/`, `experiments/`, `tests/`, and `infra/azure/scripts/`.
- Tests passed with the Makefile target's underlying command: `python -m pytest tests/ -v` -> `41 passed, 2 warnings`.
- `make test` was attempted, but `make` is not installed in the current Windows environment.

Next decision:

- Run Phase 0.5 feasibility spike and Phase 1 dry run locally before Azure execution.
- Do not create Azure resources until local dry runs are inspected.

## 2026-07-08 — Correct strict no-CoT prefill ordering and Phase 1 defaults

Decision:

- R1-Distill strict no-CoT prompts must place the base question first, then the already-closed empty think block, then `Answer:`.
- Phase 1 default conditions must include `strict_answer_only`, `visible_cot`, and `r1_style_thinking`.
- The current Phase 0.5 script is explicitly classified as an availability/model-loading check only; it does not attempt actual tiny J-lens fitting.

Next decision:

- Run Phase 0.5 availability check and Phase 1 dry run locally before any Azure execution or Plan A feasibility decision.

## Phase 0.5 Run - 2026-07-08T18:13:38.361771
- Jacobian-lens installed: False
- Pre-fitted lens found: False
- Model loading check success for all models: False
- Actual tiny fitting attempted: no
- Actual tiny fitting success: not attempted
- Results: C:\Users\alanjiao\J-space-observation\results\runs\20260708_181325

## 2026-07-08 — Local validation completed

Status:

- Tests passed: yes (`41 passed, 2 warnings`)
- Phase 0.5 availability/model-loading check completed: yes
- Phase 1 dry run completed: yes
- Azure resources created: none

Phase 0.5 interpretation:

- Pre-fitted lenses were not found locally/configured.
- jacobian-lens is not installed/importable in the local environment.
- Model loading was attempted but failed for both configured models because `accelerate` is required for `device_map`.
- Actual tiny J-lens fitting was not attempted.
- This validation does not prove Plan A feasibility.

Next recommended step:

- Resolve the local `accelerate` dependency, then run a small real Phase 1 pilot with a single model and arithmetic only before any Azure execution or Plan A decision.

## Phase 0.5 Run - 2026-07-08T18:25:22.961267
- Jacobian-lens installed: True
- Pre-fitted lens found: False
- Model loading check success for all models: True
- Actual tiny fitting attempted: no
- Actual tiny fitting success: not attempted
- Results: C:\Users\alanjiao\J-space-observation\results\runs\20260708_182022

## 2026-07-08 — Local environment validation for Phase 0.5

Status:

- Environment fixed: yes.
- Core dependencies installed/importable: yes (`torch`, `transformers`, `accelerate`, `safetensors`, `sentencepiece`).
- External jacobian-lens installed: yes, from `C:\Users\alanjiao\external\jacobian-lens`.
- jacobian-lens importable: yes, via `import jlens`.
- Phase 0.5 availability/model-loading check completed: yes.
- Model loading now succeeds for both configured models on CPU.
- Pre-fitted lenses found locally/configured: no.
- Actual tiny J-lens fitting attempted: no.
- Phase 1 dry run completed: yes, 54 cells.
- Azure resources created: none.

Decision:

- The local dependency blocker is resolved for Phase 0.5 availability/model-loading checks and Phase 1 dry runs.
- Plan A is still not proven because no actual tiny J-lens fitting has been run and no pre-fitted lens was found locally.

Superseded next step:

- The small real Phase 1 pilot should be run via Azure after readiness/quota gates, not locally.

## 2026-07-08 — Adopt Azure-first execution workflow

Decision:

- Use Azure cloud GPU containers as the default execution environment for heavy work.
- The local PC is orchestration-only from now on: tests, dry-runs, documentation, Git, and Azure CLI commands.
- Do not run real model inference, model downloads, real Phase 1 generation, J-lens fitting, patching, or ablation locally.
- Do not make a Plan A feasibility decision from local availability checks.

Azure readiness status:

- Azure CLI login: available.
- Active subscription: `MCAPS-Hybrid-REQ-125620-2025-alanjiao`.
- Microsoft.App provider: `Registered`.
- Microsoft.ContainerRegistry provider: `Registering`.
- containerapp extension: installed (`1.3.0b4`).
- Azure resources created: none.

Blockers before Azure execution:

- Wait for `Microsoft.ContainerRegistry` to become `Registered`.
- Verify Azure Container Apps GPU T4 quota for the target region/workload profile.
- Do not fall back to local inference if quota is unavailable.

Next recommended step:

- Run the Azure readiness script after provider/quota checks:
  - `.\infra\azure\scripts\00_check_prereqs.ps1`
  - or `bash infra/azure/scripts/00_check_prereqs.sh`

## 2026-07-08 — Azure readiness gate stopped on provider registration

Status:

- Microsoft.App provider: `Registered`.
- Microsoft.ContainerRegistry provider: `Registering`.
- Subscription: `MCAPS-Hybrid-REQ-125620-2025-alanjiao`.
- Azure Container Apps T4 GPU quota status: not checked because the Container Registry provider gate failed first.
- Readiness script: not run.
- Azure resources created: none.

Decision:

- Stop until `Microsoft.ContainerRegistry` becomes `Registered`.
- After provider registration is complete, confirm Azure Container Apps T4 GPU quota for `southeastasia` before running `00_check_prereqs.ps1`.
- Do not create Azure resources and do not fall back to local model inference.

## 2026-07-08 — Adopt GHCR fallback due to blocked Container Registry provider

Status:

- `az provider register --namespace Microsoft.ContainerRegistry --wait` returned exit code `0`, but the state remained `Registering` afterward and on re-check.
- Microsoft.ContainerRegistry provider: `Registering` (still blocked after several hours and an explicit retry).
- Microsoft.App provider: `Registered`.
- Subscription: `MCAPS-Hybrid-REQ-125620-2025-alanjiao`.
- Azure resources created: none.

Decision:

- Treat the ACR path as blocked. Do not wait indefinitely on `Microsoft.ContainerRegistry`.
- Adopt GHCR (GitHub Container Registry) as the fallback image registry for Azure Container Apps.
- Build/push images via a GitHub Actions workflow (stored at `infra/ci/build-ghcr.yml`) so the local PC does not build large images.
- Deploy Azure Container Apps Jobs from the GHCR image using `infra/azure/scripts/05_run_job_ghcr.sh`, with the GHCR PAT provided only via environment variable / Azure secret.
- Constraint: the CLI Git credential lacks the `workflow` OAuth scope, so `.github/workflows/` files cannot be pushed. The workflow file is stored at `infra/ci/build-ghcr.yml` and must be copied into `.github/workflows/build-ghcr.yml` via the GitHub web UI or a `workflow`-scoped token before it runs.

Still required before any GPU job:

- `Microsoft.App` must remain `Registered` (currently satisfied).
- Azure Container Apps T4 GPU quota for `southeastasia` must be confirmed.
- If T4 quota is unavailable, stop and do not fall back to local model inference.

Next recommended step:

- Run the GHCR build workflow manually in GitHub Actions to produce `ghcr.io/alanjiao1988/j-space-observation:<git-sha>`.
- Separately, confirm Azure Container Apps T4 GPU quota for `southeastasia`.
- Do not create Azure resources until both the image and quota are ready.

## 2026-07-08 — GHCR primary path; ACR now Registered again

Status:

- Microsoft.ContainerRegistry provider: `Registered` (state flipped from `Registering` to `Registered` on read-only re-check).
- Microsoft.App provider: `Registered`.
- GHCR workflow template (`infra/ci/build-ghcr.yml`) validated: workflow_dispatch, builds Dockerfile, pushes to GHCR, tags git SHA + optional latest, no model download/cache, only `contents: read` + `packages: write`.
- GHCR Azure job script (`infra/azure/scripts/05_run_job_ghcr.sh`) validated: parameterized, no hardcoded token, `GHCR_PAT` via env/Azure secret, GHCR image path, `JOB_COMMAND` override supported.
- Local checks: `41 passed, 2 warnings`; Phase 1 dry-run 54 cells.
- Azure resources created: none.

Decision:

- Keep GHCR as the primary container registry path per Alan's instruction, even though ACR is now `Registered`. ACR scripts remain available as a secondary option.
- Manual installation of `.github/workflows/build-ghcr.yml` via the GitHub web UI remains required (CLI credential lacks `workflow` scope).
- The next Azure gate is Container Apps T4 GPU quota confirmation in `southeastasia`; documented portal + support-request steps in the runbook.
- Do not create Azure resources and do not fall back to local inference.

Next recommended step:

- Alan installs the workflow via GitHub web UI and runs it to build the GHCR image.
- Confirm T4 GPU quota for `southeastasia` (portal or support request).
- Only then deploy the Container Apps Job via `05_run_job_ghcr.sh`.

## 2026-07-08 — Confirm GHCR primary / ACR secondary (final)

Status:

- Microsoft.ContainerRegistry: `Registered`. Microsoft.App: `Registered`.
- Azure resources created: none.

Decision (locked):

- GHCR is the **primary** container registry path.
- ACR is a **secondary fallback** only, used if GHCR pull/build fails.
- Rationale: git-SHA image provenance, GitHub-hosted builds (local PC does not build large images), and decoupling from ACR provider registration timing.
- Added to `docs/azure_runbook.md`: registry strategy section and a gated "Planned Azure command sequence" (quota -> resource group -> Container Apps env + GPU profile -> GHCR image smoke test -> Phase 0.5 --skip-fit -> Phase 1 --dry-run -> small Phase 1 pilot).

Next required gate:

- Confirm Container Apps T4 GPU quota in `southeastasia`. No Azure resources created until quota is confirmed and the GHCR image exists.

## 2026-07-08 — GHCR image published; quota remains next gate

Status:

- Workflow file installed: `.github/workflows/build-ghcr.yml`.
- Workflow install commit: `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Workflow run id: `28947916765`.
- Workflow conclusion: `success`.
- GHCR image published:
  - `ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66`
  - `ghcr.io/alanjiao1988/j-space-observation:latest`
- Providers:
  - Microsoft.App: `Registered`
  - Microsoft.ContainerRegistry: `Registered`
  - Microsoft.Quota: `NotRegistered`
- Azure resources created: none.
- T4 workload profile type offered in `southeastasia`: yes (`Consumption-GPU-NC8as-T4`).
- Subscription T4 quota: not confirmed.

Decision:

- GHCR image exists, satisfying the image prerequisite for future Azure Container Apps Jobs.
- Do not create any Azure GPU job until the subscription's Container Apps T4 quota in `southeastasia` is confirmed.
- Do not register `Microsoft.Quota` without Alan approval.

## 2026-07-08 — Microsoft.Quota registered; T4 quota still unknown via CLI

Status:

- Latest repo commit before this update: `c10afdd1d0817b0cf3c773b54a91d81d65f2ed05`.
- GHCR image commit: `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Diff from image commit to latest commit: documentation-only; no GHCR rebuild required.
- Microsoft.App: `Registered`.
- Microsoft.ContainerRegistry: `Registered`.
- Microsoft.Quota: `Registered`.
- Azure resources created: none.

Quota query result:

- `az quota list` and `az quota usage list` for `Microsoft.App` in `southeastasia` succeeded.
- Returned entries include `ManagedEnvironmentCount` (limit 50, usage 0) and `SessionPools` (limit 50, usage 0).
- Returned entries do not include `Consumption-GPU-NC8as-T4`, T4, NC8as, or Managed Environment Consumption T4 quota.
- `Consumption-GPU-NC8as-T4` remains regionally offered in `southeastasia`, but the subscription's actual T4 GPU quota remains unknown via CLI.

Decision:

- Do not create Azure GPU resources yet.
- Next gate remains T4 quota confirmation via Azure Portal Usage + quotas or Azure support request for Container Apps Managed Environment Consumption T4 GPUs in `southeastasia`.

## 2026-07-08 — Azure GHCR smoke path created resources, stopped on GHCR auth

Status:

- Alan approved creating minimal Azure resources to validate the GHCR/Container Apps path instead of continuing to block on invisible quota.
- Resource group created: `rg-jspace-observation-sea`.
- Log Analytics workspace created: `law-jspace-observation-sea`.
- Container Apps environment created: `cae-jspace-observation-sea`.
- T4 workload profile created: `gpu-t4` (`Consumption-GPU-NC8as-T4`).
- No Container Apps job was successfully created.
- Azure resources created: yes, limited to resource group, Log Analytics workspace, Container Apps environment, and workload profile.

Findings:

- T4 workload profile creation succeeded, so the previous quota ambiguity no longer blocks environment/profile creation.
- The first smoke job was blocked by GHCR registry authentication, not quota.
- Error code: `InvalidParameterValueInContainerTemplate`.
- Error message includes: `UNAUTHORIZED: authentication required`.

Decision:

- Stop before Phase 0.5, Phase 1 dry-run, or small pilot.
- Historical next gate at that point was GHCR pull authentication; this has since been superseded by the ACR managed-identity route.
- Do not commit or print GHCR token values.
- `infra/azure/scripts/05_run_job_ghcr.sh` was updated to use the actual `*-sea` resource names and to avoid the `--enable-dedicated-gpu` / T4 min-max parameters that failed during live Azure CLI execution.

## 2026-07-08 — GHCR auth retry confirms gh token is insufficient

Status:

- `GHCR_PAT`: not set.
- `gh auth token`: available and used as an Azure registry secret retry; token value was not printed or committed.
- ARM schema for Container Apps Job was corrected:
  - `workloadProfileName` belongs at `properties.workloadProfileName`.
- Smoke job still failed before creation/execution.

Error:

- Error code: `InvalidParameterValueInContainerTemplate`.
- Exact message includes: `DENIED: requested access to the resource is denied`.
- Classification: GHCR package pull authentication. The current `gh auth token` is insufficient for Azure to pull the private GHCR image.

Decision:

- Stop before any Phase 0.5, Phase 1 dry-run, or small pilot.
- Next step must be either making the GHCR package public or providing a proper classic PAT with `read:packages` via secure environment/Azure secret path.
- Do not send token values in chat; do not commit/log them.

## 2026-07-08 — Stop GHCR smoke retry before Azure job due missing package-read token

Status:

- Existing Azure resources remain available:
  - `rg-jspace-observation-sea`
  - `law-jspace-observation-sea`
  - `cae-jspace-observation-sea`
  - `gpu-t4`
- `GHCR_PAT`: not set.
- `gh auth token`: available, but package read preflight returns `403` / `read:packages` required.
- No smoke job was recreated in this step.
- No new Azure resources were created in this step.

Decision:

- Do not retry Azure Container Apps Job creation with the current token.
- Required next step remains secure GHCR package-read authentication:
  - make GHCR package public, or
  - provide a classic PAT with `read:packages` through environment/Azure secret path only.
- `infra/azure/scripts/05_run_job_ghcr.sh` was hardened to support env aliases and avoid passing token values as command-line arguments to helper Python.

## 2026-07-08 — GHCR_PAT set in shell but not visible to agent

Status:

- Alan reported setting `GHCR_USERNAME` and `GHCR_PAT` in PowerShell.
- Copilot checked Process/User/Machine environment scopes.
- `GHCR_USERNAME`: not visible.
- `GHCR_PAT`: not visible.
- No token value was printed or committed.
- No Azure job retry was attempted.
- Azure resources created in this step: none.

Decision:

- Stop until the PAT is exposed through a scope readable by the agent, preferably Windows User environment.
- Recommended user-scope setup:
  - `[Environment]::SetEnvironmentVariable("GHCR_USERNAME", "Alanjiao1988", "User")`
  - `[Environment]::SetEnvironmentVariable("GHCR_PAT", "<classic PAT with read:packages>", "User")`
- Do not paste token values into chat.

## 2026-07-08 — GHCR_PAT still not visible after reported restart

Status:

- Alan reported setting `GHCR_USERNAME` / `GHCR_PAT` in Windows User environment and restarting the local tools.
- Copilot checked Process/User/Machine environment scopes again.
- `GHCR_USERNAME`: not visible.
- `GHCR_PAT`: not visible.
- No package-read preflight was run.
- No Azure job retry was attempted.
- Existing Azure resources unchanged.

Decision:

- Stop until the agent can read a valid package-read token.
- Do not fall back to the current `gh auth token` because it previously failed with `read:packages` required.
- Next option: make GHCR package public, or provide a secure token path that is visible to the agent process.

## 2026-07-08 — Switch to ACR managed identity and complete Azure pilot chain

Decision:

- Stop pursuing GHCR authentication as the active path.
- Use ACR with Azure AAD / user-assigned managed identity as the active registry route.
- ACR admin user/password remains disabled and unused.

Status:

- ACR created: `acrjspaceobssea0708231738`
- ACR image built: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:d69187c7a147`
- Managed identity created: `id-jspace-aca-acrpull-sea`
- AcrPull assigned: yes
- Container Apps jobs created:
  - `job-jspace-acr-smoke`
  - `job-jspace-phase05-acr`
  - `job-jspace-phase1-dryrun-acr`
  - `job-jspace-phase1-pilot-acr`

Execution results:

- Smoke test succeeded (`job-jspace-acr-smoke-9b9wb4z`), `41 passed, 2 warnings`.
- Phase 0.5 `--skip-fit` succeeded (`job-jspace-phase05-acr-i110lnu`); both models loaded on Azure T4; no actual fitting.
- Phase 1 dry-run succeeded (`job-jspace-phase1-dryrun-acr-v0j1bkd`); 54 cells; no real generation.
- Small Phase 1 pilot succeeded (`job-jspace-phase1-pilot-acr-lhuvwbf`) with single distill model / arithmetic / depths 1,2,3 / three conditions / one item per cell.

Scientific interpretation:

- The small pilot is behavioral-only and does not count as J-space evidence.
- Plan A remains unproven until real J-lens fitting/loading and validation are implemented and pass.

Next decision:

- Configure persistent results export/storage before broader Phase 1 runs, or explicitly accept log-only summaries for the next small run.

## 2026-07-09 — Azure Files persistence blocked by shared-key policy

Status:

- Storage account `stjspaceobssea07090835` created; `allowSharedKeyAccess=False`.
- Storage account `stjspacefiles0709085305` created with explicit `--allow-shared-key-access true`, but `allowSharedKeyAccess` still remained `False`.
- Azure Files data-plane operations using account key failed with `KeyBasedAuthenticationNotPermitted`.
- Environment storage `jspace-results-storage` was registered but proved unusable; storage smoke job hung.
- Stuck storage smoke execution `job-jspace-storage-smoke-acr-1s1g5d8` was stopped.
- `job-jspace-storage-smoke-acr` was deleted.
- `jspace-results-storage` was removed from the Container Apps environment.

Decision:

- Azure Files key-based mount is blocked by organization/subscription policy.
- Do not rerun storage-mount jobs until a working persistence backend is selected.
- Do not broaden Phase 1 until result persistence is solved.

Next options:

- Request admin exception for Azure Files shared-key access; or
- Switch to Azure Blob upload with managed identity; or
- Investigate identity-based Container Apps storage support for this tenant.

## 2026-07-09 — Azure Blob persistence works; validation bug is next blocker

Status:

- Azure Blob upload with managed identity succeeded.
- Blob storage account: `stjspacefiles0709085305`.
- Blob container: `jspace-results`.
- Managed identity `id-jspace-aca-acrpull-sea` has `Storage Blob Data Contributor`.
- Blob smoke succeeded:
  - job: `job-jspace-blob-smoke-acr`
  - execution: `job-jspace-blob-smoke-acr-o7kl7s2`
  - verified blob: `smoke/20260709T013310Z/smoke.txt`
- Persistent Phase 1 pilot succeeded:
  - job: `job-jspace-phase1-pilot-blob-acr`
  - execution: `job-jspace-phase1-pilot-blob-acr-9voxpdm`
  - blob prefix: `phase1-pilot/20260709T014336Z`
  - files: eval JSONL, generation JSONL, metrics CSV, summary MD

Pilot review:

- 9 cells completed.
- Output artifacts are persisted to Blob.
- Current no-CoT validator overestimates strict answer-only validity: visible reasoning in strict answer-only outputs was not flagged.
- Numeric parser can be misled by truncated reasoning and last-number selection.

Decision:

- Do not expand Phase 1 yet.
- Fix no-CoT validation before broader runs.
- This pilot remains infrastructure + behavioral sanity only, not J-space evidence.

## 2026-07-09 — no-CoT validator hardened; strict answer-only leakage exposed

Status:

- Local tests passed: `54 passed, 2 warnings`.
- New ACR image built: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:937288cfb8ef`.
- Validator rerun job succeeded: `job-jspace-p1-validator-xkqro3f`.
- Blob output prefix: `phase1-pilot-validator/20260709T022001Z`.

Findings:

- strict_answer_only no-CoT validity is now `0.0000` for depths 1/2/3 in the tiny arithmetic pilot.
- visible reasoning marker rate is `1.0000` for strict_answer_only depths 1/2/3.
- parse ambiguity is now explicit (`parse_ambiguous_rate = 1.0000` for all cells).
- Correctness is reported separately from no-CoT compliance.

Decision:

- The validation false negative is fixed.
- The tiny pilot shows current strict-answer-only prompt/decoding still leaks visible reasoning.
- Do not broaden Phase 1 yet.
- Next step should tighten strict-answer-only generation/prompting and parser policy, then rerun the same small persistent pilot.
- No J-space or hidden reasoning conclusion may be drawn from this behavioral sanity run.

## 2026-07-09 — strict answer-only prefill variant tested

Status:

- Added `strict_answer_only_prefill_answer`.
- Rebuilt ACR images:
  - `b91bc335caf1` in build `cm5`
  - `9b5895db173f` in build `cm6`
- Reran minimal persistent pilot with four conditions:
  - `strict_answer_only`
  - `strict_answer_only_prefill_answer`
  - `visible_cot`
  - `r1_style_thinking`
- Final execution: `job-jspace-p1-strictfix2-1sjj2n5`.
- Blob prefix: `phase1-pilot-strictfix2/20260709T025356Z`.

Findings:

- Existing `strict_answer_only` remains no-CoT invalid for all depths.
- New `strict_answer_only_prefill_answer` suppresses visible reasoning on depth 1 but returns incomplete/wrong answer text.
- New `strict_answer_only_prefill_answer` still leaks meta-reasoning on depths 2/3 (`Alright`, `Wait`) and is no-CoT invalid there.

Decision:

- The direct `Answer:` prefill variant is not sufficient to establish a reliable strict answer-only condition.
- Do not expand Phase 1.
- Next step should test stop-sequence / post-processing approaches that preserve raw output and separately report raw vs postprocessed no-CoT validity.

## 2026-07-09 — raw-vs-postprocessed answer-only condition tested

Status:

- Added `strict_answer_only_postprocessed`.
- ACR image built: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:9342ef130d46`.
- Build run: `cm8`.
- Azure job succeeded: `job-jspace-p1-postprocess-gor0o1r`.
- Blob prefix: `phase1-pilot-postprocess/20260709T044224Z`.

Findings:

- Raw no-CoT validity for `strict_answer_only_postprocessed`: `0.0000` for depths 1/2/3.
- Postprocessed no-CoT validity: `1.0000` for depths 1/2/3.
- Postprocessing recovered a correct answer only for depth 1.
- Depth 2 had no answer-like span after truncation.
- Depth 3 produced a clean but wrong postprocessed answer.

Decision:

- Postprocessing is an answer-recovery analysis only.
- Postprocessed validity must not be interpreted as raw no-CoT compliance.
- Do not expand Phase 1 yet.
- Next decision should choose between stop-sequence generation controls or treating postprocessing as a separate analysis track.

## 2026-07-10 — private Blob path and stop-controlled condition verified

Infrastructure decision:

- Keep Storage public network access disabled.
- Do not use storage keys, SAS, or Azure Files.
- Use VNet-integrated Container Apps, Blob private endpoint, private DNS, and managed identity.
- Active environment: `cae-jspace-observation-sea-vnet2`.
- The first environment, `cae-jspace-observation-sea-vnet`, was created before `Microsoft.Network/AllowBringYourOwnPublicIpAddress` was registered and cannot start containers. It remains present but inactive.
- Blob network smoke succeeded as `job-jspace-blob-net-smoke-v2-l02nljz`.

Experiment status:

- Condition: `strict_answer_only_stopped`.
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:c29852ab97b5`.
- Pilot execution: `job-jspace-p1-stopcontrol-vnet-b55p4c6`.
- Blob prefix: `phase1-pilot-stopcontrol-vnet/20260710T072107Z`.
- Fifteen cells completed and four files were uploaded.

Findings:

- Raw no-CoT valid rate: `1.0000` for depths 1/2/3.
- Stopped no-CoT valid rate: `1.0000` for depths 1/2/3.
- Stop-triggered rate: `1.0000` for depths 1/2/3.
- Stop string: `\n\n` for all three stopped records.
- Stopped accuracy: depth 1 `1.0000`, depth 2 `0.0000`, depth 3 `0.0000`.
- Depth 2 stopped at a non-answer placeholder.
- Depth 3 stopped at a parseable but wrong boxed answer.

Scientific decision:

- Stop control is a generation intervention, not evidence of spontaneous no-CoT reasoning.
- Keep raw strict, stopped, and postprocessed conditions separate.
- Do not broaden Phase 1 yet because stopped answer quality fails at depths 2/3.
- No hidden-reasoning or J-space claim is supported.

## 2026-07-10 — separate Phase 1 answer-control conditions into three branches

Decision:

- Define `raw_strict` as raw strict no-CoT feasibility.
- Define `stopped_intervention` as stop-controlled generation intervention.
- Define `postprocessed_utility` as postprocessed answer-recovery utility.
- Treat the three branches as non-interchangeable in records, metrics, summaries, and interpretation.

Reason:

- Prompt-only strict no-CoT was unreliable.
- Stop controls can suppress visible reasoning but are generation-time interventions.
- Postprocessing can recover answer spans but does not establish raw no-CoT compliance.

Consequence:

- Future Phase 1 reports must preserve raw, stopped, and postprocessed outputs, validity, and correctness separately.
- Non-applicable branch metrics must be `NA`.
- Stopped validity is not spontaneous no-CoT, and postprocessed validity is not raw no-CoT.
- No branch by itself supports hidden-reasoning or J-space claims.
- Scaling remains paused until branch-specific success criteria are reviewed and approved.

## 2026-07-10 — preregister branch-specific Phase 1 success criteria

Decision:

- Preregister separate success criteria for `raw_strict`, `stopped_intervention`, and `postprocessed_utility` before scaling Phase 1.
- Classify every model x task family x depth x condition row independently.
- Treat missing required metrics as failed criteria and preserve `NA` for non-applicable metrics.

Reason:

- Prior pilots showed that raw strict generation, stop intervention, and postprocessed answer recovery behave differently.
- A single answer-only or accuracy metric would make these branches scientifically non-interpretable.
- Thresholds must be fixed before any new limited-scale run rather than selected after observing results.

Consequence:

- Future Phase 1 summaries must include independent branch classifications and interpretation warnings.
- A passing classification is behavioral and operational only.
- It does not establish hidden reasoning, internal workspace behavior, or J-space evidence.
- No new run is authorized by this decision; the next run requires explicit approval and must remain limited scale.

## 2026-07-10 — run fixed-scope Phase 1 criteria validation

Decision:

- Accept one Azure validation run using the exact approved 15-cell scope.
- Preserve the preregistered criteria and report the resulting classifications without post-hoc threshold changes.
- Do not authorize a rerun, broader sweep, new model, new task family, new depth, or higher items-per-cell count.

Evidence:

- Source commit/image tag: `f94e889ef6089aab8f651a2d14c42341440625a3` / `f94e889ef608`.
- ACR build: `cma`; digest `sha256:f27cc0e4cea0ae9569dbb384598fb391f3b923022ce9257f8301684c9dc23806`.
- Active environment: `cae-jspace-observation-sea-vnet2`.
- Job: `job-jspace-p1-criteria-val`.
- Execution: `job-jspace-p1-criteria-val-6s8p15p`; status `Succeeded`.
- Blob prefix: `phase1-pilot-criteria-validation/20260710T135655Z`.
- Generation records: `15`; exported files: `4`.

Observed classifications by depth 1/2/3:

- `raw_strict`: `surface_answer_only_but_task_failed` / `raw_strict_not_established` / `raw_strict_not_established`.
- `stopped_intervention`: `stopped_intervention_usable` / `stopped_intervention_not_useful` / `stopped_surface_compliant_but_task_failed`.
- `postprocessed_utility`: `postprocessed_answer_recovery_usable` / `postprocessed_surface_clean_but_warning_high` / `postprocessed_answer_recovery_usable`.

Consequence:

- The reporting code generated the expected classification table, passed/failed criteria, stop-string distribution, and interpretation warnings.
- Depth 3 postprocessing is classified usable by the preregistered non-degradation rule even though raw and postprocessed accuracy are both zero.
- Depth 3 raw accuracy satisfies the relative rule because matching visible-CoT accuracy is zero, but raw strict still fails its surface criteria.
- These are prospective criteria-design questions, not grounds to rewrite this run after seeing results.
- No result supports hidden reasoning, internal workspace, or J-space claims.

## 2026-07-10 — harden Phase 1 branch success gates

Decision:

- Add absolute task-accuracy floors, visible-CoT baseline validity guards, and minimum sample-size guards to Phase 1 branch classifications.
- Apply the revision prospectively. Do not rewrite the completed criteria-validation Blob artifacts or claim that they were generated by the hardened code.

Reason:

- The criteria-validation pilot showed that non-degradation alone permitted `0 >= 0` to be classified as answer-recovery success.
- Relative accuracy comparisons are meaningless when the visible-CoT baseline is zero, invalid, or undersampled.
- One observation per branch/depth validates report plumbing but cannot support a formal branch-success label.

Consequence:

- Formal branch success labels require `n >= 3`; otherwise an otherwise-passing result uses its branch-specific `pilot_only` label.
- Clear failures retain their failure labels when `n < 3`.
- Postprocessed utility requires both `accuracy_postprocessed >= accuracy_raw` and `accuracy_postprocessed >= 0.50`.
- Raw and stopped relative gates require a matching visible-CoT baseline with `n >= 3`, parse-valid rate `>= 0.80`, and nonzero accuracy. Invalid baselines make the relative gate `NA`, never passed.
- Postprocessed visible-CoT-relative performance is report-only and not a hard utility gate.
- The depth-3 `0 >= 0` case now classifies as `postprocessed_surface_clean_but_task_failed`.
- No Azure job, model inference, model download, ACR rebuild, or experiment-scale change was performed.
- These classifications remain behavioral and operational only; they do not establish hidden reasoning, internal workspace behavior, or J-space evidence.

## 2026-07-10 — run bounded Phase 1 n=3 validation

Decision:

- Run one bounded validation using the hardened branch gates.
- Keep one model, arithmetic only, depths 1/2/3, the five registered conditions, and exactly three items per condition/depth.
- After the parallel pre-run audits found arithmetic prompt capacity `3/3/2`, approve one unique third depth-3 arithmetic item so the registered `n=3` scope is executable.
- Do not change any threshold, model, task family, depth, or condition after observing results.

Reason:

- The previous `n=1` run validated the reporting pipeline but could not emit formal branch-success labels.
- The new run was needed to exercise the registered minimum-sample guard, absolute accuracy floor, and visible-CoT baseline guard on real outputs.
- Duplicating a prompt or silently accepting 40 observations would not satisfy the approved 45-observation design.

Evidence:

- Source fix commit: `359643b7b5eb8f95c13cca2e60fa753df8701282`.
- Tests: `111 passed, 2 warnings`.
- Dry-run: `15` configuration cells, `3` items per cell, `45` planned observations.
- ACR build: `cmb`; image `359643b7b5eb`; digest `sha256:004ec8bff66fbc8a23b122660aeb58914b2ee3cedfc5246429046eef252c9069`.
- Execution: `job-jspace-p1-n3-gates-02ilmgm`; first attempt `Succeeded`.
- Blob prefix: `phase1-limited-n3-gates/20260710T152820Z`; four artifacts uploaded.
- Runtime evidence: `45` generation records, `45` eval records, and `15` metric rows with `n=3`.

Consequence:

- Raw strict is not established at any depth.
- Stopped intervention is usable at depth 1 only; it remains intervention-controlled.
- Postprocessed answer recovery is usable at depth 1 only; it is not raw no-CoT.
- The depth-3 visible-CoT baseline is invalid because accuracy is zero; relative gates are `NA`.
- The depth-3 postprocessed `0 >= 0` non-degradation result correctly fails the absolute floor and is not usable.
- `n=3` meets only the registered minimum and does not establish statistical stability.
- Counts and aggregate rows passed audit. Record-level duplicate IDs, exact item membership, and field equality remain inconclusive because private Blob data cannot be read from the local machine without changing network policy; no key, SAS, or public-network workaround was used.
- No result establishes hidden reasoning, internal workspace behavior, or J-space evidence.

## 2026-07-11 — complete read-only Phase 1 record-level artifact audit

Decision:

- Accept one model-free, CPU-only audit of the immutable bounded n=3 source
  prefix through the existing VNet, private endpoint, and managed identity.
- Keep source and audit-output prefixes disjoint and use `overwrite=False` for
  audit reports.
- Treat deterministic artifact checks separately from LLM semantic review.
- Do not alter stored parser fields, correctness, metrics, classifications,
  thresholds, prompts, or historical summaries.

Reason:

- Local access could not inspect the private source artifacts at record level.
- Counts and aggregate classifications were known, but duplicate keys, exact
  membership, common-field equality, transformation derivation, parser replay,
  and all 18 ambiguous records still required direct review.
- A private-path audit resolves integrity questions without running the model or
  weakening Storage network controls.

Evidence:

- Audit implementation commit:
  `9537ed8e0b5da95b68714b73fa11236b48ee046a`.
- Tests: `139 passed, 2 warnings`.
- ACR build `cmc`; digest
  `sha256:90adfc1b6be6fbb7a17a878bed7970ffd71c62b72263a36b41110ba6f19b169b`.
- CPU-only execution `job-jspace-p1-record-audit-d9q5uy8` succeeded on the
  `Consumption` profile.
- Eight files were uploaded under
  `phase1-audits/n3-gates-20260710T152820Z/20260711T010339Z`.
- Source Blob properties remained unchanged.
- Deterministic status: `completed_clean`.
- Pairing: 45 unique generation keys, 45 unique eval keys, zero duplicates or
  one-sided keys.
- Membership: all 15 cells contain exactly three registered unique items.
- Common-field, transformation, parser, metric, and branch mismatches: zero.
- All 15 metric rows and nine branch classifications match; depth-3
  postprocessed `0 >= 0` remains task-failed.
- Two independent reviewers assessed all 18 stored ambiguous records. Category
  agreement was 17/18; an arbiter resolved all 14 records with any field-level
  disagreement.

Consequence:

- The prior record-integrity limitation is resolved as `PASS`, evidence-bounded.
- Final LLM audit opinion is 17 parser overflags and one true
  multiple-candidate ambiguity, with zero unresolved after arbitration.
- The semantic review does not rewrite stored fields and is not human ground
  truth.
- Records 2 and 3 demonstrate a last-number answer-extraction limitation while
  remaining mechanically consistent with the stored evaluator.
- Reviewing only flagged records cannot exclude parser underflags among the
  other 27 records.
- No higher-n replication is authorized. The next decision must preregister
  whether to audit all 45 outputs for underflags or revise parser methodology
  prospectively.
- This audit generated no behavioral observation and supports no
  hidden-reasoning, internal-workspace, or J-space claim.

## 2026-07-13 — preregister all-45 semantic parser audit protocol v1

Decision:

- Freeze `docs/phase1_semantic_review_protocol.md` as protocol v1 before any
  all-45 packet review.
- Select the all-45 parser-underflag audit path for the 45 already-stored
  arithmetic records from
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- Use two independent blinded stages followed by prospectively triggered
  arbitration by `gpt-5.6-sol` with reasoning effort `max`.
- Make no prospective parser change in this round. Stored parser behavior,
  thresholds, branch logic, historical metrics, classifications, summaries,
  and source artifacts remain unchanged.
- Admit production releases only from hard-coded-hash-verified source bytes
  with before/after Blob evidence; synthetic fixtures are permanently
  release-ineligible.
- Require clean-Git build preparation and a baked immutable provenance
  attestation before any project or Azure import.
- Reserve every new release prefix atomically and validate exact membership.
- Treat reviewer-derived recomputations only as audit-only semantic alternative
  estimates: post hoc, noncanonical sensitivity estimates.

Material-impact rule:

- A material evaluator error is a stored-versus-semantic disagreement that
  could change correctness, condition-depth accuracy, a branch absolute or
  relative gate, visible-CoT baseline validity, or branch classification.
- Last-number risk, observed extraction error, and material correctness error
  are reported separately.

Scientific boundary:

- Reviewing stored outputs generates no new behavioral observations and leaves
  every experimental cell at `n=3`.
- Reviewer judgments are audit opinion, not human ground truth.
- No hidden-reasoning, internal-workspace, invisible-CoT, genuine no-CoT, or
  J-space inference is authorized.
- This entry preregisters a procedure and claims no semantic-audit result.

## 2026-07-15 — select Path C after the all-45 semantic audit

Decision:

- Complete the selected all-45 parser-underflag audit without changing the
  parser, thresholds, source records, historical metrics, or historical
  classifications.
- Select preregistered **Path C**.
- Pause higher-n replication.
- Require a locked evaluator validation set and prospective parser-v2
  protocol before any new model run.
- Future work must dual-report the legacy parser and prospective parser v2;
  it must not rewrite the bounded n=3 history.

Evidence:

- Two independent blinded `gpt-5.6-sol/max` reviewers completed all 45 records
  in both stages.
- A distinct arbiter resolved four triggered disagreements; unresolved count
  is zero.
- Final semantic audit opinion: 18 parser overflags, zero underflags, zero
  true multiple-candidate ambiguities, 14 observed extraction errors, two
  material correctness errors, and 19 material evaluator issues.
- Both material correctness errors are `visible_cot`, depth 1. The audit-only
  semantic alternative accuracy is `1.0000` versus stored/recomputed
  `0.3333`.
- The audit-only depth-2 visible-CoT parse-valid rate is `0.6667`; baseline
  validity becomes false and relative gates become `NA`.
- Four baseline/gate fields differ, but none of the nine final branch
  classification labels changes.

Consequence:

- Official stored metrics and classifications remain authoritative and
  unchanged.
- Audit-only alternatives are post hoc, noncanonical sensitivity estimates,
  not corrected or replacement results.
- Parser v2 was not implemented in this audit.
- Higher-n is not authorized until evaluator validation is preregistered and
  completed.
- The review adds no behavioral observations, leaves each cell at `n=3`, and
  supports no hidden-reasoning, internal-workspace, invisible-CoT, genuine
  no-CoT, or J-space claim.

## 2026-07-15 — freeze the Phase 1.2A parser-v2 validation protocol

Decision:

- Freeze the parser-v2 extraction contract, 12-stratum evaluator-set design,
  machine-readable acceptance gates, two-stage independent labeling workflow,
  private Blob layout, and one-shot retirement policy before eligible case
  construction.
- Use 60 open development cases and 120 private locked cases.
- Keep locked inputs, labels, mappings, salts, and reviewer rows outside normal
  Git paths.

Registered provenance:

```text
final protocol commit: cc93ffe603ab8338ed860586a52b1911af4b3277
protocol bundle SHA-256: 5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666
acceptance-gate SHA-256: a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988
```

Reason:

- The all-45 audit showed that historical parser behavior was not adequate for
  a higher-n decision.
- A prospective, reference-isolated, typed-decision evaluator was required
  before parser changes or new target-model observations.
- Acceptance thresholds must be fixed before construction and before any
  locked result.

Consequence:

- Candidate material created before final amendments was discarded.
- Parser v2 may later be developed only against the open set.
- The future locked evaluation is formal and one-shot. PASS and FAIL both
  retire the holdout; a changed parser requires a new independent holdout.

## 2026-07-16 — lock the Phase 1.2A evaluator validation set

Decision:

- Accept the independently constructed and labeled 60/120 evaluator set as
  `SEALED`.
- Persist the exact 26 registered artifacts under:
  `phase1-evaluator-validation/parser-v2-v1/20260716T024856Z`.
- Stop before parser-v2 implementation, locked evaluation, or higher-n.

Evidence:

- All S01-S12 quotas are exact: development 5 and locked 10 per stratum.
- Locked support is 80 present, 10 ambiguous, and 30 no answer.
- Stage-1 reviewers completed 120/120 each; 57 disagreements were arbitrated.
- Stage-2 reviewers completed 120/120 each with zero disagreements.
- Final labels are 120/120 with zero unresolved and seven valid review seals.
- Exact, normalized, cross-set template, and historical hard overlaps are zero;
  all 37 near-duplicate findings are dispositioned.
- All five independent `gpt-5.6-sol/max` post-sealing reviews passed.
- Final model-free validation is `460 passed, 2 warnings`.

Private release bindings:

```text
final labels: 44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af
locked-label manifest: aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6
overall manifest: f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260
validation report: 5b3daf44553a7c99d57c8d5a117ef82de113c4b5cde74ef13dd218c11c56b641
```

Azure consequence:

- The sole persistence execution
  `job-jspace-parser-v2-set-ib7uc0e` succeeded on Consumption with 2 CPU /
  4 GiB and no GPU.
- Uploads used managed identity, the private Blob endpoint,
  `overwrite=false`, reservation-first/manifest-last ordering, exact membership,
  and per-object re-download verification.
- The job is idle on the immutable base with `/bin/true`, zero secrets, and
  zero secret references. The temporary transport image was deleted.
- Do not rerun the sealing execution or write to the sealed parent.

Scientific consequence:

- LLM labels are operational consensus references, not human ground truth.
- Procedural blindness is hash-audited, not security-enforced.
- No parser-v2 PASS/FAIL exists because locked evaluation was not run.
- No target-model download/load/inference, higher-n run, new behavioral
  evidence, hidden-reasoning result, internal-workspace result, or J-space
  result was produced.

## 2026-07-18 — accept bounded real J-lens technical feasibility as GREEN

Decision:

- Accept Phase 0.5A as **GREEN / COMPLETE for bounded technical feasibility
  only** on one Tesla T4.
- Retain the primary F4 checkpoint failure as immutable history and accept the
  single separately reviewed operational retry.
- Treat the retry as a serialization-only repair: restore and reuse F2/F3,
  save the exact fitted lens as fp32, preserve the registered F4 tolerance, and
  prohibit F2/F3/F5 recomputation.
- Do not automatically start Plan B, a larger J-lens fit, higher-n behavior, or
  the locked parser-v2 evaluation.

Reason:

- The pinned official `jlens` package imported, wrapped the exact target
  revision, computed one real Jacobian with 1536 successful autograd calls,
  fit three fp32 matrices from two generic prompts, checkpointed durably, and
  remained comfortably inside T4 memory/time guards.
- The primary failure was caused by official `JacobianLens.save` defaulting to
  fp16, not by an unsupported Jacobian, CUDA OOM, timeout, or scientific
  quality result.
- The retry verified and reconstructed the completed primary F3 checkpoint,
  produced exact fitted/reloaded fp32 matrix equality, passed the unchanged F4
  save/load/apply gate, and completed final manifest-last persistence.
- Measured 10-prompt and `[10,10,5]` 25-prompt projections fit the registered
  watchdog, but those larger fits were not actually executed.

Evidence:

- Target:
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B@ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`.
- Official source:
  `anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`.
- Run ID / Blob root:
  `20260718T184445Z` /
  `phase05-jlens-feasibility/20260718T184445Z`.
- Primary execution: `job-jspace-p05-jlens-l7tipil`, Failed at F4 with
  `CheckpointValidationError: F4 saved/reloaded apply mismatch at layer 13`.
- Operational retry: `job-jspace-p05-jlens-m1sazlr`, Succeeded.
- Final lens SHA-256:
  `8551dea7d3eba03930765ad65d108dec79a022a779755a3aec63f3c0da716318`.
- Final snapshot:
  `attempts/operational-fix/snapshots/11-final`; manifest uploaded last,
  persistence confirmed, failed uploads zero.
- Seven post-run `gpt-5.6-sol/max` reviews passed after stale publication text
  was corrected.
- Final model-free validation: `597 passed, 2 warnings`.

Consequence:

- Plan A has passed a tiny-scale engineering feasibility gate, not a
  scientific evidence gate.
- F5 was not run because the retry prohibited additional fitting.
- Token rankings and F4 top-k output remain technical transport/application
  sanity only.
- No new formal behavioral observation, higher-n result, locked evaluation,
  hidden-reasoning result, internal-workspace result, or J-space result was
  produced.
- The next registered gate is a separately authorized one-shot parser-v2
  locked evaluation. Until authorization, stop.

## 2026-07-23 — preserve at-most-once dispatch by accepting fail-closed stranding

> The mutable ACA Job-state mechanism below is superseded by the Private DNS
> launch/dispatch decision later in this log. The no-retry/stranding policy
> remains in force.

Decision:

- Keep the parser-v2 locked evaluation on the registered Azure Container Apps
  Job path and issue at most one non-retrying `start` request per durable claim.
- If the request result cannot be tied to exactly one new ACA execution, persist
  `dispatch-stranded` as a permanent no-retry launcher state.
- Permit only observation or adoption of one late execution after stranding;
  never issue another start from `start-requested`, `dispatch-stranded`, or
  `execution-established`.
- Apply the same fail-closed principle to an ambiguous ACR quick-build
  submission before any private holdout access.

Rejected:

- Do not use a caller-selected ACA execution name; the 2024-03-01 Jobs Start
  contract does not expose one.
- Do not treat `x-ms-client-request-id` as an idempotency key.
- Do not add an Azure Automation runbook broker. Automation can restart an
  interrupted runbook from the beginning, so one deterministic Automation Job
  can still replay the downstream non-idempotent ACA start request.
- Do not rely on repeated ACR TaskRun PUT requests as a new hard guarantee;
  `forceUpdateTag` exists, but the service documentation does not state the
  at-most-once behavior required here for identical repeated updates.

Reason:

- No available documented ACA primitive can atomically combine the durable
  local start intent with the service-generated execution identity.
- Retrying an ambiguous start can produce two scientific executions. Refusing
  every retry can lose liveness but preserves the controlling one-shot
  invariant.
- A stranded claim occurs before an execution is proved. If it happens after
  the holdout has already been spent by an earlier stage, the evaluation may
  remain incomplete; safety takes precedence over manufacturing a result.

Consequence:

- The normal no-crash path remains executable.
- A launcher/control-plane failure in the irreducible dispatch window can
  permanently stop Phase 1.2B. Such a stop is an operational INVALID/incomplete
  outcome, not permission to rerun a parser, reread labels, or replace the
  holdout.
- This decision changes only Azure launcher control state. It does not modify
  frozen parser bytes, metric semantics, gates, scientific state receipts, or
  retry authorization.

## 2026-07-23 — bind the one-shot image build through a named ACR TaskRun

> The deployment-reservation mechanism below is superseded by the Private DNS
> build-slot decision later in this log. Its TaskRun `If-None-Match` use is also
> superseded: an exact immediate `404` baseline and the DNS capability dominate
> one unconditional TaskRun PUT. The named TaskRun and GET-only recovery policy
> remain in force.

Decision:

- Replace `az acr build` with one raw HTTP PUT to a deterministic
  `Microsoft.ContainerRegistry/registries/taskRuns` resource after the durable
  build reservation wins its sole ETag-CAS transition.
- Disable curl retries and redirects, use `If-None-Match: *`, and permit no
  second PUT under any response or transport outcome. Recovery is GET-only; an
  absent TaskRun leaves the reservation permanently stranded.
- Authenticate the persisted TaskRun `runRequest` separately from its child
  `QuickRun`, which binds the service run ID, terminal status, staging image,
  and output digest.
- Bind TaskRun name/resource ID, request SHA-256, child Run ID, ACR location,
  exact Git source, OCI provenance, and immutable tag/manifest locks through
  the durable claim, image binding, runtime configuration, and launch-time
  live reauthentication.
- Reject Git replacement refs and require clean fetched
  `HEAD == origin/main == SOURCE_SHA` before any source-selected helper is
  snapshotted or executed.
- In persisted-state authentication, re-download every prediction and score
  payload member against its manifest SHA-256, size, and ETag, and validate all
  authorization-scoped Blob leaves even before `PREDICTIONS_VERIFIED`.

Reason:

- ACR Run GET responses expose `runType=QuickRun` and output metadata but do
  not expose `runRequest`; that request belongs to TaskRun properties.
- `az acr build` calls a retrying SDK `schedule_run` path, so it cannot prove
  one non-idempotent submission after transient 500/503/504 responses.
- A deterministic named TaskRun provides a durable request-bearing resource,
  while the external reservation CAS and the code's single PUT site preserve
  the required at-most-once caller behavior without assuming repeated PUT
  idempotency.
- Metadata-only payload checks and late-only leaf membership checks did not
  authenticate the complete persisted graph that authorizes a launch.

Consequence:

- Image construction remains model-free, CPU-only, and entirely before private
  holdout access, but it now fails closed on unprovable TaskRun creation,
  request mutation, child Run mutation, source substitution, payload
  replacement, or extra authorization-leaf objects.
- These changes harden operational provenance only. They do not alter frozen
  parser bytes, metrics, gates, holdout contents, or scientific interpretation.

## 2026-07-23 — use locked Private DNS TXT slots for operational CAS

Decision:

- Do not use `Microsoft.Resources/deployments` or ACA Job ETags as a
  compare-and-swap primitive. Their documented APIs provide no applicable
  conditional-write contract.
- Bind one existing, dedicated Azure Private DNS coordination zone in runtime
  configuration. It must be `global`, have exactly zero VNet links, retain the
  configured `internalId`, and have the exact direct or inherited
  `CanNotDelete` lock. Build and launch scripts validate these facts read-only
  and never create or delete the zone.
- Use deterministic build, launch, and dispatch TXT RecordSet names containing
  the complete SHA-256 claim domain. Create each once with API `2024-06-01` and
  `If-None-Match: *`. Only an exact HTTP `201` response followed by exact
  response/re-GET validation grants an ephemeral in-process capability.
- Permit only that build capability to reach the sole TaskRun PUT, only that
  launch capability to reach the sole immutable Job PUT, and only that dispatch
  capability to reach the sole ACA start. Every ambiguous or non-`201` create,
  ambiguous downstream request, and recovery path is no-retry and GET/list-only.
- Keep TXT payloads canonical ASCII and nonsecret. They may contain hashes and
  opaque authorization identifiers, but never secrets, labels, outputs, case
  IDs, raw holdout bytes, or other low-entropy private values.

Reason:

- Private DNS RecordSets CreateOrUpdate explicitly documents create-only
  `If-None-Match: *` and returns an ETag-bearing RecordSet.
- ACA Job PUT/PATCH and deployment PUT do not document the ETag/conditional
  semantics needed to authorize scientific work. Treating them as CAS could
  admit multiple contenders or unsafe retries.
- Separate launch and dispatch slots preserve the authorization boundary
  between immutable Job provisioning and the non-idempotent start request.

Consequence:

- A transport ambiguity can permanently strand a build or execution. GET may
  authenticate existing evidence and adopt exactly one remove-one execution,
  but can never recreate an ephemeral capability.
- Operational schemas now bind coordination-zone, build-slot, and launch-slot
  evidence. Frozen parser, evaluator, metric, gate, and holdout semantics are
  unchanged.

## 2026-07-23 — close one-shot parser and scoring crashes without rereads

Decision:

- At `INPUTS_READ`, allow one distinct parser-disabled prediction-adoption
  launch only when bootstrap authenticates exactly one complete immutable
  producer attempt. The adoption entrypoint may persist only the missing
  `PREDICTIONS_VERIFIED` receipt and receives no locked-input or parser options.
- After the labels payload is opened, adopt an ambiguous `LABELS_READ` create
  only by authenticating the exact receipt bytes. Never reread labels or
  rescore from a later process.
- If complete sealed score provenance is unavailable, create or exactly adopt
  an `INVALID` closure manifest that binds the labels transaction and receipt,
  producer identity, and observed score/state membership, then create or
  exactly adopt `CLOSED`.

Reason:

- Transport ambiguity must not turn an immutable-artifact recovery into a
  second parser execution, label read, or scoring attempt.
- A terminal `INVALID` graph proves holdout retirement and non-acceptance of
  metrics without emitting labels, case records, or raw predictions.

Consequence:

- Recovery may lose liveness when exact immutable evidence cannot be
  authenticated, but it cannot manufacture a scientific result.
- Normal PASS/FAIL and scientifically evaluated INVALID closures remain
  unchanged; this adds only an operational INVALID-to-CLOSED terminal variant.

## 2026-07-23 — require a private Linux orchestrator and separate identities

Decision:

- Execute parser-v2 build, bootstrap, launch, and recovery only from one
  private Debian 12 VM attached to the execution VNet with no public IP and
  private Blob DNS/connectivity. The local Windows host remains limited to
  planning, source control, and model-free local tests.
- Attach a dedicated control-plane user-assigned identity and the frozen
  runtime data identity to the VM. Authenticate Azure CLI with the control
  identity; derive and export the data identity client ID from the
  authenticated runtime binding for Blob SDK bootstrap.
- Attach only the runtime data identity to Stage P and Stage E Jobs. Never
  attach the control identity to either scientific stage.
- Treat VM, NIC/subnet placement, and identity provisioning as explicit,
  cost-bearing infrastructure that requires user approval before creation.

Reason:

- The local host resolves the storage account through the public path and has
  no managed-identity endpoint, while the locked source has public network
  access disabled.
- The launcher requires both ARM control-plane access and private Blob
  data-plane access, but those authorities must not be collapsed into the
  identity visible to scientific stage containers.
- The launcher and entrypoints rely on protected Bash, Linux absolute paths,
  and managed-identity selection and are not a supported Windows execution
  path.

Consequence:

- No private holdout operation can start from the local PC.
- Control-plane compromise does not automatically grant Stage P/E Blob data
  authority, and Stage P/E cannot create coordination records, Jobs, or
  executions through the control identity.
- No orchestrator resources are provisioned by the locked build/launch
  scripts or by this decision.

## 2026-07-23 — make dispatch and INVALID crash closure independently durable

Decision:

- Do not create a dispatch TXT record until the exact immutable ACA Job has
  reached authenticated `Succeeded` provisioning state and its full protected
  projection still matches the launch claim.
- Require recovery to authenticate both the launch TXT record and the exact
  deterministically derived dispatch TXT record. Recovery is GET/list-only,
  contains no Job PUT or ACA start capability, and may adopt only one
  remove-one execution relative to the launch-bound baseline.
- If bootstrap authenticates a labels-open transaction but cannot
  authenticate one complete sealed score graph, launch a distinct
  `invalid_closure`-only Stage E execution bound to the original scorer
  retry/execution. Pass no accepted score-manifest hash and permit no label
  payload read, scoring, parser invocation, or metric acceptance.
- Rebuild the labels-open transaction from authenticated prediction, label
  manifest, visibility, reservation, authorization, image, config, actor,
  retry, and execution provenance before writing or adopting deterministic
  `LABELS_READ`, redacted incomplete evidence, `INVALID`, and `CLOSED`.
- Clear coordination and execution-baseline evidence before each read and
  explicitly propagate every command failure, including when Bash disables
  `errexit` inside a conditional or command substitution.

Reason:

- ACA Job provisioning is asynchronous; consuming dispatch before a usable
  immutable Job exists can strand the only start authorization.
- A launch claim proves Job construction authority, not that the one-shot
  start was authorized. Recovery without dispatch proof could adopt an
  execution outside the intended mutation boundary.
- Labels may already have been exposed when a scorer crashes. Rescoring or
  rereading labels would violate the one-shot protocol, while leaving
  authenticated partial state open would fail to retire the holdout.
- Stale files plus implicit `errexit` behavior can otherwise turn a failed
  control-plane read into apparent authenticated evidence.

Consequence:

- Missing dispatch evidence or ambiguous Job provisioning may permanently
  strand the evaluation; safety dominates liveness.
- Pending or tampered post-label score state can terminate only as
  `CLOSED/INVALID`, with metrics and decision explicitly unaccepted.
- Frozen parser bytes, holdout bytes, metric semantics, gates, and normal
  PASS/FAIL scoring behavior remain unchanged.

## 2026-07-25 — accept the one-shot parser-v2 locked evaluation FAIL and retire the holdout

Decision:

- Accept **FAIL** as the formal, final outcome of the single authorized
  parser-v2 locked evaluation.
- Treat the 120-case locked holdout as spent and retired. It must not be
  reused, re-scored, or re-read.
- Do not enter a parser-v2 acceptance stage. Do not run higher-n or any new
  target-model behavioural work on the basis of this result.
- Do not attempt a metric retry or a prediction re-run. The sealed attestation
  and decision both record `metric_recompute_allowed = false` and
  `prediction_rerun_allowed = false`.
- Any modified parser requires a newly constructed locked holdout and a new,
  separately authorized one-shot evaluation.

Reason:

- Two mandatory gates failed against preregistered frozen limits:
  `boxed_final_miss` at 1/20 (limit 0 errors) and `wrong_span` at 2/80
  (limit 1 error). A single mandatory gate failure is sufficient for FAIL.
- The result is authenticated end to end: the state chain reaches `CLOSED`
  with `outcome = FAIL`, and the decision, metrics, closure manifest,
  retirement record, scoring attestation, and every scoring-ledger row agree
  on the same frozen input, prediction, label, image, and execution bindings.
- The single authorized post-result review independently recomputed the
  outcome from the sealed ledger and the frozen gate contract and agreed on
  all 38 checks, so the FAIL is not an artifact of the aggregation code.
- The primary Stage-E attempt failed for an infrastructure reason only and
  never opened the labels, so consuming the `scorer_infrastructure` retry did
  not expose the holdout to more than one scoring pass.

Consequence:

- Parser v2 is not validated on the locked set. Prior parser-v2 claims remain
  restricted to the 60-case public development set.
- The failure is concentrated in span recovery: `PV2-558779a7e52af7e736d3`
  trips both failing gates and `PV2-73e4060ef6bd6cd63e40` trips `wrong_span`.
  Report-only typed agreement remains high at 116/120, so the gap is narrow
  but preregistered and binding.
- The locked-evaluation capability is now exhausted for this holdout;
  remaining evaluator-validation work must be planned against a new set.
- No hidden-reasoning, invisible-CoT, internal-workspace, or J-space claim
  follows from this result.

## 2026-07-25 — adopt five parser-v3 rule changes and leave two retired cases unaddressed

Decision:

- Adopt five extraction rule changes in the new standalone parser v3, each
  stated as a general principle rather than a case patch, and each guarded by
  independent fixtures:
  - **C1** boxed payloads are decoration-tolerant.
  - **C2** decoration is transparent for markers and equations.
  - **C3** the `is` separator generalizes to all marker labels.
  - **C4** the unit-word list is removed from continuation invalidation.
  - **C5** the placeholder test runs before the operator test.
- Deliberately change nothing in response to the retired mismatch cases
  `PV2-406d4d4c3ba1a1b8c286` and `PV2-78396f528ee910ba7a09`.
- Keep parser v2 and the legacy parser frozen and byte-identical.

Reason:

- The two failed gates are both span- and recall-shaped, and every adopted
  change is derivable from a stated principle that also fixes independently
  authored fixtures, so the changes are not case-specific overfitting to the
  two known offenders.
- For `406d…` and `7839…` no locally derivable fix existed: every candidate
  rule contradicted at least one row of the frozen 60-case development set.
  Contradicting frozen development evidence to close two cases whose text was
  not read would have been a worse trade than leaving them open.
- Freezing v2 and legacy keeps the retired FAIL reproducible and keeps any
  future v2-vs-v3 comparison honest.

Consequence:

- All five changes are recall-increasing. Parser v3 therefore has an
  unprobed precision blind spot, and the one deducibly precision-shaped
  retired failure (`PV2-406d4d4c3ba1a1b8c286`) remains unaddressed. If
  over-extraction dominates a future holdout, v3 could score worse than v2.
  This is the primary caveat on the whole track.
- Parser v3 is not validated and no formal result may be claimed for it. A
  formal result requires a newly constructed, independently authored locked
  holdout and a separately authorized one-shot evaluation.
- The 65 adversarial fixtures share authorship with parser v3 and therefore
  cannot serve as the independent oracle.

## 2026-07-25 — Accept ENGINEERING_IMPROVING as the Phase 0.5B result

Decision:

- The Phase 0.5B J-lens saturation run `20260725T122016Z` is recorded with its
  emitted outcome, **ENGINEERING_IMPROVING**, and is neither re-run nor re-framed.

Rationale:

- `ENGINEERING_IMPROVING` is one of the preregistered outcomes of this stage. It
  means the transport-and-numerics half of the protocol passed cleanly while the
  convergence half did not yet reach threshold. That is information, not failure, and
  reporting it as anything softer would be a misrepresentation.
- Every stability criterion passed with very large margin: shard-merge versus direct
  fit differed by 2.384e-07 against a 1e-05 limit and by 4.862e-08 relative Frobenius
  against a 1e-06 limit, save/load was bit-exact, and the finite rate was 1.0. The
  fitting, sharding, merging and serialization pipeline is therefore demonstrably
  sound.
- The two convergence criteria failed by wide margins (relative Frobenius 0.4170
  against a 0.10 limit; cosine 0.9205 against a 0.99 limit). This is not marginal and
  must not be described as "nearly converged".

Consequence:

- No larger J-lens fit is authorized until the main agent reviews these measurements.
  No behavioural or semantic gate is opened by this run.
- The measured cost is essentially linear at roughly 52.8 s per fit prompt with peak
  reserved memory near 3.8 GB in both configurations, so a larger fit is affordable on
  the same T4; the open question is scientific, not budgetary.
- The nested design (the 10-prompt set is a subset of the 25-prompt set) means the
  comparison measures estimator movement as data is added, not independent
  replication. Any future saturation claim needs disjoint fit sets.
- Top-k overlap of 0.82 and rank correlation of 0.969 are recorded as technical
  stability statistics only. They are explicitly not semantic evidence and support no
  workspace, hidden-reasoning, invisible-CoT, or J-space claim.

## 2026-07-25 — Defer the Phase 1.0C headroom calibration GPU run

Decision:

- Track B is recorded as preregistered-and-blocked. The pack ships with status
  **BLOCKED** and no measurement is claimed.

Rationale:

- The main `Dockerfile` validates a build attestation from
  `.semantic_audit_build_provenance.json`, which is gitignored and absent from the
  worktree, so the `j-space-observation` image cannot be rebuilt at this commit and
  no calibration image exists in the registry.
- Fabricating a substitute Dockerfile to unblock the run would have changed the build
  provenance of a scientific artifact in the same round it was first used. That is a
  worse outcome than deferring.

Consequence:

- The preregistration, selection rules, thresholds and analysis code are frozen and
  committed now, before any data exists, which is the property that makes the eventual
  run credible.
- Restoring the build attestation, or authoring a dedicated calibration image with
  recorded provenance, is a prerequisite for executing Track B.

## 2026-07-25 — Do not seal the parser-v3 locked holdout this round

Decision:

- The parser-v3-v1 locked set is recorded as **constructed but not sealed**.

Rationale:

- One registered pre-seal cross-check, the overlap comparison against the retired
  parser-v2 locked inputs held in Blob, was not executed. Sealing before running a
  registered check would defeat the point of registering it.
- The seal itself requires a `Storage Blob Data Contributor` grant on the results
  container. That is a write privilege on immutable scientific storage and was not
  created for an operation that could not yet be completed correctly.

Consequence:

- The holdout is **not** locked. No parser-v3 evaluation may be run against it, and no
  parser-v3 result may be claimed, until the seal exists.
- The set, its labels, its manifests and the full sealing specification
  (`docs/phase1_parser_v3_sealing_run.md`, 12 objects, `set_manifest.json` written
  last, `overwrite=false`) are complete and carried forward unchanged.
- The independence evidence that was obtainable is strong: zero exact, normalized and
  numeric-normalized collisions against every reachable prior corpus. The residual
  risk is confined to the one corpus that could not be reached.

## 2026-07-25 — Report the outstanding parser-v3 cross-check as NOT PERFORMED

Decision:

- Cross-check 1 for the parser-v3-v1 seal is recorded as **NOT PERFORMED**, with the
  exact blocking reason, rather than being skipped silently or inferred from the
  checks that did run.

Rationale:

- Two of the three registered pre-seal overlap checks returned zero collisions and a
  third is vacuous by construction. It would have been easy, and wrong, to treat the
  outstanding check as a formality. The retired parser-v2 holdout is precisely the
  corpus with the highest prior probability of overlap, because parser v3 was
  developed from its failure analysis.
- The blocker was a wedged Azure Run Command extension, which says nothing about
  overlap. Reporting an untested claim as tested is the specific failure mode this
  project exists to avoid.

Consequence:

- The parser-v3-v1 set stays unsealed and unlocked. No parser-v3 evaluation may be
  run against it and no formal parser-v3 result may be claimed.
- The temporary read grant created for the attempt was deleted and its removal
  verified; no privilege was left standing to make a later attempt easier.

## 2026-07-25 — Seal the parser-v3-v1 holdout, and disclose that ABAC enforced nothing

Decision:

- The registered pre-seal cross-check against the retired parser-v2 locked inputs
  returned zero collisions on all three registered fingerprints, so the
  `parser-v3-v1` holdout was sealed to immutable storage at
  `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/`, 12 objects,
  `set_manifest.json` last.
- The teardown result that did **not** meet its expectation is recorded as
  measured, not as met. Subscription-wide Blob roles for the sealing identity are
  `1`, not `0`.

Rationale:

- The gate was defined in advance and was binary: seal if and only if exact,
  normalised and numeric-normalised collision counts are all zero. They were all
  zero, against the corpus with the highest prior probability of overlap, so the
  gate opened. Had any been non-zero the set would not have been sealed and no
  case would have been swapped this round.
- The alternative to disclosing the standing role was to report the specified
  expectation as met. That would have been false, and it would have propagated a
  security claim the project cannot support. The seal's integrity rests on
  digests and round-trip verification, which are unaffected; only the isolation
  claim is affected, and only the isolation claim has been weakened in the
  ledgers.

Consequence:

- `EV-0007` moves from `CONSTRUCTED_NOT_SEALED` to `SEALED`. `CL-06` records
  holdout sealed = yes, and its status stays **unsupported**, because the
  parser-v3 one-shot locked evaluation has not been run and was explicitly out of
  scope this round.
- `L-13` is rewritten from "not sealed" to the sealed reality with its residual
  caveats. `L-17` is added for the RBAC finding.
- The next gate is a separate, later round: a one-shot parser-v3 evaluation
  against the sealed holdout, run once, with predictions and scores produced
  under their own protocol. Nothing in this round licenses any parser-v3 accuracy
  claim.

## 2026-07-25 — Amend the J-lens fit corpus and accept REPLICATE_IMPROVING as the Phase 0.5C result

Decision:

- The Phase 0.5B fit corpus was amended from 50 to 60 records by appending ten
  `role=reserve` prompts, because the disjoint 25-prompt sample the round
  required did not exist and could not be produced any other way without
  invalidating Phase 0.5B. The amendment was made append-only, registered in the
  Phase 0.5C protocol before the run, and machine-verified.
- The Phase 0.5C outcome is accepted as measured: status COMPLETE, decision
  **REPLICATE_IMPROVING**, with **both** replicate criteria recorded as FAILED.
- No direct 50-prompt fit was performed, and none will be commissioned on the
  strength of this result.

Rationale:

- Amending the corpus was preferred over the alternatives. Re-partitioning the
  existing 50 records would have moved prompts out of the Phase 0.5B fit set and
  broken the reproducibility of an already-recorded run. Reusing the 15 reserve
  prompts alone would have compared n=25 against n=15, which answers a different
  question. Appending is the only option that leaves every prior byte and every
  prior number intact, and the prefix hash proves it did.
- The decision rules were frozen before the run, including the exact numeric
  definition of "the merge improves" (`mean(pair(25A,50M), pair(25B,50M)) -
  pair(25A,25B)` clearing 0.02 for top-k overlap and 0.005 for rank correlation
  simultaneously). The measured values cleared both margins and the replicate
  thresholds failed, so `REPLICATE_IMPROVING` is the outcome the pre-registration
  compels. It is being recorded, not celebrated.
- The failed criteria are not softened. Two same-size lenses fitted on prompts
  with nothing in common differ by 0.4831 relative Frobenius, which is the same
  order as the 0.4170 that Phase 0.5B measured between a 10-prompt fit and the
  25-prompt fit containing it. Sampling variability alone is therefore large
  enough to account for the earlier movement, so the nested result cannot be read
  as approaching saturation.
- The merged improvement is not treated as convergence evidence. The merge is an
  exact weighted mean of its two inputs and its distances to them agree to
  1.7e-08, which is the arithmetic signature of a midpoint rather than a finding.

Consequence:

- `EV-0009` is added with `claim_strength = engineering_only`. `CL-02` stays
  **unsupported**: independent replication has now been measured and not
  achieved, and no validity criterion exists or is designed.
- `L-15` is rewritten from "the comparison is nested" to the disjoint result and
  its weakening effect on any saturation reading. `L-18` is added for the
  arithmetic near-inevitability of the merged improvement. `L-19` is added for
  the provenance asymmetry between the two fit samples.
- The corpus amendment is recorded as round-level deviation `D14`. The executed
  pack's `08_deviations.json` stays empty, because zero runtime deviations from
  the Phase 0.5C protocol occurred and the pack is an immutable record of the
  run, not of the round.
- Next gate: main-agent review only. No behavioural, semantic or scientific gate
  is opened. A variance estimate would need many independent same-size fits and
  is not budgeted; a validity criterion remains undesigned and is the actual
  blocker for `CL-02`.

## 2026-07-25 — Accept INCONCLUSIVE as the Phase 1.0C Track B result, and do not relax the finalize rule

Context:

- The calibration ran and produced real data: 300/300 generations, 0 errors, 30
  cells. All 225 flagged rows were semantically adjudicated with complete
  coverage and zero rows meeting the registered arbitration trigger.
- Ten of thirty cells received a scored accuracy. Two of those met every
  preregistered per-cell gate. The other twenty cells contain at least one row
  adjudicated `unresolved`, which the preregistered per-cell rule
  ("A cell qualifies only when it has zero unresolved semantic labels") excludes.
- The pack-level status is governed by a separate preregistered rule recorded in
  `docs/phase1_headroom_calibration_protocol.md:329`: a `finalize` pack is
  `INCONCLUSIVE` when "Outstanding mandatory reviews **or unresolved labels**
  remain". 44 of 300 rows were adjudicated unresolved, so the pack is
  `INCONCLUSIVE` even though there are zero outstanding reviews.

Decision:

- **Accept `INCONCLUSIVE`.** The tooling implements the frozen rule correctly and
  the rule was registered before any data existed. Relaxing the pack-level gate
  after seeing that it blocks a `HEADROOM_CELLS_SELECTED` outcome would be
  outcome-dependent analysis, and it was explicitly considered and rejected on
  those grounds. The gate was not touched.
- The 44 unresolved rows are not an adjudication backlog. They are rows whose
  emitted output states no answer a reviewer could read — token-cap truncation
  mid-derivation, degenerate repetition loops, and unfilled answer templates.
  Re-reviewing the same outputs cannot resolve them. Only a changed generation
  profile could, and that would require a new preregistration.
- The two qualifying cells are recorded as **candidate** ablation substrates.
  They are not promoted to an established result, because `n = 10` per cell is a
  screen and a 7/10 cell's Wilson 95% interval spans `[0.397, 0.892]`.

Consequence:

- `EV-0004` moves from `REGISTERED_NOT_RUN` to `COMPLETE_INCONCLUSIVE` with
  `claim_strength = preliminary`. `CL-05` moves from **not yet measured** to
  **preliminary** and is capped there; it may not be promoted on this evidence.
- `L-16` is rewritten. It previously said Phase 1.0C was "registered but
  unmeasured", which is now false; it now records the n=10 screening limit, the
  44 unresolved rows, the token-cap-driven truncation, and the single-reviewer
  adjudication.
- Three reporting defects found in the round's own tooling were fixed, with no
  gate, threshold or classification changed and status/`criteria_passed`/
  `criteria_failed` byte-identical: `05_summary.md` reported "None recorded"
  under deviations while `08_deviations.json` already carried four execution
  implementation changes; protocol deviations rendered as raw Python dict reprs;
  and the finalize `next_gate` told the reader to return rows for adjudication
  even when every flagged row already carried a label. `04_decision.json` now
  also carries `outstanding_review_rows` so the two conditions are separable by
  machine.
- Round-level deviation framing, recorded in `08_deviations.json` with measured
  numbers: `protocol deviation: none`; `execution implementation change: a
  dedicated calibration image was introduced because the generic image required
  an unavailable historical attestation`. The attestation is unrecoverable from
  git history, ACR and Blob, and unregenerable because the registered generator
  asserts equality against a frozen 30-entry `RUNTIME_FILES` list while the
  repository now tracks 63 behavior files (33 extra, 0 missing).
- Next gate: main-agent review only. No behavioural, semantic or scientific gate
  is opened. Nothing in this pack licenses a claim about hidden reasoning, an
  internal workspace, invisible chain-of-thought, or a J-space.


## Phase 1.2D - parser-v3 preregistration decisions (commit `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea`)

- **Terminal outcome is binary.** The round must end in `PASS` or `FAIL`.
  `INVALID` is reserved for integrity or provenance corruption only. There is no
  manual override, and both `PASS` and `FAIL` retire the holdout.

- **The gating comparator is parser v2, not the legacy parser.** The derived
  contract's `clean_pooled_non_regression` and `critical_strict_improvement`
  gates compare parser v3 against parser v2. `critical_strict_improvement`
  remains **mandatory** under that remapping, which is strictly harder than the
  parser-v2 round and can turn `PASS` into `FAIL`. This is preregistered
  deliberately.

- **The legacy stream is reporting-only.** It is generated and sealed with the
  other two, but it is scored only after the holdout has been retired, inside a
  guarded pass whose failure cannot alter `PASS`/`FAIL`. Its aggregates are
  published in the Stage E result and report rather than in the sealed score
  members.

- **Historical `parser_v2_*` field names are retained.** Renaming roughly 44
  sites immediately before a one-shot evaluation would enlarge the risk surface
  without adding a security property. Candidate identity is carried by the
  import-time profile, the hardcoded worker identity, the algorithm ID, the
  parser version, the source SHA-256, and the prediction seal. Every metrics
  record additionally carries a `parser_attribution` block. Full record:
  `docs/phase1_parser_v3_orchestrator_schema_compatibility.md`.

- **The candidate parser is selected by entrypoint, never by argument or
  environment.** The profile is seeded into the module namespace before the
  module executes, is fixed before any locked input is read, and cannot be
  rebound afterwards. Parser v2 remains the default profile, so every
  pre-existing caller is byte-identical.

- **Stage E loads no parser under any profile.** Its profile is a *scoring*
  profile. The candidate parser's filename, module name, bytecode stem,
  code-object names and dynamic-import strings are all denied, and the finalizer
  reads only sealed prediction streams.

- **Build files were derived, not rewritten.** `Dockerfile.parser-v3-eval`,
  `09_build_parser_v3_eval.sh`, `10_run_parser_v3_locked_eval.sh` and
  `parser_v3_azure_contract.py` are exact, counted substitutions of their frozen
  parser-v2 originals. The image is tagged with the immutable source commit;
  `latest`, mutable tags, runtime `pip install` and floating dependencies are
  all rejected by the build script.

- **Round paused before execution, not before decision.** No POSIX host is
  available on the development machine to run the preregistered launchers, so
  Stage P has not run. Nothing about the freeze depends on that; execution
  resumes from `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea` unchanged.

- **Next gate:** build the immutable evaluation image once from `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea`, then
  Stage P, seal, Stage E, and one formal `PASS`/`FAIL`. Nothing in this
  preregistration licenses any claim about hidden reasoning, an internal
  workspace, or a J-space.

## Phase 1.2D — halt the parser-v3 locked evaluation before preregistration

**Decision:** Do not preregister, do not build, do not run Stage P. Halt the
round with the one-shot holdout `SEALED` and unspent, and publish the nine
findings instead of a `PASS`/`FAIL`.

**Why.** Preflight found that the sealed parser-v3 validation set, the frozen
scoring instrument and `docs/phase1_parser_v3_acceptance_gates.json` are three
artifacts that do not describe the same thing. Full detail is in
`docs/phase1_parser_v3_locked_evaluation_protocol.md` §15.

The decisive finding is `H9`, which involves no instrument at all. The gate
contract admits three typed-decision labels and declares
`typed_decision_support = {ambiguous: 10, no_answer: 30, present: 80}`. The
sealed set contains **four** classes — including `present_unextractable`, which
`null_collapse_prohibited: true` forbids collapsing — and its real support is
`{present: 91, no_answer: 23, ambiguous: 6}` plus 4 unextractable. The gates
`ambiguity`, `no_answer`, `answer_presence_macro_f1` and
`overall_exact_typed_decision` are calibrated against the declared support, so
against the real set their difficulty is different and unknown.

No instrument — frozen, adapted or v3-native — can score this set against these
gates. The defect is in the artifacts, not the tooling.

**Root cause.** The v3 gate contract was derived from v2 by substitution rather
than re-derived from the v3 set. The `last_number_trap` blocks in the two
contracts are byte-identical, including an `error_definition` naming a
registered distractor span the v3 set does not contain. Meanwhile
`scripts/build_parser_v3_validation_set.py` built the set to its own
conventions with no cross-check against either the instrument or the contract.
There was no artifact-level agreement test between set and contract.

**What was rejected.**

- *Score the 105 of 120 records that do validate.* Rejected: the contract fixes
  `total_cases = 120`, `cases_per_stratum = 10` and every gate denominator.
  Dropping records is a population change.
- *Preregister a mapping for the 15 divergent records.* Rejected: they differ
  semantically, not representationally. Mapping `present_unextractable` to
  `no_answer` is exactly the collapse the contract prohibits.
- *Amend the contract now to match the set and run this round.* Rejected: the
  support counts would be rewritten after observing the set, and the gate
  thresholds were calibrated against the old support. That is a threshold and
  population change disguised as a correction, made days before an irreversible
  scoring run.
- *Write a v3-native scoring instrument now.* Rejected on the same ground plus
  one more: the frozen instrument's hash pinning is the trust anchor of the
  whole protocol. A new instrument authored immediately before a one-shot run,
  reviewed by nobody, defeats the purpose of having one.

**What is kept.** The six normalisations `N1`-`N6` are validated and recorded
in §15.4. They lift the frozen-valid projection from 22 to 105 of 120 with all
105 typed decisions preserved, and they make the mandatory `last_number_trap`
gate non-vacuous on all 10 S06 cases — it would otherwise have passed
unconditionally while appearing to be enforced (`H3`). `N4` and `N5` are the
frozen instrument's own definitions, not inventions. This design is reusable
once the set and contract are reconciled.

**What this costs.** Nothing irreplaceable. The holdout's one-shot budget is
untouched. Parser v3 is unchanged and still frozen at source SHA-256
`76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9`. Because no
preregistration commit was created, the parser, the gate contract, the profile
binding and the membership rules remain editable — which is what the
remediation requires.

**Disclosed.** Diagnosing `H2`, `H3`, `H5`-`H9` required reading aggregate
structural metadata of the local curator copy of the v3 labels: field names,
enum vocabularies and counts, histograms, and masked numeric shapes. No
answer value, span text, offset or output text was read, and the sealed
holdout blobs were never read. Recorded as `H4` in §15.7.

**Next gate:** re-derive the parser-v3 gate contract from the parser-v3 set,
resolve `present_unextractable` explicitly, reconcile the span convention
across set and parsers, and add a mechanical preregistration check that
reproduces every declared support count, gate denominator and enum vocabulary
from sealed bytes before any image is built. That check is a pure function of
two sealed artifacts and would have caught `H9` immediately.

---

## Phase 1.2E — repair the parser-v3 evaluation ontology in public before touching anything private

**Decision.** After the Phase 1.2D halt, run a tooling-only repair round: define
the formal ontology, the span convention, the migration rule and the
policy/facts separation in public, implement and test the machinery, and stop
before any private construction. Retire `parser-v3-v1` permanently rather than
repair it. Terminate the round `BLOCKED` on acceptance thresholds rather than
invent them.

**Why retire rather than repair `parser-v3-v1`.** Its 15 residual cases differ
from the frozen semantics semantically, not representationally. Any repair
would require re-labelling them, and re-labelling a sealed one-shot set by a
party who has already seen its structure is not a blind construction any more.
The set is preserved as `SEALED / UNSPENT / UNSCORABLE /
RETIRED_AS_INELIGIBLE`. `UNSPENT` is deliberately worded as a statement about
what did not happen — no label was read — and explicitly does not authorize
reuse. Its one-shot budget is not transferable.

**Why the three-class ontology, and why `present_unextractable` is excluded
rather than mapped.** The candidate parser and the frozen scoring semantics can
each represent exactly three decisions. Every available mapping of
`present_unextractable` asserts something false: `no_answer` asserts the text
contains no answer, `present` asserts the parser should have found one, and
`ambiguous` asserts multiple candidates. The class is therefore excluded from
the formal set and permitted only in a separate research-only corpus that is
never scored. Collapsing it is precisely the `null_collapse_prohibited`
violation the contract already forbade.

**Why literal-only spans.** All three parsers emit literal-only spans through
the frozen `validate_evidence_span`, and the frozen scorer enforces
`normalize_rational_literal(span.text) == span.normalized_answer`. A
marker-inclusive span can never satisfy that identity, so a set registering one
could never be scored — that was `H5`. One convention now binds labels,
parsers, comparators, validation and scoring, and a span the scorer would
reject invalidates the set before sealing.

**Why the prospective policy and the set-derived facts are two artifacts.** The
structural cause of `H9` was a single artifact carrying both a prospective
commitment and an implied factual claim about a set, with no mechanical check
between them. They are now separate, with separate lifecycles, and the compiler
fails closed on any disagreement. "Derive from the set" is defined to mean
mechanically reproduce and verify — never to mean rewrite a quota or threshold
to match an observed distribution. There is no code path that edits a
threshold.

**Why the supports are 80/30/10 even though v2 used the same numbers.** They
were derived from the public stratum definitions — eight answer-bearing strata,
three no-answer strata, one ambiguous stratum, at ten cases each — not copied.
The derivation is shown explicitly and is re-checked by `validate_policy`,
which rejects any support block not reproducible from the declared stratum
presence. The coincidence with v2 is a consequence of both sets instantiating
the same registered 12-stratum design.

**Why zero-tolerance mandatory gates are not calibrated thresholds.** They
follow from stratum purpose, which is a public design fact. `S06` exists only
to detect selection of a trailing distractor, so a single such selection is the
failure the stratum was built to find. That is a definition, not a calibration.

**Why the round terminates BLOCKED.** The numeric acceptance thresholds are a
genuine unresolved scientific choice. Phase 1.0C headroom calibration has not
been run. The two shortcuts are both inadmissible: parser-v2 constants would
import an unjustified number of exactly the kind this phase exists to
eliminate, and any parser-v3-derived threshold would be selected against the
measurement it is meant to bound. Marking them `REVIEW_REQUIRED` and having the
compiler refuse to compile is the honest outcome; guessing a number to reach
`READY_FOR_INDEPENDENT_SET_REPAIR` would have reproduced the original failure
in a new artifact.

> **Erratum E-1.2F-01, appended 2026-07-26 (Phase 1.2F).** The original text
> above is retained verbatim as the historical record. The sentence "Phase 1.0C
> headroom calibration has not been run" was **false when written**. Phase 1.0C
> executed and finalized `INCONCLUSIVE` at `06eec993`, a fact already recorded
> in this same log at the 2026-07-25 entry "Accept INCONCLUSIVE as the Phase
> 1.0C Track B result". It is also a category error: Phase 1.0C screens
> target-model observable-answer task headroom, not parser extraction fidelity.
> The conclusion of the entry — that guessing a number would reproduce the
> original failure — is unaffected and was upheld by the Phase 1.2F audit.

**Why bind to the frozen instrument rather than restate it.** This decision was
forced by an independent audit, and it is the most important one in the round.

The first implementation described the frozen scorer's invariants in fresh code:
a truth table in prose and a validator that re-implemented the rules the table
stated. It looked rigorous and it passed 93 tests. It was also wrong in two
places at once — `ambiguous` was declared `parse_valid = false` where the
instrument requires `true`, and the `present` row was materially more permissive
than the instrument — and the tests could not detect either, because the
fixtures asserted the same wrong invariants as the code.

Sealed under that table, every `S11` case would have been rejected by the
scoring instrument: ten cases, a full stratum, unscorable by construction. That
is the same failure that retired `parser-v3-v1`, reproduced inside the artifact
written to prevent it.

The mechanism is what matters. `H9` did not happen because someone chose a wrong
number; it happened because a second description of a thing was allowed to exist
alongside the thing, free to drift. Any validator that *restates* an invariant
recreates that freedom. Correcting the two rows would have left it intact.

So the ontology validator now calls the frozen `_validate_extraction_fields` and
`derive_typed_decision` on every record it accepts and requires agreement. A
record this tooling admits is a record the scoring instrument admits, by
construction. The truth table remains in the protocol as documentation of
intent; it no longer has independent authority.

The same reasoning produced the second structural fix. A set-facts manifest was
originally trusted on its face, with `set_sha256` digesting the manifest rather
than any set — so the auditor compiled a fully provenance-bearing contract from
a manifest describing a set that had never been built. Facts are now re-derived
from the labels and inputs they claim to describe, and required to match byte
for byte, before any comparison runs. A deliberate consequence is that several
agreement detectors become unreachable through the entry points: the manifest
can no longer disagree with the set, so the check that would have caught the
disagreement never fires. That is defence in depth working as intended, and the
detectors are retained and tested directly.

**Why the audit finding is recorded rather than quietly fixed.** The tempting
alternative was to correct the rows, keep the green test count, and describe the
round as clean. That would have deleted the round's most useful result. A
research record whose error log is empty is not a record of careful work; it is
a record of unexamined work. The general lesson is stated once, here: an
author's own tests cannot establish that the author understood the
specification.

**Rejected alternatives.**

| Option | Why rejected |
| --- | --- |
| Repair `parser-v3-v1` in place and evaluate it | Requires re-labelling 15 cases in a sealed one-shot set whose structure is already known. Not a blind construction. |
| Amend `docs/phase1_parser_v3_acceptance_gates.json` | Destroys the evidence of the defect and makes the historical record unauditable. The corrected contract is a different artifact with a different identity. |
| Score only the 105 structurally valid cases | Changes the population after seeing which cases are inconvenient. Breaks the 12 x 10 design and every gate denominator. |
| Map `present_unextractable` to `no_answer` | Asserts a falsehood and violates `null_collapse_prohibited`. |
| Pick thresholds now from parser-v2 values | Reproduces the substitution error that caused `H9`, in a new file. |
| Declare `READY_FOR_INDEPENDENT_SET_REPAIR` with thresholds open | The brief defines an unresolved scientific design choice as `BLOCKED`. Reporting otherwise would misstate readiness. |
| Correct the two audit findings without recording them | Deletes the round's most useful result. An empty error log records unexamined work, not careful work. |

---

## Phase 1.2G - Strict finite-suite conformance as the acceptance premise

**Decision.** The future `parser-v3-v2` evaluation set is treated as a **finite
conformance suite**. Every case admitted to it is a mandatory conformance
example. An exact typed-decision mismatch on any eligible case is unacceptable
instrument behaviour. `residual_critical_exact_budget` is therefore `0`, both
pooled and per stratum, on a `LOGICAL_INVARIANT` basis, and the prospective
acceptance policy is `FINAL`.

**Why this is a premise and not a measurement.** The question Phase 1.2F left
open was never answerable by observation. No amount of data tells you whether a
suite is a conformance suite or a sample; that is a statement about what the
suite is *for*, and it has to be decided. Phase 1.2F correctly refused to invent
a number, and correctly identified that a `LOGICAL_INVARIANT` basis for `B = 0`
was available in the abstract while the decision that would license it had not
been taken. Phase 1.2G takes it.

Once taken, the invariant is not a choice about strictness. If each case is
included because a correct instrument must handle it, then tolerating a failure
on one of them is tolerating the instrument being incorrect on a case selected
for the purpose of detecting exactly that. There is no coherent non-zero value:
each admitted case carries its own requirement, and an aggregate tolerance of
`B > 0` contradicts a per-case obligation rather than relaxing it. This does
not depend on a budget being unable to name which cases it covers — "at most
one mismatch anywhere" names nothing and is still incoherent here, because a
universally quantified obligation admits no exception count.

**What the derivation deliberately does not rest on.** Determinism of the
parser. The set not being an IID sample. The absence of a registered downstream
error budget. Conservatism. Tidiness or roundness of the number zero. Parser-v2
precedent. Any expectation about parser-v3 performance. Each of these would be a
different argument with different failure modes, and several would be
disallowed bases outright. A regression test scans the recorded derivation for
appeals to them.

**The falsifier, recorded with the premise.** If a case is ever admitted to the
set that a correct instrument is not required to handle - an aspirational case,
a stress case included to observe behaviour rather than to require it, a case
whose reference label is itself uncertain - the premise fails and the invariant
loses its basis. This is a constraint the set-repair round inherits: eligibility
for admission and "must be handled correctly" have to remain the same predicate.

**Why both a pooled and a per-stratum limit.** A pooled limit of zero is
arithmetically equivalent to per-stratum zeros today. They are both recorded
because they are not equivalent under *amendment*: a later editor relaxing one
stratum to `1` while holding the pool at `0` produces an inconsistent policy the
validator can catch, whereas a policy stating only the pool would silently admit
the per-stratum change. Redundancy between two statements of the same constraint
is cheap; a single point of drift is not.

**Rejected alternatives.**

| Option | Why rejected |
| --- | --- |
| Leave the budget `REVIEW_REQUIRED` and remain blocked | The blocker was a decision, not missing evidence. Waiting produces no new information and the operator has taken the decision. |
| Execute the registered calibration protocol first | It calibrates a downstream error budget, which is only needed if a non-zero tolerance is permitted. Under conformance the branch is moot. Executing it would have left the round blocked anyway - Phase 1.2F audit finding A3. |
| Pick a small non-zero budget, such as 1 or 2 | No candidate-independent derivation exists for any positive value, and any number chosen today would be chosen by someone who already knows how parser v3 behaves in development. |
| Justify `0` by the parser being deterministic | Determinism makes an error reproducible, not acceptable. It is an argument about variance, not about tolerance. |
| Justify `0` by conservatism | "Be strict when unsure" is a disposition, not a basis. It would license any threshold and explain none. |
| Keep `overall_exact_typed_decision_minimum` as a hard gate | With all 120 cases pinned it can never bind. A gate that cannot fire is a claim of protection that does not exist. |
| Keep macro F1 as a hard gate | Exhaustive enumeration of the 861 feasible confusion matrices at the registered supports shows it awards a passing score to candidates with wrong canonical values that preserve the presence class. It measures something real but not this. |
| Make the comparator binding | No prospectively choosable margin exists, and the one substantive argument for a binding comparator was withdrawn in Phase 1.2F as unsound. |
| Number the ten defects into the `H` series | `H1`-`H9` are findings about the evaluation instrument and its artifacts' declared-versus-observed facts. `G-01`-`G-10` are internal consistency failures between this project's own documents. Merging them would corrupt the meaning of both series. |
| Fix the stale figures and describe the round as clean | Six of ten defects were figures no prose pattern covered. Fixing them without adding the generator would have left the mechanism that produced them intact. |

## Phase 1.2H — block at the source-access precondition rather than proceed on an unverified copy

**Decision.** Terminate Phase 1.2H `BLOCKED_ON_PRIVATE_SOURCE_ACCESS` at the
first precondition, rather than proceed from the local curator copies.

**Why.** The local copies match the committed public manifest exactly, on both
SHA-256 and byte count. That is agreement with a Git record. It is not agreement
with the sealed source, and the sealed source is what the set identity is
defined against. The authorization is explicit that an unverified local copy
must not be substituted when the sealed source is unavailable, and the reason is
sound: a repair round that reads the wrong bytes produces a successor set whose
provenance claim is false, and the falsity would not be detectable later.

**Rejected alternatives.**

| Option | Why rejected |
| --- | --- |
| Proceed from the local curator copies | They agree with a Git record, not with the sealed source. The whole point of sealing is that the sealed bytes are authoritative. |
| Stand up in-network compute to reach the storage account | The blind semantic review executes as reviewing agents outside that network. Reading private content inside the boundary in order to transport it out defeats exactly the isolation the network rules encode. It would also require authoring and running new infrastructure and making irreversible role-assignment and blob writes, which this round was not authorized to do. |
| Relax the network rules on the storage account | An irreversible weakening of the boundary that protects the retired sealed set, taken to make a blocked round appear to succeed. |
| Register the full protocol suite anyway (import protocol, review schemas, seal layout, replacement rules) | An unexercised instrument frozen into the permanent record with the vocabulary of a completed procedure is later read as evidence that the procedure happened. This repository's audits have caught that pattern three times. The preconditions and prohibitions were registered; the mechanisms were not. |
| Record the round as a no-op and change nothing | The round had real, honest deliverables: the disclosed Audit E gap, the live-ledger separation, and the blocking analysis itself. Discarding them would lose information. |

## Phase 1.2H — carry live access state in a ledger, not in the `FINAL` policy

**Decision.** Introduce `docs/phase1_2h_execution_access_ledger.json` and treat
the policy's `execution_state` block as an immutable finalization snapshot.

**Why.** The artifact that states *how a future evaluation will be judged*
should not also be the place where *how many things have happened so far* is
edited. This project has already been bitten by a semantic change smuggled in as
a routine state update. Separating them means a licensed state edit can never
move the policy's semantic hash, and a semantic change therefore cannot hide
behind one.

The ledger is bound to the policy twice: by full-file SHA-256, and by a
`policy_semantics_sha256` computed over the policy with `execution_state`
projected out. The second is load-bearing precisely because it is stable across
future state edits.

**Rejected alternatives.**

| Option | Why rejected |
| --- | --- |
| Keep editing `execution_state` in the policy | Makes a `FINAL` rule document mutable for reasons unrelated to the rule, and re-opens the exact smuggling channel a prior audit found. |
| Record access state in prose only | Prose cannot be validated. Every prior round that relied on prose accumulated drift that a later audit had to find. |
| A single boolean `private_data_accessed` flag | Cannot express the distinctions that matter: repair access is not evaluation access, and a byte-only digest is not a semantic read. Collapsed flags get restated later as stronger claims than the evidence supports. |
| Project more than `execution_state` out of the semantic hash | Anything else excluded could then change undetected. The exclusion list is exactly one key and is itself validated. |

## Phase 1.2H — fix the incomplete provenance inside the policy rather than in a report

**Decision.** Edit `review_provenance` in the canonical policy, accepting the
resulting SHA-256 change, rather than recording the missing audit counts in the
Phase 1.2H report alone.

**Why.** An incomplete provenance record inside the artifact is a defect *of the
artifact*. Correcting it elsewhere leaves the artifact wrong and creates a
second place a reader must consult to learn the first place is unreliable.
Exactly one block changed; no threshold, gate, population figure, ontology
entry, comparator role, status rule or `execution_state` value was touched, and
the ledger records the change and its scope explicitly.


## Phase 1.2H — narrow the semantic projection instead of widening the schema

**Decision.** After Audit G, project only the five mutable `execution_state`
counters out of `policy_semantics_sha256` rather than the whole block, and
constrain the block's free-text statement against asserting a result. Also close
the policy's top-level key set.

**Why.** A prior decision in this same log defended excluding exactly one key on
the grounds that "anything else excluded could then change undetected". Audit G
showed that argument applied one level down and had been missed: the excluded
key was a *container*, and the prose statement inside it could be rewritten to
claim a completed evaluation without moving the hash. The same reasoning that
justified a one-key exclusion list requires excluding the counters rather than
their container. The earlier entry was not wrong about the principle; it applied
it at the wrong granularity, and that is recorded here rather than edited away.

## Phase 1.2H — validate the ledger in the generator, not only in tests

**Decision.** `scripts/generate_current_state.py` validates the ledger before
rendering it, loading the validator by file path rather than through the
package.

**Why.** Audit G's blocker was not that an invalid ledger could exist — it was
that the generator would faithfully publish one into `reports/current_status.md`
and `docs/thread_handoff.md`. A validator that runs only under pytest does not
protect the artifact a reader actually reads. The file-path load is deliberate:
`jspace_observation/__init__.py` eagerly imports the legacy parser, and the
generator has no business pulling parser code into its process.
## Phase 1.2H-R1 — go inside the network rather than declare the source unreachable

**Decision.** Provision a least-privilege, VNet-injected execution boundary and
run the byte-only access gate from inside it, instead of recording a second
round of `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`.

**Why.** Phase 1.2H's determination rested on reading
`publicNetworkAccess: Disabled` as "unreachable". That is a category error:
the flag says the account refuses the *public* data plane, and the account has a
private endpoint precisely so that in-network compute can reach it. Recording a
blocker that a correct reading of committed evidence dissolves would have been a
false negative, and false negatives about one's own capability are as damaging to
a research record as false positives about a result.

## Phase 1.2H-R1 — a terminal state must be earned, not selected

**Decision.** `BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY` is registered in the ledger
validator with a precondition: at least
`BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE` (14) cumulative byte-only
verifications and zero semantic reads. A round that has not completed the gate
must record `BLOCKED_ON_PRIVATE_SOURCE_ACCESS` instead.

**Why.** Independent Audit B (B-11) found that the round's own intended terminal
state was not a state the ledger would accept. The naive fix is to add the name
to the enum. That fix is unsafe: of the two blocked states, "I reached the source
and stopped at the reviewer" sounds strictly better than "I could not reach the
source", so a round that did *less* would have an incentive to claim it. The
precedence rule removes the incentive by making the better-sounding state require
strictly more evidence.

## Phase 1.2H-R1 — say which numbers are machine-derived and which are not

**Decision.** The ledger carries a validated `counter_provenance` block
partitioning every counter into `receipt_derived_exact`,
`azure_transcript_exact` or `operator_maintained_approximate`. Counters
carrying a safety claim — the semantic-read counters, the data-plane counters,
the parser and prediction counters — must be present and must not be classified
as operator-maintained.

**Why.** R1 produced both kinds of number at once. Eight counters come from a
schema-validated execution receipt. Two — the count of `az` calls made and of
resources touched over an interactive session — are an operator's tally and
cannot be anything else. Publishing them side by side without distinction lets
the second borrow the authority of the first. The specific laundering the
validator blocks is moving "no semantic read occurred" from receipt evidence to
recollection while leaving the value at `0`: the ledger would still read as
safe, and would no longer be evidence.

## Phase 1.2H-R1 — record a field as unobservable rather than grant privilege to fill it

**Decision.** `public_network_access` is recorded as `"Unknown"` and
`effective_read_only_verdict` as `NOT_CONFIRMED_IN_JOB`. The receipt schema
refuses any other value for the first.

**Why.** Both fields could have been made observable by granting the probe
identity additional roles — a reader role on the storage account, and a
role-assignment read. Doing so would have *increased* the privilege of the
identity whose minimality is the round's central safety claim, in exchange for
two fields that are already established by operator control-plane evidence. A
receipt that is honestly incomplete is worth more than one that is complete
because the boundary was widened to complete it.

## Phase 1.2H-R2 — stop after the second public audit cycle

**Decision.** Record `BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE`; do not remediate the
second-cycle findings under the current round, do not declare a Phase A freeze,
and do not begin Phase B or any private-semantic operation.

**Why.** Section 5.4 of
`docs/prompts/phase_a3_b_to_d_cloud_execution_prompt.md` permits at most two
independent audit/remediation cycles. Cycle two, against exact commit
`423d16a7b486b8c22fa58a733ffa6a03b389f0fe` and tree
`3080241e68dc007e91f49967beebbd80ff1d4ec6`, returned four verified BLOCKER
findings and one verified MAJOR finding. Treating a third code-remediation pass
as ordinary continuation would bypass the registered bound precisely when the
bound requires a stop.

**Consequence.** The only changes after the final audits are record-only:
persisting their exact reports, binding their hashes and findings in a terminal
receipt, and updating the public logs. Any later technical fix must start as a
separately authorized public-protocol redesign with a new bounded audit plan.

## Scientific restart — close the parser program instead of refounding it

**Decision.** The parser-v3-v1 and parser-v3-v2 locked-evaluation programs are
closed as `CLOSED_NONAUTHORITATIVE_TRIAGE_ONLY`. The project state becomes
`SCIENTIFIC_MAINLINE_RESTART_AUTHORIZED`. `L-01` is elevated from a temporary
limitation to the binding design rule `DR-01`: semantic adjudication is the only
authoritative final-label path, and an automatic parser may triage, route or
diagnose but may never be a final correctness label. The drafted
public-protocol-v2 refoundation is superseded and must not be executed. Full
record: `docs/decisions/parser_v3_locked_evaluation_closure.md`; authority
object: `docs/phase_science_restart_authority.json`.

**Why.** The locked-evaluation program existed for one purpose: to license an
automatic parser as an authoritative final label. Once semantic adjudication is
authoritative *by design*, that license is never spent, and every further round
of holdouts, private boundaries and audits buys an authority the project has
decided not to use. The second and final audit cycle also gave a substantive
reason not to continue: its four BLOCKER-class properties — Stage E member-ID
uniqueness, atomic create-only state, a structurally closed construction target,
keyed schema-array uniqueness — are not reachable by pure functions over
caller-supplied evidence, so a third cycle would have been a redesign, not a fix.

**What this decision refuses to do.** It does not revise
`BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE`, which remains correct under its own
authority. It does not edit, delete or rescore any receipt, report, sealed
object or counter; the closure record pins eight artifact digests so that later
drift is detectable as a defect. It opens no private holdout, label, prediction,
Stage P/E result or formal ordinal. And it does not claim the parser material is
publishable: the code, schemas, entrypoints, IaC and audit tooling are retained
as historical artifacts carrying four known unfixed defects (`L-42`), never as a
validated protocol.

**Cost accepted.** The project will never have a mechanically validated
evaluator, so every final label from Phase 1.0D onward is LLM operational
consensus with no locked bound on its error rate. That ceiling is recorded as
`L-41` rather than left implicit.

## 2026-08-02 — Treat Phase 1.0C as defective in generation profile, not in conclusion

Decision:

- The Phase 1.0C `COMPLETE_INCONCLUSIVE` result stands. Phase 1.0D repairs the
  generation profile and re-runs on a disjoint confirmation split; it does not
  re-score, re-label, or reinterpret a single Phase 1.0C record.
- Two defects are registered, both recomputed from the committed pack rather
  than asserted:
  - `P10C-D1` literal answer placeholder — all 300 prompts carried the literal
    line `Final answer: <answer>`; 31 outputs echoed the placeholder and 5
    echoed the whole line.
  - `P10C-D2` generation token cap — all 300 records ran at
    `max_new_tokens=512`; 79 of the 225 reviewed rows reached the cap.
- Single-cause attribution is refused. Over the 44 unresolved rows the two
  defects partition as 38 token-cap only, 4 both, 1 placeholder only, 1 neither.
  Neither defect alone explains the outcome, so Phase 1.0C must not be recorded
  as a GPU-budget failure and must not be recorded as a prompt-template failure.

Rationale:

- The authority's §4.1 numbers were stated, not derived. A repair protocol built
  on unverified numbers would inherit their risk. Recomputing them costs one
  bounded Azure run and converts the repair premise into evidence.
- The 1 unresolved row explained by neither defect is retained deliberately. It
  is the standing reminder that the defect list is a lower bound on what went
  wrong, and Phase 1.0D must be able to fail for reasons not on this list.

Consequences for Phase 1.0D:

- No condition may contain the literal placeholder, and every rendered prompt is
  asserted free of it before any inference is submitted.
- Per-condition token budgets are registered before inference: at least 1024 new
  tokens for the visible-reasoning control, and for the strict conditions a
  budget large enough for the registered answer but too small to permit visible
  reasoning.

Evidence: `docs/phase1_0c_generation_profile_defects.json`;
ACR run `cm3y` at commit `8333ccaefb0955d892aef18a6df4d4bc3bfe0aae`.

## 2026-08-02 — Freeze Phase 1.0D before inference, and accept that it exhausts the bank

Decision:

- The Phase 1.0D confirmation sample is every remaining public bank item that
  Phase 1.0C did not touch: all 300 of them, 20 per family x band cell, drawn
  from both the `confirmation` and the `mechanistic` splits. Selection is a total
  order (split rank, then `task_id`) with no random number generator, and
  disjointness is proven against the item ids Phase 1.0C actually generated on.
- Consequence, accepted deliberately: after Phase 1.0D no item in the bank is
  unused. There is no slack — a single ineligible item would have triggered
  `Phase1_0DBankShortage` and stopped the run before inference. Any later work
  needing items disjoint from both 1.0C and 1.0D requires a new prospectively
  specified public batch generated without reference to model or lens output.
  This is recorded as `L-43` rather than avoided by shrinking cells to 10, which
  would have reproduced the n=10 screen that made Phase 1.0C uninformative.
- All three arms decode greedily. The project's registered per-condition
  configuration is greedy for both strict conditions and for `r1_style_thinking`,
  so adopting it makes the arms differ only in renderer and token budget. Phase
  1.0C's sampled `official_style` profile was not carried over: a paired
  visible-minus-strict difference across different sampling regimes would have
  confounded the comparison it exists to make.
- The strict budget is 32 new tokens, not the registered 8/12. The registered
  caps were chosen for other rounds and are re-registered here under a distinct
  profile name (`phase1_0d_*`) so a 1.0D configuration can never be mistaken for
  them. 32 is justified by a proof rather than by taste: byte-level BPE gives
  `token_count <= utf8_byte_length`, and the longest registered answer is 15
  bytes.
- Arbitration never resolves toward `correct` and never resolves toward the
  parser. A primary/secondary disagreement becomes `unresolved` and demands an
  explicit third adjudication. A rule that broke ties toward the parser would
  reintroduce the automatic evaluator that `DR-01` forbids.
- The secondary-review sample is a hash of the record id, fixed before any label
  exists, so the 20% stratified sample cannot be steered by an outcome.

Rationale:

- Phase 1.0C failed as evidence for two recomputed reasons and one unexplained
  one. Freezing every biasing rule before inference is what converts 1.0D from a
  second attempt into a confirmation.
- The gate is a substrate selector, not a performance claim, and the module says
  so in the returned payload rather than only in prose. Every cell is reported
  whether it passes or not.

Evidence: `docs/phase1_0d_protocol_snapshot.json`;
`src/jspace_observation/phase1_0d_confirmation.py`;
ACR runs `cm44`, `cm45`, `cm46`, `cm47`.
## D-2026-08-02-04 - Spend the single preregistration review, correct once, then refreeze

Authority section 7 allows exactly one bounded preregistration methods review
and exactly one consolidated correction before any scientific output exists.
This decision spends both.

Two independent reviewers were used rather than one. Section 7 requires one
review; it does not forbid corroboration, and the cost of a missed defect here
is an entire GPU round producing an uninterpretable result. The corroboration
paid for itself immediately: both reviewers independently identified the missing
third-adjudication path, which is the difference between a cell that fails
because the model failed and a cell that fails because the code could not record
a human decision.

Four MATERIAL findings were corrected together, as a single consolidated change:
the third adjudication, true per-stratum sampling, strict-arm no-CoT compliance
in the gate, and a closed reviewer form with a committed ingestion path.

Three findings were deliberately NOT corrected, and this is the part that needs
justification rather than assertion.

- T-06 asks for a corrupted-prompt and prompt-echo control. It is right that
  without one, a correct strict answer is consistent with surface recoverability
  rather than retained competence. Adding an arm after the freeze would change
  the preregistered sample and design, which is exactly the manoeuvre
  preregistration exists to prevent. Recorded as L-45. Any claim that a Phase
  1.0D cell shows retained competence must discharge it with a prospectively
  registered control, not with an argument.
- T-04 asks the structural arm to be rendered from pinned chat-template
  metadata. That requires the tokenizer at plan time, coupling protocol
  construction to a downloaded model artifact and making the frozen protocol
  depend on something the laptop is forbidden to fetch. Recorded as L-46, with
  the requirement that a generation run record the actual input token sequence.
- T-01 asks that the RQ2 pilot be recorded as a selected-case pilot. That is a
  disclosure, not a repair, and it is recorded as L-47.

L-03 was neither corrected nor merely recorded. The claim was that the visible
arm's format exemplar `42` would leak if a registered answer were `42`. That is
a checkable fact, so it was checked: zero of 450 bank items have that answer. The
exemplar was kept, because a concrete value is precisely the remedy for the
Phase 1.0C defect where the model echoed the format instead of writing a value,
and an impossible exemplar would teach the format less well. A test now fails if
any registered answer ever equals the exemplar.

The section 7 allowance for the J-lens validity protocol of sections 5 and 6 is
NOT spent. That protocol does not exist yet, and a review cannot be performed on
something unwritten. It must be exercised when that protocol is frozen.

The protocol is refrozen at `protocol_sha256`
`25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8`. No further
preregistration review of the Phase 1.0D protocol is authorized.

## 2026-08-02 — Phase 1.0D generation driver: what it refuses to produce

The driver stops at a reviewed-shaped hole rather than filling it.

- **A generation pack reports no headroom number.** `05_decision.json` and
  `09_summary.md` both read `AWAITING_SEMANTIC_REVIEW`. Section 4.3 makes a
  semantic label the only thing that may decide correctness, so a pack emitted
  before review has nothing to report and says exactly that. The alternative —
  a parser-derived provisional accuracy, clearly labelled provisional — was
  rejected: a number in an artifact gets quoted, and the label does not travel
  with it.
- **No generation-time stop sequence is registered.** Section 4.2 permits a stop
  only after a complete registered final-answer surface. Declining to stop early
  always satisfies that rule; a stop string chosen wrongly could truncate a
  surface mid-write and the truncated text would then be reported as the model's
  output. The registered per-condition budget is the only bound, and no text is
  clipped after the fact.
- **Failed generations are counted, not dropped.** A backend error yields a
  record with an empty output and an error class in the telemetry, so the pack's
  item count always equals the planned count. A run that silently emitted fewer
  rows would shrink its own denominator.

Two defects in existing code were found and fixed rather than worked around:
`compute_cell_outcomes`/`build_decision` scored unlabelled rows as incorrect,
and the execution module's documented stage order could not run because
`annotate_review_selection` requires the primary label it was documented as
preceding. Both are recorded in the methods ledger.

**The generation run has not been performed.** The driver is exercised on CPU
against a deterministic stub backend, which establishes that the pack is
well-formed and the accounting is honest, and establishes nothing whatsoever
about the model. Reaching the run additionally requires a Phase 1.0D container
image, a build-provenance record, and an ACA GPU job launcher.

## 2026-08-02 — Phase 1.0D image: three decisions and one near-miss

- **A separate image repository, not a reuse of Phase 1.0C's.** Reusing
  `j-space-observation-calibration` would put a frozen historical record and a
  live one behind the same tag namespace and the same provenance generator, and
  the authority forbids overwriting or reinterpreting run 20260725T170041Z.
  Phase 1.0D uses `j-space-observation-phase1-0d` with its own provenance tool.
- **The build verifies itself instead of carrying an attestation.** The
  Dockerfile fails if any pin drifts, if the baked source does not hash to the
  committed bundle digest, or if the image cannot reproduce the frozen
  `protocol_sha256` with its 300-item selection. A green build *is* the
  evidence, so there is no separate document a reader has to trust.
- **The tag and manifest are locked against write and delete.** The run launcher
  refuses to start against an unlocked image. The consequence is accepted
  deliberately: this image can never be cleaned up. An image whose bytes could
  still change cannot be the provenance of a scientific result, and an image
  that can be deleted cannot be re-examined by anyone checking the result later.
- **Near-miss, recorded because it looked like an integrity failure.** The first
  protocol check reported `ef782fea…` against the frozen `25e96401…`. The frozen
  hash covers the snapshot *including* the derived selection and strict-budget
  check; the bare `protocol_snapshot()` is a smaller document. Reproducing the
  full document returned `25e96401…` exactly, so nothing had drifted. A recorded
  hash that only reproduces under undocumented arguments is indistinguishable
  from a drifted one, so both facts are now pinned by tests.

**Still not performed: the generation run.** The image exists and is locked; no
ACA GPU job has been executed from it, no model output exists, and no cell
metric may exist before section 4.3 primary labels.

## D25 — Stopping at a prospective gate that we could have quietly passed

2026-08-03. Phase 1.0D semantic-review provider qualification.

The section 4.3 primary semantic labels have blocked Phase 1.0D since the
protocol was frozen. The authorised way to unblock them was to register a
reviewer panel *before* seeing any target output, prove it can run, and prove it
reproduces committed labels on synthetic fixtures. We did all three. The third
one failed by one call out of eighteen.

- **The gate was made hard to pass before it was run, not after.** The six
  fixtures and their expected labels were committed, hashed, baked into the
  image, and verified inside the image before a single reviewer call was made.
  The addendum's `on_label_mismatch` rule was written in the same frozen bytes.
  The value of a prospective gate is entirely in what it forbids once it fires;
  a gate that can be renegotiated after seeing its output is not evidence of
  anything.
- **The mismatch is a disagreement, not a bug.** Every call authenticated,
  routed, returned well-formed JSON inside the token cap with `finish_reason
  stop`, and 17 of 18 labels matched. The addendum separates transport and
  configuration defects, which we may fix and rerun, from label mismatches,
  which we may not. Had the reviewer 4xx'd, this would be a one-line fix. It
  answered correctly-formed and disagreed, which is the case the rule is for.
- **The specific disagreement is the one worth stopping on.** `smoke_unresolved`
  presents an output that states two different final answers and refuses to
  prefer either. The registered expectation is `unresolved`. The primary
  reviewer called it `incorrect`. That is exactly the judgement the Phase 1.0D
  measurement depends on: a bank whose whole point is separating "the model got
  it wrong" from "the model never committed" cannot be labelled by a reviewer
  that collapses the second into the first. The two other reviewers returned
  `unresolved`, which makes the primary the outlier, and makes a majority vote
  the most tempting and least defensible repair available.
- **Every repair was refused and the refusals are recorded.** We could have
  promoted the secondary to primary, adopted a two-of-three vote, softened the
  rubric's `unresolved` clause, or dropped the fixture. Each is a
  post-hoc change to a frozen instrument made after seeing its output on that
  instrument, and each would have produced 900 labels nobody could trust.
- **The gate cost is disclosed and small.** Two ACA executions, eighteen
  reviewer calls plus three qualification calls, all on synthetic bytes. They
  count towards no scientific total.

**Still not performed: the generation run.** The generation image is built and
locked, the review image is built and locked, both were verified in Azure, and
neither has produced a row of target output. The blocker has moved from "no
registered provider exists" to "a registered provider exists and does not
reproduce a registered label", which is a more informative place to be stopped
and is not progress towards a result.

**2026-08-03 — correction pointer appended to D25, original text preserved
above.** D25's procedural conclusion stands: the frozen mismatch rule fired and
was obeyed, and the round ended without a generation run. Its *causal* reading
does not. D25 says the primary reviewer "collapses the second into the first",
i.e. treats a non-commitment as a wrong answer. The frozen fixture contains two
explicit `Final answer:` surfaces, and the frozen rubric's rule 3 selects the
last one, so `incorrect` is what strict rule-3 execution yields. The fixture and
the ordered rubric conflicted with each other before any provider was called.
See `docs/decisions/phase1_0d_semantic_review_v1_specification_correction.md`
and `L-52`. D25 is not edited, rerun or reinterpreted as a pass.

## D26 — Auditing the instrument instead of the reviewer

2026-08-03. Phase 1.0D semantic-review v1 forensic specification audit.

When a prospective gate fires, there are two candidate defendants: the provider
and the specification. D25 charged the provider. Re-reading the frozen bytes
shows the specification was self-contradictory, so the provider's answer was
compatible with executing it correctly.

- **The rubric's own ordering decides the case.** Rule 3 selects the last
  complete `Final answer:` surface as *the* final commitment. Rule 4 only
  applies "with no rule selecting one". On `smoke_unresolved`, rule 3 selects
  `5`; against the registered `4`, rule 6 yields `incorrect`. The registered
  expectation `unresolved` instead follows prose that appears *after* the last
  surface — a reading rule 3 never authorises.
- **This changes the diagnosis, not the verdict.** The v1 stop was procedurally
  correct and stays terminal. What changes is what we are allowed to say caused
  it: not "the reviewer cannot tell an absent answer from a wrong one", but "the
  instrument told the reviewer two different things and we noticed only after
  it answered".
- **The two-versus-one split is not a vote we get to count.** Secondary and
  third read the trailing prose as controlling. That is a defensible reading of
  a contradictory spec, not evidence they are more accurate. Treating 2:1 as
  ground truth would have converted a specification bug into a fabricated
  reliability finding about the primary.
- **The audit is recorded as an audit, not a result.** It is an
  internal-consistency finding about six synthetic strings. It licenses nothing
  scientific, and it explicitly does not license rerunning the v1 gate.
- **The correction is appended, never substituted.** D25, L-50, EV-0012, the
  gate artifact and the commit history keep their original bytes. A ledger that
  silently rewrites its own past cannot be used to check anything.

The operational lesson is narrow and expensive: a frozen rubric with ordered
rules and a frozen fixture bank are one artifact, and freezing them without a
test that *executes the ordering against every fixture* freezes a bug. The v2
instrument carries exactly that test, written before any v2 provider call.

## D27 — Preserve the generated bank and stop at the registered transport state

2026-08-04. Sole Phase 1.0D semantic-review v2 formal execution.

The v2 instrument qualified and its sole 60-call smoke passed, so the
already-preregistered target generation was licensed and completed. The
resulting 300-item, 900-row source pack passed an independent rebuild and
entered the sole formal-review execution. The primary stage then exhausted its
registered eight byte-identical transport attempts for one call, ending on
HTTP 429.

The decision is to obey the frozen failure mapping exactly:
`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT`.

- **Do not turn an operational failure into a scientific result.** The source
  pack still says `AWAITING_SEMANTIC_REVIEW`; no semantic label, cell metric,
  candidate cell, `HEADROOM_NOT_ESTABLISHED`, or
  `RQ2_PILOT_CANDIDATE_CELLS_FOUND` decision exists.
- **Do not improvise a second measurement.** A rerun, quota workaround,
  concurrency change, model/deployment substitution, role change, rubric
  change, fixture change, target-pack change, or parser restart would be a new
  execution after target output and review failure were known. None is
  authorized.
- **Do not infer missing rows from concurrent logs.** Several primary calls
  could be in flight when one future raised. The exact provider-call and valid
  response counts are not recoverable from the surviving console trace, and no
  partial judgment artifact was sealed. Unknown counts remain unknown.
- **Retain the irreversible evidence.** The generation pack, formal-review
  lock, generation and review Jobs, immutable generation/review images, and
  terminal evidence remain available. The empty result prefix is recorded,
  not filled post hoc.

This decision closes the current execution at an operational blocker while
leaving CL-05 scientifically unchanged: Phase 1.0C remains the only
preliminary headroom evidence.

## D28 — Permit one capacity-gated review-only transport recovery

2026-08-05. Phase 1.0D semantic-review v2 transport recovery.

The controlling authority is
`docs/prompts/phase1_0d_review_only_transport_recovery_prompt.md`, SHA-256
`dc350039f118cb5931dab08fd65e24ed169757c472898b7dbe8d27eb3ce2f92b`.
It preserves the old terminal receipt
`artifacts/phase1-0d-semantic-review-v2-formal/20260804T181247Z/00_terminal_receipt.json`
(SHA-256 `430adc4870130edb58f5c6b6f1e8094db575affc9354a0dffb12b7c9cd58c3cf`)
and its terminal archive (SHA-256
`41694a6b9593756d3cbed3014367887567f5e785840dce86bceb2da41a39c204`).

The decision is narrow:

- Preserve the one completed generation and every v1/v2 protected byte. No
  generation, qualification, smoke, reviewer, request, concurrency, retry,
  parser, or J-lens change is permitted.
- Before inference, require a mechanical capacity-only gate over the three
  registered deployments. The gate uses ARM, Monitor, Blob metadata, and
  offline request reconstruction only; any permitted mutation changes only
  `sku.capacity`, under the current ETag, to the minimum passing allocation.
- A create-only passing capacity certificate may license at most one new
  provider-bearing review-only recovery execution. There is no second recovery
  execution.
- The recovery resubmits every required row uniformly. Because concurrent
  responses from the old failed process were not persisted, an unknown subset
  may be submitted again after an unobserved valid response. This
  unquantifiable prior-response resampling exposure is permanent and is not
  evidence that the old process produced zero valid responses.
- If capacity cannot be proved, stop before inference. If the recovery starts
  but does not seal a complete result, permanently close the Phase 1.0D review
  route without a result; do not reconstruct, retry, or substitute.

## D29 — Stop the review-only recovery at the capacity gate

2026-08-05. Phase 1.0D semantic-review v2 transport recovery.

The canonical capacity certificate for run `20260805T180417Z` evaluated 38
mechanical gates. Thirty-five passed; the three registered deployment floors
failed:

- primary returned 36,000 TPM / 36 RPM against 1,000,000 / 1,000;
- secondary returned 50,000 TPM / 50 RPM against 500,000 / 500;
- third returned 50,000 TPM / 50 RPM against 1,000,000 / 500.

Primary subscription usage was 1,000 / 1,000 and its exact model-capacity
readback was 0, so no permitted capacity allocation can make the full gate
pass. Increasing the other two deployments would not clear that blocker and
would be unnecessary mutation. The decision is therefore to perform no
capacity mutation and end exactly as
`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`.

The certificate and manifest were uploaded create-only and read back
byte-for-byte. Before the stop there were zero provider calls. No recovery Job,
lock, execution, result object, response, judgment, label, metric, candidate,
or scientific decision exists. The provider-bearing recovery allowance is
unspent, and no evidence-ledger row is created.

This is a resumable capacity block, not an automatic retry loop. The same
frozen authority can resume only after an operator independently makes the
required quota available on the same registered deployments. It does not
permit a quota request, alternate deployment, provider or model substitution,
or any change to the target pack, reviewer bytes, concurrency, retry policy,
or request bodies.

## D30 — Freeze the reviewed J-lens S3 validity protocol without execution

2026-08-06. J-lens S3 design-only Stage P.

The controlling authority is
`docs/prompts/phase_s3_jlens_validity_protocol_design_prompt.md`, committed
before implementation at `a98928817ce738d4e2af3365c099ed8fa6ab09e8` with
SHA-256
`5d39859bc3d75143f3fdcb469de1d199ad7f831d474509b605569cdc9c1814b8`.
The decision is to freeze the prospective protocol at canonical JSON SHA-256
`bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625`
and validator source-bundle SHA-256
`7e837b0cfdb0c9a12eb1b6c9067751c7cd4262cc18c5a6f17f4a6505f25b7410`.

The single bounded methods review targeted candidate commit
`36b54824a6c916e8d7738c6a9f65c54c314a4e20`. It returned 0 FATAL,
2 MATERIAL, and 0 MINOR findings: public readout/causal rows needed an explicit
distribution-qualified identity, and the named final-answer-synonym gate was
not mechanically reconstructible. The one permitted consolidated correction
at `3954e6e0089271e835de152e4c7e3e9591bb8491` fixed both. Same-checklist
verification returned 0 FATAL / 0 MATERIAL / 0 MINOR and no direct
contradiction. The S3 review allowance is spent; no second review or correction
cycle is authorized.

The freeze registers exact official benchmark bytes, 93 multihop, 55
order-operations, 90 causal-swap items, and the model-free 29 oriented / 24
unique unordered counterpart facts. It also fixes model/lens identities,
eligibility, leakage filtering, deterministic splits, layer bands, readout and
causal metrics, controls, bootstrap, patching support, all-or-nothing output
schemas, and the classification truth table.

No target model, tokenizer, or real lens was loaded, fitted, applied, inspected,
or compared. No inference, activation operation, coordinate swap, ablation,
patching, GPU Job, scientific result row, or RQ2 run occurred. Therefore no
J-lens validity classification exists, no row is added to
`paper/evidence_ledger.csv`, CL-02 and CL-07 remain unsupported, and CL-05 is
unchanged. Phase 1.0D independently remains
`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`.

The exact freeze record is
`docs/decisions/jlens_s3_validity_protocol_freeze.md`. The resulting state is
`NONTERMINAL_CHECKPOINT_JLENS_S3_VALIDITY_PROTOCOL_FROZEN_AWAITING_S2_LENSES_AND_EXECUTION`.
It licenses no S3 or RQ2 execution.

## D31 - Accept the independently verified full-layer S2 identities

2026-08-07. Full-layer J-lens S2 execution.

The deterministic S2 run produced exact lossless A600, B600, and official
600:600 weighted M1200 identities. Independent verification confirmed all
source layers 0--26 against target 27, float32 1536 by 1536 finite matrices,
prompt counts 600/600/1200, exact save/load identity, exact official-merge
recomputation, create-only Blob readback, complete transport provenance, and
the closed artifact schema.

The canonical lens hashes are:

- A600 `28e066960f03f51eaefb0e29aeb9cfe266e353746660f3283caaed85d0bc7689`;
- B600 `f39a656a018f99b0b0bacff97fe0eb7fe18285aa0049f1ca0f477232400272d3`;
- M1200 `9938aa66e07ca8bc2f63463dc2dfe60cb512271fa7b19955b402cb581bb0e682`.

The S2 manifest SHA-256 is
`9d10a4b07a8133b7241ce9067649ebf1de48429cf7c04e0495b4c3fe90e58e47`;
the verification receipt SHA-256 is
`b1a909cd04c991fd69932af5bfbf6427343851f87a1a00c537ac42c7d9d02a5f`.
Before the seal there were zero official benchmark tokenizer operations and
zero official benchmark model operations.

The A/B maximum relative Frobenius distance decreased across the registered
checkpoints and the heldout key space was complete, but those results are
non-gating engineering diagnostics. They do not validate a lens or establish
hidden reasoning, an internal workspace, or a J-space. The decision is solely
to accept the three byte identities as the frozen S3 E0 prerequisites. The
state becomes
`NONTERMINAL_CHECKPOINT_JLENS_S2_SEALED_AWAITING_S3_E0`.

## D32 - Close the frozen S3 E0 on insufficient behavioral support

2026-08-07. Frozen J-lens S3 Stage E0.

After independent lock readback, the sole formal E0 execution
`job-js-e0-run-081017-yi5acvy` processed all 238 official items exactly once.
It issued 238 item tokenizer calls and 238 clean next-token model forwards,
loaded or applied no lens, and produced no E1/E2 output.

Mechanical eligibility was 79 of 93 multihop, 36 of 55 order-operations, and
83 of 90 causal-swap items. Clean-behavior eligibility was 2, 2, and 5. The
frozen distribution-local split assigns the first 15 eligible items to
development; therefore all nine eligible items became development and
confirmation counts were zero for all three distributions. The pooled readout
confirmation count was also zero. All four registered floor booleans are
false.

The complete create-only pack was sealed manifest-last and independently
reconstructed. Its artifact-manifest SHA-256 is
`6d11b09b39bbeead9b38fdb23be47a4247245fb55e6b6b665b817241519df60f`.
There is no partial object, no missing row, and no operational blocker.

The exact primary terminal state is therefore:

`INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`

This floor failure is terminal under the current authority. No backfill,
replacement batch, prompt change, surface growth, threshold change, or second
E0 is authorized. It is not a J-lens validity classification: E0 contains no
lens output and establishes neither hidden reasoning nor an internal workspace
or J-space. E1/E2 and RQ2 remain unauthorized, and Phase 1.0D independently
remains `BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`.

## D33 - Close the original program as Study 1 and open independent Study 2

2026-08-07. Cross-study boundary decision.

The repository state at
`6409d2c6d665187e4459d94d490a20d7b085e8af`, tree
`bc8b80cb0e66f9426dcdedd52b624c892caa3fc9`, is designated the terminal
scientific baseline of **Study 1**. Its exact terminal state remains
`INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`; Phase 1.0D separately remains
`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`. Neither state is relabelled,
merged, or repaired by this decision.

Study 1 did not answer the original research question. Its terminal E0 tested
whether frozen official public items supplied enough clean-correct greedy
next-token cases under raw completion bytes, no chat template, and no generated
chain-of-thought. It stopped before any lens output or causal intervention.
That valid prospective floor failure is evidence about the selected behavioral
interface, not evidence for or against hidden reasoning, an internal workspace,
a J-space, or distillation-transferred reasoning.

Historical files remain at their existing paths. New files under
`studies/study1/` form an index and machine-readable closure layer only. They
do not move or replace receipts, artifacts, ledgers, decisions, protected-byte
manifests, or the final Study 1 handoff.

**Study 2** is opened as an independent prospective study with new namespaces,
task banks, authority, controls, and terminal states. It asks whether the
R1-distilled checkpoint computes and causally uses a task-defined intermediate
variable in one forward pass with zero generated reasoning tokens, and whether
that behavior or mechanism is stronger than both its lineage base and a
same-family instruction-tuned control.

Only Study 2 Stage P is authorized next: model-free protocol design,
deterministic public task-bank construction, one bounded methods review, at
most one consolidated correction, freeze, validation, ledgers, and handoff.
Stage T and all model, lens, activation, probe, patching, ablation, reviewer,
GPU, and scientific operations remain unauthorized. No Study 2 evidence row is
created by this organizational transition. The resulting state is
`NONTERMINAL_CHECKPOINT_STUDY2_OPENED_AWAITING_STAGE_P`.

## D35 - Adopt a disposable two-family development feasibility gate

2026-08-07. Study 2 Stage P operator amendment.

The operator selected Gate A after a pre-review gap analysis showed that the
original B-D stage could verify implementation but could not discard an
empirically unsuitable interface before confirmation. The original 53,018-byte
Stage P authority remains unchanged. The additive authority at
`studies/study2/prompts/stage_p_gate_a_operator_amendment.md` fixes one narrow
change: after Stage T and B-D implementation validation, before any B-C object
is opened, target NT development accuracy must pass an exact binomial gate in
both task families.

Each family pools its fixed 64 depth-2 and 64 depth-3 rows. Forty-three or more
of 128 restricted-option-correct rows pass the exact one-sided alpha .025
boundary; 42 does not. All three models still run the same development rows,
but control outcomes cannot decide the gate. A failure closes protocol v1 and
requires a new version, authority, and seeds. It cannot trigger same-version
backfill, replacement tasks, pooling rescue, or threshold change. Gate A is
operational protocol qualification, not scientific evidence.

## D36 - Freeze the reviewed Study 2 Stage P protocol and banks

2026-08-07. Study 2 Stage P freeze.

The single 15-item methods review found no FATAL or MATERIAL issue and recorded
two accepted MINOR limitations: Gate A protocol-selection bias and unidentified
joint power across conjunctive gates. No consolidated correction or second
review was used.

The canonical protocol is frozen as `FROZEN_AWAITING_STAGE_T`, the task-bank
manifest as `FROZEN_MODEL_FREE_BANKS`, and the review allowance as
`SPENT_VERIFIED`. Final ACR runs `cmcc`, `cmcd`, and `cmce` respectively passed
41 focused tests, the 3,537 / 15 / 2 full-suite envelope, and the complete
frozen validator. EV-0016 remains the evidence tail, all Study 2 claims remain
unsupported/preregistered, and Stage T is not authorized. The exact state is
`NONTERMINAL_CHECKPOINT_STUDY2_PROTOCOL_FROZEN_AWAITING_TOKENIZER_GATE_AND_EXECUTION`.

## D34 - Seal the Study 2 bootstrap authority and new-thread handoff

2026-08-07. Study 2 bootstrap handoff.

The organizational and authority transition was fast-forward committed as
`db8c100db0c16306a702d348a49a90480f440629`, tree
`032109e20e32f43126ade0d45c0abffa5c2de85f`, with the Study 1 terminal commit
as its parent. The Stage P authority prompt at
`studies/study2/prompts/stage_p_protocol_design_prompt.md` is 53,018 bytes,
1,124 lines, and SHA-256
`1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37`.

A machine-readable handoff receipt binds that authority commit/tree, prompt,
charters, Study 1 terminal identity, protected anchors, ledger tails, unspent
review allowance, and zero-operation counters. Because a receipt cannot embed
the SHA of the commit that contains itself, the operator's final handoff message
supplies the exact current `origin/main` commit/tree; the new thread must require
that exact head and verify the authority commit as its ancestor.

This handoff authorizes no new operation beyond D33. Stage P remains unexecuted,
its review allowance remains unspent, `paper/evidence_ledger.csv` remains at
EV-0016, and the state remains
`NONTERMINAL_CHECKPOINT_STUDY2_OPENED_AWAITING_STAGE_P`.


2026-08-08. Study 2 Stage T tokenizer gate sealed.

Stage T is closed and published. The gate passes cleanly: every one of the
17,408 frozen prompt rows tokenizes successfully under all three registered
checkpoints, all four option continuations are single tokens, all 2,048
mechanistic pairs are jointly eligible, and all eight selection cells filled to
128 for 1,024 selected pairs with no shortfall. See
`docs/decisions/study2_stage_t_tokenizer_gate.md`.

The substantive finding exceeds the requirement. Stage T needed exact pair
length and answer-position alignment across models; what it found is identical
token IDs on all 17,408 rows for all three checkpoints, so later mechanistic
comparisons operate on the same token sequences rather than merely
commensurable ones. The three tokenizers remain distinct artifacts by
`model_id`, resolved revision, config bytes, and special-token inventory, which
was verified directly because identical output is also what a reused-tokenizer
bug would produce.

Two corrections were made during execution and both are recorded as seal
revisions in `studies/study2/STAGE_T_AUTHORITY_RECEIPT.md`. The first replaced a
passive weight-path import assertion, which transformers 5.x makes unsound by
resolving its auto-class registry eagerly, with an active interlock that makes a
weight load raise; it was issued before any measurement existed. The second
admitted `rows: null` for single-document artifacts after the validator rejected
an otherwise complete pack. Because that second revision followed an observed
outcome, the thirteen artifact hashes from the pre-fix run were pre-registered
as a falsifiable prediction before re-running, and all thirteen reproduced
exactly. An incorrect argument in an earlier draft of the receipt, which
inferred tokenizer distinctness from differing file sizes that in fact differ
only by a role label, was measured, refuted, and corrected in place rather than
dropped.

Stage T authorizes nothing further. No model weight was downloaded or loaded, no
forward pass, generation, activation, probe, patch, ablation, or lens operation
occurred, `paper/evidence_ledger.csv` remains at EV-0016, both protected Phase
1.0D rollups are unchanged, and the state is
`NONTERMINAL_CHECKPOINT_STUDY2_STAGE_T_TOKENIZER_GATE_SEALED_AWAITING_BD_AUTHORITY`.


## Study 2 Stage B-D — development execution and Gate A

Stage B-D implemented the frozen behavioral computation, loaded the three
registered 1.5B checkpoints exactly, ran the complete 384-item development bank
under every applicable arm on an Azure T4, and evaluated the pre-registered
Gate A feasibility rule. The terminal state is
`STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`.

### The decision and why it was not a judgment call

Gate A was frozen before any Stage B-D measurement existed: target model only,
no-tool arm only, depths 2+3 pooled within family for n = 128, pass a family only
when X ≥ 43 restricted-option-correct rows, and pass overall only when both
families pass. The target scored 25/128 on `permutation_chain` (exact upper tail
0.9403523926144965) and 33/128 on `affine_mod10` (0.4526854444021635) against a
chance rate of 32/128. Reaching the threshold would have required 18 and 10 more
correct rows. `overall_gate_pass = false`.

`lineage_base` cleared the `affine_mod10` threshold at 44/128. The frozen rule
gives controls no authority precisely for this case, and one passing cell out of
six computed comparisons is unremarkable. `controls_affect_decision` is recorded
as `false`, and no control substitution was performed.

The failure is uniform rather than localized: all 24 model × family × arm
aggregates lie between 0.188 and 0.318 against a chance rate of 0.25, every one
of the 96 summary cells is finite and complete, and the target's 95% Wilson
intervals all contain 0.25. The restricted surface is a four-way choice among
fixed option tokens, so an interface producing no signal lands at 0.25, which is
what all three models did.

### Why the numbers are trustworthy

A pre-inference seal was generated in Azure, published to `main`, and only then
used. It pre-registers the 3,072-row space, its primary-key digest, the
shard-manifest digest, the option token IDs A=362 B=425 C=356 D=422, twenty
frozen input hashes, and the byte identity of the core module. The GPU job
verified it against the published copy before importing `torch`. The shard
manifest digest the GPU job reported equals the sealed value, and every prompt
was re-tokenized at inference time and checked against the Stage T sealed token
identity, so the transformers 4.46.3 runtime provably saw the same token
sequences Stage T sealed under a different transformers major version.

The seal reproduced byte-identically three times across two image digests, and
two finalization runs on two different image digests reproduced all eleven
artifact digests identically.

### Order of operations

The seal was created and published before the run, and the aggregation and Gate A
decision were computed by a model-free finalizer and then certified by an
independent validator that shares no writing code path. Gate A was therefore
never in a position to be chosen after seeing a preferred outcome.

### A defect that was disclosed rather than repaired

The core manifest's `expected_primary_keys_sha256`
(`d15cc1bd…`) is computed over lexicographically sorted keys, while the seal's
identically named field (`7b3e6c53…`) is computed over `expected_row_keys()`
generation order, which is not sorted. Both digest the same 3,072-key set;
nothing verifies the manifest field. The substantive property is proven
independently by the validator, which asserts set equality and primary-key
uniqueness and fails closed before any recomputation.

It was left uncorrected deliberately. The core module's bytes are bound by a seal
published before any weight load; rewriting them after seeing the result would
destroy the property that makes the seal worth having. The correct place to fix
the field name is a future protocol version.

### Boundary

No confirmation object was opened; all six registered confirmation paths were
physically absent from the execution image. Generations, activation operations,
probes, patching, ablations, lens operations, provider calls, Phase 1.0D
operations, RQ2/S4 operations, mechanistic operations and scientific evidence
rows are all zero. `paper/evidence_ledger.csv` remains byte-identical at EV-0016
and both protected Phase 1.0D rollups are unchanged.

Gate A failure is the registered non-scientific closure of protocol v1, not
evidence about internal reasoning, distillation, or J-space. Stage B-C,
mechanistic-cell selection, M-D and M-C were never opened and may not be opened
under this protocol version. Any further attempt requires a new protocol version,
a new operator authority, and new task-bank seeds.

## D37 - Terminalize Study 2 protocol v1 as documentation without touching the measurement

Study 2 protocol v1 was already scientifically closed at commit
`43411e09de425dfae0ee74ba46c68a389311e9a7`, but the repository's routers still
told a reader that Study 2 was awaiting Stage P or Stage B-D authority, and the
frozen Gate A documents asserted without qualification that the outcome "is not a
measurement artifact". Both defects were about how the closed result is presented,
not about the result. The decision was to fix them as documentation, under a
separate endpoint `STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE`, and to
leave the scientific terminal state
`STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY` exactly as sealed.

The alternative would have been to reopen or restate the science: to rerun the
gate, to repair the interface and try again, or to promote the one control cell
that cleared a family threshold. Each is prohibited by the frozen rule, and each
would convert a pre-registered feasibility failure into a post-hoc rescue. The
separation of a documentation state from the scientific state exists precisely so
that improving the explanation cannot quietly improve the claim.

Three boundaries were held. First, no frozen artifact was edited: the Gate A
decision document, the Stage B-D handoff, the protocol, banks, schema, thresholds,
seeds and model registrations keep their registered bytes and hashes, and the
erratum narrows their interpretation without altering a byte. Second, no scientific
operation was performed: this round added zero model downloads, weight loads,
tokenizer constructions, forward passes, generations, activations, probes, patches,
ablations, lens operations, provider calls and evidence rows, and
`paper/evidence_ledger.csv` still ends at `EV-0016`. Third, the one computation
performed - a read-only re-aggregation of already-committed development rows - was
labeled `POST_HOC_DESCRIPTIVE_ZERO_AUTHORITY_NOT_SCIENTIFIC_EVIDENCE` and recorded
as a limitation (L-89), never as a finding.

The substantive interpretive change is narrow and deliberately unsatisfying: the
Gate A failure is not an artifact of execution or bookkeeping integrity, but the
study cannot distinguish an incapable checkpoint from an inadequate interface,
because protocol v1 never measured interface adequacy or label binding. Naming that
gap is not the same as filling it. Interface calibration, a label-binding study,
protocol v2 design, Stage B-C and every mechanistic stage remain unauthorized, and
this terminalization grants no execution authority of any kind.

The charter, the machine-readable charter and the bootstrap handoff receipt were
deliberately left unedited and are labeled historical records rather than current
state, so that the opening record of the study stays legible next to its closure.


## D38 - Open Study 3 as an interface-adequacy and label-binding calibration design draft, and correct a Study 2 terminal changed-path count

**Date:** 2026-08-08
**Status:** Design draft awaiting operator review. Not frozen. Not authorized to execute.

Study 1 closed at `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` and Study 2 closed
at `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`. Both terminated on
tooling-adjacent grounds rather than on an answered scientific question, and in both
cases the record could not separate an incapable checkpoint from an inadequate
measurement interface, because neither protocol ever measured whether its own
response and scoring interface could recover competence that was independently known
to be present. D38 opens a third, isolated study whose object of measurement is that
interface itself.

The registered Study 3 question is whether a pre-specified response and scoring
interface can recover deliberately trivial and primitive task competence robustly
across answer-label permutations, option positions and prompt renderings, at a
pre-registered adequacy level, on the same three checkpoints Study 2 registered.
Study 3 explicitly does not ask whether any checkpoint reasons, whether an internal
state is causal, whether Study 2's Gate A outcome was correct, or whether any
interface is "the right one" in general. A negative Study 3 outcome would license no
claim about model capability, and a positive outcome would license no claim about
reasoning; the design carries an explicit claim ceiling to that effect.

Four candidate interface surfaces are carried forward without a winner: `S1`
label-token logits, retained solely as the Study 2 legacy comparator; `S2`
answer-content logits; `S3` content-conditional log-likelihood; and `S4` bounded
minimal generation, admissible only as a calibration reference. Selection among them
is deferred to a later, separately authorized round, and a deterministic tie-break
order (`S1 < S2 < S3 < S4`) is registered now so that the choice cannot be made after
seeing outcomes. Six fail-closed gates `I0`-`I5` are registered, none of which
authorizes mechanistic execution; the highest gate that can be reached still leaves
Gate A, Stage B-C, weight loading, forward passes, generation, activation
extraction, probing, patching, ablation and every lens operation unauthorized.

The central methodological commitment is a mandatory non-model oracle role (`R0`)
plus an explicit-binding condition (`RC`), so that an interface failure can be
distinguished from a task-construction failure before any checkpoint is consulted.
The design also registers a positive-capability reference role (`RP`) but leaves it
`UNSELECTED`, because choosing it is a scientific decision reserved to the operator;
gate `I4` is blocked until that decision is made. Eight operator decisions `OD1`-`OD8`
are recorded as open, three of them blocking.

This round performed zero scientific operations. No model was downloaded or loaded,
no tokenizer was constructed, no forward pass, generation, activation extraction,
probe, patch, ablation, lens operation, GPU job or provider call occurred, no seed
was drawn, no task-bank row was written, no interface was selected, and no evidence
row was created; `paper/evidence_ledger.csv` still ends at `EV-0016`. All statistical
quantities in the draft - exact binomial acceptance thresholds, power values,
Clopper-Pearson bounds and label-uniformity bands - were derived by model-free
arithmetic and are design parameters, not measurements. Both protected Phase 1.0D
rollups and every Study 2 terminal artifact retain their registered bytes.

Separately and first, in its own single-path commit, this round corrected a clerical
error in the Study 2 terminalization run-log entry, which described its own change
set as fourteen paths with ten modified when the commit in fact touched fifteen paths
with eleven modified, having omitted `docs/decision_log.md` from its own list. The
correction is bookkeeping only under substate
`STUDY2_TERMINAL_CHANGED_PATH_BOOKKEEPING_CORRECTED`: no Study 2 scientific content,
threshold, count, seal, hash or conclusion changed, and the Gate A outcome and the
Study 2 terminal state are untouched.

The only legal next action for Study 3 is operator review of the draft and of the
eight open decisions. Approval of this design would not itself authorize execution.

## D39 - Amend the Study 3 design to draft-v0.2 after an operator review found ten defects and refused freeze

**Date.** 2026-08-08

**Context.** Study 3 draft-v0.1 was published under D38 as a reviewable design
draft. The operator reviewed it and returned
`STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`, listing
ten design defects and explicitly declining freeze. A single design-amendment
round was authorised to produce draft-v0.2.

**Decision.** Amend the design rather than defend it, and record the review
additively rather than by rewriting history.

1. **The JSON protocol document is authoritative; the Markdown is a companion
   rendering of it.** draft-v0.1 claimed both were generated from one source of
   record. No such generator was committed, so the claim was unsupported. It is
   removed and replaced by a statement that the agreement itself is what is
   committed and checked.
2. **Design-critical checks are committed, not ephemeral.** The statistical
   derivation is now `studies/study3/analysis/design_statistics.py` with a
   `--check` mode, and the design invariants are now `tests/test_study3_design.py`
   with a negative-mutation battery. In the v0.1 round the equivalent checker was
   an ephemeral script that was never committed, and it missed a defect that a
   human reader found immediately. That process failure is recorded as a defect in
   its own right.
3. **`candidate_interfaces` becomes `interface_profiles`** with an explicit
   pre-registered `selectable_status`, an applicability map, and a declared list
   of transformations that have no referent for that profile.
4. **The data-dependent selection rule is replaced by a published
   `admissibility_order`** fixed in advance, and the draft states plainly that no
   interface is selected in this round. draft-v0.1 contained a direct
   label/value contradiction on exactly this point.
5. **`not_applicable` becomes a real third value** that is neither a pass nor a
   zero effect and may never be averaged into a rate.
6. **The fused `I1` is split into `I1a` and `I1b`**, so a symbol-binding failure
   can no longer be mistaken for a content-recovery failure.
7. **`I4` becomes part of eligibility and fails per interface profile**, not as a
   global study stop, and `I5` is extended to cover every gate-bearing construct
   including `I4`.
8. **The chance-level `I4` null is rejected** and replaced by a competence floor.
   A reference that merely beats chance is not a positive control.

**The finding that made this more than editorial.** The committed derivation
contradicts draft-v0.1's own assertion. At `n = 192` and a target power of 0.90,
the aggregate paired-equivalence margin of 0.05 that draft-v0.1 asserted is
supported at no tested discordance rate, and a 0.10 margin is supported only at
discordance 0.05 and 0.10. The aggregate criterion was therefore demoted to
secondary and an exact per-base-item consistency criterion was made primary.
`OD6` was left blocking rather than resolved by widening the margin until it fit
the sample size, which would have been the drafting party marking its own work.

Separately, exact enumeration shows that the named asymptotic paired method has
one configuration with a realised one-sided level of 0.025501 against a nominal
0.025. This is disclosed in the review packet and put to the reviewer rather than
absorbed.

**Alternatives considered and rejected.**

- *Defend draft-v0.1 and freeze it.* Rejected: two of the ten defects were
  outright contradictions in the document, and one was an unsupported provenance
  claim. There was nothing to defend.
- *Rewrite the draft-v0.1 artifacts in place so the defects disappear.* Rejected:
  the v0.1 receipt and the v0.1 authority are historical records. The review is
  recorded additively in `studies/study3/reviews/v0_1_operator_review.md` and
  `studies/study3/design_receipt.json` was left untouched.
- *Record the ten defects as limitations in `paper/limitations_ledger.md`.*
  Rejected: this repository reserves `L-` rows for limitations of executed
  measurement. These are defects in an unfrozen design document, and filing them
  as limitations would misrepresent a drafting error as a finding about the world.
- *Resolve `OD5` and `OD6` using the newly derived numbers.* Rejected: the
  numbers make the decisions answerable, but the drafting party is not the party
  entitled to answer them.

**Consequences.** Study 3 moves to
`STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW`.
Four of the eight open decisions are resolved and part of a fifth; `OD2`, `OD5`
and `OD6` remain blocking. All 22 operation counters remain zero. No Study 1 or
Study 2 file was modified, no evidence row was added, and both protected Phase
1.0D rollups are unchanged. The only legal next action is a bounded independent
methods review; no freeze prompt and no execution prompt exist.

## D40 - Return `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` on Study 3 draft-v0.2 after an independent re-derivation of its statistics

**Date.** 2026-08-08

**Context.** D39 published Study 3 draft-v0.2 and left the only legal next action
as a bounded independent methods review. That review was carried out in a fresh
session and a fresh worktree by a party that did not write the design. Its
mandate was to audit, not to repair, and to earn one of exactly three permitted
dispositions rather than to be handed one.

The review was required to be independent in a specific, checkable sense: it had
to re-derive every design statistic from the cited primary sources - Tango (1998)
*Statistics in Medicine* 17:891-908, Hsueh, Liu and Chen (2001) *Biometrics*
57:478-483, and Berger and Hsu (1996) *Statistical Science* - in a separately
structured implementation that never imports, executes, copies from, or
dynamically loads `studies/study3/analysis/design_statistics.py`. Agreement with
the drafting implementation was explicitly disallowed as evidence of
correctness, so each statistical family also had to pass at least one closed-form
or published-example check that does not involve the drafting code at all.

**Decision.** Reject draft-v0.2 and require an amendment round. Six blocking
findings were confirmed; none of them can be closed by supplying a value the
draft omitted, and at least one of them changes the core design.

1. **The `I3` primary estimand is not identifiable from the published
   construction.** `I3` is defined over the set of variants of a base item, but
   `counterbalancing_design.construction_algorithm` assigns exactly one
   `(position, symbol)` pair to each base item by the deterministic rule
   `(p, s) = (k mod 4, (k div 4) mod 4)`. No committed field states how many
   variants a base item actually has for any profile, so the denominator of the
   primary indicator does not exist in the document. Every `I3` threshold, its
   sample size, and its share of the projected work inherit that hole.
2. **The `I3` primary indicator has two incompatible published definitions.**
   The authoritative JSON scores identical-answer-across-variants; the review
   packet scores all-variants-correct. These are different estimands, and a
   stably wrong answer passes one and fails the other. The packet is the outlier,
   but the round cannot decide which definition is intended.
3. **The Family B per-profile level is asserted but not implemented.** The
   design states a per-profile alpha of `0.001666666667` while every retained
   component rule is computed at `alpha = 0.005`. The independent recalculation
   shows the union bound over three selectable profiles at the implemented level
   is `0.015`, three times the stated guarantee. Either the components must be
   recomputed at the stated level - which moves thresholds and sample sizes - or
   the stated level must be withdrawn.
4. **The conservativeness claim in the authoritative JSON is false as written.**
   The gate-hierarchy text says exact enumeration does not exceed the nominal
   one-sided level. The packet and the methods ledger disclose a realised
   `0.025501` against a nominal `0.025`. The independent enumeration reproduces
   `0.025501092` at `n = 192`, `margin = 0.10`. **The drafting enumeration is
   correct; the defect is entirely in the claim made about it.**
5. **The four-value discordance grid is a sensitivity grid, not proof of size
   control.** A finite grid bounds a supremum only from below. Maximising over
   the full feasible null boundary finds a configuration the drafting grid never
   evaluates: at `n = 384`, `margin = 0.10`, the four grid rows peak at `0.024727`
   and look compliant, while the true supremum is `0.025073` at a discordance of
   about `0.478`. Size control was asserted from evidence that cannot establish
   it.
6. **The `I3` floor is unresolved and, at the stated floor, unreachable.** At
   `p0 = 0.95`, `p1 = 0.97`, `alpha = 0.005/3` and target power `0.90`, no
   admissible sample size up to the design maximum of 768 attains the target.

**Alternatives considered and rejected.**

- *`STUDY3_METHODS_REVIEW_ACCEPTED_AS_SPECIFIED`.* Rejected. The controlling
  authority forbids acceptance while anything is unresolved and forbids
  acceptance obtained by having the reviewer supply values the draft omitted.
  The review supplies a full reviewed-parameter set precisely because the draft
  does not contain one, which is a reason to reject rather than to accept.
- *`STUDY3_METHODS_REVIEW_ACCEPTED_WITH_REQUIRED_CHANGES`.* Rejected. That
  disposition is available only when the required changes are local. Repairing
  `I3` forces re-specification of the atomic evaluation cell, the unit in which
  `n` is counted, the projected operation total, and every `I3` threshold. That
  is inventing structure the document does not contain, which the reviewer is
  not entitled to do.
- *Repairing the design in place.* Rejected on the same ground that D39 refused
  to defend draft-v0.1: the reviewing party is not the drafting party, and a
  reviewer who fixes the object no longer has an object to review. Where the
  committed design test itself encodes a defect - it verifies the drafting
  tables against the drafting script, which is circular - the defect was
  recorded as finding S3MR-009 and `tests/test_study3_design.py` was left
  untouched.
- *Resolving `OD2`, `OD5` or `OD6`.* Rejected. `OD2` is reserved to the
  operator and no checkpoint was named, pinned, downloaded, tokenized, loaded,
  run, prequalified or substituted. `OD5` and `OD6` received explicit methods
  recommendations, which this round does not adopt.

**Consequences.** Study 3 moves to
`STUDY3_DRAFT_V0_2_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`.
The next legal action is `OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_3`. Nothing is
frozen, nothing is authorized for execution, no interface is selected, no
positive reference is selected, no bank row or seed exists, and all 22 operation
counters remain zero. No Study 1 or Study 2 path was touched, `paper/evidence_ledger.csv`
is unchanged at `EV-0016`, and both protected Phase 1.0D rollups are unchanged.
The review is recorded additively: no protocol, packet, drafting statistic,
dossier, prior review, receipt, or prior authority was modified.


## D41 - Amend Study 3 to draft-v0.3 in response to the independent methods review, and publish it for a second independent methods review rather than declaring it correct

**Date.** 2026-08-08

**Context.** D40 rejected draft-v0.2 with six confirmed blocking findings and
required an operator amendment round. The drafting party that wrote draft-v0.2
had found its own design defensible; an independent reviewer then found six
defects that no supplied value could close. That is the fact this round is built
around. An amendment written by the party that must be amended is not evidence
that the amendment is correct, so the endpoint of this round is deliberately not
"the protocol is now sound". It is "the protocol has been repaired as the
authority directs, and the repairs are proposed resolved subject to a second
independent methods review".

**Decision.** Adopt the operator decisions below, rewrite the affected design,
and publish the result as an unfrozen draft-v0.3 whose only legal next action is
a second independent methods review by a party that did not write it.

1. **The `I3` estimand is redefined as a pre-registered pairwise contrast over
   base-item contrast clusters.** The independent unit is the
   `base_item_contrast_cluster` and every registered cluster carries exactly two
   variants. This is the direct repair of S3MR-001: draft-v0.2 defined `I3` over
   "the set of variants of a base item" while its construction algorithm
   assigned exactly one `(position, symbol)` pair per base item, so the
   denominator of the primary indicator did not exist in the document. It is
   also the repair of the multiplication defect: there is no cross product, `K5`
   and `K6` are not crossed, they draw on disjoint base-item identities, and no
   32 x 3 or 96-variant factorial expansion survives anywhere in the active
   protocol.

2. **`K5` is exactly seven one-factor contrasts and `K6` is exactly two.**
   `K5-P1`, `K5-P2` and `K5-P3` offset the content position by `+1`, `+2` and
   `+3` modulo 4. `K5-S1`, `K5-S2` and `K5-S3` offset the index of the correct
   displayed symbol by `+1`, `+2` and `+3` modulo 4. `K5-A1` replaces the label
   alphabet with a second alphabet. Both alphabets are disjoint from each other
   and from the answer domain, and digits are forbidden as labels so that a
   label can never be read as an answer. `K6` is `K6-SEP` and `K6-INSTR`, two
   disjoint pairwise cells drawn from the three renderings `R-base`, `R-sep` and
   `R-instr`, with the answer cue and every other byte held fixed. `K5` is
   `not_applicable` to `S2` and `S3` rather than trivially passing on them,
   because a profile that displays no options and no labels cannot be given a
   position or a label contrast at all. Balancing is deterministic over complete
   blocks with bijective option and label maps. No random draw occurs anywhere
   in this design round. This closes S3MR-010 and S3MR-011, which found that the
   committed `K5` and `K6` text was still the stale draft-v0.1 text.

3. **`I3` carries three named indicators and the primary gate is the
   conjunction.** `J_inv` is invariance of the emitted answer across the two
   variants of a cluster, `J_cor` is correctness on both variants, and
   `J_both = J_inv AND J_cor` is the primary gate indicator. A stable but wrong
   answer scores zero. A stable but invalid or unparseable answer scores zero.
   draft-v0.2 carried two mutually exclusive `I3` indicators and never said
   which one the gate used, which is S3MR-002 and S3MR-007. Under a unique
   ground truth `J_cor` implies `J_inv`; that is recorded as an expected
   integrity invariant of the scoring code rather than concealed behind a claim
   that the two indicators are independent.

4. **`OD5` is resolved as an exact-binomial primary design with exact rational
   levels.** Study-level development screening uses `1/200`, each per-profile
   development component uses `1/600`, and the components within a profile are
   combined as an intersection-union conjunction, so no further within-profile
   Bonferroni correction is applied or implied. The selectable-profile
   denominator is fixed at `K = 3` before any data exists and never shrinks,
   which is the repair of S3MR-016: draft-v0.2 made the Family B denominator
   contingent on a post-data fact. Decimal fields are renderings of the exact
   rational policy and are never the source of truth, which is the repair of
   S3MR-003.

5. **The paired aggregate-equivalence procedure is retired from every decision
   role.** It carries no gate, no eligibility role, no selection role, no
   confirmation role, no claim language, no equivalence margin, no critical
   value, no discordance grid and no conservativeness role. The four-point
   discordance grid is removed from active verification. Paired summaries
   survive only as descriptive quantities with no null, no alpha, no p-value, no
   pass or fail, no rescue path and no ranking weight. This is the response to
   S3MR-004, S3MR-005 and S3MR-009. The reviewer's own recalculation of the
   procedure is preserved unchanged as immutable historical evidence, and the
   second reviewer is asked explicitly to adjudicate whether retirement fully
   removes the size-control defect rather than merely moving it.

6. **`OD6` is resolved as one `I3` floor only.** `p0 = 0.90`, `p1 = 0.97`, power
   at least `0.90`, and `n = 256` clusters per applicable contrast cell. The
   second floor `p0 = 0.95` is deleted from every active protocol field, table
   and packet field and is permitted only inside clearly labelled historical
   narrative. This closes S3MR-006. No active rejection region has a pass count
   equal to `n`, because a region that requires every trial to succeed has no
   power against any alternative below one and is not a hypothesis test; that is
   S3MR-015.

7. **Every symbol `n` carries a unit at its definition and in every table.** One
   `n` is never reused across base items, contrast clusters, rendered rows and
   scored rows. This closes S3MR-014 and is enforced by a committed test rather
   than by prose.

8. **`OD2` remains unresolved and blocking.** No positive-reference checkpoint
   is selected, preferred, pinned, ranked, downloaded, tokenized, loaded or
   prequalified. The dossier retains its candidates and states `UNSELECTED`
   explicitly, and its two back-references to `D-07` are corrected to `D-04`,
   which is S3MR-020.

9. **The Study 3 operation projection is decomposed.** Under the current
   single-token answer domain, Study 3 adds exactly zero forward passes and zero
   sequence-scoring rows beyond Study 2, and the projection is stated as six
   named work streams each carrying its own unit. A single undifferentiated
   total is prohibited. This closes S3MR-012 and S3MR-013.

**What this decision explicitly does not do.** It does not freeze the protocol,
does not authorise execution, does not authorise a bank, does not draw a seed,
does not authorise any model operation, does not select an interface, does not
select a positive reference and does not authorise confirmation access. It does
not declare the repairs correct. Each repair is recorded as
`proposed_resolved_subject_to_independent_review`, and `OD2` is recorded as
`UNRESOLVED_BLOCKING_OPERATOR_DECISION` rather than quietly relabelled.

**Consequences.** The amendment record closes all twenty findings `S3MR-001`
through `S3MR-020` and all twenty-two packet checklist items `UR-01` through
`UR-22` exactly once each with a real disposition. A second independent methods
review packet is published as
`studies/study3/analysis/independent_methods_review_packet_v0_3.md`. The
draft-v0.2 review outputs, its receipt, its recalculation, its authority copy and
the exact packet the first reviewer reviewed are immutable and are unchanged.
The only legal next action is a second independent methods review by a party that
did not write draft-v0.3.

**Alternatives rejected.** Closing the blocking findings by supplying the missing
values was rejected because D40 established that no supplied value closes them.
Keeping the paired procedure as a secondary criterion with a corrected grid was
rejected because a size-control defect that is only made harder to trigger is
still a size-control defect, and because retiring it removes a decision role
rather than adding one. Declaring the amendment sound on the drafting party's own
assessment was rejected as the exact failure mode that produced draft-v0.2.

## D42 - Study 3 draft-v0.3 second independent methods review disposition

**Date:** 2026-08-09 (UTC)
**Decision class:** independent methods review disposition on an unfrozen design draft
**Reviewed commit:** `2b36f5321d830ea6f70fff2b7bbca3cb93394046`
**Reviewed tree:** `98d71cb35cca7b55d8f96f131064a5b9654dd3c7`
**Record:** `studies/study3/reviews/v0_3_independent_methods_review.md`
**Machine-readable:** `studies/study3/reviews/v0_3_independent_methods_review.json`
**Receipt:** `studies/study3/methods_review_receipt_v0_3.json`

**Disposition:** `STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`

**State:** `STUDY3_DRAFT_V0_3_SECOND_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`

The second bounded independent methods review of the Study 3 interface-calibration
protocol adjudicated all 20 inherited findings and all 22 unresolved items on independent
evidence, answered every mandatory audit target, and returned one of the three permitted
dispositions.

Sixteen inherited findings are `VERIFIED_RESOLVED` and four are `PARTIALLY_RESOLVED`
(`S3MR-002`, `S3MR-013`, `S3MR-014`, `S3MR-017`). `UR-22` is
`CORRECTLY_RETAINED_AS_BLOCKING_OPERATOR_DECISION`; it is the only item carrying that
status. Ten new findings were recorded, `S3MR2-001` through `S3MR2-010`, comprising
2 BLOCKING, 6 MAJOR and 2 MINOR.

Rejection rather than acceptance with required changes was returned because every valid
repair requires a substantive choice rather than a bounded conformance edit. `S3MR2-001`
requires either a new presentation-effect estimand or a narrowed claim ceiling, because
`J_both` is mathematically identical to `J_cor` and therefore identifies joint correctness
rather than presentation invariance. `S3MR2-002` requires either a registered family-level
power target with re-derived sizes or a re-registered per-cell power semantics, because
the published unqualified `9/10` target is verified only per cell while the derived
profile-eligibility power is `0.100885944` for `S1` and `0.320003768` for `S2` and `S3`.
`S3MR2-010` requires registering a stochastic model or replacing the binomial architecture,
because no artifact states the sampling frame that licenses the exact binomial test.

This decision does not resolve `OD2`, does not select an interface or a positive reference,
does not freeze anything and authorizes no execution. The only legal successor action is
`OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_4`, followed by a further independent methods
review.

## D43 - Amend Study 3 to draft-v0.4 in response to the second independent methods review, and publish it for a third independent methods review rather than declaring it correct

**Date:** 2026-06 (repository time)
**State after this decision:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_4_COMPLETE_AWAITING_THIRD_INDEPENDENT_METHODS_REVIEW`

The second independent methods review of Study 3 draft-v0.3 returned
`STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` with ten structured findings:
`S3MR2-001` through `S3MR2-010`, comprising 2 BLOCKING, 6 MAJOR and 2 MINOR. This decision
amends the design to draft-v0.4 and sends it to a THIRD independent methods review. It does
not declare the amended design correct.

**What was decided.**

The gate-bearing `I3` indicator is narrowed to `J_joint_correct`, a level over a registered
item-generating distribution, and every active claim field is stripped of invariance,
equivalence and presentation-effect language. The design does not identify a presentation
effect and no longer says that it does (`S3MR2-001`).

A registered sampling frame is added. Within each gate-bearing atomic cell, base-item units
or base-item contrast clusters are drawn independently and identically WITH replacement from
a registered generator distribution with exact rational weights. Duplicates are legitimate
and must be retained. The deterministic complete-block assignment of the 32-state `K5`
nuisance support is retired in favour of iid draws at exact weight `1/32` per state, and the
requirement that `n` be a multiple of 32 is retired with it (`S3MR2-007`, `S3MR2-010`).

The type-II architecture is re-registered as an arbitrary-dependence union bound over exact
rationals. The per-stage profile false-negative budget is `19/400`; dividing by the derived
maximum gate-bearing cell count over the selectable profiles, `m_max = 43`, gives a per-cell
budget of `19/17200` and a per-cell power target of `17181/17200`. The profile stage power
floor is `381/400` and the study end-to-end power floor is `9/10`. No binding bound assumes
independence between cells (`S3MR2-002`).

Every development sample size is re-derived as the smallest unrestricted positive integer
meeting that per-cell target: `n = 413` for the `I1/I3` joint-correctness floor, `n = 214`
for the `I2` headroom floor and `n = 448` for the `I4` positive-reference floor. The
draft-v0.3 sizes `256` and `128` are withdrawn from every active field (`S3MR2-003`).

Confirmation applicability becomes the intersection of a component's registered selectable
profiles with the single profile selected on the development split, so `S4` can never appear
and `I1b` and `K5` are confined to `S1` (`S3MR2-004`). The `S4` diagnostic stream now carries
a derived, non-null forward cost (`S3MR2-005`). The state machine is registered as total and
deterministic, with an `I0` failure mapping only to `STOP_INSTRUMENT_DEFECT` (`S3MR2-006`).
The `I0` fixture accounting is reconstructed from a registered breakdown (`S3MR2-008`), and
the binding ordering constraint `P3Q >= 19/20 > I4 p1 = 9/10 > I4 p0 = 4/5` is registered
without selecting any positive reference (`S3MR2-009`).

**What was not decided.**

`OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`. No positive reference, checkpoint,
model revision, tokenizer or wrapper is selected, preferred, pinned, downloaded or
prequalified. No interface profile is selected. Nothing is frozen, no execution is
authorised, no seed exists, no bank exists and no confirmation content exists. The original
research question remains unanswered.

**Self-approval is prohibited.** Every repair is recorded as
`PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`. Both independent reviews
remain valid rejections and neither was edited. The only legal successor action is a third
bounded independent methods review of draft-v0.4, conducted in a fresh session by a party
that did not draft draft-v0.4.

## 2026-08-09 - D44 - Study 3 draft-v0.4 third independent methods review disposition

**Decision id.** `D44`.

**Decision.** Return `STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED` against reviewed commit `e865be51da6c7e1a7a4f5b1fcad0efc513bd0f43`, tree
`86c5a5ec0e475090c14654cff27605f883495a48`.

**Round.** A bounded, CPU-only, model-free third independent methods review of the already
published draft-v0.4, conducted in a fresh session and a fresh worktree by a party that neither
drafted draft-v0.4 nor repaired its historical-regression harness. Every decision-bearing
statistical calculation, construction audit and logical derivation was implemented independently
and committed before any drafting output was opened.

**Basis.** One BLOCKING and three MAJOR methods defects remain, so acceptance as specified is
unavailable. Closing `S3MR3-001` and `S3MR3-010` necessarily alters registered applicability, the
atomic cell set of two selectable profiles, the generator specification and the per-profile claim
ceiling, all of which are excluded from an accepted-with-conformance disposition. No
rejection-driving defect is fundamental: every required repair is a localized design choice that
leaves the estimand, the interface panel, the task strata, the difficulty, the model roles and the
feasibility strategy intact.

**Verified resolved.** `S3MR2-002`, `S3MR2-005`, `S3MR2-006`, `S3MR2-007` and `S3MR2-009`.
**Partially resolved.** `S3MR2-001`, `S3MR2-003`, `S3MR2-004`, `S3MR2-008` and `S3MR2-010`.

**Independently reproduced with zero numeric disagreement.** All exact-binomial thresholds, null
tails and powers on both splits; the unrestricted positive-integer sample-size searches returning
413, 214 and 448; the gate-bearing cell census and `m_max = 43` over the selectable profiles only;
the arbitrary-dependence budget ladder `19/17200`, `17181/17200`, `381/400`, `1/200` and `9/10`;
the sixteen-branch selection map; the total deterministic state machine; and every operation
projection derived from primitive counts.

**Verdicts.** `METHOD_INTERNAL_VALIDITY_VERDICT` and
`STUDY3_PURPOSE_AND_CONSTRUCT_RELEVANCE_VERDICT` are both
`ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR`, reached separately.

**What was not decided.** `OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION` and the
disposition is not driven by it. No interface profile and no positive reference is selected.
Nothing is frozen, no execution is authorised, no seed or bank exists, no confirmation content was
opened and no evidence row was created. The original research question remains unanswered.

**Legal successor action.** `OPERATOR_BOUNDED_AMENDMENT_ROUND_FOR_DRAFT_V0_5`, followed by a further independent methods review. No
freeze, no `P3-Q`, no bank, no seed, no model execution, no development round, no confirmation
access and no feasibility-pilot authority is created. No successor prompt was written.


## 2026-08-10 - `D44`: Study 3 draft-v0.5 bounded operator amendment

**Supersedes the draft-v0.4 design recorded in `D43`.** `D43` is retained
unedited as immutable provenance. The third independent methods review of
draft-v0.4 returned `STUDY3_V0_4_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`
against commit `79bcc20244ab55045ba1c5d778d829d4caac3dd3` with one BLOCKING,
three MAJOR and six MINOR structured findings. This entry records the bounded
amendment that answers them. Everything `D43` describes is historical from this
entry onward and is not current.

**`S3MR3-001`, the blocking finding.** `K6-SEP` varies the separator between a
displayed option label and its displayed option content. `S2` and `S3` render
neither, so the factor has no referent for them and the two members of the pair
would be byte-identical; under the registered deterministic scorer that cell is a
self-comparison, not a presentation pair. `K6-SEP` is therefore recorded
`not_applicable` for `S2` and `S3` in every location. `not_applicable` is never a
pass, a zero effect, robustness evidence, a gate-bearing cell or a denominator
member. No profile-specific replacement separator is invented and no `R-sep`
duplicate of `R-base` is rendered. **`S2` and `S3` each carry exactly one genuine
`I3` contrast, `K6-INSTR`**, and their claim ceiling states joint robust
correctness for that single pair only. Applicability is now registered per
contrast ID, because family level cannot express the distinction.

**Re-derivation.** The census counts applicable contrast IDs:

| profile | `I1a` | `I1b` | `I2` | `K5` | `K6` | `I4` | total | applicable `I3` contrasts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `S1` | 3 | 3 | 6 | 21 | 6 | 4 | **43** | 9 |
| `S2` | 3 | 0 | 6 | 0 | 3 | 4 | **16** | 1 |
| `S3` | 3 | 0 | 6 | 0 | 3 | 4 | **16** | 1 |
| `S4` | 3 | 3 | 6 | 21 | 6 | 0 | **39** | 9 |

`m_max` is the maximum over the selectable profiles, so it is still `S1`'s 43:
unchanged because the profile that attains it is unchanged, not because the value
was preserved. By derivation the per-cell budget `19/17200`, the per-cell target
`17181/17200`, the profile stage floor `381/400`, the end-to-end floor `9/10` and
the sizes `413`/`214`/`448` with pass counts `389`/`129`/`383` all reproduce.

**`S3MR3-010`.** A byte-exact deterministic rendering registry and schema are
registered as binding inputs, closing the gap that made the two `K6` cells
non-instantiable and that hid `S3MR3-001`. Tokenizer distinctness is not tested,
because no checkpoint or tokenizer may be accessed; a fail-closed pre-bank rule is
registered instead and it does not resolve `OD2`.

**The remaining repairs.** Confirmation applicability becomes component level
(`S3MR3-002`); active text is aligned with history preserved (`S3MR3-003`); the
prohibition's enforcement is widened to its registered scope with explicit
auditable exemptions (`S3MR3-004`); `I4` is removed from `S4`'s applicable gates
(`S3MR3-005`); `STOP_AWAITING_AUTHORITY` is removed from the legal stop states
rather than added to the state machine (`S3MR3-006`); the local power
non-monotonicity above each registered size is disclosed and execution must use
the exact registered `n` (`S3MR3-007`); active round references now name the
fourth review (`S3MR3-008`); and the union-bound conclusion is restated over an
adequate profile (`S3MR3-009`).

**What this round did not do.** It did not freeze the design, authorise
execution, resolve `OD2` or `UR-22`, select an interface profile or a positive
reference, construct a bank, draw a seed, run a tokenizer or a model, open
confirmation content or create an evidence row. Every operation counter is zero,
every authority flag is false, and the evidence ledger still ends at `EV-0016`.
The original research question remains unanswered.

**Disposition.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`.
The sole legal successor is a fresh-session fourth independent methods review of
published draft-v0.5 by a party that did not draft it.
