# Stage P0-R1 generation-3 replay submission: operational stop

> **Operational disposition:** `STOP_NO_MODEL_OPERATION`
>
> **Scientific state:** unchanged and not evaluated. The replay gate did not
> start, so no scientific terminal state was emitted.

The single generation-3 replay envelope was consumed exactly once. Preflight
passed, including an unambiguous proof that
`job-jspace-s3-p0r1-pilot-g3` was absent. The subsequent `live-replay`
invocation exited 1 while Azure CLI was packing the committed Git context.
The captured stderr records a local `WinError 3` path failure.

No ACR run identity or replay attempt ID was returned. The complete captured
stdout raw log is the published zero-byte
`p0_r1_replay_raw_log.txt`. No canonical replay artifact was emitted, and no
reconstruction receipt was created. In particular, this publication does not
repair, regenerate, substitute, or imitate any of:

- `P0_R1_REPLAY_DISPOSITION.md`
- `p0_r1_replay_counters.json`
- `p0_r1_replay_receipt.json`
- `p0_r1_replay_result.json`

The active lock's fail-closed rule therefore applies: a replay, capture, or
reconstruction failure, or any ambiguity, publishes the registered stop and
performs no model operation. `launch-pilot` was not invoked; no GPU job,
GPU execution, CPU recovery execution, tokenizer, checkpoint, model weight,
prefill, S4 call, scored row, or model-evaluation equivalent was consumed.
Replay retry is not authorized.

The exact preflight and replay logs, preflight Azure absence proof, both
pre-replay head proofs, supersession proof, failure stderr, conservative
counters, and machine-readable stop receipt are published beside this file.
The 108,625,920-byte committed-context tar remains preserved in the operator
session artifact store with SHA-256
`7b0b2980df21897c9a5aec892c411f8c5e3638b85539adacb119a54d267ac9e4`;
it is derived from the exact starting commit and is not a replay result.

No focused methods review begins here. Draft v0.6 remains neither reviewed nor
frozen; interface, positive reference, and RP wrapper remain null; no evidence
row is added; formal execution remains unauthorized.
