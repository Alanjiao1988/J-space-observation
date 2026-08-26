# Study 4F-M1 final disclosure

Authority: `studies/study4f/prompts/study4f_m1_mooncake_four_a100_execution_authority.md`
M1 authority commit: `1ca457e105b29b73027ad21c6adce9a9e8904682`
Predecessor: `ddf592010cd8788b637a90a998724f7ccdce4383`

Exact final registered state:

```
STUDY4F_M1_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER
```

**Plain-language judgment.** The Mooncake four-A100 route executed the published
Study 4F instrument end to end, without modification, and the study reached a
registered terminal state. No candidate in the registered ladder qualified, so
the target checkpoint was never run. This **is** a scientific result in the
narrow registered sense — a terminal state of a pre-registered developmental
instrument — and it is **not** evidence about J-space. Nothing here says J-space
exists, does not exist, is observable or is unobservable, and no cell in this
study could have tested any of those.

---

## 1. Starting and final identity

| Item | Value |
| --- | --- |
| Starting commit | `ddf592010cd8788b637a90a998724f7ccdce4383` |
| Starting tree | `a96b6696a20d9169a397b427595a28225b52b53e` |
| M1 authority commit | `1ca457e105b29b73027ad21c6adce9a9e8904682` |
| M1 authority tree | `55d59d8246966675421b00205d873586221bf335` |
| Seal commit | `126563842974097e93c202ef0cfc088dc2fde208` |
| Evidence ledger | ends at `EV-0016`, unchanged, 0 rows added |
| Ancestry | strictly linear, merge-free, fast-forward only |

Study 4F-E1 remains at `STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL` and
Study 4F-E1-Q1 remains at `STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION`. No
Q1/Q1R ticket or quota request was queried, updated or closed.

## 2. Authority identity and alone-first ordering

The authority was committed **alone** as the sole path in commit `1ca457e`,
before the Storage Account was created and before either VM was modified. A test
asserts this mechanically by reading `git show --name-only` for that commit and
requiring the result to be exactly one path.

## 3. Mooncake redacted identity

| Item | Value |
| --- | --- |
| Cloud | AzureChinaCloud |
| Subscription (salted sha256) | `942506e4…d84c6b31` |
| Subscription (last four) | `8845` |
| Tenant (salted sha256) | `e0bbcf27…26c3f343` |
| Resource group (salted sha256) | `a6e043d1…604203c4` |
| Resource group (safe name) | `J-space` |

No raw subscription id, tenant id, GPU UUID, storage key or SAS token appears in
any committed file. A regex test over every M1 file enforces this.

## 4. CPU VM: actual versus recommended

| Dimension | Recommended | Actual (`cpuserver`) | Verdict |
| --- | --- | --- | --- |
| Architecture | x86-64 Linux | x86-64 Ubuntu 24.04.4 LTS | meets |
| vCPU | 8 | 16 | exceeds |
| RAM | 32 GiB | 62 GiB | exceeds |
| OS disk | ≥128 GiB | 30 GiB (P4) | **below** |
| Staging capacity | ≥512 GiB | 600 GiB at `/mnt` | exceeds |
| Outbound network | required | present | meets |
| OCI engine | required | not installed | not needed, see §7 |

The undersized OS disk is a disclosed warning, not a blocker: staging never used
the OS disk.

## 5. GPU VM: actual hardware, memory and topology

| Item | Value |
| --- | --- |
| VM | `a100-vm`, `Standard_NC96ads_A100_v4`, ChinaEast3 |
| CPU | 96 vCPU, AMD EPYC 7V13, 2 sockets, 1 thread/core |
| RAM | 866 GiB visible |
| Accelerators | 4 × NVIDIA A100 80GB PCIe, compute capability 8.0 |
| Driver / CUDA | 580.173.02 / 13.0 |
| MIG | Disabled on all four |
| Local NVMe | 4 × 894.3 GiB, RAID0 XFS, 3.5 TB at `/scratch` |
| Foreign processes on GPU | 0 |

Memory floor arithmetic, measured rather than assumed:

```
required free per device : 69,502,926,848 bytes
nvidia-smi free          : 85,094,039,552 bytes
torch in-container free  : 84,648,263,680 bytes
margin over the floor    : 15,145,336,832 bytes  (21.8%)
verdict                  : PASS on all four devices
```

Topology is **pairwise** NVLink: GPU0↔GPU1 `NV12` and GPU2↔GPU3 `NV12`, with
`SYS` across the pairs. This is not a blocker because the primary execution uses
isolated single-GPU workers and never crosses a device boundary.

## 6. Accepted degradations and warnings

1. **CPU and GPU VM in different regions** (chinanorth3 vs chinaeast3). Worked
   around by having the GPU host fetch checkpoints directly, which also avoided
   a 113.9 GB cross-region transfer and its egress charge.
2. **Pairwise NVLink, not full mesh.** Irrelevant to isolated single-GPU workers.
3. **`huggingface.co` unreachable from Mooncake.** DNS is poisoned (Alibaba DoH
   returns a Facebook address) and direct TLS to the real CloudFront addresses is
   SNI-blocked. Worked around by proving byte equality per file rather than
   trusting a mirror by name — see §9.
4. **`registry-1.docker.io` unreachable.** Worked around with a registry mirror
   while still pinning the base image by its authoritative digest, so the mirror
   could not substitute a different image.
5. **CPU VM OS disk is 30 GiB, below the 128 GiB recommendation.**
6. **`Microsoft.HpcCompute/NvidiaGpuDriverLinux` does not exist in Mooncake.**
   Worked around by installing `nvidia-driver-580-server` plus the matching
   `linux-modules-nvidia-580-server-6.8.0-1064-azure` from the Ubuntu archive.
   The 570 and 550 series have no module package for this kernel, which is why
   the first attempt silently failed.
7. **Cost Management and the consumption meter are both unusable.** See §12.
8. **One order-dependent flake in the repository baseline.** Adjudicated in
   `test_differential.json`; it is not an M1 regression.

## 7. Storage Account and containers

| Property | Value |
| --- | --- |
| Name | `s4fm11ca457e105b29b7` (derived from the authority commit) |
| Region | chinaeast3, same as the GPU VM |
| Kind / SKU / tier | StorageV2 / Standard_LRS / Hot |
| HTTPS only | true |
| Minimum TLS | TLS1_2 |
| Anonymous blob access | disabled |
| Containers | `models`, `oci`, `runs`, `logs`, `seals`, `handoff`, all private |
| Auth | system-assigned managed identity on **both** VMs |
| Role | `Storage Blob Data Contributor`, scoped to this account only |
| SAS tokens issued | 0 |
| Keys committed | none |

Exactly one Storage Account was created. No ACR, Key Vault, Bastion, NAT
Gateway, VPN Gateway, Private Endpoint, Firewall, Load Balancer, Log Analytics
workspace or ML workspace was created.

The data-plane path was verified end to end. The first token request used
audience `https://storage.chinacloudapi.cn/` and Mooncake rejected it with
`InvalidAuthenticationInfo — Audience validation failed`. The correct audience is
`https://storage.azure.com/`, after which PUT and GET both returned success.

Final contents, all written with the managed identity alone, no SAS and no key:

| Container | Blobs | Bytes | Contents |
| --- | --- | --- | --- |
| `models` | 25 | 113,860,639,632 | all 34 checkpoint files, content-addressed |
| `oci` | 2 | 3,183,944,622 | frozen execution image archive + manifest |
| `runs` | 11 | 581,732 | 10 per-cell item journals + logs archive |
| `logs` | 6 | 3,249 | shakedown report + four device canaries |
| `seals` | 3 | 32,027 | acquisition manifest, report, blob index |
| `handoff` | 0 | 0 | — |
| **total** | **47** | **117,045,201,262** | **109.00 GiB** |

Checkpoint bytes use content-addressed paths `models/sha256/<aa>/<full sha256>`,
so the blob name *is* the proof of what the blob contains. Content addressing
deduplicated the tokenizer and generation-config files that are byte-identical
across checkpoints, which is why 34 files occupy 25 blobs. Two round-trip spot
checks — a 679-byte `config.json` and an 8.79 GB weight shard — were downloaded
back and re-hashed to exactly their blob names.

The OCI archive was likewise downloaded back out of Blob and re-hashed
byte-identically, so the storage transport boundary is proven in both directions.

## 8. NVMe: proof of ephemerality before formatting

Before any disk was touched, all four devices were mechanically proven to be
ephemeral local scratch:

* model string `Microsoft NVMe Direct Disk`;
* no partition table and no filesystem (`blkid` empty — never formatted);
* not mounted anywhere;
* absent from `/dev/disk/azure/scsi1/`, which did not exist at all, proving there
  were no attached managed data disks.

The OS disk `sda` and the resource disk `sdb` were identified explicitly and
never touched. A pre-format guard re-checked every device and would have aborted
on any filesystem or mount.

## 9. Immutable acquisition and the byte-equality proof

All four registered checkpoints were acquired at their exact pinned revisions:

| Role | Repository | Revision | Files | Verified |
| --- | --- | --- | --- | --- |
| RT | DeepSeek-R1-Distill-Qwen-1.5B | `ad9f0ae0…` | 5 | 5/5 |
| RP_B1 | DeepSeek-R1-Distill-Qwen-7B | `916b56a4…` | 7 | 7/7 |
| RP_B2 | DeepSeek-R1-Distill-Qwen-14B | `1df85071…` | 9 | 9/9 |
| RP_B3 | DeepSeek-R1-Distill-Qwen-32B | `711ad2ea…` | 13 | 13/13 |

**34 / 34 files, 113,881,744,368 bytes, all verified.**
Recursive rollup: `b34f2d28bf5aad1f3aafd583b5b1f6bd0d754615e527420b6b5a2773be08ef6d`

Because the authoritative origin is unreachable from Mooncake, byte equality was
**proven per file** rather than assumed:

* every `.safetensors` file was checked against the HuggingFace **LFS object id**
  at the exact pinned revision;
* every small file was checked against the HuggingFace **git blob id**;
* `config.json`, `generation_config.json`, `tokenizer.json` and
  `tokenizer_config.json` were **additionally** cross-checked against the
  SHA-256 already committed in
  `studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json`, and all
  matched.

An independent third source agreed as well: ModelScope's published SHA-256 for
all 15 weight files matched the HuggingFace LFS object ids exactly, byte size
included. A source that reproduces every authoritative digest is byte-equal by
construction, so this is not a checkpoint substitution.

No weights were quantized, converted, merged, renamed internally, resharded or
repacked, `trust_remote_code` stayed false, and no weight byte entered Git.

## 10. Shakedown

| Item | Value |
| --- | --- |
| Attempts permitted entering this invocation | 2 |
| Complete attempts consumed | 1 |
| Attempts remaining | 1 |
| Accelerator-hours permitted | 6 |
| Accelerator-hours consumed by shakedown | 0.0011 |
| Result | **PASS**, 16/16 checks |

Fixtures were synthetic and non-study (`is_scientific_item=false`); no D2/D3 bank
was realized during shakedown and zero study-task outputs were inspected.

The frozen `W1_RAW_DIRECT` surface hash recomputed on the substrate as
`9dab5a865967308bc43b219f5b44476cc610fb0b310dd6f528dd3fd0934a4c95`, matching the
value registered in the protocol exactly.

A four-device equivalence canary produced byte-identical token ids
`[151649, 271]` on all four A100s. It is recorded explicitly as an **engineering
qualification only**; it is not scientific evidence and does not enter the
evidence ledger.

Two whitelisted engineering repairs are disclosed: two of this invocation's own
synthetic fixtures were mis-authored and correctly rejected by the instrument's
eligibility check, and `CUBLAS_WORKSPACE_CONFIG=:4096:8` was set so that the
already-registered determinism requirement is actually in force. Neither touched
a scientific byte.

## 11. Formal execution and the state-machine verdict

The seal was published at commit `1265638` **before** the first study-bank model
call. Seal sha256:
`5a59cc432ebb63dc23ea5ed07fe9ba207124b11f731a13d6422f203d4c3973c7`.

| Cell | n | correct | unparseable | boundary | verdict |
| --- | --- | --- | --- | --- | --- |
| `RP_B1\|D2\|COT` | 104 | 97 | 7 | 90 | **PASS** |
| `RP_B1\|D3\|COT` | 104 | 97 | 7 | 90 | **PASS** |
| `RP_B1\|D2\|E0` | 60 | 0 | 60 | 41 | FAIL |
| `RP_B1\|D3\|E0` | 60 | 0 | 60 | 41 | FAIL |
| `RP_B2\|D2\|COT` | 104 | 104 | 0 | 90 | **PASS** |
| `RP_B2\|D3\|COT` | 104 | 101 | 3 | 90 | **PASS** |
| `RP_B2\|D2\|E0` | 60 | 0 | 60 | 41 | FAIL |
| `RP_B2\|D3\|E0` | 60 | 0 | 60 | 41 | FAIL |
| `RP_B3\|D2\|COT` | 104 | 94 | 10 | 90 | **PASS** |
| `RP_B3\|D3\|COT` | 104 | 85 | 19 | 90 | FAIL |

**Cells executed: 10. Cells skipped: 6.** `RP_B3` E0 was never scheduled because
its CoT gate was not met on D3, and all four RT cells were never scheduled
because no candidate qualified. Both are registered rules, not shortcuts.

Candidate-local transitions, produced by `study4f_state_machine.run_study()`:

* `RP_B1` — `E0_NOT_OBSERVED_ON_D2_AND_D3`, not qualified;
* `RP_B2` — `E0_NOT_OBSERVED_ON_D2_AND_D3`, not qualified;
* `RP_B3` — `COT_HEADROOM_ABSENT_ON_D3`, not qualified;
* qualified candidate: **none**; RT authorized: **false**; RT cells run: **0**.

### Why E0 scored zero, and why that is a measurement rather than a bug

All 240 E0 continuations were `UNPARSEABLE`. This was investigated rather than
assumed:

* the registered answer tokens resolve to **distinct single ids** on both
  tokenizers: `A=32, B=33, C=34, D=35`;
* `eos_token_id` is `151643` and collides with none of them, so `parse_e0` did
  not raise;
* RP_B1's continuations all began with token `151649` = `</think>`;
* RP_B2's all began with token `32313` = `Okay`;
* the frozen contract requires exactly `[answer token, EOS]`, so both are
  `UNPARSEABLE` by the published rule, and the protocol counts unparseable as
  **incorrect** rather than dropping it;
* the same checkpoints scored 97/104 and 104/104 on CoT over the same items, so
  the models are not broken.

Two independent checkpoints failing with **two different** non-answer surfaces is
consistent with a real behavioural regularity under the raw-direct envelope. No
parser was modified, no answer surface was added, no prefix matching, whitespace
normalization, textual reparsing or post-hoc surface addition was enabled, and
no cell was rerun after its result was seen.

### Execution integrity

| Property | Value |
| --- | --- |
| Total items journalled | 864 |
| Unique journal keys | 864 |
| Duplicate keys | **0** |
| Create-only violations | **0** |
| Distinct seals across all items | 1 |
| Distinct container images | 1 |
| Cells repeated after seeing a result | 0 |
| Engineering fixes after the first study-bank call | 0 |
| Hardware switches after the first study-bank call | 0 |
| Reseals | 0 |
| Journal key rollup | `eca3f9c0…8412c3dd` |

Parallelism stayed inside the registered dependency rules: the ladder ran
sequentially, CoT D2 and CoT D3 of the same candidate ran concurrently on
separate GPUs, E0 was unlocked only after both CoT cells of that candidate
passed, and RT was gated on a qualified candidate. Item remained the statistical
unit; GPU workers were never treated as independent samples.

## 12. Counters

| Counter | Value |
| --- | --- |
| Model constructions | 10 |
| Forward passes / prefills / generations | 864 |
| Execution seeds drawn | 416 |
| Cells executed / skipped | 10 / 6 |
| Logit reads | **0** |
| Activation collections | **0** |
| Activation patches | **0** |
| D0 runs | **0** |
| RP_B selections | **0** |
| Evidence-ledger rows written | **0** |
| GitHub Actions runs | **0** |
| Study banks realized | 2 development, 0 confirmation |

No D0, activation capture, activation patching or Study 3M operation was
authorized or performed. Behavioural success was never used to infer such
authorization.

## 13. Scientific result and its ceiling

**A scientific result was produced, in exactly one narrow sense:** the
pre-registered developmental instrument reached the registered terminal state
`STUDY4F_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER`.

What it establishes:

* under the registered C1 long-generated-CoT route, the 7B checkpoint reaches
  97/104 at both depths, the 14B reaches 104/104 and 101/104, and the 32B reaches
  94/104 at D2 but only 85/104 at D3, against a boundary of 90;
* under the registered W1 raw-direct route, the 7B and 14B checkpoints produced
  zero parseable answer surfaces across 120 items each;
* no candidate in the registered ladder qualified, so RT was never run.

What it does **not** establish:

* nothing about RT, whose four cells were never executed;
* nothing about whether the raw-direct interface is valid or invalid — three
  checkpoints emitting a non-answer first token is a measurement of those
  checkpoints under that envelope, not a verdict on the interface;
* **nothing about whether J-space exists, is observable or is unobservable.**
  No cell in this study could test that and none was designed to;
* nothing confirmatory: only development banks were realized, no confirmation
  bank exists, and confirmation remains unauthorized;
* nothing that generalizes beyond the four registered checkpoints, two depths and
  two interfaces;
* nothing about internal mechanism.

## 14. Paid-resource and unit-price inventory

Price resolution followed the required order and is reported honestly.

1. **Subscription price sheet / Cost Management rate — UNAVAILABLE.**
   Cost Management returns `NotFound: Given subscription doesn't have valid
   WebDirect/AIRS offer type`; `Microsoft.Consumption/pricesheets/default`
   returns `No type was found that matches the controller named
   'ArmPriceSheets'`; zero billing accounts are visible.
2. **Actual consumption meter — UNAVAILABLE.**
   `Microsoft.Consumption/usageDetails` returns **HTTP 500** on every supported
   api-version (`2026-06-01`, `2023-03-01`, `2021-10-01`). This is a server-side
   failure, not a client defect.
3. **Official `azure.cn` pages — PARTIAL.**

| Resource | Provenance | SKU | Meter | Unit price | Accrued | Continuing |
| --- | --- | --- | --- | --- | --- | --- |
| `a100-vm` | session | NC96ads_A100_v4 | Linux compute, ChinaEast3 | **`CONTRACT_UNIT_PRICE_UNAVAILABLE`** | UNRESOLVED | UNRESOLVED/h |
| `cpuserver` | operator | D16ds_v5 | Linux compute | ¥6.63–7.032/h | ¥66.43–70.46 | ¥6.63/h |
| `a100-vm_OsDisk` | session | Premium P15, 256 GiB | managed disk | ¥225.41/mo | ¥3.32 | ¥225.41/mo |
| `cpuserver_OsDisk` | operator | Premium P4, 30 GiB | managed disk | ¥42.04/mo | ¥0.58 | ¥42.04/mo |
| `a100-vmPublicIP` | session | Standard static | public IPv4 | ¥0.026/h | ¥0.28 | ¥19.34/mo |
| `cpuserver-ip` | operator | Standard static | public IPv4 | ¥0.026/h | ¥0.26 | ¥19.34/mo |
| `s4fm11ca457e105b29b7` | session | StorageV2 Hot LRS | blob capacity | `CONTRACT_UNIT_PRICE_UNAVAILABLE` | UNRESOLVED (109.00 GiB) | UNRESOLVED/mo |
| VNets / NSGs / NICs | mixed | — | none | ¥0 | ¥0 | ¥0 |
| Local NVMe 3.5 TB | included in SKU | — | none | ¥0 | ¥0 | ¥0 |

`Standard_NC96ads_A100_v4` appears **nowhere** on the official azure.cn
virtual-machine pricing page — a scan of the full 7,865,382-byte page for
`NC96ads`, `NC24ads`, `NC48ads` and `A100` returns zero matches — and the Azure
China retail price API returns `Count=0` for it in every region. The A100 SKU is
quote-on-request in Mooncake. **No number was invented and no Global Azure retail
price was used as if it were a Mooncake price.**

Both VMs report an empty `plan` object, so no marketplace or third-party software
charge applies. No internet or cross-region egress meter was triggered: model
bytes were pulled *into* chinaeast3 (inbound, unbilled) and all 19 blobs were
written same-region.

### Totals

| Item | Value |
| --- | --- |
| Resolved invocation cost | **¥70.87 – ¥74.90** |
| Unresolved | `a100-vm` compute — the dominant charge; blob capacity for 109.00 GiB |
| Total invocation cost | `UNRESOLVED_BECAUSE_THE_DOMINANT_METER_HAS_NO_RESOLVABLE_PRICE` |
| Continuing, resolved portion | ¥7.05/hour, ¥169.16/day |

> ⚠️ **The resolved figures EXCLUDE `a100-vm` compute, which is by far the
> largest charge. Four A100 80GB accelerators bill continuously while the VM is
> running, and both VMs, both disks, both public IPs and the Storage Account were
> deliberately left in place. Charges are still accruing.**

Actions that would stop each continuing charge without deleting anything —
**none of which this invocation is authorized to take**:

| Resource | Action | Stops | Does not stop |
| --- | --- | --- | --- |
| `a100-vm` | `az vm deallocate` | all A100 compute | P15 disk, public IP |
| `cpuserver` | `az vm deallocate` | D16ds v5 compute | P4 disk, public IP |
| managed disks | only deletion | — | — |
| public IPs | only dissociation + deletion | — | — |
| storage | delete blobs | capacity charge | — |

**Deallocating `a100-vm` is now safe.** It still destroys the `/scratch` RAID0,
but every one of the 113.9 GB of verified checkpoint bytes and the exact
execution container archive now live in Blob, so nothing unrecoverable is lost
and the work does not have to be re-acquired. Before the `models/` and `oci/`
uploads this was not true, and this disclosure previously said so.

## 15. Resource preservation

| Check | Value |
| --- | --- |
| VMs created by this invocation | **0** |
| VMs resized, redeployed, replaced or cloned | **0** |
| VMs deleted | **0** |
| VMs deallocated | **0** |
| Disks deleted or detached | **0** |
| Public IPs released | **0** |
| Storage Accounts created | **1** |
| Storage Accounts deleted | **0** |
| Unauthorized paid services created | **0** |
| Lifecycle / auto-delete policies configured | **0** |
| Final power state, `a100-vm` | **running** |
| Final power state, `cpuserver` | **running** |

Both VMs, the resource group, the Storage Account, every container, every blob,
every disk, every NIC, every public IP, both managed identities, both role
assignments and both VNets/subnets are intact.

## 16. Exact next legal action

Study 4F-M1 is terminal. The result is **developmental and non-confirmatory**.

The next legal action is an **operator decision**, not an automatic step:

1. decide whether to deallocate `a100-vm` to stop the dominant charge. This is
   now **safe**: `/scratch` is destroyed but every verified checkpoint byte and
   the exact execution container survive in Blob, so nothing must be
   re-acquired;
2. if confirmation of any finding is wanted, publish a **separate** authority
   with its own confirmation bank — which does not exist today — and its own
   registered transition.

No confirmation, D0, activation capture, patching or Study 3M work is authorized
by this state, and no successor study is drafted here.

**Nothing in this disclosure may be described as evidence about J-space.**
