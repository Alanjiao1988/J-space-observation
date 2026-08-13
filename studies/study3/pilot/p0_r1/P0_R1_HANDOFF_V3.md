# P0-R1 cross-session handoff, generation 3

> **Entry state:** `STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE`.
>
> Generation 3 is execution-ready but unconsumed. Run only the model-free
> `preflight` command below on entry. Do not run `live-replay` without a new,
> explicit operator decision, and never create or start the GPU job before a
> captured replay pass and its independent reconstruction have been published.

This handoff supersedes `P0_R1_HANDOFF.md` and `P0_R1_HANDOFF_V2.md` for
execution. Both earlier handoffs and locks remain byte-identical historical
records. Their generations are unconsumed, superseded, and not launchable.

## Active generation-3 identities

| item | exact value |
| --- | --- |
| executable commit | `db0403381ab68073d497df370197ffbb5bd4ba10` |
| executable tree | `512f2afe857a8a1012f8cfd6ebad91e7da9851e5` |
| ready anchor | `0ecb90854ac1e9928a2728493af0678e757810ee` |
| ready-anchor tree | `cf522e57ee5d1b2e0cbf2e1ae5ccf2324ace3495` |
| ready-anchor parent | executable commit above |
| image | `acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r1@sha256:e1adda95862ea14bf0397f496aa0ef9f7e5918e95b5436b0eb84ee3480d91e4c` |
| image build | ACR run `cmh5`; tag `gen3-db0403381ab6` |
| base image | `pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime@sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126` |
| active lock | `p0_r1_execution_lock_v3.json`, 31,025 bytes, sha256 `f219a472705dec4e5c590614d392f39c9ec672d45397471632ad951d69097794` |
| lock schema | `p0_r1_execution_lock_v3.schema.json`, 1,224 bytes, sha256 `c5fcc19ebc234377f0d6b0281766678a1d109a18275e3c59f66f365118d8716a` |
| canary receipt | `p0_r1_canary_receipts_v3.json`, 8,623 bytes, sha256 `d83ee2c91cfaeaaa0270198d32cd560092b80fff76982e2953aff1944cf0c1c1` |
| bound executable paths | 43; each matches the executable commit's Git blob |
| generation-3 GPU job | `job-jspace-s3-p0r1-pilot-g3`, proved absent |
| CPU recovery job | `job-jspace-s3-p0r1-recover-g3`, `Consumption` |

The lock records the anchor's parent rather than its own future commit hash.
At preflight, `p0_r1_ready_anchor_v3.py` resolves the direct first-parent child,
requires that commit to carry the exact injected lock blob, and then proves
anchor-to-published-head ancestry, governance-only descendants, an empty
worktree, and no bound-byte drift.

## Authorities

| authority | bytes | sha256 |
| --- | ---: | --- |
| `study3_v0_6_p0_r1_authority.md` | 19,632 | `f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200845ddc19d2` |
| `study3_p0_r1_pre_replay_execution_completion_authority_rev2.md` | 23,486 | `ffe75ba42c023e959f3beb23927604c3ae72c07fb4b25be346f504c8ea2930de` |
| `study3_p0_r1_post_ready_transport_exception_safety_authority.md` | 30,706 | `5594e9728e8e4eb14635c34fb4895e65f2a8fa152ff2bffe76aec33a3ea84d18` |
| `study3_p0_r1_generation3_execution_closure_authority.md` | 32,068 | `debdece69a5441c8a63de680293b9969d79c27bb4012a93786fcbd14128697fd` |

## Model-free production canaries

Every passing canary used the digest-pinned image above. The exact receipts,
raw-log identities, failed/discarded runs, prefixes, object hashes, and all-zero
model counters are embedded in the active lock.

| canary | production identity | result |
| --- | --- | --- |
| non-root standalone layout | build `cmh5`; ACA `job-jspace-s3-p0r1-canary-g3-rmyr8v9` | `/opt/jspace/src`; runtime root writable as UID 10001 |
| exact shell/CLI injection | `job-jspace-s3-p0r1-cli-canary-g3-d9h2uxv` | four exact input envelopes reconstructed; sentinel reached once; EXIT trap completed |
| exact ACR task capture/recovery | ACR `cmh6` | 4 × 262,144-byte synthetic artifacts; 1,048,576 bytes recovered from the raw log; live gate false |
| image/Git byte audit | ACR `cmh7` | 79/79 image blobs equal `db04033:path`; no result bytes |
| private prefix | `job-jspace-s3-p0r1-recover-g3-vvaeb2a` | `PROVED_ABSENT`; zero objects/collisions |
| private Blob journal | `job-jspace-s3-p0r1-canary-g3-rmyr8v9` | five complete journal objects; recursive manifest written last |
| hard kill | same execution | child `-9`; exact row and open admission recovered; classified partial; retry unauthorized |
| CPU managed-identity recovery | `job-jspace-s3-p0r1-recover-g3-irp4giq` | five journal and six recursive objects verified, sequence continuous, manifest last |

No canary ran the replay gate. No tokenizer was constructed or called, no
checkpoint was accessed or loaded, no model weight was loaded, no GPU workload
was allocated, no model operation was performed, and no one-shot envelope was
consumed.

## Authoritative validation

Clean exact-commit CPU-only ACR validation ran against the ready anchor:

| run | scope | result |
| --- | --- | --- |
| `cmh8` | `tests/test_study3_p0_r1_generation3_execution_closure.py` | 74 passed; `BOUND_COMMIT=0ecb908…`, `BOUND_TREE=cf522e57…`, `DIRTY=0` |
| `cmh9` | full repository suite | **4,585 passed, 15 skipped, 2 failed**; only the two registered historical `test_parser_v3_seal_job` failures; `FULL_SUITE_ACCEPTED_HISTORICAL_FAILURES_ONLY=1` |

The retained raw logs hash to:

- `cmh8`: 3,020 bytes, sha256
  `f8eb9a00718ca93bb1fb0f585d40942c2304919d3a70a62e8f19b2637b8bc71a`;
- `cmh9`: 12,386 bytes, sha256
  `b9f0a734137575ee45bcca458f140c74c7cc49f18acebe5bae20a479ee51299d`.

## Exact first command

From a fresh checkout of the final published `origin/main`, with no local
changes:

```bash
bash studies/study3/pilot/p0_r1/container/p0_r1_successor_v3.sh preflight \
  --lock-file studies/study3/pilot/p0_r1/p0_r1_execution_lock_v3.json \
  --image-digest sha256:e1adda95862ea14bf0397f496aa0ef9f7e5918e95b5436b0eb84ee3480d91e4c \
  --work-dir <new-empty-preflight-directory>
```

This command is read-only and model-free. It must print:

```text
P0_R1_PREFLIGHT_COMPLETE=1
P0_R1_STATE=STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE
```

It also requires `HEAD == origin/main`, a clean status, the exact lock and image,
the ready anchor and bound-byte proof, generations 1 and 2 inert, and
`job-jspace-s3-p0r1-pilot-g3` proved absent. Any query error is a stop, never an
absence.

## The guarded one-shot sequence

Only after a new explicit decision to consume the replay half:

```bash
bash studies/study3/pilot/p0_r1/container/p0_r1_successor_v3.sh live-replay \
  --lock-file studies/study3/pilot/p0_r1/p0_r1_execution_lock_v3.json \
  --image-digest sha256:e1adda95862ea14bf0397f496aa0ef9f7e5918e95b5436b0eb84ee3480d91e4c \
  --work-dir <new-empty-replay-directory> \
  --i-am-sure
```

That transaction builds its context from committed Git objects, captures one
ACR run ID and the complete raw log, independently reconstructs the four
artifacts, and never rewrites the emitted receipt. On any replay or capture
failure, publish the stop and perform no model operation. Never rerun the gate.

Only after the raw log, emitted receipt, reconstruction receipt, and current
head proof have been published may the same successor invoke:

```bash
bash studies/study3/pilot/p0_r1/container/p0_r1_successor_v3.sh launch-pilot \
  --lock-file studies/study3/pilot/p0_r1/p0_r1_execution_lock_v3.json \
  --work-dir <new-empty-pilot-directory> \
  --replay-receipt <published-p0_r1_replay_receipt.json> \
  --reconstruction-receipt <published-p0_r1_replay_reconstruction_receipt_v3.json> \
  --head-proof <current-p0_r1_head_proof_v3.json> \
  --i-am-sure
```

The launcher runs the CPU private-prefix preflight before creating the GPU job,
creates a digest-pinned manual job with `replicaRetryLimit=0`, captures and
monitors exactly one execution, and always runs CPU-only Blob recovery after the
terminal status. It never updates a stale GPU job into compliance.

## Legal and scientific boundary

- `p0_r1_pilot_execution_authorized = true`, unconsumed;
- `formal_execution_authorized = false`;
- draft v0.6 is neither reviewed nor frozen;
- interface, positive reference, and RP wrapper remain `null`;
- OD2 and UR-22 remain unresolved;
- the evidence ledger still ends at `EV-0016`;
- the research question remains unanswered;
- all 31 pre-execution counters are zero;
- exactly one overall replay-then-conditional-pilot envelope remains.

This publication did not run the live replay gate, create or start the
generation-3 GPU job, select an interface, set a threshold, freeze a draft, or
add an evidence row.
