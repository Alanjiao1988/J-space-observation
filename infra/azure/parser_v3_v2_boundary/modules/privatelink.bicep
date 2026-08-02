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
