# J-space observation 实验方案

## 0. 项目定位

本项目研究 DeepSeek-R1 蒸馏小模型是否将 reasoning 内化为 hidden workspace 表征，还是主要依赖显性 CoT token 作为外部草稿纸。

核心对比不是“模型会不会输出 CoT”，而是：

> 在严格 no-CoT / answer-only 条件下，模型内部是否仍然形成可读、可干预、对最终答案有因果作用的 hidden workspace 表征？

本项目主路径使用 Anthropic 开源的 Jacobian Lens 方法，目标是尽可能做真实 J-lens / J-space observation。普通 logit lens、target-token probe 和 activation patching 可以作为 debug、fallback 或独立因果证据，但不能替代真实 J-lens 结论。

---

## 1. Project headline gate：Plan A / Plan B

### Plan A：强 J-space 结论路径

Plan A 是主路径。

要求：

1. 能加载或拟合目标模型的真实 Jacobian Lens。
2. 能通过 lens sanity checks。
3. 能在 answer-only 条件下观察 workspace 层中的中间概念 readout。
4. 能通过 activation patching 和 ablation DoD 做因果验证。

只有 Plan A 成功时，才可以使用“J-space observation”或“internal workspace observation”这种强表述。

### Plan B：弱机制证据路径

Plan B 只是保险，不提前投入过多脚手架。

触发条件：

1. 没有目标模型的预拟合 J-lens。
2. T4 上无法拟合可用 J-lens。
3. A100 子集仍不可行，或预算不允许。

Plan B 结论只能写为：

> logit lens、target probe 和 activation patching 提供了 hidden reasoning representation 的弱机制证据。

Plan B 不能声称完成直接 J-space observation。

---

## 2. 研究问题

### RQ1：显性 CoT 的行为收益是否随推理深度上升？

通过 reasoning-depth gradient 衡量：

- answer-only accuracy 是否随深度快速下降；
- visible-CoT 是否更稳；
- CoT gain 是否随深度单调上升。

这是一条便宜但信息量很高的行为先验。如果 CoT gain slope 很陡，说明模型可能更依赖外部 token 草稿纸。

### RQ2：R1-Distill 在 strict no-CoT 下是否存在 hidden workspace 表征？

主方法：真实 J-lens readout。

重点不是最终答案在末层出现，而是：

- 中间实体 / 中间概念是否在经验识别出的 workspace 层出现；
- readout 是否不是 prompt echo；
- readout 是否不是只在 motor/output 层出现；
- readout 是否能与 patching causal heatmap 对齐。

### RQ3：蒸馏是否改变了内部表征？

RQ3 必须避免能力差和知识差混淆。

主证据不以两个模型各自 J-lens 的 readout strength 为主，因为两个模型会有两个不同 lens。RQ3 的主仪器是 lens-independent 方法：

1. activation patching effect size；
2. cross-template target-token linear probe。

J-lens readout 只作为佐证。

RQ3 只在 ability-matched 任务子集上解释。

### RQ4：hidden workspace 是否具有因果作用？

通过 activation patching 和 ablation DoD 验证。

核心不是观察到内部概念，而是证明：

> 扰动 workspace 相关内部状态，会在控制组之外显著损伤 strict answer-only 表现。

---

## 3. 模型

### 主模型

- `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`

### 主对照模型

- `Qwen/Qwen2.5-Math-1.5B`

### 可选尺度锚点

- `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`

7B 只在 1.5B pipeline 稳定后，用小子集测试尺度混淆。

---

## 4. Prompt / no-CoT 条件

前瞻记录使用 branch taxonomy `v2`；缺失版本的历史记录按 `v1` 读取。完整 crosswalk 和记录字段见 `docs/phase1_no_cot_conditions.md`。

### 4.1 visible_cot

允许模型显式输出推理步骤。

### 4.2 r1_style_thinking

使用 R1 风格 `<think>...</think>` 输出。

### 4.3 strict_answer_only

这是模型无关的 prompt-only raw strict 条件，对所有模型使用同一个 answer-only prompt，prompt 中不含 think tags，也不按模型名切换策略。它映射到 `prompt_only_raw_strict`，是唯一可用于最强 spontaneous surface no-CoT 讨论的条件；行为结果本身仍不能证明 hidden reasoning。

### 4.4 strict_answer_only_prefill_answer

answer-prefix prefill 干预，映射到 `prefill_intervention`，不能当作 raw 或 spontaneous 行为。

### 4.5 strict_answer_only_empty_think_prefill

显式的 structural prefill 干预；只由该 condition 选择，绝不按模型名路由。raw assistant prefill 严格为：

格式：

```text
<think>
</think>

```

tokenizer-only metadata helper 必须使用传入 tokenizer/chat template 记录 raw prefill、rendered chat text、token IDs、decoded tokens 与 assistant-prefix boundary，且生成使用捕获的 token IDs。

该条件映射到 `prefill_intervention`。它最多支持 structural suppression 下的 internal-representation study，不能支持 spontaneous hidden reasoning。前瞻 `prefill_intervention` 没有 preregistered success criteria，分类必须为 `not_applicable` / `NA`。

### 4.6 strict_answer_only_stopped

prompt-only 输入上的 generation-time stop 干预，映射到 `stopped_intervention`。stopped validity 不代表 spontaneous validity。

### 4.7 strict_answer_only_postprocessed

prompt-only raw 输出上的 post-hoc utility 操作，映射到 `postprocessed_utility`，只衡量 answer recovery。

所有 generation 必须记录：

- `branch_taxonomy_version`
- `legacy_phase1_branch`
- `prospective_phase1_branch`
- deprecated `phase1_branch`（始终等于 `legacy_phase1_branch`）
- `no_cot_method`
- `no_cot_validity`
- `reason_for_invalidity`
- 是否出现 think tag
- 是否出现显式中间步骤
- 是否超过 token budget

只有满足设计边界的有效记录才可进入后续机制分析；任何 Phase 1 行为条件本身都不能支持 hidden reasoning 结论。

---

## 5. 任务集

### 5.1 Phase 1 深度梯度任务

#### A. Arithmetic depth gradient

- 1-op
- 2-op
- 3-op
- 可选 4-op

#### B. Synthetic relation depth gradient

所有事实都在 prompt 中提供，避免世界知识差异。

- 1-hop synthetic relation
- 2-hop synthetic relation
- 3-hop synthetic relation

#### C. Factual / counterfactual depth gradient

- 1-hop factual
- 2-hop factual
- 2-hop counterfactual
- 可选 3-hop factual / counterfactual

### 5.2 RQ2 主任务

RQ2 用于观察 R1-Distill 是否有 hidden workspace。主任务是更适合 J-lens readout 的任务：

- two-hop factual reasoning
- counterfactual entity replacement
- wrong-CoT / error-detection
- synthetic relation tasks with all facts in prompt

算术任务可以作为 sanity check 和 activation patching 任务，但不作为 RQ2 lens readout 的唯一主证据。

### 5.3 RQ3 主任务

RQ3 用于比较 distill vs base，必须使用 ability-matched 任务：

- 两模型都能做的算术任务；
- facts fully provided 的 synthetic relation；
- 两模型都答对的 two-hop 子集；
- 行为准确率接近的任务 cell。

如果 R1-Distill 在 factual two-hop 上强于 Qwen2.5-Math，不能直接解释为 workspace 更强，必须标记为 knowledge/ability-confounded。

---

## 6. Phase 0.5：J-lens feasibility and saturation spike

这是第一个实证步骤。

目标不是完整实验，而是判断 Plan A 是否可行。

### 6.1 预拟合 lens 搜索

先搜索：

- Hugging Face
- Neuronpedia
- GitHub releases

目标模型：

- `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
- `Qwen/Qwen2.5-Math-1.5B`

如果存在精确匹配 lens，先加载并验证。

### 6.2 tiny fitting

如果没有预拟合 lens，使用 `anthropics/jacobian-lens` 拟合 tiny lens。

注意：J-lens 不是 tuned lens。它估计期望 Jacobian，成本主要来自模型 backward pass。

### 6.3 saturation / cost sweep

扫描旋钮：

- prompt_count：10 / 25 / 50 / 100；
- sequence_length：64 / 128；
- sampled positions，如果实现支持；
- layer subset：单层 / 多层 / 全层。

不要寻找不存在的 rank/probe 旋钮，除非实现显式暴露。

### 6.4 记录

必须记录：

- wall-clock time；
- peak GPU memory；
- prompt count；
- sequence length；
- layer subset；
- error / failure mode；
- validation readout examples。

### 6.5 Phase 0.5 决策

- 如果 T4 上 100-prompt fitting 可行，继续 Plan A。
- 如果 T4 慢但可运行，继续 Plan A，用 sliced fitting / merge。
- 如果 T4 内存失败，预算允许时跑 A100 小子集。
- 如果 A100 不可用或仍失败，触发 Plan B。

---

## 7. Phase 1：Behavioral reasoning-depth gradient

Phase 1 必须在昂贵解释实验之前执行。

### 7.1 指标

按 model × task family × depth × prompt condition 记录：

- accuracy；
- parse validity；
- output length；
- generated tokens；
- latency；
- error type；
- strict no-CoT validity。

### 7.2 深度梯度指标

- `answer_only_accuracy_by_depth`
- `visible_cot_accuracy_by_depth`
- `r1_style_accuracy_by_depth`
- `CoT_gain_by_depth = visible_cot_accuracy - strict_answer_only_accuracy`
- `CoT_gain_slope`
- `answer_only_degradation_slope`

### 7.3 解释

- answer-only 随深度陡降、CoT 稳定：支持“外部 token 草稿纸依赖”假设。
- answer-only 随深度仍稳：支持“内部推理可能已内化”假设。

这是行为证据，不等于 J-space 证据。

### 7.4 能力地板规则

所有 sanity check 必须按 model × task type × depth 粒度做。

如果某个 cell 的 strict answer-only 接近随机，后续 hidden workspace 阴性结果不可解释。

---

## 8. Phase 1.5：Layer taxonomy characterization

不要预设 1.5B 模型一定存在 sensory / workspace / motor 三段结构。

必须从模型 config 读取实际层数，使用 zero-based layer index。

### 8.1 目标

经验识别：

- prompt-echo / sensory-like layers；
- candidate workspace layers；
- motor / output-adjacent layers。

### 8.2 指标

- J-lens readout coherence；
- prompt echo dominance；
- next-token / final-answer dominance；
- intermediate-concept stability；
- readout peaks 与 activation patching causal peaks 是否对齐。

在 Phase 1.5 输出候选 workspace 层之前，不做 workspace-layer 强结论。

---

## 9. Phase 2：J-lens workspace readout

RQ2 主阶段。

### 9.1 核心证据

- 中间概念出现在 empirically identified candidate workspace layers；
- 不只出现在 motor/output layers；
- 不是 prompt echo；
- 相对 unrelated concept controls 具有特异性；
- 出现在 behaviorally successful strict no-CoT runs。

### 9.2 不作为强证据

- 最终答案只在末层出现；
- target token 只在输出前出现；
- motor band 的 output preparation effect。

Logit lens 只作为 debug / fallback，不作为最终 J-space 证据。

---

## 10. Phase 3：Base vs Distill 表征对比

RQ3 主阶段。

### 10.1 Ability matching gate

每个 task family / depth / item subset 先分类：

- ability-matched；
- base weaker / knowledge-confounded；
- distill weaker；
- both below floor。

只有 ability-matched 子集可以支持 RQ3 主结论。

### 10.2 RQ3 主仪器

主仪器不依赖 J-lens：

1. activation patching effect size；
2. cross-template target-token linear probe。

J-lens readout 是 supporting evidence。

### 10.3 Probe 泛化要求

Probe 必须跨模板泛化，不能只跨 item。

最低要求：

- train on one template family；
- evaluate on held-out template family。

示例：

- 在 geography factual template 训练 France probe；
- 在 counterfactual template 评估 France readout；
- 在 synthetic relation template A 训练；
- 在 synthetic relation template B 评估。

如果 probe 只在同模板有效，不能作为稳定概念表示证据。

---

## 11. Phase 4：Activation patching

Phase 4 需要 layer × position 系统扫描。

### 11.1 设计

对 clean/corrupted pair：

- 保存 clean run activations；
- 在 corrupted run 中逐层逐位置 patch；
- 输出 causal heatmap。

### 11.2 控制组

必须包括：

- random patch control；
- wrong-layer control；
- wrong-position control；
- matched-norm perturbation control。

### 11.3 交叉验证

核心卖点：

> J-lens readout peak layer/position 是否与 activation patching causal peak 对齐？

如果不对齐，不做强 workspace 结论。

---

## 12. Phase 5：J-space ablation DoD

Phase 5 是因果主实验之一。

### 12.1 Headroom gate

Phase 5 只在 Phase 1 中 strict_answer_only baseline 有足够 headroom 的 cell 上运行。

必须记录：

- baseline_accuracy；
- floor_accuracy；
- Wilson CI；
- baseline_headroom_pass；
- correct baseline case count；
- skipped reason。

如果 baseline 接近地板，DoD null 不能解释为无 workspace。

### 12.2 Primary DoD

对 strict answer-only：

```text
Damage_Jspace = Accuracy_baseline - Accuracy_JspaceAblated
Damage_control = Accuracy_baseline - Accuracy_controlAblated
DoD_answer_only = Damage_Jspace - Damage_control
```

证据标准：

- `DoD_answer_only > 0`；
- confidence interval excludes zero；
- 受影响层/位置与 J-lens readout 和 activation patching peaks 对齐。

### 12.3 控制组

- matched-norm random direction ablation；
- random subspace ablation；
- non-workspace layer ablation；
- wrong-position ablation；
- motor-layer ablation。

### 12.4 CoT 对比

visible-CoT 比较是次要分析。不能用裸 answer-only vs CoT 鲁棒性差异作为证据，因为 CoT 有冗余和外部草稿纸效应。

---

## 13. 统计要求

所有 rates：

- Wilson confidence interval。

所有连续效应：

- bootstrap confidence interval。

所有 patching / ablation：

- 必须相对控制组报告 effect size；
- 不报告裸效应作为结论。

样本量：

- pilot 可小；
- 主结论每个 task family × depth 尽量 50–100 items。

---

## 14. 尺度混淆预注册

未在 1.5B 上观察到 workspace，可能是尺度问题，不是蒸馏没有内化推理。

可选尺度锚点：

- `DeepSeek-R1-Distill-Qwen-7B`；
- 小子集；
- 只在 1.5B pipeline 稳定后运行。

---

## 15. 结论模板

### Strong conclusion

需要同时满足：

- usable real J-lens；
- strict no-CoT 行为能力高于地板；
- empirical workspace layer taxonomy；
- workspace 层 readout 中间概念；
- RQ3 在 ability-matched 任务上成立；
- activation patching 与 J-lens 对齐；
- ablation DoD 显著高于控制组。

### Medium conclusion

存在 hidden representation 证据，但 J-lens 质量、能力对齐或因果验证不完整。

### Weak / Plan B conclusion

logit lens / probe / patching 提供 hidden reasoning representation 的弱证据，但不是直接 J-space observation。

---

## 16. 立即执行优先级

停止继续纸面设计。

下一步只跑：

1. Phase 0.5 J-lens feasibility and saturation spike。
2. Phase 1 behavioral reasoning-depth gradient。

根据结果决定：

- full Plan A J-lens runs；
- RQ3 ability-matched patching/probe；
- 7B scale-anchor subset。
