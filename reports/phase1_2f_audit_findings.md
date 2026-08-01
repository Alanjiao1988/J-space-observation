# Phase 1.2F — Independent audit findings

Round: Phase 1.2F, parser acceptance-policy correction and threshold
preregistration.
Baseline commit: `d843984a3b7e1a2bf9d306621b8557ce327cf987`.
Terminal status of the round: `BLOCKED_ON_ACCEPTANCE_POLICY`.

---

## 0. What "independent" means here, and what it does not

Two read-only review agents were run after the round's first draft was complete
and before any of it was committed. Each was given the repository, the draft
artifacts, and a scope; neither was given the round's conclusions to confirm.
Neither wrote to the repository.

That is the extent of the independence claim, and it is worth stating its
limits plainly:

* Both auditors are language models, not human reviewers, and both were
  commissioned by the same author whose work they audited.
* They read the same repository the author read. A shared blind spot in the
  source material remains a shared blind spot.
* Every fix recorded below was authored by the round's author, not by the
  auditor who found the defect. No auditor re-verified the full remediation.
* **The tests added in this round are self-authored. Passing them is not
  independent validation of anything.** A self-written test encodes the
  author's understanding of correctness; where that understanding was wrong,
  the test was wrong with it. That is exactly what happened — see A2 and B1,
  both of which passed a full green suite before an auditor read them.

Where a finding was reproduced by the author from primary evidence rather than
accepted on the auditor's word, this is stated in the row. Where it was
accepted on argument alone, that is stated too.

**Audit A** — methodology and statistics: challenge-set versus IID
interpretation, independence and redundancy of the four thresholds, the
confusion-matrix analysis, downstream-error-budget logic, comparator-margin
semantics, candidate and set independence, and post-hoc number selection.
10 findings: 2 BLOCKER, 3 MAJOR, 3 MINOR, 2 OBSERVATION.

**Audit B** — repository and instrument consistency: the Phase 1.0C factual
corrections, current-state consistency, policy/compiler agreement, frozen
instrument bindings, parser-isolation wording and tests, v1/v2 namespace
provenance, L-32 treatment, protected hashes, and the private-access boundary.
16 findings: 0 BLOCKER, 6 MAJOR, 7 MINOR, 3 OBSERVATION.

Audit A's summary judgement was that the round reached the right terminal
status **for materially wrong reasons**. That judgement is accepted. It is the
single most important thing in this document, and it is the reason the round
is being committed with a blocked status rather than a green one.

---

## 1. Audit A — methodology and statistics

### A1 — Two published macro-F1 spread values are unattainable

**Severity:** MAJOR. **Disposition:** ACCEPTED, FIXED.

`docs/phase1_2f_threshold_dispositions.json` published
`"10_errors": [0.866667, 0.930233]` and `"20_errors": [0.783383, 0.869048]`.
The upper figures are not attained by any feasible confusion matrix under the
round's own enumeration model; they were computed from a relaxed model and then
reported as extrema of the strict one.

**Reproduced independently.** `recompute.py` re-derived every spread from the
enumeration directly. True attained extrema, with the corrected 40-case free
population: 10 errors `[0.866667, 0.930159]`; 20 errors `[0.783355, 0.869048]`;
30 errors `[0.708791, 0.811966]`; 40 errors `[0.636895, 0.755556]`.

**Fix.** Disposition artifact regenerated from the enumeration rather than
transcribed. A test now recomputes all four spreads and asserts each endpoint is
attained by a named matrix, so a future transcription error fails rather than
publishes.

**Residual limitation.** The spreads are correct for the registered supports
(80/30/10) and the corrected free population (40). They are not general facts
about macro F1; changing the supports invalidates all six numbers.

---

### A2 — No gate declares what counts as an error; the gate-coverage baseline was wrong (BLOCKER)

**Severity:** BLOCKER. **Disposition:** ACCEPTED, FIXED — and this finding
changed the round's substance, not merely its numbers.

No gate in the v2 policy declared an error *definition*. The field
`maximum_errors` was therefore read three mutually incompatible ways within a
single artifact, and the 90/30 pinned/free split depended on the most generous
of the three readings being applied to S06.

The only **registered** S06 gate condition is narrow:
`registered_rightmost_distractor_span_selected`. It pins one specific failure
mode; it does not pin S06's exact typed decision. S06 is therefore **free**, not
pinned.

**Reproduced independently** against the policy's own gate list and the v1
stratum definitions. Corrected baseline:

* pinned by a zero-error gate on exact typed decision:
  S01, S02, S03, S07, S08, S10, S11, S12 = **80 cases**
* free: S04, S05, S06, S09 = **40 cases**

Every downstream figure moved: the confusion-matrix enumeration domain from 496
matrices to **861**, and the macro-F1 minimum from 0.708791 to **0.636895**,
attained at (16, 24).

**Fix.** Each gate now carries explicit error semantics — `error_scope`,
`error_definition`, `counting_unit` — and the validator's new
`_validate_gate_semantics` refuses a gate that omits them. All derived figures
were recomputed from the enumeration, not adjusted. The 80/40 baseline is
recorded in the policy, the protocol, the report, the disposition artifact and
the tests.

**Residual limitation.** The corrected baseline is a reading of the *registered*
gate text. If a future round widens the S06 gate, S06 becomes pinned and the
enumeration domain shrinks again. The figure 861 is conditional on the gate set
as registered at this commit, and the tests pin it to that gate set.

---

### A3 — The named blocking dependency was not the blocker, and its defence was circular (BLOCKER)

**Severity:** BLOCKER. **Disposition:** ACCEPTED, FIXED — this finding changed
what the round says its next gate is.

The policy's machine-readable `blocking_dependency` named the absent downstream
parser-error budget. The protocol simultaneously conceded that a
`LOGICAL_INVARIANT` basis would supply the value without any budget at all. Both
cannot be true. Worse, the argument offered for the concession was circular: the
*absence* of a stricter gate was offered as evidence that no stricter gate is
warranted.

The practical consequence was severe. Executing the registered calibration
protocol — an expensive, multi-week design — would have left the round **still
blocked**, because the prior question was never asked.

**Reproduced independently** by reading the two artifacts side by side; the
contradiction is textual, not statistical.

**Fix.** `blocking_dependency` is now a structured, **ordered** record:

1. **Primary.** The instrument-strictness decision on the designed-failure
   strata S04, S05, S06, S09 has not been taken. If the answer is "zero errors
   tolerated", the threshold follows as a `LOGICAL_INVARIANT` and no budget is
   needed at all.
2. **Secondary, conditional.** Only if non-zero tolerance is permitted does the
   absent downstream error budget become the blocker.

The protocol, the report and the current-state documents now state the ordering
in that direction, and the round's declared "exact next gate" is the
strictness decision — not the calibration.

**Residual limitation.** The strictness decision is a scientific judgement about
what the designed-failure strata are *for*. This round does not take it, and
deliberately so: taking it while four development results are already known
would be exactly the post-hoc selection the round exists to prevent.

---

### A4 — Two of three comparator-retention reasons do not hold

**Severity:** MAJOR. **Disposition:** ACCEPTED, both reasons WITHDRAWN.

The round gave three reasons for retiring the parser-v2 non-regression gate and
asserted "any one sufficient". Two do not survive scrutiny, and the surviving
one is defeated by a margin-free reformulation the round had not considered.

**Fix.** The two unsound reasons are struck from the protocol and the policy,
marked as withdrawn rather than deleted. The margin-free formulation
(strict per-case dominance: parser v3 correct wherever parser v2 is correct)
was then considered on its merits and recorded as `REJECTED_ON_SUBSTANCE` —
it is a coherent gate, but on a 120-case quota-constructed adversarial set it
would make acceptance turn on the comparator's incidental behaviour on cases
designed to defeat both parsers. The disposition is unchanged; the reasoning
supporting it is now sound.

**Residual limitation.** "Rejected on substance" is a judgement, not a proof. A
future round may reinstate per-case dominance with a better argument. The
withdrawal record exists so that argument starts from an honest baseline.

---

### A5 — Vacuous PASS: with zero binding criteria, PASS reduces to gates-only

**Severity:** MAJOR. **Disposition:** ACCEPTED, FIXED. Independently confirmed
by Audit B as **B6**.

`status_logic.PASS` read "every mandatory gate satisfied AND every binding
acceptance criterion satisfied". With all four thresholds retired and zero
binding criteria, both `compile_contract` refusal conditions clear and PASS
reduces to gates-only — leaving the free-population cases (40, under the
corrected baseline) entirely unconstrained while the artifact still presents
itself as an acceptance policy.

This is a hole the round *created*, not one it inherited.

**Fix.** Two independent guards, both tested:

* a retired threshold's declared successor must itself be binding, so retirement
  cannot launder a criterion out of existence;
* the policy must declare at least one binding acceptance criterion before it
  can be `FINAL`.

Because the shipped policy has zero binding criteria, the second guard is
precisely why it cannot reach `FINAL` in this round. The hole is closed by
making it a blocking condition rather than by inventing a criterion to fill it.

**Residual limitation.** The guards are structural. They ensure *a* binding
criterion exists; they cannot judge whether it is the *right* one.

---

### A6 — `PROHIBITED_BASIS_SOURCES` is far weaker than the documentation claimed

**Severity:** MINOR as filed; treated as MAJOR because the over-claim is the
same class of defect the round exists to correct. **Disposition:** ACCEPTED,
FIXED on both sides. Independently confirmed by Audit B as **B7**, and its
documentation consequence as **B8**.

The prohibited-basis scan held five substrings, was applied to one field, and
only to some items — while `paper/methods_ledger.md` and the disposition
artifact described it as machine enforcement of the full disallowed-basis list.

**Fix, code side.** The needle list is now 22 entries; normalisation collapses
whitespace, hyphenation and case before matching; the scan runs over every
declared prose field of every threshold record regardless of disposition, and
descends into nested structures.

**Fix, prose side — and this is the more important half.** `L-33`,
`paper/methods_ledger.md` and the implementation report now state what a string
scan can and cannot do: it catches a disallowed basis that is *named*; it cannot
catch one that is paraphrased, implicit, or simply undeclared. The substantive
guarantee is a review guarantee. The code is a backstop against the naive
failure mode, not a proof of provenance.

**Residual limitation.** Stated above, deliberately, in the shipped artifacts.
A determined author can still write a prohibited basis in words the scanner does
not hold. Nothing in this round changes that.

---

### A7 — Independence flags are not truth-apt on a null value

**Severity:** MINOR. **Disposition:** ACCEPTED, FIXED.

`candidate_independence` and `set_independence` were asserted `true` on
thresholds whose `value` is `null`. A value that does not exist cannot have been
derived independently of anything; the flags assert a property of a
non-existent object.

**Fix.** On a record with `value: null` the flags now carry
`not_applicable_value_absent`, and the validator refuses a bare `true`.

---

### A8 — Non-vacuity gates cannot forbid presence-class collapse

**Severity:** MINOR. **Disposition:** ACCEPTED, claim WITHDRAWN.

`relationship_to_existing_gates` claimed the three non-vacuity gates plus the
five zero-error stratum gates "already forbid presence-class collapse directly
and at zero tolerance". A non-vacuity gate requires that a class be predicted at
least once; it does not forbid collapse of the remaining mass into a single
class.

**Fix.** The claim is withdrawn and replaced with what the gates actually
establish. The macro-F1 disposition does not depend on the withdrawn claim —
the enumeration argument stands on its own — so the disposition is unchanged.

---

### A9 — "No registered error budget" is true, but a decision rule *is* registered

**Severity:** OBSERVATION. **Disposition:** ACCEPTED, qualified.

The auditor independently searched `docs/`, `paper/` and `reports/` for an
error budget and confirmed the round's central negative claim: none exists.
This is the finding that makes `BLOCKED_ON_ACCEPTANCE_POLICY` the honest status,
and it was reached by a reader who did not know the round's conclusion.

The qualification: `docs/phase1_capability_headroom_protocol.md:228-229,252`
*does* register a decision rule D. It is not an error budget and cannot serve as
one — it concerns target-model headroom, not parser-induced distortion — but the
unqualified claim "nothing downstream is registered" was too strong.

**Fix.** The report now states the narrow, accurate version: no registered
*parser-error* budget exists; a downstream decision rule exists but is not one,
with the reason given.

---

### A10 — No number in the policy was selected post hoc

**Severity:** OBSERVATION. **Disposition:** ACCEPTED as a negative result.

The auditor verified programmatically that all five thresholds carry
`value: null`, and that every number remaining in the policy is either a
registered design fact (120 cases, 12 strata, 10 per stratum, the 40/50/90/30
design splits, the supports 80/30/10) or a figure derived from the enumeration.

This is the round's one clean result and it should not be overstated: it says no
number was selected to permit a pass, because **no number was selected at all**.

---

## 2. Audit B — repository and instrument consistency

### B1 — The new consistency checker would not have caught the defect it exists to prevent

**Severity:** MAJOR. **Disposition:** ACCEPTED, checker REWRITTEN.

The checker missed the verbatim Phase 1.2E defect in `docs/thread_handoff.md`,
one of its own two registered files, because the repository's markdown is
hard-wrapped and the checker matched within single lines.

**Reproduced independently** by running the old checker against the verbatim
`d843984` text: **0 findings** in its 2 registered files.

**Fix.** Rewritten to build paragraph windows split on blank lines, with
whitespace collapsed and a character-index-to-line-number map so reporting stays
precise. Against the same baseline text the rebuilt checker reports **12
findings across 5 files**.

---

### B2 — Exemptions were a substring word-list and were trivially abusable

**Severity:** MAJOR. **Disposition:** ACCEPTED, FIXED.

`EXEMPT_MARKERS` was a per-line substring test on common words, so any paragraph
that happened to contain an exemption word anywhere was silently excused. The
auditor supplied eight constructed strings that should fail and did pass, two of
them literal quotations of the Phase 1.2E error.

**Fix.** Exemption is now **structural**: a blockquote, or an `EXEMPT_ANCHORS`
regex anchored at line start after list/heading/bold markers. Verified: all
eight evading strings are now caught, and all five legitimate errata in the
repository remain exempt.

---

### B3 — The checker never scanned the artifact class where the defect occurred

**Severity:** MAJOR. **Disposition:** ACCEPTED, FIXED.

The checker's own docstring named the policy JSON as the site of the failure,
then scanned only markdown.

**Fix.** JSON artifacts added to `CURRENT_STATE_FILES` with a structured walker
that yields one window per leaf string — necessary because pretty-printed JSON
has no blank lines and would otherwise collapse into a single window — plus
key-path exemption for subtrees that legitimately quote the defect
(`errata`, `withdrawn_argument`, `as_written`, and similar).

---

### B4 — `phase_1_0c_was_finalized` failed open; `EXECUTED_PATTERNS` was dead code

**Severity:** MINOR. **Disposition:** ACCEPTED, FIXED.

The ground-truth helper returned `False` when it could not establish the fact,
so a checker that lost its evidence would report success. `EXECUTED_PATTERNS`
was defined and never used.

**Fix.** The helper now raises `GroundTruthError` — fail-closed.
`EXECUTED_PATTERNS` is wired into a `NOT_RUN_VS_CITED_RESULT` finding kind.

---

### B5 — A non-string `status_logic` clause bypassed the re-entry check entirely

**Severity:** MAJOR. **Disposition:** ACCEPTED, FIXED.

The guard proving that removed and report-only metrics cannot silently re-enter
PASS/FAIL logic inspected string-valued clauses only. A list-valued clause
bypassed it in one line, and so did several plain prose spellings.

**Fix.** `_collect_clause_text` now recursively collects text from **all**
non-reserved keys of `status_logic`, whatever their type, and the prose
spellings are covered.

---

### B6 — Duplicate of A5

Independently found by both auditors. See A5. Fixed by the successor-must-bind
and at-least-one-binding-criterion guards.

---

### B7 — Duplicate of A6 (code side)

See A6.

---

### B8 — `L-33` asserted the validator rejects five bases; it rejects two

**Severity:** MAJOR. **Disposition:** ACCEPTED, FIXED.

The limitation ledger over-claimed enforcement — the same failure mode the round
correctly diagnosed for the parser-isolation claim, committed by the round
itself, in the ledger entry describing its own instrument.

**Fix.** `L-33` rewritten to state the real scope and the real limits of a
string scan. A new `L-34` records the consistency checker's own limitations in
the same honest register: what it detects, what it cannot detect, and that its
exemption model is structural rather than semantic.

---

### B9 — Return-type annotation contradicted the return value

**Severity:** MINOR. **Disposition:** ACCEPTED, FIXED.

`validate_acceptance_thresholds` was annotated `-> None` while returning a value
that `validate_policy` depends on. Corrected to `-> set[str]`.

---

### B10 — A `REVIEW_REQUIRED` item could declare `binding: true`

**Severity:** MINOR. **Disposition:** ACCEPTED, FIXED.

A criterion whose disposition is "we have not decided" could nonetheless be
declared binding on acceptance. The validator now refuses that combination.

---

### B11 — `sealed_object_count 12` asserted as a bare state-table fact

**Severity:** MINOR. **Disposition:** ACCEPTED, ANNOTATED.

The Phase 1.2E state block in `docs/thread_handoff.md` lists
`sealed_object_count 12` beside genuinely derived counts, with no marker,
although `L-32` says explicitly that `12` is the figure the Phase 1.2D erratum
exists to qualify.

**Fix.** The historical block is preserved verbatim; a Phase 1.2F erratum
immediately below it records that the figure is an **operator assertion**, not a
set-derived fact, and that `L-32` governs. The new Phase 1.2F state block omits
the field rather than restating it.

---

### B12 — `reports/current_status.md` still presented Phase 1.2E as the current round

**Severity:** MAJOR. **Disposition:** ACCEPTED, FIXED.

The banner and "Current Phase" line were stale — and an under-updated
current-state header is precisely the mechanism that produced the Phase 1.2E
defect this round exists to correct.

**Fix.** Banner, "Current Phase" line and all four figure blocks updated,
including the 90/30 → 80/40 and 496 → 861 corrections.

---

### B13 — `docs/thread_handoff.md` had no Phase 1.2F handoff

**Severity:** MAJOR. **Disposition:** ACCEPTED, FIXED.

Its authoritative state block, terminal status and zero-ledger still belonged to
Phase 1.2E.

**Fix.** A full Phase 1.2F handoff block appended: terminal status, ordered
blocking dependency, zero-ledger, protected-digest result, and the exact next
gate. Notably, the rebuilt consistency checker immediately flagged the author's
own verbatim quotation of the defect inside that new block; it was anchored as a
blockquote and the check returned clean. The instrument caught its author on its
first real use.

---

### B14 — Dangling cross-reference

**Severity:** MINOR. **Disposition:** ACCEPTED, FIXED — by this document, which
is the file that was missing.

---

### B15 — A file was claimed to be on the protected-digest list when it was not

**Severity:** MINOR. **Disposition:** ACCEPTED, FIXED by making the claim true.

`docs/phase1_parser_v3_v2_stratum_policy.md` asserted that
`evaluator_sets/parser_v3_v1/strata_definitions.md` is on the protected-digest
list. It was not.

**Fix.** The file's LF-normalised SHA-256 (`25d59eb0…`) was added to
`PROTECTED_DIGESTS`, and the prose now says that Phase 1.2F added it and that
it was not there before. Adding a digest strengthens protection; it relaxes
nothing. The file's bytes are unchanged from `ee0c720`.

---

### B16 — Duplicate of A1, plus "no test checks these values"

**Severity:** MINOR. **Disposition:** ACCEPTED, FIXED. See A1; the missing test
is the second half of that fix.

---

## 3. Cross-audit synthesis

Both auditors independently found the vacuous-PASS hole (A5 / B6) and the
prohibited-basis over-claim (A6 / B7). Convergence from two differently scoped
reviewers raises confidence in those two.

The two audits divided cleanly otherwise: Audit A found that the round's
*numbers and reasons* were wrong (A1, A2, A3, A4), Audit B found that its
*instruments and documents* did not do what they said (B1, B2, B3, B5, B8, B15).
No finding from either audit was rejected. Two claims made **by the round** were
withdrawn on audit (A4, A8), and one was narrowed (A9).

Audit B correctly flagged that the 90/30 → 80/40 correction from Audit A
invalidated the specific numbers in B16 and could move B6. Both were
re-verified against the recomputed policy before commit, and every figure in the
shipped artifacts was regenerated from the enumeration rather than edited.

> **Erratum (Phase 1.2G).** The last clause is false as written. The
> *enumeration* figures were regenerated. The *coverage* figures were not
> propagated: at commit `3d519e1` the 90/30 split survived in
> `docs/phase1_parser_v3_v2_stratum_policy.md` §5 (which additionally listed
> S06 as pinned), throughout
> `docs/phase1_2f_parser_error_budget_calibration_protocol.md`, and inside the
> residual criterion's own `metric_definition`, `numerator` and
> `failure_risk_controlled`, which described three strata while the structured
> population declared four.
>
> The claim was made because the policy JSON — the artifact under active edit —
> was regenerated, and the check went no further. That is precisely the failure
> mode this document elsewhere warns about: a verification scoped to the file
> the author was looking at.
>
> Phase 1.2G corrected all of it, and made recurrence a validation error rather
> than a review question: coverage is now derived once in
> `derive_gate_coverage`, the policy's restatement must agree with the
> derivation, and the residual criterion's prose is checked against its own
> declared population.

### What the audits did not do

* Neither re-verified the remediation. Findings were fixed by the author.
* Neither had access to sealed inputs, labels, or private curator material, and
  neither was permitted to run a parser. Their scope was public artifacts.
* Neither can establish that the *retained* reasoning is correct — only that the
  specific defects they found are real. Absence of further findings is not
  evidence of absence.

### The most consequential finding

A2 and A3 together. The round's first draft reached
`BLOCKED_ON_ACCEPTANCE_POLICY` — the correct answer — while naming the wrong
blocker, publishing a wrong gate-coverage baseline, and pointing at a next step
that would not have unblocked anything. A green test suite of self-authored
tests passed throughout.

That is the record's clearest evidence for a claim this project makes elsewhere:
self-authored tests are not independent validation.

---

## 4. Defect found after the audits closed

One further defect was found during remediation, by the rebuilt consistency
checker acting on the author's own text, after both audits had reported. It is
recorded here because a findings report that lists only what the auditors caught
would misrepresent how the round actually went.

**C1 — Markdown emphasis defeated every contiguous phrase pattern.**
**Severity:** MAJOR. **Disposition:** FIXED.

The rebuilt checker collapsed whitespace but did not elide markdown emphasis
delimiters. `**not**` therefore inserted asterisks into the middle of phrases
the patterns match as contiguous text.

The visible symptom was benign: a false positive on the round's own corrective
sentence *"Phase 1.0C is **not** parser calibration"*, because the negation
guard could not see the negation. The serious form is the mirror image —
`Phase 1.0C has **not** been run` would have **passed** the check. A stale
claim could have been emphasised into invisibility, in a repository that writes
`**not**` constantly.

**Fix.** `*` and backtick are elided before matching, in both the markdown
paragraph windows and the JSON leaf-string windows. `_` is deliberately *not*
elided: it is load-bearing inside `NOT_RUN` and `sealed_object_count`. Four
regression tests cover the evasion direction, two cover the false-positive
direction, and one pins the `_` exclusion. The checker was then re-proved
against the verbatim `d843984` text: 12 findings across 5 files, all eight
Audit-B evading strings still caught, all five legitimate errata still exempt.

**Residual limitation.** Recorded in `L-34`. The general point is that a matcher
over rendered prose is sensitive to markup carrying no meaning, and no amount of
pattern tuning converts it into a semantic check.

**Why this matters for the audits.** Audit B found three defects in the
checker's first version (B1, B2, B3) and did not find this one, in a rewrite it
never saw. Two independent audits plus a self-check found four defects in one
small script. That is the correct prior for how many remain.
