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

## 2026-07-08 — Executable scaffold implementation complete

Status: ✓ Implemented

What was built:

1. **Core modules** (src/jspace_observation/):
   - config.py: Model and experiment configuration
   - model_loader.py: HuggingFace model loading with device/dtype management
   - no_cot.py: Strict no-CoT utilities (empty-think prefill for R1-Distill, answer-only for Qwen)
   - prompt_sets.py: Pilot prompt generation with small datasets
   - eval_parsing.py: Numeric, entity, yes/no answer parsing
   - stats.py: Wilson CI and bootstrap confidence intervals
   - run_logging.py: Run directory creation and metadata tracking
   - jlens_utils.py: J-lens availability checking and reporting

2. **Experiment scripts**:
   - phase0_5_jlens_spike.py: J-lens feasibility check
   - phase1_depth_gradient.py: Behavioral depth gradient experiments

3. **Tests** (tests/):
   - test_no_cot.py: No-CoT validation tests
   - test_eval_parsing.py: Answer parsing tests
   - test_stats.py: Statistics utility tests
   - All tests pass without requiring model downloads

4. **Infrastructure** (infra/azure/):
   - Bash scripts for Azure job submission
   - Variables template for configuration
   - README with usage instructions

5. **Build automation**:
   - Makefile for common operations (install, test, run experiments)

Key decisions:

- No-CoT validation checks for think tags and visible reasoning patterns
- Pilot prompts kept small for rapid iteration
- Phase 0.5 prioritizes checking pre-fitted lens availability before attempting fitting
- Phase 1 focuses on behavioral metrics and does not yet attempt mechanistic interpretation
- All runs logged to docs/run_log.md and docs/decision_log.md

What remains:

- Actual Phase 0.5 execution (requires jacobian-lens package)
- Actual Phase 1 execution (generates behavioral metrics)
- Phase 1.5 layer taxonomy characterization
- Phase 2 J-lens workspace readout (if J-lens feasible)
- Phase 3 distill vs base comparison
- Phase 4 activation patching

How to proceed:

1. Test: `make test`
2. Local spike: `make phase0-5` or `make phase1-dry`
3. Full Phase 1: `make phase1`
4. Azure submission: `make azure-setup && make azure-phase0-5`
