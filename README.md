# J-space observation

> [!IMPORTANT]
> **Project status: `DISCONTINUED — RESEARCH QUESTION UNANSWERED`**
>
> The project ended on 2026-08-29. Nothing in this repository authorizes a successor experiment, model run, or cloud operation.

## Project overview

This repository investigated whether a DeepSeek-R1 distilled checkpoint acquired an observable and causally meaningful internal reasoning process, rather than only reproducing visible chain-of-thought or answer patterns.

The program did **not** answer that question. Study 1 and Study 2 stopped before behavioral confirmation; Study 3 and Study 3R stopped at protocol review; Study 4F-M1 did not qualify a natural positive reference and never ran the target; and all six Study 5 phases stopped at apparatus gates. The correct conclusion is therefore that the hypothesis was **not tested**, not that J-space or hidden reasoning was absent.

The repository is most defensibly read as an empirical methods and reproducibility archive. Its evidence-supported contributions concern interface qualification, intervention integrity, and failed measurement preconditions.

## Strongest preserved observations

1. **Batch-shape numerical integrity.** On two Study 5 objects, the old batch-one-versus-batched comparison produced mean bfloat16 baseline shifts of 0.623730 and 0.110938 logits, compared with 0.0000166 and 0.00000806 in float32. A three-part batch-matched repair produced exact zero mean deviation for all registered no-op families in the recorded runs.
2. **Interface-dependent positive-reference qualification.** Study 4F-M1 recorded 93.3%–100% generated-CoT exact-correct rates in four 7B/14B cells, while all 240 paired raw-direct continuations were unparseable under the exact answer-plus-EOS contract.
3. **Reusable engineering object.** Study 5 P-0c-2 established a constructed `NAME → letter → digit` selection set at 0.840625 clean accuracy and 0.10625 accuracy after removing the queried name's registration line. It is not evidence about a natural reasoning task or an internal intermediate.

These observations do not establish J-space, hidden reasoning, causal distillation effects, or general J-lens validity.

## Read first

- [Academic report](REPORT.md) — evidence-based methods report, results, validity threats, and future experiments
- [Experiment index](EXPERIMENTS.md) — every major experiment, status, evidence file, and claim ceiling
- [Reproducibility guide](REPRODUCIBILITY.md) — CPU audit reproduction, historical environments, and missing assets
- [Project discontinuation decision](PROJECT_DISCONTINUATION.md) — terminal project authority
- [Terminal study index](studies/README.md) — authoritative Study 1–5 routing
- [Claim audit](paper/report_claim_audit.md) — claim-to-file matrix and intentionally excluded claims

## Reproduce the report-level analysis

The report analysis reads committed result files only. It performs no model inference and requires no GPU.

```bash
python3 -m venv .venv-report
source .venv-report/bin/activate
python -m pip install -r analysis/requirements-report.txt
python analysis/reproduce_report.py --check
```

Expected output:

```text
PASS: report metrics reproduce exactly; no model execution performed
```

To regenerate the derived JSON and both PNG/SVG figures:

```bash
python analysis/reproduce_report.py
```

See [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) before attempting study-specific validators or GPU reconstruction.

## Repository structure

| Path | Contents |
|---|---|
| `studies/study1` … `studies/study5` | study-specific protocols, decisions, data, results, failures, and terminal records |
| `data/` | committed public/source-derived task and corpus inputs |
| `artifacts/` | execution receipts, manifests, selected row-level outputs, and audit records |
| `src/`, `scripts/`, `tools/` | reusable package code, experiment runners, validators, and utilities |
| `tests/` and study-local `tests/` | current and history-relative integrity tests |
| `analysis/` | report-only deterministic recalculation and derived metrics |
| `figures/` | report figures generated from committed data |
| `paper/` | historical evidence/limitations ledgers and the report claim audit |
| `docs/`, `reports/` | historical handoffs, decisions, prompts, audits, and status records |

Raw or closest-to-raw committed evidence remains in each study's `data/`, `stage_*`, `out/`, `journal/`, or `results/` directories. There is no single pooled raw-data file because the experimental object changed across studies. [`EXPERIMENTS.md`](EXPERIMENTS.md) points to the authoritative evidence for each result.

## Environment and full experiment reproduction

Historical execution spans Tesla T4 and NVIDIA A100 80GB PCIe hardware, several immutable DeepSeek/Qwen checkpoints, and multiple pinned containers. Study-specific manifests are authoritative. The most complete locks are:

- Study 2: `studies/study2/stage_bd/stage_bd_core_manifest.json`
- Study 4F-M1: `studies/study4f/execution-m1/M1_FINAL_DISCLOSURE.md`
- Study 5: `studies/study5/qualification-eq1/container_image.json` and `requirements.study5-eq1.lock.txt`

Full GPU reproduction is not self-contained: model weights, large `.pt` lens objects, private evaluator inputs, credentials, and provider resources are excluded from Git. Do not silently substitute current model revisions or regenerated private inputs.

## Known limitations

- No valid mechanistic confirmation was executed on the intended 1.5B target.
- Public checkpoint comparisons cannot identify what distillation training caused.
- The Study 4F interface routes differ in multiple bundled dimensions.
- The batch-width result has two object-level replications on a narrow model/hardware stack.
- The top-level dependency list is unpinned; exact locks are study-specific.
- Some historical scope-relative tests expire after later commits.
- The repository has no top-level license; reuse terms for original project content are therefore unspecified.

## Historical integrity and cloud boundary

All original results, failed gates, negative outcomes, reviews, receipts, and seals remain in place. Earlier prospective language is historical and cannot override the project-level terminal decision. This documentation and analysis update performs no Azure operation and authorizes none.
