# Full-layer S2 WikiText corpus

This directory contains the exact 1,402 public sequences registered for the
full-layer S2 fit:

- 600 arm A sequences;
- 600 disjoint arm B sequences;
- 200 heldout engineering-diagnostic sequences;
- 2 smoke-only sequences.

`corpus_rows.jsonl` retains the exact source text, first 128 adapter-supplied
token IDs, untruncated token count, immutable source row identity, raw-text
and token-ID hashes, role key, role, and role index. The source is
`Salesforce/wikitext`, `wikitext-103-raw-v1`, train split, immutable revision
`b08601e04326c79dfdd32d625aee71d232d685c3`.

`protected_prompt_bank.jsonl` records the exact public Phase 1, parser,
prior-J-lens, RQ2-predecessor, and official S3 prompt bytes used by the frozen
symmetric overlap exclusion. `exclusion_audit_summary.json` records exact
counts and ordered-row rollups for all 1,799,948 excluded or unassigned rows.
The 289,526,517-byte detailed audit is retained create-only at:

`jspace-results/jlens-s2/corpus/20260806T175724Z/final/exclusion_audit.jsonl`

Its SHA-256 is
`a4d50d946e50f4e911db012bdac9e0fb13a7e65aa3a6e035249118ac16d4f8dc`.

The dataset-card bytes and directory-specific licensing notice are
`upstream_README.md` and `LICENSE.md`. WikiText-derived text in this directory
remains under the upstream `cc-by-sa-3.0` and `gfdl` terms and is not
relicensed under the repository's code license.

The complete small-file identities and large-audit retrieval coordinate are
in `artifact_manifest.json` and `corpus_manifest.json`.
