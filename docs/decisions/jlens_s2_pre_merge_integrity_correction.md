# Pre-merge S2 artifact-integrity correction

## Decision

Before any cumulative lens merge or heldout application, strengthen the S2 and
E0 verification surfaces without changing any fitted scientific identity.

The correction adds:

- a dedicated closed runtime-pack schema and validator;
- runtime-manifest binding of receipts, lens bytes, source commit, image
  digest, protocol hash, stage, and create-only file identities;
- mandatory shard-bound checkpoint and checkpoint-manifest hashes for future
  resumes;
- exact heldout `(sequence_id, pair, layer)` Cartesian-key validation;
- independent production-attempt validation, including exact consumption of
  every failed partial checkpoint and an explicit `sequence_recomputed=false`
  gate;
- independent source/image provenance validation for shard, cumulative lens,
  convergence, heldout, and smoke receipts before S2 sealing;
- a closed final S2 artifact pack validated against
  `docs/jlens_s2_artifacts.schema.json`;
- recomputation of E0 schema, source-bundle, frozen S3, and vendored benchmark
  hashes during lock creation and again before E0 execution.

## Scientific identity unchanged

The correction does not change:

- corpus rows, roles, token IDs, role order, or shard membership;
- the successful production-fit image
  `sha256:403522b9a7a59b6db5d96fc211bdb3bdb80c6a9fcfa9d630541014c55587edc1`;
- model/tokenizer revision, parameter dtype, source layers, target layer,
  sequence length, skip rule, dim-batch, estimator, merge semantics, or
  checkpoint contents;
- any already successful or partial production shard byte;
- frozen S3 protocol/schema/Markdown/review/freeze/source-bundle bytes.

No production sequence is recomputed by this correction. The fitted shards
remain inputs; only later merge, analysis, and verification code uses the new
image.

## Trigger

A bounded read-only review after all production fit attempts found five
high-confidence integrity gaps: runtime manifest/schema mismatch, insufficient
resume provenance, incomplete heldout key validation, declarative E0 hashes,
and incomplete independent artifact provenance checks.

## Validation

Candidate commits `a316e8e`, `d9b0157`, and `c19e4d2` implement and test the
correction. ACR results:

- `cmb5`: two test-wiring defects, no runtime failure;
- `cmb6`: 13 targeted integrity tests passed;
- `cmb7`: 135 focused S2/E0/S3 and historical-provenance tests passed;
- `cmb8`: 3,482 passed / 15 skipped / exactly the two disclosed historical
  parser-seal failures;
- `cmb9`: 136 focused tests passed after production-attempt binding;
- `cmba`: 3,483 passed / 15 skipped / exactly the two disclosed historical
  parser-seal failures.

Relative to the 3,427 / 15 / 2 authority baseline, the exact current delta is
**+56 passed / +0 skipped / +0 failed**.
