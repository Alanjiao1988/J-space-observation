# Phase 1 all-45 semantic review protocol

## Registration

- Protocol version: **v1**
- Status: **frozen before any all-45 packet review**
- Experimental target: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
- Review model: `gpt-5.6-sol`, reasoning effort `max`, engineering audit only
- Writer commit: `359643b7b5eb8f95c13cca2e60fa753df8701282`
- Frozen deterministic shuffle seed: `20260711`; every other value is invalid

This preregisters a read-only audit of the 45 already-stored arithmetic records across three depths and five registered conditions. It does not authorize inference, parser changes, threshold changes, branch changes, source mutation, or historical metric/classification replacement.

## Scientific boundary

The all-45 semantic audit is a read-only, post hoc review of already-stored outputs from deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B. Reviewing 45 records adds no behavioral observations, does not make behavioral n=45, and leaves every experimental cell at n=3, the registered minimum only—not evidence of stability, robustness, reliability, or generalizability. Evaluator consistency establishes reproducibility of stored parser/metric/classification logic, not semantic correctness. Judgments, agreement, and arbitration by reviewer gpt-5.6-sol with reasoning effort max are audit opinion, not human ground truth. Official stored metrics/classifications remain unchanged. Reviewer-derived quantities are labeled audit-only semantic alternative estimates: post hoc, noncanonical sensitivity estimates, never corrected, replacement, true, or official metrics. stopped_intervention remains intervention-controlled, not spontaneous no-CoT. postprocessed_utility remains answer-recovery utility, not raw no-CoT. Parser or answer-extraction disagreement is a surface-measurement issue and provides no evidence of hidden reasoning, internal workspace, invisible CoT, genuine no-CoT, or J-space.

## Frozen protocol provenance

The image build context must first be prepared with:

```bash
env -u PYTHONPATH python -I -S scripts/prepare_semantic_audit_build_context.py \
  --project-root . \
  --protocol-commit <explicit-nonzero-lowercase-40-hex-clean-HEAD>
```

The helper refuses non-isolated startup and must run with `python -I -S`, with
`PYTHONPATH` removed before Python starts. The command requires the commit to
exist and equal `HEAD`, a clean tracked worktree and index, the exact frozen
behavior-file list, and no untracked or ignored files in `src/`, `scripts/`, or
the other registered behavior roots. Each working file is compared with its Git
blob after applying the registered clean filter, so a clean Windows checkout is
not rejected solely because of line-ending conversion. Ignored files outside
those roots, including `artifacts/`, do not affect the check. It writes canonical
`.semantic_audit_build_provenance.json` with the schema, commit, canonical bundle
SHA-256, exact ordered file list, every file SHA-256, and
`generated_from_clean_git=true`.

The canonical bundle hashes domain `jspace-semantic-audit/protocol-bundle/v1\0`, then each frozen relative path, path length, byte length, and exact file bytes in `PROTOCOL_RUNTIME_FILES` order. The generated file is Git-ignored but explicitly admitted to the Docker context. `Dockerfile` requires it, validates it with stdlib code after copying the complete runtime, and installs it read-only at `/opt/jspace/semantic-audit-build-provenance.json`. The image then makes `/workspace` and `/opt/jspace` root-owned and non-writable and runs as the fixed unprivileged `jspace` user; only registered cache/result/test temporary paths are writable. There are no commit or bundle Docker build arguments and no runtime bundle-digest assertion supplied by a caller.

Each production CLI rejects nonempty `PYTHONPATH` and requires `python -I -S`, then verifies that every bootstrap stdlib module resolves from the interpreter's resolved `sysconfig` stdlib roots before any project or Azure import. It uses only that verified stdlib to check local clean Git or the fixed baked attestation, including its own script. Azure imports are restricted to the exact resolved interpreter `purelib`/`platlib` roots, with symlink resolution, and must be outside the project, current directory, script directory, and `src`; a path component merely named `site-packages` confers no trust. Only after provenance and Azure-origin verification does the exporter prepend the already-attested project `src`; the finalizer follows the same order. Every loaded `jspace_observation` module must resolve under the attested `src` root and to a bundled file. In an image, `JSPACE_SEMANTIC_PROTOCOL_COMMIT` is only an optional expected-commit check and must equal the baked commit; it cannot replace or override the attestation.

## Source gate

Before constructing any packet, tooling must:

1. download in memory only the exact generation and evaluation Blob names using `ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)`;
2. compute and require generation SHA-256 `b45c972af6f8a2be771e308d943ff793bdafd44c486a4eae9ea8a4e7f1ec11a0` and evaluation SHA-256 `57aee97ef98a9be14e489bf6aa4a6e09a80fd5ceedb2df8fadc8d991be98538b`;
3. require type-valid before/after/final Blob properties that remain unchanged;
4. require exact generation/evaluation pairing, exact 45-record membership, common-field equality, and selected-output transformation consistency;
5. reconstruct every question and reference from the writer-commit-pinned arithmetic registry rather than using stored ground truth as a release reference;
6. reconstruct and verify each full condition-specific generation prompt;
7. fail before writing, printing, or uploading if any gate fails.

Production construction has only `source_evidence_mode=verified_source_bytes`; it requires the actual two byte strings and an exporter-minted private evidence capability created during live Blob download/property checks, and recomputes both hard-coded hashes. Public builders do not accept caller-created snapshot mappings. No CLI option or JSON input can inject evidence. Every review/release manifest binds the internally derived canonical evidence document with `source_evidence_sha256`. Missing evidence, caller-attested hashes/immutability, and the private `_for_tests` `synthetic_test_only` path can never produce or validate a production release.

Source and release prefixes are normalized and disjoint in both directions. Stage-1, Stage-2, and private output directories/prefixes are pairwise disjoint. Before any other Blob upload, the exporter atomically creates the registered immutable reservation with `overwrite=False` and holds a lease when supported. It uploads the packet, verifies exact prefix membership, uploads the manifest last, then re-lists exact membership and re-downloads/hashes every file. Missing or extra members make the release unusable even if a manifest exists; partial outputs are not deleted. The reservation remains as an immutable no-reuse marker. Local releases contain the same registered reservation and use exclusive creation. A prefix without a valid manifest is incomplete.

## Deterministic identifiers

The canonical compact sorted-key ASCII JSON pairing key is hashed with domain `jspace-semantic-audit/shuffle/v1\0` and seed `20260711`. Sorting by `(hash,key_json)` assigns the exact IDs `R001` through `R045`. Input permutation cannot change the mapping. CLI, builder, release validator, and finalizer reject any other seed. All seeds, expected/actual counts, `record_count` values, and integer manifest/seal bindings require `type(value) is int`; booleans and integral floats are invalid.

## Enforceable two-stage state machine

### State 0 → Stage 1 released

The Stage-1 command writes or uploads exactly:

1. `.semantic_audit_release_reservation.json`;
2. `all45_review_packet_blinded.jsonl`;
3. `all45_stage1_release_manifest.json`, last.

It never writes, uploads, or prints the Stage-2 packet or restricted packet. The blinded packet is printed only with the explicit Stage-1 print option, preventing model outputs from entering job logs by default. Stage 1 contains the full target ID, task metadata, standalone question, parse type, output variants, selected `eval_output`, intervention metadata, and available generation configuration. Exact schema versions, scalar/container types, selected-output equality, and nested allowlists are enforced. It contains no reference, stored parser/correctness field, branch aggregate, mechanical decision, or prior review. A recursive forbidden-field scan, including camelCase normalization, is mandatory.

### Stage 1 released → two Stage-1 submissions sealed

Reviewer A and B use distinct files and distinct `reviewer_id` values. Every one of the exact 45 rows contains:

- `schema_version`, `review_stage=stage1`, `review_id`;
- `reviewer_id`, `reviewer_model_id=gpt-5.6-sol`, `reviewer_reasoning_effort=max`;
- exact Stage-1 `packet_sha256`;
- `stage1_answer_presence`, `semantic_ambiguity_category`, `best_answer_if_any`;
- `issue_tags`, `confidence`, and `notes`.

No binding is synthesized from CLI values. A canonical seal manifest binds reviewer identity, stage, submission schema, packet hash, exact IDs/count, and submission SHA-256.

### Two Stage-1 seals → Stage 2 released

Stage 2 cannot be released until the exact three Stage-1 release artifacts—reservation, packet, and canonical manifest bytes, with no extras—and both complete, valid, distinct Stage-1 submissions are re-read and fully validated. The Stage-1 packet must byte-match the source reconstruction; its manifest, reservation, all-45 count/IDs, target, seed, evidence, and provenance are validated before the release-manifest hash is derived internally. A caller-supplied syntactic hash cannot advance the state. Exact canonical submission and seal bytes are fully passed through `validate_sealed_submission`; caller-constructed sealed objects are not accepted. Validation requires exact 45 rows and IDs, canonical submission hash, seal schema/state/hash, packet hash, reviewer identity/model/effort, and two distinct reviewer identities. The Stage-2 gate binds both the derived Stage-1 packet hash and derived Stage-1 release-manifest hash. Private integration applies the same exact-byte validation to the complete Stage-2 release before accepting Stage-2 seals. The Stage-2 command writes or uploads exactly:

1. `.semantic_audit_release_reservation.json`;
2. `all45_review_packet_stage2.jsonl`;
3. `all45_stage2_release_manifest.json`, last.

The Stage-2 packet contains only schema, review ID, full target ID, and registered reference answer. It is printed only with the explicit Stage-2 print option. The release manifest records the two Stage-1 seal bindings. No restricted packet is released.

### Stage 2 released → two Stage-2 submissions sealed

Each Stage-2 row contains only the mandatory binding fields, `answer_status`, and `notes`. It uses `review_stage=stage2`, the Stage-2 schema, and the exact Stage-2 packet hash. The reviewer identity must equal the corresponding Stage-1 identity. Stage-1 presence, category, best answer, issue tags, and confidence cannot be restated or revised.

### Two Stage-2 seals → private integration

Restricted construction is prohibited until both Stage-2 submission and seal byte pairs are revalidated again at the private-integration boundary against their corresponding Stage-1 bytes and the exact Stage-2 packet. The restricted representation is built only inside the finalizer from reverified private sources. It is never placed in a reviewer directory/prefix, release plan, or default stdout.

`prepare-arbitration` creates only the blinded arbitration packet and a manifest-last preparation marker in a new directory. `finalize` requires a new/empty output directory. If triggered arbitration is missing, `finalize` emits explicit `incomplete_awaiting_arbitration`, returns nonzero, and writes no final outputs. The final manifest-last marker binds the SHA-256 of every other final output. The arbiter has a third distinct identity, the exact arbitration schema/stage/hash binding, and exactly the triggered IDs.

## Judgment rubric

The judgment target is only the selected `eval_output`; auxiliary raw/stopped/postprocessed output is context.

Semantic category is exactly one of `unambiguous_single_answer`, `true_multiple_candidate_ambiguity`, `no_answer`, `incomplete_or_truncated`, `malformed_but_answer_recoverable`, `malformed_no_reliable_answer`, or `review_inconclusive`. Only `true_multiple_candidate_ambiguity` is ambiguity-positive. No-answer, truncation, and malformed output are not automatically ambiguous.

Stage-1 presence is `answer_present`, `ambiguous`, `no_answer`, or `inconclusive`. Stage-2 status is `correct`, `incorrect`, `ambiguous`, `no_answer`, or `inconclusive`. `incomplete_or_truncated` is conclusive only with a valid conclusive presence/status state; any inconclusive field remains unresolved.

Best answer is one finite numeric literal normalized with `Decimal`, without calculation, repair, tolerance, or commas. The issue vocabulary remains the frozen 14-tag list in the implementation. `last_number_selection_risk` is prospective risk, not automatically an observed extraction or material error. Confidence is `low`, `medium`, or `high`.

## Agreement, arbitration, and unresolved results

Agreement reports exact category, presence, status, normalized best answer, issue set/Jaccard, and confidence/ordinal distance. Nominal and weighted kappa are JSON `null`/`NA` for `N=0`, constant marginals, or zero denominators.

Arbitration triggers on category, presence, best answer, status, issue-set disagreement, high-versus-low confidence, agreed inconclusive, or a private stored-correctness-relation difference. The arbitration packet contains the original staged packets, both combined judgments, and the frozen rubric—never stored evaluator fields.

Any inconclusive presence, `review_inconclusive` category, inconclusive status, missing/invalid final field, or unresolved arbitration is unresolved. One unresolved record makes all overall and condition/branch/depth ambiguity rates unavailable; counts and unresolved strata remain. No-answer, truncation, and malformed categories are not ambiguity positives.

## Comparisons and material impact

Correctness tables retain all semantic statuses against stored `true`, `false`, `null`, `missing`, and `invalid` states. Reports separately count and break down by condition, Phase-1 branch, and depth:

1. `last_number_selection_risk` tags;
2. observed extraction errors derived from semantic-versus-stored parsed-answer disposition;
3. material correctness errors;
4. overall material evaluator errors.

Risk is never promoted automatically to observed or material error. Audit-only alternatives are computed on private copies only after zero unresolved judgments, reuse historical pure metric/classification helpers, preserve raw/stopped/postprocessed distinctions, and are labeled **audit-only semantic alternative estimates: post hoc, noncanonical sensitivity estimates**. Official stored history remains unchanged.
