# Phase 1.2E — Parser-v3 evaluation ontology repair (tooling-only round)

**Terminal status: `BLOCKED`**

**Round type:** public tooling, protocol, and documentation only.
**Round baseline commit:** `45a18f4221ca68c0bceac6e5481c9c52de7a2521`
**Protocol:** `docs/phase1_2e_parser_v3_ontology_repair_protocol.md`
**Prospective policy:** `docs/phase1_parser_v3_v2_evaluation_policy.json` (status `REVIEW_REQUIRED`)

This report records what was built, what was tested, what was audited, and — with
equal weight — what was deliberately *not* done. Nothing in this round touched a
private holdout, produced a prediction, or moved parser v3 any closer to being a
validated instrument.

---

## 1. Why this round exists

Phase 1.2D halted in preflight after finding nine defects (`H1`–`H9`) in which the
sealed `parser-v3-v1` holdout, the frozen scoring instrument, and the parser-v3 gate
contract described three mutually incompatible evaluation problems. The most severe,
`H8`, is an ontology defect: 15 of the 120 sealed cases carry a fourth typed decision,
`present_unextractable`, that neither the frozen scoring semantics nor the candidate
parser can represent. There is no admissible repair of that inside the sealed set: any
mapping of `present_unextractable` onto `present`, `no_answer`, or `ambiguous` is a
silent relabelling of the ground truth after the set was built.

Phase 1.2E therefore does the only thing that is scientifically available without
touching private data: it builds and tests the *public* machinery a future,
independently curated `parser-v3-v2` set would have to pass through, so that the same
class of defect cannot survive to preflight again.

**`parser-v3-v1` is not repaired by this round and is not repairable.** Its recorded
disposition is now, permanently:

```
SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE
```

"Unspent" is a statement about label access — no locked label was ever read — not a
licence to reuse the set later.

---

## 2. Count terminology (erratum)

`reports/phase1_parser_v3_locked_evaluation.md` previously reported
`Holdout objects 15`. That was a factual reporting defect: it conflated the number of
storage objects with the number of semantically incompatible cases, which coincidentally
share the value 15. The corrected, now separately named counts are:

| Name | Value | Meaning |
| --- | --- | --- |
| `sealed_object_count` | **12** | Blob objects under the sealed `parser_v3_v1/` set prefix |
| `total_case_count` | **120** | Evaluation cases in the set |
| `residual_semantic_case_count` | **15** | `H8` cases carrying the unrepresentable fourth class |
| `prediction_stream_count` | **0** | Prediction streams produced against the set, ever |
| `score_state_object_count` | **0** | Score/state objects produced against the set, ever |

The listing that produced the original `15` enumerated the parent prefix and also swept
in three runlog objects that are not members of the sealed set: 2 in the sibling
`…160340Z-runlog/` prefix and 1 orphaned `crosscheck_report.json` under the aborted
`…155224Z-runlog/` prefix, left behind when the first seal attempt failed closed on its
own `overwrite=false` guard. That reconciliation is inferred from the Phase 1.2D sealing
pack — `05_summary.md:43` for the independent 12+2 listing, deviation `D10` for the
orphan — and was not observed this round, which made no Azure call of any kind. The
erratum is recorded in place in the locked-evaluation report, and the confusion itself is
now a regression test (`test_count_kinds_reject_object_case_confusion` and neighbours) so
the two numbers cannot be silently interchanged again.

---

## 3. What was built

### 3.1 `src/jspace_observation/parser_v3_repair_ontology.py` (586 lines)

The formal three-class ontology and its fail-closed validator.

- `TYPED_DECISION_CLASSES` — exactly `present:<canonical_value>`, `ambiguous`,
  `no_answer`. No fourth class is admissible in a formal set.
- `RESEARCH_ONLY_TYPED_DECISION_CLASSES` — `present_unextractable`, preserved as a named
  research construct so it can be studied later, explicitly excluded from formal sets,
  and never collapsed into another class.
- `TRUTH_TABLE` — three rows binding `answer_presence`, `parse_valid`, `parse_ambiguous`,
  `parsed_answer`, candidate cardinality, evidence-span requirement, and allowed
  `output_quality` to a single `typed_decision`. Any record not matching exactly one row
  is rejected.
- `STRATUM_PRESENCE` — the public map from each of `S01`–`S12` to its expected decision
  class, derived from `evaluator_sets/parser_v3_v1/strata_definitions.md`.
- `derive_typed_decision`, `validate_ontology_record`, `validate_ontology_set`.

Span admissibility is *delegated* to the frozen instrument's own
`validate_evidence_span`, not re-implemented, and then further narrowed to literal-only.
A span the scoring instrument would reject therefore invalidates the set before sealing,
which is precisely the `H5` failure mode.

The same principle is applied to the record as a whole by
`_bind_to_scoring_instrument`, which is the load-bearing function of the module. After
the table's structural checks pass, every record is handed to the frozen
`_validate_extraction_fields` and `derive_typed_decision`, and the derived decision must
equal the one the table assigned. The module therefore *binds* to the scoring instrument
rather than paraphrasing it. §6 records what happened when it merely paraphrased.

### 3.2 `src/jspace_observation/parser_v3_repair_normalization.py` (554 lines)

`N1`–`N6` as pure functions, plus `normalize_record` / `normalize_set`.

Properties enforced by construction and by test: deterministic, idempotent,
typed-decision preserving, value-free in all logging, and parser-free in the differential
sense set out in §5.1. `NormalizationReceipt` carries counts and hashes only — no answer
values, span text, offsets, or case-level labels — and includes
`normalized_content_digest`, so a receipt commits to the output it describes.

Preservation is enforced through `scoring_projection`: the projection of every field the
frozen instrument reads is compared before and after each rule, and any change outside
the rule's registered licence quarantines the case. This replaced an earlier check that
compared three fields no rule writes, and so could never fail.

When a rule is ambiguous outside its registered tie-break the function **fails closed and
quarantines the case** (`QuarantineReason`) rather than guessing. `N1`'s tie-break is
registered explicitly: among contained registered numeric matches, prefer those whose
canonical value equals the declared normalized answer, then take the rightmost. If no
contained literal matches the declared value, `N1` **refuses** — it may relocate a span,
never change the value that span asserts.

Ordering `N1→N2→N3→N4→N5→N6` is load-bearing: `N5` reuses the instrument's
`_surface_features`, which requires the `output_text` that `N3` establishes.

### 3.3 `src/jspace_observation/parser_v3_repair_contract.py` (823 lines)

The artifact-agreement validator and the contract compiler.

- `COUNT_KINDS` / `SetCounts` — a type-level guard separating blob objects, evaluation
  cases, residual invalid cases, prediction streams, and score/state objects.
- `validate_policy` — mechanically re-derives the declared class supports from the public
  stratum-presence map and rejects any support block it cannot reproduce.
- `build_set_facts` — the set-derived facts manifest: actual enum vocabulary, actual class
  and stratum supports, gate denominators, member list and object count, set and member
  hashes. `set_sha256` digests the **set**; `facts_sha256` is a separate integrity seal
  over the manifest.
- `SetSource` / `_require_derivable` — a facts manifest is never trusted on its face. Every
  entry point takes the labels and inputs it claims to describe, re-derives the manifest,
  and requires byte-equality before comparing anything. A fabricated or hand-edited
  manifest is rejected outright.
- `check_agreement` — compares the prospective policy against the *re-derived* facts and
  emits findings coded to the original defects: `H1` layout, `H2` schema, `H3` vacuous
  gate, `H5` span, `H8` ontology, `H9` vocabulary/support. A zero denominator on a
  mandatory gate is an **error**, never `NA`, skip, or pass. The pure comparison is also
  exposed as `agreement_findings` so each detector can be tested in isolation.
- `compile_contract` / `write_contract` / `check_contract` — deterministic, byte-stable,
  refuses to overwrite an existing contract, supports `verify` re-derivation, carries
  complete provenance bindings, and **never adjusts a threshold to make a set acceptable**.

### 3.4 `scripts/parser_v3_repair_cli.py` (362 lines)

Subcommands `facts`, `check`, `normalize`, `compile`, `verify`. `check` is read-only.
`_guard_every_path` runs before any file is opened and hard-refuses any invocation naming
the `parser_v3_v1` namespace on *any* path argument, case-folded and separator-insensitive,
with no override flag. `check`, `compile` and `verify` all require the set itself, because
a facts manifest alone is not admissible evidence. `normalize` exits non-zero whenever any
case was quarantined unless `--permissive` is given.

### 3.5 `docs/phase1_parser_v3_v2_evaluation_policy.json` (209 lines)

The prospective policy artifact, deliberately separated from any set-derived fact.
Contains the ontology, construction quotas, comparator policy, PASS/FAIL logic, and ten
mandatory-gate definitions. Status is `REVIEW_REQUIRED`; see §7.

### 3.6 `docs/phase1_2e_parser_v3_ontology_repair_protocol.md` (544 lines)

The round protocol: old-set disposition, new set identity, the three-class truth table,
the one-span convention, the future migration rule for the existing 120 cases, the
policy/facts separation requirement, the tooling contract, and the explicit non-claims.

### 3.7 `tests/test_parser_v3_repair.py` (1 790 lines, 122 tests)

See §5.

---

## 4. Support derivation (not substitution)

The brief requires that target supports and thresholds be derived independently from the
public stratum definitions and scientific policy, not textually copied from parser v2 —
because copying the v2 contract is exactly how `H9` happened.

The class supports are derived as follows, from `STRATUM_PRESENCE` alone:

| Class | Strata | Derivation | Support |
| --- | --- | --- | --- |
| `present` | S01–S06, S09, S12 | 8 strata × 10 cases | **80** |
| `no_answer` | S07, S08, S10 | 3 strata × 10 cases | **30** |
| `ambiguous` | S11 | 1 stratum × 10 cases | **10** |

This reproduces the familiar `80/30/10` figures, and the derivation is shown rather than
asserted. `validate_policy` re-derives the same block mechanically at check time and
rejects any policy whose declared supports it cannot reproduce, so the numbers cannot
drift back to being an inherited constant.

Note the correction embedded here: the public `strata_definitions.md` places **S10** in
the `no_answer` group, whereas the sealed set labelled S10 as present-bearing. That
disagreement is part of `H9` and is one of the reasons the sealed set is unscorable.

---

## 5. Tests

All fixtures are public and synthetic. No private data of any kind is read by any test.

**Focused suite — `tests/test_parser_v3_repair.py`: 122 passed.**
**Full repository suite — `pytest tests/ -q`: 1 497 passed** (baseline 1 375 + 122 new),
893 s. Zero failures; no test skipped, weakened or removed.

Coverage includes:

- a complete synthetic 120-case, 12-stratum valid set that passes end to end;
- each allowed typed-decision state;
- every `H1`–`H9` defect as a negative regression fixture;
- every `N1`–`N6` transformation, plus idempotence and typed-decision preservation;
- contract compilation determinism and `verify` byte-for-byte reproduction;
- rejection of a fabricated facts manifest, and of one whose seal has been broken;
- rejection of mismatched support counts;
- rejection of an undeclared fourth class;
- rejection of vacuous mandatory gates (zero denominator is an error);
- rejection of inadmissible spans;
- rejection of the `12`-objects vs `15`-cases confusion;
- refusal to overwrite historical artifacts, and refusal of the retired namespace on
  every path flag of every subcommand, including case and separator variants;
- agreement between every truth-table row and the frozen scoring instrument;
- protected-file digest stability across 11 pinned artifacts.

### 5.1 A note on the parser-isolation proof

`src/jspace_observation/__init__.py` eagerly imports the whole package, including
`eval_parsing`. Consequently *any* import from this repository places a parser module in
`sys.modules`, and an absolute assertion of the form "no parser module is loaded" can
never hold and would be a false comfort if it appeared to.

The proof used instead is **differential**: a subprocess imports only
`evaluator_validation`, records `sys.modules`, then imports the three repair modules and
records it again; the delta must be exactly the three repair modules and nothing else.
This is paired with a static test asserting that no repair module references any parser
symbol. Together these establish that the repair tooling adds no parser dependency and
invokes no parser, which is the property that actually matters.

### 5.2 Other checks run

| Check | Result |
| --- | --- |
| `python -m compileall` over changed sources | rc 0 |
| `git diff --check` | clean, exit 0 |
| Credential / secret scan over changed and new files | 0 hits |
| Large-file check (>1 MB) over changed and new files | 0 files |
| Policy JSON well-formedness | OK |
| Protected-file digests (11 artifacts) | 0 changed |

No existing test or gate was weakened, skipped, or relaxed to obtain a green result.

---

## 6. Independent audit

### 6.1 Scope

After the first implementation was complete and green, a separate read-only review
agent audited the round. It was given the seven new artifacts, the frozen scoring
instrument `src/jspace_observation/evaluator_validation.py`, the Phase 1.2D record, the
public stratum definitions, and the Phase 1.2D sealing artifacts. It ran the focused
suite itself, verified the eleven protected digests against `45a18f4`, and probed the
tooling adversarially — fabricating a facts manifest, hand-editing a sealed one,
attempting to compile a contract from a policy with unresolved thresholds, and
attempting to drive the CLI at the retired namespace through each path flag in turn.

The audit found **ten defects: two critical, five major, three minor.** All ten are
recorded below and all ten were fixed. This is the honest headline of the round: the
first implementation pass, which passed 93 self-authored tests, contained two defects
that would each have been fatal if carried into a real evaluation.

### 6.2 The two critical findings

**C1 — the `ambiguous` row contradicted the frozen instrument.** The truth table
declared `parse_valid = false` for `ambiguous`. The frozen instrument requires
`parse_valid = true`: an ambiguity the parser correctly detected is a *valid* parse
whose outcome is "two or more candidates", and `failure_reasons` must be empty exactly
when `parse_valid` holds. Had a `parser-v3-v2` set been built and sealed under the
original table, **every one of the ten `S11` cases would have been rejected by the
scoring instrument** — unscorable by construction. That is precisely the condition that
retired `parser-v3-v1`. The protocol had reproduced the failure it was written to
prevent.

**C2 — the facts manifest was bound to nothing.** `set_sha256` was a digest of the
manifest itself, not of any set. Nothing tied a manifest to the labels and inputs it
claimed to describe. The auditor demonstrated the consequence directly: a manifest
typed by hand, describing a set that had never been built, compiled cleanly into a
signed contract carrying full provenance bindings. The provenance was decorative.

### 6.3 The remaining eight

| # | Severity | Finding |
| --- | --- | --- |
| M1 | major | `N1`'s fallback branch silently rewrote a declared answer to a different value, and an `ambiguous` case could collapse to a single candidate without quarantine. |
| M2 | major | The typed-decision preservation check was structurally unable to fail: its pre-image function read three fields, none of which `N1`–`N6` write. |
| M3 | major | The `present` row was more permissive than the frozen instrument — unbounded candidates, multiple `selected` spans allowed, `failure_reasons` never validated, and the `empty` biconditional tested `== ""` instead of `.strip() == ""`. |
| M4 | major | The erratum's own reconciliation of the number 15 was wrong. |
| M5 | major | The CLI's retired-namespace guard was bypassable through `--members` and `--expect-members`, was not case-folded, and its test called the helper directly instead of driving `main()`. |
| m1 | minor | `assert_parser_free` was dead code that would have failed unconditionally had it ever been called, and three documentation claims of "parser-free — no parser module imported" were literally false. |
| m2 | minor | The normalisation receipt digested only a shape reduction, so it could not commit to its own output. |
| m3 | minor | Seven smaller defects: a documented `--check` flag that does not exist, `normalize` exiting 0 on quarantine, `N4` inflating its own change count, `N5` raising a bare `KeyError`, two unreachable quarantine codes, no hex validation on member digests, and a truth-table test weak enough to pass against a broken table. |

### 6.4 What was changed in response

The textual fixes matter less than the structural one.

`C1` and `M3` share a single root cause: the ontology validator *restated* the frozen
instrument's invariants in fresh code instead of *binding* to them. That is the same
defect as `H9`, which arose because the parser-v3 gate contract was copied from
parser-v2 — a second description, free to drift from the thing it described. Fixing the
`ambiguous` row alone would have left the mechanism that produced the error intact.

The fix is `_bind_to_scoring_instrument`. Every record accepted by the ontology
validator is now passed to the frozen `_validate_extraction_fields` and
`derive_typed_decision`, and the derived decision must equal the one the table assigned.
A record this module accepts is a record the scoring instrument accepts, by construction
rather than by resemblance. Restating an invariant is now impossible to do silently: if
the two ever disagree, the repair tooling fails immediately.

`C2` was fixed by making derivability mandatory. `set_sha256` now digests the set;
`facts_sha256` is a separate integrity seal over the manifest; and `check_agreement`,
`compile_contract` and `check_contract` all take a required `SetSource` and re-derive
the manifest from it, requiring byte-equality before any comparison runs. A fabricated
or edited manifest is rejected before it can be reconciled with anything. A deliberate
consequence is that the `H8`/`H9` detectors are now unreachable via the entry points
for facts-side divergence — the manifest can no longer diverge — so those detectors are
tested through `agreement_findings` directly, and the entry points are tested by
mutating the policy, which is never re-derived.

`M1` now raises rather than substituting: `N1` may relocate a span, never change the
value it asserts. `M2` was fixed in two layers: licensed *scoring projections* are
compared before and after the pipeline, and — the authoritative check —
`normalize_record` validates its own output against the formal ontology before
returning, so any record a rule would render inadmissible is quarantined as a single
case with a reason code rather than escaping to fail whole-set validation later.
`M5` was fixed by hoisting the namespace guard into a pre-pass over every path argument
in `main()`, before any file is opened. `m1` replaced the dead runtime check with a
static source scan and corrected the three false claims to the differential form
described in §5.1.

### 6.5 A second audit round, and what it found

The remediation was re-audited by the same reviewer, which was the right call: it
confirmed eight of the ten fixes as structural — a 4 490-mutant differential sweep found
**zero records the ontology accepts and the frozen instrument rejects** — and found five
further defects, four of them introduced *by the remediation itself*.

| # | Severity | Finding | Fix |
| --- | --- | --- | --- |
| A1 | major | `M2` was only half-fixed. The projection comparison is a whitelist, and seven fields the scorer reads were invisible to it, including `expected_correctness`, `output_text` and `span["text"]`. Three live counterexamples normalised "successfully" instead of quarantining. | `normalize_record` now validates its output with `validate_ontology_record`, a new `FAILS_ONTOLOGY` reason code, and the two overstated documentation claims are corrected. |
| A2 | minor | `_require_derivable` guarded with `isinstance`, so a `SetSource` subclass overriding `derive()` defeated re-derivation entirely. | Exact-type check, and `_require_derivable` now calls the module-level `build_set_facts` directly instead of dispatching through the instance. |
| A3 | minor | `agreement_findings` was listed in `__all__` — a public function that accepts an unverified manifest, which is exactly the hole `C2` closed. | Removed from `__all__`; docstring corrected. |
| A4 | obs. | `write_contract(allow_overwrite=True)` was an untested flag whose only purpose was to violate the protocol's own "never amended in place" invariant. | Parameter deleted. |
| A5 | obs. | `apply_n6_candidate_answers` still leaked a bare `KeyError` on a malformed span, and `_classify` routed quarantine reasons by matching the substring `"beyond the"`. | `N6` fails closed; `NormalizationError` now carries its own `reason`, set at each raise site, and `_classify` is deleted. |

Two further observations were accepted without code change and are recorded as
limitations rather than fixed. First, `sealed_object_count` and the member list are
operator *assertions*, not derived facts: nothing in offline tooling can list a blob, so
a self-consistent lie is undetectable here. This is now stated explicitly in the protocol
rather than left implicit. Second, the whole-set fixture originally exercised `N1` and
`N6` zero times, so idempotence was only ever proved over no-ops for the two
highest-risk rules; the suite now includes a fixture variant with marker-inclusive and
out-of-order spans that forces both rules to apply.

The test count is 122. The count is not the evidence — the binding is — but the
direction of travel is worth noting: every one of the last nine tests exists because a
reviewer found something the author's tests could not.

### 6.5 Residual limitations

The audit was thorough but bounded, and three limits should be stated plainly.

First, **self-authored tests are not independent validation.** The 93 tests that passed
before the audit encoded the same misunderstanding as the code they tested; `C1` was
invisible to them because the fixtures asserted the wrong invariant too. The test count
now stands at 122, but the count is not the evidence — the binding to the frozen
instrument is.

Second, the audit could not exercise the tooling against a real set, because no
admissible set exists and none may be built this round. All evidence remains synthetic.

Third, the auditor examined the refusal path and confirmed it cannot be broken:
`compile_contract` checks policy status and threshold status independently before any
other work, `validate_policy` forbids desynchronising them, and `check_contract`
re-enters `compile_contract`. It explicitly advised against relaxing it. The `BLOCKED`
status in §7 therefore stands on reviewed ground.

`scripts/parser_v3_seal_job.py` remains unaudited; it is untouched by this round and
inherits the Phase 1.2D limitation.

---

## 7. The blocker

The terminal status is `BLOCKED`, by design rather than by failure.

`docs/phase1_parser_v3_v2_evaluation_policy.json` carries status `REVIEW_REQUIRED`
because four numeric acceptance thresholds cannot be justified in this round. Choosing them
now would mean inventing acceptance criteria to fit an instrument whose operating range
has never been measured — which is the same failure that produced the invalid v3 gate
contract in the first place.

> **Erratum E-1.2F-01 (Phase 1.2F).** This paragraph originally stated that the
> thresholds "depend on headroom calibration (Phase 1.0C), which is itself
> `BLOCKED / NOT RUN`". Both halves are withdrawn. Phase 1.0C had executed and
> finalized `INCONCLUSIVE` at `06eec993` before this was written, and it is
> target-model task/headroom screening, so it could not have supplied a parser
> threshold even if pending. The false claim entered this report from a stale
> current-state summary in `reports/current_status.md` that had never been
> updated after the calibration ran.

`compile_contract` therefore refuses to compile while any threshold remains open, and
that refusal is itself tested (`test_compiler_refuses_a_review_required_policy`). The
tooling is complete; the *policy* is deliberately unfinished.

Everything the brief scoped as `READY_FOR_INDEPENDENT_SET_REPAIR` — protocol, ontology,
normalizer, agreement validator, contract compiler, CLI, tests, documentation — exists and
passes. The residual open decision is scientific, not mechanical.

---

## 8. Private-access ledger

| Quantity | Count |
| --- | --- |
| Sealed inputs read | **0** |
| Sealed labels read | **0** |
| Local private / git-ignored curator files read | **0** |
| Predictions generated | **0** |
| Parser invocations on locked data | **0** |
| Azure writes or resource changes | **0** |
| Evaluation images built or reused | **0** |
| Authorization locks or state chains created | **0** |
| Stage P runs | **0** |
| Stage E runs | **0** |

The formal evaluation ordinal remains **0**. No formal parser-v3 `PASS` or `FAIL` exists.

---

## 9. Protected artifacts

Eleven protected artifacts were hashed before and after the round; all eleven are
unchanged. The pinned digests live in `tests/test_parser_v3_repair.py::PROTECTED_DIGESTS`
and are re-checked on every test run, so a future edit to any of them breaks the suite.

Parser v3 remains byte-identical:

- canonical source SHA-256 `76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9`
- raw / LF blob SHA-256 `dd729c3c23771fb112811e382bf7e55f531ce534cbbd1cfec4f0527056c8908e`

Parser v3 was not formally re-frozen by Phase 1.2D; it is voluntarily protected here.

---

## 10. What this round does not establish

Stated explicitly, because the temptation to over-read a green test suite is the whole
reason this project keeps ledgers:

- No private holdout was accessed.
- No prediction was generated.
- No formal evaluation occurred.
- **Parser v3 remains unvalidated.** It is not shown to be correct, non-regressive,
  improved, or accepted.
- The new tooling has **synthetic-test evidence only**. It has never been run against a
  real evaluation set, because no eligible real set exists.
- Self-authored tests are not independent validation. Only the audit recorded in §6 is
  external to the implementation, and its scope and limits are stated there.
- **No J-space, hidden-reasoning, internal-workspace, or invisible-chain-of-thought
  conclusion follows from anything in this round.** This round is entirely about
  measurement hygiene for a parser.

---

## 11. Next gate

*(Superseded by Phase 1.2F — see `reports/phase1_2f_parser_acceptance_policy.md`.
The four thresholds were audited: two express the same constraint, one provides
no independent protection while masking value errors, and one is not derivable
prospectively. The single surviving criterion is
`residual_critical_exact_budget`, blocked on a downstream parser-error budget
that the scientific plan does not register.)*

Resolve the `REVIEW_REQUIRED` acceptance thresholds and promote
`docs/phase1_parser_v3_v2_evaluation_policy.json` to status `FINAL`.

Until that gate is passed, do not begin `parser-v3-v2` construction, sealing,
preregistration, image construction, Stage P, or Stage E.
