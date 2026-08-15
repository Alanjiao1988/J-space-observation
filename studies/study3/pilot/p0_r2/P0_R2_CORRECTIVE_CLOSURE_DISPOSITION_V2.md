# P0-R2 corrective closure: live replay submission stop, generation 1 revision 2

**State:** `P0_R2_CORRECTIVE_CLOSURE_STOP_NO_REPLAY`

**No model operation was performed. No GPU job was created or started. No
canonical replay artifact exists. The replay envelope is unconsumed.**

## What happened

Segment A completed and was published. The inter-segment gate was recomputed
from a fresh short-path checkout of the published head
`7cc795de6682c07828630255ac515683bc7697e4`, and all twenty-eight registered
admission conditions evaluated true from evidence:

```text
P0_R2_PHASE_B_AUTHORIZED=1
conditions 28, failed 0, underived 0
```

The Phase-B admission proof was published as a governance-only commit and
re-proved from another fresh checkout, so the admission commit is covered by the
proof it claims.

Every B1 pre-invocation check then passed, immediately before the call:

| check | result |
| --- | --- |
| `HEAD` = `origin/main` = admitted head | `7cc795de6682c07828630255ac515683bc7697e4` |
| worktree clean | yes |
| v2 host preflight | all ten markers, exactly once each |
| live attempt prefix `p0r2-g1-live-20260815-0800` | `PROVED_UNUSED`, 0 objects, in-VNet |
| `job-jspace-s3-p0r2-pilot-g1` | `PROVED_ABSENT` |
| `job-jspace-s3-p0r2-recover-g1` | `PROVED_ABSENT` |
| pre-replay counters | all thirteen zero |
| `acrctx` rebuilt from committed Git objects | 2 entries, 41-character maximum native path |
| context entries | exactly `task.yaml` and `context_manifest.json` |
| context embeds authority, lock and admission bytes | verified by length and SHA-256 |
| image pinned by the active digest | `sha256:eb0e284c…` |
| guard | `P0_R2_HOST_SUBMISSION_GUARD_PROVED=1` |

The guarded wrapper then attempted the single authorized live submission, and
**the host could not launch the Azure CLI**:

```text
Azure CLI invocation failed locally: [WinError 2] the system cannot find the specified file
P0_R2_HOST_SUBMISSION_REFUSED=1 ACR submission stopped with exit code 127
```

## Why the envelope is unconsumed

The failure is a `CreateProcess` failure. The `az` program image was never
loaded, so no process existed, no request was formed and nothing left the host.
That is not an inference; it is proved from both sides.

| evidence | value |
| --- | --- |
| exception | `OSError` raised by `subprocess.run` itself, before any process started |
| exit code | `127`, the module's synthetic could-not-launch code |
| captured stdout | **0 bytes**, sha256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — the SHA-256 of the empty string |
| captured stderr | 84 bytes, sha256 `db7917dea51123073bcafbe8ee139be15929b8579f28f7c0b18183bb4aba12e9` |
| ACR run id returned | none |
| newest ACR run in the registry, after the attempt | `cmju`, created 09:55:11Z — the packing canary, hours earlier |
| live attempt prefix after the attempt | still `PROVED_UNUSED`, 0 objects |
| canonical replay artifacts | absent |
| retained submission receipt outcome | `STOP` — "the retained receipt authorizes nothing" |

The registered rule is that the envelope is consumed "when the authorized Azure
CLI live submission is invoked, even if failure occurs before an ACR run ID is
returned". That rule exists so that a failure *after* a request reaches Azure
cannot be retried, because a retry might duplicate a real submission. Here the
CLI was never invoked: the operating system refused to start it, and Azure's own
control plane confirms no run was created.

## The defect, stated exactly

`p0_r2_acr_submission._default_runner` already resolves the program the way a
shell would:

```python
program = shutil.which(command[0]) or command[0]
```

with the comment that "subprocess does not apply PATHEXT, so a bare `az` cannot
be launched on Windows, where the Azure CLI ships as `az.cmd`".

The guarded wrapper `p0_r2_host_submission_v2.py` needs its own runner for one
reason only: to scope `P0_R2_LIVE_REPLAY_AUTHORIZED=1` to exactly one child
process rather than exporting it globally. Its first version passed the bare
command straight to `subprocess.run`, and in doing so **silently reintroduced
the exact bug the module had already fixed — in the one code path that spends an
unrepeatable envelope**.

This is a defect introduced by the corrective closure itself, not an inherited
one. It is recorded here rather than quietly repaired, because a one-shot
envelope is the last place a silent repair belongs.

The wrapper now resolves the program the same way the module does, and a
regression test asserts that both do, that the wrapper's resolution happens in
the same function that builds the child environment, and that it happens before
the submission call.

## Why this stops rather than retries

Two things are true at once, and both matter:

1. The envelope's substance is provably unspent. No submission reached Azure.
2. The registered rule speaks in terms of *invocation*, and the correct reading
   of a rule that protects an unrepeatable object is not a reading chosen by the
   party whose own defect caused the failure.

Repairing the launch path and immediately re-invoking would also be, on the
plainest reading, "repairing the gate in place" — which this stage is forbidden
to do. So the stage stops here and reports, with the evidence above, rather than
deciding its own case.

What a successor needs in order to proceed is not new work. It is one operator
decision: whether a submission that the operating system refused to start, and
that Azure's control plane confirms never existed, leaves the one-shot envelope
spendable. If it does, the corrected wrapper invokes it once. If it does not,
the envelope is spent and P0-R2 ends here without a model operation.

## State this disposition leaves behind

- corrective authority: published and bound;
- v2 closure: sealed, proved, and re-proved from two independent fresh
  checkouts;
- Phase-B admission: `phase_b_authorized = true`, 28/28, published and covered;
- replay envelope: **unconsumed**;
- canonical P0-R2 replay artifacts: **absent**;
- `job-jspace-s3-p0r2-pilot-g1`: **absent**, never created;
- `job-jspace-s3-p0r2-recover-g1`: **absent**, never created;
- live and pilot attempt prefixes: both `PROVED_UNUSED`, zero objects;
- P0-R1: terminal, unchanged, zero bytes touched;
- tokenizer constructions, encodes, checkpoint downloads, model weight loads,
  prefills, generations, scored rows, GPU operations: **all zero**;
- `formal_execution_authorized = false`; draft v0.6 unreviewed and unfrozen;
  interface, positive reference and RP wrapper `null`; evidence ledger tail
  `EV-0016`; research question unanswered.
