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

The workflow definition is stored at `infra/ci/build-ghcr.yml`.

> Note: The current Git credential lacks the `workflow` OAuth scope, so the CLI cannot push files under `.github/workflows/`. To activate the workflow, install it into `.github/workflows/build-ghcr.yml` using one of:
> - GitHub web UI: create `.github/workflows/build-ghcr.yml` and paste the contents of `infra/ci/build-ghcr.yml`; or
> - a local Git credential/token that has the `workflow` scope, then copy the file to `.github/workflows/build-ghcr.yml` and push.

Once installed, trigger the build workflow manually:

1. GitHub repo -> Actions -> "Build and push image to GHCR" -> Run workflow.
2. The workflow builds the `Dockerfile` and pushes to GHCR tagged with the commit SHA (and `latest`).
3. The image does not include secrets, Hugging Face model cache, or experiment outputs.
4. Confirm the pushed image at: `https://github.com/alanjiao1988/j-space-observation/pkgs/container/j-space-observation`.

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
