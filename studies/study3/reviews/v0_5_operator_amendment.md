# Study 3 draft-v0.5 bounded operator amendment

Record class: operator amendment. This document is **not** a methods review and does
not adjudicate itself. It is drafted by the party that holds the v0.5 operator
authority, and its only legal successor is a fresh-session **fourth independent
methods review of published draft-v0.5 by a party that did not draft it**.

## 1. Round identity

| field | value |
| --- | --- |
| round | draft-v0.5 bounded operator amendment |
| authority | `studies/study3/prompts/study3_v0_5_design_amendment_authority.md` |
| authority sha256 | `b9f0023052c9056de1707ba64a8686a8df05d260cbf7aae0673c31d2dc3aadc6` |
| authority bytes | 27458 |
| starting commit | `79bcc20244ab55045ba1c5d778d829d4caac3dd3` |
| starting tree | `3855a579d0174d2c45587cba248e96d42c319664` |
| answers | the ten `S3MR3-*` findings of the third independent methods review |
| terminal disposition | `STUDY3_DRAFT_V0_5_BOUNDED_AMENDMENT_PUBLISHED_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW` |

## 2. Initial closure matrix

This section is recorded in the pre-drafting derivation commit, before any v0.5
drafting output exists or is read. Every row starts `OPEN_NOT_YET_DRAFTED`. A row
may only move to its required status when normative bytes, a positive assertion and
a relevant negative mutation all exist.

| finding | severity | required v0.5 closure | initial status |
| --- | --- | --- | --- |
| S3MR3-001 | BLOCKING | `RESOLVED_BY_NOT_APPLICABLE_REREGISTRATION_AND_FULL_REDERIVATION` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-002 | MAJOR | `RESOLVED_BY_COMPONENT_LEVEL_CONFIRMATION_APPLICABILITY` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-003 | MAJOR | `RESOLVED_ACTIVE_TEXT_ALIGNED_HISTORY_PRESERVED` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-004 | MINOR | `RESOLVED_ENFORCEMENT_SCOPE_MATCHES_REGISTERED_SCOPE` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-005 | MINOR | `RESOLVED_S4_I4_REMOVED` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-006 | MINOR | `RESOLVED_NON_MACHINE_STATUS_REMOVED_FROM_STOP_STATES` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-007 | MINOR | `RESOLVED_NONMONOTONICITY_DISCLOSED_EXACT_N_REQUIRED` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-008 | MINOR | `RESOLVED_ROUND_REFERENCES_UPDATED` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-009 | MINOR | `RESOLVED_UNION_BOUND_CLAIM_ALIGNED` | `OPEN_NOT_YET_DRAFTED` |
| S3MR3-010 | MAJOR | `RESOLVED_DETERMINISTIC_RENDERING_SURFACE_REGISTERED` | `OPEN_NOT_YET_DRAFTED` |

## 3. Scope boundary declared before drafting

This amendment is a design round only. It does not freeze Study 3, authorize
execution, select an interface, select or inspect a positive reference, resolve
`OD2` or `UR-22`, create a seed or bank, run a tokenizer or model, access
confirmation material, write scientific evidence, begin the fourth review, create
draft-v0.6, or start a feasibility pilot.

`OD2`, `UR-22` and the RP wrapper decisions remain unresolved and are not advanced.

## 4. Immutable objects this amendment may not edit

- every first-, second- and third-review authority, report, JSON, schema, receipt,
  recalculation program, recalculation table and review-specific test module;
- every earlier operator-amendment authority and record;
- the historical-harness erratum and its reviewed-commit anchoring semantics;
- every earlier finding, severity, disposition, reviewed-artifact identity,
  disclosed error, and failed or aborted run;
- every evidence-ledger row through `EV-0016`.

The final closure matrix, the substantive decisions and the validation envelope are
recorded in later commits of this same amendment. This section is the pre-drafting
record required by section 2 of the authority.
