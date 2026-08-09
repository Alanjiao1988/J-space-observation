# Project Status Report

> **Study 3 draft-v0.3 operator amendment round - 2026-08-08**
>
> **Study 3 state:**
> `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_3_COMPLETE_AWAITING_SECOND_INDEPENDENT_METHODS_REVIEW`
>
> The operator amendment round authorised after the draft-v0.2 independent methods
> review is complete. It repaired the design against all **20** findings
> (`S3MR-001` through `S3MR-020`) and all **22** unresolved items (`UR-01` through
> `UR-22`), and published an amended, **still unfrozen** draft for a **second**
> independent methods review.
>
> **The drafting party does not claim draft-v0.3 is correct.** Every repair is
> recorded as `PROPOSED_RESOLVED_SUBJECT_TO_SECOND_INDEPENDENT_METHODS_REVIEW` in
> [`studies/study3/reviews/v0_3_operator_amendment.md`](../studies/study3/reviews/v0_3_operator_amendment.md).
> draft-v0.2 was found defensible by the party that wrote it and was then
> independently rejected with six blocking findings; that is the specific failure
> mode this round was required not to repeat.
>
> **What the amendment adopted.**
>
> - **`I3` becomes a pre-registered pairwise design.** The independent unit is a
>   `base_item_contrast_cluster` carrying exactly **2** variants. There is no
>   cross-product and no factorial multiplication; `K5` and `K6` are not crossed and
>   use disjoint base-item identities. `K5` is exactly seven one-factor contrasts
>   (`K5-P1`/`P2`/`P3` content-position offsets `+1`/`+2`/`+3` mod 4;
>   `K5-S1`/`S2`/`S3` correct-displayed-symbol-index offsets `+1`/`+2`/`+3` mod 4;
>   `K5-A1` label-alphabet replacement) and is `not_applicable` for `S2` and `S3`
>   rather than passing. `K6` is two disjoint pairwise cells, `K6-SEP` and
>   `K6-INSTR`, with the answer cue and every other byte fixed. Balancing is
>   deterministic over complete blocks with bijective option-to-label mappings, and
>   **no random draw occurs anywhere in this design round.**
> - **Three `I3` indicators, one primary.** `J_inv`, `J_cor` and their conjunction
>   `J_both`, which is the **primary gate indicator**. A stable but **wrong** answer
>   scores `0`; a stable invalid or unparseable answer scores `0`. That `J_cor`
>   implies `J_inv` under a unique ground truth is recorded as an expected integrity
>   invariant rather than presented as independence.
> - **`OD5` resolved: an exact-binomial primary design in exact rational
>   arithmetic.** Study-level development screening alpha `1/200`; per-profile
>   development component alpha `1/600`; intersection-union conjunction within a
>   profile, so no further within-profile Bonferroni; and a **fixed**
>   selectable-profile denominator `K = 3` that never shrinks on a post-data fact.
>   Decimal fields are renderings of the exact rational policy, never the source of
>   truth.
> - **`OD6` resolved: one `I3` floor.** `p0 = 0.90` against `p1 = 0.97` at power at
>   least `0.90`, giving `n = 256` base-item contrast clusters per applicable
>   contrast cell. `p0 = 0.95` is deleted from every active protocol, table and
>   packet field and survives only in clearly labelled historical narrative. No
>   active rejection region has a pass count equal to `n`.
> - **Every symbol `n` carries a unit.** Four units are registered - `base_item`,
>   `base_item_contrast_cluster`, `rendered_row`, `scored_row` - at their definitions
>   and in every table, and one `n` is never reused across them.
> - **The paired aggregate-equivalence procedure is retired from every decision
>   role.** No gate, eligibility, selection, confirmation, claim-language,
>   equivalence-margin, critical-value, discordance-grid, conservativeness, rescue or
>   ranking role remains. Only purely descriptive paired 2x2 summaries survive, with
>   no null, no alpha, no p-value and no pass or fail. The reviewer's independent
>   recalculation is preserved **unedited** as immutable historical evidence, and the
>   second reviewer is explicitly asked to adjudicate whether retirement fully removes
>   the size-control defect.
> - **Operation accounting is decomposed into six named work streams** with per-stream
>   units. Under the current single-token answer domain, `S3` adds exactly **0**
>   forward passes and **0** sequence-scoring rows beyond `S2`. A single
>   undifferentiated total is prohibited.
> - **Derivation, not transcription.** The reviewer-returned planning targets are
>   independently re-derived by
>   [`studies/study3/analysis/design_statistics.py`](../studies/study3/analysis/design_statistics.py),
>   and the committed test asserts by AST inspection that they appear nowhere in the
>   script as literal constants.
>
> **`OD2` remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`.** No positive-reference
> checkpoint was selected, preferred, pinned, revision-resolved, downloaded,
> tokenized, loaded or prequalified; the dossier says `UNSELECTED`, `UR-22` stays
> `UNRESOLVED_BLOCKING_OPERATOR_DECISION`, and the dossier's two back-references were
> corrected from `D-07` to `D-04` per finding `S3MR-020`.
>
> **Nothing was measured.** Every operation counter is exactly zero: no model
> download, no revision resolution by downloading, no tokenizer construction, no
> tokenization, no weight load, no forward pass, no sequence scoring, no generation,
> no activation extraction, no hook, lens, probe, patch or ablation, no provider API
> call and no GPU job. No seed was drawn, no bank row exists, no interface profile was
> selected, no confirmation access was authorized,
> [`paper/evidence_ledger.csv`](../paper/evidence_ledger.csv) is unchanged at
> `EV-0016`, no limitations row was added, and both protected Phase 1.0D rollups are
> unchanged.
>
> **Immutability of the first review.** All three
> `studies/study3/reviews/v0_2_independent_methods_review.*` files,
> `methods_review_receipt_v0_2.json`, both
> `studies/study3/analysis/independent_methods_recalculation*` files, the v0.2 review
> authority copy, `studies/study3/analysis/independent_methods_review_packet.md` and
> `studies/study3/design_receipt_v0_2.json` are byte-identical to the reviewed round.
>
> The only legal next action is a **second** bounded independent methods review of
> draft-v0.3. Its review object is
> [`studies/study3/analysis/independent_methods_review_packet_v0_3.md`](../studies/study3/analysis/independent_methods_review_packet_v0_3.md).
> No freeze prompt, no `P3-Q` prompt, no bank prompt, no seed prompt, no model prompt,
> no GPU prompt, no development prompt, no confirmation prompt and no
> mechanistic-execution prompt exists.

> **Study 3 draft-v0.2 independent methods review - 2026-08-08**
>
> **Study 3 state:** `STUDY3_DRAFT_V0_2_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION`
>
> **Review disposition:** `STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED`
>
> The bounded independent methods review authorised after the draft-v0.2 amendment is
> complete. It was performed by a party that did not write the design, against the
> reviewed commit `8a2c4a0b2a73c5d802988333f11ea6c22828f6f5`, and it re-derived every
> design statistic from Tango (1998), Hsueh, Liu and Chen (2001) and Berger and Hsu
> (1996) in an implementation that never reaches
> [`studies/study3/analysis/design_statistics.py`](../studies/study3/analysis/design_statistics.py).
>
> **draft-v0.2 is rejected.** Six findings block: the `I3` primary estimand is not
> identifiable from the published counterbalancing construction; the `I3` primary
> indicator has two incompatible definitions across the authoritative JSON and the
> review packet; the Family B per-profile `alpha = 0.001666666667` is asserted while
> every component rule is computed at `alpha = 0.005`; the authoritative JSON asserts
> that exact enumeration never exceeds the nominal one-sided level while the packet
> discloses a realised `0.025501`; the four-value discordance grid cannot establish
> size control, and maximising over the full feasible null boundary finds `0.025073`
> at `n = 384` where the grid peaks at `0.024727`; and the `I3` floor at `p0 = 0.95`
> is unreachable at any admissible sample size.
>
> The independent enumeration **reproduces** the drafting party's `0.025501`, so the
> drafting enumeration is correct and the defect is in the claim made about it. That
> distinction is why the round required a separate implementation rather than a rerun.
>
> Eleven further findings are MAJOR, three are MINOR, and seventeen candidate
> cross-artifact inconsistencies were adjudicated individually.
>
> **Nothing was selected, adopted or authorized.** No interface, no positive reference
> - `OD2` remains an operator decision and no checkpoint was named, pinned, downloaded,
> tokenized, loaded, run, prequalified or substituted. `OD5` and `OD6` received
> explicit methods recommendations that this round does **not** adopt. All 22 operation
> counters remain zero, no bank row and no seed exists, `paper/evidence_ledger.csv` is
> unchanged at `EV-0016`, and both protected Phase 1.0D rollups are unchanged.
>
> The only legal next action is an operator amendment round producing draft-v0.3. See
> [`studies/study3/reviews/v0_2_independent_methods_review.md`](../studies/study3/reviews/v0_2_independent_methods_review.md)
> and [`studies/study3/NEXT_THREAD_HANDOFF.md`](../studies/study3/NEXT_THREAD_HANDOFF.md).
> No freeze prompt and no execution prompt exist.

> **Study 3 draft-v0.2 design amendment — 2026-08-08**
>
> **Study 3 state:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW`
>
> **Operator-review disposition recorded:**
> `STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`
>
> The operator reviewed Study 3 draft-v0.1, found **ten design defects**, and refused
> freeze. This round is the resulting single design-amendment round. It produced
> **draft-v0.2** of the interface-calibration protocol. The defects and their
> resolutions are recorded additively in
> [`studies/study3/reviews/v0_1_operator_review.md`](../studies/study3/reviews/v0_1_operator_review.md);
> the draft-v0.1 receipt was left untouched as the historical record.
>
> **The JSON protocol document is now authoritative** and the Markdown is a companion
> rendering of it. draft-v0.1's unsupported claim that both were generated from a
> single source of record has been removed, because no such generator is committed;
> what is committed, and therefore what is checked, is their agreement.
>
> **Design-critical checks are now committed rather than ephemeral.** draft-v0.2 adds
> a committed model-free statistics script with a `--check` mode
> ([`studies/study3/analysis/design_statistics.py`](../studies/study3/analysis/design_statistics.py))
> and a committed test with a negative-mutation battery
> ([`tests/test_study3_design.py`](../tests/test_study3_design.py)). In the v0.1 round
> the equivalent checker was ephemeral and missed a defect; that process failure is
> itself recorded.
>
> **A substantive statistical finding was produced against the drafting party's own
> earlier assertion.** Exact enumeration shows that at `n = 192` and a target power of
> 0.90, the aggregate paired-equivalence margin of 0.05 asserted in draft-v0.1 is
> supported at **no** tested discordance rate, and a 0.10 margin is supported only at
> discordance 0.05 and 0.10. The aggregate criterion was therefore demoted to
> secondary, an exact per-base-item consistency criterion was made primary, and `OD6`
> was left blocking rather than resolved by widening the margin to fit the sample size.
> A second issue is disclosed rather than absorbed: one configuration of the named
> asymptotic paired method has a realised one-sided level of 0.025501 against a
> nominal 0.025.
>
> **This remains a design state only.** Nothing is frozen. Nothing is authorized to
> execute. All 22 operation counters are zero: no download, no weight load, no
> tokenizer construction, no forward pass, no generation, no activation extraction, no
> probe, no patch, no ablation, no lens operation, no GPU job, no provider call. No
> seed was drawn, no task-bank row exists, no interface was selected, no positive
> reference was selected or pinned, and no evidence row was created.
> `paper/evidence_ledger.csv` still ends at `EV-0016`.
>
> **Four of the eight open decisions were resolved, and part of a fifth. None of the
> three blocking ones was.** `OD2` (positive reference), `OD5` (thresholds) and `OD6`
> (sample sizes) remain unresolved and blocking.
>
> **Both prior terminal states are unchanged.** Study 1 remains closed at
> `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`. Study 2 remains closed at
> `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY` with documentation state
> `STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE`. No Study 1 or Study 2 file was
> modified in this round and both protected Phase 1.0D rollups are unchanged.
>
> The only legal next action for Study 3 is a **bounded independent methods review**.
> The packet is
> [`studies/study3/analysis/independent_methods_review_packet.md`](../studies/study3/analysis/independent_methods_review_packet.md).
> There is no freeze prompt and no execution prompt.
>
> **Study 3 interface-calibration design draft — 2026-08-08**
>
> **Study 3 state:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW`
>
> A new study namespace, `studies/study3`, now holds a reviewable design draft for
> **Study 3 — Interface Adequacy and Label-Binding Calibration**. It asks whether a
> pre-specified response and scoring interface can recover deliberately trivial,
> primitive, and independently demonstrated task competence robustly across
> answer-label permutations, option positions and prompt renderings.
>
> **This is a design state only.** Nothing is frozen. Nothing is authorized to
> execute. Zero model operations were performed: no download, no weight load, no
> tokenizer construction, no forward pass, no generation, no activation
> extraction, no probe, no patch, no ablation, no lens operation, no GPU job. No
> seed was drawn, no task-bank row exists, no interface was selected, and no
> evidence row was created. `paper/evidence_ledger.csv` still ends at `EV-0016`.
>
> **Both prior terminal states are unchanged.** Study 1 remains closed at
> `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`. Study 2 remains closed at
> `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY` with documentation state
> `STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE`. No Study 2 scientific
> artifact was modified; only a clerical changed-path count in the Study 2
> terminal run-log prose was corrected, in its own separate commit, under substate
> `STUDY2_TERMINAL_CHANGED_PATH_BOOKKEEPING_CORRECTED`.
>
> The only legal next action for Study 3 is operator review. See
> [`studies/study3/NEXT_THREAD_HANDOFF.md`](../studies/study3/NEXT_THREAD_HANDOFF.md).
>
> **Superseded.** That operator review has since taken place. It found ten design
> defects and refused freeze, and draft-v0.1 was amended to draft-v0.2. See the
> current notice at the top of this file. This block is retained unchanged as the
> historical record of the v0.1 round.
>
> **Everything below this notice is prior status and remains historical.**

> **Study 2 protocol v1 terminalization — 2026-08-08**
>
> **Study 2 terminal state:** `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`
>
> **Documentation state:** `STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE`
>
> Study 2 protocol v1 is closed. The pre-registered, target-only Gate A feasibility
> gate failed at the end of Stage B-D: `permutation_chain` 25/128 (exact one-sided
> upper tail `0.9403523926144965`) and `affine_mod10` 33/128 (`0.4526854444021635`)
> against the frozen threshold X >= 43 at alpha = 0.025, so `overall_gate_pass` is
> `false`. Stage B-C, mechanistic-cell selection, M-D and M-C were never opened and
> may not be opened under this protocol version.
>
> **The original Study 2 research question was not answered.** Study 2 produced no
> evidence about internal computation, causal mechanism, distillation, J-space or
> J-lens, and added zero rows to `paper/evidence_ledger.csv`, which still ends at
> `EV-0016`. Cumulatively Study 2 performed 3,072 forward passes, 3 weight loads, 3
> tokenizer constructions and 3 model downloads; every other operation counter is
> zero.
>
> The Gate A outcome is not an artifact of execution or bookkeeping integrity, but
> may still be an artifact of interface or construct validity: protocol v1 never
> measured interface adequacy or label binding, so the data cannot distinguish an
> incapable checkpoint from an inadequate interface. See
> `studies/study2/decisions/study2_stage_bd_interpretation_erratum.md`.
>
> Current Study 2 entry points: `studies/study2/terminal_manifest.json` and
> `studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md`.
>
> Study 1 remains independently `CLOSED /
> INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`, and Phase 1.0D remains
> independently `BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`. Study 2's closure
> changes neither.
>
> **Everything below this notice is historical.** The Phase 1.x material that
> follows records earlier states in this repository and is retained unedited. It is
> not current status. Nothing below has been deleted, rewritten, or restated.

---

> **Phase 1.2H-R2 manual status — 2026-08-02** *(historical)*
>
> **Terminal state:** `BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE`.
>
> The exact remediated public candidate was commit
> `423d16a7b486b8c22fa58a733ffa6a03b389f0fe`, tree
> `3080241e68dc007e91f49967beebbd80ff1d4ec6`. ACR runs `cm3q` and `cm3u`
> passed the new targeted controls, compiled all boundary Bicep, and reproduced
> the full-suite baseline with 2873 passed, 15 skipped, and only the two
> disclosed pre-existing failures.
>
> The second and final permitted independent audit cycle (`cm3v`/`cm3w`)
> nevertheless returned four verified BLOCKER findings and one verified MAJOR
> finding. The controlling prompt therefore forbids another remediation/audit
> cycle in this round. Phase A is not frozen; Phase B and every private-semantic
> operation are unauthorized. No private semantic or label read, prediction,
> construction, seal, preregistration, Stage P, Stage E, formal evaluation, or
> private-boundary deployment occurred. The exact evidence is bound in
> `docs/phase1_2h_r2_phase_a_public_audit_terminal_receipt.json`.
>
> The status below is retained as historical context and predates this terminal
> record.

> **Phase 1.2H-R1 status (this round):** the cloud-first private-source access
> restoration round terminated **`BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY`**. Phase
> 1.2H had read `publicNetworkAccess = Disabled` as "unreachable"; the correct
> reading was "unreachable from *outside* the virtual network". R1 provisioned a
> least-privilege in-VNet execution boundary — a user-assigned identity holding
> exactly two role assignments, a pinned-digest image, a VNet-injected Container
> Apps job — and **the byte-only access gate passed**: 12 members listed, all 12
> objects streamed to a SHA-256 accumulator and discarded, 396,613 bytes, and an
> aggregate digest reproducing the already-committed public anchor
> `e1364afc…`. The receipt reports twelve invariants checked and none failed;
> in the build that produced receipt 003 that count was a **literal**, and it
> is derived from the invariants actually evaluated only in the current build
> (Audit C, C-12).
>
> **This changed what the operator can reach. It changed nothing about the set.**
> No byte was decoded, retained or interpreted: `decode_attempts`,
> `persist_attempts`, `azure_data_plane_writes`, `semantic_input_reads`,
> `semantic_label_reads`, `parser_invocations` and `predictions_generated` are
> all **0**. What makes those zeros credible is AST analysis of the two
> first-party Python files that run inside the job: no mutating Blob call
> appears in either, and the one function that holds object bytes passes each
> chunk to a SHA-256 digest and to `len`, and uses that name nowhere else.
> Audits E and F showed that premise was not established by the earlier check,
> which analysed whichever definition `ast.walk` reached first while Python
> binds the last, so a decorator, a plain module-level assignment, a
> tuple/`for`/`with` target, a `globals()` store, `setattr` on the module, or a
> second definition could have shipped every chunk elsewhere and still passed;
> separately `len` and `hashlib` could be rebound at module scope or by a
> `match` capture pattern, leaving the body byte-identical while every
> whitelisted call resolved elsewhere. Each of those shapes is now refused
> rather than analysed. What that establishes is bounded: no *syntactic*
> binding construct in this source rebinds the handler or the whitelisted
> names. It is not a guarantee about the running process. That is a
> property of first-party source — the Azure SDK, the standard library and the
> base image are not parsed — and it is not an observation of the running
> program. The receipt schema's `maximum: 0` pins prevent a violation from being
> *reported* in a valid receipt, but they do not observe anything.
> **No private content was read *semantically*, no set was constructed, no set
> was sealed, no parser was run, and no prediction was generated.** Audit F
> (F-20) corrected an earlier sentence here that claimed no private content
> was read at all. The ledger records 12 data-plane content reads, and two
> private curator objects were among the bytes streamed through a hashing
> function. Every byte was read; none was decoded, retained or shown. The
> supportable claim is the absence of a *semantic* read, and that is what is
> claimed.
>
> The blocker has therefore **moved, not cleared**. Set repair needs *semantic*
> review of private material, and no qualifying private review backend was found
> within the enumerated search scope: the executable boundary assessment scores
> **0 of 13 conditions passed, 5
> failed, 8 not assessable ⇒ `DOES_NOT_QUALIFY`**. The resource group contains
> zero `Microsoft.CognitiveServices` accounts and zero ML workspaces; the only
> same-region AI account belongs to an unrelated project and has
> `publicNetworkAccess: Enabled` with no private endpoint; and the worker subnet
> has no egress control configured. Provisioning that boundary is an **operator
> decision**. See `reports/phase1_2h_r1_private_source_access.md`.
>
> **Phase 1.2H status (5e3c398, superseded in part):** the authorized
> independent `parser-v3-v2` set-repair round terminated
> **`BLOCKED_ON_PRIVATE_SOURCE_ACCESS`** at its first precondition. That
> determination was accurate for the environment it was made in — a laptop
> outside the VNet — and R1 supersedes its *conclusion about reachability* while
> leaving its record intact. The round did close the audit gap Phase 1.2G had
> disclosed — Audit F found all six Audit E remediations incomplete and all six
> are now fixed — and introduced a live execution/access ledger. See
> `reports/phase1_2h_blocked_set_repair.md`.
>
> **Phase 1.2G status (0480f4f):** the parser-v3 one-shot locked evaluation
> remains **HALTED**. Phase 1.2G remediated ten post-audit consistency defects
> and *settled* the acceptance question that Phase 1.2F left open, by adopting
> **strict finite-suite conformance**: every eligible case admitted to the
> future set is a mandatory conformance example, so a zero residual budget
> follows as a `LOGICAL_INVARIANT` rather than as a severity judgement. The
> prospective acceptance policy is now **`FINAL`**. The round read no private
> data, ran no parser, generated no prediction, and produced no formal result.
> Parser v3 remains **unvalidated**, formal evaluation ordinal **0**. The round
> terminated **`READY_FOR_INDEPENDENT_SET_REPAIR`**, which authorized nothing
> beyond a separately authorized set-repair round — the round that Phase 1.2H
> then found it could not begin. See "Phase 1.2G" below.
>
> **Phase 1.2F status (3d519e1, superseded in part):** corrected the Phase 1.0C
> historical record and audited the four proposed acceptance thresholds;
> terminated **`BLOCKED_ON_ACCEPTANCE_POLICY`**. Phase 1.2G resolved that
> block. Section "Phase 1.2F" below is retained as history; where it states a
> next gate or a coverage figure, Phase 1.2G supersedes it. See "Phase 1.2F"
> below.
>
> Phase 1.0C headroom calibration **was executed** and finalized
> **`INCONCLUSIVE`** at `06eec993`. It is target-model task/headroom screening,
> not parser calibration, and no Phase 1.0C result can supply, bound, or
> unblock any parser acceptance threshold.
>
> **Phase 1.2E status (d843984):** built the public ontology-repair protocol
> and tooling only; terminated **BLOCKED** on acceptance thresholds, citing a
> dependency that was already false when written. See "Phase 1.2E" below.
>
> **Phase 1.2D status (45a18f4):** halted in preflight before preregistration
> after findings `H1`-`H9`. No formal `PASS` or `FAIL` exists. See
> "Phase 1.2D" below.

<!-- BEGIN GENERATED CURRENT STATE -->

<!-- Generated by scripts/generate_current_state.py from the canonical
     policy. Do not edit by hand; run the script with --write. CI runs
     it with --check. -->

### Machine-generated current state

- Acceptance policy: `parser-v3-v2-prospective-policy`, status **FINAL**, schema `phase1-parser-v3-prospective-evaluation-policy/v3`, settled in phase **1.2G**.
- Acceptance thresholds: **FINAL**.
- Exact-typed-decision coverage, derived: **80 of 120** cases pinned by mandatory gates (S01, S02, S03, S07, S08, S10, S11, S12); **40** residual (S04, S05, S06, S09).
- `residual_critical_exact_budget`: KEEP_HARD, binding **true**, pooled maximum errors **0**, per stratum S04 ≤ 0, S05 ≤ 0, S06 ≤ 0, S09 ≤ 0, basis `LOGICAL_INVARIANT`.
- Formal parser-v3 evaluation: **NOT_RUN**, ordinal **0**.
- Predictions generated: **0**. Locked-label reads: **0**. Parser-v3 runs against any locked set: **0**. Sealed `parser-v3-v2` sets constructed: **0** (`parser-v3-v1` was sealed and is retired; this counter is scoped to the successor set).

The block above is the policy's own finalization snapshot. The live
execution and access state is carried by the ledger, and is rendered
from it:

- Live access ledger: `phase1_2h_execution_access_ledger.json`, phase **1.2H**, status **BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY**.
- Retired `parser-v3-v1` repair access: sealed inputs read **0**, sealed labels read **0**, private curator files read **0**, byte-only integrity verifications **14** (a digest of a file reads every byte of its content and interprets none of it; Audit F (F-20) corrected an earlier claim here that no private content was read at all). State: **SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE**.
- Successor `parser-v3-v2`: exists **false**, cases constructed **0**, sealed **false**, `sealed_object_count` **null** (undefined under `L-32` without an authenticated seal-time observation; not measured to be zero).
- Parser execution: invocations on private or locked data **0**, candidate predictions **0**, comparator predictions **0**. Azure: data-plane content reads **12**, data-plane writes **0**, resource creations or changes **9**.

A `FINAL` policy is not a result. It records that the rule for judging
a future evaluation is settled, and records nothing whatever about any
parser. Specifically:

- Phase 1.0C was executed and finalized `INCONCLUSIVE`. It is target-model task/headroom screening, not parser calibration, and no Phase 1.0C result can supply, bound, or unblock any parser acceptance threshold.
- No private holdout, sealed input, sealed label or private curator file was *semantically read*. Phase 1.2H-R1 streamed all 12 sealed objects into a SHA-256 accumulator and discarded them, so bytes were touched while nothing about any case was learned: `decode_attempts`, `persist_attempts`, `semantic_input_reads` and `semantic_label_reads` are all **0**. Those zeros are literals the probe emits. What makes them credible is AST analysis of the two first-party Python files that run inside the job: no mutating Blob call appears in either, and the one function that holds object bytes passes each chunk to a SHA-256 digest and to `len`, and uses that name nowhere else. Five independent review rounds showed that premise was not established by the checks then in place: the analysis read whichever definition st.walk reached first while Python binds the last, and the name could be replaced by a decorator, a plain module-level assignment, a tuple/for/with target, a globals() store, setattr on the module, or a second definition; separately, len and hashlib could be rebound at module scope or by a match capture pattern, leaving the body byte-identical while every whitelisted call resolved elsewhere. Rounds four and five found the deeper version of the same defect: every rule above constrains a function *definition*, so a pristine handler could be left in place while the entrypoint called a different one, and the call-site check written to close that reached only streams bound by a plain assignment, leaving a downloader passed straight into a helper, opened in a `with`, bound by walrus or tuple, or chained without ever being named, outside every rule. Each of those shapes is now refused rather than analysed. What that establishes is bounded: no *syntactic* binding construct in this source rebinds the handler or the whitelisted names, and no object this source opens is ever named anywhere a byte API other than `.chunks()` could be called on it. It is not a guarantee about the running process, and an importing module could still rebind them from outside. That is a property of first-party source — not of the Azure SDK, the standard library or the base image, none of which is parsed — and not an observation of the running process. The receipt schema's `maximum: 0` pins stop a violation being *reported* as a valid receipt, but do not themselves observe anything.
- No prediction was generated and no parser was run against any evaluation or calibration corpus.
- No formal parser-v3 evaluation has occurred. Parser v3 remains **unvalidated**.
- `parser-v3-v1` remains `SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`, byte-unchanged.
- Phase 1.2H terminated `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`; Phase 1.2H-R1 established authenticated byte-only access from inside the VNet and terminated `BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY`, because set repair needs a semantic review boundary that the frozen 13-condition assessment scored `DOES_NOT_QUALIFY` — no qualifying backend was found within the enumerated search scope (resource group `rg-jspace-observation-sea` in `southeastasia`, plus same-region AI accounts visible to the operator's control-plane listing), and the worker subnet has no egress control. Whether an unlisted resource group elsewhere holds a qualifying backend was not observed and is not asserted. No `parser-v3-v2` set was constructed or sealed, and none exists.
- No J-space, hidden-reasoning, invisible-CoT or internal-workspace conclusion follows from any of this.

<!-- END GENERATED CURRENT STATE -->

## Summary

The critical-path reset is complete through bounded real-Jacobian technical
feasibility. The historical bounded n=3 record remains frozen, prospective
parser v2 was implemented from the 60-case public development set, and the
single authorized one-shot parser-v2 locked evaluation has now been executed
and closed. Its formal outcome is **FAIL**, and the 120-case locked holdout is
spent and retired. The model-free Phase 1.2B tooling delivered one-shot Azure
coordination, authenticated crash recovery, and deterministic post-label
`CLOSED/INVALID` closure, all of which were exercised in the real run.

A four-track parallel advancement round then ran on 2026-07-25. Phase 0.5B
J-lens saturation executed on a T4 and returned **ENGINEERING_IMPROVING**:
sharding, merge, serialization and apply are numerically sound, but the lens has
not converged between 10 and 25 fit prompts. Phase 1.0C headroom calibration was
preregistered and frozen, and was **executed later the same day**, finalizing
**INCONCLUSIVE** (corrected in Phase 1.2F; the earlier "BLOCKED, no model run"
wording described only the pre-execution plan pack). Parser v3 is
developed but **NOT VALIDATED**. A new 120-case parser-v3 locked holdout was
constructed with zero measured overlap and was, *at that date*, not yet sealed.
That is a point-in-time fact and no longer describes the current state: the set
was subsequently sealed as `parser-v3-v1`, then found to violate its own public
specification, and is now `SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`.
No eligible sealed parser-v3 set exists today. The no-CoT taxonomy v2 and
450-item headroom candidate bank remain design artifacts; no new behavioral
calibration was run.

## Current Phase

**Phase: Phase 0.5A GREEN; Phase 0.5B COMPLETE with decision ENGINEERING_IMPROVING; parser-v2 locked evaluation CLOSED with formal outcome FAIL and holdout retired; parser v3 developed but NOT VALIDATED; `parser-v3-v1` SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE and no eligible sealed parser-v3 set exists; Phase 1.0C EXECUTED and finalized INCONCLUSIVE; Phase 1.2E BLOCKED (superseded); Phase 1.2F terminated BLOCKED_ON_ACCEPTANCE_POLICY (superseded by Phase 1.2G); Phase 1.2G terminated READY_FOR_INDEPENDENT_SET_REPAIR with the prospective acceptance policy FINAL**

## Phase 0.5B J-lens saturation result (2026-07-25)

- Run `20260725T122016Z`; status **COMPLETE**; decision **ENGINEERING_IMPROVING**.
- Code commit `408cd00`; image digest `sha256:a15016df…3524f`; corpus SHA-256
  `41e104ef…62b4b`; protocol hash `b4422756…9d32e`. Zero deviations.
- All five stability criteria passed, with shard-merge versus direct fit agreeing
  to 2.384e-07 max_abs against a 1e-05 limit and 4.862e-08 relative Frobenius
  against a 1e-06 limit, and bit-exact save/load.
- Both convergence criteria failed: relative Frobenius 0.4170 against a 0.10
  limit and cosine 0.9205 against a 0.99 limit. More fit prompts still change the
  lens. This is the honest result, not a partial success.
- Held-out apply stability: top-k overlap 0.82, rank correlation 0.9691, logit
  cosine 0.9794. **These are technical stability statistics only and are never
  semantic evidence.**
- Cost is essentially flat per prompt: 52.85 s/prompt at 10 prompts and 52.67
  s/prompt at 25, with peak reserved memory near 3.8 GB in both cases.
- Next gate: main-agent review before any larger fit is authorized. No behavioural
  or semantic gate is opened. No workspace, hidden-reasoning, invisible-CoT or
  J-space claim follows from any of this.
- Artifacts: `artifacts/phase05b-jlens-saturation/track-a/20260725T122016Z/`.

## Phase 1.0C headroom calibration plan pack (2026-07-25) — SUPERSEDED point-in-time record

> **Erratum E-1.2F-01 (Phase 1.2F).** The section below is a historical
> point-in-time record of the *plan* pack, before the calibration ran. It was
> never updated when the run executed, and Phase 1.2E then read it and authored
> a false blocking dependency into a policy artifact. It is retained unchanged
> as history. The current record is the next section.

- Design, protocol, selection rules and analysis code are complete and frozen
  before any data exists; 100 tests pass; protocol hash `d778736f…5719d`.
- The emitted plan-pack status was **BLOCKED**: at that point no model had been
  run, so there was no measurement of the model. (Superseded: the run executed
  later the same day.)
- Blocker at that time: the main `Dockerfile` validates a build attestation from
  `.semantic_audit_build_provenance.json`, which is gitignored and absent from the
  worktree, and no calibration image existed in the registry. The image could not
  be rebuilt at that commit. This blocker was subsequently cleared.
- Artifacts:
  `artifacts/phase1-headroom-calibration/track-b/p10c-trackb-plan-d778736ff8a2/`.

## Phase 1.0C headroom calibration — EXECUTED, finalized INCONCLUSIVE

This is the current, correct record. Primary evidence:
`artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/04_decision.json`.

| Fact | Value |
| --- | --- |
| Preregistered | `62e9b961` |
| Unblocked | `5d18b708` |
| Executed | `72c3d281` (run `20260725T170041Z`) |
| Finalized | `06eec99315ff5b6c838aeaa82e0814fea6e886b4` |
| Target-model outputs generated | 300 / 300 |
| Semantic labels | 156 correct, 100 incorrect, **44 unresolved** |
| Outstanding review rows | 0 |
| Arbitration rows | 0 |
| **Final Track B decision** | **`INCONCLUSIVE`** |

Why `INCONCLUSIVE`: the preregistered finalize rule in
`docs/phase1_headroom_calibration_protocol.md` treats *any* unresolved label as
inconclusive. 44 rows were adjudicated unresolved because the emitted output
states no answer a reviewer could read, and further adjudication of the same
output cannot resolve it. The rule was **not** altered after it was seen to
block.

**What Phase 1.0C is.** Target-model observable-answer task/headroom screening.
Its own decision record states it "estimates observable answer accuracy of a
single target model on a frozen task bank … for the sole purpose of selecting
task cells with measurable headroom".

**What Phase 1.0C is not.** It is **not a parser-accuracy calibration**. It
measures whether the *model* can answer a question; a parser threshold concerns
whether the *parser* can recover an answer from the model's text. These are
different quantities on different objects, so no Phase 1.0C result can supply,
bound, or unblock any parser acceptance threshold. It neither validates a parser
nor supplies parser acceptance thresholds.

## Parser-v3 locked holdout status (2026-07-25) — SUPERSEDED point-in-time record

> **Superseded.** This section records the state on 2026-07-25, when the set had
> been constructed but not yet sealed. It is retained because it is the
> construction record. It is **not** current state. The set was subsequently
> sealed as `parser-v3-v1`, was then found to violate its own public
> specification, and is now
> `SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`. Current state is in
> the generated block at the top of this file.

- 120 cases across 12 strata, 80 critical. Dual reference-blind reviewers at
  120/120 each; 113/120 whole-row agreement pre-arbitration; 7 rows arbitrated;
  **0 unresolved labels**.
- Zero exact, zero normalized and zero numeric-normalized collisions against the
  65-case parser-v3 adversarial set and the 60-case parser-v2 development set,
  independently re-verified by `scripts/crosscheck_parser_v3_locked_set.py`.
- One registered cross-check is vacuous, not passed: the 18-record historical
  audit extract has no output-bearing field.
- **As written on 2026-07-25: the set is not sealed.** The registered overlap
  check against the retired parser-v2 locked inputs was attempted on 2026-07-25
  and is recorded as **NOT PERFORMED** after the Azure Run Command transport
  wedged; no write grant was created either. On that date the holdout was not
  locked and no parser-v3 evaluation could be run against it. Sealing happened
  later; the retirement recorded above happened later still.
- Reviewer agreement is LLM operational consensus, not human ground truth.
  Isolation from parser-v3 development is procedural, not enforced, and both
  happened in the same worktree in the same round.

## Phase 1.2B parser-v2 locked evaluation result (2026-07-25)

- Formal decision: **FAIL**, decided `2026-07-25T08:01:34Z`, formal evaluation
  ordinal 1, manual override no.
- Holdout retired and spent; parser was not re-run; metric retry and prediction
  re-run are both disallowed by the sealed attestation.
- 34 mandatory gates: 32 passed, 2 failed, 0 NA/invalid.
  - `boxed_final_miss`: 1/20 against a limit of 0 errors.
  - `wrong_span`: 2/80 against a limit of 1 error.
- Report-only aggregates: typed agreement 116/120, 4 mismatched cases, 1
  material-error case, across 120 cases in 12 strata.
- The state chain reached `CLOSED` (`12_closed_receipt.json`,
  `outcome = FAIL`), and the single authorized post-result review agreed with
  the sealed artifacts on all 38 independent checks.
- Exactly three container executions ran: one Stage-P prediction run, one
  Stage-E attempt rejected for an infrastructure reason before any label
  access, and one successful `scorer_infrastructure` retry that opened, scored,
  and retired the holdout once.
- Full record, including every authenticated artifact hash:
  `reports/phase1_parser_v2_locked_evaluation.md`.
- Boundary: this is evaluator validation, not model evaluation. No target model
  was downloaded, loaded, or run, and no GPU was used. No hidden-reasoning,
  invisible-CoT, internal-workspace, or J-space claim follows.

## Parser v3 development status (2026-07-25) — NOT VALIDATED

- Parser v3 exists as a standalone reference-blind extractor and passed every
  preregistered **development** gate: 60/60 non-regression on the frozen
  60-case public development set, 65/65 typed agreement on 65 new adversarial
  development fixtures, and zero `boxed_final_miss`, `wrong_span`,
  `last_number_trap`, and material-correctness errors across the 125 pooled
  development rows.
- **Parser v3 is not validated.** It has no formal result, no locked-holdout
  evidence, and no acceptance decision. Development-set performance is not
  evaluator validation, and no parser-v3 locked evaluation has been authorized
  or run.
- The 65 adversarial fixtures were authored by the same agent that wrote parser
  v3, so they are a development signal and not an independent oracle.
- Every adopted rule change is recall-increasing, so v3 carries an unprobed
  precision risk. The one deducibly precision-shaped retired failure remains
  unaddressed.
- Parser v2 and the legacy parser remain byte-identical to `bc6d7b7`; the
  retired FAIL is unaffected.
- A formal parser-v3 result would require a newly constructed, independently
  authored locked holdout and a separately authorized one-shot evaluation.
- Detail: `reports/phase1_parser_v3_development.md`.

## Historical prerelease snapshot — superseded (2026-07-23)

> The content below describes the historical state *before* the formal locked
> evaluation was executed. It has been superseded by the 2026-07-25 CLOSED/FAIL
> result recorded above. Statements such as "no VM has been provisioned",
> "audits are pending", and "no Azure command … occurred" were accurate on
> 2026-07-23 and are retained verbatim as a point-in-time record; they no longer
> describe the current state. Nothing in this section has been renumbered or
> back-dated.

- Stage P remains label-blind and Stage E remains parser-free.
- Private DNS TXT create-only records provide separate build, launch, and
  dispatch capabilities; recovery cannot recreate a PUT/start capability.
- ACA dispatch is delayed until the exact immutable Job reaches authenticated
  `Succeeded` provisioning state.
- Bootstrap authenticates pending primary or scorer-retry attempts without
  rereading locked inputs or labels.
- Complete immutable predictions can be adopted without rerunning a parser.
- Any authenticated post-label attempt lacking one intact score transaction
  closes deterministically as `CLOSED/INVALID` without labels reread, scoring,
  parser invocation, or metric/decision acceptance.
- Score payloads are checked against both their manifest and the original
  scoring transaction, including coordinated payload/manifest/attestation
  replacement attempts.
- The launcher is restricted to a private Debian 12 VNet orchestrator with
  separate control-plane and runtime data identities. No such VM has been
  provisioned; explicit approval is still required before cost-bearing
  infrastructure creation.
- Focused locked-evaluation validation: `162 passed`.
- Complete repository validation: `759 passed, 2 warnings`.
- Python compilation, both Azure Bash syntax checks, `git diff --check`,
  changed-file credential scan, 10 MiB size gate, and frozen
  parser/gate/data-path checks passed.
- Four independent release audits are pending.
- No Azure command, image build, private holdout read, label read, parser
  evaluation, model load, GPU use, or scientific observation occurred in this
  tooling step.

## Authoritative Phase 0.5A result (2026-07-18)

- Target: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` at
  `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`.
- Official source:
  `anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`.
- Run ID: `20260718T184445Z`.
- Primary execution `job-jspace-p05-jlens-l7tipil` completed F0-F3 and failed
  F4 because official default-fp16 lens serialization did not preserve the
  fitted fp32 transport output.
- The sole authorized retry `job-jspace-p05-jlens-m1sazlr` restored and reused
  F2/F3, losslessly reserialized the exact lens as fp32, passed the unchanged
  F4 gate, and completed final manifest-last Blob persistence.
- Final decision: **GREEN / COMPLETE for bounded technical feasibility only**.
- F5 and actual 10-/25-prompt fits were not run; the scaling results are
  measured projections.
- No new formal behavioral observations or locked parser evaluation were
  produced. No hidden-reasoning, internal-workspace, or J-space claim is
  supported.
- Final model-free validation: `597 passed, 2 warnings`.

Detailed report: `reports/phase05_jlens_feasibility.md`.

## ACR Managed Identity Azure Execution (2026-07-08)

GHCR route was abandoned for execution because private package pull authentication remained blocked. The project switched to ACR with Azure AAD / user-assigned managed identity.

### ACR and Identity

- ACR: `acrjspaceobssea0708231738`
- Login server: `acrjspaceobssea0708231738.azurecr.io`
- Admin user enabled: `False`
- ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:359643b7b5eb`
- ACR build: succeeded via `az acr build`
- Managed identity: `id-jspace-aca-acrpull-sea`
- Principal ID: `78d4348b-57eb-4fb9-aaa7-99148b303292`
- AcrPull assigned: yes

### Azure Resources

- Resource group: `rg-jspace-observation-sea`
- Log Analytics workspace: `law-jspace-observation-sea`
- Container Apps environment: `cae-jspace-observation-sea`
- Workload profile: `gpu-t4` / `Consumption-GPU-NC8as-T4`
- Jobs:
  - `job-jspace-acr-smoke`
  - `job-jspace-phase05-acr`
  - `job-jspace-phase1-dryrun-acr`
  - `job-jspace-phase1-pilot-acr`

### Execution Results

- Smoke job: `Succeeded`
  - Execution: `job-jspace-acr-smoke-9b9wb4z`
  - Logs: `41 passed, 2 warnings`
- Phase 0.5 `--skip-fit`: `Succeeded`
  - Successful execution: `job-jspace-phase05-acr-i110lnu`
  - Both configured 1.5B models loaded successfully on Azure `Tesla T4`.
  - `jacobian-lens` not installed in the image.
  - Actual tiny fitting: not attempted.
  - Output path: `/workspace/results/runs/20260708_153600`
- Phase 1 dry-run: `Succeeded`
  - Execution: `job-jspace-phase1-dryrun-acr-v0j1bkd`
  - Total cells: 54
  - No real generation.
  - Output path: `/workspace/results/runs/20260708_154052`
- Small Phase 1 pilot: `Succeeded`
  - Execution: `job-jspace-phase1-pilot-acr-lhuvwbf`
  - Scope: DeepSeek-R1-Distill-Qwen-1.5B, arithmetic only, depths 1/2/3, three conditions, `--items-per-cell 1`, `--max-new-tokens 64`
  - Output path: `/workspace/results/runs/20260708_154330`

### Current caveats

- Blob persistence is now configured and has persisted the small Phase 1 pilot outputs.
- At this historical 2026-07-08 execution, Phase 0.5 did not include real
  fitting and its general-purpose ACR image lacked `jacobian-lens`. This was
  superseded by the dedicated pinned Phase 0.5A run recorded above.
- The small Phase 1 pilot is behavioral only and is not J-space evidence.
- Review exported logs/metrics before broadening the run.

## Persistent Storage Attempt (2026-07-09)

Goal: configure Azure Files persistence before broader Phase 1 runs.

### Result

- Azure Files persistence path is currently blocked.
- Both storage accounts created in this attempt have `allowSharedKeyAccess=False`, even when `--allow-shared-key-access true` was specified during creation.
- Azure Files data-plane operations with account key fail with:
  - `KeyBasedAuthenticationNotPermitted`
  - `Key based authentication is not permitted on this storage account.`

### Storage resources

- `stjspaceobssea07090835`: created, key-based auth disabled by policy
- `stjspacefiles0709085305`: created with explicit shared-key flag, but key-based auth still disabled by policy
- File share `jspace-results` was created through ARM management plane on the first storage account, but key-based Azure Files access remains unusable for Container Apps mount.

### Container Apps mount attempt

- Environment storage `jspace-results-storage` was registered, but the smoke job using `/mnt/results` hung.
- Stuck execution: `job-jspace-storage-smoke-acr-1s1g5d8`
- Cleanup completed:
  - stopped the stuck execution
  - deleted `job-jspace-storage-smoke-acr`
  - removed `jspace-results-storage` from the Container Apps environment
- No environment storage is currently registered.

### Script status

- `infra/azure/scripts/06_run_job_acr_mi.sh` now supports Azure Files volume mounting (`ENABLE_RESULTS_MOUNT`, `STORAGE_MOUNT_NAME`, `RESULTS_MOUNT_PATH`), but this should not be used until a working storage backend is available.

### Historical next blocker (resolved)

Choose a persistence alternative:

1. Ask the Azure/admin team to allow Azure Files shared-key access for this project; or
2. Switch to Azure Blob upload using managed identity from inside the container; or
3. Use identity-based Container Apps storage if supported in this tenant.

Resolved by switching to Azure Blob upload with managed identity; see the Blob persistence success section below.

## Blob Persistence Success (2026-07-09)

Azure Blob upload with managed identity is now the working persistence route.

### Storage and identity

- Storage account: `stjspacefiles0709085305`
- Blob container: `jspace-results`
- Shared key used: no
- `allowSharedKeyAccess`: `False`
- Managed identity: `id-jspace-aca-acrpull-sea`
- Managed identity role: `Storage Blob Data Contributor`

### Code/image

- Added `src/jspace_observation/blob_export.py`
- Added `scripts/blob_export_smoke.py`
- Added `azure-identity` and `azure-storage-blob`
- Added Blob export hooks to Phase 0.5 and Phase 1
- ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:afd647a6b53e`

### Blob smoke

- Job: `job-jspace-blob-smoke-acr`
- Successful execution: `job-jspace-blob-smoke-acr-o7kl7s2`
- Blob prefix: `smoke/20260709T013310Z`
- Verified file: `smoke/20260709T013310Z/smoke.txt`

### Persistent Phase 1 pilot

- Job: `job-jspace-phase1-pilot-blob-acr`
- Execution: `job-jspace-phase1-pilot-blob-acr-9voxpdm`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot/20260709T014336Z`
- Files uploaded:
  - `phase1_eval_records.jsonl`
  - `phase1_generations.jsonl`
  - `phase1_metrics.csv`
  - `phase1_summary.md`

### Pilot review

- Expected files present: yes
- Cells completed: 9
- Strict answer-only no-CoT validity is overestimated by current validator.
- Obvious bug: strict answer-only outputs can contain visible reasoning such as `Step-by-step explanation` and `follow these steps`, but the validator did not flag them.
- Numeric parser can be misled by truncated reasoning and last-number selection.
- Scientific conclusion: infrastructure + behavioral sanity only; no J-space claim.

### Next action

Fix no-CoT visible-reasoning validation before any broader Phase 1 run.

## Validator Hardening Success (2026-07-09)

The no-CoT validator and parser warning layer were hardened and rerun on the same minimal persistent Phase 1 pilot scope.

### Code changes

- `src/jspace_observation/no_cot.py`: stricter visible-reasoning detection and explicit no-CoT violation reasons.
- `src/jspace_observation/eval_parsing.py`: parser ambiguity and answer-format warning fields.
- `experiments/phase1_depth_gradient.py`: richer generation/eval records and metrics.
- Tests expanded for known false negatives and ambiguous parsing.

### Test result

- `python -m pytest tests/ -q` -> `54 passed, 2 warnings`

### New image and rerun

- ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:937288cfb8ef`
- ACR build run: `cm4`
- Digest: `sha256:c3dcbdd7360ff1f1462263446ee8865132dd854df3a29f4f57b8e7d6ae348094`
- Azure job: `job-jspace-p1-validator`
- Execution: `job-jspace-p1-validator-xkqro3f`
- Blob prefix: `phase1-pilot-validator/20260709T022001Z`
- Files: generation JSONL, eval JSONL, metrics CSV, summary MD

### Rerun pilot review

- Cells completed: 9.
- strict_answer_only no-CoT valid rate: `0.0000` for depths 1, 2, and 3.
- strict_answer_only visible reasoning marker rate: `1.0000` for depths 1, 2, and 3.
- parse_ambiguous_rate: `1.0000` for all 9 cells.
- answer_format_warning_rate: `1.0000` for all 9 cells.
- Summary warnings now explicitly report:
  - strict_answer_only no-CoT invalid count: `3/3`
  - strict_answer_only visible reasoning marker count: `3/3`
  - parse ambiguous count: `9/9`

### Current decision

- The known validator false negative is fixed.
- The pilot reveals that current strict-answer-only prompting/decoding still produces visible reasoning, so strict no-CoT-valid samples are absent in this tiny arithmetic pilot.
- Do not expand to broader Phase 1 until strict-answer-only prompting/decoding and parser policy are reviewed.
- Scientific conclusion remains infrastructure + behavioral sanity only; no J-space claim.

## Strict Answer-only Prompt/Decoding Rerun (2026-07-09)

### Changes

- Added `strict_answer_only_prefill_answer`.
- Tightened `strict_answer_only` prompt with explicit no-explanation/no-steps/no-reasoning instruction.
- Added strict condition decoding profiles:
  - `strict_answer_only`: `max_new_tokens=12`
  - `strict_answer_only_prefill_answer`: `max_new_tokens=8`
- Kept `visible_cot` and `r1_style_thinking` unchanged.
- Added `alright`, `hmm`, and `wait` as visible/meta-reasoning markers after the first strictfix rerun exposed them.

### Tests and image

- Tests: `62 passed, 2 warnings`
- Final ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:9b5895db173f`
- Build run: `cm6`
- Digest: `sha256:267e422baaad24b577ac103af9c9ca2af56295780eaa0804161aa4ff6d4fe189`

### Azure rerun

- First strictfix job: `job-jspace-p1-strictfix`, execution `job-jspace-p1-strictfix-sq17fi0`
- Final strictfix2 job: `job-jspace-p1-strictfix2`
- Final execution: `job-jspace-p1-strictfix2-1sjj2n5`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot-strictfix2/20260709T025356Z`

### Review

- Cells completed: 12.
- `strict_answer_only`: no-CoT valid rate `0.0000` for depths 1/2/3; visible reasoning marker rate `1.0000`.
- `strict_answer_only_prefill_answer`:
  - depth 1: no-CoT valid `1.0000`, visible reasoning marker `0.0000`, parse ambiguity `0.0000`, accuracy `0.0000`.
  - depths 2/3: still no-CoT invalid due meta-reasoning markers (`Alright`, `Wait`).
- `visible_cot` and `r1_style_thinking`: no-CoT validity reported as `NA`, not judged as strict no-CoT.

### Current decision

- Direct `Answer:` prefill improves visible-reasoning suppression on the easiest item but produces incomplete/wrong answers and still leaks meta-reasoning on harder items.
- Prompt-only strict no-CoT is still not established for this model/task setup.
- Do not expand Phase 1 yet.
- Next step should test a carefully labeled stop-sequence / post-processing experiment while preserving raw-output validation.
- Scientific conclusion remains infrastructure + behavioral sanity only; no J-space claim.

## Raw-vs-Postprocessed Answer-only Evaluation (2026-07-09)

### Main fix

- Added `strict_answer_only_postprocessed`.
- Raw output is preserved.
- Postprocessed output is stored separately.
- Raw no-CoT validity and postprocessed answer validity are reported separately.
- Postprocessing does not count as genuine raw no-CoT compliance.

### Code and tests

- Added `src/jspace_observation/postprocess.py`.
- Extended Phase 1 records and metrics with postprocessing fields.
- Tests: `68 passed, 2 warnings`.

### ACR image and job

- Final ACR image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:9342ef130d46`
- Build run: `cm8`
- Digest: `sha256:3fc9e9d58b0ce6d5ea8a260cb7c172aa7cebfbe31427f94ee8cdae8d3b2a9ed1`
- Job: `job-jspace-p1-postprocess`
- Successful execution: `job-jspace-p1-postprocess-gor0o1r`
- Blob prefix: `phase1-pilot-postprocess/20260709T044224Z`
- Files: generation JSONL, eval JSONL, metrics CSV, summary MD

### Rerun review

- Cells completed: 12.
- `strict_answer_only_postprocessed` raw no-CoT valid rate: `0.0000` for all depths.
- `strict_answer_only_postprocessed` postprocessed no-CoT valid rate: `1.0000` for all depths.
- Postprocessing applied rate: `1.0000` for all depths.
- Postprocessing success rate:
  - depth 1: `1.0000`
  - depth 2: `0.0000`
  - depth 3: `1.0000`
- Accuracy postprocessed:
  - depth 1: `1.0000`
  - depth 2: `0.0000`
  - depth 3: `0.0000`

### Current decision

- Postprocessing can recover a clean correct answer in the easiest cell, but raw output still violates no-CoT.
- Postprocessing is useful as an answer-recovery analysis, not as evidence of no-CoT generation.
- Do not claim hidden reasoning or J-space evidence.
- Next step: decide whether to test stop-sequence generation controls or keep postprocessing as a separate answer-recovery analysis only.

## Private Blob Path + Stop-controlled Pilot (2026-07-10)

### Stop-control implementation

- Condition: `strict_answer_only_stopped`
- Code/image commit: `c29852ab97b5`
- Tests: `73 passed, 2 warnings`
- ACR build: `cm9`
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:c29852ab97b5`
- Digest: `sha256:2919bfa04dbcef0998cd9d770ffc91992958840d52ad512ab8b20b41dd434098`

The condition preserves:

- `raw_output_before_stop_cleanup`
- `raw_output`
- `stopped_output`
- raw, stopped, and postprocessed no-CoT validity separately
- stop trigger, string, reason, mode, and warning

### Private network

- VNet: `vnet-jspace-observation-sea`
- Active ACA subnet: `snet-aca-jspace-sea-v2` (`10.80.4.0/23`)
- Private endpoint subnet: `snet-pe-jspace-sea` (`10.80.2.0/27`)
- Blob private endpoint: `pe-stjspacefiles-blob-sea`
- Private endpoint state: `Succeeded` / `Approved`
- Private IP: `10.80.2.4`
- Private DNS zone: `privatelink.blob.core.windows.net`
- DNS link: `link-vnet-jspace-observation-sea-blob`
- Active environment: `cae-jspace-observation-sea-vnet2`
- Active environment state: `Succeeded`
- Workload profile: `gpu-t4` / `Consumption-GPU-NC8as-T4`

The first environment, `cae-jspace-observation-sea-vnet`, was created before the subscription feature `Microsoft.Network/AllowBringYourOwnPublicIpAddress` was registered. It reports `Succeeded` at the resource layer but cannot start containers. It was retained and is not the active environment.

### Blob network smoke

- Job: `job-jspace-blob-net-smoke-v2`
- Execution: `job-jspace-blob-net-smoke-v2-l02nljz`
- Status: `Succeeded`
- Prefix: `network-smoke-v2/20260710T071144Z`
- Uploaded: `smoke.txt`
- Authentication: user-assigned managed identity only
- Storage key/SAS/public network: not used

### Stop-control rerun

- Job: `job-jspace-p1-stopcontrol-vnet`
- Execution: `job-jspace-p1-stopcontrol-vnet-b55p4c6`
- Status: `Succeeded`
- Blob prefix: `phase1-pilot-stopcontrol-vnet/20260710T072107Z`
- Files uploaded: 4
- Cells: 15

`strict_answer_only_stopped` results:

| Depth | Raw no-CoT valid | Stopped no-CoT valid | Stop triggered | Stop success | Accuracy stopped | Parse ambiguous |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| 2 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

Representative outputs:

- Depth 1 raw: `7 + 5 = \boxed{12}\n\n`; stopped: `7 + 5 = \boxed{12}`; correct.
- Depth 2 raw: `__________\n\n`; stopped: `__________`; parse failed.
- Depth 3 raw: `\boxed{12}\n\n`; stopped: `\boxed{12}`; parsed but wrong.

All three stops were triggered by `\n\n`. In this run, the generation-time criterion prevented any subsequent reasoning marker from being emitted, so raw and stopped no-CoT validity were both `1.0000`. This is still an intervention: stop-controlled validity does not establish spontaneous raw no-CoT reasoning.

### Current decision

- Do not expand the experiment yet.
- Treat raw strict, stopped, and postprocessed conditions as distinct branches.
- Stop control preserves answer quality only in the easiest cell and destroys or fails to recover useful answers at depths 2/3.
- No hidden-reasoning or J-space claim is supported.

## Phase 1 Branch Taxonomy and Reporting Semantics (2026-07-10)

Phase 1 answer-control conditions are now divided into three non-interchangeable branches:

| Branch | Canonical key | Conditions |
|---|---|---|
| Raw strict no-CoT feasibility | `raw_strict` | `strict_answer_only`, `strict_answer_only_prefill_answer` |
| Stop-controlled generation intervention | `stopped_intervention` | `strict_answer_only_stopped` |
| Postprocessed answer-recovery utility | `postprocessed_utility` | `strict_answer_only_postprocessed` |

Report/schema updates:

- Records include stable branch metadata.
- Raw, stopped, and postprocessed outputs, no-CoT validity, and correctness remain separate.
- Metrics CSV includes branch labels and branch-specific accuracy columns.
- Summaries include a branch-level table and use `NA` for non-applicable metrics.
- The legacy `accuracy` field follows `eval_output_used` and must not be used for cross-branch comparisons.

Interpretation boundaries:

- Stopped validity is generation-time intervention output, not spontaneous no-CoT.
- Postprocessed validity is extracted-surface validity, not raw no-CoT.
- No Phase 1 branch by itself is hidden-reasoning or J-space evidence.

Local validation:

```text
python -m pytest tests\ -q
80 passed, 2 warnings
```

Azure state:

- Rerun performed for this update: no.
- Active environment: `cae-jspace-observation-sea-vnet2`.
- Inactive retained environment: `cae-jspace-observation-sea-vnet`.
- Latest stop-control execution: `job-jspace-p1-stopcontrol-vnet-b55p4c6`.
- Active persisted result prefix: `phase1-pilot-stopcontrol-vnet/20260710T072107Z`.
- Private Blob network path: fixed and operational.

Current blocker: none.

## Phase 1 Branch-specific Success Criteria (2026-07-10)

The criteria in `docs/phase1_experiment_branches.md` are fixed before any new data collection:

| Branch | Passing classification | Core gate |
|---|---|---|
| `raw_strict` | `raw_strict_preliminarily_established` | `n >= 3`, surface/parsing/format gates, absolute accuracy `>= 0.50`, plus the relative gate when the visible-CoT baseline is valid. |
| `stopped_intervention` | `stopped_intervention_usable` | `n >= 3`, stopped validity, stop success, parse validity, absolute accuracy `>= 0.50`, plus the relative gate when the baseline is valid. |
| `postprocessed_utility` | `postprocessed_answer_recovery_usable` | `n >= 3`, validity/recovery/warning gates, non-degradation, and absolute accuracy `>= 0.50`. |

Report changes:

- Every reported branch result includes sample-size sufficiency and provisional status.
- Missing required metrics fail their criterion; non-applicable metrics remain `NA`.
- Visible-CoT relative gates require baseline `n >= 3`, parse-valid rate `>= 0.80`, and accuracy `> 0`; otherwise they are `NA`.
- Reports include criteria passed/failed/not-applicable, matching baseline fields, stop-trigger rate, stop-string distribution, and postprocessing warning/application rates.
- The mandatory warning states that classifications are behavioral and operational, not hidden-reasoning, internal-workspace, or J-space evidence.

Local validation:

```text
python -m pytest tests\ -q
109 passed, 2 warnings
```

Execution state:

- Historical fixed-scope Azure validation run performed: yes.
- Azure rerun for gate hardening: no.
- Local model inference for gate hardening: no.
- ACR rebuild for gate hardening: no.
- Active environment: `cae-jspace-observation-sea-vnet2`.
- Active Blob prefix: `phase1-pilot-criteria-validation/20260710T135655Z`.
- Current infrastructure blocker: none.

## Phase 1 Criteria-validation Pilot (2026-07-10)

Provenance:

- ACR build: `cma`.
- Image: `acrjspaceobssea0708231738.azurecr.io/j-space-observation:f94e889ef608`.
- Digest: `sha256:f27cc0e4cea0ae9569dbb384598fb391f3b923022ce9257f8301684c9dc23806`.
- Job: `job-jspace-p1-criteria-val`.
- Execution: `job-jspace-p1-criteria-val-6s8p15p`.
- Status: `Succeeded`.
- Cells: `15`.
- Blob files: `4`.

Approved scope:

- One model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- One task family: `arithmetic`.
- Depths: `1,2,3`.
- Five conditions.
- Items per cell: `1`.
- No model, task, depth, or item-count expansion.

Classification result:

| Depth | Raw strict | Stopped intervention | Postprocessed utility |
|---|---|---|---|
| 1 | `surface_answer_only_but_task_failed` | `stopped_intervention_usable` | `postprocessed_answer_recovery_usable` |
| 2 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_warning_high` |
| 3 | `raw_strict_not_established` | `stopped_surface_compliant_but_task_failed` | `postprocessed_answer_recovery_usable` |

Key depth 1/2/3 metrics:

- Raw-strict `raw_no_cot_valid_rate`: `1.0000 / 0.0000 / 0.0000`.
- Raw-strict `accuracy_raw`: `0.0000 / 0.0000 / 0.0000`.
- Stopped `raw_no_cot_valid_rate`: `1.0000 / 1.0000 / 1.0000`.
- `stopped_no_cot_valid_rate`: `1.0000 / 1.0000 / 1.0000`.
- `stop_triggered_rate`: `1.0000 / 1.0000 / 1.0000`.
- `accuracy_stopped`: `1.0000 / 0.0000 / 0.0000`.
- Postprocessed `raw_no_cot_valid_rate`: `0.0000 / 0.0000 / 0.0000`.
- `postprocessed_no_cot_valid_rate`: `1.0000 / 1.0000 / 1.0000`.
- `postprocessing_success_rate`: `1.0000 / 0.0000 / 1.0000`.
- `postprocessing_warning_rate`: `0.0000 / 1.0000 / 0.0000`.
- `accuracy_postprocessed`: `1.0000 / 0.0000 / 0.0000`.

Validation outcome:

- The real summary includes branch classifications, criteria passed/failed, interpretation warnings, and stop-string distribution.
- The stop string distribution is `"\n\n"=1` at each stopped depth.
- Depth 3 postprocessed utility is mechanically usable because `accuracy_postprocessed >= accuracy_raw` is `0 >= 0`; this is not task success.
- The depth 3 raw relative-accuracy criterion also passes against a zero visible-CoT baseline, while raw surface criteria correctly fail.
- These limitations require a prospective criteria decision before another run; this run is not reclassified.
- Results are behavioral and operational only.
- Stop-controlled validity is not spontaneous no-CoT.
- Postprocessed validity is not raw no-CoT.
- No hidden-reasoning, internal-workspace, or J-space claim is supported.

## Phase 1 Branch-gate Hardening (2026-07-10)

Prospective rules:

- Formal success labels require `n >= 3`; otherwise an otherwise-passing result becomes `raw_strict_pilot_only`, `stopped_intervention_pilot_only`, or `postprocessed_utility_pilot_only`.
- Explicit metric failures retain failure labels below the minimum sample size.
- Raw and stopped branches always require absolute accuracy `>= 0.50`.
- Their relative gate is applied only when matching visible-CoT `n >= 3`, parse-valid rate `>= 0.80`, and accuracy `> 0`; otherwise it is `NA`.
- Postprocessed utility requires non-degradation and `accuracy_postprocessed >= 0.50`.
- Postprocessed visible-CoT comparison is report-only.

Historical regression interpretation:

- The completed Blob summary remains unchanged under the earlier criteria.
- Depth-1 stopped and postprocessed rows would now be `pilot_only` because `n=1`.
- The depth-3 postprocessed `0 >= 0` case now becomes `postprocessed_surface_clean_but_task_failed`.
- The pilot's matching visible-CoT rows have `n=1`, so relative gates are unavailable rather than passed.

No Azure job, model inference, model download, ACR rebuild, or scale increase occurred during hardening. Results remain behavioral and operational only. Stopped output remains intervention-controlled, postprocessed output remains distinct from raw no-CoT, and no hidden-reasoning or J-space claim is supported.

## Bounded Phase 1 n=3 Validation (2026-07-10)

Scope and provenance:

- Starting commit: `d1750a9d51e102c644933d8c41b7d65432f8bdfa`.
- Source commit: `359643b7b5eb8f95c13cca2e60fa753df8701282`.
- Tests: `111 passed, 2 warnings`.
- Dry-run: `configuration_cells=15`, `items_per_cell=3`, `total_observations=45`.
- ACR build: `cmb`.
- Image digest: `sha256:004ec8bff66fbc8a23b122660aeb58914b2ee3cedfc5246429046eef252c9069`.
- Job: `job-jspace-p1-n3-gates`.
- Sole execution: `job-jspace-p1-n3-gates-02ilmgm`; status `Succeeded`; retries `0`.
- Blob prefix: `phase1-limited-n3-gates/20260710T152820Z`.
- Artifacts: four files; 45 generation records, 45 eval records, 15 metric rows, every row `n=3`.

Visible-CoT baseline:

| Depth | n | Accuracy | Parse valid | Baseline valid | Failure reason |
|---|---:|---:|---:|---|---|
| 1 | 3 | 0.3333 | 1.0000 | true | `NA` |
| 2 | 3 | 0.6667 | 1.0000 | true | `NA` |
| 3 | 3 | 0.0000 | 1.0000 | false | `visible_cot_accuracy_zero` |

Branch classifications:

| Depth | Raw strict | Stopped intervention | Postprocessed utility |
|---|---|---|---|
| 1 | `raw_strict_not_established` | `stopped_intervention_usable` | `postprocessed_answer_recovery_usable` |
| 2 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_task_failed` |
| 3 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_task_failed` |

Key interpretation:

- All nine rows meet the registered sample-count gate; this means registered-gate sufficiency only, not statistical stability.
- Raw strict was not established at any depth.
- Stopped depth-1 usability is intervention utility; it is not spontaneous no-CoT.
- Postprocessed depth-1 usability is answer-recovery utility; it is not raw no-CoT.
- Depth-3 postprocessed non-degradation is `0 >= 0`, but absolute accuracy fails, so it is not usable.
- Depth-3 relative gates are `NA`, not passed or failed.
- Classification audit independently recomputed all nine rows with zero mismatches.
- Count/aggregate audits passed. The subsequent private-path record audit found zero duplicate, missing, membership, common-field, transformation, parser, metric, or classification mismatches.
- No hidden-reasoning, internal-workspace, genuine invisible-reasoning, or J-space claim is supported.

This decision was superseded by the completed all-45 semantic audit below.

## Phase 1 All-45 Semantic Parser Audit (2026-07-15)

The preregistered two-stage blinded review of all 45 historical arithmetic
records from `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` is complete.

Provenance:

```text
protocol/tooling commit: cfa99fc6e204db5cf1076a13a8975e13db226931
source writer commit: 359643b7b5eb8f95c13cca2e60fa753df8701282
source prefix: phase1-limited-n3-gates/20260710T152820Z
semantic parent prefix: phase1-semantic-audits/all45-parser-underflag-20260715T094500Z
image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:cfa99fc6e204
digest: sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac
environment/profile: cae-jspace-observation-sea-vnet2 / Consumption
resources/GPU: 2 CPU / 4Gi / none
```

Review completion:

- Two independent `gpt-5.6-sol/max` reviewers completed 45 Stage-1 and 45
  Stage-2 rows each.
- Four records (`R002`, `R009`, `R018`, `R022`) required blinded arbitration
  by a distinct `gpt-5.6-sol/max` arbiter.
- Final unresolved count is zero.
- Semantic category, presence, and status exact agreement were `0.9556`,
  `0.9778`, and `0.9778`.

Audit-only result:

- true multiple-candidate ambiguity: `0`;
- parser overflags: `18`, all in visible-reasoning conditions;
- parser underflags: `0`;
- observed extraction errors: `14`;
- material correctness errors: `2` (`R019`, `R038`, both `visible_cot`
  depth 1);
- material evaluator issues: `19`;
- official stored metrics/classifications modified: no.

The audit-only `visible_cot` depth-1 accuracy is `1.0000`, versus stored
`0.3333`. The audit-only depth-2 visible-CoT parse-valid rate is `0.6667`, so
that baseline becomes invalid and associated relative gates become `NA`.
Four baseline/gate fields change, but none of the nine final branch
classification labels changes.

Decision: preregistered **Path C**. Higher-n replication remains paused.
The next action is a locked evaluator validation set and prospective parser-v2
protocol before any new model run. No parser or historical artifact was
changed.

Detailed report: `reports/phase1_n3_all45_semantic_audit.md`.

Persistent outputs:

```text
final machine prefix:
phase1-semantic-audits/all45-parser-underflag-20260715T094500Z/final

machine upload execution:
job-jspace-p1-all45-pack-vi79nml

report prefix:
phase1-semantic-audits/all45-parser-underflag-20260715T094500Z/report

report upload execution:
job-jspace-p1-all45-pack-61s3ggf
```

Both executions succeeded through the private managed-identity path. The nine
machine artifacts used exact membership, manifest-last upload, and per-file
download/hash verification. The report was kept outside that membership and
was independently downloaded and hash-verified. All five independent post-run
checks passed. The transport secret was removed and the job is idle.

## Path C Phase 1.2A Evaluator Validation Set (2026-07-16)

Phase 1.2A preregistered, constructed, independently labeled, validated, and
privately sealed the prospective parser-v2 evaluator set.

Frozen provenance:

```text
starting commit: 58d299bb66c5536a0f1b7d0617204472fbb8c212
final protocol commit: cc93ffe603ab8338ed860586a52b1911af4b3277
tooling/development commit: e7a95a458d05d4ef211bb6902c2a20cb5f16bf60
sealed no-Git validation commit: 9b4262a9d35e6342935b8d2f72887a56c5f98486
protocol bundle: 5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666
acceptance gates: a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988
```

Dataset:

- Development: 60, exactly five per S01-S12.
- Locked: 120, exactly ten per S01-S12.
- Locked support: 80 present, 10 ambiguous, 30 no answer.
- Locked critical/material cases: 80/68.
- Exact, normalized, cross-set template, and historical hard overlaps: zero.
- Reviewed near-duplicate findings: 37, all dispositioned.
- Public development SHA-256:
  `bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27`.

Independent labeling:

- Stage-1 A/B: 120/120 each, reference-blind.
- Stage-1 arbitration: 57; Stage-2 arbitration: 0.
- Stage-2 A/B correctness agreement: 120/120, kappa 1.
- Final labels: 120; unresolved: 0.
- Seven review seals validate.
- Labels are LLM operational consensus references, not human ground truth.

Private release:

```text
parent: phase1-evaluator-validation/parser-v2-v1/20260716T024856Z
artifacts: 26
final labels: 44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af
locked-label manifest: aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6
overall manifest: f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260
validation report: 5b3daf44553a7c99d57c8d5a117ef82de113c4b5cde74ef13dd218c11c56b641
```

Azure persistence:

- ACR build `cmf` failed safely against the frozen all-45 Docker attestation;
  no image, execution, or Blob write resulted.
- Encrypted overlay build `cmg` used immutable base digest
  `sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac`.
- The sole CPU execution, `job-jspace-parser-v2-set-ib7uc0e`, succeeded in
  `cae-jspace-observation-sea-vnet2` on Consumption with 2 CPU / 4 GiB and no
  GPU.
- Managed identity, private Blob, `overwrite=false`, reservation-first,
  manifest-last, exact 26-object membership, and per-object re-download
  verification were enforced.
- The job is reset to the immutable base with `/bin/true`; secrets and secret
  references are zero.
- The temporary transport tag/digest and local encrypted build context were
  deleted.

All five independent post-sealing reviews passed. Final model-free tests:
`460 passed, 2 warnings`.

The holdout is `SEALED`, not evaluated. At sealing time parser v2 was not
implemented; it was subsequently developed from only the public set. Locked
inputs have not been exposed for evaluation, and no acceptance-gate result
exists. No target-model download/load/inference, higher-n run, new behavioral
evidence, hidden-reasoning claim, or J-space claim occurred during sealing.

Detailed report: `reports/phase1_parser_v2_validation_set.md`.

## Phase 1 n=3 Record-Level Artifact Audit (2026-07-11)

Provenance:

```text
starting commit: a4bbf8911e0f758eb10230e52c6e953ef8df9cee
audit implementation commit: 9537ed8e0b5da95b68714b73fa11236b48ee046a
tests: 139 passed, 2 warnings
ACR build: cmc
image: acrjspaceobssea0708231738.azurecr.io/j-space-observation:9537ed8e0b5d
digest: sha256:90adfc1b6be6fbb7a17a878bed7970ffd71c62b72263a36b41110ba6f19b169b
environment/profile: cae-jspace-observation-sea-vnet2 / Consumption
job: job-jspace-p1-record-audit
execution: job-jspace-p1-record-audit-d9q5uy8
status: Succeeded
GPU used: no
model inference: no
new observations: no
```

Source and output:

```text
source: phase1-limited-n3-gates/20260710T152820Z
audit output: phase1-audits/n3-gates-20260710T152820Z/20260711T010339Z
source modified: no
audit files uploaded: 8
```

Deterministic result:

- 45/45 generation records and 45/45 eval records are valid JSONL.
- Composite key: `model_name, task_family, depth, condition, task_id`.
- 45 unique keys per side; zero duplicates or one-sided keys.
- All 15 cells contain exactly three registered, unique items.
- Registered answers, common fields, selected-output transformations, parser
  replay, and correctness aliases have zero mismatches.
- All 15 metric rows match with maximum absolute difference `0.0`.
- All nine branch classifications and criteria lists match.
- Depth-3 postprocessed `0 >= 0` remains task-failed because the absolute floor
  fails.
- Before/after source Blob properties are unchanged.

Ambiguous-parse review:

- Two independent `gpt-5.6-sol/max` reviewers audited all 18 flagged records.
- Exact category agreement: `17/18`; Cohen's kappa: `0.6471`.
- Any field-level disagreement triggered arbitration: `14` records.
- Arbiter unresolved records: `0`.
- Final audit opinion: `17` parser overflags and `1` true multiple-candidate
  ambiguity.
- Final answer statuses: `6` correct, `1` incorrect, `1` ambiguous, and `10`
  with no answer.
- Stored parser/correctness fields are mechanically consistent for all 18.
  Records 2 and 3 expose semantic answer-extraction limitations rather than
  artifact corruption.
- Reviewing only flagged records cannot rule out underflags among the other 27.

Detailed report: `reports/phase1_n3_record_audit.md`.

## GHCR Workflow Run + T4 Quota Findings (2026-07-08 22:00 +08:00)

- Baseline: read `docs/thread_handoff.md`; repo was synced to `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Workflow file installed: `.github/workflows/build-ghcr.yml` exists and matches `infra/ci/build-ghcr.yml`.
- Installation note: the local `gh` token still lacks GitHub `workflow` OAuth scope, but the workflow was successfully installed through the GitHub connector / GitHub App path in commit `c07db5c9625a9f9ad96c55f77385c078e11d4a66`.
- Workflow trigger: `gh workflow run build-ghcr.yml -R Alanjiao1988/J-space-observation --ref main -f push_latest=true`.
- Workflow run: `28947916765`, completed successfully.
- Workflow URL: `https://github.com/Alanjiao1988/J-space-observation/actions/runs/28947916765`
- GHCR image pushed:
  - `ghcr.io/alanjiao1988/j-space-observation:c07db5c9625a9f9ad96c55f77385c078e11d4a66`
  - `ghcr.io/alanjiao1988/j-space-observation:latest`
- Package API note: current `gh` token lacks `read:packages`, so package version API checks return 403; the workflow logs confirm both image tags were pushed.
- Diff from image commit `c07db5c...` to latest repo commit `c10afdd...`: documentation-only (`docs/*.md`, `reports/current_status.md`); image rebuild not required.
- Providers: `Microsoft.App` = `Registered`, `Microsoft.ContainerRegistry` = `Registered`, `Microsoft.Quota` = `Registered`.
- Azure resource check: no `jspace` / `j-space` resource groups found.
- T4 GPU workload profile type availability: `Consumption-GPU-NC8as-T4` is offered in `southeastasia`.
- `az quota list` and `az quota usage list` for `Microsoft.App` / `southeastasia` returned `ManagedEnvironmentCount`, `SessionPools`, `SubscriptionDedicatedNCA100Gpus`, and `ExpressEnvironmentCount`, but did **not** expose a T4 / NC8as-T4 / Managed Environment Consumption T4 quota item.
- **T4 GPU quota (subscription): still unknown via CLI.** Use Azure Portal Usage + quotas or Azure support to confirm/request Container Apps Managed Environment Consumption T4 GPUs in `southeastasia`.
- Azure resources created: none.

### Remaining blocker

1. Confirm Container Apps **T4 GPU quota in southeastasia** via Azure Portal (Usage + quotas) or Azure support. CLI quota query did not expose the required T4 quota item.

## Azure GHCR Smoke Path Attempt (2026-07-08)

Alan explicitly approved minimal Azure resource creation to validate the deployment path instead of continuing to block on invisible quota.

### Resources Created

- Resource group: `rg-jspace-observation-sea` (`southeastasia`)
- Log Analytics workspace: `law-jspace-observation-sea`
- Container Apps environment: `cae-jspace-observation-sea`
- Workload profile: `gpu-t4` (`Consumption-GPU-NC8as-T4`)
- Jobs: none created successfully

### T4 / Quota Validation

- `Consumption-GPU-NC8as-T4` workload profile creation succeeded.
- No quota error occurred during environment/profile creation.
- GPU job execution has not yet succeeded, because GHCR image pull was blocked before job creation.

### Errors Encountered

1. Container Apps environment with `--enable-dedicated-gpu true` failed:
   - Error code: `WorkloadProfileInvalidType`
   - Message: `Workload profile type 'NC24_A100' is invalid.`
   - Fix: create environment without `--enable-dedicated-gpu true`.
2. Adding T4 profile with `--min-nodes/--max-nodes` failed:
   - Error code: `WorkloadProfilePropertyNotSupported`
   - Message: `Workload Profile property 'MinimumCount' is not supported for CONSUMPTION_GPU_NC8AS_T4`
   - Fix: omit min/max for the consumption GPU profile.
3. GHCR smoke job creation failed before execution:
   - Error code: `InvalidParameterValueInContainerTemplate`
   - Message includes: `UNAUTHORIZED: authentication required`
   - Classification: GHCR private package / registry authentication required

### Current Blocker

Azure Container Apps cannot pull the GHCR image anonymously. Next step is one of:

1. Make the GHCR package public; or
2. Provide GHCR credentials through a secure path (`GHCR_USERNAME` + `GHCR_PAT` with minimal `read:packages`), then create the registry secret / rerun `job-jspace-ghcr-smoke`.

Do not send token values in chat and do not commit them.

### GHCR Auth Retry Result

- `GHCR_PAT`: not set.
- `GHCR_USERNAME`: defaulted to `Alanjiao1988`.
- `gh auth token`: available and used as an Azure registry secret for a retry (token value not printed/logged).
- Job creation still failed:
  - Error code: `InvalidParameterValueInContainerTemplate`
  - Message includes: `DENIED: requested access to the resource is denied`
  - Classification: available `gh auth token` is insufficient for Azure to pull the private GHCR image.
- Jobs created successfully: none.
- Phase 0.5 / Phase 1 dry-run / small pilot: not attempted.

Current actionable options:

1. Make the GHCR package public; or
2. Provide a classic PAT with `read:packages` through a secure local environment variable (`GHCR_PAT`) or an approved Azure secret path. Do not send the token in chat.

### GHCR Auth Preflight Update

- `GHCR_PAT` is still not set.
- Current `gh auth token` was tested against the GHCR package versions API.
- Result: `403` with message `You need at least read:packages scope to get a package's versions.`
- Decision: do not retry Azure job creation with the known-insufficient token.
- No new Azure resources were created in this step.

### GHCR_PAT Visibility Update

- Alan set `GHCR_USERNAME` / `GHCR_PAT` in a local PowerShell shell, but the Copilot tool process could not see them.
- Checked Process/User/Machine environment scopes:
  - `GHCR_USERNAME`: not visible
  - `GHCR_PAT`: not visible
- No package-read preflight or Azure job retry was attempted in this step.
- Existing Azure resources remain unchanged.

To retry, set the variables in Windows User environment (not only shell-local), then start a new request:

```powershell
[Environment]::SetEnvironmentVariable("GHCR_USERNAME", "Alanjiao1988", "User")
[Environment]::SetEnvironmentVariable("GHCR_PAT", "<classic PAT with read:packages>", "User")
```

Do not paste the token into chat.

### GHCR_PAT Visibility Retry

- Alan reported setting `GHCR_USERNAME` / `GHCR_PAT` as Windows User environment variables and restarting VS Code / Copilot agent / terminal.
- Copilot re-checked Process/User/Machine environment scopes.
- `GHCR_USERNAME`: still not visible.
- `GHCR_PAT`: still not visible.
- GHCR package-read preflight was not run because no PAT was visible.
- Azure smoke job was not retried.
- Existing Azure resources remain unchanged.

Current blocker remains: the agent process cannot read a valid `GHCR_PAT`. Next action is to provide a secure token path visible to the agent or make the GHCR package public.

### Script Update

`infra/azure/scripts/05_run_job_ghcr.sh` has been updated to match the actual Azure resource names and the live CLI findings:

- defaults now use `rg-jspace-observation-sea`, `cae-jspace-observation-sea`, and `job-jspace-ghcr-smoke`;
- removed `--enable-dedicated-gpu true` from environment creation;
- removed `--min-nodes/--max-nodes` from the T4 workload profile add command;
- uses ARM REST job creation/update to avoid Azure CLI `--args -lc ...` parsing issues;
- places `workloadProfileName` at `properties.workloadProfileName`, which is the schema position validated by live Azure errors;
- falls back to `gh auth token` only when `GHCR_PAT` is absent;
- supports Alan's requested env var aliases: `JOB_NAME`, `CONTAINERAPPS_ENVIRONMENT`, and `WORKLOAD_PROFILE_NAME`;
- no longer passes the GHCR token as a Python command-line argument while generating the ARM body;
- added project tags to resources created by the script.

## GHCR + T4 Quota Path Status (2026-07-08 21:34 +08:00)

- Read-only provider re-check: `Microsoft.ContainerRegistry` = `Registered`, `Microsoft.App` = `Registered`.
- **Decision locked:** GHCR is the **primary** registry path; ACR is a **secondary fallback** only (used if GHCR fails). Rationale: git-SHA image provenance, GitHub-hosted builds, and decoupling from ACR provider timing.
- GHCR workflow template `infra/ci/build-ghcr.yml`: **valid**.
- GHCR Azure job script `infra/azure/scripts/05_run_job_ghcr.sh`: **valid** (parameterized; `JOB_COMMAND` override).
- Runbook now includes a gated **Planned Azure command sequence**: T4 quota -> resource group -> Container Apps env + GPU profile -> GHCR image smoke test -> Phase 0.5 `--skip-fit` -> Phase 1 `--dry-run` -> small Phase 1 pilot.
- GHCR workflow installed and run successfully.
- Next Azure gate: **confirm T4 GPU quota in southeastasia**.
- Local checks: `41 passed, 2 warnings`; Phase 1 dry-run `54` cells.
- Azure resources created: **none**.

### Next step

Confirm Azure Container Apps **T4 GPU quota for southeastasia** before any GPU job (portal, support request, or approved `Microsoft.Quota` registration and read-only quota query).

## Azure-first Policy (2026-07-08)

- Local validation is complete.
- Local PC is now limited to orchestration, tests, dry-runs, documentation, Git, and Azure CLI commands.
- Heavy execution must run on Azure GPU containers:
  - model download
  - model loading
  - Phase 0.5 fitting / model loading
  - Phase 1 real generation
  - later J-lens, patching, and ablation experiments
- Do not run real Phase 1, model downloads, or J-lens fitting locally.
- Do not silently fall back to local inference if Azure is blocked.

## Azure Readiness Status (2026-07-08)

- Azure CLI: available (`2.83.0`).
- Active subscription: `MCAPS-Hybrid-REQ-125620-2025-alanjiao`.
- Subscription state: `Enabled`.
- Microsoft.App provider: `Registered`.
- Microsoft.ContainerRegistry provider: `Registered`.
- containerapp extension: installed (`1.3.0b4`).
- Azure resources created: none.
- Azure scripts are prepared for:
  - no-resource readiness checks;
  - ACR build/push;
  - Phase 0.5 Azure availability/model-loading job;
  - Phase 1 Azure dry-run job;
  - small real Phase 1 pilot job.

## Azure Blockers Before Execution

- Verify Azure Container Apps GPU T4 quota for `southeastasia` and workload profile `Consumption-GPU-NC8as-T4`.
- Do not run real inference or model loading locally as a fallback.

## Historical Azure Readiness Gate Re-check (2026-07-08; superseded)

- Microsoft.ContainerRegistry: `Registering`.
- Microsoft.App: `Registered`.
- T4 GPU quota status: not checked because `Microsoft.ContainerRegistry` is still not `Registered`.
- Readiness script: not run.
- Azure resources created: none.
- Current status has superseded this: `Microsoft.ContainerRegistry` is now `Registered`.

## Historical Azure Provider Gate Re-check (2026-07-08 18:39 +08:00; superseded)

- Microsoft.ContainerRegistry: `Registering`.
- Microsoft.App: `Registered`.
- T4 GPU quota status: not checked because the provider gate remains blocked.
- Readiness script: not run.
- Azure resources created: none.
- Current status has superseded this: `Microsoft.ContainerRegistry` is now `Registered`.

## Historical Azure Provider Gate Re-check (2026-07-08 18:41 +08:00; superseded)

- Microsoft.ContainerRegistry: `Registering`.
- Microsoft.App: `Registered`.
- T4 GPU quota status: not checked because the provider gate remains blocked.
- Readiness script: not run.
- Azure resources created: none.
- Current status has superseded this: `Microsoft.ContainerRegistry` is now `Registered`.

## Next Command

After `Microsoft.ContainerRegistry` is registered and GPU quota is confirmed:

```powershell
.\infra\azure\scripts\00_check_prereqs.ps1
```

or:

```bash
bash infra/azure/scripts/00_check_prereqs.sh
```

## Latest Local Validation (2026-07-08)

### Validation Results

- Repository state: `main` synced with `origin/main` before validation.
- Tests: `python -m pytest tests/ -v` -> `41 passed, 2 warnings`.
- Phase 0.5 availability/model-loading check: completed.
  - Output directory: `results/runs/20260708_181325`
  - Summary: `results/runs/20260708_181325/phase0_5_summary.md`
  - Pre-fitted lenses found locally/configured: no.
  - jacobian-lens installed/importable: no / no.
  - Model loading attempted: yes.
  - Model loading succeeded: no. Both configured models failed because `accelerate` is required for `device_map`.
  - Actual tiny J-lens fitting attempted: no.
  - Actual tiny J-lens fitting success: not attempted.
- Phase 1 dry run: completed.
  - Conditions included `strict_answer_only`, `visible_cot`, and `r1_style_thinking`.
  - Total cells: 54.
  - No model download or generation was performed by the dry run.
- Azure resources created: none.

## Local Environment Validation (2026-07-08)

### Environment Results

- Active Python executable: `C:\Users\alanjiao\AppData\Local\Programs\Python\Python313\python.exe`
- Core dependencies installed/importable: yes.
- `accelerate` is now installed/importable.
- External jacobian-lens install path: `C:\Users\alanjiao\external\jacobian-lens`
- jacobian-lens import result: yes, via `import jlens`.
- The project J-lens helper now recognizes the installed `jlens` module.

### Re-run Results

- Tests: `python -m pytest tests/ -v` -> `41 passed, 2 warnings`.
- Phase 0.5 availability/model-loading check:
  - Output directory: `results/runs/20260708_182022`
  - Summary: `results/runs/20260708_182022/phase0_5_summary.md`
  - Pre-fitted lenses found locally/configured: no.
  - jacobian-lens installed/importable: yes / yes.
  - Model loading succeeded for both configured models on CPU.
  - Actual tiny J-lens fitting attempted: no.
  - Actual tiny J-lens fitting success: not attempted.
- Phase 1 dry run:
  - Completed successfully.
  - Conditions included `strict_answer_only`, `visible_cot`, and `r1_style_thinking`.
  - Total cells: 54.
  - No generation was performed by dry run.
- Azure resources created: none.

### Blockers

- Real tiny J-lens fitting has not been attempted yet.
- No pre-fitted lenses were found locally/configured.
- Models load on CPU locally; real generation may be slow without GPU.

### Previous Local Pilot Command (superseded by Azure-first policy)

The equivalent small real Phase 1 pilot must be run via Azure, not locally:

```bash
bash infra/azure/scripts/04_run_phase1_pilot.sh
```

## What Has Been Implemented

### Core Python Modules

1. **config.py** - Configuration classes for models and experiments
   - `ModelConfig`: dtype, device_map, output_hidden_states
   - `NoCoTConfig`: Generation parameters and validation thresholds
   - `ExperimentConfig`: Directory management

2. **model_loader.py** - Hugging Face model loading
   - Loads models with proper dtype and device handling
   - Collects model info (layers, hidden size, GPU info)
   - Provides logging utilities

3. **no_cot.py** - Strict no-CoT prompt utilities
   - `construct_empty_think_prefill_prompt()`: For R1-Distill
   - `construct_answer_only_prompt()`: For other models
   - `validate_no_cot_output()`: Checks for think tags and reasoning
   - `create_generation_record()`: Structured record creation

4. **prompt_sets.py** - Pilot prompt datasets
   - ArithmeticPromptSet: 1-op, 2-op, 3-op tasks
   - SyntheticRelationPromptSet: 1-hop, 2-hop, 3-hop tasks
   - FactualCounterfactualPromptSet: Factual and counterfactual reasoning
   - ~15 total pilot items (scales to 50-100 in production)

5. **eval_parsing.py** - Answer evaluation
   - `parse_numeric_answer()`: Numbers including negatives and floats
   - `parse_entity_answer()`: Short string answers
   - `parse_yes_no_answer()`: Boolean questions
   - `evaluate_answer()`: Correctness scoring with numeric tolerance

6. **stats.py** - Statistical utilities
   - `wilson_ci()`: Confidence intervals for rates
   - `bootstrap_ci()`: Confidence intervals for continuous metrics
   - `compute_slope()`: Linear regression for depth gradients
   - `cot_gain_by_depth()`: CoT gain analysis

7. **run_logging.py** - Experiment tracking
   - `RunLogger`: Timestamped run directory creation
   - `SummaryBuilder`: Markdown summary generation
   - `create_run_metadata()`: Metadata JSON generation
   - `record_resource_usage()`: Wall-clock time and GPU memory

8. **jlens_utils.py** - J-lens utilities
   - `check_jacobian_lens_installed()`: Package availability
   - `check_prefitted_lens_locally()`: Pre-fitted lens search
   - `JacobianLensWrapper`: Unified interface

### Experiment Scripts

1. **experiments/phase0_5_jlens_spike.py**
   - Searches for pre-fitted J-lenses locally and online
   - Checks jacobian-lens package availability
   - Plans cost sweeps (prompt counts, sequence lengths, layer modes)
   - Validates model loading
   - Outputs: metadata.json, sweep configs, summary.md
   - Usage: `python experiments/phase0_5_jlens_spike.py --skip-fit`

2. **experiments/phase1_depth_gradient.py**
   - Runs generation experiments across models, tasks, depths, and conditions
   - Supports conditions: strict_answer_only, visible_cot, r1_style_thinking
   - Parses and evaluates answers
   - Computes accuracy, parse validity, no-CoT validity, latency
   - Outputs: generation records (JSONL), eval records (JSONL), metrics (CSV), summary (MD)
   - Usage: `python experiments/phase1_depth_gradient.py --items-per-cell 3`

### Unit Tests

All tests pass without requiring model downloads:

- **test_no_cot.py** (9 tests)
  - Prompt construction
  - No-CoT validation
  - Think tag detection
  - Visible reasoning detection
  - Token budget checking
  - Answer extraction

- **test_eval_parsing.py** (18 tests)
  - Numeric parsing (simple, negative, float, multiple)
  - Entity parsing
  - Yes/no parsing
  - Answer evaluation with tolerance

- **test_stats.py** (13 tests)
  - Wilson confidence intervals
  - Bootstrap CI
  - Slope computation
  - CoT gain calculation

### Azure Infrastructure

1. **infra/azure/scripts/00_check_prereqs.sh**
   - Verifies Azure CLI, Docker, Python packages
   - Checks Azure login and resource group
   - Creates resource group if needed

2. **infra/azure/scripts/01_build_and_push_image.sh**
   - Builds Docker image
   - Creates ACR if needed
   - Pushes to Azure Container Registry

3. **infra/azure/scripts/02_run_phase0_5.sh**
   - Submits Phase 0.5 job to Azure Container Instances
   - Logs to run_log.md

4. **infra/azure/scripts/03_run_phase1.sh**
   - Submits Phase 1 job to Azure Container Instances
   - Logs to run_log.md

### Build Automation

- **Makefile** with targets:
  - `make install`: Install project dependencies
  - `make test`: Run unit tests
  - `make phase0-5`: Run Phase 0.5 locally
  - `make phase1`: Run Phase 1 locally
  - `make phase1-dry`: Dry-run Phase 1
  - `make azure-setup`: Setup Azure infrastructure
  - `make azure-phase0-5`: Submit Phase 0.5 to Azure
  - `make azure-phase1`: Submit Phase 1 to Azure

## How to Run

### Setup (one-time)

```bash
cd J-space-observation
make install
```

### Run Tests

```bash
make test
```

### Run Phase 0.5 (J-lens feasibility spike)

```bash
make phase0-5
```

Output:
- `results/runs/<timestamp>/phase0_5_summary.md`
- `results/runs/<timestamp>/phase0_5_sweep_configs.json`
- `results/runs/<timestamp>/metadata.json`

### Run Phase 1 (behavioral depth gradient) - Dry Run

```bash
make phase1-dry
```

### Run Phase 1 (behavioral depth gradient) - Full

```bash
make phase1
```

Output:
- `results/runs/<timestamp>/phase1_generations.jsonl`
- `results/runs/<timestamp>/phase1_eval_records.jsonl`
- `results/runs/<timestamp>/phase1_metrics.csv`
- `results/runs/<timestamp>/phase1_summary.md`

### Run on Azure

```bash
make azure-setup
make azure-phase0-5
make azure-phase1
```

## Key Design Decisions

### No-CoT Implementation

- **For R1-Distill**: Uses empty-think prefill
  ```
  [question]

  <think>
  </think>

  Answer:
  ```
  This keeps the model in distribution while closing the thinking block before final answer generation.

- **For Qwen2.5-Math**: Uses standard answer-only prompts
  No empty-think tag needed since this model doesn't have <think> training.

### Validation Rules

- A generation is marked `no_cot_valid=true` only if:
  - No generated <think> tags with content
  - No visible reasoning keywords (step, then, therefore, etc.)
  - Output is within token budget

### Pilot Dataset Scope

- Small enough for rapid iteration (~15 items)
- Structured to scale to 50-100 items per task family
- Covers three task families:
  - Arithmetic (1-3 ops)
  - Synthetic relations (1-3 hops, facts in prompt)
  - Factual/counterfactual (1-2 hops)

### Historical J-lens availability scaffold (superseded)

The original `experiments/phase0_5_jlens_spike.py` checked package/model
availability and did not perform fitting. The dedicated pinned runner
`scripts/phase05_jlens_feasibility.py` subsequently completed the bounded real
Jacobian run described in the authoritative 2026-07-18 section. The resulting
GREEN status is technical feasibility only, not Plan A scientific validation.

## What Remains

### Before Production Experiments

1. **Post-Phase-0.5 decision**
   - Phase 0.5A bounded technical feasibility is complete.
   - Any larger fit or scientific lens validation requires a new registered
     design and explicit authorization.
   - Actual 10-/25-prompt fitting was not performed.

2. **Phase 1.5: Layer Taxonomy**
   - Empirically identify sensory/workspace/motor layers
   - Prerequisite for Phase 2 J-lens readout

### For Full J-space Observation (Plan A)

3. **Phase 2: J-lens workspace readout**
   - Load fitted J-lens
   - Check intermediate concept readout in workspace layers
   - Sanity checks (not just output layer, not just prompt echo)

4. **Phase 3: Distill vs Base comparison**
   - Ability-matched task selection
   - Activation patching effect size
   - Cross-template probing

5. **Phase 4: Activation patching**
   - Layer × position heatmap
   - Control groups (random, wrong layer, etc.)
   - Alignment with J-lens readout peaks

6. **Phase 5: Ablation DoD**
   - Workspace region ablation
   - Damage on distill answer-only performance
   - Controls and headroom gates

### Fallback Path (Plan B)

If J-lens is infeasible:
- Use logit lens + target token probing
- Activation patching (lens-independent)
- Report only "hidden representation evidence" (weaker conclusion)

## Documentation

- **docs/experiment_plan.md**: Full project plan (Chinese, 548 lines)
- **docs/implementation_notes.md**: Implementation specifics (Chinese)
- **docs/decision_log.md**: Design decisions and status
- **docs/run_log.md**: Command history and Azure resources
- **reports/current_status.md**: This file
- **infra/azure/README.md**: Azure infrastructure guide

## File Structure

```
J-space-observation/
├── src/jspace_observation/
│   ├── __init__.py
│   ├── config.py
│   ├── model_loader.py
│   ├── no_cot.py
│   ├── prompt_sets.py
│   ├── eval_parsing.py
│   ├── stats.py
│   ├── run_logging.py
│   └── jlens_utils.py
├── experiments/
│   ├── phase0_5_jlens_spike.py
│   └── phase1_depth_gradient.py
├── tests/
│   ├── __init__.py
│   ├── test_no_cot.py
│   ├── test_eval_parsing.py
│   └── test_stats.py
├── infra/azure/
│   ├── README.md
│   ├── variables.example.env
│   └── scripts/
│       ├── 00_check_prereqs.sh
│       ├── 01_build_and_push_image.sh
│       ├── 02_run_phase0_5.sh
│       └── 03_run_phase1.sh
├── docs/
│   ├── experiment_plan.md
│   ├── implementation_notes.md
│   ├── decision_log.md
│   ├── run_log.md
│   └── ...
├── reports/
│   └── current_status.md (this file)
├── Makefile
├── requirements.txt
├── pyproject.toml
└── Dockerfile
```

## Next Immediate Actions

1. Treat the parser-v2 locked evaluation as finished. Do not re-score, re-read,
   or reuse the retired 120-case holdout under any circumstance.
2. If parser v2 is to be revised, first fix the span-recovery failures behind
   `wrong_span` and `boxed_final_miss` using only public development cases.
3. Construct and privately seal a new locked holdout before any further locked
   validation; a modified parser may not be validated on the retired set.
4. Keep higher-n and every new target-model behavioral run paused.
5. Treat any larger J-lens fit as a separate preregistered decision.

## Success Criteria

✓ **Implemented**: Executable scaffold for Phase 0.5 and Phase 1
✓ **Tests passing**: All unit tests pass without model downloads
✓ **Infrastructure**: ACR managed identity and private Blob persistence are operational
✓ **Pilot**: Small stop-controlled Phase 1 run persisted successfully
✓ **Reporting**: Raw strict, stopped intervention, and postprocessed utility are separate
✓ **Criteria**: Branch-specific thresholds preregistered before further runs
✓ **Path C Phase 1.2A**: 60/120 evaluator set validated and privately sealed
✓ **Isolation**: Locked inputs/labels remain outside Git; five post-sealing reviews passed
✓ **Parser v2**: Public-development-only prospective implementation frozen; locked labels not accessed before sealing
✓ **Locked evaluation**: One-shot evaluation executed once and closed; holdout retired
✗ **Parser v2 locked acceptance**: Formal outcome **FAIL** (32/34 mandatory gates; `boxed_final_miss` and `wrong_span` failed)
✓ **Phase 0.5A**: Real official J-lens bounded T4 technical feasibility GREEN
⏳ **Pending**: Scientific lens-quality validation; not implied by Phase 0.5A
⏳ **Pending**: A new locked holdout before any revised parser can be validated


## Phase 1.2D - parser-v3 locked evaluation (preregistered, not executed)

**Preregistration commit (source freeze):** `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea`, pushed to
`Alanjiao1988/J-space-observation`. Working tree clean, local `HEAD` equal to
`origin/main`.

**Holdout state:** `SEALED`. Unspent. Formal evaluation ordinal 0.

```text
holdout touched         no
predictions generated   no
locked labels accessed  no
formal result           none
```

### What is frozen

| Item | Identity |
| --- | --- |
| Candidate | parser v3, `jspace-parser-v3-reference-blind-extraction/v1` |
| Candidate version | `0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace` |
| Candidate source digest | `76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9` |
| Gating comparator | parser v2, `6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86` |
| Reporting comparator | legacy, `4b07b91859aca33b51af9c15b08f07026f11b0141f1300fd3f942138b731177e` |
| Gate contract | `docs/phase1_parser_v3_acceptance_gates.json`, `2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7` |
| Evaluation image | `j-space-observation-parser-v3-eval:e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea` (not yet built) |

The gate contract was derived from the frozen parser-v2 contract with 0 numeric
threshold changes, 0 metric semantic changes and 0 population changes. The
candidate worker was derived from the parser-v2 worker with 6 counted
substitutions and 0 unexpected diffs. Both derivations are machine-checked and
idempotent.

### Verification at the freeze

```text
full test suite     1320 passed (the one permitted full run)
targeted suites       240 passed
parser-v3 tests        78
```

The 78 parser-v3 tests include all 14 mandatory regressions: Stage E rejects a
`eval_parsing_v3.py` file, a `eval_parsing_v3.pyc` file, a code object named
`parse_v3`, and a dynamic-import string for the candidate module; the candidate
identity cannot be changed by argument or by environment after import; parser
v2's default profile stays byte-identical; the candidate never writes into a
parser-v2 member path; the three streams must share identical, identically
ordered case membership; swapped streams are rejected; the finalizer cannot
import the candidate indirectly; and all three frozen parser sources remain
byte-identical.

### Safety defect disclosed

Stage E's parser-import prohibition initially omitted parser v3 from several
exact-match deny lists and probes. Two independent read-only preflight reviews
(`claude-opus-5`, `reasoning=max`) found four further CRITICAL defects in the
three-stream wiring, two of which would have surfaced only after prediction
generation or after the first label read. All were fixed **before**
preregistration, prediction generation, holdout access and label access, so the
impact on the formal evaluation is **none**. Recorded in full in
`docs/run_log.md` and as limitation `L-24`.

### Why it is not executed

The preregistered build and run launchers are hardened POSIX shell scripts that
re-exec under `env -i` with `PATH=/usr/local/bin:/usr/bin:/bin` and resolve
`/usr/bin/python3`. The development machine is Windows with only MSYS/MINGW64
bash, no `/usr/bin/python3`, no container runtime, and WSL with no distribution
installed. Earlier Azure phases in this project were driven by Python and were
unaffected, so this path had never been exercised here.

A POSIX host with Python 3.11 and the Azure CLI is required to build the image
and run Stage P and Stage E. Nothing needs re-deriving; execution resumes from
`e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea` exactly as frozen.

### Next gate

Build the immutable image once, validate its digest and provenance, run Stage P,
seal the three prediction streams, run Stage E, and record one formal `PASS` or
`FAIL` with the holdout retired.

## Phase 1.2D parser-v3 locked evaluation (2026-07-25) — HALTED, NOT RUN

```
Outcome:                          HALTED before preregistration
Formal PASS/FAIL:                 none produced
Preregistration commit:           none created this round
Holdout state:                    SEALED, unspent
sealed_object_count:              12
total_case_count:                 120
residual_semantic_case_count:     15
Locked labels read:               0
Predictions generated:            0
Authorization lock:               not created
State chain:                      not bootstrapped
ACA job:                          not created
Formal evaluation ordinal:        0
```

The round was stopped in preflight. The sealed parser-v3 validation set, the
frozen scoring instrument and the parser-v3 acceptance gates are three
artifacts that do not describe the same thing. Nine findings (`H1`-`H9`) are
recorded in `docs/phase1_parser_v3_locked_evaluation_protocol.md` §15.

The decisive one is `H9` and it involves no instrument. The gate contract
`docs/phase1_parser_v3_acceptance_gates.json` admits three typed-decision
labels and declares `typed_decision_support = {ambiguous: 10, no_answer: 30,
present: 80}`. The sealed set contains a fourth class,
`present_unextractable` (4 cases), which `null_collapse_prohibited: true`
forbids collapsing, and its real support is `{present: 91, no_answer: 23,
ambiguous: 6}`. Strata are correct at 12 × 10 = 120. Because the `ambiguity`,
`no_answer`, `answer_presence_macro_f1` and `overall_exact_typed_decision`
gates are calibrated against the declared support, no instrument can score
this set against these gates.

Root cause: the v3 gate contract was derived from v2 by substitution rather
than re-derived from the v3 set — the `last_number_trap` blocks in the two
contracts are byte-identical, including an `error_definition` naming a
registered distractor span the v3 set does not contain. In parallel the set
was built to its own conventions. No artifact-level agreement test existed
between the two.

Two preflight instruments found all nine and are now standing requirements:
the **write-blocked dry run** (real bootstrap, real storage,
`upload_blob_once` replaced by a sentinel `BaseException`, zero side effects)
and the **projection probe** (project the set into the frozen schema and let
the *frozen* validator judge it).

Six normalisations (`N1`-`N6`, §15.4) were validated and are kept for reuse.
They lift the frozen-valid projection from 22 to 105 of 120 with all 105
typed decisions preserved, and they make the mandatory `last_number_trap`
gate non-vacuous on all 10 S06 cases — without them that gate would have
passed unconditionally while appearing to be enforced (`H3`). They cannot
reach the remaining 15 records, which differ semantically (`H8`).

Nothing irreplaceable was spent. Parser v3 is unchanged and frozen at source
SHA-256 `76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9`.
Because no preregistration commit was created, the parser, gate contract,
profile binding and membership rules remain editable — which the remediation
in §15.8 requires.

**Next gate:** re-derive the parser-v3 gate contract from the parser-v3 set,
resolve `present_unextractable` explicitly, reconcile the span convention
across the set and all three parsers, and add a mechanical preregistration
check that reproduces every declared support count, gate denominator and enum
vocabulary from sealed bytes before any image is built.

## Phase 1.2E parser-v3 evaluation ontology repair (tooling round) — BLOCKED

```
Terminal status:                  BLOCKED
Blocking item:                    acceptance thresholds REVIEW_REQUIRED
Sealed locked inputs read:        0
Sealed locked labels read:        0
Local private curator files read: 0
Predictions generated:            0
Parser invocations on locked data:0
Azure writes or resource changes: 0
Formal evaluation ordinal:        0
parser-v3-v1 state:               SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE
```

A public, tooling-only round. It built the machinery a future independently
curated `parser-v3-v2` set will need, and deliberately did not construct,
review, seal, preregister or evaluate anything.

**Old set disposition.** `parser-v3-v1` is recorded as `SEALED / UNSPENT /
UNSCORABLE / RETIRED_AS_INELIGIBLE`. `UNSPENT` records the absence of label
access; it is not a licence to reuse the set. Its bytes, provenance, and the
historical invalid gate contract are preserved unchanged, and the repair CLI
refuses to read or write anything in that namespace.

**Formal ontology.** Exactly three classes — `present:<canonical_value>`,
`ambiguous`, `no_answer` — with an explicit truth table over
`answer_presence`, `parse_valid`, `parse_ambiguous`, `parsed_answer`, candidate
cardinality, evidence-span requirements and `output_quality`.
`present_unextractable` is excluded from the formal set and may never be
collapsed into another class. Spans are literal-only everywhere. The full
specification is `docs/phase1_2e_parser_v3_ontology_repair_protocol.md`.

**`H8` is re-framed against the set's own public specification.** This is not a
new discovery — Phase 1.2D §15.3 and §15.7 already recorded the ontology and
support conflicts — but the framing changed, and the change matters. What was
recorded as "the parser-v3 gate contract was copied from parser-v2" is narrower
than what the tracked public evidence supports.
`evaluator_sets/parser_v3_v1/strata_definitions.md` is a tracked public file,
and the sealed set violates *its own public specification*, not merely the
v2-inherited contract: `S10` is publicly registered `no_answer` but its cases
are labelled `present`; the public quota table asserts 80/30/10; the public rule
that every `S11` case carries at least two distinct candidates is violated; and
the public statement that the set exercises no `empty` output is violated. The
root cause of `H9` is therefore broader than contract substitution — there was
no agreement test between the set, its own public specification, and its gate
contract. That missing test is what this round supplies. Everything above was
restated from tracked public files; no private data was opened.

**Count terminology corrected.** `sealed_object_count = 12`,
`total_case_count = 120`, `residual_semantic_case_count = 15`. The Phase 1.2D
report line `Holdout objects 15` conflated the first and third; it is corrected
by an erratum and guarded by a regression test.

**Delivered.** `parser_v3_repair_ontology.py` (truth table, fail-closed
validator bound to the frozen scoring instrument),
`parser_v3_repair_normalization.py` (`N1`-`N6` as pure, idempotent,
parser-free functions with a content-free receipt),
`parser_v3_repair_contract.py` (count kinds, set-facts builder with mandatory
re-derivation, agreement validator with `H1/H2/H3/H5/H8/H9` codes, contract
compiler), `scripts/parser_v3_repair_cli.py`, the prospective policy
`docs/phase1_parser_v3_v2_evaluation_policy.json`, and 122 synthetic tests.

**Independently audited, and it mattered.** A separate read-only reviewer
audited the finished implementation and found **ten defects: two critical, five
major, three minor**, all since fixed. The first critical: the `ambiguous`
truth-table row declared `parse_valid = false` where the frozen instrument
requires `true`, which would have made **every `S11` case in a sealed
`parser-v3-v2` unscorable by construction** — the exact condition that retired
`parser-v3-v1`. The second: the set-facts manifest was bound to no set, and a
hand-typed manifest describing a set that had never been built compiled cleanly
into a fully provenance-bearing contract. Both had one root cause — the tooling
*restated* the frozen instrument instead of *binding* to it, which is the same
defect as `H9` — and both are now fixed structurally, by
`_bind_to_scoring_instrument` and by mandatory re-derivation of every facts
manifest from the set it claims to describe. Full record:
`reports/phase1_2e_parser_v3_repair.md` §6. Recorded plainly because it is the
most useful result of the round: 93 self-authored tests passed against code
carrying a defect fatal to a tenth of the future set.

A second audit round over the remediation confirmed eight of the ten fixes as
structural — a 4 490-mutant differential sweep separated the ontology from the
frozen instrument zero times — and found five further defects, four introduced
by the remediation itself. All five are fixed. Two accepted observations became
limitation `L-32`: the sealed object count and member list are operator
assertions rather than derived facts, because no offline tool can list a blob.

**Why BLOCKED.** The numeric acceptance thresholds cannot be justified in this
round. Importing the
parser-v2 constants would carry over exactly the kind of unjustified number
this phase exists to eliminate, and deriving a threshold from a parser-v3
observation would select the threshold against the measurement it bounds. They
are marked `REVIEW_REQUIRED`, and the compiler refuses to emit a contract while
any of them is open. Everything else in the round is complete and green.

> **Erratum E-1.2F-01 (Phase 1.2F).** As originally written, this paragraph and
> the next gate below also cited the Phase 1.0C headroom calibration as an
> unrun blocking dependency. That was false when written: Phase 1.0C had already
> executed and finalized `INCONCLUSIVE` at `06eec993`. It was also a category
> error, because Phase 1.0C is target-model task/headroom screening and can
> never supply a parser acceptance threshold. The citation has been removed
> rather than updated. See `reports/phase1_2f_parser_acceptance_policy.md`.

**Not claimed.** Parser v3 is not validated, not shown non-regressive, not
shown improved, not accepted. The new tooling has synthetic-test evidence only
and has never been run against a real curated set. No J-space, hidden-reasoning,
internal-workspace or invisible-CoT conclusion follows from any of it.

**Next gate:** superseded by Phase 1.2F. See the Phase 1.2F section below.

---

## Phase 1.2F — Parser acceptance-policy correction and threshold preregistration

> **Superseded in part by Phase 1.2G.** This section is retained as the
> point-in-time record of what Phase 1.2F concluded and why. Phase 1.2G
> resolved the block by adopting strict finite-suite conformance, so this
> section's terminal status and its "next gate" no longer describe the current
> state. Its threshold analysis stands; its coverage figures were corrected in
> Phase 1.2G. Read the Phase 1.2G section for the current position.

**Status: `BLOCKED_ON_ACCEPTANCE_POLICY`** (point-in-time; resolved in Phase
1.2G).

Phase 1.2E blocked on a dependency that did not exist and could not have
existed. Phase 1.2F corrected that, then asked what the four proposed acceptance
thresholds actually constrain. The answer disqualified all four.

**The correction.** Phase 1.2E recorded its blocker as a statement that was
false when written:

> Phase 1.0C headroom calibration is NOT RUN

Phase 1.0C had already been preregistered
(`62e9b961`), unblocked (`5d18b708`), executed (`72c3d281`) and **finalized**
at `06eec993`, generating **300 / 300** target-model outputs and returning
**`INCONCLUSIVE`** with 44 unresolved semantic-equivalence rows. It was also a
category error: Phase 1.0C observes a
*target model's answer headroom*, holds no parser reference labels, and cannot
supply a parser acceptance threshold under any transformation. 45 statements
across 17 files were triaged; genuine point-in-time history was preserved
verbatim and every correction added as an erratum. Phase 1.2E's filing of this
defect under `H9` is withdrawn — `H9` is instrument-vocabulary disagreement;
this was policy provenance.

**The arithmetic that decided the round.** Mandatory gates already pin **80 of
120 cases** to exact typed-decision agreement (`S01 S02 S03 S12` via
`G_clean_strata_exact`; `S07 S08 S10 S11` via dedicated zero-error gates). Only
`S04`, `S05`, `S06`, `S09` — 40 cases — are free. Any criterion stated over 120
cases can therefore constrain only those 40, because anything else has already
failed a gate.

`S06` is free because the only *registered* definition of an `S06` error is the
narrow one in `docs/phase1_parser_v3_acceptance_gates.json`: selection of the
registered rightmost distractor span. A parser can satisfy that and still
return a wrong canonical value. An earlier 90/30 baseline in this round was
rejected by audit because it required reading one field three incompatible
ways. Every gate now declares `error_definition`, `error_scope` and
`pins_exact_typed_decision`, and coverage is derived from those declarations.

| Threshold | Disposition | Value | Independence |
| --- | --- | --- | --- |
| `overall_exact_typed_decision_minimum` | `REPLACE_HARD` | — | partially redundant |
| `critical_stratum_floor` | `MERGE_WITH_EXISTING_GATE` | — | partially redundant |
| `answer_presence_macro_f1_minimum` | `REPORT_ONLY` | — | fully redundant and masking |
| `non_regression_margin_vs_parser_v2` | `REPORT_ONLY` | — | not derivable prospectively |
| `residual_critical_exact_budget` *(new)* | `REVIEW_REQUIRED` | **`null`** | **independent** |

The overall minimum is vacuous at any value permitting ≥40 errors, and its
binding range is the free-population budget written over a denominator that
hides it. The critical floor is inert on four of its eight strata for every
possible value, leaving the same 40 cases — one constraint written twice.

**Macro F1 was the sharpest result.** Exhaustive enumeration of the **861**
feasible three-class confusion matrices at the registered supports (present 80,
no_answer 30, ambiguous 10) gives a range of **0.636895 – 1.0**, so any
threshold at or below the floor is vacuous; the metric is **non-monotone in
error count** (0.636895–0.755556 all at exactly 40 errors); and decisively, a
candidate returning **40 wrong canonical values** with perfect presence
classification scores **macro F1 = exactly 1.0000** while exact typed-decision
agreement is **80/120 = 66.7 %**. A gate that awards a perfect score to a
candidate that got a third of the canonical values wrong is not a safeguard.

**Non-regression is report-only** for one sufficient reason: no numeric margin
is choosable without observing a parser. Two further reasons offered earlier in
this round were **withdrawn as logically defective** — "parser v2 failed its own
evaluation" argues against a sufficiency standard rather than a non-regression
check, and "the comparator run does not exist" is what *prospective* means. A
margin-free per-case-dominance formulation was then considered on the merits
and rejected on substance: on a quota-constructed adversarial set the
incumbent's per-case correctness pattern is an artefact of its heuristics, and
binding to it could refuse a strictly better parser.

**Why still BLOCKED.** What survives is one genuinely independent criterion — an
exact-agreement error budget over the 40 free cases — whose *structure* is
derivable candidate-independently but whose *value* is not. The blocking
dependencies are **ordered**. Primary: `S04`, `S05`, `S06` and `S09` are
designed-failure strata, and the scientific decision of whether the instrument
must be exactly correct on them, or may be allowed a non-zero budget, has never
been taken; a `LOGICAL_INVARIANT` basis for `B = 0` is available in the
abstract, so what is missing is the decision, not the basis. Secondary, and
only if a non-zero tolerance is permitted: a repository-wide search found no
registered downstream parser-error budget to trace the number to. Any number
chosen today would be chosen by someone who already knows how parser v3 behaves
in development. It stays `null`, the policy stays `REVIEW_REQUIRED`, and the
compiler keeps refusing. No threshold was manufactured to obtain a green status.

**Also corrected.** The prospective policy no longer binds a future v2 set to
the retired `parser_v3_v1` namespace — a public, case-free, versioned v2 stratum
policy now carries an independent decision to retain the 12-stratum taxonomy.
The overbroad parser-isolation claim is withdrawn: `__init__.py` eagerly imports
the legacy parser, so package import is **not** parser-free. The supportable
claims — repair modules add no *new* parser dependency, reference no parser
symbol, and invoke no parser — are what is now stated and tested, and
`__init__.py` was deliberately **not** refactored to flatter the stronger
wording. `L-32` is preserved: a sealed member list and `sealed_object_count`
require an authenticated seal-time observation and are not derivable offline.

**Verification.** Focused Phase 1.2E + 1.2F suites **249 passed** (this figure
was recorded as "242 passed" when written; the round's own transcript shows
**249**, and the discrepancy is corrected here as Phase 1.2G erratum `G-08`);
full suite green; all protected digests unchanged; no existing test weakened,
removed or skipped. Two independent read-only audits raised **26 findings**, of
which two were blockers; all accepted findings were remediated and are recorded
in `reports/phase1_2f_audit_findings.md`. Self-authored tests are not described
as independent validation.

**Standing state.** Phase 1.0C was executed and finalized `INCONCLUSIVE`, and is
not parser calibration. No private holdout was accessed in Phase 1.2F. No
prediction was generated. No parser was run. No formal evaluation occurred.
Parser v3 remains **unvalidated**; formal evaluation ordinal remains **0**;
parser-v3 predictions against a locked set remain **0**; locked-label reads
remain **0**. `parser-v3-v1` remains **`SEALED / UNSPENT / UNSCORABLE /
RETIRED_AS_INELIGIBLE`** and byte-unchanged. **No J-space, hidden-reasoning,
invisible-CoT or internal-workspace conclusion follows.**

**Next gate (as written in Phase 1.2F; superseded).** Phase 1.2F recorded its
next gate as the instrument-strictness decision for the designed-failure strata
`S04`, `S05`, `S06`, `S09`, with a downstream parser-error budget and the
registered calibration protocol as the fallback if a non-zero tolerance were
permitted. Phase 1.2G took that decision — strict finite-suite conformance,
`B = 0` on a `LOGICAL_INVARIANT` basis — so the fallback never became live and
the calibration protocol is now `SUPERSEDED_UNEXECUTED`. The current next gate
is stated in the Phase 1.2G section. Full Phase 1.2F record:
`reports/phase1_2f_parser_acceptance_policy.md`.

---

## Phase 1.2G — Post-audit consistency remediation and conformance-policy finalization

**Status: `READY_FOR_INDEPENDENT_SET_REPAIR`.**

Phase 1.2F left one question open and ten defects behind it. Phase 1.2G closed
both.

**The decision.** The open question was whether the four designed-failure strata
`S04`, `S05`, `S06`, `S09` — the 40 cases that the mandatory gates do *not* pin
to exact typed-decision agreement — admit any error tolerance. Phase 1.2G
answers by fixing the premise that had been left implicit: the future
`parser-v3-v2` set is a **finite conformance suite**, not a sample. Every case
admitted to it is admitted precisely because a correct instrument must handle
it, so each case is a mandatory conformance example and an exact typed-decision
mismatch on any one of them is unacceptable instrument behaviour. Zero tolerance
is then a `LOGICAL_INVARIANT` — it follows from what the set *is*, not from a
judgement that errors are severe, that the parser is deterministic, that the set
is not IID, that calibration is unavailable, or that zero is tidy. The
derivation is scanned by test to make sure it never appeals to any of those.
`residual_critical_exact_budget` is therefore `KEEP_HARD`, binding, with a
pooled limit of **0** *and* per-stratum limits of **0** for each of `S04`,
`S05`, `S06`, `S09`. The pooled limit alone would have been satisfiable by a
policy that later raised one stratum's cap; both are stated so neither can drift.

**What this does not mean.** A `FINAL` policy is a settled rule for judging a
future evaluation. It is not a result, not a prediction about parser v3, and not
a claim that any parser can meet it. The policy is deliberately harder to pass
than the one it replaces, and it was written knowing that.

**The falsifier.** The conformance premise is recorded with the observation that
would refute it: if a case is ever admitted to the set that a correct instrument
is *not* required to handle, the premise fails and the invariant loses its
basis. That is a set-construction constraint the later set-repair round inherits.

**The other four metrics.** `overall_exact_typed_decision_minimum` is
`REPLACE_HARD` and `critical_stratum_floor` is `MERGE_WITH_EXISTING_GATE`: with
80 of 120 cases pinned by mandatory gates and the residual 40 at zero, both are
implied and neither can bind, but neither is deleted — the protection each aimed
at survives inside `residual_critical_exact_budget` and inside the mandatory
gates respectively, which is what those two labels record. The canonical labels
are the ones in `docs/phase1_parser_v3_v2_evaluation_policy.json`; this summary
restates them and does not define them. `answer_presence_macro_f1_minimum` is
`REPORT_ONLY`: an exhaustive enumeration of the 861 feasible three-class
confusion matrices at the registered supports (present 80, no_answer 30,
ambiguous 10) shows it cannot see a wrong canonical value that preserves the
presence class, so it cannot serve as a safeguard.
`non_regression_margin_vs_parser_v2` stays `REPORT_ONLY` and non-binding; the
one substantive argument for binding it was withdrawn in Phase 1.2F as unsound
and is no longer asserted anywhere live. A test proves that no replaced, merged
or report-only metric can re-enter `PASS`/`FAIL` logic.

**The ten defects.** Phase 1.2G opened with ten seed defects, `G-01` … `G-10`,
all of them consistency failures between artifacts rather than new scientific
findings — they are deliberately *not* numbered into the historical `H1`–`H9`
series. They ranged from stale coverage figures in the stratum policy and the
calibration protocol, through a next-gate ordering inversion and a withdrawn
argument still asserted live, to a protected-digest count of 11 where the
registry holds **12**. All ten are remediated, and each is now covered by a
regression that fails if it returns.

**Why this will not recur the same way.** Phase 1.2F relied on a prose scanner
to keep the current-state documents honest, and six of the ten seed defects were
figures no pattern covered. Phase 1.2G adds
`scripts/generate_current_state.py`, which *renders* the current-state block
from the canonical policy and the single production coverage derivation and
compares bytes under `--check`. A figure that cannot be typed by hand cannot go
stale. The policy JSON is now declared the canonical machine-readable source of
truth, and the coverage derivation
`parser_v3_repair_contract.derive_gate_coverage` is the one production
implementation that both validation and compilation consume — the policy's own
coverage block is a restatement the validator requires to agree with it.

**Verification.** See the Phase 1.2G report for the full figures, the
independent-audit findings, the protected-digest before/after table and the
private-access ledger. Full record:
`reports/phase1_2g_conformance_policy.md`; protocol:
`docs/phase1_2g_conformance_policy_protocol.md`; audits:
`reports/phase1_2g_audit_findings.md`.

**Standing state.** Phase 1.0C was executed and finalized `INCONCLUSIVE`, and is
not parser calibration. No private holdout was accessed in Phase 1.2G. No
prediction was generated. No parser was run. No formal evaluation occurred.
Parser v3 remains **unvalidated**; formal evaluation ordinal remains **0**;
parser-v3 predictions against a locked set remain **0**; locked-label reads
remain **0**. `parser-v3-v1` remains **`SEALED / UNSPENT / UNSCORABLE /
RETIRED_AS_INELIGIBLE`** and byte-unchanged. **No J-space, hidden-reasoning,
invisible-CoT or internal-workspace conclusion follows.**

**Next gate:** a **separately authorized independent set-repair round** for
`parser-v3-v2`. `READY_FOR_INDEPENDENT_SET_REPAIR` means the acceptance rule is
settled well enough for that round to begin; it authorizes nothing else. Set
construction, migration of the 105 cases, review of the 15 quarantined cases,
manifest generation, sealing, authorization locks, image construction,
preregistration, Stage P and Stage E all remain unauthorized.
