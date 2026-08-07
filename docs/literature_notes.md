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

## Study 2 Stage P design sources and boundaries

- The official DeepSeek-R1 model card identifies the 1.5B checkpoint's
  Qwen2.5-Math lineage and R1-generated fine-tuning context. It motivates both
  the lineage-base and same-family instruction controls, but does not identify
  a training-causal mechanism.
- *From Reasoning to Answer* and *Analysing Chain of Thought Dynamics* motivate
  separating visible supplied/generated traces from a no-generated-trace logit
  observable. They do not establish hidden computation in the fixed target.
- The J-lens workspace paper motivates matched readout and causal controls.
  *Observable Patterns Are Not Explanations* reinforces that decodability or
  geometry without intervention is not mechanism evidence.
- Study 2 therefore uses four-option restricted logits, exact programmatic
  ground truth, donor-recipient recombinant patching, cross-template probes,
  and target-only secondary M1200 diagnostics.

The protected four-scale Study 1 J-lens convergence trajectory is recorded only
as `EXPLORATORY_METHODS_OBSERVATION_AWAITING_CONTROLLED_VALIDATION`. No novelty,
publication-readiness, or causal `max_seq_len=128` claim is made. Any Claude
Study 1 failure analysis remains `ADVISORY_POST_HOC_METHODS_INPUT`, not
scientific evidence.
