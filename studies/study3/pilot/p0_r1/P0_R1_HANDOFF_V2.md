# P0-R1 cross-session handoff, generation 2

> **Continue from the published generation-2 ready commit below. Do not return
> to the baseline of the authority's §1, and do not launch generation 1.**

Authority:
[`../../prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md`](../../prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md),
over
[`../../prompts/study3_v0_6_p0_r1_authority.md`](../../prompts/study3_v0_6_p0_r1_authority.md)
and
[`../../prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md`](../../prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md).

This supersedes [`P0_R1_HANDOFF.md`](P0_R1_HANDOFF.md), which remains in place,
unedited, as the generation-1 historical record.

## 0. Generation 1 is superseded without consumption and cannot be launched

The generation-1 image and lock are **unconsumed historical objects**. They are
**superseded and inert for execution**. They record a real model-free
implementation round and their bytes are preserved, but they must not be
started, retagged, relabelled as an executed attempt, or treated as a spent
envelope.

| generation-1 object | value |
| --- | --- |
| lock | `studies/study3/pilot/p0_r1/p0_r1_execution_lock.json`, 10,728 bytes, sha256 `f0e0e6b609091adeb063893687659b0df3e919135c11b8e977575f15bec26c40` |
| image | `…/j-space-observation-study3-p0-r1@sha256:7e2690feb6854a53f096d5b321e69fddebd2b744289c760e2fe74ed1ccec8176` |
| executable code commit | `aad14c45e9681a34f382aa95c55ac875d2ca98ce` |
| launchable | **no** |
| consumed | **no** |
| executions, GPU allocations, tokenizer constructions, encodes, checkpoint downloads, model weight loads | 0, 0, 0, 0, 0, 0 |

Why it cannot be launched: its Container Apps job command was
`/workspace/p0_r1_model_pilot.sh`, which is not a path in that image; its entry
point defaulted `SRC` to `/workspace/src`, which exists only when an ACR task
mounts a checkout and never in a GPU job; and an `az acr run` context mount
shadows `/workspace` entirely. Superseding it **does not** consume, re-arm,
duplicate or add an execution envelope. Exactly **one** P0-R1 replay attempt
and, only after a pass, **one** bounded model-operating GPU job remain
authorized overall.

## 1. What the successor session inherits

| item | value |
| --- | --- |
| entry state | `STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE` (generation 2) |
| **ready commit** | `c7e02b43e1dbf811d1b35ae0fc0fe9d1a1d12947` |
| **ready tree** | `dc972850dccbd80c54abd74c4c99a7acf54a1103` |
| **executable code commit** | `863aca8b3a2ac73d9e8c031f762bda6fae125059` |
| **executable code tree** | `f48f577fa008d3e0ecfabff281bdae2e4a14a6b0` |
| **image** | `acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r1@sha256:5f964edb414b8a22682693d8314063693daca3b915398094ec008d2c03308827` |
| image tag (convenience only; the digest is authoritative) | `g2-863aca8b3a2a` |
| base image | `pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime@sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126` |
| **active lock** | `studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json`, 26,172 bytes, sha256 `f506f632b8602cc000229b9a40991fc666cf0cf9f0195712cfe93d12fbee4714` |
| lock schema | `studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.schema.json`, `study3-p0-r1-execution-lock-v2` |
| bound executable paths | 42 (20 generation-1, unchanged, plus 22 generation-2) |
| post-ready authority | `studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md`, 30,706 bytes, sha256 `5594e9728e8e4eb14635c34fb4895e65f2a8fa152ff2bffe76aec33a3ea84d18` |
| standalone source root in the image | `/opt/jspace/src` (no `/workspace` mount dependency) |
| candidate | draft-v0.6, `studies/study3/protocol/interface_calibration_rendering_registry_v0_6.json` |
| corpus | the frozen 35-cell / 70-member P0 corpus, reused byte-exactly |
| execution flag | `p0_r1_pilot_execution_authorized = true`, **not yet consumed** |
| every other authority flag | false; `interface_selected`, `positive_reference` and `rp_wrapper` are **null** |

The lock binds two distinct commits on purpose: the **executable code commit**
the image was built from, and the later **ready commit** that carries the lock.
A digest cannot be embedded in the image whose digest it defines, so the lock is
necessarily the later object. No executable byte changed after the build.

## 2. The transport canaries that make this generation different

All three ran model-free on the real infrastructure, in Azure Container Apps
execution **`job-jspace-s3-p0r1-canary-g2-kqpquxz`** (job
`job-jspace-s3-p0r1-canary-g2`, `Consumption` CPU profile, image pinned by the
digest above). Their receipts are inside the active lock.

| canary | result |
| --- | --- |
| `standalone_layout` | `P0_R1_STANDALONE_LAYOUT_OK=1`; root `/opt/jspace/src`; 17 required source paths; 3 installed entry points; `depends_on_the_acr_workspace_mount false` |
| `replay_transport` | `P0_R1_TRANSPORT_SELF_CHECK=1`; 4 artifacts, 2,053 lines, max line 945 bytes, 1,048,576 bytes encoded, recovered byte-exact |
| `private_blob` | `P0_R1_BLOB_CANARY_COMPLETE=1`; prefix `study3/p0_r1/gen2/gen2canary-863aca8b3a2a/`; 4 objects × 262,144 bytes plus the manifest, written last; read back byte-exact; no overwrite |

**A prior canary execution failed, and that matters.** Execution
`job-jspace-s3-p0r1-canary-g2-56y38fa`, against the now-discarded image
`sha256:928dc59b…`, failed with `ModuleNotFoundError: No module named 'azure'`
and wrote zero objects. That image passed every build gate it had, because its
transport gate ran against an in-memory backend. **A hash is not a byte.**
Printing a sha256 of an artifact proves nothing about whether the artifact can
ever be fetched again. The current image is gated on constructing the real
managed-identity client, and the durable route is exercised end to end above.

## 3. The exact first command

The registered **live replay gate** is the first action, and nothing else may
precede it. Use the successor wrapper, which refuses ambiguous defaults:

```
studies/study3/pilot/p0_r1/container/p0_r1_successor.sh preflight \
  --lock-file studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json \
  --image-digest sha256:5f964edb414b8a22682693d8314063693daca3b915398094ec008d2c03308827
```

`preflight` is model-free, consumes nothing and is safe to repeat. Then, and
only in a fresh session that has decided to spend the one-shot envelope:

```
studies/study3/pilot/p0_r1/container/p0_r1_successor.sh live-replay \
  --lock-file studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json \
  --image-digest sha256:5f964edb414b8a22682693d8314063693daca3b915398094ec008d2c03308827 \
  --ready-commit c7e02b43e1dbf811d1b35ae0fc0fe9d1a1d12947 \
  --confirm-consumes-the-one-shot-replay-envelope
```

**This is not a dry run.** It runs the registered gate through
`p0_r1_acr_task_v2.yaml` / `p0_r1_replay_v2.sh` and consumes the one-shot replay
envelope. It performs zero tokenizer constructions, zero encodes, zero
checkpoint downloads, zero model loads and zero GPU operations.

## 4. Recovering the replay bytes from the log, not from the console

The gate emits its canonical artifacts as a **complete-byte log envelope**:
every artifact is chunked, hashed, indexed and terminated by a manifest line.
Reconstruct from the captured ACR log; never rerun the gate to "get the output
again".

```
python studies/study3/pilot/p0_r1/p0_r1_transport.py \
  --recover --log <the captured acr run log> --out-dir <dir>
```

The decoder tolerates harmless Azure log prefixes, reordering and duplicate
identical lines, and refuses a missing chunk, a conflicting duplicate, an
unknown artifact, path traversal, a wrong attempt, a wrong count, or any hash or
byte mismatch. Recovery is verified against the manifest before any pass is
authorized.

The GPU pilot's artifacts are recovered from the **private object store**, which
is the primary durable record for that stage:

```
python studies/study3/pilot/p0_r1/p0_r1_blob_transport.py \
  --recover --attempt <the gen2-… attempt id> --out-dir <dir>
```

This fetches every object under the attempt prefix, checks each one against the
manifest written last, and refuses on any mismatch. The console log is a
secondary record, never the sole one.

## 5. Pass and fail boundary

The gate writes `p0_r1_replay_result.json`, `p0_r1_replay_receipt.json`,
`p0_r1_replay_counters.json` and `P0_R1_REPLAY_DISPOSITION.md`.

* **Pass** requires the derived factorization to reproduce the registered
  identity with zero tokenizer encodes, and every recovered artifact to match
  its manifest hash and byte count exactly.
* **Any** hash mismatch, missing chunk, counter disagreement or unrecoverable
  artifact is a **fail**. On fail: stop, publish the failure, and perform **no**
  model operation.

## 6. The model-operating launch, only after a pass

```
studies/study3/pilot/p0_r1/container/p0_r1_launch_gpu_pilot_v2.sh \
  --image-digest sha256:5f964edb414b8a22682693d8314063693daca3b915398094ec008d2c03308827 \
  --ready-commit c7e02b43e1dbf811d1b35ae0fc0fe9d1a1d12947 \
  --lock-file    studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json \
  --receipt-file <the receipt recovered from the passed gate> \
  --confirm-single-model-operating-execution
```

Every argument is mandatory. The lock and receipt are **injected into the
container as exact, size-checked bytes**; the image cannot contain the lock,
because the lock postdates the digest it binds. The launcher validates both
before any Azure command, queries the exact job name's execution history and
**refuses if any execution already exists**, and sets `replicaRetryLimit = 0`,
`parallelism = 1`, `replicaCompletionCount = 1`. It never deletes an execution
to make the count look like zero.

Job name: `job-jspace-study3-p0-r1-pilot-g2`. It **does not exist yet**, and
that is the invariant the "refuse if any execution exists" check depends on.

## 7. The Blob prefix rule

Every artifact is written under a unique, attempt-bound prefix:

```
study3/p0_r1/gen2/<attempt-id>/
attempt-id = gen2-<executable-commit[:12]>-<UTC %Y%m%dT%H%M%SZ>
```

* The prefix is proved unused **before** the attempt starts.
* No object is ever overwritten; overwrite is refused, not merely avoided.
* The manifest object is written **last**, so a truncated attempt is detectable
  rather than silently plausible.
* Every object is read back through the same route and compared byte-for-byte
  before the attempt may report success.
* Account `stjspacefiles0709085305`, container `jspace-results`, reached over
  **managed identity only**. No key, SAS or connection string is baked, read or
  printed; their mere presence in the environment refuses the route.

## 8. If the pilot fails part-way

Partial results are preserved, never discarded:

* the journal records each irreversible step before it happens, so a crash
  cannot make a possibly-started operation look like a zero-event non-attempt;
* on any exception, the artifacts produced so far are still written, still
  persisted and still read back, and the degradation is **published** rather
  than swallowed;
* a summariser failure never discards the rows it could not summarise;
* a failure of the primary journal sink fails closed; a mirror failure is
  recorded as `durable_mirror_degraded` and does not destroy the attempt;
* the conservative report treats missing or ambiguous evidence as
  nonzero/unknown.

**No automatic retry, platform retry, output-conditioned retry, row
replacement or re-arming is authorized.** One further infrastructure attempt is
possible only after a separate operator decision, and only when recovered,
byte-valid evidence demonstrates zero tokenizer constructions, encodes,
checkpoint accesses, model loads, forward passes, prefills, decodes,
generations, parser calls and scored rows.

## 9. Terminal publication boundary

The successor stops after publishing the terminal P0-R1 disposition. It does
**not** begin the final focused methods review, select an interface, set a
threshold, pass a formal gate, resolve OD2 or UR-22, freeze anything, or add an
evidence-ledger row. The ledger still ends at **EV-0016**.

## 10. What this round did not do

No live replay gate was run. No tokenizer was constructed and nothing was
encoded. No checkpoint was downloaded or loaded. No GPU job was created,
allocated or started. No model operation was performed. The one-shot envelope
was neither consumed nor re-armed. The final focused methods review has not
begun.
