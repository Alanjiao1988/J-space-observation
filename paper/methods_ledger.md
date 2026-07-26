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

## Phase 1.0C — bounded capability headroom calibration (executed 2026-07-25)

Preregistered 2026-07-25 with protocol hash
`d778736ff8a2f0c7e82ee14a529abc05afb44ce3c8a9b2b47fd02771c405719d` and frozen
before any data exists. Registered design: deterministic 150-item sample from the
450-item bank (5 task families x 3 difficulty bands x 10 items); conditions
`visible_cot` and `r1_style_thinking` only, giving 300 generations;
`max_new_tokens=512`, `temperature=0.6`, `top_p=0.95`, 1 sample per item/condition,
fixed recorded seed. Parser v2 is used only as a triage tool; final labels require
semantic adjudication because parser v2's formal locked validation FAILED.

**Execution status: RUN, pack status `INCONCLUSIVE`.** Run `20260725T170041Z`
executed on Azure Container Apps (`gpu-t4` workload profile, NVIDIA Tesla T4,
parallelism 1, completions 1, platform retry 0) under managed identity over a
private endpoint. 300/300 generations, 0 errors, 30 cells scored. The frozen
protocol executed unchanged: the same 150 item IDs, 300 generation units, task
families, difficulty bands, conditions, generation settings, selection thresholds
and semantic review rules.

**Execution implementation change (protocol effect: none).** The generic
`Dockerfile` validates a build attestation from
`.semantic_audit_build_provenance.json`, which is gitignored, was never committed
on any branch, and is absent from ACR and Blob. It also cannot be regenerated:
`scripts/prepare_semantic_audit_build_context.py` asserts that the tracked
behavior-file set equals a frozen 30-entry `RUNTIME_FILES` list, while the
repository now tracks 63 such files (33 extra, 0 missing), so the generator fails
by construction and always will. A dedicated `Dockerfile.calibration` plus a
deterministic two-part `calibration_build_provenance.json` was introduced instead:
a pre-build section fully determined by the source tree and committed before the
run, plus a post-build section carrying the ACR build ID and image digest and
bound to the pre-build section by its SHA-256. Image
`j-space-observation-calibration:661eff7803d33d3be7be516f76eaf8dcb9e50d4f`, digest
`sha256:c65795e1ab7233d4f2b362d7da339ce8d10de23d83a750947239d155c7ee0ce9`.

**Adjudication.** Deterministic triage flagged 225 of 300 rows under the registered
scope (all parse-invalid, ambiguous, truncated, no-answer, parser/reference
mismatch and candidate-selected-cell rows, plus a 10% deterministic sample of
otherwise-clean rows). A single primary semantic reviewer labelled all 225 in the
registered nine-field form, blinded to the deterministic verdicts. Coverage was
complete: 0 outstanding mandatory rows. **Zero rows met the registered arbitration
trigger** (`deterministic verdict is not null AND primary label is correct or
incorrect AND they differ`), so no arbiter was invoked. That is an absence of
direct contradiction with a deterministic screen, not an inter-reviewer agreement
statistic, and no agreement rate may be quoted from it.

**Outcome.** Final labels across 300 rows: 156 correct, 100 incorrect, 44
unresolved. Two cells were classified `selected_headroom`
(`prompt_grounded_two_hop_factual|hard|r1_style_thinking` and
`synthetic_relation|hard|r1_style_thinking`, both 7/10, accuracy 0.70, Wilson 95%
CI `[0.397, 0.892]`), one high-accuracy control, four difficulty boundaries, three
excluded on quality gates, twenty `not_adjudicated`. The Track B decision is
`INCONCLUSIVE` under the preregistered finalize rule, which makes a pack
inconclusive whenever outstanding mandatory reviews **or unresolved labels**
remain; 44 rows were adjudicated unresolved because the emitted output states no
answer a reviewer could read. **n = 10 per cell is a screen, never a stable
performance estimate.**

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

---

## Phase 0.5C — J-lens disjoint-fit replication (executed 2026-07-25)

Run `20260725T174743Z`, one Tesla T4, single Container Apps job execution
`job-jspace-p05c-jlens-disjoint-nfrnhcr`, 17:49:26Z to 18:13:07Z UTC (23m41s).
GPU access was serialised behind the Phase 1.0C calibration run.

Provenance: code commit `39dc6e09d0ccc2431bd3c695666033b0eeeb302d`; image digest
`sha256:1fdf406fa34d76f228bd8a3570e9564c0a63baadda8e5b3e58f9c0e1b9ad3a37`;
protocol hash `49059665f6c0c720beb712f99941f6cbf3a7a0207bac3e94cc4ac73f5af11980`;
official lens source `anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`;
target `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B@ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`
in float16 with float32 lens serialization. Environment: Python 3.11.14,
Linux-6.6.139.1-1.azl3-x86_64-with-glibc2.36, torch 2.12.0, transformers 5.9.0,
jlens 0.1.0, safetensors 0.7.0, Tesla T4 with 16,704,405,504 B device memory.
A new image was required because the previous J-lens image contained neither the
Phase 0.5C modules nor the amended corpus.

Corpus amendment. Phase 0.5B froze a 50-record corpus of 25 fit, 15 reserve and
10 held-out prompts, so no disjoint 25-prompt sample existed. Ten new
`role=reserve` prompts, `sat-reserve-016` through `sat-reserve-025`, were
appended under the identical registered generation constraints, producing corpus
revision `r2-60`: 60 records, 16,087 B, SHA-256
`dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa`, roles 25 fit
/ 25 reserve / 10 held-out. The amendment is append-only and provably so:
`sha256(bytes[:13452])` is still
`41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b`, so every
prompt Phase 0.5B fitted or applied is byte-identical and in unchanged order and
every Phase 0.5B number remains reproducible. `CORPUS_REVISIONS` in
`src/jspace_observation/phase05_jlens_saturation.py` records the relationship and
rejects the corpus if the prefix bytes ever change.
`scripts/verify_jlens_corpus_amendment.py` re-checks the amendment
deterministically: 84 checks, 0 failed, including zero exact and zero normalised
text overlap against 22,460 candidate strings from four other corpora.

Design as executed, unchanged from registration. 25A = `sat-fit-001` …
`sat-fit-025`, the merged 25-prompt lens produced by Phase 0.5B, **loaded and
never re-fitted**: the job read
`jspace-results/phase05-jlens-saturation/20260725T122016Z/attempts/primary/01-lens-binaries/fit_b_merged_lens.pt`
with its own user-assigned managed identity over the private endpoint and
verified SHA-256
`cb17a634e46e4b219b6dc16b98662ba82e986abbcc154fd650e5a8a5b828949d` and 28,314,032
bytes **before** deserialising it; the runner also recomputed the prompt-order
SHA-256 of the 25 `role=fit` prompts and required it to equal the Phase 0.5B
value. 25B = `sat-reserve-001` … `sat-reserve-025`, disjoint from 25A, fitted as
shards `[10, 10, 5]` and merged with the official merge. 50M = the official
25/25 weighted merge of 25A and 25B. Held-out apply set `sat-heldout-001` …
`sat-heldout-010`, disjoint from both fits. Source layers `[6, 13, 20]`, target
layer `27`, `max_seq_len=32`, `skip_first=16`, `dim_batch=1`.

**No direct 50-prompt fit was performed.** It was omitted by registration because
Phase 0.5B already measured the official merge against a direct subset fit on the
same prompts: `shard_merge_vs_direct_max_abs` 2.384e-07 against a 1e-05 limit and
relative Frobenius 4.862e-08 against 1e-06.

Stages S0 through S7 all completed `success`, with durations 0.30, 36.72, 3.74,
1289.91, 0.06, 0.38, 85.88 and 0.07 s. 25 records, 316 metric rows, 28 paper
rows, 58 figure rows.

Measurements. 25B fit 1289.78 s, 51.59 s/prompt, peak reserved 3,829,399,552 B,
checkpoint 84,942,369 B, lens 28,313,996 B. Transport gates all passed:
`matrix_finite_rate` 1.0 over 18 lens-layer matrices, `save_load_max_abs` 0.0,
`apply_save_load_consistency` 1.0. Replicate criteria both failed:
`25A_vs_25B_relative_frobenius` 0.4831 against a 0.10 limit and
`25A_vs_25B_cosine` 0.8781 against a 0.99 limit. Merged comparisons:
`25A_vs_50M_relative_frobenius` 0.2565246384392308 and
`25B_vs_50M_relative_frobenius` 0.25652465564092874, agreeing to 1.7e-08;
cosines 0.9673 and 0.9710. Held-out apply per pair: top-k overlap 0.7400
(25A/25B), 0.8667 (25A/50M), 0.8533 (25B/50M); rank correlation 0.9555, 0.9884,
0.9886. Per lens: 25A 0.8033 / 0.9719, 25B 0.7967 / 0.9721, 50M 0.8600 / 0.9885.
Overall logit cosine 0.9858, rank correlation 0.9775, top-k overlap 0.8200,
secondary top-k overlap 0.8136. Preregistered merged improvement met on both
statistics: top-k +0.1200 against a 0.02 margin, rank correlation +0.0330 against
a 0.005 margin.

Outcome: status COMPLETE, decision **REPLICATE_IMPROVING**. Zero runtime
deviations from the Phase 0.5C protocol.

Note on serialisation bytes. The S5 round trip re-saved all three lenses at
28,313,996 B, 36 B smaller than the 28,314,032 B Phase 0.5B object, and with
different file digests. This is serialisation container framing under torch
2.12.0 versus the Phase 0.5B environment, not a change of content:
`save_load_max_abs` is exactly 0.0, so the tensor values round-trip bit-exactly,
and 25A's source object was digest-verified before load.

Boundary: engineering numerics only. Both registered replicate criteria failed;
two independent same-size fits differ by 0.4831 relative Frobenius and 0.8781
cosine. `REPLICATE_IMPROVING` states that numerical transport worked and that the
weighted merge lands between its two inputs. Because a weighted mean must lie
between its inputs, the merged improvement is close to arithmetically forced and
is not independent evidence of convergence (`L-18`). Top-k overlap and rank
correlation are technical stability statistics for fitted linear operators and
are never semantic evidence. Nothing here supports any claim about a workspace,
hidden reasoning, an internal chain-of-thought, J-space, semantic convergence, or
any lens being scientifically usable.


---

## Phase 1.2D - parser-v3 prospective one-shot locked evaluation (preregistered e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea)

**Design.** Prospective, preregistered, single-shot evaluation of a candidate
answer-extraction parser against a sealed 120-case holdout. The preregistration
commit precedes every prediction and every label read. The holdout is retired on
first label access regardless of outcome.

**Candidate.** Parser v3,
`jspace-parser-v3-reference-blind-extraction/v1`, parser version
`0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace`, canonical
source digest
`76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9`,
implementation commit `310277bcadd67ca9e77986fc292fae47dc5ceda2`. The registered
digest is domain-separated and canonicalised, not a plain file hash.

**Comparators.** Two streams over the identical 120 cases. Parser v2
(`6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86`) is the
**gating** comparator: the derived contract's non-regression and strict
improvement gates compare parser v3 against parser v2. The legacy parser
(`4b07b91859aca33b51af9c15b08f07026f11b0141f1300fd3f942138b731177e`) is
**reporting-only** and cannot influence the verdict. Where the parser-v2
comparator must be expressed in the frozen comparator schema, a total
deterministic adapter
(`jspace-parser-envelope-to-comparator-decision/v1`) is applied to parser
envelopes only; legacy output is never re-interpreted and then presented as
legacy output.

**Gate contract.** `docs/phase1_parser_v3_acceptance_gates.json`, digest
`2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7`, derived from
the frozen parser-v2 contract
(`a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988`) with
0 numeric threshold changes, 0 metric semantic changes and 0 population
changes; 52 numeric leaves inherited unchanged; verdict `DERIVATION_FAITHFUL`
(`docs/parser_v2_to_v3_gate_contract_diff.json`).

**Execution model.** Two stages from one image digest under different hardcoded
entrypoints. Stage P generates and seals three prediction streams and never
reads a label. Stage E persists a labels-open transaction before the first label
byte, imports no parser, calls no parser, and scores only sealed streams.
Machine-readable runtime record:
`docs/phase1_parser_v3_runtime_profile.json`; derivation evidence:
`docs/phase1_parser_v3_gate_derivation.json`.

**Exclusion rules and deviations.** No case exclusions. No protocol deviation.
One implementation deviation is recorded: a defect in Stage E's parser-import
deny lists and four defects in the three-stream wiring were found by two
independent read-only preflight reviews and fixed **before** preregistration,
prediction generation and label access, with no effect on the formal
evaluation (see L-24).

**Status at this commit.** Preregistered and frozen; **not executed**. 1320
tests pass. No prediction exists, no label has been read, the holdout is
unspent, and no result may be reported (see L-25).

**Label-blindness statement.** Stage P recursively lists the parent prefix and
therefore observes locked-label blob *names*. The manifest publishes
`labels_content_accessed: false` together with `labels_prefix_listed: true`; a
bare `labels_accessed=false` is never published.
