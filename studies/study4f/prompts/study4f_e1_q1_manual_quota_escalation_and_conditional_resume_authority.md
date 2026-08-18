You are the project-level operator responsible for one manual-quota-escalation and conditional-resumption authority for Study 4F-E1.

Repository:

`https://github.com/Alanjiao1988/J-space-observation`

This is not a new study, protocol revision, methods review or scientific amendment. It performs exactly one Azure Support escalation and, only after quota is actually visible, resumes the already published Study 4F-E1 execution path unchanged.

# 0. Binding starting state

Fetch `origin/main` and require:

* commit:
  `1900aa374bf000353580b042b275a730bbad6b1f`
* clean worktree;
* strictly linear history;
* no concurrent writer;
* E1 lifecycle state:
  `STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL`;
* failed self-service request:
  `a6817961-e0f7-4cbe-a1ef-7ac4104e1089`;
* error:
  `QuotaNotAvailableForResource`;
* H100 family limit remains zero;
* no Azure resource, deployment, accelerator, bank, seal, weight, model call or executed cell;
* evidence ledger remains at `EV-0016`;
* repository baseline remains:
  `9 failed, 5,119 passed, 16 skipped`
  with the same nine failure node IDs.

Verify these authoritative predecessor artifacts:

* `studies/study4f/execution-e1/STATUS.json`
* `studies/study4f/execution-e1/azure/operator_quota_request_packet.md`
* `studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md`

If any identity or boundary differs, stop:

`STUDY4F_E1_Q1_BLOCKED_ON_STARTING_STATE_INTEGRITY`

# 1. Resumable authority ordering

Authority path:

`studies/study4f/prompts/study4f_e1_q1_manual_quota_escalation_and_conditional_resume_authority.md`

If this authority does not yet exist:

1. save this prompt byte-for-byte;
2. commit it alone as the first commit after `1900aa3…`;
3. record bytes, SHA-256, Git blob, parent and tree;
4. publish before creating a support ticket or any Q1 artifact.

If an exact previously published copy already exists:

* verify its bytes, hash, alone-first ordering and ancestry;
* do not recommit or replace it;
* resume from the first incomplete Q1 step.

All new artifacts must be additive under:

`studies/study4f/execution-e1/quota-escalation-q1/`

Do not modify any existing Study 4F, Study 4F-E1, Study 3R, historical-study or paper byte.

# 2. First perform a current read-only quota check

Using the already configured Azure identity, re-query:

* `StandardNCadsH100v5Family` quota in `australiaeast`;
* total regional vCPU quota;
* the failed self-service request;
* any existing Azure Support ticket associated with that request or workload.

Never print or commit:

* full subscription or tenant IDs;
* access tokens;
* credentials;
* full policy identifiers containing subscription IDs.

Use the existing salted subscription identity and last four characters `d32e`.

Branches:

## 2.1 Quota already granted

If the H100 family limit is at least 40, do not create a support ticket. Continue directly to §6.

## 2.2 An operator Support ticket already exists

If a matching non-closed Support ticket exists:

* do not create another;
* record only a salted ticket hash, final four characters, creation time and current state;
* if still pending, stop without another commit unless the state changed:

`STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION`

* if approved and quota is visibly at least 40, continue to §6;
* an approval message without visible quota is not sufficient.

## 2.3 No operator Support ticket exists

Continue to §3.

# 3. Authorize exactly one Azure Support ticket

Do not submit another `Microsoft.Quota/quotas PUT`. The self-service quota path is exhausted.

Create at most one Azure Support request, through the Azure Support REST API if the authenticated identity has the required permission.

Use exactly:

* issue type:
  `Service and subscription limits (quotas)`
* quota type:
  `Compute-VM (cores-vCPUs) subscription limit increases`
* subscription:
  the authenticated subscription ending `d32e`
* region:
  `australiaeast`
* VM family:
  `Standard NCadsH100v5 Family vCPUs`
* requested new limit:
  `40`
* requested instances:
  exactly one
* target SKU:
  `Standard_NC40ads_H100_v5`
* capacity type:
  standard on-demand, not Spot.

Ticket title:

`Manual enablement request: one NC40ads_H100_v5 GPU VM for bounded non-production research`

Ticket description:

> We request a VM-family quota limit of 40 vCPUs for Standard NCadsH100v5 Family in Australia East, sufficient for exactly one Standard_NC40ads_H100_v5 VM.
>
> This is a bounded, non-production scientific batch-inference workload. It requires one unquantized BF16 checkpoint whose registered runtime memory requirement is 69,502,926,848 bytes, so smaller T4/A10/V100 resources, quantization, offload and multi-GPU sharding are not valid substitutes.
>
> The VM will be on-demand rather than Spot, used temporarily, and deallocated and deleted immediately after the bounded run and artifact recovery.
>
> The subscription currently has Total Regional vCPU quota 100 with zero usage, but Standard NCadsH100v5 Family quota is zero.
>
> A self-service Microsoft.Quota request for the minimal 40-vCPU limit was attempted once and failed:
>
> Request ID: a6817961-e0f7-4cbe-a1ef-7ac4104e1089
> Error: QuotaNotAvailableForResource
>
> Please manually enable the requested 40-vCPU family quota. If the H100 family cannot be enabled for this subscription in Australia East, please state whether it can be enabled in another region returned as eligible for this subscription. If H100 cannot be granted in any eligible region, please provide that determination so the project can use its separately registered A100 fallback request.

Do not request:

* more than 40 H100-family vCPUs;
* multiple instances;
* Spot quota;
* another GPU family in the same ticket as if already authorized;
* quota in multiple regions simultaneously.

# 4. Support-ticket creation outcomes

## 4.1 Support API succeeds

Record only:

* salted hash of ticket ID;
* final four characters;
* creation timestamp;
* ticket status;
* exact requested quota fields.

Do not publish full subscription, tenant or sensitive support-contact details.

Publish:

* a machine-readable ticket receipt and restrictive schema;
* a concise lifecycle status;
* no scientific or Azure-capacity claim.

Stop:

`STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION`

Do not poll continuously and do not hold a session open indefinitely.

## 4.2 Programmatic creation is unauthorized or unsupported

Do not try to bypass RBAC or reuse credentials outside their configured purpose.

Publish a status that distinguishes “ticket not filed” from “ticket pending”:

`STUDY4F_E1_Q1_MANUAL_PORTAL_SUBMISSION_REQUIRED`

The operator-facing record must instruct the human operator to use:

Azure Portal → Quotas → Compute → Australia East → Standard NCadsH100v5 Family vCPUs → support icon/Create a support request.

Use the exact fields and ticket description in §3.

Do not claim that Azure is reviewing the request until a real support case exists.

## 4.3 Immediate rejection

Record the exact support response without converting it into a capacity result.

If H100 is rejected only for Australia East but offered in another eligible region, stop for an operator decision rather than choosing a region after observing scientific results; no scientific output yet exists.

If Azure explicitly determines that H100 cannot be enabled in any eligible region for this subscription, authorize one separately recorded fallback support request only after that determination:

* SKU:
  `Standard_NC24ads_A100_v4`
* family:
  `Standard NCADSA100v4 Family vCPUs`
* region:
  `brazilsouth`
* new limit:
  `24`
* instances:
  one.

The fallback support request must never coexist with an unresolved H100 request.

# 5. Safe repeated invocation

This authority is deliberately resumable.

On every later invocation:

1. fetch `origin/main`;
2. verify the published Q1 authority and all predecessor bytes;
3. read quota and support-ticket state once;
4. create no duplicate ticket;
5. make no repository commit if nothing changed;
6. return the exact current lifecycle state.

Do not schedule polling and do not repeatedly call the quota API.

Quota is considered approved only when `az vm list-usage` or the corresponding ARM API visibly reports:

* H100 family limit `>= 40` in the approved region; or
* after a registered H100 denial and A100 fallback approval, A100 family limit `>= 24` in its approved region.

# 6. Conditional resumption after visible quota

Once qualifying quota is actually visible:

1. create a quota-approval receipt binding the observed family, limit, region and timestamp;
2. re-fetch `origin/main`;
3. re-run the E1 instrument binding;
4. re-run read-only SKU, policy, quota and capacity discovery;
5. preserve the registered H100-before-A100 order;
6. enter §4.2 of the published E1 authority;
7. use at most four on-demand deployment attempts;
8. use no Spot resource;
9. freeze the first successfully provisioned eligible SKU/region/zone before any model output;
10. continue §§5–14 of the published E1 authority unchanged.

The existing E1 launcher and original Study 4F state machine must be reused. Do not reimplement or amend them.

The remaining shakedown allowance remains:

* two attempts;
* six accelerator-hours.

The execution must continue to prohibit:

* quantization;
* sharding;
* CPU/disk offload;
* `device_map="auto"`;
* model/checkpoint substitution;
* threshold, parser, interface or bank changes;
* D0, activation capture or patching.

# 7. Repository and testing discipline

Use strictly linear fast-forward publication.

Re-fetch `origin/main` before every push.

No merge, rebase, squash, force-push, history rewrite or GitHub Actions run.

Reproduce the starting nine failure node IDs. Require:

* zero new non-scope failures;
* no historical failure edited or suppressed;
* all Q1 tests passing;
* all Study 4F and E1 tests passing;
* evidence ledger unchanged at `EV-0016`.

Do not modify an old HEAD-relative scope test. If a new expiry occurs, it must be mechanically proved scope-only and carried forward by a new invariant.

# 8. Azure cleanup after any eventual execution

If quota approval leads to provisioning and model execution, follow the existing E1 cleanup authority exactly:

* retrieve and hash-verify all artifacts first;
* deallocate immediately;
* delete only the explicitly enumerated dedicated E1 resource group;
* verify no VM, disk, NIC, public IP or billable accelerator remains.

If artifact recovery fails, deallocate but retain the dedicated group and report it.

# 9. Final disclosure

For the current invocation, report:

* starting/final commit and tree;
* whether Q1 authority was newly published or reused;
* whether quota is still zero or approved;
* whether a Support ticket existed, was created or still requires manual submission;
* redacted ticket identity and exact state;
* zero/actual Azure resource counters;
* whether E1 execution became reachable;
* test differential;
* evidence-ledger state;
* exact lifecycle state;
* explicit claim ceiling.

Until a model cell executes, continue to state:

* no scientific result;
* Azure GPU capacity remains unknown;
* no checkpoint competence was tested;
* no RP-B candidate was identified;
* nothing was established about J-space.
