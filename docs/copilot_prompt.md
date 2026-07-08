# Copilot 执行 Prompt

下面内容给 GitHub Copilot / Copilot Agent 使用。后续所有实验过程更新都必须由 Copilot 写回本仓库。

---

## 任务背景

你正在维护 GitHub 仓库：`Alanjiao1988/J-space-observation`。

本项目研究 DeepSeek-R1 蒸馏小模型是否将 reasoning 内化为 hidden workspace 表征，还是主要依赖显性 CoT token 作为外部草稿纸。

主路径是使用 Anthropic 开源的 Jacobian Lens，在 `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` 和 `Qwen/Qwen2.5-Math-1.5B` 上做 J-lens feasibility、behavioral depth gradient、workspace readout、activation patching 和 ablation DoD。

请严格按照 `docs/experiment_plan.md` 执行。

---

## 总体工作原则

1. 不提交模型权重。
2. 不提交 Azure credentials、Hugging Face token、GitHub token 或任何 secret。
3. 不把普通 logit lens 结果写成 J-space observation。
4. 不把 prompt-based answer-only 等同于 strict structural no-CoT。
5. 不把 motor/output 末层 readout 当作 hidden reasoning 证据。
6. 所有实验运行必须写入 `docs/run_log.md`。
7. 所有设计变更或阶段进入/停止决策必须写入 `docs/decision_log.md`。
8. 每次实验必须在 `results/runs/<timestamp>/metadata.json` 保存元数据。
9. 每次 Copilot 执行后必须提交 commit，并在提交信息中写明阶段和变更。
10. 如果运行 Azure 资源，必须记录资源名、区域、SKU、启动时间、停止/清理状态。

---

## 立即执行任务

请不要继续扩展设计文档。现在进入实证前置阶段。

### Step 1：准备项目脚手架

创建或更新：

- `pyproject.toml`
- `requirements.txt`
- `Dockerfile`
- `src/jspace_observation/`
- `experiments/phase0_5_jlens_spike.py`
- `experiments/phase1_depth_gradient.py`
- `data/prompts/`
- `infra/azure/`
- `reports/`

要求：

- Python 3.11。
- 主要依赖包括 PyTorch、Transformers、Accelerate、Safetensors、Pandas、Numpy、Matplotlib、Scikit-learn、Typer、Rich。
- 研究容器以 PyTorch CUDA 镜像为基础。
- 不使用 vLLM / Ollama 作为机制实验主框架。

提交：

```text
Add executable project scaffold for J-lens experiments
```

---

### Step 2：实现 Phase 0.5 J-lens feasibility and saturation spike

文件：

- `experiments/phase0_5_jlens_spike.py`
- `src/jspace_observation/jlens_utils.py`
- `src/jspace_observation/model_loader.py`
- `src/jspace_observation/run_logging.py`

功能：

1. 搜索或记录是否存在目标模型的预拟合 J-lens artifact。
2. 如果没有预拟合 lens，使用 `anthropics/jacobian-lens` 做 tiny fitting。
3. 支持 sweep：
   - prompt_count：10 / 25 / 50 / 100；
   - sequence_length：64 / 128；
   - layer subset：single layer / selected layers / all feasible layers；
   - sampled positions，如果库支持。
4. 记录 wall-clock time、peak GPU memory、错误、lens artifact 路径。
5. 用 sanity prompt 验证 lens 能输出 token ranking。
6. 输出 summary：是否继续 Plan A。

输出：

- `results/runs/<timestamp>/metadata.json`
- `results/runs/<timestamp>/jlens_spike_results.csv`
- `results/runs/<timestamp>/jlens_validation_examples.jsonl`
- `results/runs/<timestamp>/summary.md`

提交：

```text
Implement Phase 0.5 J-lens feasibility spike
```

---

### Step 3：实现 Phase 1 behavioral reasoning-depth gradient

文件：

- `experiments/phase1_depth_gradient.py`
- `src/jspace_observation/prompt_sets.py`
- `src/jspace_observation/no_cot.py`
- `src/jspace_observation/eval_parsing.py`
- `src/jspace_observation/stats.py`

模型：

- `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
- `Qwen/Qwen2.5-Math-1.5B`

任务族：

1. arithmetic depth gradient：1-op / 2-op / 3-op / optional 4-op。
2. synthetic relation depth gradient：1-hop / 2-hop / 3-hop，所有事实在 prompt 中提供。
3. factual / counterfactual depth gradient：1-hop / 2-hop / counterfactual。

Prompt conditions：

- `strict_answer_only`
- `visible_cot`
- `r1_style_thinking`

strict no-CoT 要求：

- R1-Distill 主方法是 empty-think prefill。
- Qwen2.5-Math 使用普通 strict answer-only + max token / stop rules。
- 每条 generation 记录 `no_cot_method`、`no_cot_validity`、invalid reason。

指标：

- accuracy；
- parse validity；
- output length；
- token count；
- latency；
- error type；
- `CoT_gain_by_depth`；
- `CoT_gain_slope`；
- `answer_only_degradation_slope`；
- Wilson CI。

输出：

- `results/runs/<timestamp>/phase1_generations.jsonl`
- `results/runs/<timestamp>/phase1_metrics.csv`
- `results/runs/<timestamp>/phase1_depth_gradient_summary.md`
- figures：accuracy by depth、CoT gain by depth、answer-only degradation。

提交：

```text
Implement Phase 1 reasoning-depth gradient
```

---

## 后续实验过程更新要求

每完成一个实验阶段，Copilot 必须更新：

1. `docs/run_log.md`
   - 命令；
   - Azure 资源；
   - 模型；
   - 参数；
   - 运行时间；
   - 结果目录；
   - 错误。

2. `docs/decision_log.md`
   - 是否进入下一阶段；
   - 是否继续 Plan A；
   - 是否触发 Plan B；
   - 是否需要调整任务难度；
   - 是否需要跑 7B scale-anchor。

3. `reports/current_status.md`
   - 当前阶段；
   - 主要发现；
   - 阻塞项；
   - 下一步。

4. `README.md`
   - Current status 简短更新。

5. 如有实验输出，必须写入 `results/runs/<timestamp>/summary.md`。

---

## 给执行者的停止规则

如果遇到以下情况，请停止并记录，不要自行扩大范围：

1. J-lens fitting 显存失败。
2. Azure GPU quota 不足。
3. strict no-CoT 大量 invalid。
4. answer-only accuracy 在某任务族贴近随机。
5. 任何任务结果可能导致当前结论被能力差、知识差或 CoT 冗余性污染。

停止后更新 `docs/decision_log.md`，等待 Alan 根据结果决定。
