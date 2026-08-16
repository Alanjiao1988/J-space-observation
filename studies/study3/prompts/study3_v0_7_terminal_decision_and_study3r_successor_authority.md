You are the operator-governance executor for `Alanjiao1988/J-space-observation`.

This is a repository-governance and project-routing session. It is not a protocol-authoring, protocol-repair, model-execution, or scientific-measurement session.

## Binding objects

* Current expected `origin/main`:
  `459d002442641039196ac3880d47a45a3b79a4c8`
* Reviewed draft-v0.7 target:
  `459d002442641039196ac3880d47a45a3b79a4c8`
* Independent review head:
  `a08ec1462f023da49247cac0756b7af5f32ba75a`
* Required review disposition:
  `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`

The operator decision is:

1. Accept the independent review’s 12 BLOCKING, 3 MAJOR and 2 MINOR findings as the governing assessment of draft-v0.7.
2. Reject and terminally close draft-v0.7 without repairing it.
3. Prohibit v0.7.1, v0.8, or any incremental carry-forward repair.
4. Authorize one clean-room successor, named **Study 3R**, in the same repository.
5. Do not author the Study 3R protocol in this session.
6. Do not execute any model, tokenizer, cloud, GPU, scoring, generation, task-bank, interface-selection or patching operation.

## Phase 0 — read-only integrity checks

Fetch `origin` and verify:

* clean worktree;
* `origin/main` is exactly `459d002…`, or stop unless it has already been fast-forwarded exactly along the registered review lineage;
* `a08ec146…` exists and is exactly three commits ahead of `459d002…`, zero behind, with merge base `459d002…`;
* the comparison contains exactly eight added review paths and no modification to any reviewed candidate or historical protected path;
* the three commits are `66fec8a…`, `d5ead7f…`, `a08ec14…`, strictly linear and merge-free.

If any identity, ancestry or path-set condition differs, stop with:

`STUDY3_V0_7_OPERATOR_ROUTING_BLOCKED_ON_REPOSITORY_IDENTITY`

Do not “repair” an unexpected repository state.

## Phase 1 — authority first

Create a new branch directly from exact commit `a08ec146…`.

Save this prompt, byte-for-byte from its first line through its terminal-state declaration, as:

`studies/study3/prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md`

Record byte length, SHA-256, Git blob, newline convention, parent commit and tree.

Commit this authority alone as the first commit after `a08ec146…` and publish that commit on the session branch before creating any other artifact.

No finding, reconciliation result, terminal decision or Study 3R file may exist before the authority-only commit.

## Phase 2 — reconcile the full-suite disclosure

Do not modify any committed independent-review artifact.

In a clean detached worktree at exact commit `a08ec146…`, run the complete test suite once and record the exact command, environment and result.

The expected distinction to verify is:

* reviewed target `459d002…`: committed review artifacts report
  `7 failed, 4,926 passed, 16 skipped`;
* final review head `a08ec146…`: terminal disclosure reports
  `7 failed, 4,958 passed, 16 skipped`;
* the difference should be exactly the 32 newly added focused-review tests.

Treat this as a provenance reconciliation, not as a revision of the methods verdict.

Create additive artifacts:

* `studies/study3/reviews/v0_7_review_head_test_count_reconciliation.md`
* `studies/study3/reviews/v0_7_review_head_test_count_reconciliation.json`
* a restrictive JSON schema for the reconciliation.

The addendum must explicitly quote both counts, identify which commit each count describes, state the independently rerun result, and explain whether the 32-test difference is fully accounted for.

If the rerun does not support an exact reconciliation, stop with:

`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED_TEST_COUNT_UNRECONCILED`

Do not edit the original review report, JSON, receipt or tests.

## Phase 3 — terminalize draft-v0.7

Create a machine-readable and human-readable operator decision declaring:

`STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION`

The decision must state:

* draft-v0.7 failed its single allowed independent focused review;
* no v0.7 finding is converted into a limitation;
* draft-v0.7 is not frozen, selected, executable or amendable;
* the v0.7 protocol, pointer, registries, schemas, builder and tests are retained as immutable rejected-candidate history;
* `formal_execution_authorized = false`;
* the evidence ledger remains at `EV-0016`;
* no scientific evidence was produced and the research question remains unanswered;
* no v0.7.1 or v0.8 may be automatically drafted;
* the old `interface_calibration_protocol_current.json` is an internal pointer belonging to the rejected candidate and is not an active project protocol.

Do not modify the reviewed v0.7 protocol bundle or independent-review artifacts.

Replace only the prospective routing banner at the top of `studies/study3/README.md` with a terminal routing banner. It must route readers first to the operator terminal decision and clearly label every v0.7 protocol artifact as a rejected, non-executable candidate.

Create restrictive schemas and tests enforcing this state.

## Phase 4 — authorize Study 3R, without authoring its protocol

Create a concise Study 3R charter under a new `studies/study3r/` namespace. This is a clean-room successor, not v0.8 and not a copy-on-write continuation of the legacy protocol.

Freeze the following project-level decisions in the charter:

1. Primary headline estimand:
   `E0_zero_generated_reasoning_token_expressed_competence`.
2. `D0_single_forward_decodability` is a conditional diagnostic only and is never an RP-B gate.
3. The natural RP-B ladder has fixed membership and fixed order, with `L = 3`:

   * `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`
   * `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`
   * `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`
     ordered by parameter count ascending, with no fallback candidate and no post-result expansion.
4. Immutable checkpoint revisions must be resolved and sealed before protocol freeze.
5. Q0 uses E0 as its primary gate, item-disjoint development and confirmation sets, first-confirmed-pass selection, and multiplicity correction over the full registered `L = 3`.
6. Wrapper qualification remains a two-arm joint-adequacy gate. Both arms must be represented in the atomic-cell census and multiplicity calculation; the author may not reuse `m_max = 43` without independently re-deriving it.
7. Wrapper bytes, roles, separators, BOS/EOS behavior, answer cues, few-shot examples and template revisions must be frozen exactly.
8. The negative control must use an executable one-sided upper-bound/equivalence design with a registered unit, chance level, margin, sample size, alpha, exact construction and multiplicity family.
9. E0 legal answer surfaces and token sequences are checkpoint-revision-specific. `max_new_tokens` is derived per checkpoint as the longest frozen legal answer surface plus the registered termination margin; the universal value 3 is not inherited.
10. Tokenizer-functional inequality creates an explicitly separate isomorphic-reinstantiation stratum and may never be pooled as the same frozen interface.
11. The generated-CoT ceiling is a per-checkpoint execution precondition with `k = 1`, a frozen task population, bank relationship, parser, context/generation bound and total resource bound. It is not an interface selector.
12. Study 3R covers behavioral and interface qualification only.
13. RP-M, activation patching and mechanism claims are outside Study 3R and are not authorized. They may be considered later as a separate Study 3M only after all Study 3R gates pass.
14. The Study 3R state machine, schema, registry, statistics, manifest generator and semantic tests must be written cleanly from scratch. Do not carry forward the legacy 40-key protocol structure.
15. Every decision-bearing schema field must be constrained. Validation must include coordinated generator-mutation tests, not only artifact-versus-generator byte equality.
16. Study 3R receives one protocol-authoring session and one independent focused review. If that review returns any BLOCKING finding, Study 3R terminates; no automatic amendment follows.

The charter must not contain a protocol, task-bank realization, checkpoint download, tokenizer output, selected interface, numerical gate calculation or execution authorization.

Set its state to:

`STUDY3R_CLEAN_ROOM_PROTOCOL_AUTHORIZED_AWAITING_SINGLE_AUTHORING_SESSION`

## Publication and validation

Use strictly linear commits:

1. authority alone;
2. test-count reconciliation;
3. v0.7 terminal decision, Study 3R charter, routing change, schemas and tests.

Before every publication, re-fetch `origin/main` and verify it has not advanced unexpectedly.

Run:

* JSON/schema validation for every new machine-readable artifact;
* the new focused governance tests;
* the complete local suite at the final governance head;
* protected-byte comparisons;
* evidence-ledger and formal-execution checks.

All cloud/model/tokenizer/scientific-operation counters must remain zero.

After all artifacts and tests are complete, fast-forward `origin/main` exactly along the linear chain from `459d002…` through `a08ec146…` to the final governance commit. No merge commit, squash, rebase, force-push or history rewrite is authorized.

If branch policy prevents the fast-forward, stop with:

`STUDY3R_OPERATOR_DECISION_PUBLISHED_AWAITING_MAIN_FAST_FORWARD`

## Final disclosure

Report:

* starting `origin/main`, review head and final commit/tree;
* exact ancestry and changed paths;
* authority identity and ordering;
* original and reconciled full-suite counts;
* all terminal-decision and Study 3R charter artifacts and hashes;
* final full-suite result;
* protected-byte and evidence-ledger status;
* zero-operation counters;
* whether `origin/main` now equals the final governance commit.

Successful terminal state:

`STUDY3R_CLEAN_ROOM_PROTOCOL_AUTHORIZED_AWAITING_SINGLE_AUTHORING_SESSION`
