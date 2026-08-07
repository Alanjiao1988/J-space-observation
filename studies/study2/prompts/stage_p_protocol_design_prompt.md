Take over the next independent scientific gate in this repository:

repository: https://github.com/Alanjiao1988/J-space-observation.git
branch: main
protected Study 1 terminal commit: 6409d2c6d665187e4459d94d490a20d7b085e8af
protected Study 1 terminal tree: bc8b80cb0e66f9426dcdedd52b624c892caa3fc9
Study 2 bootstrap authority commit/tree: read exact values from
studies/study2/handoff_receipt.json
Study 1 terminal state: INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY
Phase 1.0D state: BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY
target model: deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
target revision: ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562
lineage base control: Qwen/Qwen2.5-Math-1.5B
lineage base revision: 4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2
instruction control: Qwen/Qwen2.5-Math-1.5B-Instruct
instruction control revision: aafeb0fc6f22cbf0eaeed126eff8be45b0360a35
official J-lens repository: https://github.com/anthropics/jacobian-lens.git
official J-lens commit: 581d398613e5602a5af361e1c34d3a92ea82ba8e

This authority is already stored at
`studies/study2/prompts/stage_p_protocol_design_prompt.md`. Do not copy,
rewrite, or recommit it. Before implementation, verify its exact bytes against
`studies/study2/handoff_receipt.json` and verify the authority commit/tree
recorded there.

This authority is for Study 2 Stage P only: prospective protocol design,
model-free synthetic-bank construction, one bounded methods review, one
consolidated correction if required, freeze, tests, ledgers, and handoff. It is
not authority to run a tokenizer, model, lens, activation, or intervention.

1. Controlling interpretation

Study 1 ended correctly and irreversibly as
INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY. Its sole E0 run answered only
whether the selected official public items supplied enough clean-correct
next-token cases under the frozen raw-completion interface. It did not apply a
lens and did not test hidden reasoning. Do not rerun, repair, relabel, backfill,
or reinterpret Study 1.

Study 2 is a new study, not S3 v1. It asks the original question in an
operationally testable form:

Does the R1-distilled checkpoint compute and causally use a task-defined
intermediate variable during a single forward pass with zero generated
reasoning tokens, and is that behavior or mechanism stronger than in both its
lineage base checkpoint and a same-family instruction-tuned control?

"Genuine reasoning" is not a primitive label. Study 2 may support only the
following operational statement if all registered gates pass:

The target checkpoint uses a causally load-bearing intermediate variable to
solve fresh compositional tasks under a controlled no-generated-trace
interface.

An additional distillation-associated statement requires prospective
comparisons against both controls. A difference between final checkpoints may
be attributed only to the total post-training/distillation-associated
checkpoint change. It cannot identify which training sample, loss component,
or teacher trace caused the difference.

This design deliberately removes the Study 1 output-interface failure from the
primary estimand. The model will not be required to make the full-vocabulary
top-1 token equal an open-ended answer. The primary behavioral observable is a
four-option logit vector at one registered answer position. There is no model
generation, no output-text parser, and no semantic reviewer in the primary
path.

The design must still distinguish all of these weaker explanations:

- option-label prior or output-format preference;
- direct one-hop lookup rather than composition;
- prompt echo of a state token;
- final-answer or donor-answer copying;
- generic residual transfer rather than intermediate-state transfer;
- a decodable but causally unused representation;
- motor/output preparation restricted to final layers;
- instruction tuning or generic post-training rather than R1 distillation;
- a result confined to one task family or one surface template.

Primary sources motivating the design are:

- DeepSeek-R1 official model card and repository: the 1.5B checkpoint is based
  on Qwen2.5-Math-1.5B and fine-tuned with R1-generated samples; the official
  usage guidance also states that an empty thinking block can reduce expected
  performance. https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
- From Reasoning to Answer: explicit R1 reasoning tokens can influence later
  answers, but that does not establish computation without those tokens.
  https://arxiv.org/abs/2509.23676
- Analysing Chain of Thought Dynamics: multiple-choice answer-token
  probabilities can measure pre-CoT and post-step confidence, and distilled
  reasoning models often revise their initial answer during CoT.
  https://arxiv.org/abs/2508.19827
- The J-lens paper: readout alone is insufficient; intermediate swaps and
  matched controls are required for a causal workspace claim.
  https://transformer-circuits.pub/2026/workspace/
- Observable Patterns Are Not Explanations: decodability or static geometry
  without matched causal tests does not establish a mechanism.
  https://arxiv.org/abs/2606.12689

2. Explicit non-authority

This round must not:

- load or construct any real tokenizer;
- download model weights or instantiate any target or control model;
- run any forward pass, generation, logit extraction, or semantic-review call;
- load, inspect, apply, refit, merge, compare, or modify A600, B600, or M1200;
- extract activations, fit a probe, patch, ablate, steer, or intervene;
- open or reuse Study 1 item-level output to choose Study 2 tasks, templates,
  thresholds, layers, or controls;
- resume or alter Phase 1.0D, request quota, mutate a deployment, or consume its
  recovery authority;
- revive parser-v2/parser-v3 work or create another semantic evaluator;
- execute RQ2/S4 under the old authority;
- create a scientific evidence row or claim that Study 2 has produced a model
  result.

The existing S2 lenses are pre-existing fixed artifacts. A later, independent
Study 2 authority may read the sealed target M1200 only after the new
behavioral manifest and mechanistic-cell selection are sealed. This round may
record its identity but may not inspect its tensor values.

3. Operating rules

3.1 Azure executes; the laptop edits and orchestrates

The laptop may inspect tracked public files, edit, run lightweight Git and
hash commands, and submit Azure validation. It must not run pytest,
imports-as-tests, builds, tokenizer/model downloads, sustained data generation,
or scientific computation locally.

Use existing ACR Tasks/QuickRuns for executable validation, deterministic bank
generation, focused tests, and the full suite. No GPU Job is required in this
design-only round.

3.2 GitHub is Git transport only

Allowed: clone, fetch, inspect, commit, and non-force push to the existing
repository. Forbidden: GitHub Actions, workflows, pull requests, issues,
releases, artifacts, GHCR, Packages, and Codespaces. Do not create or modify
.github/workflows/*.

3.3 Preserve user state and history

Use small, honest, non-amended commits and fast-forward pushes. Never use
force-push, destructive reset, git clean -fd, git clean -fdx, broad recursive
deletion, or an unresolved path. If unrelated worktree changes exist, preserve
them and stop with the exact paths.

All Study 1, Phase 1.0D, parser, S2, and S3 v1 artifacts are protected history.
New Study 2 files must use new namespaces and new IDs. Do not rewrite old
decisions, methods, limitations, evidence, reports, receipts, locks, manifests,
or result packs.

3.4 One bounded methods review

This new Study 2 authority supplies one review cycle over one exact candidate
protocol hash. It permits at most one consolidated correction of all FATAL and
MATERIAL findings, followed by same-checklist verification. It does not permit
recursive auditing, a second redesign cycle, a private holdout program, or a
new evaluator infrastructure project.

4. Exact starting-state gate

Before any implementation:

1. Fetch origin/main without rebasing and require a clean worktree. Preserve
   and report unrelated changes rather than overwriting them.
2. Read `studies/study2/handoff_receipt.json`. Require its schema version,
   Study 1 terminal commit/tree, Study 2 bootstrap authority commit/tree,
   prompt path, prompt byte count, and prompt SHA-256 to match the repository.
3. Require the bootstrap authority commit to be an ancestor of origin/main and
   require the Study 1 terminal commit to be an ancestor of that authority.
4. Require commit `6409d2c6d665187e4459d94d490a20d7b085e8af` to have tree
   `bc8b80cb0e66f9426dcdedd52b624c892caa3fc9`.
5. Require origin/main to equal the exact handoff head supplied by the operator
   in the new-thread message. Record that commit and tree as the Stage P
   execution starting state. A handoff document cannot embed the SHA of the
   commit that contains itself, so the operator-supplied head is binding.
6. Require `paper/evidence_ledger.csv` to end at EV-0016 and require D33 to be
   the Study 1/Study 2 boundary decision. Stage P must allocate only new IDs.

Do not edit this authority prompt after the gate. Commit Stage P implementation
and protocol outputs in small fast-forward checkpoints, keeping the handoff
starting head as an ancestor.

Rehash and record at least these protected anchors:

- docs/jlens_s2_s3_e0_final_handoff.md:
  5870c82b15575086f5c29c34661d89d96d265848846e3de74162da8919951f77
- docs/jlens_s3_validity_protocol.json:
  bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625
- docs/decisions/jlens_s3_validity_protocol_freeze.md:
  d7d9623e3668b5469b426ba45671f267b631599e44f598f710f6c16564a96b48
- S2 manifest:
  9d10a4b07a8133b7241ce9067649ebf1de48429cf7c04e0495b4c3fe90e58e47
- A600 seal:
  4032c8f30ec6aec2f12cbf0a303466a0fe66745617266dcc0fa3d2289e731dd7
- B600 seal:
  b62cd7f69aaa4a662144d8a8b75e3165330c9369990a52dbee85bb1b06b33ad4
- M1200 seal:
  9716c3802625176060b3c2a479f7860cf4045807a45c6de346833a3b66e00138
- E0 artifact manifest:
  6d11b09b39bbeead9b38fdb23be47a4247245fb55e6b6b665b817241519df60f
- E0 terminal receipt:
  e7daad69a81377aba05be2617c07522d8d04552e594bc2cdc8318b057a83f218
- Phase 1.0D capacity certificate:
  20e486e05a5f076b720ca12db3459b5a1c2c42e95684977dfdcff19d6da055d3
- Phase 1.0D capacity manifest:
  23016ad15430b1720e4b37033a3638bf45e817ac00513292d138d26e0ed0a834

Verify that paper/evidence_ledger.csv ends at EV-0016. Verify that D32 is the
Study 1 E0 terminal decision. Verify both Phase 1.0D protected-byte rollups and
the final handoff's protected-state statements. If any protected byte differs,
stop before Study 2 design as BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY. Do
not repair a starting-state mismatch under this authority.

5. Required Study 2 protocol package

Create a minimal public, machine-checkable package:

- studies/study2/protocol/reasoning_internalization_protocol.md
- studies/study2/protocol/reasoning_internalization_protocol.json
- studies/study2/protocol/reasoning_internalization_protocol.schema.json
- studies/study2/protocol/reasoning_internalization_protocol_review.md
- studies/study2/decisions/reasoning_internalization_protocol_freeze.md
- studies/study2/data/task_bank_manifest.json
- studies/study2/data/development.jsonl
- studies/study2/data/behavioral_confirmation.jsonl
- studies/study2/data/mechanistic_development_candidate_pairs.jsonl
- studies/study2/data/mechanistic_candidate_pairs.jsonl
- src/jspace_observation/study2_protocol.py
- src/jspace_observation/study2_task_bank.py
- scripts/build_study2_task_bank.py
- scripts/validate_study2_protocol.py
- tests/test_study2_protocol.py
- tests/test_study2_task_bank.py

Additional small files are allowed only for irreducible registered content.
Do not create a general experiment platform, evaluator service, private review
boundary, task marketplace, or reusable workflow framework.

The JSON is canonical. The Markdown must explain every canonical field and
formula without changing meaning. The schema and pure Python validator must
reject missing or extra fields, placeholders, NaN/Infinity, mutable model
references, overlapping semantic identities, unbalanced answer labels,
post-outcome selection, an unregistered terminal state, and any task row whose
ground truth cannot be independently recomputed.

The Stage P validator and task generator are strictly model-free. They must not
import transformers, torch, the J-lens package, Azure inference clients, or any
Study 1 result reader.

6. Models and comparative interpretation

Freeze these three models and no others:

1. target: deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B at
   ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562;
2. lineage base: Qwen/Qwen2.5-Math-1.5B at
   4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2;
3. instruction control: Qwen/Qwen2.5-Math-1.5B-Instruct at
   aafeb0fc6f22cbf0eaeed126eff8be45b0360a35.

Record why both controls are required. The lineage base is the named source
checkpoint family but is not instruction tuned. The instruction control
reduces the alternative explanation that any target advantage is merely
instruction following or generic post-training. Neither control alone supports
a distillation-specific conclusion.

A later execution must use each model's pinned tokenizer, float16 parameters,
evaluation mode, use_cache=false, and trust_remote_code=false. Models are
loaded and run separately; do not require simultaneous GPU residency.

The primary prompt is model-neutral raw text and does not use a chat template.
Every model receives identical UTF-8 prompt bytes, apart from its own
tokenizer-required BOS behavior. Token IDs, decoded tokens, BOS behavior,
config identity, tokenizer identity, input length, and exact answer-position
index must be recorded per model.

7. Synthetic tasks and exact bank sizes

Use only new programmatically generated compositional tasks. Do not use or
adapt the 450-item Phase 1 bank, the 238 S3 items, their item-level outcomes, or
their prompts. Similar high-level task ideas are not byte reuse; exact and
normalized prompt overlap must be zero and proven.

7.1 Family A: permutation_chain

- State space is the eight symbols 0 through 7.
- Every item defines three complete independently sampled permutations P, Q,
  and R over the state space.
- Every prompt displays all three maps in a canonical complete lookup-table
  form, regardless of queried depth.
- The query specifies a start state and an ordered sequence of one, two, or
  three operators.
- Depth 1 is a direct-lookup control. Depths 2 and 3 require composition.
- Ground truth includes every intermediate state and the final state.
- The four output options contain the correct final state and three distinct
  distractor states, mapped to option labels A, B, C, and D.

7.2 Family B: affine_mod10

- State space is the ten symbols 0 through 9.
- Every item defines three affine maps f_i(x) = (a_i*x + b_i) mod 10.
- a_i is selected only from 1, 3, 7, and 9; b_i is selected from 0 through 9.
- Every prompt displays all three operators and a constant state legend
  containing all ten state symbols, regardless of queried depth.
- The query specifies a start state and an ordered sequence of one, two, or
  three operators.
- Depth 1 is a direct-computation control. Depths 2 and 3 require composition.
- Ground truth includes every intermediate state and the final state.
- The four output options contain the correct final state and three distinct
  distractor states, mapped to A, B, C, and D.

7.3 Surface templates

Create exactly two semantically equivalent templates per family:

- T-A: definitions first, then start/operation sequence, then options;
- T-B: query first, then definitions in a different fixed order, then options.

Both end with the exact bytes `Answer:` and contain no answer placeholder,
think tag, reasoning instruction, solved step, intermediate state for the query,
or generated text. Template identity is explicit in every row. The generator
must prove that semantic ground truth is identical under both renderers. Each
semantic item in the development and behavioral-confirmation banks is rendered
exactly once under its assigned template; T-A/T-B balance is achieved by
assignment, not by duplicating a semantic item across rows. Within a
mechanistic pair unit, donor, recipient, and registered donor controls share
one template and the same structural field order.

7.4 Determinism, balance, and disjointness

Use SHA-256 counter-mode sampling or an equivalently explicit deterministic
algorithm. Do not rely on Python's process-randomized hash or an unrecorded RNG
state. Freeze these literal seeds:

- development: jspace-study2-dev-2026-08-07
- behavioral confirmation: jspace-study2-behavior-confirm-2026-08-07
- mechanistic development: jspace-study2-mechanistic-dev-2026-08-07
- mechanistic candidate confirmation: jspace-study2-mechanistic-confirm-2026-08-07
- option permutation: jspace-study2-option-order-2026-08-07
- bootstrap: jspace-study2-bootstrap-2026-08-07
- random controls: jspace-study2-random-controls-2026-08-07
- label permutations: jspace-study2-label-permutations-2026-08-07

Freeze these exact sizes:

- development: 64 semantic items per family x depth cell = 384 rows;
- behavioral confirmation: 256 semantic items per family x depth cell =
  1,536 rows;
- mechanistic development candidates: 256 crossed pair units per family at
  depths 2 and 3 = 1,024 candidate pair units;
- mechanistic candidate confirmation: 256 crossed pair units per family at
  depths 2 and 3 = 1,024 candidate pair units.

Within every split x family x depth cell:

- correct option labels A/B/C/D are exactly balanced when the cell size is
  divisible by four;
- T-A and T-B are exactly balanced;
- start states, final states, and operation identities are balanced to counts
  differing by no more than one where exact balance is arithmetically
  impossible;
- every registered pre-answer intermediate state is balanced to counts
  differing by no more than one where exact balance is arithmetically
  impossible;
- each option value is distinct;
- the correct option is not inferable above chance from option position, start
  state, final operator identity, template, or any single registered surface
  field. Emit and test the corresponding contingency tables.

Define semantic identity before rendering from family, state space, operator
definitions, start state, operation sequence, option-value set, and registered
ground truth. Require zero semantic-identity overlap across all four roles.
Require zero exact UTF-8 and registered-normalized prompt overlap with every
tracked Phase 1 bank prompt and every vendored official S3 prompt.

7.5 Independent ground-truth verification

Implement the generator and a separately coded verifier. The verifier must
recompute every permutation composition and affine composition from the row's
primitive fields, not call the generator's answer function. It must validate
all intermediates, final states, option mappings, counterfactual answers, and
hashes. A disagreement is a preregistration-integrity blocker, not an item to
drop.

8. Crossed mechanistic pairs

Each pair unit must contain a donor problem and a recipient problem plus
registered controls. Pair construction is model-free.

For each donor/recipient pair define:

- donor intermediate m_d;
- recipient intermediate m_r;
- donor downstream transformation g_d;
- recipient downstream transformation g_r;
- donor answer a_d = g_d(m_d);
- recipient answer a_r = g_r(m_r);
- recombinant answer a_x = g_r(m_d).

Require a_d, a_r, and a_x to be pairwise distinct. The donor and recipient
must share the same four option values in the same value-to-label mapping:
a_d, a_r, a_x, and one additional distractor. Thus the donor-correct,
recipient-correct, and recipient-recombinant option labels are also pairwise
distinct. This is the core anti-answer/value/label-copying constraint. A later
donor-to-recipient activation patch is successful for the primary causal
hypothesis only when it moves the recipient toward a_x, not merely toward a_d
or the donor's correct option label.

Every pair unit must also define:

- a no-op donor identical to the recipient;
- a same-intermediate donor with m_d = m_r but different irrelevant surface
  fields;
- a same-answer/different-intermediate donor whose answer equals a_r but whose
  intermediate differs;
- a deterministic unrelated random donor from the same family/depth/template;
- the recipient's wrong-position byte anchor: the final state-symbol span in
  the `Start:` field, whose exact per-model token index Stage T must freeze;
- exact donor, recipient, and recombinant option labels.

Both Stage P candidate pair banks are larger than their future executable
sets because equal token lengths and aligned answer positions cannot be known
without the three pinned tokenizers. A later tokenizer-only Stage T must,
separately within development and confirmation, order candidate pair units by
the frozen semantic hash and select the first 128 per family x depth cell that
pass all three models' exact length/alignment gate. Thus each later executable
mechanistic split is exactly 128 x 4 = 512 pair units. If either split has
fewer than 128 eligible candidates in any cell, stop before model loading as
BLOCKED_ON_STUDY2_MECHANISTIC_TOKEN_SUPPORT. There is no post-inference
replacement or backfill.

9. Registered prompt arms and observables

9.1 NT: no_trace primary arm

The model receives the registered task prompt ending in `Answer:`. It performs
one forward pass. It generates zero tokens. At the final input position, read
the logits for exactly four registered option-token continuations.

For each model, a later tokenizer-only gate must prove that appending each of
the literal candidate surfaces ` A`, ` B`, ` C`, and ` D` to the exact prompt
adds exactly one distinct token and that removing it returns the exact prompt
token sequence. Failure for any model is
BLOCKED_ON_STUDY2_COMMON_OPTION_TOKENIZATION. Do not substitute digits, words,
or another option alphabet after the gate.

Define restricted option probability:

p(o) = exp(logit(o)) / sum_{j in {A,B,C,D}} exp(logit(j)).

Define restricted prediction as argmax over those four logits, with the fixed
tie order A, B, C, D used only for exact ties. Record the full-vocabulary rank
and full-vocabulary top-1 token as interface diagnostics, but neither controls
eligibility nor replaces the restricted primary observable.

This arm contains no generated or supplied reasoning trace. It may support a
claim about controlled single-forward hidden computation. It cannot establish
spontaneous answer-only generation, natural conversational performance, or an
unobserved natural-language chain of thought.

9.2 PT: partial_correct_trace positive control

For depths 2 and 3, add a programmatically correct external scratch line
containing every intermediate state before the final transformation, then end
with the same `Answer:`. Do not include the final state or option label. Score
the same four option logits in one forward pass. PT is a supplied external
trace control, not hidden reasoning and not model-generated CoT.

9.3 WT: partial_wrong_trace control

Use the same byte structure and number of intermediate-state tokens as PT, but
replace the final supplied intermediate with a registered counterfactual. The
recipient's option set must contain the answer implied by continuing from that
counterfactual. Measure both loss of true-answer probability and pull toward
the counterfactual-implied option.

9.4 ST: shuffled_trace control

For depth 3 only, reverse the order of the two supplied intermediate states.
The token multiset and trace length match PT. This arm tests ordered use rather
than a bag-of-state-token effect.

9.5 No model-generated CoT in protocol v1

Do not add a model-generated visible-CoT arm in this first Study 2 protocol.
It would reintroduce sampling, termination, parsing, and semantic adjudication
as dependencies. Existing external literature and historical Phase 1 rows may
be cited as motivation only; they do not enter a Study 2 denominator.

Any future generated-text extension requires separate authority and DR-01
semantic adjudication. No automatic parser output may become a scientific
label.

10. DR-01 and exact scoring

DR-01 remains binding: a parser may not assign authoritative semantic
correctness to generated text. Study 2 does not create generated output text
in its primary or registered trace-control arms. The task program supplies a
mathematical ground-truth option, and the observable is a numeric four-logit
vector. Restricted argmax accuracy is a derived statistic over registered
numbers, not a semantic parser judgment.

If any later implementation emits natural-language model output, retain it as
diagnostic-only and exclude it from all gates, cell selection, evidence rows,
and claims unless a separate semantic-review authority exists.

11. Prospective stage separation

Freeze this state machine exactly.

Stage P: protocol and banks, this round

- Freeze all identities, banks, formulas, controls, sample sizes, seeds,
  thresholds, and classification truth tables.
- Perform one bounded methods review and at most one consolidated correction.
- Run zero tokenizer/model/lens operation.

Stage T: tokenizer and model-identity gate, later authority

- Fetch only pinned configs/tokenizers and immutable model-file manifests.
- Verify exact model/config/tokenizer revisions and option continuation tokens.
- Verify intermediate digit surfaces for the target J-lens diagnostic.
- Resolve input lengths, answer-position indices, and aligned mechanistic
  pairs without a model forward.
- Separately select the first 128 eligible mechanistic-development and
  mechanistic-confirmation pairs per registered cell by frozen hash order.
- Seal the complete Stage T manifest before any weight load.

Stage B-D: behavioral development, later authority

- Run all three models and all applicable arms on development only.
- Use development only to prove the frozen code computes the registered rows
  and to identify implementation deviations.
- No development result may change a task, template, arm, threshold, option
  surface, sample size, metric, control, or conclusion rule.

Stage B-C: behavioral confirmation, later authority

- Freeze the final execution source/image and complete output schema first.
- Run all 1,536 confirmation items for all three models under NT and all
  applicable trace-control arms.
- Write a closed all-or-nothing row pack and manifest-last artifact.
- Seal all cell metrics and the deterministic mechanistic-cell selection before
  any mechanistic-confirmation activation is computed or opened.

Stage M-D: mechanistic development and localization, later authority

- Use only the Stage T-selected executable mechanistic-development pairs.
- Run a full layer scan at the registered answer-position token for the target.
- Select the target's one primary contiguous three-layer window by the frozen
  algorithm below.
- Seal the selected window and implementation/image before confirmation.

Stage M-C: mechanistic confirmation, later authority

- Open only the preselected 128 pair units for each selected family/depth cell.
- Run the fixed-window causal patching, controls, probes, and target-only
  J-lens diagnostics.
- Confirmation is all-or-nothing. Partial or non-finite packs are operational
  blockers, not negative scientific results.

No stage may be skipped by treating engineering convergence, a development
plot, a full-vocabulary top-1 token, or an old Study 1 row as a substitute.

12. Behavioral metrics and cell selection

For each model x family x depth x template x arm report:

- exact n;
- restricted-option accuracy and Wilson 95% interval;
- mean correct-option restricted probability;
- mean correct-vs-best-incorrect logit margin;
- option-label confusion matrix;
- full-vocabulary rank of each option token as diagnostic;
- input lengths and execution-integrity counts.

Use 10,000 deterministic paired bootstrap replicates for probabilities,
margins, trace effects, and between-model differences. Resample semantic item
IDs within family x depth, keeping model, template, and arm rows paired. Use
the registered bootstrap seed. Do not resample token rows. Every registered
lower/upper 95% bootstrap bound is the 2.5th/97.5th percentile of the ordered
replicates using the canonical JSON's fixed finite-sample quantile rule.

For depths 2 and 3 define:

TRACE_GAIN = p_correct(PT) - p_correct(NT)

WRONG_TRACE_PULL = p_counterfactual_implied(WT)
                   - p_counterfactual_implied(NT)

SHUFFLE_DAMAGE = p_correct(PT) - p_correct(ST)

These are external-trace dependence diagnostics. They do not establish hidden
reasoning.

Define NT_PASS(model, family, depth) only when all are true:

- exactly 256 behavioral-confirmation rows exist;
- execution integrity is complete;
- restricted accuracy point estimate is at least 0.50;
- Wilson lower 95% bound is above chance 0.25;
- paired-bootstrap lower 95% bound of the mean correct-vs-best-incorrect logit
  margin is above zero;
- no option-balance or template-balance invariant failed.

For each family, select at most one mechanistic depth for the target: choose
depth 3 if NT_PASS; otherwise choose depth 2 if NT_PASS; otherwise select no
cell for that family. Tie-breaking and ordering may not use a control-model
result, trace arm, probe, activation, or J-lens output.

The selected cell is target-defined and must be run for all three models. Do
not choose a different best cell for each control. Behavior of both controls
is always reported, even when below floor.

If neither family has a selected depth, do not open mechanistic execution;
finish the registered behavioral and trace-control classification in
Section 16. If only one family is selected, mechanistic work may run for that
family, but the cross-family strong claim is not estimable.

13. Lens-independent causal recombination

Activation patching is the primary mechanistic instrument. It must not use a
J-lens or probe to choose an item, layer, pair, or answer.

For each donor/recipient pair, capture block-output residuals at the final
input token corresponding to the registered `Answer:` position. Patch the
donor residual into the recipient at one layer at a time and continue the
recipient forward pass. Do not patch option-token activations because no option
token has yet been generated.

For recipient option logits define:

M_x = logit(a_x) - logit(a_r)

G_x(layer) = M_x(patched donor->recipient, layer)
             - M_x(clean recipient)

Define donor-answer copying contrast:

M_d = logit(a_d) - logit(a_r)

G_d(layer) = M_d(patched donor->recipient, layer)
             - M_d(clean recipient)

The desired recombination is a_x = g_r(m_d). Because a_x differs from both
a_d and a_r, G_x > G_d distinguishes recipient-side downstream recomputation
from donor final-answer copying.

Run the same formulas for no-op, same-intermediate, same-answer,
same-family random-donor, wrong-position, early-layer, and motor-layer
controls. Emit every row; never select a favorable random donor.

For every control donor or control position c, define G_x^c with the primary
pair's fixed recipient contrast logit(a_x) - logit(a_r); do not replace a_x
with the control donor's own recombinant or answer. This makes every control
ask whether an irrelevant intervention moves the same recipient toward the
same registered recombinant answer.

13.1 Development localization

On target mechanistic-development rows only, compute:

S(layer) = mean_over_pairs[
             G_x(layer) - max(G_d(layer), G_x(random donor, layer))
           ].

Compute S first within each selected family and then take the unweighted
arithmetic mean across selected families. If only one family was selected, use
that family alone. This produces exactly one target-defined window for the
study; it is not a per-family or per-control search.

Among contiguous three-layer windows wholly inside layers 9 through 22,
select the window with the largest arithmetic mean S. Break an exact tie by
the lowest starting layer. This window is frozen before confirmation and used
unchanged for the target and both controls. Per-layer confirmation rows are
still emitted for the selected window and fixed early 0..8 and motor 23..27
control bands. No confirmation result may move or widen the window.

If a pinned control config has a different number of blocks, map the target
window endpoints by exact normalized depth and round half upward; freeze the
mapping at Stage T. Do not select a control-specific peak for a primary
comparison.

13.2 Confirmation causal statistics

Within the frozen window, average item effects equally across its three layers
before the pair-level bootstrap. Define:

PATCH_RECOMBINATION = mean G_x

PATCH_RANDOM_SPECIFICITY = mean [G_x - G_x(random donor)]

PATCH_ANSWER_COPY_SPECIFICITY = mean [G_x - G_d]

PATCH_STRUCTURAL_SPECIFICITY = mean G_x
                               - max(mean G_x(no-op donor),
                                     mean G_x(same-intermediate donor),
                                     mean G_x(same-answer donor))

PATCH_POSITION_SPECIFICITY = mean [G_x(answer position)
                                   - G_x(wrong position)]

PATCH_BAND_SPECIFICITY = mean G_x(middle window)
                         - max(mean G_x(early), mean G_x(motor))

PATCH_PASS(model, family) requires lower 95% paired-bootstrap bounds above zero
for all six quantities. For maxima, compute the maximum inside each bootstrap
replicate before taking its quantile. Top-1 recombinant-option success, KL
divergence, and correct-option probability changes are mandatory secondary
outputs but cannot override these continuous gates.

Alpha-zero/no-op hooks must reproduce clean logits to maximum absolute
difference <= 1e-5 and the same restricted argmax. Failure is an execution
blocker.

14. Cross-template intermediate probe

Probe evidence is secondary to causal patching but required to identify what
the causal state carries.

- Use the final answer-position activation.
- Use only the center layer of the frozen three-layer window.
- Train a multinomial ridge probe with fixed L2 coefficient 1.0 on T-A
  mechanistic-development rows.
- Predict the task-defined final pre-answer intermediate state.
- Test only on T-B mechanistic-confirmation rows.
- Fit separately per model and family; do not pool models.
- Balance intermediate class and final-answer option so that neither predicts
  the other above registered chance from class frequency.
- Run five deterministic intermediate-label permutations and an answer-label
  probe using the same pipeline.

PROBE_PASS(model, family) requires both:

- lower 95% pair-bootstrap bound of intermediate-state accuracy minus its
  class-frequency chance level is above zero;
- lower 95% bound of true-label accuracy minus the mean of five permuted-label
  controls is above zero.

Probe success alone is never internal-reasoning evidence. Probe failure cannot
be hidden when patching is favorable.

15. Fixed target M1200 J-lens secondary axis

Only the target has a pre-existing sealed full-layer J-lens. Study 2 does not
fit a control-model lens in protocol v1. Consequently J-lens output cannot be
the primary between-model instrument.

After behavior, cell selection, localization, and the patching image/source are
sealed, a later M-C authority may load target M1200 with exact seal
9716c3802625176060b3c2a479f7860cf4045807a45c6de346833a3b66e00138.
A600 and B600 are replicate diagnostics; M1200 is primary. Do not choose the
replicate with a favorable result.

At the answer-position activation and frozen target window, report the rank of
the known pre-answer intermediate-state digit under:

- M1200;
- A600;
- B600;
- ordinary logit lens;
- five deterministic intermediate-label permutations;
- five deterministic same-row wrong-position controls.

All state digits are present in every task prompt by construction. Therefore a
favorable rank must beat the label and position controls; raw rank alone can be
prompt echo. Final answer is an option letter, not the intermediate-state digit,
which separates the readout token from the output token.

Use pass@k for k = [1, 2, 5, 10, 20, 50, 100] and normalized trapezoidal AUC
against log(k), with equal family weighting. Do not select the best layer;
average item AUC equally across the frozen three-layer window.

For coordinate swaps, swap the M1200 coordinates of m_r and m_d in the
recipient at the frozen window and measure the same recombinant-answer G_x.
Compare with logit-lens coordinate swaps, five deterministic Gram-matched
random direction pairs, direct donor-answer option-vector swaps, alpha=0, and
wrong-band controls. Use the already frozen items and window.

Define JREADOUT_PASS when the lower 95% item-bootstrap bound of M1200 minus
logit-lens AUC and of M1200 minus each averaged label/position control are above
zero.

Define JCAUSAL_PASS when lower 95% pair-bootstrap bounds of M1200 recombinant
G_x minus logit-lens, Gram-matched random, and direct donor-answer-vector effects
are all above zero.

The J-lens axis is:

- STUDY2_JLENS_VALIDATED if JREADOUT_PASS and JCAUSAL_PASS;
- STUDY2_JLENS_PARTIAL if exactly one passes and all integrity controls pass;
- STUDY2_JLENS_NOT_VALIDATED if neither passes or a hard label/position/answer
  leakage control fails after a complete finite pack;
- STUDY2_JLENS_NOT_ESTIMABLE if token support is absent or the complete
  registered pack cannot be run for a non-scientific operational reason.

This axis cannot promote or demote the lens-independent internal-computation
axis. Only STUDY2_JLENS_VALIDATED may support a Study 2 J-space statement.

16. Frozen scientific classification

Compute three axes, then one composite state.

16.1 Internal-computation axis

INTERNAL_COMPUTATION_SUPPORTED requires, in both task families:

- a selected depth 2 or 3 target cell;
- NT_PASS for the target in that selected cell;
- PATCH_PASS for the target;
- PROBE_PASS for the target.

INTERNAL_COMPUTATION_SUPPORTED_ONE_FAMILY uses the same gates in exactly one
family and is explicitly non-generalized.

BEHAVIOR_ONLY_WITHOUT_CAUSAL_SUPPORT applies when at least one depth 2 or 3
target cell passes NT_PASS, but neither family satisfies the full internal
computation gate after every opened finite mechanistic pack completes.

NO_COMPOSITIONAL_BEHAVIORAL_SUPPORT applies only when no depth 2 or 3 target
cell passes NT_PASS, no family passes PT_SUPPORT, and the target nevertheless
passes NT_PASS at depth 1 in at least one family. This distinguishes failure
of composition from total failure of the registered task interface.

NOT_ESTIMABLE applies only to an operationally incomplete, identity-mismatched,
non-finite, or integrity-failed pack; it is not a scientific negative.

16.2 Distillation-association axis

For the two selected target cells, compare the exact same prompts and frozen
target-defined window across models. Use paired item/pair bootstrap.

DISTILLATION_ASSOCIATION_STRONGER_THAN_BOTH_CONTROLS requires:

- INTERNAL_COMPUTATION_SUPPORTED for the target;
- the lower 95% bound of target minus lineage-base aggregate NT accuracy is
  above zero;
- the lower 95% bound of target minus instruction-control aggregate NT
  accuracy is above zero;
- for each family, lower 95% bounds of target minus each control's
  PATCH_RECOMBINATION are above zero;
- no option-prior, template, random-donor, no-op, same-intermediate,
  same-answer, donor-answer, wrong-position, early-band, or motor-band hard
  control fails.

DISTILLATION_ASSOCIATION_NOT_DISTINGUISHED applies when the target internal
computation axis is supported but one or both prospective checkpoint
comparisons fail to exclude zero.

DISTILLATION_ASSOCIATION_CONTRADICTED applies only when a complete pack shows
both controls exceed the target on the registered aggregate behavior and
causal effects with lower 95% bounds above zero in the reverse direction.

DISTILLATION_ASSOCIATION_NOT_ESTIMABLE applies when the target internal axis is
not supported or a comparative pack is operationally incomplete.

16.3 Composite terminal states

Use exactly these scientific composite states:

- STUDY2_DISTILLATION_ASSOCIATED_CAUSAL_INTERNAL_REASONING_SUPPORTED
- STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_WITHOUT_DISTILLATION_ATTRIBUTION
- STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_ONE_FAMILY_ONLY
- STUDY2_BEHAVIOR_ONLY_WITHOUT_CAUSAL_SUPPORT
- STUDY2_EXTERNAL_TRACE_DEPENDENCE_ONLY
- STUDY2_EXTERNAL_TRACE_SUPPORT_ONE_FAMILY_ONLY
- STUDY2_NO_COMPOSITIONAL_BEHAVIORAL_SUPPORT
- STUDY2_TASK_INTERFACE_UNQUALIFIED
- STUDY2_RESULT_NOT_ESTIMABLE

Define PT_SUPPORT(target, family) when, for at least one depth 2 or 3 cell,
PT accuracy has Wilson lower bound above 0.25 and point estimate at least 0.50,
lower95 TRACE_GAIN > 0, and lower95 WRONG_TRACE_PULL > 0; a qualifying depth 3
cell additionally requires lower95 SHUFFLE_DAMAGE > 0. Choose the deepest
qualifying PT depth only for reporting this trace-control axis; it never opens
mechanistic confirmation or rescues NT.

STUDY2_EXTERNAL_TRACE_DEPENDENCE_ONLY requires no NT_PASS at depths 2/3, but
PT_SUPPORT holds in both families. It means supplied intermediate tokens guide
the checkpoint on these tasks; it does not prove that natural self-generated
CoT is faithful.

STUDY2_EXTERNAL_TRACE_SUPPORT_ONE_FAMILY_ONLY uses the same trace gates in
exactly one family when neither family has NT_PASS. It is explicitly
non-generalized.

STUDY2_TASK_INTERFACE_UNQUALIFIED applies when the target has no NT_PASS even
at depth 1 in either family, has no NT_PASS at depths 2/3, and no family has
PT_SUPPORT. It does not imply absence of reasoning under other tasks or
interfaces.

Apply this exact precedence to obtain one composite state:

1. Any operationally incomplete, identity-mismatched, non-finite, or
   integrity-failed pack required by the stages actually opened under the
   frozen gates -> STUDY2_RESULT_NOT_ESTIMABLE.
2. Internal computation supported in both families and distillation
   association stronger than both controls ->
   STUDY2_DISTILLATION_ASSOCIATED_CAUSAL_INTERNAL_REASONING_SUPPORTED.
3. Internal computation supported in both families without that comparative
   gate, including a contradicted comparison ->
   STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_WITHOUT_DISTILLATION_ATTRIBUTION.
4. Internal computation supported in exactly one family ->
   STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_ONE_FAMILY_ONLY.
5. At least one depth 2/3 target NT_PASS, but internal computation is supported
   in neither family after every opened finite mechanistic pack completes ->
   STUDY2_BEHAVIOR_ONLY_WITHOUT_CAUSAL_SUPPORT.
6. No depth 2/3 target NT_PASS and PT_SUPPORT in both families ->
   STUDY2_EXTERNAL_TRACE_DEPENDENCE_ONLY.
7. No depth 2/3 target NT_PASS and PT_SUPPORT in exactly one family ->
   STUDY2_EXTERNAL_TRACE_SUPPORT_ONE_FAMILY_ONLY.
8. No depth 2/3 target NT_PASS, no PT_SUPPORT, and at least one depth 1 target
   NT_PASS -> STUDY2_NO_COMPOSITIONAL_BEHAVIORAL_SUPPORT.
9. No target NT_PASS at any depth and no PT_SUPPORT ->
   STUDY2_TASK_INTERFACE_UNQUALIFIED.

Operational failures use:

- BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY
- BLOCKED_ON_STUDY2_PREREGISTRATION_INTEGRITY
- BLOCKED_ON_STUDY2_MODEL_IDENTITY
- BLOCKED_ON_STUDY2_COMMON_OPTION_TOKENIZATION
- BLOCKED_ON_STUDY2_MECHANISTIC_TOKEN_SUPPORT
- BLOCKED_ON_STUDY2_EXECUTION

BLOCKED_ON_STUDY2_EXECUTION requires a separate nonempty registered
`blocker_reason` from a closed reason-code enum; do not synthesize terminal
state names at runtime.

An operational blocker never becomes a scientific negative. A complete
scientific negative must be preserved and not repaired by a new task family,
prompt arm, threshold, option alphabet, layer search, or replacement bank.

17. One bounded Study 2 methods review

After the first complete candidate JSON/schema/Markdown/banks/validator exists
and before freeze, compute their exact hashes and perform exactly one methods
review over those bytes. The review asks only:

1. Does NT truly contain zero generated or supplied reasoning tokens while
   measuring a model preference rather than output-format compliance?
2. Are four-option tokens prospectively verifiable in all three tokenizers
   without outcome-dependent substitution?
3. Are task answers, intermediates, distractors, trace arms, and pair
   counterfactuals mechanically unique and independently reconstructible?
4. Are development, behavioral confirmation, mechanistic development, and
   mechanistic candidate confirmation semantically disjoint?
5. Can any task, model, cell, template, item, pair, layer, position, comparator,
   or exclusion depend on confirmation, lens, probe, or intervention output?
6. Do balance and direct-lookup controls distinguish composition from option
   priors and single-surface shortcuts?
7. Does a_x = g_r(m_d), with distinct answer values and shared value-to-label
   mappings, distinguish intermediate transfer from donor-answer or
   donor-option-label copying?
8. Do same-intermediate, same-answer, random-donor, no-op, wrong-position,
   early-band, and motor-band controls cover the stated alternatives?
9. Is target-defined development localization fully separated from
   confirmation and applied unchanged to both controls?
10. Does the probe test a held-out surface template and avoid final-answer
    leakage?
11. Is the target M1200 axis secondary and incapable of selecting or rescuing
    the lens-independent result?
12. Do the two controls support only the registered checkpoint-level
    distillation association, not a stronger training-causal claim?
13. Are DR-01, Study 1 protected bytes, Phase 1.0D, and all old terminal states
    preserved?
14. Are every metric, bootstrap unit, threshold, null, truth-table branch, and
    output row exactly computable from planned fields?
15. Can every positive and negative result be reconstructed from a closed
    row-level pack without semantic interpretation?

Record every finding as FATAL, MATERIAL, or MINOR with exact file/JSON-pointer
references. Permit one consolidated correction of all FATAL/MATERIAL findings.
Then rerun the same checklist only to verify those corrections. Verification
is part of the same review allowance and may identify only a direct
contradiction introduced by the correction.

If a fatal leakage, noncomputable ground truth, invalid causal recombination,
or nonclosed truth table remains, stop as
BLOCKED_ON_STUDY2_PREREGISTRATION_INTEGRITY. Otherwise freeze final bytes and
record that this Study 2 methods-review allowance is spent. Any byte change to
the frozen scientific protocol after tokenizer/model/lens output does not
inherit the review.

18. Required model-free tests and ACR validation

Run focused tests and the full suite in ACR. At minimum prove:

- exact starting commit/tree and all protected-anchor hashes;
- exact model IDs and immutable revisions are present in the protocol;
- canonical JSON/schema/Markdown closure with no placeholders;
- the generator is deterministic across process hash seeds and repeated ACR
  runs;
- exact row/pair counts in every role;
- exact A/B/C/D and T-A/T-B balance;
- state/operator balance within the registered tolerance;
- zero semantic identity overlap across roles;
- zero exact/normalized overlap with Phase 1 and official S3 prompts;
- independent recomputation of every intermediate/final answer;
- a_d, a_r, and a_x are pairwise distinct in every pair unit;
- donor and recipient share the exact option set and value-to-label mapping
  containing a_d, a_r, a_x, and one distinct distractor;
- same-intermediate, same-answer, no-op, and random controls meet their exact
  definitions;
- the Stage T selector depends only on tokenizer mechanics and frozen hashes;
- hand-calculated restricted probabilities, margins, trace effects, Wilson
  intervals, and paired bootstrap examples;
- deterministic cell selection including 127/256 versus 128/256 correct and
  every depth-3/depth-2 precedence case;
- development window selection and lowest-layer tie-break;
- hand-calculated G_x/G_d examples showing recombination, donor-answer copy,
  no-op, and random control cases;
- classification tests cover every combination of internal, distillation, and
  J-lens axes;
- operational blockers cannot produce scientific negatives;
- no transformers, torch, J-lens, model, tokenizer, inference, activation,
  provider, or GPU path is reachable from Stage P validators;
- Phase 1.0D, Study 1, S2, and S3 v1 protected bytes remain unchanged;
- the two historical parser-seal failures remain the only accepted full-suite
  failures.

The starting full-suite reference is:

3485 passed / 15 skipped / 2 disclosed historical parser-seal failures

Report the exact delta. Do not fix the two historical failures under this
authority.

19. Ledgers, claims, and paper boundaries

Append consistent new records to:

- README.md
- docs/decision_log.md
- docs/run_log.md
- docs/literature_notes.md
- paper/methods_ledger.md
- paper/limitations_ledger.md
- paper/claim_evidence_matrix.md
- paper/artifact_index.csv

Allocate the next unused sequential IDs. Do not renumber history. Do not add a
scientific row to paper/evidence_ledger.csv in this design-only round.

The README must state simultaneously:

- Study 1 remains terminal as INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY;
- Phase 1.0D remains independently
  BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY;
- Study 2 is a new prospectively reviewed protocol, not a rescue or rerun;
- Stage P ran zero tokenizer/model/lens/activation operation;
- a frozen Study 2 protocol is not empirical evidence.

Record at least these limitations:

- forced-choice logits measure controlled discriminative preference, not
  spontaneous natural-language behavior;
- synthetic finite-state tasks do not establish broad mathematical, factual,
  agentic, or real-world reasoning;
- three final checkpoints do not isolate the causal contribution of individual
  distillation examples or objectives;
- the base and instruction controls differ in post-training and possibly
  tokenizer/config details;
- supplied PT/WT/ST traces are controlled external traces, not natural
  self-generated CoT;
- activation patching can establish causal influence but not a complete
  human-readable algorithm;
- full-residual transfer carries more than one feature, making recombinant and
  matched controls essential;
- probe decodability alone is not mechanism;
- M1200 was fitted on a WikiText proxy and remains unvalidated until the new
  target-only J-lens axis passes;
- only single-token digit concepts enter the J-lens subaxis;
- public deterministic banks are prospective but not private or
  researcher-blind;
- any one-family result cannot be generalized across reasoning domains;
- no Study 2 outcome modifies Phase 1.0D or retrospectively validates Study 1.

Keep existing CL-02, CL-03, CL-05, and CL-07 honest. Stage P cannot promote
them. Add new prospective Study 2 claims only as unsupported/preregistered
until real confirmation evidence exists.

20. Checkpoints and final handoff

Push each reproducible checkpoint by fast-forward. At the end require a clean
worktree and report:

- exact origin/main, tree, and starting-commit ancestry;
- every commit made, with no amend, rebase, or force-push;
- authority, protocol, schema, Markdown, review, freeze, validator-source, task
  bank, and manifest SHA-256 values and byte counts;
- exact model identities and source references;
- exact task and pair counts, balance summaries, overlap counts, and ground
  truth verification;
- the one review's initial findings and consolidated verification result;
- focused and full ACR run IDs/results and exact baseline delta;
- protected-byte re-verification;
- every file added or changed;
- confirmation that target/control tokenizer constructions, model downloads,
  weight loads, forward passes, generations, semantic-review/provider calls,
  lens loads/fits/applies, activations, probes, patching, ablation, GPU Jobs,
  scientific rows, Phase 1.0D operations, and RQ2/S4 runs are all zero;
- whether the Study 2 methods-review allowance is spent;
- what this design establishes and what remains unmeasured.

Save the exhaustive Stage P handoff at
`studies/study2/STAGE_P_FINAL_HANDOFF.md` and update
`studies/study2/README.md` without changing this authority prompt or the
bootstrap handoff receipt.

The normal successful state for this round is:

NONTERMINAL_CHECKPOINT_STUDY2_PROTOCOL_FROZEN_AWAITING_TOKENIZER_GATE_AND_EXECUTION

The design-round scientific-integrity blocker is:

BLOCKED_ON_STUDY2_PREREGISTRATION_INTEGRITY

Do not return any empirical Study 2 state in this round. Those require later,
separately authorized Stage T, B-D/B-C, and M-D/M-C executions.
