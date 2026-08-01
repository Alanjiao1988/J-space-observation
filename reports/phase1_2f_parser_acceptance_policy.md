# Phase 1.2F — Parser acceptance-policy correction and threshold preregistration

**Report type:** implementation and decision record
**Terminal status:** `BLOCKED_ON_ACCEPTANCE_POLICY`
**Baseline:** `origin/main` @ `d843984a3b7e1a2bf9d306621b8557ce327cf987`
**Protocol:** `docs/phase1_2f_parser_acceptance_policy_protocol.md`

> **Superseded in part by Phase 1.2G.** This report remains the accurate record
> of what Phase 1.2F decided and why, and its terminal status
> `BLOCKED_ON_ACCEPTANCE_POLICY` is the correct historical outcome of that
> round. Three things in it are no longer current, and each is marked inline:
>
> * **§15 "Exact next gate"** was wrong when written — it named the *secondary*
>   dependency as the next gate, inverting the ordering §14 had just derived.
> * **§10 verification counts** recorded intermediate figures (`79`, `201`)
>   rather than the committed ones (`127`, `249`).
> * **§2 protected-digest count** records the start-of-round registry size (11)
>   without noting that the same round grew it to 12.
>
> The criterion this round left open, `residual_critical_exact_budget`, was
> resolved in Phase 1.2G. See `reports/phase1_2g_conformance_policy.md`.

---

## 1. Outcome in one paragraph

Phase 1.2E blocked on a stated dependency that did not exist and could not have
existed. Phase 1.2F corrected the record, then asked what the four proposed
acceptance thresholds actually constrain. Two of them turned out to constrain
the same 40 cases as each other, stated over denominators that concealed it. One
of them — macro F1 — returns a **perfect 1.0000 score for a candidate that gets
40 canonical values wrong**, which disqualifies it as a gate. The fourth cannot
be given a numeric margin without observing a parser. What remains after the
audit is a single, genuinely independent criterion over 40 free cases whose
**structure** is derivable candidate-independently but whose **value** is not,
because the scientific decision it depends on has never been taken. No number
was manufactured. The policy stays blocked and the compiler keeps refusing.

Two independent read-only audits then found that this outcome was **right for
partly wrong reasons**. Their accepted findings are recorded in
`reports/phase1_2f_audit_findings.md` and are applied throughout this report:
the gate-coverage baseline was 80/40 rather than 90/30, the confusion-matrix
enumeration was 861 matrices rather than 496, and the named blocking dependency
was not the actual blocker.

---

## 2. Baseline verification

| Check | Result |
| --- | --- |
| `origin/main` vs local `HEAD` | identical, `d843984` |
| Remote advanced beyond baseline | no |
| Working tree at round start | clean |
| Focused repair suite (`tests/test_parser_v3_repair.py`) | **122 passed** (38.32 s) |
| Full suite | **1497 passed** (457.76 s) |
| Protected digests at round start (11 pinned, LF-normalised SHA-256) | 11 / 11 match |

Both recorded expectations (`122 passed`, `1497 passed`) reproduced exactly.

> **Erratum (Phase 1.2G).** This row states the registry size *at the start of*
> Phase 1.2F, which was 11. Later in the same round, finding B15 was remediated
> by adding `evaluator_sets/parser_v3_v1/strata_definitions.md` to
> `PROTECTED_DIGESTS`, taking the registry to **12**. The committed state of
> `3d519e1` pins **12** digests, and the round's closing verification was
> 12 / 12. The row was never updated after the registry grew, so a reader
> checking the shipped code against this report would find a discrepancy. The
> start-of-round figure is left as written because it was true when measured;
> the end-of-round figure is stated here.

---

## 3. The Phase 1.0C correction

### 3.1 The defect

Phase 1.2E recorded its blocker as: *Phase 1.0C headroom calibration is NOT RUN,
therefore the four parser thresholds cannot be set.*

Both halves are wrong, and they are wrong for independent reasons:

* **Factually.** Phase 1.0C was preregistered (`62e9b961`), unblocked
  (`5d18b708`), executed (`72c3d281`), and **finalized** at
  `06eec99315ff5b6c838aeaa82e0814fea6e886b4`. It generated **300 / 300**
  target-model outputs and returned **`INCONCLUSIVE`**. This was already true
  when the Phase 1.2E statement was written.
* **Methodologically.** Even a completed Phase 1.0C could not supply a parser
  threshold. Phase 1.0C's own `scientific_interpretation` describes it as
  estimating "observable answer accuracy of a single target model … for the sole
  purpose of selecting task cells with measurable headroom." It observes a
  model, not a parser. It has no parser reference labels. The dependency was a
  **category error**.

### 3.2 Verified record

Primary evidence:
`artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/04_decision.json`

| Field | Value |
| --- | --- |
| `track_b_decision` | `INCONCLUSIVE` |
| outputs generated | 300 / 300 |
| correct | 156 |
| incorrect | 100 |
| `unresolved_rows` | 44 |
| `outstanding_review_rows` | 0 |
| `arbitration_rows` | 0 |

The number 44 counts **unresolved semantic-equivalence rows**, verified from the
committed result pack rather than restated from prior prose.

### 3.3 Triage and repair method

A repository-wide search returned **45 matches across 17 files**. Each was
triaged into one of three classes:

1. **Historically accurate point-in-time entries** written *before* Phase 1.0C
   executed → **preserved verbatim**, no edit.
2. **Stale current-state summaries** → corrected in place, with the stale text
   retained under an explicit "SUPERSEDED point-in-time record" heading plus an
   erratum.
3. **Phase 1.2E statements that were already false when written** → erratum
   added at the point of the false statement; original text left readable.

No past event was silently rewritten. Every correction is an added erratum or
supersession note.

Files corrected: `reports/current_status.md`, `docs/thread_handoff.md`,
`docs/phase1_2e_parser_v3_ontology_repair_protocol.md`,
`reports/phase1_2e_parser_v3_repair.md`, `docs/run_log.md`,
`docs/decision_log.md`, `paper/limitations_ledger.md`,
`docs/phase1_parser_v3_v2_evaluation_policy.json`.

### 3.4 H9 conflation withdrawn

Phase 1.2E filed the defect as another occurrence of `H9`. Withdrawn.

`H9` concerns **disagreement among declared and observed artifact vocabulary,
support, or set facts**. The Phase 1.2E defect is a **policy-provenance defect**
— a threshold bound to a source that cannot supply it. An unjustified threshold
source is not automatically an H9 occurrence. `H1`–`H9` are otherwise unchanged.

### 3.5 The mechanical guard, and the design mistake behind it

`scripts/check_current_state_consistency.py` fails if a current-state section
combines "Phase 1.0C NOT RUN" with the committed finalized result.

The **first version of this check was wrong in exactly the way Phase 1.2E was
wrong.** It looked for a *within-document* contradiction — a document asserting
both "NOT RUN" and "INCONCLUSIVE". It therefore **passed** on
`reports/current_status.md`, because the stale section only ever said "NOT RUN"
and never mentioned the outcome. A uniformly stale document scored clean.

The fix makes ground truth a **repository fact**, not a prose fact:
`phase_1_0c_was_finalized()` reads the committed result pack directly, and
`scan_text(path, text, *, executed)` takes that as input. With that change the
check immediately caught the real defects. This is recorded because the failure
mode — validating documents against themselves — is the same one that produced
the Phase 1.2E error in the first place.

---

## 4. Gate-coverage baseline

Everything downstream rests on this arithmetic, which was computed from the
policy's own declared gates:

| Coverage | Strata | Cases | Pinned by |
| --- | --- | --- | --- |
| Zero-error, clean | `S01 S02 S03 S12` | 40 | `G_clean_strata_exact` |
| Zero-error, special | `S07 S08 S10 S11` | 40 | dedicated zero-error gates |
| **Free / residual** | **`S04 S05 S06 S09`** | **40** | *nothing* |

**80 of 120 cases are already pinned to exact typed-decision agreement by
mandatory gates.** Any criterion stated over all 120 cases can only constrain
the remaining 40, because a run that errs anywhere else has already failed a
gate.

**Audit finding A2 corrected this table.** The first version reported 90/30 by
counting `S06` as pinned. That required reading `maximum_errors` three
incompatible ways in one table — broadly for `S06`, exactly for the clean
strata, and set-level-only for the null-collapse prohibition, which under the
broad reading would have pinned all 120 cases and made the round moot. The only
*registered* `S06` error definition is narrow: selection of the registered
rightmost distractor span. A parser can satisfy that and still return a wrong
canonical value, so `S06` is free.

Every gate now declares `error_definition`, `error_scope` and
`pins_exact_typed_decision`; the validator refuses a gate that omits any of
them; and the test helper derives coverage from those declarations instead of
hard-coding the disambiguation. Adopting the narrow registered reading is the
conservative choice — it *enlarges* the population the surviving criterion must
govern.

---

## 5. Threshold dispositions

| ID | Disposition | Final value | Basis type | Controlled risk | Independence |
| --- | --- | --- | --- | --- | --- |
| `overall_exact_typed_decision_minimum` | `REPLACE_HARD` | — (non-binding) | — | aggregate decision-accuracy drift | **Partially redundant** |
| `critical_stratum_floor` | `MERGE_WITH_EXISTING_GATE` | — (non-binding) | — | concentrated failure in a critical stratum | **Partially redundant** |
| `answer_presence_macro_f1_minimum` | `REPORT_ONLY` | — (non-binding) | — | presence-class collapse | **Fully redundant and masking** |
| `non_regression_margin_vs_parser_v2` | `REPORT_ONLY` | — (non-binding) | — | silent regression vs predecessor | **Not derivable prospectively** |
| `residual_critical_exact_budget` *(new)* | `REVIEW_REQUIRED` | **`null`** | *(pending an instrument-strictness decision; then `LOGICAL_INVARIANT` or `DOWNSTREAM_ERROR_BUDGET`)* | parser-induced distortion on the 40 ungated cases | **Independent** |

### 5.1 `overall_exact_typed_decision_minimum` → `REPLACE_HARD`

Any value permitting ≥40 errors is **vacuous**: those errors cannot occur
without first violating a zero-error gate. The binding range is 81–120 correct,
which is arithmetically the same constraint as a budget on the 40 free cases —
but expressed over a 120-case denominator that hides what it governs and
invites a reader to believe a 120-case tolerance is being granted.

The structure was kept; the form was discarded. Replaced by
`residual_critical_exact_budget`, stated over the population it actually
governs. The overall figure is still computed and reported, non-binding.

### 5.2 `critical_stratum_floor` → `MERGE_WITH_EXISTING_GATE`

The declared critical set `S04`–`S11` includes four strata (`S07 S08 S10 S11`)
that already carry zero-error gates pinning exact typed-decision agreement. A
per-stratum floor is **inert** on all four for **every possible value**: nothing
is stricter than zero errors, and anything looser is unreachable without already
failing.

Its only independent content is `S04`, `S05`, `S06`, `S09` — the same 40 cases
as §5.1. That is one constraint written twice, with a real risk that the two
numbers disagree at an integer boundary and the policy becomes ambiguous about
which one governs. Merged into the residual budget, where the boundary is
defined once and unambiguously.

### 5.3 `answer_presence_macro_f1_minimum` → `REPORT_ONLY`

The future evaluation is a **fixed, quota-constructed adversarial challenge
set**, not an IID draw. No confidence interval or population-performance claim
is made; `population.sampling_frame` now records this explicitly.

With registered supports `present: 80`, `no_answer: 30`, `ambiguous: 10`, the
feasible three-class confusion matrices were **exhaustively enumerated**:

| Quantity | Value |
| --- | --- |
| Feasible matrices | **861** = `C(42, 2)` |
| Macro-F1 minimum | **0.636895** (at 16 / 24 confusion) |
| Macro-F1 maximum | **1.000000** |
| Attainable spread at exactly 40 presence errors | **0.636895 – 0.755556** |

Attained extrema at equal error counts. **Audit finding A1** established that
two figures in the first version — `0.930233` at 10 errors and `0.783383` at 20
errors — were attainable by *no* admissible matrix, and that no test guarded
them. Every bound below is now an exact enumeration result and is recomputed by
`test_recorded_spreads_are_attained_extrema`:

| Presence errors | Minimum | Maximum |
| --- | --- | --- |
| 10 | 0.866667 | 0.930159 |
| 20 | 0.783355 | 0.869048 |
| 30 | 0.708791 | 0.811966 |
| 40 | 0.636895 | 0.755556 |

Three consequences, in increasing severity:

1. **Any threshold ≤ 0.636895 is vacuous by construction** — no feasible matrix
   can fall below it.
2. **The metric is non-monotone in error count.** Two runs with identical error
   counts can differ by more than 0.10 macro F1 depending only on *which*
   confusions occur. It does not order candidates by severity.
3. **It masks the failure it is nearest to.** Present-value errors were modelled
   separately from answer-presence confusion, because a wrong canonical value
   preserves the presence class while failing exact typed-decision agreement. A
   candidate returning **40 wrong canonical values** with perfect presence
   classification scores **macro F1 = exactly 1.0000** while exact
   typed-decision agreement is **80/120 = 66.7 %**.

A gate that awards a perfect score to a candidate that got a third of the set's
canonical values wrong is not a safeguard. Downgraded to report-only, and
machine-blocked from re-entering PASS/FAIL.

**Audit finding A8** withdrew one supporting argument. An earlier draft cited
the non-vacuity (minimum-denominator) gates as part of the reason class
collapse is already covered. That is a category error: a minimum-denominator
requirement constrains how many cases are *scored*, not how they are
*classified*, so it cannot forbid collapse. The redundancy argument now rests
only on the zero-error gates that pin exact typed-decision agreement.

### 5.4 `non_regression_margin_vs_parser_v2` → `REPORT_ONLY`

The first question was whether comparison with parser v2 should be a hard gate,
a secondary safety check, or report-only context. It is **report-only**, and
after audit finding A4 the justification rests on **one** reason rather than
three:

* **No numeric margin is choosable prospectively.** Every candidate
  justification for a specific margin requires observing at least one parser on
  the locked set — exactly what candidate-independence forbids.

**Two reasons were withdrawn as logically defective:**

* *"Parser v2 failed its own locked evaluation, so it is not a fitness
  reference."* This argues against using parser v2 as a **sufficiency**
  standard. A **non-regression** check makes no sufficiency claim: its whole
  content is that the successor must not be worse than the incumbent, which
  remains meaningful whatever the incumbent's absolute standing.
* *"The comparator run does not exist."* A prospective policy exists precisely
  to register criteria for runs that have not happened. The run's absence
  blocks *evaluation*, not *registration*.

**A margin-free formulation was therefore considered on the merits.** Requiring
per-case dominance — parser v3 correct on every locked case parser v2 is
correct on — needs no number and so escapes the provenance objection entirely.
It is recorded in the policy as `margin_free_formulation_considered` and
**rejected on substance, not on provenance**: on a 120-case quota-constructed
adversarial set the incumbent's per-case correctness pattern is an artefact of
its heuristics rather than a property of the task, so per-case dominance would
promote that artefact to a binding requirement and could refuse a strictly
better parser that trades one incumbent-correct case for several
incumbent-wrong ones.

`comparators.role` is now `REPORT_ONLY`. A recorded regression remains
scientifically informative; gating on it is not defensible.

### 5.5 `residual_critical_exact_budget` (new) → `REVIEW_REQUIRED`

| Attribute | Value |
| --- | --- |
| Population | the 40 free cases in `S04`, `S05`, `S06`, `S09` |
| Metric | count of cases failing exact typed-decision agreement |
| Direction | `errors ≤ B` |
| Boundary | integer; `errors == B` **passes**; `errors == B + 1` fails |
| Structure | derived candidate-independently in this round |
| **Value** | **`null` — `REVIEW_REQUIRED`** |

**Why the value is blocked — corrected by audit finding A3.**

The first version of this section named the missing downstream error budget as
the sole blocking dependency, and defended the unavailability of a
`LOGICAL_INVARIANT` basis with a circular argument: *"if these strata required
zero errors they would already carry zero-error gates."* That offers the
absence of a gate as evidence that no gate is warranted, when the absence of a
gate is exactly the open question. It also produced a block with no working
exit: executing the registered calibration protocol would have supplied a
budget, and the round would still have been blocked.

The dependencies are now **ordered**, and the policy carries a structured
`blocking_dependency` that records the ordering:

1. **Primary — an unmade scientific decision.** `S04`, `S05`, `S06` and `S09`
   are *designed-failure* strata: cases built so that a correct instrument must
   not produce a confident extraction. `S06` is such a stratum and *does* carry
   a zero-error gate, over a narrower registered error definition. Whether the
   instrument must be exactly correct on the remaining designed-failure strata,
   or may be allowed a non-zero budget, has never been decided. A
   `LOGICAL_INVARIANT` basis for `B = 0` is available in the abstract; what is
   missing is the decision, not the basis. Taking that decision is a scientific
   act about how strict this instrument must be, and it is not this round's to
   take.
2. **Secondary — a downstream error budget.** *Only if* a non-zero tolerance is
   permitted does `B` need tracing to a preregistered maximum tolerable
   parser-induced distortion in a later scientific metric. A repository-wide
   search of `docs/`, `paper/` and `reports/` for such a registered tolerance
   returned **no matches**.

The remaining bases are unavailable either way:

* **`EXTERNAL_CANDIDATE_INDEPENDENT_CALIBRATION`** — the necessary calibration
  is registered by this round but **not executed**.
* **`REVIEWED_OPERATIONAL_REQUIREMENT`** — no evaluator-reliability requirement
  independent of both candidate and holdout has been stated for these strata.

**Audit finding A9** qualifies the "no budget exists" claim. It is true as
stated, but the downstream plan is not wholly silent:
`docs/phase1_capability_headroom_protocol.md` lines 228-229 and 252 *do*
register the downstream decision rule and name the parser as a
failure-attribution category. What is absent is only the tolerance itself.

Any number inserted today would be chosen by someone who already knows how
parser v3 behaves in development. That is the definition of the post-hoc
selection this round exists to prevent. The field stays `null`.

---

## 6. Tooling changes

### 6.1 `src/jspace_observation/parser_v3_repair_contract.py`

Added a threshold-provenance validator (~260 lines) and bumped
`POLICY_SCHEMA_VERSION` to `/v2` (verified safe — the constant is referenced
only within that module).

| Construct | Purpose |
| --- | --- |
| `THRESHOLD_BASIS_TYPES` | the four recognised bases; anything else is rejected |
| `THRESHOLD_DISPOSITIONS` | the six permitted dispositions |
| `BINDING_DISPOSITIONS` | **`("KEEP_HARD",)`** — only this binds |
| `NON_BINDING_DISPOSITIONS` | includes `REPLACE_HARD`: a replaced identifier stops binding, its successor binds instead |
| `REQUIRED_THRESHOLD_FIELDS` | `basis_type`, `controlled_risk`, `derivation`, `evidence_bindings`, `candidate_independence`, `set_independence`, `boundary_semantics`, `review_status` |
| `INEQUALITY_DIRECTIONS` | rejects inconsistent directions and comparator-margin signs |
| `PROHIBITED_BASIS_SOURCES` | 22 normalised needles (`1.0c`, `headroom`, `observed parser`, `development accuracy`, `industry standard`, `carried over verbatim`, …) matched across `reason`, `blocking_dependency` (recursively), every evidence binding, and ten prose fields of **every** threshold record whatever its disposition |
| `_normalise_for_basis_scan` | collapses hyphens, underscores, line wraps and spacing so `Phase 1.0-C` and `parser v 2` cannot evade the scan |
| `GATE_ERROR_SCOPES` / `REQUIRED_GATE_SEMANTIC_FIELDS` | audit finding A2: every gate must declare `error_definition`, `error_scope` and `pins_exact_typed_decision`, and a `set_level` gate may not claim to pin a case |
| `_collect_clause_text` | audit finding B5: flattens a `status_logic` clause of any shape, so a list or nested object cannot bypass the non-binding re-entry check |

Two design decisions worth recording:

* **`REPLACE_HARD` is non-binding.** A replaced threshold that still bound would
  leave two live constraints on the same population. Non-binding thresholds must
  carry `value: None` and `binding: False`, and `REPLACE_HARD` /
  `MERGE_WITH_EXISTING_GATE` must name a `replaced_by` / `merged_into` that
  resolves to a known threshold ID or a `G_`-prefixed gate.
* **`validate_acceptance_thresholds` returns the set of non-binding IDs**, and
  `validate_policy` rejects any `status_logic` clause naming one. This is what
  makes "report-only cannot silently re-enter PASS/FAIL" a machine-checked
  property rather than a promise. Audit finding B5 widened it from the two keys
  `PASS`/`FAIL` and string clauses only, to every non-reserved key and every
  clause shape.

**Two holes found by audit and closed.** Audit finding A5/B6 showed the
validator admitted a **vacuous PASS**: with `REMOVE_REDUNDANT` requiring no
successor pointer, every threshold could be retired and PASS would reduce to
the mandatory gates alone, leaving the free cases wholly unconstrained. The
validator now requires `REMOVE_REDUNDANT` to name a `subsumed_by`, requires the
named successor to actually bind when the block is `FINAL`, and refuses a
`FINAL` block with no binding criterion at all. Audit finding B10 closed a
smaller one: a `REVIEW_REQUIRED` record could declare `binding: true`.

**Scope, stated honestly (audit finding A6/B7).** The prohibited-basis scan is
a **bounded carelessness check, not a semantic guarantee**. It catches a
disallowed source that is *named*, and survives hyphenation and line wrapping.
It cannot detect a paraphrase, and it does not replace review. The policy
records this as `enforcement_scope`.

A consequence of the prohibited-source matcher: the policy's
`acceptance_thresholds` block may contain **neither** prohibited string, so the
Phase 1.0C errata live in a separate top-level `errata` key rather than inline.

### 6.2 Other tooling

| File | Change |
| --- | --- |
| `src/jspace_observation/parser_v3_repair_ontology.py` | docstring source-of-truth repointed from the retired v1 namespace to the v2 stratum policy |
| `scripts/parser_v3_repair_cli.py` | corrected the overbroad claim "It imports no parser module." |
| `scripts/check_current_state_consistency.py` | new mechanical guard (§3.5) |
| `tests/test_parser_v3_repair.py` | `final_policy` fixture conformed to the strengthened schema; new `resolve_threshold()` helper |

---

## 7. Artifacts created

| Path | Role |
| --- | --- |
| `docs/phase1_2f_parser_acceptance_policy_protocol.md` | Phase 1.2F protocol |
| `reports/phase1_2f_parser_acceptance_policy.md` | this report |
| `docs/phase1_2f_threshold_dispositions.json` | machine-readable disposition artifact incl. the 496-matrix analysis |
| `docs/phase1_2f_parser_error_budget_calibration_protocol.md` | the §8 next-calibration protocol — `REGISTERED — NOT EXECUTED` |
| `docs/phase1_parser_v3_v2_stratum_policy.md` | public, case-free, versioned v2 stratum policy |
| `scripts/check_current_state_consistency.py` | mechanical current-state guard |
| `tests/test_parser_v3_acceptance_policy.py` | Phase 1.2F test suite |

`docs/phase1_parser_v3_v2_evaluation_policy.json` was rewritten at schema `/v2`,
adding `errata`, `post_hoc_disclosure`, `gate_coverage_analysis`,
`population.sampling_frame`, `population.zero_gated_critical_strata` /
`residual_critical_strata`, `comparators.role`, `status_logic.non_binding_rule`,
and `provenance.retired_binding`.

---

## 8. Namespace provenance and L-32

The prospective policy bound to `evaluator_sets/parser_v3_v1/strata_definitions.md`
— a **retired v1 namespace**. That conflicts with the new-set identity rule,
with the repair CLI's v1-namespace refusal, and with the requirement that reused
design artifacts be re-derived and revalidated.

`docs/phase1_parser_v3_v2_stratum_policy.md`
(`phase1-parser-v3-v2-stratum-policy/v2`) resolves it: public, case-free,
versioned, with explicit provenance and an **independent recorded decision to
retain** the 12-stratum taxonomy on its merits rather than by inheritance. It
creates no private case, label, membership manifest, or sealed object.
`policy.provenance.retired_binding` records the supersession.

**`L-32` preserved accurately.** A future sealed member list and
`sealed_object_count` require an **authenticated seal-time observation**. They
are not facts an offline prospective policy can derive, and an operator
assertion must never be recorded as a set-derived fact. The v2 stratum policy
names these quantities only to disclaim them; a test asserts no value is
attached to either.

---

## 9. Parser-isolation claim

`src/jspace_observation/__init__.py` **eagerly imports the legacy parser**.
Importing a submodule through the package may therefore already place parser
code in `sys.modules`, so the previous wording was unsupportable.

**Withdrawn:** "no parser module exists in the process"; "package import is
absolutely parser-free".

**Retained and tested:** repair modules introduce **no new** parser dependency;
contain **no parser symbol reference**; repair tooling **does not invoke** a
parser.

The differential-import test imports the package baseline, records
`sys.modules`, imports the repair tooling, and proves no *additional* parser
module appeared. An AST-based static analysis proves no parser symbol is
referenced. A subprocess runtime tracer proves **zero parser invocations**.

`__init__.py` was **not** refactored. Changing package import behaviour purely to
make a claim true would have been the wrong repair.

---

## 10. Verification

| Check | Result |
| --- | --- |
| Phase 1.2F suite (`tests/test_parser_v3_acceptance_policy.py`) | **127 passed** |
| Focused repair suite (`tests/test_parser_v3_repair.py`) | **122 passed** |
| Combined focused run | **249 passed** |
| Policy JSON validation against the strengthened validator | OK |
| `scripts/check_current_state_consistency.py` | exit 0 |
| Protected digests | unchanged |

> **Erratum (Phase 1.2G).** This table originally recorded `79 passed` for the
> Phase 1.2F suite and `201 passed` combined. Those were the counts at an
> intermediate point of the round. Phase 1.2F went on to add the audit-driven
> regressions — including the seven `_elide_markup` tests written after the
> consistency checker was found to be defeatable by markdown emphasis — and the
> committed state of `3d519e1` runs **249**, not 201. The figure was never
> re-measured before the report was written. Corrected above; the superseded
> figures are named here so a reader who saw them can recognise the change.
> `reports/current_status.md` separately carried `242`, a third intermediate
> value, also corrected.

No existing test was weakened, removed, or skipped. One assertion in the **new**
Phase 1.2F suite was corrected during development: it forbade the literal string
`sealed_object_count` anywhere in the v2 stratum policy, which wrongly failed
the L-32 note that *names the quantity in order to disclaim it*. The assertion
now forbids the quantity being **given a value** (`sealed_object_count: <digit>`),
which is the property that actually matters. That is a corrected test, not a
weakened one — the pre-existing suites were untouched.

---

## 11. Independent audits

Two read-only review agents were run: **Audit A** (methodology and statistics)
and **Audit B** (repository and instrument consistency). Findings, severities,
dispositions, fixes and residual limitations are recorded in §12 of this report.

Self-authored tests are **not** described as independent validation. The tests
in `tests/test_parser_v3_acceptance_policy.py` encode the round's own reasoning;
they demonstrate internal consistency, not external correctness.

---

## 12. Audit findings

Two read-only review agents audited the round's first draft before commit.
Audit A covered methodology and statistics; Audit B covered repository and
instrument consistency. The full record — every finding with severity,
evidence, disposition, fix and residual limitation — is
`reports/phase1_2f_audit_findings.md`.

| Audit | Findings | BLOCKER | MAJOR | MINOR | OBSERVATION | Rejected |
| --- | --- | --- | --- | --- | --- | --- |
| A — methodology / statistics | 10 | 2 | 3 | 3 | 2 | 0 |
| B — repository / instrument | 16 | 0 | 6 | 7 | 3 | 0 |

No finding from either audit was rejected. Two claims made *by this round* were
withdrawn on audit (A4, A8) and one was narrowed (A9). Both auditors
independently found the vacuous-PASS hole (A5 / B6) and the prohibited-basis
over-claim (A6 / B7).

The consequential result is A2 with A3. The first draft reached
`BLOCKED_ON_ACCEPTANCE_POLICY` — the right answer — while publishing a wrong
gate-coverage baseline (90/30 rather than 80/40), a wrong enumeration domain
(496 rather than 861 matrices), and a blocking dependency that was not the
blocker, so that executing the registered calibration would have left the round
still blocked. A green suite of self-authored tests passed throughout. The
audits are the reason the shipped figures are right; the tests were not.

Neither auditor re-verified the remediation, and both are language models
commissioned by the author whose work they reviewed. See §0 of the findings
report for the limits of the independence claim.

One further defect (`C1`) was found *after* the audits closed, by the rebuilt
consistency checker acting on the author's own prose: markdown emphasis
delimiters were not elided, so `**not**` broke every contiguous phrase pattern.
The benign symptom was a false positive on a correction; the serious form is
that `Phase 1.0C has **not** been run` would have passed the check. It is fixed
and recorded in the findings report and in `L-34`. Two independent audits plus a
self-check found four defects in one small script, which is the right prior for
how many remain.

---

## 13. Standing state after Phase 1.2F

* Phase 1.0C was **executed** and finalized **`INCONCLUSIVE`**.
* Phase 1.0C is **not** parser calibration and supplies no parser threshold.
* No private holdout was accessed in Phase 1.2F.
* No prediction was generated.
* No parser was run.
* No formal evaluation occurred.
* Parser v3 remains **unvalidated**.
* Formal parser-v3 evaluation ordinal remains **0**; parser-v3 predictions
  against a locked set remain **0**; locked-label reads remain **0**.
* `parser-v3-v1` remains **`SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`**
  and byte-unchanged.
* **No J-space, hidden-reasoning, invisible-CoT, or internal-workspace
  conclusion follows** from anything in this round.

---

## 14. Unresolved decisions

1. **The instrument-strictness decision for `S04`, `S05`, `S06`, `S09`.** This
   is the *primary* blocker (Audit A, A3). These four strata carry the 40 free
   cases: no registered gate pins their exact typed decision. The question is
   what the designed-failure strata are *for*. If the answer is that a correct
   parser must get them right and the tolerated error count is zero, then
   `residual_critical_exact_budget = 0` follows as a `LOGICAL_INVARIANT` and no
   calibration is needed. This round does not take that decision: taking it
   while four development results are already known is exactly the post-hoc
   selection the round exists to prevent.
2. **The value of `residual_critical_exact_budget`, if non-zero tolerance is
   permitted.** This is the *secondary*, conditional blocker. It arises only
   if decision 1 permits a non-zero count, and it then requires a registered
   downstream parser-error budget, which does not exist. This is what
   `docs/phase1_2f_parser_error_budget_calibration_protocol.md` is registered
   to supply. Running that calibration *before* decision 1 would leave the
   policy blocked regardless — the ordering matters.
3. **Whether the post-hoc disclosure (`L-33`) is fully mitigable.** It probably
   is not; the operator already knows development results. The mitigation is
   structural (candidate-independent derivation, external calibration), not
   epistemic.
4. **Whether the two `REPORT_ONLY` metrics should exist at all.** Macro F1 and
   the parser-v2 comparison are retained as reported context with no PASS/FAIL
   authority, and a validator guard prevents them re-entering status logic. A
   future round may find that publishing a number nobody may act on invites the
   very informal gating the demotion was meant to remove.

---

## 15. Exact next gate

> **Superseded by Phase 1.2G.** This section was wrong when written, and the
> error is recorded here rather than deleted.
>
> §14 of this report had already established that the dependencies are
> *ordered*: the strictness decision is primary, and the downstream error
> budget is required only if that decision permits a non-zero tolerance. This
> section then named the secondary dependency as the next gate, inverting the
> ordering the same report had just derived. Following it would have produced a
> calibrated number for a question nobody had asked.
>
> **What actually happened.** Phase 1.2G settled the primary decision — the
> future set is a finite conformance suite, so the permitted mismatch count is
> zero — which made the secondary dependency moot.
> `docs/phase1_2f_parser_error_budget_calibration_protocol.md` is now
> `SUPERSEDED_UNEXECUTED` and was never run.
>
> The correct next gate is recorded in
> `reports/phase1_2g_conformance_policy.md`.

**As written (superseded):**

> **Register a downstream parser-error budget**, then execute
> `docs/phase1_2f_parser_error_budget_calibration_protocol.md`.
>
> That protocol is **not** Phase 1.0C, is not a target-model headroom screen,
> and was not executed in this round.
>
> Until a budget exists: `residual_critical_exact_budget` stays
> `REVIEW_REQUIRED`; the policy stays `REVIEW_REQUIRED`; `compile_contract`
> keeps refusing; and `parser-v3-v2` set repair, construction, sealing,
> preregistration, Stage P and Stage E all remain unauthorized.
