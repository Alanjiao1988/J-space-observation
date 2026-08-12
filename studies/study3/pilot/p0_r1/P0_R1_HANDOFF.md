# P0-R1 cross-session handoff

> **Continue from the published P0-R1 ready commit. Do not return to the
> baseline of authority §1.**

Authority: [`../../prompts/study3_v0_6_p0_r1_authority.md`](../../prompts/study3_v0_6_p0_r1_authority.md)
§6, §7 and §10, as completed by
[`../../prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md`](../../prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md).

## 1. What the successor session inherits

| item | value |
| --- | --- |
| entry state | `STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE` |
| authority | `studies/study3/prompts/study3_v0_6_p0_r1_authority.md`, 19,632 bytes, sha256 `f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200845ddc19d2`, LF only, no trailing newline |
| supplement | `studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md`, 23,486 bytes, sha256 `ffe75ba42c023e959f3beb23927604c3ae72c07fb4b25be346f504c8ea2930de` |
| execution lock | `studies/study3/pilot/p0_r1/p0_r1_execution_lock.json` |
| image | `acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r1@sha256:7e2690feb6854a53f096d5b321e69fddebd2b744289c760e2fe74ed1ccec8176` |
| executable code commit | `aad14c45e9681a34f382aa95c55ac875d2ca98ce` |
| candidate | draft-v0.6, `studies/study3/protocol/interface_calibration_rendering_registry_v0_6.json` |
| corpus | the frozen 35-cell / 70-member P0 corpus, reused byte-exactly |
| execution flag | `p0_r1_pilot_execution_authorized = true`, **not yet consumed** |
| every other authority flag | false; `interface_selected`, `positive_reference` and `rp_wrapper` are **null** |

The image digest is real and resolved, not `null`. The lock binds two distinct
commits on purpose: the **executable code commit** the image was built from, and
the later **ready commit** that carries the lock. A digest cannot be embedded in
the image whose digest it defines, so the lock is necessarily the later object.
No executable byte changed after the build; `p0_r1_execution_lock.py --check`
re-proves that from the checkout.

## 2. The exact first command

The registered live replay gate is the first action, and nothing else may
precede it. It performs zero tokenizer constructions, zero encodes, zero
checkpoint downloads, zero model loads and zero GPU operations.

```
az acr run --registry acrjspaceobssea0708231738 \
  --subscription 943bacdf-8b6e-4e3a-8126-a149f623d32e \
  --platform linux/amd64 \
  -f p0_r1_acr_task.yaml \
  --set COMMIT=<the published P0-R1 ready commit> \
  --set IMAGE=acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r1@sha256:7e2690feb6854a53f096d5b321e69fddebd2b744289c760e2fe74ed1ccec8176 \
  --set DIGEST=sha256:7e2690feb6854a53f096d5b321e69fddebd2b744289c760e2fe74ed1ccec8176 \
  <context-dir>
```

The context directory must contain `p0_r1_checkout.sh`, `p0_r1_replay.sh`,
`p0_r1_acr_task.yaml` and a `repo.bundle` produced by
`git bundle create repo.bundle HEAD` at the ready commit.

**Pass and fail boundary.** The gate writes
`p0_r1_replay_result.json`, `p0_r1_replay_receipt.json`,
`p0_r1_replay_counters.json` and `P0_R1_REPLAY_DISPOSITION.md` into the writable
runtime result directory **before returning**, on both paths.

* On pass it emits `STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT` and
  exits 0, and the receipt carries `authorizes_model_pilot: true`.
* On failure it emits the applicable registered stop, exits non-zero, and the
  receipt carries `authorizes_model_pilot: false`. Publish the stop and perform
  **no** model operation. Do not repair and rerun.

## 3. The single GPU command, only after a replay pass

```
bash studies/study3/pilot/p0_r1/container/p0_r1_launch_gpu_pilot.sh \
  sha256:7e2690feb6854a53f096d5b321e69fddebd2b744289c760e2fe74ed1ccec8176 \
  <the published P0-R1 ready commit>
```

The launcher refuses to start if the job already has any execution, binds the
image by digest, sets the replica retry limit to zero and starts at most one
model-operating execution. The container entry point
`p0_r1_model_pilot.sh` refuses without a byte-valid replay-pass receipt whose
image digest, commit, tree, lock hash and attempt id all agree with the lock.

Locally, the calibration derivation remains available without a container and
without any model operation:

```
python studies/study3/pilot/p0_r1/p0_r1_replay_gate.py --check
```

That is `--check`, not `--gate`. `--gate` requires explicit successor-mode
authorization and an output directory, and refuses with exit 3 otherwise.

## 3. The boundary the successor must respect

**Before the replay gate passes**, the successor may not construct a tokenizer,
download a checkpoint, allocate a GPU, load a weight, perform a forward pass or
generate text.

**If replay fails**, publish a registered stop and perform **no** model
operation. Do not repair and rerun. The registered stop label for the
"some target role has no executable contrast" case is

```
STUDY3_P0_R1_STOPPED_SOME_TARGET_ROLE_HAS_NO_EXECUTABLE_GENUINE_I3_CONTRAST
```

**If replay passes**, the state advances to
`STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT` and one Azure
containerized GPU job may run the repaired pilot: one checkpoint at a time,
fp16, evaluation mode, no sampling, no gradients, no adapters, no quantization,
no hosted inference, no local workstation model execution. Use the exact
`RT`/`RL`/`RI` model and tokenizer repository identities and immutable revisions
recorded by P0-T and carried in `p0_r1_protocol.json`.

## 4. What the successor must count

Maintain three counter views:

1. the **immutable historical P0-T snapshot** — 4,956 encodes, 3 tokenizer
   identities — carried forward unchanged;
2. the **P0-R1 attempt counters**, cumulative and non-resettable; and
3. the **aggregate view**, where additive counters are summed and identity counts
   are **set cardinalities**, never load-event counts.

`tokenizer_construction_events` is additive and must advance on every tokenizer
construction, including a reload of an already-seen identity.
`distinct_tokenizer_identities_constructed` is a cardinality and stays at 3.

Report `common_prefix_tokens_processed` explicitly. The extra teacher-forced
token changes token processing, not the number of sequence-level prefill
evaluations.

## 5. What the successor must not do

* Edit any byte under `studies/study3/pilot/p0/` or
  `tests/test_study3_p0_feasibility_pilot.py`.
* Rewrite, relabel or re-emit the historical terminal state.
* Widen the pilot, add a row to the frozen corpus, or change a prompt, rendering,
  answer, nuisance state, allocation or ground truth.
* Perform an output-conditioned retry or replace a row. One infrastructure retry
  is allowed only with a signed receipt proving zero new tokenizer, model-load,
  prefill, decode, scoring and generation operations.
* Write to `paper/evidence_ledger.csv`, draw a seed, build a bank, select an
  interface, touch a positive reference, or resolve `OD2` or `UR-22`.
* Begin the final focused methods review of draft-v0.6. That is a **separate**
  fresh session with its own scope.

## 6. After P0-R1 reaches a terminal disposition

Stop. Preserve `frozen = false`, `formal_execution_authorized = false`, no
selected interface or positive reference, unresolved `OD2`, `UR-22` and `RP`
wrappers, no formal seed, bank, development result, confirmation access, winner
or evidence row, and the original research question as unanswered.

If P0-R1 is mechanically feasible, the sole next design action is one fresh,
focused final methods review of draft-v0.6. If P0-R1 fails mechanically, the
successor must choose a narrowly demonstrated repair or stop this Study 3 route;
it may not silently widen the pilot.
