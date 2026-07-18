# Thread handoff - J-space observation project

Date: 2026-07-18

Repository: `Alanjiao1988/J-space-observation`

Current Phase 0.5 runtime launcher commit:
`be997eefbaec410107045dac7c50423f7297c633`

## 1. Authoritative identities

Historical experimental target:

```text
Display name:
DeepSeek-R1-Distill-Qwen-1.5B

Hugging Face model ID:
deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B

Role:
historical target of the bounded n=3 behavioral records and target of the
bounded Phase 0.5A technical Jacobian run
```

Engineering, curation, labeling, arbitration, and audit agents:

```text
gpt-5.6-sol
reasoning=max
```

Do not confuse the engineering agent with the experimental target.

## 2. Current phase

Path C remains preserved:

```text
status: SEALED
development cases: 60
locked cases: 120
parser v2 implemented from public development cases: yes
locked evaluation performed: no
higher-n performed: no
new target-model behavioral run: no
```

The sealing phase constructed, independently labeled, validated, and privately
sealed a prospective parser-v2 evaluator set. Parser v2 was later implemented
using only the public development set. It has no locked PASS/FAIL result.

Phase 0.5A is also complete:

```text
run ID: 20260718T184445Z
official source: anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e
primary: job-jspace-p05-jlens-l7tipil / Failed at F4
sole operational retry: job-jspace-p05-jlens-m1sazlr / Succeeded
F2/F3 recomputed on retry: no
F4: passed with unchanged tolerance after exact fp32 serialization
F5: not run
final decision: GREEN / COMPLETE for bounded technical feasibility only
Plan B: not triggered
```

Detailed report:

- `reports/phase1_parser_v2_validation_set.md`
- `reports/phase1_parser_v2_development.md`
- `reports/phase05_jlens_feasibility.md`

## 3. Frozen protocol

```text
starting commit:
58d299bb66c5536a0f1b7d0617204472fbb8c212

final protocol commit:
cc93ffe603ab8338ed860586a52b1911af4b3277

tooling/development commit:
e7a95a458d05d4ef211bb6902c2a20cb5f16bf60

production-ingress hardening:
297420abfebb65c9f3702c56f28fe5a193913cd0

sealed no-Git validation:
9b4262a9d35e6342935b8d2f72887a56c5f98486

protocol bundle SHA-256:
5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666

acceptance-gate SHA-256:
a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988
```

Frozen files:

- `docs/phase1_parser_v2_protocol.md`
- `docs/phase1_evaluator_validation_set.md`
- `docs/phase1_parser_v2_acceptance_gates.json`

The final protocol was pushed before eligible construction. Do not amend these
v1 gates after seeing a locked result.

## 4. Evaluator set

Composition:

| Property | Development | Locked |
|---|---:|---:|
| Total | 60 | 120 |
| Per S01-S12 stratum | 5 | 10 |
| Present | 40 | 80 |
| Ambiguous | 5 | 10 |
| No answer | 15 | 30 |

Locked critical cases: 80.

Locked material cases: 68.

Public development path:

```text
evaluator_sets/parser_v2_v1/development_cases.jsonl
SHA-256: bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27
```

Hard exact, normalized, cross-set template, and historical overlaps are zero.
Thirty-seven near-duplicate findings were reviewed and dispositioned.

## 5. Labeling result

- Curator A/B independently produced 144 candidates each.
- Curator C selected the exact 60/120 set.
- Stage-1 Reviewer A/B completed 120/120 each, reference-blind.
- Stage-1 disagreements and arbitration rows: 57.
- Stage-2 Reviewer A/B completed 120/120 each.
- Stage-2 disagreements and arbitration rows: 0.
- Final labels: 120.
- Unresolved: 0.
- Review seals: 7.

Key agreement:

```text
presence/validity/ambiguity/strategy: 120/120
output quality: 112/120; rate 14/15; kappa 491/571
parsed answer: 120/120
candidate lists: 120/120; mean Jaccard 1
selected spans: 119/120; mean Jaccard 119/120
failure reasons: 111/120; mean Jaccard 229/240
format warnings: 73/120; mean Jaccard 199/240
Stage-2 correctness: 120/120; kappa 1
```

These are LLM operational consensus references, not human ground truth.

Visibility:

- Curators saw frozen construction protocols, not legacy/future parser
  predictions.
- The historical custodian produced non-content fingerprints; historical text
  was not supplied to curators or reviewers.
- Stage 1 was reference-blind for both reviewers and the extraction arbiter.
- Stage 2 saw sealed consensus plus immutable references and could not revise
  extraction.
- Validation/sealing agents handled private artifacts only for workflow,
  integrity, and persistence checks.
- No prospective parser-v2 implementation agent exists or has seen locked
  inputs/labels.
- The private visibility ledger records the full role transitions.

This is procedural, hash-audited isolation, not a security-enforced boundary.

## 6. Private release and Azure state

Sealed parent:

```text
phase1-evaluator-validation/parser-v2-v1/20260716T024856Z
```

Registered leaves:

- `development`
- `locked-inputs`
- `locked-labels`
- `reports`
- `manifests`

Key bindings:

```text
artifact count:
26

locked inputs:
2d60483e7f7a2ce1883acca2dcf9a6771f84b54d596ab2e02ed4a39d937c4e3e

final labels:
44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af

locked-label manifest:
aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6

overall manifest:
f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260

validation report:
5b3daf44553a7c99d57c8d5a117ef82de113c4b5cde74ef13dd218c11c56b641
```

Azure:

```text
environment:
cae-jspace-observation-sea-vnet2

profile/resources:
Consumption / 2 CPU / 4Gi / no GPU

job:
job-jspace-parser-v2-set

sole execution:
job-jspace-parser-v2-set-ib7uc0e

status:
Succeeded

authentication:
ManagedIdentityCredential

identity:
id-jspace-aca-acrpull-sea
```

The upload used `overwrite=false`, reservation-first/manifest-last ordering,
exact 26-object membership, and per-object re-download size/SHA-256/ETag
verification.

After persistence:

- the job was reset to the immutable base image and `/bin/true`;
- job secrets and secret references are zero;
- exactly one terminal execution exists;
- the temporary ACR transport tag and digest were deleted;
- the local encrypted build context was deleted.

Do not restart this job for Phase 1.2A and do not write to the sealed parent.

## 7. One-shot holdout rule

The holdout is at `SEALED`. It has not advanced to
`IMPLEMENTATION_FROZEN`, `UNSEAL_AUTHORIZED`, or `INPUTS_READ`.

Future workflow:

1. Implement parser v2 using only the public development set.
2. Freeze and push its implementation commit.
3. Obtain separate authorization for one locked evaluation.
4. Produce and seal predictions before labels are read.
5. Score once against the frozen gates.
6. Retain PASS or FAIL and retire the holdout.

A parser, schema, assertion, threshold, or scientific failure is not retryable.
A modified parser requires a new independent holdout.

## 8. Frozen acceptance gates

- overall typed decision: at least 114/120;
- each answer-bearing stratum: at least 9/10;
- every stratum: at least 8/10;
- answer-presence macro-F1: at least 0.95;
- ambiguity precision/recall: each at least 0.90;
- no-answer precision/recall: each at least 0.90;
- boxed/final misses: zero;
- last-number trap errors: zero;
- wrong-span errors: at most 1/80;
- material correctness errors: at most 1/120 and zero in S01/S02;
- clean pooled parser-v2 count cannot regress versus legacy;
- at least one critical stratum must strictly improve.

These gates are unevaluated. No parser-v2 PASS/FAIL exists.

## 9. Validation status

```text
python -m pytest tests\ -q
460 passed, 2 warnings
```

Five post-sealing `gpt-5.6-sol/max` reviews passed:

- `postseal-integrity`
- `postseal-strata`
- `postseal-agreement`
- `postseal-one-shot`
- `postseal-boundaries`

The secure transport separately passed `secure-persistence-review`.

## 10. Historical behavioral boundary

The last target-model run remains the bounded arithmetic n=3 run:

```text
source writer commit:
359643b7b5eb8f95c13cca2e60fa753df8701282

source prefix:
phase1-limited-n3-gates/20260710T152820Z

observations:
45

cells:
15

observations per cell:
3
```

The all-45 post hoc audit found 18 parser overflags, zero underflags, 14
observed extraction errors, two material correctness errors, and 19 material
evaluator issues. It selected Path C but did not change historical records,
metrics, classifications, or parser behavior.

Raw strict, stopped intervention, and postprocessed utility remain separate.
Stopped validity is intervention-controlled. Postprocessed validity is
answer-recovery utility, not raw no-CoT.

## 11. Scientific boundaries

- No target-model download, load, or inference occurred in Phase 1.2A.
- No parser v2 was implemented or evaluated during Phase 1.2A sealing. It was
  subsequently implemented against only the public development set; the
  locked evaluation remains unperformed.
- No locked labels are in the repository.
- No higher-n or GPU run occurred.
- Fixtures and consensus labels are not target-model evidence.
- LLM consensus is not human ground truth.
- Isolation is procedural and hash-audited, not security-enforced.
- Historical cells remain n=3 and are not stability evidence.
- No hidden-reasoning, internal-workspace, invisible-CoT, genuine-no-CoT, or
  J-space claim is supported.

## 12. Next authorized action

Request explicit authorization for the one-shot parser-v2 locked evaluation
against the already frozen implementation and gates. Predictions must be
sealed before labels are read, and PASS or FAIL retires the holdout.

Do not run that evaluation automatically. Higher-n, every new target-model
behavioral run, and any larger J-lens fit remain paused.

## 13. Prompt for the next thread

```text
Continue Alanjiao1988/J-space-observation after the critical-path reset and
Phase 0.5A technical feasibility result.

Read:
- reports/phase1_parser_v2_validation_set.md
- reports/phase1_parser_v2_development.md
- reports/phase05_jlens_feasibility.md
- docs/phase1_parser_v2_protocol.md
- docs/phase1_evaluator_validation_set.md
- docs/phase1_parser_v2_acceptance_gates.json
- docs/phase05_jlens_feasibility_protocol.md
- docs/thread_handoff.md

Authoritative historical target:
deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B

Current state:
- Phase 1.2A is SEALED.
- Public development set: 60 cases.
- Private locked set: 120 cases.
- Parser v2 is implemented and frozen from public development material only.
- Locked evaluation and higher-n are not authorized.
- Phase 0.5A is GREEN for bounded real-Jacobian technical feasibility only.
- F5 and actual 10-/25-prompt fits were not run.
- No new formal behavioral observation was generated.

Task:
If separately authorized, execute the registered one-shot parser-v2 locked
evaluation exactly once against the frozen implementation. Seal predictions
before labels are read, retain PASS or FAIL, and retire the holdout. Otherwise
stop. Do not start higher-n, a new target-model behavioral run, or a larger
J-lens fit.
```
