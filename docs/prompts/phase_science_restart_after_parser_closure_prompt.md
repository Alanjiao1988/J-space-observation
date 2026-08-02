Take over the scientific mainline in this repository:

repository: https://github.com/Alanjiao1988/J-space-observation.git
branch: main
required starting commit: ea2bce81defe9063bde2be58ada0e747d2a34c03
old parser subproject terminal state: BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE
old failed parser candidate: 423d16a7b486b8c22fa58a733ffa6a03b389f0fe
target model: deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
target model revision: ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562

The operator has made a new project-level decision: the parser-v3 locked-evaluation program is no longer on the critical path. Preserve its terminalrecord exactly, close it as a non-authoritative instrumentation subproject, andresume the scientific work on behavioral headroom, J-lens quality/validity,and the first RQ2 mechanistic pilot.

Save this prompt verbatim at:

docs/prompts/phase_science_restart_after_parser_closure_prompt.md

Commit and push the prompt and the decision record before implementation. Theexecution of this prompt is the operator authorization for the scope below.

1. Controlling decision

The following are now binding design decisions.

paper/limitations_ledger.md L-01 is elevated from a temporary limitationto a project design rule: semantic adjudication is the only authoritativefinal-label path. An automatic parser may be used for triage, routing, ordiagnostics, but never as the final correctness label for a scientificresult.

The parser-v3-v1 and parser-v3-v2 locked-evaluation programs are closed.Do not build a new private holdout, repair a set, deploy a private reviewboundary, run Stage P/E, or seek another parser freeze/audit.

Preserve all old reports, receipts, commits, failed candidates, sealedobjects, counters, and audit findings. Do not rewrite the meaning ofBLOCKED_ON_PUBLIC_PROTOCOL_FREEZE; it remains the correct terminal stateof that parser subproject under its old authority.

The old parser terminal state is not a global scientific-project blocker.Record a new project-level state, SCIENTIFIC_MAINLINE_RESTART_AUTHORIZED,without altering the old terminal receipt.

Existing parser-v3 code, tests, schemas, entrypoints, IaC, and audit toolingremain historical/methodological artifacts. Do not delete them, but do notspend this round improving or re-auditing them. Do not claim that they arepublishable merely because they are elaborate; any later methods paper is aseparate decision.

A negative headroom result, a non-converged lens, or a failed validity gateis a scientific result, not a reason to create another evaluator or auditinfrastructure project.

The previous local prompt namedphase1_2h_rd1_public_protocol_refoundation_prompt.md is superseded and mustnot be executed. If it is already present in the repository, retain it as asuperseded planning artifact and add a short pointer to this decision; do notrun its public-protocol-v2 refoundation.

2. Scope and operating rules

This round is authorized to progress through four scientific work packages:

close the parser subproject and repair Phase 1.0C as a new Phase 1.0D run;

fit a materially larger, full-layer J-lens using a pretraining-like corpus;

execute a preregistered J-lens validity benchmark against knownintermediates and causal controls;

if the headroom and validity gates support it, execute the first bounded RQ2strict-no-CoT mechanistic pilot.

2.1 Azure executes; the laptop edits and orchestrates

The laptop may edit public tracked files, use lightweight Git commands, submitAzure work, and read bounded content-free or public-scientific results. It mustnot run pytest, imports-as-tests, builds, model downloads, inference, J-lensfits, activation extraction, patching, ablation, large scans, or sustainedanalysis. Run those in ACR Tasks, Azure Container Apps Jobs, Azure ML, or anequivalent Azure runner.

T4 use is authorized. A100 or another larger GPU is also authorized when itmaterially reduces wall time or is required for the registered sequence lengthor full-layer fit. Cost must be measured and reported, but cost is not anacceptance gate and must not be cited as a reason to shrink a scientificallyneeded run. Parallelize independent J-lens shards when quota permits.

2.2 GitHub is Git transport only

Allowed: clone, fetch, commit, and non-force push to the existing repository.Forbidden: GitHub Actions, workflows, PRs, issues, releases, artifacts, GHCR,Packages, Codespaces, or other GitHub automation. Do not create or modify.github/workflows/*.

2.3 Worktree and cleanup safety

Preserve user changes and unknown ignored/private files. Never use git clean
-fd, git clean -fdx, force-push, destructive reset, broad recursive delete,or an unresolved path. Remove only exact round-created archives, caches, logs,and disposable Azure resources after resolving and recording them. Do nottouch parser-v3 sealed objects or private prefixes.

2.4 Checkpoint discipline

Use small, honest, non-amended commits and push each reproducible checkpoint.If the session ends, push the largest reproducible checkpoint and reportNONTERMINAL_CHECKPOINT_<EXACT_NEXT_SCIENTIFIC_GATE>. Expected duration is nota blocker.

No gate in this prompt requires “zero findings.” Ordinary test failures must befixed, but do not create recursive audits of the tests, harness, registry, orreceipts. One bounded preregistration review is defined in §7; it is not anopen-ended audit program.

3. Work package S0 — close parser-v3 without erasing history

At the exact starting SHA, first reproduce the current Git state and verifythat origin/main equals the required commit. If it does not, stop and reportboth SHAs without reset/rebase/force-push.

Create and commit:

docs/decisions/parser_v3_locked_evaluation_closure.md
docs/phase_science_restart_authority.json

The closure record must state:

the old two-cycle audit limit was honored and the terminal record remainsimmutable;

parser-v3 was never validated and no parser-v3 scientific result exists;

L-01 makes automatic parsing triage-only and semantic adjudicationauthoritative;

therefore a locked parser validation is no longer a prerequisite for anyscientific label or downstream experiment;

no private holdout, label, prediction, Stage P/E result, or formal ordinal isopened or created by this decision;

the parser subproject is CLOSED_NONAUTHORITATIVE_TRIAGE_ONLY;

the global project is SCIENTIFIC_MAINLINE_RESTART_AUTHORIZED;

old audit infrastructure is preserved but removed from the critical path.

Append consistent entries to README.md, docs/decision_log.md,paper/limitations_ledger.md, paper/claim_evidence_matrix.md, and, whereneeded, the methods/evidence ledgers. Do not edit old receipt/report bytes. Donot change parser implementation, parser tests, parser schemas, or parser IaCin this work package.

4. Work package S1 — Phase 1.0D headroom repair and strict-no-CoT calibration

4.1 Preserve the old result and record the actual defects

Phase 1.0C run 20260725T170041Z remains a valid historicalCOMPLETE_INCONCLUSIVE run. Do not relabel, delete, or silently replace it.

Before the new run, reproduce and record at least these facts from committedartifacts and source:

all 300 generated records were prompted with the literal format lineFinal answer: <answer>;

31 output texts contain the literal substring <answer> and 5 contain aFinal answer: <answer>... form;

79 of the 225 semantically reviewed rows reached the registered 512-tokencap;

44 of 300 rows remained semantically unresolved;

the run's INCONCLUSIVE state was therefore not a GPU-budget failure andmust not be attributed to one cause alone.

Treat the literal placeholder and the token cap as two separate, preregisteredgeneration-profile defects. Do not claim either one alone caused all 44unresolved rows.

4.2 Freeze a new Phase 1.0D protocol before inference

Create a new protocol/version and new artifact namespace. It must not overwritePhase 1.0C. Freeze all selection, prompt rendering, decoding, adjudication, anddecision rules before any new target-model generation.

Use the same pinned target model/revision and the public 450-item candidatebank. Derive a deterministic disjoint confirmation split from items not usedby Phase 1.0C. The intended design is 20 items for each task-family ×difficulty cell. Verify that the bank supports this exact disjoint split. If itdoes not, stop the run before inference, record the shortage, and create atmost one prospectively specified public replacement batch; never select orreplace an item using model or lens outputs.

Run these three conditions on the same disjoint items and registered seeds:

r1_style_thinking — visible-reasoning capability control;

strict_answer_only_empty_think_prefill — primary structural no-CoTcondition already defined by the project;

prompt_only_raw_strict — primary spontaneous surface no-CoT condition.

Do not add the Phase 1.0C literal placeholder to any condition. Condition-specific formatting must be explicit:

visible reasoning may reason, then end with Final answer: followed by theactual answer;

the instruction must explicitly say not to output angle brackets,placeholders, XML tags, or the word answer as a stand-in for the value;

strict answer-only conditions must use their existing registered no-CoTrenderers and must not inherit a visible-reasoning override;

raw strict must not contain think tags, an empty-think prefill, or amodel-name-dependent branch.

Register generation budgets by condition before inference. Use at least 1024new tokens for the visible-reasoning control. Give the strict conditions enoughroom for the answer but do not permit visible CoT by increasing their budget.A generation-time stop may stop only after a complete registered final-answersurface; never clip text post hoc and call the clipped value the model output.

Azure tests must render every real prompt and assert that no prompt containsthe literal <answer> or any unexpanded template token. Include positivesynthetic rendering examples for each condition.

4.3 Authoritative semantic labels

Automatic parsing may route cases but may not decide final correctness. Everyrow that contributes to a cell metric or eligibility decision requires asemantic label under a closed reviewer form.

Use one primary semantic reviewer for all rows, then an independently isolatedsecondary review for:

every primary unresolved/invalid row;

every parser/reviewer disagreement;

a deterministic stratified 20% sample of the remaining rows.

Arbitrate every reviewer disagreement under a frozen rule. Report agreementand disagreement counts; do not treat parser agreement as inter-revieweragreement. Because all prompts and outputs in this work package are publicscientific data, do not build a private parser review boundary for them.

4.4 Headroom metrics and gate

Report per cell and condition:

semantically adjudicated accuracy and Wilson 95% interval;

paired condition differences on the same items;

truncation, invalid, loop/repetition, placeholder, and unresolved rates;

correct-case counts available for mechanistic analysis.

A cell is an RQ2 pilot candidate only if all 20 primary rows are resolved, thevisible-reasoning control has at least 14/20 correct, the relevant strict-no-CoTcondition has 8–18/20 correct, and truncation/invalid rates are each no morethan 10%. These count gates select substrates; they are not populationperformance claims. Report every cell regardless of selection.

If no cell passes, declare HEADROOM_NOT_ESTABLISHED as a scientific result.Do not repair the parser, lower the gate, reuse Phase 1.0C items, or choose apost hoc task family.

5. Work package S2 — full-layer J-lens scaling run

5.1 Correct interpretation of existing 0.5B/0.5C evidence

Record the following as a hypothesis, not as an established cause:

D_independent(n_a,n_b) = C * sqrt(1/n_a + 1/n_b)
D_nested(n_small,n_large) = C * sqrt(1/n_small - 1/n_large)

The observed 10-vs-25 nested relative Frobenius value and the independent25A-vs-25B value imply nearly the same C ≈ 1.7; under this model, two equalfits need roughly 583 prompts each to predict a difference near 0.10. This is auseful preregistered scaling prediction, but two comparisons do not prove puresampling variance. Matrix convergence is diagnostic and must not be treated asJ-lens semantic validity.

5.2 Corpus and fit design

Pin the official anthropics/jacobian-lens source revision already used by theproject or a separately justified compatibility revision. Record the exactcommit, dependency lock, model adapter, and any compatibility patch.

Build a deterministic public English pretraining-like corpus with at least1,400 disjoint 128-token sequences:

600 for independent arm A;

600 for independent arm B;

at least 200 held out from fitting for apply/inter-lens diagnostics.

Pin the upstream dataset name, revision, license, row IDs, sampling seed,tokenizer, exact sequence bytes, and hashes. The fit corpus must be disjointfrom behavioral candidate-bank items, parser/evaluator fixtures, validitybenchmarks, and RQ2 pilot prompts. Do not author 1,200 near-duplicate templatesor expand the old 60 prompts by paraphrase alone.

Use max_seq_len=128, matching the official reference configuration. Run asmall Azure memory/runtime smoke first, but do not use the smoke to choose amore favorable scientific result. If T4 cannot execute 128 tokens, prefer alarger GPU or smaller parallel shards before reducing the registered sequencelength. Any reduction requires a pre-fit decision entry and a new protocolversion.

Fit all model layers needed for layerwise readout and patching alignment, notonly layers 6/13/20. Use disjoint shards whose merges yield cumulativecheckpoints at approximately n = 64, 128, 256, 600 for each arm while fittingeach sequence only once. Verify official weighted merge equivalence and exactsave/load behavior. Merge A600 and B600 into the preregistered primaryn=1200 lens; do not choose whichever replicate looks best on the validitybenchmark.

At every checkpoint report:

per-layer relative Frobenius and cosine agreement between A and B;

fitted scaling exponent and residuals, without forcing exponent 1/2;

finite rate, save/load exactness, shard-merge equivalence, wall time,memory, and cost;

held-out apply stability;

later, the functional validity metrics from §6.

Do not block §6 merely because a matrix threshold fails. Advance when thetransport/save/load/merge checks are sound and both independent fits exist.

6. Work package S3 — preregistered J-lens validity benchmark

This is the primary scientific instrument gate. It must be designed and frozenbefore applying any new lens to benchmark activations.

6.1 Benchmark construction without lens-based selection

Vendor or reference, with exact commit and Apache-2.0 attribution, the officialpublic evaluation sets from anthropics/jacobian-lens/data/evaluations.Primary distributions are:

lens-eval-multihop.json;

lens-eval-order-ops.json.

Association, typo, multilingual, and poetry may be reported as secondarygeneralization checks but cannot rescue a failed primary result.

Before inspecting any J-lens or logit-lens readout:

resolve intermediate-token synonym sets under the pinned Qwen tokenizer;

exclude only mechanically ineligible multi-token cases under a frozen rule;

run the target model's clean behavior and retain only items it answerscorrectly under the registered behavior condition;

assign a fixed development subset of at most 15 eligible items per primarydistribution by content hash and reserve every remaining eligible item forconfirmation;

freeze all layer bands, read positions, k values, paired alternatives,intervention strengths, metrics, gates, and replacement rules.

Selection may use tokenizer facts and clean behavior only. It must never useJ-lens rank, logit-lens rank, patching effect, or intervention outcome. Requireat least 20 confirmatory eligible items in each primary distribution and atleast 50 confirmatory items pooled across the two. If the frozen minimum fallsshort, allow one preregistered public replacement batch constructed before anyreadout; otherwise reportINSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY.

6.2 Readout validity

Using the same activations and positions, compare:

the merged n=1200 J-lens;

A600 and B600 independently as replication diagnostics;

the ordinary logit lens;

label-permuted and position-shuffled negative controls.

For each method compute pass@k curves for the registered intermediate synonymsets and normalized area under pass@k against log(k), both by layer and over aprospectively defined middle-layer band. Also report early and final-layercontrols. Do not select a best layer after seeing the confirmatory data.

6.3 Causal validity

On prospectively paired items, compare J-lens, logit-lens, and norm-matchedrandom directions using:

intermediate-direction ablation and output-distribution KL / correct-answerlogit change;

coordinate swaps from the true intermediate to a registered alternative andsuccess in moving top-1 output to the alternative-consistent answer;

answer-vector swaps across layers to test whether an apparent intermediateeffect merely smuggles in the answer;

lens-independent activation patching on counterfactual pairs to locate thecausal layer/position band.

The intervention code must operate on the actual model path and must includeclean, no-op, wrong-position, wrong-layer, random-direction, label-permuted,and surface-leakage controls. Preserve the unmodified output as the baseline.

6.4 Frozen interpretation rule

Use item-level paired bootstrap 95% intervals. Freeze exact implementationdetails before the confirmatory split is opened.

Classify the lens as:

JLENS_VALIDATED_FOR_RQ2_PILOT only if the pooled primary confirmatoryJ-lens-minus-logit readout-AUC interval is entirely above zero and theJ-lens-minus-logit causal swap-success interval is entirely above zero, withJ-lens also exceeding the registered random-direction control;

JLENS_PARTIALLY_VALIDATED if exactly one of the readout or causal gatespasses;

JLENS_NOT_VALIDATED if neither passes or a leakage/control gate fails;

INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY if the frozen minimum samplecannot be reached without post hoc selection.

Report activation-patching alignment as an independent supporting criterion:the layer/position at which the known intermediate is most causallyload-bearing should agree prospectively with the J-lens intermediate trajectorybetter than with the shuffled control. Do not promote a partial result tovalidated solely because this supporting analysis looks favorable.

A PARTIALLY_VALIDATED or NOT_VALIDATED outcome is a terminal scientificinstrument result. Do not alter thresholds, refit on the confirmatory set, orrestart parser/audit work.

7. One bounded preregistration review — no recursive auditing

Before the Phase 1.0D target-model run and before the J-lens validity benchmark,perform one methods review of the frozen public protocols. It may examine only:

train/development/confirmatory leakage;

whether selection can depend on model/lens outcomes it should not see;

whether metrics and interventions are computable from the registered data;

whether the controls distinguish intermediate representation from final-answer leakage;

whether the execution artifacts can reproduce the stated result.

Allow one consolidated correction before any scientific output is generated oropened. Then freeze. Do not demand zero minor findings, do not audit the reviewharness, and do not run a second remediation/audit cycle. A fatal unresolvedleakage or noncomputable primary metric stops before inference asBLOCKED_ON_PREREGISTRATION_INTEGRITY; all nonfatal limitations are recordedand the experiment proceeds.

After results exist, reviewers may check arithmetic and provenance, but theymay not change prompts, samples, metrics, thresholds, gates, or eligibility.

8. Work package S4 — first bounded RQ2 mechanistic pilot

Run this package only if:

Phase 1.0D produced at least one RQ2 pilot candidate cell; and

§6 returned JLENS_VALIDATED_FOR_RQ2_PILOT.

Freeze a Phase 2A pilot protocol using behaviorally successful strict-no-CoTcases from the selected cells, disjoint from instrument-validity items wherepossible. Require at least 50 correct strict-no-CoT cases with registered knownintermediates; otherwise report the exact available count and stopINSUFFICIENT_RQ2_PILOT_CASES without lowering the gate.

For the same items and seeds, compare:

strict_answer_only_empty_think_prefill;

prompt_only_raw_strict;

r1_style_thinking as a visible-reasoning control.

Primary pilot analyses:

known-intermediate J-lens rank/AUC trajectories by layer and position;

lens-independent activation-patching causal heatmaps;

intermediate coordinate swap or ablation effects on the correct answer;

J-space-targeted ablation damage versus norm- and layer-matched randomcontrol damage;

preregistered alignment between J-lens readout peaks and patching peaks.

Do not interpret a final-layer answer token as hidden reasoning. Do not infer aworkspace from behavior alone. Do not claim the R1-distill-vs-base RQ3 resultin this package; RQ3 remains a later ability-matched, lens-independentcomparison with Qwen/Qwen2.5-Math-1.5B.

The successful state is RQ2_MECHANISTIC_PILOT_COMPLETE, whether the primaryhypothesis is supported or contradicted. A null or contradicted result is not ablocker and must not be repaired away.

9. Azure validation without infrastructure expansion

Use the existing public ACR/ACA/Azure compute path wherever possible. Thisround does not require Premium ACR, Azure Firewall, Private Link, fifteen-roleprivate entrypoints, private semantic review, or a new schema registry.

Run in Azure:

exact baseline and candidate test suites;

targeted tests for Phase 1.0D prompt rendering, generation, adjudication,and decision logic;

corpus split/hash/token-length tests;

J-lens full-layer fit, shard merge, save/load, and checkpoint tests;

official evaluation-set ingestion and tokenizer eligibility tests;

readout, logit-lens, bootstrap, intervention, and patching tests;

deterministic self-tests and small synthetic positive/negative controls;

final artifact-manifest and ledger verification.

Tests should constrain the code that actually executes, but do not build a newmeta-evaluator to prove that every test is perfect. When an ordinary defect isfound, fix it, add a regression test, record it, rerun the relevant Azure gate,and continue.

10. Artifacts and reporting

Every executed work package must produce a normal scientific pack containing:

protocol snapshot and preregistration hash;

exact model/code/image/dependency/corpus/evaluation-set provenance;

row-level public records where licensing permits;

aggregate metrics with intervals and all selection/exclusion counts;

decision/result object computed from frozen gates;

deviations and implementation-error ledger;

paper-ready tables and figure data;

artifact manifest with SHA-256 for every file;

concise summary stating what the result does and does not support.

Update paper/evidence_ledger.csv, paper/claim_evidence_matrix.md,paper/limitations_ledger.md, paper/methods_ledger.md, artifact/figure/tableregistries, docs/run_log.md, and docs/decision_log.md after each completedscientific result. Parser triage statistics may be reported as diagnostics butmust never appear as final-label evidence.

Valid final states are:

RQ2_MECHANISTIC_PILOT_COMPLETE
JLENS_VALIDATED_FOR_RQ2_PILOT
JLENS_PARTIALLY_VALIDATED
JLENS_NOT_VALIDATED
HEADROOM_NOT_ESTABLISHED
INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY
INSUFFICIENT_RQ2_PILOT_CASES
BLOCKED_ON_PREREGISTRATION_INTEGRITY
BLOCKED_ON_AZURE_EXECUTION_<EXACT_CAUSE>
NONTERMINAL_CHECKPOINT_<EXACT_NEXT_SCIENTIFIC_GATE>

Do not return to any parser-v3 or public-protocol-freeze state under thisauthority.

11. Final handoff

Return:

final state and exact remote commit/tree;

parser closure decision and proof old records are unchanged;

Phase 1.0D protocol, sample, prompt, token budget, semantic-review coverage,headroom results, and whether a pilot cell exists;

J-lens corpus provenance, 128-token smoke, GPU/shard plan, all-layer lenscheckpoints, runtime/memory/cost, A/B scaling diagnostics, and merged-1200artifact hash;

validity benchmark eligibility before readout, development/confirmatorysplit, J-lens/logit/random readout and causal metrics with intervals,patching alignment, and frozen classification;

if run, the complete Phase 2A mechanistic pilot result and its limitations;

every Azure run/resource ID and exact cleanup/retention action;

the smallest next scientific gate, not an infrastructure perfection task.

Primary methodology references to pin and cite in the repository:

https://transformer-circuits.pub/2026/workspace/index.html

https://github.com/anthropics/jacobian-lens

https://github.com/anthropics/jacobian-lens/tree/main/data/evaluations

The official reference reports a default fit of 1,000 sequences × 128 tokensand evaluates lens quality on known intermediates using pass@k readout,ablation, and coordinate swaps. Reproduce the method at the scale this modeland Azure environment support; do not substitute matrix convergence for thoseexternal functional validity tests.