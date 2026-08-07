# Study 2 reasoning-internalization protocol

## Status and claim boundary

This document explains the canonical JSON at
`reasoning_internalization_protocol.json`. During candidate construction its
status is `CANDIDATE_AWAITING_REVIEW`; after the single bounded review and any
one consolidated correction it may be frozen as `FROZEN_AWAITING_STAGE_T`.
Neither status is empirical evidence.

The registered question is exactly:

> Does the R1-distilled checkpoint compute and causally use a task-defined intermediate variable during a single forward pass with zero generated reasoning tokens, and is that behavior or mechanism stronger than in both its lineage base checkpoint and a same-family instruction-tuned control?

The claim ceiling is narrower than “genuine reasoning”: if every future gate
passes, the study may say that the target checkpoint uses a causally
load-bearing intermediate variable on these fresh compositional tasks under a
controlled no-generated-trace interface. A distillation-associated statement
additionally requires superiority to both fixed controls. It remains a
checkpoint-level association, not identification of a teacher trace, training
example, loss, or objective.

## Canonical JSON crosswalk

- `/schema_version`, `/study_id`, `/created_on`, `/stage`, and `/status` bind
  the protocol version and lifecycle.
- `/authority` binds the operator-supplied starting commit/tree, bootstrap
  authority, immutable 53,018-byte Stage P prompt, Study 1 and Phase 1.0D
  states, EV-0016 evidence tail, D33 study boundary, and every protected hash.
- `/identities` fixes exactly the target, lineage-base, and instruction-control
  checkpoints and immutable revisions. It also fixes later float16/eval-mode,
  `use_cache=false`, `trust_remote_code=false`, separate loading, identical raw
  UTF-8 prompt bytes, and the target-only secondary J-lens identity.
- `/research_question` is the exact operational question quoted above.
- `/claims` fixes the internal-computation, distillation-association, and
  J-space ceilings and keeps all prospective claims unsupported until real
  confirmation evidence exists.
- `/task_design` fixes both finite-state families, depths, templates, option
  labels/surfaces, bank sizes, seeds, counter-mode generator, balance,
  semantic identity, normalization, protected-prompt overlap audit, and
  independently reconstructible ground truth.
- `/pair_design` fixes donor/recipient recombination, matched donors,
  wrong-position anchor, 256-row candidate cells, and mechanics-only Stage T
  selection of the first 128 eligible pair hashes.
- `/prompt_arms` defines NT, PT, WT, and ST and explicitly excludes generated
  chain of thought.
- `/stage_machine` fixes P → T → B-D → B-C → M-D → M-C separation. Every stage
  after P requires new authority.
- `/metrics` fixes restricted-logit, Wilson, bootstrap, trace, causal patch,
  probe, and target-only J-lens quantities.
- `/selection` fixes target-only compositional-cell and development-window
  selection and applies the choices unchanged to both controls.
- `/classification` closes the internal, distillation, J-lens, composite, and
  operational truth tables.
- `/output_contract` closes every Stage P row and future behavioral,
  mechanistic, probe, J-lens, and classification row required to reconstruct a
  result without semantic interpretation.
- `/review` fixes the one 15-question review, one consolidated correction, and
  same-checklist verification allowance.
- `/operation_limits` records that all tokenizer, model, lens, activation,
  probe, intervention, provider, GPU, Phase 1.0D, RQ2/S4, and scientific-row
  operations are zero in Stage P.
- `/limitations` freezes the interpretation boundaries listed at the end of
  this document.

The JSON Schema uses an exact closed contract for every top-level canonical
section. Missing, extra, or altered nested content therefore fails schema
validation. The pure-Python semantic validator separately checks identities,
values, formulas, bank rows, hashes, balance, truth tables, and protected
bytes. NaN and Infinity are rejected by the strict loader before either check.

## Task families and surfaces

`permutation_chain` uses states 0–7 and three complete permutations P, Q, and
R. `affine_mod10` uses states 0–9 and three invertible maps
`f(x)=(a*x+b) mod 10`, where `a ∈ {1,3,7,9}` and `b ∈ {0,…,9}`. All three
operator definitions and the complete state legend appear at every depth.
Depth 1 is the direct control; depths 2 and 3 require ordered composition.

T-A renders definitions first. T-B renders the query first and reverses the
definition order. Each semantic task is assigned exactly one template in each
behavioral role; a semantic item is never duplicated merely to obtain template
balance. Every prompt ends in the exact UTF-8 bytes `Answer:` and contains no
answer placeholder, think tag, solved step, queried intermediate, or generated
text.

The four option values are distinct. A/B/C/D and T-A/T-B are exactly balanced
inside every split × family × depth cell. Start, pre-answer intermediate,
final state, and final operator counts differ by at most one. Within each
value of those surface fields, label counts also differ by at most one. Thus a
single registered surface field cannot mechanically reveal the answer label
beyond the unavoidable finite-cell imbalance.

The semantic ID is SHA-256 over canonical family, state space, all operator
definitions, start, operation sequence, sorted option-value set, and ground
truth. It is defined before rendering and excludes template and label mapping.
The four roles must have zero semantic overlap. Prompt overlap must also be
zero against the tracked Phase 1 bank and all vendored official S3 prompts,
both as exact UTF-8 and after NFKC/casefold/whitespace normalization.

Exact bank sizes are:

| Role | Cell size | Cells | Total |
|---|---:|---:|---:|
| development | 64 tasks | 2 families × 3 depths | 384 |
| behavioral confirmation | 256 tasks | 2 × 3 | 1,536 |
| mechanistic development candidates | 256 pairs | 2 × depths 2/3 | 1,024 |
| mechanistic confirmation candidates | 256 pairs | 2 × depths 2/3 | 1,024 |

## Prompt arms

NT is the primary arm. It supplies and generates zero reasoning tokens. A
future execution performs one forward pass and reads only the four registered
continuation logits at the final input position.

PT supplies every correct pre-final intermediate state but not the final state
or option label. WT has identical structure and replaces the last supplied
intermediate with a registered counterfactual whose implied answer is already
one option. ST, at depth 3 only, reverses the two PT states while preserving
the token multiset and trace length. These are external-trace controls, not
natural or model-generated chain of thought.

Stage T must prove separately for all three pinned tokenizers that appending
each literal ` A`, ` B`, ` C`, or ` D` adds exactly one distinct token and
round-trips to the exact prompt. Failure stops as
`BLOCKED_ON_STUDY2_COMMON_OPTION_TOKENIZATION`; no alternative alphabet may be
substituted after inspection.

## Crossed causal pairs

For donor intermediate `m_d`, recipient intermediate `m_r`, donor downstream
map `g_d`, and recipient downstream map `g_r`:

- `a_d = g_d(m_d)`;
- `a_r = g_r(m_r)`;
- `a_x = g_r(m_d)`.

`a_d`, `a_r`, and `a_x` and their option labels are pairwise distinct. Donor,
recipient, and all controls share one four-value option set and exact mapping.
The recombinant target therefore cannot be obtained by copying the donor
answer value or donor option label.

Every unit also contains an exact recipient no-op donor, a semantically
distinct same-intermediate donor, a same-answer/different-intermediate donor,
and one deterministic unrelated donor. Its wrong-position control is the
recipient’s exact `Start:` state-symbol byte span. All control `G_x` values use
the primary pair’s fixed recipient contrast toward `a_x`; a control donor’s own
answer never replaces the target.

Stage T filters only on pinned tokenizer mechanics and frozen hashes, sorts by
pair semantic hash, and selects the first 128 eligible pairs per role × family
× depth. Fewer than 128 in any cell stops before weight loading as
`BLOCKED_ON_STUDY2_MECHANISTIC_TOKEN_SUPPORT`. There is no post-inference
replacement or backfill.

## Behavioral quantities

For option `o`:

`p(o) = exp(logit(o)) / sum_{j in [A,B,C,D]} exp(logit(j))`.

The restricted prediction is the largest of those four logits, with A/B/C/D
used only as the order for exact ties. Correct margin is the correct logit
minus the best incorrect logit. Full-vocabulary ranks and top-1 are mandatory
diagnostics but never select an item or replace the restricted observable.

`NT_PASS(model,family,depth)` requires exactly 256 confirmation rows, complete
finite execution, accuracy ≥ 0.50, Wilson lower 95% > 0.25, paired-bootstrap
lower 95% of mean correct margin > 0, and intact option/template balance.

Trace quantities are:

- `TRACE_GAIN = p_correct(PT) - p_correct(NT)`;
- `WRONG_TRACE_PULL = p_counterfactual_implied(WT) - p_counterfactual_implied(NT)`;
- `SHUFFLE_DAMAGE = p_correct(PT) - p_correct(ST)`.

PT support requires its Wilson lower bound > 0.25, point accuracy ≥ 0.50,
lower95 TRACE_GAIN > 0, and lower95 WRONG_TRACE_PULL > 0; depth 3 additionally
requires lower95 SHUFFLE_DAMAGE > 0. It is an external-trace axis and cannot
open or rescue mechanistic confirmation.

All non-Wilson intervals use 10,000 deterministic paired bootstrap replicates.
Behavior resamples semantic items inside family × depth while retaining model,
template, and arm pairing. Mechanism resamples pairs after equal averaging over
the three window layers. The 2.5th and 97.5th percentiles use linear
interpolation at `(n-1)*p`. A maximum comparator is recomputed inside each
replicate before its quantile.

## Cell and layer selection

Within each family, the target selects depth 3 when it passes NT, otherwise
depth 2 when it passes, otherwise no cell. Control performance, traces, probes,
activations, interventions, and lens outputs cannot enter selection. The same
target-selected cell is used for both controls.

On target mechanistic development only:

`S(layer) = family-equal mean[G_x(layer) - max(G_d(layer), G_x(random donor,layer))]`.

Among contiguous three-layer windows wholly inside layers 9–22, select the
largest mean S and break an exact tie by lowest start layer. Freeze this single
window before confirmation. Both controls use it unchanged, with exact
normalized-depth/round-half-up mapping only if block counts differ. Early
0–8 and motor 23–27 are fixed control bands.

## Lens-independent causal quantities

At the final `Answer:` input position:

- `M_x = logit(a_x) - logit(a_r)`;
- `G_x = M_x(patched donor→recipient) - M_x(clean recipient)`;
- `M_d = logit(a_d) - logit(a_r)`;
- `G_d = M_d(patched donor→recipient) - M_d(clean recipient)`.

Average each pair equally across the frozen three layers before bootstrapping:

- `PATCH_RECOMBINATION = mean G_x`;
- `PATCH_RANDOM_SPECIFICITY = mean [G_x - G_x(random donor)]`;
- `PATCH_ANSWER_COPY_SPECIFICITY = mean [G_x - G_d]`;
- `PATCH_STRUCTURAL_SPECIFICITY = mean G_x - max(mean G_x(no-op), mean G_x(same-intermediate), mean G_x(same-answer))`;
- `PATCH_POSITION_SPECIFICITY = mean [G_x(answer position) - G_x(wrong position)]`;
- `PATCH_BAND_SPECIFICITY = mean G_x(middle) - max(mean G_x(early), mean G_x(motor))`.

`PATCH_PASS(model,family)` requires every one of those six paired-bootstrap
lower 95% bounds to be strictly positive. Recombinant top-1, KL divergence,
and correct-option probability change are secondary outputs only. Alpha-zero
and no-op hooks must reproduce clean logits with max-absolute difference ≤
`1e-5` and the same restricted argmax; failure is operational.

## Cross-template probe

The multinomial ridge probe has fixed L2=1.0. It uses only final-position
activations at the frozen window’s center layer, trains on T-A mechanistic
development, and tests on disjoint T-B mechanistic confirmation. Models and
families are fitted separately. Intermediate class and final option are
balanced so neither predicts the other above registered class-frequency
chance. Controls are five deterministic intermediate-label permutations and
an answer-label probe.

`PROBE_PASS` requires lower95(true accuracy − class-frequency chance) > 0 and
lower95(true accuracy − mean permutation accuracy) > 0. Decodability alone is
never a mechanism, and a probe failure remains visible when patching is
favorable.

## Target-only J-lens axis

Only the target may later open sealed M1200; A600/B600 are fixed replicate
diagnostics and ordinary logit lens is a comparator. Readout also includes
five label permutations and five wrong positions. Report pass@k for
`k=[1,2,5,10,20,50,100]` and normalized trapezoidal AUC against log(k), with
equal family and frozen-layer weighting. Known state digits occur in the
prompt, so raw rank without label/position superiority is prompt echo.

`JREADOUT_PASS` requires lower95(M1200 − logit-lens AUC) > 0 and superiority
to every averaged label and position control. `JCAUSAL_PASS` requires M1200
coordinate-swap recombinant `G_x` to beat logit-lens swaps, five averaged
Gram-matched random pairs, and direct donor-answer-vector swaps. Alpha-zero and
wrong bands remain controls.

The exact states are `STUDY2_JLENS_VALIDATED`, `STUDY2_JLENS_PARTIAL`,
`STUDY2_JLENS_NOT_VALIDATED`, and `STUDY2_JLENS_NOT_ESTIMABLE`. This axis never
promotes or demotes the lens-independent result. Only
`STUDY2_JLENS_VALIDATED` permits a bounded Study 2 J-space statement.

## Closed scientific classification

Internal computation in both families requires selected target cells plus
target NT_PASS, PATCH_PASS, and PROBE_PASS in each. Exactly one family yields a
non-generalized one-family state. A target result is distillation-associated
only when paired lower bounds show stronger aggregate NT behavior and stronger
PATCH_RECOMBINATION than each control, with every hard control intact.

Composite precedence is exact:

1. Incomplete or integrity-failed opened pack → `STUDY2_RESULT_NOT_ESTIMABLE`.
2. Two-family internal support and stronger than both controls → `STUDY2_DISTILLATION_ASSOCIATED_CAUSAL_INTERNAL_REASONING_SUPPORTED`.
3. Two-family internal support without that comparison → `STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_WITHOUT_DISTILLATION_ATTRIBUTION`.
4. Exactly one internally supported family → `STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_ONE_FAMILY_ONLY`.
5. Any compositional NT_PASS but no internally supported family → `STUDY2_BEHAVIOR_ONLY_WITHOUT_CAUSAL_SUPPORT`.
6. No compositional NT_PASS and two-family PT support → `STUDY2_EXTERNAL_TRACE_DEPENDENCE_ONLY`.
7. No compositional NT_PASS and one-family PT support → `STUDY2_EXTERNAL_TRACE_SUPPORT_ONE_FAMILY_ONLY`.
8. No compositional NT/PT support but any depth-1 NT_PASS → `STUDY2_NO_COMPOSITIONAL_BEHAVIORAL_SUPPORT`.
9. No target NT_PASS at any depth and no PT support → `STUDY2_TASK_INTERFACE_UNQUALIFIED`.

Operational states are `BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY`,
`BLOCKED_ON_STUDY2_PREREGISTRATION_INTEGRITY`,
`BLOCKED_ON_STUDY2_MODEL_IDENTITY`,
`BLOCKED_ON_STUDY2_COMMON_OPTION_TOKENIZATION`,
`BLOCKED_ON_STUDY2_MECHANISTIC_TOKEN_SUPPORT`, and
`BLOCKED_ON_STUDY2_EXECUTION`. The last requires one nonempty reason from the
closed JSON enum. No operational blocker is a scientific negative, and no
complete negative may be repaired by another task, template, threshold,
alphabet, layer search, or replacement bank.

## Closed output packs

Stage P task and pair rows contain exactly the fields listed under
`/output_contract`. Every future behavior row binds the model/prompt/token
identity and all four logits. Every patch row binds pair, donor/control,
position, layer, alpha, clean/patched logits, G_x, and G_d. Probe and J-lens
rows preserve every control replicate. Classification rows bind their exact
gate-input hash.

Unknown fields, missing rows, non-finite rows, partial scientific
classifications, and a non-last manifest are forbidden. This makes every
positive and negative branch reconstructible without a semantic parser.

## Bounded review and frozen limitations

The 15 exact questions under `/review` are applied once to one candidate-byte
hash set. All FATAL/MATERIAL findings may be corrected only once in one
consolidated change and verified with the same checklist. Remaining fatal
leakage, noncomputable ground truth, invalid recombination, or a nonclosed truth
table stops as `BLOCKED_ON_STUDY2_PREREGISTRATION_INTEGRITY`.

Interpretation remains bounded because forced-choice logits are not
spontaneous behavior; synthetic tasks do not establish broad reasoning; three
checkpoints do not isolate training causes; controls may differ in tokenizer or
config; supplied traces are external; patching is not a full readable
algorithm; full residuals carry multiple features; probes are not mechanisms;
M1200 is a WikiText-proxy fit; the J-lens subaxis admits only single-token
digits; public banks are not private or researcher-blind; one family cannot
generalize; and no result changes Phase 1.0D or retrospectively validates Study
1.
