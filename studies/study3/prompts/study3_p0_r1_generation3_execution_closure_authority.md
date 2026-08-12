Study 3 P0-R1 generation-3 execution-closure authority

## Status and controlling decision

This authority is a **model-free pre-execution repair authority**. It is issued
because the published generation-2 successor path at
`c04ec748a4b2b63af22f50595816b5e6b6805ff6` is not mechanically capable of
performing the already-authorized replay-then-conditional-pilot sequence without
an unrecoverable one-shot failure.

It does **not** authorize the live replay gate. It does **not** authorize a GPU
job, tokenizer construction or encode, checkpoint access, model load, forward
pass, generation, scored row, seed, bank operation, interface selection,
positive-reference operation, formal execution, methods review, or evidence
ledger row.

The operative decision is:

> Do not run `p0_r1_successor.sh live-replay` and do not create or start
> `job-jspace-study3-p0-r1-pilot-g2`. Preserve the single overall P0-R1
> envelope as unconsumed. Supersede generation 2 without consumption, close the
> production wiring and durability defects below in an additive generation 3,
> rebuild and relock, validate model-free on the real paths, publish a new
> handoff, and stop again at `STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE`.

This authority supplements, and does not weaken, the scientific and governance
boundaries in:

1. `studies/study3/prompts/study3_v0_6_p0_r1_authority.md`;
2. `studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md`;
3. `studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md`.

Where an earlier document describes generation 2 as launchable, this authority's
later, narrower finding controls: generation 2 is unconsumed but not launchable.
No scientific rule, corpus byte, allocation, cap, model revision, tokenizer
revision, scoring rule, smoke criterion, parser, statistic, claim boundary, or
terminal-state meaning may change.

## 1. Exact starting state and admission gate

Before any repository write, fetch `origin/main` and require:

| object | required identity |
| --- | --- |
| `origin/main` and `HEAD` | `c04ec748a4b2b63af22f50595816b5e6b6805ff6` |
| `HEAD^{tree}` | `4313778bc67cd9436339280d1d99c0798e66e165` |
| active-but-now-refused generation-2 lock | `studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json`, 26,172 bytes, sha256 `f506f632b8602cc000229b9a40991fc666cf0cf9f0195712cfe93d12fbee4714` |
| generation-2 image | `acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r1@sha256:5f964edb414b8a22682693d8314063693daca3b915398094ec008d2c03308827` |
| evidence ledger tail | `EV-0016`; no `EV-0017` |

Require a strict first-parent, non-force lineage from
`71f4ab903295d1320881b654bda2d49cf1808794` through the five published commits
ending at the required head. Verify by read-only Azure queries that:

- no live P0-R1 replay run exists;
- `job-jspace-study3-p0-r1-pilot-g2` has no execution and, as reported, does
  not exist;
- no generation-1 or generation-2 model-operating execution, tokenizer
  construction, encode, checkpoint access, model load, GPU allocation, forward
  pass, generation, scored row, result prefix, result directory, seed, bank
  operation, positive reference, or evidence row has appeared;
- all 31 P0-R1 counters remain zero; and
- `p0_r1_pilot_execution_authorized = true`,
  `p0_r1_pilot_execution_consumed = false`, and there is exactly one overall
  envelope, not one per lock generation.

Any Azure authentication, query, parsing, timeout, or ambiguity is a stop. A
failed query is not evidence that a job or execution is absent.

### 1.1 Known cross-platform clean-filter defect

A fresh Linux checkout of the required head can report
`studies/study3/pilot/p0_r1/execution/p0_r1_model_execution.py` as modified even
when its raw worktree bytes equal its committed blob: the committed blob is CRLF
while `.gitattributes` registers `execution/*.py text eol=lf`.

At admission, distinguish this exact known clean-filter defect from a real edit:

- compare the worktree file byte-for-byte with `HEAD:<path>` using no clean or
  smudge filter;
- require the raw bytes to be identical to the committed 10,229-byte blob with
  sha256 `392f78466ee61ed303b5cf4b1fba4423e38b128441aeec1de119315b2e52a5ee`;
- require no other dirty path; and
- do not normalize, stage, or rewrite that historical file before committing
  this authority.

If the worktree is already clean, record that fact. If the only status entry is
the exact filter artifact above and the raw bytes agree, record it explicitly
and commit this authority with an exact pathspec so no normalization is staged.
Any real byte difference is a stop.

Commit this authority byte-identically as the **first new object**, publish it
by ordinary non-force fast-forward, and record its byte count, sha256, LF/CR
count, BOM status, and trailing-newline status before any implementation write.

## 2. Why generation 2 is not execution-ready

The following are demonstrated production-path defects, not optional cleanup.
Each would either make the successor fail before the intended operation or lose
the only recoverable evidence after an irreversible action.

### G2-01 — the documented first command cannot run

`container/p0_r1_successor.sh preflight` passes `--lock-file` and optionally
`--image-digest` to `p0_r1_execution_lock_v2.py`. That CLI defines neither
argument. The exact handoff command exits 2 with `unrecognized arguments`.

### G2-02 — the production model runner CLI can never authorize

`p0_r1_model_runner_v2.py --run` reads lock and receipt bytes but calls
`run(...)` without an `authorization` mapping. The first production check then
refuses with:

`the P0-R1 model pilot requires an execution authorization mapping carrying the execution lock and the replay-pass receipt`

The unit tests call `RUNNER.run(...)` directly with a synthetic authorization
mapping and therefore bypass the shell-to-CLI wiring used by the real GPU job.
As published, a passed replay followed by the T4 launch would allocate the job
and then fail before tokenizer/model work, spending the only execution path for
a wiring defect.

### G2-03 — the exact emitted replay receipt cannot authorize the pilot

The replay gate writes `p0_r1_replay_receipt.json` while
`transport.complete_byte_recovery_verified` is false. It later verifies the
four-file envelope only in memory and writes a separate transport receipt, but
does not rewrite or re-emit the canonical replay receipt. The launcher/runner
requires the canonical receipt's field to be true. Tests hand-construct that
field as true rather than consuming the receipt actually emitted by
`p0_r1_replay_gate_v2.run`.

The separate `p0_r1_replay_transport_receipt.json` is created after the
four-file envelope and only its hash and size are printed; its complete bytes
are not part of the recoverable log envelope. Thus the exact recovered gate
receipt and the exact launcher contract cannot agree.

### G2-04 — the successor is a dispatcher, not the required one-shot closure

The `live-replay` mode runs `az acr run` against the mutable current source
directory, does not construct the context from an exact Git object, does not
capture a run ID or the raw log from the first byte into a retained file, does
not reconstruct or verify the artifacts, and does not publish the replay
pass/stop commit. It prints a manual recovery suggestion after the command.

The `launch-pilot` path likewise does not monitor the exact returned execution,
recover the actual bytes, reconcile counters, publish a terminal disposition,
or stop at the terminal boundary. These were mandatory wrapper duties in the
generation-2 authority, not operator prose.

### G2-05 — Azure control-plane errors are treated as absence

The launcher evaluates the execution-history query with
`... 2>/dev/null || echo "absent"`. Authentication failure, network failure,
authorization failure, malformed output, and true job absence therefore enter
the same branch. It may attempt a create after an unproved absence. Every
read-only precondition must instead fail closed and preserve the complete
command error.

### G2-06 — the private prefix is not proved unused before GPU start

The launcher derives and prints a prefix but performs no managed-identity data
plane preflight before job creation/start. `assert_prefix_unused` is reached
only later during bulk persistence, after model operations may already have
occurred. This is too late for a unique, no-overwrite, one-shot attempt.

### G2-07 — the journal is not durable on the production path

The shell invokes the model runner without `--blob`. The runner therefore uses
only `LocalSequenceSink` under the container's ephemeral result directory.
`BlobSequenceSink` is optional and absent on the real command. The hard-kill
test also uses only a temporary local directory, so it does not prove survival
of Container Apps teardown.

Even when a Blob transport is injected in a unit test, journal entries record
operation names and row IDs but not every actual scored row, S2 reuse, raw S4
completion, exception, smoke state, resource observation, and cumulative
counter payload required by the authority. A hard termination can therefore
lose the observations while leaving only an admission label.

### G2-08 — ordinary failure evidence can still die with the container

The shell EXIT trap writes `p0_r1_infrastructure_receipt.json` only to the
ephemeral local directory and emits no complete-byte secondary envelope. It
does not persist or read it back through Blob. Serialization and upload are not
inside a durable top-level boundary.

The later bulk `--persist` command enumerates only top-level files with
`os.listdir`; it excludes the nested immutable-sequence journal directory. The
final manifest therefore cannot enumerate every journal object. A process kill,
serialization error, or transport error can still leave no operator-recoverable
canonical receipt.

### G2-09 — no production recovery path exists for the private account

The handoff's operator command instantiates `ManagedIdentityCredential`
directly. A normal external successor workstation does not possess the Azure
resource's managed identity and may also be outside the private endpoint. The
earlier authority explicitly required a separately named CPU-only,
managed-identity recovery job when direct data-plane access is unavailable.
Generation 2 provides no such job or wrapper.

### G2-10 — the ready identity is propagated, not validated

The v2 lock stores a parent and a prose relationship but no exact active ready
commit/tree. Runtime validation accepts any coordinated 40-character
`ready_commit` placed in both the gate receipt and launcher argument. It does
not prove that value is the published ready object, that the executable commit
is its ancestor, that bound paths are unchanged, or that the checkout equals
`origin/main` and is clean.

The handoff calls `c7e02b43...` the ready commit while the published closeout
calls `c04ec748...` the final ready commit. The two-object distinction may be
legitimate, but it must be represented and mechanically checked rather than
left to prose.

### G2-11 — validation did not meet the frozen acceptance rule

The controlling generation-2 authority requires a clean exact-commit CPU-only
ACR full suite based on 4,387 passes, 15 skips, and only the two registered
historical failures, plus the exact net-new node IDs. The committed run log at
`c04ec748...` instead accepts a workstation baseline of 4,378 passes and 11
failures, explaining nine as a WSL `bash` environment artifact. That may explain
the workstation, but it does not satisfy the explicit ACR acceptance rule.

The closeout mentions ACR run `cmgb`, but the committed run log does not record
its exact full-suite node count, two permitted failure identities/signatures,
skips, command, commit/tree, or raw retained receipt. No generation-3 ready
claim may inherit this unreconciled validation.

### G2-12 — several claimed production-bound tests are vacuous at the seam

The successor, launcher, and shell tests largely assert that strings occur in
files. The runner tests call an internal function with authorization already
constructed. The hard-kill test proves only a local temporary sink. No test
executes the exact handoff preflight command, the exact shell-to-runner CLI, the
gate-emitted receipt through recovery into launch validation, Azure query-error
handling, exact execution-name monitoring, private recovery job, or hard-kill
Blob survival. All must become executable seam tests.

## 3. Scope and protected bytes

Implement an additive **generation 3**. Preserve generation 1 and generation 2
as byte-identical, unconsumed historical objects and explicitly supersede both
as `launchable = false` in the v3 lock and handoff.

Do not edit:

- any immutable P0-T file or result;
- the frozen 35-cell / 70-member P0 corpus or manifest;
- any P0-R1 scientific rule, corpus binding, role identity/revision, scoring
  implementation, allocation, cap, smoke criterion, parser, summary statistic,
  state meaning, or claim boundary;
- `paper/evidence_ledger.csv` or any evidence row;
- any earlier authority, generation-1 lock/handoff/image definition, or
  generation-2 authority/lock/handoff/image definition/executable byte;
- Study 1, Study 2, OD2, UR-22, RP, seed, bank, confirmation, selection,
  positive-reference, or formal-development objects.

Prefer new `*_v3` modules, schemas, task/job definitions, entry points, lock,
handoff, tests, and receipts so the two failed pre-execution generations remain
auditable. The only permitted repair to a historical-path rule is a narrowly
scoped `.gitattributes` exception that preserves the existing CRLF blob for
`execution/p0_r1_model_execution.py` byte-for-byte while making a fresh Linux
checkout clean. Do not normalize that file.

Updates to navigational READMEs, `docs/run_log.md`, and `docs/decision_log.md`
are allowed. Record every failed build, canary, and validation; do not delete or
rewrite history.

## 4. Generation-3 execution architecture

### 4.1 One exact, model-free preflight

Provide one v3 successor wrapper with explicit `preflight`, `live-replay`, and
`launch-pilot` modes and no default. In this authority only `preflight` may run.

The exact published preflight command must be executed as a test and in a fresh
checkout. It must require and verify, without model operations:

- `HEAD == origin/main` and an empty Git status;
- the current full commit and tree, plus the distinct locked executable commit
  and tree;
- strict ancestry and zero changes to every v3 bound byte after image build;
- active v3 lock/schema/hash and exact image digest;
- generation 1 and 2 unconsumed, superseded, and not launchable;
- all counters zero, no results directory/prefix, no prior replay, and no
  generation-3 GPU job execution;
- read-only Azure queries that fail closed on every error; and
- exact context construction from committed Git objects, never mutable
  worktree bytes.

Do not force a self-referential commit hash into a file that contains itself.
Represent the executable-code commit, lock-carrying ready anchor, and final
published head as distinct identities. At successor time, require
`HEAD == origin/main`, compute its exact commit/tree, prove the ready anchor is
an ancestor, and prove every post-anchor change is inside a narrow governance
allowlist. The closeout must provide the exact final head/tree as the mandatory
fresh-session inputs.

### 4.2 Replay capture and authorization tuple

The v3 live replay mode must be a single transaction-like orchestration around
exactly one `az acr run` submission:

1. build its ACR context with `git archive` or an equivalent committed-object
   export from the exact published head; record the archive/context hash;
2. submit the registered CPU-only replay once and capture the returned ACR run
   ID unambiguously;
3. retain the complete raw log from its first byte, with no implicit tail limit;
4. retain every Azure CLI stdout, stderr, exit code, and ambiguity;
5. reconstruct the four canonical replay files from that exact log without
   invoking the gate again;
6. write and retain a deterministic reconstruction receipt binding run ID, raw
   log bytes/hash, envelope manifest, attempt ID, and all recovered file
   bytes/hashes;
7. validate the gate result and reconstruction proof together; and
8. publish the raw log, run identity, recovered bytes, reconstruction receipt,
   and registered pass/stop disposition by non-force fast-forward before any
   model job is created.

Avoid circular self-attestation. The canonical replay receipt need not claim
that its own later operator recovery has already happened. It must remain the
exact emitted byte sequence. Model authorization is the tuple of:

- the exact recovered replay receipt;
- the exact reconstruction receipt derived from the captured raw log; and
- the active v3 lock and current published-head proof.

The launcher must require all of them as mandatory exact-byte inputs and verify
that they bind the same attempt, image, executable commit/tree, ready anchor,
published head/tree, authorities, corpus/P0-T identities, raw log, artifact
manifest, and zero replay model counters. Neither receipt alone authorizes the
pilot. Never mutate or regenerate the gate receipt to add a transport pass.

On any replay, capture, reconstruction, validation, publication, push, or state
ambiguity, publish the registered stop if recoverable and perform no model
operation. Never rerun the gate.

### 4.3 Exact shell-to-runner authorization

The v3 model entry point and runner CLI must construct and validate the same
authorization document from the injected exact inputs before importing a model
library. The production shell command itself must be exercised end-to-end with
a synthetic sentinel executor that proves it reaches the authorized executor
boundary exactly once without importing `transformers`, accessing a checkpoint,
or allocating a GPU.

No unit test may bypass the real CLI wiring by supplying an authorization
mapping that production never constructs.

### 4.4 Prefix preflight and fail-closed Azure control plane

Before a GPU job create or start, prove through the registered private endpoint
and managed identity that the exact attempt prefix and every reserved final or
journal object name are absent. Because an external workstation cannot assume
the resource's managed identity or private-network route, implement a separately
named CPU-only Container Apps preflight/recovery job for this proof.

Every control-plane and data-plane query has three distinct outcomes: proved
absent, proved present, or error/unknown. Only proved absent may continue.
Remove all `|| echo absent`-style error collapsing. Preserve and publish every
failed command with pre-operation counters.

Use a new generation-3 GPU job name. If it exists, verify its complete
configuration byte-for-byte against the registered definition before start; a
zero-execution but stale or foreign job must refuse. Never update an existing
job into compliance under the live launch mode.

Capture the exact execution name returned by the single start request. If the
request result is ambiguous, do not submit another start. Reconcile the job's
execution history read-only and stop for operator disposition. Monitor only the
captured execution.

### 4.5 Private-Blob journal is the primary evidence

Before any tokenizer/model import, initialize and read back an append-only or
create-only journal under the attempt-bound private Blob prefix. Blob is the
primary sink on the production path; the container filesystem is a cache only.

Durably write and read back, with immutable sequence numbers or conditional
create semantics:

- attempt start and every bound identity;
- admission and completion/failure of each tokenizer construction, encode,
  checkpoint download/load, CUDA/model residency operation, prefill,
  generation/decode, parser call, and scored row;
- the complete actual payload of every valid scored row, S2 vector reuse, raw
  S4 completion, exception, smoke transition/state, resource observation, and
  cumulative counter snapshot;
- every open admission on interruption;
- serialization and upload start/completion/failure; and
- terminal/partial/infrastructure disposition and the final manifest.

Count at admission before the external call. Never overwrite, resume, repair,
replace, or rerun an observation. A hard kill after a row has been produced must
leave that row's exact bytes recoverable from Blob, not merely its row ID.

The final manifest, written last, must enumerate and verify every canonical
artifact and every immutable journal object. Recursive enumeration is required;
top-level `os.listdir` is insufficient.

### 4.6 Every recoverable exit has two routes

Put authorization validation, journal initialization, tokenizer construction,
checkpoint access, CUDA initialization, model loading, smoke, extension, S4,
serialization, Blob persistence, readback, manifest construction, and shell
startup under explicit exception/finalization boundaries.

Whenever the process can still write, an ordinary failure must produce and read
back the most conservative partial or infrastructure receipt in Blob. The shell
trap must also emit that receipt over a bounded complete-byte console envelope
as the secondary route. A hash-only line is not sufficient.

If Blob is unreachable, preserve the complete secondary bytes in the exact
captured execution log and report durability degradation. Missing or ambiguous
evidence is nonzero/unknown and authorizes no retry.

### 4.7 Recovery, monitoring, and publication

Provide a CPU-only, managed-identity recovery job that:

- accepts only the captured attempt/execution identity and active v3 lock;
- reads the immutable manifest and every listed object through the private
  route;
- verifies bytes, sha256, counts, sequence continuity, attempt bindings, and
  manifest-last status;
- emits the verified complete bytes through the same bounded log envelope;
- performs no tokenizer, checkpoint, model, GPU, seed, bank, or provider
  operation; and
- is not a replay or model retry.

The successor wrapper must capture that recovery execution and full log,
reconstruct the files locally, compare the Blob and console routes, reconcile
the exact GPU execution record and conservative counters, and publish every
partial or terminal byte by non-force fast-forward. It then stops without
beginning the final methods review.

## 5. Non-vacuous validation

Add tests that fail at `c04ec748...` and pass only when the exact production
seams above are closed. At minimum:

1. run the exact v2 handoff preflight and preserve its current exit-2 failure as
   the regression demonstration;
2. run the exact v3 handoff preflight successfully in a fresh Linux clone;
3. prove that clone has an empty status and the historical CRLF blob is
   byte-identical, not normalized;
4. invoke the exact v3 model shell and runner CLI with valid synthetic injected
   lock, replay receipt, reconstruction receipt, and published-head proof; reach
   a no-model sentinel executor once;
5. prove the exact v2 runner CLI currently refuses because authorization is not
   passed;
6. feed the actual gate-produced receipt shape through log recovery into launch
   validation; require the independent reconstruction receipt and never
   hand-edit a transport flag;
7. missing/truncated/conflicting/wrong-run/wrong-attempt raw logs and mismatched
   reconstruction receipts refuse before any model command;
8. simulate Azure job-not-found separately from authentication, permission,
   network, timeout, malformed-output, and unknown errors; every error yields
   zero create/start calls;
9. capture a synthetic start response's exact execution name and prove polling,
   logs, and recovery target only that execution;
10. prove a stale zero-execution job configuration refuses rather than being
    started or updated;
11. exercise the real prefix-preflight and recovery entry points with an
    injected production-shaped Blob backend, including existing-object and
    query-error refusals;
12. hard-kill a subprocess after an admitted operation and after an emitted row;
    recover the last admission and the row's exact bytes from the Blob sink;
13. force failures before runner entry, during each registered irreversible
    stage, during serialization, during each journal write, during artifact
    upload, during readback, and during manifest-last; recover the most
    conservative receipt and all prior bytes;
14. prove the shell EXIT trap persists and emits its receipt, not merely that
    the script contains a `trap` string;
15. prove the final manifest recursively enumerates every journal object and
    refuses a missing, extra, reordered, overwritten, or hash-mismatched object;
16. exercise the CPU-only private recovery job's exact command and secondary
    envelope without a tokenizer/model import or accelerator; and
17. prove generations 1 and 2 remain byte-identical, unconsumed, superseded,
    and not launchable.

String-presence tests do not satisfy a runtime seam. Synthetic Azure/Blob/model
objects are allowed, but each mutation must reach the exact production wrapper,
shell, CLI, or transport path it claims to test.

## 6. Validation and infrastructure rules

All workstation work remains code editing, static inspection, CPU-only unit
tests, Git plumbing, and read-only Azure queries. Do not download a checkpoint
or import/instantiate a real tokenizer/model locally.

Authoritative validation must run in clean exact-commit CPU-only ACR contexts
built from committed Git objects. The frozen acceptance baseline is:

- 4,387 passed;
- 15 skipped; and
- only the two registered historical `test_parser_v3_seal_job` failures with
  unchanged node IDs and signatures.

Reconcile the final full suite as 4,387 plus the exact net-new passing node IDs.
The workstation's 4,378/11 result is diagnostic only and cannot be the
acceptance baseline. Any additional failure, changed historical signature,
unexplained skip, missing raw ACR receipt, or arithmetic mismatch is a stop.

After the final v3 executable commit and before the lock:

- build a new image from exactly that commit and resolve its immutable manifest
  digest;
- prove every v3 executable blob inside the standalone image against the Git
  object bytes;
- run the standalone layout and exact CLI-wiring canaries with no context mount;
- run the replay log capture/recovery canary through the exact ACR task path,
  including run-ID capture and raw-log recovery;
- run the private prefix/journal/hard-kill/recovery canaries through the actual
  CPU-only Container Apps environment, private endpoint, and managed identity;
- retain every canary object under a unique no-overwrite prefix;
- use no GPU workload profile and perform zero model operations; and
- record all failed and successful build/canary run IDs.

A dry-run or in-memory backend may supplement, never replace, the production
path. If any executable byte changes after the image build, discard the
unexecuted image, rebuild from the new executable commit, rerun all required
canaries, and create a new lock. Never amend or retag a published object into
compliance.

## 7. Generation-3 lock and legal state

Create a versioned v3 lock and schema binding at least:

- all four authorities by exact byte identity;
- generation-1 and generation-2 locks, images, executable commits/trees, and
  explicit unconsumed/superseded/not-launchable records;
- the v3 executable commit/tree and every executable blob;
- the new image/base immutable digests and pinned dependency closure;
- the lock-carrying ready anchor and the permitted governance-only descendant
  rule;
- the exact successor context-construction algorithm;
- replay raw-log, reconstruction-receipt, and authorization-tuple schemas;
- the private prefix-preflight, primary Blob journal, full recursive manifest,
  secondary envelope, and CPU recovery-job identities;
- every model-free production canary receipt;
- immutable corpus/P0-T identities, roles/revisions, caps, exact smoke
  allocation, and all-zero counters; and
- exactly one remaining overall replay-then-conditional-pilot envelope.

The v3 legal status remains:

- `formal_execution_authorized = false`;
- `p0_r1_pilot_execution_authorized = true`;
- `p0_r1_pilot_execution_consumed = false`;
- `draft_v0_6_frozen = false`;
- `draft_v0_6_reviewed = false`;
- interface, positive reference, and RP wrapper `null`;
- OD2 and UR-22 unresolved;
- evidence ledger ends at `EV-0016`; and
- the research question remains unanswered.

## 8. Required publication order

Use append-only, non-force fast-forward history in this order:

1. commit and publish this authority alone;
2. implement the additive v3 closure and non-vacuous tests;
3. commit and publish the final v3 executable bytes;
4. build the image from exactly that executable commit and record the digest;
5. run only the authorized model-free ACR/CPU Container Apps canaries;
6. create and publish the v3 lock, schema, and handoff as strict descendants;
7. run clean exact-commit CPU-only ACR targeted and full-suite validation;
8. perform the changed-path census, protected-byte audit, image-bound byte audit,
   and generation-1/2 supersession audit;
9. publish governance/run-log closeout changes only, proving no bound byte
   changed after image build; and
10. require `HEAD == origin/main`, a clean fresh Linux checkout, and strict
    first-parent lineage, then stop.

No commit amend, rebase, merge commit, force push, deletion of Azure history,
tag movement, result overwrite, or hidden repair is authorized.

## 9. Closeout report

The final report must include:

- exact starting, authority, executable, image-build, canary, lock/ready-anchor,
  validation, and final published commits/trees/run identities;
- this authority's byte identity and line-ending facts;
- a table mapping G2-01 through G2-12 to the production path and executable test
  that closes each;
- raw reproductions of the v2 preflight and runner-CLI failures;
- proof the gate-emitted receipt plus independent reconstruction receipt reaches
  the v3 launch guard without mutation;
- proof every Azure query error fails closed and zero live create/start commands
  occurred;
- fresh-clone clean-status and historical-CRLF byte-preservation proof;
- raw ACR full-suite receipt and exact 4,387-plus-net-new reconciliation with
  only the two historical failures and 15 skips;
- every image, dependency, source-blob, lock, canary, context archive, raw-log,
  Blob prefix, manifest, and recovery identity;
- exact changed-path census and protected-byte audit;
- generation 1 and 2 byte-identical, unconsumed, superseded, not launchable,
  with zero executions/GPU/tokenizer/checkpoint/model counters;
- generation 3 with all counters zero, no results directory or real attempt,
  and no GPU job execution;
- one overall envelope still authorized and unconsumed; and
- the exact fresh-session successor instruction with final head/tree, v3 image
  digest, lock identity, mandatory preflight, and explicit live confirmation.

## 10. Stop condition

This round ends only at:

`STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE`

with generation 3 active and generations 1 and 2 inert. Do not run the live
replay gate merely because preflight passes. Do not create or start a GPU job.
Do not begin the final focused methods review.

The sole next action after a successful closeout is a **new, fresh execution
session**. That session first runs the exact v3 preflight. Only an explicit
operator decision in that fresh session may spend the one replay envelope. A
replay failure, capture failure, reconstruction failure, publication failure,
or ambiguity stops with no model operation. Only a recovered-byte replay pass
plus its independent reconstruction proof may authorize the single bounded v3
GPU pilot in that same session.
