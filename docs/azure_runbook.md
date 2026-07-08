# Azure Runbook

## Goal

Run J-space observation experiments on Azure GPU containers, not on the local PC.

The local PC is now **orchestration-only**. Use it for:

- Git operations.
- Unit tests and dry runs.
- Documentation updates.
- Azure CLI readiness checks and job submission commands.

Heavy execution must happen in Azure GPU containers:

- Model download.
- Model loading.
- Phase 0.5 fitting/model-loading checks beyond dry availability checks.
- Phase 1 real generation.
- Later J-lens fitting/readout, activation patching, and ablation experiments.

Do not silently fall back to local model inference if Azure is blocked.

## Container registry strategy: GHCR primary, ACR secondary

- **Primary: GHCR (GitHub Container Registry).** Images are built by a GitHub Actions workflow and pushed to `ghcr.io/alanjiao1988/j-space-observation:<git-sha>`.
- **Secondary fallback: ACR (Azure Container Registry).** As of 2026-07-08, `Microsoft.ContainerRegistry` is now `Registered`, so the ACR scripts (`01_build_and_push_image.sh`, `02_run_phase0_5.sh`, `03_run_phase1.sh`, `04_run_phase1_pilot.sh`) are usable again. Use ACR only if GHCR is unavailable.
- **Reason GHCR stays primary:**
  - GHCR aligns with git-SHA image provenance (each image tagged with the exact commit SHA).
  - Builds run in GitHub Actions, so the local PC does not build or push large images.
  - Avoids re-coupling the pipeline to ACR provider registration timing, which was blocked for hours.
- Both paths still require `Microsoft.App` registered and confirmed Container Apps T4 GPU quota in `southeastasia`.

## Resource principles

- Prefer Azure Container Apps Jobs with GPU T4 workload profiles for batch work.
- Do not create always-on GPU services.
- Do not expose unauthenticated notebooks or serving endpoints.
- Do not commit Azure credentials, Hugging Face tokens, or model weights.
- Record every Azure command, run, failure, and cleanup status in `docs/run_log.md`.

## Target Azure defaults

- Resource group: `rg-jspace-observation`
- Region: `southeastasia`
- Container Apps environment: `acaenv-jspace-observation`
- Container Apps job prefix: `job-jspace-observation`
- GPU workload profile type: `Consumption-GPU-NC8as-T4`
- GPU workload profile name: `gpu-t4`
- Model cache in container: `/mnt/models/huggingface`
- Results directory in container: `/mnt/results`

Copy `infra/azure/variables.example.env` to `infra/azure/variables.env` locally and fill placeholders. Do not commit `variables.env`.

## Lightweight readiness checks

These checks do not create Azure resources:

```powershell
az version
az account show --query "{name:name,id:id,state:state,isDefault:isDefault,tenantId:tenantId}" -o json
az extension list -o table
az provider show -n Microsoft.App --query registrationState -o tsv
az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv
```

Container Apps extension:

```powershell
az extension show --name containerapp
az extension add --name containerapp --upgrade
```

Use the second command only if the extension is missing or stale.

Repository readiness script:

```powershell
.\infra\azure\scripts\00_check_prereqs.ps1
```

or from bash:

```bash
bash infra/azure/scripts/00_check_prereqs.sh
```

The readiness scripts must not create resources.

## GPU quota gate

Before running any Azure job that loads models or performs generation/fitting, verify GPU quota.

Portal path:

1. Azure Portal -> Subscriptions.
2. Select the active subscription.
3. Open **Usage + quotas**.
4. Filter by region: `southeastasia`.
5. Filter/search for Container Apps or provider `Microsoft.App`.
6. Verify quota for Azure Container Apps GPU T4 workload profile, e.g. `Consumption-GPU-NC8as-T4`.
7. If quota is missing or zero, stop and request quota. Do not run local inference as a fallback.

CLI discovery helpers:

```powershell
az containerapp env workload-profile list-supported -l southeastasia -o table
az provider show -n Microsoft.App --query registrationState -o tsv
```

If using the quota extension, inspect available quota entries for the subscription/region and record the output in `docs/run_log.md`. Azure quota command coverage varies by provider; if CLI output is unclear, use the portal gate above.

## Prepared Azure scripts

Do not run these until readiness and quota gates pass.

1. Build/push image to ACR:

```bash
bash infra/azure/scripts/01_build_and_push_image.sh
```

2. Run Phase 0.5 availability/model-loading check on Azure:

```bash
bash infra/azure/scripts/02_run_phase0_5.sh
```

3. Run Phase 1 dry run on Azure:

```bash
bash infra/azure/scripts/03_run_phase1.sh
```

4. Run small real Phase 1 pilot on Azure:

```bash
bash infra/azure/scripts/04_run_phase1_pilot.sh
```

The small pilot is intentionally scoped to one model, arithmetic only, depths `1,2,3`, all three prompt conditions, one item per cell, and `max_new_tokens=64`.

## GHCR fallback when Microsoft.ContainerRegistry is blocked

If `Microsoft.ContainerRegistry` cannot reach `Registered` (for example, it stays in `Registering` for hours even after `az provider register --namespace Microsoft.ContainerRegistry --wait`), do not block the whole pipeline on ACR. Use GitHub Container Registry (GHCR) as the image source instead.

Key points:

- Azure Container Apps can pull images from public or private container registries, including GHCR.
- GHCR image path format:

  ```text
  ghcr.io/alanjiao1988/j-space-observation:<git-sha>
  ```

- Prefer building/pushing the image with GitHub Actions (`.github/workflows/build-ghcr.yml`) so the local PC does not build or push large images.
- For private GHCR packages, use a GitHub Personal Access Token (PAT) with the minimal `read:packages` permission.
- Provide the GHCR token to Azure only as a Container Apps secret at deployment time.
- Never commit the GHCR token to the repository.
- Never print or log token values.

Still required even with the GHCR fallback:

- `Microsoft.App` provider must be `Registered`.
- Azure Container Apps T4 GPU quota must be confirmed for the target region.
- T4 quota for `southeastasia` must be confirmed before creating GPU jobs.
- If T4 quota is unavailable, stop and do not fall back to local model inference.

### GHCR build workflow

The workflow is installed at `.github/workflows/build-ghcr.yml`.

Source template:

```text
infra/ci/build-ghcr.yml
```

Workflow installation status:

- The local `gh` token could not install the workflow because it lacked GitHub `workflow` OAuth scope.
- The workflow was successfully installed through the GitHub connector / GitHub App path in commit `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Do not re-add manual-install instructions unless the workflow file is removed.

Workflow trigger command:

```powershell
gh workflow run build-ghcr.yml -R Alanjiao1988/J-space-observation --ref main -f push_latest=true
```

Latest successful run:

```text
run id: 28947916765
url: https://github.com/Alanjiao1988/J-space-observation/actions/runs/28947916765
head sha: c07db5c9625a9f9ad96c55f77385c078e11d4a66
image: ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66
latest: pushed
```

The workflow builds the `Dockerfile`, pushes to GHCR with the commit SHA and `latest`, and does not download Hugging Face models, bake model cache, run experiments, or include secrets.

### GHCR deploy notes for Azure Container Apps Job

Use `infra/azure/scripts/05_run_job_ghcr.sh`. It is parameterized and must not hardcode secrets.

Required environment variables (do not commit real values):

```text
RESOURCE_GROUP=rg-jspace-observation
LOCATION=southeastasia
CONTAINER_APP_ENV=acaenv-jspace-observation
CONTAINER_APP_JOB=job-jspace-observation-ghcr
IMAGE=ghcr.io/alanjiao1988/j-space-observation:<git-sha>
GHCR_USERNAME=<github-username>
GHCR_PAT=<provided via env var or Azure secret only>
JOB_COMMAND=<container command to run>
```

Do not run the GHCR deployment script until `Microsoft.App` is registered and T4 GPU quota is confirmed.

The container command is overridable via `JOB_COMMAND`. Supported examples:

```text
# Phase 0.5 availability/model-loading check
JOB_COMMAND="python experiments/phase0_5_jlens_spike.py --skip-fit"

# Phase 1 dry run
JOB_COMMAND="python experiments/phase1_depth_gradient.py --dry-run"

# Small Phase 1 pilot: single model, arithmetic only, depths 1/2/3, all three conditions
JOB_COMMAND="python experiments/phase1_depth_gradient.py --models Qwen/Qwen2.5-Math-1.5B --task-families arithmetic --depths 1,2,3 --conditions strict_answer_only,visible_cot,r1_style_thinking --items-per-cell 1 --max-new-tokens 64"
```

## Confirm Azure Container Apps T4 quota in southeastasia

This is the next Azure gate before any GPU job. Do not create GPU jobs until quota is confirmed.

Portal check:

1. Azure Portal -> Subscriptions -> select `MCAPS-Hybrid-REQ-125620-2025-alanjiao`.
2. Open **Usage + quotas**.
3. Filter by region `southeastasia` and provider `Microsoft.App` (Container Apps).
4. Look for the managed environment Consumption T4 GPU quota.
5. Confirm the available limit is at least 1 GPU for the workload profile `Consumption-GPU-NC8as-T4`.

CLI discovery helper (read-only):

```powershell
az containerapp env workload-profile list-supported -l southeastasia -o table
```

Current CLI findings:

- `Consumption-GPU-NC8as-T4` is offered in `southeastasia`.
- `Microsoft.Quota` can be registered for read-only quota queries.
- `az quota list --scope /subscriptions/<sub>/providers/Microsoft.App/locations/southeastasia` and `az quota usage list ...` currently return environment/session pool quotas but do **not** expose a T4 / NC8as-T4 / Managed Environment Consumption T4 quota item for this subscription/region.
- Therefore, if the portal does not show the quota clearly, use Azure support.

If T4 quota is unavailable or zero, open an Azure support request:

- Issue type: **Service and subscription limits (quotas)**
- Quota type: **Container Apps**
- Quota detail: **Managed Environment Consumption T4 GPUs**
- Region: **southeastasia**

Rules:

- Do not create GPU jobs until T4 quota is confirmed.
- Do not fall back to local inference if quota is missing.

## Planned Azure command sequence (GHCR primary; do not run until gates pass)

Do not run any of these until: (a) the GHCR image exists, and (b) T4 quota is confirmed. Each numbered step is a gate; stop and record a blocker if a step fails.

1. **Confirm T4 quota** (read-only; portal or support request as above). Gate: quota >= 1 T4 in `southeastasia`.

2. **Create resource group** (only after quota confirmed):
   ```bash
   az group create --name rg-jspace-observation --location southeastasia -o table
   ```

3. **Create Container Apps environment with GPU workload profile:**
   ```bash
   az containerapp env create \
     --resource-group rg-jspace-observation \
     --name acaenv-jspace-observation \
     --location southeastasia \
     --enable-workload-profiles true \
     --enable-dedicated-gpu true -o table

   az containerapp env workload-profile add \
     --resource-group rg-jspace-observation \
     --name acaenv-jspace-observation \
     --workload-profile-name gpu-t4 \
     --workload-profile-type Consumption-GPU-NC8as-T4 \
     --min-nodes 0 --max-nodes 1 -o table
   ```

4. **GHCR image smoke test** (cheap CPU-style command to verify image pull + startup). Provide GHCR creds via env only:
   ```bash
   export IMAGE=ghcr.io/alanjiao1988/j-space-observation:<git-sha>
   export GHCR_USERNAME=<github-username>
   export GHCR_PAT=<read:packages PAT, env only>
   export JOB_COMMAND="python -c 'import torch,transformers; print(\"image ok\")'"
   bash infra/azure/scripts/05_run_job_ghcr.sh
   ```

5. **Phase 0.5 `--skip-fit` on Azure:**
   ```bash
   export JOB_COMMAND="python experiments/phase0_5_jlens_spike.py --skip-fit"
   bash infra/azure/scripts/05_run_job_ghcr.sh
   ```

6. **Phase 1 `--dry-run` on Azure:**
   ```bash
   export JOB_COMMAND="python experiments/phase1_depth_gradient.py --dry-run"
   bash infra/azure/scripts/05_run_job_ghcr.sh
   ```

7. **Small Phase 1 pilot on Azure:**
   ```bash
   export JOB_COMMAND="python experiments/phase1_depth_gradient.py --models Qwen/Qwen2.5-Math-1.5B --task-families arithmetic --depths 1,2,3 --conditions strict_answer_only,visible_cot,r1_style_thinking --items-per-cell 1 --max-new-tokens 64"
   bash infra/azure/scripts/05_run_job_ghcr.sh
   ```

Check each job execution:
```bash
az containerapp job execution list -g rg-jspace-observation -n job-jspace-observation-ghcr -o table
```

Secondary fallback: if GHCR pull fails, switch to ACR via `infra/azure/scripts/01_build_and_push_image.sh` then the `02_/03_/04_` ACR job scripts.

## Required run logging

Every Azure resource creation or job start must append to `docs/run_log.md`:

```text
Date:
Command:
Resource:
Region:
SKU / workload profile:
Run ID / job execution:
Start time:
Stop/Cleanup status:
Cost-control notes:
```

## Stop rules

Stop and update `docs/decision_log.md` if any of these occur:

- Azure CLI is not logged in or subscription is wrong.
- `Microsoft.App` is not registered.
- `Microsoft.ContainerRegistry` is not registered AND the GHCR fallback is not available.
- Container Apps GPU T4 quota is unavailable.
- ACR build fails (and GHCR fallback also fails).
- Container Apps job cannot pull the image.
- Model download fails in Azure.
- Model loading fails in Azure.
- J-lens package import fails in Azure.
- J-lens fitting fails due to memory/runtime.
- Phase 1 pilot produces invalid no-CoT behavior at high rates.

Note: If only `Microsoft.ContainerRegistry` is blocked, prefer the GHCR fallback (see above) instead of stopping the whole pipeline.

Do not compensate by running full model inference, J-lens fitting, or heavy experiments locally.
