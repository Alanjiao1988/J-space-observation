# Decision Log

## 2026-07-08 — Reset repository to final experiment plan

Decision:

- 删除既有仓库内容，用当前最终实验方案重建文档。
- Plan A 仍为主路径：使用真实 Jacobian Lens 做 J-space observation。
- Plan B 只作为保险路径：如果 J-lens 不可行，则降级为 hidden representation probe，不能声称直接 J-space observation。
- 立即执行优先级为：Phase 0.5 J-lens feasibility spike 和 Phase 1 behavioral reasoning-depth gradient。

Key constraints:

- R1-Distill strict no-CoT 主方法为 empty-think prefill。
- RQ3 主证据使用 lens-independent patching/probe。
- Phase 5 ablation 必须使用 DoD，并受 Phase 1 headroom gate 控制。
- Probe 必须跨模板泛化。

Next action:

- 由 GitHub Copilot / Copilot Agent 根据 `docs/copilot_prompt.md` 实现脚手架、Phase 0.5 和 Phase 1。
