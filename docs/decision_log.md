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

## 2026-07-08 — GitHub sync decision for executable scaffold

Status: Ready to push

Decision:

- Phase 0.5 and Phase 1 executable scaffold is implemented locally.
- Required implementation files are present under `src/jspace_observation/`, `experiments/`, `tests/`, and `infra/azure/scripts/`.
- Tests passed with the Makefile target's underlying command: `python -m pytest tests/ -v` -> `41 passed, 2 warnings`.
- `make test` was attempted, but `make` is not installed in the current Windows environment.

Next decision:

- Run Phase 0.5 feasibility spike and Phase 1 dry run locally before Azure execution.
- Do not create Azure resources until local dry runs are inspected.

## 2026-07-08 — Correct strict no-CoT prefill ordering and Phase 1 defaults

Decision:

- R1-Distill strict no-CoT prompts must place the base question first, then the already-closed empty think block, then `Answer:`.
- Phase 1 default conditions must include `strict_answer_only`, `visible_cot`, and `r1_style_thinking`.
- The current Phase 0.5 script is explicitly classified as an availability/model-loading check only; it does not attempt actual tiny J-lens fitting.

Next decision:

- Run Phase 0.5 availability check and Phase 1 dry run locally before any Azure execution or Plan A feasibility decision.

## Phase 0.5 Run - 2026-07-08T18:13:38.361771
- Jacobian-lens installed: False
- Pre-fitted lens found: False
- Model loading check success for all models: False
- Actual tiny fitting attempted: no
- Actual tiny fitting success: not attempted
- Results: C:\Users\alanjiao\J-space-observation\results\runs\20260708_181325

## 2026-07-08 — Local validation completed

Status:

- Tests passed: yes (`41 passed, 2 warnings`)
- Phase 0.5 availability/model-loading check completed: yes
- Phase 1 dry run completed: yes
- Azure resources created: none

Phase 0.5 interpretation:

- Pre-fitted lenses were not found locally/configured.
- jacobian-lens is not installed/importable in the local environment.
- Model loading was attempted but failed for both configured models because `accelerate` is required for `device_map`.
- Actual tiny J-lens fitting was not attempted.
- This validation does not prove Plan A feasibility.

Next recommended step:

- Resolve the local `accelerate` dependency, then run a small real Phase 1 pilot with a single model and arithmetic only before any Azure execution or Plan A decision.
