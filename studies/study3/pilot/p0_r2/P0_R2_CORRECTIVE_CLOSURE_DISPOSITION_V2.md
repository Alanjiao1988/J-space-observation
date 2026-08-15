# P0-R2 corrective closure disposition, generation 1 revision 2

This file records the whole sequence, including the attempt that never reached
Azure. It is updated in place as the stage progresses, and every earlier fact in
it stays.

## Segment A — complete

All four registered closure defects were reproduced read-only before anything
changed, and are retained in `p0_r2_corrective_admission_audit_v2.json`.

The corrected closure is sealed and proved. The host preflight prints each of
its ten required markers exactly once from a fresh clean checkout, and the
governance-chain proof records zero paths changed after the anchor, zero
image-bound drift, zero host-closure drift and zero P0-R1 protected-path
changes across all nine identities it keeps apart.

Four latent defects were found by building the correction, each of which would
have fired on an invocation that cannot be retried:

1. `p0_r2_replay_v1.sh` and `p0_r2_model_pilot_v1.sh` default their lock to
   `/opt/jspace/p0_r2_execution_lock_v1.json`, a path **no Dockerfile ever
   wrote**;
2. the registered CPU-only job shape leaves `NVIDIA_VISIBLE_DEVICES` and
   `NVIDIA_DRIVER_CAPABILITIES` set, inherited from the CUDA-capable base image,
   which the CPU-only guard correctly refuses — still latent in
   `p0_r2_recovery_job_v1.yaml`;
3. the v2 validator merged the image closure and the host closure, so adding a
   host-side tool after an image build looked like image drift;
4. the host preflight and the Phase-B admission gate both read a
   `ready_anchor_commit` field that the lock deliberately never sets.

All four are corrected. The second is corrected for this stage's own jobs and
**recorded rather than silently fixed** in the v1 recovery job shape, because
the pilot's recovery job must be created with the CUDA environment neutralised
or it will refuse after a terminal status.

## Inter-segment gate — 28/28

Recomputed from a fresh short-path checkout, with no reuse of the Segment A
worktree and no reuse of any in-memory conclusion drawn inside it:

```text
P0_R2_PHASE_B_AUTHORIZED=1
conditions 28, failed 0, underived 0
```

Every field is derived from Git, a published receipt, a read-only Azure answer,
or the host preflight's own transaction. There is no override and no way for a
caller to supply a condition's value. An underived condition is recorded false,
never unknown.

## Segment B, attempt 1 — the CLI was never invoked

Every B1 pre-invocation check passed. The guarded wrapper then attempted the
single authorized live submission and the host **could not launch the Azure
CLI**:

```text
Azure CLI invocation failed locally: [WinError 2] the system cannot find the specified file
P0_R2_HOST_SUBMISSION_REFUSED=1 ACR submission stopped with exit code 127
```

`WinError 2` from `subprocess.run` is a `CreateProcess` failure: the program
image was never loaded, so no process existed, no request was formed, and
nothing left the host.

| evidence | value |
| --- | --- |
| exception | `OSError` raised by `subprocess.run` itself |
| exit code | `127`, the synthetic could-not-launch code |
| captured stdout | **0 bytes**, sha256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| captured stderr | 84 bytes, sha256 `db7917dea51123073bcafbe8ee139be15929b8579f28f7c0b18183bb4aba12e9` |
| ACR run id | none |
| newest ACR run after the attempt | `cmju`, hours earlier |
| live attempt prefix after the attempt | `PROVED_UNUSED`, 0 objects, proved in-VNet |
| retained receipt outcome | `STOP` — "the retained receipt authorizes nothing" |

The diagnosis was then confirmed directly on the host:

```text
shutil.which("az")   C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.CMD
resolved launch      returncode 0
bare-name launch     OSError, winerror 2
```

### The defect, and whose it was

`p0_r2_acr_submission._default_runner` already resolved the program with
`shutil.which`, precisely because subprocess does not apply `PATHEXT` and the
Azure CLI ships as `az.cmd` on Windows. The guarded wrapper needs its own runner
for one reason only — to scope `P0_R2_LIVE_REPLAY_AUTHORIZED=1` to exactly one
child process instead of exporting it globally — and its first version passed
the bare command straight to `subprocess.run`, reintroducing the exact bug the
module had already fixed, in the one code path that spends an unrepeatable
envelope.

This defect was introduced by the corrective closure itself. It is fixed, and a
regression test asserts that both runners resolve the program the same way, that
the wrapper's resolution happens inside the same function that builds the child
environment, and that it happens before the submission call.

### Why the envelope was carried forward

The registered rule consumes the envelope "when the authorized Azure CLI live
submission is invoked, even if failure occurs before an ACR run ID is returned".
That rule exists so that a failure *after* a request reaches Azure — where a run
might exist whose id was never captured — cannot be retried, because a retry
might duplicate a real submission.

That hazard is provably absent here. The CLI was not invoked; the operating
system refused to start it, and Azure's own control plane confirms no run was
created. After the fix, the closure's own mechanical checks, rerun from a fresh
checkout, returned `P0_R2_REPLAY_ENVELOPE_UNCONSUMED=1`,
`the_replay_gate_has_never_run = true`, `its_blob_prefix_is_proved_unused = true`
and `phase_b_authorized = true` at 28/28.

The envelope was therefore carried forward rather than declared spent by a
host-side tooling failure that never reached Azure.

## Segment B, attempt 2 — outcome

Recorded in the sections appended after the invocation. Until that is written,
the state of this stage is unchanged: replay envelope unconsumed, canonical
replay artifacts absent, both bounded jobs absent, no model operation performed.
