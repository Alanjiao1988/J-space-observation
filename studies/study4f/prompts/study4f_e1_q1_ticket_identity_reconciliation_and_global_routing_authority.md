Act as the operator-authorized successor for Study 4F-E1-Q1.

The purpose of this invocation is to reconcile the registered Azure Support ticket identity, preserve all historical Q1 bytes, and then resume the previously authorized read-only Global Azure resource-routing survey.

This is an operational metadata correction only. It must not amend the scientific protocol, activate A100 fallback, create Azure resources, submit quota requests, or execute model cells.

## 0. Known contradiction and operator decision

The previously disclosed complete customer-facing support ticket identifier ends in:

`1753`

The published Q1 redacted record instead states:

`3753`

Treat this as an unresolved historical identity contradiction until mechanically verified. Do not silently choose either value solely from prose.

Azure Support resources expose two distinct identities:

1. ARM resource `name`, used in the `Microsoft.Support/supportTickets/{supportTicketName}` resource path;
2. `properties.supportTicketId`, the system-generated customer-facing support ticket identifier.

These identities must be recorded and validated separately. The ARM resource name must never be treated as interchangeable with `properties.supportTicketId`.

The operator authorizes creation of one additive Q1R successor authority and reconciliation record. Historical Q1 authorities, receipts, disclosures and status evidence must remain byte-identical.

## 1. Repository preflight

1. Fetch `origin/main`.

2. Expect `HEAD == origin/main == 01c07d8…` and tree `cca35c2…`.

3. Require a clean worktree and linear ancestry.

4. Verify the existing state:

   `STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION`

5. Verify all published Q1 authority, receipt and disclosure hashes before writing.

6. Confirm that the registered target remains:

   * Global Azure;
   * Australia East;
   * `Standard_NC40ads_H100_v5`;
   * `StandardNCadsH100v5Family`;
   * requested limit 40 vCPUs;
   * one on-demand instance.

7. If any starting identity differs, stop without writing.

## 2. Publish the reconciliation authority first

Create one narrowly scoped successor authority, for example:

`studies/study4f/prompts/study4f_e1_q1_ticket_identity_reconciliation_and_global_routing_authority.md`

It must be committed alone as the first commit after the verified starting head and published before any new Azure operation.

The authority must explicitly authorize only:

* secure ticket-identity reconciliation;
* one Support ticket GET;
* one current Australia East H100 quota query;
* the previously requested read-only Global Azure H100/A100 regional survey;
* additive reconciliation artifacts and tests;
* no Azure writes and no scientific execution.

Do not replace, amend or recommit the original Q1 authority.

## 3. Secure identity reconciliation

Obtain the complete operator-owned customer-facing ticket identifier through a non-logged secure input or environment variable.

Do not:

* place it literally in a shell command;
* print it;
* commit it;
* expose it in test output, exceptions or logs.

Issue exactly one GET for the existing Support ticket. Do not retry or poll.

From the response, separately extract:

* ARM resource `name`;
* `properties.supportTicketId`;
* `properties.createdDate`;
* `properties.status`;
* title/service/problem classification;
* quota ticket details sufficient to verify region, family and requested limit.

Validate `properties.supportTicketId`, not ARM `name`, against the secure operator-owned full identifier.

Require the complete identity tuple to agree:

* customer-facing ticket ID;
* expected suffix `1753`;
* previously registered creation time `2026-08-18T06:25:01Z`, allowing only documented API timestamp normalization;
* Australia East;
* H100 NCadsH100v5 family;
* requested limit 40 vCPUs;
* quota-request problem classification;
* same subscription identity using the existing redacted subscription binding.

Do not rely on suffix alone.

### Successful reconciliation

If the complete tuple agrees, classify:

`Q1_REGISTERED_REDACTED_TICKET_IDENTITY_TRANSCRIPTION_ERROR_CONFIRMED`

Record additively that:

* historical `3753` is preserved as an incorrect registered redaction;
* corrected customer-facing suffix is `1753`;
* `properties.supportTicketId` is the governing ticket-identity field;
* ARM resource `name` is a separate API resource identity;
* neither full value is committed;
* both full identities are stored only as separately labelled salted hashes, using the project’s existing secret-handling rules.

Do not describe this as a different ticket, Azure-side ticket change, duplicate ticket or support failure.

### Failed reconciliation

If any material tuple field disagrees, stop with:

`STUDY4F_E1_Q1_TICKET_IDENTITY_UNRESOLVED_OPERATOR_ACTION_REQUIRED`

Report only which categories disagreed. Do not disclose either full identifier, query quota, perform the regional survey, or alter current lifecycle state.

## 4. Current Q1 observation after successful reconciliation

Only after successful reconciliation:

1. Reuse the status from the same Support GET; do not issue a second ticket GET.
2. Query Australia East H100-family usage/quota exactly once.
3. Classify the support correspondence as:

   `BACKLOG_PENDING_NO_APPROVAL_NO_FINAL_DENIAL`

unless the live API status provides authoritative contradictory evidence.

Apply these rules:

* visible H100-family quota `>= 40` is the only quota-approval gate;
* backlog/pending is not approval;
* backlog/pending is not final denial;
* A100 fallback remains inactive;
* quota below 40 plus pending ticket preserves:

  `STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION`

If quota is at least 40, do not provision in this invocation. Report that the existing E1 execution authority may now be resumed.

## 5. Resume the bounded Global Azure survey

If quota remains below 40 and the ticket remains pending, continue with the previously requested read-only survey.

For the registered H100 route and registered A100 fallback only:

1. enumerate subscription-visible Global Azure regions;
2. inspect SKU availability and `NotAvailableForSubscription` restrictions;
3. query relevant VM-family and Total Regional vCPU usage/limits;
4. classify each region/SKU pair as:

   * `R0_QUOTA_ALREADY_SUFFICIENT`;
   * `R1_SKU_ALLOWED_QUOTA_INSUFFICIENT`;
   * `R2_SUBSCRIPTION_RESTRICTED`;
   * `R3_NOT_OFFERED_OR_UNRESOLVABLE`;
5. label physical capacity for every entry:

   `UNKNOWN_NOT_TESTED`

Do not submit any request or attempt deployment.

Rank H100 and A100 separately using:

1. classification order R0, R1, R2, R3;
2. smallest family-quota deficit;
3. smallest regional-quota deficit;
4. region name lexicographically.

If an R0 route exists, stop for operator authorization. If none exists, recommend no more than one candidate for a future operator-authorized quota request.

The survey does not itself activate A100 fallback.

## 6. Publication and preservation

After successful reconciliation:

* add a machine-readable reconciliation receipt with a restrictive schema;
* add tests proving field separation, suffix correction, complete-tuple matching, secret redaction and historical-byte preservation;
* retain every original Q1 artifact byte-identically;
* use copy-on-write routing if existing status/routing artifacts are protected;
* never weaken or edit a historical scope assertion merely to make the new successor pass;
* disclose any unavoidable scope expiry rather than suppressing it.

Publication order:

1. reconciliation authority alone;
2. reconciliation receipt/schema/tests and any additive routing;
3. final disclosure.

Refetch `origin/main` before each publication and require fast-forward-only publication.

## 7. Required final disclosure

Return:

1. starting and final commit/tree;
2. authority identity and alone-first ordering;
3. whether the mismatch was:

   * suffix transcription;
   * wrong API field comparison;
   * both;
   * or unresolved;
4. confirmation that the governing field is `properties.supportTicketId`;
5. only the corrected suffix and salted hashes—never full identities;
6. verified ticket tuple and support lifecycle;
7. current H100 quota observation;
8. regional survey table and rankings, if reached;
9. all Git and Azure write counters;
10. model, bank, scoring, generation, D0, activation and patching counters;
11. exact final registered state;
12. next legal operator action.

No scientific conclusion may be drawn. Nothing in this task establishes anything about J-space.
