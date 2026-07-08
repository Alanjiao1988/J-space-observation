# Implementation Notes

## 1. strict no-CoT

对 R1-Distill，strict no-CoT 主方法是 empty-think prefill：

```text
<think>
</think>

```

然后让模型只生成最终答案。

不要优先使用 logit mask ban `<think>`，因为这会把 R1 蒸馏模型推到分布外，或让它用无标签散文继续推理。

对 Qwen2.5-Math，默认不用 empty-think prefill，而用普通 strict answer-only prompt、max_new_tokens、stopping rules 和 visible-reasoning validation。

每条 generation 必须记录：

- no_cot_method；
- no_cot_validity；
- reason_for_invalidity。

只有 no_cot_validity=true 的 strict no-CoT 样本，能支持 hidden reasoning 结论。

## 2. Phase 5 headroom gate

Phase 5 ablation DoD 只能在 Phase 1 中 strict_answer_only baseline 显著高于 floor 的 cell 上运行。

如果 baseline 接近地板，DoD null 没有解释力，不能写成无 workspace。

## 3. RQ3 probe generalization

RQ3 的 probe 必须跨模板泛化。

同模板 train/test split 不够。必须至少有：

- train template family；
- held-out template family；
- cross-template metrics。

如果 probe 只在原模板工作，不能证明稳定概念表征。

## 4. Motor layer 排除

最后一层或 motor band 出现目标 token，通常是 output preparation，不是 hidden workspace 证据。

必须先经验识别 layer taxonomy，再解释 workspace-layer readout。

## 5. 运行记录

所有 Azure 命令、实验命令、运行结果、错误、资源清理状态都必须写入 `docs/run_log.md`。
