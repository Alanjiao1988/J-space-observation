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

python3 - "$@" <<PYEOF > "${BODY_FILE}"
import json, os

body = {
    "location": os.environ.get("LOCATION", "southeastasia"),
    "identity": {
        "type": "UserAssigned",
        "userAssignedIdentities": {"${IDENTITY_ID}": {}},
    },
    "properties": {
        "environmentId": "${ENV_ID}",
        "workloadProfileName": "${WORKLOAD_PROFILE_NAME}",
        "configuration": {
            "triggerType": "Manual",
            "replicaTimeout": ${REPLICA_TIMEOUT},
            # No retry. A failed access gate is one observation, not an
            # unknown number of silent re-reads.
            "replicaRetryLimit": 0,
            "manualTriggerConfig": {"parallelism": 1, "replicaCompletionCount": 1},
            "registries": [
                {"server": "${LOGIN_SERVER}", "identity": "${IDENTITY_ID}"}
            ],
            # No secrets block at all.
        },
        "template": {
            "containers": [
                {
                    "name": "access-gate",
                    "image": "${PINNED_IMAGE}",
                    "resources": {"cpu": ${CPU_CORES}, "memory": "${MEMORY}"},
                    "args": [
                        "--client-id", "${CLIENT_ID}",
                        "--execution-id", "${EXECUTION_ID}",
                        "--freeze-commit", "${FREEZE_COMMIT}",
                        "--image-digest", "${IMAGE_DIGEST}",
                    ],
                    "env": [
                        # Only the identity hint the SDK needs. No endpoint
                        # override, no account name, no container name: those
                        # come from the frozen decision record baked into the
                        # image and cannot be redirected from here.
                        {"name": "AZURE_CLIENT_ID", "value": "${CLIENT_ID}"},
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
for _ in $(seq 1 60); do
    STATE="$(az rest --method get --uri "${JOB_URI}" --query properties.provisioningState --output tsv 2>/dev/null || true)"
    log "provisioningState: ${STATE:-unknown}"
    case "${STATE}" in
        Succeeded) break ;;
        Failed|Canceled) fail "job provisioning ${STATE}" ;;
    esac
    sleep 10
done

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
