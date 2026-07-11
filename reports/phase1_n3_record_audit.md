# Phase 1 n=3 Record-Level Artifact Audit

Date: 2026-07-11

## Executive Result

The read-only, model-free audit completed successfully against the immutable
source prefix:

```text
stjspacefiles0709085305
/jspace-results
/phase1-limited-n3-gates/20260710T152820Z
```

Deterministic result: `completed_clean`.

- 45 generation records and 45 evaluation records were parsed and paired.
- All pairing, membership, registered-answer, common-field, selected-output
  transformation, parser replay, metric, baseline, and classification checks
  passed.
- The four source artifacts retained identical before/after Blob properties.
- Eight audit files were written only to a separate audit prefix.
- No model was loaded or invoked, and no new behavioral observation was
  generated.

This is artifact-integrity and evaluator-consistency evidence only.

## Scope and Provenance

```text
Starting repository commit:
a4bbf8911e0f758eb10230e52c6e953ef8df9cee

Experiment writer commit:
359643b7b5eb8f95c13cca2e60fa753df8701282

Audit implementation commit:
9537ed8e0b5da95b68714b73fa11236b48ee046a

Audit schema:
phase1-record-integrity/v1

Source prefix:
phase1-limited-n3-gates/20260710T152820Z

Audit output prefix:
phase1-audits/n3-gates-20260710T152820Z/20260711T010339Z
```

The source-run parser and current parser are both unversioned. Their source
files did not change between the writer commit and the audit implementation
commit. Current-code replay was kept separate from stored source fields.

## Audit Implementation

Added:

- `src/jspace_observation/record_audit.py`
- `scripts/audit_phase1_blob_run.py`
- `tests/test_record_audit.py`

Adjusted:

- `infra/azure/scripts/06_run_job_acr_mi.sh`
  - passes audit source/output prefixes and implementation provenance;
  - rejects audit mode on a GPU workload profile.
- `.gitignore`
  - excludes local audit downloads and raw logs.

Pairing key:

```text
type: composite
fields:
model_name
task_family
depth
condition
task_id
```

Validation:

```text
python -m pytest tests\ -q
139 passed, 2 warnings
```

No test loaded or downloaded a model.

## Review Workflow

The requested agent model was `gpt-5.6 soil`; the available model actually used
was `gpt-5.6-sol`, with reasoning level `max`.

- Pre-run design: `record-schema-audit`, `record-metrics-audit`,
  `record-ambiguity-audit`.
- Implementation review: `record-implementation-review`, `record-fix-review`.
- Post-run review: `record-integrity-review`,
  `metrics-classification-review`, `ambiguous-review-a`,
  `ambiguous-review-b`, `science-boundary-review`.
- Ambiguity arbitration: `ambiguous-review-arbiter`.

## ACR and Azure Execution

```text
ACR build:
cmc

Image:
acrjspaceobssea0708231738.azurecr.io/j-space-observation:9537ed8e0b5d

Digest:
sha256:90adfc1b6be6fbb7a17a878bed7970ffd71c62b72263a36b41110ba6f19b169b

Environment:
cae-jspace-observation-sea-vnet2

Workload profile:
Consumption

Resources:
2 CPU / 4Gi

GPU:
none

Job:
job-jspace-p1-record-audit

Execution:
job-jspace-p1-record-audit-d9q5uy8

Start:
2026-07-11T01:03:59Z

End:
2026-07-11T01:05:25Z

Status:
Succeeded
```

The first create request used the suggested `1 CPU / 4Gi` combination and was
rejected before job or execution creation because Consumption requires paired
CPU/memory shapes. The successful create used `2 CPU / 4Gi`. The helper
automatically started the sole execution; no separate start command was issued.

## Source Manifest and Immutability

| Artifact | Bytes | Lines | SHA-256 | ETag | Unchanged |
|---|---:|---:|---|---|---|
| `phase1_generations.jsonl` | 138133 | 45 | `b45c972af6f8a2be771e308d943ff793bdafd44c486a4eae9ea8a4e7f1ec11a0` | `"0x8DEDE985A8ECD24"` | true |
| `phase1_eval_records.jsonl` | 84824 | 45 | `57aee97ef98a9be14e489bf6aa4a6e09a80fd5ceedb2df8fadc8d991be98538b` | `"0x8DEDE985A8CF8AF"` | true |
| `phase1_metrics.csv` | 4223 | 16 | `14df044221ed34320d797c66aee17948e756aacb316c882e36cdf84ab496a3d1` | `"0x8DEDE985A918BD4"` | true |
| `phase1_summary.md` | 15814 | 98 | `fcc8a33efd8462e39b4f3d9fb704379bf740e0fc2cb7593d087f6de0b4c76173` | `"0x8DEDE985A933949"` | true |

Before/after comparisons used content length, ETag, last-modified time, and
version ID. Source version IDs were null. The audit did not write under the
source prefix.

## Audit Output

Eight files were uploaded with `overwrite=False`:

1. `record_audit_manifest.json`
2. `record_audit_report.json`
3. `record_audit_report.md`
4. `record_pairing_mismatches.jsonl`
5. `ambiguous_parse_records.jsonl`
6. `ambiguous_parse_deterministic_review.jsonl`
7. `recomputed_metrics.csv`
8. `recomputed_branch_classifications.json`

`record_pairing_mismatches.jsonl` contains zero findings.

## Syntax, Pairing, and Membership

| Check | Result |
|---|---|
| Generation physical/valid/invalid/blank lines | `45 / 45 / 0 / 0` |
| Evaluation physical/valid/invalid/blank lines | `45 / 45 / 0 / 0` |
| Unique generation keys | `45` |
| Unique evaluation keys | `45` |
| Generation-only/evaluation-only keys | `0 / 0` |
| Duplicate generation/evaluation keys | `0 / 0` |
| Canonical record order | `true / true` |
| Expected/actual cells | `15 / 15` |
| Records per cell | `3` |
| Unique items per cell | `3` |
| Missing/extra combinations | `0 / 0` |
| Registered-answer mismatches | `0` |

Actual membership is exactly:

- model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`;
- task family: `arithmetic`;
- depths: `1,2,3`;
- five registered conditions;
- three registered arithmetic task IDs at each depth.

## Field, Transformation, and Parser Consistency

```text
Generation/evaluation pairs checked:
45

Common-field mismatched pairs:
0

Selected-output transformation mismatches:
0

Stored/current parser mismatches:
0

Stored correctness alias mismatches:
0
```

Raw, stopped, and postprocessed outputs were not treated as interchangeable.
Stopped output and metadata were replayed with the registered stop strings.
Postprocessed output and metadata were replayed with the deterministic
postprocessor.

## Metrics, Baselines, and Branches

```text
Stored metric rows:
15

Recomputed metric rows:
15

Matching rows:
15

Mismatching rows:
0

Maximum absolute difference:
0.0

Latency limitations:
0
```

Visible-CoT baseline:

| Depth | n | Accuracy | Parse valid | Baseline valid | Failure reason |
|---|---:|---:|---:|---|---|
| 1 | 3 | 0.3333 | 1.0000 | true | `NA` |
| 2 | 3 | 0.6667 | 1.0000 | true | `NA` |
| 3 | 3 | 0.0000 | 1.0000 | false | `visible_cot_accuracy_zero` |

Branch classifications:

| Depth | Raw strict | Stopped intervention | Postprocessed utility |
|---|---|---|---|
| 1 | `raw_strict_not_established` | `stopped_intervention_usable` | `postprocessed_answer_recovery_usable` |
| 2 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_task_failed` |
| 3 | `raw_strict_not_established` | `stopped_intervention_not_useful` | `postprocessed_surface_clean_but_task_failed` |

All nine classifications and ordered passed/failed/not-applicable criteria
matched the stored summary. At depth 3, postprocessed non-degradation remains
`0 >= 0`, but the absolute accuracy floor fails; the task-failed classification
is retained.

The deterministic tool compared all 15 row payloads. The independent
post-run reviewer could verify the aggregate comparison result and all nine
classifications from recovered stdout, but not independently inspect every
recomputed metric-row payload. Its row-by-row metric verdict is therefore
`INCONCLUSIVE`; the deterministic comparison itself is `PASS`.

## Ambiguous-Parse Review

Stored `parse_ambiguous=true` records: `18`.

Two independent `gpt-5.6-sol` reviewers used reasoning level `max`. They did
not see each other's conclusions. An arbiter reviewed all disagreement records.

Agreement before arbitration:

| Measure | Result |
|---|---:|
| Exact ambiguity-category agreement | `17/18 (94.44%)` |
| Category Cohen's kappa | `0.6471` |
| Exact answer-status agreement | `17/18 (94.44%)` |
| Answer-status Cohen's kappa | `0.9082` |
| Best-answer agreement | `18/18 (100%)` |
| Parser-consistency agreement | `18/18 (100%)`; kappa `NA` because both were constant |
| Correctness-consistency agreement | `16/18 (88.89%)`; kappa `NA` because one marginal was constant |
| Exact issue-set agreement | `4/18 (22.22%)` |
| Mean issue-set Jaccard | `0.7565` |
| Exact confidence agreement | `15/18 (83.33%)` |
| Confidence mean absolute error | `0.1667` |
| Confidence quadratic-weighted kappa | `0.5263` |

Any category, answer, issue-set, consistency, or material-confidence difference
triggered arbitration. This produced 14 disagreement records, 14 arbiter
decisions, and zero unresolved records.

Final adjudication:

| Index | Task / condition | Category | Answer status | Best answer | Issues |
|---:|---|---|---|---|---|
| 1 | `arith_1op_001 / visible_cot` | `parser_overflag` | correct | `12` | incomplete/truncated; malformed |
| 2 | `arith_1op_002 / visible_cot` | `parser_overflag` | correct | `15` | explicit extraction; incomplete/truncated; last-number risk |
| 3 | `arith_1op_003 / visible_cot` | `parser_overflag` | correct | `24` | explicit extraction; incomplete/truncated; last-number risk; malformed |
| 4 | `arith_1op_001 / r1_style_thinking` | `true_multiple_candidate_ambiguity` | ambiguous | `NA` | incomplete/truncated; last-number risk; no answer |
| 5 | `arith_1op_002 / r1_style_thinking` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; no answer |
| 6 | `arith_1op_003 / r1_style_thinking` | `parser_overflag` | no answer | `NA` | last-number risk; malformed; no answer |
| 7 | `arith_2op_001 / visible_cot` | `parser_overflag` | correct | `16` | incomplete/truncated |
| 8 | `arith_2op_002 / visible_cot` | `parser_overflag` | correct | `16` | incomplete/truncated; malformed |
| 9 | `arith_2op_003 / visible_cot` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; no answer |
| 10 | `arith_2op_001 / r1_style_thinking` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; no answer |
| 11 | `arith_2op_002 / r1_style_thinking` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; no answer |
| 12 | `arith_2op_003 / r1_style_thinking` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; no answer |
| 13 | `arith_3op_001 / visible_cot` | `parser_overflag` | incorrect | `1` | none |
| 14 | `arith_3op_002 / visible_cot` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; no answer |
| 15 | `arith_3op_003 / visible_cot` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; no answer |
| 16 | `arith_3op_001 / r1_style_thinking` | `parser_overflag` | correct | `18` | none |
| 17 | `arith_3op_002 / r1_style_thinking` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; malformed; no answer |
| 18 | `arith_3op_003 / r1_style_thinking` | `parser_overflag` | no answer | `NA` | incomplete/truncated; last-number risk; no answer |

Final category totals:

```text
parser_overflag: 17
true_multiple_candidate_ambiguity: 1
parser_underflag: 0 within the selected flagged set
review_inconclusive: 0 after arbitration
```

Final answer-status totals:

```text
correct: 6
incorrect: 1
ambiguous: 1
no_answer: 10
inconclusive: 0
```

All 18 stored parser/correctness records are mechanically reproducible by the
current evaluator. Records 2 and 3 nevertheless contain unique correct answer
claims that the last-number parser misses. This is a semantic extraction
limitation, not artifact corruption.

Reviewing only records already flagged `parse_ambiguous=true` cannot detect
parser underflags among the other 27 records. The underflag count is therefore
not assessed globally.

## Operational Errors

1. Initial ACR polling used an unsupported `az acr run show --run-id` form.
   Build `cmc` was not repeated and was verified with `az acr task show-run`.
2. The first ACA create request used invalid Consumption resources
   (`1 CPU / 4Gi`). It failed before job/execution creation. The successful
   configuration used `2 CPU / 4Gi`.
3. A local JMESPath polling expression was split by Windows command parsing.
   The helper had already started the sole execution; no second start occurred.
4. The replica was cleaned before `az containerapp job logs show` ran.
   The same execution's 43 console rows were recovered from the configured Log
   Analytics workspace; no audit rerun was performed.
5. The branch JSON console event was transport-split into two Log Analytics
   rows. The two fragments reconstructed as valid JSON.

## Scientific and Audit Boundaries

- The deterministic audit completed cleanly for artifact integrity and
  evaluator consistency only.
- It generated no new behavioral observations and does not validate behavioral
  conclusions.
- `n=3` is only the registered minimum, not evidence of stability, robustness,
  or generalizability.
- Stopped outputs remain intervention-controlled.
- Postprocessed outputs measure answer-recovery utility, not raw no-CoT.
- LLM ambiguity review is audit opinion, not human ground truth.
- Parser consistency is not semantic correctness.
- Reviewing flagged records cannot exclude underflags.
- No hidden-reasoning, internal-workspace, genuine invisible-reasoning, or
  J-space claim is made.

## Next Gate

Do not run a higher-n replication yet. First preregister one of two paths:
an all-45 parser-underflag audit, or a prospective parser-method decision that
addresses the demonstrated last-number extraction limitation without rewriting
this historical run.
