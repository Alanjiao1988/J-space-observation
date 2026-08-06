# J-space observation

本仓库用于执行一个面向 DeepSeek-R1 蒸馏小模型的机制可解释性实验：观察 R1 蒸馏模型是否在严格 no-CoT / answer-only 条件下形成可读、可干预、具有因果作用的 hidden workspace 表征。

## 当前研究问题

核心问题：**R1 蒸馏模型的 reasoning 能力是被内化到模型内部 workspace，还是主要依赖显性 CoT token 作为外部草稿纸？**

本项目以 Anthropic 2026 年 J-lens / J-space 论文为方法基线，主路径优先使用真实 Jacobian Lens，而不是普通 logit lens 或 tuned lens。

## 当前阶段

**2026-08-02 项目状态：`SCIENTIFIC_MAINLINE_RESTART_AUTHORIZED`。**

parser-v3 locked-evaluation 子项目已关闭为 `CLOSED_NONAUTHORITATIVE_TRIAGE_ONLY`。关闭的理由不是它失败得不够明确，而是它的前提被取消了：`L-01` 已从临时限制升级为项目设计规则 `DR-01` —— **语义裁决是本项目唯一权威的最终标签路径**，自动 parser 只能用于分流、路由与诊断，永远不能作为科学结果的最终正确性标签。既然如此，一个"通过验证的 parser"不再是任何科学标签或下游实验的前置条件，继续建私有 holdout、私有评审边界与审计循环，买到的是一个项目已决定不使用的授权。

parser 子项目的旧终态 `BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE` 在其原授权下依然正确，不被改写、不被软化；全部报告、receipt、commit、失败候选、sealed 对象、计数器与审计发现原样保留，关闭记录中钉死了 8 个工件摘要以便检测漂移。parser-v3 从未被验证，也不存在任何 parser-v3 科学结果。详见[parser-v3 关闭决策](docs/decisions/parser_v3_locked_evaluation_closure.md)与[授权对象](docs/phase_science_restart_authority.json)。

科学主线据此重启，授权四个工作包：

1. **S1 / Phase 1.0D** — 修复 Phase 1.0C headroom run。1.0C 的 `20260725T170041Z` 作为 `COMPLETE_INCONCLUSIVE` 历史记录保留，不重贴标签、不删除。字面占位符 `Final answer: <answer>` 与 512-token cap 被当作两个独立的、预注册的 generation-profile 缺陷，不得声称其中任一独自导致了全部 44 条 unresolved。
2. **S2** — 在确定性公开 pretraining-like 语料上完成更大规模的全层 J-lens 拟合。
3. **S3** — 执行预注册的 J-lens validity benchmark（已知中间量的 pass@k readout、ablation、coordinate swap、activation patching 与随机方向对照）。**矩阵收敛只是诊断，永远不能替代功能性有效性。**
4. **S4** — 在 S1 与 S3 的门槛都通过时，执行第一个有界的 RQ2 strict-no-CoT 机制学试点。

阴性的 headroom 结果、不收敛的 lens、未通过的 validity gate 都是科学结果，不构成再造一个 evaluator 或审计基础设施项目的理由。

### 2026-08-03 · S1 / Phase 1.0D 最新状态：`BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION`

**Phase 1.0D 的 generation run 至今没有执行，本轮也不会执行。**

依 `DR-01`，语义裁决是唯一权威的最终标签路径，因此 Phase 1.0D 的 900 行必须先有一个已注册的 semantic-review 提供方，否则任何 cell metric 都不允许存在。本轮的授权工作就是去取得这个提供方：把三个 reviewer 角色、prompt、rubric、输出 schema、六条合成 fixture 及其预期标签、以及各类失败的停止规则一次性冻结成
`docs/phase1_0d_semantic_review_addendum.json`（SHA-256 `582640de…`），烘进一个只读锁定的镜像
（`sha256:d9e887e68cccf7472e956785cda3ad7cf5f3902daea9287fc7b72c357f473e10`），**在任何目标输出存在之前**先跑 qualification，再跑 smoke。

- qualification **通过**：三个角色都能从 southeastasia 的 Container Apps VNet、以 managed identity（endpoint 已禁用 local auth）访问 eastus2 端点，统一走 `/openai/v1/chat/completions`，不需要 api-version 参数。
- smoke **按设计失败**：18 次角色×fixture 调用中 17 次与冻结的预期标签一致。唯一不一致的是 fixture `smoke_unresolved`——一段同时给出两个不同 final answer 并明确拒绝二选一的输出——注册的 primary reviewer 判成 `incorrect`，冻结的预期是 `unresolved`；secondary 与 third 都判 `unresolved`。

零传输失败、零格式错误、零 schema 失败、零 4xx。所以这不是 addendum 里"可修复并重跑"的传输/配置缺陷，而是它明确定为终态的 label mismatch。**未做任何修补**：没有换 fixture、没有改预期标签、没有调 rubric、没有换模型、没有加 fallback 或多数表决、没有重跑该 gate、没有硬启 generation run。

被这个 gate 卡住恰恰是它存在的意义：Phase 1.0C 之所以有 44 行不可用，就是因为分不清"答错"和"根本没给答案"；一个把后者塌缩成前者的 reviewer 会在 headroom 估计最敏感的方向上系统性放大错误率。

记录见 `EV-0012`、`D25`、`L-50`、`L-51`，工件见
`artifacts/phase1-0d-semantic-review-gate/20260803T031343Z/`。这一结果**不**说明该 reviewer 总体不可靠、**不**说明另外两个可靠、**不**涉及目标模型的任何能力，也**不**构成关于 hidden reasoning 或 J-space 的任何证据。Phase 1.0D 的诚实状态仍然是 `AWAITING_SEMANTIC_REVIEW`。

### 2026-08-05 · S1 / Phase 1.0D 最新状态：`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`

Phase 1.0D 后来完成了唯一 generation，并在唯一 formal v2 review 中因
primary 的 HTTP 429 transport exhaustion 停止。独立授权的 review-only
transport recovery 现已在任何新 inference 之前完成 capacity gate，并按设计
阻断：

| role | allocation | normalized TPM / RPM | subscription usage | model capacity available |
| --- | ---: | ---: | ---: | ---: |
| primary | 36 | 36,000 / 36 | 1,000 / 1,000 | 0 |
| secondary | 50 | 50,000 / 50 | 50 / 1,000 | 950 |
| third | 50 | 50,000 / 50 | 50 / 1,000 | 950 |

三个 deployment 都低于各自冻结 floor；primary 又没有任何未分配 quota，
所以本授权内不存在合法的整体通过路径。没有 deployment mutation，没有
recovery Job、lock、execution 或 result object，也没有 provider call。60 分钟
Azure Monitor 查询和最后 15 分钟 quiet window 都返回 0；证书同时明确记录了
这些查询的 timeseries 为空，而不是把空日志伪装成额外证据。

完整 capacity certificate 位于
`artifacts/phase1-0d-semantic-review-v2-transport-capacity/20260805T180417Z/`
（certificate SHA-256
`20e486e05a5f076b720ca12db3459b5a1c2c42e95684977dfdcff19d6da055d3`）。
这是一条 operational block，不是 scientific result：900 行仍然没有 final
semantic label、cell metric、candidate cell 或 headroom decision，CL-05 仍只
由 Phase 1.0C 的 preliminary screen 支撑。同一冻结 authority 只能在 operator
独立为同一组 deployment 提供足够 quota 后恢复；它不授权自动轮询、quota
request、alternate deployment 或 model change。

### 2026-08-06 · S3 protocol 状态：`NONTERMINAL_CHECKPOINT_JLENS_S3_VALIDITY_PROTOCOL_FROZEN_AWAITING_S2_LENSES_AND_EXECUTION`

S3 的 design-only Stage P 已完成。canonical protocol
`docs/jlens_s3_validity_protocol.json`（SHA-256
`bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625`）
冻结了官方 public benchmark bytes、target/tokenizer/lens identities、E0/E1/E2
边界、mechanical eligibility、hash split、pass@k log-AUC、paired bootstrap、
coordinate swap、ablation、Gram-matched random controls、answer-leakage
control、lens-independent activation patching、closed row-level output pack 与
classification truth table。

唯一的 bounded methods review 在精确 candidate hash 上发现 2 个 MATERIAL、
0 个 FATAL；唯一允许的 consolidated correction 明确了
distribution-qualified source-row identity 与完全可重建的 exact
target-overlap surface gate。同清单 verification 关闭为 0 FATAL / 0 MATERIAL /
0 MINOR；review allowance 已用尽。冻结记录见
[S3 protocol freeze](docs/decisions/jlens_s3_validity_protocol_freeze.md)，
review 记录见
[S3 methods review](docs/jlens_s3_validity_protocol_review.md)。

这仍然不是 S3 execution 或科学结果：本轮 target-model、tokenizer、lens、
inference、activation、patching、ablation、GPU Job、scientific row 与 RQ2 run
均为 0。CL-02/CL-07 仍 unsupported，CL-05 不变；Phase 1.0D 同时继续保持
`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`。未来执行需要独立授权、冻结
的 S2 lens artifacts，并严格使用上述 bytes 和 E0/E1/E2 边界。

## 历史阶段（parser 关闭前）

当前已完成四条关键路径的首个可执行阶段：

1. Phase 0.5A 在单张 Tesla T4 上完成真实 Jacobian Lens 技术可行性验证，结论为 **GREEN（仅限技术可行性）**。
2. Phase 1 历史 bounded `n=3` 结果保持冻结；不授权 higher-n 扩展。
3. Prospective parser v2 已仅使用 60 条公开 development cases 完成并冻结；一次性 locked evaluation 已于 2026-07-25 执行并关闭，正式结论为 **FAIL**（34 条强制 gate 中 32 条通过，`boxed_final_miss` 与 `wrong_span` 未通过），120 条 private locked holdout 已作废退役。
4. No-CoT taxonomy v2 与 450-item capability/headroom candidate bank 已完成，但未执行新的行为校准。

一次性 parser-v2 locked evaluation 这个注册 gate 已经用尽：该 holdout 不得重用、重评或重读。任何修改后的 parser 必须先重建并密封新的 locked holdout，再另行授权评估。完整结果与全部工件哈希见 [parser-v2 locked evaluation 报告](reports/phase1_parser_v2_locked_evaluation.md)。

该评估属于 evaluator validation，不是 model evaluation：全程未下载、未加载、未运行目标模型，也未使用 GPU。Phase 0.5A 的 GREEN 不代表 lens scientific quality，也不构成 hidden reasoning、internal workspace 或 J-space evidence。

## 重要边界

- 不把 prompt-based answer-only 等同于 strict no-CoT。
- 不把末层 motor/output 表示当作 hidden reasoning 证据。
- 不用裸 CoT vs answer-only 鲁棒性差异作为 ablation 结论。
- RQ3 的 base-vs-distill 比较必须在能力对齐任务上完成。
- 如果真实 J-lens 失败，只能降级为 hidden representation probe，不能声称完成 J-space observation。

## 文档入口

- [实验方案](docs/experiment_plan.md)
- [Copilot 执行 Prompt](docs/copilot_prompt.md)
- [Azure Runbook](docs/azure_runbook.md)
- [实现注记](docs/implementation_notes.md)
- [决策日志](docs/decision_log.md)
- [运行日志](docs/run_log.md)
- [parser-v3 关闭决策](docs/decisions/parser_v3_locked_evaluation_closure.md)
- [科学主线重启授权](docs/phase_science_restart_authority.json)
- [当前执行 Prompt](docs/prompts/phase_science_restart_after_parser_closure_prompt.md)
- [J-lens S3 validity protocol](docs/jlens_s3_validity_protocol.md)
- [J-lens S3 protocol freeze](docs/decisions/jlens_s3_validity_protocol_freeze.md)
- [文献笔记](docs/literature_notes.md)
- [Phase 0.5A real J-lens feasibility report](reports/phase05_jlens_feasibility.md)
- [Parser-v2 locked evaluation formal result](reports/phase1_parser_v2_locked_evaluation.md)
