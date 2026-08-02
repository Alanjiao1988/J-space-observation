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
| Required evidence | Convergence with increasing fit corpus size; independent-fit replication; shard-merge consistency; save/load exactness; apply stability on held-out prompts; and a demonstrated validity criterion tying lens output to a ground truth. |
| Available evidence | `EV-0001` establishes engineering feasibility only. `EV-0005` (Phase 0.5B saturation, run `20260725T122016Z`) returned **ENGINEERING_IMPROVING**: transport passed, both convergence criteria failed (relative Frobenius 0.4170 against 0.10; cosine 0.9205 against 0.99), and the comparison was nested rather than independent. `EV-0009` (Phase 0.5C disjoint replication, run `20260725T174743Z`) closed that specific gap by measurement and returned **REPLICATE_IMPROVING**: the numerical transport gates passed (finite rate 1.0, save/load max_abs 0.0, apply save/load consistency 1.0), and both registered replicate criteria **failed** — two independently fitted 25-prompt lenses on disjoint prompt samples differ by relative Frobenius **0.4831** against a 0.10 limit and cosine **0.8781** against a 0.99 limit. |
| Missing evidence | Convergence, which was measured and not reached. Independent-fit agreement, which has now also been measured and not reached. And any validity criterion whatsoever, of which none exists, none is designed, and none is supplied by either run. |
| Status | **unsupported** |
| Key artifacts | `artifacts/phase05b-jlens-saturation/track-a/20260725T122016Z/`; `artifacts/phase05c-jlens-disjoint/track-a1/20260725T174743Z/`; blob prefixes `phase05-jlens-saturation/20260725T122016Z` and `phase05c-jlens-disjoint/20260725T174743Z`; images `sha256:a15016dfd025cb4e5dc166638129cc4abf7895cdddbbc1b7638672aab7a3524f` and `sha256:1fdf406fa34d76f228bd8a3570e9564c0a63baadda8e5b3e58f9c0e1b9ad3a37`. |
| Limitations | Independent replication has now been *attempted and measured*, and the answer is that two same-size fits on disjoint samples disagree substantially. That result moves this claim no closer to supported; it removes an excuse for the earlier nested result rather than supplying evidence. The merged 50-prompt lens met its preregistered held-out apply improvement margin, but a weighted mean necessarily lies between its own two inputs — the two merged-versus-input relative Frobenius values agree to 1.7e-08 — so that improvement is close to arithmetically forced and is not independent evidence of convergence (`L-18`). Two fits give one difference, not a distribution. Engineering convergence and engineering replication are both necessary and nowhere near sufficient for scientific usability, and neither has been reached. Top-k overlap and rank correlation are technical stability statistics for fitted linear operators and are never semantic evidence. |

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
| Available evidence | `EV-0004` (Phase 1.0C Track B calibration, run `20260725T170041Z`) has now **executed**: 300/300 generations on Tesla T4, 0 errors, 30 cells at n=10, all 225 flagged rows semantically adjudicated. Adjudicated labels: 156 correct, 100 incorrect, 44 unresolved. Two cells were classified `selected_headroom` — `prompt_grounded_two_hop_factual\|hard\|r1_style_thinking` and `synthetic_relation\|hard\|r1_style_thinking`, both 7/10, accuracy 0.70, Wilson 95% CI `[0.397, 0.892]`. One high-accuracy control, four difficulty boundaries, three excluded on quality gates, twenty `not_adjudicated`. The 450-item candidate bank exists as a design artifact (`reports/phase1_task_headroom_candidate_bank.md`); `EV-0008` is a frozen n=3 record that is far too small for inference. |
| Missing evidence | A sample size that can support an estimate. n=10 per cell is a screen, so the two selected cells are *candidate* substrates, not cells with established headroom. The pack status is `INCONCLUSIVE`, not `COMPLETE`, because 44 rows were adjudicated unresolved. Adjudication was single-reviewer, so there is no inter-reviewer agreement statistic. |
| Status | **preliminary** |
| Key artifacts | `data/phase1_task_headroom_candidates.jsonl`; `artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/`; blob `phase1-headroom-calibration/20260725T170041Z`. |
| Limitations | **n = 10 per cell is a screen, never a stable performance estimate**, and no cell accuracy from this pack may be quoted as target-model performance. A 7/10 cell's 95% interval spans `[0.397, 0.892]`. Selection is descriptive screening: "this cell showed measurable observable-answer headroom in this run", not "the model can or cannot do this task". 79 of 225 reviewed rows hit the 512-token cap, so truncation reflects the generation budget rather than competence. Single sample per item/condition, so no pass@k or sampling-capability claim. Parser v2 was automated triage only and never produced a final label. This claim licenses nothing about hidden reasoning, an internal workspace, invisible chain-of-thought, or a "J-space". |

**2026-08-02 — Phase 1.0D is authorized to repair, not to replace.** Phase 1.0C
run `20260725T170041Z` (`EV-0004`) remains a valid historical
`COMPLETE_INCONCLUSIVE` record and is not relabelled, deleted, or silently
superseded. Phase 1.0D runs under a new protocol version and a new artifact
namespace on a deterministic confirmation split disjoint from the Phase 1.0C
items. Two separate preregistered generation-profile defects are carried into
its design: the literal `Final answer: <answer>` placeholder that appeared in
every 1.0C prompt, and the 512-token cap. Neither defect alone may be claimed to
have caused all 44 unresolved rows. If no Phase 1.0D cell passes the frozen
count gate, `HEADROOM_NOT_ESTABLISHED` is the scientific result and the gate is
not lowered.

---

## CL-06 — Parser-v3 correction of parser-v2 failure modes

| Field | Value |
| --- | --- |
| Proposed paper claim | Parser v3 corrects the specific failure modes that caused parser v2 to fail its locked gates, without overfitting to the retired holdout. |
| Required evidence | Development-gate results on public fixtures, plus a one-shot evaluation against a newly constructed independent locked holdout. |
| Available evidence | `EV-0006` (development, **COMPLETE**): 9 development gates passed, 1 NOT_APPLICABLE, 60/60 non-regression and 65/65 adversarial typed agreement. `EV-0007` (new locked set, **SEALED** 2026-07-25 at `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/`): 120 cases in 12 strata, 0 unresolved labels, and the last outstanding pre-seal overlap check now executed — 0 exact, 0 normalised and 0 numeric-normalised collisions against the 120 retired parser-v2 locked inputs. Holdout sealed: **yes**, 12 objects, `overwrite=false`, round-trip SHA-256 and ETag verified, `set_manifest.json` written last. |
| Missing evidence | The parser-v3 one-shot locked evaluation. It was explicitly out of scope this round: no parser-v3 prediction exists and nothing was scored. |
| Status | **unsupported** |
| Key artifacts | `artifacts/phase1-parser-v3/track-c/phase1-parser-v3-track-c-20260725T114448Z/`; `artifacts/phase1-evaluator-validation/track-d/20260725T121557Z-track-d-parser-v3-locked-set/`; `artifacts/phase1-evaluator-validation/track-d1/20260725T160340Z-track-d1-parser-v3-seal/`. |
| Limitations | Parser v3 was developed with knowledge of which retired cases parser v2 failed, so overfitting risk is structural. The 65 adversarial fixtures share authorship with parser v3 and are therefore not an independent oracle. All five rule changes are recall-increasing, so precision is unprobed. The holdout is now sealed, which fixes the instrument in time but validates nothing: sealing licenses no accuracy, precision or recall claim. Any parser-v3 result on the retired parser-v2 holdout is development diagnosis and is never validation. Isolation of the retired label and score material during the seal rested on the payload code path and its tests, not on RBAC — see `L-17`. |

**2026-08-02 — CL-06 is withdrawn as a pursuable claim.** The parser-v3
locked-evaluation program is closed (`docs/decisions/parser_v3_locked_evaluation_closure.md`).
The missing evidence — the one-shot locked evaluation — will not be produced,
because `L-01` is now the binding design rule `DR-01` and no automatic parser
may ever be a final label in this project. CL-06 therefore stays permanently
`unsupported`: not refuted, not abandoned as unimportant, but deliberately never
tested. `EV-0006` and `EV-0007` remain valid records of what was built. The
final parser-v2-v2 public audit cycle found four BLOCKER-class properties that
remain defective in the retained code; see `L-42`. No paper may present the
parser-v3 material as a validated or audited protocol.

---

## CL-07 — J-lens functional validity against known intermediates

| Field | Value |
| --- | --- |
| Proposed paper claim | The fitted Jacobian lens reads out known intermediate computations better than an ordinary logit lens and better than norm-matched random directions, and those readouts are causally load-bearing rather than surface leakage from the final answer. |
| Required evidence | A preregistered validity benchmark on the official public evaluation distributions, with eligibility fixed before any lens readout; pass@k readout curves and normalized AUC against log(k) for the merged lens, both independent replicates, the logit lens, and label-permuted / position-shuffled negative controls; causal ablation, coordinate swaps, answer-vector swaps, and lens-independent activation patching with the full control set; item-level paired bootstrap intervals against a frozen classification rule. |
| Available evidence | None yet. `EV-0005` and `EV-0009` are matrix-convergence and transport diagnostics only, and under the controlling authority matrix convergence is explicitly **not** a substitute for functional validity. |
| Missing evidence | All of it. The benchmark is work package S3 and has not been designed, frozen, or run. |
| Status | **unsupported** |
| Key artifacts | None. |
| Limitations | This claim is the primary scientific instrument gate for RQ2. `JLENS_PARTIALLY_VALIDATED` and `JLENS_NOT_VALIDATED` are terminal scientific results under the controlling authority and must not be repaired away by refitting on the confirmatory set, altering thresholds, or restarting evaluator work. Secondary generalization distributions (association, typo, multilingual, poetry) may be reported but can never rescue a failed primary result. |
