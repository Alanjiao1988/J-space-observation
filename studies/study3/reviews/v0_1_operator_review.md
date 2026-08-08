# Study 3 draft-v0.1 operator review record

**Disposition:** `STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE`

**Reviewed object:** `studies/study3/protocol/interface_calibration_protocol_draft.json`
and its Markdown companion at draft-v0.1, as published in commit
`360086db495c4c5a098e49a6e8adf73dd143eaef`.

**Review outcome:** amendment required. draft-v0.1 was **not** approved for freeze,
was **not** approved for bank construction, seed drawing, interface selection or
positive-reference selection, and remains **not** approved for any of those after
this amendment.

**Nature of this record:** additive. draft-v0.1 is preserved exactly as it was
published, and `studies/study3/design_receipt.json` is retained verbatim as the
historical receipt of that round. Nothing in the v0.1 history has been edited to
hide, soften or retro-fit any defect listed below. The amended draft is a new
version, `draft-v0.2`, recorded in the same files with a new receipt at
`studies/study3/design_receipt_v0_2.json`.

**Classification:** every item below is a **design defect in an unfrozen draft**.
None of them is an empirical finding, a measurement, a result or an observation
about any model. No limitation-ledger row is created for them, because the
limitations ledger records limitations of executed measurement, and recording a
review defect there would misclassify it.

---

## How the defects were confirmed

The ten defects were supplied by the operator review. They were **not** accepted
on assertion. Each was checked against the committed blobs of
`360086db495c4c5a098e49a6e8adf73dd143eaef` before any amendment was drafted, and
each was confirmed to be a real property of the published v0.1 text. Two of them
are quoted verbatim below from the committed bytes.

One defect (D-05 and D-06, statistics) was additionally confirmed *numerically*
rather than only by reading: the committed model-free derivation at
`studies/study3/analysis/design_statistics.py` shows by exact enumeration that
the v0.1 aggregate equivalence margin of 0.05 is not attainable at 0.90 power at
n = 192 for **any** of the discordance rates 0.05, 0.10, 0.20 or 0.30. The v0.1
draft asserted that margin with no paired power analysis at all.

---

## D-01. The Markdown companion contradicted its own JSON twin

**Confirmed verbatim.** The published v0.1 Markdown contained the line:

```
- **A winner is selected in this round:** `true` (that is, no winner is selected)
```

while the JSON twin correctly carried `"no_winner_this_round": true`.

Read as written, the Markdown states that a winner **is** selected and then
parenthetically denies it. The generator had rendered the *value* of the field
`no_winner_this_round` under a *label* that dropped the negation. The two
documents therefore disagreed on the single most consequential fact in the
draft: whether an interface had been chosen.

**Severity:** critical. A reader acting on the Markdown alone could believe a
selection decision had already been made.

**v0.2 disposition:** resolved. The JSON is declared the authoritative artifact
and the Markdown is declared a companion rendering of it. The label is corrected
to state the proposition, not the field name. A committed test now asserts
semantic parity between the two documents on every decision-bearing marker, so
this class of defect fails the suite instead of reaching publication.

---

## D-02. The Markdown made an unsupported provenance claim

**Confirmed verbatim.** The published v0.1 Markdown asserted that the Markdown
and JSON "are generated from one source of record and agree exactly", but no
generator, test or check enforcing that property was committed. The generator
was an operator-side ephemeral script that was, by policy, never committed.

The claim was therefore unfalsifiable from the repository, and D-01 proves it was
also false at the time it was made.

**Severity:** high. An unverifiable provenance claim is worse than no claim,
because it discourages the check that would have caught D-01.

**v0.2 disposition:** resolved. The unsupported single-source claim is removed
outright. It is replaced by a statement of what is actually true and actually
enforced: the JSON is authoritative, the Markdown is a companion, and a committed
test verifies agreement on the enumerated decision-bearing markers.

---

## D-03. Gate lifecycle contradictions around I4 and I5

v0.1 stated that an interface is selectable when gates I0 through I3 pass, and
omitted I4 from the selection rule. Elsewhere it said an interface that fails I4
"remains eligible". It also wrote an I4 failure as a **global** study stop even
though I4 is evaluated per interface, and its I5 confirmation description did not
cover the positive-reference construct or the K4 stratum.

These cannot all be true at once. Either I4 bears on eligibility or it does not;
either its failure eliminates one interface or it halts the study.

**Severity:** critical. The selection rule is the operative rule of the study.

**v0.2 disposition:** resolved. I4 is part of eligibility. Failing I4 eliminates
**that interface only**. The study stops only when no selectable interface
remains. "Remains eligible" is deleted. I5 is redefined to cover **every**
gate-bearing construct, explicitly including I4 evaluated on the positive
reference over the K4 stratum.

---

## D-04. Positive-reference circularity and a floor that was not a capability floor

v0.1 allowed the positive reference to be evaluated through a candidate
interface. If a candidate interface is itself what demonstrates that the
reference is capable, the interface's adequacy is being established by an
argument that presupposes it.

Separately, the v0.1 I4 floor was an exact binomial test against a chance null of
p <= 0.25 at n = 128, giving an acceptance count of 49 out of 128, that is a rate
of 0.3828. Clearing that threshold shows only that the reference performs above
guessing. It is not evidence that the reference is *competent*, and only a
competence claim can license the inference "a capable model would have passed, so
the interface is adequate".

**Severity:** critical. This defect goes to the identifying assumption of the
whole study.

**v0.2 disposition:** resolved in part, and the remainder is escalated. The
positive reference is prequalified through a **separate canonical interface that
is not S1, S2, S3 or S4**, on **disjoint items**, so that no candidate interface
is validated by itself. The chance null is **rejected**; the replacement proposal
is a competence floor of p_floor = 0.80 evaluated per operation family and per
depth. The final floor value is a blocking unresolved decision, OD5, reserved for
the independent methods review. The rejected chance-null arithmetic is retained
in the statistics tables, explicitly labelled `REJECTED_BY_OPERATOR_REVIEW`, so
that the rejection is auditable rather than silently dropped.

---

## D-05. Robustness construct mismatch, and NA treated as a pass

v0.1 measured robustness by aggregate equivalence. Aggregate equivalence is
satisfiable while a large number of individual items flip their answers in
compensating directions, which is precisely the failure mode the gate is supposed
to exclude. The draft declared no pre-registered item-level content-consistency
criterion at all.

Worse, v0.1 applied position and label transformations to interface profiles that
**display no options and no labels**. For such profiles the transformation has no
referent. v0.1 scored the resulting "no effect" as a pass, which manufactures
robustness evidence out of an inapplicable manipulation.

**Severity:** critical, and it is the defect most likely to produce a false pass.

**v0.2 disposition:** resolved. Item-level content consistency on the base item
becomes the **primary** I3 criterion, tested as an exact binomial floor on the
per-base-item consistency indicator. Aggregate equivalence is demoted to a
**secondary** criterion and is bound to a named, executable, verified method
rather than an adjective. Applicability becomes a first-class, three-valued
property: a transformation is `applicable`, or it is `not_applicable`, and
`not_applicable` is neither a pass nor a zero effect nor an input to any ranking.

---

## D-06. Statistics were incomplete

v0.1 named a paired equivalence idea but never specified an operational test,
never mapped its multiplicity family structure, and asserted n = 192 with no
power analysis for the I3 construct.

**Severity:** critical.

**v0.2 disposition:** resolved by construction, with a residual escalation. A
committed model-free script, `studies/study3/analysis/design_statistics.py`,
now derives every threshold in the draft, and a committed check mode reproduces
its tables value-for-value. The paired method is named as Tango's 1998 score
procedure and is **verified before use** on three independent criteria: it
reduces exactly to McNemar's statistic at a null difference of zero, its
closed-form constrained maximum-likelihood estimate agrees with a direct
numerical maximisation of the constrained likelihood, and its exact type-I error
under enumeration of the full discordant-count distribution does not exceed its
nominal level. The multiplicity structure is now split explicitly into a
conjunctive intersection-union family within an interface, which needs no
inflation correction, and a union selection family across interfaces, which does.

The derivation also produced a substantive negative result: **n = 192 does not
support a 0.05 aggregate equivalence margin at 0.90 power at any of the tested
discordance rates.** The margin, the sample size, or both must change. That is
recorded as blocking decision OD6.

---

## D-07. Pooling could mask a failed cell

v0.1 permitted results to be pooled across the K1 and K2 strata, across primitive
operation families, and across K4 depths and families. A strong family can then
carry a failed family across a threshold, so the gate stops testing what it
claims to test.

**Severity:** high.

**v0.2 disposition:** resolved. The atomic evaluation cell is defined explicitly
as interface profile x checkpoint role x stratum x operation family x depth x
rendering x label/position condition x split. Pooling as a rescue is prohibited
across K1 and K2, across operation families, across depths, across roles, across
surfaces and across renderings. Pooled summaries survive only as descriptive
reporting with no gate authority. K1 is separated from K2, K3 is evaluated per
primitive family, and K4 is evaluated per family **and** per depth, with depth 2
and depth 3 never combined.

---

## D-08. Panel and selection contradiction

v0.1 described S4 as calibration-only and then allowed it to win the ranking. It
also treated S3 as an independent interface, but for single-token answer contents
S3's argmax is identical to S2's by construction, so S3 contributed no independent
information in the absence of a multi-token answer domain.

**Severity:** high.

**v0.2 disposition:** resolved. S4 is **never selectable** under any outcome and
is diagnostic only. S3 is **conditional**: with the current single-token frozen
answer domain its argmax identity is recorded as an integrity check against S2 and
is not counted as four additional scorings; it becomes selectable only if a
multi-token answer domain, a dedicated stratum, a boundary-token rule and a
length-confound gate are all introduced by a later authority. The data-dependent
ranking is replaced entirely by a pre-registered fail-closed admissibility order.

---

## D-09. Counterbalancing was ambiguous and collided with the answer domain

v0.1 used four cyclic option orders. Cyclic rotation does not separate the
physical position of the correct content from the identity of the displayed
symbol, because both move together. v0.1 also used the label alphabet 1/2/3/4
alongside a mod-10 answer domain, so a displayed label could be indistinguishable
from a valid answer. Its K6 stratum claimed three renderings while varying three
things at once, including the answer cue.

**Severity:** high; the label collision is a validity defect, not a nuisance.

**v0.2 disposition:** resolved. Counterbalancing must use a deterministic
orthogonal or explicitly justified balanced design that separates correct-content
physical position, displayed symbol identity and label alphabet, and the exact
construction algorithm must be published with the design rather than described.
Label alphabets must be disjoint from the answer domain, and the alphabet 1/2/3/4
is **forbidden** while the answer domain is mod-10. Label-set replacement is
crossed and balanced with position. Open decision OD4 is resolved to exactly
three K6 renderings, baseline, separator-only and instruction-wording-only, with
the answer cue **held constant**.

---

## D-10. Study 1 overstatement

v0.1 wrote as established fact that parsing caused the Study 1 E0 collapse. That
is a hypothesis. What the record supports is narrower.

**Severity:** medium as a scientific-claim defect, high as a precedent.

**v0.2 disposition:** resolved. The draft now states only what the record
supports: the frozen raw-completion, no-chat-template, single-token E0 harvest
yielded too few eligible items; a parser-v2 revision failed its locked gate; a
parser-v3 variant was explored but is non-authoritative. These facts **motivate**
an interface-adequacy study; they do **not** establish that parsing caused the
collapse.

---

## D-11 (process). Reproducibility gap

Not one of the ten numbered scientific defects, but the reason D-01 survived to
publication: the v0.1 round's consistency checker was an operator-side ephemeral
instrument. It was not committed, so it could not be re-run by a reviewer, and it
did not in fact catch D-01.

**v0.2 disposition:** resolved. Design-critical checks are now **committed
artifacts**: `tests/test_study3_design.py` under the repository test suite, and
`studies/study3/analysis/design_statistics.py` with a `--check` mode. The
committed test carries a negative-mutation battery, so each defect class above
has an executable test that fails when the defect is reintroduced. The ephemeral
operator instrument is retained only as a secondary check and has no authority.

---

## Standing after this amendment

| Item | State after v0.2 |
| --- | --- |
| D-01 Markdown/JSON contradiction | resolved, test-enforced |
| D-02 unsupported provenance claim | resolved, claim removed |
| D-03 gate lifecycle contradiction | resolved |
| D-04 positive-reference circularity | structurally resolved; floor value blocking as OD5 |
| D-05 robustness construct and NA-as-pass | resolved |
| D-06 statistics incomplete | derivations committed; margin and n blocking as OD6 |
| D-07 pooling could mask failure | resolved |
| D-08 panel and selection contradiction | resolved |
| D-09 counterbalancing and label collision | resolved |
| D-10 Study 1 overstatement | resolved |
| D-11 reproducibility gap | resolved, checks committed |

Three open decisions remain **unresolved and blocking**: OD2 (positive-reference
identity and wrappers), OD5 (the I4 competence floor) and OD6 (sample size and
the I3 margin). draft-v0.2 is therefore **not** approved for freeze. The only
legal next action is bounded independent methods review.
