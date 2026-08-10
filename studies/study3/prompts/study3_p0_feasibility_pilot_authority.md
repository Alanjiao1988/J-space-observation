Operator authority — Study 3-P0 feasibility pilot

0. Authority, decision, and narrow override

This file is the sole operator authority for one fresh-session Study 3-P0feasibility-pilot round in Alanjiao1988/J-space-observation.

The operator makes the following decision.

Preserve published draft-v0.5 as an unreviewed candidate protocol.

Do not conduct the previously named fourth full independent methods reviewbefore obtaining any empirical feasibility information.

Authorize one physically isolated, tightly capped feasibility pilot on thealready named target roles RT, RL, and RI only.

Use the pilot solely to test whether the registered rendering, tokenization,scoring, parsing, execution, accounting, and resource pipeline is runnable.

Give the pilot no authority to select an interface, set or revise aconfirmatory threshold, answer the research question, resolve OD2 orUR-22, freeze Study 3, or authorize formal development or confirmation.

This decision narrowly supersedes the statements in published draft-v0.5 thatname a fourth independent methods review as the only legal successor andforbid every feasibility pilot. It does not declare draft-v0.5 correct and doesnot reverse, relabel, weaken, or edit any prior review disposition or finding.

The governing distinction is:

formal_execution_authorized = false throughout;

p0_pilot_execution_authorized = true only for the operations and caps inthis authority, and it becomes false when the pilot closes or stops;

all pre-existing formal Study 3 counters remain historical facts; P0 uses aseparate, cumulative, non-resettable pilot counter namespace;

P0 measurements are methods-feasibility observations, not Study 3 evidence.

No other authority may be inferred from this file.

1. Exact starting point and preflight

Repository:

Alanjiao1988/J-space-observation

Required published baseline:

commit: 5b15e0ed0ee109955ef805adab3fc3e25b93e5ed

tree: 62cbfb371fdf273f0b8642c06c05b0741000e6a5

state:STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW

Start in a fresh session and a clean worktree. Fetch origin/main before anywrite and require it to equal the exact baseline above. Require the baselinetree to match, require no untracked or modified user work, and set the operationcontext so authored bytes use LF and committed-blob hashes are not confused byworking-tree newline conversion.

If origin/main moved, the tree differs, the worktree is not clean, the repo isnot the named repo, or any required baseline object cannot be read, stop as:

BLOCKED_ON_STUDY3_P0_STARTING_STATE_INTEGRITY

Do not merge, rebase, force-push, silently adopt a newer commit, or work aroundthe discrepancy.

Preflight reads, hashes, Git inspection, and environment inspection arepermitted. No tokenizer construction, tokenizer call, model download, weightload, GPU allocation, forward evaluation, scoring, or generation is permitteduntil the pre-execution publication gate in §6 passes.

2. Scientific purpose and non-purpose

P0 may answer only these feasibility questions:

Can an independent implementation instantiate the binding v0.5 renderingregistry without an unregistered wording, punctuation, whitespace,ordering, escaping, placeholder, or wrapper choice?

Under the exact pinned tokenizers for RT, RL, and RI, do everyapplicable gate-bearing presentation pair produce distinct token-IDsequences, and do the S1/S2 candidate-token eligibility rules hold?

Can S1 restricted label-token logits, S2 restricted content-token logits,and S3 CPU-only reuse of the S2 logit vector be executed and reconciledwithout missing rows, non-finite values, scorer disagreement, or hidden modelevaluations?

Can the S4 diagnostic path render, use the role-native wrapper boundary,generate a short completion, invoke the pinned parser, retain unparseable asan explicit outcome, and account for prefill and incremental decode cost?

What wall time, peak device memory, prompt-token length, generated-tokencount, failure rate, and runtime batching behavior occur in this small run?

Does this deliberately tiny corpus show any output variation or pairwisediscordance worth considering when calibrating the final protocol?

P0 may not estimate a confirmatory effect size, validate a registered powercalculation, test any draft-v0.5 null, pass or fail any formal gate, select orrank S1/S2/S3, qualify S4, compare checkpoints scientifically, answer theoriginal research question, or make a reasoning-capability claim.

Observed correctness, response variance, and discordance are descriptive atthis sample size. Zero observed discordance is not proof of invariance and isnot by itself a mechanical failure. Pilot effect sizes may never be used tochoose or justify a formal threshold, sample size, alpha, seed, bank, profile,or confirmation rule.

3. Immutable baseline and authorized path scope

3.1 Byte-protected objects

Treat the following as read-only inputs and require their committed bytes toremain identical to the baseline:

all Study 1 and Study 2 scientific, result, review, and state artifacts;

every prior Study 3 independent-review artifact and historical-reviewharness;

studies/study3/protocol/interface_calibration_protocol_draft.json;

studies/study3/protocol/interface_calibration_protocol_draft.md;

studies/study3/protocol/interface_calibration_protocol.schema.json;

studies/study3/protocol/interface_calibration_rendering_registry_v0_5.json;

studies/study3/protocol/interface_calibration_rendering_registry_v0_5.schema.json;

studies/study3/reviews/v0_5_operator_amendment.json;

studies/study3/reviews/v0_5_operator_amendment.md;

studies/study3/reviews/v0_5_operator_amendment.schema.json;

studies/study3/design_receipt_v0_5.json;

studies/study3/analysis/independent_methods_review_packet_v0_5.md;

studies/study3/analysis/design_statistics.py and its committed tables;

every existing Study 3 design, rendering, and methods-review test module;

paper/evidence_ledger.csv, which must remain byte-identical and end atEV-0016.

Do not rewrite draft-v0.5 to pretend it authorized P0. The authority and P0records are a later, separately identified governance layer over an immutablecandidate baseline.

3.2 Authorized writes

The first new repository object must be a byte-identical copy of this authorityat:

studies/study3/prompts/study3_p0_feasibility_pilot_authority.md

All P0 implementation, schemas, manifests, frozen inputs, receipts, logs, andresults must live under:

studies/study3/pilot/p0/

One new test module is authorized:

tests/test_study3_p0_feasibility_pilot.py

Only the following existing governance/index surfaces may be updated, and onlyto record the operator override, P0 lifecycle, exact artifact identities,validation, and handoff:

README.md

docs/decision_log.md

docs/run_log.md

paper/artifact_index.csv

paper/methods_ledger.md

reports/current_status.md

studies/study3/README.md

studies/study3/NEXT_THREAD_HANDOFF.md

studies/study3/RESEARCH_CHARTER_DRAFT.md

No fixed changed-path ceiling is imposed. Every changed path must be necessaryfor P0, belong to the allowlist above, be disclosed with status and byteidentity, and contain no unrelated cleanup. If another path is genuinelyrequired, stop and request authority before touching it.

4. Fixed checkpoints, tokenizers, and execution route

P0 is limited to the three target roles already registered in draft-v0.5:

Role

Repository identity

Immutable revision

RT

deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B

ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562

RL

Qwen/Qwen2.5-Math-1.5B

4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2

RI

Qwen/Qwen2.5-Math-1.5B-Instruct

aafeb0fc6f22cbf0eaeed126eff8be45b0360a35

The tokenizer for each role must be loaded from the same repository identityand exact immutable revision as its model. Record tokenizer class, vocabularysize, special-token map, library versions, downloaded-file identities, and theresolved revision. A branch, tag, floating cache entry, or substituted tokenizeris prohibited.

RP is excluded. Do not select, rank, download, tokenize, load, or call anypositive-reference candidate. Do not create an RP wrapper. OD2, UR-22, theRP canonical qualification wrapper, the RP-specific I4 wrapper, and P3-Q remainunresolved and untouched.

Execution route:

code inspection, editing, Git, hashes, upload, submission, and result readingmay occur from the workstation;

every authoritative CPU validation must run in the registered AzureContainer Registry/container route on a clean exact-commit checkout;

every model operation must run in an Azure containerized GPU job, never on theworkstation and never in GitHub Actions;

use one T4-class 16 GiB GPU or a larger compatible Azure GPU; record the exactdevice and driver/runtime identities;

load the 1.5B checkpoints in fp16, one at a time; quantization, mixedcheckpoint revisions, model conversion, adapter insertion, and remote hostedinference APIs are prohibited;

freeze the container image by immutable digest and pin Python, PyTorch,Transformers, tokenizer, CUDA, and supporting package versions before thefirst tokenizer call.

trust_remote_code must remain false unless the baseline model cannot loadwithout it. If it cannot, stop and report; this authority does not permit asilent trust-policy expansion.

5. Frozen P0 corpus

P0 uses no random seed and creates no development, confirmation, or P3-Q bank.Before any tokenizer or model operation, create and commit a deterministicpilot-only corpus from the existing registered generator and rendering surface.

Register exactly three semantic base-tuple classes:

one K2 identity/copy depth-0 tuple;

one K3 affine_mod10 depth-1 tuple;

one K3 permutation_chain depth-1 tuple.

The concrete values, ground truth, distractors, operation parameters, and allrendered bytes must be explicit in the committed corpus and independentlyrecomputed by the P0 test. They must satisfy every v0.5 validity predicate.

For each contrast cell, derive a distinct pilot base-item identity in thenamespace:

study3-p0-only/<tuple-class>/<contrast-id>

Semantic tuples may be deliberately parallel for coverage, but no base-itemidentity may cross contrast cells. Every pair contains exactly two variants,and both variants stay together. Use the binding v0.5 renderer without changingany normative byte:

S1: K5-P1, K5-P2, K5-P3, K5-S1, K5-S2, K5-S3,K5-A1, K6-SEP, and K6-INSTR;

S2: K6-INSTR only;

S3: the same prompt prefix and model output as S2, rescored on CPU with noadditional model evaluation;

S4 diagnostic: only the K2 tuple, with distinct base identities forK6-SEP and K6-INSTR.

Do not instantiate K6-SEP for S2 or S3. not_applicable remains structuralabsence, not a pass, zero, duplicate, or denominator row.

Store canonical UTF-8/LF corpus bytes, a machine-readable manifest, per-rowSHA-256, an aggregate SHA-256, generator and renderer blob identities, and ahuman-readable census. After the pre-execution commit is published, these bytesare immutable. No item, prompt, expected answer, distractor, nuisance state,variant, wrapper, or allocation may be changed in response to tokenizer ormodel output.

The complete study3-p0-only/ namespace and every semantic tuple used by P0are permanently excluded from every later development, confirmation, P3-Q, andexternal-validity bank. Enforce the exclusion in machine-readable form and in atest. P0 data may not be relabelled or promoted later.

6. Pre-execution registration and publication gate

Before any tokenizer access, model access, or GPU job:

Commit the byte-identical authority copy before any P0 drafting output.

Create under studies/study3/pilot/p0/:

a concise protocol and state machine;

the frozen corpus and manifest;

result and receipt schemas;

a counter ontology that reuses the v0.5 units without conflating asequence-level evaluation with a runtime batched forward call;

tokenizer-gate, model-run, summarization, and validation code;

an Azure container/build definition with frozen dependencies;

negative tests for every fail-closed transition.

Record that draft-v0.5 remains unreviewed, unfrozen, and unauthorized forformal execution; OD2, UR-22, and all RP objects remain unresolved/null.

Run clean CPU-only ACR validation on the exact candidate commit, withGPU_COUNT=0 and CUDA_AVAILABLE=False.

Require all pre-existing targeted Study 3 suites to retain their publishedpass counts, including 276 design/rendering passes and 88 v0.4-review passes.

Run the full suite. The baseline is 4,141 passed, 15 skipped, and exactly thetwo registered historical test_parser_v3_seal_job failures. The P0 modulemay add passes; record its exact node-ID set and reconcile:

final passes = 4,141 baseline passes + net-new P0 passes

Skips must remain 15, and the only failures must be the same two historicalnode IDs with unchanged signatures.

Validate the exact changed-path allowlist, protected bytes, authority byteidentity, corpus identity, operation arithmetic, schemas, and zero pre-P0operation counters.

Publish the pre-execution commit only by non-force fast-forward:

git push origin HEAD:refs/heads/main

Fetch again and require HEAD == origin/main, the recorded tree, a cleanworktree, and unchanged protected bytes.

The published state is:

STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE

The authority ordering proof must show that the authority commit precedes everyP0 drafting artifact and that the published frozen corpus precedes the firsttokenizer call.

If any validation differs, another path is needed, remote main moves, or thepre-execution commit cannot be published exactly, stop without tokenizer ormodel access.

7. Stage P0-T — tokenizer and renderer gate

Stage P0-T is CPU-only, must run in the registered Azure container route ratherthan on the workstation, and may begin only from the exact publishedpre-execution commit.

7.1 Required census

For all three pinned role tokenizers:

Tokenize every applicable pair in the frozen P0 corpus.

Tokenize the complete existing deterministic rendering-fixture census,including all 32 registered nuisance-support states and every applicableprofile/rendering/contrast branch the binding registry exposes.

Record exact prompt bytes, prompt SHA-256, token IDs, token count, tokenizeridentity, role, profile, contrast, rendering, tuple class, and applicability.

Assert that every applicable byte-distinct pair produces distinct fulltoken-ID sequences for every applicable role.

Assert structural absence of S2/S3 K6-SEP rows.

Assert that S1's exact label surface strings each map to one token ID and thefour IDs are pairwise distinct under every required role.

Assert that S2's ten mod-10 answer surfaces each map to one token ID and theten IDs are pairwise distinct under every required role.

Assert that S2 and S3 use identical prompt bytes and token IDs for the sameitem/rendering/role because S3 is a scoring rule, not a new surface.

Reject any unregistered normalization, BOS/EOS insertion policy, chattemplate, whitespace repair, truncation, padding-dependent comparison, ortokenizer substitution.

Every encode operation increments a cumulative P0 tokenizer-call counter. BatchAPIs must still count the number of encoded sequences as well as the runtimebatch call. Missing counters are a failure. The complete tokenizer census mayencode at most 10,000 sequences across all roles and stages; stop before thatcap rather than allowing an accidental cross-product or retry loop.

7.2 Fail-closed behavior

A registry/schema/renderer mismatch, a non-deterministic render, an unexplainedtokenizer identity, a missing census branch, or a counter mismatch stops P0before any model operation as:

STUDY3_P0_STOPPED_ON_TOKENIZER_OR_RENDERER_DEFECT

A genuine token-ID collision does not get repaired after observation. Mark thespecific role/profile/contrast INELIGIBLE_TOKEN_IDS, exclude its model rows,and continue only if at least one genuine I3 contrast remains executable foreach of RT, RL, and RI. Never turn ineligibility into a pass or robustnessobservation.

If one or more target roles has no executable genuine I3 contrast after thisrule, publish the tokenizer receipt and stop before model access as:

STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE

If P0-T passes, publish its result and receipt by non-force fast-forward andenter:

STUDY3_P0_TOKENIZER_GATE_PASSED_AWAITING_MODEL_PILOT

Re-fetch and bind the GPU image to that exact commit and tree. If remote mainmoves at any point, stop; do not merge during an active measurement round.

8. Stage P0-M — capped model pilot

8.1 Fixed inference behavior

For each eligible cell and role:

load the exact checkpoint once, in evaluation mode and fp16;

use torch.inference_mode() or its exact equivalent;

use no sampling, stochastic layer, adapter, gradient, training, calibration,fine-tuning, prompt search, or retry based on output;

S1 reads the next-token logits only for the four registered label token IDs;

S2 reads the same next-token logit vector only for the ten registered contenttoken IDs;

S3 performs CPU-only scoring from the already captured S2 vector and addsexactly zero prefill, decode, model-load, or forward operations;

S4 uses the exact registered pre-wrapper bytes and each role's registerednative-wrapper policy, greedy decoding, do_sample=false, andmax_new_tokens=4; do not pass a sampling temperature;

retain every S4 completion and map it through the pinned deterministic parser;unparseable remains an explicit value and is never dropped or imputed;

never collect hidden states, activations, attentions, gradients, hooks, lensoutputs, probes, patches, or ablations.

8.2 Smoke allocation

The smoke uses only the K2 tuple class.

For each of RT, RL, and RI, execute:

S1: nine contrast cells × two variants = 18 prefill evaluations;

S2: one K6-INSTR cell × two variants = 2 prefill evaluations;

S3: two additional scored rows reusing S2, with zero model evaluations.

With all cells eligible, the smoke maximum is exactly:

60 sequence-level prefill evaluations;

0 incremental decode evaluations;

66 scored rows, of which 6 are S3 reuse rows;

0 S4 generation calls.

The smoke mechanical gate requires:

exact row completeness and uniqueness;

exact prompt and tokenizer identities;

finite logits for every registered candidate;

deterministic tie breaking;

exact S2/S3 agreement and zero incremental S3 model cost;

correct cumulative counters;

no OOM, device fallback, truncation, silent padding change, exceptionswallowing, or partial-result relabelling;

recorded wall time, peak allocated/reserved GPU memory, prompt lengths,runtime batch calls, and device identity.

Correctness, accuracy, response diversity, and discordance are not smokepass criteria.

If the smoke mechanical gate fails after any model operation occurred, retainand publish the partial pilot-only receipt and stop. Do not fix and rerun in thesame authority. The terminal state is:

STUDY3_P0_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE

A purely infrastructural job failure may be retried once only if the signed jobreceipt proves that zero tokenizer, model-load, prefill, decode, scoring, andgeneration operations occurred. Otherwise it is not a zero-operation retry.

8.3 Automatic bounded extension

If the smoke mechanical gate passes, the same frozen implementation maycontinue without another operator decision:

Run the full S1/S2/S3 contrast allocation for the two remaining tupleclasses, K3/affine_mod10/depth1 andK3/permutation_chain/depth1.

This adds at most 120 prefill evaluations and brings the non-generativecumulative maximum to 180.

Run the S4 K2 diagnostic for both real K6 cells:two contrast cells × two variants × three roles = 12 generation calls.

At max_new_tokens=4, S4 adds at most 12 prefill and 36 incremental decodeevaluations, or 48 total sequence-level model-evaluation equivalents.

The complete authorized P0-M maxima, before tokenizer work, are therefore:

Unit

Maximum

non-generative prefill evaluations

180

S4 generation calls

12

S4 prefill evaluations

12

S4 incremental decode evaluations

36

total sequence-level model-evaluation equivalents

228

S1 scored rows

162

S2 scored rows

18

S3 CPU-only reuse scored rows

18

S4 scored generation rows

12

total scored rows

210

distinct checkpoint identities downloaded

3

distinct tokenizer identities constructed

3

model weight loads

3

GPU jobs that perform any model operation

1

additional GPU attempt

1, only with a signed zero-operation receipt

hosted-provider inference calls

0

seeds or bank rows

0

positive-reference operations

0

Ineligible tokenizer cells reduce actual counts; they never authorizereplacement rows. Counters are cumulative across every attempt and may never bereset. Runtime batched forward calls are counted separately and must not besubstituted for any quantity above. The pilot must stop before exceeding anycap.

9. Results, interpretation, and P0 disposition

Store P0 results only under studies/study3/pilot/p0/. Preserve raw row-levelrecords sufficient to reproduce every summary, including:

immutable role/model/tokenizer/container identities;

pilot corpus row ID and prompt hash;

token IDs and token count;

eligible candidate IDs and restricted logits;

deterministic prediction, ground truth, correctness, and validity;

pair membership and the complete descriptive 2×2 outcome;

S4 raw completion, generated-token IDs/count, parser result, andunparseable status;

per-stage and cumulative operation counters;

latency, peak memory, device identity, and runtime batching metrics;

every exception, partial row, retry decision, and stop reason.

Produce descriptive summaries by role, profile, contrast, tuple class, andrendering. Report output support size, prediction diversity, correctness,pairwise joint correctness, pairwise discordance, S4 parseability, prompt-tokenlengths, latency, memory, and exact operation cost. Do not compute a p-value,confidence decision, formal gate, profile rank, winner, confirmatory effect-sizeestimate, or revised sample-size recommendation.

Use one of these terminal dispositions:

STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE

tokenizer and renderer integrity pass;

every executed row is complete and mechanically valid;

S1/S2/S3 scoring and S3 reuse reconcile;

S4 wrapper/parser/accounting executes;

resource and counter records are complete.

STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE_EMPIRICALLY_LOW_INFORMATION

every mechanical condition above passes, but the tiny corpus shows aglobally degenerate prediction pattern, no observed discordance anywhere,or another explicitly descriptive low-information pattern.

STUDY3_P0_STOPPED_ON_TOKENIZER_OR_RENDERER_DEFECT

STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE

STUDY3_P0_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE

STUDY3_P0_INCONCLUSIVE_INFRASTRUCTURE_OR_TRANSPORT_FAILURE

STUDY3_P0_BLOCKED_ON_AUTHORITY_OR_REPOSITORY_INTEGRITY

The distinction between dispositions 1 and 2 is descriptive and creates noformal eligibility difference. A small pilot cannot establish that a contrasthas or lacks a substantive effect.

10. Prohibitions

This authority forbids:

any development, confirmation, or P3-Q seed or bank;

any access to existing or future confirmation material;

any formal Gate I0–I5 pass/fail, Family A/B/C analysis, selection-map run,winner, interface preference, or confirmation release;

any use of draft-v0.5's 413/214/448 sample sizes as pilot allocations;

any change to alpha, power, floors, claims, estimands, m_max, or the formaloperation projection;

any choice or inspection of RP, any resolution of OD2 or UR-22, or anyRP/P3-Q/I4 execution;

any reuse of Study 1/2 item identities, banks, seeds, confirmation data, orempirical results as P0 inputs;

any prompt, parser, scoring, tokenizer, item, allocation, checkpoint, ordependency change after the pre-execution publication in response to anobserved P0 result;

any reroll, output-conditioned retry, cherry-picking, row replacement,exclusion of a valid but inconvenient row, or reset of a cumulative counter;

any quantization, hosted-provider inference, unpinned revision, or localworkstation model execution;

any activation extraction, hook, lens, probe, patch, intervention, ablation,or mechanistic operation;

any entry in paper/evidence_ledger.csv;

any claim that P0 answers the original research question or validatesdraft-v0.5;

any direct transition from P0 to formal development or confirmation.

11. Validation and publication after measurement

After P0-T and again after P0-M or any terminal stop:

Materialize returned Azure artifacts into the P0 result paths withoutediting their scientific values.

Validate schemas, referential integrity, prompt hashes, checkpoint andtokenizer revisions, corpus membership, row counts, pair completeness,eligibility skips, S2/S3 reuse, model-operation arithmetic, cumulative caps,and all protected bytes.

Run the P0 test module and the complete pre-existing targeted suites in aclean CPU-only ACR exact-commit clone.

Run the full suite and reconcile baseline plus net-new P0 test node IDs. Onlythe same two registered historical failures and 15 skips are allowed.

Record every failed or aborted run with its actual counter values and reason;never erase, overwrite, or relabel it as a successful run.

Update only the authorized status, decision, run-log, methods-ledger,artifact-index, and handoff paths.

Fetch origin/main; require it to equal the immediately preceding publishedP0 commit and to be an ancestor of the candidate.

Publish only by non-force fast-forward with the explicit refspec, fetchagain, and verify HEAD == origin/main, exact tree, clean worktree, exactchanged paths, protected bytes, artifact identities, and unchangedEV-0016.

If remote main moved, another path is required, a protected byte changed, acounter cannot be reconciled, an artifact is missing, or validation differsfrom the registered expectations, stop without publishing a completion claim.

12. Required final state and legal successor

At the end of this authority:

draft-v0.5 remains a candidate protocol that has not received a fourthindependent methods review;

frozen = false;

formal_execution_authorized = false;

p0_pilot_execution_authorized = false because the one-shot authority isconsumed or stopped;

no interface or positive reference is selected or preferred;

OD2, UR-22, and RP wrappers remain unresolved/null;

no formal seed, bank, development result, confirmation access, winner, RPresult, or evidence row exists;

all P0 operations are recorded only in the separate pilot counter namespace;

the evidence ledger remains byte-identical through EV-0016;

the original research question remains unanswered.

The legal successor is not another pilot and is not immediate formalexecution. It is a fresh-session operator calibration round that reads the P0feasibility record and may use only:

mechanical defect evidence;

tokenizer eligibility outcomes;

parser/serialization/runtime behavior;

prompt-length, memory, latency, and operation-cost measurements;

the descriptive fact that the tiny corpus was or was not empiricallyinformative, without treating its effect sizes as design inputs.

That calibration round must choose one of:

repair a demonstrated mechanical or surface defect in a new candidateprotocol;

retain the candidate design and add only the execution details P0 showedwere needed;

stop the current Study 3 route as infeasible.

Any surviving candidate must then receive one focused, fresh-session independentmethods review before freeze, seed draw, bank construction, formal modelexecution, or confirmation. P0 does not waive that final review.

13. Completion handoff

The final handoff must begin with the exact terminal disposition and report:

starting, pre-execution, tokenizer-stage, and final commits and trees;

non-force publication proofs and remote-head checks;

authority bytes, LF/CR status, trailing-newline status, and SHA-256;

complete changed-path census and protected-byte audit;

authority-before-drafting and frozen-input-before-operation ordering proofs;

Azure validation and GPU job IDs, immutable image digest, device, driver,CUDA, PyTorch, Transformers, tokenizer, and Python versions;

exact model and tokenizer identities and revisions;

corpus row counts and hashes;

tokenizer eligibility matrix and every excluded cell;

exact smoke and extension row counts;

every P0 counter, including tokenizer sequences, model downloads, weightloads, prefill evaluations, incremental decode evaluations, generation calls,generated tokens, restricted-logit reads, scored rows, runtime batched calls,parser calls, GPU jobs, retries, and provider calls;

mechanical-gate outcomes and descriptive feasibility summaries;

all failed, partial, retried, and aborted runs without relabelling;

full-suite arithmetic and the unchanged two historical failures;

confirmation that no formal seed/bank/selection/RP/confirmation/evidence ormechanistic operation occurred;

the exact next-action boundary from §12.

Do not begin the successor calibration round, a final independent review, anOD2 decision, or any additional model operation in this session.