# Phase 1.2G — Post-audit consistency remediation and conformance-policy finalization

**Terminal status: `READY_FOR_INDEPENDENT_SET_REPAIR`.**

Baseline `3d519e1`. No private data was read, no parser was run, no prediction
was generated, no set was constructed, and no Azure resource was touched. Parser
v3 remains **unvalidated** and the formal evaluation ordinal remains **0**.

---

## 1. What was open, and what closed it

Phase 1.2F ended with one criterion left non-vacuous and blocked:
`residual_critical_exact_budget`, the allowable count of exact typed-decision
mismatches over the cases that the mandatory gates do not already pin. Phase
1.2F was right not to fill it in. It searched for a downstream parser-error
budget to trace a number to, found none, and refused to invent one. It also
recorded, correctly, that a `LOGICAL_INVARIANT` basis for `B = 0` was available
*in the abstract* — what was missing was the decision that would license it.

That decision has now been taken.

> **Strict finite-suite conformance.** The future `parser-v3-v2` set is a finite
> conformance suite, not a sample. Every case admitted to it is admitted because
> a correct instrument is required to handle it. Every admitted case is
> therefore a mandatory conformance example, and an exact typed-decision
> mismatch on any admitted case is unacceptable instrument behaviour.

The consequence is short. Admission makes each case carry a requirement of its
own: for every admitted case `c`, the instrument must reproduce the reference
typed decision on `c`. An aggregate tolerance `B > 0` does not weaken that
requirement, it contradicts it, because a universally quantified obligation
admits no exception count.

The natural objection — that an aggregate budget need not say *which* cases may
fail — is answered rather than dodged. "At most one mismatch anywhere" is a
perfectly well-defined rule that names nothing. The defect is not that the
permitted cases are unnamed; it is that any exception count at all negates a
per-case obligation. So `0` is not the strictest choice among available values;
it is the only value the premise supports. That is what makes it a
`LOGICAL_INVARIANT` rather than a severity judgement.

The earlier "cannot name which subset" phrasing, which audit finding A-01
identified as under-powered, is withdrawn wherever it appeared.

### 1.1 The derivation is constrained on purpose

Zero is an easy number to reach for the wrong reasons, and most of the wrong
reasons are disallowed bases under the rules Phase 1.2F established. The
recorded derivation therefore does **not** appeal to any of:

determinism of the parser; the set not being an IID sample; the absence of a
registered downstream error budget; conservatism or caution; the tidiness of the
number zero; parser-v2 precedent; any expectation about parser-v3 performance.

`test_the_derivation_never_appeals_to_determinism_or_tidiness` scans the
recorded derivation text for exactly these appeals. It is a carelessness check,
not a semantic guarantee — it catches a disallowed argument that is *named*, and
cannot catch a paraphrase. It should not be described as proof of provenance.

### 1.2 The falsifier is recorded with the premise

A premise that cannot fail is not doing work. This one can:

> If a case is admitted that a correct instrument is **not** required to handle
> — aspirational, observational rather than required, or carrying an uncertain
> reference label — the premise fails, the invariant loses its basis, and the
> value must be re-derived rather than inherited.

Eligibility for admission and "must be handled correctly" have to remain the
same predicate. The set-repair round inherits that constraint. It is recorded as
`L-35`.

There is a second-order form worth naming, and it is recorded in `L-35` too:
because the invariant is derived from the construction rule, it is possible to
satisfy the *policy* by weakening the *set*. Admitting fewer or easier cases
keeps the budget at zero while quietly reducing what zero means. Nothing in the
acceptance policy can detect that, because the policy sees the set only through
its declared strata and supports. The protection must come from the set-repair
round's own review.

### 1.3 What `FINAL` does not mean

`FINAL` records that the rule for judging a future evaluation is settled. It
records nothing about any parser. The policy is now **harder** to pass than the
one it replaces — every one of the 120 cases is pinned to exact typed-decision
agreement — and it was written knowing that. The policy JSON states this about
itself in `execution_state.final_policy_is_not_a_result`.

## 2. Threshold dispositions

| Threshold | Disposition | Value | Basis | Controlled risk | Status |
| --- | --- | --- | --- | --- | --- |
| `overall_exact_typed_decision_minimum` | `REPLACE_HARD`, non-binding | — | — | none reachable | fully subsumed |
| `critical_stratum_floor` | `MERGE_WITH_EXISTING_GATE`, non-binding | — | — | none reachable | fully subsumed |
| `answer_presence_macro_f1_minimum` | `REPORT_ONLY` | — | — | none binding | cannot detect value errors |
| `non_regression_margin_vs_parser_v2` | `REPORT_ONLY` | — | — | none binding | no derivable margin |
| `residual_critical_exact_budget` | `KEEP_HARD`, binding | `0` pooled, `0` per stratum | `LOGICAL_INVARIANT` | undetected extraction error on a designed-failure case | independent |

These are the dispositions recorded in the canonical policy, and this table is
checked against it. An earlier draft of this report called the first two
`REMOVE_REDUNDANT` and argued they were "removals and not merges"; independent
audit findings A2 and B1 caught the disagreement with the canonical artifact.
The canonical dispositions are the correct ones and the report was wrong: the
overall minimum was *replaced* by the residual criterion, which is a different
metric over a different population rather than a deletion, and the per-stratum
floor was *merged into* it as `limits.per_stratum_max_errors`. Recording them as
removals would have erased where the constraints went. The substantive point the
draft was making is unaffected and stands: neither is binding, and neither can
fire.

**Why neither can fire.** With 80 of 120 cases pinned by mandatory gates and the
residual 40 pinned at zero, an overall minimum and a per-stratum floor are both
implied by criteria that already exist. A criterion that cannot fire must not be
binding, because it appears in the policy as protection and a later reader counts
it. Both carry `binding: false`, and the validator refuses any policy whose
`PASS`, `FAIL` or `INVALID` clause names a non-binding identifier.

**Why macro F1 stays report-only.** Exhaustive enumeration of the 861 feasible
three-class confusion matrices at the registered supports (present 80,
`no_answer` 30, ambiguous 10) shows macro F1 responds only to *presence-class*
confusion. A candidate that assigns the correct presence class but the wrong
canonical value is invisible to it. Macro F1 measures something real; it does
not measure this, and preserving it as a hard gate would have been cosmetic.

**Why the comparator stays report-only and non-binding.** No prospectively
choosable margin exists that is not derived from one parser's observed
performance. The one substantive argument for binding it was withdrawn in Phase
1.2F as unsound (finding A4) and, as of this round, is no longer asserted
anywhere live. It survives only as a structured `withdrawn_arguments` record,
which is what `G-06` was about.

> **Withdrawn argument, quoted as written.** The predecessor "failed its own
> locked evaluation, so parity with it is not evidence of fitness." Phase 1.2F
> finding A4 rejected this: a predecessor's failure bears on the predecessor,
> not on whether matching the predecessor certifies the candidate.

A test proves no removed or report-only metric can re-enter `PASS`/`FAIL` logic.

## 3. The ten seed defects

`G-01` … `G-10` are **consistency failures between this project's own
artifacts**. They are deliberately not numbered into the historical `H1`–`H9`
series, which is unchanged and concerns the evaluation instrument's
declared-versus-observed facts. Merging the series would corrupt the meaning of
both.

| ID | Quoted defect | Remediation |
| --- | --- | --- |
| `G-01` | Residual-population prose disagreed with the structured population it described | Structured population is authoritative; `_check_population_prose` rejects prose that names strata, cardinality words or "N cases" inconsistently with it |
| `G-02` | Stratum policy carried the superseded 90/30 split and called `S06` pinned | §5 table corrected, superseded figures named as superseded, derivation authority stated |
| `G-03` | Calibration protocol specified 30 cases, three strata, budget range 0–30 | Protocol status → `SUPERSEDED_UNEXECUTED` with a §0 supersession record, correction table and four reactivation conditions |
| `G-04` | Phase 1.2F report §15 stated the next gate in inverted order | §15 marked superseded, with the ordering inversion explained |
| `G-05` | Synthetic fixture asserted "30 cases in S04, S05 and S09" | Fixture rebuilt against the derived population |
| `G-06` | Withdrawn comparator argument still asserted live in `paper/methods_ledger.md` | Removed from live prose with a correction note; retained as `withdrawn_arguments` in the policy |
| `G-07` | Audit report claimed every figure was regenerated; artifacts contradicted it | Erratum naming exactly which artifacts kept old figures and why the check was too narrow |
| `G-08` | Focused-suite totals recorded as 201 / 242; transcript shows 249 | Corrected with erratum in both the report and `reports/current_status.md` |
| `G-09` | Per-stratum cap existed only in prose | `limits.per_stratum_max_errors` added as a machine-readable, validated field |
| `G-10` | `PROTECTED_DIGESTS` holds 12 entries; report said 11 | Erratum; count verified programmatically, not by inspection |

Six of the ten were stale *figures* in prose. That is the pattern this round had
to address structurally, not one document at a time.

## 4. What changed structurally

### 4.1 The policy JSON is canonical

`docs/phase1_parser_v3_v2_evaluation_policy.json` declares itself the canonical
machine-readable statement of the policy. Where a report, protocol, ledger or
comment disagrees, the policy governs and the other artifact is defective. The
schema moves to `phase1-parser-v3-prospective-evaluation-policy/v3`.

### 4.2 One production coverage derivation

`jspace_observation.parser_v3_repair_contract.derive_gate_coverage` is now the
single implementation of exact-typed-decision coverage. Both `validate_policy`
and `compile_contract` consume it, and `compile_contract` emits the derived
coverage into the compiled contract. The policy's `gate_coverage_analysis` block
is a *restatement* the validator requires to agree with the derivation — it is
not an input.

It derives from `GATE_ERROR_DEFINITIONS`, a **closed, code-owned** registry
recording each definition's scope, counting unit, whether it pins exact
typed-decision agreement, and why. An unknown definition is refused. A policy
that restates a registry entry incorrectly is refused. The derivation is
fail-closed: a gate whose population cannot be resolved raises rather than
silently covering nothing.

Authoritative result:

* **pinned, 80 cases** — `S01`, `S02`, `S03`, `S07`, `S08`, `S10`, `S11`, `S12`;
* **residual, 40 cases** — `S04`, `S05`, `S06`, `S09`;
* accepted-policy coverage `80 + 40 = 120 / 120`.

`S06` is residual, and this is the single most misread fact in the record. Its
dedicated gate is a zero-error gate, which reads like pinning, but its only
registered error definition is
`registered_rightmost_distractor_span_selected` — it forbids one specific wrong
span and does not entail exact typed-decision agreement.

### 4.3 Current state is generated, not typed

`scripts/generate_current_state.py` renders the current-state block of
`reports/current_status.md` and `docs/thread_handoff.md` from the canonical
policy and the production derivation, between sentinel comments. `--check`
re-renders and compares bytes and prints a diff on mismatch; `--write`
regenerates.

This is the structural answer to `G-01`–`G-05`, `G-08` and `G-10`. A prose
scanner can only reject sentences someone thought to pattern-match, so every new
figure needs a new pattern and any figure nobody anticipated drifts silently. A
rendered figure cannot go stale because it is never typed.
`scripts/check_current_state_consistency.py` is retained as the backstop for
claims that are *not* figures, and gains two new checks: superseded figures, and
the calibration protocol's status.

### 4.4 Both pooled and per-stratum limits

Arithmetically equivalent today; not equivalent under amendment. An editor
raising one stratum's cap while holding the pool at zero produces an
inconsistency the validator catches. A pooled-only policy would have admitted
that change silently. Redundancy between two statements of one constraint is
cheap; a single point of drift is not.

## 5. Two defects this round's own tests found in this round's own code

Recorded because a round whose error log is empty is a record of unexamined
work.

**A zero margin is still a margin.** The comparator validator screened optional
fields with `if value not in (None, False)`. In Python `0 == False`, so a
comparator margin of `0` — which encodes the substantive rule "must not be worse
than parser v2" — was silently classified as *absent*. Fixed by testing
`is not None` and moving the `binding` flag to its own explicit `is not False`
check. Pinned by `test_a_zero_comparator_margin_is_still_a_margin`.

**A negation guard that exempted the sentence it existed to catch.** The new
superseded-figure scanner skips sentences that explicitly *deny* a superseded
figure, so that errata remain writable. The withdrawn comparator argument
contains a negation as part of the claim itself — "not worse than it is not
evidence of fitness" — so the guard exempted it. Fixed by making negatability a
per-pattern property rather than a global rule. The fix was found by a
positive-control script that asserts the scanner catches all nine defect forms
and none of the four exempt forms; that control is now a test.

## 6. Verification

| Check | Result |
| --- | --- |
| Baseline full suite (`3d519e1`) | **1624 passed** |
| Focused Phase 1.2E + 1.2F + 1.2G suites | **446 passed** |
| Full suite | **1821 passed** |
| `python -m compileall` | clean |
| `validate_policy` on `docs/phase1_parser_v3_v2_evaluation_policy.json` | OK, `status = FINAL` |
| `derive_gate_coverage`, pinned side | 8 strata, 80 cases: `S01`, `S02`, `S03`, `S07`, `S08`, `S10`, `S11`, `S12` |
| `derive_gate_coverage`, residual side | 4 strata, 40 cases: `S04`, `S05`, `S06`, `S09` |
| `scripts/check_current_state_consistency.py` | OK |
| `scripts/generate_current_state.py --check` | OK |
| `git diff --check` | clean |
| Protected-file digests | 12 / 12 unchanged, §7 |
| `docs/phase1_parser_v3_v2_evaluation_policy.json` SHA-256 | `e8d4391387f4f6682d9a947f58a4586ce0c110c16c3f66e4250b134690eb9114` |
| `docs/phase1_2f_threshold_dispositions.json` SHA-256 | `29b05df34959eff6f4cc9863cb8eb22ae14544051f437d271e36f8e4f17286fc` |

The focused and full totals above are the post-remediation figures. The first
pass of this round reached 382 focused / 1757 full. Three successive
independent re-reviews then returned seven, five and six findings; closing them
added tests and corrected further documents, reaching 399 / 1774, then
411 / 1786, then the figures above. Every intermediate figure is recorded
because the differences are the measurable cost of the re-review steps, and
reporting only the final number would hide it.

No existing test was weakened, removed, skipped or `xfail`ed. Five Phase 1.2F
tests pinned the then-correct blocked state and could not survive the policy
becoming `FINAL`; each was **superseded by a strictly stronger assertion**, with
a docstring recording what it used to assert and why the replacement is
stronger. Superseding a test with a stronger one is not weakening it, and the
distinction is load-bearing — it is exactly the move that would be abused to
manufacture a green suite, so each instance is written to be individually
checkable.

### 6.1 Recorded totals

The focused figure is the combined count of
`tests/test_parser_v3_acceptance_policy.py` and
`tests/test_parser_v3_repair.py`, which is what "focused" has meant in every
prior round of this series. It rose from **249** at `3d519e1` to **446**. The
first pass reached **382**; three successive independent re-reviews then
returned seven, five and six findings, and the regressions closing them are
collected in sections 12 to 15 of
`tests/test_parser_v3_acceptance_policy.py`.

`G-08` is the reason this report states where its figures came from: the Phase
1.2F totals were transcribed by hand and were wrong. These were read from the
pytest summary line of the runs recorded above, not reconstructed afterwards.

## 7. Protected artifacts

`PROTECTED_DIGESTS` holds **12** entries — verified programmatically, which is
the correction `G-10` required, since the previous count of 11 came from reading
the list.

**All 12 protected digests are unchanged by this round.** Verified twice: by the
registry's own LF-normalised SHA-256 comparison, and independently by raw-byte
SHA-256 recomputation of every protected path.

One clarification is worth making because an earlier draft of this report got it
wrong. `docs/phase1_parser_v3_v2_stratum_policy.md` — the public, case-free v2
stratum policy corrected under `G-02` — is **not** a protected artifact. The
protected registry contains the *retired v1* namespace file
`evaluator_sets/parser_v3_v1/strata_definitions.md`, which is untouched. The two
are easy to confuse, and confusing them is precisely the class of error this
round exists to remove, so the distinction is recorded rather than silently
corrected: the v2 policy is a live design artifact that Phase 1.2G was
authorized to correct; the v1 definitions file is frozen historical evidence
that it was not.

The protected paths are the parser sources (`eval_parsing_v3.py`,
`eval_parsing_v2.py`, `eval_parsing.py`), `evaluator_validation.py`, the
historical parser-v2 protocol and gate contract, the evaluator-validation set,
the historical invalid parser-v3-v1 gate contract, and the four
`evaluator_sets/parser_v3_v1/` provenance artifacts.

## 8. Independent audits

Recorded in `reports/phase1_2g_audit_findings.md`, including a
**post-remediation re-review**. An audit that sees only the pre-fix state and
then accepts the author's own claim of remediation is not independent
verification and is not described as such anywhere in this record.

Self-authored tests are not independent validation.

## 9. Standing state

Phase 1.0C was **executed** and finalized **`INCONCLUSIVE`**, at `06eec993`,
generating 300/300 target-model outputs with 44 unresolved semantic-equivalence
rows. It is target-model observable-answer task/headroom screening. It is not
parser calibration, and no Phase 1.0C result can supply, bound, or unblock any
parser acceptance threshold.

No private holdout was accessed in Phase 1.2G. No prediction was generated. No
parser was run. No formal evaluation occurred. Parser v3 remains
**unvalidated**; formal evaluation ordinal remains **0**; parser-v3 predictions
against a locked set remain **0**; locked-label reads remain **0**.
`parser-v3-v1` remains **`SEALED / UNSPENT / UNSCORABLE /
RETIRED_AS_INELIGIBLE`** and byte-unchanged. **No J-space, hidden-reasoning,
invisible-CoT or internal-workspace conclusion follows from any of this.**

### 9.1 A disclosure about "no parser was run"

The claim above is precise and should be read precisely: **no parser was run on
any evaluation or calibration corpus, and no prediction was generated.**

It is not the claim that no parser function executed anywhere in this
repository's test run. The pre-existing unit suites — `test_eval_parsing_v2.py`,
`test_eval_parsing_v3.py`, and several others — import parser modules and
exercise parser functions against **public synthetic fixtures** that are checked
into the repository. Running the full test suite therefore executes parser code.
That is unit testing of a public component, not evaluation: the fixtures are not
a locked set, they carry no sealed labels, nothing is scored, and no result is
recorded against any evaluation ordinal.

This is disclosed rather than glossed because the two claims are easy to
conflate, and the conflation runs in the dangerous direction — a reader who
takes "no parser was run" literally and then discovers parser code executing in
CI would be right to distrust the rest of the record. Relatedly, and for the
same reason, the parser-isolation claim about the repair modules remains
bounded: `jspace_observation/__init__.py` eagerly imports the legacy parser, so
package import is **not** parser-free and no document here says it is. What is
claimed and tested differentially is narrower — the repair modules introduce no
*new* parser dependency, reference no parser symbol, and invoke no parser.

`L-32` is preserved: a sealed member list and `sealed_object_count` require an
authenticated seal-time observation and are not facts an offline prospective
policy can derive. `L-35` and `L-36` are added — the premise-dependence of the
zero, and the gap between a conforming instrument and a demonstrated-adequate
one.

## 10. Next gate

A **separately authorized independent set-repair round** for `parser-v3-v2`.

`READY_FOR_INDEPENDENT_SET_REPAIR` means the acceptance rule is settled well
enough for that round to begin. It authorizes nothing else. Case construction,
migration of the 105 cases, review or replacement of the 15 quarantined cases,
manifest generation, sealing, authorization locks, image construction,
preregistration, Stage P and Stage E all remain unauthorized.
