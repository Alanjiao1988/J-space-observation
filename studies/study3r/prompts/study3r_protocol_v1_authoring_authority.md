You are the sole clean-room protocol author for Study 3R in:

`https://github.com/Alanjiao1988/J-space-observation`

This is the one authoring session authorized by the Study 3R charter. A different, independent party must perform the later focused methods review.

You may author and validate the protocol, resolve immutable checkpoint metadata, and perform strictly tokenizer-only qualification needed to freeze byte/token surfaces. You may not execute a model or produce scientific evidence.

## 0. Binding starting state

Expected starting `origin/main`:

* commit: `cd9c0af3118ca2f254bd0bbaa8eb2ee4dad6d1ed`
* tree: `fc303a001bbfea60149e9f425f64230c022b6d91`
* Study 3R state:
  `STUDY3R_CLEAN_ROOM_PROTOCOL_AUTHORIZED_AWAITING_SINGLE_AUTHORING_SESSION`

Binding authorities, in order:

1. This authoring authority.
2. `studies/study3r/study3r_charter.json`
3. `studies/study3r/CHARTER.md`
4. `studies/study3/reviews/v0_7_operator_terminal_decision.json`
5. The independent v0.7 review, used only as a defect checklist.

The rejected v0.7 protocol, builder, registry, schemas and tests are historical negative examples. You may inspect them to understand findings, but may not copy their structure, prose blocks, 40-key schema, state machine, generated code, sample-size tables or interface-profile architecture.

If the starting commit, tree, charter state or protected-byte identities differ, stop with:

`STUDY3R_PROTOCOL_AUTHORING_BLOCKED_ON_STARTING_STATE_INTEGRITY`

## 1. Authority-first ordering

Save this prompt byte-for-byte as:

`studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md`

Commit it alone as the first commit after `cd9c0af…`, record its byte length, SHA-256, Git blob and tree, and publish that authority-only commit before creating any tokenizer acquisition, protocol, analysis or test artifact.

No protocol content may exist before the authority-only commit.

## 2. Additional operator scope decision

Freeze the following study roles:

### Target checkpoint

`RT = deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`

RT is the sole target checkpoint in Study 3R.

### Natural positive-reference ladder

Fixed membership and order, `L = 3`:

1. `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`
2. `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`
3. `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`

No fallback, substitution, reordering or post-result expansion is permitted.

### Excluded roles

The former base/instruct lineage roles, including Qwen2.5-Math base and instruct checkpoints, are outside Study 3R. They may be considered only in a later separately authorized scientific comparison.

Study 3R must not recreate S1–S4 or select a winner from several interface profiles.

Register exactly:

* one E0 direct-answer expressed-competence interface, evaluated under two wrapper arms;
* one D0 counterfactual single-forward discriminant readout, diagnostic only;
* one separate canonical generated-CoT ceiling route.

## 3. Permitted acquisition operations

Before protocol freeze, resolve an immutable revision for RT and each of the three RP-B candidates from the authoritative model repository.

You may download only metadata and tokenizer-related files required for:

* immutable revision resolution;
* tokenizer/config hashes;
* special-token identities;
* chat-template recovery;
* legal answer-surface tokenization;
* wrapper rendering;
* bytes/token IDs/common prefix/discriminant-position comparison.

Use explicit allow-lists. Do not download `.safetensors`, `.bin`, `.pt`, adapters or model weights. Do not load a model, create a GPU/cloud job, perform prefill, forward, logit scoring or generation.

Use `trust_remote_code=false`. If a required tokenizer cannot be instantiated under that rule, fail closed; do not execute remote code.

Create a sealed acquisition record containing:

* repository ID;
* observation timestamp;
* immutable revision SHA;
* downloaded path allow-list;
* every acquired file hash;
* tokenizer class and library versions;
* network requests performed;
* proof that no weight file was acquired;
* tokenizer operation counters.

If any fixed checkpoint or required tokenizer artifact cannot be resolved, stop with:

`STUDY3R_PROTOCOL_AUTHORING_FAILED_CHECKPOINT_OR_TOKENIZER_UNRESOLVABLE`

No fallback model is allowed.

## 4. Clean-room scientific architecture

Author a minimal protocol whose purpose is behavioral and interface qualification only.

The state machine must implement this future execution order:

1. sealed engineering shakedown;
2. checkpoint/tokenizer functional-equivalence verification;
3. generated-CoT ceiling per checkpoint;
4. trivial recovery, explicit binding and single-primitive competence controls;
5. negative control;
6. two-wrapper joint adequacy;
7. RP-B ladder development and item-disjoint confirmation;
8. first-confirmed-pass RP-B freeze, or bounded no-qualified-reference terminal state;
9. RT E0 behavioral qualification;
10. D0 diagnostic reporting;
11. terminal Study 3R disposition.

Activation patching, RP-M and mechanism claims are absent and unauthorized.

Use unique gate and state identifiers. Do not reuse `Q0` for two constructs. Every state must have exhaustive, mutually exclusive transitions and a defined terminal outcome.

The no-qualified-reference state must be bounded to the registered ladder, revisions, task population and interfaces. It must not make a universal claim about all models or all restricted-logit interfaces.

## 5. Estimands and parsers

### E0 primary endpoint

`E0_zero_generated_reasoning_token_expressed_competence`

Freeze per checkpoint revision:

* all legal answer surfaces;
* normalized byte sequences;
* complete token-ID sequences;
* EOS and stopping semantics;
* `do_sample=false`;
* full-sequence exact match;
* no prefix matching;
* no rationale or extra emitted token;
* `max_new_tokens = longest legal answer surface for that checkpoint + registered termination margin`;
* unparseable output = incorrect.

Answer-set mass, full-vocabulary rank and complete candidate joint likelihood may be registered only as descriptive diagnostics and may not determine a gate.

### D0 diagnostic

`D0_single_forward_decodability`

Freeze its counterfactual surface, candidate set, common prefix, discriminant position, scoring rule and tie rule. State explicitly that it proves only conditional discriminant decodability and never natural expression, complete-answer competence or RP-B qualification.

### Generated-CoT ceiling

Freeze separately from E0:

* checkpoint granularity;
* exact task population and relation to the Study 3R bank;
* canonical CoT wrapper bytes;
* `k = 1`;
* item as statistical unit;
* parser;
* unparseable = incorrect;
* context-window calculation;
* per-item maximum generation bound;
* total token and compute upper bounds;
* numeric competence threshold;
* failure scope and terminal state.

Ceiling pass proves only generated-CoT task headroom. Pass or failure must not select an interface or prove no-CoT capability.

## 6. Wrappers and tokenizer strata

Freeze exact bytes for both E0 wrapper arms:

1. common raw/direct-answer wrapper;
2. checkpoint-revision-specific role-canonical direct-answer wrapper.

For each, register:

* message roles;
* system/user/assistant content;
* separators and newline bytes;
* BOS/EOS insertion;
* answer cue;
* few-shot examples, if any;
* tokenizer/chat-template revision;
* rendered bytes with deterministic placeholders;
* the exact field that differs between the matched arms.

The gate is joint adequacy: both arms must independently clear the competence floor. Do not claim template invariance or estimate a template effect.

Report paired discordance descriptively for every checkpoint and stratum, regardless of direction.

For every checkpoint and candidate surface, verify the tuple:

`(bytes, token IDs, common prefix, discriminant position)`

If any element differs, classify that checkpoint as an isomorphic re-instantiation stratum. Never pool it as the same frozen byte/token interface.

## 7. Task populations and sampling

Define clean-room generators for:

* trivial content recovery;
* explicit answer-label binding;
* single primitive operations;
* depth-2 and depth-3 compositional operations for RP-B qualification and RT behavioral measurement;
* a deliberately invalid or randomized negative-control condition.

Freeze:

* operation ontology;
* item eligibility;
* answer domains;
* label alphabets;
* rendering rules;
* duplicate and collision rules;
* all strata;
* statistical unit;
* development/confirmation split construction;
* item-disjointness enforcement;
* future seed-generation and commitment procedure;
* task-bank and ceiling-bank relationship.

Do not draw the execution seed or realize the scientific development/confirmation banks in this authoring session. Synthetic tokenizer fixtures used only to freeze surfaces must be clearly separated from scientific items.

## 8. Statistical closure

Independently enumerate every gate-bearing atomic cell from the registered factors. Both wrapper arms and all applicable checkpoint/ladder multiplicities must enter the census.

Do not reuse `m_max = 43`, any v0.7 sample size, threshold or alpha allocation without independently deriving it from the new Study 3R census.

For every gate, freeze:

* null and alternative;
* direction;
* statistical unit;
* chance or competence floor;
* effect/adequacy margin;
* global error budget;
* multiplicity family and allocation;
* development and confirmation alpha;
* power target;
* exact sample size;
* exact integer pass/fail boundary;
* minimality proof;
* stop rule;
* missing/unparseable treatment.

Use exact integer binomial arithmetic. Do not use normal approximations or floating-point comparisons to determine a gate.

The RP-B ladder scans past failures until the first confirmed pass. Do not claim classical fixed-sequence protection. Correct over the full fixed `L = 3`, regardless of where scanning stops. Each candidate receives at most one development evaluation and one item-disjoint confirmation evaluation.

The negative control must be executable as either:

* rejection of `H0: p ≥ registered upper margin`; or
* an exact one-sided upper confidence-bound rule.

Freeze its unit, chance level, margin, `n`, alpha, bound construction and multiplicity family. “Not significantly above chance” is prohibited as an equivalence argument.

Create:

* a production statistics generator;
* an independent stdlib-only recalculation that imports none of the production calculators;
* exact agreement tables;
* exhaustive proof that every registered `n` and integer pass boundary has the stated minimality property.

No `TBD`, deferred numeric constant, unresolved operator choice or null operation bound is permitted in the candidate.

## 9. Artifact architecture

Create a self-contained Study 3R bundle under `studies/study3r/`, including at minimum:

* `protocol/study3r_protocol_v1.json`
* `protocol/study3r_protocol_v1.schema.json`
* `protocol/study3r_protocol_v1.md`
* `protocol/study3r_rendering_registry_v1.json`
* `protocol/study3r_rendering_registry_v1.schema.json`
* `protocol/study3r_state_machine_v1.json`
* `protocol/study3r_state_machine_v1.schema.json`
* `protocol/study3r_protocol_current.json`
* `protocol/study3r_protocol_current.schema.json`
* `analysis/study3r_protocol_build.py`
* `analysis/study3r_design_statistics.py`
* `analysis/study3r_independent_recalculation.py`
* `analysis/study3r_tokenizer_probe.py`
* `analysis/study3r_manifest.py`
* acquisition, tokenizer-equivalence, census and statistical artifacts;
* one authoring disclosure in Markdown and machine-readable form;
* `tests/test_study3r_protocol_v1.py`.

There must be exactly one authoritative protocol and one unambiguous current pointer. No v0.5/v0.6/v0.7 runtime overlay or fallback is permitted.

Schemas must use restrictive types, enums/consts, required fields and `additionalProperties=false`. Empty `{}` schemas are prohibited for decision-bearing values.

The Markdown, JSON, registry, state machine, statistical tables and pointer must be mutually consistent.

## 10. Manifest and seal design

Use an explicitly acyclic sealing design. Do not make an impossible self-hash claim.

The seal must bind:

* protocol and schemas;
* current pointer;
* rendering registry;
* state machine;
* task-generator specifications;
* statistical code and independent recalculation;
* tokenizer acquisition/probe artifacts;
* wrapper bytes;
* thresholds and census;
* manifest generator itself;
* semantic and mutation tests;
* all other decision-bearing source files.

Seal exact inclusion rules and exclusions. Use the Git commit/tree as the outer recursive identity and a deterministic content manifest for path/blob/hash verification. Explain every self-exclusion.

The protocol remains `frozen=false` and `execution_authorized=false`; the manifest is a candidate reproducibility manifest, not an execution seal.

## 11. Semantic and mutation validation

Artifact-versus-generator byte reproduction is necessary but insufficient.

Add coordinated generator-mutation tests that edit the generator, rebuild the bundle, and require the semantic validation to reject at least these mutations:

* target checkpoint identity;
* RP-B membership, order or `L`;
* immutable revision;
* E0 legal surface or token IDs;
* E0 `max_new_tokens`;
* D0 discriminant position;
* wrapper bytes or role;
* gate alpha, `n`, floor or pass count;
* negative-control chance level or margin;
* CoT `k`, parser or resource bound;
* state transition;
* census wrapper factor;
* current authoritative path;
* execution authorization;
* manifest inclusion rule.

Every registered mutation must be killed. Report mutation count and survivor count; required survivors = 0.

## 12. Existing-suite baseline

At `cd9c0af…`, the registered baseline is:

`8 failed, 5,025 passed, 16 skipped`

The eight standing failures comprise the historical host-line-ending failures plus the scope-expired v0.7 focused-review invariant. Do not edit or suppress the rejected review artifact.

Run the full suite at the final authoring head and require:

* zero new failure node IDs;
* zero collection errors;
* all Study 3R protocol tests passing;
* all coordinated mutations killed.

If `tests/test_study2_stage_bd.py::test_pack_writes_the_core_manifest_last` alone flakes, rerun it twice in isolation and run its full module. It may be classified as the already disclosed filesystem-timestamp flake only if both isolated reruns and the module pass. Do not repair it in this authority.

Any other new failure is blocking.

## 13. Boundaries

Throughout this authoring session:

* no model weights, adapters or activations;
* no model load, prefill, forward, logit read, scoring or generation;
* no Azure/ACR/ACA/GPU job;
* no scientific task-bank realization;
* no RP-B selection;
* no evidence-ledger row;
* no scientific claim;
* no activation patching;
* no Study 3M artifact.

Tokenizer-only operations explicitly authorized above must be counted and disclosed separately.

`formal_execution_authorized` remains `false`.

## 14. Publication and terminal states

Use a strictly linear history:

1. authoring authority alone;
2. immutable-revision/tokenizer acquisition and probe artifacts;
3. protocol bundle, generators, statistics, schemas and tests;
4. authoring disclosure and Study 3R routing update.

Re-fetch `origin/main` before every publication. No merge, squash, rebase, force-push or history rewrite.

On successful validation, fast-forward `origin/main` to the final authoring commit and set:

`STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`

This state does not authorize freeze, task-bank realization or model execution.

If a scientifically necessary decision cannot be frozen, a fixed checkpoint cannot be resolved, the statistics cannot close, a coordinated mutation survives, or a new test failure remains, stop with:

`STUDY3R_PROTOCOL_AUTHORING_FAILED_TERMINAL_OPERATOR_DECISION_REQUIRED`

Do not start a second authoring session or draft an amendment.

## 15. Final disclosure

Report:

* starting and final commit/tree;
* exact linear ancestry;
* authority identity and ordering;
* resolved revisions and tokenizer-only acquisition counters;
* proof that no weight file was acquired;
* all bundle paths, byte lengths and hashes;
* target and ladder identities;
* E0/D0/CoT definitions;
* full atomic-cell census and derived `m_max`;
* all alpha, floor, margin, `n`, pass-count and power values;
* independent recalculation agreement;
* tokenizer equivalence/isomorphic strata;
* mutation list and survivor count;
* manifest/tree identity;
* focused and full-suite results;
* protected-byte comparison;
* evidence-ledger and execution-authorization state;
* all zero-operation counters;
* final `origin/main`.

Successful final state:

`STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`
