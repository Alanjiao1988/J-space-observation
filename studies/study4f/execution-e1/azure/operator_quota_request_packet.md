# Study 4F-E1 operator-facing GPU quota request packet

Authority: `studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md`
(section 4.1)
E1 authority commit: `58cdcda0ec3848ba2bd3a6c525b3c28ac8955d69`

This packet exists because the authenticated Azure quota API accepted exactly one
bounded, noninteractive request and then **refused it**. The registered successor
stops at `STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL` and does not retry, does
not enlarge the request and does not provision anything.

## 1. What was already attempted, once

| Field | Value |
| --- | --- |
| API | `Microsoft.Quota/quotas` `PUT`, api-version `2023-02-01` |
| SKU | `Standard_NC40ads_H100_v5` |
| Quota name | `standardNCadsH100v5Family` |
| Region | `australiaeast` |
| Requested limit | `40` family vCPUs |
| Instances requested | exactly `1` |
| Request ID | `a6817961-e0f7-4cbe-a1ef-7ac4104e1089` |
| Submitted | `2026-08-18T03:40:05Z` |
| Provisioning state | `Failed` |
| Error code | `QuotaNotAvailableForResource` |
| Quota granted | none; the family limit is still `0` |

The request was **not** enlarged and was **not** resubmitted. Section 4.1 permits
one minimal request for exactly one instance of the first eligible SKU/region,
and forbids requesting a larger quota.

## 2. Why this SKU and this region

The registered accelerator order is fixed by section 3 and is not a preference:

1. `Standard_NC40ads_H100_v5` — exactly one H100 NVL GPU, nominal 94 GB, 40 vCPUs;
2. `Standard_NC24ads_A100_v4` — exactly one A100 GPU, nominal 80 GB, 24 vCPUs.

H100 must be attempted before A100. Within a SKU, otherwise eligible regions are
ordered lexicographically **before any deployment result is observed**, so the
choice cannot be influenced by what Azure happens to answer first.
`australiaeast` is the lexicographic head of the H100 set.

T4, A10, V100, multi-GPU ND-series, Spot VMs and confidential-GPU substitutions
are not eligible and may not be offered as an alternative.

## 3. The exact request an operator should file

Submit a **quota increase support request** (the self-service path is what
already failed):

* Subscription: the one whose ID ends `d32e`
  (salted SHA-256 `9adb2550056c6e57f03aca51c3a82a4fed3808d9c17b9b0357f15260adc0bb59`
  over `STUDY4F_E1|<e1 authority commit>|<subscription id>`).
  The full subscription ID is deliberately not committed.
* Issue type: **Service and subscription limits (quotas)**
* Quota type: **Compute-VM (cores-vCPUs) subscription limit increases**
* Region: `australiaeast`
* SKU family: **Standard NCadsH100v5 Family vCPUs**
* New limit: **40**

If, and only if, the H100 family cannot be granted in any region, the registered
fallback is the second SKU, requested the same way:

* SKU family: **Standard NCADSA100v4 Family vCPUs**
* New limit: **24**
* Region: the lexicographic head of the A100 set for which the request is viable,
  which is `brazilsouth` at this discovery head.

Nothing larger than one instance may be requested for either SKU.

## 4. What must not be done to work around this

The following are prohibited by the authority and would silently turn this into a
different study:

* quantization, sharding, CPU offload, disk offload or `device_map="auto"`;
* substituting T4, A10, V100, a multi-GPU ND-series VM, a Spot VM or a
  confidential-GPU VM;
* raising the request above one instance;
* provisioning anything before quota exists.

## 5. What to do once quota is granted

1. Re-fetch `origin/main` and confirm it still matches the published E1 head.
2. Re-run the registered read-only discovery; the eligible set is recomputed, not
   remembered.
3. Enter section 4.2: at most four on-demand deployment attempts across the
   registered SKU/region order, no Spot.
4. Freeze the first successfully provisioned SKU/region/zone before any model
   output is observed.
5. Continue with sections 5 to 9 unchanged.

Quota approval authorizes **provisioning only**. It does not authorize
confirmation, D0, activation capture, patching or Study 3M, and it establishes
nothing about J-space.
