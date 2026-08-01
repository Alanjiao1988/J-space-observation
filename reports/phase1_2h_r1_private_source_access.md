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

Every row above is scoped to resource group `rg-jspace-observation-sea` in
`southeastasia` — the group and region this work runs in, and the extent of the
committed evidence. No claim is made about other resource groups in the
subscription. Note also that the failure is not simply "nothing was found": a
candidate backend class exists and *could* be provisioned, but the last row
would still fail, so provisioning a reviewer without also constraining worker
egress would not clear the boundary.

Under §10 read with §8 this is decisive **because the byte-only gate passed**,
not in spite of it: a repair round would otherwise have to either export private
material to a public endpoint or improvise a boundary mid-round. Both are
refused.

The instrument encodes the precedence rule directly: had the byte-only gate
failed, it would return `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`, not this state. The
more advanced-sounding terminal state cannot be claimed by a round that did less.

---

## 6. Validation

| Check | Local | GitHub-hosted runner |
|---|---|---|
| `tests/test_phase1_2h_r1_access.py` | pass | pass |
| `tests/test_phase1_2h_r1_review_boundary.py` | pass | pass |
| `tests/test_parser_v3_v2_access_ledger.py` | 97 passed | pass |
| Committed boundary assessment regenerates identically (`--check`) | pass | pass |
| Committed receipt is schema-valid | pass | pass |
| Current-state consistency instrument | pass | pass |
| Generated current-state block (`--check`) | pass | pass |
| Offline probe dry run reproduces the anchors | pass | pass |
| Probe imports no parser-bearing package | pass | pass |
| `compileall`, `git diff --check`, secret scan, large-file check | pass | pass |
| **Full repository suite** | **2103 passed, 0 failed** | **2086 passed, 2 failed, 15 skipped** |

The two runner failures are `tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last`
and `::test_seal_refuses_a_non_empty_parent_prefix`. Both abort with
`seal object is missing from the payload: locked_inputs.jsonl`. That file is
git-ignored private curator material: it exists on the operator's machine and
cannot exist on a public runner. The failures are environmental, are identical at
the pre-change baseline, and are unrelated to this round.

They are reported rather than suppressed. Making them skip when the file is
absent would turn a known-red signal into a green one without changing anything
real, and a suite that is green because a check quietly opted out is worse than
one that is honestly red. The consequence — that this workflow's full-suite step
can never pass on a public runner, and so trains a reader to ignore it — is a
genuine instrument weakness and is recorded as such.

---

## 7. Independent audits

### 7.1 Audits A and B — the frozen candidate `47f207a`

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

### 7.2 Audit C — the post-gate state `393ff3e`

Audit C reviewed the state after the gate had run, the ledger had been updated
and the documents rewritten. It also returned **BLOCKED**, with 1 blocker, 8
major and 5 minor findings.

It re-examined the property Audit A had established against the earlier commit
and reached the same conclusion — that it found no path by which a private
semantic read, a data-plane write, or an export of sealed content could occur —
and it separately confirmed that the six ledger tests modified in `393ff3e` were
legitimate updates to a changed committed state rather than weakened assertions.

Its blocker was the more important result:

| ID | Sev | Finding | Fix |
|---|---|---|---|
| C-01 | **Blocker** | the boundary instrument took `--byte-only-gate-passed` as an operator-set flag and never read the receipt, so it could not have detected a failed gate; CI hard-coded `true` | flag removed; `--receipt` added; the outcome is derived from 12 independent conjuncts over the receipt; the receipt's SHA-256 is recorded in the assessment; `assert_gate_evidence_consistent` re-derives the precedence rule |
| C-02 | Major | the terminal state was bound only to an integer in the ledger's own file, and `14` conflated 2 local with 12 authoritative verifications | terminal state now requires the committed receipt to agree; the composite is decomposed and named |
| C-03 | Major | `counter_provenance` was optional, its `evidence` strings unvalidated, and 4 safety counters absent from the machine-evidence set | block made mandatory; evidence strings validated; the 4 counters added |
| C-04 | Major | `comparator_predictions_generated` was declared `receipt_derived_exact`, but no such field exists in the receipt | reclassified; a `structurally_zero_by_source_analysis` class added for counters whose zero is a property of the code |
| C-05 | Major | five documents claimed the `maximum: 0` schema pins *detect* violations | corrected everywhere: the pins constrain what may be *reported*; the AST source check is what supports the zeros |
| C-06 | Major | the AST denylist missed 4 of the 9 frozen `forbidden_operations` | denylist widened to cover them |
| C-07 | Major | protocol §10 said the boundary state applied "regardless of byte-only outcome", inverting the precedence rule; two state names existed outside `TERMINAL_STATES` | table rewritten with an explicit precedence column; one vocabulary, asserted by test |
| C-08 | Minor | "protocol §12.3" does not exist; cited in a committed ledger event | erratum event 9 appended under a new `record_correction` kind; prose citations corrected to §10 with §8 |
| C-09 | Major | documents asserted "Audits C and D reviewed the final state" — written before either audit returned | withdrawn; replaced with what actually happened, here and in `L-40` |
| C-10 | Minor | a ledger event made a subscription-scoped negative claim from resource-group evidence and omitted a disqualified candidate | corrected by erratum event 9 |
| C-11 | Minor | three documents said the schema refuses any `public_network_access` other than `"Unknown"`; the enum permitted three | schema pinned to `const: "Unknown"`, making the prose true |
| C-12 | Minor | `invariants_checked: 12` was a literal restated as a measurement | counted from the invariants actually evaluated |
| C-13 | Minor | execution 002 appeared in no record | accounted for; see §5 |
| C-14 | Minor | "the entire first-party source executed by the gate" excluded the receipt validator, which also runs in-job | AST check extended to it; the scope claim is now accurate |

### 7.3 What no audit has reviewed

Audit D did not complete. Its process was lost before it reported, and no
finding is attributed to it.

More importantly, the remediation of Audit C's findings — this section included
— is material that no independent review has seen. That is the structure `L-38`
and `L-40` describe, and it is not closed. Self-authored tests are not
independent validation, and an audit that reviewed the previous commit is not a
review of this one.

---

## 8. Private-access ledger

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

The first two rows and the last are pinned `maximum: 0` in the receipt schema.
State what that buys carefully — independent Audit C (C-05) found the earlier
wording here overclaimed. The probe writes those counters as literals, so a
probe that had violated them would emit `0` and its receipt would still
validate; the pins do not detect a violation. What they do is prevent an honest
instrument from recording a non-zero count in a schema-valid artifact, which
closes the specific failure mode of a violation being normalised into an
acceptable receipt.

The support for the zeros themselves is `assert_no_write_calls_in_source`: an
AST walk over the probe's source that fails if a decode, persist, data-plane
write or parser call is present. That is a property of the code, established by
reading it.

`parser-v3-v1` remains **`SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`**,
byte-unchanged. The Phase 1.2H transition to `REPAIR_ACCESSED` did **not** occur:
streaming bytes to a digest is not a repair read, and `UNSPENT` remains accurate
without qualification.

---

## 9. The exact next gate

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
