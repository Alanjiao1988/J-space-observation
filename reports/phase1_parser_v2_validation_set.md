# Phase 1.2A Parser-v2 Evaluator Validation Set

## Outcome

Phase 1.2A is complete at the `SEALED` holdout state.

- Selected path: preregistered Path C.
- Historical experimental target:
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`.
- Open development set: 60 cases.
- Private locked set: 120 cases.
- Registered strata: 12.
- Private release artifacts: 26.
- Unresolved labels: 0.
- Parser v2 implemented: no.
- Locked parser evaluation performed: no.
- Target-model download, load, or inference: no.
- Higher-n behavioral run: no.
- GPU use: no.

This is an evaluator-fixture construction, operational labeling, validation, and
sealing result. It is not a parser-v2 result and creates no new target-model
evidence.

## Frozen protocol and provenance

| Item | Value |
|---|---|
| Starting commit | `58d299bb66c5536a0f1b7d0617204472fbb8c212` |
| Initial protocol commit | `e8aa3bcef745b6c5845418dfc353788e55ee739d` |
| Numeric-bound amendment | `a69b232c6df61953eee97a11310287b1a41465a8` |
| Final protocol commit | `cc93ffe603ab8338ed860586a52b1911af4b3277` |
| Tooling/development commit | `e7a95a458d05d4ef211bb6902c2a20cb5f16bf60` |
| Production-ingress hardening | `297420abfebb65c9f3702c56f28fe5a193913cd0` |
| Sealed no-Git validation | `9b4262a9d35e6342935b8d2f72887a56c5f98486` |
| Protocol bundle SHA-256 | `5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666` |
| Acceptance-gate SHA-256 | `a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988` |

The final protocol was pushed before eligible case construction. Candidate
material created before protocol amendments was discarded. The acceptance
gates were frozen before construction and have not been evaluated.

The frozen one-shot rule requires the future parser implementation commit to be
fixed before any locked input is read. Predictions must be sealed before labels
are read. The first formal result is retained whether PASS or FAIL, and either
outcome retires the holdout. A modified parser requires a new independent
holdout.

## Dataset composition

| Property | Development | Locked |
|---|---:|---:|
| Total | 60 | 120 |
| Cases per S01-S12 stratum | 5 | 10 |
| Present | 40 | 80 |
| Ambiguous | 5 | 10 |
| No answer | 15 | 30 |
| Curator A | 30 | 60 |
| Curator B | 30 | 60 |

The locked set contains 80 critical cases, 40 operationally correct cases, 80
operationally incorrect cases, and 68 cases registered as material if missed.
Only S11 is ambiguity-positive. S07, S08, and S10 are no-answer strata.

Two independent curators each produced 144 candidates after the final protocol
freeze. A third curator selected the exact 60/120 composition without access to
legacy or future parser predictions. Exact, normalized, cross-set template, and
historical hard overlaps are zero. Thirty-seven near-duplicate findings were
reviewed and all have explicit dispositions.

The public development set is:

```text
evaluator_sets/parser_v2_v1/development_cases.jsonl
SHA-256: bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27
```

Locked inputs, labels, mappings, reviewer rows, and private salts are not
committed to Git.

## Independent operational labeling

Stage 1 used two complete, independent, reference-blind extraction reviews.
Fifty-seven disagreements triggered reference-blind arbitration. Stage 2 gave
both reviewers the same sealed Stage-1 consensus and immutable reference
packet; both completed correctness, critical, and material judgments. Stage 2
had zero disagreements. All 120 final labels are resolved.

| Measure | Result |
|---|---:|
| Stage-1 Reviewer A | 120/120 |
| Stage-1 Reviewer B | 120/120 |
| Stage-1 arbitration | 57 |
| Stage-2 Reviewer A | 120/120 |
| Stage-2 Reviewer B | 120/120 |
| Stage-2 arbitration | 0 |
| Final labels | 120 |
| Unresolved | 0 |
| Presence/validity/ambiguity/strategy exact | 120/120 |
| Output-quality exact | 112/120 |
| Output-quality rate / kappa | `14/15` / `491/571` |
| Parsed-answer exact | 120/120 |
| Candidate-list exact / mean Jaccard | 120/120 / `1` |
| Selected-span exact / mean Jaccard | 119/120 / `119/120` |
| Failure-reason exact / mean Jaccard | 111/120 / `229/240` |
| Format-warning exact / mean Jaccard | 73/120 / `199/240` |
| Stage-2 correctness exact / kappa | 120/120 / `1` |

These labels are LLM-produced operational consensus references. They are not
human ground truth.

## Visibility and procedural isolation

- Curators A and B saw the frozen protocols and only the material required to
  construct their independent candidate pools. They did not see legacy parser
  predictions, future parser-v2 code, or each other's selection decisions.
- Curator C saw the two sealed candidate pools and frozen protocol for
  deduplication and selection. Curator C did not see legacy or future parser
  predictions.
- The historical custodian alone produced non-content contamination
  fingerprints from the registered historical records; historical text was not
  supplied to curators or label reviewers.
- Stage-1 Reviewers A and B saw locked parser-facing outputs and the frozen
  extraction rubric, but no registered references.
- The Stage-1 arbiter saw both Stage-1 judgments and the same reference-blind
  packet. The arbiter could resolve extraction only.
- Stage-2 Reviewers A and B saw the sealed Stage-1 consensus, immutable
  reference packet, and critical/material rubric. They could not revise
  extraction fields.
- The Stage-2 arbiter saw the two Stage-2 judgments and registered references,
  and could resolve correctness/critical/material fields only.
- Validation and sealing automation necessarily handled the private artifacts
  to validate hashes, manifests, release membership, and persistence.
- No prospective parser-v2 implementation agent exists yet; therefore no such
  agent has seen locked inputs or labels.
- Post-sealing checkers received only the artifacts needed for their assigned
  integrity, composition, agreement, sealing, or scientific-boundary checks.

The private visibility ledger records these role transitions. The controls are
procedural and hash-audited, not RBAC-enforced blinding or a security boundary.

## Private release and hashes

The append-only parent is:

```text
phase1-evaluator-validation/parser-v2-v1/20260716T024856Z
```

Registered leaves are `development`, `locked-inputs`, `locked-labels`,
`reports`, and `manifests`. Reservations were uploaded first. Each leaf
manifest was uploaded last, and the overall manifest was uploaded last
overall. Every write used `overwrite=false`.

| Artifact | SHA-256 |
|---|---|
| Locked inputs | `2d60483e7f7a2ce1883acca2dcf9a6771f84b54d596ab2e02ed4a39d937c4e3e` |
| Stage-1 consensus | `d3cb1c8cf1b8e71bf499272a36c7c57e9fa5b917934c25e76adb230411f76f3f` |
| Stage-2 reference packet | `80cf8593fae74d2c1fdae44a469db06cf2b1eb50f5f5c3379335f794d2588dd1` |
| Final locked reference labels | `44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af` |
| Locked-labels manifest | `aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6` |
| Validation report JSON | `5b3daf44553a7c99d57c8d5a117ef82de113c4b5cde74ef13dd218c11c56b641` |
| Overall manifest | `f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260` |
| Historical fingerprint JSONL | `58adac43e7e825e92d1aa23e062ee6a554a5eedc59274fabdb21685a981839a2` |
| Historical fingerprint summary | `eb076251d30a803d7283d0e17dfda9074c676b3c11ac095ff7d3b586f7fbabdb` |

The local and in-container validators required exact 26-object membership,
canonical bytes, registered source binding, 441 historical fingerprint rows,
all review seals, all manifest hashes, and zero unresolved labels. The Azure
persister could return success only after re-listing exact remote membership
and re-downloading all 26 objects to verify size, SHA-256, and ETag.

## CPU-only Azure persistence

A direct full-repository image build, ACR run `cmf`, failed safely because the
frozen all-45 Docker attestation intentionally excluded new Phase 1.2A files.
No image, job execution, or Blob write resulted, and the attestation was not
weakened.

An independently reviewed encrypted overlay used the immutable audited base:

```text
acrjspaceobssea0708231738.azurecr.io/j-space-observation@sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac
```

Persistence details:

| Item | Value |
|---|---|
| ACR build | `cmg` |
| Temporary digest | `sha256:cd7371b7959b4eb577f75d40f0a5a7c71b585109c5ca5a072dfaccc6492efa54` |
| Sealing-code manifest | `1e6100a97cfc914b587cc6e4a1b11f3ce4483da45ae96543cc5c0c237aaf3c59` |
| Environment | `cae-jspace-observation-sea-vnet2` |
| Workload profile | `Consumption` |
| Resources | 2 CPU / 4 GiB |
| GPU | none |
| Job | `job-jspace-parser-v2-set` |
| Sole execution | `job-jspace-parser-v2-set-ib7uc0e` |
| Execution status | `Succeeded` |
| Authentication | `ManagedIdentityCredential` |
| Identity | `id-jspace-aca-acrpull-sea` |
| Storage public network | disabled |

The transport key was passed only through stdin and an ACA secret-backed
environment reference. It was never written to disk, argv, logs, or Git. The
encrypted envelope was readable by the non-root runtime; plaintext existed only
in container memory and its temporary filesystem and was deleted before exit.

After the sole execution, the job was reset to the immutable base image with
`/bin/true`. Secret count and secret-reference count are both zero. The
temporary ACR tag and digest and the local encrypted build context were deleted.
The job retains exactly one terminal execution and must not be started again for
this sealing operation.

## Frozen acceptance gates

The following gates remain preregistered and unevaluated:

- overall exact typed decision: at least 114/120;
- every answer-bearing stratum: at least 9/10;
- every-stratum floor: at least 8/10;
- answer-presence macro-F1: at least 0.95;
- ambiguity precision and recall: each at least 0.90;
- no-answer precision and recall: each at least 0.90;
- S01/S02 boxed/final misses: zero;
- S06 rightmost-distractor selections: zero;
- wrong-span errors: at most 1/80;
- material correctness errors: at most 1/120 and zero in S01/S02;
- clean pooled parser-v2 exact count cannot regress versus legacy;
- at least one critical stratum must improve by one exact decision.

No parser-v2 PASS, FAIL, or INVALID result exists in Phase 1.2A.

## Independent post-sealing checks

All checks used `gpt-5.6-sol` with reasoning effort `max`.

| Check | Agent | Result |
|---|---|---|
| Integrity and provenance | `postseal-integrity` | PASS |
| Strata and composition | `postseal-strata` | PASS |
| Label agreement | `postseal-agreement` | PASS |
| Sealing and one-shot controls | `postseal-one-shot` | PASS |
| Scientific boundaries | `postseal-boundaries` | PASS |

The secure transport received an additional independent PASS from
`secure-persistence-review` before the Azure execution.

Final model-free validation:

```text
python -m pytest tests\ -q
460 passed, 2 warnings
```

## Scientific boundaries

Phase 1.2A constructed, operationally labeled, and sealed synthetic model-free
evaluator fixtures for the historical target
`deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`. Existing records were used only
for taxonomy and contamination checking. No target-model download, load,
inference, GPU use, parser-v2 implementation, locked evaluation, or higher-n
behavioral run occurred.

Fixture and LLM-consensus labels are operational references, not target-model
evidence or human ground truth. Isolation is procedural and hash-audited, not
security-enforced. The holdout is SEALED, not evaluated; no parser-v2 PASS/FAIL
exists. This phase provides no hidden-reasoning, internal-workspace,
invisible-CoT, genuine-no-CoT, or J-space evidence. `stopped_intervention`
remains intervention-controlled; `postprocessed_utility` remains
answer-recovery utility, not raw no-CoT.

## Next authorized step

Implement the prospective parser v2 using only the open development set. Freeze
and push the implementation commit before separately authorizing the one-shot
locked evaluation. Higher-n and any new target-model run remain paused.
