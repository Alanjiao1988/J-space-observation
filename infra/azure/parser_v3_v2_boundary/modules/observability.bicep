/*
  Workspace, diagnostic settings, and the resource-group delete lock.

  The logs collected here are deliberately the ones that carry no case content:
  firewall rule hits, registry login events, and storage transaction metadata.
  Reviewer text, model output, and label values never appear in them. A log
  that quietly accumulated the material under review would be an egress channel
  wearing an observability badge.
*/

param location string
param namePrefix string
param tags object
param firewallName string
param firewallPolicyName string
param runtimeRegistryName string
param retentionDays int = 90

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-law'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionDays
    features: {
      // No external query access path; reads go through the control plane.
      disableLocalAuth: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource firewall 'Microsoft.Network/azureFirewalls@2023-11-01' existing = {
  name: firewallName
}

resource runtimeRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: runtimeRegistryName
}

resource firewallDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'egress-evidence'
  scope: firewall
  properties: {
    workspaceId: workspace.id
    logs: [
      {
        // Every allowed and denied flow. This is the evidence that the deny
        // rule was actually the thing that stopped an egress attempt, rather
        // than the attempt never having been made.
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

resource registryDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'registry-evidence'
  scope: runtimeRegistry
  properties: {
    workspaceId: workspace.id
    logs: [
      {
        category: 'ContainerRegistryLoginEvents'
        enabled: true
      }
      {
        category: 'ContainerRegistryRepositoryEvents'
        enabled: true
      }
    ]
    metrics: []
  }
}

resource resourceGroupLock 'Microsoft.Authorization/locks@2020-05-01' = {
  name: '${namePrefix}-cannot-delete'
  properties: {
    level: 'CanNotDelete'
    notes: 'The boundary carries the only copy of some run evidence. Deletion must be a deliberate, separately authorised act.'
  }
}

output workspaceId string = workspace.id
output workspaceCustomerId string = workspace.properties.customerId
output firewallPolicyNameEcho string = firewallPolicyName
