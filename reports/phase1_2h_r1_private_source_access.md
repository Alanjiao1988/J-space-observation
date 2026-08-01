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
| Invariants checked / failed | 12 / 0 — a literal in the build that ran (C-12); derived from the evaluated set only in the current build |

The aggregate digest is the load-bearing number. It was committed publicly
**before** this round ran, in `docs/phase1_2h_r1_review_boundary_evidence.json`'s
sibling evidence file, and it was independently recomputed offline three times.
The gate reproducing it from the live source is what makes this evidence rather
than assertion: a source that had drifted from the committed expectation could
not have produced that value.

Audit F (F-15) struck the claim that stood in the last clause of that sentence:
that a run "that had reached the wrong container" could not have produced the
aggregate. It could. The aggregate is a function of the bytes, not of where they
came from. A container holding byte-identical copies of the twelve objects
yields the identical digest, and nothing in the receipt is signed by the storage
account. What the reproduction establishes is that *the bytes the job read are
the bytes the public anchor describes* — which is the property the round needs,
and is strictly weaker than a statement about location. The container identity
rests separately on the frozen decision record, which the receipt pins by
SHA-256 and which names the account and prefix; that is an operator-authored
binding, not an in-job observation.

Independent Audit E (E-07) then observed that the boundary assessor was not
using it. Every conjunct of its gate decision was a field of the receipt
compared against another field of the receipt, so the instrument checked that
the probe agreed with itself. The assessor now recomputes the anchor offline
from the committed expected-evidence file — whose SHA-256 the decision record
pins — and requires the receipt to reproduce it. That is the one value in the
receipt checkable against something the probe did not write, and it is
recomputed rather than hard-coded, so editing the evidence file cannot move the
target to meet a receipt.

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
  by `data_plane_writes: 0`, and by an AST check that no write, upload, delete
  or delegation call site appears in the two first-party Python files that run
  inside the job. Independent Audit E (E-04) required the scope of that last
  clause be stated exactly: it is a property of first-party source, not of "the
  reachable source", which would include the Azure SDK, the standard library and
  the base image — none of which is parsed.

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

The counts below are for the present commit. Where a run identifier is given it
is immutable and independently viewable; where it is not, the row is an operator
assertion and is marked as such.

| Check | Local | GitHub-hosted runner |
|---|---|---|
| `tests/test_phase1_2h_r1_access.py` | 178 passed | pass |
| `tests/test_phase1_2h_r1_review_boundary.py` | 56 passed | pass |
| `tests/test_parser_v3_v2_access_ledger.py` | 113 passed | pass |
| Committed boundary assessment regenerates identically (`--check`) | pass | pass |
| Committed receipt is schema-valid | pass | pass |
| Current-state consistency instrument | pass | pass |
| Generated current-state block (`--check`) | pass | pass |
| Offline probe dry run reproduces the anchors | pass | pass |
| Probe imports no parser-bearing package | pass | pass |
| `compileall`, `git diff --check`, secret scan, large-file check | pass | pass |
| **Full repository suite** | not run locally this round | see below |

The full suite runs on a GitHub-hosted runner rather than locally. That is an
operator constraint, not a methodological one: the local machine has overheated
and rebooted repeatedly under sustained load, and a suite that crashes its host
reports nothing.

Two runs are on record, and Audit F was right to insist they be distinguished —
an earlier version of this table presented a parent-commit run as validation of
material that commit did not contain.

| Run | Commit | Result |
|---|---|---|
| `30693832918` | `ccbaab0` | 2132 passed, 2 failed, 15 skipped |
| `30695685244` | `13015d4` | 2174 passed, 2 failed, 15 skipped — every R1-specific step passed |

The two failures are identical in both runs and are pre-existing and
environmental: `tests/test_parser_v3_seal_job.py` needs the git-ignored
`locked_inputs.jsonl`, which is absent from a fresh clone by design. They are
unrelated to this work and predate it.

**The present commit has no full-suite run recorded here**, because the commit
does not exist until this document is written into it. Its run is dispatched
after push, and the terminal state does not depend on it: every gate this round
turns on is in the three R1 suites and the `--check` steps above, all of which
run locally in seconds and are reproducible by any reader.

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
| C-06 | Major | the AST denylist missed 4 of the 9 frozen `forbidden_operations` | a *whitelist* on the one byte-handling function, not a wider denylist — see below |
| C-07 | Major | protocol §10 said the boundary state applied "regardless of byte-only outcome", inverting the precedence rule; two state names existed outside `TERMINAL_STATES` | table rewritten with an explicit precedence column; one vocabulary, asserted by test |
| C-08 | Minor | "protocol §12.3" does not exist; cited in a committed ledger event | erratum event 9 appended under a new `record_correction` kind; prose citations corrected to §10 with §8 |
| C-09 | Major | documents asserted "Audits C and D reviewed the final state" — written before either audit returned | withdrawn; replaced with what actually happened, here and in `L-40` |
| C-10 | Minor | a ledger event made a subscription-scoped negative claim from resource-group evidence and omitted a disqualified candidate | corrected by erratum event 9 |
| C-11 | Minor | three documents said the schema refuses any `public_network_access` other than `"Unknown"`; the enum permitted three | schema pinned to `const: "Unknown"`, making the prose true |
| C-12 | Minor | `invariants_checked: 12` was a literal restated as a measurement | counted from the invariants actually evaluated |
| C-13 | Minor | execution 002 appeared in no record | accounted for; see §7 |
| C-14 | Minor | "the entire first-party source executed by the gate" excluded the receipt validator, which also runs in-job | AST check extended to it; the scope is now stated as first-party in-job source rather than "reachable source" (see E-04) |

### 7.3 Audits E and F — the post-remediation state `ccbaab0`

Two further independent read-only reviews were commissioned against the commit
that closed Audit C. Both returned **BLOCKED**. They ran separately and did not
see each other's output, and they converged on the same three mechanisms, which
is the part worth recording: the receipt is a self-report; the source-analysis
claims outran what the AST checks actually expressed; and negative findings
about the environment were stated as facts about the world.

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| F-01 | Blocker | the round's terminal state rested on an unsigned, self-authored receipt, described in a ledger event as "the **signed** execution receipt" — nothing signs it | "signed" removed; `assert_execution_is_platform_attested` added, binding the receipt to the committed control-plane execution inventory (name, status, image digest, and the `--execution-id`/`--freeze-commit` the platform recorded); its docstring states that this does not make the counters true |
| F-04 | Blocker | "No qualifying backend exists" stated as a fact about the world from a resource-group listing | scoped to the enumerated search scope in the protocol, the report and `generate_current_state.py`; the second, independent egress-control ground for failure is now stated alongside it |
| F-02 | Major | the strengthened AST checks were cited for execution 003, which ran a frozen probe predating them | reframed as post-hoc verification and made true: a test recovers the frozen source at the receipt's freeze commit, confirms it hashes to `probe_source_sha256`, and runs both checks over it |
| F-03 | Major | "the bytes never leave a bounded buffer that is overwritten each chunk" — CPython drops a reference; it does not zero storage | claim withdrawn and replaced with the reference-graph property that is actually true and actually checked |
| F-05 | Major | `QUALIFIES` was unreachable through `build_assessment` by accident rather than by design | made an explicit, tested property; a future round that adds evidence fields will see that test fail and must decide deliberately |
| F-06 | Major | `byte_only_integrity_verifications: 14` classified `receipt_derived_exact` when the receipt reports 12 | new `composite_of_separately_evidenced_parts` class with a mandatory, validator-enforced decomposition; the C-02 rule was re-stated on the evidence so the reclassification could not weaken it |
| F-07 | Major | `generate_current_state.py` hard-coded the unsupported conclusions | both corrected at the generator, so every current-state document inherits the correction |
| E-01 | Major | `assert_gate_evidence_consistent` could not fail; three documents called it a three-place enforcement point | now applied to the *committed* file, and it opens the receipt the evidence block names, hashes it, and re-derives the outcome; four negative-control tests show it rejecting tampering |
| E-02 | Major | the byte-handler whitelist was called "complete"; it constrained calls, so `global SINK; SINK = chunk`, `return chunk`, `for b in chunk` and a same-named non-digest sink all passed | "complete" withdrawn; the check now tracks the chunk binding and refuses any use that is not an argument to a whitelisted digest call, with six negative-control tests. **Closure review found this incomplete — see E-12 in §7.5.** |
| E-03 | Major | the C-06 row described a denylist where the fix was a whitelist; §8 described the AST checks inaccurately | corrected |
| E-04 | Major | "the probe's reachable source" survived in the protocol and this report | replaced in `docs/phase1_2h_r1_cloud_access_protocol.md` and in this report with the first-party in-job scope actually checked; the "scope claim is now accurate" certification in the C-14 row withdrawn. The row previously said "replaced everywhere", which was false: `paper/methods_ledger.md` still carried it. **See E-13 in §7.5.** |
| E-05 | Major | `structurally_zero_by_source_analysis` claimed AST enforcement for four counters no AST check reaches, and carried no rule that the value was zero | those four moved to a new `zero_because_the_activity_has_never_occurred` class; both zero classes now refuse a non-zero value. The one counter left behind still cited checks that do not reach it — **see E-14 in §7.5.** |
| E-06 | Major | the C-12 residual test asserted a property of a synthetic fixture, never opening receipt 003 | it now opens the committed receipt, and a companion test shows a receipt built today carries the derived list |
| E-07 | Major | every gate conjunct was the receipt agreeing with itself | anchor conjuncts added, recomputed offline from the committed expected-evidence file. This is external-value consistency, not proof that a stream occurred; the docstring claiming the stronger reading was corrected on closure review |
| E-08 | Minor | the requirements docstring said "nine" where there are twelve, and did not disclose that some conjuncts are co-derived | corrected in `GATE_REQUIREMENTS`. The *module* docstring was missed and still said "nine independent" — **see §7.5** |
| E-09 | Minor | `invariants_checked: 12` restated as a measurement in four current-state documents | qualified at the generator and in this report. The hand-written `docs/thread_handoff.md` banner was missed — **see §7.5** |
| E-10 | Minor | `formal_v2_evaluation_access.labels_opened_for_scoring` — the strongest safety claim the ledger makes — was absent from `_MACHINE_EVIDENCE_REQUIRED` | added. The composite class added for F-06 in the same commit reopened the route — **see E-16 in §7.5** |
| E-11 | Minor | the committed execution inventory was bound to nothing | `tests/test_phase1_2h_r1_review_boundary.py` asserts it agrees with `azure.job_executions` |

### 7.4 Closure review of Audits E and F — both BLOCKED again

Audits E and F were re-engaged against `13015d4`, the commit remediating the
eighteen findings above, with a clean working tree. **Both returned BLOCKED.**

This is the third consecutive round in which review of a remediation found new
defects, and twice now the defect was introduced *by the remediation itself*.
Every counterexample below was produced by an independent reviewer — some by
executing the instrument, others, including F-03b and the byte-handler
rebinding, purely by reading its source. An earlier draft of this sentence
credited all of them to execution, which overstated the method and understated
the finding. The author's three suites were green throughout — which is the
point: a green suite means the properties someone thought to check hold, and the
recurring failure has been in what was not thought of.

| ID | Severity | Finding, as demonstrated | Disposition in this commit |
| --- | --- | --- | --- |
| E-16 | Major | The `composite_of_separately_evidenced_parts` class added for F-06 reopened exactly the route that adding `labels_opened_for_scoring` to `_MACHINE_EVIDENCE_REQUIRED` for E-10 closed — in the same commit. Audit E set that counter to 7 with two prose addends and `validate_ledger` accepted it. "Machine evidence" was implemented as "any class except operator-maintained", and the value rules were keyed on the *class*, so reclassifying moved a counter out from under them. | Two rules. `_PHASE_1_2H_ZERO_ACCESS_COUNTERS` pins the semantic-access counters to zero independently of class, the way the parser counters already were — which is why the same mutation always failed on those. And every addend of a counter in `_MACHINE_EVIDENCE_REQUIRED` must itself cite a committed artifact. Audit E's exact mutation is now a test, run against all six classes. |
| E-12 | Major | The byte-flow analysis tracked the loop variable but not the parameter carrying the stream, so `return digest.hexdigest(), total, chunks` returned every chunk to the caller and **passed**. Separately, `digest_names` matched on the attribute name alone, so `digest = exfil.sha256()` qualified as the digest while the docstring said `hashlib.sha256()`. | Parameters are tracked, permitted only as the iterated expression; the digest receiver must be assigned from `hashlib.sha256()` specifically. Both counterexamples are now negative-control tests, alongside a positive control that the live handler still passes. |
| F-03b | Major | `digest = hashlib.sha256()` followed by `digest = sink` left the name in `digest_names` while the object receiving bytes was no longer a digest. | Any rebinding of a digest name is refused (`DIGEST_NAME_REASSIGNED`), with a test. |
| E-13 | Major | The E-04 row above claimed the phrase was "replaced everywhere". `git grep` refuted it in one command: `paper/methods_ledger.md:840` still called it "positive structural proof" over "the probe's reachable source" — the strong form, in the most formal artifact in the repository. `L-40` also still said the Audit C remediation "produced material no audit has seen", which Audits E and F had by then seen. | `methods_ledger.md` corrected to the two-file first-party scope and to "check" rather than "proof"; `L-40` rewritten to record all three review rounds and the non-convergence; the E-04 row restated as the files actually changed. |
| F-01b | Major | The schema said the attestation field "establishes that the described execution really happened". The inventory is an operator-transcribed, unsigned JSON file in this same repository; a hand-edited entry satisfies the check as easily as real control-plane output. | Schema description rewritten: it establishes agreement with a separately committed transcript, constrains a rogue probe and not a rogue operator, and "attested" names a provenance class, not cryptographic authentication. |
| F-02b | Major | `derive_expected_anchors`'s docstring said the decision record pins the evidence file's SHA-256 *and its members digest*, "both are verified". The members digest is never read. It also said a fabricated receipt "cannot produce this value except by copying it" — but the anchor is public, so copying is freely available. | Both claims corrected in place. The docstring now states what the conjunct does establish (consistency with external values, defeating a wrong container or a truncated listing) and what it does not (proof that a stream occurred). |
| E-14 | Minor | The single counter left in `structurally_zero_by_source_analysis` still cited two AST checks as its basis. Neither constrains which files are *read* — the probe itself calls `read_text` in four places. The real basis, the frozen prefix and member list, had been demoted to a `note`. | Evidence rewritten to lead with the frozen binding. |
| E-15 / E-09b | Minor | `docs/thread_handoff.md:26` still read "Twelve invariants checked, none failed" in the hand-written banner while the generated block in the same file was corrected, and attributed the zeros to "the probe's own source … anywhere in it" — one file, where the check reads two. | Banner rewritten. |
| E-08b | Minor | The *module* docstring still said `derive_gate_outcome` "requires *nine* independent properties" after the count was corrected in `GATE_REQUIREMENTS`. | Corrected, with the miss recorded in the text. |
| F-04b | Minor | Two unscoped backend claims survived in the assessor module docstring and its `NOT_ASSESSABLE` reason text. | Scoped to the enumerated search scope. |
| F-07b | Minor | The generator said each chunk is passed "only to a SHA-256 digest". It is also passed to `len`. | Corrected; both generated documents inherit it. |
| E-17 | Minor | `load_gate_evidence` hashed the receipt raw while `_assert_cited_receipt_reproduces_the_gate` hashed it LF-normalised, so on a Windows clone with `core.autocrlf=true` the assessor refused an untampered repository. Cannot cause a false pass. | Both normalise; the R1 JSON artifacts pinned `text eol=lf`. |

Two closure findings are **accepted as residual limitations rather than fixed**,
because fixing them requires infrastructure this round is not authorised to
build:

- **The inventory is not cryptographically authenticated.** Audit F is right.
  Real attestation needs a signed control-plane response or an authenticated
  output channel. What exists constrains the probe, not the operator, and every
  document that mentions it now says so.
- **`zero_because_the_activity_has_never_occurred` rests on repository-internal
  evidence.** A validator that refuses to record an activity cannot detect that
  the activity occurred. The class name states the claim and the evidence names
  the artifacts; it is an argument from the absence of any authorised occasion,
  not an observation, and it is now labelled that way.

  *Superseded in part by §7.6.* Audit F's further point — that the class was
  nonetheless satisfying a rule whose message claimed safety counters "require
  machine evidence" — was a fixable defect, and was fixed.

### 7.6 Second closure review — both audits BLOCKED a third time

Audits E and F reviewed `55d0e2b` and converged independently on the same two
defects, neither of which the author's suites could have caught, because both
concerned properties nobody had thought to assert.

**The dispositions recorded in this table were reviewed by Audit F in the fourth
round and seven of the eight were judged overstated.** The table below is the
corrected version; each row now states what the fix does and, where the fix was
later found incomplete, says so and points at the section that closes it. The
original wording is not reproduced, because reproducing an overstatement to
annotate it is how overstatements survive; what it claimed is described in the
correction itself.

| ID | Finding, as demonstrated | Disposition, as corrected in round four |
| --- | --- | --- |
| E-18 | Two counters were excluded from the class-independent zero pin because their correct value is positive, and *nothing else constrained them*. Audit E set `azure.data_plane_content_reads = 500` with no other edit and the ledger validated. It then raised `byte_only_integrity_verifications` from 14 to 99 by resumming the composite addends with citations to files that really exist; that validated too. The sentence written in the previous commit asserting both were "constrained by the receipt-citation rule instead" was false: the rule checks addend *shape*, never addend *amounts*, and never reached the first counter at all. | Both pinned to their exact values in `_validate_status_agreement`. Regression tests assert the pin owns the *upward* direction, which the pre-existing floor could not catch. **Audit F judged this row accurate — the only one of the eight it did.** F-13 then found the pinned constant's own comment describing it as a floor a later round could exceed, contradicting the equality; corrected in §7.9. |
| E-19 | The byte-flow analysis constrained the body of the function *named* `stream_object_digest`, but nothing bound that name to what executes: the scan took the **first** definition `ast.walk` returned, while Python binds the **last**. Three handlers passed every check while shipping every chunk to a module global — one decorated, one rebound by a plain `stream_object_digest = _tap(stream_object_digest)` after the def, one simply defined twice. | Refused rather than analysed. **Incomplete twice over: E-20 (§7.7) defeated it at module scope by eight further routes, and F-08 (§7.9) bypassed it entirely by leaving the analysed handler pristine and calling a different function from the entrypoint.** A check on a definition cannot establish anything about what runs; §7.9 adds the call-site check that can. |
| F: citation existence | `_CITATION_PATTERN` matched any token ending `.py`/`.json`/`.md`, so `docs/does-not-exist.json` satisfied the evidence requirement. A citation that cannot be followed is not evidence. | Cited paths are resolved against the repository root and must be real files. **Incomplete twice: E-22 (§7.7) escaped the root via `..`; F-09 (§7.9) found the missing-checkout branch fail-open, reopening the original hole exactly where nothing could observe it.** Both closed. Note the residual the fix never removed: "names a file that exists" is not "the file supports the number", and no offline check can make it so. |
| F: name shadowing and rebinding | `len = leak_and_count` inside the handler, and digest rebinding via walrus, `for` target, `with` target and tuple unpacking, all passed. | A recursive binding collector was added — for the handler scope only, covering assignment, augmented and annotated assignment, walrus, `for`, `with`, `except`, imports and comprehensions. **It did not model `match` capture patterns and was not applied at module scope; E-20 (§7.7) exploited both.** One enumerator now serves both scopes. |
| F: provenance category | `zero_because_the_activity_has_never_occurred` satisfied a rule whose message says safety counters "require machine evidence". It carries none. | The class is documented as a **record assertion**, not evidence, and bound to committed state flags. **The bindings themselves were wrong: F-10 (§7.9) found four successor-set counters checked against `retired_v1_state.formal_evaluation_ever_run`, a flag about `parser-v3-v1`.** Each counter is now bound to the block describing the same object. The class text's residual claim to be "still machine evidence in the sense the ledger requires" is struck; it is not machine evidence, and nothing measured these zeros. |
| F: L-40 overstatement | L-40 and §7.4 said every counterexample was produced by a reviewer *executing* the code. Audit F established F-03b statically, and E-19 was found by reasoning about `ast.walk` order. | Corrected in both places — **and the correction introduced a contradiction of its own**, which F-15 (§7.9) cited: the replacement text said the counterexamples were produced "with working counterexamples rather than by reading" two paragraphs before saying static reading was sufficient. Both methods were used; L-40 now says so once. |
| F-02b | This report claimed a receipt naming a *different container* would fail the anchor check. It would not: the anchor covers per-object digests, count and byte total, and no container, account or path name enters it. | Withdrawn from the docstring. **The same claim survived in §3 of this report and was re-cited as F-15 (§7.9); it is now withdrawn there too.** What the anchor establishes is that the bytes read match the public expectation — not where they came from. Container identity rests on the frozen decision record, an operator-authored binding. |
| F-04b | The `NOT_ASSESSABLE` reason read "no review backend exists" — an unscoped claim about the world, reproduced eight times in the decision record. | Scoped to what the assessor observed. **The scoping named the wrong input: F-12 (§7.9) found it appealing to the silence of the job execution inventory, which lists access-gate runs and could never contain a review backend.** The reason now cites the review-boundary evidence bundle, which does not fall silent — it lists a candidate and reports it non-qualifying — and discloses that the bundle is an unsigned operator transcript. |

### 7.7 Third closure review — Audit E BLOCKED a fourth time

Audit E reviewed `2acbac1` and confirmed E-18, the citation-existence rule (except
one gap), the provenance-class binding, and that no test had been weakened. It
found the E-19 fix incomplete and the claims made about it false.

| ID | Severity | Finding, as demonstrated | Disposition in this commit |
| --- | --- | --- | --- |
| E-20 | Major, blocking | Eight working counterexamples, each reporting `inspected == 4` exactly like the live handler while delivering every chunk to a module-level sink. The structural point is the one worth recording: **this repository added a complete recursive binding enumerator and then wrote the module-level scan beside it by hand, with four node types and no recursion.** So `stream_object_digest, _spare = _tap(...), None` (tuple target), `for stream_object_digest in (...)`, `with ... as stream_object_digest`, `globals()['stream_object_digest'] = ...` and `setattr(sys.modules[__name__], ...)` all rebound the handler and passed. Separately, `len = _tap_len`, `hashlib = _H` and `hashlib.sha256 = _fake` at **module** scope left the body byte-identical while every whitelisted call resolved to the attacker's — because the shadowing rule inspected only bindings *inside* the handler. And `match _leak: case len:` shadowed `len` *inside* the body, because the enumerator did not model `match` capture patterns. | There is now one enumerator, `_bindings_in`, used at both scopes; it models `MatchAs`, `MatchStar` and `MatchMapping`. The whitelist check runs at module scope too, where `hashlib` may arrive only by a plain `import hashlib` — `import hashlib as h` and `import evil as hashlib` are both refused. New `_assert_no_reflective_rebinding` refuses `setattr`/`delattr`/`exec`/`eval`/`compile`/`__import__` calls, `globals()`/`vars()`/`locals()` subscript stores, and attribute assignment to any whitelisted call name. All twelve counterexamples from this and the previous round are regression-tested, each against a passing control. |
| E-21 | Major, blocking | The claim written *in the previous commit* — "the check now refuses any source in which that name is defined more than once, rebound, decorated, shadowed, or nests a scope, which is what makes the single-function premise true rather than assumed" — was false in both the "rebound" and "shadowed" terms, and had been generated into `reports/current_status.md`, `docs/thread_handoff.md` and this report. Two docstrings carried the same defect: `_handler_bindings` claimed it "lets the caller establish that `len` really is the builtin", and `assert_byte_handling_is_digest_only` claimed "no path in *this source* moves object bytes anywhere but into a digest". | All four rewritten to state the bounded fact: no *syntactic* binding construct in this source rebinds the handler or the whitelisted names, at either scope. Explicitly **not** claimed: anything about the running process, or about a rebinding performed by a module that imports this one. |
| E-22 | Minor | `_cited_paths_that_exist` said cited paths must resolve "in the repository" and did `(root / candidate).is_file()` with no containment check, so `../package.json` and `docs/../../package.json` resolved to real files outside the repository and were accepted. | Paths are resolved and required to be relative to the root. |
| E-23 | Minor | `WHITELISTED_NAME_SHADOWED` had no test at all; deleting the rule broke nothing. | Covered, at both scopes, along with every other new refusal. |

Audit E confirmed as **closed**: E-18 (including the exact resummed-and-cited 99
counterexample), citation existence for nonexistent paths, directories and
wrong-case paths, the `_assert_never_occurred_agrees_with_state` binding
(judged "real, not ceremonial", with both `return` paths shown unreachable), and
that `test_g01…` is now strictly stronger and `BYTE_NAME_ESCAPES_HANDLER` remains
reachable and asserted.

### 7.9 Third closure review — Audit F BLOCKED a fourth time

Audit F reviewed the same commit, `2acbac1`, and returned eight findings. Its
most consequential result is structural: it defeated the byte-flow analysis
**without touching it**, which no previous round had done.

| ID | Severity | Finding, as demonstrated | Disposition in this commit |
| --- | --- | --- | --- |
| F-08 | Major, blocking | The definition-level check reasons about a function; the job runs a call site. Audit F left `stream_object_digest` pristine — unique, undecorated, passing every rule added for E-19 and E-20 — and changed the entrypoint to call `evil_stream_object_digest(stream.chunks())` instead. Both checks passed, `inspected` was 4 exactly as for the live handler, and every chunk went to a module list. The analysed function was proved safe and was dead code. | New invariant `BYTE_SOURCE_REACHES_ONLY_THE_HANDLER`, added to the preflight chain. Every `.chunks()` call must appear directly as an argument of a call to `stream_object_digest` *by that name*; every name bound to `.download_blob()` may be used only as the receiver of `.chunks()`; and at least one such call site must exist, so renaming the source cannot make the check vacuous. Six bypass routes are regression-tested — variable-held iterator, wrapped iterator, aliased handler, escaping stream object, renamed source, unreadable open call — each asserted to still pass the definition-level check, because the two are not redundant. |
| F-09 | Major, blocking | Citability was fail-open by two routes. (a) When `root/"docs"` is not a directory — an installed package with no checkout — the check degraded to the shape test, so `docs/does-not-exist.json` was accepted again, precisely where nothing could observe it. (b) A zero safety counter could be reclassified as `composite_of_separately_evidenced_parts` with two **zero** addends citing two unrelated real files, satisfying the two-addend, two-evidence, sums-to-value shape while evidencing nothing. | (a) Fails closed: no path can be shown to exist, so none is returned and the callers refuse. The docstring's promise that it degrades gracefully is deleted along with the behaviour. (b) Two independent rules — an addend amount must be **positive**, and a counter whose value is zero may not carry the composite class at all, because a zero is not a sum of evidenced activity. |
| F-10 | Major, blocking | The state bindings added for the previous round were semantically wrong. `formal_v2_evaluation_access.{sealed_input_semantic_reads, sealed_label_semantic_reads, labels_opened_for_scoring}` and `parser_execution.comparator_predictions_generated` were all bound to `retired_v1_state.formal_evaluation_ever_run` — a flag recording the history of **`parser-v3-v1`**. A counter about the successor set was checked against a fact about the retired set, so the binding could hold while the fact it guaranteed had changed. The class `evidence` text also still called itself "machine evidence in the sense the ledger requires". | Each counter is bound to the block describing the same object: the three access counters and the comparator counter to `successor_set_state` (`exists: false`, `formal_evaluation_ordinal: 0`); the retired-v1 counter stays on `retired_v1_state`. The binding table now carries a block name per entry rather than assuming one block. The "machine evidence" sentence is struck and replaced with what the class is: a record assertion whose warrant is the absence of the artifacts an authorised round would have produced. |
| F-11 | Major | `assert_execution_is_platform_attested` claimed the execution was one "the platform agrees happened" and read from "Azure's own execution list". It reads committed JSON that an operator transcribed from an `az` command. Nothing signs it; an operator who can edit the receipt can edit it in the same commit. | Renamed in description rather than in name: the docstring and the constant comment now state the property as *agreement with an unsigned committed transcript*, whose value is independence of authorship — two consistent forgeries instead of one — and explicitly not attestation. "Genuine attestation would require a signed platform artifact, which this round did not obtain and does not claim." |
| F-12 | Major | The eight `NOT_ASSESSABLE` reasons rested on the silence of "the execution inventory this assessor reads". That inventory lists runs of the access-gate job and would never contain a review backend, so its silence supported nothing. Meanwhile the file that *does* carry backend facts is not silent: it lists a candidate endpoint and reports it non-qualifying. The schema said, unconditionally, that the review design "does not exist". | The reason cites the review-boundary evidence bundle, describes the candidate as listed-and-non-qualifying rather than absent, and discloses that the bundle is an unsigned operator transcript of read-only control-plane queries. The schema description is scoped to the assessed inputs. |
| F-13 | Minor | The comment on `BYTE_ONLY_VERIFICATIONS_AFTER_R1_GATE` described it as a floor a later round could exceed without moving the constant; the rule reading it pins the counter to it exactly. The two could not both be true. | The equality is the rule and the comment was wrong. The comment now says a later authorised round must raise the constant in the same reviewed commit that raises the counter, and notes that the separate `>= 14` requirement still owns the downward direction. |
| F-14 | Minor, non-blocking for this ledger | `assert_monotonic_succession` compared counters and events and nothing else, so a successor could keep every value and every event while moving a counter from a weak provenance class to a strong one. The number would not change; the reader's warrant for it would, upward, unrecorded. Audit F noted no successor exists yet and required this closed before any round relies on succession. | Provenance is immutable across succession unless the successor **appends an event naming the counter and both classes** — the same append-only discipline the event log already applies to access. Losing a classification entirely is refused outright. |
| F-15 | Minor | Seven of the eight §7.6 disposition rows overstated their fixes; §3 of this report still claimed a run reaching the wrong container could not have reproduced the aggregate digest; and L-40 contradicted itself, saying the counterexamples came "with working counterexamples rather than by reading" two paragraphs before saying static reading sufficed. | §7.6 is rewritten above with corrected dispositions and forward pointers. §3's wrong-container claim is withdrawn: the aggregate is a function of the bytes, and a byte-identical copy elsewhere yields the identical digest. L-40 states once that both methods were used. |

### 7.10 What no audit has reviewed

Audit D did not complete. Its process was lost before it reported, and no
finding is attributed to it.

More importantly, the remediation in §7.7 and §7.9 — this section included — is
material that no independent review has seen. That is the structure `L-38` and
`L-40` describe, and it is not closed. Each round of remediation creates a new
unreviewed state, and the fact that four consecutive independent reviews found
further defects in states that had already been remediated — eighteen, then
twelve, then eight, then twelve again across both auditors — is direct evidence
that the pattern does not converge on its own. Three times the defect was
introduced *by the remediation itself*. E-20 and F-08 are the sharpest
instances, and they are the same defect reached by different routes: E-20 found
a complete recursive enumerator written in this repository and then not used by
the check standing next to it; F-08 found a check that constrained a function
definition while the entrypoint called a different function entirely. Both are
"a check bound to something other than what runs", which is now the single most
recurrent finding of this phase. Self-authored tests are not independent
validation, and an audit that reviewed the previous commit is not a review of
this one.

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

The support for the zeros themselves is source analysis, in two parts.
`assert_no_write_calls_in_first_party_source` walks every first-party file that
executes inside the job — the probe *and* the receipt validator, after Audit C
(C-14) found the check reading only the first while claiming both — and fails if
a decode, persist, data-plane write or parser call site is present anywhere in
it. `assert_byte_handling_is_digest_only` then applies a *whitelist* to the one
function that touches object bytes: inside `stream_object_digest`, the only
calls permitted are `sha256`, `update`, `len` and `hexdigest`, and f-strings,
comprehensions, subscripts and `await`/`yield` over the chunk are refused.

The whitelist replaced the obvious fix, which was tried and rejected. Adding
`str`, `split`, `loads` and `splitlines` to the module-wide denylist broke the
probe, because `read_expected_members` legitimately calls `.splitlines()` and
`json.loads()` — on the *public committed* member list, not on object bytes. The
frozen rule is not "these names appear nowhere"; it is "object bytes reach a
hash and nothing else", which is a property of one function and had to be
checked there. A renamed or absent handler is a refusal
(`BYTE_HANDLER_NOT_FOUND`), so the check cannot silently guard nothing.

Both are properties of the code, established by reading it. Neither observes the
running process, and neither establishes that the source analysed on disk is the
source that executed; the image payload manifest and the digest-pinned image are
what connect the two, and they are pinned rather than proven.

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
