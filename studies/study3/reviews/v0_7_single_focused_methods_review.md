# Study 3 draft-v0.7 — single independent focused methods review

> **Verdict:** `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`
>
> Twelve BLOCKING and three MAJOR findings. No repair was implemented, no v0.8
> or v0.7.1 was drafted, no amendment was proposed, and this review did not
> continue into freeze or execution. Zero reviewed-candidate paths and zero
> historical protected paths were changed.

| item | value |
| --- | --- |
| reviewed commit | `459d002442641039196ac3880d47a45a3b79a4c8` |
| reviewed tree | `2c84d55e6a965972e7cd3f69e3b0cded0bddfb04` |
| reviewed parent | `b9cddfc3a4c57a55bfef6105702be914c2545da1` |
| review authority | [`../prompts/study3_v0_7_single_focused_methods_review_authority.md`](../prompts/study3_v0_7_single_focused_methods_review_authority.md) |
| machine-readable form | [`v0_7_single_focused_methods_review.json`](v0_7_single_focused_methods_review.json) |
| schema | [`v0_7_single_focused_methods_review.schema.json`](v0_7_single_focused_methods_review.schema.json) |
| independent recalculation | [`../analysis/independent_methods_recalculation_v0_7.py`](../analysis/independent_methods_recalculation_v0_7.py) |
| recalculation tables | [`../analysis/independent_methods_recalculation_tables_v0_7.json`](../analysis/independent_methods_recalculation_tables_v0_7.json) |
| review tests | [`../../../tests/test_study3_v0_7_focused_review.py`](../../../tests/test_study3_v0_7_focused_review.py) |
| receipt | [`../methods_review_receipt_v0_7.json`](../methods_review_receipt_v0_7.json) |

## 1. Independence and starting integrity

This reviewer did not draft draft-v0.7, its consolidated-amendment authority,
its copy-on-write successor authority, its protocol builder, its amendment
artifacts or its tests.

Verified before any review output was produced:

* repository `Alanjiao1988/J-space-observation`;
* `HEAD == fetched origin/main == 459d002…`;
* tree `2c84d55…`, parent `b9cddfc…`, clean worktree;
* exactly three linear commits ahead of `5b961cb42bada34a88a7895f83ccb2af4e5690e5`,
  with zero merge commits in that range;
* the changed-path set is exactly the thirteen disclosed additions plus one
  additive `studies/study3/README.md` modification (20 insertions, 0 deletions);
* `paper/evidence_ledger.csv` ends at `EV-0016`;
* `formal_execution_authorized == false`.

The current Git DAG establishes ancestry, parent count and the absence of merge
commits. It cannot establish an historical force-push count, and no such claim is
made here.

The review authority was saved byte-for-byte, committed alone as the first commit
after the reviewed target, and published before any finding was created:
16,515 bytes, SHA-256
`83d5d21975601ad99b505ed7e35dad263fb453e503752ebf2b5d5f78c12f7c5b`, Git blob
`428af94069adffb9636499313405d7c1153445ab`, LF only with no BOM and exactly one
trailing newline, commit `66fec8af948e4c21c6818d0007bd2b3619738b4e`, tree
`d717130936e4bd7537fe0862f3d6a7826fe7b283`.

## 2. What was reproduced, and what did not reproduce

The independent recalculation imports no external package and none of
`v0_7_protocol_build.py`, `design_statistics.py` or `scoring_boundary_v0_6.py`.
It implements the exact one-sided binomial in integer arithmetic over a common
denominator and reduces once, so every comparison below is exact and no
floating-point tolerance is used.

**Reproduced exactly — 74 agreements.** All six exact-binomial component rows,
their minimal pass counts, null tails and powers:

| stage | component | p0 | p1 | alpha | n | pass | exact null tail | exact power |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| development | I1a+I1b+I3 | `9/10` | `97/100` | `1/600` | 413 | 389 | 0.001664632930 | 0.999129439838 |
| development | I2 | `1/2` | `7/10` | `1/600` | 214 | 129 | 0.001597676081 | 0.999042859186 |
| development | I4 | `4/5` | `9/10` | `1/600` | 448 | 383 | 0.001620609599 | 0.999005509196 |
| confirmation | I1a+I1b+I3 | `9/10` | `97/100` | `1/200` | 413 | 388 | 0.003020762720 | 0.999609916012 |
| confirmation | I2 | `1/2` | `7/10` | `1/200` | 214 | 127 | 0.003765544908 | 0.999646587923 |
| confirmation | I4 | `4/5` | `9/10` | `1/200` | 448 | 381 | 0.003582895662 | 0.999626931069 |

Every pass count is confirmed minimal at its level. The registered `n` values are
confirmed to be the true minimal sample sizes at the registered per-cell power
target `17181/17200` — 413, 214 and 448 respectively — by exhaustive upward
search, not by bisection.

Also reproduced: the gate-bearing cell census for all four profiles derived
independently from the gate truth table and the registered `evaluated_per` factor
structure (S1 43, S2 16, S3 16, S4 39); `m_max = 43`; the per-cell false-negative
budget `19/17200`; the per-cell power target `17181/17200`; the profile-stage
power floor `381/400`; the study end-to-end power floor `9/10`; the registered
alternative gap `7/100`; the restricted chance level `1/10`; the negative-control
bound `17/100`; the wrapper descriptive bandwidth `7/100`; and the generated-CoT
ceiling row, which is byte-for-byte the I2 development row.

**Did not reproduce — 6 mismatches.** The S2 and S3 target-role development
projection:

| field | committed | independent |
| --- | ---: | ---: |
| S2 `base_item_contrast_clusters` | 826 | 413 |
| S2 `cluster_rendered_rows` | 1,652 | 826 |
| S2 `rendered_rows_per_target_role` | 2,493 | 1,667 |
| S3 `base_item_contrast_clusters` | 826 | 413 |
| S3 `cluster_rendered_rows` | 1,652 | 826 |
| S3 `rendered_rows_per_target_role` | 2,493 | 1,667 |

826 is `2 × 413`. The committed projection is derived from two applicable I3
contrasts for S2 and S3, while the census, the power architecture, the gate truth
table and the v0.6 registry all record one. This is finding S3V07-B05.

## 3. Mutation results

All mutation work was done in a temporary detached `git worktree` at the reviewed
commit. The reviewed worktree was never modified.

**Artifact-only mutations — 16 applied.** Fifteen were accepted by the committed
schema; only `frozen`/`execution_authorized` was rejected, by two `const`
clauses. Two also passed the entire committed test module: setting the
amendment's `zero_operation_boundary.forward_passes` to 4,096 and
`confirmation_accesses` to 1, and rewriting the amendment's generated-CoT `theta`
to `1/10` and pass count to 108.

**Coordinated mutations — 7 applied, 7 survived.** A coordinated mutation edits
`v0_7_protocol_build.py`, runs it with `--write`, and then runs the committed test
module. This is the path an author actually takes. All seven regenerated cleanly
and all 58 tests passed:

| id | decision-bearing change | tests |
| --- | --- | --- |
| C01 | generated-CoT route marker `<think>` → `<REASONING>` | 58 passed |
| C02 | E0 answer token count 2 → 5, so `max_new_tokens` 3 → 6 | 58 passed |
| C03 | shakedown `max_gpu_hours` 0 → 40 | 58 passed |
| C04 | RP-B ladder ordering rule → operator judgement at seal time | 58 passed |
| C05 | manifest inclusion glob → a glob matching nothing | 58 passed |
| C06 | negative-control chance level `1/10` → `4/10`, bound `17/100` → `47/100` | 58 passed |
| C07 | `sole_top_level_normative_protocol` → the legacy JSON the loader forbids | 58 passed |

`test_the_bundle_reproduces_byte_exactly_from_its_generator` re-runs the drafting
party's own generator and compares bytes. It measures drift between artifact and
generator, not whether a value is defensible, which is why every coordinated
change passes.

## 4. Historical preservation and full-suite differential

Independently verified at the reviewed target:

* the legacy protocol trio hashes equal the registered values;
* `p0_freeze_corpus.py --check` → the committed frozen P0 corpus reproduces byte-exactly;
* `p0_protocol.py --check` → the committed P0 protocol reproduces byte-exactly;
* `design_statistics.py --check` → `DESIGN_STATISTICS_CHECK_OK sections=20`;
* `v0_7_protocol_build.py --check` → `STUDY3_V0_7_BUNDLE_REPRODUCES=1 files=10`;
* the placement-probe output is still reproducible;
* `tests/test_study3_v0_7_protocol.py` → 58 passed.

Full suite at the review head: **7 failed, 4,926 passed, 16 skipped**. The same
seven node IDs fail at the base commit `5b961cb…`:

* `tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last`
* `tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix`
* `tests/test_phase1_0d_build_provenance.py::test_the_bundle_digest_ignores_the_checkout_line_endings`
* `tests/test_phase1_0d_generation_launcher_rp_compat.py::test_shim_has_valid_bash_syntax_and_frozen_launcher_remains_in_baseline`
* `tests/test_phase1_0d_protected_bytes.py::test_line_endings_do_not_change_the_rollup`
* `tests/test_phase1_0d_review_image.py::test_v2_refuses_a_rehashed_record_with_moved_metadata`
* `tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only`

These are standing failures of the review host's checkout, not of draft-v0.7:
they are byte-identical in signature at `5b961cb…` and at `459d002…`, and none
touches a v0.7 path. **New failures introduced by v0.7: 0.** They are reported
here separately and they hide no v0.7 failure.

## 5. Findings

Severity counts: **12 BLOCKING, 3 MAJOR, 2 MINOR.** Full evidence for each
finding is in the JSON form; this section states each finding, its authority
section and its effect. **The reviewer implemented no repair for any finding.**

### BLOCKING

**S3V07-B01 — Two active fields name different top-level normative protocols.**
`§5.1, §5.4.` `status.authoritative_artifact` names the legacy unversioned
`interface_calibration_protocol_draft.json` as "the authoritative record of this
design", while `protocol_placement_v0_7.sole_top_level_normative_protocol` names
the v0.7 JSON and the pointer sets
`must_not_load_interface_calibration_protocol_draft_json = true`. The same field
names `tests/test_study3_design.py` as the agreement enforcement test; that file
contains zero references to v0.7 and two to the legacy JSON.

**S3V07-B02 — The active bundle omits the normative v0.6 rendering registry.**
`§5.1.` The v0.7 registry declares the v0.6 scoring boundary "normative and
inherited byte-identically by reference" and `provenance_v0_7` lists it with role
"normative v0.6 scoring and rendering registry", but it is in neither the
pointer's four-file `active_bundle` nor the amendment's seven-file `new_bundle`,
while `must_resolve_only_to_the_versioned_v0_7_bundle = true` and
`fallback_to_legacy_permitted = false`. The v0.7 registry is 3,243 bytes and holds
no stems, instructions, separators, label alphabets, answer cue, placeholders,
encoding policy, token accounting or scoring boundary; the v0.6 registry is 57,331
bytes and is the only committed home of all of them, declares itself governed by
the legacy protocol, and supersedes the v0.5 registry. An executor cannot recover
every active scoring and rendering rule from the active bundle, which
`provenance_v0_7.self_contained = true`,
`executor_must_layer_amendments_manually = false` and
`legacy_and_v0_6_are_provenance_inputs_not_runtime_overlays = true` all deny.

**S3V07-B03 — OD2 remains blocking and the RP-B ladder is not deterministic.**
`§5.2.` `blocking_decisions = ["OD2"]`; OD2 is `unresolved`, `blocking: true`, and
blocks freeze. The ladder is `blocked_on: OD2`, its length `L` is deferred to
`DEFER-02`, and `ladder.priority` cites "the predeclared Qwen-family size ladder",
which has no referent anywhere in the protocol: the only Qwen strings are three
`checkpoint_roles` target identities. The candidate universe is three generic
family descriptions with no observation date and no source, and three of the five
eligibility predicates require operator judgement. `L`, and therefore the
Bonferroni denominator, varies between equally compliant operators.
`numerical_closure_v0_7.operator_discretion_clause_count = 0` is false.

**S3V07-B04 — The state machine integrates no v0.7 gate and reuses `Q0`.**
`§5.3.` `state_machine_v0_4` is byte-identical to the legacy v0.5 key and contains
nine states. Nothing registers a state, transition or guard for the shakedown
exit, the generated-CoT ceiling, E0, D0's descriptive-only branch, Q0 RP-B
qualification, RP-M validation, wrapper joint adequacy, negative-control
equivalence or the activation boundary. `Q0_INSTRUMENT` ("run only the
deterministic, model-free I0 fixtures") collides by name with v0.7's
model-executing Q0. `total: true` and
`exactly_one_legal_next_state_per_event: true` are therefore false for v0.7.

**S3V07-B05 — K6-SEP applicability is contradictory, and the S2/S3 projection is
arithmetically wrong.** `§5.4, §5.9.` Four locations record K6-SEP as
`not_applicable` for S2 and S3; `gate_hierarchy[I3].claim_ceiling_by_profile` and
`gate_hierarchy[I3].not_applicable_semantics` record it as applicable. The
committed operation projection is derived from the two-contrast figure, and the
six mismatches in section 2 are the exact consequence. 35 of the 40 carried-forward
top-level keys are byte-identical to the legacy protocol — including
`gate_hierarchy`, `gate_truth_table` and `operation_boundaries` — so the claimed
v0.5 re-derivation "in every location" never happened and v0.7 copied the
contradiction forward.

**S3V07-B06 — Wrapper arms are not identifiable.** `§5.5.` Each wrapper is
registered only by `role`, `arm`, `wrapper_id`, `chat_template_applied` and a
prose `description`. No message roles or ordering, literal content, separators,
newlines, BOS/EOS handling, generation-prompt behaviour, chat-template revision or
bytes, RL few-shot demonstrations, or the exact field allowed to differ inside a
within-role pair is registered anywhere. The canonical RT and RI arms depend on a
chat template carried by a checkpoint revision that is deferred and unsealed. No
wrapper asset exists in the repository and the manifest seal registers no wrapper
path, so the exact rendering cannot be reconstructed before data.

**S3V07-B07 — Wrapper joint adequacy doubles the census that `m_max` ignores.**
`§5.9.` The wrapper gate is `joint_adequacy` over two arms, so every gate-bearing
cell must be evaluated twice, yet `atomic_evaluation_cells.cell_factors` has no
wrapper factor and `m_max = 43` counts one arm. Independently recomputed: `m_max`
becomes 86, the per-cell power target rises from `17181/17200` to `34381/34400`,
and the minimal sizes rise from (413, 389), (214, 129) and (448, 383) to
(439, 413), (225, 135) and (477, 407). The registered sizes therefore do not
attain the registered power floors once the second arm is counted, and the
operation projection contains no stream for the wrapper arms, E0, the CoT ceiling,
the negative control or Q0/RP-B.

**S3V07-B08 — The negative-control rule is a margin, not a design.** `§5.8.` The
block has four keys. It registers no independent unit, sample size, pass count,
multiplicity family, expected null distribution or operation projection; its alpha
is "the registered development alpha" while two different development alphas
(`1/200` and `1/600`) are registered; and no confidence-bound construction is
named. The bound `17/100` is independently reproduced and remains unexecutable.
The block also carries no decision marker.

**S3V07-B09 — The E0 token contract is a universal claim over unpinned
tokenizers.** `§5.6.` "Every registered surface is exactly two tokens under the
pinned role tokenizers" and `max_new_tokens = 3` are asserted while the per-surface
token-id sequences are deferred to `DEFER-01` and the revisions are unsealed. E0
is the primary gate for RP-B, whose candidates are unknown under OD2. A four-part
functional-test failure is classified `isomorphic_reinstantiation`, but that
stratum has no separately frozen legal-surface contract, no separate
generation-length contract, no ineligibility declaration and no fail-closed state
for "a registered surface is not two tokens".

**S3V07-B10 — The generated-CoT ceiling has no population and no resource bound.**
`§5.7.` The ceiling registers thresholds, `k`, aggregation, parser id, route marker
and granularity, but no exact task population or stratum, no generator or bank
relationship and no operation or resource upper bound; none of the 17 registered
development sampling cells is the ceiling's cell. Independently recomputed, the
null floor `1/2` is distinct from the critical accuracy
`129/214 = 0.602803738318` and from the registered restricted chance level `1/10`.
The construct is transplanted from I2 — a restricted two-token exact-match readout
over stratum K3 primitives — onto free generation with a required `<think>` route
marker, a different parser and a per-item generation length up to the whole
remaining context. `DEFER-03` bounds nothing: it is per item, per checkpoint, not
comparable across checkpoints and absent from every projection.

**S3V07-B11 — Schemas do not constrain decision-bearing values, and coordinated
changes pass every validator.** `§5.10, §5.12.` 52 of the v0.7 protocol schema's 62
top-level properties are the empty schema `{}`, including `gate_hierarchy`,
`gate_truth_table`, `competence_floor_battery_v0_7`, `blocking_decisions`,
`state_machine_v0_4` and `recursive_manifest_seal_v0_7`. `generated_cot_ceiling_v0_7`
constrains booleans but not `theta`, `n` or `pass_count`; `numerical_closure_v0_7`
constrains counters but not `derived_constants`; the amendment schema leaves
`zero_operation_boundary` a bare object. 15 of 16 artifact-only mutations validate;
7 of 7 coordinated mutations pass all 58 tests. `test_the_schema_is_fail_closed`
asserts only `additionalProperties: false` and two `const` values.

**S3V07-B12 — The recursive-manifest seal is not a sealed inclusion policy.**
`§5.11.` `inclusion` is ten conceptual nouns with no paths;
`inclusion_path_globs` is four globs that omit the current pointer and its schema,
the normative v0.6 registry, parser, renderer, runner and scoring code, task banks
and generators, checkpoint and tokenizer identities, and wrapper assets.
`manifest_generation_script_is_included_and_hashed` is `true` but no generator path
is named and no such script exists, so level one has no implementation.
`covers_all_decision_bearing_bytes: true` is not established, and coordinated
mutation C05 removed the analysis glob with all tests still passing.

### MAJOR

**S3V07-M01 — Fifteen active fields assign adjudication to a "fourth independent
methods review of draft-v0.5".** `§5.4.` Eleven `disposition_status` fields plus
`status.self_approval_prohibited`, `status.note`, `claim_ceiling.no_self_approval`
and OD7's disposition, against a registered active state of
`…AWAITING_SINGLE_FOCUSED_METHODS_REVIEW` and amendment dispositions reading
`PROPOSED_RESOLVED_SUBJECT_TO_SINGLE_FOCUSED_REVIEW`. None is mechanically marked
historical.

**S3V07-M02 — Eight v0.7 blocks carry no decision marker.** `§5.4, §5.12.`
`negative_control_equivalence_v0_7`, `numerical_closure_v0_7`, `provenance_v0_7`,
`zero_operation_boundary_v0_7`, `prohibited_language_v0_7`,
`p0_r2_historical_treatment_v0_7`, `focused_review_packet_v0_7` and
`decision_markers_v0_7` are outside the 14 registered markers, so the marker and
Markdown-agreement tests never reach them.

**S3V07-M03 — The Markdown companion asserts self-containment and records no
blocking decision.** `§5.1, §5.4.` It states that an executor "never layers v0.5,
v0.6 and v0.7 by hand", which S3V07-B02 contradicts, and it nowhere discloses
`blocking_decisions = ["OD2"]` or `ladder.blocked_on = "OD2"`.

### MINOR

**S3V07-N01** — the local-operations disclosure records that no local pytest run
occurred in the drafting round; a provenance field with no gate effect.

**S3V07-N02** — several carried-forward dispositions still version-stamp
themselves "draft-v0.4" or "draft-v0.3"; substantively covered by S3V07-B03.

Both MINOR findings are compatible with acceptance in principle: neither can
change an estimand, sample, threshold, gate, transition, parser, interface,
normative byte, result interpretation or execution decision. Acceptance is
nevertheless unavailable because BLOCKING and MAJOR findings exist.

## 6. Boundary

Zero operations were performed in every prohibited class: no Azure, ACR, ACA, GPU
or cloud operation; no tokenizer construction, encode or decode; no checkpoint
resolution, download or load; no model, weight, adapter or activation load; no
prefill, forward pass, logit read, scoring or generation; no output parsing on
model outputs; no seed draw, bank generation or split realization; no confirmation
access; no interface, RP-B or RP-M qualification; no evidence-ledger addition; and
no scientific-evidence claim.

Reviewed candidate paths changed: **exactly zero.** Historical protected paths
changed: **exactly zero.** `paper/evidence_ledger.csv` is byte-identical and still
ends at `EV-0016`. `formal_execution_authorized` remains `false`. Study 3 remains
unfrozen, unselected and unexecuted, and **the research question remains
unanswered**.

## 7. Verdict and next legal action

Twelve BLOCKING and three MAJOR findings remain. No confirmed defect has been
converted into a limitation.

The next legal action is one operator-level decision on those findings, issued as
a new authority. This review drafts no v0.8 and no v0.7.1, proposes no automatic
amendment, implements no repair, and does not continue into freeze or execution.

`STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`
