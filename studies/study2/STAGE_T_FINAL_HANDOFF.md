# Study 2 Stage T — final handoff

State: `NONTERMINAL_CHECKPOINT_STUDY2_STAGE_T_TOKENIZER_GATE_SEALED_AWAITING_BD_AUTHORITY`

Stage T is complete, sealed, and published. This document is the entry point for
the next thread. It records what exists, what was verified, what is known to be
uncertain, and what the next authority must check before doing anything.

## 1. What Stage T established

The tokenizer gate passes cleanly for all three registered checkpoints.

| Quantity | Value |
| --- | ---: |
| Prompt rows per model | 17,408 |
| Prompt rows passing | 17,408 / 17,408 for each model |
| Unique prompts per model | 15,360 |
| Mechanistic pairs evaluated | 2,048 |
| Eligible per model | 2,048 |
| Jointly eligible across all three | 2,048 |
| Selection cells | 8 (2 roles × 2 families × depths 2, 3) |
| Selected per cell | 128 |
| Selected total | 1,024 (512 development + 512 confirmation) |
| Shortfalls | none |
| Tokenizer constructions | 3 |
| Weight loads, forward passes, generations, activations, probes, patches, lens ops, GPU jobs | 0 |
| Scientific evidence rows | 0 |

No prompt failure code and no eligibility rejection code fired even once.

**The principal finding.** The three checkpoints produce identical token IDs on
all 17,408 prompt rows — pairwise `input_ids_sha256` agreement on 17,408 of
17,408 rows, zero length mismatches, zero answer-position mismatches, and the
same four single-token option continuations (A=362, B=425, C=356, D=422).
Stage T was only required to prove exact alignment; it found token identity,
which is strictly stronger. Every later mechanistic comparison across these
checkpoints therefore runs on literally the same input token sequences.

The three tokenizers are nonetheless distinct artifacts — different `model_id`,
different resolved revisions (each equal to its pin), different `config.json`
bytes, and different special-token inventories (2 for the target, 14 for both
Qwen checkpoints). This was checked directly, because identical output is also
what a reused-tokenizer bug would produce.

## 2. Published artifacts

Committed under `studies/study2/stage_t/`. These are the exact bytes extracted
from the ACR-produced OCI images; nothing was regenerated locally.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `stage_t_core_manifest.json` | 149,948 | `6dec7650a05533efc5d88ba9ac1e3a498ca977a091a25b52155bbdb452622815` |
| `stage_t_identity_receipt.json` | 3,684 | `abe5113d4eeef2a47ffa047e34d7a7ce3e9274ef3f86e02b494bdd6d05a4dc40` |
| `stage_t_prompt_tokenization_target.jsonl` | 8,991,072 | `e865e3c41db585a48637f92f287edbeba93fc33d53c4fa7b2aa45c869c721eb0` |
| `stage_t_prompt_tokenization_lineage_base.jsonl` | 9,095,520 | `995f89aed40bbc7031ba2bfc099d1886adc32f6de2c0b97701b6cf322753f1c7` |
| `stage_t_prompt_tokenization_instruction_control.jsonl` | 9,217,376 | `79b0c313bc27bbc1a7c5261a13fb6602cf62b975dc7764af77e5485a986d2c79` |
| `stage_t_mechanistic_eligibility_target.jsonl` | 1,666,560 | `a6e217357880522592048ed26345671c43564a57724a6332f9f25bedc341c9e6` |
| `stage_t_mechanistic_eligibility_lineage_base.jsonl` | 1,666,560 | `a6e217357880522592048ed26345671c43564a57724a6332f9f25bedc341c9e6` |
| `stage_t_mechanistic_eligibility_instruction_control.jsonl` | 1,666,560 | `a6e217357880522592048ed26345671c43564a57724a6332f9f25bedc341c9e6` |
| `stage_t_pair_joint_eligibility.jsonl` | 941,200 | `d0a7607e629e8414bbadda020985948c4d97488e5047693852bc51a75822ac35` |
| `stage_t_selected_mechanistic_development.jsonl` | 4,006,216 | `439bea73b39cb5c1b4a7ded3496cbe471cd0188576b68569d93d695306d39722` |
| `stage_t_selected_mechanistic_confirmation.jsonl` | 4,053,320 | `82c02c46de1934e22e595721f66ec29457f68ee89f71326a93d7b527c2eac6b3` |
| `stage_t_selected_annotations.jsonl` | 519,092 | `44ebdaa1d0c06a3d385efe3f600829d301903215f8f7a4a1f1a4aaa5452f9f18` |
| `stage_t_jlens_digit_support.json` | 2,420 | `2bec6fb6464f8ec6284e3fbcf440efecf3035ca3ee60b19d4c07aab30e9f95e4` |
| `stage_t_attempt_receipt_t1a.json` | 3,496 | `1f88b24db3256458d49cf7487708fc33caa8216755ae3439d4f2123ce43ae880` |
| `stage_t_attempt_receipt_t1b.json` | 3,491 | `f8784b3f774624ccecf8a16f74b0a920ad82c30f823292a0c6106fe5ff2e1d23` |

The three eligibility files share a hash because the tokenizations are identical
and the eligibility row carries no model-role field. The three prompt files
differ *only* by the `model_role` label: at 17,408 rows the label lengths
predict the byte sizes exactly (8,991,072 + 17,408 × 6 = 9,095,520;
8,991,072 + 17,408 × 13 = 9,217,376). Neither fact indicates a defect, and both
have been verified numerically rather than assumed.

Registered as `AR-0140` through `AR-0160` in `paper/artifact_index.csv`.

## 3. Reproducibility

| Attempt | Run | `PYTHONHASHSEED` | Image digest |
| --- | --- | ---: | --- |
| `t1a` | `cmcs` | 20260808 | `sha256:86fa77b1aa515f6cc3a669e9948e6f7a7bf25ffd9f1d6d7a6e2cb66ac2044cf7` |
| `t1b` | `cmct` | 917 | `sha256:63e2f2b4f5503713a4eef3adca81eeb1a60b2aaddec6e6d536bf80cc7edd3710` |

Independently populated caches, different seeds, **13 of 13 byte-identical**
core artifacts. The two receipts differ only in `attempt_id`, `pythonhashseed`,
and `run_id`, and both bind the same `core_manifest_sha256`.

Determinism was also tested across a code change: the thirteen artifact hashes
from the earlier complete-but-unvalidated run `cmcq` were pre-registered in the
authority receipt as a falsifiable prediction before re-running, and all
thirteen reproduced exactly.

## 4. Execution and prohibited-operation control

Every executable step ran in Azure Container Registry, `linux/amd64`, over
`python:3.11-bookworm` (Python 3.11.15), with `transformers` 5.14.1,
`tokenizers` 0.22.2, `huggingface_hub` 1.26.0. The workstation performed only
text inspection, Git and SHA operations, ACR submission, and reading of results.

Weight loading is prevented, not merely observed. Before any acquisition the
runner replaces `PreTrainedModel.from_pretrained`, `PreTrainedModel.from_config`,
and every `AutoModel*.from_pretrained` with a stub that raises, and records the
patched targets in the attempt receipt; the validator rejects a receipt whose
interlock list is empty. After acquisition the cache is scanned for weight file
extensions: zero found, 30,083,882 bytes of tokenizer and config files only.

`torch` enters `sys.modules` transitively and `transformers.modeling_utils` and
`transformers.models.auto.modeling_auto` are imported when transformers resolves
its auto-class registry. Both are recorded as observations. Neither reads a
tensor. A build that treated the latter as fatal was corrected; see §5.

## 5. Corrections, and how to read them

Three seal revisions are recorded in `studies/study2/STAGE_T_AUTHORITY_RECEIPT.md`
§3.7 and §3.8. The generator `src/jspace_observation/study2_stage_t.py` is
byte-identical across all three, so no correction could alter which pairs were
selected.

1. **Revision 1 → 2**, before any measurement existed. A passive assertion that
   no weight-loading module had been imported was unsound, because transformers
   5.x resolves its auto-class registry eagerly. Replaced with the active
   interlock in §4, which is strictly stronger.
2. **Revision 2 → 3**, after a complete pack existed. The schema declared
   manifest `rows` as integer-only, but `write_json` reports `rows: null` for a
   single JSON document. The tests missed it because the synthetic manifest
   stubbed `rows: 1` everywhere. `rows` is now `["integer", "null"]` and a test
   now drives the real writers against the schema.
3. **A wrong argument, corrected in place.** An earlier draft of the receipt
   inferred tokenizer distinctness from the differing prompt-file sizes. Direct
   measurement showed those sizes differ only by the role label, so the argument
   was invalid even though the conclusion was true. It is corrected in §3.8
   with the evidence that actually supports the conclusion.

## 6. Starting-state amendment

The session ran on a platform-managed worktree branch, not `main`. Three
operator amendments progressively corrected the branch predicate, ending with
commit, tree, and protected-byte identity as the sole hard gate and branch and
worktree naming as observational metadata. The full content-identity preflight
passed and was recorded as
`STARTING_STATE_ACCEPTED_UNDER_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE`.
The complete audit, including all three amendment texts and the required
disclosure that the original prompt wrongly treated the branch label as
authoritative, is in
`studies/study2/prompts/stage_t_starting_state_operator_amendments.md`.

This was execution plumbing. No frozen Stage P byte, protocol, schema, bank,
threshold, seed, scientific selection, model registration, or tokenizer
registration was modified to accommodate it.

## 7. Invariants still holding

- `paper/evidence_ledger.csv` ends at `EV-0016`, 25,241 bytes, SHA-256
  `3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1`.
- Protected rollup v1: 152 files,
  `436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd`.
- Protected rollup v2: 36 files,
  `ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a`.
- All 16 Stage P frozen inputs match their registered blob hashes.
- Study 2 semantic review allowance remains unspent.

## 8. What the next thread must not assume

Stage T grants **no** authority for Gate A, Gate B–D, model weight download or
loading, forward passes, generation, activation extraction, probes, patching,
ablation, or J-lens operations. A separate operator authority is required.

Two things a Gate B–D author should weigh before designing anything:

- **Token identity is a double-edged result.** It makes cross-model comparison
  exact, but it also means the tokenizer contributes no differentiating signal
  whatsoever between the three checkpoints. Any observed difference downstream
  must originate in weights, not in input representation. That is a cleaner
  design than expected, and it removes a class of confound — but it also means
  a tokenizer-level explanation is unavailable for any effect that is found.
- **The 2,048 pairs were 100% eligible.** No pair was filtered on tokenizer
  grounds, so the selected 1,024 are a seed-determined sample of a fully
  eligible population rather than the survivors of a filter. Selection was by
  `ascending pair_semantic_id` within each cell, which is deterministic but not
  random; treat the development and confirmation splits accordingly.

## 9. Verification a successor should run first

```
git fetch origin
git rev-parse HEAD origin/main            # must agree
python scripts/phase1_0d_protected_bytes.py verify
python scripts/phase1_0d_rv2_protected_bytes.py verify
tail -1 paper/evidence_ledger.csv          # must be EV-0016
```

Then, in ACR only, `scripts/validate_study2_stage_t.py` re-checks the pack
against the closed schema, the manifest binding, and the attempt receipts
without constructing a tokenizer.
