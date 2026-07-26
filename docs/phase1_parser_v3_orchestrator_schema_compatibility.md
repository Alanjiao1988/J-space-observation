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

## 8. Sealed-family namespace isolation

The parser-v3 evaluation owns its own sealed family. Nothing about it is shared
with the retired parser-v2 round:

| Namespace element | parser-v2 round | parser-v3 round |
| --- | --- | --- |
| Sealed holdout family | `parser-v2-v1` | `parser-v3-v1` |
| Registered parent prefix | `phase1-evaluator-validation/parser-v2-v1/...` | `phase1-evaluator-validation/parser-v3-v1/...` |
| Case-ID family | `PV2-<20 hex>` | `PV3-<20 hex>` |
| Authorization-lock prefix | `.../parser-v2-v1/authorization-locks` | `.../parser-v3-v1/authorization-locks` |
| Holdout-ID domain | `phase1-parser-v2-holdout-id/v1` | `phase1-parser-v3-holdout-id/v1` |

These are bound from the import-time profile. Each profile **rejects** the other
family's parent prefixes and case IDs, so a candidate cannot read, write, or
lock against a namespace it does not own, and the two holdout identities are
necessarily distinct.

### 8.1 Why a translation adapter exists

`src/jspace_observation/evaluator_validation.py` is the immutable
evaluator-validation instrument. It is hash-pinned
(`63eb1c7d8b229dddafdd3d54a0d62bb415d76ae8dd5aab220bd91ff054f08344`), it is
never edited, and it hardcodes the `PV2` case-ID family and the `parser-v2-v1`
parent-prefix family in its own bytes.

Rather than fork the instrument, the editable core rewrites records onto the
instrument's namespace on the way in and back onto this profile's namespace on
the way out. Consequences:

1. **The same unmodified instrument validates both evaluations.** No second
   measuring device is introduced, so a v2/v3 difference can never be an
   artifact of a difference between two validators.
2. **Under the parser-v2 profile the translation is the identity function.** It
   short-circuits before doing any work, so parser-v2 behaviour is unchanged by
   construction, not merely by test.
3. **The mapping is bijective.** Only the family label moves; the 20-hex case
   suffix, and therefore case identity, is preserved exactly.
4. **Nothing translated is ever persisted.** Every artifact written to storage
   carries this profile's true namespace.

### 8.2 State-receipt links

A state receipt's `previous_receipt_sha256` is a hash of its predecessor's exact
bytes, so rewriting the namespace necessarily changes it. Inside a validation
call the links are recomputed over the translated predecessors, in dependency
order, so the instrument checks exactly the chain topology it would see for its
own family.

The receipts **written to storage** keep the parser-v3 namespace and their own
hashes. An independent auditor who recomputes
`sha256(canonical_json(receipt))` over the stored bytes reproduces every stored
link, and `chain_sha256` names the receipt as persisted.

## 9. Protocol binding versus candidate binding in the state chain

A state receipt carries two different gate bindings, answering two different
questions.

| Field | Value in the parser-v3 round | Meaning |
| --- | --- | --- |
| `acceptance_gates_sha256` (protocol triple) | `a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988` | The frozen protocol bundle's own gate contract |
| `artifact_manifest_hashes.acceptance_gates` | `2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7` | The **parser-v3 candidate** gate contract |

`acceptance_gates_sha256` belongs to the protocol triple
(`protocol_commit`, `protocol_bundle_sha256`, `acceptance_gates_sha256`) and is
therefore **not** profile-scoped, exactly like the two constants beside it,
which the design already deliberately leaves frozen because parser v3 binds the
parser-v2 protocol bundle inside its own `parser_version`. A candidate does not
restate the protocol it is being measured under.

The parser-v3 gate contract is bound just as strongly, and in more places:

```text
artifact_manifest_hashes.acceptance_gates   (state chain, PROTOCOL_FROZEN onward)
authorization manifest                      acceptance_gates_sha256
prediction request manifest                 acceptance_gates_sha256
locked prediction seal                      acceptance_gates_sha256
scoring ledger                              gate_contract_sha256
reported metrics                            gate_contract_sha256
```

Every one of those reads the profile-scoped constant and therefore carries
`2fcc3234...`. No mandatory gate, threshold, metric definition, or population is
affected by the protocol-triple value.

**Reporting obligation.** Any table or appendix that quotes a parser-v3 state
receipt's `acceptance_gates_sha256` must state that it names the frozen protocol
bundle's gate contract, and must cite
`artifact_manifest_hashes.acceptance_gates` as the candidate's gate contract.
