@description('Nome do recurso Azure OpenAI.')
param openAiAccountName string

@description('Subdomínio personalizado (único).')
param customSubDomainName string

@description('Localização (regiões com OpenAI disponível).')
param location string

@description('Tags.')
param tags object = {}

@description('Nome lógico do deployment do modelo.')
param deploymentName string = 'gpt-4o'

@description('Nome do modelo OpenAI.')
param modelName string = 'gpt-4o'

@description('Versão do modelo.')
param modelVersion string = '2024-11-20'

@description('Capacidade (TPM em milhares para alguns SKUs).')
param capacity int = 10

resource openai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiAccountName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: customSubDomainName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openai
  name: deploymentName
  sku: {
    name: 'Standard'
    capacity: capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

var keys = openai.listKeys()

output openAiAccountId string = openai.id
output openAiAccountName string = openai.name
// properties.endpoint já inclui esquema (https://...).
output openAiEndpoint string = openai.properties.endpoint
output openAiApiKey string = keys.key1
output openAiDeploymentName string = deploymentName
