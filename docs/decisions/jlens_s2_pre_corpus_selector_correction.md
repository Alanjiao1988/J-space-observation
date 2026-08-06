# Pre-corpus correction to the Phase 1.0D prompt selector

## Decision

Replace only the sealed Phase 1.0D review-form selector in
`docs/jlens_s2_corpus_source_contract.json`:

- frozen but incorrect: `prompt_text`, `prompt`;
- corrected from the committed producer/schema: `question`.

The symmetric raw-byte overlap rule, protected source object, source manifest
and review-form hashes, assignment seed, role-key bytes, role counts,
tokenization, model/J-lens identities, shard plan, measurements, gates, and
claim boundary are unchanged.

The corrected contract SHA-256 is
`d1eccb2eb35da65f5c3cbb98ee4b6fbbe58de434fc5e6d420981367071706775`.
The canonical S2 protocol remains byte-identical at SHA-256
`e542841890322f2407553714c65ad153e4dfbdba3cb51dad61542e122a5a29a2`.

## Why a correction is permitted before corpus selection

The first P1 execution,
`job-jspace-s2-corpus-18274d4e-2kbgf2l`, sealed the immutable WikiText source
resolution and license pack, then failed while reconstructing the protected
prompt bank because the review form exposed no field named `prompt_text` or
`prompt`. The failure occurred before:

- tokenizer construction or any corpus tokenization;
- dataset row scanning;
- any eligible row, role key, role assignment, smoke row, A/B row, or heldout
  row existed;
- any model, logit, loss, activation, Jacobian, lens, S3 behavior, or
  benchmark tokenizer operation.

The committed Phase 1.0D producer and tests independently establish that
`03_review_form.jsonl` has the exact closed fields `record_id`, `question`,
`registered_answer`, and `output_text`. The correction therefore repairs a
source-schema mismatch using pre-existing public bytes only. It cannot depend
on or respond to a corpus/model/lens/S3 outcome.

## Retained failed attempt

The failed Job, execution, immutable image
`sha256:50ee00228313e1661276aed6e290adcea034e7c28d2ab34090d53f6fe624eee1`,
and create-only partial prefix
`jlens-s2/corpus/20260806T172525Z` are retained. They are excluded from every
corpus role and every scientific or engineering statistic except operational
provenance. No object is overwritten or deleted.

## Validation

Correction commit `3c4199844143fe5755927886a693f9a2ad029d0a`, tree
`bc9d6914bad155a528da276f9cb0d3a751d0debf`, adds a synthetic exact-field
reconstruction test and updates the production extractor to consume the
selector list from the contract. ACR run `cmas` bound that commit/tree and
passed all 28 focused S2 corpus and protocol tests.
