# Summary

Phase 1.0C Track B bounded capability/headroom calibration, run `20260725T170041Z`, mode `finalize`, status **INCONCLUSIVE**.

## Objective

Which frozen Phase 1 task cells (task family x difficulty band x visible-reasoning condition) leave the target model measurable observable-answer headroom, so that later ablation and activation-patching experiments are not run on saturated or impossible tasks?

## Scope

- 150 unique bank items (5 families x 3 bands x 10 items), split `calibration`.
- Conditions run: r1_style_thinking, visible_cot.
- Conditions deferred: answer_prefill, empty_think_prefill, postprocessed, prompt_only_raw_strict, stopped.
- Total generation units: 300.

## Provenance

- Model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` at revision `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`.
- Code commit: `72c3d2816f4cca02ebc6de166a3791bf4bad4722`.
- Image digest: `not_recorded`.
- Hardware: `local x86-64 Windows host, CPU only; the finalize stage ran outside any container image`.
- Protocol hash: `d778736ff8a2f0c7e82ee14a529abc05afb44ce3c8a9b2b47fd02771c405719d`.
- Task bank: `data/phase1_task_headroom_candidates.jsonl` (sha256 `acf59ec44b7afb73c03392d2c9b7223eff7311e29e2261ff0d65b38a3a416407`).
- Selection seed: `20260725`; run base seed `20260725`.

## Execution

- Records emitted: 300.
- Generated: 300; planned-only: 0; errors: 0.
- Decoding: max_new_tokens=512, temperature=0.6, top_p=0.95, samples per item/condition=1.
- Rows flagged for semantic review: 225 of 300.

## Results

- Cells scored: 30.
- Selected headroom cells: 2.
- High-accuracy control cells: 1.
- Difficulty-boundary cells: 4.

| cell | n | correct | accuracy | 95% CI |
| --- | --- | --- | --- | --- |
| `prompt_grounded_two_hop_factual|hard|r1_style_thinking` | 10 | 7 | 0.7 | [0.396778, 0.892209] |
| `synthetic_relation|hard|r1_style_thinking` | 10 | 7 | 0.7 | [0.396778, 0.892209] |

## Decision

- Status: **INCONCLUSIVE**.
- Decision: Every flagged row carries an adjudicated label, but 44 row(s) were adjudicated as unresolved, so under the registered finalize rule cell selection is not final. An unresolved row is one whose emitted output states no answer the reviewer could read; further adjudication of the same output cannot resolve it.

## Deviations and errors

Protocol deviations:
- None recorded.

Execution implementation changes (protocol effect: none):
- A dedicated calibration container image (Dockerfile.calibration) was introduced for this run. Reason: The generic image requires a historical build attestation that is unrecoverable from git history, ACR and Blob, and is unregenerable because the registered generator asserts equality against a 30-file frozen list while the repository now tracks 63 behavior files (33 extra, 0 missing). The calibration image carries its own pre-committed, deterministic build provenance instead.
- cell_selection/ additionally emits high_accuracy_controls.csv and difficulty_boundaries.csv. Reason: Both files are derived views of rows already classified by the frozen selection rule; no threshold, gate or classification changed.
- The artifact pack is uploaded by headroom_blob_transport, which writes artifact_manifest.json last. Reason: The generic directory uploader walks the pack in filesystem order and cannot guarantee the registered manifest-last rule.
- 04_decision.json additionally carries track_b_decision and track_b_decision_vocabulary. Reason: The registered status vocabulary (BLOCKED / INCONCLUSIVE / COMPLETE / FAIL) is emitted unchanged. track_b_decision is a deterministic reporting view over the already-frozen cell classifications and applies no additional rule.
- 04_decision.json additionally carries outstanding_review_rows, and the finalize INCONCLUSIVE decision/next_gate prose distinguishes rows that are not yet adjudicated from rows adjudicated as unresolved. Reason: The registered finalize rule ('Outstanding mandatory reviews or unresolved labels remain' -> INCONCLUSIVE) is evaluated unchanged, and status, criteria_passed and criteria_failed are byte-identical. Only the human-readable explanation and one derived count were added, because the previous prose told the reader to return rows for adjudication even when every flagged row already carried a label.
- 05_summary.md now lists the execution implementation changes under 'Deviations and errors' instead of reporting 'None recorded'. Reason: 08_deviations.json already recorded them; the summary silently omitted them, which under-reported the pack against its own machine-readable record. The protocol-deviation list is still rendered separately and is still empty.

## Scientific interpretation

This run estimates observable answer accuracy of a single target model on a frozen task bank under two visible-reasoning prompt conditions, for the sole purpose of selecting task cells with measurable headroom. It licenses no claim about hidden reasoning, internal representations, or 'J-space', and it is not a formal RQ1/RQ2 result.

- Prohibited: Any claim that this run observes, measures, or bounds hidden reasoning.
- Prohibited: Any claim about an internal workspace, latent scratchpad, or invisible chain-of-thought.
- Prohibited: Any claim about 'J-space' existence, structure, capacity, or dynamics.
- Prohibited: Any RQ1 or RQ2 result claim; this is task calibration, not a formal result.
- Prohibited: Any pass@k or sampling-capability claim; one sample per item/condition is drawn.
- Prohibited: Any claim that parser v2 output is a validated correctness label.
- Prohibited: Any generalisation to conditions deferred this round.

## Limitations

- One sample per item/condition; no pass@k or sampling-variance estimate.
- Parser v2 screening is not locked-validated and is never authoritative.
- No locked typed-entity evaluator exists; entity rows rely on adjudication.
- Only two visible-reasoning conditions were run; others are deferred.
- Cell-level n = 10 is a screen, never a stable performance estimate; the Wilson intervals are correspondingly wide.
- Cell truncation and no-answer rates are computed from the deterministic screening flags, not from reviewer flags; the truncation flag is the objective token-cap signal, but the no-answer flag reflects parser v2 answer-presence detection, which is screening only.

## Paper relevance

Supplies the task-selection appendix: which cells are usable for later ablation and patching experiments, which are saturated controls, and which are difficulty boundaries. It contributes no RQ1/RQ2 result.

## Next gate

- Main agent decides whether to accept INCONCLUSIVE for this run or to preregister a change to the generation profile (for example a larger token budget) and rerun; the unresolved rows cannot be cleared by re-reviewing the existing outputs.
