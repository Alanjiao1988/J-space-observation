# Study 3 draft-v0.5 independent methods review packet

**Status:** `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW`

**Draft version:** draft-v0.5

**Document class:** review packet. This packet is drafted by the party that holds
the v0.5 operator authority. It adjudicates nothing, and it is not a review.

## 0. What this packet is, and what it is not

This packet is the reviewed object for a **fourth** bounded independent methods
review, to be conducted in a fresh session by a party that did not draft
draft-v0.5.

It does not freeze the design.
It does not authorize execution.
It does not select an interface profile.
It does not declare the amended protocol correct.

It also does not select or inspect a positive reference, resolve `OD2` or
`UR-22`, create a seed or bank, run a tokenizer or model, access confirmation
material, write scientific evidence, begin the fourth review, create draft-v0.6,
or start a feasibility pilot.

No empirical operation occurred in this round: no seed was drawn and no bank row exists.
Every operation counter is zero, every authority flag is false, and every
result field is empty or null. The evidence ledger is unchanged and still ends at
`EV-0016`.

## 1. What the third review decided

The third independent methods review of draft-v0.4, at commit
`79bcc20244ab55045ba1c5d778d829d4caac3dd3`, returned
`STUDY3_V0_4_METHODS_REVIEW_REJECTED_AMENDMENT_REQUIRED` with ten structured
findings: one BLOCKING, three MAJOR and six MINOR.

That rejection stands. No review artifact was edited, weakened, relabelled or
deleted in this round.

## 2. The ten findings and what draft-v0.5 did about them

| finding | severity | closure |
| --- | --- | --- |
| `S3MR3-001` | BLOCKING | `RESOLVED_BY_NOT_APPLICABLE_REREGISTRATION_AND_FULL_REDERIVATION` |
| `S3MR3-002` | MAJOR | `RESOLVED_BY_COMPONENT_LEVEL_CONFIRMATION_APPLICABILITY` |
| `S3MR3-003` | MAJOR | `RESOLVED_ACTIVE_TEXT_ALIGNED_HISTORY_PRESERVED` |
| `S3MR3-004` | MINOR | `RESOLVED_ENFORCEMENT_SCOPE_MATCHES_REGISTERED_SCOPE` |
| `S3MR3-005` | MINOR | `RESOLVED_S4_I4_REMOVED` |
| `S3MR3-006` | MINOR | `RESOLVED_NON_MACHINE_STATUS_REMOVED_FROM_STOP_STATES` |
| `S3MR3-007` | MINOR | `RESOLVED_NONMONOTONICITY_DISCLOSED_EXACT_N_REQUIRED` |
| `S3MR3-008` | MINOR | `RESOLVED_ROUND_REFERENCES_UPDATED` |
| `S3MR3-009` | MINOR | `RESOLVED_UNION_BOUND_CLAIM_ALIGNED` |
| `S3MR3-010` | MAJOR | `RESOLVED_DETERMINISTIC_RENDERING_SURFACE_REGISTERED` |

Every row of the closure matrix in
`studies/study3/reviews/v0_5_operator_amendment.json` carries the exact starting
evidence, the operator decision, the affected normative fields, the affected
derived fields, the committed tests, the negative mutations, the residual
limitation and the closure status. Its schema refuses a row that cites no
normative field, no committed test or no negative mutation, so no finding can be
closed by prose.

## 3. The blocking decision, stated plainly

`K6-SEP` means the separator between a **displayed option label** and its
**displayed option content**. `S1` and `S4` render labelled option lists, so the
factor has a referent for them. `S2` and `S3` render neither an option label nor
an option content, so the factor has no referent, and the two members of the
pair would be byte-identical. Under a deterministic scorer an identical prompt
yields an identical score, so such a cell would be a self-comparison whose
estimand is a plain marginal accuracy, not a joint-correctness level over a
registered presentation pair.

draft-v0.5 therefore records `K6-SEP` as `not_applicable` for `S2` and `S3`.
`not_applicable` is a third value: it is not a pass, not a zero effect, not
robustness evidence, not a gate-bearing cell and not a denominator member. No
profile-specific replacement separator is invented, and no `R-sep` duplicate of
`R-base` is rendered for the option-less profiles.

**`S2` and `S3` therefore each carry exactly ONE genuine `I3` contrast:
`K6-INSTR`.** Their per-profile `I3` claim ceiling states joint robust
correctness for that single registered pair only, and `S3`'s separately
registered conditional status continues to apply. `S1` retains its seven `K5`
pairs plus both `K6` pairs; `S4` retains the same contrast availability for
diagnostic description only and remains never selectable.

Applicability is now registered **per contrast ID** throughout, because
family-level registration cannot express this distinction. That is the same
structural defect that let the problem go undetected.

## 4. The re-derivation, including the numbers that did not change

The census is recomputed by counting **applicable contrast IDs**, not contrast
families.

| profile | I1a | I1b | I2 | K5 | K6 | I4 | total | applicable I3 contrasts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `S1` | 3 | 3 | 6 | 21 | 6 | 4 | **43** | 9 |
| `S2` | 3 | 0 | 6 | 0 | 3 | 4 | **16** | 1 |
| `S3` | 3 | 0 | 6 | 0 | 3 | 4 | **16** | 1 |
| `S4` | 3 | 3 | 6 | 21 | 6 | 0 | **39** | 9 |

`S2` and `S3` fall from 19 gate-bearing cells to 16 and from two applicable `I3`
contrasts to one.

`m_max` is the maximum total over the **selectable** profiles. The amended totals
are `S1 = 43`, `S2 = 16`, `S3 = 16`, so the maximum is still `S1`'s 43. **`m_max`
is unchanged because the profile that attains it is unchanged, not because the
value was preserved for continuity.** Consequently, and by derivation rather than
by transcription:

- per-cell false-negative budget `(19/400) / 43 = 19/17200`;
- per-cell power target `1 - 19/17200 = 17181/17200`;
- profile stage power floor `1 - 43 * (19/17200) = 381/400`;
- study end-to-end power floor `1 - 19/400 - 1/200 - 19/400 = 9/10`;
- development sizes `413`, `214`, `448` with pass counts `389`, `129`, `383`;
- confirmation pass counts `388`, `127`, `381` at component level `1/200`.

No number was preserved for continuity, and every number was recomputed from the
amended inputs.

## 5. Local power non-monotonicity

The registered sizes are the smallest unrestricted positive integers meeting the
per-cell target. The target is **not** monotone above them. Within the registered
disclosure window the target fails again at:

- `421`, `422`, `423`, `424`, `425` above `n = 413`;
- `215`, `216`, `218` above `n = 214`;
- `450`, `451`, `452`, `453`, `459` above `n = 448`.

Execution must therefore use the **exact** registered cell size. The registered
size never means "at least `n`". The registered minimum is retained rather than
replaced by an eventual-monotonicity threshold, because fresh arithmetic confirms
the design is executable at exact `n`.

## 6. The registered rendering surface

`studies/study3/protocol/interface_calibration_rendering_registry_v0_5.json` and
its schema are **binding normative inputs, not illustrative examples**. The
registry fixes the encoding, newline and normalization policy; one exact
question-stem template for every registered operation family, depth and task
stratum that can enter a gate-bearing cell; placeholder names, types, allowed
surface forms, ordering, interpolation, escaping and rejection rules; exact
option ordering and option-line grammar for `S1` and `S4`; exact label alphabets
and label-to-content separators; exact instruction sentences for every applicable
`(profile, rendering)` pair; the exact answer cue and the whitespace convention
of every candidate surface; the exact raw-completion prompt template for `S1`,
`S2` and `S3`; the exact pre-wrapper message content for `S4` and the boundary to
any role-native wrapper; the deterministic tie-break order and the exact scored
candidate surfaces; a full `(profile, rendering, contrast)` applicability table;
and a cryptographic identity for the registry and for every normative template
asset.

For `K6-SEP` the registered separator literals are `": "` for `R-base` and
`" = "` for `R-sep`, with every other prompt byte identical within the pair. For
`K6-INSTR` two exact, semantically co-referential instruction strings are
registered per applicable profile, with the answer cue and every other prompt
byte identical within the pair.

`tests/test_study3_rendering_registry_v0_5.py` instantiates this surface without
a model: 80 applicable profile/rendering/branch renders, all 32 registered
nuisance support states, byte difference within every applicable pair, structural
absence of `R-sep` for `S2` and `S3`, an explicit demonstration that the
prohibited duplicate would be byte-identical, one-factor isolation compared part
by part, and rejection of unregistered whitespace, placeholders, cues, option
counts and wrappers against the registry's own cryptographic identity.

**Tokenizer distinctness is not tested in this round**, because no checkpoint or
tokenizer may be accessed. A future fail-closed pre-bank rule is registered
instead: once checkpoints and tokenizers are separately authorized and pinned,
every gate-bearing pair must produce distinct token-ID sequences for every role
to which the cell applies, and failure makes that role/profile/contrast
`INELIGIBLE` rather than a pass. That rule does not resolve `OD2` and performs no
tokenizer call now.

## 7. What remains open

- `OD2`, the identity of the positive reference and its canonical qualification
  interface, remains `UNRESOLVED_BLOCKING_OPERATOR_DECISION`.
- `UR-22`, the external qualification interface for the positive reference,
  remains `UNRESOLVED`.
- The `RP` canonical qualification wrapper and the `RP`-specific `I4` wrapper
  remain explicitly null under `OD2`.
- `UM3-05`, the external-validity bridge, remains an unresolved future-methods
  prerequisite. A pass would apply only to the registered synthetic generator
  distributions and the named interface and checkpoint roles. It would not
  establish adequacy on an unregistered substantive task distribution. Before the
  selected instrument is relied upon outside the generator, a new authority must
  register a bridge or validation design to the target substantive distribution
  using physically isolated new data, and descriptive results observed in a future
  Study 3 run may not be retrospectively upgraded into bridge evidence.
- The original research question is **unanswered**. No interface is selected and
  none is preferred on evidence.

## 8. What the fourth reviewer is asked to determine

1. Whether recording `K6-SEP` as `not_applicable` for `S2` and `S3`, and reducing
   their per-profile `I3` claim ceiling to the single `K6-INSTR` pair, fully
   closes `S3MR3-001`, or whether a residual defect remains in the census, the
   claim ceiling, the sampling and evaluation mapping or the operation
   projection.
2. Whether a design in which two of the three selectable profiles rest on a
   single genuine `I3` contrast each is adequate for its registered purpose, or
   whether that narrowing is itself a methods defect that a later authority must
   address.
3. Whether the registered rendering surface is genuinely sufficient for an
   independent implementation to produce every applicable prompt byte with no
   further wording, punctuation, whitespace, ordering, escaping or placeholder
   choice.
4. Whether the component-level confirmation applicability is complete and
   correctly derived, and whether any row could still imply that a
   never-selectable or not-applicable profile reaches confirmation.
5. Whether the local non-monotonicity disclosure and the exact-`n` execution rule
   are adequate, or whether the registered minimum should be replaced.
6. Whether the restated union-bound conclusion matches exactly what the three
   unioned terms establish.
7. Whether the widened prohibition enforcement now matches the registered scope,
   and whether its historical exemptions are explicit and auditable rather than a
   convenient subset.

The drafting party does not claim draft-v0.5 is correct. Every repair is recorded
as `PROPOSED_RESOLVED_SUBJECT_TO_FOURTH_INDEPENDENT_METHODS_REVIEW`, and the
determination belongs to the fourth independent methods reviewer.
