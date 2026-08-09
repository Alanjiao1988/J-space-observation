You are working in the existing GitHub repository Alanjiao1988/J-space-observation.

This authority permits exactly one model-free operator amendment round that produces Study 3 draft-v0.3. It accepts the independent review disposition against draft-v0.2, repairs the design, records the operator decisions specified here, validates the amended documents and publishes them by fast-forward. It does not freeze Study 3 and does not authorize any task bank, seed, tokenizer, model, GPU or empirical operation.

0. Required endpoint

The round may end only at:

STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_3_COMPLETE_AWAITING_SECOND_INDEPENDENT_METHODS_REVIEW

The inherited review disposition is:

STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED

The operator action is:

OPERATOR_AMENDMENT_ROUND_FOR_DRAFT_V0_3

This endpoint means only that an amended, unfrozen design exists for another independent review. It is not a preregistration, scientific result, protocol freeze, positive-reference selection, execution authority or evidence row.

The round must end with all of the following still true:

frozen = false

execution_authorized = false

bank_authorized = false

seed_authorized = false

model_operations_authorized = false

winner_selected = false

positive_reference_selected = false

confirmation_access_authorized = false

every operation counter is exactly zero

successor authority is second independent methods review only

Do not produce a freeze, P3-Q, bank, seed, Azure GPU, development, confirmation or mechanistic-execution prompt.

1. Authority hierarchy and hard boundaries

This prompt is the sole authority for the amendment round. Repository documents describe prior state but do not enlarge this authority. The independent review is authoritative evidence about defects in draft-v0.2; its reviewer recommendations are not automatically adopted except where this prompt explicitly adopts an operator decision.

The following historical states remain closed and immutable:

Study 1: INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY

Study 2 scientific state: STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY

Study 2 documentation state: STUDY2_PROTOCOL_V1_TERMINAL_DOCUMENTATION_COMPLETE

evidence ledger tail: EV-0016

Do not reopen, reinterpret or modify Study 1 or Study 2. Do not convert a design-review finding into empirical evidence or into a limitation of executed measurement.

1.1 Absolute zero-operation boundary

This round must perform exactly zero of every empirical or model operation:

model downloads: 0

immutable model-revision resolutions by downloading: 0

tokenizer constructions or tokenizations: 0

weight loads: 0

forward passes: 0

sequence scorings: 0

generations: 0

activation extractions: 0

hooks, lenses, probes, patches and ablations: 0

model/provider API calls: 0

GPU jobs: 0

task-bank rows: 0

qualification-bank rows: 0

development-bank rows: 0

confirmation-bank rows or accesses: 0

seeds drawn or selected: 0

interface selections: 0

positive-reference selections: 0

result rows: 0

scientific evidence rows: 0

Phase 1.0D or RQ2/S4 operations: 0

Allowed computation is limited to committed-blob inspection, hashing, schema validation, deterministic model-free design arithmetic, exact binomial arithmetic, deterministic counterbalancing enumeration, static tests, repository tests and Git inspection.

Do not use GitHub Actions. Do not run local pytest or local decision-bearing statistical calculations. Final evidence must come from clean CPU-only Azure ACR jobs bound to exact commits. Local read-only inspection, document assembly, syntax checking and non-authoritative debugging are permitted only if disclosed precisely in the receipt and final handoff.

2. Mandatory starting-state preflight

Start in a fresh Copilot CLI session/worktree based on remote main. Branch and worktree names are non-authoritative metadata.

Fetch the remote and independently verify from committed blobs:

repository: Alanjiao1988/J-space-observation

expected published starting commit: e4bcda3a487ea9c9a085e3943103a07501014431

expected starting tree: fa1246fb72232212e29fced7e37dbef971601cfc

reviewed draft-v0.2 commit: 8a2c4a0b2a73c5d802988333f11ea6c22828f6f5

reviewed draft-v0.2 tree: 7e9077a32903adfdaa3bede95beba8752fcb5133

the compare 8a2c4a0…e4bcda3 is a strict forward history with exactly 17 changed paths: 8 added and 9 modified

independent-review disposition: STUDY3_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED

review state: STUDY3_DRAFT_V0_2_INDEPENDENT_METHODS_REVIEW_COMPLETE_AWAITING_OPERATOR_ACTION

review counts: 20 findings = 6 BLOCKING + 11 MAJOR + 3 MINOR

candidate inconsistency adjudication: 6 CONFIRMED_BLOCKING, 8 CONFIRMED_NONBLOCKING, 1 NOT_CONFIRMED, 2 QUALIFIED

current registry tails: D40, M-28, AR-0221

paper/evidence_ledger.csv is byte-identical to the reviewed start, has 16 rows and ends at EV-0016

both protected Phase 1.0D rollups and all registered Study 1/2 protected blobs match their committed identities

every Study 3 operation counter is zero; there is no bank, seed, winner, selected profile, selected RP or confirmation access

HEAD, fetched origin/main, index and working tree are clean and content-identical at the start

Verify the independent-review authority copy as a committed blob:

path: studies/study3/prompts/study3_v0_2_independent_methods_review_authority.md

bytes: 34624

lines: 931

SHA-256: ec207bb595490417078ec904c71f6bb1fda2035006dded8488a2f9071dad4968

LF only, zero CR bytes, no trailing newline

Re-read the review Markdown, JSON, schema, receipt, independent recalculation and tables from the starting commit. Do not rely only on this prompt's summary.

If the remote moved, a protected digest differs, the worktree is dirty, the review object is inconsistent, or the starting state cannot be reconstructed exactly, stop with:

BLOCKED_ON_STUDY3_V0_3_AMENDMENT_STARTING_STATE_INTEGRITY

Do not merge, rebase, reset, cherry-pick, force-push or repair a protected historical object.

On success, record:

STUDY3_V0_3_AMENDMENT_STARTING_STATE_ACCEPTED_CONTENT_IDENTITY_BRANCH_METADATA_NONAUTHORITATIVE

3. Required reading and immutable review history

Read at minimum:

studies/study3/reviews/v0_2_independent_methods_review.md

studies/study3/reviews/v0_2_independent_methods_review.json

studies/study3/reviews/v0_2_independent_methods_review.schema.json

studies/study3/methods_review_receipt_v0_2.json

studies/study3/analysis/independent_methods_recalculation.py

studies/study3/analysis/independent_methods_recalculation_tables.json

all current protocol, statistics, packet, traceability, dossier, receipt and routing files under studies/study3/

tests/test_study3_design.py

tests/test_study3_methods_review.py

the current decision, methods, run and artifact registries

The following are immutable historical review objects in this round and may not be edited:

all three reviews/v0_2_independent_methods_review.* files

methods_review_receipt_v0_2.json

both independent_methods_recalculation* files

the v0.2 independent-review authority copy

analysis/independent_methods_review_packet.md as the exact packet that the reviewer reviewed

design_receipt_v0_2.json

every v0.1 artifact and review record

The mutable protocol, planning script/tables, dossier, traceability and tests may be amended because that is the purpose of this round. Git history preserves their reviewed v0.2 bytes. Update tests/test_study3_methods_review.py so historical-review identity assertions read the reviewed objects at 8a2c4a0… or the completed review state at e4bcda3…, as appropriate, rather than incorrectly requiring future working-tree versions of mutable draft files to equal v0.2. This is a commit-addressing repair only: it may not alter the review disposition, finding text, counts or recalculated values.

4. Operator decisions adopted for draft-v0.3

These are design decisions, not measurements. They are adopted into the amended draft but remain subject to the second independent methods review.

4.1 I3 estimand and presentation construction

Replace the undefined all-transformations cluster with pre-registered pairwise contrast clusters.

The independent sampling unit for I3 is a base_item_contrast_cluster. Each cluster contains exactly one base item rendered in exactly two variants:

the registered baseline for that contrast cell;

one registered, content-equivalent transformed presentation.

Therefore:

variants_per_base_item_contrast_cluster = 2 for every applicable profile and contrast cell

a base item belongs to exactly one contrast cell and one split

base-item identities are disjoint across contrast cells within a split

K5 and K6 use disjoint base-item identities

K5 and K6 are not crossed

there is no implicit 32 × 3, 16 × 2 × 3, 96 variants per item or other factorial multiplication

S2/S3 have zero K5 variants because K5 is not_applicable, not because it passed

every rendered/scored row must be derivable as base_item_contrast_clusters × 2

K5: seven one-factor label/position contrasts

K5 applies only to label-bearing S1 and diagnostic S4. Use two registered label alphabets disjoint from the answer domain, for example A/B/C/D and W/X/Y/Z. Digits remain forbidden.

Publish executable deterministic pseudocode and committed tests for exactly seven contrast IDs:

K5-P1, K5-P2, K5-P3: move the correct content by offsets +1, +2 or +3 modulo four while holding the correct displayed-symbol index and label alphabet fixed within the pair

K5-S1, K5-S2, K5-S3: change the correct displayed-symbol index by offsets +1, +2 or +3 modulo four while holding the correct physical position and label alphabet fixed within the pair

K5-A1: replace the label alphabet while holding physical position and correct-symbol index fixed within the pair

For every contrast cell, balance baseline physical position, correct-symbol index and alphabet over complete blocks. Define the distractor option order and the remaining symbol assignment deterministically so each emitted option list is a bijection and the ground-truth mapping is preserved. No random draw is permitted in this design round.

The seven cells test registered one-factor contrasts only. Explicitly state that combined-factor interactions are outside the Study 3 claim ceiling. Do not imply full-factorial robustness.

K6: two pairwise contrasts drawn from three registered renderings

Retain the global K6 rendering set:

R-base

R-sep: separator only changes

R-instr: instruction sentence only changes

The answer cue and every other byte remain fixed. Operationalize it as two disjoint contrast cells:

K6-SEP: R-base versus R-sep

K6-INSTR: R-base versus R-instr

Each base item appears in only one K6 contrast cell, so each cluster still has exactly two variants. For S1/S4, baseline label/position conditions are balanced across base items and held fixed within each pair. K6 applies to S1–S4; K5 is NA for S2/S3.

4.2 I3 indicators

For every I3 base-item contrast cluster publish all three indicators:

J_inv = 1 iff both variants produce a valid answer-domain content and the two mapped contents are byte-identical after the registered content mapping; stable invalid/unparseable output is 0

J_cor = 1 iff both variants are scored correct against the unique registered ground truth; a stable but wrong answer is 0

J_both = J_inv AND J_cor

J_both is the primary I3 gate indicator. J_inv and J_cor are reported separately so presentation sensitivity and competence failure remain visible. Under a unique ground truth, J_cor logically implies J_inv; record this as an expected integrity invariant rather than pretending the two are independent. The explicit conjunction is retained to make stable-wrong and stable-invalid semantics fail closed.

The I3 estimand is, separately in every applicable atomic contrast cell:

Pr(J_both = 1) over independently sampled base-item contrast clusters.

Never pool K5/K6, contrast IDs, source strata, operation families, depths, roles, profiles, alphabets, position/symbol conditions or splits to rescue a failed component.

4.3 OD5 — statistical decision rules

Adopt an exact-binomial primary design and retire the Tango aggregate-equivalence procedure from all decision authority.

Development family

Fix the selectable-profile denominator at K = 3 before data. S1, S2 and S3 all count in K even when S3's activation condition is not met. S4 is excluded because it is permanently non-selectable.

Use:

study-level development screening alpha: exact rational 1/200 = 0.005

per-profile development component alpha: exact rational 1/600 = 0.001666666666…

every exact-binomial component within a profile is tested at 1/600

within-profile gates/cells are an intersection-union conjunction: every applicable component must pass, so no further within-profile Bonferroni correction is applied

across profiles, qualification of any one profile is a union event protected by the fixed denominator 3

Republish every threshold, tail probability, power figure and sample size from the committed model-free script at the implemented alpha. Decimal fields are renderings of exact rational policy, not the source of truth.

The second reviewer must reproduce, to declared tolerance, these reviewer-returned development targets:

gate

unit of n

n

p0

p1

pass count

exact null tail

power at p1

I1a

base items per atomic cell

256

0.90

0.97

244

0.001491215117

0.953040775

I1b

base items per atomic cell

256

0.90

0.97

244

0.001491215117

0.953040775

I2

base items per primitive-family cell

128

0.50

0.70

82

0.000931234262

0.938986365

I3

base-item contrast clusters per contrast cell

256

0.90

0.97

244

0.001491215117

0.953040775

I4

RP base items per operation-family × depth cell × candidate profile

256

0.80

0.90

224

0.001081002486

0.921083515

These are planning targets, not observed values and not frozen values. The committed script must independently derive them; copying constants without re-derivation is a test failure.

I4 is a conjunction over every registered operation family and depth. Each component uses 1/600; no pooling is allowed and no extra correction is needed inside the intersection-union profile claim. RP identity remains unselected under OD2.

Retirement of the paired aggregate-equivalence decision

Remove the Tango score procedure, the four-point discordance grid, equivalence margins, critical values and any conservativeness/verified-size statement from:

I3 gate authority

profile eligibility

development selection

confirmation

claim language

If paired summaries are retained, they are descriptive only: report the paired 2×2 table, raw discordance and paired accuracy difference for each contrast cell. They carry no null, alpha, p-value, confidence-based pass/fail, equivalence declaration, rescue path or ranking weight.

This is the operator resolution of S3MR-004/S3MR-005: the uncontrolled asymptotic rule is not repaired because it is unnecessary for the primary construct; it is removed from inferential use. Preserve the independent review's recalculation as immutable historical evidence. The second reviewer must explicitly adjudicate whether this retirement fully removes the size-control defect.

4.4 OD6 — floors and sample sizes

Adopt one I3 floor only:

null floor p0 = 0.90

lowest alternative of interest p1 = 0.97

target power >= 0.90

development n 256 base-item contrast clusters per applicable contrast cell

Delete p0 = 0.95 from all active protocol, table and packet fields. It may appear only in the historical review/findings narrative, clearly labelled rejected/unreachable. No active rejection region may have a pass count equal to n.

Adopt I1a/I1b n=256, I2 n=128 and I4 n=256 as in the table above. Every symbol n must carry a unit at its definition and in every table. Never use one n for base items, contrast clusters, rendered rows and scored rows.

4.5 OD2 remains unresolved

Do not select, prefer, pin, download, tokenize, load or prequalify any RP checkpoint. The existing candidate dossier may retain candidates but must say UNSELECTED and correct both D-07 back-references to D-04.

The v0.3 protocol must nevertheless freeze the methods requirements that any later OD2 authority must satisfy:

immutable checkpoint revision, runtime, dtype and wrappers

canonical qualification interface external to S1–S4, not merely a separate bank

qualification bank, floor, n, alpha, multiplicity and stop rule fixed before any model operation

no adaptive fallback or reference shopping

P3-Q demonstrates capability only under the external canonical interface

I4 separately tests whether each candidate Study 3 profile recovers that independently established competence

failure of one profile's I4 eliminates that profile, not every profile

the selected RP and wrappers must later be frozen before any P3-Q or I4 execution

OD2 remains blocking after v0.3 and is not resolved by a statistical design amendment.

5. Required gate, selection and confirmation architecture

5.1 Atomic cells and units

Redefine an atomic gate component so that variants live inside a cluster and do not masquerade as independent cells.

At minimum record:

interface profile

checkpoint role

source stratum

operation family, where applicable

depth, where applicable

contrast family and contrast ID, where applicable

label alphabet/position/symbol balancing block, where applicable

split

independent-unit type

independent-unit count

variants per independent unit

rendered-row count

scoring-operation type

For I3, rendering/label variants are repeated observations inside a base_item_contrast_cluster; the binomial observation is J_both once per cluster. For I1/I2/I4, the binomial observation is one base item. The projection may count rendered or scored rows but may never call those counts n.

Add explicit pooling prohibitions across the two label alphabets and across K5 position/symbol contrast cells, in addition to every existing prohibition.

5.2 I0–I4

I0: deterministic renderer/mapping/scorer fixtures; 100%; includes every pairwise contrast constructor, NA branch, tie, invalid/unparseable path and indicator truth table. No model.

I1a: exact-binomial trivial content recovery, per profile × required role × applicable cell, using K2 and the adopted development parameters.

I1b: exact-binomial explicit content-to-symbol binding on K1, label-bearing profiles only. S2/S3 are NA, never pass.

I2: exact-binomial primitive headroom separately per profile × role × primitive operation family. No family pooling.

I3: exact-binomial J_both separately for every applicable K5/K6 contrast cell and every required role/source family/depth. K5 is NA for S2/S3. J_inv/J_cor and descriptive paired tables cannot rescue J_both.

I4: exact-binomial RP recovery separately per candidate profile × registered operation family × depth. Every component must pass. RP must already have valid external P3-Q evidence under a later authority; no such evidence exists now.

Update every checkpoint-role record from stale I1 labels to I1a/I1b with profile applicability.

Selected-label uniformity is a diagnostic nuisance report only in v0.3. It has no gate, eligibility, selection or confirmation authority. Rename any interval fields to state the actual two-sided tail convention; do not place half-alpha numbers under a field called one-sided alpha.

5.3 Development selection map

Publish one executable pre-data map:

Compute the applicable development component pass/fail vector for S1, S2 and S3 at per-profile alpha 1/600; S4 is diagnostic only.

S3 remains in the fixed denominator 3 under every outcome. Under the current one-token domain it is an integrity check and cannot be selected independently of S2.

Form the eligible set only from profiles that meet every applicable gate and every pre-data applicability condition.

Select at most one profile by the fixed order S2 → S3 → S1.

S3 may occupy its position only if a future pre-data authority has activated a multi-token domain and every existing S3 activation condition; otherwise skip it while keeping denominator 3.

If no selectable profile is eligible, stop. Do not choose S4 and do not change the denominator.

Development data may not alter the order, applicability definitions, denominator, thresholds or confirmation plan.

No profile is selected in this amendment round.

5.4 I5 one-shot confirmation

Specify I5 completely. It confirms the single development-selected profile on a physically disjoint, one-shot confirmation bank under a later authority.

Use a separate confirmatory component alpha 1/200 = 0.005. Because the development selection map is fixed before data, exactly one profile enters the independent confirmation split, the claim is conditional on that selected profile, and no reselection is permitted, no across-profile Bonferroni is applied in confirmation. Within the selected profile, every applicable component is conjunctive and each is tested at 0.005.

Register these confirmation planning rules and make the committed script derive them:

construct

unit of n

n

p0

p1

expected pass count at alpha 0.005

I1a/I1b

base items per atomic cell

256

0.90

0.97

243

I2

base items per primitive-family cell

128

0.50

0.70

80

I3

base-item contrast clusters per contrast cell

256

0.90

0.97

243

I4

RP base items per operation-family × depth cell

256

0.80

0.90

222

The values are planning expectations and must be independently recomputed in ACR. Publish exact null tails and power values in the tables.

I5 passes only if every applicable I1a/I1b/I2/I3/I4 component passes. There is no pooling, retry, fallback profile, bank extension or threshold change. An ambiguous, incomplete or infrastructure-failed confirmation spends the split. Confirmation files remain physically absent and inaccessible until a separate release authority. A pass licenses only the bounded interface-calibration claim for the named profile/tasks/roles and no mechanistic, representational, reasoning, distillation, J-space or causal claim.

6. Operation accounting and S3

Resolve S3MR-012/S3MR-013 explicitly.

Under the current single-token answer domain:

S3's ranking is analytically identical to S2 under the same prefix

S3 is an integrity check, not an independently selectable surface

S3 reuses the S2 forward/logit result

additional S3 model forward passes = 0

additional S3 sequence-scoring rows = 0

any derived comparison is CPU arithmetic on the same recorded logits in a future authorized run

A hypothetical future multi-token S3 activation is outside the current projection and requires a new authority, image, scoring contract and cost table. Do not mix that hypothetical cost into v0.3.

Republish the projection in separate, reconciled work streams:

deterministic I0 fixtures

target-role development (RT/RL/RI)

positive-reference external P3-Q, with numeric count null/unresolved because OD2/bank are not selected

RP I4 under candidate profiles

selected-profile one-shot confirmation

S4 diagnostic generation

For each stream report separately:

base items

base-item contrast clusters

variants per cluster

rendered rows

scored rows

model roles

forward-pass/logit-read accounting

generated-token upper bound where applicable

The committed statistics/planning script must derive every total from protocol constants and assert dimensional identities. A single undifferentiated total is prohibited. Projection is not authorization or budget approval.

7. Required closure matrix for all review findings

Create a human- and machine-readable operator-amendment record mapping every finding S3MR-001 through S3MR-020 to exactly one v0.3 resolution, changed fields/paths, validation assertions and residual review question.

At minimum the matrix must show:

S3MR-001: identifiable pairwise cluster; exactly 2 variants; no cross-product; unit published

S3MR-002: J_inv, J_cor, J_both; stable-wrong and stable-invalid fail

S3MR-003: exact rational 1/600 implemented in every development component and table

S3MR-004: false conservativeness assertion removed; Tango has no decision authority

S3MR-005: four-point grid removed from active verification; second reviewer asked to adjudicate retirement of inferential paired testing

S3MR-006: one active I3 floor, p0=0.90; n=256; p0=0.95 historical only

S3MR-007: every threshold table names p0 explicitly; no mixed-null table

S3MR-008: I1a/I1b n=256 at implemented alpha with >=0.90 power

S3MR-009: active verification independently derives exact-binomial rules and tests the pairwise construction; no self-selected-row or fixed-grid assertion

S3MR-010: K5 stale cyclic/digit text replaced by the seven pairwise contrasts

S3MR-011: K6 answer cue held fixed; two pairwise cells from three renderings

S3MR-012: S3 current single-token cost fixed at zero additional forwards/scorings beyond S2

S3MR-013: projection decomposed by work stream and dimensional unit

S3MR-014: every n has a unit; rendered/scored rows never called n

S3MR-015: no active degenerate rejection region; p0=0.95 row removed from active design

S3MR-016: Family B denominator fixed at 3 before data and never shrinks

S3MR-017: I5 and development selection fully executable before data

S3MR-018: role records use I1a/I1b with applicability

S3MR-019: two-sided tail convention named correctly

S3MR-020: both dossier references corrected from D-07 to D-04

Also map and disposition all UR-01 through UR-22. OD2-related items may remain UNRESOLVED_BLOCKING_OPERATOR_DECISION; no statistical or semantic defect may be silently relabelled resolved. The amendment record may state that a repair is proposed resolved subject to independent review; it may not self-approve the protocol.

8. Required artifacts and exact mutation ceiling

The changed path set must be exactly the following 26 paths: 6 added and 20 modified. No rename or deletion.

8.1 Six added paths

studies/study3/reviews/v0_3_operator_amendment.md

studies/study3/reviews/v0_3_operator_amendment.json

studies/study3/reviews/v0_3_operator_amendment.schema.json

studies/study3/analysis/independent_methods_review_packet_v0_3.md

studies/study3/prompts/study3_v0_3_design_amendment_authority.md

studies/study3/design_receipt_v0_3.json

8.2 Twenty modified paths

studies/study3/README.md

studies/study3/RESEARCH_CHARTER_DRAFT.md

studies/study3/NEXT_THREAD_HANDOFF.md

studies/study3/protocol/interface_calibration_protocol_draft.md

studies/study3/protocol/interface_calibration_protocol_draft.json

studies/study3/protocol/interface_calibration_protocol.schema.json

studies/study3/analysis/design_statistics.py

studies/study3/analysis/design_statistics_tables.json

studies/study3/analysis/study2_to_study3_design_traceability.md

studies/study3/references/methods_sources.md

studies/study3/references/positive_reference_dossier.md

tests/test_study3_design.py

tests/test_study3_methods_review.py

README.md

studies/README.md

reports/current_status.md

docs/decision_log.md

docs/run_log.md

paper/methods_ledger.md

paper/artifact_index.csv

Any need to touch a 27th path is a hard stop requiring new authority. Do not modify:

any Study 1 or Study 2 path

paper/evidence_ledger.csv

paper/limitations_ledger.md

paper/claim_evidence_matrix.md

any v0.2 independent-review object listed in section 3

any prior authority or receipt other than the mutable routes listed above

dependencies, lockfiles, Dockerfiles, runtime/model source, infrastructure or workflows

protected rollup inputs or frozen artifacts

Commit this authority verbatim at the required prompt path. Preserve LF bytes and report its committed-blob bytes and SHA-256. Do not add a header, wrapper or trailing commentary to the committed authority.

Inspect registries and allocate only the next contiguous IDs after the verified tails. Expected next IDs begin at D41, M-29 and AR-0222, but the fetched registries are authoritative. Add no EV row and no limitations row.

The v0.3 receipt must bind every new/amended Study 3 core artifact by committed-blob bytes and SHA-256, record all zero counters and explicitly separate:

paths observed at the receipt commit

prospectively declared tail paths such as the artifact index/run log if committed later

the final independently observed changed-path set

Do not claim a receipt observed a future commit.

9. Committed validation requirements

9.1 Design/statistics tests

Update committed tests so a clean ACR run proves at least:

JSON/schema/Markdown state parity for draft-v0.3

no frozen/authorized/selected state

exact zero operation counters, including rejection of an injected new nonzero counter key

exactly 2 variants per applicable I3 contrast cluster

no K5×K6 cross-product

K5 seven-cell deterministic balance and bijective option/label mappings

K6 two pairwise cells, fixed answer cue and disjoint base-item identities

K5 is NA for S2/S3 and never counted as pass

J_inv/J_cor/J_both truth tables, including stable-wrong, stable-invalid, one-correct/one-wrong and both-correct cases

base-item cluster split integrity and no identity reuse across contrast cells

exact rational development alpha 1/600 in every component

fixed Family B denominator 3, including when S3 is inactive

every development exact-binomial threshold and power row is derived rather than copied

one active I3 floor p0=0.90 and no active p0=0.95 row

no degenerate rejection count equal to n

no Tango/grid/margin field carries gate, selection, confirmation or claim authority

I4 family/depth conjunction and no pooling

executable development selection map and fixed tie-break

full I5 nulls, alternatives, n units, alpha, rejection rules and no-reselection lifecycle

confirmation component alpha 1/200 and independently derived expected pass counts

S3 current-domain zero incremental cost and fixed denominator membership

work-stream projection identities and units

every S3MR finding and UR item appears exactly once in the amendment matrix

OD2 remains unresolved and no checkpoint/model revision is selected

S4 remains diagnostic and never selectable

claim ceiling is preserved

no bank, seed, model result, evidence row or confirmation content exists

Negative mutations must be rejected for each corresponding invariant.

9.2 Historical-review regression

tests/test_study3_methods_review.py must continue to validate the v0.2 review at its reviewed/review commit identities after mutable draft files change. Its tests must read historical committed blobs by explicit commit, not compare mutable HEAD files against v0.2 hashes. It must still prove:

disposition and counts unchanged

all 20 findings and 22 checklist answers unchanged

review authority and receipt identities unchanged

the 17-path review-round ceiling against 8a2c4a0…e4bcda3

the original reviewed design bytes at 8a2c4a0…

review outputs at e4bcda3…

The amendment must not make the historical review pass by weakening assertions or changing expected findings.

9.3 ACR-only validation envelope

Run from clean CPU-only python:3.11-bookworm ACR clones bound to exact commits. Use one test path per ACR invocation; the known --set TESTS="a b" word-splitting behavior must not be used to claim two modules ran.

At minimum run:

tests/test_study3_design.py

tests/test_study3_methods_review.py

studies/study3/analysis/design_statistics.py --check

Study 2 Stage T focused regression

Study 2 Stage B-D focused regression

both protected Phase 1.0D byte modules

full repository suite

a static committed-blob/path/digest audit of all 26 changed paths and every new AR row

The full suite may accept only the same two registered historical test_parser_v3_seal_job failures, with identical identities. Any new failure, changed skip count without explanation, or unbound run is a stop.

Run the focused and full envelope on the actual final publication candidate commit, not only on its parent. Disclose every failed ACR run and every operator-side defect; distinguish invocation/environment failures from repository failures. Never claim a commit was validated by a run bound to another commit.

10. Commit and publication discipline

Use small additive commits with auditable messages.

Preserve v0.2 review history; amend only the exact 26 paths.

Before each decision-bearing validation, require a clean worktree and bind the exact commit/tree.

Re-fetch remote main immediately before publication.

Require fetched remote main to remain exactly e4bcda3a487ea9c9a085e3943103a07501014431 and a strict ancestor of the candidate.

If remote moved, stop; do not merge/rebase/cherry-pick/reset or overwrite concurrent work.

Publish only with non-force explicit fast-forward refspec: git push origin HEAD:refs/heads/main.

Never force-push.

Post-push fetch and verify HEAD == origin/main, exact tree, clean worktree, exact 26-path set, committed artifact hashes, both rollups and EV-0016.

11. Required final handoff

Return a complete handoff headed exactly:

STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_3_COMPLETE_AWAITING_SECOND_INDEPENDENT_METHODS_REVIEW

Include:

final commit and tree

ancestry and fast-forward proof

exact 26-path list and 6-added/20-modified counts

new decision/method/artifact IDs and full committed-blob sizes/SHA-256 values

byte identity of the committed authority

starting-state proof and protected-byte proof

explicit statement that the v0.2 review was accepted as a valid rejection and was not edited

a 20-row S3MR closure summary and all UR dispositions

exact I3 pairwise construction and J_inv/J_cor/J_both semantics

development and confirmation statistical tables with units, tails and power

OD5 and OD6 operator dispositions, labelled proposed and awaiting independent review

explicit statement that OD2 remains unresolved and no RP was selected

fixed denominator/selection/I5 lifecycle

decomposed operation projection and S3 accounting

focused, historical-review, statistics, protected-byte and full-suite ACR results bound to the final commit

every failed invocation or corrected operator-side defect

every operation counter at zero

Study 1/2 unchanged and evidence ledger still ending at EV-0016

frozen=false, execution_authorized=false, no bank, seed, winner, RP or confirmation access

only legal next action: a fresh-session second independent methods review of draft-v0.3

Do not execute that second review in the drafting session. Do not predeclare its disposition. Do not provide or execute any freeze, P3-Q, bank, seed, model, GPU, development, confirmation or mechanistic prompt.