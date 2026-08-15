# P0-R2 cross-session handoff, generation 1 revision 2

> **Entry state:** `STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE`.
>
> Generation 1 is execution-ready but **unconsumed**. On entry run only the
> model-free host preflight below. It is not the `/dev/null` image command the
> v1 handoff published: that command could not observe a single host-side fact
> it was cited for. Do not run `live-replay` without a mechanically all-true
> Phase-B admission document, and never create or start the GPU job before a
> captured replay pass and its independent reconstruction have been published.

P0-R2 is an **infrastructure successor** to P0-R1, not a new experiment. This
revision is a **closure and execution revision**, not a second replay
generation: the replay envelope is still unconsumed, so the generation stays 1.

This publication modified **zero bytes** of P0-R1 and **zero bytes** of the
published P0-R2 v1 closure. P0-R1's stop commit
`30806d793872a50e581d3252382b4a0ec2af3889` and its terminal state remain exactly
as published.

## Why there is a revision 2

The v1 readiness claim was premature. Four closure defects were reproduced
read-only before anything changed and are retained in
`p0_r2_corrective_admission_audit_v2.json`.

**1. The published closure did not prove.** Eight executable validation inputs
were committed after the v1 ready anchor `7fd5fe5…`. The real governance-chain
proof refuses that relationship with `P0_R2_CLOSURE_BINDING_REFUSED=1` and exit
3. The readiness claim was published anyway. The v1 validator decided whether a
path was inert by looking it up in a literal list; a shell script that is not on
a list is still a shell script.

**2. The published first command could not prove what it asserted.** It ran
`az acr run … /dev/null`, so it had no working tree, no `origin/main`, no
anchor, no post-anchor diff and no Azure answer in scope. Its prefix check
printed `P0_R2_PREFIX_PREFLIGHT_SKIPPED=1` because the published command
supplied no attempt id.

**3. The hard-kill / open-admission recovery canary was never reproduced.** The
v1 handoff said so plainly, which is to its credit, but an implemented recovery
path with no receipt is a claim.

**4. The run record was incomplete and the failure baseline was stale.** `cmj7`
was claimed as the final run and never sealed; eighteen superseded, failed or
discarded runs existed only in external disclosure; two historical failures were
registered where four occur.

Two further latent defects were found by building the corrected closure, and
both would have fired on the one invocation that cannot be retried:

- `p0_r2_replay_v1.sh` and `p0_r2_model_pilot_v1.sh` default `--lock-file` to
  `/opt/jspace/p0_r2_execution_lock_v1.json`, a path **no Dockerfile ever
  wrote**. The live path would have refused with an unreadable lock.
- The registered CPU-only job shape leaves `NVIDIA_VISIBLE_DEVICES` and
  `NVIDIA_DRIVER_CAPABILITIES` set, inherited from the CUDA-capable base image,
  and `p0_r2_recovery_v1.assert_model_free` correctly refuses to run recovery on
  what looks like an accelerator replica. The first hard-kill execution failed
  for exactly this reason. The same omission is still latent in
  `p0_r2_recovery_job_v1.yaml`: **the pilot's recovery job must be created with
  `NVIDIA_VISIBLE_DEVICES=void`, `NVIDIA_DRIVER_CAPABILITIES=void` and
  `CUDA_VISIBLE_DEVICES=`**.

## Active revision-2 identities

| item | exact value |
| --- | --- |
| image executable commit | `c9344c52bfbacc4f2a24010fffa534a940104140` |
| image executable tree | `bb27933ebf42e811ec7e5a42a13d65377cdd2f5c` |
| host-closure executable commit | `dc68c3cf54ea33ae10630ab1a7698c394778d238` |
| closure base | `dc68c3cf54ea33ae10630ab1a7698c394778d238` |
| ready anchor | the first-parent child of the closure base carrying `p0_r2_execution_lock_v2.json` |
| image | `acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r2@sha256:eb0e284c6b420aa4992dcdee9a43b9cb92a96937499bca605f96b141619e9b58` |
| image build | ACR run `cmjr`; tag `gen1r2-c9344c52bfba` |
| base image | the P0-R1 generation-3 image, `sha256:e1adda95862ea14bf0397f496aa0ef9f7e5918e95b5436b0eb84ee3480d91e4c` |
| ACR task | `p0_r2_acr_task_v2.yaml`, blob `93d9fa5710b057c71b3c6e297650b21c4c641912` |
| bound image paths | 44; each matches the executable commit's Git blob |
| generation-1 GPU job | `job-jspace-s3-p0r2-pilot-g1`, proved absent |
| CPU recovery job | `job-jspace-s3-p0r2-recover-g1`, proved absent |
| live replay attempt | `p0r2-g1-live-20260815-0800`, prefix proved unused |
| pilot attempt | `p0r2-g1-pilot-20260815-0800`, prefix proved unused |

Superseded, unexecuted image builds: `cmj9`, `cmjb`, `cmjd`, `cmje`. Only `cmjb`
served a canary and only `cmjd` served a hard-kill canary; both canaries were
rerun against the active digest.

## The corrected validator

`p0_r2_closure_binding_v2.py` keeps **nine** identities apart —
`immutable_science`, `image_executable`, `host_closure_executable`,
`task_object`, `image`, `closure_base`, `ready_anchor`, `governance_source`,
`published_head` — and classifies every path that changed after the anchor from
its own committed blob and file mode. A post-anchor path is admitted only when
**three independent gates** hold:

1. it classifies non-executable from its bytes — no shebang, no executable mode
   bit, no executable extension, not a Dockerfile, not a deletion;
2. it is a member of the exact `governance_evidence_closure` the active lock
   publishes — an exact path set with no wildcard;
3. it is outside the bound executable, validation, task, job, image and
   immutable-scientific closure.

There is deliberately **no `--allow-path` option**. Nothing a caller passes can
widen any of those sets.

## The corrected first command

From a fresh, clean, short-path checkout of the final published `origin/main`:

```bash
python3 studies/study3/pilot/p0_r2/p0_r2_host_preflight_v2.py \
  --preflight \
  --root . \
  --lock-file studies/study3/pilot/p0_r2/p0_r2_execution_lock_v2.json \
  --prefix-receipt <in-VNet prefix preflight receipt> \
  --context-dir <the two-file acrctx> \
  --out studies/study3/pilot/p0_r2/p0_r2_host_preflight_proof_v2.json
```

It must print exactly once each:

```text
P0_R2_HOST_PREFLIGHT_COMPLETE=1
P0_R2_GOVERNANCE_CHAIN_PROVED=1
P0_R2_HEAD_EQUALS_ORIGIN_MAIN=1
P0_R2_WORKTREE_CLEAN=1
P0_R2_P0_R1_TERMINAL=1
P0_R2_REPLAY_ENVELOPE_UNCONSUMED=1
P0_R2_LIVE_PREFIX_PROVED_UNUSED=1
P0_R2_GPU_JOB_PROVED_ABSENT=1
P0_R2_RECOVERY_JOB_PROVED_ABSENT=1
P0_R2_MODEL_OPERATIONS_PERFORMED=0
```

It refuses on a foreign head, a dirty checkout, an altered task or lock, an
unpinned or wrong image, an unavailable Azure CLI, an ambiguous job query, an
occupied prefix, a missing in-VNet prefix receipt, a nonzero counter, a
post-anchor executable path, and a native packer path over 240 characters. The
image's own `p0_r2_successor_v2.sh preflight` may be run as a **subordinate**
check; it is never sufficient on its own.

The host cannot list the private results account — `publicNetworkAccess` is
`Disabled` and `defaultAction` is `Deny` — so the prefix proof must come from
inside the VNet. A host-side listing error is recorded as an ambiguity and is
never read as an absence.

## Model-free production canaries

| canary | production identity | result |
| --- | --- | --- |
| in-build image-to-Git audit | ACR `cmjr` | 44/44 bound bytes equal the executable commit's Git blobs, 0 mismatches; a drifted image cannot be pushed |
| model-free preflight | ACR `cmjt` | 44/44 image blobs match Git; 1,048,576-byte transport round trip; 0 repairs |
| designated packing canary | ACR `cmju` | the exact step that stopped P0-R1 succeeds: 2 context entries, **40-character** maximum native path against P0-R1's fatal **265**, exit 0 |
| **hard-kill / open-admission CPU recovery** | ACA `job-jspace-s3-p0r2-hardkill-g1-i3o654p` | **PASS** — a SIGKILLed child (`returncode -9`) left an open admission at sequence 3; independent CPU recovery recovered it and every committed payload byte **byte-exactly against independently regenerated bytes**, verified a continuous create-only journal, and wrote a recursive recovery manifest last |
| in-VNet prefix preflight | ACA `job-jspace-s3-p0r2-prefix-g1-qm5qp8k` | both the live and pilot prefixes `PROVED_UNUSED`, `object_count 0`, `wrote_any_object false` |
| bounded job absence | read-only control plane | `job-jspace-s3-p0r2-pilot-g1` and `job-jspace-s3-p0r2-recover-g1` both `PROVED_ABSENT`; the hard-kill and prefix jobs `PROVED_PRESENT`, which is what makes the absence proof non-vacuous |

No canary ran the replay gate. No tokenizer was constructed or called, no
checkpoint was accessed or loaded, no model weight was loaded, no GPU workload
was allocated, no model operation was performed, and no one-shot envelope was
consumed.

## The complete attempt ledger

`p0_r2_attempt_ledger_v2.json` covers **35** P0-R2 ACR runs and is append-only.
Azure still retains every one: **35 sealed, 0 unavailable, 0 ambiguous**, no
fabricated hash and no unavailable run called a pass.

| category | count | run ids |
| --- | ---: | --- |
| accepted (v1) | 6 | `cmht`, `cmhu`, `cmhv`, `cmj3`, `cmj5`, `cmj6` |
| claimed but previously unsealed | 1 | `cmj7` |
| superseded (v1) | 5 | `cmhp`, `cmhq`, `cmhs`, `cmj2`, `cmj4` |
| failed or discarded (v1) | 13 | `cmhb`, `cmhd`, `cmhe`, `cmhf`, `cmhg`, `cmhh`, `cmhk`, `cmhn`, `cmhw`, `cmhx`, `cmhy`, `cmj0`, `cmj1` |
| corrective closure | 10 | `cmj8`, `cmj9`, `cmja`, `cmjb`, `cmjc`, `cmjd`, `cmje`, `cmjf`, `cmjg`, `cmjj` |

## Validation

The full suite is **differential** and is compared by exact node id **and
complete normalized failure signature**, not by summary line. That distinction
is not academic: differential attempt `cmja` refused because a shared failure's
signature disagreed on `PosixPath('/workspace/base')` versus
`PosixPath('/workspace/head')`. The v1 harness, which compared only `FAILED`
lines, would have reported that pair as identical.

| run | scope | result |
| --- | --- | --- |
| `cmj8` | truthful baseline registration at `005aa087…` | 4,720 passed, 15 skipped, 4 failed, 0 collection errors |
| `cmja` | differential, superseded | refused: one shared signature disagreed on the checkout root |
| `cmjh` | full repository suite, differential | baseline `005aa087…` and corrected head both 4 failed / 15 skipped / 0 collection errors; **identical signature-set SHA-256**; 0 new failures; 0 fixed failures; +67 net new passing |

pytest's exit status is captured directly from the process and reconciled
against its own printed summary. Nothing is piped into anything that could hide
an exit status.

### The four standing failures, conditionally accepted

1. `tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix` — registered historical;
2. `tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last` — registered historical;
3. `tests/test_phase05_jlens_saturation.py::test_no_artifact_asserts_a_prohibited_claim` — **environment-dependent**: it passes on the authoring Windows host and fails in the registered Linux closure, and it fails at the unmodified baseline;
4. `tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only` — eight offenders, every one a **protected P0-R1 byte** under `studies/study3/pilot/p0/results/p0-r1/`, introduced by P0-R1's stop commit `30806d7…`, which is the commit *after* full-suite run `cmh9` and was therefore never covered by a full-suite run.

Failure 4 is **not repaired**, deliberately: repairing it would rewrite P0-R1
bytes, which this stage is forbidden to touch.

They are accepted only because all four occur at both the baseline and the
corrected head, their normalized signatures agree, no fifth failure occurs,
collection errors are zero, and the corrected work introduces zero new failure.

## Bounded-pilot caps

| cap | value |
| --- | ---: |
| `max_smoke_prefills_before_extension` | 60 |
| `max_non_generative_prefills` | 180 |
| `max_s4_generations` | 12 |
| `max_model_evaluation_equivalents` | 228 |
| `possible_scored_rows` | 210 |

The runner must **enforce** these, not report them. Smoke runs first; if the
registered smoke-extension criterion does not pass, the stage stops without
extension, recovers and publishes the smoke result, calls no further prefill or
generation, and does not rerun.

## Legal and scientific boundary

- `p0_r2_pilot_execution_authorized = true`, unconsumed;
- `formal_execution_authorized = false`;
- draft v0.6 is neither reviewed nor frozen;
- interface, positive reference and RP wrapper remain `null`;
- OD2 and UR-22 remain unresolved;
- the evidence ledger still ends at `EV-0016`;
- the research question remains unanswered;
- all pre-execution counters are zero;
- exactly one overall replay-then-conditional-pilot envelope remains.

This publication did not run the live replay gate, create or start the
generation-1 GPU job, allocate any GPU workload, construct a tokenizer, download
or load a checkpoint, load a model weight, perform a model operation, select an
interface, set a threshold, freeze a draft, or add an evidence row.
