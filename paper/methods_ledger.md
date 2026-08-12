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

## M-21 - Fitting and independently sealing full-layer S2 identities

The full-layer S2 run used the pinned
`deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` revision
`ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`, float16 model parameters,
evaluation mode, `use_cache=false`, and the official retained-graph
Jacobian-lens implementation at commit
`581d398613e5602a5af361e1c34d3a92ea82ba8e`. Each 128-token fit returned
float32 1536 by 1536 matrices for source layers 0 through 26 against target
layer 27.

Before production, an Azure scan of all 1,801,350 rows in the immutable
WikiText train split selected 1,402 disjoint sequences by a frozen SHA-256 role
key: 600 A, 600 B, 200 heldout, and two smoke-only. Selection used exact raw
bytes and token IDs, minimum source length and token count, duplicate rejection,
and symmetric exact prompt-overlap exclusion. It did not inspect model output.

Four independent T4 smoke Jobs compared `dim_batch` 8, 4, 2, and 1 on the same
two smoke-only rows. All returned complete finite matrices, but 8, 4, and 2
failed the prospectively fixed 1e-5 numerical limits against 1. The run
therefore fixed `dim_batch=1` and deterministically split the final
344-sequence increment as 59/59/59/59/59/49.

Production used 18 registered contiguous shards. Thirty-three executions
produced 18 successes and 15 infrastructure failures. Six failed attempts
persisted exact eight-prompt checkpoints and were resumed once under the same
image, source, corpus, shard, and configuration; nine quota-timeout attempts
had no usable checkpoint. The successful states cover every A1--A600 and
B1--B600 contribution once. Because a process can finish work after its last
surviving checkpoint, the exact number of recomputed evaluations is unknown
and bounded at zero through 42.

At 64, 128, 256, and 600 prompts, the official merge was independently
recomputed as the `n_prompts`-weighted float32 matrix mean. A600 and B600 have
equal prompt counts, so M1200 is their 600:600, or 50:50, official merge.
Every merge comparison and lossless save/load comparison had maximum absolute
difference zero. Heldout engineering apply diagnostics covered the exact
Cartesian product of 200 sequences, three lens pairs, and 27 layers.

A distinct read-only verifier re-downloaded and hashed every registered input,
validated the production-attempt state machine, exact sequence accounting,
transport manifests, lens shape/finiteness/provenance, merges, heldout keys,
and closed artifact schema, and then wrote A600, B600, M1200 seals followed by
the S2 manifest. The manifest SHA-256 is
`9d10a4b07a8133b7241ce9067649ebf1de48429cf7c04e0495b4c3fe90e58e47`.
No official S3 benchmark item was tokenized or sent through the model before
this seal.

## M-22 - Executing the frozen lens-free S3 E0 exactly once

After the S2 byte seals were pushed, a distinct E0 image was built from commit
`67b72c29bd3dc6e8707198b16cfac27177664943` over the immutable model
snapshot. Its digest is
`sha256:17d664e13d67d79d99e7bf521bce9b7aefa946d33e25ec5ebe4cc7bc0aeff6cc`;
both tag and manifest are write- and delete-disabled. The four-component E0
source bundle is 117,995 bytes with SHA-256
`95b8cede932e1ed298e5f675075530a8b1560c0aa9049abfa0c6feebf38f9085`.
A read-only image verifier recomputed that identity and all frozen protocol,
schema, and benchmark hashes before the lock.

The create-only lock
`jlens-s3/e0/20260807T081017Z/lock/e0_lock.json` binds the exact image,
source bundle, model and tokenizer revision, three S2 seals, S2 manifest,
93/55/90 benchmark bytes, row order, output schema, and destination. It is
2,561 bytes with SHA-256
`8417ec21a512f51dac094facd3e7769f0d00b8b8ee896a7e11aeb4a7acb44c1b`.
A separate read-only Job rehashed and validated the lock, its local image
bytes, S2 prerequisites, and the one-object prefix before execution. The lock
records zero pre-lock benchmark tokenizer/model operations and authorizes zero
lens operations.

The sole E0 execution used every raw official prompt byte without a chat
template or generated chain of thought. It constructed the pinned tokenizer
once, decoded its 151,665-token vocabulary for frozen surface resolution, and
performed exactly one tokenizer call and one greedy clean next-token forward
pass for each of 238 items. It performed no lens import, load, application,
ranking, activation extraction, intervention, ablation, patching, E1, or E2
operation.

The runtime applied the frozen normalization, complete-surface,
token-boundary, prompt-leakage, target-overlap, single-token, length,
control-position, clean-top-1, and distribution-local split rules. It wrote
`e0_item.jsonl`, `e0_surface.jsonl`, and
`eligibility_split_manifest.json` create-only, then wrote the artifact
manifest last. A separate model-free verifier downloaded the exact five-object
lock/output set, found no partial object, reconstructed every official item,
surface rule, eligibility decision, split, count, and floor, validated every
closed row and the complete E0 pack schema, and exported the exact bytes.

Mechanical eligibility was 79 multihop, 36 order-operations, and 83
causal-swap items. Clean-behavior eligibility was 2, 2, and 5. Because the
frozen split assigns up to the first 15 eligible rows in each distribution to
development, all nine behaviorally eligible rows are development and no
confirmation row remains. The four confirmation counts are therefore all zero
and all four floors fail.

## M-23 - Opening a new study without repairing the terminal study

Study 1 is closed at its exact terminal commit and tree. Its files are not
moved into a new physical hierarchy because many receipts, manifests, hashes,
and reports bind their historical paths. Instead, `studies/study1/` adds a
read-only organizational index, terminal manifest, and asset map while the
original bytes remain in place.

Study 2 begins under a separate namespace and authority. Its bootstrap records
the research question, claim ceiling, three fixed checkpoint identities,
stage order, permitted Stage P operations, and explicit cross-study exclusions
before Stage P implementation exists. The full Stage P prompt is committed and
then bound by a later receipt to the exact bootstrap commit/tree and prompt
hash. This two-commit pattern avoids a document attempting to embed the hash of
the commit that contains itself.

The transition is deliberately model-free. It changes project organization and
future authority only; it creates no empirical observation and appends no row
to the scientific evidence ledger.

## M-24 - Freezing a model-free causal-computation protocol with deterministic banks

Study 2 Stage P freezes two synthetic finite-state families, two balanced
surface templates, four fixed option continuations, exact task and pair
identities, fixed target and controls, a prospective stage machine, and closed
behavioral/mechanistic truth tables before any tokenizer or model operation.
The four public banks are generated by SHA-256 counter mode and independently
reconstructed from primitive fields.

The protocol's primary behavior is one four-option logit vector with zero
generated tokens. Its primary mechanism is donor-to-recipient residual
patching toward the recombinant answer `g_recipient(m_donor)`, which is
distinct from donor and recipient answers and is evaluated against no-op,
same-intermediate, same-answer, random-donor, wrong-position, early-band, and
motor-band controls. Target-only development fixes one layer window that both
controls inherit.

An additive pre-review authority introduces Gate A after Stage T and before
B-C: each family pools 128 target NT compositional development rows and must
reach the exact one-sided alpha .025 threshold of 43 correct rows. The gate can
only open confirmation or close protocol v1; it cannot revise scientific
choices. A failed version requires a new authority, version, and seeds.

ACR QuickRuns generated the exact bytes twice, compared independent hash seeds,
ran 41 focused tests, preserved the 3,537 / 15 / 2 full-suite envelope, and
validated both protected-byte rollups. The single 15-item methods review found
no FATAL/MATERIAL issue and used no consolidated correction. Stage P performs
zero tokenizer, model, lens, activation, probe, patching, provider, or GPU
operation and creates no scientific evidence row.


## Study 2 Stage T tokenizer gate

Stage T resolves the pinned config and tokenizer identity of the three
registered checkpoints and establishes the token-level preconditions the
mechanistic design assumes. It downloads no model weight and creates no
scientific evidence row.

Each checkpoint is acquired at its pinned revision with `trust_remote_code`
disabled, and every resolved revision equalled its pin. All three load
`Qwen2Tokenizer` over the `qwen2` vocabulary, and all three are distinct
artifacts by model id, resolved revision, config bytes, and special-token
inventory (2 for the target, 14 for both Qwen checkpoints).

All 17,408 frozen prompt rows tokenize successfully under all three models, with
no prompt failure code firing. The four option continuations are single tokens
under every model (A=362, B=425, C=356, D=422). All 2,048 mechanistic pairs are
eligible under each model and jointly eligible across all three, with no
eligibility rejection code firing, and the eight selection cells each filled to
128 for 1,024 selected pairs, sorted by ascending `pair_semantic_id`.

The three checkpoints produce identical token IDs on all 17,408 rows, with zero
input-length and zero answer-position mismatches pairwise. Cross-model
mechanistic comparisons therefore operate on the same input token sequences,
which subsumes the exact-alignment precondition the design required. It also
means the tokenizer contributes no differentiating signal between checkpoints,
so any downstream difference must originate in weights rather than in input
representation.

Two ACR QuickRuns with different hash seeds and independent caches produced 13
of 13 byte-identical core artifacts, and the committed bytes are those extracted
from the ACR-produced images rather than locally regenerated. Weight loading was
prevented by an active interlock that replaces every model-loading entry point
with a raising stub before acquisition; the post-run cache contained zero weight
files. Stage T performs zero forward pass, generation, activation, probe,
patching, ablation, lens, provider, or GPU operation.


## Study 2 Stage B-D development execution and Gate A

The complete 384-item development bank was executed under every applicable arm
across the three registered 1.5B checkpoints, producing 3,072 behavioral rows in
18 shards with zero retries. Scoring is a restricted four-way choice among the
fixed option tokens A=362, B=425, C=356, D=422 at the registered final input
position, with `use_cache=False`, `trust_remote_code=False`, `float16`, batch
size 1, and zero generated tokens. No natural-language generation occurred.

Three properties make the numbers auditable rather than merely reported.

First, the row space was pre-registered. A pre-inference seal binding the
3,072-row space, its primary-key digest, the shard-manifest digest, the option
token IDs, twenty frozen input hashes and the byte identity of the computation
module was generated in Azure and published to `main` before any weight was
loaded. The GPU job verified it against the published copy before importing
`torch`, and the shard-manifest digest it later reported equals the sealed value.

Second, tokenization was re-verified at inference time. Every prompt was
re-tokenized inside the execution image and checked against the Stage T sealed
token identity, so a transformers 4.46.3 runtime provably reproduced the token
sequences Stage T sealed under a different transformers major version. A mismatch
would have stopped the shard rather than been silently accepted.

Third, writing and certifying were separated. Aggregation and the Gate A decision
were computed by a model-free finalizer on an image with neither `torch` nor
`transformers` installed, then certified by an independent validator that shares
no writing code path and that recomputes the summaries, bootstrap diagnostics,
feasibility rows and decision from the raw rows. Model-freeness is therefore a
property of the image rather than a promise in the code.

The Gate A rule was frozen before any Stage B-D measurement existed: target model
only, no-tool arm only, depths 2+3 pooled within family for n = 128, an exact
one-sided binomial upper tail under p0 = 0.25 at alpha = 0.025, a family passing
only at X >= 43, and overall passage requiring both families. Controls were run
in full and recorded but have no authority over the decision.

Determinism was demonstrated rather than assumed: the seal reproduced
byte-identically three times across two image digests, and two finalization runs
on two different image digests reproduced all eleven artifact digests
identically. Every committed byte was pulled from the registry by manifest
digest.

## M-25 - Study 2 protocol v1 terminalization and post-hoc re-aggregation

Study 2 protocol v1 was terminalized as a documentation operation after the
scientific measurement had already been sealed. The terminalization ran no model,
constructed no tokenizer, executed no forward pass, and added no evidence row; it
edited only mutable routers, ledgers and interpretation controls, and created a
machine-readable terminal manifest, a terminal handoff, an interpretation erratum,
and one post-hoc diagnostic document. Frozen protocol, schema, banks, thresholds,
seeds, model registrations and stage artifacts were not touched, and their
registered hashes are unchanged.

Two method-relevant corrections were recorded. First, the frozen claim that the
Gate A outcome "is not a measurement artifact" was narrowed: the frozen analysis
excluded execution and bookkeeping artifacts, not interface or construct-validity
artifacts, so the corrected statement is that the data cannot distinguish an
incapable checkpoint from an inadequate interface. The two frozen documents keep
their exact bytes; only the interpretation is controlled, at
`studies/study2/decisions/study2_stage_bd_interpretation_erratum.md`.

Second, one descriptive re-aggregation was computed over already-committed rows.
It reads `studies/study2/stage_bd/stage_bd_behavioral_development_target.jsonl`
(1,002,446 bytes, SHA-256
`9ada004f1c9c25f940e00de7753dd6563e3898153c66099f7b84360aaa8ea34e`) from the
committed blob, verifies that digest, parses each line as JSON, selects rows on
the `arm` and `depth` fields, counts `correct`, and tallies `restricted_prediction`
with the Python standard library. Counts were recomputed from row bytes rather
than copied from any summary or manifest, and every recomputed value matched its
registered expected value with zero discrepancies. The procedure is model-free,
read-only, and reproducible from the same commit.

The resulting document is labeled
`POST_HOC_DESCRIPTIVE_ZERO_AUTHORITY_NOT_SCIENTIFIC_EVIDENCE`. It was not
pre-registered, it is not a hypothesis test, no p-value or interval is computed
or implied, and it changes no decision. It is admissible only as a limitation
(L-89) and as exploratory context for a future, separately authorized protocol
version. Validation of the terminalization used CPU-only ACR runs on committed
bytes; local pytest was not used and would carry no evidential weight.


## M-26 - Model-free derivation of Study 3 interface-calibration design parameters

**Date:** 2026-08-08
**Applies to:** `studies/study3/protocol/interface_calibration_protocol_draft.md`,
`studies/study3/protocol/interface_calibration_protocol_draft.json`
**Status:** Design parameters, not measurements. Draft, not frozen.

Every numeric quantity in the Study 3 design draft was derived by exact,
model-free arithmetic on the Python standard library, before any interface,
checkpoint, task bank or seed exists, and none of it is a measurement. No model was
downloaded or loaded, no tokenizer was constructed, no forward pass or generation
was run, no GPU job or provider call was issued, and no observation of any kind
entered the derivation.

Acceptance thresholds for the pre-registered one-sided exact binomial tests were
computed with `math.comb` as the smallest count whose exact upper-tail probability
under the registered null falls at or below the registered alpha. Gate `I1` uses
H0 p <= 0.90 at n = 192 and alpha = 0.005, giving an acceptance count of 184 and an
exact tail probability of 2.362e-3; the same construction at n = 128 was rejected
during design because its power at a true rate of 0.98 is only 0.885 against 0.984
at n = 192. Gate `I2` uses H0 p <= 0.50 at n = 192 and alpha = 0.005, giving 115.
Gate `I4` uses H0 p <= 0.25 at n = 128 and alpha = 0.001, giving 49 with an exact
tail of 6.161e-4 and power 0.997 at a true rate of 0.50. Power figures are exact
binomial sums, not normal or simulation approximations.

Robustness reporting uses two-sided Clopper-Pearson bounds inverted from the same
exact binomial family; the registered per-cell lower bounds at n = 192 with 184
successes are 0.8952, 0.8901, 0.8872 and 0.8824 for 4, 8, 12 and 24 cells. Label
selection-uniformity acceptance bands are exact central binomial intervals at a
Bonferroni-corrected alpha of 0.005 divided by 4, giving [31, 68] at n = 192,
[71, 123] at n = 384 and [156, 230] at n = 768. The equivalence margin, the
accuracy margin and the robustness margin are registered design choices, not
estimates.

The projected rendering counts in the draft - 2,432 renderings per role per surface
and 68,096 across four roles and four surfaces at development scale - are
combinatorial projections of a design that has not been authorized to run. They
describe work that would be required if execution were later approved, and they
must not be read as work performed.

Because these are design parameters rather than results, they carry no evidence row
and no p-value is reported for any observation. Sample sizes and thresholds remain
open operator decisions (`OD5`, `OD6`); the values above are recommendations with
their power consequences made explicit, not commitments. Validation of the round
used CPU-only Azure ACR runs against committed bytes, including a static structural
instrument that was deliberately not committed; local pytest was not used and would
carry no evidential weight.

## M-27 - Committed model-free design statistics and a negative-mutation design test for Study 3 draft-v0.2

**Date.** 2026-08-08

**Scope.** Study 3 design only. No model, no bank, no seed, no measurement. Every
number below is a proposed design parameter, not a result.

### Why the method changed

Study 3 draft-v0.1 derived its design numbers with an ephemeral script that was
never committed, and named a paired-equivalence criterion without an executable
definition or any verified type-I/power behaviour. The operator review found ten
defects, one of which the ephemeral checker should have caught and did not.
draft-v0.2 therefore commits both the derivation and the checks.

### The committed derivation

`studies/study3/analysis/design_statistics.py` derives every proposed threshold
using only the Python standard library. It has two modes: `--emit` writes
`design_statistics_tables.json`, and `--check` recomputes every table and
compares it value-for-value against the committed file, exiting non-zero on any
mismatch. It performs only declared arithmetic and writes no bank, item, seed,
model output or result artifact.

**Exact binomial gate thresholds.** Retained gates use one-sided exact binomial
tests at the study level. Reproduced values include `n = 192`, `p0 = 0.90`,
`alpha = 0.005` giving an acceptance count of 184, and `n = 192`, `p0 = 0.50`
giving 115.

**The rejected chance null.** draft-v0.1 proposed a chance-level null for the
positive-reference gate `I4`. That is rejected in draft-v0.2: a reference that
merely beats chance cannot demonstrate that a working interface would register
competence. The replacement is an exact binomial competence floor at `p0 = 0.80`.

**Paired equivalence.** The named executable method is the score procedure of
Tango (1998) for the difference in paired proportions, evaluated as two one-sided
tests and combined by intersection-union. The constrained maximum-likelihood
estimate of the discordant cell probability under a null difference `d0` solves

`2n q^2 - [(n12 + n21) - d0 (2n - n12 + n21)] q - n21 d0 (1 - d0) = 0`

and the statistic is

`Z(d0) = (n12 - n21 - n d0) / sqrt(n (2 q~ + d0 (1 - d0)))`.

**Three-way verification, fail-closed.** The implementation is verified before any
table is emitted, and the script exits non-zero and writes nothing if any check
fails:

1. at `d0 = 0` the statistic collapses algebraically to
   `(n12 - n21) / sqrt(n12 + n21)`, McNemar's statistic, which is Tango's
   published special case; the observed maximum absolute deviation is exactly 0;
2. the closed-form constrained MLE agrees with direct numerical maximisation to
   3.4e-09;
3. the normal-quantile routine reproduces 1.959963984540054.

**Exact power and type-I.** Power and type-I are computed by exhaustively
enumerating the trinomial distribution of the discordant pair counts. There is no
simulation and no normal approximation to the sampling distribution. The word
*exact* describes this enumeration and **not** the test: the decision rule is
asymptotic, and the enumeration itself discloses one configuration whose realised
one-sided level is 0.025501 against a nominal 0.025. Because the decision depends
only on `(n12, n21, n)`, the rejection region is enumerated once per `(n, margin)`
and cached.

**Multiplicity.** Two structurally different problems are kept apart. Within one
interface profile the gates form an intersection-union conjunction whose size is
bounded by the level of its components, so no correction is applied. Across
selectable profiles the study would proceed if any one qualified, which is a union
event, so the per-profile level is Bonferroni-divided by the number of selectable
profiles. The never-selectable profile is excluded from that count because it can
never produce a reported success.

### The committed test

`tests/test_study3_design.py` is the single dedicated Study 3 test. It contains a
dependency-free JSON-Schema validator, because `jsonschema` is not in the pinned
lock file and the validation must run in the same clean container as the rest of
the suite. It checks positive structural validity, semantic laws a structural
schema cannot express (applicability against declared non-applicable
transformations, counterbalancing completeness, label-alphabet disjointness from
the answer domain), JSON/Markdown parity on every decision-bearing marker, and
reproduction of the committed statistics.

It also runs a **negative-mutation battery**: each mutation injects a specific
prohibited state - a frozen flag, an authorised flag, a non-zero or injected
operation counter, a selected winner, a selectable never-selectable profile, an
omitted `I4`, an `I4` failure that leaves the interface eligible, an `I5` that
omits a construct, enabled pooling, a resolved blocking decision, a removed claim
ceiling, an accessible confirmation split, a results or bank row - and asserts
that the checks reject it. A companion test asserts that the **unmutated**
document is accepted, so a checker that rejected everything would fail rather than
appear maximally strict.

### What this method does not do

It does not select an interface, does not select or pin a positive reference, does
not fix any blocking threshold or sample size, and produces no evidence row. Its
output is a set of proposals and one negative feasibility finding: at `n = 192`
and a target power of 0.90, the aggregate equivalence margin asserted in
draft-v0.1 is not supported at any tested discordance rate.

## M-28 - Independent re-derivation of the Study 3 design statistics, and a committed review validator with a negative-mutation battery

**Date.** 2026-08-08

**Scope.** Study 3 design review only. No model, no tokenizer, no weights, no
forward pass, no bank, no seed, no measurement. Every number below is either a
property of a published statistical procedure or a proposed design parameter.
Nothing here is a scientific result.

### The independence requirement, and how it was made checkable

M-27 committed the drafting party's own derivation. A review that re-ran that
derivation would establish only that the code is deterministic. So the review
implementation, `studies/study3/analysis/independent_methods_recalculation.py`,
was written from the primary sources with differently structured functions and
different internal names, and it is forbidden to reach the drafting code at all.

That prohibition is enforced twice. The script itself calls
`assert_independence_of_drafting_implementation()` before it computes anything,
parsing its own source and refusing to run if it finds an import of, or a dynamic
load route to, the drafting module. Independently, `tests/test_study3_methods_review.py`
re-parses the script and asserts that it never imports the drafting module, never
uses `exec`, `eval`, `compile`, `import_module`, `__import__`, `load_module`,
`spec_from_file_location` or `module_from_spec`, and never opens a Python file at
all. Opening `design_statistics_tables.json` is permitted and necessary: comparing
against the drafting *output* is the review, whereas reaching the drafting *code*
would be borrowing its reasoning.

### Re-derivation from the primary sources

**Paired score procedure.** Under `H0: delta = d0`, writing `p21 = q` and
`p12 = q + d0`, the constrained maximum-likelihood estimate of `q` is the larger
root of

`2n q^2 - [(n12 + n21) - d0 (2n - n12 + n21)] q - n21 d0 (1 - d0) = 0`,

the null variance of the discordant difference is `n [2q + d0 (1 - d0)]`, and

`Z(d0) = (n12 - n21 - n d0) / sqrt(n (2 q~ + d0 (1 - d0)))`.

The feasible null boundary is `q` in `[0, (1 - Delta)/2]`, equivalently a
discordance rate `2q + Delta` in `[Delta, 1]`. That domain matters: it is what a
four-point grid fails to cover.

**Exact binomial gates.** Rejection regions, exact power, and exact realised
level are obtained by enumeration, never by simulation and never by a normal
approximation to the sampling distribution.

**Multiplicity.** Within a profile the gates are an intersection-union
conjunction, so the size is bounded by the component level (Berger and Hsu 1996).
Across selectable profiles the study proceeds if any one qualifies, which is a
union, so the per-profile level must be divided by the number of selectable
profiles. The review found that the design states the divided level but computes
its components at the undivided one.

### Validation that does not depend on the drafting implementation

Each family carries at least one check with a known answer:

1. binomial all-successes and at-least-one identities, deviation exactly 0;
2. binomial symmetry at `p = 1/2`, deviation exactly 0;
3. the binomial-tail/incomplete-beta identity, 3.34e-14;
4. Clopper-Pearson bounds recovered by inverting the tail, 2.46e-16, and
   monotone in the observed count, deviation exactly 0;
5. windowed enumeration against exhaustive enumeration, deviation exactly 0, with
   total lattice mass 8.37e-14 from one;
6. Tango's statistic collapsing to McNemar's at `d0 = 0`, deviation exactly 0;
7. the constrained-MLE quadratic residual 6.01e-17 and the score residual
   1.53e-14 over 2778 interior and 122 boundary configurations with 0 infeasible;
8. the normal-quantile routine, 6.66e-16.

Agreement with the drafting tables was examined only after these passed, and
every difference was classified as a drafting defect, a defensible alternative
choice, a rounding difference, or an error in the review's own implementation.
Three differences were errors in the review's own implementation and are
disclosed in `docs/run_log.md`.

### What the re-derivation established

The drafting enumeration is correct. The realised one-sided level of `0.025501`
at `n = 192`, `margin = 0.10` was reproduced as `0.025501092`, so the defect lies
in the authoritative JSON's claim that enumeration never exceeds nominal, not in
the enumeration.

Maximising over the full feasible null boundary, rather than over four discordance
values, finds a violation the grid cannot see. At `n = 384`, `margin = 0.10` the
grid rows peak at `0.024727` and appear compliant while the supremum is `0.025073`
at a discordance near `0.478`. Calibrated critical values that restore one-sided
`0.025` over the whole boundary are `z = 1.97269` at `n = 192` and `z = 1.961978`
at `n = 384`.

A complete reviewed-parameter set was computed at the design's own stated
per-profile level `alpha = 0.005/3` and target power `0.90`. Five of six gates are
attainable at an admissible sample size; `I3` at a floor of `p0 = 0.95` is not
attainable at any admissible `n` up to 768.

### The committed review validator

`tests/test_study3_methods_review.py` ships its own JSON-Schema validator because
`jsonschema` is not in `requirements.lock.txt`, and it fails closed: it raises
rather than silently skipping if the schema uses a keyword it cannot enforce, so
a schema cannot be weakened by writing a rule the checker ignores.

Beyond schema conformance it asserts that all 22 registered checklist questions
are answered, that every finding carries a stable identifier, a severity and
evidence, that every candidate inconsistency carries exactly one of the four
permitted statuses, that every operation counter is zero, that no authority flag
is set, that no bank row, seed, result row or model output exists, that no
interface and no model is selected, that `OD2` remains operator-controlled, that
a disposition requiring changes cannot route to freeze or execution, that every
recommended sample size declares its unit, and that the Markdown and the JSON
agree on every decision-bearing field. Artifact identities are read from
committed Git blobs rather than the working tree, so the binding does not depend
on a checkout's line-ending policy.

A 41-case negative-mutation battery corrupts the review one prohibited state at a
time - a non-zero counter, a set authority flag, a selected model, an adopted
`OD2`, an unanswered checklist item, a finding without evidence, a candidate
inconsistency with two statuses, a disposition outside the permitted three, an
acceptance while unresolved items remain, a missing null/alternative set, an
unregistered nuisance optimisation, a dropped work stream - and asserts each is
rejected. A companion assertion requires the unmutated document to be accepted,
so a validator that rejected everything would fail rather than look strict.

### What this method does not do

It does not select an interface, does not select, name, pin, download, tokenize,
load, run, prequalify or substitute a positive reference, does not freeze any
threshold or sample size, does not adopt any operator decision, and produces no
evidence row. Its outputs are an audit, a set of recommendations that are
explicitly not adopted, and one disposition.


## M-29 - Exact-rational binomial design for Study 3 draft-v0.3, retirement of the paired equivalence procedure from every decision role, and independent re-derivation of every planning target

**Date.** 2026-08-08

**Scope.** Study 3 design amendment only. No model, no tokenizer, no weights, no
forward pass, no sequence scoring, no bank, no seed, no measurement, no gate
evaluated on any model. Every number below is either a property of a published
statistical procedure or a proposed design parameter. Nothing here is a
scientific result and nothing here is frozen.

### Why the previous methods entry could not simply be extended

M-28 recorded the independent re-derivation that rejected draft-v0.2. Three of
its six blocking findings were statistical rather than editorial: the `I3`
estimand had no denominator, the per-profile level of Family B was asserted in
prose and implemented nowhere, and the draft asserted that a paired
aggregate-equivalence criterion was conservative when the reviewer's own
enumeration showed it was not uniformly so. A methods entry that added rows to
the existing derivation would have carried those defects forward. This entry
therefore describes a different design, not a corrected table.

### The primary design is exact-binomial with exact rational levels

Every active gate component is a one-sided exact binomial test of
`H0: p <= p0` against `H1: p > p0`, evaluated in each applicable atomic cell
separately. The rejection region is the smallest pass count `x` whose upper tail
`P(X >= x | n, p0)` does not exceed the component level. Levels are carried as
exact rationals throughout. The study-level development screening level is
`1/200`, each per-profile development component level is `1/600`, and each
confirmation component level is `1/200`. The decimal renderings `0.005`,
`0.00166...` and `0.005` appear in tables for readability and are explicitly
declared to be renderings rather than the source of truth, so no rounding of a
level can silently change a critical value.

Components within a profile are combined as an intersection-union test in the
sense of Berger and Hsu 1996 *Statistical Science* 11:283-319: the null is the
union of the component nulls, the alternative is the intersection of the
component alternatives, and rejecting every component at level `alpha` gives a
test of the intersection-union null at level `alpha`. No further within-profile
Bonferroni correction is applied, because applying one would be a second, silent
correction of a family that is already controlled by construction. Across
profiles the denominator is fixed at `K = 3` before any data exists and never
shrinks, so an inactive or eliminated profile does not enlarge the level of the
profiles that remain.

### The `I3` estimand and its unit

`I3` is evaluated over `base_item_contrast_clusters`. Each registered cluster
contains exactly two variants that differ in exactly one registered factor. The
seven `K5` clusters vary content position by `+1`, `+2` or `+3` modulo 4, vary
the index of the correct displayed symbol by `+1`, `+2` or `+3` modulo 4, or
replace the label alphabet. The two `K6` clusters vary the separator rendering
or the instruction rendering. `K5` and `K6` are not crossed and use disjoint
base-item identities, so the number of scored units is a sum over cells rather
than a product over factors.

Three indicators are defined on a cluster. `J_inv` scores one when the emitted
answer is identical across the two variants. `J_cor` scores one when the answer
is correct on both variants. `J_both` is their conjunction and is the primary
gate indicator. A stable but wrong answer scores zero under `J_cor` and
therefore under `J_both`, and a stable but invalid or unparseable answer scores
zero under `J_inv` and therefore under `J_both`. Under a unique ground truth
`J_cor` implies `J_inv`, so the truth table has eight enumerated cases rather
than four, and the implication is registered as an integrity invariant that the
scoring implementation must satisfy rather than as an independence assumption.

### One floor, and no degenerate rejection region

`I3` carries exactly one floor: `p0 = 9/10`, `p1 = 97/100`, target power at
least `9/10`, and `n = 256` clusters per applicable contrast cell. The
`p0 = 19/20` floor that draft-v0.2 also carried is deleted from every active
field. Each active component is checked for degeneracy: a rejection region whose
pass count equals `n` has power `p1^n` against the alternative and no power at
all against any alternative below one, so it is not a hypothesis test. No active
component in draft-v0.3 has that property.

### Retirement of the paired equivalence procedure

The paired aggregate-equivalence procedure is retired from every decision role:
gate, eligibility, selection, confirmation, claim language, equivalence margin,
critical value, discordance grid and conservativeness. The four-point
discordance grid is removed from active verification because a fixed
four-point grid cannot establish a claim about a procedure's size over its
parameter space, and enlarging the grid would only make the same claim harder to
falsify. Paired summaries survive as descriptive quantities only, with no null,
no alpha, no p-value, no critical value, no equivalence margin, no pass or fail,
no rescue path and no ranking weight attached to them.

The reviewer's recalculation of the retired procedure is preserved unchanged as
`studies/study3/analysis/independent_methods_recalculation.py` and
`studies/study3/analysis/independent_methods_recalculation_tables.json`. It is
immutable historical evidence of what the first review computed, and the second
reviewer is asked to adjudicate whether retirement removes the size-control
defect or merely relocates it.

### Units

Every `n` in the protocol, in the tables and in the packet carries a unit at its
definition and at every use. The registered units are base items per atomic cell
for `I1a`, `I1b` and `I2`, base-item contrast clusters per contrast cell for
`I3`, and positive-reference base items per operation-family by depth cell per
candidate profile for `I4`. A rendered row and a scored row are distinct
quantities from a base item and from a contrast cluster, and the unit registry
states that they are never interchanged.

### Independent derivation of the planning targets

The amendment authority supplied the development and confirmation targets as
planning values. `studies/study3/analysis/design_statistics.py` derives every one
of them from the exact rational levels and the registered floors using exact
integer and `Fraction` arithmetic, and `--check` compares its own derivation
against the committed table. The committed design test additionally parses the
script's abstract syntax tree and fails if any planning constant appears as a
literal in it, so a value that was transcribed rather than derived cannot pass.
The derived targets are `x = 244` at `n = 256` for `I1a`, `I1b` and `I3` at
development, `x = 243` at confirmation, `x = 82` at `n = 128` for `I2` at
development and `x = 80` at confirmation, and `x = 224` at `n = 256` for `I4` at
development and `x = 222` at confirmation, with attained power at or above the
`9/10` target in every case.

### Boundary

Nothing in this entry was measured. No model was downloaded, no tokenizer was
constructed, no weights were loaded, no forward pass or sequence scoring was
run, no bank row was generated, no seed was drawn, no interface was selected and
no positive reference was selected. The design is unfrozen and the repairs are
proposed resolved subject to a second independent methods review.

## M-30 - Independent recalculation and review method for Study 3 draft-v0.3

**Round:** Study 3 draft-v0.3 second independent methods review
**Reviewed commit:** `2b36f5321d830ea6f70fff2b7bbca3cb93394046`
**Implementation:** `studies/study3/analysis/independent_methods_recalculation_v0_3.py`
**Committed tables:** `studies/study3/analysis/independent_methods_recalculation_tables_v0_3.json`
**Committed validation:** `tests/test_study3_methods_review_v0_3.py`

The method is a CPU-only, model-free, deterministic recalculation of a proposed design.
Every quantity it produces is a proposed design parameter and none is a measurement; the
committed tables carry the status `PROPOSED_DESIGN_PARAMETERS_NOT_MEASUREMENTS`.

**Independence.** The implementation derives its formulas from the reviewed protocol's
registered exact-rational inputs and from English-language primary sources: Clopper and
Pearson (1934) for the binomial sampling model and the exact one-sided tail; Berger and Hsu
(1996) for intersection-union logic; and Tango (1998), Hsueh, Liu and Chen (2001) and Liu
et al. (2002) used only to verify that the previously defective paired procedure is retired
from decision authority. It does not import, execute, dynamically load, copy constants from,
or derive control flow from `studies/study3/analysis/design_statistics.py` or
`studies/study3/analysis/independent_methods_recalculation.py`. The committed test proves
this by AST inspection and a reachable-source-literal scan. The parameter extraction and
every derivation were committed before the reviewing session opened the drafting derived
outputs, and that ordering is recorded in the emitted tables.

**What it computes.** Exact one-sided binomial thresholds, null tails and powers from
integer-only arithmetic over exact rationals, with decimal renderings refused as arithmetic
inputs by a fail-closed parser; a full admissible sample-size sweep under the registered
complete-block balancing divisor; the complete ordered `I3` outcome lattice and the
resulting estimand identification; an independent re-implementation of the registered `K5`
and `K6` construction laws; an independently authored resolver for the sixteen-state
development selection map; gate-bearing cell counts by profile, role, family, depth,
contrast and split; per-cell, gate-family, profile, selection and confirmation power with
both Frechet bounds valid under arbitrary dependence and illustrative values under an
explicitly stated independence assumption; operation projections rebuilt from primitive
counts; and a static audit for surviving retired-procedure decision paths.

**Self-verification.** Every statistical family carries at least one closed-form identity,
exhaustive enumeration or published-example check: binomial masses summing to one exactly,
the complement and reflection identities, the closed form at full success, exhaustive
sequence enumeration for several small `n`, monotonicity of the upper tail in `p` which
justifies evaluating the supremum at `p0`, the Clopper-Pearson boundary closed form, the
Berger-Hsu intersection-union size bound by exhaustive enumeration, the exact Bonferroni
reconstruction `1/600 x 3 = 1/200`, and the Frechet bounds. Agreement with the drafting
bytes is never treated as validation.

**Modes.** `--emit` writes the canonical committed tables; `--check` recomputes and compares
them. No network, model, tokenizer, bank, seed, split, result or prior-evidence access
occurs in either mode.

## M-31 - Derivation method for Study 3 draft-v0.4

`M-30` recorded the independent recalculation that rejected draft-v0.3. This entry records
how draft-v0.4's design parameters are produced.

**Registered inputs, not adopted outputs.** The protocol JSON registers only inputs: the
null and alternative rationals per gate family, the component alphas `1/600` and `1/200`,
the per-stage profile false-negative budget `19/400`, the panel budget `1/200`, the
selectable-profile denominator `3`, the atomic cell structure, the registered target roles,
operation families and composition depths, the `K5` nuisance support, the `I0` fixture
breakdown, the `S4` generated-token bound and the sample-size search ceiling.

**Derivation.** `studies/study3/analysis/design_statistics.py` derives every adopted value
from those inputs with integer-only exact arithmetic over a common denominator: the maximum
gate-bearing cell count over the selectable profiles, the per-cell budget and target, the
profile-stage and end-to-end floors, the minimal sample sizes, the minimal pass counts, the
exact null tails and powers, the sixteen-case `J_joint_correct` outcome lattice, the
sixteen-row profile-eligibility subtable, the total state machine and every operation
projection. Its `--check` mode recomputes all nineteen emitted sections and compares them
value for value.

**Anti-transcription.** No adopted output appears as a reachable literal in the derivation
script. `tests/test_study3_design.py` parses the script's syntax tree, removes docstring
nodes as prose, and asserts that no derived size, pass count, tail, power, cell total or
registered budget rational occurs as a reachable numeric or string constant. The same test
module recomputes the six threshold rows a second time, from the protocol's registered
rationals, with its own independent integer tail arithmetic, and asserts minimality of both
the sizes and the pass counts.

**Bounds.** The union bound is stated and checked to hold under arbitrary dependence between
cells; independence-based products may be reported only as an explicitly labelled sensitivity
analysis and never as a binding bound. The registered least-favourable configuration and the
uncovered indifference region are published with the guarantee.

**Status.** These are proposed design parameters, not measurements. Nothing here is frozen
or authorised, and the method is subject to the third independent methods review.

## M-32 - Independent recalculation and review method for Study 3 draft-v0.4

**Class.** Review method. Not a scientific result and not an execution authority.

**Object.** The third bounded independent methods review of Study 3 draft-v0.4 at reviewed commit
`e865be51da6c7e1a7a4f5b1fcad0efc513bd0f43`.

**Independence.** The method extracts registered design inputs from the authoritative protocol JSON
only, and derives every binding quantity from those inputs and the English-language primary
statistical sources. It imports, executes, dynamically loads and copies nothing from
`studies/study3/analysis/design_statistics.py`, from either prior independent recalculation, or
from either prior recalculation table. The committed test proves this by syntax-tree inspection and
additionally asserts that no derived result appears as a reachable literal constant.

**Ordering.** The extraction, the derivation and the emitted table were committed before any
drafting output was opened; the field-by-field comparison was added in a strictly later commit, so
the ordering is provable from history rather than asserted.

**Arithmetic.** Exact integer and exact-rational only. Binomial tails are accumulated as exact
integers over an exact integer denominator and compared by cross-multiplication, so no floating
point participates in a decision. Decimals are comparison renderings and never policy inputs.

**Derived, not transcribed.** The ordered sixteen-case `I3` outcome lattice and its
`q11/q10/q01/q00` parameterisation; all 34 sampling-cell generator supports, exact weights and
validity predicates; the gate-bearing evaluation-cell census; the arbitrary-dependence error-budget
ladder; unrestricted positive-integer sample-size searches over every integer up to the registered
ceiling; every exact null tail and power; the admissibility and selection graph; the transition
system; and the operation projection from primitive counts.

**Validation.** Agreement with drafting bytes is never used as validation. Each statistical family
carries a closed-form identity, an exhaustive small-case enumeration and a published-example check:
the binomial total-mass identity, the Clopper-Pearson beta duality verified over 220 cases by exact
polynomial integration, the exact one-sided sign-test tails `7/128` at `n = 10` and `5425/262144`
at `n = 20`, and exhaustive enumeration of the union bound, its disjoint equality witness, the
Frechet intersection lower bound and the intersection-union size bound over 1716 finite joint
distributions covering arbitrary dependence.

**Primary sources.** Clopper and Pearson (1934) for the exact binomial tail and the interval/test
duality; Berger (1982) and Berger and Hsu (1996) for the intersection-union result; Boole and
Bonferroni for the union bound; Frechet (1935) for the complementary intersection bound. Source
citation is not treated as validation: whether the registered protocol satisfies each method's
conditions is adjudicated in the review.

**Status.** Proposed design parameters, not measurements. Nothing here is frozen or authorised.


## M-33 - Derivation method for Study 3 draft-v0.5

**Round.** Study 3 draft-v0.5 bounded operator amendment, answering the ten
`S3MR3-*` findings of the third independent methods review. Supersedes the
draft-v0.4 methods record `M-31`; `M-31` and `M-32` are retained unedited as
historical provenance.

**Design change of record.** Contrast applicability is registered per contrast ID
rather than per contrast family. `K6-SEP` varies the separator between a displayed
option label and its displayed option content; the option-less profiles `S2` and
`S3` render neither, so the factor has no referent for them and the cell is
recorded `not_applicable`, which is never a pass, a zero effect, robustness
evidence, a gate-bearing cell or a denominator member. `S2` and `S3` each carry
exactly one genuine `I3` contrast, `K6-INSTR`.

**Statistics.** The gate-bearing evaluation-cell census, recomputed from applicable
contrast IDs, is `S1 = 43`, `S2 = 16`, `S3 = 16`, `S4 = 39`. `m_max` is the maximum
over the selectable profiles and is therefore still 43, attained by `S1`, which the
change does not touch. The per-cell false-negative budget is `(19/400) / 43 =
19/17200`; the per-cell power target is `17181/17200`; the profile stage power
floor is `1 - 43 * (19/17200) = 381/400`; the study end-to-end power floor is
`1 - 19/400 - 1/200 - 19/400 = 9/10`. Development sizes are `413` for `I1a`, `I1b`
and `I3`, `214` for `I2` and `448` for `I4`, with minimal pass counts `389`, `129`
and `383` at component level `1/600`, and confirmation pass counts `388`, `127` and
`381` at component level `1/200`. Every value is re-derived by exact rational
arithmetic; none is preserved for continuity.

**Disclosed limitation of the sizing rule.** The registered sizes are the smallest
unrestricted positive integers meeting the per-cell target, and the target is NOT
monotone above them: within the registered disclosure window it fails again at
421-425 above 413, at 215, 216 and 218 above 214, and at 450-453 and 459 above 448.
Execution must use the exact registered cell size; the registered size never means
"at least n".

**Deterministic rendering surface.** The byte-exact rendering registry and schema
are binding normative inputs. They fix the encoding, newline and normalization
policy, one question-stem template per gate-bearing generator branch, placeholder
and escaping rules, the option-line grammar and ordering, the label alphabets and
separator literals `": "` and `" = "`, the per-`(profile, rendering)` instruction
strings, the answer cue and candidate-surface whitespace convention, the
deterministic tie-break order, the `S4` pre-wrapper boundary, the full
applicability table, and a cryptographic identity for the registry and every
normative template asset.

**Claim ceiling.** A pass would apply only to the registered synthetic generator
distributions and the named interface and checkpoint roles. It would not establish
adequacy on an unregistered substantive task distribution. `UM3-05`, the
external-validity bridge, remains an unresolved future-methods prerequisite.

**Status.** `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`. The
drafting party does not adjudicate its own amendment. `OD2`, `UR-22` and the `RP`
wrappers remain unresolved and the original research question is unanswered.
---

## Study 3-P0 — interface-calibration feasibility pilot, pre-execution registration (2026-08-10)

**Status.** Registered only. No model operation has been performed. This entry
records a methods-feasibility instrument, never a result, and licenses no claim
about any checkpoint.

**Models and revisions.** Three target roles, each pinned to an immutable
revision, with the tokenizer taken from the same repository identity and
revision as the model: `RT` = `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
@ `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`; `RL` = `Qwen/Qwen2.5-Math-1.5B`
@ `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2`; `RI` =
`Qwen/Qwen2.5-Math-1.5B-Instruct` @ `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35`.
`RP` is excluded: no positive-reference candidate is selected, ranked,
downloaded, tokenized, loaded or called.

**Software.** Frozen in
`studies/study3/pilot/p0/container/requirements-study3-p0.txt` and pinned by
immutable base-image digest in
`studies/study3/pilot/p0/container/Dockerfile.study3-p0`
(`pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime`
@ `sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126`).
`trust_remote_code` is `false` and no silent trust-policy expansion is permitted.

**Hardware.** Authoritative CPU validation runs in the registered ACR/container
route on a clean exact-commit checkout. Every model operation is confined to one
Azure containerized GPU job on a T4-class 16 GiB GPU or larger, in fp16, one
checkpoint at a time. No model operation runs on the workstation or in GitHub
Actions.

**Task construction.** Three semantic base-tuple classes drawn from the binding
draft-v0.5 rendering registry: one K2 identity/copy depth-0 tuple, one K3
affine_mod10 depth-1 tuple and one K3 permutation_chain depth-1 tuple. Prompt
bytes are produced by an independent registry-driven renderer that validates
every normative string against its registered SHA-256 asset identity. All 70
rendered members were verified byte-identical to the committed draft-v0.5
fixture renderer.

**Generation settings.** S1 and S2 read restricted next-token logits only, over
the four registered label token IDs and the ten registered mod-10 content token
IDs respectively. S3 rescores on CPU from the already captured S2 logit vector
and adds exactly zero model evaluations. S4 is the never-selectable diagnostic:
role-native wrapper, greedy decoding, `do_sample=false`, `max_new_tokens=4`, no
sampling temperature passed, every completion retained and mapped by the pinned
deterministic parser `study3-p0-s4-parser-v1`, with `unparseable` a first-class
retained outcome.

**Sample size.** Deliberately tiny by construction: 35 contrast cells and 70
rendered members, giving at most 180 non-generative prefill evaluations, 12 S4
generation calls and 210 scored rows across the three roles. The draft-v0.5
`413`/`214`/`448` sizes are **not** used as pilot allocations.

**Random seeds.** None. P0 draws no seed and writes no bank row. All varying
quantities are closed-form functions of the pilot base-item index.

**Exclusion rules.** A genuine token-ID collision marks the specific
role/profile/contrast `INELIGIBLE_TOKEN_IDS` and excludes its model rows; it is
never repaired after observation and never reported as a pass or as robustness.
`K6-SEP` is structurally absent for the option-less profiles S2 and S3. The
complete `study3-p0-only/` namespace is permanently excluded from every later
development, confirmation, P3-Q and external-validity bank.

**Protocol deviations.** None. The round is registered before any tokenizer or
model access, and no prompt, parser, scoring, tokenizer, item, allocation,
checkpoint or dependency may change afterwards in response to an observed
result.

**Claim boundary.** P0 answers only whether the pipeline is runnable. It selects
no interface, sets no threshold, passes no formal gate, estimates no confirmatory
effect, resolves neither `OD2` nor `UR-22`, freezes nothing and answers no
research question. Zero observed discordance would be descriptive, not proof of
invariance. No entry is made in `paper/evidence_ledger.csv`, which remains
byte-identical through `EV-0016`.


## M-30 Study 3 draft-v0.6 first-discriminative-token scoring boundary and the P0-R1 continuation

**Applies to.**
`studies/study3/protocol/interface_calibration_rendering_registry_v0_6.json`,
`studies/study3/protocol/interface_calibration_rendering_registry_v0_6.schema.json`,
`studies/study3/analysis/scoring_boundary_v0_6.py`,
`studies/study3/analysis/scoring_boundary_v0_6_tables.json`,
`studies/study3/analysis/p0_r1_corrected_eligibility_tables.json`,
`studies/study3/pilot/p0_r1/`, `tests/test_study3_rendering_registry_v0_6.py`,
`tests/test_study3_p0_r1_registration.py`.

**Design.** A registration round, not a measurement. It amends the unfrozen
Study 3 candidate from draft-v0.5 to draft-v0.6 to repair the two mechanical
defects the published P0-T disposition disclosed, and it registers one isolated
feasibility continuation on the unchanged frozen pilot corpus.

**Scoring boundary.** `S1` is unchanged: one prefill on the registered prompt
token IDs, next-token logits read at the single position after the prompt,
restricted to the four registered label token IDs. `S2` forms its scoring context
as the registered prompt token IDs followed by the verified common-prefix token,
by concatenation rather than re-encoding, performs one ordinary prefill and reads
the next-token logits only at the ten verified discriminant token IDs. `S3`
reuses that exact vector on CPU with zero model evaluations. `S4` is unchanged
and diagnostic-only.

**Derivation, not transcription.** The common-prefix and discriminant token
identities are recovered from the immutable published P0-T result and the frozen
corpus by a replay-only verifier that performs zero tokenizer encodes and imports
no tokenizer library. It binds 70 published `(prompt, token-ID)` pairs per role to
the exact frozen prompt bytes by SHA-256 and requires each reported token to be
uniquely determined by that evidence.

**Eligibility.** Computed at the narrowest applicable key: candidate-surface
eligibility at role x profile, presentation-pair distinctness at role x profile x
contrast, structural absence at profile x contrast, target-role executability at
role. Reasons are scoped and non-propagating; an ineligible row with an empty
reason list is a validator failure; `not_applicable` is structural absence and is
never instantiated or counted; `S4` can never satisfy target-role executability.

**Sample size.** Unchanged and deliberately tiny: the same frozen 35 contrast
cells and 70 rendered members, at most 180 non-generative prefill evaluations, 12
`S4` generation calls and 210 scored rows across the three roles. The
`413`/`214`/`448` sizes are **not** used as pilot allocations.

**Random seeds.** None. P0-R1 draws no seed and writes no bank row.

**Exclusion rules.** Unchanged in kind. A genuine token-ID collision marks the
specific role/profile/contrast `INELIGIBLE_TOKEN_IDS` with an explicit local
reason and excludes its model rows; it is never repaired after observation and
never reported as a pass or as robustness. `K6-SEP` remains structurally absent
for the option-less profiles `S2` and `S3`. The complete `study3-p0-only/`
namespace remains permanently excluded from every later development,
confirmation, P3-Q and external-validity bank.

**Protocol deviations.** None. The continuation is registered before any
tokenizer or model access, and no prompt, parser, scoring, tokenizer, item,
allocation, checkpoint or dependency may change afterwards in response to an
observed result.

**Counters.** Three views are maintained: the immutable P0-T snapshot carried
forward unchanged, the cumulative non-resettable P0-R1 attempt counters, and an
aggregate view in which additive counters are summed while identity counts are
set cardinalities. `tokenizer_construction_events` is additive and records every
construction, including a reload of an already-seen identity, so a reload can
never be hidden inside the identity cardinality.
`common_prefix_tokens_processed` is reported explicitly, because the extra
teacher-forced token changes token processing rather than the number of
sequence-level prefill evaluations.

**Claim boundary.** draft-v0.6 is a candidate, not a reviewed or frozen protocol,
and every repair is recorded `PROPOSED_RESOLVED_SUBJECT_TO_FINAL_FOCUSED_REVIEW`.
P0-R1 answers only whether the repaired pipeline is runnable. Neither selects an
interface, sets a threshold, passes a formal gate, estimates a confirmatory
effect, resolves `OD2` or `UR-22`, freezes anything or answers the research
question. No entry is made in `paper/evidence_ledger.csv`, which remains
byte-identical through `EV-0016`.
### Study 3 P0-R1 execution readiness (2026-08-12)

The P0-R1 replay gate and model pilot are implemented and bound, and neither was
executed. The live gate verifies the execution lock, the immutable image digest,
the executable code commit and tree, both operative authority identities, the
frozen corpus hashes and the P0-T source hashes; reads the immutable P0-T
artifacts; checks the five factorization conditions and the corrected 39-cell
matrix with 39 eligible cells, zero empty-reason ineligible rows and 11
executable genuine I3 contrasts per role; increments `replay_gate_evaluations`
exactly once with every tokenizer, model, GPU and scoring counter at zero; and
writes canonical result, receipt, counter and disposition bytes before returning
on both the pass and the failure path.

The model executor refuses without an unconsumed execution lock and a byte-valid
replay-pass receipt from the same authorized attempt. It constructs exactly the
three pinned tokenizers, loads exactly the three pinned fp16 checkpoints with at
most one GPU-resident at a time, refuses any reload after observation, and
enforces the exact 60-prefill K2 smoke in code before any extension prefill or
S4 generation. The derived allocation reconciles exactly: 60 smoke prefills, 120
extension prefills, 180 non-generative prefills, 12 S4 generation calls. S2
appends the verified common-prefix token by ID concatenation and reads the
discriminant position; S3 reuses that exact captured vector with zero model
evaluations.

The model-free boundary is structural: every byte that can touch a checkpoint
lives in `studies/study3/pilot/p0_r1/execution/`, so the replay and registration
path remains importable and testable with no model library present.

**Generation-2 result transport and exception safety.** Every P0-R1 result byte
leaves the compute environment by two independent routes: a chunked, ordered,
digest-checked log envelope readable from the container log stream, and a
private object store whose per-run prefix is refused if it is already non-empty
and whose set manifest is written last. Each recovered artifact is verified
against both its recorded sha256 and its recorded length, so a receipt cannot
stand in for the bytes it describes. Completed units are journaled durably as
they are produced, and an exception at any point preserves and exports what has
already been completed rather than discarding it, with the interruption recorded
explicitly in the disposition. Runtime binding compares the sha256 of every
bound source file inside the container against the execution lock before any
work begins, so a substituted file with an unchanged path cannot run. The
replay-gate receipt is injected into the compute job and re-verified there,
which makes the gate a precondition of the run rather than a claim about it.
None of this is exercised against stand-ins alone: the production route is
validated on the real infrastructure by model-free canaries before any model
operation is authorized.