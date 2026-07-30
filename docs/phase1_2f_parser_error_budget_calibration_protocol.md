# Parser-error-budget calibration protocol (prospective)

**Artifact ID:** `phase1-2f-parser-error-budget-calibration/v1`
**Status:** `REGISTERED — NOT EXECUTED`
**Introduced:** Phase 1.2F

> This protocol is **registered, not run**. Phase 1.2F is not authorized to
> execute it. It is **not** Phase 1.0C, is unrelated to Phase 1.0C, and must
> never be described as a continuation of it.

---

## 1. Why this protocol exists

Phase 1.2F left one acceptance criterion unresolved:

> `residual_critical_exact_budget` — the maximum number of exact typed-decision
> errors permitted within the residual critical strata **S04, S05, S09**
> (30 cases).

Its **structure** is derived: gate coverage analysis shows the mandatory gates
already pin 90 of 120 cases to zero errors, so S04/S05/S09 is the only
population over which a non-vacuous criterion can be written.

Its **value** is not derivable today. A repository-wide search found **no
registered maximum tolerable parser-induced distortion** anywhere in the
downstream scientific plan. Without one, no allowable error count can be traced
to anything, and any number chosen would be an unjustified constant.

This protocol defines the calibration that would supply a
`DOWNSTREAM_ERROR_BUDGET` basis.

---

## 2. Quantity to be calibrated

**Definition.** The maximum number of parser extraction errors, within the
residual critical strata, that can be tolerated before the parser's error
materially distorts a downstream scientific conclusion.

Formally: let *D* be a preregistered downstream decision statistic. Let
*δ(k)* be the worst-case distortion of *D* induced by *k* parser errors. The
budget is the largest *k* such that *δ(k)* remains below a preregistered
maximum tolerable distortion *δ\**.

**This is not** an estimate of how many errors the parser makes. It is a
statement of how many the science can absorb. It must be answerable before any
parser is observed.

---

## 3. Why this quantity controls parser-induced scientific error

The parser is an **instrument**, not an object of study. Its errors enter the
scientific record only by corrupting the downstream statistic *D*. A budget
expressed in units of *D*'s tolerable distortion is therefore the only budget
with scientific meaning; a budget expressed as a bare accuracy percentage
asserts a preference, not a requirement.

---

## 4. Prerequisite: register *δ\** first

**Blocking prerequisite.** The downstream scientific plan must first register:

1. the decision statistic *D*;
2. the maximum tolerable distortion *δ\**, with its justification;
3. the direction in which parser error moves *D*.

Until these exist, this protocol cannot start. Registering *δ\** is a
scientific-planning act and must not be performed by inspecting parser results.

---

## 5. Candidate-independent population and fixture generation

The calibration corpus must be **generated**, never sampled from the future
holdout.

* **Method:** programmatic fixture synthesis from the public stratum
  definitions of S04, S05 and S09, using templated arithmetic problems with
  known answers and templated surface realisations of each failure mode.
* **Independence:** fixtures are generated from a registered seed and a
  registered generator, before any candidate is observed.
* **Disjointness:** the generator must be proven to share no case, no source
  problem, and no surface template with the future `parser-v3-v2` set.
* **Publicity:** fixtures are public. They carry no sealed content.

Sampling the future holdout, reusing the 105 migrated cases, or reusing the 15
quarantined cases is **prohibited**.

---

## 6. Reference-label authority and adjudication

* Reference typed decisions are fixed **by construction** — the generator knows
  the intended answer because it built the problem.
* A second, independent human pass adjudicates a registered random subsample to
  confirm the generator's intent matches a human reading.
* Disagreements are resolved by a named adjudicator against the frozen
  three-class truth table.
* An unresolvable fixture is **discarded**, not relabelled. Discards are
  counted and reported.

---

## 7. Sample-size rationale

Sample size is set by the precision required on *δ(k)*, not by convention.

* The design must state the smallest difference in *δ* it must be able to
  resolve.
* The size follows from that resolution requirement and the generator's
  variance, computed **before** generation.
* Because fixtures are synthetic and unlimited, sample size is a cost decision,
  not a scarcity constraint. This removes the usual pressure to under-power.

---

## 8. Analysis method

1. For *k* = 0, 1, 2, … inject exactly *k* controlled extraction errors into
   otherwise-correct parses of the fixture corpus.
2. Propagate each corrupted parse through the **registered downstream
   computation** of *D*.
3. Record worst-case and typical *δ(k)*.
4. Report *δ(k)* as a curve with the injection mechanism fully specified.

Error injection is performed **on fixtures**, by the calibration harness. No
parser is run to obtain *δ(k)*.

---

## 9. Decision rule

> The budget is the largest *k* such that worst-case *δ(k)* ≤ *δ\**.

Registered before any result is seen. If the curve is flat, so that no *k* in
the feasible range 0–30 distorts *D* beyond *δ\**, the honest conclusion is that
**the downstream statistic does not constrain the parser** — and the criterion
must then be justified on a different recognised basis or dropped, **not**
assigned a comfortable number.

---

## 10. Preregistration point

Preregistration occurs **after** §4 and §5 are fixed and **before** any
fixture is parsed or any *δ* is computed. The preregistration must pin:

* the generator and its seed;
* *D*, *δ\**, and the decision rule;
* the injection mechanism;
* the analysis code digest.

---

## 11. Prohibited uses of parser-v3 observations

* Parser-v3 outputs must not be used to choose *k*.
* Parser-v3 outputs must not be used to choose the injection mechanism.
* Parser-v3 outputs must not be used to select or filter fixtures.
* Known parser-v3 development performance must not be consulted at any point.
* The resulting budget must not be revised after observing parser-v3 on any
  evaluation set.

---

## 12. Stopping rules

* Stop when the *δ(k)* curve is characterised across the feasible range 0–30.
* Stop and report `INCONCLUSIVE` if the curve cannot be characterised, if the
  generator is found non-disjoint from the future set, or if adjudication
  cannot resolve the reference labels.
* An `INCONCLUSIVE` calibration leaves the acceptance policy blocked. It must
  not be retried with adjusted parameters until the failure cause is recorded.

---

## 13. Separation from `parser-v3-v2`

| Boundary | Requirement |
| --- | --- |
| Corpus | Synthetic fixtures only; disjoint from the future set by construction and by proof |
| Ordering | Completed and preregistered **before** the `parser-v3-v2` set is sealed |
| Personnel | The calibration must not consume any sealed input or label |
| Output | A single integer budget plus its derivation; nothing about parser v3 |
| Reuse | The budget is fixed at preregistration and never revised against an observed result |

---

## 14. Explicit non-identity with Phase 1.0C

Phase 1.0C was a **target-model observable-answer task/headroom screening**
experiment. It was executed and finalized `INCONCLUSIVE`. It measures whether a
model can answer a question.

This protocol measures how much **parser extraction error** a downstream
statistic can absorb. The two concern different objects. No Phase 1.0C result
is an input here, and this protocol is not a rerun, continuation, or
reinterpretation of Phase 1.0C.
