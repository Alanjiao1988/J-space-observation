/*
  The private review boundary for the parser-v3-v2 evaluation.

  Deployed at subscription scope because two of its guarantees cannot be
  expressed inside a single resource group: the custom no-delete blob role is a
  subscription-level definition, and the data-plane grants land in the resource
  group that already holds the private storage account rather than in the new
  boundary group.

  Nothing in this file is typed twice. The subnet prefixes come from
  address_plan.json, which records how they were derived from live inventory;
  the role names, container names, prefixes, schema ids and container commands
  come from role_matrix.json, which is generated from the entrypoint registry in
  code. Both are loaded with loadJsonContent, so a change in either is a change
  here, and the accompanying test refuses if role_matrix.json has drifted from
  what the code exports.

  What this template does not do is decide whether the boundary is allowed to
  exist on top of an overlapping address space. It computes the overlap and
  hands the count to a module whose parameter accepts only zero, so a colliding
  plan fails before the first resource is created.
*/

targetScope = 'subscription'

@description('Region. Defaults to the region recorded in the address plan, which is where the private storage account already lives.')
param location string = ''

@description('Short prefix for every resource created by this template.')
@minLength(3)
@maxLength(24)
param namePrefix string = 'jspace-v2-boundary'

@description('Immutable image digest per role, keyed by role name. No default: a deployment without real digests must not be possible.')
param roleImageDigests object

@description('Resource group holding the existing private storage account.')
param privateStorageResourceGroup string = 'rg-jspace-observation-sea'

param deploymentStamp string = utcNow('yyyyMMddHHmmss')

var addressPlan = loadJsonContent('address_plan.json')
var roleMatrix = loadJsonContent('role_matrix.json')

var effectiveLocation = empty(location) ? addressPlan.region : location

var tags = {
  jspacePurpose: 'parser-v3-v2-private-review-boundary'
  jspacePhase: 'B'
  jspaceAddressPlan: addressPlan.schema_version
  jspaceRoleMatrix: roleMatrix.schema_version
}

var subnetPrefixes = toObject(addressPlan.subnets, subnet => subnet.name, subnet => subnet.prefix)

/*
  Resource names are derived from the endpoint allowlist the code enforces,
  not chosen here. If the registry were named anything else, a role would
  resolve an endpoint outside its closed set and refuse to start; deriving the
  name from the same string removes the opportunity for that to be discovered
  at runtime instead of at deployment.
*/
var acrEndpoint = filter(roleMatrix.registered_endpoints, endpoint => endsWith(endpoint, '.privatelink.azurecr.io'))[0]
var runtimeRegistryName = split(acrEndpoint, '.')[0]

var blobEndpoint = filter(
  roleMatrix.registered_endpoints,
  endpoint => endsWith(endpoint, '.privatelink.blob.${environment().suffixes.storage}')
)[0]
var privateStorageAccountName = split(blobEndpoint, '.')[0]

/*
  Overlap arithmetic.

  Every allocation in this subscription sits inside 10.0.0.0/8, so an overlap
  with the boundary /16 is exactly the case where the first octets match and
  the boundary's second octet falls inside the span the observed prefix covers.
  The span table is written out rather than computed because Bicep has no
  exponentiation; it covers /8 through /16, and anything longer than /16 spans a
  single second octet. A prefix shorter than /8 cannot occur inside 10/8 and is
  therefore not represented -- that limit is stated here rather than left for a
  reader to infer from the table.
*/
var octetSpan = {
  '8': 256
  '9': 128
  '10': 64
  '11': 32
  '12': 16
  '13': 8
  '14': 4
  '15': 2
  '16': 1
}

var boundaryPrefix = addressPlan.boundary_vnet_prefix
var boundaryFirstOctet = int(split(split(boundaryPrefix, '/')[0], '.')[0])
var boundarySecondOctet = int(split(split(boundaryPrefix, '/')[0], '.')[1])

var observedPrefixes = flatten(map(addressPlan.observed_vnets, vnet => vnet.address_prefixes))

/*
  Bicep lambda bodies must be written on a single line, so the arithmetic is
  split in two: a map that decomposes each observed prefix into an object, and
  a one-line predicate over those objects. The decomposition is the readable
  half and the predicate is the load-bearing half.
*/
var observedSpans = map(observedPrefixes, prefix => {
  prefix: prefix
  firstOctet: int(split(split(prefix, '/')[0], '.')[0])
  lowSecondOctet: int(split(split(prefix, '/')[0], '.')[1])
  secondOctetSpan: octetSpan[?split(prefix, '/')[1]] ?? 1
})

var conflictingSpans = filter(observedSpans, entry => entry.firstOctet == boundaryFirstOctet && boundarySecondOctet >= entry.lowSecondOctet && boundarySecondOctet < (entry.lowSecondOctet + entry.secondOctetSpan))

var conflictingPrefixes = map(conflictingSpans, entry => entry.prefix)

module addressPlanGate 'modules/assert_no_overlap.bicep' = {
  name: 'assert-no-overlap-${deploymentStamp}'
  params: {
    conflictingPrefixCount: any(length(conflictingPrefixes))
  }
}

resource boundaryResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${namePrefix}'
  location: effectiveLocation
  tags: tags
}

/*
  Azure RBAC has no "create but never overwrite" data action, so create-only
  remains enforced by the lifecycle's create-only plan check and by conditional
  writes. What RBAC can do is remove deletion entirely, and a capability that
  does not exist cannot be misused. The definition below grants read, write and
  add on blobs and nothing else -- in particular no delete, no container
  management, and no control-plane action of any kind.
*/
resource appendOnlyBlobRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(subscription().id, 'jspace-parser-v3-v2-blob-no-delete')
  properties: {
    roleName: 'J-space parser-v3-v2 blob writer (no delete)'
    description: 'Read, write and add blob data. Deliberately omits every delete action so evidence cannot be removed by the identity that produced it.'
    type: 'CustomRole'
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: [
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'
        ]
        notDataActions: []
      }
    ]
    assignableScopes: [
      subscription().id
    ]
  }
}

module network 'modules/network.bicep' = {
  name: 'network-${deploymentStamp}'
  scope: boundaryResourceGroup
  params: {
    location: effectiveLocation
    namePrefix: namePrefix
    tags: tags
    vnetAddressPrefix: addressPlan.boundary_vnet_prefix
    firewallSubnetPrefix: subnetPrefixes.AzureFirewallSubnet
    firewallManagementSubnetPrefix: subnetPrefixes.AzureFirewallManagementSubnet
    workloadSubnetPrefix: subnetPrefixes['snet-aca-boundary']
    privateEndpointSubnetPrefix: subnetPrefixes['snet-pe-boundary']
  }
  dependsOn: [
    addressPlanGate
  ]
}

module privateLink 'modules/privatelink.bicep' = {
  name: 'privatelink-${deploymentStamp}'
  scope: boundaryResourceGroup
  params: {
    location: effectiveLocation
    namePrefix: namePrefix
    tags: tags
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    vnetId: network.outputs.vnetId
    privateStorageAccountName: privateStorageAccountName
    privateStorageResourceGroup: privateStorageResourceGroup
    runtimeRegistryName: runtimeRegistryName
  }
}

module observability 'modules/observability.bicep' = {
  name: 'observability-${deploymentStamp}'
  scope: boundaryResourceGroup
  params: {
    location: effectiveLocation
    namePrefix: namePrefix
    tags: tags
    firewallName: '${namePrefix}-fw'
    firewallPolicyName: '${namePrefix}-fwpolicy'
    runtimeRegistryName: privateLink.outputs.runtimeRegistryName
  }
}

module workload 'modules/workload.bicep' = {
  name: 'workload-${deploymentStamp}'
  scope: boundaryResourceGroup
  params: {
    location: effectiveLocation
    namePrefix: namePrefix
    tags: tags
    environmentSubnetId: network.outputs.workloadSubnetId
    runtimeRegistryLoginServer: privateLink.outputs.runtimeRegistryLoginServer
    runtimeRegistryId: privateLink.outputs.runtimeRegistryId
    logAnalyticsWorkspaceId: observability.outputs.workspaceId
    logAnalyticsCustomerId: observability.outputs.workspaceCustomerId
    roleMatrix: roleMatrix
    gpuWorkloadProfileName: addressPlan.region_evidence.gpu_profile_found.name
    roleImageDigests: roleImageDigests
  }
}

module storageAccess 'modules/storage_access.bicep' = {
  name: 'storage-access-${deploymentStamp}'
  scope: resourceGroup(privateStorageResourceGroup)
  params: {
    privateStorageAccountName: privateStorageAccountName
    roleMatrix: roleMatrix
    identityPrincipals: workload.outputs.identityClientIds
    appendOnlyRoleDefinitionId: appendOnlyBlobRole.id
  }
}

/*
  Outputs are names, ids and counts. No output carries a container listing, a
  case identifier, a label, or anything else that would let the deployment
  record double as a copy of the material under review.
*/
output boundaryResourceGroupName string = boundaryResourceGroup.name
output region string = effectiveLocation
output vnetId string = network.outputs.vnetId
output firewallPrivateIp string = network.outputs.firewallPrivateIp
output runtimeRegistryLoginServer string = privateLink.outputs.runtimeRegistryLoginServer
output containerAppsEnvironmentId string = workload.outputs.environmentId
output jobNames array = workload.outputs.jobNames
output createdContainerCount int = length(storageAccess.outputs.createdContainers)
output readGrantCount int = storageAccess.outputs.readGrantCount
output writeGrantCount int = storageAccess.outputs.writeGrantCount
output addressPlanId string = addressPlan.schema_version
output roleMatrixSchemaVersion string = roleMatrix.schema_version
output roleCount int = length(roleMatrix.roles)
