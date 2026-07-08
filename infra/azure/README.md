# Azure Infrastructure for J-space Observation

This directory contains Azure-first automation for running J-space observation experiments on Azure GPU containers.

The local PC is orchestration-only. Do not run real model inference, model downloads, J-lens fitting, patching, or ablations locally.

## Prerequisites

- Azure CLI (`az`)
- `containerapp` Azure CLI extension
- Active Azure subscription
- Registered providers:
  - `Microsoft.App`
  - `Microsoft.ContainerRegistry`
- Azure Container Apps GPU T4 quota in the target region

## Configuration

Copy `variables.example.env` to `variables.env` and fill in local values:

```bash
cp variables.example.env variables.env
```

Do not commit `variables.env`, credentials, tokens, or secrets.

## Scripts

- `00_check_prereqs.sh`: Bash readiness check; does not create resources.
- `00_check_prereqs.ps1`: PowerShell readiness check; does not create resources.
- `01_build_and_push_image.sh`: Build image in ACR; creates/uses Azure resources when explicitly run.
- `02_run_phase0_5.sh`: Run Phase 0.5 availability/model-loading check as a Container Apps Job.
- `03_run_phase1.sh`: Run Phase 1 dry-run as a Container Apps Job.
- `04_run_phase1_pilot.sh`: Run a small real Phase 1 pilot as a Container Apps Job.

## Intended order

```bash
bash scripts/00_check_prereqs.sh
bash scripts/01_build_and_push_image.sh
bash scripts/02_run_phase0_5.sh
bash scripts/03_run_phase1.sh
bash scripts/04_run_phase1_pilot.sh
```

Run `04_run_phase1_pilot.sh` only after readiness, provider registration, GPU quota, image build, Phase 0.5 Azure check, and Phase 1 Azure dry-run pass.

## Cost management

- Use manual Container Apps Jobs, not always-on services.
- Keep workload profile min nodes at zero where possible.
- Start with the small Phase 1 pilot before full experiments.
- Stop and record blockers if GPU quota is missing.

## Logs and status

Check job executions:

```bash
az containerapp job execution list -g <resource-group> -n <job-name> -o table
```

Every Azure command and job must be logged in `docs/run_log.md`.
