# EQ2 addendum — item accuracy on the multihop set

**This is an explanatory annotation. It is not a retraction.**

It follows the convention EQ1 used for the kurtosis-axis annotation: the finding
is recorded in a **new file**, and every EQ2 artifact is left byte-identical.
Nothing below withdraws EQ2's determination, reruns any part of it, relaxes any
threshold, or reopens any round.

| | |
|---|---|
| EQ2 determination | `NEGATIVE`, D-1 category `negative-A` |
| Status after this addendum | **unchanged** |
| EQ2 artifacts modified | **0** |
| EQ2 rounds reopened | **0** |
| Recorded | 2026-08-29, from P-0 measurements |

---

## The number

Measured on `Qwen2.5-7B-Instruct` — the model EQ2 used as its positive control —
over the 184 admissible ordered pairs P-0 measured, drawn from the same
`lens-eval-multihop.json` EQ2 scored:

| quantity | value |
|---|---|
| model's top-1 continuation equals the item's own target, donor side | **32.61 %** |
| same, recipient side | **32.61 %** |
| **correct on both sides of a pair** | **9.78 %** (18 of 184 units, 9 of 92 clusters) |

The joint figure is close to the product of the marginals (0.3261² = 10.63 %),
so within this frame the two sides are roughly independent — being right on one
item of a pair barely predicts being right on the other.

## Why it matters for reading EQ2

EQ2 never checked item accuracy. Its J-lens read-rate on this set peaked at
**8.46 %**, and the layer-21 residual was about **12 hits**. Those numbers were
computed over a sample in which **the model produces the item's own target
roughly one time in three**.

So the read-rate and the accuracy are of comparable magnitude, and the sample
EQ2 measured readability on is largely a sample the model does not answer.

## What this does and does not do

**It does** tighten, quantitatively, the fourth explanation of EQ2's negative —
that the items may not have obliged the model to compute an intermediate at all.
For roughly two thirds of these items, asking whether the intermediate was
computed is close to moot: the model does not produce the item's answer, so
there is little reason to expect it ran the chain the item describes.

**It does not** establish that the items are invalid. Accuracy is not
computation: a model can compute an intermediate and still miss the final hop,
and it can answer correctly by retrieval without computing anything. That is
precisely why P-0 was designed around causal patching rather than around
accuracy, and it is why this number is recorded as an annotation rather than as
a result.

**It does not** overturn `NEGATIVE`. EQ2's determination was about what its
registered rule returned on the profiles it measured, and that remains exactly
what it was. This addendum changes how a reader should *interpret* the negative,
not whether it stands.

**It does not** license any claim about `J`, the J-lens, the published lenses,
the paper, or `T`.

## Relation to what EQ2 already said about itself

EQ2's own closing addenda recorded that it never obtained a passing positive
control, and that *"the J-lens method does not hold"* and *"we did not drive the
lens as its authors intended"* were therefore indistinguishable within it. This
addendum adds a third member to that set which EQ2 could not have separated
either: **that the sample was largely one the model cannot do.**

## Consequence recorded elsewhere, not here

The same number is what halted P-0′: under a registered inclusion rule requiring
the model to be correct on both sides, only 18 units survive against a
pre-registered floor of 30. That is recorded in
`studies/study5/validation-p0-prime/` and is not a statement about EQ2.

---

*An explanatory annotation. It licenses no claim of any kind, and it is not a
scientific finding.*
