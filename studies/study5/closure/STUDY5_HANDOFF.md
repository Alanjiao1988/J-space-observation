# Study 5 — handoff assets

Companion to [`STUDY5_CLOSURE.md`](STUDY5_CLOSURE.md). This document **starts
nothing**. It lists what a successor inherits, and what it may not inherit as
licence.

---

## 1. An established object

A constructed two-hop task, `NAME → letter → digit`. The **answer** is the
digit; the **intermediate** is the letter.

| property | value | how known |
|---|---|---|
| pairs / items | 160 / 320, 0 rejected | built |
| intermediate ∩ answer token ids | `[]` | measured at build |
| requirement-7 violations | **0** | verified position by position |
| BRIDGE span | **52 tokens**, identical in both members | verified |
| accuracy | **0.8406** | clean runs |
| ablated accuracy | **0.1062** (chance 0.1111) | clean runs |
| drop | **0.7344** | clean runs |
| correct-both units | **112** | clean runs |
| worst position-share shift after filtering | **0.0254** | measured |
| top-1 was the intermediate letter | **0 of 320** | measured |

**Its establishment depends on no estimand.** Accuracy and the ablation probe
are clean-run properties, so nothing about the estimand search can invalidate
them — which is why this asset outlives the termination.

The limitation travels with it: **it is a selection set.** Success on it is not
success on real items.

---

## 2. A bit-exact patching harness

The three-part batch repair: an **in-batch self-patch baseline**, a **cache
captured at the consuming run's width**, and **chunks padded to full width**.

| no-op family | bfloat16 | float32 |
|---|---|---|
| `EMBED_NOOP` | `0.000e+00` | `0.000e+00` |
| `PREFIX_DONOR` | `0.000e+00` | `0.000e+00` |
| `SELF_PATCH` | `0.000e+00` | `0.000e+00` |

The hazard it neutralises, and the reason this matters beyond Study 5:

| precision | baseline shift |
|---|---|
| bfloat16 | **0.110937** logits |
| float32 | **0.000008** logits |

≈14,000×. The offset is the same order as the effects being measured, so **any
bf16 patching result at this effect scale that has not demonstrated bit-exact
no-ops is uninterpretable.** The harness was re-proven on each new object rather
than inherited; a successor should do the same.

---

## 3. An unused, unmodified measurement pre-registration

`validation-p0c2/measurement/MEASUREMENT_PREREGISTRATION.json`, sha256
`31070c20…b296`.

Pushed **before** any null or real patch existed, and never edited afterwards.
A successor therefore inherits a power gate and three conclusion wordings that
**no observed result could have shaped**:

- MDE pass-line **0.15**, power 0.80, α 0.05 two-sided;
- `CAUSALLY_USED` / `NOT_CAUSALLY_USED` / `UNDERPOWERED`, fixed verbatim;
- the decision rule, with its reason: *C1 significantly > 0*, **not** versus a
  null ceiling, since a null-subtracting estimand would otherwise deduct the
  null twice;
- three variance reductions registered in advance.

---

## 4. The governance stack

`OD-011 rev 2` · `OD-017` · `OD-021` · `OD-022`, plus the unnumbered
disciplines: the directionality rule, asymmetric-motivation disclosure, pushing
the rule before computing the number, committing failed repairs, and rendering
readable artifacts *from* the committed JSON so they cannot drift.

The complementarity learned here is worth carrying: **OD-022 tests behaviour at
high nuisance parameter, OD-011 rev 2 tests it at zero.** Neither suffices
alone — C1 passed the first and died at the second.

---

## 5. A post-hoc diagnosis — **not adopted, not a proposal**

> The four candidates' failures share one structure: **each tried to be immune
> to destruction through a fixed functional form, while the amount of
> destruction varies from patch to patch.** No fixed form can be invariant to a
> varying nuisance parameter.
>
> This also explains precisely why OD-022 and OD-011 rev 2 are complementary,
> and it generalises: **the sweep tests only at high nuisance parameter, rev 2
> tests at zero, and a fixed-form correction can at best match one end.** C1
> passed the former and died at the latter.
>
> The solution it points at is a **per-patch matched control** — same norm, same
> layer, same positions, contents shuffled — so the nuisance parameter is
> estimated at the *same value it takes under the real patch*. The matched
> control of a no-op is itself a no-op, so it returns zero naturally.
>
> **This diagnosis is post-hoc, is not adopted, and is not a proposal.** By the
> D-1 precedent it belongs to a new study requiring its own independent
> pre-registration, which is outside this authorisation.

The executing session deliberately declined to volunteer a new rule in its
report, on the grounds that proposing one immediately after an unfavourable
result would be acting on that result. That handling is preserved here.

It may **not** be written as a methodological contribution of this project, nor
as a validated solution.

---

## 6. What may not be inherited as licence

- that **J-space exists or does not exist** — this project supplies no evidence
  either way;
- that a **class** of estimand was refuted — what was exhausted is a **closed
  list of four**;
- that *"the question remains open"* is a conclusion of this project — the
  correct statement is that **this project failed to test it**;
- that any result on the constructed object transfers to real items;
- P-0's withheld verdict as a published conclusion;
- hop-1 retrieval decay as a finding;
- hop 2 never failing as evidence of an internal intermediate representation.

---

*A handoff note. It licenses no claim of any kind and starts nothing.*
