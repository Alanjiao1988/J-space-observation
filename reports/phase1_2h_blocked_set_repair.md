# Phase 1.2H — Blocked `parser-v3-v2` set-repair round

Terminal status: **`BLOCKED_ON_PRIVATE_SOURCE_ACCESS`**
Phase: 1.2H
Baseline: `origin/main` at `0480f4f`
Protocol: `docs/phase1_2h_independent_set_repair_protocol.md`
Machine-readable state: `docs/phase1_2h_execution_access_ledger.json`
Audit record: `reports/phase1_2h_audit_findings.md`

---

## 1. Result in one paragraph

Phase 1.2H was authorized to repair, construct and create-only-seal a successor
`parser-v3-v2` evaluation set. It terminated at the first hard precondition. The
authoritative retired `parser-v3-v1` sealed source cannot be authenticated or
read from this environment under the required read-only boundary, and the
authorization is explicit that an unverified local copy must not be substituted
for it. **No private content was read. No set was constructed. No set was
sealed. No parser was run. No prediction was generated.** The round's products
are an honest blocking record, a machine-checked live access ledger, and the
closure of a disclosed audit gap inherited from Phase 1.2G.

## 2. Why the round blocked

### 2.1 The chain

1. The authoritative sealed source was resolved from committed evidence:
   storage account `stjspacefiles0709085305`, container `jspace-results`, prefix
   `phase1-evaluator-validation/parser-v3-v1/20260725T160340Z`, 12 objects,
   resource group `rg-jspace-observation-sea`.
2. Repair access requires reading **those bytes** through the registered
   read-only boundary.
3. The storage account reports `publicNetworkAccess = Disabled`. A
   container-metadata probe — deliberately *not* the set prefix — was refused:
   *"The request may be blocked by network rules of storage account."*
4. The registered read path is a user-assigned managed identity exercised from
   in-network compute, with container-scoped conditions. A managed identity
   cannot be obtained on a workstation outside that network.
5. The authorization states that an unverified local copy must not be used when
   the sealed source is unavailable.
6. Therefore: `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`.

### 2.2 Why the local copy does not rescue the round

Local curator copies of `locked_inputs.jsonl` (32,430 bytes) and
`locked_labels.jsonl` (109,411 bytes) were verified **byte-only** — streamed to
a SHA-256 digest, bytes discarded — and both match the committed public manifest
exactly on digest and byte count.

That is a real and useful fact, and it is **not sufficient**. It demonstrates
agreement between a local file and a Git record. It does not demonstrate
agreement with the sealed source, and the sealed source is what the set's
identity is defined against. Treating the two as interchangeable is exactly the
substitution the precondition forbids.

### 2.3 Why in-network compute was not stood up

It would have satisfied the network precondition and violated two others.

The blind semantic review the round requires executes as reviewing agents
*outside* that network. Reading private content inside the boundary in order to
transport it to those reviewers defeats the isolation the network rules encode —
the boundary would be satisfied in form and broken in substance. Separately, it
would require authoring and running new executable infrastructure and making
irreversible role-assignment and blob writes, which this round is not authorized
to do.

Blocking at the earliest honest point was the correct outcome, not a fallback.

## 3. Private-access ledger

Every figure below is enforced by
`src/jspace_observation/parser_v3_v2_access_ledger.py` and tested in
`tests/test_parser_v3_v2_access_ledger.py`, not merely asserted here.

| Quantity | Count |
| --- | --- |
| Retired v1 sealed **inputs** semantically read | 0 |
| Retired v1 sealed **labels** semantically read | 0 |
| Private curator files read | 0 |
| Labels opened for scoring | 0 |
| Byte-only integrity verifications | 2 |
| `parser-v3-v2` cases constructed | 0 |
| `parser-v3-v2` cases reviewed | 0 |
| Replacement candidates generated | 0 |
| Sets sealed | 0 |
| Listing witnesses obtained | 0 |
| Final contracts compiled | 0 |
| Parser invocations | 0 |
| Candidate predictions generated | 0 |
| Comparator predictions generated | 0 |
| Preregistrations completed | 0 |
| Formal evaluations run | 0 |
| Azure control-plane reads | 6 |
| Azure data-plane **content** reads | 0 |
| Azure data-plane writes | 0 |
| Azure resource creations or changes | 0 |
| Azure job executions | 0 |

Two distinctions in that table are load-bearing and are enforced as separate
counters rather than collapsed into one flag:

* A **byte-only integrity verification** streams a file to a digest and discards
  the bytes. It is not a semantic content read. Only a semantic read changes
  what has been seen.
* An **Azure control-plane read** is a configuration or existence query. It is
  not a data access. Six configuration queries established that the data plane
  was unreachable; none of them read an object.

## 4. State of `parser-v3-v1`

> `SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`

**Unchanged, and unqualified.** Because no semantic read occurred, the
`REPAIR_ACCESSED` transition contemplated by the authorization did not happen.
`UNSPENT` therefore remains accurate without a caveat, and no sealed byte,
namespace, manifest or historical contract was touched.

## 5. State of `parser-v3-v2`

It does not exist. There is no set, no facts manifest, no contract, no sealed
prefix and no evaluation state chain. The only `parser-v3-v2` artifacts in the
repository are public, case-free policy documents.

`sealed_object_count` is recorded as `null`, **not** `0`. Under limitation
`L-32` a sealed member list and object count require an authenticated seal-time
observation. Nothing was sealed, so the quantity is undefined rather than
measured to be zero, and an offline assertion must not stand in for the
observation.

## 6. What the round did produce

Blocking at P1 did not make the round empty. Three things were completed.

### 6.1 The disclosed Audit E gap was closed

Phase 1.2G's own policy recorded, honestly, that the remediation of its final
audit had not itself been independently re-reviewed. Phase 1.2H commissioned
that re-review (**Audit F**). It found **all six** Audit E remediations
incomplete — 0 blockers, 5 majors — and supplied a working counterexample for
each. All six are now fixed and regression-pinned. Details in
`reports/phase1_2h_audit_findings.md`.

### 6.2 A live execution/access ledger

The `FINAL` Phase 1.2G policy carries an `execution_state` block. That block was
correct when written, and it must not become a live counter: the artifact that
states *how a future evaluation will be judged* should not also be the place
where *how many things have happened* is edited. This repository has already
been bitten by a semantic change smuggled in as a routine state update.

`docs/phase1_2h_execution_access_ledger.json` separates the two. It binds the
policy twice — by full-file SHA-256 and by a `policy_semantics_sha256` computed
over the policy with the five mutable `execution_state` counters projected out.
The second hash is the load-bearing one: it is stable across any future licensed
counter edit, so a change to a threshold, gate, ontology entry, population
figure, comparator role or status rule cannot hide behind one. Audit G found the
first version of this projection excluded the *whole* `execution_state` block,
which put its free-text `final_policy_is_not_a_result` statement outside the
hash; that statement is now inside it, and is separately constrained so it
cannot assert an evaluation, a validation or an acceptance.

The ledger is append-only and monotonic: counters may rise and never fall, and
recorded events may be appended and never rewritten or erased. Its validator
refuses a ledger whose counters contradict its declared status — a "sealed"
status with no seal write, or a "blocked on source access" status that
nonetheless records a semantic read. Following Audit G it also enforces closed
schemas for the top level, both state blocks and every event; reconciles each
narrated state field against the counter measuring the same thing; requires
every access event to be accounted for by a counter; rejects event kinds this
phase does not authorise; and validates both records before comparing them for
succession. `scripts/generate_current_state.py` validates the ledger before
rendering it, so a record the validator would reject cannot become a published
claim.

### 6.3 A registered, explicitly unexecuted protocol

`docs/phase1_2h_independent_set_repair_protocol.md` registers the public,
case-free preconditions and prohibitions. Its §0.1 states plainly what was
deliberately *not* frozen — the import mechanism, review schemas, replacement
rules and seal layout — and why: an unexercised instrument frozen into the
permanent record with the vocabulary of a completed procedure is later read as
evidence that the procedure happened. This repository's audits have caught that
pattern three times.

## 7. Artifact digests

| Artifact | SHA-256 (LF-normalised) |
| --- | --- |
| `docs/phase1_parser_v3_v2_evaluation_policy.json` | `fda448869aba01bf75e865f38a2e0f35485b83890f9088c50e05e661bfe3421c` |
| `docs/phase1_2h_execution_access_ledger.json` | `4f419c1c1ceacce6e6fc0154d54d5f77ad2cd36d1bef3b1b77e22c31e9fd48aa` |
| `docs/phase1_2h_independent_set_repair_protocol.md` | `58938558e5f1cf017afaffa7c09d2a978f8aa131a6ab892b27a15d5fd9c30bc3` |

The policy's previous digest was
`e8d4391387f4f6682d9a947f58a4586ce0c110c16c3f66e4250b134690eb9114`. Exactly one
block changed: `review_provenance`. Audits A and B were listed without finding
counts while C, D and E carried them, and the limitation asserted that the Audit
E remediation had not been re-reviewed — which Phase 1.2H made false by
re-reviewing it. No threshold, gate, population figure, ontology entry,
comparator role, status rule or `execution_state` value was touched.

The policy's *semantic* hash is
`ae375481be95ae9f91265c0a9e9ff88ebfa4203cfb518e19287873426138c8ee`. It differs
from any figure recorded before Audit G because the projection was narrowed, not
because the policy's semantics moved: the excluded set went from the whole
`execution_state` block to its five mutable counters. The policy's threshold,
gate, ontology, population, comparator and status blocks are byte-identical to
Phase 1.2G.

## 8. Exact next gate

A **separately authorized** round whose sole objective is to establish
authenticated, read-only, in-network access to the retired sealed source, under
a boundary in which semantic review also occurs inside the network or the
material is never transported out of it.

That round is **not** preregistration, **not** evaluation, **not** set
construction and **not** sealing.

## 9. What this document does not establish

* Parser v3 remains **unvalidated**. Nothing here bears on its accuracy.
* Phase 1.0C was executed and finalized `INCONCLUSIVE`. It is target-model
  task/headroom screening, not parser calibration, and no Phase 1.0C result can
  supply, bound, or unblock any parser acceptance threshold.
* No private holdout was accessed in Phase 1.2H.
* No formal evaluation has ever occurred; the formal evaluation ordinal remains
  `0`.
* No J-space, hidden-reasoning, invisible-CoT or internal-workspace conclusion
  follows from any part of this round.
