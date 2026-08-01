# Phase 1.2H-R1 — Cloud private-source access protocol

**Status:** frozen at the access-protocol freeze commit.
**Round type:** access restoration and private-review-boundary qualification.
**This protocol does not authorize evaluation.**

---

## 1. What this round is for

Phase 1.2H terminated `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`: the round needed to
work with the authoritative sealed `parser-v3-v1` source and had no
authenticated path to it. This round builds that path, and only that path.

The objective is narrow on purpose:

> Obtain authenticated, least-privilege, read-only, in-VNet access to the sealed
> `parser-v3-v1` source, and verify **byte-only** that its contents are
> identical to what the committed public seal record says was sealed.

Byte-only means SHA-256 over raw bytes and nothing else. No decoding, no
parsing, no reading, no persistence, no export.

### 1.1 What this round explicitly does not do

* It does not review any case, label, span, offset or answer value.
* It does not run parser v3, parser v2 or the legacy parser.
* It does not generate a prediction.
* It does not migrate, repair, replace, construct or seal any set.
* It does not create an authorization lock, evaluation state chain or
  evaluation image.
* It does not establish that parser v3 is validated, improved, non-regressive
  or fit for scientific scoring.
* It does not support any J-space, hidden-reasoning, invisible-CoT or
  internal-workspace conclusion.

A successful byte-only verification establishes exactly one thing: that the
bytes are the bytes. That is a provenance fact about storage, not a scientific
finding about a parser.

---

## 2. Execution constraint

The operator's local machine cannot sustain heavy compute. This is a hard
constraint on the protocol, not a preference:

* container builds run in **ACR Tasks**;
* the access gate runs in an **Azure Container Apps job**;
* public validation runs in **GitHub-hosted Actions**;
* local work is limited to editing, `git`, `az`/`gh` control-plane calls, and
  checks that complete in about two minutes.

Every artifact in this round is designed so that the expensive step happens
somewhere else and returns a small, checkable result.

---

## 3. The freeze

Everything the gate trusts is fixed **before** the gate runs, in
`docs/phase1_2h_r1_access_decision_record.json`:

| Block | Fixes |
|---|---|
| `source_binding` | subscription, resource group, storage account, container, exact prefix, expected object count and total bytes |
| `expected_evidence_binding` | the committed seal record, its SHA-256, and the derived `members_digest` |
| `identity_rule` | the required credential type, the forbidden credential types, the required data role and its role-definition ID, and the maximum assignment scope |
| `endpoint_rule` | required `publicNetworkAccess`, the blob FQDN, the private-link zone, and the single permitted private IP |
| `byte_only_rule` | what may be done with a byte, and what may not |
| `receipt_rule` | what a receipt may contain |
| `counter_semantics` | how each ledger counter is derived from execution evidence |

**Post-freeze edits to the decision record terminate the run.** The probe binds
to it by digest and refuses if it has moved.

The source binding cannot be overridden from the command line, the environment,
or the job definition. Those override flags exist in the probe's argument parser
solely so that an attempt is *refused loudly* rather than silently accepted by a
permissive parser.

---

## 4. Why a new identity

The pre-existing `id-jspace-aca-acrpull-sea` holds **Storage Blob Data
Contributor at the storage account scope** — write- and delete-capable across
every container in the account. This is independently corroborated by
`docs/phase1_parser_v3_seal_execution_record.json`, which records the assignment
as pre-existing, `expected_by_spec: 0`, `matches_expectation: false`.
`id-jspace-parser-v2-control-sea` holds resource-group **Contributor**.

Using either would make "read-only" an operator promise. This round creates
`id-jspace-p12h-r1-read-sea` and grants it exactly two roles:

* `AcrPull` at the registry;
* `Storage Blob Data Reader` (`2a2b9908-6ea1-4ae2-8e65-a410df84e7d1`) scoped to
  the single blob **container**, not the account.

`infra/azure/scripts/15_p12h_r1_create_identity.sh` refuses to finish if the
principal ends up holding anything else. Read-only becomes a property of the
authorization model rather than a claim in a report.

---

## 5. Why the read is possible at all

The storage account is already configured the way this round needs:

| Setting | Value |
|---|---|
| `publicNetworkAccess` | `Disabled` |
| `allowSharedKeyAccess` | `false` |
| `networkAcls.defaultAction` | `Deny` |
| `networkAcls.bypass` | `None` |
| `allowBlobPublicAccess` | `false` |
| minimum TLS | 1.2 |

`allowSharedKeyAccess: false` means shared-key authentication, and any SAS
signed with an account key, are impossible by construction rather than merely
forbidden by policy. It does **not** by itself exclude a *user-delegation* SAS,
which is signed with an Entra-issued key and is unaffected by that flag. What
excludes that path is the identity's role set: minting a user-delegation key
requires the `Storage Blob Delegator` role on the account, and the designated
identity holds exactly two role assignments, neither of which is that one. The
only way in is therefore Entra ID plus the private endpoint, and the reason is
the role scoping, not the shared-key flag alone.

The private path is verified end to end: private endpoint
`pe-stjspacefiles-blob-sea` has NIC IP **10.80.2.4**; the linked private DNS
zone `privatelink.blob.core.windows.net` resolves the account to **10.80.2.4**;
the VNet link is `Completed`. The job runs in
`cae-jspace-observation-sea-vnet2`, VNet-injected into the same VNet.

The probe refuses if the resolved address is public, is outside `10.80.0.0/16`,
or is any private address other than the registered one. Being inside the VNet
is not sufficient: a different private endpoint is a different endpoint.

---

## 6. The gate

### Stage A — identity and endpoint

Refuse unless: no source-binding override was attempted; no ambient or secret
credential environment variable is set; no forbidden credential symbol is
reachable; verbose SDK body logging is off; the blob FQDN resolves to the single
registered private IP; the credential is `ManagedIdentityCredential` with an
explicitly supplied user-assigned client ID.

Two Stage A properties are deliberately **not** claimed as in-job observations.

`publicNetworkAccess` is a control-plane property of the storage account. The
probe holds no reader role on the account resource, so it cannot observe it, and
granting one to make the receipt look more complete would *increase* the
identity's privilege in exchange for a cosmetic field. The receipt therefore
records `"Unknown"` and refuses any other value, and names the operator
control-plane read taken before the run as the source of the `Disabled` finding
quoted in section 5. The private-IP resolution check is what the job itself
proves, and it is the stronger of the two: an account reachable from the public
internet would still not be reached over a public address by this job.

Likewise, the read-only nature of the identity's role assignments is not
verifiable from inside the job, because reading role assignments requires a role
the identity deliberately does not hold. The receipt records
`effective_read_only_verdict: NOT_CONFIRMED_IN_JOB` rather than a verdict it
cannot support. The role set is established by operator control-plane evidence
recorded in the decision record, and the absence of write capability is
demonstrated positively by `data_plane_writes: 0` and by the static proof that
no write, upload, delete or delegation call site exists in the probe source.

### Stage B — membership

List **only** the exact registered prefix. Compare the observed member set
against the 12 members derived from the committed seal record, entirely in
memory. Refuse on any count difference, any set difference, or any observed name
outside the prefix. Emit only aggregates — never a member name.

### Stage C — byte-only integrity

For each expected member, stream the object in 256 KiB chunks directly into a
SHA-256 accumulator. Compare size and digest against the seal record. Refuse on
any mismatch.

The chunk size is not merely the loop's step: it is also passed to the client as
`max_single_get_size` and `max_chunk_get_size`. Without that, the SDK is free to
buffer a whole object in memory on a single GET regardless of how the caller
iterates, and the bounded-memory claim would be an assertion about the loop
rather than a property of the download.

`stream_object_digest` is the only function in the round that sees authoritative
bytes. It holds one chunk at a time, folds it into the digest, and lets it go.
There is no accumulation, no decode, no branch that inspects content, and no
path by which a chunk reaches a return value, a log line or an exception.

Sealed-object digests are compared **raw**. Repository artifacts are digested
**LF-normalized**. These are deliberately different: a normalizing read of the
authoritative source would mask a real difference in it.

### Stage D — receipt

Emit exactly one receipt and self-validate it against
`docs/phase1_2h_r1_access_receipt.schema.json`. The schema is closed
(`additionalProperties: false` everywhere), `reason_code` and
`invariants_failed` are closed vocabularies, and
`decode_attempts`, `persist_attempts`, `azure_data_plane_writes`,
`semantic_input_reads`, `semantic_label_reads`, `parser_invocations` and
`predictions_generated` are structurally pinned `maximum: 0`.

A probe that decoded, persisted or wrote could not emit a schema-valid receipt
**reporting that it had done so**. That is a narrower claim than it may look,
and independent Audit C (C-05) was right to insist on the distinction: the
counters are literals the probe writes, so a dishonest or defective probe that
decoded a sealed object would emit `0` and its receipt would validate. The pins
close one specific hole — an honest instrument cannot normalise a violation it
did observe into a valid artifact — and nothing more.

The enforcement that makes the literal zeros credible is `assert_no_write_calls_in_source`,
an AST walk over the probe's own source that fails the build if a decode,
persist, data-plane write or parser call appears anywhere in it. That check is
inspectional rather than structural, and its scope is stated exactly in §6.

---

## 7. Honest scope of the isolation claims

Two claims about parser isolation are supportable and are made:

1. the access image contains no parser module, and the build fails if the
   `jspace_observation` package (whose `__init__` eagerly imports the legacy
   parser) is importable at all;
2. the probe's own source references no parser symbol and imports no
   parser-bearing package, verified by AST inspection in the public suite.

The following claim is **not** made and must not appear anywhere: that no parser
module could exist in any process, or that package import is absolutely
parser-free in the repository generally. It is not, and this round does not
refactor `__init__.py` merely to make a stronger sentence true.

Similarly, the read-only guarantee is stated precisely. An earlier draft of the
probe checked `hasattr(client, "upload_blob")` on the SDK object; that check was
wrong and would have refused every run, because a `BlobClient` exposes
`upload_blob` as a class method regardless of the caller's RBAC. Capability on
the wire is decided by the role assignment. What the probe can honestly assert
is a narrower structural claim, and independent Audit E (E-04) required that
claim be stated with its true scope. The AST check parses the two first-party
Python files listed in `IN_JOB_FIRST_PARTY_SOURCES` — the probe and its
validator — and refuses if a mutating Blob operation is called anywhere in
either. That is **not** the same as "the reachable source": the Azure SDK, the
standard library and the base image are all reachable from the probe and none of
them is parsed. The supportable sentence is:

> No mutating Blob operation is called anywhere in the first-party source that
> runs inside the job.

Whether the SDK or the platform performed a write is established separately, and
only negatively, by the storage account carrying no data-plane write role
assignment for the job identity.

### 7.1 Two false claims this protocol refuses to make

* **Consumption egress.** `snet-aca-jspace-sea-v2` has `routeTable: null` and
  its NSG carries no custom outbound rule, so the default
  `AllowInternetOutBound` rule applies. Egress is **unrestricted**. The
  environment `cae-jspace-observation-sea-vnet2` *is* a workload-profiles
  environment — raw ARM at `api-version=2024-03-01` shows a non-null
  `workloadProfiles` array — so a UDR *is* supported. None is attached. Egress
  control is therefore available but **not configured**, and this round does not
  claim otherwise.
* **Where the model runs.** Running Copilot CLI on an Azure VM or job does not
  place the model inside the VNet. Any private payload placed in a model or
  subagent prompt is an **export**, regardless of where the shell executing the
  command happens to run.

---

## 8. The private review boundary

Byte-only access is necessary for a future set-repair round, but it is not
sufficient. Repair requires *semantic* review of private material, and semantic
review requires a review backend that satisfies
`private_review_boundary_requirements` in the decision record.

Assessment of the current subscription is **executable**, not narrative. The
prose table below is a reading of
`docs/phase1_2h_r1_review_boundary_evidence.json`; the verdict is computed from
that same file by `scripts/phase1_2h_r1_review_boundary_assessment.py` and
committed as `docs/phase1_2h_r1_review_boundary_assessment.json`, which CI
regenerates and compares byte for byte. The instrument scores 13 conditions and
treats `NOT_ASSESSABLE` as **not** a pass, so a condition nobody checked cannot
be counted as satisfied. Observed: **0 passed, 5 failed, 8 not assessable ⇒
`DOES_NOT_QUALIFY`.**

| Requirement | Status |
|---|---|
| An in-VNet semantic-review service | **Absent.** `rg-jspace-observation-sea` contains no `Microsoft.CognitiveServices/accounts`, no ML workspace, and no in-VNet reviewer service. |
| Private endpoint on the review backend | **Absent.** The only same-region AI account, `aj-gpt56-25-943b-southeastasia` (RG `gpt56-sol-2025-rg`), has zero private endpoint connections. |
| Public network access disabled on the backend | **Fails.** That account has `publicNetworkAccess: Enabled` and `networkAcls.defaultAction: Allow`. |
| Backend within the project's authorization boundary | **Fails.** It belongs to an unrelated project. |
| Egress-controlled worker | **Not configured.** See §7.1. |

No qualifying backend was found **within the enumerated search scope**, which is
resource group `rg-jspace-observation-sea` in region `southeastasia` plus the
same-region AI accounts visible to the operator's control-plane listing.
Independent Audit F (F-04) required this be stated as a scoped observation
rather than as a fact about the world: whether some unlisted subscription,
tenant or resource group holds a qualifying backend was not observed and is not
asserted. What *is* asserted is that none is reachable under the required
boundary from the worker subnet this round would have to use, and that the
search scope is the one the round is authorized to provision into.

Under the round's terms this is decisive **even if byte-only access succeeds**,
because a repair round would otherwise have to either export private material to
a public endpoint or improvise a boundary mid-round. Both are refused. Note also
that the boundary fails on a second, independent ground: even had a qualifying
backend been found, the worker subnet has no egress control, and two of the
thirteen frozen conditions fail on that alone.

The round therefore terminates:

> **`BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY`**

The minimal design required to clear it, the resource types, the region and
network placement, the roles, the private endpoints and the cost estimate are
recorded in the round's implementation report. Provisioning it is an **operator
decision**, not something this round may improvise.

---

## 9. Counters

Ledger counters are **derived from execution evidence**, never asserted:

| Counter | Derivation |
|---|---|
| `azure_data_plane_content_reads` | one per object actually streamed |
| `byte_only_integrity_verifications` | one per object whose size and digest were compared |
| `azure_data_plane_writes` | 0 by first-party source analysis (no mutating Blob call in `IN_JOB_FIRST_PARTY_SOURCES`) **and** by RBAC (the job identity holds no data-plane write role on the account) |
| `semantic_input_reads` | 0 by first-party source analysis: the one function holding object bytes passes each chunk only to a SHA-256 digest, and no decode, parse, split or regex construct appears in it |
| `semantic_label_reads` | 0 by construction of the frozen member list — the 12 objects the record binds are inputs; no label object is enumerated, requested or streamed |
| `parser_invocations` | 0 by image content — the image installs no parser-bearing package — **and** by source analysis: no parser symbol is referenced in first-party in-job source |
| `predictions_generated` | 0 by receipt schema — no field can carry a prediction — **and** because nothing in the job writes anywhere |

Independent Audit E (E-05) and Audit F (F-06) both found an earlier version of
this table describing all five zeros as "structurally 0" by AST, which was true
of only two of them. The wording above states, per counter, what actually
establishes the zero. Where a zero rests on more than one independent basis,
both are named; where it rests on the absence of a capability rather than on
source analysis, that is said plainly.

A receipt whose counters contradict the ledger is a round failure, not a
discrepancy to be reconciled after the fact. The ledger's `counter_provenance`
block names, per counter, whether its value came from the receipt, from an Azure
control-plane query, or from an operator's hand-kept tally; the ledger validator
refuses to let a counter carrying a safety claim be classified as the last of
those. Two counters are honestly hand-kept — `control_plane_reads` and
`resource_creations_or_changes` — and neither carries a safety property.

### 9.1 The round's recorded outcome

Execution `p12h-r1-access-gate-003` (ACA execution `0fqre0m`, image
`sha256:f2cf1701…`) passed the gate: 12 members listed, 12 objects streamed,
396,613 bytes, aggregate digest `e1364afc…` reproducing the committed public
anchor, and no invariant failed. On the count of invariants: receipt 003 carries
`invariants_checked: 12`, which in the build that produced it was a **literal**
typed beside the checks, not a measurement of them — independent Audit C (C-12)
found that deleting a check would have left the number untouched. The probe now
derives the count from the checks that actually ran and lists their names in
`verdict.invariants_evaluated`, so the count and the list cannot disagree. That
list is absent from receipt 003, and its absence is the marker of a pre-fix
receipt; back-filling it would fabricate evidence about a run that has already
happened. `decode_attempts`,
`persist_attempts`, `azure_data_plane_writes`, `semantic_input_reads`,
`semantic_label_reads`, `parser_invocations` and `predictions_generated` were
all 0. The receipt is committed at
`docs/phase1_2h_r1_access_receipt_003.json`.

The preceding execution (`dlv8kmc`) is recorded too, because it refused: the
probe's own forbidden-environment denylist named `MSI_ENDPOINT` and `MSI_SECRET`,
which are exactly how Container Apps supplies the managed identity this protocol
requires. The rule was self-contradictory and the guard caught the operator's
error rather than a hypothetical adversary's. That refusal is evidence the gate
is real.

---

## 10. Terminal states

The three states are **ordered by precedence**, not overlapping. Audit B (B-09)
required that ordering and Audit C (C-07) found that this table originally
contradicted it, so state it explicitly: the gate question comes first. A round
that could not reach the source has not yet arrived at the boundary question,
and must not name the more advanced-sounding boundary state.

| State | Meaning | Precondition |
|---|---|---|
| `BLOCKED_ON_PRIVATE_SOURCE_ACCESS` | byte-only access itself could not be established | evaluated first; if it holds, the other two are unreachable |
| `BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY` | the byte-only gate passed, **and** the frozen boundary assessment does not return `QUALIFIES` | requires a passing gate |
| `READY_FOR_SEPARATELY_AUTHORISED_PRIVATE_REVIEW` | byte-only access succeeded **and** a qualifying private review boundary exists | requires a passing gate and all 13 frozen conditions PASS |

An earlier version of this table named the third state
`PRIVATE_SOURCE_ACCESS_RESTORED` and said the second applied "regardless of
byte-only outcome". Both were wrong. The name did not exist in the ledger's
`TERMINAL_STATES` vocabulary, and "regardless" inverted the precedence rule that
`classify_terminal_state` implements. The vocabulary above is the one the code
uses; there is exactly one list, in
`src/jspace_observation/parser_v3_v2_access_ledger.py`.

Reaching the third state requires every one of the thirteen frozen conditions in
§8 to be `PASS`. `NOT_ASSESSABLE` is not a pass: a condition that cannot be shown
to hold has not been shown to hold. Manufacturing a passing boundary to reach it
is prohibited.

The precedence rule is enforced in three places, so that no single edit can
defeat it: `classify_terminal_state` computes it,
`assert_gate_evidence_consistent` re-derives it and refuses a mismatch, and the
boundary suite asserts it against the committed artifact.

Independent Audit E (E-01) found that this sentence had been true only in form.
`assert_gate_evidence_consistent` was called solely on the object
`build_assessment` had just returned, whose evidence block that same call had
produced, so the second "place" could not fail and the third exercised the
first. Two changes make the sentence true. The consistency check is now run
against the **committed** file — which is the artefact a reader trusts, and the
one a hand edit would target — and when the evidence block names a receipt, the
check opens that file, hashes it against the recorded digest, re-derives the
gate outcome from it, and re-confirms the platform attestation. The boundary
suite carries negative controls for each of those, so the claim is now backed by
demonstrated refusals rather than by construction.
