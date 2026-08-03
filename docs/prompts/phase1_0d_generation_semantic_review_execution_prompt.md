Take over the scientific mainline in this repository:

repository: https://github.com/Alanjiao1988/J-space-observation.git

branch: main

required starting commit: 5ae85cb838ff2c8d296ee90b10f1ca2e9f885b0a

required starting tree: 7a2371b6acbe09f38df450739333cccfbc38f802

required clean baseline: 3067 passed / 15 skipped / 2 failed

the two baseline failures are only the disclosed pre-existing tests/test_parser_v3_seal_job.py failures

current state: NONTERMINAL_CHECKPOINT_PHASE_1_0D_GENERATION_RUN

frozen Phase 1.0D protocol SHA-256: 25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8

frozen task-id SHA-256: 0d3fe6add211a381a321ea974502d262faf65312dc504e2acceb7c6556b1f524

frozen target model: deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B

frozen target revision: ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562

locked generation image repository: j-space-observation-phase1-0d

locked generation image build commit prefix: 9cde1d95 (resolve and record the full commit from Git)

locked generation image digest: sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4

retained Phase 1.0C run: artifacts/phase1-headroom-calibration/track-b/20260725T170041Z, status COMPLETE_INCONCLUSIVE

parser-v3 subproject: CLOSED_NONAUTHORITATIVE_TRIAGE_ONLY

Save this prompt verbatim as:

docs/prompts/phase1_0d_generation_semantic_review_execution_prompt.md

Commit and push that authority record before implementing anything else. Execution of this prompt is the operator's new, narrow authorization for the semantic-review execution addendum and the Phase 1.0D scientific run described below.

1. Controlling decision

Phase 1.0D is fully built but has produced no scientific data. No target-model generation exists, no semantic judgment exists, no cell metric exists, and no RQ2 pilot cell exists.

The frozen protocol fixes the reviewer form, label vocabulary, role names, secondary-sampling rule, arbitration rule, and cell gate. It does not fix the semantic label rubric, the actual reviewer providers, their model versions, their request parameters, or the staged execution that keeps secondary and third reviewers isolated. Those facts can affect final labels. They must be frozen before any target-model output is generated or opened.

This prompt therefore authorizes exactly one prospective execution addendum. The experimental identity used in every final receipt is the ordered pair:

existing protocol SHA-256 25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8; and

the new semantic-review execution addendum SHA-256 computed and committed before inference.

Do not rewrite the existing protocol snapshot or pretend its hash alone contained the missing provider facts. Do not call the addendum a correction made under the already-spent section 7 review allowance. It is a new operator authorization issued while every Phase 1.0D scientific counter is still zero.

The addendum may complete only the previously unspecified semantic-review execution path. It may not change:

the 300 selected items;

any rendered target-model prompt;

the three target-model arms;

model or tokenizer revision;

target-model decoding or seed;

1024/32 token budgets;

semantic label vocabulary;

reviewer-presented row fields;

secondary sample fraction or strata;

forced-secondary rules;

arbitration rule;

no-CoT compliance rule;

cell metrics, thresholds, or interpretation;

parser's routing-only status.

Do not reopen parser-v3, create another parser holdout, run Stage P/E, build a private semantic-review boundary, or start another audit recursion. A negative Phase 1.0D outcome is a scientific result.

2. Operating boundaries

2.1 Azure executes; the laptop edits and orchestrates

The laptop may clone/fetch, edit public tracked files, run lightweight Git and hash commands, submit Azure work, monitor control-plane state, and read bounded content-free summaries. It must not run pytest, imports-as-tests, builds, target-model inference, semantic reviewers, label extraction, review selection, arbitration, finalization, or metric computation.

Run all tests and all reviewer or model execution in ACR Tasks or Azure Container Apps Jobs. The semantic data in this phase are public scientific prompts and outputs, so no Premium ACR, Private Link, Firewall, or private review network is required.

2.2 GitHub is Git transport only

Allowed: clone, fetch, commit, and non-force push to the existing repository.

Forbidden: GitHub Actions, workflows, PRs, issues, releases, artifacts, GHCR, Packages, Codespaces, or any other GitHub automation. Do not add or modify .github/workflows/*.

2.3 Preserve history and protected bytes

Do not edit or regenerate:

any file under the Phase 1.0C run 20260725T170041Z;

docs/phase1_0d_protocol_snapshot.json;

phase1_0d_build_provenance.json;

src/jspace_observation/phase1_0d_confirmation.py;

src/jspace_observation/phase1_0d_execution.py;

src/jspace_observation/phase1_0d_generation.py;

scripts/run_phase1_0d_confirmation.py;

the locked generation image tag or manifest;

parser-v3 code, tests, schemas, IaC, reports, sealed objects, or receipts.

Before implementation, record SHA-256 for these protected files. Recheck them before the target run and in the final handoff. A mismatch stops as BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT.

Do not use git clean -fd, git clean -fdx, force push, destructive reset, broad recursive deletion, or an unresolved path. Preserve unknown user files and unrelated changes.

2.4 No target-output-dependent method choice

Before the semantic-review addendum, exact reviewer deployments, reviewer prompt bytes, request parameters, adapters, tests, and review image are committed and locked:

do not start the target model;

do not read a target output;

do not create a target review request;

do not choose a reviewer or fallback using a target output;

do not tune the rubric against a Phase 1.0C or Phase 1.0D output.

If the required reviewers cannot be deployed and smoke-tested prospectively, stop before target inference as BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION.

3. R0 — freeze the semantic-review execution addendum

Create and commit:

docs/phase1_0d_semantic_review_addendum.json

docs/phase1_0d_semantic_review_rubric.md

src/jspace_observation/phase1_0d_semantic_review.py

scripts/run_phase1_0d_semantic_review.py

focused tests for the addendum, role isolation, exact staged coverage, source-pack binding, and result-bundle manifest

an ACR/ACA launcher for the public CPU semantic-review job

a dedicated review/finalization container definition and build-provenance record

Names may be adjusted to the repository's conventions, but their roles and evidence must remain separate and obvious.

3.1 Exact reviewer roles and models

Use three distinct immutable reviewer identities:

Role

Required model

Required version/deployment property

primary

Azure OpenAI gpt-5.6-sol

GA model version 2026-07-09; deployment must pin this version, never latest

secondary

Microsoft Foundry Mistral-Large-3

version 1, model sold and hosted by Azure

third

Microsoft Foundry DeepSeek-V4-Pro

version 2026-04-23, model sold and hosted by Azure

The secondary reviewer is independently isolated, not merely another call carrying the primary result. The third reviewer is used only where primary and secondary labels disagree.

Use an existing compatible Foundry/Azure OpenAI resource when its control-plane metadata proves the exact required model and version. Otherwise this prompt authorizes the smallest public, pay-per-token Foundry resources and exact Global Standard deployments needed for these three roles in eastus2, plus a dedicated user-assigned managed identity and least-privilege inference roles. All three models must be offerings sold and hosted by Azure; do not create a Marketplace partner-model subscription.

Use Microsoft Entra ID / managed identity only. Do not use, print, store, upload, or commit API keys, SAS tokens, account keys, client secrets, connection strings, bearer tokens, or authorization headers.

The review job identity may receive only:

Cognitive Services OpenAI User on the exact Azure OpenAI resource;

Foundry User on the exact Foundry resource/project required for Mistral and DeepSeek inference;

the narrow Blob data-plane access required to read the one public generation pack and create the corresponding review/final bundle;

ACR pull on the exact review image.

Record role-assignment IDs and scopes in a sanitized control-plane receipt. Do not commit subscription IDs, tenant IDs, endpoint secrets, access tokens, or raw authorization material. Hash resource IDs when public provenance needs stable binding.

If any exact model/version is unavailable, has no quota, is not Hosted on Azure as required, or cannot authenticate with the managed identity, do not substitute another model. Stop before generation with the exact Azure error and zero target-model generations.

3.2 Frozen reviewer rubric

The following rubric text is controlling. Store it verbatim, hash it, and send the same semantic instructions to all three roles. Provider-specific wrappers may differ only where the API requires it.

You are an isolated semantic correctness adjudicator. You receive exactly four data fields: record_id, question, registered_answer, and output_text. The registered_answer is the experiment's reference answer. Judge the answer asserted by output_text against that reference. Do not use tools, browsing, external files, parser output, task metadata, condition/arm metadata, or any other reviewer's judgment.

Return exactly one JSON object with exactly one key named "label". Its value must be exactly one of: "correct", "incorrect", "no_answer", "invalid", or "unresolved". Return no prose, Markdown, code fence, explanation, confidence, or extra key.

Apply these rules in order:

1. invalid: use only when the presented record itself cannot support a correctness judgment because the question or registered answer is missing/malformed, or the output bytes are corrupt/unreadable. Do not use invalid merely because the model is wrong, verbose, truncated, refuses, or violates answer formatting.
2. no_answer: use when output_text is empty, is only a refusal, is only reasoning with no committed answer, or ends before any answer can be identified.
3. If output_text contains one or more explicit "Final answer:" surfaces, treat the last complete such surface as the model's final commitment. Otherwise use the unambiguous answer asserted by the whole output.
4. unresolved: use when the output makes multiple conflicting final commitments with no rule selecting one, or semantic equivalence to the registered answer genuinely cannot be determined from the four presented fields. Do not use unresolved merely for harmless formatting, capitalization, whitespace, verbosity, or a correct answer accompanied by reasoning.
5. correct: use when the final committed answer is semantically equivalent to registered_answer. Exact string equality is not required. Accept harmless capitalization/whitespace differences, mathematically exact numeric equivalents, and wording variants that preserve the same answer. Do not invent an unstated tolerance or ignore a unit/entity/value change.
6. incorrect: use when the output makes a clear final commitment that is not semantically equivalent to registered_answer.

Correctness and strict-no-CoT compliance are separate. Do not penalize visible reasoning, multiple lines, think tags, or explanatory text when deciding correctness; a separate frozen deterministic rule measures no-CoT compliance.

The row payload sent to a reviewer must contain exactly the existing REVIEW_FORM_PRESENTED_FIELDS:

record_id

question

registered_answer

output_text

It must not contain role, arm, condition, task family, difficulty, parser route, triage flags, no-CoT flags, primary label, secondary label, or any metric.

The model response is raw provider output, not yet the registered judgment. The adapter may take only its validated label; the orchestrator supplies record_id, immutable role, and immutable reviewer_id to form the existing four-field judgment. No semantic normalization, synonym mapping, majority vote, or parser fallback is allowed.

3.3 Request parameters

Freeze exact request JSON separately for each provider before any target output exists.

For gpt-5.6-sol:

use the pinned deployment version 2026-07-09;

use the Azure OpenAI v1 Chat Completions or Responses API consistently;

reasoning_effort="medium";

structured output with a closed JSON schema containing only the five-label enum;

maximum visible output no greater than 64 tokens;

store=false where supported;

no tools, browsing, file search, code execution, or conversation state;

omit unsupported sampling parameters rather than relying on service defaults silently.

For Mistral-Large-3 version 1 and DeepSeek-V4-Pro version 2026-04-23:

use the Microsoft Foundry model-inference endpoint and the exact API version proven by the provider qualification receipt;

use models sold and hosted by Azure, deployed as Global Standard in eastus2;

disable tools and external access;

maximum visible output no greater than 64 tokens;

use the documented deterministic/lowest-variance request supported by that exact version;

record every explicitly set parameter and every material service default;

require the same one-key JSON response; use native JSON response mode where the exact deployment supports it, otherwise apply strict JSON parsing and reject any extra text or key;

for DeepSeek, keep any provider-separated reasoning content out of the registered judgment and extract only the final one-key JSON response.

Every role processes one row per stateless request. Concurrent transport is allowed, but no prompt may contain more than one row and no provider conversation/session may be reused across rows.

Set a fixed maximum concurrency of 8 per deployment. Record request IDs, deployment/model/version, API version, request-body SHA-256, response-body SHA-256, provider-reported model identifier/fingerprint when available, token usage, latency, retry count, and terminal status. Never record credentials or authorization headers.

3.4 Transport retry and malformed-response rules

Retry only transport/service failures: HTTP 408, 429, 500, 502, 503, 504, connection reset, or timeout. Use at most 8 attempts with bounded exponential backoff and jitter. Every retry must use byte-identical semantic request content, the same record/role custom ID, and the same pinned deployment.

After any successful provider response, do not resample or reprompt because its label is undesirable, uncertain, or unresolved.

A successful response that is not exactly the required one-key JSON object is not converted into a semantic label and is not retried semantically. Stop the affected review stage as BLOCKED_ON_MALFORMED_SEMANTIC_REVIEW_RESPONSE, preserving the raw response and all already-completed judgments. A transport failure after all allowed identical retries similarly stops as BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT rather than being mislabeled unresolved or no_answer.

An explicit valid reviewer label unresolved is a semantic judgment and proceeds through the frozen secondary/arbitration rules unchanged.

3.5 Prospective synthetic endpoint smoke

Before target inference, exercise each exact deployment and adapter on a committed, fixed synthetic conformance set that includes at least:

an obvious exact correct answer;

an obvious semantically equivalent correct answer;

an obvious incorrect answer;

an empty output producing no_answer;

conflicting commitments producing unresolved;

a record with a missing question producing invalid.

The expected labels and exact request bytes must be committed before calls are made. Run each fixture as an isolated request through all three deployed roles. Require valid schema output and the expected label for every fixture. Record all smoke responses in a non-scientific provider-qualification receipt.

Do not tune the rubric, change examples, change models, or add a fallback after seeing the smoke outputs. A failure stops before target generation. These synthetic calls do not increment any Phase 1.0D scientific counter.

4. R1 — implement and verify the staged review path

The new review module is an execution wrapper around the frozen functions. It must not reimplement or change their scientific decisions.

It must provide these deterministic stages:

verify-generation-pack

primary-review

select-secondary

secondary-review

select-third

third-review

verify-judgments

finalize

export-result-bundle

4.1 Generation-pack verification

Before any reviewer sees a row, verify:

artifact_manifest.json exists and every listed hash matches;

the generation pack status is exactly AWAITING_SEMANTIC_REVIEW;

protocol SHA-256 is the frozen 25e96401... value;

task-id SHA-256 is the frozen 0d3fe6ad... value;

code/image/model/tokenizer provenance matches the locked generation image and target revision;

exactly 300 selected items and 900 unique records exist;

exactly one record exists for every selected item x three frozen arms;

every record has a null primary, secondary, and final label;

03_review_form.jsonl has exactly 900 rows and exactly the four presented fields;

review-form rows and record rows bind one-to-one by record_id and identical registered answer/output text;

no existing Blob object already occupies the new review/final subprefix.

Do not drop a failed target generation. The frozen driver deliberately carries it as an empty/error row to semantic review, so every one of the 900 rows remains in the denominator.

4.2 Primary review

Run the pinned primary reviewer on all 900 rows. The primary job may read only the verified four-field review form and the frozen rubric/adapter. It may not read records containing triage metadata.

Emit:

exactly 900 primary judgments in the existing closed four-field schema;

one raw request/response receipt per row;

a manifest of every request and response hash;

counts of valid labels and transport retries, without computing any cell metric.

4.3 Secondary selection and review

In a separate Azure CPU process, attach only the 900 primary judgments to the verified records, call the existing frozen annotate_review_selection, and emit the required secondary record IDs.

The required set is exactly the union of:

every primary unresolved or invalid row;

every parser/primary disagreement under the frozen routing-only comparison;

the deterministic stratified 20% sample of the remainder.

There are 45 task-family x difficulty x arm strata with 20 rows each, so the fixed sampled component is exactly 180 rows before union with forced rows. Assert that fact. The final union may be larger but never smaller than 180.

Build the secondary input by selecting the original four-field review rows by ID. Do not add primary labels, selection reasons, triage, arm, task family, or difficulty. Run only the pinned secondary deployment, one isolated request per selected row.

Emit exactly one secondary judgment for every and only every required secondary ID. A secondary judgment for a nonrequired row or a missing judgment for a required row is a hard integrity failure.

4.4 Third selection and review

Using only deterministic orchestration after secondary judgments exist, select exactly the rows where primary and secondary labels disagree.

Build the third-review inputs from the original four-field rows. Do not show either prior label, the disagreement fact, the parser route, the arm, or any metric. Run only the pinned third deployment, one isolated request per selected row.

Emit exactly one third judgment for every and only every primary/secondary disagreement. No third judgment may exist where the first two reviewers agreed or where no secondary review was required.

4.5 Judgment-set verification

Before finalization, assert:

primary role set = all 900 record IDs;

secondary role set = exactly the frozen required-secondary set;

third role set = exactly the primary/secondary disagreement set;

no duplicate row/role pair;

no reviewer identity holds two roles on the same row;

all reviewer IDs bind exact deployment/model/version/rubric/request-profile hashes;

every judgment is derivable from one recorded successful raw provider response;

no provider/model substitution occurred;

no reviewer saw prohibited fields;

all input/output/receipt files are hash-bound.

Then pass the combined judgment set to the existing finalize path. Do not hand-edit labels or decision JSON.

4.6 Finalization input binding

The existing finalizer computes the frozen result but does not by itself make the source generation manifest and raw reviewer receipts part of its inner provenance. Add an outer execution receipt and outer manifest without changing the protected finalizer source.

The outer receipt must bind:

authority prompt SHA-256;

base protocol SHA-256;

semantic-review addendum SHA-256;

generation image digest and build commit;

generation run/execution ID;

generation pack manifest and 02_records.jsonl SHA-256;

all three reviewer deployments, versions, regions, adapter and request-profile hashes;

primary, secondary, and third raw-response manifests;

combined judgment file SHA-256;

final pack manifest and decision SHA-256;

exact role coverage and agreement counts;

Azure job/resource IDs and sanitized role assignments;

test run IDs and baseline comparison;

cleanup/retention actions.

The outer bundle manifest is written last with create-only Blob semantics. Never overwrite an existing run prefix or mutate the generation pack after upload.

5. R2 — Azure verification before the scientific generation

All validation runs in Azure.

Run focused tests covering at least:

exact protected-file hashes and frozen protocol binding;

exact addendum/rubric/request-profile snapshot equality;

every semantic label boundary in the rubric fixtures;

provider response schema parsing and refusal of prose/extra keys;

no automatic conversion of transport or schema failures into semantic labels;

one-row-per-request and no cross-row session state;

prohibited reviewer fields absent from every request;

primary coverage exactly 900;

sampled secondary component exactly 180;

forced-secondary union behavior;

secondary role set exactness;

third selection only on disagreement;

one reviewer cannot hold two roles for a row;

finalizer refusal of incomplete or extra role sets in the wrapper;

generation-manifest and records-hash binding;

outer manifest written last and create-only upload behavior;

positive and mutation/negative controls for the actual code path.

Then run the exact full suite in Azure. The acceptance comparison is:

baseline 3067 passed / 15 skipped / 2 failed;

every newly added test passes;

the same two disclosed parser-seal failures may remain;

zero new failure is allowed.

Do not weaken a test, xfail a new defect, or create a meta-audit of the test harness. Fix ordinary implementation defects, add a direct regression test, rerun the relevant Azure gate, and continue.

Build the dedicated review/finalization image in the existing ACR path, pin every dependency, verify the baked source and addendum hashes during the build, reference it by digest, and lock its tag and manifest against write/delete. Do not rebuild or retag the locked target-generation image.

After the provider qualification receipt, addendum, implementation, tests, and locked review image are committed and pushed, recheck origin/main, clean worktree, protected-file hashes, and all zero scientific counters. Only then may target inference start.

6. R3 — execute the one Phase 1.0D target-generation run

Use the existing launcher:

infra/azure/scripts/19_run_phase1_0d_confirmation.sh

Resolve the full 9cde1d95... image-tag commit from Git and pass it explicitly as PROJECT_SHA. Verify that the resolved ACR manifest digest is exactly:

sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4

Use:

existing resource group rg-jspace-observation-sea;

existing ACA environment cae-jspace-observation-sea-vnet2;

workload profile gpu-t4;

fresh UTC run ID;

REPLICA_TIMEOUT=21600;

GENERATION_TIMEOUT_SECONDS=21300;

replica retry limit 0;

parallelism 1;

replica completion count 1;

digest-only image reference;

managed identity only;

no mounted Azure Files;

a Blob run prefix proven empty before start.

The timeout increase is a prospective operational safeguard for the registered 900-unit run. It changes no prompt, seed, decoding parameter, output budget, stopping rule, or metric. Record the accepted control-plane values before job start.

Do not run a target-item pilot, partial generation, timing sample, or second replica. Exactly one formal execution is authorized.

Monitor it to a terminal state. On success, verify and retain the uploaded pack before any cleanup. It must contain 900 unlabelled records and report AWAITING_SEMANTIC_REVIEW; that is the correct generation-stage status, not a failure.

If the execution times out, fails, is canceled, or terminates without a valid manifest, do not rerun under this authority. Preserve logs and exact partial-state facts and stop as BLOCKED_ON_AZURE_EXECUTION_<EXACT_CAUSE>. A failed attempt may already have executed an unknown prefix of the registered generations, so a fresh retry requires a new operator decision.

7. R4 — execute review, arbitration, and finalization

After a valid generation pack exists, run the staged public CPU review job in this exact order:

verify generation pack;

900 primary reviews with gpt-5.6-sol;

deterministic secondary selection;

all required secondary reviews with Mistral-Large-3;

deterministic disagreement selection;

all required third reviews with DeepSeek-V4-Pro;

exact judgment-set verification;

frozen finalization;

independent arithmetic/provenance check over the completed pack;

outer bundle manifest and Blob upload.

The arithmetic/provenance check may recompute counts and hashes after results exist. It may not change labels, prompts, samples, metrics, thresholds, gates, or eligibility. A mismatch preserves both objects and stops as BLOCKED_ON_RESULT_PACK_INTEGRITY; it does not choose the more favorable result.

No provisional accuracy, pilot-cell list, or headroom claim may be emitted before all required roles are complete and the frozen finalizer succeeds.

8. R5 — scientific artifact pack and ledgers

Create one public, immutable repository artifact root:

artifacts/phase1-headroom-confirmation/track-b/<RUN_ID>/

Organize it so generation bytes, review receipts, finalization bytes, and the outer manifest remain distinguishable, for example:

generation/ — byte-identical verified generation pack;

review/primary/ — primary judgments and raw-response manifest;

review/secondary/ — selection receipt, judgments, raw-response manifest;

review/third/ — disagreement receipt, judgments, raw-response manifest;

review/all_judgments.json — exact combined closed-form judgments;

final/ — byte-identical frozen finalizer pack;

reporting/ — derived cell metrics, paired differences, paper table, figure data, deviations, reviewer agreement, provider usage/cost;

00_execution_receipt.json — the outer binding receipt;

artifact_manifest.json — outer manifest written last.

Do not commit credentials, full endpoint URLs containing sensitive identifiers, subscription/tenant IDs, authorization material, or mutable signed URLs.

Report at least:

all 45 registered task-family x difficulty x arm cells at row/cell level;

semantic accuracy and Wilson 95% interval;

paired condition differences;

truncation, invalid, loop/repetition, placeholder, unresolved, and no-CoT violation rates;

primary label counts;

required secondary count, sampled/forced overlap, and actual secondary count;

primary/secondary agreement and disagreement counts;

third-review count and final unresolved count;

parser/reviewer agreement separately and explicitly not as inter-reviewer agreement;

provider request/retry/malformed-response counts, token usage, latency, and measured or clearly labeled estimated cost;

every RQ2 pilot-candidate cell or an empty list;

what the result does and does not establish.

Update consistently:

README.md

docs/run_log.md

docs/decision_log.md

paper/evidence_ledger.csv

paper/claim_evidence_matrix.md

paper/limitations_ledger.md

paper/methods_ledger.md

paper/artifact_index.csv

figure and table registries

Record explicitly that:

the addendum was frozen before inference because the earlier protocol did not name executable reviewer providers or a full label rubric;

semantic reviewers are authoritative under DR-01, but no independent oracle bounds their accuracy;

inter-model agreement is consistency, not correctness proof;

the RQ2 gate selects substrates and is not a population-performance claim;

no Phase 1.0D result alone establishes hidden reasoning, internal representations, invisible CoT, or J-space.

Commit and non-force push every reproducible checkpoint and the final public artifact pack. Verify remote commit/tree and a clean worktree.

Do not start the J-lens scaling run, the J-lens validity benchmark, or the RQ2 mechanistic pilot under this prompt. The next prompt must be based on the actual Phase 1.0D result rather than an assumed one.

9. Result interpretation and terminal states

Use the existing frozen decision vocabulary and data. Do not create a favorable substitute result.

If one or more cells pass, the successful handoff state is:

PHASE_1_0D_COMPLETE_RQ2_PILOT_CANDIDATE_CELLS_FOUND

The decision object's existing result remains RQ2_PILOT_CANDIDATE_CELLS_FOUND.

If no cell passes, the terminal scientific state is:

HEADROOM_NOT_ESTABLISHED

That result is final for the frozen 1.0D design. Do not rerun, lower thresholds, relabel rows, change reviewers, reuse Phase 1.0C items, choose a family post hoc, or restart parser work.

Other permitted terminal states are only:

BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION

BLOCKED_ON_FROZEN_PHASE_1_0D_DRIFT

BLOCKED_ON_MALFORMED_SEMANTIC_REVIEW_RESPONSE

BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT

BLOCKED_ON_RESULT_PACK_INTEGRITY

BLOCKED_ON_AZURE_EXECUTION_<EXACT_CAUSE>

NONTERMINAL_CHECKPOINT_<EXACT_NEXT_GATE>

Do not return to BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE, BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY, parser-v3 validation, or any audit-loop state.

10. Cleanup and retention

Retain permanently and do not alter:

the locked target-generation image and digest;

the locked review/finalization image and digest;

generation, review, and final result Blob packs;

provider qualification and raw-response hash receipts;

committed public artifact pack;

all prior historical artifacts and parser receipts.

ACR Task QuickRuns are ephemeral. Record every run ID.

Do not delete newly created reviewer deployments, identities, or role assignments during the same scientific turn unless a security defect requires immediate revocation. They are pay-per-token/serverless resources with no authorized subsequent inference in this prompt; record their idle-cost status and leave exact cleanup as an explicit operator decision in the handoff. Never delete a resource group unless it was created by this round, is proven to contain only round-created resources, and the operator separately authorizes deletion.

11. Final handoff

Return:

final state, exact origin/main commit/tree, clean/fast-forward status;

proof the starting commit/tree and protected bytes were preserved;

exact addendum and rubric hashes;

exact reviewer provider/model/version/deployment type/region/request-profile/reviewer IDs;

provider smoke receipt and proof no target output existed before it passed;

review-image repository, tag, digest, lock state, and build provenance;

target generation run ID, ACA execution ID, timeouts, duration, GPU, image digest, model revision, and Blob manifest hash;

generation count, failed-generation count, and proof 900 rows entered primary review;

primary/secondary/third counts, selection math, agreement/disagreement, final unresolved count, retries, schema failures, token use, latency, and cost;

final decision, all pilot-candidate cells, complete cell metrics, and exact decision hash;

artifact root, outer manifest hash, all paper/ledger updates, and public/private classification;

every Azure run/resource ID and exact retention/cleanup action;

full-suite result against 3067 / 15 / 2, with zero new failures;

what the result establishes and does not establish;

the smallest next scientific gate:

if candidate cells exist, freeze the J-lens scaling/validity protocol before any RQ2 pilot;

if headroom is not established, record that no RQ2 pilot is licensed on this bank, while J-lens instrument validity may be pursued as a separate scientific question.

12. Primary official references

Pin and cite these in the repository where implementation facts rely on them:

GPT-5.6 model/version and structured-output capability: https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure

Azure OpenAI reasoning parameters and Entra authentication: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning

Mistral/DeepSeek model versions and Azure-hosted capabilities: https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure

Global Standard region/version availability: https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability

Foundry authentication and authorization: https://learn.microsoft.com/en-us/azure/foundry/concepts/authentication-authorization-foundry

Foundry RBAC: https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry

Azure OpenAI keyless RBAC role: https://learn.microsoft.com/en-us/azure/developer/ai/keyless-connections

Azure Container Apps Jobs: https://learn.microsoft.com/en-us/azure/container-apps/jobs

The implementation must use the exact service behavior observed and pinned before inference. Documentation is evidence of supported capability; the Azure control-plane receipt is evidence of the deployment actually used.