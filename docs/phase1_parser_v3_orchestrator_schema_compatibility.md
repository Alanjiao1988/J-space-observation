# Parser-v3 evaluation: orchestrator schema compatibility

This record is part of the parser-v3 preregistration. It documents a naming
decision in the one-shot orchestrator so that no reader of the sealed artifacts,
the scoring ledger, or the paper can mistake a storage-schema field name for a
statement about which parser produced a number.

## 1. Decision

Historical `parser_v2_*` field names are **retained** in the orchestrator
storage schema for the parser-v3 evaluation.

They are **not** renamed. The evaluation adds explicit identity metadata
instead.

## 2. Reason

1. The names belong to an already-verified orchestrator storage schema.
2. A wide rename immediately before a one-shot, irreversible evaluation would
   enlarge the risk surface without adding a security property.
3. The parser actually used is pinned by profile, algorithm ID, parser version,
   source SHA-256, and the prediction seal — not by a field name.
4. Parser-v2 historical recovery tooling depends on the existing field
   structure.
5. A field name is not a security boundary.

## 3. What the retained names hold under `evaluation_profile = parser_v3`

| Retained field prefix | Actual content in this round |
| --- | --- |
| `parser_v2_prediction_row_*` (scoring ledger) | **Candidate parser v3** prediction rows |
| `legacy_prediction_row_*` (scoring ledger) | **Parser-v2 comparator** rows (the gating comparator) |
| `overall_legacy_*`, `legacy_typed_agreement`, and sibling metric fields | **Parser-v2 comparator** aggregates |
| `parser_v2_*` metric fields | **Candidate parser v3** aggregates |

The reporting-only **legacy** parser stream is published separately and is
never a gating input. It is scored, if at all, only after the holdout has been
retired, and a defect in it cannot change `PASS`/`FAIL`.

## 4. Protocol statement

> Fields whose historical names begin with `parser_v2_` are retained for
> orchestration-schema compatibility. They do not identify the candidate parser
> used by the current evaluation. Candidate identity is controlled exclusively
> by the import-time profile, hardcoded worker identity, algorithm ID, parser
> version, source SHA-256 and prediction-seal bindings.

## 5. Explicit identity metadata carried by this evaluation

```text
evaluation_profile:
  parser_v3

candidate_parser_algorithm_id:
  jspace-parser-v3-reference-blind-extraction/v1

candidate_parser_version:
  0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace

candidate_parser_source_sha256:
  76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9

candidate_parser_implementation_commit:
  310277bcadd67ca9e77986fc292fae47dc5ceda2

orchestrator_schema_compatibility:
  parser_v2_field_names_v1
```

Every metrics record additionally carries a `parser_attribution` block naming
the candidate parser, the gating comparator parser, the field prefix each one
occupies, and the reporting-only comparators. That block, not the field name,
is authoritative.

## 6. Reporting obligation

User-visible reports, the run log, the decision record, and every paper table
**must not** describe these compatibility fields as parser-v2 candidate output.
Where a retained `parser_v2_*` field is quoted, the accompanying text must name
the parser that actually produced it, using `parser_attribution`.

## 7. Scientific interpretation impact

```text
Candidate identity controlled by:
  profile, algorithm ID, version, source SHA-256, worker binding,
  prediction seal

Scientific interpretation impact:
  none
```

The retained names change no threshold, no metric definition, no population,
and no gate. They are a storage detail.
