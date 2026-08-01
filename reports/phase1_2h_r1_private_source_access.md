# Phase 1.2H-R1 — Cloud-first private-source access restoration

Terminal status: **`BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY`**

Protocol: `docs/phase1_2h_r1_cloud_access_protocol.md`
Decision record: `docs/phase1_2h_r1_access_decision_record.json`
Receipt: `docs/phase1_2h_r1_access_receipt_003.json`
Boundary assessment: `docs/phase1_2h_r1_review_boundary_assessment.json`
Ledger: `docs/phase1_2h_execution_access_ledger.json`

---

## 1. What this round was for

Phase 1.2H tried to begin the authorized `parser-v3-v2` set-repair round and
stopped at its first precondition. It read `publicNetworkAccess = Disabled` on
the storage account holding the retired `parser-v3-v1` sealed source and
concluded the source was unreachable.

That conclusion was wrong in a specific and instructive way. `Disabled` does not
mean unreachable; it means unreachable **from outside the virtual network**. The
account has a private endpoint at `10.80.2.4` and a linked private DNS zone. The
source was always reachable — from inside.

R1's objective was therefore narrow: establish authenticated, least-privilege,
read-only, in-VNet, **byte-only** access to the sealed source, and determine
whether the *rest* of what a repair round needs is present.

Byte-only means: stream every object into a SHA-256 accumulator and discard it.
No decode, no persistence, no interpretation. The round is allowed to learn that
the bytes are the bytes it expected, and nothing else.

---

## 2. What was provisioned

| Resource | Detail |
|---|---|
| Identity | `id-jspace-p12h-r1-read-sea`, user-assigned |
| Role assignments | exactly **two**: `Storage Blob Data Reader` scoped to the single container `jspace-results`; `AcrPull` scoped to the registry |
| Image | built by ACR Tasks, pinned by digest `sha256:f2cf1701…`, non-root user, read-only payload |
| Compute | Container Apps job `job-jspace-p12h-r1-access-gate`, VNet-injected into the same VNet as the private endpoint, `replicaRetryLimit: 0` |

No role granting write, delete, `Storage Blob Delegator`, or role-assignment
read was requested at any point. The identity cannot mint a user-delegation SAS
because it does not hold the role that would let it.

Every heavy step ran in the cloud. The operator's machine performed only
editing, `git`, and `az` control-plane calls.

---

## 3. What the gate proved

Execution `p12h-r1-access-gate-003` (ACA execution `0fqre0m`) passed.

| Property | Observed |
|---|---|
| List operations | 1, over the exact registered prefix only |
| Members | 12 observed, 12 expected, sets equal |
| Objects streamed | 12 |
| Bytes streamed | 396,613 |
| Per-object digest mismatches | 0 |
| Aggregate digest | `e1364afcac87516813d33a4e9fb3e370769487ab2f3ca47a08a3b4059db14e71` |
| Invariants checked / failed | 12 / 0 |

The aggregate digest is the load-bearing number. It was committed publicly
**before** this round ran, in `docs/phase1_2h_r1_review_boundary_evidence.json`'s
sibling evidence file, and it was independently recomputed offline three times.
The gate reproducing it from the live source is what makes this evidence rather
than assertion: a run that had reached the wrong container, or a source that had
drifted, could not have produced that value.

### 3.1 What it did **not** prove

Two properties are explicitly *not* claimed, because the job cannot observe them
and acquiring the ability to observe them would have meant granting the identity
more privilege than the round needs:

* **`public_network_access`** is recorded as `"Unknown"`, with
  `public_network_access_observed_by: operator_control_plane_read_before_run`.
  The probe holds no reader role on the account resource. The receipt schema now
  *refuses* any other value, so a future run cannot quietly upgrade an operator
  finding into an in-job observation.
* **`effective_read_only_verdict`** is `NOT_CONFIRMED_IN_JOB`. Reading one's own
  role assignments requires a role the identity deliberately does not hold. The
  read-only property is established instead by operator control-plane evidence,
  by `data_plane_writes: 0`, and by an AST proof that no write, upload, delete or
  delegation call site exists anywhere in the probe's reachable source.

An earlier draft returned `READ_ONLY_CONFIRMED` unconditionally. Independent
Audit A found it (A-02) and Audit B found it separately (B-03). It was a
hard-coded `True`, and it is the kind of defect this project treats as equal in
severity to a functional bug: the field was not measuring anything.

---

## 4. The refusal that came first

Execution 001 (`dlv8kmc`) refused and exited non-zero before authenticating,
with `FORBIDDEN_ENV_VAR`.

The cause was the probe's own denylist. It forbade `MSI_ENDPOINT` and
`MSI_SECRET` — which are precisely how Container Apps supplies the managed
identity the protocol *requires*. The rule was self-contradictory: satisfying it
was impossible in the only environment the protocol permits.

It is recorded here rather than quietly fixed because it is the round's best
evidence that the pre-flight guard is real. The guard fired on the operator's own
error, in production, at the cost of a run. A guard that has never refused
anything is a guard nobody has tested.

---

## 5. Why the round is still blocked

Byte-only access is necessary for set repair. It is not sufficient. Repair
requires **semantic** review of private material, and semantic review requires a
review backend that satisfies `private_review_boundary_requirements`.

The assessment is executable, not narrative:
`scripts/phase1_2h_r1_review_boundary_assessment.py` scores 13 conditions from
`docs/phase1_2h_r1_review_boundary_evidence.json` and treats `NOT_ASSESSABLE` as
**not** a pass, so a condition nobody checked cannot be counted as satisfied.

**Result: 0 passed, 5 failed, 8 not assessable ⇒ `DOES_NOT_QUALIFY`.**

| Requirement | Status |
|---|---|
| In-VNet semantic-review service | **Absent** — zero `Microsoft.CognitiveServices/accounts`, zero ML workspaces in `rg-jspace-observation-sea` |
| Private endpoint on the backend | **Absent** — the only same-region AI account has zero private endpoint connections |
| Public access disabled on the backend | **Fails** — `publicNetworkAccess: Enabled`, `networkAcls.defaultAction: Allow` |
| Backend inside the authorization boundary | **Fails** — it belongs to an unrelated project |
| Egress-controlled worker | **Not configured** — `routeTable: null`, `natGateway: null`, no custom outbound NSG rule |

Under §12.3 this is decisive **even though the byte-only gate passed**, because a
repair round would otherwise have to either export private material to a public
endpoint or improvise a boundary mid-round. Both are refused.

The instrument encodes the precedence rule directly: had the byte-only gate
failed, it would return `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`, not this state. The
more advanced-sounding terminal state cannot be claimed by a round that did less.

---

## 6. Independent audits

Two read-only review agents reviewed the frozen candidate. Both returned
**BLOCKED** and both independently recomputed the public anchors.

Audit A (methodology and safety) raised 15 findings, 2 blockers. It also
recorded the finding that matters most:

> No path was found by which a private semantic read, a data-plane write, or an
> export of sealed content could occur.

Audit B (repository and instrument consistency) raised 12 findings and
independently confirmed A's blockers.

| ID | Finding | Fix |
|---|---|---|
| A-02 / B-03 | `check_identity` returned `READ_ONLY_CONFIRMED` unconditionally | designated-identity binding; mismatch refuses; verdict is now `NOT_CONFIRMED_IN_JOB` |
| A-05 / B-05 | `--no-logs false` made the `az acr build` source location unparseable (exit 2) | removed; it is a `store_true` switch |
| B-11 | the ledger did not register `BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY` — the round's own intended terminal state | state added, and *earned*: it requires ≥14 cumulative byte-only verifications and zero semantic reads |
| A-03 | `public_network_access` claimed as an in-job observation | `"Unknown"` only; observer field added |
| A-04 | counter pins asserted in prose | backed by AST checks |
| A-06 | three evasions of the write-call AST check | non-docstring constants, aliased imports, and `eval`/`exec`/`compile`/`__import__` all closed |
| A-09 / B-08 | refusal paths had no emission contract | closed refusal schema; `_emit` validates before printing |
| A-11 | chunk size bounded the loop but not the SDK's GET | `max_single_get_size` / `max_chunk_get_size` passed to the client |
| A-12 | single-address DNS resolution | `getaddrinfo`; the resolved set must equal exactly `{10.80.2.4}` |
| A-13 | `allowSharedKeyAccess: false` described as excluding all SAS | corrected — it does not exclude user-delegation SAS; the *role set* does |
| A-15 / B-04 | `execution_id` conflated with the platform execution name | relabelled; `aca_execution_name` added |
| B-06 | parser-isolation test was substring-based | AST-based; Dockerfile COPY set pinned to the payload manifest |
| B-09 | boundary assessment was prose | executable instrument + schema + evidence bundle, checked in CI |

The audits' own limitation applies: self-authored tests are not independent
validation, and these audits reviewed a frozen commit rather than the final one.
Audits C and D reviewed the final state; their findings are recorded below the
line in the same file.

---

## 7. Private-access ledger

| Quantity | Value |
|---|---|
| Sealed inputs **semantically read** | 0 |
| Sealed labels **semantically read** | 0 |
| Private curator files read | 0 |
| Byte-only integrity verifications | 14 (2 pre-R1 local, 12 in-gate) |
| Predictions generated | 0 |
| Parser runs | 0 |
| Azure data-plane content reads | 12 |
| Azure data-plane **writes** | **0** |

The first two rows and the last are pinned `maximum: 0` in the receipt schema. A
probe that had violated them could not have emitted a schema-valid receipt at
all — the constraint is enforced by the artifact format, not by the program's
good intentions.

`parser-v3-v1` remains **`SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`**,
byte-unchanged. The Phase 1.2H transition to `REPAIR_ACCESSED` did **not** occur:
streaming bytes to a digest is not a repair read, and `UNSPENT` remains accurate
without qualification.

---

## 8. The exact next gate

**Operator approval and provisioning of a private semantic-review backend and an
egress-controlled worker boundary.**

Minimum design, none of which this round may provision on its own authority:

1. A `Microsoft.CognitiveServices/accounts` deployment (or equivalent reviewer
   service) **in `rg-jspace-observation-sea`**, in the same region.
2. `publicNetworkAccess: Disabled`, `networkAcls.defaultAction: Deny`.
3. A private endpoint into `snet-pe-jspace-sea`, with the matching private DNS
   zone linked to the VNet.
4. A route table or NAT-gateway egress control on the worker subnet, so the
   reviewer worker cannot reach any endpoint but the approved one. The
   environment is a workload-profiles environment, so a UDR is supported; the gap
   is configuration, not capability.
5. A role assignment granting the review identity only the inference role it
   needs, scoped to that one account.

Cost is dominated by the private endpoints (two, at roughly USD 7–8 each per
month) plus per-token inference; the job itself is consumption-billed and idles
at zero.

Until that exists, the following remain prohibited: private set construction,
migration, replacement review, sealing, image construction for evaluation,
preregistration, Stage P and Stage E.
