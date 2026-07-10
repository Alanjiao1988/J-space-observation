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

## Container registry strategy: ACR active, GHCR historical

Historical decision: GHCR was preferred for git-SHA provenance and GitHub Actions builds. Current active route changed after private GHCR pull authentication blocked Azure job creation.

Current active route:

- **Active: ACR (Azure Container Registry) + user-assigned managed identity.**
- **GHCR: historical/secondary only** unless Alan explicitly reopens it.
- ACR admin credentials are disabled and must not be used.
- Container Apps Jobs pull from ACR using user-assigned managed identity with `AcrPull`.

Current ACR resources:

- ACR: `acrjspaceobssea0708231738`
- Login server: `acrjspaceobssea0708231738.azurecr.io`
- Current image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:f94e889ef608`
- Managed identity: `id-jspace-aca-acrpull-sea`
- AcrPull: assigned

Reason for switching:

- GHCR package is private.
- `GHCR_PAT` was not visible to the agent process.
- Current `gh auth token` lacks `read:packages`.
- ACR + managed identity avoids registry passwords and token handling.

## Resource principles

- Prefer Azure Container Apps Jobs with GPU T4 workload profiles for batch work.
- Do not create always-on GPU services.
- Do not expose unauthenticated notebooks or serving endpoints.
- Do not commit Azure credentials, Hugging Face tokens, or model weights.
- Record every Azure command, run, failure, and cleanup status in `docs/run_log.md`.

## Target Azure defaults

- Resource group: `rg-jspace-observation-sea`
- Region: `southeastasia`
- Log Analytics workspace: `law-jspace-observation-sea`
- Active Container Apps environment: `cae-jspace-observation-sea-vnet2`
- Blob network smoke job: `job-jspace-blob-net-smoke-v2`
- Phase 0.5 job: `job-jspace-phase05`
- Phase 1 dry-run job: `job-jspace-phase1-dryrun`
- Current small pilot job: `job-jspace-p1-criteria-val`
- GPU workload profile type: `Consumption-GPU-NC8as-T4`
- GPU workload profile name: `gpu-t4`
- Model cache in container: `/tmp/models/huggingface`
- Results root in container: `/workspace/results/runs`

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
RESOURCE_GROUP=rg-jspace-observation-sea
LOCATION=southeastasia
CONTAINER_APP_ENV=cae-jspace-observation-sea
CONTAINER_APP_JOB=job-jspace-ghcr-smoke
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

2. **Create resource group**:
   ```bash
   az group create --name rg-jspace-observation-sea --location southeastasia \
     --tags project=jspace-observation owner=alan purpose=research-pilot registry=ghcr environment=dev -o table
   ```

3. **Create Container Apps environment with GPU workload profile:**
   ```bash
   az monitor log-analytics workspace create \
     --resource-group rg-jspace-observation-sea \
     --workspace-name law-jspace-observation-sea \
     --location southeastasia \
     --tags project=jspace-observation owner=alan purpose=research-pilot registry=ghcr environment=dev -o table

   az containerapp env create \
     --resource-group rg-jspace-observation-sea \
     --name cae-jspace-observation-sea \
     --location southeastasia \
     --enable-workload-profiles true -o table

   az containerapp env workload-profile add \
     --resource-group rg-jspace-observation-sea \
     --name cae-jspace-observation-sea \
     --workload-profile-name gpu-t4 \
     --workload-profile-type Consumption-GPU-NC8as-T4 -o table
   ```

   Notes from first real attempt:
   - `--enable-dedicated-gpu true` caused `WorkloadProfileInvalidType: NC24_A100 invalid`; do not use it for the T4 path.
   - `--min-nodes/--max-nodes` on `Consumption-GPU-NC8as-T4` caused `WorkloadProfilePropertyNotSupported: MinimumCount is not supported`; omit min/max for this consumption GPU profile.
   - Creating `gpu-t4` with only `--workload-profile-type Consumption-GPU-NC8as-T4` succeeded.

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

## Active ACR managed-identity command sequence

The ACR path has been executed successfully through smoke, Phase 0.5, Phase 1 dry-run, and a small Phase 1 pilot.

Current image:

```text
acrjspaceobssea0708231738.azurecr.io/j-space-observation:d69187c7a147
```

Run ACR-managed-identity jobs with:

```bash
export RESOURCE_GROUP="rg-jspace-observation-sea"
export CONTAINERAPPS_ENVIRONMENT="cae-jspace-observation-sea"
export WORKLOAD_PROFILE_NAME="gpu-t4"
export ACR_NAME="acrjspaceobssea0708231738"
export ACR_LOGIN_SERVER="acrjspaceobssea0708231738.azurecr.io"
export ACR_IMAGE="acrjspaceobssea0708231738.azurecr.io/j-space-observation:d69187c7a147"
export IDENTITY_NAME="id-jspace-aca-acrpull-sea"
```

Smoke:

```bash
export JOB_NAME="job-jspace-acr-smoke"
export JOB_COMMAND="python -m pytest tests/ -q"
bash infra/azure/scripts/06_run_job_acr_mi.sh
```

Phase 0.5:

```bash
export JOB_NAME="job-jspace-phase05-acr"
export JOB_COMMAND="python experiments/phase0_5_jlens_spike.py --skip-fit"
export CPU_CORES=4
export MEMORY=16Gi
bash infra/azure/scripts/06_run_job_acr_mi.sh
```

Phase 1 dry-run:

```bash
export JOB_NAME="job-jspace-phase1-dryrun-acr"
export JOB_COMMAND="python experiments/phase1_depth_gradient.py --dry-run"
bash infra/azure/scripts/06_run_job_acr_mi.sh
```

Small Phase 1 pilot:

```bash
export JOB_NAME="job-jspace-phase1-pilot-acr"
export JOB_COMMAND="python experiments/phase1_depth_gradient.py --models deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B --task-families arithmetic --depths 1,2,3 --conditions strict_answer_only,visible_cot,r1_style_thinking --max-new-tokens 64 --items-per-cell 1"
export CPU_CORES=4
export MEMORY=16Gi
bash infra/azure/scripts/06_run_job_acr_mi.sh
```

Do not run a broader Phase 1 sweep until pilot outputs are reviewed and persistent result export is decided.

## Active persistence route: private Azure Blob with managed identity

Azure Blob upload with managed identity over a private endpoint is the working persistence path. Storage public network access remains disabled.

Current storage:

```text
storage account: stjspacefiles0709085305
container: jspace-results
shared key used: no
identity: id-jspace-aca-acrpull-sea
role: Storage Blob Data Contributor
active ACA environment: cae-jspace-observation-sea-vnet2
VNet: vnet-jspace-observation-sea
Blob private endpoint: pe-stjspacefiles-blob-sea
private DNS zone: privatelink.blob.core.windows.net
```

Blob export environment variables:

```bash
export AZURE_CLIENT_ID="479d9229-632e-4490-ad92-854a34dfddf8"
export JSPACE_BLOB_ACCOUNT="stjspacefiles0709085305"
export JSPACE_BLOB_CONTAINER="jspace-results"
export JSPACE_BLOB_PREFIX="<run-specific-prefix>"
export JSPACE_RESULTS_ROOT="/workspace/results"
```

Smoke:

```bash
export JOB_NAME="job-jspace-blob-smoke-acr"
export JOB_COMMAND="python scripts/blob_export_smoke.py"
export ACR_IMAGE="acrjspaceobssea0708231738.azurecr.io/j-space-observation:afd647a6b53e"
bash infra/azure/scripts/06_run_job_acr_mi.sh
```

Persistent small Phase 1 pilot:

```bash
export JOB_NAME="job-jspace-phase1-pilot-blob-acr"
export JOB_COMMAND="python experiments/phase1_depth_gradient.py --models deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B --task-families arithmetic --depths 1,2,3 --conditions strict_answer_only,visible_cot,r1_style_thinking --max-new-tokens 64 --items-per-cell 1 --require-blob-export"
export ACR_IMAGE="acrjspaceobssea0708231738.azurecr.io/j-space-observation:afd647a6b53e"
export CPU_CORES=4
export MEMORY=16Gi
bash infra/azure/scripts/06_run_job_acr_mi.sh
```

Do not run jobs requiring Blob export in the old non-VNet environment. Use `cae-jspace-observation-sea-vnet2`.

## Validator-hardened pilot status

The no-CoT validation false negative has been fixed and rerun on the minimal persistent pilot.

Current validator image:

```text
acrjspaceobssea0708231738.azurecr.io/j-space-observation:937288cfb8ef
```

Current validator pilot:

```text
job: job-jspace-p1-validator
execution: job-jspace-p1-validator-xkqro3f
blob prefix: phase1-pilot-validator/20260709T022001Z
```

Key result:

```text
strict_answer_only no_cot_valid_rate: 0.0000 for depths 1, 2, 3
strict_answer_only visible_reasoning_marker_rate: 1.0000 for depths 1, 2, 3
parse_ambiguous_rate: 1.0000 for all cells
```

Interpretation:

- The previous validator false negative is fixed.
- The current strict-answer-only prompt/decoding still produces visible reasoning, so no strict no-CoT-valid behavioral subset exists in this tiny pilot.
- Do not broaden Phase 1 until strict-answer-only prompting/decoding and parse policy are reviewed.
- This is still behavioral/infrastructure validation only, not J-space evidence.

## Strict answer-only prefill variant status

The strict answer-only generation strategy was tightened and rerun with one additional condition.

Current strictfix image:

```text
acrjspaceobssea0708231738.azurecr.io/j-space-observation:9b5895db173f
```

Strictfix run:

```text
job: job-jspace-p1-strictfix2
execution: job-jspace-p1-strictfix2-1sjj2n5
blob prefix: phase1-pilot-strictfix2/20260709T025356Z
```

Result:

```text
strict_answer_only: still no-CoT invalid for all depths
strict_answer_only_prefill_answer: no visible reasoning on depth 1, but incomplete/wrong; still invalid on depths 2/3
```

Do not broaden the run yet. Any future attempt should test stop-sequence or explicitly labeled post-processing while preserving raw output and reporting raw vs postprocessed validity separately.

## Raw-vs-postprocessed condition status

Condition:

```text
strict_answer_only_postprocessed
```

Current image:

```text
acrjspaceobssea0708231738.azurecr.io/j-space-observation:9342ef130d46
```

Run:

```text
job: job-jspace-p1-postprocess
execution: job-jspace-p1-postprocess-gor0o1r
blob prefix: phase1-pilot-postprocess/20260709T044224Z
```

Key result:

```text
raw_no_cot_valid_rate: 0.0000 for depths 1,2,3
postprocessed_no_cot_valid_rate: 1.0000 for depths 1,2,3
postprocessing_success_rate: depth1=1.0000, depth2=0.0000, depth3=1.0000
accuracy_postprocessed: depth1=1.0000, depth2=0.0000, depth3=0.0000
```

Interpretation:

- Raw output still leaks visible reasoning.
- Postprocessing can recover a clean correct answer in the easiest cell only.
- Postprocessed output must not be treated as genuine no-CoT generation.
- This remains behavioral/infrastructure validation, not J-space evidence.

## Private network and stop-control status

Active private resources:

```text
VNet: vnet-jspace-observation-sea
ACA subnet: snet-aca-jspace-sea-v2 (10.80.4.0/23)
private endpoint subnet: snet-pe-jspace-sea (10.80.2.0/27)
Blob private endpoint: pe-stjspacefiles-blob-sea
Blob private IP: 10.80.2.4
private DNS zone: privatelink.blob.core.windows.net
DNS link: link-vnet-jspace-observation-sea-blob
active ACA environment: cae-jspace-observation-sea-vnet2
GPU profile: gpu-t4 / Consumption-GPU-NC8as-T4
```

Subscription prerequisite:

```text
Microsoft.Network/AllowBringYourOwnPublicIpAddress = Registered
```

The first environment, `cae-jspace-observation-sea-vnet`, was created before this feature was registered and cannot start containers. Do not use it. It remains present because no deletion was authorized.

Blob network smoke:

```text
job: job-jspace-blob-net-smoke-v2
execution: job-jspace-blob-net-smoke-v2-l02nljz
status: Succeeded
prefix: network-smoke-v2/20260710T071144Z
uploaded: smoke.txt
```

Stop-control pilot:

```text
condition: strict_answer_only_stopped
image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:c29852ab97b5
job: job-jspace-p1-stopcontrol-vnet
execution: job-jspace-p1-stopcontrol-vnet-b55p4c6
status: Succeeded
prefix: phase1-pilot-stopcontrol-vnet/20260710T072107Z
files: 4
cells: 15
```

Stopped-condition result:

```text
raw_no_cot_valid_rate: 1.0000 for depths 1,2,3
stopped_no_cot_valid_rate: 1.0000 for depths 1,2,3
stop_triggered_rate: 1.0000 for depths 1,2,3
stop string: \n\n for all depths
accuracy_stopped: depth1=1.0000, depth2=0.0000, depth3=0.0000
```

Interpretation:

- The stop criterion prevented subsequent reasoning markers from being emitted in this pilot.
- Depth 2 stopped at a non-answer placeholder.
- Depth 3 stopped at a clean but wrong boxed answer.
- Stop-controlled validity is an intervention result, not spontaneous raw no-CoT evidence.
- Keep raw, stopped, and postprocessed branches separate.
- Do not broaden Phase 1 yet.

## Phase 1 branch reporting policy

Every future Phase 1 run must use the taxonomy in `docs/phase1_experiment_branches.md`:

| Branch | Key | Conditions | Meaning |
|---|---|---|---|
| Raw strict no-CoT feasibility | `raw_strict` | `strict_answer_only`, `strict_answer_only_prefill_answer` | Evaluate unmodified raw output without stop intervention or extraction. |
| Stop-controlled generation intervention | `stopped_intervention` | `strict_answer_only_stopped` | Test generation-time suppression of visible reasoning. |
| Postprocessed answer-recovery utility | `postprocessed_utility` | `strict_answer_only_postprocessed` | Test deterministic answer-span recovery, not no-CoT generation. |

Operational reporting rules:

1. Preserve raw, stopped, and postprocessed outputs and validity fields separately.
2. Report `accuracy_raw`, `accuracy_stopped`, and `accuracy_postprocessed` separately.
3. Use `NA` for metrics that do not apply to a branch.
4. If stop triggering occurs, describe the output as intervention-controlled.
5. Postprocessed validity never replaces raw validity.
6. Do not use any Phase 1 branch as hidden-reasoning or J-space evidence.

Preregistered limited-scale gates:

| Branch | Required thresholds |
|---|---|
| `raw_strict` | `n >= 3`; raw validity `>= 0.90`; reasoning markers `<= 0.10`; parse validity `>= 0.80`; ambiguity/warnings `<= 0.20`; raw accuracy `>= 0.50`; plus `>= 0.70 * visible_cot_accuracy` only when the baseline is valid. |
| `stopped_intervention` | `n >= 3`; stopped validity `>= 0.90`; stop success `>= 0.80`; parse validity `>= 0.80`; stopped accuracy `>= 0.50`; plus the relative gate only when the baseline is valid. |
| `postprocessed_utility` | `n >= 3`; postprocessed validity `>= 0.90`; recovery success `>= 0.80`; warnings `<= 0.20`; postprocessed accuracy `>=` raw accuracy and `>= 0.50`. |

The visible-CoT baseline is valid only when matching `visible_cot_n >= 3`, parse-valid rate `>= 0.80`, and accuracy `> 0`. Otherwise the relative gate is `NA`. Postprocessed visible-CoT-relative performance is report-only. The detailed and controlling definition is `docs/phase1_experiment_branches.md`.

The criteria-validation run below used these preregistered thresholds without modification.

## Criteria-validation pilot status

```text
source commit: f94e889ef6089aab8f651a2d14c42341440625a3
ACR build: cma
image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:f94e889ef608
digest: sha256:f27cc0e4cea0ae9569dbb384598fb391f3b923022ce9257f8301684c9dc23806
environment: cae-jspace-observation-sea-vnet2
workload profile: gpu-t4 / Consumption-GPU-NC8as-T4
job: job-jspace-p1-criteria-val
execution: job-jspace-p1-criteria-val-6s8p15p
status: Succeeded
Blob prefix: phase1-pilot-criteria-validation/20260710T135655Z
files: 4
cells: 15
```

The requested job name `job-jspace-p1-criteria-validation` is 33 characters and exceeds the Container Apps Jobs 32-character limit. Use `job-jspace-p1-criteria-val`.

When invoking the Bash helper from Windows:

1. Use `C:\Program Files\Git\bin\bash.exe`, not the WindowsApps WSL launcher.
2. Set `MSYS_NO_PATHCONV=1`.
3. Set `MSYS2_ARG_CONV_EXCL=*`.
4. Do not issue a separate `az containerapp job start`; `06_run_job_acr_mi.sh` already starts the job.

Observed classifications by depth 1/2/3:

- Raw strict: `surface_answer_only_but_task_failed` / `raw_strict_not_established` / `raw_strict_not_established`.
- Stopped intervention: `stopped_intervention_usable` / `stopped_intervention_not_useful` / `stopped_surface_compliant_but_task_failed`.
- Postprocessed utility: `postprocessed_answer_recovery_usable` / `postprocessed_surface_clean_but_warning_high` / `postprocessed_answer_recovery_usable`.

The summary printed all passed/failed criteria and the mandatory interpretation warnings. Blob upload completed through managed identity and the private endpoint. Storage public access and shared-key access remained disabled.

Do not treat the historical depth 3 postprocessed usable label as task success: both raw and postprocessed accuracy were zero, satisfying only the earlier non-degradation rule. The persisted summary remains unchanged as a historical artifact.

No further run is authorized. No hidden-reasoning, internal-workspace, or J-space claim is supported.

## Branch-gate hardening status

The repository now applies the following rules prospectively:

1. `n >= 3` is required for formal success; otherwise an otherwise-passing row uses a branch-specific `pilot_only` label.
2. Clear failures retain failure labels below the sample minimum.
3. Absolute branch accuracy `>= 0.50` cannot be replaced by a relative comparison.
4. Invalid or undersampled visible-CoT baselines make relative gates `NA`.
5. Postprocessed utility requires both non-degradation and absolute accuracy `>= 0.50`; `0 >= 0` is not usable.

For this hardening update:

```text
Azure job: not run
model inference: not run
model download: not performed
ACR rebuild: not performed
active image remains: acrjspaceobssea0708231738.azurecr.io/j-space-observation:f94e889ef608
latest successful execution remains: job-jspace-p1-criteria-val-6s8p15p
```

The current ACR image predates these rules. Rebuild only after a separately approved limited run.

## Persistent results storage status

Azure Files was attempted as the first persistence path and is currently blocked by organization/subscription policy.

Observed behavior:

- Storage account creation succeeds.
- `allowSharedKeyAccess` remains `False` even when `--allow-shared-key-access true` is specified.
- Azure Files data-plane operations using account keys fail:

```text
KeyBasedAuthenticationNotPermitted
Key based authentication is not permitted on this storage account.
```

- Container Apps environment storage registration can be created, but the mounted job hung and was stopped.
- The invalid environment storage registration has been removed.

Do not use `ENABLE_RESULTS_MOUNT=true` until a working storage backend is available.

Current decision:

1. Do not use Azure Files.
2. Do not enable storage public network access.
3. Do not use storage keys or SAS.
4. Use Blob managed-identity upload from `cae-jspace-observation-sea-vnet2`.
5. Verify private outputs through job logs or a review job inside the same VNet.

### GHCR pull/auth findings from first smoke attempt

The first unauthenticated GHCR smoke-job creation failed before execution because the package requires authentication:

```text
Error code: InvalidParameterValueInContainerTemplate
Message: Field 'template.containers.job-jspace-ghcr-smoke.image' is invalid:
GET ... ghcr.io ... UNAUTHORIZED: authentication required
```

Next GHCR smoke attempt needs one of:

1. Make the GHCR package public; or
2. Provide `GHCR_USERNAME` and `GHCR_PAT` via environment variables / Azure secret only.

Do not commit or log `GHCR_PAT`. The token should have minimal package read permission (`read:packages`) if the package remains private.

Follow-up retry:

- Retrying with the available `gh auth token` as the Azure registry secret also failed.
- Error code: `InvalidParameterValueInContainerTemplate`.
- Message includes: `DENIED: requested access to the resource is denied`.
- Conclusion: the current `gh auth token` is not sufficient for Azure to pull this private GHCR image.
- Next retry needs either a public GHCR package or a classic PAT with `read:packages`.

Preflight update:

- `GHCR_PAT` was not set in the local environment.
- The current `gh auth token` was tested against the GHCR package versions API and returned `403` / `read:packages` required.
- Do not retry job creation with the current `gh auth token`.
- `infra/azure/scripts/05_run_job_ghcr.sh` now supports `GHCR_PAT` first, then `gh auth token` fallback, but a proper package-read token is still required for a private GHCR package.

Environment variable visibility note:

- Setting `$env:GHCR_PAT` in a user shell may not be visible to Copilot tool processes because each command runs in a fresh process.
- If Copilot reports `GHCR_PAT` is not visible, set it in Windows User environment or another secure path readable by the agent:

  ```powershell
  [Environment]::SetEnvironmentVariable("GHCR_USERNAME", "Alanjiao1988", "User")
  [Environment]::SetEnvironmentVariable("GHCR_PAT", "<classic PAT with read:packages>", "User")
  ```

- Do not paste token values into chat and do not commit them.

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
