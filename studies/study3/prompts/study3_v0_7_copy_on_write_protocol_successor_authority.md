# Study 3 v0.7 copy-on-write protocol-placement successor authority

You are the sole drafting party for one bounded successor session in repository `Alanjiao1988/J-space-observation`.

This authority issues the operator decision required by:

* `studies/study3/reviews/v0_7_terminal_operator_decision_required.md`;
* `studies/study3/reviews/v0_7_terminal_operator_decision_required.json`.

It resolves protocol placement only and then resumes the already-authorized single consolidated v0.7 amendment. It is not v0.8, not a second amendment round, not a focused review, and not experimental execution.

## 0. Operator decision and required endpoint

The operator selects:

`OPTION_D_COPY_ON_WRITE_VERSIONED_PROTOCOL`

Create a new, versioned, self-contained draft-v0.7 normative protocol bundle. Preserve the legacy protocol bundle byte-exactly as historical P0 input.

Do not select Option A, B or C:

* do not use the rendering registry as the omnibus normative home for the entire v0.7 protocol;
* do not regenerate or alter the P0 corpus manifest;
* do not retire, weaken, waive or re-scope the frozen-corpus test.

After resolving placement, complete every still-applicable requirement of the original consolidated-amendment authority.

Successful terminal state:

`STUDY3_V0_7_CONSOLIDATED_AMENDMENT_AUTHORED_AWAITING_SINGLE_FOCUSED_REVIEW`

If another genuinely operator-level contradiction is discovered, stop with:

`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`

Do not draft v0.8 and do not conduct the focused review.

---

## 1. Exact starting state

Before editing, fetch `origin/main` and require:

* repository: `Alanjiao1988/J-space-observation`;
* target branch: `main`;
* `HEAD == fetched origin/main`;
* commit: `5b961cb42bada34a88a7895f83ccb2af4e5690e5`;
* tree: `1d1a5e2a137afcbcdaa9199a7dc67b978bee45cd`;
* clean worktree;
* `paper/evidence_ledger.csv` still ends at `EV-0016`;
* `formal_execution_authorized == false`;
* no scientific or model operation occurred after the starting commit.

Require the following three commits to be linear descendants of `9fa28a02eb578f7743e325703b812873b57e0ed2`:

1. `71d346ed1444bdbfb7dd3505824332d32a72585c`
2. `5fb1143ebd628759fda9c252a306e89bf6ef715f`
3. `5b961cb42bada34a88a7895f83ccb2af4e5690e5`

If any condition fails, make no repair and stop:

`BLOCKED_ON_STUDY3_V0_7_SUCCESSOR_STARTING_STATE_INTEGRITY`

### 1.1 Successor-authority-first ordering

Before creating or reading any new successor drafting output:

1. Save this instruction byte-for-byte as
   `studies/study3/prompts/study3_v0_7_copy_on_write_protocol_successor_authority.md`.
2. Commit it alone as the first commit after `5b961cb42bada34a88a7895f83ccb2af4e5690e5`.
3. Record its byte count, SHA-256, Git blob, newline convention, commit and tree.
4. Publish that authority-only commit before producing the new protocol bundle.

No other path may change in that commit.

### 1.2 Authority hierarchy

The binding order is:

1. this copy-on-write successor authority;
2. `study3_v0_7_consolidated_amendment_authority.md`;
3. the v0.7 terminal disposition and placement probe;
4. earlier Study 3 authorities and immutable history.

This authority supersedes only:

* the original v0.7 starting commit/tree;
* section 5’s requirement to edit the legacy unversioned protocol files;
* any implication that the operator is restricted to Options A–C.

All original zero-operation boundaries, scientific decisions, statistical requirements, validation requirements, claim ceilings and terminal rules remain binding.

---

## 2. Legacy protocol bundle is historical and immutable

Preserve these three files byte-exactly:

1. `studies/study3/protocol/interface_calibration_protocol_draft.json`
   SHA-256 `1197e08779f6360a50effeafa8035d9b1d21c0a3b038ecc7cbc0930be03c7ca7`
2. `studies/study3/protocol/interface_calibration_protocol_draft.md`
   SHA-256 `0376c7d5c659fe5535a216b614b6430499c7df235abcf52561dc8f075613b23f`
3. `studies/study3/protocol/interface_calibration_protocol.schema.json`
   SHA-256 `79a8a68a51c686014f2cfe5c8cf4e782b01fc270cf3c9ae5739964abbe4c30c4`

Although only the JSON is directly byte-bound by the P0 corpus manifest, all three must remain unchanged so that the legacy v0.5 bundle remains internally coherent.

Their status becomes:

`HISTORICAL_P0_BINDING_ONLY_NOT_CURRENT_PROTOCOL`

Do not insert that status into the legacy files themselves. Record it only in new v0.7 artifacts and active routing documents.

Also preserve unchanged:

* `studies/study3/pilot/p0/corpus/p0_corpus_manifest.json`;
* `studies/study3/pilot/p0/p0_freeze_corpus.py`;
* `tests/test_study3_p0_feasibility_pilot.py`;
* all historical P0 authorities, receipts, manifests, results and dispositions;
* the original v0.7 authority, placement probe and terminal disposition.

---

## 3. New self-contained v0.7 normative bundle

Create exactly these new protocol artifacts:

* `studies/study3/protocol/interface_calibration_protocol_draft_v0_7.json`
* `studies/study3/protocol/interface_calibration_protocol_draft_v0_7.md`
* `studies/study3/protocol/interface_calibration_protocol_draft_v0_7.schema.json`
* `studies/study3/protocol/interface_calibration_rendering_registry_v0_7.json`
* `studies/study3/protocol/interface_calibration_rendering_registry_v0_7.schema.json`
* `studies/study3/protocol/interface_calibration_protocol_current.json`
* `studies/study3/protocol/interface_calibration_protocol_current.schema.json`

### 3.1 Normative hierarchy

Register this hierarchy unambiguously:

1. `interface_calibration_protocol_draft_v0_7.json` is the sole top-level normative protocol.
2. Its v0.7 schema validates the complete protocol.
3. The v0.7 rendering registry is a subordinate normative asset referenced by exact path and hash.
4. The Markdown file is a human-readable companion and must agree with every decision-bearing JSON marker.
5. `interface_calibration_protocol_current.json` is a routing pointer, not an additional source of scientific rules.
6. Legacy v0.5 protocol files and the v0.6 registry are provenance inputs, not active overlays that an executor must merge at runtime.

An executor must be able to determine the complete v0.7 design from the new v0.7 protocol plus the exact subordinate assets it references. It must not need to reconstruct the active protocol by layering v0.5, v0.6 and v0.7 amendments manually.

### 3.2 Current-protocol pointer

The machine-readable current pointer must contain at least:

* active draft version;
* protocol state;
* `frozen: false`;
* `execution_authorized: false`;
* exact paths and SHA-256 values of the new protocol JSON, schema, Markdown and rendering registry;
* the legacy protocol path and hash under a field explicitly labelled historical P0 binding only;
* the authority and amendment identities;
* the next legal action;
* a prohibition on falling back to the legacy path if the v0.7 bundle is absent or invalid.

The pointer must fail closed. Missing, mismatched or invalid v0.7 files must not cause a loader to use the legacy v0.5 protocol.

### 3.3 Derivation and provenance

The v0.7 amendment must record that the new protocol was derived from:

* the immutable legacy v0.5 protocol bundle;
* the normative v0.6 scoring/rendering registry;
* the original v0.7 consolidated-amendment authority;
* this successor authority;
* the placement probe and terminal disposition.

Integrate all still-valid content into one self-contained v0.7 protocol. Do not merely copy the old JSON and append an unvalidated free-form block.

The v0.7 schema must explicitly register all new decision-bearing structures, including E0, D0, wrapper joint adequacy, generated-CoT ceiling, Q0, RP-B, RP-M, tokenizer functional equivalence, shakedown governance and recursive-manifest sealing.

Retain `additionalProperties: false` or an equally fail-closed schema policy for decision-bearing structures.

---

## 4. Resume the original consolidated amendment

Read the original authority in full:

`studies/study3/prompts/study3_v0_7_consolidated_amendment_authority.md`

Then complete every unexecuted requirement in its sections 2–10, including:

* the absolute zero-operation boundary;
* P0-R2 historical treatment and all four audit exceptions;
* dual E0/D0 estimands;
* exact E0 surfaces, parser and decoding contract;
* full-context tokenization rules;
* descriptive D0 diagnostics;
* existing I1a/I1b/I2 competence-floor battery;
* role-internal wrapper-only joint adequacy;
* canonical generated-CoT ceiling;
* Q0 and the first-confirmed-pass RP-B ladder;
* Bonferroni allocation over full registered ladder length `L`;
* RP-B/RP-M separation;
* per-checkpoint tokenizer functional equivalence;
* disjoint engineering-shakedown authority and numeric bounds;
* negative-control equivalence rule;
* recursive-manifest seal;
* activation/patching prerequisites;
* claim-ceiling and causal-language restrictions;
* complete numerical and semantic closure;
* focused-review preparation without a verdict.

Create the amendment artifacts originally required:

* `studies/study3/reviews/v0_7_operator_amendment.md`
* `studies/study3/reviews/v0_7_operator_amendment.json`
* `studies/study3/reviews/v0_7_operator_amendment.schema.json`

Do not create a parallel 400-cluster MDE and do not replace the registered I1a/I1b/I2 battery.

---

## 5. Active and historical code separation

Before modifying any existing analysis, validator, routing or test file, classify it mechanically:

* if its bytes are hash-bound by a historical manifest, receipt, image or reproducibility check, leave it unchanged and create a versioned v0.7 successor;
* if it is required to reproduce P0, leave it unchanged;
* otherwise it may be updated only when necessary to route prospective v0.7 work to the new versioned protocol.

Historical P0 readers must continue to load the legacy protocol explicitly.

Prospective v0.7 readers must load the current-protocol pointer or the exact versioned v0.7 path. They must not silently load `interface_calibration_protocol_draft.json`.

Do not use a global search-and-replace that changes historical paths or prose.

Update active routing/status documents only to:

* identify the new v0.7 protocol as current;
* identify the old protocol as historical P0 binding;
* state that v0.7 is unfrozen and unexecuted;
* route the next action to one independent focused review.

Historical records must retain their original wording and paths.

---

## 6. Required validation

Before publishing a successful v0.7 candidate, prove:

### 6.1 Historical preservation

* all three legacy protocol hashes equal the values in section 2;
* `p0_corpus_manifest.json` is byte-identical;
* `p0_freeze_corpus.py --check` passes;
* `p0_protocol.py --check` passes;
* all protected P0 paths are unchanged;
* the original placement probe remains reproducible;
* evidence ledger remains byte-identical and ends at `EV-0016`.

### 6.2 New protocol integrity

* the new v0.7 JSON validates against the new v0.7 schema;
* Markdown agrees with every decision-bearing JSON marker;
* rendering registry validates against its schema;
* current pointer validates and all recorded hashes match;
* the active pointer resolves only to the versioned v0.7 bundle;
* deleting or corrupting the v0.7 bundle fails closed rather than loading v0.5;
* no prospective v0.7 test or loader treats the legacy generic JSON as current;
* all v0.7 authority requirements are represented in machine-readable fields;
* no contradictory duplicate rule exists across the protocol and registry;
* no `TBD`, runtime choice, unstated threshold or operator-discretion field remains.

### 6.3 Statistical and state-machine integrity

Run all checks required by the original authority, including exact recalculation of:

* sample sizes and pass counts;
* alpha families and denominators;
* generated-CoT threshold and aggregation;
* Q0 ladder length and multiplicity;
* negative-control margin;
* wrapper descriptive bandwidth;
* reproducibility criteria;
* shakedown limits;
* operation projections;
* every legal terminal transition.

All v0.7-specific and affected tests must pass.

The full suite may contain only exact, previously registered standing failures whose paths and signatures are byte-identical to the starting state. Report them separately; do not describe them as new failures, and do not repair protected historical bytes. Any new failure, fixed historical failure caused by an unauthorized edit, collection error or changed signature blocks publication.

### 6.4 Zero-operation verification

All counters prohibited by the original authority must remain zero, including cloud, tokenizer, checkpoint, model, generation, scoring, seed, bank, qualification and evidence operations.

---

## 7. Publication discipline

Re-fetch `origin/main` before every publication. Stop on any unexpected advance.

All commits must be strictly linear descendants of the successor-authority commit. Do not merge, rebase, force-push or rewrite history.

The successor authority is one additive authority for the same v0.7 amendment. Do not rename the candidate v0.8 or v0.7.1.

Do not edit or delete:

* the earlier v0.7 terminal disposition;
* its JSON form;
* the placement probe or probe output.

They remain the historical record of the correctly triggered operator-decision stop.

If another blocking contradiction occurs, publish a new additive successor disposition without overwriting the first one.

---

## 8. Required final disclosure

Report:

* starting and final commit/tree;
* successor-authority path, commit, tree, blob, byte count, SHA-256 and newline properties;
* full linear commit sequence;
* all created and modified paths;
* hashes of the immutable legacy protocol trio before and after;
* confirmation that the P0 manifest and frozen-corpus test were neither edited nor weakened;
* paths and hashes of the complete new v0.7 normative bundle;
* current-pointer contents and validation result;
* every frozen decision-bearing numeric constant;
* exact validation commands and results;
* exact standing historical failures, if any;
* all zero-operation counters;
* evidence-ledger tail;
* `formal_execution_authorized`;
* frozen/unfrozen status;
* research-question status;
* next legal action.

Do not claim that the Git DAG independently proves an historical force-push count. Distinguish “no force-push command performed by this session” from repository-verifiable linearity.

A successful disclosure must end exactly:

`STUDY3_V0_7_CONSOLIDATED_AMENDMENT_AUTHORED_AWAITING_SINGLE_FOCUSED_REVIEW`
