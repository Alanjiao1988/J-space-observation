/*
  Workspace, diagnostic settings, and the resource-group delete lock.

  The logs collected here are deliberately the ones that carry no case content:
  firewall rule hits, registry login events, and storage transaction metadata.
  Reviewer text, model output, and label values never appear in them. A log
  that quietly accumulated the material under review would be an egress channel
  wearing an observability badge.

  The workspace is reachable only from inside the network. Public audit finding
  B-05 observed that it was previously open for both ingestion and query, which
  meant the one store holding every access event -- the evidence that the
  boundary held -- could be read from the internet by anyone who obtained a
  control-plane token. An Azure Monitor Private Link Scope carries the
  ingestion and query paths across the same private network as everything else.
*/

param location string
param namePrefix string
param tags object
param firewallName string
param firewallPolicyName string
param runtimeRegistryName string
param privateEndpointSubnetId string
param privateDnsZoneIds object
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
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
}

resource monitorScope 'Microsoft.Insights/privateLinkScopes@2021-07-01-preview' = {
  name: '${namePrefix}-ampls'
  location: 'global'
  tags: tags
  properties: {
    accessModeSettings: {
      // Private-only in both directions. 'Open' would let a resource outside
      // the scope keep using the public path, which is the same hole under a
      // different name.
      ingestionAccessMode: 'PrivateOnly'
      queryAccessMode: 'PrivateOnly'
      exclusions: []
    }
  }
}

resource monitorScopedWorkspace 'Microsoft.Insights/privateLinkScopes/scopedResources@2021-07-01-preview' = {
  parent: monitorScope
  name: '${namePrefix}-law-scoped'
  properties: {
    linkedResourceId: workspace.id
  }
}

resource monitorPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: '${namePrefix}-pe-monitor'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'monitor'
        properties: {
          privateLinkServiceId: monitorScope.id
          groupIds: [
            'azuremonitor'
          ]
        }
      }
    ]
  }
}

resource monitorPrivateDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: monitorPrivateEndpoint
  name: 'monitor-dns'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'monitor'
        properties: {
          privateDnsZoneId: privateDnsZoneIds.monitor
        }
      }
      {
        name: 'oms'
        properties: {
          privateDnsZoneId: privateDnsZoneIds.oms
        }
      }
      {
        name: 'ods'
        properties: {
          privateDnsZoneId: privateDnsZoneIds.ods
        }
      }
      {
        name: 'agentsvc'
        properties: {
          privateDnsZoneId: privateDnsZoneIds.agentsvc
        }
      }
      {
        name: 'blob'
        properties: {
          privateDnsZoneId: privateDnsZoneIds.blob
        }
      }
    ]
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
output monitorScopeId string = monitorScope.id
