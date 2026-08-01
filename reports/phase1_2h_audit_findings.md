# Phase 1.2H — Independent audit record (Audit F)

Phase: 1.2H
Baseline: `origin/main` at `0480f4f`
Supplements: `reports/phase1_2g_audit_findings.md`

---

## 1. Why this document exists

The Phase 1.2G acceptance policy recorded a disclosed gap in its own review
provenance:

> "Each of the three re-reviews found defects in the remediation of the previous
> one; the remediation of Audit E's findings was not itself independently
> re-reviewed, and the review regress was terminated by disclosure rather than by
> reaching a fixed point."

That was an honest statement of an unclosed loop. Phase 1.2H closed it. This
document records **Audit F** — the independent re-review of the Audit E
remediation — its findings, their remediation, and the final-state re-review.

## 2. Audit F — method and scope

A read-only reviewing agent was commissioned with a narrow scope: the six
Audit E remediations `R3-NEW-01` … `R3-NEW-06`, and only those. Re-litigating
the strict-finite-suite premise, the threshold dispositions, or any settled
Phase 1.2F/1.2G decision was explicitly out of scope, so that the review could
not drift into re-opening decisions the operator had already taken.

**Verdict: FINDINGS — 0 blockers, 5 majors. All six remediations incomplete.**

Every finding came with a working counterexample. That is the standard this
repository's audits have converged on, and it is why they keep finding real
defects: a claim that a guard is too weak is cheap, and a string that slips past
it is not.

### 2.1 Independence — stated precisely

The reviewer is an automated agent operating on this repository. It is
independent **of the authoring pass**; it is not independent **of the project**,
and no external human reviewer has approved anything here. Self-authored tests
are not independent validation and are not described as such anywhere in this
record.

## 3. Findings and remediation

### F-01 — MINOR — the review provenance was incomplete

`review_provenance.reviewers` listed Audits C, D and E with finding counts and
blocker counts, and listed Audits A and B without them. A reader comparing the
entries would reasonably infer that A and B found nothing worth counting.

**Fact:** Audit A returned 5 findings including 1 blocker (`A-01`). Audit B
returned 11 findings including 1 blocker (`B10`), of which 4 (`B1`, `B7`, `B8`,
`B9`) duplicated Audit A findings.

**Fix.** Both entries now carry counts. Audit F is recorded as a sixth reviewer.
The `limitation` no longer claims the Audit E remediation was never re-reviewed,
because that is now false; it states instead that *every* re-review so far has
found defects in the previous remediation — including Audit F, which reopened
all six — and that the correct reading is that the artifact has been repeatedly
corrected, not proven correct. A `supplementary_record` pointer to this file was
added.

**Pinned by** `test_f01_the_review_provenance_records_every_audit_with_counts`.

**Consequence.** The policy bytes changed, so its SHA-256 moved from
`e8d4391387f4f6682d9a947f58a4586ce0c110c16c3f66e4250b134690eb9114` to
`fda448869aba01bf75e865f38a2e0f35485b83890f9088c50e05e661bfe3421c`. Exactly one
block changed. This was a deliberate choice over recording the counts only in a
report: an incomplete provenance record inside the artifact is a defect of the
artifact, and fixing it elsewhere would leave the artifact wrong.

### F-02 — MAJOR — the superseded-figure negation was still sentence-wide

Audit E's remediation narrowed the negation *vocabulary* but left the *scope*
sentence-wide. The auditor supplied two sentences that assert the retired figure
as fact and were nonetheless exempted. Quoted defects, both superseded:

> `The mandatory gates pin 90 of 120 cases, not 80 of 120 cases.`
>
> `The mandatory gates pin 90 of 120 cases rather than 80 of 120 cases.`

In both, the negation belongs to the **replacement** number. A sentence-wide
search cannot tell the difference.

**Fix.** A denial now counts only when it is **positionally attached** to the
matched figure. Pre-markers must sit immediately before the match; post-markers
immediately after it; both remain confined to the enclosing sentence. A new
`_enclosing_sentence_with_offset` supplies the offset that makes attachment
decidable.

Two secondary corrections came out of the same work:

* A pre-marker may be separated from its figure by one copular or prepositional
  connective (`as`, `to`, `at`, `of`, `being`, `reading`). Without this,
  `previously listed` could only fire in the ungrammatical form "previously
  listed 90 of 120" — the vocabulary entry claimed a coverage it did not have.
* **Mention frames** (`the claim that …`, `the old text said …`) exempt only
  when the *same clause* also carries a falsity or supersession marker. A frame
  alone is not a denial. Quoted defect, superseded:

  > `the claim that 90 of 120 cases are pinned is correct`

  That is still an assertion, and is still caught.

**Pinned by** `test_f02_a_denial_aimed_at_the_replacement_figure_is_not_an_exemption`,
`test_f02_a_denial_in_a_different_clause_is_not_an_exemption`,
`test_f02_attached_denials_and_mention_frames_remain_exempt`,
`test_f02_a_mention_frame_alone_is_not_a_denial`.

### F-03 — MAJOR — a malformed table delimiter still enabled redaction

The delimiter test was `all("--" in cell for cell in cells)`. The auditor showed
that `| ---:--- | --- |` passes it, so a row that is not a Markdown delimiter
could still switch on column redaction and hide a live claim.

The auditor also checked the performance concern raised in the previous round
and found it unfounded: 5,000 dashes resolved in under 2 ms.

**Fix.** `_is_delimiter_cell` strips at most one leading and one trailing `:`
and then requires at least two characters, all `-`. Linear, no backtracking.
`---:---` is rejected; `---`, `:---`, `---:` and `:---:` are accepted.

**Pinned by** `test_f03_a_malformed_delimiter_cell_does_not_enable_redaction`.

### F-04 — MAJOR — one level of JSON nesting hid a whole claim

Record windows joined only a mapping's **own** scalar siblings. The auditor
moved the disposition down one level. Quoted defect, superseded:

> `{"threshold_id": "critical_stratum_floor", "decision": {"disposition": "REMOVE_REDUNDANT"}}`

Neither window saw both halves, and `validate_policy` accepts that nesting — so
the guard was avoidable by restructuring alone.

**Fix.** Each mapping's window now carries the scalar fields of its **ancestors**
as well as its own. This is not the manufactured adjacency the original note
warned against: every ancestor on the path genuinely co-describes the node, so
the pairing is one the document really makes. Siblings in unrelated subtrees are
still never joined, and that invariant is now tested directly rather than left
implicit.

**Pinned by** `test_r3new04_an_ancestor_scalar_reaches_a_nested_mapping`,
`test_r3new04_unrelated_subtrees_are_still_never_joined`.

**Superseded test.** `test_r3new04_a_nested_mapping_is_not_flattened_into_its_parent`
asserted the old behaviour and has been replaced. It was not deleted to obtain a
green result; the behaviour it pinned was found to be the defect.

### F-05 — MAJOR — undeclared execution counters were silently accepted

`_validate_execution_state` validated the counters it knew by name and ignored
everything else. The auditor added

```json
"parser_v3_v2_evaluations_run": 1
```

next to the validated zeros, and the policy passed — asserting an execution the
contract exists to forbid.

**Fix.** `execution_state` is now a **closed schema**. `EXECUTION_STATE_KEYS`
enumerates every permitted field; an unrecognised key is a defect regardless of
its value, and a missing key is reported explicitly. Widening the set requires a
deliberate edit to that list, which is the point. The specific
`sealed_sets_constructed` diagnostic is checked first so its more informative
message survives.

**Pinned by** `test_f05_an_undeclared_execution_counter_is_rejected`,
`test_f05_an_undeclared_counter_is_rejected_even_when_zero`,
`test_f05_the_closed_key_set_matches_the_shipped_policy`.

### F-06 — MAJOR — an overbroad parser-isolation claim survived in a module the scan missed

`src/jspace_observation/parser_v3_repair_normalization.py` still declared "no
parser import and no parser invocation". That is false: importing the module
through the package first runs `jspace_observation/__init__.py`, which eagerly
imports the legacy parser.

The regression test that exists precisely to catch this wording did not catch it
because its file list was **written by hand** and this module was not on it.

**Fix.** Two parts, because the omission was the more serious half.

1. The docstring now states the supportable **differential** claim: the module
   introduces no parser dependency, references no parser symbol, adds no parser
   module to `sys.modules` beyond the package baseline, and invokes no parser —
   and says explicitly that this is *not* a claim that the process is
   parser-free, giving the reason.
2. The scan now **enumerates** the repair and policy sources by glob, so a new
   repair module is covered the moment it is added. A disclaimer exemption lets
   a document quote the withdrawn wording in order to disown it, and that
   exemption is itself tested against a bare assertion so it cannot swallow one.

**Pinned by** `test_r3new06_the_scan_covers_every_repair_module`,
`test_r3new06_no_module_claims_the_process_is_parser_free`,
`test_r3new06_the_normalization_docstring_states_the_narrow_claim`,
`test_r3new06_the_disclaimer_exemption_does_not_swallow_an_assertion`.

## 4. Final-state re-review

A second read-only reviewing agent — **Audit G** — reviewed the **remediated**
state, including the new ledger module, the new tests, and the three Phase 1.2H
documents. Its findings and their disposition are recorded in §5.

The regress is terminated here by **disclosure**, as in every prior round, not
by a demonstrated fixed point. The accurate summary is: seven audits have now
been run against this instrument set; every re-review found real defects in its
predecessor's remediation; the current state is the most corrected it has been,
and that is not the same as correct.

## 5. Final-state re-review findings

Audit G returned **1 blocker, 4 majors and 1 minor**. Every finding was
reproduced with the auditor's own counterexample before being fixed, and every
fix was re-checked against that counterexample afterwards. All six were
accepted; none was rejected.

### G-01 — BLOCKER — the ledger validated contradictory access and sealing claims

`retired_v1_state` and `successor_set_state` were carried in the ledger,
rendered into the current-state documents by `generate_current_state.py`, and
validated by nothing. The auditor set `exists`, `sealed` and
`sealed_object_count` to a fully constructed 120-case sealed set while
`sets_sealed` remained `0` and the status remained blocked; `validate_ledger`
accepted it and the generator published it. Separately, an appended
`retired_v1_semantic_read` event with `private_content_read: true` was accepted
while both semantic-read counters were zero, and `assert_monotonic_succession`
accepted a status-only jump to `SEALED_READY_FOR_PREREGISTRATION` because it
compared two records without asking whether either was coherent.

This is the most serious class of defect this repository can produce: the ledger
exists precisely to make the "no private access occurred" claim checkable, and a
ledger that validates its own negation is not evidence.

**Fix.** Closed schemas for the ledger's top level, for both state blocks and
for events. Every state field is now reconciled against the counter that
measures the same thing — `repair_input_content_accessed` against
`sealed_input_semantic_reads`, `sealed` against `sets_sealed`,
`formal_evaluation_ordinal` against `formal_evaluations_run`, and so on. The
canonical retired-v1 label is pinned as a constant so it cannot be softened.
Event kinds that read private content by definition may not declare
`private_content_read: false`; kinds this phase never authorises
(`parser_invocation`, `prediction_generation`, `formal_evaluation`) are rejected
outright; and every access event must be accounted for by a counter.
`assert_monotonic_succession` now validates both ledgers before comparing them,
and `_load_ledger` validates before rendering, so the generator cannot publish a
record the validator would reject.

**Residual limitation.** These checks establish internal coherence, not truth. A
ledger stating zero access is still an operator assertion about the world; what
is now impossible is for it to disagree with itself while passing.

**Pinned by** `test_g01_*` in `tests/test_parser_v3_v2_access_ledger.py`.

### G-02 — MAJOR — a correction could cloak a later live claim

`scan_superseded_figures` examined only the *first* match of each pattern per
window. When that first occurrence was a legitimate correction, the entire
pattern was skipped and a later live assertion was never examined. The
mention-frame rule was also too loose: it accepted a falsity marker anywhere in
the sentence, so an affirming clause could hide behind a disowning one.

**Fix.** The scan iterates every match and judges each on its own. A mention
frame's falsity marker must now share the figure's semicolon/colon-delimited
clause. The ordinary attached correction form — `…, is not correct` — was added
to the post-marker vocabulary, and a post-marker may be separated from its
figure by the unit noun the figure counts, because the shorter pattern leaves
` cases,` in between. The R3-NEW-02 contrastive leak stays closed: the new
correction pattern requires a copula, so `…, not 80 of 120 cases` still fires.

**Residual limitation.** Clause segmentation is punctuation-based. A correction
written without a semicolon, colon or sentence break can still be mis-scoped.

**Pinned by** `test_g02_*` in `tests/test_parser_v3_acceptance_policy.py`.

### G-03 — MAJOR — the JSON scanner both missed and manufactured claims

Scalar members of a *list* received no ancestor context, so moving a value one
step into an array split a claim across windows again. In the other direction,
every ancestor scalar was joined indiscriminately, so a subtree recording an
option the round **declined** was reported as a live assertion.

**Fix.** Scalar list members are expanded into `key: value` fields of the
mapping that owns the list, which is what the document means by them. `rejected`
and `considered_and_rejected` join the exempt-key vocabulary alongside
`withdrawn_argument`, so a decision record is not read as a decision.

**Residual limitation.** Ancestor context is still propagated wholesale within a
non-exempt subtree. That is defensible — every ancestor on a path genuinely
co-describes the node — but it is a design choice, not a proof.

**Pinned by** `test_g03_*` in `tests/test_parser_v3_acceptance_policy.py`.

### G-04 — MAJOR — execution claims bypassed the closed schema and the semantic hash

Phase 1.2G closed `execution_state` but left the policy's **top level** open, so
`policy["parser_v3_v2_evaluations_run"] = 1` validated cleanly. Worse, the whole
`execution_state` block was projected out of `policy_semantics_sha256`, so its
free-text `final_policy_is_not_a_result` field could be rewritten to assert "A
formal evaluation was run and parser v3 was validated" **without changing the
semantic hash** the ledger binds.

**Fix.** The policy's top-level key set is closed. The semantic projection no
longer excludes anything at the top level: only the five mutable integer
counters inside `execution_state` are projected out, so the prose claim is now
inside the hash. The claim itself is constrained — it may not assert an
evaluation, a validation, an acceptance or a prediction, and it must state that
parser v3 remains unvalidated and that no evaluation has been run. The ledger
carries `semantic_projection_counter_excludes` alongside the existing
`semantic_projection_excludes`, both checked against the module constants.

**Consequence.** The semantic hash changed to
`ae375481be95ae9f91265c0a9e9ff88ebfa4203cfb518e19287873426138c8ee`. This is a
change in what the hash *covers*, not a change to any policy semantics: the
policy's threshold, gate, ontology, population, comparator and status blocks are
byte-identical.

**Residual limitation.** The forbidden-claim check is a pattern list over free
text. It catches the auditor's phrasing and the obvious variants; it is not a
semantic entailment check.

**Pinned by** `test_g04_*` in `tests/test_parser_v3_acceptance_policy.py` and
`tests/test_parser_v3_v2_access_ledger.py`.

### G-05 — MAJOR — the parser-isolation disclaimer rule swallowed genuine assertions

`_asserts_overbroad_isolation` accepted any disclaimer vocabulary within 120
preceding characters, ignoring sentence boundaries. "This module cannot process
malformed input. Package import is absolutely parser-free." passed, because
`cannot` belonged to the previous sentence.

**Fix.** The disclaimer window is clipped at the last sentence boundary before
the claim, so a disavowal must be part of the same statement as the claim it
disavows. Quoting a withdrawn wording in order to disown it still works.

**Residual limitation.** Same-sentence proximity is still proximity, not syntax.
A sentence that mentions and then asserts would not be separated.

**Pinned by** `test_g05_*` in `tests/test_parser_v3_acceptance_policy.py`.

### G-06 — MINOR — L-38 claimed a convergence the record does not support

L-38 stated that each audit pass found fewer and less severe defects than its
predecessor. The recorded sequence is A = 5 / 1 blocker, B = 11 / 1, C = 7 / 1,
D = 5 / 2, E = 6 / 1, F = 6 / 0, G = 6 / 1. Neither count nor severity is
monotonic, and A and B were initial audits rather than remediation reviews, so
they are not comparable terms in such a series at all.

**Fix.** The convergence claim is withdrawn in `paper/limitations_ledger.md`,
the figures are stated explicitly, and the regress claim is limited to the
actual re-reviews.

**Residual limitation.** None. This was a claim about the record, and the record
now says what it shows.

### Findings raised and rejected

None. All six Audit G findings were reproduced and accepted.

### What Audit G confirmed sound

Audit F's finding counts (Audit A = 5 / 1 blocker; Audit B = 11 / 1 blocker with
four duplicates); malformed-delimiter rejection with no backtracking on a
500,000-character hostile input; basic nested-mapping detection and sibling
separation; rejection of unknown, boolean and decreasing counters and of
rewritten events; repair/policy source glob coverage with no asserted overbroad
isolation phrase present; documented policy, ledger and protocol hashes; cross-
reference resolution; the current-state consistency and generator checks; and
the Phase 1.0C record as executed and `INCONCLUSIVE`. It found no claim of
parser validation, formal evaluation or private semantic access anywhere.

## 6. Post-Audit-G self-review

Audit G's blocker generalises to a rule: *a narrated field beside a validated
field will be read through the narration, so it must be validated too*. Applying
that rule to the artifacts Phase 1.2H itself authored found two more instances.
Neither was reported by an auditor.

### S-01 — the ledger's own projection note had gone stale

`policy_binding.note` still read "computed over the policy with `execution_state`
projected out" after `G-04` narrowed the projection to five counters. Every
structured field beside it — `semantic_projection_excludes`,
`semantic_projection_counter_excludes`, `policy_semantics_sha256` — was
validated. The sentence describing them was not, and it now understated what
the hash protects.

**Fix.** `_validate_projection_prose` rejects any `policy_binding` string whose
sentence describes `execution_state` as projected out unless that same sentence
either names the counters or marks itself as describing a superseded design. The
qualifier must share the sentence with the claim, for the reason `G-02`
established. Pinned by seven tests in section 10 of the ledger suite.

### S-02 — an isolation test asserted more than its name claimed

`test_the_ledger_module_names_no_parser_symbol` listed the literal `import re`
among the parser symbols it forbade. The standard library's regular expression
module is not this project's answer parser, and treating it as one is the same
overbroad-claim defect that `F-06` and `G-05` were raised about — this time
inside the isolation test itself.

**Fix.** The parser-symbol list keeps only real parser symbols, and is extended
to six. The dependency claim is restated as what it actually is: an AST-derived
import allowlist of `hashlib`, `json`, `re`, `typing` and `__future__`, with
relative imports rejected outright. That is strictly stronger than the substring
check it replaces, because it catches any project or third-party import rather
than four spellings.

**Disclosure.** `import re` was removed from an existing assertion in order to
make a change pass. That is recorded here rather than left implicit. The removed
clause was not protecting the property the test is named for, and the assertion
it was replaced with fails on a strict superset of the inputs.

## 7. Residual limitations of this audit process

* The reviewers are automated agents operating under the same instructions as
  the authoring pass. They are independent of the pass, not of the project.
* No external human reviewer has approved any value, threshold, disposition or
  claim in this repository.
* Every re-review so far has found defects in the previous remediation. The
  correct inference is that the defect rate of a single pass is not low, not
  that the current state is defect-free.
* Audit F reviewed the Audit E remediation. Audit G reviewed the Audit F
  remediation and found a blocker in it. **The Audit G remediation recorded in
  §5 has not itself been re-reviewed.** The regress is real and is disclosed
  rather than hidden.
* The two items in §6 were found by the authoring pass applying Audit G's own
  generalised rule to its own output. Self-review is not independent
  validation, and finding two more defects immediately after a re-review had
  declared the area sound is evidence for the paragraph above, not against it.

## 8. What this document does not establish

* It does not establish that the acceptance policy is correct, only that six
  specific defects found in it were fixed and pinned.
* It does not establish that parser v3 has been validated. It has not.
* It does not establish that any private material was reviewed. None was
  accessed; see `reports/phase1_2h_blocked_set_repair.md`.
