# Phase 1.2C — parser-v3-v1 sealing run specification

Status: **specification only. Track D has executed no Azure command and uploaded
nothing.** The MAIN AGENT owns all Azure execution and sealing.

Track D produced the set, the labels, the manifests and this specification. Everything
below is written so the main agent can execute it without further design decisions.

---

## 1. Objects to seal

Twelve objects. Sizes and digests are the ones produced by the final Track D build; the
main agent must re-verify them locally before uploading and abort on any mismatch.

| # | Local path | Blob leaf | Content class |
| --- | --- | --- | --- |
| 1 | `evaluator_sets/parser_v3_v1/locked_inputs.jsonl` | `locked-inputs/` | private holdout inputs |
| 2 | `evaluator_sets/parser_v3_v1/locked_labels.jsonl` | `locked-labels/` | **private holdout labels — never to GitHub** |
| 3 | `evaluator_sets/parser_v3_v1/reviewer_a_locked_labels.jsonl` | `locked-labels/` | private reviewer A rows |
| 4 | `evaluator_sets/parser_v3_v1/reviewer_b_locked_labels.jsonl` | `locked-labels/` | private reviewer B rows |
| 5 | `evaluator_sets/parser_v3_v1/arbitration_locked_labels.jsonl` | `locked-labels/` | private arbiter rows |
| 6 | `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json` | `manifests/` | integrity |
| 7 | `evaluator_sets/parser_v3_v1/manifests/labels_manifest.json` | `manifests/` | integrity |
| 8 | `evaluator_sets/parser_v3_v1/strata_definitions.md` | `reports/` | public protocol copy |
| 9 | `docs/phase1_parser_v3_locked_set.md` | `reports/` | public protocol copy |
| 10 | `reports/phase1_parser_v3_validation_set.md` | `reports/` | public report copy |
| 11 | `docs/phase1_parser_v3_sealing_run.md` | `reports/` | this specification |
| 12 | `evaluator_sets/parser_v3_v1/manifests/set_manifest.json` | `manifests/` | **written LAST** |

Object 12 is the closure record. It must be the final write of the entire operation.

Objects 1–5 are gitignored and exist only on the curator's disk; sealing them is what
makes the holdout durable. Objects 6, 7 and 12 are also committed to GitHub — that is
intentional, because they are the reviewable surface of the set and contain no case text
and no label values. Objects 8–11 are public documents.

---

## 2. Blob layout

Private Blob parent prefix:

```text
phase1-evaluator-validation/parser-v3-v1/<timestamp>
```

`<timestamp>` is a single UTC stamp of the form `YYYYMMDDTHHMMSSZ`, generated once at
the start of the run and reused for every object. Do not regenerate it per leaf.

Four separate leaves under the parent, matching the parser-v2-v1 precedent:

```text
phase1-evaluator-validation/parser-v3-v1/<timestamp>/locked-inputs/
phase1-evaluator-validation/parser-v3-v1/<timestamp>/locked-labels/
phase1-evaluator-validation/parser-v3-v1/<timestamp>/manifests/
phase1-evaluator-validation/parser-v3-v1/<timestamp>/reports/
```

The parent prefix is append-only. If any object already exists under it, the run has
already happened: abort, do not retry under the same timestamp, and do not delete.

---

## 3. Write ordering

1. Upload `locked-inputs/locked_inputs.jsonl`.
2. Upload the four `locked-labels/` objects: `locked_labels.jsonl`,
   `reviewer_a_locked_labels.jsonl`, `reviewer_b_locked_labels.jsonl`,
   `arbitration_locked_labels.jsonl`.
3. Upload the four `reports/` objects.
4. Upload `manifests/inputs_manifest.json` and `manifests/labels_manifest.json`.
5. Re-list the parent prefix and verify **exact membership**: the set of blob names
   found must equal the set of eleven expected names exactly — no extras, no omissions.
6. Re-download all eleven objects and verify size, SHA-256 and ETag (section 5).
7. Only if steps 5 and 6 both pass, upload `manifests/set_manifest.json` **last**.
8. Re-list once more and verify exact 12-object membership.
9. Re-download the set manifest and verify size, SHA-256 and ETag.

The set manifest is the last write so that its presence is proof that every other
object landed and verified. A prefix carrying a set manifest is sealed; a prefix
without one is an aborted run and must never be treated as a seal.

---

## 4. Upload semantics

* Every upload uses `overwrite=false`. A conflict is a hard failure, never a retry.
* No object is deleted, renamed or rewritten by this operation.
* Bytes are uploaded exactly as they exist on disk. No re-serialisation, no
  re-canonicalisation, no newline translation. All Track D artifacts are written with
  LF newlines and UTF-8 encoding.
* If any step fails, stop. Leave the partial prefix in place as evidence, record the
  failure, and start a new run under a **new** timestamp after the cause is fixed.

---

## 5. Per-object verification

For each of the twelve objects, in this order:

1. **Before upload** — read the local file, compute SHA-256 and byte count, and compare
   against the corresponding entry in `manifests/set_manifest.json` (`files[].sha256`
   and `files[].bytes`) where one exists; the reviewer/arbiter row files and the public
   documents are not listed there, so compare those against the digests recorded in
   `reports/phase1_parser_v3_validation_set.md` §2. Abort on any mismatch.
2. **After upload** — read the blob properties and assert that the reported size equals
   the local byte count, and capture the ETag. An unavailable or empty ETag is a
   failure.
3. **Re-download** — download the object's full content and assert:
   * downloaded byte count equals the local byte count;
   * SHA-256 of the downloaded bytes equals the local SHA-256;
   * the ETag observed at download equals the ETag captured at upload.

All three checks must pass for every object. A single failure fails the whole sealing
run.
---

## 6. Membership verification

Exact membership, not prefix-contains:

```text
expected = {
  "<parent>/locked-inputs/locked_inputs.jsonl",
  "<parent>/locked-labels/locked_labels.jsonl",
  "<parent>/locked-labels/reviewer_a_locked_labels.jsonl",
  "<parent>/locked-labels/reviewer_b_locked_labels.jsonl",
  "<parent>/locked-labels/arbitration_locked_labels.jsonl",
  "<parent>/manifests/inputs_manifest.json",
  "<parent>/manifests/labels_manifest.json",
  "<parent>/manifests/set_manifest.json",
  "<parent>/reports/strata_definitions.md",
  "<parent>/reports/phase1_parser_v3_locked_set.md",
  "<parent>/reports/phase1_parser_v3_validation_set.md",
  "<parent>/reports/phase1_parser_v3_sealing_run.md",
}
observed = set(list_blobs(name_starts_with=parent + "/"))
assert observed == expected
```

`observed - expected` non-empty means something else wrote into the prefix: abort and
investigate. `expected - observed` non-empty means an upload silently failed: abort.

---

## 7. Azure execution environment

| Item | Value |
| --- | --- |
| Container Apps environment | `cae-jspace-observation-sea-vnet2` |
| Workload profile | `Consumption` |
| CPU | 2 |
| Memory | `4Gi` |
| GPU | none |
| Storage account | `stjspacefiles0709085305` |
| Container | `jspace-results` |
| Authentication | `ManagedIdentityCredential` only |
| Identity | `id-jspace-aca-acrpull-sea` |
| Role | `Storage Blob Data Contributor` |
| Network path | private endpoint `pe-stjspacefiles-blob-sea` via `privatelink.blob.core.windows.net` |
| Storage public network access | disabled |
| Account key | **not used** |
| SAS token | **not used** |

No account key and no SAS may be created, exported, referenced or logged. If managed
identity plus private endpoint cannot reach the account, the correct action is to fix
the network path, not to fall back to a key.

After the sole execution the job must be reset to the immutable base image with
`/bin/true`, exactly as the parser-v2-v1 seal was, so it cannot be re-run accidentally.
Secret count and secret-reference count on the job must both be zero at the end.

---

## 8. Label secrecy

Secrecy is declared once, in the `SECRECY` table at the top of
`scripts/build_parser_v3_validation_set.py`, and is asserted in both directions by
`tests/test_parser_v3_validation_set.py`.

**Private — gitignored, sealed but never committed:**

| Path (under `evaluator_sets/parser_v3_v1/`) | `.gitignore` rule |
| --- | --- |
| `locked_labels.jsonl` | line 41 — `evaluator_sets/**/locked_labels.jsonl` |
| `locked_inputs.jsonl` | line 40 — `evaluator_sets/**/locked_inputs.jsonl` |
| `reviewer_a_locked_labels.jsonl` | line 45 — `evaluator_sets/**/reviewer_*_locked*.jsonl` |
| `reviewer_b_locked_labels.jsonl` | line 45 |
| `arbitration_locked_labels.jsonl` | line 46 — `evaluator_sets/**/arbitration_locked*.jsonl` |
| everything under `private/` | line 39 — `evaluator_sets/**/private/` |

**Public — committed to GitHub and also sealed:**
`manifests/inputs_manifest.json`, `manifests/labels_manifest.json`,
`manifests/set_manifest.json`. None is named `locked_manifest.json`, because that exact
filename is gitignored by line 44 and the manifests are meant to be reviewable.

Everything under `private/` is working material (case sources, salts, reviewer packet,
authoring modules) and is **not** part of the seal.

The committed manifests contain digests and salted fingerprints only. The label
fingerprints are HMAC-SHA256 keyed with a private salt that is itself gitignored, so a
reader holding the manifests and even the inputs still cannot recover or brute-force a
label.

Before executing the seal, the main agent must re-confirm:

```powershell
# every one of these must print the ignoring rule and exit 0
git check-ignore -v evaluator_sets/parser_v3_v1/locked_labels.jsonl
git check-ignore -v evaluator_sets/parser_v3_v1/locked_inputs.jsonl
git check-ignore -v evaluator_sets/parser_v3_v1/reviewer_a_locked_labels.jsonl
git check-ignore -v evaluator_sets/parser_v3_v1/reviewer_b_locked_labels.jsonl
git check-ignore -v evaluator_sets/parser_v3_v1/arbitration_locked_labels.jsonl

# these must exit 1 (not ignored) so the set stays reviewable
git check-ignore -v evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json
git check-ignore -v evaluator_sets/parser_v3_v1/manifests/labels_manifest.json
git check-ignore -v evaluator_sets/parser_v3_v1/manifests/set_manifest.json

# this must return nothing
git status --porcelain --untracked-files=all |
  Select-String 'locked_labels|locked_inputs|_locked_labels|parser_v3_v1/private/'
```

Note: query directories **without** a trailing slash. `git check-ignore -v <dir>/` on a
directory that contains no tracked file reports a spurious match against the blank final
line of `.gitignore` — `scripts/nosuchdir/` reproduces it — so a trailing-slash probe is
not evidence of anything.

---

## 9. Cross-checks the main agent must run before sealing

Track D is under procedural isolation and could not read two corpora. The main agent is
not under that isolation and must close the gap **before** the seal, because a seal is
append-only and cannot be corrected afterwards.

1. **Retired parser-v2 locked holdout.** Fetch the sealed
   `phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/` object and
   compare its per-record fingerprints against
   `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json`. Required:
   `exact_sha256`, `normalized_sha256` and `numeric_normalized_sha256` intersections all
   empty.
2. **parser-v3 public adversarial development set.** Compare
   `evaluator_sets/parser_v3_v1/adversarial_development_cases.jsonl` against the same
   manifest fingerprints. Required: the same three intersections empty.
3. **Full historical model outputs.** If `phase1_generations.jsonl` and
   `phase1_eval_records.jsonl` are retrievable, fingerprint every output-bearing field
   and compare. Track D could only reach the 18-record audit extract.

If any intersection is non-empty, **do not seal**. Return the offending case ids to
Track D for replacement and rebuild.

The normalization used by the manifest is documented in
`docs/phase1_parser_v3_locked_set.md` section 6.1 and implemented in
`scripts/build_parser_v3_validation_set.py`, so the main agent can reproduce it exactly.

---

## 10. What this sealing run does **not** do

* It does **not** run a parser-v3 evaluation. No parser-v3 predictions are produced,
  uploaded or referenced.
* It does **not** unseal, read, modify or supersede the retired parser-v2-v1 release.
* It does **not** publish labels to GitHub.
* It does **not** license any claim about parser-v3 accuracy. The seal establishes only
  that a specific 120-case instrument existed, with specific bytes, at a specific time,
  before any parser-v3 result was known.

---

## 11. Post-seal record

After a successful seal the main agent should record, in whichever shared log it owns:

* the parent prefix with its resolved timestamp;
* the nine object names;
* the nine SHA-256 digests and byte counts;
* the nine ETags;
* the ACA job name and the single execution id;
* the outcome of the three section-9 cross-checks;
* confirmation that no key and no SAS were used and that public network access remained
  disabled.

That record, plus this specification, is what makes the parser-v3 evaluation a genuine
pre-registered holdout evaluation rather than a retrospective one.
