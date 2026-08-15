# Study 3 P0-R2 generation-2 infrastructure successor and conditional execution authority

You are the sole operator for a new, disjoint **Study 3 P0-R2 generation-2** execution. Work autonomously and make decisions mechanically from committed evidence. Do not ask the operator to choose routine implementation details. If an authority boundary, identity, Azure result, or one-shot state is false, ambiguous, unavailable, or underived, fail closed and publish the truthful stop state.

This prompt is the operator authority for both:

1. model-free generation-2 preparation, correction, validation, sealing, and readiness;
2. exactly one generation-2 live replay, followed only after a proved replay pass by exactly one bounded T4 pilot and one CPU recovery execution.

It does not reopen P0-R1 or P0-R2 generation 1.

## 1. Exact starting state

Repository:

* `Alanjiao1988/J-space-observation`
* required starting `origin/main`:
  `135f725baff7f5c9c1b0ae15ad5692bf77dd4fc5`
* required starting tree:
  `0469387f7198d82a189b7bac052a0007d770fec0`

Before changing anything:

1. run `git fetch origin --prune`;
2. require `HEAD == origin/main == 135f725baff7f5c9c1b0ae15ad5692bf77dd4fc5`;
3. require tree `0469387f7198d82a189b7bac052a0007d770fec0`;
4. require a clean worktree, including untracked files relevant to the repository;
5. verify that the current commit has exactly one parent,
   `3230978127d05c97965cd6bd14fa56f1a0292bc9`;
6. verify that `005aa087e40c641affc8ca537e6c6a075bcbfe98` is the merge base and that the current head is exactly 33 commits ahead;
7. verify the existing P0-R2 attempt ledger has 45 entries, 45 sealed, zero unavailable, and zero ambiguous.

The local worktree branch name is not an admission condition. A Copilot-generated branch is acceptable if its `HEAD` object equals `origin/main`. Publish using ordinary non-force `HEAD:main` fast-forwards only.

If `origin/main` has advanced, the tree differs, the worktree is dirty, or another session changes `origin/main` during this work, stop without rebasing, merging, force-pushing, or starting Azure work. Report the observed identities.

## 2. Terminal facts that must remain terminal

P0-R1 is permanently closed:

* stop commit:
  `30806d793872a50e581d3252382b4a0ec2af3889`;
* state: `STOP_NO_MODEL_OPERATION`;
* its replay envelope is consumed;
* no P0-R1 preflight, replay, retry, recovery retry, or pilot may run;
* no existing byte under either of these roots may change:

  * `studies/study3/pilot/p0_r1/`
  * `studies/study3/pilot/p0/results/p0-r1/`

P0-R2 generation 1 is also permanently closed:

* terminal closure head:
  `135f725baff7f5c9c1b0ae15ad5692bf77dd4fc5`;
* ready anchor used by its final invocation:
  `7ff6700621ca1db9bdf06d1d91a49e935e66e2b7`;
* image executable:
  `c9344c52bfbacc4f2a24010fffa534a940104140`;
* final generation-1 image digest:
  `sha256:eb0e284c6b420aa4992dcdee9a43b9cb92a96937499bca605f96b141619e9b58`;
* consumed attempt:
  `p0r2-g1-live-20260815-0800`;
* sole ACR run:
  `cmjv`;
* generation-1 live invocations: 1;
* generation-1 ACR run IDs: 1;
* generation-1 replay-gate invocations: 0;
* generation-1 recovered canonical artifacts: 0 of 4;
* generation-1 tokenizer/model/GPU/scoring counters: all zero;
* state: `STOP_NO_MODEL_OPERATION`.

The existing `P0_R2_HANDOFF_V2.md` contains a formerly valid “unconsumed” entry state that predates `cmjv`. It is now historical and non-executable. Do not execute its generation-1 preflight or live command.

Every file that already exists beneath `studies/study3/pilot/p0_r2/` or `studies/study3/pilot/p0/results/p0-r2/` at the starting head is frozen. Do not edit, replace, rename, normalize, delete, or regenerate any of those files. Generation 2 must be additive and disjoint.

## 3. First publication: this authority only

Save this prompt verbatim, with LF line endings and one trailing newline, as:

`studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md`

The first new commit must contain only that file. Before the commit, record:

* starting commit and tree;
* authority path;
* byte length;
* Git blob identity;
* SHA-256;
* LF/trailing-newline status.

Push that authority-only commit to `origin/main` by an ordinary non-force fast-forward before performing any new Azure operation.

No Azure query, build, canary, job operation, Blob operation, replay, tokenizer, model, or GPU operation is permitted before this authority commit is published.

Bind the authority’s exact committed bytes in every later generation-2 lock and closure proof.

## 4. Fixed Azure and namespace identities

Use the existing registered Azure estate:

* subscription:
  `943bacdf-8b6e-4e3a-8126-a149f623d32e`
* resource group:
  `rg-jspace-observation-sea`
* registry:
  `acrjspaceobssea0708231738`
* storage account:
  `stjspacefiles0709085305`
* results container:
  `jspace-results`
* Container Apps environment:
  `cae-jspace-observation-sea-vnet2`

Generation-2 identities must be disjoint:

* live attempts begin `p0r2-g2-live-`;
* pilot attempts begin `p0r2-g2-pilot-`;
* canary attempts begin `p0r2-g2-canary-`;
* Blob prefixes begin `study3/p0_r2/g2/`;
* bounded GPU job:
  `job-jspace-s3-p0r2-pilot-g2`;
* CPU recovery job:
  `job-jspace-s3-p0r2-recover-g2`;
* in-VNet prefix-proof job:
  `job-jspace-s3-p0r2-prefix-g2`;
* hard-kill canary job:
  `job-jspace-s3-p0r2-hardkill-g2`;
* generation-2 results:
  `studies/study3/pilot/p0/results/p0-r2-g2/`.

Select the exact live and pilot attempt IDs once during Segment A, before sealing the lock. Record them in the lock and never substitute another attempt.

Do not reuse any generation-1 attempt, prefix, job, artifact, receipt, run ID, envelope, or claimed absence.

## 5. Scientific invariants

Generation 2 changes infrastructure only. It must reuse the exact scientific bytes and registered scientific semantics inherited by P0-R2 generation 1 from P0-R1 generation 3.

Do not change:

* corpus, manifests, item selection, cells, assignments, RT/RL/RI;
* tokenizer or checkpoint identity;
* prompt or answer semantics;
* activation/interface definitions;
* replay factorization logic;
* smoke-extension rule;
* scoring or exclusion rules;
* scientific artifact schemas except for additive generation identity and disjoint storage paths;
* bounded pilot maxima.

The generation-2 lock must bind every reused scientific Git blob and SHA-256 and prove equality with the registered generation-1/P0-R1 scientific closure before importing or executing it.

Permanent research-governance state remains:

* `formal_execution_authorized = false`;
* draft v0.6 remains unreviewed and unfrozen;
* interface selection remains `null`;
* positive-reference selection remains `null`;
* RP wrapper remains `null`;
* evidence-ledger tail remains `EV-0016`;
* the research question remains unanswered;
* no evidence-ledger row may be added in this authority.

## 6. Segment A: additive generation-2 correction

Segment A is completely model-free.

Forbidden throughout Segment A:

* tokenizer construction or encoding;
* checkpoint access, download, or load;
* model-weight load;
* prefill or generation;
* scoring;
* GPU allocation or GPU workload;
* replay-gate invocation;
* evidence-ledger mutation.

All Segment-A receipts must carry explicit zero counters for these operations.

### 6.1 Required additive generation-2 assets

Create additive generation-2 assets rather than editing v1 or v2 files. Use these exact names unless an existing immutable shared primitive can be imported byte-for-byte:

* `studies/study3/pilot/p0_r2/p0_r2_execution_lock_g2.py`
* `studies/study3/pilot/p0_r2/p0_r2_execution_lock_g2.json`
* `studies/study3/pilot/p0_r2/p0_r2_execution_lock_g2.schema.json`
* `studies/study3/pilot/p0_r2/p0_r2_closure_binding_g2.py`
* `studies/study3/pilot/p0_r2/p0_r2_host_preflight_g2.py`
* `studies/study3/pilot/p0_r2/p0_r2_prefix_proof_g2.py`
* `studies/study3/pilot/p0_r2/p0_r2_host_submission_g2.py`
* `studies/study3/pilot/p0_r2/p0_r2_image_manifest_g2.py`
* `studies/study3/pilot/p0_r2/p0_r2_image_manifest_g2.json`
* `studies/study3/pilot/p0_r2/p0_r2_attempt_ledger_g2.json`
* `studies/study3/pilot/p0_r2/P0_R2_HANDOFF_G2.md`
* `studies/study3/pilot/p0_r2/container/Dockerfile.study3-p0-r2-g2`
* `studies/study3/pilot/p0_r2/container/p0_r2_acr_task_g2.yaml`
* `studies/study3/pilot/p0_r2/container/p0_r2_replay_g2.sh`
* `studies/study3/pilot/p0_r2/container/p0_r2_canary_g2.sh`
* `studies/study3/pilot/p0_r2/container/p0_r2_model_pilot_g2.sh`
* `studies/study3/pilot/p0_r2/container/p0_r2_recovery_g2.sh`
* `studies/study3/pilot/p0_r2/container/p0_r2_pilot_job_g2.yaml`
* `studies/study3/pilot/p0_r2/container/p0_r2_recovery_job_g2.yaml`
* `studies/study3/pilot/p0_r2/container/p0_r2_prefix_job_g2.yaml`
* `studies/study3/pilot/p0_r2/container/p0_r2_hard_kill_job_g2.yaml`
* additive generation-2 tests and machine-readable canary/validation receipts.

All new text files must be LF-only. Do not repair the eight protected P0-R1 CRLF files.

### 6.2 Exact correction to the generation-1 fatal defect

The generation-1 live path failed because an ACR Tasks agent has neither the managed identity nor VNet reachability needed to list a private Storage account.

Generation 2 must implement this design:

1. A CPU-only Container Apps execution inside
   `cae-jspace-observation-sea-vnet2`, using the registered managed identity,
   performs the exact prefix listing.
2. It emits a machine-readable prefix-proof receipt.
3. The host verifies the receipt against the Azure control plane and the
   captured execution log.
4. The host embeds the exact receipt bytes and SHA-256 in the two-file ACR
   context admission.
5. The ACR live container validates the bound receipt and prints
   `P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1`.
6. The ACR live container must not attempt a managed-identity token request,
   Storage listing, private endpoint connection, or any substitute network
   proof before the replay gate.

This is not permission to bypass the prefix proof. The live path must refuse if the receipt is missing, malformed, stale at host submission time, ambiguous, for another generation/attempt/prefix/account/container, reports anything other than a successful zero-object listing, or cannot be correlated with a successful in-VNet execution.

The prefix receipt must contain at least:

* schema version;
* stage and generation;
* exact attempt ID;
* exact complete Blob prefix;
* subscription, resource group, account and container;
* Container Apps environment;
* prefix-proof job and execution identity;
* image digest used by the proof job;
* start, observation and completion timestamps in UTC;
* listing success;
* `object_count = 0`;
* `wrote_any_object = false`;
* public-network/default-action observations where available;
* stdout/stderr byte lengths and SHA-256;
* all-zero tokenizer/model/GPU/scoring counters.

There must be no `--allow-path`, `--skip-proof`, `--force`, caller-supplied truth value, environment-only bypass, or fallback that converts an error into absence.

Host submission must require the prefix observation to be no more than 15 minutes old when the Azure CLI live process is started. The ACR container must verify identity and byte binding but must not reject solely because Azure queue time makes the receipt older after submission.

### 6.3 Eliminate branch asymmetry

Do not implement separate canary and live versions of prefix-receipt validation.

Create one shared validation implementation used by both modes. Tests must prove:

* canary and live call the same implementation;
* the implementation accepts a valid, byte-bound receipt;
* it rejects missing, changed, stale-at-host, occupied, mismatched, ambiguous, duplicate, or incorrectly hashed receipts;
* live mode performs no private Storage call before the gate;
* a credential-less and network-isolated test container can pass admission with a valid receipt;
* it cannot pass without that receipt;
* no string-only or mocked-success assertion substitutes for executed behavior.

### 6.4 Mandatory new image

Because an image-bound live entry point changes, generation 2 must build and publish a new image. Do not reuse the generation-1 digest as the generation-2 execution image.

The image must:

* remain digest-pinned;
* retain the exact registered P0-R1 generation-3 base image unless a documented security/availability blocker makes that impossible;
* contain the additive generation-2 operational assets;
* contain the exact reused scientific bytes;
* run as the registered non-root user;
* have no default execution mode;
* refuse model execution unless the later pilot authorization receipt is present;
* audit every installed executable and scientific byte against committed Git blobs during build;
* bind the exact image manifest, executable commit/tree, Dockerfile, task blob and base digest.

Record the ACR build run, tag, digest, complete log hash and image-to-Git result. Every bound image path must pass; do not hard-code the old 44-file count if the new manifest has a different derived count.

### 6.5 Minimal ACR context

Never give a repository checkout to `az acr run`.

Both canary and live submission must use a short fixed Windows directory and exactly two regular files:

* `task.yaml`
* `context_manifest.json`

The context manifest may embed authority, lock, admission and prefix-receipt bytes, but the directory itself must still contain exactly two entries.

Requirements:

* use a short path such as `C:\p0r2g2\acrctx`;
* maximum native path no greater than 100 characters;
* no symlinks, junctions, directories, hidden files, credentials, model files or result bytes;
* root-level `--file task.yaml`;
* final positional argument is the context directory;
* context is built from committed Git objects and explicitly supplied machine receipts, not from an ambient worktree copy;
* manifest records each embedded object’s name, length and SHA-256;
* task and context blobs are hash-verified immediately before invocation.

### 6.6 Windows launch-path proof

Before sealing readiness, test the exact launch implementation used for the one-shot call:

* resolve Azure CLI with `shutil.which`;
* record the exact resolved executable, including `az.CMD` on Windows;
* successfully execute benign `az version` and `az account show` checks through that exact resolved program;
* invoke `subprocess` without relying on PATHEXT or an implicit shell;
* test that the generation-2 guarded wrapper and the underlying submission module resolve the identical program;
* prove that the authorization environment variable is scoped only to the single child process and is not exported globally.

Any failure here stops before replay.

## 7. Mandatory Segment-A canaries and validation

After publishing the authority, run and seal all of the following.

### 7.1 Focused tests

Run all generation-2, inherited P0-R2, transport, recovery, closure, authorization and negative tests. Capture the pytest process exit code directly. Do not pipe pytest into `tail`, `tee`, or another process in a way that changes `$?`.

### 7.2 In-VNet prefix canary

Use a disjoint canary prefix and the generation-2 CPU prefix-proof job.

Prove:

* managed identity token acquisition succeeds;
* private Storage listing succeeds;
* exact prefix is unused;
* zero objects are returned;
* the probe writes nothing;
* the receipt is reconstructed and verified independently;
* all model/GPU counters are zero.

This canary must not use the future live or pilot prefix.

### 7.3 Exact ACR packing and pre-gate canary

Invoke the final generation-2 two-file submission path in canary mode.

It must prove:

* Windows packing, upload, queueing and ACR execution succeed;
* exactly one canary run ID is returned;
* image-to-Git audit passes;
* context lock and prefix receipt verify;
* the shared live/canary prefix-receipt validator runs;
* `P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1` appears exactly once;
* no managed-identity token request or Storage listing is attempted in ACR;
* the replay gate is not imported or invoked;
* every tokenizer/model/GPU/scoring counter is zero.

### 7.4 Hard-kill/open-admission recovery canary

Run a real CPU-only generation-2 hard-kill canary in Container Apps:

* terminate the writer with real SIGKILL/exit `-9`;
* leave an open admission after at least one committed payload;
* recover with the generation-2 recovery path;
* compare every recovered payload byte against independently regenerated expected bytes;
* require a continuous create-only journal;
* require the recursive recovery manifest to be written last;
* set:

  * `NVIDIA_VISIBLE_DEVICES=void`
  * `NVIDIA_DRIVER_CAPABILITIES=void`
  * `CUDA_VISIBLE_DEVICES=-1`;
* prove no GPU allocation and no tokenizer/model operation.

No simulated exception may substitute for SIGKILL.

### 7.5 Non-vacuous absence proof

From the same control-plane listing, prove:

* `job-jspace-s3-p0r2-pilot-g2` is absent;
* `job-jspace-s3-p0r2-recover-g2` is absent;
* at least one generation-2 CPU canary/prefix job is present.

A query failure or incomplete listing is ambiguity, never absence.

### 7.6 Full differential suite

Run the entire repository suite in the registered Linux closure against:

1. baseline `135f725baff7f5c9c1b0ae15ad5692bf77dd4fc5`;
2. the generation-2 executable commit;
3. the final pre-ready generation-2 closure where practical.

Require:

* zero collection errors;
* zero newly failing test signatures;
* exact matching standing-failure signature set;
* no hidden exit status;
* all new generation-2 tests passing.

The only accepted Linux standing failures are exactly:

1. `tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix`
2. `tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last`
3. `tests/test_phase05_jlens_saturation.py::test_no_artifact_asserts_a_prohibited_claim`
4. `tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only`

If either side has a different failure signature, any new failure, or a collection error, Segment B is forbidden.

### 7.7 Complete attempt ledger

Create an append-only generation-2 ledger that:

* imports and binds the existing 45 sealed P0-R2 runs as historical records;
* records every new build, validation, canary, failed, discarded and superseded run;
* includes run ID, mode, status, timestamps, image/task/source identities, exact log availability, byte lengths and SHA-256;
* distinguishes build-only, CPU canary, replay-capable and model-capable runs;
* contains zero unavailable and zero ambiguous replay/model/GPU-capable runs;
* never fabricates an unavailable hash;
* states whether each run could possibly have entered replay, model or GPU code.

## 8. Seal generation-2 readiness

After all corrections and canaries pass:

1. publish the executable commit and tree;
2. publish the new image digest;
3. publish the task Git blob;
4. publish the immutable-science proof;
5. publish the closure binding and exact path classifications;
6. publish the generation-2 schema, lock, manifest, receipts and handoff;
7. create a ready-anchor commit containing only the final lock object;
8. permit only explicitly classified governance/evidence objects after the anchor;
9. prove every post-anchor path from the proof implementation’s own committed bytes;
10. provide no caller-controlled path allowlist;
11. run host preflight from a second fresh, short-path checkout;
12. require `HEAD == origin/main`, a clean worktree, valid ancestry, exact lock bytes, exact image/task identities, generation-1 terminality, generation-2 job absence and all-zero counters;
13. publish the fresh-checkout proof by ordinary fast-forward.

The Segment-A terminal ready state is:

`STUDY3_P0_R2_GENERATION2_EXECUTION_READY_AWAITING_REPLAY_GATE`

This state does not itself authorize replay. Segment B is admitted only by the gate below.

## 9. Inter-segment admission gate

Generate a machine-readable admission document from a fresh checkout. Every condition must be derived from Git, an exact published receipt, or a read-only Azure result. No caller may supply a condition’s truth value.

Require all of the following:

1. this authority was the first post-`135f725…` committed object;
2. the authority commit was published before any generation-2 Azure operation;
3. P0-R1 remains terminal, consumed and byte-unchanged;
4. P0-R2 generation 1 remains terminal, consumed and byte-unchanged;
5. no generation-1 replay or pilot was rerun;
6. every file existing under the two frozen P0-R2 generation-1 roots is unchanged;
7. generation-2 namespaces are disjoint;
8. scientific blobs match the registered immutable science exactly;
9. the generation-2 image is a new digest;
10. every image-bound path passes image-to-Git audit;
11. the final ACR task blob matches Git;
12. the final ACR context has exactly two admitted entries;
13. maximum native context path is no greater than 100 characters;
14. the shared prefix-receipt validator is used by canary and live paths;
15. the ACR live path performs no private Storage or managed-identity probe before replay;
16. the in-VNet prefix canary passed;
17. the exact ACR packing/pre-gate canary passed;
18. the real hard-kill/open-admission recovery canary passed;
19. both bounded generation-2 jobs are proved absent non-vacuously;
20. all required run records are sealed and unambiguous;
21. the full differential suite has zero new failures and zero collection errors;
22. the four standing Linux failure signatures match exactly;
23. the lock and schema validate from committed bytes;
24. authority, executable, image, task, manifest, attempts, jobs, prefixes and caps are bound;
25. governance ancestry and post-anchor classification pass;
26. a second fresh checkout reproduces the host preflight;
27. `HEAD == origin/main == admitted_head`;
28. worktree is clean;
29. the exact Azure CLI executable resolves and benign launch checks pass;
30. generation-2 live replay has never been invoked;
31. generation-2 replay gate has never run;
32. generation-2 one-shot envelope is unconsumed;
33. the generation-2 live prefix has not yet been written;
34. generation-2 canonical replay artifacts are absent;
35. tokenizer/checkpoint/model/prefill/generation/scoring/GPU counters are all zero;
36. `formal_execution_authorized = false`;
37. evidence ledger remains at `EV-0016`;
38. no fact is unknown or underived.

Print:

* `P0_R2_G2_PHASE_B_AUTHORIZED=1`
* total condition count;
* failed count 0;
* underived count 0.

If any condition is false, unknown, stale or underived:

* set authorization false;
* publish a truthful generation-2 stop disposition;
* invoke no live replay;
* create no pilot or recovery job;
* perform no model operation;
* report the exact failed conditions;
* end the session.

## 10. Segment B1: final live-prefix proof

Only after the inter-segment gate passes:

1. use the already sealed generation-2 live attempt ID;
2. run the CPU-only prefix-proof job inside the registered VNet;
3. list the exact complete live prefix;
4. require successful listing and `object_count = 0`;
5. require `wrote_any_object = false`;
6. correlate the receipt with the Azure job execution and exact captured log;
7. verify all receipt identities and hashes;
8. rebuild the final two-file ACR context with the exact prefix receipt embedded;
9. rerun the host pre-invocation gate;
10. require the receipt to be no more than 15 minutes old when the live Azure CLI process starts.

If the probe, listing, receipt, correlation, context rebuild, or freshness check is ambiguous or fails, stop before replay. Do not substitute a new live attempt.

## 11. Segment B2: exactly one live replay

Invoke live replay only through the generation-2 guarded host wrapper.

Immediately before invocation, require again:

* current `HEAD == origin/main == admitted_head`;
* clean worktree;
* current-head governance proof;
* exact authority/lock/image/task/context identities;
* exact fresh live-prefix receipt;
* both bounded jobs absent;
* generation-2 artifacts absent;
* generation-2 counters zero;
* generation-2 envelope unconsumed;
* the resolved Azure CLI executable has passed the exact launch checks.

One-shot semantics:

* the envelope is consumed when the Azure CLI live process is successfully started;
* after process start, it is consumed even if no run ID returns or any later step fails;
* a `CreateProcess`/program-launch failure before a process exists is still a terminal session stop requiring new operator authority; do not repair and automatically retry;
* invoke the guarded live submission no more than once;
* require exactly one ACR run ID;
* missing or multiple run IDs are terminal;
* capture complete stdout, stderr and raw ACR log without truncation or pipeline exit-code substitution;
* never rerun, regenerate, substitute another attempt, or repair the gate in place after invocation.

Inside ACR, the live sequence must be:

1. image-to-Git audit;
2. context-manifest, authority, lock and admission verification;
3. bound host/VNet prefix-receipt validation;
4. exactly one
   `P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1` marker;
5. no managed-identity or private Storage call;
6. replay gate invoked exactly once;
7. complete transport envelope emitted.

## 12. Independent replay reconstruction

After the ACR run, reconstruct only from the captured raw log using the strict decoder. Do not use a locally generated result or an emitted receipt as an alternative source.

The four canonical generation-2 artifacts belong under:

`studies/study3/pilot/p0/results/p0-r2-g2/`

They are:

* `P0_R2_REPLAY_DISPOSITION.md`
* `p0_r2_replay_counters.json`
* `p0_r2_replay_receipt.json`
* `p0_r2_replay_result.json`

Create them only if their exact bytes are recovered and checksum-proved from the raw envelope.

Require:

* expected envelope marker count;
* exactly four unique admitted artifact names;
* no undeclared name;
* no duplicate;
* no path traversal;
* no checksum mismatch;
* no unproved repair;
* receipt/result/counters cross-consistency;
* exact attempt, image, lock, authority and generation identities;
* replay result equals the already registered pass outcome;
* replay counters prove zero tokenizer/model/GPU/scoring activity.

If the replay fails, refuses, emits no complete envelope, reconstructs fewer or more than four artifacts, or fails strict validation:

* publish raw logs, submission receipt, reconstruction receipt, counters and truthful stop disposition;
* do not fabricate canonical success artifacts;
* do not create either bounded job;
* do not perform a model operation;
* stop permanently for generation 2.

## 13. Publish replay pass before pilot

A replay pass does not immediately authorize GPU execution.

First:

1. commit the four recovered artifacts plus exact raw evidence and receipts;
2. push by ordinary fast-forward;
3. create a fresh checkout of the published head;
4. rerun governance and byte validation;
5. publish a current-head proof binding the replay evidence;
6. re-fetch and require `HEAD == origin/main`;
7. require the worktree clean.

Only then evaluate pilot authorization.

## 14. Conditional pilot authorization

Authorize the GPU pilot only if all are true:

* replay invoked exactly once;
* exactly one ACR run ID exists;
* replay gate invoked exactly once;
* all four canonical artifacts reconstructed from raw bytes;
* strict receipt validation passes;
* replay outcome is the registered pass;
* replay evidence and current-head proof are published;
* generation-2 pilot attempt is still unused;
* exact pilot prefix is proved unused by a fresh in-VNet CPU proof;
* GPU and recovery jobs are still proved absent;
* image, lock, science, task and authority identities remain unchanged;
* replay counters contain zero model/GPU operations;
* no query or identity is ambiguous;
* pilot authorization receipt is generated mechanically.

If any condition is false or unknown, publish `STOP_NO_MODEL_OPERATION` and do not create a job.

## 15. Exactly one bounded T4 pilot

If pilot authorization passes:

1. render the exact generation-2 pilot job from the sealed specification;
2. use:

   * job `job-jspace-s3-p0r2-pilot-g2`;
   * manual trigger;
   * `gpu-t4` workload profile;
   * one replica;
   * parallelism 1;
   * completion count 1;
   * `replicaRetryLimit = 0`;
   * pinned generation-2 image digest;
   * exact sealed pilot attempt and Blob prefix;
3. create the GPU job exactly once;
4. start it exactly once;
5. do not update, replace, restart or rerun it.

The runner must enforce, not merely report:

| bound                           | maximum |
| ------------------------------- | ------: |
| smoke prefills before extension |      60 |
| total non-generative prefills   |     180 |
| S4 generations                  |      12 |
| model-evaluation equivalents    |     228 |
| possible scored rows            |     210 |

Smoke runs first. If the registered extension criterion does not pass:

* do not extend;
* make no further prefill or generation call;
* recover and publish the smoke result;
* do not rerun.

If an Azure create/start query is ambiguous, query read-only until its actual state can be classified. Never issue a second create or start merely because the first response was unclear.

## 16. Mandatory CPU recovery after pilot terminality

After the GPU job reaches any terminal condition—success, scientific stop, failure, timeout, eviction, or hard kill—run recovery exactly once:

* use `job-jspace-s3-p0r2-recover-g2`;
* CPU-only workload;
* `replicaRetryLimit = 0`;
* set:

  * `NVIDIA_VISIBLE_DEVICES=void`
  * `NVIDIA_DRIVER_CAPABILITIES=void`
  * `CUDA_VISIBLE_DEVICES=-1`;
* perform no tokenizer or model operation;
* recover from the create-only Blob journal;
* validate hashes and sequence continuity;
* write the recursive recovery manifest last;
* capture and publish complete receipts and logs.

Do not rerun either the GPU job or recovery job if recovery is partial or fails.

## 17. Publication and stop rules

Use ordinary linear, first-parent, non-force fast-forwards only.

Before every push:

* fetch `origin/main`;
* require it still equals the expected parent;
* require no merge commit;
* require the exact intended diff;
* require no frozen byte changed.

Never:

* force-push;
* merge or rebase over another session’s work;
* use GitHub Actions;
* delete or rewrite evidence;
* delete Azure runs, jobs or Blob canary evidence needed for audit;
* fabricate a run ID, hash, receipt, absence proof or success artifact;
* interpret an Azure error as absence;
* call a failure `STOP_NO_MODEL_OPERATION` after model operations have actually occurred.

State naming:

* failure before any model operation:
  `STOP_NO_MODEL_OPERATION`;
* failure after bounded model operations:
  publish an accurate bounded-pilot failure state with exact nonzero counters;
* successful mechanical pilot completion:
  `STUDY3_P0_R2_GENERATION2_PILOT_EXECUTION_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW`.

Even after a successful pilot:

* do not select an interface;
* do not freeze the formal draft;
* do not add an evidence-ledger row;
* do not claim that the research question is answered;
* keep `formal_execution_authorized = false`.

## 18. Final disclosure

Finish with one self-contained disclosure containing:

* starting and final `origin/main` commit/tree;
* commit count, first-parent linearity, merge count and force-push count;
* authority path, length, Git blob and SHA-256;
* frozen-byte verification for P0-R1 and P0-R2 generation 1;
* generation-2 executable commit/tree;
* ready anchor;
* image tag/digest and base digest;
* ACR task blob;
* lock/schema/manifest identities;
* all new ACR and Container Apps run/execution IDs and statuses;
* packing, prefix, hard-kill and image-audit results;
* focused and full differential test counts and exact standing failures;
* inter-segment condition count, failed count and underived count;
* replay invocation count, run ID count and gate invocation count;
* reconstruction count and artifact hashes;
* GPU job create/start counts;
* recovery job execution count;
* every tokenizer/checkpoint/model/prefill/generation/scoring/GPU counter;
* bounded-cap consumption;
* Azure jobs and Blob residue intentionally retained;
* final state;
* explicit confirmation that P0-R1 and P0-R2 generation 1 remain terminal and untouched;
* explicit confirmation that `formal_execution_authorized = false`, evidence ledger remains `EV-0016`, and the research question remains unanswered pending independent methods review.

Proceed autonomously through Segment A. Proceed into Segment B only if every machine-derived admission condition passes. After the live process starts, never retry it. After a replay pass, proceed into the bounded pilot only if every post-publication pilot condition passes.
