# Phase 1.2E — parser-v3 evaluation ontology repair protocol

**Status: tooling round. No private data was opened, no prediction was
generated, no evaluation occurred.**

Phase 1.2D halted in preflight because the sealed `parser-v3-v1` set, the frozen
scoring instrument and the parser-v3 gate contract described three different
things. Findings `H1`–`H9` and the six representational normalisations `N1`–`N6`
are recorded in `docs/phase1_parser_v3_locked_evaluation_protocol.md` §15. This
document does not rewrite that history. It defines the repair.

The repair has two halves, and only the first is in scope here:

1. **Public protocol and tooling** — the ontology, the span convention, the
   migration rule, the separation of prospective policy from set-derived fact,
   and the code that enforces all of it. This round.
2. **Private set construction** — independent curation, review, sealing and
   preregistration of a new `parser-v3-v2` set. A later round, under its own
   authorization.

Terminal status of this round is defined in §10.

---

## 1. Scope

In scope: protocol, prospective policy, repair tooling, synthetic tests,
documentation, and the correction of one reporting defect.

Explicitly out of scope, and not performed: reading any sealed locked input or
locked label; reading any git-ignored curator file; running any parser on any
locked input; generating any prediction stream; running Stage P or Stage E;
creating an authorization lock or an evaluation state chain; building or reusing
an evaluation image; creating, modifying or starting any Azure resource; and
modifying the sealed prefix or amending the historical gate contract in place.

The evidence base for this round is the committed repository plus new public
synthetic fixtures. The single external authority used is
`evaluator_sets/parser_v3_v1/strata_definitions.md`, which is a tracked public
file containing stratum definitions and quotas but no case text and no labels.

---

## 2. Disposition of `parser-v3-v1`

The existing set is recorded as:

```
SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE
```

Each term carries a distinct claim, and they are not interchangeable:

| Term | Claim |
| --- | --- |
| `SEALED` | The sealed prefix exists and its bytes are unchanged. |
| `UNSPENT` | No locked label was ever read and no prediction was ever scored against it. This records the *absence of label access*. It is a statement about what did not happen, not a licence for what may happen next. |
| `UNSCORABLE` | Its set ontology and its gate contract cannot both be satisfied by the frozen scoring instrument. No sequence of scoring choices yields a defensible `PASS` or `FAIL`. |
| `RETIRED_AS_INELIGIBLE` | It is permanently ineligible for formal evaluation. Its one-shot budget is not transferable and not redeemable. |

Consequences, all binding:

* The sealed bytes and their provenance are preserved unchanged. Nothing is
  deleted, rewritten or re-sealed.
* Findings `H1`–`H9` and normalisations `N1`–`N6` remain valid historical
  results about that set and are not withdrawn.
* The historical gate contract `docs/phase1_parser_v3_acceptance_gates.json`
  is preserved byte-for-byte as the artifact that was found defective. It is
  never amended in place; a corrected contract would be a different artifact
  with a different identity.
* `scripts/parser_v3_repair_cli.py` refuses to read or write any path inside
  the `parser_v3_v1` namespace. The refusal has no override flag.

### 2.1 Count terminology

The Phase 1.2D report stated `Holdout objects 15`. That was a factual defect
and is corrected by an erratum in
`reports/phase1_parser_v3_locked_evaluation.md`. Three populations are now
separately named and are never substituted for one another:

| Name | Value for `parser-v3-v1` | Meaning |
| --- | --- | --- |
| `sealed_object_count` | 12 | Storage objects in the sealed parent prefix. |
| `total_case_count` | 120 | Evaluation cases in the set. |
| `residual_semantic_case_count` | 15 | Cases still semantically inadmissible after `N1`–`N6`. |

A recursive listing of everything under `parser_v3_v1/` returns 15 entries, but
they are a different 15: the **12** sealed members of the parent prefix, plus
**2** objects in the sibling `…160340Z-runlog/` prefix, plus **1** orphaned
`crosscheck_report.json` under the aborted `…155224Z-runlog/` prefix. None of
those three runlog objects is a member of the sealed set. The reconciliation is
inferred from Phase 1.2D records — `artifacts/phase1-evaluator-validation/
track-d1/20260725T160340Z-track-d1-parser-v3-seal/05_summary.md:43` for the
independent 12+2 listing and the same pack's `08_deviations.json` deviation
`D10-seal-timestamp-rotated-after-an-overwrite-false-abort` for the orphan — and
was **not** observed this round; Phase 1.2E made no Azure call of any kind. The
coincidence of the two fifteens is exactly why the two counts now have different
names and a regression test.

Two further count kinds are registered so they cannot be conflated either:
`prediction_stream_count` and `score_state_object_count`. Both are `0`.

---

## 3. Identity of `parser-v3-v2`

A new set family is reserved:

```
set family      parser-v3-v2
namespace       evaluator_sets/parser_v3_v2/
blob prefix     <container>/parser_v3_v2/<sealed timestamp>/
```

Requirements on the new identity:

* It must not overwrite, alias, symlink to, or masquerade as `parser-v3-v1`.
* It carries its own manifests, its own hashes and its own seal.
* Its provenance must state that it is a replacement, not a revision, of a
  retired set, and must cite this protocol.
* No artifact of `parser-v3-v1` may be reused without being re-derived and
  re-validated under the ontology of §4.

---

## 4. The formal three-class ontology

The formal set admits exactly the three decisions that the candidate parser and
the frozen scoring semantics can both represent:

```
present:<canonical_value>
ambiguous
no_answer
```

`null_collapse_prohibited` is `true`: an answer-bearing case may never be scored
by collapsing an unextracted answer into `no_answer`.

### 4.1 Truth table

Every admissible record matches exactly one row. A record matching zero rows, or
more than one, is invalid; it is never coerced into the nearest row.

| Field | `present:<v>` | `ambiguous` | `no_answer` |
| --- | --- | --- | --- |
| `answer_presence` | `present` | `ambiguous` | `no_answer` |
| `parse_valid` | `true` | `true` | `false` |
| `parse_ambiguous` | `false` | `true` | `false` |
| `parsed_answer` | canonical literal, non-null | `null` | `null` |
| candidate cardinality (distinct, canonical) | `= 1` | `>= 2` | `= 0` |
| candidate list | dedup of evidence values, first-source order | dedup of evidence values, first-source order | empty |
| evidence spans | `>= 1`, **exactly one** `selected`, every span carrying `parsed_answer`; non-selected spans are `equivalent` | `>= 2`, all `ambiguous_candidate` | exactly `0` |
| `extraction_strategy` | `boxed_answer`, `explicit_final_marker`, `explicit_answer_marker`, `terminal_equation`, `single_candidate` | `ambiguous_candidates` | `none` |
| `output_quality` | `complete`, `truncated`, `malformed_recoverable` | `complete`, `truncated`, `malformed_recoverable` | `complete`, `truncated`, `malformed_recoverable`, `malformed_unrecoverable`, `placeholder`, `empty` |
| `typed_decision` | `present:` + canonical `parsed_answer` | `ambiguous` | `no_answer` |

Three cross-cutting rules apply to every row:

* **Stratum presence.** `answer_presence` must equal the presence registered for
  the case's stratum in the public stratum definitions. This is what turns
  "an `S10` case labelled `present`" from a matter of opinion into a mechanical
  error.
* **Reference and correctness.** `registered_reference_answer` must be
  canonical, and `expected_correctness` must equal
  `answer_presence == "present" and parsed_answer == registered_reference_answer`.
* **Criticality.** `critical_case` must equal `stratum not in {S01,S02,S03,S12}`.

### 4.2 `parse_valid` and `ambiguous`

This row is the single most consequential correction in the round, and it was
originally written the other way.

The intuitive reading — "`parse_valid` asserts that a single answer was validly
extracted, so detected ambiguity must be `parse_valid = false`" — is wrong for
this instrument. In the frozen scorer, `parse_valid` means *the parse itself is
well-formed*, not *a unique answer was selected*. Ambiguity that the parser
correctly detected and reported is a **valid** parse whose outcome is "two or
more candidates"; it is `parse_valid = true` with `parse_ambiguous = true`. The
frozen instrument enforces this directly: its `ambiguous` branch requires
`parse_valid` to be true and rejects the record otherwise, and `failure_reasons`
must be empty **exactly when** `parse_valid` holds — an ambiguous case has no
failure to report.

The pair remains non-redundant. `parse_ambiguous` alone separates `ambiguous`
from `present`; `parse_valid` alone separates both from `no_answer`, which is
the only class where the parse produced nothing to validate.

The first implementation of this protocol declared `parse_valid = false` for
`ambiguous`. Had it been sealed, **every `S11` case would have been unscorable
by construction** — the frozen instrument would have rejected all ten of them —
which is the precise failure mode that retired `parser-v3-v1`. It was caught by
the independent audit, not by the author, and not by the author's own tests,
which had encoded the same mistake. The lasting fix is structural rather than
textual: the ontology validator now *binds* to the frozen instrument by calling
`_validate_extraction_fields` and `derive_typed_decision` on every record and
requiring agreement, instead of restating the instrument's rules in prose that
can drift. See §4.6.

### 4.3 S11 candidate cardinality

`S11` exists to test detection of genuine multi-candidate ambiguity. The public
stratum definition states that every `S11` case carries at least two distinct
canonical candidates. This is enforced twice over: `S11` registers presence
`ambiguous`, and the `ambiguous` row requires at least two distinct canonical
candidates. A single-candidate `S11` case is invalid, and there is no
representational fix for it — such a case must be replaced, not repaired.

Distinctness is measured after canonicalisation. Two spans whose surface forms
differ but whose canonical values agree count as one candidate, and a case whose
"ambiguity" disappears under canonicalisation was never ambiguous.

### 4.4 `output_quality = empty`

`output_quality = empty` holds **exactly** when the locked output text is empty
after stripping whitespace — the frozen instrument's own test — not merely when
it is the zero-length string. It is not a synonym for "no answer found", and it
may not be used to describe a non-empty output that failed to parse; that is
`malformed_unrecoverable`, `truncated` or `placeholder`.

The public stratum definitions record that `parser-v3-v1` deliberately contains
no empty or whitespace-only output, so `empty` is an unexercised value in that
set. It remains in the vocabulary because the frozen instrument defines it, and
the ontology validator enforces the biconditional so a future set cannot use the
value loosely.

### 4.5 `present_unextractable`

`present_unextractable` — "an answer is present in the text but the parser is
not expected to extract it" — is a coherent research notion and an inadmissible
formal class. It is:

* **excluded** from the formal set;
* **never collapsed** into `no_answer`, `ambiguous` or `present`;
* **permitted** only in a separate research-only corpus that is never scored by
  the frozen instrument and never contributes to a gate.

The reason it cannot be collapsed is that each collapse asserts something false.
Mapping it to `no_answer` asserts the text contains no answer. Mapping it to
`present` asserts the parser should have found one. Mapping it to `ambiguous`
asserts multiple candidates. A fourth class silently present in a
three-class set is `H8`, and the whole `H9` failure followed from it.

### 4.6 Binding, not restating

The truth table above is documentation. The enforcement is not.

`H9` happened because the parser-v3 gate contract was a *copy* of the parser-v2
contract: a second description of the same rules, free to drift from the thing
it described. A validator that restates the frozen instrument's invariants in
fresh code is the same defect wearing different clothes, and §4.2 records what
it cost when this protocol did exactly that.

`parser_v3_repair_ontology._bind_to_scoring_instrument` therefore closes the
loop. For every record, after the table's own structural checks pass, it calls
the frozen `evaluator_validation._validate_extraction_fields(record,
output_text, prefix="expected_", expected=True)` and
`evaluator_validation.derive_typed_decision(record)`, and requires the derived
decision to equal the one the table assigned. A record this module accepts is
therefore a record the scoring instrument accepts, by construction rather than
by resemblance. If a future edit to the frozen instrument changes an invariant,
the repair tooling fails immediately instead of silently disagreeing.

This is what makes `H9` mechanically impossible rather than merely discouraged.

---

## 5. Span convention

**Literal-only, everywhere.** A registered evidence span covers the numeric
literal itself and nothing else: no `Final answer:` prefix, no `\boxed{…}`
wrapper, no trailing punctuation.

The convention is adopted because all three parsers already emit literal-only
spans through the frozen `validate_evidence_span`, and because the frozen
scoring instrument enforces
`normalize_rational_literal(span.text) == span.normalized_answer` on selected
spans. A marker-inclusive span can never satisfy that identity, so a set
registering one could never be scored. That was `H5`.

The convention binds labels, candidate parsers, comparators, validation and
scoring alike. **A registered span that the scoring instrument would reject
invalidates the set before sealing.** The ontology validator therefore delegates
span admissibility to the frozen instrument rather than restating it; restating
it is how the two descriptions drifted apart in the first place.

---

## 6. Treatment of the existing 120 cases

This section specifies the migration rule. **It is not executed in this round.**

### 6.1 The 105 representationally-repairable cases

The 105 cases that Phase 1.2D showed to be valid after `N1`–`N6` are *candidates*
for deterministic representational migration. Candidacy is not admission: each
must pass the §4 ontology validator after migration, on its own merits.

`N1`–`N6` must remain, and are implemented as:

| Rule | Effect |
| --- | --- |
| `N1` | Rewrite a marker-inclusive evidence span to the numeric literal it contains. |
| `N2` | Express the registered reference answer in canonical form. |
| `N3` | Attach the registered locked output text. |
| `N4` | Register the `S06` last-number distractor as the rightmost registered numeric literal. |
| `N5` | Derive the quota-diagnostic secondary tags from record content. |
| `N6` | Recompute candidate answers from the evidence spans, in first-source order. |

Required properties, each covered by a test:

* **semantic-preserving** — the typed decision before and after must be equal;
* **deterministic** — no ordering, locale or hash-seed dependence;
* **idempotent** — a second application is a no-op;
* **parser-free** — the repair sources reference no parser module and call no
  parser entry point. This is checked statically, by
  `assert_parser_free_source`, and differentially at runtime: the test suite
  compares `sys.modules` after importing only the frozen instrument against
  `sys.modules` after also importing the three repair modules, and requires the
  delta to be exactly those three. An absolute "no parser is loaded" assertion
  would be false comfort, because `jspace_observation/__init__` eagerly imports
  the parser for *any* import of the package;
* **auditable** — a content-free receipt of counts and hashes, never values.

`N1` and `N4` delegate to the frozen instrument's own definition of a registered
numeric literal. They do not restate it.

### 6.2 Quarantine, never coercion

A case is quarantined — not forced — whenever a rule would have to guess:

* the normalisation would change the typed decision;
* no unique registered rule applies, and the case falls outside the registered
  tie-break (`N1` resolves multiple contained literals to the rightmost literal
  matching the declared answer; several distinct non-matching literals is a
  quarantine, not a coin toss);
* the migrated record fails the §4 validator for any reason. This is the
  authoritative check: `normalize_record` calls `validate_ontology_record` on
  its own output before returning, so a record that survives every rule but is
  not admissible under the ontology is quarantined as one case rather than
  escaping to fail whole-set validation later. Because the §4 validator binds
  to the frozen instrument (§4.6), this also covers every field the scorer
  reads, including those no individual rule is licensed to touch.

### 6.3 The 15 residual cases

All 15 are quarantined. They differ from the frozen semantics *semantically*,
not representationally, and no rewrite can fix that. Their permitted futures
are exactly two:

1. **Fresh independent review.** Re-review under the §4 ontology, by a reviewer
   who has not seen any parser prediction for the case, with the original label
   treated as absent rather than as a prior.
2. **Replacement.** Construction of a new case in the same registered stratum
   and subtype slot.

**No old semantic label may be mechanically coerced into the new ontology.** In
particular the four `present_unextractable` cases may not be re-badged.

### 6.4 Population invariants of the migrated set

The final set must satisfy, before sealing:

* exactly 120 unique cases;
* exactly 10 cases in each of `S01`–`S12`;
* class supports of 80 `present`, 30 `no_answer`, 10 `ambiguous`, derived from
  the registered stratum presence;
* every registered subtype slot filled as the public stratum definitions
  require;
* every span literal-only and admissible to the frozen instrument.

### 6.5 Replacement selection

Rules for selecting replacement cases must be **registered before** private
review begins, and must not use parser predictions. Concretely, replacement
selection may not condition on whether parser v3, parser v2 or the legacy parser
succeeds on a candidate case, and may not be re-run after seeing a prediction.
A replacement is drawn to fill a named stratum and subtype slot, not to fill a
performance gap.

---

## 7. Prospective policy versus set-derived facts

The structural cause of `H9` was that one artifact carried both a prospective
commitment and an implied factual claim about a set, with no mechanical check
between them. The two are now separate artifacts with separate lifecycles.

### 7.1 Prospective evaluation policy

`docs/phase1_parser_v3_v2_evaluation_policy.json`. Authored by hand, registered
before a set exists, and containing **no set-derived fact**:

* ontology and truth-table identity;
* construction quotas;
* threshold formulas or numeric thresholds;
* comparator policy;
* `PASS` / `FAIL` / `INVALID` logic;
* mandatory-gate definitions.

### 7.2 Set-derived facts manifest

Produced mechanically from a candidate set and containing **no policy choice**:

* actual enum vocabulary;
* actual class supports;
* stratum counts;
* gate denominators;
* member list and object count;
* set and member hashes.

**Derived facts and asserted facts are not the same thing**, and the manifest
must not be read as though they were. The supports, stratum counts, gate
denominators and every hash are *derived*: they are recomputed from the set's
own bytes and cannot be misstated without detection. `sealed_object_count` and
the member list are *asserted*: they describe a remote storage prefix that no
offline tool can list, so a consistent misstatement of both is undetectable
here. A future round must record which listing artifact witnesses them, and the
compiled contract must name it. This is stated explicitly because `12` is
precisely the number the Phase 1.2D erratum exists to correct.

### 7.3 What "derive from the set" means

It means: mechanically reproduce and verify the declared facts. It does **not**
mean silently rewriting a prospective quota or threshold to match whatever
distribution was observed. A disagreement between the two artifacts is a
statement about the set, never a licence to move the policy.

**No entry point accepts a facts manifest on its own.** `check`, `compile` and
`verify` each require the labels and inputs the manifest claims to describe,
re-derive the manifest from them, and require byte-equality before any
comparison runs. A manifest is evidence about a set only in the presence of that
set; alone it is an unverified assertion, and consuming an unverified assertion
as though it were a derived fact is how the `parser-v3-v1` gate contract came to
exist. An implementer who rebuilds this tooling without that binding has
rebuilt the `H9` hole, whatever else they get right.

The compiler enforces this. It emits a final contract only when every declared
invariant agrees, and it has no code path that edits a threshold. It also has no
overwrite flag: a compiled contract is never amended in place.

### 7.4 Independent derivation of the supports

The target supports were derived from the public stratum definitions, not by
substitution from the parser-v2 contract and not from any parser-v3 prediction:

```
present    S01 S02 S03 S04 S05 S06 S09 S12   8 strata x 10 = 80
no_answer  S07 S08 S10                       3 strata x 10 = 30
ambiguous  S11                               1 stratum  x 10 = 10
                                                          --- 120
```

These values coincide with the parser-v2 supports because both sets instantiate
the same registered 12-stratum design at the same 10 cases per stratum. The
coincidence is shown rather than assumed, and the derivation is re-checked by
`validate_policy`, which rejects any support block that is not reproducible from
the declared stratum presence.

### 7.5 Mandatory gates

Mandatory gates are derived from stratum *purpose*, which is a public design
fact, and therefore need no calibration:

| Gate | Population | Minimum denominator | Tolerance |
| --- | --- | --- | --- |
| `G_S06_last_number_trap` | `S06` | 10 | 0 errors |
| `G_S11_ambiguity_detection` | `S11` | 10 | 0 errors |
| `G_S10_unrecoverable_no_answer` | `S10` | 10 | 0 errors |
| `G_S07_truncated_no_answer` | `S07` | 10 | 0 errors |
| `G_S08_explicit_no_answer` | `S08` | 10 | 0 errors |
| `G_clean_strata_exact` | clean strata | 40 | 0 errors |
| `G_present_class_non_vacuous` | `present` | 80 | — |
| `G_no_answer_class_non_vacuous` | `no_answer` | 30 | — |
| `G_ambiguous_class_non_vacuous` | `ambiguous` | 10 | — |
| `G_null_collapse_prohibited` | all cases | 120 | 0 errors |

Zero tolerance on the first six follows from what the stratum is for: `S06`
exists only to detect selection of a trailing distractor, so one such selection
is the failure the stratum was built to find. It is not a calibrated threshold.

**A mandatory gate with a zero denominator is an error.** It is never reported
as `NA`, never skipped, and never counted as satisfied. That was `H3`.

### 7.6 Unresolved: acceptance thresholds

The numeric acceptance thresholds are **`REVIEW_REQUIRED`** and are the reason
this round cannot finalise the policy. See §10.

---

## 8. Tooling

| Artifact | Role |
| --- | --- |
| `src/jspace_observation/parser_v3_repair_ontology.py` | Truth table, stratum-presence map, fail-closed record and set validator. |
| `src/jspace_observation/parser_v3_repair_normalization.py` | `N1`–`N6` as pure functions, quarantine reasons, content-free receipt. |
| `src/jspace_observation/parser_v3_repair_contract.py` | Count kinds, set-facts builder, agreement validator, contract compiler. |
| `scripts/parser_v3_repair_cli.py` | `facts`, `check`, `normalize`, `compile`, `verify`. |
| `docs/phase1_parser_v3_v2_evaluation_policy.json` | The prospective policy. |
| `tests/test_parser_v3_repair.py` | Synthetic fixtures and regression tests. |

Fail-closed conditions in the ontology validator: unknown typed-decision class;
inconsistent presence/validity/ambiguity flags; `present` without a canonical
answer; invalid ambiguous cardinality; invalid `S11` candidate structure;
`output_quality = empty` with non-empty output; marker-inclusive or otherwise
inadmissible spans; non-canonical reference answers; candidate lists that
disagree with the spans; duplicate or missing case ids; invalid stratum totals.

Rejection codes in the agreement validator map to the historical defects:
`H1` layout and membership, `H2` schema and case count, `H3` vacuous or
under-populated mandatory gates, `H5` span convention, `H8` ontology,
`H9` vocabulary and support.

The compiler refuses to overwrite an existing contract, is byte-stable, supports
`verify` re-derivation, records complete provenance bindings, and refuses to
compile from a policy whose status or thresholds are `REVIEW_REQUIRED`.

---

## 9. What this round establishes, and what it does not

Established: a public repair protocol; a prospective policy whose derivable
parts are derived and shown; tooling that makes `H1`, `H2`, `H3`, `H5`, `H8` and
`H9` mechanically detectable before sealing; and synthetic evidence that the
tooling behaves as specified.

Not established, and not claimed:

* Parser v3 is **not** validated, **not** shown non-regressive, **not** shown
  improved, and **not** accepted. Its formal evaluation ordinal remains `0`.
* The new tooling has **synthetic-test evidence only**. It has never been run
  against a real curated set, because no admissible set exists.
* No `parser-v3-v2` set exists, is authorized, or is under construction.
* **No J-space, hidden-reasoning, internal-workspace or invisible-CoT
  conclusion follows from anything in this round.** This is evaluation
  plumbing.

---

## 10. Terminal status and the next gate

An unresolved scientific design choice remains, so this round terminates
`BLOCKED` rather than `READY_FOR_INDEPENDENT_SET_REPAIR`.

**The blocker.** The numeric acceptance thresholds — overall exact
typed-decision minimum, per-stratum critical floor, answer-presence macro `F1`
minimum, and the non-regression margin against parser v2 — cannot be justified
in this round. The two available shortcuts are both
inadmissible: importing the parser-v2 constants would carry over an unjustified
number of exactly the kind this phase exists to eliminate, and deriving a
threshold from any parser-v3 observation would select the threshold against the
measurement it is meant to bound.

> **Erratum E-1.2F-01 (Phase 1.2F).** This paragraph and the next gate below
> originally named the Phase 1.0C headroom calibration as the calibration that
> would justify these thresholds, and described it as not run. Both claims are
> withdrawn. Phase 1.0C had already executed and finalized `INCONCLUSIVE` at
> `06eec993` when this was written, and it could never have justified a parser
> threshold in any case: it screens *target-model* observable-answer task
> headroom, whereas a parser threshold concerns *parser* extraction fidelity.
> Phase 1.2F re-derived the thresholds; see
> `docs/phase1_2f_parser_acceptance_policy_protocol.md`.

They are recorded as `REVIEW_REQUIRED` in the prospective policy, and the
compiler refuses to emit a contract while any of them is open. The refusal is
tested. This is the intended behaviour of a fail-closed design, not a defect in
the tooling: everything that could be derived in this round was derived, and the
one thing that could not be is visibly marked rather than quietly guessed.

**Everything else is complete.** The protocol, the ontology, the span
convention, the migration rule, the policy/facts separation, the tooling and the
tests are all delivered and green.

**The next gate** is the resolution of the acceptance thresholds. *(Superseded
by Phase 1.2F, which audited all four and left one non-vacuous criterion,
`residual_critical_exact_budget`, blocked on a downstream parser-error budget
that the scientific plan does not register. See
`docs/phase1_2f_parser_error_budget_calibration_protocol.md`.)*
Until that gate passes, no `parser-v3-v2` construction, review, sealing,
preregistration, image build, Stage P or Stage E may begin.
