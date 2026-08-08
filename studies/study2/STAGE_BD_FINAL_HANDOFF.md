# Study 2 Stage B-D — final handoff

Terminal state: `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`

This document closes Stage B-D and, with it, protocol v1 of the Study 2
reasoning-internalization investigation. It is written for whoever picks the
work up next and assumes no memory of the session that produced it.

## 1. What this round was allowed to do, and did

The Stage B-D operator authority
(`studies/study2/prompts/study2_stage_bd_operator_authority.md`, 25,173 bytes,
SHA-256 `f6932e50cf5692ef01df9b5b8a930a3941de9620a7404653c92ffd4e9ea7e8ed`)
authorized exactly five things: implement and validate the frozen behavioral
computation, load the three registered 1.5B checkpoints exactly, run the complete
384-item development bank under every applicable arm, seal the development
artifacts, and evaluate the already-frozen Gate A rule.

All five were completed. Nothing else was started.

The round produced 3,072 behavioral rows (384 items × arms, 1,024 rows per
model), 96 development summaries, 48 bootstrap diagnostic rows, the six-row
feasibility table, the Gate A decision, and a manifest-last core pack.

## 2. The decision

`overall_gate_pass = false`.

| family (target, NT, depths 2+3) | X | n | exact upper tail | pass |
| --- | --- | --- | --- | --- |
| `permutation_chain` | 25 | 128 | 0.9403523926144965 | no |
| `affine_mod10` | 33 | 128 | 0.4526854444021635 | no |

The threshold was X ≥ 43 (p ≤ 0.025 under p₀ = 0.25), frozen before any
measurement. Chance is 32/128. The target model was at or below chance on both
families.

The full reasoning, the descriptive control results, and the argument that this
is not a measurement artifact are in
`studies/study2/decisions/study2_stage_bd_gate_a_decision.md`.

Gate A failure is the registered non-scientific closure of protocol v1. It is
**not** evidence about internal reasoning, distillation, or J-space, and it
creates no scientific evidence row.

## 3. What is now closed, and what a successor may not do

Closed:

- Stage B-C (behavioral confirmation) was not opened and may not be opened under
  this protocol version;
- mechanistic-cell selection, M-D, and M-C were not started;
- protocol v1 is closed.

A successor must not backfill, replace, re-render, pool away, reinterpret, or
rerun this protocol version. Any further attempt requires a **new protocol
version, a new operator authority, and new task-bank seeds**. Re-running the
frozen bank to obtain a different answer is specifically prohibited.

The confirmation bank was never opened. All six registered confirmation paths
were physically absent from the execution image (`CONFIRMATION_PATHS_PRESENT=0`),
and the receipt records zero confirmation tokenizations, forwards, output
objects, identity loads, mechanistic operations, and model-free integrity reads.

## 4. Where the bytes came from

Nothing in the pack was produced on the workstation. The workstation only
inspected text, computed hashes, ran Git, submitted Azure jobs, and retrieved
Azure-produced artifacts by digest.

**Behavioral rows** — Azure Container Apps, GPU T4 workload profile:

- job `job-js-s2-bd-2bb70de3`, execution `job-js-s2-bd-2bb70de3-dyu2efq`, Succeeded;
- image `sha256:60fd31b4b396dd09565103d85b9ccf9a8d0703f4d6333e870167b95ee02ebe86`,
  locked against write and delete before launch;
- source commit `2bb70de3c2bd32a67f21b674bcecb44126032ac0`, tree
  `d585ae563b8c852aad8bfe18d288e69e9db09090`;
- runtime: `Tesla T4`, torch `2.4.1+cu121`, transformers `4.46.3`,
  Python `3.11.9`, `PYTHONHASHSEED=0`;
- 18 shards complete, 0 retries, batch size 1;
- shard artifact manifest `sha256:3145e7b1b887da3f7d45e722b1edc5ceb804448fe461c1642943ea50e92db5bc`.

**Aggregation and Gate A** — Azure Container Apps, CPU Consumption profile, on an
image with neither `torch` nor `transformers` installed:

- job `job-js-s2-bdf-efd2b507`, execution `job-js-s2-bdf-efd2b507-z1oy5b8`, Succeeded;
- image `sha256:a4b90d55c5f2a07c513a6d25b2b3c8bd29d4e263be4996661ccba496971aaaf2`;
- `scripts/finalize_study2_stage_bd.py` wrote the pack, then
  `scripts/validate_study2_stage_bd.py` — which shares no writing code path —
  certified it: `certified: true`, `rows: 3072`, `failures: []`;
- pack artifact manifest `sha256:99e54775579b8641a72fe720b287d04d810b16c76133910d546fcc15c81cbf15`.

Every committed file was pulled from the registry by **manifest digest** and
compared byte-for-byte against the digests the job printed before it exited.

## 5. Reproducibility evidence

- **The pre-inference seal.** `stage_bd_preinference_seal.json` (5,844 bytes,
  SHA-256 `0c4efb0d25012673834381df1ae566802af0f3785f1ee6df72f8d67a352c4a9a`) was
  generated, published to `main`, and only then used. It pre-registers the row
  count, the primary-key digest, the shard-manifest digest, the option token IDs,
  twenty frozen input hashes, and the byte identity of the core module. The GPU
  job verified it against the published copy **before importing torch** and
  printed `SEAL_VERIFIED=0c4efb0d…`.
- **The seal is deterministic.** It was produced three times, on two different
  image digests, with byte-identical results.
- **The pack is deterministic.** Two finalization runs on two different image
  digests reproduced all eleven artifact digests identically.
- **The shard manifest closed the loop.** The digest the GPU job reported,
  `7a0f529a9868b054fed21510959c305c01861e6dbe0692f66c1294b6885317b5`, equals the
  value sealed before any weight was loaded.

## 6. Model identity

All three loaded at their pinned revisions with `trust_remote_code=False`,
`use_cache=False`, `torch.float16`, and `generated_tokens = 0`.

| role | model_id | resolved revision | params | model class | tokenizer class |
| --- | --- | --- | --- | --- | --- |
| `target` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` | 1,777,088,000 | `Qwen2ForCausalLM` | `LlamaTokenizerFast` |
| `lineage_base` | `Qwen/Qwen2.5-Math-1.5B` | `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2` | 1,543,714,304 | `Qwen2ForCausalLM` | `Qwen2TokenizerFast` |
| `instruction_control` | `Qwen/Qwen2.5-Math-1.5B-Instruct` | `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35` | 1,543,714,304 | `Qwen2ForCausalLM` | `Qwen2TokenizerFast` |

## 7. Operation counts

From `stage_bd_core_manifest.json`, and independently re-checked by the
validator, which requires every field except the four execution counters to be
zero:

| operation | count |
| --- | --- |
| `forward_passes` | 3,072 |
| `weight_loads` | 3 |
| `tokenizer_constructions` | 3 |
| `model_downloads` | 3 |
| `generations` | 0 |
| `activation_operations` | 0 |
| `probe_fits` | 0 |
| `patching_operations` | 0 |
| `ablation_operations` | 0 |
| `lens_fits` / `lens_applies` / `lens_loads` | 0 |
| `behavioral_confirmation_forwards` | 0 |
| `behavioral_confirmation_tokenizations` | 0 |
| `mechanistic_development_operations` | 0 |
| `mechanistic_confirmation_operations` | 0 |
| `phase1_0d_operations` | 0 |
| `rq2_s4_runs` | 0 |
| `semantic_review_provider_calls` | 0 |
| `scientific_evidence_rows` | 0 |

## 8. Known defects and disclosures

These are recorded because a successor auditing the pack will notice them.

### 8.1 `expected_primary_keys_sha256` means two different things

The seal and the core manifest both contain a field named
`expected_primary_keys_sha256`, computed with the same domain string, but they
are **not** the same digest:

- seal: `7b3e6c53188fd089e0ce59c12149adf46bf4033a07b6df4d51866ff6c7d56aa1`,
  over the keys in `expected_row_keys()` generation order;
- core manifest: `d15cc1bdaaf7c7db548208ee1c68903bfc18d2170a8522c059e4ea8e36199677`,
  over the merged rows, which `merge_shard_rows` returns in lexicographic key
  order.

`expected_row_keys()` does not emit in sorted order, so the two orderings differ
and so do the digests. Both digest the identical 3,072-key set; the field name
in the core manifest is misleading and nothing verifies it.

This is a naming defect, not an integrity gap. The substantive property — that
the pack is exactly the expected row space — is proven independently by the
validator, which asserts `len(observed) == len(set(observed))` and
`set(observed) == set(expected)` and fails closed before any recomputation if
either check fails. The per-shard `row_keys_sha256` values also matched the
sealed shard manifest.

Both digests are reproducible from the committed pack. It was left uncorrected
deliberately: the core module's bytes are bound by a seal that was published
before any weight was loaded, and rewriting them after seeing the result would
destroy the property that makes the seal worth having. A future protocol version
should rename the manifest field or compute it over sorted expected keys.

### 8.2 Local development iterations

The implementation was iterated locally before execution. Local `pytest` runs
were development-only and carry no evidential weight; the admissible test
evidence is the ACR runs recorded in `docs/run_log.md`. No local run touched a
model weight, and the confirmation objects were never opened locally.

### 8.3 Azure plumbing corrections made during the round

Each was an execution-plumbing correction that changed no scientific byte,
threshold, seed, bank, or protocol value. They are listed so a successor does not
rediscover them:

- ACR's Dockerfile dependency scanner cannot parse heredocs; build-time checks
  moved into `infra/azure/acr_tasks/study2_stage_bd_image_verify.py`.
- The Windows worktree has `core.autocrlf=true`, so copied shell scripts reached
  Linux containers with CRLF and failed at `set -euo pipefail`.
  `scripts/build_azure_context.py` now materializes every context from committed
  Git blobs and refuses any blob that already contains CRLF.
- `git bundle create <file> <bare-sha>` fails because a bundle needs a ref; the
  helper verifies `HEAD == --commit` and bundles `HEAD`.
- `az acr repository update --image repo:tag` locks the **tag**, not the
  manifest. Both must be locked, and the launchers refuse an unlocked manifest.
- `az acr build` resolves `--file` against the working directory before the
  uploaded context, so running the build helpers from the repository root packed
  the repository's own top-level `Dockerfile` over the intended one and silently
  built the wrong image. Both helpers now run the build from inside the context
  directory.
- ACA GPU workload-profile containers cannot write `/work`, though Consumption
  containers can; job shells probe and fall back to `${TMPDIR:-/tmp}`.
- An mtime-based source-modification guard compared against a checked-out file,
  whose write order git does not guarantee; it now compares against a marker
  touched at job start.
- `low_cpu_mem_usage=True` requires `accelerate`, which is deliberately absent
  from the sealed image. The flag was removed rather than adding the dependency;
  it is a transient memory optimization and loaded parameter values are identical.
- The finalize job's reporting step read `overall_gate_pass` from the core
  manifest, which carries only the derived `terminal_state`. The finalizer and
  validator had already succeeded when the lookup raised `KeyError`, so the
  failure was in reporting, not measurement; it now reads the boolean from
  `stage_bd_gate_a_decision.json`.

The pre-inference seal was created and published **before** all of the failures
that followed it, and the artifacts it binds were reproduced byte-identically
across those image changes, so none of these corrections could have moved the
measurement.

## 9. Artifacts

All under `studies/study2/stage_bd/`.

| file | bytes | SHA-256 |
| --- | --- | --- |
| `stage_bd_core_manifest.json` | 41,322 | `4a64cbf9de6d2fae476589b3a8213dd5bf2dedad19c40b9d4003dd768fa56716` |
| `stage_bd_gate_a_decision.json` | 38,845 | `1aebc183e157f8097cdc88ab3a9dbdb53bd1ae3bf4ff6a428e3e9dfef49a3544` |
| `stage_bd_feasibility_gate.jsonl` | 3,019 | `75e71a39465a34aa94e8691b1b1fe16bba24d863324968049294cd0315f68a3a` |
| `stage_bd_development_summaries.jsonl` | 68,098 | `9b7531e44303f7ddde3849a49c9b0e6a49124726ca3b654d1ead7ba997ffbf3e` |
| `stage_bd_bootstrap_diagnostics.jsonl` | 17,868 | `628607fa5414737511d3ab6011d8322c21cc15913621b770db7d8429f7336c47` |
| `stage_bd_behavioral_development_target.jsonl` | 1,002,446 | `9ada004f1c9c25f940e00de7753dd6563e3898153c66099f7b84360aaa8ea34e` |
| `stage_bd_behavioral_development_lineage_base.jsonl` | 993,298 | `f4a3a7c2b09082d2f96fcde34397f2460a8633456d209c9148dccd327df69ead` |
| `stage_bd_behavioral_development_instruction_control.jsonl` | 1,010,650 | `df831dcc14d4812cd9448cc20e13f00f929f9493d51aaf8d44f01be4a9181ea4` |
| `stage_bd_weight_identity_receipt.json` | 14,249 | `5e6ec733faf3836bfcefe9bcede55b7991c5b7d3508de6db9705710c09aa767f` |
| `stage_bd_confirmation_unopened_receipt.json` | 804 | `572ed679157228f39bfba45cfd8a714aa9100365d3959810e7f170660077810c` |
| `stage_bd_shard_manifest.json` | 4,567 | `e21932139ef45a7459a40f58f0c67fec1458f880d3c1dc7559b9e1b29d96be1c` |
| `stage_bd_preinference_seal.json` | 5,844 | `0c4efb0d25012673834381df1ae566802af0f3785f1ee6df72f8d67a352c4a9a` |

## 10. Protected state

Unchanged by this round:

- `paper/evidence_ledger.csv` is byte-identical (25,241 bytes, SHA-256
  `3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1`) and still
  ends at EV-0016;
- both protected Phase 1.0D rollups remain
  `436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd` (152 files)
  and `ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a`
  (36 files), with zero differences;
- all Stage P and Stage T frozen bytes are unchanged; Stage T's sealed tokenizer
  outputs were revalidated without constructing a different tokenizer.

## 11. Branch metadata

Per the operator amendment, the local branch name and worktree path are
observational metadata and were never used as an admission gate. This round ran
on the platform-managed session branch
`alanjiao1988-microsoft-miniature-eureka`, and every commit was published to
remote `main` by explicit non-force fast-forward
(`git push origin HEAD:refs/heads/main`). Content identity — commit, tree, clean
state, ancestry, and protected bytes — was the only hard gate.
