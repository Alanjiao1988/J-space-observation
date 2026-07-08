# Azure Infrastructure for J-space Observation

This directory contains infrastructure automation for running J-space observation experiments on Azure.

## Prerequisites

- Azure CLI (`az`)
- Docker
- Valid Azure subscription
- Appropriate permissions in resource group

## Configuration

Copy `variables.example.env` to `variables.env` and fill in your Azure details:

```bash
cp variables.example.env variables.env
# Edit variables.env with your settings
```

## Scripts

- `00_check_prereqs.sh`: Verify all prerequisites
- `01_build_and_push_image.sh`: Build Docker image and push to ACR
- `02_run_phase0_5.sh`: Submit Phase 0.5 job to Azure
- `03_run_phase1.sh`: Submit Phase 1 job to Azure

## Usage

Run scripts in order:

```bash
bash scripts/00_check_prereqs.sh
bash scripts/01_build_and_push_image.sh
bash scripts/02_run_phase0_5.sh
bash scripts/03_run_phase1.sh
```

## Cost Management

- Jobs use spot VMs for cost savings
- GPU allocation is per-job, resources are cleaned up after
- Monitor costs in Azure portal during development
- Use `--dry-run` flags to preview without executing

## Troubleshooting

Check job logs:
```bash
az container logs --name <job-name> -g <resource-group>
```

Monitor resource usage:
```bash
az monitor metrics list --resource <resource-id>
```

All commands are logged to `../../docs/run_log.md`.
