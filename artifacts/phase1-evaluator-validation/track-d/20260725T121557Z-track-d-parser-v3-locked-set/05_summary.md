# Summary

Track D constructed, blind-labeled, fingerprinted and manifested the
`parser-v3-v1` locked evaluator holdout: 120 cases, 12 strata, 10 cases per
stratum, zero overlap against every reachable prior corpus, zero unresolved
labels. **No parser-v3 evaluation was run and no parser-v3 result exists.**

## Objective

Produce an independent, never-seen evaluator set for a later pre-registered
parser-v3 evaluation, together with its labels, its manifests, its public
construction protocol and a complete sealing specification the main agent can
execute without further design decisions.

## Scope

In scope: authoring 120 model-free fixtures across 12 registered strata; two
independent reference-blind LLM labeling passes; arbitration restricted to
reviewer-disagreement rows; four-way fingerprint overlap checking; a
span-boundary variation gate for S01, S02, S05 and S06; inputs, labels and set
manifests; public protocol, strata definitions, validation report and sealing
specification; targeted tests.

Out of scope: running any parser-v3 evaluation; reading any parser-v3
development artifact; executing any Azure command; uploading anything; creating
git commits.

## Provenance

| Item | Value |
| --- | --- |
| Run id | `20260725T121557Z-track-d-parser-v3-locked-set` |
| Phase / track | phase-1.2C / D |
| Code commit | `62e9b961a391e8f346e37bd9cbbf710e9b551c24` |
| Protocol hash | `27becc4e7731e6326e1bfbea39dd2734110a131ab307f72253714406ac76fcba` |
| Labeling model requested | Claude Opus 5 (`claude-opus-5`), max reasoning |
| Labeling model actual | `claude-opus-5`, max reasoning — no substitution |
| Image digest | not applicable; construction ran locally on CPU |
| Azure commands executed by Track D | none |
| Locked inputs SHA-256 | `946218357432d6f271e403a883559235a7b59da7832f534bdf7eb33e934c4e06` |
| Locked labels SHA-256 | `3e4f1b1bca3862d97a6db37854d1b046ac7a3c606f031b692b58ef1940be2743` |
| Set manifest SHA-256 | `13f021abd7a052b3b7153b6a0af8ccc13f3bced4b4c280dd3abaa7ab65b949f3` |

## Execution

1. Authored 120 fixtures into a gitignored private directory, 10 per stratum,
   5 subtype slots of 2 cases each.
2. Ran the deterministic builder, which enforces every registered quota, the
   frozen correctness rule, the four-way overlap gates and the span-boundary
   variation gate. Gate failures were fixed by rewriting cases, never waived.
3. Dispatched two independent reference-blind reviewers. Each saw only the case
   inputs and the labeling protocol — no reference answers, no strata, no
   parser output, and not each other's work.
4. Computed A-versus-B agreement, then sent exactly the
   7 disagreement rows to a reference-blind
   arbiter with the two competing judgements anonymised. The builder asserts
   arbitration membership equals the disagreement set.
5. Merged into 120 final labels, generated the three manifests, and wrote the
   public protocol, strata definitions, validation report and sealing
   specification.

## Results

| Measure | Result |
| --- | ---: |
| Cases / strata / per stratum | 120 / 12 / 10 |
| Registered presence split | 80 present, 30 no_answer, 10 ambiguous |
| Critical cases | 80 |
| Hard exact overlap | 0 |
| Normalized overlap | 0 |
| Numeric-normalized overlap | 0 |
| Max near-duplicate similarity vs prior / internal | 0.7273 / 0.8333 |
| Reviewer A / Reviewer B coverage | 120/120 / 120/120 |
| Whole-row exact agreement (A vs B) | 113/120 |
| Rows sent to arbitration | 7 |
| Unresolved labels | 0 |
| Answer-presence exact / kappa | 119/120 / 0.9787 |
| Output-quality exact / kappa | 117/120 / 0.9434 |
| Parsed-answer exact | 119/120 |
| Selected-span exact / mean Jaccard | 119/120 / 0.9917 |
| Failure-reason exact / mean Jaccard | 118/120 / 0.9833 |
| Format-warning exact / mean Jaccard | 117/120 / 0.9903 |
| Span-boundary gate S01/S02/S05/S06 | pass / pass / pass / pass |
| Targeted tests | 26 passed, 0 failed |

## Decision

**COMPLETE.** The set is constructed and sealing-ready. Every registered
criterion passed; the criteria that could not apply are recorded explicitly
rather than silently skipped.

## Deviations and errors

Five deviations, all recorded in `08_deviations.json`:

1. The published reviewer protocol asks for marker-inclusive evidence spans
   while the curator registered bare literals. Resolved by comparing span kind,
   disposition and canonical value instead of character offsets.
2. The curator's registered `candidate_answers` convention for `present` cases
   contradicted the published protocol and was corrected mid-run.
3. The overlap gates caught one exact duplicate of a parser-v2 development case
   and a family of masked-template near-duplicates among very short fixtures.
   The affected cases were rewritten and the build re-run. No gate was waived.
4. The manifests and the reviewer/arbiter row files were renamed on main-agent
   instruction so that the manifests remain committable under the shared
   `.gitignore`. The locked-inputs and locked-labels digests are unchanged.
5. The locked case inputs were deliberately kept private rather than committed.

No unregistered change was made to any frozen artifact.

## Scientific interpretation

Track D produced an instrument, not a measurement. Two independent
reference-blind LLM reviewers agreed on every field of
113/120 cases; an arbiter resolved the remaining
7 without ever seeing an agreeing row. The labels
are therefore a reproducible LLM operational consensus, not human ground truth.

The one substantive finding about the *instrument* is that reviewer-versus-
reviewer agreement on `format_warnings` is 117/120
while reviewer-versus-curator agreement on the same field is only
69/120. The two
reviewers agree with each other far more than either agrees with the curator,
which points at a systematic difference in reading the warning definitions
rather than reviewer noise. Any parser-v3 acceptance gate should weight
`format_warnings` below the presence, validity and parsed-answer fields.

## Limitations

1. Zero overlap is proven only against the two corpora Track D could read. The
   retired parser-v2 locked holdout, the parser-v3 public adversarial set and
   the full 45-record historical records were unreachable; per-record
   fingerprints are published so the main agent can close the gap before
   sealing. Until then the claim is conditional.
2. Labels are LLM consensus. A misreading shared by both reviewers would survive
   arbitration undetected.
3. Isolation is procedural and hash-audited, not security-enforced. Track C was
   authoring parser-v3 development files in the same worktree concurrently.
4. There is no empty-output case, so the `empty` quality and the `empty_output`
   failure reason are unexercised. This is a deliberate, protocol-driven gap.
5. Fixtures are hand-authored, buying determinism and contamination control at
   the cost of ecological validity.
6. n = 10 per stratum gives wide per-stratum confidence intervals; the set is
   sized to detect coarse stratum-level failure, not to produce precise rates.
7. The set is not yet sealed, so it is not yet a pre-registered holdout.
8. The locked case inputs are deliberately not committed to Git, so external
   review of the case text relies on the published per-record fingerprints and
   on the sealed private copy rather than on direct inspection of the repository.

## Paper relevance

This is the instrument section of the parser-v3 evaluation. The paper can state
that the holdout was constructed and labeled in procedural isolation from parser
development, that it does not overlap the development corpora, that its
marker-bearing strata carry strictly greater span-boundary variation than the
earlier set, and that it was sealed before any parser-v3 prediction existed —
provided the main agent completes the seal and the two outstanding cross-checks.
The paper must describe the isolation as procedural and hash-audited, and the
labels as LLM operational consensus rather than ground truth.

## Next gate

Main agent: run the three cross-checks in
`docs/phase1_parser_v3_sealing_run.md` section 9; if every intersection is
empty, seal to `phase1-evaluator-validation/parser-v3-v1/<timestamp>` with the
set manifest written last and per-object size, SHA-256 and ETag
re-verification; only then schedule a parser-v3 locked evaluation.
