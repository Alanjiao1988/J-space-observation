#!/usr/bin/env bash
# Script: 15_p12h_r1_create_identity.sh
# Purpose: Create the Phase 1.2H-R1 least-privilege access identity and grant it
#          exactly two roles: AcrPull on the registry, and Storage Blob Data
#          Reader scoped to the single blob container that holds the sealed
#          parser-v3-v1 source.
#
# Why a new identity at all. The existing id-jspace-aca-acrpull-sea holds
# Storage Blob Data Contributor at the storage ACCOUNT scope, which is
# write- and delete-capable over every container in the account. Reusing it
# would make "read-only" an operator promise rather than a property of the
# authorization model. This round's whole point is that the second kind of
# claim is the only kind worth making, so the round creates its own identity
# and grants it strictly less.
#
# This script is control-plane only. It reads no blob, streams no object and
# touches no sealed content.

set -euo pipefail

SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-943bacdf-8b6e-4e3a-8126-a149f623d32e}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
LOCATION="${LOCATION:-southeastasia}"
IDENTITY_NAME="${IDENTITY_NAME:-id-jspace-p12h-r1-read-sea}"
ACR_NAME="${ACR_NAME:-acrjspaceobservationsea}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-stjspacefiles0709085305}"
BLOB_CONTAINER="${BLOB_CONTAINER:-jspace-files}"

# Built-in role definition IDs. Pinned by ID rather than by display name so a
# renamed or shadowed custom role cannot be substituted silently.
ROLE_ACRPULL="7f951dda-4ed3-4680-a7ca-43fe172d538d"
ROLE_BLOB_DATA_READER="2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"

log() { printf '[15_p12h_r1_create_identity] %s\n' "$*"; }
fail() { printf '[15_p12h_r1_create_identity] ERROR: %s\n' "$*" >&2; exit 1; }

command -v az >/dev/null 2>&1 || fail "az CLI not found"

log "subscription: ${SUBSCRIPTION_ID}"
az account set --subscription "${SUBSCRIPTION_ID}"

# --- 1. Create (or adopt) the identity -------------------------------------

if az identity show --name "${IDENTITY_NAME}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    log "identity ${IDENTITY_NAME} already exists; adopting"
else
    log "creating identity ${IDENTITY_NAME}"
    az identity create \
        --name "${IDENTITY_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --output none
fi

PRINCIPAL_ID="$(az identity show --name "${IDENTITY_NAME}" --resource-group "${RESOURCE_GROUP}" --query principalId --output tsv)"
CLIENT_ID="$(az identity show --name "${IDENTITY_NAME}" --resource-group "${RESOURCE_GROUP}" --query clientId --output tsv)"
IDENTITY_ID="$(az identity show --name "${IDENTITY_NAME}" --resource-group "${RESOURCE_GROUP}" --query id --output tsv)"

[[ -n "${PRINCIPAL_ID}" ]] || fail "could not resolve principalId"
log "principalId: ${PRINCIPAL_ID}"
log "clientId:    ${CLIENT_ID}"

# --- 2. Scopes --------------------------------------------------------------

ACR_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ContainerRegistry/registries/${ACR_NAME}"

# Container scope, not account scope. This is the whole point of the script:
# the data role cannot reach any other container in the account, and cannot
# write, delete, lease or re-tier anything in this one.
CONTAINER_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}/blobServices/default/containers/${BLOB_CONTAINER}"

log "ACR scope:       ${ACR_SCOPE}"
log "container scope: ${CONTAINER_SCOPE}"

# --- 3. Assign exactly two roles -------------------------------------------

assign_role() {
    local role_id="$1" scope="$2" label="$3"
    if az role assignment list --assignee "${PRINCIPAL_ID}" --scope "${scope}" \
        --query "[?roleDefinitionId.ends_with(@, '${role_id}')] | length(@)" --output tsv 2>/dev/null | grep -q '^[1-9]'; then
        log "${label} already assigned at this scope"
        return 0
    fi
    log "assigning ${label}"
    az role assignment create \
        --assignee-object-id "${PRINCIPAL_ID}" \
        --assignee-principal-type ServicePrincipal \
        --role "${role_id}" \
        --scope "${scope}" \
        --output none
}

assign_role "${ROLE_ACRPULL}" "${ACR_SCOPE}" "AcrPull @ registry"
assign_role "${ROLE_BLOB_DATA_READER}" "${CONTAINER_SCOPE}" "Storage Blob Data Reader @ container"

# --- 4. Prove the identity holds nothing else -------------------------------

log "enumerating every role assignment held by this principal"
ASSIGNMENTS="$(az role assignment list --assignee "${PRINCIPAL_ID}" --all \
    --query "[].{role:roleDefinitionName, scope:scope}" --output json)"
printf '%s\n' "${ASSIGNMENTS}"

COUNT="$(printf '%s' "${ASSIGNMENTS}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
if [[ "${COUNT}" != "2" ]]; then
    fail "expected exactly 2 role assignments, found ${COUNT}. Refusing to proceed: an identity with more authority than the freeze describes cannot be used to make a least-privilege claim."
fi

WRITE_CAPABLE="$(printf '%s' "${ASSIGNMENTS}" | python3 -c '
import json, sys
bad = [a for a in json.load(sys.stdin)
       if a["role"] not in {"AcrPull", "Storage Blob Data Reader"}]
print(json.dumps(bad))')"
if [[ "${WRITE_CAPABLE}" != "[]" ]]; then
    fail "identity holds a role outside the frozen allowlist: ${WRITE_CAPABLE}"
fi

log "verified: exactly AcrPull and Storage Blob Data Reader, nothing else"

# --- 5. Emit the values the job needs --------------------------------------

cat <<EOF

Phase 1.2H-R1 access identity ready.

  IDENTITY_NAME = ${IDENTITY_NAME}
  IDENTITY_ID   = ${IDENTITY_ID}
  CLIENT_ID     = ${CLIENT_ID}
  PRINCIPAL_ID  = ${PRINCIPAL_ID}

Role assignments propagate asynchronously. Wait for propagation before
starting the access job; a premature run fails closed with an authorization
error rather than reading anything, but the wasted run still consumes an
execution ordinal.

EOF
