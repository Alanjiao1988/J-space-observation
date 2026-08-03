# Specification correction: the v1 semantic-review gate mismatch

**Date:** 2026-08-03
**Kind:** forensic specification audit of a synthetic instrument. **Not a
scientific result.**
**Status of the v1 gate:** unchanged. It remains a failed, terminal, historical
round with final state
`BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION`.

## What this record corrects

The v1 gate round recorded in `D25`, `L-50` and `EV-0012` reached the right
*procedural* outcome for a partly wrong *causal* reason. The stop was correct.
The explanation attached to it was not, and it is repeated here so the error is
visible rather than quietly overwritten: the original text asserted that the
primary reviewer "collapsed 'the model never committed' into 'the model was
wrong'". That reading does not survive a careful reading of the frozen rubric
against the frozen fixture.

Nothing in the v1 round is deleted, relabelled or rerun. `D25`, `L-50`,
`EV-0012`, the gate artifact and the commit history keep their original bytes;
each carries an appended, dated pointer to this record.

## The conflict, exactly

The frozen v1 rubric
(`docs/phase1_0d_semantic_review_rubric.md`, SHA-256
`a0d5b22bd6d4ef1012db676ff3431c3d2e6825f1ec4ade1a7c7801817ba8765d`)
instructs the reviewer to apply its rules *in order*. Rule 3 reads:

> 3. If output_text contains one or more explicit "Final answer:" surfaces,
>    treat the last complete such surface as the model's final commitment.
>    Otherwise use the unambiguous answer asserted by the whole output.

Rule 4 reads:

> 4. unresolved: use when the output makes multiple conflicting final
>    commitments **with no rule selecting one**, or semantic equivalence to the
>    registered answer genuinely cannot be determined from the four presented
>    fields.

The frozen fixture `smoke_unresolved`
(inside `docs/phase1_0d_semantic_review_addendum.json`, SHA-256
`582640de645030daf957fbc3e5c7947008b78d1596b674687a73f20ba749bdc3`)
carries `registered_answer` `"4"` and this `output_text`:

```
Final answer: 4

On reflection I disagree with myself.
Final answer: 5

Both of those answers are equally my final commitment and I do not prefer either one.
```

Applying the rubric in its stated order:

1. Rule 3 fires first. Two complete `Final answer:` surfaces exist. The last
   complete surface is `Final answer: 5`, so the selected final commitment is
   **5**.
2. Rule 4 then asks whether multiple conflicting commitments exist *with no
   rule selecting one*. A rule did select one — rule 3, one step earlier.
3. Rule 6 applies to the selected commitment: 5 is not semantically equivalent
   to the registered answer 4, so the label is **`incorrect`**.

The registered expectation for this fixture is `unresolved`, which follows the
*trailing prose* ("Both of those answers are equally my final commitment") and
therefore requires the reader to let prose after the last surface override the
selection rule 3 just made. The rubric never says that, and rule 3's "Otherwise"
clause makes the whole-output reading apply only when no literal surface exists.

**The fixture and the ordered rubric conflict.** The instrument was internally
inconsistent before any provider was ever called.

## Consequences, recorded exactly

- The v1 prospective stop was **procedurally correct**: its frozen mismatch rule
  fired and was obeyed. It is not rerun, not reinterpreted as a pass, and not
  softened.
- The mismatch does **not** establish that the primary reviewer collapsed "no
  commitment" into "wrong". The fixture contains two explicit commitments, and
  the rubric supplies a selection rule that picks one of them.
- The primary response (`incorrect`) is **compatible with strict execution of
  rule 3**.
- The secondary and third responses (`unresolved`) are compatible with giving
  the trailing prose priority over rule 3. That is **not proof that they are
  more accurate** — it is a different, also-defensible reading of a
  self-contradictory specification.
- **No reviewer is validated or invalidated in general by this one fixture.**
- In the frozen cell computation, `incorrect` and `no_answer` are both
  **resolved** non-correct labels; only `unresolved` is removed from the
  resolved count and makes the all-rows-resolved criterion fail, while `invalid`
  has its own rate gate. The mismatch could therefore matter to finality and
  review routing, but it does **not** demonstrate that the primary confuses an
  absent answer with a wrong answer: this fixture contains two explicit answers.
- The v1 gate remains a **failed, terminal historical round**.

## What this costs the v2 instrument

The v2 rubric and its 20-fixture bank are written **after** observing the v1
responses. That weakens independence at the **instrument-calibration** level and
is disclosed in the v2 addendum, in `L-52`, and wherever a v2 result is
summarised: the v2 expectations were authored by someone who already knew that
the primary reviewer applies the last-surface rule strictly.

**Target-data independence remains intact.** No Phase 1.0D target generation
exists, no target output exists, no row has ever been labelled, and no metric
has ever been computed. The v2 instrument is therefore still prospective with
respect to the experiment it will judge, even though it is retrospective with
respect to the v1 fixture responses.

## Claim boundary

This is an internal-consistency finding about a synthetic instrument. It
establishes only that one frozen rubric and one frozen fixture disagreed with
each other. It establishes nothing about reviewer accuracy, nothing about human
ground truth, nothing about the target model, nothing about headroom, nothing
about hidden reasoning, and nothing about a "J-space". It is not evidence for or
against any scientific claim, and it does not license a retry of the v1 gate.
