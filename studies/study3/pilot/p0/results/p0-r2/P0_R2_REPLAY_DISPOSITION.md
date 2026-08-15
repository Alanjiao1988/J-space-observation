# P0-R2 generation-1 live replay disposition

**State:** `STOP_NO_MODEL_OPERATION`

**Reason class:** `REPLAY_REFUSED_BEFORE_GATE_ON_PRIVATE_LISTING_UNREACHABLE`

The one-shot replay envelope is **consumed**. It was invoked exactly once, it
returned exactly one ACR run id, and it failed closed before the replay gate
ran. No model operation was performed and no canonical success artifact exists.

## Identities

| item | exact value |
| --- | --- |
| attempt | `p0r2-g1-live-20260815-0800` |
| ACR run id | `cmjv` |
| run status | `Failed`, `exit status 1` |
| started / finished | `2026-08-15T14:25:01.011923+00:00` / `2026-08-15T14:30:48.833585+00:00` |
| submitted head | `a7fb84e56826d1cc9d412d9becd350f2043a48c9` |
| image executable | `c9344c52bfbacc4f2a24010fffa534a940104140` |
| image | `…study3-p0-r2@sha256:eb0e284c6b420aa4992dcdee9a43b9cb92a96937499bca605f96b141619e9b58` |
| ready anchor | `7ff6700621ca1db9bdf06d1d91a49e935e66e2b7` |
| raw log | 7,334 bytes, sha256 `48e87c66d011f5218b91e7e477d258e102c995160d43e8ae83b3f3f93e9b2364` |
| stderr | 370 bytes, sha256 `b166c3d20c55c16f6ea2e896609b13a8b05af5d574b45d3342efdb13f555b64c` |

## What the run proved before it refused

The container got further than any P0-R2 run had before, and everything it
checked passed:

```text
P0_R2_IMAGE_TO_GIT_AUDIT_V2_COMPLETE=1     44 bound bytes, 0 mismatches
P0_R2_LOCK_FROM_CONTEXT_BYTES=158754
P0_R2_LOCK_FROM_CONTEXT_SHA256=f3bf629998ffde67fc0e140539cfb4156db78533f90154cfe02f291e0a1be4f6
P0_R2_LOCK_FROM_CONTEXT_VERIFIED=1
```

The corrected replay path worked exactly as designed: the image carried exactly
the bytes Git holds, and the active lock was taken from the submitted two-file
context and verified by length and SHA-256 rather than read from an
`/opt/jspace` path no Dockerfile ever wrote.

## Why it refused

```text
ImdsCredential.get_token failed: No token received.
ManagedIdentityCredential.get_token failed: No token received.
P0_R2_PREFIX_PREFLIGHT_REFUSED=1 the private listing failed (Bad Gateway
ErrorCode:None); a query error is never an absence
```

`p0_r2_replay_v2.sh` runs `p0_r2_prefix_preflight_v1.py` inside the container
before the gate. That module requires a **managed-identity** client against the
private results account, and it refuses rather than treating a failed listing as
an absence — which is correct, and is exactly the rule the whole stage is built
on.

But an **ACR Tasks agent has no managed identity and is not inside the VNet**.
It cannot obtain a token and cannot reach `stjspacefiles0709085305`, whose
`publicNetworkAccess` is `Disabled` and whose `defaultAction` is `Deny`. So the
step could not succeed there, and the guard did the only honest thing available
to it.

### The defect this reveals

The design already knew this. The packing-canary branch of the same script
deliberately skips the prefix proof and says so:

```text
P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1
```

with the comment that the probe "needs Azure credentials that this task is not
granted, and a probe that cannot reach the control plane can only report
ambiguity, never absence. It is run from the host, where the credentials exist,
as its own canary."

The **live** branch does not defer it. It calls the same in-VNet-only probe on
the same credential-less agent. That asymmetry is a v1 defect inherited by the
corrective closure, and it is the fifth latent defect this work has surfaced —
the only one that could not be found without spending the envelope, because the
only way to learn whether an ACR agent can reach the private account is to make
it try.

The prefix *was* proved unused, correctly, from inside the VNet, four separate
times before and after this run — most recently by ACA execution
`job-jspace-s3-p0r2-prefix-g1-4ka7hkj`, after the consumed replay, still
`PROVED_UNUSED` with `object_count 0`.

## Independent reconstruction

Attempted with the strict P0-R2 decoder against the complete captured log:

| item | value |
| --- | --- |
| decoder | `p0_r2_transport_v1.recover_with_report`, strict decoder first |
| refusal | "the captured log carries no `study3-p0-r2-transport-envelope-v1` envelope" |
| envelope markers in the log | **0** |
| artifacts recovered | **0** of 4 |
| checksum-proved repairs applied | 0 |
| `P0_R2_REPLAY_GATE_RUN=true` | absent |
| `P0_R2_REPLAY_COMPLETE=1` | absent |

The gate never ran, so it emitted nothing, so there is nothing to reconstruct.
`p0_r2_replay_result.json` and `p0_r2_replay_receipt.json` are **not created**:
recovered bytes do not prove them, and a canonical success artifact that is not
proved by recovered bytes is a fabrication.

## Counters

```text
live_replay_invocations       1
acr_run_ids_returned          1
replay_gate_invocations       0
one_shot_envelope_consumed    true
tokenizer_constructions       0
tokenizer_encodes             0
checkpoint_downloads          0
checkpoint_loads              0
model_weight_loads            0
prefills                      0
generations                   0
scored_rows                   0
evidence_rows_added           0
gpu_allocations               0
gpu_operations                0
pilot_executions_started      0
model_operations_performed    0
```

## Consequences

The replay-pass conditions are not met: the replay result is not the registered
pass outcome, the four canonical artifacts did not reconstruct, and strict
receipt validation has nothing to validate. Therefore, under the registered
rule:

- **no GPU pilot is authorized, created or started**;
- **the replay is not rerun, regenerated, or substituted**;
- **the gate is not repaired in place**;
- **no second `az acr run --live` is invoked**.

P0-R2 generation 1 ends here at `STOP_NO_MODEL_OPERATION`, with its envelope
spent and its evidence complete.

## What a successor inherits

Not a mystery, and not a repair job disguised as one. The corrected closure, its
proofs, its canaries and its ledger all stand and are unaffected by this
outcome. The single blocking defect is precisely located and one line wide in
intent: **the live branch of `p0_r2_replay_v2.sh` must not call the in-VNet
prefix preflight on a credential-less ACR agent.** The host already proves that
prefix in-VNet, and the packing-canary branch already models the correct
behaviour.

A successor generation — which requires a new operator authority, because this
generation's envelope is spent — should either defer the prefix proof to the
host on the live path exactly as the canary path does, or run the live replay
somewhere that actually holds the managed identity, such as a Container Apps job
in `cae-jspace-observation-sea-vnet2`, which is where every successful
managed-identity operation in this stage has run.

## State this leaves behind

- P0-R1: terminal, unchanged, zero bytes touched;
- P0-R2 v1 closure: preserved, superseded, zero bytes edited;
- P0-R2 v2 closure: sealed, proved, and re-proved from independent fresh
  checkouts;
- replay envelope: **consumed**, exactly one invocation, exactly one run id;
- canonical replay success artifacts: **absent**, deliberately;
- `job-jspace-s3-p0r2-pilot-g1`: **absent**, never created;
- `job-jspace-s3-p0r2-recover-g1`: **absent**, never created;
- GPU workload profiles used by this stage: **none**;
- `formal_execution_authorized = false`; draft v0.6 unreviewed and unfrozen;
  interface, positive reference and RP wrapper `null`; evidence ledger tail
  `EV-0016`; research question unanswered.
