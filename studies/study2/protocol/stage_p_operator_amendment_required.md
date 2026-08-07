# Study 2 Stage P operator amendment required

## Coordination state

`OPERATOR_AMENDMENT_REQUIRED`

This is an operator-directed pre-review gap record. It is **not** the one
bounded methods review in Stage P authority Section 17. The canonical protocol
remains `CANDIDATE_AWAITING_REVIEW`, its review allowance remains `UNSPENT`,
and no freeze decision exists.

Gap-analysis input identity:

- commit: `3dafd7c7cc730821b365c12599a51c44fcb11420`;
- tree: `384d12fc366a6cf136e56b45045ebab12d09bb39`;
- Stage P authority: 53,018 bytes, SHA-256
  `1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37`;
- sensitivity QuickRun: `cmc1`, `Succeeded`, model-free CPU only;
- sensitivity output:
  [`stage_p_power_sensitivity.json`](stage_p_power_sensitivity.json), SHA-256
  `ec0b80f2bc5eca6aa46aba16f1e11f9c2fcda5f78f86ce46ef1b62c4e5879451`.

The authority prompt and bootstrap receipt remain byte-unchanged. No content
below is adopted into the frozen stage machine unless the operator issues a
new authority.

## Advisory input boundary

Any Claude-produced Study 1 failure analysis is classified only as
`ADVISORY_POST_HOC_METHODS_INPUT`. No numerical assertion from such an analysis
is imported here. It is not Study 2 scientific evidence, receives no `EV`
identifier, does not alter Study 1's
`INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` terminal state, and cannot be
restated as fact without verification against a sealed artifact.

## 1. Domain and output-interface gap check

The candidate already removes the two identified Study 1 interface
mismatches:

1. `permutation_chain` and `affine_mod10` are programmatically closed synthetic
   domains. Every primitive, intermediate, final answer, distractor, and
   counterfactual is mechanically reconstructible; no world-knowledge recall is
   required.
2. NT reads a prospectively fixed four-option logit vector after one forward
   pass and generates zero tokens. It does not gate on raw full-vocabulary
   top-1 formatting.

No implementation contradiction was found that would justify reintroducing
natural-language knowledge questions, generated answers, or chat-template
selection. Those additions remain outside protocol v1.

## 2. Power and sensitivity

The exact calculations and all grid points are in
`stage_p_power_sensitivity.json` and are recomputable with
`scripts/analyze_study2_stage_p_sensitivity.py`. They are design sensitivity,
not evidence and not authority to change a sample size or threshold.

### Exact binomial sensitivity against chance 0.25

The table uses the smallest `k` with exact one-sided
`P[X >= k | p=0.25] <= alpha`.

| n | alpha | critical k | accuracy | Power p=.30 | p=.35 | p=.40 | p=.50 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | .050 | 23 | .359375 | .183066 | .484301 | .784464 | .991571 |
| 64 | .025 | 24 | .375000 | .121506 | .382088 | .701656 | .983617 |
| 256 | .050 | 77 | .300781 | .512685 | .958273 | .999610 | ~1.000000 |
| 256 | .025 | 79 | .308594 | .405014 | .928217 | .999015 | ~1.000000 |

The `n=64` development cells are therefore weak for small departures from
chance and useful mainly for implementation diagnosis or large interface
effects. The `n=256` confirmation cells have high exact-binomial power by true
accuracy .35, but the registered scientific gate is more demanding than this
single accuracy calculation.

### Probability of clearing the observed accuracy floor

For `X ~ Binomial(256,p)`, the accuracy component `X >= 128` has:

| True p | P[X >= 128] |
|---:|---:|
| .40 | .000754 |
| .45 | .061409 |
| .50 | .524910 |
| .55 | .952354 |
| .60 | .999514 |

These are upper bounds on full `NT_PASS` probability because execution
integrity, balance, Wilson lower95 above .25, and margin bootstrap lower95 above
zero must also pass.

### Paired target-control differences

For 256 paired items, the table conditions on a fixed discordant-pair count and
uses an exact sign/McNemar calculation at one-sided alpha .025. The minimum
detectable marginal accuracy difference is
`q * (2*pi_target_win - 1)`.

| Discordant proportion | 80% power MDE | 90% power MDE |
|---:|---:|---:|
| .101563 | .056641 | .063320 |
| .199219 | .076231 | .087141 |
| .300781 | .097482 | .111383 |
| .398438 | .113747 | .130058 |
| .500000 | .125751 | .144283 |

Each target-control comparison has this marginal sensitivity separately.
Requiring superiority to both controls is a conjunction; its joint power cannot
be recovered from either marginal table without their dependence structure.

### Mechanistic pairs

For `n=128` pairs, a normal approximation gives minimum standardized paired
effects of .247627 at 80% power and .286512 at 90% power for one-sided alpha
.025. At alpha .05 the corresponding values are .219775 and .258660. Actual
paired-bootstrap sensitivity depends on the finite effect distribution,
outliers, and correlation across the six registered patch contrasts.

### Conjunctive interpretation

Individual power calculations are not composite power. Requiring behavior,
margin, six patch contrasts, probe contrasts, hard controls, two families, and
two checkpoint comparisons to pass can sharply reduce overall power. A
conjunction does not create a union-style multiplicity inflation, but a
negative composite may result from any one weak component. No joint power
claim is available without a registered joint data-generating model.

## 3. Common-support design

The existing common-support rule is retained without amendment:

- Stage T may use only mechanics from all three fixed tokenizers and frozen
  prompt/pair hashes.
- It selects the first 128 mechanically eligible pairs per frozen cell by
  frozen hash order.
- Target, lineage base, and instruction control run the same tasks, target-
  defined cells, selected pairs, and target-defined window.
- No correctness, logit, activation, probe, patch, or lens outcome may enter
  pair eligibility.
- There is no behaviorally correct intersection and no row is removed because
  a control performs poorly.

## 4. MATERIAL pre-review risk

`MATERIAL`: the current B-D stage is authorized only to verify implementation.
Its data cannot change a task, template, arm, threshold, option surface, sample
size, metric, control, or conclusion rule. It therefore is not a disposable
empirical feasibility measurement that can stop an unsuitable scientific
interface before confirmation.

This classification is an operator-directed pre-review finding, not the formal
Section 17 review and not a use of its allowance.

### Minimal amendment invariants

Any amendment must:

- keep Stage P tokenizer, model, lens, activation, provider, and GPU operations
  at zero;
- run only after Stage T seals identity and token mechanics and before any B-C
  object is opened;
- use the fixed development split while confirmation remains unopened;
- run every fixed development row for all three models, without selecting a
  favorable model, family, task, template, or item;
- use one predeclared gate and no result-dependent fallback;
- on failure, close that protocol version and require a new version, new
  authority, and new seeds;
- forbid same-version backfill, replacement tasks, threshold changes, or
  favorable-model selection.

### Candidate Gate A: family-composition qualification

Decision input is target NT only; both controls still run the identical
development pack but cannot affect the decision. Within each family, pool the
fixed depth-2 and depth-3 development cells (`n=128`) and require a predeclared
one-sided exact-binomial result against .25 at alpha .025 in **both** families,
plus complete finite execution and intact balance.

Consequences:

- directly checks compositional interface feasibility in both domains;
- uses no cell winner or favorable control;
- is conservative because two family gates are conjunctive;
- conditions later confirmation on favorable target development and therefore
  creates winner's-curse and protocol-selection bias that must be disclosed.

### Candidate Gate B: global interface qualification

Decision input is target NT only; controls again run but cannot decide the
gate. Pool all six fixed target development cells (`n=384`) and require one
predeclared one-sided exact-binomial result against .25 at alpha .025, complete
finite execution, and all balance invariants. No family or depth may be dropped.

Consequences:

- has one aggregate test and higher power than Gate A;
- reduces familywise threshold multiplicity and prohibits cell selection;
- can be carried by depth-1 direct tasks or one stronger family, so it is a
  weaker check of compositional feasibility;
- still conditions confirmation on favorable target development and therefore
  retains selection bias.

Neither gate is adopted. The operator must choose a new authority or explicitly
retain the current no-feasibility-gate state machine.

## 5. Non-scientific execution reliability contract

Future authorized execution should add the following operational contract
without changing scientific denominators:

1. Seal an immutable shard manifest before dispatch, binding protocol, bank,
   model/config/tokenizer, source commit/tree, image digest, row IDs, and shard
   membership.
2. Derive an idempotent attempt ID from the immutable run, shard, image, and
   bounded attempt ordinal. Replaying an existing successful attempt is a
   no-op, not a duplicate contribution.
3. Complete a capacity preflight before opening the run and distinguish
   capacity refusal from scientific output.
4. Permit only a fixed finite retry count for registered infrastructure reason
   codes; scientific values cannot trigger retry.
5. Write create-only checkpoints that bind the exact processed prefix. Resume
   only after rehashing the checkpoint and reject any repeated row.
6. Isolate a failed shard; never silently drop it or shrink a denominator.
7. Reject duplicate IDs, missing IDs, out-of-shard IDs, non-finite rows, and
   source/image mismatches during merge.
8. Merge only a complete registered row universe and write the manifest last.
9. Classify exhausted infrastructure failure as operationally not estimable,
   never as a scientific negative.

GPU cost after Stage T is not a primary design constraint. A later authority
may not reduce samples, registered repetitions, or critical controls to save
GPU cost. Stage P itself remains at zero GPU Jobs and zero model operations.

## 6. J-lens four-scale observation

The protected Study 1 handoff reports a four-scale engineering convergence
trajectory. Study 2 registers that only as
`EXPLORATORY_METHODS_OBSERVATION_AWAITING_CONTROLLED_VALIDATION`.

It is not a publication claim, not a novelty claim, and not evidence that
M1200 is valid. No change in a fitted quantity may be causally attributed to
`max_seq_len=128` without a controlled repeat, uncertainty estimate, and
independent literature review. The observation cannot select or alter a primary
task, cell, pair, layer, window, or causal metric.

## Authority conflict and required operator action

The requested feasibility gate conflicts with the sealed authority in four
exact ways:

1. Section 11 says to freeze the P -> T -> B-D -> B-C -> M-D -> M-C state
   machine exactly; a new post-T/pre-B-C decision node changes it.
2. Section 11 defines B-D as implementation verification and forbids
   development results from changing frozen scientific choices.
3. Sections 12 and 16 define confirmation and terminal truth tables without a
   feasibility-closure branch.
4. Section 17 allows one review/correction cycle, not an unregistered empirical
   redesign loop.

Therefore the 53,018-byte authority remains unchanged, neither candidate gate
is incorporated, the formal review does not start, and freeze is prohibited
until the operator either:

- explicitly retains the existing exact state machine; or
- issues a new authority that selects and fully registers one amendment.
