# Study 3R protocol candidate v1 — single independent focused methods review

> **Verdict:** `STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION`
>
> Four BLOCKING findings. Under the review authority's verdict rules, one or
> more BLOCKING findings is terminal and no execution is authorized. No
> repair, amendment, second authoring session or model execution follows from
> this review.

Authority:
[`studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md`](../prompts/study3r_protocol_v1_single_focused_review_authority.md)

Machine-readable disposition:
[`study3r_protocol_v1_single_focused_review.json`](study3r_protocol_v1_single_focused_review.json)

## 1. Binding reviewed object and starting state

Every starting-state condition in section 0 of the review authority was
verified before any byte was written.

| condition | required | observed | verdict |
| --- | --- | --- | --- |
| `HEAD` | `da1ea31b51b784cb1ab3529f9de2f6ee27c853dd` | `da1ea31b51b784cb1ab3529f9de2f6ee27c853dd` | pass |
| fetched `origin/main` | equals `HEAD` | equals `HEAD` | pass |
| tree | `c1de862ba3782b4930191a51df8790bb4279344c` | `c1de862ba3782b4930191a51df8790bb4279344c` | pass |
| worktree | clean | clean | pass |
| commits from `cd9c0af…` | five, strictly linear | five, strictly linear | pass |
| first commit | `5a80c67…`, authority alone | `5a80c67…`, one file, 440 lines | pass |
| merges / rebases / rewrites | zero | zero | pass |
| protected blobs | unchanged | unchanged | pass |
| evidence ledger | ends at `EV-0016` | ends at `EV-0016`, 17 lines | pass |
| execution-authorized fields | all false | `frozen`, `execution_authorized`, `formal_execution_authorized`, pointer `execution_authorized`, pointer `frozen` all false | pass |

The five authoring commits are `5a80c67 → c650e45 → 8d59b06 → a6ea96f →
da1ea31`, each with exactly one parent.

## 2. Independence

This reviewer did not draft or materially edit the Study 3R authority,
protocol, schemas, registry, state machine, task generators, statistical
calculators, tokenizer probe, manifest generator or candidate tests. The
independent recalculation imports none of `study3r_protocol_build.py`,
`study3r_design_statistics.py`, `study3r_independent_recalculation.py` or any
task-bank production calculator, and the tokenizer reconstruction does not
import `study3r_tokenizer_probe.py`. Every rendering rule used by the
reconstruction was re-typed from the frozen registry text so that a
disagreement would surface rather than be absorbed.

The review authority was saved byte-for-byte and published **alone** as the
first commit after `da1ea31…`, before any finding, calculation, mutation or
report existed.

| field | value |
| --- | --- |
| path | `studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md` |
| byte length | 19,227 |
| SHA-256 | `ffa051d5994c9d41435c6f5bc5b693cdfab6c843b604c063cfe4def286b5a882` |
| Git blob | `046774722b1c90d70a4dfd271adb45601b84b099` |
| commit | `9952263865694dfafea4f61643e596e193edf4b4` |
| tree | `e67731b37450c56a0cfe5e412ed295cb744a7f78` |
| parent | `da1ea31b51b784cb1ab3529f9de2f6ee27c853dd` |

## 3. Findings

| id | severity | title |
| --- | --- | --- |
| `F-01` | **BLOCKING** | No registered depth-2/depth-3 allocation rule for any mixed bank |
| `F-02` | **BLOCKING** | The pooled depth cell lets depth-3 performance be masked to chance or to zero |
| `F-03` | **BLOCKING** | Prequalification gates are globally conjunctive, so one candidate's failure ends the study |
| `F-04` | **BLOCKING** | The generated-CoT route freezes no decoding contract beyond `do_sample` and `k` |
| `F-05` | MAJOR | `d0_discriminant_position` is a single fixture constant, not a per-item rule |
| `F-06` | MAJOR | `W2_ROLE_CANONICAL` injects a forced reasoning closure absent from the authoritative Markdown |
| `F-07` | MAJOR | Registered worst-case token bounds are fixture-length point estimates |
| `F-08` | MAJOR | Item-disjointness and bank realization have no registered orchestration |
| `F-09` | MAJOR | Seven coordinated decision-bearing mutations survive the semantic validator |
| `F-10` | MINOR | The governance policing test widened its own scope predicates |
| `F-11` | MINOR | `.gitattributes` is neither a manifest entry nor a declared exclusion |

No confirmed decision-bearing defect has been downgraded to a limitation.

### F-01 — BLOCKING — no registered depth-2/depth-3 allocation rule

Four registered banks declare `family_mix = ["D2", "D3"]`:
`D2_D3_CEILING_BANK` (n = 128), `D2_D3_DEVELOPMENT_BANK` (n = 74),
`D2_D3_CONFIRMATION_BANK` (n = 74) and `D2_D3_TARGET_BANK` (n = 74). For each
the candidate registers only the bank identifier, the family list and `n`.

No allocation constant, proportion, per-depth count, per-depth minimum or
balancing rule exists anywhere in `study3r_protocol_v1.json`, its schema,
`study3r_rendering_registry_v1.json`, `study3r_atomic_cell_census_v1.json`,
`study3r_design_statistics.py`, `study3r_design_statistics_tables.json` or
`study3r_task_generators_v1.py`.

The generator makes the omission concrete. `realize_bank(bank_id, family,
size, ...)` takes **one** `family` and calls `generate_item(family, rng)` for
every item, so it cannot realize a two-family bank at all. The candidate's own
test suite calls it as
`tasks.realize_bank("D2_D3_TARGET_BANK", "D2", 4)` — a mixed bank realized as
pure depth-2. No registered caller mixes the two depths, and no rule states
what a future runner should do.

This is decision-bearing under the authority's own definition: it changes the
task population and the atomic-cell content, and two different operators
executing the frozen protocol can produce banks that differ in depth
composition from 0 % to 100 % depth-3 while both remaining compliant.

### F-02 — BLOCKING — depth-3 performance can be masked to chance or to zero

Because depth is not a gate-bearing factor, each mixed bank is a single atomic
cell and one pooled integer decides it. The exact integer arithmetic below was
recomputed independently at the registered `n` and pass boundary; `alpha_per_cell
= 1/1160` throughout.

`G09_RT_E0_QUALIFICATION`, `G07_RPB_DEVELOPMENT`, `G08_RPB_CONFIRMATION` —
`n = 74`, pass if `k ≥ 51`:

| depth-2 items | depth-3 items | minimum depth-3 correct to pass with perfect depth-2 | implied depth-3 accuracy | exact one-sided p vs chance `1/4` | beats chance at `1/1160`? | reaches the `1/2` floor? |
| --- | --- | --- | --- | --- | --- | --- |
| 51 | 23 | 0 | `0/23` | 1.000000000000 | no | no |
| 54 | 20 | 0 | `0/20` | 1.000000000000 | no | no |
| 44 | 30 | 7 | `7/30` | 0.651945710976 | no | no |
| 37 | 37 | 14 | `14/37` | 0.057656922510 | no | no |

The balanced 37/37 allocation — the most defensible reading of "depth-2 and
depth-3" — passes the primary headline gate with a depth-3 record of 14/37
(0.378), which is *below the registered `1/2` competence floor* and *not
distinguishable from the 1/4 chance level* at the registered per-cell alpha.
For any allocation with 23 or fewer depth-3 items, a checkpoint passes with
**zero** depth-3 items correct. Up to `n_d3 = 44`, the minimal passing depth-3
record fails to beat chance at `alpha_per_cell`.

`G01_COT_CEILING` — `n = 128`, pass if `k ≥ 111`: any allocation with 17 or
fewer depth-3 items passes with zero depth-3 correct; up to `n_d3 = 34` the
minimal passing depth-3 record does not beat chance.

The candidate makes depth-3 competence part of its construct: the charter
authorizes "depth-2 and depth-3 compositional operations for RP-B qualification
and RT behavioral measurement", the generator registers `D3` with
`FAMILY_DEPTH["D3"] = 3` and a distinct three-operation stem template, and four
banks carry `D3` in their family mix. A gate that can be cleared while depth-3
performance is at chance, or at zero, does not support that claim.

The same pooling argument applies to the operation family: `ADD`, `SUB` and
`MUL` are registered as an ontology but are not gate-bearing factors, so
operation-specific failure is maskable by the same arithmetic.

**Counterfactual diagnostic (not a repair, not a proposed design).** Making
depth a gate-bearing factor in the four mixed banks yields `m_max = 76`,
`alpha_per_cell = 1/1520` and 10,404 scheduled evaluations against the
registered 58 / `1/1160` / 8,108. Per-gate: `G01` n = 130, k ≥ 113;
`G02`–`G04` n = 131, k ≥ 128; `G05` n = 431, k ≤ 119; `G06`–`G09` n = 77,
k ≥ 53. This is reported only to quantify the defect.

### F-03 — BLOCKING — prequalification gates are globally conjunctive

The state machine was reconstructed independently, without the production
builder. `S03`, `S04`, `S05` and `S06` each carry a single failure outcome
whose predicate is *at least one cell*:

| state | pass outcome | failure outcome | terminal |
| --- | --- | --- | --- |
| `S03_GENERATED_COT_CEILING` | `every_checkpoint_cell_passed` | `at_least_one_checkpoint_cell_failed` | `T03_COT_CEILING_FAILED` |
| `S04_COMPETENCE_CONTROLS` | `every_control_cell_passed` | `at_least_one_control_cell_failed` | `T04_COMPETENCE_CONTROL_FAILED` |
| `S05_NEGATIVE_CONTROL` | `every_negative_control_cell_passed` | `at_least_one_negative_control_cell_failed` | `T05_NEGATIVE_CONTROL_FAILED` |
| `S06_TWO_WRAPPER_JOINT_ADEQUACY` | `both_arms_cleared_the_floor_for_every_checkpoint` | `at_least_one_arm_failed_for_at_least_one_checkpoint` | `T06_WRAPPER_ADEQUACY_FAILED` |

Those gates span every checkpoint role, RT and all three RP-B candidates:
4 + 24 + 8 + 8 = **44 of the 58 atomic cells** must pass before `S07` — the
first state in which any ladder scanning happens — is reachable at all.

The consequences follow mechanically:

* a single `RP_B1` cell failing at `S03`, `S04`, `S05` or `S06` sends the study
  to a global terminal and `RP_B2` and `RP_B3` are never evaluated;
* likewise an `RP_B2` failure blocks `RP_B3`;
* the "first-confirmed-pass" ladder is therefore conditional on *every* ladder
  member already having passed *every* prequalification gate;
* candidate-specific ineligibility is promoted to study-wide failure.

This contradicts the candidate's own registered language. `study3r_protocol_v1.md`
states "The RP-B ladder scans past failures until the first confirmed pass";
the charter registers `S3R-D05` (first-confirmed-pass selection) and `S3R-D11`
(the CoT ceiling is a *per-checkpoint* execution precondition); and the
authoring authority requires a bounded `no qualified reference` interpretation
plus a per-checkpoint CoT precondition. A per-checkpoint precondition that
terminates the whole study when one checkpoint fails is not per-checkpoint.

No defensible charter-consistent reason for global scoping is given anywhere in
the bundle. The correct scopes are also not separated: an `RT` failure at
`S03`–`S06` and an `RP_B*` failure at the same states share one terminal, even
though `RT` is the target and the `RP_B*` are interchangeable ladder members
whose whole purpose is to be scanned past.

Under section 8 of the review authority — "If candidate-specific ineligibility
should continue to the next registered candidate but the state machine stops
globally, classify BLOCKING" — this is BLOCKING.

### F-04 — BLOCKING — the generated-CoT route freezes no decoding contract

The registered `generated_cot_ceiling` estimand and the per-checkpoint
`cot_route` record contain exactly: `do_sample = false`, `k = 1`,
`parser_id`, `parser_regex`, `unparseable_output`, `task_population`,
`statistical_unit`, `granularity`, the canonical wrapper bytes, and per-checkpoint
`context_window_tokens`, `max_new_tokens_per_item`, `worst_case_sequence_tokens`
and `worst_case_total_tokens`.

A repository-wide search of the entire Study 3R bundle finds **no occurrence**
of `temperature`, `top_p`, `top_k`, `num_beams`, `padding_side`, `batch_size`,
`device_map`, `dtype`, `torch_dtype`, `quantization`, `bfloat16`, `float16` or
`attn_implementation` in the CoT route. The only `num_beams` and `temperature`
in the bundle belong to the *E0* decoding block. Nothing pins a framework or
library version as part of the execution contract, no seed semantics are given
for the generation route, no aggregation rule is stated for `k = 1`, and no
EOS/stop-token set is registered for the CoT route.

Section 7 of the review authority forbids inferring these from a library
default unless the protocol explicitly pins the library version and the default
as part of the contract. It does not. Each unpinned field can change the
rendered continuation and therefore the parsed final line, which changes the
pass/fail decision of `G01_COT_CEILING`, which is a precondition for every
later state. Sampling parameters left free are decision-bearing even when
`do_sample = false`, because a future runner that sets `do_sample = true`, or a
library whose default changes, is not detectably out of contract.

The parser itself is sound in isolation: `P1_FINAL_ANSWER_LAST_LINE` with
`^Final answer: ([ABCD])$` is unambiguous over multiline output provided the
runner applies it in multiline mode and takes the last match; but the protocol
registers neither the regex flags nor the "last match" rule, so two runners can
legitimately parse a two-`Final answer:` output differently. That aggravates
rather than causes this finding.

### F-05 — MAJOR — `d0_discriminant_position` is a fixture constant

The registry stores one integer per checkpoint-arm: 57 for `W1_RAW_DIRECT` and
63 for `W2_ROLE_CANONICAL`, for all four checkpoints. These are the token
lengths of the *single* canonical depth-2 fixture.

The independent reconstruction rendered 36 synthetic non-scientific surfaces per
checkpoint (6 registered fixtures plus a 30-item adversarial grid covering
one-, two- and three-digit operands and results, every registered operation,
depths 1/2/3, every option-label position and newline/spacing boundaries). The
observed discriminant positions are:

| arm | registered | observed range over 36 renderings | distinct values |
| --- | --- | --- | --- |
| `W1_RAW_DIRECT` | 57 | 49 – 65 | 13 |
| `W2_ROLE_CANONICAL` | 63 | 55 – 71 | 13 |

Restricting to the depth-2/depth-3 families that actually populate the E0
banks still gives 53 – 65 and 59 – 71 respectively.

So `57/63` is a fixture-specific recorded value, not an absolute position valid
for variable-length prompts. That would be harmless if the protocol registered
a per-item derivation rule. It does not: the rule "the discriminant position
*is* the first position after the common prefix" appears only as a source
comment in `study3r_protocol_build.py`, and the only registered normative field
is `discriminant_position_offset = 0`.

This is classified MAJOR rather than BLOCKING because D0 is registered as a
conditional diagnostic that is explicitly never a gate, never an RP-B gate and
never qualifies a candidate, and because it registers no task population, no
`n` and no statistical cell — so no registered decision can move. It is
nonetheless a real reproducibility defect: as written, a runner that reads
`d0_discriminant_position = 57` literally would score the wrong position on
every item whose rendering is not the canonical fixture.

### F-06 — MAJOR — the role-canonical arm carries a forced reasoning closure

The native DeepSeek-R1-Distill chat template (SHA-256
`56a1447ad31926fdc21fb07e56e5642bd9c850c4f52d8c8af7bbe5f079a84f5f`, identical
across all four revisions) opens a reasoning span with `<think>\n` at the end
of the generation prompt and never emits `</think>` itself. The independent
reconstruction confirms both facts directly.

`W2_ROLE_CANONICAL` renders as: chat-template generation prompt +
`</think>\n\n` + `Answer:\n`. The `</think>\n\n` bytes are supplied by the
protocol, not by the checkpoint's template.

The candidate does register this: `frozen_reasoning_closure = "</think>\n\n"`
and `reasoning_span_opened_by_template = true` appear in the registry, the
surfaces record and the protocol JSON. That is accurate representation, and it
is why this is MAJOR and not BLOCKING.

What is not accurate is the authoritative human-readable rendering. The
`W2_ROLE_CANONICAL` row of `study3r_protocol_v1.md` §3 lists only envelope,
checkpoint-specificity, message roles and few-shot count, and states that "the
single field that differs between the matched arms is `envelope`". The forced
closure never appears in the Markdown. A reader of the authoritative Markdown
would conclude the second arm is the checkpoint's unmodified canonical route.
It is not: it is a role-canonical envelope with a forced reasoning closure, and
suppressing a reasoning span that the checkpoint's own template opens is an
additional intervention on a reasoning-distilled model.

Verified: apart from the envelope (and the closure inside it), the two arms
share identical item-body bytes, identical answer cue, zero few-shot examples,
and identical A/B/C/D discriminant token IDs `{A:32, B:33, C:34, D:35}`.

### F-07 — MAJOR — registered token bounds are point estimates

`worst_case_total_generated_and_prompt_tokens = 470952` equals exactly
`7596 × 62`, where 7,596 is the E0 scheduled-evaluation count and 62 is the
canonical fixture's prompt-plus-generation length. The CoT
`worst_case_sequence_tokens = 4184` equals `88 + 4096`, where 88 is the
canonical fixture's CoT prompt length.

Observed lengths over the adversarial grid are 49–65 (`W1`), 55–71 (`W2`) and
80–96 (CoT) tokens. The registered figures are therefore mean-length point
estimates presented as worst cases; the true worst case is larger. No
registered decision moves — the 131,072-token context window is not remotely
threatened — so this is MAJOR, and it compounds F-04's absence of a real
compute ceiling.

### F-08 — MAJOR — item-disjointness has no registered orchestration

The protocol declares nine item-disjoint bank pairs and defines an item key as
`SHA-256("family|stem|opt_a|opt_b|opt_c|opt_d")`. `realize_bank` accepts
`excluded_item_keys` and accumulates keys within one bank, but no registered
caller, order or exclusion-chaining rule exists anywhere in the bundle, so the
declared cross-bank disjointness is not mechanically enforced by anything the
protocol freezes. Combined with F-01 this means no registered procedure can
produce the nine declared pairs at all.

Separately, the bank generator is `random.Random` seeded from a SHA-256 digest.
That is deterministic for a fixed CPython version, but the bundle pins no
Python version and no library version, so the "deterministic PRNG" claim is not
anchored. Verified here on CPython 3.13.15.

### F-09 — MAJOR — seven coordinated decision-bearing mutations survive

49 mutations were executed in temporary staged trees (the repository worktree
was never mutated): the candidate's 24 registered mutations plus 25 independent
adversarial mutations covering every category named in section 12 of the review
authority. Each coordinated mutation edits a generator, rebuilds the bundle
through `study3r_protocol_build.py` → `study3r_independent_recalculation.py` →
`study3r_manifest.py`, and then runs the candidate's own
`validate_bundle`.

* All **24 registered mutations were killed**. The candidate's claim of zero
  survivors over its own registered set reproduces exactly.
* **42 of 49** total mutations were killed.
* **7 coordinated mutations survived**, each producing a changed committed
  bundle that `validate_bundle` accepted:

| mutation | category | artifacts changed |
| --- | --- | --- |
| `adv_d2_d3_family_mix_drops_depth_three` | D2/D3 allocation | protocol JSON, protocol MD, manifest |
| `adv_d2_d3_ceiling_mix_drops_depth_three` | D2/D3 allocation | protocol JSON, protocol MD, manifest |
| `adv_d3_family_depth_relabelled` | D2/D3 allocation | protocol JSON, manifest |
| `adv_forced_reasoning_closure_removed` | forced `</think>` closure | protocol schema, registry schema, manifest |
| `adv_forced_reasoning_closure_changed` | forced `</think>` closure | protocol schema, registry schema, manifest |
| `adv_surfaces_closure_emptied_while_rendered_bytes_unchanged` | forced `</think>` closure | protocol JSON, registry JSON, manifest |
| `adv_cot_parser_regex_unanchored` | parser anchoring | protocol JSON, manifest |

Three consequences are worth stating precisely.

1. Depth-3 can be **removed entirely** from the target and ceiling banks, and
   the depth of the `D3` family can be **relabelled from 3 to 2**, and the
   validator accepts the result. This is the validation-side mirror of F-01.
2. The forced reasoning closure can be emptied or shortened. The two
   generator-side variants leave the registry *data* unchanged while rewriting
   the registry *schema* enum, so the committed data no longer validates
   against its own committed schema — a contradiction `validate_bundle` cannot
   see, because it performs no JSON-schema validation. The surfaces-side
   variant is worse: it empties the closure in the registry data while
   `rendered_utf8_bytes = 231` and `rendered_token_count = 63` stay at their
   with-closure values, so the registered description of the model input
   contradicts the registered rendered length, and nothing objects.
3. The CoT parser regex can be **unanchored** from `^…$` to a bare substring
   match, changing which outputs parse, with no objection.

This is MAJOR rather than BLOCKING on its own terms: it demonstrates that the
validator does not bind these values, and the underlying design defects it
exposes are already carried as BLOCKING by F-01, F-02 and F-04. It is recorded
separately because the authority requires every survivor to be reported and
because the candidate's disclosure claims a survivor count of zero, which is
true only over the candidate's own registered mutation set.

### F-10 — MINOR — the governance test widened its own scope predicates

The authoring session modified `tests/test_study3r_operator_governance.py`,
converting two exact-set assertions into set-plus-namespace-prefix assertions.
The before/after admitted path sets differ by: the prefix `studies/study3r/`,
plus the exact paths `tests/test_study3r_protocol_v1.py`, `.gitattributes`,
`studies/study3r/README.md` and the governance module itself.

Assessed against the three possibilities the authority names: the namespace
prefix merely advances the previously declared Study 3R namespace
(`charter["study_identity"]["namespace"] == "studies/study3r/"`), and
`tests/test_study3r_protocol_v1.py` is named by path in the authoring
authority §9. Those two are pre-declared, not post-hoc. `.gitattributes` and
the module's self-permission were **not** pre-declared and are a genuine
widening.

It is MINOR because the widening is demonstrated not to move any decision:
every per-path protected-blob assertion in the module is unchanged, no
reviewed, rejected-candidate, independent-review or protected historical path
lies inside `studies/study3r/`, and an independent blob comparison against the
reviewed commit `459d0024…` confirms every rejected-candidate and protected
historical path still carries its registered blob. (The eight v0.7
*independent-review* artifacts do differ from `459d0024…` because they were
created after it, by the v0.7 review itself; they are unchanged relative to the
v0.7 review head.) Recording it as MINOR rather than accepting "no assertion
was weakened" is the point: the predicates *were* weakened, and the reason it
does not matter had to be demonstrated rather than assumed.

### F-11 — MINOR — `.gitattributes` is neither bound nor excluded

The manifest asserts `every_entry_is_lf_only = true`. That property is produced
and preserved by `.gitattributes` rules covering `studies/study3r/*` and
`tests/test_study3r_protocol_v1.py`. `.gitattributes` appears in none of the
27 manifest entries, the four deferred exclusions or the single self-exclusion,
even though the review authority §13 lists it explicitly as a path to bind
"where it affects byte reproduction". Its content is bound by the Git tree, so
no decision can move; this is presentation-level provenance only.

## 4. Independent verification results

### 4.1 Tokenizer and rendering reconstruction

Reconstructed from the four registered immutable revisions with
`trust_remote_code=false`, without importing the candidate probe.

| result | value |
| --- | --- |
| revisions resolving to themselves | 4 / 4 |
| acquired file hashes matching the acquisition record | 16 / 16 |
| chat-template SHA-256 matching the registered value | 4 / 4 |
| A/B/C/D token IDs | `{A:32, B:33, C:34, D:35}` on all four |
| longest legal answer surface | 1 token; `max_new_tokens` recomputes to 2 |
| `add_special_tokens=True` prepends | nothing |
| canonical fixture `W1` | 157 bytes / 57 tokens / SHA-256 and full ID list identical |
| canonical fixture `W2` | 231 bytes / 63 tokens / SHA-256 and full ID list identical |
| distinct functional-equivalence strata over all 36 surfaces × both arms | **1** |
| weight files requested | 0 |

Every registered surface reproduces exactly. The single-stratum claim holds not
only on the one placeholder fixture but across the full 36-surface adversarial
set on both arms — this is a genuine confirmation of the candidate's
`distinct_stratum_count = 1`.

Permitted-operation counters for this review: 4 metadata requests, 16
allow-listed file downloads, 4 tokenizer constructions, 292 chat-template
renders, 596 encode calls.

### 4.2 Statistical recalculation

Exact rational arithmetic, standard library only, importing no candidate
calculator.

| quantity | candidate | independent | agrees |
| --- | --- | --- | --- |
| `m_max` | 58 | 58 | yes |
| `alpha_global` | `1/20` | `1/20` | yes |
| `alpha_per_cell` | `1/1160` | `1/1160` | yes |
| total scheduled evaluations | — | 8,108 | — |

Per gate, every `n`, integer pass boundary, exact size and exact power agrees to
the last registered digit:

| gate | cells | n | boundary | exact power | exact size | n minimal | boundary minimal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `G01_COT_CEILING` | 4 | 128 | k ≥ 111 | 0.912498598878 | 0.000856460763 | yes | yes |
| `G02_CONTROL_RECOVERY` | 8 | 110 | k ≥ 108 | 0.901331394239 | 0.000807913105 | yes | yes |
| `G03_CONTROL_BINDING` | 8 | 110 | k ≥ 108 | 0.901331394239 | 0.000807913105 | yes | yes |
| `G04_CONTROL_PRIMITIVE` | 8 | 110 | k ≥ 108 | 0.901331394239 | 0.000807913105 | yes | yes |
| `G05_NEGATIVE_CONTROL` | 8 | 416 | k ≤ 115 | 0.902527305436 | 0.000827387853 | yes | yes |
| `G06_WRAPPER_JOINT_ADEQUACY` | 8 | 74 | k ≥ 51 | 0.907835037241 | 0.000758111832 | yes | yes |
| `G07_RPB_DEVELOPMENT` | 6 | 74 | k ≥ 51 | 0.907835037241 | 0.000758111832 | yes | yes |
| `G08_RPB_CONFIRMATION` | 6 | 74 | k ≥ 51 | 0.907835037241 | 0.000758111832 | yes | yes |
| `G09_RT_E0_QUALIFICATION` | 2 | 74 | k ≥ 51 | 0.907835037241 | 0.000758111832 | yes | yes |

Minimality was proved exhaustively: for every gate, every smaller `n` from 1
upward fails the `9/10` power target, and the boundary immediately adjacent to
the registered one violates the size constraint.

Mismatches: **none**. Zero numeric disagreements were found.

Structural checks: development and confirmation are separate inferential cells
(6 + 6 over the full `L = 3`); both wrapper arms enter every applicable family;
the single Bonferroni family `F_GLOBAL_STUDY3R` covers all 58 cells with no
duplicate or omitted gate; no gate is unnecessarily global *in the multiplicity
sense* (the global-scope defect in F-03 is a state-machine defect, not a
multiplicity defect); fixed-sequence protection is correctly disclaimed; the
worst-case family-wise error over the twelve ladder cells is `3/290`
(0.010344827586).

The one structural criterion that fails is the authority's last: the sample
sizes correspond to the *pooled* competence claim, not to the depth-3
competence the construct advertises — which is F-02.

The negative control is executable as registered: direction
`less_than_upper_margin`, `H0: p ≥ 35/100` versus `H1: p < 35/100`, n = 416,
k ≤ 115, no equivalence-by-non-significance argument anywhere. Its construction
is coherent — no option carries the derivable value and the registered label is
drawn uniformly and independently of content, so no strategy can exceed 1/4 in
expectation. This was verified mechanically over 4,000 draws per family: the
`NEG` family never exposed the derivable value, and label positions were uniform
(974 / 992 / 1019 / 1015).

### 4.3 Task generators

4,000 adversarial draws per family under an explicitly non-scientific test seed
(`REVIEW_ADVERSARIAL_NON_SCIENTIFIC_SEED_NOT_FOR_EXECUTION`); no scientific bank
was realized and no execution seed was drawn.

| check | result |
| --- | --- |
| arithmetic correctness (`evaluate` vs registered value) | 0 violations in 24,000 items |
| subtraction never produces a negative partial | 0 violations |
| evaluated value inside `[0, 999]` | 0 violations |
| exactly four distinct non-negative options | 0 violations |
| derivable label carries the value | 0 violations |
| `NEG` never exposes the derivable value | 0 violations |
| label-position balance | uniform by construction (`rng.shuffle` / `rng.randrange`) |
| duplicate keys within 4,000 draws | REC 0, BIND 0, PRIM 2, D2 0, D3 0, NEG 1 — all excluded by the registered key rule |
| rejection loops terminate | yes, bounded at 1,024 attempts |

Two observations that are *not* defects but are recorded for completeness:
operation balance is not enforced (SUB is rejection-sampled to avoid negative
partials, so it appears roughly half as often as ADD/MUL — 1,818 vs 3,145 vs
3,037 in D2), and distractor options may exceed the registered *result* domain
(a 999-valued REC item can carry an option of 1,002). Neither changes a
registered decision: no balance claim is made anywhere in the bundle, and the
result-domain constraint is registered for the evaluated value, not for
distractors.

### 4.4 Repository, schema, manifest and bundle

| check | result |
| --- | --- |
| authored path set outside `studies/study3r/` | `.gitattributes`, `tests/test_study3r_operator_governance.py`, `tests/test_study3r_protocol_v1.py` |
| ancestry | five strictly linear commits, zero merges/rebases/rewrites |
| authority-alone ordering | confirmed, one file in `5a80c67…` |
| immutable-revision acquisition records | all four verified against live metadata |
| weight-file acquisition | none; weight paths exist in every repo but none was requested |
| bundle reproduction from generators | byte-exact (candidate suite, 163 tests) |
| JSON schema validation | 10 / 10 artifacts valid |
| unconstrained decision-bearing schema properties | none found in any of the 10 schemas |
| manifest entries recomputed | 27 / 27 reproduce byte and hash |
| manifest aggregate SHA-256 | `c3983f570281c1ab0a987d97d7861943dc8e11681e3d5bb2938f5a6276db8fe0` — recomputed identical |
| current pointer | single, unambiguous, no overlay, no fallback, no alternative artifact, no supersession |

The four deferred exclusions (machine + Markdown authoring disclosure, its
schema, and the Study 3R README) are genuinely unavailable at candidate
authoring time — each records the manifest's own aggregate digest or the commit
publishing it — and each is decision-reporting rather than decision-bearing.
The single self-exclusion is the manifest itself, correctly justified by the
impossibility of a SHA-256 fixed point and compensated by the Git commit/tree
outer identity. No active normative dependency sits outside the manifest apart
from `.gitattributes` (F-11).

On the pointer's route to the complete bundle: `study3r_protocol_current.json`
names only the protocol JSON, its schema, the Markdown and the authority. The
rendering registry, state machine, task generator, statistics and acquisition
records are reachable only one hop further, through
`protocol["references"]`. That is an unambiguous route — every normative
artifact is reachable and each path is exact — but it is indirect, and a reader
who follows only the pointer sees protocol/Markdown/schema. This is recorded as
an observation, not a finding, because the route is complete and single-valued.

### 4.5 Execution feasibility

| requirement | registered? |
| --- | --- |
| RT 1.5B / RP-B 7B, 14B, 32B identities and revisions | yes |
| context window and per-item generation bound | yes |
| framework / library versions for execution | **no** (acquisition-time versions only) |
| dtype | **no** |
| quantization or its absence | **no** |
| device mapping | **no** |
| deterministic execution | partially — `do_sample=false` for E0 and CoT; nothing else |
| memory feasibility, incl. the 32B checkpoint | **no** |
| batching / padding | **no** |
| token ceiling | yes, but as point estimates (F-07) |
| wall-clock / compute ceiling | **no** |

The 32B checkpoint is registered with no hardware, memory or precision
commitment whatsoever. Nothing in the bundle establishes that it fits any
particular environment, and the historical T4 environment cannot be assumed.
Because dtype and quantization change logits, and E0 scores a single greedy
token by full-sequence exact match, those unresolved choices can change the
primary endpoint. Freeze is not possible without resolving them; this is the
execution-feasibility face of F-04.

## 5. Test differential

| run | result |
| --- | --- |
| registered candidate baseline at `da1ea31…` | 8 failed, 5,120 passed, 16 skipped |
| `tests/test_study3r_protocol_v1.py` + `tests/test_study3r_operator_governance.py` at the review head | 163 passed, 0 failed, 0 errors |
| `studies/study3r/reviews/test_study3r_protocol_v1_single_focused_review.py` | see the receipt |
| full suite at the final review head | see the receipt |

The eight registered standing failures (seven historical host-line-ending
failures plus the scope-expired v0.7 focused-review invariant) were neither
edited nor suppressed. No review artifact touches any candidate path, any
top-level test module, `.gitattributes`, or any Study 3, Study 2, Study 1 or
paper artifact; every review artifact is additive inside
`studies/study3r/reviews/`.

## 6. Boundary

Prohibited-operation counters for this review, all zero: model-weight
downloads, model constructions, adapter/activation loads, prefill operations,
forward passes, logit reads, scoring operations, generations, GPU/cloud/Azure
jobs, scientific bank realizations, execution-seed draws, RP-B selections,
evidence-ledger changes, candidate repairs and amendments.

The evidence ledger still ends at `EV-0016` and no row was added or altered.
`frozen`, `execution_authorized` and `formal_execution_authorized` remain
`false`; this review changed no Study 3R candidate state inside its protocol
pointer.

## 7. Verdict

Four BLOCKING findings are confirmed:

* **F-01** — the depth-2/depth-3 allocation of four registered banks is
  undefined, so the task population is not identifiable;
* **F-02** — the pooled depth cell permits a checkpoint to clear the primary
  headline gate while performing at chance, or at zero, on depth-3;
* **F-03** — the prequalification gates are globally conjunctive, so one
  candidate's failure terminates the study and the registered
  first-confirmed-pass ladder is unreachable as described;
* **F-04** — the generated-CoT route freezes no decoding contract beyond
  `do_sample` and `k`, so the ceiling precondition is not reproducibly
  executable.

Each changes an estimand, a task population, a rendered model input, a pass/fail
decision, a candidate-selection result, a state transition or execution
reproducibility. None is downgraded to a limitation.

The candidate is otherwise strong: every registered statistic, every byte and
token surface, every manifest identity and every registered mutation reproduced
exactly under fully independent recomputation, and the single functional
equivalence stratum survived a far larger adversarial surface set than the one
committed fixture. That is precisely why the four defects above are reported as
what they are rather than absorbed.

`STUDY3R_PROTOCOL_V1_REJECTED_TERMINAL_NO_EXECUTION`

No repair, amendment, second authoring session or model execution may follow
automatically from this review.
