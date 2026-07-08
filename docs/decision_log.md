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
