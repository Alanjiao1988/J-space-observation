# Study 2 Stage P final handoff

## Terminal Stage P state

`NONTERMINAL_CHECKPOINT_STUDY2_PROTOCOL_FROZEN_AWAITING_TOKENIZER_GATE_AND_EXECUTION`

This is a reviewed prospective design and deterministic public-bank freeze. It
is not empirical Study 2 evidence. Stage T, tokenizer construction, model
loading, behavior, activation, probe, patching, and J-lens execution were not
started.

## Repository identities

Validated freeze identity:

- commit: `d5e8e19c025410fda7c9eb430f507a201a18c9cd`;
- tree: `b044133055c697cad8828664254143f3b83f68d5`;
- branch: `main`;
- final focused/full/validator source: this exact commit and tree.

The ledger and handoff closure commit that contains this document is necessarily
reported in the operator response because a document cannot embed the SHA of
the commit that contains itself.

Registered Stage P execution start:

- commit: `191d4a3596ab64b26f54effb6ccaf6005f229139`;
- tree: `9d1c68d895435928a10ac2b0f44d277b370000c1`;
- ancestor of the validated freeze: yes.

Operator handoff checkpoint at takeover:

- commit: `1b7edc1d2108a98ca12db63bb6a76274cc6f726a`;
- tree: `fdcacc54d83ab16e1be7b034283d502a1e9f0b37`.

## Authorities

| Authority | Bytes | SHA-256 |
|---|---:|---|
| Original Stage P prompt | 53,018 | `1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37` |
| Gate A additive operator amendment | 5,836 | `e7f015a71e0491aa26f66780e94ad7fd8201b3d1b9411298d92848781310c3c1` |

The original authority was not edited. The additive authority selects Gate A
after the operator delegated the choice and instructed execution to continue.

## Ordered Stage P commits

| Commit | Tree | Subject |
|---|---|---|
| `4feb1440ee9eae35383cb771332429c0f2464b0f` | `d358ab94b2f80c39a8a728e18408749df1549ed5` | Correct Study 2 protocol candidate |
| `c3077ef97a40a72ad95eaec3e6558fa351146d31` | `c12fac6a30ea110ee7b491205f1f1dfe961acfa8` | Add Study 2 ACR bank export task |
| `7744cfedbf221bf87ed8a2643d2e8e5a11e2e60c` | `fb6664008037f839fcee9149bfd324b26d2a2e90` | Enforce Study 2 role disjointness |
| `90c729675de4ab742727efb5878f05c9778e2050` | `990f39fd3ecdbf1ee5e3f8f202cbca813dbb4c05` | Canonicalize Study 2 balance tables |
| `b4d8eaa89b6b0a3973c161b7dce3eb20b143b83d` | `e172181043dc63fbd7df0d6ec5a3fda4f20458a0` | Push Study 2 bank export image |
| `098fb2e0bc81ae71272b8c8262accb33b450a64c` | `c5765f76c6a1ae9a8074440c2355c837a7b451c5` | Add Study 2 sensitivity analysis |
| `3dafd7c7cc730821b365c12599a51c44fcb11420` | `384d12fc366a6cf136e56b45045ebab12d09bb39` | Bind sensitivity output to ACR run |
| `def1e743ba68744adff208eb8bcede18e7fa0b32` | `a699c84077068348e9023030cefdb0247f04f2f0` | Record Stage P amendment requirement |
| `e12457cf90f0105ac0ae04ab9142bbdc3a35d18f` | `1373020a263677150130a587e9038ae25dd52ef2` | Authorize Study 2 Gate A amendment |
| `09d922774e19ce4a58cbea09bdedcd3792b4f4a5` | `4623cbbe29278aef2a559483249872f9bf3e4f25` | Adopt Study 2 Gate A candidate |
| `5fe5aff10aae5e1094b8430d45edf70972842363` | `83d4dda8308e6d8443c3ee247ca8bff1eb34b445` | Add Study 2 model-free task banks |
| `97a217c7db666a27aa2161d5862a3a33838c155b` | `591cc2ff7226d11ff655f83a6af1bafd5e3f892d` | Add bounded Stage P full-suite runner |
| `97ea5b291aec1bcfc6e5ab9a0de42a6c901afae4` | `966a31aec9bb4f1aa057e90ef95a6a4134b155ea` | Restore Stage P full-suite integration |
| `86b04db4da1ad701af7a9da8f7fddb711d838dad` | `6861e1f026ac0e52bc93b65b1343e64c5b9176df` | Complete Study 2 methods review |
| `d5e8e19c025410fda7c9eb430f507a201a18c9cd` | `b044133055c697cad8828664254143f3b83f68d5` | Freeze Study 2 Stage P protocol |

No commit was amended. Every push was non-force and checked as a fast-forward.
No rebase was used.

## Frozen protocol package

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Canonical protocol JSON | 39,357 | `2f115e057249fb59e34ef34de2eb71ff042a449bb4ef1637ebec3181aedd7ad5` |
| Protocol schema | 54,502 | `d9f834282038f840707ea694bb5dd5422e87a3ca661eb987b2b9ce631d23b134` |
| Protocol Markdown | 21,151 | `4d58d8c569728d96999135c2bc5c547980a3c0d86b5c5b2c8ca0b87e57edf054` |
| Methods review | 9,741 | `e84607443798d4953a2b59ab7b47e82bd9bf89fe832a3d86de7ec5ab3fd7b139` |
| Freeze decision | 5,025 | `aa0151be87a43719ef8056b45d532281178ca5ea55480d46b0f7d484c7caff4d` |
| Power/sensitivity pack | 9,291 | `f2514ffe9bc5cff80ef164f5b05a3cd90bbdfb9550af49b755accd3cbc3589ff` |

Frozen source identities:

| Source | Bytes | SHA-256 |
|---|---:|---|
| `src/jspace_observation/study2_protocol.py` | 72,263 | `852073bd125aaf119ba7897666d49075c93a660ad7701d387e5bdbbfe71dbeaa` |
| `src/jspace_observation/study2_task_bank.py` | 29,847 | `e0053afec6a1c6abb712f292605f038263f921e34414d545876bdafe11a22d7e` |
| `scripts/build_study2_task_bank.py` | 1,583 | `d3bd127126158fdcef1c194bace3c42045188760bf34f91ef0c0302a36729b82` |
| `scripts/validate_study2_protocol.py` | 8,717 | `ba6b55e3cd5845c5ff4e9d8a2233b1f1d6cccb96a8988847c64db7c0d296dd8b` |
| `scripts/analyze_study2_stage_p_sensitivity.py` | 8,768 | `9e17ad590c0cf79bd68c198c4d46ee090f948ee972116161679fbc418d756a02` |

## Frozen model identities

These identities were recorded only; no tokenizer or model was constructed or
loaded.

| Role | Model | Revision |
|---|---|---|
| target | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| lineage base | `Qwen/Qwen2.5-Math-1.5B` | `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2` |
| instruction control | `Qwen/Qwen2.5-Math-1.5B-Instruct` | `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35` |

J-lens source identity:
`anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`.
M1200 remains target-only, secondary, and non-rescuing.

## Frozen banks and manifest

| Role | Rows or pair units | Bytes | SHA-256 |
|---|---:|---:|---|
| development | 384 | 752,708 | `7dd19884cc2cb4685863cc9df768347f7cfd52c348e5117ec574b52d3b0cf1d6` |
| behavioral confirmation | 1,536 | 3,068,780 | `cbd20d061ee5bdc8f8484b79005ad7faa018add9ef028da16cd885f2c89ea3a9` |
| mechanistic development candidates | 1,024 | 8,008,776 | `397c752162e41ff1bc83ecf4cf58b768baa6400c9e6d20dc092f317238c1ef66` |
| mechanistic confirmation candidates | 1,024 | 8,102,984 | `61dfaed3b8a56be4d27083bdca5307ea326ecfaeaa26f2d43dd3c8deafd77df6` |
| frozen task-bank manifest | - | 32,337 | `7d07db2b508136229f06a727a3deb787106e2b389bb1207ab2c2d1099b21458f` |

There are 64 development and 256 confirmation rows per family x depth
behavioral cell. There are 256 candidate pair units per role x family x depth
2/3 mechanistic cell.

Within every behavioral cell:

- A/B/C/D labels are exactly 16 each at n=64 or 64 each at n=256;
- T-A/T-B are exactly 32 each at n=64 or 128 each at n=256;
- start, pre-answer, final-state, and final-operator spreads are at most one;
- every registered single-field conditional label spread is at most one.

Within every mechanistic cell:

- recipient labels are exactly 64 each and templates exactly 128 each;
- the hash front/back partitions are exactly 128/128;
- each partition has 32 of every recipient label and 64 of each template;
- state/operator and conditional-label spreads are at most one.

Verification results:

- independently reconstructed task/pair units: 3,968;
- semantic role-pair overlap counts: all zero;
- protected prompt corpus: 1,106 prompts;
- exact protected-prompt overlap: zero;
- normalized protected-prompt overlap: zero;
- pairwise-distinct `a_d`, `a_r`, and `a_x`: every pair;
- shared exact option set and mapping: every pair;
- no-op, same-intermediate, same-answer, random-donor, and wrong-position
  definitions: every pair;
- Stage T selector inputs: tokenizer mechanics and frozen hashes only.

## Gate A and design sensitivity

Model-free ACR QuickRun `cmc2` computed the exact sensitivity pack. Gate A
uses target NT compositional development rows only, pooled within each family:

- n=128 per family;
- null accuracy .25;
- exact one-sided alpha .025;
- critical count 43, exact upper tail .018218515933;
- count 42 does not pass, upper tail .028760674518;
- both families must pass.

All three models later run the same complete development pack; controls cannot
decide Gate A. Confirmation stays unopened until the decision is sealed.
Failure closes protocol v1 and requires a new version, authority, and seeds.

The same sensitivity pack records:

- exact n=64 and n=256 power grids against chance;
- P[confirmation accuracy >= .50] from .000754 at true p=.40 to .999514 at
  true p=.60;
- paired target-control MDEs across discordant proportions;
- n=128 standardized paired-effect sensitivity of .247627 at 80% and .286512
  at 90% power for one-sided alpha .025.

These are marginal quantities. Joint power across all conjunctive gates is not
identified.

## Methods review

The unique 15-item formal review was performed over the fixed candidate bytes
at commit `97ea5b291aec1bcfc6e5ab9a0de42a6c901afae4`.

Initial findings:

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| S2P-R-01 | MINOR | Gate A conditions confirmation on target development success | Accepted and disclosed; gate can only open/close |
| S2P-R-02 | MINOR | Joint power across conjunctive gates is not identified | Accepted and disclosed; no sample/threshold change |

FATAL findings: zero. MATERIAL findings: zero. Consolidated correction:
not used. Same-checklist correction verification:
`NOT_REQUIRED_NO_FATAL_OR_MATERIAL_CORRECTION`. The review allowance is
`SPENT_VERIFIED`.

## ACR generation and validation

Authoritative successful runs:

| Run | Commit | Purpose | Status | Result |
|---|---|---|---|---|
| `cmc2` | `e12457c` | Gate A power/sensitivity | Succeeded | exact model-free sensitivity pack |
| `cmc3` | `09d9227` | final candidate bank generation | Succeeded | generated, independently verified, hash-seed repeat, OCI export |
| `cmc4` | `09d9227` | independent repeated generation | Succeeded | same four bank hashes |
| `cmc9` | `97ea5b2` | candidate focused tests | Succeeded | 41 passed |
| `cmca` | `97ea5b2` | candidate full suite | Succeeded | 3,537 passed / 15 skipped / 2 historical failures |
| `cmcb` | `97ea5b2` | candidate validator | Succeeded | package, banks, protected bytes passed |
| `cmcc` | `d5e8e19` | frozen focused tests | Succeeded | 41 passed |
| `cmcd` | `d5e8e19` | frozen full suite | Succeeded | 3,537 passed / 15 skipped / 2 historical failures |
| `cmce` | `d5e8e19` | frozen validator | Succeeded | final state, ancestry, banks, anchors, EV-0016, zero operations passed |

Full-suite reference: 3,485 passed / 15 skipped / 2 historical failures.
Final delta: **+52 passed / +0 skipped / +0 failed**.

The two accepted failures remain exactly:

- `tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last`;
- `tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix`.

Pre-final failed harness runs were retained rather than hidden:

| Run | Failure | Scientific operation |
|---|---|---:|
| `cmbu` | Windows CRLF task wrapper | 0 |
| `cmbv` | deterministic cross-role semantic collision exposed | 0 |
| `cmbw` | manifest balance-key canonicalization exposed | 0 |
| `cmc7` | four direct integration regressions plus two historical failures | 0 |

`cmbx` succeeded in generation validation but used a non-pushing task form; its
output was not used. All final bank bytes came from `cmc3`.

## Protected-state recheck

| Protected identity | SHA-256 |
|---|---|
| Study 1 final handoff | `5870c82b15575086f5c29c34661d89d96d265848846e3de74162da8919951f77` |
| S3 protocol JSON | `bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625` |
| S3 freeze decision | `d7d9623e3668b5469b426ba45671f267b631599e44f598f710f6c16564a96b48` |
| S2 manifest | `9d10a4b07a8133b7241ce9067649ebf1de48429cf7c04e0495b4c3fe90e58e47` |
| A600 seal | `4032c8f30ec6aec2f12cbf0a303466a0fe66745617266dcc0fa3d2289e731dd7` |
| B600 seal | `b62cd7f69aaa4a662144d8a8b75e3165330c9369990a52dbee85bb1b06b33ad4` |
| M1200 seal | `9716c3802625176060b3c2a479f7860cf4045807a45c6de346833a3b66e00138` |
| E0 artifact manifest | `6d11b09b39bbeead9b38fdb23be47a4247245fb55e6b6b665b817241519df60f` |
| E0 terminal receipt | `e7daad69a81377aba05be2617c07522d8d04552e594bc2cdc8318b057a83f218` |
| Phase 1.0D capacity certificate | `20e486e05a5f076b720ca12db3459b5a1c2c42e95684977dfdcff19d6da055d3` |
| Phase 1.0D capacity manifest | `23016ad15430b1720e4b37033a3638bf45e817ac00513292d138d26e0ed0a834` |

Phase 1.0D protected v1: 152 files, zero differences, rollup
`436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd`.

Phase 1.0D protected v2: 36 files, zero differences, rollup
`ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a`.

Study 1 remains `INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY`. Phase 1.0D
remains `BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`. EV-0016 is unchanged.

## Files added or modified in Stage P

Protocol and Study 2:

- `studies/study2/README.md`;
- `studies/study2/STAGE_P_FINAL_HANDOFF.md`;
- `studies/study2/prompts/stage_p_gate_a_operator_amendment.md`;
- `studies/study2/protocol/reasoning_internalization_protocol.json`;
- `studies/study2/protocol/reasoning_internalization_protocol.schema.json`;
- `studies/study2/protocol/reasoning_internalization_protocol.md`;
- `studies/study2/protocol/reasoning_internalization_protocol_review.md`;
- `studies/study2/protocol/stage_p_power_sensitivity.json`;
- `studies/study2/protocol/stage_p_operator_amendment_required.md`;
- `studies/study2/decisions/reasoning_internalization_protocol_freeze.md`;
- all five files under `studies/study2/data/`.

Source, tests, and ACR tasks:

- `src/jspace_observation/study2_protocol.py`;
- `src/jspace_observation/study2_task_bank.py`;
- `scripts/build_study2_task_bank.py`;
- `scripts/validate_study2_protocol.py`;
- `scripts/analyze_study2_stage_p_sensitivity.py`;
- `tests/test_study2_protocol.py`;
- `tests/test_study2_task_bank.py`;
- `tests/test_phase1_0d_build_provenance.py`;
- `infra/azure/acr_tasks/study2_generate_banks.sh`;
- `infra/azure/acr_tasks/study2_generate_banks.yaml`;
- `infra/azure/acr_tasks/study2_bank_output.Dockerfile`;
- `infra/azure/acr_tasks/study2_full_tests.sh`;
- `infra/azure/acr_tasks/study2_full_tests.yaml`.

Documentation and ledgers:

- `README.md`;
- `docs/thread_handoff.md`;
- `docs/decision_log.md`;
- `docs/run_log.md`;
- `docs/literature_notes.md`;
- `paper/methods_ledger.md`;
- `paper/limitations_ledger.md`;
- `paper/claim_evidence_matrix.md`;
- `paper/artifact_index.csv`.

The original Stage P authority, bootstrap handoff receipt, Study 1 artifacts,
Phase 1.0D artifacts, and `paper/evidence_ledger.csv` were not modified.

## Zero-operation statement

Stage P counts:

- target tokenizer constructions: 0;
- lineage-base tokenizer constructions: 0;
- instruction-control tokenizer constructions: 0;
- model downloads: 0;
- weight loads: 0;
- forward passes: 0;
- generations: 0;
- semantic-review/provider calls: 0;
- lens loads, fits, or applies: 0;
- activation operations: 0;
- probe fits: 0;
- patching operations: 0;
- ablations: 0;
- GPU Jobs: 0;
- Phase 1.0D operations: 0;
- RQ2/S4 runs: 0;
- scientific evidence rows: 0.

GitHub was used only for Git transport. No Actions workflow, PR, issue,
release, GitHub artifact, GHCR, Package, or Codespace was created.

## What is established and what remains unmeasured

Established:

- one reviewed, machine-checkable prospective Study 2 protocol;
- two programmatic compositional families and two balanced templates;
- exact public deterministic banks and independently reconstructible truth;
- one fixed common-support Stage T selector;
- one exact two-family Gate A;
- closed behavior, mechanism, probe, J-lens, operational, and composite rules;
- a non-scientific later-execution reliability contract;
- one spent methods-review allowance with no FATAL/MATERIAL defect.

Completely unmeasured:

- option-token support in any of the three tokenizers;
- exact input lengths and answer positions;
- Gate A behavior;
- target or control restricted logits;
- any model accuracy, probability, or margin;
- any hidden state, activation, patching, probe, or ablation effect;
- any M1200/A600/B600 Study 2 readout or coordinate swap;
- any internal-computation, distillation-association, or J-space result.

The next operation requires a separate Stage T authority. This handoff does not
grant it.
