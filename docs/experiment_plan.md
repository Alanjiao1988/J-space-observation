# Experiment Plan

## Scope

Phase 1 is a J-space-inspired hidden reasoning probe for `DeepSeek-R1-Distill-Qwen-1.5B` under no-CoT / answer-only prompts.

This project must not be described as a full Anthropic J-space replication. It uses J-space as inspiration for probing latent reasoning-like structure in hidden states, not as a claim of reproducing the original method or findings.

## Core contrast

Prior work emphasized visible reasoning tokens and chain-of-thought text. This project studies hidden model representations when the model is asked not to produce reasoning text.

## Initial research questions

1. Do hidden states differ systematically between reasoning tasks and shallow answer-recall tasks under answer-only prompts?
2. Are hidden-state trajectories predictive of final answer correctness?
3. Do intermediate layers contain separable task or solution-state information despite no visible reasoning tokens?
4. Are observed structures robust across prompt templates and task families?

## Phase 1 design

### Model

- `DeepSeek-R1-Distill-Qwen-1.5B`
- Use a pinned model revision when running experiments.
- Do not commit model weights or tokenizer artifacts.

### Prompting condition

- No-CoT / answer-only prompts.
- The prompt must explicitly request only the final answer.
- Generated chain-of-thought text should not be collected or analyzed.

### Task families

- arithmetic and symbolic reasoning
- logical consistency checks
- short mathematical word problems
- controlled non-reasoning baselines

### Measurements

- hidden states by layer and token position
- final answer correctness
- prompt family and template id
- activation summary features
- optional low-dimensional projections for exploratory visualization

### Required run artifact

Every experiment run must save `metadata.json` containing at least:

- run id
- timestamp
- git commit hash
- model id and revision
- prompt set id
- prompt template id
- answer-only instruction
- hardware and runtime environment
- activation capture configuration
- output directory
- command used

## Success criteria

Phase 1 succeeds if it produces a reproducible probe pipeline and evidence-quality plots or tables that can distinguish meaningful hidden-state structure from prompt/template artifacts.

## Non-goals

- Claiming full Anthropic J-space replication.
- Training or distributing model weights.
- Inferring private or unobservable chain-of-thought text.
- Treating exploratory projections as causal proof of reasoning.
