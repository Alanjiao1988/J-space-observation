# Study 3 draft-v0.6 operator amendment: the scoring boundary

> **Disposition:** every repair below is recorded
> `PROPOSED_RESOLVED_SUBJECT_TO_FINAL_FOCUSED_REVIEW`.
>
> The drafting party does **not** claim draft-v0.6 is correct. draft-v0.6 is
> **not** reviewed, **not** frozen, **not** selected and **not** formally
> executable. The determination belongs to a party that did not draft it.

Authority: [`../prompts/study3_v0_6_p0_r1_authority.md`](../prompts/study3_v0_6_p0_r1_authority.md)
(19,632 bytes, sha256 `f72292e7…c19d2`, LF only, no trailing newline).

Machine-readable form: [`v0_6_operator_amendment.json`](v0_6_operator_amendment.json).

Responds to: [`../pilot/p0/results/p0-t/P0_T_DISPOSITION.md`](../pilot/p0/results/p0-t/P0_T_DISPOSITION.md).

State: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_6_COMPLETE_AWAITING_FINAL_FOCUSED_METHODS_REVIEW`

## 1. What this amendment is, and is not

draft-v0.6 changes **one** normative thing: *where* the `S2`/`S3` decision
statistic is read. It changes **no** visible byte a model would see.

It is not a fourth broad methods review, not formal execution and not a
claim-bearing research round. It does not reopen Study 1 or Study 2, and it
authorizes no bank, seed, winner, confirmation access, positive reference, `OD2`
or `UR-22` resolution, and no evidence-ledger row.

## 2. The two demonstrated defects it repairs

Stage P0-T ran once, on CPU, and published its result exactly as emitted. Two
mechanical defects are demonstrated by those immutable bytes.

**`S3P0T-001` — the registered `S2`/`S3` scoring rule is not implementable.**
draft-v0.5 registered a single next-token position immediately after the answer
cue, restricted to ten registered content token IDs. Under every pinned role
tokenizer each complete candidate surface `" 0"`..`" 9"` is **two** tokens,
`[220, digit]`, not one. The rule cannot be executed as written.

**`S3P0T-002` — the eligibility classifier propagated a role-level failure.**
`evaluate_eligibility` consulted a **role-level** flag that was false whenever
*either* the `S1` or the `S2` check failed, and then marked every `S1` cell of
that role ineligible. Because only the `S2` check failed, 27 mechanically valid
`S1` cells were marked `INELIGIBLE_TOKEN_IDS` **with an empty reason list**.

A third, smaller defect is repaired with them.

**`S3P0T-003` — the terminal label reads as the wrong quantifier.**
`STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE` reads as a
universal claim over roles; the registered semantics are existential.

## 3. The operator decision

### 3.1 The visible answer surface is preserved exactly

| item | status |
| --- | --- |
| prompt answer cue | `Answer:`, no trailing whitespace — **unchanged** |
| complete candidate surfaces | `" 0"`..`" 9"`, one leading U+0020 each — **unchanged** |
| `S1` rendering and scoring bytes | **unchanged** |
| `S4` rendering, wrapper, parser, diagnostic-only status | **unchanged** |
| every question, option, instruction, contrast, nuisance state, tuple, ground truth, candidate mapping | **unchanged** |

The space was **not** removed, **not** moved into the global answer cue, and the
numeric answers were **not** changed to letters.

### 3.2 First-discriminative-token scoring for `S2`/`S3`

Every complete candidate factors as

```
candidate_d = common_prefix || discriminant_d
```

The candidate set is eligible only if all five registered conditions hold:

| id | condition |
| --- | --- |
| `SB-1` | every complete candidate is exactly two tokens |
| `SB-2` | the first token is identical for all ten candidates |
| `SB-3` | that common token decodes byte-exactly to the registered leading U+0020 |
| `SB-4` | the second token IDs are pairwise distinct and map byte-exactly to `0`–`9` in registered order |
| `SB-5` | no BOS, EOS, chat template, normalization, padding, truncation or implicit whitespace transformation participates |

For `S2`, the scoring context is the registered prompt token IDs **followed by**
the verified common-prefix token, formed by concatenation and never by
re-encoding a concatenated string. One ordinary prefill evaluation is performed
on that context, and the next-token logit vector is read **only** at the ten
verified discriminant token IDs. The deterministic restricted argmax is mapped
back to the complete registered candidate surface.

The common prefix is a **teacher-forced candidate prefix**. It is not a
prompt-rendering change, not a generated token, and not a separate
sequence-level model evaluation.

For `S3`, the exact `S2` discriminant-position logit vector is reused on CPU.
`S3` adds zero model evaluations, model loads, prefills, decodes and generations.

Explicitly prohibited: scoring the shared first token, pretending the two-token
candidate is one token, summing unrelated positions, using free generation, and
introducing a new calibration parameter.

### 3.3 The equivalence is exact, not approximate

For every prompt `x` and candidate digit `d`, with `u` the common token and
`v_d` the unique digit token:

```
P(u, v_d | x) = P(u | x) * P(v_d | x, u)
```

`P(u | x)` does not depend on `d`, so it is a strictly positive common factor of
all ten complete-candidate probabilities and cancels from the ranking:

```
argmax_d P(u, v_d | x) = argmax_d P(v_d | x, u)
```

This is an **exact factor cancellation**, not an approximation. It is valid here
because the registered decision statistic is a deterministic candidate argmax,
all ten candidates share the same two-token structure and the same common prefix,
and the registered digit-order tie break is preserved unchanged. It is asserted
mechanically on every scored two-token row.

The claim does **not** extend to arbitrary multi-token candidates, unequal
lengths, non-common prefixes, summed log probabilities, free generation, or any
tokenizer that is not separately pinned and verified.

## 4. The token identities are derived, not transcribed

The common-prefix token and the ten discriminant token IDs are **recovered from
the immutable published P0-T result and the frozen corpus** by
[`../pilot/p0_r1/p0_r1_factorization.py`](../pilot/p0_r1/p0_r1_factorization.py),
which performs **zero** tokenizer encodes and imports no tokenizer library.

The verifier binds 70 published `(prompt, token-ID)` pairs per role to the exact
frozen prompt bytes by SHA-256, then solves for the byte string each token
contributes, requiring the common-prefix token and each discriminant token to be
**uniquely** determined by that evidence. A token whose byte string is not
uniquely determined is reported as an unresolved ambiguity rather than guessed.

| role | common prefix | decodes to | discriminants | decode to |
| --- | --- | --- | --- | --- |
| `RT` | `220` | one U+0020 | `15`–`24` | `0`–`9` |
| `RL` | `220` | one U+0020 | `15`–`24` | `0`–`9` |
| `RI` | `220` | one U+0020 | `15`–`24` | `0`–`9` |

A committed test asserts that **no member of `{220, 15..24}` appears as a numeric
literal anywhere in the verifier**, so the identities cannot have been
transcribed.

## 5. The repaired eligibility classifier

Eligibility is computed at the **narrowest applicable key**:

| quantity | key |
| --- | --- |
| candidate-surface eligibility | role × profile |
| presentation-pair distinctness | role × profile × contrast |
| structural absence | profile × contrast |
| target-role executability | role |

Every reason carries its own scope, and the production validator rejects any
reason whose scope is not a prefix of the cell it is attached to. A failure
therefore cannot cross a profile, a role or a contrast. An ineligible row with an
empty reason list is a **validator failure**, not an output. `S4` is
diagnostic-only and can never satisfy target-role executability.
`not_applicable` is structural absence: never instantiated, never eligible, never
ineligible, never a pass, never a zero, never a denominator row and never
robustness evidence.

Replaying the immutable P0-T records through the successor classifier gives:

| view | cells | eligible | ineligible | empty-reason ineligible | executable genuine `I3` contrasts per role |
| --- | --- | --- | --- | --- | --- |
| historical P0-T, as emitted | 39 | 6 | 33 | **27** | 0 |
| classifier repair **only**, v0.5 rule unchanged | 39 | 33 | 6 (3 `S2`, 3 `S3`) | **0** | **9** |
| classifier repair **and** the v0.6 boundary | 39 | 39 | 0 | **0** | **11** |

The middle row is the mechanical confirmation that the emitted historical
terminal state was over-severe, exactly as the published disposition discloses.
All 27 repaired cells are `S1` cells.

The successor stop label is

```
STUDY3_P0_R1_STOPPED_SOME_TARGET_ROLE_HAS_NO_EXECUTABLE_GENUINE_I3_CONTRAST
```

whose registered semantics are "one or more target roles has no executable
genuine `I3` contrast". The old label survives **only** as historical text
attached to the consumed P0-T result.

## 6. What changed in the numbers, and what did not

Every quantity below is **recomputed** from
[`../analysis/design_statistics.py`](../analysis/design_statistics.py) at
derivation time and compared. No number is copied forward for continuity.

### Unchanged, by derivation

| quantity | value |
| --- | --- |
| `m_max` | `43` |
| per-cell false-negative budget | `19/17200` |
| per-cell power target | `17181/17200` |
| profile stage power floor | `381/400` |
| study end-to-end power floor | `9/10` |
| development sizes | `413` / `214` / `448` |
| development pass counts | `389` / `129` / `383` |
| confirmation pass counts | `388` / `127` / `381` |
| total gate-bearing cells | `S1` 43, `S2` 16, `S3` 16, `S4` 12 |
| sequence-level development projection | `31,065` |

**Why nothing moves.** The new boundary changes where one logit vector is read
and adds one teacher-forced token to the `S2` scoring context. It changes no
cell, no contrast applicability, no independent unit, no null, no alternative, no
alpha and no decision rule, so no sample size, pass count, budget, floor or
projection is mathematically required to move.

### Changed, and surfaced rather than absorbed

**1. `S2`/`S3` scoring-context token count.** From
`registered_prompt_token_count` to `registered_prompt_token_count + 1`.

| scope | extra tokens processed | extra sequence-level evaluations |
| --- | --- | --- |
| P0-R1 (18 `S2` rows) | `18` | `0` |
| development projection (5,001 `S2` rows) | `5,001` | `0` |

Both `registered_prompt_token_count` and `scoring_context_token_count` are now
recorded per profile, and they reconcile with the per-row rule.

**2. The `S3` zero-incremental-cost condition.** draft-v0.5 stated it for "a
jointly single-token registered answer domain", which the pinned tokenizers do
not provide. It is restated at the discriminant position: a registered answer
domain whose complete candidates share one common prefix token and differ in
exactly one discriminant token, rescored from the identical `S2` scoring context.
The numeric effect is **none** — `S3` incremental rendered rows, scored rows and
sequence-level evaluations all remain `0` — but the condition is now true of the
surface actually registered.

## 7. Boundary

`OD2`, `UR-22` and every `RP` object remain unresolved; the `RP` wrapper remains
**null**, not empty. Study 3 remains unfrozen. No interface or positive reference
is selected. No seed, bank, development result, confirmation access, winner or
evidence row exists. Every tokenizer, checkpoint, GPU, model and formal counter
remained exactly zero in this session. `paper/evidence_ledger.csv` is
byte-identical and still ends at `EV-0016`. The original research question
remains unanswered.

## 7a. A structural constraint, disclosed rather than hidden

The normative scoring-boundary registration lives entirely in the **new v0.6
rendering and scoring registry and its committed schema**, and the draft-v0.5
protocol JSON, its Markdown companion and the protocol schema are left
**byte-identical to the baseline**. That placement is forced, and the reason is
worth stating plainly.

The immutable P0 corpus manifest at
[`../pilot/p0/corpus/p0_corpus_manifest.json`](../pilot/p0/corpus/p0_corpus_manifest.json)
byte-binds `interface_calibration_protocol_draft.json` at 418,733 bytes, sha256
`1197e087…3c7ca7`, as a generator identity. Editing that file makes the immutable
manifest stop reproducing and fails
`tests/test_study3_p0_feasibility_pilot.py::test_frozen_corpus_re_derives_byte_exactly`,
one of the 122 historical P0 tests §10 requires to be retained. §9 forbids
editing any byte under `studies/study3/pilot/p0/` and forbids editing that test
module, so neither the manifest nor the test may be adjusted to accommodate an
edit.

This was **observed, not assumed**. An additive `scoring_boundary_v0_6` block was
drafted into the protocol JSON, Markdown companion and schema, published to a
working commit and validated in the registered CPU route. Full-suite run `cmf4`
recorded the exact consequence: 4,262 historical passes plus 77 net-new, with
`test_frozen_corpus_re_derives_byte_exactly` failing. The three protocol files
were then reverted to their baseline bytes and the immutable manifest reproduces
again.

The consequence for future rounds: **the draft protocol JSON is effectively
frozen for as long as the published P0 artifacts must reproduce byte-exactly.**
That is a real structural constraint on any later amendment, and the focused
review should weigh whether the v0.6 registry is a sufficient normative home for
the scoring boundary or whether a different arrangement is required.

## 8. The only legal next actions

1. One **fresh, focused final methods review of draft-v0.6**, by a party that did
   not draft it, limited to the first-discriminative-token factorization, the
   classifier repair, the affected accounting and the consistency of the
   resulting candidate. It is not another general review of every historical
   artifact.
2. Separately, the **P0-R1 replay gate** followed by the repaired model pilot,
   continued from the published P0-R1 registration commit.

Not a freeze. Not a seed. Not a bank. Not a selection. Not a confirmation access.
