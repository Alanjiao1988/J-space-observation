You are working in the existing GitHub repository Alanjiao1988/J-space-observation.

This authority permits one design-amendment round only. It does not freeze Study 3, generate a task bank, draw a seed, select an interface or reference model, or authorize any model operation.

0. Required endpoint

The round may end only at:

STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW

This is a documentation and model-free statistical-planning state. It is not a preregistration, scientific result, or execution authority.

The operator-review disposition is:

STUDY3_DRAFT_V0_1_REVIEWED_AMENDMENT_REQUIRED_NOT_APPROVED_FOR_FREEZE

1. Authoritative starting state

Before editing, fetch the remote and verify all of the following:

repository: Alanjiao1988/J-space-observation

expected published starting commit: 360086db495c4c5a098e49a6e8adf73dd143eaef

expected starting tree: 23ba838d5f1bc639a9b21b49ba96ac957865dd90

expected parent design-draft start: 783ad360030e9105e87301ac5e3af6346076596e

expected Study 2 bookkeeping correction commit: 1f2a50585b258dc97dbecb7deeff7d426ca5ca53

HEAD, fetched origin/main, the index, and the working tree must be clean and content-identical at the start

branch/worktree names are metadata only; never block merely because the platform chose a different branch name

Study 1 remains INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY

Study 2 remains STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY, documentation state STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE

paper/evidence_ledger.csv must remain byte-identical, still end at EV-0016, and receive no new row

both protected rollups and every frozen Study 1/2 blob must match their registered committed-blob digests

current Study 3 v0.1 files, sizes, hashes, state, and zero operation counts must match studies/study3/design_receipt.json

If the remote moved, the worktree is dirty, a protected digest differs, or the current Study 3 draft cannot be reconstructed from committed blobs, stop and report the exact mismatch. Do not merge, rebase, reset, force-push, repair a protected file, or infer permission from a branch name.

Record the accepted starting disposition:

STUDY3_V0_2_AMENDMENT_STARTING_STATE_ACCEPTED_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE

2. Why amendment is required

The v0.1 design round was executed correctly as a draft-only round. Its source-attribution correction from “Lyu et al.” to Wenjie Zhou, Qiang Wang, Mingzhou Xu, Ming Chen and Xiangyu Duan is correct, and the two additional primary sources were useful. The operator review nevertheless found design defects that prohibit freeze.

The v0.2 documents must record these findings without treating them as scientific evidence:

Markdown/JSON contradiction. The Markdown says A winner is selected in this round: true (that is, no winner is selected), while the JSON correctly says no_winner_this_round: true. The documents therefore do not agree exactly as claimed.

Gate lifecycle contradiction. The selection rule requires I0–I3 but omits I4; I4 nevertheless says an interface “remains eligible.” I4 failure is written as a global study stop even though it is evaluated per interface. I5 omits RP/K4 and therefore does not confirm the key positive-control gate.

Positive-reference circularity and weak floor. Stage P3-Q is not independent if it uses a candidate interface to prove RP capable and then uses RP to validate that interface. A chance-null I4 threshold of 49/128 (0.3828) is not a positive-capability floor.

Robustness construct mismatch. Aggregate accuracy equivalence can pass while the model changes its answer on many individual items. The design needs a pre-registered item-level content-consistency measure. S2/S3 do not show options, so option-position and label-permutation transformations are structurally inapplicable to them and cannot be counted as zero effect or automatic passes.

Statistics incomplete. The paired binary equivalence method is not operationally specified, the multiplicity family is not mapped to the actual hypotheses, and n=192 has no I3 power analysis. For paired binary equivalence, power depends on discordance/correlation; the existing binomial tables do not establish I3 feasibility.

Pooling and cell ambiguity. K1 and K2, primitive families, and K4 depths/families can be pooled under the current prose even though the lifecycle forbids cross-stratum rescue. A strong family/depth can mask a failed one.

Panel and selection contradiction. S4 is described as calibration-only and “never the default later surface” but can win the current ranking. For single-token candidate contents, S3 and S2 have the same argmax under the same prefix, so S3 is not an independent scoring surface unless a multi-token domain is actually registered.

Counterbalancing ambiguity. Four cyclic option orders do not by themselves separate physical position from option-label identity. The proposed 1/2/3/4 replacement can collide with a mod-10 answer domain. K6 also inconsistently describes three renderings while varying separator, instruction and answer cue.

Study 1 overstatement. Study 1 established that its frozen raw-completion/single-token interface yielded too few behaviorally eligible items. Parser-v2 also failed its own gate. It did not establish that parsing caused the terminal E0 eligibility collapse. Study 3 may inherit the need to validate an interface, but must not convert an unresolved cause into a fact.

Reproducibility gap. The ephemeral static checker missed the Markdown/JSON contradiction. Design-critical semantic checks and statistical derivations now need committed, reviewable tests/scripts.

Do not edit v0.1 history to hide these defects. Record them additively as operator-review findings, then amend the mutable draft.

3. Absolute operation boundary

This round must add exactly zero of every empirical/model operation:

model downloads: 0

weight loads: 0

tokenizer constructions: 0

forward passes: 0

generations: 0

activation operations: 0

hooks: 0

probes: 0

patching: 0

ablations: 0

lens loads/fits/applies: 0

GPU jobs: 0

provider/model API calls: 0

bank rows: 0

seeds drawn: 0

Study 3 result rows: 0

scientific evidence rows: 0

Phase 1.0D or RQ2/S4 operations: 0

Allowed computation is limited to CPU-only parsing, hashing, schema validation, exact model-free arithmetic, deterministic generation of design tables from declared numeric assumptions, repository tests, Git inspection, and English-language primary-source verification.

No GitHub Actions. Do not run local pytest as evidential validation. Use clean Azure ACR CPU builds/jobs for the final validation envelope, as in prior rounds. Local read-only inspection and non-evidential arithmetic are allowed but must be disclosed.

4. Required design architecture in draft-v0.2

4.1 Source of authority and semantic parity

Increment the draft version from draft-v0.1 to draft-v0.2.

Keep frozen=false, execution_authorized=false, review_state=awaiting_independent_methods_review, and successor_authority=none.

Make the JSON draft authoritative for machine state and structured gate definitions. The Markdown is the human-readable companion.

Remove the unsupported claim that Markdown and JSON were generated from one source unless a committed deterministic generator actually enforces that claim.

State unambiguously in both files: no winner is selected in this or any prior Study 3 round.

Add committed tests that fail if state, frozen/authorized flags, no-winner status, interface selectability, gate applicability, operation counters, unresolved blockers, or claim ceiling disagree between the JSON and the required Markdown markers.

4.2 Separate an interface profile from a scoring formula

Each candidate must be defined as a complete profile containing:

prompt/rendering contract

whether answer options are visible

whether option labels are visible

scoring formula

tokenizer eligibility rule

output-validity rule

chat/wrapper policy by role

applicable gates

explicitly non-applicable transformations

selectable/non-selectable status for a later substantive study

projected operation counts

An inapplicable transformation is NA, not a pass, not zero effect, and not an input to ranking.

Use the following operator dispositions:

S1 label_token_logits: selectable if and only if all applicable binding, primitive, positive-reference and robustness gates pass.

S2 answer_content_logits: selectable and preferred when the complete frozen answer domain is jointly single-token eligible for every required Study 2 role. It receives rendering-robustness gates, but label/option-position gates are NA when options are absent.

S3 content_conditional_loglikelihood: conditional. If every candidate content is one token under the same prefix, record that its argmax is analytically identical to S2 and derive it from the same logits as an integrity check; do not count four new sequence scorings. S3 may become selectable only if a later frozen task domain contains multi-token candidates and a dedicated multi-token stratum, boundary-token rule and length-confound gate are defined before any bank exists.

S4 bounded_minimal_generation: retain as a non-selectable diagnostic reference only. It can never be the development-selected future interface. Its data may diagnose divergence but may not rank S1–S3.

Replace the data-dependent ranking with a fail-closed pre-registered admissibility order:

S2, if applicable and eligible;

S3, only if its multi-token applicability condition is met and it is eligible;

S1, if eligible;

S4 is never selectable.

The order is a proposed v0.2 operator disposition, still subject to the independent methods review. Do not select a winner now.

4.3 Task strata and atomic cells

Define the base item as the independent sampling unit. All permutations/renderings of one base item are a correlated cluster and must remain in the same split.

Define every gate-bearing atomic cell explicitly. At minimum, include:

interface profile

checkpoint role

task stratum

operation family

depth

rendering condition, where applicable

label/position condition, where applicable

split

Prohibit pooling as a rescue across K1/K2, operation families, depths, roles, surfaces, or rendering conditions. Pooled summaries are descriptive only.

K1 must measure explicit content-to-symbol binding only for label-bearing profiles.

K2 must measure trivial content recovery/copy separately from K1.

K3 must gate each primitive family required by a later study separately; a pooled K3 total cannot pass a failed family.

K4 must gate each required composition family and depth (2 and 3) separately. Depth 2 cannot rescue depth 3, and one family cannot rescue another.

Do not generate any item, fixture, seed or bank in this round.

4.4 Counterbalancing and rendering

Replace the ambiguous K5 design with a deterministic orthogonal or explicitly justified balanced design that separates, as far as the chosen design permits:

correct-content physical position

displayed option-symbol identity

label alphabet

The design may use a full factorial or a tested Latin/Graeco-Latin construction, but it must publish the exact construction algorithm and prove exact balance before freeze. Do not silently treat label and position as the same factor.

Requirements:

label alphabets must be disjoint from the answer-content domain

1/2/3/4 is forbidden when answers can be mod-10 digits

candidate label strings must later pass a joint tokenizer-eligibility gate at their exact prefix boundary; no tokenizer is constructed now

all variants of one base item remain in one split

label-set replacement must be crossed or balanced with position; one ad hoc replacement condition is insufficient

Resolve OD4 as exactly three K6 renderings:

baseline;

separator-only change;

instruction-wording-only change.

Hold the answer cue and every other byte constant. If a later reviewer wants answer-cue variation, it becomes a fourth registered condition and requires a new cost/multiplicity calculation; do not smuggle it into the three-condition set.

4.5 Revised gate hierarchy

The exact IDs may be I1a/I1b or equivalent, but the logic must be machine-readable and unambiguous.

I0 — deterministic integrity

Keep the 100% finite-fixture gate. Expand committed tests so every scorer/profile, NA applicability branch, label mapping, invalid output and tie path is exercised.

I1a — trivial content recovery and output validity

inputs: K2 and any surface-appropriate explicit-content fixtures

evaluated separately per interface and required role

content-based profiles are tested as content recovery, not mislabeled as symbol binding

S4 output validity is substantive; forced logit surfaces have validity 1 only if the harness and candidate set are valid

I1b — explicit content-to-symbol binding

inputs: K1

applies only to label-bearing profiles

evaluates each required role separately

profiles with no labels receive NA, never an automatic pass

retain a conservative high binding floor provisionally, but leave final alpha/sample-size resolution under OD5/OD6

I2 — primitive headroom

evaluated per required role × primitive family × interface

no family pooling

the current H0: p <= 0.50, n=192 proposal may be retained as a provisional value, but it is not frozen and must be justified as an instrument floor rather than a claim of downstream compositional ability

I3 — applicable robustness

Use two distinct quantities:

Primary item-level content consistency. For each base item, map every surface response back to answer content and record whether the predicted content is invariant across all applicable irrelevant transformations. Use an exact binomial lower-bound/floor gate on the base-item consistency indicator. Consistent wrong answers cannot rescue low accuracy because I1/I2 remain conjunctive.

Secondary aggregate equivalence. If retained, specify an established paired-correlated-proportions method, its exact or score-based confidence interval, nuisance/discordance assumptions, hypothesis family, and executable algorithm. A non-significant difference is never equivalence.

Selected-label uniformity may remain a supporting gate for label-bearing profiles only. It is NA for content-only profiles. Define whether it is a gate or diagnostic; do not alternate between the two.

Do not assert n=192 is adequate for I3 until the committed planning script produces power/sensitivity results under declared discordance scenarios.

I4 — independently qualified positive-reference recovery

I4 is evaluated per candidate interface and must be included in interface eligibility.

RP must first be justified and, if required, prequalified using a separate canonical qualification interface that is not one of S1–S4, uses new disjoint qualification items, follows the RP model card/native wrapper, and is frozen before qualification.

P3-Q may establish that RP can solve the task family under that independent canonical interface. It may not rank S1–S4.

RP must also clear surface-compatibility/trivial recovery checks under each candidate interface before its K4 result is interpretable.

I4 must be evaluated separately by composition family and depth.

Reject the current chance-null floor p0=0.25, X=49/128 as sufficient positive-control evidence. Replace it with a proposed competence floor expressed as a lower confidence bound; use p_floor=0.80 as the v0.2 planning proposal, not a frozen decision, and recompute n/X/power under the eventual family alpha.

failure eliminates that interface. The study stops only if no selectable interface remains eligible. A single surface failing I4 must not close the whole study if another preregistered surface passes.

I5 — one-shot confirmation

I5 must confirm every gate-bearing construct used to select the interface, including I4 on RP/K4. The confirmation bank therefore contains disjoint confirmation draws for K1–K6 as applicable, including RP/K4 family × depth cells.

one selected interface only

no re-selection or fallback on confirmation

confirmation files physically absent before the separate release authority

any failure spends the bank

pass/fail still authorizes no mechanistic work

4.6 Positive-reference decision (OD2)

OD2 remains blocking. Do not download, tokenize, load or prequalify a model in this round.

Create a primary-source candidate dossier. Evaluate at least:

Qwen/Qwen3-4B-Instruct-2507 as the recommended T4-feasible first candidate: official materials state 4.0B parameters, non-thinking mode, Apache-2.0 availability through the Qwen3 release, and materially stronger math/instruction performance than smaller predecessors. Record that it requires transformers>=4.51.0, so the current Study 2 transformers 4.46.3 image cannot be reused unchanged. Its exact repository revision, tokenizer behavior and short-sequence fp16 T4 margin remain unmeasured.

Qwen/Qwen2.5-Math-7B-Instruct as a stronger same-generation alternative: official materials report strong MATH performance and native chat-template use, but its approximately 8B-parameter BF16 weights are not a safe fp16 fit on a 16-GiB T4 with activation/KV overhead. It would require a larger GPU. Do not use quantization merely to force a fit because the interfaces read logits.

Primary references to verify and record include:

https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507

https://arxiv.org/abs/2505.09388

https://huggingface.co/Qwen/Qwen2.5-Math-7B-Instruct

https://qwenlm.github.io/blog/qwen2.5-math/

The dossier may recommend Qwen3-4B-Instruct-2507 for a future single-candidate P3-Q, but it must not select or pin RP. P3-Q must later preregister exactly one candidate, immutable revision, runtime, dtype, native wrapper, qualification interface, bank, floor, sample size and stopping rule before any model operation.

No automatic 3B→7B fallback is allowed. If the preregistered candidate fails, P3-Q stops. Trying a different candidate requires a new authority and a fresh qualification bank. This removes adaptive reference shopping.

4.7 Statistical specification and committed planning instrument

Add a committed, dependency-minimal design-statistics script and committed tests. They are model-free and may perform only declared arithmetic.

The script must:

reproduce every retained exact binomial threshold and power value

calculate proposed I4 thresholds under competence floors, not chance

define the atomic hypothesis families and alpha allocation

distinguish intersection-union/conjunctive components from surfaces among which any one may be selected

produce a paired-binary equivalence/consistency sensitivity table over at least discordance rates 0.05, 0.10, 0.20 and 0.30

state the target power and demonstrate whether each proposed n can or cannot support the chosen I3 margin

fail closed if the declared paired method cannot be implemented and reproduced exactly

write no bank, item, seed, model output or result artifact

Add an appropriate primary statistical methods source for paired correlated binary equivalence, such as:

Toshiro Tango, “Equivalence Test and Confidence Interval for the Difference in Proportions for the Paired-Sample Design,” Statistics in Medicine 17 (1998), 891–908

Liu et al. (2002), “Tests for equivalence or non-inferiority for paired binary data,” as cited by the correlated-proportions method documentation

Do not label a method “exact paired TOST” without an executable definition and verified type-I/power behavior.

Create a bounded independent-methods-review packet containing only:

estimands and atomic units

all null/alternative hypotheses

gate truth table and stop states

multiplicity/selection logic

proposed margins/floors

power/sample-size sensitivity tables

unresolved statistical choices

a checklist for an independent reviewer

OD5 and OD6 remain blocking after this amendment unless the independent review has already occurred outside this authority, which it has not. The expected v0.2 state is therefore awaiting that review.

4.8 Resolve the eight operator decisions as follows

Record these dispositions explicitly in Markdown and JSON:

OD1 — resolved: retain RT, RL and RI. All three are required for the later distillation/lineage/instruction contrast; each gate is per role.

OD2 — unresolved/blocking: candidate dossier only; no RP selected.

OD3 — resolved: retain S4 only as non-selectable diagnostic.

OD4 — resolved: three one-factor renderings as specified above; answer cue fixed.

OD5 — unresolved/blocking: I1/I2 proposals may remain provisional; I3 method/margins and I4 competence floor require independent review. The chance-floor I4 proposal is rejected.

OD6 — unresolved/blocking: n=192 may remain a provisional I1/I2 value, not an I3 justification; confirmation and I3 sizes await the reviewed power analysis.

OD7 — resolved: a bounded independent review of statistics and gate logic is mandatory before freeze and before any bank/seed.

OD8 — resolved in part: no chat template for RT/RL/RI on S1–S3; S4 uses each role’s native template or explicitly records its absence. The RP canonical qualification wrapper and RP-specific I4 wrapper remain part of OD2 and must be frozen before P3-Q/I4. Do not claim cross-role byte parity where native wrappers differ.

4.9 Study 1 and Study 2 wording

Correct only mutable Study 3 prose. Do not edit Study 1 or Study 2 files.

Use the accurate statement:

Study 1’s frozen raw-completion, no-chat-template, single-token E0 surface yielded too few behaviorally eligible items to populate confirmation. Parser-v2 separately failed its locked gate, while parser-v3 remained nonauthoritative. These facts motivate prospective interface validation but do not establish that parsing caused E0’s eligibility collapse.

Study 2 remains closed and unchanged. Its post-hoc response-pattern diagnostic remains zero-authority motivation only.

5. Required artifacts

Create or update a coherent v0.2 packet. Exact filenames may follow repository conventions, but the following logical artifacts are required:

additive operator-review record for v0.1 with the ten defects above and disposition AMENDMENT_REQUIRED

amended Markdown protocol draft-v0.2

amended JSON twin draft-v0.2

amended structural schema with fail-closed enums/required fields for applicability, selectability, gate eligibility, unresolved blockers and zero counters

committed model-free design-statistics derivation script

committed Study 3 design tests, including deliberate negative mutations

bounded independent-methods-review packet

positive-reference candidate dossier based on primary sources

updated research-charter draft, traceability, README and next-thread handoff

new v0.2 design receipt binding all new/modified Study 3 artifacts from committed blobs

preserved verbatim copy of this authority under studies/study3/prompts/

normal additive updates to current-status, run/decision/methods ledgers and artifact index

Use the next available contiguous IDs after current D38, M-26, and AR-0195; inspect the registries rather than assuming no concurrent update. Do not add an evidence row. Add a limitation entry only if repository convention requires one for an unresolved design limitation; do not misclassify operator-review defects as empirical findings.

6. Mutable-path whitelist

Before editing, resolve and print an exact path whitelist. It may contain only:

existing mutable Study 3 draft/routing files under studies/study3/

new Study 3 review, dossier, methods-review, script, test, receipt and authority files under studies/study3/

one new or existing dedicated Study 3 design test under tests/

README.md

studies/README.md

reports/current_status.md

docs/decision_log.md

docs/run_log.md

paper/methods_ledger.md

paper/limitations_ledger.md only if justified as above

paper/artifact_index.csv

Do not modify:

any path under studies/study1/ or studies/study2/

paper/evidence_ledger.csv

any frozen Stage P/T/B-D artifact, seal, bank, manifest, row file or decision

protected rollup inputs

model/runtime source used by past studies

dependencies or container images in this round

GitHub workflows

If a required change falls outside the whitelist, stop and request a new authority. Do not broaden scope silently.

7. Validation requirements

Validation must be run from clean Azure ACR CPU-only clones bound to the exact commits. At minimum:

focused Study 3 design tests, including the new committed test

existing Study 2 focused regression tests

the full repository suite, accepting only the two already registered historical test_parser_v3_seal_job failures if and only if the count and identities are unchanged

committed schema validation of the v0.2 JSON

committed semantic-parity checks for the required Markdown markers

statistical derivation script in check mode, reproducing every table byte-for-byte or value-for-value

negative mutation tests that must reject at least:

frozen=true

execution_authorized=true

any nonzero operation counter, including an injected new counter key

winner selected

S4 selectable

I4 absent from eligibility

I5 omitting RP/K4

an NA gate counted as pass or zero effect

cross-family/depth pooling enabled

RP selected

OD2, OD5 or OD6 marked resolved

confirmation accessible before authority

claim ceiling removed

a bank row, seed, model result or evidence row injected

exact changed-path whitelist check

committed-blob size/SHA-256 verification for every new artifact

unchanged Study 1/2 protected bytes, both rollups and EV-0016

The previously ephemeral checker may be used only as a secondary operator instrument. It cannot substitute for the newly committed design-critical tests. Disclose every failed command and distinguish operator invocation error from test failure.

8. Commit and publication discipline

Preserve a clean worktree before every evidential validation.

Use small, auditable commits. At minimum separate the operator-review record from the amended protocol/test packet and the final run-log/handoff update.

Re-fetch immediately before publication.

Require the remote parent to be the fetched expected predecessor; if it moved, stop.

Publish only with a non-force fast-forward explicit refspec to refs/heads/main.

Never rename/switch/merge/rebase/reset solely to satisfy a platform branch name.

Post-push fetch and verify HEAD == origin/main, tree identity, clean worktree, artifact hashes, rollups and EV-0016.

9. Required final response

Return a complete handoff headed:

STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_2_COMPLETE_AWAITING_INDEPENDENT_METHODS_REVIEW

Include:

final commit and tree

ancestry and fast-forward publication proof

exact changed-path list and counts

artifact IDs, paths, sizes and full SHA-256 values

operator-review defects and how each was resolved or left blocking

exact OD1–OD8 dispositions

revised interface applicability/selectability table

revised I0–I5 truth table and legal stop states

statistical tables and explicit statement that OD5/OD6 remain unresolved

RP dossier conclusion and explicit statement that OD2 remains unresolved

committed test/script paths and mutation-test results

focused/full/static validation results bound to the final commit

exact zero operation counters for this round

unchanged Study 1/2 states, protected rollups and EV-0016

remaining authority: independent methods review only; no freeze, P3-Q, seed, bank, tokenizer, model, GPU, development, confirmation or mechanism work

Do not provide a freeze or execution prompt. The next legal action after this round is independent review of the v0.2 statistical and gate packet.