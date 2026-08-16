You are the sole independent focused methods reviewer for Study 3R in:

`https://github.com/Alanjiao1988/J-space-observation`

You must be independent of the party that authored Study 3R protocol v1. You must not have drafted or materially edited its authority, protocol, schemas, registry, state machine, task generators, statistical calculators, tokenizer probe, manifest generator or candidate tests.

This is a review-only session. You may inspect, independently recalculate, reconstruct tokenizer surfaces and run adversarial tests. You may not repair the candidate, draft an amendment, freeze it or execute any model.

## 0. Binding reviewed object

Expected starting `origin/main`:

* commit: `da1ea31b51b784cb1ab3529f9de2f6ee27c853dd`
* tree: `c1de862ba3782b4930191a51df8790bb4279344c`
* state:
  `STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`

Binding order:

1. This focused-review authority.
2. `studies/study3r/study3r_charter.json`
3. `studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md`
4. The complete Study 3R protocol-v1 candidate at `da1ea31…`
5. The Study 3R authoring disclosure.
6. The v0.7 independent review only as a historical defect checklist.

Verify before writing anything:

* `HEAD == fetched origin/main == da1ea31…`;
* clean worktree;
* exact starting tree;
* five strictly linear commits from `cd9c0af…`;
* authority commit `5a80c67…` is first and contains only the authority;
* zero merge, rebase or history rewrite;
* all disclosed protected paths retain their registered blobs;
* evidence ledger ends at `EV-0016`;
* all execution-authorized fields are false.

If any condition differs, stop with:

`STUDY3R_PROTOCOL_V1_REVIEW_BLOCKED_ON_STARTING_STATE_INTEGRITY`

## 1. Review authority first

Save this prompt byte-for-byte as:

`studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md`

Commit it alone as the first commit after `da1ea31…`. Record byte length, SHA-256, Git blob, parent and tree, and publish that authority-only commit before creating a finding, calculation, mutation or report.

All later review artifacts must be additions inside `studies/study3r/`. Do not modify:

* any candidate Study 3R artifact;
* `tests/test_study3r_protocol_v1.py`;
* `tests/test_study3r_operator_governance.py`;
* `.gitattributes`;
* any Study 3, Study 2, Study 1 or paper artifact.

Place any review-specific pytest module under `studies/study3r/reviews/`, not under top-level `tests/`.

## 2. Review standard and severity

Evaluate whether the candidate is sufficiently complete, identifiable, statistically valid and executable to be frozen by a later operator authority.

Classify findings as:

* **BLOCKING**: can change an estimand, task population, rendered/model input, statistical unit, atomic-cell census, multiplicity, sample size, pass/fail decision, candidate-selection result, state transition, checkpoint identity, execution reproducibility or permitted scientific claim.
* **MAJOR**: materially weakens reproducibility or interpretation but is demonstrated not to change a registered decision.
* **MINOR**: purely editorial or provenance presentation, incapable of changing any decision or claim.

Do not downgrade a confirmed decision-bearing defect to a limitation.

Verdict rules:

* one or more BLOCKING findings →
  `STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION`;
* zero BLOCKING but an unresolved MAJOR that prevents honest freeze →
  `STUDY3R_PROTOCOL_V1_TERMINAL_OPERATOR_DECISION_REQUIRED`;
* zero BLOCKING and no freeze-preventing MAJOR →
  `STUDY3R_PROTOCOL_V1_FOCUSED_REVIEW_ACCEPTED_AWAITING_FREEZE_AUTHORITY`.

Acceptance does not authorize execution.

## 3. Independence and prohibited actions

Permitted:

* repository inspection;
* tokenizer-only metadata/file retrieval at the four registered immutable revisions;
* tokenizer construction with `trust_remote_code=false`;
* synthetic non-scientific fixture rendering;
* exact statistical recalculation;
* temporary detached-worktree mutations;
* static analysis and local tests.

Prohibited:

* model-weight download;
* model construction or load;
* adapter/activation load;
* prefill, forward, logit read, scoring or generation;
* GPU/cloud/Azure jobs;
* scientific bank realization;
* execution-seed draw;
* RP-B selection;
* evidence-ledger changes;
* candidate repair or amendment.

All permitted tokenizer operations must be separately counted.

## 4. Repository and governance audit

Independently verify:

* exact authored path set and ancestry;
* authority-alone ordering;
* immutable-revision acquisition records;
* no weight-file acquisition;
* authoring disclosure consistency;
* protected-byte claims;
* current pointer uniqueness;
* no legacy runtime overlay or fallback;
* bundle reproduction;
* schema validation;
* manifest inclusion/exclusion claims.

Audit the exact diff to `tests/test_study3r_operator_governance.py`.

Determine whether extending its two scope assertions:

* was permitted by the authoring authority;
* merely advanced the previously declared Study 3R namespace;
* or post-hoc widened a policing test so that otherwise unauthorized paths became acceptable.

Do not accept “no assertion was weakened” without comparing the before/after predicates and their admitted path sets.

## 5. Independent tokenizer and rendering reconstruction

Using only the four registered immutable revisions, independently retrieve the registered allow-listed tokenizer/config files and verify all file hashes.

Reconstruct, without importing `study3r_tokenizer_probe.py`:

* A/B/C/D token IDs;
* raw-wrapper bytes and token IDs;
* role-envelope bytes and token IDs;
* chat-template hash;
* BOS/EOS behavior;
* the generated-CoT wrapper;
* common-prefix lengths;
* candidate discriminant token IDs;
* all registered functional-equivalence tuples.

Test more than the six committed fixtures. Generate a bounded adversarial grid of synthetic non-scientific renderings containing:

* one-, two- and three-digit operands/results;
* each operation;
* depth 1, 2 and 3;
* each option-label position;
* spacing/newline boundary cases.

Determine whether `d0_discriminant_position = 57/63` is:

* merely a fixture-specific recorded value while execution recomputes the position for every rendered item; or
* an absolute position incorrectly applied to variable-length prompts.

If the runtime protocol or future runner cannot deterministically derive and verify the discriminant position per item, classify BLOCKING.

Verify whether all four checkpoints remain in one functional-equivalence stratum over the full adversarial surface set, not only one placeholder fixture.

## 6. E0 and wrapper audit

Verify the complete E0 contract:

* `do_sample=false`;
* temperature semantics;
* beam count;
* EOS/length-limit behavior;
* exactly one permitted trailing EOS removal;
* empty, malformed, extra-token and rationale outputs count incorrect;
* `max_new_tokens=2` cannot silently accept a truncated non-EOS output under a different interpretation;
* full-sequence exact match is consistently implemented.

Inspect `W2_ROLE_CANONICAL` byte-for-byte.

The native chat template opens `<think>\n`, while the candidate injects the frozen closure:

`</think>\n\n`

Determine whether:

* this is accurately represented as part of the differing envelope;
* the wrapper should instead be named “role-canonical envelope with forced reasoning closure”;
* any claim incorrectly treats it as the checkpoint’s unmodified canonical route;
* the manually supplied closure creates an additional intervention not covered by the registered claim language;
* the raw/canonical arms differ in any field beyond the declared envelope.

Because the gate is joint adequacy rather than an effect estimand, do not demand template-effect inference. But any misleading “canonical” claim or unidentified intervention that changes the construct is decision-bearing.

## 7. Generated-CoT ceiling audit

Independently inspect whether the CoT route freezes all execution-defining fields:

* `do_sample`;
* temperature;
* top-p;
* top-k;
* seed semantics;
* `k=1`;
* aggregation;
* batch size;
* padding side;
* EOS/stop tokens;
* parser;
* unparseable handling;
* context and maximum-generation bounds;
* dtype/quantization identity where these affect execution;
* total token and compute/resource upper bounds.

Do not infer these values from a library default unless the protocol explicitly pins the library version and the default as part of the contract.

Verify that `P1_FINAL_ANSWER_LAST_LINE` and `^Final answer: ([ABCD])$` define one unambiguous parser over multiline output.

Check whether requiring every one of RT, 7B, 14B and 32B to pass the ceiling before proceeding is scientifically consistent with a ladder intended to scan past failed positive-reference candidates.

A failed RP-B candidate should not automatically prevent testing a later candidate unless the protocol gives a defensible, charter-consistent reason.

## 8. Candidate-scoped versus global gate logic

Reconstruct every state-machine path without relying on the production builder.

Pay special attention to:

* CoT ceiling;
* recovery/binding/primitive controls;
* negative control;
* wrapper joint adequacy;
* RP-B development/confirmation.

The current state machine appears to transition to a global terminal state if any checkpoint cell fails before ladder scanning.

Determine whether this means:

* failure of RP_B1 blocks evaluation of RP_B2 and RP_B3;
* failure of RP_B2 blocks RP_B3;
* the first-confirmed-pass ladder is therefore conditional on every ladder member already passing all prequalification gates;
* candidate-specific failures are incorrectly promoted to study-wide failure.

Compare this behavior against:

* fixed-order scanning past failures;
* first-confirmed-pass selection;
* no fallback outside the registered ladder;
* per-checkpoint generated-CoT precondition;
* the bounded interpretation of no qualified reference.

If candidate-specific ineligibility should continue to the next registered candidate but the state machine stops globally, classify BLOCKING.

Separately determine the correct scope of an RT failure versus an RP candidate failure.

## 9. D2/D3 construct and pooling audit

The census treats each mixed `D2_D3_*_BANK` as one atomic cell rather than separate depth-2 and depth-3 cells.

Independently establish:

* exact D2/D3 allocation rule in every mixed bank;
* whether counts per depth are fixed or seed-dependent;
* whether the protocol claims competence at both depths;
* the weakest D3 performance compatible with passing the pooled gate if D2 performance is high;
* whether depth-2 success can mask depth-3 failure;
* whether operation-family performance can similarly be pooled and masked.

Provide concrete integer counterexamples at the registered `n` and pass boundary.

For example, determine whether a model can pass `k ≥ 51/74` while performing near chance on every D3 item because D2 results supply most successes.

If the claim includes depth-3 competence but depth is not a gate-bearing factor, classify BLOCKING and independently recompute the cell census and statistical implications under the minimal valid stratification.

Do not silently redesign the protocol; report the counterfactual census only to quantify the defect.

## 10. Task-generator and sampling audit

Independently review `study3r_task_generators_v1.py` for:

* arithmetic correctness;
* subtraction constraints;
* result-domain enforcement;
* four distinct options;
* correct-label construction;
* label-position balance;
* operation balance;
* D2/D3 balance;
* duplicate/collision handling;
* item-disjointness;
* negative-control independence;
* deterministic PRNG behavior across supported Python versions;
* rejection-loop termination;
* exact relation between task family, bank and statistical unit.

Verify the claim that no strategy can exceed chance on NEG under the actual scoring construction.

Check whether the negative-control “registered correct label” is scientifically coherent when no option carries the derivable value, and whether uniform independence is mechanically enforced.

Do not realize a scientific bank or draw the execution seed. Use temporary explicitly non-scientific test seeds only if the authority and review artifacts label them as adversarial generator tests that can never enter execution.

## 11. Independent statistical recalculation

Write a stdlib-only recalculation that imports none of:

* `study3r_protocol_build.py`;
* `study3r_design_statistics.py`;
* `study3r_independent_recalculation.py`;
* task-bank production calculators.

Use exact integer/rational arithmetic.

Recalculate:

* every atomic cell;
* `m_max`;
* `alpha_global`;
* `alpha_per_cell`;
* every exact null tail;
* every integer pass boundary;
* every exact power;
* minimality of every `n`;
* total scheduled evaluations;
* first-confirmed-pass multiplicity over `L=3`;
* negative-control direction and boundary.

Then recalculate the minimal valid census under any confirmed missing factor, especially separate D2 and D3 cells. Clearly label this as a counterfactual diagnostic, not a candidate repair.

Check whether:

* development and confirmation are counted as separate inferential cells;
* both wrapper arms enter every applicable family;
* paired reuse of items changes the claimed unit or dependence assumptions;
* a single Bonferroni family over 58 cells is complete;
* any gate is duplicated, omitted or unnecessarily global;
* sample-size alternatives correspond to the scientific competence claim rather than mere statistical convenience.

Report exact agreements and mismatches, not only decimal summaries.

## 12. Schema, build and mutation audit

Validate all JSON artifacts against their committed schemas.

Confirm that every decision-bearing field is constrained by more than `{"type":"object"}` and that cross-field semantics are tested independently of the generator.

Perform two mutation classes in a temporary detached worktree:

1. artifact-only mutations;
2. coordinated generator → rebuild → semantic-validation mutations.

Include the candidate’s registered 24 mutations and additional adversarial mutations covering:

* D2/D3 allocation;
* global versus candidate-scoped failure transition;
* CoT `do_sample`/temperature/top-p;
* D0 per-item position rule;
* forced `</think>` closure;
* parser anchoring;
* checkpoint dtype/quantization;
* manifest path omission;
* current-pointer omission of a normative artifact;
* governance-test path widening.

Report every survivor. A decision-bearing coordinated mutation that survives is BLOCKING.

## 13. Manifest and bundle audit

Independently recompute the candidate manifest and Git identities.

Verify that all decision-bearing artifacts are bound, including:

* protocol and schemas;
* current pointer;
* rendering registry;
* state machine;
* task generator;
* statistics and independent recalculation;
* tokenizer acquisition/equivalence/surface records;
* build and manifest generators;
* candidate tests;
* authoring authority;
* `.gitattributes` where it affects byte reproduction.

Inspect all four deferred exclusions and the self-exclusion. Confirm that each is genuinely unavailable/non-decision-bearing at candidate authoring time and that no active normative dependency sits outside the manifest.

Check whether the current pointer provides an unambiguous route to the complete normative bundle rather than only protocol/Markdown/schema while registry and state machine remain external implicit dependencies.

## 14. Execution feasibility without execution

Do not run a model.

Review whether future execution is sufficiently specified for:

* RT 1.5B;
* RP-B 7B, 14B and 32B;
* framework/library versions;
* dtype;
* quantization or lack thereof;
* device mapping;
* deterministic execution;
* memory feasibility;
* batching/padding;
* token and wall-clock/resource ceilings.

The 32B checkpoint must not be assumed to fit the historical T4 environment. If the protocol leaves dtype/quantization/hardware to later uncontrolled choice and those choices can alter logits or E0 behavior, determine whether freeze is possible without resolving them.

## 15. Test differential

Registered candidate baseline at `da1ea31…`:

`8 failed, 5,120 passed, 16 skipped`

The eight registered standing failures are:

* seven historical host-line-ending failures;
* one scope-expired v0.7 focused-review invariant.

Run:

* candidate checks;
* focused review tests;
* complete full suite at the final review head.

Require:

* no unexplained new failure node ID;
* zero collection errors;
* candidate paths unchanged;
* historical/protected blobs unchanged.

If the known Study 2 mtime test flakes, it may be classified as the previously disclosed flake only if it passes twice in isolation and its full module passes.

Do not edit or suppress an expired historical invariant.

## 16. Review artifacts and publication

Create only additive review artifacts inside `studies/study3r/`, including:

* `reviews/study3r_protocol_v1_single_focused_review.md`
* `reviews/study3r_protocol_v1_single_focused_review.json`
* `reviews/study3r_protocol_v1_single_focused_review.schema.json`
* `reviews/study3r_protocol_v1_review_receipt.json`
* independent recalculation source and tables;
* tokenizer reconstruction report;
* mutation report;
* `reviews/test_study3r_protocol_v1_single_focused_review.py`.

Use a strictly linear publication sequence:

1. review authority alone;
2. independent recalculation/tokenizer/mutation artifacts;
3. review report, schema, receipt and review tests.

Re-fetch `origin/main` before every publication. No merge, rebase, squash, force-push or history rewrite.

After completing the review, fast-forward `origin/main` to the final review commit if and only if the ancestry remains a strict fast-forward from `da1ea31…`.

Do not change the Study 3R candidate state inside its protocol pointer. The review disposition is additive and governs the next operator action.

## 17. Final disclosure

Report:

* starting and final commit/tree;
* authority identity and alone-first ordering;
* independence declaration;
* candidate/protected path comparison;
* tokenizer reconstruction results and counters;
* every finding with severity and affected decision;
* independent census/statistical agreements and mismatches;
* D2/D3 masking analysis;
* ladder/state-machine path reconstruction;
* CoT decoding completeness;
* D0 per-item-position result;
* wrapper-closure interpretation;
* task-generator findings;
* manifest/pointer findings;
* mutation counts and survivors;
* execution-feasibility assessment;
* focused and full-suite results;
* evidence-ledger and authorization state;
* zero prohibited-operation counters;
* final `origin/main`;
* exactly one registered verdict state.

Permitted final states:

`STUDY3R_PROTOCOL_V1_FOCUSED_REVIEW_ACCEPTED_AWAITING_FREEZE_AUTHORITY`

or

`STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION`

or

`STUDY3R_PROTOCOL_V1_TERMINAL_OPERATOR_DECISION_REQUIRED`

No repair, amendment, second authoring session or model execution may follow automatically.
