# J-space observation

本仓库研究 DeepSeek-R1 蒸馏小模型是否形成可观察、可干预、具有因果作用的内部推理状态。项目现已明确划分为三个相互隔离的研究：已经关闭的 **Study 1**，同样已经关闭的 **Study 2**（protocol v1 在前瞻注册的 development feasibility gate 上失败），以及新建的 **Study 3**（仅为设计草案，draft-v0.4，已完成第二轮 operator amendment round，**等待第三次 independent methods review**）。Study 1 与 Study 2 都没有回答各自的原始科学问题；Study 3 尚未执行任何测量。

## 当前状态

| Study | 状态 | 结论边界 | 入口 |
|---|---|---|---|
| Study 1 | `CLOSED / INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` | 工程链和证据封存完成，但原始科学问题未被检验 | [Study 1 总结](studies/study1/README.md) |
| Study 2 | `CLOSED / STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY` | 前瞻注册的 Gate A 在 development 阶段失败；原始研究问题未被回答；B-C 与全部机制阶段从未打开 | [Study 2 终态清单](studies/study2/terminal_manifest.json) · [Study 2 终态 handoff](studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md) |
| Study 3 | `DESIGN DRAFT v0.4 AMENDED, UNFROZEN / STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_4_COMPLETE_AWAITING_THIRD_INDEPENDENT_METHODS_REVIEW` | 第二次独立 methods review 返回 `STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`（2 BLOCKING、6 MAJOR、2 MINOR）；draft-v0.4 是对这 10 项 finding、20 项 inherited finding 与 22 项 unresolved item 的 operator amendment，**起草方不宣称该设计正确**，每项修复均记为 `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`；仍未冻结、未授权执行、operation counter 全为 0、无 bank、无 seed、未选定 interface、未选定 positive reference、未授权 confirmation 访问 | [Study 3 索引](studies/study3/README.md) · [**v0.4 amendment 记录**](studies/study3/reviews/v0_4_operator_amendment.md) · [第二次独立 methods review](studies/study3/reviews/v0_3_independent_methods_review.md) · [权威协议 JSON](studies/study3/protocol/interface_calibration_protocol_draft.json) · [**v0.4 review packet**](studies/study3/analysis/independent_methods_review_packet_v0_4.md) · [operator 决策](studies/study3/NEXT_THREAD_HANDOFF.md) |

Study 3 是一个**设计状态**，不是结果。它把「响应与打分接口」本身当作被测对象，因为 Study 1 与 Study 2 都在不同程度上终止于工具层面的问题。Study 3 未修改、未重开、未重新解释 Study 1 或 Study 2 的任何冻结产物，也没有复用它们的任何 item identity、bank row、template outcome、confirmation content、seed 或结果。

draft-v0.1 曾提交 operator review，被判定存在**十项设计缺陷**并拒绝冻结（`STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`）。draft-v0.2 是相应的修订：JSON 文档成为**权威**记录，Markdown 仅为其渲染；设计关键校验从一次性脚本改为**已提交**的统计推导脚本与带负向变异用例的测试。修订过程中的模型自由推导推翻了 draft-v0.1 自己的一项断言——在 `n = 192`、目标 power 0.90 下，其所声称的 0.05 aggregate equivalence margin 在任何被测 discordance rate 下都不成立——因此 `OD6` 仍为 blocking，而不是通过放宽 margin 来迁就样本量。缺陷与处置见 [v0.1 operator review 记录](studies/study3/reviews/v0_1_operator_review.md)。

draft-v0.2 随后提交 **bounded independent methods review**。审阅方未参与起草，从 Tango (1998)、Hsueh, Liu and Chen (2001)、Berger and Hsu (1996) 重新推导全部统计量，其实现不引用、不加载、不读取 `design_statistics.py`。结论为 `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`：共 20 项 finding（六项 BLOCKING、十一项 MAJOR、三项 MINOR）。其中 `I3` 主要 estimand 在已提交的 counterbalancing 构造下不可识别；Family B 声称的 per-profile alpha 与实际计算所用 alpha 不一致；四个 discordance 取值仅为 sensitivity grid，无法证明 size control。审阅复现了起草方的 `0.025501`，因此枚举本身正确，缺陷在于对它的断言。完整审阅见 [v0.2 independent methods review](studies/study3/reviews/v0_2_independent_methods_review.md)。

draft-v0.4 是针对第二次独立 methods review 全部 10 项 finding 的 **operator amendment round**，其记录见 [v0.4 amendment 记录](studies/study3/reviews/v0_4_operator_amendment.md)。主要变更：`I3` 的判定指标收窄为 `J_joint_correct`（一个 level，而非 presentation contrast），并从全部 active claim 中删除 invariance / equivalence / presentation-effect 语言；为全部 34 个 sampling cell 注册 iid、有放回、精确有理权重的抽样框架，退役 `K5` 32 状态支撑集的确定性完全区组分配；type-II 结构改为任意相依下的 union bound（`m_max = 43`、per-cell `19/17200`、per-cell target `17181/17200`、profile stage `381/400`、end-to-end `9/10`）；样本量重新推导为满足 per-cell target 的最小正整数 `413 / 214 / 448`；confirmation 适用性改为可选 profile 与被选 profile 的交集；`S4` 诊断流补上非 null 的 forward 成本；状态机成为全函数且确定性的。

draft-v0.3 是针对上述 20 项 finding 与 22 项 unresolved item 的 **operator amendment round**，其记录见 [v0.3 amendment 记录](studies/study3/reviews/v0_3_operator_amendment.md)。主要变更：

- **`I3` 改为预注册的 pairwise 设计。** 独立单元为 `base_item_contrast_cluster`，每个 cluster 恰含 **2** 个 variant；不做 cross-product，不做 variant 的阶乘式相乘；`K5` 与 `K6` 不交叉，使用互不相交的 base-item identity。`K5` 恰为七个单因子 contrast（`K5-P1/P2/P3` 内容位置偏移、`K5-S1/S2/S3` 正确显示符号索引偏移、`K5-A1` label alphabet 替换），对 `S2` 与 `S3` 记为 `not_applicable` 而非 pass；`K6` 为 `K6-SEP` 与 `K6-INSTR` 两个互不相交的 pairwise cell，answer cue 与其余全部字节保持固定。平衡为确定性的完全区块设计，**本轮不存在任何随机抽取**。
- **三个 `I3` 指标，一个为主。** `J_inv`（不变性）、`J_cor`（正确性）、`J_both`（二者的合取，**主 gate 指标**）。稳定但**错误**的答案计 0；稳定的非法或不可解析输出计 0。
- **`OD5`：精确二项主设计，全部使用精确有理数。** study 级 development screening alpha 为 `1/200`，per-profile development component alpha 为 `1/600`，profile 内采用 intersection-union，因此 profile 内不再叠加 Bonferroni；可选 profile 的分母固定为 `K = 3`，不因任何 post-data 事实收缩。小数字段只是精确有理策略的渲染，不是真值来源。
- **`OD6`：只保留一个 `I3` floor。** `p0 = 0.90` 对 `p1 = 0.97`，power 不低于 `0.90`，每个适用 contrast cell 需 `n = 256` 个 base-item contrast cluster。`p0 = 0.95` 从全部生效字段中删除，仅允许出现在明确标注的历史叙述中。任何生效的拒绝域都不允许其 pass count 等于 `n`。
- **paired aggregate-equivalence 程序从一切决策角色中退役。** 它不再提供任何 gate、eligibility、selection、confirmation、claim 措辞、equivalence margin、critical value、discordance grid、conservativeness 陈述、rescue path 或排序权重；仅保留纯描述性的 paired 2x2 汇总（无 null、无 alpha、无 p 值、无 pass/fail）。审阅方的独立复算作为**不可变的历史证据**原字节保留，并**明确请第二位审阅者裁定**该退役是否完全消除了 size-control 缺陷。
- **每个 `n` 都带单位。** 注册四个单位：`base_item`、`base_item_contrast_cluster`、`rendered_row`、`scored_row`；同一个 `n` 绝不跨单位复用。
- **operation accounting 按六条 work stream 分解。** 在当前单 token 答案域下，`S3` 相对 `S2` 额外增加 **0** 次 forward pass 与 **0** 行 sequence scoring；禁止只给一个不加区分的总数。
- **`OD2` 仍为 `UNRESOLVED_BLOCKING_OPERATOR_DECISION`。** 本轮未选定、未偏好、未 pin、未解析 revision、未下载、未 tokenize、未加载、未 prequalify 任何 positive reference checkpoint；dossier 一律记为 `UNSELECTED`，`UR-22` 保持 `UNRESOLVED_BLOCKING_OPERATOR_DECISION`。

**起草方不宣称 draft-v0.4 正确。** draft-v0.3 曾被其起草方认为站得住脚，随后被第二次独立审阅以两项 blocking finding 驳回；因此每项修复只记为 `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`，判定权属于第三次独立 methods review。唯一合法的下一步动作就是这次审阅，其 review 对象为 [v0.4 review packet](studies/study3/analysis/independent_methods_review_packet_v0_4.md)。本轮不存在、也不得产生任何 freeze、`P3-Q`、bank、seed、model、GPU、development、confirmation 或机制执行 prompt。

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

## Study 3 draft-v0.4 third independent methods review

> **THIRD INDEPENDENT METHODS REVIEW COMPLETE - BOUNDED AMENDMENT REQUIRED**
>
> State: `STUDY3_DRAFT_V0_4_THIRD_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`
>
> Disposition: **`STUDY3_V0_4_THIRD_METHODS_REVIEW_REJECTED_BOUNDED_AMENDMENT_REQUIRED`**, returned against reviewed commit
> `e865be51da6c7e1a7a4f5b1fcad0efc513bd0f43`, tree `86c5a5ec0e475090c14654cff27605f883495a48`.
>
> The third bounded independent methods review of draft-v0.4 verified 5 of the 10 inherited
> second-review findings resolved and 5 partially resolved, and recorded 1 BLOCKING,
> 3 MAJOR and 6 MINOR new findings (`S3MR3-001` through `S3MR3-010`), none of them
> fundamental. Every binding statistical number in the drafting derivation was independently
> reproduced with zero numeric disagreement.
>
> The blocking finding is that the `K6-SEP` contrast cell has no referent for the option-less
> selectable profiles `S2` and `S3`: `R-sep` differs from `R-base` only in the separator between a
> label and its option content, which neither profile renders, so under the registered
> deterministic scorer that cell is a self-comparison rather than a presentation pair. The major
> findings are that the derived statistics table still admits the never-selectable profile `S4` to
> two confirmation rows, that the retired `J_both` invariance construct and the withdrawn sample
> size `256` survive in active charter, README and handoff text, and that the deterministic
> rendering surface is unregistered so the two `K6` cells cannot be instantiated.
>
> Both construct verdicts are `ADEQUATE_SUBJECT_TO_A_BOUNDED_REPAIR`. The narrowed
> `J_joint_correct` estimand does serve Study 3's instrument-calibration purpose, and excluding
> generation from the selectable set is correct rather than a gap. Read
> `reviews/v0_4_independent_methods_review.md`.
>
> The only legal next action is `OPERATOR_BOUNDED_AMENDMENT_ROUND_FOR_DRAFT_V0_5`, followed by a further independent methods
> review. **Not a freeze. Not `P3-Q`. Not a bank, a seed, model execution, a development round, a
> confirmation access, a feasibility pilot or any mechanistic work.**
>
> `OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`. The review neither resolves nor advances
> it, and the disposition is not driven by it.
>
> Study 3 remains unfrozen. No interface or positive reference is selected. No bank, seed, model
> operation, gate result, confirmation access or evidence row exists. Every operation counter is
> zero. The original research question remains unanswered.

