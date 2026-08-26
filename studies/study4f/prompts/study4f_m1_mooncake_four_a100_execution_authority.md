# Study 4F-M1 — Mooncake four-A100 execution authority

This authority is published alone, as the sole path in its commit, before any
Mooncake write. It governs one invocation only.

# 1. What this authority is, and what it is not

This is a **new parallel execution substrate**. It is not a reinterpretation,
amendment, continuation or closure of the Global Azure backlog.

Specifically:

* Study 4F-E1 remains in its registered state
  `STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL`.
* Study 4F-E1-Q1 remains in its registered state
  `STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION`.
* The Global Azure Q1/Q1R support ticket and quota request are a separate
  pending administrative route. This authority does not query, update, close,
  duplicate or reinterpret them.
* Earlier discussion of Azure China in prior sessions was hypothetical and
  involved no resource, ticket, authority or operation. Nothing in this
  authority claims otherwise, and no retrospective authority is asserted.

The Global Azure route and this Mooncake route are independent substrates for
the *same* unchanged instrument. Whichever substrate reaches execution first
does so under its own authority, and neither closes the other.

# 2. The existing scientific instrument remains normative

The published Study 4F instrument is normative and unchanged. This authority
adds **only**:

1. execution topology (which host runs which worker);
2. resource binding (which Mooncake resources are used);
3. storage transport (how immutable bytes reach the execution host);
4. resource accounting (what was paid for, and at what rate).

Nothing else is added, and nothing at all is subtracted.

The following may **not** be changed by this authority, by this invocation, or
by any artifact it produces:

* any estimand;
* either task bank, its size, its label balance, its seeds or its items;
* any threshold, alpha, pass boundary or exact binomial boundary;
* any parser, answer surface or decoding contract;
* any checkpoint repository or immutable revision;
* any claim, claim ceiling or interpretation;
* the candidate-local ladder, the development/confirmation separation, the
  RT gating rule or any registered stop state.

Concretely, the following remain exactly as registered:

| Registered element | Value |
| --- | --- |
| Statistical unit | item |
| `m_max` | 16 |
| `alpha_global` | 1/20 |
| `alpha_per_cell` | 1/320 |
| CoT cell | n = 104, pass boundary 90, null floor 3/4 |
| E0 cell | n = 60, pass boundary 41, null floor 1/2 |
| Banks | `D2_DEVELOPMENT_BANK` (104), `D3_DEVELOPMENT_BANK` (104) |
| Bank seed material | `STUDY4F\|7d5ff0837d77af9e6df9f49d580ec0e42bdc2729\|<bank id>` |
| Ladder | RP_B1 → RP_B2 → RP_B3, then RT only if a candidate qualifies |
| Unparseable | counted as incorrect |
| `trust_remote_code` | false |
| dtype | bfloat16, unquantized |

Bank realization uses the **original Study 4F authority commit hash**
`7d5ff0837d77af9e6df9f49d580ec0e42bdc2729` as registered seed material. It does
**not** use this authority's hash.

# 3. Conditional authorization of formal execution

Formal execution is **conditionally** authorized, and only after **all** of the
following gates pass, in order:

1. the existing Study 4F instrument binds byte-exactly;
2. all registered design statistics reproduce;
3. the exact registered checkpoint revisions are acquired byte-exactly and
   sealed;
4. both original banks are realized and every bank invariant and hash verifies;
5. the registered shakedown passes within the inherited allowance;
6. the execution seal is created and published before the first study-bank
   model call.

Developmental execution authorization remains **false** until the sealed commit
is published. This mirrors section 8 of the Study 4F-E1 authority and does not
relax it.

The formal execution budget and transition are inherited, not invented:

* transition: after publication of the seal, execute the existing Study 4F
  state machine **exactly once** (E1 authority section 9);
* budget: at most the 16 registered cells, subject to the candidate-local
  ladder and RT gating rules;
* shakedown allowance carried forward: **two attempts**, **six
  accelerator-hours**, of which this invocation may consume no more.

No cell may be repeated because its result is unfavorable. After the first
study-bank call, no engineering fix, hardware switch, reseal, parser change or
output reinterpretation is permitted.

# 4. Prohibited scientific operations

D0, activation capture, activation patching and any Study 3M operation remain
**prohibited** unless the existing committed Study 4F state machine explicitly
reaches and authorizes them. Behavioral success does not imply such
authorization and may not be used to infer it.

No new protocol version, no new task bank, no new study and no successor study
may be drafted during this invocation.

# 5. Resource decisions binding this invocation

These are operator decisions recorded here so that they can be mechanically
tested:

1. **Do not create any virtual machine.**
2. Do not resize, redeploy, replace, clone or recreate a VM.
3. Existing VMs may be inspected, configured, started, rebooted and used.
4. Do not delete, detach or replace any existing VM, disk, NIC, public IP or
   other operator-created resource.
5. Create **exactly one** new Storage Account, used for immutable model bytes,
   OCI image archives, logs, seals and results.
6. Do not create ACR, Key Vault, Bastion, NAT Gateway, VPN Gateway, Private
   Endpoint, Azure Firewall, Load Balancer, Log Analytics workspace, Azure
   Machine Learning workspace or any other paid service.
7. At the end, do not delete or deallocate either VM or any other Azure
   resource.
8. Do not configure automatic deletion or lifecycle expiration.
9. The final disclosure must report every paid resource, its actual unit price,
   estimated accrued cost and continuing cost rate.
10. Noncritical shortcomings are disclosed and worked around; only a registered
    hard blocker stops the invocation.

**Operator amendment recorded in-session:** modifying the configuration of
*existing* network resources (VNet, subnet, NSG, peering, DNS) is permitted.
This amendment does not permit creating a VM, and does not permit creating any
paid service excluded by decision 6.

# 6. Immutable acquisition and the mirror byte-equality rule

The registered checkpoints and immutable revisions are:

| Role | Repository | Immutable revision |
| --- | --- | --- |
| RT | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` |
| RP_B1 | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | `916b56a44061fd5cd7d6a8fb632557ed4f724f60` |
| RP_B2 | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | `1df8507178afcc1bef68cd8c393f61a886323761` |
| RP_B3 | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | `711ad2ea6aa40cfca18895e8aca02ab92df1a746` |

No checkpoint may be substituted. Weights may not be quantized, converted,
merged, renamed internally, resharded or repacked. `trust_remote_code` remains
false. Original model files are preserved byte-for-byte. Model weights are
never placed in Git.

A matching model name is **not** sufficient evidence of byte equality. Any
source other than the authoritative origin must be proven byte-equal per file.
The verification rule for this invocation is:

* **weight files (`*.safetensors`)** — the authoritative SHA-256 is the
  HuggingFace LFS object id at the exact pinned revision. Any byte source must
  reproduce that SHA-256 exactly, and the file size must match exactly.
* **`config.json`, `generation_config.json`, `tokenizer.json`,
  `tokenizer_config.json`** — the authoritative SHA-256 is the value already
  committed in
  `studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json`.
* every acquired file is hashed on the execution substrate after download and
  must match its authoritative value before it is used.

An incomplete or unverifiable source is a hard blocker. A source that
reproduces every authoritative SHA-256 exactly is byte-equal by construction,
and using it is not a substitution.

# 7. Execution topology

* exactly one isolated worker per visible GPU;
* `CUDA_DEVICE_ORDER=PCI_BUS_ID` and a single-device `CUDA_VISIBLE_DEVICES`
  for every worker;
* no tensor parallelism, no pipeline parallelism, no MIG, no multi-node
  execution for the primary behavioral study;
* parallelization only across cells the existing state machine declares
  simultaneously eligible and independent — never across the ladder, never
  across a development/confirmation boundary, and never across a precondition
  dependency such as CoT gating E0;
* item remains the statistical unit; GPU workers and repeated responses are
  never treated as independent samples;
* create-only outputs; resumption only from committed or sealed state-machine
  evidence;
* a checkpoint is never dynamically selected on the basis of favorable results.

Four GPUs may reduce wall time. They may not change the number of items,
responses, cells, retries or statistical units, and they do not change the
estimand.

Accelerator accounting reports three distinct quantities and never silently
substitutes one for another: VM wall-clock hours, allocated GPU-hours, and
actively used GPU-hours.

# 8. Hard blockers

The invocation stops fail-closed only for:

1. the target is not AzureChinaCloud/Mooncake;
2. the resource group or VM roles cannot be uniquely resolved;
3. no compatible x86-64 Linux execution path exists;
4. no A100 80GB GPU can be made visible with at least `69,502,926,848` free
   bytes without resizing, replacing a VM or killing an unowned process;
5. Storage Account creation is unauthorized or impossible;
6. neither VM can authenticate to or read/write the Storage Account;
7. the exact registered immutable checkpoint revisions cannot be acquired
   byte-exactly;
8. a required container base or dependency cannot be obtained with a frozen
   digest and no byte-equivalent source exists;
9. existing Study 4F instrument, statistics, state-machine or protected-byte
   validation fails;
10. proceeding would require changing an estimand, threshold, bank, parser,
    checkpoint, decoding contract or interpretation;
11. a protected historical artifact would have to be edited;
12. safe publication would require rewriting published Git history.

Everything else is an engineering warning or a disclosed degraded execution
condition.

# 9. Publication discipline

* fast-forward only; no merge, rebase, force-push or history rewrite;
* every Study 3R, Study 4F, E1, Q1 and Q1R artifact is preserved
  byte-identically;
* the evidence ledger stays at `EV-0016` unless the state machine reaches a
  state that authorizes a row;
* no GitHub Actions run is triggered;
* `origin/main` is refetched immediately before every publication, and
  unexpected advancement stops the invocation;
* tenant ids, subscription ids, credentials, access tokens, storage keys and
  full resource ids are never printed into a committed artifact; only salted
  identity hashes and explicitly authorized safe names are recorded;
* historical tests are never weakened, and unavoidable scope expiries are
  recorded rather than suppressed.

# 10. Registered identity of this authority

| Field | Value |
| --- | --- |
| Study id | `STUDY4F_M1` |
| Namespace | `studies/study4f/execution-m1/` |
| Cloud | AzureChinaCloud (Mooncake) |
| Subscription (salted sha256) | `942506e424308d326ff8c8e7cd3417f33b35c76a543dcf5e125a486dd84c6b31` |
| Subscription (last four) | `8845` |
| Tenant (salted sha256) | `e0bbcf27e7a04070ff44cf33b12da5468aefd4954a764f576b7aa43c26c3f343` |
| Resource group (salted sha256) | `a6e043d19f979b3fa3287c69892154f7a926d53666815b0bb8c4a487604203c4` |
| Predecessor commit | `ddf592010cd8788b637a90a998724f7ccdce4383` |
| Predecessor tree | `a96b6696a20d9169a397b427595a28225b52b53e` |
| Evidence ledger at start | `EV-0016` |

The salt is generated per invocation and is never committed.

# 11. Registered final states for this substrate

End in exactly one of:

* `STUDY4F_M1_RESOURCE_ROUTE_UNAVAILABLE`
* `STUDY4F_M1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT`
* `STUDY4F_M1_IMMUTABLE_ACQUISITION_FAILED`
* `STUDY4F_M1_SHAKEDOWN_FAILED_NO_STUDY_BANK_EXECUTION`
* `STUDY4F_M1_EXECUTION_INTERRUPTED_NO_REINTERPRETATION`
* `STUDY4F_M1_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER`
* `STUDY4F_M1_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM`
* `STUDY4F_M1_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED`
* `STUDY4F_M1_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION`

No state authorizes automatic confirmation, D0, activation capture, patching or
Study 3M. Nothing short of an executed scientific gate may be described as
evidence about J-space.
