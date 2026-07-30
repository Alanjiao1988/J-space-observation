# Phase 1.2F — Parser acceptance-policy correction and threshold preregistration

**Artifact ID:** `phase1-2f-acceptance-policy-protocol/v1`
**Status:** `EXECUTED`
**Terminal status of the round:** `BLOCKED_ON_ACCEPTANCE_POLICY`
**Authored from:** `origin/main` @ `d843984a3b7e1a2bf9d306621b8557ce327cf987`

---

## 0. What this round is, and what it is not

Phase 1.2F is a **repository audit, methodological design, policy/tooling
correction, testing and documentation** round.

It is **not** authorization to construct, seal, preregister, or evaluate
`parser-v3-v2`. No set was constructed. No case was migrated or replaced. No
manifest was generated. No seal was created. No authorization lock or evaluation
state chain was created. No evaluation image was built. Stage P and Stage E were
not run. No Azure resource was created, modified, or started.

The round answers exactly two questions:

1. **Independence.** Which of the four proposed numeric thresholds provide
   protection *beyond* the gates the policy already declares mandatory?
2. **Derivability.** For every threshold retained as a hard gate, can its value
   be derived **without** using parser-v3 performance, future holdout
   observations, or the unrelated Phase 1.0C headroom experiment?

The honest answer to (2) is *not yet, for the one criterion that survives (1)*.
The round therefore terminates `BLOCKED_ON_ACCEPTANCE_POLICY` and registers the
calibration that would unblock it, rather than manufacturing a number.

---

## 1. Post-hoc disclosure (mandatory, unconditional)

This policy is being written **after** some parser-v3 development results are
already known to the operator.

Specifically, before Phase 1.2F began, the following were already observable in
the repository or in the operator's working knowledge:

* parser-v2's locked evaluation result;
* parser-v3 development-time behaviour on non-locked material;
* the fact that `parser-v3-v1` was sealed and then retired as ineligible.

Nothing in that set was used to select a numeric threshold. The round's
principal *defence* against post-hoc selection is structural rather than
behavioural: the surviving criterion (`residual_critical_exact_budget`) is left
`REVIEW_REQUIRED` with `value: null` precisely because the operator cannot
demonstrate that a chosen number would be independent of what is already known.

Readers should treat this disclosure as a permanent limitation of the policy,
not as a resolved issue. It is registered as `L-33`.

---

## 2. Prohibitions honoured in this round

The following were prohibited and did not occur:

| Prohibition | Observed |
| --- | --- |
| Rerun Phase 1.0C | Not run |
| Use Phase 1.0C results to derive parser thresholds | Not used; explicitly rejected by the validator |
| Read private / git-ignored `parser-v3-v1` curator material | 0 reads |
| Read sealed locked inputs or labels | 0 reads |
| Access private answers, output text, spans, offsets, case identities, case-level labels | 0 accesses |
| Run parser v3, parser v2, or the legacy parser on any corpus | 0 runs |
| Generate predictions | 0 |
| Use parser-v3 development performance as a threshold basis | Not used |
| Select a threshold from parser-v2 or parser-v3 observed performance | Not done |
| Construct cases, migrate the 105, review the 15 quarantined | Not done |
| Generate a real set-facts manifest, seal a set | Not done |
| Create an authorization lock or evaluation state chain | Not done |
| Build or reuse an evaluation image; run Stage P or Stage E | Not done |
| Create/modify/start Azure resources | 0 |
| Modify `parser-v3-v1` bytes, namespace, manifests, historical invalid contract | 0 (digest-verified) |
| Change parser-v3 behaviour | 0 (digest-verified) |
| Change package import behaviour to make an "absolute parser-free" claim true | Not done; the claim was corrected instead |
| Claim parser v3 is validated / improved / non-regressive / accepted | Not claimed |

Existing candidate and comparator results were read **only** to reconstruct
project history, and were not inputs to threshold selection.

---

## 3. Corrected Phase 1.0C factual record

Phase 1.2E's stated blocker — "Phase 1.0C headroom calibration is NOT RUN" —
was **factually wrong when written** and **methodologically wrong regardless of
the facts**.

### 3.1 What actually happened

| Event | Commit |
| --- | --- |
| Preregistered | `62e9b961…` |
| Unblocked | `5d18b708…` |
| Executed | `72c3d281…` |
| Finalized | `06eec99315ff5b6c838aeaa82e0814fea6e886b4` |

Primary evidence:
`artifacts/phase1-headroom-calibration/track-b/20260725T170041Z/04_decision.json`

| Field | Value |
| --- | --- |
| `track_b_decision` | `INCONCLUSIVE` |
| target-model outputs generated | 300 / 300 |
| correct | 156 |
| incorrect | 100 |
| `unresolved_rows` | **44** |
| `outstanding_review_rows` | 0 |
| `arbitration_rows` | 0 |

The 44 figure is the count of **unresolved semantic-equivalence rows** recorded
by the finalized result pack. It is not a count of "unresolved labels" in any
parser sense, and it has no bearing on parser acceptance.

### 3.2 Why it could never have supplied parser thresholds

Phase 1.0C's own `scientific_interpretation` field states that the phase
"estimates observable answer accuracy of a single target model … for the sole
purpose of selecting task cells with measurable headroom."

That is a **target-model task/headroom screen**. It measures whether a task cell
is answerable-and-not-saturated by the model under study. It does not observe a
parser, does not score parser output, and contains no parser reference labels.
A parser acceptance threshold cannot be derived from it under any
transformation. Phase 1.2E's dependency claim was a category error, and it would
have remained a category error even if Phase 1.0C had genuinely been unrun.

### 3.3 Failure-class clarification

Phase 1.2E filed this defect under `H9`. That was incorrect and has been
withdrawn.

* **`H9`** concerns *disagreement among declared and observed artifact
  vocabulary, support, or set facts* — an instrument-consistency failure.
* The Phase 1.2E defect is a **policy-provenance defect**: a threshold was bound
  to a source that cannot supply it.

An unjustified threshold source is not automatically another occurrence of H9.
Historical findings `H1`–`H9` are neither redefined nor erased by this round.

### 3.4 Mechanical guard

`scripts/check_current_state_consistency.py` reads ground truth **from the
committed Phase 1.0C result pack**, not from prose, and fails if any
current-state document again asserts that Phase 1.0C is `NOT RUN`/blocked
pre-execution, or asserts a parser-threshold dependency on it. Documents that
are explicitly marked as superseded point-in-time history are exempt via an
`EXEMPT_MARKERS` allowance, so legitimate history is preserved.

---

## 4. Gate-coverage baseline (the analysis everything else rests on)

Before asking whether a threshold is justified, the round asked what the
already-mandatory gates leave free.

Registered strata and case counts (120 cases, 12 strata):

| Coverage | Strata | Cases | Pinned by |
| --- | --- | --- | --- |
| Zero-error, clean | `S01 S02 S03 S12` | 40 | `G_clean_strata_exact` |
| Zero-error, special | `S07 S08 S10 S11` | 40 | dedicated zero-error gates |
| **Free / residual** | **`S04 S05 S06 S09`** | **40** | *nothing* |

**8 strata / 80 of 120 cases are already pinned to exact typed-decision
agreement.**

Consequence: any acceptance criterion expressed over all 120 cases can only
constrain behaviour on the 40 free cases, because a run that violates any
zero-error gate already fails regardless. This single fact disposes of two of
the four proposed thresholds.

### 4.1 Why `S06` is in the free population

Audit finding A2 rejected an earlier 90/30 split. That split required reading
one field, `maximum_errors`, three incompatible ways in the same table: broadly
for `S06`, exactly for the clean strata, and set-level-only for the
null-collapse prohibition — which under the broad reading would have pinned all
120 cases and made the whole round moot.

The only *registered* definition of an `S06` error is the narrow one in
`docs/phase1_parser_v3_acceptance_gates.json` and the historical parser-v2 gate
contract: selection of the registered rightmost distractor span. A parser can
satisfy that and still return a wrong canonical value. `S06` is therefore
**not** pinned to exact typed-decision agreement, and belongs with the free
strata.

Every gate now declares `error_definition`, `error_scope` and
`pins_exact_typed_decision`, and the validator refuses a gate that omits them.
Coverage is derived from those declarations rather than from a disambiguation
buried in a test helper. Adopting the registered narrow reading is the
conservative choice: it *enlarges* the population the surviving criterion must
govern.

---

## 5. Threshold audit method

Each proposed threshold received a structured disposition record containing:
threshold ID; metric definition; numerator; denominator; inequality direction;
population; failure risk controlled; relationship to existing mandatory gates;
independence classification; candidate-independent evidence basis; derivation;
boundary examples; sensitivity analysis; disposition.

Permitted dispositions: `KEEP_HARD`, `REPLACE_HARD`, `MERGE_WITH_EXISTING_GATE`,
`REPORT_ONLY`, `REMOVE_REDUNDANT`, `REVIEW_REQUIRED`.

A threshold was **not** allowed to survive as a hard criterion merely because
parser v2 used a similar number. Reproducing an older value is permitted only
when the same value follows from a new, explicit, candidate-independent
derivation. No threshold met that condition.

### 5.1 Recognised basis types

1. `LOGICAL_INVARIANT` — follows directly from a stratum's purpose or an
   integrity requirement.
2. `DOWNSTREAM_ERROR_BUDGET` — traced to a preregistered maximum tolerable
   distortion in a later scientific metric or decision.
3. `EXTERNAL_CANDIDATE_INDEPENDENT_CALIBRATION` — a separate calibration design
   preregistered before candidate outputs are observed.
4. `REVIEWED_OPERATIONAL_REQUIREMENT` — a stated evaluator-reliability
   requirement justified independently of candidate and holdout.

### 5.2 Rejected basis sources (machine-enforced)

Phase 1.0C headroom results; parser-v3 development accuracy; parser-v2 locked
performance; expected parser-v3 performance; "industry standard" without a
primary source and applicability analysis; textual substitution from parser-v2;
selecting a number because it would likely permit a pass.

`PROHIBITED_BASIS_SOURCES` in `src/jspace_observation/parser_v3_repair_contract.py`
rejects these by normalised substring match across `reason`,
`blocking_dependency` (recursively, since it is a structured record), every
evidence binding, and ten registered prose fields of **every** threshold record
regardless of its disposition.

Audit finding A6/B7 corrected an over-claim here. This is a **bounded
carelessness check, not a semantic guarantee**: it catches a disallowed source
that is *named*, and it survives hyphenation, line wrapping and spacing
variants. It cannot detect a prohibited basis that is paraphrased, and it is
not a substitute for review. The scope is recorded in the policy as
`enforcement_scope`.

### 5.3 Required machine-readable fields per numeric hard threshold

`basis_type`, `controlled_risk`, `derivation`, `evidence_bindings`,
`candidate_independence`, `set_independence`, `boundary_semantics`,
`review_status`.

---

## 6. Findings per threshold

### 6.1 `overall_exact_typed_decision_minimum` → `REPLACE_HARD`

Any value that permits ≥40 errors is **vacuous**: the zero-error gates already
forbid every error outside S04/S05/S06/S09, so a run failing this threshold has
already failed a gate. The binding range is 81–120 correct, which is
arithmetically identical to placing a budget on the 40 free cases — but stated
over the wrong denominator, which conceals what it actually constrains.

Retained *structure*, discarded *form*: replaced by
`residual_critical_exact_budget`, stated over the population it genuinely
governs. The overall figure remains computed and reported, non-binding.

### 6.2 `critical_stratum_floor` → `MERGE_WITH_EXISTING_GATE`

The declared critical set `S04`–`S11` contains four strata (`S07 S08 S10 S11`)
that already carry zero-error mandatory gates pinning exact typed-decision
agreement. A per-stratum floor is **inert** on those four for every possible
value: no floor can be stricter than zero errors, and any floor looser than
zero is unreachable without first failing the gate.

Its only independent content is therefore `S04`, `S05`, `S06`, `S09` — the same
40 cases as §6.1. That is one constraint written twice, with a live risk of the
two numbers disagreeing at integer boundaries. Merged into the residual budget.

### 6.3 `answer_presence_macro_f1_minimum` → `REPORT_ONLY`

The future evaluation is a **fixed, quota-constructed adversarial challenge
set**, not an IID draw from a deployment population. Confidence intervals and
population-performance statements do not apply, and the policy now records this
in `population.sampling_frame`.

With registered supports `present: 80`, `no_answer: 30`, `ambiguous: 10`, the
round **exhaustively enumerated the feasible three-class confusion matrices**:

* **861 feasible matrices** — all integer pairs
  `(errors_to_no_answer, errors_to_ambiguous)` summing to at most 40, i.e.
  `C(42, 2)`;
* macro-F1 range **0.636895 – 1.000000**, the minimum attained at
  `(16, 24)`;
* therefore any threshold ≤ 0.636895 is **vacuous by construction**;
* macro F1 is **non-monotone in error count** — at exactly 40 presence errors,
  attainable macro F1 spans **0.636895 – 0.755556** depending only on *which*
  confusions occur, so the metric does not order runs by severity.

Attained extrema at equal error counts (audit finding A1 established that every
published bound must be an enumeration result, not a rounded illustration; a
test recomputes all four):

| Presence errors | Minimum macro F1 | Maximum macro F1 |
| --- | --- | --- |
| 10 | 0.866667 | 0.930159 |
| 20 | 0.783355 | 0.869048 |
| 30 | 0.708791 | 0.811966 |
| 40 | 0.636895 | 0.755556 |

**The decisive defect.** Present-value errors were modelled separately from
answer-presence confusion, because a wrong canonical value preserves the
presence class while failing exact typed-decision agreement. A candidate
returning **40 wrong canonical values** with perfect presence classification
scores **macro F1 = exactly 1.0000** while exact typed-decision agreement is
**80/120 = 66.7%**.

A metric that reports a perfect score for a candidate that got a third of the
set's canonical values wrong cannot be a hard acceptance gate. Downgraded to
report-only, and machine-blocked from re-entering PASS/FAIL logic.

The macro-F1 redundancy argument rests only on the zero-error gates that pin
exact typed-decision agreement. Audit finding A8 withdrew an earlier appeal to
the non-vacuity gates: a minimum-denominator requirement constrains how many
cases are *scored*, not how they are *classified*, so it cannot forbid class
collapse and must not be offered as if it could.

### 6.4 `non_regression_margin_vs_parser_v2` → `REPORT_ONLY`

**One reason, and it is sufficient.** No margin is choosable prospectively:
every candidate justification for a *numeric* margin requires observing at
least one parser on the locked set, which is precisely what
candidate-independence forbids.

Audit finding A4 **withdrew two further reasons** that were offered in an
earlier draft, because neither survives inspection:

* *"Parser v2 failed its own locked evaluation, so it is not a fitness
  reference."* This argues against treating parser v2 as a **sufficiency**
  standard. It does not argue against a **non-regression** check, whose entire
  content is that the successor must not be worse than the incumbent. That
  remains meaningful whatever the incumbent's absolute standing.
* *"The comparator run does not exist."* A prospective policy registers
  criteria for runs that do not yet exist; that is what prospective means. The
  absence of the run is a reason the criterion cannot be *evaluated* now, not a
  reason it cannot be *registered*.

A **margin-free formulation** was therefore considered on the merits and is
recorded in the policy as `margin_free_formulation_considered`: require
per-case dominance, i.e. that parser v3 be correct on every locked case parser
v2 is correct on, with no numeric margin to derive. It is
`REJECTED_ON_SUBSTANCE`, not on provenance: on a 120-case quota-constructed
adversarial set the incumbent's per-case correctness pattern is an accident of
its heuristics, so per-case dominance would elevate that accident to a binding
requirement and could refuse a strictly better parser that trades one
incumbent-correct case for several incumbent-wrong ones.

Retained as **report-only context**, with `comparators.role: REPORT_ONLY`.
Recording a regression remains scientifically informative; gating on it is not
defensible.

### 6.5 `residual_critical_exact_budget` (new) → `REVIEW_REQUIRED`

The one criterion that is genuinely independent and non-vacuous.

* **Population:** the 40 free cases in `S04`, `S05`, `S06`, `S09`.
* **Metric:** count of cases failing exact typed-decision agreement.
* **Direction:** `errors ≤ B`, integer, with `errors == B` passing.
* **Structure:** derived candidate-independently in this round.
* **Value:** **`null`** — `REVIEW_REQUIRED`.

#### What actually blocks the value

Audit finding A3 rejected this section's first version, which named the missing
downstream error budget as the sole blocking dependency and defended that with
a circular argument: *"if these strata required zero errors they would already
carry zero-error gates."* That offers the absence of a gate as evidence that no
gate is warranted, when the absence of a gate is exactly the open question.
Worse, it made the block unexitable in the wrong direction — executing the
registered calibration protocol would have supplied a budget and the round
would still have been blocked, because the strictness question would remain
unanswered.

The dependencies are therefore now **ordered**, and recorded that way in the
policy's structured `blocking_dependency`:

1. **Primary — an unmade scientific decision.** `S04`, `S05`, `S06` and `S09`
   are *designed-failure* strata: cases constructed so that a correct
   instrument must not produce a confident extraction. `S06` is exactly such a
   stratum and *does* carry a zero-error gate, over a narrower registered error
   definition. Whether the instrument must be exactly correct on the remaining
   designed-failure strata, or may be permitted a non-zero budget, has never
   been decided. A `LOGICAL_INVARIANT` basis for `B = 0` is available in the
   abstract; what is missing is the decision, not the basis.
2. **Secondary — a downstream error budget.** *Only if* a non-zero tolerance is
   permitted does `B` need tracing to a preregistered maximum tolerable
   parser-induced distortion in a later scientific metric. A repository-wide
   search returned no such registered budget.

The remaining bases are unavailable either way:

* `EXTERNAL_CANDIDATE_INDEPENDENT_CALIBRATION` — the required calibration is
  registered by this round but **not executed**.
* `REVIEWED_OPERATIONAL_REQUIREMENT` — no evaluator-reliability requirement
  independent of candidate and holdout has been stated for these strata.

Audit finding A9 further established that the downstream plan is not entirely
silent: `docs/phase1_capability_headroom_protocol.md` (lines 228-229 and 252)
*does* register the downstream decision rule and names the parser as a
failure-attribution category. What is missing is only the tolerance itself.
The claim "no budget exists" is true as stated but was too broad in spirit, and
is qualified accordingly.

Per §8 of the round's charter, no placeholder number was inserted.

---

## 7. Consequence for the policy and the compiler

`docs/phase1_parser_v3_v2_evaluation_policy.json` remains
**`status: REVIEW_REQUIRED`**, because `residual_critical_exact_budget` is
`REVIEW_REQUIRED`.

`compile_contract` continues to refuse to compile while any required policy
decision is `REVIEW_REQUIRED`. That refusal is **correct behaviour and was not
weakened**. Synthetic boundary tests confirm the compiler would succeed only if
the policy became `FINAL`, and no contract tied to a synthetic set is committed.

Four of the five thresholds carry `status: FINAL` — a `REPORT_ONLY` or
`MERGE_WITH_EXISTING_GATE` decision *is* a decision, and is not pending. Only
the residual budget is open.

---

## 8. Namespace provenance (§10) and L-32

The prospective policy previously bound to
`evaluator_sets/parser_v3_v1/strata_definitions.md` — a **retired v1
namespace**. That conflicts with the new-set identity rule, with the repair
CLI's v1-namespace refusal, and with the requirement that reused design
artifacts be re-derived and revalidated.

Resolution: `docs/phase1_parser_v3_v2_stratum_policy.md`, a **public, case-free,
versioned v2 stratum policy** (`phase1-parser-v3-v2-stratum-policy/v2`) with
explicit provenance and an independent, recorded decision to **retain** the
12-stratum taxonomy on its merits. It creates no private case, label, membership
manifest, or sealed object. `policy.provenance.retired_binding` records the
supersession.

**`L-32` preserved accurately.** A future sealed member list and
`sealed_object_count` require an **authenticated seal-time observation**. They
are not facts an offline prospective policy can derive, and an operator
assertion must never be recorded as a set-derived fact. The v2 stratum policy
names these quantities only to disclaim them, and asserts no value for either.

---

## 9. Parser-isolation claim (§9)

`src/jspace_observation/__init__.py` **eagerly imports the legacy parser**.
Importing a submodule through the package may therefore already place parser
code in `sys.modules`.

**Withdrawn** (unsupportable): "no parser module exists in the process";
"package import is absolutely parser-free".

**Retained** (supportable and tested):

* repair modules introduce **no new** parser dependency;
* repair modules contain **no parser symbol reference**;
* repair tooling **does not invoke** a parser.

The differential-import test imports the package baseline, records
`sys.modules`, imports the repair tooling, and proves no *additional* parser
module was introduced. A separate AST-based static proof shows no parser symbol
is referenced, and a subprocess runtime tracer proves **zero parser
invocations**.

`__init__.py` was **not** refactored to make the stronger wording true. Doing so
would have changed package import behaviour for the sole purpose of flattering a
claim.

---

## 10. Next gate

**Register a downstream parser-error budget**, then execute
`docs/phase1_2f_parser_error_budget_calibration_protocol.md`.

That protocol is `REGISTERED — NOT EXECUTED`. It is **not** Phase 1.0C, is not a
target-model headroom screen, and must not be executed in this round.

Until a budget exists, `residual_critical_exact_budget` stays `REVIEW_REQUIRED`,
the policy stays `REVIEW_REQUIRED`, the compiler keeps refusing, and
`parser-v3-v2` remains unauthorized.

---

## 11. Standing state after Phase 1.2F

* Phase 1.0C was **executed** and finalized **`INCONCLUSIVE`**.
* Phase 1.0C is **not** parser calibration and supplies no parser threshold.
* No private holdout was accessed in Phase 1.2F.
* No prediction was generated.
* No parser was run.
* No formal evaluation occurred.
* Parser v3 remains **unvalidated**.
* Formal parser-v3 evaluation ordinal remains **0**; parser-v3 predictions
  against a locked set remain **0**; locked-label reads remain **0**.
* `parser-v3-v1` remains **`SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`**
  and byte-unchanged.
* **No J-space, hidden-reasoning, invisible-CoT, or internal-workspace
  conclusion follows** from anything in this round.
