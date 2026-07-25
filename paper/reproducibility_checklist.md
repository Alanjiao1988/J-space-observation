# Reproducibility checklist

Status vocabulary: `yes`, `partial`, `no`, `not_applicable`.

## Code and provenance

| Item | Status | Notes |
| --- | --- | --- |
| All analysis code is in version control | yes | `Alanjiao1988/J-space-observation`, branch `main`. |
| Every run records its code commit | yes | Recorded in `00_stage_manifest.json` and in `paper/evidence_ledger.csv`. |
| Every containerised run records an image digest | yes | Images are pulled by digest; `latest` is never used. |
| Container images are immutable | yes | ACR tags and manifests are write- and delete-disabled. |
| Frozen scientific code is never modified after freeze | yes | Verified by diffing `src/jspace_observation/eval_parsing.py`, `eval_parsing_v2.py`, and `parser_v2_locked_evaluation.py` against the freeze commit. |
| Third-party research code is pinned to an exact commit | yes | `anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`, lock SHA-256 recorded. |

## Data

| Item | Status | Notes |
| --- | --- | --- |
| Every input corpus has a recorded SHA-256 | yes | Recorded in `paper/artifact_index.csv`. |
| Public development fixtures are committed | yes | `evaluator_sets/parser_v2_v1/development_cases.jsonl`. |
| Locked holdout inputs and labels are excluded from Git | yes | Enforced by `.gitignore` and verified with `git check-ignore`. |
| Row-level records carry provenance, not just output text | yes | `02_records.jsonl` requires `input_hash`, `output_hash`, and `source_item_id` on every line. |
| Overlap between development and locked sets is verified, not asserted | yes | Hard exact and normalized overlap must be zero and is checked by code. |
| Retired holdout content is available for re-verification | partial | It remains immutable in private Blob storage, but access requires a temporary, prefix-scoped role grant that is removed immediately after use. |

## Protocol

| Item | Status | Notes |
| --- | --- | --- |
| Acceptance gates are preregistered before results are seen | yes | `docs/phase1_parser_v2_acceptance_gates.json`, frozen and hashed before construction. |
| Gate denominators are frozen populations, not observed counts | yes | Documented in `paper/methods_ledger.md`; this was the only point of initial disagreement during independent verification. |
| Deviations are recorded even when they change nothing | yes | `08_deviations.json` is emitted for every stage, empty when there are no deviations. |
| Negative results are retained | yes | The parser-v2 FAIL is recorded in full and is not being reframed. |
| One-shot evaluations are not repeated for a better result | yes | Enforced by sealed attestations with `metric_recompute_allowed = false` and `prediction_rerun_allowed = false`. |
| Every stage emits the same artifact pack | yes | Ten fixed files with `artifact_manifest.json` written last; missing content is recorded as `not_applicable` with a reason rather than omitted. |

## Statistics

| Item | Status | Notes |
| --- | --- | --- |
| Sample sizes are reported per cell | yes | `03_metrics.csv` carries `n`, `numerator`, and `denominator` on every row. |
| Confidence intervals are reported | yes | Wilson 95% score intervals are emitted per cell in `03_metrics.csv` and the four `cell_selection/` tables for Phase 1.0C run `20260725T170041Z`; the implementation is unit-tested against known values. Not meaningful for the deterministic parser evaluation. |
| Seeds are fixed and recorded | yes | Recorded in `01_protocol_snapshot.json`. Phase 1.0C used selection seed `20260725` and run base seed `20260725`. |
| Multiple-comparison exposure is acknowledged | partial | Acceptance gates are preregistered, but per-cell headroom screening across 30 family x band x condition cells is not corrected and is described as a screen, not a test. n=10 per cell is a screen and never a stable performance estimate. |
| Inconclusive outcomes are reported as such | yes | Phase 1.0C run `20260725T170041Z` carries the preregistered status `INCONCLUSIVE` because 44 of 300 rows were adjudicated unresolved; the two qualifying cells are reported as candidate substrates, not as established results. |

## Environment

| Item | Status | Notes |
| --- | --- | --- |
| Hardware is recorded | yes | Tesla T4 with exact device memory for GPU runs; CPU-only profiles otherwise. |
| Software versions are recorded | yes | Python, torch, transformers, huggingface-hub, numpy, CUDA and cuDNN versions in `paper/methods_ledger.md`. |
| The committed tree alone reproduces the run environment | no | See limitation L-12: two infrastructure-only workarounds were applied on the orchestrator host outside the repository. |
| Storage access uses managed identity only | yes | Private endpoint, no key, no SAS, public network access disabled. |
| Temporary privilege grants are removed and the removal is verified | yes | Phase 0.5B used one temporary `Storage Blob Data Reader` grant, removed and confirmed absent at container and subscription scope. Phase 0.5C used one temporary ABAC grant scoped by `blobs:path` to a single blob for the launcher preflight, deleted afterwards, with container-scope assignments measured as 0 and the control identity holding 0 blob-data roles. Note the standing account-scope assignment described in L-17, which was not removed. |

## Replication

| Item | Status | Notes |
| --- | --- | --- |
| Runs are replicated | no | Every execution is a single run under one-shot discipline. See limitation L-10. Phase 0.5C fitted a second same-size J-lens on a disjoint sample, which measures independent-fit disagreement once; it is not a replication of a run and yields one difference, not a distribution. |
| An independent same-size refit was performed | yes, once | Phase 0.5C run `20260725T174743Z` fitted 25B on prompts disjoint from 25A. The two lenses disagree by 0.4831 relative Frobenius and 0.8781 cosine, both outside their registered limits. |
| Results are replicated across hardware | no | Single T4 configuration only. |
| An independent recomputation was performed | yes | The parser-v2 result was independently recomputed from the sealed ledger and the frozen gate contract; 38 of 38 checks agreed. |
