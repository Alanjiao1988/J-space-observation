# Study 3 P0-R2 infrastructure-successor authority

## Status and controlling decision

This is a **model-free infrastructure-successor preparation authority**. It
does not retry, reopen, repair, or reinterpret P0-R1. P0-R1 consumed its only
generation-3 replay envelope and remains permanently closed at
`STOP_NO_MODEL_OPERATION` under commit
`30806d793872a50e581d3252382b4a0ec2af3889`.

The controlling decision is:

> Preserve P0-R1 and every one-shot fact byte-identically. Create a separately
> registered P0-R2 envelope whose scientific design is identical to P0-R1 and
> whose only permitted difference is the host-to-ACR submission transport.
> Implement and validate that transport without tokenizer, checkpoint, model,
> GPU, replay-gate, scoring, or evidence-ledger activity. Publish a new lock and
> handoff, then stop at
> `STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE`.

This authority does **not** authorize the P0-R2 live replay gate or any model
pilot. Both require a later explicit operator decision after the ready
publication has been independently checked.

## 1. Exact admission state

Before any implementation write, require:

| item | required identity |
| --- | --- |
| `HEAD` and `origin/main` | `30806d793872a50e581d3252382b4a0ec2af3889` |
| `HEAD^{tree}` | `db7c957fe24be18c780687d471014ef5ec6e4fce` |
| worktree | clean |
| P0-R1 parent | `aed13b7257096963c90a1ae5340d14ef3892392c` |
| P0-R1 stop disposition | `STOP_NO_MODEL_OPERATION` |
| P0-R1 stop receipt | `studies/study3/pilot/p0/results/p0-r1/p0_r1_generation3_stop_receipt.json` |
| P0-R1 stderr | 433 bytes, sha256 `1323c36df5943c9dcdb34918fdd8a8c34656d48bdc7643dc3fcacfc2e59b110e` |
| evidence-ledger tail | `EV-0016`; no new evidence row |

The authority itself must be the first new committed object and must be
published by ordinary non-force fast-forward before implementation begins.
Record its exact byte count, SHA-256, line-ending counts, BOM status, and
trailing-newline status. No Azure operation is permitted in that first
publication.

## 2. Registered interpretation of the P0-R1 stop

The P0-R1 preflight passed. The single `live-replay` invocation then failed on
the operator host while Azure CLI was packing the local source context. The
captured error names this committed regular blob:

`artifacts/jlens-s2-production/20260806T194226Z/analysis/convergence_per_layer.jsonl`

The blob exists at the required P0-R1 starting commit as mode `100644`, object
`807fcd4c69dc9a53c46af7c49cbe0dc160e27c0c`, 15,398 bytes. The complete native
Windows path presented to the packer was 265 characters. No ACR run ID or
replay attempt ID was created, the captured stdout was the zero-byte file, and
the replay gate never started.

This is registered as a **pre-ACR host submission failure**, not an Azure run,
replay-science, tokenizer, checkpoint, model, or GPU outcome. Nevertheless,
the P0-R1 one-shot rule remains controlling: its envelope is consumed and may
not be rerun. The local stop receipt is not, and must never be represented as,
the signed Azure zero-operation retry receipt required by the old retry rule.

P0-R2 is therefore a new preregistered infrastructure successor, not a renamed
P0-R1 retry. No P0-R1 receipt, attempt ID, result path, prefix, job name, state,
or counter may be reused as a P0-R2 identity.

## 3. Scientific invariants

P0-R2 must bind and use the exact P0-R1 scientific bytes. It may not change:

- the frozen 35-cell / 70-member corpus or manifest;
- roles RT, RL, and RI, their revisions, templates, or task allocation;
- fp16 evaluation mode, no-sampling rule, seeds, parser, scoring, eligibility,
  factorization, smoke conditions, summary statistic, or pass/stop boundary;
- the maximum of exactly 60 smoke prefills before extension, 180
  non-generative prefills, 12 S4 generations, 228 model-evaluation
  equivalents, and 210 scored rows;
- any P0-T artifact, Study 1 or Study 2 artifact, OD2, UR-22, RP, positive
  reference, formal-development object, or evidence-ledger row; or
- the rule that this is a pilot-only methods-feasibility observation that
  cannot select an interface, set a threshold or confirmation sample size,
  freeze draft v0.6, or answer the research question.

The P0-R2 lock must carry exact Git blob and SHA-256 bindings for every reused
scientific file and must prove that each equals the P0-R1 generation-3 image
source. Delegating scientific calculations to those unchanged modules is
preferred over copied or edited science.

## 4. Permitted implementation scope

Implementation is additive under
`studies/study3/pilot/p0_r2/`, new P0-R2 tests, the P0-R2 lock and schema, a
P0-R2 handoff, and navigational/run-log updates. Every P0-R1 source, lock,
handoff, result, stop receipt, raw log, counter, and authority is protected and
must remain byte-identical.

The P0-R2 namespace must be disjoint:

- stage and artifact identifiers use `P0-R2` / `p0_r2` / `P0_R2`;
- attempts begin `p0r2-g1-`;
- the GPU job is `job-jspace-s3-p0r2-pilot-g1`;
- the CPU recovery job is `job-jspace-s3-p0r2-recover-g1`;
- durable Blob prefixes begin `study3/p0_r2/g1/`; and
- canonical P0-R2 result files live under
  `studies/study3/pilot/p0/results/p0-r2/`.

No existing Azure job may be updated or repurposed into a P0-R2 job.

## 5. Required submission-transport repair

P0-R2 must never give the full repository checkout to `az acr run`. The ACR
task executes the digest-pinned standalone image and needs no repository
context mount. The successor must instead build a **minimal context** from
exact committed Git objects with all of these properties:

1. The context contains only a root-level `task.yaml` and a root-level
   `context_manifest.json` before Azure CLI packing.
2. `task.yaml` is extracted byte-for-byte from the exact published commit with
   `git show <commit>:<registered-task-path>` or an equivalent Git-object read;
   it is never copied from mutable worktree bytes.
3. The manifest records source commit and tree, registered source path, Git
   blob ID, byte count, SHA-256, context-relative name, and an explicit
   declaration that no model or result byte is present.
4. The wrapper re-reads both context files, rejects symlinks and extra entries,
   and verifies the manifest immediately before submission.
5. The context directory name is short and fixed, such as `acrctx`; it must not
   contain the 40-character commit in its name or mirror repository paths.
6. Before invoking Azure CLI, the wrapper measures every native absolute path
   that the local packer can encounter. On Windows the maximum must be at most
   240 characters, leaving explicit headroom below classic `MAX_PATH`; an
   unavailable conversion to a native Windows path is an admission failure,
   not permission to guess.
7. The wrapper prints and retains a model-free admission receipt containing the
   file set, hashes, native paths, maximum path length, platform, Azure CLI
   version, and exact command arguments with secrets excluded.
8. The `az acr run --file` argument names root-level `task.yaml`, and the final
   positional context is the verified minimal directory only.

On non-Windows hosts, the same two-file context and byte verification are
mandatory; the native-path ceiling is still recorded even though the Windows
limit is not controlling.

## 6. Mandatory model-free tests and canaries

Before any ready claim, tests must execute rather than inspect strings and
prove at least:

- a synthetic deep Windows base path reproduces a greater-than-260 full-repo
  path while the two-file minimal context stays at or below 240;
- a task-byte mutation, extra context file, symlink, wrong Git blob, wrong
  source commit/tree, or path-measurement failure refuses before `az acr run`;
- mocked command capture passes only `task.yaml` and the minimal context;
- the exact P0-R2 preflight command performs no create, update, start, replay,
  tokenizer, checkpoint, model, GPU, scoring, or evidence operation;
- P0-R1 protected bytes and its stop publication remain unchanged; and
- every counter starts at zero with real, non-placeholder identities.

Run an exact-host production packing canary through the same Azure CLI path
that failed P0-R1. It must use the final minimal-context builder and final task
shape, run CPU-only in a disjoint canary mode, and prove from the returned ACR
run ID and captured raw log that packing/upload/queueing succeeded. The canary
must not evaluate the replay factorization gate and must report zero tokenizer,
checkpoint, model, GPU, prefill, generation, scoring, and evidence operations.

The canary does not consume the P0-R2 replay envelope. Any canary ambiguity or
missing complete log is a stop and forbids the ready claim.

## 7. Lock, ready publication, and execution boundary

The generation-1 P0-R2 lock must bind:

- this authority and every inherited scientific authority;
- the P0-R1 terminal stop commit, receipt, counters, stderr, and zero-byte raw
  log as historical predecessor evidence;
- the executable commit/tree and SHA-256 of every new operational byte;
- every unchanged scientific dependency by Git blob and SHA-256;
- the digest-pinned image, base-image digest, canary run ID, host packing
  receipt, and complete retained raw-log identity;
- a real ready-anchor relationship and governance-only descendant rule;
- the disjoint Azure jobs, Blob prefix, artifact names, and attempt format; and
- all zero pre-execution counters and the exact bounded maxima.

Validation must include the focused P0-R2 suite and a clean exact-commit,
CPU-only full repository suite. Historical failures may be accepted only if
their exact node IDs and signatures match the already registered baseline;
new failures are forbidden.

Publish the lock, schema, audits, canary receipts, validation receipts, and
`P0_R2_HANDOFF.md` by ordinary non-force fast-forward. The handoff's first
command is model-free `preflight`. It must require `HEAD == origin/main`, a
clean worktree, exact lock/image/anchor/bound-byte agreement, P0-R1 terminal
and nonlaunchable, proved absence of the P0-R2 GPU job and unused P0-R2 result
prefix, and the final two-file context admission proof.

Stop after publishing:

`STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE`

Do not run `live-replay` in the preparation/closure session. A future explicit
operator decision may consume the P0-R2 replay envelope exactly once. Only a
captured replay pass plus independent byte reconstruction and a published
current-head proof may authorize the bounded P0-R2 GPU pilot. Any replay,
capture, reconstruction, or publication failure again stops with no model
operation and no rerun.

## 8. State at this authority publication

- P0-R1: `STOP_NO_MODEL_OPERATION`, consumed, nonlaunchable;
- P0-R2: preparation authorized, replay unconsumed, not execution-ready;
- `p0_r2_pilot_execution_authorized = false` until the ready lock and handoff
  are published and independently checked;
- `formal_execution_authorized = false`;
- draft v0.6 reviewed/frozen: false/false;
- interface, positive reference, and RP wrapper: null/null/null;
- evidence ledger tail: `EV-0016`;
- tokenizer/checkpoint/model/GPU/prefill/generation/scoring operations in this
  authority round: zero; and
- research question answered: false.
