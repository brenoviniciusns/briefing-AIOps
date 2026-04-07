targetScope = 'resourceGroup'

@description('Principal ID (object id) da Managed Identity da Function App.')
param principalId string

@description('Nome da storage account (ADLS Gen2).')
param storageAccountName string

@description('Nome do Key Vault.')
param keyVaultName string

@description('Nome do recurso Azure OpenAI (Cognitive Services).')
param openAiAccountName string

// IDs de built-in roles (globais na subscrição Azure)
var roleStorageBlobDataContributor = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)
var roleKeyVaultSecretsUser = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)
var roleCognitiveServicesOpenAiUser = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)

resource stg 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource oai 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: openAiAccountName
}

resource raBlob 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(stg.id, principalId, roleStorageBlobDataContributor)
  scope: stg
  properties: {
    roleDefinitionId: roleStorageBlobDataContributor
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

resource raKv 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, principalId, roleKeyVaultSecretsUser)
  scope: kv
  properties: {
    roleDefinitionId: roleKeyVaultSecretsUser
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

resource raOpenAi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(oai.id, principalId, roleCognitiveServicesOpenAiUser)
  scope: oai
  properties: {
    roleDefinitionId: roleCognitiveServicesOpenAiUser
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

output assignmentsCreated bool = true
