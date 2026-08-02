/*
  Containers and least-privilege data-plane RBAC on the existing private
  storage account. Deployed into the storage account's own resource group,
  because a role assignment must be created where its scope lives.

  Two properties matter more than the rest.

  A role reads only the containers its lane names, and writes only its own.
  That is not a comment: the assignments below are generated from the same
  role matrix the entrypoints resolve their lanes from, so a lane that was
  widened in code widens here too and a test comparing the two notices.

  The write assignment uses a custom definition without a delete action. Azure
  RBAC cannot express "create but do not overwrite" -- that is enforced by the
  create-only plan check in the lifecycle and by conditional writes -- but it
  can express "cannot delete", and removing the capability outright is worth
  more than a rule that says not to use it.
*/

param privateStorageAccountName string
param roleMatrix object
param identityPrincipals array
param appendOnlyRoleDefinitionId string

var storageBlobDataReaderId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
)

var writeContainers = map(roleMatrix.roles, role => role.container)
var readContainers = flatten(map(roleMatrix.roles, role => role.read_containers))
var allContainers = union(writeContainers, readContainers)

var readAssignments = flatten(map(
  roleMatrix.roles,
  role => map(role.read_containers, containerName => {
    role: role.role
    containerName: containerName
  })
))

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: privateStorageAccountName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  parent: storageAccount
  name: 'default'
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [
  for containerName in allContainers: {
    parent: blobService
    name: containerName
    properties: {
      publicAccess: 'None'
    }
  }
]

resource readGrants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for assignment in readAssignments: {
    name: guid(
      storageAccount.id,
      assignment.containerName,
      assignment.role,
      'StorageBlobDataReader'
    )
    scope: containers[indexOf(allContainers, assignment.containerName)]
    properties: {
      roleDefinitionId: storageBlobDataReaderId
      principalId: filter(identityPrincipals, item => item.role == assignment.role)[0].principalId
      principalType: 'ServicePrincipal'
    }
  }
]

resource writeGrants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for role in roleMatrix.roles: {
    name: guid(storageAccount.id, role.container, role.role, 'AppendOnlyWriter')
    scope: containers[indexOf(allContainers, role.container)]
    properties: {
      roleDefinitionId: appendOnlyRoleDefinitionId
      principalId: filter(identityPrincipals, item => item.role == role.role)[0].principalId
      principalType: 'ServicePrincipal'
    }
  }
]

output createdContainers array = allContainers
output readGrantCount int = length(readAssignments)
output writeGrantCount int = length(roleMatrix.roles)
