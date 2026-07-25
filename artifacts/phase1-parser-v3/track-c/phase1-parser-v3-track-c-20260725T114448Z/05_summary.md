# Summary

Parser v3 was developed from the parser-v2 locked FAIL and evaluated against
public development gates only. All applicable development gates pass. Parser v3
is **not validated**.

## Objective

Diagnose the two failed parser-v2 locked gates (`boxed_final_miss` 1/20,
`wrong_span` 2/80) and implement a standalone, reference-blind parser v3 that
repairs the underlying rule defects without weakening any fail-closed guard.

## Scope

In scope: failure-directed diagnosis, `src/jspace_observation/eval_parsing_v3.py`,
65 new public adversarial development fixtures, tests, and
development-gate evaluation on public material.

Out of scope: any validation claim, any modification of frozen sources, any
scoring of the retired 120-case parser-v2 holdout, and construction of the new
independent locked holdout.

## Provenance

- code_commit: `bc6d7b70c7794055a33401b8b7b0aa7c027f2e3f`
- parser v3 algorithm_id: `jspace-parser-v3-reference-blind-extraction/v1`
- parser v3 parser_version: `0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace`
- parser v3 source_sha256: `76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9`
- frozen protocol hash: `417d9ff5d27b17ce588b7713a1b1072fb32ef21a03fd135e4e339719db28866b`
- model_id / model_revision / image_digest / hardware: `not_applicable`
  (deterministic, model-free, CPU-only track)

## Execution

Deterministic single pass. Each case was parsed once by parser v3 and once by
parser v2 through the identical three-field request contract, then scored
against the declared oracle. No sampling, no seeds, no retries.

## Results

- parser v3 vs parser v2, 60 frozen public development rows: 60/60 field-exact
- parser v3 typed agreement, 60 public development rows: 60/60
- parser v3 typed agreement, 65 adversarial rows: 65/65
- parser v2 typed agreement, 65 adversarial rows: 50/65 (report only)
- boxed_final_miss (S01+S02 pooled, n=29): 0 errors
- wrong_span (expected-present pooled, n=88): 0 errors
- last_number_trap (S06 pooled, n=9): 0 errors
- material correctness errors (pooled, n=125): 0
- reference-blind extraction structurally enforced: true
- frozen legacy and v2 sources byte-identical: true

## Decision

Status: **COMPLETE**. Every applicable development gate passes. One criterion is
`not_applicable`: the four retired mismatch cases could not be re-scored because
their case text is unavailable to this track.

## Deviations and errors

One registered deviation: `retired_mismatch_resolution` is unevaluated. See
`08_deviations.json`.

## Scientific interpretation

The parser-v2 failures are consistent with recall defects rather than precision
defects: decoration-intolerant payload grammars, a separator rule narrower than
the registered protocol, and a unit-word rule that invalidated otherwise
unambiguous claims. Parser v3 widens exactly those rules. Every widening is
justified from the frozen protocol and exercised by at least one new adversarial
fixture that is independent of any retired case.

## Limitations

Parser v3 was developed with knowledge of which retired cases parser v2 failed,
but without their text. Development-set agreement is therefore an upper bound on
held-out behaviour and carries no generalization claim. Three of the four retired
mismatch cases remain diagnostically unresolved; the diagnosis for them is
hypothesis-ranked, not confirmed.

## Paper relevance

Supplies the failure-directed development record for the parser section: what
the locked FAIL implies about the parser-v2 rule set, which rules were changed,
and why the resulting evidence is development evidence only.

## Next gate

One-shot locked evaluation of parser v3 against the new independent locked
holdout, scored once under the frozen acceptance gates.
