# Methods ledger

Per-phase methods records, written so that they can be lifted directly into a
paper Methods section. Each entry records model and revision, software versions,
hardware, prompt/task construction, generation settings, evaluation method,
sample size, random seeds, exclusion rules, protocol deviations, and artifact
hashes.

---

## Phase 0.5A — real Jacobian Lens T4 feasibility (2026-07-18)

**Model / revision.** `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` at revision
`ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`. Architecture `Qwen2ForCausalLM`,
28 layers, hidden width 1536. Checkpoint metadata dtype `torch.bfloat16`;
runtime dtype `float16`.

**Software versions.** Python 3.11.14; torch 2.12.0; transformers 5.9.0;
huggingface-hub 1.16.1; numpy 2.4.6; CUDA 13.0; cuDNN 92000. Lens package
`jlens==0.1.0` installed from `anthropics/jacobian-lens` at commit
`581d398613e5602a5af361e1c34d3a92ea82ba8e`, Apache-2.0, lock SHA-256
`981e580531e517be1bd1a3fef98ac12822f40d626ba8f365e59973ff258f36ea`. The
official source was installed unmodified; project code supplied only the model
adapter, staged controls, checkpoint bindings, persistence, and reporting.

**Hardware.** One Tesla T4, 16,704,405,504 bytes of device memory, on Azure
Container Apps environment `cae-jspace-observation-sea-vnet2`, workload profile
`gpu-t4` (`Consumption-GPU-NC8as-T4`), job `job-jspace-p05-jlens`.

**Prompt / task construction.** Two generic fit prompts, canonical corpus
SHA-256 `2e421ed4fc806fe1d7e6e09e2b1dfc946295d8f0cf90a844f06e88c312b09290`.
Three sanity prompts for apply. The prompts are generic and carry no answer
labels; they are not drawn from any behavioral or evaluator set.

**Generation settings.** Not applicable — no free-form generation was
performed. This phase computes Jacobians and fits lens matrices.

**Evaluation method.** Staged gates F0–F5 with explicit pass conditions per
stage. Source layers `[6, 13, 20]`, target layer `27`. fp16 model with fp32 lens
serialization.

**Sample size.** 2 fit prompts; 3 apply prompts; 3 fitted Jacobian matrices.

**Random seeds.** Recorded in the run's staged snapshots under
`phase05-jlens-feasibility/20260718T184445Z`.

**Exclusion rules.** None applied; no data were discarded.

**Protocol deviations.** One authorized operational retry after F4 failed on
lens serialization. F2 and F3 were reused from the primary attempt and were not
recomputed. F5 was not run. Both facts are recorded in the result.

**Artifact hashes.** Primary image
`sha256:d3ffaba4fea1d4ee9b03dc5dd369f5b2c5100c84d183f7a729f609d2187bb22f`
(source `86922df02143d191dfa3d9fcf1d92adfaffc0062`); operational-fix image
`sha256:345dde4f70235af3ad2542f79ea1445b66f4f53abe6fd569cd0818b8c4e8db35`
(source `5d4945b6ec477b6da485d19d90daeeb274b919e7`). Both tags and manifests
were write- and delete-disabled; `latest` was not used. The retry was launched
by digest under launcher commit `be997eefbaec410107045dac7c50423f7297c633`.

**Claim boundary.** Bounded engineering feasibility only. This phase supports no
claim about lens quality, hidden reasoning, internal chain-of-thought, an
internal workspace, or J-space.

---

## Phase 1.2A — parser-v2 evaluator set construction and sealing (2026-07-16)

**Model / revision.** Not applicable — no target model was run. Curation,
labeling and arbitration were performed by LLM agents (`gpt-5.6-sol`, reasoning
`max`), which produce operational consensus references, **not** human ground
truth.

**Software versions.** Repository code at the sealing commits recorded in
`docs/thread_handoff.md`. Protocol bundle SHA-256
`5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666`;
acceptance-gate SHA-256
`a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988`.

**Hardware.** Azure Container Apps, environment
`cae-jspace-observation-sea-vnet2`, Consumption profile, 2 CPU, 4 GiB, no GPU,
job `job-jspace-parser-v2-set`, sole execution
`job-jspace-parser-v2-set-ib7uc0e`.

**Task construction.** 12 strata `S01`–`S12`. Development set 60 cases (5 per
stratum); locked set 120 cases (10 per stratum). Presence composition: 40/80
present, 5/10 ambiguous, 15/30 no-answer for development/locked respectively.
Locked critical cases 80; locked material cases 68.

**Evaluation method.** Two-stage reference-blind labeling. Curators A and B each
produced 144 candidates; curator C selected the final 60/120. Stage-1 reviewers
A and B each labeled 120/120 reference-blind, with 57 disagreement rows sent to
an extraction arbiter. Stage-2 reviewers A and B each labeled 120/120, with 0
disagreements.

**Sample size.** 180 cases total (60 development, 120 locked).

**Exclusion rules.** Hard exact, normalized, cross-set template, and historical
overlaps were all required to be zero. Thirty-seven near-duplicate findings were
reviewed and dispositioned.

**Protocol deviations.** None recorded. Final labels 120, unresolved 0, review
seals 7.

**Artifact hashes.** Development set
`bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27`; locked
inputs `2d60483e7f7a2ce1883acca2dcf9a6771f84b54d596ab2e02ed4a39d937c4e3e`;
final labels `44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af`;
locked-label manifest
`aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6`; overall
manifest `f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260`.

**Isolation.** Procedural, hash-audited isolation — explicitly **not** a
security-enforced boundary.

---

## Phase 1.2B — parser-v2 one-shot locked evaluation (2026-07-25)

**Model / revision.** Not applicable. No target model was downloaded, loaded, or
run. No GPU was used. This is evaluator validation, not model evaluation.

**Software versions.** Implementation commit
`654f3bb463fedc33b0638b77fefdd9b2b9d1c9c2`; runtime image digest
`sha256:7ef281187f04692fa17a476c2a3265de051de2300bcd8c3242639b8b4ca6a489`.

**Hardware.** Azure Container Apps, environment
`cae-jspace-observation-sea-vnet2`, Consumption profile, no GPU. Three
executions in total: Stage P `pv2-p-76a4018ffd782aa1e8398853-mqmkmxg`; Stage E
primary `pv2-e-66f225af8c562425fe168b8c-8tgogbi` (rejected pre-label); Stage E
`scorer_infrastructure` retry `pv2-e-f2fcd3f9456d44ff15224f25-l33zhbh`
(succeeded).

**Task construction.** The sealed 120-case locked holdout, 12 strata, 10 cases
per stratum, constructed in Phase 1.2A and never previously read.

**Generation settings.** Not applicable — no generation. Stage P produced 120
parser-v2 predictions and 120 legacy predictions from sealed inputs with
`labels_accessed: false`.

**Evaluation method.** Two-stage, label-secret design. Stage P produces and
seals predictions before any label is read. Stage E opens labels exactly once,
scores against the frozen acceptance gates in
`docs/phase1_parser_v2_acceptance_gates.json`, and closes the holdout.
Thirty-four mandatory gates. Gate denominators are frozen populations, not
observed row counts: `boxed_final_miss` denominator is
`len(boxed_strata) x cases_per_stratum` = 20; `wrong_span` denominator is
`typed_decision_support["present"]` = 80.

**Sample size.** 120 scored rows.

**Random seeds.** Not applicable — the evaluation is deterministic.

**Exclusion rules.** None. All 120 rows were scored; 0 gates were NA or invalid.

**Protocol deviations.** The primary Stage-E attempt was rejected before any
label access because the frozen finalizer's subprocess audit guard blocked a
lazy Azure Identity import calling `platform.platform()` (which shells out to
`uname -p`). It is recorded as an abandoned attempt and consumed the single
authorized `scorer_infrastructure` retry. Two infrastructure-only workarounds
were applied on the orchestrator host, outside the repository: pre-importing
Azure SDK modules before guard activation, and accepting the authenticated label
manifest's additional reviewer/consensus/arbitration metadata. Neither changed
parser bytes, holdout bytes, metric semantics, acceptance gates, or PASS/FAIL
behaviour.

**Artifact hashes.** Full authenticated list in
`reports/phase1_parser_v2_locked_evaluation.md`. Key values: closure receipt
`992b857aeb1a95ec650a714c99dbdcdec89bd21ee24338e3e2cfe8288cbff051`; decision
`2b4386048e57ff847a5f447a0420005db3a2fe53902d0ac91ef66a9511313efb`; ledger
`c8ace06e413f7915188eb2ff3d0ee6f0b857bc8b79a77bce13c8be298c674eeb`.

**Independent verification.** One authorized post-result recomputation from the
sealed ledger and the frozen gate contract agreed on all 38 checks.

**Claim boundary.** Evaluator validation only. No hidden-reasoning,
invisible-CoT, internal-workspace, or J-space claim follows.

---

## Phase 0.5B — J-lens saturation (executed 2026-07-25)

Run `20260725T122016Z`, one Tesla T4, single Container Apps job execution
`job-jspace-p05-jlens-saturation-jxkk7fk`, 12:21:57Z to 12:58:16Z UTC.

Provenance: code commit `408cd00540d5ded2b94ba75fc3616f8702e85465`; image digest
`sha256:a15016dfd025cb4e5dc166638129cc4abf7895cdddbbc1b7638672aab7a3524f`;
protocol hash `b4422756bec723534b78981d79837f3cf9422244f4c1bf40eba205fcce29d32e`;
official lens source `anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`;
target `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B@ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`
in float16 with float32 lens serialization.

Design as executed, unchanged from registration: fit corpus
`data/jlens_saturation_prompts.jsonl` (SHA-256
`41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b`, 25 fit / 10
held-out / 15 reserve, disjoint from all behavioural and evaluator sets); Fit A at
10 prompts fitted directly; Fit B at 25 prompts fitted as shards `[10, 10, 5]` and
merged with the official merge; a direct-subset merge control over 5 prompts;
source layers `[6, 13, 20]`, target layer `27`; `max_seq_len=32`, `skip_first=16`,
`dim_batch=1`.

Measurements: Fit A 528.47 s (52.85 s/prompt), peak reserved 3,829,399,552 B, lens
28,314,032 B. Fit B 1316.87 s (52.67 s/prompt), peak reserved 3,774,873,600 B,
checkpoint 84,942,315 B, merged lens 28,314,032 B. 22 records, 184 metric rows.

Outcome: status COMPLETE, decision **ENGINEERING_IMPROVING**. Stability criteria all
passed (finite rate 1.0; save/load max_abs 0.0; shard-merge vs direct max_abs
2.384e-07 against 1e-05; relative Frobenius 4.862e-08 against 1e-06; apply save/load
consistency 1.0). Convergence criteria failed (relative Frobenius 0.4170 against
0.10; cosine 0.9205 against 0.99). Held-out apply stability: top-k overlap 0.82,
rank correlation 0.9691, logit cosine 0.9794. Zero deviations recorded.

Verification: the artifact pack was retrieved under a temporary prefix-conditioned
`Storage Blob Data Reader` grant that was deleted and verified removed, transferred
with an end-to-end tarball digest check, and `validate_artifact_pack` was re-run
independently against the local copy.

Boundary: engineering feasibility and numerical stability only. The 10-prompt fit
set is nested inside the 25-prompt set, so this measures estimator movement under
added data, not independent replication. Top-k overlap and rank correlation are
technical stability statistics and are never semantic evidence.

---

## Phase 1.0C — bounded capability headroom calibration (preregistered, NOT run)

Preregistered 2026-07-25 with protocol hash
`d778736ff8a2f0c7e82ee14a529abc05afb44ce3c8a9b2b47fd02771c405719d` and frozen
before any data exists. Registered design: deterministic 150-item sample from the
450-item bank (5 task families x 3 difficulty bands x 10 items); conditions
`visible_cot` and `r1_style_thinking` only, giving 300 generations;
`max_new_tokens=512`, `temperature=0.6`, `top_p=0.95`, 1 sample per item/condition,
fixed recorded seed. Parser v2 is used only as a triage tool; final labels require
semantic adjudication because parser v2's formal locked validation FAILED.

Execution status: **BLOCKED, no model was run and no measurement exists.** The main
`Dockerfile` validates a build attestation from `.semantic_audit_build_provenance.json`,
which is gitignored and absent from the worktree, and no calibration image exists in
the registry. The emitted pack therefore carries status `BLOCKED` by design rather
than a fabricated result.

---

## Phase 1.2C — parser-v3 development and new locked-set construction (2026-07-25)

**Track C, parser-v3 development (complete, NOT validated).** Parser v3 was
implemented in a new standalone module with reference-blind extraction, verified by
`co_names`/`co_varnames` inspection so it cannot read a registered answer while
extracting. The frozen parsers are byte-identical to `bc6d7b7`. 65 new public
adversarial fixtures were authored. Results: 9 development gates passed, 1
NOT_APPLICABLE, 60/60 non-regression and 65/65 adversarial typed agreement, against
parser v2's 50/65 on the same fixtures with all 15 differences being v2 fail-closed
recall losses. Protocol hash
`417d9ff5d27b17ce588b7713a1b1072fb32ef21a03fd135e4e339719db28866b`.

**Track D, locked-set construction (constructed, NOT sealed).** 120 cases across 12
strata, 80 critical. Two reference-blind reviewers each covered 120/120
independently; whole-row exact agreement 113/120 pre-arbitration; 7 rows arbitrated;
0 unresolved labels. Zero exact, normalized and numeric-normalized collisions
against the parser-v3 adversarial set and the parser-v2 development set, re-verified
independently by `scripts/crosscheck_parser_v3_locked_set.py`. Protocol hash
`27becc4e7731e6326e1bfbea39dd2734110a131ab307f72253714406ac76fcba`.

**No parser-v3 locked evaluation was executed and the set is not sealed.** The seal
requires the outstanding overlap check against the retired parser-v2 locked inputs
and a write grant that was not created. Parser v3 is not validated and no formal
parser-v3 result exists.
