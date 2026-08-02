/*
  Identities, the internal Container Apps environment, and one job per role.

  The container command is not written here. It is read from role_matrix.json,
  which is generated from the entrypoint registry in code, so the command the
  platform executes and the command the tests resolve are the same array. A
  command typed into this file would be correct only until someone renamed an
  entrypoint.

  Every job is a manual-trigger job rather than a long-running app. A role that
  is always running is a role that can be asked to do something twice; a job
  that must be launched explicitly leaves a launch record, and the second-launch
  refusal has something to refuse.
*/

param location string
param namePrefix string
param tags object
param environmentSubnetId string
param runtimeRegistryLoginServer string
param runtimeRegistryId string
param logAnalyticsWorkspaceId string
param logAnalyticsCustomerId string

@description('Generated from the entrypoint registry. Never hand-written.')
param roleMatrix object

@description('The T4 workload profile name discovered from live regional inventory.')
param gpuWorkloadProfileName string

@description('Immutable image digest per role. No default: a deployment without real digests must not be possible.')
param roleImageDigests object

@description('Roles that run on the GPU profile. Only the parser-bearing stage needs one.')
param gpuRoles array = [ 'stage_p' ]

resource identities 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = [
  for role in roleMatrix.roles: {
    name: role.uami_name
    location: location
    tags: union(tags, { jspaceRole: role.role })
  }
]

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for (role, index) in roleMatrix.roles: {
    name: guid(runtimeRegistryId, role.uami_name, 'AcrPull')
    scope: runtimeRegistryResource
    properties: {
      // AcrPull. Pull only: no role may push an image into the registry its
      // peers pull from, so a compromised role cannot become the supply chain.
      roleDefinitionId: subscriptionResourceId(
        'Microsoft.Authorization/roleDefinitions',
        '7f951dda-4ed3-4680-a7ca-43fe172d538d'
      )
      principalId: identities[index].properties.principalId
      principalType: 'ServicePrincipal'
    }
  }
]

resource runtimeRegistryResource 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: last(split(runtimeRegistryId, '/'))
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae'
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: environmentSubnetId
      // Internal: the environment gets no public ingress endpoint at all, so
      // there is no address for anything outside the VNet to reach.
      internal: true
    }
    zoneRedundant: false
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
      {
        name: 'gpu-t4'
        workloadProfileType: gpuWorkloadProfileName
      }
    ]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        // The shared key is supplied by the platform binding, not by an
        // application setting; no role container ever sees it.
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
  }
}

resource roleJobs 'Microsoft.App/jobs@2024-03-01' = [
  for (role, index) in roleMatrix.roles: {
    name: '${namePrefix}-job-${replace(role.role, '_', '-')}'
    location: location
    tags: union(tags, { jspaceRole: role.role })
    identity: {
      type: 'UserAssigned'
      userAssignedIdentities: {
        '${identities[index].id}': {}
      }
    }
    properties: {
      environmentId: environment.id
      workloadProfileName: contains(gpuRoles, role.role) ? 'gpu-t4' : 'Consumption'
      configuration: {
        triggerType: 'Manual'
        replicaTimeout: 3600
        replicaRetryLimit: 0
        manualTriggerConfig: {
          parallelism: 1
          replicaCompletionCount: 1
        }
        registries: [
          {
            server: runtimeRegistryLoginServer
            identity: identities[index].id
          }
        ]
        // No secrets block. A role that cannot hold a secret cannot leak one,
        // and every credential it legitimately needs is its managed identity.
        secrets: []
      }
      template: {
        containers: [
          {
            name: replace(role.role, '_', '-')
            // Digest, never a tag. A tag can be moved after the freeze binds it.
            image: '${runtimeRegistryLoginServer}/jspace-v2-${replace(role.role, '_', '-')}@${roleImageDigests[role.role]}'
            command: [ role.command[0] ]
            args: skip(role.command, 1)
            resources: {
              cpu: contains(gpuRoles, role.role) ? json('8.0') : json('1.0')
              memory: contains(gpuRoles, role.role) ? '56Gi' : '2Gi'
            }
            env: [
              { name: 'JSPACE_ROLE', value: role.role }
              { name: 'AZURE_CLIENT_ID', value: identities[index].properties.clientId }
              { name: 'JSPACE_CONTAINER', value: role.container }
              { name: 'JSPACE_PREFIX', value: role.prefix }
              { name: 'JSPACE_SCHEMA_IDS', value: join(role.schema_ids, ',') }
              { name: 'JSPACE_IMAGE_DIGEST', value: roleImageDigests[role.role] }
            ]
          }
        ]
      }
    }
  }
]

output environmentId string = environment.id
output identityClientIds array = [
  for (role, index) in roleMatrix.roles: {
    role: role.role
    clientId: identities[index].properties.clientId
    principalId: identities[index].properties.principalId
  }
]
output jobNames array = [for (role, index) in roleMatrix.roles: roleJobs[index].name]
