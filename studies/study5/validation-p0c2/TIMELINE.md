# Study 5-P-0c-2 — the one permitted rebuild

P-0c built an object and it did not establish: accuracy 0.7562 against a floor of
0.80. That determination **stands, unwithdrawn and unreinterpreted**, and is
cited rather than revised.

This phase rebuilt the object once — the only rebuild permitted — and the object
**established**.

EQ1, EQ2, P-0, P-0′ and P-0c are all byte-identical.

---

## Why 0.80 did not move

The rationale I registered for the floor was weak, and that is recorded as a
defect in my own registration rather than smoothed over: the units floor of 60
already measures directly how many units carry known ground truth, so the two
gates are partly redundant and a proxy was able to veto a direct metric.
Recording a defect in one's own registration is not a licence to act on it after
seeing the result it produced.

The reason the **data** supplied is stronger than the one I wrote:

> The real work the 0.80 floor does is to bound the selection bias that
> correct-both filtering introduces. Accuracy at position 0 was 1.000 and at
> position 3 was 0.565; once correct-both filtering is applied the surviving
> subset is systematically biased toward earlier positions, and **source-line
> position is the only free confound in this design that the BRIDGE
> equal-length identity does not eliminate.** An accuracy of 0.7562 means
> roughly 43 percent of pairs would be filtered out, and filtered out very
> unevenly.

Direction disclosure: arguing the floor is redundant pushes toward *"we may
continue"*, which is the direction of p-hacking. Not taken. The floor was held at
0.80 here too.

---

## Why a rebuild was admissible

> The line between admissible and inadmissible is not **whether** the object is
> rebuilt, but **what quantity it is tuned toward**. Tuning until the *patching
> results* improve is tuning toward the hypothesis. Tuning until *the model can
> reliably perform the task* is admissible: clean accuracy is causally upstream,
> independently measured, and unrelated to any patching result — the same reason
> the correct-only inclusion rule is legitimate. And a positive control is
> supposed to be easy. Making the control tractable is not the same as making
> the hypothesis look good.

Condition 2 held throughout and is on the record: **0 candidate estimands
evaluated, 0 patching runs performed** at the moment the object was rebuilt. No
patching data existed to be consulted.

---

## The compensating tightening

Fewer distractors make retrieval easier, and "the task becomes retrievable" is
precisely what requirement 3 exists to prevent. So the rebuild was paid for:

| threshold | was | now | direction |
|---|---|---|---|
| requirement 3 drop floor | > 0.50 | **≥ 0.640625** | **tightened** |
| ablation ceiling | 0.1611 | 0.1611 | unchanged |
| accuracy floor | 0.80 | 0.80 | unchanged |

0.640625 is the value P-0c actually measured, so the successor had to be **at
least as anti-retrievable as the object it replaced**.

---

## The object

One substantive change: registration lines **6 → 4**, the direct response to
P-0c's diagnostic that 78 of 78 errors were hop-1 retrieval errors. One control
added: positions balanced by cycling every **ordered** pair of distinct
positions, which balances coverage *and* the donor/recipient roles by
construction rather than in expectation.

All seven requirements re-proven from scratch **by measurement**, because
changing the line count perturbs the token geometry that requirements 2, 6 and 7
depend on:

| | |
|---|---|
| pairs built | **160 of 160**, 0 rejected |
| requirement 2 vocabulary overlap | `[]` |
| requirement 7 violations | **0** |
| sites | PREFIX 63.19, CUE 2.00, BRIDGE **52.00**, READOUT 1 |
| build seed | unchanged from P-0c |

The in-context alignment constraint moved from pair-selection time to the name
pool, so requirement 6 is satisfied by construction with no silent rejection —
the defect P-0c found, fixed at its root.

---

## The object establishes

| requirement | observed | threshold | |
|---|---|---|---|
| 4 accuracy | **0.8406** | ≥ 0.80 | PASS |
| 3 ablated accuracy | **0.1062** | ≤ 0.1611 (chance 0.1111) | PASS |
| 3 drop | **0.7344** | ≥ 0.640625 | PASS |
| 5 correct-both units | **112** | ≥ 60 | PASS |

Ablated accuracy came out slightly **below** chance and the drop cleared the
tightened floor by 0.094. Requirement 2 also holds behaviourally: top-1 was the
intermediate letter in **0 of 320** items.

Determination **`OBJECT_ESTABLISHED`**, in the wording fixed before any forward
pass — a wording which states in its own text that a constructed object is a
**selection set** and that success on it is not success on real items.

---

## The mandatory per-position report

This exists so the selection bias cannot return unnoticed.

| position | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| accuracy, all items | 0.9878 | 0.7750 | 0.7342 | 0.8608 |
| share before filtering | 0.2562 | 0.2500 | 0.2469 | 0.2469 |
| share after filtering | 0.2500 | 0.2411 | 0.2366 | 0.2723 |
| change | −0.0062 | −0.0089 | −0.0103 | **+0.0254** |

**Worst absolute share shift: 0.0254.** The position control worked. P-0c drew
positions freely and spanned 1.000 to 0.565; here correct-both filtering moves no
position's share by more than 2.5 percentage points, so the one free confound is
controlled rather than averaged over.

---

## The OD-022 sweep — all four candidates, including the eliminated

Clean runs only, no GPU, no patched data, and **two** destruction constructions
because *destroyed* is not one thing.

| candidate | flatten mean | resample mean | |
|---|---|---|---|
| C1 null-subtracted | +0.000000 | **−0.002085** | **SURVIVES** |
| C2 matched-control | −0.299562 | −0.256238 | eliminated |
| C3 rank | +1.054350 | −0.288368 | eliminated |
| C4 two-sided margin | +0.538043 | +0.558693 | eliminated |

**One survivor.** Each elimination happened in the way its own pre-declared risk
anticipated: C2's matching is imperfect and leaves the term it was meant to
remove; C3's rank behaves badly when flattening collapses order; C4's
multiplicative cancellation fails because destruction is not multiplicative.

**An honesty note that must travel with C1:** its flatten column is exactly zero
because in that construction the minuend and the subtrahend are the same
deterministic function, so the subtraction cancels *by identity*. That is a
limitation of the sweep, not a strength of C1. The resample column is the
informative one — mean −0.002085 with a 95% interval of [−0.737, +0.761] and
0.5053 of draws at or below zero. Unbiased and high-variance, which is exactly
the risk the shortlist recorded for it in advance.

Shortlist closed: **0 added, 0 repaired**. The sweep tool *refuses to run* if its
implemented candidates differ from the shortlist.

---

## Numerical precision, re-proven rather than assumed

| family | bfloat16, 160 units |
|---|---|
| `EMBED_NOOP` | **0.000e+00** |
| `PREFIX_DONOR` | **0.000e+00** |
| `SELF_PATCH` | **0.000e+00** |
| worst single unit | **0.000e+00** |

Bit-exact, not merely within tolerance. Baseline shift against a batch-of-one
forward: 0.110937 logits — the bf16 hazard is present in this object too, and the
three-part repair neutralises it.

---

## Gates

**OD-017, extended by OD-021: 23 entries, 0 divergences.** Six audit the rebuild
specifically, because a rebuild is exactly where a threshold quietly moves: that
the accuracy floor did not move, that the drop floor moved only in the tightening
direction, that the ablation ceiling held, that one rebuild is permitted, that
the predecessor determination is preserved, and that no patching data existed
while the object was adjusted.

**Guard PASS.** `T` untouched, sealed lenses unread, zero imports of the
instrument under test.

---

## Writing limitations carried forward

**hop 2 never fails** — recorded, not adjudicated, entering no gate:

> A behaviourally correct composition is **not** an internal intermediate
> representation. It must not be written as "the intermediate is computed", nor
> as "the intermediate is used", nor as anything else implying an internal
> representation.

**hop-1 retrieval** is not taken up as a study and is not a finding of this
project. The third reason it was declined is worth keeping: *after consecutive
negatives, turning toward the one object that produced a clean signal.* Its
prettiness is exactly the danger.

**The constructed object is a selection set.** Success on it is not success on
real items.

---

## Accounting

| quantity | value |
|---|---|
| actively used GPU-hours, this phase | 0.318611 |
| cumulative | 39.96134 |
| ceiling | none applies |
| gates reduced to save time or hours | **0** |

Azure: 0 reconfigurations, 0 power-state changes, 0 NSG rules, 0 containers, 0
blobs. All four `TRAINING` machines running, idle and untouched.

**P-0c-2 builds and validates an instrument. No state it can reach is a
scientific result.**
