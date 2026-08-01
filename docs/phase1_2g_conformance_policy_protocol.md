# Phase 1.2G protocol — Post-audit consistency remediation and deterministic conformance-policy finalization

Status: `EXECUTED`
Phase: 1.2G
Supersedes: nothing. Extends `docs/phase1_2f_parser_acceptance_policy_protocol.md`.
Baseline: `origin/main` at `3d519e1`
Private data accessed: none
Parser invocations: 0
Predictions generated: 0

---

## 0. What this round is

Phase 1.2F produced a corrected historical record and an audited threshold
analysis, and terminated `BLOCKED_ON_ACCEPTANCE_POLICY`. It blocked on a
question it was right not to answer by invention: whether the four
designed-failure strata admit any exact typed-decision error tolerance.

Phase 1.2G does two things.

1. It **settles that question by decision**, and derives the consequence.
2. It **remediates ten consistency defects** that Phase 1.2F's own audits and
   post-round review surfaced, and closes the mechanism that produced most of
   them.

It is a policy, tooling, testing and documentation round. It runs no experiment,
reads no private data, invokes no parser, generates no prediction, constructs no
set, and creates no Azure resource.

## 1. The normative premise

> **Strict finite-suite conformance.** The future `parser-v3-v2` evaluation set
> is a finite conformance suite, not a sample from a deployment population.
> Every case admitted to it is admitted because a correct instrument is required
> to handle it. Every admitted case is therefore a mandatory conformance
> example, and an exact typed-decision mismatch on any admitted case is
> unacceptable instrument behaviour.

This premise is a design decision, taken by the operator and recorded in
`docs/decision_log.md`. It is not a measurement and no observation licenses it.

### 1.1 The consequence

Given the premise, the residual exact-typed-decision budget over the strata that
the mandatory gates do not already pin is `0`. This is a `LOGICAL_INVARIANT`:
it follows from what the set is, not from a judgement about how bad an error
would be.

The argument is short and is meant to be. Admission makes each case carry a
requirement *of its own*: for every admitted case `c`, the instrument must
reproduce the reference typed decision on `c`. An aggregate tolerance `B > 0`
does not weaken that requirement, it contradicts it — a universally quantified
obligation admits no exception count at all, so permitting `B` violations
somewhere is a statement that the obligation does not hold of every case.

The objection that an aggregate budget need not name a subset is answered
directly: the defect is not that the permitted cases are unnamed. "At most one
mismatch anywhere" is perfectly well defined without naming anything. The defect
is that *any* exception count is the negation of a per-case obligation. So `0`
is not a strict choice among available values but the only value the premise
supports.

### 1.2 Bases the derivation must not use

The derivation is constrained, and the constraint is enforced by test. It must
not appeal to:

* the parser being deterministic — determinism makes an error reproducible, not
  acceptable;
* the set not being an IID sample — true, and irrelevant to tolerance;
* the absence of a registered downstream error budget — an absence of evidence
  is not a derivation;
* conservatism, caution, or strictness-when-unsure — a disposition, not a basis;
* the number zero being tidy, clean, round or simple;
* parser-v2 precedent — textual substitution from a predecessor is a disallowed
  basis under the Phase 1.2F rules and remains one;
* any expectation about how parser v3 will perform.

`tests/test_parser_v3_acceptance_policy.py` scans the recorded derivation text
for appeals to these and fails if one appears.

### 1.3 The falsifier

The premise is recorded together with the observation that would refute it.

> If a case is admitted to the set that a correct instrument is **not** required
> to handle — an aspirational case, a case included to observe behaviour rather
> than to require it, or a case whose own reference label is uncertain — then
> the premise fails, the invariant loses its basis, and the value must be
> re-derived rather than inherited.

Eligibility for admission and "must be handled correctly" must remain the same
predicate. This is a constraint the later set-repair round inherits. It is
recorded as `L-35` in `paper/limitations_ledger.md`.

### 1.4 What the decision is not

It is not a claim that parser v3 can meet the policy. The policy became
**stricter** in this round. It is not a result, not a prediction, and not an
authorization to evaluate anything.

## 2. The ten seed defects

Phase 1.2G opened with ten defects, `G-01` … `G-10`. They are **consistency
failures between this project's own artifacts**, not findings about the
evaluation instrument. They are deliberately not numbered into the historical
`H1`–`H9` series, which is unchanged; `H9` in particular remains specifically
about disagreement among declared and observed artifact vocabulary, support and
set facts.

| ID | Quoted defect |
| --- | --- |
| `G-01` | Residual-population prose disagreed with the structured population it described |
| `G-02` | `docs/phase1_parser_v3_v2_stratum_policy.md` carried the superseded 90/30 split and described `S06` as pinned |
| `G-03` | The calibration protocol still specified 30 cases across three strata, and a budget range of 0–30 |
| `G-04` | The Phase 1.2F report's §15 stated a next gate in the wrong order, implying calibration preceded the decision |
| `G-05` | The synthetic policy fixture asserted "30 cases in S04, S05 and S09" |
| `G-06` | The withdrawn comparator argument was still asserted live in `paper/methods_ledger.md` |
| `G-07` | `reports/phase1_2f_audit_findings.md` claimed every figure had been regenerated; several artifacts contradicted it |
| `G-08` | Focused-suite totals recorded as 201 and 242 where the round's transcript shows 249 |
| `G-09` | The per-stratum cap existed only in prose, with no machine-readable field |
| `G-10` | `PROTECTED_DIGESTS` holds 12 entries; the report said 11 |

Each is remediated, and each has a regression that fails if it returns.

## 3. Required structural changes

### 3.1 The policy JSON is canonical

`docs/phase1_parser_v3_v2_evaluation_policy.json` declares itself the canonical
machine-readable statement of the prospective acceptance policy. Where a report,
protocol, ledger or code comment disagrees with it, the policy governs and the
other artifact is defective. Its schema moves to
`phase1-parser-v3-prospective-evaluation-policy/v3`.

### 3.2 One production coverage derivation

Exact-typed-decision coverage is **derived**, not declared. The single
production implementation is
`jspace_observation.parser_v3_repair_contract.derive_gate_coverage`. Both
`validate_policy` and `compile_contract` consume it. The policy's
`gate_coverage_analysis` block is a restatement that the validator requires to
agree with the derivation; it is not an input.

The derivation reads each gate's registered error definition from
`GATE_ERROR_DEFINITIONS`, a closed, code-owned registry recording, for each
definition, its scope, its counting unit, whether it pins exact typed-decision
agreement, and why. An unknown definition is refused; a policy that restates a
registry entry incorrectly is refused. The derivation is fail-closed: a gate
whose population cannot be resolved to a stratum set raises rather than
defaulting to "covers nothing".

The authoritative figures it yields are:

* **pinned, 80 cases**: `S01`, `S02`, `S03`, `S07`, `S08`, `S10`, `S11`, `S12`;
* **residual, 40 cases**: `S04`, `S05`, `S06`, `S09`.

`S06` is residual. Its dedicated gate registers exactly one error definition,
`registered_rightmost_distractor_span_selected`, which forbids one specific
wrong span and does not entail exact typed-decision agreement.

### 3.3 Generated current state

`scripts/generate_current_state.py` renders the current-state block of
`reports/current_status.md` and `docs/thread_handoff.md` from the canonical
policy and the production derivation, between sentinel comments. `--check`
re-renders and compares bytes; `--write` regenerates.

This is the structural answer to the defect class that produced six of the ten
seed defects. A prose scanner can only reject sentences someone thought to
pattern-match; a rendered figure cannot go stale because it is never typed.
`scripts/check_current_state_consistency.py` is retained as the backstop for
claims that are not figures, and gains a superseded-figure check and a
calibration-protocol status check.

### 3.4 Both pooled and per-stratum limits

`residual_critical_exact_budget` carries disposition `KEEP_HARD` and is the one
binding numeric criterion this round finalizes. It states
`limits.pooled_max_errors = 0` **and**
`limits.per_stratum_max_errors` of `0` for each of `S04`, `S05`, `S06`, `S09`.

These are arithmetically equivalent today. They are both recorded because they
are not equivalent under amendment: an editor relaxing one stratum while holding
the pool produces an inconsistency the validator can catch, whereas a pooled-only
policy would admit the change silently.

## 4. Dispositions of the other four metrics

| Threshold | Disposition | Reason |
| --- | --- | --- |
| `overall_exact_typed_decision_minimum` | `REPLACE_HARD`, non-binding | With all 120 cases pinned it can never bind. Its content is carried by the successor criterion, which is why this is a replacement rather than a deletion. |
| `critical_stratum_floor` | `MERGE_WITH_EXISTING_GATE`, non-binding | Same, over a subset; its per-stratum shape survives as `limits.per_stratum_max_errors` on the successor. |
| `answer_presence_macro_f1_minimum` | `REPORT_ONLY` | Exhaustive enumeration of the 861 feasible three-class confusion matrices at the registered supports shows it cannot see a wrong canonical value that preserves the presence class. |
| `non_regression_margin_vs_parser_v2` | `REPORT_ONLY` | No prospectively choosable margin exists, and the one substantive argument for binding it was withdrawn in Phase 1.2F as unsound. |

The canonical dispositions live in
`docs/phase1_parser_v3_v2_evaluation_policy.json`; this table restates them and
is checked against it. A criterion that cannot fire must not be binding, so all
four carry `binding: false`.

A test proves that no removed or report-only metric can re-enter `PASS`/`FAIL`
logic.

## 5. Testing requirements

Phase 1.2G adds regressions for, at minimum:

* the conformance premise and its falsifier being recorded;
* the derivation never appealing to determinism, non-IID sampling, absence of
  calibration, conservatism, tidiness, parser-v2 precedent or expected
  performance;
* the production coverage derivation agreeing with the policy's restatement,
  and refusing when it does not;
* an unknown or misrestated gate error definition being refused;
* pooled and per-stratum limits both present, integral, non-Boolean and
  mutually consistent;
* a comparator margin of `0` being treated as a margin, not as absence;
* every one of `G-01` … `G-10` failing if reintroduced;
* the superseded-figure scanner catching each defect form and exempting errata;
* the current-state generator's `--check` failing on a hand-edited block;
* protected-file digest stability, with intentional changes declared.

No existing test may be weakened, removed, skipped or `xfail`ed. Where a Phase
1.2F test pinned the then-correct blocked state, it is **superseded by a
strictly stronger assertion**, with a docstring recording what it used to assert
and why the replacement is stronger.

## 6. Prohibitions

Unchanged from Phase 1.2F, and restated because they bind this round:

no sealed input, sealed label, private curator file, answer value, output text,
span, offset, case identity or case-level label may be read; no parser may be
run on any evaluation or calibration corpus; no prediction may be generated; no
case may be constructed, migrated, reviewed for replacement or sealed; no
manifest, authorization lock, evaluation state chain or evaluation image may be
created; Stage P and Stage E may not run; no Azure resource may be created,
modified or started; `parser-v3-v1` bytes, namespace, manifests and historical
invalid contract may not change; parser-v3 behaviour may not change;
`__init__.py` may not be refactored to make a stronger parser-isolation claim
true; and the calibration protocol may not be executed.

The zero-versus-non-zero tolerance question may not be re-asked of the operator.
It is settled.

## 7. Terminal states

* **`READY_FOR_INDEPENDENT_SET_REPAIR`** — the premise is recorded with its
  falsifier, the invariant is derived without a disallowed appeal, all ten seed
  defects are remediated with regressions, the policy and its comparator policy
  are `FINAL`, both audits and the post-remediation re-review are complete with
  no unresolved material finding, and the full suite is green.
* **`BLOCKED_ON_ACCEPTANCE_POLICY`** — anything above is unmet.

`READY_FOR_INDEPENDENT_SET_REPAIR` authorizes a separately authorized set-repair
round and nothing else.

## 8. Audit requirement

Two independent read-only audits, plus a **post-remediation re-review**. An
audit that sees only the pre-fix state and then accepts the author's claim of
remediation is not independent verification, and may not be described as such.
Findings are recorded with severity, disposition, fix and residual limitation in
`reports/phase1_2g_audit_findings.md`. Self-authored tests are not independent
validation.
