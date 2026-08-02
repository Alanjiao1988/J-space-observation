# Phase 1.0D preregistration methods review (authority section 7)

This is the single bounded preregistration review the controlling prompt allows.
It was performed before any Phase 1.0D target-model generation existed, on the
frozen public protocol at commit `b07b90dba5b8b15a17516ba32a8c0be5f6cfa0af`.

Two independent reviewers examined the protocol against exactly the five
questions in authority section 7 and nothing else. Neither reviewer returned a
FATAL finding, so the round did not stop as
`BLOCKED_ON_PREREGISTRATION_INTEGRITY`.

## Scope

Reviewed: `src/jspace_observation/phase1_0d_confirmation.py`,
`src/jspace_observation/phase1_0d_execution.py`,
`docs/phase1_0d_protocol_snapshot.json`, both Phase 1.0D test modules,
`src/jspace_observation/phase1_0c_defect_audit.py`,
`docs/phase1_0c_generation_profile_defects.json`, and
`data/phase1_task_headroom_candidates.jsonl`.

Not reviewed, by instruction: style, typing, test coverage, the review harness,
and anything outside the five questions.

The J-lens validity protocol of authority sections 5 and 6 does not exist yet at
this commit and therefore was not and could not be reviewed. The section 7
allowance for that protocol is unspent and must be exercised when it is frozen.

## Findings and disposition

| ID | Severity | Q | Finding | Disposition |
| --- | --- | --- | --- | --- |
| T-03, L-01 | MATERIAL | c | `arbitrate` escalates a reviewer disagreement to a third adjudication, but no third label could ever be supplied. Every disagreement was permanently `unresolved`, and the gate requires all 20 rows resolved, so one routine disagreement permanently killed a cell for a mechanical reason rather than a scientific one. | CORRECTED |
| T-02 | MATERIAL | b | The secondary-review sample was documented as a stratified 20% but implemented as an unstratified per-row hash threshold, which can leave an individual cell with no sampled review while the global rate still looks right. | CORRECTED |
| T-05 | MATERIAL | d | Strict-arm outputs were never checked for emitted reasoning. A short rationale could be labelled `correct` and carry a cell through the gate, so the gate could select a cell whose apparent strict competence still relied on emitted reasoning. | CORRECTED |
| T-07 | MATERIAL | e | No closed reviewer form and no judgment ingestion path were committed, so an independent party holding the generations could not reproduce a label-dependent decision without inventing a review process. | CORRECTED |
| T-01 | NONFATAL | a | Phase 1.0D consumes the `mechanistic` split, so the RQ2 pilot is a selected-case pilot rather than independent confirmation. | RECORDED as L-47 |
| T-04 | NONFATAL | d | The structural arm is a string-level empty-think prefill, not a tokenizer-level one. | RECORDED as L-46 |
| T-06 | NONFATAL | d | No clean/corrupted pair and no prompt-echo control are registered, so surface recoverability is not excluded. | RECORDED as L-45 |
| L-02 | NONFATAL | a | Same fact as T-01. | RECORDED as L-43 and L-47 |
| L-03 | NONFATAL | d | The visible arm's format exemplar uses the value `42`, which would leak if any registered answer were `42`. | VERIFIED HARMLESS and GUARDED |

Two reviewers reached T-03 and L-01 independently. That agreement is why it was
treated as the primary defect rather than as a matter of taste.

## The single consolidated correction

Applied once, before any inference, as authority section 7 permits.

1. **Third adjudication exists.** `arbitrate` accepts a third label, which
   decides the row, including deciding `unresolved`. A disagreement without one
   is now reported as `arbitration_pending` rather than silently `unresolved`,
   and the gate refuses a cell with pending arbitration. A third label offered
   where the reviewers already agreed is refused, so adjudication cannot reopen
   a settled row.
2. **The stratified sample is stratified.** `stratified_secondary_sample` ranks
   record ids by a fixed hash within every `task_family` x `difficulty_band` x
   `arm_id` stratum and takes the top `ceil(20%)`. Every cell of 20 now receives
   exactly 4 sampled reviews. The rank is a hash of the record id, so it is
   still fixed before any label exists.
3. **No-CoT compliance is measured and gated.** `strict_output_compliance`
   reports whether a strict-arm output withheld visible reasoning, `CellOutcome`
   counts violations, and the gate requires zero violations in a strict arm
   before a cell can be an RQ2 pilot candidate. It is compliance evidence about
   the arm and never a correctness label.
4. **The review path is closed and committed.** `REVIEW_FORM_FIELDS` fixes what
   a reviewer may return, `REVIEW_FORM_PRESENTED_FIELDS` fixes what a reviewer
   is shown, which excludes the parser route and any other reviewer's label, and
   `ingest_judgments` is the registered path from judgments to a decision.
   Duplicate role judgments and one reviewer holding two roles on one row are
   refused.

The correction changed the protocol, so the frozen snapshot was regenerated in
Azure. `protocol_sha256` moved from
`fd52f2d58b59198512aff43eb826250dbadf9675306d8231af5809d3b763c84c` to
`25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8`. The
arbitration rule id moved from `phase1_0d_arbitration_v1` to
`phase1_0d_arbitration_v2`. The item selection did not change:
`task_ids_sha256` remains
`0d3fe6add211a381a321ea974502d262faf65312dc504e2acceb7c6556b1f524`.

The committed snapshot is now the complete Azure transcript, disclosures
included, rather than an Azure body inside a hand-authored wrapper.

## Findings recorded rather than corrected

T-01, T-04, and T-06 are real and are recorded as L-47, L-46, and L-45. They
were not repaired because each would change the preregistered sample or design
after the freeze, or would couple protocol construction to a downloaded model
artifact. Authority section 7 permits one consolidated correction and forbids a
second cycle, so they stand as disclosed limitations that any downstream claim
must discharge.

L-03 was checked rather than argued: no registered answer in any of the 450 bank
items equals the exemplar value, so no leak exists. A test now fails if that
ever stops being true, which converts a latent trap into an enforced invariant
without altering the frozen prompt text.

## Status

The protocol is frozen again. No further preregistration review of the Phase
1.0D protocol is authorized. After results exist, reviewers may check arithmetic
and provenance but may not change prompts, samples, metrics, thresholds, gates,
or eligibility.