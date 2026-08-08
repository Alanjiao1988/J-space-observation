# Study 2 Stage T starting-state operator amendments

This document is part of the Stage T audit record required by the final
amendment, §5. It is an execution-plumbing record. It changes no frozen Stage P
protocol, schema, bank, threshold, seed, scientific selection, model
registration, tokenizer registration, or protected artifact, and it creates no
scientific evidence.

The governing authority remains
`studies/study2/prompts/stage_t_tokenizer_gate_prompt.md`
(22,229 bytes, SHA-256 `dce8c7167682b57e9a6cd8c7dbe651cbdcbfda13255ad9d434d06b7e7949b974`).
Both amendments below modify **only** that authority's local-branch-name
predicate. Every other Stage T requirement, boundary, blocker, and prohibition
continues to apply unchanged.

---

## 1. The original blocker

The original Stage T authority required the session to start on local branch
`main`. The Copilot session executes inside a platform-managed Git worktree
whose branch is generated and may later be renamed by the platform. At the
first preflight the observed branch was:

```
alanjiao-microsoft-miniature-eureka
```

Every content-identity check already passed at that point, but the local branch
label did not read `main`, so Stage T stopped under
`BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY` without editing a file, running an
ACR job, constructing a tokenizer, or touching a model.

**Fact 1 (required audit statement).** The original prompt incorrectly treated
the local branch label as authoritative. A branch name is a mutable local
reference; it carries none of the content identity that Stage T actually
depends on.

---

## 2. First amendment: exact alias (superseded)

The operator issued an amendment accepting the worktree branch as a controlled
execution alias of `main`, on the basis that it had been verified to satisfy:

- `HEAD == origin/main == c2e2383e96ba3d94f3dcf9b9b57db36e1f08dcd1`
- tree `533fb62db4db096f4f6d09eeb858a391936a28c9`
- clean worktree
- ancestor relationships to the registered Stage P origin and validated-freeze
  commits
- all checked protected bytes equal to their registered hashes
- no file modification, ACR run, tokenizer construction, model load, commit, or
  push had yet occurred

That amendment permitted the starting branch to be either `main` or that one
exactly named branch, required full revalidation before execution, kept
fail-closed behaviour for every other inconsistency, forbade switching,
merging, rebasing, resetting, cherry-picking, or recreating the worktree, and
required publication to remote `main` via a non-force, fast-forward-only
explicit refspec.

The platform then renamed the session branch to:

```
alanjiao1988-microsoft-miniature-eureka
```

The commit, tree, index, worktree cleanliness, and protected bytes were all
unchanged, but the new label fell outside the exact alias, so Stage T stopped
again — again without modifying anything.

**Fact 2 (required audit statement).** The earlier exact-alias amendment
remained too narrow. Enumerating one permitted branch name reproduced the
original defect at a smaller scale, because the platform may create, normalize,
or rename its session branch at any time.

---

## 3. Final amendment: content identity is authoritative

The operator issued a final amendment superseding only the local-branch-name
predicate in the original authority and in the exact-alias amendment.

### 3.1 Branch and worktree names are non-authoritative metadata

`git branch --show-current`, the local branch name, the session name, and the
worktree path are recorded for audit purposes and are **not** Stage T admission
gates. Any platform-managed local branch name is acceptable, including `main`,
`alanjiao-microsoft-miniature-eureka`,
`alanjiao1988-microsoft-miniature-eureka`, any later platform-generated or
normalized session branch name, and detached HEAD if the platform imposes it.

A branch-name-only or worktree-path-only change must trigger revalidation and
logging, and must not produce `BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY`.

The branch or worktree must not be renamed, switched, merged, rebased, reset,
cherry-picked, deleted, or recreated merely to satisfy a branch-name condition.

### 3.2 Content identity remains the mandatory hard gate

Before any file change or tokenizer construction, the complete original Stage T
preflight is rerun and all of the following must hold:

- repository identity and origin remote are the expected `J-space-observation`
  repository;
- after fetch, `HEAD == origin/main == c2e2383e96ba3d94f3dcf9b9b57db36e1f08dcd1`;
- `HEAD^{tree} == 533fb62db4db096f4f6d09eeb858a391936a28c9`;
- the index and worktree are completely clean;
- the registered Stage P origin and validated-freeze commits retain the
  required ancestor relationships;
- all Stage P frozen Git-blob hashes match the registered manifest;
- both protected Phase 1.0D rollups match their registered values with zero
  differences;
- `paper/evidence_ledger.csv` still ends at `EV-0016`;
- no tokenizer construction, model download or load, model forward, generation,
  activation extraction, lens, probe, patching, ablation, Gate A, B-D, GPU job,
  provider call, Phase 1.0D operation, RQ2/S4 operation, or scientific evidence
  row has occurred.

The original cryptographic checks, protected-byte checks, ancestry checks,
zero-operation checks, and fail-closed behaviour remain mandatory. Only the
local branch-name equality requirement is removed. Any difference in an
authoritative commit, tree, file content, hash, rollup, remote state, protected
boundary, or prohibited-operation count stops Stage T under the applicable
registered blocker and must not be treated as a branch-metadata exception.

### 3.3 Required preflight disposition

On a complete pass, record:

```
STARTING_STATE_ACCEPTED_UNDER_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE
```

together with the observed local branch name and the explanation that the
platform changed the label without changing the commit, tree, index, worktree,
or protected bytes. A passing validation authorises resuming the original Stage
T workflow from its initial stopped point. It is **not** authority for Gate A,
B-D, model weights, model forward, generation, activation extraction, probe,
patching, ablation, lens, or any scientific-evidence creation. Stage T must not
stop again merely to request permission for the observed branch name.

### 3.4 Commit and publication rule

Stage T commits may be created on the platform-managed session branch. Before
every publication attempt: fetch `origin`; confirm remote `main` has not moved
unexpectedly relative to the expected Stage T publication parent; confirm the
local Stage T history is a strict descendant of the verified starting commit;
confirm the push is fast-forward only; publish with an explicit non-force
refspec such as `git push origin HEAD:refs/heads/main`. Never force push. If
publication is rejected as non-fast-forward, or remote `main` has moved
unexpectedly, stop and report the divergence without merging, rebasing,
resetting, cherry-picking, or otherwise integrating the remote movement.

After a successful push, fetch again and verify `HEAD == origin/main`, the
expected tree identity, a clean worktree, and unchanged protected hashes and
rollups.

**Fact 3 (required audit statement).** This final amendment makes
commit/tree/protected-byte identity authoritative and local branch naming
observational only.

---

## 4. Disposition recorded for this session

| Item | Value |
| --- | --- |
| Preflight disposition | `STARTING_STATE_ACCEPTED_UNDER_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE` |
| Observed local branch at acceptance | `alanjiao1988-microsoft-miniature-eureka` |
| Worktree directory name | `alanjiao-microsoft-miniature-eureka` |
| `HEAD` = `origin/main` | `c2e2383e96ba3d94f3dcf9b9b57db36e1f08dcd1` |
| `HEAD^{tree}` | `533fb62db4db096f4f6d09eeb858a391936a28c9` |
| Index and worktree | clean, zero entries from `git status --porcelain=v1` |
| Registered blob identities re-derived | 30 of 30 matched, 0 failures |
| Phase 1.0D protected rollup v1 | 152 files, `436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd`, zero differences |
| Phase 1.0D protected rollup v2 | 36 files, `ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a`, zero differences |
| `paper/evidence_ledger.csv` | 25,241 bytes, SHA-256 `3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1`, last row `EV-0016` |
| Prohibited operations executed before acceptance | 0 |

The acceptance basis is that the commit, tree, index state, worktree
cleanliness, and every protected byte were identical to the values the original
authority required. Only the mutable local label differed.

## 5. Classification

This correction is **execution plumbing**, not a scientific protocol change. It
alters no measurement, no threshold, no seed, no bank, no selection rule, and no
claim. It was issued and applied before any tokenizer was constructed and before
any scientific measurement of any kind.

## 6. Disclosure: pre-existing Hugging Face cache on the workstation

The preflight observed a pre-existing user-level Hugging Face cache at
`C:\Users\alanjiao\.cache\huggingface\hub` containing
`models--deepseek-ai--DeepSeek-R1-Distill-Qwen-1.5B` and
`models--Qwen--Qwen2.5-Math-1.5B`. It was created by earlier, unrelated work on
a shared workstation. Stage T neither created, read, wrote, nor referenced it:
all Stage T acquisition happens inside Azure ACR against a cache root that the
task asserts is empty before acquisition and weight-free afterwards. It is
disclosed here because an auditor inspecting the machine would otherwise see
model directories and could not otherwise tell that Stage T did not use them.
