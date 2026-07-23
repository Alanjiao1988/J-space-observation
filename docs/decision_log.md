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
