@description('Nome do Application Insights.')
param name string

@description('Localização.')
param location string

@description('Tags.')
param tags object = {}

resource ai 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
    RetentionInDays: 90
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output connectionString string = ai.properties.ConnectionString
output instrumentationKey string = ai.properties.InstrumentationKey
output appInsightsId string = ai.id
