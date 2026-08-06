# J-lens S3 validity protocol candidate

## Status and authority

The canonical scientific source of truth is
`docs/jlens_s3_validity_protocol.json`; this document is its explanatory
crosswalk. The closed structural contract is
`docs/jlens_s3_validity_protocol.schema.json`, and the model-free semantic
validator is `src/jspace_observation/jlens_s3_protocol.py`. If prose and JSON
differ, the JSON controls and validation must fail until the prose is corrected.

This is the first complete **design-only candidate**, not a review record,
freeze decision, execution, or scientific result. Its current state is
`NONTERMINAL_CHECKPOINT_JLENS_S3_VALIDITY_PROTOCOL_CANDIDATE_AWAITING_BOUNDED_REVIEW`.
The controlling prompt and still-live Phase 1.0D capacity block are registered
at `$.authority`. The zero-operation declaration and create-only rules are at
`$.artifact_semantics`. No target model, tokenizer, lens, inference, activation,
patching, provider, or GPU operation is licensed by this candidate.

## Public upstream identities

`$.upstream.files` registers the exact vendored public bytes:

| Upstream path | Bytes | SHA-256 | Count and role |
|---|---:|---|---|
| `LICENSE` | 11,358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` | Apache-2.0 text |
| `data/evaluations/README.md` | 3,815 | `e061d9cce02a1cc651d58a81927833b760d3cef65bf4995126ecbe372a0ebe07` | upstream definitions |
| `data/experiments/README.md` | 8,570 | `1d78c702fa22ba610990d545b4c9c96839cc75cd4e451f2badb1cab23e04ad0f` | intervention definitions |
| `data/evaluations/lens-eval-multihop.json` | 21,869 | `50b7e4c9255291c0ca2a8e94615be9f44531fa57bb1a844e4f9616056d987416` | 93 primary readout items |
| `data/evaluations/lens-eval-order-ops.json` | 9,589 | `b203206d16ff628152cc86f3838604e06cb54776f3e14fa1c34f150db8bc7560` | 55 primary readout items |
| `data/experiments/probe-swap.json` | 26,567 | `a0edd27ca23f7b4d0fbe90448c2ddcc7457a3d812121bf024ed12a032ff86796` | 90 separate causal items |

The repository is `https://github.com/anthropics/jacobian-lens.git`, the
immutable commit is `581d398613e5602a5af361e1c34d3a92ea82ba8e`, the
license is Apache-2.0, and the vendored JSON is unmodified
Anthropic-authored synthetic public data. Association, typo, multilingual, and
poetry data are excluded.

The model-free rule at `$.upstream.counterparts` case-folds only the exact raw
triples `(category, intermediate, answer)` and
`(category, swap_to, swap_answer)`. It produces 29 oriented matches and 24
unique unordered pairs. The two primary readout distributions and the causal
benchmark retain separate roles.

## Prospective stage boundary

The four-stage boundary is fully registered at these paths:

* `$.stages.P`: freeze data identities, algorithms, eligibility signals, token
  rules, bands, split, metrics, controls, interventions, bootstrap, floors, and
  gates. This round performs zero target or lens operations.
* `$.stages.E0`: under later authority only, use the pinned tokenizer and one
  clean next-token forward pass per item to resolve mechanical and behavioral
  eligibility, assign the frozen hash split, and write a create-only manifest.
  Seal its bytes and all selection/exclusion counts before computing or opening
  any lens, logit-lens, intervention, or patching output.
* `$.stages.E1`: development proves computations execute and diagnoses
  implementation defects. It cannot change any prompt, synonym, band,
  position, `k`, strength, metric, threshold, gate, or confirmation member.
* `$.stages.E2`: confirmation remains unopened until the executing image/code,
  E0 manifest, and output schemas are sealed. Its pack is all-or-nothing.

There is no backfill and no replacement batch in v1. A floor failure returns
`INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` before any lens output is
opened.

## Fixed execution identities and layers

`$.identities.target_model` fixes
`deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` at revision
`ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`, `torch.float16`,
evaluation mode, `trust_remote_code=false`, `use_cache=false`, 28 blocks, and a
512-token maximum. `$.identities.tokenizer` fixes the same revision, no chat
template, and no truncation. `$.identities.j_lens_code` fixes the official
commit and HF adapter `force_bos=true`.

`$.identities.lens_artifacts` requires full-layer A600 and B600 independent
600-sequence S2 fits and their official `n_prompts`-weighted M1200 merge before
S3 execution. M1200 is the only primary lens. A600 and B600 are mandatory
replication diagnostics; choosing the better replicate is forbidden.

The zero-based bands at `$.layers` are:

* early control 0--8;
* primary middle 9--22;
* motor/output-adjacent control 23--26;
* final target block 27, which is an output control and not a fitted source.

The J-lens target is 27 and fitted source layers are every layer 0--26.
Per-layer results are required, and output cannot move bands or select a best
layer.

## Normalization and token eligibility

The exact text rules are at `$.normalization`:

1. Apply Unicode NFKC.
2. Replace every maximal run of characters for which `str.isspace()` is true
   with one ASCII space, then strip ASCII spaces from both ends. No other
   character is removed or rewritten.
3. A vocabulary decode may have zero or one leading ASCII boundary space
   before the complete surface. Other leading whitespace or two spaces fail.
4. A prompt literal is token-bounded only when adjacent characters, if any,
   are neither Unicode alphanumeric nor underscore.
5. Case-folding is used only for casing-equivalent surface comparisons,
   prompt/target leakage, and the separately specified raw counterpart triples.

`$.eligibility.multihop` permits only each official intermediate and its
casing/boundary equivalents; semantic synonyms are forbidden.

`$.eligibility.order_ops` freezes this complete finite table:

| Key | Permitted complete surfaces |
|---|---|
| 3 | `3`, `three` |
| 4 | `4`, `four` |
| 5 | `5`, `five` |
| 6 | `6`, `six` |
| 7 | `7`, `seven` |
| 8 | `8`, `eight` |
| 9 | `9`, `nine` |
| 10 | `10`, `ten` |
| 11 | `11`, `eleven` |
| 12 | `12`, `twelve` |
| 13 | `13`, `thirteen` |
| 15 | `15`, `fifteen` |
| 16 | `16`, `sixteen` |
| 20 | `20`, `twenty` |
| 24 | `24`, `twenty-four` |
| addition | `+`, `add`, `addition`, `plus` |
| division | `/`, `divide`, `divided`, `division`, division sign U+00F7 |
| mod | `%`, `mod`, `modulo`, `remainder` |
| multiplication | `*`, `multiplication`, `multiply`, `times`, multiplication sign U+00D7 |
| squared | `^2`, `square`, `squared`, superscript two U+00B2 |
| subtraction | `-`, `minus`, `subtract`, `subtraction` |

Runtime thesauri, generation, or growth are forbidden. The official-inclusive
diagnostic is reported but never enters a primary gate.

Under `$.eligibility.primary_leakage_filter`, a candidate is removed when its
complete normalized/case-folded form occurs as a token-bounded prompt literal
or equals the registered target-answer surface. An intermediate with no
remaining single-token surface is mechanically ineligible. Counts are emitted
by item and intermediate for prompt surface, target overlap, and multi-token
failure.

At `$.eligibility.targets`, each primary readout target is only the exact
official target string with casing/boundary equivalents; semantic synonyms and
generated numeric words are forbidden. Causal `answer` and `swap_answer` use
the same exact-official rule. Every required target must have a complete
single-token vocabulary surface.

Mechanical eligibility also requires at least one complete direction token,
input length at most 512 without truncation, and at least one non-final
surface-free control position. Causal items require complete single-token
surfaces for official `intermediate`, `swap_to`, `answer`, and `swap_answer`.

At `$.eligibility.clean_behavior`, the exact raw official prompt bytes are fed
without a chat template or generated chain of thought. Only the final-position
next-token distribution is read. Greedy top-1 must be in the registered target
token set. For causal items the unchanged answer must pass; `swap_answer` is an
intervention target and need not be the unchanged clean answer.

## Frozen split

`$.split` defines canonical item bytes as compact, key-sorted UTF-8 JSON of the
raw upstream item. The order key is
`SHA-256(canonical_item_bytes || UTF-8("jlens-s3-v1-split-2026-08-06"))`,
with item name only as a collision tie-break. After mechanical and clean
eligibility, the first 15 in each distribution are development and all
remaining items are confirmation. No stratification, output-dependent
selection, reshuffle, or backfill is allowed.

Confirmation floors are 20 multihop, 20 order-ops, 50 pooled readout, and 30
causal items.

## Readout validity

All definitions are at `$.readout`. At the final prompt-token position and on
the same captured activations, emit M1200, A600, B600, and ordinary logit-lens
readouts. The logit lens uses the same final norm/unembedding path without
Jacobian transport.

For five label controls, within each distribution and replicate, order items by
the registered SHA-256 construction and cyclically rotate complete labels by a
nonzero offset, guaranteeing a derangement. For five position controls, order
eligible non-final surface-free positions by the registered SHA-256
construction and select the first. Seeds are respectively
`jlens-s3-v1-label-permutation-2026-08-06` and
`jlens-s3-v1-position-shuffle-2026-08-06`. No rank informs selection.

For each intermediate/layer/method, rank is the minimum rank across retained
single-token surfaces. The grid is `[1, 2, 5, 10, 20, 50, 100]`. Within a band,
first minimize rank over its layers. At each `k`, an item's contribution is the
fraction of intermediates with band-minimum rank at most `k`. Its AUC is the
natural-log-`k` trapezoidal area divided by `log(100)`.

The pooled primary statistic is

```
0.5 * mean(multihop confirmation item AUC)
+ 0.5 * mean(order-ops confirmation item AUC)
```

regardless of unequal counts. The primary effect and controls are

```
R = pooled_middle_AUC(M1200) - pooled_middle_AUC(logit_lens)
label_control = M1200 true-label AUC - mean(five label-control AUCs)
position_control = M1200 true-position AUC - mean(five position-control AUCs)
```

Every source layer, band, distribution, replicate lens, and pooled statistic is
reported.

## Causal validity

All causal formulas and controls are fixed at `$.causal`. At source layer
`l`, M1200 vocabulary directions are rows of `D_l = W_U @ J_l`; logit-lens
directions are rows of the actual pinned `W_U`. With
`V = [v_source, v_target]`:

```
c = pinv(V) @ h
h_swap = h + alpha * V @ (swap(c) - c)
```

Algebra is float32; patched residuals return to float16.
`torch.linalg.pinv` uses `rtol=1e-6`, `atol=0.0`. Primary `alpha=1.0`,
secondary `alpha=0.5`, and integrity `alpha=0.0`. Condition numbers are always
reported; inconvenience, ill-conditioning, or non-finite output is never an
exclusion.

The primary hook applies at every prompt position after every middle-band block
in one forward pass and preserves the clean distribution. Early/motor controls
use their fixed bands. Wrong-position controls use only the five E0-sealed
non-final surface-free positions with all middle layers.

Required comparators are M1200 and logit-lens intermediate swaps; five
deterministic Gram-matched random pair swaps; M1200 answer-vector swap; M1200,
logit-lens, and five random ablations; no-op; and wrong-position/early/motor
diagnostics. Random pairs match the complete 2-by-2 Gram matrix within absolute
`1e-9`, use
`jlens-s3-v1-random-direction-2026-08-06`, and are averaged within item.

Ablation is `h - v * dot(v,h) / dot(v,v)`. Report
`KL(p_clean || p_intervened)`, correct-answer logit change, swap-answer
log-prob change, condition number, top-1 success, and

```
G(method) =
  [log p_intervened(swap_answer) - log p_intervened(clean_answer)]
- [log p_clean(swap_answer) - log p_clean(clean_answer)]
```

Multiple answer-token surfaces use log-sum-exp over the complete token set.
The binary outcome is one only when intervened top-1 is in the registered
`swap_answer` set. Primary effects are:

```
C_logit   = success(M1200 intermediate swap) - success(logit-lens swap)
C_random  = success(M1200 intermediate swap) - mean(success(random swaps))
C_leakage = G(M1200 intermediate swap) - G(M1200 answer-vector swap)
```

`C_leakage` is the answer-smuggling control.

## Lens-independent activation patching

`$.patching` admits only model-free unordered counterparts for which both
members pass clean behavior, have equal tokenized length, have distinct
registered clean answers, and are causal-confirmation members. A pair touching
development is diagnostic only. Lens rank and all observed outcomes are
forbidden selectors.

For both orientations, replace one recipient block-output activation at one
position with the donor clean activation and emit all source-layer by position
cells. The patching operation uses no lens direction. Cell recovery is the
baseline-adjusted donor-versus-recipient answer log-odds specified in JSON.
The prospective M1200 rank contrast is the log recipient rank minus log donor
rank of the donor intermediate at the same cell. Spearman correlation with the
true trajectory is compared with the deterministic within-layer
position-shuffled trajectory.

Bootstrap clusters by unordered pair ID. With fewer than 12 eligible
confirmation pairs, report `PATCHING_ALIGNMENT_NOT_ESTIMABLE`. Otherwise,
lower95 of mean true-minus-shuffled correlation above zero is
`PATCHING_ALIGNMENT_SUPPORTED`; the alternative is
`PATCHING_ALIGNMENT_NOT_SUPPORTED`. Patching is supporting evidence only and
never changes the core classification.

## Statistics and classification

`$.statistics` fixes 10,000 deterministic paired replicates using
`jlens-s3-v1-bootstrap-2026-08-06`. Readout resamples item IDs separately
within each distribution and preserves equal 0.5 weighting. Causal resampling
retains paired method rows for each sampled item. Patching cluster-resamples
unordered pair IDs. Token-, row-, intermediate-, and layer-level resampling are
forbidden. The JSON fixes the SHA-256-to-big-endian-integer seed, Python
`random.Random`, sorted distribution order, and `randrange(n)` draw order.
Percentile 95% limits use linear interpolation at sorted zero-based index
`(n-1)*p`.

`$.classification` first applies the four E0 floors. A floor failure returns
`INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY` without opening lens output.
After a complete run, execution integrity requires complete source/model/lens/
layer/row identities, finite primary computations, and alpha-zero/no-op
top-1 equality with clean plus maximum absolute logit difference at most
`1e-5`. Integrity failure is an operational blocker and produces no scientific
classification.

Hard gates require lower95 of label control, position control, and
`C_leakage` each above zero, plus no forbidden primary surface. Core gates are
`READOUT_PASS = lower95(R) > 0` and
`CAUSAL_PASS = lower95(C_logit) > 0 and lower95(C_random) > 0`.

With all integrity preconditions met:

| Hard gates | Readout | Causal | Classification |
|---|---|---|---|
| any fail | either | either | `JLENS_NOT_VALIDATED` |
| all pass | fail | fail | `JLENS_NOT_VALIDATED` |
| all pass | exactly one passes | exactly one passes | `JLENS_PARTIALLY_VALIDATED` |
| all pass | pass | pass | `JLENS_VALIDATED_FOR_RQ2_PILOT` |

Secondary diagnostics cannot override this table.

## Reconstructible output pack

`$.outputs` closes every row schema (`additional_fields=false`) and marks every
table create-only and all-or-nothing:

| JSON path | Reconstruction role |
|---|---|
| `$.outputs.e0_item` | raw prompt/item hashes, exact token IDs, identities, clean top-1, mechanical/behavioral decisions, exclusion counts, split hash and role |
| `$.outputs.e0_surface` | every surface candidate, normalized form, token IDs, leakage decisions, and primary/diagnostic retention |
| `$.outputs.readout_rank` | item/intermediate/lens/control/position/layer minimum vocabulary rank |
| `$.outputs.readout_item` | band, `k`, fractional pass, and item AUC |
| `$.outputs.causal_item` | paired method, draw, alpha, layers/positions, token sets, logit hashes, success, condition, and all registered metrics |
| `$.outputs.causal_direction` | per-layer direction hashes, token identities, full Gram entries, condition number, random draw, and finiteness |
| `$.outputs.patching_cell` | pair orientation, cell, answer IDs, logit hashes, recovery, and true/shuffled rank contrast |
| `$.outputs.patching_alignment` | per-pair true/shuffled Spearman values and difference |
| `$.outputs.bootstrap_replicate` | endpoint, sampling unit, exact draw IDs, and replicate effect |
| `$.outputs.bootstrap_summary` | point estimate, interval, seed, method, and finiteness |
| `$.outputs.classification` | every floor, integrity, hard/core gate, patching status, operational status, and nullable classification |
| `$.outputs.artifact_manifest` | paths, byte hashes, schema/protocol hashes, immutable execution identity, ordering, completeness, and open state |

The E0 and confirmation manifests are written last. A partial confirmation
prefix remains separate and cannot enter a gate or classification.

## Bounded methods review

`$.review` registers exactly one review of the exact candidate hash, at most
one consolidated correction for all FATAL/MATERIAL findings, and a same-
checklist correction verification. It records no review outcome in this
candidate. The six permitted questions are:

1. Are fit, development, confirmation, Phase 1 bank, and official benchmark
   roles non-overlapping where claimed?
2. Can any item, synonym, layer, position, comparator, or exclusion depend on a
   lens, intervention, or confirmation outcome?
3. Are token eligibility, pass@k AUC, bootstrap, coordinate swap, ablation,
   random control, answer-leakage control, patching, and classification exactly
   computable?
4. Do controls distinguish intermediate information from prompt echo,
   final-answer leakage, motor preparation, and arbitrary perturbation?
5. Are development and confirmation operationally separated?
6. Can every result be reconstructed from the planned row-level pack?

Findings must be FATAL, MATERIAL, or MINOR and cite exact file and field
references. Verification may introduce a finding only if the correction itself
created a direct contradiction.

## Roles, limitations, and claims

`$.role_separation` fixes the non-overlap claims among A600/B600 fit sequences,
official benchmarks, Phase 1 bank, development, confirmation, primary readout,
and causal swap. Only vendored bytes, mechanical eligibility, clean greedy
correctness, and the deterministic split hash may select items. Lens/readout/
activation/intervention/patching outcomes, best replicate/layer, and favorable
random controls are forbidden selectors.

The registered limitations are:

* source-paper public items were not authored for this target model;
* clean-correct single-token eligibility is selected-case instrument validation,
  not a population capability estimate;
* multi-token concepts are outside v1;
* public confirmation labels are neither private nor researcher-blind;
* the official repository lacks a complete reusable intervention runtime, so
  actual-path compatibility must be proven before confirmation;
* even later S3 validity would not establish Phase 1.0D headroom, human ground
  truth, hidden reasoning, an internal workspace, or a J-space.

`$.verification` records the ACR-only validation surface and the historical
full-suite reference of 3372 passed, 15 skipped, and only two accepted failures
from `tests/test_parser_v3_seal_job.py`. This document claims only a complete
prospective candidate; it does not claim that the candidate has been reviewed,
frozen, executed, or validated.
