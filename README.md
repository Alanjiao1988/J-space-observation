# J-space observation

本仓库研究 DeepSeek-R1 蒸馏小模型是否形成可观察、可干预、具有因果作用的内部推理状态。项目现已明确划分为两个相互隔离的研究：已经关闭的 **Study 1**，以及已完成 Stage P 前瞻性冻结、等待独立 tokenizer gate 授权的 **Study 2**。

## 当前状态

| Study | 状态 | 结论边界 | 入口 |
|---|---|---|---|
| Study 1 | `CLOSED / INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` | 工程链和证据封存完成，但原始科学问题未被检验 | [Study 1 总结](studies/study1/README.md) |
| Study 2 | `PROTOCOL_FROZEN / AWAITING_STAGE_T_AUTHORITY` | 协议、Gate A 与公开确定性 banks 已冻结；尚无 tokenizer、模型、lens、activation 或科学结果 | [Study 2 入口](studies/study2/README.md) |

Study 1 的终态基线是 commit `6409d2c6d665187e4459d94d490a20d7b085e8af`、tree `bc8b80cb0e66f9426dcdedd52b624c892caa3fc9`。旧文件保持原路径和原字节；新的 `studies/study1/` 只是索引层，不重写历史证据。

## Study 1 的诚实结论

Study 1 最终测得的是：在冻结的 raw-completion、无 chat template、无生成式 CoT、greedy clean next-token 接口下，官方公开任务只能产生 2/93 multihop、2/55 order-ops 和 5/90 causal-swap 个行为合格项。冻结的 development-first split 因而留下 0 个 confirmation item，S3 在 lens 被读取之前停止。

因此 Study 1：

- 没有验证或否定 A600、B600、M1200；
- 没有检验 hidden reasoning、internal workspace 或 J-space；
- 没有回答“蒸馏是否传递了真正 reasoning”这一原始问题；
- 不能通过回填、替换样本、修改 prompt、扩大答案表面、降低阈值或第二次 E0 来修补。

Phase 1.0D 仍作为独立历史子状态保留为 `BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`。它不属于 Study 2 的授权范围，Study 2 也不能恢复或修改它。

完整证据见 [Study 1 最终 handoff](docs/jlens_s2_s3_e0_final_handoff.md) 与 [机器可读终态清单](studies/study1/terminal_manifest.json)。

## Study 2 的研究问题

Study 2 重新对齐原始问题，并把“真正 reasoning”限定为可证伪的操作性命题：

> R1-distilled checkpoint 是否会在零个生成式 reasoning token 的单次前向传播中，计算并因果使用一个由任务定义的中间变量；这种行为或机制是否强于其 lineage base 与同族 instruction-tuned control？

主实验不要求模型开放式生成答案。它读取同一答案位置上的四个候选 logit，并使用程序可验证的合成组合任务。主要机制检验把 donor 的中间状态移入 recipient，同时要求模型转向第三个“重组答案” `g_recipient(m_donor)`；该答案与 donor、recipient 原答案均不同，从而排除简单复制 donor 最终答案或选项标签。

Study 2 的 claim ceiling 是：

> 目标 checkpoint 在受控的 no-generated-trace 接口下，使用一个具有因果负载的中间变量解决新的组合任务。

只有与两个固定对照都通过前瞻性比较后，才能进一步使用 checkpoint-level 的“distillation-associated”表述；不能据此识别具体训练样本、损失项或 teacher trace 的因果作用。

## Study 2 阶段

| 阶段 | 内容 | 当前状态 |
|---|---|---|
| P | 协议、合成任务库、方法审查与冻结 | `COMPLETE / FROZEN_AWAITING_STAGE_T` |
| T | tokenizer、模型身份及 token-alignment gate | 未授权 |
| B-D / B-C | 行为 development / confirmation | 未授权 |
| M-D / M-C | 机制定位 / confirmation | 未授权 |

Stage P 已严格保持 model-free，并在唯一一次有界方法学审查后冻结。新增的 Gate A 要求未来在 Stage T 之后、打开 B-C 之前，以固定 development rows 对两个任务族分别执行一次 target-only 组合能力 gate；失败只能关闭当前协议版本，不能在同一版本换题、回填或改阈值。Stage P 的设计文件不是经验性证据，`paper/evidence_ledger.csv` 仍止于 `EV-0016`。Stage T 尚未授权。

## 固定模型身份

| 角色 | 模型 | revision |
|---|---|---|
| Target | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| Lineage base | `Qwen/Qwen2.5-Math-1.5B` | `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2` |
| Instruction control | `Qwen/Qwen2.5-Math-1.5B-Instruct` | `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35` |
| J-lens source | `anthropics/jacobian-lens` | `581d398613e5602a5af361e1c34d3a92ea82ba8e` |

## 目录入口

- [研究总索引](studies/README.md)
- [Study 1 总结与限制](studies/study1/README.md)
- [Study 1 权威资产索引](studies/study1/asset_index.csv)
- [Study 2 研究章程](studies/study2/RESEARCH_CHARTER.md)
- [Study 2 机器可读章程](studies/study2/study2_charter.json)
- [Study 2 下一线程 handoff](studies/study2/NEXT_THREAD_HANDOFF.md)
- [Study 2 冻结协议](studies/study2/protocol/reasoning_internalization_protocol.md)
- [Study 2 Stage P freeze decision](studies/study2/decisions/reasoning_internalization_protocol_freeze.md)
- [Study 2 Stage P final handoff](studies/study2/STAGE_P_FINAL_HANDOFF.md)
- [全局决策日志](docs/decision_log.md)
- [全局运行日志](docs/run_log.md)
- [Claim–evidence matrix](paper/claim_evidence_matrix.md)

## 不可跨越的边界

- Study 1 的终态、receipts、ledgers、artifact packs 和 protected bytes 不得因 Study 2 被重写或重新解释。
- Study 2 使用新的 namespace、authority、task banks、IDs 和终态；它不是 S3 v1 的 rerun 或 rescue。
- J-lens readout 不能替代 lens-independent causal evidence；既有 M1200 在 Study 2 中只能作为 target-only 次级轴。
- 自动 parser 不能成为生成文本的权威科学标签；Study 2 主路径通过数值 logits 与程序 ground truth 避免该依赖。
- operational blocker 不能被写成科学阴性结论；完整科学阴性也不能靠事后换任务、阈值、层或样本来修复。
