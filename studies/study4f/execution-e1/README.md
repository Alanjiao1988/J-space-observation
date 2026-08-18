# Study 4F-E1 — Qualifying Accelerator Execution

**Read `STATUS.json` first.** It is the authoritative lifecycle router for this
execution successor, and for this successor only. It does not route Study 4F,
Study 3R or any other study.

Current lifecycle state:

```
STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL
```

## What this is

Study 4F published a complete, mechanically validated behavioral-feasibility
instrument and then stopped at `STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`,
because the host it ran on had no accelerator that could hold the 32B checkpoint
unquantized.

Study 4F-E1 is the **resource-only** successor to that instrument. Its entire job
is to supply a qualifying Azure accelerator and then execute the existing
instrument *unchanged*. It amends, repairs, redesigns and reinterprets nothing:

* every decision-bearing Study 4F file is bound byte-exactly at
  `5fd9602df207e95789263d0f8d52428540f48fb8`;
* the ladder is executed by `studies/study4f/analysis/study4f_state_machine.py`
  itself, not by a copy;
* the D2 and D3 banks would be realized from the **original** Study 4F authority
  hash, never from the E1 authority hash;
* `studies/study4f/STATUS.json`, the Study 4F protocol, parsers, generator,
  statistics and tests, every Study 3R byte and `paper/evidence_ledger.csv` are
  all untouched.

## Where it stopped, and why

Read-only Azure discovery found both registered accelerator SKUs offered
broadly, with **no** `NotAvailableForSubscription` restriction and no Azure
Policy assignment denying a compute SKU or a region. The blocking dimension is
VM-family vCPU quota, which is `0` in every region returned for either SKU.

Exactly one minimal quota request was submitted — 40 family vCPUs for one
`Standard_NC40ads_H100_v5` in `australiaeast`, the lexicographic head of the
registered order — and the quota service refused it with
`QuotaNotAvailableForResource`. No larger request was made and no second request
was made.

Because section 4.1 forbids provisioning without quota, **capacity was never
observed**. This successor therefore reports capacity as *unknown*, not as
unavailable.

Nothing was provisioned: zero Azure resources created, zero deployment attempts,
zero checkpoint downloads, zero model calls, zero cells executed.

## Layout

| Path | What it is |
| --- | --- |
| `STATUS.json` | the lifecycle router; read it first |
| `STATUS.schema.json` | restrictive schema that pins every flag and counter |
| `azure/azure_discovery.json` | read-only SKU/region/zone/quota evidence |
| `azure/quota_disposition.json` | quota versus capacity, and the single request |
| `azure/operator_quota_request_packet.md` | the exact escalation an operator should file |
| `manifest/predecessor_instrument_manifest.json` | byte-exact binding of 15 decision-bearing files |
| `manifest/predecessor_semantic_invariants.json` | 13 reconfirmed semantic invariants |
| `analysis/study4f_e1_instrument_binding.py` | the binding, and its refutation |
| `analysis/study4f_e1_resource_selection.py` | registered SKU order, eligibility, quota vs capacity |
| `analysis/study4f_e1_runtime_preflight.py` | the measured-device gate |
| `analysis/study4f_e1_deployment_plan.py` | dedicated group, tags, explicit cleanup targets |
| `analysis/study4f_e1_lifecycle.py` | terminal states, shakedown budget, post-call freeze |
| `tests/` | the E1 resource and execution tests |
| `STUDY4F_E1_TERMINAL_DISCLOSURE.md` | the full section 14 disclosure |

## Running the tests

The repository's default `pytest` run collects `tests/` only. Run this
successor's tests explicitly, alongside the predecessor's:

```
python -m pytest studies/study4f/tests studies/study4f/execution-e1/tests
```

## What this successor does not establish

It establishes nothing about whether J-space exists, is observable or is
unobservable. It establishes nothing about the capability of any checkpoint,
because no cell was executed. It establishes nothing about Azure GPU capacity,
because capacity was never observed. It is not a scientific result and it adds
no evidence-ledger row; the ledger still ends at `EV-0016`.
