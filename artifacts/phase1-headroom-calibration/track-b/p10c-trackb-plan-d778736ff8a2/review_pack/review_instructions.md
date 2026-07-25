# Semantic review instructions (Phase 1.0C Track B)

## What you are deciding

For each row in `review_pack.jsonl`, decide whether the model's emitted output
states the registered answer. Return exactly one `semantic_label`:

- `correct` - the output's final answer matches the registered answer.
- `incorrect` - the output's final answer is present but does not match.
- `unresolved` - you cannot decide (no answer, truncated mid-answer, or genuinely
  ambiguous). Do not guess.

## What you must not do

- Do not judge the reasoning, style, or verbosity. Only the stated final answer matters.
- Do not infer an answer the model did not state.
- Do not make any claim about hidden reasoning, internal state, or "J-space".
  This pack is capability calibration only.

## Blinding

Rows are deliberately blinded to the deterministic screening verdict. The
screening labels live in `deterministic_triage.jsonl` and exist only for audit
and arbitration. Do not read them before you label.

## Output format

Write JSON Lines to a file the orchestrator can ingest. One object per row:

```
{"review_id": "R001", "record_id": "<record id>", "semantic_label": "correct",
 "reviewer_id": "<your id>", "notes": ""}
```

`record_id` is mandatory and must be copied exactly from the review row.

## Arbitration

If your label conflicts with the deterministic screening verdict, the row is
written to `arbitration_packet.jsonl` and an arbiter resolves it. An arbiter is
never invoked otherwise.
