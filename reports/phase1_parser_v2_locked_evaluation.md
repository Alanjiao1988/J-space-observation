# Phase 1.2B Parser-v2 Locked Evaluation — Formal Result

Status: **complete and closed**. The 120-case locked holdout is retired.

This is evaluator validation, not model evaluation. No target model was
downloaded, loaded, or run, and no GPU was used at any point.

## Formal decision

| Field | Value |
| --- | --- |
| Formal decision | **FAIL** |
| Decided (UTC) | `2026-07-25T08:01:34Z` |
| Formal evaluation ordinal | 1 (the single authorized evaluation) |
| Holdout retired | yes |
| Holdout spent | yes |
| Parser re-run | no |
| Manual override | no |
| Metric retry allowed | no |
| Prediction re-run allowed | no |
| Mandatory gates | 34 |
| Gates passed | 32 |
| Gates failed | 2 |
| Gates NA/invalid | 0 |
| Scored rows | 120 |

## Failed mandatory gates

| Gate | Observed | Population | Frozen limit | Outcome |
| --- | --- | --- | --- | --- |
| `boxed_final_miss` | 1 | 20 (strata `S01`, `S02`) | ≤ 0 errors, ≤ 1/50 rate | FAIL |
| `wrong_span` | 2 | 80 (`expected_present`) | ≤ 1 error, ≤ 1/50 rate | FAIL |

Offending cases:

- `boxed_final_miss`: `PV2-558779a7e52af7e736d3`
- `wrong_span`: `PV2-558779a7e52af7e736d3`, `PV2-73e4060ef6bd6cd63e40`

## Report-only aggregates

These are descriptive and are not acceptance gates.

- Overall typed agreement: 116/120 (`29/30`).
- Mismatched cases: 4 — `PV2-406d4d4c3ba1a1b8c286`, `PV2-558779a7e52af7e736d3`,
  `PV2-73e4060ef6bd6cd63e40`, `PV2-78396f528ee910ba7a09`.
- Material-error cases: 1 — `PV2-406d4d4c3ba1a1b8c286`.
- Dataset: 120 cases across 12 strata, 10 cases per stratum.

## Run identity

| Field | Value |
| --- | --- |
| Authorization ID | `pv2-locked-654f3bb-66588c8b-canon` |
| Implementation commit | `654f3bb463fedc33b0638b77fefdd9b2b9d1c9c2` |
| Runtime image digest | `sha256:7ef281187f04692fa17a476c2a3265de051de2300bcd8c3242639b8b4ca6a489` |
| Registered parent prefix | `phase1-evaluator-validation/parser-v2-v1/20260716T024856Z` |
| Scoring actor | `stage-e-managed-runtime` |
| Scoring execution ID | `stage-e-e5e938a4db1c1910f8528dacd37a4b6a` |
| Scoring retry kind | `scorer_infrastructure` |

## Execution history

Exactly three container executions ran in total.

| UTC | Execution | Stage | Outcome |
| --- | --- | --- | --- |
| `2026-07-25T04:15:48Z` | `pv2-p-76a4018ffd782aa1e8398853-mqmkmxg` | P | `PREDICTIONS_VERIFIED`, 120 inputs, 120 parser-v2 and 120 legacy predictions, `labels_accessed: false` |
| `2026-07-25T06:28:32Z` | `pv2-e-66f225af8c562425fe168b8c-8tgogbi` | E (primary) | `STAGE_E_ERROR:EXECUTION_REJECTED:RuntimeError`, rejected before any label access or scientific write |
| `2026-07-25T08:01:07Z`–`08:01:42Z` | `pv2-e-f2fcd3f9456d44ff15224f25-l33zhbh` | E (`scorer_infrastructure` retry) | `Succeeded`; the labels were opened, scored, and retired exactly once |

The primary Stage-E attempt failed for an infrastructure reason only: after the
frozen finalizer installed its subprocess audit guard, a lazy Azure Identity
import called `platform.platform()`, which shells out to `uname -p`; the guard
correctly blocked the subprocess and the attempt aborted. The labels were never
opened by that attempt. It is recorded as an abandoned attempt, and the single
authorized retry kind `scorer_infrastructure` was used for the successful run.

## Holdout state chain

The state sequence advanced `00_draft_protocol` → `12_closed`, ending in
`CLOSED`:

- `12_closed_receipt.json`: `state = CLOSED`, `previous_state = SCORES_VERIFIED`,
  `previous_receipt_sha256 = f6b00cafcee473da3affb7921274c1f15b0042058c0ec224bab2eb12040ba02d`,
  `outcome = FAIL`, `holdout_retired = true`, `holdout_spent = true`.
- `scoring_attestation.json`: `outcome = FAIL`, `formal_evaluation_ordinal = 1`,
  `metric_recompute_allowed = false`, `overwrite = false`.

## Authenticated artifact hashes

State prefix `…/state/pv2-locked-654f3bb-66588c8b-canon`:

| Artifact | SHA-256 |
| --- | --- |
| `09_predictions_verified_receipt.json` | `0995f687e5a8d6cbc842223084f7a7e5874b760bd5492d2c4aba531c92cf7217` |
| `10_labels_read_receipt.json` | `6b4977d6f3dc3334ece2fc6b439875aea31e6850432934dd74d84bbff8026bfb` |
| `11_scores_verified_receipt.json` | `f6b00cafcee473da3affb7921274c1f15b0042058c0ec224bab2eb12040ba02d` |
| `12_closed_receipt.json` | `992b857aeb1a95ec650a714c99dbdcdec89bd21ee24338e3e2cfe8288cbff051` |
| `closure_manifest.json` | `97e703e49dc2a6e7fb0901f1cc890e92873f6a745eb7663945c8faff78d1eb38` |
| `scoring_attestation.json` | `17bfbf1c8925e54528de12ba65e8c023140f66d054ca99fb26b5b43d5a3921c8` |
| `scoring_transaction.json` | `8d3dcd2964b5add2ceacbea205e6fc4b1130cb4a4a84915e0d55578552dff68e` |
| `labels_open_transaction.json` | `1e4c3ad1531e94310850f9a51e22c678d48484fc3152083c5f80289db6fd3fcb` |
| `retry_scorer_infrastructure_receipt.json` | `31e4e09f321ab231d69cb6c5f6b9c246a498e732db5eb1269390cdf0b005c072` |

Score prefix
`…/scores/pv2-locked-654f3bb-66588c8b-canon/attempts/scorer_infrastructure/78ddfd37791611e08c59c834221608357212def40de544925137a8dc2d08442a`:

| Artifact | SHA-256 | Bytes |
| --- | --- | --- |
| `scores_manifest.json` | `a74f42335eb92b85b3994d15ba73f2212392b43de02fe58e951f51b94d2df386` | 4957 |
| `locked_evaluation_decision.json` | `2b4386048e57ff847a5f447a0420005db3a2fe53902d0ac91ef66a9511313efb` | 2690 |
| `retirement_record.json` | `0083e49d1fd59504dbf8a6ea94c6710e6f3ed96db589e8cdf65f74c366343a7a` | 2803 |
| `locked_evaluation_report.md` | `17087f8c555ecde39681658287dacf0c33a9941c2fa0148d17d3d9d9f5381b49` | 673 |
| `locked_evaluation_metrics.json` | `7e735622f89ef50d725a60d389f74ab83e6dccaef84e8024bd5e8e84c7a8a521` | 45166 |
| `locked_evaluation_failures.jsonl` | `f2dd18671118040e35255b691b6eb67a53e4d1e6fd801407e43db13c13b9004f` | 2581 |
| `scoring_ledger.jsonl` | `c8ace06e413f7915188eb2ff3d0ee6f0b857bc8b79a77bce13c8be298c674eeb` | 650946 |
| `.scores_reservation.json` | `5d0c42df14145ae594fc5e16ba7dcb2758465e16fda2210eb951efc39d453894` | 435 |

Visibility and abandoned-attempt records:

| Artifact | SHA-256 |
| --- | --- |
| retry `stage_e_visibility.json` | `447f3f6551efc1c2bc660b5822b70c7a939e7fb225457acc5ce2fa4573615039` |
| `abandoned_attempt.json` (primary) | `6e38f1f3c29cf8d7845d643d34aa8726a5ff3e010877b16e1135a3ec08214ea9` |
| primary `stage_e_visibility.json` | `d397d1d6c0588149575181db8d0007a844cb92231bb206ffa0be9b33ee37f02e` |
| primary `.scores_reservation.json` | `7ee1af764cfb65004dcae3d55b7408485b62ef4cb62b4eabf0da4f83a2fc3104` |

Frozen input bindings recorded identically by the decision, metrics, closure
manifest, retirement record, attestation, and every ledger row:

| Binding | SHA-256 |
| --- | --- |
| `locked_input_sha256` | `2d60483e7f7a2ce1883acca2dcf9a6771f84b54d596ab2e02ed4a39d937c4e3e` |
| `locked_manifest_sha256` | `f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260` |
| `labels_sha256` | `44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af` |
| `labels_manifest_sha256` | `aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6` |
| `prediction_manifest_sha256` | `1a406a36a62ebbdba86382cb4f60dfd56bb292ccb0cf37346ece179cdfdba492` |
| `prediction_seal_sha256` | `1859a0b4efaa388c6dfbbde06c534d83d5a125c96cb6ccc0da0132f15c7d1a12` |
| `authorization_lock_sha256` | `d461c08fc0065f6dbc02ef490ee13e41378e37a42c5cc321b2b82a5837809c8f` |
| `authorization_manifest_sha256` | `f1354f5e3408fc375b340bf3254c53c135b2875b19d3a69bf7b2d3077a847c99` |
| `implementation_manifest_sha256` | `3ae11fc03b73252753c34ee12803bdae8781911ab8f7c8586d74bf31128146d2` |
| `config_sha256` | `9a0dca61e7ba3236caf84722fde9b5c6de815cb681f041b4d1ede65161a8ece9` |
| `case_universe_sha256` | `1e21e61f9a7e2cc8b337c3f60a0da31aafd6cc522c91f35d2aad46f2d281b41a` |

## Independent post-result verification

The single authorized post-result review recomputed the outcome directly from
the sealed `scoring_ledger.jsonl` and the frozen gate contract in
`docs/phase1_parser_v2_acceptance_gates.json`, without re-reading labels,
re-running the parser, or writing any evaluation state.

All 38 independent checks agreed with the sealed artifacts:

- ledger integrity: 120 rows, 120 unique case IDs, contiguous `row_index`
  `0…119`, and a self-consistent declared `row_count`;
- provenance: all 10 sampled binding fields are constant across every row and
  equal to the decision record;
- gates: `boxed_final_miss` 1/20 and `wrong_span` 2/80, with both offending
  case sets contained in their frozen populations, and both derived as failing
  against the frozen error limits;
- populations: `expected_present` = 80 and boxed strata (`S01`, `S02`) = 20
  cases, matching the frozen gate denominators;
- aggregates: typed agreement 116/120, 4 mismatched cases, 1 material-error
  case, all with identical case-ID sets;
- tallies: 34 mandatory gates, 32 passed, 2 failed, 0 NA/invalid; and
- derivation: `FAIL` follows because at least one mandatory gate failed.

## Interpretation and boundary

- Parser v2 **did not** meet the preregistered locked acceptance gates. The
  formal outcome is FAIL.
- The failure is concentrated in span recovery: a single case
  (`PV2-558779a7e52af7e736d3`) trips both failing gates, and one further case
  (`PV2-73e4060ef6bd6cd63e40`) trips `wrong_span`.
- The 120-case locked holdout is now spent and retired. Any modified parser
  requires a newly constructed holdout; this one must not be reused.
- Fixtures are operational evaluator cases, not behavioral samples, and
  operational consensus references are not human ground truth.
- No hidden-reasoning, invisible-CoT, internal-workspace, or J-space claim
  follows from this result.

## Infrastructure remarks

The frozen scientific code was not modified. Two infrastructure-only
incompatibilities in the surrounding runtime had to be worked around outside
the repository to let the frozen finalizer run at all:

1. Azure Identity must be imported before the Stage-E subprocess audit guard is
   installed, otherwise `platform.platform()` triggers a blocked `uname -p`.
2. The frozen label-manifest validator expected a minimal manifest shape, while
   the authenticated manifest legitimately carries additional reviewer,
   consensus, and arbitration metadata.

Neither workaround touched parser bytes, holdout bytes, metric semantics,
acceptance gates, or PASS/FAIL scoring behaviour, and both were confined to the
orchestrator host outside the committed tree.

## Post-result handling

Authenticating the artifact hashes above required read access to the results
container, which the control identity did not hold. A temporary
`Storage Blob Data Reader` assignment was granted to
`id-jspace-parser-v2-control-sea`, scoped to the `jspace-results` container
only, and removed once verification was complete. Removal is confirmed: the
container scope carries no role assignments, and the identity holds no
blob-data role anywhere in the subscription.

The locally downloaded copy of the artifact graph was then shredded from the
orchestrator host. This included the only on-host file containing label bytes,
`scoring_ledger.jsonl` (120 `label_record_base64` values), whose identity was
re-confirmed against
`c8ace06e413f7915188eb2ff3d0ee6f0b857bc8b79a77bce13c8be298c674eeb`
immediately before deletion. Every deleted file is immutable in Blob storage
and its SHA-256 is recorded above, so no unique evidence was lost.

All immutable claims, DNS TXT records, the three ACA Jobs, seals, decisions,
coordination evidence, and build and runtime records were retained unchanged.
