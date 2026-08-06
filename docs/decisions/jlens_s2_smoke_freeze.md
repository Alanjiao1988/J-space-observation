# Full-layer S2 smoke and production configuration freeze

## Decision

Select `dim_batch=1` for every production S2 fit and freeze the final
344-sequence increment as:

`59, 59, 59, 59, 59, 49`

The state is:

`NONTERMINAL_CHECKPOINT_JLENS_S2_SMOKE_SEALED_AWAITING_PRODUCTION_FITS`

## Exact smoke

Four independent T4 Jobs used the same two smoke-only rows, source layers
0-26, target layer 27, 128 tokens, `skip_first=16`, float16 model parameters,
and the immutable S2 image
`sha256:403522b9a7a59b6db5d96fc211bdb3bdb80c6a9fcfa9d630541014c55587edc1`.

| dim_batch | seconds/prompt | peak reserved ratio | max abs vs 1 | max rel. Frobenius vs 1 | min cosine | Result |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 74.0679 | 0.2491 | 0 | 0 | 1.000089 | pass/reference |
| 2 | 39.3051 | 0.2613 | 0.007557 | 0.005107 | 1.000084 | fail numerical limits |
| 4 | 35.4020 | 0.3127 | 0.006994 | 0.005207 | 1.000084 | fail numerical limits |
| 8 | 32.9281 | 0.3977 | 0.008046 | 0.005141 | 1.000082 | fail numerical limits |

Every attempt returned all 27 finite float32 matrices with exact 1536 by 1536
shape and stayed below the 92% memory ceiling. Candidates 2/4/8 were faster
but failed both frozen 1e-5 numerical equivalence limits. They cannot be used
for production. Cosines slightly above one are disclosed raw floating-point
dot/norm results and do not override either failed distance gate.

## Planner

Using the selected worst observed 74.067897819 seconds per prompt, 7,200-second
container timeout, 900-second export reserve, and 0.70 safety factor gives a
4,410-second fit budget and maximum final-increment subshard size 59. The
fixed 64/64/128 checkpoint increments remain unchanged; only the final 344 is
operationally split.

## Artifacts and operations

The selected configuration is 121,097 bytes with SHA-256
`44720471570b63bff6eda6f8c4df56c5703adf5c22803d4968eb1a401df02440`.
A separate read-only Job verified all 13 manifest-listed smoke objects. Exact
attempt and manifest bytes are committed under
`artifacts/jlens-s2-smoke/20260806T191855Z`.

The round performed four target model loads, four target tokenizer loads, and
eight official all-layer `jacobian_for_prompt` calls. It performed zero
official S3 benchmark tokenizer/model operations, zero Phase 1.0D operations,
zero production A/B fits, and zero lens applications.

The smoke rows remain excluded from A, B, heldout diagnostics, S3, and paper
statistics other than this runtime/memory compatibility record.
