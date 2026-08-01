#!/usr/bin/env bash
# Script: 17_p12h_r1_run_access_gate.sh
# Purpose: Create and start the Phase 1.2H-R1 in-VNet access gate as a manual
#          Azure Container Apps job, then retrieve the content-free receipt.
#
# The job runs inside cae-jspace-observation-sea-vnet2, which is VNet-injected
# into the same VNet as the storage private endpoint. That is what makes the
# read possible at all: the storage account has publicNetworkAccess=Disabled,
# so a run from anywhere else fails to connect rather than reading anything.
#
# Deliberate properties:
#   * image pinned by digest, never by tag;
#   * user-assigned managed identity only -- no secrets, no registry password,
#     no connection string, no SAS;
#   * replicaRetryLimit 0, so a failed gate is one observation rather than a
#     silent retry that could produce several unlogged reads;
#   * no ingress;
#   * CPU only.
#
# What this script does NOT do: it does not decode, persist, print or export
# any object content, and it does not perform or enable any semantic review.

set -euo pipefail

SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-943bacdf-8b6e-4e3a-8126-a149f623d32e}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
LOCATION="${LOCATION:-southeastasia}"
CONTAINER_APP_ENV="${CONTAINER_APP_ENV:-cae-jspace-observation-sea-vnet2}"
WORKLOAD_PROFILE_NAME="${WORKLOAD_PROFILE_NAME:-Consumption}"
JOB_NAME="${JOB_NAME:-job-jspace-p12h-r1-access-gate}"
IDENTITY_NAME="${IDENTITY_NAME:-id-jspace-p12h-r1-read-sea}"
ACR_NAME="${ACR_NAME:-acrjspaceobssea0708231738}"
IMAGE_DIGEST="${IMAGE_DIGEST:-}"
IMAGE_REPO="${IMAGE_REPO:-j-space-observation}"
FREEZE_COMMIT="${FREEZE_COMMIT:-}"
EXECUTION_ID="${EXECUTION_ID:-}"
CPU_CORES="${CPU_CORES:-2}"
MEMORY="${MEMORY:-4Gi}"
REPLICA_TIMEOUT="${REPLICA_TIMEOUT:-1800}"

log() { printf '[17_p12h_r1_run_access_gate] %s\n' "$*"; }
fail() { printf '[17_p12h_r1_run_access_gate] ERROR: %s\n' "$*" >&2; exit 1; }

command -v az >/dev/null 2>&1 || fail "az CLI not found"
[[ -n "${IMAGE_DIGEST}" ]] || fail "IMAGE_DIGEST is required (sha256:...). Deploying by tag is refused."
[[ "${IMAGE_DIGEST}" == sha256:* ]] || fail "IMAGE_DIGEST must be a sha256: digest, not a tag"
[[ -n "${FREEZE_COMMIT}" ]] || fail "FREEZE_COMMIT is required"
[[ "${#FREEZE_COMMIT}" -eq 40 ]] || fail "FREEZE_COMMIT must be the full 40-character SHA"
[[ -n "${EXECUTION_ID}" ]] || fail "EXECUTION_ID is required so the receipt is traceable"

az account set --subscription "${SUBSCRIPTION_ID}"

# --- 1. Verify the freeze commit is actually published ---------------------
# A gate that runs from an unpublished commit produces evidence nobody else can
# reconstruct.

log "verifying the freeze commit exists on the public remote"
if command -v git >/dev/null 2>&1; then
    git ls-remote https://github.com/Alanjiao1988/J-space-observation.git \
        | grep -q "^${FREEZE_COMMIT}" \
        || fail "freeze commit ${FREEZE_COMMIT} is not present on the public remote. Publish it before running the gate."
    log "freeze commit is published"
fi

# --- 2. Resolve identity and registry --------------------------------------

IDENTITY_ID="$(az identity show --name "${IDENTITY_NAME}" --resource-group "${RESOURCE_GROUP}" --query id --output tsv)"
CLIENT_ID="$(az identity show --name "${IDENTITY_NAME}" --resource-group "${RESOURCE_GROUP}" --query clientId --output tsv)"
LOGIN_SERVER="$(az acr show --name "${ACR_NAME}" --query loginServer --output tsv)"
ENV_ID="$(az containerapp env show --name "${CONTAINER_APP_ENV}" --resource-group "${RESOURCE_GROUP}" --query id --output tsv)"

[[ -n "${IDENTITY_ID}" ]] || fail "identity ${IDENTITY_NAME} not found; run 15_p12h_r1_create_identity.sh first"
[[ -n "${ENV_ID}" ]] || fail "environment ${CONTAINER_APP_ENV} not found"

PINNED_IMAGE="${LOGIN_SERVER}/${IMAGE_REPO}@${IMAGE_DIGEST}"

log "environment: ${CONTAINER_APP_ENV}"
log "identity:    ${IDENTITY_NAME} (${CLIENT_ID})"
log "image:       ${PINNED_IMAGE}"

# --- 3. Confirm the storage account is still private ------------------------
# Cheap, and it converts "we believe the endpoint is private" into a checked
# precondition at the moment of the run rather than at the moment of design.

PNA="$(az storage account show --name stjspacefiles0709085305 --resource-group "${RESOURCE_GROUP}" --query publicNetworkAccess --output tsv)"
[[ "${PNA}" == "Disabled" ]] || fail "storage publicNetworkAccess is ${PNA}, expected Disabled. Refusing to run."
log "storage publicNetworkAccess: Disabled"

# --- 4. Build the job definition -------------------------------------------

BODY_FILE="$(mktemp)"
trap 'rm -f "${BODY_FILE}"' EXIT

# Every value below is validated before it can reach the ARM body. The first
# frozen version of this script used an UNQUOTED heredoc, so the shell expanded
# ${EXECUTION_ID}, ${CPU_CORES}, ${MEMORY} and ${REPLICA_TIMEOUT} directly into
# Python source: a value containing a quote or a newline would have rewritten
# the job definition, including its identity and image. Independent Audit A
# raised this as A-07. The heredoc is now quoted, so Python is a fixed program,
# and every value crosses the boundary through the environment where it is a
# string and nothing else.
validate() {
    local name="$1" value="$2" pattern="$3"
    [[ "${value}" =~ ${pattern} ]] || fail "${name} is not of the required shape; refusing to build a job definition from it"
}

validate IDENTITY_ID "${IDENTITY_ID}" '^/subscriptions/[0-9a-fA-F-]+/resourceGroups/[A-Za-z0-9._()-]+/providers/Microsoft\.ManagedIdentity/userAssignedIdentities/[A-Za-z0-9-]+$'
validate ENV_ID "${ENV_ID}" '^/subscriptions/[0-9a-fA-F-]+/resourceGroups/[A-Za-z0-9._()-]+/providers/Microsoft\.App/managedEnvironments/[A-Za-z0-9-]+$'
validate CLIENT_ID "${CLIENT_ID}" '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
validate EXECUTION_ID "${EXECUTION_ID}" '^[A-Za-z0-9._-]{1,200}$'
validate FREEZE_COMMIT "${FREEZE_COMMIT}" '^[0-9a-f]{7,40}$'
validate IMAGE_DIGEST "${IMAGE_DIGEST}" '^sha256:[0-9a-f]{64}$'
validate PINNED_IMAGE "${PINNED_IMAGE}" '^[A-Za-z0-9./_-]+@sha256:[0-9a-f]{64}$'
validate LOGIN_SERVER "${LOGIN_SERVER}" '^[A-Za-z0-9.-]+$'
validate WORKLOAD_PROFILE_NAME "${WORKLOAD_PROFILE_NAME}" '^[A-Za-z0-9-]+$'
validate REPLICA_TIMEOUT "${REPLICA_TIMEOUT}" '^[0-9]{1,5}$'
validate CPU_CORES "${CPU_CORES}" '^[0-9]+(\.[0-9]+)?$'
validate MEMORY "${MEMORY}" '^[0-9]+(\.[0-9]+)?Gi$'
validate LOCATION "${LOCATION:-southeastasia}" '^[a-z0-9]+$'

export IDENTITY_ID ENV_ID CLIENT_ID EXECUTION_ID FREEZE_COMMIT IMAGE_DIGEST
export PINNED_IMAGE LOGIN_SERVER WORKLOAD_PROFILE_NAME REPLICA_TIMEOUT CPU_CORES MEMORY

python3 - <<'PYEOF' > "${BODY_FILE}"
import json, os

env = os.environ
identity_id = env["IDENTITY_ID"]
client_id = env["CLIENT_ID"]

body = {
    "location": env.get("LOCATION", "southeastasia"),
    "identity": {
        "type": "UserAssigned",
        "userAssignedIdentities": {identity_id: {}},
    },
    "properties": {
        "environmentId": env["ENV_ID"],
        "workloadProfileName": env["WORKLOAD_PROFILE_NAME"],
        "configuration": {
            "triggerType": "Manual",
            "replicaTimeout": int(env["REPLICA_TIMEOUT"]),
            # No retry. A failed access gate is one observation, not an
            # unknown number of silent re-reads.
            "replicaRetryLimit": 0,
            "manualTriggerConfig": {"parallelism": 1, "replicaCompletionCount": 1},
            "registries": [
                {"server": env["LOGIN_SERVER"], "identity": identity_id}
            ],
            # No secrets block at all.
        },
        "template": {
            "containers": [
                {
                    "name": "access-gate",
                    "image": env["PINNED_IMAGE"],
                    "resources": {
                        "cpu": float(env["CPU_CORES"]),
                        "memory": env["MEMORY"],
                    },
                    "args": [
                        "--client-id", client_id,
                        "--execution-id", env["EXECUTION_ID"],
                        "--freeze-commit", env["FREEZE_COMMIT"],
                        "--image-digest", env["IMAGE_DIGEST"],
                    ],
                    "env": [
                        # Only the identity hint the SDK needs. No endpoint
                        # override, no account name, no container name: those
                        # come from the frozen decision record baked into the
                        # image and cannot be redirected from here.
                        {"name": "AZURE_CLIENT_ID", "value": client_id},
                    ],
                }
            ],
            "volumes": [],
        },
    },
}
print(json.dumps(body, indent=2))
PYEOF

log "job definition:"
cat "${BODY_FILE}"

# --- 5. Create or replace the job ------------------------------------------

JOB_URI="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/jobs/${JOB_NAME}?api-version=2024-03-01"

log "creating job ${JOB_NAME}"
az rest --method put --uri "${JOB_URI}" --body "@${BODY_FILE}" --output none

log "waiting for the job resource to reach a terminal provisioning state"
PROVISIONED="no"
for _ in $(seq 1 60); do
    STATE="$(az rest --method get --uri "${JOB_URI}" --query properties.provisioningState --output tsv 2>/dev/null || true)"
    log "provisioningState: ${STATE:-unknown}"
    case "${STATE}" in
        Succeeded) PROVISIONED="yes"; break ;;
        Failed|Canceled) fail "job provisioning ${STATE}" ;;
    esac
    sleep 10
done
# The first frozen version fell out of this loop on timeout and started the job
# anyway, against whatever definition happened to be live. Independent Audit A
# raised this as A-14.
[[ "${PROVISIONED}" == "yes" ]] || fail "job provisioning did not reach a terminal state within ~600s; refusing to start an execution against an unconfirmed definition"

# --- 6. Start exactly one execution ----------------------------------------

log "starting the access gate"
START_OUTPUT="$(az containerapp job start --name "${JOB_NAME}" --resource-group "${RESOURCE_GROUP}" --output json)"
EXECUTION_NAME="$(printf '%s' "${START_OUTPUT}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name",""))')"

log "execution: ${EXECUTION_NAME}"

cat <<EOF

Access gate started.

  JOB_NAME       = ${JOB_NAME}
  EXECUTION_NAME = ${EXECUTION_NAME}
  EXECUTION_ID   = ${EXECUTION_ID}
  IMAGE_DIGEST   = ${IMAGE_DIGEST}
  FREEZE_COMMIT  = ${FREEZE_COMMIT}

Retrieve the receipt with:

  az containerapp job execution show \\
    --name ${JOB_NAME} --resource-group ${RESOURCE_GROUP} \\
    --job-execution-name ${EXECUTION_NAME}

  az containerapp logs show --name ${JOB_NAME} --resource-group ${RESOURCE_GROUP} \\
    --container access-gate --type console --follow false

The console output is the receipt. It is content-free by construction: the
receipt schema has no field that could carry a member name, an offset, a span
or object text, and the probe never decodes a byte it streams.

EOF
