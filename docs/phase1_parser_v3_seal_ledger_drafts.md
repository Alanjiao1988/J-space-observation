# Parser-v3-v1 seal — ledger and log drafts

Status: **drafts for the main agent to apply and commit.** Track D has no git
write access. Nothing in this file has been committed. Each section names its
target file and whether it is an append or a replacement.

Every number here comes from one of three sources, and the source is stated:

* **evidence** — read from the two durable Blob objects
  `crosscheck_report.json` (SHA-256 `893b24a52172aed1b3223dcf15d85d2e286762c50b4258ad10e5586678a0aefc`)
  and `seal_record.json` (SHA-256 `eb11b1f0658ef50d003a2723a846221f22c448ec2e3c6bf117177f2e18a37dd8`),
  both re-hashed locally;
* **attestation** — measured by the main agent with `az` and recorded in
  `docs/phase1_parser_v3_seal_execution_record.json`; Track D did not re-measure it;
* **local** — verified on this machine.

---

## 1. `docs/run_log.md` — APPEND at end of file

```markdown
## 2026-07-25 — Parser-v3-v1 pre-seal cross-check PASSED and the holdout is SEALED

- Objective: execute the one outstanding registered pre-seal check, then seal the
  120-case `parser-v3-v1` holdout if and only if that check passed.
- Transport: the check did **not** run on the orchestrator VM. It ran as a
  short-lived Azure Container Apps CPU job, `job-jspace-parser-v3-seal`, in the
  VNet-integrated environment `cae-jspace-observation-sea-vnet2` on the
  `Consumption` profile, 2 CPU / 4Gi, no GPU. Storage
  `stjspacefiles0709085305` has public network access `Disabled`, so managed
  identity inside the VNet was the only reachable path. No account key and no SAS
  were created, referenced or logged. The VM was separately repaired during this
  round, but it was not used for this work.
- **Cross-check 1 result: PASS.** New set 120 records, retired set 120 records,
  exact collisions 0, normalised collisions 0, numeric-normalised collisions 0.
  Decision `PROCEED_TO_SEAL`. The retired object hashed to its registered digest
  `2d60483e7f7a2ce1883acca2dcf9a6771f84b54d596ab2e02ed4a39d937c4e3e`
  (26651 bytes), so provenance matched.
- Isolation actually exercised: of the three objects under the retired
  locked-inputs leaf, only `locked_inputs.jsonl` was read.
  `.locked_inputs_reservation.json` and `locked_inputs_manifest.json` were listed
  and not read. The report records `label_material_touched: false`,
  `score_material_touched: false`, `rescoring_performed: false`. No retired input
  text left the container; only counts and one-way digests did.
- Guards that had to pass before any comparison was allowed: the registered
  fingerprint functions `fingerprints`, `normalize_text` and
  `numeric_normalized_text` were imported from
  `scripts/build_parser_v3_validation_set.py` and reproduced 5 pinned
  known-answer vectors, and reproduced all 120 records of the committed
  `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json`.
- **Seal: 12 objects at `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/`.**
  `overwrite=false` on every write; size, SHA-256 and ETag round-trip verified for
  all 12; exact membership 12 of 12; `manifests/set_manifest.json` written last at
  order 12. The cross-check report and the seal record are in the sibling prefix
  `20260725T160340Z-runlog/`, which keeps the sealed parent at exactly 12 objects.
- Membership was verified independently of the job: a separate listing under a
  separate identity returned exactly 12 objects in the parent, with byte counts
  matching the staged payload one for one, and 2 objects in the sibling runlog.
- Executions: `job-jspace-parser-v3-seal-57w51qd` (crosscheck, Succeeded),
  `job-jspace-parser-v3-seal-0fz4tkj` (seal attempt 1, Failed by design),
  `job-jspace-parser-v3-seal-61zgric` (seal, Succeeded). Image digest
  `sha256:f13220aed82c320150a63868e4519ec8d3d4dae7331ae4d421257f191c7d2388` for
  both tags; base `python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d`.
- **Deviation: the first seal attempt aborted, and that was correct.** Under
  timestamp `20260725T155224Z` the recommended dry pass had already written
  `crosscheck_report.json`; seal mode re-runs the cross-check and re-writes that
  report, so the upload hit its own `overwrite=false` guard with
  `ResourceExistsError` and the job failed closed with
  `state=BLOCKED_INFRASTRUCTURE`. No seal object was written under that timestamp
  and nothing was overwritten. The timestamp was rotated to `20260725T160340Z`,
  the stale write grant was deleted, a fresh grant was pinned to the new
  timestamp, and mode `seal` ran exactly once.
- **Deviation: no rebuild for the rotation.** The existing image was imported to
  the new tag, so the bytes that sealed the set are provably the bytes that were
  reviewed and that ran the passing cross-check.
- **Deviation, and the one that matters: the ABAC grants enforced nothing.**
  Teardown measured subscription-wide Blob roles for the sealing identity
  `id-jspace-aca-acrpull-sea` (principal
  `78d4348b-57eb-4fb9-aaa7-99148b303292`) as **1, not 0**: an unconditioned
  `Storage Blob Data Contributor` at account scope on
  `stjspacefiles0709085305`, created 2026-07-09, sixteen days before this round.
  Because that assignment was already unconditioned and account-scoped, the two
  temporary prefix-conditioned grants created for this run did not narrow the
  identity's effective permissions at all. The isolation of the retired parser-v2
  labels, scores and scoring ledger therefore rested on the payload's code path,
  on the Track D tests that pin that code path, and on the report's own
  attestations — not on RBAC. The standing assignment was **not** removed: it
  pre-dates this round and other Container Apps jobs depend on it to write
  results. This is recorded as deviation D13 and as limitation L-17.
- Teardown, with actual outputs: both temporary grants deleted; container-scope
  assignments for any principal `0`; control identity
  `1ec93a23-1126-4058-a537-4f1016b8c325` blob-data roles `0`; sealing identity
  blob-data roles `1` (the standing assignment above); job reset to base image
  `j-space-observation@sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac`
  with command `/bin/true`; job secrets `0` and secret references `0`; storage
  `publicNetworkAccess` still `Disabled`; the single-use repository
  `j-space-observation-pv3seal` deleted from ACR; staging context removed.
- Artifact pack:
  `artifacts/phase1-evaluator-validation/track-d1/20260725T160340Z-track-d1-parser-v3-seal/`,
  final state `SEALED`. It is built from the two durable Blob objects rather than
  from the in-container summary, which was ephemeral and is gone; the generator
  re-verifies the seal record's pinned report digest, the verdict and the three
  collision counts across both objects, and every sealed object's digest, byte
  count and order against the registered staging pins.
- Boundary, unchanged: **sealing validates nothing.** No parser-v3 evaluation was
  run, no parser-v3 prediction exists, nothing was scored, and no parser was
  imported. The sealed labels are a two-reviewer-plus-arbiter LLM operational
  consensus, not human ground truth. Isolation between holdout construction and
  parser-v3 development remains procedural, not security-enforced, and this round
  produced a concrete instance of that.
```

---

## 2. `docs/decision_log.md` — APPEND at end of file

```markdown
## 2026-07-25 — Seal the parser-v3-v1 holdout, and disclose that ABAC enforced nothing

Decision:

- The registered pre-seal cross-check against the retired parser-v2 locked inputs
  returned zero collisions on all three registered fingerprints, so the
  `parser-v3-v1` holdout was sealed to immutable storage at
  `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/`, 12 objects,
  `set_manifest.json` last.
- The teardown result that did **not** meet its expectation is recorded as
  measured, not as met. Subscription-wide Blob roles for the sealing identity are
  `1`, not `0`.

Rationale:

- The gate was defined in advance and was binary: seal if and only if exact,
  normalised and numeric-normalised collision counts are all zero. They were all
  zero, against the corpus with the highest prior probability of overlap, so the
  gate opened. Had any been non-zero the set would not have been sealed and no
  case would have been swapped this round.
- The alternative to disclosing the standing role was to report the specified
  expectation as met. That would have been false, and it would have propagated a
  security claim the project cannot support. The seal's integrity rests on
  digests and round-trip verification, which are unaffected; only the isolation
  claim is affected, and only the isolation claim has been weakened in the
  ledgers.

Consequence:

- `EV-0007` moves from `CONSTRUCTED_NOT_SEALED` to `SEALED`. `CL-06` records
  holdout sealed = yes, and its status stays **unsupported**, because the
  parser-v3 one-shot locked evaluation has not been run and was explicitly out of
  scope this round.
- `L-13` is rewritten from "not sealed" to the sealed reality with its residual
  caveats. `L-17` is added for the RBAC finding.
- The next gate is a separate, later round: a one-shot parser-v3 evaluation
  against the sealed holdout, run once, with predictions and scores produced
  under their own protocol. Nothing in this round licenses any parser-v3 accuracy
  claim.
```

---

## 3. `paper/claim_evidence_matrix.md` — REPLACE the CL-06 table rows

Replace the `Available evidence`, `Missing evidence`, `Key artifacts` and
`Limitations` rows of the `## CL-06 — Parser-v3 correction of parser-v2 failure
modes` table with the following. **Leave `Status` as `**unsupported**`** — the
seal is not a result.

```markdown
| Available evidence | `EV-0006` (development, **COMPLETE**): 9 development gates passed, 1 NOT_APPLICABLE, 60/60 non-regression and 65/65 adversarial typed agreement. `EV-0007` (new locked set, **SEALED** 2026-07-25 at `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/`): 120 cases in 12 strata, 0 unresolved labels, and the last outstanding pre-seal overlap check now executed — 0 exact, 0 normalised and 0 numeric-normalised collisions against the 120 retired parser-v2 locked inputs. Holdout sealed: **yes**, 12 objects, `overwrite=false`, round-trip SHA-256 and ETag verified, `set_manifest.json` written last. |
| Missing evidence | The parser-v3 one-shot locked evaluation. It was explicitly out of scope this round: no parser-v3 prediction exists and nothing was scored. |
| Key artifacts | `artifacts/phase1-parser-v3/track-c/phase1-parser-v3-track-c-20260725T114448Z/`; `artifacts/phase1-evaluator-validation/track-d/20260725T121557Z-track-d-parser-v3-locked-set/`; `artifacts/phase1-evaluator-validation/track-d1/20260725T160340Z-track-d1-parser-v3-seal/`. |
| Limitations | Parser v3 was developed with knowledge of which retired cases parser v2 failed, so overfitting risk is structural. The 65 adversarial fixtures share authorship with parser v3 and are therefore not an independent oracle. All five rule changes are recall-increasing, so precision is unprobed. The holdout is now sealed, which fixes the instrument in time but validates nothing: sealing licenses no accuracy, precision or recall claim. Any parser-v3 result on the retired parser-v2 holdout is development diagnosis and is never validation. Isolation of the retired label and score material during the seal rested on the payload code path and its tests, not on RBAC — see `L-17`. |
```

---

## 4. `paper/evidence_ledger.csv` — REPLACE the `EV-0007` row

One row, CSV-quoted exactly as written:

```csv
EV-0007,Is an independent parser-v3 locked holdout constructed and sealed with zero overlap?,1.2C,parser-v3-holdout,20260725T160340Z-track-d1-parser-v3-seal,2026-07-25,SEALED,not_applicable,not_applicable,a91db88,sha256:f13220aed82c320150a63868e4519ec8d3d4dae7331ae4d421257f191c7d2388,bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27,be350c66d24062d6cc628a7908da59b3777c1f99b8167ee0a0f7766f6020618d,preseal_collision_count,"0 exact, 0 normalised and 0 numeric-normalised collisions between the 120-case parser-v3-v1 set and the 120 retired parser-v2 locked inputs; sealed as 12 objects at phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/ with overwrite=false, exact 12-object membership and round-trip SHA-256 and ETag verification, set_manifest.json written last",instrument_only,CL-04;CL-06,"Sealing fixes the instrument in time and validates nothing: no parser-v3 evaluation was run, no prediction exists and nothing was scored. Reviewer agreement is LLM operational consensus, not human ground truth. Zero overlap is proven only against the corpora actually compared; cross-check 3 against the 18-record historical audit extract is VACUOUS, not passed, because that extract carries no output-bearing field. Isolation between construction and parser-v3 development is procedural, not security-enforced, and both happened in the same worktree. The temporary prefix-conditioned ABAC grants did not narrow the sealing identity's permissions because it already held an unconditioned account-scope blob-write role, so isolation of the retired label and score material rested on the payload code path and its tests; see L-17",phase1-evaluator-validation/parser-v3-v1/20260725T160340Z,artifacts/phase1-evaluator-validation/track-d1/20260725T160340Z-track-d1-parser-v3-seal/05_summary.md
```

Note on two fields, so they are not misread:

* `code_commit` is `a91db88`, the commit the payload was authored against. If the
  main agent commits this round's changes before recording the row, use the new
  commit instead — the correct value is whatever commit the sealed **payload**
  came from, and the payload did not change after `a91db88`.
* `data_hash` and `protocol_hash` are carried forward unchanged from the
  construction row: the set's bytes did not change, only its location did.

---

## 5. `paper/limitations_ledger.md` — REPLACE `L-13`, then APPEND `L-17`

Replace the whole `## L-13` section with:

```markdown
## L-13 — The parser-v3 locked holdout is sealed, but sealing is not validation

The 120-case `parser-v3-v1` set was sealed on 2026-07-25 to
`phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/` as 12 objects, with
`overwrite=false` on every write, exact 12-object membership, round-trip SHA-256
and ETag verification, and `set_manifest.json` written last. The last outstanding
pre-seal overlap check also ran and passed: 0 exact, 0 normalised and 0
numeric-normalised collisions against the 120 retired parser-v2 locked inputs.

What that does and does not buy. It establishes that a specific instrument, with
specific bytes, existed at a specific time, before any parser-v3 result was
known, which is what makes a later one-shot evaluation genuinely prospective. It
establishes nothing about parser v3: no evaluation was run, no prediction exists,
nothing was scored, and no accuracy, precision or recall claim is licensed. The
sealed labels remain a two-reviewer-plus-arbiter LLM operational consensus, not
human ground truth. Zero overlap is proven only against the corpora actually
compared; the third registered cross-check, against an 18-record historical audit
extract, is vacuous rather than passed, because that extract carries no
output-bearing field.
```

Append at the end of the file:

```markdown
## L-17 — The seal's prefix-conditioned ABAC grants enforced nothing

The parser-v3-v1 seal ran under the shared Container Apps job identity
`id-jspace-aca-acrpull-sea`, not a dedicated one, and that identity already held
an **unconditioned** `Storage Blob Data Contributor` assignment at account scope
on `stjspacefiles0709085305`, created 2026-07-09, sixteen days before the round.
The two temporary prefix-conditioned grants created for the run therefore did not
narrow its effective permissions at all: they were defence in depth on paper and
enforced nothing in practice. Post-run teardown measured subscription-wide Blob
roles for that identity as 1, not the 0 the specification expected, and the
surviving assignment was deliberately left in place because it pre-dates the
round and other jobs depend on it.

The consequence is specific. The guarantee that the retired parser-v2 locked
labels, scores and scoring ledger were never touched rests on the job payload's
code path, on the tests that pin that code path, and on the cross-check report's
own attestations `label_material_touched: false` and
`score_material_touched: false`. It does not rest on RBAC. This is a concrete,
evidenced instance of the project's standing caveat that isolation is procedural
rather than security-enforced, and it should be cited as that instance rather
than left abstract. The seal's integrity is unaffected, because that rests on
digests and round-trip verification, not on privilege. Any future round that
wants RBAC-enforced isolation must use a dedicated identity holding no standing
account-scope blob role, and must verify that **before** creating the grants.
```

---

## 6. `paper/artifact_index.csv` — APPEND two rows

Matching the existing convention of indexing only `04_decision.json` and
`06_paper_table.csv` per pack. Digests are of the emitted files and were verified
locally.

```csv
AR-0033,1.2C,20260725T160340Z-track-d1-parser-v3-seal,04_decision.json,decision,repo:artifacts/phase1-evaluator-validation/track-d1/20260725T160340Z-track-d1-parser-v3-seal,a541bd34bd103ff566d30ca79aef383c1fad42c89813f2fb28276c3a1b01c3a8,4522,no,no,primary_result
AR-0034,1.2C,20260725T160340Z-track-d1-parser-v3-seal,06_paper_table.csv,metrics,repo:artifacts/phase1-evaluator-validation/track-d1/20260725T160340Z-track-d1-parser-v3-seal,58d76e653371cc5ce0c4284aa4d98ba70e90dcfa9ffbb95ec0290685e17d85bd,895,no,no,table_source
```

If the main agent regenerates the pack with a different `--generated-at`, these
two digests change. Regenerate the rows from the emitted files rather than
copying these values blindly.

---

## 7. What must NOT be written anywhere

* Not "the holdout is validated", "parser v3 is validated", or any accuracy,
  precision or recall figure. None exists.
* Not "no standing privilege was left behind". Subscription-wide Blob roles for
  the sealing identity are 1.
* Not "the ABAC conditions restricted the job to the retired inputs prefix". They
  were superseded by a broader standing grant.
* Not "cross-check 3 passed". It is vacuous.
* Not the locked inputs, the locked labels, any reviewer row, any arbitration
  row, or any retired input text. Those are sealed and gitignored, and none of
  them appears in the pack or in these drafts.
