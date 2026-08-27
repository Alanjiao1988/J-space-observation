# Study 5-EQ1 — J-space × distillation-delta engineering qualification authority

This authority is published alone, as the sole path in its commit, before any
Mooncake write and before any model call. It governs one invocation only.

It authorizes **engineering qualification**. It does not authorize confirmation,
and no state it can reach is a scientific result.

---

# 0. Provenance of this authority

| Field | Value |
| --- | --- |
| Approved by | operator, in session, 2026-08-27 |
| Basis | Study 5 methods decision memo, 2026-08-27 |
| Predecessor branch | `origin/alanjiao1988-azure-mooncake-a100-vm` |
| Predecessor commit | `dac07a695e9cf820fcf3546ccff24826d3e47a30` |
| Predecessor study terminal state | `STUDY4F_M1_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER` |
| Evidence ledger at start | `EV-0016` |

Study 5 branches from the Mooncake branch, not from `main`, because the model
blob index, storage transport record and acquisition manifest that Study 5
depends on exist only on that branch. This authority does not merge, rebase or
advance `main`.

---

# 1. What this authority is, and what it is not

**It is** the qualification stage for a new study: acquire the missing bytes,
build the missing instrument, and test — against pre-registered gates — whether
the intended causal design is measurable at all on this model pair.

**It is not:**

* a reopening, reinterpretation or amendment of Study 4F, Study 4F-M1, Study 3R,
  Study 3 or Phase 1.0D. Every one of those keeps its registered state and its
  bytes;
* a confirmatory study. No confirmation bank is realized, no confirmation item is
  ever passed to a model, and no primary hypothesis is tested;
* a licence to describe any result as evidence about J-space, about distillation,
  or about reasoning.

Study 4F-M1's E0 outcome is registered as an **interface/parser finding**. This
authority does not re-derive it, does not extend it, and does not inherit its
gate. The retired gate is named here so it cannot return by default:

> **RETIRED:** `zero-generated-reasoning-token expressed competence` is not a
> gate in Study 5, at any stage, for any purpose. No answer surface narrower
> than the model's own chat template plus a full chain of thought may decide
> whether internal mechanism is measurable.

---

# 2. Operator resource decisions (VM configuration freeze)

These are operator decisions recorded so that they can be mechanically tested.
They are **stricter** than the Study 4F-M1 decisions and supersede them for this
invocation.

1. **Do not change the configuration of any existing VM.** No resize, no SKU
   change, no redeploy, replace, clone or migrate.
2. **Do not start, stop, deallocate, restart or reboot any VM.** Both VMs are
   already running and must stay running. A step that would require a reboot,
   a driver change or a host-level package that forces a restart is a hard
   blocker, not a fix.
3. Do not modify any OS disk, data disk, NIC, public IP, VM extension, managed
   identity, RBAC assignment, VNet, subnet or NSG.
4. Do not format, repartition, remount or reformat any disk. `/scratch`
   (RAID0 XFS over the four ephemeral NVMe devices) is already mounted and is
   used as-is.
5. **Do not create or delete any Azure resource.** No new Storage Account, no
   ACR, no Key Vault, no Log Analytics workspace, no Bastion, no gateway, no
   AML workspace, no anything.
6. **Do not create or delete a blob container.** The existing account
   `s4fm11ca457e105b29b7` already has `models`, `oci`, `runs`, `logs`, `seals`
   and `handoff`. New bytes go into new **paths** inside those containers.
7. **Every existing blob is immutable.** No existing blob may be overwritten,
   renamed, tiered, lifecycle-expired or deleted. Every upload is create-only
   and must be issued with an `If-None-Match: *` precondition; a precondition
   failure is a stop, never a retry with overwrite.
8. Do not issue a SAS token, do not read or commit a storage key, do not commit
   a subscription id, tenant id, full resource id or credential. Only salted
   identity hashes and the already-published safe names.
9. Data-plane access is via the existing system-assigned managed identities.
   **Do not add, remove or modify any role assignment**, including to make
   verification easier. If a read cannot be performed under the existing
   identity, that is recorded as a limitation, not repaired.
10. At the end of the invocation, both VMs remain running and every Azure
    resource remains exactly as it was found. Cost accrual is expected and
    intended; the invocation must not propose, imply or perform any
    cost-reduction action.

**Verification requirement.** Before the first write and again at the end, the
invocation records a read-only inventory — VM names, sizes, locations, power
states, storage account name, container list — and commits both snapshots. Any
difference between them, other than blob count and byte totals, is a hard
blocker and must be reported, not corrected.

---

# 3. Registered scientific decisions (approved; normative for Study 5)

These were approved by the operator on 2026-08-27 and may not be changed by this
invocation or by any artifact it produces.

### 3.1 J-alignment is geometric, not a moment statistic

`lens-kurtosis` is **not** a J-signal and may not be used to select features.
Its two registered roles are:

* **layer-band identification** — excess kurtosis of the readout logit
  distribution for a single `(position, layer)` across a large activation set,
  plotted against depth, used to locate the workspace band;
* **motor-risk flagging** — a per-feature high kurtosis value flags a feature
  for motor review, because a feature that constantly promotes one fixed token
  is maximally kurtotic and is exactly what must be excluded.

The registered per-feature J-alignment statistic is the **J-space explained
variance ratio**

```
JA(f) = ||P_J(Δ_f)||² / ||Δ_f||²
```

where `P_J` is the nearest point in J-space obtained by **k-sparse nonnegative
gradient pursuit** over the layer-`ℓ` J-lens frame with `k ≤ 25`, and `Δ_f` is
the vector the feature writes into the residual stream. Pursuit is nonnegative,
so sign is meaningful; because the adapter encoder is ReLU-gated, `a ≥ 0` and
the `+d` orientation is used.

### 3.2 Thresholds are externally calibrated, not chosen

The published workspace paper supplies the calibration:

| Anchor | Published value | Registered use |
| --- | --- | --- |
| Generic concept vector, J-space variance share | median **6–7%** | null band; matched low-J controls must sit here |
| Intermediate-concept probe, J-space variance share | **10–15%** | signal band |
| Probe swap, J-space component flips answer | **61%** | pursuit acceptance |
| Probe swap, non-J component flips answer | **28%** | pursuit acceptance |
| Non-J effect after J coordinates clamped | **6%** | pursuit acceptance |
| Workspace band, depth-reindexed to [0,100] | ≈ **38 → 92** | prior only; band is re-derived empirically |

No global Frobenius threshold is registered and none may be introduced.

### 3.3 Reference frame

The registered J-lens reference frame is the **target** `T`. `J_ℓ(F)` and
`J_ℓ(H)` are measured and reported as a sensitivity analysis. If `J_ℓ(H)`
departs materially from `J_ℓ(T)`, the sufficiency arm's interpretation narrows
accordingly, and that departure is itself reported.

### 3.4 Scope removed from Study 5

`DeepSeek-R1-Distill-Qwen-1.5B` scaling replication is **removed** from Study 5.
No adapter has been released for any pair other than the 7B pair; a second scale
point would require training a new adapter and is a separate project. This
authority does not promise it, does not pre-register it and does not budget it.

### 3.5 Sample size is derived, not pre-fixed

Confirmation `n` is **not** fixed in advance. This invocation measures the
paired discordance rate on development items and solves for `n` using a rule
that is registered **here, before any measurement**:

```
n_required = ceil( ( z_{1-α/2} + z_{power} )² · p_disc / δ_target² )
```

with `α = 0.025` (two primary contrasts, gatekept), `power = 0.80`,
`δ_target` = the smaller of (0.5 × observed `F−H` accuracy gap) and 0.05,
`p_disc` = observed discordance rate on development items. The rule is frozen;
only its inputs come from data. If `n_required` exceeds the available
confirmation pool, the registered outcome is a declared power limitation, never
a relaxed `δ_target`.

### 3.6 Answer scoring

Native chat template, full chain of thought, `max_new_tokens = 4096`. The
answer is the **last** `\boxed{...}` occurrence; equivalence is decided by a
frozen symbolic checker whose version is pinned in the container. The parser's
own false-negative rate is measured on development items with known answers and
reported. The Study 4F `parse_e0` contract is not used, not imported and not
referenced.

### 3.7 Third-party licence position

`nathanhu0/transcoder-adapters` and all five HuggingFace adapter checkpoints
carry **no licence**. The registered position for this invocation is:

* the adapters and their code are used for research;
* **no adapter weight byte and no repository source file is redistributed** —
  not into Git, not into any public location, not into the `handoff` container;
* the missing licence is recorded verbatim in the disclosure as an open legal
  question;
* whether to seek an explicit grant from the authors is an operator decision and
  is **not** an action this invocation takes.

`Qwen2.5-Math-7B` is apache-2.0, `DeepSeek-R1-Distill-Qwen-7B` is MIT,
`anthropics/jacobian-lens` is apache-2.0. Those three are unencumbered.

---

# 4. Registered identities (immutable; no substitution)

### 4.1 Models

| Role | Repository | Immutable revision | Status |
| --- | --- | --- | --- |
| `T` target | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | `916b56a44061fd5cd7d6a8fb632557ed4f724f60` | already byte-verified in `models` container (Study 4F-M1) |
| base / MLP donor | `Qwen/Qwen2.5-Math-7B` | `b101308fe89651ea5ce025f25317fea6fc07e96e` | to acquire |
| adapter, primary | `nathu0/transcoder-adapters-R1-Distill-Qwen-7B-l1w0.001-l0-1.4` | `9033fcd16d2fcb8fbe18efa2e6ed6503b0a784dc` | to acquire (includes `classifications/`) |
| adapter, sparsity sensitivity | `nathu0/transcoder-adapters-R1-Distill-Qwen-7B-l1w0.003-l0-4.3` | `89ead0db81b65fa1ed6d433324d100c74bf77edd` | to acquire |

Recorded but **not** acquired by this invocation:
`l1w0.01-l0-10.3` `0f628036f9522bc8687c7fd09fc5af2cf6c51336`,
`l1w0.0003-l0-0.4` `893466285964c27b7b9ecb42d8036fd67686afaa`,
`l1w0.0001-l0-0.1` `5846092d62317129ec24af0c5b276c2e5f7dbf0e`.

Model geometry, from the adapter config: 28 layers, `hidden_size` 3584,
`intermediate_size` 18944, `vocab_size` 152064, `transcoder_n_features` 8192.
Total adapter feature count: **28 × 8192 = 229,376**.

### 4.2 Code

| Artifact | Commit | Licence |
| --- | --- | --- |
| `anthropics/jacobian-lens` | `581d398613e5602a5af361e1c34d3a92ea82ba8e` | Apache-2.0 |
| `nathanhu0/transcoder-adapters` | `a944cd1dccd8c5a1d26deac841a85819b589015f` | none — see §3.7 |

`anthropics/jacobian-lens` provides `fit()`, `apply()` and `merge()` only. It
does **not** provide gradient pursuit or J-space decomposition; that must be
implemented in this repository and validated against §3.2.

### 4.3 Data

| Purpose | Source | Revision |
| --- | --- | --- |
| J-lens fitting corpus | `data/jlens_s2_wikitext/corpus_rows.jsonl`, already committed | rows sha256 `63ed70ef0a7457f47a77a0d96855a2aeb605026c99a6708b6cf8d2f630b1445d` |
| Primary benchmark | `HuggingFaceH4/MATH-500` | `6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be` |
| Secondary benchmark | `Idavidrein/gpqa`, diamond split | `633f5ee89ab8ad4522a9f850766b73f62147ffdd` — **gated: auto** |
| Registered secondary fallback | `TIGER-Lab/MMLU-Pro`, STEM slice | `b189ec765aa7ed75c8acfea42df31fdae71f97be` |
| Contamination reference | `nathu0/transcoder-adapters-openthoughts3-stratified-55k` | `b6d6ca48ac7e12517bd16411687a28e404cc2692` |

The WikiText corpus is reused for its **raw text rows and its frozen
A=600 / B=600 / heldout=200 / smoke=2 role assignment**. It was tokenized for
the 1.5B tokenizer; it is re-tokenized with the 7B target tokenizer and both
token-id hashes are recorded. The corpus is a public Wikipedia-derived proxy,
not the target's training distribution; that limitation is carried forward
verbatim.

The GPQA gate is resolved at **P-0, before any model call**. If access is not
obtained at P-0, the registered fallback secondary is MMLU-Pro STEM. This choice
is made before any outcome is observed and may not be revisited afterwards.

---

# 5. Registered conditions, contrasts and estimands

Registered here so that they are frozen; **only the anchors and the development
arms are executed by this invocation.**

| Condition | Construction |
| --- | --- |
| `T` | published distilled target |
| `H` | target attention/embed/norm + base MLP, adapter off (`misc_scripts/make_hybrid_model.py`) |
| `F` | `H` + all transcoder features |
| `F−J` | `F` minus J-aligned, non-motor features |
| `F−N` | `F` minus matched low-J control features |
| `H+J` | `H` plus the same J set |
| `H+N` | `H` plus the matched control set |
| `H+J*` | `H` plus the same J directions with per-position activations shuffled across items — equal energy, scrambled content |

Estimands, both item-paired:

```
Δ_necessity   = E_i[ Y_i(F−N) ] − E_i[ Y_i(F−J) ]
Δ_sufficiency = E_i[ Y_i(H+J) ] − E_i[ Y_i(H+N) ]
```

`Y_i` is per-item accuracy on the registered benchmark under the registered
decoding law. **The statistical unit is the item.** Features, tokens, layers,
GPU workers and repeated responses are never independent samples. Where multiple
responses per item are drawn, they are aggregated to a per-item score before any
analysis.

`F` and `H` are anchors for fidelity and qualification. They are not the
estimand and are not tested.

Dose-response: `α ∈ {0.5, 1, 2}`. Monotonicity is pre-registered as secondary
evidence.

---

# 6. J-alignment construction and controls

### 6.1 Construction order (must run in this order)

1. Fit the J-lens on `T` with `jlens.fit()` at `581d398`, independently on
   corpus half `A` and half `B`, merging disjoint slices with `merge()`.
2. Compute excess kurtosis of the readout logit distribution per
   `(position, layer)` across the held-out corpus rows; plot against depth;
   derive the workspace band empirically. The `[38, 92]` depth-reindexed prior
   corresponds to roughly layers 11–26 of 28 and is a prior only.
3. Implement k-sparse nonnegative gradient pursuit, `k ≤ 25`, over the layer-`ℓ`
   J-lens frame. Where a restricted atom set is used for tractability, the
   restriction rule is registered and an exact-vs-restricted equivalence check
   is run on a random subsample and reported.
4. Screen every candidate feature by `JA(d_f)` on the decoder direction.
5. Compute the registered statistic `JA(Δ_f)` on the **actual in-context write
   delta** at positions where the feature fires.
6. Keep only features that clear the band under **both** the `A` and the `B`
   lens, and whose `JA` rank correlation across the two lenses meets the
   pre-registered floor.
7. Apply motor exclusion (§6.2).
8. Build matched controls (§6.3).
9. Freeze both sets by SHA-256. **After the freeze they cannot change.**

### 6.2 Motor / output-format exclusion — three layers, all required

1. **Published labels.** Exclude `mechanism == "output"` from
   `classifications/feature_classifications_all_layer*.json` in the primary
   adapter repository. Coverage is essentially complete (layer 0: 8190 of 8192
   classified, judge `gpt-5-mini`, seed 42). These are single-pass LLM-judge
   labels and are never the sole criterion.
2. **Functional motor test.** Register a token set — format control
   (`<think>`, `</think>`, EOS, `\n\n`, `Answer`, `boxed`) and hesitation
   markers (`wait`, `Wait`, `Hmm`, `Alternatively`, `But`). A feature whose
   intervention places more than the pre-registered share of its total logit
   displacement mass on that set is motor, and is excluded.
3. **Kurtosis motor-risk flag.** High per-feature readout kurtosis triggers
   manual review. It never causes inclusion.

### 6.3 Matched low-J controls

Matched on: **layer**, **activation frequency** (log-binned), **decoder norm**,
**realized activation magnitude distribution**, **actual intervention energy**
`Σ a·||d||`, **set size**, and **reconstruction damage** (NMSE and `KL(·‖T)`).

Matching is a one-to-one optimal assignment on standardized covariates, not
marginal matching. Standardized mean differences are reported for every
covariate. **If any SMD exceeds the pre-registered bound, the contrast is
invalid: rematch, do not report.**

Reconstruction damage is a matching variable, not a diagnostic. If `F−J` and
`F−N` are not matched on it, the accuracy difference between them is
uninterpretable and must not be reported.

---

# 7. Qualification gates

Each gate is pass/fail against a criterion written **before** the measurement.
A failure stops the invocation at an engineering or construct blocker. **No gate
failure may be registered as a scientific finding, and in particular none may be
written as a "no natural positive reference" style terminal state.**

| Gate | Criterion |
| --- | --- |
| **Q-1** Availability and legality | all §4 bytes obtainable; §3.7 licence position recorded |
| **Q-2** Immutable hashes | every acquired file hashed on the execution host and matching its authoritative value before use; content-addressed into `models/sha256/<aa>/<full>`; round-trip re-hash after upload |
| **Q-3** Adapter fidelity | `F` recovers **≥ 50%** of the `H → T` accuracy gap on the development slice, and does not shorten responses relative to `T` beyond the pre-registered tolerance; **and** the true `L0` of each acquired checkpoint is measured empirically (the published README's table and prose disagree on the direction of `l1_weight → sparsity`; neither is trusted) |
| **Q-4a** Workspace band | a discernible mid-depth kurtosis band exists on the 7B target |
| **Q-4b** Pursuit validity | the implementation reproduces the §3.2 published anchors within pre-registered tolerance |
| **Q-5** Numerical stability | no NaN/inf in bf16; per-item reproducibility under fixed seed; `α` sweep monotone and jump-free |
| **Q-6** Scoring independence | scoring runs without any Study 4F E0 artifact; parser false-negative rate measured and reported |
| **Q-7** Logging and isolation | create-only journaling demonstrated; confirmation split frozen and provably untouched; the full run record is committed to GitHub |

---

# 8. Phase plan

Phases run in order. Each ends with a commit. A phase may not start until the
previous phase's gate has passed and been committed.

| Phase | Work | Gate | Accelerator budget |
| --- | --- | --- | --- |
| **P-0** | Read-only Azure inventory snapshot. Resolve GPQA access. Acquire and byte-verify `Qwen2.5-Math-7B` and both adapters into content-addressed paths. Build the new container image and freeze its digest. Freeze the benchmark development/confirmation split. Contamination check against OpenThoughts3-55k. | Q-1, Q-2 | 0 h |
| **P-1** | Build `H`. Measure `T` / `H` / `F` on the development slice (n = 200, k = 1). Measure true `L0`. | Q-3 | ≤ 24 h |
| **P-2** | Fit the J-lens on halves `A` and `B`. Kurtosis-vs-depth. Derive the band. | Q-4a | ≤ 48 h |
| **P-3** | Implement and validate gradient pursuit against the published anchors. | Q-4b | ≤ 24 h |
| **P-4** | `JA` for every candidate feature in the band. Three-layer motor exclusion. Build matched `N` and the `J*` arm. Balance and reconstruction-damage tables. Freeze both sets by hash. | — | ≤ 72 h |
| **P-5** | Development-only intervention pilot: `F−J`, `F−N`, `H+J`, `H+N`, `H+J*` at `α ∈ {1, 2}` plus the three anchors, n = 200, k = 1. Stability checks. **Measure discordance and solve §3.5 for `n_required`.** | Q-5, Q-6 | ≤ 60 h |
| **P-6** | Assemble the qualification dossier: frozen feature sets, derived `n_required`, band, all gate outcomes, complete run record, disclosure. | Q-7 | 0 h |

Total registered accelerator ceiling: **240 accelerator-hours**. Exceeding it is
a fail-closed stop with everything committed. The ceiling bounds this
invocation; it does not bound, and must not be used to argue about, the running
cost of the VMs.

`batch_size = 1` for every measurement that feeds a registered statistic.
One isolated worker per visible GPU, `CUDA_DEVICE_ORDER=PCI_BUS_ID`, a
single-device `CUDA_VISIBLE_DEVICES` per worker, `trust_remote_code = false`
for `T` and the base model, bf16, unquantized, no tensor or pipeline
parallelism, no MIG, no device_map auto, no offload. Four GPUs may reduce wall
time; they may not change items, responses, conditions, retries or statistical
units.

---

# 9. Run record — the paper-traceability requirement

The operator's requirement is explicit: **the process and its timing must be
recorded in the GitHub repository so that a paper can be written from it later.**
This is a first-class deliverable of this invocation, not an accessory.

### 9.1 Journal

`studies/study5/qualification-eq1/journal/<phase>.jsonl`, append-only, one
record per step, never rewritten:

```
ts_start_utc, ts_end_utc, duration_s, phase, step_id, host, gpu_index,
gpu_seconds, command_sha256, inputs_sha256[], outputs_sha256[],
exit_status, blocker_id|null, note
```

Journal keys are unique. Duplicate keys are a hard blocker. Records are written
before the next step begins, so an interrupted run still leaves a complete
prefix.

### 9.2 Timeline

`studies/study5/qualification-eq1/TIMELINE.md` — a human-readable chronology in
UTC: what ran, when, for how long, on which host, what it produced, what failed
and why. Every failure, retry, degraded condition and skipped step appears here.
Suppressing a failure is a governance violation.

### 9.3 Resource accounting

`studies/study5/qualification-eq1/resource_accounting.json` reports three
quantities separately and never substitutes one for another:
**VM wall-clock hours**, **allocated GPU-hours**, **actively used GPU-hours**;
plus per-phase breakdown, blob bytes written, and the unit price and continuing
cost rate of every paid resource.

### 9.4 Traceability

Every number, table and figure that could appear in a paper must resolve to:
a committed artifact, the script that produced it, and the SHA-256 of every
input. A number with no committed provenance may not be reported.

### 9.5 Commit cadence

Commit at the end of every phase, and additionally whenever a gate is decided or
a blocker is hit. Never batch the run record to the end. Model weights, adapter
weights and container archives are never committed to Git; their hashes and blob
paths are.

---

# 10. Development / confirmation isolation

1. The benchmark development/confirmation split is a deterministic hash split,
   frozen and committed at **P-0**, before any model call.
2. This invocation touches **development items only**. No confirmation item is
   tokenized, prefilled, generated from, scored or inspected.
3. No confirmation bank is realized. No confirmation protocol is sealed. Those
   belong to the successor authority.
4. Feature-set selection uses development data only. The selected sets are
   frozen by hash at the end of P-4 and are inputs to the successor authority,
   not free parameters within it.
5. Isolation is asserted by a committed check that recomputes the split and
   proves no confirmation item id appears in any journal record.

---

# 11. Prohibited operations

* Any Azure control-plane write, and every action listed in §2.
* Confirmation of any kind; realizing or reading a confirmation bank.
* Writing a row to `paper/evidence_ledger.csv`. It stays at `EV-0016`.
* Modifying any Study 3, Study 3R, Study 4F, Study 4F-M1 or Phase 1.0D byte.
* Merging into `main`; rebase, force-push or any history rewrite.
* Triggering a GitHub Actions run.
* Repeating a step because its result is unfavorable.
* Changing, after any measurement is seen: the benchmark, the split, a
  threshold, the band, a feature set, `α`, the decoding law, the scoring rule or
  the `n_required` formula.
* Introducing a zero-CoT, raw-bytes or narrow-answer-surface gate.
* Redistributing adapter weights or unlicensed source (§3.7).
* Claiming, implying or hinting at: J-space existence or non-existence, an
  internal causal reasoning mechanism, a training-causal effect of distillation,
  an explanation of attention/embedding/normalization, or anything about
  consciousness.

---

# 12. Hard blockers

Stop fail-closed, commit everything, and report — do not repair — on:

1. the target is not AzureChinaCloud/Mooncake, or the resource group and VM
   roles cannot be uniquely resolved;
2. any VM configuration difference between the opening and closing inventory
   snapshots;
3. a required step would need a reboot, a driver change, a resize or any §2
   prohibited action;
4. free GPU memory below the registered floor `69,502,926,848` bytes on a device
   without killing an unowned process;
5. a registered byte source cannot be acquired byte-exactly, or a mirror cannot
   reproduce its authoritative SHA-256;
6. a create-only upload hits an `If-None-Match` precondition failure — i.e. the
   path already exists;
7. the container image cannot be built with a frozen digest and no byte-equal
   source exists;
8. Q-3, Q-4a or Q-4b fails against its pre-registered criterion;
9. proceeding would require changing an estimand, threshold, split, feature set,
   decoding contract or interpretation;
10. a protected historical artifact would have to be edited, or safe publication
    would require rewriting published Git history;
11. `origin/main` or the predecessor branch advanced unexpectedly.

Everything else is an engineering warning or a disclosed degraded condition, and
is worked around and recorded rather than escalated.

---

# 13. Publication discipline

* This authority is committed **alone, as the sole path in its commit**, on a
  new branch off `dac07a695e9cf820fcf3546ccff24826d3e47a30`, before any other
  Study 5 write. Its SHA-256 and commit hash are recorded in `STATUS.json`.
* Fast-forward only. No merge, no rebase, no force-push, no history rewrite.
* Every Study 3R, Study 4F, Study 4F-M1, E1, Q1 and Q1R artifact stays
  byte-identical.
* The predecessor branch and `origin/main` are refetched immediately before every
  publication; unexpected advancement stops the invocation.
* No credential, key, SAS token, subscription id, tenant id or full resource id
  is ever printed into a committed artifact.
* Historical tests are never weakened. Unavoidable scope expiries are recorded.

---

# 14. Registered identity

| Field | Value |
| --- | --- |
| Study id | `STUDY5_EQ1` |
| Namespace | `studies/study5/qualification-eq1/` |
| Kind | engineering qualification for a causal decomposition study |
| Cloud | AzureChinaCloud (Mooncake) |
| Subscription (last four) | `8845` |
| Storage account (safe name) | `s4fm11ca457e105b29b7` |
| GPU host (safe name) | `a100-vm`, `Standard_NC96ads_A100_v4`, chinaeast3 |
| CPU host (safe name) | `cpuserver`, `Standard_D16ds_v5`, chinanorth3 |
| Predecessor commit | `dac07a695e9cf820fcf3546ccff24826d3e47a30` |
| Evidence ledger at start | `EV-0016` |
| Confirmation authorized | **false** |

Salted identity hashes are recomputed per invocation with a fresh salt that is
never committed.

---

# 15. Registered terminal states

End in exactly one of the following. **None of these is a scientific result.**

* `STUDY5_EQ1_RESOURCE_INVENTORY_DRIFT_DETECTED`
* `STUDY5_EQ1_IMMUTABLE_ACQUISITION_FAILED`
* `STUDY5_EQ1_CONTAINER_OR_RUNTIME_UNAVAILABLE`
* `STUDY5_EQ1_ADAPTER_FIDELITY_BELOW_REGISTERED_FLOOR`
* `STUDY5_EQ1_WORKSPACE_BAND_NOT_ESTABLISHED_AT_THIS_SCALE`
* `STUDY5_EQ1_PURSUIT_VALIDATION_FAILED`
* `STUDY5_EQ1_INTERVENTION_NUMERICALLY_UNSTABLE`
* `STUDY5_EQ1_BUDGET_CEILING_REACHED_NO_REINTERPRETATION`
* `STUDY5_EQ1_EXECUTION_INTERRUPTED_NO_REINTERPRETATION`
* `STUDY5_EQ1_QUALIFIED_AWAITING_CONFIRMATORY_AUTHORITY`

`STUDY5_EQ1_WORKSPACE_BAND_NOT_ESTABLISHED_AT_THIS_SCALE` means the construct
was not established on this model and therefore nothing was measured. It is
**not** evidence that J-space is absent at 7B, and it may not be written up as
such.

---

# 16. What the successor authority must do

Only `STUDY5_EQ1_QUALIFIED_AWAITING_CONFIRMATORY_AUTHORITY` permits a successor.
That successor is a separate authority, separately approved, and it must:

1. register the frozen feature sets, band, `α` and `n_required` produced here,
   by hash, without recomputing or adjusting them;
2. realize and seal the confirmation bank before any confirmation forward pass;
3. publish the seal before the first confirmation model call;
4. test exactly two primary contrasts under gatekeeping — necessity first,
   sufficiency only if necessity passes — with all secondary outcomes
   descriptive and BH-FDR controlled;
5. carry the result-to-claim truth table verbatim, including its four blocker
   rows, and refuse any claim the table does not license.

No state reachable by this invocation authorizes that successor automatically.

---

*End of authority. Nothing below this line is normative.*
