# Literature Notes

## Anthropic 2026 — Verbalizable Representations Form a Global Workspace in Language Models

Key relevance:

- Defines J-lens and J-space.
- J-lens transports residual-stream vectors to final-layer basis through an average Jacobian and decodes with unembedding.
- J-space is a sparse set of verbalizable representations that can support internal reasoning, directed modulation, flexible generalization and causal intervention.
- Important distinction: workspace-like middle layers vs motor/output-adjacent final layers.

## anthropics/jacobian-lens

Key relevance:

- Open-source reference implementation for fitting and applying Jacobian Lenses.
- Supports fitting on prompts and merging sliced fits.
- Main cost is model backward passes.

## DeepSeek-R1 distillation release

Key relevance:

- DeepSeek released R1 distilled models based on Qwen and Llama families.
- Main model in this project: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- Baseline model: `Qwen/Qwen2.5-Math-1.5B`.

## From Reasoning to Answer

Key relevance:

- Existing work shows visible reasoning tokens in distilled DeepSeek R1 models contribute to final answer generation.
- This project differs by asking whether hidden workspace exists under strict no-CoT / answer-only conditions.

## Related activation patching / error detection work

Key relevance:

- Activation patching can provide lens-independent causal evidence.
- For RQ3, patching effect size is a primary instrument because model-specific J-lens readouts are not directly comparable across models.
