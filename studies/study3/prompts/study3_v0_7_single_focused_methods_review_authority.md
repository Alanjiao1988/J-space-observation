# Study 3 draft-v0.7 — single independent focused methods review authority

You are the sole independent methods reviewer for one fresh, bounded review session in repository `Alanjiao1988/J-space-observation`.

You must not have participated in drafting draft-v0.7, its consolidated-amendment authority, its copy-on-write successor authority, its protocol builder, amendment artifacts or tests.

If you participated in any of those drafting activities, stop immediately:

`BLOCKED_STUDY3_V0_7_REVIEWER_NOT_INDEPENDENT`

This is the one registered focused review. It is not an amendment, correction session, protocol freeze, shakedown, model execution or scientific experiment.

## 0. Permitted outcomes

Review the published draft-v0.7 candidate without editing it.

Exactly two substantive outcomes are permitted:

### Acceptance

`STUDY3_V0_7_FOCUSED_METHODS_REVIEW_ACCEPTED_AWAITING_SEPARATE_FREEZE_AUTHORITY`

Acceptance requires:

* zero BLOCKING findings;
* zero MAJOR findings;
* no contradictory decision-bearing fields;
* no unresolved operator choice required for execution;
* complete deterministic state transitions;
* complete and reproducible normative assets;
* independently verified statistics;
* all gate-bearing implementation semantics fixed or legitimately and deterministically sealed before data.

Acceptance does not freeze or authorize execution. A separate operator freeze authority would still be required.

### Rejection

`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`

Return this state if any BLOCKING or MAJOR finding remains.

Do not repair the candidate, draft v0.8, create v0.7.1, propose an automatic amendment, or continue into freeze or execution.

MINOR findings are compatible with acceptance only when they cannot change an estimand, sample, threshold, gate, transition, parser, interface, normative byte, result interpretation or execution decision.

---

## 1. Exact reviewed target and starting integrity

Require:

* repository: `Alanjiao1988/J-space-observation`;
* branch target: `main`;
* `HEAD == fetched origin/main`;
* reviewed commit: `459d002442641039196ac3880d47a45a3b79a4c8`;
* reviewed tree: `2c84d55e6a965972e7cd3f69e3b0cded0bddfb04`;
* parent: `b9cddfc3a4c57a55bfef6105702be914c2545da1`;
* clean worktree;
* `paper/evidence_ledger.csv` ends at `EV-0016`;
* `formal_execution_authorized == false`.

Independently verify that the reviewed target is three linear commits ahead of:

`5b961cb42bada34a88a7895f83ccb2af4e5690e5`

and that its changed-path set consists only of the disclosed 13 additions and additive Study 3 README routing modification.

The current Git DAG can establish ancestry, parent count and absence of merge commits. It cannot independently prove historical force-push count.

If the target differs, stop without repair:

`BLOCKED_ON_STUDY3_V0_7_FOCUSED_REVIEW_STARTING_STATE_INTEGRITY`

### 1.1 Review-authority-first ordering

Before producing or reading any review output:

1. Save this instruction byte-for-byte as
   `studies/study3/prompts/study3_v0_7_single_focused_methods_review_authority.md`.
2. Commit it alone as the first commit after the reviewed target.
3. Record its bytes, SHA-256, Git blob, newline convention, commit and tree.
4. Publish that authority-only commit before creating review findings.

The review target remains commit `459d002…`, not the later authority commit.

---

## 2. Absolute review boundary

Perform zero:

* Azure, ACR, ACA, GPU or cloud-job operations;
* tokenizer construction, encode or decode;
* checkpoint resolution, download or loading;
* model, weight, adapter or activation loading;
* prefill, forward pass, logit read, scoring or generation;
* output parsing on model outputs;
* seed draw, bank generation or split realization;
* confirmation access;
* interface, RP-B or RP-M qualification;
* evidence-ledger addition;
* scientific-evidence claim.

Permitted operations are read-only repository inspection, independent CPU-only exact arithmetic, schema validation, mutation testing in temporary copies, static analysis and deterministic test execution.

Do not modify any reviewed protocol, registry, amendment, builder, candidate test, legacy protocol or historical P0 artifact.

---

## 3. Required reading

Read completely:

* both v0.7 authorities;
* the v0.7 placement probe and terminal disposition;
* all seven active protocol-bundle artifacts;
* all three v0.7 operator-amendment artifacts;
* `v0_7_protocol_build.py`;
* `tests/test_study3_v0_7_protocol.py`;
* the v0.6 registry, schema and operator amendment;
* the legacy v0.5 protocol JSON, Markdown and schema;
* `design_statistics.py` and its tables;
* the current Study 3 README and routing state;
* relevant P0 freeze code, manifest, tests and dispositions;
* prior review findings needed to distinguish historical text from active rules.

Do not treat the drafting party’s tests, builder output or final disclosure as independent evidence. Recalculate and inspect independently.

---

## 4. Required independent artifacts

Create additive review artifacts only:

* `studies/study3/reviews/v0_7_single_focused_methods_review.md`
* `studies/study3/reviews/v0_7_single_focused_methods_review.json`
* `studies/study3/reviews/v0_7_single_focused_methods_review.schema.json`
* `studies/study3/analysis/independent_methods_recalculation_v0_7.py`
* `studies/study3/analysis/independent_methods_recalculation_tables_v0_7.json`
* `tests/test_study3_v0_7_focused_review.py`
* `studies/study3/methods_review_receipt_v0_7.json`

The independent recalculation must not import:

* `v0_7_protocol_build.py`;
* `design_statistics.py`;
* a production gate calculator whose values it is supposed to verify.

Standard-library or independently implemented exact-binomial arithmetic is permitted. State every external package used.

---

## 5. Mandatory review questions

The following are audit targets, not pre-adjudicated findings. Verify each directly from committed bytes and classify it independently.

### 5.1 Normative-source uniqueness and self-containment

Determine whether the active protocol has exactly one unambiguous top-level normative source.

Specifically reconcile:

* `protocol_placement_v0_7.sole_top_level_normative_protocol`;
* the current pointer;
* `status.authoritative_artifact`, which may still identify the legacy unversioned JSON;
* the v0.7 registry’s normative inheritance of the v0.6 scoring registry;
* the current pointer’s active-bundle list, which may omit that v0.6 registry.

Ask whether an independent executor can recover every active scoring and rendering rule from the active bundle without manually layering v0.5, v0.6 and v0.7.

Any unresolved competing normative source or unsealed normative dependency is BLOCKING.

### 5.2 OD2, RP-B ladder and multiplicity

Inspect:

* `blocking_decisions`;
* `unresolved_operator_decisions`;
* `positive_reference_candidates`;
* `q0_and_rp_b_v0_7`;
* `deterministic_deferrals_v0_7`;
* positive-reference operation projections.

Determine whether OD2 was actually closed.

For `DEFER-02`, verify that the candidate universe, eligibility predicate, ordering rule and metadata snapshot deterministically produce one unique ladder and one unique `L` without operator judgment.

A generic family description such as “eligible Qwen-family candidates” is not a deterministic enumeration unless the candidate universe and observation date/source are frozen.

Verify that `L` and the Bonferroni denominator are fixed before any Q0 development result.

If OD2 remains blocking, or ladder membership can vary under equally compliant operators, classify BLOCKING.

### 5.3 State-machine integration

Determine whether all v0.7 preconditions and gates are integrated into one total state machine, including:

* engineering shakedown exit;
* generated-CoT ceiling;
* E0;
* D0’s descriptive-only branch;
* Q0 RP-B qualification;
* RP-M method validation;
* wrapper joint adequacy;
* interface development and confirmation;
* activation/patching authorization boundary.

Check whether legacy `Q0_INSTRUMENT` conflicts by name or meaning with v0.7 Q0.

Verify exactly one legal transition for every complete outcome.

A collection of prose blocks that is not integrated into the executable state machine is BLOCKING.

### 5.4 Cross-field consistency

Search all active fields, not only new v0.7 blocks, for contradictory statements.

At minimum compare:

* K6 applicability in `gate_hierarchy`, `gate_truth_table`, cell census and rendering registry;
* active review round and state;
* authoritative protocol path;
* OD2 status;
* RP wrapper status;
* gate counts and operation projections;
* “fourth review” language versus “single focused review”;
* legacy status fields carried into the new protocol.

Any two active decision-bearing fields assigning different meanings or outcomes to the same event are BLOCKING.

Historical prose may retain prior wording only when mechanically identified as historical and excluded from active interpretation.

### 5.5 Wrapper-only identifiability

Verify that every wrapper arm is frozen as executable bytes or a deterministic rendering algorithm with no unstated choice.

For each role require exact registration of:

* message roles and ordering;
* literal system/user/assistant content;
* separators and newlines;
* BOS/EOS handling;
* generation prompt behavior;
* chat-template revision or exact template bytes;
* RL few-shot demonstrations, ordering and answer cue;
* the exact field allowed to differ inside each within-role pair.

Wrapper IDs and natural-language descriptions alone are insufficient.

Verify mechanically that each pair differs only in the registered wrapper transformation.

If exact rendering cannot be reconstructed before data, classify BLOCKING.

### 5.6 E0 answer and tokenizer contract

Verify whether the universal claims:

* every surface has two tokens;
* `max_new_tokens = 3`;

remain valid for:

* every RT/RL/RI immutable revision;
* every natural RP-B candidate;
* every isomorphic-reinstantiation stratum;
* every training-constructed fallback candidate.

Reconcile those claims with deferred checkpoint revisions and per-checkpoint functional-equivalence testing.

If a tokenizer mismatch creates an isomorphic stratum, determine whether that stratum has a separately frozen legal-surface and generation-length contract or is ineligible for E0/RP-B.

Verify EOS, length-cap termination and exact-match handling for every branch.

### 5.7 Generated-CoT ceiling

Verify that the ceiling registers:

* exact task population and stratum;
* exact generator/bank relationship;
* checkpoint-level decision scope;
* null, alternative, alpha, n and critical count;
* exact canonical wrapper and route marker;
* parser;
* generation length;
* reproducibility rule;
* operation and resource upper bound.

Determine whether reusing the I2 primitive-headroom test is construct-valid for the task whose canonical generated-CoT headroom is intended to be established.

Distinguish the null floor `theta=1/2` from the actual critical accuracy `129/214`.

For `DEFER-03`, assess whether “all remaining context-window tokens” is:

* a legitimate runtime identity;
* a pre-registered resource bound;
* comparable across checkpoints;
* compatible with the sealed operation projection.

An execution-time design choice or unbounded cost is BLOCKING.

### 5.8 Negative-control equivalence

Independently verify the scientific and statistical meaning of the `17/100` upper bound.

Require exact registration of:

* independent unit;
* sample size;
* alpha;
* confidence-bound construction;
* pass count or deterministic equivalent;
* multiplicity family;
* expected null/chance distribution;
* resource/operation projection.

A margin alone is not an executable equivalence design.

### 5.9 Statistical recalculation

Independently reproduce every decision-bearing statistic, including:

* all development and confirmation exact-binomial tails;
* all sample sizes and pass counts;
* `m_max`;
* false-positive and false-negative allocations;
* profile and study power bounds;
* CoT ceiling statistics;
* Q0 multiplicity formula;
* negative-control rule;
* operation projections after adding wrappers, E0, CoT and RP qualification.

Check whether wrapper joint adequacy creates additional gate-bearing cells or multiplicity obligations not reflected in the reported census.

Do not accept “unchanged” without a derivation.

### 5.10 Schema and mutation resistance

Inspect the v0.7 protocol, registry, pointer and amendment schemas recursively.

Determine whether schemas constrain decision-bearing values and structures, rather than merely requiring top-level keys.

Perform temporary-copy mutations of at least:

* E0/D0 gate membership;
* CoT `theta`, n and pass count;
* OD2 status;
* ladder multiplicity;
* K6 applicability;
* wrapper role and arm;
* authoritative protocol path;
* `frozen` and `execution_authorized`;
* terminal transitions;
* manifest exclusions.

A decision-bearing mutation accepted by both schema and committed validators is at least MAJOR and is BLOCKING when it can change execution or interpretation.

### 5.11 Recursive-manifest completeness

Verify that sealed inclusion rules cover the actual future paths for:

* protocol and schemas;
* all transitive normative registries;
* current pointer;
* parser and renderer code;
* runner and scoring code;
* task banks and generators;
* checkpoint and tokenizer identities;
* analysis/finalizer/validator code;
* decision tables;
* wrapper assets;
* manifest generator itself.

Require a named manifest-generator path and a non-self-referential construction.

Conceptual nouns that are not mapped to exact paths or deterministic future path rules do not constitute a sealed inclusion policy.

### 5.12 Tests and historical preservation

Independently verify:

* the legacy protocol trio remains byte-identical;
* P0 corpus manifest and tests remain unchanged;
* P0 reproduction checks pass;
* no new full-suite failure or changed historical signature exists;
* the v0.7 tests do not simply regenerate and compare outputs using the same implementation;
* the 58 passing tests cover substantive contradictions and mutation resistance.

Historical standing failures must be reported separately and cannot hide a new v0.7 failure.

---

## 6. Finding and verdict rules

Each finding must include:

* stable ID;
* severity: BLOCKING, MAJOR or MINOR;
* exact paths and JSON fields;
* independently reproduced evidence;
* affected estimand, gate or claim;
* why existing tests did or did not detect it;
* whether it creates operator discretion;
* minimal operator-level decision needed, if any;
* explicit statement that the reviewer did not implement a repair.

Return acceptance only if the candidate is complete, internally consistent, independently reproducible and executable without unstated choices.

If any BLOCKING or MAJOR finding exists, the terminal disposition must be:

`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`

Do not convert a confirmed defect into a “limitation” merely to reach acceptance.

---

## 7. Validation and publication

Run:

* the independent v0.7 recalculation;
* all v0.7 candidate tests;
* the new focused-review tests;
* P0 reproduction checks;
* design-statistics checks;
* the full suite at the reviewed target and review head where feasible.

Publish linearly:

1. review authority alone;
2. independent recalculation and findings;
3. final review report, JSON, schema, receipt and tests.

Do not modify the reviewed candidate or historical artifacts.

Re-fetch `origin/main` before every publication. Stop on unexpected advancement. No merge, rebase, force-push or history rewrite.

---

## 8. Required final disclosure

Report:

* reviewed commit/tree;
* final commit/tree;
* authority identity and authority-only ordering;
* review independence;
* every finding by severity;
* exact independent recalculation results;
* mutation-test results;
* full-suite differential;
* reviewed candidate paths changed: exactly zero;
* historical protected paths changed: exactly zero;
* all prohibited operation counters;
* evidence-ledger tail;
* `formal_execution_authorized`;
* whether the research question was answered;
* exact review verdict;
* exact next legal action.

End with exactly one of:

`STUDY3_V0_7_FOCUSED_METHODS_REVIEW_ACCEPTED_AWAITING_SEPARATE_FREEZE_AUTHORITY`

or

`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`

Do not draft v0.8 or begin a repair.
