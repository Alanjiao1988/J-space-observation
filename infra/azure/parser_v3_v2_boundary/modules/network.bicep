/*
  Network and egress control for the parser-v3-v2 private review boundary.

  Section 5.3 asks for a VNet, subnets, NSGs, a UDR and an Azure Firewall
  Standard with a policy. The shape below is chosen so that the *absence* of a
  rule is a denial rather than an accident:

  - the workload subnet has no route to the Internet except through the
    firewall, so an egress path that nobody wrote does not exist;
  - the firewall policy's threat intel mode is Deny, and there is no
    catch-all allow rule, so a destination that was never registered is
    refused rather than logged;
  - model weights do not travel over the Internet at all. They are staged into
    the private Blob account and reached through its private endpoint, so the
    "model weight lane" is a storage lane, not a firewall exception. An
    exception, once written, is available to everything behind the firewall.
*/

@description('Azure region. Must match the region of the private Blob account holding the retired source.')
param location string

@description('Boundary VNet prefix, taken from address_plan.json. Not a free choice.')
param vnetAddressPrefix string

@description('Subnet prefixes, in the order fixed by address_plan.json.')
param firewallSubnetPrefix string
param firewallManagementSubnetPrefix string
param workloadSubnetPrefix string
param privateEndpointSubnetPrefix string

param namePrefix string
param tags object

var vnetName = '${namePrefix}-vnet'
var workloadSubnetName = 'snet-aca-boundary'
var privateEndpointSubnetName = 'snet-pe-boundary'

// Cloud-specific hosts are derived rather than typed, so the same template is
// correct in a sovereign cloud and so a reader cannot mistake a hard-coded
// string for a deliberate choice about which cloud this runs in.
var resourceManagerHost = replace(replace(environment().resourceManager, 'https://', ''), '/', '')
var loginHost = replace(replace(environment().authentication.loginEndpoint, 'https://', ''), '/', '')
var storageSuffix = environment().suffixes.storage

resource workloadNsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: '${namePrefix}-nsg-aca'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        // Written explicitly rather than relying on the default deny, because a
        // reader must be able to see the denial without knowing the platform
        // defaults, and because a later rule added above it is then visibly a
        // change to a stated position rather than a gap being filled.
        name: 'deny-internet-outbound'
        properties: {
          priority: 4000
          direction: 'Outbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: 'Internet'
          destinationPortRange: '*'
          description: 'All egress must traverse the firewall via the route table.'
        }
      }
      {
        name: 'deny-inbound-internet'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
          description: 'The environment is internal; nothing reaches it from the Internet.'
        }
      }
    ]
  }
}

resource privateEndpointNsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: '${namePrefix}-nsg-pe'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'deny-inbound-internet'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

resource firewallPublicIp 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: '${namePrefix}-pip-fw'
  location: location
  tags: tags
  sku: { name: 'Standard' }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
  }
}

resource firewallManagementPublicIp 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: '${namePrefix}-pip-fwmgmt'
  location: location
  tags: tags
  sku: { name: 'Standard' }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
  }
}

resource firewallPolicy 'Microsoft.Network/firewallPolicies@2023-11-01' = {
  name: '${namePrefix}-fwpolicy'
  location: location
  tags: tags
  properties: {
    sku: { tier: 'Standard' }
    threatIntelMode: 'Deny'
  }
}

resource platformRules 'Microsoft.Network/firewallPolicies/ruleCollectionGroups@2023-11-01' = {
  parent: firewallPolicy
  name: 'platform-required'
  properties: {
    priority: 200
    ruleCollections: [
      {
        ruleCollectionType: 'FirewallPolicyFilterRuleCollection'
        name: 'aca-control-plane'
        priority: 200
        action: { type: 'Allow' }
        rules: [
          {
            // The Container Apps platform cannot start a revision without
            // these. They are listed one by one; a wildcard here would also
            // cover every other use of the same hosts.
            ruleType: 'ApplicationRule'
            name: 'aca-platform-fqdns'
            protocols: [
              { protocolType: 'Https', port: 443 }
            ]
            sourceAddresses: [ workloadSubnetPrefix ]
            targetFqdns: [
              'mcr.microsoft.com'
              '*.data.mcr.microsoft.com'
              resourceManagerHost
              'login.microsoft.com'
              loginHost
              '*.blob.${storageSuffix}'
              'packages.microsoft.com'
              'acs-mirror.azureedge.net'
            ]
          }
        ]
      }
      {
        ruleCollectionType: 'FirewallPolicyFilterRuleCollection'
        name: 'deny-everything-else'
        priority: 65000
        action: { type: 'Deny' }
        rules: [
          {
            ruleType: 'NetworkRule'
            name: 'deny-all'
            ipProtocols: [ 'Any' ]
            sourceAddresses: [ '*' ]
            destinationAddresses: [ '*' ]
            destinationPorts: [ '*' ]
          }
        ]
      }
    ]
  }
}

resource routeTable 'Microsoft.Network/routeTables@2023-11-01' = {
  name: '${namePrefix}-rt-aca'
  location: location
  tags: tags
  properties: {
    disableBgpRoutePropagation: true
    routes: [
      {
        name: 'default-via-firewall'
        properties: {
          addressPrefix: '0.0.0.0/0'
          nextHopType: 'VirtualAppliance'
          nextHopIpAddress: firewall.properties.ipConfigurations[0].properties.privateIPAddress
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: [ vnetAddressPrefix ] }
    subnets: [
      {
        name: 'AzureFirewallSubnet'
        properties: { addressPrefix: firewallSubnetPrefix }
      }
      {
        name: 'AzureFirewallManagementSubnet'
        properties: { addressPrefix: firewallManagementSubnetPrefix }
      }
      {
        name: privateEndpointSubnetName
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          networkSecurityGroup: { id: privateEndpointNsg.id }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// The workload subnet is added after the firewall exists, because its route
// table needs the firewall's private IP. Declaring it inline would create a
// cycle, and breaking that cycle with a hard-coded IP is exactly the kind of
// guess this design is trying to remove.
resource workloadSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-11-01' = {
  parent: vnet
  name: workloadSubnetName
  properties: {
    addressPrefix: workloadSubnetPrefix
    networkSecurityGroup: { id: workloadNsg.id }
    routeTable: { id: routeTable.id }
    delegations: [
      {
        name: 'aca-environment'
        properties: { serviceName: 'Microsoft.App/environments' }
      }
    ]
  }
}

resource firewall 'Microsoft.Network/azureFirewalls@2023-11-01' = {
  name: '${namePrefix}-fw'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'AZFW_VNet'
      tier: 'Standard'
    }
    firewallPolicy: { id: firewallPolicy.id }
    ipConfigurations: [
      {
        name: 'fw-ipconfig'
        properties: {
          subnet: { id: '${vnet.id}/subnets/AzureFirewallSubnet' }
          publicIPAddress: { id: firewallPublicIp.id }
        }
      }
    ]
    managementIpConfiguration: {
      name: 'fw-mgmt-ipconfig'
      properties: {
        subnet: { id: '${vnet.id}/subnets/AzureFirewallManagementSubnet' }
        publicIPAddress: { id: firewallManagementPublicIp.id }
      }
    }
  }
  dependsOn: [ platformRules ]
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output workloadSubnetId string = workloadSubnet.id
output privateEndpointSubnetId string = '${vnet.id}/subnets/${privateEndpointSubnetName}'
output firewallPrivateIp string = firewall.properties.ipConfigurations[0].properties.privateIPAddress
output firewallPolicyId string = firewallPolicy.id
