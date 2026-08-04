You are GitHub Copilot CLI operating the repository:

Alanjiao1988/J-space-observation

This is a new, independent operator execution authorization. It is not a requestfor a plan, a review, or another reviewer-instrument revision. Carry the workthrough exactly one of the permitted terminal states, verify every materialclaim in Azure, commit in small auditable checkpoints, fast-forward push eachcompleted checkpoint to origin/main, and return the exact handoff required in§12.

The authorization is deliberately narrow:

preserve the one completed Phase 1.0D generation byte-for-byte;

preserve the entire v1 and v2 semantic-review instruments byte-for-byte;

diagnose and, only if possible without changing semantic behavior, increasetransport capacity on the three already-registered deployments;

if and only if the capacity gate passes, launch one new review-only recoveryexecution using the already-locked v2 image;

never generate target output again;

never run qualification or smoke again;

never create RV3, change a reviewer, or revive parser work;

if the recovery execution cannot complete and seal a result, permanentlyclose the Phase 1.0D review route and return the scientific mainline to thestill-unspent J-lens S3 validity-protocol gate.

Do not pause for another operator choice inside this authorization. A capacitygate that cannot be satisfied stops before inference. A provider-bearingrecovery execution, once started, is the final Phase 1.0D semantic-reviewexecution authorized by this project.

1. Exact starting state

Require all of the following before editing or making an Azure write:

origin/main = d145b1c79db8b6866fadaa8875c2374a813a7e31
tree        = b4329a4062415cf7cb3b058d3defe6da7c14f25c
worktree    = clean
history     = fast-forward only; 5ae85cb838ff2c8d296ee90b10f1ca2e9f885b0a is an ancestor

The recorded test baseline is:

3336 passed / 15 skipped / 2 failed

The two failures are only the disclosed pre-existing cases intests/test_parser_v3_seal_job.py. No new failure is allowed.

Require these protected-byte facts:

Set

Count

SHA-256 / rollup

v1 protected files

152

436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd

v2 protected files

36

ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a

v2 protected manifest file

1

9b7705ccdc630bce5fe77503c35ff6644cd37f876b886fa9cd8a14f8c7012e77

v1 addendum

1

582640de645030daf957fbc3e5c7947008b78d1596b674687a73f20ba749bdc3

v1 rubric

1

a0d5b22bd6d4ef1012db676ff3431c3d2e6825f1ec4ade1a7c7801817ba8765d

v1 gate manifest

1

d70c0c9925fdd9d764f17068d1c712e2c1ff1fdde4f75ed266b4b08018b0083f

v2 authority prompt

1

7b93c90a299ff4e77b83d4633624053f8ce53afcd04279ca3050c5ab14428e19

v2 addendum

1

20e5f30455f90a95c07e05e080e51443511c957e09d4ce97a42bd118bd9268e4

v2 rubric

1

91f687087fbd56cb07369da7a4c28beddb49d822f2d6fa1832cb3849a26f60e3

v2 fixture bank

20

41adb246ec36d5ac7b16f5144c466351b93abe8b3f56dc811e58a789b197e75f

Do not rely on abbreviated values when verifying bytes. Read the full expectedhashes from the committed protected manifests and compare full values.

Require these immutable image facts:

generation image digest = sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4
v1 review image digest  = sha256:d9e887e68cccf7472e956785cda3ad7cf5f3902daea9287fc7b72c357f473e10
v2 review image digest  = sha256:b3cf2c5933fe296c6a4d59eba9d73c3f10fc42bdddc494b25b679ca679b449dd
v2 review image commit  = 1b56f775b5457e2e11124559052ad4caf028fdad

All referenced tags and manifests must still report bothwriteEnabled=false and deleteEnabled=false. Do not rebuild, retag, copy,import, unlock, or replace any image.

Require these completed generation facts:

generation run id       = 20260804T154518Z
generation execution    = job-jspace-p10d-confirmation-pdlhmah
source Blob prefix      = phase1-headroom-confirmation/20260804T154518Z/
source object count     = 8
selected items          = 300
records/work units/rows = 900 / 900 / 900
failed generations      = 0
source manifest SHA-256 = 76accb0f675130989f3db698ecfeaa8736f288980026cdaca0e8413c05234536
source status           = AWAITING_SEMANTIC_REVIEW

Require these v2 gate facts:

qualification run       = 20260803T230642Z
qualification receipt   = fc18950ab10ae576559d8ab2102f4c4363428f0c5d8619e762488435a4b56875
qualification manifest  = 9e942f49667ac15ec0c0cbccdbc12af39612079e399f9bde6de025268fd40206
smoke run               = 20260803T235227Z
smoke result            = 60/60 exact matches
smoke receipt           = c1bd6cbbcf888511cfee9da48111e7950f0c746988937a02a386dfcc574137fc
smoke manifest          = aa0aabb37a9a41bea476fd5e612fc32208af9495316e30ad98081481a07a3c43

Require these failed formal-review facts:

formal review run       = 20260804T181247Z
formal execution        = job-p10d-rv2-r-d4a84a59bc28a91f-tjzwlse
terminal state          = BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT
terminal exception      = primary exhausted 8 identical attempts; last status 429 error None
old formal lock SHA-256 = d7b184b486e757ba0a7702c41300157627e03616b873555d87ea27ada7d7e93f
old result prefix       = phase1-headroom-confirmation-review-v2/20260804T181247Z/
old result object count = 0
terminal archive hash   = 41694a6b9593756d3cbed3014367887567f5e785840dce86bceb2da41a39c204

The old formal-review Job must still have exactly one execution and thegeneration Job must still have exactly one execution. The old result prefixmust remain empty. If any starting fact differs, make no provider call and end:

BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_STARTING_STATE_MISMATCH

Record the exact mismatch. Do not repair history to make the gate pass.

2. Binding interpretation of the failed execution

Preserve the existing terminal archive and all ledgers. Do not relabel the oldformal execution as incomplete, successful, resumed, or retried.

The following interpretation is binding:

The source pack was independently rebuilt as 900 ordered rows.

The first formal v2 execution made concurrent primary requests.

At least one primary row exhausted eight registered byte-identical transportattempts and ended with HTTP 429.

Other concurrent requests were in flight, so the exact aggregate call countand exact valid-response count are not recoverable.

No judgment, response, semantic label, metric, candidate, or decision wassealed. None may be reconstructed.

Therefore the first formal execution establishes no Phase 1.0D headroomresult and cannot contribute a row to a later result.

This authorization accepts one unavoidable limitation: the recovery executionwill submit all required rows from the beginning, so an unknown subset might besubmitted again after having received an unpersisted valid response in the oldprocess. Call this unquantifiable prior-response resampling exposure. It isnot a continuation of the eight retries and it is not evidence that zero validresponses existed.

The exposure is methodologically tolerable for this one recovery only because:

no old response body, label, judgment, token count, latency, or metric wasobserved or used to select which rows are resubmitted;

every required row is resubmitted under one uniform rule, rather than onlyrows with undesirable labels;

the old execution is excluded in full from all scientific denominators;

the recovery result, if complete, is derived only from the new sealed bundle;

the exposure is disclosed permanently in the limitations ledger and everyfuture use of the Phase 1.0D result.

Do not describe the combined history as one formal call, one formal execution,or exactly 900 provider requests. The correct history after a recovery launchis: one generation execution, one failed formal-review execution withunrecoverable partial transport state, and one separately authorized formalreview recovery execution.

3. Non-negotiable exclusions

3.1 Frozen scientific and semantic bytes

Do not change, directly or indirectly:

the Phase 1.0D base protocol, task bank, task IDs, sample, prompts, arms,decoding, seeds, generation budgets, model, tokenizer, thresholds, metrics,arbitration, or interpretation;

any generated row, review-form row, source manifest, source object name, orsource Blob byte;

the v1 correction, v1 addendum, v1 rubric, v1 fixtures, or v1 evidence;

the v2 authority, addendum, rubric, fixtures, expected labels, role profiles,reviewer IDs, providers, deployments, model versions, endpoint paths, APIversions, presented/prohibited fields, JSON schemas, output caps, selection,arbitration, or finalize rules;

max_in_flight_per_deployment=8;

the eight-attempt retry policy, retry status list, backoff parameters, jitter,timeouts, or byte-identical-request requirement;

the registered request bodies, including primaryreasoning_effort=medium, max_completion_tokens=4096, store=false, andstrict JSON schema;

the Mistral and DeepSeek request parameters;

any immutable image or protected manifest.

Do not add Retry-After handling now. Microsoft recommends honoringretry-after-ms, but that behavior was not part of the frozen v2 image. Thisrecovery resolves capacity outside the semantic image; it does not create a newtransport implementation after seeing the failure.

3.2 No additional inference before the recovery execution

Do not run:

provider qualification;

the 20-fixture smoke or any subset of it;

a new synthetic probe;

a one-row target probe;

a quota test prompt;

a dry-run chat completion;

any call to primary, secondary, or third outside the single recovery Job.

All capacity checks before the Job must use Azure Resource Manager, AzureMonitor, repository bytes, and Blob metadata only. No inference endpoint may becalled to prove capacity.

3.3 No alternate route

Do not:

create or use a new deployment, resource, region, provider, model, version,route, or API version;

use PTU, priority processing, spillover, batch inference, a gateway, or asecond endpoint;

load-balance or distribute rows;

reduce max_completion_tokens or another request budget;

reduce, increase, pace, or otherwise change registered concurrency;

change worker ordering or split one role into multiple executions;

run reviewers locally;

use API keys, SAS, account keys, connection strings, client secrets, or localauthentication;

revive parser-v3, use parser output as a final label, run J-lens, or start anRQ2 pilot;

delete any Job, execution, Blob, image, deployment, identity, role record,lock, or scientific artifact.

3.4 No new infrastructure program

This is one recovery launcher and one capacity certificate, not a new auditproject. Do not create a new reviewer protocol, holdout, fixture bank, schemaregistry, private-link topology, provider abstraction, generic orchestrationframework, or multi-round approval loop.

Parser remains permanently triage-only under DR-01. Semantic review is theauthority for this behavioral experiment; this does not reopen parser work.

4. Freeze this recovery authority before capacity writes

Persist this prompt unchanged at:

docs/prompts/phase1_0d_review_only_transport_recovery_prompt.md

Record its full SHA-256. Add one concise decision record that:

cites the exact old terminal receipt and archive hash;

authorizes at most one provider-bearing recovery execution;

preserves all v1/v2 protected bytes and the one generation;

discloses unquantifiable prior-response resampling exposure;

defines the capacity-only gate in §5;

states that there is no second recovery execution;

states that failure after recovery inference permanently closes this reviewroute without a Phase 1.0D result.

Use the next unused IDs in the existing sequences. Based on the starting state,the expected next records are D28, L-54, and M-18, but verify that they areunused rather than overwriting them. Add a CL-05 note. Do not create a newscientific evidence item merely for writing an authorization.

Implement and test all non-inference tooling, commit, and fast-forward push itbefore any capacity mutation or provider call. Re-run both protected-byterollups in Azure at this commit.

5. Transport-capacity gate

The failed code counted max_completion_tokens=4096 in every primary request,used eight workers, did not honor the 429 retry-after-ms response header, andkept other requests in flight while one row retried. Azure documents that TPMenforcement estimates prompt tokens plus the configured maximum completionbudget, that RPM is enforced over short burst windows, and that unsuccessfulrequests can continue to count toward the limit. It also documents that quotamust be allocated to the specific deployment, not merely available at thesubscription level.

Use only these official control-plane surfaces:

quota and rate-limit behavior:https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/quota

quota tiers and current gpt-5.6-sol limits:https://learn.microsoft.com/en-us/azure/foundry/openai/quotas-limits

Foundry-model quota guidance:https://learn.microsoft.com/en-us/azure/foundry/foundry-models/quotas-limits

deployment GET:Microsoft.CognitiveServices/accounts/deployments, API 2024-10-01

deployment PATCH, only when §5.4 permits it:Microsoft.CognitiveServices/accounts/deployments, API 2024-10-01

subscription/location Usages API and Model Capacities API, API2024-10-01.

Do not infer live limits from billed-token metrics alone.

5.1 Registered deployments

The three deployments remain exactly:

Role

Account / deployment

Model version

Profile hash

primary

aj-gpt56-25-943b-eastus2 / gpt-5-6-sol-global

gpt-5.6-sol:2026-07-09

5b2352bf8428e0c278397b24efa2469cbb94692be64f8e0b50e878c3c85c97af

secondary

aif-jspace-p10d-review-eastus2 / mistral-large-3-global

Mistral-Large-3:1

35ebb8afc283a17baa12cf422cb952a5d088bd5690e1a731b9f76fd1b3af2b8e

third

aif-jspace-p10d-review-eastus2 / deepseek-v4-pro-global

DeepSeek-V4-Pro:2026-04-23

5361270acc780b00d73de0dff9b51baefcd103d0f9cd0678a923b8dc3749bf4f

Resolve resource groups from the existing committed/Azure evidence. Do notguess. Verify the complete profile hashes from the v2 protected bytes.

5.2 Read-only capacity evidence

Before any mutation, capture sanitized control-plane readbacks for all threedeployments:

account name, deployment name, endpoint host, location;

deployment etag, provisioning state, deployment state, SKU name andcapacity;

exact model format, name, version, and version-upgrade option;

current capacity and every returned rate-limit rule, normalized to RPM andTPM without discarding the original units/window;

dynamic-throttling setting;

spillover/parent deployment fields;

subscription quota tier;

relevant Usages API currentValue and limit lines;

relevant Model Capacities API records;

Azure Monitor request/token/429 metrics for the preceding 60 minutes,dimensioned by deployment when the platform exposes that dimension;

all retained project Jobs capable of reaching the inference accounts andtheir execution counts.

Redact subscription IDs, tenant IDs, bearer tokens, authorization headers, andother credentials. Hash the canonical unsanitized readback in memory, but donot commit or print sensitive values. Persist only the minimum sanitized factsneeded to reproduce the gate.

5.3 Mechanical capacity floors

Normalize the live deployment rate limits to per-minute units. The gate passesonly if every role meets both floors:

Role

Minimum assigned TPM

Minimum assigned RPM

primary

1,000,000

1,000

secondary

500,000

500

third

1,000,000

500

These are capacity floors for the unchanged eight-worker workload, not a claimthat Azure guarantees zero transient throttling. They are intentionally basedon the configured maximum output budgets, not the 735 visible tokens observedin the small smoke.

The gate additionally requires:

all three deployments are Running/Succeeded and exact model/version/SKUreadbacks match the frozen profiles;

no spillover or parent deployment is configured;

local authentication remains disabled on both accounts;

the project UAMI and Entra routes remain the registered identities/routes;

no non-project traffic is observed on these dedicated deployments during acontinuous 15-minute quiet window immediately before lock creation;

at least one complete one-minute rate-limit window has elapsed since the lastrequest or capacity change;

the old formal lock and empty old result prefix remain unchanged;

the recovery result prefix and recovery lock do not exist;

zero recovery Jobs/executions exist.

If a rate-limit field is absent, ambiguous, or cannot be normalized, do notsubstitute a quota-tier maximum for the missing deployment allocation. The gatefails closed.

5.4 The only permitted capacity mutation

If and only if a registered deployment is below its §5.3 floor and enoughcurrently unallocated quota is available, you may increase sku.capacity onthat same deployment to the smallest allocation that makes its returned TPMand RPM meet the floor.

The mutation must:

use the deployment's current etag as a concurrency guard;

use ARM API 2024-10-01;

change only the capacity allocation;

not reduce, delete, pause, rename, or modify any other deployment;

not consume quota by shrinking an unrelated deployment;

not change SKU name, model, version, upgrade option, RAI policy, spillover,network, auth, endpoint, or account properties;

poll to a successful stable readback;

compare before/after canonical structures with an explicit allowlist ofcapacity, rate-limit, provisioning, and etag fields;

stop if any non-allowlisted field changes.

Quota allocation by itself is not an inference call. Do not request a quotaincrease, create another deployment, or work around an unavailable floor insidethis authorization. If existing unallocated quota is insufficient, record thecapacity certificate and end before inference as:

BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY

This state does not consume the one provider-bearing recovery execution. Thesame frozen authority may be resumed only after an operator independently makesthe required quota available on the same deployments; it does not authorize anautomatic poll, quota request, alternate deployment, or model change.

Do not automatically scale capacity back down after the review. Record theallocation and leave any later reallocation to a separate operator decision.

5.5 Capacity certificate

Write a canonical, public, sanitized capacity certificate before inference. Itmust include:

authority prompt hash and starting commit/tree;

all protected rollups;

old terminal archive and formal-lock hashes;

source/gate/image identities;

before/after deployment capacity and normalized rate limits;

exact capacity mutations, or none;

quiet-window evidence;

each mechanical gate with expected/observed/pass;

explicit provider_calls=0 and the method used to prove it;

the ordered SHA-256 rollup of all 900 possible frozen request bodies for eachrole, computed offline from the source review form and frozen request builder;

capacity_gate_passed;

certificate SHA-256.

Upload/create the certificate and manifest with create-only semantics. Commitand push the sanitized copy before creating the recovery lock.

If the gate fails, there must be no recovery lock, Job, execution, resultobject, or provider request.

6. Recovery launcher

Create one narrow operator launcher, derived mechanically from the existing v2formal launcher. It is not part of the review image and may not implementreview semantics.

The launcher must be structurally incapable of:

qualify or smoke mode;

generation mode;

selecting another image, deployment, route, provider, model, profile,addendum, rubric, fixture bank, source pack, gate receipt, concurrency, retrypolicy, or result root;

accepting target identities through arbitrary CLI/environment overrides;

starting more than one recovery execution.

Pin inside the launcher:

the v2 review image digest;

review image commit 1b56f775b5457e2e11124559052ad4caf028fdad;

source generation run/prefix/manifest;

qualification and smoke receipt/manifest hashes;

old terminal archive and old formal-lock hashes;

capacity certificate hash;

all three full role-profile hashes;

v1 and v2 protected rollups;

replicaRetryLimit=0;

one replica, one completion, one container;

CPU/memory, identity, command, environment, route, and execution timeoutequal to the prior registered formal Job except for the new recovery run ID,recovery Job name, capacity-certificate binding, and new result prefix.

Provision and fully read back the inert Job before claiming the recovery lock.Tests must prove that the normalized container command and environment differfrom the old formal Job only in the explicitly allowed recovery identityfields. The semantic request bodies must be identical to the offline hashes inthe capacity certificate.

Do not build a new review image.

7. Unique recovery lock and execution

Use one create-only global lock under a new namespace, for example:

phase1-0d-semantic-review-v2/transport-recovery/formal-review-lock.json

The exact namespace must be frozen in code and tests before inference. It maynot be supplied by the caller.

The lock must bind:

artifact/schema version;

authority prompt hash;

starting and launcher commits;

recovery run ID and Job name;

v2 image digest and image commit;

source generation run/prefix/manifest;

v2 gate receipt/manifest hashes;

v1/v2 protected rollups and profile hashes;

old formal run, execution, lock hash, terminal archive hash, and empty resultprefix;

capacity certificate hash and passing state;

three offline request-body rollups;

exact recovery result prefix.

Before creating the lock, prove:

the capacity certificate passes;

the recovery lock is absent;

the recovery result prefix has zero objects;

there is no recovery execution;

the source and old terminal state are unchanged;

all temporary launcher permissions are exact and time-bounded;

the inert Job readback matches the pinned contract.

Create the lock atomically with If-None-Match: * / overwrite false. Then startexactly one Container Apps Job execution.

If the start response is ambiguous, inventory executions before doing anythingelse. Never issue a second start automatically. If zero or more than oneexecution cannot be proven, stop as:

BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_LAUNCH_AMBIGUITY

Do not use a platform retry. Do not restart a failed replica. Do not create asecond Job to continue rows.

Any provider-bearing execution consumes the recovery allowance, regardless ofhow many responses complete.

8. Execute the unchanged review and finalize

The locked v2 image must perform the existing sequence unchanged:

download exactly the eight source objects;

independently rebuild exactly 900 ordered records/review rows;

primary-review exactly 900 rows under the frozen profile;

compute the frozen secondary sample/forced set from the complete primaryjudgments;

secondary-review exactly the required rows;

compute the frozen third-review disagreement set;

third-review exactly the required rows;

verify coverage and per-call receipts;

combine judgments and apply the frozen arbitration rule;

finalize the source pack;

independently verify all labels, metrics, candidates, decision, provenance,and manifest membership;

publish the complete result bundle with manifest written last andcreate-only semantics.

No reviewer sees another reviewer's label or the fact that disagreement exists.No valid response is semantically retried inside the recovery execution.

If the result seals successfully, accept the frozen decision exactly:

RQ2_PILOT_CANDIDATE_CELLS_FOUND, if at least one cell passes every frozengate; or

HEADROOM_NOT_ESTABLISHED, if no cell passes.

HEADROOM_NOT_ESTABLISHED is a valid completed scientific result. Do not loweror reinterpret a gate.

Even if candidate cells exist, do not run RQ2 in this authorization. The resultonly supplies behavioral substrate candidates. J-lens S3 validity remains aseparate prerequisite and its review allowance remains unspent.

9. Failure after recovery inference

If any transport, malformed-response, persistence, integrity, timeout, Azure,or verification failure occurs after the provider-bearing recovery executionstarts:

do not rerun any row, role, stage, Job, or execution;

do not change capacity, concurrency, backoff, timeout, request parameters,model, deployment, route, code, or image to try again;

do not reconstruct responses or judgments from logs, token metrics, requestIDs, or provider billing;

do not use any partial response, label, agreement, cell, or metric;

independently inventory source, old result, recovery result, old lock,recovery lock, Jobs, and executions;

seal a terminal archive with bounded console evidence and exact uncertaintystatements;

end as:

CLOSED_PHASE_1_0D_WITHOUT_RESULT_TRANSPORT_RECOVERY_EXHAUSTED

Do not call this HEADROOM_NOT_ESTABLISHED; that scientific result requires acomplete reviewed pack. CL-05 remains preliminary on Phase 1.0C alone.

After this closure there is no second transport recovery, RV3, provider swap,human relabeling round, or parser fallback under this project authority. Thenext scientific gate is J-lens S3 validity-protocol design.

10. Evidence, tests, Git, and retention

10.1 Required tests before capacity mutation

Add focused tests proving at minimum:

both protected rollups and every pinned full hash;

exact starting-state/old-terminal verification;

capacity-rate normalization and all floors;

fail-closed behavior on absent or ambiguous rate-limit fields;

capacity PATCH allowlist and etag guard;

no inference in the capacity checker;

offline request-body rollups for all 900 possible rows per role;

launcher fixed identities and absence of qualify/smoke/generation paths;

no concurrency/retry/request override surface;

one create-only recovery lock;

zero/multiple/ambiguous execution defenses;

no platform retry;

old result-prefix immutability;

recovery result-prefix create-only behavior;

successful-result and terminal-failure archive membership;

no parser or J-lens entrypoint reachable from this launcher.

Run focused tests and the full suite in Azure. The final full-suite comparisonmust report change from 3336 passed / 15 skipped / 2 failed, with no newfailure. Do not repair the two parser baseline failures in this round.

10.2 Git order

Use small fast-forward commits in this order:

recovery authority, decision/limitation/method records, and non-inferencetests;

capacity checker/certificate schema and recovery launcher;

passing or blocked capacity certificate;

if launched, exact recovery lock/readback evidence;

successful result archive or terminal recovery archive and ledger updates;

final verification/handoff corrections only.

Push every completed checkpoint. Never force-push, amend a pushed commit,rewrite history, or mix unrelated work.

10.3 Artifact ordering

For every new archive:

canonicalize JSON deterministically;

hash every member;

write the manifest last;

use create-only Blob semantics;

re-download/re-read and verify bytes;

commit only sanitized public evidence;

never claim an absent fact from an empty log.

On success, create the next evidence-ledger item for the completed Phase 1.0Dreviewed result. On capacity block or post-inference failure, record operationalevidence only and do not fabricate a scientific result.

Update at least:

docs/run_log.md;

docs/decision_log.md;

paper/methods_ledger.md;

paper/limitations_ledger.md;

paper/evidence_ledger.csv when a scientific result exists;

paper/artifact_index.csv;

paper/claim_evidence_matrix.md CL-05;

README status.

10.4 Retention

Retain all old and new Jobs, executions, locks, images, Blob packs, identities,deployments, certificates, and scientific artifacts. Remove only temporary roleassignments created by this launcher after proving they are no longer needed,and record their exact assignment IDs and verified absence. Do not delete anyresource or artifact.

11. Claim boundary

Never claim that this recovery establishes:

reviewer accuracy or human ground truth;

zero valid responses in the first failed formal execution;

an exact combined provider-call count across the two formal executions;

absence of response resampling exposure;

target-model reasoning, hidden chain of thought, an internal workspace, or aJ-space;

J-lens validity;

causal mechanism;

RQ2 permission merely because infrastructure completed.

A successful recovery establishes only:

the frozen 900-row generation pack was completely labelled by the registeredv2 panel in the separately authorized recovery execution;

the frozen Phase 1.0D behavioral gates produced their recorded result;

the result carries a permanent limitation that an unknown subset of requestsmight have received unpersisted valid responses in the earlier failed process.

A failed recovery establishes only that the project could not obtain a completesemantic-review result under the registered reviewer path after one explicitlyauthorized capacity-gated recovery.

12. Required final handoff

Return one exact handoff containing:

terminal state;

origin/main, tree, ancestor proof, worktree status, and push mode;

full v1/v2 protected rollups and all immutable image digests;

old generation and failed formal-review identities, unchanged;

recovery authority prompt path/hash and decision record;

complete sanitized capacity certificate:

before/after allocations;

normalized TPM/RPM;

quota/capacity readbacks;

quiet-window evidence;

mutations or none;

gate outcome;

explicit count of provider calls before recovery launch (0 required);

recovery lock, Job, execution, result prefix, and manifest identities, iflaunched;

exact provider-call/valid-response/retry/token/latency counts for the recoveryexecution when recoverable, separated by role;

primary/secondary/third judgment counts, final-label counts, agreement,metrics, candidates, decision, and decision hash on success;

exact uncertainty boundary on failure, without reconstructing partial state;

unquantifiable prior-response resampling exposure disclosure;

focused and full Azure test results versus the baseline;

all Azure run IDs and all retained resources;

temporary role-assignment IDs and verified teardown status;

a precise statement of what the round establishes and does not establish;

the smallest next scientific gate.

End with one of these states only:

BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_STARTING_STATE_MISMATCH

BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY

BLOCKED_ON_PHASE_1_0D_TRANSPORT_RECOVERY_LAUNCH_AMBIGUITY

CLOSED_PHASE_1_0D_WITHOUT_RESULT_TRANSPORT_RECOVERY_EXHAUSTED

HEADROOM_NOT_ESTABLISHED

RQ2_PILOT_CANDIDATE_CELLS_FOUND

No other success wording is allowed.