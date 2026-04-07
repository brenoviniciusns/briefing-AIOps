targetScope = 'subscription'

@description('Prefixo para nomes de recursos (ex.: techintel).')
param projectPrefix string = 'techintel'

@description('Ambiente (dev, prod).')
param environment string = 'dev'

@description('Localização Azure.')
param location string = 'eastus'

@description('Criar resource group via Bicep (se false, o RG deve existir).')
param createResourceGroup bool = true

@description('Nome do resource group.')
param resourceGroupName string = ''

@description('Nome do deployment OpenAI (deve coincidir com App Settings da Function).')
param openAiDeploymentName string = 'gpt-4o'

@description('Modelo OpenAI.')
param openAiModelName string = 'gpt-4o'

@description('Versão do modelo.')
param openAiModelVersion string = '2024-11-20'

@description('Criar roleAssignments (MI da Function → Storage/KV/OpenAI). Requer Owner ou User Access Administrator na subscrição ou RG.')
param deployRbacAssignments bool = false

@description('Omitir chaves OPENAI/STORAGE nas App Settings e usar MI + Azure AD no código. Exige roles já aplicadas (use com deployRbacAssignments ou RBAC manual).')
param useManagedIdentityDataPlane bool = false

var suffix = uniqueString(subscription().id, projectPrefix, environment)
var rgName = !empty(resourceGroupName) ? resourceGroupName : '${projectPrefix}-${environment}-rg'
var storageName = toLower(take('${projectPrefix}${environment}st${suffix}', 24))
var kvName = take('${projectPrefix}-${environment}-kv-${suffix}', 24)
var openAiName = take('${projectPrefix}-${environment}-oai-${suffix}', 24)
var openAiSubdomain = toLower(take('${projectPrefix}${environment}oai${suffix}', 63))
var funcName = take('${projectPrefix}-${environment}-func-${suffix}', 60)
var aiName = take('${projectPrefix}-${environment}-ai-${suffix}', 255)

module rgModule 'modules/rg.bicep' = if (createResourceGroup) {
  name: 'rg-deploy'
  params: {
    name: rgName
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage-deploy'
  scope: resourceGroup(rgName)
  params: {
    storageAccountName: storageName
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
  }
  dependsOn: createResourceGroup ? [ rgModule ] : []
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault-deploy'
  scope: resourceGroup(rgName)
  params: {
    keyVaultName: kvName
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
  }
  dependsOn: createResourceGroup ? [ rgModule ] : []
}

module appinsights 'modules/appinsights.bicep' = {
  name: 'appinsights-deploy'
  scope: resourceGroup(rgName)
  params: {
    name: aiName
    location: location
    tags: {
      environment: environment
      project: projectPrefix
    }
  }
  dependsOn: createResourceGroup ? [ rgModule ] : []
}

module openai 'modules/openai.bicep' = {
  name: 'openai-deploy'
  scope: resourceGroup(rgName)
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
  dependsOn: createResourceGroup ? [ rgModule ] : []
}

module functionapp 'modules/functionapp.bicep' = {
  name: 'functionapp-deploy'
  scope: resourceGroup(rgName)
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
  dependsOn: createResourceGroup ? [ rgModule ] : []
}

module rbac 'modules/rbac.bicep' = if (deployRbacAssignments) {
  name: 'rbac-deploy'
  scope: resourceGroup(rgName)
  params: {
    principalId: functionapp.outputs.principalId
    storageAccountName: storage.outputs.storageAccountName
    keyVaultName: keyvault.outputs.keyVaultName
    openAiAccountName: openai.outputs.openAiAccountName
  }
}

output resourceGroupName string = rgName
output storageAccountName string = storage.outputs.storageAccountName
@description('Não expor em pipelines públicos; obter chaves com: az storage account keys list')
output keyVaultName string = keyvault.outputs.keyVaultName
output keyVaultUri string = keyvault.outputs.keyVaultUri
output openAiEndpoint string = openai.outputs.openAiEndpoint
output openAiDeploymentName string = openAiDeploymentName
output functionAppName string = functionapp.outputs.functionAppName
output functionAppUrl string = 'https://${functionapp.outputs.functionAppHostName}'
output functionPrincipalId string = functionapp.outputs.principalId
output applicationInsightsConnectionString string = appinsights.outputs.connectionString
