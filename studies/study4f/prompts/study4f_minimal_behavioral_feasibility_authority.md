You are the project-level operator responsible for:

1. auditing and, if necessary, completing the already-authorized Study 3R terminal closure; and then
2. authorizing, sealing and executing one bounded developmental behavioral-feasibility pilot named Study 4F.

Repository:

`https://github.com/Alanjiao1988/J-space-observation`

This is a fresh project-level operator decision outside Study 3R. It does not amend, repair or reactivate Study 3R.

# 0. Concurrency and fail-closed rule

Before doing anything:

* fetch `origin/main`;
* require a clean worktree;
* verify that no concurrent repository-writing session or unconsumed repository lock is active;
* re-fetch before every publication;
* if `origin/main` changes unexpectedly at any point, stop without merging or rebasing:

`STUDY4F_BLOCKED_ON_CONCURRENT_REPOSITORY_ADVANCE`

Never merge, rebase, squash, force-push or rewrite history.

# 1. Audit what the previous prompt actually executed

Known predecessor identities:

* Study 3R focused-review terminal commit:
  `08c01ff4753b98ad0f43843fc49c93fac68c89da`
* its tree:
  `0dbf9ab33c19606c12c84a985dfabb93131bc0aa`
* review disposition:
  `STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION`
* already published terminal-closure authority commit:
  `f3935293d29dac6df0277179ebcdf9f5778d304b`
* authority path:
  `studies/study3r/prompts/study3r_terminal_closure_authority.md`
* authority SHA-256:
  `5daf943cc1a236715e39c29013addfb3e1b34da54b98ffc4f385ea4ace5f3a99`
* authority Git blob:
  `4ffb72895562be28dbb2ad8d77b6c1cb7050502f`

Mechanically compare `08c01ff…` with fetched `origin/main` and produce a step matrix containing:

* terminal-closure authority published;
* authority committed alone first;
* terminal closure Markdown created;
* terminal closure JSON/schema created;
* authoritative `STATUS.json`/schema created;
* closure tests created and passed;
* Study 3R README terminal routing updated;
* full-suite differential completed;
* final closure disclosure published;
* final lifecycle state reached;
* model/scientific operation counters.

Recognized states:

## State A — authority only

If `origin/main == f393529…`, and the only change from `08c01ff…` is the authority path above:

* classify the previous prompt as `AUTHORITY_ONLY_PARTIALLY_EXECUTED`;
* do not recreate, edit or recommit the authority;
* resume sections 4–9 of that existing authority;
* create and validate its closure artifacts;
* finish its remaining strictly linear publications.

## State B — valid partial descendant

If `origin/main` is a strict linear descendant of `f393529…` but closure is incomplete:

* verify every intervening commit and changed path against the publication order and allowed paths in the existing authority;
* preserve valid completed steps;
* do not rewrite or duplicate them;
* continue only from the first missing step.

## State C — closure already complete

If a strict descendant already contains a valid lifecycle router with:

`STUDY3R_TERMINAL_CLOSURE_COMPLETE_RESEARCH_QUESTION_UNANSWERED`

verify all closure requirements and continue to §2 without recreating closure artifacts.

Any other state stops with:

`STUDY4F_RESTART_BLOCKED_ON_STUDY3R_CLOSURE_INTEGRITY`

The Study 3R closure must end with:

* `active_protocol = null`;
* every Study 3R execution/repair/amendment flag false;
* successor authorization by Study 3R false;
* evidence ledger still ending at `EV-0016`;
* no scientific result;
* no claim about the presence or absence of J-space.

Do not change any rejected Study 3R candidate or review byte.

# 2. Publish this fresh project-level authority alone

Only after Study 3R terminal closure is complete and published, save this prompt byte-for-byte as:

`studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md`

Commit it alone as the first Study 4F commit. Record:

* parent commit/tree;
* byte length;
* SHA-256;
* Git blob;
* resulting commit/tree.

Publish it before creating any Study 4F protocol, code, bank, seal, test or result.

This new project-level authority does not modify Study 3R’s terminal `STATUS.json`. Study 4F derives authority from this new file, not from Study 3R.

# 3. Study 4F question and claim boundary

Study 4F is a developmental, non-confirmatory behavioral-feasibility pilot.

Its sole question is:

> Under one frozen raw direct-answer interface, does at least one member of the registered natural Qwen-tokenizer ladder demonstrate generated-CoT task headroom and zero-generated-reasoning-token expressed competence separately on both D2 and D3, thereby providing a developmentally qualified natural positive-reference candidate for later confirmation?

Study 4F:

* does not test whether J-space exists;
* does not claim that J-space is observable or unobservable;
* does not make a mechanistic claim;
* does not run D0;
* does not read restricted logits;
* does not perform activation collection or patching;
* does not perform Study 3M work;
* does not add a scientific-evidence row to `paper/evidence_ledger.csv`;
* cannot produce a confirmed RP-B;
* may only identify `RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION`.

No open-ended methods-review cycle is authorized. Mechanical preflight either passes and execution proceeds, or the pilot stops.

# 4. Fixed checkpoints

Register these immutable identities:

| Role  | Repository                                  | Revision                                   |
| ----- | ------------------------------------------- | ------------------------------------------ |
| RT    | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| RP_B1 | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`   | `916b56a44061fd5cd7d6a8fb632557ed4f724f60` |
| RP_B2 | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`  | `1df8507178afcc1bef68cd8c393f61a886323761` |
| RP_B3 | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`  | `711ad2ea6aa40cfca18895e8aca02ab92df1a746` |

Ladder order is exactly:

`RP_B1 → RP_B2 → RP_B3`

Re-verify all immutable revisions, tokenizer/config hashes, legal answer surfaces and token IDs before execution.

Study 4F may copy verified bytes or algorithms into its own namespace with provenance, but must not dynamically treat any rejected Study 3R protocol or pointer as normative.

Model loading contract:

* `trust_remote_code = false`;
* unquantized weights;
* `torch_dtype = bfloat16`;
* no adapter;
* no CPU or disk offload;
* no `device_map="auto"`;
* one explicitly recorded accelerator device;
* `batch_size = 1`;
* evaluation mode;
* pinned container digest and exact versions of Python, CUDA, PyTorch, Transformers, Tokenizers and Safetensors;
* explicit attention implementation;
* deterministic algorithms enabled wherever supported.

Before weight acquisition, prove that one accelerator can hold the 32B checkpoint, maximum registered KV cache and a fixed safety reserve without offloading. If that route is unavailable, do not quantize or silently shard; stop with:

`STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`

# 5. Separate D2 and D3 banks

Mixed-family banks are prohibited.

Create exactly:

* `D2_DEVELOPMENT_BANK`: family `D2`, 104 unique eligible items;
* `D3_DEVELOPMENT_BANK`: family `D3`, 104 unique eligible items.

Requirements:

* no item may belong to both banks;
* canonical content hashes must prove cross-bank disjointness;
* answer labels A/B/C/D must each occur exactly 26 times in each 104-item bank;
* the deterministic first 60 items of each bank must contain exactly 15 instances of each answer label;
* no answer or answer-derived field may leak into the rendered prompt;
* the same sealed items are intentionally reused across checkpoints and routes;
* this reuse is paired repeated evaluation, not independent sampling;
* no confirmation bank exists in Study 4F.

Derive the bank seed deterministically from the Study 4F authority commit hash plus the literal bank ID. Freeze the derivation algorithm before bank realization.

First seal the protocol, generator and ordering rule. Only then realize and commit the two banks. No threshold, parser, interface or generator change is allowed after inspecting realized bank bytes.

If either bank cannot realize 104 eligible unique items, stop before model execution:

`STUDY4F_REGISTERED_BANK_CAPACITY_UNAVAILABLE`

# 6. Interfaces and parsers

## 6.1 E0 primary route

Register one primary route only:

`W1_RAW_DIRECT`

Copy the already verified raw-direct wrapper bytes into the Study 4F registry and bind their source hash. Do not use a chat template and do not add a forced `</think>` closure.

Legal answers are exactly the frozen one-token surfaces A/B/C/D at every registered tokenizer revision.

E0 generation contract:

* `do_sample = false`;
* `temperature = 1.0` as the explicitly frozen neutral value;
* `top_p = 1.0`;
* `top_k = 0`;
* `num_beams = 1`;
* `num_return_sequences = 1`;
* `repetition_penalty = 1.0`;
* `length_penalty = 1.0`;
* `early_stopping = false`;
* `use_cache = true`;
* `batch_size = 1`;
* no padding;
* exact EOS/PAD/BOS IDs frozen per checkpoint;
* `max_new_tokens = 2`: one answer token plus one EOS opportunity.

E0 is correct only if the generated continuation is exactly:

`[one registered answer token, registered EOS]`

No prefix matching, whitespace normalization, textual reparsing or post-hoc surface addition is permitted. Missing EOS, any extra non-EOS token and all unparseable outputs are incorrect.

## 6.2 Generated-CoT headroom route

Register:

`C1_LONG_GENERATED_COT_HEADROOM`

Copy the verified canonical generated-CoT wrapper bytes into Study 4F and bind their provenance. This route is a headroom precondition only and never selects an interface.

Freeze all runtime fields, including:

* `do_sample = true`;
* `temperature = 0.6`;
* `top_p = 0.95`;
* `top_k = 0`;
* `num_beams = 1`;
* `num_return_sequences = 1`;
* `k = 1`;
* aggregation = per-item exact correctness;
* `repetition_penalty = 1.0`;
* `length_penalty = 1.0`;
* `early_stopping = false`;
* `use_cache = true`;
* `max_new_tokens = 4096`;
* `batch_size = 1`;
* no padding;
* exact stop-token IDs;
* exact dtype, device and attention implementation;
* pinned libraries and container;
* per-item seed semantics.

Derive each sampling seed from the sealed study identity, checkpoint role, depth and item ID. Record seeds before generation.

Require every prompt length plus 4096 generated tokens to fit the checkpoint’s registered context window.

The final non-empty generated line must exactly match:

`FINAL: A`, `FINAL: B`, `FINAL: C`, or `FINAL: D`.

Anything else is incorrect. Unparseable responses are never dropped.

# 7. Frozen statistical gates

Statistical unit: item.

Maximum registered gate cells:

* four checkpoints × two depths × CoT = 8;
* four checkpoints × two depths × E0 = 8;
* total `m_max = 16`.

Freeze:

* global familywise alpha = `1/20`;
* Bonferroni over all 16 cells regardless of how many are reached;
* per-cell alpha = `1/320`;
* target power = `9/10`;
* exact one-sided integer binomial tests only.

CoT cell:

* null competence floor `p ≤ 3/4`;
* design alternative `p = 9/10`;
* `n = 104`;
* pass iff correct count `≥ 90`.

E0 cell:

* null competence floor `p ≤ 1/2`;
* design alternative `p = 3/4`;
* `n = 60`;
* pass iff correct count `≥ 41`.

Independently recompute and test the exact sizes, powers and minimality of both `(n, boundary)` pairs without importing the production statistics implementation.

D2 and D3 are always separate cells. They may never be pooled for a gate, headline or ladder transition.

# 8. Candidate-local execution state machine

For each candidate in fixed order RP_B1, RP_B2, RP_B3:

1. Run its CoT D2 cell.
2. Run its CoT D3 cell.
3. If either CoT cell fails, mark only that candidate unqualified and continue to the next candidate.
4. If both CoT cells pass, run its E0 D2 and E0 D3 cells.
5. If either E0 cell fails, mark only that candidate unqualified and continue.
6. If both E0 cells pass, freeze that checkpoint as:
   `RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION`
   and stop the ladder.

A failure by RP_B1 must never block RP_B2 or RP_B3. Exhaustively test the state machine over all candidate-level pass/fail combinations before execution.

If no candidate passes:

`STUDY4F_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER`

In that state:

* do not run RT;
* do not introduce an unregistered model;
* do not conclude that no positive reference exists generally;
* do not conclude that the interface or J-space is globally unobservable.

# 9. RT developmental route

Only after a developmental positive-reference candidate is identified:

1. Run RT CoT D2 and D3 separately.
2. If either fails, stop:
   `STUDY4F_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM`
3. If both pass, run RT E0 D2 and D3 separately.

If either RT E0 cell fails:

`STUDY4F_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED`

If both RT E0 cells pass:

`STUDY4F_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION`

Even the successful state is developmental only. It does not authorize D0, activation patching, a paper claim or automatic confirmation.

# 10. Engineering shakedown and seal

Before study-bank execution, run a disjoint engineering shakedown using synthetic non-study fixtures.

It may test:

* environment and dependency availability;
* checkpoint download and checksum;
* unquantized load/unload;
* memory fit;
* renderer/parser I/O;
* logging and artifact recovery;
* deterministic seed plumbing;
* stub-result state-machine routing.

It may not inspect D2/D3 study-bank model outputs or change:

* estimands;
* checkpoints;
* checkpoint order;
* task definitions;
* bank sizes or ordering;
* prompt bytes;
* parsers;
* decoding fields;
* thresholds;
* alpha;
* pass boundaries;
* claim language.

White-listed fixes are limited to environment, dependencies, paths, serialization, crashes, logging and recovery. Maximum:

* three complete shakedown attempts;
* six accelerator-hours total.

Any non-white-listed defect stops with:

`STUDY4F_TERMINAL_OPERATOR_DECISION_REQUIRED`

After shakedown passes:

* freeze the final container digest;
* freeze code/config hashes;
* realize and commit the banks;
* create an execution seal binding all decision-bearing bytes;
* record the final Git commit/tree;
* set Study 4F developmental execution authorization true only for that seal.

After the first study-bank model call, no byte may change. Runtime failure then terminates the pilot; it does not reopen shakedown.

# 11. Required mechanical validation

Before model execution, require all of the following:

* separate D2/D3 banks and exact allocation;
* answer-label balance at n=104 and deterministic n=60 prefixes;
* no cross-depth duplicate content hash;
* exact tokenizer surface verification at all four revisions;
* full decoding contract with no inherited unspecified field;
* candidate-local ladder simulation over every pass/fail pattern;
* exact independent statistical recalculation;
* E0 and CoT parser mutation tests;
* the seven coordinated mutation patterns reported by the Study 3R review are either killed or rendered structurally inapplicable and tested as such;
* no bare or weak schema for a decision-bearing value;
* complete inclusion/exclusion inventory for the execution seal;
* candidate, review, historical and Study 3R closure bytes unchanged;
* the eight registered standing repository failure node IDs unchanged;
* zero new failure node IDs and zero collection errors.

A preflight failure cannot be repaired by changing a decision-bearing value. It stops with:

`STUDY4F_PREFLIGHT_FAILED_NO_MODEL_EXECUTION`

# 12. Publication and execution order

Use a strictly linear history:

1. complete and publish the remaining Study 3R closure commits under the existing authority, if required;
2. publish this Study 4F authority alone;
3. publish Study 4F protocol, schemas, generators, parsers, state machine, statistics and tests;
4. run bounded engineering shakedown and publish its disposition;
5. publish realized banks and the final execution seal before any study-bank model call;
6. execute the candidate-local ladder;
7. conditionally execute RT only if authorized by the ladder result;
8. publish raw immutable outputs, receipts, counters, results and final disclosure.

Re-fetch `origin/main` before every push. Use fast-forward publication only.

Do not run GitHub Actions unless a separately existing authority explicitly requires it.

# 13. Reporting and claim discipline

Report, for every executed cell:

* checkpoint and immutable revision;
* depth;
* route;
* bank and item count;
* correct, incorrect and unparseable counts;
* exact binomial tail;
* pass/fail;
* parser-validity rate;
* output-label distribution;
* generated-token count and accelerator time;
* container, code, bank and seal hashes.

Also report:

* the predecessor-execution audit matrix;
* whether the previous prompt was authority-only, partially completed or complete;
* the Study 3R final closure commit/tree;
* all Study 4F commits and paths;
* shakedown attempts and permitted fixes;
* weight/download/load/generation/GPU counters;
* skipped cells and the registered reason;
* evidence-ledger hash and unchanged tail `EV-0016`;
* confirmation that D0, logit readout, activation capture and patching counts are zero.

Prohibited conclusions include:

* “J-space does not exist”;
* “J-space is unobservable”;
* “the model cannot reason internally”;
* “single-forward reasoning was demonstrated”;
* “RP-B was confirmed”;
* “the result generalizes beyond the registered checkpoints, depths and interface.”

The final disclosure must end in exactly one registered Study 4F state and explicitly state what that state does and does not establish.
