# Limitations ledger

Every limitation recorded here must survive into the paper. Nothing in this file
may be softened, removed, or reframed to make a result look stronger.

## L-01 — The evaluator has failed its own validation

Prospective parser v2 failed its one-shot locked evaluation on 2026-07-25
(`boxed_final_miss` 1/20 against a limit of 0; `wrong_span` 2/80 against a limit
of 1). Consequently, **no automatic parser output may be treated as a final
label anywhere in this project.** Parser v2 remains usable only as a triage
tool, and every downstream label that matters must be semantically adjudicated.
Parser v3 is under development but is not validated and has no locked result.

## L-02 — The parser-v2 holdout is spent

The 120-case locked holdout is retired. It may not be reused for a formal
result and may not be rescored. Post-retirement reads are permitted only for
diagnosis and parser-v3 development. Any parser-v3 number computed on it is
development diagnosis, never validation. This means the parser-v2 gate results
can never be recomputed against different predictions.

## L-03 — Labels are LLM operational consensus, not human ground truth

All evaluator-set labels were produced by LLM reviewers with arbitration, not by
human annotators. Agreement statistics measure inter-model consensus. Wherever
the paper uses the phrase "ground truth", it must instead say "operational
consensus reference".

## L-04 — Isolation is procedural, not enforced

Separation between holdout curation and parser implementation is maintained by
role discipline, instruction scoping, and hash auditing. It is **not** a
security boundary. An agent with filesystem access could in principle have read
material it was instructed not to read. This must be stated whenever
independence is claimed.

## L-05 — The J-lens result is engineering feasibility only

Phase 0.5A demonstrated that the pinned official lens runs end to end on a T4
with two fit prompts. It says nothing about lens quality, correctness, or
meaning. F5 was not run. Phase 0.5B then measured saturation directly and
returned `ENGINEERING_IMPROVING`: the lens did **not** converge between 10 and 25
fit prompts (relative Frobenius 0.4170 against a 0.10 limit; cosine 0.9205
against a 0.99 limit). Engineering convergence is a necessary but far from
sufficient condition for scientific usability, and it has not been reached. No
validity criterion tying lens output to any ground truth currently exists or is
currently designed.

## L-06 — Top-k overlap is not semantic evidence

Top-k overlap and rank correlation between lens applications are numerical
stability statistics. They must never be presented as evidence about
representations, reasoning, or meaning. The Phase 0.5B values (top-k overlap
0.82, rank correlation 0.9691, logit cosine 0.9794) are reported for transport
and serialization stability only.

## L-07 — No hidden-workspace claim is available

No result in this project supports, or is on a path to supporting, a claim about
hidden reasoning, invisible chain-of-thought, an internal workspace, or
"J-space". The required chain — a validated lens, calibrated headroom cells, a
preregistered causal design, and a discriminating result — is entirely absent.

## L-08 — The historical behavioural record is underpowered

The frozen n=3 record (45 observations across 15 cells) is far too small for
inference. Its post hoc audit found 18 parser overflags, 14 observed extraction
errors, 2 material correctness errors, and 19 material evaluator issues. It may
be cited only as motivation for building a better evaluator, never as a result.

## L-09 — Headroom calibration is a screen, not an estimate

Phase 1.0C uses 1 sample per item per condition at n=10 per cell. It is designed
to screen out saturated and impossible task cells. It does not estimate pass@k,
and its confidence intervals are wide. Only two of the planned conditions
(`visible_cot`, `r1_style_thinking`) are run in this round.

## L-10 — Single-run infrastructure with no replication

Every Azure execution in this project is a single run under a one-shot
discipline. There is no repeated-measure variance for wall-clock, memory, or any
GPU-side metric, and results are not replicated across hardware.

## L-11 — Parser-v3 development is failure-informed

Parser v3 is being written with explicit knowledge of which retired holdout
cases parser v2 failed. This creates a structural overfitting risk. Each rule
change must be justified as a general improvement and exercised by an
independent public adversarial fixture, and the residual risk must be stated in
any parser-v3 report.

## L-12 — Infrastructure workarounds sit outside the committed tree

The parser-v2 locked evaluation required two infrastructure-only workarounds
applied on the orchestrator host rather than in the repository (pre-importing
Azure SDK modules before the subprocess audit guard activated, and accepting
additional label-manifest metadata). Neither changed scientific behaviour, but
they mean the committed tree alone does not reproduce the run environment
exactly.

## L-13 — The parser-v3 locked holdout is sealed, but sealing is not validation

The 120-case `parser-v3-v1` set was sealed on 2026-07-25 to
`phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/` as 12 objects, with
`overwrite=false` on every write, exact 12-object membership, round-trip SHA-256
and ETag verification, and `set_manifest.json` written last. The last outstanding
pre-seal overlap check also ran and passed: 0 exact, 0 normalised and 0
numeric-normalised collisions against the 120 retired parser-v2 locked inputs.

What that does and does not buy. It establishes that a specific instrument, with
specific bytes, existed at a specific time, before any parser-v3 result was
known, which is what makes a later one-shot evaluation genuinely prospective. It
establishes nothing about parser v3: no evaluation was run, no prediction exists,
nothing was scored, and no accuracy, precision or recall claim is licensed. The
sealed labels remain a two-reviewer-plus-arbiter LLM operational consensus, not
human ground truth. Zero overlap is proven only against the corpora actually
compared; the third registered cross-check, against an 18-record historical audit
extract, is vacuous rather than passed, because that extract carries no
output-bearing field.

## L-14 — The parser-v3 set was built in the same worktree as parser v3

Track C developed parser v3 and Track D constructed the new locked holdout during
the same round, on the same machine, in the same checkout. The separation was
enforced by task boundaries and by keeping locked inputs out of git, not by any
technical control. This is weaker isolation than an independently staffed holdout
and must be disclosed alongside any future parser-v3 result.

## L-15 — Two independent same-size J-lens fits disagree substantially

Phase 0.5B compared a 10-prompt fit against a 25-prompt fit whose corpus strictly
contained it, so that comparison described how the estimator moves as data is
added, not whether two independent fits agree. Phase 0.5C removed that
confound by construction: the corpus was amended so a genuinely disjoint
25-prompt sample existed, and a second 25-prompt lens (25B, `sat-reserve-001` …
`sat-reserve-025`) was fitted with no prompt in common with the first (25A,
`sat-fit-001` … `sat-fit-025`).

The measured answer is that they disagree substantially: relative Frobenius
**0.4831** against a registered 0.10 limit, and cosine **0.8781** against a
registered 0.99 limit. Both preregistered replicate criteria failed.

This **weakens** rather than supports a saturation reading of the earlier nested
10-to-25 movement. The nested 0.5B difference was 0.4170 relative Frobenius; two
lenses that share no fit data at all differ by 0.4831, which is the same order.
So the earlier movement cannot be attributed to the estimator converging as the
corpus grows — sampling variability between same-size fits is already large
enough to account for a difference of that size. The nested design could not
distinguish those two explanations, and the disjoint design shows the benign one
is not available.

Two fits give **one difference, not a distribution**. There is no variance
estimate, no confidence interval, and no basis for saying whether 0.4831 is
typical, high, or low for this configuration. Establishing that would require
many independent same-size fits, which was not done and is not budgeted.

## L-16 — Phase 1.0C measured 30 cells at n=10, which is a screen and not an estimate

The headroom calibration protocol, item sample, generation settings, selection
thresholds and analysis code are frozen, and the run has now executed: 300
generations, 0 errors, 30 cells scored, run `20260725T170041Z`. The earlier
statement that Phase 1.0C was "registered but unmeasured" is no longer true.

What the measurement does **not** support is any per-cell performance estimate.
Each cell holds exactly **n = 10** single-sample generations, so a cell at 7/10
carries a Wilson 95% interval of roughly `[0.40, 0.89]` — wide enough to span
"clearly below the band" to "clearly above it". Cell accuracies are a **screen**
for choosing later ablation substrates, never a stable performance estimate of
the target model, and they must never be quoted as such.

Three further limits bound the pack:

- **The pack is `INCONCLUSIVE`, not `COMPLETE`.** 44 of 300 rows were adjudicated
  as `unresolved` because the emitted output states no answer a reviewer could
  read (token-cap truncation, degenerate loops, unfilled answer templates). The
  registered finalize rule makes any unresolved label block finality, so only 2
  of 30 cells were classified `selected_headroom` and 20 fell to
  `not_adjudicated`. These 44 rows cannot be cleared by re-reviewing the same
  outputs; only a changed generation profile could clear them, and that would
  require a new preregistration.
- **Truncation is severe and is a property of the 512-token budget, not of the
  model's competence.** 79 of the 225 reviewed rows hit the cap exactly. A cell's
  truncation and no-answer rates are computed from the deterministic screening
  flags; the truncation flag is the objective token-cap signal, but the
  no-answer flag comes from parser v2 answer-presence detection, which is
  screening only and which the semantic review contradicted on 62 rows.
- **Adjudication was single-reviewer.** One primary semantic reviewer labelled
  all 225 flagged rows. Zero rows met the registered arbitration trigger, so no
  arbiter was invoked — that is an absence of contradiction with a deterministic
  screen, not an inter-reviewer agreement statistic, and no agreement rate should
  be quoted from it.

Nothing in the pack may be quoted as evidence about hidden reasoning, an internal
workspace, invisible chain-of-thought, or a "J-space"; it is task calibration.

## L-17 — The seal's prefix-conditioned ABAC grants enforced nothing

The parser-v3-v1 seal ran under the shared Container Apps job identity
`id-jspace-aca-acrpull-sea`, not a dedicated one, and that identity already held
an **unconditioned** `Storage Blob Data Contributor` assignment at account scope
on `stjspacefiles0709085305`, created 2026-07-09, sixteen days before the round.
The two temporary prefix-conditioned grants created for the run therefore did not
narrow its effective permissions at all: they were defence in depth on paper and
enforced nothing in practice. Post-run teardown measured subscription-wide Blob
roles for that identity as 1, not the 0 the specification expected, and the
surviving assignment was deliberately left in place because it pre-dates the
round and other jobs depend on it.

The consequence is specific. The guarantee that the retired parser-v2 locked
labels, scores and scoring ledger were never touched rests on the job payload's
code path, on the tests that pin that code path, and on the cross-check report's
own attestations `label_material_touched: false` and
`score_material_touched: false`. It does not rest on RBAC. This is a concrete,
evidenced instance of the project's standing caveat that isolation is procedural
rather than security-enforced, and it should be cited as that instance rather
than left abstract. The seal's integrity is unaffected, because that rests on
digests and round-trip verification, not on privilege. Any future round that
wants RBAC-enforced isolation must use a dedicated identity holding no standing
account-scope blob role, and must verify that **before** creating the grants.

## L-18 — The merged-50 improvement is close to arithmetically forced

Phase 0.5C registered, before the run, that "merged-50 held-out apply stability
improves" means `mean(pair(25A,50M), pair(25B,50M)) - pair(25A,25B)` clears
0.02 for top-k overlap and 0.005 for rank correlation simultaneously. Both were
met, by +0.1200 and +0.0330. That result is real and was honestly gated, but it
is weak evidence and must not be read as convergence.

The 50-prompt lens is the official 25/25 weighted merge of the two single fits,
which is an exact weighted mean of their matrices. A mean necessarily lies
between its own two inputs, so it is expected to be closer to each of them than
they are to each other, and to be roughly equidistant from both. The run shows
exactly that signature: `25A_vs_50M_relative_frobenius` is 0.2565246384392308
and `25B_vs_50M_relative_frobenius` is 0.25652465564092874, agreeing to
**1.7e-08**. A held-out statistic computed against a point that sits between two
disagreeing endpoints will move toward both endpoints almost mechanically.

The improvement therefore says the merge is well formed and the transport
arithmetic is sound. It does **not** say that adding data is making the estimator
converge, that the merged lens is closer to any truth, or that a 50-prompt fit
would be better than a 25-prompt fit. No ground truth was available and none was
used. Distinguishing a genuine data-driven improvement from this arithmetic
artefact would require comparing the merge against an independently fitted third
lens on prompts used by neither input, which was not done.

## L-19 — The two fit samples are not provenance-symmetric

25A and 25B are disjoint but they are not interchangeable draws from one
generation process. All 25 prompts in 25A, and the first 15 in 25B, come from
the original registered corpus generation for Phase 0.5B. The remaining 10
(`sat-reserve-016` … `sat-reserve-025`) were authored later, for this round, by
the agent that also wrote the Phase 0.5C protocol, with the Phase 0.5B outcome
already known.

The generation constraints were replicated mechanically and verified — neutral
third-person descriptions of mundane non-reasoning processes, 38–44 proxy tokens,
199–238 characters, zero forbidden cues, zero exact or normalised overlap with
22 460 strings from four other corpora, pairwise distinct — and
`scripts/verify_jlens_corpus_amendment.py` re-checks all of it deterministically
(84 checks, 0 failed). But 40 percent of 25B was written by a party that knew the
result the amendment was meant to enable, and no blinding was applied. This
cannot be corrected retrospectively and should be disclosed alongside the 0.4831
figure. It is a reason the measured disagreement could be either over- or
under-stated; its direction is unknown.

AR-0035,0.5C,20260725T174743Z,04_decision.json,decision,repo:artifacts/phase05c-jlens-disjoint/track-a1/20260725T174743Z,f47a6f26b51ccaa4aec0ed6f2d54a340f298181f7482aa13f26b26a17cea3742,2859,no,no,primary_result
AR-0036,0.5C,20260725T174743Z,06_paper_table.csv,metrics,repo:artifacts/phase05c-jlens-disjoint/track-a1/20260725T174743Z,a5473dd5bf4850bd2eaad9c1d9dda9a3249454c8c9c7e36a3ff6e9bf19ab8087,3819,no,no,table_source
AR-0037,0.5C,20260725T174743Z,07_figure_data.csv,figure_data,repo:artifacts/phase05c-jlens-disjoint/track-a1/20260725T174743Z,0df3d12128bb12c87b4fbdf65d0bcb7370a3c907c816526bb7238a937333e684,9307,no,no,figure_source
AR-0038,0.5C,20260725T174743Z,artifact_manifest.json,manifest,repo:artifacts/phase05c-jlens-disjoint/track-a1/20260725T174743Z,abe0a6125eaa6ac1e184d7949a25a8ba461487dba97914b83584107e48aeebf2,1515,no,no,provenance
AR-0039,0.5C,20260725T174743Z,jlens_saturation_prompts.jsonl,fit_corpus,repo:data/jlens_saturation_prompts.jsonl,dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa,16087,no,no,public_fixture
AR-0040,0.5C,20260725T174743Z,j-space-jlens image,container_image,acr:acrjspaceobssea0708231738/j-space-observation-jlens,1fdf406fa34d76f228bd8a3570e9564c0a63baadda8e5b3e58f9c0e1b9ad3a37,not_recorded,yes,no,provenance


## L-24 - The parser-v3 safety boundary needed repair before it was trusted

Before the parser-v3 preregistration commit `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea`, Stage E's
parser-import prohibition omitted parser v3 from several exact-match deny lists
and probes, and the three-stream orchestration contained four further defects
that would have surfaced only after prediction generation or after the first
label read. Two of those four would have spent or wasted the one-shot holdout:
a payload-ordering fault that fails after all 360 parser invocations, and a
ledger validator fault that raises **after** the label download and forces
`INVALID`.

They were found by two independent read-only preflight reviews and fixed before
preregistration, prediction generation, holdout access and label access, so the
formal evaluation is unaffected. The limitation that survives into the paper is
not "a bug existed" but this: **the isolation between parser development and
holdout scoring in this project is procedural and hash-audited, not
security-enforced, and it required an explicit adversarial review pass to hold.**
A reader should treat the parser-v3 result as depending on that review having
been thorough, not on a mechanism that makes the failure impossible.

## L-25 - Parser v3 has no locked result

As of commit `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea` parser v3 is preregistered and frozen but **not
evaluated**. No prediction has been generated, no locked label has been read,
and the holdout is unspent. Parser v3 must not be described as validated,
non-regressive, or better than parser v2 anywhere, and no automatic parser
output may be treated as a final label. Parser v2's failed locked evaluation
(L-01) remains the only locked parser result in this project.

## L-26 - The parser-v3 acceptance gates do not describe the parser-v3 set

The parser-v3 gate contract and the sealed parser-v3 validation set were
built independently and never cross-checked. They disagree, and the
disagreement is fatal to scoring.

```
docs/phase1_parser_v3_acceptance_gates.json
  typed_decision.labels                   3 classes
  null_collapse_prohibited                true
  dataset_contract.typed_decision_support {ambiguous: 10, no_answer: 30, present: 80}

evaluator_sets/parser_v3_v1 (sealed)
  typed-decision classes present          4  (adds present_unextractable, 4 cases)
  answer-presence support                 {present: 91, no_answer: 23, ambiguous: 6}
  strata                                  12 x 10 = 120   (correct)
```

The gates `ambiguity`, `no_answer`, `answer_presence_macro_f1` and
`overall_exact_typed_decision` are calibrated against the declared support.
Against the real support their difficulty is different and unknown. The
fourth decision class has no gate treatment at all and cannot be collapsed
into `no_answer` without violating `null_collapse_prohibited`.

The contract was derived from the parser-v2 contract by substitution rather
than re-derived from the parser-v3 set: the `last_number_trap` gate blocks in
the two contracts are byte-identical, including an `error_definition` naming a
registered distractor span that the parser-v3 set does not contain.

Consequence for the paper: **no parser-v3 acceptance threshold in this
repository may be cited as calibrated**, and no parser-v3 gate result may be
reported, because none was computed. The Phase 1.2D round was halted in
preflight with the holdout `SEALED` and unspent. Full detail in
`docs/phase1_parser_v3_locked_evaluation_protocol.md` §15.

## L-27 - The parser-v3 set and the scoring instrument use different span conventions

The sealed parser-v3 set registers **marker-inclusive** evidence spans: 104 of
its 111 registered spans have `span.text` equal to the enclosing marker phrase
rather than the numeric literal. All three parsers, including parser v3
(`eval_parsing_v3.py:390-400`), construct candidates through the frozen
`validate_evidence_span` and therefore emit **literal-only** spans.

Had this been scored as built, prediction and label spans could never have
matched, and every span-conditioned gate would have failed for reasons
unrelated to parser quality. Any future parser-v3 result must state which span
convention was in force and demonstrate that set and parsers agree on it.

A lossless normalisation exists and is recorded (§15.4, `N1`): each marker span
maps to its contained numeric literal, uniquely for 109 of 111 spans. It is
recorded, not adopted, because it does not resolve L-26.

## L-28 - A mandatory parser-v3 gate would have been vacuous

`last_number_trap` is mandatory under `status_logic.PASS =
all_absolute_and_legacy_comparison_gates_pass`. Its error definition names a
registered distractor span, and the sealed parser-v3 set contains no distractor
span in any of its 120 records. Scored as written, `label["distractor"]` would
have been `None` everywhere, the gate would have counted zero errors
unconditionally, and it would have appeared in the result table as an enforced
mandatory gate that passed.

This is recorded as a limitation of the *artifact set*, not of any result: it
was found in preflight and no evaluation was run. Deriving the distractor by
the frozen instrument's own rule — the rightmost registered numeric literal,
which `evaluator_validation.py:2109-2116` already *requires* a registered
distractor to be — makes the gate non-vacuous on all 10 S06 cases. Any future
parser-v3 evaluation must demonstrate non-vacuity of every mandatory gate
before preregistration.

## L-29 - The parser-v3 repair tooling has synthetic-test evidence only

The Phase 1.2E ontology validator, `N1`-`N6` normalizer, agreement validator and
contract compiler are exercised exclusively against public synthetic fixtures:
a constructed 120-case, 12-stratum valid set and one negative fixture per
historical defect. They have never been run against a real curated evaluation
set, because no admissible one exists.

Synthetic fixtures are built by the same author as the code they test, so they
demonstrate that the tooling behaves as specified; they cannot demonstrate that
the specification anticipates every way a real curated set can be wrong. The
first application of this tooling to a real `parser-v3-v2` set is therefore
itself an untested step, and any failure it reports on that first run must be
investigated as a possible tooling defect before it is treated as a set defect.

This limitation is not hypothetical. The first implementation of this tooling
passed 93 self-authored tests and was nevertheless found by an independent
reviewer to declare `parse_valid = false` for `ambiguous`, where the frozen
scoring instrument requires `true` — a defect that would have rendered every
`S11` case unscorable by construction. The fixtures did not catch it because
they encoded the same misunderstanding as the code. Ten defects were found and
fixed in total, two of them critical; the record is
`reports/phase1_2e_parser_v3_repair.md` §6. The structural remedy —
`_bind_to_scoring_instrument`, which requires every accepted record to be
accepted by the frozen instrument itself — reduces but does not eliminate this
limitation: it now covers everything the frozen instrument checks, and nothing
it does not.

## L-30 - The parser-v3 acceptance thresholds have no calibration basis

The prospective policy `docs/phase1_parser_v3_v2_evaluation_policy.json` leaves
every numeric acceptance threshold `REVIEW_REQUIRED`: the overall exact
typed-decision minimum, the per-stratum critical floor, the answer-presence
macro `F1` minimum, and the non-regression margin against parser v2.

There is no basis to set them. Importing the parser-v2 constants would carry
over an unjustified number, and deriving
a threshold from any parser-v3 observation would select the threshold against
the measurement it is meant to bound.

> **Erratum E-1.2F-01 (Phase 1.2F).** As first written, this limitation also
> stated that "Phase 1.0C headroom calibration is preregistered but `BLOCKED`
> with no model run". That was false when written, and it contradicted `L-16`
> in this same ledger, which already recorded that Phase 1.0C *was* measured.
> Phase 1.0C executed and finalized `INCONCLUSIVE` at `06eec993`. It is
> target-model task/headroom screening and is not a parser calibration, so it
> was never capable of supplying these thresholds. This limitation also
> described the unjustified-constant problem as "of exactly the kind that
> produced `H9`"; that conflation is withdrawn. An unjustified threshold source
> is a **policy-provenance defect**, a distinct failure class from `H9`, which
> concerns disagreement among declared and observed artifact vocabulary,
> support, or set facts. `H1`–`H9` are unchanged. Superseded in substance by
> `L-33`.

The mandatory gates are unaffected: they are derived from stratum purpose,
which is a public design fact, and their zero-tolerance definitions are
definitional rather than calibrated. But no parser-v3 `PASS` is expressible
until the thresholds are resolved, and the contract compiler refuses to emit a
contract while any of them is open.

## L-31 - The sealed parser-v3 set violates its own public specification

`evaluator_sets/parser_v3_v1/strata_definitions.md` is a tracked public file
that registers, per stratum, the expected answer presence and several
cross-cutting quotas. The sealed set disagrees with it in four separate ways:
`S10` is publicly `no_answer` but its cases are labelled `present`; the public
quota table asserts 80 `present`, 30 `no_answer` and 10 `ambiguous`; the public
rule that every `S11` case carries at least two distinct canonical candidates is
violated; and the public statement that the set exercises no `empty` output is
violated.

This widens the root cause recorded for `H9`. The gate contract was indeed
derived from parser v2 by substitution, but even a contract correctly derived
from the public stratum definitions would have disagreed with the set. The
missing artifact was never merely a better contract — it was any mechanical
agreement test between the set, its own public specification, and its gates.
Phase 1.2E supplies that test; it has not been run against the retired set, and
will not be, because that set is permanently ineligible.

## L-32 - The sealed object count and member list are asserted, not derived

The Phase 1.2E facts manifest separates two kinds of claim that look alike in a
JSON file. Class supports, stratum counts, gate denominators and every hash are
*derived*: they are recomputed from the set's own bytes by `build_set_facts`,
and every entry point re-derives the whole manifest and requires byte-equality
before using it, so none of them can be misstated without detection.

`sealed_object_count` and the member list are not like that. They describe a
remote storage prefix, and no offline tool can list a blob. An operator who
declares twelve objects and supplies twelve fabricated member digests produces a
self-consistent manifest that the agreement validator accepts, because there is
nothing available to contradict it. This was demonstrated during the round's
second audit and is recorded here rather than fixed, because it cannot be fixed
offline.

The mitigation is procedural and belongs to a future round: the listing artifact
that witnesses the object count must be named in the manifest and bound into the
compiled contract, so the assertion is at least attributable. Until then, the
object count in any compiled parser-v3-v2 contract carries the authority of the
operator who typed it, not of the tooling that recorded it. The number `12` is
exactly the figure the Phase 1.2D erratum exists to correct, which is why the
distinction is written down rather than assumed.

## L-33 - The acceptance policy is written after some development results are known

Phase 1.2F preregisters acceptance criteria for a `parser-v3-v2` evaluation
that has not been designed, built, sealed or run. That ordering is correct. What
it cannot undo is that the operator writing the policy already knows things: how
parser v2 performed on its locked set, how parser v3 behaved during development
on non-locked material, and why `parser-v3-v1` was retired as ineligible.

A policy written under those conditions is exposed to a failure mode that no
amount of care fully removes. A threshold can be chosen because it is defensible
and *also* because the author quietly expects the candidate to clear it, and the
author will not reliably be able to tell the two apart from the inside. Stating
the derivation does not settle it, because a derivation can be selected after
the fact to reach a number that was picked first.

The round's defence is structural rather than introspective. Every recognised
basis type requires the value to be traceable to something outside the
candidate: a logical invariant, a registered downstream error budget, an
external calibration preregistered before candidate outputs are observed, or a
stated operational requirement independent of both candidate and holdout.
The one criterion that survived the redundancy audit,
`residual_critical_exact_budget`, was left `REVIEW_REQUIRED` with a null
value throughout Phase 1.2F for exactly this reason: its structure was
derivable then, its number was not, and inserting a plausible integer would
have been the failure this limitation describes.

> **Phase 1.2G update.** That criterion is now `FINAL` with a value of `0`, on
> a `LOGICAL_INVARIANT` basis. The number was not calibrated and no observation
> supplied it; it is entailed by the strict finite-suite conformance premise
> adopted in Phase 1.2G, under which every admitted case carries an individual
> mandatory requirement. The limitation above is therefore not discharged, it
> is relocated: what now needs scrutiny is the premise rather than the integer,
> and that is recorded as `L-35`. The general warning stands unchanged — a
> number that looks defensible is not the same as a number that is derived, and
> this ledger entry remains the place to check which one a future threshold is.

**What the validator actually does, stated precisely.** Audit finding B8
rejected an earlier version of this paragraph, which claimed the validator
rejects five prohibited bases. It rejected two. The scan now carries 22
normalised needles covering parser-v3 development accuracy, parser-v2 locked
performance, expected performance, Phase 1.0C headroom, verbatim carry-over
from the predecessor contract, selection because a value would permit a pass,
and unsourced appeals to industry practice or common practice — applied across
`reason`, the structured `blocking_dependency`, every evidence binding, and ten
prose fields of every threshold record whatever its disposition, after
collapsing hyphens, underscores and line wraps.

That is a **bounded carelessness check, not a semantic guarantee**. It catches a
prohibited basis that is *named*. It cannot catch one that is paraphrased, and
it is not a substitute for review. Claiming more of it would itself be an
instance of the over-claiming this ledger exists to prevent.

This is recorded as a permanent limitation, not a resolved issue. Even after the
strictness decision is taken and, if needed, a calibration supplies a budget,
the resulting threshold will have been set by someone who was never blind to the
candidate. The honest claim is that the number is traceable to a preregistered
requirement, not that it was chosen in ignorance.

## L-34 - The current-state consistency check bounds a class of error, not all of it

`scripts/check_current_state_consistency.py` exists because Phase 1.2E read a
stale summary and wrote a false blocking dependency into a policy artifact. Its
first version could not have caught that: it matched line by line with patterns
that forbade a newline, while this repository hard-wraps at about 76 columns, so
the actual defect split across three lines and matched nothing. Its exemption
list was a substring test against common words, so writing "corrected" anywhere
on a line disabled the check for that line, and it did not scan the artifact
class in which the defect occurred. All three were found by the round's second
independent audit and repaired, and the repaired checker is proved against the
verbatim `d843984` text of five files.

What remains is a genuine limitation. The check is a pattern matcher over
whitespace-collapsed paragraphs. It detects the *phrasings* of "Phase 1.0C was
never run" and "Phase 1.0C supplies a parser threshold" that are registered in
its pattern tables. A future stale claim expressed in wording nobody anticipated
will pass, and a document could be uniformly stale in some other respect
entirely without the check noticing, because it knows about exactly one
experiment.

Its exemption rule is also a trade. Errata must remain writable, so a paragraph
structurally anchored as historical or corrective, or a sentence that explicitly
negates the claim, is skipped. That is deliberately narrower than the first
version, but an author who anchors a genuinely current-state paragraph with the
word "Historical" will still evade it. The check reduces the cost of a known
recurring error; it does not make the class of error impossible, and it must not
be cited as evidence that a document is accurate.

One further defect was found by the checker itself during Phase 1.2F
remediation, after both audits had reported. Markdown emphasis delimiters were
not elided before matching, so `**not**` inserted asterisks into the middle of
every contiguous phrase pattern. The visible symptom was a false positive on the
round's own corrective sentence "Phase 1.0C is **not** parser calibration". The
more serious form was the mirror image: `Phase 1.0C has **not** been run` would
have passed the check, so a stale claim could have been emphasised into
invisibility. Emphasis and code-span delimiters are now elided; `_` is not,
because it is load-bearing inside `NOT_RUN` and `sealed_object_count`. The
general lesson stands as part of this limitation: a matcher over rendered-prose
patterns is sensitive to markup that carries no meaning, and no amount of
pattern tuning converts it into a semantic check.


## L-35 - Zero residual tolerance rests on a premise, not on a proof

`residual_critical_exact_budget` is `0` because Phase 1.2G adopted **strict
finite-suite conformance**: the future `parser-v3-v2` set is a finite
conformance suite, every case admitted to it is admitted because a correct
instrument must handle it, and so a mismatch on any admitted case is
unacceptable instrument behaviour. Given that premise, zero is a
`LOGICAL_INVARIANT` - there is no coherent positive tolerance, because each
admitted case carries its own requirement and an aggregate allowance of `B > 0`
contradicts a per-case obligation rather than relaxing it. The argument does not
turn on a budget being unable to name which cases it covers.

The premise itself is a design decision. It was taken by the operator, recorded
in `docs/decision_log.md`, and it is not a measurement. No observation licenses
it and none refutes it directly; what refutes it is a change in how the set is
built.

That is the limitation. The value `0` is exactly as secure as the premise, and
the premise has a stated falsifier: if a future authorized round admits a case
that a correct instrument is *not* required to handle - an aspirational case, a
case included to observe behaviour rather than to require it, or a case whose
own reference label is uncertain - then the suite is no longer a pure
conformance suite, the invariant loses its basis, and the value must be
re-derived rather than inherited. Eligibility for admission and "must be handled
correctly" have to remain the same predicate. The set-repair round inherits that
constraint, and this ledger entry is the place it is recorded as a liability
rather than as a settled fact.

A second-order caution. Because the invariant is derived from the construction
rule, it is possible to satisfy the *policy* by weakening the *set* - admitting
fewer or easier cases keeps the budget at zero while reducing what zero means.
Nothing in the acceptance policy can detect that, because the policy sees the
set only through its declared strata and supports. The protection has to come
from the set-repair round's own review, not from here.

## L-36 - A conforming instrument is not a demonstrated-adequate one

Every criterion in the prospective acceptance policy constrains the
**instrument**. None of them constrains the **science**.

A parser that satisfies the policy is one that reproduces the reference typed
decision on all 120 cases of a stratified challenge set. That is a statement
about extraction fidelity on a designed suite. It is not a statement that the
downstream scientific conclusion is robust to parser error, and it must never be
reported as one.

The gap is concrete and is not closed anywhere in this repository. No downstream
parser-error budget is registered: the scientific plan does not state how much
parser-induced distortion any later metric or decision can absorb before its
conclusion changes. Phase 1.2F searched for one and found none; Phase 1.2G did
not create one, because under the conformance premise the residual budget did
not need it, and manufacturing a budget to fill a documentation hole would have
been worse than recording the hole.

So the following inference is unavailable, and remains unavailable after any
future `PASS`:

> The parser passed, therefore parser error does not threaten the scientific
> result.

What a `PASS` would license is narrower and should be stated in exactly this
form: on this fixed 120-case suite, under this ontology and span convention, the
parser reproduced every reference typed decision. Whether that fidelity is
*sufficient* for any particular downstream claim is a separate question that
requires a downstream error budget, and that question is open.

The reverse direction is also worth stating, because it is easy to overclaim in
the other direction. A `FAIL` on this policy is not evidence that the scientific
conclusion is wrong either. It is evidence that the instrument is not fit to be
used to reach one.

## L-37 - The successor evaluation set cannot currently be built at all

Phase 1.2H was authorized to repair, construct and seal the successor
`parser-v3-v2` evaluation set. It could not begin. The authoritative retired
`parser-v3-v1` sealed source sits behind a storage account with
`publicNetworkAccess = Disabled`, reachable only by a user-assigned managed
identity exercised from in-network compute. That access is unobtainable from the
environment the project is currently operated from.

This is a limitation on the *project*, not only on one round. Until it is
resolved, no successor set can be constructed, so no evaluation set exists, so
no preregistration and no evaluation are possible. Every downstream scientific
claim that depends on a validated parser is therefore blocked behind an
infrastructure-access problem, not behind a methodological one.

Two things must not be inferred from the block.

First, it is **not** evidence that the retired set is unavailable in principle.
The infrastructure exists and the objects exist; what is missing is a path from
the current operating environment to them that satisfies the read-only boundary.

Second, the local curator copies are **not** a workaround. They match the
committed public manifest exactly, on digest and byte count. That establishes
agreement with a Git record, not with the sealed source, and the sealed source
is what the set's identity is defined against. Proceeding from them would
produce a successor set carrying a provenance claim that is false in a way no
later check could detect. The correct reading of the byte-only verification is
narrow: the local files are what the repository says they are. It says nothing
about whether the repository's record matches the seal.

There is also a design constraint that the eventual fix must respect, and that
makes the fix harder than "obtain network access". The blind semantic review the
repair requires executes as reviewing agents *outside* that network. A solution
that reads private content inside the boundary and then transports it out to
those reviewers satisfies the network rule in form and breaks it in substance. A
sound resolution has to place the semantic review inside the boundary, or
establish an equivalent isolation that the reviewers genuinely operate under.

### Amendment (Phase 1.2H-R1): the first clause of this limitation was wrong

The claim that the access "is unobtainable from the environment the project is
currently operated from" was a false negative. It is corrected here rather than
rewritten above.

`publicNetworkAccess = Disabled` does not mean unreachable. It means unreachable
from outside the virtual network. The account has a private endpoint at
`10.80.2.4` and a linked private DNS zone, both recorded in committed evidence
Phase 1.2H itself cited. Phase 1.2H-R1 provisioned a VNet-injected Container Apps
job under a two-role identity and reached the source: 12 members listed, 12
objects streamed to a SHA-256 accumulator, 396,613 bytes, aggregate digest
reproducing the public anchor `e1364afc…`.

That is worth stating plainly because the error ran in the project's favour in
one sense — it produced a *more* conservative record — and against it in another:
a round was terminated on a capability the project already had. A research record
that overstates its own blockers is not thereby safe; it is inaccurate.

What survives unchanged is the second half of this limitation, and it is the half
that still blocks the project. The design constraint described in the paragraph
above — that blind semantic review must occur inside the boundary — is now the
**operative** blocker. R1's executable assessment scores 0 of 13 conditions
passed, 5 failed and 8 not assessable: no in-VNet reviewer service exists, the
only same-region AI account is public-facing and belongs to another project, and
the worker subnet has no egress control attached. So this limitation's conclusion
stands — no successor set can be constructed, no preregistration and no
evaluation are possible — but its reason has moved from *source access* to
*review boundary*.

The paragraph about the local curator copies is unaffected. R1 does not make them
a workaround; it makes them unnecessary, and it confirms what they could not: the
repository's public record does agree with the sealed source, at the level of
bytes and digests.

## L-38 - The audit regress has never reached a fixed point

Seven independent read-only reviews have now been run against this repository's
policy and instrument set: Audits A and B in Phase 1.2F/1.2G, three
post-remediation re-reviews C, D and E, and Audits F and G in Phase 1.2H. **Every
re-review found real defects in the remediation of the one before it.** Audit F
found all six Audit E remediations incomplete, each with a working
counterexample; Audit G then found a blocker and four majors in the Audit F
remediation, including a ledger that would validate a fabricated sealed set.

The regress has been terminated at every stage by *disclosure*, never by a
review that found nothing. Audit G was the final-state pass of Phase 1.2H, and
its own remediation is likewise not re-reviewed.

The available inference is therefore weaker than "the instrument set is
correct". It is: the per-pass defect rate is not low, and the current state is
the most corrected the artifacts have been. It is specifically **not** that the
process is converging. The recorded sequence is A = 5 findings / 1 blocker,
B = 11 / 1, C = 7 / 1, D = 5 / 2, E = 6 / 1, F = 6 / 0, G = 6 / 1 — neither
count nor severity is monotonic, and A and B were initial audits rather than
remediation reviews, so they are not comparable terms in such a series anyway.
An earlier version of this entry claimed each pass found fewer and less severe
defects than its predecessor. That claim was not supported by these figures and
is withdrawn; it was identified by Audit G.

A further caveat applies to what "independent" means here. The reviewers are
automated agents operating on this repository under the same instructions as the
authoring pass. They are independent **of the pass**; they are not independent
**of the project**, and no external human reviewer has approved any value,
threshold, disposition or claim recorded anywhere in it.
## L-39 - Byte-only access proves provenance, not content, and cannot be stretched further

Phase 1.2H-R1 streamed every object of the retired `parser-v3-v1` sealed set
and matched every digest. It is important to state exactly how little that
licenses.

What it establishes: the 12 objects at the registered prefix are, byte for byte,
the objects the committed public manifest describes, and the aggregate digest
matches an anchor that was published before the read occurred. That is a
provenance fact about the *container*, and it is a real one — it rules out drift,
substitution and wrong-container error.

What it does not establish, and what no amount of digesting could:

* that the cases inside are well formed, or ontologically consistent, or free of
  the defects the repair round exists to fix;
* that the 15 quarantined cases are repairable;
* that the 105 migratable cases are in fact migratable;
* anything whatever about parser v3.

The distinction is not pedantic. The temptation a passing gate creates is to
treat "we verified the sealed set" as progress toward validation. It is progress
toward *access*, and access was never the scientific question. Every defect the
repair round was chartered to find is a semantic property, and semantic
properties are precisely what a byte-only read is constructed to be blind to.

A second caution concerns the direction of the evidence. The gate compares the
live source against the repository's committed record. Agreement means the two
agree. It does not independently corroborate either: had both been wrong in the
same way from the start, the check would still pass. The seal-time observation
that would settle that is the one limitation `L-32` describes, and it remains
unavailable.

## L-40 - Every R1 audit reviewed a commit that is not the one being published

Audits A and B for Phase 1.2H-R1 reviewed commit `47f207a`. Both returned
BLOCKED, and their blockers were remediated in `56141c1` — after which the
access gate ran, the ledger gained a terminal state and a provenance block, six
documents were updated, and roughly a further 400 lines of test were added.

Audit C then reviewed `393ff3e`. It also returned BLOCKED, with one blocker and
eight major findings, and its blocker was material: the instrument that decides
this round's terminal state took the byte-only gate outcome as an operator-set
command-line flag and never read the execution receipt, so it could not have
detected a failed gate. That was remediated in `ccbaab0`.

Audits E and F then reviewed `ccbaab0` — the remediated state. Both returned
BLOCKED, with eighteen findings between them. That result is the most useful
evidence this ledger entry has, and it points the other way from reassurance:
one round of remediation, reviewed, produced eighteen further defects, several
of them in the very sentences written to describe the previous fixes. Their
findings were remediated in `13015d4`.

Audits E and F then reviewed `13015d4` on closure. **Both returned BLOCKED
again.** Between them they demonstrated, with working counterexamples rather
than by reading: that the composite provenance class added to satisfy F-06 let
`labels_opened_for_scoring` carry the value 7 on two lines of prose, reopening
precisely the route that adding that counter to `_MACHINE_EVIDENCE_REQUIRED`
for E-10 had closed in the same commit; that the byte-flow analysis still
admitted `return digest.hexdigest(), total, chunks`, handing every chunk back to
the caller, because it tracked the loop variable and not the parameter; that a
digest receiver from any module offering `sha256` was accepted while the
docstring said `hashlib`; and that two rows of the disposition table certifying
these fixes were false as written. Those are remediated in the present commit,
which is again material no audit has seen.

The pattern is now three rounds long and has not converged. Each remediation has
been found defective by the next review, and twice the defect was introduced *by
the remediation itself*. The honest reading is not that the instruments are
converging on correctness but that self-review does not find this class of
defect — every one of the counterexamples above was produced by an independent
reviewer, and none by the author's own test suite, which was green throughout. A
green suite here means "the properties I thought to check hold", and the
recurring failure has been in what was not thought of.

A previous version of the sentence above said the counterexamples were produced
by a reviewer *executing the code*. That was itself an overstatement of the kind
this section documents. Several were: Audit E ran the validator to show that
`data_plane_content_reads = 500` was accepted. But Audit F established F-03b by
reading the source, with no execution, and the byte-handler rebinding defect
(E-19) was found by reasoning about which definition `ast.walk` returns versus
which one Python binds. Attributing all of them to execution overstated the
method and understated the finding: static reading was sufficient to break these
instruments, which is a worse result than needing to run them.

The third review round (of `55d0e2b`) found eight further defects and is
recorded in §7.6 of the round report. Its two most serious findings share a
shape worth naming, because it is the shape that keeps recurring: **a check that
constrains an artifact it was never bound to.** The byte-flow analysis
constrained the body of a function selected by `ast.walk` order, while Python
binds by definition order, so three different wrappers passed while exfiltrating
every chunk. Two counters were excluded from a safety pin on the stated grounds
that another rule constrained them; that rule constrained neither. In both cases
the check was correct about what it examined and silent about whether what it
examined was what ran.

The sequence is eighteen findings, then twelve, then eight. The counts are
falling, which is not the same as convergence and should not be read as it: each
round's remediation has still been found defective by the next independent
review, and no round has yet closed. Whether the fourth review closes is not a
fact this document can assert in advance — the last two times a version of this
paragraph tried, the attempt was itself cited as a finding.

An earlier draft of this section claimed that "Audits C and D reviewed the final
state, so the gap is narrowed rather than open". That sentence was written
before either audit returned, and Audit C identified it as the sharpest instance
in the round of the defect it was describing: a claim about evidence, asserted
in advance of the evidence. It has been withdrawn. Audit D did not complete; its
process was lost before it reported, and no finding of its should be attributed.

The gap is therefore not closed. It is the structure `L-38` describes: every
remediation pass produces material that the pass which motivated it never saw,
and the only way to close it completely is a review that finds nothing, which
has not yet happened in this phase.

One specific residual should be named rather than left implicit. Audit A stated
that "no path was found by which a private semantic read, a data-plane write, or
an export of sealed content could occur", and that statement is the load-bearing
safety finding of the round. It was made against `47f207a`. The probe changed
substantially afterwards — the emission contract, the AST checks, the client
chunk bindings and the identity handling were all rewritten. Audit C re-examined
the property against `393ff3e` and reached the same conclusion, which is the
strongest support the finding currently has.

That support should not be overstated in one specific direction. The `maximum:
0` schema pins have been described elsewhere in this repository as if they
detected a violation. They do not, and the claim has been withdrawn wherever it
appeared. The probe writes those counters as literals; a probe that decoded a
sealed object would emit `0` just the same and the receipt would validate. What
the pins actually do is narrower and still worth having: they make it impossible
for a receipt to *report* a non-zero count and remain schema-valid, so an honest
instrument cannot quietly normalise a violation into a valid artefact. The
enforcement that makes the literal zeros credible is the AST check over the
probe's own source, plus the fact that the module performs no decode and no
data-plane write — properties that are established by reading the code, which is
inspectional, not structural.
