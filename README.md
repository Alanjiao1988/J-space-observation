# J-space observation

本仓库研究 DeepSeek-R1 蒸馏小模型是否形成可观察、可干预、具有因果作用的内部推理状态。项目现已明确划分为三个相互隔离的研究：已经关闭的 **Study 1**，同样已经关闭的 **Study 2**（protocol v1 在前瞻注册的 development feasibility gate 上失败），以及新建的 **Study 3**（仅为设计草案，draft-v0.4，已完成第二轮 operator amendment round，**等待第三次 independent methods review**）。Study 1 与 Study 2 都没有回答各自的原始科学问题；Study 3 尚未执行任何测量。

## 当前状态

> **STUDY 3 P0-R1 IS EXECUTION READY - AWAITING ITS REPLAY GATE**
>
> States: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_6_COMPLETE_AWAITING_FINAL_FOCUSED_METHODS_REVIEW`
> 与 `STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE`。
>
> 一轮 model-free 的 execution-completion round 补齐了「已注册」与「可运行」之间的缺口：此前 `--gate` 是无条件拒绝，replay shell 调用的是 calibration 用的 `derive()` 而非 live gate，model runner 恒抛异常，既无 GPU launcher 也无 job definition，pre-execution receipt 的 `image_digest` 仍为 `null`。以上全部补齐。
>
> **generation 2 现为当前代**：一轮 model-free 的 transport 与 exception-safety round 修复了 generation 1 的五项缺陷——runtime binding 只比对路径清单而不比对字节、结果只回传 hash 而不回传完整字节、replay receipt 从不注入 GPU 作业、异常路径丢弃已完成的部分结果、以及验证只覆盖 in-memory 替身。绑定对象为 `studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json`（26,172 字节，sha256 `f506f632b8602cc000229b9a40991fc666cf0cf9f0195712cfe93d12fbee4714`，绑定 42 条可执行路径），image digest 为 `sha256:5f964edb414b8a22682693d8314063693daca3b915398094ec008d2c03308827`。
>
> 本轮**诚实记录了一次真实失败**：第一版 generation-2 image 通过了全部七道 build gate，却连一个结果字节都导不出——它根本没有装私有对象存储的客户端；build 的 transport gate 走的是 `--dry-run` 的 in-memory backend，能否真正联通存储账户对它毫无区别。该缺陷由真实基础设施上的 private-Blob canary 捕获（执行 `job-jspace-s3-p0r1-canary-g2-56y38fa` 失败，写出 0 个对象），该 image 已作废；修复后重建的 image 上三条 canary 全部通过（执行 `job-jspace-s3-p0r1-canary-g2-kqpquxz`）。
>
> generation 1 **未经消耗即被取代**：零 execution、零 GPU 分配、零 tokenizer construction、零 encode、零 checkpoint 下载、零权重加载；其 lock、image 与 handoff 字节原样保留。
>
> 本轮**未执行任何测量**：零 replay-gate evaluation、零 tokenizer construction、零 encode、零 checkpoint 下载、零权重加载、零 GPU 分配、零 forward pass、零生成、零 scored row。`p0_r1_pilot_execution_authorized` 为 `true` 且**尚未消耗**；`formal_execution_authorized` 仍为 `false`。
>
> draft-v0.6 修复了已发布的 P0-T disposition 所披露的两项机械缺陷，且**只**改变一件规范性的事：`S2`/`S3` 的判定统计量在**哪个位置**读取。模型可见的字节一个都没有改：answer cue 仍为 `Answer:` 且无尾随空白，完整候选面仍为 `" 0"`..`" 9"`（各带恰好一个前导 U+0020），`S1` 与 `S4` 完全不变，draft-v0.5 的 registry 逐字节保留为历史。
>
> 每个完整的 `S2`/`S3` 候选分解为 `candidate_d = common_prefix || discriminant_d`。scoring context 为「已注册的 prompt token IDs」后接「已验证的 common-prefix token」，由拼接构成，绝不通过重新编码拼接后的字符串得到；在该 context 上执行**一次**普通 prefill，并**仅**在十个已验证的 discriminant token ID 上读取 next-token logits；`S3` 在 CPU 上复用这一完全相同的向量，新增 **0** 次 model evaluation。common-prefix token 是 teacher-forced 的候选前缀：它不是生成的 token，也不是一次独立的 sequence-level model evaluation。
>
> token 身份是**推导得出而非誊抄**的：common prefix `220` 承载恰好一个 U+0020，discriminant `15`-`24` 承载 `0`-`9`，由不可变的已发布 P0-T result 与冻结语料在**零次** tokenizer encode 下恢复，且对 `RT`、`RL`、`RI` 完全一致。
>
> eligibility 分类器在一个**带版本的后继实现**中修复，历史结果绝不就地编辑。用不可变记录重放：在仅移除传播、scoring 规则保持 draft-v0.5 不变时，带空 reason 列表的 ineligible cell 由 27 降为 **0**，且每个目标角色仍保有**九**个可执行的真实 `I3` contrast——这机械地确认了当时发出的终态**过于严厉**，与已发布 disposition 的披露一致。在 draft-v0.6 边界下，39 个 cell 全部 eligible，每个角色保有十一个。
>
> 没有任何已注册的统计量发生变化：`m_max` 43、样本量 `413`/`214`/`448`、pass count `389`/`129`/`383` 与 `388`/`127`/`381`、以及 `31,065` 的 sequence-level development projection 全部**由推导重现**。确实变化的两项——`S2`/`S3` 的 scoring-context token 计数，以及 `S3` 零增量成本条件的表述——被单独列出而非被吸收，且二者都不增加任何 sequence-level model evaluation。
>
> P0-R1 是**已注册、未执行**：未构造 tokenizer、未下载 checkpoint、未加载权重、未分配 GPU、无 forward pass、无生成。全部 P0-R1 counter 为 0，不可变的 P0-T counter 未被触碰，`studies/study3/pilot/p0/` 下没有一个字节改变。
>
> `formal_execution_authorized = false`。draft-v0.6 **未**审阅、**未**冻结、**未**被选定。`OD2`、`UR-22` 与全部 `RP` 对象仍未解决，`RP` wrapper 为 **null** 而非空。不存在 seed、bank、winner 或 evidence row；`paper/evidence_ledger.csv` 逐字节不变，仍止于 `EV-0016`；原始研究问题仍未回答。
>
> 入口：[draft-v0.6 amendment 记录](studies/study3/reviews/v0_6_operator_amendment.md) · [focused review packet](studies/study3/analysis/final_focused_review_packet_v0_6.md) · [v0.6 rendering/scoring registry](studies/study3/protocol/interface_calibration_rendering_registry_v0_6.json) · [P0-R1 包](studies/study3/pilot/p0_r1/README.md) · [P0-R1 handoff（generation 2，当前）](studies/study3/pilot/p0_r1/P0_R1_HANDOFF_V2.md) · [P0-R1 handoff（generation 1，历史）](studies/study3/pilot/p0_r1/P0_R1_HANDOFF.md) · [operator authority](studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md)


> **STUDY 3-P0 FEASIBILITY PILOT REGISTERED - AWAITING THE TOKENIZER GATE**
>
> State: `STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE`
>
> 一项 narrow operator decision 取代了 draft-v0.5 中「第四次 independent methods review 是唯一合法后继」的条款，改为先授权**一次**物理隔离、严格设限的 feasibility pilot，仅在既有目标角色 `RT`、`RL`、`RI` 上进行，且**只**用于检验已注册的 rendering、tokenization、scoring、parsing、execution、accounting 与 resource pipeline 是否**可运行**。
>
> `formal_execution_authorized = false` 始终成立。draft-v0.5 仍是**未审阅、未冻结**的候选协议：P0 不宣称其正确，不推翻、不重贴标签、不削弱任何既往 review disposition，也**不豁免**最终的 independent methods review。P0 的测量是 methods-feasibility observation，**绝不是 Study 3 证据**，并记入独立、累计、不可重置的 pilot counter namespace。
>
> 尚未执行任何 model operation：未构造 tokenizer、未下载 checkpoint、未加载权重、未分配 GPU，所有 P0 counter 均为 0。`OD2`、`UR-22` 与全部 `RP` 对象仍未解决且未被触碰；不存在 seed、bank、interface 选择、winner 或 evidence row；`paper/evidence_ledger.csv` 保持逐字节不变，止于 `EV-0016`。
>
>
> **更新（stage P0-T 已执行并停止）**：State 现为 `STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE`。CPU-only tokenizer 与 renderer census 已在注册的 Azure container route 中执行，并返回一个已注册的 fail-closed stop，按原样发布、未作任何编辑。P0-M **未**开始：未下载 checkpoint、未加载权重、未分配 GPU、无 forward pass、无生成。
>
> 结论：renderer 与 `S1` 在机械层面成立（全 census 零 token-ID 冲突，4,902 次 encode 全部 byte-exact 往返）；但 `S2`/`S3` 对三个角色全部为 `INELIGIBLE_TOKEN_IDS`，因为注册的候选面 `" 0"`..`" 9"` 在三个 tokenizer 下均为**两个** token（`[220, digit]`），已注册的单点 restricted-logit 规则按原文不可实现。gate 自身的 eligibility 分类器存在一处缺陷，已如实披露而非修复。详见 [`P0_T_DISPOSITION.md`](studies/study3/pilot/p0/results/p0-t/P0_T_DISPOSITION.md)。
> 入口：[P0 协议与状态机](studies/study3/pilot/p0/README.md) · [operator authority](studies/study3/prompts/study3_p0_feasibility_pilot_authority.md) · [冻结语料 census](studies/study3/pilot/p0/corpus/p0_corpus_census.md)

| Study | 状态 | 结论边界 | 入口 |
|---|---|---|---|
| Study 1 | `CLOSED / INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` | 工程链和证据封存完成，但原始科学问题未被检验 | [Study 1 总结](studies/study1/README.md) |
| Study 2 | `CLOSED / STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY` | 前瞻注册的 Gate A 在 development 阶段失败；原始研究问题未被回答；B-C 与全部机制阶段从未打开 | [Study 2 终态清单](studies/study2/terminal_manifest.json) · [Study 2 终态 handoff](studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md) |
| Study 3 | `DESIGN DRAFT v0.4 AMENDED, UNFROZEN / STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_4_COMPLETE_AWAITING_THIRD_INDEPENDENT_METHODS_REVIEW` | 第二次独立 methods review 返回 `STUDY3_V0_3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`（2 BLOCKING、6 MAJOR、2 MINOR）；draft-v0.4 是对这 10 项 finding、20 项 inherited finding 与 22 项 unresolved item 的 operator amendment，**起草方不宣称该设计正确**，每项修复均记为 `PROPOSED_RESOLVED_SUBJECT_TO_THIRD_INDEPENDENT_METHODS_REVIEW`；仍未冻结、未授权执行、operation counter 全为 0、无 bank、无 seed、未选定 interface、未选定 positive reference、未授权 confirmation 访问 | [Study 3 索引](studies/study3/README.md) · [**v0.4 amendment 记录**](studies/study3/reviews/v0_4_operator_amendment.md) · [第二次独立 methods review](studies/study3/reviews/v0_3_independent_methods_review.md) · [权威协议 JSON](studies/study3/protocol/interface_calibration_protocol_draft.json) · [**v0.4 review packet**](studies/study3/analysis/independent_methods_review_packet_v0_4.md) · [operator 决策](studies/study3/NEXT_THREAD_HANDOFF.md) |

Study 3 是一个**设计状态**，不是结果。它把「响应与打分接口」本身当作被测对象，因为 Study 1 与 Study 2 都在不同程度上终止于工具层面的问题。Study 3 未修改、未重开、未重新解释 Study 1 或 Study 2 的任何冻结产物，也没有复用它们的任何 item identity、bank row、template outcome、confirmation content、seed 或结果。

draft-v0.1 曾提交 operator review，被判定存在**十项设计缺陷**并拒绝冻结（`STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`）。draft-v0.2 是相应的修订：JSON 文档成为**权威**记录，Markdown 仅为其渲染；设计关键校验从一次性脚本改为**已提交**的统计推导脚本与带负向变异用例的测试。修订过程中的模型自由推导推翻了 draft-v0.1 自己的一项断言——在 `n = 192`、目标 power 0.90 下，其所声称的 0.05 aggregate equivalence margin 在任何被测 discordance rate 下都不成立——因此 `OD6` 仍为 blocking，而不是通过放宽 margin 来迁就样本量。缺陷与处置见 [v0.1 operator review 记录](studies/study3/reviews/v0_1_operator_review.md)。

draft-v0.2 随后提交 **bounded independent methods review**。审阅方未参与起草，从 Tango (1998)、Hsueh, Liu and Chen (2001)、Berger and Hsu (1996) 重新推导全部统计量，其实现不引用、不加载、不读取 `design_statistics.py`。结论为 `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`：共 20 项 finding（六项 BLOCKING、十一项 MAJOR、三项 MINOR）。其中 `I3` 主要 estimand 在已提交的 counterbalancing 构造下不可识别；Family B 声称的 per-profile alpha 与实际计算所用 alpha 不一致；四个 discordance 取值仅为 sensitivity grid，无法证明 size control。审阅复现了起草方的 `0.025501`，因此枚举本身正确，缺陷在于对它的断言。完整审阅见 [v0.2 independent methods review](studies/study3/reviews/v0_2_independent_methods_review.md)。

draft-v0.5 是针对第三次独立 methods review 全部 10 项 finding 的 **bounded operator amendment round**，其记录见 [v0.5 amendment 记录](studies/study3/reviews/v0_5_operator_amendment.md)。主要变更：`K6` 的适用性改为**按 contrast 注册**——`K6-SEP` 变动的是「显示的选项标签」与「其显示的选项内容」之间的分隔符，而 `S2` 与 `S3` 两者都不渲染，因此该 factor 对它们没有指称对象，记为 `not_applicable`（既非 pass，也不计入分母），`S2` 与 `S3` 各自因而只保留**一个**真实的 `I3` contrast，即 `K6-INSTR`；注册一份 byte-exact 的**确定性渲染 registry** 与其 schema 作为 binding input（编码、换行、归一化策略，每个 gate-bearing 生成分支的题干模板，占位符与转义规则，选项行文法，label alphabet 与分隔符字面量，每个适用 `(profile, rendering)` 的指令句，answer cue 与候选面串，`S4` 的 pre-wrapper 边界，完整适用性表，以及 registry 与每个规范模板资产的密码学身份）；confirmation 适用性改为**组件级**；`S4` 从 `applicable_gates` 中移除 `I4`；`STOP_AWAITING_AUTHORITY` 从合法停机态中移除；精确二项 power 在注册样本量正上方的**局部非单调性**被明确披露，执行必须使用**精确**的注册 cell size；end-to-end union bound 的结论改述为返回并确认「**一个** adequate profile」。重新推导后 `m_max` 仍为 43（因为达到该上界的可选 profile `S1` 未受影响），`S2` 与 `S3` 的 gate-bearing cell 数由 19 降为 16。

draft-v0.4 是针对第二次独立 methods review 全部 10 项 finding 的 **operator amendment round**，其记录见 [v0.4 amendment 记录](studies/study3/reviews/v0_4_operator_amendment.md)。它已被第三次独立 methods review 驳回（`STUDY3_V0_4_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`），以下为其历史记录：`I3` 的判定指标收窄为 `J_joint_correct`（一个 level，而非 presentation contrast），并从全部 active claim 中删除相关退役措辞；为全部 34 个 sampling cell 注册 iid、有放回、精确有理权重的抽样框架，退役 `K5` 32 状态支撑集的确定性完全区组分配；type-II 结构改为任意相依下的 union bound（`m_max = 43`、per-cell `19/17200`、per-cell target `17181/17200`、profile stage `381/400`、end-to-end `9/10`）；样本量重新推导为满足 per-cell target 的最小正整数 `413 / 214 / 448`；confirmation 适用性改为可选 profile 与被选 profile 的交集；`S4` 诊断流补上非 null 的 forward 成本；状态机成为全函数且确定性的。

draft-v0.3 是针对上述 20 项 finding 与 22 项 unresolved item 的 **operator amendment round**，其记录见 [v0.3 amendment 记录](studies/study3/reviews/v0_3_operator_amendment.md)。主要变更：

- **以下为 draft-v0.3 的历史记录（historical record only）。** draft-v0.3 已被第二次独立 methods review 驳回并由 draft-v0.4 取代，draft-v0.4 又被第三次独立 methods review 驳回并由 draft-v0.5 取代。本节保留其当时的措辞与数值仅作为不可变的 provenance；其中的指标名与样本量均已 withdrawn，**不是**现行设计，任何 active field 都不得再使用它们。
- **`I3` 改为预注册的 pairwise 设计。** 独立单元为 `base_item_contrast_cluster`，每个 cluster 恰含 **2** 个 variant；不做 cross-product，不做 variant 的阶乘式相乘；`K5` 与 `K6` 不交叉，使用互不相交的 base-item identity。`K5` 恰为七个单因子 contrast（`K5-P1/P2/P3` 内容位置偏移、`K5-S1/S2/S3` 正确显示符号索引偏移、`K5-A1` label alphabet 替换），对 `S2` 与 `S3` 记为 `not_applicable` 而非 pass；`K6` 为 `K6-SEP` 与 `K6-INSTR` 两个互不相交的 pairwise cell，answer cue 与其余全部字节保持固定。平衡为确定性的完全区块设计，**本轮不存在任何随机抽取**。
- **三个 `I3` 指标，一个为主。** `J_inv`（不变性）、`J_cor`（正确性）、`J_both`（二者的合取，**主 gate 指标**）。稳定但**错误**的答案计 0；稳定的非法或不可解析输出计 0。
- **`OD5`：精确二项主设计，全部使用精确有理数。** study 级 development screening alpha 为 `1/200`，per-profile development component alpha 为 `1/600`，profile 内采用 intersection-union，因此 profile 内不再叠加 Bonferroni；可选 profile 的分母固定为 `K = 3`，不因任何 post-data 事实收缩。小数字段只是精确有理策略的渲染，不是真值来源。
- **`OD6`：只保留一个 `I3` floor。** `p0 = 0.90` 对 `p1 = 0.97`，power 不低于 `0.90`，每个适用 contrast cell 需 `n = 256` 个 base-item contrast cluster。`p0 = 0.95` 从全部生效字段中删除，仅允许出现在明确标注的历史叙述中。任何生效的拒绝域都不允许其 pass count 等于 `n`。
- **paired aggregate-equivalence 程序从一切决策角色中退役。** 它不再提供任何 gate、eligibility、selection、confirmation、claim 措辞、equivalence margin、critical value、discordance grid、conservativeness 陈述、rescue path 或排序权重；仅保留纯描述性的 paired 2x2 汇总（无 null、无 alpha、无 p 值、无 pass/fail）。审阅方的独立复算作为**不可变的历史证据**原字节保留，并**明确请第二位审阅者裁定**该退役是否完全消除了 size-control 缺陷。
- **每个 `n` 都带单位。** 注册四个单位：`base_item`、`base_item_contrast_cluster`、`rendered_row`、`scored_row`；同一个 `n` 绝不跨单位复用。
- **operation accounting 按六条 work stream 分解。** 在当前单 token 答案域下，`S3` 相对 `S2` 额外增加 **0** 次 forward pass 与 **0** 行 sequence scoring；禁止只给一个不加区分的总数。
- **`OD2` 仍为 `UNRESOLVED_BLOCKING_OPERATOR_DECISION`。** 本轮未选定、未偏好、未 pin、未解析 revision、未下载、未 tokenize、未加载、未 prequalify 任何 positive reference checkpoint；dossier 一律记为 `UNSELECTED`，`UR-22` 保持 `UNRESOLVED_BLOCKING_OPERATOR_DECISION`。

**起草方不宣称 draft-v0.5 正确。** draft-v0.3 曾被其起草方认为站得住脚，随后被第二次独立审阅以两项 blocking finding 驳回；draft-v0.4 同样被第三次独立审阅以一项 blocking finding 驳回。因此每项修复只记为 `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`，判定权属于第四次独立 methods review。唯一合法的下一步动作就是这次审阅，其 review 对象为 [v0.5 review packet](studies/study3/analysis/independent_methods_review_packet_v0_5.md)。本轮不存在、也不得产生任何 freeze、`P3-Q`、bank、seed、model、GPU、development、confirmation 或机制执行 prompt。

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

