@description('Nome da Function App.')
param functionAppName string

@description('Localização.')
param location string

@description('Tags.')
param tags object = {}

@description('Connection string da storage (runtime + conteúdo).')
param storageConnectionString string

@description('Endpoint Azure OpenAI.')
param openAiEndpoint string

@description('Chave API Azure OpenAI.')
@secure()
param openAiApiKey string

@description('Nome do deployment do modelo.')
param openAiDeploymentName string

@description('Nome da storage account (para paths ABFSS e env).')
param storageAccountName string

@description('Chave da storage (para Delta / DataLake SDK). Vazio se useManagedIdentityDataPlane=true.')
@secure()
param storageAccountKey string

@description('Se true, omite chaves nas App Settings e ativa flags para MI + Azure AD no código.')
param useManagedIdentityDataPlane bool = false

@description('Application Insights connection string.')
param applicationInsightsConnectionString string

@description('Content share name (único por app).')
param contentShareName string

var planName = '${functionAppName}-plan'

// Consumption Linux (Y1) é bloqueado em algumas subscrições/RGs (LinuxDynamicWorkersNotAllowedInResourceGroup).
// EP1 (Elastic Premium) costuma ser aceite para Functions Python em Linux.
resource hostingPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  sku: {
    name: 'EP1'
    tier: 'ElasticPremium'
  }
  kind: 'elastic'
  properties: {
    reserved: true
    maximumElasticWorkerCount: 1
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: false
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: storageConnectionString
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: storageConnectionString
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: contentShareName
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'AzureWebJobsFeatureFlags'
          value: 'EnableWorkerIndexing'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsConnectionString
        }
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccountName
        }
        {
          name: 'STORAGE_ACCOUNT_KEY'
          value: useManagedIdentityDataPlane ? '' : storageAccountKey
        }
        {
          name: 'USE_MANAGED_IDENTITY_DATA_PLANE'
          value: useManagedIdentityDataPlane ? 'true' : 'false'
        }
        {
          name: 'OPENAI_USE_AZURE_AD'
          value: useManagedIdentityDataPlane ? 'true' : 'false'
        }
        {
          name: 'ADLS_CONTAINER_RAW'
          value: 'raw'
        }
        {
          name: 'ADLS_CONTAINER_PROCESSED'
          value: 'processed'
        }
        {
          name: 'ADLS_CONTAINER_REPORTS'
          value: 'reports'
        }
        {
          name: 'DELTA_TABLE_PATH'
          value: 'articles'
        }
        {
          name: 'OPENAI_API_KEY'
          value: useManagedIdentityDataPlane ? '' : openAiApiKey
        }
        {
          name: 'OPENAI_ENDPOINT'
          value: openAiEndpoint
        }
        {
          name: 'OPENAI_DEPLOYMENT_NAME'
          value: openAiDeploymentName
        }
        {
          name: 'MAX_ARTICLES_PER_RUN'
          value: '35'
        }
      ]
    }
  }
}

output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output functionAppHostName string = functionApp.properties.defaultHostName
output principalId string = functionApp.identity.principalId
