# Phase 1.2H protocol — Independent `parser-v3-v2` set repair, construction and create-only sealing

Status: `REGISTERED / UNEXECUTED`
Phase: 1.2H
Supersedes: nothing. Extends `docs/phase1_2g_conformance_policy_protocol.md`.
Baseline: `origin/main` at `0480f4f`
Private data accessed: none
Parser invocations: 0
Predictions generated: 0
Sets constructed: 0
Sets sealed: 0
Azure resource creations or changes: 0

---

## 0. What this document is, and what it is not

This document registers the **public, case-free** part of the Phase 1.2H design
before any private access, exactly as the round required. It is *not* a record
that the round was carried out.

Phase 1.2H **did not execute**. It terminated
`BLOCKED_ON_PRIVATE_SOURCE_ACCESS` at the first hard precondition: the
authoritative retired `parser-v3-v1` sealed source is unreachable from the
environment the round ran in. The blocking analysis is in
`reports/phase1_2h_blocked_set_repair.md`. The machine-readable state is in
`docs/phase1_2h_execution_access_ledger.json`.

Everything below §4 is therefore a **prospective design**. No step in it has
been performed, no artifact it describes exists, and nothing in it may be cited
as evidence that a successor set was repaired, constructed, reviewed or sealed.

### 0.1 What was deliberately *not* frozen, and why

The authorization contemplated freezing a full protocol suite before private
access: an import protocol, blind-review schemas, replacement-curation rules and
a seal-object layout.

Only the parts that are **independently derivable and load-bearing for the
blocking decision** were registered here. The rest was deliberately left
unwritten. The reason is a pattern this repository's audits have now caught
three separate times: an unexercised instrument, frozen into the permanent
record with the vocabulary of a completed procedure, is later read as evidence
that the procedure happened. A review schema that no reviewer ever filled in, a
seal layout that no seal ever used, and an admission rule that no case was ever
tested against are not preregistration — they are unearned specificity.

The honest boundary is: register the **preconditions and prohibitions**, which
are testable now and constrain any future round; do not register the
**mechanisms**, which cannot be validated without the access that was denied.
A later authorized round that obtains access must write those mechanisms then,
against the real material, and must not inherit an unvalidated skeleton from
here.

## 1. Scope

Phase 1.2H, had it proceeded, would have covered:

* read-only custodial access to the retired `parser-v3-v1` sealed inputs and
  labels, for repair purposes only;
* one-way import of eligible material under a **new** `parser-v3-v2` identity;
* the deterministic `N1`–`N6` representational normalizations already
  implemented and tested in `src/jspace_observation/parser_v3_repair_normalization.py`;
* blind semantic review of migrated cases by mutually isolated reviewers, with
  an arbiter for disagreements;
* curation of replacements for cases that cannot be repaired;
* construction of exactly one 120-case, 12-stratum set;
* pre-seal audits;
* **create-only** sealing to a new namespace.

It would **not** have covered preregistration, evaluation-image construction,
Stage P, Stage E, or any parser execution. Those remain separately authorized.

## 2. Hard preconditions

Each of these is a **gate**, not a guideline. A round that cannot satisfy one
must terminate in the corresponding blocked state rather than substitute an
approximation.

### P1 — Authenticated read-only access to the authoritative sealed source

The retired `parser-v3-v1` sealed objects are the only authoritative statement
of what the set contains. Repair must read *those bytes*, through the
registered read-only boundary, with the access recorded.

**A local copy is not a substitute.** A local file that matches the committed
public manifest demonstrates agreement with a Git record; it does not
demonstrate agreement with the sealed source, and the sealed source is what the
set's identity is defined against. If the source cannot be authenticated or
read, the correct outcome is `BLOCKED_ON_PRIVATE_SOURCE_ACCESS`.

**This precondition failed.** See §4.

### P2 — Reviewer isolation

Blind review is only blind if the reviewers cannot observe each other's output,
the arbiter's reasoning, or the curator's intent. Isolation must be a property
of the execution environment, not an instruction given to a cooperative agent.

A review performed by agents that share a context, a transcript or a filesystem
is not independent, whatever the prompt says. If isolation cannot be
established, the correct outcome is `BLOCKED_ON_INDEPENDENCE`.

### P3 — Private material must not leave the boundary that protects it

The registered read boundary for the sealed namespace is a managed identity
exercised from inside a virtual network, with container-scoped conditions. That
configuration is a deliberate statement that the content does not leave that
network.

Any design in which private content is read inside the boundary and then
transported to a reviewer outside it defeats the boundary. That includes
transporting it to a reviewing agent, however the agent is described.

### P4 — New identity, no in-place mutation

The successor set is a **new** set. `parser-v3-v1` bytes, namespace, manifests
and historical invalid contract are immutable. Migration is one-way: v1 → v2,
never the reverse, and never an edit to v1.

### P5 — Create-only sealing

Sealing may create objects and may never overwrite or delete one. A seal that
can overwrite cannot support the claim that the set was fixed before it was
evaluated.

### P6 — `sealed_object_count` requires an observation

Under limitation `L-32`, a sealed member list and a `sealed_object_count` are
facts about the sealed namespace at seal time. They require an **authenticated
seal-time listing witness**. An operator assertion, a construction-side tally,
or an offline computation must never be recorded as if it were the observation.

Where no seal occurred, the quantity is `null` — undefined — and not `0`.

## 3. Prohibitions in force for the whole phase

Phase 1.2H authorises none of the following, and the committed ledger enforces
each as a zero counter:

* running parser v3, parser v2 or the legacy parser on any private, locked or
  evaluation corpus;
* generating any prediction, candidate or comparator;
* opening any label for scoring;
* preregistering the successor set;
* running a formal evaluation;
* modifying `parser-v3-v1` in any respect;
* asserting that parser v3 is validated, improved, non-regressive, accepted, or
  fit for scientific scoring.

No J-space, hidden-reasoning, invisible-CoT or internal-workspace conclusion
follows from anything in this phase.

## 4. Execution record — precondition P1 failed

The round resolved the registered authoritative source from committed evidence
and probed its reachability at the control plane and at container-metadata
level only. It did not list the sealed set prefix and did not request any
object.

The storage account that holds the retired sealed set reports
`publicNetworkAccess = Disabled`, and the data plane refused the request under
its network rules. The registered read path is a user-assigned managed identity
exercised from in-network compute; a managed identity is not obtainable from the
workstation the round executed on.

Standing up in-network compute was considered and rejected, for two reasons:

1. The blind semantic review required by P2 executes as reviewing agents outside
   that network. Reading private content inside the boundary in order to ship it
   out to those reviewers violates P3 — it would defeat precisely the isolation
   the network rules encode.
2. It would require authoring and running new executable infrastructure and
   making irreversible role-assignment and blob writes, which this round is not
   authorized to do and which the authorization independently treats as
   grounds for a blocked termination.

Terminating at the earliest honest point was therefore correct.

Two **byte-only integrity verifications** were performed on local curator copies:
each file was streamed to a SHA-256 digest and the bytes discarded. No record
was decoded, parsed, printed or retained. Both matched the committed public
manifest on digest and byte count. This is recorded as a distinct counter from
a semantic read, because only a semantic read changes what has been seen.

Because no semantic read occurred, the state transition to `REPAIR_ACCESSED`
did **not** happen. `parser-v3-v1` therefore remains

> `SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`

unqualified and unchanged.

## 5. Exact next gate

A **separately authorized** round whose sole objective is to establish
authenticated, read-only, in-network access to the retired sealed source under a
boundary that also satisfies P2 and P3 — that is, one in which semantic review
occurs *inside* the boundary or the material is never transported out of it.

That round is not preregistration, not evaluation, not set construction and not
sealing. Until it succeeds, Phase 1.2H cannot proceed past P1.

## 6. What this document does not establish

* It does not establish that a `parser-v3-v2` set exists. None does.
* It does not establish that any case was migrated, reviewed, replaced or
  admitted. None was.
* It does not establish that parser v3 has been validated. It has not.
* It does not establish that the review or sealing mechanisms it declines to
  specify have been designed, only that they were deliberately left for a round
  that can validate them.
