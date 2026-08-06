# Full-layer S2 implementation and image freeze

## Decision

Freeze the tested S2 runtime before the first all-layer GPU smoke. The next
state is:

`NONTERMINAL_CHECKPOINT_JLENS_S2_IMPLEMENTATION_FROZEN_AWAITING_SMOKE`

The immutable image is:

`acrjspaceobssea0708231738.azurecr.io/j-space-observation-jlens-s2@sha256:403522b9a7a59b6db5d96fc211bdb3bdb80c6a9fcfa9d630541014c55587edc1`

Its tag and manifest have write and delete disabled. The image extends the
already retained pinned J-lens image, embeds the exact 1,402-row corpus, and
bakes a nine-file, 3,562,046,103-byte model snapshot whose manifest SHA-256 is
`1cdefe845504be7b6051b7b5dde4c56ae54cc7b8dbbb4ebe4c44e7bc89cdcb51`.

## Frozen implementation

The runtime fixes:

- exact runtime re-tokenization against every registered 128-token sequence;
- source layers 0-26 and target layer 27 in one retained-graph official call;
- fresh-process smoke candidates 1, 2, 4, and 8 with two smoke-only rows;
- deterministic descending dim-batch selection against the dim-batch-1
  reference and the frozen numerical/memory limits;
- exact A/B role slicing, upstream checkpoint/resume, create-only checkpoint
  mirroring every eight completed prompts, and exactly-once successful
  accounting;
- official cumulative merge plus independent float32 weighted recomputation;
- lossless float32 serialization and exact save/load identity;
- per-layer convergence, free-exponent scaling, and the non-gating `C=1.7`
  prior diagnostic;
- all-200 heldout pairwise logit, top-10, top-50, and full-vocabulary rank
  diagnostics;
- independent canonical-lens verification and A600/B600/M1200 seals;
- a distinct lens-free E0 implementation, create-only lock, exact 238 item
  tokenizations/forward passes, frozen surface rules, distribution-local
  split, four floors, no backfill, and zero E1/E2 output.

The 20-file S2 production source bundle is 4,676,769 bytes with SHA-256
`87c8b38013485c84f03f573c5deeb7e1ccd61b2ce7eaab4108085c38262da2f4`.
Complete component hashes are in `docs/jlens_s2_image_provenance.json`.

## Tests

All tests ran in ACR:

- `cmax` found one tiny synthetic shape assumption in the independent weighted
  mean helper; no model, tokenizer, GPU, or corpus signal was involved.
- corrective commit `b85e6e2` made the helper shape-generic while the
  production matrix gate remained exactly 1536 by 1536.
- `cmay` passed all 106 S2/S3 focused controls.
- full run `cmb0` exposed one new historical-image integration expectation:
  the frozen Phase 1.0D verifier correctly rejected the newly authorized S2
  modules.
- commit `06e1604` changed only the non-protected historical integration test;
  it still rebuilds and verifies every old recorded byte and requires the
  unchanged old verifier to fail closed for exactly the five later J-lens/S2
  modules plus bundle digest drift.
- `cmb1` passed 144 focused S2, E0, S3, protected-byte, and historical-image
  integration tests.
- `cmb2` completed the full suite at 3,478 passed / 15 skipped / exactly the
  two disclosed historical parser-seal failures.

Relative to the authority baseline 3,427 passed / 15 skipped / 2 failed, the
exact delta is **+51 passed / +0 skipped / +0 failed**.

No target tokenizer, target model, GPU, Jacobian, lens, official benchmark
tokenization, or benchmark model operation occurred during I0.
