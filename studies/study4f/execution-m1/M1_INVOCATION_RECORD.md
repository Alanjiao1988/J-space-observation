# Study 4F-M1 invocation record

Authority: `studies/study4f/prompts/study4f_m1_mooncake_four_a100_execution_authority.md`
M1 authority commit: `1ca457e105b29b73027ad21c6adce9a9e8904682`
Predecessor: Study 4F at `5fd9602df207e95789263d0f8d52428540f48fb8`

Exact current state:

```
STUDY4F_M1_RESOURCE_ROUTE_QUALIFIED_ACQUISITION_IN_PROGRESS
```

The plain-language judgment is procedural: the Mooncake resource route is
qualified and immutable acquisition is underway, but formal execution is not yet
authorized. **No scientific result.** No study-bank cell was executed, no model
output was scored and no claim about J-space was reached.

---

## 1. Starting and current identity

| Item | Value |
| --- | --- |
| Starting M1 authority commit | `1ca457e105b29b73027ad21c6adce9a9e8904682` |
| Starting M1 authority tree | `55d59d8246966675421b00205d873586221bf335` |
| Authority parent commit | `ddf592010cd8788b637a90a998724f7ccdce4383` |
| Authority parent tree | `a96b6696a20d9169a397b427595a28225b52b53e` |
| Study 4F predecessor commit | `5fd9602df207e95789263d0f8d52428540f48fb8` |
| Original Study 4F authority hash used for bank seeds | `7d5ff0837d77af9e6df9f49d580ec0e42bdc2729` |
| Current lifecycle state | `STUDY4F_M1_RESOURCE_ROUTE_QUALIFIED_ACQUISITION_IN_PROGRESS` |
| Evidence ledger | ends at `EV-0016` |

Study 4F-E1 remains in
`STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL`. Study 4F-E1-Q1 remains in
`STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION`. M1 does not amend,
reinterpret or close the Global Azure route, and no Q1/Q1R ticket or quota
request was queried or modified.

## 2. Authority identity and alone-first ordering

| Item | Value |
| --- | --- |
| Path | `studies/study4f/prompts/study4f_m1_mooncake_four_a100_execution_authority.md` |
| Byte length | 13,056 |
| SHA-256 | `8d07bee782c7c8f47adeba89f38d0a6b5093b2c895dd3bbd2df089485e5f0f46` |
| Git blob | `9e990aadda5bea2e0301d48b9fb249f539f873f4` |
| Commit | `1ca457e105b29b73027ad21c6adce9a9e8904682` |
| Tree | `55d59d8246966675421b00205d873586221bf335` |
| Parent commit | `ddf592010cd8788b637a90a998724f7ccdce4383` |
| Parent tree | `a96b6696a20d9169a397b427595a28225b52b53e` |

The authority was published alone as the sole path in its commit before any
Mooncake write. It governs one invocation only and adds resource topology,
resource binding, storage transport and resource accounting. It changes no
estimand, bank, threshold, parser, checkpoint, decoding contract, state or claim
language.

## 3. Mooncake identity and redaction

Only salted hashes and safe names are recorded. No raw subscription id, tenant
id, full Azure resource id, storage key, SAS token or full GPU UUID is committed.

| Item | Value |
| --- | --- |
| Cloud | `AzureChinaCloud` |
| Subscription salted SHA-256 | `942506e424308d326ff8c8e7cd3417f33b35c76a543dcf5e125a486dd84c6b31` |
| Subscription final four | `8845` |
| Tenant salted SHA-256 | `e0bbcf27e7a04070ff44cf33b12da5468aefd4954a764f576b7aa43c26c3f343` |
| Resource group salted SHA-256 | `a6e043d19f979b3fa3287c69892154f7a926d53666815b0bb8c4a487604203c4` |
| Resource group safe name | `J-space` |
| GPU VM safe name | `a100-vm` |
| CPU VM safe name | `cpuserver` |

## 4. CPU VM actual versus recommended configuration

| Dimension | Recommended | Actual | Disposition |
| --- | --- | --- | --- |
| vCPU | 8 | 16 | exceeds |
| RAM | 32 GiB | 62 GiB | exceeds |
| OS disk | at least 128 GiB | 30 GiB Premium_LRS | below recommendation |
| Staging disk | at least 512 GiB | 600 GiB resource disk at `/mnt` | exceeds |
| Region | same substrate preferred | `chinanorth3` | differs from GPU VM |
| OS | compatible x86-64 Linux | Ubuntu 24.04.4 LTS | compatible |

The OS disk shortfall is recorded as a degradation because staging space is
available at `/mnt`. It is not treated as a hard blocker by itself.

## 5. GPU VM hardware, memory and topology

| Item | Value |
| --- | --- |
| VM SKU | `Standard_NC96ads_A100_v4` |
| Region | `chinaeast3` |
| OS image | `Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:22.04.202608060` |
| OS | Ubuntu 22.04 LTS gen2 |
| vCPU | 96, AMD EPYC 7V13, 2 sockets, 1 thread/core |
| Visible RAM | 866 GiB |
| OS disk | 256 GiB Premium_LRS |
| Local NVMe | 4 x 894.3 GiB |
| Resource disk | 256 GiB |
| Power state | running |
| Operator-created | no |
| Session-created | yes |

The GPU observation is live-verified, not inferred from SKU:

| Item | Value |
| --- | --- |
| Driver | `580.173.02` |
| Host CUDA | `13.0` |
| Visible devices | 4 |
| Model | NVIDIA A100 80GB PCIe |
| Compute capability | 8.0 |
| MIG mode | Disabled on all four |
| Total memory per device | 85,093,777,408 bytes |
| Free memory per device, `nvidia-smi` | 85,094,039,552 bytes |
| Free memory per device, torch in container | 84,648,263,680 bytes |
| Registered floor | 69,502,926,848 bytes |
| Foreign GPU-memory processes | 0 |

Floor check arithmetic, using the lower torch-in-container measurement:

```
84,648,263,680 - 69,502,926,848 = 15,145,336,832 bytes
```

All four devices pass the registered floor. Full GPU UUIDs are not committed;
only the last twelve characters are recorded:

| GPU | UUID final twelve |
| --- | --- |
| 0 | `e85524f36fdf` |
| 1 | `b29579ca41a6` |
| 2 | `0ec45dca0dfc` |
| 3 | `5767cc3ad060` |

Topology is pairwise NVLink, not full mesh: GPU0-GPU1 is `NV12`, GPU2-GPU3 is
`NV12`, and cross-pair links are `SYS`. This is disclosed and is not a blocker
because primary execution uses isolated single-GPU workers.

## 6. Accepted degradations and warnings

| Warning or degradation | Disposition |
| --- | --- |
| CPU VM and GPU VM are in different regions: `chinanorth3` versus `chinaeast3` | disclosed warning, not a blocker |
| NVLink is pairwise, not full mesh | disclosed warning, not a blocker for isolated single-GPU workers |
| `huggingface.co` was unreachable from Mooncake | a byte-verified mirror was used |
| `registry-1.docker.io` was unreachable | a registry mirror was used while still pinning the base image by its authoritative digest |
| CPU VM OS disk is 30 GiB, below the 128 GiB recommendation | disclosed degradation; staging uses the 600 GiB resource disk at `/mnt` |
| Azure `NvidiaGpuDriverLinux` extension does not exist in Mooncake | driver installed from the Ubuntu archive |

None of these warnings changes the registered instrument, parser, thresholds,
bank seeds, checkpoint revisions or claim ceiling.

## 7. Runtime and worker isolation

| Item | Value |
| --- | --- |
| Docker | `29.1.3` |
| NVIDIA Container Toolkit | `1.20.0` |
| Base image | `pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime` |
| Base image digest | `sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126` |
| Torch | `2.4.1+cu121` |
| Container CUDA | `12.1` |
| Worker isolation | `CUDA_DEVICE_ORDER=PCI_BUS_ID` plus one-device `CUDA_VISIBLE_DEVICES` |
| Torch device count per worker | 1 on each of four workers |
| bfloat16 support | true |
| deterministic algorithms enabled | true |
| SDPA available | true |

## 8. Storage account configuration

Exactly one Storage Account was created.

| Item | Value |
| --- | --- |
| Safe name | `s4fm11ca457e105b29b7` |
| Region | `chinaeast3` |
| Kind | `StorageV2` |
| SKU | `Standard_LRS` |
| Access tier | Hot |
| HTTPS only | true |
| Minimum TLS | `TLS1_2` |
| Blob public access | false |
| SAS issued | no |
| Storage keys committed | no |

Containers are `models`, `oci`, `runs`, `logs`, `seals` and `handoff`, each
private. Authentication uses system-assigned managed identity on both VMs with
`Storage Blob Data Contributor` scoped to the Storage Account only.

## 9. Ephemeral NVMe and scratch

| Item | Value |
| --- | --- |
| Devices | four `Microsoft NVMe Direct Disk` devices |
| Before format | no partition table, no filesystem, not mounted |
| Managed-disk check | absent from `/dev/disk/azure/scsi1` |
| RAID | RAID0 over all four devices |
| Filesystem | XFS |
| Mount | `/scratch` |
| Mounted size | 3.5 TB |
| OS disk `sda` | untouched |
| Resource disk `sdb` | untouched |

The NVMe devices were proven ephemeral before formatting. No managed disk was
formatted as scratch.

## 10. Acquisition status and byte-equality proof

Acquisition is in progress and is not complete. The proof rule is per-file:

| File class | Authoritative byte-equality source |
| --- | --- |
| `*.safetensors` weights | HuggingFace LFS object id at the exact pinned revision |
| `config.json`, `generation_config.json`, `tokenizer.json`, `tokenizer_config.json` | SHA-256 already committed in `studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json` |

Every acquired file is hashed on the execution substrate after download and must
match its authoritative value before use. A byte-verified mirror is not a
checkpoint substitution when every authoritative SHA-256 and file size matches.

## 11. Shakedown

The registered shakedown has not yet run.

| Item | Value |
| --- | --- |
| Attempts remaining | 2 |
| Accelerator-hours remaining | 6 |
| Consumed by this invocation so far | 0 |
| Study-bank outputs inspected during shakedown | 0 |

Developmental execution authorization remains false until acquisition,
shakedown, bank realization and execution-seal publication are complete in the
registered order.

## 12. Counters

| Counter | Value |
| --- | --- |
| Checkpoint downloads | in progress |
| Model constructions | 0 |
| Forward passes | 0 |
| Prefill operations | 0 |
| Generations | 0 |
| Generated tokens | 0 |
| Logit reads | 0 |
| Activation collections | 0 |
| Activation patches | 0 |
| D0 runs | 0 |
| Execution seeds drawn | 0 |
| Study banks realized | 0 |
| RP-B selections | 0 |
| GPU seconds | 0 |
| Accelerator-hours | 0 |
| Evidence-ledger rows written | 0 |
| GitHub Actions runs | 0 |
| Cells executed | 0 |

No tokenizer construction, model construction, generation, scoring, D0,
activation capture or activation patching occurred.

## 13. Resource-change counters

| Item | Count |
| --- | --- |
| VMs created by this invocation | 0 |
| VMs resized | 0 |
| VMs deleted | 0 |
| Resources deleted | 0 |
| Storage Accounts created | 1 |

No resource was deleted or deallocated. No VM was created, resized, redeployed,
replaced or cloned by the authorized-execution phase. The GPU VM and CPU VM
remain running.

## 14. Evidence ledger

`paper/evidence_ledger.csv` is byte-unchanged and still ends at `EV-0016`.
This invocation wrote zero evidence rows. The recorded SHA-256 is
`3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1`.

## 15. What this state establishes

| Establishes | Does not establish |
| --- | --- |
| The Mooncake resource route is qualified: four live A100 80GB devices were observed above the registered floor, MIG was off and no foreign GPU-memory process was present. | Nothing about any checkpoint's CoT headroom or E0 competence, because no cell was executed. |
| Byte-exact acquisition is provable per file on this substrate under the registered mirror byte-equality rule. | Nothing about whether a natural positive reference exists, because the ladder was not run. |
| Exactly one Storage Account was created, and no VM was created, resized or deleted. | Nothing about whether J-space exists, is observable or is unobservable. |

## 16. Scientific claim ceiling

This invocation produced **no scientific result** and none could have been
produced at this state. No study-bank model call occurred. No cell reached a
registered scientific gate. No output was scored. No RP-B was identified and
none was confirmed.

It is impermissible to describe resource qualification, GPU memory, storage
configuration, acquisition status or mirror byte-equality as evidence about
J-space. Nothing here authorizes confirmation, D0, activation capture, patching
or Study 3M.

## 17. Next legal action

The next legal action is to complete byte-verified acquisition, then run the
registered shakedown within the inherited allowance, then realize the original
banks using the ORIGINAL Study 4F authority hash
`7d5ff0837d77af9e6df9f49d580ec0e42bdc2729`, then create and publish the
execution seal **before** the first study-bank model call.
