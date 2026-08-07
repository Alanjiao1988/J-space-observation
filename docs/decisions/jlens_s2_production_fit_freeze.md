# Full-layer S2 production fit freeze

## Decision

Accept the 18 successful registered shard lenses as the only inputs to S2-M0.
The state is:

`NONTERMINAL_CHECKPOINT_JLENS_S2_PRODUCTION_FITS_SEALED_AWAITING_MERGES`

The create-only production prefix is
`jlens-s2/production/20260806T194226Z`. The sealed attempt manifest is 30,965
bytes with SHA-256
`0c1b4c8070f579b1d7fe22b2c0c74cec36b3e8d198dd0ec30bdc48a3c7a8561b`.

## Attempts and quota

The Azure environment exposes five T4 replicas. Starting all 18 registered
primary Jobs exactly once produced:

- 4 primary successes;
- 14 primary infrastructure failures;
- 5 exact checkpoint-bound `resume-1` successes;
- 8 from-scratch `retry-1` successes;
- 1 `retry-1` timeout for the 128-sequence B shard;
- 1 exact checkpoint-bound `resume-2` success.

Total: 33 attempts, 18 successes, and 15 infrastructure failures. Nine
failures created no checkpoint because GPU quota remained exhausted until
their absolute execution deadline. Six failures produced partial checkpoints:

- A129: 88 of 128;
- A434: 24 of 59;
- B065: 32 of 64;
- B434: 32 of 59;
- B493: 32 of 59;
- B129 retry: 88 of 128.

Every partial checkpoint was consumed by exactly one later success under the
same fit image, corpus, shard, dim-batch, layer set, target layer, token
length, and skip rule. Successful shard receipts cover each A1-A600 and
B1-B600 sequence exactly once in the final lens identities.

## Recomputed evaluations

The exact number of recomputed sequence evaluations is unknowable. The
upstream checkpoint is written every eight prompts, so each external timeout
could have completed zero through seven evaluations after its last surviving
checkpoint. Across six partial failures, the registered bound is therefore
zero through 42 potentially recomputed evaluations.

This is disclosed as
`unknown_due_to_uncheckpointed_suffix`; it is not reported as zero. The final
successful lens state contains every registered sequence once, but the
infrastructure may have evaluated an unpersisted suffix twice across failed
and resumed processes.

## Runtime and memory

Successful attempts processed 904 new prompts after loading their starting
checkpoints and recorded 68,291.8117 fit seconds (18.9699 T4-hours). Their
maximum peak-reserved-memory ratio was 0.2661. The remaining 296 registered
prompt contributions were inherited from exact failed-attempt checkpoints.
Final cost accounting additionally includes failed partial attempts, image
loads, merges, and diagnostics and is reported in the final S2 handoff.

## Verification

The hardened analysis image
`sha256:25fdd44b6d9ce103ca3e0c9aa4941a023caf95ab69b5c38ec89fab3e0934c27f`
loaded and SHA-checked all 18 success receipts and six checkpoint manifests,
validated the 33-attempt state machine, and wrote the attempt manifest
create-only. It did not load or apply a lens.

No official S3 benchmark tokenizer/model operation, Phase 1.0D operation, or
E1/E2/RQ2 operation occurred.
