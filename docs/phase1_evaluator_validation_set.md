# Phase 1 parser-v2 evaluator validation-set protocol

## Registration and stop point

This document preregisters Phase 1.2A, the first part of Path C. It creates:

- an open 60-case development set;
- a private 120-case locked validation set;
- independent operational consensus reference labels;
- hashes, manifests, visibility records, and a one-shot holdout state.

The phase stops after set validation and sealing. It does not implement parser
v2, run the locked parser evaluation, run
`deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`, or authorize higher-n replication.

Only fixtures constructed after the final parser-v2-v1.1 protocol commit are
eligible. Candidate pools produced under superseded protocol bytes are
discarded, are not inputs to selection or labeling, and contribute no
development or locked evidence.

## Exact set composition

| Stratum | Description | Development | Locked | Reference presence |
|---|---|---:|---:|---|
| S01 | explicit boxed single answer | 5 | 10 | present |
| S02 | explicit `Answer` / `Final answer` marker | 5 | 10 | present |
| S03 | terminal equation with unique result | 5 | 10 | present |
| S04 | multiple intermediate numbers with clear final answer | 5 | 10 | present |
| S05 | final answer followed by continued reasoning | 5 | 10 | present |
| S06 | last-number trap with earlier unique final answer | 5 | 10 | present |
| S07 | truncated before any final answer | 5 | 10 | no answer |
| S08 | placeholder or explicit no-answer output | 5 | 10 | no answer |
| S09 | malformed but answer recoverable | 5 | 10 | present |
| S10 | malformed with no reliable answer | 5 | 10 | no answer |
| S11 | true multiple-candidate ambiguity | 5 | 10 | ambiguous |
| S12 | signed integer, decimal, and fraction normalization | 5 | 10 | present |

Exact support:

```text
development:
  present = 40
  ambiguous = 5
  no_answer = 15
  total = 60

locked:
  present = 80
  ambiguous = 10
  no_answer = 30
  total = 120
```

Only S11 is ambiguity-positive. S07, S08, and S10 are no-answer-positive.
These supports cannot be changed after construction to improve a metric.

Clean comparison strata are S01, S02, S03, and S12. Critical comparison strata
are S04 through S11. Locked critical-case count is therefore 80.

## Primary-stratum precedence

Every case has exactly one primary stratum. Apply precedence:

1. S07 for a recognizable incomplete construct ending before any complete
   final claim.
2. S08 for a complete placeholder, refusal, or task echo with no answer.
3. S09 or S10 for non-truncation malformation, split by unique recoverability.
4. S11 for complete distinct final claims with no resolution.
5. S06 for an earlier unique final claim followed by a distinct non-answer
   rightmost numeral.
6. S05 for continued reasoning after a final claim.
7. S04 for multiple intermediate numbers followed by a clear final answer.
8. S03 for one terminal equation without a separate marker or box.
9. S01 for one boxed candidate without another structural challenge.
10. S02 for one unboxed explicit marker without multi-step structure.
11. S12 for normalization-focused output without higher-priority structure.

Secondary feature tags may overlap and never change the primary quota.

## Five subtype slots per stratum

Each slot contributes one development and two independently authored locked
cases:

| Stratum | Required subtype slots |
|---|---|
| S01 | inline box; display-math box; spaced box; math-delimited box; trailing punctuation |
| S02 | `Answer:`; `Final answer:`; `The answer is`; `Final:`; case/colon/newline variant |
| S03 | plain infix; parenthesized; chained equivalent; LaTeX; prose lead-in then terminal equation |
| S04 | numbered steps; multiline equations; prose sequence; mixed prose/math; balanced think working with final outside |
| S05 | verbal verification; equation check; reconsideration; rejected alternative; tagged continuation |
| S06 | trailing step number; rating/confidence; check operand; count/metadata; explicitly rejected alternative |
| S07 | cut before marker; empty marker; missing equation RHS; incomplete box; unclosed reasoning tag |
| S08 | empty/empty-wrapper; ellipsis/N/A; refusal without numbers; refusal with incidental number; task echo |
| S09 | extra delimiter; doubled marker punctuation; broken LaTeX wrapper; stray tag; encoding/markup noise |
| S10 | corrupted box; broken marker; corrupted equation; tag-mixed fragments; invalid numeric form |
| S11 | two markers; two boxes; marker-box conflict; incompatible terminal equations; two unranked final claims |
| S12 | positive signed integer; negative integer; positive decimal; negative decimal; fraction |

The two locked fraction cases in S12 use distinct proper/improper or
reduced/unreduced surfaces.

Only one truly empty or whitespace-only output is allowed across both sets; it
is assigned to development. The two locked cases in S08's first slot use
distinct nonempty empty-wrapper placeholders. They cannot normalize to the
development empty output or to each other.

## Cross-cutting quotas

- Each locked answer-bearing stratum contains exactly five
  reference-correct and five reference-incorrect outputs: 40/40 overall.
- Development answer-bearing strata total exactly 20 reference-correct and 20
  reference-incorrect outputs.
- Each answer-bearing stratum outside S12 contains at least one development and
  two locked signed, decimal, or fractional surfaces.
- Locked cases include at least ten negative answers, ten decimal surfaces, and
  ten fraction surfaces. Development includes at least five of each.
- At least five development and ten locked cases contain balanced think tags.
- At least five development and ten locked cases contain malformed, stray, or
  unclosed think tags.
- In each of S07, S08, and S10, at least two development and five locked cases
  contain incidental numeric distractors.
- Every S06 rightmost distractor differs canonically from the earlier answer.
- Every S11 case contains at least two distinct canonical answer candidates.

The private manifest records exact realized feature counts and case IDs.

## Constructed-fixture boundary

Every case is an artificial, model-free arithmetic evaluator fixture.

Required:

- `source_kind=constructed_model_free_fixture`;
- unique opaque case ID;
- construction provenance and curator identity;
- one primary stratum and closed secondary tags;
- no personal information, environment data, secrets, or copied model output;
- no representation as a real output from the historical target model.

Historical 45 generation/evaluation outputs may inform the already registered
failure taxonomy only. Curators do not inspect them. An authorized custodian
performs contamination checks without showing historical text to curators or
reviewers.

## Case IDs, serialization, and ordering

Case IDs are opaque:

```text
PV2-<first 20 lowercase hex characters>
```

The suffix is SHA-256 over a registered domain, private per-set ID salt,
parse type, and exact output bytes. It contains no stratum or label hint. ID
salts remain in the private mapping.

Artifacts use UTF-8 canonical JSON/JSONL, sorted object keys, compact
separators, no duplicate keys or non-finite values, and a terminal LF.
JSONL is ordered by case ID. The same inputs and private salt reproduce the
same IDs, ordering, and hashes.

## Duplicate and contamination controls

Define normalized fixture text as:

1. Unicode NFKC;
2. CRLF/CR converted to LF;
3. leading/trailing whitespace stripped;
4. every remaining whitespace run collapsed to one ASCII space;
5. Unicode casefold applied.

The following are hard failures:

- exact duplicate output text within development;
- exact duplicate output text within locked;
- exact duplicate across development and locked;
- normalized duplicate in any of those comparisons;
- exact or normalized overlap with any historical selected eval output,
  generation output, raw output, stopped output, or postprocessed output;
- shared private `template_family_id` across development and locked.

Near-duplicate screening masks every numeric literal as `<NUM>`, computes
character 5-gram Jaccard similarity, and flags pairs at or above 0.85. Every
flag needs a documented keep/reject disposition before sealing. Approximate
similarity is reported; it is not silently repaired after lock.

## Curator isolation

Curator A and Curator B:

- use `gpt-5.6-sol`, reasoning effort `max`;
- independently produce at least 12 candidates per stratum;
- receive only the frozen protocols and construction schema;
- do not inspect the legacy parser, legacy predictions, historical output
  text, future parser implementation, or each other's candidates.

Curator C:

- receives both independently sealed candidate pools and the frozen protocol;
- deduplicates and selects exactly 60 development and 120 locked cases;
- selects exactly one Curator-A and one Curator-B locked case for every subtype
  slot;
- selects exactly 30 Curator-A and 30 Curator-B development cases overall;
- cannot select based on legacy or future parser behavior;
- records selection and rejection reasons;
- does not serve as the sole locked-label reviewer.

The custodian alone performs historical contamination checks. Agent visibility
is recorded in a redacted ledger.

## Development record schema

The open repository record contains:

```text
schema_version
case_id
source_kind
stratum
secondary_tags
output_text
parse_type
expected_answer_presence
expected_parse_valid
expected_parse_ambiguous
expected_parsed_answer
expected_candidate_answers
expected_evidence_spans
expected_extraction_strategy
expected_output_quality
expected_failure_reasons
expected_format_warnings
registered_reference_answer
expected_correctness
critical_case
material_error_if_missed
curation_notes
```

The development set may expose all labels and notes after the locked set is
sealed. It is the only validation set parser implementation agents may use.

## Parser-facing locked input

`locked_inputs.jsonl` contains exactly:

```text
schema_version
case_id
source_kind
output_text
parse_type
```

It omits stratum, tags, reference answer, expected fields, provenance, and
curation notes. Future implementation agents do not see locked inputs; only the
frozen prediction runner receives them after authorization.

The runner projects one outer record to:

```text
{
  "schema_version": "phase1-parser-v2-request/v1",
  "answer_type": "numeric",
  "output_text": outer.output_text
}
```

`parse_type` must equal `numeric`; it selects the fixed `answer_type` but is not
passed as an extra request field. `case_id` and `source_kind` remain only in the
runner's prediction envelope. The envelope schema is:

```text
schema_version
case_id
input_record_sha256
parser_request_sha256
parser_result
```

## Private locked reference label

`locked_reference_labels.jsonl` contains the full expected schema plus:

```text
acceptable_selected_spans
last_number_distractor_span
template_family_id
construction_provenance
```

An acceptable span uses original-output half-open Unicode code-point offsets
and must satisfy `output_text[start:end] == text`. A present case has at least
one acceptable span. S06 has exactly one registered rightmost distractor span.
No-answer and ambiguity cases have no selected acceptable span.

These labels are operational consensus references, not human ground truth.
They are never committed to the normal repository or included in a Docker
build context.

## Independent two-stage labeling

Reviewer A and Reviewer B are distinct `gpt-5.6-sol/max` agents and do not see
each other's work, legacy predictions, future parser predictions, strata,
curator labels, curation notes, or historical outputs.

Stage 1:

- each reviewer sees only the locked parser-facing cases and frozen rubric;
- each completes all 120 extraction labels;
- neither sees registered reference answers;
- each submission is canonical, complete, hashed, and sealed.

Stage-1 arbitration:

- starts after both Stage-1 submissions are sealed and before any reference
  answer is released;
- resolves every extraction-field disagreement while reference-blind;
- produces and seals one final extraction consensus for all 120 cases;
- cannot label correctness.

Stage 2:

- begins only after the complete Stage-1 arbitration/consensus seal exists;
- each reviewer receives the same sealed final extraction consensus plus
  registered reference answers and the critical/material rubric;
- extraction fields cannot be changed;
- each completes correctness, critical, and material fields for all 120;
- each Stage-2 submission is canonical, complete, hashed, and sealed.

Stage-2 arbitration is separate. It sees the sealed final Stage-1 consensus,
registered references, critical/material rubric, and both Stage-2 judgments.
It resolves only correctness, critical, and material disagreements and cannot
revise extraction fields. A third distinct `gpt-5.6-sol/max` arbiter performs
both passes under those visibility limits. Final unresolved count in each
stage must be zero; otherwise the set is INVALID and cannot be used.

## Agreement report

Report:

- exact agreement and nominal Cohen's kappa for presence, validity, ambiguity,
  strategy, quality, and correctness;
- exact normalized parsed-answer agreement;
- candidate-list exact agreement and Jaccard;
- selected-span exact agreement;
- failure/warning set exact agreement and Jaccard;
- arbitration count and IDs;
- unresolved count.

Zero denominator or constant-marginal kappa is JSON `null` and rendered `NA`.
No row is removed to improve agreement.

## Private Blob layout

Use a new UTC parent:

```text
P=phase1-evaluator-validation/parser-v2-v1/<YYYYMMDDTHHMMSSZ>
```

Registered leaf prefixes and exact membership follow.

`P/development`:

1. `.development_reservation.json`
2. `development_cases.jsonl`
3. `development_manifest.json`, last

`P/locked-inputs`:

1. `.locked_inputs_reservation.json`
2. `locked_inputs.jsonl`
3. `locked_inputs_manifest.json`, last

`P/locked-labels`:

1. `.locked_labels_reservation.json`
2. `reviewer_a_stage1.jsonl`
3. `reviewer_b_stage1.jsonl`
4. `arbitration_stage1.jsonl`
5. `stage1_consensus.jsonl`
6. `reviewer_a_stage2.jsonl`
7. `reviewer_b_stage2.jsonl`
8. `arbitration_stage2.jsonl`
9. `locked_reference_labels.jsonl`
10. `locked_labels_manifest.json`, last

`P/reports`:

1. `.reports_reservation.json`
2. `validation_set_report.json`
3. `validation_set_report.md`
4. `reports_manifest.json`, last

`P/manifests`, completed after every preceding prefix:

1. `.locked_manifest_reservation.json`
2. `locked_case_mapping.json`
3. `visibility_ledger.jsonl`
4. `overlap_report.json`
5. `locked_manifest.json`, last overall

The overall manifest binds every registered relative path and rejects missing
or extra parent membership. Future predictions, scores, state receipts, and
visibility updates use new authorization-specific prefixes:

```text
P/predictions/<authorization-id>
P/scores/<authorization-id>
P/state/<authorization-id>
P/visibility/<authorization-id>
```

Every leaf prefix must be entirely new. For each leaf, the uploader:

1. conditionally creates a reservation with `overwrite=false`;
2. never deletes or reuses a partial prefix;
3. uploads canonical bytes in registered order;
4. verifies exact membership before manifest;
5. uploads the manifest last;
6. re-lists exact leaf and registered parent membership;
7. re-downloads every object and verifies size, SHA-256, and ETag.

The manifest binds protocol commit/bundle, acceptance-gate hash, ordered IDs,
counts, schemas, file sizes/hashes, reservation hash, label-review seals,
arbitration, overlap report, feature counts, visibility-ledger hash, source
boundaries, UTC timestamp, private nonce, and no-model-run attestation.

Repository-visible material contains only open development cases, aggregate
counts, agreement, Blob prefixes, file/manifest hashes, and a redacted seal
receipt. It contains no locked case ID, output, reference, label, mapping,
review submission, arbitration row, private nonce, or selection seed.

## Procedural visibility and residual limitation

The current Azure design uses the existing user-assigned managed identity
`id-jspace-aca-acrpull-sea`. The ledger records actor/reviewer ID, role,
artifact classes visible, purpose, authorization, execution ID, model/effort,
and first/last access time.

The locked set, future predictions, and labels use the same user-assigned
managed identity. Separation, blinding, immutability, and one-shot use are
procedural and audit-evidenced, not security-enforced. A principal able to run
or modify workloads with that identity could access all locked artifacts;
absent Blob WORM controls, authorized writers could also delete objects. Hash
commitments make modification detectable, not impossible.

No key, SAS, public network path, Azure Files mount, or GPU is permitted.
Locked plaintext is not printed to job logs or placed in the repository,
Docker context, command arguments, or environment values. Any transport
envelope must be encrypted before entering an ACR build context; only a
short-lived decryption key may be an ACA secret. The key reference and secret
are removed after execution, the job is restored to an idle command, and
secret count zero is verified.

## One-shot holdout state

This phase stops at `SEALED`:

```text
DRAFT_PROTOCOL
PROTOCOL_FROZEN
PRIVATE_CONSTRUCTION
RESERVED
PAYLOAD_COMPLETE
SEALED
```

A later authorized evaluation continues:

```text
IMPLEMENTATION_FROZEN
UNSEAL_AUTHORIZED
INPUTS_READ
PREDICTIONS_VERIFIED
LABELS_READ
SCORES_VERIFIED
CLOSED
```

Each transition writes an overwrite-false canonical hash-chained receipt with
the prior receipt hash, UTC time, execution ID, actor, visibility, protocol,
implementation, image/config, and artifact-manifest hashes.

Retry policy:

- ACA automatic retries are zero.
- Before `INPUTS_READ`, one independently approved infrastructure-only retry
  may use identical bindings and a new execution/output prefix.
- After `INPUTS_READ`, prediction is never rerun.
- After predictions verify but before labels are read, one scorer-only
  infrastructure retry may reuse byte-identical predictions.
- After `LABELS_READ`, only verification of already-written bytes is allowed.
- Parser, schema, content, assertion, or threshold failure is a scientific
  outcome and is not retryable.
- Partial prefixes remain immutable and linked from the retry receipt.

After any authorized input exposure the holdout is spent. PASS and FAIL both
retire it. A modified parser or threshold requires a new independent holdout.

## Azure execution constraints

If private persistence is needed:

```text
environment: cae-jspace-observation-sea-vnet2
profile: Consumption
resources: 2 CPU / 4Gi
GPU: none
suggested job: job-jspace-parser-v2-set
identity: id-jspace-aca-acrpull-sea
authentication: ManagedIdentityCredential only
replicaRetryLimit: 0
parallelism: 1
completion count: 1
```

Source/output prefixes must be pairwise non-equal and non-ancestor/descendant.
The uploader must reject:

```text
phase1-limited-n3-gates/20260710T152820Z
phase1-semantic-audits/all45-parser-underflag-20260715T094500Z
```

as output prefixes. It never writes historical source artifacts.

## Phase completion gates

Phase 1.2A completes only when:

- protocol and acceptance gates were pushed before construction;
- development count is exactly 60;
- locked count is exactly 120;
- all 12 quotas and exact class supports pass;
- exact and normalized duplicate/overlap counts are zero;
- near-duplicate dispositions are complete;
- both reviewers complete 120/120 in both stages;
- arbitration is complete and unresolved is zero;
- locked labels are absent from Git and Docker contexts;
- private Blob membership and hashes verify exactly;
- source prefixes remain untouched;
- model-free tests pass;
- parser v2 remains unimplemented and locked evaluation remains unrun.

Permitted future claim:

> Parser v2 passed a preregistered, model-free operational conformance test
> against a sealed fixture oracle.

That claim is available only after a future one-shot PASS. It is not available
in this set-construction phase.
