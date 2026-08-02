/*
  Private-link surface for the boundary.

  Two facts drive everything here.

  The build registry and the runtime registry are different registries. The
  existing Basic registry is reachable from the public Internet because that is
  how public Phase A validation runs. A runtime registry that pulled images for
  private roles must not share that property, so this deploys a *new* Premium
  registry with public network access disabled and a private endpoint. Reusing
  the Basic one and "turning off public access later" would mean the private
  boundary depended on a setting that public work needs to be the other way.

  The private Blob account already exists and already has public network access
  disabled. What it does not have is a private endpoint inside this boundary, so
  that is what is added; the account itself is referenced, never recreated,
  because recreating it is indistinguishable from losing it.
*/

param location string
param namePrefix string
param tags object
param privateEndpointSubnetId string
param vnetId string

@description('Existing private Blob account holding the retired source. Referenced, never created.')
param privateStorageAccountName string
param privateStorageResourceGroup string

@description('Runtime registry name, derived in main.bicep from the endpoint allowlist in code.')
param runtimeRegistryName string

@description('''
Private DNS zone names for the Azure Monitor private link scope.

Parameters rather than literals. Azure Monitor's private-link zone names are not
exposed by `environment()`, and public audit finding B-06 established that a
hostname hardwired into a template is a hostname that is wrong in every cloud
except the one the author was in. Defaults describe the public cloud; a
sovereign deployment overrides them at the parameter file rather than by editing
the template.
''')
param monitorPrivateDnsZoneNames object = {
  monitor: 'privatelink.monitor.azure.com'
  oms: 'privatelink.oms.opinsights.azure.com'
  ods: 'privatelink.ods.opinsights.azure.com'
  agentsvc: 'privatelink.agentsvc.azure-automation.net'
}

resource runtimeRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: runtimeRegistryName
  location: location
  tags: tags
  sku: { name: 'Premium' }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Disabled'
    networkRuleBypassOptions: 'None'
    anonymousPullEnabled: false
    dataEndpointEnabled: true
    zoneRedundancy: 'Disabled'
    policies: {
      quarantinePolicy: { status: 'enabled' }
      trustPolicy: { type: 'Notary', status: 'enabled' }
      retentionPolicy: { days: 30, status: 'disabled' }
      exportPolicy: { status: 'disabled' }
    }
  }
}

resource existingStorage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: privateStorageAccountName
  scope: resourceGroup(privateStorageResourceGroup)
}

resource acrDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.azurecr.io'
  location: 'global'
  tags: tags
}

resource blobDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.blob.${environment().suffixes.storage}'
  location: 'global'
  tags: tags
}

resource acrDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: acrDnsZone
  name: '${namePrefix}-acr-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

resource blobDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: blobDnsZone
  name: '${namePrefix}-blob-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

resource monitorDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: monitorPrivateDnsZoneNames.monitor
  location: 'global'
  tags: tags
}

resource omsDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: monitorPrivateDnsZoneNames.oms
  location: 'global'
  tags: tags
}

resource odsDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: monitorPrivateDnsZoneNames.ods
  location: 'global'
  tags: tags
}

resource agentsvcDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: monitorPrivateDnsZoneNames.agentsvc
  location: 'global'
  tags: tags
}

resource monitorDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: monitorDnsZone
  name: '${namePrefix}-monitor-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

resource omsDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: omsDnsZone
  name: '${namePrefix}-oms-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

resource odsDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: odsDnsZone
  name: '${namePrefix}-ods-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

resource agentsvcDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: agentsvcDnsZone
  name: '${namePrefix}-agentsvc-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

resource acrPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: '${namePrefix}-pe-acr'
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'acr-connection'
        properties: {
          privateLinkServiceId: runtimeRegistry.id
          groupIds: [ 'registry' ]
        }
      }
    ]
  }
}

resource blobPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: '${namePrefix}-pe-blob'
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'blob-connection'
        properties: {
          privateLinkServiceId: existingStorage.id
          groupIds: [ 'blob' ]
        }
      }
    ]
  }
}

resource acrDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: acrPrivateEndpoint
  name: 'acr-dns'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'acr', properties: { privateDnsZoneId: acrDnsZone.id } }
    ]
  }
  dependsOn: [ acrDnsLink ]
}

resource blobDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: blobPrivateEndpoint
  name: 'blob-dns'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'blob', properties: { privateDnsZoneId: blobDnsZone.id } }
    ]
  }
  dependsOn: [ blobDnsLink ]
}

output runtimeRegistryId string = runtimeRegistry.id
output runtimeRegistryName string = runtimeRegistry.name
output runtimeRegistryLoginServer string = runtimeRegistry.properties.loginServer
output privateStorageId string = existingStorage.id
output acrPrivateEndpointName string = acrPrivateEndpoint.name
output blobPrivateEndpointName string = blobPrivateEndpoint.name
output monitorDnsZoneIds object = {
  monitor: monitorDnsZone.id
  oms: omsDnsZone.id
  ods: odsDnsZone.id
  agentsvc: agentsvcDnsZone.id
  blob: blobDnsZone.id
}
