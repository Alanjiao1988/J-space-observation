# Full-layer S2 protocol and S3-E0 execution-schema freeze

## Decision

The full-layer S2 protocol, corpus-source contract, create-only artifact
schema, and frozen S3-E0 pack schema are sealed before corpus acquisition or
any tokenizer/model/J-lens operation. The successful state is:

`NONTERMINAL_CHECKPOINT_JLENS_S2_PROTOCOL_FROZEN_AWAITING_CORPUS_FREEZE`

This decision does not execute or validate a lens, does not open S3-E0, and
does not change the independent Phase 1.0D state
`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`.

## Starting-state gate

The independently verified starting commit was
`72336f822a8ffdbd2e0caf40f4a62c68cce68156`, tree
`d0592ae0b0edb62b4f082c0a12a9bcafe5693ee5`. The complete receipt is
`docs/jlens_s2_starting_state_receipt.json`, SHA-256
`fa88b9ac5a6fcc25562b8d5667a67dd778916f8487abd202e9ba53102c99cec4`.
It records:

- both Phase 1.0D protected-byte rollups with zero differences;
- the restored `.dockerignore` SHA-256
  `c965ea6e67cb9d473aa76d57913f8976b4d7b38b59fa2bedb64dcab06df163c2`;
- exact frozen S3, recovery-authority, and capacity-pack hashes;
- the validator source-bundle SHA-256
  `7e837b0cfdb0c9a12eb1b6c9067751c7cd4262cc18c5a6f17f4a6505f25b7410`;
- append-only D25-D30 decision-log prefix SHA-256
  `e37299087788738009ad0264597c161fac536982869367916dc228cd744b3108`;
- the pre-round evidence-ledger tail `EV-0014` and prefix SHA-256
  `16121192cf4ca0ee507a310356b0d9bb6cc7770323fa650867d8a4c65bb1bb85`.

## Frozen package

Hashes are over exact committed Git blob bytes at candidate commit
`72356dba0aa02a10797a3ac8489e9a21c6be36c2`, tree
`1a0d98967dc74fdf14c55c6fbcef3756a2947364`.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `docs/jlens_s2_protocol.json` | 11,306 | `e542841890322f2407553714c65ad153e4dfbdba3cb51dad61542e122a5a29a2` |
| `docs/jlens_s2_protocol.schema.json` | 24,171 | `947eac1bf710277a0884c3c2783841ffd21c5eeef7cbf247aec13b87cc3f2a80` |
| `docs/jlens_s2_corpus_source_contract.json` | 5,678 | `bde80360e5f0dda1701ebc41341bdc777416efcae43a4764493180e185008e6d` |
| `docs/jlens_s2_artifacts.schema.json` | 13,727 | `36a5a5df70d859bfabc808ffb926bf61bc1738106650a58b9e62951966b3a2da` |
| `docs/jlens_s3_e0_pack.schema.json` | 12,467 | `9fdb9a45b78bae98ab72e1ffb9eb5b757de889e27b05f799e175f67a82dfbb7c` |
| `scripts/validate_jlens_s2_protocol.py` | 2,404 | `d08caff74b6b9269ca543b4f76ebad44f1d0f7c2588cc80cb01cf5152f4c13a6` |
| `src/jspace_observation/jlens_s2_protocol.py` | 47,707 | `12c2e9261f9dd03a54ddfd3e8a9af05b824ddd02eebf507206f903e613fc0bad` |
| `tests/test_jlens_s2_protocol.py` | 14,462 | `6b0b0575fe82592a57d6b4982c50bd001be8f274949a24e5b6110341230d6f91` |

The source-bundle byte format is:

1. ASCII `jlens-s2-protocol-source-bundle-v1` followed by LF.
2. For each of the script, module, and test paths above in UTF-8
   lexicographic order: UTF-8 path, NUL, ASCII decimal blob length, NUL, and
   exact raw Git blob bytes.

The resulting 64,739-byte source bundle has SHA-256
`3b1ef1ee1f3ddc9b7128ef34edc3afae2fcba315bfe986bf8fcc69c7f5f3d5a5`.

## Frozen choices

The package fixes:

- model revision, float16 parameters, eval mode, `use_cache=false`, and
  `trust_remote_code=false`;
- pinned upstream J-lens commit, `force_bos=true`, and `compile=false`;
- source layers 0-26, target layer 27, 128 token IDs, and `skip_first=16`;
- the literal corpus assignment seed, exact role-key bytes, 600/600/200/2
  role counts, and one raw-byte symmetric overlap rule;
- dim-batch candidates 8/4/2/1, a dim-batch-1 reference, numerical
  equivalence limits, and a 92% peak-reserved-memory ceiling;
- cumulative checkpoints 64/128/256/600 and the deterministic final-increment
  planner with a 7,200-second timeout, 900-second export reserve, and 0.70
  safety factor;
- lossless float32 identities, official merge plus independent weighted
  recomputation, per-layer diagnostics, a free-exponent scaling fit, and the
  non-gating `C=1.7` prior diagnostic;
- all-200-sequence heldout engineering diagnostics;
- create-only, manifest-last artifact schemas and the exact E0 row schemas
  inherited from frozen S3;
- zero E0 lens operations, exact pre-lock zeros, frozen floor branches, and no
  E1/E2 output.

## ACR validation and retained failures

All validation used ACR QuickRuns; no local test, build, import-as-test,
dataset scan, tokenizer load, model load, or J-lens operation occurred.

- `cmaa` failed before repository validation because an absolute Windows task
  path was interpreted below `/workspace`.
- `cmab` bound candidate `3fecdea` and found two model-free test defects:
  noncanonical corpus-contract key order and an overbroad string import check
  that matched `jlens_s3_protocol`.
- `cmac` was a bounded ACR-only byte diagnostic that identified the first
  canonical-order difference. It performed no tokenizer/model/lens operation.
- corrective commit `72356db` changed only the corpus-contract key order and
  import-guard implementation.
- `cmad` bound `72356db` / tree `1a0d9896` and passed all 17 new S2 tests.
- `cmae` independently reproduced every package hash and every frozen
  starting-state anchor.
- `cmaf` bound the same commit/tree and passed 113 focused S2, frozen S3, and
  Phase 1.0D protected-byte tests.

No corpus row was scanned, no Hugging Face revision or license was resolved,
and no target tokenizer, target model, GPU, Jacobian, lens, benchmark
tokenization, or benchmark forward pass occurred in P0.
