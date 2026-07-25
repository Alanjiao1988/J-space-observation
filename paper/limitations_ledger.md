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
meaning. F5 was not run. Even after Phase 0.5B saturation, engineering
convergence is a necessary but far from sufficient condition for scientific
usability, and no validity criterion tying lens output to any ground truth
currently exists.

## L-06 — Top-k overlap is not semantic evidence

Top-k overlap and rank correlation between lens applications are numerical
stability statistics. They must never be presented as evidence about
representations, reasoning, or meaning.

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
