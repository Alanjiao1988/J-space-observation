# Study 2 Stage T authority receipt (pre-execution)

Stage T is a tokenizer gate. It resolves the pinned configuration and tokenizer
identity of the three registered checkpoints, proves that the frozen Stage P
prompt bytes tokenize with single-token option continuations, verifies exact
pair length and answer-position alignment, selects the mechanistic pair sets by
tokenizer mechanics alone, and seals the result.

This receipt is written **before** any tokenizer is constructed and before any
Stage T rule can be influenced by a Stage T outcome. Everything it seals is a
rule; nothing it seals is a measurement.

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

The platform generated this branch label and later renamed it. The rename
changed no commit, no tree, no index entry, no worktree file, and no protected
byte. Under the final operator amendment these labels are audit metadata only.

### 1.2 Authoritative content identity (hard gate, all verified)

| Check | Result |
| --- | --- |
| `HEAD` after `git fetch origin` | `c2e2383e96ba3d94f3dcf9b9b57db36e1f08dcd1` |
| `origin/main` | `c2e2383e96ba3d94f3dcf9b9b57db36e1f08dcd1` |
| `HEAD^{tree}` | `533fb62db4db096f4f6d09eeb858a391936a28c9` |
| `git status --porcelain=v1` | empty (index and worktree clean) |
| Stage P registered origin `191d4a35…` is an ancestor | yes |
| Stage P validated freeze `d5e8e19c…` is an ancestor | yes |
| Registered ancestor `6409d2c6…` | yes |
| Registered ancestor `db8c100d…` | yes |
| Registered Stage P blob identities re-derived from `git cat-file` | 30 of 30 matched, 0 mismatches |
| Phase 1.0D protected rollup v1 | 152 files, `436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd`, `PROTECTED_BYTES_OK=1` |
| Phase 1.0D protected rollup v2 | 36 files, `ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a`, `RV2_PROTECTED_BYTES_OK=1` |
| `paper/evidence_ledger.csv` | 25,241 bytes, `3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1`, 17 lines, last row `EV-0016` |
| Stage T authority text | 22,229 bytes, `dce8c7167682b57e9a6cd8c7dbe651cbdcbfda13255ad9d434d06b7e7949b974` |

### 1.3 Zero-operation attestation at acceptance

At the moment of acceptance, and for every step up to the point this receipt was
written, the following counts were and remain zero: tokenizer constructions,
model downloads, model loads, forward passes, generations, activation
extractions, lens operations, probe fits, patching operations, ablations, GPU
jobs, semantic-review provider calls, Gate A operations, B-D operations, Phase
1.0D operations, RQ2/S4 operations, and scientific evidence rows.

---

## 2. Amendment audit (execution-plumbing correction)

Recorded in full in
[`studies/study2/prompts/stage_t_starting_state_operator_amendments.md`](prompts/stage_t_starting_state_operator_amendments.md).

1. **The original prompt incorrectly treated the local branch label as
   authoritative.** It required the session to start on `main`, but the Copilot
   worktree runs on a platform-generated branch. The first stop
   (`BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY`) was caused solely by a branch
   name, while every content check already passed.
2. **The earlier exact-alias amendment remained too narrow.** It admitted one
   literal branch name, `alanjiao-microsoft-miniature-eureka`. When the platform
   renamed the branch to `alanjiao1988-microsoft-miniature-eureka`, Stage T
   stopped a second time on a label, again with identical content.
3. **The final amendment makes commit/tree/protected-byte identity
   authoritative and local branch naming observational only.** Content identity
   remains a mandatory fail-closed hard gate; only the branch-name equality
   requirement was removed.

This correction is execution plumbing. It changed no frozen Stage P protocol,
schema, bank, threshold, seed, scientific selection, model registration,
tokenizer registration, or protected artifact, and it created no evidence row.
It was issued and applied before tokenizer construction and before any
scientific measurement.

---

## 3. Sealed Stage T rules

Every rule below is fixed by this receipt. If any of these bytes change, the
Stage T result they produced is void and must be re-derived.

### 3.1 Sealed source and contract

Seal revision 2 (see §3.7). The rows marked ▲ were revised after seal revision 1
and before any Stage T measurement existed.

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/jspace_observation/study2_stage_t.py` | 45,932 | `e81dedd99e1aed9347faa359eb1b2a5283b0ba74959c1ca83e83a14044ac9c7c` |
| ▲ `scripts/run_study2_stage_t.py` | 11,011 | `03953680aecc7a1362153dd0cff179812588711b743d771fa85407c63ebc12d4` |
| ▲ `scripts/validate_study2_stage_t.py` | 15,265 | `d040089339e718f7a922c2af8c537e36a399b09bca4322abf328bac227d5d757` |
| ▲ `tests/test_study2_stage_t.py` | 38,699 | `e473bb8b9a08c5daf83abd48c98574c95f96e676faba6b808ae82cf3e4371975` |
| ▲ `studies/study2/protocol/stage_t_pack.schema.json` | 38,872 | `394ef2e827c493e71d4e4780b7738e15ecdb9ef49128b105c4f5528568eb6290` |
| `infra/azure/acr_tasks/study2_stage_t.sh` | 4,549 | `ce78fca20251cf2280b7913c02a8cc0e11c169d2d92bdee3be325ef9dc9efcc5` |
| `infra/azure/acr_tasks/study2_stage_t.yaml` | 795 | `1916065a219dc0640bc108cf1f29ba99f2630e6b9e1a0605423e956f0434dbe7` |
| `infra/azure/acr_tasks/study2_stage_t_output.Dockerfile` | 568 | `74f7d6a4d03a128bffae5a6bd235047f5493fa770d6593f29ebc6fe74c54f1ff` |
| `studies/study2/prompts/stage_t_tokenizer_gate_prompt.md` | 22,229 | `dce8c7167682b57e9a6cd8c7dbe651cbdcbfda13255ad9d434d06b7e7949b974` |
| `studies/study2/prompts/stage_t_starting_state_operator_amendments.md` | 9,764 | `3aa642d472abc0b1b7f73980a7cf85c52086d9bbc632acd8d1735a4bed4a06fe` |

Seal revision 1 recorded these values for the four revised paths, and they are
kept here so the revision is auditable rather than silent:
`scripts/run_study2_stage_t.py` 9,409 /
`9733cbac8fdad9c19c6b925844eb0e358660e2ca3e8f27c3b1fcd8fbbec3931c`;
`scripts/validate_study2_stage_t.py` 15,266 /
`010f8492cb95d2e1884b93795f621a1deca341ed1c666896c72515a9267b11c7`;
`tests/test_study2_stage_t.py` 36,660 /
`44cfae98104977c8f449d93b3dd4696798a0461ff37e4f32031996f3a42c0da4`;
`studies/study2/protocol/stage_t_pack.schema.json` 38,358 /
`231144614a83dc4a658af81ebe44b02d24fdb6af72265a8ad8c5a5535a43154d`.

All ten blobs are stored LF-only; `.gitattributes` registers each of them with
`text eol=lf` so that the bytes the ACR agent executes are the bytes committed
here. A Stage P ACR run has already failed once because an unregistered `.sh`
reached the Linux agent with CRLF endings; that failure mode is now closed for
every Stage T file.

### 3.2 Sealed pinned identities

| Role | Model | Revision (immutable) |
| --- | --- | --- |
| `target` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| `lineage_base` | `Qwen/Qwen2.5-Math-1.5B` | `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2` |
| `instruction_control` | `Qwen/Qwen2.5-Math-1.5B-Instruct` | `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35` |

Acquisition is restricted to an explicit configuration/tokenizer allowlist. The
run refuses to continue if any weight or adapter file, or any unallowlisted
file, reaches the staged snapshot; `trust_remote_code` is `False`; downloads are
pinned by commit SHA and the resolved SHA must equal the pinned SHA.

### 3.3 Sealed gate rules

A prompt passes only if all of the following hold, and every failure is recorded
under a closed reason code:

- the prompt bytes hash to their frozen Stage P `prompt_hashes` value;
- the prompt ends with the frozen terminator `Answer:`;
- the tokenizer adds no special-token **suffix** (a suffix would move the answer
  position, so it is refused outright rather than compensated for);
- the canonical encoding is non-empty, is not truncated by `model_max_length`,
  contains no special token after the measured prefix, and decodes back to the
  measured prefix text plus the exact prompt;
- each of the four option surfaces adds **exactly one** token, preserves the
  complete prompt-token prefix, is not a special token, and round-trips
  byte-exactly;
- the four option token IDs are pairwise distinct.

BOS behaviour is **measured**, never assumed: the profile is the difference
between `add_special_tokens=True` and `add_special_tokens=False` on a probe
string, and the measured prefix is required to appear in every encoding.

`answer_position_index` is `len(base_ids) - 1`. Anchor resolution is
tokenizer-agnostic: the encodings of the prompt truncated at the anchor's start
and end byte offsets must both be prefixes of the full encoding and must differ
by exactly one token, otherwise the anchor is unresolved.

A mechanistic pair is eligible only if every one of its six objects passes the
option gate, all six encode to the same length, all six share the same answer
position, the pair's `wrong_position_anchor` equals the recipient's registered
`start_anchor`, and that anchor resolves to exactly one token. Joint eligibility
is a strict conjunction across all three pinned tokenizers.

### 3.4 Sealed selection rule

For each of the eight cells (2 mechanistic roles × 2 families × depths 2 and 3):
sort the jointly eligible pairs by ascending `pair_semantic_id` and take the
first 128, giving 512 per mechanistic role and 1,024 in total. There is no
outcome field in scope, no balance optimisation, no backfill from another cell,
and no replacement after inference. If any cell has fewer than 128 jointly
eligible pairs, Stage T stops under
`BLOCKED_ON_STUDY2_MECHANISTIC_TOKEN_SUPPORT` and reports the shortfall instead
of selecting a smaller or substituted set.

### 3.5 Sealed secondary axis

The J-lens digit-support table is a **target-only secondary diagnostic**.
Recording it may make that future readout axis ineligible; it can never rescue,
select, promote, or demote the lens-independent Stage T result. Both properties
are asserted as constants in the artifact and in the schema.

### 3.6 Sealed execution route

All Stage T execution happens in Azure Container Registry tasks on
`linux/amd64` from `python:3.11-bookworm`, against a `git bundle` of the sealed
commit that the agent clones and verifies itself. The workstation is limited to
text inspection and editing, Git and hashing operations, submitting ACR work,
and reading ACR results. No Stage T generator, gate, selector, or validator is
executed locally, and no local byte is uploaded except the task files, which the
agent compares against its own checkout with `cmp` before running them.

The cache root is asserted empty before acquisition and scanned for weight file
extensions afterwards; both assertions must pass. Before any acquisition the run
installs a **weight-load interlock**: it replaces
`transformers.modeling_utils.PreTrainedModel.from_pretrained`, the same class's
`from_config`, and the `from_pretrained` of every `AutoModel*` class with a stub
that raises. A weight load therefore aborts the run rather than succeeding
quietly. The interlock targets are listed in the attempt receipt, and the
validator refuses a receipt whose interlock list is empty.

Deterministic core artifacts contain no run ID, image digest, timestamp,
hostname, or filesystem path. Those live only in the per-attempt receipt, which
binds itself to the core manifest by hash.

### 3.7 Seal revision 2, issued before any Stage T measurement existed

Attempt `t1a` (ACR run `cmck`, source commit `2b1bd84`) **aborted before the
gate ran**. All three pinned tokenizers were acquired and constructed, and every
resolved revision equalled its pinned revision, but the run then stopped in a
self-check: seal revision 1 treated the mere *import* of
`transformers.models.auto.modeling_auto` as proof that a weight path had been
entered, and `transformers` 5.14.1 resolves its auto-class registry eagerly, so
that module appears without a single tensor being read. Reading the registry is
not a weight load, so the original check was simply wrong about its own
evidence.

The correction replaces a passive observation with an active interlock, as
described in §3.6. This is strictly stronger: seal revision 1 could only report,
after the fact, that a weight-loading module had not been imported, whereas
revision 2 makes a weight load raise. The module-import list is retained in the
receipt as an observation, and a new test asserts statically that the interlock
is installed in `main` before the first acquisition call and that it replaces
loaders via `setattr` rather than merely inspecting them.

What this revision does **not** touch: no frozen Stage P byte, no protocol, no
schema of any scientific row, no bank, no threshold, no seed, no model or
tokenizer registration, no prompt or option gate rule, no eligibility rule, and
no selection rule. It cannot change which pairs are selected.

Crucially, no Stage T measurement existed when this revision was made. Run
`cmck` produced no core manifest, no prompt pack, no eligibility table, no joint
table, and no selection; it never reached `run_gate`. The revision was therefore
made blind to every Stage T outcome, which is exactly the condition a
pre-execution seal is meant to guarantee.

---

## 4. Boundaries this receipt does **not** cross

Stage T is authorised for tokenizer mechanics only. This receipt is not
authority for, and Stage T performs none of: Gate A, Gate B, Gate C, Gate D,
model weight download or load, model forward passes, generation, activation
extraction, probe fitting, activation patching, ablation, J-lens computation,
GPU jobs, semantic-review provider calls, Phase 1.0D operations, RQ2/S4
operations, or any scientific evidence row. `paper/evidence_ledger.csv` must
still end at `EV-0016` when Stage T finishes.

---

## 5. Disclosure

A pre-existing user-level Hugging Face cache is present on the shared
workstation at `C:\Users\alanjiao\.cache\huggingface\hub`, containing
`models--deepseek-ai--DeepSeek-R1-Distill-Qwen-1.5B` and
`models--Qwen--Qwen2.5-Math-1.5B`. It was created by earlier unrelated work.
Stage T did not create, read, write, or reference it. All Stage T acquisition
occurs inside ACR against a cache root that is proven empty beforehand and
weight-free afterwards.
