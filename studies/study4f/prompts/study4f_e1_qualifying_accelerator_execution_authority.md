You are the project-level operator responsible for one resource-only execution successor to the already published Study 4F instrument.

Repository:

`https://github.com/Alanjiao1988/J-space-observation`

Successor name:

`Study 4F-E1 — Qualifying Accelerator Execution`

This authority supplies a qualifying Azure accelerator and executes the existing Study 4F instrument unchanged. It does not amend, repair, redesign or reinterpret Study 4F or Study 3R.

# 0. Binding starting state

Fetch `origin/main` and require:

* commit:
  `5fd9602df207e95789263d0f8d52428540f48fb8`
* clean worktree;
* strictly linear ancestry;
* zero concurrent repository writer;
* Study 4F lifecycle state:
  `STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`;
* Study 4F terminal `STATUS.json` unchanged;
* Study 3R tree unchanged from its closure head;
* evidence ledger ending at `EV-0016`;
* zero previously executed Study 4F cells;
* zero bank realizations, weights, model calls, logit reads, activations and patches.

Reproduce the registered repository baseline:

`9 failed, 5,119 passed, 16 skipped`

Require the same nine failure node IDs, including the one disclosed immutable scope expiry.

If any starting identity differs, stop:

`STUDY4F_E1_BLOCKED_ON_STARTING_STATE_INTEGRITY`

If `origin/main` advances unexpectedly at any later point, stop without merging, rebasing or overwriting:

`STUDY4F_E1_BLOCKED_ON_CONCURRENT_REPOSITORY_ADVANCE`

# 1. Publish this authority alone

Save this prompt byte-for-byte as:

`studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md`

Commit and publish it alone as the first commit after `5fd9602…`.

Record:

* byte length;
* SHA-256;
* Git blob;
* parent commit/tree;
* authority commit/tree.

Do not create an Azure resource, execution artifact, bank, seal, launcher or report before the authority-only commit is published.

Use only additive successor paths under:

`studies/study4f/execution-e1/`

Do not modify:

* `studies/study4f/STATUS.json` or its schema;
* the original Study 4F authority;
* the Study 4F protocol, parsers, interfaces, generator, state machine, statistics or tests;
* any Study 3R byte;
* any historical study or paper byte;
* `paper/evidence_ledger.csv`;
* the nine existing failing tests.

`studies/study4f/execution-e1/STATUS.json` becomes the lifecycle router for this execution successor only.

# 2. Bind the existing instrument byte-exactly

Create a read-only predecessor manifest covering all decision-bearing Study 4F files at `5fd9602…`, including:

* `protocol/study4f_protocol_v1.json` and schema;
* task-bank generator and ordering logic;
* E0 and CoT renderers/parsers;
* statistical calculator;
* candidate-local state machine;
* checkpoint identities and tokenizer surfaces;
* semantic/mutation validators;
* original shakedown disposition;
* Study 4F tests.

Recompute every file hash and require exact agreement with `5fd9602…`.

Reconfirm, without modifying anything:

* D2 and D3 are separate;
* each planned bank has 104 items;
* `m_max = 16`;
* `alpha_per_cell = 1/320`;
* CoT gate is `n=104`, pass `≥90`;
* E0 gate is `n=60`, pass `≥41`;
* candidate order is 7B → 14B → 32B;
* candidate failures are local;
* RT is unreachable until a developmental positive-reference candidate qualifies;
* quantization, sharding, offload and model substitution are prohibited.

If any byte or semantic invariant differs, stop:

`STUDY4F_E1_INSTRUMENT_BINDING_FAILED`

# 3. Azure identity and read-only resource discovery

Use the already configured Azure CLI identity. Never request, print or commit credentials.

Record only non-sensitive provenance. Do not commit tenant IDs, subscription IDs, access tokens, SSH private keys, SAS tokens or secrets. Subscription identity may be represented by a salted hash and final four characters only.

Check:

* active subscription;
* applicable Azure Policy restrictions;
* regional total-vCPU quota;
* VM-family quota;
* SKU restrictions;
* availability zones;
* current deployment capacity where validation is supported.

Quota and capacity must be reported separately.

Use official Azure CLI mechanisms including:

* `az vm list-skus`;
* `az vm list-usage`;
* ARM deployment validation or equivalent non-creating validation.

Registered accelerator selection order:

1. `Standard_NC40ads_H100_v5`

   * exactly one H100 NVL GPU;
   * nominal GPU memory 94 GB;
   * 40 vCPUs.
2. `Standard_NC24ads_A100_v4`

   * exactly one A100 GPU;
   * nominal GPU memory 80 GB;
   * 24 vCPUs.

H100 must be attempted before A100. Within a SKU, consider only regions:

* permitted by the subscription and Azure Policy;
* returned for that SKU;
* without `NotAvailableForSubscription`;
* with sufficient total-regional and VM-family vCPU quota.

Order otherwise eligible regions lexicographically before any deployment result is observed.

T4, A10, V100, multi-GPU ND-series, Spot VMs and confidential-GPU substitutions are not eligible.

# 4. Quota and availability branches

## 4.1 No sufficient quota

If neither eligible SKU has sufficient quota, do not provision anything.

Where the authenticated Azure quota API supports a bounded noninteractive request, submit one minimal request for exactly one instance of the first eligible SKU/region:

* 40 family vCPUs for `Standard_NC40ads_H100_v5`; or
* 24 family vCPUs for `Standard_NC24ads_A100_v4`.

Do not request a larger quota.

Record the request ID and stop:

`STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL`

If quota submission cannot be performed safely, create an exact operator-facing quota request packet and stop in the same state.

## 4.2 Quota exists but capacity is unavailable

Permit at most four on-demand deployment attempts across the registered SKU/region order.

Each failed attempt must be recorded with:

* SKU;
* region/zone;
* Azure error code;
* whether failure was quota, policy, SKU restriction or capacity;
* confirmation that no model operation occurred.

Do not use Spot capacity.

If all registered attempts fail:

`STUDY4F_E1_QUALIFYING_ACCELERATOR_CAPACITY_UNAVAILABLE`

## 4.3 Qualifying resource found

Freeze the first successfully provisioned eligible SKU/region/zone before any model output is observed. All checkpoints must run on that same physical GPU class and execution environment.

Once frozen, the successor may not switch from H100 to A100 or between regions after the first study-bank call.

# 5. Dedicated and recoverable Azure deployment

Create a new dedicated resource group whose name is deterministically derived from the E1 authority commit. Never use or delete an existing resource group.

Tag every created resource with:

* `project=J-space-observation`;
* `study=study4f-e1`;
* `authority_commit`;
* creation timestamp;
* automatic expiry timestamp.

Provision:

* Linux VM;
* exactly one eligible GPU;
* sufficient OS/local storage for the four immutable checkpoints and artifacts;
* NVIDIA driver and container runtime;
* outbound access only as required for immutable checkpoint and container acquisition;
* no public service endpoint beyond the minimum management path;
* no persistent secret in source, cloud-init or logs.

Use an on-demand VM, not Spot.

All resource IDs and cleanup targets must be explicit. Never use globs or unresolved variables for deletion.

# 6. Runtime contract

Reuse the original Study 4F runtime contract exactly:

* immutable checkpoint revisions;
* `trust_remote_code=false`;
* unquantized BF16;
* no adapter;
* no CPU/disk offload;
* no model sharding;
* no `device_map="auto"`;
* batch size 1;
* original attention implementation;
* original E0 and CoT generation fields;
* original seeds and parsers;
* original context and KV-cache bounds.

Before loading a checkpoint, verify with `nvidia-smi` and the runtime API:

* exactly one eligible accelerator is visible;
* GPU model matches the frozen SKU;
* no unrelated process occupies material GPU memory;
* measured free device memory exceeds
  `69,502,926,848` bytes;
* BF16 is supported;
* driver, CUDA and framework compatibility tests pass.

A paper specification of 80/94 GB is not sufficient: measured runtime visibility and free memory must pass.

If the accelerator exists but the measured memory condition fails, stop without quantization or offload:

`STUDY4F_E1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT`

# 7. Consume only the remaining shakedown allowance

The original Study 4F consumed:

* shakedown attempts: 1 of 3;
* accelerator-hours: 0 of 6.

E1 may use at most:

* two additional complete shakedown attempts;
* six total accelerator-hours.

Use synthetic non-study fixtures only.

The shakedown may verify:

* all four immutable checkpoint downloads and hashes;
* load/unload;
* unquantized BF16 memory fit;
* renderer/parser I/O;
* deterministic seed plumbing;
* container recovery;
* create-only logging;
* result retrieval;
* state-machine routing using stub outcomes.

Do not realize D2/D3 banks or inspect study-task outputs during shakedown.

White-listed fixes are limited to:

* driver/container compatibility;
* dependency installation;
* paths and permissions;
* networking needed for public checkpoint acquisition;
* serialization;
* logging;
* crash recovery;
* Azure deployment mechanics.

The following may not change:

* checkpoint;
* revision;
* dtype;
* hardware-selection rule;
* task;
* bank;
* prompt;
* parser;
* decoding configuration;
* threshold;
* alpha;
* pass boundary;
* state transition;
* claim language.

If shakedown cannot pass within the remaining allowance:

`STUDY4F_E1_SHAKEDOWN_FAILED_NO_STUDY_BANK_EXECUTION`

# 8. Final seal before study execution

After shakedown passes:

1. freeze the exact container image digest;
2. freeze VM SKU, region, zone, GPU model and driver;
3. freeze framework/library versions;
4. freeze launcher and recovery code;
5. re-run the original Study 4F preflight;
6. realize the original D2 and D3 banks using the original Study 4F authority hash and original registered seed derivation—not the E1 authority hash;
7. verify all bank invariants and hashes;
8. create the E1 execution seal;
9. publish the bank bytes and seal before the first study-bank model call.

The seal must bind:

* E1 authority;
* predecessor instrument manifest;
* Git commit/tree;
* container digest;
* resource identity;
* runtime configuration;
* checkpoint revisions and downloaded weight hashes;
* tokenizer/config hashes;
* launcher, parser and scoring code;
* both realized banks;
* all seeds;
* output schema;
* recovery journal schema.

Developmental execution authorization remains false until this sealed commit is published.

# 9. Execute the original state machine exactly once

After publication of the seal, execute the existing Study 4F state machine without alteration.

For each candidate in order 7B → 14B → 32B:

1. CoT D2;
2. CoT D3;
3. if either fails, continue to the next candidate;
4. if both pass, E0 D2;
5. E0 D3;
6. if both pass, freeze it as:
   `RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION`
   and stop the ladder.

If no candidate qualifies, do not run RT.

If a candidate qualifies:

1. run RT CoT D2 and D3;
2. only if both pass, run RT E0 D2 and D3.

No cell may be repeated because its result is unfavorable. A process interruption may resume only through the sealed create-only item journal, without duplicating or replacing a completed item.

After the first study-bank call:

* no engineering fix is permitted;
* no hardware switch is permitted;
* no reseal is permitted;
* no parser or output reinterpretation is permitted.

# 10. Registered final states

End in exactly one of:

* `STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL`
* `STUDY4F_E1_QUALIFYING_ACCELERATOR_CAPACITY_UNAVAILABLE`
* `STUDY4F_E1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT`
* `STUDY4F_E1_SHAKEDOWN_FAILED_NO_STUDY_BANK_EXECUTION`
* `STUDY4F_E1_EXECUTION_INTERRUPTED_NO_REINTERPRETATION`
* `STUDY4F_E1_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER`
* `STUDY4F_E1_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM`
* `STUDY4F_E1_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED`
* `STUDY4F_E1_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION`

No state authorizes automatic confirmation, D0, activation capture, patching or Study 3M.

# 11. Tests and the known scope expiry

Run:

* original Study 4F tests;
* E1 resource and execution tests;
* schema validation;
* independent statistics reproduction;
* mutation tests;
* full repository suite.

Starting baseline is:

`9 failed, 5,119 passed, 16 skipped`

Prefer the same nine failure node IDs at the final head.

Do not edit or suppress any historical failure.

If an immutable HEAD-relative scope assertion expires only because additive E1 files were created inside `studies/study4f/`, it may be recorded only if all of the following are mechanically proved:

* the test module itself is byte-identical;
* it is solely a `git diff <historical commit> HEAD` scope predicate;
* no substantive protected byte moved;
* a successor invariant carries forward the original guarantee;
* there are zero new non-scope failures.

Otherwise stop:

`STUDY4F_E1_TEST_DIFFERENTIAL_FAILED`

# 12. Artifact recovery and Azure cleanup

Persist all raw outputs, journals, receipts, summaries and hashes in the repository before resource deletion.

Never commit:

* model weights;
* credentials;
* Azure tokens;
* SSH private keys;
* subscription or tenant identifiers in full;
* transient caches.

After artifacts are retrieved and independently hash-verified:

* deallocate the VM immediately;
* delete only the dedicated E1 resource group and its explicitly enumerated resources;
* verify that no E1 VM, disk, NIC, public IP or billable accelerator remains.

If artifact publication fails, deallocate the VM but retain the dedicated resource group until recovery; report its exact state rather than deleting the only copy.

# 13. Publication order

Use strictly linear fast-forward publication:

1. E1 authority alone;
2. Azure discovery/selection or quota disposition plus tested launcher;
3. shakedown disposition;
4. realized banks and execution seal;
5. raw execution artifacts and machine-readable results;
6. final disclosure and E1 status.

Skip steps that are unreachable under the registered terminal branch.

Re-fetch `origin/main` before every publication.

No GitHub Actions run, merge, rebase, squash, force-push or history rewrite.

# 14. Final disclosure

Report:

* starting/final commit and tree;
* full ancestry;
* authority identity and alone-first ordering;
* predecessor instrument hash verification;
* Azure SKU/region/zone selection evidence;
* quota versus capacity evidence;
* measured GPU identity and free memory;
* all created Azure resources and cleanup state;
* shakedown attempts and accelerator-hours;
* container and execution-seal identities;
* bank hashes and invariant checks;
* every reached and skipped cell;
* correct/incorrect/unparseable counts per cell;
* exact gate calculations;
* candidate-local transitions;
* raw-output and receipt hashes;
* full-suite differential;
* evidence-ledger unchanged at `EV-0016`;
* all D0/logit-read/activation/patching counters;
* exact final registered state;
* explicit scientific claim ceiling.

No result may be described as establishing that J-space exists, does not exist, is observable or is unobservable.
