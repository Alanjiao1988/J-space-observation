# Phase 1.2C — parser-v3-v1 locked evaluator set: public construction protocol

Status: **constructed and sealed-ready. No parser-v3 evaluation has been run.**
Track: D (holdout curation)
Set id: `parser-v3-v1`
Owner: Agent D, holdout curator

This document is public. It contains the research question, the stratum quotas, the
construction rules, the labeling protocol, the isolation record, the overlap
methodology and the sealing plan. **It contains no label content and no case text.**

---

## 1. Research question

> Does a locked, independently curated, never-seen evaluator set of 120 cases across 12
> failure strata give a defensible estimate of answer-extraction reliability, when the
> set is constructed in procedural isolation from the parser under test?

The set exists to answer that question **later**. This round produces the instrument
only. No parser-v3 result exists and none may be inferred from anything in this
document.

Secondary question: does increasing span-boundary variation in the marker-bearing
strata (S01, S02, S05, S06) relative to the parser-v2 development set surface
boundary-sensitivity that the earlier set could not?

---

## 2. Stratum quotas

120 cases, 12 strata, exactly 10 cases per stratum, 5 subtype slots of 2 cases each.
Full definitions and cross-cutting quotas are in
`evaluator_sets/parser_v3_v1/strata_definitions.md`.

| Stratum | Name | n |
| --- | --- | --- |
| S01 | boxed single answer | 10 |
| S02 | explicit final-answer marker | 10 |
| S03 | terminal equation | 10 |
| S04 | multiple intermediate numbers | 10 |
| S05 | final answer followed by reasoning | 10 |
| S06 | last-number trap | 10 |
| S07 | truncated before answer | 10 |
| S08 | explicit no-answer / placeholder | 10 |
| S09 | malformed recoverable | 10 |
| S10 | malformed unrecoverable | 10 |
| S11 | true multiple-candidate ambiguity | 10 |
| S12 | numeric normalization | 10 |

---

## 3. Construction rules

1. **Model-free fixtures.** Every case is a hand-authored string. No case is a model
   generation, so no model's behaviour is baked into the instrument and no generation
   run is required to rebuild it.
2. **Deterministic rebuild.** `scripts/build_parser_v3_validation_set.py` rebuilds the
   locked inputs, the locked labels, and all three manifests byte-for-byte from the
   private case sources plus the reviewer label files. No randomness is used anywhere;
   the only stored entropy is a private salt file, generated once and reused, that keys
   the case ids and the label fingerprints.
3. **Case ids** are `PV3-<20 hex>` derived from a salted digest of the case text and
   parse type. Ids therefore change if and only if the case text changes.
4. **Frozen result schema.** Cases, labels and vocabularies use the parser-v2 protocol's
   frozen schema (`docs/phase1_parser_v2_protocol.md`): the same ten extraction fields,
   the same closed `failure_reasons` and `format_warnings` vocabularies, the same
   evidence-tier precedence, the same numeric grammar, and the same correctness rule.
   Nothing in the parser-v2 protocol was modified.
5. **Correctness is computed, never asserted.** `expected_correctness` is derived
   mechanically as `answer_presence == present AND canonical(parsed_answer) ==
   canonical(registered_reference_answer)`. A registered correctness flag that
   disagrees with the computed value is a build failure.
6. **Registered composition is enforced, not documented.** Every quota in
   `strata_definitions.md` is asserted by the builder; a shortfall aborts the build.
7. **No empty output.** See the deliberate coverage gap in `strata_definitions.md`.

### 3.1 Span-boundary variation in S01, S02, S05, S06

The requirement was "more span-boundary variation than the old parser-v2 set". Because
the parser-v2 development set has 5 cases per stratum and this set has 10, raw counts
are confounded. The gate is therefore stated as a **strict superset plus strictly wider
range** condition, which is not sensitive to n:

For each of S01, S02, S05, S06 the builder measures, over the *selected* evidence spans:

* the **boundary window**: two characters before the span start, a `|` marker, and two
  characters after the span end, with digits folded to `d`;
* the **start offset** of the span;
* the **tail gap**: characters between span end and end of output;
* the **span length**;
* the **span-count values** observed in the stratum;
* the **line class** of the span (first / interior / last line).

The gate requires, for every one of the four strata:

1. every parser-v2 boundary window is also present in parser-v3 (`covers_v2_windows`);
2. parser-v3 has strictly more distinct boundary windows;
3. parser-v3 observes strictly more distinct span-count values;
4. parser-v3 has a strictly wider start range, tail-gap range and length range;
5. parser-v3 covers at least as many line classes.

**Measured result — all four strata pass.**

| Stratum | v2 distinct windows | v3 distinct windows | Windows added by v3 | v2 span counts | v3 span counts | v2 start range | v3 start range | v2 tail-gap range | v3 tail-gap range | v2 length range | v3 length range | v2 line classes | v3 line classes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 5 | 9 | `d{\|}\n`, `d{\|} `, `d{\|}.`, `{ \| }` | {1} | {1,2,3} | 15–71 | 9–390 | 1–15 | 1–45 | 21–77 | 15–394 | first, last | first, interior, last |
| S02 | 4 | 9 | `: \|\n-`, `: \|\nF`, `: \|\nT`, `r:\|`, `：\| ` | {1} | {1,2,3} | 8–64 | 7–367 | 0–1 | 0–41 | 13–69 | 11–370 | first, last | first, interior, last |
| S05 | 3 | 7 | `: \|\nA`, `: \|\nC`, `: \|\nI`, `: \|\nV` | {1} | {1,2,3} | 7–14 | 7–282 | 30–85 | 9–350 | 42–103 | 24–368 | first | first, interior |
| S06 | 4 | 7 | `: \|\nT`, `: \| (`, `d{\|}\n` | {1} | {1,3} | 7–47 | 7–286 | 20–56 | 10–265 | 36–78 | 21–343 | first, interior | first, interior |

Concretely, the added variation is:

* **S01** — boxes that are not the last thing in the output (followed by a newline, by a
  space, by a sentence-ending period), boxes with padded braces, boxes in interior
  lines, and cases carrying 2 or 3 evidence spans rather than exactly 1.
* **S02** — markers followed by a further line beginning with `-`, `F` or `T`; a marker
  with no space after the colon (`r:|`); a full-width colon marker; interior-line
  markers; multi-span cases.
* **S05** — four new post-answer continuation openings (`A`, `C`, `I`, `V`) beyond the
  parser-v2 pair, tail gaps from 9 to 350 characters instead of 30 to 85, spans starting
  as late as offset 282 instead of 14, and 2- and 3-span cases.
* **S06** — a trailing distractor introduced by a parenthesis (`: | (`), a boxed answer
  followed by a distractor line (`d{|}\n`), tail gaps up to 265 characters, and 3-span
  cases.

The honest caveat: parser-v3 has 10 cases per stratum against parser-v2's 5, so a raw
count comparison would be confounded. The **superset** and **range** claims above are
the strong ones, and they are the ones the gate enforces.

---

## 4. Labeling protocol

### 4.1 Reviewers

* **Reviewer A** — labeled 120/120, reference-blind.
* **Reviewer B** — labeled 120/120, reference-blind, independently.
* **Arbiter** — invoked **only** on rows where A and B differed on at least one of the
  ten extraction fields. The builder asserts that the arbitration membership equals the
  disagreement set exactly; running the arbiter on an already-agreeing row is a build
  failure.

Requested model for all three roles: **Claude Opus 5 at maximum reasoning effort**
(`claude-opus-5`, `reasoning_effort: max`). The exact requested enumeration was
available and was used. Requested and actual are identical; no silent substitution
occurred.

### 4.2 What each reviewer saw

Each reviewer received exactly two files:

1. the reviewer packet — `case_id`, `output_text`, `parse_type` only;
2. the labeling protocol — field schema, closed vocabularies, tier precedence, warning
   definitions, numeric grammar, output format.

Each reviewer was explicitly forbidden from reading the case sources, the reference
answers, the stratum assignments, the builder, the other reviewer's output, any parser
source file, and any parser prediction. Reviewers did not see stratum quotas, so they
could not back-solve the composition.

The arbiter received only the disagreeing rows, the raw output text for those rows, the
list of differing fields, and the two competing judgements presented as anonymised
`judgement_1` / `judgement_2` in a non-informative order. The arbiter saw no reference
answer, no stratum, and no parser prediction, and was free to produce a corrected
judgement rather than picking a side.

### 4.3 Fields labeled

`answer_presence`, `parse_valid`, `parse_ambiguous`, `parsed_answer`,
`candidate_answers`, `evidence_spans`, `extraction_strategy`, `output_quality`,
`failure_reasons`, `format_warnings`.

Reviewers declare spans as `{text, occurrence, kind, disposition}` — an exact substring
plus a 1-based occurrence index — and the builder resolves character offsets. Asking a
language model for raw character indices is unreliable; asking for a substring it can
copy is not.

`expected_correctness`, `critical_case` and `material_error_if_missed` are **not**
reviewer judgements. Correctness is computed from the frozen rule; criticality and
materiality come from registration. There is therefore no second labeling stage.

### 4.4 Vocabulary rules applied

Beyond the frozen parser-v2 vocabularies, three warning definitions were tightened so
that two independent reviewers could apply them consistently. They are reproduced here
verbatim as given to the reviewers:

* `multiple_numeric_mentions` — two or more numeric surfaces appear anywhere in the
  output.
* `noncanonical_numeric_surface` — the **selected** literal's surface differs from its
  canonical rendering.
* `incidental_numeric_material` — numerals appear that are not part of the computation
  (metadata, step or field counts, confidence codes, identifiers). Equation operands are
  **not** incidental.

### 4.5 Status of the labels

These labels are an **LLM operational consensus reference**. They are not human ground
truth. No human adjudicated any case. Every downstream claim must be phrased as
agreement with a two-reviewer-plus-arbiter LLM consensus, never as accuracy against
truth.

---

## 5. Isolation record

Track D was executed under **procedural, hash-audited isolation — not a
security-enforced boundary.** The curator had ordinary filesystem read access to the
whole worktree and chose not to exercise it on the excluded paths. Nothing prevented a
violation; the record below is a good-faith declaration plus the mechanical evidence
that supports it.

### 5.1 Paths deliberately not read by the curator

* `src/jspace_observation/eval_parsing_v3.py`
* `reports/phase1_parser_v3_development.md`
* `evaluator_sets/parser_v3_v1/adversarial_development_cases.jsonl`
* anything under `phase1-parser-v3/track-c/`
* any parser-v3 prediction, and any parser-v3 development error detail beyond the
  public stratum definitions

### 5.2 Paths read

`docs/phase1_parser_v2_protocol.md`, `docs/phase1_evaluator_validation_set.md`,
`docs/phase1_parser_v2_acceptance_gates.json`,
`reports/phase1_parser_v2_validation_set.md`,
`scripts/build_parser_v2_validation_set.py`,
`scripts/persist_parser_v2_validation_set.py`,
`src/jspace_observation/evaluator_validation.py`,
`evaluator_sets/parser_v2_v1/development_cases.jsonl` (overlap checking and boundary
baseline only).

### 5.3 Mechanical support

* The builder imports nothing from `eval_parsing_v3` and references no parser-v3
  symbol. It has no dependency on any parser implementation at all: it implements its
  own canonicalisation from the frozen numeric grammar.
* Every case is hand-authored, so no parser-v3 output could have influenced case
  selection.
* Reviewer and arbiter sub-agents were given explicit path denylists covering all
  parser-v3 development artifacts.
* The code commit recorded in the artifact pack lets any auditor diff the worktree and
  confirm that no excluded file was modified by this track.

### 5.4 What isolation does **not** guarantee

Isolation was not enforced by sandboxing, by filesystem permissions, or by a separate
checkout. A determined or careless agent in this worktree could have read the excluded
files. Track C authored its files concurrently in the same worktree. The isolation claim
is therefore only as strong as the declaration plus the hash audit, and it must be
described that way in the paper.

---

## 6. Overlap methodology

### 6.1 Fingerprints

Four SHA-256 fingerprints are computed per record:

| Fingerprint | Definition |
| --- | --- |
| `exact_sha256` | SHA-256 over the exact UTF-8 output bytes |
| `normalized_sha256` | NFKC normalisation, CRLF/CR to LF, unicode punctuation folded to ASCII, all whitespace runs collapsed to a single space, stripped, casefolded |
| `numeric_normalized_sha256` | the normalized text with every legal numeric surface replaced by its exact reduced-rational canonical rendering |
| `masked_template_sha256` | the normalized text with every legal numeric surface replaced by `<NUM>` |

Punctuation folding maps unicode dashes, quotes, ellipses and full-width forms onto
their ASCII equivalents so that a "different" case cannot be manufactured by swapping a
hyphen for an en dash.

### 6.2 Requirements enforced by the builder

* hard exact overlap with any reachable prior corpus = **0**
* normalized overlap with any reachable prior corpus = **0**
* numeric-normalized overlap with any reachable prior corpus = **0**
* internal exact duplicates = **0**
* internal normalized duplicates = **0**
* no near-duplicate pair at or above Jaccard **0.85** on masked-template character
  5-grams, either against a prior corpus or inside the set

Any violation aborts the build. These are gates, not reports.

### 6.3 Corpora actually checked

| Corpus | Records | Readable |
| --- | --- | --- |
| `evaluator_sets/parser_v2_v1/development_cases.jsonl` | 60 | yes |
| `artifacts/record_audit/ambiguous_records_for_review.jsonl` (historical model outputs, 90 text fields across 7 output columns) | 18 | yes |

### 6.4 Corpora that could **not** be checked directly, and the mitigation

| Corpus | Why unreachable | Mitigation |
| --- | --- | --- |
| the retired parser-v2 locked holdout | sealed in private Blob storage; its content is not readable from this worktree, and reading it would defeat the purpose of retiring it | per-record `exact`, `normalized`, `numeric_normalized` and `masked_template` fingerprints for all 120 new cases are published in `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json` so the main agent can run the same four-way comparison against the sealed set |
| the parser-v3 public adversarial development set | inside Track D's isolation denylist | the same published fingerprints allow the main agent, who is not under this isolation, to run the comparison |
| the full 45-record phase-1 generation and evaluation records | `phase1_generations.jsonl` and `phase1_eval_records.jsonl` are not present in this worktree | the reachable 18-record audit extract was fingerprinted instead; the gap is recorded here and in the artifact pack |

**This is a real limitation.** Track D can prove zero overlap only against what it can
read. Zero overlap against the sealed holdout and the parser-v3 adversarial set is
**asserted by construction and left to be verified by the main agent** using the
published fingerprints. Until that cross-check runs, the zero-overlap claim is
conditional.

### 6.5 Measured result

* hard exact overlap: **0**
* normalized overlap: **0**
* numeric-normalized overlap: **0**
* internal exact duplicates: **0**
* internal normalized duplicates: **0**
* near-duplicates at or above 0.85: **0** (max similarity against a prior corpus 0.7273;
  max similarity inside the set 0.8333)

---

## 7. Sealing plan

The main agent executes the seal. Track D produces the artifacts and the specification
and runs no Azure command. The full specification is
`docs/phase1_parser_v3_sealing_run.md`. In outline:

* private Blob parent prefix `phase1-evaluator-validation/parser-v3-v1/<timestamp>`;
* separate leaves `locked-inputs/`, `locked-labels/`, `manifests/`, `reports/`;
* `overwrite=false` on every upload;
* the set manifest written **last**, after every other object is durable;
* exact membership verified against the manifest — no extra objects, no missing objects;
* every object re-downloaded and verified on size, SHA-256 and ETag;
* labels never committed to GitHub;
* managed identity plus private endpoint only — no account key, no SAS, public network
  access disabled.

---

## 8. Files

| Path | Committed | Contents |
| --- | --- | --- |
| `evaluator_sets/parser_v3_v1/locked_inputs.jsonl` | no (gitignored, line 40) | 120 case inputs, no labels |
| `evaluator_sets/parser_v3_v1/locked_labels.jsonl` | **no — gitignored line 41, must never be committed** | 120 final labels |
| `evaluator_sets/parser_v3_v1/reviewer_a_locked_labels.jsonl` | no (gitignored, line 45) | reviewer A rows |
| `evaluator_sets/parser_v3_v1/reviewer_b_locked_labels.jsonl` | no (gitignored, line 45) | reviewer B rows |
| `evaluator_sets/parser_v3_v1/arbitration_locked_labels.jsonl` | no (gitignored, line 46) | arbiter rows, disagreements only |
| `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json` | yes | file digest plus per-record input fingerprints |
| `evaluator_sets/parser_v3_v1/manifests/labels_manifest.json` | yes | file digest plus per-record salted label fingerprints — no label values |
| `evaluator_sets/parser_v3_v1/manifests/set_manifest.json` | yes | all files, all digests, composition, overlap and agreement report |
| `evaluator_sets/parser_v3_v1/strata_definitions.md` | yes | stratum definitions and quotas |
| `evaluator_sets/parser_v3_v1/private/**` | no (gitignored, line 39) | case sources, salts, reviewer packet, authoring modules |
| `scripts/build_parser_v3_validation_set.py` | yes | deterministic builder, contains no case text |
| `tests/test_parser_v3_validation_set.py` | yes | schema, quota, overlap, manifest and label-secrecy tests |
| `docs/phase1_parser_v3_sealing_run.md` | yes | sealing specification |
| `reports/phase1_parser_v3_validation_set.md` | yes | construction and labeling report |

### 8.1 What is secret and why

The builder declares one `SECRECY` table naming every artifact as `private` or `public`,
and `tests/test_parser_v3_validation_set.py` asserts that table against
`git check-ignore` in both directions: every private path must be ignored, every public
path must not be.

The **inputs are deliberately private**, not merely for symmetry with the labels.
Parser-v3 is being developed by another agent in the same worktree; publishing the 120
case strings would make it possible to tune the parser to the holdout and would void the
pre-registration claim that the whole set exists to support. The parser-v2 precedent is
identical — its locked inputs were private and only the development set was published.

The **manifests are deliberately public**. They carry, per record, four independent
fingerprints, a character count and a byte count for the inputs, and a salted HMAC
fingerprint and byte length for the labels. That is sufficient for a third party to
verify set membership, verify that a sealed copy is byte-identical, and reproduce the
overlap analysis — without reading a case or a label. None of them is named
`locked_manifest.json`, because that exact filename is gitignored by line 44.

Verification that the label file cannot be staged:

```powershell
git check-ignore -v evaluator_sets/parser_v3_v1/locked_labels.jsonl   # exits 0
git status --porcelain --untracked-files=all |
  Select-String 'locked_labels|locked_inputs|_locked_labels'          # returns nothing
```

---

## 9. Scientific boundary

* No parser-v3 evaluation was run in this round. **No parser-v3 result exists.**
* Nothing in this document licenses any claim about parser-v3 accuracy, headroom, or
  comparison against parser-v2.
* The labels are an LLM operational consensus reference, not human ground truth.
* Zero overlap is proven against reachable corpora and asserted-pending-verification
  against sealed and isolated ones.
* Isolation is procedural and hash-audited, not security-enforced.
