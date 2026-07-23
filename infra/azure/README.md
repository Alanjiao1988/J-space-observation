# Azure Infrastructure for J-space Observation

This directory contains Azure-first automation for running J-space observation experiments on Azure GPU containers.

The local PC is planning and source-control only. Do not run real model
inference, model downloads, J-lens fitting, patching, ablations, or the
parser-v2 private launcher locally.

## Prerequisites

- Azure CLI (`az`)
- `containerapp` Azure CLI extension
- Active Azure subscription
- Registered providers:
  - `Microsoft.App`
  - `Microsoft.ContainerRegistry`
  - `Microsoft.Network`
  - `Microsoft.Authorization`
- Azure Container Apps GPU T4 quota in the target region

### Parser-v2 private Linux orchestrator

Run `09_build_parser_v2_eval.sh` and `10_run_parser_v2_locked_eval.sh` only
from one private Debian 12 VM attached to the execution VNet. The VM must have
no public IP and must resolve and reach the configured Blob private endpoint.
The launcher is Linux-only: its protected Bash re-execution, clean absolute
tool paths, managed-identity selection, and private Blob bootstrap are not
supported from the local Windows host.

Attach two existing user-assigned managed identities to the VM:

- a control-plane identity used by the authenticated Azure CLI session for
  the minimum ARM, Private DNS, ACR, and Container Apps permissions needed by
  the build/launcher; it must not be attached to Stage P or Stage E; and
- the runtime data identity bound in `runtime_config.json`, selected for Blob
  SDK access through the launcher's authenticated `AZURE_CLIENT_ID`; it is the
  only identity attached to Stage P and Stage E and retains only the bound
  Blob data and ACR pull roles.

The VM, NIC, subnet placement, and control identity are prerequisites, not
resources created by these scripts. Obtain explicit approval before
provisioning this cost-bearing orchestrator. Do not give either identity
storage keys, SAS tokens, credentials, or public-Blob access.

### Parser-v2 coordination zone

Provision this prerequisite outside these scripts, then bind its exact live
values in `variables.env` and `runtime_config.json`:

- one dedicated Azure Private DNS zone used only for parser-v2 coordination;
  do not reuse the Blob private-link zone;
- location `global`, API version `2024-06-01`, and the exact immutable
  `properties.internalId` copied into the configuration;
- exactly zero `virtualNetworkLinks` (the zone must remain unlinked); and
- one exact `CanNotDelete` management lock, either directly on the zone or
  inherited from its resource group or subscription. Bind the lock's complete
  resource ID, name, level, and API version `2016-09-01`.

An infrastructure owner can provision a direct-lock variant once (outside the
build/launch scripts) with nonsecret names such as:

```bash
COORDINATION_RESOURCE_GROUP="rg-parser-v2-coordination"
COORDINATION_ZONE="parser-v2-coordination.example.internal"
COORDINATION_LOCK="parser-v2-coordination-cannot-delete"

az network private-dns zone create \
  --resource-group "$COORDINATION_RESOURCE_GROUP" \
  --name "$COORDINATION_ZONE"
az lock create --name "$COORDINATION_LOCK" --lock-type CanNotDelete \
  --resource-group "$COORDINATION_RESOURCE_GROUP" \
  --namespace Microsoft.Network --resource-type privateDnsZones \
  --resource-name "$COORDINATION_ZONE"
```

Do not create a VNet link for this zone. A resource-group or subscription lock
may be used instead; bind that inherited lock's exact resource ID. Retrieve the
nonsecret values for `variables.env` read-only:

```bash
ZONE_ID="$(az network private-dns zone show \
  --resource-group "$COORDINATION_RESOURCE_GROUP" \
  --name "$COORDINATION_ZONE" --query id -o tsv)"
az rest --method get \
  --url "https://management.azure.com${ZONE_ID}?api-version=2024-06-01" \
  --query '{id:id,name:name,location:location,internalId:properties.internalId}'
az rest --method get \
  --url "https://management.azure.com${ZONE_ID}/virtualNetworkLinks?api-version=2024-06-01" \
  --query 'length(value)'
az rest --method get \
  --url "https://management.azure.com${ZONE_ID}/providers/Microsoft.Authorization/locks/${COORDINATION_LOCK}?api-version=2016-09-01"
```

The build and launcher perform only GET/list validation of the zone, links, and
lock. They never create, delete, or repair this prerequisite. Use read-only
`az rest --method get` on the configured zone and lock resource IDs, and list
`${zoneResourceId}/virtualNetworkLinks?api-version=2024-06-01`, before creating
the runtime configuration. A recreated zone (different `internalId`), any VNet
link, a missing/different lock, or a non-`CanNotDelete` level fails closed.

## Configuration

Copy `variables.example.env` to `variables.env` and fill in local values:

```bash
cp variables.example.env variables.env
```

Do not commit `variables.env`, credentials, tokens, or secrets.

## Scripts

- `00_check_prereqs.sh`: Bash readiness check; does not create resources.
- `00_check_prereqs.ps1`: PowerShell readiness check; does not create resources.
- `01_build_and_push_image.sh`: Build image in ACR; creates/uses Azure resources when explicitly run.
- `02_run_phase0_5.sh`: Run Phase 0.5 availability/model-loading check as a Container Apps Job.
- `03_run_phase1.sh`: Run Phase 1 dry-run as a Container Apps Job.
- `04_run_phase1_pilot.sh`: Run a small real Phase 1 pilot as a Container Apps Job.
- `09_build_parser_v2_eval.sh`: Build and immutably lock the dedicated CPU-only
  parser-evaluation image from the registered GitHub origin plus exact clean
  `origin/main` commit and a repository-pinned base digest. Local Git blobs are
  verified independently with Git replacement refs disabled, but ACR receives
  only the content-addressed remote Git URL/ref. The source must be a clean,
  fetched `HEAD == origin/main` before any committed helper is snapshotted or
  executed. A deterministic TXT RecordSet in the dedicated coordination zone
  binds the full build-domain SHA-256, contender nonce, TaskRun name, staging
  tag, exact request hash, source binding, and provenance. Only the process
  receiving and validating exact HTTP `201` from its one create-only PUT
  (`If-None-Match: *`) receives the ephemeral capability to issue the sole
  non-retrying TaskRun PUT. HTTP `200`/`202`, redirects, errors, or transport
  ambiguity never grant it. Every later path is GET-only and can never resubmit.
  The TaskRun durably exposes the exact `runRequest`; its child Run separately
  proves `QuickRun` status and the output digest. The canonical provenance binds
  source, Dockerfile/dependencies, ACR location/destination, image names,
  Linux/amd64 request, and exact nonsecret arguments. Recovery reauthenticates
  TaskRun identity/request, child Run identity/output, claim, OCI
  manifest/config hashes and provenance label, source tag/digest, and both
  immutable locks before finishing a missing final record.
- `10_run_parser_v2_locked_eval.sh`: Launch exactly one `P` or `E` execution
  with the same image digest, 2 CPU/4 GiB, managed identity, and zero platform
  retries. It derives every physical Azure name/resource ID from the canonical
  runtime configuration. Before each private read, ACA mutation, start, or
  adoption it reauthenticates the exact build TXT evidence, final ACR
  tag/digest, named TaskRun/request/source, child Run, OCI manifest/config
  provenance label, and tag/manifest locks. After persisted-state, source,
  image, and topology checks,
  a create-only launch TXT slot authorizes at most one immutable, uniquely named
  Job PUT. A separate create-only dispatch TXT slot binds that launch record,
  exact Job body/projection, state receipt, and baseline execution membership;
  the immutable Job must first reach an exact authenticated `Succeeded`
  provisioning state. Only then may a dispatch slot be created, and only its
  exact-`201` process may issue the sole non-retrying ACA start. Caller
  environment variables cannot redirect storage, networking, registry,
  identity, or Container Apps resources.

The parser-v2 locked-evaluation helpers are inert until explicitly invoked.
Build first. The build emits the write-once pair `image_binding.json` and
`image_binding.sha256`. Pass both the binding and its expected hash when creating
`runtime_config.json` and `implementation_manifest.json` together with
`scripts/create_parser_v2_runtime_config.py`. Supply the exact subscription,
resource group, ACA environment/job, managed identity, storage account/resource
ID/Blob endpoint/container, registered parent and authorization prefixes,
VNet/subnets, Blob private endpoint/connection/NIC IPs, Blob private DNS
zone/group/link, the distinct coordination zone/internal ID/zero-link
control/lock, and ACR resource/repository. Pass all
`--coordination-*` arguments exposed by the generator; they correspond exactly
to the `PARSER_EVAL_COORDINATION_*` values in `variables.example.env`.
Caller-supplied digest or base-image values are accepted only when they equal
the immutable binding. The generator
fetches the exact approved GitHub `main`, requires a clean
`HEAD == origin/main`, authenticates its own executing bytes against that
commit, and loads both the locked-evaluation core and frozen validator directly
from committed Git blob bytes. It then reads every registered source blob from
the same exact commit and cross-checks the complete image source binding.
The frozen four-field implementation-manifest schema is unchanged: its
`config_sha256` transitively binds the complete physical destination, embedded
image binding, coordination binding, and helper snapshot set. Runtime schema v5
embeds the complete nonsecret image binding plus its hash and essential
provenance record. The
authorization manifest directly records the image-binding and helper-snapshot
hashes as well as the destination and source bindings.

The exact coordination argument mapping is:

```bash
--coordination-private-dns-zone-name "$PARSER_EVAL_COORDINATION_ZONE_NAME"
--coordination-private-dns-zone-resource-id "$PARSER_EVAL_COORDINATION_ZONE_RESOURCE_ID"
--coordination-private-dns-zone-location "$PARSER_EVAL_COORDINATION_ZONE_LOCATION"
--coordination-private-dns-zone-internal-id "$PARSER_EVAL_COORDINATION_ZONE_INTERNAL_ID"
--coordination-private-dns-api-version "$PARSER_EVAL_COORDINATION_PRIVATE_DNS_API_VERSION"
--coordination-record-ttl "$PARSER_EVAL_COORDINATION_RECORD_TTL"
--coordination-expected-vnet-link-count "$PARSER_EVAL_COORDINATION_EXPECTED_VNET_LINK_COUNT"
--coordination-lock-name "$PARSER_EVAL_COORDINATION_LOCK_NAME"
--coordination-lock-resource-id "$PARSER_EVAL_COORDINATION_LOCK_RESOURCE_ID"
--coordination-lock-level "$PARSER_EVAL_COORDINATION_LOCK_LEVEL"
--coordination-management-lock-api-version "$PARSER_EVAL_COORDINATION_LOCK_API_VERSION"
```

Run `scripts/bootstrap_parser_v2_locked_evaluation.py` only as the custodian
from the execution VNet. It accepts the complete runtime, implementation, and
image-binding files plus their hashes, not caller-supplied launcher hashes.
Initial mode persists or authenticates the canonical construction chain, global
authorization lock, implementation/runtime records, authorization manifest, and
`UNSEAL_AUTHORIZED`. Authentication-only mode performs no writes and
re-downloads the complete persisted graph immediately before launch/private
read. This mode also re-downloads every prediction/score payload member
against its frozen SHA-256, size, and ETag and checks all four
authorization-scoped Blob leaves even before predictions exist. Stage P/E
authenticate the embedded persisted image binding through the runtime and
authorization records; they do not need the local build-record path.

Stage P authenticates the real global authorization lock, implementation/config
objects, and complete frozen `DRAFT_PROTOCOL` through `UNSEAL_AUTHORIZED`
receipt graph before it can persist `INPUTS_READ`. It reads only the exact
overall manifest, preregistered locked-input reservation, locked-input manifest,
and payload from the source release. The reservation nonce is compared by exact typed equality. Its SHA-256 plus the
reservation path/hash/ETag and leaf-manifest identity are carried through
authorization, request, seal, and prediction-manifest artifacts. It lists exact
registered-parent names/metadata before exposure and around manifest-last
prediction persistence, but never downloads locked-label payload bytes.
Post-input parser/schema/content failure writes a redacted spent-incomplete
record and permanently prevents parser rerun without pretending the holdout is
retired. Exact persisted predictions or closure bytes can be crash-adopted by
writing only their missing state receipt.

Parser-v2 itself is never imported into Stage P. Each exact three-field request
crosses a one-request `python -I -S` worker process with an allowlisted empty
environment, frozen source/version checks, canonical JSON framing, and redacted
failure output. The parent retains only a slotless callable facade; the legacy
numeric parser remains the separately extracted constrained callable.

Stage E is parser-free by procedure, not a hostile-code security boundary: the
same immutable image contains the parsers to satisfy the same-digest rule. Its
separate entry point blocks normal imports and supported path/alias loading of
both parser files, then scores only sealed JSON with the frozen gate JSON.
Public Markdown contains aggregate counts only; case-level failures remain in
the private Blob score prefix.

If bootstrap authenticates a labels-open transaction but cannot authenticate
one complete sealed score graph, the launcher derives an
`invalid_closure`-only Stage E job. That job is bound to the original scorer
retry/execution, receives no accepted score-manifest hash, never downloads the
label payload, never invokes a parser or scorer, and may write only the
deterministic `LABELS_READ` receipt (if absent), redacted incomplete-scoring
evidence, `INVALID` closure manifest, and `CLOSED` receipt. A complete but
tampered score set follows this same non-accepting closure path.

The launcher explicitly follows ARM `nextLink` pages. Its private-network
preflight ties the named endpoint and approved `blob` connection to the exact
storage resource, VNet/subnets, endpoint NICs, Blob private DNS zone/group/link
and A record, and requires DNS answers to equal only the endpoint NIC IP set.
It also requires `allowBlobPublicAccess=false` on the account and authenticates
the exact bound Blob container ARM resource with absent/null `publicAccess`.
Those required values are fixed in the hashed runtime destination as
`allow_blob_public_access=false` and `container_public_access=null`.
At startup it atomically snapshots runtime, implementation, and image-binding
bytes under the private Git directory, materializes every registered helper from
its verified Git blob, and re-executes the snapshotted launcher. Later worktree
changes cannot replace launcher helpers; the build helper uses the same
verified-snapshot rule. All four shell entrypoints use Bash protected mode;
both helpers self-reexec with `env -i` and
`bash --noprofile --norc -p`; stage entrypoints scrub shell/Python injection
variables and execute the pinned absolute interpreter with `-I`. A missing or
changed snapshot aborts.
The protected ACA projection includes identity, registry, digest, exact
command/args/environment, resources, scale/retry/timeout, secrets, volumes,
mounts, init containers, sidecars, probes, lifecycle, and security context.
Forbidden optional surfaces must be empty.

Recovery authenticates both the launch and its deterministically derived
dispatch TXT record before inspecting executions of the uniquely named,
ready, immutable Job. GET can authenticate a record but cannot reconstruct
either ephemeral create capability. An ambiguous or missing Job PUT is
permanently stranded. An absent dispatch record cannot authorize recovery
adoption. An ambiguous ACA start is never retried; recovery only lists/GETs
executions and may adopt exactly one candidate whose removal restores the
launch-bound baseline membership. Recovery contains no Job PUT or start path.
The Job body and protected projection are never patched after their launch
claim. Every coordination and execution-baseline read clears prior evidence
before the request and explicitly propagates failure. This deliberate liveness
sacrifice is required because ACA Jobs 2024-03-01 documents neither conditional
Job PUT/PATCH nor an idempotency contract for start.

## Intended order

```bash
bash scripts/00_check_prereqs.sh
bash scripts/01_build_and_push_image.sh
bash scripts/02_run_phase0_5.sh
bash scripts/03_run_phase1.sh
bash scripts/04_run_phase1_pilot.sh
```

Run `04_run_phase1_pilot.sh` only after readiness, provider registration, GPU quota, image build, Phase 0.5 Azure check, and Phase 1 Azure dry-run pass.

## Cost management

- Use manual Container Apps Jobs, not always-on services.
- Keep workload profile min nodes at zero where possible.
- Start with the small Phase 1 pilot before full experiments.
- Stop and record blockers if GPU quota is missing.

## Logs and status

Check job executions:

```bash
az containerapp job execution list -g <resource-group> -n <job-name> -o table
```

Every Azure command and job must be logged in `docs/run_log.md`.
