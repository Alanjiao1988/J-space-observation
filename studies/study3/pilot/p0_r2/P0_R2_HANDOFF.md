# P0-R2 cross-session handoff, generation 1

> **Entry state:** `STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE`.
>
> Generation 1 is execution-ready but unconsumed. Run only the model-free
> `preflight` command below on entry. Do not run `live-replay` without a new,
> explicit operator decision, and never create or start the GPU job before a
> captured replay pass and its independent reconstruction have been published.

P0-R2 is an **infrastructure successor** to P0-R1, not a new experiment. P0-R1
generation 3 stopped permanently at `STOP_NO_MODEL_OPERATION` when the Azure CLI
failed host-side while packing a repository tree whose deepest native Windows
path was 265 characters. P0-R2 changes exactly one thing: the host-to-registry
submission transport. The science is the byte-identical P0-R1 generation-3
modules, delegated by verified SHA-256 identity through narrow wrappers.

This publication modified **zero bytes** of P0-R1. Its stop commit
`30806d793872a50e581d3252382b4a0ec2af3889` and its terminal state remain exactly
as published; P0-R1 is not reopened, and nothing here makes it launchable.

## Active generation-1 identities

| item | exact value |
| --- | --- |
| executable commit | `1eb3e21b408213cb183bd8d2f55c3554b9713160` |
| executable tree | `88d7e9a016772c4129f56637edd2d7fbd96b105b` |
| ready anchor | `7fd5fe57707461fcf70bfc9ab00b707b3c44ef71` |
| ready-anchor tree | `4fcb480c3479e001c93e73440aca036b74b0f472` |
| ready-anchor parent | executable commit above |
| image | `acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r2@sha256:3d857e54007d12bd943b383db522b913ba627a544b4d31b3e648eef30a65d8e7` |
| image build | ACR run `cmht`; tag `gen1-1eb3e21b4082` |
| base image | the P0-R1 generation-3 image, `sha256:e1adda95862ea14bf0397f496aa0ef9f7e5918e95b5436b0eb84ee3480d91e4c` |
| active lock | `p0_r2_execution_lock_v1.json`, 17,961 bytes, sha256 `2c9789e27fad5ac463e105a42a69d686cdcf1389bcfd44503baf79cabd61f7d7` |
| lock schema | `p0_r2_execution_lock_v1.schema.json`, 12,544 bytes, sha256 `44a0c1e6b50ec70b411d4a82f7e25c60002dca724fda1731c485991055a87d9d` |
| canary receipt | `p0_r2_canary_receipts_v1.json`, 7,915 bytes, sha256 `f3f1df213650ed02fbbc71f71938a6764c9bcf304273723e214f56d5a5acb0e7` |
| image manifest | `p0_r2_image_manifest_v1.json`, 12,790 bytes, sha256 `ab70d7ae34e78bff434e286aa8d1fe211112aa8e537099a5f8fed7360d5ff613` |
| bound image paths | 33; each matches the executable commit's Git blob |
| generation-1 GPU job | `job-jspace-s3-p0r2-pilot-g1`, proved absent |
| CPU recovery job | `job-jspace-s3-p0r2-recover-g1`, proved absent, `Consumption` |
| attempt namespace | `study3/p0_r2/g1/<attempt>/` in `jspace-results` on `stjspacefiles0709085305` |

The lock records the anchor's parent rather than its own future commit hash. At
preflight the anchor is proved by ancestry: the direct first-parent child of the
executable commit must carry the exact lock blob, and the anchor must be an
ancestor of the published head with governance-only descendants.

### The closure-binding cycle, and how it is resolved

`require_packing_canary` demands that a future live submission agree with the
designated packing canary on the source it submits. The canary necessarily runs
*before* the commit that contains the final lock exists, so a naive "same source
commit" rule is unsatisfiable. P0-R2 splits the single notion of "source commit"
into six identities — `executable_code`, `task_object`, `image`, `ready_anchor`,
`governance_source`, `published_head` — and requires canary and live submission
to agree on only the immutable subset:

`(executable_commit, executable_tree, task_path, task_blob, image, digest)`

`ready_anchor` is deliberately excluded, which is exactly why passing the
executable commit as the canary's anchor is honest rather than a workaround.

## Authorities

| authority | bytes | sha256 |
| --- | ---: | --- |
| `study3_p0_r2_infrastructure_successor_authority.md` | 11,288 | `eb2407216fcb48506b97b43a88d541ab27e857e72ef319cbf575799cf8451deb` |

The P0-R1 authorities remain in force for the delegated science and are recorded
in the P0-R1 generation-3 handoff.

## Model-free production canaries

Every passing canary used the digest-pinned image above, except where a question
could only be asked from inside the VNet. The exact receipts, raw-log
identities, prefixes, object names and all-zero model counters are embedded in
the active lock.

| canary | production identity | result |
| --- | --- | --- |
| designated packing canary | ACR `cmhv` | the exact step that stopped P0-R1 now succeeds: 2 context entries, **40-character** maximum native path against P0-R1's fatal **265**, 1.319 KiB sent, exit 0 |
| model-free preflight | ACR `cmhu` | 33/33 image blobs equal the executable commit's Git blobs, 0 mismatches; 1,048,576-byte transport round trip; 0 repairs |
| in-build image audit | ACR `cmht` | the build itself fails unless the image carries exactly the executable commit's bytes, so a drifted image could never have been pushed |
| managed-identity Blob round trip | ACA `job-jspace-s3-p0r2-canary-g1-2x3cpyj` | real managed-identity client against `stjspacefiles0709085305`; 4 × 262,144 B written and read back `recovered_byte_exact`; manifest written last |
| prefix preflight is not vacuous | same execution | `PROVED_UNUSED` on an unused prefix with `wrote_any_object: false`, then **REFUSED** on the same prefix once occupied |
| job absence is not vacuous | read-only control plane | the same query returns `PROVED_ABSENT` for both bounded pilot jobs and `PROVED_PRESENT` for the CPU-only canary job this stage did create |
| blob data-plane access | read-only control plane | the pilot identity holds a data-plane role covering the account the transport actually uses; the account the job spec previously advertised returns `AMBIGUOUS`, because it does not exist |
| GPU pilot job absence | read-only control plane | `job-jspace-s3-p0r2-pilot-g1` `PROVED_ABSENT` |
| CPU recovery job absence | read-only control plane | `job-jspace-s3-p0r2-recover-g1` `PROVED_ABSENT` |
| journal self-check | in-image | monotonic immutable sequences written and read back; a duplicate sequence is a defect, never a retry |

No canary ran the replay gate. No tokenizer was constructed or called, no
checkpoint was accessed or loaded, no model weight was loaded, no GPU workload
was allocated, no model operation was performed, and no one-shot envelope was
consumed.

### What was *not* reproduced

P0-R1 recorded a **hard-kill CPU recovery** canary. P0-R2 did **not** reproduce
it. The recovery path is implemented and its job shape is pinned, but no
generation-1 receipt exists for a killed child. This is stated rather than
claimed, and a successor should treat hard-kill recovery as unproven for P0-R2.

### Azure state this publication leaves behind

- Container Apps job `job-jspace-s3-p0r2-canary-g1` **still exists**. It is
  CPU-only (`Consumption`), requests no accelerator, and has
  `replicaRetryLimit 0`. It is disclosed here rather than quietly deleted
  because it is the evidence for the managed-identity canary above.
- Four canary objects, 1,048,576 bytes in total, remain under
  `study3/p0_r2/g1/p0r2-g1-blob-canary-20260815-0315/`. The pilot's attempt
  prefix is a different, unused prefix, and the preflight refuses any occupied
  one.

## Authoritative validation

Clean exact-commit CPU-only ACR validation, in the dependency closure the
repository itself registers in `requirements.lock.txt` (sha256
`570775850eb31b5a8613295fa6e9099400670408a6ce3a162dc6d9159dda87bf`, all 94
pinned packages verified present at exactly the pinned version):

| run | scope | result |
| --- | --- | --- |
| `cmj5` | `tests/test_study3_p0_r2_execution_closure.py` | **95 passed**; `BOUND_COMMIT=1eb3e21b…`, `BOUND_TREE=88d7e9a0…`, `DIRTY=0` |
| `cmj3` | full repository suite, **differential** | baseline `22ae685b…`: 4,625 passed, 15 skipped, 4 failed. Executable `1eb3e21b…`: **4,720 passed, 15 skipped, 4 failed**. `P0_R2_NEW_FAILURE_COUNT=0`; 0 collection errors; both checkouts `DIRTY=0` |
| `cmj6` | the published first command, end to end | `P0_R2_PREFLIGHT_COMPLETE=1` |

The full suite is **differential**: the same suite ran against the unmodified
baseline and the executable commit in one container, in one dependency closure,
and the two non-passing sets were compared rather than asserted. The set of
failures introduced by this change is empty, and the executable commit adds
exactly **+95** passing tests, which is precisely the closure suite `cmj5`
reports.

The retained raw logs hash to:

- `cmj5`: 4,193 bytes, sha256
  `1501208e0be8d3f5bc2ea0922c0ab0653d91fba9f9a2d844c9877b8dd0d2ba03`;
- `cmj3`: 5,841 bytes, sha256
  `890ad0b275533bedd89413a4f183955897f5ef677a93e1083c7e3e4867651052`.

### The registered historical-failure baseline is stale, by two

P0-R1 registered **two** historical failures. There are now **four**, at the
unmodified baseline as well as at the executable commit:

1. `test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix` —
   registered historical;
2. `test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last`
   — registered historical;
3. `test_phase05_jlens_saturation.py::test_no_artifact_asserts_a_prohibited_claim`
   — **not** registered; it passes on the authoring host and fails in the
   registered closure, so it is environment-dependent drift that post-dates
   P0-R1's `cmh9`;
4. `test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only`
   — **not** registered. Its eight offenders are P0-R1's own stop-disposition
   artifacts, committed with CRLF by `30806d7 "Publish P0-R1 generation-3 replay
   stop"`, which is the commit *after* `cmh9` and was therefore never covered by
   a full-suite run.

Failure 4 is **not repaired here**, and deliberately so: repairing it would
rewrite P0-R1 bytes, which this stage is forbidden to touch. It is recorded so
that a successor inherits a true baseline instead of a stale one.

## Exact first command

From a fresh checkout of the final published `origin/main`, with no local
changes. This command is read-only, model-free, and safe to repeat:

```bash
az acr run \
  --registry acrjspaceobssea0708231738 \
  --subscription 943bacdf-8b6e-4e3a-8126-a149f623d32e \
  --cmd 'acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r2@sha256:3d857e54007d12bd943b383db522b913ba627a544b4d31b3e648eef30a65d8e7 /usr/local/bin/p0_r2_successor_v1.sh preflight' \
  /dev/null
```

It must print:

```text
P0_R2_IMAGE_TO_GIT_AUDIT_COMPLETE=1
P0_R2_PREFLIGHT_COMPLETE=1
P0_R2_REPLAY_GATE_RUN=false
P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false
P0_R2_MODEL_OPERATIONS_PERFORMED=0
```

It proves module identity, verifies the delegated P0-R1 science by SHA-256,
audits all 33 image paths against Git, and round-trips 1 MiB through the
transport. Supplying an attempt id additionally proves the attempt prefix is
unused; without one the prefix check reports
`P0_R2_PREFIX_PREFLIGHT_SKIPPED=1` rather than pretending to have passed. Any
query error is a stop, never an absence.

## The guarded one-shot sequence

Only after a new explicit decision to consume the replay half:

```bash
P0_R2_LIVE_REPLAY_AUTHORIZED=1 \
P0_R2_REPLAY_MODE=live-replay \
  /usr/local/bin/p0_r2_successor_v1.sh live-replay
```

The entry point refuses without `P0_R2_LIVE_REPLAY_AUTHORIZED=1`, and the replay
script itself refuses an empty or unrecognised `P0_R2_REPLAY_MODE` rather than
falling through to the live path. That transaction builds its context from
committed Git objects, captures one ACR run id and the complete raw log,
independently reconstructs the four canonical artifacts, and never rewrites the
emitted receipt. On any replay or capture failure, publish the stop and perform
no model operation. Never rerun the gate.

Only after the raw log, emitted receipt, reconstruction receipt and current head
proof have been published may the same successor invoke:

```bash
P0_R2_PILOT_AUTHORIZED=1 \
  /usr/local/bin/p0_r2_successor_v1.sh launch-pilot
```

`launch-pilot` requires an authorization built from a completed replay. The
launcher runs the CPU private-prefix preflight before creating the GPU job,
creates a digest-pinned manual job on the `gpu-t4` workload profile with
`replicaRetryLimit=0`, captures and monitors exactly one execution, and always
runs CPU-only Blob recovery after the terminal status. It never updates a stale
GPU job into compliance.

## Bounded-pilot caps

| cap | value |
| --- | ---: |
| `max_smoke_prefills_before_extension` | 60 |
| `max_non_generative_prefills` | 180 |
| `max_s4_generations` | 12 |
| `max_model_evaluation_equivalents` | 228 |
| `possible_scored_rows` | 210 |

## Legal and scientific boundary

- `p0_r2_pilot_execution_authorized = true`, unconsumed;
- `formal_execution_authorized = false`;
- draft v0.6 is neither reviewed nor frozen;
- interface, positive reference, and RP wrapper remain `null`;
- OD2 and UR-22 remain unresolved;
- the evidence ledger still ends at `EV-0016`;
- the research question remains unanswered;
- all pre-execution counters are zero;
- exactly one overall replay-then-conditional-pilot envelope remains.

This publication did not run the live replay gate, create or start the
generation-1 GPU job, allocate any GPU workload, construct a tokenizer, download
or load a checkpoint, load a model weight, perform a model operation, select an
interface, set a threshold, freeze a draft, or add an evidence row.
