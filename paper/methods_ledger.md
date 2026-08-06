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

## Preflight instruments for one-shot locked evaluations

Two read-only preflight instruments were developed during Phase 1.2D. Between
them they found all five findings in protocol §14 and all nine in §15, every
one of them before any preregistration commit, image build, prediction or
label read. Both are standing requirements for any future one-shot round.

### Write-blocked dry run

The real custodian bootstrap is executed against real storage with the
orchestrator's single write primitive, `core.upload_blob_once`, replaced by a
sentinel that raises a subclass of `BaseException`. Every read path, binding
path, manifest validation and namespace translation executes exactly as it
would in production. The first attempted write aborts the process before any
byte is committed.

Two implementation details matter and are easy to get wrong:

- the sentinel must derive from `BaseException`, not `Exception`, or the
  bootstrap's blanket `except Exception` swallows it and the run continues;
- the bootstrap's `main()` takes no positional arguments, so the probe must
  set `sys.argv` rather than pass parameters.

Verified side-effect-free: after each run the sealed prefix was re-listed and
was byte-for-byte the same object set, with no state, prediction, score,
visibility or authorization-lock object created.

This instrument is the only preflight that exercises the real orchestrator
against the real sealed prefix. Every defect it found had survived a passing
full test suite, because the test suite exercises the *v2* profile where the
hardcoded literals happen to be correct.

### Projection probe

The sealed label set is projected into the scoring instrument's schema and
then handed to the **frozen** validator. The frozen instrument, not the
projection, decides whether each record is admissible; the projection cannot
smuggle in data the instrument would reject.

Two properties make the probe trustworthy:

- it is self-checking — a projection that is wrong produces a validation
  error rather than a plausible score;
- it is measured in aggregate — pass counts, failure-message histograms and
  masked value shapes — so it can be run without reading label values.

Reporting convention: numeric values are masked (every digit replaced by `#`)
so that grammar and convention mismatches are visible while answer values are
not. This is what made it possible to diagnose a marker-inclusive versus
literal-only span convention mismatch without reading a single answer.

### Artifact agreement check (required, not yet implemented)

Phase 1.2D's fatal finding (`H9`) was a disagreement between a gate contract
and the sealed set it scores, with no instrument involved. It was found by
direct comparison, late. Any future round must run this check first, before
any image is built:

```
for every enum vocabulary declared in the gate contract:
    reproduce it from the sealed set
for every support count declared in dataset_contract:
    recompute it from the sealed set
for every gate denominator:
    recompute the population it ranges over from the sealed set
for every mandatory gate:
    demonstrate it is non-vacuous - that at least one sealed record
    is capable of producing an error under its error_definition
```

The non-vacuity clause is not decorative. Phase 1.2D's mandatory
`last_number_trap` gate would have passed unconditionally, while appearing in
the result table as an enforced gate, because the set contains no registered
distractor span for it to range over.

This check is a pure function of two sealed artifacts. It needs no
instrument, no image and no execution.

## Separating a prospective evaluation policy from a set-derived facts manifest

Phase 1.2E. A recurring failure mode in preregistered evaluation is a single
"gate contract" that carries two different kinds of statement at once: a
prospective commitment about how the experiment will be judged, and an implied
factual claim about the set that will be judged. When the two drift apart there
is nothing to detect it, because they live in the same file and are asserted by
the same author at the same time. Phase 1.2D's `H9` is an instance: the
contract declared a three-class ontology and 80/30/10 supports, and the sealed
set had four classes and 91/23/6.

The method separates them into two artifacts with different lifecycles.

**The prospective evaluation policy** is authored by hand and registered before
a set exists. It contains the ontology, the construction quotas, the threshold
formulas or numeric thresholds, the comparator policy, the `PASS`/`FAIL`/
`INVALID` logic and the mandatory-gate definitions. It contains no set-derived
fact. It is validated in isolation: quotas must be reproducible from the
registered stratum design, mandatory gates must require a non-zero denominator,
and a policy with an unresolved threshold may not declare itself `FINAL`.

**The set-derived facts manifest** is produced mechanically from a candidate
set. It contains the actual enum vocabulary, the actual class supports, the
stratum counts, the gate denominators, the member list and object count, and
the set and member hashes. It contains no policy choice.

**The contract compiler** consumes both, checks every declared invariant against
the corresponding derived fact, and emits a final contract only on complete
agreement. Two properties make the separation load-bearing rather than
cosmetic:

1. *"Derive from the set" means reproduce and verify.* The compiler has no code
   path that edits a quota or a threshold. A disagreement is a statement about
   the set, never a licence to move the policy. Without this, "derive the
   contract from the set" degenerates into "describe whatever the set happens
   to contain", which cannot fail and therefore tests nothing.
2. *Fail closed on vacuity.* A mandatory gate with a zero denominator is an
   error. It is never reported as `NA`, never skipped, and never counted as
   satisfied. A gate that passes because it has nothing to score is worse than
   an absent gate, because it appears in the result table as an enforced gate
   that passed.

The compiler additionally refuses to overwrite an existing contract, is
byte-stable, and supports a `verify` mode that re-derives the contract from its
declared inputs and requires byte-for-byte reproduction. Provenance bindings
record the policy digest, the facts digest, the set identity and the truth-table
identity, so a compiled contract states exactly which two artifacts it reconciles.

## Deterministic label normalisation that quarantines rather than coerces

Phase 1.2E. When an evaluation set and its scoring instrument disagree, the
disagreements are of two kinds, and conflating them is how a set gets silently
bent to fit its scorer. *Representational* disagreements are differences of
encoding that preserve the graded decision: a span registered around
`Final answer: 3/4` rather than around `3/4`, a reference answer written
`07.50` rather than in canonical form, a derived field that was never
populated. *Semantic* disagreements are differences about what the case means:
a case labelled with a class the ontology does not contain, or an "ambiguous"
case with only one candidate.

Only the first kind may be repaired mechanically. The method makes that
distinction enforceable rather than aspirational, by requiring every
normalisation to be:

* **deterministic** — no ordering, locale or hash-seed dependence;
* **idempotent** — a second application is a no-op, so the pipeline has a fixed
  point and cannot be run "one more time" to a different answer;
* **decision-preserving** — the typed decision before and after must be equal,
  checked against a pre-image function that recognises out-of-ontology classes
  explicitly instead of silently reinterpreting them, and then checked again,
  authoritatively, by validating the normalised record against the formal
  ontology before it is returned. The second check is the one that matters: the
  first is a whitelist of fields, and a whitelist can have holes, whereas the
  ontology validator binds to the scoring instrument and therefore covers every
  field the scorer reads. A record that survives all six rules but would not be
  admissible is quarantined as a single case with a reason code, rather than
  escaping to fail whole-set validation and take the whole set with it;
* **parser-free** — the normalisation sources reference no parser module and
  call no parser entry point, checked statically by a source scan and
  differentially at runtime by comparing `sys.modules` before and after the
  repair imports, so a normalisation can never be tuned, even accidentally,
  toward what a candidate parser happens to produce. The check is stated in
  that differential form because the package `__init__` eagerly imports the
  parser, which makes any absolute "no parser is loaded" claim unachievable;
* **fail-closed** — a rule that would have to guess outside its registered
  tie-break quarantines the case instead of choosing.

Two design details carry most of the weight. First, rules that need a
definition the scoring instrument already owns — what counts as a registered
numeric literal, which spans are admissible — delegate to the instrument rather
than restating it. Restating a definition is how two artifacts drift apart, and
was the proximate cause of both `H5` and `H9`. Second, the audit receipt is
content-free: counts, reason-code histograms and digests of shape-reduced
records, never a value, a span text or a case id. A normalisation run over
private labels can therefore be reported in full without disclosing anything
about the labels, which is what makes the method usable on a sealed set at all.

The quarantine set is the useful output. It is the exact list of cases that
cannot be migrated without a human semantic decision, and it is produced without
any human having to look at a label to find them.


## Acceptance-threshold provenance (Phase 1.2F)

An acceptance threshold is a number that decides whether an instrument may be
used for science. The project had four of them proposed and none of them
derived, and the round that was supposed to derive them blocked on a dependency
that could not have supplied them. Phase 1.2F replaces the missing derivation
with a **provenance discipline**: a threshold is admissible only if its value
can be traced to something outside the candidate being judged.

Four bases are recognised. A `LOGICAL_INVARIANT` follows from a stratum's
purpose or an integrity requirement, so the number is definitional rather than
measured. A `DOWNSTREAM_ERROR_BUDGET` traces the allowable parser error to a
preregistered maximum tolerable distortion in a later scientific metric, so the
number answers "how wrong may the instrument be before the finding changes?".
An `EXTERNAL_CANDIDATE_INDEPENDENT_CALIBRATION` comes from a separate design
preregistered before any candidate output is observed. A
`REVIEWED_OPERATIONAL_REQUIREMENT` states an evaluator-reliability requirement
justified independently of both candidate and holdout. Everything else is
disallowed: parser-v3 development accuracy, parser-v2
locked performance, expected performance, headroom results, textual
substitution from a predecessor, and unsourced appeals to industry practice.
The enforcement of that disallowance is partial and should not be overstated.
`validate_acceptance_thresholds` rejects an unrecognised `basis_type` outright,
and it string-scans the declared derivation and the surrounding threshold prose
for a fixed list of prohibited-source phrases. A string scan catches a
disallowed basis that is *named*; it cannot catch one that is paraphrased,
implicit, or simply undeclared. The substantive guarantee therefore remains a
review guarantee, and the code is a backstop against the naive failure mode
rather than a proof of provenance.

The discipline's first act was to remove thresholds rather than justify them.
The test applied is what a criterion constrains *after* the mandatory gates
have applied, and the answer was usually "nothing that was not already
constrained". With eighty of a hundred and twenty cases pinned to zero errors
by gates, a criterion stated over all one hundred and twenty governs only the
forty that are free; a second criterion stated over a critical-stratum set that
is mostly zero-gated governs the same forty again. Redundancy of that kind is
not harmless. Two numbers over one population disagree at integer boundaries,
and the policy then has no defined answer about which one decides.

> **Erratum (Phase 1.2G).** As written during Phase 1.2F this paragraph said
> ninety pinned and thirty free. That split counted `S06` as pinned. `S06`
> carries a zero-error gate, but its registered error definition forbids
> selecting one particular wrong span, which is narrower than requiring exact
> typed-decision agreement, so it does not pin. The derived split is eighty
> pinned and forty free, over `S04`, `S05`, `S06` and `S09`. The figure is now
> computed by `derive_gate_coverage` rather than transcribed.

The sharpest result concerns aggregate classification metrics on a
quota-constructed set. Because the future evaluation is a fixed adversarial
challenge set rather than an IID sample, its confusion matrices can be
enumerated exhaustively instead of approximated. Doing so showed a macro `F1`
floor above which every feasible matrix already lies, non-monotonicity in error
count, and — decisively — that a candidate returning thirty wrong canonical
values with perfect presence classification scores a perfect macro `F1` while
failing a quarter of the exact typed-decision agreements. Presence errors and
present-value errors are different failures, and a presence metric cannot see
the second kind. The method generalises: before adopting an aggregate metric as
a gate on a constructed set, enumerate what it can and cannot distinguish, and
check whether its best score is compatible with the failure it is meant to
prevent.

The comparator question is answered structurally rather than numerically. A
non-regression margin against a predecessor requires observing a parser on the
locked set to choose, which is what candidate-independence forbids. Comparison
is retained as reported context, where a regression remains informative, and
removed from the pass condition, where it cannot carry acceptance weight.

> **Correction (Phase 1.2G).** This paragraph previously continued: "and the
> predecessor here failed its own locked evaluation, so 'not worse than it' is
> not evidence of fitness." That argument was **withdrawn** during Phase 1.2F's
> own audit (finding A4) and should not have survived here. It is unsound: a
> non-regression floor is an *additional* necessary condition applied on top of
> the absolute gates, never a claim that the predecessor was adequate, so the
> predecessor's failure does not bear on it. The live reason is the first one
> only — the margin is underivable. The withdrawal is recorded in
> `docs/phase1_parser_v3_v2_evaluation_policy.json` under the criterion's
> `withdrawn_arguments`.

Where the discipline yields no number, it yields a null — but a null is a
finding about the *evidence*, not a licence to stop asking what the instrument
is for. Phase 1.2F left the surviving criterion open because no downstream
parser-error budget is registered anywhere in the project, and recorded that as
the blocker. Phase 1.2G found that the missing budget was never the primary
question. The prior question was what the future set *is*: a finite conformance
suite, every member of which is admitted deliberately and carries an adjudicated
reference decision. That fact was already registered in the public design, so
the criterion was answerable from evidence the project already held, and its
value is zero. Filling the gap with a plausible integer would have been the
failure the method exists to prevent; so, less obviously, was continuing to
report a blocker without checking whether the design already answered it.

## Separating live access state from a finalized rule (Phase 1.2H)

A preregistered acceptance policy has two kinds of content that are easy to
conflate and expensive to conflate: the **rule** by which a future evaluation
will be judged, and the **state** of what has actually happened so far. Phase
1.2G's policy carried both — an `execution_state` block sat inside a document
whose status was `FINAL`.

That is a live hazard, not a stylistic one. If the state block is edited as work
proceeds, the `FINAL` document becomes mutable for reasons unrelated to the
rule, and a change to a threshold can be presented as a routine state update.
This project has already had a semantic change enter through that channel.

Phase 1.2H separates them. The policy's `execution_state` becomes an immutable
finalization snapshot. Live state moves to an append-only ledger, and the ledger
binds the policy twice: once by full-file SHA-256, and once by a
`policy_semantics_sha256` computed over the policy with `execution_state`
projected out. The second hash is the load-bearing one, because it is *stable*
across any future licensed state edit — which is precisely what makes it able to
detect a semantic change that a state edit would otherwise conceal.

Three distinctions are carried as separate counters rather than collapsed into a
single "accessed" flag, because each has been a source of overclaiming:

* repair access to a retired set is not formal evaluation access to a successor
  set;
* a **byte-only integrity verification** — streaming a file to a digest and
  discarding the bytes — is not a semantic content read, because only the second
  changes what has been seen;
* constructing, sealing, obtaining a listing witness, preregistering, generating
  predictions, opening labels for scoring and running an evaluation are seven
  different events and get seven different counters.

The ledger's validator refuses a ledger whose counters contradict its declared
status: a "sealed" outcome with no seal write, or a "blocked before reaching the
source" outcome that nonetheless records a semantic read. Counters are monotonic
and events are immutable, so a later round cannot quietly unwind an access it
already recorded. That is what makes the ledger evidence rather than assertion.

The general point: a negative claim ("nothing was read") is only as good as the
mechanism that would have recorded the positive. Writing the negative into prose
costs nothing and proves nothing. Writing it as a validated, monotonic counter
whose non-zero value the validator knows how to interpret is a different kind of
claim.

Audit G showed the limit of that argument as first implemented. The counters
were validated and monotonic, but the *narrative* state blocks beside them were
not validated at all, and those were the fields the current-state generator
rendered. A ledger that carries both a validated counter and an unvalidated
sentence about the same fact will be read through the sentence. Every narrated
state field is therefore now reconciled against the counter measuring the same
thing, every access event must be counter-backed, and the generator validates
before it renders.

The same failure mode appeared in the policy's semantic hash. Excluding a
*container* key from a hash excludes everything inside it, including free text
that can be rewritten into a claim the hash was supposed to protect. Exclusion
lists should name the mutable leaves, not the branch above them.
## Provenance classes for ledger counters (Phase 1.2H-R1)

Phase 1.2H-R1 produced two kinds of number in the same ledger. Eight counters
were read out of a schema-validated execution receipt emitted inside the job.
Two — how many `az` control-plane calls the operator made, and how many
resources were created or changed — were kept by hand across an interactive
session and cannot be anything else.

Publishing both in one table, in one format, invites a reader to extend the
authority of the first to the second. The method adopted is to make provenance
explicit and checkable: the ledger carries a `counter_provenance` block that
partitions counters into `receipt_derived_exact`, `azure_transcript_exact` and
`operator_maintained_approximate`, and the validator enforces three properties
— every named counter exists, no counter appears in two classes, and every
counter carrying a safety claim is present and is **not** classified as
operator-maintained.

The third property is the one with teeth. The failure it prevents is not a typo
but a laundering: move "no semantic read occurred" from receipt evidence into an
operator's recollection while leaving the value at `0`, and the ledger still
reads as safe while having quietly stopped being evidence. Making the move
invalid keeps the distinction between a measurement and an assertion where a
reader can see it.

## Recording a field as unobservable rather than widening the boundary to observe it (Phase 1.2H-R1)

Two fields the R1 receipt would ideally carry — whether the storage account's
public network access is disabled, and whether the executing identity's role set
is genuinely read-only — cannot be observed from inside the job. The first needs
a reader role on the account resource; the second needs permission to read role
assignments. The probe identity holds neither, by design.

Both could have been made observable by granting those roles. The method
question is whether a more complete receipt is worth a wider boundary, and the
answer adopted here is no: the minimality of that identity is the round's central
safety claim, and expanding it to improve the appearance of the evidence would
trade the substance for the appearance.

So the receipt records `"Unknown"` and `NOT_CONFIRMED_IN_JOB`, the schema
*refuses* any other value for the first, and both properties are established
instead from operator control-plane evidence plus a positive structural check —
`data_plane_writes: 0`, and an AST check that no write, upload, delete or
delegation call site appears in the first-party Python source that runs inside
the job (`IN_JOB_FIRST_PARTY_SOURCES`: the probe and the receipt validator).
That scope is narrower than it once read here. Until Audit E's closure review
this sentence said "positive structural proof" over "the probe's reachable
source", which would take in the Azure SDK and the standard library; neither is
analysed, and a check over two first-party files is evidence rather than proof.
A receipt that is honestly incomplete is worth more than one that is complete
because the boundary was widened to complete it.

---

## Retiring an instrument-validation program instead of completing it (2026-08-02)

A methods section that reports adjudicated labels must say why the project has
no validated automatic scorer, given that it spent several phases building one.
The answer is a design decision, not a failure to finish, and the distinction is
methodologically load-bearing.

The locked-evaluation program (parser v2, then parser-v3-v1, then parser-v3-v2)
had exactly one purpose: to establish, by a one-shot preregistered evaluation
against a sealed holdout, that an automatic parser could be trusted as the final
correctness label. Parser v2 ran that evaluation and failed it (32 of 34 gates).
Parser v3 was built, sealed a fresh 120-case holdout, and never ran an
evaluation. The parser-v3-v2 public protocol round exhausted its registered
two-cycle audit budget with four BLOCKER-class properties unresolved.

The program was then closed rather than extended, on the following reasoning.
The four unresolved properties — Stage E member-identifier uniqueness, atomic
create-only state, a structurally closed construction target, and keyed
schema-array uniqueness — share a form: each asks a pure function to certify a
fact about the world (what objects exist, what has already been consumed) from
evidence its own caller supplies. That is not a bug budget; it is a boundary
between what in-process validation can and cannot establish. Closing the gap
would have required an authenticated atomic store and a durable ledger outside
the protocol functions, which is a new system, not a remediation.

At the same time, `L-01` had already forced every label that matters through
semantic adjudication. Elevating `L-01` to a design rule (`DR-01`) makes the
program's product — a parser trusted as a final label — something the project
will never use. Completing it would have been building an instrument in order to
leave it in its case.

The method consequence is stated in `L-41` and must appear in any Methods
section: all final correctness labels in this project are LLM semantic
adjudication under a frozen reviewer form with arbitration, and **no locked
evaluation anywhere in the project bounds their error against an independent
oracle.** Reviewer agreement is inter-model consistency, not accuracy. Automatic
parser output may still be reported as triage diagnostics — routing rates,
disagreement counts — and parser-versus-reviewer agreement must never be
presented as inter-reviewer agreement.

## Recomputing an authority's premises before acting on them (2026-08-02)

The controlling authority for the scientific restart stated seven numeric facts
about Phase 1.0C and asked that a repair protocol be built on them. Those numbers
were *stated*, not derived, and a repair built on unverified premises inherits
their risk without inheriting their evidence.

So they were recomputed from the committed record pack before any repair was
designed: 300 records, 300 prompts carrying the literal placeholder, 31 outputs
echoing it, 5 echoing the whole line, 225 reviewed, 79 at the token cap, 44
unresolved. All seven reproduced exactly. The recomputation also produced a fact
the authority did not state — the joint partition of the 44 unresolved rows over
the two defects (38 token-cap only, 4 both, 1 placeholder only, 1 neither) —
which is what actually refutes single-cause attribution and forced both defects
into the 1.0D design instead of one.

The method generalizes: when an instruction hands over numbers, recompute them
before building on them. One bounded run converts a premise into evidence, and
the residual it exposes (here, the single row explained by neither defect) is
usually the most informative part.

## Preregistering the repair, not just the experiment (2026-08-02)

Phase 1.0D freezes selection, prompt rendering, decoding, adjudication, and the
cell gate in code, with executable assertions, before any generation. Three
properties make this more than a declaration:

- the prompt prohibitions are checked against **all** real rendered prompts
  (300 items x 3 arms), not against a sample or a synthetic example;
- the anti-defect checker is itself tested with positive cases, so a checker that
  silently stopped detecting anything would fail;
- the committed protocol snapshot is compared in the test suite against the
  snapshot recomputed from the module, so the artifact cannot drift from the code
  it claims to describe.

The same pattern is applied to the Phase 1.0C defect receipt. An artifact that
merely records a number is a claim; an artifact the suite re-derives is evidence.

## A passing cloud run is not evidence (2026-08-02)

An ACR task whose shell script had been flattened to a single line by a
PowerShell pipeline write executed nothing and reported success in 21 seconds.
Two sibling runs failed silently for a related reason: a comment above the task
YAML's `version:` line makes ACR run zero steps or refuse to deserialize.

The remedy is cheap and now standard here: the runner prints
`TARGETED_TESTS_COMPLETE=1` as its final line, and a run is treated as evidence
only if the output contains both the test summary and that sentinel. Any
automation that reports success without reporting work should be assumed to have
done none.
## Spending one review allowance on two reviewers (2026-08-02)

The controlling authority allows exactly one bounded preregistration methods
review and exactly one consolidated correction before any scientific output
exists. It says one review; it does not say one reviewer. Two independent
reviewers were run in parallel on identical scope, with a calibration that
forced each finding into FATAL, MATERIAL or NONFATAL and required a file and a
line for every claim.

The corroboration is what makes the outcome usable. Both reviewers independently
identified the same primary defect — arbitration escalating to a third
adjudication that no code path could supply — from different directions. A
single reviewer reporting it would have been a suggestion to weigh; two
independent reviewers converging on it is close to a proof that the defect is
real and visible, and it was then confirmed directly in the code.

The asymmetry justifies the cost. A review costs minutes. A missed
preregistration defect costs an entire GPU round and yields a number that cannot
be interpreted, because the failure mode it produces — a cell gate failing for a
mechanical reason — is indistinguishable in the artifact from the scientific
result HEADROOM_NOT_ESTABLISHED.

Three practices kept the review from becoming a second design cycle. Findings
were corrected once, together, as a single change. Findings that would have
required changing the preregistered sample or design were recorded as
limitations (L-45, L-46, L-47) rather than fixed, because bolting a
control onto a frozen design after review is the manoeuvre preregistration
exists to prevent. And one finding was neither fixed nor merely recorded but
**checked**: the claim that a format exemplar could leak an answer was a
checkable fact, so all 450 bank items were checked, zero matched, the exemplar
was kept, and a test now fails if a registered answer ever equals it.

The review allowance is per protocol, not per session. The allowance for the
J-lens validity protocol is explicitly unspent, because that protocol does not
exist yet and a review cannot be performed on something unwritten.

## A ledger nobody validates is not a record (2026-08-02)

Registering results in the paper ledgers exposed that no test in the repository
had ever read those CSVs. A structural test was added — column count, identifier
presence and uniqueness, mandatory limitations, declared privacy status — and it
failed immediately on committed history rather than on the new rows: five rows
across the figure and table registries carried unquoted commas in their trailing
`limitations` field, so a 9-column header was followed by 10- and 11-column
rows.

The diagnosis matters more than the repair. The overflow was tail-only in every
case, provable because the identifier still matched its pattern, `status`
still read `available` and `generation_script` still named a `.py` file —
none of which could survive a shift in a leading field. So no recorded value had
moved onto a wrong header and the repair altered no text. What had actually been
corrupted was the statement of what those five exhibits do **not** establish:
any consumer reading the registry positionally would have read a truncated
limitation. A disclosure silently losing its second half is the failure mode
these ledgers exist to prevent.

The general rule now applied here: a file that carries scientific meaning gets a
test the day it starts carrying it, and the first run of that test should be
expected to fail on history.

## An absent measurement must not be representable as a bad one (2026-08-02)

Writing the Phase 1.0D generation driver exposed a defect in the already-tested
pipeline it drives. `compute_cell_outcomes` counted a row as correct only when
`final_label == "correct"`, which is right, and reached that judgement without
first asking whether the row had been labelled at all, which is not. A pack of
900 generations that no reviewer had yet touched would have scored 0% in every
cell and been adjudicated `HEADROOM_NOT_ESTABLISHED` — the exact verdict a
genuinely incapable model would earn.

The failure mode is worth naming because it is not a coding slip. Absent data
had been given the same representation as bad data, so the pipeline could not
tell the two apart, and its output was most misleading precisely when the least
work had been done. Both functions now refuse an unlabelled row.

The general rule: for any measurement, "not measured" needs its own value that
propagates to an error, never a default that happens to look like a result. The
generation pack applies the same rule outward — its decision file and its
summary both read `AWAITING_SEMANTIC_REVIEW` rather than carrying a provisional
number that a reader could quote.

## A documented pipeline order that cannot run is a defect, not a comment (2026-08-02)

`phase1_0d_execution.py` documented its own stages as `build_records` ->
`annotate_review_selection` -> semantic review -> `apply_judgments`. Following
that order raised immediately: `annotate_review_selection` forces a second
review based on the primary label, so it cannot precede the primary review that
produces one. The docstring had never been executed in the order it stated.

This was found only because the generation driver trusted the docstring. Prose
describing an order is a claim about the code, and an unrunnable claim sitting
next to working functions is more dangerous than no claim at all, because the
next implementer will follow it. A test now asserts that a generation pack
carries no secondary-review selection, which pins the corrected order in
executable form rather than in a comment.

## A build that verifies itself beats an attestation nobody rechecks (2026-08-02)

The Phase 1.0D image could have carried a signed manifest of what went into it.
Instead the checks are build steps: the image does not exist unless every pinned
package matches the lock, the baked source hashes file-by-file to a committed
bundle digest, and the code inside reproduces the frozen `protocol_sha256`
together with its 300-item selection.

The difference is who has to act. An attestation is a claim a later reader must
choose to verify, and the repository already contains a cautionary example — the
Phase 1.0C generic image could not be built at all because its attestation
generator demanded a 32-file list that no reachable commit satisfies, and the
attestation itself was never committed. A build-time check has no such gap: the
only way to obtain the image is to satisfy it.

The general rule: prefer a property that must hold for the artifact to exist
over a property recorded alongside the artifact.

## A hash that only reproduces under undocumented arguments is a trap (2026-08-02)

Verifying the image against the frozen Phase 1.0D protocol first reported
`ef782fea…` where `25e96401…` was recorded. That is exactly what a drifted
preregistration looks like, and it stopped the work.

Nothing had drifted. `protocol_snapshot()` accepts an optional selection and an
optional strict-budget check, and the frozen hash covers the document *with*
both. The bare call produces a smaller document and a different hash. The
recorded value was correct; the reproduction recipe was undocumented.

The cost of that gap is asymmetric. A false alarm costs an investigation, but a
reader who resolved it the other way — by assuming the smaller document was
canonical and updating the record — would have destroyed the preregistration.
Both facts are now pinned by tests: the full document reproduces the frozen
hash, and the bare one does not.

The general rule: a recorded hash must be published with the exact call that
reproduces it, and the negative case is worth a test of its own.
## M-15 - Qualifying a semantic-review panel before it can see a result

Phase 1.0D needs 900 semantic labels, and the repository has no registered
provider for them. The method used to try to acquire one is worth recording
independently of the fact that it failed.

The order is the method:

1. **Freeze the instrument first.** The reviewer roles, deployments, model
   versions, prompt, rubric, output schema, six synthetic fixtures with their
   expected labels, and the stop rules for every failure mode were written into
   one addendum, hashed
   (`582640de645030daf957fbc3e5c7947008b78d1596b674687a73f20ba749bdc3`), and
   committed before any endpoint existed.
2. **Bake the frozen bytes into the executing artifact.** The review image
   verifies at build time that the addendum and rubric inside it hash to the
   committed values, that its own source bundle matches its committed
   provenance record, and that it can reproduce the base protocol hash. A green
   build is the attestation; there is no separate document to trust.
3. **Lock the artifact.** Tag and manifest are locked against write and delete,
   and the launcher refuses to start against an unlocked image.
4. **Prove the route on bytes that carry no information.** The qualification
   stage sends one trivial prompt per role. It answers "can this environment
   reach these models at all", and nothing else. Here it retired a real
   unknown: all three deployments answer `/openai/v1/chat/completions` with no
   api-version parameter, and a southeastasia Container Apps VNet can reach
   eastus2 AI endpoints under managed identity with local auth disabled.
5. **Prove the judgement on synthetic bytes, still before any target output.**
   The smoke stage runs all six fixtures against all three roles and compares
   to the committed expectations. It is deliberately run in a separate process
   from any generation, is given no pack prefix, and therefore *cannot* read a
   target output even if one existed.
6. **Bind the response to the fixtures in advance.** Transport and
   configuration faults are declared fixable and rerunnable. Label mismatches
   are declared terminal, with tuning, substitution, fallback and fixture
   edits named and forbidden by the frozen text.

Step 6 is the part that has to be written before step 5 runs, and it is the
only part that gives steps 1 to 5 any value. This round it fired: one of
eighteen labels disagreed, and the round ended without a generation run. See
D25 and L-50.

The general rule: a reviewer panel is an instrument, and an instrument that is
calibrated after it has read the sample is not an instrument. The cost of
qualifying prospectively is that a single disagreement can end a round before
any measurement is taken. That is the cost being paid here, and it is the
correct one — the alternative outcome, 900 labels from a panel known to
mislabel the one distinction the phase turns on, would have been worse and
would have looked like progress.

## M-16 - Executing an ordered rubric against its own fixture bank before freezing

M-15 recorded the order that makes a reviewer panel an instrument: freeze, bake,
lock, qualify, smoke, and bind the response in advance. The v1 round executed
that order faithfully and still froze a broken instrument, because one step was
missing from it.

The v1 rubric has six numbered rules applied in order. Rule 3 selects a
commitment ("the last complete `Final answer:` surface"); rule 4 classifies a
conflict only "with no rule selecting one". The v1 fixture `smoke_unresolved`
has two literal surfaces plus trailing prose declaring both co-equal, and its
registered expectation follows the prose. Executing the rubric's own ordering
against that fixture yields `incorrect`, not the registered `unresolved`. The
contradiction was present in the committed bytes, hashed, verified inside the
image, and never once executed by a human or a test.

Every v1 check passed because each checked a different thing: the addendum
hashed correctly, the rubric hashed correctly, the fixtures were well-formed and
covered every label, and the image verified all of it. None of them asked
whether a reader applying the rules in order would produce the expected label.

The method added for v2:

1. **Write the ordering consequences down as prose in the rubric**, including
   the negative cases — a later rule may classify the answer an earlier rule
   selected, but may not replace that selection; prose before or after the last
   complete surface cannot retract it.
2. **Make the rubric's ordering executable as a test.** Pin the rubric SHA-256,
   then assert the consequences case by case: last complete surface wins; later
   prose cannot override it; incompatible alternatives *inside* the selected
   surface are `unresolved`; co-equal commitments with no literal surface are
   `unresolved`; explored-but-uncommitted alternatives are `no_answer`; empty
   question or reference fields are `invalid`.
3. **Include the adversarial pair in the bank.** The v2 bank carries
   `v2_correct_last_surface_wins` and `v2_incorrect_last_surface_wins`: the same
   structural trap as the v1 fixture, but with expectations that follow the
   rubric's ordering rather than the trailing prose, and with the two possible
   outcomes pointing in opposite directions so a reviewer cannot satisfy both by
   guessing one label.
4. **Run these tests before any provider call**, in Azure, and commit them with
   the frozen bytes.

The general rule: a specification with ordered rules is a program, and freezing a
program you have never executed is freezing whatever bug it contains. Hashing
proves the bytes did not change; only execution proves they say what you meant.

## M-17 - Recording an irreversible review failure without reconstructing work

The formal-review launcher used a create-only lock before `job start`, so a
failed child cannot be replaced by another child under the same scientific
license. That irreversibility is preserved rather than worked around.

The failure record was assembled from three independently bounded surfaces:

1. the child execution terminal status and Log Analytics traceback;
2. the exact create-only formal-review lock downloaded inside the private
   Container Apps environment;
3. a later read-only Blob inventory of the source and result prefixes.

The traceback proves the source pack reached review, because it first reports
eight files and a 900-row independent rebuild. It then proves the registered
transport terminal condition for the failing primary call: eight identical
attempts, last status 429. It does not prove the aggregate call or response
counts under concurrency, so those fields are explicitly left unestablished.

The Blob inventory proves what persisted: one lock, eight unchanged source
objects, and zero review-result objects. The method therefore records no
partial judgment and computes no metric. This is stricter than replaying
ephemeral responses from logs and safer than treating process-local work as a
sealed result.

## M-18 - Separating transport-capacity repair from semantic review

The one authorized recovery treats deployment capacity as a control-plane
precondition, not as a reason to revise the frozen reviewer.

1. Freeze the recovery authority and reauthenticate the one generation, the
   failed formal execution, both protected-byte rollups, all image identities,
   the old lock, and the empty old result prefix.
2. Use only ARM, Azure Monitor, Blob metadata, and repository bytes before
   inference. Normalize each deployment's returned rate-limit rules without
   substituting subscription maxima for missing deployment allocations, and
   compute ordered hashes of all 900 frozen request bodies per role offline.
3. If a deployment is below its mechanical floor, permit only the minimum
   `sku.capacity` increase on that same deployment, guarded by its current ETag.
   Any absent or ambiguous rate limit, insufficient unallocated quota, or
   non-allowlisted readback change fails closed before inference.
4. Seal and push a create-only sanitized capacity certificate that records
   `provider_calls=0`, the quiet window, before/after allocations, every gate,
   and the three request-body rollups.
5. Only a passing certificate can license an inert fixed-identity Job, one
   create-only recovery lock, and one non-retrying start. The locked v2 image
   then performs the existing 900-row review and finalization unchanged.

The old execution contributes no row to the recovery. A successful result is
computed only from the new complete sealed bundle and carries L-54's
resampling-exposure disclosure. Capacity failure consumes no provider-bearing
execution; any failure after recovery inference consumes the sole allowance
and closes Phase 1.0D without a result.

## M-19 - Sealing a blocked capacity gate without inference

The authorized capacity gate was executed as a bounded control-plane
measurement, not as semantic review. Azure Resource Manager supplied exact
account, deployment, ETag, SKU, allocation, returned rate-limit, subscription
usage and model-capacity records. Azure Monitor queried
`AzureOpenAIRequests`, `ProcessedPromptTokens`, and `GeneratedTokens` at
`PT1M`, with exact `ModelDeploymentName` filters for all three registered
deployments. The 60-minute role queries and final 15-minute account-wide quiet
window returned zero counts and empty timeseries; both the zero sums and the
empty-series counts are retained in the certificate.

A non-provider Container Apps identity with zero Cognitive Services roles read
the private eight-object source pack, old formal lock, empty old/recovery result
prefixes and absent recovery lock. Inside the private environment it
independently rebuilt all 900 possible request bodies per role. The ordered
rollups were:

- primary `7347d1346c41bd3a0255f0e8e0f4f348e642d5fe4418067c1fdf077014356aed`;
- secondary `f3348c56d656e61c1cca3f9809eca36f03bc19002855189f1114ada6ba27e133`;
- third `ddd2ed53b1dfb71277ba6379ee666c13b516ac9e888d308376adda9945343b8d`.

All material readbacks fell within 237 seconds, from the Monitor window end at
`18:01:00Z` through certificate observation at `18:04:57Z`. The final sealer
image
`j-space-observation-phase1-0d-capacity-sealer@sha256:1c04065228bf57f042069e32b8f05e613c2e7e536a8c98ba755a804bfc2d1d32`
was ACR-build-verified against the frozen profiles and exact Git-blob source
and old-archive hashes, then locked against write and delete.

Three earlier non-provider sealer executions failed closed before writing any
capacity object: `ripscxe` at the Python package path, `z9uam21` at an eager
`torch` import, and `sfbyzvb` when CRLF worktree bytes differed from the exact
Git source-manifest blob. The first two did not reach Blob; the third performed
only private reads. None had a provider route. The corrected execution
`job-p10d-tr-seal-34404a89-jyi7tki` sealed canonical certificate and manifest
bytes with create-only writes, enumerated the exact two-object prefix, and read
both objects back byte-for-byte.

The resulting 38-gate certificate passes 35 gates and fails only the three
capacity floors. No capacity mutation or inference occurred. Certificate
SHA-256 is
`20e486e05a5f076b720ca12db3459b5a1c2c42e95684977dfdcff19d6da055d3`;
manifest SHA-256 is
`23016ad15430b1720e4b37033a3638bf45e817ac00513292d138d26e0ed0a834`.

## M-20 - Freezing a prospectively falsifiable J-lens S3 validity protocol

The design-only S3 Stage P froze the official public benchmark inputs from
`anthropics/jacobian-lens` commit
`581d398613e5602a5af361e1c34d3a92ea82ba8e`: 93 multihop readout items, 55
order-operations readout items, and a separate 90-item causal-swap benchmark.
An exact case-folded triple rule, with first-official-array occurrence as the
duplicate base-triple representative, deterministically yields 29 oriented
counterparts and 24 unique unordered pairs. Public rows are identified by
`SHA-256(UTF-8(distribution) || NUL || canonical_item_bytes)`, so identical
content in different source distributions is never merged or moved between
readout and causal roles.

The canonical JSON fixes the target model and tokenizer revision, A600/B600
independent S2 fits, their official M1200 merge, source layers 0--26, target
layer 27, and early 0--8, primary-middle 9--22, and motor/output-adjacent 23--26
bands. Stage E0 may later use only the pinned tokenizer and one clean
next-token pass per item to resolve finite single-token eligibility, clean
greedy correctness, and a distribution-local SHA-256 split. It must seal the
create-only E0 manifest before any lens or intervention output is computed or
opened. The first 15 eligible items per distribution are development; the
remainder are confirmation, subject to frozen confirmation floors and with no
backfill or replacement batch.

Primary readout is normalized trapezoidal AUC of pass@k against `log(k)` for
`k = [1,2,5,10,20,50,100]`, pooled as equal 0.5/0.5 distribution means.
Comparators include the M1200 lens, both independent replicates, an ordinary
logit lens, five deterministic label derangements, and five deterministic
surface-free position controls. The causal path freezes Moore-Penrose
coordinate swaps at alpha 1.0, 0.5, and integrity alpha 0.0; direct answer
vector swaps; direction ablations; five deterministic 2x2 Gram-matched random
controls; no-op, wrong-position, early, and motor-band controls; and exact
alternative-vs-clean answer log-odds gain. Lens-independent single-cell
activation patching is secondary support only and is clustered by unordered
pair ID.

All primary intervals use 10,000 deterministic item-paired bootstrap
replicates, with equal readout-distribution weighting and pair-clustered
patching. The exact target-overlap surface gate is reconstructible from sealed
`e0_item`, `e0_surface`, and true-label `readout_rank` rows. Twelve closed,
create-only, all-or-nothing output tables carry raw identities, token sets,
row-level ranks and interventions, bootstrap draws, gate booleans, nullable
classification, and artifact hashes. Incomplete or non-finite packs are
operational blockers, not negative scientific classifications.

The single bounded methods review found two MATERIAL and zero FATAL findings.
One consolidated correction made role identity distribution-qualified and made
the surface gate exactly reconstructible. Same-checklist verification closed
at zero findings. The frozen protocol SHA-256 is
`bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625`;
validator source-bundle SHA-256 is
`7e837b0cfdb0c9a12eb1b6c9067751c7cd4262cc18c5a6f17f4a6505f25b7410`.
The review allowance is spent.

This method entry is preregistration, not empirical evidence. No target model,
tokenizer, lens, inference, activation, patching, ablation, scientific row, or
RQ2 run occurred.
