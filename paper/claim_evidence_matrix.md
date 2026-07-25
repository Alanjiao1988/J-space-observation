# Claim–evidence matrix

This matrix tracks every claim the project might make in a paper against the
evidence that currently exists. A claim may only move to `supported` when the
listed required evidence actually exists in `paper/evidence_ledger.csv` and is
backed by an immutable artifact.

Status vocabulary: `unsupported`, `preliminary`, `supported`, `contradicted`.

---

## CL-01 — J-lens T4 engineering feasibility

| Field | Value |
| --- | --- |
| Proposed paper claim | The official Jacobian Lens can be installed at a pinned commit, wrapped around a 1.5B target model, and run end to end on a single Tesla T4, including a real Jacobian computation, a multi-layer fit, and lens save/load/apply. |
| Required evidence | A staged run that completes the feasibility gates on real hardware with pinned model, pinned lens commit, and immutable image digest. |
| Available evidence | `EV-0001`. Phase 0.5A run `20260718T184445Z`, GREEN/COMPLETE, F0–F4 passed after one authorized serialization-only retry. |
| Missing evidence | None for this bounded claim. |
| Status | **supported** |
| Key artifacts | `phase05-jlens-feasibility/20260718T184445Z`; image `sha256:345dde4f70235af3ad2542f79ea1445b66f4f53abe6fd569cd0818b8c4e8db35`; lock SHA-256 `981e580531e517be1bd1a3fef98ac12822f40d626ba8f365e59973ff258f36ea`. |
| Limitations | Two fit prompts only. F5 not run. Nothing about lens quality, correctness, or meaning follows. |

---

## CL-02 — Scientifically usable J-lens

| Field | Value |
| --- | --- |
| Proposed paper claim | The fitted Jacobian lens is of sufficient quality to support scientific inference about the target model's internal computation. |
| Required evidence | Convergence with increasing fit corpus size; shard-merge consistency; save/load exactness; apply stability on held-out prompts; and a demonstrated validity criterion tying lens output to a ground truth. |
| Available evidence | `EV-0001` establishes engineering feasibility only. `EV-0005` (Phase 0.5B saturation) is planned but not yet run. |
| Missing evidence | Convergence and apply-stability measurements; any validity criterion whatsoever. |
| Status | **unsupported** |
| Key artifacts | None yet. |
| Limitations | Engineering convergence is a necessary but nowhere near sufficient condition for scientific usability. Top-k overlap is a technical stability statistic and is never semantic evidence. |

---

## CL-03 — Hidden workspace in no-CoT conditions

| Field | Value |
| --- | --- |
| Proposed paper claim | The target model maintains a hidden internal reasoning workspace when visible chain-of-thought is suppressed. |
| Required evidence | A validated lens (CL-02), calibrated task cells with genuine headroom (CL-05), a preregistered causal intervention design, and a result that discriminates the hidden-workspace hypothesis from simpler explanations. |
| Available evidence | None. |
| Missing evidence | All of it. No component of the required chain exists. |
| Status | **unsupported** |
| Key artifacts | None. |
| Limitations | This claim must not be made, implied, or hinted at in any artifact, report, log, or summary produced by this project until every prerequisite above is independently satisfied. |

---

## CL-04 — Parser-v2 formal validation

| Field | Value |
| --- | --- |
| Proposed paper claim | Prospective parser v2 is a validated evaluator, suitable for automatic scoring of model outputs without semantic review. |
| Required evidence | A one-shot locked evaluation against a preregistered holdout passing all mandatory acceptance gates. |
| Available evidence | `EV-0002`. The evaluation was executed once on 2026-07-25 and CLOSED. 32 of 34 mandatory gates passed; `boxed_final_miss` (1/20, limit 0) and `wrong_span` (2/80, limit 1) failed. |
| Missing evidence | Not applicable — the evidence exists and refutes the claim. |
| Status | **contradicted / FAIL** |
| Key artifacts | `reports/phase1_parser_v2_locked_evaluation.md`; decision `2b4386048e57ff847a5f447a0420005db3a2fe53902d0ac91ef66a9511313efb`; closure receipt `992b857aeb1a95ec650a714c99dbdcdec89bd21ee24338e3e2cfe8288cbff051`. |
| Limitations | The 120-case holdout is spent and retired. It may not be reused for a formal result and may not be rescored. Parser v2 remains usable only as a triage tool whose output requires semantic adjudication. |

---

## CL-05 — Model capability headroom

| Field | Value |
| --- | --- |
| Proposed paper claim | Specific task families and difficulty bands leave the target model measurable headroom, making them suitable substrates for ablation and patching experiments. |
| Required evidence | An actual target-model run over a deterministic item sample with registered generation settings, semantically adjudicated labels, and per-cell accuracy with confidence intervals. |
| Available evidence | The 450-item candidate bank exists as a design artifact (`reports/phase1_task_headroom_candidate_bank.md`). `EV-0008` is a frozen n=3 record that is far too small for inference. `EV-0004` (Phase 1.0C calibration) is planned but not yet run. |
| Missing evidence | The calibration run itself. |
| Status | **not yet measured** |
| Key artifacts | `data/phase1_task_headroom_candidates.jsonl`. |
| Limitations | Bank membership is a design decision, not a measurement. No cell may be described as having headroom until it is measured. |

---

## CL-06 — Parser-v3 correction of parser-v2 failure modes

| Field | Value |
| --- | --- |
| Proposed paper claim | Parser v3 corrects the specific failure modes that caused parser v2 to fail its locked gates, without overfitting to the retired holdout. |
| Required evidence | Development-gate results on public fixtures, plus a one-shot evaluation against a newly constructed independent locked holdout. |
| Available evidence | `EV-0006` (development, in progress) and `EV-0007` (new locked set construction, in progress). |
| Missing evidence | The parser-v3 one-shot locked evaluation, which is explicitly out of scope this round. |
| Status | **unsupported** |
| Key artifacts | Pending. |
| Limitations | Parser v3 is being developed with knowledge of which retired cases parser v2 failed. Overfitting risk is structural and must be assessed explicitly. Any parser-v3 result on the retired parser-v2 holdout is development diagnosis and is never validation. |
