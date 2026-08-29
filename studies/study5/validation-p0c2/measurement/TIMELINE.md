# Study 5-P-0c-2 measurement — the last candidate falls before any measurement

The object established. The measurement phase registered its power first, as
ordered. Then the sole surviving estimand failed its own pipeline demonstration,
and the phase stopped **before the null-only run and before any real patch**.

EQ1, EQ2, P-0, P-0′, P-0c and the P-0c-2 object phase are byte-identical.

---

## Step 1 — power registered before it could be computed

Pushed at `6572f8e` with nothing run.

| | |
|---|---|
| MDE pass-line | **0.15** normalised restoration |
| power | 0.80 |
| alpha | 0.05, two-sided |

The number is mine. The adjudicator explicitly declined to issue it, because
OD-021 exists precisely *because* an intuition-issued value was the previous
failure. It derives from no variance, no measured effect and no earlier phase's
value. The null variance was unknown when it was written, so it could well have
failed — which is the point of setting it first.

> EQ2's "too weak to adjudicate" was painful because, after the fact, **no
> effect** and **no power** could not be told apart. Registering the MDE in
> advance closes that ambiguity.

**Three** outcomes were fixed verbatim, not two, and `UNDERPOWERED` was fenced on
both sides: terminal for the route, and forbidden from being written as *"the
question remains open"*, which would present a defect of the instrument as a
property of the world.

**Decision rule, one only:** *C1 significantly greater than zero* — **not** C1
versus a null ceiling. C1 already subtracts the null, so using both would deduct
it twice.

**Variance reduction registered in advance:** common random numbers (the largest
gain, since C1 is a difference), k 5 → 20, and cluster-level inference. On the
honest note there: each pair contributes exactly one ordered unit, so 112
clusters for 112 units and the conservative step is a **no-op here**. Applied and
stated anyway, because a step that happens not to bite must not be presented as a
tightening that did.

**n-expansion decided now**, keyed to the MDE, which is a null-only quantity. A
real result could never have triggered it.

---

## Step 2 — C1's OD-011 rev-2 demonstration, and its failure

Run on the real model, through the real pipeline, with the real null subtraction.

| case | must be | observed | |
|---|---|---|---|
| `no_op` | exactly 0 | **−0.506888** | **FAIL** |
| `random_vector` | ≈ 0 | 0.032604 | **FAIL** |
| `flatten_only` | ≈ 0 | **0.144698** | **FAIL** |
| `full_donor` | `CAUSALLY_USED` | +0.038606 | PASS |
| `attenuated_transfer` | positive **and below** full | +0.043370 vs +0.038606 | **FAIL** |

**Four of five failed.**

### The diagnosis, and why it is not a bug

C1's registered form is `raw(patched) − mean over replicates of
raw(destructive patch)`. It therefore subtracts a destruction term from **every**
patch — including one that was never destroyed. For a no-op the expression
reduces to `baseline − null_mean`, which is neither zero nor near it.

The implementation computes exactly the registered expression. Making a no-op
return zero would be **repairing the candidate**, which the pre-registration
forbids.

The magnitude settles it:

| | |
|---|---|
| no-op bias | **−0.506888** |
| largest real signal (`full_donor`) | +0.038606 |
| ratio | **13.1×** |

The estimator's own subtraction term is more than thirteen times the largest
genuine effect it would have to detect. And the attenuated 50% transfer scored
*higher* than the 100% transfer — incoherent for an estimator that should be
monotone in the amount transferred.

### Why the OD-022 sweep did not catch it

My own honesty note predicted half of this: C1's flatten column in the sweep was
`0.000000` **by identity cancellation**, recorded as a limitation of the sweep
rather than a strength of C1, before this demonstration was written. In the real
pipeline no identity cancellation is available, and flatten fails at 0.1447.

The deeper gap is larger than that note. **The sweep evaluates candidates only on
destructive patches.** It never evaluates a no-op, because a no-op is not a
destruction construction — so C1's worst failure lies in a cell the sweep could
not reach even in principle.

> **OD-022 and OD-011 rev 2 are complementary and neither is sufficient alone.**
> OD-022 tests behaviour *under* destruction; OD-011 rev 2 tests behaviour under
> *non*-destruction, including the no-op and a genuine transfer. C1 passed the
> first and failed the second in four cases out of five.

That is recorded as an observation about the two gates. It proposes no new rule,
because proposing one now would be acting on an unfavourable result.

---

## What was not done

C1 **not** repaired. No candidate added. No eliminated candidate revisited. No
selection rule revised. No threshold moved. The MDE pass-line untouched.

**The MDE was never computed**, and correctly so — the power of an eliminated
estimand is not a meaningful quantity. This is therefore **not** an
`UNDERPOWERED` determination.

---

## What survives

The **object** is untouched by this and remains established: accuracy 0.8406,
ablated 0.1062, drop 0.7344, 112 correct-both units, bit-exact no-ops in both
precisions. It is still a **selection set**, not a conclusion.

The measurement pre-registration — its pass-line, its three outcome wordings, its
decision rule — stands unused and unmodified, available to any successor.

---

## Gates

**OD-017 × OD-021: 23 entries, 0 divergences.** Guard PASS. `T` untouched,
sealed lenses unread, zero imports of the instrument under test.

---

## Accounting

| quantity | value |
|---|---|
| GPU-hours, this step | 0.183333 |
| cumulative | 40.144673 |
| ceiling | none applies |
| gates reduced to save time | **0** |

Azure: 0 reconfigurations, 0 power changes, 0 NSG rules, 0 containers, 0 blobs.

---

## State

The closed four-candidate shortlist is **exhausted**: three eliminated by the
OD-022 sweep, the fourth by the OD-011 rev-2 pipeline demonstration. No estimand
registered in this study can currently measure the constructed object, and the
executing party may not declare a fifth.

Reserved for the operator: whether a fifth candidate may be declared at all;
whether requiring a no-op to return exactly zero is even the right requirement
for a null-**subtracting** estimand, since that class is structurally incapable
of satisfying it; whether the answer is a different *class* of estimand; or
whether to stop the J-lens route here.

**No state this phase can reach is a scientific finding.**
