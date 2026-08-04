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

**2026-08-02 — the Phase 1.0D protocol is frozen and preregistered.** The
selection, prompt rendering, decoding, adjudication, and gate rules are fixed in
`src/jspace_observation/phase1_0d_confirmation.py` and recorded in
`docs/phase1_0d_protocol_snapshot.json` (protocol SHA-256
`fd52f2d5…`), verified by ACR runs `cm44`/`cm46` and a full-suite run `cm47`.
The design is 300 items — 20 per family × band cell, `task_ids_sha256`
`0d3fe6ad…` — proven disjoint from the Phase 1.0C item ids, with 1024 new tokens
for the visible control and a provably sufficient 32 for the strict arms. All
300 items × 3 arms were rendered and asserted free of the 1.0C placeholder. **No
generation has been run**, so CL-05 stays `preliminary` on the strength of
Phase 1.0C alone; this note records a frozen design, not a result. The sample
exhausts the bank — see `L-43`.

**2026-08-02 — the frozen protocol was corrected once and refrozen; the hash
above is superseded.** The single bounded preregistration methods review
authorized by the controlling authority was spent on this protocol before any
generation existed, and it found four material defects, the most consequential
being that the arbitration rule escalated a reviewer disagreement to a third
adjudication that no code path could supply. Left uncorrected, a routine
disagreement would have failed a cell gate for a mechanical reason and that
failure would have been reported as `HEADROOM_NOT_ESTABLISHED`. The consolidated
correction moved the protocol SHA-256 from `fd52f2d5…` to
`25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8` and the
arbitration rule from `phase1_0d_arbitration_v1` to `phase1_0d_arbitration_v2`.
The item selection was not touched: `task_ids_sha256` is unchanged at
`0d3fe6ad…`, so the preregistered sample is the same sample. The record is
`docs/audits/phase1_0d_preregistration_review.md`. Still no generation has been
run and CL-05 remains `preliminary` on Phase 1.0C alone.

**2026-08-02 — a Phase 1.0D pass cannot by itself mean retained competence.**
The review's strongest uncorrected point is recorded as `L-45`: the design has no
corrupted-prompt or prompt-echo control, so a correct strict-arm answer is
equally consistent with surface recoverability from the prompt as with reasoning
performed without a visible chain of thought. Adding an arm after the freeze is
exactly the manoeuvre preregistration exists to prevent, so the control was not
bolted on. The consequence is binding on this claim: a Phase 1.0D cell that
passes its gate establishes measurable observable-answer headroom under the
strict rendering and nothing more. `L-46` further records that the structural
arm is rendered from a hand-specified template rather than pinned tokenizer chat
metadata, and `L-47` that any resulting RQ2 pilot is a selected-case pilot.

**2026-08-02 — Phase 1.0D is fully instrumented and has produced no data.**
A locked container image now reproduces the frozen protocol and its 300-item
selection, the generation driver emits a complete artifact pack, and the
repository passes 3067 tests. None of that is evidence for this claim. No
generation has been run, no row has been semantically labelled, and no cell
metric exists; the driver emits `AWAITING_SEMANTIC_REVIEW` rather than a number
precisely so that an unreviewed pack cannot be mistaken for a result. CL-05
remains `preliminary` on Phase 1.0C alone. `L-48` records this in full, and
`L-49` records that the image is permanently undeletable by design.

**2026-08-03 — the semantic-review panel failed its prospective gate, so Phase
1.0D still has no labels.** The missing piece for this claim has always been
`EV-0011`'s open item: 900 rows cannot become a cell metric without section 4.3
semantic labels, and no provider was registered to supply them. A three-model
reviewer panel was therefore frozen, hashed, baked into a locked image and
smoke-tested on six committed synthetic fixtures **before** any target output
existed. It failed: 17 of 18 role-fixture calls matched, and the registered
primary reviewer labelled the `unresolved` fixture `incorrect` — collapsing
"the model never committed to an answer" into "the model was wrong", which is
the exact distinction this claim's headroom estimate turns on. The frozen
`on_label_mismatch` rule made that terminal, the generation run was not
started, and no repair was applied. `EV-0012` records the gate,
`BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION` is the round's final
state, and `L-50` and `L-51` record the consequences. CL-05 is unchanged and
remains `preliminary` on Phase 1.0C alone; a failed instrument check is not
evidence for or against headroom.

**2026-08-03 — the v1 mismatch was an instrument defect, and a v2 instrument is
authorized.** A forensic audit of the frozen v1 bytes (`EV-0013`, `D26`) shows
the rubric and the fixture contradicted each other: the rubric's rule 3 selects
the last complete literal `Final answer:` surface, rule 4 applies only "with no
rule selecting one", and the fixture registers `unresolved` on the strength of
prose placed *after* that surface. The observed `incorrect` is what strict
in-order execution of the rubric produces. The correction to this claim's
reading is narrow but real: the v1 round does **not** show that the registered
primary reviewer confuses an absent answer with a wrong one, so the earlier
statement that it "reproduces the defect the phase exists to repair" is
withdrawn. What remains true is that Phase 1.0D still has zero labels, zero cell
metrics and zero candidate cells, and that CL-05 therefore still rests on Phase
1.0C alone. A single re-frozen v2 instrument is authorized under
`docs/prompts/phase1_0d_semantic_review_v2_execution_prompt.md`; its
conformance bank was authored after seeing the v1 responses, which `L-52`
records as a disclosed loss of instrument-calibration independence. Target-data
independence is intact — no target output exists.

**2026-08-04 — Phase 1.0D generated its frozen bank, but semantic review
failed operationally before a result bundle existed.** The sole generation
execution completed 300 items × 3 arms with zero generation failures, and the
eight-object source pack was independently rebuilt as 900 records and 900
review rows. This advances the available artifact from a preregistration to an
unreviewed target-output pack; it does not advance this claim. The sole formal
v2 review ended as `BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT` after one primary
call exhausted eight byte-identical attempts with last HTTP status 429. The
review-result prefix is empty, so there are zero final semantic labels, zero
cell metrics, zero candidate cells, and no scientific decision. CL-05 remains
`preliminary` on Phase 1.0C alone. `EV-0014`, `D27`, `L-53`, and `M-17` bind
the terminal record and its no-reconstruction rule.

**2026-08-05 — one capacity-gated review-only transport recovery is authorized,
but no new scientific evidence exists yet.** The frozen authority
`docs/prompts/phase1_0d_review_only_transport_recovery_prompt.md` (SHA-256
`dc350039f118cb5931dab08fd65e24ed169757c472898b7dbe8d27eb3ce2f92b`)
preserves the generation and all v1/v2 semantic bytes, permits no inference
before a mechanical capacity certificate passes, and permits at most one new
provider-bearing execution. Authorization is not evidence: CL-05 remains
`preliminary` on Phase 1.0C alone until a complete recovery bundle is sealed.
Any completed result will carry L-54's permanent disclosure that an unknown
subset of requests may have received unpersisted valid responses in the old
failed process before being uniformly resubmitted.

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
