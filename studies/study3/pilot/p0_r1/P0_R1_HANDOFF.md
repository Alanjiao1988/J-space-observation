# P0-R1 cross-session handoff

> **Continue from the published P0-R1 registration commit. Do not return to the
> baseline of authority §1.**

Authority: [`../../prompts/study3_v0_6_p0_r1_authority.md`](../../prompts/study3_v0_6_p0_r1_authority.md)
§6, §7 and §10.

## 1. What the successor session inherits

| item | value |
| --- | --- |
| entry state | `STUDY3_P0_R1_REGISTERED_AWAITING_REPLAY_GATE` |
| authority | `studies/study3/prompts/study3_v0_6_p0_r1_authority.md`, 19,632 bytes, sha256 `f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200845ddc19d2`, LF only, no trailing newline |
| candidate | draft-v0.6, `studies/study3/protocol/interface_calibration_rendering_registry_v0_6.json` |
| corpus | the frozen 35-cell / 70-member P0 corpus, reused byte-exactly |
| execution flag | `p0_r1_pilot_execution_authorized = true`, **not yet consumed** |
| every other authority flag | false; `interface_selected`, `positive_reference` and `rp_wrapper` are **null** |

The authority explicitly permits continuation **from the published P0-R1
registration commit**, rather than requiring a return to the §1 baseline.

## 2. The exact first command

The registered replay gate is the first action, and nothing else may precede it:

```
az acr run --registry acrjspaceobssea0708231738 \
  --subscription 943bacdf-8b6e-4e3a-8126-a149f623d32e \
  --platform linux/amd64 \
  -f p0_r1_acr_task.yaml \
  --set COMMIT=<the published P0-R1 registration commit> \
  --set IMAGE=<the P0-R1 image, by immutable digest> \
  <context-dir>
```

The image digest is `null` in the pre-execution receipt until the successor
builds the image. It is deliberately not a placeholder: the task cannot run until
a real digest is recorded.

Locally, the same derivation is available without a container and without any
model operation:

```
python studies/study3/pilot/p0_r1/p0_r1_replay_gate.py --check
```

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
