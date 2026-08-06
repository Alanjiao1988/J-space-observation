# J-lens S3 validity protocol methods review

## Exact review target

The single bounded review allowance was spent on this immutable candidate:

| Field | Value |
|---|---|
| Candidate commit | `36b54824a6c916e8d7738c6a9f65c54c314a4e20` |
| Candidate tree | `632b99f91daa4b071a1f1ebaee19b03c17796fc3` |
| Canonical protocol SHA-256 | `eed211b11020851651bdcc4142e0e0c0d402e9814e9c7ede510667d425f897d4` |
| Focused pre-review ACR run | `cma2`: 52 passed |

The review was static and read-only. It did not run Python, tests, a model,
tokenizer, lens, inference, activations, interventions, patching, provider
calls, or Azure mutations. It asked only the six questions registered at
`$.review.questions`.

## Initial review

| Question | Result | Basis or finding |
|---|---|---|
| Q1 role non-overlap | MATERIAL `S3R-01` | The candidate claimed primary-readout and causal-swap benchmark disjointness although official source files contain shared names and content. |
| Q2 outcome-independent selection | PASS | Selectors are limited to vendored bytes, mechanical eligibility, clean greedy correctness, and the frozen split hash; lens/intervention/confirmation outcomes are forbidden. |
| Q3 exact computability | MATERIAL `S3R-02` | The hard gate named final-answer synonyms without a finite synonym rule or sufficient row-level definition. |
| Q4 control discrimination | MATERIAL `S3R-02` | Prompt, motor, random, and answer-vector controls were explicit, but the named final-answer-synonym condition was not exact. |
| Q5 development/confirmation separation | PASS | E0 is sealed before lens output, E1 is development-only, and E2 stays unopened until the execution boundary is sealed. |
| Q6 reconstruction | MATERIAL `S3R-02` | All other results were reconstructible, but the named final-answer-synonym hard gate was not. |

## Findings

| ID | Severity | Candidate reference | Finding | Required consolidated correction |
|---|---|---|---|---|
| `S3R-01` | MATERIAL | `docs/jlens_s3_validity_protocol.json` `$.role_separation.required_disjoint_pairs[4]` and `$.role_separation.roles` | Source-role separation was contradicted or underdefined because public multihop and probe-swap rows can share names and exact content. | Define identity by distribution-qualified canonical row bytes and state explicitly that cross-distribution content overlap does not merge or transfer roles. |
| `S3R-02` | MATERIAL | `docs/jlens_s3_validity_protocol.json` `$.classification.hard_scientific_gates[3]`, `$.eligibility.primary_leakage_filter`, and `$.outputs.e0_surface` | "Final-answer synonym" had no closed mechanical definition, so the hard gate was not exactly computable or reconstructible. | Narrow the gate to exact normalized target overlap, freeze its row-level reconstruction rule, and mirror it in JSON, schema, Markdown, validator, and tests. |

Disposition: **0 FATAL / 2 MATERIAL / 0 MINOR**. The candidate did not require
`BLOCKED_ON_PREREGISTRATION_INTEGRITY`, but it was not freeze-ready. Exactly one
consolidated correction was authorized for `S3R-01` and `S3R-02`.

## Consolidated correction

The one correction:

1. registers `$.role_separation.role_identity`, including immutable
   distribution-source IDs, distribution-qualified canonical row bytes,
   cross-distribution overlap policy, and output reconstruction;
2. replaces the ambiguous benchmark pair with distribution-qualified
   source-role rows; and
3. registers `$.classification.hard_surface_rule`, an exact join and equality
   over `e0_item`, `e0_surface`, and true-label `readout_rank`, while explicitly
   forbidding semantic-synonym generation.

## Same-checklist verification

The correction verification targeted only the two cited findings:

| Field | Value |
|---|---|
| Corrected commit | `3954e6e0089271e835de152e4c7e3e9591bb8491` |
| Corrected tree | `dbb275b3ae7e0cd41af365dbac14b103c18ee0a7` |
| Corrected protocol SHA-256 | `bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625` |
| Corrected schema SHA-256 | `5d6e2fc33771b427130bd1dbe94c79cdf6d5827288b96929352c0caa793acbf1` |
| Focused correction ACR run | `cma3`: 55 passed |

`S3R-01` is **VERIFIED**. `$.role_separation.role_identity` now qualifies
each official row by its immutable source distribution, explicitly acknowledges
cross-distribution content overlap, forbids merge/transfer across roles, and
keeps readout and causal source-role rows operationally distinct. The schema,
Markdown, validator helpers, and tests carry the same rule.

`S3R-02` is **VERIFIED**. `$.classification.hard_surface_rule` is finite and
reconstructible from scoped `e0_item`, `e0_surface`, and true-label
`readout_rank` rows. Target overlap is exact normalized case-folded equality;
semantic synonym generation is not used. The separate direct-answer,
prompt-echo, motor-band, and random-perturbation controls remain registered.

The correction created no direct contradiction. Final disposition:
**0 FATAL / 0 MATERIAL / 0 MINOR**. The protocol is freeze-ready and
`BLOCKED_ON_PREREGISTRATION_INTEGRITY` is not required.

This verification completes the already-spent single review; it is not a
second review cycle. No further correction or S3 methods review is authorized
after this record is frozen.
