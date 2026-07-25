# J-space observation

本仓库用于执行一个面向 DeepSeek-R1 蒸馏小模型的机制可解释性实验：观察 R1 蒸馏模型是否在严格 no-CoT / answer-only 条件下形成可读、可干预、具有因果作用的 hidden workspace 表征。

## 当前研究问题

核心问题：**R1 蒸馏模型的 reasoning 能力是被内化到模型内部 workspace，还是主要依赖显性 CoT token 作为外部草稿纸？**

本项目以 Anthropic 2026 年 J-lens / J-space 论文为方法基线，主路径优先使用真实 Jacobian Lens，而不是普通 logit lens 或 tuned lens。

## 当前阶段

当前已完成四条关键路径的首个可执行阶段：

1. Phase 0.5A 在单张 Tesla T4 上完成真实 Jacobian Lens 技术可行性验证，结论为 **GREEN（仅限技术可行性）**。
2. Phase 1 历史 bounded `n=3` 结果保持冻结；不授权 higher-n 扩展。
3. Prospective parser v2 已仅使用 60 条公开 development cases 完成并冻结；一次性 locked evaluation 已于 2026-07-25 执行并关闭，正式结论为 **FAIL**（34 条强制 gate 中 32 条通过，`boxed_final_miss` 与 `wrong_span` 未通过），120 条 private locked holdout 已作废退役。
4. No-CoT taxonomy v2 与 450-item capability/headroom candidate bank 已完成，但未执行新的行为校准。

一次性 parser-v2 locked evaluation 这个注册 gate 已经用尽：该 holdout 不得重用、重评或重读。任何修改后的 parser 必须先重建并密封新的 locked holdout，再另行授权评估。完整结果与全部工件哈希见 [parser-v2 locked evaluation 报告](reports/phase1_parser_v2_locked_evaluation.md)。

该评估属于 evaluator validation，不是 model evaluation：全程未下载、未加载、未运行目标模型，也未使用 GPU。Phase 0.5A 的 GREEN 不代表 lens scientific quality，也不构成 hidden reasoning、internal workspace 或 J-space evidence。

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
- [Phase 0.5A real J-lens feasibility report](reports/phase05_jlens_feasibility.md)
- [Parser-v2 locked evaluation formal result](reports/phase1_parser_v2_locked_evaluation.md)
