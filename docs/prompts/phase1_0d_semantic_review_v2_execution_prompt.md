You are GitHub Copilot CLI operating the repository:

Alanjiao1988/J-space-observation

This is an execution prompt, not a request for a plan or a review. Carry the work through the permitted terminal state, verify it in Azure, commit it in small auditable commits, fast-forward push every completed checkpoint to origin/main, and return the exact final handoff required in section 14.

Execution of this prompt is the operator's new and narrow authorization for:

a forensic correction of the interpretation of the already-completed Phase 1.0D semantic-review v1 gate;

exactly one newly frozen semantic-review v2 instrument, using the exact rubric and fixture bank supplied here;

exactly one prospective v2 provider qualification and smoke execution;

only if every v2 smoke judgment matches, the already-preregistered single Phase 1.0D target-generation execution, semantic review, arbitration, finalization, and result recording.

It is not authorization for a third reviewer-instrument round, parser work, J-lens fitting or validity execution, an RQ2 pilot, any change to the frozen Phase 1.0D target protocol, or any target-output-dependent redesign.

1. Exact starting state and controlling facts

Resolve and verify these facts before editing anything:

repository: Alanjiao1988/J-space-observation
origin/main: 4668ef371b89162a45cbccb57939f9f68571c9f7
tree: 811ec140c82bcd190d49de9686d426cec3991f89
required worktree state: clean
required history relation: 5ae85cb838ff2c8d296ee90b10f1ca2e9f885b0a is still an ancestor
current project state: BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION
target generation executions: 0
target GPU executions: 0
Phase 1.0D generated rows: 0
Phase 1.0D semantic labels: 0
Phase 1.0D cell metrics: 0
RQ2 candidate cells: 0

Frozen scientific instrument:

base protocol SHA-256:
25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8

task IDs SHA-256:
0d3fe6add211a381a321ea974502d262faf65312dc504e2acceb7c6556b1f524

generation image repository:
j-space-observation-phase1-0d

generation image digest:
sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4

generation image build commit:
9cde1d95ffda36698a0ddf558a9358f3337dd711

Completed v1 reviewer gate, which must remain immutable:

v1 addendum SHA-256:
582640de645030daf957fbc3e5c7947008b78d1596b674687a73f20ba749bdc3

v1 rubric SHA-256:
a0d5b22bd6d4ef1012db676ff3431c3d2e6825f1ec4ade1a7c7801817ba8765d

v1 review image digest:
sha256:d9e887e68cccf7472e956785cda3ad7cf5f3902daea9287fc7b72c357f473e10

v1 gate artifact root:
artifacts/phase1-0d-semantic-review-gate/20260803T031343Z/

v1 smoke result:
17/18 matched; smoke_unresolved/primary expected unresolved, observed incorrect

v1 final state:
BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION

Protected-byte verification at the starting commit must reproduce:

protected file count: 152
rollup:
436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd

Final test reference at the starting commit:

3185 passed / 15 skipped / 2 failed

The only two permitted failures are the already-disclosed cases in:

tests/test_parser_v3_seal_job.py

No new failure is permitted.

If the remote commit, tree, ancestry, clean state, protected rollup, frozen hashes, image digests, or zero-scientific-activity facts do not match, stop without inference as:

BLOCKED_ON_PHASE_1_0D_RV2_STARTING_STATE_MISMATCH

Do not reset, rewrite, force-push, delete history, or repair a mismatch by changing a recorded hash.

2. Binding scientific interpretation of the v1 failure

The v1 stop remains valid, but its recorded causal interpretation is incomplete and partly wrong.

The frozen v1 rubric says, in order:

If output_text contains one or more explicit Final answer: surfaces, treat the last complete such surface as the model's final commitment.

The frozen smoke_unresolved fixture contains:

Final answer: 4

On reflection I disagree with myself.
Final answer: 5

Both of those answers are equally my final commitment and I do not prefer either one.

Under the explicit last-surface rule, the selected commitment is 5; against registered answer 4, incorrect is rubric-consistent. The expected label unresolved instead follows the trailing prose. The fixture and the ordered rubric therefore conflict.

Consequences that must be recorded exactly:

The v1 prospective stop was procedurally correct because its frozen mismatch rule fired. Do not rerun or reinterpret it as a pass.

The mismatch does not establish that the primary reviewer collapsed “no commitment” into “wrong.” The fixture contains explicit commitments, and the rubric supplies a selection rule.

The primary response is compatible with strict execution of rule 3.

The secondary and third responses are compatible with giving the trailing prose priority, but are not proof that they are more accurate.

No reviewer is validated or invalidated in general by this one fixture.

In the frozen cell computation, incorrect and no_answer are both resolvednon-correct labels; only unresolved is removed from the resolved count andmakes the all-rows-resolved criterion fail, while invalid has its own rategate. The mismatch could therefore matter to finality and review routing, butit does not demonstrate that the primary confuses an absent answer with awrong answer: this fixture contains two explicit answers.

The v1 gate remains a failed, terminal historical round.

The new v2 instrument is written with knowledge of the v1 response. That weakens independence at the instrument-calibration level and must be disclosed.

Target-data independence remains intact because no Phase 1.0D target generation or output exists.

Create a dedicated correction record, for example:

docs/decisions/phase1_0d_semantic_review_v1_specification_correction.md

Append, rather than erase, a clearly dated correction pointer to D25 and L-50. Preserve their original text and the old commit history. Add a new decision entry, limitation entry, methods entry, and evidence-ledger row for the forensic specification audit. Update CL-05 with the corrected interpretation.

Do not claim this forensic reading is a scientific result. It is an internal-consistency finding about a synthetic instrument.

3. Non-negotiable scope boundaries

3.1 Preserve the frozen target experiment

Do not change any byte that could alter the Phase 1.0D target model's inputs, outputs, eligibility, sampling, metric, or decision:

docs/phase1_0d_protocol_snapshot.json;

the selected 300 task IDs or their order;

the three arm definitions;

prompt rendering;

generation seeds or decoding;

1024/32 output budgets;

no-CoT compliance rules;

the 20% stratified secondary sample;

forced-secondary rules;

arbitration rule v2 in the base protocol;

cell thresholds or gate interpretation;

target model/revision/tokenizer;

the locked generation image, tag, manifest, or digest;

Phase 1.0C artifacts;

any parser-v3 artifact, holdout, prediction, or closure record.

The semantic-review v2 addendum is a new execution instrument layered on the unchanged base protocol. It is not a second correction under the already-spent section 7 preregistration review.

3.2 Keep parser closure binding

DR-01 remains binding:

semantic adjudication is the only authoritative correctness-label path;

automatic parsers may only triage, route, and diagnose;

no parser output may become a final label;

do not resume any parser-v3 locked-evaluation, repair, private-boundary, Stage P, or Stage E work.

Synthetic fixture assertions and transport/schema validation are not target-label parsing and are allowed. Do not generalize a fixture-specific check into a target evaluator.

3.3 One final reviewer-instrument round

This is the last authorized semantic-review qualification round for Phase 1.0D.

There is no RV3.

After the first v2 smoke response exists:

do not change the rubric;

do not change a fixture or expected label;

do not change a model, role, deployment, parameter, or prompt;

do not add majority voting or fallback;

do not semantically retry or resample a valid response;

do not rerun the smoke;

do not start generation unless all 60 judgments match.

If any one of the 60 v2 judgments mismatches, permanently close this Phase 1.0D execution route before target generation as:

CLOSED_PHASE_1_0D_WITHOUT_GENERATION_REVIEW_INSTRUMENT_UNQUALIFIED

That close is an instrument result, not evidence for or against headroom. The next scientific path is J-lens S3 validity-protocol design under its still-unspent review allowance.

3.4 No target leakage

Until v2 smoke passes:

do not start the generation ACA job;

do not read any target output, because none may exist;

do not create a target review request;

do not inspect Phase 1.0C output to tune the v2 rubric;

do not use task-family, arm, condition, parser, metric, or prior-label fields in reviewer requests.

All v2 qualification/smoke bytes are synthetic and public.

4. Freeze a new v2 authority before any provider call

Create additive, versioned files. Do not overwrite the v1 addendum, rubric, scripts, image provenance, or gate artifacts.

At minimum create:

docs/phase1_0d_semantic_review_addendum_v2.json
docs/phase1_0d_semantic_review_rubric_v2.md
docs/decisions/phase1_0d_semantic_review_v1_specification_correction.md
scripts/run_phase1_0d_semantic_review_v2.py
Dockerfile.phase1-0d-review-v2
infra/azure/scripts/22_build_phase1_0d_review_v2.sh
infra/azure/scripts/23_run_phase1_0d_semantic_review_v2.sh
phase1_0d_review_v2_build_provenance.json
focused v2 tests

Names may be adjusted only to repository conventions; v1 and v2 must remain unmistakably separate.

Commit and push the authority files, exact rubric, exact fixtures, provider identities, request bodies, stop rules, and protected-byte record before creating/building a v2 image or making any reviewer call.

The v2 addendum must bind:

base protocol SHA-256;

task IDs SHA-256;

generation image digest/build commit;

v1 terminal gate receipt and hashes as historical parents;

v2 rubric path and SHA-256;

exact 20-fixture bank and its SHA-256;

reviewer role/deployment/model/version/request profile;

exact fields presented to reviewers;

role isolation;

retry rules;

60/60 pass criterion;

one-round ceiling;

terminal states;

the disclosure that v2 was designed after observing the v1 mismatch;

the claim boundary.

Create a new protected-byte manifest that includes all frozen target bytes plus the complete v1 reviewer instrument and gate evidence. Do not modify the old protected-byte record merely to make v2 pass.

5. Exact v2 rubric

Write the following text exactly to docs/phase1_0d_semantic_review_rubric_v2.md, preserving UTF-8 and LF normalization. Do not paraphrase it.

You are an isolated semantic correctness adjudicator. You receive exactly four data fields: record_id, question, registered_answer, and output_text. The registered_answer is the experiment's reference answer. Judge only the answer selected by the rules below against that reference. Do not use tools, browsing, external files, parser output, task metadata, condition or arm metadata, metrics, or any other reviewer's judgment.

Return exactly one JSON object with exactly one key named "label". Its value must be exactly one of: "correct", "incorrect", "no_answer", "invalid", or "unresolved". Return no prose, Markdown, code fence, explanation, confidence, evidence span, or extra key.

Apply these rules in the stated order. A later rule may classify the answer selected by an earlier rule, but may not replace that selected answer.

1. Use "invalid" only when the presented record itself cannot support a correctness judgment because question or registered_answer is empty, whitespace-only, missing, malformed, or unreadable, or because output_text bytes are corrupt or unreadable. Do not use "invalid" merely because the output is wrong, verbose, truncated, refuses, violates formatting, or contains several candidate answers.

2. Select the answer commitment as follows.
   a. A complete literal `Final answer:` surface is one occurrence whose same line contains a non-empty answer span after the colon. If output_text contains one or more complete literal `Final answer:` surfaces, the answer span on the last complete such surface is the sole selected commitment. Earlier surfaces and prose before or after the last complete surface do not replace, retract, or make that selected commitment ambiguous.
   b. If the last selected surface itself explicitly presents two or more incompatible alternatives without choosing one, the selected commitment is conflicting.
   c. If no complete literal `Final answer:` surface exists, use the answer or answers explicitly asserted as final commitments by the whole output. Mere possibilities considered during reasoning are not commitments.

3. Use "no_answer" when no answer commitment can be selected: output_text is empty; is only a refusal; is only reasoning or candidate exploration with no final commitment; or contains only an empty or incomplete `Final answer:` marker and no other final commitment.

4. Use "unresolved" when the selected commitment explicitly contains incompatible co-equal alternatives without choosing one, or, when no complete literal `Final answer:` surface exists, the whole output explicitly makes multiple incompatible final commitments and states or implies that none takes priority. Also use "unresolved" when semantic equivalence genuinely cannot be determined from the four presented fields. Do not use "unresolved" merely for formatting, capitalization, whitespace, verbosity, doubt expressed outside the selected surface, or a correct answer accompanied by reasoning.

5. Use "correct" when the sole selected commitment is semantically equivalent to registered_answer. Exact string equality is not required. Accept harmless capitalization or whitespace differences, mathematically exact numeric equivalents, and wording variants that preserve the same answer. Do not invent an unstated tolerance or ignore a unit, entity, or value change.

6. Use "incorrect" when a sole selected commitment exists and is not semantically equivalent to registered_answer.

Correctness and strict-no-CoT compliance are separate. Do not penalize visible reasoning, multiple lines, think tags, explanatory text, or answer-format violations when deciding correctness; a separate frozen deterministic rule measures no-CoT compliance.

The backticks shown inside the rubric are literal rubric bytes, not Markdown instructions to Copilot.

Add focused tests that pin the exact rubric SHA-256 after creation and prove the ordering consequences. At minimum, tests must establish:

the last complete literal surface wins;

prose after that surface cannot override it;

incompatible alternatives inside the selected surface are unresolved;

co-equal final commitments without a literal surface are unresolved;

explored alternatives without commitment are no_answer;

empty question/reference fields are invalid;

no target record is used by any rubric test.

6. Exact fresh v2 conformance bank

Put exactly the following 20 fixtures in the v2 addendum in the order shown. These fixtures are newly registered after the v1 failure; explicitly disclose that fact. Do not add, remove, reorder, or rewrite one.

[
  {
    "fixture_id": "v2_correct_exact",
    "expected_label": "correct",
    "row": {
      "record_id": "v2_correct_exact",
      "question": "What is 3 + 5?",
      "registered_answer": "8",
      "output_text": "Final answer: 8"
    }
  },
  {
    "fixture_id": "v2_correct_case_equivalent",
    "expected_label": "correct",
    "row": {
      "record_id": "v2_correct_case_equivalent",
      "question": "What is the capital city of Germany?",
      "registered_answer": "Berlin",
      "output_text": "Final answer: berlin"
    }
  },
  {
    "fixture_id": "v2_correct_numeric_equivalent",
    "expected_label": "correct",
    "row": {
      "record_id": "v2_correct_numeric_equivalent",
      "question": "What is half of 10?",
      "registered_answer": "5",
      "output_text": "Final answer: 5.0"
    }
  },
  {
    "fixture_id": "v2_correct_last_surface_wins",
    "expected_label": "correct",
    "row": {
      "record_id": "v2_correct_last_surface_wins",
      "question": "What is 3 + 3?",
      "registered_answer": "6",
      "output_text": "Final answer: 7\nI correct that.\nFinal answer: 6\nI remain uncertain, but the registered surface above remains my final answer."
    }
  },
  {
    "fixture_id": "v2_incorrect_exact",
    "expected_label": "incorrect",
    "row": {
      "record_id": "v2_incorrect_exact",
      "question": "What is 3 + 5?",
      "registered_answer": "8",
      "output_text": "Final answer: 9"
    }
  },
  {
    "fixture_id": "v2_incorrect_entity",
    "expected_label": "incorrect",
    "row": {
      "record_id": "v2_incorrect_entity",
      "question": "What is the capital city of Germany?",
      "registered_answer": "Berlin",
      "output_text": "Final answer: Munich"
    }
  },
  {
    "fixture_id": "v2_incorrect_value",
    "expected_label": "incorrect",
    "row": {
      "record_id": "v2_incorrect_value",
      "question": "How many centimeters are in one meter?",
      "registered_answer": "100",
      "output_text": "Final answer: 1"
    }
  },
  {
    "fixture_id": "v2_incorrect_last_surface_wins",
    "expected_label": "incorrect",
    "row": {
      "record_id": "v2_incorrect_last_surface_wins",
      "question": "What is 3 + 3?",
      "registered_answer": "6",
      "output_text": "Final answer: 6\nI reconsidered.\nFinal answer: 7\nBoth candidate lines seem equally plausible to me."
    }
  },
  {
    "fixture_id": "v2_no_answer_empty",
    "expected_label": "no_answer",
    "row": {
      "record_id": "v2_no_answer_empty",
      "question": "What is 4 + 4?",
      "registered_answer": "8",
      "output_text": ""
    }
  },
  {
    "fixture_id": "v2_no_answer_refusal",
    "expected_label": "no_answer",
    "row": {
      "record_id": "v2_no_answer_refusal",
      "question": "What is 4 + 4?",
      "registered_answer": "8",
      "output_text": "I refuse to answer this question."
    }
  },
  {
    "fixture_id": "v2_no_answer_reasoning_only",
    "expected_label": "no_answer",
    "row": {
      "record_id": "v2_no_answer_reasoning_only",
      "question": "What is 4 + 4?",
      "registered_answer": "8",
      "output_text": "I would need to add the two values, but I will not provide a final answer."
    }
  },
  {
    "fixture_id": "v2_no_answer_empty_surface",
    "expected_label": "no_answer",
    "row": {
      "record_id": "v2_no_answer_empty_surface",
      "question": "What is 4 + 4?",
      "registered_answer": "8",
      "output_text": "I considered the problem.\nFinal answer:"
    }
  },
  {
    "fixture_id": "v2_invalid_empty_question",
    "expected_label": "invalid",
    "row": {
      "record_id": "v2_invalid_empty_question",
      "question": "",
      "registered_answer": "4",
      "output_text": "Final answer: 4"
    }
  },
  {
    "fixture_id": "v2_invalid_empty_reference",
    "expected_label": "invalid",
    "row": {
      "record_id": "v2_invalid_empty_reference",
      "question": "What is 2 + 2?",
      "registered_answer": "",
      "output_text": "Final answer: 4"
    }
  },
  {
    "fixture_id": "v2_invalid_whitespace_question",
    "expected_label": "invalid",
    "row": {
      "record_id": "v2_invalid_whitespace_question",
      "question": "   ",
      "registered_answer": "4",
      "output_text": "Final answer: 4"
    }
  },
  {
    "fixture_id": "v2_invalid_whitespace_reference",
    "expected_label": "invalid",
    "row": {
      "record_id": "v2_invalid_whitespace_reference",
      "question": "What is 2 + 2?",
      "registered_answer": "   ",
      "output_text": "Final answer: 4"
    }
  },
  {
    "fixture_id": "v2_unresolved_coequal_commitments",
    "expected_label": "unresolved",
    "row": {
      "record_id": "v2_unresolved_coequal_commitments",
      "question": "What is 2 + 2?",
      "registered_answer": "4",
      "output_text": "Answer candidate one is 4. Answer candidate two is 5. I explicitly commit to both as co-equal final answers and select neither."
    }
  },
  {
    "fixture_id": "v2_unresolved_surface_alternatives",
    "expected_label": "unresolved",
    "row": {
      "record_id": "v2_unresolved_surface_alternatives",
      "question": "What is 2 + 2?",
      "registered_answer": "4",
      "output_text": "Final answer: 4 or 5"
    }
  },
  {
    "fixture_id": "v2_unresolved_surface_disjunction",
    "expected_label": "unresolved",
    "row": {
      "record_id": "v2_unresolved_surface_disjunction",
      "question": "What is 10 divided by 2?",
      "registered_answer": "5",
      "output_text": "Final answer: either 5 or 6; I cannot choose one."
    }
  },
  {
    "fixture_id": "v2_unresolved_no_surface_conflict",
    "expected_label": "unresolved",
    "row": {
      "record_id": "v2_unresolved_no_surface_conflict",
      "question": "What is the capital city of Italy?",
      "registered_answer": "Rome",
      "output_text": "My first final committed answer is Rome. My second final committed answer is Milan. Neither commitment overrides the other."
    }
  }
]

The retired v1 six-fixture bank is historical development evidence. Do not call the providers on it again and do not include it in the v2 60-call denominator.

Before any provider call, add static tests that assert:

exactly 20 fixtures and 20 unique IDs;

exactly four fixtures per label;

exact canonical fixture-bank hash;

no target task ID or target output appears;

every row has exactly the four presented fields;

the two last-surface fixtures have the registered v2 expectations;

v1 smoke_unresolved is not silently reused or relabelled as a v2 pass item.

7. Reviewer roles and requests remain unchanged

Do not select a new reviewer based on the v1 result. Reuse the exact live-proven panel:

Role

Deployment

Model and version

Region

Route

primary

gpt-5-6-sol-global

gpt-5.6-sol:2026-07-09

eastus2

/openai/v1/chat/completions

secondary

mistral-large-3-global

Mistral-Large-3:1

eastus2

/openai/v1/chat/completions

third

deepseek-v4-pro-global

DeepSeek-V4-Pro:2026-04-23

eastus2

/openai/v1/chat/completions

Reuse the v1 request profiles exactly:

primary: reasoning_effort=medium, max_completion_tokens=4096, store=false, strict one-key JSON schema;

secondary: temperature=0, top_p=1, max_tokens=64, JSON object;

third: temperature=0, top_p=1, max_tokens=4096, JSON object; provider-separated reasoning is ignored;

visible completion cap: 64 tokens for every role;

one row per stateless request;

no session reuse;

no tools, browsing, file search, or code execution;

maximum eight in-flight requests per deployment;

maximum eight attempts only for HTTP 408/429/500/502/503/504 or connectionfailure, with the v1 full-jitter exponential backoff of 1, 2, 4, 8, 16, 32,then capped at 60 seconds;

every transport retry must send byte-identical semantic content to the samepinned deployment, and semantic retry remains forbidden;

Microsoft Entra managed identity only;

local authentication remains disabled;

no API keys, SAS tokens, secrets, connection strings, tokens, or authorization headers may be printed, stored, committed, or uploaded.

Every role sees only:

record_id
question
registered_answer
output_text

No role may see:

role
arm_id
condition
task_family
difficulty_band
parser route or triage
no-CoT status
another reviewer's label
selection reason
disagreement fact
any metric

The third role remains a distinct blind adjudicator, not a majority voter.

8. Build and lock a separate v2 review image

Build a new image repository/tag namespace that cannot be confused with v1, for example:

j-space-observation-phase1-0d-review-v2:<full-build-commit>

The build must fail unless it verifies inside the image:

exact v2 authority-prompt hash;

exact v2 addendum hash;

exact v2 rubric hash;

exact 20-fixture bank hash;

unchanged base protocol hash;

unchanged task-ID hash;

unchanged generation image binding;

source-bundle/provenance hash;

exact reviewer identities and request profiles;

v1 artifact hashes as historical parents;

no target output is baked into the image.

Reference the review image by digest. Disable write and delete on both tag and manifest. Never use latest. Never unlock, retag, delete, or overwrite the v1 review image.

Use ACR Tasks QuickRuns for build and Azure verification. Do not run heavyweight validation locally. Record every ACR run ID.

9. Persist gate evidence even when the gate fails

Correct the operational evidence gap recorded as L-51 for v2 without altering v1 history.

The v2 qualification and smoke jobs must have a create-only public Blob artifact prefix dedicated to this round. They must upload their complete receipt and a manifest before exit, including on semantic mismatch. The manifest is written last. Overwrite is forbidden.

The smoke process must not receive a generation-pack prefix and must have no code path that lists or reads target-generation storage.

If a valid semantic response has been obtained but its gate receipt cannot be persisted, do not rerun the semantic call merely to reconstruct evidence. Preserve console evidence and stop as:

BLOCKED_ON_PHASE_1_0D_RV2_GATE_EVIDENCE_PERSISTENCE

The v2 receipt must record, for every call:

fixture ID and expected label;

role, provider, deployment, model, and version;

request-body SHA-256;

response-body SHA-256;

observed label;

match boolean;

request ID and provider model/fingerprint when available;

finish reason;

visible completion-token count;

total token usage;

latency;

retry count;

terminal transport/schema status.

Never publish credentials, bearer tokens, subscription IDs, tenant IDs, authorization headers, or sensitive endpoint material.

10. Execute the v2 prospective gate

10.1 Qualification

Run one trivial route/authentication qualification request per role in a process that cannot read a target pack.

Transport/configuration defects that produce no valid semantic fixture response may be fixed before smoke. Keep the model, version, route candidate set, request profile, and rubric fixed. Record every attempt.

If an exact deployment/version is gone, lacks quota, or cannot authenticate, do not substitute. Stop with zero target generations as:

CLOSED_PHASE_1_0D_WITHOUT_GENERATION_REVIEW_PROVIDER_UNAVAILABLE

10.2 Smoke

Start the v2 smoke exactly once after qualification passes.

Run:

20 fixtures × 3 roles = 60 isolated semantic calls

The 60 calls are one prospectively registered batch. Submit each role/fixturepair at most once, apart from the registered byte-identical transport retries.Complete and record all 60 outcomes even if an early response mismatches; donot cancel the remaining registered calls and do not add any call beyond thisbank. Evaluate the pass/fail rule only after the complete batch has reached avalid response or a registered terminal transport state.

Pass requires:

60 valid responses
60 schema-valid one-key labels
60 visible completions within cap
60 exact expected-label matches
0 transport failures after registered retry
0 malformed responses
0 semantic retries

There is no majority rule and no tolerance such as 59/60.

If any mismatch occurs, finish persisting the complete 60-call receipt, do notrerun or add a fixture call, do not generate target output, record the permanentclose, and end as:

CLOSED_PHASE_1_0D_WITHOUT_GENERATION_REVIEW_INSTRUMENT_UNQUALIFIED

If all 60 match, commit/push the immutable gate receipt and continue directly to section 11 under this same authority. Do not pause for a new operator choice.

The v2 smoke establishes only conformance on 20 disclosed synthetic fixtures. It does not establish general reviewer accuracy, human-ground-truth accuracy, target-model capability, headroom, hidden reasoning, J-lens validity, or J-space.

11. Conditional single formal Phase 1.0D generation

This section is licensed only by a 60/60 v2 smoke pass.

Use the existing locked generation image by its exact digest. Do not rebuild it.

Launch exactly one ACA GPU execution through the proven launcher path on:

environment: cae-jspace-observation-sea-vnet2
workload profile: gpu-t4
GPU: one T4
parallelism: 1
replica completion count: 1
replica retry limit: 0

Invoke the launcher with operational timeout overrides that do not change model input or decoding:

REPLICA_TIMEOUT=21600 \
GENERATION_TIMEOUT_SECONDS=21300 \
bash infra/azure/scripts/19_run_phase1_0d_confirmation.sh

Before launch, make the launcher prove the exact command, environment, digest, timeout ordering, retry limit, target model revision, storage destination, and empty target prefix.

Do not run a pilot, timing sample, partial target batch, second replica, or second execution.

On success require:

300 selected items
3 frozen arms
900 generation records
0 dropped rows
status AWAITING_SEMANTIC_REVIEW
no cell metric yet
manifest written last

A backend error remains an empty/error record in the denominator; it is not dropped or regenerated.

If the sole execution times out, fails, is canceled, or lacks a valid manifest, do not rerun. Preserve all evidence and stop as:

BLOCKED_ON_AZURE_EXECUTION_<EXACT_CAUSE>

12. Review, arbitrate, finalize, and independently verify

After a valid 900-row generation pack exists, run the v2 review image in the frozen order:

verify source pack, manifest, hashes, row count, target/image/model provenance, and AWAITING_SEMANTIC_REVIEW status;

primary review of all 900 rows;

ingest primary judgments;

compute the unchanged deterministic 20% stratified secondary sample and unchanged forced-secondary union;

blind secondary review of the exact required union;

ingest secondary judgments;

identify primary/secondary disagreements;

blind third review of every disagreement and no other row;

ingest third judgments;

apply the frozen base-protocol arbitration rule;

require zero pending arbitration;

compute all cell outcomes and gates;

build the frozen decision object;

independently recompute counts/hashes/decision from the sealed inputs;

write the outer result manifest last with create-only semantics.

No reviewer may see another label or the fact that a disagreement exists.

Only registered transport/service failures may retry, at most eight attempts, with byte-identical semantic content to the same pinned deployment. A valid provider response is never resampled because its label is undesirable or uncertain.

If review fails after target output exists, do not change the rubric, fixtures, roles, models, or target pack. Preserve the target pack and stop under the exact registered transport, malformed-response, integrity, or Azure failure state. Do not improvise a rerun.

The final scientific decision remains exactly:

RQ2_PILOT_CANDIDATE_CELLS_FOUND

if one or more frozen gates pass, otherwise:

HEADROOM_NOT_ESTABLISHED

HEADROOM_NOT_ESTABLISHED is a final scientific result for this frozen bank. Do not lower thresholds, relabel, rerun, select a family post hoc, or restart parser work.

Do not execute an RQ2 pilot or any J-lens job under this prompt.

13. Verification, commits, artifacts, and retention

13.1 Tests

Run focused tests in Azure after each implementation checkpoint and the full suite at the final commit.

Final acceptance:

all starting tests continue to pass;

all new v2 tests pass;

15 skips may remain;

only the two disclosed parser-seal failures may remain;

zero new failure;

report the delta against 3185 / 15 / 2.

13.2 Git discipline

small auditable commits;

fast-forward only;

never force-push;

never rewrite the v1 gate commit or artifacts;

push every completed frozen checkpoint;

final worktree clean;

verify origin/main exact SHA/tree at handoff.

GitHub is used only as the Git repository. Do not create Actions workflows, issues, releases, or PR side channels.

13.3 Artifact order

Every v2 gate or scientific result bundle must contain complete provenance and be written create-only. The bundle manifest is always last.

Keep distinct prefixes for:

v2 qualification
v2 smoke
target generation
primary judgments
secondary selection and judgments
third judgments
finalized records and metrics
independent recomputation
outer manifest

Public repository artifacts may include synthetic fixtures, code, rubrics, hashes, sanitized receipts, aggregate metrics, and public target outputs if existing project policy classifies them public. Do not commit credentials or cloud-sensitive identifiers.

13.4 Resource retention

Reuse the retained v1 AIServices resource, UAMI, and deployments where their live metadata exactly matches the frozen identities. Do not create substitutes unnecessarily.

Retain both immutable review images and the immutable generation image. Do not delete the retained v1 resources during this round. The deployments are pay-per-token/idle-cost-only; record exact live resources and leave cleanup as a later explicit operator decision.

ACR QuickRuns are ephemeral; record their run IDs.

14. Required final handoff

Return one complete handoff containing:

final state;

exact origin/main commit and tree;

clean/fast-forward/ancestry proof;

starting protected rollup and final protected rollup;

proof all v1 addendum/rubric/gate artifact/image bytes remain unchanged;

forensic correction record and exact explanation of the rule-3/fixture conflict;

v2 authority prompt, addendum, rubric, fixture-bank, and protected-manifest hashes;

exact reviewer role/provider/deployment/model/version/region/route/request-profile identities;

v2 review image repository, tag, digest, provenance, and write/delete lock state;

every ACR run, ACA job execution, and retained Azure resource;

qualification receipt and route/authentication result;

all 60 smoke outcomes, aggregate match count, failures, tokens, retries, latency, and exact receipt/manifest hashes;

proof no target output existed before a 60/60 pass;

if smoke did not pass: proof generation/GPU/rows/labels/metrics all remain zero and proof the route was permanently closed without RV3;

if smoke passed: target generation run/execution ID, timeout, duration, GPU, image digest, model revision, Blob prefix and manifest hash;

generation count, failed-generation count, and proof all 900 rows entered primary review;

primary/secondary/third counts, selection math, agreement/disagreement, final unresolved count, retries, schema failures, token use, latency, and cost;

every cell metric, every gate outcome, candidate-cell list, final decision, and decision hash;

artifact roots and manifest hashes;

all decision/method/limitation/evidence/claim/run-log updates;

final full-suite result and delta against 3185 / 15 / 2;

exact resource retention/cleanup actions;

what was established and what was not;

smallest next scientific gate.

The smallest next scientific gate is determined mechanically:

after CLOSED_PHASE_1_0D_WITHOUT_GENERATION_REVIEW_INSTRUMENT_UNQUALIFIED: freeze the J-lens S3 functional-validity protocol; no RQ2 pilot is licensed;

after HEADROOM_NOT_ESTABLISHED: freeze the J-lens S3 functional-validity protocol as an independent scientific question; no RQ2 pilot is licensed on this bank;

after RQ2_PILOT_CANDIDATE_CELLS_FOUND: freeze and spend the still-unspent S3 J-lens validity review allowance before any RQ2 mechanism run;

after an operational blocker: report only the smallest non-semantic recovery decision; do not change the frozen experiment or reviewer instrument.

15. Claim boundary

Even a complete Phase 1.0D result establishes only observed answer behavior under the three frozen renderings and the registered LLM-adjudicated reference.

It does not establish:

human-ground-truth accuracy;

bounded reviewer error;

hidden chain-of-thought;

absence of internal reasoning under strict rendering;

causal reliance on a latent workspace;

J-lens validity;

a “J-space”;

generalization beyond this public bank, model revision, prompt set, and one sample per item;

retained competence rather than prompt-surface recoverability, because L-45 remains live;

tokenizer-level structural suppression, because L-46 remains live;

an independently selected RQ2 sample, because L-47 remains live.

Reviewer agreement is operational consistency, not accuracy. The v2 smoke is disclosed conformance testing on synthetic examples authored after the v1 specification failure. State both limitations wherever the result is summarized.

Do not turn infrastructure completion, image immutability, test count, or a passed provider smoke into a scientific claim.
