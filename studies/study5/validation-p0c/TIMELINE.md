# Study 5-P-0c — build the object first, choose the estimand after

P-0 closed `UNINTERPRETABLE`. P-0′ halted twice: the prescribed replacement
estimand was the one already in use, and only 18 of 184 pairs were correct on
both sides. P-0c was to remove both dependencies at once by **building** an
object whose intermediate is known by construction, instead of borrowing one and
hoping the model could do it.

It built the object. The object did not establish.

EQ1, EQ2, P-0 and P-0′ are byte-identical.

---

## Governance first, pushed before anything else

**OD-021, in force.** A criterion, estimand, threshold or inclusion rule
**issued by the adjudicator** must pass OD-017 conformance before it may enter a
pre-registration. The instruction does not exempt it from verification.

The precipitating event is on the record: the P-0′ directive prescribed
replacing the estimand, and the prescribed formula was algebraically the one
already in use. It surfaced only because OD-017 entry 0 compared the
*prescribed* form against the *implemented* one. A conformance regime that audits
only the executing party's code against the executing party's registration
cannot see a defect that entered through the instruction.

**OD-022, in force — the clean-run destruction sweep.** Before a candidate
estimand may be registered, its value under a purely destructive patch must be
computed from **clean runs alone** and its distribution and fraction at or below
zero reported. Not approximately zero means not registrable, and a failing
candidate is out rather than repaired.

The rule records what it has already done: it killed the whole difference-ratio
family with no GPU work, in closed form, and predicted the failure value in
advance — `−L_clean/(L_full−L_clean)`, swept mean 0.4997, fraction ≤ 0 **0.0000**,
against a synthetic case that then measured 0.515487 and a null that had measured
0.4139. It also kills the next obvious candidate before a round is spent on it:
the rise in the donor answer's own log-probability fails for the mirror reason,
since `a_D` is a low-probability token and destruction *flattens*, which lifts
low-probability tokens. **Two natural forms dead by the same mechanism**, so no
functional form is assumed safe before the sweep.

---

## The object

```
Rules: A=2 B=3 C=8 D=7 E=4 F=5 G=9 H=6
Violet is registered under letter B.
... five more registrations ...
Question: consider Violet.
... four fixed filler lines ...
The value registered to it is _
```

`NAME → letter → digit`. The **answer** is the digit; the **intermediate** is the
letter.

| requirement | how it is met | verified |
|---|---|---|
| 1 intermediate known | it *is* the build parameter | by construction |
| 2 never the emitted token | letters vs digits, token-id sets **disjoint** | overlap `[]` |
| 3 both hops real | table randomised per pair; ablation probe | see below |
| 4 model accurate | floor registered before measuring | **failed** |
| 5 enough pairs | counted only after the rule is pushed | not reached |
| 6 equal token length | names matched **in the question line** | 0 misaligned |
| 7 BRIDGE identical | fixed template after the name | **0 violations** |

Pairs are built *as* pairs — both members share the table, the registrations and
the filler and differ only in the queried name. That is what makes CUE one to
three tokens and BRIDGE a **52-token** span whose tokens are identical in both
members, so a patch there could carry nothing except what the model computed.

**160 of 160 pairs built, 0 rejected, 320 items.**

Two build defects were caught and fixed before any measurement, both the same
kind of fault — a property assumed rather than checked. Digits were assumed
single-token with a leading space, but Qwen splits `" 1"` into two tokens while
`"1"` is one; the tool now collects every single-token surface form, which is
what makes the disjointness check meaningful rather than decorative. And names
were filtered by their **bare** token length while the alignment constraint bites
**in context**, silently discarding 89 of 160 pairs; filtering where the
constraint applies took the yield to 160 of 160.

---

## The floors, registered before any measurement

Pushed in `5d157a2`, before a single forward pass:

| floor | value | provenance |
|---|---|---|
| accuracy | **0.80** | adjudicator's suggestion adopted unchanged; chance is 0.1111 |
| correct-both units | 60 | set by the executing party |
| ablation ceiling | 0.1611 | chance + 0.05 |
| required drop | > 0.50 | full minus ablated |

Disclosure the directive requires: the correct-both count was **not** known when
the floor of 60 was set, and was deliberately left uncomputed.

---

## What the measurement returned

**Requirement 3 — PASSED, and not narrowly.**

| | |
|---|---|
| ablated accuracy | **0.1156** |
| chance | 0.1111 |
| ceiling | 0.1611 |
| drop from full | **0.6406** (required > 0.50) |

Removing the **first** hop's input, while leaving the second hop's clue entirely
intact, drops the model to essentially exactly chance. The task cannot be
answered by retrieval; it genuinely requires composing two lookups. The two-hop
**structure** is demonstrated rather than argued.

Requirement 2 also holds *behaviourally*: the model's top-1 was the intermediate
letter in **0 of 320** items.

**Requirement 4 — FAILED.**

| | |
|---|---|
| accuracy | **0.7562** |
| floor | **0.80** |
| margin | −0.04375 |

Stop condition 1. Determination **`OBJECT_NOT_ESTABLISHED`**, in the wording
fixed before any data existed.

0.7562 against 0.80 is exactly the circumstance in which moving a threshold is
most tempting and least defensible. **The floor was not lowered and the object
was not rebuilt** — the pre-registration forbids both, and the second is the
first by another route.

---

## The diagnostic that cannot change the outcome

Motivation asymmetry disclosed: it would not have been written had the floor been
met. It is admissible because the determination is already committed and nothing
consumes its output.

| error kind | count | share |
|---|---|---|
| **hop-1: hop 2 applied correctly to the wrong letter** | **78** | **1.000** |
| digit not in this table | 0 | 0.000 |
| emitted a letter | 0 | 0.000 |
| not a digit at all | 0 | 0.000 |

**Hop 2 never fails.** The entire shortfall is hop 1 — retrieving the right
registration line — and it tracks that line's position in context:

| registration line position | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| accuracy | **1.000** | 0.792 | 0.655 | **0.565** | 0.721 | 0.813 |

An in-context lookup difficulty, not a reasoning failure. It authorises nothing:
not lowering the floor, and not rebuilding with fewer or reordered registration
lines.

---

## Gates

**OD-017, extended by OD-021: 18 entries, 0 divergences.** Three entries audit
values that were *handed down* rather than authored here, which is the direction
OD-021 exists to add.

The audit caught one thing on its first run — a divergence produced by its own
scan of the guard's source, which necessarily contains the target markers. It was
routed through the guard's registered self-exclusion, moving implementation
toward registered text.

**Guard PASS.** `T` untouched, sealed lenses unread, zero imports of the
instrument under test, all predecessor namespaces byte-identical.

---

## Accounting

| quantity | value |
|---|---|
| actively used GPU-hours, this phase | **0.129167** |
| cumulative | **39.642729** |
| ceiling | none applies |
| gates reduced to save time or hours | **0** |

Azure: 0 reconfigurations, 0 power-state changes, 0 NSG rules, 0 containers, 0
blobs. All four `TRAINING` machines running, idle and untouched.

---

## State

`STUDY5_P0C_HALTED_OBJECT_NOT_ESTABLISHED`, under `HB-006`. The estimand remains
**HELD**; the shortlist is declared and closed at four, and **zero candidates
were evaluated** because the phase halted before the object could serve as a
selection set.

What this phase did establish is narrow and worth stating exactly: **a two-hop
object of this shape can be constructed whose intermediate is known by build,
whose answer vocabulary is disjoint from it, and whose anti-retrieval property is
demonstrated at chance.** What it did not establish is that this model can do
that object reliably enough for it to serve as a known-positive selection set —
which is precisely what the accuracy floor was for.

**P-0c builds and validates an instrument. No state it can reach is a scientific
result, and nothing here is a claim about real items, the J-lens, the paper, or
`T`.**
