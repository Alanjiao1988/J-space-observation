# Azure Runbook

This runbook captures operational rules for Azure-backed experiments.

## Required logging

Every Azure command must be recorded in `docs/run_log.md`.

For each command, record:

- timestamp
- operator
- subscription or resource group alias
- command with secrets redacted
- purpose
- result

## Secret handling

- Do not commit Azure credentials, service principal secrets, tokens, or `.env` files.
- Use local environment variables, Azure managed identity, or a secure secret store.
- If a command emits a secret, redact it before adding the command or result to the run log.

## Suggested workflow

1. Select subscription and resource group.
2. Record the intended Azure command in `docs/run_log.md`.
3. Execute the command.
4. Update the run-log result.
5. Save experiment outputs under `results/` with a run-specific `metadata.json`.

## Placeholder resources

No Azure resources have been created by this scaffold.
