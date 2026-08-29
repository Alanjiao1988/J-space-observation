# Study 5 — closure of the J-lens route

**Terminated: the estimand search, this measurement route, and the J-lens
instrument line.** The registration closed the door; continuing would require a
new study, which is outside this authorisation.

This is a documentation-only phase. No measurement was run, no lens was read, no
GPU was used.

---

## 1. The conclusion that must appear verbatim

> **This project never tested its hypothesis.** All six phases failed at the
> level of the **measurement apparatus**, and none at the level of the
> hypothesis. Every failure was constructional, demonstrated and reproducible —
> not a case of "we looked and saw nothing".
>
> Therefore: **it must not be claimed that J-space exists or does not exist.**
> This project supplies no evidence on that question, in either direction.

---

## 2. The failure map

The principal output of this project is not a result. It is a record of *which
layer* failed, *by what kind of proof*, and *what survived*.

| phase | determination | layer that failed | nature of the proof |
|---|---|---|---|
| **EQ1** | `Q-4a FAIL` | convention choice (the V axis) | an explanatory annotation, **not** a retraction |
| **EQ2** | `NEGATIVE`, D-1 → negative-A | instrument: `J ≈ αI` degeneracy | identity energy 0.749 at L26, α ≈ 1.0 over L23–26; condition (ii) collapsed the band to length 1; settled by R-0's pre-registered arithmetic |
| **P-0** | `UNINTERPRETABLE` | batch baseline **and** estimand | a no-op guaranteed by the architecture returned 0.013754; the withheld verdict's direction is on record |
| **P-0′** | halted | the estimand *family*, proven dead | the prescription was identical to P-0's own estimand (177,944 values, 0.000e+00); 20,000 clean-run sweep, fraction ≤ 0 = **0.0000**; n = 18 ended that frame |
| **P-0c** | `OBJECT_NOT_ESTABLISHED` | object accuracy | 0.7562 vs 0.80 — **threshold not moved, object not rebuilt** |
| **P-0c-2** | object **established**; shortlist exhausted | the estimand *class as declared* | 0.8406 / 0.1062 / 0.7344 / 112 units; C1 failed 4 of 5 pipeline gate cases |

Six phases, six failures, **all of them in the apparatus**.

---

## 3. Methodological output

To be reported **alongside** the failures, not buried beneath them.

- **The directionality rule** — moving the implementation toward the
  registration is a bug fix; moving the registration toward the data is
  p-hacking. *The boundary is the direction, not the outcome.*
- **Post-hoc tightening vs loosening** — the distinction that made OA-005
  legitimate and would have made its inverse illegitimate.
- **Asymmetric-motivation disclosure** — if a check would only have occurred to
  you on an unfavourable result, say so.
- **OD-011 rev 2** — a non-vacuity demonstration must include a
  *must-return-positive* case; three must-return-negative cases are passed by a
  rule that always returns the negative.
- **OD-017** — a diff of registered text against implementation, comparing
  **live imported values**, never comments.
- **OD-021** — a criterion issued by the *adjudicator* is not exempt from
  verification.
- **OD-022** — the clean-run destruction sweep: a zero-GPU precondition gate that
  killed two estimand families before either cost a forward pass.
- **Push the rule before computing the number** — applied to the n floor, the
  correct-both count, and the MDE pass-line.
- **Commit failed repairs; do not discard them.**
- **The sweep and rev 2 are complementary at the two ends of the nuisance
  parameter** — one tests at high destruction, the other at zero.

---

## 4. Why no fifth candidate was declared

This is not an adjudicator's judgement. It is **registered arithmetic**:

- the measurement pre-registration's stop condition 3 — *"continuing would
  require adding a candidate → stop"*;
- the prior directive — *"if zero candidates survive, stop and report, and add
  no candidate"*;
- the estimand line's *one revision only* allowance was spent on P-0′. This
  shortlist **is** that revision's product, so a fifth candidate is a **second**
  revision.

Recorded verbatim:

> A fifth candidate would necessarily be designed **after** seeing four
> failures, to evade those four failures. Each failure was hit by its own
> pre-declared risk, which proves the pre-declaration was genuine — but it does
> not make a fifth candidate clean, because it would be designed under knowledge
> of **which risks actually bite**.
>
> More fundamentally: if a stop condition written in advance is overturned here,
> then every earlier refusal is retroactively void. The value of this entire
> record rests on this particular refusal holding.

---

## 5. The no-op requirement is coherent; C1's failure is a real defect

> C1 subtracts the same destruction term from every patch, including patches
> where no destruction occurred. For a no-op it degenerates to
> `baseline − null_mean`, measured at **−0.506888**, consistent with the
> destruction mean of 0.4997 that the sweep had already computed.
>
> **The defect is not "subtraction". It is "subtracting a constant that does not
> match".** The amount of destruction is a **nuisance parameter that varies with
> the patch**: zero for a no-op, some unknown intermediate value for a real
> donor patch, largest for a random vector. A fixed additive correction cannot
> track a varying quantity. Requiring a no-op to return zero is exactly the test
> that forces this defect into view, and it is not an unfair demand on a
> subtraction-based estimand.

### Two precision constraints on how this is recorded

**(a) The decisive defect is the no-op bias at 13.1×, not an ordering
violation.** The attenuated transfer (+0.043370) exceeded the full-donor
transfer (+0.038606) by roughly 0.005 — at that noise scale, a violation of
monotonicity is **not statistically established**. It is therefore recorded only
as *"the monotonicity that rev 2 requires was not established"*, and never as
*"non-monotonicity was established"*.

**(b) The "just subtract the constant bias" escape is also closed.** The
full-donor signal is itself only +0.038606 against a bias of 0.507; after
re-centring, the signal-to-noise ratio still does not hold. And rev 2 requires
monotonicity to be *established*, which it was not. **This is written down so a
successor does not walk the same path.**

---

## 6. Limitations, preserved verbatim

- This study **never obtained a passing positive control on the J-lens line**.
  The negative conclusions are strong about *our execution* and weak about *the
  method itself*.
- **bfloat16 reduction order** produces a batch-width-dependent offset on the
  order of 0.476 / 0.110937 logits — the same order as the effects under
  measurement. **Any bf16 patching result that has not demonstrated bit-exact
  no-ops is uninterpretable.**
- **The constructed object is a selection set.** Success on it is not success on
  real items.
- **hop 2 never failing is behavioural evidence, *not* an internal intermediate
  representation.**
- **hop-1 retrieval decay is not a finding of this project.**

---

## 7. Accounting

| quantity | value |
|---|---|
| cumulative actively used GPU-hours | **40.144672** |
| original registered ceiling | 240 |
| gates reduced to save time or hours | **0** |
| Azure configuration changes | **0** |
| blobs written | **0** |
| `T` touched | never |
| `lens_A` / `lens_B` read | never |

Per phase: EQ1 31.582505 · EQ2 7.483333 · P-0 0.106056 · P-0′ 0.341667 ·
P-0c 0.129167 · P-0c-2 0.501944.

---

## 8. What may not be claimed

Nothing here states, implies, or permits a reader to infer: that J-space exists
or does not exist; that the paper is wrong (it measured Sonnet 4.5); that the
published lenses are defective; how `T` would behave (never measured); that
internal causal reasoning machinery exists; any training-causal effect of
distillation; that attention, embeddings, normalisation or whole-model
differences have been explained; that the paper's mid-depth band was reproduced.
No consciousness conclusion is offered or implied.

Additionally:

- **"The question remains open" is not this project's conclusion.** The correct
  statement is that **this project failed to test the question.**
- No result on the constructed object may be presented as a result on real items.
- P-0's withheld verdict may not be cited as a published conclusion.
- The post-hoc diagnosis in the handoff is **not** a methodological contribution
  of this project and **not** a validated solution.
- **Shortlist exhaustion must not be written as "this class of estimand is
  refuted".** What was exhausted is a *closed list*, not a class.

---

*A closure record. It licenses no claim of any kind, and nothing in it is a
scientific finding.*
