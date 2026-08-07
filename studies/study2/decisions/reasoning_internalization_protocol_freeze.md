# Freeze Study 2 reasoning-internalization protocol

## Decision

Freeze the reviewed Study 2 protocol and deterministic public task banks with
these lifecycles:

- protocol: `FROZEN_AWAITING_STAGE_T`;
- task-bank manifest: `FROZEN_MODEL_FREE_BANKS`;
- methods-review allowance: `SPENT_VERIFIED`.

The successful Stage P state remains
`NONTERMINAL_CHECKPOINT_STUDY2_PROTOCOL_FROZEN_AWAITING_TOKENIZER_GATE_AND_EXECUTION`.
This is not a scientific result and does not authorize Stage T.

## Authorities and starting identity

- Original Stage P authority: 53,018 bytes, SHA-256
  `1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37`.
- Additive Gate A authority: 5,836 bytes, SHA-256
  `e7f015a71e0491aa26f66780e94ad7fd8201b3d1b9411298d92848781310c3c1`.
- Original registered Stage P start:
  `191d4a3596ab64b26f54effb6ccaf6005f229139`, tree
  `9d1c68d895435928a10ac2b0f44d277b370000c1`.
- Reviewed candidate: `97ea5b291aec1bcfc6e5ab9a0de42a6c901afae4`,
  tree `966a31aec9bb4f1aa057e90ef95a6a4134b155ea`.
- Review commit: `86b04db4da1ad701af7a9da8f7fddb711d838dad`,
  tree `6861e1f026ac0e52bc93b65b1343e64c5b9176df`.

## Review disposition

The single 15-item methods review passed with two MINOR findings:

1. disclosed Gate A protocol-selection and winner's-curse risk;
2. unidentified joint power across conjunctive gates.

There were no FATAL or MATERIAL findings. No consolidated correction was used,
and no second redesign or review occurred. The review is 9,741 bytes, SHA-256
`e84607443798d4953a2b59ab7b47e82bd9bf89fe832a3d86de7ec5ab3fd7b139`.

## Reviewed candidate to frozen bytes

The freeze changes only protocol lifecycle, review status, bank-manifest
lifecycle, and the manifest's binding to the frozen protocol hash.

| Artifact | Reviewed candidate SHA-256 | Frozen SHA-256 | Frozen bytes |
|---|---|---|---:|
| Canonical protocol JSON | `a1ae4d18fc88410c00dbe9c211b0ebac723ed67d56732cb73a8bd5080a1d767f` | `2f115e057249fb59e34ef34de2eb71ff042a449bb4ef1637ebec3181aedd7ad5` | 39,357 |
| Protocol schema | `f063328d9fc38288e0b657f4d74c0b9b082d09c55f0ca4a29591fdda26accb38` | `d9f834282038f840707ea694bb5dd5422e87a3ca661eb987b2b9ce631d23b134` | 54,502 |
| Protocol Markdown | `4d58d8c569728d96999135c2bc5c547980a3c0d86b5c5b2c8ca0b87e57edf054` | `4d58d8c569728d96999135c2bc5c547980a3c0d86b5c5b2c8ca0b87e57edf054` | 21,151 |
| Task-bank manifest | `7fa20875b11052f000b3694c76a1f53e4782b987317c94b7f93bff89293d36e7` | `7d07db2b508136229f06a727a3deb787106e2b389bb1207ab2c2d1099b21458f` | 32,337 |

## Frozen model-free banks

| Role | Rows or pair units | Bytes | SHA-256 |
|---|---:|---:|---|
| development | 384 | 752,708 | `7dd19884cc2cb4685863cc9df768347f7cfd52c348e5117ec574b52d3b0cf1d6` |
| behavioral confirmation | 1,536 | 3,068,780 | `cbd20d061ee5bdc8f8484b79005ad7faa018add9ef028da16cd885f2c89ea3a9` |
| mechanistic development candidates | 1,024 | 8,008,776 | `397c752162e41ff1bc83ecf4cf58b768baa6400c9e6d20dc092f317238c1ef66` |
| mechanistic confirmation candidates | 1,024 | 8,102,984 | `61dfaed3b8a56be4d27083bdca5307ea326ecfaeaa26f2d43dd3c8deafd77df6` |

ACR QuickRuns `cmc3` and `cmc4` independently produced these same hashes and
each compared `PYTHONHASHSEED=1` with `PYTHONHASHSEED=777` byte-for-byte.
The manifest records zero role overlap, zero exact or normalized protected-
prompt overlap, 1,106 protected prompts, and 3,968 independently verified task
or pair units.

## Gate A

Gate A is frozen as a future post-T, pre-B-C development decision. Both fixed
families must independently obtain at least 43 target NT correct rows among
their 128 pooled depth-2/depth-3 development rows, with complete finite
execution and intact balance. Forty-two rows do not pass. Controls run the same
development pack but cannot decide the gate. Failure closes protocol v1 and
requires a new version, authority, and seeds; it cannot trigger same-version
repair.

## Candidate validation

- Focused ACR `cmc9`: 41 passed.
- Full ACR `cmca`: 3,537 passed / 15 skipped / 2 disclosed historical
  parser-seal failures.
- Delta from the registered 3,485 / 15 / 2 reference:
  +52 passed / +0 skipped / +0 failed.
- Candidate validator ACR `cmcb`: succeeded, including both Phase 1.0D
  protected rollups.

Final frozen ACR validation is required over the freeze commit. A failure does
not silently unfreeze or alter scientific bytes.

## Claim and operation boundary

All Study 2 claims remain unsupported and preregistered. The freeze establishes
only a reviewed prospective protocol, deterministic public banks, fixed Gate A,
and a later-execution reliability contract.

Stage P tokenizer constructions, model downloads, weight loads, forward passes,
generations, provider calls, lens loads/fits/applies, activations, probes,
patching, ablation, GPU Jobs, Phase 1.0D operations, RQ2/S4 runs, and scientific
evidence rows are all zero. `paper/evidence_ledger.csv` remains at `EV-0016`.

Any later change to a frozen scientific protocol byte requires new authority
and does not inherit this review.
