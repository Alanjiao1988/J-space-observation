# Study 3 P0-R2 corrective closure and conditional execution authority

This is a new operator-authorized authority for Study 3 pilot stage P0-R2. It
supersedes the premature P0-R2 readiness claim only to the extent stated here.
It does not reopen P0-R1 and it alters no scientific invariant.

It is published as the **first** new committed object after
`005aa087e40c641affc8ca537e6c6a075bcbfe98`, before any Azure mutation and
before any implementation change, so that everything the corrective closure
does afterwards is bound by an authority that already exists.

## 1. Bound identities

### 1.1 Repository state this authority starts from

| item | exact value |
| --- | --- |
| repository | `Alanjiao1988/J-space-observation` |
| `HEAD` = `origin/main` | `005aa087e40c641affc8ca537e6c6a075bcbfe98` |
| `HEAD^{tree}` | `9d3610a85d5fb35dd8a34544296b81c8f5e77f28` |
| worktree | clean |
| merge commits in `22ae685b83daeaf3fb89057db0761f20644d9b7a..HEAD` | none |

### 1.2 P0-R2 generation-1 objects that existed before this authority

| item | exact value |
| --- | --- |
| v1 executable commit | `1eb3e21b408213cb183bd8d2f55c3554b9713160` |
| v1 executable tree | `88d7e9a016772c4129f56637edd2d7fbd96b105b` |
| v1 ready anchor | `7fd5fe57707461fcf70bfc9ab00b707b3c44ef71` |
| image | `acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r2@sha256:3d857e54007d12bd943b383db522b913ba627a544b4d31b3e648eef30a65d8e7` |
| ACR task blob | `0ec0bfa0c2e3ebe882963564ef758b06bf890657` |
| replay envelope | unconsumed |
| canonical P0-R2 replay artifacts | absent |
| P0-R2 GPU job / recovery job | absent |

### 1.3 Azure

| item | exact value |
| --- | --- |
| subscription | `943bacdf-8b6e-4e3a-8126-a149f623d32e` |
| registry | `acrjspaceobssea0708231738` |
| resource group | `rg-jspace-observation-sea` |
| storage account | `stjspacefiles0709085305` |
| results container | `jspace-results` |
| attempt namespace | `study3/p0_r2/g1/<attempt>/` |
| bounded GPU pilot job | `job-jspace-s3-p0r2-pilot-g1` |
| bounded CPU recovery job | `job-jspace-s3-p0r2-recover-g1` |

Only ordinary non-force first-parent fast-forwards are permitted. Force-pushing
is forbidden under this authority without exception.

## 2. Permanent invariants this authority does not touch

P0-R1 is terminal and immutable:

- stop commit `30806d793872a50e581d3252382b4a0ec2af3889`;
- state `STOP_NO_MODEL_OPERATION`;
- its replay envelope is consumed and must never be rerun;
- no P0-R1 preflight, replay, retry, recovery retry or pilot may be executed;
- zero bytes may change under `studies/study3/pilot/p0_r1/`,
  `studies/study3/pilot/p0/results/p0-r1/`, or the P0-R1 authority files.

P0-R2 science remains the byte-identical P0-R1 generation-3 science. This
authority changes none of: corpus, manifest, cells, assignments, RT, RL, RI,
prompts, templates, tokenizer behaviour, seeds, fp16/no-sampling behaviour,
parser, scoring, eligibility, factorization, smoke or extension conditions, the
limits 60 / 180 / 12 / 228 / 210, or any Study 1, Study 2, P0-T, OD2, UR-22,
interface, reference, RP or evidence-ledger object.

Permanent legal state, unchanged by this authority:

- `formal_execution_authorized = false`;
- draft v0.6 reviewed / frozen = `false` / `false`;
- interface / positive reference / RP wrapper = `null` / `null` / `null`;
- evidence-ledger tail = `EV-0016`;
- research question answered = `false`.

## 3. The registered closure defects

The premature P0-R2 readiness claim is corrected because of four **closure
defects**, reproduced read-only before any change and retained as the
machine-readable admission audit
`studies/study3/pilot/p0_r2/p0_r2_corrective_admission_audit_v2.json`.

### Defect 1 — the published closure does not prove

`git diff --name-only 7fd5fe5… 005aa087…` changes eight
`studies/study3/pilot/p0_r2/validation/` paths — four `*.sh`, one `*.yaml` and
two `*.json`, plus `p0_r2_identity_canary_job_v1.yaml` — none of which is
accepted by the published `GOVERNANCE_ALLOWLIST` or
`GOVERNANCE_ALLOWLIST_PREFIXES`. Calling the real governance-chain proof of
`p0_r2_closure_binding_v1.py` against executable `1eb3e21…`, anchor `7fd5fe5…`
and governance head `005aa087…` therefore **refuses** with
`P0_R2_CLOSURE_BINDING_REFUSED=1` and exit code 3. The published readiness
claim was made without the proof it names. There is no false-pass route: the
validator refuses correctly, and the defect is the claim, not the validator.

These are executable validation scripts, an ACR task definition and a Container
Apps job definition. They may not be relabelled "governance-only" to make the
proof pass.

### Defect 2 — the first command cannot prove what it asserts

The published first command is an `az acr run … /dev/null` invocation of
`p0_r2_successor_v1.sh preflight` inside the pinned image. Its context is
`/dev/null`, so it structurally cannot observe `HEAD == origin/main`, a clean
worktree, ready-anchor ancestry, post-anchor changed paths, the exact published
lock bytes, GPU or recovery job absence, or the exact future live attempt
prefix. Its prefix check further reports `P0_R2_PREFIX_PREFLIGHT_SKIPPED=1`
when no attempt id is supplied, which the published command does not supply.

### Defect 3 — the hard-kill recovery canary was never reproduced

P0-R1 recorded a hard-kill CPU recovery canary. P0-R2 carries no such asset and
no such receipt: `p0_r2_canary_receipts_v1.json` contains no hard-kill entry.
The recovery path is implemented and its job shape is pinned, but for P0-R2 the
open-admission recovery property is **unproven**.

### Defect 4 — the run record is incomplete and the failure baseline is stale

- No sealed receipt exists in the repository for the claimed final run `cmj7`.
- The superseded runs `cmhp`, `cmhq`, `cmhs`, `cmj2`, `cmj4` and the
  failed/discarded runs `cmhb`, `cmhd`, `cmhe`, `cmhf`, `cmhg`, `cmhh`, `cmhk`,
  `cmhn`, `cmhw`, `cmhx`, `cmhy`, `cmj0`, `cmj1` appear only in external
  disclosure and are not sealed in the repository at all.
- The differential full suite carries **four** standing failures while the
  original authority registered only **two**.

## 4. The four standing failures, conditionally accepted

| # | node id | registered before? |
| --- | --- | --- |
| 1 | `tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix` | yes |
| 2 | `tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last` | yes |
| 3 | `tests/test_phase05_jlens_saturation.py::test_no_artifact_asserts_a_prohibited_claim` | no |
| 4 | `tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only` | no |

Failure 3 is environment-dependent and must be demonstrated to exist at the
unmodified baseline in the registered closure.

Failure 4 has exactly eight offenders, every one of them a protected P0-R1
byte introduced by the P0-R1 stop commit
`30806d793872a50e581d3252382b4a0ec2af3889`, which is the commit *after* P0-R1
full-suite run `cmh9` and was therefore never covered by a full-suite run:

```text
studies/study3/pilot/p0/results/p0-r1/P0_R1_GENERATION3_STOP_DISPOSITION.md
studies/study3/pilot/p0/results/p0-r1/p0_r1_generation3_stop_counters.json
studies/study3/pilot/p0/results/p0-r1/p0_r1_generation3_stop_receipt.json
studies/study3/pilot/p0/results/p0-r1/p0_r1_live_replay_command.log
studies/study3/pilot/p0/results/p0-r1/p0_r1_preflight_command.log
studies/study3/pilot/p0/results/p0-r1/p0_r1_preflight_gpu_job_presence.json
studies/study3/pilot/p0/results/p0-r1/p0_r1_preflight_supersession_v3.json
studies/study3/pilot/p0/results/p0-r1/p0_r1_replay_stderr.txt
```

They are **not** repaired. Repairing them would rewrite P0-R1 bytes, which this
stage is forbidden to touch.

This authority conditionally accepts exactly these four standing failures only
if **all** of the following hold:

- all four occur at both the unmodified baseline and the corrected executable
  and final head;
- their normalized signatures agree between baseline and corrected head;
- no fifth failure occurs;
- collection errors equal zero;
- the corrected work introduces zero new failure.

Anything else is a stop.

## 5. What the corrective closure may and may not do

### 5.1 v1 is historical and must not be edited

The published v1 lock, v1 lock schema, v1 canary receipts, v1 image manifest,
`P0_R2_HANDOFF.md` and the v1 ready anchor `7fd5fe5…` remain exactly as
published. They are **historical**. No byte of them may be edited, replaced or
back-dated. They are marked superseded by an explicit, separate supersession
record — never by mutation.

### 5.2 Corrected artifacts are additive and use v2 names

All corrected artifacts carry additive `_v2` names, for example
`p0_r2_execution_lock_v2.json`, `p0_r2_execution_lock_v2.schema.json`,
`P0_R2_HANDOFF_V2.md`, a v2 closure/admission proof module, a v2 host preflight
module, a v2 attempt/run ledger, v2 validation and canary receipts, and an
explicit v1 supersession record.

Generation remains **P0-R2 generation 1**, because the replay envelope is still
unconsumed. Version 2 is a closure and execution revision, not a second replay
generation.

### 5.3 The v2 validator must distinguish nine identities

The v2 validator must separate, and prove relations between, at least:

1. immutable scientific commit and blob identities;
2. image-executable commit and tree;
3. host-closure executable commit and tree;
4. task object;
5. image and digest;
6. closure base;
7. ready anchor;
8. governance source;
9. published head.

The old defect may **not** be solved by broad caller-supplied allow-lists.
Everything placed after the new ready anchor must be demonstrably
non-executable governance or evidence. Validation scripts, shell code, YAML
task and job definitions, Python modules and test implementations must be
committed **before** the new anchor, or explicitly bound as executable or
validation inputs. Executable validation scripts may not be called
"governance-only".

### 5.4 Segment A is model-free

No tokenizer construction or encode, no checkpoint download or load, no model
weight load, no prefill, no generation, no scoring and no GPU operation is
authorized anywhere in Segment A. Every Segment A receipt must carry all-zero
model and GPU counters.

## 6. The publication and fresh-checkout boundary

A **hard** boundary separates the two segments.

After Segment A is published, its mutable worktree and every in-memory
conclusion drawn inside it are discarded. Every condition is recomputed from a
fresh short-path checkout of the new `origin/main`, and the resulting canonical
Phase-B admission document must derive every field from evidence rather than
assertion. That admission document is itself published as a governance-only
commit and re-proved from another fresh checkout, so that the admission commit
is covered by the proof it claims.

## 7. Conditional authorization of Segment B

Segment B — one-shot live replay, and only after a published replay pass one
bounded GPU pilot — is authorized by the operator prompt this authority
records, and by nothing else. That authorization is **conditional and
mechanical**: it takes effect only if every registered admission condition
evaluates true after Segment A has been published and independently rechecked
from a fresh checkout.

- Any condition that is false **or unknown** forbids live replay. The correct
  response is to set `phase_b_authorized = false`, publish a truthful
  `P0_R2_CORRECTIVE_CLOSURE_STOP_NO_REPLAY` disposition, invoke no live replay,
  create no GPU job, and report the exact failed conditions.
- Publishing `STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE` at the end of
  Segment A does **not** consume the replay envelope and is not by itself an
  authorization to replay.

### 7.1 The one-shot replay envelope

The live replay envelope is consumed the moment the authorized Azure CLI live
submission is invoked — **even if failure occurs before an ACR run id is
returned**. From that instant:

- it may never be rerun;
- it may never be regenerated;
- no other attempt may be substituted;
- the gate may never be repaired in place;
- no further `az acr run --live` may be invoked;
- canonical success artifacts may never be created unless recovered bytes prove
  them.

Exactly one ACR run id is required. Missing or multiple run ids are terminal
stop conditions, not retry conditions. `P0_R2_LIVE_REPLAY_AUTHORIZED=1` may
never be set globally; the guarded wrapper sets and passes it for exactly one
admitted invocation.

### 7.2 The pilot is authorized only after a proved replay pass

A bounded GPU pilot is authorized only after **all** of:

- replay was invoked exactly once and exactly one ACR run id exists;
- the complete raw log and stderr are retained from the first byte;
- all four canonical artifacts are **independently reconstructed byte-exactly**
  with the strict P0-R2 decoder, using checksum-proved fragment repair only
  where exact decoded length and chunk SHA-256 prove the repair;
- strict receipt validation passes and the emitted and reconstruction receipts
  agree;
- the replay result is the registered pass outcome;
- counters prove zero tokenizer, model and GPU operations;
- the replay evidence is published to `origin/main`, a fresh checkout of the
  new published head is clean, the v2 governance-chain proof still passes, and
  a **current-head proof binding the replay evidence** is published;
- the exact pilot attempt prefix is unused, both bounded jobs are still proved
  absent, and the active image, task and lock are unchanged.

If any of those is false or unknown, a no-model terminal disposition is
published and the stage stops permanently.

### 7.3 The pilot remains bounded and non-interpretive

The runner must **enforce**, not merely report: 60 smoke prefills before
extension, 180 total non-generative prefills, 12 S4 generations, 228
model-evaluation equivalents and 210 possible scored rows. Smoke runs first;
if the registered smoke-extension criterion does not pass, the stage stops
without extension, recovers and publishes the smoke result, calls no further
prefill or generation, and does not rerun. Exactly one GPU execution may be
started, `replicaRetryLimit=0`, manual trigger, `gpu-t4` workload profile,
digest-pinned image, registered managed identity and storage route. CPU-only
Blob recovery always runs afterwards, including after failure, timeout or hard
kill.

The final scientific interpretation remains limited to pilot methods
feasibility. Under this authority no interface may be selected, no formal
threshold set, no confirmation sample size set, no draft frozen, no
evidence-ledger row added, no claim made that the research question is
answered, and no formal execution authorized.

## 8. Refusals

The corrective closure stops, without proceeding, on any of:

- `origin/main` having moved from `005aa087…` before the first write;
- a registered refusal from any validator;
- ambiguity in any query, run id, image, prefix, receipt or ancestry result;
- unavailable authority or unavailable Azure CLI or log capture;
- unexpected remote drift;
- any failed admission condition;
- a missing, partial-without-registered-classification, ambiguous or
  non-byte-exact hard-kill recovery result — this canary may not be waived;
- an unavailable historical log that might have entered replay, model or GPU
  code. A build-only or model-free canary may be recorded as unavailable
  evidence only when its submitted task identity proves it could not have
  entered a model path. A hash may never be fabricated and an unavailable run
  may never be called a pass.

## 9. Authority provenance

This document is authored from the operator prompt "Study 3 P0-R2 corrective
closure and conditional one-shot execution authority", which is the operator's
explicit authority for Segment A and for the conditional Segment B described
above. Its own byte count, SHA-256, line-ending profile, BOM status and
trailing-newline status are recorded in the publication commit message and are
re-bound in `p0_r2_execution_lock_v2.json`; a file cannot contain its own hash,
so those identities are recorded about it rather than inside it.

Completion is never claimed merely because artifacts were published.
Completion requires every applicable mechanical proof to have been produced and
retained.
