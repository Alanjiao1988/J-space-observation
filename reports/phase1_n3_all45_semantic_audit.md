# Phase 1 bounded n=3 all-45 semantic parser audit

## Executive result

The preregistered all-45 review is complete for historical outputs from
`deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`. Two independent blinded
`gpt-5.6-sol` reviewers at reasoning effort `max` completed Stage 1 and
Stage 2 for all 45 records. Four disagreements were resolved by a distinct
`gpt-5.6-sol`/`max` arbiter; no record remains unresolved.

The final semantic review found:

- parser underflags: **0**;
- parser overflags: **18**, all in visible-reasoning conditions;
- true multiple-candidate ambiguity: **0**;
- observed extraction errors: **14**;
- material correctness errors: **2**;
- material evaluator issues: **19**.

The two material correctness errors are `visible_cot`, depth-1 records
`R019` and `R038`: stored correctness was false while the audit-only semantic
judgment was correct. The audit-only `visible_cot` depth-1 accuracy is
`1.0000`, versus stored/recomputed `0.3333`. At depth 2, the audit-only
visible-CoT parse-valid rate is `0.6667`, making that baseline invalid under
the registered baseline guard. These changes affect baseline and relative
gate interpretation, although none of the nine final branch classification
labels changes.

This is preregistered **Path C**: pause higher-n replication and first build a
locked evaluator validation set and prospective parser-v2 protocol. No parser
was changed in this audit, and no historical artifact was rewritten.

## Scope and provenance

| Field | Value |
|---|---|
| Experimental target | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` |
| Task family | arithmetic |
| Source writer commit | `359643b7b5eb8f95c13cca2e60fa753df8701282` |
| Source Blob prefix | `phase1-limited-n3-gates/20260710T152820Z` |
| Source observations | 45 historical records; 15 cells at n=3 |
| Protocol/tooling commit | `cfa99fc6e204db5cf1076a13a8975e13db226931` |
| Protocol bundle SHA-256 | `21e713bab3ad54362e0e8571c5c61cca0f4ae5312230ad9760c6264ea9e9d633` |
| Shuffle seed | `20260711` |
| Stage-1 packet SHA-256 | `4e6b9b5085fcd859d03cbd5ddccd3749904af19edd875c12c1965f713476f622` |
| Stage-2 packet SHA-256 | `06f1d5b5a95e7cd39fb692a4ce798fa64747b362aaefcbb6532c6630db73ed3d` |
| Arbitration packet SHA-256 | `08734f887b516fd9f3746d2fdb1e78016b7267f26b57dc73e98f9461a8df8fad` |
| Semantic audit parent prefix | `phase1-semantic-audits/all45-parser-underflag-20260715T094500Z` |

Source bytes were re-read through the private endpoint with managed identity.
Before/read/after Blob properties were unchanged, conditional ETag reads
succeeded, and no source write was attempted.

| Source artifact | Bytes | SHA-256 |
|---|---:|---|
| `phase1_generations.jsonl` | 138133 | `b45c972af6f8a2be771e308d943ff793bdafd44c486a4eae9ea8a4e7f1ec11a0` |
| `phase1_eval_records.jsonl` | 84824 | `57aee97ef98a9be14e489bf6aa4a6e09a80fd5ceedb2df8fadc8d991be98538b` |

## Azure execution

| Field | Value |
|---|---|
| Environment | `cae-jspace-observation-sea-vnet2` |
| Workload profile | `Consumption` |
| Resources | 2 CPU / 4Gi |
| GPU | none |
| Managed identity | `id-jspace-aca-acrpull-sea` |
| ACR build run | `cme` |
| Image | `acrjspaceobssea0708231738.azurecr.io/j-space-observation:cfa99fc6e204` |
| Image digest | `sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac` |
| Job | `job-jspace-p1-all45-pack` |

Executions used for the staged release and private byte transfer:

| Execution | Status | Purpose |
|---|---|---|
| `job-jspace-p1-all45-pack-2f0w7do` | Succeeded | Stage-1 private Blob release |
| `job-jspace-p1-all45-pack-yfn9b09` | Failed | Read-only print attempt used a non-writable directory; no Blob write |
| `job-jspace-p1-all45-pack-k5jb2g8` | Succeeded | Deterministic Stage-1 packet print |
| `job-jspace-p1-all45-pack-t2vz2b1` | Succeeded | Stage-1 release-byte verification |
| `job-jspace-p1-all45-pack-kuw8801` | Succeeded | Stage-2 release and packet print |
| `job-jspace-p1-all45-pack-kc3kot4` | Succeeded | Private immutable-source byte verification |

Replica retry limit was zero. No execution loaded, downloaded, or ran the
experimental model. No key, SAS, public Storage network path, GPU, or Azure
Files shared-key mount was used.

## Review design and completion

The protocol was frozen and pushed before any all-45 packet was released.
Stage 1 contained model outputs and task metadata but no registered reference
answer, stored parser field, stored correctness field, metric, classification,
or previous review. Stage 2 released only registered references after both
complete Stage-1 submissions had been sealed.

| Role | Identity | Model / effort | Records |
|---|---|---|---:|
| Reviewer A | `gpt-5.6-sol-max-reviewer-a` | `gpt-5.6-sol` / `max` | 45 + 45 |
| Reviewer B | `gpt-5.6-sol-max-reviewer-b` | `gpt-5.6-sol` / `max` | 45 + 45 |
| Arbiter | `gpt-5.6-sol-max-arbiter` | `gpt-5.6-sol` / `max` | 4 |

Missing IDs, duplicate IDs, invalid categories, invalid issue tags, and invalid
answer statuses were all zero. Arbitration was triggered for `R002`, `R009`,
`R018`, and `R022`. Final unresolved count is zero.

## Reviewer agreement

| Measure | Agreement | Kappa / related measure |
|---|---:|---:|
| Semantic category | 43/45 (`0.9556`) | nominal kappa `0.9372` |
| Answer presence | 44/45 (`0.9778`) | nominal kappa `0.9564` |
| Answer status | 44/45 (`0.9778`) | nominal kappa `0.9615` |
| Best answer overall | 45/45 (`1.0000`) | nominal kappa `1.0000` |
| Best answer, both non-null | 21/21 (`1.0000`) | — |
| Issue-set exact | 43/45 (`0.9556`) | exact-set kappa `0.9488` |
| Issue-set mean Jaccard | `0.9704` | — |
| Confidence exact | 45/45 (`1.0000`) | quadratic weighted kappa `1.0000` |

These are same-model independent-review agreement measures, not agreement
between human ground-truth annotators.

## Ambiguity confusion matrix

Only `true_multiple_candidate_ambiguity` is semantic ambiguity-positive.

| | Semantic ambiguity positive | Semantic ambiguity negative |
|---|---:|---:|
| Stored ambiguity flag positive | TP 0 | FP 18 |
| Stored ambiguity flag negative | FN 0 | TN 27 |

| Metric | Value |
|---|---:|
| Precision | `0.0000` |
| Recall | `NA` (zero semantic-positive denominator) |
| Specificity | `0.6000` |
| False-positive rate | `0.4000` |
| False-negative rate | `NA` |
| Negative predictive value | `1.0000` |
| Accuracy | `0.6000` |

All 18 stored ambiguity flags were semantic overflags: nine `visible_cot` and
nine `r1_style_thinking`. No semantic ambiguity was found among the 27
unflagged records, so parser underflag count is zero.

## Final semantic categories and answer status

| Semantic category | Count |
|---|---:|
| Unambiguous single answer | 11 |
| True multiple-candidate ambiguity | 0 |
| No answer | 10 |
| Incomplete or truncated | 20 |
| Malformed but answer recoverable | 3 |
| Malformed with no reliable answer | 1 |
| Review inconclusive | 0 |

| Answer status | Count |
|---|---:|
| Correct | 17 |
| Incorrect | 4 |
| Ambiguous | 0 |
| No answer | 24 |
| Inconclusive | 0 |

## Extraction findings

| Finding | Count |
|---|---:|
| Parser overflags | 18 |
| Parser underflags | 0 |
| Explicit answer marker missed | 0 |
| Boxed answer missed | 0 |
| Last-number selection risks | 15 |
| Observed extraction errors among those risks | 14 |
| Intermediate-number selections | 0 |
| Parser wrong-span tags | 0 |

The 15 last-number tags are risk indicators, not automatically observed or
material errors. Fourteen coincide with observed selected-answer/presence
disagreement; `R001` is the risk-only exception.

## Correctness consistency

| Semantic status | Stored true | Stored false |
|---|---:|---:|
| Correct | 15 | 2 |
| Incorrect | 0 | 4 |
| No answer | 0 | 24 |
| Ambiguous | 0 | 0 |
| Inconclusive | 0 | 0 |

The two stored-false/semantic-correct records are `R019` and `R038`, both
`visible_cot`, depth 1. No stored-correct record became semantic-incorrect.

## Condition, branch, and depth breakdown

| Condition | n | Correct | Incorrect | No answer | Overflag | Underflag | Material evaluator issue |
|---|---:|---:|---:|---:|---:|---:|---:|
| `strict_answer_only_prefill_answer` | 9 | 3 | 1 | 5 | 0 | 0 | 1 |
| `strict_answer_only_stopped` | 9 | 4 | 1 | 4 | 0 | 0 | 0 |
| `strict_answer_only_postprocessed` | 9 | 4 | 1 | 4 | 0 | 0 | 0 |
| `visible_cot` | 9 | 5 | 1 | 3 | 9 | 0 | 9 |
| `r1_style_thinking` | 9 | 1 | 0 | 8 | 9 | 0 | 9 |

`strict_answer_only_stopped` remains intervention-controlled, not spontaneous
no-CoT. `strict_answer_only_postprocessed` remains answer-recovery utility, not
raw no-CoT.

| Depth | n | Correct | Incorrect | No answer | Overflag | Underflag | Material evaluator issue |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 15 | 11 | 0 | 4 | 6 | 0 | 7 |
| 2 | 15 | 5 | 0 | 10 | 6 | 0 | 6 |
| 3 | 15 | 1 | 4 | 10 | 6 | 0 | 6 |

## Material impact and audit-only alternatives

The audit distinguishes prospective last-number risk, observed extraction
error, material correctness error, and overall material evaluator issue.

| Impact | Count | Main concentration |
|---|---:|---|
| Last-number risk | 15 | 14/15 visible-reasoning baseline |
| Observed extraction error | 14 | 13 visible-reasoning, 1 raw strict |
| Material correctness error | 2 | `visible_cot`, depth 1 |
| Material evaluator issue | 19 | 18 visible-reasoning, 1 raw strict |

Seven condition/depth cells have audit-only parser or accuracy differences.
The largest correctness difference is:

| Cell | Stored/recomputed accuracy | Audit-only semantic alternative |
|---|---:|---:|
| `visible_cot`, depth 1 | `0.3333` | `1.0000` |

At depths 1, 2, and 3, both visible-reasoning conditions' stored ambiguity
rate is `1.0000`, while the audit-only semantic ambiguity rate is `0.0000`.
For `strict_answer_only_prefill_answer`, depth 1, the stored parse-valid rate
is `1.0000` and the audit-only rate is `0.6667`.

The audit-only branch recomputation changes four gate/baseline fields:

1. Raw strict depth-1 relative accuracy gate: stored `passed`, audit-only
   `failed` because the visible-CoT alternative accuracy rises to `1.0000`.
2. Visible-CoT depth-2 baseline validity: stored `true`, audit-only `false`
   because audit-only parse-valid rate is `0.6667`.
3. Raw strict and stopped depth-2 relative gates become `NA`.
4. The postprocessed depth-2 reported relative metric becomes `NA`; it is not
   a hard postprocessed utility gate.

None of the nine final branch classification labels changes. Official stored
metrics and classifications remain authoritative and unchanged. Every number
in this section is an **audit-only semantic alternative estimate: post hoc,
noncanonical sensitivity estimate**, not a corrected or replacement result.

## Decision

The preregistered decision is **Path C** because material evaluator errors
change visible-CoT correctness/baseline interpretation and registered relative
gates. Higher-n replication is not authorized by this audit.

The next action is to preregister an evaluator validation set and a locked
prospective parser-v2 protocol, validate both before any new model run, and
dual-report legacy and prospective parser outputs in future work. Historical
results must not be rewritten.

## Scientific boundaries

- This review added no behavioral observations and does not make the
  experiment behavioral n=45; every experimental cell remains n=3.
- Reviewer and arbiter judgments are audit opinion, not human ground truth.
- The audit evaluates surface answer extraction and stored evaluator
  consistency only.
- It provides no evidence of hidden reasoning, internal workspace, invisible
  CoT, genuine no-CoT reasoning, or J-space.
- No model inference, model loading, model download, GPU use, parser change,
  historical metric change, or historical classification rewrite occurred.
