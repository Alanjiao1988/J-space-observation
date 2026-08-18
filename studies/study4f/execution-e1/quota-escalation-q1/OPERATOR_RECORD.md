# Study 4F-E1-Q1 operator record

Authority: `studies/study4f/prompts/study4f_e1_q1_manual_quota_escalation_and_conditional_resume_authority.md`
Q1 authority commit: `8a9bb7617fcc6507aba86c4359042b5e90818ce4`

Current lifecycle state:

```
STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION
```

**Read `STATUS.json` first.** This file is the human-facing companion to it.

## 1. What happened in this invocation

| Step | Outcome |
| --- | --- |
| Starting state (§0) | verified at `1900aa374bf000353580b042b275a730bbad6b1f` |
| Q1 authority (§1) | did not exist; published alone as `8a9bb76…` |
| Read-only quota re-check (§2) | H100 family limit still `0` in `australiaeast` |
| Existing support ticket (§2.2) | none found; branch `2.3` taken |
| Support ticket (§3) | **one** created via the Support REST API |
| Outcome branch (§4) | `4.1` — programmatic creation succeeded |

A ticket now exists and is `Open`. This is *not* a decision, and nothing here
claims Azure has approved, denied or is otherwise disposed toward the request
beyond that recorded status.

## 2. The ticket, redacted

| Field | Value |
| --- | --- |
| Ticket ID (salted SHA-256) | `3115437c07487a4b825eaa7b5017b570db8e38da9cd88824cc88cf8147f84021` |
| Ticket ID final four | `3753` |
| Resource name | `study4f-e1-q1-h100-australiaeast` |
| Created | `2026-08-18T06:25:01Z` |
| Status | `Open` |
| Azure acknowledgement | receipt acknowledged; stated review window of **two business days** |
| Azure decision | **none yet** — an acknowledgement is not an approval |
| Severity | `Minimal` |
| Support SLA | 480 minutes, expiring `2026-08-19T05:26:00Z` |
| Issue type | Service and subscription limits (quotas) |
| Quota type | Compute-VM (cores-vCPUs) subscription limit increases |
| Subscription | ends `d32e` (full ID deliberately not committed) |
| Region | `australiaeast` |
| VM family | Standard NCadsH100v5 Family vCPUs |
| Requested new limit | `40` |
| Requested instances | exactly `1` |
| Target SKU | `Standard_NC40ads_H100_v5` |
| Capacity type | standard on-demand, **not** Spot |

The salt material is `STUDY4F_E1_Q1|<q1 authority commit>|<support ticket id>`,
so the hash is reproducible by anyone who legitimately holds the ticket ID and
cannot be reversed by anyone who does not.

## 3. What was deliberately *not* done

* **No second `Microsoft.Quota/quotas` PUT.** The self-service path was already
  exhausted under the E1 authority and §3 forbids retrying it.
* **No duplicate support ticket.** The subscription was queried for existing
  tickets first; there were none, and exactly one was created.
* **No enlarged request.** Not more than 40 H100-family vCPUs, not multiple
  instances, not Spot quota, not multiple regions at once.
* **No A100 fallback.** §4.3 authorizes it only after Azure explicitly
  determines that H100 cannot be enabled in any eligible region, and the
  fallback may never coexist with an unresolved H100 request. The H100 request
  is unresolved.
* **No provisioning.** Zero resource groups, zero VMs, zero deployment attempts.
* **No polling loop.** The session did not stay open waiting for a decision.

## 4. What the human operator may need to do

Microsoft Support has acknowledged receipt and stated it will respond within
**two business days**. That is an acknowledgement, not a decision: it grants no
quota, and the family limit still reads `0`.

Nothing is required right now. Azure owns the next move.

One thing that does matter: if you reply to the support thread, **do not alter
the subject line and use reply-all**, or the response will not be tracked
against the case.

If Azure contacts you for confirmation, the answer to the usual follow-ups is:

* **"Can you use a smaller GPU?"** No. The registered runtime requirement is
  69,502,926,848 bytes of free device memory for one unquantized BF16
  checkpoint. T4, A10 and V100 cannot hold it, and quantization, CPU/disk
  offload and multi-GPU sharding are prohibited by the study's own authority —
  taking any of them would make it a different study.
* **"Will Spot work?"** No. The registered capacity type is standard on-demand.
* **"How long will it run?"** Bounded and short. The VM is deallocated and the
  dedicated resource group deleted immediately after the run and artifact
  recovery.
* **"Why 40 vCPUs?"** That is exactly one `Standard_NC40ads_H100_v5`. It is the
  minimum, not a buffer.

If Azure declines H100 in `australiaeast` but offers another region, **stop and
decide as an operator** — do not let the region be chosen after any scientific
output exists. No scientific output exists yet, which is precisely why this is
the safe moment to make that choice.

If Azure determines H100 cannot be enabled in any eligible region, that
determination authorizes exactly one separately recorded fallback request:
`Standard_NC24ads_A100_v4`, Standard NCADSA100v4 Family vCPUs, `brazilsouth`,
new limit `24`, one instance.

## 5. When quota is actually granted

Quota counts as approved **only when it is visible**, not when a message says so:

* `az vm list-usage --location <approved region>` reports an H100 family limit
  of at least `40`; or
* after a registered H100 denial and A100 fallback approval, an A100 family
  limit of at least `24` in its approved region.

An approval e-mail without visible quota is not sufficient.

Once it is visible, re-invoking this authority resumes §6: bind a quota-approval
receipt, re-fetch `origin/main`, re-run the E1 instrument binding and read-only
discovery, preserve the H100-before-A100 order, then enter §4.2 of the published
E1 authority with at most four on-demand attempts and no Spot. The existing E1
launcher and the original Study 4F state machine are reused unchanged.

## 6. Re-invoking this authority safely

This authority is deliberately resumable and idempotent. A later invocation
will fetch `origin/main`, verify the published Q1 authority and predecessor
bytes, read quota and ticket state **once**, create no duplicate ticket, and
commit nothing if nothing changed.

Do not schedule polling and do not repeatedly call the quota API.

## 7. Claim ceiling

No scientific result. Azure GPU capacity remains unknown. No checkpoint
competence was tested. No RP-B candidate was identified. Nothing was established
about J-space. The evidence ledger is unchanged at `EV-0016`.
