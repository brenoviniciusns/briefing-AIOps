targetScope = 'resourceGroup'

@description('Prefixo para nomes de recursos (ex.: techintel).')
param projectPrefix string = 'techintel'

@description('Ambiente (dev, prod).')
param environment string = 'dev'

@description('Localização Azure (alinhada ao resource group).')
param location string = resourceGroup().location

@description('Nome do deployment OpenAI (deve coincidir com App Settings da Function).')
param openAiDeploymentName string = 'gpt-4o'

@description('Modelo OpenAI.')
param openAiModelName string = 'gpt-4o'

@description('Versão do modelo.')
param openAiModelVersion string = '2024-08-06'

@description('Criar roleAssignments (MI da Function → Storage/KV/OpenAI). Requer Owner ou User Access Administrator no RG.')
param deployRbacAssignments bool = false

@description('Omitir chaves OPENAI/STORAGE nas App Settings e usar MI + Azure AD no código.')
param useManagedIdentityDataPlane bool = false

var suffix = uniqueString(subscription().id, resourceGroup().id, projectPrefix, environment)
var storageName = toLower(take('${projectPrefix}${environment}st${suffix}', 24))
var kvName = take('${projectPrefix}-${environment}-kv-${suffix}', 24)
var openAiName = take('${projectPrefix}-${environment}-oai-${suffix}', 24)
var openAiSubdomain = toLower(take('${projectPrefix}${environment}oai${suffix}', 63))
var funcName = take('${projectPrefix}-${environment}-func-${suffix}', 60)
var aiName = take('${projectPrefix}-${environment}-ai-${suffix}', 255)

module storage 'modules/storage.bicep' = {
  name: 'storage-deploy'
  params: {
    storageAccountName: storageName
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault-deploy'
  params: {
    keyVaultName: kvName
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
  }
}

module appinsights 'modules/appinsights.bicep' = {
  name: 'appinsights-deploy'
  params: {
    name: aiName
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
  }
}

module openai 'modules/openai.bicep' = {
  name: 'openai-deploy'
  params: {
    openAiAccountName: openAiName
    customSubDomainName: openAiSubdomain
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
    deploymentName: openAiDeploymentName
    modelName: openAiModelName
    modelVersion: openAiModelVersion
  }
}

module functionapp 'modules/functionapp.bicep' = {
  name: 'functionapp-deploy'
  params: {
    functionAppName: funcName
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
    storageConnectionString: storage.outputs.connectionString
    openAiEndpoint: openai.outputs.openAiEndpoint
    openAiApiKey: openai.outputs.openAiApiKey
    openAiDeploymentName: openAiDeploymentName
    storageAccountName: storage.outputs.storageAccountName
    storageAccountKey: storage.outputs.primaryKey
    useManagedIdentityDataPlane: useManagedIdentityDataPlane
    applicationInsightsConnectionString: appinsights.outputs.connectionString
    contentShareName: take(toLower(replace(funcName, '-', '')), 63)
  }
}

module rbac 'modules/rbac.bicep' = if (deployRbacAssignments) {
  name: 'rbac-deploy'
  params: {
    principalId: functionapp.outputs.principalId
    storageAccountName: storage.outputs.storageAccountName
    keyVaultName: keyvault.outputs.keyVaultName
    openAiAccountName: openai.outputs.openAiAccountName
  }
}

output resourceGroupName string = resourceGroup().name
output storageAccountName string = storage.outputs.storageAccountName
output keyVaultName string = keyvault.outputs.keyVaultName
output keyVaultUri string = keyvault.outputs.keyVaultUri
output openAiEndpoint string = openai.outputs.openAiEndpoint
output openAiDeploymentName string = openAiDeploymentName
output functionAppName string = functionapp.outputs.functionAppName
output functionAppUrl string = 'https://${functionapp.outputs.functionAppHostName}'
output functionPrincipalId string = functionapp.outputs.principalId
output applicationInsightsConnectionString string = appinsights.outputs.connectionString
