# Phase A public audit — scope A

**Audit A: methodology, lifecycle, admission, blinding, replacement, sealing.**

You are auditing whether the *scientific* machinery of a one-shot, preregistered
parser evaluation actually enforces what it claims. You are not auditing the
repository layout, the container entrypoints, the JSON Schemas, the Azure
infrastructure, or the security boundary; a second auditor covers those and you
should not spend effort there.

## What the material is supposed to do

The programme evaluates a candidate parser (`v3`) against a held-out set of 120
cases, under a protocol designed so that the evaluators cannot tune themselves
into a pass. The essential claims are:

- The evaluation is **one-shot**: exactly one formal evaluation ordinal exists,
  it is consumed once, and a second attempt is refused rather than overwritten.
- The set is built **before** anyone sees a score: cases are admitted by blinded
  independent A/B review, disagreements are routed to an arbiter deterministically,
  and unusable cases are quarantined for closed, registered reasons.
- Repair is **bounded**: replacement of quarantined cases is capped, and running
  out of budget is a terminal blocked state (`BLOCKED_ON_SET_REPAIR`), not a
  licence to relax the set.
- The set is **sealed create-only** before predictions exist, predictions are
  sealed create-only before scoring exists, and scoring (Stage E) recomputes the
  verdict from preregistered gates rather than accepting a reported one.
- No label-bearing or parser-bearing field ever reaches a role forbidden to see
  it.

## Areas

Use one of these strings for `area`:
`lifecycle`, `construction`, `admission`, `blinding`, `arbitration`,
`quarantine`, `replacement`, `collision-rules`, `sealing`, `preregistration`,
`stage-p`, `stage-e`, `rehearsal`, `methodology`.

## What to look for, in order of value

1. **A claimed invariant that no code enforces.** For each guarantee named above,
   find the function that enforces it and the branch that raises. If the
   guarantee exists only in a docstring, a comment, or a test fixture, that is a
   `BLOCKER`.
2. **A control that cannot fail.** A test that asserts something already
   guaranteed by construction, a `pytest.raises` whose body would raise for an
   unrelated reason (wrong argument name, missing key, typo), an assertion on a
   value the test itself just wrote, or a negative control whose "mutation" does
   not actually change live behaviour. Prove it by naming the substitution that
   would still pass.
3. **A path to a terminal verdict that skips a check.** In particular: can
   `run_stage_e` reach `PASS` for a set that is short of its full member count,
   that contains an ineligible sealed case, or whose denominator has silently
   shrunk?
4. **Order dependence where determinism is claimed.** Content-hash selection,
   collision-rule evaluation order, arbitration routing, and replacement ordering
   are all claimed deterministic. Find any place where a `set`, a `dict`
   insertion order, a `sorted` on a mutable key, or an unstable comparison could
   change the outcome.
5. **The four collision rules.** `exact`, `normalized`, `numeric_normalized`,
   `template_family`. Check that each one can independently catch a duplicate,
   that the reported rule name is the rule that actually fired, and specifically
   that `template_family` does **not** mask every alphanumeric segment — an
   earlier defect (recorded as PA-03) made it reject sound sets by collapsing
   distinct cases into one family. Check that the rehearsal fixtures do not use
   "one template plus a case ID" to defeat the rule they are supposed to
   exercise.
6. **Blinding.** Does the blinded case packet given to reviewers actually exclude
   the fields that would unblind them? Is the blinding enforced by a check, or
   only by the fixture happening not to include them?
7. **Create-only semantics.** "Create-only" means an existing object is never
   overwritten and never deleted. Find where that is enforced, and whether a
   second write is refused or silently accepted.

## Properties to check

Return one `properties_checked` entry for each of the following, verbatim, in
this order.

1. Exactly one formal evaluation ordinal exists and a second formal evaluation is refused rather than overwritten.
2. Stage E refuses any sealed case marked ineligible; it never skips it or shrinks the 120-case denominator.
3. Stage E recomputes PASS/FAIL from preregistered gates rather than trusting a reported verdict.
4. The preregistration lock is create-only over a closed binding set and cannot be amended after creation.
5. Prediction sealing is create-only and refuses an incomplete prediction stream.
6. Quarantine reasons are drawn from a closed registered set and an unregistered reason is refused.
7. Replacement is bounded and exhausting the budget raises BLOCKED_ON_SET_REPAIR rather than relaxing the set.
8. Blinded A/B review compares only the registered agreement fields and routes to the arbiter deterministically.
9. All four collision rules can independently reject a set and the reported rule name is the rule that fired.
10. template_family does not mask every alphanumeric segment and does not recreate the PA-03 false-positive defect.
11. Rehearsal fixtures do not use "one template plus case ID" to defeat the registered collision rule.
12. Content-hash selection is order-independent.
13. The construction refuses to target the historical 105/15 split.
14. No label-bearing field reaches a role forbidden to read labels.
15. No parser-bearing field reaches a role forbidden to invoke the parser.
16. No existing test is weakened, removed, skipped, or xfailed by the material under audit.
