# Phase 1.2G — Independent audit findings, dispositions and re-review

Round: Phase 1.2G — Post-audit consistency remediation and deterministic
conformance-policy finalization.

Baseline commit: `3d519e1` (`origin/main` at round start).

Scope of this document: every finding raised by the two independent read-only
review agents commissioned under the Phase 1.2G brief, the disposition of each
finding, the concrete fix, and the residual limitation that survives the fix.
It closes with a post-remediation re-review conducted by a third agent that saw
the remediated tree rather than the seed tree.

This document is an audit record. It is not a claim that parser v3 was
validated, evaluated, improved, or scored. No evaluation occurred in this round.

---

## 1. Why this document exists

The Phase 1.2G brief required two things that a single author cannot supply
alone:

1. independent review of the round's methodology and of its repository
   consistency; and
2. a re-review *after* remediation, because an author who fixes the findings
   they were handed has not thereby been independently validated.

Self-authored tests are not independent validation. Neither is an author's own
statement that an audit finding was addressed. The audits below were performed
by read-only agents that could not edit the tree, and the re-review in §5 was
performed against the remediated diff.

The honest limit of this arrangement is recorded in §6: the reviewers are
language-model agents operating on the repository contents, not a human
methodologist and not a replication. Their agreement raises confidence; it does
not establish correctness.

---

## 2. Audit A — methodology and statistics

Charter: the conformance premise and its derivation, the independence and
redundancy analysis of the five candidate metrics, the confusion-matrix
enumeration, the comparator-margin semantics, candidate and set independence,
and whether any number was selected after observing behaviour it was supposed
to constrain.

### A-01 — BLOCKER — the derivation invoked prohibited grounds

Finding. The recorded derivation for `residual_critical_exact_budget` argued
from the determinism of the instrument, from the non-IID character of the
challenge set, and from the absence of a registered downstream error budget.
All three are disallowed bases under the round's own rules, and the brief
specifically requires the zero to follow from the conformance premise as a
`LOGICAL_INVARIANT` rather than from conservatism.

The audit further observed that the supporting argument was under-powered even
on its own terms.

Quoted defect: the derivation reasoned that a non-zero budget could not be
adopted because "no principled procedure can name which cases are permitted to
fail". The auditor correctly noted that an *aggregate* allowance of B > 0 does
not require naming a subset in advance. A budget of "at most one mismatch
anywhere in the residual population" is perfectly well defined without
identifying which case it will be spent on. The argument as written therefore
did not defeat the aggregate form of the objection it was raised against.

Disposition. Accepted in full. Rewritten.

Fix. The derivation was rewritten as a seven-step universal-implication
argument. Each eligible case admitted to the set carries its *own* conformance
requirement, because admission is what makes it a mandatory example. A
universally quantified per-case obligation is contradicted, not merely
weakened, by any aggregate allowance B > 0: an aggregate allowance is precisely
a statement that some case may fail its own requirement, and that statement is
the negation of the premise. The rewritten derivation explicitly disclaims the
four prohibited grounds by name and states that it does not rest on any of
them. A test scans the derivation text for appeals to determinism, tidiness,
conservatism and the absence of calibration.

Residual limitation. The zero is only as sound as the conformance premise it
follows from, and that premise was adopted by operator decision in this round
rather than derived from a prior artifact. This is recorded as a limitation in
the ledger. Anyone who rejects strict finite-suite conformance is not obliged
to accept the zero.

### A-02 — MAJOR — disposition labels disagreed across artifacts

Finding. The round report and the protocol described two of the five candidate
metrics as removed, while the canonical policy JSON recorded them as replaced
and merged. Since Phase 1.2G declares the policy JSON to be the single
machine-readable source of truth, the prose contradicted the artifact it was
supposed to describe.

Disposition. Accepted. The policy JSON is correct; the prose was wrong.

Fix. The disposition tables in §2 of the round report and §4 of the protocol
were corrected to `REPLACE_HARD` and `MERGE_WITH_EXISTING_GATE`, with an added
paragraph explaining why replacement and merger are the more honest labels: the
protective intent of both metrics survives inside another criterion, so calling
them "removed" would understate what the policy still enforces. The correction
credits findings A-02 and B1 in the text.

Residual limitation. None. The artifacts now agree, and a test asserts the
report's table against the policy.

### A-03 — MAJOR — per-stratum caps were only range-checked

Finding. The residual-criterion validator checked that each per-stratum cap
fell within an allowed range, but never checked the cap against the pooled
limit. A policy declaring a pooled limit of 0 together with a per-stratum cap
of 1 for S04 would validate, even though the two statements cannot both hold.
The round report claimed this combination was rejected. It was not.

Disposition. Accepted. The report's claim was false as written.

Fix. `_validate_residual_criterion` now rejects any per-stratum cap that
exceeds the pooled limit, naming the offending stratum. A regression test
constructs exactly the `pooled=0, S04=1` policy the report claimed was caught
and asserts that validation fails.

Residual limitation. The check enforces the relation between the pooled limit
and each individual cap. It does not enforce a relation between the pooled
limit and the *sum* of the caps, because the caps are ceilings rather than
allocations and a sum constraint would be a different policy decision.

### A-04 — MAJOR — status logic accepted registered comparator names

Finding. The validator rejected non-binding *threshold identifiers* appearing
in `PASS`, `FAIL` and `INVALID` logic, but did nothing about *comparator*
names. A comparator registered as report-only could therefore be referenced
from the pass condition and silently become an acceptance gate, which is the
exact failure mode the report-only disposition exists to prevent. Separately,
`status_logic.binding_criteria` was accepted as declared rather than verified
against the set of criteria actually marked binding.

Disposition. Accepted in full.

Fix. `validate_policy` now rejects any registered comparator name that appears
in `PASS`, `FAIL`, `INVALID` or `binding_criteria`, via a new
`_registered_comparator_names` helper that degrades safely on malformed input.
It additionally requires `binding_criteria` to be a non-empty list equal to the
computed set of criteria carrying `binding: true`. Regression tests cover a
comparator name injected into `PASS`, an empty `binding_criteria`, and a
`binding_criteria` that omits a binding criterion.

Residual limitation. The check is name-based. A policy that referred to a
report-only quantity by a paraphrase rather than by its registered identifier
would not be caught by this check, though it would still have to survive the
basis-type and derivation checks.

### A-05 — MAJOR — the coverage derivation admitted non-integer error limits

Finding. `derive_gate_coverage` decided whether a gate pinned a stratum by
testing `maximum_errors != 0`. In Python, `False != 0` is false and
`0.0 != 0` is false, so a gate whose limit was the boolean `False` or the float
`0.0` would be treated as a zero-error pinning gate. A malformed policy could
thus acquire pinned strata it had not earned.

Disposition. Accepted.

Fix. `maximum_errors` is now type-checked in the derivation. `None` is
permitted only for gates that do not claim to pin exact typed-decision
agreement — the three class-support gates legitimately carry `None`, because
they constrain support rather than errors. A pinning gate with `None` raises.
Every other value goes through `_require_int`, which rejects `bool` and
non-integral floats. `_require_int` gained an optional upper bound so it can
express an "at least N" requirement.

Residual limitation. None known for the value type. The derivation still trusts
the gate's declared `error_definition` prose to mean what it says; that
semantic step is human-checked, not machine-checked, and is the reason S06's
status had to be reasoned about rather than computed.

### Audit A — items verified as sound

The auditor independently reproduced and confirmed:

* the gate-coverage split of the 120-case set into a pinned majority and a
  four-stratum residual population of 40 cases;
* the count of feasible three-class confusion matrices under the registered
  supports, `C(42, 2) = 861`;
* the minimum attainable answer-presence macro F1 over that enumeration,
  `0.636895`, and the confusion matrix attaining it;
* that limitations `L-35` and `L-36` state the round's weaknesses honestly
  rather than defensively.

---

## 3. Audit B — repository and instrument consistency

Charter: the factual record, current-state consistency, agreement between the
policy and the compiler, frozen-instrument bindings, parser-isolation wording
and tests, namespace provenance, the treatment of limitation `L-32`, protected
digests, and the private-access boundary.

### B1 — MAJOR — duplicate of A-02

Disposition. Merged into A-02. Same fix.

### B2 — MAJOR — the policy's own sensitivity analysis contradicted its coverage

Finding. The `critical_stratum_floor` entry's sensitivity analysis and
rationale still described S06 as carrying a gate that pins exact typed-decision
agreement, which is inconsistent with the coverage derivation that the same
policy file drives. S06's registered error definition forbids selecting one
particular wrong span; forbidding one wrong answer is not the same as requiring
the right one.

Disposition. Accepted.

Fix. Both fields were rewritten to place S06 in the residual population and to
state why: a gate can be zero-error and still not pin exact typed-decision
agreement, if its error definition is narrower than "disagrees with the
reference decision". A scanner pattern now catches any future document that
places S06 among the pinned strata outside an erratum context.

Residual limitation. This is a semantic judgement about the meaning of one
registered error definition. It is recorded in the policy so that a future
reviewer can disagree with it explicitly rather than discover it by accident.

### B3 — MAJOR — seed defect G-05 survived in a test fixture

Finding. The synthetic threshold fixture in `tests/test_parser_v3_repair.py`
still declared the superseded residual population.

Quoted defect: the fixture's boundary population read "the 30 cases in S04, S05
and S09". Phase 1.2F corrected that population, and Phase 1.2G's whole coverage
derivation depends on the correction, so the fixture was carrying a figure the
repository had already retired.

The defect was dormant rather than active: the shipped policy no longer
contains a `REVIEW_REQUIRED` item, so the fixture's resolution loop currently
finds nothing to resolve. Dormancy is not correctness. The moment any future
round reopened a criterion, the fixture would have reintroduced the retired
population into a passing test.

Disposition. Accepted.

Fix. The fixture now declares the residual population as 40 cases across S04,
S05, S06 and S09, and its docstring records the defect, the audit finding, and
why a dormant wrong fixture is still a defect. The fixture file was added to
the superseded-figure scanner's target list so the same text cannot return.

Residual limitation. None.

### B4 — MAJOR — withdrawn arguments were stored as live text

Finding. The threshold-dispositions artifact stored two comparator arguments
that Phase 1.2F had already withdrawn as unsound, in a field that reads as a
live finding rather than as withdrawn history.

Disposition. Accepted.

Fix. The comparator row's summary field was reduced to the one surviving
argument. The two withdrawn arguments were moved into a structured
`withdrawn_arguments` list carrying the withdrawal reason, and
`withdrawn_argument` is a recognized exempt JSON key so the scanner treats the
subtree as history rather than assertion.

Residual limitation. None.

### B5 — MAJOR — stale schema binding and live `REVIEW_REQUIRED` prose

Finding. The dispositions artifact still bound to the `/v2` schema and still
described the surviving criterion as under review in three places, including
the top-level post-hoc disclosure and limitation `L-30`. Phase 1.2G finalized
that criterion, so the prose asserted a state the repository had left.

Disposition. Accepted.

Fix. The artifact was rebound to `/v3` with a `schema_version_history` note
recording the previous binding. The post-hoc disclosure was rewritten. `L-30`
was converted to past tense with a "Phase 1.2G update" blockquote rather than
being rewritten in place, preserving the original entry as history.

Residual limitation. None.

### B6 — MAJOR — the regression net had artifact-shaped holes

Finding. Several seed defects were fixed in the documents but had no
artifact-specific regression test, so a reversion would not fail anything. The
superseded-figure scanner's target list was also narrower than the set of
documents that carry the corrected figures.

Disposition. Accepted.

Fix. The scanner's target list was widened to include the Phase 1.2G protocol
and report, this audit report, the Phase 1.2F report, the methods ledger and
the repair test module. Artifact-specific regressions were added for the
remaining seed defects, including the corrected focused-suite total and the
size of the protected-digest registry.

Residual limitation. The regression net is pattern-based. It catches the
specific retired figures that are registered, not every possible way a future
document could be wrong.

### B7 — duplicate of A-05

Disposition. Merged into A-05. Same fix.

### B8 — duplicate of A-04

Disposition. Merged into A-04. Same fix.

### B9 — duplicate of A-03

Disposition. Merged into A-03. Same fix.

### B10 — BLOCKER — dangling cross-references

Finding. Two references pointed at files that do not exist. The Phase 1.2G
protocol cited the Phase 1.2F protocol under a filename containing an extra
path component, and the round report referenced this audit-findings report,
which had not been written.

Disposition. Accepted.

Fix. The protocol's citations were corrected to
`docs/phase1_2f_parser_acceptance_policy_protocol.md`. This document was
written. The consistency checker now reports a registered-but-missing file as a
contradiction, so a future dangling registration fails rather than shrinking
coverage silently.

Residual limitation. The missing-file check covers documents registered with
the checker, not every cross-reference in the repository.

### B11 — MINOR — coverage measured against a mutable module attribute

Finding. The generator tests iterated the module's own target tuple, so
shrinking that tuple would shrink test coverage while every test continued to
pass. The consistency checker skipped missing files silently, with the same
effect.

Disposition. Accepted.

Fix. The tests now assert the expected target set literally, independently of
the module, so removing an entry fails. The checker reports missing registered
files as described under B10.

Residual limitation. The literal expectation must be updated deliberately when
a target is legitimately added, which is the intended cost.

### Audit B — items verified as sound

The auditor independently confirmed:

* no test was skipped, marked expected-failure, deleted or loosened in this
  round;
* the protected-digest registry holds twelve entries and none changed;
* the public v2 stratum policy is correctly *not* in the protected registry,
  and the protected artifact is the retired v1 stratum definition file;
* the policy validates, and its coverage derivation reproduces the pinned and
  residual counts;
* the generator's `--check` mode and the consistency checker both report clean;
* the diff contains no parser invocation, no Azure interaction, and no private
  or sealed access.

---

## 4. Findings raised and rejected

None. Every finding from both audits was accepted, in whole or as a duplicate
of an accepted finding. Two findings (A-01, B10) were rated blocking and both
were remediated before commit.

---

## 5. Post-remediation re-review

An author who repairs the findings handed to them has not been independently
validated by the audit that produced them. A third read-only agent therefore
reviewed the remediated tree, with the finding list above as context and the
full diff as evidence.

Charter: confirm that each accepted finding is actually fixed in the artifact
it concerns rather than only described as fixed; confirm that the remediation
introduced no new contradiction; confirm that no test was weakened to
accommodate the new checks.

### 5.1 Verdict of the first re-review

**Not safe to commit.** Seven findings: one blocker, six major. Four were
partial-fix findings — a repair that closed the example the auditor gave while
leaving the class of defect open. Three were new defects introduced *by* the
remediation. This is the expected failure mode of author-repaired findings and
is the reason the re-review step exists.

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| R-A-01 | BLOCKER | The withdrawn "cannot name which subset" argument was still live in four documents, and the policy's first rejected alternative still cited the *absence* of a downstream error budget as grounds. | Fixed |
| R-A-04 | MAJOR | `_collect_clause_text` walked mapping values only, so `status_logic["FAIL"] = {"legacy_parser": "required"}` validated cleanly. | Fixed |
| R-B-06 | MAJOR | `paper/methods_ledger.md` still asserted the retired 90/30 split spelled out in words; the scanner patterns were numeric-only. | Fixed |
| R-B-10 | MAJOR | `check_calibration_protocol_is_superseded` returned no findings when its target file was absent. | Fixed |
| R-01 | MAJOR | The new quoted-defect-table exemption exempted the **whole table**, so a remediation cell could assert a superseded figure unseen; the `\|` added to the anchor prefix also exempted standalone rows. | Fixed |
| R-02 | MAJOR | Three current-state records still labelled two thresholds `REMOVE_REDUNDANT` against the canonical `REPLACE_HARD` / `MERGE_WITH_EXISTING_GATE`. | Fixed |
| R-03 | MAJOR | `reports/current_status.md` simultaneously stated that `parser-v3-v1` is `SEALED … RETIRED_AS_INELIGIBLE` and that the parser-v3 holdout is `NOT SEALED`. | Fixed |

### 5.2 R-A-01 — the withdrawn argument, second pass

The first remediation replaced the argument in the policy JSON but left it
standing in the protocol, the round report, the decision log and the
limitations ledger, where a later reader would have found the retired form
stated as current reasoning.

The valid argument is the **universal implication**: each admitted case carries
its own requirement, so an aggregate allowance of `B > 0` *contradicts* a
per-case obligation rather than weakening it. The defect is not that a budget
declines to name its subset — "at most one mismatch anywhere" names nothing and
is still incoherent — it is that a universally quantified obligation admits no
exception count at all. All four documents now state the valid form and
explicitly answer the aggregate objection.

The policy's `rejected_alternatives[0].reason` no longer appeals to the absent
downstream budget. An absent budget is an absence of evidence; deriving a
number from it would be choosing a value because nothing constrains it, which
is the prohibited basis this round exists to rule out.

Fix: four documents rewritten, `rejected_alternatives[0].reason` rewritten.
Tests: `test_a01_the_named_subset_argument_is_withdrawn_everywhere`,
`test_a01_the_rejected_alternative_does_not_cite_an_absent_budget`,
`test_a01_the_valid_form_of_the_argument_is_stated`.
Residual limitation: the withdrawal scan is a regex over paragraph windows. A
sufficiently different paraphrase of the retired argument would not be caught.

### 5.3 R-A-01 corollary — disclaimers must sit outside the argument

Remediating R-A-01 produced a second-order defect of its own. The rewritten
derivation disclaimed determinism, IID sampling and prudence *by name*, which
made it match the very scan that forbids appealing to them. Weakening the scan
to tolerate the disclaimer would have made the scan unable to see the real
thing.

The structural fix is to move every prohibited-ground disclaimer out of
`derivation` and into a sibling field, `derivation_excludes`, holding six
`{ground, why_not_used}` records. The derivation text is then a pure argument
and can be scanned literally.
Test: `test_no_excluded_ground_is_smuggled_back_into_the_argument` asserts that
`iid`, `deterministic`, `cautious` and `prudent` appear in none of
`derivation`, `numeric_derivation` or `controlled_risk`.

### 5.4 R-A-04 — mapping keys are clause text

`_collect_clause_text` recursed into mapping values and ignored keys, so a
comparator or a non-binding threshold referenced as a **key** in `status_logic`
passed validation. The walk now collects keys as well as values.
Tests: `test_a04_a_comparator_used_as_a_mapping_key_is_rejected`,
`test_a04_a_non_binding_threshold_used_as_a_mapping_key_is_rejected`,
`test_a04_the_clause_walk_collects_keys_and_values`.
Residual limitation: the check is name-based. A clause that reaches a
comparator without naming it — by index, or through an alias defined
elsewhere — is not detected.

### 5.5 R-01 — an exemption must be as narrow as its structure

Audit finding B2 established that an exemption must rest on a *structural*
signal rather than a reassuring word in prose. The remediation honoured that
and then over-applied it: a table whose header contained an exempt anchor in
any column was exempted **entirely**, so a "Remediation" cell in that table
could assert a retired figure and never be reported. Adding `|` to the anchor
prefix compounded it, exempting any standalone row that began with a cell
delimiter.

The principle is sharper than first stated: an exemption must be as narrow as
the structure that justifies it. A labelled *column* justifies exempting that
column, not the table. `_is_quoted_defect_table` was deleted and replaced with
per-column redaction — `_split_row`, `_quoted_columns`, `_redact_quoted_columns`
— and `|` was removed from `_ANCHOR_PREFIX`. `_windows` now blanks the anchored
columns and scans everything else.
Tests: `test_r01_only_the_quoted_column_of_a_defect_table_is_exempt` and four
siblings, including proof that the blockquote and erratum exemptions still work.

### 5.6 R-02 and R-03 — current-state records drifted from the canonical policy

Two classes of stale claim survived the first wave. `REMOVE_REDUNDANT` appeared
in `docs/thread_handoff.md`, `reports/current_status.md` and `docs/run_log.md`
after the canonical dispositions had become `REPLACE_HARD` and
`MERGE_WITH_EXISTING_GATE`. Separately, `reports/current_status.md` asserted
both that `parser-v3-v1` is sealed and retired and that the parser-v3 holdout
is not sealed.

Both are corrected, the construction record is now explicitly marked a
superseded point-in-time record, and both classes gained scanner patterns so a
recurrence fails the consistency check. Both patterns are registered
**non-negatable**. The stale seal claim contains the word "NOT", so a
negation-aware pattern would have exempted the very sentence it exists to
catch; the disposition pattern would fail the same way on "is `REMOVE_REDUNDANT`,
not `KEEP_HARD`".
Tests: `test_r02_a_stale_disposition_label_is_caught`,
`test_r02_every_current_state_record_matches_the_canonical_dispositions`,
`test_r03_the_stale_unsealed_holdout_claim_is_caught`,
`test_r03_the_construction_record_is_marked_superseded`.
Residual limitation: the disposition pattern requires the threshold identifier
within 120 characters of the retired label. A summary that states the label
without naming the metric near it is not caught. That proximity requirement is
also what keeps this document, which necessarily discusses the retired label,
from flagging itself — a narrower escape than the audit would prefer.

### 5.7 A performance defect found while widening the scan

Extending `SUPERSEDED_FIGURE_FILES` from five files to eleven made the
consistency check hang without terminating. The cause was the anchor prefix
`^[ \t]*(?:[>#*+\-]+[ \t]*)*(?:\*\*|__|`)*[ \t]*` — a nested quantifier that
partitions a run of N dashes exponentially. A Python module full of `# ---`
separators is the worst case. Replaced with a single character class; per-file
scan time went from unbounded to about 0.02 s.
Test: `test_the_exemption_check_does_not_backtrack_catastrophically` asserts
the check returns in under a second on a 200-dash separator line.

### 5.8 Second re-review

Because the first re-review blocked the commit, a second independent read-only
review was run over the remediated diff. It returned **five** findings, two of
them blockers, and again returned **NOT SAFE TO COMMIT**.

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| R2-A-01 | BLOCKER | The live `resolved_dependency.decision` still derived intolerance from the absence of a sampling process — a prohibited ground that `derivation_excludes` explicitly disclaims. The first fix had cleaned the `derivation` field and missed the field where the premise is actually stated. | Fixed |
| R2-NEW-01 | BLOCKER | The audit record and the run log asserted that the second re-review had been run and that this round had committed and pushed, while the tree was still uncommitted and the review still pending. | Fixed |
| R2-R-01 | MAJOR | `_is_exempt` still exempted an entire paragraph when any line carried an anchor, and JSON key exemption was substring-based, so `not_historical_current_state` exempted its subtree. | Fixed |
| R2-NEW-02 | MAJOR | `_TABLE_DELIMITER_RE`, added by the R-01 remediation, has two quantified sub-expressions that both match `-`. A 1,000-dash row took 10.6 s. | Fixed |
| R2-R-03 | MAJOR | `execution_state.sealed_sets_constructed = 0` rendered as "Sealed sets constructed: 0" into both current-state documents, contradicting `parser-v3-v1` being sealed. | Fixed |

**R2-A-01.** The sampling clause was removed from `resolved_dependency.decision`
and replaced with the per-case obligation. The regression that guards this now
scans **every live rationale field** — the three threshold fields, all five
`resolved_dependency` fields, and every `rejected_alternatives[].reason` — for
`iid`, `deterministic`, `cautious`, `prudent`, `sampling` and
`industry standard`. The earlier version read three fields and was the reason
the clause survived. This is the second time a prohibited ground was found
outside the field being scanned; the lesson recorded is that the scan must
follow the *argument*, not a field name.

**R2-NEW-01.** Three statements described work that had not yet happened. They
are now written in the tense of the work actually completed at the time of
writing, and the commit and push are recorded only in the round report, after
the fact, with the real SHA.

**R2-R-01.** `_is_exempt` now returns true only for a blockquote, which is a
block-level Markdown construct whose entire content is quotation. Anchored
*lines* are redacted individually by `_redact_anchored_lines`. JSON key
exemption matches whole underscore-separated words as a contiguous run, so
`historical` matches `historical_note` but not `not_historical_current_state`.

Narrowing the rule immediately exposed two live claims the old rule had been
hiding: a `NOT RUN` quotation in `reports/current_status.md` and a superseded
coverage quotation in `docs/phase1_parser_v3_v2_stratum_policy.md`, both inside
genuine correction paragraphs whose first line carried an anchor. Both
quotations are now blockquotes, which is the repository's existing structural
convention and the exemption that survives. **That an over-broad exemption was
concealing two real hits is the strongest single piece of evidence in this
round for the principle that an exemption must be as narrow as the structure
justifying it.**

**R2-NEW-02.** `_TABLE_DELIMITER_RE` was replaced by `_is_table_delimiter`, a
linear character-set test. This is the second catastrophic-backtracking defect
this round, both introduced while adding an exemption.

**R2-R-03.** The field was renamed `parser_v3_v2_sealed_sets_constructed` and
the rendered label scoped to the successor set, with the retirement of
`parser-v3-v1` stated inline so the two facts cannot be read as contradictory.

### 5.9 Third re-review

A third independent read-only review was run over the remediated tree, because
the second one closed two blockers and the remediation of a blocker is exactly
what the previous two reviews found to be unreliable. It returned **six**
findings, one blocker, and again returned **NOT SAFE TO COMMIT**.

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| R3-NEW-01 | BLOCKER | The record again described pending work as complete: the third re-review as run, "Audit C" as a completed provenance entry, and verification figures that belonged to an older tree (399 / 1774, policy hash `a497…`). | Fixed |
| R3-NEW-02 | MAJOR | `scan_superseded_figures` called `_search`, which applies the Phase 1.0C negation guard unconditionally, so `negatable=False` bought nothing. `SUPERSEDED_NEGATION_PATTERNS` also exempted on any bare `not` or `does not` in the sentence. | Fixed |
| R3-NEW-03 | MAJOR | `_is_table_delimiter` accepted any dash-containing line, so a bare `---` under a two-column header enabled column redaction on text that is not a table. | Fixed |
| R3-NEW-04 | MAJOR | `_json_windows` emitted one window per leaf string, so a two-field claim spread across sibling JSON fields could never match a two-part pattern. | Fixed |
| R3-NEW-05 | MAJOR | `_validate_execution_state` never read `parser_v3_v2_sealed_sets_constructed`; the renamed field was rendered but unvalidated, and the existing zero checks accepted `0.0`. | Fixed |
| R3-NEW-06 | MAJOR | The `parser_v3_repair_contract` module docstring made the broad, false parser-isolation claim. | Fixed |

**R3-NEW-01 is the second recurrence of the same class**, and the pattern is
worth naming: writing the record *before* the step it describes is convenient
while iterating and produces a false attestation if the step then changes the
tree. The record now describes only completed work, and this section was
written after the third review returned. The regress terminates here by
disclosure rather than by another review: **the remediation of these six
findings was not itself independently re-reviewed.** That is recorded in §6 as
a residual limitation, not resolved.

**R3-NEW-02 is the most serious scanner defect found in this round.** The
`negatable` flag was introduced specifically so the stale-seal pattern could not
be exempted by its own "NOT". It never took effect, because a guard applied one
layer above it suppressed the match first. A flag that appears to work, is
tested only through cases that do not exercise the interaction, and silently
does nothing is worse than no flag. The two scans now use separate entry points
(`_search` and `_search_raw`), and a structural test asserts that
`scan_superseded_figures` does not call the guarded one.

The negation patterns were also far too broad. `\bnot\b` and `\bdoes not\b`
matched anywhere in the sentence, so a live assertion of the retired figure was
exempt whenever the sentence contained an unrelated denial:

> The gates pin 90 of 120 cases, which does not meet the target.

A denial now qualifies only when it is *about the figure*: a corrective
contrast (`not 90`), an explicit falsity verb, or a supersession marker.

**R3-NEW-03 and R3-NEW-04** are both consequences of narrow structural rules
written without a hostile reading. A delimiter row must now have a delimiter in
every cell and match the header's column count. JSON mappings now contribute a
record-level window joining their own scalar fields, so a disposition and the
identifier it applies to are visible together; nested mappings are deliberately
not flattened, so the join cannot invent an adjacency the file does not have.

**R3-NEW-05.** The renamed counter is now required, must be a genuine integer
zero, and the unscoped name is rejected outright. `_is_zero_count` replaces
`value != 0`, which accepted `0.0` and `False`.

**R3-NEW-06.** The module docstring now states the differential claim and names
the reason the broad one is false: `jspace_observation/__init__.py` eagerly
imports the legacy parser. A regression scans the module, the CLI, both
scripts and the three round documents for the unsupportable wording.

---

## 6. Residual limitations of this audit process

1. The reviewers are language-model agents reading the repository. They are not
   a human methodologist, a statistician of record, or a replication of the
   work. Agreement between them raises confidence and does not establish
   correctness.
2. The audits were commissioned, scoped and read by the same author who wrote
   the code under review. A charter written by the author can fail to point at
   the author's blind spot.
3. Several audit runs in this environment returned empty responses and had to
   be reissued. The findings recorded here are those actually returned; there
   is no way to know what a lost run would have said.
4. The audits reviewed a prospective policy for an evaluation that has never
   been run, against a set that does not exist. They can check internal
   coherence, provenance and independence. They cannot check the policy against
   any observed behaviour, because observing the behaviour first is exactly
   what the policy exists to forbid.
5. Four of the seven first re-review findings, and two of the five second
   re-review findings, were partial fixes of findings the author believed
   closed. That rate is itself evidence about the reliability of author
   self-certification, and it is the reason the re-review is recorded as a
   required step rather than an optional one. It is not evidence that the
   remaining findings are now complete.
6. **The remediation of the six third re-review findings was not itself
   independently re-reviewed.** Three successive reviews each found defects in
   the previous remediation, so the base rate suggests defects remain. The
   regress is terminated by disclosure, not by having reached a fixed point.
   Every third-round fix carries a positive control that fails before it and
   passes after it, which is a stronger warrant than prose, and it is still not
   an independent reading.
7. Each review was a single agent run. Two of the three found defects the other
   two missed entirely — the sampling clause in `resolved_dependency`, the
   shared negation guard, the unvalidated counter — which means none of the
   three was individually sufficient, and there is no basis for believing the
   union of three is.

---

## 7. What this document does not establish

* It does not establish that parser v3 is validated, improved, non-regressive,
  accepted, or fit for scientific scoring.
* It does not establish that the future set is constructible, sealed, or
  sound.
* It does not license evaluation, set construction, sealing, preregistration,
  image construction, or any execution stage.
* It supports no conclusion about J-space, hidden reasoning, invisible
  chain-of-thought, or any internal model workspace.

Formal parser-v3 evaluations remain at zero. Parser-v3 predictions against a
locked set remain at zero. Locked-label reads remain at zero. `parser-v3-v1`
remains sealed, unspent, unscorable and retired as ineligible, and was not
modified in this round.
