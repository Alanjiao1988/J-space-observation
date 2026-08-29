# Study 5-P-0′ — successor to P-0, halted twice before any effect measurement

P-0 closed `UNINTERPRETABLE`. This phase was to repair the batch baseline,
replace the estimand, and re-measure. It got the first done and was stopped on
the second, and would have been stopped independently by a third thing nobody
had counted.

EQ1, EQ2 and P-0 are all byte-identical. EQ2 is annotated by a **new file** only.

---

## What was ordered, and what was found

The directive ordered the estimand replaced with a logit-difference recovery
ratio,

```
effect = (L_patch − L_clean) / (L_full − L_clean)
```

on the reasoning that a purely destructive patch depresses both answer tokens by
roughly equal amounts, leaving the difference — and therefore the effect — at
zero.

Before writing a line of the pre-registration, that formula was compared against
what P-0 actually implemented:

| prescribed | P-0's code |
|---|---|
| `L_clean` | `ld_recipient` |
| `L_patch` | `gap` |
| `L_full` | `ld_donor` |
| `(L_patch − L_clean)/(L_full − L_clean)` | `(gap − ld_recipient)/denominator` |

**They are the same formula.** 200,000 random draws of the six underlying
logits give a worst absolute difference of `0.0`. Later, on the committed data,
177,944 stored values round-trip with a worst discrepancy of `0.0`.

The premise does not hold either, and the reason is structural rather than a
matter of precision. In its own clean run the recipient **prefers its own
answer**, so `logit(a_R)` starts high and `logit(a_D)` starts low. A patch that
destroys the state moves the output toward something uninformative about which
token is which, which drags the high one down far more than the low one.
Substituting the expected gap of a destroyed state, `L_patch = 0`:

```
effect = −L_clean / (L_full − L_clean)
```

strictly positive whenever each clean run prefers its own answer. Swept over
20,000 plausible clean-run pairs, using no P-0 data at all: min `0.0635`, mean
`0.4997`, max `0.9352`, **fraction at or below zero `0.0000`**. P-0's measured
random-donor null at BRIDGE was `0.4139`, which is where the closed form says it
should sit.

---

## The four synthetic cases

Run against the prescribed estimand, on a constructed world seeded from a
registered constant, with no threshold taken from P-0's data, and **before any
GPU work**:

| case | must return | returned | |
|---|---|---|---|
| 1 no-op | exactly 0 | `0.000e+00` | PASS |
| **2 random vector** | **≈ 0** | **`0.515487`** | **FAIL** |
| 3 full donor run | 1 | dev `0.000e+00` | PASS |
| 4 carries the intermediate | positive | lcb `0.600` | PASS |

Case 2 is the case the replacement existed to fix, and it is the case that
fails. "Approximately zero" was formalised as *the 95 % interval contains zero at
every layer*, not as a numeric tolerance — a tolerance chosen after the failure
it is meant to judge is not evidence.

That is stop condition 1. Making the estimand work would require a **second**
revision, which is stop condition 5. **Zero estimands were proposed by the
agent**: one chosen after seeing which one failed would be the agent selecting
the instrument that decides the question.

---

## The batch baseline — resolved, not halted

The first repair attempt **failed, instructively, at `0.5543`**. It moved the
baseline into the batch but still captured the **cache** at width 1, so
batch-1-derived states were written into a batch-48 run — the original
inconsistency one level down. That attempt is committed as
`out/baseline_first_attempt_INCOMPLETE_REPAIR.json` rather than discarded.

The repair needs three parts:

1. the baseline is an in-batch self-patch job;
2. the cache is captured at the consuming run's width;
3. every chunk is padded to full width, so no short final chunk runs a
   differently-shaped kernel.

With all three, over all **190 units**:

| family | worst \|mean\| normalised | worst single unit |
|---|---|---|
| `EMBED_NOOP` | `0.000e+00` | `0.000e+00` |
| `PREFIX_DONOR` | `0.000e+00` | `0.000e+00` |
| `SELF_PATCH` | `0.000e+00` | `0.000e+00` |

Not *within* the `1e-4` tolerance — **bit-exact**, and reproduced in `float32`
as well as `bfloat16`. Stop condition 2 is **not** triggered.

Root cause confirmed by running both dtypes: the baseline shift against a
batch-of-one forward is **0.476 logits in bfloat16** and **0.000017 in float32**.
Batch-size-dependent reduction order, exactly as P-0 diagnosed.

A units error in the verification tool was caught and fixed on the way: it
compared **raw logit** deviations against a tolerance registered on the
**normalised** scale. That is precisely the shape of defect OD-017 exists to
catch. It was caught before any verdict was recorded, and the tool now computes
both scales and decides on the registered one.

---

## The halt nobody had counted

Under the registered inclusion rule — the model's top-1 equals the item's own
target, in the **clean** runs, on **both** sides of a pair:

| | |
|---|---|
| units measured in P-0 | 184 |
| **correct on both sides** | **18 units, 9 clusters (9.78 %)** |
| after the 1.0-logit denominator floor | 18 units |
| registered floor | **30** |

Below the floor. The directive pre-decided the consequence — report and move to
P-0c — and stated it does not require further consultation.

The count was computed **only after** its rule was pushed. The directive asked
for a disclosure about whether the pair count was known when the floor was set:
it was not. P-0 published donor and recipient accuracy as separate marginals,
`0.3261` each; the joint had never been computed, and it was deliberately left
uncomputed until the registration was in. 9.78 % against 10.63 % under
independence, so being right on one item of a pair barely predicts being right on
the other.

**This halt is independent of the estimand.** It would have ended the phase even
if the estimand had been sound.

---

## Governance

**OD-011 revised, in force.** A non-vacuity demonstration must from now on
include a case that **must return positive**. Three must-return-negative cases
are passed by a rule that always returns the negative. The original text is
preserved and not weakened. The hole was found by reasoning rather than by data,
which is the mirror image of OD-017: that rule exists because a flattering
divergence would never surface, this one because a rule that can only fail in one
direction cannot be shown to work by tests that only probe that direction. The
revision reopens nothing.

**OD-017: 18 entries, 1 divergence** — and the divergence is expected and
load-bearing. Entry `0.estimand_is_a_replacement` compares the *prescribed*
estimand against the one P-0 implemented and reports that they are the same. An
audit that only ever compared each tool to its own registration could not have
noticed that a prescribed replacement was not one.

**Guard PASS.** `T` untouched, sealed lenses unread, zero imports of the
instrument under test, EQ1 / EQ2 / P-0 artifacts unmodified.

**EQ2 addendum**, `eq2_addendum_item_accuracy.md`, a new file: EQ2's 8.46 % peak
read-rate was computed on a sample this model answers about one time in three.
It tightens the fourth explanation quantitatively. It does **not** establish that
the items are invalid — accuracy is not computation, which is why P-0 was built
on patching in the first place — and EQ2's `NEGATIVE` stands untouched.

---

## Accounting

| quantity | value |
|---|---|
| actively used GPU-hours, this phase | **0.341667** |
| cumulative | **39.513562** |
| ceiling | none applies; the route ceiling was lifted |
| gates reduced to save time or hours | **0** |

Azure: 0 reconfigurations, 0 power-state changes, 0 resizes, 0 reboots, 0 NSG
rules, 0 containers created, 0 blobs written, 0 SAS tokens, 0 storage keys. All
four `TRAINING` `Standard_NC24s_v3` machines stayed running, idle and untouched.
No cost action proposed, performed or discussed.

---

## State

`STUDY5_P0PRIME_HALTED_ESTIMAND_HELD_AND_N_FLOOR_NOT_MET`, under `HB-005`.

Two things are reserved for the operator: **which estimand**, given that a
logit-difference recovery ratio is what P-0 already used, and whether to go
straight to **P-0c**, which `n = 18` says the phase ends at regardless.

**P-0′ is item-validity verification. No state it can reach is a scientific
result, and this state is a halt rather than a determination.**
