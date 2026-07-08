# J-space Observation

This repository studies whether `DeepSeek-R1-Distill-Qwen-1.5B` internalizes reasoning as hidden, J-space-like representations when prompted for answers only.

## Research boundary

This is not a full Anthropic J-space replication. Phase 1 is a J-space-inspired hidden reasoning probe focused on internal activations under no-CoT / answer-only prompting.

The key difference from prior visible-reasoning-token work is that this project does not analyze generated chains of thought. Instead, it probes hidden representations while the model is constrained to answer-only behavior.

## Phase 1 question

Can answer-only prompts induce separable hidden representations that correlate with reasoning steps, task structure, or answer correctness in `DeepSeek-R1-Distill-Qwen-1.5B`?

## Initial scaffold

```text
docs/                 Research plans, logs, decisions, and runbooks
src/jspace_observation/ Python package for probes and analysis code
experiments/          Experiment entrypoints and notebooks/scripts
data/prompts/         Prompt sets and task definitions
results/              Generated outputs and run metadata
infra/azure/          Azure deployment and execution assets
```

## Project policies

- Do not commit model weights.
- Do not commit Azure credentials, secrets, tokens, or `.env` files.
- Every Azure command must be recorded in `docs/run_log.md`.
- Every experiment run must save a `metadata.json` file.
- Every phase decision must be recorded in `docs/decision_log.md`.

## Reproducibility expectations

Each experiment should record:

- model identifier and revision
- prompt set and prompt format
- answer-only / no-CoT instruction template
- activation capture points
- random seeds
- environment details
- output path
- `metadata.json` path

## Status

Phase 1 scaffold initialized. No experiments have been run yet.
