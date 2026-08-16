# Study 3 v0.7 single consolidated amendment — sole authoring authority

You are the sole drafting party for one bounded Study 3 v0.7 consolidated-amendment session in repository `Alanjiao1988/J-space-observation`.

This session is authorized to create and publish the v0.7 design candidate and its deterministic validation artifacts. It is **not** an independent methods review, engineering-shakedown execution, model run, tokenizer run, scientific measurement, or protocol freeze.

## 0. Required endpoint

Produce exactly one consolidated draft-v0.7 amendment incorporating all binding decisions below.

Successful terminal state:

`STUDY3_V0_7_CONSOLIDATED_AMENDMENT_AUTHORED_AWAITING_SINGLE_FOCUSED_REVIEW`

If a binding requirement cannot be made internally consistent, numerically complete, and machine-verifiable without an additional operator-level scientific choice, stop with:

`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`

Do not draft v0.8. Do not perform or simulate the focused review. Do not freeze or execute Study 3.

---

## 1. Exact starting state

Before editing, fetch `origin/main` and require:

* repository: `Alanjiao1988/J-space-observation`;
* branch target: `main`;
* `HEAD == fetched origin/main`;
* commit: `9fa28a02eb578f7743e325703b812873b57e0ed2`;
* tree: `5863bfcd25dc005fdca27707ac5f76b61e0c3f87`;
* clean worktree;
* `paper/evidence_ledger.csv` still ends at `EV-0016`;
* `formal_execution_authorized == false`;
* no Study 3 scientific operation has occurred after the starting commit.

If any condition fails, make no repair and stop:

`BLOCKED_ON_STUDY3_V0_7_STARTING_STATE_INTEGRITY`

Recheck `origin/main` immediately before every publication. Do not merge, rebase, cherry-pick around a mismatch, force-push, or overwrite concurrent work.

### 1.1 Authority-first ordering

Before reading or creating any v0.7 drafting output:

1. Save this complete instruction as
   `studies/study3/prompts/study3_v0_7_consolidated_amendment_authority.md`.
2. Preserve its wording and decision semantics exactly.
3. Commit that file alone as the first commit after the exact starting commit.
4. Record its byte count, Git blob ID, SHA-256, newline convention, commit and tree.
5. Publish the authority commit before any v0.7 derivation or amendment output is committed.

No other path may change in the authority commit.

---

## 2. Absolute zero-operation boundary

This session must perform zero:

* Azure, ACR, ACA, GPU, accelerator or cloud-job operations;
* tokenizer construction, encode, decode or tokenizer-file retrieval;
* checkpoint resolution that downloads checkpoint assets;
* checkpoint, weight, adapter or activation loading;
* prefill, forward pass, logit read, scoring or generation;
* model-output parsing;
* seed draw, task-bank generation, random split realization or confirmation access;
* interface qualification or selection;
* RP-B or RP-M qualification;
* evidence-ledger additions;
* scientific-evidence claims.

Permitted work is limited to repository inspection, deterministic protocol drafting, CPU-only static validation, schema validation, exact arithmetic, symbolic/statistical derivation, fixture construction from already committed non-secret bytes, and tests that import no model or tokenizer library and contact no external service.

Do not use GitHub Actions as a substitute for local deterministic validation.

---

## 3. Immutable history and P0-R2 disposition

P0-R1, P0-R2 generation 1 and P0-R2 generation 2 remain terminal, consumed and historically immutable.

Do not:

* create P0-R2 generation 3;
* repair, reopen, rerun or retrospectively reclassify any P0 execution;
* alter historical authorities, raw logs, receipts, dispositions, manifests or result bytes;
* treat a P0 infrastructure result as scientific evidence;
* infer model competence or incapability from P0-R2.

The v0.7 starting-state disclosure must state:

* generation-2 live replay mechanically passed and was independently reconstructed;
* bounded pilot authorization failed;
* no GPU job was created or started;
* model, tokenizer, scoring and GPU operation counters remained zero;
* evidence ledger remained at `EV-0016`;
* the research question remained unanswered.

It must also record these governance audit exceptions without repairing historical files:

1. Aggregate attempt-ledger and handoff counts predate the final live-prefix/replay operations and are not a complete final aggregate, although the individual terminal receipts exist.
2. Committed Phase-B/preflight evidence binds an earlier head and lock; no committed artifact proves the entire 38-condition admission result at the exact replay anchor.
3. The final hard-kill job used an empty `CUDA_VISIBLE_DEVICES` value although the authority literally specified `-1`; the safe no-GPU intent was preserved, but literal byte-level compliance cannot be claimed.
4. The current Git DAG establishes linear history and no merge, but historical force-push count is `UNKNOWN` without an independent GitHub audit log.

Therefore the legal characterization is:

`P0_R2_G2_TERMINAL_VERIFIED_WITH_AUDIT_EXCEPTIONS`

Do not write “full authority compliance verified” or “zero force-pushes verified.”

---

## 4. Required reading

Read completely at the exact starting commit:

* the current protocol JSON, Markdown and schema;
* rendering registries and schemas through v0.6;
* `v0_6_operator_amendment.md`, JSON and schema;
* all v0.5/v0.6 authority documents;
* all P0-T, P0-R1 and P0-R2 dispositions, authorities, handoffs, locks, ledgers and receipts needed to establish current state;
* `design_statistics.py` and all generated design-statistics tables;
* current Study 3 validators and tests;
* Study 3 README, repository routing documents, handoff, current-status report, decision log, methods ledger, run log and artifact index;
* all earlier independent review and operator-amendment records as immutable provenance.

The discussion memo and external AI review are non-authoritative inputs. Do not copy their proposed 400-cluster MDE or create a parallel experiment. The registered I1a/I1b/I2 battery remains the calibration battery.

---

## 5. Required v0.7 artifacts

At minimum create:

* `studies/study3/reviews/v0_7_operator_amendment.md`
* `studies/study3/reviews/v0_7_operator_amendment.json`
* `studies/study3/reviews/v0_7_operator_amendment.schema.json`
* `studies/study3/protocol/interface_calibration_rendering_registry_v0_7.json`
* `studies/study3/protocol/interface_calibration_rendering_registry_v0_7.schema.json`

Update the active normative protocol:

* `studies/study3/protocol/interface_calibration_protocol_draft.json`
* `studies/study3/protocol/interface_calibration_protocol_draft.md`
* `studies/study3/protocol/interface_calibration_protocol.schema.json`

Update or add, as required:

* deterministic design-statistics derivations and generated tables;
* machine-readable decision tables and state transitions;
* recursive-manifest specification, generator and validators;
* active Study 3 routing/status documents;
* focused-review input packet without a review verdict;
* v0.7-specific tests and mutation tests.

Earlier registries, amendments, reviews, authorities and execution evidence are immutable. Active routing files may be updated prospectively but must not rewrite historical outcomes.

The JSON protocol is normative. Markdown must agree with every decision-bearing JSON field.

---

## 6. Binding v0.7 scientific and governance decisions

### 6.1 Dual estimands and claim ceiling

Register two distinct estimands:

#### E0 — primary

`E0_zero_generated_reasoning_token_expressed_competence`

Meaning: the model actually emits a correct registered answer surface without emitting generated reasoning/rationale tokens.

E0 is:

* the headline expressed-competence endpoint;
* the primary behavioral endpoint;
* the expressed-competence component of Q0;
* the primary gate for RP-B.

E0 does **not** establish absence of internal computation. For multi-token answers, answer-token autoregression is explicitly part of the estimand. Never describe E0 as “one forward pass,” “no intermediate computation,” or proof that reasoning was absent.

#### D0 — secondary conditional mechanism claim

`D0_single_forward_decodability`

Permitted claim only:

> Under the frozen counterfactual readout, discriminant information was decodable from one registered logit read.

D0:

* covers only the registered discriminant, not necessarily the complete answer;
* does not establish natural expression, behavioral competence or causal use;
* does not enter Q0 or the RP-B gate;
* is reported separately from E0.

The phrase “single forward” may appear only in this explicitly conditional D0 context.

### 6.2 E0 answer and decoding contract

Freeze before any model result:

* every legal answer surface per item;
* normalization policy;
* complete token-ID sequence per legal surface and checkpoint revision;
* EOS and stop semantics;
* parser implementation and hash;
* invalid-output treatment;
* complete decoding configuration.

E0 must use full-sequence exact match, never prefix match.

Outputs such as `7 because...` are incorrect unless the complete emitted sequence is itself a frozen legal surface. Unparseable or out-of-domain output is incorrect and may never be dropped.

Freeze `do_sample=false` as the actual deterministic switch. Sampling-only parameters must either be omitted or explicitly recorded as inactive; temperature alone must never be treated as the switch. Freeze batch size, padding side, EOS IDs, stopping criteria and `max_new_tokens`, including a numeric EOS margin.

Define exact reproducibility operationally. Do not leave “exact” to operator interpretation.

### 6.3 Full-context tokenization and D0 diagnostics

All tokenization eligibility and scoring proofs must use the actual complete context:

`rendered_prompt_bytes + candidate_surface_bytes`

Do not infer full-context tokenization from candidate-only encoding.

For every candidate and checkpoint revision, verify:

* bytes;
* complete token IDs;
* common prefix;
* discriminant position;
* reconstruction/round-trip requirements;
* equality between the IDs actually supplied to scoring and the independently computed full-string encoding.

Pre-register and always report, descriptively:

* restricted accuracy;
* full-vocabulary answer-set probability mass;
* complete candidate joint log-likelihood;
* full-vocabulary rank;
* short-generation/E0 validity.

Do not introduce an uncalibrated probability-mass threshold. These diagnostics cannot rescue a failed E0 gate.

### 6.4 Registered I1a/I1b/I2 battery

Retain the existing competence-floor structure. Do not replace it with a new MDE.

The registered component logic remains an exact one-sided binomial test against `p <= 0.90`, with the existing per-component alpha allocation of `1/600` per applicable atomic development cell unless a purely mechanical contradiction is demonstrated.

Recalculate and validate all affected cell counts, operation projections, multiplicity allocations, sample sizes and pass counts. A change to the scientific null, competence floor or existing floor-test meaning is outside this amendment and requires terminal operator decision.

### 6.5 Wrapper-only matched contrast

Within each role, compare:

* a registered common raw wrapper;
* that role’s registered canonical wrapper.

For RL, which lacks a canonical chat template, register a deterministic few-shot completion-format wrapper. Do not pretend that “chat versus raw” is the same intervention across roles.

The gate is joint adequacy:

* raw rendering meets its competence floor; and
* role-canonical rendering meets its competence floor.

Do not register a template-effect, equivalence or invariance claim.

Prohibited result wording includes:

* “robust to prompt format”;
* “template-independent”;
* “format-insensitive”;
* equivalent Chinese wording.

The only permitted positive wording is that both registered renderings met their competence floors.

Always report paired discordance and risk difference descriptively, irrespective of magnitude or direction. Freeze a numeric descriptive bandwidth and a fixed limitation paragraph triggered when the bandwidth is exceeded. The trigger has no gate effect.

### 6.6 Canonical generated-CoT ceiling

Add a canonical generated-CoT ceiling as a separate execution-precondition gate, not an interface selector and not S4.

S4 remains a short answer-only generation diagnostic with its existing token bound and is never selectable.

For the generated-CoT ceiling, freeze:

* exact canonical route and wrapper;
* whether `<think>` or another route marker is required;
* `do_sample`, temperature, top-p and all other generation parameters;
* item-level sample count `k`;
* seed policy;
* maximum generation length;
* batch size and padding side;
* parser and answer extraction;
* item-level aggregation;
* numeric accuracy threshold `theta`;
* checkpoint/family decision granularity;
* exact scope of a failure;
* inferential unit and reproducibility tolerance.

The ceiling parser and E0 parser are separate registered objects. Unparseable output is incorrect; dropping is prohibited.

The statistical unit is the item. `n × k` responses may never be treated as independent items.

If `k > 1`, select exactly one estimand before data:

* per-item mean correctness estimating pass@1; or
* majority-vote@k, explicitly identified as a self-consistency ceiling.

Do not leave both available at execution time.

Failure must yield:

`NO_CANONICAL_TASK_HEADROOM_FOR_TARGET_ROUTE`

A pass establishes only generated-CoT task competence. A pass or failure says nothing by itself about zero-generated-reasoning-token competence and cannot select an interface.

### 6.7 Q0 and RP-B

Q0 is a one-way prequalification layer:

* pass is interpretable;
* failure is not evidence that the interface is invalid or that the construct does not exist.

Q0 must contain an E0 expressed-competence component. D0 alone can never qualify a candidate.

Register the natural RP-B ladder before observing any Q0 development result. Its order must be determined by predeclared observable metadata, such as parameter count ascending with publication time as tie-break. Result-informed ordering is prohibited.

Prioritize same-tokenizer natural candidates, including the predeclared Qwen-family size ladder where eligible. Training-constructed implicit-CoT/direct-answer models may appear only as a separately identified fallback stratum with the lower claim ceiling “the isomorphic interface construction is valid,” not “the exact RT byte interface is valid.”

Require:

* physically and logically item-disjoint Q0 development and confirmation sets;
* confirmation set frozen before development access;
* one confirmation attempt per candidate;
* no tuning or rerun after confirmation failure;
* first-confirmed-pass selection;
* scan stops immediately after the first confirmed pass.

Because the scan continues past failures, classical fixed-sequence protection does not apply. Use the full predeclared ladder length `L` in the candidate-level Bonferroni allocation regardless of how many candidates are actually visited. Preserve any within-candidate component multiplicity allocation separately.

If no candidate qualifies, the terminal state is exactly:

`NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_THE_REGISTERED_LADDER`

Its claim ceiling is restricted to the registered family, size range, checkpoint revisions and interface set. No universal statement about all checkpoints or all restricted-logit interfaces is permitted.

### 6.8 RP-B versus RP-M

Register two separate positive-reference constructs:

* `RP-B`: a behavioral reference for expressed competence and interface readout;
* `RP-M`: a ground-truth mechanism/method reference for patching validation, such as a registered synthetic or circuit-known model.

Never combine them into one gate or one claim.

RP-M is not required to share RT’s tokenizer because it validates intervention methodology rather than the frozen behavioral interface. RP-B transfer claims remain subject to tokenizer/interface equivalence.

### 6.9 Per-checkpoint functional equivalence

Do not infer tokenizer equivalence from model names.

For every immutable checkpoint revision and every registered candidate surface, require equality of:

* bytes;
* token IDs in full context;
* common prefix;
* discriminant position.

File hashes are provenance; the four-part functional test is the decision criterion.

A checkpoint failing any equality is an `isomorphic_reinstantiation` and must be analyzed as a separate stratum. It may not be pooled with checkpoints described as sharing the exact frozen interface.

Runtime checkpoint revisions may be populated only by a later pre-execution seal under a deterministic registered procedure. Intentional deferral must be represented as an explicit fail-closed state, not `TBD`.

### 6.10 Engineering shakedown authority

Define a future engineering-shakedown authority that is disjoint from formal calibration authority.

It may allow recorded fix-and-rerun only within a sealed whitelist, including narrowly defined:

* environment and dependency defects;
* container/runtime launch defects;
* I/O and path defects;
* crashes before decision-bearing output;
* logging, receipt or manifest completeness defects;
* renderer/tokenizer/scorer mechanical defects detected by registered fixtures;
* trivial-copy and negative-control pipeline checks.

Freeze exact numeric limits for:

* maximum attempts/cycles;
* maximum wall-clock duration;
* maximum CPU/GPU resource consumption;
* maximum cloud-job count, if future shakedown authority permits cloud use.

Changes to an estimand, interface, threshold, item bank, answer surface, candidate ladder, task definition or gate logic are outside shakedown authority. Such a discovery produces:

`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`

Register a quantitative negative-control upper-bound/equivalence rule. “Not significantly above chance” is not an equivalence demonstration.

Do not run the shakedown in this authoring session.

### 6.11 Recursive-manifest seal

Replace informal seal lists with a recursive-manifest definition covering all decision-bearing bytes, including:

* image digest;
* immutable checkpoint revisions;
* tokenizer files;
* renderer/wrapper registry;
* task banks;
* readout and parser code;
* thresholds and decision tables;
* analysis code;
* decoding configuration;
* manifests and provenance records required by the registered construction.

Seal both inclusion rules/path globs and the explicit exclusion list.

The manifest-generation script must itself be included and hashed. Define a non-self-referential construction: do not require a manifest file or terminal root record to contain its own hash as a fixed point. Explicitly register generated-output exclusions or a valid two-level construction.

Write the final root hash into the applicable future terminal record.

### 6.12 Activation and causal-claim boundary

Activation collection, J-lens fitting, patching, ablation and mechanism inference remain unauthorized until all applicable conditions pass, including:

* software/mechanical integrity;
* engineering shakedown exit;
* generated-CoT headroom where applicable;
* E0 behavioral competence;
* registered interface floors;
* wrapper joint adequacy;
* RP-B qualification or its registered bounded terminal outcome;
* RP-M method validation before natural-model patch claims.

Checkpoint differences may be described only as checkpoint-level associations. “Distillation caused the mechanism” requires a separate future design with matched training interventions and independent seeds.

---

## 7. Numerical and semantic closure

The published v0.7 candidate must contain no decision-bearing:

* `TBD`;
* “for example”;
* “such as” where the executor must choose;
* unresolved alternative;
* unspecified threshold;
* unspecified denominator;
* unspecified parser behavior;
* unspecified retry;
* unspecified tolerance;
* operator-discretion clause.

Before publication, freeze or deterministically defer every value required for execution, including:

* all sample sizes and pass counts;
* all alpha allocations and family definitions;
* generated-CoT `theta`;
* `k` and aggregation;
* ladder length `L` and complete ordering rule;
* negative-control equivalence margin;
* wrapper descriptive bandwidth;
* reproducibility criteria;
* decoding lengths and EOS margin;
* shakedown attempt, resource and time limits;
* stop-state transition for every outcome.

Use exact arithmetic and pre-data rationale. Runtime identities that legitimately cannot exist until a later seal must have a deterministic acquisition rule and a fail-closed absent-state; they must not remain informal placeholders.

If a value cannot be justified from the registered estimand, existing design constraints and deterministic calculations, stop for terminal operator decision rather than inventing a convenient number.

---

## 8. Validation requirements

Before publication, run CPU-only deterministic validation proving at minimum:

* JSON/schema validity;
* JSON/Markdown decision-marker agreement;
* complete gate and stop-state coverage;
* exactly one legal transition per complete outcome;
* no D0 path enters Q0 or RP-B;
* no generated-CoT or S4 result selects an interface;
* wrapper gate is joint adequacy, not an effect/equivalence claim;
* Q0 multiplicity uses full ladder length `L`;
* confirmation cannot be accessed or rerun after failure;
* E0 parser rejects prefixes, rationale suffixes, unparseable output and unregistered surfaces;
* full-context tokenization is required rather than candidate-only encoding;
* all diagnostic quantities are excluded from rescue paths;
* manifest inclusion and exclusion rules are complete and non-self-referential;
* all numeric constants are regenerated and agree with committed tables;
* prohibited active claim language is rejected by mutation tests;
* no historical authority or evidence artifact changed;
* all scientific/model/cloud operation counters remain zero;
* evidence ledger remains at `EV-0016`.

Do not publish a passing state with skipped, expected-failing or manually waived decision-bearing tests.

---

## 9. Publication and governance

All commits must be linear descendants of the authority commit. No merge commits, rebases, force-pushes or history rewriting.

This is one amendment version even if bounded derivation and validation commits are needed. Do not create v0.7.1, v0.8 or another amendment cycle.

On success, the only legal successor is a fresh-session, independent, single focused methods review by a party that did not draft v0.7.

That review may return only:

* freeze/accept under its registered acceptance state; or
* `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`.

It may not automatically draft v0.8.

---

## 10. Required final disclosure

Report:

* starting and final commit/tree;
* authority path, commit, blob, byte count, SHA-256 and newline properties;
* complete commit list and parent structure;
* every created or modified path;
* confirmation that historical P0 bytes were unchanged;
* the four P0-R2 governance audit exceptions;
* all frozen decision-bearing numeric constants in one table;
* validation commands and exact results;
* zero-operation counters;
* evidence-ledger tail;
* whether `origin/main` remained unchanged until each publication;
* final protocol state;
* research-question status;
* exact terminal state.

A successful disclosure must end with:

`STUDY3_V0_7_CONSOLIDATED_AMENDMENT_AUTHORED_AWAITING_SINGLE_FOCUSED_REVIEW`
