@description('Nome único da storage account (3-24 chars, minúsculas e números).')
param storageAccountName string

@description('Localização Azure.')
param location string

@description('Tags.')
param tags object = {}

resource stg 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    isHnsEnabled: true
    accessTier: 'Hot'
  }
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: 'default'
  parent: stg
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

var containerNames = [
  'raw'
  'processed'
  'reports'
  'idempotency'
]

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for name in containerNames: {
  name: name
  parent: blob
  properties: {
    publicAccess: 'None'
  }
}]

#disable-next-line outputs-should-not-contain-secrets
var connectionString = 'DefaultEndpointsProtocol=https;AccountName=${stg.name};AccountKey=${stg.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

output storageAccountId string = stg.id
output storageAccountName string = stg.name
output blobEndpoint string = stg.properties.primaryEndpoints.blob
output dfsEndpoint string = stg.properties.primaryEndpoints.dfs
#disable-next-line outputs-should-not-contain-secrets
output connectionString string = connectionString
#disable-next-line outputs-should-not-contain-secrets
output primaryKey string = stg.listKeys().keys[0].value
