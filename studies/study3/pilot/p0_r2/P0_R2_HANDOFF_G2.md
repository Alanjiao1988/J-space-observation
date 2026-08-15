# P0-R2 cross-session handoff, generation 2

> **Terminal state:** `STOP_NO_MODEL_OPERATION`.
>
> The generation-2 live replay **passed** and was independently
> reconstructed from its raw log. The bounded T4 pilot was **not**
> authorized: no GPU job was created or started and no model operation was
> performed. The generation-2 one-shot replay envelope is **consumed** and
> must never be reopened.
> Generation 2 is a **new, disjoint execution** of the P0-R2 infrastructure
> successor. It does not reopen P0-R1 and it does not reopen P0-R2 generation 1.
> Both remain terminal, consumed and byte-unchanged.

Authority:
`studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md`

## 1. What generation 1 proved, and what killed it

Generation 1 reached its one irreversible invocation and stopped there. ACR run
`cmjv`, attempt `p0r2-g1-live-20260815-0800`, image
`sha256:eb0e284c6b420aa4992dcdee9a43b9cb92a96937499bca605f96b141619e9b58`.

The raw log is unambiguous about why:

```text
ImdsCredential.get_token failed: No token received.
ManagedIdentityCredential.get_token failed: No token received.
Unexpected return type <class 'str'> from ContentDecodePolicy...
P0_R2_PREFIX_PREFLIGHT_REFUSED=1 the private listing failed (Bad Gateway
ErrorCode:None); a query error is never an absence
```

An ACR Tasks agent has neither the registered managed identity nor a route into
`cae-jspace-observation-sea-vnet2`, so it cannot list a private Storage account.
The preflight was **right** to refuse: a Bad Gateway is an ambiguity, and an
ambiguity is never an absence. The design was wrong, not the guard.

Generation 1 carried a second latent refusal behind the one that fired: its live
path invoked the replay gate without the successor authorization the gate
requires, and the ACR task never set it. That would have refused too.

## 2. What generation 2 changes, and what it does not

Generation 2 changes **infrastructure only**.

| changed | unchanged |
| --- | --- |
| the prefix proof runs inside the VNet, not inside ACR | corpus, manifests, item selection, cells, assignments, RT/RL/RI |
| one shared receipt validator serves canary and live | tokenizer and checkpoint identity |
| the ACR container validates a bound host receipt | prompt and answer semantics |
| a new digest-pinned image | activation and interface definitions |
| a disjoint `p0r2-g2-` / `study3/p0_r2/g2/` namespace | replay factorization logic |
| the gate authorization is named explicitly | scoring, exclusion and the smoke-extension rule |

The nine P0-R1 generation-3 scientific modules are carried byte-identically and
verified by SHA-256 before import. The generation-2 lock **proves** that rather
than asserting it: it compares every reused scientific blob against the identity
the generation-1 lock registered, and the schema refuses a lock whose
`immutable_science.proved` is not `true`.

## 3. The corrected design

1. `job-jspace-s3-p0r2-prefix-g2`, a CPU-only Container Apps execution inside
   `cae-jspace-observation-sea-vnet2` using `id-jspace-aca-acrpull-sea`,
   performs the exact prefix listing and prints a base64 **observation** between
   `P0_R2_G2_PREFIX_OBSERVATION_BEGIN` and `P0_R2_G2_PREFIX_OBSERVATION_END`.
2. The host recovers that observation **from the captured log alone**,
   correlates it with the Azure control-plane execution record, and produces a
   **receipt**. A supplied observation that the log does not carry is refused.
3. The host embeds the exact receipt bytes and SHA-256 in the two-file ACR
   context admission, and refuses to start the live process if the observation
   is more than 15 minutes old.
4. The ACR container validates the bound receipt through the single shared
   validator and prints `P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1` exactly once.
5. The container requests no managed-identity token, lists no Storage and opens
   no private endpoint before the gate.

This is not permission to bypass the prefix proof. The live path refuses if the
receipt is missing, malformed, stale at host submission, ambiguous, for another
generation, attempt, prefix, account or container, reports anything other than a
successful zero-object listing, or cannot be correlated with a successful
in-VNet execution. There is no `--allow-path`, no `--skip-proof`, no `--force`,
no caller-supplied truth value and no fallback that turns an error into absence.

### No branch asymmetry

Generation 1's canary skipped the step that killed its live run. Generation 2
has **one** validator, `p0_r2_prefix_proof_g2.validate_receipt`, called with the
same arguments in both modes; `mode` selects a marker, never a rule. The
committed tests execute both paths and assert the two reports are identical
apart from the mode label.

## 4. Active generation-2 identities

| item | exact value |
| --- | --- |
| authority | `studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md` |
| authority bytes / SHA-256 | 32,944 / `9b1f50843b8d7170142f0aa0640f19f7d3fb126120a0cd83db0440cae2919f50` |
| authority Git blob | `6e06f8d07e40e08479681a710b4da76477084473` |
| authority commit | `2740648761bd49af52b2e106afebd9a5883f420c` (first object after `135f725…`) |
| image executable commit | `a5115e0faf6acc686f777c8f9b3e496602832493` |
| image | `acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r2@sha256:4c4f815b86917a6867b014a2591ac415eba5544f7dc32968fad6ca04af6e0079` |
| image build | ACR `cmk3`; tag `gen2-a5115e0faf6a` |
| base image | the P0-R1 generation-3 image, `sha256:e1adda95862ea14bf0397f496aa0ef9f7e5918e95b5436b0eb84ee3480d91e4c` |
| bound image paths | 57, each equal to the executable commit's Git blob |
| ACR task | `p0_r2_acr_task_g2.yaml` |
| live replay attempt | `p0r2-g2-live-20260815-1700` |
| pilot attempt | `p0r2-g2-pilot-20260815-1700` |
| blob prefix root | `study3/p0_r2/g2/` |
| GPU job | `job-jspace-s3-p0r2-pilot-g2`, proved absent |
| CPU recovery job | `job-jspace-s3-p0r2-recover-g2`, proved absent |
| results root | `studies/study3/pilot/p0/results/p0-r2-g2/` |

Superseded, unexecuted generation-2 images: `cmjx`
(`sha256:df1b7275…`), `cmk0` (`sha256:a14adbd8…`), `cmk2` (`sha256:6000df85…`).

## 5. Reuse without editing a frozen byte

`p0_r2_namespace_g2.py` re-executes the frozen generation-1 transport, strict
decoder, blob transport, journal, recovery, hard-kill canary and authorization
**byte-for-byte** into separate module objects and rebinds only the namespace
constants. The generation-1 module objects in `sys.modules` are never mutated,
and the source SHA-256 is verified **before** the instance cache is consulted —
a defect the additive test suite found and which is now closed.

Every file that existed under the four frozen roots at `135f725…` is proved
byte-unchanged at the generation-2 head: 182 protected files, 0 changed,
0 removed.

## 6. Model-free production canaries

| canary | production identity | result |
| --- | --- | --- |
| in-build image-to-Git audit | ACR `cmk3` | 57/57 bound bytes equal the executable commit's Git blobs, 0 mismatches; a drifted image cannot be pushed |
| in-VNet prefix proof | ACA `job-jspace-s3-p0r2-prefix-g2-h6hd2sv` | managed identity acquired, private listing succeeded, prefix `PROVED_UNUSED`, `object_count 0`, `wrote_any_object false` |
| ACR packing and pre-gate | ACR `cmk4` | 2 context entries, **38**-character maximum native path against a 100 ceiling, `P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1` exactly once, no managed-identity or Storage call, gate not invoked, exit 0 |
| hard-kill / open-admission CPU recovery | ACA `job-jspace-s3-p0r2-hardkill-g2-5rwdm03` | **PASS** — a real `SIGKILL` (`returncode -9`, `HARD_TERMINATION_SIGKILL`) left an open admission at sequence 3; independent CPU recovery recovered every committed payload byte **byte-exactly against independently regenerated bytes**, verified a continuous create-only journal, and wrote the recursive recovery manifest last |
| bounded job absence | read-only control plane | `job-jspace-s3-p0r2-pilot-g2` and `job-jspace-s3-p0r2-recover-g2` both `PROVED_ABSENT`; `job-jspace-s3-p0r2-prefix-g2` `PROVED_PRESENT`, which is what makes the absence non-vacuous; 0 ambiguous |
| Windows launch path | host | `shutil.which` resolved `az.CMD`; benign `az version` and `az account show` both exit 0 against the registered subscription; the authorization variable is never exported globally |

No canary ran the replay gate. No tokenizer was constructed or called, no
checkpoint was accessed or loaded, no model weight was loaded, no GPU workload
was allocated, no model operation was performed, and no one-shot envelope was
consumed.

### Canaries that refused, and why that matters

Three generation-2 attempts refused before doing anything irreversible, and each
found a real defect that would otherwise have fired on the one invocation that
cannot be retried:

* ACR `cmjy` — the canary entry point asked `p0_r2_transport` for `--identity`,
  which it does not expose.
* ACA `…-hardkill-g2-v8iabiy` — `CUDA_VISIBLE_DEVICES=-1` is read as an exposed
  accelerator by the frozen `assert_model_free` guard. **Section 7.4 of the
  authority names `-1`; the guard, which section 5 forbids changing, accepts
  only `""`, `void` or `none`.** The generation-2 job specifications therefore
  declare `""`, which is the registered way to say that no device is offered,
  and the committed test now *executes* the guard against each declared job
  environment instead of asserting a literal. No object was written.
* ACA `…-hardkill-g2-hcb7ki0` — the attempt id did not begin with the registered
  generation-2 hard-kill canary prefix. No object was written.

ACR `cmjw` was a failed build: the context argument was lost and the repository
root Dockerfile was uploaded. No generation-2 image was produced.

## 7. The complete attempt ledger

`p0_r2_attempt_ledger_g2.json` is append-only and covers **54** runs: the 45
sealed P0-R2 runs imported from the generation-1 ledger, the consumed
generation-1 live run `cmjv`, and the 8 generation-2 ACR runs. It also records
the 8 Container Apps executions.

**54 sealed, 0 unavailable, 0 ambiguous**, no fabricated hash and no unavailable
run called a pass. Exactly one run in the whole ledger — `cmjv` — could ever
have entered replay, model or GPU code. **Zero generation-2 runs could.**

## 8. Bounded-pilot caps

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

## 9. Legal and scientific boundary

- `formal_execution_authorized = false`;
- draft v0.6 is neither reviewed nor frozen;
- interface, positive reference and RP wrapper remain `null`;
- the evidence ledger still ends at `EV-0016`, and this authority added no row;
- the research question remains unanswered;
- all pre-replay counters are zero;
- P0-R1 and P0-R2 generation 1 remain terminal, consumed and byte-unchanged.

This publication did not run the live replay gate, create or start the
generation-2 GPU job, allocate any GPU workload, construct a tokenizer, download
or load a checkpoint, load a model weight, perform a model operation, select an
interface, set a threshold, freeze a draft, or add an evidence row.

## 10. Segment B: what actually happened

| step | identity | result |
| --- | --- | --- |
| inter-segment admission gate | fresh checkout at `59a52bc…` | `P0_R2_G2_PHASE_B_AUTHORIZED=1`, 38 conditions, 0 failed, 0 underived |
| final live-prefix proof | ACA `job-jspace-s3-p0r2-prefix-g2-4l4b68i` | `study3/p0_r2/g2/p0r2-g2-live-20260815-1700/` `PROVED_UNUSED`, `object_count 0` |
| **one live replay** | ACR `cmk7` | **PASS** — exactly one run id, exit 0, gate invoked exactly once, envelope consumed |
| independent reconstruction | captured raw log only | 4 of 4 canonical artifacts, 0 repairs, 18 of 18 strict checks pass |
| bounded T4 pilot | — | **not authorized**; no job created, no job started, 0 model operations |

The live path did exactly what generation 1 could not: it validated a bound,
host-verified in-VNet prefix receipt, printed
`P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1` exactly once, made no managed-identity
or Storage call, and reached the replay gate.

### Why the bounded pilot stopped

Two section-14 conditions are false, and both are derived, not asserted:

1. **The pilot authorization receipt cannot be generated mechanically.** The
   frozen `p0_r2_authorization_v1.build` reads `lock["state"]`. The generation-2
   lock publishes its terminal state under `terminal_state`, following the v2
   lock's own field name, so the authorization refuses.
2. **The registered runner cannot perform a bounded model operation.**
   `p0_r2_model_runner_v1` exposes only `--identity` and `--sentinel`, and the
   sentinel performs no model work by construction. Its `production_executor` is
   a library function that no entry point in the image invokes.

Repairing either would mean editing reused logic, which section 5 forbids, or
resealing a ready anchor that the already-consumed replay is bound to, which
section 11 forbids. The truthful stop is therefore `STOP_NO_MODEL_OPERATION`,
published in `studies/study3/pilot/p0/results/p0-r2-g2/`.

A successor authority that wants the bounded pilot must decide, explicitly,
whether the generation-2 lock should also publish `state`, and whether the
registered runner should expose a production entry point. Neither decision
belongs to this authority.
