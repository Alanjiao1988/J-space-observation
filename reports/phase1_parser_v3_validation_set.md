# Phase 1.2C — parser-v3-v1 locked evaluator set: construction and labeling report

Track: D (holdout curation)
Set id: `parser-v3-v1`
Status: **constructed, labeled, manifested, sealing-ready. Not sealed. Not evaluated.**

**No parser-v3 evaluation was run in this round and no parser-v3 result exists.** This
report describes an instrument, not a measurement.

This report contains no label content and no case text.

---

## 1. What was built

| Item | Value |
| --- | --- |
| Cases | 120 |
| Strata | 12 |
| Cases per stratum | 10 |
| Subtype slots per stratum | 5 (2 cases each) |
| Registered presence split | present 80 / no_answer 30 / ambiguous 10 |
| Critical cases | 80 |
| Material-if-missed cases | 55 |
| Case source | hand-authored model-free fixtures |
| Determinism | full — no randomness; a private salt file is generated once and reused |

Per-stratum counts, all exactly 10:

| S01 | S02 | S03 | S04 | S05 | S06 | S07 | S08 | S09 | S10 | S11 | S12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |

Cross-cutting feature counts measured by the builder: negative answers 30, decimal
surfaces 35, fraction surfaces 54, balanced reasoning-tag regions 10, malformed or stray
reasoning-tag regions 10. All meet or exceed their registered minimum of 10.

Stratum definitions and the full quota table are in
`evaluator_sets/parser_v3_v1/strata_definitions.md`. The construction protocol is in
`docs/phase1_parser_v3_locked_set.md`.

---

## 2. Artifacts and digests

Committed to Git (public, reviewable — no case text, no label values):

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `manifests/inputs_manifest.json` | 53703 | `ec954093648cb68ce8e6a83db07639bf7de426cc14e35c0a4503b0a6d75ede9d` |
| `manifests/labels_manifest.json` | 17786 | `ab32c559cd62c72d059fc2527e17d3e806d5ddc9227f8bd8f8f6b0295d7e67a2` |
| `manifests/set_manifest.json` | 8086 | `13f021abd7a052b3b7153b6a0af8ccc13f3bced4b4c280dd3abaa7ab65b949f3` |

Private, gitignored, sealed rather than committed:

| Artifact | Bytes | SHA-256 | `.gitignore` rule |
| --- | ---: | --- | --- |
| `locked_inputs.jsonl` | 32430 | `946218357432d6f271e403a883559235a7b59da7832f534bdf7eb33e934c4e06` | line 40 |
| `locked_labels.jsonl` | 109411 | `3e4f1b1bca3862d97a6db37854d1b046ac7a3c606f031b692b58ef1940be2743` | line 41 |
| `reviewer_a_locked_labels.jsonl` | 55407 | `ee85baa3f1aeced9d2e5f15ef5dd8d97d5d23378a0808b8708b2bb9ea794fa6c` | line 45 |
| `reviewer_b_locked_labels.jsonl` | 55264 | `41a5eef727a793b5c0e80d89d9174fd8c15b859660cba7530512105e5cb2c335` | line 45 |
| `arbitration_locked_labels.jsonl` | 3345 | `07613a47dad94f52ea3e521a5d7585e5628c0cf7ac3ab49c69524f38351b4b37` | line 46 |
| `private/case_sources.jsonl` | 114224 | `b1bfca7b8ebda0b2581ed5b21d3228432cf0ffd42f22f75720c07d8ccaf92e60` | line 39 |

### 2.1 Why the locked inputs are private and the manifests are not

The main agent offered to publish the case inputs as a committable
`locked_case_inputs.jsonl`. Track D declined, for one reason: parser-v3 is being
developed by another agent **in this same worktree**. Committing the 120 case
strings would make it possible — accidentally or otherwise — to tune the parser
to the holdout, which would void the pre-registration claim that motivates the
whole set. The parser-v2 precedent is the same: its locked inputs were private
and only the *development* set was published.

Reviewability is preserved without disclosure. `manifests/inputs_manifest.json`
publishes, per record, four independent fingerprints (`exact`, `normalized`,
`numeric_normalized`, `masked_template`), a character count and a byte count.
That is enough for a third party to verify set membership, verify that a sealed
copy is byte-identical, and run the outstanding overlap cross-checks — without
ever reading a case.

`manifests/labels_manifest.json` publishes salted HMAC-SHA256 label
fingerprints and byte lengths only. It carries no label values.

The builder holds a single `SECRECY` table naming every artifact and its
intended disposition, and `tests/test_parser_v3_validation_set.py` asserts that
table against `git check-ignore` in both directions: every `private` path must
be ignored, every `public` path must not be.

### 2.2 Recorded rename

The manifests and the reviewer/arbiter row files were renamed after the first build, on
instruction from the main agent, who owns `.gitignore`. The rules that agent added also
matched `evaluator_sets/**/locked_manifest.json`, which would have made the manifests
uncommittable and the set unreviewable.

| Before | After | Reason |
| --- | --- | --- |
| `manifests/input_manifest.json` | `manifests/inputs_manifest.json` | avoid the ignored `locked_manifest.json` family and match the agreed names |
| `manifests/label_manifest.json` | `manifests/labels_manifest.json` | same |
| `manifests/overall_manifest.json` | `manifests/set_manifest.json` | same |
| `private/reviewer_a_labels.jsonl` | `reviewer_a_locked_labels.jsonl` | promoted to a first-class sealed artifact, covered by rule 45 |
| `private/reviewer_b_labels.jsonl` | `reviewer_b_locked_labels.jsonl` | same |
| `private/arbitration_labels.jsonl` | `arbitration_locked_labels.jsonl` | promoted, covered by rule 46 |

No case, label or reviewer row changed. `locked_inputs.jsonl` and `locked_labels.jsonl`
are byte-identical before and after the rename — same size, same SHA-256. Only the three
manifest digests moved, because a manifest embeds the paths it describes.

Verification:

| Check | Result |
| --- | --- |
| Span-boundary gate S01/S02/S05/S06 | pass in all four |
| Targeted tests | `tests/test_parser_v3_validation_set.py` — 26 passed, 0 failed |
| Artifact pack | `phase1-evaluator-validation/track-d/20260725T121557Z-track-d-parser-v3-locked-set/` |

---

## 3. Independent operational labeling

Two complete, independent, reference-blind extraction reviews over all 120 cases. Seven
rows disagreed on at least one of the ten extraction fields; those seven and only those
seven went to a reference-blind arbiter. The builder asserts that arbitration membership
equals the disagreement set exactly, so the arbiter provably never touched an
already-agreeing row. All 120 final labels are resolved.

There is no second labeling stage. `expected_correctness` is computed mechanically from
the frozen correctness rule, and `critical_case` and `material_error_if_missed` come
from registration, so there is nothing for a Stage-2 reviewer to decide.

| Measure | Result |
| --- | ---: |
| Reviewer A | 120/120 |
| Reviewer B | 120/120 |
| Rows disagreeing on any field | 7 |
| Rows sent to arbitration | 7 |
| Rows never sent to arbitration | 113 |
| Final labels | 120 |
| **Unresolved** | **0** |
| Whole-row exact agreement (A vs B, pre-arbitration) | 113/120 |
| Answer-presence exact / kappa | 119/120 / `0.9787` |
| Parse-validity exact | 119/120 |
| Parse-ambiguity exact | 119/120 |
| Extraction-strategy exact | 119/120 |
| Parsed-answer exact | 119/120 |
| Output-quality exact / kappa | 117/120 / `0.9434` |
| Candidate-list exact / mean Jaccard | 119/120 / `0.9917` |
| Evidence-span set exact | 118/120 |
| Selected-span exact / mean Jaccard | 119/120 / `0.9917` |
| Selected-span canonical value exact | 119/120 |
| Failure-reason exact / mean Jaccard | 118/120 / `0.9833` |
| Format-warning exact / mean Jaccard | 117/120 / `0.9903` |

All agreement figures are **A versus B before arbitration**. They measure reviewer
reproducibility, not label quality.

### 3.1 Model used

| Role | Requested | Actual | Reasoning effort |
| --- | --- | --- | --- |
| Reviewer A | `Claude Opus 5` (`claude-opus-5`) | `claude-opus-5` | max |
| Reviewer B | `Claude Opus 5` (`claude-opus-5`) | `claude-opus-5` | max |
| Arbiter | `Claude Opus 5` (`claude-opus-5`) | `claude-opus-5` | max |

The exact requested enumeration was available. Requested and actual are identical for
all three roles; no substitution occurred and none was made silently.

### 3.2 What the arbiter resolved

| Case | Fields in dispute | Ruling |
| --- | --- | --- |
| 1 | `format_warnings` | dropped `incidental_numeric_material`: the rejected value was answer-relevant, not metadata |
| 2 | `output_quality` | `malformed_recoverable`: doubled braces break the box but the value is recoverable |
| 3 | `evidence_spans` | kept the `equivalent` span implied by the asserted `equivalent_repeated_claim`; also corrected a `parsed_answer` that both reviewers had canonicalised instead of quoting the surface |
| 4 | `output_quality` | `malformed_recoverable`: markup splits the marker; corrected the surface form of `parsed_answer` |
| 5 | all ten fields | later same-tier marker wins, so no ambiguity; the earlier lower-tier claim yields `lower_priority_conflict_ignored` |
| 6 | `format_warnings` | `stray_think_tag` only: the valid tags balance, the mangled one is not a think tag |
| 7 | `output_quality`, `failure_reasons` | `truncated` / `truncated_before_final_answer`: output ends inside an unclosed reasoning block before committing |

Case ids are omitted here deliberately; they are recorded in the private agreement
report and in the artifact pack's records file.

### 3.3 Status of these labels

**These labels are an LLM-produced operational consensus reference. They are not human
ground truth.** No human adjudicated any case. Two independent language-model reviewers
plus an arbiter, all reference-blind, produced them. Every downstream claim must be
phrased as agreement with that consensus. A systematic error shared by both reviewers
would not have been caught by this procedure.

### 3.4 Curator intent versus reviewer consensus

An additional honest diagnostic: how often the blind consensus reproduced what the
curator intended when authoring the case.

| Comparison | Result |
| --- | ---: |
| Presence and parsed answer both match intent | 109/120 |
| All ten fields match intent | 52/120 |
| All fields except spans match intent | 56/120 |
| `answer_presence` matches intent | 109/120 |
| `parse_valid` matches intent | 111/120 |
| `parse_ambiguous` matches intent | 116/120 |
| `parsed_answer` matches intent | 113/120 |
| `candidate_answers` matches intent | 116/120 |
| `extraction_strategy` matches intent | 111/120 |
| `output_quality` matches intent | 106/120 |
| `failure_reasons` matches intent | 106/120 |
| `format_warnings` matches intent | 69/120 |
| `evidence_spans` (kind, disposition, value) matches intent | 104/120 |

The consensus, not the curator's intent, is the label of record. The gap is concentrated
in `format_warnings` (69/120) and `evidence_spans` (104/120):

* **Warnings** are advisory and their boundaries are genuinely fuzzy. The two reviewers
  agreed with *each other* on warnings 117/120 while agreeing with the curator only
  69/120, which says the disagreement is a systematic curator-versus-reviewer reading of
  the warning definitions, not reviewer noise. Any parser-v3 acceptance gate should
  therefore treat `format_warnings` as a secondary, lower-weight field.
* **Spans** diverge partly for a mechanical reason: the published protocol asks
  reviewers to quote the licensing construct including its marker, whereas the curator
  registered bare literals. The comparison above already normalises for that by
  comparing `(kind, disposition, canonical value)` rather than character offsets.
* Registered reference-correct cases number 40; under the consensus labels 44 cases are
  reference-correct. The 4-case difference is a direct consequence of the consensus
  disagreeing with curator intent on presence or parsed answer in 11 cases.

This diagnostic is reported because hiding it would make the instrument look cleaner
than it is.

---

## 4. Overlap verification

Implemented in code and enforced as a build gate, not asserted in prose. Any violation
aborts the build.

| Check | Requirement | Result |
| --- | --- | ---: |
| Hard exact overlap vs prior corpora | 0 | **0** |
| Normalized overlap vs prior corpora | 0 | **0** |
| Numeric-normalized overlap vs prior corpora | 0 | **0** |
| Internal exact duplicates | 0 | **0** |
| Internal normalized duplicates | 0 | **0** |
| Near-duplicates at Jaccard >= 0.85 vs prior | 0 | **0** (max 0.7273) |
| Near-duplicates at Jaccard >= 0.85 internal | 0 | **0** (max 0.8333) |

Four fingerprints per record — exact, normalized, numeric-normalized, masked-template —
are defined in `docs/phase1_parser_v3_locked_set.md` section 6.1 and implemented in
`scripts/build_parser_v3_validation_set.py`. Normalization is NFKC, CRLF/CR to LF,
unicode punctuation folded to ASCII, whitespace collapsed, stripped, casefolded.

Corpora actually compared:

| Corpus | Records | SHA-256 of the corpus file |
| --- | ---: | --- |
| `evaluator_sets/parser_v2_v1/development_cases.jsonl` | 60 | `bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27` |
| `artifacts/record_audit/ambiguous_records_for_review.jsonl` (90 output-bearing text fields) | 18 | `b9062e851a1dd1f4e41da6b598ac4c40d391d60b428d4ff524eaeb4ea02a5614` |

Three collisions were found and fixed during construction rather than waived: one exact
duplicate of a parser-v2 development case, plus a family of masked-template collisions
among very short marker-only fixtures. The affected cases were rewritten and the build
re-run until every gate passed with zero waivers.

---

## 5. Span-boundary variation in S01, S02, S05, S06

The requirement was more span-boundary variation than the parser-v2 set. Because
parser-v3 has 10 cases per stratum against parser-v2's 5, a raw count comparison would
be confounded by n. The gate is therefore a **strict superset plus strictly wider
range** condition, which is insensitive to n, and it passes for all four strata.

| Stratum | v2 windows | v3 windows | v3 covers all v2 windows | v2 span counts | v3 span counts | v2 start range | v3 start range | v2 tail-gap range | v3 tail-gap range | v2 length range | v3 length range |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 5 | 9 | yes | {1} | {1,2,3} | 15–71 | 9–390 | 1–15 | 1–45 | 21–77 | 15–394 |
| S02 | 4 | 9 | yes | {1} | {1,2,3} | 8–64 | 7–367 | 0–1 | 0–41 | 13–69 | 11–370 |
| S05 | 3 | 7 | yes | {1} | {1,2,3} | 7–14 | 7–282 | 30–85 | 9–350 | 42–103 | 24–368 |
| S06 | 4 | 7 | yes | {1} | {1,3} | 7–47 | 7–286 | 20–56 | 10–265 | 36–78 | 21–343 |

Concretely, what was added: boxes that are not the last thing in the output and boxes
with padded braces (S01); markers with no space after the colon, full-width-colon
markers, and markers on interior lines (S02); four new post-answer continuation openings
and tail gaps up to 350 characters instead of 85 (S05); parenthesised trailing
distractors, boxed answers followed by a distractor line, and tail gaps up to 265
characters (S06). Every stratum also gains multi-span cases, where parser-v2 had exactly
one evidence span in every case.

Line-class coverage also widens: S01 and S02 gain interior-line spans, and S05 gains
interior-line spans.

---

## 6. Isolation record

Track D ran under **procedural, hash-audited isolation — not a security-enforced
boundary.** The curator had ordinary read access to the entire worktree and chose not to
exercise it on the excluded paths. Nothing technical prevented a violation.

Deliberately not read:

* `src/jspace_observation/eval_parsing_v3.py`
* `reports/phase1_parser_v3_development.md`
* `evaluator_sets/parser_v3_v1/adversarial_development_cases.jsonl`
* anything under `phase1-parser-v3/track-c/`
* any parser-v3 prediction or development error detail beyond the public stratum
  definitions

Read: the parser-v2 protocol, the evaluator validation-set protocol, the parser-v2
acceptance gates, the parser-v2 validation-set report, the parser-v2 build and persist
scripts, `src/jspace_observation/evaluator_validation.py`, and
`evaluator_sets/parser_v2_v1/development_cases.jsonl` for overlap checking and the
boundary baseline.

Supporting evidence:

* the builder imports no parser module and implements its own canonicalisation from the
  frozen numeric grammar, so it cannot inherit a parser-v3 behaviour;
* every case is hand-authored, so no parser-v3 output could have shaped case selection;
* reviewer and arbiter sub-agents were given explicit path denylists covering all
  parser-v3 development artifacts, and each received only its packet plus the protocol;
* the recorded code commit lets an auditor diff the worktree and confirm this track
  modified none of the excluded files.

Track C was authoring parser-v3 development files concurrently in the same worktree. The
isolation claim is therefore only as strong as this declaration plus the hash audit, and
the paper must describe it that way.

---

## 7. Limitations

1. **The zero-overlap claim is conditional.** It is proven against the two corpora Track
   D could read. Overlap with the retired parser-v2 locked holdout, with the parser-v3
   public adversarial development set, and with the full 45-record historical generation
   and evaluation records is **not** verified here — the first is sealed in private Blob
   storage, the second is inside Track D's isolation denylist, and the third is not
   present in this worktree. Per-record fingerprints for all 120 cases are published in
   `manifests/inputs_manifest.json` so the main agent can close the gap before sealing.
   Until that cross-check runs, treat zero overlap as asserted-pending-verification.
2. **Labels are LLM consensus, not ground truth.** A systematic misreading shared by
   both reviewers would survive arbitration undetected.
3. **Isolation is procedural.** It was not enforced by sandboxing, permissions or a
   separate checkout.
4. **No empty-output coverage.** The parser-v2 protocol placed its only empty-output
   case in the parser-v2 development set, so any whitespace-only parser-v3 case would
   collide on the normalized fingerprint. The `empty` output quality and the
   `empty_output` failure reason are consequently unexercised. This is a deliberate,
   protocol-driven gap.
5. **Fixtures are synthetic.** Cases are hand-authored rather than sampled from model
   generations. This buys determinism, zero contamination and full stratum control, and
   it costs ecological validity: the distribution of surface forms is the curator's, not
   a model's.
6. **Warning labels are noisy relative to intent.** Reviewer-versus-curator agreement on
   `format_warnings` is 69/120 even though reviewer-versus-reviewer agreement is
   117/120. Acceptance gates should weight this field accordingly.
7. **n = 10 per stratum.** A per-stratum accuracy estimate from 10 cases has a wide
   confidence interval. The set is sized to detect coarse stratum-level failure, not to
   produce precise per-stratum rates.
8. **Not sealed yet.** The bytes are reproducible today but not yet immutable. Until the
   main agent completes the seal described in `docs/phase1_parser_v3_sealing_run.md`,
   this is not a pre-registered holdout.
9. **The case text is not open for inspection.** Because the locked inputs stay out of
   Git (§2.1), an external reviewer can verify membership, integrity and non-overlap
   from the published fingerprints, but cannot read the cases until the set is retired.

---

## 8. Scientific boundaries

* **No parser-v3 evaluation was run. No parser-v3 result exists.** Nothing here supports
  any statement about parser-v3 accuracy, about parser-v3 versus parser-v2, or about
  remaining headroom.
* The set is an instrument. Its value depends entirely on being sealed before any
  parser-v3 prediction is made against it.
* Agreement statistics describe reviewer reproducibility, not correctness.
* Overlap results describe the corpora that were reachable, not all corpora.
* Isolation is procedural and hash-audited, not RBAC-enforced blinding or a security
  boundary.

---

## 9. Next gate

The main agent, in this order:

1. run the three section-9 cross-checks in `docs/phase1_parser_v3_sealing_run.md`
   against the published fingerprints;
2. seal to `phase1-evaluator-validation/parser-v3-v1/<timestamp>` exactly as specified,
   with the set manifest written last;
3. only then permit a parser-v3 locked evaluation to be scheduled against the sealed
   set.
