# Study 3 draft-v0.7 — operator terminal decision

> **Decision:** `STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION`
>
> draft-v0.7 is **rejected and terminally closed without repair**. It is not
> frozen, not selected, not executable and **not amendable**. No v0.7.1, no v0.8
> and no incremental carry-forward repair is permitted.
>
> The authorized continuation is a clean-room successor, **Study 3R**, whose
> protocol is not authored here.

| item | value |
| --- | --- |
| reviewed commit / tree | `459d002442641039196ac3880d47a45a3b79a4c8` / `2c84d55e6a965972e7cd3f69e3b0cded0bddfb04` |
| independent review head | `a08ec1462f023da49247cac0756b7af5f32ba75a` |
| governing assessment | [`v0_7_single_focused_methods_review.md`](v0_7_single_focused_methods_review.md) · [`.json`](v0_7_single_focused_methods_review.json) |
| review disposition | `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED` |
| severity counts | **12 BLOCKING, 3 MAJOR, 2 MINOR** |
| authority | [`../prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md`](../prompts/study3_v0_7_terminal_decision_and_study3r_successor_authority.md) |
| machine-readable form | [`v0_7_operator_terminal_decision.json`](v0_7_operator_terminal_decision.json) |
| schema | [`v0_7_operator_terminal_decision.schema.json`](v0_7_operator_terminal_decision.schema.json) |
| successor charter | [`../../study3r/CHARTER.md`](../../study3r/CHARTER.md) |

## 1. The governing assessment

The single independent focused methods review of draft-v0.7, performed by a party
that did not draft it, returned `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`
with twelve BLOCKING, three MAJOR and two MINOR findings.

The operator **accepts that review as the governing assessment of draft-v0.7**.
Its findings are adopted as written. None of them is reinterpreted, downgraded,
partially accepted or reclassified.

draft-v0.7 was allowed exactly one independent focused review. **It failed it.**

## 2. No finding is converted into a limitation

No BLOCKING or MAJOR finding is recorded as a limitation, a caveat, a known
issue, a deferred item or a future work note. A defect that would change an
estimand, sample, threshold, gate, transition, parser, interface, normative byte,
result interpretation or execution decision is a defect, and draft-v0.7 carries
fifteen of them.

The two MINOR findings are also not converted into anything. They lapse with the
candidate.

## 3. What draft-v0.7 now is

`REJECTED_CANDIDATE_HISTORY_NOT_AN_ACTIVE_PROTOCOL`.

| property | value |
| --- | --- |
| frozen | **false** |
| selected | **false** |
| executable | **false** |
| amendable | **false** |

The v0.7 protocol JSON, Markdown, schema, rendering registry, registry schema,
current pointer, pointer schema, builder, candidate tests and operator-amendment
artifacts are **retained byte-exactly as immutable rejected-candidate history**.
This decision changes zero bytes of them. Their recorded identities are in the
machine-readable form.

They are retained for provenance only. They are not a protocol, not a template,
not a starting point and not a source of inheritable text.

### The old current pointer

`studies/study3/protocol/interface_calibration_protocol_current.json` was an
**internal routing pointer belonging to the rejected candidate**. It is not, and
never becomes, an active project protocol. A prospective reader must not resolve
it. Its `active_bundle`, `loader_contract` and `next_legal_action` fields
describe a candidate that no longer has standing.

The repository therefore has **no active Study 3 interface-calibration protocol**
until a Study 3R protocol is authored and independently reviewed.

## 4. Why repair was refused

The review established that several BLOCKING defects are not v0.7 defects at all
but legacy structure carried forward verbatim: 35 of the 40 top-level keys are
byte-identical to the legacy v0.5 protocol, including `gate_hierarchy`,
`gate_truth_table` and `operation_boundaries`, which is precisely where the
contradictory K6-SEP applicability and the wrong S2/S3 projection live. The
registered state machine is the legacy machine unchanged and integrates no v0.7
gate. Fifteen active fields still assign adjudication to a review round that had
already occurred.

An incremental repair must keep that structure in order to remain incremental.
Repair was therefore refused as a matter of governance, not of effort.

Additionally, the review's coordinated mutation testing showed that seven of
seven decision-bearing changes — including moving `max_new_tokens` from 3 to 6,
raising the shakedown GPU budget from 0 to 40, and redirecting the sole normative
protocol path to the legacy JSON the loader forbids — regenerate cleanly and pass
all 58 committed tests. The validation apparatus cannot be trusted to protect a
repaired candidate, so it is not carried forward either.

## 5. Prohibitions

* draft-v0.7 **may not be repaired**.
* **v0.7.1 may not be automatically drafted.**
* **v0.8 may not be automatically drafted.**
* **No incremental carry-forward repair** of the legacy protocol structure is
  permitted, under any version name.

## 6. Provenance reconciliation

The independent review's committed artifacts report `7 failed, 4,926 passed,
16 skipped` for the reviewed target `459d002…`, while the review's terminal
disclosure reports `7 failed, 4,958 passed, 16 skipped` for the review head
`a08ec146…`. That difference is reconciled additively in
[`v0_7_review_head_test_count_reconciliation.md`](v0_7_review_head_test_count_reconciliation.md)
and its machine-readable form. The reconciliation is a provenance record. It does
**not** revise the methods verdict, and no committed review artifact was edited.

## 7. Boundary

`formal_execution_authorized = false`. `paper/evidence_ledger.csv` is unchanged
and still ends at `EV-0016`. **No scientific evidence was produced by draft-v0.7
or by its review, and the research question remains unanswered.**

Every prohibited operation counter is zero: no Azure/ACR/ACA/GPU/cloud operation,
no tokenizer construction, encode or decode, no checkpoint resolution, download
or load, no model/weight/adapter/activation load, no prefill, forward pass, logit
read, scoring or generation, no model-output parsing, no seed draw, task-bank
realization or split realization, no confirmation access, no interface, RP-B or
RP-M qualification, no patching operation, no evidence-ledger row and no
scientific-evidence claim.

## 8. The authorized continuation

**Study 3R**, a clean-room successor in `studies/study3r/`. It is not v0.8 and not
a copy-on-write continuation. Its charter freezes sixteen project-level decisions
and contains no protocol, no bank realization, no checkpoint download, no
tokenizer output, no selected interface, no numerical gate calculation and no
execution authorization.

Study 3R state: `STUDY3R_CLEAN_ROOM_PROTOCOL_AUTHORIZED_AWAITING_SINGLE_AUTHORING_SESSION`.

Its next legal action is one protocol-authoring session under a separate
authority, followed by one independent focused review. Any BLOCKING finding in
that review terminates Study 3R with no automatic amendment.

`STUDY3_DRAFT_V0_7_REJECTED_TERMINAL_NO_EXECUTION`
