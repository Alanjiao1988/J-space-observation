# Study 2 Stage B-D interpretation erratum

Status: interpretation control for already-published frozen documents.
Scope: wording and inference boundary only.
Authority: none over any measurement, decision, threshold, row, or artifact.

This erratum narrows overbroad interpretive wording in two frozen Study 2 Stage B-D
documents. It changes no byte of either document, no decision, no threshold, no row,
and no hash. It creates no evidence row. It grants no execution authority.

## 1. What is being corrected

Two frozen documents contain a sentence pattern asserting, without qualification,
that the Gate A outcome "is not a measurement artifact":

| document | sha256 | bytes | location |
| --- | --- | --- | --- |
| `studies/study2/decisions/study2_stage_bd_gate_a_decision.md` | `e535504725b2e5d918af19ecce5eda82ebdf573feb0ca3a1f1efd358f065eab4` | 8590 | section 5, titled "Why this is not a measurement artifact" |
| `studies/study2/STAGE_BD_FINAL_HANDOFF.md` | `8acc361f40ea9d3ee6aad7af0d905c808acaf19dec69e88ca0d8c23a637f008f` | 14218 | the corresponding integrity-validity discussion |

Both documents remain frozen at exactly these hashes. Neither is edited, replaced,
withdrawn, or superseded. Their measured content stands.

## 2. The defect

The reasoning in those sections is sound for the class of artifact it actually
examined, and the section heading generalizes past it.

What the frozen analysis genuinely established is that the Gate A result is not an
artifact of **execution and bookkeeping integrity**. It ruled out:

- a wrong or incomplete row space (3,072 rows, all present, no retries, shard
  manifest matched);
- prompt or token identity mismatch against the Stage T seal;
- wrong option-token IDs (A=362, B=425, C=356, D=422, identical across all three
  checkpoints);
- non-finite or incomplete summary cells;
- unregistered decision inputs;
- post-measurement movement of the frozen Gate A rule.

Those exclusions are correct and are not withdrawn.

What the heading "Why this is not a measurement artifact" implies, but the analysis
never tested, is the broader class of **construct and interface validity**. Integrity
validity does not establish:

- that the four-option letter surface validly measures the underlying capability;
- that label binding to the option letters succeeded;
- that a no-tool, no-generated-trace, single-forward-pass interface can express the
  target computation at this model scale;
- that the estimand is construct-valid;
- that the interface is adequate to the question.

An interface that is fully integrity-valid can still be an inadequate instrument. The
frozen wording collapses those two senses of "artifact" into one.

## 3. The corrected statement

The following is the controlling interpretation. Where it conflicts with the
unqualified frozen wording, this statement governs:

> The Study 2 Stage B-D Gate A outcome is not an artifact of execution or
> bookkeeping integrity. The execution is complete, the row space is correct, the
> token and prompt identities match the Stage T seal, the decision inputs were
> registered before measurement, and the frozen rule did not move. It remains
> entirely possible that the outcome is an artifact of interface or construct
> validity. Protocol v1 did not measure interface adequacy or label binding, so the
> data cannot distinguish an incapable checkpoint from an inadequate interface. No
> claim in either direction is supported.

The phrase "the result is not a measurement artifact" must not be used about Study 2
without this qualification.

## 4. What does not change

- Gate A still fails. `overall_gate_pass` remains `false`.
- The decisive target rows are unchanged: `permutation_chain` 25/128 (exact one-sided
  binomial upper tail `0.9403523926144965`) and `affine_mod10` 33/128
  (`0.4526854444021635`), against the frozen threshold X >= 43 at alpha = 0.025.
- `gate_inputs_sha256` remains `1433f8119b2d8e377be7ede2735430ab55006c3737ebd2bf9e0c85c486b93cf7`.
- The distance from threshold is unchanged and is not marginal: 18 and 10 additional
  correct rows respectively would have been required.
- Stage B-C and every mechanistic stage remain unopened and unavailable under
  protocol v1. The confirmation bank was never read.
- The primary terminal state remains
  `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`.
- No control cell is promoted. The `lineage_base` / `affine_mod10` cell at 44/128
  still carries zero authority.
- Every frozen artifact keeps its registered bytes and hashes.

## 5. What this erratum does not authorize

This erratum is not a reason to rerun, repair, relabel, backfill, rescore, or reopen
anything under protocol v1. It is not authority to design protocol v2, to calibrate
or redesign the interface, to run an interface-adequacy or label-binding study, to
open Stage B-C, or to begin any mechanistic work. It does not convert the failed
feasibility gate into a scientific finding about the model, and it does not convert
the interface concern into a scientific finding about the interface.

The interface-adequacy concern is recorded as a limitation, not as a result. See
`paper/limitations_ledger.md` entries L-85 and L-89.

## 6. Related records

- `studies/study2/terminal_manifest.json` - `interpretation_boundary`
- `studies/study2/STUDY2_PROTOCOL_V1_TERMINAL_HANDOFF.md`
- `studies/study2/analysis/stage_bd_posthoc_interface_diagnostic.md` - descriptive,
  zero-authority, not scientific evidence
- `paper/limitations_ledger.md` - L-85, L-89
- `docs/decision_log.md` - D37
