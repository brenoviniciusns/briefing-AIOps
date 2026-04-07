targetScope = 'subscription'

@description('Nome do resource group.')
param name string

@description('Localização do resource group.')
param location string

@description('Tags aplicadas ao resource group.')
param tags object = {}

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: name
  location: location
  tags: tags
}

output id string = rg.id
output name string = rg.name
