# J-space observation

本仓库用于执行一个面向 DeepSeek-R1 蒸馏小模型的机制可解释性实验：观察 R1 蒸馏模型是否在严格 no-CoT / answer-only 条件下形成可读、可干预、具有因果作用的 hidden workspace 表征。

## 当前研究问题

核心问题：**R1 蒸馏模型的 reasoning 能力是被内化到模型内部 workspace，还是主要依赖显性 CoT token 作为外部草稿纸？**

本项目以 Anthropic 2026 年 J-lens / J-space 论文为方法基线，主路径优先使用真实 Jacobian Lens，而不是普通 logit lens 或 tuned lens。

## 当前阶段

当前阶段只做文档与执行计划初始化。下一步由 GitHub Copilot / Copilot Agent 执行：

1. Phase 0.5：J-lens feasibility and saturation spike。
2. Phase 1：behavioral reasoning-depth gradient。

后续所有实验过程、Azure 资源创建、运行结果、错误、决策和结论更新，都必须由 Copilot 写回本仓库文档。

## 重要边界

- 不把 prompt-based answer-only 等同于 strict no-CoT。
- 不把末层 motor/output 表示当作 hidden reasoning 证据。
- 不用裸 CoT vs answer-only 鲁棒性差异作为 ablation 结论。
- RQ3 的 base-vs-distill 比较必须在能力对齐任务上完成。
- 如果真实 J-lens 失败，只能降级为 hidden representation probe，不能声称完成 J-space observation。

## 文档入口

- [实验方案](docs/experiment_plan.md)
- [Copilot 执行 Prompt](docs/copilot_prompt.md)
- [Azure Runbook](docs/azure_runbook.md)
- [实现注记](docs/implementation_notes.md)
- [决策日志](docs/decision_log.md)
- [运行日志](docs/run_log.md)
- [文献笔记](docs/literature_notes.md)
