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

`allowSharedKeyAccess: false` means shared-key and SAS authentication are
impossible by construction, not merely forbidden by policy. The only way in is
Entra ID plus the private endpoint.

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
reachable; verbose SDK body logging is off; `publicNetworkAccess` is `Disabled`;
the blob FQDN resolves to the single registered private IP; the credential is
`ManagedIdentityCredential` with an explicitly supplied user-assigned client ID.

### Stage B — membership

List **only** the exact registered prefix. Compare the observed member set
against the 12 members derived from the committed seal record, entirely in
memory. Refuse on any count difference, any set difference, or any observed name
outside the prefix. Emit only aggregates — never a member name.

### Stage C — byte-only integrity

For each expected member, stream the object in 256 KiB chunks directly into a
SHA-256 accumulator. Compare size and digest against the seal record. Refuse on
any mismatch.

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

A probe that decoded, persisted or wrote **cannot emit a schema-valid receipt**.
That is the point: the constraint is enforced by the artifact format, not by the
program's good intentions.

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
is the narrower structural claim — no mutating operation appears anywhere in its
reachable source — and that is what it asserts, by AST.

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

Assessment of the current subscription:

| Requirement | Status |
|---|---|
| An in-VNet semantic-review service | **Absent.** `rg-jspace-observation-sea` contains no `Microsoft.CognitiveServices/accounts`, no ML workspace, and no in-VNet reviewer service. |
| Private endpoint on the review backend | **Absent.** The only same-region AI account, `aj-gpt56-25-943b-southeastasia` (RG `gpt56-sol-2025-rg`), has zero private endpoint connections. |
| Public network access disabled on the backend | **Fails.** That account has `publicNetworkAccess: Enabled` and `networkAcls.defaultAction: Allow`. |
| Backend within the project's authorization boundary | **Fails.** It belongs to an unrelated project. |
| Egress-controlled worker | **Not configured.** See §7.1. |

No qualifying backend exists. Under the round's terms this is decisive **even if
byte-only access succeeds**, because a repair round would otherwise have to
either export private material to a public endpoint or improvise a boundary
mid-round. Both are refused.

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
| `azure_data_plane_writes` | structurally 0 — no write operation exists in the probe's reachable source |
| `semantic_input_reads` | structurally 0 — nothing decodes |
| `semantic_label_reads` | structurally 0 |
| `parser_invocations` | structurally 0 — no parser in the image |
| `predictions_generated` | structurally 0 |

A receipt whose counters contradict the ledger is a round failure, not a
discrepancy to be reconciled after the fact.

---

## 10. Terminal states

| State | Meaning |
|---|---|
| `PRIVATE_SOURCE_ACCESS_RESTORED` | byte-only access succeeded **and** a qualifying private review boundary exists |
| `BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY` | no qualifying private semantic-review backend exists, regardless of byte-only outcome |
| `BLOCKED_ON_PRIVATE_SOURCE_ACCESS` | byte-only access itself could not be established |

Manufacturing a passing boundary to reach the first state is prohibited.
