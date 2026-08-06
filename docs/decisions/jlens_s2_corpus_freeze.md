# Full-layer S2 corpus freeze

## Decision

Seal the deterministic WikiText corpus at:

`jlens-s2/corpus/20260806T175724Z/final`

The registered state is:

`NONTERMINAL_CHECKPOINT_JLENS_S2_CORPUS_FROZEN_AWAITING_IMPLEMENTATION`

This is a corpus and provenance result only. It does not validate a lens,
open S3-E0, or change the independent Phase 1.0D capacity block.

## Immutable source and license

- dataset: `Salesforce/wikitext`;
- configuration: `wikitext-103-raw-v1`;
- split: `train`;
- immutable revision:
  `b08601e04326c79dfdd32d625aee71d232d685c3`;
- exact train rows scanned: 1,801,350;
- exact dataset-card bytes: 10,464 bytes, SHA-256
  `d5aabf145d341366745ac703b5844c442c143943b6c77929481395c822b1c28c`;
- license values: `cc-by-sa-3.0`, `gfdl`.

The two exact train Parquet objects are bound in
`data/jlens_s2_wikitext/source_resolution.json`. Source/license bytes were
uploaded create-only and read back before the tokenizer was constructed.

## Deterministic selection

The frozen seed is `jlens-s2-wikitext-roles-2026-08-06`. The scan used the
exact raw-byte symmetric overlap rule and inspected no model-dependent signal.

| Category | Count |
|---|---:|
| Registered A | 600 |
| Registered B | 600 |
| Registered heldout | 200 |
| Registered smoke-only | 2 |
| Eligible unique before role truncation | 378,511 |
| Short raw text | 1,390,878 |
| Protected prompt overlap | 18,561 |
| Under 128 tokens | 8,113 |
| Duplicate 128-token sequence | 5,287 |
| Eligible but unassigned after first 1,402 | 377,109 |

The exact 1,402-row file is 2,774,340 bytes with SHA-256
`63ed70ef0a7457f47a77a0d96855a2aeb605026c99a6708b6cf8d2f630b1445d`.
The exact 1,835-row protected prompt bank is 1,674,877 bytes with SHA-256
`1056a1458a4d2a911159a03229c957d4c46947b2ae0b91fd197f2bb5b4a7a9fc`.

The 289,526,517-byte detailed exclusion audit remains in create-only Blob at
the frozen prefix with SHA-256
`a4d50d946e50f4e911db012bdac9e0fb13a7e65aa3a6e035249118ac16d4f8dc`.
Its category counts and ordered-row rollups are committed.

## Execution and verification

The successful acquisition:

- Job `job-jspace-s2-corpus-4b0ea1c9`;
- execution `job-jspace-s2-corpus-4b0ea1c9-hcyl2wo`;
- immutable image
  `sha256:e13e97f723e8d84d98994cd24cb5953c34f35d26a5c7dea61df7b66d1d479937`;
- 2026-08-06 17:58:17Z through 18:14:11Z;
- one tokenizer construction, zero model/lens/benchmark-tokenizer operations.

The independent read-only verifier
`job-js-s2c-export-4b0ea1c9-lgdejpc` checked the complete ten-object set and
every manifest-bound byte count and SHA-256, then emitted nine repository
files in 1,494 hash-checked chunks. The final artifact manifest SHA-256 is
`a181a861c15f24d61192c750b79d79567d94d43acb69f802c2abab912a9bb460`.

## Retained failures

Two P1 attempts are preserved and excluded:

1. `job-jspace-s2-corpus-18274d4e-2kbgf2l` stopped after source/license seal
   and before tokenizer construction because the Phase 1 review-form selector
   named nonexistent fields.
2. `job-jspace-s2-corpus-b77f7df6-i1qcwwm` stopped after source/license and
   protected-bank seals and one tokenizer construction, before dataset scan,
   because Transformers 5.9 exposed no tokenizer `_commit_hash`.

Their Jobs, executions, immutable images, and partial create-only prefixes
remain retained. Neither produced a role assignment or final corpus manifest.

## Boundary

This freeze establishes exact public corpus identities, role separation,
license/provenance, and exclusion accounting. It establishes nothing about
model behavior, matrix convergence, J-lens validity, hidden reasoning, an
internal workspace, or a J-space.
