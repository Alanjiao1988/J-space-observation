# Phase 1 prospective parser-v2 protocol

## Registration

- Protocol version: **parser-v2-v1.2**
- Phase: **1.2A / Path C**
- Status: **preregistered before fixture construction**
- Historical experimental target:
  `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
- Engineering and audit agents: `gpt-5.6-sol`, reasoning effort `max`
- Parser v2 implemented in this phase: **no**
- Locked parser evaluation in this phase: **no**
- Higher-n behavioral run authorized: **no**

The first Git commit containing this document,
`docs/phase1_evaluator_validation_set.md`, and
`docs/phase1_parser_v2_acceptance_gates.json` freezes the protocol. Case
construction cannot begin before that commit is pushed to `origin/main`.

Version 1.1 added the finite canonical-rendering bound required to make
scientific-notation normalization executable under adversarial exponents.
Version 1.2 adds machine-bound independent curator-pool seals and an immutable
Stage-2 reference packet. Any candidate pool produced under superseded protocol
bytes is construction-ineligible and must be regenerated after the version 1.2
commit.

## Scientific boundary

Phase 1.2A is model-free evaluator engineering on constructed fixtures. These
fixtures are not outputs or behavioral observations of
`deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`. No target-model inference,
download, or load occurs, and no new behavioral evidence is created. LLM
consensus labels are operational references, not human ground truth. Parser
validation measures surface answer extraction only; it is not hidden-reasoning,
internal-workspace, invisible-CoT, genuine-no-CoT, or J-space evidence.
Historical cells remain n=3. `stopped_intervention` remains
intervention-controlled; `postprocessed_utility` remains answer-recovery
utility, not raw no-CoT.

The fixtures form a quota-balanced operational conformance benchmark. They are
not probability sampled and do not estimate natural output prevalence,
population reliability, stability, robustness, or generalizability. Path C is
not Phase 1 Branch C.

## Motivation and legacy preservation

The bounded n=3 all-45 audit found 18 legacy ambiguity overflags, 15
last-number risks, 14 observed extraction disagreements, two material
correctness changes, and 19 material evaluator issues. It found no semantic
ambiguity positive among the 45 historical records. That historical audit
motivates this prospective protocol but contributes no locked test cases.

The legacy parser in `src/jspace_observation/eval_parsing.py` remains unchanged.
Its current last-number fallback, parser fields, stored records, metrics, and
classifications remain historical artifacts. Future evaluation must dual-report
legacy and parser-v2 results; it must not overwrite or relabel history.

## Extraction-only interface

Parser v2 has an extraction-only request:

```text
parse_v2({
  "schema_version": "phase1-parser-v2-request/v1",
  "answer_type": "numeric",
  "output_text": "<exact selected output>"
}) -> ParserV2Result
```

The request has exactly those three fields. Extra fields fail closed. The
parser receives no case ID, task, question, expected answer, registered
reference answer, ground truth, correctness, model, condition, branch,
stratum, curation metadata, filesystem path, network handle, registry, or
arbitrary keyword arguments.

The future prediction runner validates each outer locked-input record, then
projects only `output_text` and the fixed `numeric` answer type into this exact
three-field request. Outer `case_id`, `source_kind`, and artifact metadata are
never passed to the parser. The runner persists a separate prediction envelope
containing `case_id`, the input-record SHA-256, the exact request SHA-256, and
the parser result. It seals every prediction envelope before a separate scorer
is allowed to load reference labels. This makes reference-answer-guided
candidate selection impossible through the registered interface, while
remaining procedural rather than a security-enforced isolation claim.

## Prospective result schema

Parser v2 returns exactly:

```text
schema_version
parser_version
answer_type
input_sha256
answer_presence
parse_valid
parse_ambiguous
parsed_answer
candidate_answers
evidence_spans
extraction_strategy
output_quality
failure_reasons
format_warnings
```

Field definitions:

```text
schema_version:
  phase1-parser-v2-result/v1

parser_version:
  immutable implementation digest

answer_type:
  numeric

input_sha256:
  SHA-256 of the exact UTF-8 output_text bytes

answer_presence:
  present | absent | uncertain

parse_valid:
  boolean

parse_ambiguous:
  boolean

parsed_answer:
  canonical numeric string or null

candidate_answers:
  ordered unique canonical values from the selected evidence tier

evidence_spans:
  exact half-open spans in the original output_text

extraction_strategy:
  boxed_answer
  explicit_final_marker
  explicit_answer_marker
  terminal_equation
  single_candidate
  none
  ambiguous_candidates

output_quality:
  complete
  truncated
  malformed_recoverable
  malformed_unrecoverable
  placeholder
  empty

failure_reasons:
  closed ordered list

format_warnings:
  closed ordered list
```

All arrays are present even when empty. JSON objects reject extra properties,
duplicate keys, non-finite JSON values, invalid enums, and invalid scalar
types. Candidate and warning order is deterministic.

## Field invariants

The three registered typed decisions are:

```text
present:<canonical value>
ambiguous
no_answer
```

They derive from result fields as follows:

| Typed decision | Required fields |
|---|---|
| `present:v` | `answer_presence=present`, `parse_valid=true`, `parse_ambiguous=false`, `parsed_answer=v`, one selected acceptable span |
| `ambiguous` | `answer_presence=uncertain`, `parse_valid=true`, `parse_ambiguous=true`, `parsed_answer=null`, at least two distinct selected-tier candidates |
| `no_answer` | `answer_presence=absent`, `parse_valid=false`, `parse_ambiguous=false`, `parsed_answer=null`, no selected span |

Additional invariants:

- `parsed_answer` is non-null only for `present`.
- `candidate_answers` contains unique normalized values from the first
  applicable evidence tier, ordered by first source occurrence.
- Equivalent repeated claims collapse to one candidate value while retaining
  their separate evidence spans.
- Every candidate maps to at least one exact original-output evidence span.
- `failure_reasons` is empty for a valid parse. Non-fatal warnings never change
  validity.
- Multiple numeric mentions alone do not imply ambiguity.
- Truncated or malformed output alone does not imply ambiguity.
- A recoverable malformed output may still be `present`.
- No-answer output may contain incidental numeric distractors.
- Parser v2 does not determine no-CoT validity, reasoning visibility, task
  correctness, intervention status, or branch classification.

## Numeric grammar and exact normalization

Only ASCII numeric surfaces are registered.

Decimal/scientific grammar:

```text
[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]+)?
```

Simple fraction grammar:

```text
[+-]?[0-9]+/[0-9]+
```

Fractions permit no internal whitespace, decimal/scientific numerator or
denominator, signed denominator, mixed number, or zero denominator. Numeric
tokens are at most 100 ASCII characters. Their canonical reduced-rational
rendering is at most 4096 ASCII characters, including a slash and sign.
Exponent magnitude and resulting rendering length are checked before any
power, integer, or output allocation. A surface that would exceed this bound is
unsupported and fails deterministically. Numeric tokens must not be embedded
in an identifier, version, date, percentage, or unit-bearing token.

Every accepted literal is converted exactly to a reduced rational:

1. Decimal/scientific forms are interpreted exactly, never through `float`.
2. The denominator is positive.
3. Numerator and denominator are divided by their greatest common divisor.
4. A denominator of one renders as the integer numerator.
5. Otherwise the result renders as `numerator/denominator`.
6. Every signed zero renders as `0`.

Examples:

```text
+0012       -> 12
-0.000      -> 0
.5          -> 1/2
1.25        -> 5/4
5e-1        -> 1/2
-6/8        -> -3/4
```

Commas, percentages, units, mixed numbers, expressions, calculation, repair,
tolerance, NaN, and Infinity are prohibited. Equality is exact canonical-string
equality. The parser never chooses a candidate because it equals a reference.

## Think-region handling

Balanced, case-insensitive `<think>...</think>` regions are excluded from final
answer evidence while original string offsets are retained. Nested, stray, or
unclosed tags produce quality/warning annotations. An unclosed opening tag
excludes its suffix from extraction. An answer found only inside excluded
thinking is not a final answer.

This is an extraction rule only. It does not establish no-CoT behavior or
hidden reasoning.

## Evidence priority

The first tier containing a complete answer claim controls the decision:

1. Complete balanced `\boxed{literal}` evidence.
2. A word-bounded `Final answer`, `Answer`, `Final`, or `The answer is` marker
   followed by an ASCII/full-width colon, equals sign, `is`, or whitespace and
   a literal.
3. The right-hand literal of an equation ending the final substantive line.
4. A single candidate only when the residual answer-bearing segment is one
   literal plus harmless delimiters or punctuation.
5. Multiple same-tier distinct values with no registered resolution are
   ambiguous.
6. No reliable complete answer evidence is no answer.

Equivalent values at one tier are not ambiguous. Conflicting values at one
tier are ambiguous. A later explicit revision such as "Correction: Final
answer: ..." resolves an earlier claim only when the fixture reference labels
register the revision relation. Lower-tier or merely later numeric material
cannot override higher-tier evidence. An invalid complete higher-tier claim
fails closed. An incomplete higher-tier construct may fall through only with a
registered warning.

Unconditional last-number selection, reference-answer matching, arbitrary
intermediate-number selection, and position-only selection are prohibited.

## Evidence spans

Each evidence span is:

```text
start:
  zero-based inclusive Unicode-code-point offset

end:
  zero-based exclusive Unicode-code-point offset

text:
  output_text[start:end], exactly

kind:
  boxed
  explicit_final_marker
  explicit_answer_marker
  terminal_equation
  single_candidate

normalized_answer:
  canonical value

disposition:
  selected
  equivalent
  ambiguous_candidate
```

There is exactly one `selected` span for a unique present answer. Operational
labels may register more than one acceptable selected span when equivalent
claims repeat. Wrong-span scoring compares the parser-selected span with that
frozen acceptable set. S06 labels separately register the rightmost distractor
span; it is never an acceptable answer span.

## Quality, failure, and warning vocabularies

`output_quality` is a single dominant category with this precedence:

```text
empty
placeholder
malformed_unrecoverable
malformed_recoverable
truncated
complete
```

Closed failure reasons:

```text
empty_output
placeholder_without_answer
truncated_before_final_answer
malformed_without_reliable_answer
unsupported_numeric_literal
no_reliable_answer
```

Closed non-fatal warnings:

```text
multiple_numeric_mentions
reasoning_continues_after_answer
equivalent_repeated_claim
lower_priority_conflict_ignored
incomplete_box
unbalanced_think_tag
stray_think_tag
redundant_answer_marker
noncanonical_numeric_surface
incidental_numeric_material
```

## Correctness is a separate layer

After extraction predictions are sealed, a scorer may load the registered
reference answer and apply the same exact rational normalizer:

```text
parser_correctness =
  parse_valid
  and not parse_ambiguous
  and parsed_answer == canonical(registered_reference_answer)
```

`ambiguous` and `no_answer` are incorrect for task-correctness purposes.
Operational expected correctness uses the same rule on the consensus parser
decision. A material correctness error is the XOR of parser correctness and
operational expected correctness. Correctness cannot feed back into extraction.

## Future dual report

The one-shot locked evaluation, when separately authorized, must run:

```text
legacy parser
prospective parser v2
```

Both receive the same parser-facing output text. The legacy parser remains
unchanged and is adapted reference-blind to the registered typed decision:

1. If legacy `parse_ambiguous` is true, the decision is `ambiguous`, regardless
   of its simultaneous `parse_valid` or non-null answer fields.
2. Otherwise, if legacy `parse_valid` is true, `parsed_answer` is non-null, and
   that value passes the registered exact rational normalizer, the decision is
   `present:<canonical value>`.
3. Otherwise the decision is `no_answer`.

Legacy warnings, candidate lists, reference answers, and correctness do not
alter this precedence. A non-normalizable legacy answer is reported as an
adapter failure diagnostic and maps to `no_answer`; it does not make the
locked evaluation INVALID. The adapter changes no stored legacy record or
metric.

Results remain separate and use the same frozen typed-decision scorer for
comparison. Span-based absolute gates apply to parser v2 only because the
legacy parser has no registered evidence-span interface. Parser v2 passes only
if every
absolute gate in `docs/phase1_parser_v2_acceptance_gates.json` passes, the
registered clean-strata non-regression gate passes, and at least one registered
critical stratum strictly improves. A worse legacy parser never grants an
automatic pass.

## One-shot policy

This phase creates and seals the set but does not evaluate a parser.

Before future unseal:

1. Parser-v2 implementation commit and tests are frozen and pushed.
2. Runtime bundle and image digest are recorded.
3. Protocol, acceptance-gate, command, and configuration hashes are bound.
4. Predictions are produced and sealed without labels or references.
5. Labels are read only by the later scoring stage.
6. The result is retained whether PASS or FAIL.

After the first authorized locked-input read, the prediction stage is not
rerun. After label read, no rescore is allowed. A failed scientific result
retires the holdout; a later parser version needs a new independent locked set.
Only the byte-identical infrastructure recovery rules in the evaluator-set
protocol are eligible for a retry.

## Protocol hashes

The protocol bundle contains the Git blobs from the freezing commit, in this
exact order:

```text
docs/phase1_parser_v2_protocol.md
docs/phase1_evaluator_validation_set.md
docs/phase1_parser_v2_acceptance_gates.json
```

`.gitattributes` requires LF Git blobs for all three files. Hashes are computed
from `git show <freezing-commit>:<path>` bytes, never from checkout-dependent
working-tree bytes. The bundle SHA-256 hashes domain
`jspace-parser-v2-validation/protocol-bundle/v1\0`, then for each file:
4-byte big-endian ASCII path length, path bytes, 8-byte big-endian content
length, and exact file bytes.

The acceptance-gate SHA-256 is the hash of the exact freezing-commit Git blob
for `docs/phase1_parser_v2_acceptance_gates.json`. Both hashes and the freezing
Git commit are recorded publicly after the protocol commit; adding that
execution record does not alter the already frozen byte bundle.
