# Parser-v3-v1 pre-seal cross-check and seal — Azure job specification

Status: **specification only. Track D has executed no Azure command, created no
role assignment, built no image and uploaded nothing.** The main agent owns all
Azure execution and all git operations.

This document supersedes nothing in `docs/phase1_parser_v3_sealing_run.md`. That
document remains the registered protocol; this one only says *how* to execute it.

Round context: the registered pre-seal cross-check 1 was attempted last round on
`vm-pv2-orchestrator-sea` and is recorded as **NOT PERFORMED**, because the Azure
Run Command extension entered a `Conflict` state and never cleared. That is a
transport fault, not a result, and it must never be reported as a passed check.
The work is therefore moved to a short-lived Container Apps CPU job inside the
VNet-integrated environment, which is also the only network path to the storage
account, whose public network access is disabled.

The VM has since been repaired: the root cause was `provisioningState: Failed`
with zero extensions installed, `az vm update --set tags.*` reconciled it to
`Succeeded`, and a Run Command probe now returns `Enable succeeded` with
`python3` 3.11.2 present. **This does not change the plan.** The Container Apps
job remains the authoritative path, as the round specification directs; the
repaired VM is a fallback for moving small payloads in and out of the VNet only.
The repair also does not retroactively convert last round's `NOT PERFORMED` into
a result — the check is performed when, and only when, the job runs.

Environment facts relied on without re-derivation: `cae-jspace-observation-sea-vnet2`
exposes exactly two workload profiles, `Consumption` and `gpu-t4`; this job takes
`Consumption`, so it does not contend with Track B on the single GPU.

---

## 1. What runs

| Item | Value |
| --- | --- |
| Payload | `scripts/parser_v3_seal_job.py` |
| Fingerprints | imported from `scripts/build_parser_v3_validation_set.py`, never reimplemented |
| Job name | `job-jspace-parser-v3-seal` |
| Environment | `cae-jspace-observation-sea-vnet2` |
| Workload profile | `Consumption` |
| CPU / memory | `2` / `4Gi` |
| GPU | none |
| Trigger type | `Manual` |
| Parallelism | `1` |
| Completions | `1` |
| Replica retry limit | `0` |
| Replica timeout | `1800` seconds |
| Storage account | `stjspacefiles0709085305` |
| Container | `jspace-results` |
| Identity | `id-jspace-aca-acrpull-sea` (user-assigned) |
| Authentication | `ManagedIdentityCredential` only |
| Account key | **not used, not created, not referenced, not logged** |
| SAS | **not used, not created, not referenced, not logged** |
| Storage public network access | stays `Disabled` |
| Secrets on the job | `0` |
| Secret references on the job | `0` |

The job does exactly two things, in this order:

1. **Cross-check 1** — the new set's fingerprints against the retired parser-v2
   locked *inputs*.
2. **The seal** — the twelve registered objects of
   `docs/phase1_parser_v3_sealing_run.md` §1, and only if the cross-check passes.

It imports no parser, produces no prediction and scores nothing.

---

## 2. Decision rule

```text
exact_collision_count == 0
  and normalised_collision_count == 0
  and numeric_normalised_collision_count == 0
  and the retired object matches its registered digest
    => cross_check = PASS  -> seal

any collision > 0
    => cross_check = FAIL  -> DO NOT SEAL, do not swap cases this round,
                              do not run any evaluation, record the
                              conflicting hashes, state BLOCKED_COLLISION

guard / provenance / transport fault
    => cross_check = ABORT -> DO NOT SEAL, state BLOCKED_INFRASTRUCTURE
```

Exit codes: `0` PASS (and sealed in `--mode seal`), `2` FAIL, `3` ABORT, `1`
usage error. `ABORT` is neither a pass nor a fail; it is the absence of a result.

Cross-check 2, the parser-v3 public adversarial development set (65 strings) and
the parser-v2 public development set (60 strings), already returned zero
collisions on all three fingerprints and can be reproduced locally with
`python scripts/crosscheck_parser_v3_locked_set.py`. Cross-check 3 is **VACUOUS**:
the reachable 18-record historical audit extract carries no output-bearing field,
so it cannot collide. Report it as vacuous, never as passed.

---

## 3. Isolation properties the payload enforces

* The retired source prefix is the module constant
  `phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/`.
  No command-line argument can change it.
* Exactly one blob leaf is downloaded, `locked_inputs.jsonl`. Everything else in
  that leaf is listed by name and never read.
* Any blob name containing `locked-labels`, `reviewer_`, `arbitration`,
  `consensus`, `stage1`, `stage2`, `score`, `scoring`, `ledger`, `prediction`,
  `verdict` or `grade` is refused before any download.
* Every retired record must match the frozen label-free key set
  `{schema_version, case_id, source_kind, output_text, parse_type}` and carry
  `schema_version = phase1-parser-v2-locked-input/v1`. A record with any other
  field aborts the run before its values are read.
* Only `output_text`-class fields are read; nothing label-shaped is ever touched.
* The emitted report is scanned against the retired texts before it is written.
  If any retired body text would appear in it, the job refuses to emit.
* The job refuses to run at all unless the imported fingerprint functions
  reproduce five pinned known-answer vectors **and** reproduce all 120 records of
  the committed `inputs_manifest.json` exactly. A divergent normaliser would
  produce a meaningless "0 collisions", which is worse than not running.

The retired holdout is **not** re-run, re-scored or re-opened. Its input text is
fingerprinted for overlap diagnosis only.

---

## 4. Build the payload image

The seal must upload private holdout material that is gitignored. The repo's
`.dockerignore` correctly excludes `evaluator_sets/`, `artifacts/` and every
locked filename, and **must not be weakened**. Stage an out-of-tree context
instead:

```powershell
cd C:\Users\alanjiao\J-space-observation
python scripts\stage_parser_v3_seal_payload.py C:\Users\alanjiao\pv3-seal-context
```

The staging script refuses to write inside the repository or inside any Git
worktree, verifies all twelve objects against the Track D build digests, copies
the hash-pinned `requirements-parser-v2-eval.txt`, writes the Dockerfile and
emits `payload_manifest.json`.

```powershell
az acr build `
  --registry acrjspaceobssea0708231738 `
  --image j-space-observation-pv3seal:$env:SEAL_TS `
  --file Dockerfile `
  C:\Users\alanjiao\pv3-seal-context
```

The resulting image carries the private holdout. Treat it as sensitive:

* it must never be pushed anywhere but this private ACR;
* after the sole execution, delete the manifest
  (`az acr repository delete --name acrjspaceobssea0708231738 --image j-space-observation-pv3seal@sha256:<digest> --yes`);
* the staging context directory must be removed from disk afterwards.

---

## 5. Pick the timestamp first

The ABAC write condition is pinned to the run's timestamp, so choose it before
creating any grant and reuse it everywhere:

```powershell
$SEAL_TS = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
```

Prefixes for that run:

```text
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/          # the 12 sealed objects
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>-runlog/   # report + seal record
```

The runlog prefix is a **sibling**, not a child, of the sealed parent, because
`docs/phase1_parser_v3_sealing_run.md` §6 requires exact twelve-object membership
under the parent. A thirteenth object inside the parent would fail the seal.

If a run aborts, do not retry under the same timestamp. Pick a new one, and
create new grants pinned to the new one.

**Do not run `--mode crosscheck` and then `--mode seal` under the same
timestamp.** Seal mode re-runs the cross-check and re-writes
`crosscheck_report.json`, so it collides with the dry pass's report under that
timestamp's runlog prefix and aborts on its own `overwrite=false` guard. That is
the guard behaving correctly, but it costs a timestamp rotation and a fresh
grant. Either give the dry pass its own throwaway timestamp, or skip it when the
grants are already trusted. This happened on 2026-07-25: the seal attempt under
`20260725T155224Z` aborted for exactly this reason, and the seal completed under
`20260725T160340Z`.

A rotation does not require a rebuild. If no source changed, import the existing
image to the new tag (`az acr import`) so the bytes that seal the set are
provably the bytes that were reviewed.

---

## 6. Minimum temporary RBAC

Two assignments, both at **container** scope, both ABAC-conditioned, both deleted
immediately after the run.

```text
SCOPE = /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-jspace-observation-sea/providers/Microsoft.Storage/storageAccounts/stjspacefiles0709085305/blobServices/default/containers/jspace-results
ASSIGNEE = <objectId of id-jspace-aca-acrpull-sea>   # az identity show ... --query principalId -o tsv
```

### 6.1 The lesson that must be encoded

A condition written only against `blobs:path` **denies `List Blobs`**. Listing
does not evaluate `blobs:path`; it evaluates the request attribute
`blobs:prefix`. That is exactly how a prefix-conditioned read grant can look
correct and still fail with `AuthorizationPermissionMismatch` on the very first
`list_blobs` call. Every read clause below therefore carries **both** an
`@Resource[...blobs:path]` term and an `@Request[...blobs:prefix]` term.

Corollary the payload already respects: never list without `name_starts_with`.
If the request carries no prefix attribute, the `@Request` term is false and the
listing is denied by design.

### 6.2 Read grant — retired parser-v2 locked inputs, read + list

Role: `Storage Blob Data Reader`
(`2a2b9908-6ea1-4ae2-8e65-a410df84e7d1`).

Condition version `2.0`. Exact condition string, on one line:

```text
((!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith 'phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/') OR (@Request[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:prefix] StringStartsWith 'phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/'))
```

```powershell
$readCondition = "((!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith 'phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/') OR (@Request[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:prefix] StringStartsWith 'phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/'))"

az role assignment create `
  --assignee-object-id $ASSIGNEE `
  --assignee-principal-type ServicePrincipal `
  --role "Storage Blob Data Reader" `
  --scope $SCOPE `
  --description "temporary parser-v3 pre-seal cross-check, retired parser-v2 locked INPUTS only" `
  --condition $readCondition `
  --condition-version "2.0"
```

This grant cannot reach `locked-labels/`, `manifests/`, `reports/` or
`development/` under the retired release, and cannot reach any other prefix in
the container.

### 6.3 Write grant — the new parser-v3 run prefix only

Role: `Storage Blob Data Contributor`
(`ba92f5b4-2d11-453d-a403-e96b0029c9fe`).

Three clauses: read+list scoped to the run prefix, write scoped to the run
prefix, and a delete clause pinned to a path that never receives an object.
Exact condition string, on one line, with `<SEAL_TS>` substituted:

```text
((!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith 'phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>') OR (@Request[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:prefix] StringStartsWith 'phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>')) AND ((!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith 'phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>')) AND ((!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith 'phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/__never_written__/'))
```

```powershell
$prefix = "phase1-evaluator-validation/parser-v3-v1/$SEAL_TS"
$writeCondition = "((!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith '$prefix') OR (@Request[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:prefix] StringStartsWith '$prefix')) AND ((!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith '$prefix')) AND ((!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith '$prefix/__never_written__/'))"

az role assignment create `
  --assignee-object-id $ASSIGNEE `
  --assignee-principal-type ServicePrincipal `
  --role "Storage Blob Data Contributor" `
  --scope $SCOPE `
  --description "temporary parser-v3-v1 seal, run prefix only" `
  --condition $writeCondition `
  --condition-version "2.0"
```

Notes and honest limits:

* `StringStartsWith '<...>/<SEAL_TS>'` without a trailing slash is deliberate: it
  covers both `<SEAL_TS>/` (the seal) and `<SEAL_TS>-runlog/` (the evidence) and
  nothing from any other run.
* The delete clause is defence in depth, not a proof: it does not forbid delete
  in the abstract, it pins delete to a path that this job never writes. Combined
  with `overwrite=false` on every upload, no existing object can be replaced.
* `Storage Blob Data Contributor` is used rather than a write-only role because
  round-trip verification requires reading back what was just written.
* Role assignment conditions can take up to a few minutes to propagate. If the
  first execution fails with `AuthorizationPermissionMismatch`, wait and re-run
  under a **new** timestamp with a **new** write grant.

---

## 7. Create and run the job

```powershell
az containerapp job create `
  --name job-jspace-parser-v3-seal `
  --resource-group rg-jspace-observation-sea `
  --environment cae-jspace-observation-sea-vnet2 `
  --workload-profile-name Consumption `
  --trigger-type Manual `
  --replica-timeout 1800 `
  --replica-retry-limit 0 `
  --parallelism 1 `
  --replica-completion-count 1 `
  --image acrjspaceobssea0708231738.azurecr.io/j-space-observation-pv3seal:$SEAL_TS `
  --cpu 2 --memory 4Gi `
  --mi-user-assigned $IDENTITY_ID `
  --registry-server acrjspaceobssea0708231738.azurecr.io `
  --registry-identity $IDENTITY_ID `
  --env-vars AZURE_CLIENT_ID=$IDENTITY_CLIENT_ID `
  --command "/usr/local/bin/python3.11" `
  --args "-I","/payload/parser_v3_seal_job.py","--mode","seal","--payload-dir","/payload","--seal-timestamp","$SEAL_TS","--out","/runtime/work/summary.json"
```

Then start exactly one execution:

```powershell
az containerapp job start --name job-jspace-parser-v3-seal --resource-group rg-jspace-observation-sea
```

Before the seal run, an optional dry pass is available and is recommended only if
there is real doubt about the grants. It must use its **own** throwaway
timestamp — see §5:

```text
--mode crosscheck --payload-dir /payload --seal-timestamp <THROWAWAY_TS>
```

`--mode crosscheck` reads the retired inputs, writes only the report to the
runlog prefix and never touches the seal parent. `--mode preflight` needs no
Azure at all and can be run locally:

```powershell
python scripts\parser_v3_seal_job.py --mode preflight --repo-root .
```

Preflight prints `cross_check=NOT PERFORMED` by construction. It verifies the
fingerprint registration, the 120-record manifest reproduction and all twelve
object digests. It is not a substitute for the cross-check and must never be
recorded as one.

---

## 8. What lands where

Sealed parent, exactly twelve objects, `set_manifest.json` last:

```text
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/locked-inputs/locked_inputs.jsonl
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/locked-labels/locked_labels.jsonl
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/locked-labels/reviewer_a_locked_labels.jsonl
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/locked-labels/reviewer_b_locked_labels.jsonl
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/locked-labels/arbitration_locked_labels.jsonl
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/reports/strata_definitions.md
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/reports/phase1_parser_v3_locked_set.md
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/reports/phase1_parser_v3_validation_set.md
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/reports/phase1_parser_v3_sealing_run.md
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/manifests/inputs_manifest.json
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/manifests/labels_manifest.json
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>/manifests/set_manifest.json
```

Sibling runlog, two objects:

```text
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>-runlog/crosscheck_report.json
phase1-evaluator-validation/parser-v3-v1/<SEAL_TS>-runlog/seal_record.json
```

Both runlog objects are text-free: counts, one-way digests, blob names, ETags
and verdicts only.

---

## 9. Teardown, and how to verify it

Immediately after the execution, whatever the outcome:

```powershell
# 1. remove both temporary grants
az role assignment list --assignee $ASSIGNEE --scope $SCOPE --query "[].id" -o tsv |
  ForEach-Object { az role assignment delete --ids $_ }

# 2. container-scope assignments for the sealing identity must be 0
az role assignment list --assignee $ASSIGNEE --scope $SCOPE --query "length(@)" -o tsv
# expected: 0

# 3. subscription-wide Blob roles for that identity: RECORD THE ACTUAL VALUE
az role assignment list --assignee $ASSIGNEE --all `
  --query "[?contains(roleDefinitionName, 'Blob')].{role:roleDefinitionName,scope:scope,condition:condition,createdOn:createdOn}" -o json
# This is a measurement, not a pass condition. Write down what it returns.
#   0                      -> no standing blob privilege for this identity
#   more than 0            -> DISCLOSE IT. For each surviving assignment record the
#                             role, the scope, whether it carries a condition, and
#                             when it was created. If any of them is unconditioned
#                             and at account or subscription scope, then the
#                             temporary prefix-conditioned grants above narrowed
#                             NOTHING, and the isolation of the retired label,
#                             score and ledger material rested on the payload code
#                             path and its tests rather than on RBAC. That belongs
#                             in 08_deviations.json and in the limitations ledger.
# Measured on 2026-07-25 for id-jspace-aca-acrpull-sea: 1, an unconditioned
# Storage Blob Data Contributor at account scope created 2026-07-09, sixteen days
# before this round. It was NOT removed: it pre-dates the round and other
# Container Apps jobs depend on it. Recorded as deviation D13.

# 4. reset the job to the immutable base image so it cannot re-run
az containerapp job update --name job-jspace-parser-v3-seal `
  --resource-group rg-jspace-observation-sea `
  --image acrjspaceobssea0708231738.azurecr.io/j-space-observation@sha256:43af06291f6196d5426fe5e014196c86d3d00aae978470d369a9c1c2bd3dfeac `
  --command "/bin/true" --args ""

# 5. secrets and secret references on the job must both be 0
az containerapp job show --name job-jspace-parser-v3-seal `
  --resource-group rg-jspace-observation-sea `
  --query "length(properties.configuration.secrets || [])" -o tsv
# expected: 0

# 6. storage public network access must still be Disabled
az storage account show --name stjspacefiles0709085305 `
  --resource-group rg-jspace-observation-sea `
  --query publicNetworkAccess -o tsv
# expected: Disabled

# 7. delete the single-use payload image and the staging context
```

Both checks in steps 2 and 3 must be recorded in the run log with their actual
output. Step 2 is a pass condition: it must return `0`. Step 3 is **not** a pass
condition, it is a disclosure: record what it actually returns. A non-zero result
does not invalidate the seal, whose integrity rests on digests, but it does
invalidate any claim that RBAC enforced the isolation, and that claim must then
not be made. "No standing privilege was left behind" may only be written if step
3 actually returned `0`.

Precondition worth checking **before** granting, which this round learned the
hard way: if the sealing identity already holds an unconditioned blob-write role
at account or subscription scope, the prefix-conditioned grants below are
decorative. A round that wants RBAC-enforced isolation needs a dedicated identity
with no standing blob role, verified before the grants are created.

---

## 10. After the run

1. Download `crosscheck_report.json` and `seal_record.json` from the runlog
   prefix. They contain no case text, no label values and no retired text.
2. Re-emit the Track D pack **from those two durable objects**, not from the
   in-container summary, which is ephemeral:

   ```powershell
   python scripts\emit_track_d1_artifacts.py `
     --run-id <SEAL_TS>-track-d1-parser-v3-seal `
     --crosscheck-report <path>\crosscheck_report.json `
     --seal-record <path>\seal_record.json `
     --execution-record docs\phase1_parser_v3_seal_execution_record.json
   ```

   The generator re-verifies three bindings and refuses to emit a pack if any
   fails: the seal record's pinned digest of the cross-check report against the
   report's measured bytes, the verdict and all three collision counts across the
   two objects, and every sealed object's digest, byte count and order against
   the registered staging pins. Facts that the Blob objects cannot carry —
   execution ids, image digest, teardown measurements — come from
   `--execution-record` and are labelled as operator attestation, not as Track D
   measurement.

   The pack's final state is one of `SEALED`, `BLOCKED_COLLISION`,
   `BLOCKED_INFRASTRUCTURE`. There is no other allowed value, and an absent or
   aborted cross-check is never rendered as a pass.
3. Record in `docs/run_log.md` and `docs/decision_log.md`: the resolved
   timestamp, the twelve object names, digests, byte counts and ETags, the job
   name and the single execution id, the outcome of all three registered
   cross-checks (with check 3 stated as vacuous), the grant-removal evidence from
   §9, and confirmation that no key and no SAS were used and that public network
   access stayed disabled.

## 11. Payload integrity

Before building, confirm the staged payload is the intended bytes. `.gitattributes`
pins these files to LF, so the working-tree digests below are the canonical ones.

| File | LF SHA-256 | Bytes |
| --- | --- | --- |
| `scripts/parser_v3_seal_job.py` | `7b5bb59b820d987c953e446d3231b412903c6298b0fbe31d6da2bc3a061cd966` | 47179 |
| `scripts/stage_parser_v3_seal_payload.py` | `4ef50f418ef853b647f991077c5cfe1eadc59dd1bd214c32c57db9bf8d547bd9` | 7980 |
| `scripts/build_parser_v3_validation_set.py` (fingerprint source, copied verbatim, CRLF on disk) | `92efed3cf1c89e2424340303f8497b883a52187baa97681026be1e02b48f0add` | 65042 |

The fingerprint source is deliberately *not* EOL-normalised: it is an already
committed file whose bytes other records pin, and Python source line endings do
not change the fingerprint values. The payload does not trust this digest anyway
— it re-derives trust from five pinned known-answer vectors and from a full
120-record reproduction of the committed inputs manifest, and refuses to run if
either check fails.

`payload_manifest.json`, written by the staging script into the build context,
must reproduce the first two rows exactly. If it does not, stop: the container
would run something other than the reviewed payload.

## 12. What this does not establish

Sealing does not validate parser v3. It licenses no accuracy, precision, recall
or error claim. It establishes only that a specific 120-case instrument existed,
with specific bytes, at a specific time, before any parser-v3 result was known.
The sealed labels are a two-reviewer-plus-arbiter LLM operational consensus, not
human ground truth. The isolation between holdout construction and parser-v3
development is procedural and hash-audited, not security-enforced.
