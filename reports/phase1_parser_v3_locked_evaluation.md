# Phase 1.2D — parser-v3 locked evaluation: HALTED before preregistration

**Status: no formal result. The one-shot holdout is `SEALED` and unspent.**

```
Outcome                            HALTED in preflight
Formal PASS / FAIL                 none produced
Preregistration commit this round  none created
Holdout state                      SEALED, unspent
Holdout objects                    15
Locked inputs read                 0
Locked labels read                 0
Prediction streams generated       0
Authorization lock                 not created
State chain                        not bootstrapped
ACA job                            not created
Formal evaluation ordinal          0
```

This document reports why the round was stopped. The full technical record is
`docs/phase1_parser_v3_locked_evaluation_protocol.md` §15; the decision and the
options rejected are in `docs/decision_log.md`.

---

## 1. What was supposed to happen

Preregister, build one immutable image, bootstrap the state chain, run Stage P
to produce three prediction streams (parser v3 candidate, parser v2 comparator,
legacy comparator), seal them, open the labels under transaction, run Stage E,
emit one formal `PASS` or `FAIL`, retire the holdout, and recompute
independently.

## 2. What actually happened

Preflight found that three artifacts do not describe the same thing:

- the **sealed parser-v3 validation set** (`evaluator_sets/parser_v3_v1`, built by
  `scripts/build_parser_v3_validation_set.py`),
- the **frozen scoring instrument** (`src/jspace_observation/evaluator_validation.py`,
  hash-pinned at `63eb1c7d8b229dddafdd3d54a0d62bb415d76ae8dd5aab220bd91ff054f08344`),
- the **parser-v3 acceptance gates** (`docs/phase1_parser_v3_acceptance_gates.json`).

Nine findings, `H1`-`H9`, are tabulated in §15.3 of the protocol. Severity
ranges from a two-record canonicalisation issue to one that makes the set
unscorable by anything.

## 3. The decisive finding

`H9` involves no instrument. It is a direct disagreement between the sealed set
and its own gate contract.

| | gate contract declares | sealed set actually contains |
|---|---|---|
| typed-decision vocabulary | 3 classes, `null_collapse_prohibited: true` | **4** classes — adds `present_unextractable` (4 cases) |
| `typed_decision_support` | `{ambiguous: 10, no_answer: 30, present: 80}` | `{present: 91, no_answer: 23, ambiguous: 6}` |
| strata | 12 × 10 = 120 | 12 × 10 = 120 ✓ |

The gates `ambiguity`, `no_answer`, `answer_presence_macro_f1` and
`overall_exact_typed_decision` are calibrated against the declared support, so
against the real set their difficulty is different and unknown. The fourth
decision class has no gate treatment and cannot be collapsed into `no_answer`
without violating the contract's own prohibition.

No instrument — frozen, adapted, or purpose-built for v3 — can score this set
against these gates. The defect is in the artifacts, not the tooling.

## 4. Root cause

The v3 gate contract was **derived from the v2 contract by substitution**
rather than re-derived from the v3 set. The evidence is direct: the
`last_number_trap` gate blocks in the two contracts are byte-identical,
including a `denominator` of 10 and an `error_definition` naming a registered
distractor span that the v3 set does not contain. The support counts and the
decision vocabulary were inherited the same way.

Meanwhile the set was built to its own conventions — marker-inclusive evidence
spans, competing-candidate-only candidate lists, a `present_unextractable`
decision class. Nothing tested that the set and the contract agreed.

## 5. Two preflight instruments found everything

**Write-blocked dry run.** The real custodian bootstrap runs against real
storage with `core.upload_blob_once` replaced by a sentinel that raises a
`BaseException` subclass. Every read, binding and validation path executes
exactly as in production; the first attempted write aborts the process. Zero
side effects. Found `H1`.

**Projection probe.** The sealed label set is projected into the frozen
final-label schema and handed to the *frozen* validator. The frozen instrument,
not the projection, judges admissibility. Found `H2`, `H3`, `H5`, `H6`, `H7`,
`H8`. `H9` then fell out of comparing the set directly against the contract.

Both are read-only and neither touched the sealed holdout. Both are now
standing preflight requirements.

## 6. What was salvaged

Six normalisations (`N1`-`N6`, protocol §15.4) are validated and recorded for
reuse. All are deterministic, parser-free and recomputable from sealed bytes.

```
labels                                   120
projected and frozen-valid                105    (up from 22 with no normalisation)
typed_decision preserved                  105 of 105
typed_decision changed                    0
S06 cases where last_number_trap can fire  10 of 10
residual failures                          15    (semantic, not representational)
```

`N4` (S06 distractor = rightmost registered numeric literal) and `N5`
(`secondary_tags` = content-derived quota features) are not inventions: the
frozen instrument already *requires* registered values to equal exactly those
derivations. Without `N4` the mandatory `last_number_trap` gate is vacuous —
it would have passed unconditionally while appearing enforced.

The 15 residual records differ semantically and were not forced.

## 7. What was rejected, and why

| Option | Rejected because |
|---|---|
| Score the 105 valid records | The contract fixes 120 cases, 10 per stratum and every gate denominator. This is a population change. |
| Preregister a mapping for the 15 | They differ semantically. Mapping `present_unextractable` to `no_answer` is exactly the collapse the contract prohibits. |
| Amend the contract now and run | Support counts would be rewritten after observing the set, and thresholds were calibrated against the old support. A threshold and population change dressed as a correction, days before an irreversible run. |
| Author a v3-native instrument now | Same objection, plus: the frozen instrument's hash pinning is the trust anchor of the protocol. A new instrument written immediately before a one-shot run and reviewed by nobody defeats the point. |

## 8. Cost of halting

Nothing irreplaceable. The holdout's one-shot budget is untouched. Parser v3 is
unchanged and frozen at source SHA-256
`76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9`
(implementation commit `310277bcadd67ca9e77986fc292fae47dc5ceda2`). Because no
preregistration commit was created this round, the parser, gate contract,
profile binding and membership rules remain editable — which the remediation
requires.

## 9. Disclosure

Diagnosing `H2`, `H3`, `H5`-`H9` required reading aggregate structural metadata
of the **local curator copy** of the v3 labels (git-ignored): field names, enum
vocabularies and their counts, spans- and candidates-per-record histograms,
stratum and decision-class counts, masked numeric shapes (every digit replaced
by `#`), and per-record structural flags for the 15 residual records.

No `registered_reference_answer`, `expected_parsed_answer`,
`expected_candidate_answers`, span text, span offset or `output_text` value was
read. The sealed holdout blobs were never read. Recorded as `H4` in §15.7.

Bias risk on any future evaluation is nil — parser v3 was frozen before this
diagnosis and was not modified — but the read is disclosed regardless.

## 10. Scientific boundaries

Parser v3 must not be described as validated, non-regressive, or better than
parser v2. No parser-v3 gate result exists. No parser-v3 acceptance threshold
in this repository may be cited as calibrated. Parser v2's failed locked
evaluation remains the only locked parser result in this project. Nothing here
licenses any claim about hidden reasoning, an internal workspace, or a J-space.

## 11. Next gate

1. Re-derive the parser-v3 gate contract from the parser-v3 set: every support
   count, gate denominator and enum vocabulary computed from sealed bytes.
2. Resolve `present_unextractable` explicitly — admit it with its own gate
   treatment, or rebuild those cases. Do not collapse it silently.
3. Reconcile the label ontology with the scoring instrument: S11
   minimum-candidate rule, `ambiguous` / `parse_valid` semantics, and the
   `output_quality = empty` definition.
4. Freeze one span convention across the set and all three parsers, with an
   artifact-level agreement test.
5. Add a mechanical preregistration check that reproduces the contract from the
   sealed set before any image is built. It is a pure function of two sealed
   artifacts and would have caught `H9` immediately.
6. Keep both preflight instruments as standing steps.
