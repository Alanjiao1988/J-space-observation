You are working in the existing GitHub repository:

Alanjiao1988/J-space-observation

Do not create, migrate to, mirror into, or publish a new repository. The samerepository is required because Study 3 is part of the same research program andmust retain an auditable, non-selective chain through the closed Study 1 andStudy 2 protocols. Scientific separation is created by a new namespace,authority, estimand, protocol, banks, seeds, gates, and receipts, not by hidingearlier null or feasibility-closure results in another repository.

This authority contains two strictly ordered, non-empirical tasks:

correct the known Study 2 terminal-documentation changed-path bookkeepingundercount in docs/run_log.md; and

create a reviewable design draft for a new, scientifically distinct Study 3interface-calibration study.

This prompt does not authorize Study 3 execution, Study 2 protocol v2, anytask-bank draw, tokenizer construction, model download or load, forward pass,generation, GPU job, activation operation, probe, patch, ablation, or lensoperation.

The required normal endpoint is:

STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW

That endpoint is a design state only. It is not a frozen protocol, an empiricalresult, or execution authority.

The primary Study 2 scientific terminal state must remain exactly:

STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY

The Study 2 documentation state must remain exactly:

STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE

1. Authority hierarchy and scientific separation

This prompt is the complete operator authority for this round. No README,charter, old handoff, TODO, protocol paragraph, code path, or inferred next stepmay expand it.

This round may:

fetch and inspect the repository read-only;

verify the complete content-identity starting state;

make the exact one-file Study 2 bookkeeping correction in section 5;

create only the Study 3 design-draft files in section 10;

update only the mutable routers and non-evidence registries in section 11;

perform model-free calculations for sample-size, power, exact thresholds,equivalence margins, multiplicity, and deterministic bank-design proposals;

use English-language primary research sources for methodological grounding;

run CPU-only validation in Azure ACR against committed bytes;

create ordinary commits and publish them by a non-force,fast-forward-only push to remote main.

This round may not:

reopen, repair, rerun, replace, relabel, backfill, or reinterpret Study 1 orStudy 2;

create Study 2 protocol v2;

freeze Study 3 or draw its task-bank seeds;

choose a final Study 3 interface, model panel, task bank, threshold, samplesize, or confirmation rule as irrevocable;

execute any empirical or model operation;

create a scientific evidence row or scientific claim.

Study 3 has a different estimand from Study 2. Study 2 asked whether the targetcheckpoint computes and causally uses a task-defined intermediate variableduring a single forward pass. Study 3 will ask whether candidate response andscoring interfaces are adequate, robust instruments for eliciting and measuringknown or deliberately trivial competence before any later causal study relieson them.

Study 3 may cite Study 2 only as motivation and as a source of explicitlypost-hoc, zero-authority failure modes to guard against. Study 2 item-leveloutcomes may not select Study 3 tasks, templates, thresholds, seeds, modellayers, or preferred winning interface.

2. Mandatory starting-state preflight

Perform this preflight before editing any file.

2.1 Branch metadata is observational

Record:

git branch --show-current;

the local branch name or detached-HEAD state;

session name, if exposed;

worktree path;

repository path.

Local branch names, session names, worktree paths, and platform-imposed detachedHEAD states are non-authoritative metadata. Do not rename, switch, merge,rebase, reset, cherry-pick, delete, or recreate a branch or worktree to obtain aspecific label.

2.2 Commit, tree, blobs, and protected bytes are authoritative

Fetch origin without rebasing and verify all of the following:

repository identity is Alanjiao1988/J-space-observation;

origin points to the expected repository;

HEAD equals origin/main equals783ad360030e9105e87301ac5e3af6346076596e;

HEAD tree equals 1b97103e1cdca281cac015b79184e9c83002654f;

index and worktree are completely clean, including untracked files;

commit 43411e09de425dfae0ee74ba46c68a389311e9a7 is an ancestor;

commit a958adf4aec5736ef04f468fc3532ca7c92f7e5e is an ancestor;

commit c2e2383e96ba3d94f3dcf9b9b57db36e1f08dcd1 is an ancestor;

the Study 1 terminal commit6409d2c6d665187e4459d94d490a20d7b085e8af is an ancestor;

no studies/study3 path exists;

no Study 3 evidence, task bank, seed, tokenizer, model, or execution objectalready exists.

Verify these four Study 2 terminal-documentation blobs from committed Git blobs,not newline-converted working-copy bytes:

Path

Bytes

SHA-256

studies/study2/terminal_manifest.json

19,739

75fc5a88faed24852ee858804a8c166042c8edbfff148f60235c2942650e1292

studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md

9,516

efe21ffa73351e027c5b38d8a828cc8ea8fce1fdd37bc1b799bb416a3e9f9ff9

studies/study2/decisions/study2_stage_bd_interpretation_erratum.md

5,551

7a992ae27ec30cedd95818d84efe759e11263700b7740d0fe7b7728c944d59f8

studies/study2/analysis/stage_bd_posthoc_interface_diagnostic.md

7,487

806fc94f4c26b55246e6b8a454d29d4788da27937f8f954a58742a14ef6acb8d

Verify:

protected rollup436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51ddstill covers exactly 152 files with zero differences;

protected rollupef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82astill covers exactly 36 files with zero differences;

paper/evidence_ledger.csv is exactly 25,241 bytes, has SHA-2563821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1,contains 16 evidence records, and ends at EV-0016;

paper/artifact_index.csv ends at AR-0185 with no duplicate ID;

docs/decision_log.md ends at D37;

paper/methods_ledger.md ends at M-25;

paper/limitations_ledger.md ends at L-89.

Verify from the Study 2 terminal manifest and frozen Stage B-D artifacts:

overall_gate_pass is false;

the combined gate input digest is1433f8119b2d8e377be7ede2735430ab55006c3737ebd2bf9e0c85c486b93cf7;

cumulative Study 2 counts remain 3,072 forward passes, 3 weight loads,3 tokenizer constructions, and 3 model downloads;

every other registered Study 2 operation counter remains zero;

confirmation remains unopened;

no Study 2 scientific evidence row exists.

Run a committed-history comparison from43411e09de425dfae0ee74ba46c68a389311e9a7 to783ad360030e9105e87301ac5e3af6346076596e and independently verify:

exactly 15 changed paths;

exactly 4 added paths;

exactly 11 modified paths;

docs/decision_log.md is one of the 11 modified paths;

every path was inside the terminalization authority whitelist.

The known discrepancy is only that the terminalization entry in docs/run_log.mdsays 14 total and 10 modified and omits docs/decision_log.md. If Git itself doesnot show the 15 / 4 / 11 facts above, stop rather than applying the correction.

If any authoritative commit, tree, ancestry, blob identity, rollup, evidenceboundary, ledger tail, operation count, terminal state, or Git comparison factdiffers, stop as:

BLOCKED_ON_STUDY3_DESIGN_STARTING_STATE_INTEGRITY

Do not repair an authoritative discrepancy under this prompt.

If the only difference is branch, session, or worktree metadata, record it andcontinue. Record a passing disposition as:

STUDY3_DESIGN_STARTING_STATE_ACCEPTED_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE

3. Required repository reading

Read every item below completely from the verified starting commit beforedrafting:

README.md

studies/README.md

studies/study1/README.md

studies/study1/terminal_manifest.json

studies/study2/README.md

studies/study2/terminal_manifest.json

studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md

studies/study2/decisions/study2_stage_bd_interpretation_erratum.md

studies/study2/analysis/stage_bd_posthoc_interface_diagnostic.md

studies/study2/RESEARCH_CHARTER.md

studies/study2/protocol/reasoning_internalization_protocol.md

studies/study2/protocol/reasoning_internalization_protocol.json

studies/study2/STAGE_P_FINAL_HANDOFF.md

studies/study2/STAGE_T_FINAL_HANDOFF.md

studies/study2/STAGE_BD_FINAL_HANDOFF.md

studies/study2/decisions/study2_stage_bd_gate_a_decision.md

paper/evidence_ledger.csv

paper/artifact_index.csv

paper/claim_evidence_matrix.md

paper/methods_ledger.md

paper/limitations_ledger.md

docs/decision_log.md

docs/run_log.md

reports/current_status.md

pyproject.toml and the existing repository test layout, for validationplanning only.

Do not read any Study 2 confirmation-bank content. Reading the registeredunopened receipt and file identities is sufficient.

4. Required English-language methodological grounding

Use primary research sources, not blogs or summaries. At minimum inspect andcite the following in the Study 3 methods-source note:

Pezeshkpour and Hruschka, Large Language Models Sensitivity to The Order ofOptions in Multiple-Choice Questions, Findings of NAACL 2024:https://aclanthology.org/2024.findings-naacl.130/

Wang et al., Look at the Text: Instruction-Tuned Language Models are MoreRobust Multiple Choice Selectors than You Think, arXiv:2404.08382:https://arxiv.org/abs/2404.08382

Li et al., Can Multiple-choice Questions Really Be Useful in Detecting theAbilities of LLMs?, LREC-COLING 2024:https://aclanthology.org/2024.lrec-main.251/

Lyu et al., Revisiting the Self-Consistency Challenges in Multi-ChoiceQuestion Formats for Large Language Model Evaluation, LREC-COLING 2024:https://aclanthology.org/2024.lrec-main.1229/

You may add directly relevant primary sources. Record title, authors, venue orversion, URL, the methodological point used, and the limitation of applying itto this project. Do not treat literature findings as empirical evidence aboutthe three registered J-space checkpoints.

The draft must explicitly address the literature-supported risks that:

option order can materially change measured accuracy;

A/B/C/D or other label tokens can carry token or position preferences;

first-token probability choices can disagree with generated text choices;

multiple-choice and open or direct-answer surfaces can measure differentbehavior;

ordinary non-significance does not establish interface invariance.

5. Phase A: correct the Study 2 changed-path bookkeeping

Before creating studies/study3, make a separate commit that modifies only:

docs/run_log.md

In the existing Study 2 terminalization entry:

change the total from fourteen to fifteen;

change the modified count from ten to eleven;

add docs/decision_log.md to the modified-path list;

add a concise additive bookkeeping note stating that the original entryundercounted one already-authorized modified path, that Git history is theauthority for the correction, and that the correction changes no frozenartifact, Gate A value, operation count, evidence row, interpretation, orscientific terminal state.

Do not modify the Study 2 terminal manifest, handoff, erratum, diagnostic,decision, protocol, banks, receipts, or protected artifacts. Do not create anew Study 2 artifact record or evidence row for this correction.

Commit this as a logically separate commit with a message equivalent to:

docs: correct Study 2 terminal changed-path count

After that commit, verify that its parent is the registered starting commit andthat its diff contains exactly one path, docs/run_log.md. Do not publish yet ifthe subsequent design work can continue safely; both commits may be publishedtogether at the end.

Record the local substate:

STUDY2_TERMINAL_CHANGED_PATH_BOOKKEEPING_CORRECTED

6. Study 3 identity and question

Create the new namespace:

studies/study3/

Use the working study name:

Study 3 — Interface Adequacy and Label-Binding Calibration

Use a stable study identifier equivalent to:

jspace-study3-interface-calibration

The draft research question must be:

Can a pre-specified response and scoring interface recover deliberately trivial,primitive, and independently demonstrated task competence robustly acrossanswer-label permutations, option positions, and prompt renderings for thecheckpoint roles relevant to a later J-space study?

The draft must explicitly state that Study 3 does not ask:

whether the R1-distilled model reasons;

whether it internalized a chain of thought;

whether distillation transferred a causal mechanism;

whether a task-defined intermediate variable exists;

whether J-space or J-lens is valid;

whether Study 2 Gate A should have passed.

Passing Study 3 in a future separately authorized execution would establish onlythat a specified interface met pre-registered adequacy and robustness criteria.It would not authorize a causal-mechanism claim and would not automaticallyauthorize a later experiment. Failing Study 3 would establish only that thecandidate interface panel did not meet its calibration gates under theregistered conditions; it would not establish model incapability.

7. Required design content

The protocol draft must be concrete enough for an independent reviewer to auditand for a later operator to decide whether to amend and freeze it. It must notpretend unresolved choices are frozen.

7.1 Validation targets

Separate at least these constructs:

scoring-pipeline correctness;

answer-content to label binding;

output-surface adequacy;

primitive task headroom;

compositional task headroom in an independently capable positive control;

robustness to answer-position and label permutation;

robustness to a small, pre-specified rendering set;

agreement or disagreement among scoring surfaces.

Explain why each target is needed and what it cannot prove.

7.2 Candidate response and scoring surfaces

The draft must compare, at minimum, these candidate families:

label-token logits over A/B/C/D, retained as the Study 2 legacy comparator;

direct answer-content logits over exact single-token answer contents where afuture tokenizer gate proves single-token eligibility;

conditional log-likelihood of exact option contents, with an explicitproposal for length handling and multi-token scoring;

bounded minimal-answer generation that permits only the final answer and nogenerated rationale, included as a calibration reference rather than assumedto be the later causal-study surface.

For every surface, specify:

prompt contract;

answer position;

permitted output;

scoring equation;

tokenization assumptions;

abstention or invalid-output handling;

whether a chat template is used;

how base, distilled, and instruction-tuned checkpoints are treated fairly;

what future operation counts the surface would require;

known confounds and disqualifying failures.

Do not select a winner in this round. Propose a pre-registered,development-only selection rule and deterministic tie-breaker for later review.The held-out confirmation bank must never be used to choose the surface.

7.3 Task strata

Propose disjoint strata that include:

deterministic software-oracle and scoring-pipeline fixtures;

explicit-answer binding items in which the correct content is stated and theonly task is to map it to a balanced or permuted label;

identity, copy, and other depth-0 sanity items;

depth-1 primitive operations;

depth-2 and depth-3 compositions used only where the positive-controlrationale and power analysis justify them;

counterbalanced option-position and label-permutation variants;

carefully limited prompt-rendering variants.

For each stratum, define the data-generating process, ground-truth function,duplicate and leakage prevention, balance invariants, expected failure mode,and role in a gate. Avoid natural-language parser dependence where adeterministic ground truth is possible.

Actual task-bank rows and actual seeds must not be generated or drawn in thisround. Specify the future seed-draw and bank-sealing procedure instead.

Study 3 may reuse abstract operation families only when justified. It may notreuse any Study 2 item identity, frozen bank row, selected template outcome, orconfirmation content. New future seeds and disjoint development andconfirmation banks are mandatory.

7.4 Controls and checkpoint roles

The draft must distinguish:

a deterministic non-model oracle for renderer, scorer, mapping, and groundtruth;

explicit-answer binding conditions as an interface sanity control;

the Study 2 target, lineage-base, and instruction-control roles, if retained;

at least one independently justified positive-capability reference modelthat is not qualified on the held-out confirmation bank.

Do not silently treat the lineage base cell that reached 44/128 in Study 2 as apositive control. That cell has zero authority and came from multiple observedcontrol comparisons.

The design must give candidate positive-reference models, pinned-identity andrevision requirements, licensing constraints, expected precision and memoryrequirements, and Tesla T4 feasibility. It must not download, load, tokenize,or benchmark any candidate in this round. If no positive reference can bejustified without empirical screening, mark model choice as an operator-reviewitem and propose a separate prequalification stage that cannot inspect theStudy 3 confirmation bank.

7.5 Splits, selection, and confirmation

Specify a prospective lifecycle with at least:

non-evidential implementation fixtures;

development bank;

sealed confirmation bank;

a one-way surface-selection decision using development only;

a hard stop before confirmation requiring separate operator authority;

one-shot confirmation and fail-closed handling.

The design must prevent:

trying several surfaces on confirmation and reporting the best;

changing answer mappings after observing accuracy;

replacing failed positive controls;

threshold shopping;

cross-stratum pooling rescue;

prompt-template rescue;

reusing Study 2 outcomes as Study 3 selection data.

7.6 Statistical design

Provide reproducible, model-free calculations and candidate tables for:

sample sizes by stratum and split;

exact binomial thresholds for accuracy gates;

simultaneous error control across candidate interfaces and checkpoint roles;

confidence intervals;

a pre-specified maximum position or permutation effect;

equivalence or non-inferiority testing for robustness, rather than treating anon-significant difference as proof of invariance;

minimum practically important accuracy and robustness margins;

power or assurance at the proposed alternatives;

deterministic tie-breaking among eligible interfaces.

Do not freeze final numbers. Clearly label each number as proposed, derived,or unresolved. Include machine-reproducible formulas or standard-librarypseudocode in the draft without executing any empirical measurement.

7.7 Proposed gate hierarchy

The draft must propose a fail-closed hierarchy at least as strict as:

Gate I0 — deterministic renderer, scorer, ground-truth, and mapping integrity;

Gate I1 — explicit answer-to-label binding and output-validity adequacy;

Gate I2 — primitive-task headroom on content-based surfaces;

Gate I3 — answer-position, label-permutation, and rendering robustness underpre-specified equivalence or non-inferiority margins;

Gate I4 — independently capable positive-control headroom on the compositionalstrata needed by any later study;

Gate I5 — one-shot held-out confirmation of the development-selected interface.

For each gate, define proposed inputs, model roles, candidate threshold logic,what passes, what fails, what remains merely descriptive, and the only legalnext state. No gate may authorize mechanistic execution.

The draft must explicitly evaluate whether the target itself must pass I1 andI2 for an interface to be useful in a later target-centered causal study, whilekeeping I4 logically distinct from target capability.

7.8 Compute and reproducibility plan

All future model work, if separately authorized, must use the registered Azureremote route: ACR and Azure containerized GPU execution. The workstation is forinspection, editing, Git, hashes, and Azure submission only. Do not use GitHubActions.

The draft must propose:

immutable model and tokenizer revision pinning;

image digest and dependency locking;

pre-inference sealing;

operation counters;

independent finalization and validation;

confirmation-bank physical exclusion before authorization;

fast-forward publication and post-push verification;

branch-name-as-metadata handling;

how to prevent local newline conversion from corrupting blob checks.

These are design proposals only in this round.

7.9 Interpretation and claim ceiling

Pre-register the maximum future Study 3 conclusion in both directions:

pass: the named interface met the registered adequacy and robustness gatesfor the named tasks and checkpoint roles;

fail: no candidate interface met those gates under the registered conditions.

Neither direction may be written as evidence for or against hidden reasoning,distillation, causal internal computation, J-space, or J-lens.

The draft must state that a Study 3 pass would permit only a new operatordecision about whether to design a later substantive protocol. It would notreopen Study 2 and would not itself authorize Study 4, Study 2 v2, behavioralconfirmation, activation extraction, patching, probes, ablations, or lens work.

8. Required operator-review questions

The handoff must isolate a short list of genuine decisions for the operator,including at least:

whether Study 3 should retain all three Study 2 checkpoint roles;

which positive-capability reference model is defensible and T4-feasible;

whether bounded final-answer generation belongs in the calibration panel;

which prompt-rendering variants are methodologically necessary;

the acceptable accuracy, robustness, equivalence, and multiplicitythresholds;

development and confirmation sample sizes;

whether a bounded independent methods review is required before freeze.

Give a recommended answer and trade-off for each, but leave each visiblyreviewable. Do not bury operator choices inside JSON defaults.

9. Absolute operation prohibitions

This round must add zero to every model or scientific operation counter.

Do not:

construct a tokenizer;

access or populate a tokenizer cache;

download model files;

load model weights;

run a forward pass;

run generation, including a smoke generation;

allocate or submit a GPU job;

extract or hook activations;

fit or apply probes;

patch or ablate;

fit, load, or apply J-lens;

run Study 1 Phase 1.0D or RQ2/S4;

call a semantic-review provider or external model;

inspect any Study 2 confirmation content;

generate actual Study 3 task-bank rows;

draw actual Study 3 seeds;

create a frozen protocol, seal, execution pack, result, or evidence object;

change paper/evidence_ledger.csv;

change any Study 1 or Study 2 scientific byte;

run local pytest;

use GitHub Actions or edit workflow files.

Model-free arithmetic, schema validation, hashes, Git operations, text editing,and CPU-only Azure validation are allowed.

10. Exact Study 3 files to create

Create exactly these ten new files:

studies/study3/README.md

studies/study3/RESEARCH_CHARTER_DRAFT.md

studies/study3/protocol/interface_calibration_protocol_draft.md

studies/study3/protocol/interface_calibration_protocol_draft.json

studies/study3/protocol/interface_calibration_protocol.schema.json

studies/study3/analysis/study2_to_study3_design_traceability.md

studies/study3/references/methods_sources.md

studies/study3/NEXT_THREAD_HANDOFF.md

studies/study3/design_receipt.json

studies/study3/prompts/study3_interface_calibration_design_authority.md

The last file must preserve this operator authority verbatim. Record its bytecount and SHA-256 from the committed Git blob.

The Markdown and JSON protocol drafts must agree exactly on:

study identity;

research question;

non-questions;

candidate interfaces;

task strata;

model and control roles;

split lifecycle;

gate hierarchy;

proposed statistics;

operation boundaries;

claim ceiling;

unresolved operator decisions;

state name.

The schema must reject missing gates, missing claim boundaries, a frozen status,an execution-authorized status, actual result rows, actual bank rows, nonzerooperation counts, or an omitted confirmation-isolation rule.

The design receipt must bind:

starting commit and tree;

parent Study 1 and Study 2 terminal identities;

the bookkeeping-correction commit;

authority-prompt path, bytes, and digest;

all new design-artifact paths, bytes, and digests;

mutation whitelist;

branch and worktree metadata;

zero operation counts;

evidence-ledger identity;

protected rollups;

draft-only state;

explicit absence of execution authority.

Avoid self-reference. Do not invent the final commit or tree inside a filecontained by that commit. The final response supplies the final publicationcommit and tree.

The traceability document must separate:

sealed Study 2 facts;

post-hoc, zero-authority Study 2 observations;

literature-motivated risks;

Study 3 prospective design requirements;

choices that remain unresolved.

It must not convert option C being selected zero times in Study 2 into a Study 3hypothesis result or into evidence that a label-binding defect occurred.

11. Exact modification whitelist

Apart from the ten new files in section 10, modify only:

docs/run_log.md

README.md

studies/README.md

reports/current_status.md

docs/decision_log.md

paper/methods_ledger.md

paper/artifact_index.csv

No other path may change.

Required router and registry changes:

README.md: change the current index from two studies to three; retain Study 1and Study 2 as closed; add Study 3 as DESIGN DRAFT / AWAITING OPERATOR REVIEW;state that Study 3 has no empirical data and no execution authority.

studies/README.md: add the same distinct Study 3 row and update thecross-study rules.

reports/current_status.md: add a current top notice pointing to the Study 3draft and preserving both earlier terminal states.

docs/decision_log.md: after verifying D37 is the tail, add D38 recording thedecision to keep the same repository, create a new Study 3 namespace, anddraft rather than execute interface calibration.

paper/methods_ledger.md: after verifying M-25 is the tail, add M-26 describingthe model-free design-draft process and its non-evidential status.

paper/artifact_index.csv: after verifying AR-0185 is the tail, register theten new files as AR-0186 through AR-0195, with unique IDs, committed bytes andSHA-256 values, and paper usage limited to authority, provenance, methoddraft, or handoff. None may be marked as a scientific result or evidence.

docs/run_log.md: contain both the separate Study 2 bookkeeping correction andthe Study 3 design-round record, including preflight, commits, CPU-onlyvalidation, publication, and zero operations.

Do not modify:

paper/evidence_ledger.csv;

paper/claim_evidence_matrix.md;

paper/limitations_ledger.md;

any studies/study1 path;

any existing studies/study2 path;

any source, script, test, task-bank, artifact, Dockerfile, dependency lock, orworkflow.

At final commit, the diff from the registered starting commit must containexactly 17 paths: 10 added and 7 modified. If the count or set differs, stopbefore publication.

12. Validation

12.1 Static validation before the first design commit

Verify at minimum:

the mutation whitelist and exact 17-path final diff;

the Phase A commit contains exactly docs/run_log.md;

all JSON parses;

the protocol JSON validates against the new schema;

Markdown and JSON identities and state names agree;

no new file claims Study 3 is frozen, passed, failed, executed, or evidential;

no new file authorizes a model or tokenizer operation;

no actual seed or task-bank row exists;

all links resolve to committed paths;

D38, M-26, and AR-0186 through AR-0195 are unique and contiguous;

paper/evidence_ledger.csv remains byte-identical and ends at EV-0016;

both protected rollups remain exact;

the four Study 2 terminal-documentation artifact blobs remain exact;

the Study 2 Gate A digest and terminal states remain exact;

every Study 1 and existing Study 2 path is unchanged from the startingcommit;

no source, test, script, workflow, or dependency file changed;

cumulative and round operation counts are accurate and the round contributionis zero for every model and scientific counter.

The new JSON schema and static checks must be fail-closed. Do not weaken a checkmerely to make the draft pass.

12.2 CPU-only Azure validation

Use Azure ACR CPU-only validation against clean clones of the exact committedsource. Do not run local pytest and do not use a GPU.

Run:

the existing focused repository tests relevant to Study 2 registries andrepository ledgers;

the full repository test suite;

an ephemeral, operator-side static validation instrument for this exactround.

The static instrument may be placed in the ACR build context but must not becommitted because no new script is whitelisted. Disclose that status in the runlog.

The accepted baseline contains exactly two historical failures intest_parser_v3_seal_job, with all other tests passing. No new failure,collection error, warning promoted to error, or missing test is acceptable.

Every ACR validation must report:

bound commit;

bound tree;

dirty state equal to zero;

CPU-only execution;

no tokenizer construction;

no model download or load;

no forward or generation;

no GPU.

After recording the first committed validation results in the mutable run log,create the final documentation commit and rerun at least the focused tests,full suite, and terminal static validation against that final commit. The finalresponse may report final-commit validation that cannot be embeddedself-referentially in the same commit.

If Azure validation cannot be obtained, stop as:

BLOCKED_ON_STUDY3_DESIGN_CPU_VALIDATION

Do not substitute local evidential validation.

13. Commit and publication rules

Create intentional commits in this logical order:

the one-file Study 2 bookkeeping correction;

the Study 3 draft and router/registry update;

a final validation-record commit if required.

Do not squash away the separate bookkeeping correction. Do not amend publishedhistory.

Before every publication attempt:

fetch origin;

verify remote main still equals the registered starting commit for the firstpublication attempt;

verify local history is a strict descendant of the registered startingcommit;

verify the exact whitelist and clean index/worktree;

verify the push is fast-forward only.

Publish only with an explicit non-force refspec equivalent to:

git push origin HEAD:refs/heads/main

Never force push.

If remote main moved unexpectedly, or the push is rejected as non-fast-forward,stop as:

BLOCKED_ON_STUDY3_DESIGN_REMOTE_DIVERGENCE

Do not merge, rebase, reset, cherry-pick, or otherwise integrate unexpectedremote movement without new operator authority.

After a successful push:

fetch again;

verify HEAD equals origin/main;

record the final commit and tree;

verify the worktree is clean;

verify the exact 17-path comparison from the registered starting commit;

verify all new artifacts against committed Git blobs;

verify Study 1 and Study 2 protected states again;

verify paper/evidence_ledger.csv again;

verify no operation counter changed.

14. Required final response

Return one concise but complete handoff containing:

the preflight disposition;

observed branch, session, and worktree metadata;

the Study 2 bookkeeping-correction commit and proof that its diff is onepath;

the final commit, tree, origin/main identity, ancestry, and clean state;

exact changed-path count and list, separated into added and modified paths;

AR-0186 through AR-0195 paths, bytes, and SHA-256 values;

D38 and M-26 registration;

the Study 3 draft research question and explicit non-questions;

proposed interface families, gate hierarchy, and positive-control strategy;

the unresolved operator-review decisions;

CPU-only Azure validation runs and exact results;

confirmation that paper/evidence_ledger.csv remains EV-0016;

confirmation that both protected rollups and all Study 2 terminal blobs areunchanged;

exact zero round-operation counts;

confirmation that no new repository was created;

the terminal design state:

STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_COMPLETE_AWAITING_OPERATOR_REVIEW

End by stating plainly:

Study 1 remains closed;

Study 2 protocol v1 remains closed;

Study 3 is only a design draft;

no Study 3 protocol is frozen;

no Study 3 task bank or seed exists;

no interface has been selected;

no execution has been authorized;

the next legal action is operator review of the draft, not model execution.

