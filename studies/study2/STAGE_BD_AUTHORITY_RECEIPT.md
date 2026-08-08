# Study 2 Stage B-D authority receipt (pre-execution)

Stage B-D is a development-only behavioral execution round plus the
pre-registered, non-scientific **Gate A** feasibility decision. It implements the
frozen behavioral computation, loads the three registered 1.5B checkpoints
exactly as pinned, runs the complete 384-item development bank under every
applicable arm, seals the development artifacts, and evaluates the already-frozen
Gate A rule.

This receipt is written **before** any model weight is loaded and before any
forward pass exists. Everything it seals is a rule. Nothing it seals is a
measurement. No Gate A count in this document is observed; every threshold,
every arm set, every shard boundary and every terminal branch below was fixed
while the outcome was still unknown.

---

## 1. Starting-state disposition

```
STARTING_STATE_ACCEPTED_UNDER_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE
```

### 1.1 Observed session metadata (recorded, non-authoritative)

| Item | Observed value |
| --- | --- |
| `git branch --show-current` | `alanjiao1988-microsoft-miniature-eureka` |
| Worktree directory name | `alanjiao-microsoft-miniature-eureka` |
| Workspace type | platform-managed Copilot worktree |
| Remote | `origin` → `Alanjiao1988/J-space-observation` |

The branch label, the worktree path and the session name are audit metadata.
They are not admission gates. A label-only change triggers revalidation and
logging; it never produces `BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY`.

### 1.2 Authoritative content identity (hard gate, all verified)

| Check | Result |
| --- | --- |
| `HEAD` after `git fetch origin` | `a958adf4aec5736ef04f468fc3532ca7c92f7e5e` |
| `origin/main` | `a958adf4aec5736ef04f468fc3532ca7c92f7e5e` |
| `HEAD^{tree}` | `f96729c41dcbd8b20e156177e2533516cb44a1ef` |
| `git status --porcelain=v1` at acceptance | empty (index and worktree clean) |
| Stage P registered origin `191d4a35…` is an ancestor | yes |
| Stage P validated freeze `d5e8e19c…` is an ancestor | yes |
| Stage T starting commit `c2e2383e…` is an ancestor | yes |
| Registered ancestors `6409d2c6…`, `db8c100d…` | yes |
| Registered Stage P / Stage T blob identities re-derived from disk | 14 of 14 matched, 0 mismatches |
| Phase 1.0D protected rollup v1 | 152 files, `436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd`, `PROTECTED_BYTES_OK=1` |
| Phase 1.0D protected rollup v2 | 36 files, `ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a`, `RV2_PROTECTED_BYTES_OK=1` |
| `paper/evidence_ledger.csv` | 25,258 bytes, `fec8dba3bc0e7906a448702b64060ac4058a65d14f0eafc9afe005d2b0a72135`, 17 rows, last row `EV-0016` |
| Stage B-D authority text | 25,173 bytes, `f6932e50cf5692ef01df9b5b8a930a3941de9620a7404653c92ffd4e9ea7e8ed`, 355 lines |

`a958adf4…` is the commit Stage T published. Stage B-D therefore starts from the
sealed Stage T state, not from a re-derived one.

### 1.3 Zero-operation attestation at acceptance

At acceptance, and for every step up to the moment this receipt was written, the
following counts were and remain zero: model downloads, model loads, forward
passes, generations, activation extractions, lens operations, probe fits,
patching operations, ablations, GPU jobs, semantic-review provider calls, B-C
operations, mechanistic-cell selections, M-D operations, M-C operations, Phase
1.0D operations, RQ2/S4 operations, and scientific evidence rows.

Tokenizer construction is **not** claimed to be zero for this stage: Stage T
already constructed the three registered tokenizers under its own authority and
sealed the resulting prompt identities. Stage B-D reuses those sealed identities
and re-derives them at execution time only to confirm they still hold.

---

## 2. Amendment and plumbing audit

### 2.1 Branch-metadata amendment (inherited, still in force)

Recorded in full in
[`prompts/stage_t_starting_state_operator_amendments.md`](prompts/stage_t_starting_state_operator_amendments.md)
and carried into this stage unchanged:

1. **The original prompt incorrectly treated the local branch label as
   authoritative.** The first stop was caused solely by a branch name while every
   content check already passed.
2. **The earlier exact-alias amendment remained too narrow.** It admitted one
   literal branch name; the platform then renamed the branch and Stage T stopped
   a second time on a label with identical content.
3. **The final amendment makes commit/tree/protected-byte identity authoritative
   and local branch naming observational only.** Content identity remains a
   mandatory fail-closed hard gate; only branch-name equality was removed.

### 2.2 AcrPush role-assignment correction (new, this stage)

Stage B-D must return artifacts from a GPU container to the workstation. Both
storage accounts in the subscription are private-endpoint-only and are therefore
unreachable from this session, so artifacts travel over the container registry as
OCI blobs — the same transport Stage T used for retrieval, run in the opposite
direction.

The managed identity `id-jspace-aca-acrpull-sea` held `AcrPull` only. It was
granted `AcrPush` on the registry `acrjspaceobssea0708231738` so a job running
under that identity can upload its own output artifact.

This is execution plumbing. It changed no frozen protocol, schema, bank,
threshold, seed, scientific selection, model registration, tokenizer
registration, or protected artifact, it created no evidence row, and it was
applied before any weight was loaded. It grants no ability to modify repository
content: the registry is a transport, and every artifact retrieved from it is
verified against hashes registered here before it is admitted.

---

## 3. Sealed Stage B-D rules

Every rule below is fixed by this receipt. If any of these bytes change, the
result they produced is void and must be re-derived.

### 3.1 Sealed source and contract

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/jspace_observation/study2_stage_bd.py` | see `stage_bd_preinference_seal.json` | sealed at execution time |
| `scripts/run_study2_stage_bd_gpu.py` | see seal | sealed at execution time |
| `scripts/finalize_study2_stage_bd.py` | see seal | sealed at execution time |
| `scripts/validate_study2_stage_bd.py` | see seal | sealed at execution time |
| `tests/test_study2_stage_bd.py` | see seal | sealed at execution time |
| `studies/study2/protocol/stage_bd_pack.schema.json` | 36,009 | `f24ed3168f743d1141da9c2e9549b63020aa5c1652f1ea6829de4bfbbfd811f7` |
| `studies/study2/prompts/study2_stage_bd_operator_authority.md` | 25,173 | `f6932e50cf5692ef01df9b5b8a930a3941de9620a7404653c92ffd4e9ea7e8ed` |

The five paths marked "sealed at execution time" are hashed into
`studies/study2/stage_bd/stage_bd_preinference_seal.json`, which is committed and
published **before** the first weight load. Their values are not written here
because this receipt is authored first; the seal is the binding record, and the
commit order is the proof that no measurement could have influenced them.

### 3.2 Frozen inputs (20 files, hash-checked at every entry point)

`study2_stage_bd.FROZEN_INPUTS` registers the exact byte length and SHA-256 of
every input Stage B-D reads: the development bank, the task-bank manifest, the
three Stage T prompt-tokenization packs, the Stage T seal and pack manifests, the
frozen protocol module, the charter, the Stage P handoff, the protocol document
and freeze, and this stage's authority text. `verify_frozen_inputs` runs at the
start of the GPU runner, the finalizer and the validator. Any drift is a hard
stop.

### 3.3 Row space

| Quantity | Value |
| --- | ---: |
| Development items | 384 |
| Model roles | 3 (`target`, `lineage_base`, `instruction_control`) |
| Applicable arms per item | derived from the frozen arm rule |
| Logical rows | 3,072 |
| Rows per model | 1,024 |
| Run ID | `s2-bd-development-v1` |

`RUN_ID` is a deterministic constant because `run_id` is part of the frozen
`behavioral_row` primary key. No cloud job ID, container name, timestamp or
attempt number may enter a core row; those live in receipts only, so a retry can
never change a row's identity.

### 3.4 Shard boundaries (outcome-independent, sealed before execution)

Work is partitioned by `role × family × depth` into **18 shards** of 64, 192 or
256 rows (1,024 per model). Every arm of an item stays in one shard, so no shard
boundary can split a within-item comparison. The manifest digest is

```
shard_manifest_sha256 = 15d0c454f8f3e8aa839998bab9090f9e706b69629b1758b5909d5a0dfac986c0
```

A shard may be retried at most 3 times, only for one of the 7 registered B-D
blocker reasons, and each attempt is identified by
`attempt_id = "bd-" + sha256("jspace-study2-stage-bd/attempt/v1\n{run_id}\n{shard}\n{attempt}\n")[:16]`.
Retries are recorded in the execution receipt. A retry may replace a shard's rows
only in full; partial merges are rejected.

### 3.5 Execution discipline

Authoritative forwards run at **batch size 1** with `use_cache=False`,
`trust_remote_code=False`, fp16, and the pinned revision for each role.
`install_interlocks()` disables `generate`, `sample`, beam search, hook
registration and `apply_chat_template` before any weight is loaded, so a
generation or activation read is not merely forbidden by policy but unavailable
in the process. `verify_prompt_identity` re-derives the Stage T
`input_ids_sha256`, `input_length` and `answer_position` for every prompt
immediately before its forward; a mismatch stops the shard.

The GPU build context excludes the confirmation banks, and
`assert_confirmation_unaddressable` proves their absence from the execution
filesystem. The resulting receipt is carried forward by the model-free stages
rather than recomputed, because only the execution context can honestly attest
to it.

### 3.6 Gate A (frozen before any count exists)

| Element | Registered value |
| --- | --- |
| Population | target model, `NT` arm, development bank only |
| Pooling | depths 2 and 3 pooled within family |
| Cell size | exactly 64 items per depth → n = 128 per family |
| Null | p₀ = 0.25 |
| α | 0.025, one-sided binomial upper tail |
| Pass threshold | X ≥ 43 |
| Decision rule | both families must pass |
| Controls | run and reported, zero authority over the decision |

Verified exactly against the frozen implementation:
`binomial_upper_tail(128, 0.25, 43) = 0.018218515932540265` and
`binomial_upper_tail(128, 0.25, 42) = 0.028760674518293294`. A passing control
model cannot rescue a failing target.

Terminal branches, also frozen:

* both families pass →
  `NONTERMINAL_CHECKPOINT_STUDY2_STAGE_BD_GATE_A_PASSED_AWAITING_BC_AUTHORITY`
* otherwise → `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`

Gate A is a feasibility decision about whether the study can proceed. It is not a
scientific result, it creates no evidence row, and it changes no support status.

### 3.7 Balance invariant granularity

The registered balance invariant `_validate_cell_balance` is defined at
**family × depth** granularity (64 items), which is how the frozen protocol
applies it. Applying it to the pooled 128-item Gate A population is not the
registered check and fails on the frozen bank's own start-state distribution.
`gate_balance` therefore validates the registered invariant per depth and checks
only structural facts — n = 128, 64 per depth, distinct item and semantic IDs —
on the pooled population. This is a reading of the frozen rule, not a change to
it.

---

## 4. Two-stage verification

No pack may reach Gate A on the writer's own word.

1. `scripts/finalize_study2_stage_bd.py` — model-free. Verifies every shard
   receipt against the sealed manifest, merges, re-verifies every row, computes
   the summaries, bootstrap diagnostics and Gate A rows, and writes the closed
   pack.
2. `scripts/validate_study2_stage_bd.py` — independent. Reconstructs the expected
   3,072 primary keys from the frozen bank, re-reads every emitted row,
   re-derives every derived field, re-checks every prompt identity against the
   sealed Stage T pack, recomputes the summaries, diagnostics and Gate A counts,
   re-validates every artifact against the closed schema, re-checks the operation
   counts and confirms the evidence ledger still ends at `EV-0016`. It certifies
   only a complete pack, and any unexpected condition is reported as a structured
   refusal rather than an exception.

Both refuse to import `torch`, `transformers` or any lens/probe module, and both
assert that refusal at runtime.

---

## 5. Scope limits

This receipt is authority for exactly one thing: development-bank behavioral
execution and the frozen Gate A decision.

It is **not** authority for B-C, mechanistic-cell selection, M-D, M-C, activation
extraction, probes, patching, ablation, J-lens, natural-language generation, the
confirmation banks, any Phase 1.0D or RQ2/S4 operation, or any scientific
evidence row. `paper/evidence_ledger.csv` ends at `EV-0016` before this stage and
must end at `EV-0016` after it.
