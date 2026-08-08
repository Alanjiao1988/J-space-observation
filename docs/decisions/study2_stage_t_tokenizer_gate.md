# Study 2 Stage T — tokenizer gate

Status: closed. Terminal state
`NONTERMINAL_CHECKPOINT_STUDY2_STAGE_T_TOKENIZER_GATE_SEALED_AWAITING_BD_AUTHORITY`.

Stage T resolves the pinned tokenizer identity of the three registered Study 2
checkpoints, proves the frozen Stage P prompt bytes tokenize with single-token
option continuations, verifies exact pair length and answer-position alignment,
and deterministically selects the mechanistic pairs that Gate B–D will later
use. It creates no scientific evidence. No model weight was downloaded, loaded,
or evaluated at any point.

## 1. What was decided

**The gate passes.** All three checkpoints tokenize every frozen prompt
successfully, the four option continuations are single tokens under all three,
every pair aligns exactly, and all eight selection cells filled to their full
quota. The selected 512 + 512 mechanistic pairs are sealed and available to a
future Gate B–D authority.

| Quantity | Value |
| --- | ---: |
| Prompt rows per model | 17,408 |
| Prompt rows passing the gate | 17,408 / 17,408 (all three models) |
| Unique prompts per model | 15,360 |
| Mechanistic pairs evaluated | 2,048 |
| Pairs eligible per model | 2,048 |
| Pairs jointly eligible across all three | 2,048 |
| Selection cells | 8 |
| Selected per cell | 128 |
| Selected total | 1,024 (512 development + 512 confirmation) |
| Cell shortfalls | none |
| Tokenizer constructions | 3 |
| Weight loads / forward passes / generations | 0 / 0 / 0 |
| Scientific evidence rows created | 0 |

No prompt failure code and no eligibility rejection code fired even once. This
is a clean pass, not a marginal one.

## 2. The principal finding: exact cross-model token identity

The three checkpoints do not merely agree on prompt *lengths*. They produce
**identical token IDs on all 17,408 prompt rows**. Pairwise comparison of
`input_ids_sha256` agrees on 17,408 of 17,408 rows for all three model pairs,
with zero `input_length` and zero `answer_position_index` mismatches, and the
option continuations resolve to the same four single tokens under every model
(A=362, B=425, C=356, D=422).

The consequence is that every downstream mechanistic comparison across these
three checkpoints operates on literally the same input token sequences. Length
alignment, which is all Stage T was required to establish, is subsumed by the
stronger property actually observed.

The mechanism is straightforward once the identity receipt is read: all three
load `Qwen2Tokenizer` over the same `qwen2` vocabulary and merge table, and the
frozen prompts are ordinary mathematical text using no chat template and no
special tokens. The distillation that produced the target checkpoint did not
disturb the base vocabulary.

### 2.1 Why identical output is not evidence of a reused tokenizer

Because this result would also be produced by the bug of loading one tokenizer
three times, it was checked directly rather than assumed. The three tokenizers
are distinct artifacts:

| Property | target | lineage_base | instruction_control |
| --- | --- | --- | --- |
| `model_id` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `Qwen/Qwen2.5-Math-1.5B` | `Qwen/Qwen2.5-Math-1.5B-Instruct` |
| `resolved_revision` | `ad9f0ae0…` | `4a83ca6e…` | `aafeb0fc…` |
| `config.json` bytes | 679 | 676 | 656 |
| special token IDs | 2 | 14 | 14 |

Every `resolved_revision` equals its pinned `requested_revision`. Had a single
tokenizer been reused, the special-token inventories and config hashes would
have coincided; they do not.

A related artifact of the pack invites the same misreading in the opposite
direction. The three `stage_t_prompt_tokenization_*.jsonl` files have different
sizes, which looks like evidence of differing tokenization but is not: they
differ **only** in the `model_role` label each row carries. At 17,408 rows, the
label lengths predict the sizes exactly — 8,991,072 for `target`, plus
17,408 × 6 = 9,095,520 for `lineage_base`, plus 17,408 × 13 = 9,217,376 for
`instruction_control` — matching the observed sizes to the byte. Conversely the
three eligibility files are byte-identical because the tokenizations are
identical and the eligibility row carries no model-role field.

An earlier draft of the authority receipt argued from the differing file sizes
that three distinct tokenizers had been applied. That inference was wrong, was
refuted by direct measurement of the published artifacts, and is corrected in
§3.8 of the receipt rather than silently removed.

## 3. Determinism

Two independent ACR runs at the same source commit, with different
`PYTHONHASHSEED` values (20,260,808 and 917) and independently populated
tokenizer caches, produced **13 of 13 byte-identical** core artifacts.

| Attempt | Run | Seed | Image digest |
| --- | --- | ---: | --- |
| `t1a` | `cmcs` | 20260808 | `sha256:86fa77b1aa515f6cc3a669e9948e6f7a7bf25ffd9f1d6d7a6e2cb66ac2044cf7` |
| `t1b` | `cmct` | 917 | `sha256:63e2f2b4f5503713a4eef3adca81eeb1a60b2aaddec6e6d536bf80cc7edd3710` |

The two attempt receipts differ only in `attempt_id`, `pythonhashseed`, and
`run_id`, and both bind the same `core_manifest_sha256`
`6dec7650a05533efc5d88ba9ac1e3a498ca977a091a25b52155bbdb452622815`.

Determinism was additionally tested across a *code* change. Section 5 describes
a validator defect fixed between the first complete run and these two. Because
the fix could not touch the generator, the thirteen artifact hashes from the
pre-fix run were pre-registered in the receipt as a falsifiable prediction
before re-running. All thirteen reproduced exactly.

## 4. Execution route and prohibited-operation control

Every executable step ran in Azure Container Registry on `linux/amd64` over
`python:3.11-bookworm`. The workstation performed only text inspection, Git and
SHA operations, ACR submission, and reading of ACR results.

Weight loading was prevented rather than merely observed. Before any tokenizer
acquisition the runner replaces `PreTrainedModel.from_pretrained`,
`PreTrainedModel.from_config`, and every `AutoModel*.from_pretrained` with a
stub that raises, and records the patched targets in the attempt receipt. The
validator rejects any receipt whose interlock list is empty. After acquisition
the cache is scanned for weight file extensions; zero were found, and the cache
totalled 30,083,882 bytes of tokenizer and config files only.

`torch` does enter `sys.modules` transitively, and
`transformers.modeling_utils` and `transformers.models.auto.modeling_auto` are
imported when `transformers` 5.14.1 resolves its auto-class registry. Both facts
are recorded in the receipt as observations. Neither reads a tensor; §5 explains
why an earlier build treated the second as fatal.

## 5. Corrections made during execution

Three seal revisions were recorded. None altered a scientific rule, and the
generator `src/jspace_observation/study2_stage_t.py` is byte-identical across
all three.

**Revision 1 → 2** (before any measurement existed). Run `cmck` acquired all
three tokenizers and then aborted because the build treated the mere *import* of
`transformers.models.auto.modeling_auto` as proof that a weight path had been
entered. Transformers 5.x resolves its auto-class registry eagerly, so that
module appears without any tensor being read; the check was wrong about its own
evidence. It was replaced with the active interlock described in §4, which is
strictly stronger. The run had produced no manifest, table, or selection.

**Revision 2 → 3** (after a complete pack existed). Run `cmcq` ran the gate to
completion and was then rejected by the post-gate validator with
`type mismatch at $/files/stage_t_identity_receipt.json/rows: expected
['integer']`. The defect was in the contract, not the data: `write_jsonl`
reports an integer row count while `write_json` reports `rows: null`, since a
single JSON document has no rows, and the generated `file_entry` definition had
declared `rows` integer-only. The seal-revision-2 tests missed it because the
synthetic manifest stubbed `rows: 1` for every file — a shape the real writers
never produce. `rows` is now `["integer", "null"]`, the synthetic manifest
mirrors the writer convention, and a new test drives the real writers and
validates their output against the schema so the two cannot drift again.

Because revision 3 was made after an outcome had been observed, it is recorded
under stricter treatment: the generator never reads the schema, only the
validator and tests do, and the pre-registered hash prediction described in §3
converted the argument into a test that passed 13/13.

## 6. Starting-state amendment

The session ran on a platform-managed worktree branch rather than `main`. Three
operator amendments progressively corrected the starting-branch predicate,
ending with commit, tree, and protected-byte identity as the sole hard gate and
branch naming as observational metadata. The complete content-identity preflight
passed and was recorded as
`STARTING_STATE_ACCEPTED_UNDER_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE`.
This is execution plumbing, not a protocol change; the full audit is in
`studies/study2/prompts/stage_t_starting_state_operator_amendments.md`.

## 7. What Stage T does not authorize

Stage T grants no authority for Gate A, Gate B–D, model weight download or
loading, forward passes, generation, activation extraction, probes, patching,
ablation, or J-lens operations. `paper/evidence_ledger.csv` remains at EV-0016
and no evidence row was created. Both protected Phase 1.0D rollups are
unchanged.
