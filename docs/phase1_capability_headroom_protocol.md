# Phase 1 capability-headroom protocol (Track D, Phase 1.0C design)

## Status and boundary

This is a preregistration for **future calibration**, not an experiment result. This
track creates model-free tasks, validation tooling, and method-entry gates only. It
does not authorize model execution, tokenizer loading, Azure use, network access,
parser holdout access, or formal metrics.

The current depth-3 result of 0/3 does **not** establish model inability. The audit
found that exact finish/truncation instrumentation was absent, many outputs were
incomplete, legacy parser errors were material, the sample was tiny, decoding was
narrow, and the task construction was weak. An existing synthetic relation also
contained an entailment error, while prior factual questions could require outside
world knowledge. None of those tasks or outputs is treated as a capability-limit
fixture here.

Arithmetic is one sanity/patching family. It is not, by itself, RQ2 evidence and
must never be the sole basis for a hidden-workspace or model-level claim.

## Candidate bank

The frozen design candidate bank is:

- `data/phase1_task_headroom_candidates.jsonl`
- `data/phase1_task_headroom_candidate.schema.json`
- generator and validator:
  `src/jspace_observation/headroom_candidates.py`
- command-line materializer:
  `python scripts/generate_phase1_task_headroom_bank.py`

The bank contains 450 records: five families × three difficulty bands × three
splits × ten items. Each family/band has 10 calibration, 10 confirmation, and 10
untouched mechanistic items. Each family/band/split cell has five template
families, two items per template. Template-family IDs and synthetic entities are
disjoint across splits.

The required families are:

1. **Arithmetic** — 2, 3, or 4 explicit integer operations for
   easy/medium/hard.
2. **Synthetic relation** — mechanically checked directed paths of 2, 3, or 4
   hops, with both branches and all distractor edges in the prompt.
3. **Prompt-grounded two-hop factual** — always exactly two supplied lookup
   hops; difficulty increases only through 0, 2, or 4 complete distractor paths.
4. **Counterfactual entity replacement** — a scoped entity substitution followed
   by 2, 3, or 4 supplied links.
5. **Wrong-CoT/error detection** — a proposed 3-, 4-, or 5-step calculation with
   the first erroneous step registered by a numeric step code.

All factual and relation premises are literal prompt lines. Synthetic names are
used to prevent world-knowledge shortcuts. References are recomputed from
structured metadata. Every clean/corrupt pair changes one surface token in the
same rendered slot, changes the registered answer, and has a separately verified
reference. Target-token equality and exact tokenizer position alignment remain
future gates, not design-time claims.

Every record has the exact top-level fields:

`task_id`, `task_family`, `difficulty_band`, `split`,
`template_family_id`, `prompt_template`, `question`, `registered_answer`,
`intermediate_concept`, `concept_tokenization_requirement`,
`clean_corrupted_pair_availability`, `jlens_suitability`,
`patching_suitability`, `ablation_suitability`,
`ability_match_suitability`, `clean_corrupted_pair`, and `metadata`.

The nested metadata registers facts, clean and corrupted derivations, balance
keys, matched controls, prompt-echo control construction, evaluation route,
difficulty parameters, and template slots. A candidate's one-token concept status
is deliberately `pending_frozen_tokenizer_registration`; no token count is
inferred from spelling.

## Split discipline

- **Calibration** selects whole family/band cells and freezes all downstream
  choices. Individual items may not be retained or removed based on their result.
- **Confirmation** uses disjoint entities and template-family IDs. It must
  independently confirm a selected cell; failure cannot be repaired by moving
  calibration items into confirmation.
- **Mechanistic** remains untouched until the family/band, evaluator, tokenizer
  registration, runtime profile, layer/position scope, and analysis are frozen.
- Learned probes or ablation directions may use calibration templates only.
  Confirmation and mechanistic templates are held out.
- A tokenizer-registration failure makes that method/cell ineligible. Updating
  tasks requires a new version and a complete pre-calibration re-freeze, not an
  outcome-dependent item substitution.

## Future calibration grid

No calibration is run in this phase. When separately authorized, run both
conditions and report them separately:

- `visible_cot`
- `r1_style_thinking`

Run and report each decoding profile separately:

| Profile | Frozen settings |
|---|---|
| `deterministic` | `do_sample=false`; omit `temperature`, `top_p`, and every other sampling parameter from the request |
| `official_style` | `do_sample=true`, `temperature=0.6`, `top_p=0.95` |

Budgets are 256 and 512 generated tokens. A 1024-token budget is allowed only by
this trigger: at 512, a family × band × condition × profile calibration cell has
a task-level material-truncation rate above 5%. A task is materially truncated
only when the frozen primary seed reaches the cap, has no EOS, has a length/cap
finish reason, and semantic review labels the answer incomplete because of the
cap. With ten calibration tasks, one such task triggers 1024. Re-run the **whole
cell** at 1024; never rerun only failures. Other seeds are sensitivity runs and
do not change the trigger.

### Frozen seed derivation

For every run, derive an unsigned 64-bit seed as follows:

1. UTF-8 encode
   `phase1-headroom-seed-v1\0{task_id}\0{condition}\0{budget}\0{profile}\0{replicate_index}`.
2. Compute SHA256.
3. Interpret the first eight digest bytes as an unsigned big-endian integer.

`derive_run_seed` implements this rule. Record the seed even when deterministic
decoding does not consume it. Replicate indices and counts must be frozen before
execution; they cannot be added in response to outcomes.

### Required runtime record

Persist one append-only record per generation with at least:

- task ID, bank hash, condition, profile, budget/cap, replicate index, and seed;
- exact request settings and tokenizer identity/hash;
- prompt token IDs/count and generated token IDs/count;
- EOS token ID, whether EOS was emitted, finish reason, and cap reached flag;
- unmodified raw output;
- parser version/result, including ambiguity and failure fields;
- semantic label and adjudication provenance;
- one ordered failure attribution from the hierarchy below.

Missing finish reason, generated token IDs/count, EOS status, or exact cap makes
the run unusable for headroom selection. Raw output must never be reconstructed
from parsed text.

## Evaluator gate

Parser v2 must first pass a **separately authorized, one-shot locked evaluation**
before any formal numeric metric is computed. This design neither opens nor runs
that evaluation.

The current parser-v2 protocol is numeric-only. Therefore:

- arithmetic may use parser v2 only after the locked numeric pass;
- wrong-CoT uses the preregistered integer-to-`STEP_n` codebook in each record
  and still waits for the locked numeric pass;
- synthetic relation, prompt-grounded factual, and counterfactual entity answers
  require a separately locked typed-entity evaluator;
- any future boolean/entity family likewise requires a separately locked typed
  evaluator or a numeric coding frozen before evaluation.

A parser-v2 PASS validates no entity or boolean evaluator. Semantic
visible-reasoning accuracy is based on the separately frozen semantic evaluator,
not on opportunistic parser recovery.

## Band eligibility and statistics

The unit selected is the complete family × band cell. Condition, decoding
profile, and budget are never pooled for selection or reporting.

A cell is behaviorally eligible only when all of the following hold:

1. Semantic visible-reasoning accuracy is in **[0.70, 0.90]** in calibration and
   independently in the disjoint confirmation split.
2. The same frozen evaluator and profile are used within a comparison.
3. Material truncation is at most 5% of distinct tasks at the selected budget
   (zero of ten in either split).
4. Construction validation, runtime completeness, and the applicable locked
   evaluator gate pass.
5. The whole cell is retained; there is no item-level performance filtering.
6. The mechanistic analysis has at least eight distinct tasks correct under all
   required pre-intervention baselines. A 7/10 cell can satisfy the behavioral
   range but is mechanism-ineligible.
7. Concepts and clean/corrupt positions pass the frozen tokenizer registration
   checks required by the selected method.

Report point estimates and task-clustered confidence intervals. Resample tasks
as clusters and keep all seeds from a task inside its cluster. Seeds are repeated
decodes, **not independent task observations**, and must not inflate `n`.
Family-wide summaries must also cluster at task and preserve cell strata.

## Method-specific entry and success criteria

Design-candidate flags do not mean method eligibility. Every criterion below is
an entry gate.

### J-lens

- The readout target is a necessary, non-final intermediate concept.
- Its exact surface form is registered as one token under the frozen target
  tokenizer before cell freeze.
- Use the registered same-cell/same-template matched control with a different
  answer and concept.
- Materialize and baseline-check the registered prompt-echo control so lexical
  echo alone cannot explain readout.
- Include only tasks answered correctly under the strict answer-only baseline;
  visible-CoT success is not a substitute.
- Freeze the layer scope before results. Primary readout excludes embedding,
  final motor/output positions, the output head, and any layer region designated
  as motor/output. A signal confined to those regions is not workspace evidence.

### Activation patching

- Use the registered one-token clean/corrupt pair with different answers.
- After tokenizer registration, require equal token count and exact position
  alignment around the changed slot; otherwise the pair is ineligible.
- Both clean and corrupted prompts must be correct before intervention.
- Run the complete preregistered layer × position scan.
- Include clean→clean, corrupt→corrupt, random-position, and motor/output
  controls. A best-cell-only result is invalid.

### Ablation

- Require substantial strict answer-only prompt headroom: full-prompt accuracy
  at least 0.70 and at least 0.20 above the matched no-informative-evidence
  control.
- Learn directions only from calibration templates and evaluate on disjoint
  confirmation/mechanistic templates.
- Require at least eight baseline-correct distinct tasks in the analysis cell.
- Include matched-norm, random-direction, non-workspace, and motor/output
  controls.
- The preregistered task-clustered 95% confidence interval for the
  difference-in-differences must exclude zero in the predicted direction.

### Ability matching

- Use prompt-grounded tasks; no outside facts may be needed.
- Compare models with the same prompt, evaluator, condition, profile, and
  effective nontruncated budget.
- Require nonmaterial truncation and held-out-template confirmation.
- Freeze an accuracy-difference equivalence margin of ±0.10. Ability matching
  requires the task-clustered two-sided 90% confidence interval to lie wholly
  inside that margin (TOST-equivalent logic). A nonsignificant difference is not
  evidence of equivalence.
- Arithmetic can be a sanity check but cannot be the sole ability-matching or
  RQ2 evidence.

## Ordered failure attribution

Assign the first supported category in this order and preserve the evidence:

1. **construction** — invalid reference, missing premise, entailment error,
   leakage, or broken pair;
2. **runtime** — request, model serving, logging, or instrumentation failure;
3. **truncation** — cap/finish/EOS evidence plus semantic incompleteness;
4. **parser** — semantically adequate answer lost or misclassified by the frozen
   evaluator;
5. **decoding-sensitive** — materially different valid outcomes across frozen
   profiles/seeds after the preceding causes are excluded;
6. **underpowered** — task-clustered uncertainty is too wide or too few
   baseline-correct tasks remain;
7. **task-specific capability** — a validated, adequately powered family/cell
   fails without supporting broader generalization;
8. **model-level limitation** — only after all preceding causes are excluded
   across multiple non-arithmetic, prompt-grounded families and held-out
   templates.

No zero-accuracy cell, especially the prior depth-3 n=3 cell, may skip directly
to category 8.

## Design-phase completion checks

Before this design can be used, the checked-in tests must continue to verify:

- exact schema and unique IDs;
- exact family/band/split counts and split-disjoint template IDs;
- recomputed clean and corrupted references and literal premise inclusion;
- one-token surface pair differences and different answers;
- answer/concept counterbalancing and split-disjoint entities;
- all method-suitability fields and controls;
- byte-deterministic generation, schema freshness, and frozen seed vectors;
- standard-library-only generation with no target-model or network dependency.

Passing these checks establishes only task-bank integrity. It does not establish
behavioral headroom, method suitability, hidden reasoning, or model inability.
