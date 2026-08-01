# Parser-v3-v2 stratum policy (v2)

**Artifact ID:** `phase1-parser-v3-v2-stratum-policy/v2`
**Status:** `FINAL` (design artifact; not an authorization to construct a set)
**Introduced:** Phase 1.2F
**Corrected:** Phase 1.2G — §5 gate-coverage table and consequence (see §5)
**Scope:** public, case-free, label-free

---

## 1. Why this artifact exists

The prospective evaluation policy for a future `parser-v3-v2` set previously
derived its population facts directly from:

```
evaluator_sets/parser_v3_v1/strata_definitions.md
```

Phase 1.2F found that binding a **future v2 policy** to the **retired v1
namespace** conflicts with three standing rules:

| Rule | Conflict |
| --- | --- |
| New-set identity rule | A new set must have its own identity. A v2 policy whose population facts are read out of the v1 namespace inherits v1 identity by reference. |
| Repair CLI namespace refusal | The repair tooling hard-refuses any path containing `parser_v3_v1`. A policy that names that path as its live source describes a binding the tooling would reject. |
| Re-derivation requirement | A reused design artifact must be re-derived and revalidated, not cited across a retirement boundary. |

This artifact resolves the conflict. It is a **new, public, versioned v2
artifact** that restates the stratum taxonomy under v2 identity, records an
explicit decision to retain it, and cites v1 only as historical ancestry.

### What this artifact is not

* It is **not** a set. It contains no case, no input text, no label, no
  membership list, and no manifest.
* It creates **no** sealed object and asserts **no** set-derived fact.
* It is **not** an authorization to construct, migrate, seal, or evaluate
  anything.

---

## 2. Provenance and ancestry

| Field | Value |
| --- | --- |
| Ancestry | `evaluator_sets/parser_v3_v1/strata_definitions.md` (retired) |
| Ancestry status | `SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE` |
| Relationship | design ancestry only; **not** a live binding |
| Re-derived in | Phase 1.2F |
| Derived from any prediction? | No |
| Derived from any sealed input or label? | No |
| Derived from any observed parser performance? | No |

The v1 file was read in Phase 1.2F **only** as a public design document, to
confirm that the taxonomy being carried forward is the taxonomy that was
originally registered. Its bytes are unchanged. Phase 1.2F added its
LF-normalised SHA-256 (`25d59eb0…`) to the protected-digest list in
`tests/test_parser_v3_repair.py`, so this citation is now mechanically
checkable; before Phase 1.2F the file was **not** on that list.

---

## 3. Independent decision: retain the 12-stratum taxonomy

Phase 1.2F evaluated whether the 12-stratum design should be retained,
modified, or replaced for v2.

**Decision: retain unchanged.**

Reasoning, stated independently of the v1 set's fate:

1. The v1 set was retired for an **ontology** defect — it admitted a fourth
   typed-decision class, `present_unextractable`, which the three-class formal
   ontology forbids. The retirement was not caused by any defect in the
   stratum taxonomy.
2. Each stratum encodes a distinct, nameable extraction failure mode. The
   taxonomy is a statement about how answer extraction can fail, not about any
   particular corpus.
3. Changing the taxonomy now, after some development results are known, would
   introduce exactly the post-hoc design freedom this project is trying to
   eliminate. Retaining it is the conservative choice.
4. The taxonomy is retained **with** the ontology correction applied:
   `present_unextractable` is not a formal class and no stratum may produce it
   in a formal set.

---

## 4. Registered composition

12 strata × 10 cases = **120 cases**.

| Stratum | Role | Cases | Registered presence | Class |
| --- | --- | --- | --- | --- |
| S01 | boxed single answer | 10 | `present` | clean |
| S02 | explicit final-answer marker | 10 | `present` | clean |
| S03 | terminal equation | 10 | `present` | clean |
| S04 | multiple intermediate numbers | 10 | `present` | critical |
| S05 | final answer followed by reasoning | 10 | `present` | critical |
| S06 | last-number trap | 10 | `present` | critical |
| S07 | truncated before answer | 10 | `no_answer` | critical |
| S08 | explicit no-answer / placeholder | 10 | `no_answer` | critical |
| S09 | malformed recoverable | 10 | `present` | critical |
| S10 | malformed unrecoverable | 10 | `no_answer` | critical |
| S11 | true multiple-candidate ambiguity | 10 | `ambiguous` | critical |
| S12 | numeric normalization | 10 | `present` | clean |

**Clean strata:** S01, S02, S03, S12 (40 cases)
**Critical strata:** S04–S11 (80 cases)

### Derived typed-decision support

Counted from the presence column above at 10 cases per stratum:

| Class | Strata | Support |
| --- | --- | --- |
| `present` | S01 S02 S03 S04 S05 S06 S09 S12 | 8 × 10 = **80** |
| `no_answer` | S07 S08 S10 | 3 × 10 = **30** |
| `ambiguous` | S11 | 1 × 10 = **10** |
| | | **120** |

These supports equal the parser-v2 supports only because both designs use the
same registered taxonomy. They were **not** copied from the parser-v2 gate
contract and were **not** derived from any prediction.

---

## 5. Gate coverage of the taxonomy

Recorded here because every acceptance-threshold disposition depends on it.

**Correction (Phase 1.2G).** The table and consequence below previously
recorded superseded coverage figures:

> S06 pinned; gate coverage 90 of 120 over a three-stratum residual.

That was already false when Phase 1.2F wrote it: the same round had recomputed
coverage from the registered per-gate error definitions and found S06
*unpinned*, and had recorded the corrected figures in the policy JSON. The
error was confined to this document. It is corrected below rather than
silently rewritten, and the superseded figures are named so that a reader who
saw them can recognise what changed.

| Stratum | Dedicated zero-error mandatory gate | Pins exact typed decision | Pinned by |
| --- | --- | --- | --- |
| S01 S02 S03 S12 | yes (collective) | yes | `G_clean_strata_exact` |
| S06 | yes | **no** | — |
| S07 | yes | yes | `G_S07_truncated_no_answer` |
| S08 | yes | yes | `G_S08_explicit_no_answer` |
| S10 | yes | yes | `G_S10_unrecoverable_no_answer` |
| S11 | yes | yes | `G_S11_ambiguity_detection` |
| **S04 S05 S06 S09** | S06 only | **no** | — |

**Why S06 has a zero-error gate but is not pinned.** `G_S06_last_number_trap`
carries exactly one registered error definition,
`registered_rightmost_distractor_span_selected`. It forbids selecting the
trailing distractor span and forbids nothing else. A parser can avoid that span
and still return a different wrong canonical value, or emit `no_answer`,
without violating the gate. Zero errors under that definition therefore does
not entail exact typed-decision agreement.

**Consequence.** Satisfying every mandatory gate implies at least **80 of 120**
exact typed decisions. The **residual strata** are exactly **S04, S05, S06,
S09** (40 cases), and they are the only population over which a non-vacuous
numeric acceptance criterion can be written.

**Superseded figures.** `90 of 120`; residual `S04, S05, S09`; residual case
count `30`. Do not cite them.

**Derivation authority.** These figures are not maintained by hand. They are
derived by
`jspace_observation.parser_v3_repair_contract.derive_gate_coverage`, which
`validate_policy` calls and which therefore runs before any contract can be
compiled. The policy JSON restates them and the validator rejects the policy if
the restatement disagrees. This document restates them a second time for a
human reader and is checked by
`scripts/check_current_state_consistency.py`.

---

## 6. Sampling frame

The set is a **fixed, quota-constructed adversarial challenge set**. It is
**not** an IID sample from any deployment population.

Prohibited interpretations:

* confidence intervals over a deployment population;
* generalisation of a measured rate to unseen inputs;
* any claim of the form "the parser is *X*% accurate in deployment".

A rate measured on this design estimates performance **on the quota design**.
Interval estimates that assume independent identically distributed sampling do
not apply.

---

## 7. Limitations preserved

* **L-32.** A future sealed member list and `sealed_object_count` require an
  authenticated seal-time observation. They are **not** facts an offline
  prospective policy can derive, and an operator assertion must never be
  recorded as a set-derived fact. Nothing in this artifact asserts either.
* This artifact describes a design. It does not assert that any set matching
  the design exists.

---

## 8. Change control

Any change to the composition table, the presence column, or the clean/critical
split changes the derived supports and therefore the gate denominators. Such a
change requires a new version of this artifact and a re-derivation of the
prospective evaluation policy. It must never be made to accommodate an observed
result.
