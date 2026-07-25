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
