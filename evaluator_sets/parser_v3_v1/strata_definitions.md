# parser-v3-v1 locked set: stratum definitions and quotas

Set id: `parser-v3-v1`
Total cases: **120**
Strata: **12**
Cases per stratum: **10**

This file is public. It contains stratum definitions, quotas and subtype slots only.
It contains no case text and no labels.

## Composition

| Stratum | Name | n | Answer presence (registered) |
| --- | --- | --- | --- |
| S01 | boxed single answer | 10 | present |
| S02 | explicit final-answer marker | 10 | present |
| S03 | terminal equation | 10 | present |
| S04 | multiple intermediate numbers | 10 | present |
| S05 | final answer followed by reasoning | 10 | present |
| S06 | last-number trap | 10 | present |
| S07 | truncated before answer | 10 | no_answer |
| S08 | explicit no-answer / placeholder | 10 | no_answer |
| S09 | malformed recoverable | 10 | present |
| S10 | malformed unrecoverable | 10 | no_answer |
| S11 | true multiple-candidate ambiguity | 10 | ambiguous |
| S12 | numeric normalization | 10 | present |

Registered totals: `present` 80, `no_answer` 30, `ambiguous` 10.

`critical_case` is true for every stratum outside the clean set `{S01, S02, S03, S12}`,
so 80 of 120 cases are critical.

## Stratum definitions

### S01 — boxed single answer
The output commits to a single answer inside `\boxed{...}`. The box is well formed and
is the highest-priority construct present. Includes display math, inline math, nested
formatting inside the box, spacing inside the braces, and boxes that are not the final
line of the output.

### S02 — explicit final-answer marker
The output commits to a single answer behind an explicit final-answer marker
(`Final answer:`, `Final:`, `FINAL ANSWER`, `Final =`, `The final answer is`, and
full-width or spaced variants). No box is present.

### S03 — terminal equation
The last meaningful line is an equation whose right-hand side is the answer. No box and
no explicit answer marker fires.

### S04 — multiple intermediate numbers
A worked solution containing several intermediate numeric surfaces, ending in a single
committed answer. Tests that intermediate arithmetic is not mistaken for the answer.

### S05 — final answer followed by reasoning
The answer is stated and then substantive reasoning, verification or commentary
continues after it. Tests that a marker earlier in the output still wins over trailing
material.

### S06 — last-number trap
The output states its answer, then a **different** number appears after it in
non-answer material (a citation, a step index, a timestamp, a distractor equation, a
unit conversion note). Every trailing distractor canonicalises to a value different from
the answer. Tests last-number heuristics directly.

### S07 — truncated before answer
Generation stops before the answer is committed: mid-sentence, mid-equation, mid-box,
mid-marker, or inside an unclosed reasoning block.

### S08 — explicit no-answer / placeholder
The output explicitly declines, states that it cannot determine the answer, or emits a
placeholder. No numeric commitment is made.

### S09 — malformed recoverable
Structure is broken — mangled box, split marker, stray or unbalanced reasoning tags,
duplicated delimiters — but exactly one answer is still reliably recoverable.

### S10 — malformed unrecoverable
Structure is broken **and** no reliable answer survives: illegal literals (zero
denominator, doubled sign, digits split by spaces, exponent beyond the registered
bound), destroyed equations, or answer text that never resolves to a legal literal.

### S11 — true multiple-candidate ambiguity
Two or more candidates tie at the highest tier that fires and canonicalise to
**different** values. Every S11 case carries at least two distinct canonical candidates.
Repetition of the same value is deliberately excluded from this stratum — it belongs to
`equivalent_repeated_claim`.

### S12 — numeric normalization
A single unambiguous answer whose **surface** is non-canonical: padded zeros, explicit
`+`, unreduced fraction, trailing zeros, leading-point decimal, scientific notation,
`-0`. Tests canonicalisation rather than location.

## Subtype slots

Each stratum is divided into **5 subtype slots with 2 cases each**, mirroring the
parser-v2 locked set. Slots vary the surface realisation of the stratum (delimiter
style, marker spelling, position in the output, distractor family, literal family).

## Cross-cutting quotas (all verified by the builder)

| Quota | Requirement | Actual |
| --- | --- | --- |
| Cases per stratum | exactly 10 | 10 in all 12 strata |
| Registered presence split | 80 / 30 / 10 | 80 present, 30 no_answer, 10 ambiguous |
| Reference-correct per answer-bearing stratum | exactly 5 correct + 5 incorrect | satisfied in S01–S06, S09, S12 |
| Negative answers | >= 10 | 30 |
| Decimal surfaces | >= 10 | 35 |
| Fraction surfaces | >= 10 | 54 |
| Balanced reasoning-tag regions | >= 10 | 10 |
| Malformed / stray / unclosed reasoning-tag regions | >= 10 | 10 |
| Incidental-distractor cases in each of S07, S08, S10 | >= 5 each | satisfied |
| S06 trailing distractor differs canonically from the answer | all 10 | 10 |
| S11 distinct canonical candidates | >= 2 per case | 10 |

## Deliberate coverage gap

The set contains **no empty or whitespace-only output**. The parser-v2 protocol assigned
its single empty-output case to the parser-v2 *development* set, so any whitespace-only
parser-v3 case would collapse to the same normalized fingerprint and violate the
zero-normalized-overlap requirement. As a consequence the `empty` output quality and the
`empty_output` failure reason are **not exercised by this set**. This is a
protocol-driven, deliberate gap, not an oversight.

## Span-boundary variation

S01, S02, S05 and S06 are required to carry strictly more span-boundary variation than
the parser-v2 development set. The gate and the measured result are documented in
`docs/phase1_parser_v3_locked_set.md`.
