# J-space observation

本仓库研究 DeepSeek-R1 蒸馏小模型是否形成可观察、可干预、具有因果作用的内部推理状态。项目现已明确划分为三个相互隔离的研究：已经关闭的 **Study 1**，同样已经关闭的 **Study 2**（protocol v1 在前瞻注册的 development feasibility gate 上失败），以及新建的 **Study 3**（仅为设计草案，等待 operator review）。Study 1 与 Study 2 都没有回答各自的原始科学问题；Study 3 尚未执行任何测量。

## 当前状态

| Study | 状态 | 结论边界 | 入口 |
|---|---|---|---|
| Study 1 | `CLOSED / INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` | 工程链和证据封存完成，但原始科学问题未被检验 | [Study 1 总结](studies/study1/README.md) |
| Study 2 | `CLOSED / STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY` | 前瞻注册的 Gate A 在 development 阶段失败；原始研究问题未被回答；B-C 与全部机制阶段从未打开 | [Study 2 终态清单](studies/study2/terminal_manifest.json) · [Study 2 终态 handoff](studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md) |
| Study 3 | `DESIGN DRAFT / STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW` | 仅为设计草案：未冻结、未授权执行、零模型操作、无 bank、无 seed、未选定 interface | [Study 3 索引](studies/study3/README.md) · [协议草案](studies/study3/protocol/interface_calibration_protocol_draft.md) · [operator 决策](studies/study3/NEXT_THREAD_HANDOFF.md) |

Study 3 是一个**设计状态**，不是结果。它把「响应与打分接口」本身当作被测对象，因为 Study 1 与 Study 2 都在不同程度上终止于工具层面的问题。Study 3 未修改、未重开、未重新解释 Study 1 或 Study 2 的任何冻结产物，也没有复用它们的任何 item identity、bank row、template outcome、confirmation content、seed 或结果。

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

## Study 2 的研究问题（未被回答）

Study 2 重新对齐原始问题，并把“真正 reasoning”限定为可证伪的操作性命题：

> R1-distilled checkpoint 是否会在零个生成式 reasoning token 的单次前向传播中，计算并因果使用一个由任务定义的中间变量；这种行为或机制是否强于其 lineage base 与同族 instruction-tuned control？

**该问题没有被回答。** protocol v1 实际测得的是一个远窄于此的问题：完整、完整性有效的四选一 / no-generated-trace 冻结接口，是否在冻结的 384 项 development bank 上通过了前瞻注册的 target-only feasibility gate。答案是否定的，因此协议在任何机制阶段之前关闭。

以下段落描述的是当时的**设计意图**，其机制部分从未执行：主实验不要求模型开放式生成答案。它读取同一答案位置上的四个候选 logit，并使用程序可验证的合成组合任务。主要机制检验把 donor 的中间状态移入 recipient，同时要求模型转向第三个“重组答案” `g_recipient(m_donor)`；该答案与 donor、recipient 原答案均不同，从而排除简单复制 donor 最终答案或选项标签。

Study 2 的 claim ceiling 是：

> 目标 checkpoint 在受控的 no-generated-trace 接口下，使用一个具有因果负载的中间变量解决新的组合任务。

该 claim ceiling 从未被触及。只有与两个固定对照都通过前瞻性比较后，才能进一步使用 checkpoint-level 的“distillation-associated”表述；由于 Gate A 失败，任何此类表述都不被支持。

## Study 2 阶段

| 阶段 | 内容 | 当前状态 |
|---|---|---|
| P | 协议、合成任务库、方法审查与冻结 | `COMPLETE / FROZEN` |
| T | tokenizer、模型身份及 token-alignment gate | `COMPLETE / SEALED` |
| B-D | 行为 development 执行与 Gate A | `COMPLETE / GATE_A_FAILED` |
| B-C | 行为 confirmation | 从未打开；在 protocol v1 下不可用 |
| M-D / M-C | 机制定位 / confirmation | 从未打开；在 protocol v1 下不可用 |

Stage P 严格保持 model-free 并在唯一一次有界方法学审查后冻结。Stage T 构造了三个 tokenizer、未加载任何模型权重，并封存了机制配对选择。Stage B-D 在三个注册 checkpoint 上完整执行了 384 项 development bank，产生 3,072 行行为数据，随后执行前瞻注册的 Gate A：`permutation_chain` 25/128（精确单侧上尾 `0.9403523926144965`）、`affine_mod10` 33/128（`0.4526854444021635`），两族均未达到冻结阈值 X ≥ 43，`overall_gate_pass = false`。按冻结规则，失败只能关闭当前协议版本，不能换题、回填、改阈值或用对照替代 target。

因此 Study 2：

- 没有回答“蒸馏 checkpoint 是否在零生成 token 的单次前向中计算并因果使用任务定义的中间变量”这一原始问题；
- 没有产生任何关于内部计算、因果机制、蒸馏差异、J-space 或 J-lens 的证据；
- 其 development 行为整体停留在四选一的 0.25 随机水平，且**无法区分“模型不具备该能力”与“接口不足以表达该能力”**；
- 没有向 `paper/evidence_ledger.csv` 增加任何证据行，该账本仍止于 `EV-0016`。

对照结果仅供描述、不具任何权威性；其中一个对照单元达到族阈值，但冻结规则只由两个 target 族决定，不得据此改写结论。任何后续尝试都必须是单独授权的新协议版本。

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
- [Study 2 终态清单（机器可读）](studies/study2/terminal_manifest.json)
- [Study 2 protocol v1 终态 handoff](studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md)
- [Study 2 Gate A 决策](studies/study2/decisions/study2_stage_bd_gate_a_decision.md)
- [Study 2 解释性勘误](studies/study2/decisions/study2_stage_bd_interpretation_erratum.md)
- [Study 2 事后描述性诊断（零权威）](studies/study2/analysis/stage_bd_posthoc_interface_diagnostic.md)
- [Study 2 Stage B-D final handoff](studies/study2/STAGE_BD_FINAL_HANDOFF.md)
- [Study 2 入口与阅读顺序](studies/study2/README.md)
- [全局决策日志](docs/decision_log.md)
- [全局运行日志](docs/run_log.md)
- [Claim–evidence matrix](paper/claim_evidence_matrix.md)

以下 Study 2 文件是研究开启时的历史记录，不代表当前状态：[研究章程](studies/study2/RESEARCH_CHARTER.md)、[机器可读章程](studies/study2/study2_charter.json)、[bootstrap handoff receipt](studies/study2/handoff_receipt.json)、[下一线程 handoff](studies/study2/NEXT_THREAD_HANDOFF.md)。

## 不可跨越的边界

- Study 1 的终态、receipts、ledgers、artifact packs 和 protected bytes 不得因 Study 2 被重写或重新解释。
- Study 2 使用新的 namespace、authority、task banks、IDs 和终态；它不是 S3 v1 的 rerun 或 rescue。
- J-lens readout 不能替代 lens-independent causal evidence；既有 M1200 在 Study 2 中只能作为 target-only 次级轴。
- 自动 parser 不能成为生成文本的权威科学标签；Study 2 主路径通过数值 logits 与程序 ground truth 避免该依赖。
- operational blocker 不能被写成科学阴性结论；完整科学阴性也不能靠事后换任务、阈值、层或样本来修复。
