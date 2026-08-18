# Study 4F-E1 terminal disclosure

Authority: `studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md`
E1 authority commit: `58cdcda0ec3848ba2bd3a6c525b3c28ac8955d69`
Predecessor: Study 4F at `5fd9602df207e95789263d0f8d52428540f48fb8`

Exact final registered state:

```
STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL
```

**No scientific result.** No cell was executed, no model was called, no Azure
resource was created and no accelerator was ever observed.

---

## 1. Starting and final identity

| Item | Value |
| --- | --- |
| Starting commit | `5fd9602df207e95789263d0f8d52428540f48fb8` |
| Starting tree | `365a5d090e1474305143a7e5aa268db969e62069` |
| Starting Study 4F lifecycle state | `STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE` |
| Starting evidence ledger | ends at `EV-0016` |
| E1 authority commit | `58cdcda0ec3848ba2bd3a6c525b3c28ac8955d69` |
| E1 authority tree | `a587a0de590645ccdd008828bda33ec531274767` |
| Ancestry | strictly linear, merge-free, fast-forward only |

The starting state was verified before anything was written: `origin/main` at the
registered commit, a clean worktree, zero merge commits in the entire history,
the Study 4F terminal `STATUS.json` unchanged, the Study 3R tree byte-identical
to its closure head `ee8a852111d27cb39bf21743e18857485cff1efe`, the evidence
ledger ending at `EV-0016`, zero previously executed Study 4F cells and zero bank
realizations, weights, model calls, logit reads, activations and patches.

The registered repository baseline was reproduced at the starting commit:

```
9 failed, 5,119 passed, 16 skipped
```

with exactly the nine registered failure node IDs, including the one disclosed
immutable scope expiry
`tests/test_study3r_protocol_v1.py::test_the_authoring_session_wrote_nothing_outside_the_study3r_namespace`.

## 2. Authority identity and alone-first ordering

| Item | Value |
| --- | --- |
| Path | `studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md` |
| Byte length | 15,373 |
| SHA-256 | `4e8b036e1247d5e671fdfc8d66febb7ff0bf20f37e674fc3c46a9a596f5ac6ab` |
| Git blob | `a12dae7772e3dd4d2de32ddd278b99f37078a3ed` |
| Parent commit | `5fd9602df207e95789263d0f8d52428540f48fb8` |
| Parent tree | `365a5d090e1474305143a7e5aa268db969e62069` |
| Authority commit | `58cdcda0ec3848ba2bd3a6c525b3c28ac8955d69` |
| Authority tree | `a587a0de590645ccdd008828bda33ec531274767` |

The authority was saved byte-for-byte and committed **alone** as the first commit
after the predecessor. `git show --name-only` for that commit lists exactly one
path. No Azure resource, execution artifact, bank, seal, launcher or report
existed at or before it: `git ls-tree -r 58cdcda studies/study4f/execution-e1`
is empty.

## 3. Predecessor instrument hash verification

All fifteen decision-bearing Study 4F files were bound byte-exactly at
`5fd9602…`. Every hash was recomputed from the worktree and required to agree
with the committed blob. **Zero files differed.**

| Role | Path | Bytes | SHA-256 |
| --- | --- | --- | --- |
| protocol | `protocol/study4f_protocol_v1.json` | 11,749 | `0bd1fff1…5d13a240` |
| protocol schema | `protocol/study4f_protocol_v1.schema.json` | 23,523 | `a8d242a5…40e6e941` |
| task-bank generator and ordering | `analysis/study4f_task_banks.py` | 14,757 | `dc39782d…2fdbff766`* |
| E0 and CoT renderers/parsers | `analysis/study4f_interfaces.py` | 11,391 | `7828bca3…ce9a2f705`* |
| statistical calculator | `analysis/study4f_design_statistics.py` | 5,614 | `10ce33b0…89c30b0`* |
| candidate-local state machine | `analysis/study4f_state_machine.py` | 5,988 | `78e15c37…b7344e137` |
| semantic/mutation validators | `analysis/study4f_validation.py` | 15,445 | `2534b6d5…a5baff94` |
| checkpoint identities and resource route | `analysis/study4f_resource_route.py` | 6,002 | `7c1f701f…e21a432897`* |
| original shakedown disposition | `shakedown/study4f_shakedown_disposition.json` | 3,036 | `81efd8f6…56c3aaca` |
| original authority | `prompts/study4f_minimal_behavioral_feasibility_authority.md` | 17,822 | `bafba585…68de0773` |
| original STATUS router | `STATUS.json` | 11,747 | `4229cb69…bd1ed3d0` |
| original STATUS schema | `STATUS.schema.json` | 14,860 | `3f5e73d7…927647fb` |
| Study 4F tests | `tests/test_study4f_behavioral_feasibility.py` | 54,691 | `1389a2ba…d558b6ca` |
| original terminal disclosure | `STUDY4F_TERMINAL_DISCLOSURE.md` | 15,446 | `7fa015e5…6323e4f0` |
| original README | `README.md` | 5,465 | `7d62915e…f24eee7bb`* |

\* abbreviated for readability; the exact 64-hex digests are in
`manifest/predecessor_instrument_manifest.json`, which is the authoritative
record. The `original authority` digest `bafba585…` matches the value Study 4F
itself recorded, so the binding is anchored to the predecessor's own claim.

Thirteen semantic invariants were reconfirmed **without modifying anything**, and
all thirteen hold: D2 and D3 are separate and cannot be pooled; each planned bank
has 104 items; `m_max = 16`; `alpha_per_cell = 1/320`; the CoT gate is `n = 104`
with pass `≥ 90`; the E0 gate is `n = 60` with pass `≥ 41`; the candidate order is
7B → 14B → 32B; candidate failures are local; RT is unreachable until a
developmental positive-reference candidate qualifies; quantization, sharding,
offload and model substitution are prohibited; the only candidate disposition is
developmental; the W1 raw-direct surface still reproduces the verified source
hash `9dab5a86…0934a4c95`; and bank seeds derive from the **original** Study 4F
authority commit `7d5ff0837d77af9e6df9f49d580ec0e42bdc2729`, not from the E1
authority commit.

## 4. Azure identity and non-sensitive provenance

The already configured Azure CLI identity was used. No credential was requested,
printed or committed.

| Item | Value |
| --- | --- |
| Subscription salted SHA-256 | `9adb2550056c6e57f03aca51c3a82a4fed3808d9c17b9b0357f15260adc0bb59` |
| Salt material | `STUDY4F_E1|<e1 authority commit>|<subscription id>` |
| Subscription final four | `d32e` |
| Full subscription ID committed | no |
| Tenant ID committed | no |
| Cloud / state | `AzureCloud` / `Enabled` |

Azure Policy: every assignment in scope is a Microsoft Defender / ASC
provisioning or data-protection assignment. None carries a deny effect on a
compute SKU or on a location, so Azure Policy removed no region from
consideration.

## 5. SKU, region and zone selection evidence

Registered selection order, unchanged:

1. `Standard_NC40ads_H100_v5` — exactly one H100 NVL GPU, nominal 94 GB, 40 vCPUs;
2. `Standard_NC24ads_A100_v4` — exactly one A100 GPU, nominal 80 GB, 24 vCPUs.

H100 was considered before A100. `az vm list-skus --resource-type virtualMachines`
returned:

| SKU | Regions returned | Reported GPUs | Reported vCPUs | Regions with `NotAvailableForSubscription` |
| --- | --- | --- | --- | --- |
| `Standard_NC40ads_H100_v5` | 25 | 1 | 40 | 0 |
| `Standard_NC24ads_A100_v4` | 15 | 1 | 24 | 0 |

Two regions returned for the H100 SKU, `CentralUSEUAP` and `JioIndiaCentral`, are
not registered for this subscription (`NoRegisteredProviderFound` for
`locations/usages`) and are therefore not eligible.

Zones were recorded per region — for example `australiaeast` offers zones 1 and
3, `eastus2` offers 1, 2 and 3 — and are published in
`azure/azure_discovery.json`. No zone was selected, because no deployment was
attempted.

T4, A10, V100, multi-GPU ND-series, Spot VMs and confidential-GPU substitutions
were not eligible and were not used. `study4f_e1_resource_selection.sku_record`
raises on every one of them, so an ineligible accelerator cannot be reached even
by mistake.

Otherwise eligible regions were ordered lexicographically **before any deployment
result was observed**, over the canonical lowercase alphanumeric region name so
the order cannot depend on which API answered.

## 6. Quota versus capacity

These are reported separately, because they are different things.

**Quota — measured.** `az vm list-usage` was queried in all 29 candidate regions.

| Metric | Value |
| --- | --- |
| `StandardNCadsH100v5Family` limit | `0` in every region returned for the SKU |
| `StandardNCADSA100v4Family` limit | `0` in every region returned for the SKU |
| Total regional `cores` limit | `100`, of which `0` used |
| Eligible SKU/region pairs with sufficient quota | `0` |
| Blocking dimension | VM-family vCPU quota |

The total-regional budget would have admitted one instance of either SKU. Only
the family quota blocks.

**Capacity — not observed.** Section 4.1 forbids provisioning anything when no
eligible SKU/region has sufficient quota, so zero deployments were attempted and
zero Spot capacity was used. Azure GPU capacity is therefore **unknown**. It is
explicitly *not* reported as unavailable, and this successor's terminal state is
not `STUDY4F_E1_QUALIFYING_ACCELERATOR_CAPACITY_UNAVAILABLE`.

**The single permitted quota request.** The authenticated quota API
(`Microsoft.Quota/quotas`, api-version `2023-02-01`) supports a bounded
noninteractive request, so exactly one was submitted, for exactly one instance of
the first eligible SKU/region:

| Item | Value |
| --- | --- |
| SKU | `Standard_NC40ads_H100_v5` |
| Quota name | `standardNCadsH100v5Family` |
| Region | `australiaeast` (lexicographic head of the H100 set) |
| Requested limit | `40` family vCPUs |
| Instances requested | exactly `1` |
| Request ID | `a6817961-e0f7-4cbe-a1ef-7ac4104e1089` |
| Submitted | `2026-08-18T03:40:05Z` |
| Provisioning state | `Failed` |
| Error code | `QuotaNotAvailableForResource` |
| Quota granted | none; the family limit is still `0` |

No larger quota was requested and no second request was submitted. Because the
self-service path refused the request, the exact operator-facing escalation
packet was also produced, at
`azure/operator_quota_request_packet.md`, and the successor stops in the same
registered state.

## 7. Measured GPU identity and free memory

None. No accelerator was ever provisioned, so `nvidia-smi` was never run against
an E1 device and no free-memory measurement exists.

The registered gate is published and tested against synthetic observations:
measured free device memory must strictly exceed **69,502,926,848** bytes, which
is not a new number — it is exactly what the predecessor's own
`study4f_resource_route.required_bytes("RP_B3")` computes from 64,000,000,000
weight bytes, 1,207,959,552 maximum registered KV-cache bytes and a 4,294,967,296
safety reserve. A paper specification of 80 or 94 GB does not satisfy it, and the
gate refuses to accept an unmeasured value.

## 8. Azure resources created and cleanup state

| Item | Count |
| --- | --- |
| Resource groups created | 0 |
| VMs provisioned | 0 |
| Disks, NICs, public IPs created | 0 |
| Deployment attempts | 0 |
| Billable accelerators remaining | 0 |
| Resources remaining | 0 |

There is nothing to clean up. No existing resource group was used and none was
deleted. The dedicated resource-group name this successor *would* have used is
deterministically derived from the E1 authority commit
(`rg-study4f-e1-f35ad870cabe7107`), and the cleanup code refuses any target that
contains a glob or an unresolved variable, or that lies outside a dedicated E1
group.

## 9. Shakedown attempts and accelerator-hours

| Item | Value |
| --- | --- |
| Original Study 4F attempts used | 1 of 3 |
| Original accelerator-hours used | 0 of 6 |
| E1 additional attempts permitted | 2 |
| E1 attempts used | 0 |
| Total accelerator-hours permitted | 6 |
| Accelerator-hours used | 0 |
| Study-bank outputs inspected during shakedown | 0 |

The shakedown was never entered, because it needs an accelerator.

## 10. Container and execution-seal identities

None. No container image was pulled or built and no execution seal was created,
so there is no container digest, no frozen driver or framework version set, no
realized bank and no seal. Developmental execution authorization is `false`.

## 11. Bank hashes and invariant checks

No bank was realized. `study_banks_realized` is `0` and no bank bytes are
committed. The registered bank invariants were reconfirmed **as design
properties of the bound generator**, not as properties of realized items:
two single-family banks of 104 items each, 26 of each answer label per bank, 15
of each label in the deterministic first 60, cross-bank disjointness by canonical
content hash, and a seed derived from the original Study 4F authority commit.

## 12. Cells reached and skipped

| Item | Count |
| --- | --- |
| Registered cells | 16 |
| Cells reached | 0 |
| Cells skipped | 16 |

Every cell was skipped for the same reason: no qualifying accelerator was ever
provisioned, so no model was loaded. Consequently there are **no**
correct/incorrect/unparseable counts, **no** gate calculations, **no**
candidate-local transitions and **no** raw outputs or receipts to hash. The
ladder was not run and RT was not run.

Reasoning about why: the gate calculations that *would* apply are unchanged and
published — CoT passes at `≥ 90` of 104, E0 passes at `≥ 41` of 60, each at
`alpha_per_cell = 1/320` under Bonferroni over all 16 cells regardless of how
many are reached. None of them was evaluated against any observation.

## 13. Full-suite differential

| Item | Value |
| --- | --- |
| Registered starting baseline | `9 failed, 5,119 passed, 16 skipped` |
| Reproduced at the starting commit | yes, with the same nine node IDs |
| Suite at the final head | `9 failed, 5,119 passed, 16 skipped` |
| Failure node IDs at the final head | identical to the starting nine |
| New non-scope failures | 0 |
| New scope expiries recorded | 0 |
| Historical failures edited or suppressed | 0 |

No scope assertion expired. Every E1 path was added strictly inside
`studies/study4f/`, which the Study 3R operator-governance module already admits,
so the two governance scope predicates still pass and the four previously
recorded Study 4F expiries are unchanged. Nothing in `tests/` was modified, and
the section 11 expiry-recording branch was therefore not needed and not used.

The Study 4F tests and the E1 tests are collected explicitly, because the
repository's default `pytest` configuration sets `testpaths = ["tests"]`:

```
python -m pytest studies/study4f/tests studies/study4f/execution-e1/tests
```

## 14. Evidence ledger

`paper/evidence_ledger.csv` is byte-unchanged and still ends at `EV-0016`. This
successor wrote zero evidence rows, because it produced no evidence about any
scientific question.

## 15. Prohibited-operation counters

| Counter | Value |
| --- | --- |
| D0 runs | 0 |
| Logit reads | 0 |
| Activation collections | 0 |
| Activation patches | 0 |
| Checkpoint downloads | 0 |
| Weight files acquired | 0 |
| Model constructions | 0 |
| Forward passes | 0 |
| Generations | 0 |
| Generated tokens | 0 |
| Execution seeds drawn | 0 |
| RP-B selections | 0 |
| GPU seconds | 0 |
| GitHub Actions runs | 0 |

No prohibited fallback was attempted: no quantization, no sharding, no CPU
offload, no disk offload, no `device_map="auto"`, no Spot capacity, no ineligible
accelerator substitution, no enlarged quota request and no threshold, estimand or
claim-language change.

## 16. Publication order

Section 13 requires strictly linear fast-forward publication, with unreachable
steps skipped. Under the section 4.1 terminal branch the shakedown disposition,
the realized banks and execution seal, and the raw execution artifacts are all
unreachable, so three of the six registered steps were skipped:

| Step | Commit | Contents |
| --- | --- | --- |
| 1. E1 authority alone | `58cdcda0ec3848ba2bd3a6c525b3c28ac8955d69` | the authority file, and nothing else |
| 2. Azure discovery/quota disposition plus tested launcher | `28c7ff3160ce0ee386c83311199fe91e068bc414` | predecessor manifest, invariants, discovery, quota disposition, operator packet, launcher modules, schema, README, tests |
| 3. shakedown disposition | — | skipped; unreachable without an accelerator |
| 4. realized banks and execution seal | — | skipped; unreachable without a passed shakedown |
| 5. raw execution artifacts | — | skipped; no cell was executed |
| 6. final disclosure and E1 status | this commit | this disclosure and `STATUS.json` |

`origin/main` was re-fetched before every publication and matched the expected
head each time. Every publication was a fast-forward. There was no GitHub
Actions run, no merge, no rebase, no squash, no force-push and no history
rewrite.

## 17. Scientific claim ceiling

This successor produced **no scientific result** and is not evidence about any
research question.

It establishes only three things, all of them procedural: that the published
Study 4F instrument binds byte-exactly and its registered semantic invariants
still hold; that on this Azure identity the blocking dimension for a qualifying
accelerator is VM-family vCPU quota rather than SKU availability or Azure Policy;
and that the single permitted minimal quota request was submitted and refused.

It establishes nothing about whether any registered checkpoint has generated-CoT
task headroom on D2 or on D3, nothing about zero-generated-reasoning-token
expressed competence, nothing about whether a natural positive-reference
candidate exists in the registered ladder, nothing about whether the raw
direct-answer interface is valid or invalid, and nothing about Azure GPU
capacity.

No result here may be described as establishing the existence, the
non-existence, the observability or the unobservability of J-space. No RP-B was
identified and none was confirmed. Nothing authorizes automatic confirmation,
D0, activation capture, patching or Study 3M.
