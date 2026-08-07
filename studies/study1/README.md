# Study 1 — completed original J-space observation program

## Disposition

**Closed on 2026-08-07 at `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`.**

Terminal repository identity:

- commit: `6409d2c6d665187e4459d94d490a20d7b085e8af`
- tree: `bc8b80cb0e66f9426dcdedd52b624c892caa3fc9`
- final handoff SHA-256: `5870c82b15575086f5c29c34661d89d96d265848846e3de74162da8919951f77`

Study 1 is not merely “a negative J-lens result.” It stopped before lens
validity was measured. Its central methodological failure was a mismatch
between the original research question and the behavioral eligibility
interface used to reach that question.

## Original question versus measured question

Original question:

> Did an R1-distilled model acquire an observable, causally meaningful internal
> reasoning process rather than merely reproducing visible chain-of-thought?

What the terminal E0 actually measured:

> Under raw completion bytes, no chat template, no generated chain-of-thought,
> and one greedy clean next-token decision, are enough official public items
> answered with a registered single-token surface to populate confirmation?

The answer to the measured question was no. That does not answer the original
question.

## What was established

1. The official Jacobian Lens can run end to end on the pinned 1.5B target on a
   Tesla T4 for bounded engineering tests.
2. Parser-v2 failed its one-shot locked gate; parser-v3 was never validated and
   was later closed as nonauthoritative triage-only under `DR-01`.
3. Phase 1.0C generated 300 rows and ended `INCONCLUSIVE`; it is a preliminary
   behavior screen, not a mechanism result.
4. Phase 1.0D generated its exact 900-row pack but obtained no final semantic
   labels or cell metrics. Its preserved independent state is
   `BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`.
5. Two independent full-layer 600-sequence fits and their 50:50 M1200 merge
   were losslessly produced and independently byte-sealed. Their convergence
   and heldout statistics are engineering diagnostics only.
6. The sole frozen S3 E0 run processed all 238 official items exactly once and
   was independently reconstructed.

## Terminal E0 result

| Distribution | Official items | Mechanical eligible | Behavioral eligible | Confirmation |
|---|---:|---:|---:|---:|
| multihop | 93 | 79 | 2 | 0 |
| order-ops | 55 | 36 | 2 | 0 |
| causal-swap | 90 | 83 | 5 | 0 |

All nine behaviorally eligible rows entered development under the frozen
development-first split. Every confirmation floor was therefore zero. No
lens, E1/E2, intervention, ablation, patching, or RQ2 operation occurred.

## What was not established

Study 1 provides no evidence that:

- A600, B600, or M1200 is functionally valid or invalid;
- the target has or lacks hidden reasoning;
- a J-space or internal workspace exists or does not exist;
- R1 distillation transferred a reasoning mechanism;
- the model would fail under chat, supplied-trace, forced-choice, generated
  CoT, or another output interface.

## Closure rules

- Do not rerun, repair, relabel, backfill, rescore, or reinterpret E0.
- Do not change prompt bytes, answer surfaces, thresholds, split rules, or
  official item membership under Study 1.
- Do not use A600/B600/M1200 engineering convergence as lens validity.
- Do not resume Phase 1.0D from a Study 2 authority.
- Preserve all historical paths. This folder indexes them; it does not replace
  them.

## Authoritative reading order

1. [`terminal_manifest.json`](terminal_manifest.json)
2. [`asset_index.csv`](asset_index.csv)
3. [`../../docs/jlens_s2_s3_e0_final_handoff.md`](../../docs/jlens_s2_s3_e0_final_handoff.md)
4. [`../../docs/decision_log.md`](../../docs/decision_log.md), decisions D25–D32
5. [`../../paper/evidence_ledger.csv`](../../paper/evidence_ledger.csv), through EV-0016
6. [`../../paper/claim_evidence_matrix.md`](../../paper/claim_evidence_matrix.md)
7. [`../../paper/limitations_ledger.md`](../../paper/limitations_ledger.md), through L-67
